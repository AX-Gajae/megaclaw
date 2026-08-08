# -*- coding: utf-8 -*-
# 노트 859 — 아이돌 군집 열쇠 (사전등록 '859' · 828 '한 왕국 간발'의 완결)
# 0단계: 828 챌린저 팔 재현(Δ 0.1732) → 행별 동결. 1단계: 소속사 군집 부트(BCa · 동결 별칭표 v1).
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G, idolset, pairboot as PB, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

t0 = time.time()
ROOT = Path("/Users/ax/world_model")
ALIAS = json.load(open(ROOT / "data/lab/idol_agency_alias_v1.json"))["별칭"]


def rho(p, y):
    ok = np.isfinite(p) & np.isfinite(y)
    return float(spearmanr(p[ok], y[ok])[0])


data = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]
d = "아이돌"
yr = np.asarray(data.yr[d], float)
y_all = np.asarray(data.dom[d][2], float)
ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y_all)
kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y_all)
A, M, yv, tv = data.slice(d, kho)
Atr, Mtr, ytr, ttr = data.slice(d, ktr)
assert int(kho.sum()) == 51, f"유보 {int(kho.sum())} ≠ 51"

# 행↔레코드 정렬(810 선례): idolset 재빌드로 record 순서 확보 후 데뷔연도 일치 대조
rows_all = idolset._rows(wide_post=True)
hold_rec = [r for r in rows_all if float(str(r.get("debut_date", "0000"))[:4]) >= 2025.0]
assert len(hold_rec) == 51, f"레코드 유보 {len(hold_rec)} ≠ 51"
yrs_rec = np.array([float(str(r["debut_date"])[:4]) for r in hold_rec])
yrs_dat = np.asarray(data.yr[d], float)[kho]
assert np.allclose(np.floor(yrs_dat), yrs_rec), "행↔레코드 연도 대조 실패"
print(f"배선: 유보 51 · 연도 전수 일치 ({time.time()-t0:.0f}s)", flush=True)

# ── 0단계: 828 챌린저 팔 재현 ────────────────────────────────────
print("챔피언 씨앗 1~4 적합...", flush=True)
fits = [G._fit_on(lambda s=s: cls(seed=s), data, 2025.0, seed=s) for s in (1, 2, 3, 4)]
ens = PB.rank_ensemble([np.asarray(f.predict(d, A, M, tv), float) for f in fits])
okr = np.isfinite(ytr)
Xtr = np.nan_to_num(np.hstack([Atr, Mtr, np.asarray(ttr, float)[:, None]]), nan=0.5)[okr]
Xho = np.nan_to_num(np.hstack([A, M, np.asarray(tv, float)[:, None]]), nan=0.5)
from tabpfn import TabPFNRegressor  # noqa: E402
tb_p = []
for s in (4, 5, 6, 7):
    m = TabPFNRegressor(device="cpu", random_state=s)
    m.fit(Xtr, ytr[okr])
    tb_p.append(np.asarray(m.predict(Xho), float))
tb_ens = PB.rank_ensemble(tb_p)
delta_pt = rho(tb_ens, yv) - rho(ens, yv)
repro_ok = abs(delta_pt - 0.1732) <= 0.02
print(f"0단계: Δ 점추정 {delta_pt:+.4f} (828 기록 +0.1732 · 재현 {'성공' if repro_ok else '실패'}) "
      f"({time.time()-t0:.0f}s)", flush=True)

rows_out = [{"record_id": hold_rec[i].get("record_id") or hold_rec[i].get("id") or i,
             "agency": hold_rec[i].get("agency"), "group": hold_rec[i].get("group_name"),
             "y": round(float(yv[i]), 6), "champ_ens": round(float(ens[i]), 4),
             "tabpfn_ens": round(float(tb_ens[i]), 4)} for i in range(51)]
json.dump({"Δ 점추정": round(delta_pt, 4), "재현": bool(repro_ok), "행": rows_out},
          open(ROOT / "runners/out859_rows.json", "w"), ensure_ascii=False, indent=1)

# ── 군집 열쇠(동결 별칭표 v1 + 세그먼트 규칙) ────────────────────
from ingest.idol_axes import norm_agency  # noqa: E402


def agency_key(raw):
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    if s in ALIAS:
        return ALIAS[s]
    seg = re.split(r"\s*[\(（]", s)[0].strip()      # 괄호 앞 첫 법인(동결 규칙)
    if seg in ALIAS:
        return ALIAS[seg]
    n = norm_agency(seg)
    return ALIAS.get(n, n)


keys = [agency_key(r.get("agency")) for r in hold_rec]
n_null = sum(1 for k in keys if k is None)
groups = {}
solo_i = 0
for i, k in enumerate(keys):
    if k is None:
        groups[f"_solo{solo_i}"] = [i]
        solo_i += 1
    else:
        groups.setdefault(k, []).append(i)
cl = [np.array(ix) for ix in groups.values()]
n_cl = len(cl)
n_multi = sum(1 for ix in cl if len(ix) > 1)
print(f"군집: {n_cl}/51 (다건 {n_multi} · null solo {n_null}) — 상한 병기 44~48", flush=True)


def stat(idx):
    return rho(tb_ens[idx], yv[idx]) - rho(ens[idx], yv[idx])


th_c, lo_c, hi_c, kind_c = PB.cluster_boot(stat, cl, seed=827)
cl_solo, _solo_note = PB.solo_clusters(51)
th_s, lo_s, hi_s, kind_s = PB.cluster_boot(stat, cl_solo, seed=827)
w_c, w_s = hi_c - lo_c, hi_s - lo_s
verdict_c = {"승": "TabPFN승", "패": "챔피언승"}.get(PB.verdict(lo_c, hi_c), "판정 불능")

branches = []
if lo_c > 0:
    branches.append(f"a.확정 — 하한 {lo_c:+.4f} > 0 · '한 왕국' 유지(군집 {n_cl}/51 — 교정 상한이 구조적으로 작았음 병기)")
else:
    branches.append(f"b.강등 — 하한 {lo_c:+.4f} ≤ 0 → 판정 불능 · 828 서술 정정")
if w_c > 2 * w_s:
    branches.append("c.폭 확대 실물(>2배) — 티처 #4 구멍 ① 확정")
if w_c < w_s:
    branches.append("d.해로움 — 군집 폭 < 무군집(구현 의심)")

out = {"0단계 재현": {"Δ": round(delta_pt, 4), "828": 0.1732, "성공": bool(repro_ok)},
       "군집": {"수": n_cl, "다건": n_multi, "null(유보)": n_null,
               "다건 명단": {k: len(v) for k, v in groups.items() if len(v) > 1 and not k.startswith("_solo")}},
       "군집 자": {"Δ": round(th_c, 4), "CI95": [round(lo_c, 4), round(hi_c, 4)], "종류": kind_c,
                  "판정": verdict_c, "폭": round(w_c, 4)},
       "무군집 자(병기)": {"Δ": round(th_s, 4), "CI95": [round(lo_s, 4), round(hi_s, 4)],
                          "종류": kind_s, "폭": round(w_s, 4)},
       "828 기록": {"CI": [0.0082, 0.388], "폭": 0.3798},
       "폭 비(군집/무군집)": round(w_c / w_s, 3) if w_s else None,
       "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out859_idolkey.json", "w"), ensure_ascii=False, indent=1)
