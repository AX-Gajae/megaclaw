# 노트 847 — 청정 창 마감 (사전등록 '847' · 마감 8/12 전)
# v2 규칙은 사전(897) 원문만으로 제정 — 봉인 13편은 시험로만(첫 줄 규율).
import html
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

t0 = time.time()
T = 2025.0
SEEDS = list(range(12))
ROOT = Path("/Users/ax/world_model")


# ── v2 정규화(동결) — 세그먼트 분해 · 전 세그먼트 등재 · 첫 세그먼트 조회 ──
def _clean_one(sv):
    """v1 의 한-세그먼트 정리(역할어 절단 · 한글 우선 · 붕괴 방지)를 그대로 쓴다."""
    sv = re.sub(r"\s+", " ", sv).strip()
    sv = re.split(r"\s+(?:제공|수입사|공동제공|공동 제공|배급|투자)\b", sv)[0].strip()
    sv = re.split(r"\s*(?:제공|배급)\s*$", sv)[0].strip()
    m = re.match(r"([가-힣0-9()주식회사㈜\s]+)", sv)
    cand = m.group(1).strip() if m else ""
    core = re.sub(r"[()㈜\s]|주식회사", "", cand)
    return (cand if len(core) >= 2 else sv).rstrip("( ").strip()[:30]


def segments_v2(raw):
    """와이드 갭(nbsp 연속·2+공백)으로 공동배급을 가른다 — html.unescape 로
    nbsp 가 U+00A0 이 되므로 **공백 붕괴 전에** 갈라야 한다(v1 의 병)."""
    s = html.unescape(str(raw or ""))
    parts = [p.strip() for p in re.split(r"[ ]{1,}|\s{2,}", s) if p.strip()]
    # 영문 병기 꼬리(예: 'CJ ENM Corp')는 _clean_one 의 한글 우선이 처리한다
    parts = [re.sub(r"^(?:수입사|제공|공동제공|배급|투자)\s+", "", p) for p in parts]
    segs = [_clean_one(p) for p in parts]
    return [x for x in segs if len(re.sub(r"[()㈜\s]|주식회사|유한회사", "", x)) >= 2]


raw = [json.loads(l) for l in open(ROOT / "data/ingest/kobis/axes_raw_897.jsonl")]
train_v2 = {}
for r in raw:
    if "⛔" not in r and r.get("code") and r["개봉일"] < "2025-01-01" and r.get("배급사"):
        for seg in set(segments_v2(r["배급사"])):
            train_v2[seg] = train_v2.get(seg, 0) + 1
ranked_v2 = sorted(train_v2.values())


def dist_pct_v2(name):
    segs = segments_v2(name) if name else []
    if not segs or segs[0] not in train_v2:
        return None
    return float(np.searchsorted(ranked_v2, train_v2[segs[0]], side="right") / len(ranked_v2))


# ── 봉인 30편에 v2 적용(시험로만) ─────────────────────────────────
seal = json.load(open(ROOT / "cycle_log/forward/kobis/seal_2026-08-08.json"))
films = seal["작품"]
recovered, autopsy = [], []
for m in films:
    was_masked = m["mask"]["venue_prominence"] == 0
    vp2 = dist_pct_v2(m.get("배급사")) if m.get("배급사") else None
    m["_vp2"] = vp2
    if was_masked:
        first = (segments_v2(m.get("배급사")) or [None])[0]
        verdict = ("회복(v2)" if vp2 is not None else
                   ("원문 없음" if not m.get("배급사") else "사전 밖(v2 후에도)"))
        autopsy.append({"제목": m["제목"], "첫 세그먼트": first, "판": verdict})
        if vp2 is not None:
            recovered.append(m["제목"])
cov_v1 = float(np.mean([m["mask"]["venue_prominence"] for m in films]))
cov_v2 = float(np.mean([1.0 if (m["_vp2"] is not None or m["mask"]["venue_prominence"] == 1) else 0.0
                        for m in films]))
print(f"v2: 사전 {len(train_v2)}(v1 103) · 확보 {cov_v1:.3f}→{cov_v2:.3f} · 회복 {recovered}", flush=True)

# ── 적합 12 + v2 재예측(predict 전용) ────────────────────────────
data12 = sideaudit.champion_data()
names = list(data12.names["영화"])
ALL5 = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
J = {k: names.index(k) for k in ALL5 if k in names}
y_f = np.asarray(data12.dom["영화"][2], float)
yr_f = np.asarray(data12.yr["영화"], float)
kho = np.isfinite(yr_f) & (yr_f >= T) & np.isfinite(y_f)
Ah, Mh, yh, th = data12.slice("영화", kho)

