# -*- coding: utf-8 -*-
"""1037 A부 배선 ① — sao973 26,364 문서의 WARC 좌표(f·o·s·rs·u·ts·collection) 색출.

HPLT parquet 464 샤드를 훑어 표적 문서 id 만 골라 좌표를 적는다. 측정 아님(배선).
"""
import json, gzip, os, sys, time, collections
from pathlib import Path
os.environ.setdefault("OMP_NUM_THREADS", "4")
import pyarrow.parquet as pq
import pyarrow as pa
pa.set_cpu_count(4)

ROOT = Path("/Users/ax/world_model")
OUT = Path("/Users/ax/wm_harvest/foundation/warc1037")
OUT.mkdir(parents=True, exist_ok=True)

want = {}
with gzip.open(ROOT / "data/ingest/sao973_hplt/pairs.jsonl.gz", "rt") as f:
    for line in f:
        a = json.loads(line)["a_액션"]
        want[a["문서id"]] = a.get("collection")
print(f"표적 문서 {len(want):,}", flush=True)

found = {}
t0 = time.time()
shards = sorted((ROOT / "data/ingest/hplt_ko").glob("train-*.parquet"))
COLS = ["id", "f", "o", "s", "rs", "u", "ts", "collection"]
for i, sh in enumerate(shards):
    pf = pq.ParquetFile(sh)
    for b in pf.iter_batches(batch_size=20000, columns=COLS):
        d = b.to_pydict()
        for j, did in enumerate(d["id"]):
            if did in want and did not in found:
                found[did] = {
                    "문서id": did, "f": d["f"][j], "o": d["o"][j], "s": d["s"][j],
                    "rs": d["rs"][j], "u": d["u"][j],
                    "ts": str(d["ts"][j]), "collection": d["collection"][j],
                }
    if (i + 1) % 20 == 0 or len(found) == len(want):
        print(f"  [{i+1}/{len(shards)}] {len(found):,}/{len(want):,} · {time.time()-t0:.0f}s", flush=True)
    if len(found) == len(want):
        print("전부 찾음 — 중단", flush=True)
        break

with gzip.open(OUT / "warc_coords.jsonl.gz", "wt") as f:
    for v in found.values():
        f.write(json.dumps(v, ensure_ascii=False) + "\n")

miss = [d for d in want if d not in found]
rep = {
    "표적": len(want), "좌표 찾음": len(found), "못 찾음": len(miss),
    "스캔 샤드": i + 1, "초": round(time.time() - t0, 1),
    "collection 별": dict(collections.Counter(v["collection"] for v in found.values())),
    "f 날짜 접두": dict(collections.Counter(v["f"].split("CC-MAIN-")[-1][:6] for v in found.values() if "CC-MAIN-" in v["f"]).most_common()),
    "f 비CC 예": [v["f"] for v in found.values() if "CC-MAIN-" not in v["f"]][:5],
}
(OUT / "scan_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(rep, ensure_ascii=False, indent=1), flush=True)
