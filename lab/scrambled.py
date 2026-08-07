"""검사 다섯째 --- 이 축이 **제 섞은 쌍둥이**를 이기나(노트 340).

노트 239 이후 축 채택 검사가 넷이다.

    ① 연도를 통제한 학습 구간 상관   --- 정보가 있나
    ② 시간 조각 다섯의 부호 일치     --- 시기에 안 흔들리나
    ③ 기존 축과의 겹침               --- 새로운가
    ④ 비상수성                       --- 갈라 주나

**넷 다 학습 구간에서 축이 무엇을 아는가를 잰다.** 노트 335가 그 넷으로는
못 짚는 자리를 봤다 --- 아이돌 ``goods_scale`` 이 ①(rho +0.475 · p<1e-4)과
②(시간 조각 5/5)를 통과하는데 붙이면 유보가 -0.046 이고, **값만 섞은
위약이 -0.058 로 구별이 안 됐다.** 학습에서 아는 것이 유보에서 안 살아남은
것이다.

그리고 노트 339 · 340이 그 이유를 좁혔다. 무작위 열 하나를 판에 붙이면
판이 **-0.1262**(12/12) 내려가는데, 정작 실제 계열을 빼면 -0.007~-0.044
뿐이다. **나무는 쓸모없는 열을 그냥 안 쓴다** --- 그런데 무작위 열은
학습 잡음에 우연히 맞는 갈림을 준다. 그래서 채택의 문턱은

    "0 보다 나은가" 가 아니라 **"제 섞은 쌍둥이보다 나은가"**

다. 이 파일이 그 검사다.

**싸지 않다.** 짝지은 학습 재추출을 돌리므로 뽑기마다 적합이 둘이다 ---
여덟 뽑기면 열여섯 번이다. 그래서 다른 이름표(``hearing`` · ``overlap`` ·
``marker`` · ``ordering`` · ``poolshadow`` · ``listaudit``)처럼 매 실행에
자동으로 붙이지 않는다. **축을 붙일지 정하는 날 한 번 부른다.**
"""
from __future__ import annotations

import numpy as np

DRAWS = 8
T = 2025.0


def scramble(extra: dict, axis: str, seed: int = 0) -> dict:
    """``extra`` 의 한 축만 **관측된 값끼리 섞는다.**

    열 수 · 관측 무늬 · 결측 자리가 그대로고 정보만 없어진다. 도메인마다
    따로 섞어야 도메인 안 순위가 무너진다(판정치가 도메인 안 순위다).
    """
    out = {k: dict(v) for k, v in extra.items()}
    if axis not in out:
        return out
    rng = np.random.default_rng(seed)
    for d, (v, o) in list(out[axis].items()):
        v = np.array(v, float).copy()
        idx = np.where(np.asarray(o, float) > .5)[0]
        if len(idx) > 2:
            v[idx] = v[idx[rng.permutation(len(idx))]]
        out[axis][d] = (v.astype(np.float32), np.asarray(o, np.float32))
    return out


def _resample(data, seed):
    """학습 행만 재추출한다. **유보는 안 건드린다**(노트 329의 정정)."""
    from .harness import Data
    dom, yr = {}, {}
    for i, (k, (A, M, y, t)) in enumerate(sorted(data.dom.items())):
        v = data.yr[k]
        tr = np.where(np.isfinite(v) & (v < T) & np.isfinite(y))[0]
        te = np.where(~(np.isfinite(v) & (v < T) & np.isfinite(y)))[0]
        if len(tr) < 5:
            dom[k] = (A, M, y, t); yr[k] = v; continue
        rng = np.random.default_rng(seed * 1000 + i)
        b = rng.integers(0, len(tr), len(tr))
        idx = np.concatenate([tr[b], te])
        dom[k] = (A[idx], M[idx], y[idx], t[idx]); yr[k] = v[idx]
    return Data(dom, data.names, yr)


def test5(make_data, make_form, axis: str, targets=None,
          draws: int = DRAWS, seed: int = 0) -> dict:
    """검사 ⑤ --- 진짜 축과 섞은 축을 **같은 뽑기에서** 견준다.

    ``make_data(extra)`` 가 자료를, ``make_form()`` 이 정식화를 낸다.
    ``extra`` 는 그 축을 담은 dict 다.
    """
    from . import harness as H
    a = make_data(False)
    b = make_data(True)
    tg = targets or list(a.dom)
    real, fake = [], []
    for s in range(draws):
        real.append(H.evaluate(make_form, _resample(a, s), "deploy", T, tg))
        fake.append(H.evaluate(make_form, _resample(b, s), "deploy", T, tg))
    out = {}
    for d in tg:
        v = np.array([r.get(d, np.nan) - f.get(d, np.nan)
                      for r, f in zip(real, fake)], float)
        v = v[np.isfinite(v)]
        if len(v) < 3:
            continue
        out[d] = {"차": round(float(v.mean()), 4),
                  "SD": round(float(v.std(ddof=1)), 4),
                  "양수": f"{int((v > 0).sum())}/{len(v)}"}
    pb = np.array([a.pooled(r) - a.pooled(f) for r, f in zip(real, fake)])
    win = [d for d, o in out.items()
           if o["차"] > 0 and int(o["양수"].split("/")[0]) >= 0.75 * draws]
    return {"축": axis, "뽑기": draws, "도메인": out,
            "판": {"차": round(float(pb.mean()), 4),
                  "SD": round(float(pb.std(ddof=1)), 4),
                  "양수": f"{int((pb > 0).sum())}/{len(pb)}"},
            "이긴 도메인": win,
            "판정": ("쌍둥이를 이긴다" if pb.mean() > 0 and (pb > 0).mean() >= .75
                   else ("일부만" if win else "쌍둥이와 못 가른다")),
            "한 줄": (f"검사⑤ {axis} --- 판 {pb.mean():+.4f} "
                    f"({int((pb > 0).sum())}/{len(pb)}) · 이긴 도메인 "
                    + (", ".join(win) if win else "없음"))}
