# 1036 — HPLT parquet 에서 «실제 본문»을 꺼내 문서id 로 이어 붙인다.
import pyarrow.parquet as pq, glob, gzip, json, os, sys, time
OUT="/Users/ax/wm_harvest/foundation/textfix1036"
want=set()
for l in gzip.open('/Users/ax/world_model/data/ingest/sao973_hplt/pairs.jsonl.gz','rt',encoding='utf-8'):
    want.add(json.loads(l)['a_액션']['문서id'])
sys.stderr.write(f"찾을 문서 {len(want):,}\n")
found={}; t0=time.time()
files=sorted(glob.glob('/Users/ax/world_model/data/ingest/hplt_ko/*.parquet'))
for n,p in enumerate(files):
    try:
        f=pq.ParquetFile(p)
        for rg in range(f.metadata.num_row_groups):
            t=f.read_row_groups([rg],columns=['id','text'])
            ids=t.column('id').to_pylist()
            for i,d in enumerate(ids):
                if d in want and d not in found:
                    found[d]=t.column('text')[i].as_py() or ""
    except Exception as e:
        sys.stderr.write(f"🔴 {os.path.basename(p)} 실패: {e}\n")
    if (n+1)%20==0:
        sys.stderr.write(f"  [{n+1}/{len(files)}] 찾음 {len(found):,}/{len(want):,} · {time.time()-t0:.0f}s\n"); sys.stderr.flush()
    if len(found)==len(want): 
        sys.stderr.write(f"  전부 찾음 — {n+1} 파일에서 중단\n"); break
with gzip.open(f"{OUT}/doc_text.jsonl.gz","wt",encoding="utf-8") as w:
    for d,tx in found.items(): w.write(json.dumps({"문서id":d,"text":tx},ensure_ascii=False)+"\n")
import statistics as st
L=[len(v) for v in found.values()]
rep={"찾을 문서":len(want),"찾은 문서":len(found),"못 찾음":len(want)-len(found),
     "본문 길이 중앙":st.median(L) if L else 0,"평균":round(st.mean(L),1) if L else 0,
     "최대":max(L) if L else 0,"빈 본문":sum(1 for x in L if x==0),
     "스캔 파일":n+1,"초":round(time.time()-t0,1)}
json.dump(rep,open(f"{OUT}/extract_report.json","w"),ensure_ascii=False,indent=1)
print(json.dumps(rep,ensure_ascii=False))
