# -*- coding: utf-8 -*-
"""이슈 #123 (티처 #61 C1·C7) — **씨앗0 상수 게이트 전수 확인. 그리고 규칙을 기계로 박는다.**

## 무엇이 났나

노트 898 이 판 정본을 옮겼다(`state/rank_test.spearman` 서수 순위 → 동률 평균).
그런데 **씨앗0 상수는 아무도 안 옮겼다.** 그래서 다섯 자리가 조용히 죽었다 ---
`dose896.py` 의 판정 게이트는 **영구 False**, `nanfix115.py` 의 *"회귀 증거 ·
조항 59"* 라 적힌 줄도 **영구 False**, 그리고 정본을 만든 러너 둘
(`board898.py`·`wire898.py`)은 옛 구현을 **반입**해 쓰는 바람에 **자기 자신을
다시 못 돌리게** 됐다. 같은 사이클의 `thr898.py:41-43` 은 같은 함정을 알고
피했다 --- 한 파일에선 피하고 두 파일에선 밟았다.

## 🔴 그래서 박는 규칙 (지금까지 저장소에 이 규칙이 **없었다**)

    ① 정본(채점 함수 · 채점 배치 · 적합 경로)이 옮겨가면 **씨앗0 상수도 같이 옮긴다.**
    ② 옛 정본을 계속 재야 하는 러너는 **옛 구현을 파일 안에 박는다 --- 반입 금지.**
       (`thr898.py:41-43` 이 그렇게 살아남았다)
    ③ 두 길뿐이다. 아무것도 안 하는 셋째 길이 **「영구 False 게이트」** 다.

이 파일이 그 규칙의 **집행자**다. 규칙을 산문으로만 적으면 다음 사이클이 또
밟는다(898 이 정확히 그랬다 --- 규약을 인용하면서 규약을 어긴 커밋이 이 저장소에
둘 있다).

## 어떻게 집행하나

    정적(적합 0회)  은퇴값 문자열을 저장소 전체에서 훑어 **자리마다 허가 사유**를
                    요구한다. 사유 없는 자리 = 실패. 그리고 「옛 값을 이고 있으면서
                    `state.rank_test` 를 반입」하는 파일은 **AST 로** 잡는다(②).
    동적(full)      게이트 셋을 **실제로 돌려서** True 를 내는지 본다(조항 59 ---
                    고쳤다고 되는 게 아니다). 이력 산출물은 하나도 안 덮는다.

사용:
    python3 runners/out899a_gates.py          # 정적만 (초 단위)
    python3 runners/out899a_gates.py full     # 정적 + 동적 (적합 2회 · 30분쯤)
    python3 runners/out899a_gates.py reuse    # 정적 + **이미 남긴 동적 산출물을 읽어서**
                                              #   다시 판정(적합 0회). 🔴 다시 재는 것이
                                              #   아니라 **읽는** 것이라 그렇게 적는다.

산출물: `runners/out899a_gates.json`
  곁딸린 증거 --- `out899a_dose896_step0.json` · `out899a_verdict112.json` ·
  `out899a_nanfix115_trace.json` · `out898_board.899a.json` · `out898_wire.899a.json`
  (뒤의 둘은 `OUT898_TAG=899a` 로 돌린 재현본이다. 이력 산출물은 하나도 안 덮었다.)
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import ast                                                      # noqa: E402
import datetime as dt                                           # noqa: E402
import hashlib                                                  # noqa: E402
import json                                                     # noqa: E402
import shutil                                                   # noqa: E402
import subprocess                                               # noqa: E402
import sys                                                      # noqa: E402
import tempfile                                                 # noqa: E402
import time                                                     # noqa: E402
from pathlib import Path                                        # noqa: E402

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out899a_gates.json"

#: 🔴 **은퇴값 --- 898 이전(서수 순위) 챔피언의 씨앗0.**
#: 여기 한 번만 적는다. 이 파일이 검출기라 검출기 자신은 예외다(티처 #49 C1 이
#: *"검출기가 옛 값을 이고 있었다"* 로 잡은 그 병을 피하려고 **한 자리**로 묶는다).
RETIRED = "0.4724867181663707"

#: 🔴 **산 값은 손으로 안 적는다** --- `dose896` 한 자리에서 읽어 온다(규칙 ①의 정본).
from dose896 import EXPECT_POOLED_K1_S0 as LIVE   # noqa: E402
LIVE_S = repr(LIVE)

#: 은퇴값을 이고 있어도 되는 자리 --- **사유 없이는 못 있는다.**
#: 갈래: `옛구현` 옛 값을 재는 러너(②를 지켜야 한다) · `동결` 얼어붙은 산출물과의
#: 대조라 옮기면 오히려 부러진다 · `산문` 게이트가 아닌 딱지 · `이력` 지난 판정의 기록.
ALLOW = {
    # 🔴 노트 899 ⑤′ --- 이 둘은 **취합 커밋 df441d272 자신이 만든 자리**다.
    # 집행자가 그 자리를 옳게 붉게 만들었다(티처 #62 M7): 체크박스 ④(죽은 값 등록)를
    # 지킨 행위가 체크박스 ②(집행자)를 깨뜨렸다. **그것이 이 집행자가 하라고 만든 일이다.**
    # 사유를 달아 닫되, **닫는 행위 자체가 기록으로 남게** 여기 적는다.
    "ingest/audit.py": ("등록",
        "죽은 숫자 표 자신. 은퇴값을 **등록하려면 그 값을 적어야 한다** --- "
        "검출기가 자기가 잡는 수를 이고 있는 것은 구조상 불가피하다. "
        "⚠ 티처 #62 C4: 여기 적힌 것은 `...707` 이고 **오늘 board898 이 내는 값은 `...708`** 이다. "
        "끝자리가 다른 짝은 아직 등록 안 됐다 --- 이슈 #133"),
    "paper/steps/477_cancel/meta.json": ("errata",
        "발행물의 errata. 본문 77행이 은퇴값을 인쇄하므로 errata 가 그 수를 **인용해야** "
        "무엇이 왜 은퇴했는지 적을 수 있다. 본문은 안 고친다(발행물 개작 금지)"),
    "runners/thr898.py": ("옛구현",
        "팔 A(서수) 문턱을 재는 러너. 같은 사이클에서 **유일하게** 함정을 피했다 "
        "--- :41-43 이 옛 서수 구현을 파일 안에 박아 뒀다"),
    "runners/board898.py": ("옛구현",
        "노트 898 2단계 측정. 팔 A = 898 이전 챔피언. 이슈 #123 으로 "
        "`rt_spearman_old` 를 박아 재현성 복구"),
    "runners/wire898.py": ("옛구현",
        "노트 898 0단계 배선 검사. ㄷ 의 네 조합 중 둘이 옛 서수 구현이다. "
        "이슈 #123 으로 `rt_spearman_old` 를 박아 재현성 복구"),
    "runners/verdict112.py": ("동결",
        "`out112_board.json`(동결 산출물)의 씨앗0 과 견준다 --- 오늘 다시 적합하지 "
        "않으므로 **옮기면 부러진다**. 다섯 자리 중 유일한 ⓑ"),
    "runners/dose896.py": ("이력",
        "은퇴값을 산 값 옆에 **같이** 적어 「언제부터 False 였나」를 세게 한다 "
        "(게이트 자체는 `EXPECT_POOLED_K1_S0` = 산 값으로 옮겼다)"),
    "runners/nanfix115.py": ("이력",
        "게이트는 `dose896.EXPECT_POOLED_K1_S0` 를 **읽어서** 쓴다. 여기 남은 것은 "
        "대조용 은퇴값 하나"),
    "runners/emul112.py": ("산문",
        "게이트가 아니라 산문. 결론(「중립화가 무연산」)은 두 판 어느 쪽으로 재도 참"),
    "runners/out899a_gates.py": ("검출기",
        "이 파일. 은퇴값을 한 자리(`RETIRED`)에만 둔다"),
    # ── 이미 규칙 ①을 지킨 자리(다른 세션이 이름에 「서수시대」를 박아 뒀다) ──
    "runners/ruler890.py": ("이력",
        "`:93 EXPECT_POOLED_K1_S0_서수시대` --- 이름에 시대를 박아 뒀다. 규칙 ①을 "
        "이미 지킨 자리다(이 파일은 899a 의 금지 파일이라 읽기만 했다)"),
    "runners/condperm841.py": ("이력",
        "`:159 BOARD_RHO_SEED0_서수시대` + *「판정에 쓰지 마라」* --- 규칙 ①을 이미 "
        "지켰다(899a 의 금지 파일)"),
    # ── 동결 산출물·로그 ──
    "runners/out112_verdict.json": ("이력", "#112 판정의 동결 산출물"),
    "runners/out898_board.json": ("이력", "노트 898 판정의 동결 산출물"),
    "runners/out898_wire.json": ("이력", "노트 898 배선 검사의 동결 산출물"),
    "runners/out898_thr.json": ("이력", "노트 898 문턱 측정의 동결 산출물"),
    "runners/out898_confirm.json": ("이력", "노트 898 확인 산출물 --- 자기 필드 이름이 "
                                          "이미 `옛 서수 값(이력)` 이다"),
    "runners/out898_confirm.txt": ("이력", "위의 사람용 사본"),
    "runners/out112_board.json": ("이력", "#112 판 재측정의 동결 산출물"),
    "runners/out896_step0.json": ("이력", "노트 896 0단계의 동결 산출물"),
    "runners/out115_trace.json": ("이력", "이슈 #115 추적의 동결 산출물"),
    "runners/out890_ruler.json": ("이력", "노트 890 자의 동결 산출물"),
    "runners/out892_floor.json": ("이력", "노트 892 잡음 바닥의 동결 산출물"),
    "runners/out888_speck.json": ("이력", "노트 888 의 동결 산출물"),
    "runners/out890_log.txt": ("이력", "실행 로그"),
    "runners/out112_board.log": ("이력", "실행 로그"),
    "runners/out112_emul837.log": ("이력", "실행 로그"),
    "runners/out898_wire.log": ("이력", "실행 로그"),
    "data/lab/denominator.json": ("이력", "대장 --- 역사이므로 죽은 수가 남는 것이 옳다"),
    "docs/prereg_898_oneruler.md": ("이력",
        "사전등록은 정의상 얼어붙은 기록이다(`ingest/audit.py:705-713`)"),
    # ── 🔴 미결: 딱지가 낡았는데 내 소유가 아니다. **통과로 세지 않는다.** ──
    "docs/용어.md": ("🔴미결",
        ":44 가 *「챔피언은 `state/rank_test.py:44` 의 `argsort(argsort)`(서수)」* 라고 "
        "**현재형으로** 적는다 --- 노트 898 이 바꾼 뒤라 틀렸다. 🔴 `docs/**` 는 "
        "LIVE_GLOBS 의 **산 문서**다(`ingest/audit.py:715`). 899a 의 금지 파일이라 "
        "손대지 않았다 --- 이슈 #123 보고서로 넘긴다"),
    "runners/refit112.py": ("🔴미결",
        ":11 이 은퇴값에 **`(챔피언)`** 딱지를 단다. 898 이후로는 「898 이전 챔피언」이 "
        "맞다. 899a 소유 파일이 아니라 손대지 않았다"),
    "runners/text680.py": ("🔴미결",
        ":55 는 딱지가 옳다(*「이력(서수 시대 · 판정에 쓰지 마라)」*). 🔴 다만 그 위 :54 가 "
        "적은 **오늘 씨앗0 `0.4731063028988083` 이 이 파일의 `EXPECT_POOLED_K1_S0`("
        "`0.4731063028988084`)와 1 ULP 다르다** --- 같은 수인데 **누적 순서가 다르다**"
        "(board898 의 자체 누적 대 `Data.pooled`). `==` 게이트를 세우는 쪽은 어느 "
        "경로에서 나온 값인지 적어야 한다. 899a 소유 파일이 아니라 손대지 않았다"),
}

#: `옛구현` 갈래가 반드시 지켜야 하는 것 --- ② 의 기계 판본.
FORBIDDEN_IMPORT = "state.rank_test"

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
SCAN_SUFFIX = {".py", ".json", ".md", ".html", ".txt", ".log", ".jsonl"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def stamp() -> dict:
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    return {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git HEAD": head,
            "이 파일 sha256": sha(Path(__file__).resolve())}


# ── 정적: 은퇴값 전수 훑기 ──────────────────────────────────────────────────
def scan() -> dict:
    hits, unlisted = {}, []
    scanned = 0
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in SCAN_SUFFIX:
            continue
        if any(d in SKIP_DIRS for d in p.parts):
            continue
        try:
            txt = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        if RETIRED not in txt:
            continue
        rel = str(p.relative_to(ROOT))
        lines = [i + 1 for i, ln in enumerate(txt.splitlines()) if RETIRED in ln]
        kind, why = ALLOW.get(rel, (None, None))
        if kind is None and rel.startswith("runners/out899a_"):
            kind, why = "검출기", "이 검사기 자신의 산출물"
        if kind is None and ".899a." in rel:
            kind, why = "검출기", ("`OUT898_TAG=899a` 재현본 --- 이력 산출물을 안 덮으려고 "
                                "꼬리표를 붙여 따로 썼다(이슈 #123)")
        hits[rel] = {"줄": lines, "갈래": kind, "사유": why}
        if kind is None:
            unlisted.append(rel)
    pend = sorted(k for k, v in hits.items() if v["갈래"] == "🔴미결")
    return {"훑은 파일": scanned,
            "은퇴값을 이고 있는 파일 수": len(hits),
            "🔴 다섯이 아니라 이만큼이다": len(hits),
            "은퇴값을 이고 있는 파일": hits,
            "🔴 허가 없는 자리": unlisted,
            "🔴 미결(딴 소유 · 통과로 안 센다)": pend}


def imports_rank_test(path: Path) -> list:
    """AST 로 `state.rank_test` 반입을 잡는다(문자열 매칭이 아니다 --- 주석은 봐준다)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    found = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module and \
                n.module.replace("runners.", "") == FORBIDDEN_IMPORT:
            found.append(f"{n.lineno}: from {n.module} import "
                         + ", ".join(a.name for a in n.names))
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.replace("runners.", "") == FORBIDDEN_IMPORT:
                    found.append(f"{n.lineno}: import {a.name}")
    return found


