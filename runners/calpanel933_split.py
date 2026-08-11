# -*- coding: utf-8 -*-
"""팔 933 **진단** — [달력제거]의 개선이 **어느 행에서 오나**.

🔴 **이것은 판정이 아니다.** 사전등록 §4 의 판정은 `runners/out933_calpanel.json` 하나로 끝났다.
이 러너는 그 판정 **뒤에** 돌고, 산출물의 어떤 수도 판정에 못 들어간다 —
**행을 결과 보고 가른 사후 부분집합**이기 때문이다(티처 #60 M2 가 걸린 병).
쓰임은 **다음 사이클의 후보**를 가리키는 것 하나다.

나누는 축은 하나: `prevmed` 가 있는가 = **그 격자의 첫 간격인가**.
  · 첫 간격 행 2,277 = [달력제거] − [둘 다] 의 차이
  · 나머지 52,585 = [둘 다] 판 그대로

산출물: runners/out933_split.json
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

from state.interval918 import (DAY0, NDAY, OBS_MIN_FRAC, TAU_PRIMARY,  # noqa: E402
                               baseline_ratio, sha256_text, split_grids, surges)
from state.perm922 import gaps_from_events, real_events  # noqa: E402
from state.gap925 import null_n2_plantable  # noqa: E402
from state.calpanel933 import _cell_oracle, rows_x  # noqa: E402

SCRATCH = Path(os.environ.get(
    "G933_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/"
    "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad"))
NPZ = Path(os.environ.get("G933_NPZ", str(SCRATCH / "g922/daily.npz")))
OUT = ROOT / "runners/out933_split.json"
NSEED = int(os.environ.get("G933_SPLIT_N", "20"))
NPZ_SHA = "4472b7f69cb5170c8a804dfbdb72a0289dcd34936aa5e05b6e9e191878ae97b2"


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
    out = {
        "팔": "933 진단 — 개선이 어느 행에서 오나",
        "🔴 이것은 판정이 아니다": "행을 나눈 축이 사전등록에 없다. 사후 부분집합이므로 "
                          "이 산출물의 어떤 수도 933 판정에 안 들어간다. 다음 사이클의 후보일 뿐이다",
        "언제": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/calpanel933.py", "runners/calpanel933_split.py")},
    }
    z = np.load(NPZ, allow_pickle=False)
    V = z["V"].astype(np.float64)
    OBS = z["C"] > 0
    grids = z["grids"].tolist()
    G, D = V.shape
    assert D == NDAY
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
    real = rows_x(tab_real, tr_set, ho_set, cal_off=True, drop_first=False)
    hom = real["_hom"]
    is_first = ~np.isfinite(tab_real["prevmed"][hom])          # 격자의 첫 간격
    y = real["_gap_panel"]

    def parts(rows):
        imp = rows["imp"]
        return {"첫 간격 행": float(imp[is_first].mean()),
                "나머지 행": float(imp[~is_first].mean()),
                "전체": float(imp.mean())}

    pr = parts(real)
    nulls = []
    for s in range(1, NSEED + 1):
        dd, mm, _mv, _hh = null_n2_plantable(first, r, seed=s)
        tb = gaps_from_events(dd, mm, V, OBS, DAY0)
        nulls.append(parts(rows_x(tb, tr_set, ho_set, cal_off=True, drop_first=False)))
    nf = np.asarray([x["첫 간격 행"] for x in nulls])
    nr = np.asarray([x["나머지 행"] for x in nulls])
    na = np.asarray([x["전체"] for x in nulls])
    w1 = float(is_first.mean())

    # 첫 간격 행만의 오라클 천장 (같은 칸 구조)
    yb = y[is_first]
    base_f = float(np.abs(yb - 6.0).mean())
    prv = tab_real["prevmed"][hom][is_first]
    mag = tab_real["mag"][hom][is_first]
    from state.interval918 import _bin
    T = real["_T"]
    bp = np.asarray([_bin(v, T["prevmed 3분위 경계"]) for v in prv], int)
    bm = np.asarray([_bin(v, T["mag 3분위 경계"]) for v in mag], int)
    o1 = _cell_oracle(yb, (bp + 1) * 10 + (bm + 1))
    o_grid = _cell_oracle(yb, real["gi"][is_first])

    out["행 회계(조항 60 — 세 분모)"] = {
        "판 행(홀드아웃 간격)": int(y.size),
        "🔴 첫 간격 행(prevmed 결측 · 격자마다 하나)": int(is_first.sum()),
        "나머지 행(= [둘 다] 판의 행)": int((~is_first).sum()),
        "첫 간격 행의 비중": w1,
    }
    out["🔴 개선을 행으로 갈랐다 (일)"] = {
        "진짜": pr,
        "귀무 %d개 평균" % NSEED: {"첫 간격 행": float(nf.mean()), "나머지 행": float(nr.mean()),
                            "전체": float(na.mean())},
        "귀무 SD(ddof=1)": {"첫 간격 행": float(nf.std(ddof=1)), "나머지 행": float(nr.std(ddof=1)),
                        "전체": float(na.std(ddof=1))},
        "🔴 차(진짜 − 귀무평균)": {
            "첫 간격 행": pr["첫 간격 행"] - float(nf.mean()),
            "나머지 행": pr["나머지 행"] - float(nr.mean()),
            "전체": pr["전체"] - float(na.mean())},
        "🔴 전체 차에서 첫 간격 행이 낸 몫":
            w1 * (pr["첫 간격 행"] - float(nf.mean())) / (pr["전체"] - float(na.mean())),
    }
    out["🔴 첫 간격 행의 정답"] = {
        "진짜 홀드아웃 첫 간격 중앙값": float(np.median(yb)),
        "진짜 홀드아웃 첫 간격 평균": float(yb.mean()),
        "기준 팔(상수 6.0)의 MAE": base_f,
        "그 칸 구조의 오라클 MAE": o1["MAE"], "칸 수": o1["칸 수"],
        "🔴 오라클 천장(첫 간격 행만)": base_f - o1["MAE"],
        "격자 정체 오라클 MAE": o_grid["MAE"], "그 개선": base_f - o_grid["MAE"],
    }
    out["🔴 그래서 무엇을 말하나(다음 사이클의 후보 · 결론 아님)"] = (
        "[달력제거] 판의 개선은 **격자의 첫 간격 행**에서 크게 나온다 — 순열은 그 행의 "
        "「첫 간격은 길다」를 부순다. 🔴 그런데 이 축은 사전등록에 없었고 행을 결과 보고 갈랐다. "
        "**다음 사이클이 이것을 재려면 사전등록에 축과 크기를 먼저 박아야 한다.**")
    out["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(_scrub(out), ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT, out["초"], "초")


if __name__ == "__main__":
    main()
