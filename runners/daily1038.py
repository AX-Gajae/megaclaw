# 1038-라 — 검정력 수리: 프로젝트 단위(104) → «일 단위»(558). 표적·기준선·자 계보는 그대로.
# 🔴 붓스트랩은 «프로젝트» 클러스터로 — 같은 팝업의 날들은 독립이 아니다.
import json,glob,os,re,numpy as np,datetime as dt
from collections import Counter
np.seterr(all="ignore")
ART="/Users/ax/wm_harvest/foundation"
bf={}
for l in open(f"{ART}/brandfeat1038.jsonl",encoding='utf-8'):
    try:
        d=json.loads(l)
        if d.get('code') and '오류' not in d: bf[d['code']]=d
    except Exception: pass
rows=[]
for p in sorted(glob.glob('data/records/*.json')):
    try: d=json.load(open(p,encoding='utf-8'))
    except Exception: continue
    code=os.path.basename(p)[:-5]
    o=d.get('outcome') or {}
    dl=[r for r in (o.get('daily') or []) if isinstance(r,dict) and r.get('visitors') is not None]
    if not dl: continue
    cd=d.get('conditions') or {}; iv=d.get('intervention') or {}
    dl=sorted(dl,key=lambda r:str(r.get('date') or ''))
    for i,r in enumerate(dl):
        v=float(r['visitors'])
        if v<=0: continue
        rows.append({'code':code,'day':i+1,'ndays':len(dl),'date':str(r.get('date') or ''),
                     'v':v,'cond':cd,'iv':iv})
print(f"일별 행 {len(rows):,} · 프로젝트 {len({r['code'] for r in rows})}")
y=np.log(np.array([r['v'] for r in rows])); n=len(rows)
grp=np.array([r['code'] for r in rows])
loc=lambda r:(r['cond'].get('location') or {})
def onehot(fn,k,tag):
    vals=[fn(r) for r in rows]; top=[x for x,_ in Counter([v for v in vals if v]).most_common(k)]
    M=np.zeros((n,len(top)))
    for i,v in enumerate(vals):
        if v in top: M[i,top.index(v)]=1
    return M,[f"{tag}={t}" for t in top]
cols=[];names=[]
# 🔴 일별 «곡선 모양» — 이게 새로 생긴 신호다
d1=np.array([r['day'] for r in rows],dtype=float); nd=np.array([r['ndays'] for r in rows],dtype=float)
cols.append(np.c_[np.log(d1), d1/nd, (d1==1).astype(float), (d1==nd).astype(float), np.log(nd)])
names+=['log(몇일차)','진행률','첫날','마지막날','log(총일수)']
def dow(r):
    try: return dt.date.fromisoformat(r['date'][:10]).weekday()
    except Exception: return -1
W=np.array([dow(r) for r in rows])
M=np.zeros((n,7))
for i,w in enumerate(W):
    if w>=0: M[i,w]=1
cols.append(M); names+=[f'요일{i}' for i in range(7)]
cols.append(((W>=5).astype(float))[:,None]); names.append('주말')
for fn,k,tag in ((lambda r:(loc(r).get('venue_type') or '').split('(')[0].strip(),3,'장소'),
                 (lambda r: loc(r).get('city'),2,'도시')):
    M,nm=onehot(fn,k,tag); cols.append(M); names+=nm
