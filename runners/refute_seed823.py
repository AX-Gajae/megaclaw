# 반증 시도 — 발견: "합성 4형이 같은 seed 를 공유해 다른-형태 쌍 잡음이 상쇄, p95 널과 비대칭"
import sys, json
import numpy as np
sys.path.insert(0, "/Users/ax/world_model")
from lab import curveshape as CS

SHAPES = ("감쇠", "이중피크", "지연상승", "계단")

# ── (1) 사실 확인: 같은 seed → 형태 불문 같은 잡음·규모 수열인가 ──
def residual_noise(shape, noise, seed):
    """synth 를 재현해 잡음 성분(noise*low)과 scale 수열을 복원."""
    rng = np.random.default_rng(seed)
    t = np.arange(45.0)
    C = CS.synth(shape, noise=noise, seed=seed)
    lows, scales = [], []
    for _ in range(len(C)):
        w = rng.normal(0, 1, 45)
        lows.append(CS._smooth(w, 9))
        scales.append(rng.uniform(0.5, 2.0))
    return np.vstack(lows), np.array(scales), C

low1, sc1, C1 = residual_noise("감쇠", 0.35, 100)
low2, sc2, C2 = residual_noise("이중피크", 0.35, 100)
print("(1) seed=100 잡음 수열 동일(감쇠 vs 이중피크):", np.array_equal(low1, low2),
      "| scale 수열 동일:", np.array_equal(sc1, sc2))
# 클리핑 전 재구성 검증
t = np.arange(45.0)
base = 3.0 * np.exp(-t / 8.0) / np.exp(-t / 8.0).max()
recon = np.clip(base * sc1[:, None] + 0.35 * low1, 0, None)
print("    synth 재구성 일치(감쇠):", np.allclose(recon, C1))
# 평균 곡선에서 잡음 상쇄: (M1 - M2) 가 (base1-base2)*mean(scale) 와 얼마나 같나
b2 = np.exp(-((t - 3) ** 2) / 18.0) + 0.8 * np.exp(-((t - 24) ** 2) / 32.0)
b2 = 3.0 * b2 / b2.max()
M1, M2 = C1.mean(0), C2.mean(0)
pure = (base - b2) * sc1.mean()
print("    평균곡선 차 vs 순수 base 차 최대 이탈(클리핑 탓):",
      round(float(np.max(np.abs((M1 - M2) - pure))), 5),
      "| 잡음항 크기(noise*mean(low) std):", round(float((0.35 * low1.mean(0)).std()), 5))

# 독립 seed 면 잡음이 안 상쇄됨을 대조
low3, sc3, C3 = residual_noise("이중피크", 0.35, 101)
M3 = C3.mean(0)
print("    [대조] seed 101 이중피크: 평균곡선 차 - 순수차 최대 이탈:",
      round(float(np.max(np.abs((M1 - M3) - (base - b2) * ((sc1.mean()+sc3.mean())/2)))), 5))

# ── (2) 실질: B팔 판정이 shared vs per-shape seed 로 달라지나 ──
def run_b(noise, seeds1, seeds2, split_seed=823):
    gen  = {s: CS.synth(s, noise=noise, seed=seeds1[i]) for i, s in enumerate(SHAPES)}
    gen2 = {s: CS.synth(s, noise=noise, seed=seeds2[i]) for i, s in enumerate(SHAPES)}
    rng = np.random.default_rng(split_seed)
    feats_all, feat_of, per_shape_same, same_d = [], {}, {}, []
    for s in SHAPES:
        feat_of[s] = CS.shape_features(CS.mean_curve(gen[s]))
        feats_all.append(feat_of[s])
        feats_all.append(CS.shape_features(CS.mean_curve(gen2[s])))
    scale = np.std(np.vstack(feats_all), axis=0, ddof=1)
    for s in SHAPES:
        C = gen[s]; ds = []
        for k in range(10):
            pi = rng.permutation(len(C)); h = len(C) // 2
            ds.append(CS.feat_dist(CS.shape_features(CS.mean_curve(C[pi[:h]])),
                                   CS.shape_features(CS.mean_curve(C[pi[h:]])), scale))
        ds.append(CS.feat_dist(feat_of[s], CS.shape_features(CS.mean_curve(gen2[s])), scale))
        per_shape_same[s] = ds; same_d += ds
    p95 = float(np.percentile(same_d, 95))
    cv = {s: (float(np.std(d, ddof=1) / np.mean(d)) if np.mean(d) > 0 else 0.0)
          for s, d in per_shape_same.items()}
    key_d = CS.feat_dist(feat_of["감쇠"], feat_of["이중피크"], scale)
    unstable = any(np.mean(per_shape_same[s]) > 0 and cv[s] > 1.0 for s in SHAPES)
    v = "B1" if unstable else ("B2" if key_d > p95 else "B3")
    # 다른-형태 6쌍 전부
    dd = {}
    for i in range(4):
        for j in range(i+1, 4):
            dd[f"{SHAPES[i][:2]}-{SHAPES[j][:2]}"] = round(
                CS.feat_dist(feat_of[SHAPES[i]], feat_of[SHAPES[j]], scale), 3)
    return {"p95": round(p95, 4), "key_d": round(key_d, 4), "판정": v,
            "maxCV": round(max(cv.values()), 2), "diff_d": dd}

