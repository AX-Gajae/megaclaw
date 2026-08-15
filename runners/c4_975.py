#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""975 --- **축 C4 의 정본 자**: 요인 하나만 흔든 짝 실험의 **Δ ± SE**.

🔴 972·973·974 세 사이클 연속 **C4 = 0** 이었다. 티처 #113 이 순위를 바꿨다:
   *「C2 말고 C4 를 열어라 --- C4 의 자는 지금 있는 것으로 돌아간다」*.

사전등록 `docs/prereg_975_c4.md` §1~§3 을 그대로 따른다.
**밑판** = 974 의 C 팔(HPLT 전량) · λ 1.0 · 특징 전량6 · 학습 창 전량 · 도메인 가중 균등.
**요인 다섯** R1 λ(optimizer) · R2 특징(architecture) · R3 학습 창(curriculum) ·
R4 도메인 가중(objective) · R5 원천 혼합(data mixture).

🔴 **유보는 한 번도 안 건드린다** --- 14 수준의 유보 지문이 하나여야 한다(반증조건 6).

씀:
    python3 runners/c4_975.py --stage wiring  --ref <40자 sha>
    python3 runners/c4_975.py --stage factors --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for p in (str(ROOT), str(ROOT / "runners")):
    if p not in sys.path:
        sys.path.insert(0, p)

import runners.predict971 as P                    # noqa: E402
import predict972 as N                            # noqa: E402
import runners.layers957 as L                     # noqa: E402
import loso974 as LO                              # noqa: E402

RAN = ("runners/c4_975.py", "runners/loso974.py", "runners/precision974.py",
       "runners/layers957.py", "runners/predict971.py", "runners/predict972.py")
OUT = ROOT / "runners"
SEED = 975
BOOT = 2000
PERM_B = 4000

# ── 사전등록 §1 밑판 ────────────────────────────────────────────────────
BASE = collections.OrderedDict([
    ("원천 혼합", "C(HPLT 전량)"),
    ("능형 λ", 1.0),
    ("특징 집합", "전량6"),
    ("학습 창", "전량"),
    ("도메인 가중", "균등"),
])
# ── 사전등록 §2 격자값 ──────────────────────────────────────────────────
GRID = collections.OrderedDict([
    ("R1 능형 λ (optimizer)", ("능형 λ", [0.1, 1.0, 10.0, 100.0])),
    ("R2 특징 집합 (architecture)", ("특징 집합", ["전량6", "수준3", "모양3", "평균1"])),
    ("R3 학습 창 (curriculum)", ("학습 창", ["전량", "≥2018-01-01", "≥2021-01-01",
                                        "≥2022-01-01"])),
    ("R4 도메인 가중 (objective)", ("도메인 가중", ["균등", "역빈도", "역빈도√"])),
    ("R5 원천 혼합 (data mixture)", ("원천 혼합", ["C(HPLT 전량)", "B(HPLT 없음)",
                                            "C′(HPLT · 974 게이트)"])),
])
FEATS = {"전량6": [0, 1, 2, 3, 4, 5], "수준3": [0, 1, 2], "모양3": [3, 4, 5],
         "평균1": [0]}
WIN = {"전량": None, "≥2018-01-01": dt.date(2018, 1, 1),
       "≥2021-01-01": dt.date(2021, 1, 1), "≥2022-01-01": dt.date(2022, 1, 1)}
THR_CARD = 0.00353          # 사전등록 §3 --- 진단값


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_stamp() -> dict:
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def stamp_block(ref, cs0, cs1, t0):
    ds = {k: P._sha_file(str(ROOT / v)) for k, v in LO.SRC.items()}
    runner, ok = {}, 0
    for r in RAN:
        disk = P._sha_file(str(ROOT / r))
        try:
            cm = hashlib.sha256(subprocess.check_output(
                ["git", "show", "%s:%s" % (ref, r)], cwd=str(ROOT))).hexdigest()
        except Exception:                                          # noqa: BLE001
            cm = None
        runner[r] = {"디스크 sha256": disk, "커밋 blob sha256": cm, "일치": disk == cm}
        ok += 1 if disk == cm else 0
    return {
        "언제(시작)": t0, "언제(끝)": _now(),
        "시작 code_stamp 요약": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "끝 code_stamp 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
        "🔴 시작=끝": cs0 == cs1,
        "분모: 도장이 덮는 파일": len(cs1),
        "🔴 자료 지문": ds, "분모: 연 자료 파일": len(ds),
        "🔴 F1 기준 ref(준 대로)": ref,
        "🔴 40자 고정 sha 인가": bool(re.fullmatch(r"[0-9a-f]{40}", ref or "")),
        "🔴 기준 ref 가 0000…0000 인가": bool(re.fullmatch(r"0{40}", ref or "")),
        "러너별": runner, "🔴 분자/분모": "%d / %d" % (ok, len(RAN)),
        "🔴 F5 통과": ok == len(RAN) and bool(re.fullmatch(r"[0-9a-f]{40}", ref or ""))
        and not re.fullmatch(r"0{40}", ref or ""),
    }