def rule2(hits: dict) -> dict:
    """② **옛 값을 이고 있으면서 `state.rank_test` 를 반입하면 안 된다.**

    이것이 C1 의 기계 판본이다. `board898.py` 초판이 정확히 이 꼴이었다.
    """
    rows, bad = {}, []
    #: 🔴 hits 만 돌면 **`thr898.py` 가 빠진다** --- 그 파일은 상수를 안 이고
    #: 옛 *구현*만 이고 있기 때문이다. 그런데 ②를 처음 지킨 자리가 바로 거기다.
    #: 그래서 `ALLOW` 의 `옛구현` 전량을 돈다(허가 목록이 곧 검사 목록이다).
    targets = sorted({k for k, v in ALLOW.items() if v[0] == "옛구현"}
                     | {k for k, v in hits.items() if v["갈래"] == "옛구현"})
    for rel in targets:
        p = ROOT / rel
        if not p.exists():
            rows[rel] = {"🔴": "파일이 없다"}
            bad.append(rel)
            continue
        imp = imports_rank_test(p)
        txt = p.read_text(encoding="utf-8")
        inline = ("argsort(np.argsort" in txt) or ("argsort(np.argsort(" in txt)
        rows[rel] = {"반입": imp, "옛 구현을 파일에 박았나": inline,
                     "통과": (not imp) and inline}
        if not rows[rel]["통과"]:
            bad.append(rel)
    return {"검사": "옛 값을 재는 러너는 옛 구현을 박고 state.rank_test 를 반입하지 않는다",
            "자리": rows, "🔴 위반": bad}