print("\n(2) noise 후보 5개 — shared(러너 그대로: 전형태 100/200) vs per-shape(100+i/200+i)")
for nz in (0.15, 0.25, 0.35, 0.5, 0.7):
    a = run_b(nz, [100]*4, [200]*4)
    b = run_b(nz, [100+i for i in range(4)], [200+i for i in range(4)])
    print(f" nz={nz}: shared {a['판정']} key_d={a['key_d']} p95={a['p95']} maxCV={a['maxCV']}"
          f" || pershape {b['판정']} key_d={b['key_d']} p95={b['p95']} maxCV={b['maxCV']}")
    print(f"   shared diff_d={a['diff_d']}")
    print(f"   persh  diff_d={b['diff_d']}")

print("\n(3) 20조합 집계 (noise 0.35) — 판정 분포 비교")
tal_a, tal_b = {}, {}
for gs in (100, 300, 500, 700, 900):
    for ss in (823, 1, 42, 7):
        a = run_b(0.35, [gs]*4, [gs+100]*4, split_seed=ss)
        b = run_b(0.35, [gs+i for i in range(4)], [gs+100+i for i in range(4)], split_seed=ss)
        tal_a[a["판정"]] = tal_a.get(a["판정"], 0) + 1
        tal_b[b["판정"]] = tal_b.get(b["판정"], 0) + 1
print(" shared:", tal_a, "| per-shape:", tal_b)

# 같은-형태 gen vs gen2 거리(독립 100 대 200)와 다른-형태 shared 거리의 잡음 성분 크기 비교
print("\n(4) 잡음 독립성 비대칭의 크기 — 같은형태 gen-gen2 거리(독립) 대 다른형태(공유) 잡음 기여")
for nz in (0.35,):
    a = run_b(nz, [100]*4, [200]*4)
    # 다른-형태 거리를 '독립 seed' 로 20회 재추정해 산포를 본다
    dd_samples = []
    for rep in range(20):
        s1 = CS.synth("감쇠", noise=nz, seed=1000+2*rep)
        s2 = CS.synth("이중피크", noise=nz, seed=1000+2*rep+1)
        gen2r = {s: CS.synth(s, noise=nz, seed=3000+rep*10+i) for i, s in enumerate(SHAPES)}
        feats = [CS.shape_features(CS.mean_curve(CS.synth(s, noise=nz, seed=5000+rep*10+i)))
                 for i, s in enumerate(SHAPES)]
        sc = np.std(np.vstack(feats + [CS.shape_features(CS.mean_curve(gen2r[s])) for s in SHAPES]),
                    axis=0, ddof=1)
        dd_samples.append(CS.feat_dist(CS.shape_features(CS.mean_curve(s1)),
                                       CS.shape_features(CS.mean_curve(s2)), sc))
    print(f" 감쇠-이중피크 독립seed 20회: mean={np.mean(dd_samples):.4f} sd={np.std(dd_samples, ddof=1):.4f}"
          f" min={min(dd_samples):.4f} max={max(dd_samples):.4f} | shared 한 번={a['key_d']}")
