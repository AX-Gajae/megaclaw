# 노트 822 — (a) 앱 짝 릿지 대 전이 · (b) 판 11도메인 합동 대 단독 릿지
# 사전등록: prereg822.md
import json, sys, time
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import pairs as PR, guards as G, sideaudit
from lab.forms import REGISTRY

t0 = time.time()
OUT = {}

def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    if ok.sum() < 10:
        return np.nan
    return float(spearmanr(p[ok], yy[ok])[0])

def fit_ridge(Xp, yp, Xe, seed=0):
    best_a, best_s = None, -9
    for a in (0.1, 1.0, 10.0, 100.0, 1000.0):
        ss = []
        for tr, te in KFold(5, shuffle=True, random_state=seed).split(Xp):
            m = Ridge(alpha=a).fit(Xp[tr], yp[tr])
            ss.append(rho(m.predict(Xp[te]), yp[te]))
        s = float(np.nanmean(ss))
        if s > best_s:
            best_a, best_s = a, s
    m = Ridge(alpha=best_a).fit(Xp, yp)
    return m.predict(Xe), best_a, best_s, m

# ── (a) 앱 짝 ────────────────────────────────────────────────────
data = FF.shell(FF.base())
CLS = REGISTRY["F18_bagboost"]["cls"]
src = PR.SRC_DOM["비게임 앱"]; names = list(data.names.get(src) or [])
recs = PR.build("비게임 앱")
A, M, y, t = PR.to_arrays(recs, names)
X = np.nan_to_num(np.hstack([A, M, np.asarray(t, float)[:, None]]), nan=0.5)
fin = np.isfinite(y)
years = np.array([int(str((r.get("release_date") or "0000"))[:4] or 0) for r in recs.values()])
ev = np.flatnonzero(fin & (years >= 2025))
pool = np.flatnonzero(fin & (years < 2025) & (years > 0))
wa = {"행": int(len(y)), "평가": int(len(ev)), "풀": int(len(pool)), "열": int(X.shape[1])}
print(json.dumps({"(a) 배선": wa}, ensure_ascii=False), flush=True)
assert (wa["행"], wa["평가"], wa["풀"]) == (1600, 189, 1411), "배선 불일치 — 갈래 1"

ch = []
for s in (4, 5, 6, 7):
    f = G._fit_on(lambda s=s: CLS(seed=s), data, 2025.0, seed=s)
    p = np.asarray(f.predict(src, A[ev], M[ev], np.asarray(t, float)[ev]), float)
    ch.append(rho(p, y[ev]))
    print(f"  전이 씨앗 {s}: {ch[-1]:+.4f} ({time.time()-t0:.0f}s)", flush=True)
CH = float(np.mean(ch)); CHSD = float(np.std(ch, ddof=1))

p_r, a_r, cv_r, m_r = fit_ridge(X[pool], y[pool], X[ev])
RG = rho(p_r, y[ev])
plc = []
for d in range(6):
    r2 = np.random.default_rng(8220 + d)
    ysh = y[pool].copy(); r2.shuffle(ysh)
    mp_ = Ridge(alpha=a_r).fit(X[pool], ysh)
    plc.append(rho(mp_.predict(X[ev]), y[ev]))
Xnt = X[:, :-1]
mnt = Ridge(alpha=a_r).fit(Xnt[pool], y[pool])
rg_nt = rho(mnt.predict(Xnt[ev]), y[ev])
OUT["(a) 앱 짝"] = {"전이": round(CH, 4), "전이 SD": round(CHSD, 4),
    "릿지": round(RG, 4), "alpha": a_r, "풀 CV": round(cv_r, 4),
    "릿지 t제외": round(rg_nt, 4),
    "위약": {"평균": round(float(np.mean(plc)), 4), "최대": round(float(np.max(plc)), 4)},
    "차(릿지-전이)": round(RG - CH, 4)}
if np.mean(plc) >= RG:
    OUT["(a) 판정"] = "1.배선/위약"
elif RG >= CH - 0.024:
    OUT["(a) 판정"] = f"2.폐기 확정 (릿지 {RG:+.4f} ≥ 전이-0.024)"
