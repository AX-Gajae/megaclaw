# -*- coding: utf-8 -*-
# 노트 851(b 반사실 + c annex5) — Δ(n) 완주 후 실행(사전등록 851).
# 반사실: TRAINW 에 KR만화(유보322 몫) 등록 — 판 무관 진단 전용 · 챔피언 승격 금지.
# annex5: v3 필모 실적(재측정)으로 봉인 마스크 5편 채움 — v1 척도 유지(격리형 · 재척도 금지).
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G, pairs as PR, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402
from lab.harness import Data  # noqa: E402

t0 = time.time()
T = 2025.0
SEEDS = list(range(12))
ROOT = Path("/Users/ax/world_model")

# ── 반사실 팔: d0 의 n15 · n160 을 TRAINW 등록으로 재적합 ────────
data12 = sideaudit.champion_data()
src = PR.SRC_DOM["KR 만화"]
names = list(data12.names[src])
recs = PR.build("KR 만화")
A, M, y, t = PR.to_arrays(recs, names)
A = np.asarray(A, float); M = np.asarray(M, float)
y = np.asarray(y, float); t = np.asarray(t, float)
years = np.array([int(str((r.get("start_date") or "0000"))[:4] or 0) for r in recs.values()])
fin = np.isfinite(y)
ev = np.flatnonzero(fin & (years >= 2025))
pool = np.flatnonzero(fin & (years < 2025) & (years > 0))
assert len(ev) == 322

base = REGISTRY["F18_bagboost"]["cls"]


class F18KR(base):  # noqa: N801 — 진단 전용(챔피언 후보 아님)
    TRAINW = {**base.TRAINW, "KR만화": 322}


perm = np.random.default_rng(8480 + 0).permutation(pool)   # d0 와 같은 순열
cf = {}
for n in (15, 160):
    idx = perm[:n]
    y13 = np.full(len(y), np.nan)
    y13[idx] = y[idx]
    dom13 = dict(data12.dom)
    nm13 = dict(data12.names)
    dom13["KR만화"] = (A, M, y13, t)
    nm13["KR만화"] = list(names)
    d13 = Data(dom13, nm13)
    d13.yr = dict(data12.yr)
    d13.yr["KR만화"] = years.astype(float)
    preds = []
    for s in SEEDS:
        f = G._fit_on(lambda s=s: F18KR(seed=s), d13, T, seed=s)
        preds.append(np.asarray(f.predict("KR만화", A[ev], M[ev], t[ev]), float))
    pe = np.nanmean(preds, axis=0)
    ok = np.isfinite(pe) & np.isfinite(y[ev])
    cf[n] = round(float(spearmanr(pe[ok], y[ev][ok])[0]), 4)
    print(f"반사실 n={n}: ρ {cf[n]} ({time.time()-t0:.0f}s)", flush=True)

ck = [json.loads(l) for l in open(ROOT / "runners/out848_checkpoint.jsonl")]
orig = {r["n"]: r["rho_joint"] for r in ck if r["d"] == 0 and r["n"] in (15, 160)}
jump15 = cf[15] - orig.get(15, float("nan"))
jump160 = cf[160] - orig.get(160, float("nan"))
print(f"반사실 점프: n15 {jump15:+.4f} · n160 {jump160:+.4f}", flush=True)

# ── annex5: v3 필모 실적으로 봉인 마스크 5편 채움(v1 척도 유지) ──
import html, re  # noqa: E402

seal = json.load(open(ROOT / "cycle_log/forward/kobis/seal_2026-08-08.json"))
films = seal["작품"]
re851 = json.load(open(ROOT / "runners/out851_refilmo.json"))
counts = {r["봉인 작품"]: r["pre-2025 실적(재)"] for r in re851["회사별(재)"]
          if r.get("판(재)") == "실적 있음"}

# v1 사전(897 · 학습 구간)의 순위 분포 — 백분위 눈금으로 재사용(기저 차이 병기)
raw = [json.loads(l) for l in open(ROOT / "data/ingest/kobis/axes_raw_897.jsonl")]


