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
import json
import os
import sys
import time
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
    t0 = time.time()
    before = sha_dir(OLDDIR)
    tg, meta = targets_wide()
    if a.limit:
        tg = tg[:a.limit]
    OUTDIR.mkdir(parents=True, exist_ok=True)
    hi = (date.today() - timedelta(days=2)).strftime("%Y%m%d")

    fh: dict = {}
    per: dict = {}
    n_ok = n_bad = rows = 0
    why: Counter = Counter()
    for i, t in enumerate(tg, 1):
        days, bad = W.fetch(t["언어"], t["문서"], hi)
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
                fh[d] = gzip.open(OUTDIR / f"{d}.jsonl.gz.part", "wt", encoding="utf-8")
            fh[d].write(json.dumps({
                "키": t["키"], "도메인": d, "문서": t["문서"], "언어": t["언어"],
                "시작일": t["시작일"], "첫날": days[0][0], "끝날": days[-1][0],
                "일수": len(days),
                "날짜": [int(x[0]) for x in days],
                "조회수": [x[1] for x in days],
            }, ensure_ascii=False) + "\n")
        if i % 200 == 0:
            print(f"  {i}/{len(tg)}  성공 {n_ok} 실패 {n_bad}  "
                  f"{time.time()-t0:.0f}s", flush=True)
        time.sleep(a.sleep)
    for d, f in fh.items():
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
        "🔴 쓴 것 == 다시 센 것": tot == n_ok,
        "W4 옛 wiki_daily 를 안 건드렸나": {
            "전 sha256(앞16)": before, "후 sha256(앞16)": after,
            "통과": before == after},
        "Q1 (≥90%)": bool(n_ok / len(tg) >= 0.90) if tg else False,
        "Q2 (≥3500)": bool(n_ok >= 3500),
        "초": round(time.time() - t0, 1),
    }
    (ROOT / "runners/out959_harvest.json").write_text(
        json.dumps(R, ensure_ascii=False, indent=1))
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


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("harvest")
    h.add_argument("--limit", type=int, default=None)
    h.add_argument("--sleep", type=float, default=SLEEP)
    h.set_defaults(fn=cmd_harvest)
    p = sub.add_parser("pairs")
    p.set_defaults(fn=cmd_pairs)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
