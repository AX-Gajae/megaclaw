"""잠재 상태 빌더 — popga 인코더(data/encoder/)로 임의 레코드들의 world_state 생성.

전향용: 전기간 임베딩(embeddings.npz) 사용, 조회 이력은 오늘까지(미래 누출 원천 불가).
백테스트용: 컷오프 임베딩 + 오픈 전 시간 마스크 (실험 스크립트 참조).

사용: python3 -m harness.latent_state CODE1,CODE2 출력파일.json
"""
from __future__ import annotations

import csv
import datetime
import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ENC = Path("data/encoder")


def bq_csv(sql: str) -> list[list[str]]:
    out = subprocess.run(["bq", "query", "--project_id=sweetspot-ax", "--use_legacy_sql=false",
                          "--format=csv", "--max_rows=200000", sql],
                         capture_output=True, text=True, check=True).stdout
    lines = [l for l in out.splitlines() if l and not l.startswith("Waiting")]
    return [row for row in csv.reader(lines[1:])]


def build_state(codes: list[str]) -> dict:
    sys.path.insert(0, ".")
    from harness.records import load_records
    by_id = {r.record_id: r for r in load_records("data/records")}
    targets = [by_id[c] for c in codes if c in by_id]
    if not targets:
        return {}

    d = np.load(ENC / "embeddings.npz", allow_pickle=True)
    emb, stores = d["emb"], [str(s) for s in d["stores"]]
    idx = {s: i for i, s in enumerate(stores)}
    meta = {}
    with open(ENC / "stores.csv") as f:
        for row in csv.reader(f):
            if len(row) >= 3:
                meta[row[0]] = row[2].replace(" | 팝가 Popga", "")
    weekly = {}
    with gzip.open(ENC / "store_weekly.csv.gz", "rt") as f:
        for s, wk, u in csv.reader(f):
            weekly.setdefault(s, []).append((wk, int(u)))

    # 관심 고객의 과거 스토어 이력 (최근 45일 조회자, 이력은 오늘 이전 전체)
    structs = []
    for t in targets:
        brand = t.data["intervention"].get("brand_name") or t.data["entities"].get("brand_key", "")
        toks = [x for x in re.split(r"[\s(/·×xX&,+-]+", brand) if len(x) >= 2][:2]
        pat = "|".join(re.escape(x) for x in toks) or "___none___"
        structs.append(f'STRUCT("{t.record_id}" AS code, r"{pat}" AS pat)')
    start = (datetime.date.today() - datetime.timedelta(days=45)).strftime("%Y%m%d")
    rows = bq_csv(f'''WITH t AS (SELECT * FROM UNNEST([{",".join(structs)}])),
ev AS (SELECT event_date, user_pseudo_id u,
        CAST((SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key="store_idx") AS STRING) s,
        (SELECT ep.value.string_value FROM UNNEST(event_params) ep WHERE ep.key="page_title") pt
       FROM `sweetspot-popga-ga-prd.analytics_449717889.events_*`
       WHERE event_name="view_store" AND _TABLE_SUFFIX >= "20251001"),
pv AS (SELECT t.code, ev.u FROM t JOIN ev ON REGEXP_CONTAINS(ev.pt, t.pat) AND ev.event_date >= "{start}" GROUP BY 1,2)
SELECT pv.code, ev.s, COUNT(DISTINCT pv.u) v FROM pv JOIN ev ON ev.u = pv.u
WHERE ev.s IS NOT NULL GROUP BY 1,2 HAVING v >= 2''')
    hist = {}
    for code, s, v in rows:
        hist.setdefault(code, []).append((s, int(v)))

    this_wk = datetime.date.today().strftime("%Y-%W")
    state = {}
    for t in targets:
        h = [(s, v) for s, v in hist.get(t.record_id, []) if s in idx]
        if not h:
            continue
        coord = np.average([emb[idx[s]] for s, _ in h], axis=0, weights=[v for _, v in h])
        coord /= (np.linalg.norm(coord) + 1e-9)
        sims = emb @ coord
        neigh = []
        for i in np.argsort(-sims):
            s = stores[i]
            wkly = [(w, u) for w, u in weekly.get(s, []) if w < this_wk]
            if not wkly or sum(u for _, u in wkly) < 30:
                continue
            pw, pu = max(wkly, key=lambda x: x[1])
            neigh.append({"store": s, "sim": round(float(sims[i]), 3), "title": meta.get(s, s)[:40],
                           "total_viewers": sum(u for _, u in wkly), "peak_weekly_viewers": pu, "peak_week": pw})
            if len(neigh) >= 8:
                break
        state[t.record_id] = {
            "latent_neighbors": neigh,
            "coordinate_basis": f"최근 45일 관심 고객 {sum(v for _, v in h)}명의 과거 조회 이력 가중 좌표",
        }
    return state


def main() -> int:
    codes = sys.argv[1].split(",")
    out = Path(sys.argv[2])
    state = build_state(codes)
    out.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    print(f"잠재 상태 생성: {len(state)}/{len(codes)}건 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
