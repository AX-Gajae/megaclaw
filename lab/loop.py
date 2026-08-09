"""큰 루프 --- 정식화 포트폴리오를 굴린다.

**바뀐 것.** 노트 124까지는 ``한 번 깨어남 = 한 노트''였고 루프의 크기가
한 사이클로 고정돼 있었다. 그래서 스물여덟 노트 동안 같은 정식화 안에서만
움직였고, 노트 103에서 ``구조적 막다른 골목''이라 진단해 놓고도 스무 편을
더 그 안에서 돌았다.

여기서는 **목표만 고정**이다.

    IP · 기획 → 소비자 반응.  측정은 lab/harness.py 가 방법과 무관하게 한다.

그 아래 정식화는 챔피언/도전자로 경쟁하고, 이기면 승격 지면 은퇴한다.
루프가 하는 일은 넷뿐이다.

    ① 아직 안 붙여 본 도전자를 붙인다
    ② 이긴 것을 챔피언으로 올리고 진 것은 은퇴시킨다
    ③ 가드가 깨진 실행은 점수를 무효로 한다
    ④ 무엇을 언제 했는지 다 남긴다(lab/store.py → 모니터 UI)

사용:
    python3 -m lab.loop --once            한 라운드
    python3 -m lab.loop --rounds 5        다섯 라운드
    python3 -m lab.loop --form F1_procrustes   하나만
"""
from __future__ import annotations

import argparse
import json
import time
import traceback

import numpy as np

from . import forms, guards, store
from .harness import PRIMARY, Data, board, bootstrap_ci, evaluate, headline, load

PROTOCOLS = [("deploy", 2025.0), ("all", None)]

# 축 세트는 정식화의 성질이 아니라 **자료의 성질**이다. 정식화마다 ``+검색''
# 변형을 만드는 대신 자료를 갈아 끼우고 실행에 꼬리표를 단다.
def _fixed(extra=None, labels: bool = True):
    """자료를 읽고 확인된 측정 아티팩트를 고친다(노트 207 · 210).

    ``labels`` 는 라벨 고침이다 --- 게임의 누적 리뷰를 30일 창으로 바꾼다.
    라벨을 바꾸면 과제가 바뀌므로 판 수를 옛것과 직접 견주면 안 된다."""
    from .fixaxes import apply, apply_labels, orient
    d = orient(apply(load(extra) if extra else load()))
    return apply_labels(d) if labels else d