cls = REGISTRY["F18_bagboost"]["cls"]
fits = []
for s in SEEDS:
    fits.append(G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s))
    print(f"  씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)


def ens(A, M, t):
    return np.nanmean([np.asarray(f.predict("영화", A, M, t), float) for f in fits], axis=0)


X1 = np.full((len(films), len(names)), 0.5)
M1 = np.zeros((len(films), len(names)))
for j, a in enumerate(names):
    if a in ALL5:
        X1[:, j] = [m["axes"][a] for m in films]
        M1[:, j] = [m["mask"][a] for m in films]
X2, M2 = X1.copy(), M1.copy()
jv = J["venue_prominence"]
for i, m in enumerate(films):
    if m["_vp2"] is not None:
        X2[i, jv] = m["_vp2"]
        M2[i, jv] = 1.0
tx = np.array([float(m["개봉일"][:4]) for m in films])
p1 = ens(X1, M1, tx)
p2 = ens(X2, M2, tx)
r1 = np.argsort(np.argsort(-p1)) + 1
r2 = np.argsort(np.argsort(-p2)) + 1
moved = [{"제목": films[i]["제목"], "v1": int(r1[i]), "v2": int(r2[i])}
         for i in range(len(films)) if r1[i] != r2[i]]
unchanged_axes = [i for i in range(len(films))
                  if not (films[i]["mask"]["venue_prominence"] == 0 and films[i]["_vp2"] is not None)]
moved_same = sum(1 for i in unchanged_axes if r1[i] != r2[i])
print(f"순위 이동 {len(moved)}편 (축 불변 행의 이동 {moved_same} — 회복 행이 밀어낸 재배열)", flush=True)

# ── 합성×m 표(마스크 40뽑기 × m뽑기 25 · 고정 씨앗) + 분산 분해 ──
MS = (10, 15, 20, 25, 30)
rng = np.random.default_rng(847)
per_mask_rhos = []      # 마스크별 전체-406 ρ (between 성분)
comp = {m: [] for m in MS}
for k in range(40):
    A2, Mm = Ah.copy(), Mh.copy()
    for key, frac in (("venue_prominence", 0.433), ("entry_friction", 0.167)):
        j = J[key]
        hit = rng.random(len(A2)) < frac
        A2[hit, j] = 0.5
        Mm[hit, j] = 0.0
    pm = ens(A2, Mm, th)
    okm = np.isfinite(pm) & np.isfinite(yh)
    idx = np.flatnonzero(okm)
    per_mask_rhos.append(float(spearmanr(pm[okm], yh[okm])[0]))
    for m in MS:
        for _ in range(25):
            pick = rng.choice(idx, size=m, replace=False)
            comp[m].append(float(spearmanr(pm[pick], yh[pick])[0]))
    if (k + 1) % 10 == 0:
        print(f"  합성 {k+1}/40 ({time.time()-t0:.0f}s)", flush=True)
table = {m: {"평균": round(float(np.nanmean(comp[m])), 4),
             "2σ": round(2 * float(np.nanstd(comp[m], ddof=1)), 4)} for m in MS}
between = float(np.std(per_mask_rhos, ddof=1))
within30 = float(np.sqrt(max(np.var(comp[30], ddof=1) - between ** 2, 0)))
# 단조 강제(합산 조회용 — m 이 커질수록 2σ 는 줄어야 한다)
iso = {}
cur = 1e9
for m in sorted(MS):
    cur = min(cur, table[m]["2σ"])
    iso[m] = round(cur, 4)
print(f"합성×m: {table} · between σ {between:.4f} · within(m30) σ {within30:.4f}", flush=True)

# ── 갈래 판정 ────────────────────────────────────────────────────
branches = []
if len(recovered) >= 2 and cov_v2 >= 0.60:
    branches.append("1.이중 팔 확정 — annex3 봉인 · 수확 부호 시험(ρ_v2>ρ_v1 예측) 등록")
elif len(recovered) <= 1:
    branches.append("2.v2 무력 — 사전 밖 지배 확정 · 부호 시험 취소")
branches.append("3.합산 자 갱신 — 합성×m 표 동결")

annex3 = {
    "작성일": "2026-08-08", "성격": "보조 병기 — 봉인·annex1/2 정본 불변 · 라벨 무관(predict 전용)",
    "v2 정규화(동결)": {"규칙": "와이드 갭(U+00A0·2+공백) 세그먼트 분해 — 공백 붕괴 전 · 사전은 전 세그먼트 등재 · 조회는 첫 세그먼트 · 의미 병합 별칭 없음",
                       "사전 크기": len(train_v2), "제정 원천": "897 사전 원문만(봉인 13편은 시험로만)"},
    "봉인 30편 v2 보조 팔": {"확보율 v1→v2": [round(cov_v1, 3), round(cov_v2, 3)], "회복": recovered,
                            "예측(자루 평균 순위·v2 축)": [
                                {"code": films[i]["code"], "제목": films[i]["제목"],
                                 "v1 순위": int(r1[i]), "v2 순위": int(r2[i]),
                                 "v2 점수": round(float(p2[i]), 4)} for i in range(len(films))],
                            "수확 부호 시험(사전등록)": "9/28 수확에서 ρ_v2 ≥ ρ_v1 이면 '결측선' 진단 전향 확정(부호만 — 크기 주장 없음)"},
    "결측 부검 정본(재분류)": autopsy,
    "합성×m 표(마스크40×m25 · 씨앗 847)": table,
    "분산 분해": {"between(마스크) σ": round(between, 4), "within(m=30) σ": round(within30, 4),
                  "읽기": "밴드를 좁히는 지렛대 — between 은 커버리지 수리(v2), within 은 봉인 누적"},
    "합산 σ̄ 조회 표(단조 강제 · annex1 규칙의 σᵢ 는 이제 이 표)": iso,
    "갈래 판정": branches,
}
ap = ROOT / "cycle_log/forward/kobis/annex3_2026-08-08.json"
with open(ap, "x") as fh:
    json.dump(annex3, fh, ensure_ascii=False, indent=1)

out = {"v2 확보율": [round(cov_v1, 3), round(cov_v2, 3)], "회복": recovered,
       "순위 이동": len(moved), "합성×m": table,
       "분산 분해": annex3["분산 분해"], "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out847_cleanwin.json", "w"), ensure_ascii=False, indent=1)
