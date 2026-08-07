# 노트 819 — 공유 기저 검증: 도메인별 치환 중요도 벡터의 교차 코사인
# 사전등록: prereg819.md (이 파일보다 먼저 적었다)
import json, sys, time
import numpy as np
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, guards as G
from lab.forms import REGISTRY

T = 2025.0
NPERM = 6          # 규약 20
NSPLIT = 6         # 자기 천장도 뽑기 6 (규약 20 확장)
NSHUF = 200        # 축 셔플 널
rng = np.random.default_rng(819)

t0 = time.time()
data = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]
f = G._fit_on(lambda: cls(seed=0), data, T)
print(f"적합 {time.time()-t0:.0f}s · 도메인 {len(f.doms)} · 공유축 {len(f.order)}", flush=True)

# ── 블록 지도 (배선 검사 갈래 1 재료) ────────────────────────────
L = len(f.order)
assert not getattr(f, "DOMAX", False), "DOMAX 켜짐 — 블록 지도 무효"
n_season = 2 if getattr(f, "SEASON", False) else 0
n_spec = 2 if getattr(f, "SPEC", False) else 0
n_time = 2 if getattr(f, "TIMEAX", False) else 0
width_expect = 2 * L + n_season + n_spec + n_time + len(f.doms)

blocks = [(a, [2 * i, 2 * i + 1]) for i, a in enumerate(f.order)]
p = 2 * L
for nm2, w in (("계절", n_season), ("전용", n_spec), ("시간축", n_time)):
    if w:
        blocks.append((nm2, [p, p + 1])); p += 2
names = [b[0] for b in blocks]
NB = len(blocks)

def rho_of(pred, y):
    return float(spearmanr(pred, y)[0])

def base_pred(X, y):
    acc = np.zeros(len(y))
    for m in f.ms:
        acc += rankdata(m.predict(X))
    return acc

def imp_vector(X0, y, seed):
    """축 블록별 치환 중요도 Δρ (뽑기 NPERM 평균) — 전 블록·전 뽑기를
    한 덩어리로 이어 자루당 predict 1회."""
    r = np.random.default_rng(seed)
    n = len(y)
    base = rho_of(base_pred(X0, y), y)
    big = np.tile(X0, (NB * NPERM, 1))
    for bi, (_, cols) in enumerate(blocks):
        for k in range(NPERM):
            off = (bi * NPERM + k) * n
            pi = r.permutation(n)
            for c in cols:
                big[off:off + n, c] = X0[pi, c]
    acc = np.zeros((NB * NPERM, n))
    for m in f.ms:
        raw = m.predict(big)
        for c in range(NB * NPERM):
            acc[c] += rankdata(raw[c * n:(c + 1) * n])
    v = np.zeros(NB)
    for bi in range(NB):
        rhos = [rho_of(acc[bi * NPERM + k], y) for k in range(NPERM)]
        v[bi] = base - float(np.mean(rhos))
    return base, v

def cos(a, b):
    na, nb_ = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-12 or nb_ < 1e-12:
        return np.nan
    return float(a @ b / (na * nb_))

wiring, vecs, ceils = {}, {}, {}
pooled_parts = []
for d in sorted(data.dom):
    yr = np.asarray(data.yr[d], float)
    y_all = np.asarray(data.dom[d][2], float)
    kho = np.isfinite(yr) & (yr >= T) & np.isfinite(y_all)
    if kho.sum() < 20:
        continue
    A, M, y, t = data.slice(d, kho)
    ok = np.isfinite(y)
    A, M, y, t = A[ok], M[ok], y[ok], t[ok]
    X0 = f._design(d, A, M, t)
    p_ref = np.asarray(f.predict(d, A, M, t), float)
    rho_ref = rho_of(p_ref, y)
    dseed = sum(map(ord, d))            # 해시 소금 회피 — 결정적
    base, v = imp_vector(X0, y, seed=dseed)
    wiring[d] = {"n": int(len(y)), "폭": int(X0.shape[1]),
                 "폭기대": int(width_expect),
                 "rho_ref": round(rho_ref, 4), "rho_base": round(base, 4),
                 "차": round(abs(rho_ref - base), 6),
                 "L2": round(float(np.linalg.norm(v)), 5)}
    vecs[d] = v
    pooled_parts.append((len(y), rho_ref))
    cc = []
    for s in range(NSPLIT):
        pi = rng.permutation(len(y)); h = len(y) // 2
        i1, i2 = pi[:h], pi[h:]
        _, v1 = imp_vector(X0[i1], y[i1], seed=dseed + 1000 + s)
        _, v2 = imp_vector(X0[i2], y[i2], seed=dseed + 2000 + s)
        cc.append(cos(v1, v2))
    ceils[d] = cc
    print(f"{d}: n={len(y)} rho={base:.4f} L2={np.linalg.norm(v):.4f} "
          f"천장중앙 {np.nanmedian(cc):.3f} ({time.time()-t0:.0f}s)", flush=True)

pooled = float(np.average([r for _, r in pooled_parts],
                          weights=[n for n, _ in pooled_parts]))

doms = sorted(vecs)
pairs = []
for i in range(len(doms)):
    for j in range(i + 1, len(doms)):
        d1, d2 = doms[i], doms[j]
        c = cos(vecs[d1], vecs[d2])
        null = [cos(vecs[d1][rng.permutation(NB)], vecs[d2]) for _ in range(NSHUF)]
        p95 = float(np.nanpercentile(null, 95))
        pairs.append({"쌍": f"{d1}-{d2}", "cos": round(c, 4), "널p95": round(p95, 4),
                      "초과": bool(c > p95),
                      "천장min": round(float(min(np.nanmedian(ceils[d1]),
                                                 np.nanmedian(ceils[d2]))), 4)})

out = {"공유축수": L, "블록수": NB, "블록": names,
       "seed0_유보_가중rho": round(pooled, 4),
       "배선": wiring,
       "자기천장": {d: [round(float(x), 4) for x in ceils[d]] for d in doms},
       "벡터": {d: [round(float(x), 5) for x in vecs[d]] for d in doms},
       "쌍": pairs,
       "평균교차": {d: round(float(np.nanmean(
           [q["cos"] for q in pairs if d in q["쌍"].split("-")])), 4) for d in doms},
       "소요초": round(time.time() - t0, 1)}
outp = "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out819.json"
json.dump(out, open(outp, "w"), ensure_ascii=False, indent=1)
print("완료", outp, flush=True)
