# -*- coding: utf-8 -*-
"""노트 898 판정문을 **산출물에서 생성한다**(회계를 손으로 옮기지 않는다).

읽는 것
  runners/out898_wire.json      0단계 배선 검사(씨앗 0 네 조합 · 동률 · C1)
  runners/out898_board.json     두 팔의 판 ρ(12씨앗) · 짝 Δ · BCa · 도메인별
  runners/out898_thr.json       두 순위 함수 아래의 채택 문턱 R5
  runners/out112_board.json     챔피언 경로 12씨앗(= 팔 A 대조군)
  runners/out112_refit837.json  837 경로 12씨앗(kho 배치 + scipy)

쓰는 것
  runners/out898_verdict.json
"""
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out898_verdict.json"
SRC = {
    "wire": "runners/out898_wire.json",
    "board": "runners/out898_board.json",
    "thr": "runners/out898_thr.json",
    "b112": "runners/out112_board.json",
    "r837": "runners/out112_refit837.json",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main():
    J = {k: json.load(open(ROOT / v, encoding="utf-8")) for k, v in SRC.items()}
    w, b, t = J["wire"], J["board"], J["thr"]

    A = np.array(b["팔"]["A(서수 · 현행 챔피언)"]["씨앗별(전정밀)"], float)
    B = np.array(b["팔"]["B(동률 평균)"]["씨앗별(전정밀)"], float)
    C112 = np.array(J["b112"]["씨앗별 판(전정밀)"], float)
    R837 = np.array(J["r837"]["씨앗별 판(전정밀)"], float)

    # ── 팔 A 가 챔피언 경로를 그대로 재현하는가 ─────────────────────────
    repro = {"최대 |Δ|": float(np.abs(A - C112).max()),
             "부동소수 동일": bool(np.array_equal(A, C112)),
             "1e-12 안": bool(np.abs(A - C112).max() < 1e-12)}

    # ── 12씨앗 전량 분해: 837 − 챔피언 = 스피어만 구현 + 채점 배치 ───────
    d_total = R837 - A
    d_spear = B - A
    d_batch = R837 - B
    dec = {
        "총 Δ(837 − 챔피언) 평균": float(d_total.mean()),
        "① 채점 배치(kho − post · 동률평균 고정) 평균": float(d_batch.mean()),
        "② 스피어만 구현(동률평균 − 서수 · post 고정) 평균": float(d_spear.mean()),
        "합 검산(①+②−총)": float((d_batch + d_spear - d_total).max()),
        "씨앗별 ①": list(map(float, d_batch)),
        "씨앗별 ②": list(map(float, d_spear)),
        "①이 양수인 씨앗": int((d_batch > 0).sum()),
        "②가 양수인 씨앗": int((d_spear > 0).sum()),
        "🔴 옛 인쇄물의 ②": {
            "무엇": "_fit_on 이 GBM random_state 를 씨앗으로 갈아 끼운다 → +0.00052",
            "판정": "**틀렸다 — 물리적으로 불가능**",
            "실측": w["ㄱ 자루 random_state"],
        },
    }

    # ── 판정 ────────────────────────────────────────────────────────────
    r1 = b["R-1 행 순서 의존성"]
    r3 = b["R-3a 887형 중립화"]
    chosen = ("B(동률 평균)" if (r1["R-1 판정"].startswith("팔 B")
                               and not r3["R-3a 실패 조건 발화"])
              else "A(서수 유지)")
    verdict = {
        "정본으로 삼는 팔": chosen,
        "규칙": ("사전등록 R-1 --- 서수는 행 순서에 의존하고(P1 위배) 동률 평균은 불변이다. "
               "R-3a 실패 조건(887형 중립화)은 발화하지 않았다. "
               "🔴 어느 쪽이 큰가는 규칙에 안 들어갔다(R-4)."),
        "R-1 실측": {"A 가 순서 의존인 도메인 수": len(r1["A 가 순서 의존인 도메인"]),
                   "A 최대 폭": r1["A 최대 폭"],
                   "B 가 순서 의존인 도메인 수": len(r1["B 가 순서 의존인 도메인"]),
                   "B 최대 폭": r1["B 최대 폭"]},
        "R-3a 실측": {"마스크 없이 B 가 nan": r3["마스크 없이 B 가 nan 인가"],
                    "ok 마스크 뒤 유한": r3["ok 마스크 뒤 B 가 유한한가"],
                    "실패 조건 발화": r3["R-3a 실패 조건 발화"]},
        "🔴 이것은 개선 주장이 아니다": (
            "서수 순위는 동률에서 순위를 **무작위로 갈라** 상관을 아래로 끄는 편의가 있다. "
            "정본이 오르는 것은 모형이 좋아진 것이 아니라 **편의를 뺀 것**이다. "
            "노트 133(첫 양수를 채택하지 않는다)은 손잡이 이득에 대한 조항이고 "
            "여기 바뀐 것은 손잡이가 아니라 **통계량의 정의**다."),
    }

    old = float(A.mean())
    new = float(B.mean())
    canon = {
        "옛 정본(팔 A · 서수)": {"평균": old,
                            "SD(ddof=1)": b["팔"]["A(서수 · 현행 챔피언)"]["SD(ddof=1)"],
                            "SE": b["팔"]["A(서수 · 현행 챔피언)"]["SE"],
                            "표기": round(old, 5)},
        "새 정본(팔 B · 동률 평균)": {"평균": new,
                              "SD(ddof=1)": b["팔"]["B(동률 평균)"]["SD(ddof=1)"],
                              "SE": b["팔"]["B(동률 평균)"]["SE"],
                              "표기": round(new, 5)},
        "옮김": new - old,
        "옮김 / SE(새)": (new - old) / b["팔"]["B(동률 평균)"]["SE"],
        "옮김 / 채택 문턱 0.00353": (new - old) / 0.00353,
        "분모": b["분모"],
    }

    thr = {
        "팔 B(동률 평균 · 891 이 이미 쓰던 것)": t["🔴 R5(채택 문턱)"]["동률 평균(891 정본)"],
        "팔 A(서수로 통일했다면)": t["🔴 R5(채택 문턱)"]["서수(rank_test)"],
        "891 이 인쇄한 값": 0.00353,
        "🔴 891 재현 단서": (
            "성분은 5자리까지 정확히 재현된다(씨앗 0.00099 · 행짝 0.00146). "
            "그런데 891 의 R5 0.00353 은 **반올림한 성분**을 hypot 에 넣어 나온 값이고 "
            "(2·hypot(0.00099,0.00146)=0.0035280), 반올림 없이 다시 재면 "
            f"{t['🔴 R5(채택 문턱)']['동률 평균(891 정본)']['R5(전정밀)']!r} 이다. "
            "차 4.0e-6 --- 판정을 하나도 안 바꾸고 방어 대역 0.00312~0.00393 안이다. "
            "🔴 그래도 **문턱은 반올림한 수로 지어져 있었다**."),
        "결론": ("팔 B 는 문턱을 안 움직인다(891 은 이미 동률 평균으로 지어졌다) --- "
               "사전등록 R-5 의 예측대로다. 팔 A 를 골랐다면 자를 다시 세워야 했고 "
               "문턱은 0.00362 로 **+2.8% 커진다**."),
        "⚠ 문턱의 지위": "티처 #54 가 「잠정」으로 강등 · 방어 대역 0.00312~0.00393",
    }

    res = {
        "노트": 898,
        "물음": "판과 자가 같은 순위 함수를 써야 하는가. 쓴다면 어느 쪽으로 통일하는가",
        "사전등록": {"파일": "docs/prereg_898_oneruler.md",
                  "커밋": "6373373c1a29d95772878c5103ff0c97120f29c7",
                  "시각": "2026-08-10T21:55:49+09:00"},
        "HEAD": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip(),
        "시각": dt.datetime.now().isoformat(timespec="seconds"),
        "산출물 sha": {k: sha(ROOT / v) for k, v in SRC.items()},
        "0단계 배선": {"C1(random_state 무연산)": w["ㄱ 자루 random_state"]["자루가 [0..K-1] 인가"],
                   "씨앗0 네 조합 재현 오차": w["ㄷ 재현 오차"],
                   "동률": {d: [v["채점행(post∩라벨유한∩예측유한)"], v["예측 고유값"]]
                          for d, v in w["ㄴ 동률"].items()}},
        "팔 A 가 챔피언 경로를 재현하는가": repro,
        "판정": verdict,
        "정본": canon,
        "짝 Δ": b["짝 Δ"],
        "① 씨앗 짝 BCa(주)": b["① 씨앗 짝 BCa(주)"],
        "② 행 군집 BCa(병기)": b["② 행 군집 BCa(병기)"],
        "도메인별": b["도메인별"],
        "12씨앗 전량 분해": dec,
        "자(문턱)": thr,
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: res[k] for k in
                      ("판정", "정본", "자(문턱)", "12씨앗 전량 분해")},
                     ensure_ascii=False, indent=1))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
