"""학습 기록 규격 --- **상수와 검사.** 노트 912 팔 ㅇ.

정본 문서는 `docs/학습기록규격.md` 이고 이 파일은 그것의 **기계 판본**이다.
두 벌을 손으로 적으면 갈라진다(노트 546 · 549 · 670 이 세 번 밟은 병) --- 그래서
문서가 인용하는 수·이름은 **여기서 나온다**.

# 왜 이 규격이 있나

노트 897 이 파이썬 604개를 전수 AST 로 훑어 `state/masked_encoder` ·
`shared_encoder` · `fewshot` · `transfer_eval` **넷을 아무도 안 부른다**는 것을
찾았다. 학습이 돌아도 **어디에도 안 남아서** 조각들이 조용히 죽었다. 남기려면
남길 자리와 꼴이 있어야 한다. 이 규격이 그 꼴이다.

# 세 갈래를 규격 안에 박는다 (조항 59)

    있다        값이 있다
    없다        원래 없는 것이다 (예: 자 없는 run --- **그것도 적는다**)
    못 읽었다    읽으려 했는데 실패했다 (예: 아키텍처를 introspect 못 함)

🔴 셋을 합치지 마라. 아키텍처를 **못 읽은 것**과 **아키텍처가 없는 것**은 다르고,
자가 **없는 것**과 자를 **안 적은 것**도 다르다.
"""
from __future__ import annotations

import re

#: 규격 이름과 판. 🔴 **판 칸은 필수다** --- 규격은 나중에 바뀐다.
#:
#: 🔴 **판 1.1.0(노트 913 팔 ㅈ)** --- 규격 **이름은 그대로 `trainlog/1`** 이다.
#: 늘어난 것은 전부 **더한 칸**이고 뺀 칸이 없으므로 판 1.0.0 으로 적힌 옛 run 은
#: 그대로 읽힌다(`READ_VERSIONS` 가 그것을 명시한다). 무엇이 왜 늘었는지는
#: `docs/학습기록규격.md` §9 에 적혀 있다.
SPEC = "trainlog/1"
SPEC_VERSION = "1.1.0"

#: 🔴 **이 판이 읽을 수 있는 옛 판.** 없는 칸은 「없다」로 읽고 **지어내지 않는다**.
READ_VERSIONS = ("1.0.0", "1.1.0")

#: 판마다 무엇이 늘었나 --- 문서와 코드가 갈라지지 않게 **여기가 정본이다**.
SPEC_CHANGELOG = {
    "1.0.0": "신설(노트 912 팔 ㅇ) --- manifest · metrics.jsonl · arch.json 셋",
    "1.1.0": (
        "노트 913 팔 ㅈ --- **임의 DAG · 동적 잘라내기 · 실시간 · 노드별 상태**를 "
        "위해 여섯을 더했다. ① `층[].묶음`·`층[].묶음 종류`·`arch.json.묶음 표` "
        "(모듈 등록 경로와 그릇 클래스 --- 같은 부분그래프가 N번 나오는 것을 **구조로** "
        "탐지해 `N×` 로 접는 데 쓴다) · ② `층[].헤드 수`(있을 때만) · "
        "③ `arch.json` 에 `규격 판` 칸 · ④ manifest 에 `학습 돌렸나`(구조만 있는 run 과 "
        "지표를 못 남긴 run 을 가른다) · ⑤ 🔴 **`node_metrics.jsonl` 신설** --- "
        "노드별 시계열(grad_norm 등)을 append-only 로 담는다(`Run.log_node()`) · "
        "⑥ 창구가 내는 그림에 `깊이`·`레인`·`간선 표`·`노드 상태`. **뺀 칸은 없다**"),
}

#: 지표 스트림의 규격(파일이 다르므로 이름도 다르다).
METRICS_SPEC = "trainlog/metrics/1"
#: 🔴 판 1.1.0 --- **노드별** 시계열(그래디언트 노름 · 활성 통계 …).
#: 파일이 다르다(`node_metrics.jsonl`) --- 스칼라 스트림을 안 건드리려고 나눴다.
NODE_METRICS_SPEC = "trainlog/node_metrics/1"

#: 노드 지표로 **자주 쓰는 이름**. 목록에 없는 이름도 적을 수 있다(막지 않는다).
#: 🔴 **안 적으면 「못 잼」이다** --- 화면이 회색으로 두고 그렇게 적는다(추정 금지).
NODE_METRIC_NAMES = ("grad_norm", "param_norm", "act_mean", "act_std",
                     "act_zero_frac", "update_norm")
#: 아키텍처 그래프의 규격.
ARCH_SPEC = "trainlog/arch/1"

#: `docs/목표.md` 의 다섯 출력. **「해당 없음」도 값이다** --- 안 적는 것만 금지다.
OUTPUTS = ("①우려", "②결과", "③시점", "④개선", "⑤파생", "해당 없음")

