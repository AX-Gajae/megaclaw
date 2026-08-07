# 노트 825 — 합동승 지도의 IP 겹침 통제 (사전등록: 대장 '사전등록 825' · 커밋 후 측정)
import json, re, sys, time
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, guards as G
from lab.forms import REGISTRY
from lab.decay import AXD, AX

t0 = time.time()

def norm(s):
    s = str(s or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(r"[^0-9a-z가-힣]+", "", s)
    return s

def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    if ok.sum() < 10:
        return np.nan
    return float(spearmanr(p[ok], yy[ok])[0])

data = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]
f = G._fit_on(lambda: cls(seed=0), data, 2025.0)
print(f"적합 {time.time()-t0:.0f}s", flush=True)

def titles_of(dkey):
    r = json.loads((AXD / f"{AX[dkey]}.json").read_text())
    return [norm(v.get("name") or v.get("title") or "") for v in r.values()]

def train_titleset(dkey):
    tl = titles_of(dkey)
    yr = np.asarray(data.yr[dkey], float)
    y = np.asarray(data.dom[dkey][2], float)
    ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y)
    assert len(tl) == len(y), f"{dkey} 정렬 어긋남"
    return {t for t, k in zip(tl, ktr) if k and t}

def fit_ridge(Xp, yp):
    best_a, best_s = None, -9
    for a in (0.1, 1.0, 10.0, 100.0, 1000.0):
        ss = []
        for tr, te in KFold(5, shuffle=True, random_state=1).split(Xp):
            m = Ridge(alpha=a).fit(Xp[tr], yp[tr])
            ss.append(rho(m.predict(Xp[te]), yp[te]))
        s = float(np.nanmean(ss))
        if s > best_s:
            best_a, best_s = a, s
    return Ridge(alpha=best_a).fit(Xp, yp), best_a

OUT = {}
CASES = [("세계애니", ["만화"]), ("게임", ["모바일"]), ("애니", ["만화", "세계애니", "웹툰"])]
REF822 = {"세계애니": 0.1427, "게임": 0.1795, "애니": 0.1526}
for d, partners in CASES:
    tl = titles_of(d)
    yr = np.asarray(data.yr[d], float)
    y_all = np.asarray(data.dom[d][2], float)
    ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y_all)
    kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y_all)
    assert len(tl) == len(y_all), f"{d} 정렬 어긋남"
    ptrain = set()
    for p in partners:
        ptrain |= train_titleset(p)
    ho_ix = np.flatnonzero(kho)
    is_ov = np.array([tl[i] in ptrain and tl[i] != "" for i in ho_ix])
    n_ov, n_cl = int(is_ov.sum()), int((~is_ov).sum())

    A, M, yv, tv = data.slice(d, kho)
    okf = np.isfinite(yv)
    p_joint = np.asarray(f.predict(d, A, M, tv), float)
    Atr, Mtr, ytr, ttr = data.slice(d, ktr)
    okr = np.isfinite(ytr)
    Xtr = np.nan_to_num(np.hstack([Atr, Mtr, np.asarray(ttr, float)[:, None]]), nan=0.5)[okr]
    Xho = np.nan_to_num(np.hstack([A, M, np.asarray(tv, float)[:, None]]), nan=0.5)
    mR, alpha = fit_ridge(Xtr, ytr[okr])
    p_ridge = mR.predict(Xho)

    def sub(mask):
        n = int(mask.sum())
        if n < 20:
            return {"n": n}
        dj = rho(p_joint[mask], yv[mask]); dr = rho(p_ridge[mask], yv[mask])
        sig = 2 * 0.262 / np.sqrt(n)
        return {"n": n, "합동": round(dj, 4), "릿지": round(dr, 4),
                "Δ": round(dj - dr, 4), "2σ": round(sig, 4)}
    full = sub(np.ones(len(yv), bool))
    clean = sub(~is_ov)
    over = sub(is_ov)
    row = {"유보": int(kho.sum()), "겹침행": n_ov, "비겹침행": n_cl,
           "alpha": alpha, "전체": full, "비겹침": clean, "겹침": over,
           "822 Δ": REF822[d]}
    if n_ov < 20:
        row["판정"] = "1.배선/검정 불능 — 겹침행 <20"
    elif clean.get("Δ") is not None and clean["Δ"] < clean["2σ"] and \
         over.get("Δ") is not None and over["Δ"] > clean["Δ"]:
        row["판정"] = "2.오염 — 합동승 강등(동어반복 후보)"
    elif clean.get("Δ") is not None and clean["Δ"] >= clean["2σ"]:
        row["판정"] = "3.통과 — 오염 가설 기각"
    else:
        row["판정"] = "그 외(비겹침 Δ<2σ 이나 겹침 대비 미확인)"
    OUT[d] = row
    print(json.dumps({d: row}, ensure_ascii=False, indent=1), flush=True)

OUT["초"] = round(time.time() - t0, 1)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out825.json", "w"), ensure_ascii=False, indent=1)
print("완료", flush=True)
