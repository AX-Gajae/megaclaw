# -*- coding: utf-8 -*-
# 노트 861 — 엔티티 자 v2 (사전등록 '861' · 재적합 없음 · 자 위생 아크 마감)
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from lab import pairboot as PB  # noqa: E402
from lab.decay import AXD, AX  # noqa: E402
from ingest.idol_axes import norm_agency  # noqa: E402

t0 = time.time()
ROOT = Path("/Users/ax/world_model")
V2 = json.load(open(ROOT / "data/lab/idol_agency_alias_v2.json"))
ALIAS2 = V2["별칭(정규형 통일)"]

R = json.load(open(ROOT / "runners/out859_rows.json"))
rows = R["행"]
yv = np.array([r["y"] for r in rows])
ens = np.array([r["champ_ens"] for r in rows])
tb = np.array([r["tabpfn_ens"] for r in rows])


def rho2(p, y):
    ok = np.isfinite(p) & np.isfinite(y)
    return float(spearmanr(p[ok], y[ok])[0])


def stat(idx):
    return rho2(tb[idx], yv[idx]) - rho2(ens[idx], yv[idx])


def norm_ent(s):
    return re.sub(r"[^0-9a-z가-힣]+", "", str(s or "").casefold())


def agency_key_v2(raw):
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    if s in ALIAS2:
        return ALIAS2[s]
    seg = re.split(r"\s*[\(（]", s)[0].strip()
    if seg in ALIAS2:
        return ALIAS2[seg]
    n = norm_agency(seg)
    return ALIAS2.get(n, n)


def clusters_from(keys):
    groups, solo = {}, 0
    for i, k in enumerate(keys):
        if k is None or k == "":
            groups[f"_s{solo}"] = [i]
            solo += 1
        else:
            groups.setdefault(k, []).append(i)
    return [np.array(v) for v in groups.values()], groups


# ── ① 엔티티 군집(그룹 매처 — 행 병합 금지) ─────────────────────
ent_keys = [norm_ent(r["group"]) or None for r in rows]
cl_e, g_e = clusters_from(ent_keys)
n_e = len(cl_e)
multi_e = {k: len(v) for k, v in g_e.items() if len(v) > 1 and not k.startswith("_s")}
print(f"엔티티 군집 {n_e}/51 · 다건 {multi_e}", flush=True)

# ── ② 소속사 v2 군집(SM 수리) ────────────────────────────────────
ag_keys = [agency_key_v2(r["agency"]) for r in rows]
cl_a, g_a = clusters_from(ag_keys)
n_a = len(cl_a)
multi_a = {k: len(v) for k, v in g_a.items() if len(v) > 1 and not k.startswith("_s")}
print(f"소속사 v2 군집 {n_a}/51 · 다건 {multi_a}", flush=True)


def boot(cl, seed=827, B=10000):
    th, lo, hi, kind = PB.cluster_boot(stat, cl, seed=seed)
    rg = np.random.default_rng(seed)
    vals = []
    for _ in range(B):
        pick = rg.integers(0, len(cl), len(cl))
        idx = np.concatenate([cl[j] for j in pick])
        if len(np.unique(yv[idx])) < 5:
            continue
        vals.append(stat(idx))
    v = np.array(vals)
    plo, phi = float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))
    se_end = float(np.std(v, ddof=1)) * 2.67 / np.sqrt(len(v))     # 2.5% 분위 상수 정정(티처 #26)
    return {"BCa": [round(lo, 4), round(hi, 4)], "종류": kind,
            "percentile": [round(plo, 4), round(phi, 4)], "끝점 SE(2.67)": round(se_end, 4),
            "폭(BCa)": round(hi - lo, 4)}


b_e = boot(cl_e)
b_a = boot(cl_a)
print(f"엔티티: BCa {b_e['BCa']} · perc {b_e['percentile']}", flush=True)
print(f"소속사 v2: BCa {b_a['BCa']} · perc {b_a['percentile']}", flush=True)

# ── ③ 12도메인 유보 엔티티 중복률 표 ─────────────────────────────
from lab import sideaudit  # noqa: E402

data = sideaudit.champion_data()
dup = {}
for dkey in AX:
    try:
        r = json.loads((AXD / f"{AX[dkey]}.json").read_text())
    except Exception:
        continue
    items = list(r.values())
    yrs = []
    for v in items:
        dt_ = str(v.get("release_date") or v.get("start_date") or "")[:4]
        yrs.append(int(dt_) if dt_.isdigit() else 0)
    hold = [v for v, yy in zip(items, yrs) if yy >= 2025]
    if len(hold) < 20:
        continue
    keys = [PB.franchise_key(v.get("name") or v.get("title") or "") for v in hold]
    n_rows = len(hold)
    n_keys = len(set(keys))
    dup[dkey] = {"유보 행": n_rows, "고유 엔티티": n_keys,
                 "중복률": round(1 - n_keys / n_rows, 3)}
dup["아이돌(그룹 매처)"] = {"유보 행": 51, "고유 엔티티": n_e, "중복률": round(1 - n_e / 51, 3)}
print("중복률 표:", json.dumps(dup, ensure_ascii=False), flush=True)
over = {k: v for k, v in dup.items() if v["중복률"] > 0.10}

# ── ④ seal2 수리(침묵 except → 명시 스킵 · erratum 배제) ─────────
src = open(ROOT / "runners/seal2.py").read()
old = '''    out = set()
    for p in SEALDIR.glob("seal_*.json"):
        try:
            for m in json.loads(p.read_text())["작품"]:
                out.add(m["code"])
        except Exception:
            pass
    return out'''
new = '''    out = set()
    for p in sorted(SEALDIR.glob("seal_*.json")):
        if "erratum" in p.name or "annex" in p.name:
            continue
        doc = json.loads(p.read_text())          # 손상은 침묵하지 않고 즉사(860 위생)
        if "작품" not in doc:
            raise SystemExit(f"⛔ 봉인 파일에 '작품' 없음: {p.name}")
        for m in doc["작품"]:
            out.add(m["code"])
    return out'''
if old in src:
    open(ROOT / "runners/seal2.py", "w").write(src.replace(old, new))
    seal2_fixed = True
else:
    seal2_fixed = False
print(f"seal2 수리 {seal2_fixed}", flush=True)

# ── 갈래 ─────────────────────────────────────────────────────────
branches = []
if b_e["BCa"][0] <= 0:
    branches.append(f"a.강등 확정 — 엔티티 자({n_e}/51)로도 0 물음(BCa {b_e['BCa']}) → '자 무관+엔티티 강건' 승급 · 재개 조건 = 실효 엔티티 ≥{n_e*2}")
else:
    branches.append("b.구현 의심 — 접었는데 0 벗어남(원칙 위반) — 절차 재발동")
if over:
    branches.append(f"c.자 개정 사유 — 중복률 >10%: {list(over)} → pairboot 엔티티 군집 기본값 별도 사전등록")
else:
    branches.append("d.자 아크 봉인 — 전 도메인 중복률 ≤10%")

out = {"엔티티 군집": {"수": n_e, "다건": multi_e, "자": b_e},
       "소속사 v2 군집": {"수": n_a, "다건": multi_a, "자": b_a},
       "중복률 표": dup, "초과(>10%)": over or "없음",
       "seal2 수리": bool(seal2_fixed), "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps({k: v for k, v in out.items() if k != "중복률 표"}, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out861_entity.json", "w"), ensure_ascii=False, indent=1)
