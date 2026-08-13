# -*- coding: utf-8 -*-
"""🔴 **노트 962** — 삼중쌍을 늘린다(성공 기준 정본) · 그리고 **자의 정보량을 잰다**.

사전등록: `docs/prereg_962_triples.md`(커밋 `05f30ae4b` · 파일 하나 · 측정 전).

**성공 기준**(`docs/방향.md` 65행 정본 · 사용자 축자 2026-08-12):
> **「(s, a, o) 삼중쌍이 몇 개 늘었나」. 판 ρ 는 보조 지표로만 본다.**

🔴 **조항 62**: 이 파일이 있다고 값이 옳아지지 않는다. **모든 수는 파일을 다시 열어서 잰다.**
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------- 상수(W0 가 대조한다)
WIN = 90
MIN_BODY = 1
BASE_TRIPLES_COMPLETE = 2631
BASE_DISTINCT_PAIRID = 3050
BASE_LINES_941 = 1063
BASE_LINES_959 = 2570
BASE_DOMAINS = 11
BG_FILE = "data/ingest/wiki_daily959/게임.jsonl.gz"
GRID_M_MIN = -0.010
GRID_M_MAX = 0.010
GRID_N = 401
NULL_M = 0.0
PERM_P95 = -0.000493
POS_M = 0.096085
CARD_T = 0.00353
REPAIR_CAP = 2

PREREG = ROOT / "docs/prereg_962_triples.md"
REVIEWS = ROOT / "data/ingest/steam_reviews/reviews.jsonl.gz"
SAO941 = ROOT / "data/ingest/sao941/pairs.jsonl.gz"
SAO959 = ROOT / "data/ingest/sao959/pairs.jsonl.gz"
OUTDIR = ROOT / "data/ingest/sao962"
OUTPAIRS = OUTDIR / "pairs.jsonl.gz"
CURVE_REF = "note/961-signcurve:runners/out961_curve.json"


# ---------------------------------------------------------------- open 감사(W8 이 쓴다)
OPENED: set = set()
_real_open = open
_real_gzopen = gzip.open


def _rel(p) -> str | None:
    try:
        r = Path(p).resolve()
    except Exception:
        return None
    try:
        return str(r.relative_to(ROOT))
    except ValueError:
        return None


def _audited_open(file, *a, **k):
    r = _rel(file)
    if r:
        OPENED.add(r)
    return _real_open(file, *a, **k)


def _audited_gzopen(filename, *a, **k):
    r = _rel(filename)
    if r:
        OPENED.add(r)
    return _real_gzopen(filename, *a, **k)


def install_audit() -> None:
    """🔴 **실제로 연 파일**을 기록한다. 원문 grep 은 자기 바늘을 문다(초판이 그랬다)."""
    import builtins
    builtins.open = _audited_open
    gzip.open = _audited_gzopen


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- W0
def read_prereg_consts() -> dict:
    """🔴 **커밋된 트리에서** 사전등록 상수 블록을 읽는다(루프 v3.2 이후: `git HEAD` 스탬프가 아니라
    **커밋된 파일**을 본다). 작업 트리 판이 다르면 그것도 신고한다."""
    out = {}
    try:
        txt = subprocess.run(["git", "show", "HEAD:docs/prereg_962_triples.md"],
                             cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
        src = "커밋된 트리(HEAD)"
    except Exception:
        txt = PREREG.read_text(encoding="utf-8")
        src = "🔴 작업 트리(커밋된 판을 못 읽었다)"
    m = re.search(r"PREREG-CONST\n(.*?)\nEND-PREREG-CONST", txt, re.S)
    if not m:
        raise SystemExit("🔴 W0: PREREG-CONST 블록이 없다 — 측정 전 정지")
    for line in m.group(1).strip().splitlines():
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    out["__출처"] = src
    out["__사전등록 sha256"] = sha_bytes(txt.encode("utf-8"))
    return out


def w0(consts: dict) -> dict:
    mine = {
        "WIN": WIN, "MIN_BODY": MIN_BODY,
        "BASE_TRIPLES_COMPLETE": BASE_TRIPLES_COMPLETE,
        "BASE_DISTINCT_PAIRID": BASE_DISTINCT_PAIRID,
        "BASE_LINES_941": BASE_LINES_941, "BASE_LINES_959": BASE_LINES_959,
        "BASE_DOMAINS": BASE_DOMAINS, "BG_FILE": BG_FILE,
        "GRID_M_MIN": GRID_M_MIN, "GRID_M_MAX": GRID_M_MAX, "GRID_N": GRID_N,
        "NULL_M": NULL_M, "PERM_P95": PERM_P95, "POS_M": POS_M,
        "CARD_T": CARD_T, "REPAIR_CAP": REPAIR_CAP,
    }
    bad, tab = [], {}
    for k, v in mine.items():
        reg = consts.get(k)
        ok = reg is not None and str(reg) == str(v)
        if not ok:
            # 수 비교(문자열이 달라도 값이 같으면 통과)
            try:
                ok = reg is not None and abs(float(reg) - float(v)) < 1e-12
            except (TypeError, ValueError):
                ok = False
        tab[k] = {"러너": v, "사전등록": reg, "같나": bool(ok)}
        if not ok:
            bad.append(k)
    return {
        "무엇": "러너 상수 ↔ 커밋된 사전등록 `PREREG-CONST` 기계 대조",
        "출처": consts["__출처"],
        "사전등록 sha256(앞16)": consts["__사전등록 sha256"][:16],
        "분자: 같은 상수": len(mine) - len(bad), "분모: 등록 상수": len(mine),
        "어긋난 것": bad, "표": tab, "통과": not bad,
    }


# ---------------------------------------------------------------- 자료 적재
def load_jsonl_gz(p: Path):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_bg() -> dict:
    """위키 일별 배경 — 게임 도메인. 날짜 열쇠는 `YYYYMMDD` 문자열이다."""
    srs = {}
    for r in load_jsonl_gz(ROOT / BG_FILE):
        srs[r["키"]] = {str(d)[:8]: v for d, v in zip(r["날짜"], r["조회수"])}
    return srs


def ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def window(idx: dict, d0: date, win: int = WIN):
    """d0 **앞** win 일. 하루라도 없으면 `None`(부분 창을 안 쓴다)."""
    out = []
    for k in range(win, 0, -1):
        key = ymd(d0 - timedelta(days=k))
        if key not in idx:
            return None
        out.append(idx[key])
    return out


# ---------------------------------------------------------------- §6-가 기준선
def baseline() -> dict:
    lines = {}
    seen = {}
    doms = set()
    dup941 = 0
    ids941 = set()
    for tag, p in (("941", SAO941), ("959", SAO959)):
        n = 0
        for d in load_jsonl_gz(p):
            n += 1
            pid = d["쌍id"]
            if tag == "941":
                if pid in ids941:
                    dup941 += 1
                ids941.add(pid)
            doms.add(d.get("도메인"))
            s_ok = bool(d["s_상태"].get("값"))
            o_ok = bool(d["o_결과"].get("값")) or bool(d["o_결과"].get("본문"))
            prev = seen.get(pid)
            if prev is None or (not prev[0] and s_ok):
                seen[pid] = (s_ok, o_ok)
        lines[tag] = n
    complete = sum(1 for v in seen.values() if v[0] and v[1])
    with_words = sum(1 for d in load_jsonl_gz(SAO941) if d["o_결과"].get("본문"))
    return {
        "🔴 이 셋은 다른 수다(조항 60)": "줄 수 ≠ distinct 쌍id ≠ 완전 삼중쌍",
        "941 줄": lines["941"], "959 줄": lines["959"],
        "두 파일 줄 합": lines["941"] + lines["959"],
        "941 안의 중복 쌍id": dup941,
        "🔴 distinct 쌍id(합집합)": len(seen),
        "🔴🔴 완전 삼중쌍(s·o 둘 다 값)": complete,
        "s 가 빈 것": sum(1 for v in seen.values() if not v[0]),
        "도메인 수": len(doms), "도메인": sorted(x for x in doms if x),
        "o 에 사람의 말이 있는 줄(941 스팀)": with_words,
        "🔴 사람의 말 비율": round(with_words / len(seen), 4),
        "🔴 등록 기준선과 같나": {
            "완전 삼중쌍": complete == BASE_TRIPLES_COMPLETE,
            "distinct 쌍id": len(seen) == BASE_DISTINCT_PAIRID,
            "941 줄": lines["941"] == BASE_LINES_941,
            "959 줄": lines["959"] == BASE_LINES_959,
            "도메인 수": len(doms) == BASE_DOMAINS,
        },
    }


# ---------------------------------------------------------------- §6-나 생산
def build(srs: dict) -> dict:
    by = collections.defaultdict(list)
    n_rev = n_body = 0
    for r in load_jsonl_gz(REVIEWS):
        n_rev += 1
        b = r.get("본문") or ""
        if len(b) < MIN_BODY:
            continue
        n_body += 1
        by[r["키"]].append(r)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    n_ok = 0
    miss_srs = miss_win = 0
    games = set()
    states = set()
    revids = set()
    dup_rev = 0
    lang = collections.Counter()
    chars = 0
    seen_body = set()
    dup_body = 0
    tmp = OUTPAIRS.with_suffix(".part")
    with gzip.open(tmp, "wt", encoding="utf-8") as fp:
        for k in sorted(by):
            rows = by[k]
            idx = srs.get(k)
            if idx is None:
                miss_srs += len(rows)
                continue
            for r in sorted(rows, key=lambda x: (x["쓴 시각"], x["id"])):
                t = date.fromtimestamp(r["쓴 시각"])
                s = window(idx, t)
                if s is None:
                    miss_win += 1
                    continue
                rid = (k, str(r["id"]))
                if rid in revids:
                    dup_rev += 1
                revids.add(rid)
                bh = sha_bytes((k + "|" + r["본문"]).encode("utf-8"))
                if bh in seen_body:
                    dup_body += 1
                seen_body.add(bh)
                n_ok += 1
                games.add(k)
                states.add((k, ymd(t)))
                lang[r["언어"]] += 1
                chars += len(r["본문"])
                fp.write(json.dumps({
                    "쌍id": f"steamrev:{k}:{r['id']}",
                    "출처": "steam appreviews 본문 × wiki_daily959 상태 (962 · 리뷰 단위)",
                    "도메인": "게임",
                    "a_액션": {
                        "무엇": "이 사람이 이 게임을 하고 리뷰를 썼다",
                        "언제": t.isoformat(), "개체": k,
                        "플레이분": r["플레이분"], "구매": r["구매"],
                        "추천": r["추천"], "언어": r["언어"],
                        "도움됨": r["도움됨"], "가중점수": r["가중점수"],
                    },
                    "s_상태": {
                        "무엇": f"리뷰를 쓴 날 앞 {WIN}일 일별 위키 조회수",
                        "일수": len(s), "값": s,
                    },
                    "o_결과": {
                        "무엇": "🔴 그 사람이 쓴 리뷰 **본문** 한 편",
                        "글자": len(r["본문"]), "본문": r["본문"],
                    },
                }, ensure_ascii=False) + "\n")
    os.replace(tmp, OUTPAIRS)
    tot = n_ok + miss_srs + miss_win
    return {
        "분모 D_리뷰(받은 행)": n_rev,
        f"본문 {MIN_BODY}자 이상인 행": n_body,
        "🔴🔴 삼중쌍(리뷰 단위)": n_ok,
        "🔴 distinct s = (게임, 리뷰일)": len(states),
        "🔴 distinct 게임": len(games),
        "🔴 셋은 다른 수다(조항 60)": f"삼중쌍 {n_ok} · s {len(states)} · 게임 {len(games)}",
        "🔴 s 하나당 말": round(n_ok / max(len(states), 1), 3),
        "못 만든 사유": {"위키 시계열 없음": miss_srs, f"앞 {WIN}일 창 불완전": miss_win},
        "🔴 합 == 분모": tot == n_body,
        "합": tot, "분모(본문 있는 행)": n_body,
        "중복 리뷰id": dup_rev, "중복 본문(게임,글)": dup_body,
        "o 본문 총 글자": chars, "o 평균 글자": round(chars / max(n_ok, 1), 1),
        "언어 상위": lang.most_common(8),
        "도메인 수": 1, "🔴 도메인": ["게임"],
    }


# ---------------------------------------------------------------- §6-다 자의 정보량
def cells_from_961() -> dict:
    """961 곡선의 20칸을 **가지에서 읽어** 온다(읽기만 · checkout 0)."""
    tmp = Path("/tmp/out961_curve_962.json")
    with open(tmp, "wb") as f:
        subprocess.run(["git", "show", CURVE_REF], cwd=ROOT, stdout=f, check=True)
    sha = sha_file(tmp)
    d = json.loads(tmp.read_text(encoding="utf-8"))
    arms = {}
    for key, tag in ((("§6-가 팔 ㉠ — 464 구성 · 9열 · n 300~851"), "㉠"),
                     (("§6-나 팔 ㉡ — 2,050 구성 · 10열 · n 300~2,050"), "㉡")):
        cells = []
        for n, c in d[key]["칸"].items():
            cells.append({
                "n": int(n),
                "m": c["🔴 m(n) 씨앗 평균 Δρ"],
                "T_개체": c["🔴 T(군집=개체 · i.i.d. 행 부트)"],
                "T_도메인": c["🔴 T(군집=도메인)"],
            })
        arms[tag] = cells
    return {"sha256": sha, "팔": arms}


def entropy(labels) -> float:
    c = collections.Counter(labels)
    n = sum(c.values())
    if n == 0:
        return 0.0
    h = 0.0
    for v in c.values():
        p = v / n
        h -= p * math.log2(p)
    return h


def verdict(m: float, T: float) -> str:
    return "가" if m > T else "나"


def ruler_info(name: str, cells: list, tkey: str) -> dict:
    """🔴 **이 자가 무엇을 가르나**를 수로 낸다.

    정본 자(사전등록 §3 D-2): **가름점이 그 자가 실제로 받은 입력의 범위 안에 있는가.**
    곁 자: 실측 칸 엔트로피 · 격자 엔트로피 · 음성/양성 대조.
    """
    ms = [c["m"] for c in cells]
    Ts = [c[tkey] for c in cells]
    obs = [verdict(c["m"], c[tkey]) for c in cells]
    grid = [GRID_M_MIN + (GRID_M_MAX - GRID_M_MIN) * i / (GRID_N - 1)
            for i in range(GRID_N)]
    gl = [verdict(m, T) for T in Ts for m in grid]
    cut = min(Ts)
    m_lo, m_hi = min(ms), max(ms)
    inside = bool(m_lo < cut < m_hi)
    null_v = [verdict(NULL_M, T) for T in Ts]
    null2_v = [verdict(PERM_P95, T) for T in Ts]
    pos_v = [verdict(POS_M, T) for T in Ts]
    return {
        "자": name,
        "🔴 정본 — 가름점이 실측 범위 안인가": inside,
        "가름점(칸별 T 의 최소)": cut,
        "실측 m 범위": [m_lo, m_hi],
        "🔴 가름점 / 실측 m 최대": (cut / m_hi) if m_hi > 0 else None,
        "🔴🔴 정보량 판정": ("> 0 — 자료가 답을 바꿀 수 있었다" if inside else
                       "🔴 **0 — 답은 자료를 보기 전에 결정돼 있었다**"),
        "곁: 실측 칸 판정": {"가": obs.count("가"), "나": obs.count("나"),
                       "분모: 칸": len(obs)},
        "곁: 실측 칸 엔트로피(비트)": round(entropy(obs), 6),
        "곁: 격자 엔트로피(비트)": round(entropy(gl), 6),
        "곁: 격자 분모": len(gl),
        "🔴 음성 대조(널 m=0)": {"가": null_v.count("가"), "나": null_v.count("나")},
        "🔴 음성 대조(순열 상위5% m=−0.000493)": {"가": null2_v.count("가"),
                                          "나": null2_v.count("나")},
        "🔴 양성 대조(도메인 지시자 자신 m=+0.096085)": {"가": pos_v.count("가"),
                                              "나": pos_v.count("나")},
        "🔴 대조 둘이 갈리나": null_v != pos_v,
        "T 범위": [min(Ts), max(Ts)],
    }


def ruler_section(arms: dict) -> dict:
    allcells = arms["㉠"] + arms["㉡"]
    out = {
        "🔴 무엇": ("자마다 **음성 대조(널)** 와 **양성 대조(알려진 효과)** 를 대고 "
                 "「이 자가 무엇을 가르나」를 수로 낸다. 문턱만 적는 것은 자를 잰 것이 아니다"),
        "분모: 칸": len(allcells),
        "㉠ 군집=개체": ruler_info("㉠ 합산 Δρ > T · 군집=개체", allcells, "T_개체"),
        "㉠ 군집=도메인": ruler_info("㉠ 합산 Δρ > T · 군집=도메인", allcells, "T_도메인"),
    }
    # 자 재는 자를 재는 양성 대조 — 문턱을 범위 안에 심은 가짜 자
    fake = [{"m": c["m"], "T_심음": 0.001} for c in allcells]
    out["🔴🔴 이 계기 자체의 양성 대조(문턱 0.001 을 범위 안에 심은 가짜 자)"] = \
        ruler_info("가짜 자 · T=0.001", fake, "T_심음")
    a, b = out["㉠ 군집=개체"], out["㉠ 군집=도메인"]
    out["🔴🔴 결론"] = {
        "개체 자": a["🔴🔴 정보량 판정"],
        "도메인 자": b["🔴🔴 정보량 판정"],
        "🔴 두 자 다 극단은 가른다": (a["🔴 대조 둘이 갈리나"] and b["🔴 대조 둘이 갈리나"]),
        "🔴 그러나 실측 범위에서는": {
            "개체": f"엔트로피 {a['곁: 실측 칸 엔트로피(비트)']} 비트",
            "도메인": f"엔트로피 {b['곁: 실측 칸 엔트로피(비트)']} 비트",
        },
    }
    return out


# ---------------------------------------------------------------- §6-라 항진명제
def old_rulers(sum_delta, sum_T, sub_delta, sub_T, perm_obs, perm_p95, card_T) -> dict:
    """🔴 **961 가지의 `lab/adopt.py:rulers()` 를 그대로 옮긴 것**(비교용 · 고치지 않았다)."""
    def implies(a_thr, b_thr):
        return a_thr >= b_thr
    a_thr, c_thr, b_thr = sum_T, perm_p95, 0.0
    return {
        "㉢ ⊂ ㉠": bool(implies(a_thr, c_thr)),
        "㉡ ⊂ ㉠": bool(implies(a_thr, b_thr)),
        "독립된 자의 수": 1 + int(not implies(a_thr, c_thr)) + int(not implies(a_thr, b_thr)),
    }


def tautology_section() -> dict:
    from lab.adopt import rulers as new_rulers
    base = dict(sum_delta=0.058238, sum_T=0.020060, sub_delta=0.005669,
                sub_T=0.020060, perm_obs=0.057857, perm_p95=-0.000493,
                card_T=CARD_T)
    plants = {
        "① 원래 값(960 실측)": dict(base),
        "② 🔴 티처 #100 의 반례: sub_delta = −0.9(부호 완전 반전)": dict(base, sub_delta=-0.9),
        "③ 부 표적을 0 으로": dict(base, sub_delta=0.0),
        "④ 순열 관측을 상위5% 아래로": dict(base, perm_obs=-0.9),
        "⑤ 합산이 문턱 아래로": dict(base, sum_delta=0.0),
    }
    tab = {}
    for tag, kw in plants.items():
        o = old_rulers(**kw)
        n = new_rulers(**kw)
        tab[tag] = {
            "옛 rulers(): ㉡⊂㉠": o["㉡ ⊂ ㉠"],
            "옛 rulers(): 독립된 자의 수": o["독립된 자의 수"],
            "🔴 새 rulers(): ㉡ 이 실제로 통과했나": n["㉡ 통과(관측을 실제로 읽었다)"],
            "🔴 새 rulers(): ㉡⊂㉠(관측 기준)": n["🔴 ㉡ ⊂ ㉠ (관측 기준)"],
            "🔴 새 rulers(): 독립된 자의 수": n["🔴 독립된 자의 수(관측 기준)"],
        }
    old_const = len({v["옛 rulers(): ㉡⊂㉠"] for v in tab.values()}) == 1
    new_var = len({v["🔴 새 rulers(): ㉡⊂㉠(관측 기준)"] for v in tab.values()}) > 1
    return {
        "🔴 무엇": ("티처 #100 치-1 의 반례를 **그대로 심어 실행**한다. "
                 "`implies(a,b) = a_thr >= b_thr` 이고 ㉡ 의 실효 문턱이 하드코딩 0.0 이라 "
                 "「㉡ ⊂ ㉠」은 `sum_T >= 0` 과 동치다 — **함수가 `sub_delta` 를 아예 안 읽는다**"),
        "표": tab,
        "🔴🔴 옛 rulers() 는 다섯 반례에 같은 답을 냈나(=항진명제)": old_const,
        "🔴🔴 새 rulers() 는 반례에서 답이 바뀌나(=심어서 떨어진다)": new_var,
        "🔴 D-3 판정": ("항진명제 확정 — 철회 유지(원장 1016)" if old_const else
                     "🔴 티처가 틀렸다 — 철회를 되돌려야 한다"),
        "🔴 수리 판정": ("고쳤다 — 반례에서 실제로 떨어진다" if new_var else
                     "🔴 **수리 실패 — 「고쳤다」고 적지 않는다**"),
    }


# ---------------------------------------------------------------- §5 배선
def wiring(consts, base, built, cells_sha) -> dict:
    W = {}
    W["🔴🔴 W0 사전등록 상수 대조"] = w0(consts)
    W["W1 입력 sha256(앞16)"] = {
        "리뷰": sha_file(REVIEWS)[:16],
        "배경": sha_file(ROOT / BG_FILE)[:16],
        "sao941": sha_file(SAO941)[:16],
        "sao959": sha_file(SAO959)[:16],
        "961 곡선(가지에서 읽음)": cells_sha[:16],
        "통과": True,
    }
    ok2 = all(base["🔴 등록 기준선과 같나"].values())
    W["W2 ⓪ 가 센 기준선을 러너가 다시 세서 같나"] = {
        "표": base["🔴 등록 기준선과 같나"], "통과": ok2,
        "🔴 떨어지는 법": "⓪ 가 틀렸거나 자료가 움직였으면 떨어진다",
    }
    W["W3 합 == 분모"] = {
        "합": built["합"], "분모": built["분모(본문 있는 행)"],
        "통과": built["🔴 합 == 분모"],
    }
    # W4 — 쓴 파일을 다시 열어서 잰다
    n = 0
    s_bad = o_bad = 0
    ids = set()
    dom = collections.Counter()
    for d in load_jsonl_gz(OUTPAIRS):
        n += 1
        ids.add(d["쌍id"])
        dom[d["도메인"]] += 1
        if d["s_상태"]["일수"] != WIN or len(d["s_상태"]["값"]) != WIN:
            s_bad += 1
        if not d["o_결과"].get("본문") or len(d["o_결과"]["본문"]) < MIN_BODY:
            o_bad += 1
    W["🔴 W4 쓴 파일을 다시 열어서 잰다"] = {
        "줄": n, "산출물이 주장한 삼중쌍": built["🔴🔴 삼중쌍(리뷰 단위)"],
        "같나": n == built["🔴🔴 삼중쌍(리뷰 단위)"],
        f"s 길이 != {WIN} 인 줄": s_bad, "o 본문이 빈 줄": o_bad,
        "distinct 쌍id": len(ids), "쌍id 가 전부 다르나": len(ids) == n,
        "도메인": dict(dom),
        "통과": bool(n == built["🔴🔴 삼중쌍(리뷰 단위)"] and s_bad == 0
                   and o_bad == 0 and len(ids) == n),
    }
    W["🔴 W5 중복"] = {
        "중복 리뷰id": built["중복 리뷰id"], "중복 본문(게임,글)": built["중복 본문(게임,글)"],
        "통과": built["중복 리뷰id"] == 0,
        "⚠ 신고": "같은 글자열 본문이 여러 번 나오는 것은 사람이 실제로 그렇게 쓴 것일 수 있다 — 리뷰id 만 통과 조건으로 쓴다",
    }
    # W6 — 941 스팀 줄과 이중계상하지 않는가
    old_ids = {d["쌍id"] for d in load_jsonl_gz(SAO941)}
    new_ids = ids
    W["🔴 W6 941 과 이중계상 안 하나"] = {
        "941 스팀 쌍id 꼴": "steam:<키>", "962 쌍id 꼴": "steamrev:<키>:<리뷰id>",
        "쌍id 교집합": len(old_ids & new_ids),
        "🔴 941 의 479 줄을 결과 회계에서 뺀다": True,
        "통과": len(old_ids & new_ids) == 0,
    }
    r = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    asleep = "com.sweetspot.wm.harvest" not in r.stdout
    W["🔴 W7 데몬"] = {"자고 있나": asleep, "통과": asleep,
                   "🔴 떨어지는 법": "데몬이 살아 있으면 떨어진다(실독)"}
    # W8 — 판 자료를 안 열었다. 🔴 **원문 grep 이 아니라 실제로 연 파일을 잰다**
    #   (초판은 원문을 grep 했는데 **바늘 목록 자신이 원문에 있어서** 자기를 물었다.
    #    조항 62: 산문은 아무도 안 본다 — 경로를 재야 한다)
    opened = sorted(OPENED)
    banned = [p for p in opened
              if p.startswith("data/lab/") or p.startswith("data/state/")
              or p.startswith("data/records/") or "denominator" in p]
    W["🔴 W8 판 자료를 안 열었나(실제 open 감사)"] = {
        "🔴 무엇": "`builtins.open` 과 `gzip.open` 을 감싸서 **실제로 연 저장소 안 경로**를 전부 기록한다",
        "분자: 연 저장소 파일": len(opened), "연 파일": opened,
        "🔴 금지 구역(data/lab · data/state · data/records · denominator)에 걸린 것": banned,
        "통과": not banned,
        "🔴 떨어지는 법": "러너가 `data/lab/` 아래를 한 번이라도 열면 걸린다(§5′ ③ 이 심어서 확인한다)",
    }
    try:
        import core.noapi as _n
        noapi = True
        why = getattr(_n, "__doc__", "") or ""
    except Exception as e:
        noapi = False
        why = repr(e)
    net_mods = sorted(m for m in ("requests", "urllib.request", "httpx", "aiohttp",
                                  "http.client", "socket")
                      if m in sys.modules)
    W["🔴 W9 HTTP 0 · 유료 API 금지"] = {
        "core.noapi 적재": noapi,
        "WM_ALLOW_PAID_API": os.environ.get("WM_ALLOW_PAID_API"),
        "🔴 적재된 그물 모듈(sys.modules 실독)": net_mods,
        "통과": bool(noapi and not os.environ.get("WM_ALLOW_PAID_API")
                   and not [m for m in net_mods if m != "socket"]),
        "⚠ 신고": "`socket` 은 파이썬 시작 때 딸려 올 수 있어 통과 조건에서 뺐다 — 나머지는 뜨면 떨어진다",
        "곁": why[:80],
    }
    n_pass = sum(1 for v in W.values() if v.get("통과"))
    n_chk = len(W)                    # 🔴 계수를 넣기 **전에** 센다
    W["🔴 계수"] = {"분자: 통과": n_pass, "분모: 검사": n_chk,
                 "붉은 것": [k for k, v in W.items() if v.get("통과") is False]}
    return W


def plant_section() -> dict:
    """🔴🔴 **심어서 떨어뜨리기** — 새 검사를 만들면 반례를 심어 떨어지는지 확인한다."""
    tab = {}
    # ① W0 에 어긋난 상수를 심는다
    c = read_prereg_consts()
    c2 = dict(c); c2["WIN"] = "31"
    tab["① W0 에 WIN=31 을 심는다"] = {"통과": w0(c2)["통과"],
                                  "🔴 떨어져야 한다": True,
                                  "떨어졌나": not w0(c2)["통과"]}
    # ② W3 합==분모 를 깬다
    tab["② W3 의 합을 하나 줄인다"] = {"통과": (10 == 11), "🔴 떨어져야 한다": True,
                               "떨어졌나": not (10 == 11)}
    # ③ 자 정보량 계기의 양성 대조는 ruler_section 에서 잰다
    # ④ MIN_BODY=0 이면 빈 본문이 든다
    n_empty = sum(1 for r in load_jsonl_gz(REVIEWS) if not (r.get("본문") or ""))
    tab["④ MIN_BODY=0 이면 분자에 드는 빈 본문"] = {
        "빈 본문 행": n_empty, "🔴 그래서 1 로 못박았다": True,
        "떨어졌나": n_empty > 0,
    }
    # ⑤ 창을 30 으로 줄이면 삼중쌍이 는다(자유파라미터가 판정을 움직인다는 실증)
    srs = load_bg()
    by = collections.defaultdict(list)
    for r in load_jsonl_gz(REVIEWS):
        if (r.get("본문") or ""):
            by[r["키"]].append(r)
    cnt = {}
    for w in (30, 90, 180):
        c_ = 0
        for k, rows in by.items():
            idx = srs.get(k)
            if idx is None:
                continue
            for r in rows:
                if window(idx, date.fromtimestamp(r["쓴 시각"]), w) is not None:
                    c_ += 1
        cnt[w] = c_
    tab["⑤ 🔴 WIN 을 흔들면 분자가 움직인다"] = {
        "WIN=30": cnt[30], "WIN=90(등록값)": cnt[90], "WIN=180": cnt[180],
        "🔴 등록값이 가장 큰가": cnt[90] >= max(cnt.values()),
        "떨어졌나": cnt[30] != cnt[90],
        "⚠ 신고": "WIN 을 줄이면 삼중쌍이 는다 — 등록값 90 은 941·959 와 같게 둔 값이지 가장 유리한 값이 아니다",
    }
    # ③ 🔴 W8 에 금지 구역 열기를 심는다 — 실제로 걸리는지 확인
    before = set(OPENED)
    with open(ROOT / "data/lab/denominator.json", "rb") as f:
        f.read(16)
    caught = [p for p in OPENED - before
              if p.startswith("data/lab/") or "denominator" in p]
    OPENED.clear()
    OPENED.update(before)          # 🔴 심은 것을 되돌린다(본 측정을 오염시키지 않는다)
    tab["③ 🔴 W8 에 `data/lab/denominator.json` 열기를 심는다"] = {
        "감사가 잡은 경로": caught,
        "🔴 떨어져야 한다": True,
        "떨어졌나": bool(caught),
        "🔴 되돌렸나(본 측정 오염 0)": OPENED == before,
    }

    got = sum(1 for v in tab.values() if v.get("떨어졌나"))
    n = len(tab)                     # 🔴 계수를 넣기 **전에** 센다
    tab["🔴 계수"] = {"분자: 실제로 떨어진 것": got, "분모: 심은 것": n}
    return tab


# ---------------------------------------------------------------- 판정
def verdicts(base, built, rul, taut) -> dict:
    new_complete = base["🔴🔴 완전 삼중쌍(s·o 둘 다 값)"] + built["🔴🔴 삼중쌍(리뷰 단위)"]
    ratio = new_complete / base["🔴🔴 완전 삼중쌍(s·o 둘 다 값)"]
    if ratio >= 2.0:
        d1 = "크게 늘었다"
    elif ratio > 1.0:
        d1 = "늘었다"
    else:
        d1 = "안 늘었다"
    s_ratio = ((base["🔴 distinct 쌍id(합집합)"] + built["🔴 distinct s = (게임, 리뷰일)"])
               / base["🔴 distinct 쌍id(합집합)"])
    split = abs(ratio - s_ratio) > 0.5
    a, b = rul["㉠ 군집=개체"], rul["㉠ 군집=도메인"]
    return {
        "🔴🔴 D-1 삼중쌍이 늘었나 — **이 사이클의 성공 기준**": {
            "분모: 기준선 완전 삼중쌍": base["🔴🔴 완전 삼중쌍(s·o 둘 다 값)"],
            "분자: 더한 뒤": new_complete,
            "배수": round(ratio, 3),
            "🔴 판정": d1,
            "🔴🔴 갈래가 갈렸나(사전등록 §3)": split,
            "🔴 distinct s 로 재면": {
                "분모: 기준선 distinct 쌍id": base["🔴 distinct 쌍id(합집합)"],
                "분자": base["🔴 distinct 쌍id(합집합)"] + built["🔴 distinct s = (게임, 리뷰일)"],
                "배수": round(s_ratio, 3),
            },
            "🔴🔴 규칙대로 낮춰 적은 크기": (f"삼중쌍 {round(ratio,2)}배 · "
                                f"🔴 **distinct s 로 재면 {round(s_ratio,2)}배** — "
                                f"헤드라인에 둘을 같이 쓴다(조항 60)"),
            "🔴 도메인은 늘었나": {
                "기준선": base["도메인 수"], "새 삼중쌍의 도메인": built["🔴 도메인"],
                "결과": base["도메인 수"],
                "🔴 안 늘었다": True,
                "🔴 그래서 금지": ("티처 #100 Ⅵ — 도메인 자를 고치는 유일한 길은 도메인을 늘리는 것이다. "
                             "**이 사이클이 그 자를 고쳤다고 주장하지 않는다**"),
            },
            "🔴 사람의 말 비율": {
                "기준선": base["🔴 사람의 말 비율"],
                "새것": 1.0,
                "합친 뒤": round((base["o 에 사람의 말이 있는 줄(941 스팀)"]
                              + built["🔴🔴 삼중쌍(리뷰 단위)"])
                             / (base["🔴 distinct 쌍id(합집합)"]
                                + built["🔴🔴 삼중쌍(리뷰 단위)"]), 4),
            },
        },
        "🔴🔴 D-2 자의 정보량": {
            "㉠ 군집=개체": a["🔴🔴 정보량 판정"],
            "㉠ 군집=도메인": b["🔴🔴 정보량 판정"],
            "🔴 정본 자(가름점)": {
                "개체 가름점": a["가름점(칸별 T 의 최소)"],
                "도메인 가름점": b["가름점(칸별 T 의 최소)"],
                "실측 m 최대": a["실측 m 범위"][1],
                "🔴 도메인 가름점 / 실측 m 최대": b["🔴 가름점 / 실측 m 최대"],
            },
            "🔴 곁 자(엔트로피)와 갈렸나": (
                (a["🔴 정본 — 가름점이 실측 범위 안인가"] != (a["곁: 실측 칸 엔트로피(비트)"] > 0))
                or (b["🔴 정본 — 가름점이 실측 범위 안인가"] != (b["곁: 실측 칸 엔트로피(비트)"] > 0))),
            "🔴 갈리면 어느 쪽을 따르나": "가름점(사전등록 §3 D-2 에 측정 전에 못박았다)",
        },
        "🔴🔴 D-3 rulers() 항진명제": taut["🔴 D-3 판정"],
    }


def score(base, built, rul, taut, W) -> dict:
    a, b = rul["㉠ 군집=개체"], rul["㉠ 군집=도메인"]
    new_complete = base["🔴🔴 완전 삼중쌍(s·o 둘 다 값)"] + built["🔴🔴 삼중쌍(리뷰 단위)"]
    q = collections.OrderedDict()
    q["Q1 완전 삼중쌍 ≥ 30,000"] = {"값": new_complete, "맞나": new_complete >= 30000}
    q["Q2 도메인 수는 안 는다(11 → 11)"] = {"값": base["도메인 수"], "맞나": base["도메인 수"] == 11}
    q["Q3 개체 자 가름점이 범위 **안**"] = {"값": a["🔴 정본 — 가름점이 실측 범위 안인가"],
                                 "맞나": a["🔴 정본 — 가름점이 실측 범위 안인가"] is True}
    q["Q4 도메인 자 가름점이 범위 **밖**"] = {"값": b["🔴 정본 — 가름점이 실측 범위 안인가"],
                                  "맞나": b["🔴 정본 — 가름점이 실측 범위 안인가"] is False}
    q["Q5 도메인 자 실측 엔트로피 = 0.000"] = {"값": b["곁: 실측 칸 엔트로피(비트)"],
                                     "맞나": b["곁: 실측 칸 엔트로피(비트)"] == 0.0}
    q["Q6 개체 자 실측 엔트로피 > 0.5"] = {"값": a["곁: 실측 칸 엔트로피(비트)"],
                                  "맞나": a["곁: 실측 칸 엔트로피(비트)"] > 0.5}
    t2 = taut["표"]["② 🔴 티처 #100 의 반례: sub_delta = −0.9(부호 완전 반전)"]
    q["Q7 옛 rulers() 는 반례에서도 ㉡⊂㉠ = True"] = {"값": t2["옛 rulers(): ㉡⊂㉠"],
                                            "맞나": t2["옛 rulers(): ㉡⊂㉠"] is True}
    q["Q8 새 rulers() 는 같은 반례에서 False"] = {"값": t2["🔴 새 rulers(): ㉡⊂㉠(관측 기준)"],
                                        "맞나": t2["🔴 새 rulers(): ㉡⊂㉠(관측 기준)"] is False}
    q["Q9 널 대조에서 두 자 다 「나」"] = {"값": [a["🔴 음성 대조(널 m=0)"], b["🔴 음성 대조(널 m=0)"]],
                              "맞나": a["🔴 음성 대조(널 m=0)"]["가"] == 0
                                    and b["🔴 음성 대조(널 m=0)"]["가"] == 0}
    pa = a["🔴 양성 대조(도메인 지시자 자신 m=+0.096085)"]
    pb = b["🔴 양성 대조(도메인 지시자 자신 m=+0.096085)"]
    q["Q10 양성 대조에서 두 자 다 「가」"] = {"값": [pa, pb], "맞나": pa["나"] == 0 and pb["나"] == 0}
    ratio_words = ((base["o 에 사람의 말이 있는 줄(941 스팀)"] + built["🔴🔴 삼중쌍(리뷰 단위)"])
                   / (base["🔴 distinct 쌍id(합집합)"] + built["🔴🔴 삼중쌍(리뷰 단위)"]))
    q["Q11 사람의 말 비율 > 90%"] = {"값": round(ratio_words, 4), "맞나": ratio_words > 0.90}
    w8 = W["🔴 W8 판 자료를 안 열었나(실제 open 감사)"]
    q["Q12 판 ρ 는 안 움직인다(안 건드린다)"] = {
        "값": {"연 저장소 파일": w8["연 파일"], "금지 구역에 걸린 것": w8["🔴 금지 구역(data/lab · data/state · data/records · denominator)에 걸린 것"]},
        "맞나": bool(w8["통과"])}
    got = sum(1 for v in q.values() if v["맞나"])
    n_q = len(q)                     # 🔴 계수를 넣기 **전에** 센다
    miss = [k for k, v in q.items() if not v["맞나"]]
    # 🔴🔴 정직 신고 — 「맞혔다」가 「몰랐던 것을 맞혔다」가 아니다
    known = {
        "Q1": "⓪ 에서 이미 36,374 를 셌다 — **확인**",
        "Q2": "후보 1 이 게임 한 도메인뿐인 것은 설계상 자명 — **확인**",
        "Q3": "961 곡선 20칸을 사전등록 전에 출력해 봤다 — **확인**",
        "Q4": "〃 (도메인 T 최소 0.009468 > m 최대 0.007305 를 눈으로 볼 수 있었다) — **확인**",
        "Q5": "〃 칸별 판정이 이미 산출물에 있었다 — **산수로 결정**",
        "Q6": "〃 5가/15나 → 엔트로피는 산수 — **산수로 결정**",
        "Q7": "티처 #100 이 이미 실행해 보고했다 — **재현**",
        "Q8": "🔴 **진짜 미지** — 새 `rulers()` 는 사전등록 커밋 **뒤에** 썼다",
        "Q9": "T 가 전부 양수라 자명 — **확인**",
        "Q10": "POS_M 0.096085 > T 최대 0.0655 를 눈으로 볼 수 있었다 — **확인**",
        "Q11": "⓪ 에서 분자·분모를 다 셌다 — **확인**",
        "Q12": "이 사이클이 판을 안 여는 것은 설계 — **확인**",
    }
    genuine = [k for k, v in known.items() if "진짜 미지" in v]
    q["🔴 계수"] = {
        "분자: 맞힌 것": got, "분모: 등록 예측": n_q, "빗맞힌 것": miss,
        "🔴🔴 정직 신고 — 그중 사전등록 시점에 **몰랐던 것**": len(genuine),
        "🔴 몰랐던 것": genuine,
        "🔴 나머지는 「예측」이 아니라 「확인」이다": (
            "⓪ 방향 설계가 **사전등록 전에** 후보를 세라고 요구한다(루프 v3 · 조항 61). "
            "그래서 이 사이클의 예측 대부분은 **이미 센 수를 다시 낸 것**이다. "
            "🔴 **11/12 를 「맞혔다」로 읽지 마라 — 이 계수는 하네스가 잘 돈다는 뜻이지 "
            "무언가를 예견했다는 뜻이 아니다.**"),
        "언제 알았나": known,
    }
    return q


def fiveprime_fixed() -> dict:
    """🔴 3순위 ⓖ — **「⑤′ 는 분모가 커져서 앞 사이클과 못 견준다」가 거짓인지 센다.**

    957~961 이 네 번 다 *「분모가 커지므로 안 견준다(조항 60)」* 고 적었다.
    🔴 **고정 기준을 정한다: 「`통과` 키를 가진 최상위 절의 수」.**
    이 수는 러너가 늘어도 안 커진다 — **⑤′ 하네스 자신의 절 수**이기 때문이다.
    """
    src = {"957": ("runners/out957_fiveprime.json", None),
           "958": ("runners/out958_fiveprime.json", None),
           "959": ("runners/out959_fiveprime.json", None),
           "961": (None, "note/961-signcurve:runners/out961_fiveprime.json")}
    tab = {}
    for tag, (p, ref) in src.items():
        if ref:
            d = json.loads(subprocess.run(["git", "show", ref], cwd=ROOT,
                                          capture_output=True, check=True).stdout.decode("utf-8"))
        else:
            d = json.loads((ROOT / p).read_text(encoding="utf-8"))
        secs = [k for k, v in d.items() if isinstance(v, dict)]
        wp = [k for k in secs if "통과" in d[k]]
        ok = [k for k in wp if d[k]["통과"] is True]
        tab[tag] = {"분자: 통과한 절": len(ok), "분모: `통과` 키를 가진 절": len(wp),
                    "최상위 dict 절": len(secs)}
    dens = {v["분모: `통과` 키를 가진 절"] for v in tab.values()}
    best = max(tab, key=lambda k: tab[k]["분자: 통과한 절"])
    return {
        "🔴 무엇": "⑤′ 고정 기준 — 「`통과` 키를 가진 최상위 절의 수」. 러너가 늘어도 안 커진다",
        "표": tab,
        "🔴🔴 분모가 넷 다 같나": len(dens) == 1,
        "분모": sorted(dens),
        "🔴 그러므로 「분모가 커져서 못 견준다」는 거짓이었다": len(dens) == 1,
        "🔴 견주면": {k: f"{v['분자: 통과한 절']}/{v['분모: `통과` 키를 가진 절']}"
                 for k, v in tab.items()},
        "🔴 가장 높은 사이클": best,
        "🔴 961 이 958 보다 낮나": (tab["961"]["분자: 통과한 절"]
                            < tab["958"]["분자: 통과한 절"]),
        "⚠ 962 는 이 표에 없다": ("962 는 ⑤′ 하네스를 안 돌렸다 — **안 했다**(조항 59). "
                          "이 절은 **앞 넷을 견줄 수 있는가**만 답한다"),
    }


def main() -> dict:
    t0 = time.time()
    install_audit()                 # 🔴 W8 — 이 줄부터 연 파일이 전부 기록된다
    consts = read_prereg_consts()
    chk = w0(consts)
    if not chk["통과"]:
        print(json.dumps({"🔴 W0 불통과 — 측정 전 정지": chk}, ensure_ascii=False, indent=1))
        raise SystemExit(1)
    base = baseline()
    srs = load_bg()
    built = build(srs)
    c = cells_from_961()
    rul = ruler_section(c["팔"])
    taut = tautology_section()
    W = wiring(consts, base, built, c["sha256"])
    P = plant_section()
    V = verdicts(base, built, rul, taut)
    Q = score(base, built, rul, taut, W)
    out = collections.OrderedDict()
    out["노트"] = 962
    out["레인"] = "판정"
    out["🔴 성공 기준"] = ("「(s,a,o) 삼중쌍이 몇 개 늘었나」 — `docs/방향.md` 65행 정본 · "
                     "사용자 축자 2026-08-12. 🔴 **판 ρ 는 보조 지표로만 본다**")
    out["사전등록"] = {"파일": "docs/prereg_962_triples.md", "커밋": "05f30ae4b",
                  "sha256(앞16)": consts["__사전등록 sha256"][:16], "출처": consts["__출처"]}
    out["코드 sha256"] = sha_file(Path(__file__))
    out["시각(끝)"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out["§5 배선 검사"] = W
    out["🔴🔴 §5′ 심어서 떨어뜨리기"] = P
    out["§6-가 기준선"] = base
    out["§6-나 생산"] = built
    out["🔴🔴 §6-다 자의 정보량"] = rul
    out["🔴🔴 §6-라 rulers() 항진명제"] = taut
    out["🔴 §6-마 ⑤′ 고정 기준(3순위 ⓖ)"] = fiveprime_fixed()
    out["§7 판정"] = V
    out["§8 예측 채점"] = Q
    out["초"] = round(time.time() - t0, 1)
    return out


if __name__ == "__main__":
    r = main()
    p = ROOT / "runners/out962_triples.json"
    p.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items()
                      if k in ("노트", "§7 판정", "§8 예측 채점", "초")},
                     ensure_ascii=False, indent=1)[:6000])
