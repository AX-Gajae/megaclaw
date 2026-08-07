"""진단 공용 모듈 --- 규칙이 아니라 구조로 막는다.

노트 64가 같은 종류의 오진을 셋 모았다.

    노트 52  아이돌 소속사 정규화가 없다고 했는데 본 코드엔 있었다
    노트 54  복원추출 뒤에 고유 축을 붙여 레코드 대응이 깨졌고 부호가 뒤집혔다
    노트 63  원본 미매칭 7건이라 했는데 다른 디렉터리에 있었다

세 번 다 본 파이프라인은 옳았고 급히 짠 진단 코드가 틀렸다. 원인이 하나다 ---
\\textbf{판정을 내리는 코드가 가장 검증이 약한 자리에 있다.} 본 코드는 노트마다
검정을 통과하고 다시 쓰이는데 진단 코드는 한 번 쓰고 버린다.

그래서 진단에 필요한 것을 여기 모은다. 규칙("본 코드 함수를 불러 쓴다")은
사람이 어기지만 구조는 안 어긴다.

**핵심 설계 --- 설정은 함수다.**

배선 변경, 축 끄기, 고유 축 추가를 전부 `(doms, names) -> (doms, names)` 함수로
표현한다. 그러면 `paired()`가 **복원추출을 먼저 하고 그 뒤에 두 설정을 적용**할
수 있다. 노트 54의 버그는 순서가 반대여서 생겼는데, 이 구조에서는 순서를
틀릴 방법이 없다.

사용:
    from state.audit import domains, rho, paired, cfg_mask_off

    base, names = domains()
    print(rho(base, names))
    r = paired(cfg_mask_off("게임", "venue_prominence"))
    print(r["ci"], r["p_gt0"])
"""
from __future__ import annotations

import glob
import json
from itertools import permutations
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from .procrustes import align_pair, factor_space, lam_by_overlap
from .rank_test import spearman
from .tri_domain import ALL5, load_all

IX = {a: i for i, a in enumerate(ALL5)}
SEED = 20260729

# 레코드가 흩어져 있는 모든 디렉터리. 노트 63이 한 곳만 봐서 7건을 놓쳤다.
RECORD_DIRS = ("data/records", "data/market_records", "data/idol_records",
               "data/records_draft", "data/records_incomplete", "data/records_thinbak")


def domains():
    """정본 도메인. 고유 축과 축 이름을 함께 낸다."""
    return load_all(with_names=True)


def rho(doms, names=None) -> float:
    """정본 판정치 --- 셀 평균 스피어만 순위 상관(노트 43)."""
    lam = lam_by_overlap(doms, names=names)
    F = {k: factor_space(*v, lam=lam.get(k, 1.0), names=(names or {}).get(k))
         for k, v in doms.items()}
    rs = []
    for s, t in permutations(doms, 2):
        r = align_pair(F[s], F[t])
        if r is None:
            continue
        rs.append(spearman(Ridge(alpha=1.0).fit(r[0], F[s]["y"]).predict(F[t]["S"]),
                           F[t]["y"]))
    return float(np.mean(rs)) if rs else float("nan")


def rho_ens(doms, names=None) -> float:
    """앙상블 판정치 --- 대상마다 **출처 전부를 순위 평균**한 뒤 잰다(노트 71).

    `rho()`는 셀별 전이의 평균이라 ``출처 하나로 대상 하나''를 재고, 이것은
    ``가진 것 전부로 대상 하나''를 잰다. 제품이 실제로 쓰는 것은 뒤쪽이다 ---
    노트 58의 팝업 수치도 다섯 출처를 합쳐 냈다."""
    from scipy.stats import rankdata
    lam = lam_by_overlap(doms, names=names)
    F = {k: factor_space(*v, lam=lam.get(k, 1.0), names=(names or {}).get(k))
         for k, v in doms.items()}
    rs = []
    for t in doms:
        ps = []
        for s in doms:
            if s == t:
                continue
            r = align_pair(F[s], F[t])
            if r is None:
                continue
            ps.append(Ridge(alpha=1.0).fit(r[0], F[s]["y"]).predict(F[t]["S"]))
        if not ps:
            continue
        e = np.column_stack([rankdata(p) / len(p) for p in ps]).mean(1)
        rs.append(spearman(e, F[t]["y"]))
    return float(np.mean(rs)) if rs else float("nan")


