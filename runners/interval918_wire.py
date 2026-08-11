# -*- coding: utf-8 -*-
"""팔 918-ㅌ · 배선 검사 — 🔴 **결함을 심어서 검사가 실제로 붉어지는지 본다.**

915 의 「죽는 층은 없다」는 **원리상 발화할 수 없는 검사**가 낸 문장이었다(이슈 #171 ·
`grid915_ssl.py:243-246` 이 후보 집합에 `block0` 자신을 넣고 `v < block0/100` 을 걸었다).
그래서 이 팔은 검사마다 결함을 심고 **발화 여부를 센다.** 못 심으면 **검정력 0 으로 신고**한다.

여섯 검사는 사전등록 §7 의 표 그대로다(W1~W6). 음성 대조(아무것도 안 심은 사본)도 돈다.

산출물: runners/out918_wire.json
사용:   python3 runners/interval918_wire.py
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
from state.interval918 import (DAY0, TAU_PRIMARY, baseline_ratio,  # noqa: E402
                               events_and_gaps, fit_tables, permute_events,
                               predict, sha256_text, split_grids, surges)

SCRATCH = Path(os.environ.get(
    "G918_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad")) / "g918"
OUT = ROOT / "runners/out918_wire.json"
NG = int(os.environ.get("G918_WIRE_GRIDS", "2000"))     # 검사는 부분집합으로 충분하다


def check_sha(mine: dict, theirs: dict) -> dict:
    same = sum(1 for k, v in mine.items() if theirs.get(k) == v)
    return {"같다": same, "분모": len(mine), "통과": same == len(mine)}


def main() -> None:
    t0 = time.time()
    tstart = dt.datetime.now(dt.timezone.utc)
    z = np.load(SCRATCH / "daily.npz", allow_pickle=False)
    V = z["V"].astype(np.float64)[:NG]
    C = z["C"][:NG]
    grids = z["grids"].tolist()[:NG]
    OBS = C > 0
    obs_frac = OBS.mean(axis=1)
    base, r, ok = baseline_ratio(V, OBS)
    ok = ok & (obs_frac >= 0.95)[:, None]
    first = surges(r, ok, TAU_PRIMARY)
    tab = events_and_gaps(first, r, V, OBS, grids, [DAY0])
    G = len(grids)
    gidx = {g: i for i, g in enumerate(grids)}

    def masks(plant_leak=False):
        tr_g, ho_g = split_grids(grids, plant_leak=plant_leak)
        tr = np.zeros(G, bool)
        ho = np.zeros(G, bool)
        for g in tr_g:
            tr[gidx[g]] = True
        for g in ho_g:
            ho[gidx[g]] = True
        return tr_g, ho_g, tr[tab["gi"]], ho[tab["gi"]]

    #: 저장소 산출물의 zip sha256 — W1 의 기준본
    mine = {k: v["sha256"] for k, v in
            json.loads((ROOT / "runners/out918_build.json").read_text(
                encoding="utf-8"))["달별"].items()}
    theirs = {k: v["sha256"] for k, v in
              json.loads((ROOT / "runners/out915_count.json").read_text(
                  encoding="utf-8"))["달별"].items()}

    def run_case(name, *, plant):
        """한 사본에서 여섯 검사를 전부 돌린다. plant=None 이면 음성 대조."""
        res = {}
        # W1 입력 비트 대조
        t = dict(theirs)
        if plant == "W1":
            k0 = sorted(t)[0]
            t[k0] = "0" + t[k0][1:]
        c = check_sha(mine, t)
        res["W1 입력 zip sha256 비트 대조"] = c
        # W2 분할 누설
        tr_g, ho_g, trm, hom = masks(plant_leak=(plant == "W2"))
        res["W2 분할 누설"] = {"겹침": len(tr_g & ho_g),
                          "통과": len(tr_g & ho_g) == 0}
        # W6 달력이 실제로 쓰이나 (표를 만들 때 심는다)
        T = fit_tables(tab, trm, plant_const_cal=(plant == "W6"))
        res["W6 달력이 실제로 쓰이나"] = {"달력 셀 가짓수": T["🔴 달력 셀 가짓수"],
                               "통과": T["🔴 달력 셀 가짓수"] > 1}
        # 예측 (W3 오라클 · W4 상태 무시)
        pa, _ = predict(tab, hom, T, arm="가 기후값")
        pb, _ = predict(tab, hom, T, arm="나 조건부(주)",
                        plant_ignore_state=(plant == "W4"),
                        plant_oracle=(plant == "W3"))
        gap = tab["gap"][hom].astype(float)
        # W3 인과성 — 예측이 참값과 **정확히** 같은 행이 얼마나 되나
        exact = float((pb == gap).mean())
        res["W3 인과성(오라클 탐지)"] = {"예측==참값 비율": exact,
                               "문턱": 0.5, "통과": exact < 0.5}
        # W4 상태 열이 예측을 움직였나
        moved = float((pb != pa).mean())
        res["W4 상태 열이 예측에 닿았나"] = {"기후값과 다른 행 비율": moved,
                                 "통과": moved > 0.0}
        # W5 순열이 진짜 섞였나
        _, mv = permute_events(first, ok, seed=918,
                               plant_identity=(plant == "W5"))
        res["W5 순열이 실제로 섞였나"] = {"자리가 바뀐 격자 비율": mv,
                               "문턱": 0.9, "통과": mv > 0.9}
        res["🔴 이 사본에서 실패한 검사"] = [k for k, v in res.items()
                                  if isinstance(v, dict) and v.get("통과") is False]
        # 개선값도 같이 적는다(W3 는 여기서 폭증해야 한다)
        res["개선(일) — 참고"] = float((np.abs(gap - pa) - np.abs(gap - pb)).mean())
        return res

    neg = run_case("음성 대조", plant=None)
    planted, fired, missed = 0, 0, []
    cases = {"음성 대조(아무것도 안 심었다)": neg}
    for w in ("W1", "W2", "W3", "W4", "W5", "W6"):
        planted += 1
        c = run_case(w, plant=w)
        cases[f"{w} 심음"] = c
        target = [k for k in c if k.startswith(w)][0]
        ok_fire = (c[target]["통과"] is False)
        c["🔴 심은 검사가 붉어졌나"] = ok_fire
        #: 🔴 국소성 — 심은 것만 붉어졌나(남이 대신 붉어지면 겹치는 방어다)
        c["🔴 국소 시험(심은 것만 붉어졌나)"] = (c["🔴 이 사본에서 실패한 검사"] == [target])
        if ok_fire:
            fired += 1
        else:
            missed.append(w)

    out = {
        "팔": "918-ㅌ", "단계": "배선 검사(심어서 확인 · 사전등록 §7)",
        "사전등록": "docs/prereg_918_interval.md",
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/interval918.py", "runners/interval918_wire.py")},
        "🔴 분모": {"검사 수": 6, "심은 결함 수": planted,
                 "검사에 쓴 격자(부분집합)": G,
                 "그 부분집합의 간격 수": tab["🔴 간격 수(분모 B)"]},
        "🔴 검정력": {"심은 수": planted, "발화한 수": fired,
                   "🔴 놓친 수": len(missed), "놓친 것": missed or "없다",
                   "🔴 검정력": fired / planted if planted else None},
        "🔴 음성 대조(안 심은 사본)에서 실패한 검사":
            neg["🔴 이 사본에서 실패한 검사"] or "없다(여섯 전부 통과)",
        "사본별": cases,
        "🔴 못 한 것": [
            "W1 은 저장소 산출물의 문자열 대조다 — zip 자체를 다시 해싱해 비교한 것은 "
            "runners/interval918_build.py 안에서 했고(19/19 일치), 여기서는 그 결과를 "
            "**심어서 깨뜨릴 수 있는지**만 시험한다",
            "검사는 격자 부분집합에서 돈다 — 판정 러너의 전량과 분모가 다르다(조항 60)",
        ],
        "시작 UTC": tstart.isoformat(timespec="seconds"),
        "끝 UTC": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "초": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["🔴 검정력"], ensure_ascii=False))
    print(json.dumps({k: v.get("🔴 심은 검사가 붉어졌나", "음성") for k, v in cases.items()},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