AXES = {
    "base":    lambda: _fixed(),
    "trend":   lambda: _fixed(_trend(zero_is_data=True)),
    "trend0":  lambda: load(_trend(zero_is_data=False)),
    # 웹툰은 라벨(네이버 즐겨찾기)과 축(네이버 검색)이 같은 플랫폼이라 따로
    # 뗀 판을 남겨 둔다. 노트 129에서 재 보니 이득이 덮음이 비슷한 모바일보다
    # 오히려 낮아 결합 증거는 안 나왔지만, 판단이 바뀔 수 있으니 갈래를 남긴다.
    "trend_nowt": lambda: load(_trend(zero_is_data=True, drop_wt=True)),
    # 달력 --- 수집 비용 0, 전 도메인 100% 덮음. 노트 130 에서 팝업 일평균을
    # 제일 잘 설명한 것이 주말 비중(+0.427)이었던 데서 나왔다.
    "cal":      lambda: _fixed(_cal()),
    "grp":      lambda: load(_grp()),
    "trendcalgrp": lambda: load({**_trend(zero_is_data=True), **_cal(), **_grp()}),
    "trendcal": lambda: _fixed({**_trend(zero_is_data=True), **_cal()}),
    # 위키 조회수 --- 노트 149. 네이버 검색이 0%인 만화·세계애니를 채운다
    "wiki": lambda: _fixed(_wiki()),
    "trendcalwiki": lambda: _fixed({**_trend(zero_is_data=True), **_cal(),
                                    **_wiki()}),
    # 태그 내용까지 --- 웹툰 큐레이션 태그 SVD(노트 255)
    "trendcalwikitag": lambda: _fixed({**_trend(zero_is_data=True), **_cal(),
                                       **_wiki(), **_tag()}),
    # 팝업 전용 축까지 --- 노트 276. 판은 이걸 못 본다(노트 274의 0.435).
    # 노트 275의 규칙으로 재는 판이다: 판이 미결정 폭 안이면 배포가 정한다.
    "trendcalwikitagpop": lambda: _fixed({**_trend(zero_is_data=True), **_cal(),
                                          **_wiki(), **_tag(), **_pop()}),
    # 시장팝업 범주까지 --- 노트 285. 열한 번째 도메인의 굶은 축을 채운다.
    "trendcalwikitagmkt": lambda: _fixed({**_trend(zero_is_data=True), **_cal(),
                                          **_wiki(), **_tag(), **_mkt()}),
    # 레코드 필드까지 --- 웹툰 태그 수(노트 239)
    "full": lambda: _fixed({**_trend(zero_is_data=True), **_cal(),
                            **_wiki(), **_rec()}),
    # 펀딩 전용 범주 축을 더한 판(노트 309). 노트 303 이 "도서·펀딩에 축을
    # 더 --- 빌릴 자리가 있다"를 남겼고 그 자리를 실제로 채운 것이다.
    "trendcalwikitagfund": lambda: _fixed({**_trend(zero_is_data=True), **_cal(),
                                           **_wiki(), **_tag(), **_fund()}),
    # 애니 전용 매체 축을 더한 판(노트 321). fund_cat 과 같은 훑기에서 나왔고
    # 채택 검사 셋을 통과했다. 다만 학습의 94%가 TVA 라 거의 상수다.
    "trendcalwikitagani": lambda: _fixed({**_trend(zero_is_data=True), **_cal(),
                                          **_wiki(), **_tag(), **_anime()}),
    # 둘 다 --- fund_cat + anime_medium
    "trendcalwikitagfundani": lambda: _fixed({**_trend(zero_is_data=True),
                                              **_cal(), **_wiki(), **_tag(),
                                              **_fund(), **_anime()}),
    # 원천 레코드에서 캐낸 전용 축 열(노트 324). 검사 ①②③④ + 출처를 다
    # 통과한 것만 --- 선별기가 마흔셋을 주고 출처가 서른둘을 막았다.
    "trendcalwikitagraw": lambda: _fixed({**_trend(zero_is_data=True), **_cal(),
                                          **_wiki(), **_tag(), **_raw()}),
    "trendcalwikitagfundraw": lambda: _fixed({**_trend(zero_is_data=True),
                                              **_cal(), **_wiki(), **_tag(),
                                              **_fund(), **_raw()}),
    # 팝업 이력을 넓힌 판 --- 노트 133
    "wide":          lambda: _wide(),
    "wide_trend":    lambda: _wide(lambda: _trend(zero_is_data=True)),
    "wide_trendcal": lambda: _wide(
        lambda: {**_trend(zero_is_data=True), **_cal()}),
    # 넓힌 판 + 팝업 전용 축 --- 노트 287. 노트 286 이 벽 셋이 전부 팝업
    # 학습 16행에서 나온다고 밝혔고, 넓힌 판은 그것을 73행으로 늘려 청력
    # 문턱(22)과 채택 검사 ①(30)을 둘 다 넘긴다. **벽을 치우고 노트 276 을
    # 다시 하는 판이다.**
    "wide_trendcalpop": lambda: _wide(
        lambda: {**_trend(zero_is_data=True), **_cal(), **_pop()}),
    # 같은 코드 경로의 좁은 판 --- 확장 효과만 떼어 보려면 이것과 견줘야 한다
    "narrow_trendcal": lambda: _wide(
        lambda: {**_trend(zero_is_data=True), **_cal()}, mode="now"),
    # **챔피언 축 세트는 ``idolwide_full`` 이다**(노트 346). 아이돌 넓힘을
    # 노트 325~334 에서 재고 자료 결정으로 적어 놓고도 열두 노트 동안 기본
    # 경로에 안 넣고 있었다 --- ``쟀다''와 ``쓴다''는 다르다.
    #
    # 아이돌 라벨 기준 필터를 푼 판(노트 326). 학습 54 -> 122, **유보는 25 그대로**
    # 라 분모가 안 바뀐다. ``cut`` 이 앨범 메타 파생 축 둘을 뺀다 --- 그 둘의
    # 표시자가 한터 여부와 99.4% 같아서 기준을 나른다(풀의 그림자).
    "idolwide": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                               **_wiki(), **_tag()}, mode="cut"),
    # 위키를 되살린 판(노트 332). 173건을 다 긁어 풀 그림자를 지운 뒤다.
    "idolwide_wiki": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                    **_wiki(), **_tag()}, mode="cut",
                                   with_wiki=True),
    "idolnarrow_wiki": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                      **_wiki(), **_tag()}, mode="cut",
                                     wide=False, with_wiki=True),
    # 값이 버나 표시자가 버나(노트 332). 노트 306의 덫이 여기도 있나 본다.
    # 위키 + 검색 둘 다 되살린 판(노트 333)
    # **챔피언**(노트 346 · 347). 아이돌 넓힘 + 위키 · 검색 되살림 +
    # ``fund_cat``. fund_cat 은 노트 309 에서 채택 검사 셋을 다 통과하고도
    # 축 세트 ``trendcalwikitagfund`` 로만 있었다 --- 노트 347 이 그것을
    # 찾아 검사 ⑤ 를 돌리고(판 +0.0035 · 8/8) 붙였다(판 +0.0030 · 11/12 ·
    # 펀딩 +0.0964 · 12/12).
    #
    # **유보를 25 -> 51 로 늘렸다**(노트 353). 노트 352가 아이돌 rho 의 95%
    # 구간을 [0.052, 0.817] --- 폭 0.756 --- 으로 쟀다. 판에서 제일 안 재지는
    # 도메인이고 원인은 유보 25행이다. 버려 뒀던 비한터 2025년 이후 26행을
    # 넣으니 폭 0.757 -> 0.556 이다.
    #
    # **점수로 고른 것이 아니다** --- 넣으면 아이돌이 0.4860 -> 0.3021 로
    # 내려가고 판도 0.4953 -> 0.4891 이다. 분모도 2,669 -> 2,695 로 바뀌니
    # 옛 판 수와 직접 못 견준다.
    #
    # 미리 적은 거부 조건(``새 26행의 rho 가 한터 25행과 0.25 이상 다르면
    # 안 넣는다'')이 실제로 켜졌다(+0.0972 대 +0.5188). 그런데 그 검사가
    # **연도를 안 맞춘 것**이었다 --- 아이돌 rho 는 연도에 크게 흔들린다
    # (한터 2025 +0.3131 대 2026 +0.6727). 연도를 맞추면 2025 에서 한터
    # +0.3131(n=14) 대 추가 +0.3884(n=17) 로 **추가 쪽이 낫고**, 차이는
    # 전부 2026 의 스무 행(한터 11 · 추가 9)에서 온다. 검사가 틀렸지 자료가
    # 틀린 게 아니다.
    #
    # **팝업 등급 필터도 푼다**(노트 358). ``popupset`` 이 ``grades=("A","B")``
    # 로 조이는데, 노트 352 가 시장팝업 유보 104행에서 ``label_trust`` 등급이
    # **정확도를 전혀 예측하지 않는다**를 쟀다(깨끗한 B+C 가 0.2147 로 전체
    # 0.2880 보다 낮고, 같은 크기 무작위와 견줘 p=0.907). 점수와 무관한
    # 근거이고 다른 도메인에서 먼저 나왔다.
    #
    # 계수 방법은 안 건드린다 --- 노트 357 이 ``organizer_claim`` 은 수준이
    # 곱셈으로 부풀어 섞으면 순위가 기준으로 서는 것을 보였다. 여기서 푸는
    # 것은 등급뿐이라 그 위험이 없다. 팝업 75행 -> 89행(학습 16 -> 24 ·
    # 유보 59 -> 65), 판 분모 2,717 -> 2,723.
    #
    # 짝 열둘: 판 +0.0010(6/12) · **팝업 +0.0140(9/12)**. 판은 미결정이고
    # 제일 나쁜 도메인이 도서 |t|=0.07 이라 노트 275 규칙이 배포로 넘기고,
    # 배포 수치가 오르므로 넣는다 --- 노트 351 과 같은 자리다.
    #
    # **집단 표지 축 grp 를 넣었다**(노트 413). 노트 138 이 바닥선을 만들려고
    # 지은 축인데 챔피언에 한 번도 안 들어가 있었다 --- 여덟 도메인에 100%
    # 덮음이고 전부 기획 시점 정보다(연령등급 · 무료 여부 · 매체 · 포맷 ·
    # 국가 · 카테고리).
    #
    # 짝 12뽑기: 판 **+0.0029 +- 0.0025 · 11/12**, 조건 ① 로 채택.
    #
    # **사전 등록이 거꾸로 틀렸다.** 노트 412 를 보고 ``덮인 도메인이 벌고
    # 안 덮인 셋이 낸다''고 적었는데 --- 덮인 평균 +0.0042 대
    # **안 덮인 평균 +0.0278**(아이돌 +0.0482 · 팝업 +0.0361). grp 가
    # 도메인 사이 분산을 흡수하니 공유 축이 도메인 가르기에 안 쓰이고
    # 도메인 **안**의 신호를 나르게 된다 --- 안 덮인 도메인이 제일 크게 번다.
    #
    # creator_track 과 anime_medium 은 같이 넣으면 판이 +0.0010 · 6/12 로
    # 내린다. 노트 164 가 적은 대로 venue_prominence 슬롯이 이미 사전
    # 출시작 수라 **중복**이다. grp 만 넣는다.
    #
    # **갈래 축 gen 도 넣었다**(노트 419). 레코드 전수조사에서 `genres` 가
    # 다섯 도메인(만화·모바일·애니·세계애니·게임)에 80% 넘게 차 있는 것을
    # 찾았다. grpaxes 와 달리 **눈금을 도메인 사이에서 공유한다** ---
    # 어휘가 실제로 겹치기 때문이다(romance/로맨스 · action/액션).
    #
    # 짝 12뽑기: 판 **+0.0034 +- 0.0022 · 11/12**, 조건 ① 로 채택.
    # gen 이 덮는 도메인이 오른다(만화 +0.0171·12/12 · 애니 +0.0093 ·
    # 모바일 +0.0073). 팝업 -0.0332 · 게임 -0.0106 이 낸다.
    #
    # **그런데 전이는 안 샀다**(노트 419) --- KR 만화에 gen 값을 1713/1716
    # 채웠는데도 전이가 +0.2128 -> +0.1946 이다. **``안 본 도메인에 값이
    # 있느냐''는 요점이 아니다.** 노트 417 이 적은 기계 설명을 그만큼 고친다.
    "idolwide_full": lambda: _idol({**_trendsub(zero_is_data=True), **_calsub(),
                                    **_wikisub(), **_tag(), **_fund(), **_rawsub(),
                                    **_grp(), **_gen()},
                                   mode="cut", with_wiki=True, with_trend=True,
                                   wide_post=True, wide_pop="grades"),
    # fund_cat 없는 판 --- 노트 347 의 대조
    "idolwide_nofund": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                      **_wiki(), **_tag()}, mode="cut",
                                     with_wiki=True, with_trend=True),
    "idolwide_trend": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                     **_wiki(), **_tag()}, mode="cut",
                                    with_trend=True),
    # **그림자를 다 지운 뒤의 판**(노트 334). 앨범 메타를 173건 다 긁어
    # 관측률이 한터 85% · 추가 87% 가 됐으므로 노트 326 이 뺐던 축 둘
    # (entry_friction · goods_scale)을 되살린다.
    # 축 둘을 따로 되살린다(노트 335) --- 원천이 같다고 축이 같지 않다.
    "idolwide_goods": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                     **_wiki(), **_tag()}, mode="cut",
                                    with_wiki=True, with_trend=True,
                                    keep_axes=("goods_scale",)),
    "idolwide_entry": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                     **_wiki(), **_tag()}, mode="cut",
                                    with_wiki=True, with_trend=True,
                                    keep_axes=("entry_friction",)),
    # 열 위약 --- 값만 섞는다. 열 수·관측 무늬는 그대로다(노트 335).
    "idolwide_goods_pl": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                        **_wiki(), **_tag()}, mode="cut",
                                       with_wiki=True, with_trend=True,
                                       keep_axes=("goods_scale",), scramble=335),
    # 열의 한계값(노트 338) --- 같은 위약 열을 축이 적은 판과 많은 판에
    # 각각 붙인다. 노트 337 이 같은 25행에 앨범 축 둘(-0.05)과 위키 축
    # 넷(+0.07)을 붙여 부호가 갈린 것을 봤고, 남은 설명이 "이미 몇 열이
    # 있었나" 다.
    "idolwide_bare_pl": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                       **_wiki(), **_tag()}, mode="cut",
                                      keep_axes=("goods_scale",), scramble=338),
    "idolwide_all": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                   **_wiki(), **_tag()}, mode="keep",
                                  with_wiki=True, with_trend=True),
    "idolwide_wikival": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                       **_wiki(), **_tag()}, mode="cut",
                                      with_wiki=True, wiki_part="값만"),
    "idolwide_wikiobs": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                       **_wiki(), **_tag()}, mode="cut",
                                      with_wiki=True, wiki_part="표시자만"),
    "idolwide_keep": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                    **_wiki(), **_tag()}, mode="keep"),
    # 같은 코드 경로의 좁은 판 --- 넓힘 효과만 떼려면 이것과 견준다
    "idolnarrow": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                 **_wiki(), **_tag()}, mode="cut", wide=False),
    # 같은 경로 · 좁은 판 · 축을 지킨 것 --- 축 둘의 값만 떼려면 이것과 견준다
    "idolnarrow_keep": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                      **_wiki(), **_tag()}, mode="keep",
                                     wide=False),
    # 위약 --- 추가 68행의 라벨만 섞는다. 행이 늘어 생기는 이득과 라벨
    # 정보를 가른다(노트 133: 첫 양수를 그대로 채택하지 않는다).
    "idolwide_placebo": lambda: _idol({**_trend(zero_is_data=True), **_cal(),
                                       **_wiki(), **_tag()}, mode="cut",
                                      placebo=326),
}


def _basis(n: int, grades=("A", "B")):
    """팝업 넓힌 판의 행별 계수 기준(노트 357). ``popupset.build`` 와 같은 순서."""
    import json as _j
    import numpy as _np
    z = _np.load("data/state/popup_v2.npz", allow_pickle=True)
    cols = [str(c) for c in z["names"]]
    X, yv = z["X"], z["y_perday"]
    meta = _j.loads(open("data/state/popup_v2_meta.json").read())
    keep = _np.zeros(len(yv), bool)
    for g in grades:
        if "trust_%s" % g in cols:
            keep |= X[:, cols.index("trust_%s" % g)] > 0.5
    keep &= _np.isfinite(yv)
    keep &= _np.array([bool(m.get("scope_usable")) for m in meta])
    out = [m.get("counting") for m, k in zip(meta, keep) if k]
    assert len(out) == n, (len(out), n)
    return out


def _dead_axes(data, T: float = 2025.0) -> dict:
    """표시자가 **어디서도 1 이 아닌** 축을 찾는다(노트 415 규약).

    축 모듈이 옛 행 수로 지어져 있으면 `harness.load` 가 길이 불일치로
    떨어뜨리고 중립 0.5 · 표시자 0 을 채운다 --- 열은 목록에 남아 있는데
    **아무 값도 안 나른다**. 노트 415 가 `popaxes` 넷이 노트 358(팝업
    75행 -> 89행) 이후로 그렇게 죽어 있던 것을 찾았다. 관문을 돌리면
    ``무해하다''로 보이지만 실은 **한 번도 안 재 본 것**이다.

    거부권이 아니라 이름표다 --- 판을 안 바꾸고 기록에만 남긴다."""
    import numpy as _np
    from .forms import DirectPool, axis_order
    order = axis_order(data, None)
    seen = {a: 0.0 for a in order}
    for d in data.dom:
        A, M, y, t = data.dom[d]
        if len(y) == 0:
            continue
        F = DirectPool._feat(A, M, data.names.get(d), order)
        for j, a in enumerate(order):
            seen[a] = max(seen[a], float(F[:, 2 * j + 1].mean()))
    return {"죽은 축": [a for a in order if seen[a] <= 0.0],
            "축 수": len(order)}


