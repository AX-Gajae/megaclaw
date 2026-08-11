# -*- coding: utf-8 -*-
"""팔 922-ㅎ — **바닥을 고치고 ③ 을 다시 잰다** (사전등록 `docs/prereg_922_permfix.md`).

🔴 순서가 규약이다(사전등록 §3·§5):
    ① 표를 만들고 **918 의 표와 열 단위로 대조**(W0)
    → ② 진짜 세계의 **기후값 팔만** 계산(개선 수는 아직 없다)
    → ③ **주 귀무 N2 를 먼저** 돌린다 → 비교가능성 관문 → 정지 관문
    → ④ 통과할 때만 **진짜 비교**를 계산한다   ← 🔴 멈추면 함수가 `return` 한다(#176)
    → ⑤ N1 · N0(심은 결함) 을 잰다 → ⑥ 배선 회계 → ⑦ 판정

산출물: runners/out922_permfix.json
사용:
    python3 runners/perm922_run.py
    G922_STOP_COEF=1e9 G922_TAG=_stopfire python3 runners/perm922_run.py   # 정지 관문 강제 발화
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))

from state.interval918 import (BASE_LAGS, CELL_MIN, DAY0, NDAY,  # noqa: E402
                               OBS_MIN_FRAC, SPLIT_SALT, TAU_PRIMARY,
                               baseline_ratio, boot, coverage, events_and_gaps,
                               fit_tables, predict, sha256_text, split_grids,
                               surges)
from state.perm922 import (COMPARABLE_REL, HALFWIDTH_CAP,  # noqa: E402
                           comparability, gap_multiset_same, gaps_from_events,
                           null_n0_old, null_n1_shuffle_r, null_n2_gap_order,
                           real_events, same_table)

SCRATCH = Path(os.environ.get(
    "G922_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad")) / "g922"
TAG = os.environ.get("G922_TAG", "")
OUT = ROOT / f"runners/out922_permfix{TAG}.json"
B = int(os.environ.get("G922_B", "2000"))
SEED = int(os.environ.get("G922_SEED", "918"))
STOP_COEF = float(os.environ.get("G922_STOP_COEF", "0.01"))

#: 🔴 자기시험의 대조값 — 918 이 공표한 정본(소수점 끝까지)
CANON = {
    "개선(일)": 0.7545204330866538,
    "lo": 0.6436055429260724,
    "hi": 0.8861167731832372,
    "홀드아웃 간격": 54862,
    "홀드아웃 격자": 2277,
    "학습 간격": 121908,
    "사건 수": 185070,
    "간격 수": 176770,
}


# ────────────────────────────────────────────────────────────── 한 세계를 잰다
def measure(tab, tr_set, ho_set, *, world: str, arms, do_boot=True, do_cov=False,
            plant_ignore_state=False):
    """한 세계(진짜 또는 귀무)에서 자를 잰다. 🔴 모든 결과에 `세계` 딱지를 붙인다."""
    trm = tr_set[tab["gi"]]
    hom = ho_set[tab["gi"]]
    T = fit_tables(tab, trm)
    gap = tab["gap"][hom].astype(float)
    gi = tab["gi"][hom]
    res = {
        "세계": world,
        "표(학습)": {k: T[k] for k in
                  ("학습 간격 수(분모)", "전체 중앙값", "🔴 달력 셀 가짓수",
                   "🔴 3수준 셀 가짓수", "mag 3분위 경계", "prevmed 3분위 경계",
                   "전체 10~90분위")},
        "🔴 사건 수(분모 A)": tab["🔴 사건 수(분모 A)"],
        "🔴 간격 수(분모 B)": tab["🔴 간격 수(분모 B)"],
        "홀드아웃 간격 수(분모)": int(hom.sum()),
        "홀드아웃 격자(군집) 수": int(len(np.unique(gi))),
        "간격 중앙값": float(np.median(tab["gap"])) if tab["gap"].size else None,
        "간격 평균": float(tab["gap"].mean()) if tab["gap"].size else None,
    }
    preds, errs = {}, {}
    for a in arms:
        p, back = predict(tab, hom, T, arm=a, plant_ignore_state=plant_ignore_state)
        preds[a] = p
        errs[a] = np.abs(gap - p)
        res[a] = {"MAE": float(errs[a].mean()), "MedAE": float(np.median(errs[a])),
                  "후퇴 회계": back}
    if len(arms) > 1:
        base = errs["가 기후값"]
        cell_all = {}
        for a in arms:
            if a == "가 기후값":
                continue
            imp = base - errs[a]
            cell = {"개선(일)": float(imp.mean()),
                    "🔴 개선율(그 세계의 기후값 MAE 로 나눈 수)":
                        float(imp.mean() / base.mean()) if base.mean() > 0 else None}
            if do_boot:
                bb = boot(imp, gi, B=B, seed=SEED)
                cell["🔴 군집 부트스트랩(규약 47)"] = bb
                cell["🔴 반폭 > 0.7545 인가(사전등록 §2)"] = bool(
                    bb["🔴 반폭(=MDE 자리)"] > HALFWIDTH_CAP)
            cell_all[a] = cell
            res.setdefault("_imp", {})[a] = (imp, gi)
        res["🔴 자 — MAE(기후값) − MAE(팔)"] = cell_all
        d = preds["나 조건부(주)"] - preds["가 기후값"]
        res["🔴 배선 — 상태 열이 예측을 움직였나"] = {
            "다른 행": int((d != 0).sum()), "분모": int(d.size),
            "다른 행 비율": float((d != 0).mean()), "통과": bool((d != 0).any())}
    if do_cov:
        res["🔴 덮음"] = {"가 기후값": coverage(tab, hom, T, which="달력"),
                       "나 조건부(주)": coverage(tab, hom, T, which="조건부")}
    return res


def count_real_improvements(o) -> int:
    """🔴 산출물을 재귀로 훑어 **진짜 세계의 개선 수**를 담은 절을 센다(#176 의 자)."""
    n = 0
    if isinstance(o, dict):
        if o.get("세계") == "진짜" and o.get("🔴 자 — MAE(기후값) − MAE(팔)"):
            n += 1
        for v in o.values():
            n += count_real_improvements(v)
    elif isinstance(o, list):
        for v in o:
            n += count_real_improvements(v)
    return n


def _scrub(o):
    """산출물에서 작업용 배열(`_imp`)을 뺀다."""
    if isinstance(o, dict):
        return {k: _scrub(v) for k, v in o.items() if k != "_imp"}
    if isinstance(o, (list, tuple)):
        return [_scrub(x) for x in o]
    return o


def finish(out: dict, t0: float, tstart: dt.datetime) -> None:
    out = _scrub(out)
    out["🔴 배선 W8 — 산출물에 남은 진짜 세계 개선 절의 수"] = count_real_improvements(out)
    out["시작 UTC"] = tstart.isoformat(timespec="seconds")
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({
        "멈췄나": out.get("⓪ 정지 관문", {}).get("🔴 멈췄나"),
        "진짜 세계 개선 절 수": out["🔴 배선 W8 — 산출물에 남은 진짜 세계 개선 절의 수"],
        "산출물": str(OUT), "초": out["초"]}, ensure_ascii=False))


