"""판 표기값을 씨앗 평균으로 낸다(노트 395).

**자료를 한 글자도 안 바꿔도 판이 0.012 를 오간다.** 챔피언 자료를 고정하고
``F18_bagboost`` 의 배깅 씨앗만 0..11 로 바꿔 재면 0.4419 ~ 0.4540,
SD **0.0033** 이다. 배깅 자루가 여덟 개뿐이라 씨앗이 남긴 분산이 그만큼
남는다.

그래서 ``판이 0.4435 에서 0.4420 으로 내려갔다'' 같은 문장은 뜻이 없다 ---
그 차이가 씨앗 SD 의 절반도 안 된다. 노트 394의 애니 채택에서 짝 12뽑기는
$+0.0073$ · 12/12 인데 단일 적합은 내려간 것이 그 때문이다.

**판정은 안 고친다.** 짝 12뽑기는 두 팔에 같은 되뽑기와 같은 씨앗을 주므로
이 잡음이 상쇄된다(노트 366의 ``짝 SD 0.003 대 수준 SD 0.016''에서 수준 SD
쪽이 바로 이것이다). 고치는 것은 **표기**뿐이다.

**도메인 표기값은 더 심하다** --- 씨앗 SD 가 아이돌 0.0420 · 팝업 0.0285 ·
도서 0.0132 로, 유보가 작을수록 크다. 대장에 넷째 자리로 적어 온 도메인
수는 이 폭을 달고 읽어야 한다.

    from lab.board import board
    b = board(data)          # {'판': .., 'SE': .., '도메인': {..: (평균, SD)}}
"""
from __future__ import annotations

import numpy as np

from . import forms
from .harness import evaluate

SEEDS = 12
FORM = "F18_bagboost"


def board(data, seeds: int = SEEDS, form: str = FORM, T: float = 2025.0) -> dict:
    """씨앗을 바꿔 가며 재고 평균과 표준오차를 돌려준다."""
    cls = forms.REGISTRY[form]["cls"]
    vals, per = [], {}
    for s in range(seeds):
        sc = evaluate(lambda s=s: cls(seed=s), data, T=T)
        # **T 를 가중에도 넘긴다**(노트 668). 안 넘기면 평가는 T 유보로 하고
        # 가중은 2025 유보 수로 하는 어긋남이 생긴다 --- 노트 273·328 이 잡은
        # 것과 같은 병이다(``T 를 한 군데만 넘김''). 기본 T 에서는 아무것도
        # 안 바뀌므로 지금까지 조용했다.
        vals.append(float(data.pooled(sc, T=T)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    v = np.array(vals)
    return {"판": float(v.mean()),
            "SD": float(v.std(ddof=1)),
            "SE": float(v.std(ddof=1) / np.sqrt(len(v))),
            "씨앗": len(v),
            "도메인": {k: (float(np.mean(a)), float(np.std(a, ddof=1)))
                     for k, a in per.items()}}


def fmt(b: dict) -> str:
    """대장·노트에 적을 한 줄."""
    return "판 %.4f ± %.4f (씨앗 %d)" % (b["판"], b["SE"], b["씨앗"])