def _scored_census(data, T: float = 2025.0) -> dict:
    """도메인마다 학습·유보 행 수와 **걸린 문턱**을 적는다(노트 401 규약).

    거부권이 아니라 이름표다 --- 판을 안 바꾸고, 무엇이 조용히 빠졌는지만
    기록에 남긴다."""
    import lab.harness as _H
    import numpy as _np
    out = {}
    for d in sorted(data.dom):
        y = data.dom[d][2]; yr = data.yr[d]
        tr = int(((yr < T) & _np.isfinite(y)).sum())
        ho = int(((yr >= T) & _np.isfinite(y)).sum())
        why = []
        if tr < _H.MIN_TRAIN:
            why.append("학습<%d(안 배우고 채점만)" % _H.MIN_TRAIN)
        if ho < 20:
            why.append("유보<20(채점에서 빠짐)")
        out[d] = {"학습": tr, "유보": ho, "걸림": why or None}
    return out


def _date_hole(data, T: float = 2025.0) -> dict:
    """유보 안에서 **날짜가 라벨과 얼마나 붙어 있나**(노트 446 규약).

    판은 유보 위의 날 rho 라 **날짜를 통제하지 않는다**. 그런데 유보
    안에서 날짜와 라벨이 가중평균 $-0.228$ 로 붙어 있다(도서 $-0.562$ ·
    웹툰 $-0.350$) --- 늦게 나온 것일수록 라벨이 낮다. 라벨이 관측
    시점까지 쌓이는 양이라 **늦게 나온 쪽이 기계적으로 낮은** 것이지
    작품이 나빠서가 아니다.

    챔피언은 이 구멍을 안 쓰고 있다(예보와 날짜의 상관 $-0.067$, 날짜를
    통제해도 판이 $+0.5143 \\to +0.5158$ 로 안 내려간다). 그러나 **쓰면
    크게 오른다** --- 최근순 축 하나를 넣으니 날 판이 $+0.4764 \\to
    +0.4950$ (**$+0.0186$**) 인데 **날짜 통제 판은 $+0.5158 \\to
    +0.4864$ 로 내려간다**(도서 혼자 $+0.2376$). 이 사이클에서 진짜로
    채택된 것 중 제일 큰 게 깊이 6 의 $+0.0093$ 이니 **구멍이 진짜
    개선의 두 배**다.

    그래서 규약을 만든다 --- **판이 오르는데 날짜 통제 판이 내려가는
    변경은 안 넣는다.** 순위 규약(유보 표본의 판 rho)은 안 바꾼다;
    이건 거부권 있는 가드다.

    여기서는 자료 쪽만 찍는다(예보가 없으므로) --- 도메인마다 유보
    안 날짜↔라벨 상관과, 구멍이 큰 도메인 목록."""
    import numpy as _np
    from scipy.stats import spearmanr as _sp
    out, big = {}, []
    for d in sorted(data.dom):
        y = data.dom[d][2]; yr = data.yr[d]
        m = (yr >= T) & _np.isfinite(y) & _np.isfinite(yr)
        if m.sum() < 20 or len(_np.unique(yr[m])) < 3:
            out[d] = {"유보": int(m.sum()), "날짜↔라벨": None,
                      "걸림": "유보<20 또는 날짜가 한두 값"}
            continue
        r = float(_sp(yr[m], y[m]).correlation)
        out[d] = {"유보": int(m.sum()), "날짜↔라벨": round(r, 3)}
        if abs(r) > 0.15:
            big.append(d)
    return {"도메인": out, "구멍 큰 도메인": big,
            "규약": "판이 오르는데 날짜 통제 판이 내려가면 안 넣는다(노트 446)"}


def _cell_census(data, T: float = 2025.0) -> dict:
    """축이 행을 **몇 칸으로 가르나**(노트 454 규약).

    시장팝업은 축 셋의 덮음이 100% · 100% · 93% 로 흠잡을 데가 없는데,
    값이 두세 가지뿐이라 **249행이 18칸**에 들어간다(한 칸에 162행).
    칸 평균을 오라클로 줘도 스피어만이 **+0.2505** 를 못 넘는다 --- 그
    도메인의 같은 시기 교차검증 천장이 -0.0901 로 음수였던 것은 모형
    탓이 아니라 **자가 굵어서**였다.

    **덮음만 봐서는 안 보인다.** 그래서 따로 찍는다.

    칸 수는 노트 453 의 의존도(남만 흔들 때 내 점수의 SD)도 예보한다 ---
    고정 도메인 넷에서 행 수와는 rho -0.200 인데 **칸 수와는 +0.800**
    이다(아이돌 122행 173칸 대 시장팝업 123행 18칸).

    거부권이 아니라 이름표다 --- 판을 안 바꾸고 기록에만 남긴다."""
    import numpy as _np
    from collections import defaultdict as _dd
    from scipy.stats import spearmanr as _sp
    out, thin = {}, []
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        ok = _np.isfinite(y)
        if ok.sum() < 10:
            out[d] = {"행": int(ok.sum()), "걸림": "행<10"}
            continue
        use = [j for j in range(M.shape[1]) if (M[ok, j] > 0).sum() >= 5]
        rows = _np.where(ok)[0]
        key = [tuple(list(_np.round(A[i, use], 6))
                     + list(M[i, use].astype(int))) for i in rows]
        g = _dd(list)
        for i, k in enumerate(key):
            g[k].append(i)
        yy = y[ok]
        pred = _np.zeros(len(yy))
        for k, idx in g.items():
            pred[idx] = yy[idx].mean()
        r = _sp(pred, yy).correlation
        r = float(r) if _np.isfinite(r) else 0.0
        big = max(len(v) for v in g.values())
        out[d] = {"행": int(len(yy)), "칸": len(g),
                  "행/칸": round(len(yy) / max(1, len(g)), 2),
                  "제일 큰 칸": big, "오라클 상한": round(r, 4)}
        if r < 0.9:
            thin.append(d)
    return {"도메인": out, "상한 0.9 아래": thin,
            "왜": "덮음이 가득 차도 값 종류가 적으면 축이 행을 못 가른다(노트 454)"}


def _split_census(data, T: float = 2025.0) -> dict:
    """**축 개수로 반을 가를 수 있나**(노트 488 규약).

    노트 480~487 여덟 노트가 '축 많은 행 대 적은 행'을 독립변수로 썼는데,
    유보 행의 축 개수 분포를 찍어 보니 **다섯 중 넷이 최빈값 하나에 절반
    넘게 뭉쳐 있었다**(만화 71% · 애니 72% · 세계애니 62% · 모바일 85%).
    모바일은 441행 중 375행이 축 개수 15로 같아 중앙값 나누기의 '많은
    쪽'이 **28행**이었고, 그 28행 중 **다섯 행**에만 붙은 축 하나가
    그 여덟 노트의 '이상' 전부였다.

    그리고 뭉쳐 있으면 나누기는 개수가 아니라 **수집 하나의 있음/없음**이
    된다 --- 애니는 venue_prominence 100% 대 2%, 모바일은 wiki 82% 대 0%.
    즉 '축이 많은 행'은 대개 '축이 한 개 더 있는 행'이다.

    덮음 0% 축도 같이 센다. '저덮음 축 32개'는 거의 늘 부풀려진 수이고
    (가려도 정확히 +0.0000), 살아 있는 것은 도메인당 두셋뿐이다.

    거부권이 아니라 이름표다 --- 판을 안 바꾸고 기록에만 남긴다."""
    import numpy as _np
    out, lumpy = {}, []
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        yr = data.yr.get(d)
        ok = _np.isfinite(y)
        if yr is not None:
            ok = ok & _np.isfinite(yr) & (yr >= T)
        if ok.sum() < 20:
            continue
        cnt = M[ok].sum(axis=1)
        vs, cs = _np.unique(cnt, return_counts=True)
        mode = float(cs.max() / cs.sum())
        med = float(_np.median(cnt))
        many = int((cnt > med).sum())
        cov = (M[ok] > 0).mean(axis=0)
        out[d] = {"유보": int(ok.sum()), "축 개수 종류": int(len(vs)),
                  "최빈몫": round(mode, 3), "중앙값": med,
                  "많은 쪽": many, "적은 쪽": int(ok.sum()) - many,
                  "덮음 0% 축": int((cov <= 0).sum()),
                  "살아있는 저덮음 축": int(((cov > 0) & (cov < 0.95)).sum())}
        if mode > 0.5 or many < 40:
            lumpy.append(d)
    return {"도메인": out, "나누기 못 씀": lumpy,
            "왜": "축 개수가 최빈값에 뭉쳐 있으면 중앙값 나누기는 "
                  "개수가 아니라 수집 하나의 표시자가 된다(노트 488)"}


