# 노트 838 — 영화 실측 곡선 대 안정 무리 (사전등록 '838' · 커밋 후 측정)
import datetime as dt
import json, sys, time
import numpy as np
sys.path.insert(0, "/Users/ax/world_model")
from lab import curveshape as CS
from lab.harness import load

t0 = time.time()
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
            series.setdefault(k, {})[d] = c[3]   # 일관객

curves = []
for m in FR["명단"]:
    k = (m["제목"], m["개봉일"])
    if k[1] >= "2025-01-01":      # 학습 구간만(decay 관례 — 유보 곡선 안 봄)
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
        curves.append(cv)
C_raw = np.vstack(curves) if curves else np.zeros((0, 90))
print(f"영화 학습 곡선(관측≥60일) {len(C_raw)} ({time.time()-t0:.0f}s)", flush=True)

def nan_mean_curve(C):
    mc = np.nanmean(C, axis=0)
    # 결측 날은 이웃 보간(끝은 최근접)
    idx = np.arange(len(mc))
    ok = np.isfinite(mc)
    return np.interp(idx, idx[ok], mc[ok])

def smooth7(C):
    out = C.copy()
    for i in range(len(out)):
        s = out[i]
        ok = np.isfinite(s)
        si = np.interp(np.arange(90), np.arange(90)[ok], s[ok])
        k = np.ones(7) / 7
        pad = 3
        x = np.concatenate([si[pad:0:-1], si, si[-2:-2 - pad:-1]])
        out[i] = np.convolve(x, k, mode="valid")
    return out

# 위키 무리(같은 기계 · 90일)
wk = CS.load_curves(90)
wdom, _ = CS.domain_curves(wk, load())
STABLE = ("게임", "모바일", "세계애니")

def floor_nan(C, mode, draws=10, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    n = len(C)
    for _ in range(draws):
        pi = rng.permutation(n); h = n // 2
        out.append(CS.pair_rmse(nan_mean_curve(C[pi[:h]]), nan_mean_curve(C[pi[h:]]), mode))
    return out

OUT = {"곡선 수": int(len(C_raw))}
arms = {}
for arm, Cm in (("A(원곡선)", C_raw), ("B(7일 평활)", smooth7(C_raw))):
    mc = nan_mean_curve(Cm)
    amp = CS.amp_of(mc)
    f_self = floor_nan(Cm, "both", seed=8)
    self_floor = float(np.mean(f_self))
    rowset = {"진폭": round(amp, 3), "자기 바닥": round(self_floor, 4), "쌍": {}}
    for d in STABLE:
        Cw = wdom[d][0]
        r = CS.pair_rmse(mc, CS.mean_curve(Cw), "both")
        pf = CS.pair_floor(f_self, CS.floor_of(Cw, "both", seed=9))
        # 합동 널: 영화 곡선(보간판)과 위키 곡선 섞기
        Ci = np.vstack([np.interp(np.arange(90), np.arange(90)[np.isfinite(c)],
                                  c[np.isfinite(c)]) for c in Cm])
        p95 = CS.joint_null(Ci, Cw, "both", seed=10)
        rowset["쌍"][f"영화-{d}"] = {"rmse": round(r, 4), "쌍바닥": round(pf, 4),
            "배수": round(r / pf, 2), "널p95": round(p95, 4),
            "판정": CS.verdict(r, pf, p95)}
    arms[arm] = rowset
    print(json.dumps({arm: rowset}, ensure_ascii=False), flush=True)
OUT["팔"] = arms

# 기존 무리 바닥(v2 눈금) — 배선 게이트 재료
mob_floor = float(np.mean(CS.floor_of(wdom["모바일"][0], "both", seed=11)))
OUT["모바일 바닥(v2)"] = round(mob_floor, 4)
selfA = arms["A(원곡선)"]["자기 바닥"]
vA = [v["판정"] for v in arms["A(원곡선)"]["쌍"].values()]
vB = [v["판정"] for v in arms["B(7일 평활)"]["쌍"].values()]
if len(C_raw) < 60 or selfA > 3 * mob_floor:
    OUT["판정"] = f"1.배선 — 곡선 {len(C_raw)} · 자기바닥 {selfA}(모바일 {mob_floor:.3f}의 3배 게이트)"
elif all(x == "다르다" for x in vA) and sum(x == "다르다" for x in vB) >= 2:
    OUT["판정"] = "2.족 분리 — 영화 곡선은 위키 감쇠 무리와 다른 족(평활로도 안 겹침)"
elif sum(x in ("같다", "모른다") for x in vB) >= 2:
    OUT["판정"] = "3.무리 확장 — 주간 진동을 걷어내면 같은 족 후보"
else:
    OUT["판정"] = f"4.혼합 — A {vA} · B {vB}"
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps({k: OUT[k] for k in ("곡선 수", "모바일 바닥(v2)", "판정", "초")}, ensure_ascii=False), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out838.json", "w"), ensure_ascii=False, indent=1)
