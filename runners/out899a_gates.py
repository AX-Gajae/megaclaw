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
    자기 시험       🔴 **검출기를 심어서 확인한다**(`selftest()` · `PLANT`).
                    반입 우회 일곱 꼴 + *「주석만 있는 박음」* 을 임시 파일로 써서
                    물린다. 하나라도 놓치면 **정적 통과가 false** 다.
    동적(full)      게이트 셋을 **실제로 돌려서** True 를 내는지 본다(조항 59 ---
                    고쳤다고 되는 게 아니다). 이력 산출물은 하나도 안 덮는다.

────────────────────────────────────────────────────────────────────────────
🔴 **2026-08-11 · 수리 C · 이슈 #131(티처 #62 C3·M7) --- 세 자리를 고쳤다.**

  ㄱ **검사 대상이 `ALLOW` 안의 셋뿐이라 새 러너를 원리상 안 봤다.**
     이제 저장소 `.py` **전량**(629개)을 돌고 세 갈래로 판정한다(`rule2` docstring).
     허가 목록이 곧 검사 목록이면, 목록에 자기를 안 적는 파일은 영원히 안 걸린다.

  ㄴ **반입 검출이 반입문 두 꼴만 봐서 14 변이 중 7 이 우회됐다.**
     별칭(`from state import rank_test`) · 상대 · `sys.path` 조작 · `importlib` ·
     `exec` · `__import__`+`getattr` · `spec_from_file_location` 을 닫았다.
     🔴 **전부 닫지는 못한다** --- 못 닫는 길은 `CANNOT_CLOSE` 에 적었다.
     (실물 성과: `ruler890.py:127` 의 **별칭반입**이 이 수리로 처음 보였다.)

  ㄷ **`inline` 문턱이 주석 한 줄로 참이 됐다**(옛 `:241` 은 `in txt` 문자열 검사).
     이제 AST 에서 `argsort(argsort(x))` **중첩 호출**을 찾는다. 실제로 주석만으로
     문턱을 넘던 파일이 셋 있다(`verdict112:11`·`text680:31`·`state/rank_test.py:48`).

