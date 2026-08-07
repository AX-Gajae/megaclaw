# 노트 849 — 격리 팔과 커버리지×m 표 (사전등록 '849' · 8/12 전)
# 정정 ①②의 두 빈칸을 메운다: 회복/재척도 몫 분해 · 편향(커버리지) 대 분산(m) 재서술.
import json
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

seal = json.load(open(ROOT / "cycle_log/forward/kobis/seal_2026-08-08.json"))
a3 = json.load(open(ROOT / "cycle_log/forward/kobis/annex3_2026-08-08.json"))
films = seal["작품"]
v2rows = {r["code"]: r for r in a3["봉인 30편 v2 보조 팔"]["예측(자루 평균 순위·v2 축)"]}
RECOVERED = set(a3["봉인 30편 v2 보조 팔"]["회복"])

data12 = sideaudit.champion_data()
names = list(data12.names["영화"])
ALL5 = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
jv = names.index("venue_prominence")
je = names.index("entry_friction")
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


# ── ⓐ 격리 팔: v1 축 그대로 + 회복 3편만 v2 값 ───────────────────
# 회복 3편의 v2 venue 값은 cleanwin847 의 v2 사전을 재구성해 얻는다(동결 규칙 그대로).
import html, re  # noqa: E402


def _clean_one(sv):
    sv = re.sub(r"\s+", " ", sv).strip()
    sv = re.split(r"\s+(?:제공|수입사|공동제공|공동 제공|배급|투자)\b", sv)[0].strip()
    sv = re.split(r"\s*(?:제공|배급)\s*$", sv)[0].strip()
    m = re.match(r"([가-힣0-9()주식회사㈜\s]+)", sv)
    cand = m.group(1).strip() if m else ""
    core = re.sub(r"[()㈜\s]|주식회사", "", cand)
    return (cand if len(core) >= 2 else sv).rstrip("( ").strip()[:30]


def segments_v2(raw):
    s = html.unescape(str(raw or ""))
    parts = [p.strip() for p in re.split("[ ]+|[ \t]{2,}", s) if p.strip()]
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


X1 = np.full((len(films), len(names)), 0.5)
M1 = np.zeros((len(films), len(names)))
for j, a in enumerate(names):
    if a in ALL5:
        X1[:, j] = [m["axes"][a] for m in films]
        M1[:, j] = [m["mask"][a] for m in films]
Xi, Mi = X1.copy(), M1.copy()
n_fill = 0
for i, m in enumerate(films):
    if m["제목"] in RECOVERED:
        vp2 = dist_pct_v2(m.get("배급사"))
        assert vp2 is not None, f"회복 재현 실패: {m['제목']}"
        Xi[i, jv] = vp2
        Mi[i, jv] = 1.0
        n_fill += 1
assert n_fill == 3, f"회복 채움 {n_fill} ≠ 3"
tx = np.array([float(m["개봉일"][:4]) for m in films])
p1 = ens(X1, M1, tx)
pi = ens(Xi, Mi, tx)
r1 = np.argsort(np.argsort(-p1)) + 1
ri = np.argsort(np.argsort(-pi)) + 1
# 격리 자기시험: 점수 불변 행들(비회복 27)의 상대 순서 보존?
keep = [i for i in range(len(films)) if films[i]["제목"] not in RECOVERED]
ord1 = [i for i in sorted(keep, key=lambda i: r1[i])]
ordi = [i for i in sorted(keep, key=lambda i: ri[i])]
order_kept = ord1 == ordi
top10_same = [int(i) for i in np.argsort(r1)[:10]] == [int(i) for i in np.argsort(ri)[:10]]
print(f"ⓐ 격리 팔: 회복 3편 채움 · 비회복 27행 상대 순서 보존 {order_kept}", flush=True)

# ── ⓑ 커버리지×m 표 ──────────────────────────────────────────────
COV = (0.433, 0.333, 0.20, 0.0)
MS = (10, 15, 20, 25, 30)
rng = np.random.default_rng(849)
tab = {}
for cv in COV:
    rhos_full, sub = [], {m: [] for m in MS}
    for k in range(30):
        A2, M2 = Ah.copy(), Mh.copy()
        hit = rng.random(len(A2)) < cv
        A2[hit, jv] = 0.5
        M2[hit, jv] = 0.0
        hit2 = rng.random(len(A2)) < 0.167
        A2[hit2, je] = 0.5
        M2[hit2, je] = 0.0
        pm = ens(A2, M2, th)
        okm = np.isfinite(pm) & np.isfinite(yh)
        idx = np.flatnonzero(okm)
        rhos_full.append(float(spearmanr(pm[okm], yh[okm])[0]))
        for m in MS:
            for _ in range(20):
                pick = rng.choice(idx, size=m, replace=False)
                sub[m].append(float(spearmanr(pm[pick], yh[pick])[0]))
    tab[cv] = {"평균(406)": round(float(np.mean(rhos_full)), 4),
               "2σ(m)": {m: round(2 * float(np.nanstd(sub[m], ddof=1)), 4) for m in MS}}
    print(f"  cov {cv}: 평균 {tab[cv]['평균(406)']} · 2σ(m30) {tab[cv]['2σ(m)'][30]} ({time.time()-t0:.0f}s)", flush=True)

gains = {"0.433→0.333": round(tab[0.333]["평균(406)"] - tab[0.433]["평균(406)"], 4),
         "0.333→0": round(tab[0.0]["평균(406)"] - tab[0.333]["평균(406)"], 4),
         "0.433→0": round(tab[0.0]["평균(406)"] - tab[0.433]["평균(406)"], 4)}

annex4 = {
    "작성일": "2026-08-09", "성격": "보조 병기 — 정본·annex1~3 불변 · 라벨 무관",
    "정정 기재": "annex3 '분산 분해 읽기'는 범주 오류였다(대장 849 서문) — 수리는 편향(평균), 누적은 분산(밴드).",
    "격리 팔(v1 척도 + 회복 3편만)": {
        "순위": [{"code": films[i]["code"], "제목": films[i]["제목"],
                  "v1": int(r1[i]), "격리": int(ri[i]), "v2": int(v2rows[films[i]["code"]]["v2 순위"])}
                 for i in range(len(films))],
        "자기시험": {"비회복 27행 상대 순서 보존": bool(order_kept), "상위 10 동일": bool(top10_same)},
        "수확 분해(사전등록)": "ρ_격리−ρ_v1 = 회복의 몫 · ρ_v2−ρ_격리 = 재척도의 몫",
    },
    "커버리지×m 표(마스크30×m20 · 씨앗 849)": {str(k): v for k, v in tab.items()},
    "커버리지 평균 이득": gains,
    "읽기(정정판)": "평균은 커버리지 축에서(계통 편향 — 편수로 안 사라짐), 밴드는 m 축에서(누적으로 좁힘).",
}
ap = ROOT / "cycle_log/forward/kobis/annex4_2026-08-09.json"
with open(ap, "x") as fh:
    json.dump(annex4, fh, ensure_ascii=False, indent=1)

out = {"격리 자기시험": annex4["격리 팔(v1 척도 + 회복 3편만)"]["자기시험"],
       "커버리지 평균": {str(cv): tab[cv]["평균(406)"] for cv in COV},
       "이득": gains, "2σ(m30) by cov": {str(cv): tab[cv]["2σ(m)"][30] for cv in COV},
       "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out849_quota.json", "w"), ensure_ascii=False, indent=1)
