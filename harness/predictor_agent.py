"""에이전트 예측기 — 구독 세션 내 서브에이전트가 예측을 수행하는 경로 (API 종량제 대체).

배경(2026-07-27 비용 사고): 백테스트·절제 실험을 종량제 API로 돌려 하루 $297 발생.
실험 트랙은 구독 세션 내 에이전트로 처리하면 추가 비용이 0이다.

프로토콜 (ManualPredictor와 동일한 2-패스 구조):
  1패스  하네스 실행 → 조건화 재료 전문을 {code}.request.md 로 덤프하고 종료(예측 없음)
  (에이전트) request.md 를 Read → 예측 산출 → {code}.prediction.json 에 저장
  2패스  하네스 재실행 → prediction.json 을 읽어 봉인·채점 (API 호출 0)

무결성:
  - predictor_id = agent:{model}@prompt-{hash} — SYSTEM_PROMPT+스키마 해시는 API 경로와 동일 계산이나
    **모델이 다르므로 API 경로 성적과 합산 금지**(버전 장부 원칙 그대로).
  - 조건화 재료는 API 경로와 완전히 동일한 빌더(build_digest / build_market_block)로 생성 →
    입력 등가성 보장.
"""
from __future__ import annotations

import json
from pathlib import Path

from .predictor_llm import (DIGEST_THRESHOLD, PREDICTION_SCHEMA, STATE_RULE, SYSTEM_PROMPT,
                            _canon, build_conditioning_text, build_digest, select_relevant)


class AgentPredictor:
    def __init__(self, cycle_dir: str | Path, model: str = "session-agent",
                 state_file: str | Path | None = None, market: bool = True,
                 signals: bool = True, features: bool = True):
        from core.llm_runtime import prompt_version
        self.cycle_dir = Path(cycle_dir)
        self.model = model
        self.market = market
        self.signals = signals
        self.features = features
        self.state = {}
        if state_file and Path(state_file).exists():
            self.state = json.loads(Path(state_file).read_text(encoding="utf-8"))
        self.system_prompt = SYSTEM_PROMPT + (STATE_RULE if self.state else "")
        pv = prompt_version(self.system_prompt, PREDICTION_SCHEMA)
        self.prompt_version = pv
        mode = "+state" if self.state else ""
        mkt = "" if self.market else "-nomkt"
        sig = "" if self.signals else "-nosig"
        ft = "" if self.features else "-nofeat"
        self.predictor_id = f"agent:{model}@prompt-{pv}{mode}{mkt}{sig}{ft}"

    def _build_request(self, target_stimulus: dict, conditioning_manifest: list[dict]) -> str:
        relevant_block = ""
        if len(conditioning_manifest) > DIGEST_THRESHOLD:
            conditioning_text = build_digest(conditioning_manifest, features=self.features)
            rel = select_relevant(conditioning_manifest, target_stimulus)
            relevant_block = "\n" + build_conditioning_text(rel).replace(
                "<conditioning_bank>", "<relevant_records_full>").replace(
                "</conditioning_bank>", "</relevant_records_full>") + "\n"
        else:
            conditioning_text = build_conditioning_text(conditioning_manifest)

        market_block = ""
        if self.market:
            from .market_bank import build_market_block
            market_block = build_market_block(target_stimulus, signals=self.signals,
                                              features=self.features)
        state_block = ""
        st = self.state.get(target_stimulus["record_id"])
        if st:
            state_block = f"\n<world_state>\n예측 시점의 세계 상태 (오픈 전 데이터만):\n{_canon(st)}\n</world_state>\n"

        return "\n".join([
            f"# 예측 요청 — {target_stimulus['record_id']}",
            f"\n예측기 ID: `{self.predictor_id}` (이 값이 봉인에 기록된다)",
            "\n## 시스템 규칙 (이대로 따를 것)\n", self.system_prompt,
            "\n## 출력 스키마 (StructuredOutput으로 정확히 이 형태를 반환)\n```json",
            json.dumps(PREDICTION_SCHEMA, ensure_ascii=False, indent=1), "```",
            "\n## 조건화 뱅크\n", conditioning_text,
            relevant_block, market_block,
            "\n## 예측 대상\n<target>\n" + _canon(target_stimulus) + "\n</target>\n" + state_block,
            "\n위 팝업의 성과를 예측하라. 2단 분해를 지키고, 방문 예측은 타깃과 같은 counting 기준의 "
            "선례에 앵커하라. rationale에 참조한 record_id·MKT-ID를 명시하라.",
        ])

    def predict(self, target_stimulus: dict, conditioning_manifest: list[dict]) -> dict | None:
        record_id = target_stimulus["record_id"]
        self.cycle_dir.mkdir(parents=True, exist_ok=True)
        pending = self.cycle_dir / f"{record_id}.prediction.json"
        if pending.exists():
            pred = json.loads(pending.read_text(encoding="utf-8"))
            for k in list(pred):
                if k.startswith("_"):
                    pred.pop(k)
            return pred
        req = self.cycle_dir / f"{record_id}.request.md"
        req.write_text(self._build_request(target_stimulus, conditioning_manifest), encoding="utf-8")
        print(f"예측 요청 생성: {req}\n→ 에이전트가 이 파일을 읽고 {pending} 에 예측 JSON을 쓴 뒤 재실행하면 봉인됩니다.")
        return None