def records() -> dict:
    """모든 디렉터리의 레코드. 노트 63의 미매칭 7건이 여기서 사라진다."""
    out = {}
    for d in RECORD_DIRS:
        for f in glob.glob(f"{d}/*.json"):
            try:
                r = json.loads(Path(f).read_text())
            except (json.JSONDecodeError, OSError):
                continue
            k = r.get("record_id") or r.get("market_record_id")
            if k and k not in out:
                out[k] = r
    return out


# ── 설정 함수 ──────────────────────────────────────────────────────────
# 전부 (doms, names) -> (doms, names). 복원추출 뒤에 적용되므로 대응이 안 깨진다.

def cfg_none(doms, names):
    return doms, names


def cfg_mask_off(dom, axis):
    def f(doms, names):
        if dom not in doms:
            return doms, names
        o = dict(doms)
        A, M, y, t = doms[dom]
        M = M.copy()
        M[:, IX[axis]] = 0.0
        o[dom] = (A, M, y, t)
        return o, names
    return f


def cfg_shuffle(dom, axis, seed=0):
    """레코드 대응만 깬다(노트 53). 진단용 귀무 조건."""
    def f(doms, names):
        o = dict(doms)
        A, M, y, t = doms[dom]
        A = A.copy()
        A[:, IX[axis]] = A[:, IX[axis]][np.random.default_rng(seed).permutation(len(y))]
        o[dom] = (A, M, y, t)
        return o, names
    return f


def cfg_flip(dom, *axes):
    """축의 **방향**만 뒤집는다(값 → 1-값). 기하는 그대로고 라벨과의 부호만 바뀐다.

    노트 69가 필요로 한 설정이다. 프로크루스테스 정렬은 축의 *기하*를 맞추지
    라벨과의 *방향*을 맞추지 않는다. 방향이 반대인 도메인이 들어오면 정렬은
    성공하는데 예측 부호가 뒤집힌다 --- 이 함수가 그 진단이다."""
    def f(doms, names):
        if dom not in doms:
            return doms, names
        o = dict(doms)
        A, M, y, t = doms[dom]
        A = A.copy()
        for ax in axes:
            j = IX[ax]
            A[:, j] = np.where(M[:, j] > 0, 1.0 - A[:, j], A[:, j])
        o[dom] = (A, M, y, t)
        return o, names
    return f


def cfg_wire(dom, slot, name):
    """배선 변경. 후보 열은 **원본 순서**로 계산되므로 복원추출 인덱스를 함께
    받아 다시 뽑는다 --- 이 함수가 복원추출 뒤에 불리기 때문이다."""
    def f(doms, names):
        from .factor_search import COLS, build
        if dom not in doms:
            return doms, names
        pool = COLS[dom]()
        idx = _IDX.get(dom)
        if idx is not None:
            pool = {k: (v[0][idx], v[1][idx]) for k, v in pool.items()}
        o = dict(doms)
        o[dom] = build(dom, doms, {slot: name}, pool)
        return o, names
    return f


def cfg_drop_own(dom):
    """고유 축을 뗀다 --- 공통 다섯 슬롯만 남긴다(노트 54의 반대 방향)."""
    def f(doms, names):
        if dom not in doms:
            return doms, names
        A, M, y, t = doms[dom]
        if A.shape[1] <= len(ALL5):
            return doms, names
        o, nm = dict(doms), dict(names or {})
        o[dom] = (A[:, :len(ALL5)], M[:, :len(ALL5)], y, t)
        nm[dom] = list(ALL5)
        return o, nm
    return f