# ── 동적 ①: 오늘 챔피언 경로 씨앗0 (dose896.stage0 을 그대로) ───────────────
def _dose_gate(got: dict, how: str) -> dict:
    return {"어떻게": how,
            "오늘 챔피언 경로 씨앗0": repr(got["챔피언 씨앗0 판"]),
            "EXPECT_POOLED_K1_S0": repr(LIVE),
            "🔴 부동소수 완전 일치": got["🔴 부동소수 완전 일치"],
            # 🔴 노트 899 ⑤′ --- 취합 커밋이 `dose896.py:397` 의 키 이름을 바꾸고
            # 이 소비자를 안 고쳐 여기서 KeyError 로 죽었다(티처 #62 C3).
            # 이름을 다시 손으로 맞추는 대신 **접두사로 찾는다** --- 같은 병이 또 나면
            # 이름이 아니라 **구조**가 바뀐 것이고, 그때는 걸리는 게 옳다.
            "은퇴값과의 차": next(
                (v for k, v in got.items() if k.startswith("은퇴값") and "차" in k),
                None),
            "산출물": "runners/out899a_dose896_step0.json"}


def reuse_dose896_stage0() -> dict:
    p = ROOT / "runners/out899a_dose896_step0.json"
    if not p.exists():
        return {"🔴 실패": f"{p.name} 이 없다 --- `full` 로 한 번은 돌려야 한다"}
    return _dose_gate(json.loads(p.read_text())["배선"], "이미 남긴 산출물을 읽었다(적합 0회)")


