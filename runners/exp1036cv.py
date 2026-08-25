# 1036-나 — 검정력 수리: 단일 val(문서 104) → 10겹 교차검증(문서 485). 자료·라벨·팔은 «무변경».
import json,numpy as np,hashlib
np.seterr(all="ignore")
OUT="/Users/ax/wm_harvest/foundation/textfix1036"; TRI="/Users/ax/wm_harvest/foundation/triples"
z=np.load(f"{TRI}/sao.npz"); rows=json.load(open(f"{OUT}/row_docid.json"))
doms=json.load(open(f"{TRI}/domains.json",encoding="utf-8"))
S=np.log1p(z["S"].astype(np.float64)); O=np.log1p(z["O"].astype(np.float64))
base=np.median(S,axis=1,keepdims=True); Sc=S-base
y=((O-base).max(axis=1)>=np.log(3)).astype(int)
dom,year,doy=z["dom_id"],z["year"].astype(np.float64),z["doy"].astype(np.float64)
DOM=np.zeros((len(S),len(doms))); DOM[np.arange(len(S)),dom]=1
C=np.c_[DOM,np.sin(2*np.pi*doy/365),np.cos(2*np.pi*doy/365),(year-2013)/10,base]
def hb(s): return int(hashlib.md5(str(s).encode()).hexdigest()[:8],16)%10
grp=np.array([hb(r["문서"]) for r in rows]); docs=np.array([r["문서"] for r in rows])
Eb=np.load(f"{TRI}/text_emb_qwen05b.npz")["E"].astype(np.float64)
Ec=np.load(f"{OUT}/text_emb_body512.npz")["E"].astype(np.float64)
def logit(X,idx_tr,lam):
    mu=X[idx_tr].mean(0); sd=X[idx_tr].std(0); k=sd>1e-8
    Z=np.c_[(X[:,k]-mu[k])/sd[k],np.ones(len(X))]; w=np.zeros(Z.shape[1])
    for _ in range(60):
        p=np.clip(1/(1+np.exp(-Z[idx_tr]@w)),1e-9,1-1e-9)
        g=Z[idx_tr].T@(p-y[idx_tr])+lam*w
        H=Z[idx_tr].T@(Z[idx_tr]*(p*(1-p))[:,None])+lam*np.eye(Z.shape[1])
        try: st=np.linalg.solve(H,g)
        except Exception: break
        w-=st
        if np.abs(st).max()<1e-7: break
    return Z@w
def auc(t,s):
    o=np.argsort(s); t=t[o]; n1=t.sum(); n0=len(t)-n1
    return np.nan if n1==0 or n0==0 else (np.arange(1,len(t)+1)[t==1].sum()-n1*(n1+1)/2)/(n1*n0)
def p_at(t,s,f=.10):
    k=max(1,int(len(t)*f)); return t[np.argsort(-s)[:k]].mean()
ARMS={"ⓐ 곡선만":np.c_[Sc,C],"ⓑ 메타데이터 96토큰":np.c_[Sc,C,Eb],"ⓒ 실제 본문 512토큰":np.c_[Sc,C,Ec]}
LAM={"ⓐ 곡선만":1.0,"ⓑ 메타데이터 96토큰":10.0,"ⓒ 실제 본문 512토큰":100.0}   # 1036-가 에서 고른 값 고정
oof={}
for name,X in ARMS.items():
    s=np.zeros(len(y))
    for b in range(10):
        te=np.where(grp==b)[0]; tr=np.where(grp!=b)[0]
        s[te]=logit(X,tr,LAM[name])[te]
    oof[name]=s
print(f"전 행 {len(y):,} · 고유 문서 {len(set(docs)):,} · 사건 기저율 {100*y.mean():.1f}%")
print(f"\n{'팔':<22}{'AUC':>8}{'P@10%':>9}{'배수':>7}")
for n,s in oof.items(): print(f"{n:<22}{auc(y,s):>8.4f}{p_at(y,s):>9.4f}{p_at(y,s)/y.mean():>7.2f}×")
rng=np.random.default_rng(10362); ud=np.array(sorted(set(docs)))
idx={d:np.where(docs==d)[0] for d in ud}
def boot(f,B=4000):
    out=[]
    for _ in range(B):
        sel=np.concatenate([idx[t] for t in rng.choice(ud,len(ud))])
        if y[sel].sum()==0 or y[sel].sum()==len(sel): continue
        out.append(f(sel))
    return np.array(out)
print(f"\n[붓스트랩 4,000 · 문서 클러스터 {len(ud)}개 · seed 10362]")
for n in oof:
    d=boot(lambda sel,n=n: auc(y[sel],oof[n][sel]))
    lo,hi=np.percentile(d,[2.5,97.5])
    print(f"  {n:<22} AUC {d.mean():.4f}  SE {d.std():.4f}  CI95 [{lo:.4f},{hi:.4f}]  {'✅ 0.5 초과' if lo>0.5 else '🔴 0.5 포함'}")
print()
for A,B in (("ⓒ 실제 본문 512토큰","ⓑ 메타데이터 96토큰"),("ⓒ 실제 본문 512토큰","ⓐ 곡선만"),("ⓑ 메타데이터 96토큰","ⓐ 곡선만")):
    d=boot(lambda sel,A=A,B=B: auc(y[sel],oof[A][sel])-auc(y[sel],oof[B][sel]))
    lo,hi=np.percentile(d,[2.5,97.5])
    print(f"  {A[:1]} − {B[:1]}   Δ={d.mean():+.4f}  SE {d.std():.4f}  CI95 [{lo:+.4f},{hi:+.4f}]  {'   0 배제' if not(lo<=0<=hi) else '🔴 0 포함 — 못 갈랐다'}")
print(f"\n  ▶ 이 자의 MDE(2SE) ≈ {2*boot(lambda sel: auc(y[sel],oof['ⓒ 실제 본문 512토큰'][sel])-auc(y[sel],oof['ⓑ 메타데이터 96토큰'][sel])).std():.4f} AUC")