else:
    OUT["(a) 판정"] = f"3.쌍 특유 (전이-릿지 {CH-RG:+.4f} ≥ 0.024)"
print(json.dumps({k: OUT[k] for k in ("(a) 앱 짝", "(a) 판정")}, ensure_ascii=False, indent=1), flush=True)

# ── (b) 판 11도메인 ──────────────────────────────────────────────
cdata = sideaudit.champion_data()
ref = json.load(open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out819.json"))
wiring819 = ref["배선"]
rows = {}
bad_plc = 0
for d in sorted(cdata.dom):
    yr = np.asarray(cdata.yr[d], float)
    y_all = np.asarray(cdata.dom[d][2], float)
    ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y_all)
    kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y_all)
    if kho.sum() < 20 or ktr.sum() < 30:
        continue
    Atr, Mtr, ytr, ttr = cdata.slice(d, ktr)
    Aho, Mho, yho, tho = cdata.slice(d, kho)
    okr = np.isfinite(ytr); oke = np.isfinite(yho)
    Xtr = np.nan_to_num(np.hstack([Atr, Mtr, np.asarray(ttr, float)[:, None]]), nan=0.5)[okr]
    Xho = np.nan_to_num(np.hstack([Aho, Mho, np.asarray(tho, float)[:, None]]), nan=0.5)[oke]
    ytr2, yho2 = ytr[okr], yho[oke]
    n_ho = int(len(yho2))
    ref_n = wiring819.get(d, {}).get("n")
    p, a_, cv_, _ = fit_ridge(Xtr, ytr2, Xho, seed=1)
    r_ridge = rho(p, yho2)
    pl = []
    for dd in range(6):
        r2 = np.random.default_rng(8221 + dd)
        ysh = ytr2.copy(); r2.shuffle(ysh)
        mm = Ridge(alpha=a_).fit(Xtr, ysh)
        pl.append(rho(mm.predict(Xho), yho2))
    pmean = float(np.nanmean(pl))
    if pmean >= r_ridge:
        bad_plc += 1
    champ = wiring819.get(d, {}).get("rho_ref")
    sig = 0.262 / np.sqrt(n_ho) * 2
    diff = None if champ is None else round(champ - r_ridge, 4)
    rows[d] = {"유보": n_ho, "819n": ref_n, "합동(819)": champ,
               "릿지": round(r_ridge, 4), "alpha": a_, "위약평균": round(pmean, 4),
               "차(합동-릿지)": diff, "2σ": round(sig, 4),
               "판정": ("합동승" if diff is not None and diff >= sig else
                        "릿지승" if diff is not None and diff <= -sig else "동점")}
    print(f"  {d}: 합동 {champ} 릿지 {r_ridge:+.4f} 차 {diff} (2σ {sig:.3f}) → {rows[d]['판정']}", flush=True)

wins_j = sum(1 for v in rows.values() if v["판정"] == "합동승")
wins_r = sum(1 for v in rows.values() if v["판정"] == "릿지승")
ties = sum(1 for v in rows.values() if v["판정"] == "동점")
mismatch = [d for d, v in rows.items() if v["819n"] is not None and v["유보"] != v["819n"]]
OUT["(b) 표"] = rows
OUT["(b) 집계"] = {"합동승": wins_j, "릿지승": wins_r, "동점": ties,
                   "배선 불일치": mismatch, "위약 실패 수": bad_plc}
if mismatch or bad_plc >= 3:
    OUT["(b) 판정"] = "1.배선"
elif wins_j >= 7:
    OUT["(b) 판정"] = f"2.합동 우세 ({wins_j}/{len(rows)})"
elif wins_j >= 3:
    OUT["(b) 판정"] = f"3.혼전 (합동 {wins_j} · 릿지 {wins_r} · 동점 {ties})"
else:
    OUT["(b) 판정"] = f"4.릿지 우세 — 합동 재고 (합동승 {wins_j})"
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps({k: OUT[k] for k in ("(b) 집계", "(b) 판정", "초")}, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out822.json", "w"), ensure_ascii=False, indent=1)
print("완료", flush=True)