def run_dose896_stage0() -> dict:
    """`dose896.stage0` 을 **그대로** 부른다. `ROOT` 만 임시로 돌려 이력을 안 덮는다
    (`nanfix115.armA` 가 쓴 방식 그대로)."""
    import dose896 as D
    tmp = Path(tempfile.mkdtemp(prefix="out899a_dose_"))
    (tmp / "runners").mkdir()
    # stage0 이 ROOT 아래에서 읽는 입력 하나
    shutil.copy(ROOT / "runners/out895_truth.json", tmp / "runners/out895_truth.json")
    real_root, real_stamp = D.ROOT, D.stamp
    D.ROOT = tmp
    D.stamp = lambda: {**stamp(), "재현": "dose896.stage0 (ROOT 만 임시)"}
    err = None
    try:
        D.stage0()
    except Exception as e:                                  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"
    finally:
        D.ROOT, D.stamp = real_root, real_stamp
    src = tmp / "runners/out896_step0.json"
    if not src.exists():
        shutil.rmtree(tmp, ignore_errors=True)
        return {"🔴 실패": err or "산출물이 안 생겼다"}
    got = json.loads(src.read_text())["배선"]
    shutil.copy(src, ROOT / "runners/out899a_dose896_step0.json")
    shutil.rmtree(tmp, ignore_errors=True)
    return {"예외": err, **_dose_gate(got, "dose896.stage0 을 실제로 돌렸다(적합 1회)")}


