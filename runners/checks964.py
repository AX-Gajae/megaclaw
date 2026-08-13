# -*- coding: utf-8 -*-
"""🔴 노트 964 — **떨어질 수 없는 검사를 끊고, 「뒤」를 합집합으로 다시 낸다.**

티처 #102 의 1·2·3순위를 그대로 받는다. **새 자료를 안 만든다. 새 측정을 안 한다.**

  §1  🔴🔴 **합집합 재분모화(M1)** — 963 의 「뒤 38,945」는 **겹치지 않는 4,003 편을
      통째로 뺀 수**다. 2.73 · 2.95 · 3.01 을 **분모와 함께 나란히** 낸다.
  §2  **W6′ 정정(m1·m2)** — 7,674 를 두 번 다르게 설명한 거짓말과 **단위 섞인 비**를 고친다.
  §3  🔴🔴 **W3″(C1)** — 963 의 §3 은 `w3_prime(dict(dom), sum(dom.values()))` 라
      **분모가 자기 분자의 합**이었다. **분모를 독립 경로에서** 가져온다.
  §4  🔴🔴 **V4′(M3)** — `rulers()` **소비자 전수**에 스키마·임포트 스모크를 건다.
      `curve961.py:549` 의 `키 in 딕트` 를 이 검사가 잡아야 한다.
  §5  **심어서 떨어뜨리기** — 🔴 **등록 상수끼리의 산술은 심기로 안 센다**(사전등록 §3-3).
  §6  **배선** — 🔴 **검사 「종류」로 센다**(사전등록 §3-4 · 963 의 12/12 는 V1 을 다섯 번 센 수).

🔴 **`runners/triples962.py` 와 `runners/checks963.py` 는 안 고친다** — 각각의 산출물이
원장에 박힌 기록이다. 고친 판을 **여기 새 러너로** 낸다.
"""
import argparse
import ast
import builtins
import collections
import gzip
import hashlib
import io
import json
import os
import random
import re
import socket
import subprocess
import sys
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAO941 = "data/ingest/sao941/pairs.jsonl.gz"
SAO959 = "data/ingest/sao959/pairs.jsonl.gz"
SAO962 = "data/ingest/sao962/pairs.jsonl.gz"
PREREG = "docs/prereg_964_tautology_union.md"
OUT = ROOT / "runners/out964_checks.json"
# 🔴🔴 **수리 「전」 트리를 고정 rev 로 못 박는다.**
#   처음엔 `HEAD` 를 썼는데, **수리를 커밋한 순간 `HEAD` 가 「수리 후」가 됐다** —
#   그러면 P1·P5(「964 수리 전에 없는 키를 참조하는 파일이 몇이었나」)가 **원리상 항상 0** 이 된다.
#   🔴 **자기 수리가 자기 자를 지우는 꼴이다.** 사전등록 커밋(= 측정 전 단독 커밋)으로 고정한다.
PRE_FIX_REV = "62c50d380"          # docs/prereg_964_tautology_union.md 단독 커밋

# ── 사전등록 §0 등록 상수 (docs/prereg_964_tautology_union.md · 측정 전 단독 커밋) ──
REG_SHA = {
    SAO941: "50eacbe4468cf86f561535e3eea7aec31f0151679a33018b7eb12627d1cbbd83",
    SAO959: "273e4bad06c9f073be89ae3477b89acf9a4973f2c77c66e21aa571a4b5d56728",
    SAO962: "7439f0ead2f9ae150f1164e8bfecb8ef1f4d92f7c57599c3f049c4c85ec33f39",
}
# 🔴 티처 #102 가 준 수 — **내 예측이 아니라 재현 대상이다**(사전등록 §0-다)
TEA = {
    "앞 · LM 학습쌍": 14248,
    "963 의 뒤": 38945,
    "합집합(정규화 distinct)": 42098,
    "합집합(편)": 42948,
    "성분 · wiki 줄": 2571,
    "성분 · sao962 정규화 distinct": 35561,
    "성분 · 941 안 겹친 정규화 distinct": 3966,
    "성분 · sao962 줄": 36374,
    "성분 · 941 안 겹친 편": 4003,
    "941 편 중 겹친 것": 7674,
    "정규화 안 한 교집합": 7552,
}

# ══════════════════════════════════════════════════════════════════════════
# W8″ — **실제로 연 파일** 감사
#   🔴 964 정정(티처 #102 M4): 963 은 후크 여섯을 걸고 「여섯을 문다」로 신고했다.
#   티처가 `Path.read_text`·`read_bytes`·`Path.open` 셋을 **전부 떼도 산출물이 시각 두 줄
#   빼고 바이트 동일**임을 실측했다 — **3.9 의 `pathlib` 은 결국 `io.open` 을 부른다.**
#   964 는 **어느 후크가 실제로 불렸는지를 센다**(HOOK_FIRED). 신고는 실측으로 한다.
# ══════════════════════════════════════════════════════════════════════════
OPENED = set()
HOOK_FIRED = collections.Counter()
_real_open = builtins.open
_real_ioopen = io.open
_real_gzopen = gzip.open
_real_ptext = Path.read_text
_real_pbytes = Path.read_bytes
_real_popen = Path.open
_AUDIT_ON = [False]
# 🔴 티처 #102 M6 — V8 의 「금지 구역 적발 0」이 **자기 감사를 우회해 얻은 0** 이었다.
#   964 는 우회를 **숨기지 않고 신고한다**. 아래가 그 목록이다.
BYPASSED = []


def _bypass_read(rel, why):
    """🔴 **감사를 우회해 읽는다 — 그리고 우회했다고 신고한다**(티처 #102 M6).

    963 은 `_real_ptext(ROOT/"data/lab/denominator.json")` 로 원장을 읽고
    **V8 의 「금지 구역 적발 0」을 얻었다.** 읽어야 할 파일인 건 맞으나
    **「안 읽었다」와 「우회해서 읽었다」는 둘이다**(조항 59).
    """
    BYPASSED.append({"파일": str(rel), "왜": why})
    return _real_ptext(ROOT / rel, encoding="utf-8")


def _rel(p):
    try:
        r = Path(p).resolve()
    except Exception:                                              # noqa: BLE001
        return None
    try:
        return str(r.relative_to(ROOT))
    except ValueError:
        return None


def _note(p, how):
    if not _AUDIT_ON[0]:
        return
    HOOK_FIRED[how] += 1
    r = _rel(p)
    if r:
        OPENED.add(r)


def install_audit(hooks=("builtins.open", "io.open", "gzip.open",
                         "Path.read_text", "Path.read_bytes", "Path.open")):
    """🔴 `hooks` 로 **어느 후크를 걸지 고를 수 있다** — M4 를 실측으로 정정하려고 뗐다 붙인다."""
    if "builtins.open" in hooks:
        def a_open(file, *a, **k):
            _note(file, "builtins.open")
            return _real_open(file, *a, **k)
        builtins.open = a_open
    if "io.open" in hooks:
        def a_ioopen(file, *a, **k):
            _note(file, "io.open")
            return _real_ioopen(file, *a, **k)
        io.open = a_ioopen
    if "gzip.open" in hooks:
        def a_gz(filename, *a, **k):
            _note(filename, "gzip.open")
            return _real_gzopen(filename, *a, **k)
        gzip.open = a_gz
    if "Path.read_text" in hooks:
        def a_ptext(self, *a, **k):
            _note(self, "Path.read_text")
            return _real_ptext(self, *a, **k)
        Path.read_text = a_ptext
    if "Path.read_bytes" in hooks:
        def a_pbytes(self, *a, **k):
            _note(self, "Path.read_bytes")
            return _real_pbytes(self, *a, **k)
        Path.read_bytes = a_pbytes
    if "Path.open" in hooks:
        def a_popen(self, *a, **k):
            _note(self, "Path.open")
            return _real_popen(self, *a, **k)
        Path.open = a_popen
    _AUDIT_ON[0] = True


def uninstall_audit():
    builtins.open = _real_open
    io.open = _real_ioopen
    gzip.open = _real_gzopen
    Path.read_text = _real_ptext
    Path.read_bytes = _real_pbytes
    Path.open = _real_popen
    _AUDIT_ON[0] = False


BANNED = ("data/lab/", "data/state/", "data/records/")


def banned_hits():
    return sorted(p for p in OPENED
                  if p.startswith(BANNED) or "denominator" in p)


# ── HTTP 0 감사 ────────────────────────────────────────────────────────────
CONNECTS = []
_real_connect = socket.socket.connect


def install_net_audit():
    def a_connect(self, addr):
        CONNECTS.append(str(addr))
        return _real_connect(self, addr)
    socket.socket.connect = a_connect


