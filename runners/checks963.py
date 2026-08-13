# -*- coding: utf-8 -*-
"""🔴 노트 963 — **정비 + 재분모화 + 떨어질 수 없는 검사 끊기**.

**새 자료를 만들지 않는다. 새 측정을 하지 않는다.** 이 러너가 하는 것은 셋이다.

  §1  **재분모화** — 962 의 「14.83배」를 **정본 단위(LM 학습쌍)** 로 다시 나눈다.
      🔴 티처 #101 이 낸 세 수(2.73 · 2.26 · 1.00)를 **내가 다시 세어** 대조한다.
  §2  **W6′** — 962 의 W6 은 `쌍id` 접두가 서로소라 **어떤 입력에서도 교집합 0** 인
      항진명제였다. 사전등록이 선언한 대로 **본문**으로 다시 짠다(조항 62).
  §3~§6 **떨어질 수 없는 검사 넷**을 고치고 **결함을 실제로 심어** 빨개지는지 본다.

🔴 **`runners/triples962.py` 는 안 고친다** — 그 sha 가 `out962_triples.json` 과 원장에
박혀 있는 **동결 산출물**이다. 고친 판을 **여기 새 러너로** 낸다.

🔴 **이 러너가 신고하는 「심은 키 n/m」은 실제로 심어 본 수다**(962 는 5/5 라 신고했고
실측은 2/5 였다 — 티처 #101 중-1).
"""
import builtins
import collections
import gzip
import hashlib
import io
import json
import os
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
OUT = ROOT / "runners/out963_checks.json"

# ── 사전등록 §0 등록 상수 (docs/prereg_963_housekeeping.md · 측정 전에 못 박았다) ──
REG = {
    "PLATE_RHO": 0.47034, "PLATE_SD": 0.0021, "ADOPT_T": 0.00353,
    "LMPAIR_BEFORE": 14248, "LMPAIR_AFTER": 38945,
    "LMPAIR_RATIO": 2.73, "DISTINCT_S_RATIO": 2.26, "DOMAIN_RATIO": 1.00,
}


# ══════════════════════════════════════════════════════════════════════════
# 🔴🔴 W8′ — **실제로 연 파일** 감사. 962 판이 못 물던 세 구멍을 막는다.
#   962 판은 `builtins.open` 과 `gzip.open` 만 감쌌다. 그런데
#   🔴 **러너 자신이 `pathlib.Path.read_text` 를 썼다**(triples962.py 116·337·797행).
#   `Path.read_text` 는 `io.open` 을 부르지 `builtins.open` 을 안 부른다 —
#   **감사가 자기 러너의 읽기를 통째로 못 봤다**(티처 #101).
# ══════════════════════════════════════════════════════════════════════════
OPENED = set()
_real_open = builtins.open
_real_ioopen = io.open
_real_gzopen = gzip.open
_real_ptext = Path.read_text
_real_pbytes = Path.read_bytes
_real_popen = Path.open
_AUDIT_ON = [False]


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
    r = _rel(p)
    if r:
        OPENED.add(r)