사용:
    python3 runners/out899a_gates.py          # 정적만 (초 단위)
    python3 runners/out899a_gates.py full     # 정적 + 동적 (적합 2회 · 30분쯤)
    OUT899A_WIRE_TAG=900c … full              # 🔴 **오늘 돌린** 재현본과 견준다
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
import re                                                       # noqa: E402
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
    # 🔴 티처 #64 가 이 자리를 붉게 만들었다 --- **집행자가 옳게 작동했다.**
    # 논문 486 의 errata 가 *"이 논문은 은퇴값을 한 번도 인용하지 않는다"* 를 적으면서
    # **그 값들을 나열했다.** `paper_dead()` 의 errata 사면은 그걸 통과시키지만
    # **집행자는 별개 검사라 안 통과시킨다** --- 두 게이트가 같은 자리를 다르게 본다.
    # 🔴 그 자체가 발견이다: **errata 는 `paper_dead` 의 사면 근거일 뿐 집행자의 면허가 아니다.**
    # 본문(`main.tex`)은 은퇴값을 한 자도 안 쓴다(티처가 훑어 확인) --- 그래서 여기서 닫는다.
    "paper/steps/486_nolever/meta.json": ("errata",
        "발행물의 errata. **「이 논문은 은퇴값을 인용하지 않는다」를 적으려면 "
        "어느 값을 안 쓰는지 적어야 한다** --- 그 문장 자체가 값을 요구한다. "
        "본문 `main.tex` 은 은퇴값이 0건(티처 #64 가 훑어 확인). 본문은 안 고친다(발행물 개작 금지). "
        "⚠ 다음에 이런 문장을 쓸 때는 값을 나열하지 말고 `ingest/audit.py:DEAD_NUMBERS` 를 "
        "가리켜라 --- 그러면 이 등록이 필요 없다"),
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
    # ── 미결 넷이었던 자리 --- **2026-08-11 · 수리 C · 이슈 #131 로 넷 다 닫았다** ──
    "docs/용어.md": ("산문",
        ":43-47. 옛 딱지는 *「챔피언은 `argsort(argsort)`(서수)」* 를 **현재형으로** "
        "적었다. 지금은 :45-46 이 *「🔴 오늘은 아니다 --- 노트 898 이 판을 자에 맞춰 "
        "`rank_test` 를 동률 평균으로 바꿨다. 이 줄은 #112 시대의 기술이다」* 로 "
        "닫혀 있다(2026-08-11 확인). 은퇴값은 #112 시대를 **인용**하는 자리라 남는다"),
    "runners/refit112.py": ("이력",
        ":11 의 딱지를 **`(챔피언)` → `(은퇴 · 「서수 순위 시대 값」 · 898 이전 챔피언)`** "
        "으로 고쳤다(2026-08-11 · 이슈 #131). `(챔피언)` 은 `OK_MARKS` 에 없는 낱말이라 "
        "**표시 구실도 못 하면서** 오늘의 챔피언인 척했다"),
    "runners/text680.py": ("이력",
        ":55 는 딱지가 옳다(*「이력(서수 시대 · 판정에 쓰지 마라)」*). 🔴 그 위 :53 이 적은 "
        "`0.4731063028988083` 과 정본 `dose896.EXPECT_POOLED_K1_S0`(`…84`)의 차는 "
        "**재 봤다: 2 ULP 이고 원인은 누적 차례다**(`runners/out900c_ulp.py` → "
        "`out900c_ulp.json` --- 차례만 바꿔 더하면 서로 다른 double 이 **다섯**, 폭 "
        "**5 ULP**. `sorted` → …83 · 하네스 `list(data.dom)` → …84). :53 에 그 출처를 "
        "적었다. 옛 사유가 *「1 ULP」* 라 적은 것도 틀렸다(2 ULP)"),
}

#: 🔴 **`state.rank_test` 를 반입해도 되는 자리** --- ② 의 예외는 **사유 없이는 못 산다**.
#: (티처 #62 M7 수리 · 2026-08-11 · 이슈 #131)
IMPORT_OK = {
    "runners/ruler890.py": (
        "**시대 감별기**. `:104-120 _rank_fn_stamp()` 이 반입한 함수의 소스를 "
        "`inspect.getsource` 로 해싱하고 동률 표본으로 midrank/서수를 **매 실행 실측**한다. "
        "반입을 금지하는 이유(어느 시대인지 모르게 된다)를 **다른 방법으로 닫은** 자리라 "
        "금지의 목적이 이미 충족된다. 규칙 ②의 셋째 길이고, 이 자리가 그 본보기다"),
    "runners/out899c_ruler890R12.py": (
        "**양시대 러너**. `:70 sp_ord` 가 옛 서수 구현을 파일에 박고(②를 지킨다), "
        "`:56` 이 반입한 `rt_spearman` 은 **오늘 팔** 채점자로만 쓴다(`:198`). "
        "두 시대를 한 파일에서 나란히 재는 것이 이 러너의 일이라 반입이 필요하다. "
        "자기 docstring `:78-80` 이 그 경계를 적어 뒀다"),
}

#: `옛구현` 갈래가 반드시 지켜야 하는 것 --- ② 의 기계 판본.
FORBIDDEN_IMPORT = "state.rank_test"

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
SCAN_SUFFIX = {".py", ".json", ".md", ".html", ".txt", ".log", ".jsonl"}

#: `runners/out898_wire.900c.json` 처럼 **꼬리표 붙은 재현본**. 꼬리표는 사이클 이름이다.
TAGGED_RERUN = re.compile(r"^runners/out898_(wire|board)\.[0-9a-z]+\.(json|log)$")

