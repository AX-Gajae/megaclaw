"""노트 816(시간 갈림 · 사전등록 별도) — 적응 곡선(봉인 도메인 KR 만화): 몇 건이면 전이를 따라잡나."""
import json, sys, time
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0,"/Users/ax/world_model")
sys.path.insert(0,"/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import forms, guards as G, pairs as PR

t0=time.time()
data=FF.shell(FF.base())
CLS=forms.REGISTRY["F18_bagboost"]["cls"]
src=PR.SRC_DOM["KR 만화"]; names=list(data.names.get(src) or [])
A,M,y,t=PR.to_arrays(PR.build("KR 만화"), names)
X=np.nan_to_num(np.hstack([A,M,np.asarray(t,float)[:,None]]),nan=0.5)
fin=np.isfinite(y)
print(json.dumps({"배선":{"행":len(y),"y 유한":int(fin.sum()),"열":X.shape[1],
    "살아있는 축":int((M.mean(axis=0)>0).sum())}},ensure_ascii=False),flush=True)

#: 🔴 시간 갈림 --- 평가 = 2025~26 시작(고정) · 풀 = 그 이전만
years=np.array([int(str((r.get("start_date") or "0000"))[:4] or 0)
                for r in PR.build("KR 만화").values()])
ev=np.flatnonzero(fin & (years>=2025))
pool=np.flatnonzero(fin & (years<2025) & (years>0))
print(f"평가(2025~) {len(ev)} · 풀(과거) {len(pool)}",flush=True)

# 기준선: 챔피언 전이(씨앗 4~7 · 같은 500행)
ch=[]
for s in (4,5,6,7):
    f=G._fit_on(lambda s=s: CLS(seed=s), data, 2025.0, seed=s)
    p=np.asarray(f.predict(src, A[ev], M[ev], np.asarray(t,float)[ev]),float)
    ok=np.isfinite(p)
    ch.append(float(spearmanr(p[ok],y[ev][ok]).statistic))
    print(f"  전이 씨앗 {s}: {ch[-1]:+.4f} · {round(time.time()-t0,1)}초",flush=True)
CH=float(np.mean(ch)); CHSD=float(np.std(ch,ddof=1))
print(f"[전이 기준선] {CH:.4f} ± {CHSD:.4f}",flush=True)

from tabpfn import TabPFNRegressor
NS=(5,10,20,50,100,200,400,800)
curve={}
for n in NS:
    vals=[]
    for d in range(4):
        r2=np.random.default_rng(8160+10*n+d)
        pick=r2.choice(pool, size=min(n,len(pool)), replace=False)
        try:
            m=TabPFNRegressor(device="cpu", random_state=d)
            m.fit(X[pick], y[pick])
            p=np.asarray(m.predict(X[ev]),float)
            ok=np.isfinite(p)
            vals.append(float(spearmanr(p[ok],y[ev][ok]).statistic))
        except Exception as e:
            vals.append(np.nan)
            print(f"  ⛔ n={n} d={d}: {type(e).__name__}",flush=True)
    a=np.array(vals,float)
    curve[n]={"평균":round(float(np.nanmean(a)),4),"SD":round(float(np.nanstd(a,ddof=1)),4),
              "뽑기":[round(float(x),4) for x in a]}
    print(f"[n={n}] {curve[n]['평균']:+.4f} ± {curve[n]['SD']:.4f}",flush=True)

# 판정(번호 우선순위)
tgt=CH-0.025
sd800=curve[800]["SD"]
nstar=None
for n in NS:
    if curve[n]["평균"]>=tgt: nstar=n; break
if sd800>0.05: verdict="1.모"
elif nstar is not None and nstar<=20: verdict="2.즉시"
elif nstar is not None: verdict=f"3.교차 (n*={nstar})"
else: verdict="4.못 따라잡음"
print("=== 모아서 ===",flush=True)
print(json.dumps({"전이 기준선":round(CH,4),"기준선 SD":round(CHSD,4),
  "목표(전이−0.025)":round(tgt,4),"곡선":curve,"n*":nstar,
  "**판정**":verdict,"초":round(time.time()-t0,1)},ensure_ascii=False,indent=1),flush=True)
