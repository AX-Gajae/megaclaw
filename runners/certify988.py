#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""988 §2 — 🔴🔴🔴 **일곱 칸에 «여덟째»를 더한다 — 「등록한 판정식 == 채점기가 평가한 식」**.

987 판의 일곱 칸(판정문·card·handoff 글자 수 · 치환표 칸 수 · 표 sha256 ·
⑥ 치환표의 채점 칸 == 채점 산출물의 채점 칸 · ⑦ 사전등록 정본 값)에 **여덟째**를 더한다:

> **⑧ 사전등록 §5 의 「맞았다의 정의」 == 채점기가 그 예측에 대해 «실제로 평가한» 식**

🔴 **왜 (티처 #126 C1).** **987 의 최상위 통과 `True` 는 거짓이다.**
등록된 P6 의 정의는 `명부판 §3 통과 = False` 인데 `score987.py:812` 가
`ok6 = bool(isinstance(sink, list) and sink)` 로 **그 식을 아예 계산하지 않았다.**
🔴 **일곱째 칸은 「값」의 교체만 잡는다 --- 이것은 「판정식」의 교체라 값 대조로는
원리상 못 잡는다.**

🔴 **즉시 정정(티처 #126)**: **일곱째 칸을 「985 에도」 문다** ---
「986 «에서만» 떨어진다」는 미검증이었다.

씀:
    python3 runners/certify988.py --stage certify --ref <40자 sha>
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

import cycle988 as CY                                   # noqa: E402
import cycle987 as C7                                   # noqa: E402
import cycle986 as C6                                   # noqa: E402

OUT = "runners/out988_certify.json"
TABLE_KEY = "🔴🔴 치환표"
CELLS_KEY = "🔴 칸"
DEN = "data/lab/denominator.json"

#: 🔴 **사전등록 §8 의 이름 → 이 사이클 산출물의 키 경로**(일곱째 칸의 정의).
CANON_PATH = {
    "987 예측 분자":
        ("runners/out988_score.json",
         ["§17 🔴🔴🔴 지연 없는 일곱째 칸(사전등록 정본)", "🔴 칸별", "987 예측 분자",
          "🔴 산출물이 낸 값"]),
    "987 최상위 통과":
        ("runners/out988_score.json",
         ["§17 🔴🔴🔴 지연 없는 일곱째 칸(사전등록 정본)", "🔴 칸별", "987 최상위 통과",
          "🔴 산출물이 낸 값"]),
    "987 audit §C 986 절 3 통과":
        ("runners/out988_score.json",
         ["§17 🔴🔴🔴 지연 없는 일곱째 칸(사전등록 정본)", "🔴 칸별",
          "987 audit §C 986 절 3 통과", "🔴 산출물이 낸 값"]),
    "987 §K 센 한글 수사 수":
        ("runners/out988_score.json",
         ["§17 🔴🔴🔴 지연 없는 일곱째 칸(사전등록 정본)", "🔴 칸별", "987 §K 센 한글 수사 수",
          "🔴 산출물이 낸 값"]),
    "987 §K 바늘이 걸린 수사 수":
        ("runners/out988_score.json",
         ["§17 🔴🔴🔴 지연 없는 일곱째 칸(사전등록 정본)", "🔴 칸별",
          "987 §K 바늘이 걸린 수사 수", "🔴 산출물이 낸 값"]),
    "987 §K 값 대조 어긋남 수":
        ("runners/out988_score.json",
         ["§17 🔴🔴🔴 지연 없는 일곱째 칸(사전등록 정본)", "🔴 칸별",
          "987 §K 값 대조 어긋남 수", "🔴 산출물이 낸 값"]),
    "987 산문 등록 안 된 주장 문장 수":
        ("runners/out988_score.json",
         ["§17 🔴🔴🔴 지연 없는 일곱째 칸(사전등록 정본)", "🔴 칸별",
          "987 산문 등록 안 된 주장 문장 수", "🔴 산출물이 낸 값"]),
    "986 예측 분자":
        ("runners/out988_score.json",
         ["§17 🔴🔴🔴 지연 없는 일곱째 칸(사전등록 정본)", "🔴 칸별", "986 예측 분자",
          "🔴 산출물이 낸 값"]),
}

#: 🔴🔴 **987 의 사전등록 정본**(`docs/prereg_987_…` §8 표) --- 검정력 시연용.
CANON_987 = collections.OrderedDict([
    ("985 치환표 칸 소.전량", (446, "소.446")),
    ("985 치환표 칸 소.원장뺀", (349, "소.349")),
    ("986 ⑤′ 절 3 대상 파일 수", (8, "전.986절3대상")),
])
#: 🔴🔴 **986 의 사전등록 정본** --- 987 이 「986 에서 떨어진다」를 보인 그 자리.
CANON_986 = collections.OrderedDict([
    ("⑤′ 절 1 소비자(정본)", (446, "오.소비자정본")),
    ("⑤′ 절 1 소비자(원장 뺀)", (349, "오.소비자원장뺀")),
])
#: 🔴🔴🔴 **즉시 정정 --- 985 에도 문다.** 985 사전등록은 정본을 `415 → 414` 로 박았고
#:  985 치환표는 `446 / 349` 다. **「986 에서만 떨어진다」는 미검증이었다.**
CANON_985 = collections.OrderedDict([
    ("⑤′ 절 1 소비자(정본)", (415, "소.전량")),
    ("⑤′ 절 1 소비자(원장 뺀)", (414, "소.원장뺀")),
])

SCORE_CELLS_987 = dict(C7.SCORE_CELLS)
SCORE_CELLS_986 = dict(C6.SCORE_CELLS)

SPEC = {
    988: {"table": "runners/out988_table.json",
          "score": "runners/out988_score.json",
          "rule_d": "§D 🔴 규칙 D 감사(분모 여섯)",
          "docs": ("docs/판정_988.md", "docs/card_988.md", "docs/handoff_988.md"),
          "cells": CY.SCORE_CELLS,
          "canon": None,
          "ledger_key": "노트 988"},
    987: {"table": "runners/out987_table.json",
          "score": "runners/out987_score.json",
          "rule_d": "§D 🔴 규칙 D 감사(분모 여섯)",
          "docs": ("docs/판정_987.md", "docs/card_987.md", "docs/handoff_987.md"),
          "cells": SCORE_CELLS_987,
          "canon": CANON_987,
          "doc_ref": CY.REF_987,
          "ledger_key": "노트 987"},
    986: {"table": "runners/out986_table.json",
          "score": "runners/out986_score.json",
          "rule_d": "§D 🔴 규칙 D 감사(분모 여섯)",
          "docs": ("docs/판정_986.md", "docs/card_986.md", "docs/handoff_986.md"),
          "cells": SCORE_CELLS_986,
          "canon": CANON_986,
          "doc_ref": CY.REF_986,
          "ledger_key": "노트 986"},
    985: {"table": "runners/out985_table.json",
          "score": "runners/out985_score.json",
          "rule_d": "§D 🔴 규칙 D 감사(분모 다섯)",
          "docs": ("docs/판정_985.md", "docs/card_985.md", "docs/handoff_985.md"),
          "cells": {},
          "canon": CANON_985,
          "doc_ref": CY.REF_985,
          "ledger_key": "노트 985"},
}


def _read(rel, ref=None):
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


def seventh_cell_988():
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


def seventh_cell_other(cycle):
    """🔴🔴 **검정력 시연** --- 같은 일곱째 칸을 987·986·**985** 에 문다."""
    s = SPEC[cycle]
    tb = _json(s["table"], s.get("doc_ref"))
    T, _n = _cells(tb)
    rows, bad = collections.OrderedDict(), []
    for name, (want, cell) in (s["canon"] or {}).items():
        live = (T or {}).get(cell)
        ok = bool(want == live)
        rows[name] = {"🔴 %d 사전등록이 박은 값" % cycle: want,
                      "🔴 %d 치환표 칸(`%s`)" % (cycle, cell): live, "🔴 같은가": ok}
        if not ok:
            bad.append(name)
    return rows, bad


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 ⑧ 등록한 판정식 == 채점기가 평가한 식
# ══════════════════════════════════════════════════════════════════════
def eighth_cell():
    import audit988 as A8                                          # noqa: E402
    au = _json("runners/out988_audit.json") or {}
    B = au.get("§B 🔴🔴🔴 여덟째 칸 — 등록 판정식 대조") or {}
    mine = B.get("🔴🔴 988 자신에 문다(㉠ 엄격)") or {}
    theirs = B.get("🔴🔴🔴 987 에 문다(검정력 시연 · 조항 64)") or {}
    same = mine.get("🔴🔴🔴 ㉠ 두 집합이 같은가")
    mine_bad = mine.get("🔴🔴 어긋난 예측 수")
    _ = A8
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **사전등록 §5 의 「맞았다의 정의」 == 채점기가 «실제로 평가한» 식**"),
        ("🔴🔴 ㉠ 사전등록 키 경로 집합", mine.get("🔴🔴🔴 ㉠ 엄격 — 사전등록 키 경로 집합")),
        ("🔴🔴 ㉠ 선언표 `PRED_DEF` 키 경로 집합",
         mine.get("🔴🔴🔴 ㉠ 엄격 — 선언표 `PRED_DEF` 키 경로 집합")),
        ("🔴🔴🔴 ㉠ 두 집합이 같은가", same),
        ("🔴 사전등록에만 있는 키 경로", mine.get("🔴 ㉠ 사전등록에만 있는 키 경로")),
        ("🔴 선언표에만 있는 키 경로", mine.get("🔴 ㉠ 선언표에만 있는 키 경로")),
        ("🔴 988 자신에서 ㉡·㉢ 로 어긋난 예측 수", mine_bad),
        ("🔴🔴 987 에서 어긋난 예측", theirs.get("🔴🔴 어긋난 예측")),
        ("🔴🔴 987 에서 어긋난 예측 수", theirs.get("🔴🔴 어긋난 예측 수")),
        ("🔴🔴🔴 전부 같은가", bool(same is True and (mine_bad or 0) == 0)),
    ])


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
    ok6 = bool(s["cells"] and not six_bad and not six_unread)
    rows["🔴🔴 ⑥ 치환표의 채점 칸 == 채점 산출물의 채점 칸(986 신설)"] = {
        "🔴 분모(그 사이클 표에서 «풀리는» 칸 수)": len(s["cells"]),
        "🔴 칸별": six,
        "🔴🔴 어긋난 칸": six_bad or "없음",
        "🔴 못 읽은 칸(= 「같다」가 아니다 · 조항 59)": six_unread or "없음",
        "🔴 전부 같은가": ok6,
    }
    if not ok6:
        bad.append("⑥ 표 ↔ 채점기")

    if cycle == 988:
        sev, sev_bad, sev_unread = seventh_cell_988()
        ok7 = bool(not sev_bad and not sev_unread)
        rows["🔴🔴🔴 ⑦ 사전등록이 박은 정본 값 == 산출물의 그 칸(987 신설)"] = {
            "🔴 분모(사전등록 §8 의 칸 수)": len(CY.PREREG_CANON),
            "🔴 칸별": sev, "🔴🔴 어긋난 칸": sev_bad or "없음",
            "🔴 못 읽은 칸": sev_unread or "없음", "🔴 전부 같은가": ok7,
        }
    else:
        sev, sev_bad = seventh_cell_other(cycle)
        ok7 = bool(not sev_bad)
        rows["🔴🔴🔴 ⑦ 사전등록이 박은 정본 값 == 산출물의 그 칸(987 신설)"] = {
            "🔴 분모(%d 사전등록의 칸 수)" % cycle: len(s["canon"] or {}),
            "🔴 칸별": sev, "🔴🔴 어긋난 칸": sev_bad or "없음", "🔴 전부 같은가": ok7,
        }
    if not ok7:
        bad.append("⑦ 사전등록 ↔ 산출물")

    return collections.OrderedDict([
        ("🔴 사이클", cycle),
        ("🔴🔴 문서를 어디서 읽었나",
         ("🔴 **커밋된 트리 `%s`**" % dref) if dref else "작업 트리(디스크)"),
        ("🔴 칸별", rows),
        ("🔴🔴 어긋난 칸", bad or "없음"),
        ("🔴🔴🔴 수렴했나", bool(not bad)),
    ])


