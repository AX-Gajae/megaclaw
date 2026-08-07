"""노트 807 — 시장팝업 달력 축(목록 누락 수리)의 값을 잰다."""
import json, sys, time
import numpy as np
sys.path.insert(0,"/Users/ax/world_model")
sys.path.insert(0,"/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
from lab import calaxes, loop as LP
#: 🔴 메모리 패치 둘 --- 판을 짓기 **전에**(파일 안 고침)
#: ① calaxes.SPEC (한 번도 없었다) ② loop.CAL_KEEP (노트 349 의 절단 ---
#:    시장팝업은 그 측정에 없었으므로 여기 더해 재 보는 것이 곧 그 측정이다)
calaxes.SPEC["시장팝업"] = ("market_axes.json", "period_from")
LP.CAL_KEEP = tuple(LP.CAL_KEEP) + ("시장팝업",)
for fn in ("_dates", "build"):
    try:
        getattr(calaxes, fn).cache_clear()
    except Exception:
        pass
import ff753 as FF
from lab import forms
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = (0, 1, 2)
T = 2025.0
DOM = "시장팝업"
CAL = ["cal_dow_sin","cal_dow_cos","cal_weekend","cal_month_sin","cal_month_cos","cal_holiday_gap"]

def board(data):
    vals, per = [], {}
    for s in SEEDS:
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc, T=T)))
        for k,v in sc.items():
            if np.isfinite(v): per.setdefault(k,[]).append(float(v))
    return {"판": round(float(np.mean(vals)),4),
            "도메인": {k: round(float(np.mean(a)),4) for k,a in per.items()}}

def main():
    t0=time.time()
    d1 = FF.shell(FF.base())          # SPEC 패치 뒤라 cal 이 시장팝업에 산다
    names = list(d1.names[DOM]); A,M,y,t = d1.dom[DOM]
    idx=[names.index(c) for c in CAL if c in names]
    cov={names[i]: round(float(M[:,i].mean()),3) for i in idx}
    others={}
    for k in ("게임","도서"):
        Ao,Mo,_,_ = d1.dom[k]
        others[k]=round(float(Mo.mean()),4)
    print(json.dumps({"배선(진짜 판)": {"시장팝업 cal 덮음": cov,
        "시장팝업 전체 덮음": round(float(M.mean()),3),
        "다른 도메인 평균 덮음(불변 확인)": others}}, ensure_ascii=False), flush=True)
    if not all(cov.get(c,0)>0.9 for c in CAL):
        print(json.dumps({"중단":"cal 이 안 살았다"},ensure_ascii=False),flush=True); return

    # 없이 팔 --- 시장팝업 cal 을 도로 죽인다(마스크 0·값 0.5)
    def kill(data):
        import copy
        dom=dict(data.dom); A2,M2,y2,t2 = dom[DOM]
        A2=A2.copy(); M2=M2.copy()
        for i in idx: A2[:,i]=0.5; M2[:,i]=0.0
        dom[DOM]=(A2,M2,y2,t2)
        from lab.harness import Data
        return Data(dom, data.names, data.yr)
    def shuffle_arm(data, seed):
        dom=dict(data.dom); A2,M2,y2,t2=dom[DOM]
        A2=A2.copy()
        rng=np.random.default_rng(seed)
        perm=rng.permutation(len(A2))
        for i in idx: A2[:,i]=A2[perm,i]     # 행째 섞기(블록 유지 · 노트 335)
        dom[DOM]=(A2,M2,y2,t2)
        from lab.harness import Data
        return Data(dom, data.names, data.yr)

    b0=board(kill(d1));  print(f"[없이] 판 {b0['판']} · {DOM} {b0['도메인'].get(DOM)} · {round(time.time()-t0,1)}초",flush=True)
    b1=board(d1);        print(f"[진짜] 판 {b1['판']} · {DOM} {b1['도메인'].get(DOM)}",flush=True)
    pv=[]; pb=[]
    for i in range(6):
        bp=board(shuffle_arm(d1, 8070+i))
        pv.append(bp["도메인"].get(DOM,np.nan)); pb.append(bp["판"])
        print(f"[위약 {i}] {DOM} {pv[-1]}",flush=True)
    pv=np.array(pv,float)
    sig=float(b1["도메인"][DOM]-np.nanmean(pv)); psd=float(np.nanstd(pv,ddof=1))
    thr=max(0.0233, 2*psd)
    verdict=("모" if (np.nanmax(pv)-np.nanmin(pv))>3*abs(sig) and abs(sig)<thr
             else "좋" if sig>thr and b1["도메인"][DOM]>np.nanmax(pv)
             else "해" if sig<-thr else "없")
    print("=== 모아서 ===",flush=True)
    print(json.dumps({
      "없이": {"판": b0["판"], DOM: b0["도메인"].get(DOM)},
      "진짜": {"판": b1["판"], DOM: b1["도메인"].get(DOM)},
      "위약 6": [round(float(x),4) for x in pv],
      "위약 평균": round(float(np.nanmean(pv)),4), "뽑기 SD": round(psd,5),
      "**신호 몫(진짜−위약)**": round(sig,4),
      "**순효과(진짜−없이)**": round(float(b1["도메인"][DOM]-b0["도메인"][DOM]),4),
      "문턱": round(thr,4), "위약 전부보다 큰가": bool(b1["도메인"][DOM]>np.nanmax(pv)),
      "판 변화(진짜−없이)": round(float(b1["판"]-b0["판"]),4),
      "**판정**": verdict, "초": round(time.time()-t0,1)},ensure_ascii=False,indent=1),flush=True)

if __name__=="__main__":
    main()
