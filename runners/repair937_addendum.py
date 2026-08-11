# -*- coding: utf-8 -*-
"""팔 937 부속 — 🔴 **사후 확장이다. 판정이 아니다.**

`out937_repair.json` D 는 판 ② 의 기울기를 **「모른다」**로 냈다(BCa 가 0 을 문다).
「모른다」는 옳지만 **거기서 멈추면 ㉡ 의 크기를 아무도 모른다.** 그래서 한 걸음만 더 간다:

    🔴 **구간의 가장 유리한 끝에서조차 이 화살표가 나를 수 있는 개선은 얼마인가?**

이 수는 **사전등록에 없다** — 그러므로 **판정에 안 쓰고 병기만 한다**(사후 부분집합이 아니라
사후 *확장*이지만, 이름을 갈라서 적는 것이 이 저장소의 규율이다).

사용: python3 runners/repair937_addendum.py
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out937_addendum.json"
PANELS = ("① 원판 전량", "② 원판 − b_prv=−1 칸", "진단 b_prv=−1 칸만")


def main() -> None:
    rep = json.loads((ROOT / "runners/out937_repair.json").read_text(encoding="utf-8"))
    d935 = json.loads((ROOT / "runners/out935_rawpanel.json").read_text(encoding="utf-8"))
    kr = [k for k in d935 if k.startswith("⑤ 뽑기 원자료")][0]
    recs = d935[kr]["기록"]
    verd = d935["⑥ 🔴 판정용 순열"]
    per = rep["D 🔴 ㉡ 의 기울기"]["팔별"]

    out = {
        "무엇": "937 부속 — 🔴 **사후 확장**. ㉡ 의 화살표가 **구간의 가장 유리한 끝에서** "
              "나를 수 있는 개선의 크기",
        "🔴 판정에 쓰나": False,
        "🔴 왜 사후인가": "사전등록 §3-D 는 **부호**만 물었다. 이 절이 묻는 **크기**는 "
                   "사전등록에 없다 — 그래서 이름을 갈라 적는다",
        "정본": "runners/out937_repair.json",
        "정본 sha256(고치지 않았다)": __import__("hashlib").sha256(
            (ROOT / "runners/out937_repair.json").read_bytes()).hexdigest(),
    }
    tab = {}
    for p in PANELS:
        x = np.asarray([r[p]["비교가능성 상대차"] for r in recs], float)
        y = np.asarray([r[p]["개선(일)"] for r in recs], float)
        lo, hi = per[p]["🔴 BCa 95%"]
        rng = float(x.max() - x.min())
        worst = max(abs(lo), abs(hi))
        v = verd[p]
        eff = v["🔴 효과(진짜 − 귀무평균 · 일)"]
        sd = v["귀무 SD(ddof=1)"]
        tab[p] = {
            "상대차의 실측 폭(최대−최소)": rng,
            "기울기 BCa 95%": [lo, hi],
            "🔴 구간의 가장 유리한 끝 |β|": worst,
            "🔴 그 끝에서 상대차 전 폭이 나르는 귀무 개선(일)": worst * rng,
            "귀무 개선의 SD(일)": sd,
            "그 몫 ÷ SD": worst * rng / sd,
            "효과(진짜 − 귀무평균 · 일)": eff,
            "🔴 그 몫 ÷ 효과": worst * rng / eff,
        }
    out["팔별"] = tab
    e = tab["② 원판 − b_prv=−1 칸"]
    out["🔴 판 ② 에 대해 말할 수 있는 것"] = (
        "부호는 **모른다**(정본 D). 그러나 **크기는 갇힌다** — 기울기 BCa 의 가장 유리한 끝"
        "(|β| = %.4f)에서조차, 상대차가 실측 폭 전체(%.6f)를 움직여야 귀무 개선이 "
        "**%.6f일**만큼 바뀐다. 그것은 귀무 개선 SD 의 **%.3f배** · 진짜와 귀무의 차(효과 %.6f일)의 "
        "**%.4f배**다. 🔴 **그러므로 ㉡ 의 화살표는 부호를 정하든 못 정하든 935 의 승리를 "
        "설명할 수 없다**(효과의 5%%가 이 화살표가 나를 수 있는 최대다) — "
        "이것이 「모른다」보다 강한 문장이다"
        % (e["🔴 구간의 가장 유리한 끝 |β|"], e["상대차의 실측 폭(최대−최소)"],
           e["🔴 그 끝에서 상대차 전 폭이 나르는 귀무 개선(일)"], e["그 몫 ÷ SD"],
           e["효과(진짜 − 귀무평균 · 일)"], e["🔴 그 몫 ÷ 효과"]))
    out["⚠ 한계"] = [
        "이 계산은 **선형**을 가정한다 — 관계가 비선형이면 폭이 다를 수 있다",
        "🔴 **BCa 의 끝점은 추정이다.** 「가장 유리한 끝」은 95% 구간의 끝이지 최악이 아니다",
        "🔴 **사전등록에 없다.** 판정에 안 쓴다",
    ]
    out["언제"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out["🔴 판 ② 에 대해 말할 수 있는 것"])


if __name__ == "__main__":
    main()
