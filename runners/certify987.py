#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""987 §3 — 🔴🔴🔴 **여섯 칸에 «일곱째»를 더한다 — 「사전등록이 박은 값 == 채점이 낸 값」**.

986 판의 여섯 칸(판정문·카드·handoff 글자 수 · 치환표 칸 수 · 표 sha256 ·
🔴 치환표의 채점 칸 == 채점 산출물의 채점 칸)에 **일곱째**를 더한다:

> **⑦ 사전등록 §8 이 박은 「정본 값」 == 이 사이클 산출물의 그 칸**

🔴 **왜 (티처 #125 2순위 ⓒ).** **986 은 사전등록 `:98` 에 정본을 `446 → 349` 로 등록해
놓고 판정문·원장에 `415 → 414` 를 실었다.** 🔴 **반증조건 3 이 「분모 넷」만 봐서
「등록된 «값»」의 교체를 원리상 못 봤고, 사전등록 자체가 규칙 D 여섯 대상이 아니라
아무 자도 안 본다.**

🔴 **검정력 시연(조항 64)**: 같은 일곱째 칸을 **986 에 물리면 «떨어진다»** ---
986 의 치환표 칸 `오.소비자정본` 은 **415** 이고 사전등록이 박은 정본은 **446** 이다.

씀:
    python3 runners/certify987.py --stage certify --ref <40자 sha>
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

import cycle987 as CY                                   # noqa: E402
import cycle986 as C6                                   # noqa: E402

OUT = "runners/out987_certify.json"
TABLE_KEY = "🔴🔴 치환표"
CELLS_KEY = "🔴 칸"
DEN = "data/lab/denominator.json"

#: 🔴 **사전등록 §8 의 이름 → 이 사이클 산출물의 키 경로**(일곱째 칸의 정의).
CANON_PATH = {
    "985 치환표 칸 소.전량":
        ("runners/out987_audit.json",
         ["§B 🔴🔴🔴 985 가 한 이름으로 두 범위를 쟀다", "🔴🔴🔴 그 반박이 참인가",
          "985 치환표 칸 `소.전량`"]),
    "985 치환표 칸 소.원장뺀":
        ("runners/out987_audit.json",
         ["§B 🔴🔴🔴 985 가 한 이름으로 두 범위를 쟀다", "🔴🔴🔴 그 반박이 참인가",
          "985 치환표 칸 `소.원장뺀`"]),
    "985 fiveprime §1 분모 ②":
        ("runners/out987_audit.json",
         ["§B 🔴🔴🔴 985 가 한 이름으로 두 범위를 쟀다",
          "🔴🔴🔴 진짜 병 — 같은 이름 · 다른 범위", "`fiveprime_985.json §1` 의 값"]),
    "985 audit §C 분모 ②":
        ("runners/out987_audit.json",
         ["§B 🔴🔴🔴 985 가 한 이름으로 두 범위를 쟀다",
          "🔴🔴🔴 진짜 병 — 같은 이름 · 다른 범위", "`out985_audit.json §C` 의 값"]),
    "986 판정문의 「985 문서 수」 잰 값":
        ("runners/out987_audit.json",
         ["§B-나 🔴🔴 986 문서의 한글 수사 「985 의 다섯 문서」",
          "🔴🔴🔴 잰 값(`out986_audit §A/①`)"]),
    "986 ⑤′ 절 3 대상 파일 수":
        ("runners/out987_audit.json",
         ["§C 🔴🔴 `⑤′` 절 3 을 고정 명부로 다시 낸다", "🔴 986 절 3 대상 수(고정 ref)"]),
    "985 ⑤′ 절 3 대상 파일 수":
        ("runners/out987_audit.json",
         ["§C 🔴🔴 `⑤′` 절 3 을 고정 명부로 다시 낸다", "🔴 985 절 3 대상 수(고정 ref)"]),
}

#: 🔴🔴 **986 의 사전등록 정본**(`docs/prereg_986_sixth_cell_power_ci.md` §2-4 표) ---
#:  **검정력 시연용**이다. 🔴 이 두 수는 «사전등록 문서에서 읽은 것»이고 986 은
#:  판정문·원장에 `415 → 414` 를 실었다.
CANON_986 = collections.OrderedDict([
    ("⑤′ 절 1 소비자(정본)", (446, "오.소비자정본")),
    ("⑤′ 절 1 소비자(원장 뺀)", (349, "오.소비자원장뺀")),
])

SCORE_CELLS_986 = dict(C6.SCORE_CELLS)

SPEC = {
    987: {"table": "runners/out987_table.json",
          "score": "runners/out987_score.json",
          "rule_d": "§D 🔴 규칙 D 감사(분모 여섯)",
          "docs": ("docs/판정_987.md", "docs/card_987.md", "docs/handoff_987.md"),
          "cells": CY.SCORE_CELLS,
          "ledger_key": "노트 987"},
    986: {"table": "runners/out986_table.json",
          "score": "runners/out986_score.json",
          "rule_d": "§D 🔴 규칙 D 감사(분모 여섯)",
          "docs": ("docs/판정_986.md", "docs/card_986.md", "docs/handoff_986.md"),
          "cells": SCORE_CELLS_986,
          #: 🔴🔴🔴 **986 문서는 «986 이 끝난 트리»에서 읽는다** --- 987 이 «얹는»
          #:  정정이 이 자를 흔들지 못하게 «정정 이전의 바이트»로 잰다.
          "doc_ref": CY.REF_986,
          "ledger_key": "노트 986"},
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


def _json(rel, ref=None):
    t = _read(rel, ref)
    return json.loads(t, object_pairs_hook=collections.OrderedDict) if t else None


def _cells(tb):
    t = (tb or {}).get(TABLE_KEY)
    if isinstance(t, dict) and CELLS_KEY in t:
        return t[CELLS_KEY], t.get("🔴 칸 수")
    return t, None


def table_sha(T):
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


def seventh_cell_987():
    """🔴🔴🔴 **⑦ 사전등록 §8 이 박은 「정본 값」 == 이 사이클 산출물의 그 칸.**"""
    rows, bad, unread = collections.OrderedDict(), [], []
    cache = {}
    for name, want in CY.PREREG_CANON.items():
        rel, path = CANON_PATH[name]
        if rel not in cache:
            cache[rel] = _json(rel)
        got, live = CY.resolve(cache[rel] or {}, path)
        if not got:
            rows[name] = {"🔴 사전등록이 박은 값": want,
                          "🔴": "🔴 산출물에 그 키 경로가 «없다»(= 「같다」가 아니다)",
                          "산출물": rel, "키 경로": path}
            unread.append(name)
            continue
        ok = bool(want == live)
        rows[name] = {"🔴 사전등록이 박은 값": want, "🔴 산출물이 낸 값": live,
                      "🔴 산출물": rel, "🔴 같은가": ok}
        if not ok:
            bad.append(name)
    return rows, bad, unread


def seventh_cell_986():
    """🔴🔴 **검정력 시연 --- 같은 일곱째 칸을 986 에 문다.**

    986 의 사전등록 §2-4 는 정본을 **`446 → 349`** 로 박았는데
    치환표·판정문·원장은 **`415 → 414`** 를 실었다.
    """
    tb = _json(SPEC[986]["table"], SPEC[986]["doc_ref"])
    T, _n = _cells(tb)
    rows, bad = collections.OrderedDict(), []
    for name, (want, cell) in CANON_986.items():
        live = (T or {}).get(cell)
        ok = bool(want == live)
        rows[name] = {"🔴 986 사전등록이 박은 값": want,
                      "🔴 986 치환표 칸(`%s`)" % cell: live, "🔴 같은가": ok}
        if not ok:
            bad.append(name)
    return rows, bad


def certify(cycle):
    s = SPEC[cycle]
    dref = s.get("doc_ref")
    tb = _json(s["table"], dref)
    sc = _json(s["score"], dref)
    rows, bad = collections.OrderedDict(), []

    for p in s["docs"]:
        txt = _read(p, dref)
        live = len(txt) if txt is not None else None
        rd = (sc or {}).get(s["rule_d"]) or {}
        per = rd.get("🔴 대상별") or {}
        cert = (per.get(p) or {}).get("글자 수")
        ok = bool(live is not None and cert is not None and live == cert)
        rows[p] = {"🔴 인증한 글자 수(채점기가 본 것)": cert,
                   "🔴 실린 글자 수(실측)": live, "🔴 같은가": ok}
        if not ok:
            bad.append(p)

    rd = (sc or {}).get(s["rule_d"]) or {}
    T, _inner = _cells(tb)
    live_n = len(T) if isinstance(T, dict) else None
    decl_n = (tb or {}).get("🔴🔴 칸 수")
    cert_n = rd.get("🔴 치환표 칸 수")
    ok_n = bool(live_n is not None and decl_n == live_n and cert_n == live_n)
    rows["치환표 칸 수"] = {"🔴 표가 스스로 적은 칸 수": decl_n,
                      "🔴 채점기가 인증한 칸 수": cert_n,
                      "🔴🔴 실제 표 키 수": live_n, "🔴 셋이 같은가": ok_n}
    if not ok_n:
        bad.append("치환표 칸 수")

    live_sha = table_sha(T) if isinstance(T, dict) else None
    decl_sha = (tb or {}).get("🔴🔴 표 sha256")
    cert_sha = rd.get("🔴 치환표 sha256")
    ok_s = bool(live_sha and decl_sha == live_sha and cert_sha == live_sha)
    rows["표 sha256"] = {"🔴 표가 스스로 적은 sha": decl_sha,
                      "🔴 채점기가 인증한 sha": cert_sha,
                      "🔴🔴 다시 해시한 값": live_sha, "🔴 셋이 같은가": ok_s}
    if not ok_s:
        bad.append("표 sha256")

    six, six_bad, six_unread = sixth_cell(T, sc, s["cells"])
    ok6 = bool(not six_bad and not six_unread)
    rows["🔴🔴 ⑥ 치환표의 채점 칸 == 채점 산출물의 채점 칸(986 신설)"] = {
        #: 🔴 **즉시 정정 ⑤ --- 986 의 키 이름이 「분모(`SCORE_CELLS` 의 길이)」였다.**
        #:  985 에 물리면 8 을 내서 「986 판 분모」로 읽힌다. 실제 뜻은 아래 이름이다.
        "🔴 분모(그 사이클 표에서 «풀리는» 칸 수)": len(s["cells"]),
        "🔴 칸별": six,
        "🔴🔴 어긋난 칸": six_bad or "없음",
        "🔴 못 읽은 칸(= 「같다」가 아니다 · 조항 59)": six_unread or "없음",
        "🔴 전부 같은가": ok6,
        "⚠ 이 자의 한계(조항 61)":
            "🔴 **표에 «안 실린» 채점 칸은 원리상 못 본다** --- 그래서 분모를 여기 싣는다",
    }
    if not ok6:
        bad.append("⑥ 표 ↔ 채점기")

    if cycle == 987:
        sev, sev_bad, sev_unread = seventh_cell_987()
        ok7 = bool(not sev_bad and not sev_unread)
        rows["🔴🔴🔴 ⑦ 사전등록이 박은 정본 값 == 산출물의 그 칸(987 신설)"] = {
            "🔴 분모(사전등록 §8 의 칸 수)": len(CY.PREREG_CANON),
            "🔴 칸별": sev, "🔴🔴 어긋난 칸": sev_bad or "없음",
            "🔴 못 읽은 칸": sev_unread or "없음", "🔴 전부 같은가": ok7,
        }
    else:
        sev, sev_bad = seventh_cell_986()
        ok7 = bool(not sev_bad)
        rows["🔴🔴🔴 ⑦ 사전등록이 박은 정본 값 == 산출물의 그 칸(987 신설)"] = {
            "🔴 분모(986 사전등록 §2-4 의 칸 수)": len(CANON_986),
            "🔴 칸별": sev, "🔴🔴 어긋난 칸": sev_bad or "없음", "🔴 전부 같은가": ok7,
            "🔴🔴🔴 이것이 검정력 시연이다":
                "🔴 **986 은 사전등록에 정본을 `446 → 349` 로 박아 놓고 "
                "치환표·판정문·원장에 `415 → 414` 를 실었다.** "
                "🔴 **986 의 어떤 자도 이것을 못 봤다** --- 반증조건 3 은 「분모 넷」만 본다",
        }
    if not ok7:
        bad.append("⑦ 사전등록 ↔ 산출물")

    return collections.OrderedDict([
        ("🔴 사이클", cycle),
        ("🔴🔴 문서를 어디서 읽었나",
         ("🔴 **커밋된 트리 `%s`** --- 987 이 «얹은» 정정이 이 자를 흔들지 못하게 "
          "«정정 이전의 바이트»로 잰다" % dref) if dref else "작업 트리(디스크)"),
        ("🔴 일곱 칸", rows),
        ("🔴🔴 어긋난 칸", bad or "없음"),
        ("🔴🔴🔴 수렴했나(일곱 칸이 전부 같다)", bool(not bad)),
    ])


def self_perturb():
    """🔴🔴🔴 **자기 입력 교란**(986 이 만든 자를 그대로 쓴다)."""
    s = SPEC[987]
    sc = _json(s["score"]) or {}
    rd = sc.get(s["rule_d"]) or {}
    per = rd.get("🔴 대상별") or {}
    doc = s["docs"][0]
    txt = _read(doc)
    if txt is None:
        return {"🔴": "🔴 판정문이 아직 없다 --- 「떨어졌다」가 아니라 「모른다」다",
                "통과": False}
    cert = (per.get(doc) or {}).get("글자 수")
    live = len(txt)
    live_plus = len(txt + "​")
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **자기 입력 교란** --- 자기 판정문에 한 글자를 더하면 자가 떨어지나"),
        ("🔴 대상", doc),
        ("🔴 인증한 글자 수", cert),
        ("🔴 실린 글자 수", live),
        ("🔴 한 글자 더한 가짜 판의 글자 수", live_plus),
        ("🔴 진짜 판에서 같은가", bool(cert is not None and cert == live)),
        ("🔴🔴🔴 가짜 판에서 «떨어지나»", bool(cert is not None and cert != live_plus)),
        ("통과", bool(cert is not None and cert != live_plus)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **교란한 입력에서 자가 «떨어지는가»** 하나다"),
    ])


def stage(ref):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    mine = certify(987)
    theirs = certify(986)
    out = collections.OrderedDict()
    out["무엇"] = "987 §3 — 🔴🔴🔴 **표 ↔ 채점기 ↔ 디스크 문서 ↔ «사전등록»을 «일곱 칸»으로**"
    out["🔴 축"] = "자기 자(문서 고리 수렴)"
    out["🔴 수렴의 정의(사전등록 §3-3 · 측정 전에 박았다)"] = [
        "① 판정문 글자 수", "② card 글자 수", "③ handoff 글자 수",
        "④ 치환표 칸 수", "⑤ 표 sha256",
        "⑥ 치환표의 채점 칸 == 채점 산출물의 채점 칸(986 신설)",
        "🔴🔴🔴 ⑦ 사전등록 §8 이 박은 정본 값 == 산출물의 그 칸(987 신설)",
    ]
    out["§가 🔴🔴🔴 987 자신"] = collections.OrderedDict(
        list(mine.items()) + [
            ("통과", bool(mine["🔴🔴🔴 수렴했나(일곱 칸이 전부 같다)"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **채점기가 인증한 일곱 칸이 실린 파일·채점 산출물·사전등록과 «전부» 같은가**"),
        ])
    KN = "§나 🔴🔴 검정력 시연 — 같은 일곱 칸 자를 986 에 문다(조항 64)"
    out[KN] = collections.OrderedDict(list(theirs.items()) + [
        ("🔴🔴 986 에서 어긋난 칸 수",
         (len(theirs["🔴🔴 어긋난 칸"]) if isinstance(theirs["🔴🔴 어긋난 칸"], list) else 0)),
        ("🔴🔴🔴 일곱째 칸이 986 에서 «떨어지나»",
         bool(isinstance(theirs["🔴🔴 어긋난 칸"], list)
              and "⑦ 사전등록 ↔ 산출물" in theirs["🔴🔴 어긋난 칸"])),
        ("🔴 이것이 이 절의 헤드라인이다",
         "🔴🔴🔴 **986 의 여섯 칸은 자기 자신에게 전부 초록이었다. 일곱째 칸만 떨어진다** --- "
         "곧 이 칸이 «없어서» 986 이 사전등록 정본을 사이클 중에 갈아 끼우고도 초록이었다"),
        ("통과", bool(theirs["🔴🔴🔴 수렴했나(일곱 칸이 전부 같다)"] is False)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **이 자가 986 에서 «떨어지는가»** --- 안 떨어지면 자가 아니다"),
    ])
    out["§다 🔴 원장 고정점 지문"] = collections.OrderedDict([
        ("🔴 무엇", "🔴 **자기 항목을 뺀 원장의 sha256** --- 문서에 실을 수 있는 유일한 지문"),
        ("🔴 987 판", ledger_fixed_point("노트 987")),
        ("🔴 986 판", ledger_fixed_point("노트 986")),
        ("통과", bool(ledger_fixed_point("노트 987"))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "고정점 지문을 «냈는가» 하나다"),
    ])
    out["§라 🔴🔴 자기 입력 교란"] = self_perturb()
    out["통과"] = bool(out["§가 🔴🔴🔴 987 자신"]["통과"] and out[KN]["통과"]
                     and out["§다 🔴 원장 고정점 지문"]["통과"]
                     and out["§라 🔴🔴 자기 입력 교란"]["통과"])
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["certify"])
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    r = stage(a.ref)
    KN = "§나 🔴🔴 검정력 시연 — 같은 일곱 칸 자를 986 에 문다(조항 64)"
    print(json.dumps({
        "통과": r["통과"],
        "987 수렴": r["§가 🔴🔴🔴 987 자신"]["🔴🔴🔴 수렴했나(일곱 칸이 전부 같다)"],
        "987 어긋난 칸": r["§가 🔴🔴🔴 987 자신"]["🔴🔴 어긋난 칸"],
        "986 어긋난 칸": r[KN]["🔴🔴 어긋난 칸"],
        "일곱째가 986 에서 떨어지나": r[KN]["🔴🔴🔴 일곱째 칸이 986 에서 «떨어지나»"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
