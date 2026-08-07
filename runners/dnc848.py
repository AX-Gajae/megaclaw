# 노트 848 — 합동 적응 곡선 Δ(n) · KR 짝 (사전등록 '848' · 배경 6~7h · 체크포인트 재개)
# Δ(n) = ρ_합동(전이+라벨 n) − ρ_릿지(n) · 같은 뽑기·같은 채점행 짝 · α=1 고정 전 격자.
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G, pairs as PR, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402
from lab.harness import Data  # noqa: E402

t0 = time.time()
T = 2025.0
SEEDS = list(range(12))
GRID = (10, 20, 40, 80, 160)
DRAWS = 6
ROOT = Path("/Users/ax/world_model")
CKPT = ROOT / "runners/out848_checkpoint.jsonl"
PAIR = "KR 만화"

data12 = sideaudit.champion_data()
src = PR.SRC_DOM[PAIR]
names = list(data12.names[src])
recs = PR.build(PAIR)
A, M, y, t = PR.to_arrays(recs, names)
A = np.asarray(A, float); M = np.asarray(M, float)
y = np.asarray(y, float); t = np.asarray(t, float)
years = np.array([int(str((r.get("start_date") or "0000"))[:4] or 0) for r in recs.values()])
fin = np.isfinite(y)
ev = np.flatnonzero(fin & (years >= 2025))
pool = np.flatnonzero(fin & (years < 2025) & (years > 0))
assert len(ev) == 322, f"배선: 평가 {len(ev)} ≠ 322"
# 배선: KR t 가 판 만화 t 와 같은 자(로그 경과일)인지 — 자릿수로 검사
t_pan = np.asarray(data12.dom[src][3], float)
r_kr = (np.nanmin(t[fin]), np.nanmax(t[fin]))
r_pan = (np.nanmin(t_pan), np.nanmax(t_pan))
print(f"KR 행 {int(fin.sum())} · 평가 {len(ev)} · 풀 {len(pool)} · t KR {r_kr} 대 판 {r_pan}", flush=True)
assert abs(r_kr[1] - r_pan[1]) < 5, f"배선: t 자 불일치 {r_kr} 대 {r_pan}"

cls = REGISTRY["F18_bagboost"]["cls"]
Xr = np.nan_to_num(np.hstack([A, M, t[:, None]]), nan=0.5)


def rho(p, yy, sel):
    ok = np.isfinite(p[sel]) & np.isfinite(yy[sel])
    return float(spearmanr(p[sel][ok], yy[sel][ok])[0])


done = set()
if CKPT.exists():
    for line in open(CKPT):
        j = json.loads(line)
        done.add((j["d"], j["n"]))
    print(f"체크포인트 재개 — 기존 {len(done)}", flush=True)


def joint_rho(train_idx):
    """KR만화를 13번째 도메인으로 넣어 합동 적합 · 평가 322 ρ (씨앗 12 평균 순위)."""
    y13 = np.full(len(y), np.nan)
    y13[train_idx] = y[train_idx]
    y13[ev] = y[ev]                     # 평가 라벨은 채점용 — T 게이트(연도)가 적합에서 자동 제외
    dom13 = dict(data12.dom)
    nm13 = dict(data12.names)
    dom13["KR만화"] = (A, M, y13, t)
    nm13["KR만화"] = list(names)
    d13 = Data(dom13, nm13)
    d13.yr = dict(data12.yr)
    d13.yr["KR만화"] = years.astype(float)
    preds = []
    for s in SEEDS:
        f = G._fit_on(lambda s=s: cls(seed=s), d13, T, seed=s)
        preds.append(np.asarray(f.predict("KR만화", A[ev], M[ev], t[ev]), float))
    pe = np.nanmean(preds, axis=0)
    ok = np.isfinite(pe) & np.isfinite(y[ev])
    return float(spearmanr(pe[ok], y[ev][ok])[0]), pe


# n=0 전이 앵커(빈 도메인 합동 1회 — 실패하면 833 실측 0.2969 로 폴백)
if (0, 0) not in done:
    try:
        r0, p0 = joint_rho(np.array([], int))
        rec = {"d": 0, "n": 0, "rho_joint": round(r0, 4), "rho_ridge": None,
               "joint_pred": [round(float(x), 3) for x in p0], "비고": "전이 앵커(빈 도메인)"}
    except Exception as e:
        rec = {"d": 0, "n": 0, "rho_joint": 0.2969, "rho_ridge": None,
               "비고": f"빈 도메인 적합 실패({str(e)[:60]}) — 833 실측 앵커"}
    rec["초"] = round(time.time() - t0, 1)
    with open(CKPT, "a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"n=0 앵커: {rec.get('rho_joint')} ({rec.get('비고')})", flush=True)

for dd in range(DRAWS):
    perm = np.random.default_rng(8480 + dd).permutation(pool)   # 중첩 뽑기 — 앞 n 이 곡선을 짝지운다
    for n in GRID:
        if (dd, n) in done:
            continue
        idx = perm[:n]
        rj, pj = joint_rho(idx)
        m = Ridge(alpha=1.0).fit(Xr[idx], y[idx])               # α=1 고정 — 하이퍼 체제 혼합 차단
        pr_ = m.predict(Xr[ev])
        okr = np.isfinite(pr_) & np.isfinite(y[ev])
        rr = float(spearmanr(pr_[okr], y[ev][okr])[0])
        rec = {"d": dd, "n": int(n), "rho_joint": round(rj, 4), "rho_ridge": round(rr, 4),
               "delta": round(rj - rr, 4),
               "joint_pred": [round(float(x), 3) for x in pj],
               "ridge_pred": [round(float(x), 4) for x in pr_],
               "초": round(time.time() - t0, 1)}
        with open(CKPT, "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  d{dd} n{n}: 합동 {rj:+.4f} 릿지 {rr:+.4f} Δ {rj-rr:+.4f} ({time.time()-t0:.0f}s)", flush=True)

print(f"완료 — {time.time()-t0:.0f}s", flush=True)
