# -*- coding: utf-8 -*-
# 노트 862 — 엔티티 자 v3: 정오의 재도출 (사전등록 '862' · 답 공개 상태 · 861 재작성 금지)
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

t0 = time.time()
ROOT = Path("/Users/ax/world_model")
V3 = json.load(open(ROOT / "data/lab/idol_group_alias_v3.json"))
ROMA = V3["그룹 로마자 별칭"]

R = json.load(open(ROOT / "runners/out859_rows.json"))
rows = R["행"]
yv = np.array([r["y"] for r in rows])
ens = np.array([r["champ_ens"] for r in rows])
tb = np.array([r["tabpfn_ens"] for r in rows])


def norm_flat(s):
    return re.sub(r"[^0-9a-z가-힣]+", "", str(s or "").casefold())


def ent_key_v3(g):
    """v3 매처(동결): ①괄호 안 한글 우선 ②전체 정규형 ③로마자 별칭."""
    s = str(g or "").strip()
    if not s:
        return None
    m = re.search(r"[\(（]([^)）]*[가-힣][^)）]*)[\)）]", s)
    if m:
        return norm_flat(m.group(1))
    n = norm_flat(s)
    return ROMA.get(n, n)


keys = [ent_key_v3(r["group"]) for r in rows]
groups = {}
solo = 0
for i, k in enumerate(keys):
    if not k:
        groups[f"_s{solo}"] = [i]
        solo += 1
    else:
        groups.setdefault(k, []).append(i)
cl = [np.array(v) for v in groups.values()]
n_cl = len(cl)
multi = {k: len(v) for k, v in groups.items() if len(v) > 1}
# 복제 검증 병기(병합 근거 아님 — y 동일성 확인용)
same_y = sum(1 for k, v in groups.items() if len(v) > 1 and len({round(yv[i], 6) for i in v}) == 1)
print(f"v3 군집 {n_cl}/51 · 다건 {len(multi)}({multi}) · y 완전동일 다건 {same_y}", flush=True)


def rho2(p, y):
    ok = np.isfinite(p) & np.isfinite(y)
    return float(spearmanr(p[ok], y[ok])[0])


def stat(idx):
    return rho2(tb[idx], yv[idx]) - rho2(ens[idx], yv[idx])


th, lo, hi, kind = PB.cluster_boot(stat, cl, seed=827)
rg = np.random.default_rng(827)
vals = []
for _ in range(10000):
    pick = rg.integers(0, n_cl, n_cl)
    idx = np.concatenate([cl[j] for j in pick])
    if len(np.unique(yv[idx])) < 5:
        continue
    vals.append(stat(idx))
v = np.array(vals)
plo, phi = float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))
se_end = float(np.std(v, ddof=1)) * 2.67 / np.sqrt(len(v))
print(f"v3 BCa [{lo:+.4f},{hi:+.4f}]({kind}) · perc [{plo:+.4f},{phi:+.4f}] · 끝점SE {se_end:.4f}", flush=True)
match_teacher = abs(lo - (-0.0156)) <= 0.005 and abs(hi - 0.4002) <= 0.005

# ── 중복률 표 정정판(침묵 탈락 금지 · 아이돌 = v3) ────────────────
dup = {}
fails = {}
for dkey in AX:
    try:
        r = json.loads((AXD / f"{AX[dkey]}.json").read_text())
    except Exception as e:
        fails[dkey] = f"파일 열기 실패: {str(e)[:50]}"
        continue
    items = list(r.values())
    hold = []
    for v_ in items:
        dt_ = None
        for f_ in ("release_date", "start_date", "debut_date", "open_date", "date"):
            x = str(v_.get(f_) or "")[:4]
            if x.isdigit():
                dt_ = int(x)
                break
        if dt_ and dt_ >= 2025:
            hold.append(v_)
    if len(hold) < 20:
        fails[dkey] = f"유보 {len(hold)}행(<20) — 미측정"
        continue
    kk = [PB.franchise_key(v_.get("name") or v_.get("title") or "") for v_ in hold]
    dup[dkey] = {"유보 행": len(hold), "고유 엔티티": len(set(kk)),
                 "중복률": round(1 - len(set(kk)) / len(hold), 3)}
dup["아이돌(v3)"] = {"유보 행": 51, "고유 엔티티": n_cl, "중복률": round(1 - n_cl / 51, 3)}
over = {k: v for k, v in dup.items() if v["중복률"] > 0.10}
print("중복률 정정판:", json.dumps(dup, ensure_ascii=False), flush=True)
print("미측정/실패:", json.dumps(fails, ensure_ascii=False), flush=True)

branches = []
if n_cl in (35, 36, 37) and match_teacher and lo <= 0:
    branches.append(f"1.정오 완결 — 군집 {n_cl} · 티처 수치 재도출 일치 · 강등 '진짜 엔티티 자 강건' 확정 · 재개 조건 = 실효 엔티티 ≥72")
elif not match_teacher:
    branches.append(f"2.불일치 — BCa [{lo:+.4f},{hi:+.4f}] 대 티처 [−0.0156,+0.4002] — 매처 규칙 차 해부")
if over:
    branches.append(f"3.표 갈래 — >10%: {list(over)}")

out = {"v3 군집": {"수": n_cl, "다건": multi, "y 동일 다건": same_y},
       "v3 자": {"BCa": [round(lo, 4), round(hi, 4)], "종류": kind,
                "percentile": [round(plo, 4), round(phi, 4)], "끝점 SE": round(se_end, 4)},
       "티처 재도출 일치": bool(match_teacher),
       "중복률 정정판": dup, "미측정": fails, "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps({k: v for k, v in out.items() if k not in ("중복률 정정판",)}, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out862_entity_v3.json", "w"), ensure_ascii=False, indent=1)
