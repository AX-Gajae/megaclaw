"""초매개변수를 **학습 구간 안에서** 고른다(노트 189).

**왜 필요했나.** 노트 187$\\sim$189 에서 열을 늘리는 처방을 여섯 가지
시도했고 전부 졌다 --- 짝 곱 · 무리 안 곱 · 3차 · 무리 사이 곱 · 무리 쌓기 ·
조건부 쪼갬. 그러다 규제를 훑어 보니 능형의 ``alpha=1.0'' 이 정식화를 쓴
날부터 한 번도 안 바뀐 기본값이었고, 그것만 고쳐도 판이 $+$0.011$\\sim$0.013
오른다. **열을 늘리는 데 여섯 번 실패하는 동안 안 건드린 숫자 하나가 있었다.**

**규약.** 유보(2025년 이후)는 한 칸도 안 본다. 학습 구간을 시간으로 다시
7 대 3 으로 갈라 앞쪽으로 적합하고 뒤쪽으로 고른다 --- 시간 분할을 안쪽에서
한 번 더 흉내 내는 것이라 노트 141의 시점 규칙과 결이 같다. 무작위 접힘이
아니라 시간 접힘인 까닭은 노트 182 가 보인 대로 축과 라벨의 관계가 시간에
시들기 때문이다.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr

from .harness import Data

ALPHAS = (0.5, 1.0, 2.0, 5.0, 20.0, 100.0, 500.0)
# 안쪽 봉우리 지수가 이보다 낮으면 고르지 않는다(노트 190). 능형 셋이
# 0.81~0.84 로 이득을 봤고 배깅 트리가 0.129 로 손해를 봤다 --- 그 사이.
PEAK_MIN = 0.5


def inner_split(data: Data, T: float = 2025.0, frac: float = 0.7):
    """학습 구간을 시간으로 7 대 3. (앞, 뒤)."""
    def sub(fn):
        dom, names, yr = {}, {}, {}
        for d in data.dom:
            A, M, y, t = data.dom[d]
            m = fn(d)
            if m.sum() < 25:
                continue
            dom[d] = (A[m], M[m], y[m], t[m])
            names[d] = data.names[d]
            yr[d] = data.yr[d][m]
        return Data(dom=dom, names=names, yr=yr)
    cut = {}
    for d in data.dom:
        y, ys = data.dom[d][2], data.yr[d]
        ok = np.isfinite(y) & np.isfinite(ys) & (ys < T)
        v = ys[ok]
        cut[d] = float(np.quantile(v, frac)) if len(v) >= 30 else T - 1.0
    base = lambda d: np.isfinite(data.dom[d][2]) & np.isfinite(data.yr[d])
    return (sub(lambda d: base(d) & (data.yr[d] < cut[d])),
            sub(lambda d: base(d) & (data.yr[d] >= cut[d]) & (data.yr[d] < T)))


def inner_score(make, tr: Data, te: Data) -> float:
    """안쪽 평가 --- 표본 수로 가중한 스피어만."""
    f = make()
    f.fit(tr)
    num = den = 0.0
    for d in te.dom:
        if d not in tr.dom:
            continue
        A, M, y, t = te.dom[d]
        try:
            p = f.predict(d, A, M, t)
        except Exception:
            continue
        m = np.isfinite(p) & np.isfinite(y)
        if m.sum() < 20 or np.std(p[m]) < 1e-12:
            continue
        num += float(spearmanr(p[m], y[m]).statistic) * m.sum()
        den += m.sum()
    return num / den if den else float("nan")


def pick(make_with, data: Data, grid=ALPHAS, T: float = 2025.0):
    """grid 를 훑어 안쪽 점수가 제일 높은 값을 돌려준다.

    ``make_with(v)`` 는 **정식화를 만드는 함수를 돌려주는** 함수여야 한다\n    --- 객체를 돌려주면 안쪽 점수가 전부 nan 이 된다(노트 189)."""
    tr, te = inner_split(data, T)
    sc = {}
    for v in grid:
        try:
            sc[v] = inner_score(make_with(v), tr, te)
        except Exception:
            sc[v] = float("nan")
    good = {k: v for k, v in sc.items() if np.isfinite(v)}
    if not good:
        return grid[0], sc
    return max(good, key=good.get), sc


def peak_index(sc: dict) -> float:
    """안쪽 곡면이 얼마나 봉우리인가(노트 190).

    ``(최고 - 중앙) / (최고 - 최저)``. 진짜 봉우리면 1 에 가깝고 평평하면
    0 에 가깝다. **평평한 곡면에서 최댓값을 고르면 잡음을 고른다.**

    쟀더니 갈렸다 --- 능형 셋이 0.81 · 0.84 · 0.81 로 전부 유보에서
    $+$0.011$\sim$0.013 을 얻었고, 배깅 트리는 \textbf{0.129} 로 $-$0.010 을
    잃었다. 트리 격자 쉰넷의 상위 열이 0.0026 안에 몰려 있고 현행 기본값은
    안쪽 32위인데 유보에서는 1위다."""
    v = [x for x in sc.values() if np.isfinite(x)]
    if len(v) < 4:
        return 0.0
    mx, md, mn = max(v), float(np.median(v)), min(v)
    return float((mx - md) / (mx - mn)) if mx > mn else 0.0


def mono_index(sc: dict, order=None) -> float:
    """1차원 격자에서 안쪽 곡선이 얼마나 단조인가(노트 194).

    **봉우리 지수의 결함을 메운다.** 봉우리 지수는 ``(최고 - 중앙) /
    (최고 - 최저)`` 라 \emph{단조} 곡선을 벌한다 --- 단조면 중앙이 대략
    가운데라 지수가 0.5 를 못 넘는다. 그런데 단조는 약한 신호가 아니라
    **강한 신호**다: ``이 방향으로 갈수록 낫다''가 격자 전체에서 일관된
    것이다.

    노트 194에서 최근 가중 $\tau$ 를 고를 때 안쪽 곡선이 0.478 $\to$ 0.507
    로 단조 상승하는데 봉우리 지수가 0.298 이었다 --- 막았으면 유보
    $+$0.0304($t{=}5.69$)를 놓쳤을 것이다.

    ``order`` 는 격자 값의 정렬 순서다. 없으면 키를 정렬해 쓴다.
    **다차원 격자에는 못 쓴다** --- 순서가 없다."""
    from scipy.stats import spearmanr
    ks = list(order or sorted(sc, key=lambda k: (isinstance(k, str), k)))
    v = [sc[k] for k in ks if np.isfinite(sc.get(k, np.nan))]
    if len(v) < 4:
        return 0.0
    r = spearmanr(range(len(v)), v).statistic
    return float(abs(r)) if np.isfinite(r) else 0.0



def stable(makers, data: Data, order=None,
           fracs=(0.60, 0.65, 0.70, 0.75, 0.80)) -> tuple:
    """안쪽 분할을 바꾸면 그 선택이 그대로인가(노트 216).

    봉우리 지수(노트 190)는 ``(최고 $-$ 중앙) $\div$ (최고 $-$ 최저)'' 라
    **상대 척도다** --- 곡면 전체가 절대적으로 평평해도 통과한다. 능형
    알파(범위 0.0062)와 감쇠 $\tau$(범위 0.0058)가 봉우리 0.63 · 0.59 로
    통과하는데 **바깥 이득이 $-$0.0002 와 $+$0.0013 뿐**이다.

    잡음 바닥을 짝 붓스트랩 $t$ 로 세워 봤는데 **그것도 안 된다** --- 같은
    안쪽 분할에서 재므로 그 분할의 잡음을 물려받아 $t$ 가 1.77 과 3.07 을
    오간다(노트 216). 판도 안 움직였다.

    되는 것은 **분할을 바꿔 보는 것**이다. 다섯 분할에서 최고가 알파는
    [1, 100, 500, 500, 2], $\tau$ 는 [없음, 8, 12, 1, 12] 로 격자 전체를
    헤맨다 --- 둘 다 최빈이 2/5 다. **고를 것이 없다는 말을 유보를 한 번도
    안 보고 할 수 있다.**

    ``makers`` 는 {격자값: 공장} 또는 {격자값: (공장, 자료변환)} 이다.
    (안정한가, 최빈값, 몇 번) 을 준다."""
    from collections import Counter
    ks = list(order or makers)
    wins = []
    for fr in fracs:
        tr, te = inner_split(data, frac=fr)
        sc = {}
        for k in ks:
            mk = makers[k]
            if isinstance(mk, tuple):
                mk, tf = mk
                sc[k] = inner_score(mk, tf(tr), te)
            else:
                sc[k] = inner_score(mk, tr, te)
        v = [sc[k] for k in ks]
        if not np.isfinite(v).any():
            continue
        wins.append(ks[int(np.nanargmax(v))])
    if not wins:
        return False, None, 0
    c = Counter(map(str, wins))
    top, n = c.most_common(1)[0]
    best = next(k for k in ks if str(k) == top)
    return (n >= STABLE_MIN), best, n


# 다섯 분할 중 셋. 격자가 일곱이면 우연히 셋이 겹칠 확률이 4\% 안이다.
STABLE_MIN = 3


def accept(sc: dict, order=None, peak_min: float = None,
           mono_min: float = 0.8, stable_ok: bool | None = None) -> tuple:
    """골라도 되나. (된다, 봉우리, 단조) --- 노트 190 · 194.

    봉우리가 서 있거나(다차원도 가능) 1차원 격자가 단조이면 통과."""
    pm = PEAK_MIN if peak_min is None else peak_min
    pk = peak_index(sc)
    mo = mono_index(sc, order) if order is not None else 0.0
    ok = (pk >= pm or mo >= mono_min)
    # **안정성**(노트 216). ``stable_ok`` 가 오면 그것도 넘어야 한다 ---
    # 봉우리 지수는 상대 척도라 평평한 곡면을 봉우리로 읽고, 그 지수 자체가
    # 분할마다 0.035 에서 0.966 까지 흔들린다.
    if ok and stable_ok is not None:
        ok = bool(stable_ok)
    return ok, pk, mo


def tuned(name: str, attr: str = "alpha", grid=ALPHAS):
    """등록용 --- 적합할 때 안쪽에서 골라 쓰는 정식화를 만든다.

    **``pick`` 은 공장을 받는다**(노트 189). 처음에 객체를 넘겼더니 안쪽
    점수가 전부 nan 이 되어 격자의 첫 값이 그냥 뽑혔고, 판이 원본과 소수
    넷째 자리까지 같게 나왔다 --- 노트 187 이 하루 전에 적은 규약(``안
    움직이면 안 닿은 것'')이 바로 그것을 잡았다."""
    from . import forms

    def make():
        o = forms.REGISTRY[name]["make"]()
        base_fit = o.fit

        def fit(train: Data):
            def factory(v):
                def g():
                    f = forms.REGISTRY[name]["make"]()
                    setattr(f, attr, v)
                    return f
                return g
            v, sc = pick(factory, train, grid)
            # **안정성**(노트 216). 봉우리 지수는 상대 척도라 평평한 곡면을
            # 봉우리로 읽는다 --- 알파 격자가 봉우리 0.63 으로 통과하는데
            # 바깥에서 -0.0002 다. 분할을 다섯 번 바꿔 최고가 셋 이상
            # 겹쳐야 고른다(다섯 분할의 최고가 1·100·500·500·2 였다).
            st_ok, st_best, st_n = stable({g: factory(g) for g in grid},
                                          train, order=list(grid))
            ok_, pk, mo = accept(sc, order=list(grid), stable_ok=st_ok)
            o.stable = (st_ok, st_best, st_n)
            o.peak, o.mono = pk, mo
            if ok_:                               # 평평하고 단조도 아니면 안 고른다
                setattr(o, attr, v)
                o.picked = v
            else:
                o.picked = None
            o.inner = sc
            base_fit(train)

        o.fit = fit
        return o
    return make
