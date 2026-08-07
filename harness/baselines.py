"""Naive 베이스라인 — LLM 예측이 조회 테이블을 넘었는지 판별하는 비교선.

naive-1: 같은 venue_traffic_type 조건화 레코드들의 방문 중앙값 (카테고리 중앙값)
naive-2: 같은 공간 또는 브랜드의 가장 최근 선례 실측 그대로 (최근접 이웃)
naive-3: 기획 예상치 — 레코드에 구조화돼 있지 않아 미구현 (visit_notes 자유텍스트뿐; counting_method와 함께 추출 스키마 확장 시 추가)

사용: python3 -m harness.baselines --records data/records --cycle-dir cycle_log/rolling-v1
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics
import sys
from pathlib import Path

from .records import load_records


def visitors_of(r) -> int | None:
    return r.data["outcome"]["totals"].get("visitors")


def naive1(target, conditioning):
    ttype = (target.data["conditions"].get("scale") or {}).get("venue_traffic_type")
    tcm = target.data["outcome"].get("counting_method")
    def cm_of(r): return r.data["outcome"].get("counting_method")
    pool = [visitors_of(r) for r in conditioning
            if visitors_of(r) and (r.data["conditions"].get("scale") or {}).get("venue_traffic_type") == ttype
            and (not tcm or tcm == "unknown" or cm_of(r) == tcm)]
    used = f"same-type+counting({ttype}/{tcm}, n={len(pool)})"
    if not pool:
        pool = [visitors_of(r) for r in conditioning
                if visitors_of(r) and (r.data["conditions"].get("scale") or {}).get("venue_traffic_type") == ttype]
        used = f"same-type({ttype}, n={len(pool)})"
    if not pool:
        pool = [visitors_of(r) for r in conditioning if visitors_of(r)]
        used = f"all(n={len(pool)})"
    return (statistics.median(pool) if pool else None), used


def naive3(target):
    """기획 예상치 — 운영자 자신의 예측 (레코드에 구조화된 경우만)."""
    v = target.data["outcome"].get("plan_visitors_expected")
    return (v, "plan") if v else (None, "no-plan")


def naive2(target, conditioning):
    te = target.data["entities"]
    for r in reversed(conditioning):  # 시간순 정렬 → 뒤가 최근
        re_ = r.data["entities"]
        if visitors_of(r) and (
            (te.get("space_key") and re_.get("space_key") == te.get("space_key"))
            or (te.get("brand_key") and re_.get("brand_key") == te.get("brand_key"))
        ):
            return visitors_of(r), f"nearest({r.record_id})"
    return None, "no-match"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default="data/records")
    ap.add_argument("--cycle-dir", default="cycle_log/rolling-v1")
    args = ap.parse_args()

    recs = sorted([r for r in load_records(args.records) if r.has_outcome], key=lambda r: r.start)
    by_id = {r.record_id: r for r in recs}
    order = [r.record_id for r in recs]

    rows, apes = [], {"llm": [], "naive1": [], "naive2": []}
    for f in sorted(glob.glob(f"{args.cycle_dir}/*.scored.json")):
        e = json.loads(Path(f).read_text())
        v = e["scores"]["per_metric"].get("visitors")
        if not v or v.get("ape") is None:
            continue
        rid = e["record_id"]
        target = by_id[rid]
        conditioning = [by_id[c] for c in order[:order.index(rid)]]
        actual = v["actual"]

        n1, n1_note = naive1(target, conditioning)
        n2, n2_note = naive2(target, conditioning)
        row = {"id": rid, "actual": actual, "llm_ape": v["ape"]}
        apes["llm"].append(v["ape"])
        for key, val, note in (("naive1", n1, n1_note), ("naive2", n2, n2_note)):
            if val is not None:
                ape = abs(val - actual) / actual
                row[key] = (val, ape, note)
                apes[key].append(ape)
            else:
                row[key] = (None, None, note)
        rows.append(row)

    print(f"{'홀드아웃':10s} {'실측':>7s} | {'LLM':>6s} | {'n1 중앙값':>16s} {'APE':>6s} | {'n2 최근접':>16s} {'APE':>6s}")
    for r in rows:
        n1v, n1a, n1n = r["naive1"]; n2v, n2a, n2n = r["naive2"]
        print(f"{r['id']:10s} {r['actual']:7,.0f} | {r['llm_ape']:6.0%} | "
              f"{(f'{n1v:,.0f}' if n1v else '—'):>16s} {(f'{n1a:.0%}' if n1a is not None else '—'):>6s} | "
              f"{(f'{n2v:,.0f}' if n2v else '—'):>16s} {(f'{n2a:.0%}' if n2a is not None else '—'):>6s}")
    print()
    for k, label in (("llm", "LLM"), ("naive1", "naive-1 카테고리 중앙값"), ("naive2", "naive-2 최근접 선례")):
        if apes[k]:
            s = sorted(apes[k])
            print(f"{label:24s} MAPE 중앙값 {s[len(s)//2]:.1%}  (n={len(s)})")
    print("\nnaive-3(기획 예상치): 미구현 — 레코드에 비구조화. counting_method 확장 시 함께 추출.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
