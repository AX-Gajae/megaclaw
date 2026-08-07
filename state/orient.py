"""전이 방향을 대상 라벨로 정한다 --- 노트 69의 뒤집기를 정당한 절차로 만든다.

노트 69가 문제를 규명했다. 프로크루스테스 정렬은 축의 **기하**를 맞추지 라벨과의
**방향**을 맞추지 않는다. 애니메이션은 세 공통 축이 전부 라벨과 음의 상관이라
정렬은 성공하는데 예측 부호가 뒤집혔고, 42셀 평균이 +0.3480에서 +0.1797로
무너졌다. 방향만 뒤집으면 +0.3175로 돌아온다.

그런데 노트 69는 **답을 보고** 뒤집었다. 이 프로젝트가 금지하는 바로 그것이다.
여기서는 정당한 절차로 바꾼다.

    대상 라벨 k건만 본다 → 그 k건으로 방향을 정한다 → **나머지로 평가한다**

**세 방식을 잰다.**

    셀별 부호   42개 셀이 각자 k건으로 예측의 부호를 정한다.
    도메인별 부호 대상 도메인이 들어오는 여섯 예측을 합쳐 부호 하나를 정한다.
    축 정향     **대상의 원 축을 뒤집는다.** k건으로 각 공통 축과 라벨의 순위
                상관을 보고 음수면 축을 뒤집는다. 구조적 교정이다.

앞의 둘은 사후 교정이고 셋째만 모형을 고친다. 그리고 셋째가 물리적으로 맞는
자리다 --- 노트 69가 규명한 결함이 **원 축이 반대를 가리킨다**는 것이었기 때문이다.

**성분 부호는 손댈 필요가 없다.** 인자 공간 성분에 diag(±1)을 걸면 프로크루스테스
회전이 R→RD로 흡수하고 릿지가 직교변환에 등변이라 예측이 그대로다. 뒤집어야 하는
것은 성분이 아니라 **축**이다.

**누출 차단.** 보정에 쓴 k건은 평가에서 뺀다. 라벨 탈추세도 k건 안에서만 한다
(`detrend`는 표본이 10 미만이면 그대로 돌려준다). 복제마다 평가 집합을 먼저
고정하고(가장 큰 k를 뺀 크기) 보정 k건은 나머지에서 뽑으므로 k끼리 비교된다.

사용: python3 -m state.orient
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from .audit import IX, domains
from .procrustes import COMMON, align_pair, factor_space, lam_by_overlap
from .rank_test import spearman
from .tri_domain import detrend

SEED = 20260729
KS = (0, 4, 8, 16, 24, 32, 40)
OUT = Path("data/state/orient.json")


def _sign(v: float) -> float:
    """0 이나 NaN 은 뒤집지 않는다 --- 정보가 없을 때의 기본값은 '그대로'다."""
    return -1.0 if np.isfinite(v) and v < 0 else 1.0


def spaces(doms, names, k=None):
    """도메인별 인자 공간. 대상 라벨은 여기서 안 쓴다(축 탈추세는 t만 쓴다).

    k --- 성분 수. 대상 공간과 **같은 값**을 써야 프로크루스테스가 성립한다
    (노트 91에서 대상만 k=1로 두었다가 모양이 안 맞았다)."""
    lam = lam_by_overlap(doms, names=names)
    return {x: factor_space(*v, lam=lam.get(x, 1.0), names=(names or {}).get(x),
                            k=k)
            for x, v in doms.items()}


def flip_axes(dom_tuple, nm, which):
    """원 축을 뒤집는다(값 → 1-값). 마스크가 0인 자리는 안 건드린다."""
    A, M, y, t = dom_tuple
    A = A.copy()
    for ax in which:
        if ax not in nm:
            continue
        j = nm.index(ax) if nm is not None else IX[ax]
        A[:, j] = np.where(M[:, j] > 0, 1.0 - A[:, j], A[:, j])
    return A, M, y, t


def cal_label(F, cal):
    """보정 k건 **안에서만** 탈추세한 라벨.

    전표본으로 탈추세한 `F["y"]`를 k건만 잘라 쓰면 나머지 n-k건의 정보가 새어
    든다 --- 추세 계수가 전표본에서 왔기 때문이다. 노트 35·54·64가 같은 종류의
    누수였다. 순위 상관은 단조변환에 불변이므로 표준화는 안 해도 된다."""
    return detrend(F["y_raw"][cal], F["t_raw"][cal])


def pick_flips(F, cal, yc):
    """보정 k건으로 뒤집을 공통 축을 고른다.

    인자 공간의 **원 열**(Z)과 라벨의 순위 상관을 본다. Z의 앞쪽 열이 공통 축
    순서이므로 축 이름을 그대로 쓸 수 있다."""
    out = []
    for j, ax in enumerate(F["axes"]):
        if ax not in COMMON:
            continue
        if _sign(spearman(F["Z"][cal, j], yc)) < 0:
            out.append(ax)
    return out


def curve(ks=KS, reps: int = 120, seed: int = SEED, drop=()) -> dict:
    doms, names = domains()
    for d in drop:                      # 여섯 도메인 기준선을 같은 규약으로 잰다
        doms.pop(d, None); names.pop(d, None)
    F0 = spaces(doms, names)
    kmax = max(ks)
    rng = np.random.default_rng(seed)
    acc = {k: {m: [] for m in ("cell", "dom", "axis")} for k in ks}

    for _ in range(reps):
        per = {k: {m: [] for m in ("cell", "dom", "axis")} for k in ks}
        for t in doms:
            n = len(F0[t]["y"])
            if n <= kmax + 20:
                continue
            perm = rng.permutation(n)
            ev, pool = perm[kmax:], perm[:kmax]
            y = F0[t]["y"]
            # 출처는 라벨이 다 있으므로 정향이 공짜다. 대상만 k건으로 정한다.
            base = [(s, Ridge(alpha=1.0)
                     .fit(align_pair(F0[s], F0[t])[0], F0[s]["y"])
                     .predict(F0[t]["S"]))
                    for s in doms if s != t and align_pair(F0[s], F0[t]) is not None]
            for k in ks:
                cal = pool[:k]
                yc = None if k == 0 else cal_label(F0[t], cal)
                agg = 0.0 if k == 0 else sum(spearman(p[cal], yc) for _, p in base)
                sd = _sign(agg)
                for _s, p in base:
                    sc = 1.0 if k == 0 else _sign(spearman(p[cal], yc))
                    per[k]["cell"].append(spearman(sc * p[ev], y[ev]))
                    per[k]["dom"].append(spearman(sd * p[ev], y[ev]))
                # ── 축 정향 ── 구조적 교정. 대상 인자 공간을 다시 만든다.
                if k == 0:
                    per[k]["axis"] += [spearman(p[ev], y[ev]) for _, p in base]
                    continue
                which = pick_flips(F0[t], cal, yc)
                if not which:
                    per[k]["axis"] += [spearman(p[ev], y[ev]) for _, p in base]
                    continue
                nm = names.get(t)
                Ft = factor_space(*flip_axes(doms[t], nm, which),
                                  lam=1.0, names=nm)
                for s, _p in base:
                    r = align_pair(F0[s], Ft)
                    if r is None:
                        continue
                    q = Ridge(alpha=1.0).fit(r[0], F0[s]["y"]).predict(Ft["S"])
                    per[k]["axis"].append(spearman(q[ev], y[ev]))
        for k in ks:
            for m in ("cell", "dom", "axis"):
                if per[k][m]:
                    acc[k][m].append(float(np.mean(per[k][m])))
    out = {k: {m: [round(float(np.mean(v[m])), 4),
                   round(float(np.percentile(v[m], 2.5)), 4),
                   round(float(np.percentile(v[m], 97.5)), 4)]
               for m in ("cell", "dom", "axis")} for k, v in acc.items()}
    # 복제가 씨앗을 공유하므로 k끼리 **짝지어** 뺄 수 있다(노트 44의 규약).
    out["_raw"] = acc
    return out


def run(reps: int = 120, write: bool = True) -> dict:
    r = curve(reps=reps)
    r6 = curve(ks=(0,), reps=reps, drop=("애니",))
    r6.pop("_raw", None)
    print(f"대상 라벨 k건으로 방향을 정하고 나머지로 평가한다 (복제 {reps}회)\n")
    print(f"{'k':>4}  {'셀별 부호':>10}  {'도메인별 부호':>12}  {'축 정향':>10}")
    raw = r.pop("_raw")
    for k, v in r.items():
        print(f"{k:>4}  {v['cell'][0]:+.4f}      {v['dom'][0]:+.4f}        "
              f"{v['axis'][0]:+.4f}")
    print("\n짝지은 차이 --- 보정 없음 대비 (같은 복제끼리 뺀다)")
    z0 = np.array(raw[0]["cell"])
    paired = {}
    for k in [x for x in r if x]:
        d = np.array(raw[k]["cell"]) - z0
        lo, hi = np.percentile(d, [2.5, 97.5])
        paired[k] = [round(float(d.mean()), 4), round(float(lo), 4), round(float(hi), 4)]
        print(f"  k={k:<3} Δ{d.mean():+.4f} [{lo:+.4f}, {hi:+.4f}]  "
              f"{'채택' if lo > 0 else '보류'}")
    b = r[min(r)]
    print(f"\n여섯 도메인·보정 없음 {r6[0]['cell'][0]:+.4f} "
          f"[{r6[0]['cell'][1]:+.4f}, {r6[0]['cell'][2]:+.4f}]  (같은 유보 규약)")
    print(f"일곱 도메인·보정 없음 {b['axis'][0]:+.4f}")
    for m, lab in (("cell", "셀별"), ("dom", "도메인별"), ("axis", "축 정향")):
        best = max(r, key=lambda k: r[k][m][0])
        print(f"  {lab:<8} 최선 k={best:<3} {r[best][m][0]:+.4f} "
              f"[{r[best][m][1]:+.4f}, {r[best][m][2]:+.4f}]")
    if write:
        OUT.write_text(json.dumps({"ks": list(r), "r": {str(k): v for k, v in r.items()},
                                   "six": r6[0]["cell"],
                                   "paired": {str(k): v for k, v in paired.items()}},
                                  ensure_ascii=False, indent=1))
        print(f"\n저장: {OUT}")
    return r


if __name__ == "__main__":
    run()