# ── 동적 ②: nanfix115.trace 의 회귀 게이트 ─────────────────────────────────
def _trace_gate(got: dict, how: str) -> dict:
    key = next((k for k in got if "정본 경로 씨앗0 상수" in k), None)
    return {"어떻게": how, "게이트 키": key, "게이트": got.get(key),
            "산출물": "runners/out899a_nanfix115_trace.json"}


def reuse_nanfix115_trace() -> dict:
    p = ROOT / "runners/out899a_nanfix115_trace.json"
    if not p.exists():
        return {"🔴 실패": f"{p.name} 이 없다 --- `full` 로 한 번은 돌려야 한다"}
    return _trace_gate(json.loads(p.read_text()), "이미 남긴 산출물을 읽었다(적합 0회)")


def run_nanfix115_trace() -> dict:
    import nanfix115 as N
    tmp = Path(tempfile.mkdtemp(prefix="out899a_nanfix_"))
    real_out = N.OUT
    N.OUT = tmp
    err = None
    try:
        N.trace()
    except Exception as e:                                  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"
    finally:
        N.OUT = real_out
    src = tmp / "out115_trace.json"
    if not src.exists():
        shutil.rmtree(tmp, ignore_errors=True)
        return {"🔴 실패": err or "산출물이 안 생겼다"}
    got = json.loads(src.read_text())
    shutil.copy(src, ROOT / "runners/out899a_nanfix115_trace.json")
    shutil.rmtree(tmp, ignore_errors=True)
    return {"예외": err, **_trace_gate(got, "nanfix115.trace 를 실제로 돌렸다(적합 1회)")}


# ── 동적 ③: verdict112 의 동결 대조 (적합 0회) ─────────────────────────────
def run_verdict112() -> dict:
    import verdict112 as V
    tmp = Path(tempfile.mkdtemp(prefix="out899a_verdict_"))
    real_out = V.OUT
    V.OUT = tmp / "out112_verdict.json"
    err = None
    try:
        V.main()
    except Exception as e:                                  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"
    finally:
        V.OUT = real_out
    src = tmp / "out112_verdict.json"
    if not src.exists():
        shutil.rmtree(tmp, ignore_errors=True)
        return {"🔴 실패": err or "산출물이 안 생겼다"}
    got = json.loads(src.read_text())
    k1 = "① 내가 직접 잰 값 — 씨앗 0~11 · 오늘 챔피언 경로"
    gate = got.get(k1, {}).get("씨앗0 동결값 대조")
    shutil.copy(src, ROOT / "runners/out899a_verdict112.json")
    shutil.rmtree(tmp, ignore_errors=True)
    return {"예외": err, "씨앗0 동결값 대조": gate,
            "⚠": "이 게이트는 동결 산출물을 읽는다 --- 적합 0회",
            "산출물 사본": "runners/out899a_verdict112.json"}


