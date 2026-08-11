# -*- coding: utf-8 -*-
"""팔 925-ㄱㄱ — **빈틈의 이름을 확정한다** (사전등록 `docs/prereg_925_gapsplit.md`).

🔴 순서가 규약이다:
    ① 표 대조(W0) · N2 재구현이 922 와 비트로 같은가(W1b)
    → ② 자기시험 S1~S3 (918·922 정본 재현) — 🔴 **안 맞으면 §6-다 로 멈춘다**
    → ③ 🔴 **G4 항등 N2**(심은 결함 W1a) — 안 발화하면 §6-라 로 멈춘다
    → ④ 절제 넷 × 세계 둘 = **여덟 수** · 티처 여덟 수 재현(S4)
    → ⑤ prevmed 결측 절 · §7 바닥 내리기 · §8 구간 덮음 눈금
    → ⑥ 배선 회계(분모 둘) → ⑦ 판정(사전등록 §6 을 기계로 적용)

산출물: runners/out925_gapsplit.json
사용:   python3 runners/gap925_run.py
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
from state.perm922 import (gap_multiset_same, gaps_from_events,  # noqa: E402
                           null_n2_gap_order, real_events, same_table)
from state.gap925 import (ALPHAS, CAL_PCT, CAL_SALT, COV_TOL, NOMINAL,  # noqa: E402
                          PANEL_DEF, PANELS, build_intervals, coverage_at,
                          dates_bitwise_same, gate_report, gate_separation,
                          null_n2_plantable, predict_grid_aware, split_cal)

SCRATCH = Path(os.environ.get(
    "G925_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/"
    "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad"))
NPZ = Path(os.environ.get("G925_NPZ", str(SCRATCH / "g922/daily.npz")))
TAG = os.environ.get("G925_TAG", "")
OUT = ROOT / f"runners/out925_gapsplit{TAG}.json"
B = int(os.environ.get("G925_B", "2000"))
SEED = int(os.environ.get("G925_SEED", "918"))

#: 🔴 자기시험 S1~S3 의 대조값 — 918·922 가 공표한 정본(소수점 끝까지)
CANON = {
    "진짜 개선(일)": 0.7545204330866538,
    "진짜 lo": 0.6436055429260724,
    "진짜 hi": 0.8861167731832372,
    "N2 개선(일)": 0.28271845721993366,
    "N2 lo": 0.23746212640592873,
    "N2 hi": 0.33138488905691077,
    "홀드아웃 간격": 54862,
    "홀드아웃 격자(군집)": 2277,
    "학습 간격": 121908,
    "사건 수": 185070,
    "간격 수": 176770,
    "덮음 기후값": 0.904724581677664,
    "덮음 조건부": 0.8795705588567679,
}

#: 🔴 S4 — 티처 #73 C1 이 사후에 낸 여덟 수. **정본이 아니다.** 내가 재서 대조한다
TEACHER = {
    ("원판", "진짜"): 0.754520433, ("원판", "N2"): 0.282718457,
    ("첫간격제외", "진짜"): 0.4479, ("첫간격제외", "N2"): 0.2062,
    ("달력제거", "진짜"): 0.323803361, ("달력제거", "N2"): 0.219004047,
    ("둘 다", "진짜"): 0.2165, ("둘 다", "N2"): 0.1986,
}
TEACHER_EXPECTED_GAP = -0.0214          # [둘 다] 판의 기대 빈틈(티처 수)


def _f(x):
    return None if x is None else float(x)


# ────────────────────────────────────────────── 한 세계 × 한 달력설정을 통째로 잰다
def world_pack(tab, tr_set, ho_set, *, world: str, cal_off: bool, with_extra: bool):
    """표 → 학습표 → 홀드아웃 예측. 🔴 절제 「첫간격제외」는 **여기서 안 한다**(자 계산에서 한다)."""
    trm = tr_set[tab["gi"]]
    hom = ho_set[tab["gi"]]
    T = fit_tables(tab, trm, plant_const_cal=cal_off)
    gap = tab["gap"][hom].astype(float)
    gi = tab["gi"][hom]
    prv = tab["prevmed"][hom]
    arms = {}
    for a in ("가 기후값", "나 조건부(주)"):
        p, back = predict(tab, hom, T, arm=a)
        arms[a] = {"pred": p, "err": np.abs(gap - p), "후퇴 회계": back}
    p, back = predict_grid_aware(tab, hom, T)
    arms["가′ 기후값+prevmed"] = {"pred": p, "err": np.abs(gap - p), "후퇴 회계": back}
    if with_extra:
        for a in ("다 조건부(보조)", "라 무정보"):
            p, back = predict(tab, hom, T, arm=a)
            arms[a] = {"pred": p, "err": np.abs(gap - p), "후퇴 회계": back}
    return {
        "세계": world, "달력제거": cal_off, "T": T, "hom": hom, "gap": gap,
        "gi": gi, "prevmed": prv, "arms": arms, "tab": tab,
        "요약": {
            "🔴 사건 수(분모 A)": tab["🔴 사건 수(분모 A)"],
            "🔴 간격 수(분모 B)": tab["🔴 간격 수(분모 B)"],
            "홀드아웃 간격 수(분모)": int(hom.sum()),
            "홀드아웃 격자(군집) 수": int(len(np.unique(gi))),
            "🔴 prevmed 결측 행(분모 · 격자마다 첫 간격)": int((~np.isfinite(prv)).sum()),
            "학습 간격 수(분모)": T["학습 간격 수(분모)"],
            "🔴 달력 셀 가짓수": T["🔴 달력 셀 가짓수"],
            "🔴 3수준 셀 가짓수": T["🔴 3수준 셀 가짓수"],
            "간격 중앙값": float(np.median(tab["gap"])),
            "간격 평균": float(tab["gap"].mean()),
            "MAE": {k: float(v["err"].mean()) for k, v in arms.items()},
        },
    }


def stat(pack, *, drop_first: bool, base="가 기후값", test="나 조건부(주)",
         plant_no_drop: bool = False):
    """자 = MAE(base) − MAE(test). 🔴 「첫간격제외」는 **홀드아웃 부분집합**이고 학습은 안 건드린다."""
    sub = np.ones(pack["gap"].size, bool)
    if drop_first and not plant_no_drop:
        sub = np.isfinite(pack["prevmed"])
    imp = (pack["arms"][base]["err"] - pack["arms"][test]["err"])[sub]
    gi = pack["gi"][sub]
    bb = boot(imp, gi, B=B, seed=SEED)
    return {
        "자": f"MAE({base}) − MAE({test})",
        "행(간격) 수": int(sub.sum()), "군집(격자) 수": int(len(np.unique(gi))),
        "개선(일)": bb["점추정"], "BCa": [bb["lo"], bb["hi"]], "판정": bb["판정"],
        "구간 종류": bb["구간 종류"], "🔴 폴백 사유": bb["🔴 폴백 사유"],
        "반폭": bb["🔴 반폭(=MDE 자리)"], "B": bb["B"],
        "그 판의 기준 팔 MAE": float(pack["arms"][base]["err"][sub].mean()),
        "🔴 개선율(기준 팔 MAE 로 나눈 수)":
            float(imp.mean() / pack["arms"][base]["err"][sub].mean()),
        "_bb": bb,
    }


def _scrub(o):
    if isinstance(o, dict):
        return {k: _scrub(v) for k, v in o.items()
                if not (isinstance(k, str) and k.startswith("_"))}
    if isinstance(o, (list, tuple)):
        return [_scrub(x) for x in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return o


def main() -> None:
    t0 = time.time()
    tstart = dt.datetime.now(dt.timezone.utc)
    out: dict = {
        "팔": "925-ㄱㄱ (빈틈의 이름을 확정한다)",
        "사전등록": "docs/prereg_925_gapsplit.md",
        "이슈": ["#177 (빈틈 분해)", "#178 (관문의 도달 가능 폭 ÷ 문턱)"],
        "🔴 판 ρ": "한 번도 안 돌렸다. 이 팔의 자는 「간격 예측이 기후값을 이기나 · 구간 덮음」 둘이다",
        "🔴 러너 실행 이력 — 자백한다(티처 #73 M2 가 922 에서 잡은 자리)": {
            "완주 횟수": 2,
            "1차": "scratchpad/g925/out925_run1.json (sha256 c80dbfef1191d7e5d67ac2827baddab1"
                  "8651cc12895fd911f3480cf78f86e1d4) · 로그 scratchpad/g925/run1.log",
            "1차 뒤에 고친 것": [
                "§7 에 gate_separation(자′ 로 잰 빈틈 · MDE) 절을 **더했다**",
                "§8 에 「덮음을 맞춘 자리에서의 폭」 진단 곡선을 **더했다**",
                "이 자백 필드를 **더했다**",
            ],
            "🔴 안 고친 것": "팔 · 절제의 정의 · 문턱 · 판정 분기 · 주 판정 판(§3 의 [둘 다]) — "
                       "한 자리도 안 건드렸다. 1차 산출물과 대조하면 확인된다",
        },
        "사전등록 mtime(UTC)": dt.datetime.fromtimestamp(
            (ROOT / "docs/prereg_925_gapsplit.md").stat().st_mtime,
            dt.timezone.utc).isoformat(timespec="seconds"),
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/gap925.py", "runners/gap925_run.py",
                        "state/perm922.py", "state/interval918.py")},
        "코드 mtime(UTC)": {c: dt.datetime.fromtimestamp(
            (ROOT / c).stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds")
            for c in ("docs/prereg_925_gapsplit.md", "state/gap925.py",
                      "runners/gap925_run.py")},
        "입력": {"daily.npz 경로(🔴 저장소 밖이다)": str(NPZ),
               "sha256": sha256_text(NPZ), "바이트": NPZ.stat().st_size},
        "설정": {"τ": TAU_PRIMARY, "기저선 lag": list(BASE_LAGS),
               "셀 최소 학습행": CELL_MIN, "B": B, "seed": SEED,
               "분할": f"격자 sha256('{SPLIT_SALT}'+격자) 70/30",
               "눈금 분할": f"학습 격자를 sha256('{CAL_SALT}'+격자) {CAL_PCT}/{100-CAL_PCT}",
               "α 격자": list(ALPHAS)},
    }

    z = np.load(NPZ, allow_pickle=False)
    V = z["V"].astype(np.float64)
    C = z["C"]
    grids = z["grids"].tolist()
    OBS = C > 0
    G, D = V.shape
    assert D == NDAY, (D, NDAY)
    qualify = OBS.mean(axis=1) >= OBS_MIN_FRAC
    base_arr, r, ok = baseline_ratio(V, OBS)
    ok = ok & qualify[:, None]

    tr_g, ho_g = split_grids(grids)
    assert not (tr_g & ho_g)
    gidx = {g: i for i, g in enumerate(grids)}
    tr_set = np.zeros(G, bool)
    ho_set = np.zeros(G, bool)
    for g in tr_g:
        tr_set[gidx[g]] = True
    for g in ho_g:
        ho_set[gidx[g]] = True
    out["🔴 분모 딱지"] = {
        "격자(전체)": G, "날짜": D, "칸": G * D,
        "관측 칸": int(OBS.sum()), "자격 격자(관측률 ≥0.95)": int(qualify.sum()),
        "기저선이 정의된 칸": int(ok.sum()),
        "학습 격자": len(tr_g), "홀드아웃 격자": len(ho_g),
        "🔴 이 수들은 전부 다른 분모다": True}

    # ── ① 표 · N2 재구현 대조 ────────────────────────────────────────────
    first = surges(r, ok, TAU_PRIMARY)
    rdates, rmags = real_events(first, r)
    tab_real = gaps_from_events(rdates, rmags, V, OBS, DAY0)
    tab_918 = events_and_gaps(first, r, V, OBS, grids, [DAY0])
    w0 = same_table(tab_real, tab_918)
    bad_mags = [rmags[(g + 1) % G] if rmags[(g + 1) % G].size == rmags[g].size
                else rmags[g] for g in range(G)]
    w0_plant = same_table(gaps_from_events(rdates, bad_mags, V, OBS, DAY0), tab_918)
    assert w0["전부 같다"], f"🔴 W0 실패: {w0}"

    n2d, n2m, n2moved, n2have = null_n2_plantable(first, r, seed=922)
    ref_d, ref_m, ref_moved = null_n2_gap_order(first, r, seed=922)
    w1b = dates_bitwise_same(n2d, ref_d)
    assert w1b["같다"], f"🔴 W1b 실패 — 내 N2 가 922 의 N2 와 다르다: {w1b}"
    tab_n2 = gaps_from_events(n2d, n2m, V, OBS, DAY0)
    assert np.array_equal(tab_real["gi"], tab_n2["gi"]), "🔴 두 세계의 행 격자가 다르다"

    out["① 표와 귀무"] = {
        "W0 내 표 == 918 의 표": w0,
        "W1b 내 N2 == perm922 의 N2 (비트)": w1b,
        "🔴 두 세계의 행 순서가 같다(격자 배열 동일)": True,
        "N2 간격 순서가 바뀐 격자 비율": n2moved,
        "N2 대상 격자(분모 · 간격 ≥1)": n2have,
        "W9 다중집합 보존(음성 대조)": gap_multiset_same(rdates, n2d),
        "🔴 홀드아웃 간격 다중집합이 비트로 같은가(비교가능성의 정본 근거)": None,
    }

    # ── ② 자기시험 S1~S3 ────────────────────────────────────────────────
    packs = {}
    for wname, tb in (("진짜", tab_real), ("N2", tab_n2)):
        for cal_off in (False, True):
            packs[(wname, cal_off)] = world_pack(
                tb, tr_set, ho_set, world=wname, cal_off=cal_off,
                with_extra=(not cal_off))
    pr = packs[("진짜", False)]
    pn = packs[("N2", False)]
    ho_gap_real = np.sort(pr["gap"])
    ho_gap_n2 = np.sort(pn["gap"])
    out["① 표와 귀무"]["🔴 홀드아웃 간격 다중집합이 비트로 같은가(비교가능성의 정본 근거)"] = {
        "같다": bool(np.array_equal(ho_gap_real, ho_gap_n2)),
        "행(분모)": int(ho_gap_real.size)}

    s_real = stat(pr, drop_first=False)
    s_n2 = stat(pn, drop_first=False)
    cov_real = coverage(pr["tab"], pr["hom"], pr["T"], which="달력")
    cov_cond = coverage(pr["tab"], pr["hom"], pr["T"], which="조건부")
    st_ok = {
        "진짜 개선(일)": s_real["개선(일)"] == CANON["진짜 개선(일)"],
        "진짜 BCa": (s_real["BCa"][0] == CANON["진짜 lo"]
                   and s_real["BCa"][1] == CANON["진짜 hi"]),
        "N2 개선(일)": s_n2["개선(일)"] == CANON["N2 개선(일)"],
        "N2 BCa": (s_n2["BCa"][0] == CANON["N2 lo"]
                 and s_n2["BCa"][1] == CANON["N2 hi"]),
        "홀드아웃 간격": pr["요약"]["홀드아웃 간격 수(분모)"] == CANON["홀드아웃 간격"],
        "홀드아웃 격자": pr["요약"]["홀드아웃 격자(군집) 수"] == CANON["홀드아웃 격자(군집)"],
        "학습 간격": pr["요약"]["학습 간격 수(분모)"] == CANON["학습 간격"],
        "사건 수": pr["요약"]["🔴 사건 수(분모 A)"] == CANON["사건 수"],
        "간격 수": pr["요약"]["🔴 간격 수(분모 B)"] == CANON["간격 수"],
        "덮음 기후값": cov_real["실측 덮음"] == CANON["덮음 기후값"],
        "덮음 조건부": cov_cond["실측 덮음"] == CANON["덮음 조건부"],
    }
    out["② 자기시험 S1~S3 — 918·922 정본을 비트로 재현하는가"] = {
        "정본": CANON,
        "이번": {"진짜 개선(일)": s_real["개선(일)"], "진짜 BCa": s_real["BCa"],
               "N2 개선(일)": s_n2["개선(일)"], "N2 BCa": s_n2["BCa"],
               "홀드아웃 간격": pr["요약"]["홀드아웃 간격 수(분모)"],
               "홀드아웃 격자(군집)": pr["요약"]["홀드아웃 격자(군집) 수"],
               "학습 간격": pr["요약"]["학습 간격 수(분모)"],
               "사건 수": pr["요약"]["🔴 사건 수(분모 A)"],
               "간격 수": pr["요약"]["🔴 간격 수(분모 B)"],
               "덮음 기후값": cov_real["실측 덮음"],
               "덮음 조건부": cov_cond["실측 덮음"]},
        "항목별": st_ok,
        "🔴 전부 같다": all(st_ok.values()),
    }
    if not all(st_ok.values()):
        out["🔴 판정"] = "§6-다 — 자기시험이 안 맞는다. 관이 다르다. 판정을 안 낸다"
        _finish(out, t0, tstart)
        return

    # ── ③ G4 — 항등 N2 를 심는다(W1a) ──────────────────────────────────
    idd, idm, idmoved, _ = null_n2_plantable(first, r, seed=922, plant_identity=True)
    tab_id = gaps_from_events(idd, idm, V, OBS, DAY0)
    p_id = world_pack(tab_id, tr_set, ho_set, world="N2(항등 · 심은 결함)",
                      cal_off=False, with_extra=False)
    s_id = stat(p_id, drop_first=False)
    g4 = gate_report(
        "G4 N2 가 정말 섞였나(🔴 신설 · 티처 #73 M1)",
        axis="간격 순서가 실제로 바뀐 격자 비율", threshold=1e-12,
        reach_lo=0.0, reach_hi=1.0, observed=n2moved,
        note="심은 결함 = 항등 N2. 심은 판에서 비율이 0 이면 발화")
    g4.update({
        "심은 판의 비율": idmoved, "안 심은 판의 비율": n2moved,
        "🔴 발화했나": bool(idmoved == 0.0),
        "🔴 항등 판에서 N2 개선이 진짜와 비트로 같은가":
            bool(s_id["개선(일)"] == s_real["개선(일)"]),
        "항등 판 N2 개선(일)": s_id["개선(일)"], "항등 판 N2 BCa": s_id["BCa"],
        "🔴 항등 판에서 판정이 뒤집히나(겹친다)":
            bool(not (s_real["BCa"][0] > s_id["BCa"][1])),
        "🔴 W9(다중집합)는 항등 판을 통과시킨다(눈이 멀다)":
            gap_multiset_same(rdates, idd)["통과"],
    })
    out["③ G4 — 항등 N2 를 심었다"] = g4
    if not g4["🔴 발화했나"]:
        out["🔴 판정"] = "§6-라 — G4 가 발화 안 했다. N2 가 섞였다는 보증이 없다. 판정을 안 낸다"
        _finish(out, t0, tstart)
        return

    # ── ④ 여덟 수 ────────────────────────────────────────────────────
    eight = {}
    for panel in PANELS:
        cal_off, drop_first = PANEL_DEF[panel]
        eight[panel] = {}
        for wname in ("진짜", "N2"):
            s = stat(packs[(wname, cal_off)], drop_first=drop_first)
            t_ref = TEACHER[(panel, wname)]
            s["🔴 티처 #73 의 수(정본 아님)"] = t_ref
            s["🔴 내 수 − 티처 수"] = s["개선(일)"] - t_ref
            s["🔴 소수 셋째 자리까지 같은가(S4)"] = bool(
                round(s["개선(일)"], 3) == round(t_ref, 3))
            eight[panel][wname] = s
        rb = eight[panel]["진짜"]["_bb"]
        nb = eight[panel]["N2"]["_bb"]
        eight[panel]["🔴 관문"] = gate_separation(
            f"[{panel}] 진짜 lo > N2 hi", rb, nb,
            expected_gap=(TEACHER_EXPECTED_GAP if panel == "둘 다" else None),
            note=("🔴 주 판정 판(사전등록 §3 에서 미리 지정)" if panel == "둘 다"
                  else "병기"))
    out["④ 여덟 수 — 절제 넷 × 세계 둘"] = eight
    out["④ 🔴 ⓪ 의 예상이 틀린 자리 — 내가 세서 고친다"] = {
        "⓪ 에 적은 예상": "첫간격제외 판도 군집은 2,277 그대로일 것이다"
                    "(격자마다 첫 간격만 빠지므로)",
        "실측": {"원판 군집": eight["원판"]["진짜"]["군집(격자) 수"],
               "첫간격제외 군집": eight["첫간격제외"]["진짜"]["군집(격자) 수"]},
        "🔴 왜 틀렸나": "홀드아웃 간격이 **하나뿐인 격자**는 그 하나가 첫 간격이므로 통째로 빠진다. "
                  "그런 격자가 "
                  f"{eight['원판']['진짜']['군집(격자) 수'] - eight['첫간격제외']['진짜']['군집(격자) 수']}"
                  "개다",
        "🔴 판정에 영향": "군집이 줄면 BCa 가 넓어지는 방향이라 **결론에 보수적**이다",
    }
    s4 = {f"{p}/{w}": eight[p][w]["🔴 소수 셋째 자리까지 같은가(S4)"]
          for p in PANELS for w in ("진짜", "N2")}
    out["④ 🔴 자기시험 S4 — 티처의 여덟 수를 재현했는가"] = {
        "항목별": s4, "🔴 여덟 전부 재현": all(s4.values()),
        "🔴 티처 수는 정본이 아니다": "안 맞으면 내 수로 판정한다(사전등록 §5)"}

    # ── ⑤-가 prevmed 결측 절 ─────────────────────────────────────────
    miss = ~np.isfinite(pr["prevmed"])
    keep = ~miss
    imp_r = pr["arms"]["가 기후값"]["err"] - pr["arms"]["나 조건부(주)"]["err"]
    imp_n = pn["arms"]["가 기후값"]["err"] - pn["arms"]["나 조건부(주)"]["err"]
    n_all = imp_r.size
    b_miss_r = boot(imp_r[miss], pr["gi"][miss], B=B, seed=SEED)
    b_miss_n = boot(imp_n[miss], pn["gi"][miss], B=B, seed=SEED)
    gap_all = float(imp_r.mean() - imp_n.mean())
    out["⑤-가 🔴 prevmed 결측 절 (= 격자마다 첫 간격 · 관측창의 가장자리)"] = {
        "🔴 분모 딱지": "이 절의 행 수와 홀드아웃 격자 수는 **서로 다른 분모인데 값이 같다** — "
                   "격자마다 첫 간격이 정확히 하나라서다. 나란히 놓기 전에 확인했다(조항 60)",
        "행 수": int(miss.sum()),
        "홀드아웃 간격(분모)": n_all,
        "홀드아웃 격자(군집 · 다른 분모)": pr["요약"]["홀드아웃 격자(군집) 수"],
        "🔴 홀드아웃 안의 비율": float(miss.mean()),
        "🔴 행 수 == 홀드아웃 격자 수인가": bool(
            int(miss.sum()) == pr["요약"]["홀드아웃 격자(군집) 수"]),
        "그 행의 평균 간격(일) — 진짜": float(pr["gap"][miss].mean()),
        "나머지 행의 평균 간격(일) — 진짜": float(pr["gap"][keep].mean()),
        "배수": float(pr["gap"][miss].mean() / pr["gap"][keep].mean()),
        "그 행의 평균 간격(일) — N2": float(pn["gap"][miss].mean()),
        "🔴 진짜가 N2 보다 긴 정도": float(
            pr["gap"][miss].mean() / pn["gap"][miss].mean() - 1.0),
        "그 행만의 개선 — 진짜": {"개선(일)": b_miss_r["점추정"],
                          "BCa": [b_miss_r["lo"], b_miss_r["hi"]],
                          "판정": b_miss_r["판정"], "구간 종류": b_miss_r["구간 종류"],
                          "군집": b_miss_r["군집(격자) 수"], "행": b_miss_r["행(간격) 수"]},
        "그 행만의 개선 — N2": {"개선(일)": b_miss_n["점추정"],
                         "BCa": [b_miss_n["lo"], b_miss_n["hi"]],
                         "판정": b_miss_n["판정"], "구간 종류": b_miss_n["구간 종류"]},
        "🔴 전체 개선에서의 몫 — 진짜": {
            "결측행 기여(일)": float(imp_r[miss].sum() / n_all),
            "전체 개선(일)": float(imp_r.mean()),
            "몫": float(imp_r[miss].sum() / n_all / imp_r.mean())},
        "🔴 빈틈에서의 몫": {
            "전체 빈틈(점추정 차 · 일)": gap_all,
            "결측행 몫(일)": float((imp_r[miss].sum() - imp_n[miss].sum()) / n_all),
            "나머지 행 몫(일)": float((imp_r[keep].sum() - imp_n[keep].sum()) / n_all),
            "나머지 행 수": int(keep.sum()),
            "🔴 결측행의 몫 비율": float(
                (imp_r[miss].sum() - imp_n[miss].sum()) / n_all / gap_all)},
        "🔴 과정의 구조인가 관측창의 가장자리인가 — 한 줄 판정": None,
    }

    # ── ⑤-나 §7 바닥 내리기 ──────────────────────────────────────────
    floor = {}
    for panel in PANELS:
        cal_off, drop_first = PANEL_DEF[panel]
        floor[panel] = {}
        for wname in ("진짜", "N2"):
            p = packs[(wname, cal_off)]
            s = stat(p, drop_first=drop_first, base="가′ 기후값+prevmed")
            tot = eight[panel][wname]["개선(일)"]
            s["🔴 그 판의 총 개선(가 기후값 기준)"] = tot
            s["🔴 prevmed 의 몫(총 − 자′)"] = tot - s["개선(일)"]
            s["🔴 prevmed 의 몫 비율"] = (tot - s["개선(일)"]) / tot if tot else None
            floor[panel][wname] = s
        rb = floor[panel]["진짜"]["_bb"]
        nb = floor[panel]["N2"]["_bb"]
        floor[panel]["🔴 관문 G6-분리(자′ 로 잰 빈틈)"] = gate_separation(
            f"[{panel}] 자′ 진짜 lo > N2 hi", rb, nb,
            note="🔴 병기다 — 주 판정이 아니다")
        floor[panel]["🔴 관문 G6"] = {
            "🔴 N2 의 BCa 가 0 을 무나(바닥이 0 으로 내려왔나)":
                bool(nb["lo"] <= 0 <= nb["hi"]),
            "N2 BCa": [nb["lo"], nb["hi"]], "N2 반폭": nb["🔴 반폭(=MDE 자리)"],
            "진짜 lo > 0": bool(rb["lo"] > 0),
            "🔴 깨끗한 갈래(922 §6-1)가 발화하나":
                bool(nb["lo"] <= 0 <= nb["hi"] and rb["lo"] > 0),
            "🔴 두 구간이 안 겹치나": bool(rb["lo"] > nb["hi"]),
        }
    out["⑤-나 §7 병기 — 🔴 기후값 팔에 격자 정보를 넣어 바닥을 내려 본다"] = {
        "🔴 이 절은 주 판정이 아니다": "병기다. 주 판정은 §6 으로만 한다",
        "새 바닥 팔": "가′ = T[2수준][(dow, quarter, bin(prevmed))] → 달력 셀 → 전체 중앙값. mag 을 안 본다",
        "결과": floor}

    # ── ⑤-다 §8 구간 덮음 — 눈금을 맞춘다 ────────────────────────────
    cal_tr, cal_ck = split_cal(tr_g)
    tr_a = np.zeros(G, bool)
    tr_b = np.zeros(G, bool)
    for g in cal_tr:
        tr_a[gidx[g]] = True
    for g in cal_ck:
        tr_b[gidx[g]] = True
    assert not (cal_tr & cal_ck)
    assert not (cal_tr & ho_g) and not (cal_ck & ho_g), "🔴 눈금 절차에 홀드아웃이 샜다"
    tab = pr["tab"]
    T = pr["T"]
    m_a = tr_a[tab["gi"]]
    m_b = tr_b[tab["gi"]]
    sweep = []
    for a in ALPHAS:
        IV = build_intervals(tab, m_a, T, a)
        row = {"α": a, "명목": 1 - 2 * a}
        for which in ("달력", "조건부"):
            c = coverage_at(tab, m_b, T, IV, which)
            row[which] = {"눈금확인 덮음": c["실측 덮음"], "평균 폭": c["평균 폭(일)"],
                          "행": c["행(분모)"]}
        sweep.append(row)
    best = {}
    for which in ("달력", "조건부"):
        cand = sorted(sweep, key=lambda x: (abs(x[which]["눈금확인 덮음"] - NOMINAL), x["α"]))
        best[which] = cand[0]["α"]
    final = {}
    for which in ("달력", "조건부"):
        IV = build_intervals(tab, tr_set[tab["gi"]], T, best[which])
        final[which] = coverage_at(tab, pr["hom"], T, IV, which)
    # 🔴 W12 — 눈금 안 맞춘 α=0.10 이 922 의 공표 덮음을 재현하는가
    IV10 = build_intervals(tab, tr_set[tab["gi"]], T, 0.10)
    w12 = {w: coverage_at(tab, pr["hom"], T, IV10, w) for w in ("달력", "조건부")}
    cond_ok = abs(final["조건부"]["실측 덮음"] - NOMINAL) <= COV_TOL
    narrower = final["조건부"]["평균 폭(일)"] < final["달력"]["평균 폭(일)"]
    # 🔴 진단(판정 미사용) — 홀드아웃을 25번 봤으므로 판정에 못 쓴다.
    #   두 팔의 α 가 달라서 폭을 그냥 비교하면 분모가 다르다(조항 60).
    #   그래서 **덮음을 맞춘 자리에서의 폭**을 홀드아웃 곡선에서 선형보간해 같이 낸다.
    curve = {}
    for a in ALPHAS:
        IVa = build_intervals(tab, tr_set[tab["gi"]], T, a)
        curve[a] = {w: coverage_at(tab, pr["hom"], T, IVa, w) for w in ("달력", "조건부")}

    def _w_at(which, target=NOMINAL):
        xs = [(curve[a][which]["실측 덮음"], curve[a][which]["평균 폭(일)"], a)
              for a in ALPHAS]
        xs.sort()
        for (c0, w0, a0), (c1, w1, a1) in zip(xs, xs[1:]):
            if c0 <= target <= c1:
                t = 0.0 if c1 == c0 else (target - c0) / (c1 - c0)
                return {"덮음": target, "폭(보간)": w0 + t * (w1 - w0),
                        "사이 α": [a0, a1]}
        return {"덮음": target, "폭(보간)": None, "사이 α": None}
    out["⑤-다 §8 ③ 의 둘째 자 — 구간 덮음. 🔴 900노트 만에 처음으로 이 자로 판정한다"] = {
        "🔴 어느 판인가": "진짜 세계 · 원판(달력 있음). 홀드아웃 54,862행",
        "눈금 분할": {"눈금용 학습 격자": len(cal_tr), "눈금 확인 격자": len(cal_ck),
                  "🔴 홀드아웃과 겹침": 0,
                  "눈금용 학습 행": int(m_a.sum()), "눈금 확인 행": int(m_b.sum())},
        "α 훑기(눈금 확인에서 잰 덮음)": sweep,
        "🔴 고른 α": best,
        "🔴 홀드아웃 실측": final,
        "🔴 관문 G5": gate_report(
            "G5 구간 덮음", axis="실측 덮음", threshold=COV_TOL,
            reach_lo=0.0, reach_hi=NOMINAL, observed=final["조건부"]["실측 덮음"],
            note="도달 가능 최대 편차 0.80 → 비 16 · 검정력 있음"),
        "🔴 진단(판정 미사용) — 덮음을 맞춘 자리에서의 폭": {
            "🔴 왜 판정에 못 쓰나": "이 곡선은 홀드아웃을 25번 봤다. 눈금은 학습 안에서만 맞췄고(위), "
                            "이 절은 **읽는 사람이 분모를 맞춰 보라고** 싣는 진단이다",
            "홀드아웃 곡선": {str(a): {w: {"덮음": curve[a][w]["실측 덮음"],
                                     "폭": curve[a][w]["평균 폭(일)"]}
                                for w in ("달력", "조건부")} for a in ALPHAS},
            "🔴 덮음 0.80 자리의 폭(선형보간)": {w: _w_at(w) for w in ("달력", "조건부")},
        },
        "🔴 통과 규칙(사전등록 §8)": "|실측 − 0.80| ≤ 0.05 이면서 조건부 폭 < 기후값 폭",
        "🔴 통과했나": bool(cond_ok and narrower),
        "|실측 − 0.80|": abs(final["조건부"]["실측 덮음"] - NOMINAL),
        "조건부 폭 < 기후값 폭": bool(narrower),
        "🔴 W12 — 눈금 전(α=0.10)이 922 의 공표 덮음을 재현하는가": {
            "이번": {w: w12[w]["실측 덮음"] for w in w12},
            "922 공표": {"달력": CANON["덮음 기후값"], "조건부": CANON["덮음 조건부"]},
            "🔴 같은가": bool(w12["달력"]["실측 덮음"] == CANON["덮음 기후값"]
                          and w12["조건부"]["실측 덮음"] == CANON["덮음 조건부"]),
            "눈금 전 평균 폭": {w: w12[w]["평균 폭(일)"] for w in w12}},
    }

    # ── ⑥ 관문 신고 (#178) ──────────────────────────────────────────
    real_clim = pr["요약"]["MAE"]["가 기후값"]
    real_unin = pr["요약"]["MAE"]["라 무정보"]
    n2_clim = pn["요약"]["MAE"]["가 기후값"]
    reach = abs(real_unin - real_clim) / real_clim
    g2 = gate_report(
        "G2 W7 비교가능성(922 가 쓴 관문) — 🔴 이번엔 판정에 안 쓴다",
        axis="기후값 MAE 상대차", threshold=0.05,
        reach_lo=0.0, reach_hi=reach,
        observed=(n2_clim - real_clim) / real_clim,
        note="달력 결합이 완전히 깨지면 기후값 팔은 무정보 팔로 퇴화한다 — 그것이 이 축의 끝이다")
    g2.update({
        "진짜 기후값 MAE": real_clim, "진짜 무정보 MAE": real_unin,
        "N2 기후값 MAE": n2_clim,
        "🔴 N2 기후값 팔이 이미 무정보 팔인가(차 · 일)": float(n2_clim - real_unin),
        "🔴 그래서 비교가능성의 정본 근거를 W9 로 옮긴다":
            out["① 표와 귀무"]["🔴 홀드아웃 간격 다중집합이 비트로 같은가(비교가능성의 정본 근거)"]})
    g3 = gate_report("G3 W9 다중집합 보존", axis="깨진 격자 수", threshold=1.0,
                     reach_lo=0.0, reach_hi=float(n2have), observed=0.0,
                     note="🔴 항등 순열에는 눈이 멀다 — 그래서 G4 를 신설했다")
    out["⑥ 관문 신고 (#178) — 🔴 관문마다 도달 가능 폭 ÷ 문턱"] = {
        "G1 주 판정": eight["둘 다"]["🔴 관문"],
        "G1 병기(나머지 세 판)": {p: eight[p]["🔴 관문"] for p in PANELS if p != "둘 다"},
        "G2": g2, "G3": g3, "G4": {k: v for k, v in g4.items() if k != "비고"},
        "G5": out["⑤-다 §8 ③ 의 둘째 자 — 구간 덮음. 🔴 900노트 만에 처음으로 이 자로 판정한다"]["🔴 관문 G5"],
        "G6": {p: floor[p]["🔴 관문 G6"] for p in PANELS},
        "🔴 검정력 0 으로 자동 신고된 관문": [
            g["관문"] for g in (g2, g3, g4) if g.get("🔴 검정력 0 인가(비 < 1 이면 자동)")]
            + [eight[p]["🔴 관문"]["관문"] for p in PANELS
               if eight[p]["🔴 관문"].get("🔴 검정력 0 인가(비 < 1 이면 자동)")],
    }

    # ── ⑦ 배선 회계 — 🔴 분모 둘 ─────────────────────────────────────
    tr_leak, ho_leak = split_grids(grids, plant_leak=True)
    bd, bm, _, _ = null_n2_plantable(first, r, seed=922, plant_break_multiset=True)
    w9_plant = gap_multiset_same(rdates, bd)
    w9_neg = gap_multiset_same(rdates, n2d)
    n_drop = int(np.isfinite(pr["prevmed"]).sum())
    T_on = fit_tables(tab, tr_set[tab["gi"]], plant_const_cal=False)
    T_off = fit_tables(tab, tr_set[tab["gi"]], plant_const_cal=True)
    checks = {
        "W0 표 동치": {"심었나": True, "발화했나": (w0_plant["mag"] is False),
                   "음성 대조 통과": bool(w0["전부 같다"]),
                   "심은 결함": "mag 을 격자 한 칸 굴렸다"},
        "🔴 W1a N2 가 정말 섞였나(신설 · 티처 #73 M1)": {
            "심었나": True, "발화했나": g4["🔴 발화했나"],
            "음성 대조 통과": bool(n2moved > 0.5),
            "심은 결함": "항등 N2(순서를 하나도 안 섞는다)",
            "심은 판 비율": idmoved, "안 심은 판 비율": n2moved,
            "🔴 심은 판에서 판정이 뒤집힌다": g4["🔴 항등 판에서 판정이 뒤집히나(겹친다)"]},
        "W2 분할 누설": {"심었나": True,
                    "발화했나": bool(len(tr_leak & ho_leak) > 0),
                    "음성 대조 통과": bool(len(tr_g & ho_g) == 0),
                    "심은 결함": "홀드아웃 격자 하나를 학습에도 넣었다"},
        "W9 다중집합 보존": {"심었나": True, "발화했나": bool(not w9_plant["통과"]),
                      "음성 대조 통과": bool(w9_neg["통과"]),
                      "심은 결함": "간격 하나를 +1 해서 다중집합을 깬다",
                      "🔴 이 검사는 항등 순열에 눈이 멀다": True},
        "🔴 W10 첫간격제외가 정말 행을 빼나(신설)": {
            "심었나": True,
            "발화했나": bool(stat(pr, drop_first=True, plant_no_drop=True)["행(간격) 수"]
                         == n_all),
            "음성 대조 통과": bool(n_drop < n_all),
            "심은 결함": "첫간격제외 마스크가 아무 행도 안 뺀다",
            "안 심은 판의 행": n_drop, "심은 판의 행": n_all,
            "🔴 뺀 행": n_all - n_drop},
        "🔴 W11 달력제거가 정말 달력을 없애나(신설)": {
            "심었나": True,
            "발화했나": bool(T_on["🔴 달력 셀 가짓수"] > 1),
            "음성 대조 통과": bool(T_off["🔴 달력 셀 가짓수"] == 1),
            "심은 결함": "달력제거라 부르면서 plant_const_cal 을 안 켠다",
            "달력 있는 표의 셀 가짓수": T_on["🔴 달력 셀 가짓수"],
            "달력 제거한 표의 셀 가짓수": T_off["🔴 달력 셀 가짓수"],
            "🔴 달력 제거 판의 기후값 MAE == 무정보 MAE 인가": bool(
                packs[("진짜", True)]["요약"]["MAE"]["가 기후값"] == real_unin)},
        "🔴 W12 덮음 재구현이 922 를 재현하나(신설)": {
            "심었나": False, "음성 대조": True,
            "발화했나": None,
            "🔴 이것은 심은 결함이 아니라 음성 대조다":
                out["⑤-다 §8 ③ 의 둘째 자 — 구간 덮음. 🔴 900노트 만에 처음으로 이 자로 판정한다"][
                    "🔴 W12 — 눈금 전(α=0.10)이 922 의 공표 덮음을 재현하는가"]["🔴 같은가"]},
    }
    planted = {k: v for k, v in checks.items() if v.get("심었나")}
    fired = sum(1 for v in planted.values() if v["발화했나"])
    unplantable = [
        "🔴 918 의 모형·부트 코드가 옳은가 — 여덟 개를 그대로 import 한다. 그 관이 틀렸으면 원리상 못 잡는다(티처 #73 M6)",
        "🔴 「달력제거」가 달력의 몫만 떼는가 — 셀 해상도 저하와 뒤엉킨다(사전등록 §3). 가르는 검사를 못 만들었다",
        "🔴 daily.npz 가 옳게 만들어졌는가 — 저장소 밖 파일이고 만드는 러너가 없다(티처 #73 M9). sha 대조는 자기 자신하고만 가능하다",
    ]
    out["⑦ 배선 검사 — 🔴 분모를 둘로 낸다"] = {
        "검사": checks,
        "🔴 심은 수": len(planted), "🔴 발화한 수": fired,
        "🔴 놓친 수": len(planted) - fired,
        "🔴 못 심은 수": len(unplantable),
        "🔴 못 심은 것(검정력 0 으로 신고 · 분모에 넣는다)": unplantable,
        "🔴 검정력(심은 것 기준)": f"{fired}/{len(planted)} = {fired/len(planted):.3f}",
        "🔴🔴 검정력(못 심은 것까지 분모에)":
            f"{fired}/{len(planted)+len(unplantable)} = "
            f"{fired/(len(planted)+len(unplantable)):.3f} — "
            f"**이 수가 관문 전체에 대한 검정력이다**",
    }

    # ── ⑧ 판정 (사전등록 §6 을 기계로 적용) ────────────────────────────
    main_gate = eight["둘 다"]["🔴 관문"]
    sep = main_gate["🔴 안 겹치나(진짜 lo > 귀무 hi)"]
    mde = main_gate["🔴 가를 수 있는 최소 빈틈(두 반폭의 합 · = MDE)"]
    if sep:
        verdict = ("🔴 §6-가 — [달력제거 ∧ 첫간격제외] 에서도 진짜 lo > N2 hi. "
                   "**③ 이 이름까지 옳게 0 을 벗어난다.** ③ 의 첫째 자를 0.5 → 1 로 올린다")
    else:
        verdict = (f"🔴 §6-나 — [달력제거 ∧ 첫간격제외] 에서 두 구간이 **겹친다**. "
                   f"**「이 자로는 순서를 못 잰다」가 확정된다.** ③ 의 첫째 자를 0.5 → 0 으로 되돌린다. "
                   f"🔴 그리고 이것은 「빈틈이 0 이다」가 아니라 "
                   f"**「빈틈이 {mde:.5f}일 미만이다」**는 상한이다(사전등록 §4·§6-나)")
    prev = out["⑤-가 🔴 prevmed 결측 절 (= 격자마다 첫 간격 · 관측창의 가장자리)"]
    edge_share = prev["🔴 빈틈에서의 몫"]["🔴 결측행의 몫 비율"]
    prev["🔴 과정의 구조인가 관측창의 가장자리인가 — 한 줄 판정"] = (
        f"🔴 **가장자리다** — 홀드아웃의 {prev['🔴 홀드아웃 안의 비율']*100:.3f}% 인 "
        f"{prev['행 수']}행(격자마다 첫 간격 하나)이 빈틈의 {edge_share*100:.1f}% 를 만든다. "
        f"그 행의 평균 간격이 {prev['그 행의 평균 간격(일) — 진짜']:.3f}일로 나머지 "
        f"{prev['나머지 행의 평균 간격(일) — 진짜']:.3f}일의 "
        f"{prev['배수']:.2f}배다. 🔴 **다만 「가장자리라서 길다」와 「가장자리에서 시작한 격자가 "
        f"원래 드문 격자다」를 이 표로는 못 가른다** — 못 가른다고 적는다")
    cov_final = out["⑤-다 §8 ③ 의 둘째 자 — 구간 덮음. 🔴 900노트 만에 처음으로 이 자로 판정한다"]
    out["🔴🔴 판정 (사전등록 §6 을 기계로 적용)"] = {
        "🔴 첫째 자(간격 예측이 기후값을 이기나)": verdict,
        "쓴 갈래의 재료": {
            "진짜 [둘 다]": {"개선": eight["둘 다"]["진짜"]["개선(일)"],
                         "BCa": eight["둘 다"]["진짜"]["BCa"]},
            "N2 [둘 다]": {"개선": eight["둘 다"]["N2"]["개선(일)"],
                        "BCa": eight["둘 다"]["N2"]["BCa"]},
            "빈틈(진짜 lo − N2 hi)": main_gate["실측 빈틈(일)"],
            "가를 수 있는 최소 빈틈": mde,
            "안 겹치나": sep},
        "🔴 둘째 자(구간 덮음)": (
            "🔴 **넘었다** — " if cov_final["🔴 통과했나"] else "🔴 **못 넘었다** — ") + (
            f"눈금 뒤 조건부 덮음 {cov_final['🔴 홀드아웃 실측']['조건부']['실측 덮음']:.6f} "
            f"(α*={cov_final['🔴 고른 α']['조건부']}) · 명목 0.80 · "
            f"|차| {abs(cov_final['🔴 홀드아웃 실측']['조건부']['실측 덮음']-NOMINAL):.6f} · "
            f"조건부 폭 {cov_final['🔴 홀드아웃 실측']['조건부']['평균 폭(일)']:.4f} 대 "
            f"기후값 폭 {cov_final['🔴 홀드아웃 실측']['달력']['평균 폭(일)']:.4f}"),
        "🔴 헤드라인에 반드시 같이 적는 두 줄(사전등록 §6)": {
            "1 바닥이 0 이 아니다": (
                f"시간 구조가 전혀 없는 N2 세계에서도 이 자는 원판에서 "
                f"{eight['원판']['N2']['개선(일)']:.6f}일 [{eight['원판']['N2']['BCa'][0]:.4f}, "
                f"{eight['원판']['N2']['BCa'][1]:.4f}] 로 **유의하게 이긴다** — 기후값 팔이 "
                f"**격자를 모르는 팔**이라서다. 그 이득 중 prevmed 의 몫 = "
                f"{floor['원판']['N2']['🔴 prevmed 의 몫 비율']*100:.1f}%"),
            "2 ③ 의 자는 둘이다": "위의 둘째 자 줄을 같이 읽어라",
        },
        "🔴 첫 양수를 채택하지 않았다(노트 133)": (
            "네 판 여덟 수를 전부 낸 뒤 **사전등록 §3 에서 미리 지정한 [둘 다] 판 하나로만** 판정했다. "
            "병기 판이 더 좋게 나와도 주 판정을 안 바꿨다"),
        "🔴 못 한 것(「없다」가 아니라 「못 했다」)": [
            "「달력제거」가 달력의 몫만 떼는지 — 셀 해상도 저하와 못 갈랐다",
            "가장자리 행이 「가장자리라서 긴가」와 「드문 격자라서 긴가」 — 이 표로는 못 갈랐다",
            "918 의 모형·부트 코드 자체의 옳음 — 빌린 관이라 원리상 못 잡는다",
        ],
    }
    _finish(out, t0, tstart)


def _finish(out: dict, t0: float, tstart: dt.datetime) -> None:
    out = _scrub(out)
    out["시작 UTC"] = tstart.isoformat(timespec="seconds")
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"산출물": str(OUT), "초": out["초"],
                      "판정": out.get("🔴🔴 판정 (사전등록 §6 을 기계로 적용)", {})
                      .get("🔴 첫째 자(간격 예측이 기후값을 이기나)", out.get("🔴 판정"))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
