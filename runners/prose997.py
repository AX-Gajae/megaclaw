# -*- coding: utf-8 -*-
"""🔴 노트 997 의 **산문 주장 = 산출물 키** 등록부 (`⑤′` 절 8).

🔴🔴🔴 **`CLAIMS` 를 손으로 안 적는다.** 아래 `REG` 는 «키 경로»만 적고, 문장은
`docs/판정_997.md` 에서 **그 값이 실제로 앉은 줄**을 기계로 찾아 쓴다.
곧 「표를 고치고 문서를 안 다시 찍은」 자리가 있으면 그 슬롯이 «빈 문장»으로 등록돼 떨어진다.

🔴 **한계(조항 61)**: 등록한 주장만 본다. 「전부 초록」은 「문서에 거짓이 없다」가 «아니다».
"""
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
DOC = "docs/판정_997.md"
ART = "runners/out997_score.json"

S1 = "①🔴🔴🔴 `MDE` 표 --- 997 의 «유일한 필수 산출»"
S2 = "②🔴🔴 915 는 «못 잴 자»로 갔다 --- 설정 전량에서"
S3 = "③🔴🔴 순열 자의 «역단조» --- 효과가 클수록 힘을 잃는다"
S4 = "④🔴🔴 「사이 칸」의 정체 --- 한 도메인인가. 🔴 두 분모를 «나란히»"
S5 = "⑤🔴 조각 분해표(조항 79) --- 사다리 셋"
S6 = "⑥🔴 `cluster_se` 칸 «전량»(조항 79 개정 2)"
S7 = "⑦🔴 다중비교 --- 가족 `FC-997`"
S8 = "⑧🔴 조항 78 계수(기계 · 손 라벨 «아님»)"
S9 = "⑨🔴 예측 채점 `P01`~`P18`"
SA = "⑩🔴 반증조건 채점 `F01`~`F17`"
K2 = "🔴🔴 두 분모를 나란히 --- 해석식 `MDE_a`"
KS = "㉡ 스텝 사다리(0 → 750 → 1500 → 3000)"
KK = "㉠ k 사다리(8 → 16 → 32 → 64 → 128 · 🔴 공통 분모 도메인 고정)"

REG = [
    [S1, "🔴 분모: 잰 설정"],
    [S1, "🔴🔴 `ρ 0.10` 아래인 설정 수"],
    [S1, "🔴🔴 「사이 칸」 설정 수"],
    [S1, "🔴 `ρ 0.30` 이상인 설정 수"],
    [S1, "🔴 배수 ㉠전량/㉡"],
    [S2, "🔴 915 의 차(0.1719 SSL − 0.1708 라벨순열 바닥)"],
    [S2, "🔴 915 가 실제로 선 자리(`k=16`)의 배수"],
    [S2, "🔴🔴 915 와 «같은 종류»의 자(㉠ 라벨 프로브) 안에서 가장 유리한 배수"],
    [S2, "🔴 가장 «유리한» 설정에서도 몇 배인가"],
    [S3, "🔴 δ=0 의 기각률(= 1종 오류) · ㉠ 전량"],
    [S3, "🔴 δ=0 의 기각률(= 1종 오류) · ㉡"],
    [S3, "🔴🔴 마지막 격자점(δ=0.80)의 힘 · ㉠ 전량"],
    [S3, "🔴🔴 `MDE` 를 낸 설정 수(순열 검정 단독)"],
    [S3, "🔴🔴 연언(㉠∧㉡)이 `MDE` 를 낸 설정 수"],
    [S3, "🔴🔴🔴 헤드라인 대비 ㉡ 의 순열 `p`(조항 79 개정 3 이 요구한 칸)"],
    [S3, "🔴🔴 그런데 같은 대비의 `t_clu`"],
    [S4, "🔴🔴🔴 팝업 하나의 몫"],
    [S4, "🔴 팝업 + 도서 둘의 몫"],
    [S4, "🔴 팝업의 학습 라벨"],
    [S4, K2, "㉮ d=12(팝업 포함 · 러너가 실제로 낸 값)"],
    [S4, K2, "🔴🔴 ㉯ d=11(팝업 뺀 «계산» · 러너 산출물에 이 칸은 «없다»)"],
    [S4, K2, "🔴 ㉯ 의 `SE_0`(해석 근사)"],
    [S5, KS, "🔴 순열 p(조각 «전부» 넘는다 = 연언)"],
    [S5, KS, "🔴 순열 p(조각 «하나라도» 넘는다)"],
    [S5, KK, "🔴 순열 p(조각 «전부» 넘는다 = 연언)"],
    [S5, KK, "🔴 분모: 도메인"],
    [S6, "🔴🔴 분모: 전량"],
    [S6, "🔴 2·SE 를 넘은 칸"],
    [S6, "판정 불가 칸"],
    [S7, "🔴 사전등록 m"],
    [S7, "모인 p 수"],
    [S7, "🔴 Holm 뒤 살아남은 수"],
    [S8, "🔴 분모: 검사한 주장 합"],
    [S8, "🔴 ㉮ 분자 합"],
    [S8, "🔴 ㉯ 분자 합"],
    [S9, "🔴 채점 합", "맞다"],
    [S9, "🔴 채점 합", "🔴 틀림"],
    [S9, "🔴 채점 합", "🔴 미측정"],
    [SA, "🔴 채점 합", "통과"],
    [SA, "🔴 채점 합", "🔴 불통과"],
    [SA, "🔴 채점 합", "🔴 미측정"],
]

CLAIMS = []
SKIPPED = []


def _dig(o, path):
    for k in path:
        o = o[k]
    return o


def _fmt(v):
    if isinstance(v, float):
        return ("%.6f" % v).rstrip("0").rstrip(".")
    return str(v)


def _build():
    art = ROOT / ART
    doc = ROOT / DOC
    if not art.is_file() or not doc.is_file():
        SKIPPED.append({"🔴": "산출물이나 문서가 없다 --- 생성기를 먼저 돌려라"})
        return
    src = json.loads(art.read_text(encoding="utf-8"))
    lines = doc.read_text(encoding="utf-8").split("\n")
    for path in REG:
        try:
            v = _dig(src, path)
        except (KeyError, TypeError):
            SKIPPED.append({"키": path, "🔴": "키가 없다"})
            continue
        if isinstance(v, (dict, list)):
            SKIPPED.append({"키": path, "🔴": "값이 목록/사전이라 한 줄 형식본이 없다"})
            continue
        s = _fmt(v)
        hit = ""
        for ln in lines:
            if s in ln:
                hit = ln.strip()
                break
        if isinstance(v, float):
            dec = len(s.split(".")[1]) if "." in s else 0
            spec = "{:.%df}" % dec
        else:
            spec = "{}"
        CLAIMS.append({"문서": DOC, "산출물": ART, "키": path,
                       "문장": hit, "형식": spec})


_build()
