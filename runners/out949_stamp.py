# -*- coding: utf-8 -*-
"""노트 949 [판정] — 「도장(stamp)」과 「대조(check)」를 갈라 ㉮ 를 다시 잰다.

사전등록: ``docs/prereg_949_stampcheck.md`` (**측정 전에 커밋됐다** — `part0` 이 증언).

쓰기::

    python3 -m runners.out949_stamp --phase before   # 두 자리를 고치기 **전**
    python3 -m runners.out949_stamp --phase after    # 고친 **뒤**
    python3 -m runners.out949_stamp --phase score    # 🔴 위 둘 + ⑤′ 를 **읽어** 채점

🔴 **한 실행의 분해는 한 실행에서**(티처 #88 M2). ``score`` 는 스스로 재지 않고
**어느 산출물의 어느 키에서 왔는지**를 값마다 적는다.
"""
import argparse
import ast
import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import gitcall as gc            # noqa: E402
from lab import keyspace as ks           # noqa: E402

PREREG = "docs/prereg_949_stampcheck.md"
ME = "runners/out949_stamp.py"

#: 🔴 948 이 `--exempt` 사유로 「사전등록 P9 · 판 계산 import 0」을 **주장한** 자리 전량.
#:    출처는 커밋된 산출물이다(손 나열 금지) — 아래 `p9_ruler()` 가 그 산출물에서 읽는다.
EXEMPT_SRC = "runners/out948_fiveprime.json"
P9_CLAIM = "판 계산 import 0"

#: 판 계산 모듈로 치는 낱말(947 의 P9 와 **같은 자**를 쓴다 — 자를 갈면 채점이 안 이어진다)
BOARD_WORDS = ("board", "denominator", "verdict", "thresh")


def sha(p) -> str:
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "🔴 파일 없음"


#: 🔴 **날 것으로 git 을 부르지 않는다**(상시 조항 1 · `lab/gitcall.py` 가 정본).
#:    이 러너가 날 것을 쓰면 **자기가 세는 분모를 자기가 늘린다** ---
#:    「매 사이클 검출기를 고치면서 새것을 낳는다」의 가장 값싼 판이다.
def git_lines(*a):
    return ks.git_lines(*a, root=ROOT)


def git_paths(*a):
    return ks.git_paths(*a, root=ROOT)


def jload(rel):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ══════════════════════════════════════════ 0 · 사전등록이 측정보다 먼저였다
def part0() -> dict:
    ln = git_lines("log", "-1", "--format=%H %cI", "--", PREREG)
    c_pre = ln[0] if ln else ""
    h = c_pre.split(" ")[0] if c_pre else ""
    files = sorted(git_paths("show", "--pretty=format:", h)) if h else []
    return {
        "무엇": "0 🔴 사전등록이 **측정보다 먼저** 커밋됐다 — 기계가 증언한다",
        "사전등록": PREREG,
        "사전등록 sha256(지금 다시 계산)": sha(ROOT / PREREG),
        "사전등록만 담은 커밋": c_pre,
        "그 커밋이 담은 파일": files,
        "🔴 그 커밋에 측정 러너가 들어 있었나": ME in files,
        "측정 시작(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "통과": bool(c_pre) and (ME not in files),
    }


# ══════════════════════════════════════════ 1 · 자와 그 검정력
def part1() -> dict:
    pc = gc.plant_check_stamp()
    return {"무엇": "1 🔴 대조의 자를 못 박고 **검정력을 먼저 잰다**(말이 아니라 발화)",
            "자": gc.CHECK_CRITERIA, "심어서 확인": pc, "통과": pc["통과"]}


# ══════════════════════════════════════════ 2 · 대조 전수 + 자연 양성 대조
NATURAL = ("runners/ratio940_run.py", "docs/prereg_940_ratio.md")


