import json,numpy as np,os,re,hashlib,warnings
from collections import Counter
np.seterr(all="ignore")  # Accelerate 가짜 플래그 — 대신 아래에서 유한성을 «검사»한다
SN=os.path.join(os.path.dirname(os.path.abspath(__file__)),"snap")
z=np.load(os.path.join(SN,"sao.npz"))
meta=[json.loads(l) for l in open(os.path.join(SN,"meta.jsonl"),encoding="utf-8")]
doms=json.load(open(os.path.join(SN,"domains.json"),encoding="utf-8"))
S=np.log1p(z["S"].astype(np.float64));O=np.log1p(z["O"].astype(np.float64))
base=S.mean(1,keepdims=True);Sc=S-base;R=O-base
dom,year,doy=z["dom_id"],z["year"].astype(np.float64),z["doy"].astype(np.float64)
T=[m["텍스트"] for m in meta];host=[];coll=[];title=[]
for t in T:
    p=[x.strip() for x in t.split("·")]
    h=[x for x in p if re.fullmatch(r"[a-z0-9.\-]+\.[a-z]{2,}",x)]
    c=[x for x in p if re.fullmatch(r"cc\d\d|[a-z]{2,}\d{2,}",x)]
    host.append(h[0] if h else "?");coll.append(c[0] if c else "?");title.append(max(p,key=len))
def hb(s):return int(hashlib.md5(str(s).encode()).hexdigest()[:8],16)%10
grp=np.array([hb(x) for x in title]);tr=np.where(grp>=2)[0];va=np.where(grp<2)[0]
vt=np.array(title)[va]
def oh(lab,minc=1):
    c=Counter(lab);u=sorted({k for k,v in c.items() if v>=minc});ix={k:i for i,k in enumerate(u)}
    M=np.zeros((len(lab),len(u)))
    for i,l in enumerate(lab):
        if l in ix:M[i,ix[l]]=1
    return M
DOM=oh([doms[d] for d in dom]);COLL=oh(coll);HOST=oh(host,20)
SEAS=np.c_[np.sin(2*np.pi*doy/365),np.cos(2*np.pi*doy/365),(year-2013)/10,base]
def fit(X):
    mu=X[tr].mean(0);sd=X[tr].std(0)
    keep=sd>1e-8                                        # 🔴 train 에서 상수인 열은 «버린다»
    Z=(X[:,keep]-mu[keep])/sd[keep];Z=np.c_[Z,np.ones(len(Z))]
    best=None
    for lam in (10,100,1000,1e4,1e5,1e6):
        W=np.linalg.solve(Z[tr].T@Z[tr]+lam*np.eye(Z.shape[1]),Z[tr].T@R[tr])
        assert np.isfinite(W).all() and np.isfinite(Z).all(), "🔴 비유한 값"
        P=Z[va]@W;r2=1-((R[va]-P)**2).sum()/((R[va]-R[va].mean(0))**2).sum()
        if best is None or r2>best[0]:best=(r2,P,lam,keep.sum())
    return best
E={n:np.load(os.path.join(SN,f"text_emb_{n}.npz"))["E"].astype(np.float64) for n in("qwen05b","ftv1","ftv2","qwen3e4b")}
M={}
M["① 곡선만"]=fit(Sc)
M["② +현행 조건 C"]=fit(np.c_[Sc,DOM,SEAS])
M["③ ②+메타 원핫(coll·host)"]=fit(np.c_[Sc,DOM,SEAS,COLL,HOST])
for n in E: M[f"⑤ ③+E[{n}]"]=fit(np.c_[Sc,DOM,SEAS,COLL,HOST,E[n]])
print(f"train {len(tr):,} · val {len(va):,} · val 고유제목 {len(set(vt)):,}\n")
for k,(r2,P,lam,nc) in M.items(): print(f"  {k:<30} val R² {r2:+.4f}  (λ={lam:g} · 열 {nc})")
# 붓스트랩 — 제목 클러스터 재표집
rng=np.random.default_rng(1029);uts=np.array(sorted(set(vt)));idx={t:np.where(vt==t)[0] for t in uts}
def r2of(P,sel):
    y=R[va][sel];return 1-((y-P[sel])**2).sum()/((y-y.mean(0))**2).sum()
pairs=[("⑤ ③+E[qwen05b]","③ ②+메타 원핫(coll·host)"),("⑤ ③+E[ftv2]","③ ②+메타 원핫(coll·host)"),
       ("⑤ ③+E[qwen3e4b]","③ ②+메타 원핫(coll·host)"),("⑤ ③+E[qwen05b]","⑤ ③+E[ftv2]"),
       ("⑤ ③+E[qwen05b]","⑤ ③+E[qwen3e4b]"),("② +현행 조건 C","① 곡선만")]
print("\n[붓스트랩 1,000 · val 제목 클러스터 재표집 · seed 1029]")
for a,b in pairs:
    d=[]
    for _ in range(1000):
        pick=rng.choice(uts,len(uts));sel=np.concatenate([idx[t] for t in pick])
        d.append(r2of(M[a][1],sel)-r2of(M[b][1],sel))
    d=np.array(d);lo,hi=np.percentile(d,[2.5,97.5])
    star="🔴 0 포함(못 갈랐다)" if lo<=0<=hi else "   0 배제"
    print(f"  Δ({a.split('+')[-1][:14]:<14} − {b.split('+')[-1][:14]:<14}) = {d.mean():+.4f}  SE {d.std():.4f}  CI95 [{lo:+.4f},{hi:+.4f}]  {star}")
