# 심사 2부 — B1 CV 게이트 · 작은 tau 퇴화 · 러너 recipe 그대로
import sys
sys.path.insert(0, "/Users/ax/world_model")
import numpy as np
from lab import curveshape as CS

SHAPES = ("감쇠", "이중피크", "지연상승", "계단")

def run_B(noise, split_seed=823, g1=100, g2=200):
    gen = {s: CS.synth(s, noise=noise, seed=g1) for s in SHAPES}
    gen2 = {s: CS.synth(s, noise=noise, seed=g2) for s in SHAPES}
    feats_all, feat_of = [], {}
    for s in SHAPES:
        feat_of[s] = CS.shape_features(CS.mean_curve(gen[s]))
        feats_all.append(feat_of[s])
        feats_all.append(CS.shape_features(CS.mean_curve(gen2[s])))
    scale = np.std(np.vstack(feats_all), axis=0, ddof=1)
    rng = np.random.default_rng(split_seed)
    per, same = {}, []
    for s in SHAPES:
        C = gen[s]; ds = []
        for k in range(10):
            pi = rng.permutation(len(C)); h = len(C) // 2
            ds.append(CS.feat_dist(CS.shape_features(CS.mean_curve(C[pi[:h]])),
                                   CS.shape_features(CS.mean_curve(C[pi[h:]])), scale))
        ds.append(CS.feat_dist(feat_of[s], CS.shape_features(CS.mean_curve(gen2[s])), scale))
        per[s] = ds; same += ds
    p95 = float(np.percentile(same, 95))
    cv = {s: (float(np.std(d, ddof=1) / np.mean(d)) if np.mean(d) > 0 else 0.0)
          for s, d in per.items()}
    key = CS.feat_dist(feat_of["감쇠"], feat_of["이중피크"], scale)
    unstable = any(np.mean(per[s]) > 0 and cv[s] > 1.0 for s in SHAPES)
    verdict = "B1(자 무효)" if unstable else ("B2" if key > p95 else "B3")
    return {"noise": noise, "p95": round(p95, 3), "cv": {k: round(v, 2) for k, v in cv.items()},
            "key": round(key, 3), "판정": verdict, "scale_min": round(float(scale.min()), 4)}

for nz in (0.15, 0.25, 0.35, 0.5, 0.7):
    print(run_B(nz))
print()
# 씨앗만 바꿔 B1 이 얼마나 자주 켜지나 (noise 0.35 고정)
flips = []
for ss in range(20):
    r = run_B(0.35, split_seed=ss, g1=100 + ss, g2=300 + ss)
    flips.append(r["판정"])
print("씨앗 20개 판정 분포:", {v: flips.count(v) for v in set(flips)})

print()
print("== 작은 tau 퇴화: 서로 다른 급감 곡선이 both 정규화 후 겹침 ==")
t = np.arange(45.0)
a = 3.0 * np.exp(-t / 0.7)                 # 하루 만에 급감
b = np.concatenate([[3.0, 0.3], 0.3 * np.exp(-(t[2:] - 2) / 5)])   # 뒤꼬리 완전 다름
print("tau a:", CS.tau_of(a), "tau b:", CS.tau_of(b))
print("amp만 RMSE:", round(CS.pair_rmse(a, b, 'amp'), 4),
      "| both RMSE:", round(CS.pair_rmse(a, b, 'both'), 4))
