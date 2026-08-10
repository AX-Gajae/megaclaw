# 노트 841 — 조건부 치환 12도메인 (사전등록 '841' · 819 기계 + 그룹 치환)
import json, sys, time
import numpy as np
from scipy.stats import spearmanr, rankdata
sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, guards as G
from lab.forms import REGISTRY

t0 = time.time()
NPERM = 6
NSHUF = 200
rng = np.random.default_rng(841)
data = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]
f = G._fit_on(lambda: cls(seed=0), data, 2025.0)
L = len(f.order)
print(f"도메인 {len(data.dom)} · 공유축 {L} · 적합 {time.time()-t0:.0f}s", flush=True)

# ── 축 상관 무리(학습 구간 값 열 · |스피어만|≥0.5 병합) ──────────
tr_rows = []
for d in data.dom:
    yr = np.asarray(data.yr[d], float)
    y = np.asarray(data.dom[d][2], float)
    k = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y)
    A, M, _, tt = data.slice(d, k)
    X = f._design(d, A, M, tt)
    tr_rows.append(X[:, :2 * L:2])          # 값 열만(짝수 인덱스)
V = np.vstack(tr_rows)
corr = np.abs(spearmanr(V).statistic)
np.fill_diagonal(corr, 0)
parent = list(range(L))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
for i in range(L):
    for j in range(i + 1, L):
        if corr[i, j] >= 0.5:
            parent[find(i)] = find(j)
groups = {}
for i in range(L):
    groups.setdefault(find(i), []).append(i)
GROUPS = [sorted(g) for g in groups.values()]
gnames = [" + ".join(f.order[i] for i in g) for g in GROUPS]
NB = len(GROUPS)
print(f"상관 무리 {NB}개(다축 무리: {[n for n, g in zip(gnames, GROUPS) if len(g) > 1]})", flush=True)

n_season = 2 if getattr(f, "SEASON", False) else 0
n_spec = 2 if getattr(f, "SPEC", False) else 0
blocks = [[c for i in g for c in (2 * i, 2 * i + 1)] for g in GROUPS]
p = 2 * L
if n_season:
    blocks.append([p, p + 1]); gnames.append("계절"); p += 2
if n_spec:
    blocks.append([p, p + 1]); gnames.append("전용"); p += 2
NBT = len(blocks)

def rho(a, b):
    return float(spearmanr(a, b)[0])

def imp_vector(X0, y, seed):
    r2 = np.random.default_rng(seed)
    n = len(y)
    acc0 = np.zeros(n)
    for m in f.ms:
        acc0 += rankdata(m.predict(X0))
    base = rho(acc0, y)
    big = np.tile(X0, (NBT * NPERM, 1))
    for bi, cols in enumerate(blocks):
        for k in range(NPERM):
            off = (bi * NPERM + k) * n
            pi = r2.permutation(n)
            for c in cols:
                big[off:off + n, c] = X0[pi, c]
    acc = np.zeros((NBT * NPERM, n))
    for m in f.ms:
        raw = m.predict(big)
        for c in range(NBT * NPERM):
            acc[c] += rankdata(raw[c * n:(c + 1) * n])
    v = np.zeros(NBT)
    for bi in range(NBT):
        v[bi] = base - float(np.mean([rho(acc[bi * NPERM + k], y) for k in range(NPERM)]))
    return base, v

def cos(a, b):
    na, nb_ = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-12 or nb_ < 1e-12:
        return np.nan
    return float(a @ b / (na * nb_))

