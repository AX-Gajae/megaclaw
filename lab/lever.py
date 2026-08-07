"""손잡이 충실도 --- 축을 돌리면 모형이 옳은 방향으로 움직이나(노트 155~159).

판 $\\rho$ 는 ``줄을 잘 세우나''를 재고 이것은 ``손잡이를 돌리면 맞게
움직이나''를 잰다. 노트 155~158에서 둘이 서로 다른 것을 재고 있음이
드러났다 --- 판 순위와 자료 부호 일치의 순위상관이 $-0.87$ 이고, 달력 축은
판을 깎으면서 부호를 고친다.

**재는 법.** 유보 레코드의 무작위 절반만 축 j 를 한 칸 올리고, 그 절반이
나머지에 견주어 순위가 올랐는지 본다.

    · 모든 행을 같이 올리면 안 된다 --- 순위를 내는 정식화에서 항상 0 이다
      (노트 156에서 그것을 ``역전''으로 잘못 읽었다).
    · **크기로 가중한다** --- 노트 159에서 능형의 장소 노출 효과가
      0.002~0.006 으로 나머지의 1/10 인데 단순 부호율은 그 칸을 같은 무게로
      센다. 그래서 58\\% 와 82\\% 가 갈렸다.

사전 부호는 상식이다: 입장 마찰만 내려가야 하고 나머지 넷은 올라가야 한다.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import rankdata

from .guards import _fit_on

SHARED = ("target_breadth", "venue_prominence", "entry_friction",
          "media_push", "goods_scale")
PRIOR = {"target_breadth": +1, "venue_prominence": +1, "entry_friction": -1,
         "media_push": +1, "goods_scale": +1}


def _orient() -> dict:
    """축 방향 보정 목록(노트 160). {축: [뒤집힌 도메인]}

    **사전 부호는 원 방향 기준이다.** 하네스의 열은 여섯 도메인에서
    ``값 → 1-값'' 으로 뒤집혀 있어서(노트 108 채택), 뒤집힌 곳에서는 사전
    부호도 같이 뒤집어야 한다. 노트 155~159가 이걸 안 해서 입장 마찰을
    다섯 노트에 걸쳐 ``어느 통제로도 안 고쳐지는 축''으로 적었다."""
    import json as _j
    from pathlib import Path as _P
    p = _P("data/state/axis_orient.json")
    return _j.loads(p.read_text()) if p.exists() else {}


def prior_of(axis: str, domain: str) -> int:
    o = _orient().get(axis) or []
    return PRIOR[axis] * (-1 if domain in o else 1)
DELTA = 0.25          # 0~4 척도에서 한 칸


def _fits(make, data, T, K=3):
    out = []
    for s in range(K):
        def m(s=s):
            o = make()
            for a in ("seed", "random_state"):
                if hasattr(o, a):
                    setattr(o, a, s)
            kw = getattr(o, "kw", None)
            if isinstance(kw, dict) and "random_state" in kw:
                o.kw = {**kw, "random_state": s}
            return o
        out.append(_fit_on(m, data, T))
    return out


def step_of(v, msk) -> float:
    """그 열에서 ``한 칸''이 얼마인가(노트 169).

    처음에는 0~4 척도의 한 칸이라는 뜻으로 0.25 를 고정으로 썼다. 그런데
    이진 열(0/1)에 0.25 를 밀면 트리는 분기(대개 0.5)를 못 넘어 예측이 한
    비트도 안 변한다 --- 노트 169에서 장소 노출을 이진화했더니 효과가
    0.0132 에서 0.0010 으로 떨어졌고, 그것을 ``이진화가 축을 죽였다''로
    읽을 뻔했다. 죽은 것은 축이 아니라 섭동이었다.

    그래서 **관측된 값 사이의 중앙 간격**을 한 칸으로 본다. 이진 열이면
    1.0, 촘촘한 열이면 작다."""
    x = np.unique(v[msk > 0])
    if len(x) < 2:
        return 0.25
    return float(np.median(np.diff(x)))


def effect(f, d, A, M, t, j, rng, rep=8, raw=False, step="auto"):
    """절반만 올렸을 때 그 절반의 순위 이동. raw=True 면 draw 목록을 낸다."""
    p0 = np.asarray(f.predict(d, A, M, t), float)
    k = np.isfinite(p0)
    if k.sum() < 20:
        return None
    r0 = rankdata(p0[k]) / k.sum()
    step = step_of(A[:, j], M[:, j]) if step in ("auto", None) else float(step)
    vs = []
    for _ in range(rep):
        sel = rng.random(len(A)) < 0.5
        A2 = A.copy()
        A2[sel, j] = np.clip(A2[sel, j] + step, 0, 1)
        p1 = np.asarray(f.predict(d, A2, M, t), float)
        if not np.isfinite(p1[k]).all():
            continue
        s = sel[k]
        if s.sum() < 5 or (~s).sum() < 5:
            continue
        vs.append(float(np.mean((rankdata(p1[k]) / k.sum() - r0)[s])))
    if not vs:
        return None
    return vs if raw else float(np.mean(vs))


STEPS = (0.05, 0.10, 0.25, 0.50, None)     # None = 그 열의 관측 간격


def fidelity(make, data, T: float = 2025.0, K: int = 3, seed: int = 11,
             steps=STEPS) -> dict:
    """{plain, weighted, top, stable, ...} --- 실행마다 요약에 싣는 값.

    **걸음 불변성**(노트 170). 섭동 크기를 다섯으로 바꿔도 부호가 그대로인
    칸만 믿는다. 라벨도 사전 부호도 안 보고 매기는 표지라 순환이 아니다.
    F18 배깅에서 불변 칸의 사전 부호 정확도가 93\%(26/28)이고 흔들리는
    칸은 62\%(5/8)다 --- 31\%p 가른다. 그리고 타깃 폭 · 굿즈 규모는 두
    정식화 모두 전 칸이 불변이다."""
    F = _fits(make, data, T, K)
    rng = np.random.default_rng(seed)
    E = []
    for d in sorted(data.dom):
        nm = list(data.names.get(d) or [])
        post = np.isfinite(data.yr[d]) & (data.yr[d] >= T)
        if post.sum() < 20:
            continue
        A, M, y, t = data.slice(d, post)
        for a in SHARED:
            if a not in nm:
                continue
            j = nm.index(a)
            if M[:, j].mean() < .5:
                continue
            draws = []
            for f in F:
                v = effect(f, d, A, M, t, j, rng, raw=True)
                if v:
                    draws += v
            # 걸음 다섯에서 부호가 그대로인가
            sg = set()
            for st in steps:
                vv = [effect(f, d, A, M, t, j, rng, rep=4, step=st) for f in F]
                vv = [x for x in vv if x is not None]
                if vv:
                    sg.add(int(np.sign(np.mean(vv))))
            stab = len(sg) == 1
            if draws:
                e = float(np.mean(draws))
                se = float(np.std(draws, ddof=1) / np.sqrt(len(draws))) \
                    if len(draws) > 1 else float("inf")
                E.append((e, prior_of(a, d), d, a, se, stab))
    if not E:
        return {"plain": None, "weighted": None, "size": None, "cells": 0}
    e = np.array([x[0] for x in E])
    p = np.array([x[1] for x in E])
    se = np.array([x[4] for x in E])
    hit = np.sign(e) == p
    w = np.abs(e)
    # **분해되는 칸만 센다**(노트 162). 단순 부호율은 0.002 짜리 칸과
    # 0.06 짜리 칸을 같은 무게로 세고(노트 159), 크기 가중은 다섯 정식화를
    # 91~93% 에 몰아넣어 변별이 안 된다(노트 161). 사이 눈금 --- 효과가
    # 0 과 갈리는 칸에서만 부호를 세고, 그 칸이 몇인지도 같이 적는다.
    stb = np.array([x[5] for x in E])
    sig = np.abs(e) > 2 * se
    # **상위절반**(노트 162). 후보 다섯 중 폭(0.056) · 씨앗 순위 안정
    # (+1.000) · 판과의 반상관($-$0.866) 셋 다 제일 낫다. 단순은 작은 칸에
    # 끌려가고 크기 가중은 다섯 정식화를 0.022 폭에 몰아넣는다.
    big = w >= np.median(w)
    return {"stable": float(stb.mean()),
            "stable_acc": float(hit[stb].mean()) if stb.any() else None,
            "wobble_acc": float(hit[~stb].mean()) if (~stb).any() else None,
            "top": float(hit[big].mean()) if big.any() else None,
            "top_cells": int(big.sum()),
            "plain": float(hit.mean()),
            "weighted": float((w * hit).sum() / w.sum()),
            "size": float(w.mean()), "cells": len(E),
            "sig_share": float(sig.mean()),
            "sig_plain": float(hit[sig].mean()) if sig.any() else None,
            "sig_cells": int(sig.sum()),
            "per": {f"{x[2]}|{x[3]}": x[0] for x in E},
            "stable_per": {f"{x[2]}|{x[3]}": bool(x[5]) for x in E},
            "se": {f"{x[2]}|{x[3]}": x[4] for x in E}}
