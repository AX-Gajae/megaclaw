"""웹툰 빠진 편 수집(노트 387) --- 원본 build 를 그대로 쓴다."""
import json,urllib.request,gzip,time,sys,os
sys.path.insert(0,".")
from ingest.webtoon_domain import build, _get, API, WEEK
CK="/Users/ax/.claude/jobs/a5c89f96/tmp/webtoon_more.jsonl"
ours=set(int(k.split("-")[-1]) for k in json.load(open("data/state/webtoon_axes.json")))
plat={}
for w in WEEK:
    d=_get(f"{API}/webtoon/titlelist/weekday?week={w}&order=user", f"wk2_{w}")
    for t in ((d or {}).get("titleList") or []): plat[t["titleId"]]=0
    time.sleep(0.2)
p=1
while True:
    d=_get(f"{API}/webtoon/titlelist/finished?page={p}&order=UPDATE", f"fin2_{p}")
    tl=(d or {}).get("titleList") or []
    if not tl: break
    for t in tl: plat.setdefault(t["titleId"],p)
    tp=((d or {}).get("pageInfo") or {}).get("totalPages") or 0
    if p>=tp: break
    p+=1; time.sleep(0.2)
miss=sorted(set(plat)-ours)
print("플랫폼 %d · 우리 %d · 빠진 것 %d"%(len(plat),len(ours),len(miss)),flush=True)
done={}
if os.path.exists(CK):
    for l in open(CK):
        try: o=json.loads(l); done[o["record_id"]]=o
        except Exception: pass
print("이어받기 %d"%len(done),flush=True)
ck=open(CK,"a",buffering=1); n=0
for tid in miss:
    rid="WT-%d"%tid
    if rid in done: continue
    r=build(tid)
    if r:
        r["_src_page"]=plat.get(tid,0)
        done[rid]=r; ck.write(json.dumps(r,ensure_ascii=False)+"\n"); ck.flush(); n+=1
        if n%50==0: print("  %d/%d"%(len(done),len(miss)),flush=True)
    time.sleep(0.2)
json.dump(done, open("data/state/webtoon_more.json","w"), ensure_ascii=False)
import numpy as np
yr=[int(v["start_date"][:4]) for v in done.values()]
print("끝: %d편 · 2025+ %d편 · 학습 갈 것 %d편"%(len(done),sum(1 for y in yr if y>=2025),sum(1 for y in yr if y<2025)),flush=True)
