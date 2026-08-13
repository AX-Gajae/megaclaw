# -*- coding: utf-8 -*-
"""노트 966 — 🔴 **사후 강건성 검사. 사전등록에 없다. 그렇게 신고한다.**

**물음**: §4 의 「들뜸」이 실은 **「문서가 최근에 생겼다」**를 재는 것 아닌가?
긴 띠(시작일 이전 91~455일)의 조회수가 0 에 가까우면 들뜸이 커진다. 그리고 그것은
**문서 나이**의 함수다. 두 자를 못 가르면 §4 의 명제는 「기억」이 아니라
**「신참인가」**를 말하는 것이 된다.

🔴 **이것은 판정을 바꾸려는 것이 아니다**(F8). §4 의 자는 그대로 두고,
**나이를 하나 더 뺀 뒤에도 부호가 살아남나**를 잰다. 살아남으면 §4 가 세진다.
안 살아남으면 **§4 의 뜻이 좁아진다** — 그리고 그 좁아진 뜻을 그대로 적는다.

`나이` = 시작일 이전에 **조회수가 있는 날의 수**(원천 개시일 2015-07-01 이후).

    python3 runners/agecheck966.py --out runners/out966_age.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
os.chdir(str(ROOT))

sys.argv0 = None
import longmem966 as LM                                   # noqa: E402


def _rank(x):
    x = np.asarray(x, float)
    o = x.argsort().argsort().astype(float)
    return (o - o.mean()) / (o.std() + 1e-12)


def _resid(a, *ctrl):
    """순위 잔차 — 통제열을 차례로 뺀다(그람-슈미트)."""
    r = _rank(a)
    for c in ctrl:
        rc = _rank(c)
        rc = rc / (rc.std() + 1e-12)
        r = r - rc * float((r * rc).mean())
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "runners/out966_age.json"))
    ap.add_argument("--draws", type=int, default=1000)
    a = ap.parse_args()

    recs = LM.load_series()
    val, _ = LM.excite(recs)

    # 나이 — 시작일 이전에 조회수 > 0 인 날의 수
    age = {}
    for k, r in recs.items():
        s = r.get("시작일")
        if not s or k not in val:
            continue
        s0 = dt.date(*map(int, s.split("-"))).toordinal()
        dd = np.array([LM._d2o(x) for x in r["날짜"]])
        vv = np.asarray(r["조회수"], float)
        age[k] = int(((dd < s0) & (vv > 0)).sum())

    data, ids = LM.board_keys()
    rng = np.random.RandomState(9660)
    out = {}
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        nm = list(data.names.get(d) or [])
        kk = ids.get(d)
        if not kk or len(kk) != len(y) or "wiki_level" not in nm:
            continue
        ex = np.array([val.get(k, np.nan) for k in kk], float)
        ag = np.array([age.get(k, np.nan) for k in kk], float)
        lv = A[:, nm.index("wiki_level")].astype(float)
        ok = np.isfinite(ex) & np.isfinite(ag) & np.isfinite(y) & np.isfinite(lv)
        if ok.sum() < 30:
            out[d] = {"n": int(ok.sum()), "🔴 잰다": False}
            continue
        x, aa, yy, zz = ex[ok], ag[ok], y[ok], lv[ok]
        rx1 = _resid(x, zz)                    # §4 와 같은 자(수준만 뺀 것)
        rx2 = _resid(x, zz, aa)                # 🔴 나이를 하나 더 뺀 것
        ry1 = _resid(yy, zz)
        ry2 = _resid(yy, zz, aa)
        p1 = float((rx1 * ry1).mean() / (rx1.std() * ry1.std() + 1e-12))
        p2 = float((rx2 * ry2).mean() / (rx2.std() * ry2.std() + 1e-12))
        nl = []
        for _ in range(a.draws):
            pm = rng.permutation(len(yy))
            ry = _resid(yy[pm], zz, aa)
            nl.append(float((rx2 * ry).mean() / (rx2.std() * ry.std() + 1e-12)))
        nl = np.array(nl)
        flo = float(np.percentile(np.abs(nl), 95))
        out[d] = {
            "n": int(ok.sum()), "🔴 잰다": True,
            "들뜸 ↔ 나이(순위)": round(float((_rank(x) * _rank(aa)).mean()), 4),
            "§4 의 자(수준만 뺌)": round(p1, 4),
            "🔴 나이까지 뺀 뒤": round(p2, 4),
            "순열 바닥 |ρ| 95%": round(flo, 4),
            "🔴 바닥을 넘었나": bool(abs(p2) > flo),
            "🔴 부호가 살아남았나": bool(p1 * p2 > 0),
        }
    live = {d: v for d, v in out.items() if v.get("🔴 잰다")}
    over = {d: v for d, v in live.items() if v["🔴 바닥을 넘었나"]}
    R = {"노트": 966, "레인": "판정 · 🔴 **사후 강건성 — 사전등록에 없다**",
         "🔴 물음": ("§4 의 「들뜸」이 실은 「문서가 최근에 생겼다」를 재는 것 아닌가. "
                 "긴 띠의 조회수가 0 에 가까우면 들뜸이 커지고 그것은 문서 나이의 함수다"),
         "🔴 무엇을 안 바꿨나": "§4 의 자를 안 바꿨다(F8). **나이를 하나 더 뺀 판을 곁에 낸다**",
         "나이의 정의": "시작일 이전에 조회수 > 0 인 날의 수(원천 개시일 2015-07-01 이후)",
         "코드 sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         "도메인별": out,
         "🔴 분모: 잰 도메인": len(live),
         "🔴 잰 개체 합": int(sum(v["n"] for v in live.values())),
         "🔴 나이까지 뺀 뒤 바닥을 넘은 도메인": len(over),
         "🔴 그중 양수": sum(1 for v in over.values() if v["🔴 나이까지 뺀 뒤"] > 0),
         "🔴 그중 음수": sum(1 for v in over.values() if v["🔴 나이까지 뺀 뒤"] < 0),
         "🔴 부호가 살아남은 도메인": sum(1 for v in live.values() if v["🔴 부호가 살아남았나"]),
         "끝(UTC)": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
    Path(a.out).write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in R.items() if k != "도메인별"},
                     ensure_ascii=False, indent=1))
    for d, v in sorted(live.items(), key=lambda kv: -kv[1]["🔴 나이까지 뺀 뒤"]):
        print(d, json.dumps(v, ensure_ascii=False))


if __name__ == "__main__":
    main()