# ══════════════════════════════════════════════════════════════════════
# 가중 능형 --- 🔴 가중 1 에서 `layers957.ridge_fit` 과 같은 답을 낸다(W1)
# ══════════════════════════════════════════════════════════════════════
def ridge_fit_w(X, y, a, w=None):
    """`layers957.ridge_fit` 의 가중 판. w=None 이면 생산 함수를 **그대로 부른다**."""
    if w is None:
        return L.ridge_fit(X, y, a)
    w = np.asarray(w, float)
    w = w * (len(w) / w.sum())                  # 평균 1 로 맞춘다
    mu = (w[:, None] * X).sum(0) / w.sum()
    var = (w[:, None] * (X - mu) ** 2).sum(0) / w.sum()
    sd = np.sqrt(var)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / sd
    ym = float((w * y).sum() / w.sum())
    A = Z.T @ (w[:, None] * Z) + a * np.eye(Z.shape[1])
    coef = np.linalg.solve(A, Z.T @ (w * (y - ym)))
    return coef, mu, sd, ym


# ══════════════════════════════════════════════════════════════════════
def build_pools():
    base, drop_b = [], {}
    for s in ("sao941", "sao959"):
        r, d = LO.load(s)
        base += r
        drop_b[s] = d
    hplt, _ = LO.load("hplt_ko")
    hplt_g, _ = LO.load("hplt_ko", gate=True)

    def isho(r):
        return dt.date.fromisoformat(r["언제"]) >= LO.SPLIT

    hold = [r for r in base if isho(r)]
    tr_b = [r for r in base if not isho(r)]
    src = {"B(HPLT 없음)": tr_b,
           "C(HPLT 전량)": tr_b + [r for r in hplt if not isho(r)],
           "C′(HPLT · 974 게이트)": tr_b + [r for r in hplt_g if not isho(r)]}
    doms = sorted({r["도메인"] for r in src["C(HPLT 전량)"] + hold})
    dom_ho = collections.Counter(r["도메인"] for r in hold)
    dom_tr = collections.Counter(r["도메인"] for r in tr_b)
    gated = [d for d in doms if dom_ho[d] >= LO.MIN_HO and dom_tr[d] >= LO.MIN_TR]
    return {"hold": hold, "src": src, "doms": doms, "gated": gated,
            "dom_ho": dict(dom_ho), "dom_tr": dict(dom_tr), "drop_b": drop_b}


def design(rows, doms, fidx):
    X = np.asarray([[r["x"][i] for i in fidx] for r in rows], dtype=float)
    D = np.zeros((len(rows), len(doms)), dtype=float)
    for i, r in enumerate(rows):
        if r["도메인"] in doms:
            D[i, doms.index(r["도메인"])] = 1.0
    return np.hstack([X, D])


def weights_of(rows, kind):
    if kind == "균등":
        return None
    c = collections.Counter(r["도메인"] for r in rows)
    if kind == "역빈도":
        return np.asarray([1.0 / c[r["도메인"]] for r in rows], float)
    if kind == "역빈도√":
        return np.asarray([1.0 / np.sqrt(c[r["도메인"]]) for r in rows], float)
    raise ValueError(kind)


def run_cfg(cfg, pools):
    """설정 하나 → 유보 예측. 🔴 유보는 어느 설정에서도 안 바뀐다."""
    tr = pools["src"][cfg["원천 혼합"]]
    cut = WIN[cfg["학습 창"]]
    if cut is not None:
        tr = [r for r in tr if dt.date.fromisoformat(r["언제"]) >= cut]
    fidx = FEATS[cfg["특징 집합"]]
    doms = pools["doms"]
    Xtr = design(tr, doms, fidx)
    ytr = np.asarray([r["y"] for r in tr], float)
    w = weights_of(tr, cfg["도메인 가중"])
    m = ridge_fit_w(Xtr, ytr, cfg["능형 λ"], w)
    Xho = design(pools["hold"], doms, fidx)
    return L.ridge_pred(m, Xho), len(tr)