def _coverage_shift(data, T: float = 2025.0, thr: float = 0.15) -> dict:
    """**학습과 유보의 덮음이 다른 축**을 찍는다(노트 493~494 규약).

    노트 493 이 애니에서 잡은 것 --- 트렌드 덮음이 학습 56.4%에서 유보
    96.5%로 뛴다. 제목 길이로 같은 덮음을 맞춰 견주면 **늘 붙던 짧은
    제목은 0.1914 -> 0.1773 으로 안 늙었고** 새로 찬 긴 제목만 0.1266 ->
    0.0632 다. 축이 늙은 게 아니라 **묻는 대상이 바뀐 것**이고, 애니
    늙음의 76%가 그 선택 이동이다.

    **다만 일반 규칙은 아니다**(노트 494). 전 도메인에서 덮음 15%p 넘게
    움직이는 (도메인, 축) 짝 스물다섯을 세어 보니 덮음차와 |rho|차의
    스피어만이 **0.092** 로 관계가 없다 --- 덮음이 오른 열아홉은 오히려
    |rho| 가 평균 +0.0556 오르고, 내린 다섯이 -0.0901 로 나쁘다.

    그래서 이 가드는 **방향을 주장하지 않는다.** 이동이 있는 짝을 찍기만
    한다 --- 그 짝에서 학습 |rho| 와 유보 |rho| 를 견주려면 먼저 같은
    덮음으로 짝을 맞춰야 한다는 표시다.

    제일 큰 것들: 애니 venue_prominence -65.1%p · 만화 goods_scale
    -58.7%p(|rho| 0.3932 -> 0.1107) · 아이돌 target_breadth -29.2%p
    (0.3703 -> 0.0428) · 애니 트렌드 +40.1%p.

    거부권이 아니라 이름표다 --- 판을 안 바꾸고 기록에만 남긴다."""
    import numpy as _np
    from scipy.stats import spearmanr as _sp
    out, moved = {}, []
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        yr = data.yr.get(d)
        if yr is None:
            continue
        ok = _np.isfinite(y) & _np.isfinite(yr)
        tr, po = ok & (yr < T), ok & (yr >= T)
        if tr.sum() < 30 or po.sum() < 20:
            continue
        hits = []
        for j, a in enumerate(data.names.get(d) or []):
            c1 = float((M[tr, j] > 0).mean())
            c2 = float((M[po, j] > 0).mean())
            if max(c1, c2) <= 0.0 or abs(c2 - c1) < thr:
                continue
            rr = []
            for k in (tr, po):
                kk = k & (M[:, j] > 0)
                v = _np.nan
                if kk.sum() >= 25 and _np.std(A[kk, j]) > 1e-12:
                    v = _sp(A[kk, j], y[kk]).correlation
                rr.append(abs(float(v)) if _np.isfinite(v) else None)
            hits.append({"축": a, "학습덮음": round(c1, 3), "유보덮음": round(c2, 3),
                         "덮음차": round(c2 - c1, 3),
                         "학습|rho|": rr[0], "유보|rho|": rr[1]})
        if hits:
            hits.sort(key=lambda h: -abs(h["덮음차"]))
            out[d] = hits
            moved.append(d)
    return {"도메인": out, "이동 있음": moved,
            "왜": "덮음이 다르면 학습 |rho| 와 유보 |rho| 를 그대로 못 견준다 "
                  "--- 선택 이동을 축의 늙음으로 읽는다(노트 493). "
                  "방향은 일반 규칙이 아니다(노트 494, rho 0.092)"}


def _idol(make_extra=None, mode: str = "cut", wide: bool = True,
          placebo: int | None = None, with_wiki: bool = False,
          wiki_part: str = "both", with_trend: bool = False,
          keep_axes: tuple = (), scramble: int | None = None,
          wide_post: bool = False, wide_pop: bool = False):
    """아이돌 라벨 기준 필터를 푼 자료(노트 326).

    **자료 결정이고 점수로 고른 것이 아니다**(노트 82 · 90의 분모 규칙).
    근거는 노트 326의 분해다 --- 같은 유보 25행에서 학습만 54 -> 122 로
    늘리면 0.2199 -> 0.4728 이고 씨앗 스물이 다 양수다. 라벨 섞은 위약이
    +0.179 라 이득의 70%가 진짜 정보고, 기준별 순위 정규화는 오히려 나쁘다
    (+0.428) --- **수준 이동은 순위 채점에 안 아프다.**

    ``wide=False`` 는 같은 코드 경로로 좁은 판(한터 79행)을 만든다.
    넓힘 효과만 떼려면 이것과 견줘야 한다(``narrow_trendcal`` 관례).

    ``mode="cut"`` 은 앨범 메타 파생 축 둘을 끈다. 앨범 메타가 한터 풀에만
    긁혀 있어서 그 표시자가 한터 여부와 99.4% 같다 --- **풀의 그림자**다.
    """
    import numpy as np
    from . import idolset
    from .fixaxes import apply, apply_labels
    from .harness import Data, load as _load
    # **팝업도 같이 넓힌다**(노트 357). 노트 127·132 가 계수 필터를 푼 팝업
    # (75 -> 189행 · 학습 16 -> 73)을 재고 ``자료 결정''으로 적어 놓고도
    # ``_wide`` 라는 **다른 코드 경로**에 뒀다. 챔피언은 ``_idol`` 을 타므로
    # 열두 노트가 넘도록 좁은 팝업으로 돌고 있었다 --- 노트 346 이 아이돌
    # 넓힘에서 잡은 것과 같은 모양이다(``쟀다''와 ``쓴다''는 다르다).
    #
    # 두 넓힘이 한 경로에서 겹치게 하는 것이 이 인자다.
    from . import trendaxes as _ta
    from .popupset import build as pbuild
    _ta.set_wide(wide_pop in (True, "train", "norm"))
    _ta.set_grades(("A", "B", "C", "D", "E")
                   if wide_pop in ("grades", "norm") else ("A", "B"))
    try:
        extra = make_extra() if callable(make_extra) else make_extra
        base = apply_labels(apply(_load(extra, quiet={idolset.DOM, PRIMARY}
                                        if wide_pop else {idolset.DOM})))
        if wide_pop:
            _md = "claim" if wide_pop in (True, "train", "norm") else "now"
            _gr = (("A", "B", "C", "D", "E")
                   if wide_pop in ("grades", "norm") else ("A", "B"))
            pA, pM, py, pt, pnm, _pi = pbuild(_md, min_rho=9.9, grades=_gr)
            if wide_pop == "norm":
                # **주장 라벨을 기준 안에서 중심 맞춘다 --- 학습만**(노트 360).
                # 노트 357 이 주최자 주장이 해마다 일정하게 부풀어 있음을
                # 쟀다(일평균 log10 중앙 +0.27 · +0.44 · +0.20). 곱셈
                # 부풀림이라 **기준 안에서 중앙을 빼면 사라진다.**
                #
                # 노트 357 은 이 정규화를 ``과제를 바꾸는 결정''이라 미뤘는데
                # 그것은 **유보에 넣을 때**의 얘기다. 채점 집합을 실측만
                # 두고 학습만 손보면 과제가 안 바뀐다 --- 노트 224 가 막는
                # 것은 라벨을 다시 정의해 점수를 바꾸는 일이다.
                #
                # **중앙은 학습 행으로만 잰다**(유보를 안 본다).
                _b = np.array(_basis(len(py), _gr))
                _post = pt >= 2025.0
                _keep = np.isin(_b, ("entry", "participation"))
                py = py.astype(float).copy()
                for _u in set(_b[~_post]):
                    _m = (_b == _u) & ~_post
                    if _m.sum() >= 5:
                        py[(_b == _u)] -= float(np.median(py[_m]))
                # 유보는 실측만 --- 채점 집합이 챔피언과 같다.
                # **자르는 것은 추가 열을 붙인 뒤**(노트 360) --- 먼저
                # 자르면 ``extra`` 의 팝업 열이 길이가 안 맞아 통째로
                # 중립이 된다(노트 359 가 같은 자리에서 걸렸다).
                _sel = _keep | ~_post
            if wide_pop == "train":
                # **주장 라벨은 학습에만 넣는다**(노트 357). 실측(entry ·
                # participation)과 주장(organizer_claim)은 수준이 다르다 ---
                # 주장 중앙이 해마다 +0.27 · +0.44 · +0.20 (log10) 높다.
                # 곱셈 부풀림이라 같은 기준 안에서는 순위가 안 다치지만
                # **섞으면** 스피어만이 크기가 아니라 기준으로 줄을 세운다
                # (노트 353 아이돌과 같은 기제). 그래서 채점 집합은 실측만
                # 두고 이력만 16 -> 73 으로 늘린다.
                _keep = np.array([b in ("entry", "participation")
                                  for b in _basis(len(py), _gr)])
                _post = pt >= 2025.0
                _sel = _keep | ~_post          # 유보는 실측만 · 학습은 다
            pcols, pmsk, pnames = [pA.astype(float)], [pM.astype(float)], list(pnm)
            for c, byd in (extra or {}).items():
                v = byd.get(PRIMARY)
                if v is not None and len(v[0]) == len(pA):
                    pcols.append(np.asarray(v[0], float).reshape(-1, 1))
                    pmsk.append(np.asarray(v[1], float).reshape(-1, 1))
                else:
                    pcols.append(np.full((len(pA), 1), .5))
                    pmsk.append(np.zeros((len(pA), 1)))
                pnames.append(c)
            _pAA, _pMM = np.hstack(pcols), np.hstack(pmsk)
            if wide_pop in ("train", "norm"):
                _pAA, _pMM = _pAA[_sel], _pMM[_sel]
                py, pt = py[_sel], pt[_sel]
            d2 = dict(base.dom); n2 = dict(base.names)
            d2[PRIMARY] = (_pAA, _pMM, py, pt)
            n2[PRIMARY] = pnames
            base = Data(d2, n2)
    finally:
        _ta.set_wide(False)
        _ta.set_grades(("A", "B"))
    A, M, y, t, nm, info = idolset.build(mode, placebo, keep_axes, scramble,
                                         wide_post=wide_post)
    if not wide:                              # 좁은 판 --- 한터 79행만 남긴다
        k = np.arange(len(A)) < info["한터"]
        A, M, y, t = A[k], M[k], y[k], t[k]
    calv = idolset.cal(wide_post=wide_post)
    # **위키를 되살린다**(노트 332). 노트 326 때는 추가행이 0% 라 중립으로
    # 뒀는데, ``ingest/wiki_views.idol_items`` 를 원천 레코드에서 만들게
    # 고쳐 173건을 다 긁으니 한터 54% · 추가 39% 로 좁혀졌고 ``poolshadow``
    # 판정이 ``괜찮다`` 가 됐다. 검색 · 태그는 아직 안 긁혔으니 중립이다.
    wikv = idolset.wiki(part=wiki_part, wide_post=wide_post) if with_wiki else {}
    # 검색도 원천에서 다 긁었다(노트 333) --- 한터 96% · 추가 99%.
    trnv = idolset.trend(wide_post=wide_post) if with_trend else {}
    cols, msk, names = [A], [M], list(nm)
    for c, byd in (extra or {}).items():
        # 🔴 **`byd` 를 먼저 본다 --- 팝업과 같은 규약**(2026-08-09 · 노트 888 · 티처 #52 (나)).
        #
        # 옛 코드는 `calv`·`wikv`·`trnv` **셋만** 봤다. 팝업은 같은 함수 605-613 에서
        # `byd.get(PRIMARY)` 로 `extra` 를 읽는데 아이돌만 안 읽었다. 그래서 `extra` 로
        # 아이돌 전용 열을 넣으면 아래 `else` 로 떨어져 **0.5/마스크0 으로 조용히
        # 중립화**된다 --- 노트 887 초판이 무효가 된 근인이 정확히 이것이다
        # (위약 여섯의 도메인 Δ 가 전부 정확히 0.0000 이었던 것이 그 지문).
        #
        # 수리 전 실측(`runners/hole888.py`): 아이돌 주입 `닿는다=False ·
        # 중립화됐다=True`, 같은 주입을 팝업에 하면 `닿는다=True`. 비대칭이 값으로 찍혔다.
        #
        # ⚠ **이 수리는 열을 `Data` 에 넣을 뿐 설계행렬에 넣지 않는다.**
        # `lab/forms.py:171 AXIS_MODE='common'` 이라 `axis_order()` 는 12도메인이
        # 전부 가진 축만 돌려주고 `_feat` 는 그 목록으로만 돈다(티처 #52 C1).
        # 여기서 '아이돌 축을 살렸다' 고 말하면 887 의 실수를 반복하는 것이다.
        # 🔴 **길이 가드는 무조건이다 --- 여기가 이 수리의 핵심이다**(자가 적발).
        # 초판은 가드를 `not wide` 일 때만 걸었다가 `ValueError: size 173 vs 81` 로
        # 죽었고, 그 크래시가 티처 #52 의 실측 하나를 뒤집었다:
        #
        #   티처 C1 *"현행 extra 31열 중 아이돌 항목이 있는 열 **0개**"* → **틀렸다. 6개다.**
        #   `trend_level`·`trend_momentum`·`trend_volatility`·`wiki_level`·
        #   `wiki_momentum`·`wiki_volatility` 가 전부 아이돌 항목을 갖고 있고
        #   **길이가 81** 이다 --- 한터 79행 시절 값이다. 아이돌은 노트 332 에서
        #   원천 레코드 기반 **173행**으로 커졌는데 이 여섯은 안 따라왔다.
        #
        # 그래서 **옛 코드는 우연히 옳았다.** `byd` 를 안 읽은 덕에 낡은 81행을 피하고
        # 올바른 173행 제공자(`idolset.wiki`·`idolset.trend`)를 썼다. 가드 없이
        # `byd` 를 먼저 보게 고치면 **낡은 값으로 되돌아간다** --- 수리가 퇴행이 된다.
        #
        # 팝업 605-613 의 규약이 정확히 이것이고(`len(v[0]) == len(pA)`), 그 규약을
        # 그대로 가져온다: **길이가 맞을 때만 `byd`, 아니면 제공자.**
        v = byd.get(idolset.DOM) if isinstance(byd, dict) else None
        if v is not None and len(np.asarray(v[0], float)) != len(A):
            v = None                       # 낡았거나 다른 행 집합이다 --- 조용히 자르지 않는다
        v = v or calv.get(c) or wikv.get(c) or trnv.get(c)
        if v is not None:
            vv, oo = v
            if not wide:
                vv, oo = vv[:len(A)], oo[:len(A)]
        else:
            # 검색 · 태그는 추가행에 안 긁혀 있다. 중립으로 둔다 ---
            # 마스크 0 을 추가행에만 주면 그 표시자가 곧 기준이 된다(노트 326).
            vv, oo = np.full(len(A), 0.5), np.zeros(len(A))
        cols.append(np.asarray(vv, float).reshape(-1, 1))
        msk.append(np.asarray(oo, float).reshape(-1, 1))
        names.append(c)
    dom = dict(base.dom); nmd = dict(base.names)
    dom[idolset.DOM] = (np.hstack(cols), np.hstack(msk), y, t)
    nmd[idolset.DOM] = names
    # **축의 방향을 원 방향으로 세운다**(노트 583). 마지막에 건다 ---
    # n701·n705 가 잰 자리가 정확히 여기(``_idol`` 이 돌려주는 Data)다.
    from .fixaxes import orient as _orient
    return _orient(Data(dom, nmd))


