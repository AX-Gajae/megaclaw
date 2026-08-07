"""청력 --- 이 정식화가 어느 도메인의 **전용 축**을 들을 수 있나(노트 276~280).

노트 276이 팝업 전용 축 넷의 ``정확히 0.0000''을 파고들어 범인을 찾았다:
``HistGradientBoostingRegressor`` 의 ``min_samples_leaf`` 기본값 20 이다.
관측 학습행이 그보다 적으면 그 열로 가르는 분기가 **후보에도 못 오른다**.

노트 277~280이 그것을 정식화 일곱 x 도메인 다섯으로 넓혀 곡선을 그렸다
(도메인마다 라벨 순위를 그대로 전용 열로 주는 진단). 모양이 넷이다:

    문턱 없음      F6 · F9    순수 풀링. 16행에서도 +0.53~0.63
    40행 계단      F8 · F18   2 x min_samples_leaf. 16행 0.000 → 54행 +0.57~0.66
    완만한 경사     F21 · F23  .088 → .246 → .311 → .314 → .596
    80~259 계단    F10        넘고 나면 일곱 중 최고(+0.735)

**판 rho 는 이 성질을 구조적으로 못 본다**(노트 279) --- 웹툰 27.3% + 애니
23.6% 로 절반이 큰 도메인인데, 정식화 일곱이 서로 달라지는 자리는 작은
도메인뿐이다. 웹툰에서 일곱의 폭이 0.209(1.4배)인데 팝업에서는 0.634(무한)다.

그래서 **판정치 옆에 손으로 적는다**(노트 278 규약). 이 파일이 그 자리다.
승격을 막지 않는다 --- 거부권이 아니라 이름표다.
"""
from __future__ import annotations

import numpy as np

# 노트 280 이 라벨 누출 열로 잰 문턱(배포 학습행). 나무 계열은 코드에서
# 직접 읽으므로 여기 안 적는다 --- 손잡이가 바뀌면 같이 바뀌어야 한다.
MEASURED = {
    "F6_directpool": (0, "순수 풀링 --- 16행에서도 +0.527"),
    "F9_ranklik": (0, "순수 풀링 --- 16행에서도 +0.634"),
    "F21_recentpick": (0, "경사 --- 16행 +0.088, 2,106행 +0.596"),
    "F23_rankmix": (0, "경사 --- F21 과 F18 의 반반"),
    # 노트 281이 웹툰을 얇게 만들어 좁혔다 --- 200행까지 0, 400행에서
    # +0.7354 이고 그 값이 2,106행과 소수 넷째 자리까지 같다(배합 선택이
    # 이산이라 넘고 나면 포화한다). 나무의 22보다 열 배 이상 높다.
    "F10_pershrink": (400, "도메인별 배합 --- 이산 전환, 문턱은 200~400 사이"),
}

_DEFAULT_LEAF = 20      # sklearn HistGradientBoostingRegressor 의 기본값


def _leaf(make) -> int | None:
    """정식화가 실제로 쓰는 잎 하한. 나무가 아니면 None."""
    try:
        f = make()
    except Exception:
        return None
    kw = getattr(f, "kw", None)
    if not isinstance(kw, dict) or "max_depth" not in kw:
        return None                    # 나무 계열이 아니다
    return int(kw.get("min_samples_leaf") or _DEFAULT_LEAF)


def threshold(name: str, make=None) -> tuple[int | None, str]:
    """(학습행 문턱, 왜). 이 아래 도메인의 전용 축은 무시된다.

    **안 잰 정식화는 ``None``(모름)이다 --- 0(다 들린다)이 아니다.**
    ``provenance`` 가 ``등록 안 된 축은 사후로 본다''로 세운 규약과 같은
    방향이다(노트 141 --- 모르면 막는 쪽이 맞다). 첫 판에서 0 으로 뒀다가
    F2 · F16 같은 안 잰 정식화가 ``못 듣는 도메인 없음''으로 보고됐다.
    """
    leaf = _leaf(make) if make is not None else None
    if leaf is not None:
        # **두 배가 아니다**(노트 281이 노트 276 · 280의 추론을 정정).
        # 전용 열은 그 도메인 행에서만 값이 변하고 나머지 수천 행은 채움값
        # 0.5 라, 특수 행을 한쪽으로 가르면 반대쪽 잎에는 언제나 수천 행이
        # 있다. **채워야 할 잎은 하나뿐이다.** 웹툰을 얇게 만들어 훑으니
        # 20까지 정확히 0, 22 에서 +0.0765 --- 배깅 자루가 특수 행을
        # 평균만큼만 가지므로 +2 만큼 여유를 둔다.
        return leaf + 2, f"min_samples_leaf({leaf}) + 배깅 여유 2 --- 노트 281"
    if name in MEASURED:
        return MEASURED[name]
    return None, "안 쟀다 --- 모름(0 이 아니다). 재려면 노트 280 의 누출 열 실험"


def train_rows(data, T: float = 2025.0, axis: str | None = None) -> dict:
    """도메인별 배포 학습행.

    ``axis`` 를 주면 **그 축이 관측된** 학습행만 센다. 노트 271이 셋을
    갈랐다 --- 유보 행 · 라벨 있는 행 · **그 축 관측 행**. 청력은 셋째를
    봐야 한다.

    노트 287에서 이걸로 한 번 틀렸다: 넓힌 팝업 판이 학습을 16 → 73 으로
    늘려 청력 문턱 22 를 넘긴 것처럼 보였는데, ``pop_*`` 축이 관측된 학습행은
    **17** 이었다(넓힌 판이 더한 57행에 파생 필드가 없다). 축 없이 부르면
    ``어떤 축이든 다 관측된다''고 가정하는 셈이다.
    """
    out = {}
    for d in data.dom:
        y = data.dom[d][2]
        k = np.isfinite(data.yr[d]) & (data.yr[d] < T) & np.isfinite(y)
        if axis is not None:
            nm = list(data.names.get(d) or [])
            if axis not in nm:
                out[d] = 0
                continue
            k = k & (data.dom[d][1][:, nm.index(axis)] > 0)
        out[d] = int(k.sum())
    return out


def report(name: str, data, make=None, T: float = 2025.0,
           axis: str | None = None) -> dict:
    """이 실행에서 못 듣는 도메인은 어디인가.

    ``axis`` 를 주면 그 축이 관측된 학습행으로 센다(노트 287). 안 주면
    라벨 있는 학습행이고, 그건 **관측 100% 인 축에만** 맞는 수다.
    """
    th, why = threshold(name, make)
    rows = train_rows(data, T, axis=axis)
    if th is None:
        return {"문턱": None, "왜": why, "학습행": rows, "축": axis,
                "못 듣는 도메인": None,
                "한 줄": f"청력 **모름** ({why})"}
    deaf = sorted((d for d, n in rows.items() if n < th), key=lambda d: rows[d])
    tag = f" · 축 {axis}" if axis else " · 축 무관(관측 100% 가정)"
    return {"문턱": th, "왜": why, "학습행": rows, "축": axis,
            "못 듣는 도메인": deaf,
            "한 줄": (f"청력 문턱 {th}행 ({why}){tag} --- 못 듣는 도메인 "
                    + (", ".join(f"{d} {rows[d]}행" for d in deaf) if deaf
                       else "없음"))}