mon=np.array([int((r['date'][5:7]) if len(r['date'])>=7 and r['date'][5:7].isdigit() else 6) for r in rows])
cols.append(np.c_[np.sin(2*np.pi*mon/12),np.cos(2*np.pi*mon/12)]); names+=['월sin','월cos']
rec=np.array([float(bf.get(r['code'],{}).get('인지도') or 3) for r in rows])
miss=np.array([0.0 if r['code'] in bf else 1.0 for r in rows])
ip=np.array([1.0 if bf.get(r['code'],{}).get('유명IP결합') else 0.0 for r in rows])
ex=np.array([1.0 if bf.get(r['code'],{}).get('체험형') else 0.0 for r in rows])
cols.append(np.c_[rec,miss,ip,ex]); names+=['인지도','인지도결측','유명IP','체험형']
M,nm=onehot(lambda r: bf.get(r['code'],{}).get('카테고리'),4,'카테고리'); cols.append(M); names+=nm
X=np.hstack(cols); assert np.isfinite(X).all()
print(f"특징 {X.shape[1]}")
def l1fit(Z,yy,lam,it=60):
    w=np.linalg.solve(Z.T@Z+lam*np.eye(Z.shape[1]),Z.T@yy)
    for _ in range(it):
        wt=1/np.maximum(np.abs(Z@w-yy),0.05)
        try: w2=np.linalg.solve((Z*wt[:,None]).T@Z+lam*np.eye(Z.shape[1]),(Z*wt[:,None]).T@yy)
        except Exception: break
        if not np.isfinite(w2).all(): break
        if np.abs(w2-w).max()<1e-8: return w2
        w=w2
    return w
# 🔴 프로젝트 단위 LOO — 같은 팝업이 train/test 에 걸치면 누수다
codes=sorted(set(grp))
def loo_proj(lam):
    p=np.zeros(n)
    for c in codes:
        te=grp==c; tr=~te
        mu=X[tr].mean(0); sd=X[tr].std(0); k=sd>1e-8
        Z=np.c_[(X[:,k]-mu[k])/sd[k],np.ones(n)]
        p[te]=Z[te]@l1fit(Z[tr],y[tr],lam)
    return p
best=None
for lam in (5,15,40,100,250):
    p=loo_proj(lam); e=np.abs(p-y).mean()
    if best is None or e<best[0]: best=(e,p,lam)
mae,pred,lam=best
base=np.zeros(n)
for c in codes: base[grp==c]=np.median(y[grp!=c])
e_m=np.abs(pred-y); e_b=np.abs(base-y)
print(f"\n[프로젝트 단위 LOO · 일별 행 채점]")
print(f"  기준선(중앙값)  log MAE {e_b.mean():.4f}  ×2 이내 {100*np.mean(e_b<np.log(2)):.1f}%")
print(f"  모형(λ={lam:g})     log MAE {e_m.mean():.4f}  ×2 이내 {100*np.mean(e_m<np.log(2)):.1f}%")
rng=np.random.default_rng(10384); C=np.array(codes)
idx={c:np.where(grp==c)[0] for c in codes}
d=[]
for _ in range(4000):
    sel=np.concatenate([idx[c] for c in rng.choice(C,len(C))])
    d.append(e_m[sel].mean()-e_b[sel].mean())
d=np.array(d); lo,hi=np.percentile(d,[2.5,97.5])
v='✅ 모형이 낫다(0 배제)' if hi<0 else ('🔴 이 자를 못 넘었다' if lo<=0<=hi else '🔴 기준선이 낫다')
print(f"  Δ {d.mean():+.4f}  SE {d.std():.4f}  CI95 [{lo:+.4f},{hi:+.4f}]  → {v}")
mu=X.mean(0);sd=X.std(0);k=sd>1e-8
Z=np.c_[(X[:,k]-mu[k])/sd[k],np.ones(n)]; w=l1fit(Z,y,lam)
nk=[nm for nm,kk in zip(names,k) if kk]
print("\n[계수 상위12]")
for i in np.argsort(-np.abs(w[:-1]))[:12]: print(f"   {w[i]:+.3f}  ×{np.exp(w[i]):.2f}  {nk[i]}")
json.dump({"n행":n,"n프로젝트":len(codes),"lam":lam,
  "logMAE":{"기준선":float(e_b.mean()),"모형":float(e_m.mean())},
  "×2이내":{"기준선":float(np.mean(e_b<np.log(2))),"모형":float(np.mean(e_m<np.log(2)))},
  "Δ":float(d.mean()),"SE":float(d.std()),"CI95":[float(lo),float(hi)],"판정":v},
  open(f"{ART}/daily1038.json","w"),ensure_ascii=False,indent=1)
