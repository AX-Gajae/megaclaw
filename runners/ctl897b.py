"""노트 897 · **사후 진단 ㅂ** — 🔴 사전등록 밖. 판정에 안 쓴다.

`ctl897.py` 의 ㄷ 가 뜻밖의 것을 냈다: **날짜 지표 1열의 S 가 +0.10028** 로
장 표현 8열(+0.05075)의 **두 배**다. 그리고 표현 8열은 날짜와 세게 단조다
(열별 스피어만 +0.776 · −0.766 · −0.545 · +0.472 · +0.469 …).

**그러면 물음은 하나다 — 장이 시각을 뺀 뒤에도 남나?**

    ㅂ-1  시각만          ridge( [날짜 지표] )
    ㅂ-2  시각 + 장       ridge( [날짜 지표, 표현 8열] )
    ㅂ-3  장만            ridge( [표현 8열] )            = decay897 의 「표현」

**ΔS = ㅂ-2 − ㅂ-1** 이 장의 **증분**이다. 셋을 같은 자·같은 널로 낸다.
🔴 시각과 장의 열 수가 다르므로(1 대 8 대 9) **널을 팔마다 따로 뽑는다.**
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")

from runners import decay897 as D           # noqa: E402

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()
OUT = ROOT / "runners/out897_partial.json"


def stamp() -> dict:
    h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                       capture_output=True, text=True).stdout.strip()
    return {"git HEAD": h, "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "코드 sha(ctl897b.py)": hashlib.sha256(ME.read_bytes()).hexdigest()[:16],
            "🔴 지위": "사후 진단 — 사전등록 밖. 판정에 안 쓴다"}


def arm(rs, rows, F, tag, drop_degenerate: bool):
    r2 = dict(rs)
    r2["F"] = F
    r2["one"] = np.arange(len(rs["yrs"]), dtype=float)
    tab = D.table(r2, rows)
    per = D.measure(tab)
    if drop_degenerate:
        bad = [dm for dm, p in per.items()
               if "제외" not in p and p["유보 고유날"] < 10]
        rows2 = {k: v for k, v in rows.items() if k not in bad}
        tab = D.table(r2, rows2)
        per = D.measure(tab)
    S, used, n = D.headline(tab, per, "표현")
    nul = D.perm_null(tab, per, "표현")
    ci = D.boot_ci(tab, per, "표현")
    return {"팔": tag, "열 수": int(F.shape[1]), "S": round(float(S), 5), "n": n,
            "순열 널": nul, "군집 BCa": {k: v for k, v in ci.items() if k != "군집 병기"},
            "군집 병기": ci["군집 병기"],
            "🔴 널 2σ 밖": bool(abs(S - nul["널 평균"]) > nul["널 2σ"]),
            "도메인별": used}


def main():
    rs = D.rep_series()
    rows, _d0 = D.board_rows()
    t = np.arange(len(rs["yrs"]), dtype=float)[:, None]
    t = (t - t.mean()) / t.std()
    Fr = rs["F"]
    out = {"stamp": stamp(), "팔": {}}
    for tag, F in (("ㅂ-1 시각만", t), ("ㅂ-2 시각+장", np.hstack([t, Fr])),
                   ("ㅂ-3 장만", Fr)):
        for sub, dd in (("전 도메인", False), ("퇴화 제외", True)):
            r = arm(rs, rows, F, f"{tag} · {sub}", dd)
            out["팔"][f"{tag} · {sub}"] = r
            print(json.dumps({"팔": r["팔"], "S": r["S"], "n": r["n"],
                              "BCa": [r["군집 BCa"]["lo"], r["군집 BCa"]["hi"]],
                              "판정": r["군집 BCa"]["판정(0 을 무나)"]},
                             ensure_ascii=False), flush=True)
    for sub in ("전 도메인", "퇴화 제외"):
        a = out["팔"][f"ㅂ-1 시각만 · {sub}"]["S"]
        b = out["팔"][f"ㅂ-2 시각+장 · {sub}"]["S"]
        out.setdefault("🔴 장의 증분 ΔS = ㅂ2 − ㅂ1", {})[sub] = round(b - a, 5)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(out["🔴 장의 증분 ΔS = ㅂ2 − ㅂ1"], ensure_ascii=False))
    print("→", OUT)


if __name__ == "__main__":
    main()