#: 🔴 동적 ㄹ·ㅁ 이 **어느 재현본과 견주는가**. 옛 판은 `.899a.` 를 파일 안에 박아 뒀는데,
#: 그 재현본은 취합 커밋 **이전** 코드로 만든 것이었다(티처 #62 C3). 꼬리표를 밖에서
#: 주면 오늘 돌린 재현본과 견줄 수 있다: `OUT899A_WIRE_TAG=900c … full`
WIRE_TAG = os.environ.get("OUT899A_WIRE_TAG", "899a")
BOARD_TAG = os.environ.get("OUT899A_BOARD_TAG", "899a")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


#: 🔴 **`git HEAD` 스탬프는 원리상 「시작 시점」이다** --- ⑤′ v3.1 의 체크리스트 3 번이 이걸
#: 몰랐다. 실물: 수리 C 가 `wire898`(475초)을 도는 동안 HEAD 가 다섯 번 움직였고
#: (`0a4d43a2→f3ca1d3e→9bd63101→3f721c19→c21d6afb`), 취합 뒤 이 게이트를 다시 돌려도
#: **그 산출물을 커밋하는 순간 HEAD 가 또 바뀌어** 스탬프가 어긋난다. 티처 #63 C1 이
#: 실측했다: 커밋본 `c21d6afbd` · 작업본 `49513995b` · 그때 HEAD `80ea94507` --- **셋이 다 다르다.**
#: 뒤쫓아 다시 찍는 것으로는 안 닫힌다(`main` 의 `a5e5d950a` 가 이미 한 번 손으로 고쳤고
#: 한 사이클 만에 재발했다).
#:
#: **그래서 자를 바꾼다.** HEAD 대신 ① 시작·**끝** 시각 ② 이 러너와 **읽는 코드의 sha256**
#: 을 박는다. 소비자는 「④ 코드 sha == 지금 커밋된 코드의 sha」와 「끝 시각 > 마지막 소스
#: 커밋 시각」을 본다 --- **긴 러너에서도 이 둘은 안 거짓말한다.**
#: `git HEAD` 는 참고용으로만 남기고 이름에 그 뜻을 박는다(판정에 쓰지 마라).
STAMP_CODE = ["runners/out899a_gates.py", "lab/harness.py", "lab/forms.py",
              "state/rank_test.py", "ingest/audit.py"]


def stamp() -> dict:
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    codes = {c: (sha(ROOT / c) if (ROOT / c).exists() else "🔴 파일 없음")
             for c in STAMP_CODE}
    return {"시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "⚠ git HEAD(시작 시점 · 판정에 쓰지 마라)": head,
            "🔴 코드 sha256(이게 자다)": codes,
            "이 파일 sha256": sha(Path(__file__).resolve())}


