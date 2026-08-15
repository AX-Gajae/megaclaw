#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""974 --- 논문 치환기. 🔴 **모든 값은 `runners/out974_*.json` 에서만 온다**(규칙 D).

🔴 채점: 치환 뒤 **남은 슬롯이 0** 이어야 하고, 그 뒤에
`ledger974.py --stage numaudit` 으로 **본문의 모든 수**를 다시 훑는다
(973 이 걸린 자리 --- 남은 슬롯만 보면 손 리터럴을 못 본다).
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
OUT = ROOT / "runners"
D = ROOT / "paper/steps/974_precision"
A = {p.stem.replace("out974_", ""): json.loads(p.read_text(encoding="utf-8"))
     for p in sorted(OUT.glob("out974_*.json"))}

P = A["precision"]
ALL = P["🔴🔴 ① 층화 표본 전체(층 무시)"]
SRS = P["🔴 ①′ 단순무작위 300 만"]
ST = P["🔴 ① 층별"]
EF = P["🔴🔴 ② 유효 삼중쌍"]
GA = P["🔴 ③ 게이트"]
G4 = P["🔴 ③ 게이트 넷을 다 걸면"]
CT = A["contexts"]
C5 = CT["⑤ 한글 문턱"]
LO = A["loso"]["🔴🔴🔴 C3 --- leave-one-source-out Δ"]
C2 = A["loso"]["🔴🔴🔴 C2 --- 도메인별 유보 성능의 최저값"]
DZ = A["loso"]["🔴 자료"]
KC, KG, KB = "C(HPLT 전량)", "C′(HPLT · 974 게이트)", "B(HPLT 없음)"
EK = "🔴 주 자 = 개체 정밀도(모름=실패)"
T3 = dict(C5["늘어난 제목 상위 40"])


def f(x, d=6):
    return ("%." + str(d) + "f") % float(x)


def g(x):
    return "{:,}".format(int(x))


M = {
    "ROWS": g(EF["🔴 분모: 973 이 부른 수"]),
    "NLAB": g(ALL["분모: 라벨한 행"]),
    "NTRUE": g(ALL["참"]),
    "GENN": g(ALL["거짓·일반어"]),
    "PREC": f(ALL[EK]),
    "PRECD": f(ALL["🔴 문서(페이지) 정밀도"]),
    "CILO": f(ALL["🔴 개체 정밀도 95% CP"][0]),
    "CIHI": f(ALL["🔴 개체 정밀도 95% CP"][1]),
    "NSRS": g(SRS["분모: 라벨한 행"]),
    "PRECS": f(SRS[EK]),
    "EFF": "{:,.1f}".format(EF["점추정"]),
    "EFFLO": "{:,.1f}".format(EF["95% 붓스트랩 구간"][0]),
    "EFFHI": "{:,.1f}".format(EF["95% 붓스트랩 구간"][1]),
    "EFFPCT": ("%.2f\\%%" % (100.0 * EF["비율"])),
    "P_SE": f(ST["단일·en"][EK]), "P_ME": f(ST["다중·en"][EK]),
    "P_SK": f(ST["단일·ko"][EK]), "P_MK": f(ST["다중·ko"][EK]),
    "N_SK": g(ST["단일·ko"]["전량 행"]),
    "NDOC": g(CT["🔴 되찾은 문서"]), "NMISS": g(CT["🔴 못 찾은 문서"]),
    "CUT": g(G4["🔴 전량에서 떼는 행"]),
    "CUTPCT": ("%.2f\\%%" % (100.0 * G4["비율"])),
    "PCUT": f(G4["표본에서 떼는 쪽 정밀도"][EK]),
    "PKEEP": f(G4["표본에서 남는 쪽 정밀도"][EK]),
    "PH3IN": f(GA["H3 위키 자기 순환"]["표본에서 무는 행의 정밀도"][EK]),
    "PH3OUT": f(GA["H3 위키 자기 순환"]["표본에서 남는 행의 정밀도"][EK]),
    "T3TITLE": g(C5["🔴 3 판에만 있는 제목 수"]),
    "T3PAIR": g(C5["🔴 같은 표본 문서에서 늘어난 (문서,제목) 짝"]),
    "T3TOP": g(C5["늘어난 제목 상위 40"][0][1]),
    "T3OPM": g(T3["원펀맨"]),
    "HOHPLT": g(DZ["🔴 유보에 든 HPLT 행"]),
    "TRB": g(DZ["학습 행 B"]), "TRC": g(DZ["학습 행 C"]),
    "ADDC": g(LO[KC]["🔴 늘어난 학습 행"]),
    "LOSO": f(LO[KC]["🔴🔴 묶음 Δρ(C−B)"]),
    "LOSOG": f(LO[KG]["🔴🔴 묶음 Δρ(C−B)"]),
    "PVAL": f(LO[KC]["🔴 순열 귀무"]["🔴🔴🔴 순열 p(단측 · 사전등록 §3-가 정본 자)"]),
    "PVALG": f(LO[KG]["🔴 순열 귀무"]["🔴🔴🔴 순열 p(단측 · 사전등록 §3-가 정본 자)"]),
    "NULL95": f(LO[KC]["🔴 순열 귀무"]["귀무 95 분위"]),
    "POSC": LO[KC]["🔴 양수 도메인"].replace("/", "/"),
    "DPLUS": f(LO[KC]["🔴🔴 C5 --- Δ⁺(가장 오른 도메인)"][1]),
    "DMINUS": f(LO[KC]["🔴🔴 C5 --- 최대 Δ⁻(가장 내린 도메인)"][1]),
    "MINB": f(C2[KB]["🔴🔴 최저값"]), "MINC": f(C2[KC]["🔴🔴 최저값"]),
    "MING": f(C2[KG]["🔴🔴 최저값"]),
    "AVGB": f(C2[KB]["평균"]), "AVGC": f(C2[KC]["평균"]), "AVGG": f(C2[KG]["평균"]),
}


def main():
    src = (D / "main.tex.tmpl").read_text(encoding="utf-8")
    for k, v in M.items():
        src = src.replace("@@" + k + "@@", str(v))
        src = src.replace("@@" + k.replace("_", "\\_") + "@@", str(v))
    left = re.findall(r"@@[A-Z_\\0-9]+@@", src)
    if left:
        raise SystemExit("🔴 남은 슬롯: %s" % sorted(set(left)))
    (D / "main.tex").write_text(src, encoding="utf-8")
    print("치환 %d 개 · 남은 슬롯 0" % len(M))
    return 0


if __name__ == "__main__":
    sys.exit(main())
