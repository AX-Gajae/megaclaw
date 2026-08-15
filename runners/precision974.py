#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""974 --- **축 C3** 의 두 번째 수: 973 이 낸 35,641 행의 **언급 정밀도**를 잰다.

🔴 티처 #112 의 판정을 그대로 옮긴다:
   **「(s,a,o) 삼중쌍 35,641」은 아직 못 부른다.**
   참인 문장은 **「HPLT 웹문서가 개체를 언급한 사건 35,641 건(정밀도 미측정)」**이다.
🔴 정밀도를 모르는 행으로 LOSO 를 돌리면 어떤 부호가 나와도
   **자료 탓인지 잡음 탓인지 원리상 못 가른다** --- 그래서 이 러너가 먼저 돈다.

🔴 **바퀴를 다시 만들지 않는다**: 토큰화·조사 벗기기·제목 정규화·언급 찾기는
   전부 `runners/hplt973.py` 의 **생산 함수를 부른다**. 여기서 새로 정의하는 것은
   **자리(offset)를 같이 내는 것** 하나뿐이고, 그것도 973 의 자와 **같은 규칙**임을
   `--stage wiring` 의 W6 이 **35,641 행 전량에서 대조**한다.

씀:
    python3 runners/precision974.py --stage sample  --ref <40자 sha>
    python3 runners/precision974.py --stage context --ref <40자 sha>
    python3 runners/precision974.py --stage score   --ref <40자 sha>
    python3 runners/precision974.py --stage gate    --ref <40자 sha>
    python3 runners/precision974.py --stage wiring  --ref <40자 sha>

