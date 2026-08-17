#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""986 §2 — 🔴🔴🔴 **인증한 문서와 실린 문서가 같은가 · 그리고 «표와 채점기»가 같은가**.

985 판은 다섯 칸을 쟀다: 판정문 글자 수 · 카드 글자 수 · handoff 글자 수 ·
치환표 칸 수 · 표 sha256. 🔴 **그 다섯이 전부 초록인 채로 985 는 틀렸다.**

| 자 | 985 에서 무엇을 봤나 | 왜 못 잡았나 |
|---|---|---|
| 규칙 D | 문서의 수 ⊆ 표의 칸 | 🔴 표가 **`13 / 14`** 를 들고 있어 통과 |
| `certify985` | 표 ↔ 디스크 문서 | 🔴 둘 다 `13 / 14` 라 **수렴 `true`** |
| 반증조건 9 | 여섯 자리가 같은 수를 적나 | 🔴 바늘이 **세 수**뿐 |

🔴 **「표 ↔ 채점기」를 잇는 자가 없었다.** 986 이 그 **여섯째 칸**을 박는다:

> **⑥ 치환표의 «채점 칸» == 채점 산출물의 «채점 칸»**(`cycle986.SCORE_CELLS`)

씀:
    python3 runners/certify986.py --stage certify --ref <40자 sha>