def part2(chk: dict) -> dict:
    cov = chk["덮인 파일 → 그 대조 자리"]
    nat = [s for s in cov.get(NATURAL[1], []) if s.startswith(NATURAL[0])]
    return {
        "무엇": "2 🔴 커밋된 트리의 **대조** 전수 — 도장과 갈랐다",
        "훑은 `.py`(분모)": chk["🔴 훑은 `.py`(분모)"],
        "🔴 대조 자리 수": chk["🔴 대조 자리 수"],
        "🔴 대조가 덮는 파일 수": chk["🔴 대조가 덮는 파일 수"],
        "🔴 대상을 못 푼 자리 수(「모른다」)":
            chk["🔴 대상을 못 푼 자리 수(「모른다」 --- 「없다」가 아니다)"],
        "🔴 자연 양성 대조": {
            "무엇": "%s 가 %s 를 **대조**하나 — 못 잡으면 「대조 0」은 판정에 못 쓴다"
                  % NATURAL,
            "잡은 자리": nat, "🔴 잡았나": bool(nat)},
        "덮인 파일 전량": sorted(cov),
        "대조 자리": chk["대조 자리"],
        "🔴 이 자로 안 센 갈래(rev 기준 비교)":
            chk["🔴 이 자로 안 센 갈래(rev 기준 비교 · 기록된 상수와 안 견준다)"],
        "통과": bool(nat) and
                chk["🔴 대상을 못 푼 자리 수(「모른다」 --- 「없다」가 아니다)"] == 0,
    }


# ══════════════════════════════════════════ 3 · ㉮/㉯/㉲/순㉯ 를 다시 잰다
def part3(cen: dict) -> dict:
    k = "🔴 분모 ④"
    return {
        "무엇": "3 🔴 ㉮/㉯/㉲/순㉯ 를 **대조**로 다시 잰다(947 은 이름 · 948 은 도장)",
        "🔴 날 것": cen[k + " 날 것"],
        "🔴 ㉮ 원리상 못 고친다(대조 ≥ 1)":
            cen[k + "-㉮ 원리상 못 고친다(🔴 **대조** ≥ 1 · 949 가 도장에서 갈아탄 자)"],
        "⚠ 옛 자(도장 ≥ 1)로 세면 ㉮ 는":
            cen["⚠ 참고 --- 947~948 의 옛 자(도장 ≥ 1)로 세면 ㉮ 는"],
        "🔴 ㉯ 고칠 수 있다": cen[k + "-㉯ 고칠 수 있다(🔴 이 수가 0 이어야 통과)"],
        "🔴 ㉲ 규약상 안 고친다(㉯ 의 부분집합)":
            cen[k + "-㉲ 그중 규약상 안 고친다(동결 · ㉯ 의 부분집합)"],
        "🔴 순㉯ 막는 것이 아무것도 없는 것": cen[k + "-순㉯ 막는 것이 아무것도 없는 것"],
        "🔴 순㉯ 목록": sorted(
            set(cen["🔴 ㉯ 목록(㉲ 포함)"]) -
            {r["파일:줄"] for r in cen["🔴 ㉯/㉲ 목록과 사유"]
             if r["사유"].startswith("🔴 ㉯-㉲")}),
        "🔴 분해가 닫히나": {
            "날 것 + 의도적 + 안전": cen[k + " 날 것"] + cen["분모 ⑤ 의도적 날 것(음성 대조)"]
                              + cen["분모 ⑥ 안전"],
            "자 A 호출 자리": cen["🔴 분모 ② 자 A 호출 자리(경로를 내는 것만)"],
            "🔴 같은가": (cen[k + " 날 것"] + cen["분모 ⑤ 의도적 날 것(음성 대조)"]
                     + cen["분모 ⑥ 안전"]) == cen["🔴 분모 ② 자 A 호출 자리(경로를 내는 것만)"]},
        "🔴 날 것 소스 중 대조로 덮인 것":
            cen["🔴🔴 949 --- 도장/대조 가르기"]["🔴 날 것 소스 중 대조로 덮인 것"],
        "통과": cen["통과"],
    }


