# B팔 재현 검증 — shape823.py 의 (B) 특징 자 블록을 합성 전용으로 재실행
import sys, json
import numpy as np
sys.path.insert(0, "/Users/ax/world_model")
from lab import curveshape as CS

SHAPES = ("감쇠", "이중피크", "지연상승", "계단")

def run_b(noise, gseed1=100, gseed2=200, split_seed=823):
    gen = {s: CS.synth(s, noise=noise, seed=gseed1) for s in SHAPES}
    gen2 = {s: CS.synth(s, noise=noise, seed=gseed2) for s in SHAPES}
    rng = np.random.default_rng(split_seed)
    feats_all, feat_of, per_shape_same, same_d = [], {}, {}, []
    for s in SHAPES:
        C = gen[s]
        feat_of[s] = CS.shape_features(CS.mean_curve(C))
        feats_all.append(feat_of[s])
        feats_all.append(CS.shape_features(CS.mean_curve(gen2[s])))
    scale = np.std(np.vstack(feats_all), axis=0, ddof=1)
    for s in SHAPES:
        C = gen[s]
        ds = []
        for k in range(10):
            pi = rng.permutation(len(C)); h = len(C) // 2
            ds.append(CS.feat_dist(CS.shape_features(CS.mean_curve(C[pi[:h]])),
                                   CS.shape_features(CS.mean_curve(C[pi[h:]])), scale))
        ds.append(CS.feat_dist(feat_of[s], CS.shape_features(CS.mean_curve(gen2[s])), scale))
        per_shape_same[s] = ds
        same_d += ds
    p95 = float(np.percentile(same_d, 95))
    cv = {s: (float(np.std(d, ddof=1) / np.mean(d)) if np.mean(d) > 0 else 0.0)
          for s, d in per_shape_same.items()}
    key_d = CS.feat_dist(feat_of["감쇠"], feat_of["이중피크"], scale)
    unstable = any(np.mean(per_shape_same[s]) > 0 and cv[s] > 1.0 for s in SHAPES)
    if unstable:
        verdict = "B1"
    elif key_d > p95:
        verdict = "B2"
    else:
        verdict = "B3"
    return {"noise": noise, "p95": round(p95, 4),
            "cv": {s: round(v, 2) for s, v in cv.items()},
            "key_d(감쇠-이중피크)": round(key_d, 4), "판정": verdict,
            "same_d(계단)": [round(x, 4) for x in per_shape_same["계단"]]}

print("== 러너 recipe 그대로(분할 823 · 생성 100/200), noise 후보 5개 ==")
for nz in (0.15, 0.25, 0.35, 0.5, 0.7):
    r = run_b(nz)
    print(json.dumps(r, ensure_ascii=False))

print("\n== 씨앗 20조합 (noise 0.35 고정) — 생성씨앗 x 분할씨앗 ==")
tally = {"B1": 0, "B2": 0, "B3": 0}
rows = []
for gs in (100, 300, 500, 700, 900):
    for ss in (823, 1, 42, 7):
        r = run_b(0.35, gseed1=gs, gseed2=gs + 100, split_seed=ss)
        tally[r["판정"]] += 1
        rows.append((gs, ss, r["판정"], r["p95"], r["key_d(감쇠-이중피크)"],
                     max(r["cv"].values())))
for row in rows:
    print(f"gen={row[0]:4d} split={row[1]:4d} 판정={row[2]} p95={row[3]:.4f} "
          f"key_d={row[4]:.4f} maxCV={row[5]:.2f}")
print("집계:", tally)
print("key_d>p95 인 조합:", sum(1 for r in rows if r[4] > r[3]), "/", len(rows))
print("p95 범위:", min(r[3] for r in rows), "~", max(r[3] for r in rows))