#: 짧은 딱지 → 정식 딱지. 사용자가 `pushes="③"` 처럼 적을 수 있게.
OUTPUT_ALIAS = {
    "①": "①우려", "②": "②결과", "③": "③시점", "④": "④개선", "⑤": "⑤파생",
    "1": "①우려", "2": "②결과", "3": "③시점", "4": "④개선", "5": "⑤파생",
    "없음": "해당 없음", "none": "해당 없음", "": "해당 없음",
}

#: run 의 생애. **「터짐」을 「끝남」으로 적지 않는다.**
RUN_STATUS = ("도는 중", "끝남", "터짐")

#: 아키텍처를 어디서 얻었나. 🔴 **「못 읽음」이 셋째 갈래로 반드시 있다.**
ARCH_SOURCES = ("torch introspect", "준 dict", "못 읽음")

#: 간선을 무엇으로 이었나. **가정으로 이은 것을 실측인 양 적지 않는다.**
EDGE_SOURCES = ("torch.fx 추적", "모듈 등록 순서(가정)", "준 dict", "없음")

#: run_id 에 허용되는 글자. ASCII 만(노트 693 --- 한글 이름은 API 에서 400 이다).
ID_OK = re.compile(r"^[A-Za-z0-9._\-]+$")

#: 이름을 id 로 접을 때 쓸 수 없는 글자를 바꾸는 무늬.
ID_BAD = re.compile(r"[^A-Za-z0-9._\-]+")


def ascii_id(name: str) -> str:
    """이름을 **ASCII run_id 조각**으로 접는다 --- 원래 이름은 따로 남긴다.

    한글 이름(`"학습 909"`)을 그대로 쓰면 URL·파일명·API 에서 터진다(노트 693).
    그렇다고 **조용히 바꾸면** 나중에 누가 무엇을 돌렸는지 못 찾는다 --- 그래서
    `manifest.json` 에 `이름(원래)` 을 그대로 남기고 여기서는 접기만 한다.
    """
    s = ID_BAD.sub("-", str(name or "run")).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s[:64] or "run"


def norm_output(x) -> list:
    """`pushes` 를 다섯 출력 딱지 목록으로 접는다. **모르는 딱지는 죽인다.**"""
    if x is None:
        x = "해당 없음"
    if isinstance(x, str):
        x = [x]
    out = []
    for one in x:
        k = str(one).strip()
        k = OUTPUT_ALIAS.get(k, k)
        if k not in OUTPUTS:
            raise SpecError(
                f"모르는 출력 딱지 '{one}' --- {OUTPUTS} 중 하나여야 한다. "
                f"미는 것이 없으면 '해당 없음' 이라고 **적어라**(안 적는 것만 금지다)")
        if k not in out:
            out.append(k)
    return out or ["해당 없음"]


class SpecError(Exception):
    """규격 위반 --- **기록을 시작하는 자리에서** 죽는다(나중에 조용히 아니라)."""


#: manifest.json 이 반드시 갖는 칸. `check_manifest()` 가 이것으로 잰다.
REQUIRED_MANIFEST = (
    "규격", "규격 판", "run_id", "이름(원래)", "데모인가", "상태",
    "시작 UTC", "끝 UTC", "씨앗", "하이퍼파라미터",
    "코드 sha256", "입력 데이터 sha256",
    "미는 출력", "자", "자 없음", "지표 줄 수", "기록 실패 n건", "환경",
)


def check_manifest(m: dict) -> list:
    """manifest 가 규격을 지키나 --- 어긴 목록을 낸다(비었으면 통과)."""
    bad = []
    for k in REQUIRED_MANIFEST:
        if k not in m:
            bad.append(f"칸 '{k}' 이 없다")
    if m.get("규격") != SPEC:
        bad.append(f"규격 이름이 '{m.get('규격')}' 이다 --- '{SPEC}' 이어야 한다")
    if not m.get("규격 판"):
        bad.append("규격 판이 비었다 --- 규격은 나중에 바뀐다")
    rid = str(m.get("run_id") or "")
    if not ID_OK.match(rid):
        bad.append(f"run_id '{rid}' 가 ASCII 가 아니다(노트 693)")
    if m.get("상태") not in RUN_STATUS:
        bad.append(f"모르는 상태 '{m.get('상태')}' --- {RUN_STATUS}")
    for o in (m.get("미는 출력") or []):
        if o not in OUTPUTS:
            bad.append(f"모르는 출력 딱지 '{o}'")
    if not (m.get("미는 출력") or []):
        bad.append("**미는 출력이 안 적혔다** --- '해당 없음' 이라도 적어야 한다")
    #: 🔴 자 없는 run 도 기록은 된다. 다만 **「자 없음」이 보여야 한다.**
    if bool(m.get("자 없음")) != (not m.get("자")):
        bad.append("'자' 와 '자 없음' 이 어긋난다 --- 자가 없으면 보이게 적어야 한다")
    return bad