# ══════════════════════════════════════════ 4 · ㄱ seed_pad 가드 실측
def part4() -> dict:
    """🔴 티처 #88 C2 — `seed_pad` 가 **판정 수를 바꿨다**를 실측한다.

    948 의 커밋된 산출물에서 **그 절의 A·B 를 그대로 읽어** 두 번 센다.
    (재현이지 새 측정이 아니다 — 출처를 키까지 적는다.)
    """
    d = jload("runners/out948_fiveprime.json") or {}
    sec = d.get("1 소비자 역참조", {})
    A = set(sec.get("역참조 소비자(전량)", []))
    B = set(sec.get("돌렸다", []))
    seed = gc.CONTROL_SEED
    fired, err = False, ""
    try:
        gc.diff62("A", A, "B", B, probe=ks.octal_escape, seed_pad=seed)
    except gc.SeedPadError as e:
        fired, err = True, str(e)[:300]
    #: 음성 대조 — 양쪽에 다 없는 원소로는 **안 터져야** 한다
    neg = False
    try:
        gc.diff62("A", A, "B", B, probe=ks.octal_escape, seed_pad="lab/없는파일_949.py")
    except gc.SeedPadError:
        neg = True
    return {
        "무엇": "4 🔴 ㄱ `seed_pad` 가 판정 수를 바꾼다 — 가드가 잡나(티처 #88 C2)",
        "출처": "runners/out948_fiveprime.json › `1 소비자 역참조` › "
              "`역참조 소비자(전량)` · `돌렸다`",
        "대조 원소": seed,
        "|A| 역참조 소비자": len(A), "|B| 돌렸다": len(B),
        "🔴 원소가 A−B 에 있나": seed in (A - B),
        "🔴 가드가 발화했나": fired, "예외 문안": err,
        "🔴 음성 대조(양쪽에 없는 원소로는 안 터진다)": {"발화했나": neg, "0 이어야 한다": not neg},
        "🔴 948 이 공표한 `A−B`": sec.get("🔴 조항 62 ㉠ 안 돌린 것(= 소비자 − 돌린 것)",
                                  {}).get("🔴 A − B"),
        "🔴 대조 원소를 안 넣고 세면 `A−B`": len(A - B),
        "🔴 948 이 공표한 `분모 ④ 안 돌린 수`": sec.get("🔴 분모 ④ 안 돌린 수"),
        "🔴 차": (len(A - B) - sec.get("🔴 조항 62 ㉠ 안 돌린 것(= 소비자 − 돌린 것)",
                                    {}).get("🔴 A − B", 0)),
        "통과": fired and (not neg),
    }


# ══════════════════════════════════════════ 5 · ㄷ `--exempt` 사유에 자를 붙인다
def board_imports(rels) -> dict:
    """🔴 947 의 P9 와 **같은 자**: 이 `.py` 가 판 계산 모듈을 import 하나."""
    out = {}
    for rel in rels:
        p = ROOT / rel
        if not p.exists():
            out[rel] = "🔴 파일 없음(「import 0」이 아니다 — 조항 59)"
            continue
        try:
            t = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, OSError) as e:
            out[rel] = "🔴 못 읽었다: %s" % type(e).__name__
            continue
        mods = []
        for n in ast.walk(t):
            names = ([a.name for a in n.names] if isinstance(n, ast.Import) else
                     ([n.module] if isinstance(n, ast.ImportFrom) and n.module else []))
            mods += [m for m in names if any(w in m for w in BOARD_WORDS)]
        out[rel] = sorted(set(mods))
    return out


