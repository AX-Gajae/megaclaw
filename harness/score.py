"""채점. 예측과 실측 양쪽에 존재하는 필드만 채점한다 — 데이터 소스가 빈약해도 루프는 돈다."""
from __future__ import annotations

METRICS = ["visitors", "sales_krw", "rev_mm_recognized"]


def ape(pred: float, actual: float) -> float | None:
    if actual in (None, 0) or pred is None:
        return None
    return abs(pred - actual) / abs(actual)


def score_prediction(prediction: dict, outcome: dict) -> dict:
    """prediction.totals[metric] = {point, low, high} vs outcome.totals[metric]"""
    scores: dict = {"per_metric": {}, "caveats": ["생존 편향: 조건화 뱅크는 실행된 팝업만 포함 (드랍된 기획 부재)"]}
    pred_totals = prediction.get("totals", {})
    actual_totals = (outcome or {}).get("totals", {})
    completion = (outcome or {}).get("rev_mm_completion", {})
    for m in METRICS:
        p, a = pred_totals.get(m), actual_totals.get(m)
        if p is None or a is None:
            continue
        if m == "rev_mm_recognized" and completion.get("status") not in (None, "complete"):
            scores["caveats"].append(
                f"rev_mm 채점 제외 — 라벨 {completion.get('status')}: {completion.get('rule', '')}")
            continue
        entry = {"actual": a, "point": p.get("point"), "ape": ape(p.get("point"), a)}
        if p.get("low") is not None and p.get("high") is not None:
            entry["interval"] = [p["low"], p["high"]]
            entry["covered"] = bool(p["low"] <= a <= p["high"])
        scores["per_metric"][m] = entry
    apes = [v["ape"] for v in scores["per_metric"].values() if v.get("ape") is not None]
    scores["mape"] = sum(apes) / len(apes) if apes else None
    covered = [v["covered"] for v in scores["per_metric"].values() if "covered" in v]
    scores["interval_coverage"] = (sum(covered) / len(covered)) if covered else None
    return scores


def render_report(record_id: str, scores: dict) -> str:
    lines = [f"# 채점 리포트 — {record_id}", ""]
    for m, v in scores["per_metric"].items():
        iv = f" 구간 {v['interval']} → {'적중' if v.get('covered') else '이탈'}" if "interval" in v else ""
        lines.append(f"- **{m}**: 예측 {v['point']:,} / 실측 {v['actual']:,} / APE {v['ape']:.1%}{iv}" if v.get("ape") is not None
                     else f"- **{m}**: 채점 불가 (결측)")
    if scores.get("mape") is not None:
        lines.append(f"\n**MAPE: {scores['mape']:.1%}**")
    lines.append("\n주의: " + "; ".join(scores["caveats"]))
    return "\n".join(lines)
