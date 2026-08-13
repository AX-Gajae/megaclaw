# -*- coding: utf-8 -*-
"""노트 959 [판정] — 🔴 **D3 을 다시 결정한다. 958 의 「못 가른다」는 판정이 아니라 동전 던지기였다.**

사전등록 `docs/prereg_959_reach.md` §1-B · §6 D-B · §7 (커밋 `4212af9ab` · **측정 전**).
티처 #97 **F1** 처방 ⓐⓑⓒ.

**무엇이 문제였나.** 958 의 `within_boot` 은 재표집마다 `within_stat(..., n_min)` 을
**다시** 부른다. 도서 20 · 모바일 24 · 웹툰 24 · 팝업 24 가 문턱 20 **바로 위**에 앉아 있어서
묶음 집합이 재표집마다 **4~8 로 출렁인다** — 🔴 **추정량 자체가 매 재표집마다 바뀐다.**
그러면 SE 는 「그 추정량의 표집 변동」이 아니라 **두 잡음의 합**이다.

**두 설계를 이름으로 가른다**(사전등록 §7).
  · **㉮ 재적용**       재표집 표본 위에서 묶음을 **다시 고른다**(958 이 쓴 것)
  · **㉯ 원표본 조건부**  🔴 **정본** — 원표본에서 뽑힌 묶음 집합을 **고정**한다

**그리고 씨앗 하나를 안 싣는다** — 씨앗 24개를 돌려 **「T 를 넘는 씨앗 비율」**을 낸다.
사전등록 D-B: 비율이 5%~95% 사이면 🔴 **판정을 내지 않고 구간만 싣는다**.

**곁들이(§1-C · 티처 #97 T4)**: 팔 B 의 칸막이를 「도메인」 말고 **둘 더** 대서
안쪽 몫 43.6246% 가 얼마나 흔들리는지 낸다. 칸막이 정의는 사전등록 §6 에 못 박았다.

🔴 **입력은 얼린 957 의 것**(`data/frozen/957_inputs/`). **959 가 새로 받은 표는 여기 안 쓴다**
— 두 절의 분모가 다르다(조항 60).
🔴 **이 러너는 958 의 코드를 안 부른다**(`within958.py` 는 가지에만 있다). 같은 자를 **다시 구현**하고
**958 의 수를 소수 여섯 자리까지 재현하는지**를 배선 검사로 삼는다.

    python3 runners/d3_959.py
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
np.seterr(all="ignore")

import runners.layers957 as L                                   # noqa: E402

FROZEN = ROOT / "data/frozen/957_inputs"
OUT = ROOT / "runners/out959_d3.json"

# 얼린 입력으로 갈아 끼운다 — 958 과 같은 blob
L.WIKI = FROZEN / "wiki_daily"
L.ATT = FROZEN / "grid915_attach.json"
L.GEO = FROZEN / "geo919_coords.json"

REPS = 4000                 # 사전등록 §4 — MC 오차 ≈ SE/√4000
SEEDS = list(range(1, 25))  # 사전등록 §4 — 씨앗 24개
N_MINS = (1, 5, 10, 15, 20, 25)
N_MIN_MAIN = 20             # 958 이 고른 값 — 비교를 위해 정본 칸으로 둔다


# ── 빠른 스피어만 (동점 평균 순위 · scipy 와 같은 값) ────────────────────────
def sp(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3:
        return float("nan")
    ra = rankdata(a)
    rb = rankdata(b)
    sa, sb = ra.std(), rb.std()
    if sa == 0 or sb == 0:
        return float("nan")
    return float(((ra - ra.mean()) * (rb - rb.mean())).mean() / (sa * sb))


def fixed_preds(rows, base, plus) -> dict:
    """🔴 팔 전량에서 **한 번만** 적합한다(958 과 같은 자)."""
    y = np.asarray([r["y_들림"] for r in rows], dtype=float)
    g = np.asarray([r["개체"] for r in rows])
    r1, sd1, P1 = L.rho_of(L.mat(rows, *base), y, g)
    r2, sd2, P2 = L.rho_of(L.mat(rows, *(base + plus)), y, g)
    return {"y": y, "P1": P1, "P2": P2, "ρ(기준) 합산": r1, "ρ(더한 것) 합산": r2,
            "🔴 합산 Δρ": r2 - r1}


def bags_of(y, grp, idx, n_min):
    """이 표본에서 **쓸 수 있는 묶음**의 집합."""
    out = []
    for gg in sorted(set(grp[idx])):
        sel = idx[grp[idx] == gg]
        if len(sel) >= n_min and len(set(y[sel])) >= 3:
            out.append(gg)
    return out


def within_stat(y, P1, P2, grp, idx, n_min, bags=None) -> dict:
    """묶음 안으로 **채점만** 좁힌다.

    `bags` 가 주어지면 **그 묶음만** 쓴다(설계 ㉯ 원표본 조건부).
    `bags` 가 None 이면 이 표본에서 **다시 고른다**(설계 ㉮ 재적용).
    """
    per, num, den = {}, 0.0, 0
    use = sorted(set(grp[idx])) if bags is None else bags
    for gg in use:
        sel = idx[grp[idx] == gg]
        n = len(sel)
        if bags is None and (n < n_min or len(set(y[sel])) < 3):
            continue
        if n < 3 or len(set(y[sel])) < 3:
            continue
        a = sp(P1[sel], y[sel])
        b = sp(P2[sel], y[sel])
        if math.isnan(a) or math.isnan(b):
            continue
        per[str(gg)] = {"쌍": n, "ρ(기준)": a, "ρ(더한 것)": b, "Δρ": b - a}
        num += n * (b - a)
        den += n
    return {"분자: 쌍 가중 Δρ 합": num, "분모: 쓴 쌍": den,
            "🔴 Δρ_within": (num / den) if den else float("nan"),
            "묶음 수": len(per), "묶음별": per}


def boot(y, P1, P2, grp, clus, n_min, design, reps, seed) -> dict:
    """군집 재표집. `design` 은 '㉮ 재적용' 또는 '㉯ 원표본 조건부'."""
    rng = np.random.RandomState(seed)
    cs = np.unique(clus)
    pos = {c: np.where(clus == c)[0] for c in cs}
    idx0 = np.arange(len(y))
    fixed = bags_of(y, grp, idx0, n_min) if design == "㉯" else None
    d, fail = [], 0
    for _ in range(reps):
        pick = rng.choice(len(cs), len(cs), replace=True)
        ii = np.concatenate([pos[cs[j]] for j in pick])
        v = within_stat(y, P1, P2, grp, ii, n_min, bags=fixed)["🔴 Δρ_within"]
        if math.isnan(v):
            fail += 1
            continue
        d.append(v)
    d = np.asarray(d)
    return {"설계": design, "씨앗": seed, "재표집 성공": int(len(d)), "요청": reps,
            "실패": fail, "SE": float(d.std()), "평균": float(d.mean()),
            "2.5%": float(np.percentile(d, 2.5)), "97.5%": float(np.percentile(d, 97.5)),
            "고정 묶음": (sorted(map(str, fixed)) if fixed is not None else None)}


def kendall_split(y, P1, P2, grp) -> dict:
    n = len(y)
    iu, ju = np.triu_indices(n, 1)
    sy = np.sign(y[iu] - y[ju])
    tie = sy == 0
    c1 = np.sign(P1[iu] - P1[ju]) * sy
    c2 = np.sign(P2[iu] - P2[ju]) * sy
    gain = c2 - c1
    same = grp[iu] == grp[ju]
    ok = ~tie
    win, bet = ok & same, ok & ~same
    tot = float(gain[ok].sum())
    return {"분자: 안쪽 차(C−D)": float(gain[win].sum()), "분모: 안쪽 짝": int(win.sum()),
            "분자: 사이 차(C−D)": float(gain[bet].sum()), "분모: 사이 짝": int(bet.sum()),
            "분자: 전체 차": tot, "분모: 전체 짝(y 동점 뺀 것)": int(ok.sum()),
            "안 짝당": float(gain[win].sum()) / max(int(win.sum()), 1),
            "사이 짝당": float(gain[bet].sum()) / max(int(bet.sum()), 1),
            "🔴 안쪽 몫": (float(gain[win].sum()) / tot) if tot else float("nan"),
            "y 동점 짝": int(tie.sum()),
            "W10 짝 회계 == C(n,2)": bool(int(win.sum()) + int(bet.sum()) + int(tie.sum())
                                       == n * (n - 1) // 2)}


def quartile_labels(vals: np.ndarray, name: str) -> np.ndarray:
    q = np.percentile(vals, [25, 50, 75])
    lab = np.digitize(vals, q, right=False)
    return np.asarray([f"{name}Q{i+1}" for i in lab])


def main() -> dict:
    t0 = dt.datetime.now(dt.timezone.utc)
    pairs = L.load_pairs()
    wd = L.load_wiki_daily()
    coords = L.load_coords()
    lp = L.load_lifepop()
    L.assert_no_label_files()
    built = L.build_arms(wd, coords, lp, pairs)
    B = built["B"]

    R: dict = {
        "노트": 959, "레인": "판정", "논문 스텝": 501,
        "사전등록": "docs/prereg_959_reach.md (커밋 4212af9ab · 측정 전 · 파일 하나)",
        "시작(UTC)": t0.isoformat(),
        "🔴 무엇을 재나": "958 의 D3 을 다시 결정한다 — 부트 설계 둘 · 씨앗 24개 · "
                    "「T 를 넘는 씨앗 비율」",
        "🔴 입력": "data/frozen/957_inputs (얼린 957 blob) — 959 의 새 표를 안 쓴다",
        "🔴 판을 뗐다": "판 ρ · 유보를 한 번도 안 건드린다 — 판 주장 0",
        "🔴 데몬을 재웠나": L.daemon_asleep(),
        "🔴 쓴 코드 sha256(앞16)": {p: L.sha(ROOT / p) for p in
                                ("runners/d3_959.py", "runners/layers957.py")},
        "분모: 팔 B 쌍": len(B),
    }

    F = fixed_preds(B, ["x1"], ["x3"])
    y, P1, P2 = F["y"], F["P1"], F["P2"]
    grp = np.asarray([str(r["도메인"]) for r in B])
    clus = np.asarray([str(r["개체"]) for r in B])
    idx0 = np.arange(len(B))

    w20 = within_stat(y, P1, P2, grp, idx0, N_MIN_MAIN)
    kd = kendall_split(y, P1, P2, grp)
    dw = w20["🔴 Δρ_within"]

    # ── V — 958 의 수를 재현하는가 (이 러너의 배선 검사) ────────────────────
    R["🔴 V 958 재현"] = {
        "958 의 Δρ_within": 0.087763, "🔴 지금 Δρ_within": dw,
        "차": abs(dw - 0.087763),
        "958 의 안쪽 몫": 0.436246, "🔴 지금 안쪽 몫": kd["🔴 안쪽 몫"],
        "몫 차": abs(kd["🔴 안쪽 몫"] - 0.436246),
        "958 의 분자 40.45895898482041 · 분모 461": [w20["분자: 쌍 가중 Δρ 합"], w20["분모: 쓴 쌍"]],
        "통과": bool(abs(dw - 0.087763) < 1e-5 and abs(kd["🔴 안쪽 몫"] - 0.436246) < 1e-5)}
    R["§6 자 A(N_min=20)"] = w20
    R["§6 자 B 켄달 짝 분해(칸막이 = 도메인)"] = kd
    R["🔴 합산 Δρ"] = F["🔴 합산 Δρ"]

    # ── D-B · 두 설계 × 씨앗 24 ─────────────────────────────────────────────
    per_design = {}
    for design in ("㉮", "㉯"):
        rows_ = []
        for s in SEEDS:
            b = boot(y, P1, P2, grp, clus, N_MIN_MAIN, design, REPS, s)
            T = max(L.CARD_T, 2 * b["SE"])
            rows_.append({"씨앗": s, "SE": b["SE"], "T": T,
                          "95%": [b["2.5%"], b["97.5%"]],
                          "T 를 넘나": bool(abs(dw) > T),
                          "구간이 0 을 품나": bool(b["2.5%"] <= 0 <= b["97.5%"]),
                          "판정": L.verdict(dw, T)})
        cross = sum(1 for r in rows_ if r["T 를 넘나"])
        ses = np.asarray([r["SE"] for r in rows_])
        per_design[design] = {
            "이름": {"㉮": "재적용(958 이 쓴 것)", "㉯": "원표본 조건부(🔴 정본)"}[design],
            "🔴 R8 분자: T 를 넘는 씨앗": cross, "🔴 R8 분모: 돌린 씨앗": len(rows_),
            "🔴 씨앗 비율": cross / len(rows_),
            "SE 평균": float(ses.mean()), "SE 최소": float(ses.min()),
            "SE 최대": float(ses.max()),
            "MC 오차 ≈ SE/√reps": float(ses.mean() / math.sqrt(REPS)),
            "구간이 0 을 품는 씨앗": sum(1 for r in rows_ if r["구간이 0 을 품나"]),
            "고정 묶음": boot(y, P1, P2, grp, clus, N_MIN_MAIN, design, 2, 1)["고정 묶음"],
            "씨앗별": rows_}
    R["§7 부트 설계 둘 × 씨앗 24"] = per_design
    R["W11 두 설계가 정말 다른 추정량인가"] = {
        "㉮ SE 평균": per_design["㉮"]["SE 평균"], "㉯ SE 평균": per_design["㉯"]["SE 평균"],
        "차": abs(per_design["㉮"]["SE 평균"] - per_design["㉯"]["SE 평균"]),
        "통과": bool(abs(per_design["㉮"]["SE 평균"] - per_design["㉯"]["SE 평균"]) > 1e-6)}

    ratio = per_design["㉯"]["🔴 씨앗 비율"]
    if ratio >= 0.95:
        db = "가 — 든다"
    elif ratio <= 0.05:
        db = "나 — 못 가른다"
    else:
        db = "🔴 다 — 판정을 내지 않는다. 구간만 싣는다"
    lo = float(np.mean([r["95%"][0] for r in per_design["㉯"]["씨앗별"]]))
    hi = float(np.mean([r["95%"][1] for r in per_design["㉯"]["씨앗별"]]))
    R["🔴🔴 D-B 판정(정본 = ㉯)"] = {
        "Δρ_within": dw, "씨앗 비율": ratio,
        "씨앗 평균 95% 구간": [lo, hi],
        "🔴 판정": db,
        "🔴 958 이 낸 판정": "나 — 못 가른다 (씨앗 7 하나)",
        "🔴 바뀌었나": db != "나 — 못 가른다"}

    # ── D-B 곁들이 · N_min 쓸기 × 두 설계 ───────────────────────────────────
    sweep = {}
    for nm in N_MINS:
        w = within_stat(y, P1, P2, grp, idx0, nm)
        cell = {"Δρ_within": w["🔴 Δρ_within"], "묶음 수": w["묶음 수"],
                "분모: 쓴 쌍": w["분모: 쓴 쌍"]}
        for design in ("㉮", "㉯"):
            cr = 0
            for s in SEEDS[:8]:
                b = boot(y, P1, P2, grp, clus, nm, design, 1000, s)
                T = max(L.CARD_T, 2 * b["SE"])
                cr += int(abs(w["🔴 Δρ_within"]) > T)
            cell[f"{design} T 를 넘는 씨앗(8 중)"] = cr
        sweep[f"N_min={nm}"] = cell
    R["§4 N_min 쓸기 × 설계 (씨앗 8 · 재표집 1000)"] = sweep
    R["🔴 N_min 이 판정을 바꾸나(㉯)"] = bool(
        len({(v["㉯ T 를 넘는 씨앗(8 중)"] >= 5) for v in sweep.values()}) > 1)

    # ── D-C · 칸막이 셋 ─────────────────────────────────────────────────────
    size = np.asarray([r["x1"][2] for r in B])          # log10(1+최근 28일 평균)
    when = np.asarray([dt.date.fromisoformat(r["언제"]).toordinal() for r in B], dtype=float)
    parts = {
        "도메인 (958 의 칸막이)": grp,
        "개체 규모 분위 4 (s 최근 28일 평균)": quartile_labels(size, "규모"),
        "액션 시각 분위 4": quartile_labels(when, "시각"),
    }
    pc = {}
    for name, g2 in parts.items():
        k2 = kendall_split(y, P1, P2, g2)
        w2 = within_stat(y, P1, P2, g2, idx0, N_MIN_MAIN)
        pc[name] = {"칸막이 수": int(len(set(g2))),
                    "🔴 안쪽 몫": k2["🔴 안쪽 몫"],
                    "안쪽 짝": k2["분모: 안쪽 짝"], "안쪽 차": k2["분자: 안쪽 차(C−D)"],
                    "사이 짝": k2["분모: 사이 짝"], "사이 차": k2["분자: 사이 차(C−D)"],
                    "Δρ_within(N_min=20)": w2["🔴 Δρ_within"], "묶음 수": w2["묶음 수"],
                    "W10 짝 회계": k2["W10 짝 회계 == C(n,2)"]}
    shares = [v["🔴 안쪽 몫"] for v in pc.values()]
    spread = max(shares) - min(shares)
    R["§8 칸막이 셋(T4 · 팔 B)"] = {
        "칸막이별": pc,
        "🔴 안쪽 몫 최대−최소": spread,
        "🔴🔴 D-C 판정": ("가 — 굳다(15%p 미만)" if spread < 0.15
                     else "나 — 🔴 흔들린다. 501 의 D1 도 흔들린다"),
        "Q8 (15%p 넘게 흔들린다)": bool(spread >= 0.15)}

    R["🔴 예측 채점"] = {
        "Q7 씨앗 비율이 0% 도 100% 도 아니다": {
            "㉮": per_design["㉮"]["🔴 씨앗 비율"], "㉯": ratio,
            "맞았나": bool(0 < ratio < 1 or 0 < per_design["㉮"]["🔴 씨앗 비율"] < 1)},
        "Q8 칸막이 둘에서 15%p 넘게 흔들린다": {
            "최대−최소": spread, "맞았나": bool(spread >= 0.15)},
    }
    t1 = dt.datetime.now(dt.timezone.utc)
    R["끝(UTC)"] = t1.isoformat()
    R["🔴 걸린 시간(초)"] = (t1 - t0).total_seconds()
    OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in R.items()
                      if k not in ("§7 부트 설계 둘 × 씨앗 24", "§6 자 A(N_min=20)")},
                     ensure_ascii=False, indent=1)[:6000])
    return R


if __name__ == "__main__":
    main()
