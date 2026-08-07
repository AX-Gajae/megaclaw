"""결측 패턴 누출을 네 도메인 전부에서 기계적으로 검사한다.

노트 35에서 도서의 판형 결측이 곧 전자책 여부였고, 두 형식의 라벨이 열 배
달랐다. 축은 물리량을 재는 척하면서 매체 형식을 맞히고 있었다.

그 검사는 손으로 했다. 여기서는 기계적으로 돌린다 --- **마스크 자체가 라벨과
상관되는가**를 도메인 × 축 스무 칸에서 잰다. 세 가지를 본다.

  단독      마스크(0/1)와 탈추세 라벨의 상관. 크면 '이 축이 관측되지 않는다'는
            사실이 라벨을 말해 준다.
  마스크만  다섯 마스크만으로 라벨을 예측한다(5폴드). 축 값을 하나도 안 쓰고
            얼마나 맞히는지가 누출의 총량이다.
  조건부    축 값을 통제한 뒤 마스크가 남기는 몫. 값이 이미 담고 있는 정보가
            아니라 결측 자체가 더하는 정보다.

**팝업이 가장 의심스럽다.** 팝업 축은 사람이 기획서를 읽고 매긴다. 기획서에
안 적혀 있으면 마스크 0이 되는데, 큰 기획일수록 문서가 상세할 개연성이 있다.
그러면 '적혀 있음'이 곧 규모 신호가 된다 --- 도서 판형과 같은 병이다.

Rubin(1976)의 용어로는 결측이 MCAR이 아니라 라벨에 의존하는 경우다.

사용: python3 -m state.mask_leak
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

from .tri_domain import ALL5, KO, detrend, load_all, z

SEED = 20260728
OUT = Path("data/state/mask_leak.json")


def cv_r(X, y):
    if X.shape[1] == 0 or len(y) < 25:
        return float("nan")
    pr = np.zeros(len(y))
    for tr, te in KFold(5, shuffle=True, random_state=SEED).split(X):
        pr[te] = Ridge(alpha=1.0).fit(X[tr], y[tr]).predict(X[te])
    s = pr.std()
    return float(np.corrcoef(pr, y)[0, 1]) if s > 1e-9 else 0.0


def domain_report(A, M, y, t) -> dict:
    yy = z(detrend(y, t))
    rows = {}
    for j, a in enumerate(ALL5):
        m = M[:, j]
        if m.std() < 1e-9:                       # 전부 관측 또는 전부 결측
            rows[a] = {"rate": float(m.mean()), "r": None, "cond": None}
            continue
        r = float(np.corrcoef(z(m), yy)[0, 1])
        # 조건부 --- 관측된 것들의 축 값을 통제한 뒤 마스크가 남기는 몫.
        # 결측 행의 축 값은 관측군 평균으로 채운다(값 자체는 정보가 없다고 보는 것).
        v = A[:, j].copy().astype(float)
        v[m < .5] = v[m > .5].mean() if (m > .5).any() else 0.0
        X = np.column_stack([np.ones(len(yy)), z(detrend(v, t))])
        rm = z(m) - X @ np.linalg.lstsq(X, z(m), rcond=None)[0]
        ry = yy - X @ np.linalg.lstsq(X, yy, rcond=None)[0]
        cond = float(np.corrcoef(rm, ry)[0, 1]) if rm.std() > 1e-9 else 0.0
        rows[a] = {"rate": float(m.mean()), "r": r, "cond": cond}

    var = [j for j in range(5) if M[:, j].std() > 1e-9]
    mask_only = cv_r(np.column_stack([z(M[:, j]) for j in var]), yy) if var else float("nan")
    obs = [j for j in range(5) if M[:, j].mean() >= 0.6]
    val_only = cv_r(np.column_stack([z(detrend(A[:, j], t)) for j in obs]), yy) if obs else float("nan")
    return {"axes": rows, "mask_only": mask_only, "val_only": val_only, "n": len(yy)}


def run() -> dict:
    doms = load_all()
    out = {}
    print("=== 도메인 × 축: 마스크와 라벨의 상관 ===")
    print(f"  {'도메인':<7}{'축':<12}{'관측률':>8}{'마스크 r':>10}{'조건부':>9}")
    for k, v in doms.items():
        rep = domain_report(*v)
        out[k] = rep
        for a, d in rep["axes"].items():
            if d["r"] is None:
                continue
            flag = "  ←의심" if abs(d["r"]) >= 0.15 else ""
            print(f"  {k:<7}{KO[a]:<12}{d['rate']:>8.0%}{d['r']:>+10.3f}"
                  f"{d['cond']:>+9.3f}{flag}")
    print(f"\n=== 마스크만으로 라벨 예측 (축 값 미사용) ===")
    print(f"  {'도메인':<7}{'n':>5}{'마스크만':>10}{'축 값만':>10}{'비율':>8}")
    for k, r in out.items():
        mo, vo = r["mask_only"], r["val_only"]
        rat = mo / vo if vo and abs(vo) > 1e-6 else float("nan")
        print(f"  {k:<7}{r['n']:>5}{mo:>+10.3f}{vo:>+10.3f}{rat:>8.2f}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