def self_perturb():
    s = SPEC[988]
    sc = _json(s["score"]) or {}
    rd = sc.get(s["rule_d"]) or {}
    per = rd.get("🔴 대상별") or {}
    doc = s["docs"][0]
    txt = _read(doc)
    if txt is None:
        return {"🔴": "🔴 판정문이 아직 없다 --- 「떨어졌다」가 아니라 「모른다」다",
                "통과": bool(txt)}
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
    mine = certify(988)
    out = collections.OrderedDict()
    out["무엇"] = "988 §2 — 🔴🔴🔴 **표 ↔ 채점기 ↔ 문서 ↔ 사전등록 ↔ «판정식»을 «여덟 칸»으로**"
    out["🔴 축"] = "자기 자(문서 고리 수렴)"
    out["🔴 수렴의 정의(사전등록 §2-2 · 측정 전에 박았다)"] = [
        "① 판정문 글자 수", "② card 글자 수", "③ handoff 글자 수",
        "④ 치환표 칸 수", "⑤ 표 sha256",
        "⑥ 치환표의 채점 칸 == 채점 산출물의 채점 칸(986 신설)",
        "⑦ 사전등록 §8 이 박은 정본 값 == 산출물의 그 칸(987 신설)",
        "🔴🔴🔴 ⑧ 등록한 「맞았다의 정의」 == 채점기가 «실제로 평가한» 식(988 신설)",
    ]
    e8 = eighth_cell()
    out["§가 🔴🔴🔴 988 자신"] = collections.OrderedDict(
        list(mine.items()) + [
            ("🔴🔴🔴 ⑧ 등록한 판정식 == 채점기가 평가한 식", e8),
            ("통과", bool(mine["🔴🔴🔴 수렴했나"] and e8["🔴🔴🔴 전부 같은가"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **여덟 칸이 실린 파일·채점 산출물·사전등록·판정식과 «전부» 같은가**"),
        ])
    KN = "§나 🔴🔴 검정력 시연 — 같은 여덟 칸 자를 987·986·985 에 문다(조항 64)"
    others = collections.OrderedDict()
    for c in (987, 986, 985):
        others["%d" % c] = certify(c)
    fell7 = {c: ("⑦ 사전등록 ↔ 산출물" in (others["%d" % c]["🔴🔴 어긋난 칸"]
                                     if isinstance(others["%d" % c]["🔴🔴 어긋난 칸"], list)
                                     else []))
             for c in (987, 986, 985)}
    out[KN] = collections.OrderedDict([
        ("🔴 사이클별", others),
        ("🔴🔴 일곱째 칸이 «떨어진» 사이클", {str(k): v for k, v in fell7.items()}),
        ("🔴🔴🔴 즉시 정정 — 「986 «에서만» 떨어진다」가 참인가",
         bool(fell7[986] and not fell7[985] and not fell7[987])),
        ("🔴 왜 985 에도 무나",
         "🔴 **987 은 「일곱째 칸이 986 에서 떨어진다」만 보였고 「986 에서만」은 «미검증»이었다.** "
         "985 사전등록은 정본을 `415 → 414` 로 박았고 985 치환표는 `446 / 349` 다 --- "
         "**985 에도 떨어질 개연이 크다**(티처 #126 즉시정정)"),
        ("🔴🔴🔴 여덟째 칸이 987 에서 «떨어지나»",
         bool((e8.get("🔴🔴 987 에서 어긋난 예측 수") or 0) >= 1)),
        ("🔴🔴 987 에서 여덟째 칸이 잡은 예측", e8.get("🔴🔴 987 에서 어긋난 예측")),
        ("통과", bool((e8.get("🔴🔴 987 에서 어긋난 예측 수") or 0) >= 1)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **여덟째 칸이 987 에서 «떨어지는가»** --- 안 떨어지면 자가 아니다"),
    ])
    out["§다 🔴 원장 고정점 지문"] = collections.OrderedDict([
        ("🔴 무엇", "🔴 **자기 항목을 뺀 원장의 sha256** --- 문서에 실을 수 있는 유일한 지문"),
        ("🔴 988 판", ledger_fixed_point("노트 988")),
        ("🔴 987 판", ledger_fixed_point("노트 987")),
        ("통과", bool(ledger_fixed_point("노트 988"))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "고정점 지문을 «냈는가» 하나다"),
    ])
    out["§라 🔴🔴 자기 입력 교란"] = self_perturb()
    out["§마 🔴🔴🔴 ⑧ 등록한 판정식 == 채점기가 평가한 식(988 신설)"] = collections.OrderedDict(
        list(e8.items()) + [
            ("통과", bool(e8["🔴🔴🔴 전부 같은가"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **등록한 판정식과 채점기가 평가한 식의 «키 경로 집합»이 같은가**"),
        ])
    out["통과"] = bool(out["§가 🔴🔴🔴 988 자신"]["통과"] and out[KN]["통과"]
                     and out["§다 🔴 원장 고정점 지문"]["통과"]
                     and out["§라 🔴🔴 자기 입력 교란"]["통과"]
                     and out["§마 🔴🔴🔴 ⑧ 등록한 판정식 == 채점기가 평가한 식(988 신설)"]["통과"])
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["certify"])
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    r = stage(a.ref)
    KN = "§나 🔴🔴 검정력 시연 — 같은 여덟 칸 자를 987·986·985 에 문다(조항 64)"
    print(json.dumps({
        "통과": r["통과"],
        "988 수렴": r["§가 🔴🔴🔴 988 자신"]["🔴🔴🔴 수렴했나"],
        "988 어긋난 칸": r["§가 🔴🔴🔴 988 자신"]["🔴🔴 어긋난 칸"],
        "일곱째가 떨어진 사이클": r[KN]["🔴🔴 일곱째 칸이 «떨어진» 사이클"],
        "여덟째가 987 에서 떨어지나": r[KN]["🔴🔴🔴 여덟째 칸이 987 에서 «떨어지나»"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
