# 노트 831 — 다년 백필(2023-01-01 ~ 2026-05-03) · 예의 1.5초 · 실패는 결측
import datetime as dt
import json, sys, time
sys.path.insert(0, "/Users/ax/world_model")
from ingest.kobis import fetch_daily, SLEEP

t0 = time.time()
start = dt.date(2023, 1, 1)
end = dt.date(2026, 5, 3)
days = []
d = start
while d <= end:
    days.append(d.isoformat())
    d += dt.timedelta(days=1)
print(f"대상 {len(days)}일", flush=True)
data, fails = {}, []
for i, ds in enumerate(days):
    try:
        rows = fetch_daily(ds)
        if rows:
            data[ds] = rows
        else:
            fails.append(ds)
    except Exception as e:
        fails.append(f"{ds}:{type(e).__name__}")
    time.sleep(SLEEP)
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(days)} · 실패 {len(fails)} ({time.time()-t0:.0f}s)", flush=True)
out = {"찍은 때": dt.datetime.now().isoformat(timespec="seconds"),
       "창": [days[0], days[-1]], "성공일": len(data), "실패": fails}
json.dump(data, open("/Users/ax/world_model/data/ingest/kobis/backfill_2023-01-01_full.json", "w"), ensure_ascii=False)
json.dump(out, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out831_backfill.json", "w"), ensure_ascii=False, indent=1)
print(f"완료 — 성공 {len(data)} · 실패 {len(fails)} · {time.time()-t0:.0f}s", flush=True)
