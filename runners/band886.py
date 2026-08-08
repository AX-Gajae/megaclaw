# -*- coding: utf-8 -*-
# 노트 886 갑 — **짝 Δρ 귀무 밴드 + 티처 #50 검산 3건**
#
# 라벨·자료·판 하네스에 손대지 않는다. 입력은 오직
#   · cycle_log/forward/kobis/annex7_2026-08-09.json  (동결된 두 순위 벡터)
#   · cycle_log/forward/kobis/seal_2026-08-08.json    (정본 v1 순위)
#   · data/state/kobis_axes.json                      (국적 코드 재현 — 값만, 라벨 무접촉)
# 이므로 T4 미결 22 의 '재측정 금지'에 걸리지 않는다(티처 #50 M8 우회로).
#
# 왜 필요한가. annex7 의 9/28 판정문은 "차가 **대조 밴드** 밖"이라고만 쓰는데
# 저장소의 '밴드' 넷은 전부 *단일 ρ* 의 밴드다. 짝 Δρ 의 밴드는 존재한 적이 없다.
import datetime as dt
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path("/Users/ax/world_model")
KD = ROOT / "cycle_log/forward/kobis"
A7 = KD / "annex7_2026-08-09.json"
SEAL = KD / "seal_2026-08-08.json"
NPERM = 200_000
PERM_SEED = 886
SUBSET_SEED = 1886          # 부분집합 표를 뽑을 때만 쓴다(참고용)
MG = 20
T = 2025.0
JUNK = {"전체관람가", "청소년관람불가", "예술영화", "드라마", "12세이상관람가", "15세이상관람가"}


def rho(pred_rank, y):
    """봉인 정본과 같은 자: 순위는 작을수록 좋으므로 -rank 와 y 의 spearman."""
    return float(spearmanr([-r for r in pred_rank], y)[0])


def perm_band(rn, rc, n=NPERM, seed=PERM_SEED):
    """동결된 두 순위 벡터 위에서 라벨을 순열해 Δρ = ρ_국적 − ρ_대조 의 귀무분포를 낸다.

    H0: 라벨이 두 팔 모두와 무관. 라벨의 주변분포는 순위 치환군이므로
    y = 무작위 순열(1..m) 로 충분하다(동순위 없음 가정 — 라벨은 log10 누적이라 실제로도 없다).
    """
    m = len(rn)
    a = -np.asarray(rn, float)
    b = -np.asarray(rc, float)
    az = (a - a.mean()) / a.std()
    bz = (b - b.mean()) / b.std()
    rs = np.random.default_rng(seed)
    d = np.empty(n)
    base = np.arange(1.0, m + 1)
    for i in range(n):
        y = rs.permutation(base)
        yz = (y - y.mean()) / y.std()
        d[i] = (az @ yz - bz @ yz) / m
    sd = float(d.std(ddof=1))
    return {"m": m, "표본": n, "씨앗": seed, "평균": round(float(d.mean()), 6),
            "SD": round(sd, 6), "2σ": round(2 * sd, 4),
            "97.5분위": round(float(np.quantile(d, 0.975)), 4),
            "95분위": round(float(np.quantile(d, 0.95)), 4),
            "2.5분위": round(float(np.quantile(d, 0.025)), 4)}


