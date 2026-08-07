"""측정 아티팩트가 확인된 축을 자료를 읽을 때 고친다(노트 207).

**첫 항목: 웹툰 \\texttt{goods\\_scale}.** 정의가 ``연재 밀도 $=$ 회차 수
$\\div$ 시작 이후 경과 주''인데, 분모의 ``지금''이 긁은 날로 고정돼 있다.
그래서 최근 작품일수록 분모가 작아진다 --- 시작 연도별 경과 주 중앙이
2018년 \\textbf{418주}에서 2026년 \\textbf{8주}로 무너지고 밀도 중앙이
0.37에서 2.69로 폭발한다. 그 결과 축이 재는 것이 ``연재 밀도''가 아니라
``얼마나 최근에 시작했나''가 된다.

**이것이 노트 182가 잡은 부호 역전의 정체다** --- 학습 $+$0.378, 유보
$-$0.283. 경과 주를 통제하면 유보 상관이 $-$0.312 에서 $-$0.031 로
사라진다(노트 207).

**고침은 회차 수 자체다.** 분모를 없앤다. 판이 F6 능형 $+$0.3709 $\\to$
$+$0.4093($t{=}5.2$), F18 배깅 $+$0.4490 $\\to$ $+$0.4645 가 된다.

**진단에 라벨을 안 썼다.** 경과 주가 무너지는 것은 시작일과 긁은 날만
있으면 보인다 --- 유보 라벨을 보고 고른 것이 아니다. 만화도 같은 정의이고
같은 붕괴(569주 $\\to$ 102주)인데 유보가 여섯 건뿐이라 판이 안 움직이고,
같이 고치면 F21 이 $-$0.001 이라 웹툰만 고친다.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from .harness import Data

D = Path("data/state")


def _pct(v: np.ndarray) -> np.ndarray:
    out = np.full(len(v), 0.5)
    m = np.isfinite(v)
    if m.sum() > 20:
        out[m] = rankdata(v[m]) / m.sum()
    return out


def _count(axf: str, rf: str, fields) -> np.ndarray:
    ax = json.loads((D / f"{axf}.json").read_text())
    rec = json.loads((D / f"{rf}.json").read_text())
    by = rec if isinstance(rec, dict) else {r["record_id"]: r for r in rec}
    ks = list(ax)
    v = np.full(len(ks), np.nan)
    for i, k in enumerate(ks):
        r = by.get(k)
        if not r:
            continue
        for f in fields:
            if r.get(f) is not None:
                v[i] = r[f]
                break
    return v


# 도메인 → (축 이름, 새 값을 만드는 함수)
FIX = {
    "웹툰": ("goods_scale",
           lambda: _count("webtoon_axes", "webtoon_records", ("n_episode",))),
}

# ── 막을 (도메인, 축) ──────────────────────────────────────────────────
#
# **웹툰 ``entry_friction`` 은 ``daily_pass`` 다**(노트 262).
# ``webtoon_axes.py:134`` 가 ``1.0 if r.get("daily_pass") else 0.0`` 이다.
# 그런데 ``daily_pass`` 는 ``finished`` 와 **+0.841**, 연도와 -0.437 이다 ---
# 연재가 끝난 뒤 붙는 과금 표지이고, 학습 70.1\% 대 유보 22.4\% 로 **같은 축이
# 두 시기에 다른 것을 뜻한다.**
#
# 노트 260이 메타 축을 만들 때 바로 이 필드를 같은 근거로 뺐다. 한쪽에서 빼고
# 다른 쪽에서 쓰는 것은 앞뒤가 안 맞는다.
#
# **가드 둘이 다 놓쳤다.** ``시점``은 ``WHEN`` 에 축 이름으로 등록된 뜻
# (``기획서 태깅``)을 보는데 도메인마다 채우는 원본 필드가 다르다 --- 나머지
# 여덟은 가격·연령이라 사전이고 웹툰만 사후다. ``한철``은 **지표**가 시기별로
# 벌어졌는지 보는데 이 축은 덮음이 두 시기 다 100\% 라 안 걸린다.
#
# 막는 값: 웹툰 -0.0557(t=-3.09) · 판 -0.0141. 노트 213의 공휴일과 같다 ---
# **점수가 내려간 게 아니라 옳아진 것이다.**
#
# **웹툰 ``goods_scale`` 도 막는다**(노트 263). 노트 208이 연재 밀도(비율)를
# 회차 수(셈꼴)로 바꾸면서 ``셈꼴은 시간을 담아도 해가 없다''고 적었는데,
# 그 문장은 **분모에 측정 시각이 든 비율**에 대한 것이었다. 셈꼴 자체도
# 연재가 이어지는 동안 쌓인다 --- ``n_episode`` 가 연도와 **-0.490** 이고
# 학습 평균 100.4 대 유보 평균 44.7(45\%)이다. 예측 시점(연재 시작)에는
# 모두가 0 이다. 노트 224가 웹툰 화 간격 축을 사후로 물린 것과 같은 집안이다.
#
# **만화 · 세계애니는 안 막는다.** 만화는 유보가 6건이라 증거가 없고(연도
# 상관 -0.002), 세계애니는 ``status == FINISHED`` 일 때만 관측이라 연도 상관이
# -0.063 이고 유보/학습 비가 81\% 다. 셋 다 막으면 판이 오히려 내려간다
# (0.4890 -> 0.4855).
#
# **시장팝업 ``entry_friction`` 은 배치를 나른다**(노트 354). 노트 354가
# ``ingest/market_axes`` 의 ``single_event`` 필터를 고쳐 MKT2 배치 44행을
# 되살렸는데, 그 배치는 ``is_free_entry``/``reservation_required`` 가
# 한 번도 안 채워져 있다 --- 표시자가 MKT 0.79 대 MKT2 **0.00** 이다.
# 그러면 ``관측됐나''가 곧 ``어느 배치인가''가 되고, 모형이 축이 아니라
# 수집 회차를 읽는다. 노트 326의 **풀 그림자**와 같은 모양이고, 노트 354의
# 사전 등록이 ``갈라지면 뺀다''고 미리 적어 둔 자리다.
# **펀딩 ``trend_*`` 셋도 배치를 나른다**(노트 379). 노트 379가 텀블벅
# 목록에서 씨앗 고정 균일 표본 2,500건을 뽑아 2025년 이후 449건을
# **유보에만** 넣었는데, 그 449건에는 트렌드 계열이 없다 --- 표시자가
# 옛 400 의 **99.5%** 대 새 449 의 **0.00** 이다. 시장팝업과 같은 모양인데
# **여기가 더 나쁘다**: 옛 배치는 목록 상위 19\% 라 배치가 라벨 수준과
# 통째로 붙어 있다(쪽수와 라벨이 -0.6944). 그러면 ``관측됐나''가 곧
# ``후원자가 많은가''가 된다.
#
# 막는 값: 펀딩 +0.4195 -> +0.3769 · 판 0.4654 -> 0.4620. 노트 213의
# 공휴일 · 노트 262의 웹툰과 같다 --- **점수가 내려간 게 아니라 옳아진
# 것이다.** 새 449건의 트렌드를 받아 오면 이 항목은 없앨 수 있다.
BLOCK = {("웹툰", "entry_friction"):
         "daily_pass --- finished 와 +0.841, 학습 70% 대 유보 22%",
         ("웹툰", "goods_scale"):
         "n_episode --- 연재 중 쌓인다, 연도와 -0.490, 유보/학습 45%",
         ("시장팝업", "entry_friction"):
         "표시자가 배치다 --- MKT 0.79 대 MKT2 0.00 (노트 354)",
         ("펀딩", "trend_level"):
         "표시자가 배치다 --- 옛 400 99.5% 대 새 449 0.00 (노트 379)",
         ("펀딩", "trend_momentum"):
         "표시자가 배치다 --- 옛 400 99.5% 대 새 449 0.00 (노트 379)",
         ("펀딩", "trend_volatility"):
         "표시자가 배치다 --- 옛 400 99.5% 대 새 449 0.00 (노트 379)"}


# ── 축의 방향을 원 방향으로 세운다 (노트 583) ────────────────────────
#
# ``data/state/axis_orient.json`` 이 **하네스 열이 뒤집혀 있는 (축, 도메인)**
# 을 적어 둔다(노트 108 채택 · 노트 160 기록). 그 파일은 두 해 동안
# ``lever.prior_of`` 라는 **진단 함수에서만** 읽혔고, 모형이 보는 열은
# 뒤집힌 채로 있었다.
#
# ``entry_friction`` 에서 그것이 **공유 뜻을 깨뜨린다**(노트 581) ---
# 하네스 열의 학습 가중 평균이 **-0.023**(사실상 0)이라 방향이 없고,
# 모형은 도메인 지시자와 **함께서만** 그 축을 쓸 수 있다. 안 본 도메인에는
# 쓸 근거가 없으므로 ``OOC_DROP`` 으로 통째로 버려 왔다.
#
# 되돌리면 원 방향 가중이 **-0.105** 로 서고, 집 밖 짝(원 방향으로 들어온다)
# 과 뜻이 맞는다. 노트 583 이 잰 값(씨앗 12):
#
#   ====================  ==========  ==========
#   자                    챔피언      되돌림+해제
#   ====================  ==========  ==========
#   판                    +0.4679     **+0.4699**
#   날짜 통제 판          +0.5051     **+0.5086**
#   KR 만화               +0.6376     **+0.6824**
#   비게임 앱             +0.2860     **+0.5038**
#   ====================  ==========  ==========
#
# **무작위로 같은 개수를 뒤집는 대조 팔은 집 밖을 무너뜨린다**
# (KR -0.0114 · 앱 -0.0195, 둘 다 0/12) --- 이득이 *뒤집기* 가 아니라
# **방향 정보**에서 온다.
#
# ``media_push`` 는 **되돌리지 않는다**. 감사(노트 581)에서 그 축은
# 하네스 열 일치율 100% · 원 방향 80% 다 --- 애니 뒤집기는 **고침**이었다.
# 그래서 이 목록은 축을 골라 받는다.
ORIENT_FIX = ("entry_friction",)


def orient(data: Data) -> Data:
    """뒤집혀 있는 열을 원 방향으로 되돌린다(노트 583).

    ``ORIENT_FIX`` 에 든 축만 건드린다. 무엇을 몇 행에서 되돌렸는지는
    ``ORIENT_HITS`` 에 남는다(노트 547 ``STALE_HITS`` 와 같은 규약)."""
    import json as _j
    ORIENT_HITS.clear()
    p = Path("data/state/axis_orient.json")
    if not p.exists():
        return data
    table = _j.loads(p.read_text())
    dom = dict(data.dom)
    for axis in ORIENT_FIX:
        for d in (table.get(axis) or []):
            if d not in dom:
                continue
            nm = list(data.names.get(d) or [])
            if axis not in nm:
                continue
            j = nm.index(axis)
            A, M, y, t = dom[d]
            ok = M[:, j] > 0
            if not ok.any():
                continue
            A2 = A.copy()
            A2[ok, j] = 1.0 - A2[ok, j]
            dom[d] = (A2, M, y, t)
            ORIENT_HITS[f"{axis}_{d}"] = int(ok.sum())
    return Data(dom=dom, names=dict(data.names), yr=dict(data.yr))


ORIENT_HITS: dict = {}


def apply(data: Data) -> Data:
    """확인된 아티팩트를 고친 자료를 돌려준다."""
    dom = dict(data.dom)
    for d, (axis, mk) in FIX.items():
        if d not in dom:
            continue
        nm = list(data.names.get(d) or [])
        if axis not in nm:
            continue
        A, M, y, t = dom[d]
        v = mk()
        if len(v) != len(A):
            continue
        A2 = A.copy()
        A2[:, nm.index(axis)] = _pct(v)
        dom[d] = (A2, M, y, t)
    for (d, axis) in BLOCK:
        if d not in dom:
            continue
        nm = list(data.names.get(d) or [])
        if axis not in nm:
            continue
        A, M, y, t = dom[d]
        M2 = M.copy()
        M2[:, nm.index(axis)] = 0.0
        dom[d] = (A, M2, y, t)
    return Data(dom=dom, names=dict(data.names), yr=dict(data.yr))


# ── 라벨 고침(노트 210) ────────────────────────────────────────────────
# **게임 라벨은 스팀 리뷰 \emph{누적} 수였다.** 레코드의 ``label\_note'' 가
# 이미 적어 뒀다 --- ``출시 후 계속 누적되므로 출시일 통제가 필수다.''
# 실제로 누적 라벨은 출시 연도와 $-$0.635 이고, 유보에서 ``$-$시작일'' 하나로
# $+$0.494 가 나오는데 챔피언이 $+$0.493 이다 --- **모형이 달력과 동점이었다.**
#
# 레코드에 출시 30일 창 리뷰(``y\_w30'')가 이미 있다. 그것으로 바꾸면 출시
# 연도와의 상관이 $-$0.045 로 사라지고, 달력 기준선이 $+$0.182(안 잘린 것)로
# 떨어지는데 모형은 $+$0.48 을 지킨다. 게임 도메인 $\rho$ 가 $+$0.4934 에서
# $+$0.5871 로 오른다.
#
# **잘린 것은 결측으로 본다.** 긁은 날 기준 30일이 안 지난 2026년 출시작
# 43건은 ``30일 리뷰''가 아니다 --- 유효한 측정이 아닌 것을 값으로 쓰지 않는다.
LABEL_FIX = {
    "게임": ("game_axes", "game_records", "y_w30", "y_w30_truncated"),
}


def _labels(axf: str, rf: str, field: str, tflag: str):
    ax = json.loads((D / f"{axf}.json").read_text())
    rec = json.loads((D / f"{rf}.json").read_text())
    by = rec if isinstance(rec, dict) else {r["record_id"]: r for r in rec}
    ks = list(ax)
    v = np.full(len(ks), np.nan)
    for i, k in enumerate(ks):
        r = by.get(k)
        if not r:
            continue
        if r.get(tflag):
            continue                      # 잘린 것은 결측
        x = r.get(field)
        if x is not None:
            v[i] = np.log1p(float(x))
    return v


def apply_labels(data: Data) -> Data:
    """확인된 라벨 오염을 고친다(노트 210)."""
    dom = dict(data.dom)
    for d, (axf, rf, field, tflag) in LABEL_FIX.items():
        if d not in dom:
            continue
        A, M, y, t = dom[d]
        v = _labels(axf, rf, field, tflag)
        if len(v) != len(y):
            continue
        dom[d] = (A, M, v, t)
    return Data(dom=dom, names=dict(data.names), yr=dict(data.yr))
