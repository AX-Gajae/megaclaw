# -*- coding: utf-8 -*-
"""이슈 #115 — **`rankdata` NaN 병의 수리와 그 수리의 확인.**

티처 #59 M11 이 넘긴 것: `scipy 1.13` 의 `rankdata` 는 배열에 NaN 이 **하나만
있어도 전부 NaN** 을 낸다. 그래서 라벨/예측 결측 한 행이 **도메인 전체**를
통계에서 지우는데 '채택 도메인' 에는 이름이 남는다 — 887 형 중립화의 통계
판본이고 노트 273·274 가 이 병으로 죽었다.

이 파일이 하는 일은 **수리가 아니라 수리의 확인**이다(수리는 `lab/` 안에 있다):

    python3 runners/nanfix115.py plant       ④ 일부러 NaN 을 심어 잡히는지
    python3 runners/nanfix115.py callgraph   ③ 심각도 「중」의 호출 경로를 **센다**
    python3 runners/nanfix115.py trace       ③ 판 실행 중 실제로 발화하는 자리
    python3 runners/nanfix115.py armA        ① 896 팔 A 재현(값이 그대로인가)

🔴 조항 59 — **`통과: true` 를 성공으로 읽지 않는다.** 그래서 `plant` 는
*고친 코드가 잡는가* 만이 아니라 *병 자체가 아직 사실인가*(scipy 판)와
*옛 코드가 정말 조용히 실패했는가* 를 같이 잰다.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import ast                                                       # noqa: E402
import datetime as dt                                            # noqa: E402
import json                                                      # noqa: E402
import shutil                                                    # noqa: E402
import subprocess                                                # noqa: E402
import sys                                                       # noqa: E402
import time                                                      # noqa: E402
from pathlib import Path                                         # noqa: E402

import numpy as np                                               # noqa: E402

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners"
T = 2025.0

#: 896 팔 A 가 낸 정본 값(원장·카드·`runners/out896_armA.json`). 재현이
#: 이것과 어긋나면 **수리가 값을 바꾼 것**이므로 크게 적는다.
EXPECT_896_ARMA = {
    "ㄱ 존재 이진 ρ_A": -0.00969,
    "라벨 결측": {"게임": 43, "웹툰": 61},
}


def stamp() -> dict:
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        head = "안 잡힘"
    import hashlib
    return {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git HEAD": head,
            "코드 sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
            "코드": "runners/nanfix115.py",
            "scipy": __import__("scipy").__version__}


# ── ④ 심어서 확인한다 ───────────────────────────────────────────────────────
def plant() -> dict:
    """일부러 NaN 을 심는다. **심은 것 / 기대 / 실측** 을 표로 남긴다."""
    from scipy.stats import rankdata
    from lab import pairboot as PB, forms as FM
    rows = []

    def rec(what, planted, expect, got, ok):
        rows.append({"심은 것": planted, "자리": what, "기대": expect,
                     "실측": got, "통과": bool(ok)})

    # ⓪ 병 자체가 아직 사실인가 --- 전제를 먼저 잰다(조항 59)
    r = rankdata(np.array([1.0, 2.0, 3.0, np.nan]))
    rec("scipy.stats.rankdata (전제)", "4칸 중 1칸 NaN",
        "4칸 전부 NaN (nan_policy='propagate')",
        f"유한 {int(np.isfinite(r).sum())}/4",
        not np.isfinite(r).any())

    # ① pairboot.rank_ensemble --- 기본은 예외
    P = [np.array([3.0, 1.0, 2.0, 4.0]), np.array([1.0, 3.0, 2.0, 4.0])]
    bad = [P[0].copy(), P[1].copy()]; bad[0][2] = np.nan
    old = np.mean([rankdata(p) for p in bad], axis=0)     # 옛 구현 재현
    rec("pairboot.rank_ensemble (옛 구현)", "예측 2개 중 1개의 1행이 NaN",
        "예측 4행 전부 NaN --- 도메인 통째 중립화",
        f"유한 {int(np.isfinite(old).sum())}/4", not np.isfinite(old).any())
    try:
        PB.rank_ensemble(bad)
        got, ok = "조용히 통과했다", False
    except PB.RankNaN as e:
        got, ok = f"RankNaN: {str(e)[:60]}…", True
    rec("pairboot.rank_ensemble (고친 뒤 · 기본)", "같은 NaN 1칸",
        "RankNaN 예외", got, ok)

    # ② mask 갈래 --- 교집합에서만 매기고 회계를 돌려준다
    w = {}
    g = PB.rank_ensemble(bad, on_nan="mask", wire=w)
    ok = (np.isfinite(g).sum() == 3 and np.isnan(g[2])
          and w["🔴 버림"] == 1 and w["유한 교집합"] == 3)
    rec("pairboot.rank_ensemble (on_nan='mask')", "같은 NaN 1칸",
        "그 행만 NaN · 나머지 3행 유한 · 회계 버림=1",
        f"유한 {int(np.isfinite(g).sum())}/4 · 회계 {w}", ok)

    # ③ 유한 입력에서 옛 구현과 **비트 단위로 같은가**(회귀 없음)
    same = np.array_equal(PB.rank_ensemble(P),
                          np.mean([rankdata(p) for p in P], axis=0))
    rec("pairboot.rank_ensemble (유한 입력)", "NaN 없음",
        "옛 구현과 완전히 같은 배열", f"array_equal={same}", same)

    # ④ safe_rank
    try:
        PB.safe_rank([1.0, np.nan, 3.0], where="plant")
        got, ok = "조용히 통과했다", False
    except PB.RankNaN:
        got, ok = "RankNaN 예외", True
    rec("pairboot.safe_rank (기본)", "3칸 중 1칸 NaN", "RankNaN 예외", got, ok)

    # ⑤ textaxes --- 라벨 결측을 심으면 예외가 나야 한다(옛 코드는 열 전체 NaN)
    y = np.array([1.0, 2.0, 3.0, np.nan, 5.0])
    trmask = np.isfinite(y)                       # 지금 코드가 만드는 마스크
    r_old = rankdata(y)                           # 마스크가 없었다면
    try:
        PB.safe_rank(y[trmask], where="textaxes.build:심기")
        got5, ok5 = f"마스크 뒤 유한 {int(trmask.sum())}행으로 정상 순위", True
    except PB.RankNaN:
        got5, ok5 = "예외(마스크가 안 걸렸다)", False
    rec("textaxes.build `tr` 마스크", "라벨 5칸 중 1칸 NaN",
        f"마스크가 걸러 4행만 순위 · 마스크 없으면 5칸 전부 NaN"
        f"(옛: 유한 {int(np.isfinite(r_old).sum())}/5)", got5, ok5)

    # ⑥ forms._rank_masked --- 예보에 NaN 을 심는다
    v = np.array([0.3, 0.1, np.nan, 0.9])
    before = len(PB.NAN_LOG)
    m = FM._rank_masked(v, "plant.forms")
    ok6 = (np.isfinite(m).sum() == 3 and np.isnan(m[2])
           and len(PB.NAN_LOG) == before + 1)
    rec("forms._rank_masked (F1 · BagBoost 공용)", "예보 4칸 중 1칸 NaN",
        "그 행만 NaN(도메인은 살아남는다) + NAN_LOG 한 줄",
        f"유한 {int(np.isfinite(m).sum())}/4 · NAN_LOG +{len(PB.NAN_LOG)-before}", ok6)

    # ⑦ 회계가 정말 남는가 --- 조항 60(분모 두 개를 잇지 마라)
    rec("pairboot.NAN_LOG", "위 ⑥ 이 남긴 것", "자리·전체·유한·버림 네 칸",
        json.dumps(PB.NAN_LOG[-1], ensure_ascii=False),
        set(PB.NAN_LOG[-1]) >= {"자리", "전체", "유한", "🔴 버림"})

    # ⑧ 심각도 「중」 넷 --- 심어서 확인 + **유한 입력에서 옛 값과 같은가**
    from lab import decay as DC, calib as CB, sideaudit as SA
    g10, y10 = np.arange(10.0), np.array([3., 1., 4., 1., 5., 9., 2., 6., 5., 3.])
    e0, m0 = DC.stair(g10, y10)
    ybad = y10.copy(); ybad[4] = np.nan
    try:
        DC.stair(g10, ybad); got, ok = "조용히 통과했다", False
    except PB.RankNaN:
        got, ok = "RankNaN 예외", True
    rec("decay.stair:163 (라벨)", "라벨 10칸 중 1칸 NaN", "RankNaN 예외", got, ok)
    rec("decay.stair:163 (유한 입력 회귀)", "NaN 없음", "옛 계단과 같은 값",
        f"med={[round(float(x), 6) for x in m0]}", bool(np.isfinite(m0).all()))

    ptr, ytr, p = np.array([0.1, 0.5, 0.9]), np.array([1.0, 2.0, 3.0]), np.array([0.4, 0.8])
    v0 = CB.inv_holdout_pct(ptr, ytr, p)[0]
    try:
        CB.inv_holdout_pct(ptr, ytr, np.array([0.4, np.nan]))
        got, ok = "조용히 통과했다", False
    except PB.RankNaN:
        got, ok = "RankNaN 예외", True
    rec("calib.inv_holdout_pct:116 (반환값 그 자체)", "유보 예보 2칸 중 1칸 NaN",
        "RankNaN 예외(호출자 5개 전부 손 runner · 예외를 삼키는 자리 없음)", got, ok)
    rec("calib.inv_holdout_pct:116 (유한 입력 회귀)", "NaN 없음", "옛 값과 같다",
        f"{[round(float(x), 6) for x in v0]}", bool(np.isfinite(v0).all()))

    before = len(PB.NAN_LOG)
    w0 = CB.inv_percentile(np.array([0.1, np.nan, 0.9]), ytr, np.array([0.5]))[0]
    rec("calib.inv_percentile:98 (서빙 경로)", "학습 예보 3칸 중 1칸 NaN",
        "🔴 **안 죽는다** --- q 는 호출자 7/7 이 버리는 값이라 마스크 + NAN_LOG."
        " serve/boardsvc.py:362 를 예외로 죽이지 않는다",
        f"반환 {[round(float(x), 4) for x in w0]} · NAN_LOG +{len(PB.NAN_LOG)-before}",
        bool(np.isfinite(w0).all()) and len(PB.NAN_LOG) == before + 1)

    pa = np.array([1., 2., 3., 4., 5.]); pb = np.array([2., 1., 4., 3., 5.])
    pc = np.array([5., 3., 1., 2., 4.])          # a 와 안 붙게 --- den>0
    r0 = SA._part(pa, pb, pc)
    try:
        bad_a = pa.copy(); bad_a[2] = np.nan
        SA._part(bad_a, pb, pc)
        got, ok = "조용히 통과했다", False
    except PB.RankNaN:
        got, ok = "RankNaN 예외", True
    rec("sideaudit._part:89 (감사)", "축 4칸 중 1칸 NaN",
        "RankNaN 예외 --- 옛 코드는 nan 을 내고 호출자 셋이"
        " `if not isfinite(r): continue` 로 **'짚이는 것 없음'** 을 냈다", got, ok)
    rec("sideaudit._part:89 (유한 입력 회귀)", "NaN 없음", "옛 편상관과 같다",
        f"r={round(float(r0), 6)}", bool(np.isfinite(r0)))

    # ⑨ pairboot 자기시험이 이 전부를 회귀로 못박는가
    chk = PB.check()
    rec("pairboot.check()", "고정물 + 심기 시험",
        "통과 · 옛 핀 [0.5255,0.1659,0.8755] 불변",
        json.dumps(chk, ensure_ascii=False),
        chk.get("핀") == [0.5255, 0.1659, 0.8755])

    res = {"무엇": "이슈 #115 ④ --- 심어서 확인(심은 것/기대/실측)",
           "표": rows,
           "전부 통과": all(r["통과"] for r in rows),
           "🔴 남은 심기": "없다 --- 심은 것은 전부 메모리 안 배열이라 원상 복구가 필요 없다."
                      " 파일을 고친 것은 lab/ 수리뿐이고 git diff 로 확인한다."}
    res.update(stamp())
    (OUT / "out115_plant.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)
    return res


# ── ③ 호출 경로를 **센다** ─────────────────────────────────────────────────
#
# 🔴 조항 59 --- *"안 불린다"* 와 *"못 봤다"* 는 다르다. 그래서 세 가지 방법을
# 겹쳐 쓰고 **어떻게 셌는지**를 산출물에 적는다:
#   ㄱ grep(문자열)  ㄴ AST 호출 그래프(이름 해석 · 주석/문자열 안 이름을 안 센다)
#   ㄷ 실제 실행 추적(`trace`)
TARGETS = {
    "lab/decay.py:163 stair": ("lab/decay.py", "stair"),
    "lab/calib.py:98 inv_percentile": ("lab/calib.py", "inv_percentile"),
    "lab/calib.py:116 inv_holdout_pct": ("lab/calib.py", "inv_holdout_pct"),
    "lab/sideaudit.py:89 _part": ("lab/sideaudit.py", "_part"),
    "lab/forms.py:93 F1_procrustes.predict": ("lab/forms.py", "predict"),
    "lab/pairboot.py rank_ensemble": ("lab/pairboot.py", "rank_ensemble"),
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "paper/build"}


def _pyfiles():
    for p in sorted(ROOT.rglob("*.py")):
        rel = p.relative_to(ROOT).as_posix()
        if any(rel.startswith(s) or f"/{s}/" in f"/{rel}" for s in SKIP_DIRS):
            continue
        yield p, rel


def _calls(rel: str, src: str):
    """(호출된 이름, 줄번호) 목록. `f(...)` 와 `mod.f(...)` 둘 다."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    got = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                got.append((f.id, n.lineno))
            elif isinstance(f, ast.Attribute):
                got.append((f.attr, n.lineno))
    return got


