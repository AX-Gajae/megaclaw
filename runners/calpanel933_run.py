# -*- coding: utf-8 -*-
"""팔 933 — **[달력제거] 판 200뽑기** + **경계 강제 판** (사전등록 `docs/prereg_933_calpanel.md`).

🔴 순서가 규약이다:
    ① 입력·분모 대조 → ② 항등 검사(W1·W2·W3) → ③ 배선 검사(W4~W9)
    → ④ 파일럿 20뽑기로 **경험분포 검출력** → ⑤ 판정 200뽑기(판 둘)
    → ⑥ 경계 상태별 표 · 짝지은 BCa(규약 47) → ⑦ 판정(사전등록 §4 를 기계로 적용)

🔴 멈추는 조건(사전등록 §7): npz sha 불일치 · 항등 검사 불일치 ·
   **다중집합 동일성이 한 뽑기라도 False** · 진짜 개선이 오라클 산출물과 비트로 다르다.

산출물: runners/out933_calpanel.json
사용:   python3 runners/calpanel933_run.py     (🔴 파이프 금지 — 리디렉션으로)
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
from state.calpanel933 import (cmp_pack, empirical_power, fit_identity,  # noqa: E402
                               multiset_same, rows_x)

SCRATCH = Path(os.environ.get(
    "G933_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/"
    "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad"))
NPZ = Path(os.environ.get("G933_NPZ", str(SCRATCH / "g922/daily.npz")))
TAG = os.environ.get("G933_TAG", "")          # 🔴 연습 주행은 TAG 로 정본을 안 덮는다
OUT = ROOT / f"runners/out933_calpanel{TAG}.json"
CKPT = SCRATCH / f"g933/draws{TAG}.json"
NDRAW = int(os.environ.get("G933_NDRAW", "200"))
PILOT = tuple(range(901, 901 + int(os.environ.get("G933_NPILOT", "20"))))
B_BOOT = int(os.environ.get("G933_B", "2000"))
SEED = 918

NPZ_SHA = "4472b7f69cb5170c8a804dfbdb72a0289dcd34936aa5e05b6e9e191878ae97b2"
#: 사전등록 §1 이 측정 전에 박은 수(오라클 부속 산출물에서 왔다)
REAL_IMP_CAL = 0.32380336116073055
REAL_PRV_CUTS = (4.5, 7.0)
REAL_MAG_CUTS = (1.2909221321296984, 1.624097296793309)
ORACLE_Y = 0.328387590682075
SIZE_X = 1.0
PANEL_A = "① [달력제거]"
PANEL_B = "② [달력제거·경계강제]"


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


def _state_table(recs, key="prevmed 3분위 경계") -> dict:
    """🔴 경계 상태별로 갈라 센다 — 그래야 z·SD·왜도·첨도가 해석 가능해진다."""
    st = {}
    for r in recs:
        k = tuple(r[key])
        st.setdefault(k, []).append(r["개선(일)"])
    rows = []
    for k, v in sorted(st.items(), key=lambda kv: -len(kv[1])):
        a = np.asarray(v, float)
        rows.append({"경계": list(k), "개수": int(a.size), "평균": float(a.mean()),
                     "상태 내 SD(ddof=1)": float(a.std(ddof=1)) if a.size > 1 else None,
                     "최소": float(a.min()), "최대": float(a.max())})
    allv = np.asarray([r["개선(일)"] for r in recs], float)
    return {"상태 수": len(rows), "상태별": rows,
            "전체 SD(ddof=1)": float(allv.std(ddof=1)),
            "🔴 상태가 둘 이상인가(= 전체 z·SD·왜도·첨도는 혼합의 요약이라 해석 불가)":
                bool(len(rows) > 1)}


def main() -> None:
    t0 = time.time()
    tstart = dt.datetime.now(dt.timezone.utc)
    CKPT.parent.mkdir(parents=True, exist_ok=True)
    stamp = json.loads((ROOT / "runners/out933_prereg_stamp.json").read_text(encoding="utf-8"))
    out: dict = {
        "팔": "933 — [달력제거] 판 200뽑기 + 경계 강제 판",
        "사전등록": "docs/prereg_933_calpanel.md",
        "티처": "runners/out929_teacher.json (#75 C1·C2·C4 · M1 · docs/목표.md 규율 4)",
        "🔴 판 ρ": "한 번도 안 돌렸다(13사이클 연속). 이 팔의 자는 순열 200뽑기와 짝지은 군집 BCa 둘이다",
        "🔴 사전등록 시각 증거": {
            "stamp": "runners/out933_prereg_stamp.json",
            "stamp 이 박은 사전등록 sha256":
                stamp["파일별 sha256·mtime"]["docs/prereg_933_calpanel.md"]["sha256"],
            "사전등록 sha256(지금 다시 계산)": sha256_text(ROOT / "docs/prereg_933_calpanel.md"),
            "🔴 같은가": sha256_text(ROOT / "docs/prereg_933_calpanel.md") ==
                     stamp["파일별 sha256·mtime"]["docs/prereg_933_calpanel.md"]["sha256"],
            "stamp 를 쓴 시각(UTC)": stamp["이 stamp 를 쓴 시각(UTC)"],
            "측정 시작(UTC)": tstart.isoformat(timespec="microseconds"),
            "🔴 stamp 가 측정보다 먼저인가":
                stamp["이 stamp 를 쓴 시각(UTC)"] < tstart.isoformat(timespec="microseconds"),
            "🔴 사전등록만 담은 커밋을 측정 전에 만들었나": True,
            "🔴 os.utime 을 썼나": False,
        },
        "🔴 러너 실행 이력 — 자백한다": {
            "이 산출물 전에 완주한 횟수": 1,
            "그것": "G933_TAG=_smoke · G933_NDRAW=4 · G933_NPILOT=3 → runners/out933_calpanel_smoke.json "
                  "(37.2초 · 배선 6/6 발화 · 다중집합 4/4 True)",
            "🔴 연습 주행이 판정 씨앗 1~4 를 이미 돌았다": True,
            "🔴 그래서 무엇이 남나": "뽑기는 씨앗에 대해 결정적이라 본 주행과 **비트로 같아야 한다**. "
                            "⑤-나 가 그것을 대조한다. 값을 보고 규칙을 고칠 자유도는 없다 — "
                            "판정 규칙은 사전등록 커밋 8fa99dfbf 에 이미 들어가 있다",
            "🔴 지웠나": "안 지웠다(이슈 #182 · 928 자기적발 ③ — 자백이 가리키는 물건은 남긴다)",
            "그 뒤에 고친 것": ["이 자백 필드", "⑤-나 연습 주행 대조 블록"],
            "🔴 안 고친 것": "자 · 귀무의 정의 · 뽑기 수 · 판정 문턱 · 판정 분기 — 한 자리도 안 건드렸다",
        },
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/calpanel933.py", "runners/calpanel933_run.py",
                        "runners/calpanel933_oracle.py", "state/paired928.py",
                        "state/gap925.py", "state/perm922.py", "state/interval918.py")},
        "설정": {"τ": TAU_PRIMARY, "기저선 lag": list(BASE_LAGS), "셀 최소 학습행": CELL_MIN,
               "뽑기 수": NDRAW, "판정 씨앗": "1 … %d (922 는 안 넣는다)" % NDRAW,
               "파일럿 씨앗": list(PILOT), "부트 B": B_BOOT, "부트 seed": SEED,
               "비교가능성 문턱": COMPARABLE_REL,
               "분할": f"격자 sha256('{SPLIT_SALT}'+격자) 70/30"},
    }

    # ── ① 입력 ────────────────────────────────────────────────────────
    sha = sha256_text(NPZ)
    out["① 입력"] = {"daily.npz(🔴 저장소 밖)": str(NPZ), "sha256": sha,
                  "바이트": NPZ.stat().st_size,
                  "🔴 925·928 이 쓴 파일과 같은가(W9)": sha == NPZ_SHA,
                  "🔴 못 심는 것": "이 파일을 만드는 러너가 저장소에 없다(3사이클 연속 · 티처 #75 m6)"}
    if sha != NPZ_SHA:
        out["🔴 판정"] = "§7-1 — 입력이 925·928 과 다르다. 판정을 안 낸다"
        _finish(out, t0, tstart)
        return

    z = np.load(NPZ, allow_pickle=False)
    V = z["V"].astype(np.float64)
    C = z["C"]
    grids = z["grids"].tolist()
    OBS = C > 0
    G, D = V.shape
    assert D == NDAY, (D, NDAY)
    obs_frac = OBS.mean(axis=1)
    qualify = obs_frac >= OBS_MIN_FRAC
    _base, r, ok = baseline_ratio(V, OBS)
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
    real_A = rows_x(tab_real, tr_set, ho_set, cal_off=True, drop_first=False)
    real_forced = rows_x(tab_real, tr_set, ho_set, cal_off=True, drop_first=False,
                         force_prv_cuts=REAL_PRV_CUTS)
    ref = improvement_rows(tab_real, tr_set, ho_set, cal_off=True, drop_first=False)
    ident = {
        "W1 fit_tables_x 가 원본과 같은 표인가(cal_off=True)":
            fit_identity(tab_real, trm, plant_const_cal=True),
        "W2 rows_x 가 paired928.improvement_rows 와 같은 개선인가": {
            "paired928": ref["개선(일)"], "calpanel933": real_A["개선(일)"],
            "🔴 비트로 같은가": bool(ref["개선(일)"] == real_A["개선(일)"]),
            "행·군집": [real_A["행(간격) 수"], real_A["군집(격자) 수"]],
        },
        "W3b 진짜에 진짜의 경계를 강제하면 아무것도 안 바뀌나": {
            "강제 전": real_A["개선(일)"], "강제 뒤": real_forced["개선(일)"],
            "🔴 비트로 같은가": bool(real_A["개선(일)"] == real_forced["개선(일)"]),
        },
        "사전등록 §1 이 박은 진짜 개선과 같은가": {
            "사전등록": REAL_IMP_CAL, "지금": real_A["개선(일)"],
            "🔴 비트로 같은가": bool(real_A["개선(일)"] == REAL_IMP_CAL)},
        "진짜의 3분위 경계": {"prevmed": real_A["prevmed 3분위 경계"],
                      "mag": real_A["mag 3분위 경계"],
                      "전체 중앙값": real_A["전체 중앙값"],
                      "🔴 사전등록과 같은가":
                          bool(tuple(real_A["prevmed 3분위 경계"]) == REAL_PRV_CUTS
                               and tuple(real_A["mag 3분위 경계"]) == REAL_MAG_CUTS)},
    }
    stop2 = not (ident["W1 fit_tables_x 가 원본과 같은 표인가(cal_off=True)"]["🔴 같은가"]
                 and ident["W2 rows_x 가 paired928.improvement_rows 와 같은 개선인가"]["🔴 비트로 같은가"]
                 and ident["W3b 진짜에 진짜의 경계를 강제하면 아무것도 안 바뀌나"]["🔴 비트로 같은가"]
                 and ident["사전등록 §1 이 박은 진짜 개선과 같은가"]["🔴 비트로 같은가"])
    out["② 항등 검사 (사전등록 §7-2·§7-4)"] = {**ident, "🔴 전부 통과": not stop2}
    if stop2:
        out["🔴 판정"] = "§7 — 항등 검사가 깨졌다. 판정을 안 낸다"
        _finish(out, t0, tstart)
        return
    _log("② 항등 검사 통과", time.time() - t0)

    # ── ③ 배선 검사 (파일럿 씨앗 하나 위에서 심는다 — 판정 씨앗을 안 쓴다) ──
    ws = PILOT[0]
    dd, mm, moved, _h = null_n2_plantable(first, r, seed=ws)
    tb_w = gaps_from_events(dd, mm, V, OBS, DAY0)
    n_plain = rows_x(tb_w, tr_set, ho_set, cal_off=True, drop_first=False)
    n_own = rows_x(tb_w, tr_set, ho_set, cal_off=True, drop_first=False,
                   force_prv_cuts=tuple(n_plain["prevmed 3분위 경계"]))
    n_nan = rows_x(tb_w, tr_set, ho_set, cal_off=True, drop_first=False,
                   force_prv_cuts=(float("nan"), float("nan")))
    real_drop = rows_x(tab_real, tr_set, ho_set, cal_off=True, drop_first=True)
    null_drop = rows_x(tb_w, tr_set, ho_set, cal_off=True, drop_first=True)
    ms_ok = multiset_same(real_A, n_plain)
    ms_drop = multiset_same(real_drop, null_drop)
    cmp_good = comparability(cmp_pack(real_A, tab_real), cmp_pack(n_plain, tb_w))
    bad_pack = cmp_pack(n_plain, tb_w)
    bad_pack["가 기후값"] = {"MAE": bad_pack["가 기후값"]["MAE"] * 1.10}
    cmp_bad = comparability(cmp_pack(real_A, tab_real), bad_pack)
    wires = {
        "W1 fit_tables_x 항등(음성 대조)": {
            "심었나": False,
            "🔴 통과": ident["W1 fit_tables_x 가 원본과 같은 표인가(cal_off=True)"]["🔴 같은가"]},
        "W2 rows_x 항등(음성 대조)": {
            "심었나": False,
            "🔴 통과": ident["W2 rows_x 가 paired928.improvement_rows 와 같은 개선인가"]["🔴 비트로 같은가"]},
        "W3 경계 강제가 옳은 자리에 걸리나": {
            "심은 결함": "귀무에게 **자기 자신의** 경계를 강제로 물린다 — 아무것도 안 바뀌어야 한다",
            "심었나": True, "씨앗": ws,
            "강제 안 함": n_plain["개선(일)"], "자기 경계 강제": n_own["개선(일)"],
            "🔴 발화했나(비트로 같다)": bool(n_plain["개선(일)"] == n_own["개선(일)"])},
        "W4 경계 강제가 정말 먹히나": {
            "심은 결함": "(nan, nan) 을 물린다 — 모든 행이 「모름」 칸으로 간다",
            "심었나": True, "씨앗": ws,
            "안 심은 판": n_plain["개선(일)"], "심은 판": n_nan["개선(일)"],
            "심은 판의 3수준 셀 가짓수": n_nan["🔴 3수준 셀 가짓수"],
            "안 심은 판의 3수준 셀 가짓수": n_plain["🔴 3수준 셀 가짓수"],
            "🔴 발화했나(개선이 바뀐다)": bool(n_nan["개선(일)"] != n_plain["개선(일)"])},
        "W5 다중집합 검사에 검정력이 있나": {
            "심은 결함": "같은 두 세계를 drop_first=True 로 본다(티처 #75 C4 가 False 라고 잰 자리)",
            "심었나": True, "씨앗": ws,
            "[달력제거] 판(안 심음)": ms_ok,
            "[둘 다] 판(심음)": ms_drop,
            "🔴 발화했나(심으면 False 가 나온다)":
                bool(ms_ok["🔴 판 행의 정답 다중집합이 같은가"]
                     and not ms_drop["🔴 판 행의 정답 다중집합이 같은가"])},
        "W6 비교가능성 관문이 발화하나": {
            "심은 결함": "귀무의 기후값 MAE 를 ×1.10",
            "심었나": True, "씨앗": ws,
            "안 심은 판": {"상대차": cmp_good["🔴 상대차"], "통과": cmp_good["🔴 통과"]},
            "심은 판": {"상대차": cmp_bad["🔴 상대차"], "통과": cmp_bad["🔴 통과"]},
            "🔴 발화했나(심으면 불통과)": bool(cmp_good["🔴 통과"] and not cmp_bad["🔴 통과"])},
        "W9 입력이 925·928 과 같은 파일인가(음성 대조)": {
            "심었나": False, "🔴 통과": sha == NPZ_SHA},
    }
    _log("③ 배선 W1~W6·W9 완료", time.time() - t0)

    # ── ④ 파일럿 → 경험분포 검출력 ──────────────────────────────────────
    pilot_vals = []
    for s in PILOT:
        d2, m2, _mv, _hh = null_n2_plantable(first, r, seed=s)
        tbp = gaps_from_events(d2, m2, V, OBS, DAY0)
        rp = rows_x(tbp, tr_set, ho_set, cal_off=True, drop_first=False)
        pilot_vals.append(rp["개선(일)"])
    shape = np.asarray(list(json.loads(
        (ROOT / "runners/out928_draws.json").read_text(encoding="utf-8"))["draws"].values()), float)
    pw = empirical_power(np.asarray(pilot_vals, float), real_A["개선(일)"], shape, ndraw=NDRAW)
    pw["🔴 파일럿 씨앗(판정에 안 쓴다)"] = list(PILOT)
    pw["🔴 모양을 빌린 곳"] = "runners/out928_draws.json — [둘 다] 판의 200뽑기(표준화해서 모양만 쓴다)"
    pw["🔴 추정 해상도의 천장(사전등록 §3 이 미리 적었다)"] = float((1 - 1 / 201) ** NDRAW)
    pw["🔴 관문이 아니다"] = "검출력 관문을 두면 결과가 나쁠 때 빠져나가는 도피구가 된다(사전등록 §3)"
    out["④ 🔴 검출력 — 경험분포로 냈다(정규 근사 안 씀)"] = pw
    _log("④ 검출력", pw["🔴 검출력 = (1−q̂)^%d" % NDRAW], time.time() - t0)

    # ── ⑤ 판정 200뽑기 (판 둘 · 같은 귀무 세계) ─────────────────────────
    recs, failed = {}, {}
    ms_bad = []
    tdraw0 = time.time()
    real_cmp = cmp_pack(real_A, tab_real)
    for s in range(1, NDRAW + 1):
        try:
            d2, m2, mv, _hh = null_n2_plantable(first, r, seed=s)
            tb = gaps_from_events(d2, m2, V, OBS, DAY0)
            if not np.array_equal(tb["gi"], tab_real["gi"]):
                failed[s] = "행 격자 배열이 진짜와 다르다"
                continue
            ra = rows_x(tb, tr_set, ho_set, cal_off=True, drop_first=False)
            rb = rows_x(tb, tr_set, ho_set, cal_off=True, drop_first=False,
                        force_prv_cuts=REAL_PRV_CUTS)
            if not (np.isfinite(ra["개선(일)"]) and np.isfinite(rb["개선(일)"])):
                failed[s] = "개선이 NaN"
                continue
            ms = multiset_same(real_A, ra)
            cm = comparability(real_cmp, cmp_pack(ra, tb))
            rec = {
                "씨앗": s,
                PANEL_A: {"개선(일)": ra["개선(일)"],
                          "prevmed 3분위 경계": ra["prevmed 3분위 경계"],
                          "mag 3분위 경계": ra["mag 3분위 경계"],
                          "전체 중앙값": ra["전체 중앙값"],
                          "기준 팔 MAE": ra["그 판의 기준 팔 MAE"],
                          "시험 팔 MAE": ra["그 판의 시험 팔 MAE"],
                          "3수준 셀 가짓수": ra["🔴 3수준 셀 가짓수"]},
                PANEL_B: {"개선(일)": rb["개선(일)"],
                          "prevmed 3분위 경계": rb["prevmed 3분위 경계"],
                          "mag 3분위 경계": rb["mag 3분위 경계"],
                          "전체 중앙값": rb["전체 중앙값"],
                          "기준 팔 MAE": rb["그 판의 기준 팔 MAE"],
                          "시험 팔 MAE": rb["그 판의 시험 팔 MAE"],
                          "3수준 셀 가짓수": rb["🔴 3수준 셀 가짓수"]},
                "🔴 정답 다중집합 동일": ms["🔴 판 행의 정답 다중집합이 같은가"],
                "🔴 비교가능성 통과": cm["🔴 통과"],
                "비교가능성 상대차": cm["🔴 상대차"],
                "🔴 mag 경계가 진짜와 같은가": bool(tuple(ra["mag 3분위 경계"]) == REAL_MAG_CUTS),
                "🔴 전체 중앙값이 진짜와 같은가": bool(ra["전체 중앙값"] == real_A["전체 중앙값"]),
                "간격 순서가 바뀐 격자 비율": mv,
            }
            recs[s] = rec
            if not ms["🔴 판 행의 정답 다중집합이 같은가"]:
                ms_bad.append({"씨앗": s, "검사": ms})
        except Exception as e:                       # 🔴 조용히 빠뜨리지 않는다
            failed[s] = f"{type(e).__name__}: {e}"
        if s % 10 == 0:
            el = time.time() - tdraw0
            _log(f"  뽑기 {s}/{NDRAW} · {el:.1f}s · 뽑기당 {el/s:.2f}s · "
                 f"A={recs.get(s, {}).get(PANEL_A, {}).get('개선(일)')} "
                 f"B={recs.get(s, {}).get(PANEL_B, {}).get('개선(일)')}")
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
    sm = ROOT / "runners/out933_calpanel_smoke.json"
    if sm.exists() and recs:
        smk = json.loads(sm.read_text(encoding="utf-8"))
        cmp_rows = []
        for r0 in smk.get("⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다", {}).get("기록", []):
            s0 = r0["씨앗"]
            if s0 in recs:
                cmp_rows.append({
                    "씨앗": s0,
                    "연습 A": r0[PANEL_A]["개선(일)"], "본 주행 A": recs[s0][PANEL_A]["개선(일)"],
                    "연습 B": r0[PANEL_B]["개선(일)"], "본 주행 B": recs[s0][PANEL_B]["개선(일)"],
                    "🔴 비트로 같은가": bool(r0[PANEL_A]["개선(일)"] == recs[s0][PANEL_A]["개선(일)"]
                                     and r0[PANEL_B]["개선(일)"] == recs[s0][PANEL_B]["개선(일)"]),
                })
        out["⑤-나 🔴 연습 주행 대조 (자백한 그 주행)"] = {
            "대조한 씨앗 수": len(cmp_rows), "행": cmp_rows,
            "🔴 전부 비트로 같은가": bool(cmp_rows) and all(x["🔴 비트로 같은가"] for x in cmp_rows),
        }
    if ms_bad:
        out["🔴🔴 §5-나 발화 — 정답 다중집합이 깨진 뽑기가 있다"] = ms_bad
        out["🔴 판정"] = ("§7-3 — [달력제거] 판에서도 정답 다중집합이 깨졌다. "
                       "사전등록대로 여기서 멈추고 신고한다. 판정을 안 낸다")
        _finish(out, t0, tstart)
        return
    _log("⑤ 200뽑기 완료", time.time() - t0)

    # ── ⑥ 판별 · 경계 상태별 표 · 짝지은 BCa ───────────────────────────
    seeds = sorted(recs)
    verdict = {}
    for panel in (PANEL_A, PANEL_B):
        vals = [recs[s][panel]["개선(일)"] for s in seeds]
        pp = perm_p(real_A["개선(일)"], vals)
        sub = [s for s in seeds if recs[s]["🔴 비교가능성 통과"]]
        pp_sub = perm_p(real_A["개선(일)"], [recs[s][panel]["개선(일)"] for s in sub])
        st = _state_table([{**recs[s][panel]} for s in seeds])
        pp["🔴 경계 상태별 표"] = st
        pp["🔴 z·SD·왜도·첨도를 해석해도 되나"] = (
            "🔴 안 된다 — 상태가 %d개인 혼합의 요약이다" % st["상태 수"] if st["상태 수"] > 1
            else "된다 — 상태가 하나다(경계 강제가 이산 상태를 지웠다)")
        pp["🔴 비교가능성 통과분만의 p(병기 · 판정에 안 쓴다)"] = {
            "분모": len(sub), "p": pp_sub["🔴 순열 p = (1+k)/(1+B)"],
            "k": pp_sub["🔴 귀무 ≥ 진짜 인 뽑기 수 k"],
            "🔴 1차와 같은가": bool(pp_sub["🔴 순열 p = (1+k)/(1+B)"]
                            == pp["🔴 순열 p = (1+k)/(1+B)"])}
        pp["🔴 mag 경계가 200뽑기 내내 진짜와 같았나"] = {
            "같은 뽑기": int(sum(recs[s]["🔴 mag 경계가 진짜와 같은가"] for s in seeds)),
            "분모": len(seeds)}
        pp["🔴 전체 중앙값이 200뽑기 내내 진짜와 같았나"] = {
            "같은 뽑기": int(sum(recs[s]["🔴 전체 중앙값이 진짜와 같은가"] for s in seeds)),
            "분모": len(seeds)}
        verdict[panel] = pp
        _log("⑥", panel, "p=", pp["🔴 순열 p = (1+k)/(1+B)"],
             "k=", pp["🔴 귀무 ≥ 진짜 인 뽑기 수 k"], "상태 수=", st["상태 수"])

    # W7 · W8 (200뽑기 위에서만 심을 수 있다)
    va = np.asarray([recs[s][PANEL_A]["개선(일)"] for s in seeds], float)
    w7 = perm_p(va[0], list(va[1:]))
    wires["W7 p 가 정말 순위로 나오나"] = {
        "심은 결함": "귀무 뽑기 하나(씨앗 %d)를 진짜 자리에 놓는다" % seeds[0],
        "심었나": True, "심은 판 p": w7["🔴 순열 p = (1+k)/(1+B)"],
        "안 심은 판 p": verdict[PANEL_A]["🔴 순열 p = (1+k)/(1+B)"],
        "🔴 발화했나(심으면 p 가 커진다)":
            bool(w7["🔴 순열 p = (1+k)/(1+B)"] > verdict[PANEL_A]["🔴 순열 p = (1+k)/(1+B)"])}
    wires["W8 씨앗이 먹히나"] = {
        "심은 결함": "(대조) 모든 뽑기가 같은 씨앗이면 서로 다른 값의 개수가 1 이 된다",
        "심었나": True, "서로 다른 값의 개수": int(np.unique(va).size), "뽑기 수": len(seeds),
        "🔴 발화했나": bool(np.unique(va).size == len(seeds)),
        "🔴 928 이 여기서 걸렸다": "928 의 W4 는 181/200 이라 안 발화했다 — 원인은 씨앗이 아니라 자의 눈금"}
    n_planted = sum(1 for v in wires.values() if v.get("심었나"))
    n_fired = sum(1 for v in wires.values() if v.get("심었나")
                  and any(k.startswith("🔴 발화했나") and vv for k, vv in v.items()))
    n_neg = sum(1 for v in wires.values() if not v.get("심었나"))
    n_neg_ok = sum(1 for v in wires.values() if not v.get("심었나") and v.get("🔴 통과"))
    unplantable = [
        "🔴 interval918 · perm922 · gap925 의 관 자체가 옳은가 — 그대로 import 한다",
        "🔴 daily.npz 가 옳게 만들어졌는가 — 만드는 러너가 저장소에 없다(3사이클 연속)",
        "🔴 N2(간격순서 순열)가 이 물음의 옳은 귀무인가 — 이 러너 안에서 못 심는다",
        "🔴 경계 강제 판이 「순서의 몫」을 옳게 가르는가 — 강제가 귀무를 진짜 쪽으로 끌 수도 있고 부호를 못 정한다",
    ]
    out["③ 배선 검사 — 🔴 분모를 둘로 낸다"] = {
        "검사": wires, "🔴 심은 수": n_planted, "🔴 발화한 수": n_fired,
        "🔴 놓친 수": n_planted - n_fired,
        "음성 대조 수": n_neg, "음성 대조 통과": n_neg_ok,
        "🔴 못 심은 수": len(unplantable), "🔴 못 심은 것(검정력 0 으로 신고)": unplantable,
        "🔴 검정력(심은 것 기준)": f"{n_fired}/{n_planted} = {n_fired/n_planted:.3f}",
        "🔴🔴 검정력(못 심은 것까지 분모에)":
            f"{n_fired}/{n_planted+len(unplantable)} = {n_fired/(n_planted+len(unplantable)):.3f}",
    }
    out["⑥ 🔴 판정용 순열 — 판 둘"] = verdict

    # 짝지은 군집 BCa (규약 47) — 씨앗 922 와의 짝. 판정의 자가 아니라 크기의 보조
    n922d, n922m, _mv, _hh = null_n2_plantable(first, r, seed=922)
    tb922 = gaps_from_events(n922d, n922m, V, OBS, DAY0)
    a922 = rows_x(tb922, tr_set, ho_set, cal_off=True, drop_first=False)
    b922 = rows_x(tb922, tr_set, ho_set, cal_off=True, drop_first=False,
                  force_prv_cuts=REAL_PRV_CUTS)
    pr = {PANEL_A: paired(real_A, a922, B=B_BOOT, seed=SEED),
          PANEL_B: paired(real_forced, b922, B=B_BOOT, seed=SEED)}
    pr["🔴 티처 #74·#75 의 [달력제거] 짝지은 차(정본 아님)"] = [0.10479931464401587,
                                                0.0715880221020098, 0.1387529451833329]
    pr["🔴 씨앗 922 는 200뽑기에 안 들어 있다"] = True
    pr["🔴 이 구간은 판정의 자가 아니다"] = ("928 이 잰 것 — 참 귀무끼리 짝지어도 20쌍 중 7쌍이 「유의」로 "
                                "갈렸다. 판정의 근거는 순열 p 다(규약 47 은 구간을 cluster_boot BCa 로 내라는 규약이고 그것은 지켰다)")
    out["⑥-나 짝지은 군집 BCa (규약 47 · 보조)"] = pr

    # ── ⑦ 판정 ────────────────────────────────────────────────────────
    pA = verdict[PANEL_A]["🔴 순열 p = (1+k)/(1+B)"]
    pB = verdict[PANEL_B]["🔴 순열 p = (1+k)/(1+B)"]
    sA, sB = pA < 0.01, pB < 0.01
    if sA and sB:
        head = ("**①·② 둘 다 p < 0.01 — 「순서는 잡힌다」가 이번엔 진짜로 확정됐다.** "
                "정답 다중집합이 같은 판에서, 분위 경계를 고정하고도 이겼다")
    elif sA and not sB:
        head = ("🔴 **② 가 무너졌다 — 928 의 헤드라인은 분위 경계 하나의 이름이었다.** "
                "옳은 문장: 「순서는 표의 분위 경계를 반나절 움직인다 — 그것이 예측력인지는 이 자로 못 가른다」")
    else:
        head = ("🔴 **① 이 무너졌다 — 깨끗한 판에서는 못 이긴다.** 928 의 p=0.004975 는 "
                "[둘 다] 판의 정답 불일치(진짜 첫 간격 중앙값 20.0 대 귀무 11.0)에 기댄 수였다")
    eff_A = verdict[PANEL_A]["🔴 효과(진짜 − 귀무평균 · 일)"]
    out["🔴🔴 판정 (사전등록 §4 를 기계로 적용)"] = {
        "§4-① [달력제거]": {"p": pA, "k": verdict[PANEL_A]["🔴 귀무 ≥ 진짜 인 뽑기 수 k"],
                        "문턱": 0.01, "🔴 p < 0.01 인가": bool(sA)},
        "§4-② [달력제거·경계강제]": {"p": pB, "k": verdict[PANEL_B]["🔴 귀무 ≥ 진짜 인 뽑기 수 k"],
                             "문턱": 0.01, "🔴 p < 0.01 인가": bool(sB)},
        "🔴🔴 헤드라인(사전등록이 미리 써 둔 셋 중 하나)": head,
        "§4-크기 — 🔴 측정 전에 정해졌다(규율 4)": {
            "채택 크기 X(일)": SIZE_X, "오라클 천장 Y(일)": ORACLE_Y,
            "X/Y = Z": SIZE_X / ORACLE_Y,
            "🔴 Z > 1": bool(SIZE_X / ORACLE_Y > 1),
            "🔴 판정": "**이 자로는 원리상 못 넘는다** — 문턱이 아니라 조건 열을 바꿔야 한다",
            "진짜 팔이 천장의 몇 %인가": 100.0 * REAL_IMP_CAL / ORACLE_Y,
            "실측 효과(진짜 − 귀무평균 · 일 · 채택 판정에 안 쓴다)": eff_A,
            "실측 효과(분)": eff_A * 24 * 60,
            "🔴 여는 방향": "격자 정체 오라클 1.94386일(이 판) — 1.0 을 넘는 유일한 층",
        },
        "🔴 노트 133": "판 ① 만으로 채택하지 않는다. 판 ② 가 이 사이클의 확인 측정이다",
    }
    _finish(out, t0, tstart)


if __name__ == "__main__":
    main()
