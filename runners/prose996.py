# -*- coding: utf-8 -*-
"""🔴 노트 996 의 **산문 주장 = 산출물 키** 등록부 (`⑤′` 절 8).

🔴🔴🔴 **`CLAIMS` 를 손으로 안 적는다.** 아래 `REG` 는 «키 경로»만 적고, 문장은
`docs/판정_996.md` 에서 **그 값이 실제로 앉은 줄**을 기계로 찾아 쓴다.
곧 「표를 고치고 문서를 안 다시 찍은」 자리가 있으면 그 슬롯이 «빈 문장»으로 등록돼 떨어진다.

🔴 **한계(조항 61)**: 등록한 주장만 본다. 「전부 초록」은 「문서에 거짓이 없다」가 «아니다».
"""
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
DOC = "docs/판정_996.md"
ART = "runners/out996_score.json"

S1 = "🔴🔴🔴 ① 995 세계 명제 --- 죽었나 살았나"
S2 = "🔴🔴🔴 ② 팔 C --- 「닫았다」는 «거짓»이다"
S3A = "③ 팔 A --- 「조각 수준」과 「축 수준」을 가른다"
S3B = "③ 팔 B --- 계수 이식"
S5 = "⑤ 🔴🔴 `cluster_se` 칸 «전량»(조항 79 개정 2)"
S6 = "⑥ 🔴 조항 78 계수"
S8 = "⑧ 🔴 예측 채점 P1~P15"
S9 = "⑨ 🔴 반증조건 채점 F1~F16"
S11 = "⑪ 🔴 n* --- 「법칙」이 아니다"

REG = [
    [S1, "M1 기준선 합(995 재현)"],
    [S1, "🔴🔴 M2 잔여 낙차 합"],
    [S1, "🔴🔴🔴 학습량 몫 = (M1 − M2)/M1"],
    [S1, "🔴🔴 문턱까지의 여유 = M2 − 문턱"],
    [S1, "🔴🔴🔴 그 여유를 M2 자신의 SE 로 나눈 값"],
    [S1, "M3 감도 합(한 뽑기 · 세계 명제에 안 쓴다)"],
    [S1, "M1 순열 p(연언)"],
    [S1, "🔴🔴 M2 순열 p(연언)"],
    [S2, "틈 2→4 (기준선 Z1)"],
    [S2, "틈 2→4 (처치 Z3)"],
    [S2, "🔴 닫힌 절대량"],
    [S2, "🔴🔴🔴 닫힌 것 중 길 ② 의 몫"],
    [S2, "🔴 닫힌 것 중 길 ① 의 몫"],
    [S2, "길 ① 먼 원점 2 가 올랐나", "점추정"],
    [S2, "길 ① 먼 원점 2 가 올랐나", "t_clu"],
    [S2, "길 ② 가까운 원점 4 가 내렸나", "점추정"],
    [S2, "길 ② 가까운 원점 4 가 내렸나", "t_clu"],
    [S2, "🔴🔴🔴 양성 대조", "점추정"],
    [S2, "🔴🔴🔴 양성 대조", "t_clu"],
    [S2, "Z 주효과 주효과(원점 4)", "점추정"],
    [S3A, "🔴🔴 축 수준(가족 F1)", "실측 m(결측을 뺀 뒤)"],
    [S3A, "🔴🔴🔴 그 생존자를 열어 보면", "t_clu"],
    [S3A, "🔴🔴🔴 그 생존자를 열어 보면", "d*"],
    [S3A, "🔴🔴 실질 후보(도메인이 많은 칸)", "p"],
    [S3B, "🔴🔴 몫(대리 세계 «안»에서)"],
    [S3B, "🔴🔴 계수 이식 Δ(원점 1)", "t_clu"],
    [S5, "🔴🔴🔴 네 팔 합", "🔴 분모: 이 사이클이 낸 cluster_se 칸 전량"],
    [S5, "🔴🔴🔴 네 팔 합", "2·SE 를 넘은 칸"],
    [S5, "🔴🔴🔴 네 팔 합", "🔴 판정 불가 칸"],
    [S5, "팔 0", "🔴 분모: 낸 칸 전량"],
    [S5, "팔 A", "🔴 분모: 낸 칸 전량"],
    [S5, "팔 B", "🔴 분모: 낸 칸 전량"],
    [S5, "팔 C", "🔴 분모: 낸 칸 전량"],
    [S6, "🔴🔴🔴 네 팔 합(기계)", "🔴 기계 ㉮"],
    [S6, "🔴🔴🔴 네 팔 합(기계)", "🔴 기계 ㉯"],
    [S6, "🔴🔴 사전등록이 «손»으로 센 것", "합"],
    [S8, "🔴 채점 합", "맞다"],
    [S8, "🔴 채점 합", "🔴 틀림"],
    [S8, "🔴 채점 합", "🔴 미측정"],
    [S9, "🔴 채점 합", "통과"],
    [S9, "🔴 채점 합", "🔴 불통과(게재값)"],
    [S11, "챔피언 세계(996 이 직접)"],
    [S11, "alpha977 세계(979~995 가 쓰던 값)"],
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
