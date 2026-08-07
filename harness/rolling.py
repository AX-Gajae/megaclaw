"""Rolling-origin 백테스트 (블록 1 확정 설계).

홀드아웃 1개의 일화가 아니라 오차 분포를 뽑는다:
  시간순 정렬 → 앞 min_train건 조건화 → 다음 step건 예측 → 원점 전진 → 반복.
67건이면 예측-실측 쌍 15+개 → MAPE 분위수, 순위상관(Spearman), 구간 커버리지.

사용:
  python3 -m harness.rolling --records data/records --min-train 50 --step 5
  (각 타깃마다 cycle_log/rolling/<id>.prediction.json 템플릿 생성 → 채우고 재실행.
   여러 번 재실행해도 봉인/채점된 타깃은 건너뛰므로 점진적으로 진행 가능.)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .backtest import build_manifest, target_stimulus
from .cycle import append_cycle_log, commit_prediction, verify_commit
from .predictor import make_predictor
from .records import load_records
from .score import METRICS, score_prediction


def spearman(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (vx * vy) if vx and vy else None


def quantile(sorted_vals: list[float], q: float) -> float:
    idx = q * (len(sorted_vals) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default="data/records")
    ap.add_argument("--cycle-dir", default="cycle_log/rolling")
    ap.add_argument("--min-train", type=int, default=50)
    ap.add_argument("--step", type=int, default=5)
    ap.add_argument("--predictor", choices=["manual", "llm"], default="manual")
    ap.add_argument("--auto", action="store_true", help="llm 예측기: 사람 검토 없이 즉시 봉인 (15개 폴드 일괄 실행용)")
    ap.add_argument("--state-file", default=None, help="상태층 피처 JSON — 월드모델(B) 모드")
    args = ap.parse_args()

    recs = [r for r in load_records(args.records) if r.has_outcome]
    if len(recs) <= args.min_train:
        print(f"outcome 있는 레코드 {len(recs)}건 ≤ min-train {args.min_train} — 폴드 불가", file=sys.stderr)
        return 1

    predictor = make_predictor(args.predictor, args.cycle_dir, auto=args.auto, state_file=args.state_file)
    cycle_dir = Path(args.cycle_dir)
    pending, scored = [], []

    for origin in range(args.min_train, len(recs), args.step):
        for target in recs[origin:origin + args.step]:
            rid = target.record_id
            report_marker = cycle_dir / f"{rid}.scored.json"
            if report_marker.exists():
                scored.append(json.loads(report_marker.read_text(encoding="utf-8")))
                continue
            conditioning = recs[:origin]
            manifest = build_manifest(conditioning)
            stimulus = target_stimulus(target)
            prediction = predictor.predict(stimulus, manifest)
            if prediction is None:
                pending.append(rid)
                continue
            commit_path = cycle_dir / f"{rid}.commit.json"
            if not commit_path.exists():
                commit_prediction(args.cycle_dir, rid, prediction, manifest, predictor.predictor_id, "backtest")
            if not verify_commit(commit_path):
                print(f"{rid}: 커밋 해시 불일치 — 무효", file=sys.stderr)
                continue
            sealed = json.loads(commit_path.read_text(encoding="utf-8"))["prediction"]
            s = score_prediction(sealed, target.data["outcome"])
            append_cycle_log(args.cycle_dir, rid,
                             {"record_id": rid, "docs": stimulus["docs"]},
                             target.data["conditions"], sealed, target.data["outcome"], s)
            entry = {"record_id": rid, "scores": s}
            report_marker.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
            scored.append(entry)

    lines = [f"# Rolling-origin 리포트", "",
             f"- 레코드(outcome 보유): {len(recs)} / min-train {args.min_train} / step {args.step}",
             f"- 채점 완료 {len(scored)}건, 예측 대기 {len(pending)}건"]
    for m in METRICS:
        pts = [(e["scores"]["per_metric"][m]["point"], e["scores"]["per_metric"][m]["actual"],
                e["scores"]["per_metric"][m].get("ape"), e["scores"]["per_metric"][m].get("covered"))
               for e in scored if m in e["scores"]["per_metric"]]
        apes = sorted(a for _, _, a, _ in pts if a is not None)
        if not apes:
            continue
        rho = spearman([p for p, _, _, _ in pts], [a for _, a, _, _ in pts])
        cov = [c for _, _, _, c in pts if c is not None]
        lines.append(f"\n## {m} (n={len(apes)})")
        lines.append(f"- MAPE 중앙값 {quantile(apes, .5):.1%} (p25 {quantile(apes, .25):.1%} / p75 {quantile(apes, .75):.1%})")
        lines.append(f"- 순위상관(Spearman) {rho:.2f}" if rho is not None else "- 순위상관: n<3")
        if cov:
            lines.append(f"- 80% 구간 커버리지 {sum(cov)/len(cov):.0%} (목표 ~80% — 크게 높으면 과소확신, 낮으면 과잉확신)")
    lines.append("\n주의: 생존 편향 — 조건화·채점 모두 실행된 팝업만 포함. 드랍된 기획의 분포는 부재.")
    if pending:
        lines.append(f"\n대기 중 타깃: {', '.join(pending[:20])}{' …' if len(pending) > 20 else ''}")
    report = "\n".join(lines)
    (cycle_dir / "rolling_report.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
