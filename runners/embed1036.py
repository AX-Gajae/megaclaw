# 1036 — «실제 본문» 임베딩. 규약은 기존과 같되 두 가지만 바꾼다:
#   ① 입력 = 메타데이터 문자열 → «문서 본문»
#   ② 최대 토큰 = 96 → 512
import json,gzip,os,sys,time
import numpy as np, torch
from transformers import AutoTokenizer, AutoModel
OUT="/Users/ax/wm_harvest/foundation/textfix1036"
SNAP=os.environ.get("WM_SNAP","/Users/ax/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B/snapshots/060db6499f32faf8b98477b0a26969ef7d8b9987")
MAXTOK=int(os.environ.get("WM_MAXTOK","512")); CHARS=int(os.environ.get("WM_CHARS","3000"))
BATCH=int(os.environ.get("WM_BATCH","8")); DEV=os.environ.get("WM_DEV","mps")
rows=json.load(open(f"{OUT}/row_docid.json"))
txt={}
for l in gzip.open(f"{OUT}/doc_text.jsonl.gz","rt",encoding="utf-8"):
    d=json.loads(l); txt[d["문서id"]]=d["text"]
docs=sorted({r["문서id"] for r in rows})
miss=[d for d in docs if d not in txt or not txt[d].strip()]
sys.stderr.write(f"고유문서 {len(docs):,} · 본문 없음 {len(miss):,}\n")
tok=AutoTokenizer.from_pretrained(SNAP)
model=AutoModel.from_pretrained(SNAP, torch_dtype=torch.float32).to(DEV).eval()
E={}; t0=time.time()
with torch.no_grad():
    for i in range(0,len(docs),BATCH):
        chunk=docs[i:i+BATCH]
        texts=[(txt.get(d,"") or " ")[:CHARS] for d in chunk]
        enc=tok(texts,padding=True,truncation=True,max_length=MAXTOK,return_tensors="pt").to(DEV)
        h=model(**enc).last_hidden_state
        m=enc["attention_mask"].unsqueeze(-1).float()
        v=((h*m).sum(1)/m.sum(1).clamp(min=1)).float().cpu().numpy()
        for d,vec in zip(chunk,v): E[d]=vec
        if (i//BATCH)%80==0:
            sys.stderr.write(f"  {i:,}/{len(docs):,} · {time.time()-t0:.0f}s\n"); sys.stderr.flush()
dim=len(next(iter(E.values())))
M=np.zeros((len(rows),dim),dtype=np.float32)
for k,r in enumerate(rows):
    if r["문서id"] in E: M[k]=E[r["문서id"]]
np.savez_compressed(f"{OUT}/text_emb_body512.npz", E=M)
rep={"모델":SNAP.split('/')[-3],"최대토큰":MAXTOK,"최대글자":CHARS,"장치":DEV,
     "고유문서":len(docs),"본문없음":len(miss),"형상":list(M.shape),
     "영벡터 행":int((np.abs(M).sum(1)==0).sum()),"초":round(time.time()-t0,1)}
json.dump(rep,open(f"{OUT}/embed_report.json","w"),ensure_ascii=False,indent=1)
print(json.dumps(rep,ensure_ascii=False))
