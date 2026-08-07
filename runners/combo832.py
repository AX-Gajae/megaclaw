# 노트 832a — 자 결합 (사전등록 '832a' · 커밋 후 측정)
import json, sys, time
from itertools import combinations
import numpy as np
sys.path.insert(0, "/Users/ax/world_model")
from lab import curveshape as CS

t0 = time.time()
SHAPES = ("감쇠", "이중피크", "지연상승", "계단")
# 눈금: 830 백필 이전과 동일 관례 — 게임 실측 바닥(90d)
from lab.harness import load
curves = CS.load_curves(90)
data = load()
dom, _ = CS.domain_curves(curves, data)
game_floor = float(np.mean(CS.floor_of(dom["게임"][0], "both", seed=3)))
grid = (0.15, 0.3, 0.5, 0.8, 1.2, 1.8, 2.7)
cand = [(abs(float(np.mean(CS.floor_of(CS.synth("감쇠", noise=nz, seed=111), "both", seed=4))) - game_floor), nz) for nz in grid]
_, NOISE = min(cand)
syn_floor = float(np.mean(CS.floor_of(CS.synth("감쇠", noise=NOISE, seed=111), "both", seed=4)))
scale_ok = abs(syn_floor - game_floor) <= 0.5 * game_floor
print(f"눈금: 게임 {game_floor:.4f} · noise {NOISE} · 합성 {syn_floor:.4f} · 게이트 {scale_ok} ({time.time()-t0:.0f}s)", flush=True)
OUT = {"눈금": {"게임": round(game_floor, 4), "noise": NOISE, "합성": round(syn_floor, 4), "게이트": bool(scale_ok)}}
if not scale_ok:
    OUT["판정"] = "1.배선 — 눈금 실패"
else:
    gens = {s: [CS.synth(s, noise=NOISE, seed=100 + i)] +
               [CS.synth(s, noise=NOISE, seed=200 + 10 * i + k) for k in range(6)]
            for i, s in enumerate(SHAPES)}
    feats = {s: [CS.shape_features(CS.mean_curve(C)) for C in gens[s]] for s in SHAPES}
    allf = np.vstack([f for s in SHAPES for f in feats[s]])
    scale = np.std(allf, axis=0, ddof=1)
    same_d = [CS.feat_dist(a, b, scale) for s in SHAPES for a, b in combinations(feats[s], 2)]
    p95 = float(np.percentile(same_d, 95))

    def combo(C1, C2, f1, f2, seedq):
        r = CS.pair_rmse(CS.mean_curve(C1), CS.mean_curve(C2), "both")
        pf = CS.pair_floor(CS.floor_of(C1, "both", seed=seedq), CS.floor_of(C2, "both", seed=seedq + 1))
        n95 = CS.joint_null(C1, C2, "both", seed=seedq + 2)
        rv = CS.verdict(r, pf, n95)
        fd = CS.feat_dist(f1, f2, scale)
        if rv == "다르다" or fd > p95:
            cv = "다르다"
        elif rv == "같다" and fd <= p95:
            cv = "같다"
        else:
            cv = "모른다"
        return {"RMSE": rv, "배수": round(r / pf, 2), "특징": round(fd, 3), "결합": cv}

    diff_pairs = {}
    for i, j in combinations(range(4), 2):
        s1, s2 = SHAPES[i], SHAPES[j]
        diff_pairs[f"{s1}-{s2}"] = combo(gens[s1][0], gens[s2][0], feats[s1][0], feats[s2][0], 10 + i * 4 + j)
    # 같은형태 위양성: 독립 재생성 쌍(원본 대 재생성 6) 4형 × 6 = 24쌍
    fp = 0; total = 0
    same_detail = {}
    for i, s in enumerate(SHAPES):
        vs = []
        for k in range(1, 7):
            c = combo(gens[s][0], gens[s][k], feats[s][0], feats[s][k], 100 + i * 10 + k)
            vs.append(c["결합"]); total += 1
            fp += c["결합"] == "다르다"
        same_detail[s] = vs
    OUT["같은형태 p95"] = round(p95, 3)
    OUT["다른형태 6쌍"] = diff_pairs
    OUT["같은형태 위양성"] = {"다르다": fp, "전체": total, "율": round(fp / total, 3), "상세": same_detail}
    all_diff = all(v["결합"] == "다르다" for v in diff_pairs.values())
    key_ok = diff_pairs["감쇠-이중피크"]["결합"] == "다르다"
    ls_ok = diff_pairs["지연상승-계단"]["결합"] == "다르다"
    if fp / total > 0.05:
        OUT["판정"] = f"4.위양성 — {fp}/{total}"
    elif all_diff:
        OUT["판정"] = "2.전부 가름 — 능력 카드 한계 삭제 후보(확인 후)"
    elif key_ok and not ls_ok:
        OUT["판정"] = "3.부분 — 감쇠-이중피크는 가르고 지연상승-계단은 어느 자로도 못 봄"
    else:
        OUT["판정"] = f"그 외 — 감쇠-이중피크 {diff_pairs['감쇠-이중피크']['결합']}"
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps(OUT, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out832a.json", "w"), ensure_ascii=False, indent=1)
