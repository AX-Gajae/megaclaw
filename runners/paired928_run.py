# -*- coding: utf-8 -*-
"""팔 928-ㄴㄴ — **925 의 판정을 옳은 검정으로 다시 낸다** (사전등록 `docs/prereg_928_paired.md`).

🔴 순서가 규약이다:
    ① 입력·분모 대조(925 와 같은 파일인가)
    → ② 자기시험 S1~S9 (티처 #74 의 짝지은 수와 20뽑기를 **내 손으로 재현**) — 안 맞으면 §6-가 로 멈춘다
    → ③ 배선 검사 W1~W6 (심은 결함 · 못 심은 것도 분모에)
    → ④ 순열 **200뽑기** · 귀무 대 귀무 · 408개 격자의 정체
    → ⑤ 크기 관문(§5 의 1.0일) → ⑥ 판정(사전등록 §4 를 기계로 적용)

산출물: runners/out928_paired.json
사용:   python3 runners/paired928_run.py      (🔴 파이프 금지 — 리디렉션으로)
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
from state.perm922 import gaps_from_events, real_events  # noqa: E402
from state.gap925 import PANEL_DEF, PANELS, null_n2_plantable  # noqa: E402
from state.paired928 import (BASE, BASE_PRIME, TEST, improvement_rows,  # noqa: E402
                             paired, perm_p)
from runners.gap925_run import stat as gap925_stat  # noqa: E402  (남의 것 — 읽기만)
from runners.gap925_run import world_pack as gap925_world_pack  # noqa: E402

SCRATCH = Path(os.environ.get(
    "G928_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/"
    "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad"))
NPZ = Path(os.environ.get("G928_NPZ", str(SCRATCH / "g922/daily.npz")))
TAG = os.environ.get("G928_TAG", "")          # 🔴 연습 주행은 TAG 를 붙여 정본을 안 덮는다
OUT = ROOT / f"runners/out928_paired{TAG}.json"
CKPT = SCRATCH / f"g928/draws{TAG}.json"
B_BOOT = int(os.environ.get("G928_B", "2000"))
SEED = int(os.environ.get("G928_SEED", "918"))
NDRAW = int(os.environ.get("G928_NDRAW", "200"))
NPAIR_BOOT = int(os.environ.get("G928_NPAIRBOOT", "20"))

#: 🔴 925 산출물이 실은 수 — 내가 비트로 재현해야 하는 대조값
CANON = {
    "진짜 [둘 다]": 0.21648759151849387,
    "N2(seed 922) [둘 다]": 0.1985547209280213,
    "짝지은 점추정 [둘 다]": 0.017932870590472577,
    "홀드아웃 행([둘 다])": 52585,
    "홀드아웃 군집([둘 다])": 2102,
    "홀드아웃 행(원판)": 54862,
    "홀드아웃 군집(원판)": 2277,
    "홀드아웃 격자": 2685,
    "학습 격자": 6195,
    "daily.npz sha256": "4472b7f69cb5170c8a804dfbdb72a0289dcd34936aa5e05b6e9e191878ae97b2",
    "그 판의 기준 팔 MAE": 10.380735951316915,
}

#: 🔴 티처 #74(out926_teacher.json)가 낸 수 — **정본이 아니다.** 내가 재서 대조한다
TEACHER_PAIRED = {
    "원판": (0.4718019758667202, 0.37346876044086375, 0.5900440382089565),
    "첫간격제외": (0.24170390795854332, 0.17487569982344306, 0.31961508490279783),
    "달력제거": (0.10479931464401587, 0.0715880221020098, 0.1387529451833329),
    "둘 다": (0.017932870590472577, 0.008983914541289936, 0.027130155489504697),
}
TEACHER_20 = {"최소": 0.19193686412475042, "최대": 0.209413330797756,
              "평균": 0.20314633450603786, "SD": 0.006516326375650564}
TEACHER_PRIME = (0.01306456213749168, 0.006199666644490977, 0.019247940001204757)
TEACHER_NULLPAIR = {"922 대 1000": (-0.016735, -0.024976, -0.007748),
                    "922 대 923": (-0.010041, -0.018095, -0.001348)}
#: §5 에서 측정 전에 박은 채택 크기
SIZE_THRESHOLD_DAYS = 1.0


#: 🔴 사전등록 정정 1 — 「비트로 같다」 대신 상대차 문턱. 이유는 사전등록 §2 정정 1
REL_TOL = 1e-14


def _same(mine: float, theirs: float) -> dict:
    """🔴 재현 판정 — **비트 일치 여부도 같이 싣는다**(문턱만 옮겼지 감춘 게 아니다)."""
    d = float(mine) - float(theirs)
    rel = abs(d) / max(abs(float(theirs)), 1e-300)
    return {"내 수": float(mine), "그쪽 수": float(theirs), "차": d, "상대차": rel,
            "비트로 같은가": bool(float(mine) == float(theirs)),
            "🔴 재현(상대차 ≤ 1e-14)": bool(rel <= REL_TOL)}


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


def main() -> None:
    t0 = time.time()
    tstart = dt.datetime.now(dt.timezone.utc)
    CKPT.parent.mkdir(parents=True, exist_ok=True)
    stamp = json.loads((ROOT / "runners/out928_prereg_stamp.json").read_text(encoding="utf-8"))
    stamp2 = json.loads((ROOT / "runners/out928_prereg_stamp2.json").read_text(encoding="utf-8"))
    out: dict = {
        "팔": "928-ㄴㄴ (925 의 판정을 옳은 검정으로 · 채택 크기 칸)",
        "사전등록": "docs/prereg_928_paired.md",
        "티처": "runners/out926_teacher.json (#74 C1 · C3 · M3)",
        "🔴 판 ρ": "한 번도 안 돌렸다. 이 팔의 자는 짝지은 군집 BCa 와 순열 200뽑기 둘이다",
        "🔴 사전등록 시각 증거": {
            "stamp 파일 둘": ["runners/out928_prereg_stamp.json (첫 판)",
                         "runners/out928_prereg_stamp2.json (정정 1)"],
            "사전등록 sha256(첫 stamp)": stamp["sha256"],
            "사전등록 sha256(정정 1 stamp)": stamp2["사전등록 sha256(정정 뒤)"],
            "사전등록 sha256(지금 다시 계산)": sha256_text(ROOT / "docs/prereg_928_paired.md"),
            "🔴 지금 파일이 정정 1 판과 같은가":
                sha256_text(ROOT / "docs/prereg_928_paired.md") == stamp2["사전등록 sha256(정정 뒤)"],
            "사전등록 mtime(UTC · 첫 판)": stamp["mtime(UTC)"],
            "사전등록 mtime(UTC · 정정 뒤)": stamp2["mtime(UTC · 정정 뒤)"],
            "첫 stamp 를 쓴 시각(UTC)": stamp["이 stamp 를 쓴 시각(UTC)"],
            "정정 stamp 를 쓴 시각(UTC)": stamp2["이 stamp 를 쓴 시각(UTC)"],
            "측정 시작(UTC)": tstart.isoformat(timespec="microseconds"),
            "🔴 두 stamp 가 모두 측정보다 먼저인가":
                (stamp["이 stamp 를 쓴 시각(UTC)"] < tstart.isoformat(timespec="microseconds")
                 and stamp2["이 stamp 를 쓴 시각(UTC)"] < tstart.isoformat(timespec="microseconds")),
            "🔴 os.utime 을 썼나": False,
            "🔴 정정이 있었다": stamp2["정정 내용"],
            "🔴 이것도 못 넘는 것": stamp2["🔴 이것도 못 넘는 것"],
        },
        "🔴 러너 실행 이력 — 자백한다": {
            "이 산출물 전에 완주한 횟수": 1,
            "그것": "G928_TAG=_smoke · G928_NDRAW=4 · G928_NPAIRBOOT=1 → runners/out928_paired_smoke.json "
                  "(자기시험 S3·S4 가 1 ulp 로 어긋나 §6-가 로 멈춘 판)",
            "그 뒤에 고친 것": ["사전등록 §2 에 **정정 1** 을 더했다(재현 문턱을 상대차 1e-14 로)",
                        "러너의 S3·S4 판정을 그 문턱으로 바꿨다 · 비트 일치 여부는 그대로 싣는다",
                        "이 자백 필드와 stamp2 를 더했다"],
            "🔴 안 고친 것": "자 · 귀무의 정의 · 뽑기 수 · 판정 문턱(p<0.01 · 크기 1.0일) · 판정 분기 — 한 자리도 안 건드렸다",
        },
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/paired928.py", "runners/paired928_run.py",
                        "state/gap925.py", "runners/gap925_run.py",
                        "state/perm922.py", "state/interval918.py")},
        "코드 mtime(UTC)": {c: dt.datetime.fromtimestamp(
            (ROOT / c).stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds")
            for c in ("docs/prereg_928_paired.md", "state/paired928.py",
                      "runners/paired928_run.py")},
        "설정": {"τ": TAU_PRIMARY, "기저선 lag": list(BASE_LAGS), "셀 최소 학습행": CELL_MIN,
               "부트 B": B_BOOT, "부트 seed": SEED, "뽑기 수": NDRAW,
               "귀무 씨앗": "1 … %d (🔴 925 가 쓴 922 는 안 넣는다 — 넣으면 선택 편향)" % NDRAW,
               "분할": f"격자 sha256('{SPLIT_SALT}'+격자) 70/30"},
    }

    # ── ① 입력 ──────────────────────────────────────────────────────────
    sha = sha256_text(NPZ)
    out["① 입력"] = {
        "daily.npz(🔴 저장소 밖이다)": str(NPZ), "sha256": sha,
        "바이트": NPZ.stat().st_size,
        "🔴 925 가 쓴 파일과 같은가(W6 음성 대조)": sha == CANON["daily.npz sha256"],
        "🔴 못 심는 것": "이 파일을 만드는 러너가 저장소에 없다 — sha 대조는 자기 자신하고만 된다",
    }
    if sha != CANON["daily.npz sha256"]:
        out["🔴 판정"] = "§6-가 — 입력 파일이 925 와 다르다. 판정을 안 낸다"
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

    first = surges(r, ok, TAU_PRIMARY)
    rdates, rmags = real_events(first, r)
    tab_real = gaps_from_events(rdates, rmags, V, OBS, DAY0)
    _log("① 표 준비 완료", time.time() - t0)

    # ── ② 자기시험 ─────────────────────────────────────────────────────
    real_both = improvement_rows(tab_real, tr_set, ho_set, cal_off=True, drop_first=True)
    real_plain = improvement_rows(tab_real, tr_set, ho_set, cal_off=False, drop_first=False)

    n2d, n2m, n2moved, n2have = null_n2_plantable(first, r, seed=922)
    tab_n2 = gaps_from_events(n2d, n2m, V, OBS, DAY0)
    assert np.array_equal(tab_real["gi"], tab_n2["gi"]), "🔴 두 세계의 행 격자가 다르다"
    n2_both = improvement_rows(tab_n2, tr_set, ho_set, cal_off=True, drop_first=True)

    # S8 — 빠른 경로가 925 의 world_pack 경로와 비트로 같은가
    wp = gap925_world_pack(tab_real, tr_set, ho_set, world="진짜", cal_off=True, with_extra=False)
    s_wp = gap925_stat(wp, drop_first=True)
    s8 = {
        "빠른 경로 개선": real_both["개선(일)"], "925 경로 개선": s_wp["개선(일)"],
        "🔴 비트로 같은가": bool(real_both["개선(일)"] == s_wp["개선(일)"]),
        "행": [real_both["행(간격) 수"], s_wp["행(간격) 수"]],
        "군집": [real_both["군집(격자) 수"], s_wp["군집(격자) 수"]],
        "기준 팔 MAE 도 같은가": bool(real_both["그 판의 기준 팔 MAE"] == s_wp["그 판의 기준 팔 MAE"]),
    }

    pr_both = paired(real_both, n2_both, B=B_BOOT, seed=SEED)
    _log("② 짝지은 [둘 다]", pr_both["짝지은 차(일)"], pr_both["BCa"], time.time() - t0)

    # S4 — 네 판 전부
    four = {}
    for panel in PANELS:
        cal_off, drop_first = PANEL_DEF[panel]
        a = (real_both if (cal_off and drop_first) else
             real_plain if not (cal_off or drop_first) else
             improvement_rows(tab_real, tr_set, ho_set, cal_off=cal_off, drop_first=drop_first))
        b = (n2_both if (cal_off and drop_first) else
             improvement_rows(tab_n2, tr_set, ho_set, cal_off=cal_off, drop_first=drop_first))
        pp = paired(a, b, B=B_BOOT, seed=SEED)
        t_pt, t_lo, t_hi = TEACHER_PAIRED[panel]
        cmp3 = {"점추정": _same(pp["짝지은 차(일)"], t_pt),
                "lo": _same(pp["BCa"][0], t_lo), "hi": _same(pp["BCa"][1], t_hi)}
        pp.update({
            "진짜 개선(일)": a["개선(일)"], "귀무(seed 922) 개선(일)": b["개선(일)"],
            "🔴 티처 #74 의 수(정본 아님)": [t_pt, t_lo, t_hi],
            "🔴 대조": cmp3,
            "🔴 비트로 같은가": all(v["비트로 같은가"] for v in cmp3.values()),
            "🔴 재현했나(사전등록 정정 1 · 상대차 ≤ 1e-14)":
                all(v["🔴 재현(상대차 ≤ 1e-14)"] for v in cmp3.values()),
        })
        four[panel] = pp
        _log("  S4", panel, pp["짝지은 차(일)"], pp["BCa"],
             pp["🔴 재현했나(사전등록 정정 1 · 상대차 ≤ 1e-14)"])

    # S6 — 자′ (기후값 팔에 격자 정보를 넣은 바닥)
    a_pr = improvement_rows(tab_real, tr_set, ho_set, cal_off=True, drop_first=True, base=BASE_PRIME)
    b_pr = improvement_rows(tab_n2, tr_set, ho_set, cal_off=True, drop_first=True, base=BASE_PRIME)
    pr_prime = paired(a_pr, b_pr, B=B_BOOT, seed=SEED)
    pr_prime["🔴 티처 #74 의 수(정본 아님)"] = list(TEACHER_PRIME)
    pr_prime["🔴 대조"] = {"점추정": _same(pr_prime["짝지은 차(일)"], TEACHER_PRIME[0]),
                       "lo": _same(pr_prime["BCa"][0], TEACHER_PRIME[1]),
                       "hi": _same(pr_prime["BCa"][1], TEACHER_PRIME[2])}
    pr_prime["🔴 재현했나"] = all(v["🔴 재현(상대차 ≤ 1e-14)"] for v in pr_prime["🔴 대조"].values())

    s3 = _same(pr_both["짝지은 차(일)"], CANON["짝지은 점추정 [둘 다]"])
    s3["🔴 왜 비트로 안 같나(사전등록 §2 정정 1)"] = (
        "925 의 수는 「두 평균의 차」이고 짝지은 부트의 점추정은 「차의 평균」이다. "
        "수학적으로 같고 부동소수 결합순서만 다르다")
    s_ok = {
        "S1 진짜 [둘 다]": real_both["개선(일)"] == CANON["진짜 [둘 다]"],
        "S2 N2(922) [둘 다]": n2_both["개선(일)"] == CANON["N2(seed 922) [둘 다]"],
        "S3 짝지은 점추정": s3["🔴 재현(상대차 ≤ 1e-14)"],
        "S4 짝지은 BCa 네 판(티처)":
            all(four[p]["🔴 재현했나(사전등록 정정 1 · 상대차 ≤ 1e-14)"] for p in PANELS),
        "S8 빠른 경로 == 925 경로": s8["🔴 비트로 같은가"],
        "S9 분모": (real_both["행(간격) 수"] == CANON["홀드아웃 행([둘 다])"]
                and real_both["군집(격자) 수"] == CANON["홀드아웃 군집([둘 다])"]
                and real_plain["행(간격) 수"] == CANON["홀드아웃 행(원판)"]
                and real_plain["군집(격자) 수"] == CANON["홀드아웃 군집(원판)"]
                and len(ho_g) == CANON["홀드아웃 격자"]
                and len(tr_g) == CANON["학습 격자"]),
    }
    out["② 자기시험 — 🔴 티처의 수를 내 손으로 재현했는가"] = {
        "S1~S3·S9 대조값(925 산출물)": CANON,
        "S1 진짜 [둘 다]": real_both["개선(일)"],
        "S2 N2(seed 922) [둘 다]": n2_both["개선(일)"],
        "S3 짝지은 점추정 [둘 다]": pr_both["짝지은 차(일)"],
        "S3 대조": s3,
        "S4 짝지은 BCa 네 판": four,
        "S6 자′ 짝지은 [둘 다]": pr_prime,
        "S8 빠른 경로 대조": s8,
        "S9 분모 딱지 — 🔴 전부 다른 분모다": {
            "격자(전체)": G, "날짜": D, "칸": G * D, "관측 칸": int(OBS.sum()),
            "자격 격자(관측률 ≥0.95)": int(qualify.sum()),
            "학습 격자": len(tr_g), "🔴 홀드아웃 격자": len(ho_g),
            "🔴 홀드아웃 격자 중 간격이 하나라도 있는 것(원판 군집)": real_plain["군집(격자) 수"],
            "🔴 첫간격제외 뒤 군집([둘 다])": real_both["군집(격자) 수"],
            "홀드아웃 간격(원판 행)": real_plain["행(간격) 수"],
            "홀드아웃 간격([둘 다] 행)": real_both["행(간격) 수"],
            "🔴 925 가 어긴 자리": "925 는 2,277 을 「홀드아웃 격자 수」라 불렀다. 홀드아웃 격자는 2,685 이고 "
                           "2,277 은 그중 간격이 하나라도 있는 격자다(티처 #74 C4)",
        },
        "항목별": s_ok, "🔴 전부 같다": all(s_ok.values()),
    }
    if not all(s_ok.values()):
        out["🔴 판정"] = "§6-가 — 자기시험이 안 맞는다. 관이 다르다. 판정을 안 낸다"
        _finish(out, t0, tstart)
        return
    _log("② 자기시험 통과", time.time() - t0)

    # ── ③ 배선 검사 ────────────────────────────────────────────────────
    idd, idm, idmoved, _ = null_n2_plantable(first, r, seed=922, plant_identity=True)
    tab_id = gaps_from_events(idd, idm, V, OBS, DAY0)
    id_both = improvement_rows(tab_id, tr_set, ho_set, cal_off=True, drop_first=True)
    w1 = paired(real_both, id_both, B=B_BOOT, seed=SEED)
    w2 = paired(real_both, n2_both, B=B_BOOT, seed=SEED, plant_roll=True)
    w5 = improvement_rows(tab_real, tr_set, ho_set, cal_off=True, drop_first=True,
                          plant_no_drop=True)
    wires = {
        "W1 짝지음이 진짜 짝인가": {
            "심은 결함": "항등 순열(간격 순서를 하나도 안 섞는다)",
            "심었나": True, "짝지은 차": w1["짝지은 차(일)"], "BCa": w1["BCa"],
            "🔴 발화했나(차가 정확히 0.0 이고 구간도 [0,0])":
                bool(w1["짝지은 차(일)"] == 0.0 and w1["BCa"] == [0.0, 0.0]),
            "안 심은 판의 섞인 비율": n2moved, "심은 판의 섞인 비율": idmoved,
        },
        "W2 짝의 정렬이 살아 있나": {
            "심은 결함": "귀무 쪽 행 벡터를 한 칸 굴린다(짝을 깬다)",
            "심었나": True,
            "심은 판 점추정": w2["짝지은 차(일)"], "안 심은 판 점추정": pr_both["짝지은 차(일)"],
            "🔴 점추정이 안 변한다(평균은 순열 불변) — 예상대로인가":
                bool(abs(w2["짝지은 차(일)"] - pr_both["짝지은 차(일)"]) < 1e-12),
            "심은 판 BCa": w2["BCa"], "안 심은 판 BCa": pr_both["BCa"],
            "🔴 발화했나(구간이 변한다)": bool(w2["BCa"] != pr_both["BCa"]),
            "🔴 이 검사가 가르쳐 준 것": "짝이 깨져도 **점추정은 못 잡는다**. 짝지음의 값은 전부 구간에 있다",
        },
        "W5 첫간격제외가 정말 행을 빼나": {
            "심은 결함": "drop_first 마스크가 아무 행도 안 뺀다",
            "심었나": True,
            "안 심은 판 행": real_both["행(간격) 수"], "심은 판 행": w5["행(간격) 수"],
            "🔴 발화했나": bool(w5["행(간격) 수"] == CANON["홀드아웃 행(원판)"]
                          and real_both["행(간격) 수"] == CANON["홀드아웃 행([둘 다])"]),
            "🔴 뺀 행": w5["행(간격) 수"] - real_both["행(간격) 수"],
        },
        "W6 입력이 925 와 같은 파일인가(음성 대조 · 심은 결함 아님)": {
            "심었나": False, "통과": out["① 입력"]["🔴 925 가 쓴 파일과 같은가(W6 음성 대조)"],
        },
    }
    _log("③ 배선 W1·W2·W5 완료", time.time() - t0)

    # ── ④ 순열 200뽑기 ─────────────────────────────────────────────────
    real = real_both["개선(일)"]
    draws, imps, failed = {}, {}, {}
    tdraw0 = time.time()
    for s in range(1, NDRAW + 1):
        try:
            dd, mm, mv, _h = null_n2_plantable(first, r, seed=s)
            tb = gaps_from_events(dd, mm, V, OBS, DAY0)
            if not np.array_equal(tb["gi"], tab_real["gi"]):
                failed[s] = "행 격자 배열이 진짜와 다르다"
                continue
            ir = improvement_rows(tb, tr_set, ho_set, cal_off=True, drop_first=True)
            if not np.isfinite(ir["개선(일)"]):
                failed[s] = "개선이 NaN"
                continue
            draws[s] = ir["개선(일)"]
            imps[s] = ir["imp"]
        except Exception as e:                      # 🔴 조용히 빠뜨리지 않는다
            failed[s] = f"{type(e).__name__}: {e}"
        if s % 10 == 0:
            el = time.time() - tdraw0
            _log(f"  뽑기 {s}/{NDRAW} · {el:.1f}s · 뽑기당 {el/s:.2f}s · 최근값 {draws.get(s)}")
            CKPT.write_text(json.dumps({"draws": draws, "failed": failed},
                                       ensure_ascii=False), encoding="utf-8")
    CKPT.write_text(json.dumps({"draws": draws, "failed": failed}, ensure_ascii=False),
                    encoding="utf-8")
    seeds = sorted(draws)
    pp = perm_p(real, [draws[s] for s in seeds])
    pp["🔴 씨앗 922(925 가 쓴 참조 뽑기 · 200뽑기에 안 넣었다)"] = n2_both["개선(일)"]
    pp["🔴 922 뽑기의 백분위(200뽑기 안에서)"] = float(
        (np.asarray([draws[s] for s in seeds]) < n2_both["개선(일)"]).mean())
    pp["뽑기당 초"] = (time.time() - tdraw0) / max(len(seeds), 1)
    pp["🔴 실패한 뽑기"] = failed
    _log("④ 순열", pp["🔴 순열 p = (1+k)/(1+B)"], "k=", pp["🔴 귀무 ≥ 진짜 인 뽑기 수 k"],
         "z=", pp["🔴 z = (진짜 − 귀무평균) ÷ 귀무SD(ddof=1)"], time.time() - t0)

    # S5 — 티처의 20뽑기 재현
    first20 = [draws[s] for s in range(1, 21) if s in draws]
    a20 = np.asarray(first20, float)
    out_s5 = {
        "씨앗 1~20 의 값": first20,
        "최소": float(a20.min()), "최대": float(a20.max()), "평균": float(a20.mean()),
        "SD(ddof=0)": float(a20.std(ddof=0)), "SD(ddof=1)": float(a20.std(ddof=1)),
        "🔴 티처 #74 의 20뽑기(정본 아님)": TEACHER_20,
        "🔴 최소·최대·평균이 비트로 같은가": bool(
            float(a20.min()) == TEACHER_20["최소"] and float(a20.max()) == TEACHER_20["최대"]
            and float(a20.mean()) == TEACHER_20["평균"]),
        "🔴 티처의 SD 는 ddof 몇인가": ("0" if abs(float(a20.std(ddof=0)) - TEACHER_20["SD"]) < 1e-15
                                else "1" if abs(float(a20.std(ddof=1)) - TEACHER_20["SD"]) < 1e-15
                                else "🔴 둘 다 아니다"),
        "🔴 20뽑기만 썼다면 p": (1.0 + int((a20 >= real).sum())) / 21.0,
    }
    out["②-나 S5 — 티처의 20뽑기 재현"] = out_s5

    # W3 · W4 (200뽑기 위에서만 심을 수 있다)
    pseudo = draws[seeds[0]]
    rest = [draws[s] for s in seeds[1:]]
    w3 = perm_p(pseudo, rest)
    wires["W3 p 가 정말 순위로 나오나"] = {
        "심은 결함": "귀무 뽑기 하나(씨앗 %d)를 진짜 자리에 놓는다" % seeds[0],
        "심었나": True, "심은 판 p": w3["🔴 순열 p = (1+k)/(1+B)"],
        "안 심은 판 p": pp["🔴 순열 p = (1+k)/(1+B)"],
        "🔴 발화했나(심으면 p 가 커진다)":
            bool(w3["🔴 순열 p = (1+k)/(1+B)"] > pp["🔴 순열 p = (1+k)/(1+B)"]),
    }
    vals = np.asarray([draws[s] for s in seeds], float)
    wires["W4 뽑기가 서로 다른가(씨앗이 먹히나)"] = {
        "심은 결함": "(대조) 모든 뽑기가 같은 씨앗이었다면 서로 다른 값의 개수가 1 이 된다",
        "심었나": True,
        "서로 다른 값의 개수": int(np.unique(vals).size), "뽑기 수": len(seeds),
        "🔴 발화했나": bool(np.unique(vals).size == len(seeds)),
    }
    n_planted = sum(1 for k, v in wires.items() if v.get("심었나"))
    n_fired = sum(1 for k, v in wires.items()
                  if v.get("심었나") and any(kk.startswith("🔴 발화했나") and vv
                                          for kk, vv in v.items()))
    unplantable = [
        "🔴 state/interval918.py · state/perm922.py 의 관 자체가 옳은가 — 그대로 import 한다. 틀렸으면 원리상 못 잡는다",
        "🔴 daily.npz 가 옳게 만들어졌는가 — 만드는 러너가 저장소에 없다. sha 대조는 자기 자신하고만 된다",
        "🔴 N2(간격순서 순열)가 이 물음의 옳은 귀무인가 — 이 러너 안에서 못 심는다",
    ]
    out["③ 배선 검사 — 🔴 분모를 둘로 낸다"] = {
        "검사": wires, "🔴 심은 수": n_planted, "🔴 발화한 수": n_fired,
        "🔴 놓친 수": n_planted - n_fired,
        "🔴 못 심은 수": len(unplantable), "🔴 못 심은 것(검정력 0 으로 신고 · 분모에 넣는다)": unplantable,
        "🔴 검정력(심은 것 기준)": f"{n_fired}/{n_planted} = {n_fired/n_planted:.3f}",
        "🔴🔴 검정력(못 심은 것까지 분모에)":
            f"{n_fired}/{n_planted+len(unplantable)} = {n_fired/(n_planted+len(unplantable)):.3f}",
    }
    out["④ 순열 200뽑기 — 🔴 진짜의 순위로 p 를 낸다"] = pp

    # ── ④-나 귀무 대 귀무 ───────────────────────────────────────────────
    pairs = [(seeds[i], seeds[i + 1]) for i in range(0, len(seeds) - 1, 2)]
    pt = np.asarray([draws[a] - draws[b] for a, b in pairs], float)
    eff = pr_both["짝지은 차(일)"]
    nn_boot = []
    for a, b in pairs[:NPAIR_BOOT]:
        pa = {"imp": imps[a], "gi": real_both["gi"], "개선(일)": draws[a]}
        pb = {"imp": imps[b], "gi": real_both["gi"], "개선(일)": draws[b]}
        rr = paired(pa, pb, B=B_BOOT, seed=SEED)
        nn_boot.append({"쌍": [a, b], "차": rr["짝지은 차(일)"], "BCa": rr["BCa"],
                        "판정": rr["판정"]})
    # 티처가 낸 두 쌍
    teacher_pairs = {}
    for nm, (sa, sb) in (("922 대 1000", (922, 1000)), ("922 대 923", (922, 923))):
        pk = {}
        for s in (sa, sb):
            dd, mm, _mv, _h = null_n2_plantable(first, r, seed=s)
            tb = gaps_from_events(dd, mm, V, OBS, DAY0)
            pk[s] = improvement_rows(tb, tr_set, ho_set, cal_off=True, drop_first=True)
        rr = paired(pk[sa], pk[sb], B=B_BOOT, seed=SEED)
        t_pt, t_lo, t_hi = TEACHER_NULLPAIR[nm]
        rr["🔴 티처 #74 의 수(정본 아님)"] = [t_pt, t_lo, t_hi]
        rr["🔴 소수 여섯째 자리까지 같은가"] = bool(round(rr["짝지은 차(일)"], 6) == t_pt)
        teacher_pairs[nm] = rr
    nsig = sum(1 for x in nn_boot if x["판정"] != "판정 불능")
    out["④-나 🔴 귀무 대 귀무 — 참 귀무 안의 변동이 효과와 같은 크기인가"] = {
        "🔴 무엇을 하나": "200뽑기를 겹치지 않는 쌍으로 묶어 **귀무끼리** 짝지어 잰다. "
                   "이 분포가 효과와 겹치면 효과는 뽑기 잡음과 구별이 안 된다",
        "쌍 수(분모)": len(pairs),
        "점추정 차 평균": float(pt.mean()), "SD(ddof=1)": float(pt.std(ddof=1)),
        "|차| 분위(50·90·95·99%)": [float(np.percentile(np.abs(pt), q))
                               for q in (50, 90, 95, 99)],
        "🔴 |귀무 대 귀무 차| ≥ 효과(%.6f) 인 쌍" % eff: int((np.abs(pt) >= abs(eff)).sum()),
        "🔴 그 비율": float((np.abs(pt) >= abs(eff)).mean()),
        "🔴 앞 %d 쌍의 짝지은 BCa" % NPAIR_BOOT: nn_boot,
        "🔴 그중 「유의」로 갈린 쌍(= 참 귀무에서의 거짓 양성)": nsig,
        "🔴 거짓 양성률": nsig / max(len(nn_boot), 1),
        "티처가 낸 두 쌍 재현": teacher_pairs,
    }
    _log("④-나 귀무 대 귀무 완료", time.time() - t0)

    # ── ④-다 408개 격자의 정체 ────────────────────────────────────────
    ev = first.sum(axis=1)
    ho_idx = np.flatnonzero(ho_set)
    ho_ev = ev[ho_idx]
    ho_q = qualify[ho_idx]
    cat = {
        "홀드아웃 격자(분모)": int(ho_idx.size),
        "🔴 간격이 하나라도 있는 격자(사건 ≥2)": int((ho_ev >= 2).sum()),
        "🔴 간격이 0 인 격자": int((ho_ev < 2).sum()),
        "  ├ ① 관측률 < 0.95 라 자격 미달(급증을 아예 못 잰다)": int((~ho_q).sum()),
        "  ├ ② 자격은 되는데 급증 사건 0개": int((ho_q & (ho_ev == 0)).sum()),
        "  └ ③ 급증 사건이 정확히 1개(간격은 2개 사건이 있어야 생긴다)":
            int((ho_q & (ho_ev == 1)).sum()),
        "🔴 셋의 합 == 간격 0 인 격자": int((~ho_q).sum() + (ho_q & (ho_ev == 0)).sum()
                                    + (ho_q & (ho_ev == 1)).sum()) == int((ho_ev < 2).sum()),
        "간격 0 인 격자의 비율": float((ho_ev < 2).mean()),
        "자격 미달 격자의 관측률 중앙값": float(np.median(obs_frac[ho_idx][~ho_q])) if (~ho_q).any() else None,
        "자격 미달 격자의 관측률 최대": float(obs_frac[ho_idx][~ho_q].max()) if (~ho_q).any() else None,
    }
    gi_ho = real_plain["gi"]
    uq, cnt = np.unique(gi_ho, return_counts=True)
    cat2 = {
        "🔴 원판 군집(간격 ≥1 인 홀드아웃 격자)": int(uq.size),
        "🔴 홀드아웃 간격이 정확히 1개인 격자(= 첫간격제외가 통째로 떨어뜨리는 격자)": int((cnt == 1).sum()),
        "🔴 [둘 다] 군집": real_both["군집(격자) 수"],
        "🔴 2,277 − 2,102 과 같은가": bool(int((cnt == 1).sum()) == uq.size - real_both["군집(격자) 수"]),
        "홀드아웃 간격 수 중앙값(격자당)": float(np.median(cnt)),
    }
    out["④-다 🔴 408개 격자의 정체 (조항 60 — 925 가 어긴 자리)"] = {
        "🔴 925 가 무엇을 어겼나": "같은 산출물이 「홀드아웃 격자 2,685」와 「홀드아웃 격자 수 2,277」을 "
                          "나란히 실었다. 뒤엣것은 **간격이 하나라도 있는 격자**다",
        "갈라 센 것": cat, "첫간격제외가 떨어뜨리는 격자": cat2,
    }

    # ── ⑤ 크기 관문 ────────────────────────────────────────────────────
    eff_days = pp["🔴 효과(진짜 − 귀무평균 · 일)"]
    base_mae = real_both["그 판의 기준 팔 MAE"]
    test_mae = real_both["그 판의 시험 팔 MAE"]
    imp_rows = real_both["imp"]
    size = {
        "🔴 문턱(사전등록 §5 · 측정 전에 박았다)": SIZE_THRESHOLD_DAYS,
        "문턱의 근거": "제품 출력이 「언제」이고 간격은 정수 일이다. 하루보다 작은 개선은 "
                 "사용자가 보는 화면에서 사라진다 — 통계가 아니라 **출력의 단위**다",
        "실측 효과(일 · 진짜 − 귀무평균)": eff_days,
        "실측 효과(분)": eff_days * 24 * 60,
        "🔴 문턱을 넘었나": bool(eff_days >= SIZE_THRESHOLD_DAYS),
        "🔴 문턱 ÷ 효과(몇 배 모자라나)": SIZE_THRESHOLD_DAYS / eff_days if eff_days else None,
        "짝지은 점추정으로 재도": pr_both["짝지은 차(일)"],
        "🔴 근거를 실측으로 확인": {
            "기준 팔 MAE(일)": base_mae, "시험 팔 MAE(일)": test_mae,
            "차": base_mae - test_mae,
            "하루 단위로 반올림한 기준 팔 MAE": round(base_mae),
            "하루 단위로 반올림한 시험 팔 MAE": round(test_mae),
            "🔴 반올림하면 같은 수인가(= 표시되는 답이 안 바뀐다)":
                bool(round(base_mae) == round(test_mae)),
        },
        "🔴 행 단위로도 세어 본다": {
            "행(분모)": int(imp_rows.size),
            "시험 팔이 더 가까운 행": int((imp_rows > 0).sum()),
            "기준 팔이 더 가까운 행": int((imp_rows < 0).sum()),
            "정확히 같은 행": int((imp_rows == 0).sum()),
            "🔴 1일 이상 좋아진 행": int((imp_rows >= 1).sum()),
            "🔴 1일 이상 나빠진 행": int((imp_rows <= -1).sum()),
            "🔴 순(좋아진 − 나빠진) 행": int((imp_rows >= 1).sum() - (imp_rows <= -1).sum()),
        },
        "병기(안 쓴 후보 문턱)": {
            "기준 MAE 의 5%": 0.05 * base_mae,
            "뽑기 SD 의 2배(= 검출 바닥이지 채택 크기가 아니다)":
                2 * pp["귀무 SD(ddof=1)"],
        },
    }
    out["⑤ 🔴 크기 관문 — 유의성과 둘이다"] = size

    # ── ⑥ 판정 ────────────────────────────────────────────────────────
    p = pp["🔴 순열 p = (1+k)/(1+B)"]
    sig = p < 0.01
    out["🔴🔴 판정 (사전등록 §4 를 기계로 적용)"] = {
        "§4-가 유의성 — 지시받은 규칙 그대로": {
            "순열 p": p, "문턱": 0.01,
            "🔴 p < 0.01 인가": bool(sig),
            "🔴 판정": ("**p < 0.01 — ③ 의 첫째 자에서 순서는 잡힌다가 확정됐다**" if sig
                    else "**p ≥ 0.01 — 「뽑기 잡음과 못 가른다」로 확정한다. 이 물음을 닫는다**"),
            "🔴 이 닫힘이 뽑기로 열리나": "안 열린다 — 사전등록 ⓪-마 가 측정 전에 계산했다: "
                              "순열 p 는 참 꼬리확률로 수렴하므로 뽑기를 늘리면 p<0.01 도달 확률이 "
                              "오히려 내려간다(200뽑기 0.0849 → 1000뽑기 0.0039). "
                              "다시 열려면 뽑기가 아니라 **자료나 자**가 바뀌어야 한다",
            "병기 p < 0.05 인가": bool(p < 0.05),
        },
        "§4-나 크기": {
            "문턱(일)": SIZE_THRESHOLD_DAYS, "실측(일)": eff_days,
            "🔴 넘었나": bool(eff_days >= SIZE_THRESHOLD_DAYS),
            "🔴 판정": ("크기로도 이겼다" if eff_days >= SIZE_THRESHOLD_DAYS
                    else "**크기로는 패 — p 가 얼마든 ③ 칸은 안 움직인다**"),
        },
        "🔴 두 문장을 따로 낸다": True,
    }
    _finish(out, t0, tstart)


if __name__ == "__main__":
    main()
