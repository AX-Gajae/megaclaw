# -*- coding: utf-8 -*-
"""노트 899 · 🔴 **DEFF 검산** — 인용한 공식으로 직접 대입해 실측과 나란히 놓는다.

티처 #61 이 898 탐색을 친 자리가 정확히 여기다:
*"DEFF 4.8 을 냈는데 유도가 안 선다 · 자기가 인용한 공식으로 검산 안 했다."*

공식:  DEFF = 1 + (m̄ − 1)·ICC      (도메인마다)
       판 DEFF(공식) = Σ_d (w_d/Σw)·DEFF_d        ← 판 통계가 도메인 가중 평균이므로
실측:  DEFF = (SD_군집부트 / SD_행부트)²           ← `out899_dateclust.json`

산출물: `runners/out899_deffchk.json`. 입력을 **읽어서** 쓴다(손 전사 금지).
"""
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
DC = ROOT / "runners/out899_dateclust.json"
AX = ROOT / "runners/out899_axesdie.json"
OUT = ROOT / "runners/out899_deffchk.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def main():
    dc = json.loads(DC.read_text(encoding="utf-8"))
    ax = json.loads(AX.read_text(encoding="utf-8"))
    rel = ax["판 기여와의 관계(표·산점만 · 🔴 회귀선 없음 — 조항 60 · n=12)"]
    icc = dc["ICC · DEFF · n_eff"]

    rows, agg = {}, {}
    for lvl, key in (("일 군집", "잔차 ICC(일)"), ("월 군집", "잔차 ICC(월)")):
        s = 0.0
        for d, v in icc.items():
            a = v[key] if isinstance(v, dict) else None
            if not isinstance(a, dict):
                rows.setdefault(d, {})[lvl] = "잴 수 없다"
                continue
            w = rel[d]["판 가중 w/Σw"]
            # 🔴 공식을 **여기서 다시 대입한다** --- 산출물의 DEFF 를 그대로 믿지 않는다
            chk = 1 + (a["m̄(N/K)"] - 1) * a["ICC"]
            rows.setdefault(d, {})[lvl] = {
                "N": a["N"], "K": a["K"], "m̄": round(a["m̄(N/K)"], 4),
                "ICC": round(a["ICC"], 5),
                "DEFF(내가 다시 대입)": round(chk, 5),
                "DEFF(산출물)": round(a["DEFF(공식 · m̄)"], 5),
                "대입 일치": abs(chk - a["DEFF(공식 · m̄)"]) < 1e-9,
                "n_eff = N/DEFF": round(a["N"] / chk, 2),
                "w/Σw": w}
            s += w * chk
        agg[lvl] = round(s, 5)

    emp = dc["🔴 판 수준 실측 DEFF = (SD_군집/SD_행)²"]
    verdict = {}
    for lvl in ("일 군집", "월 군집"):
        e = emp[lvl]
        lo, hi = min(e.values()), max(e.values())
        f = agg[lvl]
        ratio = max(f / lo, hi / f) if lo > 0 else float("inf")
        verdict[lvl] = {
            "판 DEFF(공식 · 가중평균)": f,
            "판 DEFF(실측 · 통계 넷)": e,
            "실측 범위": [lo, hi],
            "공식 대 실측 최대 배수": round(ratio, 3),
            "🔴 사전등록 판정(2배 이상 갈리면 「모른다」)":
                "일치 — 검산 통과" if ratio < 2 else "🔴 모른다 — 공식과 실측이 2배 이상 갈린다"}

    res = {
        "노트": 899, "무엇": "DEFF 검산 — 공식 대입 대 부트 실측",
        "HEAD": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip(),
        "시각": dt.datetime.now().isoformat(timespec="seconds"),
        "코드 sha": {"runners/deffchk899.py": sha(__file__),
                     "runners/out899_dateclust.json": sha(DC),
                     "runners/out899_axesdie.json": sha(AX)},
        "공식": "DEFF = 1 + (m̄ − 1)·ICC · 판 DEFF = Σ (w/Σw)·DEFF_d · n_eff = N/DEFF",
        "도메인별": rows, "판 DEFF(공식)": agg, "검산": verdict,
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
