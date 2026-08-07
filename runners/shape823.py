# 노트 823 — 곡선 층 수리: (A) 겹침 제외 재측정 · (B) 형태 특징 자
# 사전등록: prereg823.md · 파이프라인: lab/curveshape.py (규약 41 수리)
import json, re, sys, time
import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from lab import curveshape as CS
from lab.harness import load
from lab.decay import AXD, AX

t0 = time.time()
OUT = {}

curves = CS.load_curves()
data = load()
dom, wire = CS.domain_curves(curves, data)
total = sum(len(ids) for _, ids in dom.values())
OUT["배선"] = {"곡선 전체(45일+)": len(curves), "학습 곡선 합": total,
              "재현 목표": "2,137 ±25% = [1603, 2671]", "도메인": {k: len(i) for k, (_, i) in dom.items()},
              "wire": wire}
print(json.dumps(OUT["배선"], ensure_ascii=False), flush=True)

def norm(s):
    s = str(s or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(r"[^0-9a-z가-힣]+", "", s)
    return s

def names_of(dkey):
    f = AX[dkey]
    r = json.loads((AXD / f"{f}.json").read_text())
    return {rid: norm(v.get("name") or v.get("title") or "") for rid, v in r.items()}

def pair_measure(d1, d2, excl=frozenset(), seed=0):
    C1, ids1 = dom[d1]; C2, ids2 = dom[d2]
    k1 = [i for i, r in enumerate(ids1) if r not in excl]
    k2 = [i for i, r in enumerate(ids2) if r not in excl]
    A1, A2 = C1[k1], C2[k2]
    if len(A1) < 30 or len(A2) < 30:
        return None
    r = CS.pair_rmse(CS.mean_curve(A1), CS.mean_curve(A2), "both")
    f1 = CS.floor_of(A1, "both", seed=seed); f2 = CS.floor_of(A2, "both", seed=seed + 1)
    pf = float((np.mean(f1) + np.mean(f2)) / 2)
    return {"n": [len(A1), len(A2)], "rmse": round(r, 4), "쌍바닥": round(pf, 4),
            "배수": round(r / pf, 2), "판정": CS.verdict(r, pf),
            "바닥 SD": [round(float(np.std(f1, ddof=1)), 4), round(float(np.std(f2, ddof=1)), 4)]}

# ── (A) 세 쌍 v2 무제외 (재현 게이트) + 게임-모바일 제외 ──────────
PAIRS = [("게임", "모바일"), ("모바일", "세계애니"), ("게임", "세계애니")]
REPRO814 = {"게임-모바일": "같다", "모바일-세계애니": "같다", "게임-세계애니": "모른다"}
A = {}
for d1, d2 in PAIRS:
    A[f"{d1}-{d2}"] = pair_measure(d1, d2)
OUT["(A) v2 무제외"] = A

# 겹침 id 집합 (양쪽 도메인에서 그 제목 전부 제외)
share = {}
for d1, d2 in PAIRS:
    n1, n2 = names_of(d1), names_of(d2)
    common = (set(n1.values()) & set(n2.values())) - {""}
    ids = {r for r, nm in n1.items() if nm in common} | {r for r, nm in n2.items() if nm in common}
    share[f"{d1}-{d2}"] = {"제목": len(common), "레코드": len(ids), "ids": ids}
OUT["(A) 겹침"] = {k: {"제목": v["제목"], "레코드": v["레코드"]} for k, v in share.items()}

AX_ = {}
for d1, d2 in PAIRS:
    key = f"{d1}-{d2}"
    if share[key]["제목"] > 0:
        AX_[key] = pair_measure(d1, d2, excl=frozenset(share[key]["ids"]), seed=7)
OUT["(A) 제외 후"] = AX_

repro_ok = all(A[k] and A[k]["판정"] == REPRO814[k] for k in REPRO814)
gm0, gm1 = A.get("게임-모바일"), AX_.get("게임-모바일")
if not repro_ok:
    OUT["(A) 판정"] = "A1.배선 — v2 가 814 판정을 질적으로 재현 못함: " + json.dumps(
        {k: (A[k] or {}).get("판정") for k in REPRO814}, ensure_ascii=False)
elif gm1 is None:
    OUT["(A) 판정"] = "A1.배선 — 제외 후 행 부족"
elif gm1["판정"] == "같다":
    OUT["(A) 판정"] = f"A3.복권 — 제외 후에도 같다({gm1['배수']}×) · 겹침 무해"
else:
    OUT["(A) 판정"] = f"A2.동어반복 — 제외 후 {gm1['판정']}({gm1['배수']}×) · 814 게임-모바일 철회"
print(json.dumps({k: OUT[k] for k in ("(A) v2 무제외", "(A) 겹침", "(A) 제외 후", "(A) 판정")},
                 ensure_ascii=False, indent=1), flush=True)

# ── (B) 합성 4형 + 형태 특징 자 ──────────────────────────────────
SHAPES = ("감쇠", "이중피크", "지연상승", "계단")
# 잡음 눈금: 감쇠형 바닥(both)이 실측 게임 바닥에 가장 가까운 noise 선택
game_floor = float(np.mean(CS.floor_of(dom["게임"][0], "both", seed=3)))
cand = []
for nz in (0.15, 0.25, 0.35, 0.5, 0.7):
    f = float(np.mean(CS.floor_of(CS.synth("감쇠", noise=nz, seed=11), "both", seed=4)))
    cand.append((abs(f - game_floor), nz, f))
_, NOISE, syn_floor = min(cand)
OUT["(B) 눈금"] = {"게임 바닥": round(game_floor, 4), "채택 noise": NOISE,
                  "합성 감쇠 바닥": round(syn_floor, 4)}

gen = {s: {0: CS.synth(s, noise=NOISE, seed=100 + i) for i in (0,)} for s in SHAPES}
gen2 = {s: CS.synth(s, noise=NOISE, seed=200) for s in SHAPES}   # 독립 재생성

# RMSE 판정(818 재현 대조)
brm = {}
for i in range(len(SHAPES)):
    for j in range(i + 1, len(SHAPES)):
        s1, s2 = SHAPES[i], SHAPES[j]
        C1, C2 = gen[s1][0], gen[s2][0]
        r = CS.pair_rmse(CS.mean_curve(C1), CS.mean_curve(C2), "both")
        pf = float((np.mean(CS.floor_of(C1, "both", seed=5)) +
                    np.mean(CS.floor_of(C2, "both", seed=6))) / 2)
        brm[f"{s1}-{s2}"] = {"rmse": round(r, 4), "배수": round(r / pf, 2),
                             "판정": CS.verdict(r, pf)}
OUT["(B) RMSE 판정"] = brm

# 특징 자: 같은-형태 분포(반쪽 10뽑기 + 독립 재생성) → p95 문턱
rng = np.random.default_rng(823)
feats_all = []
same_d, feat_of = [], {}
for s in SHAPES:
    C = gen[s][0]
    feat_of[s] = CS.shape_features(CS.mean_curve(C))
    feats_all.append(feat_of[s])
    feats_all.append(CS.shape_features(CS.mean_curve(gen2[s])))
scale = np.std(np.vstack(feats_all), axis=0, ddof=1)
per_shape_same = {}
for s in SHAPES:
    C = gen[s][0]
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
diff_d = {}
for i in range(len(SHAPES)):
    for j in range(i + 1, len(SHAPES)):
        s1, s2 = SHAPES[i], SHAPES[j]
        diff_d[f"{s1}-{s2}"] = round(CS.feat_dist(feat_of[s1], feat_of[s2], scale), 3)
OUT["(B) 특징 자"] = {"같은형태 p95": round(p95, 3), "같은형태 CV": {k: round(v, 2) for k, v in cv.items()},
                     "다른형태 거리": diff_d,
                     "특징(평균 곡선)": {s: [round(float(x), 3) for x in feat_of[s]] for s in SHAPES}}

unstable = any(np.mean(per_shape_same[s]) > 0 and cv[s] > 1.0 for s in SHAPES)
key_d = diff_d["감쇠-이중피크"]
if unstable:
    OUT["(B) 판정"] = "B1.자 무효 — 같은-형태 거리 불안정(CV>1)"
elif key_d > p95:
    OUT["(B) 판정"] = f"B2.자 개선 — 감쇠-이중피크 {key_d} > p95 {round(p95,3)} (RMSE 는 {brm['감쇠-이중피크']['판정']})"
else:
    OUT["(B) 판정"] = f"B3.자 한계 — 감쇠-이중피크 {key_d} ≤ p95 {round(p95,3)}"

# 실측 3쌍 병기(특징 자)
realf = {}
for d1, d2 in PAIRS:
    f1 = CS.shape_features(CS.mean_curve(dom[d1][0]))
    f2 = CS.shape_features(CS.mean_curve(dom[d2][0]))
    realf[f"{d1}-{d2}"] = round(CS.feat_dist(f1, f2, scale), 3)
OUT["(B) 실측 3쌍 특징 거리(병기)"] = realf

OUT["초"] = round(time.time() - t0, 1)
print(json.dumps({k: OUT[k] for k in ("(B) 눈금", "(B) RMSE 판정", "(B) 특징 자", "(B) 판정",
                                      "(B) 실측 3쌍 특징 거리(병기)", "초")}, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out823.json", "w"),
          ensure_ascii=False, indent=1, default=str)
print("완료", flush=True)
