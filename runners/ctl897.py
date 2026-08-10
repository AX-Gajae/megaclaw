"""노트 897 · **사후 진단**(🔴 사전등록에 없다 — 그렇게 표시하고 판정에 안 쓴다).

`runners/decay897.py`(사전등록 코드 · 커밋 33926f2af)의 결과를 보고 나서 생긴
물음 셋을 잰다. **판정은 사전등록 규칙으로 하고, 여기 값은 「다음 사이클의
확인 대상」으로만 쓴다**(노트 133 의 정신 — 첫 양수를 그대로 채택하지 않는다).

**ㄷ 시간 대용 통제** — 장의 표현이 날짜만의 함수라, 라벨이 시간 추세를 가지면
  표현은 **달력의 대용값**만으로도 상관을 낸다. 그래서 표현 8열을 **같은 열 수의
  순수 시간 기저**(날짜 위 RBF 8개)로 바꿔 같은 S 를 낸다.
  🔴 **위약 팔(날짜 연결 끊기)은 이것을 못 잡는다** — 무작위 날짜는 추세도 같이
  지우기 때문이다. 그러므로 시간 통제는 위약과 **다른 물음**이다.

**ㄹ 퇴화 도메인 제외** — 유보 고유날이 2 인 도메인이 넷 있다(시작 시각이 연
  단위). 두 값짜리 특성에서 스피어만은 **한 대비의 부호**일 뿐이다.

**ㅁ 도메인 하나 빼기(LOO)** — 조항 60. 결론을 한 도메인이 지고 있나.
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
OUT = ROOT / "runners/out897_control.json"
NRBF = 8


def stamp() -> dict:
    h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                       capture_output=True, text=True).stdout.strip()
    return {"git HEAD": h, "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "코드 sha(ctl897.py)": hashlib.sha256(ME.read_bytes()).hexdigest()[:16],
            "코드 sha(decay897.py)":
                hashlib.sha256((ROOT / "runners/decay897.py").read_bytes()).hexdigest()[:16],
            "🔴 지위": "사후 진단 — 사전등록 밖. 판정에 안 쓴다"}


def time_basis(n_days: int) -> np.ndarray:
    """날짜 위 RBF 8개. **표현과 열 수를 맞춘다**(8열 대 8열)."""
    z = np.linspace(0.0, 1.0, n_days)
    cs = np.linspace(0.0, 1.0, NRBF)
    w = 1.0 / NRBF
    return np.exp(-0.5 * ((z[:, None] - cs[None, :]) / w) ** 2)


def drift(rs) -> dict:
    """표현 8열이 날짜와 얼마나 단조인가 — 대용값 의심의 직접 진단."""
    F, yrs = rs["F"], rs["yrs"]
    return {f"열 {j}": round(D._sp(F[:, j], yrs), 4) for j in range(F.shape[1])}


def s_of(tab, per, arm):
    S, used, n = D.headline(tab, per, arm)
    return (round(float(S), 5) if np.isfinite(S) else None), used, n


def main():
    rs = D.rep_series()
    rows, _d0 = D.board_rows()
    out = {"stamp": stamp(), "표현 열의 날짜 상관(스피어만)": drift(rs)}

    # ── 진짜(재현) ────────────────────────────────────────────────
    tab = D.table(rs, rows)
    per = D.measure(tab)
    for arm in ("1열", "표현"):
        S, used, n = s_of(tab, per, arm)
        out.setdefault("ㄱ 진짜(재현)", {})[arm] = {"S": S, "n": n}

    # ── ㄷ 시간 대용 통제 ─────────────────────────────────────────
    TB = time_basis(len(rs["yrs"]))
    rs_t = dict(rs)
    rs_t["F"] = TB
    rs_t["one"] = np.arange(len(rs["yrs"]), dtype=float)   # 1열 통제 = 날짜 자체
    tab_t = D.table(rs_t, rows)
    per_t = D.measure(tab_t)
    out["ㄷ 시간 대용 통제"] = {"뜻": "표현 8열을 순수 시간 RBF 8열로 바꿨다. "
                                 "1열 통제는 날짜 지표 자체다."}
    for arm in ("1열", "표현"):
        S, used, n = s_of(tab_t, per_t, arm)
        out["ㄷ 시간 대용 통제"][arm] = {"S": S, "n": n, "도메인별": used}
    out["ㄷ 시간 대용 통제"]["순열 널(시간 8열)"] = D.perm_null(tab_t, per_t, "표현")
    out["ㄷ 시간 대용 통제"]["군집 BCa(시간 8열)"] = D.boot_ci(tab_t, per_t, "표현")

    # ── ㄹ 퇴화 도메인 제외 ───────────────────────────────────────
    bad = [dm for dm, p in per.items()
           if "제외" not in p and p["유보 고유날"] < 10]
    keep = {dm: v for dm, v in rows.items() if dm not in bad}
    tab_k = D.table(rs, keep)
    per_k = D.measure(tab_k)
    out["ㄹ 퇴화 도메인 제외"] = {"뺀 도메인(유보 고유날 < 10)": bad}
    for arm in ("1열", "표현"):
        S, used, n = s_of(tab_k, per_k, arm)
        out["ㄹ 퇴화 도메인 제외"][arm] = {"S": S, "n": n, "도메인별": used}
    out["ㄹ 퇴화 도메인 제외"]["순열 널(표현)"] = D.perm_null(tab_k, per_k, "표현")
    out["ㄹ 퇴화 도메인 제외"]["군집 BCa(표현)"] = D.boot_ci(tab_k, per_k, "표현")
    # 같은 부분집합에서 시간 통제도 낸다 --- 분모를 맞춘다(조항 60)
    tab_kt = D.table(rs_t, keep)
    per_kt = D.measure(tab_kt)
    St, _u, nt = s_of(tab_kt, per_kt, "표현")
    out["ㄹ 퇴화 도메인 제외"]["같은 부분집합의 시간 8열 통제 S"] = {"S": St, "n": nt}

    # ── ㅁ 도메인 하나 빼기 ───────────────────────────────────────
    loo = {}
    for dm in list(rows):
        sub = {k: v for k, v in rows.items() if k != dm}
        tb = D.table(rs, sub)
        pr = D.measure(tb)
        S, _u, n = s_of(tb, pr, "표현")
        loo[f"{dm} 뺌"] = {"S(표현)": S, "n": n}
    out["ㅁ 도메인 하나 빼기(표현)"] = loo

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps({"ㄱ": out["ㄱ 진짜(재현)"],
                      "ㄷ 시간 8열 S": out["ㄷ 시간 대용 통제"]["표현"]["S"],
                      "ㄷ 날짜 1열 S": out["ㄷ 시간 대용 통제"]["1열"]["S"],
                      "ㄹ 뺀 도메인": bad,
                      "ㄹ 표현 S": out["ㄹ 퇴화 도메인 제외"]["표현"]["S"],
                      "ㄹ 같은 부분집합 시간 S": St},
                     ensure_ascii=False, indent=1))
    print("→", OUT)


if __name__ == "__main__":
    main()