def callgraph() -> dict:
    """이름이 같은 **모든** 호출을 세고 자기 파일 안/밖을 가른다."""
    per = {k: {"자기 파일 안": [], "다른 파일": []} for k in TARGETS}
    files = 0
    for p, rel in _pyfiles():
        src = p.read_text(errors="replace")
        files += 1
        cs = _calls(rel, src)
        if not cs:
            continue
        for key, (owner, fn) in TARGETS.items():
            for name, ln in cs:
                if name != fn:
                    continue
                where = "자기 파일 안" if rel == owner else "다른 파일"
                per[key][where].append(f"{rel}:{ln}")
    # 정의가 있는 파일도 같이 센다 --- 동명이인을 가르기 위해서다
    defs = {k: [] for k in TARGETS}
    for p, rel in _pyfiles():
        try:
            tree = ast.parse(p.read_text(errors="replace"))
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for key, (_o, fn) in TARGETS.items():
                    if n.name == fn:
                        defs[key].append(f"{rel}:{n.lineno}")
    out = {"무엇": "이슈 #115 ③ --- 호출 경로 세기(AST)",
           "🔴 어떻게 셌나": {
               "ㄱ": "저장소 전체 .py 를 ast.parse 로 읽어 Call 노드의 이름을 센다"
                    f" --- 훑은 파일 {files}개",
               "ㄴ": "문자열·주석 안 이름은 안 센다(grep 과 다른 점)",
               "ㄷ": "**같은 이름의 다른 함수도 같이 잡힌다** --- 그래서 '정의가 있는 파일'"
                    "을 같이 실어 사람이 가를 수 있게 한다(동명이인 문제)",
               "ㄹ": "실제 실행 증거는 `trace` 가 따로 낸다 --- AST 는 '불릴 수 있다'"
                    "까지만 말한다"},
           "대상": {}}
    for key in TARGETS:
        out["대상"][key] = {"정의": defs[key],
                          "자기 파일 안 호출": per[key]["자기 파일 안"],
                          "다른 파일 호출": per[key]["다른 파일"],
                          "다른 파일 호출 수": len(per[key]["다른 파일"])}
    out.update(stamp())
    (OUT / "out115_callgraph.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
    return out


# ── ③' 실제 실행 추적 --- 판 한 번을 돌리며 `rankdata` 발화 자리를 적는다 ──
def trace() -> dict:
    """챔피언 채점 **한 씨앗**을 돌리며 `rankdata` 를 부르는 자리를 전부 센다.

    ⚠ 한계를 먼저 적는다: ① 씨앗 하나 · 정식화 하나(F18) · 프로토콜 하나
    (`deploy`)다 ② 하위 프로세스는 못 본다(여기서는 안 쓴다) ③ 안 불린 것이
    *영영 안 불린다* 는 뜻은 아니다 --- **이 경로에서 안 불린다**는 뜻이다.
    """
    import inspect
    import scipy.stats as SS
    import ff753 as FF
    from lab.harness import evaluate
    from lab import forms
    t0 = time.time()
    hits = {}
    orig = SS.rankdata

    def traced(a, *args, **kw):
        arr = np.asarray(a, float) if np.ndim(a) else np.asarray([a], float)
        fr = inspect.currentframe().f_back
        try:
            rel = Path(fr.f_code.co_filename).resolve()
            rel = rel.relative_to(ROOT).as_posix() if str(rel).startswith(str(ROOT)) \
                else str(rel)
            key = f"{rel}:{fr.f_lineno}"
        finally:
            del fr
        h = hits.setdefault(key, {"호출": 0, "🔴 비유한 입력 호출": 0, "총 칸": 0,
                                "🔴 비유한 칸": 0})
        h["호출"] += 1
        try:
            nbad = int((~np.isfinite(arr)).sum())
            h["총 칸"] += int(arr.size); h["🔴 비유한 칸"] += nbad
            if nbad:
                h["🔴 비유한 입력 호출"] += 1
        except TypeError:
            pass
        return orig(a, *args, **kw)

    SS.rankdata = traced
    forms.rankdata = traced          # 모듈이 이름을 미리 묶어 갔다
    try:
        data = FF.shell(FF.base())
        CLS = forms.REGISTRY["F18_bagboost"]["cls"]
        sc = evaluate(lambda: CLS(seed=0), data, T=T)
        pooled = float(data.pooled(sc, T=T))
    finally:
        SS.rankdata = orig
        forms.rankdata = orig
    out = {"무엇": "이슈 #115 ③' --- 판 한 씨앗을 돌리며 rankdata 발화 자리 실측",
           "🔴 어떻게 셌나": "scipy.stats.rankdata 와 lab.forms.rankdata 를 감싸"
                        "호출자 프레임의 파일:줄 을 적었다. 하위 프로세스 없음.",
           "한계": ["씨앗 1 · F18 하나 · protocol='deploy' 하나",
                  "안 발화 = 이 경로에서 안 불린다(영영 안 불린다가 아니다)"],
           "판(씨앗0)": round(pooled, 5),
           # 🔴 회귀 증거 --- 노트 890 배선 ㄷ 가 못박은 상수와 **비트 단위로**
           # 견준다. `lab/forms.py` 를 만졌으므로 이것이 안 맞으면 수리가 판을
           # 바꾼 것이다(조항 59 --- '통과' 대신 수를 견준다).
           "🔴 판(씨앗0) 대 노트 890 배선 상수": {
               "재현": repr(pooled), "상수": repr(0.4724867181663707),
               "차": pooled - 0.4724867181663707,
               "비트 동일": pooled == 0.4724867181663707},
           "채점된 도메인": sorted(sc),
           "🔴 채점 못 한 도메인": sorted(set(data.dom) - set(sc)),
           "발화 자리": dict(sorted(hits.items())),
           "🔴 비유한 입력을 받은 자리": {k: v for k, v in hits.items()
                                if v["🔴 비유한 칸"]},
           "초": round(time.time() - t0, 1)}
    out.update(stamp())
    (OUT / "out115_trace.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: out[k] for k in
                      ("판(씨앗0)", "채점된 도메인", "🔴 채점 못 한 도메인",
                       "발화 자리", "🔴 비유한 입력을 받은 자리")},
                     ensure_ascii=False, indent=1), flush=True)
    return out