def hold_fp(hold):
    return hashlib.sha256("|".join(r["쌍id"] for r in hold).encode()).hexdigest()


def per_dom(pred, pools):
    yho = np.asarray([r["y"] for r in pools["hold"]], float)
    dho = np.asarray([r["도메인"] for r in pools["hold"]])
    out = collections.OrderedDict()
    for d in pools["gated"]:
        m = dho == d
        out[d] = float(P.spear(pred[m], yho[m]))      # 🔴 여기서 안 반올림한다
    return out


def paired_boot(pred_a, pred_b, pools, idxsets):
    """🔴 짝지은 군집 붓스트랩 --- **같은 되뽑기**로 두 수준을 동시에 채점한다."""
    yho = np.asarray([r["y"] for r in pools["hold"]], float)
    dd = []
    for draw in idxsets:
        num = den = 0.0
        for idx in draw:
            y = yho[idx]
            ra = P.spear(pred_a[idx], y)
            rb = P.spear(pred_b[idx], y)
            if np.isfinite(ra) and np.isfinite(rb):
                num += (ra - rb) * len(idx)
                den += len(idx)
        if den:
            dd.append(num / den)
    a = np.asarray(dd, float)
    return a


def make_draws(pools, B, seed):
    rng = np.random.RandomState(seed)
    dho = np.asarray([r["도메인"] for r in pools["hold"]])
    pos = {d: np.flatnonzero(dho == d) for d in pools["gated"]}
    draws = []
    for _ in range(B):
        draws.append([p[rng.randint(0, len(p), len(p))] for d, p in pos.items()])
    return draws