# ── 동적 ④: board898·wire898 재현본과 이력 산출물의 수치 대조 ──────────────
SKIP_KEYS = {"HEAD", "시각", "초", "코드 sha", "배선"}


def leaves(o, pre=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if pre == "" and k in SKIP_KEYS:
                continue
            yield from leaves(v, f"{pre}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{pre}[{i}]")
    else:
        yield pre, o


def compare(orig: Path, rerun: Path) -> dict:
    if not rerun.exists():
        return {"🔴": f"재현본이 없다: {rerun.name}"}
    a, b = json.loads(orig.read_text()), json.loads(rerun.read_text())
    A, B = dict(leaves(a)), dict(leaves(b))
    only = sorted(set(A) ^ set(B))
    diff = {}
    for k in sorted(set(A) & set(B)):
        va, vb = A[k], B[k]
        if isinstance(va, float) and isinstance(vb, float):
            if va != vb and not (va != va and vb != vb):    # nan == nan 으로 본다
                diff[k] = {"이력": va, "재현": vb, "차": vb - va}
        elif va != vb:
            diff[k] = {"이력": va, "재현": vb}
    return {"이력": orig.name, "재현": rerun.name,
            "견준 잎": len(set(A) & set(B)),
            "한쪽에만 있는 키": only[:20], "한쪽에만 있는 키 수": len(only),
            "🔴 값이 다른 잎": diff,
            "🔴 수치 비트 동일": (not diff) and (not only)}


def main(full: bool, reuse: bool = False):
    t0 = time.time()
    s = scan()
    r2 = rule2(s["은퇴값을 이고 있는 파일"])

    res = {
        "무엇": "이슈 #123 --- 씨앗0 상수 게이트 전수 확인 + 규칙 집행",
        "🔴 규칙": [
            "① 정본이 옮겨가면 씨앗0 상수도 같이 옮긴다",
            "② 옛 정본을 재는 러너는 옛 구현을 파일 안에 박는다 --- 반입 금지",
            "③ 셋째 길(아무것도 안 함)이 「영구 False 게이트」다",
        ],
        "은퇴값": RETIRED,
        "산 값(dose896.EXPECT_POOLED_K1_S0 에서 읽음)": LIVE_S,
        "정적 ① 전수 훑기": s,
        "정적 ② 반입 금지": r2,
        "모드": ("full(실제로 돌렸다)" if full else
                ("reuse(남긴 산출물을 읽었다)" if reuse else "정적만")),
    }

    if full or reuse:
        res["동적 ㄱ dose896.stage0 (판정 게이트)"] = (
            reuse_dose896_stage0() if reuse else run_dose896_stage0())
        # verdict112 는 적합 0회라 언제나 다시 돌린다(동결 산출물을 읽을 뿐이다)
        res["동적 ㄴ verdict112 (동결 대조)"] = run_verdict112()
        res["동적 ㄷ nanfix115.trace (회귀 증거)"] = (
            reuse_nanfix115_trace() if reuse else run_nanfix115_trace())
        res["동적 ㄹ board898 재현 대조"] = compare(
            ROOT / "runners/out898_board.json",
            ROOT / "runners/out898_board.899a.json")
        res["동적 ㅁ wire898 재현 대조"] = compare(
            ROOT / "runners/out898_wire.json",
            ROOT / "runners/out898_wire.899a.json")

    ok = (not s["🔴 허가 없는 자리"]) and (not r2["🔴 위반"])
    res["🔴 정적 통과"] = ok
    res["초"] = round(time.time() - t0, 1)
    res.update(stamp())
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: res[k] for k in res
                      if k.startswith(("정적", "동적", "🔴", "산 값"))},
                     ensure_ascii=False, indent=1), flush=True)
    return res


if __name__ == "__main__":
    _m = sys.argv[1] if len(sys.argv) > 1 else ""
    main(full=(_m == "full"), reuse=(_m == "reuse"))
