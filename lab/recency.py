"""최근 가중 --- 학습 행을 최근 쪽으로 되뽑는다(노트 194).

**왜.** 노트 182 가 웹툰의 \\texttt{goods\\_scale} 이 학습 $+$0.378 에서 유보
$-$0.283 으로 부호를 뒤집는 것을, 그리고 그 시들기가 학습 구간 안에서 이미
보이는 것을 쟀다. 노트 189$\\sim$193 에서 축을 끄거나 열을 늘리는 처방이
아홉 번 졌는데, **행에 가중을 주는 것은 안 해 봤다.**

$\\tau$ 년 감쇠로 되뽑으면 판이 크게 오른다 --- F6 능형 $+$0.3709 $\\to$
$+$0.4012($t{=}5.69$), F18 배깅 $+$0.4490 $\\to$ $+$0.4604($t{=}1.59$).
$\\tau{=}2$ 년이 제일 좋고 씨앗 sd 가 0.001 로 안정적이다.

**정식화를 안 건드린다** --- 가중 대신 되뽑기를 쓰므로 어떤 형태에도 붙는다.
"""
from __future__ import annotations

import numpy as np

from .harness import Data

TAUS = (None, 12.0, 8.0, 4.0, 2.0, 1.0)


def reweight(data: Data, tau: float | None, T: float = 2025.0,
             seed: int = 0) -> Data:
    """학습 행(``< T``)만 $e^{-(T-t)/\\tau}$ 에 비례해 되뽑는다.

    유보 행은 손대지 않는다 --- 채점 대상이므로."""
    if tau is None:
        return data
    rng = np.random.default_rng(seed)
    dom, names, yr = {}, {}, {}
    for d, (A, M, y, t) in data.dom.items():
        ys = data.yr[d]
        pre = np.isfinite(y) & np.isfinite(ys) & (ys < T)
        idx = np.flatnonzero(pre)
        if len(idx) < 20:
            dom[d], names[d], yr[d] = (A, M, y, t), data.names[d], ys
            continue
        w = np.exp(-(T - ys[idx]) / tau)
        w = w / w.sum()
        pick = rng.choice(idx, size=len(idx), replace=True, p=w)
        keep = np.concatenate([pick, np.flatnonzero(~pre)])
        dom[d] = (A[keep], M[keep], y[keep], t[keep])
        names[d], yr[d] = data.names[d], ys[keep]
    return Data(dom=dom, names=names, yr=yr)


def recent(name: str, taus=TAUS, seeds=(0, 1, 2)):
    """등록용 --- 적합할 때 안쪽에서 $\\tau$ 를 고르고 되뽑아 적합한다.

    노트 190 · 194 의 규약을 그대로 쓴다 --- 안쪽 곡면이 봉우리이거나
    단조여야 고른다. 아니면 가중 없이 간다."""
    from . import forms
    from .tune import accept, inner_split, inner_score

    def make():
        o = forms.REGISTRY[name]["make"]()
        base_fit = o.fit

        def fit(train: Data):
            tr, te = inner_split(train)
            now = {d: float(np.nanmax(tr.yr[d])) for d in tr.dom}
            sc = {}
            for tau in taus:
                vs = []
                for s in seeds[:2]:
                    d2 = (tr if tau is None else
                          _inner_reweight(tr, tau, now, s))
                    vs.append(inner_score(forms.REGISTRY[name]["make"], d2, te))
                sc[tau] = float(np.mean(vs))
            ok, pk, mo = accept(sc, order=list(taus))
            o.peak, o.mono = pk, mo
            best = max(sc, key=lambda k: sc[k] if np.isfinite(sc[k]) else -9)
            o.tau = best if ok else None
            base_fit(reweight(train, o.tau) if o.tau else train)

        o.fit = fit
        return o
    return make


def _inner_reweight(dat: Data, tau: float, now: dict, seed: int) -> Data:
    """안쪽 학습을 그 안의 '현재' 기준으로 되뽑는다."""
    rng = np.random.default_rng(seed)
    dom, names, yr = {}, {}, {}
    for d, (A, M, y, t) in dat.dom.items():
        ys = dat.yr[d]
        idx = np.flatnonzero(np.isfinite(y) & np.isfinite(ys))
        if len(idx) < 20:
            dom[d], names[d], yr[d] = (A, M, y, t), dat.names[d], ys
            continue
        w = np.exp(-(now.get(d, float(np.nanmax(ys))) - ys[idx]) / tau)
        w = w / w.sum()
        pick = rng.choice(idx, size=len(idx), replace=True, p=w)
        dom[d] = (A[pick], M[pick], y[pick], t[pick])
        names[d], yr[d] = dat.names[d], ys[pick]
    return Data(dom=dom, names=names, yr=yr)