def clean_dist_v1(sv):
    sv = html.unescape(str(sv or ""))
    sv = re.sub(r"\s+", " ", sv).strip()
    sv = re.split(r"\s+(?:제공|수입사|공동제공|공동 제공|배급|투자)\b", sv)[0].strip()
    sv = re.split(r"\s*(?:제공|배급)\s*$", sv)[0].strip()
    m = re.match(r"([가-힣0-9()주식회사㈜\s]+)", sv)
    cand = m.group(1).strip() if m else ""
    core = re.sub(r"[()㈜\s]|주식회사", "", cand)
    return (cand if len(core) >= 2 else sv).rstrip("( ").strip()[:30]


tc = {}
for r in raw:
    if "⛔" not in r and r.get("code") and r["개봉일"] < "2025-01-01" and r.get("배급사"):
        k = clean_dist_v1(r["배급사"])
        tc[k] = tc.get(k, 0) + 1
ranked = sorted(tc.values())

ALL5 = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
jv = names_f = None
names_f = list(data12.names["영화"])
jv = names_f.index("venue_prominence")
X1 = np.full((len(films), len(names_f)), 0.5)
M1 = np.zeros((len(films), len(names_f)))
for j, a in enumerate(names_f):
    if a in ALL5:
        X1[:, j] = [m["axes"][a] for m in films]
        M1[:, j] = [m["mask"][a] for m in films]
X3, M3 = X1.copy(), M1.copy()
fills = []
for i, m in enumerate(films):
    c = counts.get(m["제목"])
    if c and m["mask"]["venue_prominence"] == 0:
        X3[i, jv] = float(np.searchsorted(ranked, c, side="right") / len(ranked))
        M3[i, jv] = 1.0
        fills.append((m["제목"], c, round(float(X3[i, jv]), 3)))
print(f"v3 채움 {len(fills)}: {fills}", flush=True)

fits = []
for s in SEEDS:
    fits.append(G._fit_on(lambda s=s: base(seed=s), data12, T, seed=s))
    print(f"  annex5 씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)
tx = np.array([float(m["개봉일"][:4]) for m in films])
p3 = np.nanmean([np.asarray(f.predict("영화", X3, M3, tx), float) for f in fits], axis=0)
r3 = np.argsort(np.argsort(-p3)) + 1

annex5 = {
    "작성일": "2026-08-08", "성격": "보조 병기 — 정본·annex1~4 불변 · 라벨 무관(첫 라벨 관측 8/12 전)",
    "v3(필모 실적 · 재측정 기반)": {
        "원천": "회사 필모 전 페이지(etcParam 페이징 — 티처 #16 절단 정정 후) × pre-2025 일별 표 대조",
        "기저 차이 병기": "실적 카운트 기저(전 상영작)가 v1 사전 기저(897 문턱작)와 다르다 — 백분위 눈금만 v1 을 빌린다. 필름다빈·씨엠닉스는 MAXP=20 가드로 하한.",
        "채움(v1 척도 유지 · 재척도 없음 — 849 격리 교훈)": [
            {"제목": t_, "실적": c_, "v3 venue": v_} for t_, c_, v_ in fills],
    },
    "예측 팔(자루 평균 순위)": [
        {"code": films[i]["code"], "제목": films[i]["제목"], "v1 순위": None, "v3 순위": int(r3[i]),
         "v3 점수": round(float(p3[i]), 4)} for i in range(len(films))],
    "수확 사다리 갱신": "ρ_v1(정본) · ρ_격리(+3) · ρ_v3(+5 · 이 팔) · ρ_v2(전면 재척도) — 몫 분해는 사다리 인접 차로. 근접짝 캐스케이드 잡음 병기(850 서문).",
    "반사실 팔 결과(Δ(n) 판별 — 진단 전용)": {"n15": cf[15], "n160": cf[160],
        "원 곡선 d0": orig, "점프": {"n15": round(jump15, 4), "n160": round(jump160, 4)}},
}
ap = ROOT / "cycle_log/forward/kobis/annex5_2026-08-08.json"
with open(ap, "x") as fh:
    json.dump(annex5, fh, ensure_ascii=False, indent=1)
out = {"반사실": annex5["반사실 팔 결과(Δ(n) 판별 — 진단 전용)"], "v3 채움": len(fills),
       "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out851_cf_annex5.json", "w"), ensure_ascii=False, indent=1)