def part5() -> dict:
    d = jload(EXEMPT_SRC) or {}
    #: 🔴 **자리(= 절 × 파일)** 로 센다. 파일로만 세면 두 절에 같이 걸린 것이 하나로 눌린다
    #:    --- 사전등록의 낱말이 「자리」다. 두 수를 **둘 다** 싣는다(조항 60).
    spots, claim = [], set()
    for sec in ("1 소비자 역참조", "2 게이트"):
        for k, v in (d.get(sec, {}).get("안 돌린 .py 의 사유")
                     or d.get(sec, {}).get("안 돌린 사유") or {}).items():
            if P9_CLAIM in v:
                spots.append("%s › %s" % (sec, k))
                claim.add(k)
    got = board_imports(sorted(claim))
    bad = {k: v for k, v in got.items() if v}
    return {
        "무엇": "5 🔴 ㄷ `--exempt` 사유에 **자**를 붙인다 — 「판 계산 import 0」을 "
              "**이 실행 안에서** 잰다(티처 #88 M5: 948 은 안 돌렸다)",
        "출처": "%s › 두 절의 사유 문자열에 `%s` 가 있는 자리" % (EXEMPT_SRC, P9_CLAIM),
        "🔴 그 사유를 주장한 자리 수": len(spots),
        "⚠ 자리를 파일로 눌러 세면": len(claim),
        "그 자리": spots,
        "그 파일": sorted(claim),
        "파일별 판 계산 모듈 import": got,
        "🔴 판 계산 모듈을 import 한 파일": bad or "없음",
        "자": "AST · `Import`/`ImportFrom` 의 모듈명에 %s 가 들어가나" % (BOARD_WORDS,),
        "⚠ 948 은 이 검사를 이 사이클에 안 돌렸다": "티처 #88 M5 — 사유의 유일한 근거가 "
                                    "**남의 사이클 예측을 잘못 가리키는 문자열**이었다",
        "통과": bool(spots) and not bad,
    }


# ══════════════════════════════════════════ 6 · P11 이 사이클은 판을 안 건드린다
def part6(base: str) -> dict:
    changed = sorted(git_paths("diff", "%s..HEAD" % base))
    dirty = [x[3:] for x in sorted(git_paths("status", "--porcelain")) if x.strip()]
    mine = sorted({p for p in changed + dirty if p.endswith(".py")})
    got = board_imports(mine)
    bad = {k: v for k, v in got.items() if v}
    return {
        "무엇": "6 🔴 P11 이 사이클은 판 ρ 를 안 건드린다 — **이 실행 안에서** AST 로 잰다",
        "기준(base)": base,
        "이 사이클이 만진 `.py`": mine,
        "파일별 판 계산 모듈 import": got,
        "🔴 판 계산 모듈 import 수": sum(len(v) for v in got.values() if isinstance(v, list)),
        "⚠ 자 정본(안 움직였다)": "판 ρ 0.47034 ± 0.0021(SD) · SE 0.00060 · 12도메인 · "
                        "유보 3,775 · 채택 문턱 0.00353",
        "통과": not bad,
    }


# ══════════════════════════════════════════ 7 · 낱말 증식(M7) 진단
WORDS = ("조항 61", "조항 62", "㉮", "㉯", "㉲", "도장", "대조")


def part7(base: str) -> dict:
    rows = {}
    for w in WORDS:
        a = gc.grep_files([w], root=ROOT, tree=base, pathspec=("*.py",))
        b = gc.grep_files([w], root=ROOT, pathspec=("*.py",))
        rows[w] = {"파일 수(%s)" % base: len(a), "파일 수(작업 트리)": len(b),
                   "차": len(b) - len(a)}
    return {
        "무엇": "7 🔴 낱말 증식 진단(티처 #87 M7 · #88 「안 쟀다」 ③) — 이번엔 **잰다**",
        "자": "`git grep -c -F <낱말> -- '*.py'` 의 **파일 수**(줄 수가 아니다 · 규약 60)",
        "낱말별": rows,
        "⚠": "판정에 안 쓴다 — **재고 적는 것**이 이 절의 일이다",
        "통과": True,
    }


