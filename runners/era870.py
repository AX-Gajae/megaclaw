# -*- coding: utf-8 -*-
# 노트 870 — era870: 영화를 빼면 0.2969 가 돌아오는가(사전등록 '870' · 티처 #35 제안 1)
# 런타임 몽키패치로 833 세계(kobis 합류 전)를 재구성 — 파일 무변경. era manifest 동결.
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
TARGET, FP852 = 0.2969, "adb00d2827b0"


def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    return float(spearmanr(p[ok], yy[ok])[0])


def manifest(data):
    """학습측 재료 지문(규약 첫 적용): 도메인별 행수 + 라벨 해시. dom[d] = (A, M, y, t)."""
    out = {}
    for dom in sorted(data.dom):
        yv = np.asarray(data.dom[dom][2], float)
        out[dom] = {"행": int(len(yv)),
                    "라벨 해시": hashlib.sha256(np.round(yv, 6).tobytes()).hexdigest()[:12]}
    return out


def main():
    t0 = time.time()
    import ff753 as FF
    from lab import pairs as PR, guards as G
    from lab import pairboot as PB
    from lab.forms import REGISTRY
    import state.tri_domain as TD
    import state.audit as SA

    data_now = FF.shell(FF.base())
    man_now = manifest(data_now)
    print(f"현 세계 도메인 {len(man_now)} ({time.time()-t0:.0f}s)", flush=True)

    # ── 833 세계 재구성: '영화' 제거 패치(파일 무변경) ──────────────
    # 1차 시도(out870_era_wfail1.json)는 TD.load_all/SA.domains 만 갈아 끼워 실패 —
    # harness.py:31 이 `from state.audit import domains` 로 **지역 바인딩**을 잡는다.
    import lab.harness as H
    _orig_h = H.domains

    def _strip(r):
        if isinstance(r, tuple):
            return tuple({kk: vv for kk, vv in part.items() if kk != "영화"}
                         if isinstance(part, dict) else part for part in r)
        return {kk: vv for kk, vv in r.items() if kk != "영화"}

    H.domains = lambda *a, **k: _strip(_orig_h(*a, **k))
    _orig_td = TD.load_all
    TD.load_all = lambda *a, **k: _strip(_orig_td(*a, **k))          # 방어적 이중
    if hasattr(SA, "domains"):
        _orig_sa = SA.domains
        SA.domains = lambda *a, **k: _strip(_orig_sa(*a, **k))
    data_833 = FF.shell(FF.base())
    man_833 = manifest(data_833)
    print(f"재구성 도메인 {len(man_833)} ({time.time()-t0:.0f}s)", flush=True)

    src = PR.SRC_DOM["KR 만화"]
    names = list(data_833.names.get(src) or [])
    recs = PR.build("KR 만화")
    A, M, y, t = PR.to_arrays(recs, names)
    fin = np.isfinite(y)
    years = np.array([int(str((r.get("start_date") or "0000"))[:4] or 0) for r in recs.values()])
    ev = np.flatnonzero(fin & (years >= 2025))
    fp = hashlib.sha256(np.round(y[ev], 6).tobytes()).hexdigest()[:12]

    w_fail = []
    if "영화" in man_833:
        w_fail.append("재구성에 영화 잔존")
    if len(ev) != 322:
        w_fail.append(f"평가 {len(ev)} ≠ 322")
    if fp != FP852:
        w_fail.append(f"지문 {fp} ≠ {FP852}")
    if w_fail:
        out = {"갈래": "W 발동 — 재구성 불능: " + " · ".join(w_fail),
               "manifest 현": man_now, "manifest 재구성": man_833, "초": round(time.time() - t0, 1)}
        json.dump(out, open(ROOT / "runners/out870_era.json", "x"), ensure_ascii=False, indent=1)
        print(json.dumps(out["갈래"], ensure_ascii=False), flush=True)
        return

    CLS = REGISTRY["F18_bagboost"]["cls"]
    preds = []
    for s in (4, 5, 6, 7):
        f = G._fit_on(lambda s=s: CLS(seed=s), data_833, 2025.0, seed=s)
        p = np.asarray(f.predict(src, A[ev], M[ev], np.asarray(t, float)[ev]), float)
        preds.append(p)
        print(f"  적합 {s}: ρ {rho(p, y[ev]):.4f} ({time.time()-t0:.0f}s)", flush=True)
    E1r = rho(PB.rank_ensemble(preds), y[ev])
    dlt = abs(E1r - TARGET)
    branch = (f"R 확정 — E1재구성 {E1r:.4f} · |Δ| {dlt:.4f} ≤ 0.005: '재료의 시대' 확정 — 미결 14 최종 도장"
              if dlt <= 0.005 else
              f"R 잔여 — E1재구성 {E1r:.4f} · |Δ| {dlt:.4f} > 0.005: 잔여 요인 실물 — 물음 재개(확정 주장 금지)")

    out = {"E1재구성(rank4~7·영화 제외)": round(E1r, 4), "표적": TARGET, "|Δ|": round(dlt, 4),
           "씨앗별 ρ(재구성)": [round(rho(p, y[ev]), 4) for p in preds],
           "갈래": branch,
           "era manifest": {"현 세계(837 이후)": man_now, "재구성(833 세계)": man_833},
           "짝 지문": {"평가": int(len(ev)), "라벨": fp}, "초": round(time.time() - t0, 1)}
    with open(ROOT / "runners/out870_era.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "era manifest"}, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
