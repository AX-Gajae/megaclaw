# 노트 824 — 곡선 층 수리 2판 (사전등록: 대장 '사전등록 824' · 커밋 후 측정)
import json, re, sys, time
from itertools import combinations
import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from lab import curveshape as CS
from lab.harness import load
from lab.decay import AXD, AX

t0 = time.time()
OUT = {}

curves = CS.load_curves(90)
data = load()
dom, wire = CS.domain_curves(curves, data)
n90 = len(curves)
count_ok = 1603 <= n90 <= 2671
OUT["배선"] = {"90일 곡선 수": n90, "게이트[1603,2671]": bool(count_ok),
              "도메인": {k: len(i) for k, (_, i) in dom.items()}, "wire": wire}
print(json.dumps(OUT["배선"], ensure_ascii=False), flush=True)

def norm(s):
    s = str(s or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(r"[^0-9a-z가-힣]+", "", s)
    return s

def train_names(dkey):
    """학습 행(keep_ids) 명부에서만 제목을 뽑는다(823 검증 — 유보 경유 차단)."""
    r = json.loads((AXD / f"{AX[dkey]}.json").read_text())
    keep = set(dom[dkey][1])
    return {rid: norm(v.get("name") or v.get("title") or "")
            for rid, v in r.items() if rid in keep}

def pair_measure(d1, d2, excl=frozenset(), seed=0):
    C1, ids1 = dom[d1]; C2, ids2 = dom[d2]
    A1 = C1[[i for i, r in enumerate(ids1) if r not in excl]]
    A2 = C2[[i for i, r in enumerate(ids2) if r not in excl]]
    if len(A1) < 60 or len(A2) < 60:          # MINROW 통일(823 검증)
        return None
    r = CS.pair_rmse(CS.mean_curve(A1), CS.mean_curve(A2), "both")
    f1 = CS.floor_of(A1, "both", seed=seed); f2 = CS.floor_of(A2, "both", seed=seed + 1)
    pf = CS.pair_floor(f1, f2)                 # RSS — 814 관례
    p95 = CS.joint_null(A1, A2, "both", seed=seed + 2)
    return {"n": [int(len(A1)), int(len(A2))], "rmse": round(r, 4),
            "쌍바닥(RSS)": round(pf, 4), "배수": round(r / pf, 2),
            "널p95": round(p95, 4), "판정": CS.verdict(r, pf, p95)}

# ── A 단계 1: v2-90일 재현 ───────────────────────────────────────
PAIRS = [("게임", "모바일"), ("모바일", "세계애니"), ("게임", "세계애니")]
V814 = {"게임-모바일": "같다", "모바일-세계애니": "같다", "게임-세계애니": "모른다"}
A1r = {}
for d1, d2 in PAIRS:
    A1r[f"{d1}-{d2}"] = pair_measure(d1, d2)
OUT["A 단계1(재현)"] = A1r
gm = A1r.get("게임-모바일")
flip = any(A1r[k] and {A1r[k]["판정"], V814[k]} == {"같다", "다르다"} for k in V814)
gate = bool(count_ok and gm and gm["판정"] == "같다" and not flip)
OUT["A 게이트"] = {"곡선수": bool(count_ok), "게임-모바일 같다": bool(gm and gm["판정"] == "같다"),
                  "같다↔다르다 반전 없음": not flip, "통과": gate}
print(json.dumps({k: OUT[k] for k in ("A 단계1(재현)", "A 게이트")}, ensure_ascii=False, indent=1), flush=True)

if not gate:
    OUT["A 판정"] = "A1 — 814 는 정의 민감 인공물로 기록 · 정의는 안 만진다"
else:
    n1, n2 = train_names("게임"), train_names("모바일")
    common = (set(n1.values()) & set(n2.values())) - {""}
    ids = {r for r, nm in n1.items() if nm in common} | {r for r, nm in n2.items() if nm in common}
    OUT["A 겹침(학습만)"] = {"제목": len(common), "레코드": len(ids)}
    gm2 = pair_measure("게임", "모바일", excl=frozenset(ids), seed=7)
    OUT["A 단계2(제외)"] = gm2
    if gm2 is None:
        OUT["A 판정"] = "A1 — 제외 후 MINROW 60 미달"
    elif gm2["판정"] == "같다":
        OUT["A 판정"] = f"A3 복권 — 제외 후에도 같다({gm2['배수']}×)"
    else:
        OUT["A 판정"] = f"A2 동어반복 — 제외 후 {gm2['판정']}({gm2['배수']}×) · 814 게임-모바일 철회"
print(json.dumps({k: v for k, v in OUT.items() if k.startswith("A ")}, ensure_ascii=False, indent=1), flush=True)

# ── B: 형태 특징 자 ──────────────────────────────────────────────
SHAPES = ("감쇠", "이중피크", "지연상승", "계단")
game_floor = float(np.mean(CS.floor_of(dom["게임"][0], "both", seed=3)))
grid = (0.15, 0.3, 0.5, 0.8, 1.2, 1.8, 2.7)
cand = []
for nz in grid:
    f = float(np.mean(CS.floor_of(CS.synth("감쇠", noise=nz, seed=111), "both", seed=4)))
    cand.append((abs(f - game_floor), nz, f))
_, NOISE, syn_floor = min(cand)
edge = NOISE in (grid[0], grid[-1])
scale_ok = abs(syn_floor - game_floor) <= 0.5 * game_floor
OUT["B 눈금"] = {"게임 바닥(90d)": round(game_floor, 4), "채택 noise": NOISE,
                "합성 감쇠 바닥": round(syn_floor, 4), "격자 끝": bool(edge),
                "게이트(±50%)": bool(scale_ok)}
print(json.dumps(OUT["B 눈금"], ensure_ascii=False), flush=True)

if not scale_ok:
    OUT["B 판정"] = "B0 눈금 실패(모) — 요동 생성기로도 실측 바닥에 못 닿음"
else:
    # 형태별 독립 씨앗: 원본 100+i · 재생성 200+10i+k (k=0..5)
    gens = {}
    for i, s in enumerate(SHAPES):
        gens[s] = [CS.synth(s, noise=NOISE, seed=100 + i)] + \
                  [CS.synth(s, noise=NOISE, seed=200 + 10 * i + k) for k in range(6)]
    feats = {s: [CS.shape_features(CS.mean_curve(C)) for C in gens[s]] for s in SHAPES}
    allf = np.vstack([f for s in SHAPES for f in feats[s]])
    scale = np.std(allf, axis=0, ddof=1)
    same = [CS.feat_dist(a, b, scale)
            for s in SHAPES for a, b in combinations(feats[s], 2)]
    p95 = float(np.percentile(same, 95))
    diff = {}
    for s1, s2 in combinations(SHAPES, 2):
        ds = [CS.feat_dist(a, b, scale) for a in feats[s1] for b in feats[s2]]
        diff[f"{s1}-{s2}"] = round(float(np.mean(ds)), 3)
    OUT["B 분포"] = {"같은형태 p95": round(p95, 3), "같은형태 중앙": round(float(np.median(same)), 3),
                    "다른형태 평균 거리": diff}
    key = diff["감쇠-이중피크"]
    if p95 >= min(diff.values()):
        OUT["B 판정"] = f"B1 자 무효 — 같은형태 p95 {round(p95,3)} ≥ 다른형태 최솟값 {min(diff.values())}"
    elif key > p95:
        OUT["B 판정"] = f"B2 자 개선 — 감쇠-이중피크 {key} > p95 {round(p95,3)}"
    else:
        OUT["B 판정"] = f"B3 자 한계 — 감쇠-이중피크 {key} ≤ p95 {round(p95,3)}"
    # RMSE 대조(같은 눈금)
    rm = {}
    for s1, s2 in combinations(SHAPES, 2):
        C1, C2 = gens[s1][0], gens[s2][0]
        pf = CS.pair_floor(CS.floor_of(C1, "both", seed=5), CS.floor_of(C2, "both", seed=6))
        r = CS.pair_rmse(CS.mean_curve(C1), CS.mean_curve(C2), "both")
        rm[f"{s1}-{s2}"] = {"배수": round(r / pf, 2), "판정": CS.verdict(r, pf)}
    OUT["B RMSE 대조"] = rm
    # 실측 3쌍 병기
    realf = {}
    for d1, d2 in PAIRS:
        f1 = CS.shape_features(CS.mean_curve(dom[d1][0]))
        f2 = CS.shape_features(CS.mean_curve(dom[d2][0]))
        realf[f"{d1}-{d2}"] = round(CS.feat_dist(f1, f2, scale), 3)
    OUT["B 실측 3쌍(병기)"] = realf

OUT["초"] = round(time.time() - t0, 1)
print(json.dumps({k: v for k, v in OUT.items() if k.startswith("B") or k == "초"}, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out824.json", "w"), ensure_ascii=False, indent=1, default=str)
print("완료", flush=True)
