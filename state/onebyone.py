"""한 건씩 예측한다 --- 전도적 가정을 없앤다.

노트 76이 시간을 갈랐지만 가정 하나를 남겼다. \\textbf{대상의 인자 공간을 미래
레코드 전체로 만든다.} 팝업 축은 기획 단계에 정해지므로 라벨 누출은 아니지만,
쉰아홉 건을 한꺼번에 보고 주성분을 뽑는 것은 제품이 쓰이는 방식이 아니다.
제품은 기획서 \\emph{한 장}을 들고 온다.

**규약 셋을 비교한다.**

    한꺼번에   대상 인자 공간을 평가 대상 전체로 만든다(노트 76까지)
    하나 빼고  레코드 i 를 뺀 나머지로 만들고 i 를 투영한다(LOO)
    과거만으로 T 이전 대상 레코드로만 만들고 미래를 투영한다

셋째가 제품 그대로다 --- 지금까지 연 팝업으로 공간을 만들고 새 기획을 넣는다.

**투영을 제대로 한다.** 표준화 · 탈추세 · 주성분을 전부 적합 집합에서만 구하고
같은 변환을 평가 레코드에 건다. `factor_space` 는 한 집합에 대해 전부 한꺼번에
하므로 여기서는 적합/적용을 나눈 함수를 따로 쓴다 --- 규약을 베끼는 것이 아니라
같은 계산을 나눠 쓰는 것이므로 노트 64의 위험이 없도록 상수와 순서를 그대로
따라간다.

사용: python3 -m state.onebyone
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import Ridge

from .audit import domains
from .orient import spaces
from .procrustes import COMMON, K, LAM_OWN, procrustes
from .prospective import years
from .rank_test import spearman
from .tri_domain import ALL5, detrend, z

SEED = 20260729
OUT = Path("data/state/onebyone.json")


def fit_apply(A, M, y, t, fit, use, min_cov: float = 0.6, lam: float = LAM_OWN,
              names=None, k: int | None = None):
    """적합 집합 `fit` 에서 변환을 구하고 `use` 에 건다.

    `factor_space` 와 같은 순서다 --- 관측 축 고르기 → 탈추세 → 표준화 →
    고유 축 lam 축소 → 공분산 주성분. 다른 점은 평균 · 기울기 · 고유벡터를
    전부 `fit` 에서만 구한다는 것뿐이다."""
    nm = names or ALL5
    kk = k or K
    ka = [j for j in range(len(nm)) if M[fit][:, j].mean() >= min_cov]
    rows_f = fit[M[fit][:, ka].all(1)]
    rows_u = use[M[use][:, ka].all(1)]
    # 적합 집합은 축 수보다 넉넉해야 한다. 평가는 한 건이어도 된다
    # --- '한 건씩 예측'이 이 함수의 목적이기 때문이다.
    if len(rows_f) < max(12, 2 * len(ka)) or len(rows_u) < 1:
        return None
    sh = [nm.index(a) for a in COMMON if a in nm and nm.index(a) in ka]
    own = [j for j in ka if j not in sh]
    if len(sh) < 2:
        return None

    def col(j, rows, ref):
        """ref 에서 추세와 눈금을 구해 rows 에 건다."""
        vr, tr = A[ref][:, j], t[ref]
        ok = np.isfinite(tr)
        if ok.sum() >= 10:
            X = np.column_stack([np.ones(ok.sum()), tr[ok]])
            b = np.linalg.lstsq(X, vr[ok], rcond=None)[0]
            base = vr - np.where(np.isfinite(t[ref]), b[0] + b[1] * tr, 0.0)
            vv = A[rows][:, j] - np.where(np.isfinite(t[rows]),
                                          b[0] + b[1] * t[rows], 0.0)
        else:
            base, vv = vr, A[rows][:, j]
        mu, sd = base.mean(), base.std() + 1e-9
        return (vv - mu) / sd

    def block(rows):
        cols = [np.column_stack([col(j, rows, rows_f) for j in sh])]
        if own and lam > 1e-9:
            cols.append(lam * np.column_stack([col(j, rows, rows_f) for j in own]))
        return np.column_stack(cols)

    Zf, Zu = block(rows_f), block(rows_u)
    ev, V = np.linalg.eigh(np.cov(Zf, rowvar=False))
    V = V[:, ::-1][:, :kk]
    yy = z(detrend(y[rows_u], t[rows_u]))
    axes = [nm[j] for j in sh] + [nm[j] for j in own]
    return {"S": Zu @ V, "V": V, "y": yy, "axes": axes, "rows": rows_u,
            "n": len(rows_u)}


def predict(F_src, Ftgt, take: int | None = None):
    """출처들을 대상 공간에 맞춰 예측을 모은다.

    take 를 주면 **그 행 하나의 순위 백분위**를 낸다. 한 건씩 예측할 때 순위
    평균이 무너지는 것을 막는다 --- 레코드가 하나뿐이면 rankdata 가 항상 1을
    내므로 대상 집합 안에서 줄을 세울 수 없다. 그래서 적합 집합을 참조로 함께
    투영하고 그 안에서 새 레코드의 자리를 잰다. 제품이 내는 문장도 이것이다
    --- "지금까지 연 팝업 중 상위 몇 퍼센트인가"."""
    ps = []
    for s, Fs in F_src.items():
        shared = [a for a in COMMON if a in Fs["axes"] and a in Ftgt["axes"]]
        if len(shared) < 2:
            continue
        Ls = Fs["V"][[Fs["axes"].index(a) for a in shared], :]
        Lt = Ftgt["V"][[Ftgt["axes"].index(a) for a in shared], :]
        R = procrustes(Ls, Lt)
        ps.append(Ridge(alpha=1.0).fit(Fs["S"] @ R, Fs["y"]).predict(Ftgt["S"]))
    if not ps:
        return None
    R = np.column_stack([rankdata(p) / len(p) for p in ps]).mean(1)
    return R if take is None else float(R[take])


def run(tgt: str = "팝업", T: float = 2025.0, B: int = 600, write: bool = True) -> dict:
    doms, names = domains()
    F_all = spaces(doms, names)
    src = {k: v for k, v in F_all.items() if k != tgt}
    A, M, y, t = doms[tgt]
    nm = names.get(tgt)

    # 평가 집합 --- 인자 공간에 들어간 행 기준으로 미래를 고른다.
    yr_all = years(F_all[tgt])
    idx_all = np.arange(len(y))
    keep = M[:, [i for i, a in enumerate(nm or ALL5)
                 if M[:, i].mean() >= 0.6]].all(1)
    rows = idx_all[keep]
    yr = np.full(len(y), np.nan)
    yr[rows] = yr_all
    fut = rows[np.isfinite(yr[rows]) & (yr[rows] >= T)]
    past = rows[np.isfinite(yr[rows]) & (yr[rows] < T)]

    out = {"tgt": tgt, "T": T, "n_future": int(len(fut)), "n_past": int(len(past))}

    # ① 한꺼번에 --- 노트 76까지의 규약
    e = predict(src, F_all[tgt])
    pos = {r: i for i, r in enumerate(rows)}
    fi = [pos[r] for r in fut]
    out["batch"] = round(float(spearman(e[fi], F_all[tgt]["y"][fi])), 4)

    # ② 하나 빼고 --- LOO 투영. 적합 집합을 참조로 함께 투영해 그 안의 자리를 잰다.
    loo, yl = [], []
    for r in fut:
        f = np.array([x for x in rows if x != r])
        Ft = fit_apply(A, M, y, t, f, np.append(f, r), names=nm)
        if Ft is None or Ft["rows"][-1] != r:
            continue
        p = predict(src, Ft, take=len(Ft["rows"]) - 1)
        if p is None:
            continue
        loo.append(p)
        yl.append(float(F_all[tgt]["y"][pos[r]]))
    out["loo"] = round(float(spearman(np.array(loo), np.array(yl))), 4) if loo else None
    out["n_loo"] = len(loo)

    # ④ 완전 한 건씩 --- 과거로 공간을 만들고 **새 기획 하나씩** 넣는다.
    one, yo = [], []
    for r in fut:
        Ft = fit_apply(A, M, y, t, past, np.append(past, r), names=nm)
        if Ft is None or Ft["rows"][-1] != r:
            continue
        p = predict(src, Ft, take=len(Ft["rows"]) - 1)
        if p is None:
            continue
        one.append(p)
        yo.append(float(F_all[tgt]["y"][pos[r]]))
    if one:
        o, yv = np.array(one), np.array(yo)
        out["one"] = round(float(spearman(o, yv)), 4)
        rng = np.random.default_rng(SEED)
        v = [spearman(o[ix], yv[ix]) for ix in
             (rng.choice(len(o), len(o), replace=True) for _ in range(B))]
        v = [x for x in v if np.isfinite(x)]
        lo, hi = np.percentile(v, [2.5, 97.5])
        out["one_ci"] = [round(float(lo), 4), round(float(hi), 4)]
        out["n_one"] = len(one)

    # ③ 과거만으로 --- 제품 그대로
    Ft = fit_apply(A, M, y, t, past, fut, names=nm)
    if Ft is not None:
        p = predict(src, Ft)
        out["past_only"] = round(float(spearman(p, Ft["y"])), 4)
        rng = np.random.default_rng(SEED)
        v = []
        for _ in range(B):
            ix = rng.choice(len(p), len(p), replace=True)
            s = spearman(p[ix], Ft["y"][ix])
            if np.isfinite(s):
                v.append(s)
        lo, hi = np.percentile(v, [2.5, 97.5])
        out["past_only_ci"] = [round(float(lo), 4), round(float(hi), 4)]
        out["n_fit"] = int(Ft["n"])
    else:
        out["past_only"] = None

    print(f"대상 {tgt} · 시점 {T:.0f} · 미래 {out['n_future']}건 "
          f"(공간 적합용 과거 {out['n_past']}건)\n")
    print(f"  ① 한꺼번에 (노트 76)      ρ = {out['batch']:+.4f}")
    if out["loo"] is not None:
        print(f"  ② 하나 빼고 (LOO 투영)    ρ = {out['loo']:+.4f}  ({out['n_loo']}건)")
    if out["past_only"] is not None:
        print(f"  ③ 과거 공간 + 미래 묶음    ρ = {out['past_only']:+.4f}  "
              f"[{out['past_only_ci'][0]:+.4f}, {out['past_only_ci'][1]:+.4f}]")
    if out.get("one") is not None:
        print(f"  ④ 완전 한 건씩 (제품 그대로) ρ = {out['one']:+.4f}  "
              f"[{out['one_ci'][0]:+.4f}, {out['one_ci'][1]:+.4f}]  ({out['n_one']}건)")
    if write:
        prev = json.loads(OUT.read_text()) if OUT.exists() else {}
        prev[f"{tgt}_{int(T)}"] = out
        OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
        print(f"\n저장: {OUT}")
    return out


if __name__ == "__main__":
    run()
