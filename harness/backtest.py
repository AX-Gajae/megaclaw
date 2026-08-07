"""블록 1 백테스트 = 블록 2 전향 사이클의 시간여행 버전. 같은 코드, 데이터 소스만 다르다.

흐름:
  1. 레코드 뱅크 로드 (시간순)
  2. 홀드아웃 선택 (기본: outcome 있는 마지막 팝업; 전향 모드: outcome 없는 미래 팝업)
  3. 조건화 manifest 구성 = 홀드아웃 이전 레코드들 + 원문 URI (요약 금지 원칙)
  4. 예측 획득 (ManualPredictor: 템플릿 생성 → 채움 → 재실행)
  5. 커밋 봉인 (해시) — outcome을 보기 전에
  6. 채점 + 사이클 로그 적재 + 리포트

사용:
  python3 -m harness.backtest --records data/records [--holdout RCPU2602] [--cycle-dir cycle_log]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import gate
from .cycle import append_cycle_log, commit_prediction, verify_commit
from .predictor import make_predictor
from .records import PopupRecord, load_records
from .score import render_report, score_prediction


def build_manifest(conditioning: list[PopupRecord]) -> list[dict]:
    return [
        {
            "record_id": r.record_id,
            "record_path": str(r.path),
            "docs": r.doc_uris,  # 조건화 시점엔 이 원문을 읽는다
        }
        for r in conditioning
    ]


def target_stimulus(rec: PopupRecord) -> dict:
    """홀드아웃에게 보여줄 것: 기획서+계약서(intervention/conditions/docs)만. outcome은 절대 미포함."""
    return {
        "record_id": rec.record_id,
        "entities": rec.data["entities"],
        "intervention": rec.data["intervention"],
        "conditions": rec.data["conditions"],
        # 측정 정의: '무엇을 셀 것인가'의 단위. enum만 전달 — basis 원문은 실측 숫자를 포함할 수 있어
        # 누출 사고(2026-07-24, RCPU2629/2631에서 실측값 노출) 이후 제외함.
        "measurement": {"visitors_counting_method": rec.data["outcome"].get("counting_method", "unknown")},
        "docs": [d for d in rec.doc_uris if d.get("kind") in ("기획서", "계약서")],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default="data/records")
    ap.add_argument("--holdout", default=None, help="record_id. 생략 시 outcome 있는 시간순 마지막 팝업")
    ap.add_argument("--cycle-dir", default="cycle_log")
    ap.add_argument("--forward", action="store_true", help="전향 모드: outcome 없는 레코드를 홀드아웃으로 허용, 채점은 실측 인제스트 후")
    ap.add_argument("--predictor", choices=["manual", "llm", "agent"], default="manual",
                    help="llm=종량제 API / agent=구독 세션 내 서브에이전트(2패스) / manual=사람")
    ap.add_argument("--auto", action="store_true", help="llm 예측기: 사람 검토 없이 즉시 봉인")
    ap.add_argument("--state-file", default=None, help="상태층 피처 JSON (챌린저 모드)")
    ap.add_argument("--ensemble", type=int, default=1,
                    help="K>1이면 K회 독립 예측의 필드별 중앙값을 봉인 (llm+auto 전용)")
    ap.add_argument("--no-gate", action="store_true", help="자극 빈곤 게이트 비활성 (실험 전용)")
    ap.add_argument("--no-market", action="store_true", help="시장 층 미주입 (A/B 절제 실험용)")
    args = ap.parse_args()

    records = load_records(args.records)
    if not records:
        print("레코드 없음. data/records/*.json 먼저.", file=sys.stderr)
        return 1

    if args.holdout:
        holdout = next((r for r in records if r.record_id == args.holdout), None)
        if holdout is None:
            print(f"홀드아웃 {args.holdout} 없음", file=sys.stderr)
            return 1
    else:
        with_outcome = [r for r in records if r.has_outcome]
        if not with_outcome:
            print("outcome 있는 레코드가 없음 — 백테스트 불가. --forward로 전향 모드 사용.", file=sys.stderr)
            return 1
        holdout = with_outcome[-1]

    mode = "forward" if args.forward else "backtest"
    if mode == "backtest" and not holdout.has_outcome:
        print(f"{holdout.record_id}에 outcome 없음 — 백테스트 채점 불가. --forward를 쓰거나 outcome 채울 것.", file=sys.stderr)
        return 1

    conditioning = [r for r in records if r.record_id != holdout.record_id and r.start <= holdout.start]
    manifest = build_manifest(conditioning)
    stimulus = target_stimulus(holdout)

    # 자극 빈곤 게이트 — 예측 전 판정 (refuse면 API 호출 자체를 안 함)
    g = gate.assess(stimulus)
    if g["level"] == "refuse" and not args.no_gate:
        gate_path = Path(args.cycle_dir) / f"{holdout.record_id}.gate.json"
        gate_path.parent.mkdir(parents=True, exist_ok=True)
        gate_path.write_text(json.dumps({"record_id": holdout.record_id, "gate": g}, ensure_ascii=False, indent=1))
        print(f"예측 거부 (자극 게이트): {'; '.join(g['reasons'])} → {gate_path}")
        return 0

    predictor = make_predictor(args.predictor, args.cycle_dir, auto=args.auto,
                               state_file=args.state_file, ensemble=args.ensemble,
                               market=not args.no_market)
    prediction = predictor.predict(stimulus, manifest)
    if prediction is not None and g["level"] == "widen" and not args.no_gate:
        prediction = gate.widen(prediction)
        prediction["gate"] = {"level": "widen", "factor": gate.WIDEN_FACTOR, "reasons": g["reasons"]}
        print(f"구간 강제 확대 (자극 게이트 ×{gate.WIDEN_FACTOR}): {'; '.join(g['reasons'])}")
    if prediction is None:
        print(f"예측 대기: {args.cycle_dir}/{holdout.record_id}.prediction.json 생성됨/검토 대기.")
        print("→ 채우거나(manual) 검토 승인(llm: _review_pending 키 삭제) 후 재실행하면 봉인+채점.")
        return 0

    commit_path = Path(args.cycle_dir) / f"{holdout.record_id}.commit.json"
    if not commit_path.exists():
        commit_path = commit_prediction(args.cycle_dir, holdout.record_id, prediction, manifest, predictor.predictor_id, mode)
        print(f"봉인 완료: {commit_path}")
    if not verify_commit(commit_path):
        print("커밋 해시 불일치 — 예측이 사후 수정됨. 이 사이클은 무효.", file=sys.stderr)
        return 2

    if not holdout.has_outcome:
        print("전향 커밋 봉인됨. 실측 인제스트 후 재실행하면 채점.")
        return 0

    sealed = json.loads(commit_path.read_text(encoding="utf-8"))["prediction"]
    scores = score_prediction(sealed, holdout.data["outcome"])
    append_cycle_log(
        args.cycle_dir, holdout.record_id,
        stimulus_ref={"record_id": holdout.record_id, "docs": stimulus["docs"]},
        conditions_ref=holdout.data["conditions"],
        prediction=sealed,
        actual=holdout.data["outcome"],
        scores=scores,
    )
    report = render_report(holdout.record_id, scores)
    report_path = Path(args.cycle_dir) / f"{holdout.record_id}.report.md"
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n리포트: {report_path} / 사이클 로그 적재 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
