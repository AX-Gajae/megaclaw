# -*- coding: utf-8 -*-
"""🔴 `docs/판정/965.md` 의 `{{…}}` 자리를 **산출물에서 읽어서** 채운다.

⑦ 인용 규약(노트 901): **손 전사 금지.** 판정문의 수는 전부 여기서 산출물을 열어 넣는다.
남은 `{{…}}` 가 하나라도 있으면 **종료 3** 으로 죽는다(조항 59 — 「없다」와 「못 채웠다」는 둘이다).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import datetime as dt
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
DOC = ROOT / "docs/판정/965.md"
M = json.loads((ROOT / "runners/out965_meta.json").read_text(encoding="utf-8"))
C = json.loads((ROOT / "runners/out965_checks.json").read_text(encoding="utf-8"))
LED = json.loads((ROOT / "data/lab/denominator.json").read_text(encoding="utf-8"))

S1 = M["§1 🔴🔴 등록 러너 전수 — 자 셋"]
S3 = M["§3 🔴🔴 V2·V3 검정력과 거짓 양성 — **심어서 잰다**"]
S4 = M["§4 🔴🔴 F1 — **내가 새로 만든 `통과` 키가 상수인가**"]
S5 = M["§5 산출물 쪽 전수 — `통과` 키를 **모든 중첩 레벨**에서 센다"]

rows = S1["🔴 잡은 자리 전량"]
table = "\n".join(
    "| `%s` | %s | `%s` | %s |" % (
        r["자리"], "·".join(r["자"]), r["표현식"][:74].replace("|", "\\|"),
        ("`%s`" % ", ".join(r["🔴 뿌리"])) if r.get("🔴 뿌리") else "—")
    for r in rows)

sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                     capture_output=True, text=True).stdout.strip()

V = {
    "SITES_N": S1["🔴 분모 ② `통과` 자리 + 위임 자리"],
    "TAUT_N": S1["🔴 분자: 항진명제로 잡힌 자리"],
    "UNK_N": S1["🔴 모른다(자 B 가 슬라이스를 못 돌렸거나 상수 False)"],
    "FALL_N": S1["🔴 떨어진다(자 셋 중 아무도 안 잡았고 자 B 가 값이 변함을 봤다)"],
    "A_N": S1["자별 계수"]["A 리터럴"],
    "B_N": S1["자별 계수"]["B 슬라이스"],
    "C_N": S1["자별 계수"]["C 자기재계산"],
    "COND_N": S1["🔴 조건부 리터럴(가지가 자다 — 항진명제로 안 센다)"]["수"],
    "CONSTF_N": S1["🔴 상수 False(생성기가 유효 입력을 못 만들었을 수 있다 — 「모른다」)"]["수"],
    "GLOB_N": S1["🔴 전역이 망가지면 떨어진다(뿌리는 상수 · **항진명제 아님**)"]["수"],
    "TAUT_TABLE": table,
    "PLANT_HIT": S3["🔴 분자: 잡은 심기(어느 자든)"],
    "PLANT_N": S3["분모: 심은 수"],
    "PLANT_EXPECT": S3["⚠ 기대한 자가 잡은 수"],
    "FP_N": S3["분자: 거짓 양성"],
    "NEG_N": S3["분모: 음성 대조 수"],
    "MINE_N": S4["🔴 분모: 내 `통과` 자리"],
    "MINE_TAUT_N": S4["🔴 분자: 상수인 자리"],
    "MINE_TAUT_LIST": (", ".join(S4["🔴 상수인 자리 목록"])
                       if isinstance(S4["🔴 상수인 자리 목록"], list) else S4["🔴 상수인 자리 목록"]),
    "MINE_UNK_N": len(S4["🔴 모른다"]) if isinstance(S4["🔴 모른다"], list) else 0,
    "MINE_BITE_N": S4["🔴 판정을 무는 뿌리를 가진 자리"],
    "OUTKEYS_N": S5["합"],
    "LEDGER_N": len(LED),
    "FINAL_SHA": sha,
    "FINAL_UTC": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}

txt = DOC.read_text(encoding="utf-8")
for k, v in V.items():
    txt = txt.replace("{{%s}}" % k, str(v))
left = re.findall(r"\{\{([A-Z_]+)\}\}", txt)
DOC.write_text(txt, encoding="utf-8")
if left:
    print("🔴 못 채운 자리:", sorted(set(left)))
    sys.exit(3)
print("채웠다:", json.dumps({k: str(v)[:40] for k, v in V.items() if k != "TAUT_TABLE"},
                         ensure_ascii=False))
