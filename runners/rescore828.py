# 노트 828 — 정오표 재채점 (사전등록: 대장 '사전등록 828' · 자 = lab/pairboot)
import json, re, sys, time
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, guards as G, pairboot as PB
from lab.forms import REGISTRY
from lab.decay import AXD, AX

t0 = time.time()
DELTA_NI = 0.03

def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    if ok.sum() < 10:
        return np.nan
    return float(spearmanr(p[ok], yy[ok])[0])

data = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]
def titles_of(dkey):
    r = json.loads((AXD / f"{AX[dkey]}.json").read_text())
    return [v.get("name") or v.get("title") or "" for v in r.values()]

print("챔피언 씨앗 1~4 적합...", flush=True)
fits = [G._fit_on(lambda s=s: cls(seed=s), data, 2025.0, seed=s) for s in (1, 2, 3, 4)]
print(f"적합 완료 {time.time()-t0:.0f}s", flush=True)

REF827 = json.load(open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out827.json"))
DOMS = ["게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "펀딩"]
OUT = {"(a) 대 릿지": {}, "(b) 챌린저": {}, "(c) 825 부분집합": {}, "군집 병기": {}}
for d in DOMS:
    yr = np.asarray(data.yr[d], float)
    y_all = np.asarray(data.dom[d][2], float)
    ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y_all)
    kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y_all)
    if kho.sum() < 20 or ktr.sum() < 30:
        continue
    A, M, yv, tv = data.slice(d, kho)
    Atr, Mtr, ytr, ttr = data.slice(d, ktr)
    okr = np.isfinite(ytr)
    Xtr = np.nan_to_num(np.hstack([Atr, Mtr, np.asarray(ttr, float)[:, None]]), nan=0.5)[okr]
    Xho = np.nan_to_num(np.hstack([A, M, np.asarray(tv, float)[:, None]]), nan=0.5)
    best_a, best_s = None, -9
    for a in (0.1, 1.0, 10.0, 100.0, 1000.0):
        ss = []
        for tr, te in KFold(5, shuffle=True, random_state=1).split(Xtr):
            m = Ridge(alpha=a).fit(Xtr[tr], ytr[okr][tr])
            ss.append(rho(m.predict(Xtr[te]), ytr[okr][te]))
        s = float(np.nanmean(ss))
        if s > best_s:
            best_a, best_s = a, s
    p_r = Ridge(alpha=best_a).fit(Xtr, ytr[okr]).predict(Xho)
    pj = [np.asarray(f.predict(d, A, M, tv), float) for f in fits]
    ens = PB.rank_ensemble(pj)                       # 🔴 정오표 핵심 — 고정 앙상블 예측자
    if d in AX:
        tl_all = titles_of(d)
        tl = [tl_all[i] for i in np.flatnonzero(kho)] if len(tl_all) == len(y_all) else None
    else:
        tl = None
    if tl is not None:
        cl, wire = PB.clusters_of(tl)
    else:
        cl = [np.asarray([i], int) for i in range(len(yv))]
        wire = {"행": int(len(yv)), "군집": int(len(yv)), "병합": 0,
                "⚠ 무군집": "제목 원천 없음/정렬 실패 — 폭 과소 방향"}
    OUT["군집 병기"][d] = wire

    def stat(idx, ens=ens, p_r=p_r, yv=yv):
        return rho(ens[idx], yv[idx]) - rho(p_r[idx], yv[idx])

    th, lo, hi, kind = PB.cluster_boot(stat, cl, seed=827)
    v827 = REF827["(a) 대 릿지"][d]
    row = {"n": int(len(yv)), "군집": len(cl), "Δ": round(th, 4),
           "CI95": [round(lo, 4), round(hi, 4)], "종류": kind,
           "판정": {"승": "합동승", "패": "릿지승"}.get(PB.verdict(lo, hi), "판정 불능"),
           "비열등": bool(lo > -DELTA_NI),
           "827": {"Δ": v827["Δ"], "CI": v827["CI95"], "판정": v827["판정"]}}
    row["변화"] = "불변" if row["판정"] == v827["판정"] else f"뒤집힘({v827['판정']}→{row['판정']})"
    OUT["(a) 대 릿지"][d] = row
    print(f"  {d}: Δ {th:+.4f} [{lo:+.4f},{hi:+.4f}] → {row['판정']} ({row['변화']}) {time.time()-t0:.0f}s", flush=True)

    if d in ("아이돌", "시장팝업"):
        from tabpfn import TabPFNRegressor
        tb_p = []
        for s in (4, 5, 6, 7):
            m = TabPFNRegressor(device="cpu", random_state=s)
            m.fit(Xtr, ytr[okr])
            tb_p.append(np.asarray(m.predict(Xho), float))
        tb_ens = PB.rank_ensemble(tb_p)
        def stat_tb(idx, tb_ens=tb_ens, ens=ens, yv=yv):
            return rho(tb_ens[idx], yv[idx]) - rho(ens[idx], yv[idx])
        th2, lo2, hi2, kind2 = PB.cluster_boot(stat_tb, cl, seed=827)
        v827b = REF827["(b) 챌린저"][d]
        row2 = {"Δ": round(th2, 4), "CI95": [round(lo2, 4), round(hi2, 4)], "종류": kind2,
                "판정": {"승": "TabPFN승", "패": "챔피언승"}.get(PB.verdict(lo2, hi2), "판정 불능"),
                "827": {"Δ": v827b["Δ(TabPFN-챔피언)"], "CI": v827b["CI95"], "판정": v827b["판정"]}}
        row2["변화"] = "불변" if row2["판정"] == v827b["판정"] else f"뒤집힘({v827b['판정']}→{row2['판정']})"
        OUT["(b) 챌린저"][d] = row2
        print(f"  {d} 챌린저: Δ {th2:+.4f} [{lo2:+.4f},{hi2:+.4f}] → {row2['판정']} ({row2['변화']})", flush=True)

    if d == "세계애니":
        r = json.loads((AXD / f"{AX['만화']}.json").read_text())
        def n820(s):
            s = str(s or "").lower()
            s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
            return re.sub(r"[^0-9a-z가-힣]+", "", s)
        yr_m = np.asarray(data.yr["만화"], float)
        y_m = np.asarray(data.dom["만화"][2], float)
        ktr_m = np.isfinite(yr_m) & (yr_m < 2025.0) & np.isfinite(y_m)
        tl_m = [n820(v.get("title") or v.get("name") or "") for v in r.values()]
        ptrain = {t for t, k in zip(tl_m, ktr_m) if k and t}
        is_ov = np.array([n820(t) in ptrain and n820(t) != "" for t in tl])
        for label, mask in (("비겹침", ~is_ov), ("겹침", is_ov)):
            sub = np.flatnonzero(mask)
            cl_s = [c[np.isin(c, sub)] for c in cl]
            cl_s = [c for c in cl_s if len(c)]
            th3, lo3, hi3, kind3 = PB.cluster_boot(stat, cl_s, seed=827)
            v827c = REF827["(c) 825 부분집합"][label]
            OUT["(c) 825 부분집합"][label] = {"n": int(mask.sum()), "Δ": round(th3, 4),
                "CI95": [round(lo3, 4), round(hi3, 4)],
                "판정": {"승": "합동승", "패": "릿지승"}.get(PB.verdict(lo3, hi3), "판정 불능"),
                "827": {"Δ": v827c["Δ"], "판정": v827c["판정"]}}
            print(f"  세계애니 {label}: Δ {th3:+.4f} [{lo3:+.4f},{hi3:+.4f}] → {OUT['(c) 825 부분집합'][label]['판정']}", flush=True)

wins = sum(1 for v in OUT["(a) 대 릿지"].values() if v["판정"] == "합동승")
losses = sum(1 for v in OUT["(a) 대 릿지"].values() if v["판정"] == "릿지승")
und = sum(1 for v in OUT["(a) 대 릿지"].values() if v["판정"] == "판정 불능")
ni = sum(1 for v in OUT["(a) 대 릿지"].values() if v["비열등"])
flips = [f"{k}: {v['변화']}" for sec in ("(a) 대 릿지", "(b) 챌린저") for k, v in OUT[sec].items() if v["변화"] != "불변"]
OUT["집계"] = {"합동승": wins, "릿지승": losses, "판정 불능": und, "비열등": f"{ni}/{len(OUT['(a) 대 릿지'])}",
              "뒤집힘": flips or "없음"}
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps(OUT["집계"], ensure_ascii=False), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out828.json", "w"), ensure_ascii=False, indent=1)
print("완료", flush=True)