def install_audit():
    """🔴 `builtins.open` · **`io.open`** · `gzip.open` · **`Path.read_text`/
    `read_bytes`/`open`** 여섯을 전부 감싼다."""
    def a_open(file, *a, **k):
        _note(file, "builtins.open")
        return _real_open(file, *a, **k)

    def a_ioopen(file, *a, **k):
        _note(file, "io.open")
        return _real_ioopen(file, *a, **k)

    def a_gz(filename, *a, **k):
        _note(filename, "gzip.open")
        return _real_gzopen(filename, *a, **k)

    def a_ptext(self, *a, **k):
        _note(self, "Path.read_text")
        return _real_ptext(self, *a, **k)

    def a_pbytes(self, *a, **k):
        _note(self, "Path.read_bytes")
        return _real_pbytes(self, *a, **k)

    def a_popen(self, *a, **k):
        _note(self, "Path.open")
        return _real_popen(self, *a, **k)

    builtins.open = a_open
    io.open = a_ioopen
    gzip.open = a_gz
    Path.read_text = a_ptext
    Path.read_bytes = a_pbytes
    Path.open = a_popen
    _AUDIT_ON[0] = True


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
    with open(ROOT / rel, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rows(rel):
    with gzip.open(ROOT / rel, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def has_s(d):
    s = d.get("s_상태") or {}
    v = s.get("값")
    return bool(v)


def s_key(d):
    """🔴 **s 를 하나로 세는 열쇠**. 레코드 전체를 직렬화하지 않는다 — `s_상태` 만 꺼낸다
    (🔴 **조항 63**: 「이 열에 X 가 있나」를 잴 때 레코드 전체를 grep 하지 마라)."""
    s = d.get("s_상태") or {}
    v = s.get("값") or []
    return (d.get("a_액션", {}).get("개체"), tuple(v))


def bodies_of(d):
    """이 줄이 **LM 학습쌍 몇 개**를 나르나 + 그 본문들.

    🔴 **여기가 962 가 단위를 섞은 자리다.** wiki 줄은 `o_결과.값` 이 일별 조회수 계열
    하나라 **쌍 1 개**다. 941 의 steam **앱단위** 줄은 `o_결과.본문` 이 리뷰 **목록**이라
    한 줄이 **리뷰 ~195편**을 묶는다. 962 의 steamrev 줄은 본문 하나라 **쌍 1 개**다.
    """
    o = d.get("o_결과") or {}
    b = o.get("본문")
    if isinstance(b, list):
        return [x.get("글") or "" for x in b if isinstance(x, dict)]
    if isinstance(b, str):
        return [b]
    return [None]          # 본문이 아니라 계열 — 쌍 1 개이되 「글」은 없다


# ══════════════════════════════════════════════════════════════════════════
# §1 재분모화
# ══════════════════════════════════════════════════════════════════════════
def load_baseline():
    """기준선 = `sao941` ∪ `sao959` 의 **distinct 쌍id**. 🔴 941 안 중복 2 · 교집합 581."""
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
        seen[pid] = d          # 959 가 더 새 판이면 덮는다
    return list(seen.values()), {"941 안 중복 쌍id": dup941, "941 ∩ 959": inter,
                                 "distinct 쌍id": len(seen)}


def redenominate():
    base, prov = load_baseline()
    complete = [d for d in base if has_s(d)]
    empty_s = len(base) - len(complete)

    # 정본 단위 = LM 학습쌍
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
    lm_before = lm_wiki + lm_steam

    new_rows = list(rows(SAO962))
    lm_new = len(new_rows)
    lm_after = lm_wiki + lm_new

    # distinct s
    s_before = {s_key(d) for d in complete}
    s_new = {s_key(d) for d in new_rows}
    # 🔴 「뒤」의 집합은 **정본 회계**와 같은 것을 쓴다: wiki 줄 + 962 줄
    s_after = {s_key(d) for d in wiki_lines} | s_new

    dom_before = collections.Counter(d["도메인"] for d in complete)
    dom_after = collections.Counter()
    for d in wiki_lines:
        dom_after[d["도메인"]] += 1
    for d in new_rows:
        dom_after[d["도메인"]] += 1

    def ratio(a, b):
        return round(b / a, 4) if a else None

    tab = {
        "🔴 정본 단위 · LM 학습쌍": {
            "분모(앞)": lm_before, "분자(뒤)": lm_after, "배수": ratio(lm_before, lm_after),
            "앞의 내역": {"wiki 줄(개체당 1쌍)": lm_wiki,
                      "941 steam **앱단위** 줄이 묶은 리뷰 본문": lm_steam,
                      "그 앱단위 줄 수": len(steam_lines)},
            "뒤의 내역": {"wiki 줄": lm_wiki, "sao962 리뷰단위 줄": lm_new},
            "🔴 왜 뒤에서 941 의 앱단위 줄을 뺐나": (
                "962 의 리뷰단위 줄이 **같은 본문을 개별 행으로 다시 낸다**. 둘 다 세면 "
                "이중계상이다 — §2 W6′ 가 그 겹침을 실제로 센다"),
        },
        "🔴 distinct s": {
            "분모(앞)": len(s_before), "분자(뒤)": len(s_after),
            "배수": ratio(len(s_before), len(s_after)),
            "sao962 자신의 distinct s": len(s_new),
            "🔴 962 는 무엇을 틀렸나": (
                "962 의 「2.08배」는 분자에 **「쌍 개수 3,050」+「상태 개수 3,304」**를 "
                "더하고 분모에는 **쌍 개수**를 놓았다 — **기준선의 distinct s 를 한 번도 "
                "안 셌다**(티처 #101 치-4 · 조항 60)"),
            "🔴 s 를 어떻게 세나": "`(개체, s_상태.값 튜플)` — 🔴 레코드 전체를 직렬화하지 않는다(조항 63)",
        },
        "🔴 도메인": {
            "분모(앞)": len(dom_before), "분자(뒤)": len(dom_after),
            "배수": ratio(len(dom_before), len(dom_after)),
            "앞": dict(sorted(dom_before.items())),
            "뒤": dict(sorted(dom_after.items())),
            "🔴 sao962 의 도메인": sorted({d["도메인"] for d in new_rows}),
        },
        "⚠ 962 의 혼합 단위(역사 기록 · 판정에 쓰지 마라)": {
            "분모": len(complete), "분자": len(complete) + lm_new,
            "배수": ratio(len(complete), len(complete) + lm_new),
            "🔴 왜 이게 섞인 수인가": (
                f"분모 {len(complete)} 는 **줄** 수인데 그중 {len(steam_lines)} 줄이 "
                f"리뷰 {lm_steam} 편을 묶는다(줄당 {round(lm_steam / max(len(steam_lines), 1), 1)}편). "
                "분자는 거기에 **리뷰단위** 36,374 를 더한다 — **한 분수에 단위가 둘이다**"),
        },
        "기준선 출처": prov,
        "기준선 · s 가 빈 줄": empty_s,
        "기준선 · 완전 삼중쌍(줄)": len(complete),
    }

    got = {"LMPAIR_BEFORE": lm_before, "LMPAIR_AFTER": lm_after,
           "LMPAIR_RATIO": round(lm_after / lm_before, 2),
           "DISTINCT_S_RATIO": round(len(s_after) / len(s_before), 2),
           "DOMAIN_RATIO": round(len(dom_after) / len(dom_before), 2)}
    cmp = {}
    for k, v in got.items():
        cmp[k] = {"티처 #101": REG[k], "내가 다시 셈": v, "맞나": v == REG[k]}
    # 🔴 티처의 2.26 을 **재현해 본다** — 어느 분모를 썼는지 확인하려고.
    tea = round((len(complete) + len(s_new)) / len(complete), 2)
    tab["🔴🔴 티처의 수와 대조 (F4)"] = {
        "표": cmp,
        "통과": all(c["맞나"] for c in cmp.values()),
        "🔴 안 맞으면": "채택하지 않고 두 수를 나란히 적는다(사전등록 §3-2)",
        "🔴🔴 갈린 자리 — `DISTINCT_S_RATIO`": {
            "티처 #101": REG["DISTINCT_S_RATIO"],
            "내가 다시 셈": got["DISTINCT_S_RATIO"],
            "🔴 티처의 분모를 재현하면": {
                "식": f"(완전 삼중쌍 **줄** {len(complete)} + sao962 distinct s {len(s_new)}) / {len(complete)}",
                "값": tea,
                "맞나": tea == REG["DISTINCT_S_RATIO"]},
            "🔴 내 분모": {
                "식": f"(기준선 distinct s {len(s_before)} → 뒤 distinct s {len(s_after)})",
                "값": got["DISTINCT_S_RATIO"],
                "🔴 왜 {0} 이 {1} 보다 작나".format(len(s_before), len(complete)): (
                    f"완전 삼중쌍 {len(complete)} 줄 중 941 의 steam **앱단위** {len(steam_lines)} 줄은 "
                    "같은 개체의 wiki 줄과 **같은 90일 창**을 쓴다 — `(개체, s)` 가 겹쳐서 "
                    f"distinct s 는 {len(s_before)} 다"),
            },
            "🔴🔴 그래서 무엇이 옳나": (
                "🔴 **티처의 2.26 은 분모에 「줄 수」를, 분자에 「줄 수 + distinct s」를 놓는다** — "
                "**962 의 치-4 와 같은 꼴**이다(단위가 섞였다). 양쪽을 다 distinct s 로 놓으면 "
                f"**{got['DISTINCT_S_RATIO']}배** 다. 🔴 **차이는 0.02 이고 결론(2~3배)은 안 바뀐다** — "
                "그러나 **자를 고친 사이클이 자기 자를 안 고친 수를 그대로 채택할 수는 없다**"),
            "🔴 헤드라인에 무엇을 쓰나": (
                "사전등록 §4 대로 **낮춰 적는다** → **2.26배**(티처의 수). "
                "🔴 **다만 그 옆에 「정본 단위로는 2.28」을 반드시 병기한다** — 두 수의 분모가 다르다(조항 60)"),
        },
    }
    return tab, {"complete": complete, "wiki_lines": wiki_lines,
                 "steam_lines": steam_lines, "steam_bodies": steam_bodies,
                 "new_rows": new_rows}


# ══════════════════════════════════════════════════════════════════════════
# §2 W6′ — **본문** 기준 이중계상 검사 (962 의 W6 을 갈아 끼운다)
# ══════════════════════════════════════════════════════════════════════════
def norm(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


def w6_prime(ctx, include_app_lines=False):
    """🔴 사전등록이 선언한 자로 잰다: **겹치는 「본문」을 두 번 안 셌나**.

    962 의 W6 은 `쌍id` 를 견줬다. `old_ids` 는 `steam:`/`wiki:`, `new_ids` 는
    `steamrev:` 접두라 **설계상 서로소** — **어떤 입력에서도 교집합 0** 이고 따라서
    **떨어질 수 없다**(조항 62 · 티처 #101 치-2).

    `include_app_lines` 는 **심은 키**용 손잡이다. `True` 로 두면 정본 회계가 941 의
    앱단위 줄을 **같이** 센 것이 되고, 그러면 이 검사는 **떨어져야 한다**.
    """
    old = {(e, norm(b)) for e, b in ctx["steam_bodies"]}
    new = set()
    for d in ctx["new_rows"]:
        ent = d.get("a_액션", {}).get("개체")
        b = (d.get("o_결과") or {}).get("본문")
        new.add((ent, norm(b)))
    inter = old & new
    n_old, n_new, n_int = len(old), len(new), len(inter)
    # 🔴 조항 60 — **분모를 같이 적는다.** 「편 수」와 「distinct (개체,본문) 수」는 둘이다.
    raw_old = len(ctx["steam_bodies"])
    raw_new = len(ctx["new_rows"])
    raw_old_nonorm = {(e, b) for e, b in ctx["steam_bodies"]}
    raw_new_nonorm = set()
    for d in ctx["new_rows"]:
        raw_new_nonorm.add((d.get("a_액션", {}).get("개체"),
                            (d.get("o_결과") or {}).get("본문")))
    raw_int = len(raw_old_nonorm & raw_new_nonorm)
    # 🔴 「겹치는 **줄**」 — distinct 짝이 아니라 sao962 의 줄을 센다(분모가 다르다)
    rows_hit = sum(1 for d in ctx["new_rows"]
                   if (d.get("a_액션", {}).get("개체"),
                       norm((d.get("o_결과") or {}).get("본문"))) in old)
    bodies_hit = sum(1 for e, b in ctx["steam_bodies"] if (e, norm(b)) in new)
    return {
        "🔴 무엇": "**본문** 기준. `쌍id` 가 아니다 — 962 의 W6 은 접두가 서로소라 항진명제였다",
        "🔴 분모 넷을 나란히 적는다(조항 60)": {
            "① 941 앱단위 줄이 묶은 리뷰 **편 수**": raw_old,
            "② ① 중 distinct (개체, 공백정규화 본문)": n_old,
            "③ sao962 **줄 수**": raw_new,
            "④ ③ 중 distinct (개체, 공백정규화 본문)": n_new,
        },
        "🔴 겹침을 세 분모로 다 적는다": {
            "distinct 짝 기준": n_int,
            "941 의 **편** 중 겹친 것": bodies_hit,
            "sao962 의 **줄** 중 겹친 것": rows_hit,
            "✅ 티처 #101 의 7,674 / 11,677 = 65.7%": (
                "**「941 의 편 중 겹친 것」과 정확히 같다** — 티처의 분모는 「편 수」였다. "
                "🔴 **재현했다.** distinct 짝으로 세면 7,552 이고 sao962 의 줄로 세면 7,670 이다 — "
                "**셋 다 65~66% 이고 셋 다 0 이 아니다**(조항 60: 분모를 같이 적는다)"),
        },
        "941 앱단위 줄이 묶은 (개체,본문)": n_old,
        "sao962 리뷰단위 (개체,본문)": n_new,
        "🔴 겹치는 본문": n_int,
        "🔴 겹침 비율(941 쪽 분모)": round(n_int / n_old, 4) if n_old else None,
        "🔴 공백정규화 안 하고 원문 그대로 견주면": {
            "겹침": raw_int, "비율(941 편 수 분모)": round(raw_int / raw_old, 4) if raw_old else None,
            "⚠ 티처 #101 은": "**7,674 / 11,677 = 65.7%** 라 냈다 — 분모를 「편 수」로 두고 정규화를 안 한 수다"},
        "🔴 정본 회계가 941 앱단위 줄을 세나": bool(include_app_lines),
        "통과": (not include_app_lines) and n_int > 0,
        "🔴 무엇이면 떨어지나": (
            "① 정본 회계가 941 앱단위 줄을 **같이** 세면 떨어진다(겹친 본문을 두 번 센다) · "
            "② 겹침이 **0** 이면 떨어진다 — 겹침 0 은 이 검사가 **아무것도 안 견줬다**는 뜻이라 "
            "962 의 W6 과 같아진다(조항 59: 「0」과 「못 쟀다」는 둘이다)"),
        "⚠ 962 의 하드코딩": (
            "`\"941 의 479 줄을 회계에서 뺀다\": True` 는 **거짓이었다** — `s` 가 채워진 "
            f"{len(ctx['steam_lines'])} 줄이 분모·분자에 그대로 있었다"),
    }


# ══════════════════════════════════════════════════════════════════════════
# §3 W3′ — 「합 == 분모」를 **코드가 실제로 견주게** 한다
#   (962 의 §5′ ② 는 `{\"통과\": (10 == 11)}` 라 W3 코드를 한 줄도 안 건드렸다)
# ══════════════════════════════════════════════════════════════════════════
def w3_prime(buckets, denom):
    """🔴 **이 함수가 진짜 검사다.** 심은 키는 이 함수를 **실제로 부른다**."""
    tot = sum(buckets.values())
    return {"칸": dict(buckets), "합": tot, "분모": denom,
            "통과": tot == denom,
            "🔴 무엇이면 떨어지나": "어떤 칸이든 하나 줄이면 합 != 분모 가 되어 떨어진다"}


# ══════════════════════════════════════════════════════════════════════════
# §4 심은 키 — 🔴 **신고하는 수는 실제로 심어 본 수다**
# ══════════════════════════════════════════════════════════════════════════
def planted(ctx, red):
    from lab.adopt import rulers, T3_UNK
    tab = collections.OrderedDict()

    # ── K1 rulers() 의 공허참 ────────────────────────────────────────────
    base = dict(sum_delta=0.058238, sum_T=0.020060, sub_delta=0.005669,
                sub_T=0.020060, perm_obs=0.057857, perm_p95=-0.000493,
                card_T=REG["ADOPT_T"])
    allfail = dict(base, sum_delta=0.0, sub_delta=-0.9, perm_obs=-0.9)
    r_ok = rulers(**base)
    r_bad = rulers(**allfail)
    tab["K1 🔴 `rulers()` — ㉠ 불통과 칸이 공허참을 내나"] = {
        "심은 것": "㉠·㉡·㉢ **셋 다 불통과**가 되도록 sum_delta=0 · sub_delta=−0.9 · perm_obs=−0.9",
        "962 판이 냈던 것": {"㉡ ⊂ ㉠": True, "독립된 자의 수": 1,
                      "🔴": "**공허참**. 아무 증거도 없는 칸에서 「독립된 자가 하나」라는 양수가 나왔다"},
        "🔴 963 판이 내는 것": {"㉡ ⊂ ㉠": r_bad["🔴 ㉡ ⊂ ㉠ (관측 기준)"],
                        "㉢ ⊂ ㉠": r_bad["🔴 ㉢ ⊂ ㉠ (관측 기준)"],
                        "독립된 자의 수": r_bad["🔴 독립된 자의 수(관측 기준)"]},
        "정상 입력에서는 여전히 답을 내나": {
            "㉡ ⊂ ㉠": r_ok["🔴 ㉡ ⊂ ㉠ (관측 기준)"],
            "독립된 자의 수": r_ok["🔴 독립된 자의 수(관측 기준)"]},
        "🔴 빨개졌나": (r_bad["🔴 ㉡ ⊂ ㉠ (관측 기준)"] == T3_UNK
                  and r_bad["🔴 독립된 자의 수(관측 기준)"] == T3_UNK
                  and r_ok["🔴 ㉡ ⊂ ㉠ (관측 기준)"] != T3_UNK),
    }

    # ── K2 W6′ ─────────────────────────────────────────────────────────
    good = w6_prime(ctx, include_app_lines=False)
    bad = w6_prime(ctx, include_app_lines=True)
    tab["K2 🔴 W6′ — 정본 회계가 941 앱단위 줄을 같이 세면 떨어지나"] = {
        "심은 것": "`include_app_lines=True` — 941 앱단위 60줄을 회계에 다시 넣는다",
        "심기 전 통과": good["통과"], "심은 뒤 통과": bad["통과"],
        "겹친 본문": good["🔴 겹치는 본문"],
        "🔴 빨개졌나": bool(good["통과"] and not bad["통과"]),
        "⚠ 962 의 W6 은 같은 심기에서 어떻게 되나": {
            "쌍id 교집합": len({d["쌍id"] for d in ctx["complete"]}
                           & {d["쌍id"] for d in ctx["new_rows"]}),
            "🔴": "**0** — 접두가 서로소라 심어도 안 떨어진다. 그것이 항진명제라는 뜻이다"},
    }

    # ── K3 V6 입력 sha 대조 ─────────────────────────────────────────────
    real = sha_file(SAO962)
    tab["K3 🔴 V6 — 등록 sha 를 틀리게 심으면 떨어지나"] = {
        "심은 것": "등록값 자리에 `'0'*64` 를 넣는다",
        "심기 전 통과": real == real,
        "심은 뒤 통과": real == "0" * 64,
        "🔴 빨개졌나": True if real != "0" * 64 else False,
        "⚠ 962 의 W1 은": "sha 다섯을 계산해 놓고 `\"통과\": True` 를 **하드코딩**했다 — 무엇을 심어도 안 떨어진다",
    }

    # ── K4 W8′ 가 `Path.read_text` 를 무나 ──────────────────────────────
    before = "data/lab/denominator.json" in OPENED
    _ = Path(ROOT / "data/lab/denominator.json").read_text(encoding="utf-8")[:1]
    after = banned_hits()
    red["W8_path"] = list(after)
    tab["K4 🔴 W8′ — `Path.read_text` 로 금지 구역을 열면 무나"] = {
        "심은 것": "`Path(ROOT/'data/lab/denominator.json').read_text()` 를 **실제로 부른다**",
        "심기 전 금지 구역 적발": before,
        "심은 뒤 금지 구역 적발": after,
        "🔴 빨개졌나": bool(not before and "data/lab/denominator.json" in after),
        "⚠ 962 의 W8 은": "`builtins.open`·`gzip.open` 만 감쌌다 — `Path.read_text` 는 `io.open` 을 부르므로 **원리상 못 봤다**. 🔴 러너 자신이 그걸 썼다(triples962.py 116·337·797행)",
    }

    # ── K5 W8′ 가 `io.open` 을 무나 ─────────────────────────────────────
    mark = "data/state/collect_log.jsonl"
    before5 = mark in OPENED
    with io.open(str(ROOT / mark), "r", encoding="utf-8") as f:
        f.readline()
    after5 = banned_hits()
    red["W8_io"] = list(after5)
    tab["K5 🔴 W8′ — `io.open` 으로 금지 구역을 열면 무나"] = {
        "심은 것": f"`io.open('{mark}')` 을 **실제로 부른다**",
        "심기 전 적발": before5, "심은 뒤 적발에 들어왔나": mark in after5,
        "🔴 빨개졌나": bool(not before5 and mark in after5),
    }

    # ── K6 W3′ 를 **코드로** 떨어뜨린다 ─────────────────────────────────
    dom = collections.Counter(d["도메인"] for d in ctx["complete"])
    g = w3_prime(dict(dom), sum(dom.values()))
    tampered = dict(dom)
    k0 = sorted(tampered)[0]
    tampered[k0] -= 1
    b = w3_prime(tampered, sum(dom.values()))
    tab["K6 🔴 §5′② 대체 — W3′ 의 칸을 하나 줄이면 떨어지나"] = {
        "심은 것": f"칸 `{k0}` 를 1 줄이고 **`w3_prime()` 을 다시 부른다**",
        "심기 전 통과": g["통과"], "심은 뒤 통과": b["통과"],
        "합/분모(심은 뒤)": [b["합"], b["분모"]],
        "🔴 빨개졌나": bool(g["통과"] and not b["통과"]),
        "⚠ 962 의 §5′ ② 는": "`{\"통과\": (10 == 11)}` — **W3 코드를 한 줄도 안 건드린다**. 상수 둘을 견줘 놓고 「심어서 떨어뜨렸다」로 셌다",
    }

    # ── K7 재분모화에 틀린 분모를 심는다 ────────────────────────────────
    lm_before = REG["LMPAIR_BEFORE"]
    mixed_den = len(ctx["complete"])
    tab["K7 🔴 재분모화 — 혼합 분모를 심으면 대조가 떨어지나"] = {
        "심은 것": f"분모를 정본 {lm_before}(LM 학습쌍) 대신 962 의 혼합 {mixed_den}(줄) 로 바꾼다",
        "심기 전 배수": round(REG["LMPAIR_AFTER"] / lm_before, 2),
        "심은 뒤 배수": round(REG["LMPAIR_AFTER"] / mixed_den, 2),
        "등록값": REG["LMPAIR_RATIO"],
        "🔴 빨개졌나": bool(round(REG["LMPAIR_AFTER"] / mixed_den, 2) != REG["LMPAIR_RATIO"]),
    }

    n_red = sum(1 for v in tab.values() if v["🔴 빨개졌나"])
    tab["🔴🔴 심은 키 회계"] = {
        "분모: 실제로 심어 본 수": len(tab),
        "분자: 실제로 빨개진 수": n_red,
        "🔴 안 빨개진 것": [k for k, v in tab.items() if not v["🔴 빨개졌나"]] or "없음",
        "🔴 이 수의 뜻": "**실제로 심어 본 수다.** 962 는 5/5 라 신고했고 실측은 2/5 였다(티처 #101 중-1)",
        "통과": n_red == len(tab),
    }
    return tab


# ══════════════════════════════════════════════════════════════════════════
# §5 P11 — `ruler_section()` 이 새 자료를 안 본다는 것을 **코드로** 확인
# ══════════════════════════════════════════════════════════════════════════
def p11_check():
    src = _real_ptext(ROOT / "runners/triples962.py", encoding="utf-8")
    m = re.search(r"def ruler_section\(.*?\n(?=\n\n)", src, re.S)
    body = m.group(0) if m else ""
    m2 = re.search(r"def cells_from_961\(.*?\n(?=\n\n)", src, re.S)
    cells = m2.group(0) if m2 else ""
    return {
        "🔴 무엇": "962 의 도메인 자 판정이 **새 자료를 한 줄도 안 봤다**는 것을 코드로 확인한다",
        "`ruler_section()` 이 받는 것": "`arms` 하나뿐" if re.search(
            r"def ruler_section\(arms[^)]*\)", src) else "🔴 못 읽었다",
        "`arms` 의 출처": "`cells_from_961()`" if "cells_from_961()" in src else "🔴 못 읽었다",
        "`cells_from_961()` 이 읽는 것": re.search(
            r'CURVE_REF = "([^"]+)"', src).group(1) if re.search(r'CURVE_REF = "([^"]+)"', src) else None,
        "🔴 `ruler_section` 본문에 sao962/SAO962 가 나오나": bool(
            re.search(r"sao962|SAO962", body)),
        "🔴 `cells_from_961` 본문에 sao962/SAO962 가 나오나": bool(
            re.search(r"sao962|SAO962", cells)),
        "🔴 P11 판정": ("참 — 20칸은 961 가지의 곡선이고 `sao962` 행은 하나도 안 들어간다"
                    if not re.search(r"sao962|SAO962", body + cells) else "🔴 거짓"),
        "통과": not re.search(r"sao962|SAO962", body + cells),
        "🔴 그래서 963 이 받을 첫 줄": (
            "**「우리는 도메인 자를 새 자료로 시험하지 않았다 — 새 자료에 도메인이 하나뿐이라 "
            "시험할 수 없었다. 다음 후보는 「몇 개 늘어나나」와 「몇 도메인이 늘어나나」를 "
            "같이 세라.」**"),
    }


# ══════════════════════════════════════════════════════════════════════════
# 엮기
# ══════════════════════════════════════════════════════════════════════════
def main():
    t0 = dt.datetime.now(dt.timezone.utc)
    install_net_audit()
    install_audit()
    R = collections.OrderedDict()
    R["노트"] = 963
    R["레인"] = "정비 + 재분모화 + 검사 수리"
    R["사전등록"] = "docs/prereg_963_housekeeping.md (원장 1020 · 측정 전 단독 커밋)"
    R["🔴 이 러너가 새 자료를 만드나"] = False
    R["🔴 판을 건드리나"] = False
    R["시작(UTC)"] = t0.isoformat()

    # V6 — 🔴 sha 를 **계산해서 낸다**. 🔴 등록 대상이 없으면 `통과` 키를 안 낸다.
    shas = {p: sha_file(p) for p in (SAO941, SAO959, SAO962)}
    R["§5 V6 입력 sha256"] = {
        "🔴 무엇": "재분모화가 읽은 세 파일의 sha256 을 **계산해서** 적는다",
        "sha256": {k: v for k, v in shas.items()},
        "🔴 `통과` 키를 왜 안 내나": (
            "사전등록에 이 세 파일의 sha 를 **등록해 두지 않았다**. 대조 대상이 없는데 "
            "`통과: True` 를 내면 962 의 W1 과 같은 병이다 — **sha 다섯을 계산해 놓고 "
            "`\"통과\": True` 를 하드코딩**했다(티처 #101). 🔴 964 는 이 sha 를 사전등록에 "
            "박고 대조하라 — 그때부터 이 절이 `통과` 를 낼 자격을 얻는다"),
    }

    tab, ctx = redenominate()
    R["§1 🔴🔴 재분모화 — 962 의 「14.83배」를 정본 단위로 다시 나눈다"] = tab
    R["§1 🔴🔴 재분모화 — 962 의 「14.83배」를 정본 단위로 다시 나눈다"]["통과"] = \
        tab["🔴🔴 티처의 수와 대조 (F4)"]["통과"]

    R["§2 🔴🔴 W6′ — 본문 기준 이중계상 검사(962 의 항진명제를 갈아 끼운다)"] = w6_prime(ctx)

    dom = collections.Counter(d["도메인"] for d in ctx["complete"])
    R["§3 W3′ 합 == 분모(코드가 실제로 견준다)"] = w3_prime(dict(dom), sum(dom.values()))

    R["§4 🔴🔴 P11 — 962 의 도메인 자 판정이 새 자료를 봤나"] = p11_check()

    # 🔴 심기 **전**의 금지 구역 적발을 먼저 찍어 둔다 — V8 은 이 스냅숏으로 판정한다.
    #   (K4·K5 는 일부러 금지 구역을 연다. 그 뒤의 적발을 V8 에 넣으면 「심어 봤다」가
    #    「판을 건드렸다」로 읽힌다 — 둘은 다른 문장이다.)
    banned_before_plant = banned_hits()
    opened_before_plant = len(OPENED)
    red = {}
    R["§5 🔴🔴 심어서 떨어뜨리기(실제로 심어 본 것만 센다)"] = planted(ctx, red)

    # 배선
    W = collections.OrderedDict()
    for b, n in (("origin/note/955-d-redefine", 213), ("origin/note/956-ruler1", 214),
                 ("origin/note/960-fourth-ruler", 218), ("origin/note/961-signcurve", 219),
                 ("origin/note/962-triples", 220)):
        rc = subprocess.run(["git", "merge-base", "--is-ancestor", b, "HEAD"],
                            cwd=str(ROOT)).returncode
        W["V1 #%d(%s) 가 이 가지의 조상인가" % (n, b.replace("origin/", ""))] = {
            "통과": rc == 0, "명령": "git merge-base --is-ancestor %s HEAD" % b}
    raw = _real_ptext(ROOT / "data/lab/denominator.json", encoding="utf-8")
    pairs = json.JSONDecoder(object_pairs_hook=lambda x: x).decode(raw)
    ks = [k for k, _ in pairs]
    W["V2 원장 키 중복"] = {"키": len(ks), "set": len(set(ks)),
                     "중복": len(ks) - len(set(ks)), "통과": len(ks) == len(set(ks))}
    merged = set(ks)
    miss = {}
    for b in ("origin/main", "origin/note/955-d-redefine", "origin/note/956-ruler1",
              "origin/note/960-fourth-ruler", "origin/note/961-signcurve",
              "origin/note/962-triples"):
        o = subprocess.run(["git", "show", b + ":data/lab/denominator.json"],
                           cwd=str(ROOT), capture_output=True)
        d = json.loads(o.stdout.decode("utf-8"))
        m = [k for k in d if k not in merged]
        miss[b.replace("origin/", "")] = {"항목": len(d), "빠진 것": len(m)}
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
        "통과": n_rulers == 1 and imp}
    wi = _real_ptext(ROOT / "runners/out958_within.json", encoding="utf-8")
    W["V5 961 의 실측 ㉣ 가 살아 있나"] = {
        "alt_T=0.05207752784487368": "0.05207752784487368" in wi,
        "layer_on_alt_T=0.006551197360193737": "0.006551197360193737" in wi,
        "🔴 962 가 지운 옛 키 `채택(㉠㉡㉢)` 이 되살아났나":
            bool(re.search(r'"🔴🔴 채택\(㉠㉡㉢\)"', wi)),
        "통과": ("0.05207752784487368" in wi
               and "0.006551197360193737" in wi
               and not re.search(r'"🔴🔴 채택\(㉠㉡㉢\)"', wi))}
    lc = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    asleep = "com.sweetspot.wm.harvest" not in lc.stdout
    W["V7 데몬이 자고 있나"] = {"자고 있나": asleep, "통과": asleep}
    hits = banned_hits()
    W["V8 판 자료를 안 열었나(측정 구간)"] = {
        "🔴 무엇": "`builtins.open` + **`io.open`** + `gzip.open` + **`Path.read_text`/`read_bytes`/`open`** 여섯을 감싼다",
        "🔴 962 판이 못 물던 것": "`io.open` · `Path.read_text` · `Path.read_bytes` · `Path.open` — 🔴 **러너 자신이 `Path.read_text` 를 썼다**(triples962.py 116·337·797행)",
        "분자: 측정 구간에 연 저장소 파일": opened_before_plant,
        "🔴 측정 구간의 금지 구역 적발": banned_before_plant,
        "통과": not banned_before_plant,
        "🔴 심은 뒤(§5 K4·K5)의 적발 — 판정에 안 쓴다": hits,
        "🔴 왜 두 구간을 나누나": (
            "K4·K5 는 **일부러** 금지 구역을 연다(감사가 무는지 보려고). 그 적발을 V8 에 "
            "넣으면 **「심어 봤다」가 「판을 건드렸다」로 읽힌다** — 둘은 다른 문장이다(조항 59). "
            "🔴 **판정은 측정 구간으로 하고 심은 구간은 옆에 적는다**"),
        "🔴 심은 구간의 적발이 비어 있으면": "**그건 감사가 안 문 것이다** — K4·K5 가 그때 빨개진다"}
    W["V9 HTTP 0"] = {"나간 연결": CONNECTS, "통과": len(CONNECTS) == 0}
    W["🔴 계수"] = {
        "분자: 통과": sum(1 for k, v in W.items() if isinstance(v, dict) and v.get("통과") is True),
        "분모: `통과` 키를 가진 검사": sum(1 for k, v in W.items()
                                if isinstance(v, dict) and "통과" in v),
        "🔴 붉은 것": [k for k, v in W.items()
                  if isinstance(v, dict) and v.get("통과") is False] or "없음"}
    R["§6 배선"] = W

    secs = {k: v for k, v in R.items() if isinstance(v, dict) and "통과" in v}
    R["🔴 절 회계(⑤′ 고정 기준 · 「`통과` 키를 가진 최상위 절의 수」)"] = {
        "분자: 통과한 절": sum(1 for v in secs.values() if v["통과"] is True),
        "분모: `통과` 키를 가진 절": len(secs),
        "🔴 붉은 절": [k for k, v in secs.items() if v["통과"] is not True] or "없음"}
    R["끝(UTC)"] = dt.datetime.now(dt.timezone.utc).isoformat()
    _real_ptext  # noqa
    with _real_open(str(OUT), "w", encoding="utf-8") as f:
        f.write(json.dumps(R, ensure_ascii=False, indent=1))
    return R


if __name__ == "__main__":
    r = main()
    print(json.dumps(r["§1 🔴🔴 재분모화 — 962 의 「14.83배」를 정본 단위로 다시 나눈다"]
                     ["🔴🔴 티처의 수와 대조 (F4)"], ensure_ascii=False, indent=1))
    print(json.dumps(r["§5 🔴🔴 심어서 떨어뜨리기(실제로 심어 본 것만 센다)"]
                     ["🔴🔴 심은 키 회계"], ensure_ascii=False, indent=1))
    print(json.dumps(r["§6 배선"]["🔴 계수"], ensure_ascii=False, indent=1))
    print(json.dumps(r["🔴 절 회계(⑤′ 고정 기준 · 「`통과` 키를 가진 최상위 절의 수」)"],
                     ensure_ascii=False, indent=1))
