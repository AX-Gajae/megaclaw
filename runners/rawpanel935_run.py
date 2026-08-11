# -*- coding: utf-8 -*-
"""팔 935 — **원판 200뽑기** (사전등록 `docs/prereg_935_rawpanel.md`).

🔴 순서가 규약이다:
    ① 입력·사전등록 sha 대조 → ② 항등 검사(W1·W2·W3·W10·W11) → ③ 배선(W4~W6)
    → ④ 파일럿 20뽑기 · 🔴 **관문 검정력 먼저** · 경험분포 검출력
    → ⑤ 판정 200뽑기(판 ①·② · 진단 ③) → ⑥ 판별·상태표·부호 결정·짝지은 BCa
    → ⑦ 판정(사전등록 §4 를 기계로 적용)

🔴 멈추는 조건(사전등록 §7): npz sha 불일치 · 항등 검사 불일치 ·
   **판 ① 의 다중집합 동일성이 한 뽑기라도 False** · 진짜 개선이 오라클 산출물과 비트로 다르다.
   (🔴 판 ②·③ 의 다중집합은 원리상 다르다 — 멈춤 조건이 아니다 · 사전등록 §0-라)

산출물: runners/out935_rawpanel.json
사용:   python3 runners/rawpanel935_run.py     (🔴 파이프 금지 — 리디렉션으로)
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
                               baseline_ratio, sha256_text, split_grids, surges)
from state.perm922 import (COMPARABLE_REL, comparability,  # noqa: E402
                           gaps_from_events, real_events)
from state.gap925 import null_n2_plantable  # noqa: E402
from state.paired928 import improvement_rows, paired, perm_p  # noqa: E402
from state.calpanel933 import fit_identity  # noqa: E402
from state.rawpanel935 import (PANEL_ALL, PANEL_EXC, PANEL_ONLY,  # noqa: E402
                               cmp_pack, empirical_power_k, multiset_same,
                               p_equivalence, rows_pair)

SCRATCH = Path(os.environ.get(
    "G935_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/"
    "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad"))
NPZ = Path(os.environ.get("G935_NPZ", str(SCRATCH / "g922/daily.npz")))
TAG = os.environ.get("G935_TAG", "")          # 🔴 연습 주행은 TAG 로 정본을 안 덮는다
OUT = ROOT / f"runners/out935_rawpanel{TAG}.json"
CKPT = SCRATCH / f"g935/draws{TAG}.json"
NDRAW = int(os.environ.get("G935_NDRAW", "200"))
PILOT = tuple(range(901, 901 + int(os.environ.get("G935_NPILOT", "20"))))
B_BOOT = int(os.environ.get("G935_B", "2000"))
SEED = 918
ALPHA = 0.01

NPZ_SHA = "4472b7f69cb5170c8a804dfbdb72a0289dcd34936aa5e05b6e9e191878ae97b2"
#: 사전등록 §1 이 측정 전에 박은 수(오라클 부속 산출물에서 왔다 · 커밋 659008127)
REAL_IMP_ALL = 0.7545204330866538
REAL_IMP_EXC = 0.4478748692592945
REAL_IMP_ONLY = 7.83618796662275
REAL_PRV_CUTS = (4.5, 7.0)
REAL_MAG_CUTS = (1.2909221321296984, 1.624097296793309)
ORACLE_Y_ALL = 0.7768947541103142        # 🔴 LOO (규율 4 ㉮)
ORACLE_Y_EXC = 0.4276885043263281
ORACLE_Y_ONLY = 8.83201581027668
SIZE_X = 1.0                              # 🔴 개선 눈금 (docs/목표.md ③)
PANELS = (PANEL_ALL, PANEL_EXC, PANEL_ONLY)
JUDGED = (PANEL_ALL, PANEL_EXC)           # 🔴 진단 ③ 은 판정에 안 들어간다


def _log(*a):
    print(*a, flush=True)


def _scrub(o):
    if isinstance(o, dict):
        return {k: _scrub(v) for k, v in o.items()
                if not (isinstance(k, str) and k.startswith("_"))}
    if isinstance(o, (list, tuple)):
        return [_scrub(x) for x in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def _finish(out: dict, t0: float, tstart: dt.datetime) -> None:
    out["시작 UTC"] = tstart.isoformat(timespec="seconds")
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(_scrub(out), ensure_ascii=False, indent=1), encoding="utf-8")
    _log("wrote", OUT, out["초"], "초")


def _state_table(vals, cuts, key="개선(일)") -> dict:
    """🔴 경계 상태별로 갈라 센다 — 그래야 z·SD·왜도·첨도가 해석 가능해진다."""
    st = {}
    for v, c in zip(vals, cuts):
        st.setdefault(tuple(c), []).append(v)
    rows = []
    for k, v in sorted(st.items(), key=lambda kv: -len(kv[1])):
        a = np.asarray(v, float)
        rows.append({"경계": list(k), "개수": int(a.size), "평균": float(a.mean()),
                     "상태 내 SD(ddof=1)": float(a.std(ddof=1)) if a.size > 1 else None,
                     "최소": float(a.min()), "최대": float(a.max())})
    allv = np.asarray(vals, float)
    within = float(np.mean([r["상태 내 SD(ddof=1)"] ** 2 for r in rows
                            if r["상태 내 SD(ddof=1)"] is not None])) if rows else None
    tot = float(allv.var(ddof=1))
    return {"상태 수": len(rows), "상태별": rows,
            "전체 SD(ddof=1)": float(allv.std(ddof=1)),
            "🔴 경계 상태가 설명하는 분산 몫(1 − 상태내평균분산/전체분산)":
                (1.0 - within / tot) if (within is not None and tot > 0) else None,
            "🔴 상태가 둘 이상인가(= 전체 z·SD·왜도·첨도는 혼합의 요약이라 해석 불가)":
                bool(len(rows) > 1)}


def _mae_variety(vals) -> dict:
    """🔴 관문의 검정력 증거 — **기준 팔 MAE 의 가짓수**(티처 #76 M1)."""
    a = np.asarray(vals, float)
    u = np.unique(a)
    return {"뽑기 수(분모)": int(a.size), "🔴 서로 다른 값의 개수": int(u.size),
            "최소": float(a.min()), "최대": float(a.max()),
            "최대−최소": float(a.max() - a.min()),
            "🔴 관문에 검정력이 있나(가짓수 ≥ 2)": bool(u.size >= 2)}


def main() -> None:
    t0 = time.time()
    tstart = dt.datetime.now(dt.timezone.utc)
    CKPT.parent.mkdir(parents=True, exist_ok=True)
    stamp = json.loads((ROOT / "runners/out935_prereg_stamp.json").read_text(encoding="utf-8"))
    prereg_now = sha256_text(ROOT / "docs/prereg_935_rawpanel.md")
    prereg_stamped = stamp["파일별 sha256·mtime"]["docs/prereg_935_rawpanel.md"]["sha256"]
    smoke = sorted(str(p.relative_to(ROOT)) for p in
                   (ROOT / "runners").glob("out935_rawpanel_*.json"))
    out: dict = {
        "팔": "935 — 원판(cal_off=False · drop_first=False) 200뽑기 + b_prv=−1 칸 분리",
        "사전등록": "docs/prereg_935_rawpanel.md",
        "티처": "runners/out934_teacher.json (#76 C5 2순위 · M8 3순위 · C2·C3 규율 4 개정 · C4 눈금 · M1 관문)",
        "🔴 판 ρ": "한 번도 안 돌렸다(14사이클 연속). 이 팔의 자는 순열 200뽑기와 짝지은 군집 BCa 둘이다",
        "🔴 사전등록 시각 증거": {
            "stamp": "runners/out935_prereg_stamp.json",
            "stamp 이 박은 사전등록 sha256": prereg_stamped,
            "사전등록 sha256(지금 다시 계산)": prereg_now,
            "🔴 같은가(W11)": prereg_now == prereg_stamped,
            "stamp 를 쓴 시각(UTC)": stamp["이 stamp 를 쓴 시각(UTC)"],
            "측정 시작(UTC)": tstart.isoformat(timespec="microseconds"),
            "🔴 stamp 가 측정보다 먼저인가":
                stamp["이 stamp 를 쓴 시각(UTC)"] < tstart.isoformat(timespec="microseconds"),
            "🔴 사전등록만 담은 커밋을 측정 전에 만들었나": True,
            "🔴 오라클 부속은 그보다 앞선 별도 커밋인가(933 m8 을 안 되풀이한다)": True,
            "🔴 os.utime 을 썼나": False,
        },
        "🔴🔴 주행 회계 — 이름을 갈라서 적는다 (티처 #76 C1)": {
            "🔴 인용 규칙": "논문·원장·카드는 **`본 주행` 이름이 붙은 수만** 인용한다. "
                       "933 에서 연습 주행(4뽑기)의 6/6 이 정본(5/6)을 덮고 넷으로 새어 나갔다",
            "연습 주행(smoke) 산출물": smoke,
            "연습 주행(smoke) 수": len(smoke),
            "🔴 연습 주행을 지웠나": "안 지웠다(이슈 #182)",
            "본 주행 수": 1,
            "이 산출물": str(OUT.relative_to(ROOT)),
            "🔴 이 산출물의 태그(비어 있으면 본 주행)": TAG or "(없음 — 본 주행)",
        },
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/rawpanel935.py", "runners/rawpanel935_run.py",
                        "runners/rawpanel935_oracle.py", "runners/rawpanel935_stamp.py",
                        "state/calpanel933.py", "state/paired928.py",
                        "state/gap925.py", "state/perm922.py", "state/interval918.py")},
        "설정": {"τ": TAU_PRIMARY, "기저선 lag": list(BASE_LAGS), "셀 최소 학습행": CELL_MIN,
               "뽑기 수": NDRAW, "판정 씨앗": "1 … %d (922 는 안 넣는다)" % NDRAW,
               "파일럿 씨앗": list(PILOT), "부트 B": B_BOOT, "부트 seed": SEED,
               "비교가능성 문턱": COMPARABLE_REL,
               "분할": f"격자 sha256('{SPLIT_SALT}'+격자) 70/30",
               "🔴 판정 문턱 α": ALPHA,
               "🔴 α 의 k 동치 조건(러너가 계산 · 933 자기적발 ①)": p_equivalence(ALPHA, NDRAW)},
    }

    # ── ① 입력 ────────────────────────────────────────────────────────
    sha = sha256_text(NPZ)
    out["① 입력"] = {"daily.npz(🔴 저장소 밖)": str(NPZ), "sha256": sha,
                  "바이트": NPZ.stat().st_size,
                  "🔴 925·928·933 이 쓴 파일과 같은가(W9)": sha == NPZ_SHA,
                  "🔴 못 심는 것": "이 파일을 만드는 러너가 저장소에 없다(4사이클 연속 · 티처 #75 m6)"}
    if sha != NPZ_SHA or prereg_now != prereg_stamped:
        out["🔴 판정"] = "§7-1/§7-2 — 입력 또는 사전등록 sha 가 다르다. 판정을 안 낸다"
        _finish(out, t0, tstart)
        return

    z = np.load(NPZ, allow_pickle=False)
    V = z["V"].astype(np.float64)
    C = z["C"]
    grids = z["grids"].tolist()
    OBS = C > 0
    G, D = V.shape
    assert D == NDAY, (D, NDAY)
    qualify = OBS.mean(axis=1) >= OBS_MIN_FRAC
    _b, r, ok = baseline_ratio(V, OBS)
    ok = ok & qualify[:, None]
    tr_g, ho_g = split_grids(grids)
    gidx = {g: i for i, g in enumerate(grids)}
    tr_set = np.zeros(G, bool)
    ho_set = np.zeros(G, bool)
    for g in tr_g:
        tr_set[gidx[g]] = True
    for g in ho_g:
        ho_set[gidx[g]] = True
    first = surges(r, ok, TAU_PRIMARY)
    rdates, rmags = real_events(first, r)
    tab_real = gaps_from_events(rdates, rmags, V, OBS, DAY0)
    trm = tr_set[tab_real["gi"]]
    _log("① 표 준비", time.time() - t0)

    # ── ② 항등 검사 ───────────────────────────────────────────────────
    RR = rows_pair(tab_real, tr_set, ho_set, cal_off=False)
    ref_all = improvement_rows(tab_real, tr_set, ho_set, cal_off=False, drop_first=False)
    ref_exc = improvement_rows(tab_real, tr_set, ho_set, cal_off=False, drop_first=True)
    ident = {
        "W1 fit_tables_x 가 원본과 같은 표인가(cal_off=False)":
            fit_identity(tab_real, trm, plant_const_cal=False),
        "W2 rows_pair 가 paired928.improvement_rows 와 같은 개선인가": {
            "판 ①": {"paired928": ref_all["개선(일)"], "rawpanel935": RR[PANEL_ALL]["개선(일)"],
                   "🔴 비트로 같은가": bool(ref_all["개선(일)"] == RR[PANEL_ALL]["개선(일)"])},
            "판 ②": {"paired928": ref_exc["개선(일)"], "rawpanel935": RR[PANEL_EXC]["개선(일)"],
                   "🔴 비트로 같은가": bool(ref_exc["개선(일)"] == RR[PANEL_EXC]["개선(일)"])},
        },
        "W3 b_prv=−1 이 prevmed 결측과 같은 행인가 · 행 회계": {
            "동치": RR["🔴 b_prv=−1 과 prevmed 결측이 같은 행인가"],
            "행": {"판 ①": RR[PANEL_ALL]["행(간격) 수"], "판 ②": RR[PANEL_EXC]["행(간격) 수"],
                 "진단 ③": RR[PANEL_ONLY]["행(간격) 수"]},
            "🔴 합이 맞나": bool(RR[PANEL_ALL]["행(간격) 수"]
                           == RR[PANEL_EXC]["행(간격) 수"] + RR[PANEL_ONLY]["행(간격) 수"]),
            "b_prv 칸별 홀드아웃 행 수": RR["b_prv 칸별 행 수"]},
        "W10 사전등록 §1 이 박은 진짜 개선과 같은가": {
            "판 ①": {"사전등록": REAL_IMP_ALL, "지금": RR[PANEL_ALL]["개선(일)"],
                   "🔴 비트로 같은가": bool(RR[PANEL_ALL]["개선(일)"] == REAL_IMP_ALL)},
            "판 ②": {"사전등록": REAL_IMP_EXC, "지금": RR[PANEL_EXC]["개선(일)"],
                   "🔴 비트로 같은가": bool(RR[PANEL_EXC]["개선(일)"] == REAL_IMP_EXC)},
            "진단 ③": {"사전등록": REAL_IMP_ONLY, "지금": RR[PANEL_ONLY]["개선(일)"],
                    "🔴 비트로 같은가": bool(RR[PANEL_ONLY]["개선(일)"] == REAL_IMP_ONLY)}},
        "진짜의 3분위 경계": {"prevmed": RR[PANEL_ALL]["prevmed 3분위 경계"],
                      "mag": RR[PANEL_ALL]["mag 3분위 경계"],
                      "전체 중앙값": RR[PANEL_ALL]["전체 중앙값"],
                      "🔴 사전등록과 같은가":
                          bool(tuple(RR[PANEL_ALL]["prevmed 3분위 경계"]) == REAL_PRV_CUTS
                               and tuple(RR[PANEL_ALL]["mag 3분위 경계"]) == REAL_MAG_CUTS)},
        "진짜 기준·시험 팔 MAE": {p: {"기준": RR[p]["그 판의 기준 팔 MAE"],
                              "시험": RR[p]["그 판의 시험 팔 MAE"]} for p in PANELS},
    }
    stop2 = not (ident["W1 fit_tables_x 가 원본과 같은 표인가(cal_off=False)"]["🔴 같은가"]
                 and ident["W2 rows_pair 가 paired928.improvement_rows 와 같은 개선인가"]["판 ①"]["🔴 비트로 같은가"]
                 and ident["W2 rows_pair 가 paired928.improvement_rows 와 같은 개선인가"]["판 ②"]["🔴 비트로 같은가"]
                 and ident["W3 b_prv=−1 이 prevmed 결측과 같은 행인가 · 행 회계"]["동치"]
                 and ident["W3 b_prv=−1 이 prevmed 결측과 같은 행인가 · 행 회계"]["🔴 합이 맞나"]
                 and ident["W10 사전등록 §1 이 박은 진짜 개선과 같은가"]["판 ①"]["🔴 비트로 같은가"]
                 and ident["W10 사전등록 §1 이 박은 진짜 개선과 같은가"]["판 ②"]["🔴 비트로 같은가"])
    out["② 항등 검사 (사전등록 §7-2·§7-4)"] = {**ident, "🔴 전부 통과": not stop2}
    if stop2:
        out["🔴 판정"] = "§7 — 항등 검사가 깨졌다. 판정을 안 낸다"
        _finish(out, t0, tstart)
        return
    _log("② 항등 검사 통과", time.time() - t0)

    # ── ③ 배선 (파일럿 씨앗 하나 위에서 심는다 — 판정 씨앗을 안 쓴다) ──────
    ws = PILOT[0]
    dd, mm, moved, _h = null_n2_plantable(first, r, seed=ws)
    tb_w = gaps_from_events(dd, mm, V, OBS, DAY0)
    NW = rows_pair(tb_w, tr_set, ho_set, cal_off=False)
    NW_nan = rows_pair(tb_w, tr_set, ho_set, cal_off=False,
                       force_prv_cuts=(float("nan"), float("nan")))
    ms_all = multiset_same(RR[PANEL_ALL], NW[PANEL_ALL])
    ms_exc = multiset_same(RR[PANEL_EXC], NW[PANEL_EXC])
    cmp_good = comparability(cmp_pack(RR[PANEL_ALL], tab_real),
                             cmp_pack(NW[PANEL_ALL], tb_w))
    bad_pack = cmp_pack(NW[PANEL_ALL], tb_w)
    bad_pack["가 기후값"] = {"MAE": bad_pack["가 기후값"]["MAE"] * 1.10}
    cmp_bad = comparability(cmp_pack(RR[PANEL_ALL], tab_real), bad_pack)
    wires = {
        "W1 fit_tables_x 항등(음성 대조)": {
            "심었나": False,
            "🔴 통과": ident["W1 fit_tables_x 가 원본과 같은 표인가(cal_off=False)"]["🔴 같은가"]},
        "W2 rows_pair 항등(음성 대조)": {
            "심었나": False,
            "🔴 통과": bool(ident["W2 rows_pair 가 paired928.improvement_rows 와 같은 개선인가"]["판 ①"]["🔴 비트로 같은가"]
                        and ident["W2 rows_pair 가 paired928.improvement_rows 와 같은 개선인가"]["판 ②"]["🔴 비트로 같은가"])},
        "W3 b_prv=−1 ⟺ prevmed 결측 · 행 회계(음성 대조)": {
            "심었나": False,
            "🔴 통과": bool(ident["W3 b_prv=−1 이 prevmed 결측과 같은 행인가 · 행 회계"]["동치"]
                        and ident["W3 b_prv=−1 이 prevmed 결측과 같은 행인가 · 행 회계"]["🔴 합이 맞나"])},
        "W4 경계 주입이 정말 먹히나": {
            "심은 결함": "(nan, nan) 을 물린다 — 모든 행이 「모름」 칸으로 간다",
            "심었나": True, "씨앗": ws,
            "안 심은 판": NW[PANEL_ALL]["개선(일)"], "심은 판": NW_nan[PANEL_ALL]["개선(일)"],
            "심은 판의 3수준 셀 가짓수": NW_nan[PANEL_ALL]["🔴 3수준 셀 가짓수"],
            "안 심은 판의 3수준 셀 가짓수": NW[PANEL_ALL]["🔴 3수준 셀 가짓수"],
            "🔴 발화했나(개선이 바뀐다)":
                bool(NW_nan[PANEL_ALL]["개선(일)"] != NW[PANEL_ALL]["개선(일)"])},
        "W5 다중집합 검사에 검정력이 있나": {
            "심은 결함": "같은 두 세계를 판 ②(b_prv=−1 제외)로 본다 — 티처 #75 C4 가 False 라고 잰 자리",
            "심었나": True, "씨앗": ws,
            "판 ①(안 심음)": ms_all, "판 ②(심음)": ms_exc,
            "🔴 발화했나(심으면 False 가 나온다)":
                bool(ms_all["🔴 같은가"] and not ms_exc["🔴 같은가"])},
        "W6 비교가능성 관문이 발화하나": {
            "심은 결함": "귀무의 기후값 MAE 를 ×1.10",
            "심었나": True, "씨앗": ws,
            "안 심은 판": {"상대차": cmp_good["🔴 상대차"], "통과": cmp_good["🔴 통과"]},
            "심은 판": {"상대차": cmp_bad["🔴 상대차"], "통과": cmp_bad["🔴 통과"]},
            "🔴 발화했나(심으면 불통과)": bool(cmp_good["🔴 통과"] and not cmp_bad["🔴 통과"])},
        "W9 입력이 925·928·933 과 같은 파일인가(음성 대조)": {
            "심었나": False, "🔴 통과": sha == NPZ_SHA},
        "W10 진짜 개선이 오라클 산출물과 같은가(음성 대조)": {
            "심었나": False,
            "🔴 통과": bool(RR[PANEL_ALL]["개선(일)"] == REAL_IMP_ALL
                        and RR[PANEL_EXC]["개선(일)"] == REAL_IMP_EXC)},
        "W11 사전등록이 stamp 이후 안 바뀌었나(음성 대조)": {
            "심었나": False, "🔴 통과": bool(prereg_now == prereg_stamped)},
    }
    _log("③ 배선 W1~W6·W9~W11 완료", time.time() - t0)

    # ── ④ 파일럿 → 🔴 관문 검정력 먼저 · 그 다음 경험분포 검출력 ────────────
    pilot_vals, pilot_base, pilot_rel = [], [], []
    real_cmp_all = cmp_pack(RR[PANEL_ALL], tab_real)
    for s in PILOT:
        d2, m2, _mv, _hh = null_n2_plantable(first, r, seed=s)
        tbp = gaps_from_events(d2, m2, V, OBS, DAY0)
        rp = rows_pair(tbp, tr_set, ho_set, cal_off=False)
        pilot_vals.append(rp[PANEL_ALL]["개선(일)"])
        pilot_base.append(rp[PANEL_ALL]["그 판의 기준 팔 MAE"])
        pilot_rel.append(comparability(real_cmp_all,
                                       cmp_pack(rp[PANEL_ALL], tbp))["🔴 상대차"])
    gate_pilot = {
        "🔴 왜 먼저 보나": "933 의 「200/200 통과 · 상대차 0.0」은 통과가 아니라 **원리상 발화 불가**였다"
                    "(귀무 기준 팔 MAE 가짓수 = 1 · 티처 #76 M1). 그래서 파일럿에서 **가짓수부터** 센다",
        "파일럿 씨앗": list(PILOT),
        "귀무 기준 팔 MAE": _mae_variety(pilot_base),
        "진짜 기준 팔 MAE": RR[PANEL_ALL]["그 판의 기준 팔 MAE"],
        "상대차 평균": float(np.mean(pilot_rel)),
        "상대차 최소·최대": [float(np.min(pilot_rel)), float(np.max(pilot_rel))],
        "🔴 한쪽 방향인가": bool(np.all(np.asarray(pilot_rel) > 0)
                          or np.all(np.asarray(pilot_rel) < 0)),
    }
    out["④-가 🔴 관문의 검정력 — 파일럿에서 먼저 본다 (티처 #76 M1)"] = gate_pilot
    shape = np.asarray(list(json.loads(
        (ROOT / "runners/out928_draws.json").read_text(encoding="utf-8"))["draws"].values()), float)
    pw = empirical_power_k(np.asarray(pilot_vals, float), RR[PANEL_ALL]["개선(일)"],
                           shape, ndraw=NDRAW, alpha=ALPHA)
    pw["🔴 파일럿 씨앗(판정에 안 쓴다)"] = list(PILOT)
    pw["🔴 모양을 빌린 곳"] = "runners/out928_draws.json — [둘 다] 판의 200뽑기(표준화해서 모양만 쓴다)"
    pw["🔴 관문이 아니다"] = "검출력 관문을 두면 결과가 나쁠 때 빠져나가는 도피구가 된다(사전등록 §3)"
    out["④-나 🔴 검출력 — 경험분포로 냈다(정규 근사 안 씀 · k ≤ kmax 를 이항 꼬리로)"] = pw
    _log("④ 파일럿·검출력", time.time() - t0)

    # ── ⑤ 판정 200뽑기 ────────────────────────────────────────────────
    recs, failed, ms_bad_all = {}, {}, []
    tdraw0 = time.time()
    real_cmp = {p: cmp_pack(RR[p], tab_real) for p in PANELS}
    for s in range(1, NDRAW + 1):
        try:
            d2, m2, mv, _hh = null_n2_plantable(first, r, seed=s)
            tb = gaps_from_events(d2, m2, V, OBS, DAY0)
            if not np.array_equal(tb["gi"], tab_real["gi"]):
                failed[s] = "행 격자 배열이 진짜와 다르다"
                continue
            R = rows_pair(tb, tr_set, ho_set, cal_off=False)
            if not all(np.isfinite(R[p]["개선(일)"]) for p in PANELS):
                failed[s] = "개선이 NaN"
                continue
            rec = {"씨앗": s, "간격 순서가 바뀐 격자 비율": mv,
                   "🔴 mag 경계가 진짜와 같은가":
                       bool(tuple(R[PANEL_ALL]["mag 3분위 경계"]) == REAL_MAG_CUTS),
                   "🔴 전체 중앙값이 진짜와 같은가":
                       bool(R[PANEL_ALL]["전체 중앙값"] == RR[PANEL_ALL]["전체 중앙값"]),
                   "판①개선 − 판②개선": R[PANEL_ALL]["개선(일)"] - R[PANEL_EXC]["개선(일)"]}
            for p in PANELS:
                ms = multiset_same(RR[p], R[p])
                cm = comparability(real_cmp[p], cmp_pack(R[p], tb))
                rec[p] = {
                    "개선(일)": R[p]["개선(일)"],
                    "prevmed 3분위 경계": R[p]["prevmed 3분위 경계"],
                    "mag 3분위 경계": R[p]["mag 3분위 경계"],
                    "전체 중앙값": R[p]["전체 중앙값"],
                    "기준 팔 MAE": R[p]["그 판의 기준 팔 MAE"],
                    "시험 팔 MAE": R[p]["그 판의 시험 팔 MAE"],
                    "3수준 셀 가짓수": R[p]["🔴 3수준 셀 가짓수"],
                    "달력 셀 가짓수": R[p]["🔴 달력 셀 가짓수"],
                    "🔴 정답 다중집합 동일": ms["🔴 같은가"],
                    "정답 중앙값(진짜/귀무)": ms["정답 중앙값"],
                    "🔴 비교가능성 통과": cm["🔴 통과"],
                    "비교가능성 상대차": cm["🔴 상대차"],
                }
            recs[s] = rec
            if not rec[PANEL_ALL]["🔴 정답 다중집합 동일"]:
                ms_bad_all.append({"씨앗": s, "검사": multiset_same(RR[PANEL_ALL], R[PANEL_ALL])})
        except Exception as e:                       # 🔴 조용히 빠뜨리지 않는다
            failed[s] = f"{type(e).__name__}: {e}"
        if s % 10 == 0:
            el = time.time() - tdraw0
            _log(f"  뽑기 {s}/{NDRAW} · {el:.1f}s · 뽑기당 {el/s:.2f}s · "
                 f"①={recs.get(s, {}).get(PANEL_ALL, {}).get('개선(일)')} "
                 f"②={recs.get(s, {}).get(PANEL_EXC, {}).get('개선(일)')}")
            CKPT.write_text(json.dumps(_scrub({"recs": recs, "failed": failed}),
                                       ensure_ascii=False), encoding="utf-8")
    CKPT.write_text(json.dumps(_scrub({"recs": recs, "failed": failed}),
                               ensure_ascii=False), encoding="utf-8")
    out["⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다"] = {
        "성공한 뽑기(분모)": len(recs), "실패한 뽑기": failed,
        "뽑기당 초": (time.time() - tdraw0) / max(len(recs), 1),
        "기록": [recs[s] for s in sorted(recs)],
    }
    # ⑤-나 연습 주행 대조 — 🔴 같은 씨앗이면 비트로 같아야 한다
    if TAG == "":
        cmp_rows = []
        for sp in smoke:
            smk = json.loads((ROOT / sp).read_text(encoding="utf-8"))
            for r0 in smk.get("⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다", {}).get("기록", []):
                s0 = r0["씨앗"]
                if s0 in recs:
                    cmp_rows.append({
                        "연습 산출물": sp, "씨앗": s0,
                        "연습 ①": r0[PANEL_ALL]["개선(일)"],
                        "본 주행 ①": recs[s0][PANEL_ALL]["개선(일)"],
                        "연습 ②": r0[PANEL_EXC]["개선(일)"],
                        "본 주행 ②": recs[s0][PANEL_EXC]["개선(일)"],
                        "🔴 비트로 같은가":
                            bool(r0[PANEL_ALL]["개선(일)"] == recs[s0][PANEL_ALL]["개선(일)"]
                                 and r0[PANEL_EXC]["개선(일)"] == recs[s0][PANEL_EXC]["개선(일)"]),
                    })
        out["⑤-나 🔴 연습 주행 대조 (지우지 않았다 · 이슈 #182)"] = {
            "대조한 씨앗 수": len(cmp_rows), "행": cmp_rows,
            "🔴 전부 비트로 같은가": bool(cmp_rows) and all(x["🔴 비트로 같은가"] for x in cmp_rows),
        }
    if ms_bad_all:
        out["🔴🔴 §5-나 발화 — 판 ① 의 정답 다중집합이 깨진 뽑기가 있다"] = ms_bad_all
        out["🔴 판정"] = ("§7-3 — 원판에서도 정답 다중집합이 깨졌다. "
                       "사전등록대로 여기서 멈추고 신고한다. 판정을 안 낸다")
        _finish(out, t0, tstart)
        return
    _log("⑤ %d뽑기 완료" % NDRAW, time.time() - t0)

    # ── ⑤-다 🔴 관문의 검정력 — 판정 뽑기 전량에서 ──────────────────────
    seeds = sorted(recs)
    gate = {}
    for p in PANELS:
        rel = np.asarray([recs[s][p]["비교가능성 상대차"] for s in seeds], float)
        gate[p] = {
            "귀무 기준 팔 MAE": _mae_variety([recs[s][p]["기준 팔 MAE"] for s in seeds]),
            "진짜 기준 팔 MAE": RR[p]["그 판의 기준 팔 MAE"],
            "상대차": {"평균": float(rel.mean()), "최소": float(rel.min()),
                    "최대": float(rel.max()), "절대 최대": float(np.abs(rel).max()),
                    "🔴 한쪽 방향인가": bool((rel > 0).all() or (rel < 0).all())},
            "🔴 통과한 뽑기": int(sum(recs[s][p]["🔴 비교가능성 통과"] for s in seeds)),
            "분모": len(seeds),
            "🔴 정답 다중집합이 같은 뽑기": int(sum(recs[s][p]["🔴 정답 다중집합 동일"] for s in seeds)),
            "🔴 정답 중앙값(진짜/귀무) 첫 뽑기": recs[seeds[0]][p]["정답 중앙값(진짜/귀무)"],
        }
    out["⑤-다 🔴 비교가능성 관문 — 검정력과 실측 (티처 #76 M1)"] = {
        **gate,
        "🔴 이 판에서 관문이 발화 가능한가": gate[PANEL_ALL]["귀무 기준 팔 MAE"]["🔴 관문에 검정력이 있나(가짓수 ≥ 2)"],
        "🔴 933 과의 대조": "933([달력제거])에서는 가짓수가 **1**(12.185793445372024)이라 관문이 "
                      "**원리상 발화 불가**였다. 원판은 기준 팔이 상수가 아니다",
    }

    # ── ⑥ 판별 · 상태표 · 부호 결정 · BCa ──────────────────────────────
    verdict = {}
    for p in PANELS:
        vals = [recs[s][p]["개선(일)"] for s in seeds]
        pp = perm_p(RR[p]["개선(일)"], vals)
        pp["🔴 α 의 k 동치 조건(러너가 계산)"] = p_equivalence(ALPHA, len(seeds))
        pp["🔴 p < α 인가"] = bool(pp["🔴 순열 p = (1+k)/(1+B)"] < ALPHA)
        sub = [s for s in seeds if recs[s][p]["🔴 비교가능성 통과"]]
        pp_sub = perm_p(RR[p]["개선(일)"], [recs[s][p]["개선(일)"] for s in sub]) if sub else None
        pp["🔴 비교가능성 통과분만의 p(병기 · 판정에 안 쓴다)"] = ({
            "분모": len(sub), "p": pp_sub["🔴 순열 p = (1+k)/(1+B)"],
            "k": pp_sub["🔴 귀무 ≥ 진짜 인 뽑기 수 k"],
            "🔴 1차와 같은가": bool(pp_sub["🔴 순열 p = (1+k)/(1+B)"]
                            == pp["🔴 순열 p = (1+k)/(1+B)"])} if sub else
            {"분모": 0, "🔴 통과한 뽑기가 없다": True})
        st = _state_table(vals, [recs[s][p]["prevmed 3분위 경계"] for s in seeds])
        pp["🔴 경계 상태별 표"] = st
        pp["🔴 z·SD·왜도·첨도를 해석해도 되나"] = (
            "🔴 안 된다 — 상태가 %d개인 혼합의 요약이다" % st["상태 수"] if st["상태 수"] > 1
            else "된다 — 상태가 하나다")
        pp["🔴 mag 경계가 뽑기 내내 진짜와 같았나"] = {
            "같은 뽑기": int(sum(recs[s]["🔴 mag 경계가 진짜와 같은가"] for s in seeds)),
            "분모": len(seeds)}
        pp["🔴 전체 중앙값이 뽑기 내내 진짜와 같았나"] = {
            "같은 뽑기": int(sum(recs[s]["🔴 전체 중앙값이 진짜와 같은가"] for s in seeds)),
            "분모": len(seeds)}
        pp["🔴 판정에 쓰나"] = bool(p in JUDGED)
        verdict[p] = pp
        _log("⑥", p, "p=", pp["🔴 순열 p = (1+k)/(1+B)"],
             "k=", pp["🔴 귀무 ≥ 진짜 인 뽑기 수 k"], "상태 수=", st["상태 수"])

    # W7 · W8 (뽑기 위에서만 심을 수 있다)
    va = np.asarray([recs[s][PANEL_ALL]["개선(일)"] for s in seeds], float)
    w7 = perm_p(va[0], list(va[1:]))
    wires["W7 p 가 정말 순위로 나오나"] = {
        "심은 결함": "귀무 뽑기 하나(씨앗 %d)를 진짜 자리에 놓는다" % seeds[0],
        "심었나": True, "심은 판 p": w7["🔴 순열 p = (1+k)/(1+B)"],
        "안 심은 판 p": verdict[PANEL_ALL]["🔴 순열 p = (1+k)/(1+B)"],
        "🔴 발화했나(심으면 p 가 커진다)":
            bool(w7["🔴 순열 p = (1+k)/(1+B)"] > verdict[PANEL_ALL]["🔴 순열 p = (1+k)/(1+B)"])}
    wires["W8 씨앗이 먹히나"] = {
        "심은 결함": "(대조) 모든 뽑기가 같은 씨앗이면 서로 다른 값의 개수가 1 이 된다",
        "심었나": True, "서로 다른 값의 개수": int(np.unique(va).size), "뽑기 수": len(seeds),
        "🔴 발화했나": bool(np.unique(va).size == len(seeds)),
        "🔴 933 은 여기서 놓쳤다": "933 의 W8 은 192/200 이었고(티처 #76 C1) 그 사실이 "
                          "논문·원장·카드에서 200/200 으로 잘못 인용됐다"}
    n_planted = sum(1 for v in wires.values() if v.get("심었나"))
    n_fired = sum(1 for v in wires.values() if v.get("심었나")
                  and any(k.startswith("🔴 발화했나") and vv for k, vv in v.items()))
    n_neg = sum(1 for v in wires.values() if not v.get("심었나"))
    n_neg_ok = sum(1 for v in wires.values() if not v.get("심었나") and v.get("🔴 통과"))
    unplantable = [
        "🔴 interval918 · perm922 · gap925 의 관 자체가 옳은가 — 그대로 import 한다",
        "🔴 daily.npz 가 옳게 만들어졌는가 — 만드는 러너가 저장소에 없다(4사이클 연속)",
        "🔴 N2(간격순서 순열)가 이 물음의 옳은 귀무인가 — 이 러너 안에서 못 심는다",
    ]
    out["③ 배선 검사 — 🔴 **본 주행** 회계 · 분모를 둘로 낸다"] = {
        "🔴 이 블록은 본 주행의 수다": True,
        "검사": wires,
        "🔴 본 주행 배선 — 심은 수": n_planted,
        "🔴 본 주행 배선 — 발화한 수": n_fired,
        "🔴 본 주행 배선 — 놓친 수": n_planted - n_fired,
        "본 주행 음성 대조 수": n_neg, "본 주행 음성 대조 통과": n_neg_ok,
        "🔴 못 심은 수": len(unplantable), "🔴 못 심은 것(검정력 0 으로 신고)": unplantable,
        "🔴 933 의 넷째를 뺐다": "「경계 강제의 부호를 못 정한다」는 못 심는 것이 아니었다"
                        "(티처 #74 M5 → #75 M2 → #76 M2 · 3세대). 이번엔 ⑥-다 에서 **정한다**",
        "🔴 본 주행 검정력(심은 것 기준)": f"{n_fired}/{n_planted} = {n_fired/n_planted:.3f}",
        "🔴🔴 본 주행 검정력(못 심은 것까지 분모에)":
            f"{n_fired}/{n_planted+len(unplantable)} = {n_fired/(n_planted+len(unplantable)):.3f}",
    }
    out["⑥ 🔴 판정용 순열"] = verdict

    # ⑥-나 두 판의 상관 — 🔴 「독립 확인 측정」이라 부르지 않으려고 (티처 #76 M6)
    vb = np.asarray([recs[s][PANEL_EXC]["개선(일)"] for s in seeds], float)
    vc = np.asarray([recs[s][PANEL_ONLY]["개선(일)"] for s in seeds], float)
    out["⑥-나 🔴 판 ① 과 판 ② 는 독립이 아니다 (티처 #76 M6)"] = {
        "corr(판①, 판②)": float(np.corrcoef(va, vb)[0, 1]),
        "corr(판①, 진단③)": float(np.corrcoef(va, vc)[0, 1]),
        "🔴 같은 귀무 세계를 쓴다": True,
        "🔴 그래서": "판 ② 를 **노트 133 의 독립 확인 측정이라 부르지 않는다**. "
                "같은 200 세계 위의 **다른 행 집합**이다",
    }

    # ⑥-다 🔴 부호를 정한다 (사전등록 §6 — 「모른다」로 안 적는다)
    dif = np.asarray([recs[s]["판①개선 − 판②개선"] for s in seeds], float)
    real_dif = RR[PANEL_ALL]["개선(일)"] - RR[PANEL_EXC]["개선(일)"]
    rel_exc = np.asarray([recs[s][PANEL_EXC]["비교가능성 상대차"] for s in seeds], float)
    out["⑥-다 🔴 부호를 정한다 — b_prv=−1 칸을 빼면 누가 손해인가"] = {
        "㉠ 판①개선 − 판②개선": {
            "진짜": real_dif, "귀무 평균": float(dif.mean()),
            "귀무 SD(ddof=1)": float(dif.std(ddof=1)),
            "진짜가 귀무보다 큰 뽑기": int((dif < real_dif).sum()), "분모": len(seeds),
            "🔴 뜻": "이 차가 진짜에서 더 크면 **그 칸이 진짜에게 더 많이 이바지한다** — "
                  "칸을 빼는 것은 **진짜에게 불리하다(보수적이다)**"},
        "㉡ 판 ② 의 기준 팔 MAE 상대차(귀무 − 진짜)/진짜": {
            "평균": float(rel_exc.mean()), "최소": float(rel_exc.min()),
            "최대": float(rel_exc.max()),
            "양수인 뽑기": int((rel_exc > 0).sum()), "분모": len(seeds),
            "🔴 뜻": "양수면 귀무의 남은 정답이 기후값에서 **더 멀다** — 그 판에서 귀무가 "
                  "**더 어려운 정답**을 받는다"},
        "🔴 결론(부호)": None,          # ⑦ 에서 채운다
    }

    # 짝지은 군집 BCa (규약 47) — 씨앗 922 와의 짝. 판정의 자가 아니라 크기의 보조
    n922d, n922m, _mv, _hh = null_n2_plantable(first, r, seed=922)
    tb922 = gaps_from_events(n922d, n922m, V, OBS, DAY0)
    R922 = rows_pair(tb922, tr_set, ho_set, cal_off=False)
    pr = {p: paired(RR[p], R922[p], B=B_BOOT, seed=SEED) for p in PANELS}
    pr["🔴 씨앗 922 는 판정 뽑기(1…%d)에 안 들어 있다" % NDRAW] = True
    pr["🔴 이 구간은 판정의 자가 아니다"] = (
        "판정의 근거는 순열 p 다. 규약 47 은 **구간을 lab.pairboot.cluster_boot 의 BCa 로 내라**는 "
        "규약이고 그것은 지켰다(폴백이면 사유 필드). 🔴 티처 #75 M3 의 정정: 짝지은 BCa 는 "
        "못 믿을 물건이 아니라 **상태 차를 정확히 집어내는 것**이다")
    out["⑥-라 짝지은 군집 BCa (규약 47 · 보조)"] = pr

    # ── ⑦ 판정 ────────────────────────────────────────────────────────
    pA = verdict[PANEL_ALL]["🔴 순열 p = (1+k)/(1+B)"]
    pB = verdict[PANEL_EXC]["🔴 순열 p = (1+k)/(1+B)"]
    sA, sB = pA < ALPHA, pB < ALPHA
    if sA and sB:
        head = ("**①·② 둘 다 p < 0.01 — 「순서는 잡힌다」가 한 칸 밖에서도 산다.** "
                "효과의 대부분을 나르는 첫 간격 칸(b_prv=−1 · 행의 4.15%)을 통째로 빼도 순열이 진다")
    elif sA and not sB:
        head = ("🔴 **② 가 무너졌다 — 옳은 문장은 「격자의 첫 간격은 그 격자의 다른 간격들보다 길고, "
                "표가 그 한 칸을 배운다」이고 그것이 이 자료가 지지하는 전부다.** "
                "933·928 의 헤드라인은 **한 칸의 이름**이었다")
    else:
        head = ("🔴 **① 이 무너졌다 — 원판에서는 못 이긴다.** 933 의 p=0.004975 는 판 선택의 산물이고, "
                "기준 팔이 상수가 아닌 판에서는 살아남지 못한다")
    eff_A = verdict[PANEL_ALL]["🔴 효과(진짜 − 귀무평균 · 일)"]
    eff_B = verdict[PANEL_EXC]["🔴 효과(진짜 − 귀무평균 · 일)"]
    sign_txt = ("칸을 빼는 것은 **진짜에게 불리하다(보수적이다)** — "
                "판①−판② 차가 진짜(%.6f)에서 귀무 평균(%.6f)보다 크다" % (real_dif, dif.mean())
                if real_dif > dif.mean() else
                "칸을 빼는 것은 **진짜에게 유리하다** — 판①−판② 차가 진짜(%.6f)에서 "
                "귀무 평균(%.6f)보다 작다" % (real_dif, dif.mean()))
    out["⑥-다 🔴 부호를 정한다 — b_prv=−1 칸을 빼면 누가 손해인가"]["🔴 결론(부호)"] = {
        "부호": "진짜에게 불리(보수적)" if real_dif > dif.mean() else "진짜에게 유리",
        "문장": sign_txt,
        "🔴 「모른다」로 안 적었다": True,
        "기준 MAE 방향": ("귀무의 남은 정답이 더 어렵다(상대차 평균 %+.6f)" % rel_exc.mean()
                    if rel_exc.mean() > 0 else
                    "진짜의 남은 정답이 더 어렵다(상대차 평균 %+.6f)" % rel_exc.mean()),
    }
    out["🔴🔴 판정 (사전등록 §4 를 기계로 적용)"] = {
        "§4-① 원판 전량": {"p": pA, "k": verdict[PANEL_ALL]["🔴 귀무 ≥ 진짜 인 뽑기 수 k"],
                       "문턱": ALPHA, "동치 조건": p_equivalence(ALPHA, len(seeds))["🔴 p < α 의 동치 조건"],
                       "🔴 p < 0.01 인가": bool(sA)},
        "§4-② b_prv=−1 칸 제외": {"p": pB, "k": verdict[PANEL_EXC]["🔴 귀무 ≥ 진짜 인 뽑기 수 k"],
                            "문턱": ALPHA, "🔴 p < 0.01 인가": bool(sB)},
        "🔴🔴 헤드라인(사전등록이 미리 써 둔 셋 중 하나)": head,
        "§4-크기 — 🔴 측정 전에 정해졌다(규율 4 개정판 · 판정용은 **개선** 눈금)": {
            "채택 크기 X(일 · 개선 눈금)": SIZE_X,
            "판 ①": {"Y(LOO)": ORACLE_Y_ALL, "Z = X/Y": SIZE_X / ORACLE_Y_ALL,
                   "🔴 Z > 1": bool(SIZE_X / ORACLE_Y_ALL > 1),
                   "진짜 개선": REAL_IMP_ALL,
                   "천장의 몇 %": 100.0 * REAL_IMP_ALL / ORACLE_Y_ALL,
                   "🔴 몇 배 모자라나(개선 눈금 · 판정용)": SIZE_X / REAL_IMP_ALL,
                   "효과(일 · 병기 · 판정에 안 쓴다)": eff_A,
                   "효과(분 · 병기)": eff_A * 24 * 60,
                   "몇 배 모자라나(효과 눈금 · 🔴 판정에 안 쓴다)": SIZE_X / eff_A if eff_A else None},
            "판 ②": {"Y(LOO)": ORACLE_Y_EXC, "Z = X/Y": SIZE_X / ORACLE_Y_EXC,
                   "🔴 Z > 1": bool(SIZE_X / ORACLE_Y_EXC > 1),
                   "진짜 개선": REAL_IMP_EXC,
                   "천장의 몇 %": 100.0 * REAL_IMP_EXC / ORACLE_Y_EXC,
                   "🔴 몇 배 모자라나(개선 눈금 · 판정용)": SIZE_X / REAL_IMP_EXC,
                   "효과(일 · 병기)": eff_B, "효과(분 · 병기)": eff_B * 24 * 60},
            "🔴 판정": "**두 판 다 Z > 1 — 이 자로는 원리상 못 넘는다.** 문턱이 아니라 조건 열을 바꿔야 한다",
            "🔴 눈금": "판정은 **개선** 눈금 하나로 한다(티처 #76 C4). 효과 눈금은 병기다",
        },
        "§4-다 진단 ③(판정에 안 들어간다)": {
            "p": verdict[PANEL_ONLY]["🔴 순열 p = (1+k)/(1+B)"],
            "k": verdict[PANEL_ONLY]["🔴 귀무 ≥ 진짜 인 뽑기 수 k"],
            "진짜 개선(일)": REAL_IMP_ONLY, "Y(LOO)": ORACLE_Y_ONLY,
            "Z = X/Y": SIZE_X / ORACLE_Y_ONLY,
            "🔴 여기서는 Z < 1 이다": bool(SIZE_X / ORACLE_Y_ONLY < 1),
            "🔴 그런데 왜 판정에 안 쓰나": "① 진짜와 귀무의 정답이 아예 다른 값들이다 "
                                "② 비교가능성 관문이 원리상 걸린다 ③ prevmed 층 오라클이 칸 1개로 퇴화한다. "
                                "🔴 **수는 남기되 결론 문장에 안 쓴다**(사전등록 §4-다)",
        },
        "🔴 노트 133": "판 ② 는 판 ① 과 **같은 귀무 세계**를 쓴다 — **독립 확인 측정이 아니다**"
                   "(티처 #76 M6 이 933 에서 잡은 오용을 안 되풀이한다)",
    }
    _finish(out, t0, tstart)


if __name__ == "__main__":
    main()