vecs, ceils, wiring = {}, {}, {}
pooled = []
for d in sorted(data.dom):
    yr = np.asarray(data.yr[d], float)
    y_all = np.asarray(data.dom[d][2], float)
    kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y_all)
    if kho.sum() < 20:
        continue
    A, M, yv, tv = data.slice(d, kho)
    ok = np.isfinite(yv)
    A, M, yv, tv = A[ok], M[ok], yv[ok], tv[ok]
    X0 = f._design(d, A, M, tv)
    base, v = imp_vector(X0, yv, sum(map(ord, d)))
    wiring[d] = {"n": int(len(yv)), "rho": round(base, 4), "L2": round(float(np.linalg.norm(v)), 4)}
    vecs[d] = v
    pooled.append((len(yv), base))
    cc = []
    for s in range(6):
        pi = rng.permutation(len(yv)); h = len(yv) // 2
        _, v1 = imp_vector(X0[pi[:h]], yv[pi[:h]], 1000 + s)
        _, v2 = imp_vector(X0[pi[h:]], yv[pi[h:]], 2000 + s)
        cc.append(cos(v1, v2))
    ceils[d] = float(np.nanmedian(cc))
    print(f"  {d}: rho {base:.4f} · 천장 {ceils[d]:.3f} ({time.time()-t0:.0f}s)", flush=True)

pool_rho = float(np.average([r for _, r in pooled], weights=[n for n, _ in pooled]))
doms = sorted(vecs)
pairs = []
for i in range(len(doms)):
    for j in range(i + 1, len(doms)):
        d1, d2 = doms[i], doms[j]
        c = cos(vecs[d1], vecs[d2])
        null = [cos(vecs[d1][rng.permutation(NBT)], vecs[d2]) for _ in range(NSHUF)]
        pairs.append({"쌍": f"{d1}-{d2}", "cos": round(c, 3),
                      "초과": bool(c > float(np.nanpercentile(null, 95)))})
exceed = sum(p_["초과"] for p_ in pairs)
rate = exceed / len(pairs)
# 영화 최근접 이웃
mv = {p_["쌍"]: p_["cos"] for p_ in pairs if "영화" in p_["쌍"]}
nearest = max(mv, key=mv.get)
OUT = {"공유축": L, "상관 무리": NBT, "무리 이름(다축만)": [n for n in gnames if "+" in n],
       "seed0 판(12)": round(pool_rho, 4), "배선": wiring,
       "자기 천장(중앙)": {d: round(c, 3) for d, c in ceils.items()},
       "널 초과": f"{exceed}/{len(pairs)} = {rate:.0%}",
       "영화 최근접": {nearest: mv[nearest]},
       "819 참조": "축 단위 25%(14/55)"}
deg = sum(1 for d in doms if wiring[d]["L2"] < 1e-6)
#: 🔴 이슈 #112(티처 #59 C1 · 조항 60) --- 여기서 재는 `pool_rho` 는 **씨앗 0 하나**인데
#: 옛 코드는 그것을 **씨앗 0~11 평균**(0.4710)에 견줬다. 분모가 다른 두 수를 이어 붙인
#: 것이다. 씨앗 0 의 정본은 **0.4724867181663707**(노트 890 배선 ㄷ · `dose896.py:54` ·
#: 오늘 `runners/rerun112.py` 가 부동소수 정확 일치로 재현). 12씨앗 평균 정본은 별개로
#: **0.46982 ± 0.0020(SD)** 다 --- 옛 0.4710 은 은퇴한 두 규약(라벨 배치 채점 ·
#: `_fit_on(seed=s)` 의 random_state) 위의 값이라 오늘 어느 자로도 안 나온다.
BOARD_RHO_SEED0 = 0.4724867181663707
if abs(pool_rho - BOARD_RHO_SEED0) > 0.01 or deg >= 6:
    OUT["판정"] = f"1.배선 — 판 {pool_rho:.4f} · 퇴화 {deg}"
elif rate <= 0.35:
    OUT["판정"] = f"2.확정 — 초과 {rate:.0%} ≤35% · '합동은 공유 기저 안 씀' 조건부 자로도 성립 — 819 문패 종결"
elif rate >= 0.50:
    OUT["판정"] = f"3.반전 — 초과 {rate:.0%} ≥50% · 819 는 상관-몫 인공물"
else:
    OUT["판정"] = f"4.중간 — 초과 {rate:.0%}"
OUT["쌍(상위)"] = sorted(pairs, key=lambda p_: -p_["cos"])[:6]
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps({k: OUT[k] for k in ("상관 무리", "무리 이름(다축만)", "널 초과", "영화 최근접", "판정", "초")}, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out841.json", "w"), ensure_ascii=False, indent=1)
