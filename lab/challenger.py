"""챌린저 장부 --- **챔피언이 아닌 모형의 실측 기록**(노트 803·804 · 규약 41).

**챌린저는 채택이 아니다.** 판의 챔피언(`F18_bagboost` 합동 적합)은 그대로이고,
이 장부는 *"다른 모형이 어디서 얼마나 이기는가"* 의 실측을 담는다. 승격 절차
(규약 12 등)는 서빙에 물릴 때 그때 따진다.

첫 항목 --- **TabPFN 보조 헤드(소외 도메인)**. 노트 803 이 얇은 5도메인에서
재고 804 가 새 씨앗으로 확인했다:

    판 중앙 엔진으로는 기각 --- 5도메인 가중 0.3377 대 챔피언 0.4244.
    전이가 센 곳(팝업·도서·게임)에서 챔피언이 2σ 밖 압승.

    그러나 판이 소외한 두 도메인에서 TabPFN(도메인 단독 · SCM 사전)이
    2σ 밖으로 이기고 새 씨앗에서 유지된다:

        아이돌    챔피언 0.45~0.46 → TabPFN 0.63   (+0.17~0.18 · 2σ 0.0367)
        시장팝업   챔피언 0.14~0.15 → TabPFN 0.23   (+0.07~0.09 · 2σ 0.0233)

    기제 읽기(노트 806 이 가렸다): **아이돌은 부류의 문제**다 --- 단독 F18 도
    0.4367 로 합동(0.4515)과 2σ 안이라 전이가 거의 안 주고, gbdt 로는 어떻게
    적합해도 0.45 근처다. **시장팝업은 합동이 크게 돕는 곳**이다 --- 살아 있는
    열이 3개뿐이라 단독 F18 은 무신호(0.0277)이고 합동이 +0.127 을 끌어올리며,
    같은 3열로 SCM 사전은 0.2286 을 낸다. **합동 제거는 어느 쪽에도 답이
    아니다** --- 보조 헤드가 옳은 처방이다. 도서(80행)에서는 단독 TabPFN 도 죽었다
    (0.170) --- 사전은 '세계가 어떤가' 를 주지 '이 도메인이 어떤가' 를 주지
    않으며, 후자는 이웃 도메인의 전이가 준다(노트 803 의 핵심 반증).

쓰는 법::

    python3 -m lab.challenger            # 장부 찍기
    python3 -m lab.challenger --rerun    # 다시 재기(씨앗 넷 · 약 6분)
"""
from __future__ import annotations

import json

import numpy as np
from scipy.stats import spearmanr

T = 2025.0

#: 확인된 항목. **측정 없이 이 표를 고치지 않는다** --- 숫자는 노트가 근거다.
LEDGER = [
    {"챌린저": "TabPFN 2.2.1 (도메인 단독 · X=[A|M|t] · CPU)",
     "구역": {"아이돌": {"챔피언": 0.4515, "TabPFN": 0.6315, "차": +0.1800,
                     "2σ": 0.0367, "확인": "노트 804 (씨앗 4~7)"},
            "시장팝업": {"챔피언": 0.1545, "TabPFN": 0.2286, "차": +0.0741,
                      "2σ": 0.0233, "확인": "노트 804 (씨앗 4~7)"}},
     "기각 구역": {"팝업": -0.2159, "도서": -0.2134, "게임": -0.1223},
     "지위": "**챌린저 --- 서빙 아님.** 판 챔피언 그대로(노트 803·804)",
     "노트": [803, 804]},
]


def xy(data, d, T=T):
    """챔피언과 같은 행 · 같은 정보. 노트 803 의 배선 그대로."""
    yr = np.asarray(data.yr[d], float)
    A, M, y, t = data.dom[d]
    y = np.asarray(y, float)
    fin = np.isfinite(yr) & np.isfinite(y)
    ktr, kho = fin & (yr < T), fin & (yr >= T)
    X = np.nan_to_num(np.hstack([A, M, np.asarray(t, float)[:, None]]), nan=0.5)
    return X[ktr], y[ktr], X[kho], y[kho]


def rerun(domains=("아이돌", "시장팝업"), seeds=(4, 5, 6, 7)) -> dict:
    """장부 항목을 다시 잰다 --- 지문이 낡았는지 볼 때."""
    from lab import calib as C, forms
    from lab.sideaudit import champion_data
    from tabpfn import TabPFNRegressor
    cls = forms.REGISTRY["F18_bagboost"]["cls"]
    data = champion_data()
    out = {}
    for d in domains:
        ch, tb = [], []
        for s in seeds:
            fc = C.forecasts(lambda s=s: cls(seed=s), data, T=T, seed=s)
            if d in fc:
                _, _, pho, yho = fc[d]
                ch.append(float(spearmanr(pho, yho).statistic))
            Xtr, ytr, Xho, yho2 = xy(data, d)
            m = TabPFNRegressor(device="cpu", random_state=s)
            m.fit(Xtr, ytr)
            p = np.asarray(m.predict(Xho), float)
            tb.append(float(spearmanr(p, yho2).statistic))
        out[d] = {"챔피언": round(float(np.mean(ch)), 4),
                  "TabPFN": round(float(np.mean(tb)), 4),
                  "차": round(float(np.mean(tb) - np.mean(ch)), 4)}
    return out


if __name__ == "__main__":
    import sys
    if "--rerun" in sys.argv:
        print(json.dumps(rerun(), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(LEDGER, ensure_ascii=False, indent=1))
