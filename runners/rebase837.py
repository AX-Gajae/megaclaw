# 노트 837 — 재기선 집행 (사전등록 '837' · 빌드 완료 후 실행)
# Data 는 러너가 손수 조립(tri_domain 커밋은 판정 후 — 반쯤 배선 금지)
import json, sys, time
import numpy as np
from scipy.stats import spearmanr, rankdata

sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, guards as G
from lab.forms import REGISTRY
from lab.harness import Data

t0 = time.time()
SEEDS = list(range(12))
T = 2025.0

# ── KOBIS 도메인 조립 (kobis_axes.json → (A, M, y, t)) ───────────
KA = json.load(open("/Users/ax/world_model/data/state/kobis_axes.json"))
build_meta = json.load(open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out836_build.json"))
assert build_meta["항등식(행+결측+실패=897)"], "836 항등식 실패"
ALL5 = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
ids = list(KA)
A = np.array([[KA[i]["axes"][a] for a in ALL5] for i in ids], float)
M = np.array([[KA[i]["mask"][a] for a in ALL5] for i in ids], float)
y_raw = np.array([KA[i]["y"] for i in ids], float)
yr = np.array([float(KA[i]["release_date"][:4]) for i in ids], float)
# 🔴 정정(문안≠코드 자기 적발): 로더 기본(_from_axes_json trend="year")은
# **y 원값 + t=연도** — 중심화하지 않는다(팝업·펀딩·아이돌 관례 동일).
ktr0 = yr < T
y = y_raw
# 살아있는 축 결측 게이트(≤20%)
live_miss = 1 - M[:, :3].mean(axis=0)
print(f"KOBIS 행 {len(ids)} · 학습 {int(ktr0.sum())} · 유보 {int((~ktr0).sum())} · 살아있는 축 결측 {np.round(live_miss,3)}", flush=True)
assert (live_miss <= 0.20).all(), f"결측 게이트 실패 {live_miss}"

data11 = sideaudit.champion_data()
#: 🔴 배선 수리(837 1차 시행의 발견) — axis_order("common") 은 전 도메인
#: 이름 **교집합**이다. 영화에 5개 이름만 주면 공유 축이 36→5 로 붕괴해
#: 기존 도메인 전부가 확장 축(trend/cal/wiki…)을 잃는다(12도메인 판 0.383
#: = 5축 시대 수준으로 실측 확인). 기존 관례대로 **공통 이름 전체를 주고
#: 없는 축은 0.5/마스크 0 열**로 붙인다(harness.load 의 중립 채움과 동일).
common = [a for a in data11.names[sorted(data11.names)[0]]
          if all(a in data11.names[d] for d in data11.dom)]
assert len(common) >= 30, f"공통 축 {len(common)} — 배선 이상"
idx5 = {a: ALL5.index(a) for a in ALL5}
import numpy as _np
A_full = _np.full((len(ids), len(common)), 0.5)
M_full = _np.zeros((len(ids), len(common)))
for j, a in enumerate(common):
    if a in idx5:
        A_full[:, j] = A[:, idx5[a]]
        M_full[:, j] = M[:, idx5[a]]
dom12 = dict(data11.dom); nm12 = dict(data11.names)
dom12["영화"] = (A_full, M_full, y, yr)
nm12["영화"] = list(common)
data12 = Data(dom12, nm12)
data12.yr = dict(data11.yr); data12.yr["영화"] = yr

cls = REGISTRY["F18_bagboost"]["cls"]

def score(f, data, doms):
    out = {}
    preds = {}
    for d in doms:
        yrv = np.asarray(data.yr[d], float)
        yv_all = np.asarray(data.dom[d][2], float)
        kho = np.isfinite(yrv) & (yrv >= T) & np.isfinite(yv_all)
        if kho.sum() < 20:
            continue
        Ah, Mh, yh, th = data.slice(d, kho)
        p = np.asarray(f.predict(d, Ah, Mh, th), float)
        ok = np.isfinite(p) & np.isfinite(yh)
        out[d] = float(spearmanr(p[ok], yh[ok])[0])
        preds[d] = (p[ok], yh[ok])
    return out, preds

rows11, rows12, kobis_r = [], [], []
per11_by_seed, per12_by_seed = [], []
last_preds12 = None
for s in SEEDS:
    f11 = G._fit_on(lambda s=s: cls(seed=s), data11, T, seed=s)
    sc11, _ = score(f11, data11, list(data11.dom))
    f12 = G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s)
    sc12, preds12 = score(f12, data12, list(data12.dom))
    last_preds12 = preds12
    per11_by_seed.append(sc11); per12_by_seed.append(sc12)
    w11 = {d: int(np.isfinite(np.asarray(data11.dom[d][2], float)[
        np.isfinite(np.asarray(data11.yr[d], float)) & (np.asarray(data11.yr[d], float) >= T)]).sum())
        for d in sc11}
    pool11 = float(np.average([sc11[d] for d in sc11], weights=[w11[d] for d in sc11]))
    w12 = dict(w11); w12["영화"] = int((~ktr0).sum())
    pool12 = float(np.average([sc12[d] for d in sc12], weights=[w12[d] for d in sc12]))
    rows11.append(pool11); rows12.append(pool12)
    kobis_r.append(sc12.get("영화", float("nan")))
    print(f"  씨앗 {s}: 11도메인 {pool11:.4f} · 12도메인 {pool12:.4f} · 영화 {sc12.get('영화'):+.4f} ({time.time()-t0:.0f}s)", flush=True)