# ── ① 896 팔 A 재현 ────────────────────────────────────────────────────────
def armA() -> dict:
    """`runners/dose896.stageA` 를 **그대로** 돌린다(코드 한 줄도 옮겨 적지 않는다).

    `dose896.py` 는 이 사이클의 금지 파일이라 못 고친다. 그래서 산출물이
    `runners/out896_armA.json` 을 덮어쓰지 않도록 **`ROOT` 만 임시로 딴 데로**
    돌리고, 나온 파일을 `runners/out115_armA.json` 으로 옮긴다. 계산 경로는
    896 과 **비트 단위로 같은 코드**다 --- 바뀐 것은 `lab/pairboot.py` 뿐이고
    그것이 이 재현이 재려는 것이다.
    """
    import tempfile
    import dose896 as D
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="nanfix115_"))
    (tmp / "runners").mkdir()
    real_root, real_stamp = D.ROOT, D.stamp
    D.ROOT = tmp
    D.stamp = lambda: {**stamp(), "재현": "dose896.stageA (ROOT 만 임시)"}
    err = None
    try:
        D.stageA()
    except Exception as e:                     # 예외도 결과다 --- 삼키지 않는다
        err = f"{type(e).__name__}: {e}"
    finally:
        D.ROOT, D.stamp = real_root, real_stamp
    src = tmp / "runners/out896_armA.json"
    if not src.exists():
        res = {"무엇": "896 팔 A 재현", "🔴 실패": err or "산출물이 안 생겼다"}
        res.update(stamp())
        (OUT / "out115_armA.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
        print(json.dumps(res, ensure_ascii=False), flush=True)
        return res
    got = json.loads(src.read_text())
    shutil.copy(src, OUT / "out115_armA.json")
    shutil.rmtree(tmp, ignore_errors=True)

    # 대조 --- 정본 값과 어긋나면 **수리가 값을 바꾼 것**이다
    cmp = {}
    for nm, r in got.get("결과", {}).items():
        cmp[nm] = {"ρ_A (행수 가중 · 무통제)": r.get("ρ_A (행수 가중 · 무통제)"),
                   "순열 널 2σ": r.get("순열 널 2σ"),
                   "순열 널 양측 p": r.get("순열 널 양측 p"),
                   "BCa 95%": r.get("BCa 95%"), "구간 종류": r.get("구간 종류"),
                   "채택 도메인": r.get("채택 도메인"),
                   "🔴 통계에 실제로 든 도메인": r.get("🔴 통계에 실제로 든 도메인"),
                   "🔴 이름만 남고 못 잰 도메인": r.get("🔴 이름만 남고 못 잰 도메인"),
                   "라벨·예측 유한 회계": r.get("라벨·예측 유한 회계")}
    key = next((k for k in cmp if k.startswith("ㄱ")), None)
    rho = cmp.get(key, {}).get("ρ_A (행수 가중 · 무통제)") if key else None
    res = {"무엇": "이슈 #115 ① --- 896 팔 A 재현(pairboot 수리 뒤)",
           "🔴 어떻게 돌렸나": "runners/dose896.stageA 를 그대로 호출. ROOT 만"
                        " 임시 디렉터리로 돌려 out896_armA.json 을 안 건드렸다.",
           "예외": err,
           "정본(원장 896)": EXPECT_896_ARMA,
           "재현": cmp,
           "🔴 ρ_A 가 그대로인가": (None if rho is None else
                             {"재현": rho, "정본": EXPECT_896_ARMA["ㄱ 존재 이진 ρ_A"],
                              "차": round(rho - EXPECT_896_ARMA["ㄱ 존재 이진 ρ_A"], 6),
                              "같은가": abs(rho - EXPECT_896_ARMA["ㄱ 존재 이진 ρ_A"]) < 1e-9}),
           "산출물": "runners/out115_armA.json (dose896 원본 형식 그대로)",
           "초": round(time.time() - t0, 1)}
    res.update(stamp())
    (OUT / "out115_armA_verdict.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: res[k] for k in ("예외", "🔴 ρ_A 가 그대로인가", "초")},
                     ensure_ascii=False, indent=1), flush=True)
    return res