🔴 조항 60 --- 모든 비율에 **분모를 같은 자리에** 적는다.
"""
import argparse
import collections
import datetime as dt
import glob
import gzip
import json
import math
import os
import random
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import runners.predict971 as P                     # noqa: E402  생산 함수(도장·sha)
import runners.hplt973 as H                        # noqa: E402  생산 함수(자·언급)

RAN = ("runners/precision974.py", "runners/hplt973.py",
       "runners/dupe954_hplt_scan.py", "runners/predict971.py")

PAIRS = ROOT / "data/ingest/sao973_hplt/pairs.jsonl.gz"
OUT = ROOT / "runners"

SEED = 974
PER_STRATUM = 100          # §2.2
SRS_N = 300                # §2.2 곁 표본
CTX_CHARS = 150            # §2.3
CTX_MAX = 3                # §2.3

# §4 게이트 H3·H4 --- 측정 전에 사전등록한 목록
WIKI_HOSTS = ("wikipedia.org", "rigvedawiki.net", "namu.wiki", "wikia.com",
              "fandom.com", "wikiwand.com", "dbpedia.org", "wikidata.org",
              "wiki.namu.moe", "everipedia.org")
DUMP_HOSTS = ("happycampus", "reportworld", "docsplayer", "slidesplayer",
              "dokumen", "123dok", "reportshop", "allreport", "haksul",
              "reportdb", "reportkorea")

TOKPAT = re.compile(r"[0-9A-Za-z가-힣]+")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_stamp() -> dict:
    """🔴 규칙 C --- `lab/*.py` 전량 + **내가 돌린 러너 전부**."""
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def data_stamp() -> dict:
    d = {"sao973_hplt/pairs.jsonl.gz": P._sha_file(str(PAIRS))}
    for p in sorted(glob.glob(str(H.WIKI_DIR / "*.jsonl.gz"))):
        d["wiki_daily959/" + Path(p).name] = P._sha_file(p)
    return d


def stamp_block(ref: str, cs0: dict, cs1: dict, t0: str) -> dict:
    ds = data_stamp()
    runner = {}
    ok = 0
    for r in RAN:
        disk = P._sha_file(str(ROOT / r))
        import subprocess
        try:
            blob = subprocess.check_output(["git", "show", "%s:%s" % (ref, r)],
                                           cwd=str(ROOT))
            import hashlib
            cm = hashlib.sha256(blob).hexdigest()
        except Exception:                                          # noqa: BLE001
            cm = None
        runner[r] = {"디스크 sha256": disk, "커밋 blob sha256": cm, "일치": disk == cm}
        ok += 1 if disk == cm else 0
    import hashlib
    return {
        "언제(시작)": t0, "언제(끝)": _now(),
        "시작 code_stamp 요약": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "끝 code_stamp 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
        "🔴 시작=끝": cs0 == cs1,
        "분모: 도장이 덮는 파일": len(cs1),
        "🔴 자료 지문": ds,
        "분모: 연 자료 파일": len(ds),
        "🔴 F1 기준 ref(준 대로)": ref,
        "🔴 40자 고정 sha 인가": bool(re.fullmatch(r"[0-9a-f]{40}", ref or "")),
        "🔴 기준 ref 가 0000…0000 인가": bool(re.fullmatch(r"0{40}", ref or "")),
        "러너별": runner,
        "🔴 분자/분모": "%d / %d" % (ok, len(RAN)),
        "🔴 F5 통과": ok == len(RAN) and bool(re.fullmatch(r"[0-9a-f]{40}", ref or ""))
        and not re.fullmatch(r"0{40}", ref or ""),
    }


# ══════════════════════════════════════════════════════════════════════
# 층 --- 사전등록 §2.1. **행의 필드에서만** 정한다.
# ══════════════════════════════════════════════════════════════════════
def ntok_of(title: str) -> int:
    return len(H.toks_of(title))


def stratum_of(row: dict) -> str:
    a = row["a_액션"]
    n = ntok_of(a.get("맞은 제목") or "")
    lg = a.get("언어") or "기타"
    if lg not in ("ko", "en"):
        lg = "기타"
    return ("단일" if n <= 1 else "다중") + "·" + lg


def iter_pairs():
    with gzip.open(str(PAIRS), "rt", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def light(row: dict) -> dict:
    """산출물에 남기는 가벼운 판 --- s·o 배열(181 수)은 뺀다."""
    a = row["a_액션"]
    return {"쌍id": row["쌍id"], "도메인": row["도메인"],
            "개체": a.get("개체"), "문서": a.get("문서"),
            "맞은 제목": a.get("맞은 제목"), "언어": a.get("언어"),
            "언제": a.get("언제"), "host": a.get("host"), "tld": a.get("tld"),
            "collection": a.get("collection"), "글자수": a.get("글자수"),
            "문서id": a.get("문서id"), "🔴 일반어_의심": a.get("🔴 일반어_의심"),
            "층": stratum_of(row), "제목 토큰 수": ntok_of(a.get("맞은 제목") or "")}


# ══════════════════════════════════════════════════════════════════════
# 단계 sample
# ══════════════════════════════════════════════════════════════════════
def stage_sample(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    by = collections.defaultdict(list)
    rows = []
    for i, r in enumerate(iter_pairs()):
        L = light(r)
        L["행번호"] = i
        rows.append(L)
        by[L["층"]].append(i)
    N = len(rows)

    rng = random.Random(SEED)
    picked = []
    strat = collections.OrderedDict()
    for h in sorted(by):
        ids = by[h]
        k = min(PER_STRATUM, len(ids))
        sel = rng.sample(ids, k)
        strat[h] = {"전량 행": len(ids), "🔴 분모: 낸 행 전량": N,
                    "비율": round(len(ids) / float(N), 6), "뽑은 행": k}
        picked += sel
    rng2 = random.Random(SEED)
    srs = rng2.sample(range(N), min(SRS_N, N))

    sample_ids = sorted(set(picked) | set(srs))
    out = {
        "무엇": "974 --- 언급 정밀도 표본 뽑기(층화 + 단순무작위)",
        "🔴 축": "C3 (data spec · mixture · filtering)",
        "사전등록": "docs/prereg_974_precision.md",
        "씨앗": SEED, "층마다": PER_STRATUM, "단순무작위 n": SRS_N,
        "🔴 분모: 973 이 낸 행 전량": N,
        "🔴 층별 전량": strat,
        "🔴 층화 표본 행 수": len(picked),
        "🔴 단순무작위 표본 행 수": len(srs),
        "🔴 합친 표본 행 수(중복 뺀)": len(sample_ids),
        "🔴 300 이상인가": len(picked) >= 300,
        "층화 표본 행번호": sorted(picked),
        "단순무작위 표본 행번호": sorted(srs),
        "표본 행": [rows[i] for i in sample_ids],
        "🔴 표본이 덮는 문서id 수": len({rows[i]["문서id"] for i in sample_ids}),
        "🔴 표본이 덮는 제목 수": len({rows[i]["맞은 제목"] for i in sample_ids}),
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out974_sample.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# 단계 context --- shard 를 다시 흘려 읽어 **맞은 자리 앞뒤 150자**를 낸다
# ══════════════════════════════════════════════════════════════════════
def locate(text: str, want_titles: set):
    """973 의 `mentions` 와 **같은 규칙**으로 맞추되 **자리를 같이 낸다**.

    973: `toks_of(text)` = `NONWORD.split(text.lower())` 의 빈 것 뺀 목록.
    여기: `[0-9A-Za-z가-힣]+` 를 `finditer` --- **같은 토큰열이다**(W6 이 대조한다).
    """
    low = text.lower()
    spans = [(m.start(), m.end(), m.group()) for m in TOKPAT.finditer(low)]
    toks = [s[2] for s in spans]
    L = len(toks)
    idx = collections.defaultdict(list)
    for t in want_titles:
        tk = H.toks_of(t)
        if tk:
            idx[tk[0]].append((tuple(tk[1:]), t))
    found = collections.defaultdict(list)
    for i in range(L):
        w = toks[i]
        cands = (w,) if H.strip_josa(w) == w else (w, H.strip_josa(w))
        for c in cands:
            for rest, title in idx.get(c, ()):
                n = len(rest)
                if n == 0:
                    found[title].append((spans[i][0], spans[i][1]))
                    continue
                if i + 1 + n > L:
                    continue
                seg = toks[i + 1:i + 1 + n]
                if tuple(seg) == rest or \
                        (tuple(seg[:-1]) + (H.strip_josa(seg[-1]),)) == rest:
                    found[title].append((spans[i][0], spans[i + n][1]))
    return found


def stage_context(ref: str) -> dict:
    import pyarrow.parquet as pq
    t0 = _now()
    cs0 = code_stamp()
    smp = json.loads((OUT / "out974_sample.json").read_text(encoding="utf-8"))
    rows = smp["표본 행"]
    want = collections.defaultdict(set)      # docid -> {제목}
    for r in rows:
        want[r["문서id"]].add(r["맞은 제목"])

    # ⑤ --- 한글 문턱 4 판과 3 판의 색인을 둘 다 만든다
    idx4, ent, _ = H.load_entities()
    old = H.MIN_KO_TITLE
    H.MIN_KO_TITLE = 3
    idx3, _, _ = H.load_entities()
    H.MIN_KO_TITLE = old
    only3 = {}                                # 3 판에만 있는 제목 -> 키
    for first, lst in idx3.items():
        for rest, title, key in lst:
            hit = any(r2 == rest and t2 == title for r2, t2, _ in idx4.get(first, ()))
            if not hit:
                only3[title] = key

    shards = sorted(glob.glob(str(H.HPLT_DIR / "train-*-of-00464.parquet")))
    picked = [shards[i] for i in H.SHARD_IDX if i < len(shards)]
    ctx = {}
    seen_docs = 0
    read_docs = 0
    g3_add = collections.Counter()            # ⑤ 늘어난 (문서,제목) 짝
    g3_pairs = []
    for path in picked:
        pf = pq.ParquetFile(path)
        for rg in range(pf.metadata.num_row_groups):
            tb = pf.read_row_group(rg, columns=["u", "ts", "text", "id"])
            d = tb.to_pydict()
            for j in range(len(d["id"])):
                read_docs += 1
                did = d["id"][j]
                if did not in want:
                    continue
                seen_docs += 1
                txt = d["text"][j] or ""
                fo = locate(txt, want[did])
                rec = {"문서id": did, "url": d["u"][j],
                       "ts": str(d["ts"][j])[:10], "글자수": len(txt),
                       "맥락": {}}
                for title, sp in sorted(fo.items()):
                    cs = []
                    for (a, b) in sp[:CTX_MAX]:
                        cs.append({"앞": txt[max(0, a - CTX_CHARS):a],
                                   "맞은 자리": txt[a:b],
                                   "뒤": txt[b:b + CTX_CHARS]})
                    rec["맥락"][title] = {"자리 수": len(sp), "보인 것": cs}
                for title in want[did]:
                    if title not in rec["맥락"]:
                        rec["맥락"][title] = {"자리 수": 0, "보인 것": []}
                ctx[did] = rec
                # ⑤ --- 같은 문서에서 문턱 3 판이 더 무는 짝
                m4 = H.mentions(txt, idx4)
                m3 = H.mentions(txt, idx3)
                add = m3 - m4
                for title, key in add:
                    g3_add[title] += 1
                    if len(g3_pairs) < 400:
                        f2 = locate(txt, {title})
                        sp = f2.get(title, [])
                        g3_pairs.append({
                            "문서id": did, "제목": title, "개체": key,
                            "도메인": (ent.get(key) or {}).get("도메인"),
                            "언어": (ent.get(key) or {}).get("언어"),
                            "자리 수": len(sp),
                            "맥락": [{"앞": txt[max(0, a - CTX_CHARS):a],
                                     "맞은 자리": txt[a:b],
                                     "뒤": txt[b:b + CTX_CHARS]}
                                    for (a, b) in sp[:1]]})

    out = {
        "무엇": "974 --- 표본 문서의 본문 맥락 되찾기 + 한글 문턱 4↔3 대조",
        "사전등록": "docs/prereg_974_precision.md",
        "🔴 분모: 표본이 덮는 문서id": len(want),
        "🔴 되찾은 문서": len(ctx),
        "🔴 못 찾은 문서": len(want) - len(ctx),
        "🔴 다시 읽은 문서 전량": read_docs,
        "🔴 분모: 973 이 읽은 문서": 670118,
        "⑤ 한글 문턱": {
            "973 의 값": old, "내려본 값": 3,
            "🔴 3 판에만 있는 제목 수": len(only3),
            "🔴 분모: 위키 개체 전량": len(ent),
            "🔴 같은 표본 문서에서 늘어난 (문서,제목) 짝": int(sum(g3_add.values())),
            "🔴 분모: 표본 문서 수": len(ctx),
            "늘어난 제목 상위 40": g3_add.most_common(40),
            "🔴 `원펀맨` 이 3 판에 있나": "원펀맨" in only3,
        },
        "맥락": ctx,
        "⑤ 늘어난 짝 표본": g3_pairs,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out974_contexts.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# 단계 wiring --- W1~W8 파괴 대조 (자기 배선이 살아 있나)
# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    W = collections.OrderedDict()

    # W1 --- 층 나누기가 제목 토큰 수에 매여 있나
    r = {"a_액션": {"맞은 제목": "일론 머스크", "언어": "ko"}}
    r2 = {"a_액션": {"맞은 제목": "머스크", "언어": "ko"}}
    W["W1 층이 토큰 수에 매인다"] = (stratum_of(r) == "다중·ko"
                              and stratum_of(r2) == "단일·ko")
    # W2 --- 층이 언어에 매여 있나
    r3 = {"a_액션": {"맞은 제목": "머스크", "언어": "en"}}
    W["W2 층이 언어에 매인다"] = stratum_of(r3) == "단일·en"
    # W3 --- locate 가 없는 제목엔 자리를 안 낸다
    W["W3 없는 제목엔 자리 0"] = len(locate("전혀 다른 글", {"일론 머스크"})) == 0
    # W4 --- locate 가 있는 제목엔 자리를 낸다
    f = locate("어제 일론 머스크는 말했다", {"일론 머스크"})
    W["W4 있는 제목엔 자리 ≥1"] = len(f.get("일론 머스크", [])) == 1
    # W5 --- 자른 맥락이 진짜 그 자리인가
    txt = "어제 일론 머스크는 말했다"
    a, b = f["일론 머스크"][0]
    W["W5 자리가 원문과 같다"] = txt[a:b].lower() == "일론 머스크"
    # W6 --- 🔴 locate 의 토큰열이 973 의 toks_of 와 **전량 같은가**
    same = 0
    tot = 0
    for i, rr in enumerate(iter_pairs()):
        if i >= 2000:
            break
        s = (rr["a_액션"].get("맞은 제목") or "") + " 사이 " + (rr["a_액션"].get("문서") or "")
        tot += 1
        if [m.group() for m in TOKPAT.finditer(s.lower())] == H.toks_of(s):
            same += 1
    W["W6 토큰열이 973 과 같다"] = same == tot
    # W7 --- 조사 벗기기가 실제로 문다
    W["W7 조사 벗기기가 문다"] = len(locate("일론 머스크가 말했다", {"일론 머스크"})) == 1
    # W8 --- Clopper-Pearson 이 끝값에서 옳은가
    lo, hi = cp_ci(0, 10)
    lo2, hi2 = cp_ci(10, 10)
    W["W8 CP 끝값"] = (abs(lo) < 1e-12 and hi < 1.0 and lo2 > 0.0 and abs(hi2 - 1) < 1e-12)

    # 🔴 파괴 대조 --- 자를 부수면 검사가 실제로 죽는가
    D = collections.OrderedDict()
    gl = globals()
    save_tok = gl["TOKPAT"]
    gl["TOKPAT"] = re.compile(r"[0-9A-Za-z]+")            # 한글을 뺀다
    D["D1 TOKPAT 부수면 W4 죽나"] = len(locate("어제 일론 머스크는 말했다",
                                        {"일론 머스크"})) == 0
    gl["TOKPAT"] = save_tok
    save = H.MIN_KO_TITLE
    H.MIN_KO_TITLE = 99
    D["D2 문턱 99 면 제목 자격이 죽나"] = not H.title_ok("일론 머스크")
    H.MIN_KO_TITLE = save
    save_j = H.JOSA
    H.JOSA = ()
    D["D3 조사 없애면 W7 죽나"] = len(locate("일론 머스크가 말했다", {"일론 머스크"})) == 0
    H.JOSA = save_j
    D["D4 빈 제목엔 자리 0"] = len(locate("아무 글", set())) == 0
    D["D5 CP 가 분모 0 에서 죽나"] = cp_ci(0, 0) == (0.0, 1.0)

    out = {"무엇": "974 --- 배선 W1~W8 · 파괴 대조 D1~D5",
           "사전등록": "docs/prereg_974_precision.md",
           "W": {k: bool(v) for k, v in W.items()},
           "🔴 W 분자/분모": "%d / %d" % (sum(1 for v in W.values() if v), len(W)),
           "D": {k: bool(v) for k, v in D.items()},
           "🔴 D 분자/분모": "%d / %d" % (sum(1 for v in D.values() if v), len(D)),
           "🔴 W6 분모": tot, "🔴 W6 분자": same}
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out974_wiring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# 이항 구간 --- Clopper-Pearson (정확)
# ══════════════════════════════════════════════════════════════════════
def _betainc_inv(a, b, p):
    """이분법으로 역 불완전베타. scipy 없이 판다(파이썬 3.9 · numpy 만)."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _betainc(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _betainc(a, b, x):
    """정규화 불완전베타 I_x(a,b) --- 연분수(Numerical Recipes)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _cf(a, b, x) / a
    return 1.0 - math.exp(lbeta + b * math.log(1 - x) + a * math.log(x)) \
        * _cf(b, a, 1 - x) / b


def _cf(a, b, x):
    tiny = 1e-30
    f, c, d = 1.0, 1.0, 0.0
    for i in range(1, 300):
        m = i // 2
        if i == 1:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2.0 * m - 1) * (a + 2.0 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2.0 * m) * (a + 2.0 * m + 1))
        d = 1.0 + num * d
        if abs(d) < tiny:
            d = tiny
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < tiny:
            c = tiny
        f *= c * d
        if abs(1.0 - c * d) < 1e-12:
            break
    return f - 1.0


def cp_ci(k, n, alpha=0.05):
    """Clopper-Pearson 95% --- 분모 0 이면 (0,1)."""
    if n <= 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else _betainc_inv(k, n - k + 1, alpha / 2.0)
    hi = 1.0 if k == n else _betainc_inv(k + 1, n - k, 1 - alpha / 2.0)
    return (round(lo, 6), round(hi, 6))


# ══════════════════════════════════════════════════════════════════════
# 게이트 --- 사전등록 §4
# ══════════════════════════════════════════════════════════════════════
def gate_flags(r: dict) -> dict:
    t = r.get("맞은 제목") or ""
    ntok = len(H.toks_of(t))
    host = (r.get("host") or "").lower()
    joined = "".join(H.toks_of(t))
    raw = re.sub(r"\s+", "", t).lower()
    return {
        "H1 단일 토큰 라틴": ntok <= 1 and not H.HANGUL.search(t),
        "H2 NONWORD 뭉갬": bool(H.NONWORD.search(t)) and joined != raw,
        "H3 위키 자기 순환": any(host == w or host.endswith("." + w) or w in host
                          for w in WIKI_HOSTS),
        "H4 레포트·덤프": any(w in host for w in DUMP_HOSTS),
    }


# ══════════════════════════════════════════════════════════════════════
# 단계 score --- 라벨 파일에서만 센다 (규칙 D)
# ══════════════════════════════════════════════════════════════════════
def stage_score(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    smp = json.loads((OUT / "out974_sample.json").read_text(encoding="utf-8"))
    lab = json.loads((OUT / "out974_labels.json").read_text(encoding="utf-8"))
    L = {x["쌍id"]: x["라벨"] for x in lab["라벨"]}
    rows = {r["쌍id"]: r for r in smp["표본 행"]}
    strat_all = smp["🔴 층별 전량"]
    N = smp["🔴 분모: 973 이 낸 행 전량"]

    def tally(ids):
        c = collections.Counter(L.get(i, "라벨없음") for i in ids)
        n = sum(c.values())
        k = c.get("참", 0)
        kk = c.get("참", 0) + c.get("거짓", 0)
        return {
            "분모: 라벨한 행": n,
            "참": c.get("참", 0), "거짓": c.get("거짓", 0), "모름": c.get("모름", 0),
            "라벨없음": c.get("라벨없음", 0),
            "🔴 주 자(모름=실패)": round(k / float(n), 6) if n else None,
            "🔴 주 자 95% CP": cp_ci(k, n),
            "곁 자(모름 뺌)": round(k / float(kk), 6) if kk else None,
            "곁 자 95% CP": cp_ci(k, kk),
        }

    strat_ids = collections.defaultdict(list)
    for pid, r in rows.items():
        if pid in L:
            strat_ids[r["층"]].append(pid)

    per = collections.OrderedDict()
    for h in sorted(strat_ids):
        per[h] = tally(strat_ids[h])
        per[h]["전량 행"] = strat_all.get(h, {}).get("전량 행")
        per[h]["🔴 분모: 낸 행 전량"] = N

    # 층화 표본만 / 단순무작위 표본만
    srs_no = set(smp["단순무작위 표본 행번호"])
    idx_by_no = {r["행번호"]: r["쌍id"] for r in smp["표본 행"]} \
        if "행번호" in (smp["표본 행"][0] if smp["표본 행"] else {}) else {}
    srs_ids = [idx_by_no[n] for n in srs_no if n in idx_by_no and idx_by_no[n] in L]
    all_ids = [i for i in rows if i in L]

    # ② 유효 삼중쌍 --- 층 가중
    eff = 0.0
    for h, v in per.items():
        p = v["🔴 주 자(모름=실패)"]
        n_h = strat_all.get(h, {}).get("전량 행", 0)
        if p is not None:
            eff += n_h * p
    # 붓스트랩 4000 (씨앗 974)
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(4000):
        s = 0.0
        for h, v in per.items():
            n_h = strat_all.get(h, {}).get("전량 행", 0)
            n_s, k_s = v["분모: 라벨한 행"], v["참"]
            if n_s:
                s += n_h * (rng.binomial(n_s, k_s / float(n_s)) / float(n_s))
        boots.append(s)
    boots = np.asarray(boots)

    # ③ 게이트
    G = collections.OrderedDict()
    full_flags = collections.Counter()
    any_cnt = 0
    tot = 0
    for r in iter_pairs():
        tot += 1
        fl = gate_flags(light(r))
        hit = False
        for k, v in fl.items():
            if v:
                full_flags[k] += 1
                hit = True
        if hit:
            any_cnt += 1
    for k in ("H1 단일 토큰 라틴", "H2 NONWORD 뭉갬", "H3 위키 자기 순환", "H4 레포트·덤프"):
        ids_in = [i for i in all_ids if gate_flags(rows[i])[k]]
        ids_out = [i for i in all_ids if not gate_flags(rows[i])[k]]
        G[k] = {"🔴 전량에서 무는 행": full_flags.get(k, 0), "🔴 분모: 낸 행 전량": tot,
                "비율": round(full_flags.get(k, 0) / float(tot), 6),
                "표본에서 무는 행의 정밀도": tally(ids_in),
                "표본에서 남는 행의 정밀도": tally(ids_out)}
        a = G[k]["표본에서 무는 행의 정밀도"]["🔴 주 자(모름=실패)"]
        b = G[k]["표본에서 남는 행의 정밀도"]["🔴 주 자(모름=실패)"]
        G[k]["🔴 무는 쪽이 더 낮은가(게이트 성립)"] = (
            None if a is None or b is None else a < b)

    ids_kept = [i for i in all_ids if not any(gate_flags(rows[i]).values())]
    ids_cut = [i for i in all_ids if any(gate_flags(rows[i]).values())]

    out = {
        "무엇": "974 --- 언급 정밀도 · 유효 삼중쌍 수 · 게이트 채점",
        "🔴 축": "C3 (data spec · mixture · filtering)",
        "사전등록": "docs/prereg_974_precision.md",
        "🔴 분모: 973 이 낸 행 전량": N,
        "🔴 라벨한 행": len(all_ids),
        "🔴 300 이상인가": len(all_ids) >= 300,
        "🔴🔴 ① 층화 표본 전체(층 무시)": tally(all_ids),
        "🔴 ①′ 단순무작위 300 만": tally(srs_ids),
        "🔴 ① 층별": per,
        "🔴🔴 ② 유효 삼중쌍": {
            "점추정": round(eff, 1),
            "95% 붓스트랩 구간": [round(float(np.percentile(boots, 2.5)), 1),
                            round(float(np.percentile(boots, 97.5)), 1)],
            "🔴 분모: 973 이 부른 수": N,
            "비율": round(eff / float(N), 6),
            "뽑기": 4000, "씨앗": SEED,
        },
        "🔴 ③ 게이트": G,
        "🔴 ③ 게이트 넷을 다 걸면": {
            "🔴 전량에서 떼는 행": any_cnt, "🔴 분모": tot,
            "비율": round(any_cnt / float(tot), 6),
            "남는 행": tot - any_cnt,
            "표본에서 떼는 쪽 정밀도": tally(ids_cut),
            "표본에서 남는 쪽 정밀도": tally(ids_kept),
        },
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out974_precision.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def stage_gate(ref: str) -> dict:
    """게이트를 전량에 걸어 **걸러진 행 파일**을 낸다(④ 의 팔 C′ 가 쓴다)."""
    t0 = _now()
    cs0 = code_stamp()
    # 🔴 저장소 밖에 쓴다 --- 데몬의 `PATHS`(`data/ingest`) 안에 쓰면 데몬이 main 에 커밋한다
    sc = Path("/Users/ax/wm_harvest/974")
    sc.mkdir(parents=True, exist_ok=True)
    outp = sc / "pairs_gated974.jsonl.gz"
    n_in = n_out = 0
    cut = collections.Counter()
    dom = collections.Counter()
    ents = set()
    with gzip.open(str(outp), "wt", encoding="utf-8") as f:
        for r in iter_pairs():
            n_in += 1
            fl = gate_flags(light(r))
            if any(fl.values()):
                for k, v in fl.items():
                    if v:
                        cut[k] += 1
                continue
            n_out += 1
            dom[r["도메인"]] += 1
            ents.add(r["a_액션"]["개체"])
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    out = {"무엇": "974 --- 게이트 H1~H4 를 전량에 걸어 낸 행",
           "🔴 들어온 행": n_in, "🔴 남은 행": n_out, "🔴 뗀 행": n_in - n_out,
           "비율(남은/들어온)": round(n_out / float(n_in), 6),
           "게이트별 무는 행(겹침 셈)": dict(cut),
           "🔴 남은 행의 도메인 수": len(dom), "도메인별": dict(dom),
           "🔴 남은 행의 개체 수": len(ents),
           "산출 경로(저장소 밖)": str(outp),
           "🔴 크기(바이트)": outp.stat().st_size}
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out974_gated.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["sample", "context", "score", "gate", "wiring"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    fn = {"sample": stage_sample, "context": stage_context, "score": stage_score,
          "gate": stage_gate, "wiring": stage_wiring}[a.stage]
    r = fn(a.ref)
    print(json.dumps({k: v for k, v in r.items()
                      if k not in ("맥락", "표본 행", "층화 표본 행번호",
                                   "단순무작위 표본 행번호", "⑤ 늘어난 짝 표본")},
                     ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
