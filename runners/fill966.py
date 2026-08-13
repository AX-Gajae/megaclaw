# -*- coding: utf-8 -*-
"""🔴 `docs/판정/966.md` 의 `{{…}}` 자리를 **산출물에서 읽어서** 채운다.

⑦ 인용 규약(노트 901): **손 전사 금지.** 판정문의 수는 전부 여기서 산출물을 열어 넣는다.
남은 `{{…}}` 가 하나라도 있으면 **종료 3** 으로 죽는다(조항 59 — 「없다」와 「못 채웠다」는 둘이다).

🔴 **F7(사전등록 §5)**: *「판정문의 수 중 산출물에 영수증이 없는 것이 하나라도 있으면 실패」*.
이 파일의 `V` 딕트가 **그 영수증 전량**이다 --- 965 의 「초판 34」가 검증 불가능했던 이유는
그 수가 이 표에 **없었기** 때문이다.

🔴 **도장은 `git rev-parse HEAD` 가 아니다**(노트 966 R1 · 티처 #104 C5) ---
`docs/루프.md:532` 가 폐기한 규칙이고 긴 러너에서 그 sha 는 원리상 「시작 시점」이다.
**코드 sha256 + 끝 시각(UTC)** 을 쓴다.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
DOC = ROOT / "docs/판정/966.md"
L = json.loads((ROOT / "runners/out966_longmem.json").read_text(encoding="utf-8"))
M = json.loads((ROOT / "runners/out966_meta.json").read_text(encoding="utf-8"))
LED = json.loads((ROOT / "data/lab/denominator.json").read_text(encoding="utf-8"))
AG = json.loads((ROOT / "runners/out966_age.json").read_text(encoding="utf-8"))

W = L["§2 배선"]["검사"]
B = L["§3 판"]
P = L["§4 명제"]
G = L["§5 도메인 게이트"]
S1 = M["§1 🔴🔴 등록 러너 전수 — 자 셋"]
S4 = M["§4 🔴🔴 F1 — **내가 새로 만든 `통과` 키가 상수인가**"]


def _code_sha() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "runners").glob("*966*.py")):
        h.update(p.read_bytes())
    return h.hexdigest()


live = {d: v for d, v in P["도메인별"].items() if v.get("🔴 잰다")}
rows = sorted(live.items(),
              key=lambda kv: -kv[1]["🔴 들뜸 ↔ 결과(수준을 뺀 뒤)"])
DOM_TABLE = "\n".join(
    "| %s | %d | %.4f | %.4f | %.4f | %s |" % (
        d, v["n"], v["곁: 수준 ↔ 결과"], v["🔴 들뜸 ↔ 결과(수준을 뺀 뒤)"],
        v["순열 바닥 |ρ| 95%"], "🔴 **넘었다**" if v["🔴 바닥을 넘었나"] else "못 넘었다")
    for d, v in rows)

BOARD_TABLE = "\n".join(
    "| %s | %.4f | %.4f | %+.4f |" % (d, v["기준선"], v["처리"], v["Δ"])
    for d, v in sorted(B["도메인별"].items(), key=lambda kv: -kv[1]["Δ"]))

V = {
    # §1 특징
    "SRC_ENT": L["§1 특징"]["원천 개체"],
    "VALID_ENT": L["§1 특징"]["🔴 유효 개체"],
    "SRC_FILES": L["원천 파일 수"],
    # §2 배선
    "WIRE_OK": L["§2 배선"]["🔴 분자: 통과"],
    "WIRE_N": L["§2 배선"]["🔴 분모: 돌린 검사"],
    "LEAK_N": W["W1 누출 없음(F5)"]["🔴 분자: 시작일 이후 날짜를 쓴 개체"],
    "LEAK_DEN": W["W1 누출 없음(F5)"]["분모: 유효 개체"],
    "LEAK_MAX": W["W1 누출 없음(F5)"]["쓴 최대날짜 − 시작일의 최댓값(일)"],
    "LEAK_PLANT": W["W1 누출 없음(F5)"]["심은 누출판의 위반 개체"],
    "ATT_N": W["W2 유보 부착"]["🔴 분자: 부착 유보 행"],
    "ATT_PCT": W["W2 유보 부착"]["부착률(%)"],
    "ATT_DOM": W["W2 유보 부착"]["🔴 붙은 도메인"],
    "UNIQ_N": W["W3 열이 상수가 아니다(조항 64)"]["🔴 분자: 서로 다른 값 가짓수"],
    "UNIQ_CONST": W["W3 열이 상수가 아니다(조항 64)"]["심은 상수판의 가짓수"],
    "COL_BEFORE": W["W4 열 이름이 모형 입력에 있다"]["기준선 열 수(도서)"],
    "COL_AFTER": W["W4 열 이름이 모형 입력에 있다"]["처리 열 수(도서)"],
    "MOVED_N": W["W5 그 열이 모형에 닿았다(F6)"]["🔴 분자: 열만 섞었을 때 점수가 변한 도메인"],
    "MOVED_DEN": W["W5 그 열이 모형에 닿았다(F6)"]["분모: 점수가 난 도메인"],
    # §3 판
    "BASE_RHO": "%.6f" % B["기준선"]["판"],
    "BASE_SD": "%.4f" % B["기준선"]["SD"],
    "TREAT_RHO": "%.6f" % B["처리"]["판"],
    "TREAT_SD": "%.4f" % B["처리"]["SD"],
    "REPRO_DIFF": "%.6f" % B["🔴 기준선이 정본 0.47034 를 재현하나"]["차"],
    "DELTA": "%+.6f" % B["🔴 Δρ"],
    "THRESH": B["🔴 문턱(열 1개 증가)"],
    "RATIO": "%.4f" % B["🔴 Δρ ÷ 문턱"],
    "CLEARED": "넘었다" if B["🔴 이 자를 넘었나"] else "🔴 **못 넘었다**",
    "BOARD_TABLE": BOARD_TABLE,
    "BOARD_SEC": int(B["초"]["기준선"] + B["초"]["처리"]),
    # §4 명제
    "PROP_DOM": P["🔴 분모: 잰 도메인"],
    "PROP_N": P["🔴 잰 개체 합"],
    "SIGN_POS": P["🔴 부호 +"],
    "SIGN_NEG": P["🔴 부호 −"],
    "OVER_N": P["🔴 바닥을 넘은 도메인"],
    "DOM_TABLE": DOM_TABLE,
    "OVER_POS": sum(1 for v in live.values()
                    if v["🔴 바닥을 넘었나"]
                    and v["🔴 들뜸 ↔ 결과(수준을 뺀 뒤)"] > 0),
    "OVER_NEG": sum(1 for v in live.values()
                    if v["🔴 바닥을 넘었나"]
                    and v["🔴 들뜸 ↔ 결과(수준을 뺀 뒤)"] < 0),
    # 사후 강건성(나이)
    "AGE_OVER": AG["🔴 나이까지 뺀 뒤 바닥을 넘은 도메인"],
    "AGE_POS": AG["🔴 그중 양수"],
    "AGE_NEG": AG["🔴 그중 음수"],
    "AGE_SIGN": AG["🔴 부호가 살아남은 도메인"],
    # §5 도메인 게이트
    "GATE_DELTA": G["🔴 Δ"],
    "GATE_BEFORE": G["실측"]["앞 도메인 수"],
    "GATE_AFTER": G["실측"]["뒤 도메인 수"],
    "GATE_LOST": (", ".join(G["실측"]["🔴 사라진 도메인(앞 − 뒤)"])
                  if isinstance(G["실측"]["🔴 사라진 도메인(앞 − 뒤)"], list)
                  else G["실측"]["🔴 사라진 도메인(앞 − 뒤)"]),
    "GATE_PASS": "통과" if G["🔴 게이트 통과"] else "🔴 **떨어졌다**",
    "GATE_BITES": "무다" if G["🔴 자가 무나(ⓓ·ⓔ 는 떨어지고 ⓖ 는 안 떨어진다)"] else "🔴 안 문다",
    # F1
    "F1_DEN": S4["🔴 분모: 내 `통과` 자리"],
    "F1_TAUT": S4["🔴 분자: 상수인 자리"],
    "F1_UNK": len(S4["🔴 모른다"]) if isinstance(S4["🔴 모른다"], list) else 0,
    "F1_FALL": S1["🔴 떨어진다(자 셋 중 아무도 안 잡았고 자 B 가 값이 변함을 봤다)"],
    "F1_CONSTF": S1["🔴 상수 False(생성기가 유효 입력을 못 만들었을 수 있다 — 「모른다」)"]["수"],
    "F1_COND": S1["🔴 조건부 리터럴(가지가 자다 — 항진명제로 안 센다)"]["수"],
    # 도장
    "LEDGER_N": len(LED),
    "FINAL_SHA": _code_sha()[:32],
    "FINAL_UTC": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}

txt = DOC.read_text(encoding="utf-8")
for k, v in V.items():
    txt = txt.replace("{{%s}}" % k, str(v))
left = re.findall(r"\{\{([A-Z_0-9]+)\}\}", txt)
DOC.write_text(txt, encoding="utf-8")
if left:
    print("🔴 못 채운 자리:", sorted(set(left)))
    sys.exit(3)
print("채웠다 %d 자리:" % len(V),
      json.dumps({k: str(v)[:34] for k, v in V.items()
                  if k not in ("DOM_TABLE", "BOARD_TABLE")}, ensure_ascii=False))