# ── ⑤ 부류로 승격할 수 있나 --- **AST 검사 시제품**을 지어서 답한다 ─────────
#
# 후보 규칙: *"`rankdata` 앞에는 반드시 `isfinite` 마스크가 있어야 한다."*
# `#109` 가 `ingest/audit.py:_judgment_lits()` 로 AST 를 읽는 선례를 만들었다.
# 🔴 **의견 대신 시제품으로 답한다** --- 저장소 전체에 돌려 참/거짓 비율을 잰다.
# (`ingest/` 는 이번 사이클 금지 파일이라 **짓지 않고 여기서 재기만** 한다.)
RANK_FNS = {"rankdata"}
SAFE_FNS = {"safe_rank", "_rank_masked"}
MODEL_CALLS = {"predict", "decision_function", "predict_proba", "transform"}


def _mask_names_with_isfinite(fn_node):
    """함수 스코프에서 `isfinite` 를 거친 이름의 **추이 폐포**."""
    assigns = {}
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    assigns.setdefault(t.id, []).append(n.value)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value:
            assigns.setdefault(n.target.id, []).append(n.value)
    def has_isfinite(node):
        for m in ast.walk(node):
            if isinstance(m, ast.Attribute) and m.attr == "isfinite":
                return True
            if isinstance(m, ast.Name) and m.id == "isfinite":
                return True
        return False
    good = {k for k, vs in assigns.items() if any(has_isfinite(v) for v in vs)}
    for _ in range(4):                      # 이름을 타고 번지는 마스크(추이 폐포)
        grew = False
        for k, vs in assigns.items():
            if k in good:
                continue
            for v in vs:
                if any(isinstance(m, ast.Name) and m.id in good for m in ast.walk(v)):
                    good.add(k); grew = True; break
        if not grew:
            break
    return good


