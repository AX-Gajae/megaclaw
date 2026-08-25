# 1038-나 — 자 수리: 채점이 MAE 이므로 «중앙값 회귀»(L1)로 적합한다. 특징도 줄인다.
import json,glob,os,re,numpy as np
from collections import Counter
np.seterr(all="ignore")
R=[]
for p in sorted(glob.glob('data/records/*.json')):
    try: d=json.load(open(p,encoding='utf-8'))
    except Exception: continue
    o=d.get('outcome') or {}; t=o.get('totals') or {}
    dl=[r for r in (o.get('daily') or []) if isinstance(r,dict) and r.get('visitors') is not None]
    per=(d.get('conditions') or {}).get('period') or {}
    if dl: v=sum(float(r['visitors']) for r in dl); days=len(dl)
    elif t.get('visitors') is not None: v=float(t['visitors']); days=per.get('days')
    else: continue
    if not v or not days or v<=0: continue
    R.append((os.path.basename(p)[:-5],d,v,float(days)))
y=np.log(np.array([v/dd for _,_,v,dd in R])); n=len(R)
loc=lambda d:(d.get('conditions') or {}).get('location') or {}
per=lambda d:(d.get('conditions') or {}).get('period') or {}
iv =lambda d: d.get('intervention') or {}
def onehot(f,topk):
    vals=[f(d) for _,d,_,_ in R]
    top=[k for k,_ in Counter([v for v in vals if v]).most_common(topk)]
    M=np.zeros((n,len(top)))
    for i,v in enumerate(vals):
        if v in top: M[i,top.index(v)]=1
    return M,top
# 🔴 특징을 «적게» — n=104
cols=[];names=[]
days=np.array([dd for _,_,_,dd in R]); cols.append(np.log(days)[:,None]); names.append('log(운영일수)')
M,t=onehot(lambda d:(loc(d).get('venue_type') or '').split('(')[0].strip(),3); cols.append(M); names+=[f'장소={x[:10]}' for x in t]
M,t=onehot(lambda d:loc(d).get('city'),2); cols.append(M); names+=[f'도시={x}' for x in t]
mon=np.array([int((per(d).get('from') or '2020-01-01')[5:7]) for _,d,_,_ in R])
cols.append(np.c_[np.sin(2*np.pi*mon/12),np.cos(2*np.pi*mon/12)]); names+=['월sin','월cos']
tags=[' '.join((iv(d).get('staging_tags') or [])) for _,d,_,_ in R]
TOP=[t for t,_ in Counter(re.findall(r'[가-힣A-Za-z/]+',' '.join(tags))).most_common(4)]
cols.append(np.array([[1.0 if t in tg else 0.0 for t in TOP] for tg in tags])); names+=[f'태그:{t}' for t in TOP]
X=np.hstack(cols); print(f"표본 {n} · 특징 {X.shape[1]}개 (41 → {X.shape[1]})")
def l1fit(Z,yy,lam,iters=60):
    w=np.linalg.solve(Z.T@Z+lam*np.eye(Z.shape[1]),Z.T@yy)
    for _ in range(iters):
        r=np.abs(Z@w-yy); wt=1.0/np.maximum(r,0.05)
        A=(Z*wt[:,None]).T@Z+lam*np.eye(Z.shape[1]); b=(Z*wt[:,None]).T@yy
        try: w2=np.linalg.solve(A,b)
        except Exception: break
        if np.abs(w2-w).max()<1e-8: w=w2; break
        w=w2
    return w
def loo(fitfn):
    p=np.zeros(n)
    for i in range(n):
        m=np.ones(n,bool); m[i]=False
        mu=X[m].mean(0); sd=X[m].std(0); k=sd>1e-8
        Z=np.c_[(X[:,k]-mu[k])/sd[k],np.ones(n)]
        p[i]=Z[i]@fitfn(Z[m],y[m])
    return p
base_med=np.array([np.median(np.delete(y,i)) for i in range(n)])
base_mean=np.array([np.mean(np.delete(y,i)) for i in range(n)])
best=None
for lam in (5,15,40,100,250,600):
    p=loo(lambda Z,yy,l=lam: l1fit(Z,yy,l)); e=np.abs(p-y).mean()
    if best is None or e<best[0]: best=(e,p,lam)
mae,pred,lam=best
def rep(nm,p):
    e=np.abs(p-y); print(f"  {nm:<22} log MAE {e.mean():.4f}   ×2 이내 {100*np.mean(e<np.log(2)):>5.1f}%   중앙오차 ×{np.exp(np.median(e)):.2f}")
    return e
print("\n[LOO · 자 수리 후]")
e0=rep("ⓐ 전체 중앙값",base_med); em=rep("ⓐ' 전체 평균",base_mean); e2=rep(f"ⓒ L1 회귀(λ={lam:g})",pred)
rng=np.random.default_rng(10382)
def boot(a,b,B=4000):
    d=np.array([ (a[s].mean()-b[s].mean()) for s in (rng.integers(0,n,n) for _ in range(B))])
    return d.mean(),d.std(),np.percentile(d,2.5),np.percentile(d,97.5)
print("\n[붓스트랩 4,000 · 음수 = 모형이 낫다]")
for nm,a,b in (("ⓒ − ⓐ(중앙값)",e2,e0),):
    m,s,lo,hi=boot(a,b)
    v='✅ 모형이 낫다(0 배제)' if hi<0 else ('🔴 0 포함 — 이 자를 못 넘었다' if lo<=0<=hi else '🔴 기준선이 낫다')
    print(f"  {nm}  Δ {m:+.4f}  SE {s:.4f}  CI95 [{lo:+.4f},{hi:+.4f}]  {v}")
mu=X.mean(0);sd=X.std(0);k=sd>1e-8
Z=np.c_[(X[:,k]-mu[k])/sd[k],np.ones(n)]; w=l1fit(Z,y,lam)
nk=[nm for nm,kk in zip(names,k) if kk]
print("\n[계수 — 일평균 방문자에 대한 효과(log)]")
for i in np.argsort(-np.abs(w[:-1])): print(f"   {w[i]:+.3f}  ×{np.exp(w[i]):.2f}  {nk[i]}")
np.savez('/Users/ax/wm_harvest/foundation/base1038.npz',w=w,mu=mu,sd=sd,k=k,y=y,pred=pred)
json.dump({"n":n,"특징":nk,"lam":lam,"logMAE":{"중앙값":float(e0.mean()),"평균":float(em.mean()),"모형":float(e2.mean())},
           "×2이내":{"중앙값":float(np.mean(e0<np.log(2))),"모형":float(np.mean(e2<np.log(2)))}},
          open('/Users/ax/wm_harvest/foundation/base1038.json','w'),ensure_ascii=False,indent=1)
