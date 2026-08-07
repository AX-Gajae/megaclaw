"""표본을 얼마나 늘려야 무엇을 볼 수 있나 --- 검정력 지도.

노트 44가 지렛대를 둘로 좁혔고(배선과 데이터), 노트 45의 전수 검정에서 배선이
소진됐다(후보 50개 중 문턱 통과 0개). 남은 것은 데이터뿐이다.

그러면 **얼마나** 늘려야 하는가. 지금 평균 순위 상관의 95\\% 구간 반폭이 0.071인데,
그 값이 표본에 어떻게 의존하는지 알면 무엇을 검정할 수 있는지의 지도가 나온다.

부분추출로 잰다. 각 도메인을 비율 $f$로 줄여 붓스트랩 구간을 구하고, 반폭이
$n^{-1/2}$를 따르는지 확인한 뒤 외삽한다.

**외삽은 조심해서 읽어야 한다.** 부분추출은 현재 표본의 구조를 그대로 축소한
것이라 새 데이터의 다양성을 반영하지 못한다. 여기서 나오는 숫자는 하한이며,
실제로는 더 많이 필요할 수 있다.

사용: python3 -m state.power_map
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .rho_ci import mean_rho, resample
from .tri_domain import load_all

OUT = Path("data/state/power_map.json")
SEED = 20260729
FRACS = (0.2, 0.3, 0.45, 0.6, 0.8, 1.0)


def subsample(base, f, rng):
    """도메인마다 연도 층화 비복원 부분추출."""
    out = {}
    for k, (A, M, y, t) in base.items():
        idx = np.arange(len(y))
        pick = []
        for v in np.unique(t[np.isfinite(t)]):
            g = idx[t == v]
            m = max(1, int(round(len(g) * f)))
            pick += list(rng.choice(g, size=min(m, len(g)), replace=False))
        nan = idx[~np.isfinite(t)]
        if len(nan):
            m = max(1, int(round(len(nan) * f)))
            pick += list(rng.choice(nan, size=min(m, len(nan)), replace=False))
        p = np.array(sorted(pick))
        out[k] = (A[p], M[p], y[p], t[p])
    return out


def halfwidth(doms, B, rng):
    vals = []
    for _ in range(B):
        d = resample(doms, rng)
        try:
            v = mean_rho(d)
        except (np.linalg.LinAlgError, ValueError):
            continue
        if np.isfinite(v):
            vals.append(v)
    if len(vals) < 20:
        return float("nan"), float("nan")
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float((hi - lo) / 2), float(np.mean(vals))


def run(B: int = 200) -> dict:
    base = load_all()
    rng = np.random.default_rng(SEED)
    n0 = sum(len(v[2]) for v in base.values())
    print(f"현재 총 레코드 {n0}건 (도메인 {len(base)}개)\n")
    print(f"  {'비율':<8}{'총 레코드':>10}{'구간 반폭':>11}{'평균 ρ':>10}")
    rows = []
    for f in FRACS:
        d = base if f >= 1.0 else subsample(base, f, rng)
        n = sum(len(v[2]) for v in d.values())
        hw, m = halfwidth(d, B, rng)
        rows.append({"f": f, "n": n, "hw": hw, "rho": m})
        print(f"  {f:<8.2f}{n:>10}{hw:>11.4f}{m:>+10.4f}")

    ok = [r for r in rows if np.isfinite(r["hw"])]
    x = np.log(np.array([r["n"] for r in ok], float))
    y = np.log(np.array([r["hw"] for r in ok]))
    slope, inter = np.polyfit(x, y, 1)
    print(f"\n  적합 기울기 {slope:.3f}   (n^(-1/2)이면 -0.5)")
    # **기울기를 믿지 않는다.** 부분추출 폭이 좁아 추정이 불안정하다. 이론값
    # -0.5 로 고정하고 현재 점을 지나는 선을 쓴다 --- 보수적이다.
    n0_ = rows[-1]["n"]; hw0 = rows[-1]["hw"]

    def need(target):
        return float(n0_ * (hw0 / target) ** 2)

    print(f"\n=== 무엇을 보려면 얼마가 필요한가 (기울기 -0.5 가정) ===")
    print(f"  {'보려는 효과':<22}{'필요 반폭':>10}{'필요 레코드':>12}{'현재 대비':>10}")
    for lab, eff in (("배선 급(노트34, 0.094)", 0.094),
                     ("공통 축 급(0.022)", 0.022),
                     ("이중 배선 급(0.009)", 0.009)):
        hw = eff / 2          # 효과가 구간 밖에 있으려면 반폭이 효과의 절반쯤
        n = need(hw)
        print(f"  {lab:<22}{hw:>10.4f}{int(n):>12,}{n/n0:>9.1f}배")

    out = {"rows": rows, "slope": float(slope), "hw0": rows[-1]["hw"], "n0": n0}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