# **원천 축 열 중 넷**(노트 348). 노트 324가 열을 묶음으로 붙여 판
# -0.0027 을 얻고 서랍에 넣었다. 노트 348이 검사 ⑤ 를 돌리니 묶음은
# 판 -0.0003(4/8)인데 **이긴 도메인의 축만 남기면 +0.0082(8/8)** 이고
# 붙이니 판 +0.0068(**12/12**) · 펀딩 +0.0521 · 모바일 +0.0135 이다.
# **묶음으로는 못 쓰고 갈라면 쓴다** --- 지는 여섯이 이기는 넷을 덮고
# 있었다(노트 339의 잡음 축 값).
RAW_KEEP = ("fund_maxprice", "mob_advisory", "mob_ngenre", "mob_nlang")

# **달력은 이기는 두 도메인에만 남긴다**(노트 349). 노트 342의 지도가
# 달력이 펀딩 +0.0939(8/8) · 웹툰 +0.0474(8/8) 둘만 이기고 모바일
# -0.0065(1/8) · 팝업 -0.0337(1/8) · 도서 -0.0235(2/8) 은 진다고 했다.
# 축 여섯 x 도메인 아홉을 빼니 판 +0.0044(**11/12**) --- 도서 +0.0398 ·
# 아이돌 +0.0360 · 팝업 +0.0269. 제일 나쁜 애니가 -0.0075(t~1.25)로
# 문턱 안이다.
#
# **노트 341 은 위키를 진 두 도메인에서 빼고 안 올랐다**(+0.0009 · 7/12).
# 그때는 도메인 둘 x 축 셋이었고 이번은 아홉 x 여섯이다 --- **빼기도 값이
# 있는데 충분히 커야 보인다.**
CAL_KEEP = ("펀딩", "웹툰")

# **위키도 진 데서 뺀다**(노트 350). 노트 342의 지도에서 양수가 3/8 이하인
# 넷 --- 웹툰(3/8) · 팝업(3/8) · 애니(0/8) · 시장팝업(0/8). 축 셋 x 도메인
# 넷 = 열두 칸이다.
#
# 노트 341이 같은 일을 둘(시장팝업 · 애니)에만 하고 +0.0009(7/12)를 얻어
# ``빼기는 값이 없다''로 읽었다. 넷으로 늘리니 **판 +0.0033(10/12)** 이고
# 시장팝업이 +0.0557(10/12) 오른다 --- 지도가 -0.0873(0/8)이라 적은 그
# 자리다. **노트 349의 교훈(크게 빼라)이 두 번째로 맞았다.**
#
# **도서를 하나 더 뺀다**(노트 351). 노트 342의 지도는 판이 여덟 번 바뀐
# 뒤라 낡았고, 다시 그리니 위키에서 진 자리는 도서 하나뿐이었다
# (-0.0160, **1/8**). 실제로 빼니 도서 +0.0124(9/12)로 지도대로다.
WIKI_DROP = ("웹툰", "팝업", "애니", "시장팝업", "도서")

# **검색은 팝업에서만 뺀다**(노트 351). 다시 그린 지도에서 검색이 진
# 자리는 팝업 하나(-0.0218, **0/8**)이고 나머지 아홉은 이기거나 못
# 가른다. 노트 342 때는 팝업이 -0.0007(4/8)로 못 가르는 자리였다 ---
# 판이 바뀌면 지도도 바뀐다.
#
# **판은 안 움직인다**(+0.0002, 7/12). 팝업 가중이 59/2,675 = 2.2%라
# 지도 차 0.0218 을 곱하면 +0.0005 --- 판 SD 0.0031 의 6분의 1이다.
# 그런데 **팝업 자체는 +0.0168(11/12)** 이고 팝업이 대표 수치다
# (``harness.PRIMARY``). 판이 안 내려가면서 대표가 오르므로 넣는다.
TREND_DROP = ("팝업",)

# **``zero_is_data`` 를 도메인마다 다르게 준다**(노트 564).
#
# 노트 306 이 위키에서 ``물어봤는데 빈 것''을 관측-$0$ 으로 세면 마스크가
# 사후가 된다는 것을 보이고 ``zero_is_data=False`` 로 정정했는데, **검색은
# 명시적으로 면제**했다 --- ``빈 계열을 받은 것은 수집 시점의 진짜 측정''.
# 노트 559 가 그 면제를 검색 전체로 뒤집으려다 **기각**됐다(판 $-0.0034$ ---
# 유보 관측이 $\sim$100\% 인 도메인은 이미 배포와 같아 고칠 것이 없었다).
#
# **그런데 도메인마다 뜻이 다르다.** 노트 563 이 갈랐다 ---
#
#     게임    값있음 305행(한글 제목 36\%) · **관측-0 42행(한글 100\%)**
#             영문 제목 중 관측-0 이 **0건**이다. 영문(글로벌 대작)은 긁으면
#             늘 값이 나오고, 관측-0 은 전부 한글 제목이다. 그러면 그 마스크는
#             수요가 아니라 **``한글 제목 소규모 국산인가''** 라는 도메인 안
#             하위집단 표지이고, 값 $0$(백분위 최저)으로 두면 **잘못된 크기**를
#             준다. 결측으로 두면 ``모른다''가 되어 낫다.
#     도서    값있음 97행 · 관측-0 109행 --- **둘 다 한글 100\%**. 언어로 안
#             갈리므로 관측-0 이 진짜 ``무명하다''다. 노트 560 이 도서만
#             False 로 두는 것을 **기각**했다(도서 $-0.0820$).
#
# 짝 씨앗 **40**: 판 $+0.0005$(23/40, 문다) · **날짜 통제 판 $+0.0007$
# ($0$ 밖 양수)** · 무리 안 $+0.0009$(문다) · KR $+0.0001$(문다) ·
# 앱 $-0.0006$(문다) · **게임 $+0.6459 \to +0.6597$, $+0.0138$(40/40)**
# $[+0.0123,+0.0153]$. 어떤 자도 $0$ 밖 음수가 아니다.
#
# 대조(씨앗 12): 게임 검색을 **통째로** 가리면 $-0.0587$ --- 값은 필요하고
# **관측-$0$ 만** 해롭다. 도서에서는 반대였다(둘 다 음수).
#
# 판은 안 움직인다 --- 노트 351 · 553 과 같은 모양이다.
TREND_ZERO_FALSE = ("게임",)


