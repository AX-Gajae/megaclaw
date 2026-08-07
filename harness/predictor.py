"""Predictor 인터페이스. 첫 사이클은 ManualPredictor로 돈다 —
템플릿 파일을 만들어주면 사람(또는 채팅의 LLM)이 원문을 읽고 채워넣는 방식.
LLM API 자동화는 신호 확인(go) 후에 붙인다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

PREDICTION_TEMPLATE = {
    "_instructions": [
        "conditioning_manifest의 원문(docs.uri)을 전부 읽고 채울 것 — 레코드 요약만 보고 예측 금지.",
        "2단 분해 필수: stage1에서 총 소비자 성과를 먼저 추정하고, stage2에서 계약 구조(수수료/고정비)를 산수로 적용해 rev_mm을 도출할 것.",
        "rev_mm을 바로 찍으면 모델이 '잘 되는 팝업'이 아니라 '마진 좋은 계약'을 배운다 — 신호 오염.",
        "point는 최선 추정, [low, high]는 80% 신뢰 구간.",
        "rationale에는 어떤 과거 팝업을 어떤 근거로 참조했는지 명시.",
        "다 채우면 _instructions 키를 지우고 저장 → 하네스 재실행.",
    ],
    "stage1_gross": {
        "gross_consumer_sales_krw": {"point": None, "low": None, "high": None},
        "visitors_total": {"point": None, "low": None, "high": None},
        "assumptions": "",
    },
    "stage2_contract_transform": "계약 구조를 stage1에 적용해 rev_mm을 도출한 산수 (예: 고정 대행료 X + RS y%)",
    "totals": {
        "visitors": {"point": None, "low": None, "high": None},
        "sales_krw": {"point": None, "low": None, "high": None},
        "rev_mm_recognized": {"point": None, "low": None, "high": None},
    },
    "rationale": "",
}


class Predictor(Protocol):
    predictor_id: str

    def predict(self, target_stimulus: dict, conditioning_manifest: list[dict]) -> dict | None:
        """예측 dict 반환. 아직 준비 안 됐으면 None (하네스가 대기 안내)."""
        ...


def make_predictor(kind: str, cycle_dir: str | Path, auto: bool = False, state_file=None,
                   ensemble: int = 1, market: bool = True, features: bool = True):
    """kind: 'manual' | 'llm'. llm은 anthropic SDK 필요, 사람은 검토만(--auto면 검토 생략).
    state_file: 상태층(월드모델 B) 피처 JSON — 주면 <world_state> 블록이 조건화에 주입됨.
    ensemble: K>1이면 K회 독립 실행의 필드별 중앙값 예측(run variance 대응).
    market: False면 시장 층(<market_bank>) 미주입 — A/B 절제 실험용, id에 -nomkt 태그."""
    if kind == "llm":
        from .predictor_llm import LLMPredictor
        return LLMPredictor(cycle_dir, auto=auto, state_file=state_file, ensemble=ensemble,
                            market=market, features=features)
    if kind == "agent":
        # 구독 세션 내 서브에이전트 경로 — 종량제 API 호출 0 (2026-07-27 비용 사고 대응).
        # 2패스: 1패스에서 request.md 덤프 → 에이전트가 prediction.json 작성 → 2패스에서 봉인.
        from .predictor_agent import AgentPredictor
        return AgentPredictor(cycle_dir, state_file=state_file, market=market, features=features)
    return ManualPredictor(cycle_dir)


class ManualPredictor:
    def __init__(self, cycle_dir: str | Path, author: str = "human"):
        self.cycle_dir = Path(cycle_dir)
        self.predictor_id = f"manual:{author}"

    def predict(self, target_stimulus: dict, conditioning_manifest: list[dict]) -> dict | None:
        record_id = target_stimulus["record_id"]
        pending = self.cycle_dir / f"{record_id}.prediction.json"
        if not pending.exists():
            self.cycle_dir.mkdir(parents=True, exist_ok=True)
            payload = dict(PREDICTION_TEMPLATE)
            payload["_conditioning_manifest"] = conditioning_manifest
            payload["_target"] = target_stimulus
            pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return None
        pred = json.loads(pending.read_text(encoding="utf-8"))
        if "_instructions" in pred:
            return None  # 아직 안 채움
        # 봉인 대상에서 작업용 메타 제거
        pred.pop("_conditioning_manifest", None)
        pred.pop("_target", None)
        return pred
