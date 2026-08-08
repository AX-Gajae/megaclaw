# -*- coding: utf-8 -*-
# 노트 869 — 833 격차의 망원 분해(사전등록 '869' · 티처 #34 제안 1)
# E1−0.2561 = (E1−E2)씨앗 + (E2−E4)순위결합 + (E4−E5)앙상블화 + (E5−0.2561)재료 — 잔차 구조상 0.
# pairgap833.py 의 재료·예측 경로를 문자 그대로(씨앗만 0~11 확장). 원본 불변 — 사본 러너.
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")   # ff753(main 가드 실재 — import 안전)
import ff753 as FF  # noqa: E402
from lab import pairs as PR, guards as G, pairboot as PB  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

ROOT = Path("/Users/ax/world_model")
A852, A833, FP852 = 0.2561, 0.2969, "adb00d2827b0"


def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    return float(spearmanr(p[ok], yy[ok])[0])


def main():
    t0 = time.time()
    data = FF.shell(FF.base())
    CLS = REGISTRY["F18_bagboost"]["cls"]

    src = PR.SRC_DOM["KR 만화"]
    names = list(data.names.get(src) or [])
    recs = PR.build("KR 만화")
    A, M, y, t = PR.to_arrays(recs, names)
    fin = np.isfinite(y)
    years = np.array([int(str((r.get("start_date") or "0000"))[:4] or 0) for r in recs.values()])
    ev = np.flatnonzero(fin & (years >= 2025))
    import hashlib
    fp = hashlib.sha256(np.round(y[ev], 6).tobytes()).hexdigest()[:12]   # 852 와 동일식(unify852.py:32)
    wiring = {"평가": int(len(ev)), "라벨 지문": fp}
    print("배선:", wiring, flush=True)
    if len(ev) != 322 or fp != FP852:
        out = {"갈래": f"W 발동 — 재현 불능(평가 {len(ev)} · 지문 {fp} ≠ {FP852}) — 드리프트/의존물 실물",
               "배선": wiring, "초": round(time.time() - t0, 1)}
        json.dump(out, open(ROOT / "runners/out869_gap.json", "x"), ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
        return

    preds, per_seed = [], []
    for s in range(12):
        f = G._fit_on(lambda s=s: CLS(seed=s), data, 2025.0, seed=s)
        p = np.asarray(f.predict(src, A[ev], M[ev], np.asarray(t, float)[ev]), float)
        preds.append(p)
        per_seed.append(rho(p, y[ev]))
        print(f"  적합 {s}: ρ {per_seed[-1]:.4f} ({time.time()-t0:.0f}s)", flush=True)

    E1 = rho(PB.rank_ensemble(preds[4:8]), y[ev])
    E2 = rho(PB.rank_ensemble(preds), y[ev])
    E4 = rho(np.nanmean(np.vstack(preds), axis=0), y[ev])
    E5 = float(np.mean(per_seed))
    E6 = float(np.mean(per_seed[4:8]))
    shares = {"씨앗 부분집합(E1−E2)": E1 - E2, "순위결합(E2−E4)": E2 - E4,
              "앙상블화(E4−E5)": E4 - E5, "재료(E5−0.2561)": E5 - A852}
    total = E1 - A852
    assert abs(sum(shares.values()) - total) < 1e-9, "사슬 합 불일치 — W(구현 오류)"

    if abs(E1 - A833) > 0.005:
        branch = f"R 실패 — E1 {E1:.4f} 대 0.2969(|Δ| {abs(E1-A833):.4f} > 0.005): 구현 의심 우선·판정 중단·D 안 열음"
    else:
        mx = max(shares, key=lambda k: abs(shares[k]))
        branch = (f"R 성공(E1 {E1:.4f}) → D: 주범 = {mx}({shares[mx]:+.4f} · 총 {total:+.4f} 의 {abs(shares[mx])/abs(total)*100:.0f}%)"
                  if abs(shares[mx]) >= 0.4 * abs(total) else
                  f"R 성공(E1 {E1:.4f}) → D: 복합 — 최대 |몫| {abs(shares[mx]):.4f} < 총 {abs(total):.4f} 의 40%")

    out = {"배선": wiring, "씨앗별 ρ": [round(x, 4) for x in per_seed],
           "E": {"E1(rank4~7)": round(E1, 4), "E2(rank0~11)": round(E2, 4),
                 "E4(mean0~11)": round(E4, 4), "E5(씨앗별 평균)": round(E5, 4), "E6(4~7 평균)": round(E6, 4)},
           "몫": {k: round(v, 4) for k, v in shares.items()}, "총격차": round(total, 4),
           "갈래": branch, "초": round(time.time() - t0, 1)}
    with open(ROOT / "runners/out869_gap.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