def _wikisub():
    w = _wiki()
    return {ax: {d: v for d, v in byd.items() if d not in WIKI_DROP}
            for ax, byd in w.items()}


def _trendsub(**kw):
    """검색 축 --- ``TREND_DROP`` 을 빼고 ``TREND_ZERO_FALSE`` 를 갈아 끼운다.

    두 번 짓는 것이 아깝지만 ``zero_is_data`` 가 ``trendaxes`` 의 전역이라
    도메인마다 다르게 주려면 이 길뿐이다(노트 564). 갈아 끼우는 도메인이
    비면 두 번째 빌드를 아예 안 한다.
    """
    t = _trend(**kw)
    if TREND_ZERO_FALSE and kw.get("zero_is_data", True):
        kw2 = dict(kw); kw2["zero_is_data"] = False
        tf = _trend(**kw2)
        for ax in t:
            for d in TREND_ZERO_FALSE:
                if d in tf.get(ax, {}):
                    t[ax][d] = tf[ax][d]
    return {ax: {d: v for d, v in byd.items() if d not in TREND_DROP}
            for ax, byd in t.items()}


def _calsub():
    c = _cal()
    return {ax: {d: v for d, v in byd.items() if d in CAL_KEEP}
            for ax, byd in c.items()}


def _rawsub():
    from .rawaxes import build
    r = build()
    return {k: v for k, v in r.items() if k in RAW_KEEP}


def _gen():
    """갈래 축(노트 419) --- 도메인 사이에서 **눈금을 공유하는** 범주."""
    from .genaxes import build
    return build()


def _grp():
    from .grpaxes import build
    return build()


def _cal():
    from .calaxes import build
    return build()


def _rec():
    """레코드에 있는데 축으로 안 쓰인 필드(노트 239) --- 지금은 웹툰 태그 수."""
    from .recaxes import build
    return build()


def _tag():
    """태그 **내용** 축(노트 255) --- 웹툰 큐레이션 태그의 SVD 성분 둘.

    수(``target_breadth``)는 이미 판에 있고 이것은 내용이다. 사후 표지
    (완결 · 각색)를 걸러내고 라벨을 한 번도 안 보고 만든다."""
    from .tagaxes import build
    return build()


def _fund():
    """펀딩 전용 범주 축(노트 309) --- 채택 검사 셋을 다 통과한 첫 축."""
    from .fundaxes import build
    return build()


def _anime():
    """애니 전용 매체 축(노트 321) --- 선별기가 전 도메인을 훑어 찾은 것."""
    from .animeaxes import build
    return build()


def _raw():
    """원천 레코드에서 캐낸 전용 축 열(노트 324)."""
    from .rawaxes import build
    return build()


def _mkt():
    """시장팝업 **전용** 축 --- 범주(노트 285).

    노트 283이 잰 제일 센 신호(크루스칼 H=29.4)인데 노트 284가 도메인을
    열면서 안 넣었다. 학습 101행이라 청력 문턱 22 를 넘으므로 전용 이름이
    실제로 일할 수 있다."""
    from .mktaxes import build
    return build()


def _pop():
    """팝업 **전용** 축(노트 276) --- 프로젝트 레코드의 파생 열 다섯.

    경쟁 열 넷이 서로 0.85~1.00 으로 겹쳐(500m 과 1km 은 정확히 1.000)
    하나만 쓴다. 판은 이 축들을 못 본다 --- 노트 274가 팝업에 대해 잰
    문턱이 도메인 안 $\\Delta\\rho=0.435$ 다. 노트 275의 배포 규칙으로
    판정한다."""
    from .popaxes import build
    return build()


def _wiki(zero_is_data: bool = False, cat_check: bool = True, thin="peak"):
    """위키 축.

    ``cat_check`` 는 기본으로 켠다(노트 179) --- 문서 분류가 도메인과 안
    맞으면 결측으로 돌린다(웹툰 ``해귀''가 임진왜란 문서에 붙어 있던 것
    따위). 판은 안 움직이지만($-$0.0001 · $t{=}{-}0.02$) 배포를 위해 켠다.

    **``zero_is_data`` 기본값을 True 에서 False 로 바꿨다**(노트 306). 이것은
    개선이 아니라 **정정**이다. ``wikiaxes._read`` 는 문서를 못 찾으면 결측,
    찾으면 관측으로 두는데 ``zero_is_data=True`` 에서는 창이 비어도(n=0)
    값 0.0 으로 관측이 선다. 그러면 **마스크 = 긁은 시점(2026)에 위키 문서를
    찾았나** 이고 그것은 **사후**다 --- 2025년에 나온 게임이 2026년까지
    위키 문서를 갖게 되는 것은 그 게임이 어떻게 됐는지의 결과다.

    잰 것: 표시자와 라벨의 상관이 게임 유보 $+$0.397 · 애니 학습 $+$0.301 ·
    유보 $+$0.243 이고 연도 탓이 아니다. 그리고 **사전 창 조회수가 둘 다
    0 인데 문서 유무만 다른 두 무리**의 라벨이 갈린다(게임 유보 7.643 대
    9.087 · $p{=}0.0008$, 여덟 칸 중 여섯이 $p{<}0.01$). 출시 전 관심이
    같은데 라벨이 갈리므로 사전 정보일 수 없다.

    ``False`` 로 두면 창에 조회수가 있어야 관측으로 치고, 그러려면 문서가
    **출시 전에 존재해야** 하므로 표시자가 사전이 된다. 표지가 애니 유보
    0.243$\to$0.098 · 웹툰 학습 0.221$\to$0.03 · 만화 0.126$\to-$0.011 로
    준다. 게임 유보는 0.31 로 남는데, 수선 뒤 그 표시자는 ``출시 전에 문서가
    있었고 조회수가 있었다''이므로 **진짜 사전 신호**다.

    값은 원래 깨끗했다(창이 시작일 이전 90일). 고친 것은 표시자다.
    ``provenance`` 가 ``wiki_*`` 를 PRE 로 등록해 둔 것은 **값**에 대해
    맞았고 표시자를 말하지 않았다.

    대가: 판 0.4851 $\to$ 0.4799($-$0.0052 · 짝SE 0.0036 · $t{=}{-}1.44$ ·
    문턱 0.0072, **못 가른다**). 게임 $-$0.0321 · 애니 $-$0.0249 로 표지가
    있던 자리에서만 비용이 난다. **내려가도 되돌리지 않는다** --- 배포 규칙
    (노트 275)은 개선을 위한 것이고 이것은 정정이다.

    **검색 축은 이 문제가 없다**(노트 306). 수집기가 데이터랩에 물어보고
    빈 계열을 받은 것은 수집 시점의 진짜 측정이고(창이 오픈 210일 전부터),
    마스크가 0 인 것은 그 레코드의 검색어를 아예 모른다는 뜻이다. 위키는
    문서가 없으면 물어볼 대상 자체가 없다는 점이 다르다."""

    from .wikiaxes import build
    d = build(zero_is_data=zero_is_data, cat_check=cat_check)
    return _thin(d, thin)


def _wide(make_extra=None, mode: str = "claim"):
    """팝업 계수 필터를 풀어 학습 이력을 넓힌 자료.

    **자료 결정이고 점수로 고른 것이 아니다**(노트 82 · 90의 분모 규칙).
    근거는 노트 127의 분해다 --- 분모를 원래 59건에 고정해 놓고 봐도
    +0.3688 이 +0.4495 로 오르고, 그 이득이 ``팝업이 학습 풀에 들어가서''
    생긴 것임을 확인했다(팝업을 학습에서 빼면 +0.3244 로 내린다).
    organizer_claim 라벨은 더 거칠지만 2025년 이전 이력을 16건에서 73건으로
    늘린다 --- 노트 132가 확정한 병목이 바로 그 16건이다.

    축은 채우지 않는다. 노트 127이 자동 태깅으로 채우면 팝업이 +0.4562 에서
    +0.1150 으로 무너지는 것을 봤다."""
    import numpy as np
    from . import trendaxes
    from .popupset import build as pbuild
    from .harness import Data, load as _load
    # **축을 넓은 팝업 기준으로 만든다.** 좁은 판 축을 만들어 놓고 넓힌
    # 팝업에 중립 0.5 · 표시자 0 으로 채우면 넓힌 판이 정보가 더 적어져
    # 비교가 성립하지 않는다. audit 의 팝업은 늘 75행이므로 harness.load 가
    # 길이 불일치로 중립을 넣는다 --- 팝업 열은 여기서 직접 붙인다.
    trendaxes.set_wide(mode == "claim")
    try:
        extra = make_extra() if callable(make_extra) else make_extra
        # 팝업은 아래에서 통째로 교체하므로 행 수 경고를 끈다
        base = _load(extra, quiet={PRIMARY})
        A, M, y, t, nm, info = pbuild(mode, min_rho=9.9)
        A = A.astype(float); M = M.astype(float)
        cols, msk, names = [A], [M], list(nm)
        for c, byd in (extra or {}).items():
            v = byd.get(PRIMARY)
            if v is not None and len(v[0]) == len(A):
                cols.append(np.asarray(v[0], float).reshape(-1, 1))
                msk.append(np.asarray(v[1], float).reshape(-1, 1))
            else:
                cols.append(np.full((len(A), 1), .5))
                msk.append(np.zeros((len(A), 1)))
            names.append(c)
        dom = dict(base.dom); nmd = dict(base.names)
        dom[PRIMARY] = (np.hstack(cols), np.hstack(msk), y, t)
        nmd[PRIMARY] = names
        return Data(dom, nmd)
    finally:
        trendaxes.set_wide(False)


