# 노트 846 — 수확 자 완결(리허설 2) (사전등록 '846' · 마감 8/12 전)
# 한계: 844 동결 문면·845 annex 원본 불변 — 산출은 전부 annex2(보조 병기).
import html
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

t0 = time.time()
T = 2025.0
SEEDS = list(range(12))
ROOT = Path("/Users/ax/world_model")
F_VP, F_EF, F_TB = 0.433, 0.167, 0.433

data12 = sideaudit.champion_data()
y_f = np.asarray(data12.dom["영화"][2], float)
yr_f = np.asarray(data12.yr["영화"], float)
kho = np.isfinite(yr_f) & (yr_f >= T) & np.isfinite(y_f)
names = list(data12.names["영화"])
J = {k: names.index(k) for k in ("venue_prominence", "entry_friction", "target_breadth")}

cls = REGISTRY["F18_bagboost"]["cls"]
Ah, Mh, yh, th = data12.slice("영화", kho)
fits = []
for s in SEEDS:
    fits.append(G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s))
    print(f"  씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)


def ens(A, M):
    return np.nanmean([np.asarray(f.predict("영화", A, M, th), float) for f in fits], axis=0)


def rho(p, y, sel=None):
    if sel is None:
        sel = np.ones(len(p), bool)
    ok = sel & np.isfinite(p) & np.isfinite(y)
    return float(spearmanr(p[ok], y[ok])[0]) if ok.sum() >= 5 else float("nan")


pe0 = ens(Ah, Mh)
rho_full = rho(pe0, yh)
print(f"기준 ρ {rho_full:.4f}", flush=True)


def masked(rng, cols):
    A2, M2 = Ah.copy(), Mh.copy()
    hits = {}
    for key, frac in cols:
        j = J[key]
        hit = rng.random(len(A2)) < frac
        A2[hit, j] = 0.5
        M2[hit, j] = 0.0
        hits[key] = hit
    return A2, M2, hits


# ── ⓐ 합성 밴드: 마스크 100뽑기 × m=30 비복원 20뽑기 ─────────────
rng = np.random.default_rng(846)
comp = []
tie_rates = []
split_drop = []
for k in range(100):
    A2, M2, hits = masked(rng, (("venue_prominence", F_VP), ("entry_friction", F_EF)))
    pm = ens(A2, M2)
    okm = np.isfinite(pm) & np.isfinite(yh)
    idx = np.flatnonzero(okm)
    for _ in range(20):
        pick = rng.choice(idx, size=30, replace=False)
        comp.append(spearmanr(pm[pick], yh[pick])[0])
    # ⓑ 분리 ρ(동시 마스크의 마스크 행/비마스크 행) · ⓒ 동점률 — 같은 뽑기 재사용
    vmask = hits["venue_prominence"]
    split_drop.append((rho(pm, yh, ~vmask), rho(pm, yh, vmask)))
    r = np.round(pm[vmask & okm], 6)
    tie_rates.append(float(1 - len(np.unique(r)) / max(len(r), 1)))
    if (k + 1) % 25 == 0:
        print(f"  합성 {k+1}/100 ({time.time()-t0:.0f}s)", flush=True)
comp = np.array(comp, float)
comp_mean, comp_2sd = float(np.nanmean(comp)), 2 * float(np.nanstd(comp, ddof=1))
unm_rho = float(np.nanmean([a for a, _ in split_drop]))
msk_rho = float(np.nanmean([b for _, b in split_drop]))
tie_rate = float(np.nanmean(tie_rates))
print(f"ⓐ 합성: 평균 {comp_mean:.4f} · 2σ {comp_2sd:.4f} | ⓑ 분리: 비마스크 {unm_rho:.4f} · 마스크 {msk_rho:.4f} | ⓒ 동점률 {tie_rate:.3f}", flush=True)

# ── ⓑ 축 절제(단독 마스크 · 각 6뽑기) ────────────────────────────
abl = {}
for label, cols in (("venue만", (("venue_prominence", F_VP),)),
                    ("entry만", (("entry_friction", F_EF),)),
                    ("tb만(대조)", (("target_breadth", F_TB),))):
    vals = []
    for k in range(6):
        LBL = {"venue만": 0, "entry만": 100, "tb만(대조)": 200}
        r2 = np.random.default_rng(8460 + LBL[label] + k)  # 🔴 hash() 는 프로세스별 랜덤이었다(티처 #13) — 고정 정수로 수리
        A2, M2, _ = masked(r2, cols)
        vals.append(rho(ens(A2, M2), yh))
    abl[label] = {"ρ": round(float(np.mean(vals)), 4), "Δ": round(float(np.mean(vals)) - rho_full, 4),
                  "SD": round(float(np.std(vals, ddof=1)), 4)}
    print(f"  절제 {label}: {abl[label]}", flush=True)
both_delta = comp_mean_full = None
# 동시 마스크 전체(406행) ρ — 합성 루프의 마스크 뽑기에서 이미 pm 을 냈지만 전체 ρ 로 다시 6뽑기
vals = []
for k in range(6):
    r2 = np.random.default_rng(8469 + k)
    A2, M2, _ = masked(r2, (("venue_prominence", F_VP), ("entry_friction", F_EF)))
    vals.append(rho(ens(A2, M2), yh))
both = {"ρ": round(float(np.mean(vals)), 4), "Δ": round(float(np.mean(vals)) - rho_full, 4)}
print(f"  동시(재현): {both}", flush=True)

# ── ⓓ 결측 부검(봉인 13편) ───────────────────────────────────────
def clean_dist(sv):
    sv = html.unescape(str(sv or ""))
    sv = re.sub(r"\s+", " ", sv).strip()
    sv = re.split(r"\s+(?:제공|수입사|공동제공|공동 제공|배급|투자)\b", sv)[0].strip()
    sv = re.split(r"\s*(?:제공|배급)\s*$", sv)[0].strip()
    m = re.match(r"([가-힣0-9()주식회사㈜\s]+)", sv)
    cand = m.group(1).strip() if m else ""
    core = re.sub(r"[()㈜\s]|주식회사", "", cand)
    return (cand if len(core) >= 2 else sv).rstrip("( ").strip()[:30]


raw = [json.loads(l) for l in open(ROOT / "data/ingest/kobis/axes_raw_897.jsonl")]
dic = set()
for r in raw:
    if "⛔" not in r and r.get("code") and r["개봉일"] < "2025-01-01" and r.get("배급사"):
        dic.add(clean_dist(r["배급사"]))
seal = json.load(open(ROOT / "cycle_log/forward/kobis/seal_2026-08-08.json"))
autopsy = []
for m in seal["작품"]:
    if m["mask"]["venue_prominence"] != 0:
        continue
    rawname = m.get("배급사")
    if not rawname:
        autopsy.append({"제목": m["제목"], "원문": None, "판": "상세 자체에 배급 없음"})
        continue
    key = clean_dist(rawname)
    toks = [t for t in re.split(r"\s{2,}|&nbsp;| {1,}", html.unescape(rawname)) if len(t) >= 3]
    partial = [dv for dv in dic for t in toks if t[:6] and t[:6] in dv]
    verdict = ("파싱/연결 미스(부분 일치 존재)" if partial else "사전 밖(신규/소형)")
    autopsy.append({"제목": m["제목"], "정규화 키": key, "판": verdict,
                    "부분 일치": sorted(set(partial))[:2]})
bug_n = sum(1 for a in autopsy if "미스" in a["판"])
print(f"ⓓ 부검: 13편 중 매처 버그류 {bug_n} · 사전 밖 {sum(1 for a in autopsy if '사전 밖' in a['판'])} · 원문 없음 {sum(1 for a in autopsy if a.get('원문', 1) is None)}", flush=True)

# ── ⓔ m-표 등화 + annex2 동결 ────────────────────────────────────
a1 = json.load(open(ROOT / "cycle_log/forward/kobis/annex_2026-08-08.json"))
band = {int(k): v for k, v in a1["m-적응 밴드 2σ(부트 B=2000)"].items()}
iso = {}
cur = 1e9
for m in sorted(band):
    cur = min(cur, band[m])
    iso[m] = round(cur, 4)

branches = []
if abl["venue만"]["Δ"] <= 0.8 * both["Δ"] and abs(unm_rho - rho_full) < 0.02:
    branches.append("1.한 축 확정(venue 단독이 전체의 ≥80% · 비마스크 유지)")
else:
    branches.append("2.정정 — '한 축' 서술을 '마스크 취약/동점 압축 포함'으로")
if comp_2sd >= 0.35:
    branches.append("3.봉인 1호 단독 재판정 불능 — '총붕괴 아님/보류'만 · 합산(≥60편) 전용")
if bug_n >= 3:
    branches.append("4.별칭 정규화 v2 를 봉인 2호 전 T4 미결로 격상")

annex2 = {
    "작성일": "2026-08-08", "성격": "보조 병기(리허설 2) — 동결 문면·annex 원본 불변",
    "합성 밴드(마스크100×m30뽑기20)": {"평균": round(comp_mean, 4), "2σ": round(comp_2sd, 4)},
    "축 절제": {**abl, "동시(재현)": both,
                "분리 ρ(동시 마스크)": {"비마스크 행": round(unm_rho, 4), "마스크 행": round(msk_rho, 4)},
                "마스크 행 동점률": round(tie_rate, 3)},
    "결측 부검(봉인 13편)": autopsy,
    "m-표 등화(단조 강제 · 합산 σ 조회는 이것)": iso,
    "갈래 판정": branches,
}
ap = ROOT / "cycle_log/forward/kobis/annex2_2026-08-08.json"
with open(ap, "x") as fh:
    json.dump(annex2, fh, ensure_ascii=False, indent=1)

out = {"ⓐ 합성": annex2["합성 밴드(마스크100×m30뽑기20)"],
       "ⓑ 절제": annex2["축 절제"], "ⓓ 버그류": bug_n,
       "갈래": branches, "기준 ρ": round(rho_full, 4), "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out846_ruler.json", "w"), ensure_ascii=False, indent=1)