# ══════════════════════════════════════════ main
def measure(phase: str, base: str) -> dict:
    t0 = time.time()
    st = {"무엇": "노트 949 [판정] — 도장과 대조를 갈라 ㉮ 를 다시 잰다",
          "국면": phase,
          "시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
          "🔴 코드 sha256(이게 자다)": {c: sha(ROOT / c) for c in
                                (ME, "lab/gitcall.py", "lab/keyspace.py")},
          "🔴 사전등록 sha256": sha(ROOT / PREREG)}
    chk = gc.checkers()
    cen = gc.census(harm=False, chk=chk)
    res = dict(st)
    res["0 사전등록"] = part0()
    res["1 자와 검정력"] = part1()
    res["2 대조 전수"] = part2(chk)
    res["3 ㉮/㉯/㉲/순㉯"] = part3(cen)
    res["4 ㄱ seed_pad 가드"] = part4()
    res["5 ㄷ --exempt 사유의 자"] = part5()
    res["6 P11 판 불변"] = part6(base)
    res["7 낱말 증식"] = part7(base)
    res["⚠ census 전문"] = cen
    secs = [k for k, v in res.items() if isinstance(v, dict) and "통과" in v]
    res["🔴 절 수(분모)"] = len(secs)
    res["🔴 실패한 절"] = [k for k in secs if res[k]["통과"] is False] or "없음"
    res["통과"] = all(res[k]["통과"] for k in secs)
    res["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    res["초"] = round(time.time() - t0, 1)
    return res


def _p(rows, name, pred, got, ok, src):
    rows[name] = {"예측(본문 그대로)": pred, "실측": got, "🔴 맞았나": bool(ok),
                  "🔴 어느 실행에서 왔나": src}


def score() -> dict:
    """🔴 사전등록 P1~P12 채점 — **스스로 재지 않고 산출물을 읽는다**(M2)."""
    bef = jload("runners/out949_stamp_before.json")
    aft = jload("runners/out949_stamp_after.json")
    fp = jload("runners/out949_fiveprime.json")
    rows: dict = {}
    B, A = "out949_stamp_before.json", "out949_stamp_after.json"
    b1, b2, b3 = bef["1 자와 검정력"], bef["2 대조 전수"], bef["3 ㉮/㉯/㉲/순㉯"]
    pc = b1["심어서 확인"]
    _p(rows, "P1 심은 양성 3/3 · 음성 0/2",
       "3/3 · 0/2",
       "%d/3 · 오발 %d" % (pc["🔴 양성 중 잡은 수"], pc["🔴 음성 오발 수"]),
       pc["🔴 양성 중 잡은 수"] == 3 and pc["🔴 음성 오발 수"] == 0, B)
    _p(rows, "P2 자연 양성이 잡히고 덮인 파일 ≥ 10",
       "ratio940_run.py 가 prereg_940_ratio.md 를 대조 = 참 · 덮인 파일 ≥ 10",
       "잡았나=%s · 덮인 파일 %d" % (b2["🔴 자연 양성 대조"]["🔴 잡았나"],
                              b2["🔴 대조가 덮는 파일 수"]),
       b2["🔴 자연 양성 대조"]["🔴 잡았나"] and b2["🔴 대조가 덮는 파일 수"] >= 10, B)
    _p(rows, "P3 날 것 15 중 대조로 덮인 것 0 → ㉮ = 0",
       "날 것 15 · ㉮ 0",
       "날 것 %d · ㉮ %d · 덮인 날 것 %s" % (b3["🔴 날 것"],
                                     b3["🔴 ㉮ 원리상 못 고친다(대조 ≥ 1)"],
                                     b3["🔴 날 것 소스 중 대조로 덮인 것"]),
       b3["🔴 날 것"] == 15 and b3["🔴 ㉮ 원리상 못 고친다(대조 ≥ 1)"] == 0, B)
    _p(rows, "P4 ㉯ 15 · ㉲ 13 · 순㉯ 2",
       "㉯ 15 · ㉲ 13 · 순㉯ 2",
       "㉯ %d · ㉲ %d · 순㉯ %d" % (b3["🔴 ㉯ 고칠 수 있다"],
                              b3["🔴 ㉲ 규약상 안 고친다(㉯ 의 부분집합)"],
                              b3["🔴 순㉯ 막는 것이 아무것도 없는 것"]),
       (b3["🔴 ㉯ 고칠 수 있다"], b3["🔴 ㉲ 규약상 안 고친다(㉯ 의 부분집합)"],
        b3["🔴 순㉯ 막는 것이 아무것도 없는 것"]) == (15, 13, 2), B)
    want5 = ["runners/gate940_wiring.py:252", "runners/ratio940_run.py:77"]
    _p(rows, "P5 순㉯ 둘의 파일:줄", " · ".join(want5), b3["🔴 순㉯ 목록"],
       sorted(b3["🔴 순㉯ 목록"]) == sorted(want5), B)
    a3 = aft["3 ㉮/㉯/㉲/순㉯"]
    _p(rows, "P6 고친 뒤 날 것 13 · ㉮ 0 · ㉯ 13 · ㉲ 13 · 순㉯ 0",
       "13 · 0 · 13 · 13 · 0",
       "%d · %d · %d · %d · %d" % (a3["🔴 날 것"],
                                   a3["🔴 ㉮ 원리상 못 고친다(대조 ≥ 1)"],
                                   a3["🔴 ㉯ 고칠 수 있다"],
                                   a3["🔴 ㉲ 규약상 안 고친다(㉯ 의 부분집합)"],
                                   a3["🔴 순㉯ 막는 것이 아무것도 없는 것"]),
       (a3["🔴 날 것"], a3["🔴 ㉮ 원리상 못 고친다(대조 ≥ 1)"], a3["🔴 ㉯ 고칠 수 있다"],
        a3["🔴 ㉲ 규약상 안 고친다(㉯ 의 부분집합)"],
        a3["🔴 순㉯ 막는 것이 아무것도 없는 것"]) == (13, 0, 13, 13, 0), A)
    g = bef["4 ㄱ seed_pad 가드"]
    #: 🔴 **첫 판의 자가 약했다 — 스스로 적발한다.** 「발화 자리 수」를 `bool` 하나로
    #:    세면 언제나 1 이 나온다(조항 60: 자를 먼저 적어라). 진짜 자는 **오늘 실행의
    #:    산출물에서 그 표지를 세는 것**이다. 두 수를 **둘 다** 싣고 **엄한 쪽으로 채점한다**.
    seedkey = "🔴🔴 대조 원소를 못 심었다(949 · 티처 #88 C2)"
    def _count(o):
        n = 0
        if isinstance(o, dict):
            for k, v in o.items():
                n += (1 if k == seedkey else 0) + _count(v)
        elif isinstance(o, list):
            for v in o:
                n += _count(v)
        return n
    today = _count(fp) if fp else None
    old948 = 1 if g["🔴 가드가 발화했나"] else 0
    _p(rows, "P7 가드가 정확히 1 자리에서 발화 · 948 의 A−B 가 참값보다 1 작았다",
       "발화 자리 1 · 차 1",
       {"🔴 오늘 ⑤′ 산출물에서 센 발화 자리": today,
        "⚠ 948 의 네 호출 자리 중에서 세면": old948,
        "🔴 왜 다른가": ("949 가 `seed_pad` 를 넘기는 호출 자리를 **둘 더 만들었다** "
                    "(절 1 의 ㉡′ · `1-라`). 예측의 「1」은 **948 의 자리**를 보고 쓴 수다 "
                    "--- 오늘 실행으로 채점하면 %s 다" % today),
        "차(948 공표 %s · 참값 %s)" % (g["🔴 948 이 공표한 `A−B`"],
                                 g["🔴 대조 원소를 안 넣고 세면 `A−B`"]): g["🔴 차"]},
       (today == 1) and g["🔴 차"] == 1,
       "%s + out949_fiveprime.json" % B)
    if fp:
        ra = fp.get("1-라 🔴 `_grep_l` 건초더미 대조(947)", {})
        _p(rows, "P8 `1-라` 를 조항 62 와 AND 로 엮으면 False",
           "False", ra.get("통과"), ra.get("통과") is False, "out949_fiveprime.json")
        g2 = fp.get("2 게이트", {}).get("🔴 조항 62 ㉡ 자를 통과한 사유만 B 로(949)", {})
        _p(rows, "P10 절 2 ㉡ 의 자를 바꾸면 A−B > 0",
           "> 0", g2.get("🔴 A − B"),
           isinstance(g2.get("🔴 A − B"), int) and g2["🔴 A − B"] > 0,
           "out949_fiveprime.json")
        fail = fp.get("🔴 실패한 절")
        n = len(fail) if isinstance(fail, list) else 0
        _p(rows, "P12 ⑤′ 실패 절 수 > 2", "> 2", "%d (%s)" % (n, fail), n > 2,
           "out949_fiveprime.json")
    else:
        for k in ("P8 `1-라` 를 조항 62 와 AND 로 엮으면 False",
                  "P10 절 2 ㉡ 의 자를 바꾸면 A−B > 0", "P12 ⑤′ 실패 절 수 > 2"):
            rows[k] = {"🔴 안 쟀다": "⑤′ 산출물(`runners/out949_fiveprime.json`)이 없다 "
                               "--- 「빗맞혔다」가 아니라 **못 쟀다**(조항 59)",
                       "🔴 맞았나": None, "🔴 어느 실행에서 왔나": "없음"}
    p5 = aft["5 ㄷ --exempt 사유의 자"]
    _p(rows, "P9 「판 계산 import 0」 주장 18 자리를 이 실행 안에서 재어 참",
       "18 자리 · import 0",
       "%d 자리 · import 한 파일 %s" % (p5["🔴 그 사유를 주장한 자리 수"],
                                  p5["🔴 판 계산 모듈을 import 한 파일"]),
       p5["🔴 그 사유를 주장한 자리 수"] == 18 and p5["통과"], A)
    p6 = aft["6 P11 판 불변"]
    _p(rows, "P11 이 사이클이 만진 `.py` 의 판 계산 import 0",
       "0", p6["🔴 판 계산 모듈 import 수"], p6["🔴 판 계산 모듈 import 수"] == 0, A)
    hit = [k for k, v in rows.items() if v.get("🔴 맞았나") is True]
    miss = [k for k, v in rows.items() if v.get("🔴 맞았나") is False]
    nm = [k for k, v in rows.items() if v.get("🔴 맞았나") is None]
    return {
        "무엇": "🔴 사전등록 949 채점 — **본문 상수 그대로**(티처 #88 M7)",
        "🔴 채점 규칙(사전등록 §3 에 **먼저** 적었다)":
            "각 예측은 사전등록 본문의 상수 그대로 채점한다. 본문과 반증 조항이 어긋나면 "
            "**본문을 쓴다**. 못 맞히면 **「빗맞혔다」로 적는다**. 측정 뒤에 예측을 안 고친다",
        "사전등록 sha256(지금 다시 계산)": sha(ROOT / PREREG),
        "🔴 분모": len(rows), "🔴 맞았다": len(hit), "🔴 빗맞혔다": len(miss),
        "🔴 못 쟀다(「빗맞혔다」가 아니다 · 조항 59)": nm or "없음",
        "🔴 빗맞힌 것": miss or "없음",
        "예측별": rows,
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "통과": not miss,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("before", "after", "score"), required=True)
    ap.add_argument("--base", default="87d53a34a")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = ROOT / (a.out or ("runners/out949_%s.json" %
                            ("score" if a.phase == "score" else "stamp_" + a.phase)))
    if out.exists():                     # 🔴 옛 산출물을 새 결과로 읽는 사고가 두 번 있었다
        out.unlink()
    res = score() if a.phase == "score" else measure(a.phase, a.base)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("산출물: %s · 통과 %s" % (out, res.get("통과")))


if __name__ == "__main__":
    main()