# ``peak_ratio`` 둘은 **겹말**이다(노트 242). 가드 열일곱
# (``guards.g_dup``)이 지금 판에서 겹치는 축 쌍 열다섯을 찾았는데 전부 같은
# 모양이었다 --- ``level`` ~ ``volatility`` ~ ``peak_ratio`` 가 한 방향을 세
# 번 싣고 있다(만화 ``wiki_volatility``~``wiki_peak_ratio`` 는 rho=1.000).
#
# 그런데 **겹말이라고 다 뺄 수 있는 것은 아니다.** 파이프라인 그대로 재면:
#
#   peak_ratio 둘 뺌 (17축)   F21 +0.0007   F18 +0.0012   F23 +0.0021
#   peak+vol 넷 뺌  (15축)   F21 -0.0010   F18 -0.0055   F23 -0.0024
#   level 둘만 뺌   (17축)   안쪽 -0.0017  유보 -0.0061 (t=-2.51)
#
# ``peak_ratio`` 는 셋 다 올라가고, ``volatility`` 를 마저 빼면 **나무가**
# 무너진다(F18 t=-1.96). rho>=0.95 는 선형의 눈이라 후보를 짚을 뿐이고,
# 나무는 그 남은 5\%를 쓴다. 그래서 peak_ratio 둘만 뺀다.
#
# 근거는 겹말 구조(라벨을 안 보는 학습 구간 순위 상관)이고 유보 수는
# 확인이다 --- 축을 빼는 것도 더하는 것과 같은 설계 선택이라 유보로
# 정하면 안 된다(노트 239).
DROP_SHAPE = ("trend_peak_ratio", "trend_volatility",
              "wiki_peak_ratio", "wiki_volatility")
DROP_PEAK = ("trend_peak_ratio", "wiki_peak_ratio")


def _thin(d: dict, thin):
    """thin: False 그대로 · "peak" peak_ratio 둘만 · True 넷 다"""
    if not thin:
        return dict(d)
    drop = DROP_PEAK if thin == "peak" else DROP_SHAPE
    return {k: v for k, v in d.items() if k not in drop}


def _trend(zero_is_data: bool = True, drop_wt: bool = False, thin="peak"):
    from .trendaxes import build
    d = build(zero_is_data=zero_is_data, drop_same_platform=drop_wt)
    return _thin(d, thin)


def calendar_share(data, T: float = 2025.0) -> dict:
    """``-시작일'' 하나만으로 얻는 유보 rho --- 판이 얼마나 달력인가.

    노트 209가 판 전체에서 $+$0.2513 을 쟀고(우연 $+$0.0126), 노트 210이
    게임의 옛 라벨에서 그것이 챔피언과 동점($+$0.4938 대 $+$0.4934)임을
    보였다. 노트 211이 두 층으로 갈랐다 --- 누적 라벨(고칠 수 있다)과
    인기순 표본(못 고친다).

    **판정치가 아니라 판정치를 읽는 눈금이다.** 순위에 안 쓴다."""
    from scipy.stats import spearmanr
    num = den = 0.0
    per = {}
    for d in data.dom:
        y = data.dom[d][2]
        yr = data.yr[d]
        m = np.isfinite(y) & np.isfinite(yr) & (yr >= T)
        if m.sum() < 20 or np.std(yr[m]) < 1e-12:
            continue
        v = spearmanr(-yr[m], y[m]).statistic
        if not np.isfinite(v):
            continue
        per[d] = round(float(v), 4)
        num += float(v) * m.sum()
        den += m.sum()
    return {"판": round(num / den, 4) if den else None, "도메인별": per}


def run_tag(name: str, axes: str) -> str:
    """저장 이름에 **설정을 다 넣는다**(노트 134).

    문턱만 다른 두 실행이 같은 이름으로 저장돼 포트폴리오의 최고값이 섞였다.
    기준선 선택 하나가 팝업 rho 를 0.09 움직이는 판에서, 이름이 설정을 안
    담으면 순위표가 무엇을 비교한 표인지 알 수 없게 된다."""
    import lab.harness as _H
    t = name if axes == "base" else f"{name}@{axes}"
    if _H.MIN_TRAIN != 40:
        t += f"\u00b7t{_H.MIN_TRAIN}"
    return t


def run_one(name: str, data: Data, program: str = "P0",
            ci: bool = True, B: int = 40, axes: str = "base") -> dict:
    spec = forms.REGISTRY[name]
    tag = run_tag(name, axes)
    import lab.harness as _H
    # **팝업 빌드를 반드시 기록한다**(노트 134). 이 선택 하나가 팝업 rho 를
    # 0.09 움직이는데, 이번 판에서 잰 처치 효과 거의 전부보다 크다.
    # 기록 안 하면 나중에 무엇과 무엇을 견줬는지 알 수 없게 된다.
    build = "popupset" if axes.startswith(("wide", "narrow")) else "audit"
    # 같은 이유로 **아이돌 빌드도 기록한다**(노트 326). 라벨 기준 필터를
    # 푸느냐가 아이돌 유보 순위상관을 0.22 에서 0.47 로 움직인다.
    ibuild = ("idolset:" + ("keep" if axes == "idolwide_keep" else
                            "narrow" if axes == "idolnarrow" else "cut")
              ) if axes.startswith("idol") else "hanteo"
    cfg = {"formulation": name, "축": axes, "문턱": _H.MIN_TRAIN,
           "팝업 빌드": build, "아이돌 빌드": ibuild, "idea": spec["idea"],
           "protocols": [p for p, _ in PROTOCOLS], "ci_B": B if ci else 0,
           "null_make": bool(spec.get("null_make")),
           # 축 세트 **이름**만으로는 두 실행을 못 견준다(노트 274 · 275).
           # 이름이 같아도 열이 변하면 도메인 점수의 차가 통째로 잡음이다.
           "지문": _H.fingerprint(data),
           # **누가 빠졌는지 찍고 지나간다**(노트 401 · 402 규약). 조용한
           # 탈락 자리가 셋 있다 --- 학습 문턱(harness.py MIN_TRAIN, 아래
           # 도메인은 안 배우고 **채점은 받는다**), _score_one 의 유보
           # 20행 미만, 그리고 **predict 가 터지면 삼키는 except**. 셋 다
           # pooled 가 분모를 다시 맞춰 주므로 판은 멀쩡해 보인다.
           # 노트 402 는 팝업이 2년째 첫 자리에 걸려 있던 것을 뒤늦게
           # 찾았다. 오늘 감사는 깨끗하지만(11 중 11 채점) 잠복이지
           # 없어진 게 아니다.
           "채점 집합": _scored_census(data),
           "죽은 축": _dead_axes(data),
           "날짜 구멍": _date_hole(data),
           "칸 수": _cell_census(data),
           "나누기": _split_census(data),
           "덮음 이동": _coverage_shift(data)}
    # **판이 못 보는 성질을 판정치 옆에 적는다**(노트 278~280 규약). 거부권이
    # 아니라 이름표다 --- 승격은 안 막는다.
    try:
        from . import hearing
        cfg["청력"] = hearing.report(name, data, spec["make"])
    except Exception as e:                      # 진단이 실행을 죽이면 안 된다
        cfg["청력"] = {"오류": f"{type(e).__name__}: {e}"}
    # **이 축이 판에 새로운가**(노트 299 · 300). 청력과 같은 자리 · 같은
    # 규약 --- 거부권이 아니라 이름표다. 0 에는 "안 오른다"(정보 없음)와
    # "이미 있다"(판이 갖고 있음) 두 뜻이 있고 다음 수가 다르다.
    try:
        from . import overlap
        cfg["겹침"] = overlap.report(data, PROTOCOLS[0][1] or 2025.0)
    except Exception as e:
        cfg["겹침"] = {"한 줄": f"겹침 검사 실패: {type(e).__name__} {e}"}
    # **표시자가 값 너머로 무엇을 나르나**(노트 306 · 307). 위키 마스크가
    # "긁은 시점에 문서를 찾았나"라 사후였던 것을 손으로 잡았고, 이 검사가
    # 그 넷을 그대로 짚는다. 역시 이름표다 --- 사후인지는 자료가 어떻게
    # 만들어졌나를 알아야 정해지고 그건 사람이 안다.
    try:
        from . import marker
        cfg["표시자"] = marker.report(data, PROTOCOLS[0][1] or 2025.0)
    except Exception as e:
        cfg["표시자"] = {"한 줄": f"표시자 검사 실패: {type(e).__name__} {e}"}
    # **판이 안 쓰는 행과 견준다**(노트 326 · 327). 자료 층의 이름표라 실행마다
    # 같지만, 그래서 더 남겨야 한다 --- 풀을 넓히려는 날에 이 줄이 이미 적혀
    # 있어야 한다. 넷 중 넷이 풀 모양이었고 부호가 다음 수를 정한다.
    try:
        from . import poolshadow
        cfg["풀그림자"] = poolshadow.audit()
    except Exception as e:
        cfg["풀그림자"] = {"한 줄": f"풀 그림자 검사 실패: {type(e).__name__} {e}"}
    # **긁어 놓고 안 읽는 자료가 있나**(노트 337). 다섯 번 손으로 찾았다 ---
    # 거르는 쪽 · 긁는 쪽 둘 · 읽는 쪽 둘. 대조는 공짜다.
    try:
        from . import listaudit
        cfg["목록"] = listaudit.report()
    except Exception as e:
        cfg["목록"] = {"한 줄": f"목록 대조 실패: {type(e).__name__}: {e}"}
    store.upsert_formulation(tag, spec["status"], spec["idea"])
    with store.Run(tag, program=program, config=cfg) as r:
        r.event(f"시작 · {spec['idea']}")
        for _k in ("청력", "겹침", "표시자", "순위", "풀그림자", "목록"):
            _v = cfg.get(_k) or {}
            if isinstance(_v, dict) and _v.get("한 줄"):
                r.event(_v["한 줄"])
        got = {}
        step = 0
        for proto, T in PROTOCOLS:
            t0 = time.time()
            try:
                sc = evaluate(spec["make"], data, protocol=proto,
                              T=T or 2025.0)
            except Exception as e:
                r.event(f"{proto} 실패: {type(e).__name__} {e}", "error")
                r.event(traceback.format_exc()[-600:], "error")
                continue
            got[proto] = sc
            for tgt, v in sorted(sc.items()):
                r.score(proto, tgt, "spearman", v)
            step += 1
            r.log(step=step, **{f"{proto}_board": board(sc),
                                f"{proto}_popup": sc.get(PRIMARY, float("nan"))})
            r.event(f"{proto}: 대상 {len(sc)}개 · 평균 {board(sc):+.4f}"
                    f" · 팝업 {sc.get(PRIMARY, float('nan')):+.4f}"
                    f" · {time.time()-t0:.1f}초")

        # 가드 --- 점수를 믿을 수 있나
        try:
            grp = guards.popup_groups(wide=axes.startswith("wide"))
        except Exception:
            grp = None
        # **그늘**(노트 183) --- 축을 더하거나 뺀 판은 기본 축만 실은 판과
        # 견준다. 판이 올라도 어느 도메인이 무너지면 막는다. 기본 판
        # 자신은 견줄 것이 없으므로 건너뛴다.
        try:
            ref = None if axes == "base" else load()
        except Exception:
            ref = None
        gl = guards.check_all(spec["make"], data, got,
                              null_make=spec.get("null_make"), groups=grp,
                              ref_data=ref)
        for g in gl:
            r.guard(g["name"], g["passed"], g["detail"])
            if not g["passed"]:
                r.event(f"가드 실패: {g['name']} — {g['detail']}", "warn")

        # 팝업 구간 --- 적합이 비싸면 횟수를 줄이고 줄였다고 적는다
        lo = hi = float("nan")
        Beff = B
        if ci and got.get("deploy"):
            t1 = time.time()
            evaluate(spec["make"], data, "deploy", 2025.0, [PRIMARY])
            per = max(time.time() - t1, 1e-3)
            Beff = int(min(B, max(10, 300.0 / per)))
            if Beff < B:
                r.event(f"적합 {per:.1f}초/회 — 붓스트랩을 {B}에서 {Beff}회로 줄임",
                        "warn")
            r.event(f"팝업 붓스트랩 {Beff}회")
            base, lo, hi = bootstrap_ci(
                spec["make"], data, PRIMARY, "deploy", 2025.0, B=Beff,
                on_step=lambda i, m: (r.log(step=100 + i, ci_mean=m),
                                      r.event(f"붓스트랩 {i}/{Beff} 평균 {m:+.4f}")))
            r.score("deploy_ci", PRIMARY, "spearman", base, lo, hi)
            r.event(f"팝업 {base:+.4f}  구간 [{lo:+.4f}, {hi:+.4f}]"
                    f"  반폭 {(hi-lo)/2:.4f}")

        # 집단 보정 판 rho 를 같이 남긴다(노트 137)
        try:
            _f = guards._fit_on(spec["make"], data, 2025.0)
            _b, _bc = guards.corrected_board(_f, data, 2025.0)
        except Exception:
            _b = _bc = float("nan")
        head = got.get("deploy", {}).get(PRIMARY, float("nan"))
        pm = next((g for g in gl if g["name"] == "치환"), {})
        rp = next((g for g in gl if g["name"] == "재현"), {})
        at = next((g for g in gl if g["name"] == "귀착"), {})
        try:
            from . import lever as _L
            lv = _L.fidelity(spec["make"], data, 2025.0)
        except Exception as e:
            r.event(f"손잡이 충실도 실패: {type(e).__name__} {e}", "warn")
            lv = {}
        # **달력 몫**(노트 209 · 211). 라벨이 누적이거나 표본이 인기순이면
        # ``-시작일'' 하나만으로도 유보 순위가 상당히 맞는다 --- 게임은 옛
        # 라벨에서 그것이 +0.494 로 챔피언과 동점이었다. 판 옆에 상시로
        # 적어 두지 않으면 판을 얼마나 할인해 읽어야 하는지 매번 잊는다.
        try:
            _cs = calendar_share(data)
        except Exception as e:
            r.event(f"달력 몫 실패: {type(e).__name__} {e}", "warn")
            _cs = {}
        summary = {"headline": None if not np.isfinite(head) else float(head),
                   "board": board(got.get("deploy", {})),
                   "cal_share": _cs.get("판"),
                   "cal_share_by": _cs.get("도메인별"),
                   "z": pm.get("z"), "p": pm.get("p"),
                   "pooled": pm.get("pooled"), "null_sd": pm.get("null_sd"),
                   "board_grp": None if _bc != _bc else float(_bc),
                   "ci": [lo, hi], "guards_ok": all(g["passed"] for g in gl),
                   # **씨앗과 풀에 대한 흔들림을 순위표에 같이 싣는다**(노트 146).
                   # 순위표의 연속 격차 열둘 중 열이 씨앗 폭보다 작았다 ---
                   # 흔들림을 안 적으면 순위가 해상도를 넘어서 읽힌다.
                   "seed_span": rp.get("span"), "seed_stab": rp.get("stab"),
                   "attrib_stab": at.get("stab"),
                   # **손잡이 충실도**(노트 159). 판 rho 는 줄 세우기만 재고
                   # 개입 방향은 안 본다 --- 둘의 순위상관이 -0.87 이다.
                   "lever_top": lv.get("top"),
                   "lever_stable": lv.get("stable"),
                   "lever_stable_acc": lv.get("stable_acc"),
                   "lever_plain": lv.get("plain"),
                   "lever_weighted": lv.get("weighted"),
                   "lever_size": lv.get("size"),
                   "targets": len(got.get("deploy", {}))}
        if summary["z"] is not None and np.isfinite(summary["z"]):
            r.log(step=1, z=summary["z"], null_sd=summary["null_sd"])
        r.finish("done", summary)
        r.event("끝")
        return {"run": r.id, **summary}


