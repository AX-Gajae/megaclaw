# -*- coding: utf-8 -*-
"""노트 959 [탐색] — 🔴 **표적 표를 키운다. 잠금은 한 줄이었다.**

사전등록 `docs/prereg_959_reach.md`(커밋 `4212af9ab` · **측정 전** · 파일 하나).

**무엇이 있었나.** `ingest/wikidaily941.targets()` 의 첫 줄이

    hold = json.loads(HOLD.read_text())["유보키"]

라서 **수확 표적이 「판 유보」로 잠겨 있었다**. 위키 문서가 해결된 개체는 **3,933** 인데
그중 **815(20.7%)** 만 수확기의 시야에 들어왔고, 수확기는 그 815 중 **810 을 이미 다 돌았다**.
🔴 **표가 464 에서 안 자란 것은 수집이 게을러서가 아니라 표적 선택 때문이다.**
그리고 `wikidaily941` 자신의 독스트링이 *「옛 자(판 유보 3,775 에 몇 행 붙나)는 이 사이클의
자가 아니다」* 라고 적어 놓고 **표적 선택에는 그 옛 자를 남겼다** — 선언과 배선이 어긋난 자리다.

**이 러너가 하는 것 셋** (하위 명령).

  ``harvest``  문서가 해결된 개체 **전량**을 받아 `data/ingest/wiki_daily959/` 에 쓴다.
               🔴 **옛 `data/ingest/wiki_daily/` 를 한 바이트도 안 건드린다**(W4).
  ``pairs``    그 계열로 삼중쌍을 만들어 `data/ingest/sao959/pairs.jsonl.gz` 에 쓴다.
               🔴 **941 의 쌍 파일을 안 덮는다**(W5). 규약(WIN 90 · MIN_SIDE 30)은 941 그대로.
  ``arms``     `layers957.build_arms` 로 팔 A · 팔 B 를 다시 세고 T 를 낸다.

🔴 **판 라벨을 한 비트도 안 연다**(`assert_no_label_files`). 판 주장 0.
🔴 **유료 API 아님** — Wikimedia REST pageviews 는 키·로그인 없는 공개 분석 API 다.
🔴 요청 간격 0.6초(= 1.67 req/s · 사전등록 §4). User-Agent 에 연락처를 밝힌다.

    python3 runners/grow959.py harvest
    python3 runners/grow959.py pairs
    python3 runners/grow959.py arms
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import math
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from ingest import wikidaily941 as W                            # noqa: E402

VIEWS = ROOT / "data/state/wiki_views"
OUTDIR = ROOT / "data/ingest/wiki_daily959"
OLDDIR = ROOT / "data/ingest/wiki_daily"
PAIRDIR = ROOT / "data/ingest/sao959"
OLDPAIRS = ROOT / "data/ingest/sao941/pairs.jsonl.gz"

SLEEP = 0.6                 # 사전등록 §4
#: 🔴 **사전등록에 없다 — 신고한다.** 첫 주행이 개체당 3.5초라 3,933 개에 4시간이 걸렸다.
#: 일꾼 6 · 일꾼마다 0.6초 → **실효 ≈ 1.6 req/s**(Wikimedia 분석 API 의 공개 한도보다
#: 두 자리 아래다). 🔴 **받는 자료는 한 비트도 안 달라진다 — 순서와 시간만 바뀐다.**
WORKERS = 6
WIN = 90                    # 941 그대로 — 안 바꾼다
MIN_SIDE = 30               # 941 그대로 — 안 바꾼다

#: 접두사 → 도메인. 941 의 `PREFIX` 와 `POPUP_PREFIX` 를 **그대로** 쓴다.
POPUP_PREFIX = W.POPUP_PREFIX


def domain_of(rid: str) -> str | None:
    head = rid.split("-")[0]
    if head[:3] in POPUP_PREFIX:
        return "팝업"
    if head in W.PREFIX:
        return W.PREFIX[head][0]
    return None


def sha_dir(d: Path) -> dict:
    """디렉터리 안 파일마다 sha256(앞16). 🔴 파일로 받아서 해싱한다."""
    if not d.exists():
        return {}
    out = {}
    for p in sorted(d.glob("*.jsonl.gz")):
        out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return out


# ── 표적 ────────────────────────────────────────────────────────────────────
def targets_wide() -> tuple[list, dict]:
    """🔴 **유보 잠금을 푼다** — 문서가 해결된 개체 전량."""
    out, unk, nopage, bad = [], Counter(), 0, 0
    for p in sorted(VIEWS.glob("*.json")):
        rid = p.stem
        try:
            c = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            bad += 1
            continue
        if not c.get("page"):
            nopage += 1
            continue
        dom = domain_of(rid)
        if dom is None:
            unk[rid.split("-")[0]] += 1
            continue
        out.append({"도메인": dom, "키": rid, "문서": c["page"],
                    "언어": W._lang_of(rid, c), "시작일": c.get("start")})
    meta = {"분모: wiki_views 파일": len(list(VIEWS.glob("*.json"))),
            "문서 미해결": nopage, "못 읽은 파일": bad,
            "🔴 접두사를 모르는 개체": sum(unk.values()), "그 접두사": dict(unk),
            "🔴 넓힌 표적": len(out),
            "옛 표적(유보 잠금)": len(W.targets()),
            "시작일 없는 표적": sum(1 for t in out if not t["시작일"]),
            "도메인별": dict(Counter(t["도메인"] for t in out))}
    return out, meta


# ── ㄱ 수확 ─────────────────────────────────────────────────────────────────
def cmd_harvest(a) -> dict:
    """🔴🔴 **960 수리 — 959 가 방금 고친 병을 자기 새 수확기에 다시 만들었다.**

    959 는 `ingest/wikidaily941.py` 의 「파일을 통째로 다시 쓴다」를 고치면서
    **못 받은 키의 옛 행을 이어싣는** 블록과 `--keys`·`--no-merge` 를 새로 넣었다.
    🔴 **그런데 같은 사이클에 쓴 이 수확기에는 그 블록이 없었다**(티처 #98 치명 ⑨).
    지금 **37건이 timeout 실패 상태**라 다시 돌리면 그 37개의 옛 행이 죽는다.

    그래서 이 함수는 이제

      ① 도메인 파일을 다시 쓰되 **이번에 안 쓴 키의 옛 행을 이어싣는다**
         (요청 안 한 키 · 요청했지만 **실패한** 키 둘 다)
      ② `--keys` 로 **부분 주행**을 할 수 있고, 부분 주행의 집계는 **별 파일**로 낸다
      ③ `--no-merge` 로 이어싣기를 **일부러** 끌 수 있다(끄면 산출물이 그 사실을 신고한다)
    """
    t0 = time.time()
    before = sha_dir(OLDDIR)
    tg, meta = targets_wide()
    n_all = len(tg)
    if a.keys:
        want = {k.strip() for k in a.keys.split(",") if k.strip()}
        tg = [t for t in tg if t["키"] in want]
    if a.limit:
        tg = tg[:a.limit]
    partial = len(tg) < n_all
    merge = not a.no_merge
    OUTDIR.mkdir(parents=True, exist_ok=True)
    hi = (date.today() - timedelta(days=2)).strftime("%Y%m%d")

    fh: dict = {}
    per: dict = {}
    written: dict = {}          # 도메인 → 이번 주행이 실제로 쓴 키
    n_ok = n_bad = rows = 0
    why: Counter = Counter()
    lock = threading.Lock()
    done = [0]

    def one(t):
        """🔴 한 개체. 요청 **전에** 간격을 둔다(일꾼마다)."""
        time.sleep(a.sleep)
        return t, W.fetch(t["언어"], t["문서"], hi)

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for t, (days, bad) in ex.map(one, tg):
            with lock:
                done[0] += 1
                c = per.setdefault(t["도메인"], {"표적": 0, "성공": 0, "실패": 0, "행": 0})
                c["표적"] += 1
                if bad:
                    n_bad += 1
                    why[bad] += 1
                    c["실패"] += 1
                else:
                    n_ok += 1
                    rows += len(days)
                    c["성공"] += 1
                    c["행"] += len(days)
                    d = t["도메인"]
                    if d not in fh:
                        fh[d] = gzip.open(OUTDIR / f"{d}.jsonl.gz.part", "wt",
                                          encoding="utf-8")
                    written.setdefault(d, set()).add(t["키"])
                    fh[d].write(json.dumps({
                        "키": t["키"], "도메인": d, "문서": t["문서"], "언어": t["언어"],
                        "시작일": t["시작일"], "첫날": days[0][0], "끝날": days[-1][0],
                        "일수": len(days),
                        "날짜": [int(x[0]) for x in days],
                        "조회수": [x[1] for x in days],
                    }, ensure_ascii=False) + "\n")
                if done[0] % 100 == 0:
                    print(f"  {done[0]}/{len(tg)}  성공 {n_ok} 실패 {n_bad}  "
                          f"{time.time()-t0:.0f}s", flush=True)
    # 🔴🔴 **960 수리 — 이어싣기.** 이번에 안 쓴 키(요청 안 함 · 요청했으나 실패)의
    # 옛 행을 같은 `.part` 에 그대로 옮긴 **뒤에** 갈아 끼운다.
    carried = 0
    carried_keys: dict = {}
    for d, f in fh.items():
        old = OUTDIR / f"{d}.jsonl.gz"
        if merge and old.exists():
            got = written.get(d, set())
            ks = set()
            with gzip.open(old, "rt", encoding="utf-8") as g:
                for line in g:
                    try:
                        k = json.loads(line)["키"]
                    except (json.JSONDecodeError, KeyError):
                        continue
                    if k in got:
                        continue
                    f.write(line if line.endswith("\n") else line + "\n")
                    carried += 1
                    ks.add(k)
            if ks:
                carried_keys[d] = len(ks)
        f.close()
        os.replace(OUTDIR / f"{d}.jsonl.gz.part", OUTDIR / f"{d}.jsonl.gz")

    # 🔴 「썼다」가 아니라 **다시 열어 센다**(조항 59)
    reread = {}
    tot = 0
    for p in sorted(OUTDIR.glob("*.jsonl.gz")):
        n = sum(1 for _ in gzip.open(p, "rt", encoding="utf-8"))
        reread[p.name] = n
        tot += n
    after = sha_dir(OLDDIR)
    R = {
        "노트": 959, "레인": "탐색", "무엇": "표적 선택의 유보 잠금을 풀고 전량 수확",
        "사전등록": "docs/prereg_959_reach.md (커밋 4212af9ab · 측정 전 · 파일 하나)",
        "논문 스텝": 502,
        "§0 표적": meta,
        "🔴 R1 분자: 수확 성공한 개체": n_ok,
        "🔴 R1 분모: 넓힌 표적": len(tg),
        "R1 성공률": n_ok / len(tg) if tg else float("nan"),
        "실패 사유": dict(why),
        "🔴 합 == 분모": n_ok + n_bad == len(tg),
        "받은 일별 행": rows,
        "도메인별": per,
        "🔴 다시 열어 센 개체(파일별)": reread,
        "🔴 다시 열어 센 개체 합": tot,
        # 🔴 960 수리 — 이어싣기가 켜지면 「쓴 것」과 「파일 안의 것」은 **다른 수다**
        "🔴 이번에 새로 쓴 것 + 이어실은 것 == 파일 안의 것": tot == n_ok + carried,
        "🔴 이어실은 옛 개체": carried,
        "🔴 이어실은 옛 개체(도메인별)": carried_keys,
        "🔴 이어싣기를 껐나(--no-merge)": bool(a.no_merge),
        "🔴 부분 주행인가": partial,
        "🔴 표적 / 전량": [len(tg), n_all],
        "W4 옛 wiki_daily 를 안 건드렸나": {
            "전 sha256(앞16)": before, "후 sha256(앞16)": after,
            "통과": before == after},
        "Q1 (≥90%)": bool(n_ok / len(tg) >= 0.90) if tg else False,
        "Q2 (≥3500)": bool(n_ok >= 3500),
        "초": round(time.time() - t0, 1),
        "🔴 사전등록에 없던 것(신고)": {"일꾼": a.workers, "간격(초)": a.sleep,
                            "왜": "개체당 3.5초 × 3,933 = 4시간. 자료는 안 바뀐다"},
    }
    # 🔴🔴 **960 수리 — 부분 주행의 집계는 별 파일로.**
    # 959 의 수리 ⑤가 `--keys` 5키 주행으로 `out941_wikidaily.json` 을
    # 「요청 5 · 3도메인 · 10,001행」으로 파괴했다(실제는 815행 표적 · 810 성공 · 1,366,034행).
    # **부분 주행의 수가 전량 주행의 회계를 덮으면 그 수를 인용한 문서가 통째로 틀린다.**
    _rep = ROOT / ("runners/out959_harvest_part.json" if partial
                   else "runners/out959_harvest.json")
    R["🔴 이 집계를 어디에 썼나"] = str(_rep.relative_to(ROOT))
    _rep.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in R.items() if k != "도메인별"},
                     ensure_ascii=False, indent=1)[:4000])
    return R


# ── ㄴ 쌍 ───────────────────────────────────────────────────────────────────
def _daystr(s) -> date:
    s = str(s)
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def cmd_pairs(a) -> dict:
    t0 = time.time()
    oldsha = hashlib.sha256(OLDPAIRS.read_bytes()).hexdigest()[:16]
    PAIRDIR.mkdir(parents=True, exist_ok=True)
    pf = PAIRDIR / "pairs.jsonl.gz"
    tot = ok = no_start = short_pre = short_post = 0
    per: dict = {}
    with gzip.open(pf, "wt", encoding="utf-8") as fp:
        for p in sorted(OUTDIR.glob("*.jsonl.gz")):
            dom = p.name.split(".")[0]
            c = per.setdefault(dom, {"개체": 0, "삼중쌍": 0, "시작일 없음": 0,
                                     "앞창 부족": 0, "뒤창 부족": 0})
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for line in f:
                    r = json.loads(line)
                    tot += 1
                    c["개체"] += 1
                    st = r.get("시작일")
                    if not st or len(st) < 10:
                        no_start += 1
                        c["시작일 없음"] += 1
                        continue
                    d0 = date(int(st[:4]), int(st[5:7]), int(st[8:10]))
                    idx = {_daystr(d): v for d, v in zip(r["날짜"], r["조회수"])}
                    pre = [(d0 - timedelta(days=k)) for k in range(WIN, 0, -1)]
                    post = [(d0 + timedelta(days=k)) for k in range(0, WIN + 1)]
                    sv = [idx[d] for d in pre if d in idx]
                    ov = [idx[d] for d in post if d in idx]
                    if len(sv) < MIN_SIDE:
                        short_pre += 1
                        c["앞창 부족"] += 1
                        continue
                    if len(ov) < MIN_SIDE:
                        short_post += 1
                        c["뒤창 부족"] += 1
                        continue
                    ok += 1
                    c["삼중쌍"] += 1
                    fp.write(json.dumps({
                        "쌍id": f"wiki:{r['키']}",
                        "출처": "wikimedia pageviews per-article (959 · 표적 잠금 해제)",
                        "도메인": dom,
                        "a_액션": {"무엇": "개봉/발매/개최", "언제": st,
                                 "개체": r["키"], "문서": r["문서"], "언어": r["언어"]},
                        "s_상태": {"무엇": f"액션 앞 {WIN}일 일별 위키 조회수",
                                 "일수": len(sv), "값": sv},
                        "o_결과": {"무엇": f"액션 당일~뒤 {WIN}일 일별 위키 조회수",
                                 "일수": len(ov), "값": ov},
                    }, ensure_ascii=False) + "\n")
    n_lines = sum(1 for _ in gzip.open(pf, "rt", encoding="utf-8"))
    R = {
        "노트": 959, "레인": "탐색", "무엇": "넓힌 수확물로 삼중쌍을 다시 만든다",
        "논문 스텝": 502,
        "🔴 R2 분자: wiki 삼중쌍": ok,
        "🔴 R2 분모: 받은 개체": tot,
        "R2 생산률": ok / tot if tot else float("nan"),
        "못 만든 사유": {"시작일 없음": no_start, "앞창 < 30일": short_pre,
                    "뒤창 < 30일": short_post},
        "W6 합 == 분모": ok + no_start + short_pre + short_post == tot,
        "도메인별": per,
        "🔴 다시 열어 센 줄": n_lines,
        "🔴 쓴 것 == 다시 센 것": n_lines == ok,
        "W5 941 쌍 파일을 안 덮었나": {
            "옛 pairs sha256(앞16)": oldsha,
            "지금 sha256(앞16)": hashlib.sha256(OLDPAIRS.read_bytes()).hexdigest()[:16],
            "통과": oldsha == hashlib.sha256(OLDPAIRS.read_bytes()).hexdigest()[:16],
            "새 파일": str(pf.relative_to(ROOT))},
        "옛 wiki 쌍(941)": 584,
        "Q3 (≥2000)": bool(ok >= 2000),
        "초": round(time.time() - t0, 1),
    }
    (ROOT / "runners/out959_pairs.json").write_text(
        json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in R.items() if k != "도메인별"},
                     ensure_ascii=False, indent=1)[:3000])
    return R




# ── ㄷ 팔 ───────────────────────────────────────────────────────────────────
#
# 🔴 **왜 `layers957.build_arms` 를 그대로 못 쓰나.** 그 함수는 층 ③ 배경을
# **파이썬 이중 루프**로 만든다 — 쌍마다 도메인의 개체 전량을 훑고, 개체마다 90일을
# `int(d.strftime(...))` 로 다시 만들어 사전에서 찾는다. 808 개체에서는 30초지만
# **3,933 개체에서는 시간 단위**가 된다(세계애니만 1,649 개체 × 1,300 쌍 × 90일).
#
# 그래서 **같은 수를 내는 numpy 판**을 쓴다. 🔴 **「같은 수」는 주장이 아니라 검사다** ---
# `--verify` 가 **941 의 옛 입력** 위에서 둘을 나란히 돌려 팔 크기와 x3 벡터를
# **원소 단위로** 맞댄다(W12). 안 맞으면 멈춘다.

def build_arms_fast(wd: dict, coords: dict, lp: dict, pairs: list,
                    bg_min=None, bg_gap=None, lift_post=None) -> dict:
    import datetime as _dt
    import math as _math
    import numpy as _np
    import runners.layers957 as L
    bg_min = L.BG_MIN if bg_min is None else bg_min
    bg_gap = L.BG_GAP if bg_gap is None else bg_gap
    lift_post = L.LIFT_POST if lift_post is None else lift_post
    daily, startd = wd["일별"], wd["시작일"]
    LP0, LP1 = _dt.date(2025, 1, 1), _dt.date(2026, 7, 31)

    # 도메인마다 (개체 × 날짜) 행렬을 한 번 만든다. 값은 log10(1+조회수), 없는 칸은 NaN.
    DOM = {}
    for dom, ents in daily.items():
        keys = sorted(ents)
        alldates = sorted({d for e in keys for d in ents[e]})
        col = {d: i for i, d in enumerate(alldates)}
        M = _np.full((len(keys), len(alldates)), _np.nan, dtype=float)
        for r, e in enumerate(keys):
            ser = ents[e]
            idx = _np.fromiter((col[d] for d in ser), dtype=_np.int64, count=len(ser))
            val = _np.fromiter((_math.log10(1.0 + float(v)) for v in ser.values()),
                               dtype=float, count=len(ser))
            M[r, idx] = val
        DOM[dom] = {"keys": keys, "pos": {e: i for i, e in enumerate(keys)},
                    "col": col, "M": M}

    rec, drop = [], defaultdict(int)
    bg_selfhit = 0
    fill = 0
    for p in pairs:
        if not p["쌍id"].startswith("wiki:"):
            drop["steam 쌍(층 ① 이 빈 것)"] += 1
            continue
        a, s_, o_ = p["a_액션"], p["s_상태"], p["o_결과"]
        e, dom = a["개체"], p["도메인"]
        s = _np.asarray(s_["값"], dtype=float)
        o = _np.asarray(o_["값"], dtype=float)
        if len(s) != L.WIN:
            drop[f"s 가 {L.WIN}일이 아니다"] += 1
            continue
        if len(o) < lift_post:
            drop["o 가 뒤 창보다 짧다"] += 1
            continue
        T = _dt.date.fromisoformat(a["언제"])
        dates = [T - _dt.timedelta(days=L.WIN - i) for i in range(L.WIN)]
        dints = [int(d.strftime("%Y%m%d")) for d in dates]
        D = DOM.get(dom)
        if D is None:
            drop[f"배경 개체 N_p < {bg_min}"] += 1
            continue
        cols = _np.array([D["col"][x] for x in dints if x in D["col"]], dtype=_np.int64)
        colpos = _np.array([i for i, x in enumerate(dints) if x in D["col"]],
                           dtype=_np.int64)
        # 후보: 자기 자신이 아니고 · 시작일이 bg_gap 안이 아니고 · 90일 중 하나라도 값이 있는 개체
        keep = _np.ones(len(D["keys"]), dtype=bool)
        if e in D["pos"]:
            keep[D["pos"][e]] = False
            bg_selfhit += 1
        for i, k2 in enumerate(D["keys"]):
            if not keep[i]:
                continue
            st = startd.get(k2) or ""
            if st:
                try:
                    if abs((_dt.date.fromisoformat(st) - T).days) <= bg_gap:
                        keep[i] = False
                except ValueError:
                    pass
        if len(cols):
            sub = D["M"][:, cols]
            has = ~_np.isnan(sub)
            keep &= has.any(axis=1)
        else:
            keep[:] = False
        n_cand = int(keep.sum())
        if n_cand < bg_min:
            drop[f"배경 개체 N_p < {bg_min}"] += 1
            continue
        b = _np.zeros(L.WIN)
        if len(cols):
            sel = sub[keep]                                   # (후보 × 있는 날짜)
            m = ~_np.isnan(sel)
            cnt = m.sum(axis=0)
            ssum = _np.where(m, sel, 0.0).sum(axis=0)
            vals = _np.where(cnt > 0, ssum / _np.maximum(cnt, 1), 0.0)
            b[colpos] = vals
        r = _np.log10(1.0 + s) - b

        f2 = None
        gid = None
        if e in coords:
            lat, lon, src = coords[e]
            gid = L.grid_of(lat, lon)
            if dates[0] >= LP0 and T <= LP1 and gid in lp:
                tab = lp[gid]
                H = _np.zeros((L.WIN, 24))
                have = []
                for i, d in enumerate(dates):
                    row = tab.get(d.strftime("%Y%m%d"))
                    if row is None:
                        have.append(i)
                    else:
                        H[i] = row
                if have:
                    fill += len(have)
                    ok = [i for i in range(L.WIN) if i not in have]
                    med = _np.median(H[ok], axis=0)
                    for i in have:
                        H[i] = med
                dsum = H.sum(axis=1)
                wknd = _np.array([d.weekday() >= 5 for d in dates])
                f2 = L.feats_field(dsum, H, wknd)
        rec.append({
            "쌍id": p["쌍id"], "개체": e, "도메인": dom, "언제": a["언제"],
            "격자": gid, "좌표원천": coords[e][2] if e in coords else None,
            "N_p": n_cand,
            "x1": L.feats_log(s), "x2": f2, "x3": L.feats_dev(r),
            "y_들림": (_math.log10(1.0 + float(o[:lift_post].mean()))
                     - _math.log10(1.0 + float(s[-L.LIFT_PRE:].mean()))),
            "y_수준": _math.log10(1.0 + float(o[:91].sum())),
        })
    A = [x for x in rec if x["x2"] is not None]
    return {"B": rec, "A": A, "뺀 사유": dict(drop),
            "🔴 배경에서 자기 자신을 뺀 횟수(W6)": bg_selfhit,
            "🔴 결측 (격자,날짜) 를 창 중앙값으로 채운 칸": fill}


def _cmp_arms(a: dict, b: dict) -> dict:
    """두 판의 팔을 **원소 단위**로 맞댄다."""
    import numpy as _np
    out = {"팔 B": [len(a["B"]), len(b["B"])], "팔 A": [len(a["A"]), len(b["A"])],
           "뺀 사유": [a["뺀 사유"], b["뺀 사유"]],
           "자기 배제": [a["🔴 배경에서 자기 자신을 뺀 횟수(W6)"],
                    b["🔴 배경에서 자기 자신을 뺀 횟수(W6)"]]}
    if len(a["B"]) != len(b["B"]):
        out["통과"] = False
        return out
    worst = 0.0
    bad = []
    for ra, rb in zip(a["B"], b["B"]):
        if ra["쌍id"] != rb["쌍id"] or ra["N_p"] != rb["N_p"]:
            bad.append(ra["쌍id"])
            continue
        for k in ("x1", "x3"):
            worst = max(worst, float(_np.abs(_np.asarray(ra[k]) - _np.asarray(rb[k])).max()))
        if (ra["x2"] is None) != (rb["x2"] is None):
            bad.append(ra["쌍id"])
        elif ra["x2"] is not None:
            worst = max(worst, float(_np.abs(_np.asarray(ra["x2"]) - _np.asarray(rb["x2"])).max()))
        worst = max(worst, abs(ra["y_들림"] - rb["y_들림"]))
    out["🔴 최대 원소차"] = worst
    out["쌍id·N_p 가 어긋난 행"] = bad
    # 🔴 **뺀 사유는 「수」로 맞댄다.** `layers957` 의 사유 이름 하나가 수를 **하드코딩**해
    # 담고 있어서(`"steam 쌍(층 ① 이 빈 것이 419)"`) 글자로 맞대면 늘 어긋난다 ---
    # 「이름이 다르다」와 「수가 다르다」는 둘이다(조항 59). 이름 차이는 따로 신고한다.
    out["뺀 사유 값(정렬)"] = [sorted(a["뺀 사유"].values()), sorted(b["뺀 사유"].values())]
    out["⚠ 사유 이름만 다른 것"] = sorted(set(a["뺀 사유"]) ^ set(b["뺀 사유"]))
    out["통과"] = bool(not bad and worst < 1e-12
                     and len(a["A"]) == len(b["A"])
                     and sorted(a["뺀 사유"].values()) == sorted(b["뺀 사유"].values()))
    return out


def cmd_arms(a) -> dict:
    import time as _time
    import datetime as _dt
    import numpy as _np
    import runners.layers957 as L
    t0 = _time.time()

    # ── W12 검정 · **941 의 옛 입력** 위에서 두 판을 나란히 ──────────────────
    wd0 = L.load_wiki_daily()
    coords = L.load_coords()
    lp = L.load_lifepop()
    pairs0 = L.load_pairs()
    L.assert_no_label_files()
    old = L.build_arms(wd0, coords, lp, pairs0)
    new = build_arms_fast(wd0, coords, lp, pairs0)
    W12 = _cmp_arms(old, new)
    W12["🔴 무엇"] = ("numpy 판이 layers957 의 파이썬 판과 **같은 수**를 내는가 — "
                   "941 의 옛 입력(팔 B 464 · 팔 A 39) 위에서 원소 단위로 맞댄다")
    if not W12["통과"]:
        R = {"노트": 959, "🔴 W12 불통과 — 여기서 멈춘다": W12}
        (ROOT / "runners/out959_arms.json").write_text(
            json.dumps(R, ensure_ascii=False, indent=1))
        print(json.dumps(R, ensure_ascii=False, indent=1)[:3000])
        return R

    # ── 959 의 새 표 ────────────────────────────────────────────────────────
    L.WIKI = OUTDIR
    L.PAIRS = PAIRDIR / "pairs.jsonl.gz"
    wd = L.load_wiki_daily()
    pairs = L.load_pairs()
    built = build_arms_fast(wd, coords, lp, pairs)
    B, A = built["B"], built["A"]

    def judge(rows, name, base, plus, ckey):
        y = _np.asarray([r["y_들림"] for r in rows], dtype=float)
        g = _np.asarray([r["개체"] for r in rows])
        r1, sd1, P1 = L.rho_of(L.mat(rows, *base), y, g)
        r2, sd2, P2 = L.rho_of(L.mat(rows, *(base + plus)), y, g)
        clus = _np.asarray([str(r[ckey]) for r in rows])
        rng = _np.random.RandomState(7)
        cs = _np.unique(clus)
        pos = {c: _np.where(clus == c)[0] for c in cs}
        from scipy.stats import spearmanr
        d = []
        for _ in range(400):
            pick = rng.choice(len(cs), len(cs), replace=True)
            ii = _np.concatenate([pos[cs[j]] for j in pick])
            if len(set(y[ii])) < 3:
                continue
            va = float(spearmanr(P1[ii], y[ii]).statistic)
            vb = float(spearmanr(P2[ii], y[ii]).statistic)
            if not (math.isnan(va) or math.isnan(vb)):
                d.append(vb - va)
        se = float(_np.asarray(d).std())
        T = max(L.CARD_T, 2 * se)
        return {"무엇": name, "분모: 쌍": len(rows), "군집 열": ckey,
                "군집 수": int(len(cs)),
                "ρ(기준)": r1, "ρ(더한 것)": r2, "🔴 Δρ": r2 - r1,
                "SE_boot(Δρ)": se, "🔴 문턱 T = max(0.00353, 2·SE)": T,
                "부트 성공/요청": [len(d), 400],
                "🔴 판정": L.verdict(r2 - r1, T)}

    M = {"B-③ 무관 배경": judge(B, "팔 B · ① → ①+③", ["x1"], ["x3"], "개체")}
    if A:
        M["A-② 물리 장"] = judge(A, "팔 A · ① → ①+②", ["x1"], ["x2"], "격자")
        M["A-②③ 동시"] = judge(A, "팔 A · ① → ①+②+③", ["x1"], ["x2", "x3"], "격자")

    from collections import Counter as _C
    R = {
        "노트": 959, "레인": "판정", "논문 스텝": 502,
        "사전등록": "docs/prereg_959_reach.md (커밋 4212af9ab · 측정 전 · 파일 하나)",
        "🔴 무엇을 재나": "표적 잠금을 풀고 받은 표에서 팔 A · 팔 B 를 다시 세고 T 를 낸다",
        "🔴 입력": {"위키 일별": str(OUTDIR.relative_to(ROOT)),
                 "쌍": str((PAIRDIR / "pairs.jsonl.gz").relative_to(ROOT))},
        "🔴 판을 뗐다": "판 ρ · 유보를 한 번도 안 건드린다 — 판 주장 0",
        "🔴 데몬을 재웠나": L.daemon_asleep(),
        "W12 numpy 판 == 파이썬 판": W12,
        "🔴 R3 분자: 팔 B 행": len(B), "🔴 R3 분모: wiki 쌍": len(pairs),
        "🔴 R4 분자: 팔 A 행": len(A),
        "뺀 사유": built["뺀 사유"],
        "W7 팔 회계": {"팔 B + 뺀 것": len(B) + sum(built["뺀 사유"].values()),
                   "쌍 전량": len(pairs),
                   "통과": len(B) + sum(built["뺀 사유"].values()) == len(pairs)},
        "도메인별 팔 B": dict(_C(r["도메인"] for r in B)),
        "도메인별 팔 A": dict(_C(r["도메인"] for r in A)),
        "🔴 옛 값(957·958)": {"팔 B": 464, "팔 A": 39, "wiki 쌍": 584,
                        "팔 A T": 0.358007, "팔 B Δρ(③)": 0.059774},
        "§6 측정": M,
        "🔴 배수": {"팔 B": len(B) / 464, "팔 A": len(A) / 39 if A else 0.0},
        "🔴 예측 채점": {
            "Q4 팔 B ≥ 1500": bool(len(B) >= 1500),
            "Q5 팔 A ≥ 78": bool(len(A) >= 78),
            "Q6 팔 A T < 0.25": (bool(M["A-② 물리 장"]["🔴 문턱 T = max(0.00353, 2·SE)"] < 0.25)
                              if "A-② 물리 장" in M else None),
            "Q9 층 ③ 부호가 그대로 +": bool(M["B-③ 무관 배경"]["🔴 Δρ"] > 0)},
        "🔴🔴 D-A 표적 표가 자랐나": (
            "가 — 자랐다" if (len(A) >= 78 and len(B) >= 1500)
            else ("나 — 반쯤 자랐다" if (len(A) >= 78 or len(B) >= 1500)
                  else "다 — 안 자랐다")),
        "🔴 D-A3 커진 표에서 층 ③ 의 부호": (
            "가 — 그대로다(강건)" if M["B-③ 무관 배경"]["🔴 Δρ"] > 0
            else "나 — 뒤집혔다. 957·958 의 이야기를 다시 연다"),
        "⚠ 가를 수 없는 것": "표가 커지면 층 ③ 의 **배경 풀도 같이 커진다**. "
                      "Δρ 의 변화는 「표본이 커진 것」과 「배경이 좋아진 것」이 섞인 값이다",
        "초": round(_time.time() - t0, 1),
    }
    if "A-② 물리 장" in M:
        R["🔴 D-A2 T 가 판정 가능 구간에 들었나"] = (
            "가" if M["A-② 물리 장"]["🔴 문턱 T = max(0.00353, 2·SE)"] < 0.25 else "나")
    (ROOT / "runners/out959_arms.json").write_text(
        json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in R.items() if k != "W12 numpy 판 == 파이썬 판"},
                     ensure_ascii=False, indent=1)[:5000])
    return R


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("harvest")
    h.add_argument("--limit", type=int, default=None)
    h.add_argument("--sleep", type=float, default=SLEEP)
    h.add_argument("--workers", type=int, default=WORKERS)
    # 🔴 960 수리 — 부분 주행과 이어싣기
    h.add_argument("--keys", default=None,
                   help="쉼표로 나눈 키 부분집합. 🔴 부분 주행이다 — 집계는 별 파일로 간다")
    h.add_argument("--no-merge", action="store_true",
                   help="🔴 이어싣기를 끈다. 이번에 못 받은 키의 **옛 행이 죽는다**")
    h.set_defaults(fn=cmd_harvest)
    p = sub.add_parser("pairs")
    p.set_defaults(fn=cmd_pairs)
    m = sub.add_parser("arms")
    m.set_defaults(fn=cmd_arms)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