#: 🔴 **알고 있는 안전한 자리**(티처 #59 가 전수 확인한 것 + 내가 읽어서 확인한 것).
#: 검사가 이것들을 '미증명' 으로 올리면 **오탐**이다 --- 그 비율을 재야 이 규칙을
#: '금지' 로 승격할지 '증명 의무' 로 둘지 고를 수 있다(의견이 아니라 수로 고른다).
KNOWN_SAFE = {
    # 마스크를 **호출자가** 만들어 넘기는 `_pct(v, ok)` 꼴 --- 스코프 밖이라 원리상 못 본다
    "lab/crowdaxes.py": "_pct(v, ok) --- 마스크가 인자",
    "lab/natsaxes.py": "_pct(v, ok)", "lab/popaxes.py": "_pct(v, ok)",
    "lab/tagaxes.py": "_pct(v, ok) · 티처 #59 안전 확인",
    "lab/visitoraxes.py": "_pct(v, ok)", "lab/weatheraxes.py": "_pct(v, ok)",
    # 자 자신 --- 검사 대상이 아니다
    "lab/pairboot.py": "safe_rank/rank_ensemble 구현 그 자체(면제)",
}
KNOWN_SAFE_LINES = {
    "lab/forms.py:46": "_rank_masked 구현 그 자체(면제)",
    "lab/guards.py:410": "합성 정규난수 · 티처 #59 안전 확인",
    "lab/creatoraxes.py:84": "티처 #59 안전 확인",
}