def main() -> None:
    t0 = time.time()
    tstart = dt.datetime.now(dt.timezone.utc)
    z = np.load(SCRATCH / "daily.npz", allow_pickle=False)
    V = z["V"].astype(np.float64)
    C = z["C"]
    grids = z["grids"].tolist()
    OBS = C > 0
    G, D = V.shape
    assert D == NDAY, (D, NDAY)

    qualify = OBS.mean(axis=1) >= OBS_MIN_FRAC
    base, r, ok = baseline_ratio(V, OBS)
    ok = ok & qualify[:, None]

    out = {
        "팔": "922-ㅎ (918 의 순열 바닥 수리)",
        "사전등록": "docs/prereg_922_permfix.md",
        "사전등록 mtime(UTC)": dt.datetime.fromtimestamp(
            (ROOT / "docs/prereg_922_permfix.md").stat().st_mtime,
            dt.timezone.utc).isoformat(timespec="seconds"),
        "🔴 판 ρ": "한 번도 안 돌렸다. 이 팔의 자는 「간격 예측이 기후값을 이기나」 하나다",
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/perm922.py", "runners/perm922_run.py",
                        "state/interval918.py")},
        "코드 mtime(UTC)": {c: dt.datetime.fromtimestamp(
            (ROOT / c).stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds")
            for c in ("docs/prereg_922_permfix.md", "state/perm922.py",
                      "runners/perm922_run.py")},
        "입력 sha256": {"daily.npz": sha256_text(SCRATCH / "daily.npz")},
        "설정": {"τ": TAU_PRIMARY, "기저선 lag": list(BASE_LAGS),
               "셀 최소 학습행": CELL_MIN, "B": B, "seed": SEED,
               "분할": f"격자 sha256('{SPLIT_SALT}'+격자) 70/30",
               "정지 계수(기본 0.01)": STOP_COEF,
               "비교가능성 문턱(상대)": COMPARABLE_REL,
               "반폭 상한": HALFWIDTH_CAP},
        "🔴 분모 딱지": {
            "격자(전체)": G, "날짜": D, "칸": G * D,
            "관측 칸(행이 있었나)": int(OBS.sum()),
            "자격 격자(관측률 ≥0.95)": int(qualify.sum()),
            "기저선이 정의된 칸(자격 격자 안)": int(ok.sum()),
            "🔴 이 다섯은 전부 다른 분모다": True},
        "🔴 안 한 것(「없다」가 아니라 「안 했다」)": [
            "τ 민감도 1.10·1.50 — 918 이 이미 돌렸고 이 팔은 바닥만 고친다",
            "「큰 격자만」 민감도 절 — 안 돌렸다",
            "덮음은 진짜 세계에서만 낸다(귀무 세계 덮음은 안 냈다)",
        ],
    }

    # ── 분할 ─────────────────────────────────────────────────────────────
    tr_g, ho_g = split_grids(grids)
    assert not (tr_g & ho_g), "🔴 W2 — 학습 ∩ 홀드아웃 이 비지 않았다"
    tr_set = np.zeros(G, bool)
    ho_set = np.zeros(G, bool)
    gidx = {g: i for i, g in enumerate(grids)}
    for g in tr_g:
        tr_set[gidx[g]] = True
    for g in ho_g:
        ho_set[gidx[g]] = True
    out["분할"] = {"학습 격자": len(tr_g), "홀드아웃 격자": len(ho_g),
                 "🔴 겹침(assert)": len(tr_g & ho_g),
                 "합 == 전체": len(tr_g) + len(ho_g) == G}

    # ── ① 표를 만들고 918 의 표와 열 단위로 대조(W0) ───────────────────────
    first = surges(r, ok, TAU_PRIMARY)
    rdates, rmags = real_events(first, r)
    tab_real = gaps_from_events(rdates, rmags, V, OBS, DAY0)
    tab_918 = events_and_gaps(first, r, V, OBS, grids, [DAY0])
    w0 = same_table(tab_real, tab_918)
    #: 심은 결함 — mag 을 한 칸 굴린다(검사가 원리상 발화하는지 본다)
    bad_mags = [rmags[(g + 1) % G] if rmags[(g + 1) % G].size == rmags[g].size
                else rmags[g] for g in range(G)]
    tab_bad = gaps_from_events(rdates, bad_mags, V, OBS, DAY0)
    w0_plant = same_table(tab_bad, tab_918)
    out["🔴 배선 W0 — 내 표가 918 의 표와 같은가"] = {
        "음성 대조(안 심음)": w0,
        "심은 결함(mag 을 한 칸 굴림) → 붉어져야 한다": {
            "mag 열이 같다고 나오나": w0_plant["mag"],
            "발화했나": (w0_plant["mag"] is False)},
    }
    assert w0["전부 같다"], f"🔴 W0 실패 — 내 표가 918 의 표와 다르다: {w0}"

    # ── ② 진짜 세계의 **기후값 팔만** (개선 수는 아직 계산 안 한다) ─────────
    real_lite = measure(tab_real, tr_set, ho_set, world="진짜",
                        arms=["가 기후값"], do_boot=False)
    out["② 진짜 세계 — 기후값 팔만(정지 관문 전에 아는 것)"] = real_lite

    # ── ③ 주 귀무 N2 를 **먼저** 돌린다 ───────────────────────────────────
    n2d, n2m, n2moved = null_n2_gap_order(first, r, seed=922)
    tab_n2 = gaps_from_events(n2d, n2m, V, OBS, DAY0)
    n2 = measure(tab_n2, tr_set, ho_set, world="N2 간격순서 순열",
                 arms=["가 기후값", "나 조건부(주)"])
    n2["🔴 간격 순서가 실제로 바뀐 격자 비율"] = n2moved
    n2["🔴 격자별 간격 다중집합 보존(설계 주장)"] = gap_multiset_same(rdates, n2d)
    cmp_n2 = comparability(real_lite, n2)
    out["③ 주 귀무 N2 — 간격순서 순열(발생률·급증 크기 보존 · 순서만 파괴)"] = n2
    out["③ 🔴 비교가능성 관문 — N2 대 진짜"] = cmp_n2

    nb = n2["🔴 자 — MAE(기후값) − MAE(팔)"]["나 조건부(주)"]["🔴 군집 부트스트랩(규약 47)"]
    mde = nb["🔴 반폭(=MDE 자리)"]
    climate_null = n2["가 기후값"]["MAE"]
    stop = bool(mde >= STOP_COEF * climate_null)
    out["⓪ 정지 관문"] = {
        "규칙": "MDE_실측 ≥ 계수 × 기후값MAE(주 귀무 N2) 이면 진짜 비교를 계산하지 않고 멈춘다",
        "계수": STOP_COEF,
        "MDE_실측(N2 BCa 반폭 · 일)": mde,
        "기후값 MAE(N2 · 일)": climate_null,
        "문턱": STOP_COEF * climate_null,
        "🔴 멈췄나": stop,
        "🔴 이 관문의 지위(사전등록 §5 자백)":
            "살아 있는 관문이 아니라 배선 시험이다 — 진짜 비교값은 918 이 이미 공표했고 "
            "나는 ⓪ 전에 재현했다. 「계산하지 않았다」를 결론으로 쓰지 않는다",
    }
    if stop:
        out["🔴 판정"] = ("멈췄다 — 진짜 조건부 예측기를 **계산하지 않았다**. "
                       "🔴 이 판에서 진짜 세계 개선 절의 수는 0 이어야 한다(#176)")
        finish(out, t0, tstart)          # 🔴 918 의 병 — 여기서 **함수가 끝난다**
        return

    # ── ④ 진짜 비교 (관문을 통과했을 때만) ────────────────────────────────
    real = measure(tab_real, tr_set, ho_set, world="진짜",
                   arms=["가 기후값", "나 조건부(주)", "다 조건부(보조)", "라 무정보"],
                   do_cov=True)
    rb = real["🔴 자 — MAE(기후값) − MAE(팔)"]["나 조건부(주)"]["🔴 군집 부트스트랩(규약 47)"]
    out["④ 진짜 비교"] = real
    out["④ 🔴 자기시험 — 918 정본과 소수점까지 같은가"] = {
        "정본": CANON,
        "이번": {"개선(일)": rb["점추정"], "lo": rb["lo"], "hi": rb["hi"],
               "홀드아웃 간격": real["홀드아웃 간격 수(분모)"],
               "홀드아웃 격자": real["홀드아웃 격자(군집) 수"],
               "학습 간격": real["표(학습)"]["학습 간격 수(분모)"],
               "사건 수": real["🔴 사건 수(분모 A)"],
               "간격 수": real["🔴 간격 수(분모 B)"]},
        "🔴 전부 같다": bool(
            rb["점추정"] == CANON["개선(일)"] and rb["lo"] == CANON["lo"]
            and rb["hi"] == CANON["hi"]
            and real["홀드아웃 간격 수(분모)"] == CANON["홀드아웃 간격"]
            and real["홀드아웃 격자(군집) 수"] == CANON["홀드아웃 격자"]
            and real["표(학습)"]["학습 간격 수(분모)"] == CANON["학습 간격"]),
    }

    # ── ⑤ N1(‘r’ 도 섞는 순열) 과 N0(옛 귀무 · 심은 결함) ─────────────────
    n1d, n1m, n1moved = null_n1_shuffle_r(first, r, ok, seed=SEED, mag_seed=922)
    tab_n1 = gaps_from_events(n1d, n1m, V, OBS, DAY0)
    n1 = measure(tab_n1, tr_set, ho_set, world="N1 r 도 섞는 순열",
                 arms=["가 기후값", "나 조건부(주)"])
    n1["🔴 순열이 실제로 섞였나(격자 비율)"] = n1moved
    cmp_n1 = comparability(real_lite, n1)
    out["⑤ 귀무 N1 — r 도 섞는 순열(사전등록 918 §5-바 가 원래 적은 것)"] = n1
    out["⑤ 🔴 비교가능성 관문 — N1 대 진짜"] = cmp_n1

    n0d, n0m, n0moved, _ = null_n0_old(first, r, ok, seed=SEED)
    tab_n0 = gaps_from_events(n0d, n0m, V, OBS, DAY0)
    n0 = measure(tab_n0, tr_set, ho_set, world="N0 옛 귀무(918 · r 을 안 섞는다)",
                 arms=["가 기후값", "나 조건부(주)"])
    n0["🔴 순열이 실제로 섞였나(격자 비율)"] = n0moved
    cmp_n0 = comparability(real_lite, n0)
    out["⑤ 귀무 N0 — 🔴 918 의 옛 귀무. **판정에 안 쓴다. 심은 결함이다**"] = n0
    out["⑤ 🔴 비교가능성 관문 — N0 대 진짜 (W7 이 붉어져야 하는 자리)"] = cmp_n0
    out["⑤ 🔴 N0 과 N1 의 유일한 차이"] = (
        "날짜 순열이 **같은 permute_events(seed=918)** 이고, 다른 것은 mag 뿐이다 — "
        "N0 은 새 날짜의 r 을 다시 읽고, N1 은 그 격자의 진짜 사건 mag 다중집합을 섞어 붙인다")

    # ── 🔴 진단(판정 미사용 · 사전등록 §6 의 자가 아니다) — 격자로 짝지은 차 ──
    def _per_grid(v, g):
        o = np.argsort(g, kind="stable")
        gs, vs = g[o], v[o]
        b = np.flatnonzero(np.r_[True, gs[1:] != gs[:-1]])
        keys = gs[b]
        means = np.asarray([vs[a:c].mean() for a, c in
                            zip(b, np.r_[b[1:], gs.size])])
        return dict(zip(keys.tolist(), means.tolist()))

    diag = {}
    ri, rg = real["_imp"]["나 조건부(주)"]
    pr = _per_grid(ri, rg)
    for nm, world in (("N2", n2), ("N1", n1), ("N0", n0)):
        ni, ng = world["_imp"]["나 조건부(주)"]
        pn = _per_grid(ni, ng)
        common = sorted(set(pr) & set(pn))
        dv = np.asarray([pr[k] - pn[k] for k in common], float)
        diag[nm] = {"격자(분모)": len(common),
                    "격자 평균의 차 평균(일)": float(dv.mean()),
                    "🔴 군집 부트스트랩(격자 단위 · 규약 47)":
                        boot(dv, np.arange(len(common)), B=B, seed=SEED)}
    out["🔴 진단 — 진짜 − 귀무 (격자로 짝지었다 · 판정에 안 쓴다)"] = {
        "🔴 이 절은 사전등록 §6 의 자가 아니다": "진단이다. 판정은 §6 으로만 한다",
        "결과": diag}

    # ── ⑥ 배선 회계 — 🔴 모든 검정력에 분모를 붙인다 ───────────────────────
    from state.interval918 import permute_events as _pe
    _, moved_id = _pe(first, ok, seed=SEED, plant_identity=True)
    tr_leak, ho_leak2 = split_grids(grids, plant_leak=True)
    n2bd, n2bm, _ = null_n2_gap_order(first, r, seed=922, plant_break_multiset=True)
    w9_plant = gap_multiset_same(rdates, n2bd)
    w9_neg = gap_multiset_same(rdates, n2d)

    checks = {
        "W0 표 동치": {
            "심었나": True, "발화했나": (w0_plant["mag"] is False),
            "음성 대조 통과": bool(w0["전부 같다"]),
            "심은 결함": "mag 을 격자 한 칸 굴렸다"},
        "W2 분할 누설": {
            "심었나": True,
            "발화했나": bool(len(tr_leak & ho_leak2) > 0),
            "음성 대조 통과": bool(len(tr_g & ho_g) == 0),
            "심은 결함": "홀드아웃 격자 하나를 학습에도 넣었다",
            "겹친 격자 수": int(len(tr_leak & ho_leak2))},
        "W5 순열이 섞였나": {
            "심었나": True, "발화했나": bool(moved_id == 0.0),
            "음성 대조 통과": bool(n1moved > 0.9),
            "심은 결함": "항등 순열(plant_identity=True)",
            "심은 판의 섞인 비율": float(moved_id),
            "안 심은 판의 섞인 비율": float(n1moved)},
        "🔴 W7 비교가능성(#175 처방 2 · 신설)": {
            "심었나": True,
            "발화했나": bool(not cmp_n0["🔴 통과"]),
            "심은 결함": "N0 = 918 의 옛 귀무(r 을 안 섞는다)",
            "심은 판의 상대차": cmp_n0["🔴 상대차"],
            "음성 대조(N2)의 상대차": cmp_n2["🔴 상대차"],
            "음성 대조 통과(N2 가 문턱 안인가)": bool(cmp_n2["🔴 통과"]),
            "N1 의 상대차": cmp_n1["🔴 상대차"],
            "N1 이 문턱 안인가": bool(cmp_n1["🔴 통과"])},
        "🔴 W9 N2 의 간격 다중집합 보존(신설)": {
            "심었나": True,
            "발화했나": bool(not w9_plant["통과"]),
            "음성 대조 통과": bool(w9_neg["통과"]),
            "심은 결함": "간격 하나를 +1 해서 다중집합을 깬다",
            "심은 판": w9_plant, "안 심은 판": w9_neg},
    }
    planted = len(checks)
    fired = sum(1 for v in checks.values() if v["발화했나"])
    out["⑥ 배선 검사"] = {
        "검사": checks,
        "🔴 심은 수": planted, "🔴 발화한 수": fired,
        "🔴 놓친 수": planted - fired,
        "🔴 검정력": f"{fired}/{planted} = {fired/planted:.3f} — "
                 f"🔴 **분모는 {planted} 이고 관문 전체가 아니다**(#176)",
        "🔴 W8(정지 관문)은 이 판에 없다":
            "별도 판(G922_STOP_COEF 를 올린 강제 발화 판)에서만 잴 수 있다. "
            "이 판에서는 「진짜 세계 개선 절의 수 > 0」만 확인한다",
        "🔴 못 심은 것(검정력 0 으로 신고)": [
            "「N2 가 시각 구조 **만** 부수는가」 — 달력(요일·분기)과의 짝도 같이 깨진다. "
            "그것만 따로 심어서 확인하는 검사를 **못 만들었다**",
        ],
    }

    # ── ⑦ 판정 (사전등록 §6) ─────────────────────────────────────────────
    n2b = n2["🔴 자 — MAE(기후값) − MAE(팔)"]["나 조건부(주)"]["🔴 군집 부트스트랩(규약 47)"]
    n1b = n1["🔴 자 — MAE(기후값) − MAE(팔)"]["나 조건부(주)"]["🔴 군집 부트스트랩(규약 47)"]
    n0b = n0["🔴 자 — MAE(기후값) − MAE(팔)"]["나 조건부(주)"]["🔴 군집 부트스트랩(규약 47)"]
    out["⑦ 판정 재료(사전등록 §6)"] = {
        "진짜 개선(일)": rb["점추정"], "진짜 BCa": [rb["lo"], rb["hi"]],
        "진짜 판정": rb["판정"],
        "진짜 개선율": real["🔴 자 — MAE(기후값) − MAE(팔)"]["나 조건부(주)"][
            "🔴 개선율(그 세계의 기후값 MAE 로 나눈 수)"],
        "N2 개선(일)": n2b["점추정"], "N2 BCa": [n2b["lo"], n2b["hi"]],
        "N2 판정": n2b["판정"], "N2 반폭": n2b["🔴 반폭(=MDE 자리)"],
        "N2 개선율": n2["🔴 자 — MAE(기후값) − MAE(팔)"]["나 조건부(주)"][
            "🔴 개선율(그 세계의 기후값 MAE 로 나눈 수)"],
        "N2 비교가능성 통과": cmp_n2["🔴 통과"], "N2 상대차": cmp_n2["🔴 상대차"],
        "N1 개선(일)": n1b["점추정"], "N1 BCa": [n1b["lo"], n1b["hi"]],
        "N1 판정": n1b["판정"], "N1 반폭": n1b["🔴 반폭(=MDE 자리)"],
        "N1 비교가능성 통과": cmp_n1["🔴 통과"], "N1 상대차": cmp_n1["🔴 상대차"],
        "N0(판정 미사용) 개선(일)": n0b["점추정"],
        "N0 BCa": [n0b["lo"], n0b["hi"]],
        "N0 비교가능성 통과": cmp_n0["🔴 통과"], "N0 상대차": cmp_n0["🔴 상대차"],
        "🔴 구간이 겹치나 — 진짜 대 N2": bool(
            not (rb["lo"] > n2b["hi"] or n2b["lo"] > rb["hi"])),
        "🔴 구간이 겹치나 — 진짜 대 N1": bool(
            not (rb["lo"] > n1b["hi"] or n1b["lo"] > rb["hi"])),
        "🔴 반폭 상한(0.7545) 을 넘은 귀무": [
            k for k, v in (("N2", n2b), ("N1", n1b))
            if v["🔴 반폭(=MDE 자리)"] > HALFWIDTH_CAP],
    }

    # ── ⑦ 판정문 — 사전등록 §6 을 **기계로** 적용한다 ──────────────────────
    overlap = not (rb["lo"] > n2b["hi"] or n2b["lo"] > rb["hi"])
    if not cmp_n2["🔴 통과"]:
        verdict_txt = ("§6-4 — 주 귀무 N2 가 비교가능성 관문에 걸렸다. "
                       "「N2 로도 못 가른다」 · ③ 은 **판정 불능**으로 남는다")
    elif n2b["🔴 반폭(=MDE 자리)"] > HALFWIDTH_CAP:
        verdict_txt = ("§6-2 단서 — N2 의 반폭이 0.7545 를 넘는다. "
                       "「0 을 문다」를 근거로 못 쓴다 · **못 가른다**")
    elif n2b["lo"] <= 0 <= n2b["hi"] and rb["lo"] > 0:
        verdict_txt = ("🔴 §6-1 — N2 의 BCa 가 0 을 물고 진짜의 lo > 0 이다. "
                       "**③ 이 처음으로 0 을 벗어난다**")
    elif n2b["lo"] > 0 and n2b["점추정"] >= rb["점추정"]:
        verdict_txt = ("🔴 §6-2 — N2 가 진짜를 이긴다. "
                       "**「이 표로는 못 잰다」가 확정된다** — 표를 바꿔야 한다")
    elif n2b["lo"] > 0 and n2b["점추정"] < rb["점추정"] and not overlap:
        verdict_txt = ("🔴 §6-3 — N2 의 lo > 0 이지만 점추정이 진짜보다 낮고 "
                       "두 구간이 **안 겹친다**. **신호가 바닥 위에 있다 → ③ 이 0 을 벗어난다**")
    else:
        verdict_txt = ("§6-3 뒷갈래 — 두 구간이 겹친다. "
                       "「못 이긴다」가 아니라 **「못 이긴다와 못 잰다를 못 가른다」**")
    out["🔴 판정 (사전등록 §6 을 기계로 적용)"] = {
        "판정문": verdict_txt,
        "쓴 갈래의 재료": {
            "N2 비교가능성 통과": cmp_n2["🔴 통과"],
            "N2 BCa": [n2b["lo"], n2b["hi"]], "N2 점추정": n2b["점추정"],
            "진짜 BCa": [rb["lo"], rb["hi"]], "진짜 점추정": rb["점추정"],
            "구간이 겹치나": overlap,
            "N2 반폭": n2b["🔴 반폭(=MDE 자리)"]},
        "🔴 N1 은 판정에 안 썼다": (
            f"N1 의 기후값 MAE 상대차가 {cmp_n1['🔴 상대차']:.4f} 로 문턱 0.05 를 넘는다 "
            "— 사전등록 §6-5 대로 병기만 한다"),
        "🔴 첫 양수를 채택하지 않았다(노트 133)":
            "N2·N1·N0 셋을 다 재고, 그중 비교가능성 관문을 통과한 하나로만 판정했다",
    }

    finish(out, t0, tstart)


if __name__ == "__main__":
    main()
