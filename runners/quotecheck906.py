# -*- coding: utf-8 -*-
"""🔴 노트 906 — **「검산했다」를 산출물로 증명한다** (이슈 #153 C4 처방 · 905 의 꼴을 물려받는다).

🔴 **`runners/quote901.py` 를 한 글자도 안 고친다.** 부르고 결과를 파일에 남긴다.

산출물 `runners/out906_quotecheck.json` 이 담는 것:
  검산 대상 키 **전량** · 각 키의 **산출물 값** · **내가 적은 값** · **어긋남 수** ·
  🔴 **검정력**(일부러 틀린 값을 넣어 도구가 실제로 붉어지는지) ·
  🔴 **조항 59**(없는 키가 종료 4 로 죽는가) ·
  🔴🔴 **한글 수사 검사** — 티처 #68 C4 가 잡은 **다섯 번째 얼굴**. `quotecheck` 은
  「여덟」·「넷」 같은 한글 수사를 **원리상 못 잡는다.** 그래서 이 러너가 **논문·원장·PR 원문을
  읽어 한글 수사가 수를 세는 자리에 쓰였는지 직접 훑는다.**

실행: python3 runners/quotecheck906.py
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT / "runners"))

import time                                               # noqa: E402

T0 = time.time()
START = dt.datetime.now().isoformat(timespec="seconds")

from inv901 import sha                                    # noqa: E402

TOOL = ROOT / "runners/quote901.py"
SRC = "runners/out906_grade.json"
OUT = ROOT / "runners/out906_quotecheck.json"

GA = "3-가 팔 ㄱ · 등급은 무엇의 함수인가 (예측 아님 · §0 에서 이미 돌렸다)"
GB = "3-나 팔 ㄱ · 복잡도를 통제한 재현 (재대입 · LODO · 암기 상한)"
GC = "3-다 팔 ㄴ · 「등급 미사용」 형제 키가 등급을 복제하는가"
W = "2 배선 검사"
P = "4 예측 판정 (🔴 예측마다 반증 입력을 심었다 — 이슈 #155 처방 1)"
L = "0-다 원장이 이미 뭐라 했나"
D = "1 분모 (조항 60 — 매 수마다 병기한다)"
K = "0-가 🔴 입력 산출물 최상위 키 전량 (티처 #68 ⑧ — 러너 절 1/2)"
Z = "0-나 🔴 오늘 낼 판정문의 수를 입력에서 되찾기 (티처 #68 ⑧ — 러너 절 2/2)"

# 🔴 (내가 적을 값, 산출물, 키) — 논문·원장·PR·커밋이 인용할 수 **전량**
CITES: list[tuple[object, str, str]] = [
    # ── 분모
    (81, SRC, f"{D}/T1 수(분모)"),
    (24, SRC, f"{D}/T2 수(분모 · 따로 센다)"),
    (105, SRC, f"{D}/T1+T2(참고)"),
    (12, SRC, f"{D}/도메인 수(분모)"),
    (21, SRC, f"{D}/T1 등급 분포/A"),
    (47, SRC, f"{D}/T1 등급 분포/B"),
    (13, SRC, f"{D}/T1 등급 분포/C"),
    # ── 팔 ㄱ · 이미 아는 것(예측 아님)
    (0, SRC, f"{GA}/🔴 식1 ≡ (소수 쪽 ≥ 10) 어긋남"),
    (105, SRC, f"{GA}/🔴 식1 ≡ (소수 쪽 ≥ 10) 분모"),
    (5, SRC, f"{GA}/🔴 칸 수"),
    (23, SRC, f"{GA}/🔴 등급 = f(식1, 식3) 의 칸/식1=예 × 식3=예 → A"),
    (64, SRC, f"{GA}/🔴 등급 = f(식1, 식3) 의 칸/식1=예 × 식3=모른다 → B"),
    (13, SRC, f"{GA}/🔴 등급 = f(식1, 식3) 의 칸/식1=아니오 × 식3=모른다 → C"),
    (3, SRC, f"{GA}/🔴 등급 = f(식1, 식3) 의 칸/식1=예 × 식3=아니오 → C"),
    (2, SRC, f"{GA}/🔴 등급 = f(식1, 식3) 의 칸/식1=아니오 × 식3=예 → B"),
    # ── 팔 ㄱ · 비트
    (1.3842, SRC, f"{GA}/엔트로피 · T1 81/H(등급)"),
    (0.9406, SRC, f"{GA}/엔트로피 · T2 24/H(등급)"),
    (81, SRC, f"{GA}/엔트로피 · T1 81/🔴 5-튜플 암기/🔴 서로 다른 튜플 수"),
    (1.0, SRC, f"{GA}/엔트로피 · T1 81/🔴 5-튜플 암기/🔴 유일 비율"),
    (0, SRC, f"{GA}/엔트로피 · T1 81/🔴 5-튜플 암기/🔴 암기 재대입 오류"),
    (0.3328, SRC, f"{GA}/엔트로피 · T1 81/H(등급 | 소수 쪽 ≥ 10)/🔴 상호정보(비트)"),
    (0.5532, SRC, f"{GA}/엔트로피 · T1 81/H(등급 | 소수 쪽 ≥ 10, 형=d)/🔴 상호정보(비트)"),
    (0.4121, SRC, f"{GA}/엔트로피 · T1 81/H(등급 | 도메인)/🔴 상호정보(비트)"),
    (0.0, SRC, f"{GA}/엔트로피 · T1 81/H(등급 | 다섯 통계 전부)/조건부 엔트로피 H(등급|특징)"),
    # ── 팔 ㄱ · 복잡도 사다리
    (0, SRC, f"{GB}/F5 다섯 통계(전부)/🔴 최소 재대입 오류"),
    (22, SRC, f"{GB}/F5 다섯 통계(전부)/🔴 최소 LODO 오류"),
    (0, SRC, f"{GB}/F4 도메인 뺀 넷/🔴 최소 재대입 오류"),
    (22, SRC, f"{GB}/F4 도메인 뺀 넷/🔴 최소 LODO 오류"),
    (7, SRC, f"{GB}/F3 소수 쪽 뺀 넷(음성 대조)/🔴 최소 재대입 오류"),
    (25, SRC, f"{GB}/F3 소수 쪽 뺀 넷(음성 대조)/🔴 최소 LODO 오류"),
    (7, SRC, f"{GB}/F4 도메인 뺀 넷/깊이별/깊이 3/재대입 오류"),
    (1.0221, SRC, f"{GB}/🔴 잔여 비트(= H(등급 | LODO 예측))"),
    (0.362, SRC, f"{GB}/🔴 일반화 기준 상호정보(비트)"),
    (22, SRC, f"{GB}/🔴 잔여를 지는 짝 수"),
    (15, SRC, f"{GB}/🔴 잔여 짝의 도메인 분해/팝업"),
    (14, SRC, f"{GB}/🔴 잔여 짝의 식3 분해/예"),
    (8, SRC, f"{GB}/🔴 잔여 짝의 식3 분해/모른다"),
    (3, SRC, f"{GB}/🔴 잔여 짝의 식3 분해/아니오"),
    (12, SRC, f"{GB}/🔴 최소 LODO 규칙의 상세/접기 수(도메인)"),
    (81, SRC, f"{GB}/🔴 최소 LODO 규칙의 상세/채점된 짝"),
    # ── 팔 ㄴ
    (1.3842, SRC, f"{GC}/🔴 주 — 범주형 인코딩/🔴 상호정보(비트)"),
    (0.0, SRC, f"{GC}/🔴 주 — 범주형 인코딩/조건부 엔트로피 H(등급|특징)"),
    (36, SRC, f"{GC}/🔴 주 — 범주형 인코딩/특징 값 가짓수"),
    (1.3842, SRC, f"{GC}/W 코드 집합만/🔴 상호정보(비트)"),
    (5, SRC, f"{GC}/W 코드 집합만/특징 값 가짓수"),
    (5, SRC, f"{GC}/🔴 대응이 일대일인가/W 코드 집합 가짓수(분모)"),
    (0, SRC, f"{GC}/🔴 대응이 일대일인가/등급이 두 가지 이상 섞인 W 코드 집합 수"),
    (21, SRC, f"{GC}/🔴 W 코드 집합 → 등급 대응표(T1 81)/('W2', 'W8')/A"),
    (45, SRC, f"{GC}/🔴 W 코드 집합 → 등급 대응표(T1 81)/('W2', 'W4', 'W8')/B"),
    (10, SRC, f"{GC}/🔴 W 코드 집합 → 등급 대응표(T1 81)/('W2', 'W4', 'W6', 'W8')/C"),
    (0.6921, SRC, f"{GC}/🔴 절반 문턱(H/2)"),
    # ── 배선 검사
    (11, SRC, f"{W}/🔴 분모(심은 결함 수)"),
    (11, SRC, f"{W}/발화"),
    (11, SRC, f"{W}/🔴 국소 시험 통과"),
    (11, SRC, f"{W}/음성 대조 통과"),
    (11, SRC, f"{W}/🔴 지우면 통과로 바뀐 수"),
    (11, SRC, f"{W}/🔴 계수기가 늘어난 수"),
    (8, SRC, f"{W}/🔴 ㉱ 국소 열 검정력을 잰 검사 수(분모)"),
    (8, SRC, f"{W}/🔴 ㉱ 국소 열 검정력 > 0 인 검사 수"),
    ("true", SRC, f"{W}/통과"),
    # ── 예측 장치
    (4, SRC, f"{P}/🔴 심은 반증 입력 수(분모)"),
    (3, SRC, f"{P}/🔴 반증 가능한 것으로 확인된 수"),
    (3, SRC, f"{P}/🔴 명부에 남은 예측 수"),
    (2, SRC, f"{P}/🔴 그중 확인"),
    (1, SRC, f"{P}/🔴 그중 반증"),
    # ── §3-기계 (티처 #68 ⑧)
    (30, SRC, f"{K}/runners/out902_identify.json/최상위 키 수"),
    (9, SRC, f"{Z}/판정문에서 뽑은 정수 가짓수(분모)"),
    (3, SRC, f"{Z}/🔴 입력에서 못 찾은 수의 개수"),
    (6, SRC, f"{Z}/🔴 입력에 이미 있는 수의 개수"),
    # ── 원장 훑기
    (899, SRC, f"{L}/원장 최상위 항목(분모)"),
    (339, SRC, f"{L}/🔴 합집합(이 물음에 걸리는 옛 항목 수)"),
    (38, SRC, f"{L}/🔴 좁은 바늘(비트·엔트로피·재명명) 합집합 수"),
    (0.726, SRC, f"{L}/🔴 제일 넓은 바늘이 합집합에서 차지하는 비율"),
    # ── 스탬프
    ("d286a260c88b775f8b3a3460b892d05479ed90c5", SRC, "사전등록/커밋"),
    ("2026-08-11T09:30:17+09:00", SRC, "사전등록/커밋 시각"),
]

# 🔴 2차 — **이 러너 자신의 산출물**에 대한 검산(논문 meta 가 그 키를 인용한다).
#    자기 참조라 **한 번 더 돌려야** 값이 채워진다: 러너가 두 번 돌면 두 번째가 참이다
SRC2 = "runners/out906_quotecheck.json"
HK = "🔴🔴 한글 수사 훑기 (티처 #68 C4)"
CITES2: list[tuple[object, str, str]] = [
    (0, SRC2, f"{HK}/🔴 걸린 자리 합"),
    (0, SRC2, f"{HK}/🔴 못 읽은 파일 수"),
    (3, SRC2, f"{HK}/🔴 훑기의 검정력(심어서 확인)/🔴 잡은 수"),
    (0, SRC2, f"{HK}/🔴 훑기의 검정력(심어서 확인)/🔴 음성 대조에서 잘못 잡은 수"),
    (0, SRC2, f"{HK}/🔴 훑기의 검정력(심어서 확인)/🔴🔴 이 자가 원리상 못 잡는 것(사각지대 · 심어서 확인)/🔴 잡은 수"),
    (2, SRC2, f"{HK}/🔴 훑기의 검정력(심어서 확인)/🔴🔴 이 자가 원리상 못 잡는 것(사각지대 · 심어서 확인)/심은 문장(분모)"),
    (42, SRC2, f"{HK}/🔴 넓은 훑기(신고용 · 통과 조건 아님)/🔴 걸린 자리 합"),
    (3, SRC2, "🔴 검정력(일부러 틀린 값을 넣었다)/🔴 도구가 붉어진 수(종료 6)"),
    (1, SRC2, "🔴 조항 59 — 없는 키는 종료 4 로 죽는가/🔴 종료 4 로 죽은 수"),
]

# 🔴 검정력 — 일부러 틀린 값. 도구가 **붉어져야 한다**(종료 6)
POWER: list[tuple[object, str, str]] = [
    (21, SRC, f"{GB}/🔴 잔여를 지는 짝 수"),                 # 참값 22
    (1.3843, SRC, f"{GA}/엔트로피 · T1 81/H(등급)"),          # 참값 1.3842
    (6, SRC, f"{GC}/🔴 대응이 일대일인가/W 코드 집합 가짓수(분모)"),  # 참값 5
]

# 🔴 조항 59 — 「그 키가 없다」가 종료 4 로 죽는지
NOKEY: list[tuple[object, str, str]] = [
    (1, SRC, f"{GA}/🔴 있지도 않은 키"),
]

# 🔴🔴 한글 수사 검사 (티처 #68 C4 — 다섯 번째 얼굴)
#     병의 정확한 꼴: **재어서 나온 수**를 한글 수사로 적으면 `quote901 --check` 이
#     원리상 못 잡는다(「904 는 넷」). 그래서 **수사 + 세는 단위**가 붙은 자리만 잡는다 —
#     「다섯 서술 통계」처럼 **집합의 이름**인 자리는 재어서 나온 수가 아니다.
#     🔴 두 목록을 다 산출물에 싣는다(손 목록이라 감추지 않는다).
NUMERAL = ["하나", "한", "둘", "두", "셋", "세", "넷", "네", "다섯", "여섯", "일곱",
           "여덟", "아홉", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔",
           "여든", "아흔", "온", "백"]
COUNTER = ["짝", "도메인", "개", "곳", "건", "가지", "자리", "사이클", "비트", "절",
           "키", "칸", "번", "벌", "줄", "군데", "가짓수", "사례", "항목", "노트"]
PROSE = ["paper/steps/491_gradebits/main.tex",
         "paper/steps/491_gradebits/meta.json"]


def _delatex(t: str) -> str:
    # 🔴 `\texttt{...}` 는 **산출물 키 경로**다 — 주장이 아니라 **가리킴**이고
    #    그 안의 수는 이미 `CITES` 로 기계 검산된다. 그래서 훑기에서 뺀다
    t = re.sub(r"\\texttt\{[^{}]*\}", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\s*", " ", t)
    t = re.sub(r"[{}$~\\_^%&#]", " ", t)
    return re.sub(r"\s+", " ", t)


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


def _hangul_power(pat) -> dict:
    """🔴 「걸린 자리 0」이 공짜가 아님을 보인다 — 심은 문장에서 실제로 붉어지는지 잰다.

    조항 59 — 「안 걸렸다」와 「못 잡는다」는 둘이다.
    🔴 그리고 **이 자가 원리상 못 잡는 것**을 같이 심어 못 잡는다는 사실을 산출물에 박는다.
    """
    planted = ["이 사이클의 팔은 두 개다", "잔여를 지는 짝은 스물 두 짝이다",
               "원장 훑기는 세 곳 을 찾았다"]
    clean = ["이 사이클의 팔은 2개다", "잔여를 지는 짝은 22짝이다",
             "원장 훑기는 3곳을 찾았다"]
    blind = ["원장 훑기는 904 에서 넷 을 찾았다",
             "직전 노트가 찾은 것은 여덟 이었다"]
    hit = [t for t in planted if pat.search(_delatex(t))]
    fp = [t for t in clean if pat.search(_delatex(t))]
    bhit = [t for t in blind if pat.search(_delatex(t))]
    return {
        "심은 문장(분모)": len(planted), "🔴 잡은 수": len(hit),
        "심은 문장 전량": planted, "잡은 것": hit,
        "음성 대조 문장(분모)": len(clean), "🔴 음성 대조에서 잘못 잡은 수": len(fp),
        "잘못 잡은 것": fp,
        "🔴🔴 이 자가 원리상 못 잡는 것(사각지대 · 심어서 확인)": {
            "심은 문장(분모)": len(blind), "🔴 잡은 수": len(bhit), "전량": blind,
            "🔴 뜻": ("**단위 없는 수사**(「904 는 넷」·「여덟」)는 이 자로 못 잡는다 — "
                   "티처 #68 C4 의 **원래 사례가 바로 이 꼴**이다. "
                   "🔴 좁은 자는 「수사+단위」만 막고, 단위 없는 쪽은 아래 "
                   "`넓은 훑기(신고용)` 가 **목록으로만** 드러낸다. "
                   "「막았다」가 아니라 **「여기까지 막았다」**로 적는다(조항 59)")},
        "통과": len(hit) == len(planted) and not fp,
    }


def _broad_scan() -> dict:
    """🔴 신고용 — **단위 없는 한글 수사**를 전량 목록으로 낸다. 통과 조건이 아니다."""
    pat = re.compile(r"(?<![가-힣])(" + "|".join(map(re.escape, NUMERAL)) + r")(?![가-힣])")
    per, tot = {}, 0
    for rel in PROSE:
        f = ROOT / rel
        if not f.exists():
            per[rel] = {"🔴": "그 파일이 없다"}
            continue
        txt = _delatex(f.read_text(encoding="utf-8"))
        found = [{"수사": m.group(0),
                  "앞뒤": txt[max(0, m.start() - 12):m.end() + 12]}
                 for m in pat.finditer(txt)]
        per[rel] = {"걸린 수": len(found), "전량": found}
        tot += len(found)
    return {"🔴 이것은 통과 조건이 아니다": ("좁은 자가 못 잡는 자리를 **사람이 볼 수 있게** 낸다. "
                              "여기 실린 것을 전부 숫자로 고치라는 뜻이 아니다 — "
                              "**재어서 나온 수인지 사람이 판정할 목록**이다"),
            "🔴 걸린 자리 합": tot, "파일별": per}


def hangul_scan() -> dict:
    """🔴 원문을 훑어 **한글 수사 + 세는 단위**가 붙은 자리를 센다.

    🔴 면제는 하나뿐이다 — 그 자리가 **사전등록 §6 판정문 원문에 그대로 있을 때.**
    판정문은 측정 전에 얼어붙은 어법이라 이 사이클이 못 고친다. **면제도 기계로 판정한다.**
    """
    src = json.loads((ROOT / SRC).read_text())
    verdict = _delatex(src["5 판정"]["팔 ㄱ 판정문"] + " " + src["5 판정"]["팔 ㄴ 판정문"])
    # 🔴 앞에 한글 음절이 오면 수사가 아니다(「선언한 칸」의 `한`) — 뒤보기로 막는다
    # 🔴 뒤에 「째」(서수) 나 「도」(「한 번도 …않는다」 꼴 부정 관용구)가 오면 재어서 나온 수가 아니다
    pat = re.compile(r"(?<![가-힣])(" + "|".join(map(re.escape, NUMERAL)) + r")\s*("
                     + "|".join(map(re.escape, COUNTER)) + r")(?![째도])")
    per, tot, exempt, missing = {}, 0, 0, []
    for rel in PROSE:
        p = ROOT / rel
        if not p.exists():
            per[rel] = {"🔴": "그 파일이 없다(「한글 수사가 없다」가 아니다 — 조항 59)"}
            missing.append(rel)
            continue
        txt = _delatex(p.read_text(encoding="utf-8"))
        found, ex = [], []
        for m in pat.finditer(txt):
            seg = txt[max(0, m.start() - 10):m.end() + 10]
            item = {"수사+단위": m.group(0), "앞뒤": seg}
            if m.group(0) in verdict:
                ex.append(item)
            else:
                found.append(item)
        per[rel] = {"걸린 수": len(found), "전량": found,
                    "🔴 사전등록 §6 판정문이라 면제된 수": len(ex), "면제 전량": ex}
        tot += len(found)
        exempt += len(ex)
    return {
        "🔴 무엇인가": ("티처 #68 C4 — 「904 는 넷」이 한글 수사라 `quote901 --check` 이 "
                   "**원리상 못 잡았다**. 그 사각지대를 **원문 훑기**로 막는다. "
                   "🔴 잡는 꼴은 **수사 + 세는 단위**다 — 「다섯 서술 통계」처럼 "
                   "집합의 이름인 자리는 재어서 나온 수가 아니다"),
        "훑은 파일(분모)": len(PROSE),
        "🔴 수사 목록(분모)": NUMERAL, "🔴 세는 단위 목록(분모)": COUNTER,
        "🔴 면제 규칙": ("① 사전등록 §6 판정문 원문에 그 문자열이 그대로 있을 때(측정 전에 얼어붙은 어법) "
                 "② `\\texttt{}` 안(=산출물 키 경로 · 이미 CITES 로 검산된다) "
                 "③ 앞에 한글 음절이 붙은 것(「선언한 칸」의 `한`) "
                 "④ 뒤에 「째」(서수)나 「도」(「한 번도 …않는다」 꼴 부정)가 붙은 것. 넷 다 기계로 판정한다"),
        "🔴 걸린 자리 합": tot, "🔴 면제된 자리 합": exempt, "파일별": per,
        "🔴 훑기의 검정력(심어서 확인)": _hangul_power(pat),
        "🔴 넓은 훑기(신고용 · 통과 조건 아님)": _broad_scan(),
        "🔴 못 읽은 파일(=「없다」가 아니다 · 조항 59)": missing or "없다(전량 읽었다)",
        "🔴 못 읽은 파일 수": len(missing),
        "통과": (tot == 0 and not missing),
    }


def main():
    rows = [run(*c) for c in CITES]
    rows2 = [run(*c) for c in CITES2] if (ROOT / SRC2).exists() else []
    rows = rows + rows2
    pw = [run(*c) for c in POWER]
    nk = [run(*c) for c in NOKEY]
    hg = hangul_scan()
    bad = [x for x in rows if x["어긋났나"]]
    out = {
        "노트": 906,
        "🔴 무엇인가": ("논문·원장·PR·커밋이 인용할 수 전량을 `runners/quote901.py --check` 로 "
                   "검산한 **산출물**이다(이슈 #153 C4). "
                   "🔴 그리고 **한글 수사 훑기**를 더했다(티처 #68 C4 — 다섯 번째 얼굴)"),
        "시작 시각": START,
        "코드 sha256": {"runners/quotecheck906.py": sha(Path(__file__)),
                     "runners/quote901.py": sha(TOOL)},
        "입력 sha256": {SRC: sha(ROOT / SRC)},
        "🔴 도구를 안 고쳤다": "quote901.py 를 한 글자도 안 고쳤다 — 부르기만 했다",
        "🔴 검산 대상 키 수(분모)": len(rows),
        "🔴 그중 자기 산출물(2차 · 자기 참조라 두 번째 실행부터 참이다)": len(rows2),
        "🔴 자기 참조라 검산 목록에서 뺀 키": ["🔴 검산 대상 키 수(분모)", "🔴 어긋남 수"],
        "🔴 왜 뺐나": ("이 둘은 **자기 자신을 세는 키**라 값을 적는 순간 값이 바뀐다(고정점이 없다). "
                 "그래서 검산 목록에 안 넣고 **읽는 쪽이 파일을 직접 보게** 한다 — "
                 "🔴 「검산했다」가 아니라 「이 둘은 검산 대상이 아니다」로 적는다(조항 59)"),
        "🔴 어긋남 수": len(bad),
        "어긋난 것": bad,
        "검산 전량": rows,
        "🔴 검정력(일부러 틀린 값을 넣었다)": {
            "심은 수(분모)": len(pw),
            "🔴 도구가 붉어진 수(종료 6)": sum(1 for x in pw if x["--check 종료 코드"] == 6),
            "전량": pw,
            "통과": sum(1 for x in pw if x["--check 종료 코드"] == 6) == len(pw),
            "⚠ 통과의 뜻": "심은 틀린 값을 도구가 **전부** 종료 6 으로 잡았나(검정력 0 이면 검산이 공짜다)"},
        "🔴 조항 59 — 없는 키는 종료 4 로 죽는가": {
            "심은 수(분모)": len(nk),
            "🔴 종료 4 로 죽은 수": sum(1 for x in nk if x["--check 종료 코드"] == 4),
            "전량": nk,
            "통과": sum(1 for x in nk if x["--check 종료 코드"] == 4) == len(nk),
            "⚠ 통과의 뜻": "없는 키가 **종료 4** 로 죽나. 빈 값이나 0 을 찍고 종료 0 이면 조항 59 위반이다"},
        "🔴🔴 한글 수사 훑기 (티처 #68 C4)": hg,
    }
    out["통과"] = bool(
        len(bad) == 0
        and out["🔴 검정력(일부러 틀린 값을 넣었다)"]["🔴 도구가 붉어진 수(종료 6)"] == len(pw)
        and out["🔴 조항 59 — 없는 키는 종료 4 로 죽는가"]["🔴 종료 4 로 죽은 수"] == len(nk)
        and hg["통과"] and hg["🔴 훑기의 검정력(심어서 확인)"]["통과"])
    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["초"] = round(time.time() - T0, 3)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("완료 →", OUT)
    print("검산", len(rows), "· 어긋남", len(bad),
          "· 검정력", out["🔴 검정력(일부러 틀린 값을 넣었다)"]["🔴 도구가 붉어진 수(종료 6)"],
          "/", len(pw), "· 한글 수사", hg.get("🔴 걸린 자리 합"), "· 통과", out["통과"])
    for b in bad:
        print("  🔴", b["키"], "적은", b["내가 적은 값"], "산출물", b["산출물 값"])
    for rel, v in hg.get("파일별", {}).items():
        if isinstance(v, dict) and v.get("걸린 수"):
            for f in v["전량"]:
                print("  🔴 한글수사", rel, f["수사+단위"], "|", f["앞뒤"])
    if hg.get("🔴 못 읽은 파일 수"):
        print("  🔴 못 읽은 파일", hg["🔴 못 읽은 파일(=「없다」가 아니다 · 조항 59)"])


if __name__ == "__main__":
    main()
