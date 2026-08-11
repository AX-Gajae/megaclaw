# -*- coding: utf-8 -*-
"""🔴 노트 905 — **「검산했다」를 산출물로 증명한다** (이슈 #153 C4 처방).

병: 904 가 *"본문이 인용한 수 **서른다섯**을 `quote901.py --check` 로 검산했고 어긋남 0"*
이라 적었는데 **그 검산 결과를 담은 산출물이 브랜치에 하나도 없었다.** 「서른다섯」도
어느 산출물에도 없는 수였고, 그 사이 논문은 **산출물에 없는 수 둘을 인용했고 둘 다 틀렸다**
— 즉 「어긋남 0」은 성립할 수 없는 주장이었다.

🔴 **`runners/quote901.py` 를 한 글자도 안 고친다.** 도구를 고치는 것은 수리 팔의 일이다.
이 러너는 그 도구를 **부르고 결과를 파일에 남긴다**.

산출물 `runners/out905_quotecheck.json` 이 담는 것:
  검산 대상 키 **전량** · 각 키의 **산출물 값** · **내가 적은 값** · **어긋남 수** ·
  🔴 **검정력(일부러 틀린 값을 넣어 도구가 실제로 붉어지는지)**.

🔴 논문·원장·PR 은 **이 산출물의 키를 병기한다. 손으로 옮겨 적지 않는다.**

실행: python3 runners/quotecheck905.py
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT / "runners"))

T0 = time.time()
START = dt.datetime.now().isoformat(timespec="seconds")

from inv901 import sha                                    # noqa: E402

TOOL = ROOT / "runners/quote901.py"
SRC = "runners/out905_cond.json"
OUT = ROOT / "runners/out905_quotecheck.json"

GA = "3-가 팔 ㄱ · 66짝은 식3 하나에서만 떨어지는가"
GB = "3-나 「모른다」는 무엇을 안 적어 뒀는가 (열 이름)"
GB2 = "3-나′ 🔴 사후 집계 — 「모른다」 안의 두 무리 (예측 아님)"
GC = "3-다 팔 ㄴ · 조건의 판정 단위는 짝인가 도메인인가"
W = "2 배선 검사"
P = "4 예측 판정"
L = "0-가 원장이 이미 뭐라 했나"

# 🔴 (내가 적을 값, 산출물, 키) — **논문·원장·PR 이 인용할 수 전량**
CITES: list[tuple[object, str, str]] = [
    # ── 팔 ㄱ
    (66,  SRC, f"{GA}/🔴 수(분모)"),
    (105, SRC, f"{GA}/짝 전량(분모)"),
    (54,  SRC, f"{GA}/🔴 식3 **하나만** 걸리는 짝 수"),
    (51,  SRC, f"{GA}/🔴 식3 하나만 걸리는 짝의 식3 라벨/모른다"),
    (3,   SRC, f"{GA}/🔴 식3 하나만 걸리는 짝의 식3 라벨/아니오"),
    (12,  SRC, f"{GA}/🔴 걸리는 조건이 둘 이상인 짝 수"),
    (0,   SRC, f"{GA}/🔴 넷 다 예인 짝 수(=A 가 됐어야 할 짝)"),
    (0,   SRC, f"{GA}/🔴 66 중 A 등급 수"),
    (21,  SRC, f"{GA}/A∧T1 수(분모)"),
    # ── 팔 ㄱ · 교차표 (아무도 안 센 수)
    (51,  SRC, f"{GA}/🔴 식1 × 식3 교차표(아무도 안 센 수)/표/식1=예 × 식3=모른다"),
    (3,   SRC, f"{GA}/🔴 식1 × 식3 교차표(아무도 안 센 수)/표/식1=예 × 식3=아니오"),
    (12,  SRC, f"{GA}/🔴 식1 × 식3 교차표(아무도 안 센 수)/표/식1=아니오 × 식3=모른다"),
    (66,  SRC, f"{GA}/🔴 식1 × 식3 교차표(아무도 안 센 수)/분모"),
    # ── 「모른다」가 무엇을 안 적어 뒀나
    (63,  SRC, f"{GB}/🔴 모른다 짝 수(분모)"),
    (0,   SRC, f"{GB}/🔴 어긋남(근거가 지목한 열 ≠ 짝 자신의 개입 열)"),
    (63,  SRC, f"{GB}/🔴 지시적 문형인 짝 수"),
    (10,  SRC, f"{GB}/🔴 그 이름의 가짓수"),
    (10,  SRC, f"{GB}/도메인 수(분모)"),
    (51,  SRC, f"{GB}/🔴 식1 통과분 안에서의 모른다 수"),
    (12,  SRC, f"{GB}/🔴 식1 미통과분 안에서의 모른다 수"),
    # ── 사후 집계 — 「모른다」 안의 두 무리
    (4,   SRC, f"{GB2}/무리 ㄱ · 도메인에 시점 필드가 하나도 없다(「없다」)/도메인 수"),
    (19,  SRC, f"{GB2}/무리 ㄱ · 도메인에 시점 필드가 하나도 없다(「없다」)/"
               "식3 하나만 걸리고 모른다 인 짝 수"),
    (6,   SRC, f"{GB2}/무리 ㄴ · 시점 필드는 있는데 개입 열을 안 덮는다(「안 적어 뒀다」)/도메인 수"),
    (32,  SRC, f"{GB2}/무리 ㄴ · 시점 필드는 있는데 개입 열을 안 덮는다(「안 적어 뒀다」)/"
               "식3 하나만 걸리고 모른다 인 짝 수"),
    (51,  SRC, f"{GB2}/🔴 합(분모 대조)"),
    # ── 팔 ㄴ
    (12,  SRC, f"{GC}/도메인 수(분모)"),
    (105, SRC, f"{GC}/짝 수(분모)"),
    (5,   SRC, f"{GC}/조건별/식1/🔴 도메인 안 상수인 도메인 수"),
    (12,  SRC, f"{GC}/조건별/식2/🔴 도메인 안 상수인 도메인 수"),
    (3,   SRC, f"{GC}/조건별/식3/🔴 도메인 안 상수인 도메인 수"),
    (12,  SRC, f"{GC}/조건별/식4/🔴 도메인 안 상수인 도메인 수"),
    (12,  SRC, f"{GC}/조건별/분모/🔴 도메인 안 상수인 도메인 수"),
    (12,  SRC, f"{GC}/조건별/식2/🔴 실효 자유도(도메인별 값 가짓수 합)"),
    (12,  SRC, f"{GC}/조건별/식4/🔴 실효 자유도(도메인별 값 가짓수 합)"),
    (19,  SRC, f"{GC}/조건별/식1/🔴 실효 자유도(도메인별 값 가짓수 합)"),
    (23,  SRC, f"{GC}/조건별/식3/🔴 실효 자유도(도메인별 값 가짓수 합)"),
    (0,   SRC, f"{GC}/조건별/형/🔴 도메인 안 상수인 도메인 수"),
    # ── 배선 검사
    (7,   SRC, f"{W}/🔴 분모(심은 결함 수)"),
    (7,   SRC, f"{W}/발화"),
    (7,   SRC, f"{W}/🔴 국소 시험 통과"),
    (7,   SRC, f"{W}/음성 대조 통과"),
    (7,   SRC, f"{W}/🔴 지우면 통과로 바뀐 수"),
    (7,   SRC, f"{W}/🔴 계수기가 늘어난 수"),
    # 🔴 `quote901` 은 JSON 불리언을 `true` 로 찍는다 — 파이썬 `True` 로 적으면 어긋난다.
    #    실측으로 확인하고 도구의 표기에 맞췄다(도구를 고치지 않았다)
    ("true", SRC, f"{W}/통과"),
    # ── 예측 · §0 장치
    (4,   SRC, f"{P}/🔴 예측 수(분모)"),
    (3,   SRC, f"{P}/🔴 확인"),
    (0,   SRC, "0-나 §0 대 예측 교집합 (이슈 #152 처방 · 기계로 센다)/🔴 교집합 수"),
    # ── 원장
    (894, SRC, f"{L}/원장 최상위 항목(분모)"),
    (80,  SRC, f"{L}/🔴 합집합(이 물음에 걸리는 옛 항목 수)"),
    (15,  SRC, f"{L}/🔴 좁은 바늘(식3·역인과·관측 시점) 합집합 수"),
    # ── 스탬프
    ("9a8d42a04639265abfbd6cf1e0cec81538052a58", SRC, "사전등록/커밋"),
    ("2026-08-11T08:22:38+09:00", SRC, "사전등록/커밋 시각"),
]

# 🔴 검정력 — 일부러 틀린 값. 도구가 **붉어져야 한다**(종료 6). 어긋남 계수에 안 넣는다
POWER: list[tuple[object, str, str]] = [
    (65, SRC, f"{GA}/🔴 식3 **하나만** 걸리는 짝 수"),          # 참값 54
    (1,  SRC, f"{GC}/조건별/식2/🔴 도메인 안 상수인 도메인 수"),  # 참값 12
    (9,  SRC, f"{W}/🔴 국소 시험 통과"),                        # 참값 7
]

# 🔴 조항 59 — 「그 키가 없다」가 종료 4 로 죽는지도 확인한다(빈 값·0 이 아니다)
NOKEY: list[tuple[object, str, str]] = [
    (1, SRC, f"{GA}/🔴 있지도 않은 키"),
]


def run(val, path, key) -> dict:
    r = subprocess.run([sys.executable, str(TOOL), "--check", str(val), path, key],
                       capture_output=True, text=True, cwd=str(ROOT))
    got = subprocess.run([sys.executable, str(TOOL), path, key],
                         capture_output=True, text=True, cwd=str(ROOT))
    return {"키": key, "산출물": path, "내가 적은 값": val,
            "산출물 값": got.stdout.strip() if got.returncode == 0 else None,
            "값 읽기 종료 코드": got.returncode,
            "--check 종료 코드": r.returncode,
            "어긋났나": r.returncode != 0,
            "메시지": (r.stderr or r.stdout).strip()[:200] if r.returncode else ""}


def main():
    rows = [run(*c) for c in CITES]
    pw = [run(*c) for c in POWER]
    nk = [run(*c) for c in NOKEY]
    bad = [x for x in rows if x["어긋났나"]]
    out = {
        "노트": 905,
        "🔴 무엇인가": ("논문·원장·PR 이 인용할 수 전량을 `runners/quote901.py --check` 로 "
                   "검산한 **산출물**이다. 이슈 #153 C4 의 처방 — 「검산했다」는 "
                   "손으로 적는 문장이 아니라 파일이어야 한다"),
        "시작 시각": START,
        "코드 sha256": {"runners/quotecheck905.py": sha(Path(__file__)),
                     "runners/quote901.py": sha(TOOL)},
        "입력 sha256": {SRC: sha(ROOT / SRC)},
        "🔴 도구를 안 고쳤다": "quote901.py 를 한 글자도 안 고쳤다 — 부르기만 했다",
        "🔴 검산 대상 키 수(분모)": len(rows),
        "🔴 어긋남 수": len(bad),
        "어긋난 것": bad,
        "검산 전량": rows,
        "🔴 검정력(일부러 틀린 값을 넣었다)": {
            "심은 수(분모)": len(pw),
            "🔴 도구가 붉어진 수(종료 6)": sum(1 for x in pw if x["--check 종료 코드"] == 6),
            "전량": pw},
        "🔴 조항 59 — 없는 키는 종료 4 로 죽는가": {
            "심은 수(분모)": len(nk),
            "🔴 종료 4 로 죽은 수": sum(1 for x in nk if x["--check 종료 코드"] == 4),
            "전량": nk},
    }
    out["통과"] = bool(
        len(bad) == 0
        and out["🔴 검정력(일부러 틀린 값을 넣었다)"]["🔴 도구가 붉어진 수(종료 6)"] == len(pw)
        and out["🔴 조항 59 — 없는 키는 종료 4 로 죽는가"]["🔴 종료 4 로 죽은 수"] == len(nk))
    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["초"] = round(time.time() - T0, 3)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("완료 →", OUT)
    print("검산", len(rows), "· 어긋남", len(bad),
          "· 검정력", out["🔴 검정력(일부러 틀린 값을 넣었다)"]["🔴 도구가 붉어진 수(종료 6)"],
          "/", len(pw), "· 통과", out["통과"])
    if bad:
        for b in bad:
            print("  🔴", b["키"], "적은", b["내가 적은 값"], "산출물", b["산출물 값"])


if __name__ == "__main__":
    main()
