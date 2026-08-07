# 노트 827 — 자 교체 전면 재채점 (사전등록: 대장 '사전등록 827' · 커밋 후 측정)
import json, re, sys, time
import numpy as np
from scipy.stats import spearmanr, rankdata
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, guards as G
from lab.forms import REGISTRY
from lab.decay import AXD, AX

t0 = time.time()
B = 10_000
RNG = np.random.default_rng(827)
DELTA_NI = 0.03

def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    if ok.sum() < 10:
        return np.nan
    return float(spearmanr(p[ok], yy[ok])[0])

# ── 프랜차이즈 클러스터 v0 ───────────────────────────────────────
_SEASON = re.compile(r"(시즌|season|part|파트)\s*[0-9ivx]+|[0-9]+기$|[0-9]+부$|"
                     r"\b[ivx]{1,4}$|[0-9]+$")
def norm(s):
    s = str(s or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(r"[^0-9a-z가-힣 ]+", "", s).strip()
    s = _SEASON.sub("", s).strip()
    return re.sub(r"\s+", "", s)

def clusters_of(titles):
    key = {}
    out = []
    for i, t in enumerate(titles):
        k = norm(t) or f"__solo{i}"
        key.setdefault(k, []).append(i)
    return list(key.values())

def cluster_boot(stat_fn, clusters, B=B, seed=827):
    """군집 재표집 BCa 95% (가속 실패/퇴화 시 percentile 폴백 — 사전 선언)."""
    rng = np.random.default_rng(seed)
    nC = len(clusters)
    th = stat_fn(np.concatenate([clusters[i] for i in range(nC)]))
    bs = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, nC, nC)
        idx = np.concatenate([clusters[i] for i in pick])
        bs[b] = stat_fn(idx)
    bs = bs[np.isfinite(bs)]
    if len(bs) < B * 0.9:
        return th, float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5)), "percentile(유실)"
    # BCa
    try:
        from scipy.stats import norm as _n
        z0 = _n.ppf(np.clip(np.mean(bs < th), 1e-6, 1 - 1e-6))
        jack = []
        for i in range(nC):
            idx = np.concatenate([clusters[j] for j in range(nC) if j != i])
            jack.append(stat_fn(idx))
        jack = np.asarray(jack, float)
        jm = np.nanmean(jack)
        num = np.nansum((jm - jack) ** 3)
        den = 6.0 * (np.nansum((jm - jack) ** 2) ** 1.5)
        a = num / den if den > 0 else 0.0
        def q(alpha):
            z = _n.ppf(alpha)
            adj = _n.cdf(z0 + (z0 + z) / (1 - a * (z0 + z)))
            return float(np.percentile(bs, np.clip(adj * 100, 0.01, 99.99)))
        return th, q(0.025), q(0.975), "BCa"
    except Exception:
        return th, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), "percentile(폴백)"

def verdict(lo, hi):
    if lo > 0:
        return "합동승"
    if hi < 0:
        return "상대승"
    return "판정 불능"

# ── 자료·모델 ────────────────────────────────────────────────────
data = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]
DF = {"게임": "release_date", "모바일": "release_date"}
def titles_of(dkey):
    r = json.loads((AXD / f"{AX[dkey]}.json").read_text())
    return [v.get("name") or v.get("title") or "" for v in r.values()]

joint_preds = {}   # 도메인 → (n_ho, [씨앗4 예측 순위], y, 제목)
print("챔피언 씨앗 1~4 적합...", flush=True)
fits = [G._fit_on(lambda s=s: cls(seed=s), data, 2025.0, seed=s) for s in (1, 2, 3, 4)]
print(f"적합 완료 {time.time()-t0:.0f}s", flush=True)

