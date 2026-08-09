"""종량제 API 를 **기본 차단**한다 (노트 889 · 사용자 지시 2026-08-10).

지시 원문: *"무조건 api 키로 클로드 돌리지 말고."*

**왜 기본이 차단인가.** 옵트인(“막고 싶으면 켜라”)은 이 저장소에서 이미 실패했다.
`core/agent_task.py` 는 **2026-07-27 에 하루 $297 을 쓰고 나서** 만들어졌는데,
그 뒤로도 `harness/forward.py` 는 유료 경로를 계속 불렀다 --- 무인 크론 전제로
짜였고 아무도 그 한 줄을 안 봤기 때문이다. 2026-08-09 에 그것이 `400 credit
balance is too low` 로 드러났고, **종료 코드는 0 이었다.**

옵트인 가드는 "켜는 것을 잊는" 실패 모드를 갖는다. 그리고 이 판에서 잊힌 것은
**돈이 나가고 나서** 드러난다. 그래서 방향을 뒤집는다 --- **막는 것이 기본이고
쓰려면 명시한다.**

    WM_ALLOW_PAID_API=1 python3 -m ingest.bulk_normalize ...   # 이래야만 열린다

무료 경로는 이미 다 있다:

    ingest.bulk_normalize --agent-dir cycle_log/agent_tasks/<이름>   (2패스)
    harness.backtest --predictor agent --ensemble 3                 (2패스)

**이 가드는 조용하지 않다.** 막을 때 무엇을 대신 쓰라고 적는다 --- 사유 없는
차단은 다음 사람이 그냥 환경변수를 켜게 만든다.
"""
from __future__ import annotations

import os

ENV = "WM_ALLOW_PAID_API"

_HOW = {
    "bulk_normalize": "python3 -m ingest.bulk_normalize --agent-dir cycle_log/agent_tasks/<이름>",
    "predictor_llm": "python3 -m harness.backtest --predictor agent --ensemble 3",
}


def allowed() -> bool:
    return str(os.environ.get(ENV, "")).strip() in ("1", "true", "TRUE", "yes")


def assert_free(where: str) -> None:
    """유료 클라이언트를 만들기 **직전에** 부른다. 막히면 SystemExit."""
    if allowed():
        return
    how = _HOW.get(where, "에이전트 2패스 경로(--agent-dir / --predictor agent)")
    raise SystemExit(
        f"🔴 종량제 API 차단됨 ({where}) --- 사용자 상시 지시: "
        f"'무조건 api 키로 클로드 돌리지 말고'(2026-08-10).\n"
        f"   무료 경로를 쓰라:  {how}\n"
        f"   정말 유료로 돌려야 하면 {ENV}=1 을 붙여 명시하라(노트 889)."
    )