def stamp_close(st: dict) -> dict:
    """🔴 끝 시각을 박는다 --- 시작 시각만으로는 「언제까지의 코드를 봤나」를 못 말한다."""
    st["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return st


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
        #: 🔴 꼬리표 붙은 재현본은 **꼬리표가 무엇이든** 재현본이다(옛 판은 `.899a.`
        #: 하나만 봐서, 다른 꼬리표로 다시 돌리면 그 산출물이 **허가 없는 자리**로
        #: 잡혀 정적 통과를 뒤집었다 --- 이슈 #131 에서 `OUT898_TAG=900c` 로 실측).
        if kind is None and TAGGED_RERUN.match(rel):
            kind, why = "검출기", ("`OUT898_TAG=<꼬리표>` 재현본 --- 이력 산출물을 안 덮으려고 "
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


#: 🔴 **동적 반입을 여는 함수들**(문자열로 모듈을 고르는 자리). 여기 **문자열 인자로**
#: `rank_test` 가 들어가면 반입으로 센다. 임의의 함수에 든 문자열은 **안 본다** ---
#: 산문(`say("state.rank_test 를 반입하지 마라")`)까지 잡으면 검출기가 시끄러워져
#: 아무도 안 본다.
DYN_IMPORT_FN = {
    "import_module", "__import__", "exec", "eval", "compile",
    "spec_from_file_location", "module_from_spec", "load_module",
    "run_path", "run_module", "SourceFileLoader", "machinery",
}


def _fname(node) -> str:
    """호출 대상의 **끝 이름**(`importlib.import_module` → `import_module`)."""
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def _norm_mod(m: str) -> str:
    return (m or "").replace("runners.", "")


def rank_test_refs(path: Path) -> list:
    """🔴 `state.rank_test` 를 끌어오는 **모든 꼴**을 AST 로 잡는다.

    티처 #62 M7 이 옛 판(반입문 두 꼴만 봄)에서 **14 변이 중 7 우회**를 셌다.
    여기서 닫는 것(각 꼴에 이름을 붙여 산출물에 찍는다 --- 무엇이 걸렸는지 사람이
    읽을 수 있어야 한다):

      직접반입   `from state.rank_test import spearman` · `import state.rank_test`
      별칭반입   `from state import rank_test [as RT]`      ← 우회 ①
      상대반입   `from .rank_test import …` · `from . import rank_test`  ← 우회 ②
      경로조작   `sys.path` 를 만진 뒤 `import rank_test` / `from rank_test import …` ← 우회 ③
      문자열경유 `importlib.import_module("state.rank_test")` · `__import__(…)` ·
                `exec("from state.rank_test import …")` ·
                `spec_from_file_location(…, "state/rank_test.py")`   ← 우회 ④⑤⑥⑦

    🔴 **못 닫는 것은 `CANNOT_CLOSE` 에 적는다.** 파이썬에서 반입 우회는 원리상
    끝이 없다(모듈 이름을 실행 중에 만들면 정적으로는 안 보인다). 여기서 그은 선은
    **「소스에 `rank_test` 라는 글자가 반입 자리에 있으면 잡는다」** 이고,
    그 글자조차 없는 것은 못 잡는다고 적어 둔다.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    found = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            mod = _norm_mod(n.module)
            names = [a.name for a in n.names]
            if n.level:                                   # 상대반입
                if mod.endswith("rank_test") or "rank_test" in names:
                    found.append(f"{n.lineno}: 상대반입 from {'.'*n.level}{n.module or ''} "
                                 f"import {', '.join(names)}")
            elif mod == FORBIDDEN_IMPORT:
                found.append(f"{n.lineno}: 직접반입 from {n.module} import "
                             + ", ".join(names))
            elif "rank_test" in names:                    # 별칭반입
                found.append(f"{n.lineno}: 별칭반입 from {n.module} import "
                             + ", ".join(names))
            elif mod == "rank_test":                      # sys.path 조작 뒤
                found.append(f"{n.lineno}: 경로조작 from rank_test import "
                             + ", ".join(names))
        elif isinstance(n, ast.Import):
            for a in n.names:
                nm = _norm_mod(a.name)
                if nm == FORBIDDEN_IMPORT:
                    found.append(f"{n.lineno}: 직접반입 import {a.name}")
                elif nm == "rank_test" or nm.endswith(".rank_test"):
                    found.append(f"{n.lineno}: 경로조작 import {a.name}")
        elif isinstance(n, ast.Call) and _fname(n) in DYN_IMPORT_FN:
            for s in [a for a in n.args if isinstance(a, ast.Constant)
                      and isinstance(a.value, str)]:
                v = s.value
                if ("state.rank_test" in v or "state/rank_test" in v
                        or v.strip() == "rank_test" or "rank_test.py" in v
                        or "import rank_test" in v):
                    found.append(f"{n.lineno}: 문자열경유 {_fname(n)}({v[:60]!r})")
    return found


def _is_argsort(f) -> bool:
    return ((isinstance(f, ast.Attribute) and f.attr == "argsort")
            or (isinstance(f, ast.Name) and f.id == "argsort"))


def inlines_ordinal(path: Path) -> list:
    """🔴 옛 서수 구현을 **정말로 박았나** --- 주석 한 줄로는 참이 안 된다.

    옛 판(`:241`)은 `"argsort(np.argsort" in txt` 였다. 그래서 **주석·문서열
    한 줄이 문턱을 넘겼다** --- `verdict112.py:11`·`text680.py:31`·
    `state/rank_test.py:48` 셋이 실제로 그 꼴이다(전부 설명문인데 문자열 검사는
    통과시킨다). 이제 **AST 에서 `argsort(argsort(x))` 중첩 호출**을 찾는다.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _is_argsort(n.func):
            for a in n.args:
                if isinstance(a, ast.Call) and _is_argsort(a.func):
                    out.append(n.lineno)
    return sorted(set(out))


#: 🔴 **못 닫는 것.** 이 저장소의 관례대로 코드에 적는다 --- 「전부 닫았다」고 적는
#: 편이 위험하다. 아래는 이 검출기가 **원리상** 못 보는 길이다.
CANNOT_CLOSE = [
    "모듈 이름을 실행 중에 만드는 반입 --- `__import__('state.' + 'rank' + '_test')` · "
    "`import_module(cfg['mod'])`. 소스에 `rank_test` 라는 글자가 없으면 정적으로는 안 보인다",
    "옛/새 구현을 **글자로 베껴** 다른 이름으로 부르는 것 --- 반입이 아니라 복제라 "
    "②(반입 금지)의 사정거리 밖이다. 그건 규칙 ②가 **권장하는** 길이기도 하다(박아라)",
    "`state/rank_test.py` **자신**이 바뀌는 것 --- 이 검출기는 누가 그 함수를 쓰는지를 "
    "볼 뿐 그 함수가 어느 시대인지는 안 본다. 시대는 `ruler890._rank_fn_stamp()` 처럼 "
    "**실행 중에** 재야 한다(소스 sha + 동률 표본)",
    "임의의 함수에 문자열로 넘긴 모듈 이름 --- `DYN_IMPORT_FN` 밖의 호출은 안 본다. "
    "넓히면 산문까지 잡혀 검출기가 시끄러워지고, 시끄러운 검출기는 안 읽힌다",
    "🔴 **`.py` 가 아닌 실행 경로**(노트북 · 셸 문자열 · 원격). 이 저장소엔 아직 없다",
]


#: 🔴 **심어서 확인한다.** 검출기를 고쳐 놓고 안 심어 보면 그건 「고쳤다」이지
#: 「돌려 봤다」가 아니다(조항 59 · 이슈 #131 의 본체가 그 문장이다).
#: 각 줄: (이름, 소스, 반입으로 잡혀야 하나, 박은 것으로 잡혀야 하나)
PLANT = [
    ("직접반입", "from state.rank_test import spearman\n", True, False),
    ("직접반입(모듈)", "import state.rank_test\n", True, False),
    ("🔴우회① 별칭반입", "from state import rank_test\n", True, False),
    ("🔴우회①' 별칭반입+as", "from state import rank_test as RT\n", True, False),
    ("🔴우회② 상대반입", "from .rank_test import spearman\n", True, False),
    ("🔴우회②' 상대반입(패키지)", "from . import rank_test\n", True, False),
    ("🔴우회③ sys.path 조작",
     "import sys\nsys.path.insert(0, '/Users/ax/world_model/state')\n"
     "import rank_test\n", True, False),
    ("🔴우회④ importlib",
     "import importlib\nRT = importlib.import_module('state.rank_test')\n", True, False),
    ("🔴우회⑤ exec",
     "exec('from state.rank_test import spearman')\n", True, False),
    ("🔴우회⑥ __import__+getattr",
     "sp = getattr(__import__('state.rank_test', fromlist=['spearman']), 'spearman')\n",
     True, False),
    ("🔴우회⑦ spec_from_file_location",
     "from importlib.util import spec_from_file_location\n"
     "s = spec_from_file_location('rt', 'state/rank_test.py')\n", True, False),
    ("🔴 주석만 있는 '박음'(옛 :241 문턱이 참으로 읽던 것)",
     "# 옛 구현은 np.argsort(np.argsort(v)) 였다\n", False, False),
    ("🔴 문서열만 있는 '박음'",
     '"""옛 구현: np.argsort(np.argsort(v))."""\n', False, False),
    ("진짜로 박음", "import numpy as np\ndef r(v):\n    return np.argsort(np.argsort(v))\n",
     False, True),
    ("진짜로 박음(맨 argsort)", "def r(v):\n    return argsort(argsort(v))\n", False, True),
    ("산문 속의 이름(잡으면 안 된다)",
     "def say(s):\n    print(s)\nsay('state.rank_test 를 반입하지 마라')\n", False, False),
]


def selftest() -> dict:
    """`PLANT` 를 임시 디렉터리에 **실제로 써서** 검출기에 물린다. 저장소는 안 건드린다."""
    tmp = Path(tempfile.mkdtemp(prefix="out899a_plant_"))
    rows, bad = {}, []
    for i, (name, src, want_imp, want_inline) in enumerate(PLANT):
        f = tmp / f"plant{i}.py"
        f.write_text(src, encoding="utf-8")
        got_imp, got_inline = rank_test_refs(f), inlines_ordinal(f)
        ok = (bool(got_imp) == want_imp) and (bool(got_inline) == want_inline)
        rows[name] = {"반입으로 잡혔나": [r.split(": ", 1)[-1] for r in got_imp],
                      "박은 것으로 잡혔나": bool(got_inline),
                      "기대(반입·박음)": [want_imp, want_inline], "통과": ok}
        if not ok:
            bad.append(name)
    shutil.rmtree(tmp, ignore_errors=True)
    return {"어떻게": "임시 파일 %d개를 써서 검출기에 물렸다(적합 0회)" % len(PLANT),
            "자리": rows, "🔴 놓친 것": bad, "🔴 전부 잡았나": not bad}


def _py_files():
    for p in sorted(ROOT.rglob("*.py")):
        if any(d in SKIP_DIRS for d in p.parts):
            continue
        yield p


def rule2(hits: dict) -> dict:
    """② **옛 값을 재는 러너는 옛 구현을 박고 `state.rank_test` 를 반입하지 않는다.**

    이것이 C1 의 기계 판본이다. `board898.py` 초판이 정확히 이 꼴이었다.

    ────────────────────────────────────────────────────────────────────────
    🔴 **2026-08-11 · 티처 #62 M7 수리 · 이슈 #131 --- 검사 대상을 `ALLOW` 밖으로 넓혔다.**

    옛 판은 대상이 **`ALLOW` 안의 `옛구현` 셋뿐**이라 **새 러너를 원리상 안 봤다.**
    허가 목록이 곧 검사 목록이면, 목록에 자기를 안 적는 파일은 영원히 안 걸린다.
    이제 저장소의 **`.py` 전량**을 돌고 아래 셋 중 하나에 걸리는 것만 판정한다:

      ㄱ `ALLOW` 의 `옛구현`               → 박았나 · 반입 안 했나 (옛 검사 그대로)
      ㄴ **옛 구현을 박았는데 반입도 한다**  → 어느 쪽으로 재는지 알 수 없다.
                                            `IMPORT_OK` 에 사유가 있어야 산다
      ㄷ **은퇴값을 이고 + 반입 + 안 박았다** → 898 의 병 **그 자체**. `ALLOW` 나
                                            `IMPORT_OK` 에 사유가 있어야 산다

    ⚠ **넓히되 「위반」은 좁게** 잡았다. 반입만 하는 파일(`lab/harness.py` 등 20여 개)은
    옛 값을 재는 파일이 아니므로 대상이 아니다. 넓힌 자리가 시끄러우면 다음 세션이
    **산출물을 안 읽는다** --- 그게 이 집행자가 죽는 방식이다.
    """
    rows, bad, warn, only_inline = {}, [], [], []
    #: 🔴 hits 만 돌면 **`thr898.py` 가 빠진다** --- 그 파일은 상수를 안 이고
    #: 옛 *구현*만 이고 있기 때문이다. 그런데 ②를 처음 지킨 자리가 바로 거기다.
    allow_old = {k for k, v in ALLOW.items() if v[0] == "옛구현"} \
        | {k for k, v in hits.items() if v["갈래"] == "옛구현"}

    seen = set()
    for p in _py_files():
        rel = str(p.relative_to(ROOT))
        seen.add(rel)
        try:
            txt = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        refs = rank_test_refs(p)
        inline = inlines_ordinal(p)
        holds = RETIRED in txt
        why_ok = IMPORT_OK.get(rel)
        kind = ALLOW.get(rel, (None, None))[0]

        if rel in allow_old:
            갈래 = "ㄱ ALLOW 옛구현"
            ok = bool(inline) and (not refs or bool(why_ok))
        elif inline and refs:
            갈래 = "ㄴ 박고도 반입"
            ok = bool(why_ok)
        elif holds and refs and not inline:
            갈래 = "ㄷ 은퇴값 + 반입 + 안 박음(898 의 병)"
            ok = bool(why_ok) or kind is not None
        elif inline:
            only_inline.append(f"{rel}:{inline[0]}")
            continue
        else:
            continue

        rows[rel] = {"갈래": 갈래, "반입": refs, "박은 자리(줄)": inline,
                     "은퇴값을 이고 있나": holds,
                     "반입 허가 사유": why_ok, "ALLOW 갈래": kind, "통과": ok}
        if not ok:
            bad.append(rel)
        elif refs:
            warn.append(rel)

    for rel in sorted(allow_old - seen):
        rows[rel] = {"🔴": "파일이 없다"}
        bad.append(rel)

    return {"검사": "옛 값을 재는 러너는 옛 구현을 박고 state.rank_test 를 반입하지 않는다",
            "🔴 검사 대상": "저장소 .py 전량(ALLOW 밖도 본다 --- 티처 #62 M7)",
            "훑은 .py": len(seen),
            "자리": rows,
            "⚠ 반입하되 사유가 있는 자리": sorted(warn),
            "박기만 했다(반입 없음 · 문제 없음)": sorted(only_inline),
            "🔴 못 닫는 것": CANNOT_CLOSE,
            "🔴 위반": bad}


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


#: 🔴 **일부러 바꾼 키 이름**. 이슈 #131 · 티처 #62 C3 --- 취합 커밋이
#: `post+rank_test(챔피언)` 을 `post+rank_test(그때의 챔피언)` 으로 바꿨다
#: (「챔피언」이 **898 이전**을 뜻한다는 것을 이름에 박으려고).
#: 이름을 바꾼 것은 **옳은 변경**이지만, 그러면 이력 산출물과 잎 이름이 갈려서
#: 대조가 *"한쪽에만 있는 키 24개"* 로 시끄러워진다. 그래서 **이름만** 되돌려
#: 견주고, **되돌렸다는 사실을 산출물에 적는다**(조용히 맞추면 그게 은폐다).
RENAMED = {"post+rank_test(그때의 챔피언)": "post+rank_test(챔피언)"}


def _unrename(k: str) -> str:
    for new, old in RENAMED.items():
        k = k.replace(new, old)
    return k


def compare(orig: Path, rerun: Path) -> dict:
    if not rerun.exists():
        return {"🔴": f"재현본이 없다: {rerun.name}"}
    a, b = json.loads(orig.read_text()), json.loads(rerun.read_text())
    A = {_unrename(k): v for k, v in leaves(a)}
    B = {_unrename(k): v for k, v in leaves(b)}
    only = sorted(set(A) ^ set(B))
    diff = {}
    for k in sorted(set(A) & set(B)):
        va, vb = A[k], B[k]
        if isinstance(va, float) and isinstance(vb, float):
            if va != vb and not (va != va and vb != vb):    # nan == nan 으로 본다
                diff[k] = {"이력": va, "재현": vb, "차": vb - va}
        elif va != vb:
            diff[k] = {"이력": va, "재현": vb}
    used = sorted(n for n in RENAMED
                  if any(n in k for k, _ in leaves(a))
                  or any(n in k for k, _ in leaves(b)))
    return {"이력": orig.name, "재현": rerun.name,
            "견준 잎": len(set(A) & set(B)),
            "한쪽에만 있는 키": only[:20], "한쪽에만 있는 키 수": len(only),
            "⚠ 이름만 되돌려 견준 키": {n: RENAMED[n] for n in used} or "없음",
            "🔴 값이 다른 잎": diff,
            "🔴 수치 비트 동일": (not diff) and (not only)}


def main(full: bool, reuse: bool = False):
    t0 = time.time()
    # 🔴 **`stamp()` 은 실행 「시작」에서 불러야 한다**(티처 #64 C3).
    # v3.2 가 `git HEAD` 스탬프를 폐기하며 「시작·끝 시각 + 코드 sha256」을 세웠는데,
    # 그 구현이 `res.update(stamp_close(stamp()))` 로 **끝에서 둘 다** 불렀다.
    # 실측: `out899a_gates.json` 이 **시작 18:45:10 · 끝 18:45:10 · 초 116.9** —
    # **116.9초 걸린 실행의 시작과 끝이 같은 초다. 「시작 시각」이 실은 끝 시각이었다.**
    # 코드 sha 도 끝에서 읽혔으므로, 도는 동안 다른 팔이 `ingest/audit.py` 를 고치면
    # **실행에 쓰인 코드가 아니라 끝난 뒤의 코드**를 증언한다 —
    # 🔴 **v3.1 의 HEAD 스탬프가 걸린 그 병이 자리만 옮겨 재발했다.**
    _st = stamp()
    s = scan()
    r2 = rule2(s["은퇴값을 이고 있는 파일"])
    st = selftest()

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
        "정적 ③ 🔴 검출기 자기 시험(심어서 확인)": st,
        "재현본 꼬리표": {"wire": WIRE_TAG, "board": BOARD_TAG,
                    "⚠": "OUT899A_WIRE_TAG / OUT899A_BOARD_TAG 로 바꾼다"},
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
            ROOT / f"runners/out898_board.{BOARD_TAG}.json")
        res["동적 ㅁ wire898 재현 대조"] = compare(
            ROOT / "runners/out898_wire.json",
            ROOT / f"runners/out898_wire.{WIRE_TAG}.json")

    #: 🔴 검출기가 스스로를 못 잡으면 그 뒤의 「통과」는 아무 뜻이 없다 --- 자기 시험도 건다.
    ok = ((not s["🔴 허가 없는 자리"]) and (not r2["🔴 위반"])
          and st["🔴 전부 잡았나"])
    res["🔴 정적 통과"] = ok
    res["초"] = round(time.time() - t0, 1)
    res.update(stamp_close(_st))
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: res[k] for k in res
                      if k.startswith(("정적", "동적", "🔴", "산 값"))},
                     ensure_ascii=False, indent=1), flush=True)
    return res


if __name__ == "__main__":
    _m = sys.argv[1] if len(sys.argv) > 1 else ""
    main(full=(_m == "full"), reuse=(_m == "reuse"))
