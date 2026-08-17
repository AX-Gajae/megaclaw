#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""985 §2-2 — 🔴🔴🔴 **인증한 문서와 실린 문서가 같은가**를 «잰다».

🔴 **왜 (티처 #123 1순위 ⓑ·ⓓ).** 984 의 `§D` 가 인증한 것은

| 칸 | 인증값 | 실린 값 |
|---|---|---|
| 판정문 글자 수 | **8193** | **8156** |
| handoff 글자 수 | **3224** | **3187** |
| 치환표 칸 수 | **168** | **166** |
| 표 sha256 | `0f42bec5…` | `eea591a4…` |

🔴 **곧 실린 문서는 감사받은 적이 없다.** 그리고 표 sha 자체가 **재현 불가능**했다 ---
`seal_sections` 가 표 dict 에 두 키를 주입해 **표가 스스로 적은 칸 수(166)와 파일 안의
실제 칸 수(168)가 갈렸고**, 인용된 sha 는 **165 키 판**의 것이라 디스크 파일을 해시하는
검증자는 `736db334…` 를 얻는다.

**이 러너가 재는 것 다섯(= 수렴의 정의 · 사전등록 §2-2):**
1. 판정문 글자 수 · 2. card 글자 수 · 3. handoff 글자 수 · 4. 치환표 칸 수 · 5. 표 sha256

🔴 **검정력 시연(조항 64)**: 같은 자를 **984 의 파일에도** 물려 `False` 가 나오는 것을
같이 싣는다 --- 「입력이 변하면 값이 변한다」.

씀:
    python3 runners/certify985.py --stage certify --ref <40자 sha>
"""
import argparse
import collections
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cycle985 as CY                                   # noqa: E402

OUT = "runners/out985_certify.json"
TABLE_KEY = "🔴🔴 치환표"
#: 🔴 985 는 표를 «한 겹 감싼다**(`["🔴🔴 치환표"]["🔴 칸"]`) --- 984 는 안 감쌌다.
#:  해싱 대상은 **언제나 칸 dict 하나**이고 이 함수가 그 자리를 정한다.
CELLS_KEY = "🔴 칸"
DEN = "data/lab/denominator.json"


def _cells(tb):
    """🔴 985 는 표를 감쌌고 984 는 안 감쌌다 --- 해싱 대상 자리를 여기서 하나로 정한다."""
    t = (tb or {}).get(TABLE_KEY)
    if isinstance(t, dict) and CELLS_KEY in t:
        return t[CELLS_KEY], t.get("🔴 칸 수")
    return t, None

SPEC = {
    985: {"table": "runners/out985_table.json",
          "score": "runners/out985_score.json",
          "rule_d": "§D 🔴 규칙 D 감사(분모 다섯)",
          "docs": ("docs/판정_985.md", "docs/card_985.md", "docs/handoff_985.md"),
          "ledger_key": "노트 985"},
    984: {"table": "runners/out984_table.json",
          "score": "runners/out984_score.json",
          "rule_d": "§D 🔴 규칙 D 감사(분모 다섯)",
          "docs": ("docs/판정_984.md", "docs/card_984.md", "docs/handoff_984.md"),
          "ledger_key": "노트 984"},
}


def _read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _json(rel):
    t = _read(rel)
    return json.loads(t, object_pairs_hook=collections.OrderedDict) if t else None


def table_sha(T):
    """🔴 `note98*_gen.table_sha` 와 **같은 정규화**(`sort_keys=True`)."""
    return hashlib.sha256(
        json.dumps(T, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def ledger_fixed_point(key):
    """🔴 자기 항목을 뺀 원장의 sha256 --- `house985._minus_self` 와 같은 자."""
    p = ROOT / DEN
    if not p.is_file():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    d.pop(key, None)
    return hashlib.sha256(
        json.dumps(d, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def certify(cycle):
    s = SPEC[cycle]
    tb = _json(s["table"])
    sc = _json(s["score"])
    rows = collections.OrderedDict()
    bad = []

    # ── 1~3 문서 글자 수 ──────────────────────────────────────────
    rd = (sc or {}).get(s["rule_d"]) or {}
    per = rd.get("🔴 대상별") or {}
    for p in s["docs"]:
        txt = _read(p)
        live = len(txt) if txt is not None else None
        cert = (per.get(p) or {}).get("글자 수")
        ok = bool(live is not None and cert is not None and live == cert)
        rows[p] = {"🔴 인증한 글자 수(채점기가 본 것)": cert,
                   "🔴 실린 글자 수(디스크 실측)": live,
                   "🔴 같은가": ok}
        if not ok:
            bad.append(p)

    # ── 4 치환표 칸 수 ────────────────────────────────────────────
    T, _inner_n = _cells(tb)
    live_n = len(T) if isinstance(T, dict) else None
    decl_n = (tb or {}).get("🔴🔴 칸 수")
    cert_n = rd.get("🔴 치환표 칸 수")
    ok_n = bool(live_n is not None and decl_n == live_n and cert_n == live_n)
    rows["치환표 칸 수"] = {
        "🔴 표가 스스로 적은 칸 수": decl_n,
        "🔴 채점기가 인증한 칸 수": cert_n,
        "🔴🔴 디스크 파일의 실제 표 키 수": live_n,
        "🔴 셋이 같은가": ok_n,
    }
    if not ok_n:
        bad.append("치환표 칸 수")

    # ── 5 표 sha256 ──────────────────────────────────────────────
    live_sha = table_sha(T) if isinstance(T, dict) else None
    decl_sha = (tb or {}).get("🔴🔴 표 sha256")
    cert_sha = rd.get("🔴 치환표 sha256")
    ok_s = bool(live_sha and decl_sha == live_sha and cert_sha == live_sha)
    rows["표 sha256"] = {
        "🔴 표가 스스로 적은 sha": decl_sha,
        "🔴 채점기가 인증한 sha": cert_sha,
        "🔴🔴 디스크의 표를 다시 해시한 값(= 검증자가 얻는 값)": live_sha,
        "🔴 셋이 같은가": ok_s,
        "⚠ 자": "`json.dumps(T, ensure_ascii=False, sort_keys=True)` 를 sha256 ---"
               " `note98*_gen.table_sha` 와 «같은» 정규화",
    }
    if not ok_s:
        bad.append("표 sha256")

    return collections.OrderedDict([
        ("🔴 사이클", cycle),
        ("🔴 다섯 칸", rows),
        ("🔴🔴 어긋난 칸", bad or "없음"),
        ("🔴🔴🔴 수렴했나(다섯 칸이 전부 같다)", bool(not bad)),
    ])


def stage(ref):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    mine = certify(985)
    theirs = certify(984)
    out = collections.OrderedDict()
    out["무엇"] = "985 §2-2 — 🔴🔴🔴 **인증한 문서와 실린 문서가 같은가**"
    out["🔴 축"] = "자기 자(문서 고리 수렴)"
    out["🔴 수렴의 정의(사전등록 §2-2 · 측정 전에 박았다)"] = [
        "① 판정문 글자 수", "② card 글자 수", "③ handoff 글자 수",
        "④ 치환표 칸 수", "⑤ 표 sha256",
        "🔴 다섯 칸이 «디스크의 실린 파일 실측»과 전부 같으면 수렴이다",
    ]
    out["§가 🔴🔴🔴 985 자신"] = collections.OrderedDict(
        list(mine.items()) + [
            ("통과", bool(mine["🔴🔴🔴 수렴했나(다섯 칸이 전부 같다)"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **채점기가 인증한 다섯 칸이 실린 파일과 «전부» 같은가.** "
             "하나라도 다르면 실린 문서는 감사받은 적이 없다"),
        ])
    out["§나 🔴🔴 검정력 시연 — 같은 자를 984 에 물린다(조항 64)"] = \
        collections.OrderedDict(list(theirs.items()) + [
            ("🔴🔴🔴 왜 이 절이 있나",
             "🔴 **「입력이 변하면 값이 변해야」 한다**(조항 64). 같은 함수를 984 의 "
             "파일에 물려 **`False` 가 나오는 것**이 이 자가 항진명제가 아니라는 증거다. "
             "🔴 **어긋난 칸이 «몇 개»인지는 산문에 안 적는다** --- 바로 아래 "
             "「984 에서 어긋난 칸 수」가 «잰» 값이고, 985 가 984 의 문서에 정정을 얹으면 "
             "그 수가 «는다»(그때 산문만 남으면 984 가 저지른 병의 재발이다)"),
            ("🔴🔴 984 에서 어긋난 칸 수",
             (len(theirs["🔴🔴 어긋난 칸"])
              if isinstance(theirs["🔴🔴 어긋난 칸"], list) else 0)),
            ("통과", bool(theirs["🔴🔴🔴 수렴했나(다섯 칸이 전부 같다)"] is False)),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **이 자가 984 에서 «떨어지는가»** --- 안 떨어지면 자가 아니다"),
        ])
    out["§다 🔴 원장 고정점 지문"] = collections.OrderedDict([
        ("🔴 무엇", "🔴 **자기 항목을 뺀 원장의 sha256** --- 문서에 실을 수 있는 유일한 지문"),
        ("🔴 985 판", ledger_fixed_point("노트 985")),
        ("🔴 984 판(= 984 항목을 뺀 지금 원장)", ledger_fixed_point("노트 984")),
        ("🔴 왜 고정점인가",
         "🔴 이 사이클의 항목을 더하거나 고쳐도 «안 바뀐다» --- 984 가 실은 전량 sha 는 "
         "그 뒤 세 번 바뀌었다"),
        ("통과", bool(ledger_fixed_point("노트 985"))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "고정점 지문을 «냈는가» 하나다"),
    ])
    out["통과"] = bool(out["§가 🔴🔴🔴 985 자신"]["통과"]
                     and out["§나 🔴🔴 검정력 시연 — 같은 자를 984 에 물린다(조항 64)"]["통과"]
                     and out["§다 🔴 원장 고정점 지문"]["통과"])
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["certify"])
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    r = stage(a.ref)
    print(json.dumps({
        "통과": r["통과"],
        "985 수렴": r["§가 🔴🔴🔴 985 자신"]["🔴🔴🔴 수렴했나(다섯 칸이 전부 같다)"],
        "985 어긋난 칸": r["§가 🔴🔴🔴 985 자신"]["🔴🔴 어긋난 칸"],
        "984 어긋난 칸": r["§나 🔴🔴 검정력 시연 — 같은 자를 984 에 물린다(조항 64)"][
            "🔴🔴 어긋난 칸"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
