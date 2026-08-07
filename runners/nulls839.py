# 노트 839 — 판별 널·모수 표 4-무리 (사전등록 '839' · 커밋 후 측정)
import datetime as dt
import json, sys, time
from itertools import combinations
import numpy as np
sys.path.insert(0, "/Users/ax/world_model")
from lab import curveshape as CS
from lab.harness import load

t0 = time.time()
# 영화 곡선(838 조립 재사용)
B1 = json.load(open("/Users/ax/world_model/data/ingest/kobis/backfill_2023-01-01_full.json"))
B2 = json.load(open("/Users/ax/world_model/data/ingest/kobis/backfill_2026-05-04_90d.json"))
data = {**B1, **B2}
FR = json.load(open("/Users/ax/world_model/data/ingest/kobis/threshold897_frozen.json"))
series = {}
for d, rr in data.items():
    for r in rr:
        k = (r["제목"], r.get("개봉일"))
        c = r["숫자 셀(원본 순서)"]
        if len(c) >= 5:
            series.setdefault(k, {})[d] = c[3]
mov = []
for m in FR["명단"]:
    k = (m["제목"], m["개봉일"])
    if k[1] >= "2025-01-01":
        continue
    sv = series.get(k)
    if not sv:
        continue
    op = dt.date.fromisoformat(k[1])
    cv = np.full(90, np.nan)
    for d, v in sv.items():
        off = (dt.date.fromisoformat(d) - op).days
        if 0 <= off < 90:
            cv[off] = np.log1p(v)
    if np.isfinite(cv).sum() >= 60:
        ok = np.isfinite(cv)
        mov.append(np.interp(np.arange(90), np.arange(90)[ok], cv[ok]))
C_mov = np.vstack(mov)
wk = CS.load_curves(90)
wdom, _ = CS.domain_curves(wk, load())
DOMC = {"영화": C_mov, "게임": wdom["게임"][0], "모바일": wdom["모바일"][0], "세계애니": wdom["세계애니"][0]}
print(f"곡선: {[f'{d}:{len(C)}' for d, C in DOMC.items()]} ({time.time()-t0:.0f}s)", flush=True)

OUT = {}
# ① 합성 눈금 + 판별력 재확인
game_floor = float(np.mean(CS.floor_of(DOMC["게임"], "both", seed=3)))
mov_floor = float(np.mean(CS.floor_of(C_mov, "both", seed=4)))
grid = (0.15, 0.3, 0.5, 0.8, 1.2, 1.8, 2.7)
target = (game_floor + mov_floor) / 2
cand = [(abs(float(np.mean(CS.floor_of(CS.synth("감쇠", noise=nz, seed=111), "both", seed=5))) - target), nz) for nz in grid]
_, NOISE = min(cand)
syn_floor = float(np.mean(CS.floor_of(CS.synth("감쇠", noise=NOISE, seed=111), "both", seed=5)))
gate = abs(syn_floor - target) <= 0.5 * target
SHAPES = ("감쇠", "이중피크", "지연상승", "계단")
gens = {s: CS.synth(s, noise=NOISE, seed=100 + i) for i, s in enumerate(SHAPES)}
n_same = 0
syn_rows = {}
for s1, s2 in combinations(SHAPES, 2):
    r = CS.pair_rmse(CS.mean_curve(gens[s1]), CS.mean_curve(gens[s2]), "both")
    pf = CS.pair_floor(CS.floor_of(gens[s1], "both", seed=6), CS.floor_of(gens[s2], "both", seed=7))
    p95 = CS.joint_null(gens[s1], gens[s2], "both", seed=8)
    v = CS.verdict(r, pf, p95)
    syn_rows[f"{s1}-{s2}"] = v
    n_same += v == "같다"
OUT["① 합성"] = {"눈금 게이트": bool(gate), "noise": NOISE, "같다 수": n_same, "판정들": syn_rows}
print(json.dumps(OUT["① 합성"], ensure_ascii=False), flush=True)

# ②③ 실측 6쌍 — both 와 time
def pair(d1, d2, mode, seed):
    C1, C2 = DOMC[d1], DOMC[d2]
    r = CS.pair_rmse(CS.mean_curve(C1), CS.mean_curve(C2), mode)
    pf = CS.pair_floor(CS.floor_of(C1, mode, seed=seed), CS.floor_of(C2, mode, seed=seed + 1))
    p95 = CS.joint_null(C1, C2, mode, seed=seed + 2)
    return {"배수": round(r / pf, 2), "판정": CS.verdict(r, pf, p95)}
both_rows, time_rows = {}, {}
ds = list(DOMC)
for i, (d1, d2) in enumerate(combinations(ds, 2)):
    both_rows[f"{d1}-{d2}"] = pair(d1, d2, "both", 20 + i * 3)
    time_rows[f"{d1}-{d2}"] = pair(d1, d2, "time", 50 + i * 3)
OUT["② 실측 6쌍(both)"] = both_rows
OUT["③ 시간만 6쌍"] = time_rows
print(json.dumps({"both": {k: v["판정"] for k, v in both_rows.items()},
                  "time": {k: v["판정"] for k, v in time_rows.items()}}, ensure_ascii=False), flush=True)

# ④ 모수 표
params = {}
for d, C in DOMC.items():
    mc = CS.mean_curve(C)
    params[d] = {"tau(일)": round(CS.tau_of(mc), 1), "진폭": round(CS.amp_of(mc), 3)}
OUT["④ 모수 표"] = params

vb = [v["판정"] for v in both_rows.values()]
mv_time = [time_rows[k]["판정"] for k in time_rows if "영화" in k]
if not gate or n_same > 0:
    OUT["판정"] = f"1.배선 — 눈금 {gate} · 합성 같다 {n_same}"
elif vb.count("다르다") == 0 and vb.count("같다") >= 2 and all(x != "같다" for x in mv_time):
    OUT["판정"] = "2.얇은 장 유지·판정력 상승 — 4-무리 확정 · 813/814/818 문패 완결"
elif "다르다" in vb:
    OUT["판정"] = f"3.모순 — both 에 다르다: {[k for k, v in both_rows.items() if v['판정'] == '다르다']}"
else:
    OUT["판정"] = f"그 외 — both {vb} · 영화 time {mv_time}"
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps({k: OUT[k] for k in ("④ 모수 표", "판정", "초")}, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out839.json", "w"), ensure_ascii=False, indent=1)
