"""배선 후보를 순위 기준으로 전수 검정하고 살아남는 것에 구간을 붙인다.

노트 44가 남은 지렛대를 하나로 좁혔다. 알고리즘 조정 셋은 전부 구간이 0을
포함했고, 배선 하나(노트 34의 도서 타깃 폭)만 $+$0.0939 [$+$0.046, $+$0.199]로
살아남았다. 그러니 배선을 제대로 훑는다.

**노트 38의 탐색과 다르다.** 그때는 목적함수가 인자 공간 자기 상관이었고 그것은
MAE 계열이라 눈금에 반응한다(노트 42). 여기서는 **스무 셀 평균 순위 상관**을
직접 목적으로 쓴다.

**두 단계로 나눈다.** 후보마다 붓스트랩 300회를 돌리면 계산이 감당이 안 된다.

    1단계  모든 후보의 점추정 $\\Delta\\rho$ 를 잰다. 한 후보에 한 번씩.
    2단계  $|\\Delta\\rho| \\ge$ 문턱인 것만 짝지은 붓스트랩으로 구간을 붙인다.

문턱은 0.02로 둔다 --- 노트 44에서 알고리즘 조정 셋의 효과가 0.009--0.022였고
전부 구간이 0을 포함했으므로, 그 아래는 볼 필요가 없다.

**선택 편향을 기록한다.** 후보를 많이 보고 최댓값을 고르므로 점추정은 낙관적이다.
2단계 구간이 그것을 걸러 내는 역할을 하지만, 후보 수와 문턱 통과 수를 함께
적어 얼마나 걸렀는지 남긴다.

사용: python3 -m state.wiring_ci
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .factor_search import CAND, COLS, IX, build
from .rho_ci import mean_rho, paired
from .tri_domain import KO, load_all

OUT = Path("data/state/wiring_ci.json")
THRESH = 0.02
BOOT = 200


def candidates(base):
    """도메인 × 슬롯 × 후보. 현행과 같은 것은 건너뛴다."""
    out = []
    for dom, slots in CAND.items():
        if dom not in base:
            continue
        pool = COLS[dom]()
        for slot, names in slots.items():
            for name in names:
                if name is not None and name not in pool:
                    continue
                out.append((dom, slot, name, pool))
    return out


def run(thresh: float = THRESH, boot: int = BOOT) -> dict:
    base = load_all()
    ref = mean_rho(base)
    print(f"현행 평균 ρ = {ref:+.4f}\n")

    cands = candidates(base)
    print(f"=== 1단계: 후보 {len(cands)}개 점추정 ===")
    rows = []
    for dom, slot, name, pool in cands:
        try:
            d = dict(base)
            d[dom] = build(dom, base, {slot: name}, pool)
            v = mean_rho(d)
        except (np.linalg.LinAlgError, ValueError, KeyError):
            continue
        if not np.isfinite(v):
            continue
        rows.append({"dom": dom, "slot": slot, "name": name, "rho": v,
                     "delta": v - ref})
    rows.sort(key=lambda r: -r["delta"])
    print(f"  {'도메인':<7}{'슬롯':<12}{'후보':<16}{'ρ':>9}{'Δ':>9}")
    for r in rows[:12]:
        print(f"  {r['dom']:<7}{KO[r['slot']]:<12}{str(r['name']):<16}"
              f"{r['rho']:>+9.4f}{r['delta']:>+9.4f}")
    if len(rows) > 12:
        print(f"  ... 나머지 {len(rows)-12}개 (Δ {rows[12]['delta']:+.4f} 이하)")

    top = [r for r in rows if abs(r["delta"]) >= thresh and r["delta"] > 0]
    print(f"\n=== 2단계: Δ≥{thresh} 인 {len(top)}개에 짝지은 붓스트랩 {boot}회 ===")
    print(f"  {'도메인':<7}{'슬롯':<12}{'후보':<16}{'Δ':>9}{'95% 구간':>21}{'P(>0)':>8}")
    conf = []
    for r in rows:
        if r not in top:
            continue
        pool = COLS[r["dom"]]()
        cfgB = {"wiring": (lambda dm=r["dom"], sl=r["slot"], nm=r["name"], pl=pool:
                           (lambda d: {dm: build(dm, d, {sl: nm}, pl)}))()}
        try:
            b = paired(base, {}, cfgB, B=boot)
        except (np.linalg.LinAlgError, ValueError):
            continue
        r["ci"] = b["ci"]; r["p_gt0"] = b["p_gt0"]
        conf.append(r)
        ci = f"[{b['ci'][0]:+.4f}, {b['ci'][1]:+.4f}]"
        mark = "  ←채택 후보" if b["ci"][0] > 0 else ""
        print(f"  {r['dom']:<7}{KO[r['slot']]:<12}{str(r['name']):<16}"
              f"{r['delta']:>+9.4f}{ci:>21}{b['p_gt0']:>8.3f}{mark}")

    win = [r for r in conf if r.get("ci") and r["ci"][0] > 0]
    print(f"\n후보 {len(rows)}개 → 문턱 통과 {len(top)}개 → 구간이 0을 넘는 것 "
          f"{len(win)}개")
    OUT.write_text(json.dumps({"ref": ref, "rows": rows, "n_cand": len(rows),
                               "n_thresh": len(top), "n_win": len(win)},
                              ensure_ascii=False, indent=1))
    return {"rows": rows, "win": win}


if __name__ == "__main__":
    run()