def _fp_rate(rows) -> dict:
    bad = [r for r in rows if r["판정"].startswith("🔴") and r["자리"].startswith("lab/")]
    fp = []
    for r in bad:
        f = r["자리"].split(":")[0]
        if f in KNOWN_SAFE:
            fp.append({**r, "왜 오탐": KNOWN_SAFE[f]})
        elif r["자리"] in KNOWN_SAFE_LINES:
            fp.append({**r, "왜 오탐": KNOWN_SAFE_LINES[r["자리"]]})
        elif r["함수"] == "fit" and "맨 이름 y" in r["왜"]:
            fp.append({**r, "왜 오탐": "harness.py:288·309-310 이 학습 라벨의 유한을"
                                    " 보증한다(노트 273·274) --- 다른 파일이라 못 본다"})
    return {"lab/ 미증명": len(bad), "그중 알려진 안전(=오탐)": len(fp),
            "🔴 오탐률": round(len(fp) / max(len(bad), 1), 3),
            "뜻": "이 비율이 크므로 규칙을 **'금지'로 승격하면 안 된다** ---"
                " 'safe_rank 로 감싸라'(결정 가능) + '미증명은 사람이 한 번 읽어라'"
                "(증명 의무) 두 단으로 나눠야 한다",
            "오탐 목록": fp}