def main():
    a7 = json.loads(A7.read_text())
    seal = json.loads(SEAL.read_text())
    rows = a7["예측 팔(자루 평균 순위)"]
    codes = [r["code"] for r in rows]
    rn = [r["국적 팔 순위"] for r in rows]
    rc = [r["대조 순위"] for r in rows]
    v1 = {w["code"]: w["예측 순위"] for w in seal["작품"]}

    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                      capture_output=True, text=True).stdout.strip(),
           "입력 sha": {"annex7": hashlib.sha256(A7.read_bytes()).hexdigest()[:12],
                      "seal": hashlib.sha256(SEAL.read_bytes()).hexdigest()[:12]}}

    # ── 검산 M5: 대조 팔 = seal v1 정본인가 ──────────────────────────
    same = sum(1 for c, r in zip(codes, rc) if v1[c] == r)
    out["검산 M5 — 대조 팔 = seal v1"] = {
        "일치 편수": f"{same}/{len(codes)}", "참": same == len(codes),
        "왜 중요한가": "일치해야 annex7 이 봉인과 **같은 세계**에서 계산됐다는 증명이 된다(annex7 이 인라인으로 안 남긴 사실)",
        "불일치 예": [{"code": c, "seal": v1[c], "annex7 대조": r}
                  for c, r in zip(codes, rc) if v1[c] != r][:5]}

    # ── 검산 M1: 학습만 코딩 == 전체 코딩의 상위 3범주 제한인가 ────────
    ax = json.loads((ROOT / "data/state/kobis_axes.json").read_text())
    ids = list(ax)
    yrs = [(ax[k].get("release_date") or "")[:4] for k in ids]
    raw = [None if (ax[k].get("국적") in JUNK) else ax[k].get("국적") for k in ids]

    def code(pool_idx, keep=None):
        c = Counter(raw[i] for i in pool_idx if raw[i] not in (None, ""))
        big = [u for u, n in c.items() if n >= MG]
        order = sorted(big, key=lambda u: -c[u])
        if keep is not None:
            order = [u for u in order if u in keep]
        pos = {u: i / max(1, len(order) - 1) for i, u in enumerate(order)}
        v = np.array([pos.get(x, 0.5) for x in raw], np.float32)
        m = np.array([1.0 if x in pos else 0.0 for x in raw], np.float32)
        return v, m, order, c

    tr = [i for i, y in enumerate(yrs) if y and int(y) < T]
    v_tr, m_tr, ord_tr, c_tr = code(tr)
    v_all, m_all, ord_all, c_all = code(range(len(raw)))
    v_top3, m_top3, ord_top3, _ = code(range(len(raw)), keep=set(ord_tr))
    out["검산 M1 — 학습만 = 전체의 상위3 제한인가"] = {
        "학습만 범주": ord_tr, "전체 범주": ord_all, "전체를 상위3으로 제한": ord_top3,
        "값 비트 동일": bool(np.array_equal(v_tr, v_top3)),
        "마스크 비트 동일": bool(np.array_equal(m_tr, m_top3)),
        "학습 카운트": {u: c_tr[u] for u in ord_all if u in c_tr},
        "전체 카운트": {u: c_all[u] for u in ord_all},
        "마스크 밖으로 밀린 행": int((m_all - m_tr).sum()),
        "해석": ("참이면 885 ⑤ 의 +0.0168 은 **전이 누출 차단이 아니라 이산화**(MIN_GROUP 이 소수 국적을 "
               "마스크 밖으로 민 효과)다 — 티처 #50 M1"),
    }

    # ── 갑① 짝 Δρ 귀무 밴드 ────────────────────────────────────────
    band30 = perm_band(rn, rc)
    out["갑① 짝 Δρ 귀무 밴드(m=30)"] = band30

    # 참고 표: 검열로 줄어든 m 에서의 밴드(9/28 에는 **생존 코드 집합으로 다시 계산**한다)
    rs = np.random.default_rng(SUBSET_SEED)
    tab = {}
    for m in (27, 25, 22, 20, 15, 12, 10):
        idx = rs.choice(len(codes), m, replace=False)
        b = perm_band([rn[i] for i in idx], [rc[i] for i in idx], n=40_000, seed=PERM_SEED + m)
        tab[str(m)] = {"2σ": b["2σ"], "97.5분위": b["97.5분위"], "SD": b["SD"]}
    out["참고 표(무작위 부분집합 · 실제로는 생존 집합으로 재계산)"] = {
        "왜 참고인가": "밴드는 **어느 30편이 살아남았는지**에 의존한다. 9/28 에는 생존 코드로 다시 돌린다(재량 0).",
        "부분집합 씨앗": SUBSET_SEED, "표": tab}

    # ── 출력(power) 정직 계산 ─────────────────────────────────────
    r_arms = float(spearmanr(rn, rc)[0])
    d_perfect_nat = rho(rn, [-x for x in rn]) - rho(rc, [-x for x in rn])
    d_perfect_ctl = rho(rn, [-x for x in rc]) - rho(rc, [-x for x in rc])
    # 도달 가능 범위: y 를 적대적으로 골라 Δρ 를 최대/최소화 (선형이므로 정렬로 최적)
    a = -np.asarray(rn, float); b = -np.asarray(rc, float)
    az = (a - a.mean()) / a.std(); bz = (b - b.mean()) / b.std()
    w = az - bz
    ysort = np.arange(1.0, len(rn) + 1)
    ysort = (ysort - ysort.mean()) / ysort.std()
    hi = float((np.sort(w) @ np.sort(ysort)) / len(rn))
    lo = float((np.sort(w) @ np.sort(ysort)[::-1]) / len(rn))
    out["갑① 출력(power) — 정직 계산"] = {
        "두 팔 순위 상관": round(r_arms, 4),
        "Δρ 도달 범위(적대적 y)": [round(lo, 4), round(hi, 4)],
        "🔴 국적 팔이 라벨을 **완벽히** 맞혔을 때의 Δρ": round(d_perfect_nat, 4),
        "대조 팔이 완벽히 맞혔을 때의 Δρ": round(d_perfect_ctl, 4),
        "밴드(2σ)": band30["2σ"],
        "🔴 완벽 예측이 밴드를 넘나": bool(d_perfect_nat > band30["2σ"]),
        "완벽 예측의 σ 배수": round(d_perfect_nat / band30["SD"], 2),
    }

    # ── 2차 통계(더 강한 짝 검정) 후보의 출력 ────────────────────────
    e_nat = np.abs(np.asarray(rn, float) - np.arange(1.0, len(rn) + 1))   # 자리표시(치환 전)
    del e_nat
    def err_stat(rn_, rc_, y_):
        y_rank = (-np.asarray(y_, float)).argsort().argsort() + 1
        en = np.abs(np.asarray(rn_, float) - y_rank)
        ec = np.abs(np.asarray(rc_, float) - y_rank)
        return float((ec - en).mean()), int((ec > en).sum()), int((ec < en).sum())

    rs2 = np.random.default_rng(PERM_SEED)
    m = len(rn)
    stats = np.empty(40_000)
    for i in range(40_000):
        y = rs2.permutation(np.arange(1.0, m + 1))
        stats[i], _, _ = err_stat(rn, rc, -y)
    sd2 = float(stats.std(ddof=1))
    perfect2, win2, lose2 = err_stat(rn, rc, [-x for x in rn])
    out["2차 후보 — 짝 순위오차 감소(평균)"] = {
        "정의": "Δ|err| = mean|r_대조 − r_라벨| − mean|r_국적 − r_라벨| (양수 = 국적 팔이 라벨에 더 가깝다)",
        "귀무 SD": round(sd2, 4), "2σ": round(2 * sd2, 4),
        "97.5분위": round(float(np.quantile(stats, 0.975)), 4),
        "🔴 국적 팔 완벽 예측 시 Δ|err|": round(perfect2, 4),
        "그때 이기는 편수/지는 편수": [win2, lose2],
        "🔴 완벽 예측이 밴드를 넘나": bool(perfect2 > 2 * sd2),
        "완벽 예측의 σ 배수": round(perfect2 / sd2, 2),
    }

    with open(ROOT / "runners/out886_band.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