def cfg_all(*cfgs):
    """설정 여러 개를 잇는다."""
    def f(doms, names):
        for c in cfgs:
            doms, names = c(doms, names)
        return doms, names
    return f


# 복원추출 인덱스. cfg_wire 가 원본 순서 열을 다시 뽑을 때 쓴다.
_IDX: dict = {}


def _resample(doms, rng):
    """연도 층화 복원추출. **행 인덱스를 함께 낸다** --- 확장본에도 같은 인덱스를
    써야 대응이 유지된다."""
    out, idxs = {}, {}
    for k, (A, M, y, t) in doms.items():
        idx = np.arange(len(y))
        pick = []
        for v in np.unique(t[np.isfinite(t)]):
            g = idx[t == v]
            pick += list(rng.choice(g, size=len(g), replace=True))
        nan = idx[~np.isfinite(t)]
        if len(nan):
            pick += list(rng.choice(nan, size=len(nan), replace=True))
        p = np.array(sorted(pick))
        out[k] = (A[p], M[p], y[p], t[p])
        idxs[k] = p
    return out, idxs


def _set_idx(idxs):
    _IDX.clear()
    if idxs:
        _IDX.update(idxs)


def paired(cfgB, cfgA=cfg_none, B: int = 200, seed: int = SEED,
           metric=None) -> dict:
    """두 설정의 평균 ρ 차이에 짝지은 붓스트랩 구간을 붙인다.

    **복원추출을 먼저 하고 설정을 뒤에 적용한다.** 노트 54의 버그가 구조적으로
    불가능해진다."""
    base, names = domains()
    f = metric or rho
    rng = np.random.default_rng(seed)
    d = []
    _set_idx(None)
    a0 = f(*cfgA(base, names))
    b0 = f(*cfgB(base, names))
    for _ in range(B):
        rs, ix = _resample(base, rng)
        _set_idx(ix)
        try:
            x = f(*cfgA(rs, names))
            y = f(*cfgB(rs, names))
        except (np.linalg.LinAlgError, ValueError):
            continue
        if np.isfinite(x) and np.isfinite(y):
            d.append(y - x)
    _set_idx(None)
    v = np.array(d)
    lo, hi = np.percentile(v, [2.5, 97.5])
    return {"A": a0, "B": b0, "diff": b0 - a0, "ci": [float(lo), float(hi)],
            "p_gt0": float((v > 0).mean()), "reps": len(v),
            "verdict": "채택" if lo > 0 else ("악화" if hi < 0 else "보류")}


def run() -> None:
    base, names = domains()
    print(f"정본 ρ = {rho(base, names):+.4f}   "
          f"도메인 {len(base)} · 레코드 {sum(len(v[2]) for v in base.values())}")
    rec = records()
    print(f"레코드 색인 {len(rec)}건 ({len(RECORD_DIRS)}개 디렉터리)\n")
    print("자기 점검 --- 알려진 조건을 재현하는가")
    for lab, cfg in (("게임 매장축 끄기(이미 꺼짐)", cfg_mask_off("게임", "venue_prominence")),
                     ("두 번 끄기 = 한 번 끄기", cfg_all(
                         cfg_mask_off("팝업", "venue_prominence"),
                         cfg_mask_off("팝업", "venue_prominence"))),
                     ("현행 배선 재적용(항등)", cfg_wire("도서", "target_breadth", "판형(현행)")),
                     ("팝업 매장축 끄기", cfg_mask_off("팝업", "venue_prominence")),
                     ("웹툰 매장축 대응 깨기", cfg_shuffle("웹툰", "venue_prominence"))):
        r = paired(cfg, B=60)
        print(f"  {lab:<24}Δ{r['diff']:+.4f}  "
              f"[{r['ci'][0]:+.4f}, {r['ci'][1]:+.4f}]  {r['verdict']}")


if __name__ == "__main__":
    run()