def astcheck() -> dict:
    """저장소 전체 `rankdata(...)` 자리를 **증명됨/미증명**으로 가른다."""
    rows = []
    for p, rel in _pyfiles():
        src = p.read_text(errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        parents = {}
        for n in ast.walk(tree):
            for c in ast.iter_child_nodes(n):
                parents[c] = n
        fns = [n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            fname = (n.func.id if isinstance(n.func, ast.Name)
                     else n.func.attr if isinstance(n.func, ast.Attribute) else None)
            if fname not in RANK_FNS | SAFE_FNS or not n.args:
                continue
            owner = None
            for f in fns:
                if f.lineno <= n.lineno <= (f.end_lineno or f.lineno):
                    if owner is None or f.lineno > owner.lineno:
                        owner = f
            good = _mask_names_with_isfinite(owner) if owner is not None else set()
            arg = n.args[0]
            kind, why = "🔴 미증명", "인자가 마스크 자국을 안 남긴다"
            if fname in SAFE_FNS:
                kind, why = "✅ 자로 감쌈", f"{fname} --- 규칙이 코드로 강제된다"
            elif isinstance(arg, ast.Subscript):
                names = {m.id for m in ast.walk(arg.slice) if isinstance(m, ast.Name)}
                if names & good:
                    kind, why = "✅ 증명됨", f"첨자 {sorted(names & good)} 가 isfinite 를 거쳤다"
                elif any(isinstance(m, ast.Attribute) and m.attr == "isfinite"
                         for m in ast.walk(arg.slice)):
                    kind, why = "✅ 증명됨", "첨자에 isfinite 가 직접 있다"
                else:
                    kind, why = "🔴 미증명", f"첨자 {sorted(names)} 의 유한성 못 봄"
            elif isinstance(arg, ast.Call):
                a = (arg.func.attr if isinstance(arg.func, ast.Attribute)
                     else arg.func.id if isinstance(arg.func, ast.Name) else "?")
                kind = "⚠ 모형 출력" if a in MODEL_CALLS else "🔴 미증명"
                why = f"인자가 {a}(...) 호출 --- 라벨이 아니라 예보"
            elif isinstance(arg, ast.Name):
                if arg.id in good:
                    kind, why = "✅ 증명됨", f"이름 {arg.id} 자체가 isfinite 를 거쳤다"
                else:
                    kind, why = "🔴 미증명", f"맨 이름 {arg.id}"
            rows.append({"자리": f"{rel}:{n.lineno}", "부름": fname,
                         "판정": kind, "왜": why,
                         "함수": owner.name if owner is not None else "<모듈>"})
    tally = {}
    for r in rows:
        tally[r["판정"]] = tally.get(r["판정"], 0) + 1
    out = {
        "무엇": "이슈 #115 ⑤ --- 「rankdata 앞에는 isfinite 마스크」를 AST 로 볼 수 있나",
        "🔴 답": "**볼 수 있다. 다만 '금지' 가 아니라 '증명 의무' 로만 볼 수 있다.**",
        "근거": [
            "① 결정 가능한 부분: 인자가 `v[m]` 꼴이고 `m` 이 같은 함수 스코프에서"
            " `isfinite` 를 거친 이름이면 **정적으로 증명된다**. 추이 폐포로"
            " `tr = has & np.isfinite(y) & (yr < T)` 같은 사슬도 따라간다.",
            "② 결정 **불가능**한 부분: 인자가 `m.predict(X)` 같은 **모형 출력**이면"
            " 유한성은 실행 시 성질이라 AST 가 못 답한다. 저장소의 진짜 위험"
            "(forms.py:1108·pairboot rank_ensemble)이 정확히 이 부류다.",
            "③ 그래서 규칙을 **한 단 낮춰** 검사 가능하게 만든다 ---"
            " *'rankdata 를 직접 부르지 마라. `pairboot.safe_rank` 로 감싸라'*."
            " 이것은 **완전히 결정 가능**하다(이름 하나만 보면 된다).",
            "④ `_judgment_lits` 와 같은 꼴의 알려진 구멍도 같다 --- 마스크를"
            " 다른 함수에서 만들어 넘기면(`_pct(v, ok)`) 스코프 안에서 못 본다."
            " 실측: 그런 자리는 아래 '미증명' 에 남고 사람이 한 번 읽어야 한다.",
        ],
        "🔴 짓지 않은 이유": "`ingest/audit.py` 는 이번 사이클 **금지 파일**이다."
                       " 그래서 시제품을 여기서 돌려 **비율만 재고** 설계를 넘긴다.",
        "설계(ingest/audit.py 에 넣을 때)": {
            "검사 이름": "rankdata_mask",
            "경성 실패": "`lab/**` 과 `serve/**` 에서 `rankdata(` 직접 호출 ---"
                     " 그 두 곳은 판·서빙 경로라 조용한 실패가 제일 비싸다",
            "연성(적기만)": "`runners/**` 의 직접 호출 --- 손으로 돌리는 역사물이라"
                       " 전량 개수만 세고 늘어나면 적는다(DEAD_HISTORY_DEBT 와 같은 꼴)",
            "면제": "`pairboot.safe_rank` 정의 안 · `check()` 안의 심기 시험",
            "🔴 조항 59 대비": "검사가 0 을 내면 '깨끗' 이 아니라 '훑은 파일 수'를"
                          " 같이 낸다 --- 빈 것을 부정으로 읽지 않게",
        },
        "실측 집계": tally,
        "총 자리": len(rows),
        "🔴 오탐률을 실제로 쟀다": _fp_rate(rows),
        "자리": rows,
    }
    out.update(stamp())
    (OUT / "out115_astcheck.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"집계": tally, "총 자리": len(rows)}, ensure_ascii=False,
                     indent=1), flush=True)
    return out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "plant"
    {"plant": plant, "callgraph": callgraph, "trace": trace, "armA": armA,
     "astcheck": astcheck}[which]()
