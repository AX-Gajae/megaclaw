"""노트 812 측정 — 시장팝업 trend 3열: 없이 / 진짜 / 위약 6."""
import json, sys, time
import numpy as np
sys.path.insert(0,"/Users/ax/world_model")
sys.path.insert(0,"/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
from lab import trendaxes as TX
TX.FILE = dict(TX.FILE); TX.FILE["시장팝업"] = "market_trend"   # 메모리 패치
for fn in ("_read","_ids","build"):
    try: getattr(TX, fn).cache_clear()
    except Exception: pass
import ff753 as FF
from lab import forms
from lab.harness import evaluate, Data
CLS=forms.REGISTRY["F18_bagboost"]["cls"]; SEEDS=(0,1,2); T=2025.0; DOM="시장팝업"
TR=["trend_level","trend_momentum","trend_volatility"]
def board(data):
    vals,per=[],{}
    for s in SEEDS:
        sc=evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc,T=T)))
        for k,v in sc.items():
            if np.isfinite(v): per.setdefault(k,[]).append(float(v))
    return {"판":round(float(np.mean(vals)),4),
            "도메인":{k:round(float(np.mean(a)),4) for k,a in per.items()}}
def main():
    t0=time.time()
    d1=FF.shell(FF.base())
    names=list(d1.names[DOM]); A,M,y,t=d1.dom[DOM]
    idx=[names.index(c) for c in TR if c in names]
    cov={names[i]: round(float(M[:,i].mean()),3) for i in idx}
    print(json.dumps({"배선": {"trend 덮음": cov, "전체 덮음": round(float(M.mean()),3)}},ensure_ascii=False),flush=True)
    if not any(cov.get(c,0)>0.05 for c in TR):
        print(json.dumps({"중단":"trend 가 안 살았다"},ensure_ascii=False),flush=True); return
    def kill(data):
        dom=dict(data.dom); A2,M2,y2,t2=dom[DOM]; A2=A2.copy(); M2=M2.copy()
        for i in idx: A2[:,i]=0.5; M2[:,i]=0.0
        dom[DOM]=(A2,M2,y2,t2); return Data(dom,data.names,data.yr)
    def shuf(data,seed):
        dom=dict(data.dom); A2,M2,y2,t2=dom[DOM]; A2=A2.copy(); M2=M2.copy()
        rng=np.random.default_rng(seed); perm=rng.permutation(len(A2))
        for i in idx: A2[:,i]=A2[perm,i]; M2[:,i]=M2[perm,i]   # 관측 무늬도 행째 이동
        dom[DOM]=(A2,M2,y2,t2); return Data(dom,data.names,data.yr)
    b0=board(kill(d1)); print(f"[없이] 판 {b0['판']} · {DOM} {b0['도메인'].get(DOM)} · {round(time.time()-t0,1)}초",flush=True)
    b1=board(d1); print(f"[진짜] 판 {b1['판']} · {DOM} {b1['도메인'].get(DOM)}",flush=True)
    pv=[]
    for i in range(6):
        bp=board(shuf(d1,8120+i)); pv.append(bp["도메인"].get(DOM,np.nan))
        print(f"[위약 {i}] {pv[-1]}",flush=True)
    pv=np.array(pv,float); sig=float(b1["도메인"][DOM]-np.nanmean(pv)); psd=float(np.nanstd(pv,ddof=1))
    thr=max(0.0233, 2*psd)
    verdict=("모" if (np.nanmax(pv)-np.nanmin(pv))>3*abs(sig) and abs(sig)<thr
             else "좋" if sig>thr and b1["도메인"][DOM]>np.nanmax(pv)
             else "해" if sig<-thr else "없")
    print("=== 모아서 ===",flush=True)
    print(json.dumps({"없이":b0["도메인"].get(DOM),"진짜":b1["도메인"].get(DOM),
      "위약 6":[round(float(x),4) for x in pv],"위약 평균":round(float(np.nanmean(pv)),4),
      "뽑기 SD":round(psd,5),"신호 몫":round(sig,4),"순효과":round(float(b1["도메인"][DOM]-b0["도메인"][DOM]),4),
      "문턱":round(thr,4),"판 변화":round(float(b1["판"]-b0["판"]),4),
      "**판정**":verdict,"초":round(time.time()-t0,1)},ensure_ascii=False,indent=1),flush=True)
main()