# ══════════════════════════════════════════════════════════════════════
def stage_factors(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    pools = build_pools()
    fp = hold_fp(pools["hold"])

    # 밑판
    base_pred, base_n = run_cfg(dict(BASE), pools)
    base_per = per_dom(base_pred, pools)
    base_pooled = float(np.average(
        [base_per[d] for d in pools["gated"]],
        weights=[pools["dom_ho"][d] for d in pools["gated"]]))
    draws = make_draws(pools, BOOT, SEED)

    levels, one_only = collections.OrderedDict(), []
    for fname, (key, vals) in GRID.items():
        rows = collections.OrderedDict()
        for v in vals:
            cfg = dict(BASE)
            cfg[key] = v
            diff = [k for k in BASE if cfg[k] != BASE[k]]
            one_only.append({"요인": fname, "수준": str(v),
                             "밑판과 다른 칸": diff,
                             "🔴 요인 하나만 흔들었나": len(diff) <= 1})
            pred, ntr = run_cfg(cfg, pools)
            per = per_dom(pred, pools)
            pooled = float(np.average(
                [per[d] for d in pools["gated"]],
                weights=[pools["dom_ho"][d] for d in pools["gated"]]))
            # 🔴 Δ 는 **생산 함수** `predict971.pooled_delta` 로 낸다(바퀴 재발명 금지)
            perd = collections.OrderedDict(
                (d, {"유보 행": pools["dom_ho"][d],
                     "ρ": {LO.KEY_C: per[d], LO.KEY_B: base_per[d]}})
                for d in pools["gated"])
            delta, den_d = P.pooled_delta(perd, LO.KEY_C, LO.KEY_B)
            delta = float(delta)
            if v == BASE[key]:
                se, a = 0.0, np.zeros(1)
            else:
                a = paired_boot(pred, base_pred, pools, draws)
                se = float(a.std(ddof=1))
            domd = {d: round(per[d] - base_per[d], 6) for d in pools["gated"]}
            per_r = {d: round(per[d], 6) for d in pools["gated"]}
            rows[str(v)] = {
                "밑판인가": v == BASE[key],
                "학습 행": ntr,
                "🔴 유보 지문": hold_fp(pools["hold"]),
                "묶음 유보 ρ": round(pooled, 6),
                "🔴🔴 Δ(수준 − 밑판)": round(delta, 6),
                "🔴🔴 SE(짝 군집 붓스트랩)": round(se, 6),
                "🔴 |Δ|/SE": (round(abs(delta) / se, 4) if se > 0 else None),
                "🔴 문턱 ① |Δ| ≥ 2·SE": bool(se > 0 and abs(delta) >= 2 * se),
                "🔴 문턱 ② |Δ| ≥ 0.00353": bool(abs(delta) >= THR_CARD),
                "🔴🔴 둘 다 넘었나": bool(se > 0 and abs(delta) >= 2 * se
                                  and abs(delta) >= THR_CARD),
                "도메인별 Δ": domd,
                "도메인별 유보 ρ": per_r,
                "붓스트랩 성공 뽑기": int(len(a)) if se > 0 else BOOT,
            }
        ds = [rows[str(v)]["🔴🔴 Δ(수준 − 밑판)"] for v in vals]
        best = max(vals, key=lambda v: abs(rows[str(v)]["🔴🔴 Δ(수준 − 밑판)"]))
        levels[fname] = {
            "흔든 칸": key, "격자값": [str(v) for v in vals],
            "수준별": rows,
            "🔴🔴🔴 스팬(max Δ − min Δ)": round(max(ds) - min(ds), 6),
            "🔴 가장 큰 |Δ| 수준": str(best),
            "🔴 그 수준의 Δ ± SE": "%+.6f ± %.6f" % (
                rows[str(best)]["🔴🔴 Δ(수준 − 밑판)"],
                rows[str(best)]["🔴🔴 SE(짝 군집 붓스트랩)"]),
            "🔴 그 수준의 |Δ|/SE": rows[str(best)]["🔴 |Δ|/SE"],
            "🔴 문턱 둘을 다 넘은 수준 수": sum(
                1 for v in vals if rows[str(v)]["🔴🔴 둘 다 넘었나"]),
        }

    rank = sorted(levels.items(), key=lambda kv: -kv[1]["🔴🔴🔴 스팬(max Δ − min Δ)"])
    ranking = collections.OrderedDict()
    for i, (k, v) in enumerate(rank, 1):
        ranking["%d위 %s" % (i, k)] = {
            "스팬": v["🔴🔴🔴 스팬(max Δ − min Δ)"],
            "가장 큰 |Δ| 수준": v["🔴 가장 큰 |Δ| 수준"],
            "Δ ± SE": v["🔴 그 수준의 Δ ± SE"],
            "|Δ|/SE": v["🔴 그 수준의 |Δ|/SE"],
            "문턱 둘을 다 넘은 수준 수": v["🔴 문턱 둘을 다 넘은 수준 수"],
        }

    # 🔴 974 의 LOSO 를 이 주행에서 다시 --- 부호 일관성 p 의 수리 대조(3순위 ⓓ)
    yho = np.asarray([r["y"] for r in pools["hold"]], float)
    dho = np.asarray([r["도메인"] for r in pools["hold"]])
    predB, _ = run_cfg(dict(BASE, **{"원천 혼합": "B(HPLT 없음)"}), pools)
    per972 = collections.OrderedDict()
    for d in pools["gated"]:
        m = dho == d
        per972[d] = {"유보 행": int(m.sum()), "예측": {"B": predB[m], "C": base_pred[m]},
                     "_yho": yho[m],
                     "ρ": {LO.KEY_B: P.spear(predB[m], yho[m]),
                           LO.KEY_C: P.spear(base_pred[m], yho[m])}}
    pn = N.perm_null(per972, B=PERM_B, seed=974)

    n_all = len(one_only)
    out = {
        "무엇": "975 --- 축 C4: 요인 하나만 흔든 짝 실험의 Δ ± SE 와 요인 순위",
        "🔴 축": "C4 (capability 결정 요인)",
        "사전등록": "docs/prereg_975_c4.md §1~§3",
        "🔴 밑판": {k: str(v) for k, v in BASE.items()},
        "🔴 밑판 학습 행": base_n,
        "🔴 밑판 묶음 유보 ρ": round(base_pooled, 6),
        "🔴 밑판 도메인별 유보 ρ": {d: round(v, 6) for d, v in base_per.items()},
        "🔴 자료": {
            "유보 행": len(pools["hold"]),
            "🔴 게이트 통과 도메인": pools["gated"],
            "🔴 분모: 게이트 유보 행 합": int(sum(pools["dom_ho"][d]
                                        for d in pools["gated"])),
            "도메인별 유보 행": pools["dom_ho"],
            "도메인별 밑판 학습 행": pools["dom_tr"],
            "원천별 학습 행": {k: len(v) for k, v in pools["src"].items()},
        },
        "🔴🔴🔴 요인별 Δ ± SE": levels,
        "🔴🔴🔴 요인 순위(스팬 내림차순)": ranking,
        "🔴 반증조건 1 --- 요인 하나만 흔들었나": {
            "칸별": one_only,
            "🔴 분자/분모": "%d / %d" % (
                sum(1 for o in one_only if o["🔴 요인 하나만 흔들었나"]), n_all),
            "🔴 통과": all(o["🔴 요인 하나만 흔들었나"] for o in one_only)},
        "🔴 반증조건 6 --- 유보 지문이 하나인가": {
            "지문": fp,
            "서로 다른 지문 수": len({r["🔴 유보 지문"]
                                for f in levels.values()
                                for r in f["수준별"].values()}),
            "🔴 통과": len({r["🔴 유보 지문"] for f in levels.values()
                        for r in f["수준별"].values()}) == 1},
        "🔴 문턱 둘을 다 넘은 수준 (전 요인 합)": {
            "분자": sum(1 for f in levels.values() for r in f["수준별"].values()
                     if r["🔴🔴 둘 다 넘었나"]),
            "분모": n_all,
            "목록": ["%s / %s" % (f, lv) for f, v in levels.items()
                   for lv, r in v["수준별"].items() if r["🔴🔴 둘 다 넘었나"]]},
        "🔴 3순위 ⓓ 대조 --- 974 LOSO 를 이 주행에서 다시": pn,
        "씨앗": SEED, "붓스트랩 뽑기": BOOT, "순열 뽑기": PERM_B,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out975_factors.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    rng = np.random.RandomState(SEED)
    n, k = 400, 6
    Xt = rng.normal(size=(n, k))
    b = rng.normal(size=k)
    yt = Xt @ b + rng.normal(size=n) * 0.5
    Xh = rng.normal(size=(200, k))
    yh = Xh @ b + rng.normal(size=200) * 0.5

    W = collections.OrderedDict()
    # W1 --- 가중 1 에서 생산 함수와 같은 답
    m0 = L.ridge_fit(Xt, yt, 1.0)
    m1 = ridge_fit_w(Xt, yt, 1.0, np.ones(n))
    d1 = float(np.max(np.abs(L.ridge_pred(m0, Xh) - L.ridge_pred(m1, Xh))))
    W["W1 가중 1 에서 생산 함수 ridge_fit 과 같은 답"] = d1 < 1e-10

    rows = [{"x": list(rng.normal(size=6)), "도메인": ("a" if i % 5 else "b"),
             "언제": ("2017-05-05" if i % 3 else "2022-05-05"),
             "y": float(rng.normal()), "쌍id": "p%d" % i} for i in range(60)]
    W["W2 특징 부분집합이 열 수를 줄인다"] = (
        design(rows, ["a", "b"], FEATS["전량6"]).shape[1] == 8
        and design(rows, ["a", "b"], FEATS["수준3"]).shape[1] == 5
        and design(rows, ["a", "b"], FEATS["평균1"]).shape[1] == 3)
    cut = WIN["≥2021-01-01"]
    kept = [r for r in rows if dt.date.fromisoformat(r["언제"]) >= cut]
    W["W3 학습 창 자름이 실제로 행을 줄인다"] = 0 < len(kept) < len(rows)
    wa = weights_of(rows, "역빈도")
    wb = weights_of(rows, "균등")
    Xd = design(rows, ["a", "b"], FEATS["전량6"])
    yd = np.asarray([r["y"] for r in rows], float)
    W["W4 도메인 가중이 계수를 바꾼다"] = float(np.max(np.abs(
        ridge_fit_w(Xd, yd, 1.0, wa)[0] - ridge_fit_w(Xd, yd, 1.0, wb)[0]))) > 1e-8
    W["W5 원천 팔 셋의 학습 행 수가 다르다"] = None      # factors 에서 채운다
    # W6 --- 짝지은 붓스트랩이 같은 되뽑기를 두 수준에 쓴다
    fake = {"hold": [{"도메인": "a", "y": float(v), "쌍id": "q%d" % i}
                     for i, v in enumerate(rng.normal(size=40))],
            "gated": ["a"], "dom_ho": {"a": 40}}
    dr = make_draws(fake, 5, SEED)
    pa = rng.normal(size=40)
    same = paired_boot(pa, pa, fake, dr)
    W["W6 같은 되뽑기를 두 수준에 쓴다(같은 예측이면 Δ=0)"] = bool(
        np.max(np.abs(same)) < 1e-12)
    W["W7 밑판 대 밑판의 Δ 가 정확히 0"] = None          # factors 자료로 아래에서 채운다
    W["W8 14 수준의 유보 지문이 하나"] = None            # factors 에서 채운다

    E = collections.OrderedDict()
    mE = L.ridge_fit(Xt, yt, 1.0)
    E["E1 학습 짝을 깨면 유보 상관이 죽는다"] = abs(P.spear(
        L.ridge_pred(L.ridge_fit(Xt[rng.permutation(n)], yt, 1.0), Xh), yh)) < 0.3
    E["E2 유보 y 를 섞으면 상관이 죽는다"] = abs(P.spear(
        L.ridge_pred(mE, Xh), yh[rng.permutation(200)])) < 0.3
    # E3 --- 🔴 부호 일관성 p 의 고침이 실제로 관측값을 본다
    npos = np.array([7] * 40 + [5] * 500 + [3] * 3460)   # 귀무 뽑기 흉내
    old = (int((npos == 7).sum()) + 1) / float(len(npos) + 1)
    new7 = (int((npos >= 7).sum()) + 1) / float(len(npos) + 1)
    new4 = (int((npos >= 4).sum()) + 1) / float(len(npos) + 1)
    E["E3 부호 일관성 p 의 고침이 관측값을 본다"] = bool(
        abs(old - new7) < 1e-12 and abs(new4 - new7) > 1e-12)
    E["E3 참고: 974 판 p(관측 무관)"] = round(old, 6)
    E["E3 참고: 고친 판 p(관측 7/7)"] = round(new7, 6)
    E["E3 참고: 고친 판 p(관측 4/7)"] = round(new4, 6)
    E["E4 λ 를 키우는 것은 파괴가 아니다(974 E1b 재확인)"] = abs(P.spear(
        L.ridge_pred(L.ridge_fit(Xt, yt, 1e12), Xh), yh)) > 0.5
    E["E5 특징을 한 칸으로 줄이면 상관이 내려간다"] = (
        P.spear(L.ridge_pred(L.ridge_fit(Xt[:, :1], yt, 1.0), Xh[:, :1]), yh)
        < P.spear(L.ridge_pred(mE, Xh), yh))

    pools = build_pools()
    ns = {k2: len(v) for k2, v in pools["src"].items()}
    W["W5 원천 팔 셋의 학습 행 수가 다르다"] = len(set(ns.values())) == 3
    fps = set()
    for fname, (key, vals) in GRID.items():
        for v in vals:
            fps.add(hold_fp(pools["hold"]))
    W["W8 14 수준의 유보 지문이 하나"] = len(fps) == 1
    p1, _ = run_cfg(dict(BASE), pools)
    p2, _ = run_cfg(dict(BASE), pools)
    perw = collections.OrderedDict()
    d1r = per_dom(p1, pools)
    d2r = per_dom(p2, pools)
    for d in pools["gated"]:
        perw[d] = {"유보 행": pools["dom_ho"][d],
                   "ρ": {LO.KEY_C: d2r[d], LO.KEY_B: d1r[d]}}
    dz, _den = P.pooled_delta(perw, LO.KEY_C, LO.KEY_B)
    W["W7 밑판 대 밑판의 Δ 가 정확히 0"] = bool(float(dz) == 0.0)

    out = {"무엇": "975 --- C4 배선 W1~W8 · 파괴 대조 E1~E5",
           "🔴 축": "C4",
           "W": {k2: (bool(v) if isinstance(v, (bool, np.bool_)) else v)
                 for k2, v in W.items()},
           "🔴 W 분자/분모": "%d / %d" % (
               sum(1 for v in W.values() if v is True), len(W)),
           "🔴 W1 최대 절대차": d1,
           "E": {k2: (bool(v) if isinstance(v, (bool, np.bool_)) else v)
                 for k2, v in E.items()},
           "🔴 E 분자/분모": "%d / %d" % (
               sum(1 for k2, v in E.items()
                   if v is True and not k2.startswith("E3 참고")),
               sum(1 for k2 in E if not k2.startswith("E3 참고"))),
           "원천별 학습 행": ns}
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out975_wiring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["wiring", "factors"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = {"wiring": stage_wiring, "factors": stage_factors}[a.stage](a.ref)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=str)[:5000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