"""
import argparse
import collections
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cycle986 as CY                                   # noqa: E402

OUT = "runners/out986_certify.json"
TABLE_KEY = "🔴🔴 치환표"
CELLS_KEY = "🔴 칸"
DEN = "data/lab/denominator.json"

#: 🔴 985 의 치환표 칸 ↔ `out985_score.json` 키 경로.
#:  🔴 **이것은 「자의 정의」지 「전사한 수」가 아니다** --- `note985_gen.py:280-287` 이
#:  쓴 바로 그 경로다. 여섯째 칸을 **985 에도 물려** `False` 가 나오는 것을 싣는다(조항 64).
SCORE_CELLS_985 = {
    "채.반증분자모": ["§6 🔴 반증조건", "🔴🔴 분자 / 분모"],
    "채.반증분모": ["§6 🔴 반증조건", "🔴 분모"],
    "채.반증된": ["§6 🔴 반증조건", "🔴🔴 반증된 조건"],
    "채.예측분자모": ["§5 🔴 예측", "🔴🔴 분자 / 분모"],
    "채.예측분자": ["§5 🔴 예측", "🔴 분자"],
    "채.규칙D표밖": ["§D 🔴 규칙 D 감사(분모 다섯)", "🔴🔴 표 밖 합"],
    "채.규칙D분모": ["§D 🔴 규칙 D 감사(분모 다섯)", "🔴🔴 채점 분모"],
    "채.여섯자리": ["§9 🔴🔴 여섯 자리가 같은 수를 적나", "통과"],
}

SPEC = {
    986: {"table": "runners/out986_table.json",
          "score": "runners/out986_score.json",
          "rule_d": "§D 🔴 규칙 D 감사(분모 여섯)",
          "docs": ("docs/판정_986.md", "docs/card_986.md", "docs/handoff_986.md"),
          "cells": CY.SCORE_CELLS,
          "ledger_key": "노트 986"},
    985: {"table": "runners/out985_table.json",
          "score": "runners/out985_score.json",
          "rule_d": "§D 🔴 규칙 D 감사(분모 다섯)",
          "docs": ("docs/판정_985.md", "docs/card_985.md", "docs/handoff_985.md"),
          "cells": SCORE_CELLS_985,
          #: 🔴🔴🔴 **985 문서는 «985 가 끝난 트리»에서 읽는다**(986 신설).
          #:  🔴 **왜.** 986 은 985 의 세 오기에 «정정을 얹는다» --- 그러면 985 의
          #:  문서 글자 수가 바뀌고, 그 어긋남은 **986 자신의 편집**이 만든 것이다.
          #:  티처 #124 가 985 에 물린 그 병(「다섯 칸 어긋난다」의 정체가 `4 + 1`
          #:  이고 다섯째는 985 자신의 편집이었다)이 그대로 재발한다.
          #:  🔴 그래서 **정정 «이전»의 바이트**로 잰다. 그 ref 를 산출물에 박는다.
          "doc_ref": "582444a856f6c573c7d5ebb34c5579497f5faee6",
          "ledger_key": "노트 985"},
}


def _read(rel, ref=None):
    """🔴 `ref` 를 주면 **그 커밋된 트리**에서 읽는다(디스크가 아니다 · 조항 59)."""
    if ref:
        p = subprocess.run(["git", "show", "%s:%s" % (ref, rel)], cwd=str(ROOT),
                           capture_output=True)
        if p.returncode != 0:
            return None
        return p.stdout.decode("utf-8", "surrogateescape")
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _json(rel):
    t = _read(rel)
    return json.loads(t, object_pairs_hook=collections.OrderedDict) if t else None


def _cells(tb):
    t = (tb or {}).get(TABLE_KEY)
    if isinstance(t, dict) and CELLS_KEY in t:
        return t[CELLS_KEY], t.get("🔴 칸 수")
    return t, None


def table_sha(T):
    """🔴 `note98*_gen.table_sha` 와 **같은 정규화**(`sort_keys=True`)."""
    return hashlib.sha256(
        json.dumps(T, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def ledger_fixed_point(key):
    p = ROOT / DEN
    if not p.is_file():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    d.pop(key, None)
    return hashlib.sha256(
        json.dumps(d, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def sixth_cell(T, sc, cells):
    """🔴🔴🔴 **여섯째 칸 — 치환표의 채점 칸 == 채점 산출물의 채점 칸.**

    🔴 `note98*_gen`(표를 채우는 쪽)과 이 함수(표를 검사하는 쪽)가 **같은 상수**
    (`cycle986.SCORE_CELLS`)를 읽는다. 그래서 「표와 채점기 중 무엇이 늦었나」를
    **원리상** 잡는다.
    """
    rows, bad, unread = collections.OrderedDict(), [], []
    for name, path in sorted(cells.items()):
        in_t = isinstance(T, dict) and name in T
        got, live = CY.resolve(sc or {}, path)
        cell = T.get(name) if in_t else None
        if not in_t:
            rows[name] = {"🔴": "🔴 치환표에 그 칸이 «없다»(= 「같다」가 아니다 · 조항 59)",
                          "채점 산출물 값": live if got else None}
            unread.append(name)
            continue
        if not got:
            rows[name] = {"🔴": "🔴 채점 산출물에 그 키 경로가 «없다»", "치환표 값": cell,
                          "키 경로": path}
            unread.append(name)
            continue
        ok = bool(cell == live)
        rows[name] = {"🔴 치환표의 칸": cell, "🔴 채점 산출물의 값": live,
                      "🔴 키 경로": path, "🔴 같은가": ok}
        if not ok:
            bad.append(name)
    return rows, bad, unread


def certify(cycle):
    s = SPEC[cycle]
    tb = _json(s["table"])
    sc = _json(s["score"])
    rows = collections.OrderedDict()
    bad = []

    # ── 1~3 문서 글자 수 ──────────────────────────────────────────
    rd = (sc or {}).get(s["rule_d"]) or {}
    per = rd.get("🔴 대상별") or {}
    dref = s.get("doc_ref")
    for p in s["docs"]:
        txt = _read(p, dref)
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
    rows["치환표 칸 수"] = {"🔴 표가 스스로 적은 칸 수": decl_n,
                      "🔴 채점기가 인증한 칸 수": cert_n,
                      "🔴🔴 디스크 파일의 실제 표 키 수": live_n,
                      "🔴 셋이 같은가": ok_n}
    if not ok_n:
        bad.append("치환표 칸 수")

    # ── 5 표 sha256 ──────────────────────────────────────────────
    live_sha = table_sha(T) if isinstance(T, dict) else None
    decl_sha = (tb or {}).get("🔴🔴 표 sha256")
    cert_sha = rd.get("🔴 치환표 sha256")
    ok_s = bool(live_sha and decl_sha == live_sha and cert_sha == live_sha)
    rows["표 sha256"] = {"🔴 표가 스스로 적은 sha": decl_sha,
                      "🔴 채점기가 인증한 sha": cert_sha,
                      "🔴🔴 디스크의 표를 다시 해시한 값(= 검증자가 얻는 값)": live_sha,
                      "🔴 셋이 같은가": ok_s}
    if not ok_s:
        bad.append("표 sha256")

    # ── 🔴🔴🔴 6 치환표의 채점 칸 == 채점 산출물의 채점 칸 (986 신설) ──
    six, six_bad, six_unread = sixth_cell(T, sc, s["cells"])
    ok6 = bool(not six_bad and not six_unread)
    rows["🔴🔴🔴 ⑥ 치환표의 채점 칸 == 채점 산출물의 채점 칸(986 신설)"] = {
        "🔴 분모(`SCORE_CELLS` 의 길이)": len(s["cells"]),
        "🔴 칸별": six,
        "🔴🔴 어긋난 칸": six_bad or "없음",
        "🔴 못 읽은 칸(= 「같다」가 아니다 · 조항 59)": six_unread or "없음",
        "🔴 전부 같은가": ok6,
        "⚠ 이 자의 한계(조항 61)":
            "🔴 **표에 «안 실린» 채점 칸은 원리상 못 본다** --- 그래서 분모를 여기 싣는다",
    }
    if not ok6:
        bad.append("⑥ 표 ↔ 채점기")

    return collections.OrderedDict([
        ("🔴 사이클", cycle),
        ("🔴🔴 문서를 어디서 읽었나",
         ("🔴 **커밋된 트리 `%s`** --- 986 이 «얹은» 정정이 이 자를 흔들지 못하게 "
          "«정정 이전의 바이트»로 잰다(티처 #124 즉시정정 ③: 985 의 「다섯 칸」의 "
          "정체는 `4 + 1` 이었고 다섯째는 985 «자신의» 편집이 만들었다)" % dref)
         if dref else "작업 트리(디스크)"),
        ("🔴 여섯 칸", rows),
        ("🔴🔴 어긋난 칸", bad or "없음"),
        ("🔴🔴🔴 수렴했나(여섯 칸이 전부 같다)", bool(not bad)),
    ])


def self_perturb():
    """🔴🔴🔴 **자기 입력 교란**(티처 #124 즉시정정 ⑤ · 986 신설).

    985 는 「같은 자를 984 에 물리면 떨어진다」로 검정력을 보였는데
    **그 다섯 칸 중 하나는 985 «자신의 편집»이 만든 것**이었다 --- 곧 그 시연은
    「남의 파일이 원래 어긋나 있었다」와 구별이 안 된다.

    🔴 **986 판**: **자기 판정문에 한 바이트를 더한 판**으로 같은 칸을 다시 재
    **`False` 가 나오는지**를 본다. 디스크는 **안 건드린다**(메모리에서만 잰다).
    """
    s = SPEC[986]
    sc = _json(s["score"]) or {}
    rd = sc.get(s["rule_d"]) or {}
    per = rd.get("🔴 대상별") or {}
    doc = s["docs"][0]
    txt = _read(doc)
    if txt is None:
        return {"🔴": "🔴 판정문이 아직 없다 --- 「떨어졌다」가 아니라 「모른다」다",
                "통과": bool(txt is not None)}
    cert = (per.get(doc) or {}).get("글자 수")
    live = len(txt)
    live_plus = len(txt + "​")            # 🔴 한 바이트(제로폭 공백)를 더한 «가짜» 판
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **자기 입력 교란** --- 자기 판정문에 한 글자를 더하면 자가 떨어지나"),
        ("🔴 대상", doc),
        ("🔴 인증한 글자 수", cert),
        ("🔴 실린 글자 수", live),
        ("🔴 한 글자 더한 가짜 판의 글자 수", live_plus),
        ("🔴 진짜 판에서 같은가", bool(cert is not None and cert == live)),
        ("🔴🔴🔴 가짜 판에서 «떨어지나»", bool(cert is not None and cert != live_plus)),
        ("🔴 왜 이 절이 있나",
         "🔴 **985 의 검정력 시연은 「984 의 파일이 원래 어긋나 있었다」와 구별이 안 됐다** "
         "--- 어긋난 다섯 칸 중 하나는 **985 자신의 편집**이 만든 것이었다(티처 #124). "
         "🔴 자기 입력을 교란하면 그 모호함이 사라진다"),
        ("통과", bool(cert is not None and cert != live_plus)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **교란한 입력에서 자가 «떨어지는가»** 하나다"),
    ])


def stage(ref):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    mine = certify(986)
    theirs = certify(985)
    out = collections.OrderedDict()
    out["무엇"] = "986 §2 — 🔴🔴🔴 **표 ↔ 채점기 ↔ 디스크 문서를 «여섯 칸»으로 잇는다**"
    out["🔴 축"] = "자기 자(문서 고리 수렴)"
    out["🔴 수렴의 정의(사전등록 §2-1 · 측정 전에 박았다)"] = [
        "① 판정문 글자 수", "② card 글자 수", "③ handoff 글자 수",
        "④ 치환표 칸 수", "⑤ 표 sha256",
        "🔴🔴🔴 ⑥ 치환표의 채점 칸 == 채점 산출물의 채점 칸(986 신설)",
        "🔴 여섯 칸이 «디스크의 실린 파일 실측»과 전부 같으면 수렴이다",
    ]
    out["§가 🔴🔴🔴 986 자신"] = collections.OrderedDict(
        list(mine.items()) + [
            ("통과", bool(mine["🔴🔴🔴 수렴했나(여섯 칸이 전부 같다)"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **채점기가 인증한 여섯 칸이 실린 파일·채점 산출물과 «전부» 같은가**"),
        ])
    out["§나 🔴🔴 검정력 시연 — 같은 여섯 칸 자를 985 에 문다(조항 64)"] = \
        collections.OrderedDict(list(theirs.items()) + [
            ("🔴🔴 985 에서 어긋난 칸 수",
             (len(theirs["🔴🔴 어긋난 칸"])
              if isinstance(theirs["🔴🔴 어긋난 칸"], list) else 0)),
            ("🔴🔴🔴 여섯째 칸이 985 에서 «떨어지나»",
             bool(isinstance(theirs["🔴🔴 어긋난 칸"], list)
                  and "⑥ 표 ↔ 채점기" in theirs["🔴🔴 어긋난 칸"])),
            ("🔴 이것이 이 사이클의 헤드라인이다",
             "🔴🔴🔴 **985 의 다섯 칸은 전부 초록이었다. 여섯째 칸만 떨어진다** --- "
             "곧 이 칸이 «없어서» 985 가 틀린 문서를 실었다"),
            ("통과", bool(theirs["🔴🔴🔴 수렴했나(여섯 칸이 전부 같다)"] is False)),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **이 자가 985 에서 «떨어지는가»** --- 안 떨어지면 자가 아니다"),
        ])
    out["§다 🔴 원장 고정점 지문"] = collections.OrderedDict([
        ("🔴 무엇", "🔴 **자기 항목을 뺀 원장의 sha256** --- 문서에 실을 수 있는 유일한 지문"),
        ("🔴 986 판", ledger_fixed_point("노트 986")),
        ("🔴 985 판(= 985 항목을 뺀 지금 원장)", ledger_fixed_point("노트 985")),
        ("통과", bool(ledger_fixed_point("노트 986"))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "고정점 지문을 «냈는가» 하나다"),
    ])
    out["§라 🔴🔴🔴 자기 입력 교란(986 신설)"] = self_perturb()
    out["통과"] = bool(out["§가 🔴🔴🔴 986 자신"]["통과"]
                     and out["§나 🔴🔴 검정력 시연 — 같은 여섯 칸 자를 985 에 문다(조항 64)"]["통과"]
                     and out["§다 🔴 원장 고정점 지문"]["통과"]
                     and out["§라 🔴🔴🔴 자기 입력 교란(986 신설)"]["통과"])
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
        "986 수렴": r["§가 🔴🔴🔴 986 자신"]["🔴🔴🔴 수렴했나(여섯 칸이 전부 같다)"],
        "986 어긋난 칸": r["§가 🔴🔴🔴 986 자신"]["🔴🔴 어긋난 칸"],
        "985 어긋난 칸": r["§나 🔴🔴 검정력 시연 — 같은 여섯 칸 자를 985 에 문다(조항 64)"][
            "🔴🔴 어긋난 칸"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
