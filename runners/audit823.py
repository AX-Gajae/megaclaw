# 심사용 수치 검증 — curveshape.py 의 함정 재현 (읽기 전용)
import sys
sys.path.insert(0, "/Users/ax/world_model")
import numpy as np
from lab import curveshape as CS

t = np.arange(45.0)

print("== (1) tau_of / normalize ==")
mono = np.log1p(np.linspace(0, 300, 45))          # 단조 증가, argmax=44
print("단조증가 tau_of:", CS.tau_of(mono), "(docstring 은 44 라고 주장)")
nm = CS.normalize(mono, "both")
print("  재표집 후 사용 구간: u_max =", 3.0 * max(CS.tau_of(mono), 1.0), "일 / 45일")
print("  정규화 곡선이 원곡선의 처음 며칠만 반영:", np.allclose(
    nm, (np.interp(np.linspace(0, 3, 45), t, mono) - np.interp(np.linspace(0,3,45), t, mono).min())
        / (np.interp(np.linspace(0,3,45), t, mono).max() - np.interp(np.linspace(0,3,45), t, mono).min())))

pk43 = np.concatenate([np.linspace(0, 3, 44), [3.01]])   # 피크 43~44 근처, 안 내려옴
print("피크44 근처 미하강 tau:", CS.tau_of(pk43))

flat = np.ones(45)
print("평평 tau_of:", CS.tau_of(flat), "→ normalize:", CS.normalize(flat, "both")[:3])

dual = np.exp(-((t - 3) ** 2) / 18.0) + 0.8 * np.exp(-((t - 24) ** 2) / 32.0)
dual = 3.0 * dual / dual.max()
tau_d = CS.tau_of(dual)
print("이중피크 base: argmax =", int(np.argmax(dual)), "tau =", tau_d,
      "→ 재표집 창 [0,", 3 * tau_d, "] — 둘째 피크(24일) 포함 여부:", 3 * tau_d >= 24)
nd = CS.normalize(dual, "both")
decay = 3.0 * np.exp(-t / 8.0)
print("  base 끼리 RMSE both:", round(CS.pair_rmse(decay, dual, 'both'), 4),
      "| amp만:", round(CS.pair_rmse(decay, dual, 'amp'), 4))
print("  정규화된 이중피크의 피크 수(창 절단 후):", CS._peaks(CS._smooth((nd - nd.min())/(nd.max()-nd.min())), 0.15))

print()
print("== (6) _peaks 대 scipy prominence ==")
from scipy.signal import find_peaks
# 감쇠 곡선의 어깨(주피크 옆 작은 굴곡): 표준 prominence 로는 무시, 전역최소 방식은 카운트
c = np.exp(-t / 8.0)
c[5] += 0.02; c[6] += 0.05; c[7] += 0.02        # 어깨 굴곡 (진폭 1 대비 0.05)
z = (c - c.min()) / (c.max() - c.min())
s = CS._smooth(z)
mine = CS._peaks(s, 0.15)
sp = len(find_peaks(s, prominence=0.15)[0])
print("어깨 있는 감쇠: 직접 _peaks =", mine, "| scipy =", sp)
# 원인 데모: 둘째 극대의 왼쪽 base 를 전역 최소로 잡는다
demo = np.array([0.0, 1.0, 0.9, 0.95, 0.9, 0.5, 0.3, 0.1, 0.05, 0.0])
print("데모 [0,1,.9,.95,...]: 직접 =", CS._peaks(demo, 0.15),
      "| scipy(prom 0.15) =", len(find_peaks(demo, prominence=0.15)[0]))

print()
print("== (B) 재현: scale · p95 · 판정 민감도 ==")
NOISE = 0.35
SHAPES = ("감쇠", "이중피크", "지연상승", "계단")
gen = {s: CS.synth(s, noise=NOISE, seed=100) for s in SHAPES}
gen2 = {s: CS.synth(s, noise=NOISE, seed=200) for s in SHAPES}
feats_all, feat_of = [], {}
for s in SHAPES:
    feat_of[s] = CS.shape_features(CS.mean_curve(gen[s]))
    feats_all.append(feat_of[s])
    feats_all.append(CS.shape_features(CS.mean_curve(gen2[s])))
