# -*- coding: utf-8 -*-
"""팔 935 **사전등록 부속** — 🔴 자의 성질만 잰다: **LOO 오라클 천장**(규율 4 ㉮·㉯)과 항등 검사.

🔴 왜 사전등록 **전**에 도는가
  · `docs/목표.md` 규율 4 가 「채택 크기 X · 오라클 천장 Y · X/Y = Z」를 **사전등록에 박으라**고 한다.
    그러려면 Y 를 먼저 알아야 한다.
  · 🔴 **이 러너는 귀무를 한 번도 안 만든다.** 순열 뽑기·p·판정은 여기서 안 나온다.
  · X=1.0일(**개선 눈금**)은 이 사이클이 고른 수가 아니라 `docs/목표.md` ③ 행에 이미 박혀 있던 수다.
  · 🔴 **933 의 m8 을 안 되풀이한다**: 이 산출물은 **사전등록 커밋과 다른 커밋**에 들어간다.
    그래야 「사전등록만 담은 커밋」이 정말로 사전등록만 담는다.

산출물: runners/out935_oracle.json
사용:   python3 runners/rawpanel935_oracle.py   (🔴 파이프 금지 — 리디렉션으로)
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
from state.calpanel933 import fit_identity  # noqa: E402
from state.rawpanel935 import (PANEL_ALL, PANEL_EXC, PANEL_ONLY,  # noqa: E402
                               oracle_layers, rows_pair)

SCRATCH = Path(os.environ.get(
    "G935_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/"
    "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad"))
NPZ = Path(os.environ.get("G935_NPZ", str(SCRATCH / "g922/daily.npz")))
OUT = ROOT / "runners/out935_oracle.json"
NPZ_SHA = "4472b7f69cb5170c8a804dfbdb72a0289dcd34936aa5e05b6e9e191878ae97b2"
SIZE_X = 1.0            # docs/목표.md ③ — 🔴 개선 눈금. 이 사이클이 고르지 않았다


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
        "팔": "935 사전등록 부속 — 🔴 LOO 오라클 천장(규율 4 ㉮·㉯)과 항등 검사",
        "🔴 이 러너가 안 하는 것": "귀무 생성 · 순열 뽑기 · p · 판정. 하나도 안 한다",
        "🔴 판": "원판 — cal_off=False · drop_first=False (티처 #76 의 2순위)",
        "① 입력": {"daily.npz(🔴 저장소 밖)": str(NPZ), "sha256": sha,
                 "🔴 925·928·933 이 쓴 파일과 같은가": sha == NPZ_SHA},
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/rawpanel935.py", "runners/rawpanel935_oracle.py",
                        "state/calpanel933.py", "state/paired928.py", "state/gap925.py",
                        "state/perm922.py", "state/interval918.py")},
        "설정": {"τ": TAU_PRIMARY, "기저선 lag": list(BASE_LAGS), "셀 최소 학습행": CELL_MIN,
               "분할": f"격자 sha256('{SPLIT_SALT}'+격자) 70/30",
               "채택 크기 X(일 · 🔴 개선 눈금)": SIZE_X},
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
    tab = gaps_from_events(rdates, rmags, V, OBS, DAY0)
    trm = tr_set[tab["gi"]]

    # ── ② 항등 검사 ───────────────────────────────────────────────────
    R = rows_pair(tab, tr_set, ho_set, cal_off=False)
    ref_all = improvement_rows(tab, tr_set, ho_set, cal_off=False, drop_first=False)
    ref_exc = improvement_rows(tab, tr_set, ho_set, cal_off=False, drop_first=True)
    out["② 항등 검사 — 🔴 안 맞으면 이 사이클은 여기서 멈춘다"] = {
        "표(cal_off=False) 복사본이 원본과 같은가": fit_identity(tab, trm, plant_const_cal=False),
        "W2-가 원판 전량 개선": {
            "paired928(drop_first=False)": ref_all["개선(일)"],
            "rawpanel935": R[PANEL_ALL]["개선(일)"],
            "🔴 비트로 같은가": bool(ref_all["개선(일)"] == R[PANEL_ALL]["개선(일)"]),
            "행·군집": [R[PANEL_ALL]["행(간격) 수"], R[PANEL_ALL]["군집(격자) 수"]]},
        "W2-나 b_prv=−1 제외 개선": {
            "paired928(drop_first=True)": ref_exc["개선(일)"],
            "rawpanel935": R[PANEL_EXC]["개선(일)"],
            "🔴 비트로 같은가": bool(ref_exc["개선(일)"] == R[PANEL_EXC]["개선(일)"]),
            "행·군집": [R[PANEL_EXC]["행(간격) 수"], R[PANEL_EXC]["군집(격자) 수"]]},
        "W3 b_prv=−1 이 prevmed 결측과 같은 행인가": R["🔴 b_prv=−1 과 prevmed 결측이 같은 행인가"],
        "행 회계(전량 = 제외 + 그 칸만)": {
            "전량": R[PANEL_ALL]["행(간격) 수"], "제외": R[PANEL_EXC]["행(간격) 수"],
            "그 칸만": R[PANEL_ONLY]["행(간격) 수"],
            "🔴 합이 맞나": bool(R[PANEL_ALL]["행(간격) 수"]
                           == R[PANEL_EXC]["행(간격) 수"] + R[PANEL_ONLY]["행(간격) 수"])},
        "b_prv 칸별 홀드아웃 행 수": R["b_prv 칸별 행 수"],
        "진짜의 3분위 경계": {"prevmed": R[PANEL_ALL]["prevmed 3분위 경계"],
                      "mag": R[PANEL_ALL]["mag 3분위 경계"],
                      "전체 중앙값": R[PANEL_ALL]["전체 중앙값"]},
    }

    # ── ③ 🔴 오라클 천장 — 층마다 LOO · 식별 가능성 (규율 4 ㉮·㉯) ────────
    orc = {}
    for key, lab in ((PANEL_ALL, "원판 전량"), (PANEL_EXC, "원판 − b_prv=−1 칸"),
                     (PANEL_ONLY, "b_prv=−1 칸만(진단)")):
        orc[key] = oracle_layers(R, key, cal_off=False, label=lab, size_x=SIZE_X)
        print("  층 완료", key, time.time() - t0, flush=True)
    out["③ 🔴 오라클 천장 (규율 4 ㉮ LOO · ㉯ 식별 가능성)"] = orc

    # ── ③-나 티처 #76 이 낸 수와의 대조(자기행포함 눈금) ─────────────────
    out["③-나 🔴 티처 #76 C5 와 대조"] = {
        "티처의 원판 진짜 개선": 0.7545204330866538,
        "내 원판 진짜 개선": R[PANEL_ALL]["개선(일)"],
        "🔴 비트로 같은가": bool(R[PANEL_ALL]["개선(일)"] == 0.7545204330866538),
        "티처의 원판 Y(자기 행 포함)": 0.8655717983303575,
        "내 원판 Y(자기 행 포함)":
            orc[PANEL_ALL]["층"]["① 시험 팔의 칸 구조(dow·quarter·b_prv·b_mag)"]["자기행포함 개선(일) — 🔴 암기 · 진단으로만"],
        "🔴 내 원판 Y(LOO · 판정용)": orc[PANEL_ALL]["🔴 판정용 Y(= ① 층의 LOO)"],
        "티처의 첫간격제외 진짜 개선": 0.4478748692592945,
        "내 b_prv=−1 제외 진짜 개선": R[PANEL_EXC]["개선(일)"],
        "티처의 첫간격제외 Y(자기 행 포함)": 0.4684986212798332,
        "내 제외판 Y(자기 행 포함)":
            orc[PANEL_EXC]["층"]["① 시험 팔의 칸 구조(dow·quarter·b_prv·b_mag)"]["자기행포함 개선(일) — 🔴 암기 · 진단으로만"],
        "🔴 내 제외판 Y(LOO · 판정용)": orc[PANEL_EXC]["🔴 판정용 Y(= ① 층의 LOO)"],
    }

    # ── ③-다 크기 눈금 — 🔴 개선 눈금 하나로 통일한다 (티처 #76 C4) ────────
    ya = orc[PANEL_ALL]["🔴 판정용 Y(= ① 층의 LOO)"]
    ye = orc[PANEL_EXC]["🔴 판정용 Y(= ① 층의 LOO)"]
    out["③-다 🔴 크기 눈금 — 판정용은 **개선** 눈금 하나다 (티처 #76 C4)"] = {
        "🔴 판정용 눈금": "개선 = MAE(기준) − MAE(시험). X=1.0일 의 근거 문장이 그 눈금이다"
                    "(docs/목표.md ③: 「MAE 가 10.38 → 10.37」)",
        "판 ①": {"진짜 개선": R[PANEL_ALL]["개선(일)"],
                "X ÷ 진짜 개선 = 몇 배 모자라나(개선 눈금 · 🔴 판정용)":
                    SIZE_X / R[PANEL_ALL]["개선(일)"],
                "Y(LOO)": ya, "Z = X/Y": SIZE_X / ya if ya and ya > 0 else None},
        "판 ②": {"진짜 개선": R[PANEL_EXC]["개선(일)"],
                "X ÷ 진짜 개선(개선 눈금)": SIZE_X / R[PANEL_EXC]["개선(일)"],
                "Y(LOO)": ye, "Z = X/Y": SIZE_X / ye if ye and ye > 0 else None},
        "🔴 효과 눈금은 여기서 안 낸다": "효과(진짜 − 귀무평균)는 귀무가 있어야 나온다 — "
                              "측정 뒤 정본에 **병기**하되 판정에 안 쓴다(티처 #76 C4)",
    }

    # ── ③-라 네 판 대조(자기행포함 · 티처 #76 C5 의 Z 표를 LOO 로 다시) ────
    four = {}
    for panel, (cal_off, drop_first) in PANEL_DEF.items():
        Rp = rows_pair(tab, tr_set, ho_set, cal_off=cal_off)
        key = PANEL_EXC if drop_first else PANEL_ALL
        o = oracle_layers(Rp, key, cal_off=cal_off, label=panel, size_x=SIZE_X)
        L = o["층"]["① 시험 팔의 칸 구조(dow·quarter·b_prv·b_mag)"]
        four[panel] = {
            "진짜 개선": Rp[key]["개선(일)"],
            "Y 자기행포함": L["자기행포함 개선(일) — 🔴 암기 · 진단으로만"],
            "🔴 Y LOO": L["🔴 LOO 개선(일) — 판정용"],
            "Z(LOO 기준)": (SIZE_X / L["🔴 LOO 개선(일) — 판정용"])
                        if L["🔴 LOO 개선(일) — 판정용"] > 0 else None,
            "칸 수": L["칸 수"], "칸당 평균 행": L["칸당 평균 행"],
            "천장의 몇 %(LOO 기준)": (100.0 * Rp[key]["개선(일)"] / L["🔴 LOO 개선(일) — 판정용"])
                              if L["🔴 LOO 개선(일) — 판정용"] > 0 else None,
        }
        print("  네 판", panel, time.time() - t0, flush=True)
    out["③-라 네 판을 같은 자로 다시 (🔴 LOO)"] = four

    out["시작 UTC"] = tstart.isoformat(timespec="seconds")
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(_scrub(out), ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT, out["초"], "초")


if __name__ == "__main__":
    main()