# 기존 11도메인 부분판 이동(같은 유보 행 · 같은 씨앗 짝)
moves = {}
for d in per11_by_seed[0]:
    ds = [per12_by_seed[i].get(d, np.nan) - per11_by_seed[i].get(d, np.nan) for i in range(len(SEEDS))]
    moves[d] = {"Δ평균": round(float(np.nanmean(ds)), 4), "씨앗 SD": round(float(np.nanstd(ds, ddof=1)), 4)}
big = {d: v for d, v in moves.items() if abs(v["Δ평균"]) > 0.0045}

# 뽑기 SD 재측정 — 마지막 씨앗의 12도메인 예측 위 유보 행 부트스트랩
rng = np.random.default_rng(837)
B = 2000
bs = []
doms_l = list(last_preds12)
for _b in range(B):
    tot_n = 0; acc = 0.0
    for d in doms_l:
        p, yv = last_preds12[d]
        idx = rng.integers(0, len(yv), len(yv))
        r = spearmanr(p[idx], yv[idx])[0]
        acc += r * len(yv); tot_n += len(yv)
    bs.append(acc / tot_n)
new_sd = float(np.std(bs, ddof=1))

OUT = {"KOBIS": {"행": len(ids), "학습": int(ktr0.sum()), "유보": int((~ktr0).sum()),
                 "살아있는 축 결측": [round(float(x), 3) for x in live_miss],
                 "도메인 ρ(씨앗 평균)": round(float(np.nanmean(kobis_r)), 4)},
       "구 11도메인 판(참고 회계)": {"평균": round(float(np.mean(rows11)), 4),
                                    "씨앗 SD": round(float(np.std(rows11, ddof=1)), 4)},
       "🔴 새 기준선(12도메인)": {"평균": round(float(np.mean(rows12)), 4),
                                 "씨앗 SD": round(float(np.std(rows12, ddof=1)), 4),
                                 "주의": "0.4689 와 비교 금지 — 재기선 회계(만화 선례 0.4862→0.4654)"},
       "기존 도메인 이동(짝)": moves,
       "이동 게이트(>0.0045)": big or "없음",
       "새 뽑기 SD(부트스트랩)": round(new_sd, 5),
       "새 2σ": round(2 * new_sd, 5)}
if big:
    OUT["판정"] = f"2.이동 조사 — {list(big)}"
else:
    OUT["판정"] = "3.재기선 확정 — tri_domain 배선 커밋·문패 6건 개시"
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps(OUT, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out837.json", "w"), ensure_ascii=False, indent=1)
print("완료", flush=True)
