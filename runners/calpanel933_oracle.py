# -*- coding: utf-8 -*-
"""팔 933 **사전등록 부속** — 🔴 자의 성질 둘만 잰다: **오라클 천장**과 **항등 검사**.

🔴 왜 사전등록 **전**에 도는가
  · `docs/목표.md` 규율 4 가 「채택 크기 X · 오라클 천장 Y · X/Y = Z」를 **사전등록에 박으라**고
    한다. 그러려면 Y 를 먼저 알아야 한다.
  · 🔴 **이 러너는 귀무를 한 번도 안 만든다.** 순열 뽑기·p·판정은 여기서 안 나온다.
    Y 는 「이 자가 원리상 낼 수 있는 최대 개선」이고 **진짜 세계만으로** 정해진다.
  · X=1.0일 은 이 사이클이 고른 수가 아니라 `docs/목표.md` ③ 행에 **이미 박혀 있던** 수다.
    그러므로 Y 를 먼저 안다고 해서 문턱을 고를 자유도가 생기지 않는다.

산출물: runners/out933_oracle.json
사용:   python3 runners/calpanel933_oracle.py   (🔴 파이프 금지)
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
from state.gap925 import PANEL_DEF  # noqa: E402
from state.paired928 import improvement_rows  # noqa: E402
from state.calpanel933 import fit_identity, oracle_ceiling, rows_x  # noqa: E402

SCRATCH = Path(os.environ.get(
    "G933_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/"
    "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad"))
NPZ = Path(os.environ.get("G933_NPZ", str(SCRATCH / "g922/daily.npz")))
OUT = ROOT / "runners/out933_oracle.json"
NPZ_SHA = "4472b7f69cb5170c8a804dfbdb72a0289dcd34936aa5e05b6e9e191878ae97b2"
SIZE_THRESHOLD_DAYS = 1.0        # docs/목표.md ③ — 이 사이클이 고르지 않았다


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


def main() -> None:
    t0 = time.time()
    tstart = dt.datetime.now(dt.timezone.utc)
    sha = sha256_text(NPZ)
    out = {
        "팔": "933 사전등록 부속 — 오라클 천장(규율 4)과 항등 검사",
        "🔴 이 러너가 안 하는 것": "귀무 생성 · 순열 뽑기 · p · 판정. 하나도 안 한다",
        "① 입력": {"daily.npz(🔴 저장소 밖)": str(NPZ), "sha256": sha,
                 "🔴 925·928 이 쓴 파일과 같은가": sha == NPZ_SHA},
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/calpanel933.py", "runners/calpanel933_oracle.py",
                        "state/paired928.py", "state/gap925.py",
                        "state/perm922.py", "state/interval918.py")},
        "설정": {"τ": TAU_PRIMARY, "기저선 lag": list(BASE_LAGS), "셀 최소 학습행": CELL_MIN,
               "분할": f"격자 sha256('{SPLIT_SALT}'+격자) 70/30"},
    }
    if sha != NPZ_SHA:
        out["🔴 판정"] = "입력이 다르다 — 멈춘다"
        OUT.write_text(json.dumps(_scrub(out), ensure_ascii=False, indent=1), encoding="utf-8")
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
    gidx = {g: i for i, g in enumerate(grids)}
    tr_set = np.zeros(G, bool)
    ho_set = np.zeros(G, bool)
    for g in tr_g:
        tr_set[gidx[g]] = True
    for g in ho_g:
        ho_set[gidx[g]] = True
    first = surges(r, ok, TAU_PRIMARY)
    rdates, rmags = real_events(first, r)
    tab = gaps_from_events(rdates, rmags, V, OBS, DAY0)
    trm = tr_set[tab["gi"]]

    # ── ② 항등 검사 — 복사본이 원본과 같은 표·같은 개선을 내는가 ──────────
    ident = {}
    for cal_off in (False, True):
        ident["fit_tables 항등(cal_off=%s)" % cal_off] = fit_identity(
            tab, trm, plant_const_cal=cal_off)
    same_rows = {}
    for panel, (cal_off, drop_first) in PANEL_DEF.items():
        a = improvement_rows(tab, tr_set, ho_set, cal_off=cal_off, drop_first=drop_first)
        b = rows_x(tab, tr_set, ho_set, cal_off=cal_off, drop_first=drop_first)
        same_rows[panel] = {
            "paired928.improvement_rows 개선": a["개선(일)"],
            "calpanel933.rows_x 개선": b["개선(일)"],
            "🔴 비트로 같은가": bool(a["개선(일)"] == b["개선(일)"]),
            "행·군집": [[a["행(간격) 수"], b["행(간격) 수"]],
                     [a["군집(격자) 수"], b["군집(격자) 수"]]],
            "기준 MAE 도 같은가": bool(a["그 판의 기준 팔 MAE"] == b["그 판의 기준 팔 MAE"]),
            "prevmed 3분위 경계": b["prevmed 3분위 경계"],
            "mag 3분위 경계": b["mag 3분위 경계"],
            "전체 중앙값": b["전체 중앙값"],
        }
    out["② 항등 검사 — 🔴 안 맞으면 이 사이클은 여기서 멈춘다"] = {
        "표": ident, "네 판의 개선": same_rows,
        "🔴 전부 같다": bool(all(v["🔴 같은가"] for v in ident.values())
                        and all(v["🔴 비트로 같은가"] for v in same_rows.values())),
    }

    # ── ③ 오라클 천장 — 판마다 ─────────────────────────────────────────
    orc = {}
    for panel, (cal_off, drop_first) in PANEL_DEF.items():
        rows = rows_x(tab, tr_set, ho_set, cal_off=cal_off, drop_first=drop_first)
        o = oracle_ceiling(rows, label=panel)
        Y = o["🔴 이 자의 오라클 천장 Y(= ①)"]
        o["🔴🔴 규율 4"] = {
            "채택 크기 X(일 · docs/목표.md ③ — 이 사이클이 고르지 않았다)": SIZE_THRESHOLD_DAYS,
            "오라클 천장 Y(일)": Y,
            "🔴 X/Y = Z": SIZE_THRESHOLD_DAYS / Y if Y else None,
            "🔴 Z > 1 인가(= 이 자로는 원리상 못 넘는다)":
                bool(Y <= 0 or SIZE_THRESHOLD_DAYS / Y > 1.0),
        }
        orc[panel] = o
    out["③ 🔴 오라클 천장 (규율 4)"] = orc
    out["③-나 🔴 티처 #75 C3 의 [둘 다] 값과 대조"] = {
        "티처가 낸 Y([둘 다] · 9칸 오라클)": 0.2180,
        "내가 낸 Y([둘 다])": orc["둘 다"]["🔴 이 자의 오라클 천장 Y(= ①)"],
        "티처의 기준 팔 MAE": 10.380736,
        "내 기준 팔 MAE([둘 다])": orc["둘 다"]["기준 팔 MAE(실제로 쓰는 팔)"],
        "티처의 ② prevmed 실수값 오라클 개선": 0.7698,
        "내 ②([둘 다])": orc["둘 다"]["② prevmed 실수값 칸 오라클"]["개선(일)"],
        "티처의 ③ 격자 오라클 개선": 1.3901,
        "내 ③([둘 다])": orc["둘 다"]["③ 격자 정체 칸 오라클"]["개선(일)"],
    }
    out["시작 UTC"] = tstart.isoformat(timespec="seconds")
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(_scrub(out), ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT, out["초"], "초")


if __name__ == "__main__":
    main()
