# -*- coding: utf-8 -*-
"""팔 918-ㅌ · 1~3단계 — **간격 예측이 기후값을 이기나** (사전등록 `docs/prereg_918_interval.md`).

🔴 순서가 규약이다(사전등록 §2 정지 규칙):
    ① 사건·간격 표를 만든다  → ② **순열 귀무를 먼저** 돌려 실측 MDE 를 낸다
    → ③ 정지 규칙을 건다     → ④ 통과할 때만 진짜 비교를 계산한다
915 는 이 순서가 없어서 원리상 못 가르는 자리까지 갔다.

산출물: runners/out918_interval.json
사용:   python3 runners/interval918_run.py            (주 판정)
        G918_B=500 python3 runners/interval918_run.py (부트 횟수만 바꾼다 · 파일은 안 고친다)
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
                               OBS_MIN_FRAC, SPLIT_SALT, TAU_PRIMARY, TAU_SENS,
                               baseline_ratio, boot, coverage, events_and_gaps,
                               fit_tables, permute_events, predict,
                               sha256_text, split_grids, surges)

SCRATCH = Path(os.environ.get(
    "G918_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad")) / "g918"
OUT = ROOT / f"runners/out918_interval{os.environ.get('G918_TAG','')}.json"
B = int(os.environ.get("G918_B", "2000"))
SEED = int(os.environ.get("G918_SEED", "918"))


def _mask_of(tab, grids, keep: set) -> np.ndarray:
    gi = tab["gi"]
    keepv = np.zeros(len(grids), bool)
    for g in keep:
        keepv[grids.index(g)] = True
    return keepv[gi]


def compare(tab, grids, tr_mask, ho_mask, *, arms, plant_ignore_state=False,
            plant_const_cal=False, plant_oracle=False, do_boot=True,
            do_cov=True):
    T = fit_tables(tab, tr_mask, plant_const_cal=plant_const_cal)
    gap = tab["gap"][ho_mask].astype(float)
    gi = tab["gi"][ho_mask]
    res = {"표(학습)": {k: T[k] for k in
                     ("학습 간격 수(분모)", "전체 중앙값", "🔴 달력 셀 가짓수",
                      "🔴 3수준 셀 가짓수", "mag 3분위 경계", "prevmed 3분위 경계",
                      "전체 10~90분위")},
           "홀드아웃 간격 수(분모)": int(ho_mask.sum()),
           "홀드아웃 격자(군집) 수": int(len(np.unique(gi)))}
    preds, errs = {}, {}
    for a in arms:
        p, back = predict(tab, ho_mask, T, arm=a,
                          plant_ignore_state=plant_ignore_state,
                          plant_oracle=(plant_oracle and a == "나 조건부(주)"))
        preds[a] = p
        errs[a] = np.abs(gap - p)
        res[a] = {"MAE": float(errs[a].mean()),
                  "MedAE": float(np.median(errs[a])),
                  "후퇴 회계": back}
    base = errs["가 기후값"]
    res["🔴 자 — MAE(기후값) − MAE(팔)"] = {}
    for a in arms:
        if a == "가 기후값":
            continue
        imp = base - errs[a]
        cell = {"개선(일)": float(imp.mean()),
                "개선율": float(imp.mean() / base.mean()) if base.mean() > 0 else None}
        if do_boot:
            cell["🔴 군집 부트스트랩(규약 47)"] = boot(imp, gi, B=B, seed=SEED)
        res["🔴 자 — MAE(기후값) − MAE(팔)"][a] = cell
        res.setdefault("_imp", {})[a] = (imp, gi)
    #: 🔴 W4 — 상태 열이 정말 예측에 닿았나(예측 벡터가 기후값과 다른가)
    if "나 조건부(주)" in arms:
        d = preds["나 조건부(주)"] - preds["가 기후값"]
        res["🔴 배선 — 상태 열이 예측을 움직였나"] = {
            "다른 행": int((d != 0).sum()), "분모": int(d.size),
            "다른 행 비율": float((d != 0).mean()),
            "통과": bool((d != 0).any())}
    if do_cov:
        res["🔴 덮음"] = {"가 기후값": coverage(tab, ho_mask, T, which="달력"),
                       "나 조건부(주)": coverage(tab, ho_mask, T, which="조건부")}
    return res


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

    obs_frac = OBS.mean(axis=1)
    qualify = obs_frac >= OBS_MIN_FRAC              # 사전등록 §4-5
    base, r, ok = baseline_ratio(V, OBS)
    ok = ok & qualify[:, None]

    out = {
        "팔": "918-ㅌ",
        "사전등록": "docs/prereg_918_interval.md",
        "사전등록 mtime(UTC)": dt.datetime.fromtimestamp(
            (ROOT / "docs/prereg_918_interval.md").stat().st_mtime,
            dt.timezone.utc).isoformat(timespec="seconds"),
        "🔴 판 ρ": "한 번도 안 돌렸다. 이 팔의 자는 「간격 예측이 기후값을 이기나」 하나다",
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/interval918.py", "runners/interval918_run.py",
                        "runners/interval918_build.py")},
        "코드 mtime(UTC)": {c: dt.datetime.fromtimestamp(
            (ROOT / c).stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds")
            for c in ("state/interval918.py", "runners/interval918_run.py")},
        "입력 sha256": {"daily.npz": sha256_text(SCRATCH / "daily.npz")},
        "설정": {"τ 주": TAU_PRIMARY, "τ 민감도": list(TAU_SENS),
               "기저선 lag": list(BASE_LAGS), "셀 최소 학습행": CELL_MIN,
               "분할": f"격자 sha256('{SPLIT_SALT}'+격자) 70/30", "B": B, "seed": SEED},
        "🔴 분모 딱지": {
            "격자(전체)": G, "날짜": D, "칸": G * D,
            "관측 칸(행이 있었나)": int(OBS.sum()),
            "자격 격자(관측률 ≥0.95)": int(qualify.sum()),
            "기저선이 정의된 칸(자격 격자 안)": int(ok.sum()),
            "🔴 이 다섯은 전부 다른 분모다": True,
        },
    }

    # ── 분할 ────────────────────────────────────────────────────────────
    tr_g, ho_g = split_grids(grids)
    assert not (tr_g & ho_g), "🔴 W2 — 학습 ∩ 홀드아웃 이 비지 않았다"
    out["분할"] = {"학습 격자": len(tr_g), "홀드아웃 격자": len(ho_g),
                 "🔴 겹침(assert)": len(tr_g & ho_g),
                 "합 == 전체": len(tr_g) + len(ho_g) == G}
    tr_set = np.zeros(G, bool)
    ho_set = np.zeros(G, bool)
    gidx = {g: i for i, g in enumerate(grids)}
    for g in tr_g:
        tr_set[gidx[g]] = True
    for g in ho_g:
        ho_set[gidx[g]] = True

    out["팔별"] = {}
    for tau in (TAU_PRIMARY,) + TAU_SENS:
        key = f"τ={tau}" + (" 🔴 주" if tau == TAU_PRIMARY else " (민감도)")
        first = surges(r, ok, tau)
        tab = events_and_gaps(first, r, V, OBS, grids, [DAY0])
        trm = tr_set[tab["gi"]]
        hom = ho_set[tab["gi"]]
        sec = {"🔴 사건 수(분모 A)": tab["🔴 사건 수(분모 A)"],
               "🔴 간격 수(분모 B)": tab["🔴 간격 수(분모 B)"],
               "사건이 1개 이상인 격자": tab["🔴 사건이 1개 이상인 격자"],
               "간격이 1개 이상인 격자": tab["🔴 간격이 1개 이상인 격자"],
               "간격 중앙값": float(np.median(tab["gap"])) if tab["gap"].size else None,
               "간격 SD": float(tab["gap"].std()) if tab["gap"].size else None,
               "학습 간격": int(trm.sum()), "홀드아웃 간격": int(hom.sum())}

        if tau == TAU_PRIMARY:
            # ── ② 순열 귀무를 **먼저** 돌린다 ──────────────────────────
            pfirst, moved = permute_events(first, ok, seed=SEED)
            ptab = events_and_gaps(pfirst, r, V, OBS, grids, [DAY0])
            ptrm = tr_set[ptab["gi"]]
            phom = ho_set[ptab["gi"]]
            null = compare(ptab, grids, ptrm, phom,
                           arms=["가 기후값", "나 조건부(주)"], do_cov=False)
            null["🔴 순열이 실제로 섞였나(격자 비율)"] = float(moved)
            nb = null["🔴 자 — MAE(기후값) − MAE(팔)"]["나 조건부(주)"][
                "🔴 군집 부트스트랩(규약 47)"]
            mde = nb["🔴 반폭(=MDE 자리)"]
            climate_mae_null = null["가 기후값"]["MAE"]
            stop = bool(mde >= 0.01 * climate_mae_null)
            sec["🔴 ② 순열 귀무(진짜 비교보다 먼저 돌렸다)"] = null
            sec["⓪ 정지 규칙"] = {
                "규칙": "MDE_실측 ≥ 0.01 × 기후값MAE(귀무) 이면 진짜 비교를 계산하지 않고 멈춘다",
                "MDE_실측(귀무 BCa 반폭 · 일)": mde,
                "기후값 MAE(귀무 · 일)": climate_mae_null,
                "문턱 = 0.01 × 기후값MAE(귀무)": 0.01 * climate_mae_null,
                "🔴 멈췄나": stop,
                "사전 추정 MDE(사전등록 §2)": 0.04,
            }
            if stop:
                sec["🔴 판정"] = ("멈췄다 — 이 자는 1% 상대개선을 원리상 못 가른다. "
                              "진짜 조건부 예측기를 **계산하지 않았다**(사전등록 §2)")
                out["팔별"][key] = sec
                break
            # ── ④ 진짜 비교 ────────────────────────────────────────────
            real = compare(
                tab, grids, trm, hom,
                arms=["가 기후값", "나 조건부(주)", "다 조건부(보조)", "라 무정보"])
            # ── 🔴 진단(판정 미사용 · 사전등록에 없다) — 실제가 귀무를 얼마나 넘나 ──
            ri, rg = real["_imp"]["나 조건부(주)"]
            ni, ng_ = null["_imp"]["나 조건부(주)"]
            def _per_grid(v, g):
                o = np.argsort(g, kind="stable")
                gs, vs = g[o], v[o]
                b = np.flatnonzero(np.r_[True, gs[1:] != gs[:-1]])
                keys = gs[b]
                means = np.asarray([vs[a:c].mean() for a, c in
                                    zip(b, np.r_[b[1:], gs.size])])
                return dict(zip(keys.tolist(), means.tolist()))
            pr, pn = _per_grid(ri, rg), _per_grid(ni, ng_)
            common = sorted(set(pr) & set(pn))
            dv = np.asarray([pr[k] - pn[k] for k in common], float)
            sec["🔴 진단 — 실제 − 순열귀무 (판정에 안 쓴다)"] = {
                "🔴 이 절은 사전등록 §6 의 자가 아니다": "진단이다. 판정은 §6-1 로만 한다",
                "격자(분모)": len(common),
                "격자 평균의 차 평균(일)": float(dv.mean()),
                "🔴 군집 부트스트랩(격자 단위 · 규약 47)":
                    boot(dv, np.arange(len(common)), B=B, seed=SEED),
            }
            real.pop("_imp", None)
            null.pop("_imp", None)
            sec["🔴 ④ 진짜 비교"] = real
        else:
            sec["진짜 비교(민감도 · 덮음 생략)"] = compare(
                tab, grids, trm, hom,
                arms=["가 기후값", "나 조건부(주)"], do_cov=False)
        out["팔별"][key] = sec

    # ── 민감도: 큰 격자만(사전등록 §4-5) ────────────────────────────────
    first = surges(r, ok, TAU_PRIMARY)
    med_lvl = np.array([np.median(V[g][OBS[g]]) if OBS[g].any() else 0.0
                        for g in range(G)])
    thr = float(np.median(med_lvl[tr_set & qualify]))
    big = med_lvl >= thr
    okb = ok & big[:, None]
    fb = surges(r, okb, TAU_PRIMARY)
    tabb = events_and_gaps(fb, r, V, OBS, grids, [DAY0])
    out["민감도 — 큰 격자만"] = {
        "문턱(학습 자격격자 일중앙값의 중앙값)": thr,
        "격자 수": int((big & qualify).sum()),
        "🔴 간격 수(분모)": tabb["🔴 간격 수(분모 B)"],
        "결과": compare(tabb, grids, tr_set[tabb["gi"]], ho_set[tabb["gi"]],
                      arms=["가 기후값", "나 조건부(주)"], do_cov=False),
    }

    def scrub(o):
        if isinstance(o, dict):
            return {k: scrub(v) for k, v in o.items() if k != "_imp"}
        if isinstance(o, (list, tuple)):
            return [scrub(x) for x in o]
        return o
    out = scrub(out)
    out["시작 UTC"] = tstart.isoformat(timespec="seconds")
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    k = f"τ={TAU_PRIMARY} 🔴 주"
    print(json.dumps(out["팔별"][k].get("⓪ 정지 규칙", {}), ensure_ascii=False))
    real = out["팔별"][k].get("🔴 ④ 진짜 비교")
    if real:
        print(json.dumps(real["🔴 자 — MAE(기후값) − MAE(팔)"], ensure_ascii=False)[:800])


if __name__ == "__main__":
    main()