scale = np.std(np.vstack(feats_all), axis=0, ddof=1)
print("scale(SD, 8표본):", np.round(scale, 4), " min =", scale.min())
print("특징 벡터:", {s: np.round(feat_of[s], 3).tolist() for s in SHAPES})

# 피크 수: 직접 _peaks 대 scipy — 반쪽 평균에서 갈리는가
rng = np.random.default_rng(0)
for s in SHAPES:
    C = gen[s]
    cnt_mine, cnt_sp = [], []
    for k in range(20):
        pi = rng.permutation(len(C)); h = len(C) // 2
        m = CS.mean_curve(C[pi[:h]])
        a = m.max() - m.min()
        zz = (m - m.min()) / a
        ss = CS._smooth(zz)
        cnt_mine.append(CS._peaks(ss, 0.15))
        cnt_sp.append(len(find_peaks(ss, prominence=0.15)[0]))
    print(f"  {s}: 반쪽 20회 피크수 직접 {sorted(set(cnt_mine))} (평균 {np.mean(cnt_mine):.2f})"
          f" | scipy {sorted(set(cnt_sp))} (평균 {np.mean(cnt_sp):.2f})")

# (5) p95 안정성: 뽑기 rng 씨앗과 재생성 씨앗을 바꿔 p95 분포
def p95_of(split_seed, g1seed, g2seed):
    gA = {s: CS.synth(s, noise=NOISE, seed=g1seed) for s in SHAPES}
    gB = {s: CS.synth(s, noise=NOISE, seed=g2seed) for s in SHAPES}
    fa, fo = [], {}
    for s in SHAPES:
        fo[s] = CS.shape_features(CS.mean_curve(gA[s]))
        fa.append(fo[s]); fa.append(CS.shape_features(CS.mean_curve(gB[s])))
    sc = np.std(np.vstack(fa), axis=0, ddof=1)
    rng = np.random.default_rng(split_seed)
    same = []
    for s in SHAPES:
        C = gA[s]
        for k in range(10):
            pi = rng.permutation(len(C)); h = len(C) // 2
            same.append(CS.feat_dist(CS.shape_features(CS.mean_curve(C[pi[:h]])),
                                     CS.shape_features(CS.mean_curve(C[pi[h:]])), sc))
        same.append(CS.feat_dist(fo[s], CS.shape_features(CS.mean_curve(gB[s])), sc))
    key = CS.feat_dist(fo["감쇠"], fo["이중피크"], sc)
    return float(np.percentile(same, 95)), key

res = [p95_of(ss, gs, gs + 100) for ss, gs in
       [(823, 100), (1, 100), (2, 100), (3, 100), (823, 101), (823, 102), (7, 103), (11, 104)]]
print("p95 (씨앗 8조합):", [round(a, 3) for a, _ in res])
print("감쇠-이중피크 거리:", [round(b, 3) for _, b in res])
print("B2/B3 판정:", ["B2" if b > a else "B3" for a, b in res])

# (3) AM 대 RSS — 814 장부 숫자로 직접
f_game, f_mob, f_wan = 0.030, 0.1273, 0.0601
pairs = {"게임-모바일": (0.0864, f_game, f_mob), "모바일-세계애니": (0.1584, f_mob, f_wan),
         "게임-세계애니": (0.1864, f_game, f_wan)}
print()
print("== (3) 쌍바닥 AM 대 RSS (814 장부 수치 대입) ==")
for k, (r, a, b) in pairs.items():
    rss = float(np.hypot(a, b)); am = (a + b) / 2
    print(f"  {k}: rmse {r} | RSS {rss:.4f} → {r/rss:.2f}x → {CS.verdict(r, rss)}"
          f" | AM {am:.4f} → {r/am:.2f}x → {CS.verdict(r, am)}")
