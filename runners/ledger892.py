# -*- coding: utf-8 -*-
"""노트 892 곁가지 — **논문 463 의 '원장 판 차 83건' 을 자를 바꿔 가며 다시 센다**.

티처 #54 C1: *'891 의 「뒤집힘 0건」은 검사 범위가 이번 사이클뿐인데 전역 주장으로
적혔다. 논문 463 이 원장 판 차 83건 중 60건이 0.0045 아래라고 세어 뒀는데 그 83건을
새 자로 다시 세지 않았다.'*

🔴 **463 자신이 적어 둔 한계를 그대로 이어받는다**: *'원장 훑기가 글자 기반이다. 기각과
사전 등록이 섞여 있어 83·60 은 정확한 수가 아니다.'* 그러므로 **절대 건수를 주장하지
않는다.** 주장하는 것은 **같은 훑기를 자만 바꿨을 때 몇 건이 편을 바꾸는가** --- 훑기의
편향은 자에 대해 상수라 그 차는 견딘다.

자 넷을 댄다:
    0.0045    옛 상수(11도메인 유물)
    0.00353   노트 891 채택 문턱(티처 #54 로 '잠정')
    0.0011    노트 890 예리한 자(실격)
    바닥      노트 892 가 잰 **순수 난수 열의 잡음 바닥**(있으면 읽어 쓴다 --- 손 전사 금지)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
LED = ROOT / "data/lab/denominator.json"
FLOOR_OUT = ROOT / "runners/out892_floor.json"
OUT = ROOT / "data/lab/ledger_recount_892.json"

#: 판 값이 붙은 수. 463 과 같은 글자 훑기 --- '판' 이라는 낱말 뒤 8글자 안의 부호 있는 소수.
PAT = re.compile(r"판[^0-9\n]{0,8}([+\-−]\s?0\.0\d{2,4})")
RULERS = {"옛 0.0045": 0.0045, "891 0.00353": 0.00353, "890 0.0011": 0.0011}


def walk(o, key=None):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, key or k)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v, key)
    elif isinstance(o, str):
        yield key, o


def main():
    led = json.loads(LED.read_text())
    hits = []
    for top, body in led.items():
        blob = json.dumps(body, ensure_ascii=False)
        if "채택" not in blob and "채택" not in top:
            continue
        for _, s in walk(body, top):
            for m in PAT.finditer(s):
                raw = m.group(1).replace("−", "-").replace(" ", "")
                try:
                    v = abs(float(raw))
                except ValueError:
                    continue
                hits.append({"항목": top[:90], "판 차": v, "원문": m.group(0)})
    #: 같은 항목에서 같은 값이 여러 번 나오면 한 번만 --- 463 은 안 했다(그래서 병기한다)
    uniq, seen = [], set()
    for h in hits:
        k = (h["항목"], h["판 차"])
        if k not in seen:
            seen.add(k)
            uniq.append(h)

    rulers = dict(RULERS)
    floor = None
    if FLOOR_OUT.exists():
        f = json.loads(FLOOR_OUT.read_text())
        cont = f["🔴 열 수별 잡음 바닥(연속 · 뽑기 12 · 씨앗 0~5)"]
        rulers["892 난수 1열 바닥"] = cont["연속 1열"]["🔴 **잡음 바닥 = μ + 2σ**"]
        rulers["892 난수 3열 바닥"] = cont["연속 3열"]["🔴 **잡음 바닥 = μ + 2σ**"]
        floor = rulers["892 난수 3열 바닥"]

    vals = [h["판 차"] for h in uniq]
    table = {name: {"자 위(순위를 정할 수 있다)": sum(1 for v in vals if v >= r),
                    "자 아래(못 정한다)": sum(1 for v in vals if v < r),
                    "몫(아래)": round(sum(1 for v in vals if v < r) / max(len(vals), 1), 3)}
             for name, r in rulers.items()}
    band = sorted([h for h in uniq if 0.00353 <= h["판 차"] < 0.0045],
                  key=lambda h: -h["판 차"])
    band2 = sorted([h for h in uniq if floor and 0.0045 <= h["판 차"] < floor],
                   key=lambda h: -h["판 차"])
    out = {
        "노트": 892,
        "무엇": "논문 463 의 '원장 판 차 83건' 을 자 넷으로 다시 센다",
        "🔴 한계(463 에서 이어받음)": "글자 훑기다 --- 기각·사전등록이 섞인다. **절대 건수를 "
                                "주장하지 않는다.** 주장은 '자를 바꾸면 몇 건이 편을 바꾸나' 뿐이고 "
                                "그 차는 훑기 편향에 대해 견딘다.",
        "훑은 값 수(중복 제거 전)": len(hits),
        "훑은 값 수(중복 제거 후)": len(uniq),
        "463 이 적은 수": {"판 차 건수": 83, "2SD(0.0045) 아래": 60, "1SD(0.0023) 아래": 38},
        "자": rulers,
        "자별 분포": table,
        "🔴 0.0045 → 0.00353 로 편을 바꾸는 항목(새로 열린 띠)": band,
        "🔴 0.0045 → 892 난수 3열 바닥 으로 편을 바꾸는 항목(바닥이 더 크면)": band2,
        "전량": sorted(uniq, key=lambda h: -h["판 차"]),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "전량"},
                     ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