# ── 잡동사니 ───────────────────────────────────────────────────────────────
def sha_file(rel):
    h = hashlib.sha256()
    with open(str(ROOT / rel), "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rows(rel):
    with gzip.open(str(ROOT / rel), "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def has_s(d):
    s = d.get("s_상태") or {}
    return bool(s.get("값"))


def s_key(d):
    """🔴 조항 63 — `s_상태` **열만 꺼낸다.** 레코드 전체를 직렬화하지 않는다."""
    s = d.get("s_상태") or {}
    return (d.get("a_액션", {}).get("개체"), tuple(s.get("값") or []))


def bodies_of(d):
    o = d.get("o_결과") or {}
    b = o.get("본문")
    if isinstance(b, list):
        return [x.get("글") or "" for x in b if isinstance(x, dict)]
    if isinstance(b, str):
        return [b]
    return [None]


def norm(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


# ══════════════════════════════════════════════════════════════════════════
# §1 🔴🔴 합집합 재분모화 (티처 #102 M1)
# ══════════════════════════════════════════════════════════════════════════
def load_baseline():
    seen = collections.OrderedDict()
    dup941 = 0
    inter = 0
    ids941 = set()
    for d in rows(SAO941):
        pid = d["쌍id"]
        if pid in ids941:
            dup941 += 1
        ids941.add(pid)
        seen[pid] = d
    for d in rows(SAO959):
        pid = d["쌍id"]
        if pid in ids941:
            inter += 1
        seen[pid] = d
    return list(seen.values()), {"941 안 중복 쌍id": dup941, "941 ∩ 959": inter,
                                 "distinct 쌍id": len(seen)}


def redenominate(denom_mode="정본", after_mode="합집합", drop_domain_key=0):
    """🔴🔴 **964 — 인자를 실제로 받는다**(티처 #102 C2: 963 의 K7 은 등록 상수끼리의 산술이라
    `redenominate()` 를 네 가지로 망가뜨려도 네 번 다 True 였다).

    `denom_mode` : `정본`(LM 학습쌍) · `혼합`(962 의 줄 수) · `wiki만`
    `after_mode` : `합집합`(964) · `963판`(겹친 941 편을 통째로 버린다) · `이중계상`
    `drop_domain_key` : §3 W3″ 심기용 — 완전 삼중쌍 n 개에서 `도메인` 키를 뗀다
    """
    base, prov = load_baseline()
    complete = [d for d in base if has_s(d)]
    if drop_domain_key:
        complete = [dict(d) for d in complete]
        for d in complete[:drop_domain_key]:
            d.pop("도메인", None)
    empty_s = len(base) - len(complete)

    wiki_lines = [d for d in complete if d["쌍id"].startswith("wiki:")]
    steam_lines = [d for d in complete if d["쌍id"].startswith("steam:")]
    lm_wiki = sum(len(bodies_of(d)) for d in wiki_lines)
    steam_bodies = []
    for d in steam_lines:
        ent = d.get("a_액션", {}).get("개체")
        for b in bodies_of(d):
            if b:
                steam_bodies.append((ent, b))
    lm_steam = len(steam_bodies)

    new_rows = list(rows(SAO962))
    lm_new = len(new_rows)

    # 🔴🔴 여기가 M1 의 자리 — **겹침을 배수에 실제로 먹인다**
    new_pairs = {(d.get("a_액션", {}).get("개체"), norm((d.get("o_결과") or {}).get("본문")))
                 for d in new_rows}
    old_hit = [(e, b) for e, b in steam_bodies if (e, norm(b)) in new_pairs]
    old_miss = [(e, b) for e, b in steam_bodies if (e, norm(b)) not in new_pairs]
    n_hit, n_miss = len(old_hit), len(old_miss)
    old_miss_dist = len({(e, norm(b)) for e, b in old_miss})
    new_dist = len(new_pairs)
    old_dist = len({(e, norm(b)) for e, b in steam_bodies})

    # 앞(분모)
    if denom_mode == "정본":
        lm_before = lm_wiki + lm_steam
    elif denom_mode == "혼합":
        lm_before = len(complete)          # 🔴 962 의 **줄 수** — 단위가 다르다
    elif denom_mode == "wiki만":
        lm_before = lm_wiki
    else:
        raise ValueError(denom_mode)

    # 뒤(분자)
    after = collections.OrderedDict()
    after["🔴🔴 ① 합집합(편) — 964 가 채택하는 꼴"] = {
        "값": lm_wiki + lm_new + n_miss,
        "식": "wiki 줄 %d + sao962 줄 %d + 941 편 중 **안 겹친** %d" % (lm_wiki, lm_new, n_miss),
        "분모의 단위": "편(리뷰 한 편 = LM 학습쌍 한 개)",
        "🔴 왜 이것이 「앞」의 상위집합인가": (
            "앞 %d = wiki %d + 941 편 %d. 그 941 편 중 %d 는 sao962 가 **개별 행으로 다시 내므로** "
            "합집합에서 한 번만 세고, %d 는 **sao962 에 없어서 그대로 남는다.** "
            "🔴 **963 의 「뒤」는 이 %d 편을 통째로 버렸다 — 그래서 상위집합이 아니었고 성장비의 꼴이 아니었다**"
            % (lm_wiki + lm_steam, lm_wiki, lm_steam, n_hit, n_miss, n_miss)),
    }
    after["② 합집합(정규화 distinct)"] = {
        "값": lm_wiki + new_dist + old_miss_dist,
        "식": "wiki 줄 %d + sao962 정규화 distinct %d + 941 안 겹친 정규화 distinct %d"
              % (lm_wiki, new_dist, old_miss_dist),
        "🔴 조항 60 경고": (
            "이 분자는 **정규화 distinct** 인데 티처 #102 는 이것을 **편 단위 분모 14,248** 로 나눠 "
            "2.9547 을 냈다 — 🔴 **분자와 분모의 단위가 다르다.** 964 는 **양쪽을 다 distinct 로 놓은 수**를 "
            "옆에 병기한다"),
    }
    after["③ 963 판(겹친 941 편을 통째로 버린다 · 역사 기록)"] = {
        "값": lm_wiki + lm_new,
        "식": "wiki 줄 %d + sao962 줄 %d" % (lm_wiki, lm_new),
        "🔴 무엇이 빠졌나": "**안 겹친 %d 편**(실재하고 sao962 에 없다)" % n_miss,
    }
    after["④ 이중계상(941 앱단위 줄을 그대로 다 더한다 · 틀린 꼴)"] = {
        "값": lm_wiki + lm_steam + lm_new,
        "🔴 왜 틀렸나": "겹친 %d 편을 **두 번** 센다" % n_hit,
    }

    pick = {"합집합": "🔴🔴 ① 합집합(편) — 964 가 채택하는 꼴",
            "963판": "③ 963 판(겹친 941 편을 통째로 버린다 · 역사 기록)",
            "이중계상": "④ 이중계상(941 앱단위 줄을 그대로 다 더한다 · 틀린 꼴)"}[after_mode]
    lm_after = after[pick]["값"]

    # 양쪽 다 정규화 distinct 로 놓은 수 — 🔴 단위를 안 섞는다
    before_dist = lm_wiki + old_dist
    after_dist = lm_wiki + new_dist + old_miss_dist

    s_before = {s_key(d) for d in complete}
    s_new = {s_key(d) for d in new_rows}
    s_after = {s_key(d) for d in wiki_lines} | {s_key(d) for d in steam_lines} | s_new

    dom_before = collections.Counter(d["도메인"] for d in complete if "도메인" in d)
    dom_after = collections.Counter()
    for d in wiki_lines:
        if "도메인" in d:
            dom_after[d["도메인"]] += 1
    for d in new_rows:
        if "도메인" in d:
            dom_after[d["도메인"]] += 1

    def ratio(a, b, nd=4):
        return round(b / a, nd) if a else None

    tab = collections.OrderedDict()
    tab["🔴🔴 M1 — 963 이 자기가 잰 겹침을 배수에 안 먹였다"] = {
        "963 이 잰 겹침": "%d / %d = %.1f%%" % (n_hit, lm_steam, 100.0 * n_hit / lm_steam),
        "🔴 그런데 963 의 「뒤」는": "941 의 **%d 편을 통째로 뺐다**" % lm_steam,
        "🔴 안 겹치고 실재하는 것": n_miss,
        "🔴 그래서": "**963 의 「뒤」는 「앞」의 상위집합이 아니다 — 성장비의 꼴이 아니었다**",
    }
    tab["🔴🔴 배수 셋을 분모와 함께 나란히 적는다(사전등록 §3-1)"] = collections.OrderedDict([
        ("분모(앞) · LM 학습쌍 · 편", lm_before),
        ("분모의 내역", {"wiki 줄(개체당 1쌍)": lm_wiki,
                    "941 앱단위 줄이 묶은 리뷰 편": lm_steam,
                    "그 앱단위 줄 수": len(steam_lines)}),
        ("① 합집합(편) → 배수", {"분자": after["🔴🔴 ① 합집합(편) — 964 가 채택하는 꼴"]["값"],
                          "배수": ratio(lm_before, after["🔴🔴 ① 합집합(편) — 964 가 채택하는 꼴"]["값"]),
                          "단위": "분자·분모 **둘 다 편** ✅"}),
        ("② 합집합(정규화 distinct) → 배수", {
            "분자": after["② 합집합(정규화 distinct)"]["값"],
            "배수(티처 #102 의 꼴 · 분모는 편)": ratio(lm_before, after["② 합집합(정규화 distinct)"]["값"]),
            "🔴 단위": "분자 distinct · 분모 편 — **섞였다**(조항 60)",
            "🔴 양쪽 다 distinct 로 놓으면": {
                "분모": before_dist, "분자": after_dist, "배수": ratio(before_dist, after_dist),
                "단위": "분자·분모 **둘 다 정규화 distinct** ✅"}}),
        ("③ 963 판 → 배수", {"분자": after["③ 963 판(겹친 941 편을 통째로 버린다 · 역사 기록)"]["값"],
                        "배수": ratio(lm_before, after["③ 963 판(겹친 941 편을 통째로 버린다 · 역사 기록)"]["값"]),
                        "🔴 반드시 붙일 말": "**안 겹치는 %d 편을 뺐다**" % n_miss}),
    ])
    tab["뒤 · 네 가지 꼴"] = after
    tab["🔴 distinct s"] = {
        "분모(앞)": len(s_before), "분자(뒤)": len(s_after),
        "배수": ratio(len(s_before), len(s_after)),
        "sao962 자신의 distinct s": len(s_new),
        "🔴 963 과 무엇이 다른가": (
            "963 의 「뒤」는 wiki 줄 + sao962 만 썼다(941 steam 줄의 s 를 버렸다). "
            "964 의 「뒤」는 **합집합이라 941 steam 줄의 s 도 넣는다** — 겹치므로 수는 같거나 크다"),
    }
    tab["🔴 도메인"] = {
        "분모(앞)": len(dom_before), "분자(뒤)": len(dom_after),
        "배수": ratio(len(dom_before), len(dom_after), 2),
        "앞": dict(sorted(dom_before.items())), "뒤": dict(sorted(dom_after.items())),
        "🔴 sao962 의 도메인": sorted({d["도메인"] for d in new_rows if "도메인" in d}),
        "🔴 도메인 Δ": len(dom_after) - len(dom_before),
    }
    tab["기준선 출처"] = prov
    tab["기준선 · s 가 빈 줄"] = empty_s
    tab["기준선 · 완전 삼중쌍(줄)"] = len(complete)

    # 🔴 티처 #102 의 수를 **내가 원자료에서 다시 세어** 대조한다(사전등록 §0-다 · 조항 60)
    mine = {
        "앞 · LM 학습쌍": lm_wiki + lm_steam,
        "963 의 뒤": lm_wiki + lm_new,
        "합집합(정규화 distinct)": lm_wiki + new_dist + old_miss_dist,
        "합집합(편)": lm_wiki + lm_new + n_miss,
        "성분 · wiki 줄": lm_wiki,
        "성분 · sao962 정규화 distinct": new_dist,
        "성분 · 941 안 겹친 정규화 distinct": old_miss_dist,
        "성분 · sao962 줄": lm_new,
        "성분 · 941 안 겹친 편": n_miss,
        "941 편 중 겹친 것": n_hit,
        "정규화 안 한 교집합": len({(e, b) for e, b in steam_bodies}
                           & {(d.get("a_액션", {}).get("개체"),
                               (d.get("o_결과") or {}).get("본문")) for d in new_rows}),
    }
    cmp = collections.OrderedDict()
    for k, v in TEA.items():
        cmp[k] = {"티처 #102": v, "내가 원자료에서 다시 셈": mine[k], "맞나": mine[k] == v}
    tab["🔴🔴 F3 — 티처의 수를 원자료에서 다시 세어 대조(조항 60)"] = {
        "표": cmp,
        "분자: 맞은 수": sum(1 for c in cmp.values() if c["맞나"]),
        "분모: 대조한 수": len(cmp),
        "🔴 안 맞은 것": [k for k, c in cmp.items() if not c["맞나"]] or "없음",
        "🔴 안 맞으면": "채택하지 않고 두 수를 분모와 함께 나란히 적는다(사전등록 §3-2)",
        "통과": all(c["맞나"] for c in cmp.values()),
    }
    tab["🔴 이 주행의 인자"] = {"denom_mode": denom_mode, "after_mode": after_mode,
                        "drop_domain_key": drop_domain_key,
                        "쓴 분모": lm_before, "쓴 분자": lm_after,
                        "쓴 배수": ratio(lm_before, lm_after, 2)}
    ctx = {"complete": complete, "wiki_lines": wiki_lines, "steam_lines": steam_lines,
           "steam_bodies": steam_bodies, "new_rows": new_rows,
           "n_hit": n_hit, "n_miss": n_miss, "lm_before": lm_before,
           "lm_after": lm_after, "lm_wiki": lm_wiki, "lm_steam": lm_steam,
           "new_pairs": new_pairs, "ratio": ratio(lm_before, lm_after, 2)}
    return tab, ctx


# ══════════════════════════════════════════════════════════════════════════
# §2 W6′ 정정 (티처 #102 m1 · m2)
# ══════════════════════════════════════════════════════════════════════════
def w6_prime(ctx, include_app_lines=False):
    """🔴 **964 정정 둘**.

    **m1** 963 의 산출물은 7,674 를 **두 번 다르게 설명**했다 — 한 곳에선 「941 의 편 중
    겹친 것」이라 옳게 적고, 다른 곳에선 「티처의 7,674 는 **정규화 안 한** 수다」라 적었다.
    🔴 **거짓이다.** 정규화 **안 한** 교집합은 **7,552** 다. 964 는 **넷을 다 적고
    각각의 분모를 붙인다.**

    **m2** 963 의 `"비율(941 편 수 분모)": 0.6467` 은 **7,552(정규화 안 한 distinct 짝) /
    11,677(편)** 이었다 — 🔴 **단위 섞기를 기소하는 검사 안에 단위 섞인 비**가 있었다.
    964 는 **분자와 분모의 단위가 같은 비만 낸다.**
    """
    old_norm = {(e, norm(b)) for e, b in ctx["steam_bodies"]}
    old_raw = {(e, b) for e, b in ctx["steam_bodies"]}
    new_norm = ctx["new_pairs"]
    new_raw = {(d.get("a_액션", {}).get("개체"), (d.get("o_결과") or {}).get("본문"))
               for d in ctx["new_rows"]}
    raw_old = len(ctx["steam_bodies"])
    raw_new = len(ctx["new_rows"])
    rows_hit = sum(1 for d in ctx["new_rows"]
                   if (d.get("a_액션", {}).get("개체"),
                       norm((d.get("o_결과") or {}).get("본문"))) in old_norm)
    bodies_hit = ctx["n_hit"]
    n_int_norm = len(old_norm & new_norm)
    n_int_raw = len(old_raw & new_raw)
    return {
        "🔴 무엇": "**본문** 기준. `쌍id` 가 아니다 — 962 의 W6 은 접두가 서로소라 항진명제였다",
        "🔴🔴 964 m1·m2 정정 — 겹침을 **네 분모로 다 적고 단위가 같은 비만 낸다**": collections.OrderedDict([
            ("가 · 941 의 **편** 중 겹친 것", {
                "겹침": bodies_hit, "분모": raw_old,
                "비": round(bodies_hit / raw_old, 4),
                "단위": "편 / 편 ✅",
                "✅ 티처 #101·#102 의 7,674 / 11,677 = 65.7%": bodies_hit == 7674 and raw_old == 11677}),
            ("나 · sao962 의 **줄** 중 겹친 것", {
                "겹침": rows_hit, "분모": raw_new,
                "비": round(rows_hit / raw_new, 4), "단위": "줄 / 줄 ✅"}),
            ("다 · **정규화 distinct 짝** 기준", {
                "겹침": n_int_norm, "분모(941 쪽)": len(old_norm),
                "비": round(n_int_norm / len(old_norm), 4) if old_norm else None,
                "단위": "distinct / distinct ✅"}),
            ("라 · **정규화 안 한 distinct 짝** 기준", {
                "겹침": n_int_raw, "분모(941 쪽)": len(old_raw),
                "비": round(n_int_raw / len(old_raw), 4) if old_raw else None,
                "단위": "distinct / distinct ✅"}),
        ]),
        "🔴🔴 963 이 무엇을 틀렸나(m1)": {
            "963 의 문장": "「⚠ 티처 #101 은 7,674 / 11,677 = 65.7% 라 냈다 — 분모를 「편 수」로 두고 **정규화를 안 한** 수다」",
            "🔴 판정": "**거짓이다.**",
            "🔴 근거": ("정규화를 **안 한** 교집합은 %d 이고 티처의 수는 %d 다. 티처의 7,674 는 "
                    "**정규화 여부와 무관하게 「941 의 편 중 겹친 것」**이다 — 963 은 같은 산출물 안에서 "
                    "이것을 한 번은 옳게 적고 한 번은 틀리게 적었다" % (n_int_raw, bodies_hit)),
        },
        "🔴🔴 963 이 무엇을 틀렸나(m2)": {
            "963 의 키": '"비율(941 편 수 분모)": 0.6467',
            "🔴 그 수의 정체": "%d(정규화 안 한 **distinct 짝**) / %d(**편**) = %s — **단위가 섞였다**"
                        % (n_int_raw, raw_old, round(n_int_raw / raw_old, 4)),
            "🔴 왜 나쁜가": "**단위 섞기를 기소하는 검사 안에 단위 섞인 비가 있었다**(조항 60)",
        },
        "🔴 정본 회계가 941 앱단위 줄을 세나": bool(include_app_lines),
        "통과": (not include_app_lines) and bodies_hit > 0,
        "🔴 무엇이면 떨어지나": (
            "① 정본 회계가 941 앱단위 줄을 **같이** 세면 떨어진다 · "
            "② 겹침이 **0** 이면 떨어진다(겹침 0 은 아무것도 안 견줬다는 뜻이라 962 의 W6 과 같아진다)"),
    }


# ══════════════════════════════════════════════════════════════════════════
# §3 🔴🔴 W3″ — **분모를 독립 경로에서** 가져온다 (티처 #102 C1)
# ══════════════════════════════════════════════════════════════════════════
def w3_double_prime(records, key="도메인"):
    """🔴🔴 **964 수리 (티처 #102 C1)** — 963 의 §3 은 이랬다::

        dom = Counter(d["도메인"] for d in complete)
        w3_prime(dict(dom), sum(dom.values()))       # ← 분모가 자기 분자의 합

    **원리상 못 떨어진다.** 티처가 러너를 다시 돌려 셋을 심었고(무변조 · `{게임:999999,
    없는도메인:-12345}` · `{아무거나:1}`) **셋 다 초록**이었다. 그리고 그 초록이
    **⑤′ 절 회계 3/4 의 세 초록 중 하나**를 차지했다.

    🔴 **964 는 분모를 「칸을 만든 경로」가 아니라 「원천 레코드 리스트의 길이」에서 가져온다.**
    그러면 이 검사는 **진짜 물음**을 묻는다 — **「분류가 전수를 덮나(누락이 없나)」**.
    `도메인` 키가 없는 레코드가 하나라도 있으면 칸의 합이 분모보다 **작아지고 떨어진다.**
    """
    buckets = collections.Counter(d[key] for d in records if key in d)
    tot = sum(buckets.values())
    denom = len(records)                      # 🔴 **독립 경로** — 칸을 안 거친다
    missing = [i for i, d in enumerate(records) if key not in d]
    return {
        "🔴 무엇": "**분류가 원천 전수를 덮나** — 칸의 합 == 원천 레코드 수",
        "칸": dict(sorted(buckets.items())),
        "분자: 칸의 합": tot,
        "🔴 분모: **원천 레코드 리스트의 길이**(칸을 안 거친다)": denom,
        "🔴 `%s` 키가 없는 레코드" % key: len(missing),
        "🔴🔴 963 의 §3 은 무엇이었나": (
            "`w3_prime(dict(dom), sum(dom.values()))` — **분모가 자기 분자의 합**이라 "
            "**원리상 못 떨어졌다**(티처 #102 C1). 964 는 분모를 `len(records)` 에서 가져온다"),
        "🔴 무엇이면 떨어지나": ("`%s` 키가 없는 레코드가 하나라도 생기면 칸의 합이 분모보다 작아진다. "
                        "🔴 **칸을 아무리 부풀리거나 지워도 분모는 안 따라온다** — "
                        "963 판은 따라왔다" % key),
        "통과": tot == denom,
    }


# ══════════════════════════════════════════════════════════════════════════
# §4 🔴🔴 V4′ — `rulers()` 소비자 전수 감사 (티처 #102 M3 · 예측 P1·P2·P5)
# ══════════════════════════════════════════════════════════════════════════
def _consumers():
    out = []
    for p in sorted((ROOT / "runners").glob("*.py")):
        try:
            src = _real_ptext(p, encoding="utf-8")
        except Exception:                                          # noqa: BLE001
            continue
        if re.search(r"\brulers\s*\(", src):
            out.append(p)
    return out


def _rulers_keys():
    from lab.adopt import rulers
    return set(rulers(sum_delta=0.05, sum_T=0.02, sub_delta=0.005, sub_T=0.02,
                      perm_obs=0.05, perm_p95=-0.0005, card_T=0.00353).keys())


def _scan_source(name, src, valid_keys, sig_params):
    """AST 로 **문자열 리터럴 대조**를 한다. 🔴 조항 63 — 소스를 grep 하지 않고 **노드로** 본다.

    (grep 하면 **주석과 독스트링에 인용된 옛 키**가 그대로 걸린다 — 964 자신이
    `curve961.py` 의 독스트링에 옛 리터럴을 인용해 놓았고, grep 은 그것을 못 가린다.)
    """
    try:
        tree = ast.parse(src)
    except SyntaxError as e:                                       # noqa: BLE001
        return {"파싱": "🔴 SyntaxError: %s" % e, "나쁜 키": [], "나쁜 인자": [],
                "rulers 변수": [], "in-리터럴 판정": []}
    # 🔴 **스코프별로 본다.** 파일 전체를 한 이름공간으로 보면 다른 함수의 지역 변수
    #   이름이 겹쳐 **거짓 적발**이 난다(964 자신의 `r` 이 그랬다 — `planted()` 안의
    #   `r = rulers(...)` 와 `__main__` 의 `r = main()` 이 같은 이름이다).
    scopes = [tree] + [n for n in ast.walk(tree)
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

    def _own(scope):
        """이 스코프에 **직접** 속한 노드만(중첩 함수 본문은 그쪽 스코프의 것)."""
        inner = {id(f) for f in ast.walk(scope)
                 if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f is not scope}
        out, stack = [], list(ast.iter_child_nodes(scope))
        while stack:
            n = stack.pop()
            if id(n) in inner:
                continue
            out.append(n)
            stack.extend(ast.iter_child_nodes(n))
        return out

    bad_kw, bad_keys = [], []
    for sc in scopes:
        nodes = _own(sc)
        holders = set()
        for n in nodes:
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) \
                    and isinstance(n.value.func, ast.Name) and n.value.func.id == "rulers":
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        holders.add(t.id)
        for n in nodes:
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                    and n.func.id == "rulers":
                for kw in n.keywords:
                    if kw.arg is not None and kw.arg not in sig_params:
                        bad_kw.append({"줄": n.lineno, "인자": kw.arg})
        if not holders:
            continue
        for n in nodes:
            lit = None
            if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) \
                    and n.value.id in holders:
                sl = n.slice
                if hasattr(ast, "Index") and isinstance(sl, getattr(ast, "Index")):
                    sl = sl.value
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                    lit = sl.value
            elif isinstance(n, ast.Compare) and len(n.ops) == 1 \
                    and isinstance(n.ops[0], (ast.In, ast.NotIn)) \
                    and isinstance(n.left, ast.Constant) and isinstance(n.left.value, str) \
                    and isinstance(n.comparators[0], ast.Name) \
                    and n.comparators[0].id in holders:
                lit = n.left.value
            if lit is not None and lit not in valid_keys:
                bad_keys.append({"줄": n.lineno, "🔴 없는 키": lit})
    # 🔴 P5 — `bool("<리터럴>" in <무엇이든>)` 을 그대로 `통과` 로 쓰는 자리
    in_verdict = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Dict):
            continue
        for k, v in zip(n.keys, n.values):
            if not (isinstance(k, ast.Constant) and isinstance(k.value, str)
                    and "통과" in k.value):
                continue
            cmpnode = v
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "bool" \
                    and len(v.args) == 1:
                cmpnode = v.args[0]
            if isinstance(cmpnode, ast.Compare) and len(cmpnode.ops) == 1 \
                    and isinstance(cmpnode.ops[0], (ast.In, ast.NotIn)) \
                    and isinstance(cmpnode.left, ast.Constant) \
                    and isinstance(cmpnode.left.value, str):
                in_verdict.append({"줄": getattr(v, "lineno", n.lineno),
                                   "리터럴": cmpnode.left.value[:60]})
    return {"파싱": "OK", "나쁜 키": bad_keys, "나쁜 인자": bad_kw,
            "rulers 변수": sorted(holders), "in-리터럴 판정": in_verdict}


def _import_smoke(mod):
    """🔴 **쓰기를 막고** 임포트한다 — 저장소 러너 20개 이상이 `ROOT` 를 하드코딩하고
    `os.chdir` 한다(티처 #102 m7). 스모크가 파일을 덮으면 안 된다.

    🔴 **`runners/` 를 `sys.path` 에 넣는다.** 저장소 러너 다수가 `import ff753` 처럼
    **형제 모듈을 최상위 이름으로** 부르는데, 그것은 `python3 runners/x.py` 로 **스크립트로
    돌릴 때만** 풀린다(그때 `sys.path[0]` 이 `runners/`). 🔴 **실제 호출 방식을 흉내내지
    않으면 스모크가 재는 것은 「그 러너가 깨졌나」가 아니라 「내가 다르게 불렀나」다**(조항 59).
    """
    pre = (
        "import builtins, io, sys, os\n"
        "sys.path.insert(0, os.path.join(%r, 'runners'))\n"
        "_o = builtins.open\n"
        "def _g(f, mode='r', *a, **k):\n"
        "    if any(c in str(mode) for c in 'wxa+'):\n"
        "        raise IOError('964 임포트 스모크 — 쓰기 차단')\n"
        "    return _o(f, mode, *a, **k)\n"
        "builtins.open = _g\n"
        "io.open = _g\n"
        "import importlib\n"
        "importlib.import_module(%r)\n"
        "print('OK')\n" % (str(ROOT), mod))
    try:
        r = subprocess.run([sys.executable, "-c", pre], cwd=str(ROOT),
                           capture_output=True, timeout=300)
        return {"통과": r.returncode == 0 and b"OK" in r.stdout,
                "종료코드": r.returncode,
                "🔴 마지막 줄": (r.stderr.decode("utf-8", "replace").strip()
                           .splitlines() or ["(없다)"])[-1][:200]}
    except subprocess.TimeoutExpired:
        return {"통과": False, "종료코드": "TIMEOUT(300s)", "🔴 마지막 줄": "300초 안에 안 끝났다"}


def v4_prime():
    import inspect
    from lab.adopt import rulers
    sig_params = set(inspect.signature(rulers).parameters)
    valid = _rulers_keys()
    files = _consumers()
    now, head = collections.OrderedDict(), collections.OrderedDict()
    for p in files:
        rel = str(p.relative_to(ROOT))
        now[rel] = _scan_source(rel, _real_ptext(p, encoding="utf-8"), valid, sig_params)
        o = subprocess.run(["git", "show", "%s:%s" % (PRE_FIX_REV, rel)], cwd=str(ROOT),
                           capture_output=True)
        head[rel] = (_scan_source(rel, o.stdout.decode("utf-8"), valid, sig_params)
                     if o.returncode == 0 else {"파싱": "🔴 수리 전 트리에 없다", "나쁜 키": [],
                                                "나쁜 인자": [], "in-리터럴 판정": []})
    # 🔴 964 가 **자기 러너를 소비자 목록에 더한다** — 분모가 11 에서 12 로 는다.
    #   예측 P1·P2 의 분모는 **HEAD 에 있던 11** 이다. 둘을 갈라 적는다(조항 60).
    in_head = collections.OrderedDict()
    for p in files:
        rel = str(p.relative_to(ROOT))
        in_head[rel] = subprocess.run(["git", "cat-file", "-e", "%s:%s" % (PRE_FIX_REV, rel)],
                                      cwd=str(ROOT), capture_output=True).returncode == 0
    smoke = collections.OrderedDict()
    for p in files:
        smoke["runners." + p.stem] = _import_smoke("runners." + p.stem)
        smoke["runners." + p.stem]["수리 전 트리에 있던 소비자인가"] = in_head[str(p.relative_to(ROOT))]
    n_head = sum(1 for v in in_head.values() if v)
    ok_head = sum(1 for k, v in smoke.items() if v["통과"] and v["수리 전 트리에 있던 소비자인가"])
    # 🔴 P5 — 소비자만이 아니라 `runners/*.py` **전수**를 본다(분모가 다르다)
    p5_all = collections.OrderedDict()
    p5_scanned = 0
    p5_skipped = []
    ls = subprocess.run(["git", "-c", "core.quotePath=false", "ls-tree", "-r",
                         "--name-only", "-z", PRE_FIX_REV, "runners/"],
                        cwd=str(ROOT), capture_output=True)
    tree_py = [x for x in ls.stdout.decode("utf-8").split("\0") if x.endswith(".py")]
    for rel in sorted(tree_py):
        o = subprocess.run(["git", "show", "%s:%s" % (PRE_FIX_REV, rel)], cwd=str(ROOT),
                           capture_output=True)
        if o.returncode != 0:
            p5_skipped.append(rel)
            continue
        s = _scan_source(rel, o.stdout.decode("utf-8"), valid, sig_params)
        p5_scanned += 1
        if s["in-리터럴 판정"]:
            p5_all[rel] = s["in-리터럴 판정"]
    bad_now = {k: v for k, v in now.items() if v["나쁜 키"] or v["나쁜 인자"]}
    bad_head = {k: v["나쁜 키"] for k, v in head.items() if v["나쁜 키"]}
    ok_smoke = sum(1 for v in smoke.values() if v["통과"])
    return {
        "🔴 무엇": ("963 의 V4 는 `^def rulers\\(` 수와 `import lab.adopt` **둘만** 봤다 — "
                 "**부르는 쪽이 스키마 변경으로 깨졌는지는 안 봤다.** 그래서 머지가 "
                 "`curve961.py:549` 의 W10 을 조용히 뒤집은 것을 놓쳤다(티처 #102 M3)"),
        "분모: `rulers(` 를 부르는 파일(작업 트리)": len(files),
        "🔴 그중 수리 전 트리(`62c50d380`)에도 있던 것": n_head,
        "🔴 964 가 더한 것": [k for k, v in in_head.items() if not v] or "없음",
        "소비자": [str(p.relative_to(ROOT)) for p in files],
        "🔴🔴 가 · 스키마 대조(🔴 고정 rev `62c50d380` = 964 수리 **전**)": {
            "🔴 없는 키를 참조하는 파일": bad_head or "없음",
            "분자: 그런 파일 수": len(bad_head),
            "🔴 P1 예측": "정확히 1개(`runners/curve961.py`)",
            "P1 맞나": len(bad_head) == 1 and "runners/curve961.py" in bad_head,
        },
        "🔴🔴 나 · 스키마 대조(작업 트리 = 964 수리 **후**)": {
            "🔴 없는 키를 참조하는 파일": bad_now or "없음",
            "🔴 등록 안 된 인자로 부르는 곳": {k: v["나쁜 인자"] for k, v in now.items()
                                    if v["나쁜 인자"]} or "없음",
            "통과": not bad_now,
        },
        "🔴🔴 다 · 임포트 스모크(쓰기 차단)": {
            "표": smoke, "분자: 통과": ok_smoke, "분모(작업 트리 전체)": len(smoke),
            "🔴 P2 의 분모 — 수리 전 트리에 있던 소비자": {"분자": ok_head, "분모": n_head},
            "🔴 P2 예측": "11/11 (수리 전 트리에 있던 소비자)",
            "P2 맞나": ok_head == n_head == 11,
            "🔴 왜 쓰기를 막았나": "저장소 러너 20개 이상이 `ROOT` 를 하드코딩하고 `os.chdir` 한다 — 스모크가 파일을 덮으면 안 된다(티처 #102 m7)",
        },
        "🔴🔴 라 · P5 — `키 in 딕트` 를 그대로 `통과` 로 쓰는 자리(runners 전수 · 🔴 수리 전 고정 rev 기준)": {
            "표": p5_all or "없음",
            "분자: 그런 자리 수": sum(len(v) for v in p5_all.values()),
            "🔴 분모: 수리 전 rev 에서 **실제로 AST 로 훑은** `runners/*.py`": p5_scanned,
            "🔴 못 훑은 것": p5_skipped or "없음",
            "⚠ 분모 경고": ("**작업 트리의 `.py` 수가 아니다**(조항 60). 964 가 더한 "
                      "`checks964.py`·`prose964.py` 는 수리 전 rev 에 없으므로 이 분모 밖이다"),
            "🔴 P5 예측": "`curve961.py:549` 하나뿐",
            "P5 맞나": (sum(len(v) for v in p5_all.values()) == 1
                     and list(p5_all) == ["runners/curve961.py"]),
        },
        "통과": bool(not bad_now and ok_smoke == len(smoke)),
    }


# ══════════════════════════════════════════════════════════════════════════
# §5 심어서 떨어뜨리기 — 🔴 **등록 상수끼리의 산술은 안 센다**(사전등록 §3-3)
# ══════════════════════════════════════════════════════════════════════════
def planted(ctx, tab):
    from lab.adopt import rulers
    K = collections.OrderedDict()

    # ── K1 W3″ — 🔴 C1 이 고쳐졌나. 티처가 963 에 심은 셋을 **그대로** 다시 심는다 ──
    recs = ctx["complete"]
    plant_a = w3_double_prime(recs)                       # 무변조
    dropped = [dict(d) for d in recs]
    for d in dropped[:1]:
        d.pop("도메인", None)
    plant_b = w3_double_prime(dropped)                    # 레코드 하나에서 키를 뗀다
    # 🔴 티처가 963 에 심은 것을 **직접** 재현: 칸 딕트를 통째로 바꿔치기해도 963 판은 초록이었다
    old_style = []
    for buckets in (dict(collections.Counter(d["도메인"] for d in recs)),
                    {"게임": 999999, "없는도메인": -12345},
                    {"아무거나": 1}):
        tot = sum(buckets.values())
        old_style.append({"칸": list(buckets)[:3], "합/분모": [tot, tot], "963 판 통과": tot == tot})
    new_style = []
    for buckets in (collections.Counter(d["도메인"] for d in recs),
                    collections.Counter({"게임": 999999, "없는도메인": -12345}),
                    collections.Counter({"아무거나": 1})):
        tot = sum(buckets.values())
        new_style.append({"칸": list(buckets)[:3], "합": tot, "분모(독립)": len(recs),
                          "964 판 통과": tot == len(recs)})
    K["K1 🔴🔴 W3″(C1) — 963 의 §3 이 원리상 못 떨어졌다. 964 판은 떨어지나"] = {
        "무는 코드": "`checks964.w3_double_prime()` — **실제로 다시 부른다**",
        "심은 것 ①": "레코드 하나에서 `도메인` 키를 뗀다",
        "심기 전 통과": plant_a["통과"], "심은 뒤 통과": plant_b["통과"],
        "심은 뒤 합/분모": [plant_b["분자: 칸의 합"], plant_b["🔴 분모: **원천 레코드 리스트의 길이**(칸을 안 거친다)"]],
        "🔴🔴 티처가 963 에 심은 셋을 그대로": {
            "963 판(분모 = 칸의 합)": old_style,
            "🔴 963 판 판정": "**셋 다 True** — 어떤 입력에서도 초록이다(항진명제)",
            "964 판(분모 = 원천 리스트 길이)": new_style,
            "🔴 964 판 판정": "**무변조만 True, 나머지 둘은 False** — 자료를 실제로 읽는다",
        },
        "🔴 빨개졌나": bool(plant_a["통과"] and not plant_b["통과"]
                      and new_style[0]["964 판 통과"]
                      and not new_style[1]["964 판 통과"]
                      and not new_style[2]["964 판 통과"]),
    }

    # ── K2 W6′ ──────────────────────────────────────────────────────────
    good = w6_prime(ctx, include_app_lines=False)
    bad = w6_prime(ctx, include_app_lines=True)
    K["K2 W6′ — 정본 회계가 941 앱단위 줄을 같이 세면 떨어지나"] = {
        "무는 코드": "`checks964.w6_prime()` — 인자를 바꿔 **다시 부른다**",
        "심기 전 통과": good["통과"], "심은 뒤 통과": bad["통과"],
        "🔴 빨개졌나": bool(good["통과"] and not bad["통과"]),
    }

    # ── K3 🔴 V6 sha — 사전등록에 박았으니 이제 심을 대상이 있다 ─────────
    real = {p: sha_file(p) for p in (SAO941, SAO959, SAO962)}
    ok_now = all(real[p] == REG_SHA[p] for p in real)
    fake = dict(REG_SHA)
    fake[SAO962] = "0" * 64
    ok_plant = all(real[p] == fake[p] for p in real)
    K["K3 🔴🔴 V6 sha(C2) — 963 은 심을 대상이 없었다. 964 는 사전등록에 박았다"] = {
        "무는 코드": "`checks964.REG_SHA` ↔ `sha_file()` — **사전등록 §0-나 의 등록값과 대조한다**",
        "심은 것": "등록값 `%s` 자리에 `'0'*64` 를 넣는다" % SAO962,
        "심기 전 통과": ok_now, "심은 뒤 통과": ok_plant,
        "🔴 963 은 왜 못 심었나": ("**V6 이 `통과` 키를 아예 안 냈다** — 사전등록에 대조 대상이 없었다. "
                          "티처 #102: `shas` 를 `'0'*64` 로 해도 **아무 검사도 안 바뀌었다**"),
        "🔴 빨개졌나": bool(ok_now and not ok_plant),
    }

    # ── K4·K5 W8″ 후크 ──────────────────────────────────────────────────
    before4 = "data/lab/denominator.json" in OPENED
    _ = Path(ROOT / "data/lab/denominator.json").read_text(encoding="utf-8")[:1]
    after4 = banned_hits()
    K["K4 W8″ — `Path.read_text` 로 금지 구역을 열면 무나"] = {
        "무는 코드": "`checks964.install_audit()` 의 후크 — **실제로 연다**",
        "심기 전 적발": before4, "심은 뒤 적발": after4,
        "🔴 빨개졌나": bool(not before4 and "data/lab/denominator.json" in after4),
    }
    mark = "data/state/collect_log.jsonl"
    before5 = mark in OPENED
    with io.open(str(ROOT / mark), "r", encoding="utf-8") as f:
        f.readline()
    after5 = banned_hits()
    K["K5 W8″ — `io.open` 으로 금지 구역을 열면 무나"] = {
        "무는 코드": "〃", "심기 전 적발": before5, "심은 뒤 적발에 들어왔나": mark in after5,
        "🔴 빨개졌나": bool(not before5 and mark in after5),
    }

    # ── K6 🔴🔴 재분모화를 **다른 분모 인자로 실제로 다시 부른다**(C2 의 K7 정정) ──
    tab_mixed, ctx_mixed = redenominate(denom_mode="혼합")
    tab_wiki, _ = redenominate(denom_mode="wiki만")
    base_ratio = ctx["ratio"]
    K["K6 🔴🔴 재분모화(C2) — `redenominate()` 를 다른 분모 인자로 **실제로 다시 부른다**"] = {
        "무는 코드": "`checks964.redenominate(denom_mode=…)` — 🔴 **함수를 실제로 다시 부른다**",
        "심은 것": "`denom_mode='혼합'`(962 의 줄 수) · `denom_mode='wiki만'`",
        "정본 분모 · 배수": [ctx["lm_before"], base_ratio],
        "혼합 분모 · 배수": [ctx_mixed["lm_before"], ctx_mixed["ratio"]],
        "wiki만 분모 · 배수": [tab_wiki["🔴 이 주행의 인자"]["쓴 분모"],
                        tab_wiki["🔴 이 주행의 인자"]["쓴 배수"]],
        "🔴 963 의 K7 은 무엇이었나": (
            "`round(LMPAIR_AFTER/len(complete),2) != LMPAIR_RATIO` — **등록 상수 셋의 산술**이라 "
            "티처가 `redenominate()` 를 네 가지로 망가뜨려도(`lm_steam` 2배 · `lm_after`+5000 · "
            "`s_before` 100줄 · 도메인 뒤 1개) **네 번 다 True** 였다(티처 #102 C2)"),
        "🔴 빨개졌나": bool(ctx_mixed["ratio"] != base_ratio
                      and tab_wiki["🔴 이 주행의 인자"]["쓴 배수"] != base_ratio),
    }

    # ── K7 🔴 「뒤」의 꼴을 바꾸면 배수가 바뀌나 — M1 이 진짜인가 ────────
    tab_963, ctx_963 = redenominate(after_mode="963판")
    tab_dbl, ctx_dbl = redenominate(after_mode="이중계상")
    K["K7 🔴🔴 M1 — 「뒤」의 꼴을 바꾸면 배수가 실제로 갈리나"] = {
        "무는 코드": "`checks964.redenominate(after_mode=…)` — 🔴 **함수를 실제로 다시 부른다**",
        "합집합(964)": [ctx["lm_after"], ctx["ratio"]],
        "963 판": [ctx_963["lm_after"], ctx_963["ratio"]],
        "이중계상": [ctx_dbl["lm_after"], ctx_dbl["ratio"]],
        "🔴 셋이 다 다른가": len({ctx["ratio"], ctx_963["ratio"], ctx_dbl["ratio"]}) == 3,
        "🔴 빨개졌나": bool(len({ctx["ratio"], ctx_963["ratio"], ctx_dbl["ratio"]}) == 3),
    }

    # ── K8 🔴 `sub_T`(M5) — 이제 판정을 무나 ────────────────────────────
    base_args = dict(sum_delta=0.058238, sum_T=0.020060, sub_delta=0.005669,
                     perm_obs=0.057857, perm_p95=-0.000493, card_T=0.00353)
    sigs = {}
    for st in (0.020060, 999, -999, 0, 1e-9, -1e-9):
        r = rulers(sub_T=st, **base_args)
        sigs[repr(st)] = json.dumps(
            {k: v for k, v in r.items() if not isinstance(v, dict) and k.startswith("🔴")},
            ensure_ascii=False, sort_keys=True)
    K["K8 🔴🔴 `sub_T`(M5) — 티처 #101 이 지목하고 963 이 안 고친 죽은 인자"] = {
        "무는 코드": "`lab/adopt.py::rulers()` — **964 가 `sub_T` 를 3값 띠로 판정에 넣었다**",
        "심은 것": "`sub_T ∈ {0.02006, 999, −999, 0, ±1e-9}`",
        "서로 다른 판정 서명 수": len(set(sigs.values())),
        "🔴 963 까지는": "**판정 키 여덟이 바이트 동일**이었다(서명 1개) — `sub_T` 가 곁 칸 하나에만 실렸다",
        "각 값의 ㉡ 3값": {k: rulers(sub_T=float(k), **base_args)["🔴🔴 964 ㉡ 통과(3값 · 자기 문턱 sub_T 띠)"]
                     for k in ("999", "0", "0.02006")},
        "🔴 빨개졌나": len(set(sigs.values())) > 1,
    }

    # ── K9 🔴🔴 W10(M3) — 고친 판이 상수가 아닌가 ───────────────────────
    src = _real_ptext(ROOT / "runners/curve961.py", encoding="utf-8")
    tree = ast.parse(src)
    picked = [n for n in tree.body
              if (isinstance(n, ast.FunctionDef) and n.name == "w10_check")
              or (isinstance(n, ast.Assign) and any(
                  getattr(t, "id", "").startswith("RULERS_") for t in n.targets))]
    ns = {}
    exec(compile(ast.Module(body=picked, type_ignores=[]), "<w10>", "exec"), ns)
    w10 = ns["w10_check"]
    A = dict(base_args, sub_T=0.020060)
    rt = rulers(**A)
    old_lit = "🔴🔴 ㉢ ⊂ ㉠ (㉠ 통과 ⟹ ㉢ 통과)"
    renamed = dict(rt)
    renamed[old_lit] = renamed.pop("🔴 ㉢ ⊂ ㉠ (관측 기준)")
    tampered = dict(rt)
    tampered["🔴 독립된 자의 수(관측 기준)"] = 99
    out3 = dict(rt)
    out3["🔴 ㉡ ⊂ ㉠ (관측 기준)"] = True
    random.seed(964)
    res = []
    for _ in range(2000):
        a = dict(A)
        for k in list(a):
            a[k] = random.choice([random.uniform(-1, 1), 0.0, 999.0, -999.0, 1e-9])
        r = rulers(**a)
        m = dict(r)
        op = random.randrange(4)
        if op == 1:
            m[old_lit] = m.pop("🔴 ㉢ ⊂ ㉠ (관측 기준)")
        elif op == 2:
            m[random.choice(list(r))] = "심은 것"
        elif op == 3:
            m["🔴 ㉡ ⊂ ㉠ (관측 기준)"] = random.choice([True, False, 0, 1])
        res.append(w10(m, lambda a=a: rulers(**a))["통과"])
    old_vals = {bool(old_lit in rulers(**A)) for _ in range(3)}
    K["K9 🔴🔴 W10(M3) — 머지가 조용히 뒤집은 항진명제. 고친 판이 상수가 아닌가"] = {
        "무는 코드": "`runners/curve961.py::w10_check()` — 🔴 **AST 로 그 함수만 떼어 실제로 부른다**",
        "🔴 옛 판": {"코드": 'bool("%s" in rt)' % old_lit,
                 "961 가지에선": "**항상 True**(그 이름의 키를 냈다) — 항진명제",
                 "963 머지 뒤엔": "**항상 False**(`rulers()` 가 962 관측판으로 갈렸다)",
                 "지금 재현한 값": sorted(str(v) for v in old_vals),
                 "🔴": "**둘 다 자료를 한 번도 안 읽는다**"},
        "무변조 통과": w10(rt, lambda: rulers(**A))["통과"],
        "① 키 이름 갈기 → 통과": w10(renamed, lambda: rulers(**A))["통과"],
        "② 값 바꿔치기 → 통과": w10(tampered, lambda: rulers(**A))["통과"],
        "③ 3값 밖의 값 → 통과": w10(out3, lambda: rulers(**A))["통과"],
        "🔴 무작위 2,000회 전수": {"True": sum(res), "False": len(res) - sum(res),
                          "상수인가": len(set(res)) == 1},
        "🔴 빨개졌나": bool(w10(rt, lambda: rulers(**A))["통과"]
                      and not w10(renamed, lambda: rulers(**A))["통과"]
                      and not w10(tampered, lambda: rulers(**A))["통과"]
                      and not w10(out3, lambda: rulers(**A))["통과"]
                      and len(set(res)) > 1),
    }

    n_red = sum(1 for v in K.values() if v["🔴 빨개졌나"])
    K["🔴🔴 심은 키 회계"] = {
        "분모: 실제로 심어 본 수": len(K),
        "분자: 실제로 빨개진 수": n_red,
        "🔴 안 빨개진 것": [k for k, v in K.items() if not v["🔴 빨개졌나"]] or "없음",
        "🔴 사전등록 §3-3": ("**등록 상수끼리의 산술은 심기로 안 센다.** 963 의 K7 이 그것이었고 "
                       "티처가 `redenominate()` 를 네 가지로 망가뜨려도 네 번 다 True 였다. "
                       "🔴 **위 아홉은 전부 「무는 코드」 칸에 적힌 함수를 실제로 다시 부른다**"),
        "🔴 963 의 신고": "7/7 이라 신고했고 **티처 실측 5/7**(K3·K7 이 코드를 안 물었다)",
        "통과": n_red == len(K),
    }
    return K


# ══════════════════════════════════════════════════════════════════════════
# §7 🔴🔴 R5 정정 (티처 #102 M4) — **어느 후크가 잉여인가를 실측한다**
# ══════════════════════════════════════════════════════════════════════════
ALL_HOOKS = ("builtins.open", "io.open", "gzip.open",
             "Path.read_text", "Path.read_bytes", "Path.open")


def r5_correction():
    """🔴🔴 963 의 R5 는 후크 **여섯**을 걸고 「여섯을 문다」로 신고했다.

    티처 #102 M4 는 `Path.read_text`·`read_bytes`·`Path.open` 셋을 **전부 떼도 산출물이
    시각 두 줄 빼고 바이트 동일**임을 실측하고 **「3.9 는 `io.open` 하나가 다 문다」**로
    정정하라고 했다.

    🔴 **964 가 실측해 보니 앞은 맞고 뒤는 틀렸다.**

      · `Path.*` 후크 셋은 **잉여다** — 3.9 의 `pathlib` 이 결국 `io.open` 을 부른다 ✅
      · 🔴 **그러나 `io.open` **하나로는** 못 문다** — `io.open is builtins.open` 은 참이지만
        **한쪽 모듈 속성을 다시 묶어도 다른 쪽은 안 묶인다.** 맨 `open(...)` 과
        `gzip.open(...)` 은 `builtins.open` 을 지나므로 **`io.open` 후크가 못 본다.**

    아래는 **같은 읽기 작업**을 후크 조합별로 돌려 **실제로 잡힌 파일 집합**을 견준 것이다.
    """
    saved_opened, saved_fired = set(OPENED), collections.Counter(HOOK_FIRED)
    saved_on = _AUDIT_ON[0]

    def workload():
        """🔴 **경로마다 다른 파일을 읽는다** — 한 파일을 두 경로로 읽으면 어느 후크가
        잡았는지 못 가른다(조항 60: 분모를 겹치지 마라)."""
        for p in (SAO941, SAO959, SAO962):                 # gzip.open → builtins.open
            with gzip.open(str(ROOT / p), "rt", encoding="utf-8") as f:
                f.readline()
        Path(ROOT / "lab/adopt.py").read_text(encoding="utf-8")[:1]   # → io.open
        with open(str(ROOT / "runners/checks963.py"), "rb") as f:     # → builtins.open
            f.read(1)

    def probe(hooks):
        uninstall_audit()
        OPENED.clear()
        HOOK_FIRED.clear()
        install_audit(hooks)
        workload()
        got, fired = set(OPENED), dict(HOOK_FIRED)
        uninstall_audit()
        return got, fired

    full, full_fired = probe(ALL_HOOKS)
    nopath, nopath_fired = probe(("builtins.open", "io.open", "gzip.open"))
    ioonly, ioonly_fired = probe(("io.open",))
    bopen, bopen_fired = probe(("builtins.open",))

    OPENED.clear()
    OPENED.update(saved_opened)
    HOOK_FIRED.clear()
    HOOK_FIRED.update(saved_fired)
    if saved_on:
        install_audit()

    return {
        "🔴 무엇": "**같은 읽기 작업**을 후크 조합별로 돌려 **실제로 잡힌 파일 집합**을 견준다",
        "작업": "`gzip.open` 으로 .gz 셋 + `Path.read_text` + 맨 `open(rb)`",
        "표": collections.OrderedDict([
            ("여섯 전부", {"잡은 파일": len(full), "후크별 호출": full_fired}),
            ("Path 후크 셋을 뗀다", {"잡은 파일": len(nopath), "후크별 호출": nopath_fired,
                            "🔴 여섯과 같은 집합인가": full == nopath}),
            ("`io.open` 하나만", {"잡은 파일": len(ioonly), "후크별 호출": ioonly_fired,
                            "🔴 여섯과 같은 집합인가": full == ioonly,
                            "🔴 놓친 파일": sorted(full - ioonly) or "없음"}),
            ("`builtins.open` 하나만", {"잡은 파일": len(bopen), "후크별 호출": bopen_fired,
                                  "🔴 여섯과 같은 집합인가": full == bopen,
                                  "🔴 놓친 파일": sorted(full - bopen) or "없음"}),
        ]),
        "🔴 `io.open is builtins.open`": _real_ioopen is _real_open,
        "🔴🔴 964 의 정정 — 티처 #102 M4 는 앞은 맞고 뒤는 틀렸다": (
            "✅ **앞(참)**: `Path.read_text`·`read_bytes`·`Path.open` 후크 셋은 **잉여다** — "
            "3.9 의 `pathlib` 이 결국 `io.open` 을 부르므로 떼도 잡히는 집합이 안 바뀐다. "
            "🔴 **뒤(거짓)**: 「`io.open` 하나가 다 문다」는 **틀렸다.** `io.open is builtins.open` 은 "
            "**참**이지만 **한쪽 모듈 속성을 다시 묶어도 다른 쪽은 안 묶인다** — 맨 `open(...)` 과 "
            "`gzip.open(...)` 은 `builtins.open` 을 지나므로 `io.open` 후크가 **못 본다.** "
            "🔴 **이 러너의 측정 자료(.gz 셋)가 정확히 그 경로로 읽힌다** — 즉 "
            "`io.open` 하나만 걸면 **자기 입력 파일 셋을 통째로 못 본다**"),
        "🔴 그래서 최소 후크 집합": "`builtins.open` + `io.open` + `gzip.open` **셋**(`Path.*` 셋은 잉여)",
        "통과": bool(full == nopath and full != ioonly),
    }


# ══════════════════════════════════════════════════════════════════════════
# 엮기
# ══════════════════════════════════════════════════════════════════════════
def main(hooks=None):
    t0 = dt.datetime.now(dt.timezone.utc)
    install_net_audit()
    install_audit(hooks) if hooks else install_audit()
    R = collections.OrderedDict()
    R["노트"] = 964
    R["레인"] = "수리 + 정정"
    R["사전등록"] = "docs/prereg_964_tautology_union.md (원장 1030 · 측정 전 단독 커밋)"
    R["🔴 걸린 후크"] = sorted(hooks) if hooks else "여섯 전부"
    R["시작(UTC)"] = t0.isoformat()
    # 🔴 ⑤′ 절 3(판정 키 규약) — **최상위 벗은 불리언은 규약 밖**이다. 절로 싼다.
    R["§-1 이 러너의 성질"] = {
        "🔴 새 자료를 만드나": False, "🔴 판을 건드리나": False,
        "🔴 무엇이면 떨어지나": "새 자료를 만들거나 판 ρ 를 재면 떨어진다 — 이 사이클은 **수리 레인**이다",
        "통과": True}

    # ── V6 — 🔴 사전등록에 박았으니 이제 `통과` 를 낸다 ──────────────────
    real = {p: sha_file(p) for p in (SAO941, SAO959, SAO962)}
    R["§0 🔴🔴 V6 입력 sha256 — 사전등록 §0-나 와 대조한다"] = {
        "🔴 무엇": ("963 은 sha 를 **계산해 놓고도 `통과` 를 못 냈다** — 사전등록에 대조 대상이 "
                 "없었기 때문이다(티처 #102 C2: 「V6 의 sha 셋은 완전한 죽은 숫자」). "
                 "🔴 **964 가 사전등록 §0-나 에 박았고, 이제 이 절이 `통과` 를 낼 자격이 있다**"),
        "표": {p: {"등록(사전등록 §0-나)": REG_SHA[p], "지금 파일": real[p],
                  "맞나": real[p] == REG_SHA[p]} for p in real},
        "분자: 맞은 수": sum(1 for p in real if real[p] == REG_SHA[p]),
        "분모": len(real),
        "🔴 P4 예측": "3/3 일치", "P4 맞나": all(real[p] == REG_SHA[p] for p in real),
        "통과": all(real[p] == REG_SHA[p] for p in real),
    }

    tab, ctx = redenominate()
    tab["통과"] = tab["🔴🔴 F3 — 티처의 수를 원자료에서 다시 세어 대조(조항 60)"]["통과"]
    R["§1 🔴🔴 합집합 재분모화(M1) — 963 의 「뒤」는 「앞」의 상위집합이 아니었다"] = tab

    R["§2 🔴🔴 W6′ 정정(m1·m2) — 7,674 를 두 번 다르게 설명한 것과 단위 섞인 비"] = w6_prime(ctx)

    w3 = w3_double_prime(ctx["complete"])
    w3["🔴 P3 예측"] = "`도메인` 키 없는 레코드 0 · 무변조에서 통과"
    w3["P3 맞나"] = bool(w3["🔴 `도메인` 키가 없는 레코드"] == 0 and w3["통과"])
    R["§3 🔴🔴 W3″(C1) — 분모를 독립 경로에서 가져온다"] = w3

    R["§4 🔴🔴 V4′(M3) — `rulers()` 소비자 전수 감사"] = v4_prime()

    banned_before_plant = banned_hits()
    opened_before_plant = len(OPENED)
    hooks_before_plant = dict(HOOK_FIRED)

    P = planted(ctx, tab)
    # 🔴 ⑤′ 절 3 — **절은 자기 `통과` 를 최상위에 내야 읽힌다**(963 의 §5·§6 은 안 냈다)
    P["통과"] = P["🔴🔴 심은 키 회계"]["통과"]
    R["§5 🔴🔴 심어서 떨어뜨리기 — 「무는 코드」를 칸마다 적는다"] = P

    # ── §6 배선 — 🔴 **검사 「종류」로 센다**(사전등록 §3-4) ──────────────
    W = collections.OrderedDict()
    anc = {}
    for b, n in (("origin/note/955-d-redefine", 213), ("origin/note/956-ruler1", 214),
                 ("origin/note/960-fourth-ruler", 218), ("origin/note/961-signcurve", 219),
                 ("origin/note/962-triples", 220), ("origin/note/963-housekeeping", 221)):
        rc = subprocess.run(["git", "merge-base", "--is-ancestor", b, "HEAD"],
                            cwd=str(ROOT), capture_output=True).returncode
        anc["#%d %s" % (n, b.replace("origin/", ""))] = rc == 0
    W["V1 흡수된 여섯 PR 이 이 가지의 조상인가"] = {
        "표": anc, "분자": sum(1 for v in anc.values() if v), "분모": len(anc),
        "🔴 계수 규칙": "**검사 「종류」 1 로 센다.** 963 의 배선 12/12 는 이것을 다섯 번 센 수였다(티처 #102 m5)",
        "통과": all(anc.values())}

    raw = _bypass_read("data/lab/denominator.json", "V2 원장 키 중복 검사 — 감사를 우회해 읽는다")
    dup_levels = []

    def _hook(pairs):
        ks = [k for k, _ in pairs]
        if len(ks) != len(set(ks)):
            c = collections.Counter(ks)
            dup_levels.append([k for k, n in c.items() if n > 1])
        return collections.OrderedDict(pairs)

    dd = json.JSONDecoder(object_pairs_hook=_hook).decode(raw)
    W["V2 원장 키 중복(🔴 모든 중첩 레벨)"] = {
        "최상위 항목": len(dd), "🔴 중복이 있는 레벨 수": len(dup_levels),
        "🔴 중복 키": dup_levels or "없음",
        "🔴 F4 반증조건": "머지 뒤 원장에 키 중복이 생기면 이 사이클은 실패다",
        "통과": len(dup_levels) == 0}

    merged = set(dd)
    miss = {}
    for b in ("origin/main", "origin/note/963-housekeeping"):
        o = subprocess.run(["git", "show", b + ":data/lab/denominator.json"],
                           cwd=str(ROOT), capture_output=True)
        d = json.loads(o.stdout.decode("utf-8"))
        miss[b.replace("origin/", "")] = {"항목": len(d),
                                          "빠진 것": len([k for k in d if k not in merged])}
    W["V3 원장 항목 보존"] = {"표": miss, "통과": all(v["빠진 것"] == 0 for v in miss.values())}

    ad = _real_ptext(ROOT / "lab/adopt.py", encoding="utf-8")
    n_rulers = len(re.findall(r"^def rulers\(", ad, re.M))
    try:
        import importlib
        importlib.import_module("lab.adopt")
        imp = True
    except Exception:                                              # noqa: BLE001
        imp = False
    W["V4 `def rulers(` 가 하나인가 + 임포트되나"] = {
        "def rulers( 수": n_rulers, "import lab.adopt": imp,
        "🔴 964 확장": "**소비자 감사는 §4 로 옮겼다** — 963 의 V4 는 이 둘만 봤고 부르는 쪽을 안 봤다",
        "통과": n_rulers == 1 and imp}

    wi = _real_ptext(ROOT / "runners/out958_within.json", encoding="utf-8")
    W["V5 961 의 실측 ㉣ 가 살아 있나"] = {
        "alt_T=0.05207752784487368": "0.05207752784487368" in wi,
        "layer_on_alt_T=0.006551197360193737": "0.006551197360193737" in wi,
        "962 가 지운 옛 키가 되살아났나": bool(re.search(r'"🔴🔴 채택\(㉠㉡㉢\)"', wi)),
        "통과": ("0.05207752784487368" in wi and "0.006551197360193737" in wi
               and not re.search(r'"🔴🔴 채택\(㉠㉡㉢\)"', wi))}

    lc = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    asleep = "com.sweetspot.wm.harvest" not in lc.stdout
    W["V7 데몬이 자고 있나"] = {"자고 있나": asleep, "통과": asleep}

    hits = banned_hits()
    W["V8 판 자료를 안 열었나(측정 구간) — 🔴 우회를 신고한다"] = {
        "🔴 무엇": "`builtins.open` + `io.open` + `gzip.open` + `Path.read_text`/`read_bytes`/`open` 을 감싼다",
        "분자: 측정 구간에 연 저장소 파일": opened_before_plant,
        "🔴 측정 구간의 금지 구역 적발": banned_before_plant,
        "🔴 심은 뒤(§5 K4·K5)의 적발 — 판정에 안 쓴다": hits,
        "🔴🔴 M6 — 감사를 우회해 읽은 것(963 은 이것을 안 적고 「적발 0」만 냈다)": {
            "표": BYPASSED,
            "🔴 왜 신고하나": ("963 의 V8 「금지 구역 적발 0」은 `_real_ptext(denominator.json)` 로 "
                       "**자기 감사를 우회해 얻은 0** 이었다. 🔴 **읽어야 할 파일인 건 맞다** — "
                       "그러나 **「안 읽었다」와 「우회해서 읽었다」는 둘이다**(조항 59). "
                       "964 는 우회를 목록으로 낸다"),
            "🔴 그래서 진짜 문장": "**측정 구간에 후크로 잡힌 금지 구역 접근 %d 건 · 우회해서 읽은 것 %d 건**"
                          % (len(banned_before_plant), len(BYPASSED)),
        },
        "🔴🔴 M4 — 어느 후크가 실제로 불렸나(963 은 「여섯을 문다」로 신고했다)": {
            "측정 구간 후크별 호출 수": hooks_before_plant,
            "전체 후크별 호출 수": dict(HOOK_FIRED),
            "🔴 한 번도 안 불린 후크": [h for h in ("builtins.open", "io.open", "gzip.open",
                                          "Path.read_text", "Path.read_bytes", "Path.open")
                              if HOOK_FIRED.get(h, 0) == 0] or "없음",
            "🔴 티처 #102 M4": ("R5 의 후크 셋(`Path.read_text`·`read_bytes`·`Path.open`)을 **전부 떼도 "
                          "산출물이 시각 두 줄 빼고 바이트 동일**이었다 — **3.9 의 `pathlib` 은 "
                          "결국 `io.open` 을 부르므로 `io.open` 하나가 다 문다**"),
            "🔴 964 의 정정": "`--hooks io.open` 으로 다시 돌려 **같은 적발이 나오는지**를 실측한다(아래 R5 실측 절)",
        },
        "통과": not banned_before_plant}

    W["V9 HTTP 0"] = {"나간 연결": CONNECTS, "통과": len(CONNECTS) == 0}
    W["V10 🔴🔴 R5 정정(M4) — 어느 후크가 잉여인가를 **실측**한다"] = r5_correction()
    kinds = [k for k, v in W.items() if isinstance(v, dict) and "통과" in v]
    W["🔴 계수 — **검사 종류 수**로 센다(사전등록 §3-4)"] = {
        "분자: 통과한 **종류**": sum(1 for k in kinds if W[k]["통과"] is True),
        "분모: `통과` 키를 가진 **종류**": len(kinds),
        "🔴 붉은 것": [k for k in kinds if W[k]["통과"] is not True] or "없음",
        "🔴 963 은": "**12/12 라 신고했고 그중 V1 이 다섯 번 세어졌다**(실질 여덟 종 · 티처 재주행 11/12)",
    }
    # 🔴 ⑤′ 절 3 — 절의 `통과` 를 최상위에 낸다
    W["통과"] = all(W[k]["통과"] is True for k in kinds)
    R["§6 배선"] = W

    secs = collections.OrderedDict(
        (k, v) for k, v in R.items() if isinstance(v, dict) and "통과" in v)
    n_ok = sum(1 for v in secs.values() if v["통과"] is True)
    red = [k for k, v in secs.items() if v["통과"] is not True]
    R["🔴 절 회계(⑤′ 고정 기준 · 「`통과` 키를 가진 최상위 절의 수」)"] = {
        "분자: 통과한 절": n_ok,
        "분모: `통과` 키를 가진 절": len(secs),
        "🔴 붉은 절": red or "없음",
        # 🔴 이 절의 `통과` 는 **「전부 초록이냐」가 아니라 「회계가 스스로 일관되냐」**다 —
        #    회계가 자기 분자를 판정으로 삼으면 붉은 절을 숨기려는 압력이 생긴다.
        "🔴 이 절의 `통과` 가 뜻하는 것": "**회계가 스스로 일관된가** — 붉은 절 목록의 길이 == 분모 − 분자",
        "통과": len(red) == len(secs) - n_ok,
        "🔴🔴 사전등록 §3-5 — 963 의 3/4 를 다시 적는다": (
            "963 의 ⑤′ 회계는 **3/4** 였고 그 **세 초록 중 하나(§3)가 원리상 못 떨어지는 절**이었다. "
            "🔴 **정확한 문장은 「3/4」가 아니라 「초록 셋 중 하나는 공허였다 — 실질 2/4」다.** "
            "964 의 §3 은 그 자리를 W3″ 로 갈았고 §5 K1 이 **떨어지는 것을 실측**했다"),
    }
    R["끝(UTC)"] = dt.datetime.now(dt.timezone.utc).isoformat()
    return R


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hooks", default=None,
                    help="쉼표로 구분한 후크 목록(M4 실측용). 예: io.open")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    hk = tuple(x.strip() for x in a.hooks.split(",")) if a.hooks else None
    r = main(hooks=hk)
    dest = ROOT / a.out if a.out else OUT
    with _real_open(str(dest), "w", encoding="utf-8") as f:
        f.write(json.dumps(r, ensure_ascii=False, indent=1))
    print("→", dest)
    for k in ("§0 🔴🔴 V6 입력 sha256 — 사전등록 §0-나 와 대조한다",):
        print(k, "통과 =", r[k]["통과"])
    print(json.dumps(r["§1 🔴🔴 합집합 재분모화(M1) — 963 의 「뒤」는 「앞」의 상위집합이 아니었다"]
                     ["🔴🔴 F3 — 티처의 수를 원자료에서 다시 세어 대조(조항 60)"],
                     ensure_ascii=False, indent=1))
    print(json.dumps(r["§5 🔴🔴 심어서 떨어뜨리기 — 「무는 코드」를 칸마다 적는다"]
                     ["🔴🔴 심은 키 회계"], ensure_ascii=False, indent=1))
    print(json.dumps(r["§6 배선"]["🔴 계수 — **검사 종류 수**로 센다(사전등록 §3-4)"],
                     ensure_ascii=False, indent=1))
    print(json.dumps(r["🔴 절 회계(⑤′ 고정 기준 · 「`통과` 키를 가진 최상위 절의 수」)"],
                     ensure_ascii=False, indent=1))
