"""순위 안정성 --- 이 순서를 주장해도 되나(노트 314).

노트 310이 leave-one-out 으로 여덟 도메인의 차를 재고 \"개별 도메인은 못
가른다 --- 갈린 것은 **순서**\"라고 적은 뒤 그 순서 위에 결론을 세웠다.
하루 뒤 잡음이 작은 자로 다시 재니 두 순서의 상관이 **-0.048**(p=0.91)
이었다. **못 가르는 값들의 순서도 못 가른다.**

그런데 그것을 그때 알 수 있었다 --- 차와 짝SE 가 다 있었으므로 **짝짝이
순서가 뒤집힐 확률**을 셀 수 있었다. 이 파일이 그 셈이다.

    P(i 가 j 보다 크다) = Phi( (d_i - d_j) / sqrt(se_i^2 + se_j^2) )

**보수적인 근사다.** 차들이 같은 기준선을 나눠 쓰므로 서로 양의 상관이 있고,
그러면 차의 차는 이 식보다 **덜** 흔들린다. 그래서 이 검사가 \"안정\"이라고
하면 진짜 안정이고, \"흔들린다\"고 하면 더 봐야 한다. 부트스트랩 표본을
그대로 갖고 있으면 `pairs_from_draws` 로 정확히 셀 수 있다.

**거부권이 아니라 이름표다**(`hearing` · `overlap` · `marker` 와 같은 규약).
순서를 주장하지 말라고 막는 게 아니라, 주장하기 전에 몇 쌍이 동전 던지기인지
적어 둔다.
"""
from __future__ import annotations

import math

STABLE = 0.90          # 이 확률 이상이면 그 쌍은 섰다고 본다
MIN_PAIRS = 3


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def pair_prob(d_i: float, se_i: float, d_j: float, se_j: float) -> float:
    """P(i 가 j 보다 크다). se 가 0 이면 결정적으로 본다."""
    v = se_i * se_i + se_j * se_j
    if v <= 0:
        return 1.0 if d_i > d_j else (0.0 if d_i < d_j else 0.5)
    return _phi((d_i - d_j) / math.sqrt(v))


def report(items: dict, stable: float = STABLE) -> dict:
    """{이름: (차, 짝SE)} → 순서를 얼마나 믿을 수 있나.

    ``items`` 의 값은 (값, 짝SE) 쌍이다. 값이 클수록 위로 놓는다.
    """
    ks = [k for k, v in items.items() if v is not None and v[1] is not None]
    if len(ks) < 2:
        return {"판정": "못 잰다", "왜": "항목이 둘 미만"}
    order = sorted(ks, key=lambda k: -items[k][0])
    pairs, flip, coin = [], [], []
    for a in range(len(order)):
        for b in range(a + 1, len(order)):
            i, j = order[a], order[b]
            p = pair_prob(items[i][0], items[i][1], items[j][0], items[j][1])
            pairs.append((i, j, p))
            if p < 0.5:
                flip.append((i, j, p))          # 순서가 이미 뒤집혀 있다(있을 수 없음)
            if p < stable:
                coin.append((i, j, p))
    n = len(pairs)
    n_stable = n - len(coin)
    # 이웃 쌍만 따로 --- 순서를 읽을 때 실제로 쓰는 것
    adj = []
    for a in range(len(order) - 1):
        i, j = order[a], order[a + 1]
        adj.append((i, j, pair_prob(items[i][0], items[i][1],
                                    items[j][0], items[j][1])))
    adj_stable = sum(1 for _, _, p in adj if p >= stable)
    frac = n_stable / n if n else 0.0
    판정 = ("순서 선다" if frac >= 0.8 else
          ("일부만" if frac >= 0.4 else "순서 못 읽는다"))
    return {"순서": order, "쌍": n, "선 쌍": n_stable, "몫": round(frac, 3),
            "이웃 쌍": len(adj), "선 이웃": adj_stable,
            "동전 던지기": [(i, j, round(p, 3)) for i, j, p in coin[:8]],
            "판정": 판정,
            "한 줄": (f"순위 --- {n_stable}/{n} 쌍이 섰다({100*frac:.0f}%) · "
                    f"이웃 {adj_stable}/{len(adj)} · {판정}")}


def pairs_from_draws(draws: dict, stable: float = STABLE) -> dict:
    """부트스트랩 표본이 있으면 정확히 센다.

    ``draws`` 는 {이름: [뽑기마다의 값]} 이고 모든 이름이 **같은 재추출**을
    써야 한다(그래야 상관이 살아 있다).
    """
    import numpy as np
    ks = list(draws)
    if len(ks) < 2:
        return {"판정": "못 잰다"}
    M = {k: np.asarray(draws[k], float) for k in ks}
    order = sorted(ks, key=lambda k: -float(M[k].mean()))
    n = n_stable = 0
    coin = []
    for a in range(len(order)):
        for b in range(a + 1, len(order)):
            i, j = order[a], order[b]
            p = float((M[i] > M[j]).mean())
            n += 1
            if p >= stable:
                n_stable += 1
            else:
                coin.append((i, j, round(p, 3)))
    frac = n_stable / n if n else 0.0
    return {"순서": order, "쌍": n, "선 쌍": n_stable, "몫": round(frac, 3),
            "동전 던지기": coin[:8],
            "판정": ("순서 선다" if frac >= 0.8 else
                   ("일부만" if frac >= 0.4 else "순서 못 읽는다")),
            "한 줄": f"순위(정확) --- {n_stable}/{n} 쌍이 섰다({100*frac:.0f}%)"}