DOMS = ["게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "펀딩"]
OUT = {"(a) 대 릿지": {}, "(b) 챌린저": {}, "(c) 825 부분집합": {}}
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
    # 릿지(822 설정)
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
    # 제목(클러스터) — 축파일 정렬(아이돌은 어긋남 → 단독 클러스터)
    if d in AX:
        tl_all = titles_of(d)
        tl = [tl_all[i] for i in np.flatnonzero(kho)] if len(tl_all) == len(y_all) else None
    else:
        tl = None
    idx_all = np.arange(len(yv))
    cl = clusters_of(tl) if tl else [[i] for i in idx_all]
    cl = [np.asarray(c, int) for c in cl]

    def stat(idx, pj=pj, p_r=p_r, yv=yv):
        js = [rho(np.asarray(rankdata(p[idx]), float), yv[idx]) for p in pj]
        return float(np.nanmean(js)) - rho(p_r[idx], yv[idx])

    th, lo, hi, kind = cluster_boot(stat, cl)
    row = {"n": int(len(yv)), "군집": len(cl), "Δ": round(th, 4),
           "CI95": [round(lo, 4), round(hi, 4)], "종류": kind,
           "판정": verdict(lo, hi), "비열등(하한>-0.03)": bool(lo > -DELTA_NI),
           "822 판정": None}
    OUT["(a) 대 릿지"][d] = row
    print(f"  {d}: Δ {th:+.4f} [{lo:+.4f},{hi:+.4f}] {kind} → {row['판정']} ({time.time()-t0:.0f}s)", flush=True)

    # (b) 챌린저 (아이돌·시장팝업)
    if d in ("아이돌", "시장팝업"):
        from tabpfn import TabPFNRegressor
        tb_p = []
        for s in (4, 5, 6, 7):
            m = TabPFNRegressor(device="cpu", random_state=s)
            m.fit(Xtr, ytr[okr])
            tb_p.append(np.asarray(m.predict(Xho), float))
        def stat_tb(idx, pj=pj, tb_p=tb_p, yv=yv):
            tj = float(np.nanmean([rho(p[idx], yv[idx]) for p in tb_p]))
            cj = float(np.nanmean([rho(np.asarray(rankdata(p[idx]), float), yv[idx]) for p in pj]))
            return tj - cj
        th2, lo2, hi2, kind2 = cluster_boot(stat_tb, cl, seed=8271)
        OUT["(b) 챌린저"][d] = {"Δ(TabPFN-챔피언)": round(th2, 4),
            "CI95": [round(lo2, 4), round(hi2, 4)], "종류": kind2,
            "판정": ("TabPFN승" if lo2 > 0 else "챔피언승" if hi2 < 0 else "판정 불능"),
            "803 판정": "TabPFN승(절반 자)"}
        print(f"  {d} 챌린저: Δ {th2:+.4f} [{lo2:+.4f},{hi2:+.4f}] → {OUT['(b) 챌린저'][d]['판정']}", flush=True)

    # (c) 세계애니 부분집합
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
        tl_ho = [n820(t) for t in tl]
        is_ov = np.array([t in ptrain and t != "" for t in tl_ho])
        for label, mask in (("비겹침", ~is_ov), ("겹침", is_ov)):
            sub = np.flatnonzero(mask)
            subset = set(sub.tolist())
            cl_s = [c[np.isin(c, sub)] for c in cl]
            cl_s = [c for c in cl_s if len(c)]
            th3, lo3, hi3, kind3 = cluster_boot(lambda idx: stat(idx), cl_s, seed=8272)
            OUT["(c) 825 부분집합"][label] = {"n": int(mask.sum()), "Δ": round(th3, 4),
                "CI95": [round(lo3, 4), round(hi3, 4)], "종류": kind3,
                "판정": verdict(lo3, hi3)}
            print(f"  세계애니 {label}: Δ {th3:+.4f} [{lo3:+.4f},{hi3:+.4f}] → {OUT['(c) 825 부분집합'][label]['판정']}", flush=True)

wins = sum(1 for v in OUT["(a) 대 릿지"].values() if v["판정"] == "합동승")
losses = sum(1 for v in OUT["(a) 대 릿지"].values() if v["판정"] == "상대승")
und = sum(1 for v in OUT["(a) 대 릿지"].values() if v["판정"] == "판정 불능")
ni = sum(1 for v in OUT["(a) 대 릿지"].values() if v["비열등(하한>-0.03)"])
OUT["집계"] = {"합동승": wins, "릿지승": losses, "판정 불능": und,
              "비열등(δ=0.03)": f"{ni}/{len(OUT['(a) 대 릿지'])}",
              "주의": "개별 95% 구간 · 다중비교 미보정 · 학습된 모델 고정 조건부"}
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps(OUT["집계"], ensure_ascii=False), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out827.json", "w"), ensure_ascii=False, indent=1)
print("완료", flush=True)