def round_once(program: str = "P0", only: str | None = None, B: int = 40,
               axes: str = "base") -> None:
    data = AXES[axes]()
    nax = len(next(iter(data.names.values())))
    store.event(f"라운드 시작 · 축 세트 {axes}({nax}축) · 도메인 {len(data.dom)}"
                f" · 레코드 {sum(len(v[2]) for v in data.dom.values())}")
    names = [only] if only else list(forms.REGISTRY)
    res = {}
    for nm in names:
        if nm not in forms.REGISTRY:
            store.event(f"모르는 정식화 {nm}", "warn")
            continue
        tag = run_tag(nm, axes)
        try:
            res[tag] = run_one(nm, data, program, B=B, axes=axes)
            store.event(f"{tag}  판 {res[tag].get('pooled')}"
                        f"  가드 {'통과' if res[tag]['guards_ok'] else '실패'}")
        except Exception as e:
            store.event(f"{tag} 터짐: {type(e).__name__} {e}", "error")
    promote(res)


def rank_key(v: dict) -> float:
    """**순위는 유보 표본 위의 판 rho 다. z 는 순위가 아니라 가드다.**

    처음엔 z 로 줄을 세웠는데 F8(부스팅)이 판 rho 는 제일 낮은데(+0.3363)
    z 는 제일 높게(+4.41) 나왔다. 강하게 규제된 모형은 섞인 라벨도 못 맞추니
    귀무가 좁아지고, 그러면 z 가 커진다. z 는 ``우연보다 나은가''를 재는
    검정통계량이지 ``얼마나 잘 맞히는가''가 아니다. 둘을 섞으면 규제가 셀수록
    이기는 순위표가 된다.

    그래서 순위는 rho, z 는 통과/탈락. 다만 rho 차이가 잡음 안이면
    (대상별 짝지은 1 SE) **귀무가 좁은 쪽**을 고른다 --- 노트 125 의 교훈과
    joint 의 tau 선택에 쓴 것과 같은 규칙이다."""
    r = v.get("pooled")
    return float(r) if r is not None and np.isfinite(r) else -9.0


def _per_target(run_id: str) -> dict:
    return {r["target"]: r["value"] for r in store.q(
        "SELECT target,value FROM scores WHERE run_id=? AND split='deploy'",
        (run_id,))}


def promote(res: dict) -> None:
    """이긴 것을 챔피언으로. 가드 실패는 승격 대상이 아니다."""
    ok = {k: v for k, v in res.items()
          if v.get("guards_ok") and rank_key(v) > -9
          and (v.get("p") is None or v["p"] <= 0.05)}
    if not ok:
        store.event("승격 없음 — 가드를 통과하고 우연보다 나은 결과가 없다", "warn")
        return
    top = max(ok, key=lambda k: rank_key(ok[k]))
    per = {k: _per_target(v["run"]) for k, v in ok.items()}

    # rho 차이가 대상별 짝지은 1 SE 안이면 같다고 보고 귀무가 좁은 쪽
    tie = [top]
    for k in ok:
        if k == top:
            continue
        sh = [t for t in per[k] if t in per[top]]
        if len(sh) < 3:
            continue
        d = np.array([per[k][t] - per[top][t] for t in sh])
        se = float(d.std(ddof=1) / np.sqrt(len(d)))
        if d.mean() >= -max(se, 1e-9):
            tie.append(k)
    best = min(tie, key=lambda k: ok[k].get("null_sd") or 9.9)
    if len(tie) > 1:
        store.event(f"판 rho 가 1 SE 안에서 같은 것 {len(tie)}개 {tie}"
                    f" — 귀무가 제일 좁은 {best} 선택")

    cur = store.q("SELECT formulation,best FROM portfolio WHERE status='champion'")
    if not cur or rank_key(ok[best]) > (cur[0]["best"] or -9):
        for c in cur:
            if c["formulation"] != best:
                store.set_status(c["formulation"], "challenger")
        store.set_status(best, "champion")
        store.event(f"챔피언 → {best}  (판 rho {rank_key(ok[best]):+.4f}"
                    f" · 귀무 {ok[best].get('null_sd') or float('nan'):.4f})")
    else:
        store.event(f"챔피언 유지 {cur[0]['formulation']}"
                    f"  (도전 최고 {best} {rank_key(ok[best]):+.4f})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--form", default=None)
    ap.add_argument("--program", default="P0")
    ap.add_argument("--B", type=int, default=40)
    ap.add_argument("--axes", default="base", choices=sorted(AXES))
    ap.add_argument("--min-train", type=int, default=None,
                    help="도메인이 학습 풀에 들 최소 T 이전 건수 (기본 40)")
    a = ap.parse_args()
    if a.min_train:
        import lab.harness as _H
        _H.MIN_TRAIN = a.min_train
        store.event(f"학습 문턱 {a.min_train}")
    store.init()
    n = 1 if a.once else a.rounds
    for i in range(n):
        store.event(f"=== 라운드 {i+1}/{n} ===")
        round_once(a.program, a.form, a.B, a.axes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
