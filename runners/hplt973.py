#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""973 --- **축 C3**(data spec · mixture · filtering) 의 첫 수.

HPLT 2.0 `kor_Hang` shard 를 **끝까지 통과시켜** (s,a,o) 삼중쌍을 낸다. 「0 → n」이 전부다.

🔴 **사전등록 `docs/prereg_973_hplt_c3.md`(측정 전 단독 커밋)의 자를 글자 그대로 옮긴다.**
🔴 **바퀴를 다시 만들지 않는다**(원장 954~957): 도박 정규식·URL 정규화는
   `runners/dupe954_hplt_scan.py` 의 **생산 함수를 부른다**. 형태소 분석기는 안 쓴다
   (954 결론: 공백 5-gram 대비 이득 없음). MinHash 도 안 쓴다(진짜 Jaccard ≥0.9 = 0).

씀:
    python3 runners/hplt973.py --stage wiring  --ref <40자 sha>
    python3 runners/hplt973.py --stage build   --ref <40자 sha>
    python3 runners/hplt973.py --stage census  --ref <40자 sha>

🔴 조항 59 --- 종료코드가 아니라 **연 shard 수 · 읽은 문서 수 · 낸 행 수**를 산출물에 적는다.
🔴 조항 60 --- 모든 비율에 **분모를 같은 자리에** 적는다.
🔴 산출물은 저장소 밖(`/Users/ax/wm_harvest/973/`)에 쓰고 크기를 재고 배관으로 반입한다.
"""
import argparse
import collections
import datetime as dt
import glob
import gzip
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import runners.predict971 as P                     # noqa: E402  생산 함수(도장·sha)
import runners.dupe954_hplt_scan as S954           # noqa: E402  생산 함수(도박 자·URL 정규화)

SCRATCH = Path("/Users/ax/wm_harvest/973")
SCRATCH.mkdir(parents=True, exist_ok=True)
PROG = SCRATCH / "progress.jsonl"

RAN = ("runners/hplt973.py", "runners/dupe954_hplt_scan.py", "runners/predict971.py")

# ══════════════════════════════════════════════════════════════════════
# 자 --- 사전등록 §3·§4·§5 에서 그대로 옮긴 상수. 측정 뒤에 안 바꾼다.
# ══════════════════════════════════════════════════════════════════════
SHARD_IDX = (0, 58, 116, 174, 232, 290, 348, 406)   # §5
MIN_PROB = 0.9          # G3
MIN_CHARS = 200         # G5
MIN_HANGUL = 0.5        # G5
MAXN = 5                # §4 공백 5-gram
MIN_KO_TITLE = 4        # §4
MIN_LAT_TITLE = 6       # §4
ROW_CAP = 300000        # §5
DF_CAP = 0.01           # §4 일반어 의심
S_DAYS = 90             # §2
O_DAYS = 91             # §2

JOSA = ("이라는", "라는", "으로", "에서", "에게", "부터", "까지",
        "은", "는", "이", "가", "을", "를", "의", "에", "와", "과", "도", "로", "만")

PAREN = re.compile(r"\s*\([^)]*\)\s*$")
NONWORD = re.compile(r"[^0-9A-Za-z가-힣]+")
HANGUL = re.compile(r"[가-힣]")

SRC_TAG = "hplt_ko"
WIKI_DIR = ROOT / "data/ingest/wiki_daily959"
HPLT_DIR = ROOT / "data/ingest/hplt_ko"

# 원장 954~957 이 이미 조사한 것 --- 다시 만들지 않는다(사전등록 §3 각주)
REUSE = {
    "도박 정규식": "runners/dupe954_hplt_scan.py:GAMBLE_PAT (954 전량 1.7666%)",
    "URL 정규화": "runners/dupe954_hplt_scan.py:norm_url (954 전량 38,866,835 → 20,080,264 키)",
    "MinHash 안 쓴다": "954 실측 --- 0.28% 제거 · 진짜 Jaccard ≥0.9 = 0",
    "형태소 분석 안 쓴다": "954~957 실측 --- 공백 5-gram 대비 이득 없음",
    "nemo-curator/dolma 안 쓴다": "darwin 거부 · numpy 로 datatrove 와 공존 불가",
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(**kw):
    kw["시각"] = _now()
    with PROG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def code_stamp() -> dict:
    """🔴 규칙 C --- `lab/*.py` 전량 + **내가 돌린 러너 전부**. `P._sha_file` 을 **부른다**."""
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


# ══════════════════════════════════════════════════════════════════════
# §4 --- 개체 언급 자 (생산 함수)
# ══════════════════════════════════════════════════════════════════════
def norm_title(t: str) -> str:
    t = PAREN.sub("", (t or "").strip())
    return re.sub(r"\s+", " ", t).strip()


def toks_of(s: str) -> list:
    return [x for x in NONWORD.split((s or "").lower()) if x]


def strip_josa(tok: str) -> str:
    for j in JOSA:
        if len(tok) > len(j) + 1 and tok.endswith(j):
            return tok[:-len(j)]
    return tok


def title_ok(t: str) -> bool:
    """§4 자격 --- 한글이 있으면 4자, 라틴만이면 6자."""
    if not t:
        return False
    need = MIN_KO_TITLE if HANGUL.search(t) else MIN_LAT_TITLE
    return len(t) >= need


def hangul_ratio(s: str) -> float:
    if not s:
        return 0.0
    return len(HANGUL.findall(s)) / float(len(s))


def load_entities() -> tuple:
    """위키 일별 상태 3,896 개체를 읽어 ① 언급 색인 ② 날짜/조회수 배열을 만든다."""
    idx = collections.defaultdict(list)     # 첫 토큰 -> [(나머지 토큰들, 제목, 키)]
    ent = {}                                # 키 -> dict
    files = sorted(glob.glob(str(WIKI_DIR / "*.jsonl.gz")))
    for p in files:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                k = d["키"]
                days = np.asarray(d.get("날짜") or [], dtype=np.int64)
                views = np.asarray(d.get("조회수") or [], dtype=np.int64)
                if days.size != views.size or days.size == 0:
                    continue
                order = np.argsort(days)
                days, views = days[order], views[order]
                ordn = np.asarray([dt.date(int(x) // 10000, (int(x) // 100) % 100,
                                           int(x) % 100).toordinal() for x in days],
                                  dtype=np.int64)
                ent[k] = {"도메인": d.get("도메인"), "문서": d.get("문서"),
                          "언어": d.get("언어"), "ord": ordn, "views": views}
                t = norm_title(d.get("문서"))
                if not title_ok(t):
                    continue
                tk = toks_of(t)
                if not tk or len(tk) > MAXN:
                    continue
                idx[tk[0]].append((tuple(tk[1:]), t.lower(), k))
    return idx, ent, files


def mentions(text: str, idx) -> set:
    """문서에서 개체 언급을 찾는다 --- 공백 n-gram(≤5) + 얼린 조사 벗기기."""
    tk = toks_of(text)
    L = len(tk)
    out = set()
    for i in range(L):
        w = tk[i]
        cands = (w,) if strip_josa(w) == w else (w, strip_josa(w))
        for c in cands:
            lst = idx.get(c)
            if not lst:
                continue
            for rest, title, key in lst:
                n = len(rest)
                if n == 0:
                    out.add((title, key))
                    continue
                if i + 1 + n > L:
                    continue
                seg = tk[i + 1:i + 1 + n]
                if tuple(seg) == rest or \
                        (tuple(seg[:-1]) + (strip_josa(seg[-1]),)) == rest:
                    out.add((title, key))
    return out


def window(e: dict, day_ord: int):
    """§2 --- s = D−90…D−1(90일) · o = D…D+90(91일). 전량 덮을 때만 낸다(G9)."""
    o = e["ord"]
    lo, hi = day_ord - S_DAYS, day_ord + O_DAYS - 1
    a = int(np.searchsorted(o, lo, "left"))
    b = int(np.searchsorted(o, hi, "right"))
    if b - a != (S_DAYS + O_DAYS):
        return None
    seg_o, seg_v = o[a:b], e["views"][a:b]
    if int(seg_o[0]) != lo or int(seg_o[-1]) != hi:
        return None
    if not np.array_equal(seg_o, np.arange(lo, hi + 1)):
        return None
    return seg_v[:S_DAYS].tolist(), seg_v[S_DAYS:].tolist()


def tld_of(host: str) -> str:
    return host.rsplit(".", 1)[-1] if host and "." in host else ""


# ══════════════════════════════════════════════════════════════════════
# 단계 build --- 사전등록 §3 게이트 G1~G9
# ══════════════════════════════════════════════════════════════════════
def stage_build(ref: str, shard_idx=SHARD_IDX, row_cap=ROW_CAP, out_name="pairs.jsonl.gz") -> dict:
    import pyarrow.parquet as pq

    t0 = time.time()
    cs0 = code_stamp()
    idx, ent, wiki_files = load_entities()
    _prog(단계="build", 무엇="개체 색인 완성", 첫토큰=len(idx), 개체=len(ent))

    shards = sorted(glob.glob(str(HPLT_DIR / "train-*-of-00464.parquet")))
    picked = [shards[i] for i in shard_idx if i < len(shards)]

    G = collections.OrderedDict((k, 0) for k in
                                ["G0 읽은 문서", "G1 filter=keep", "G2 robotstxt=allowed",
                                 "G3 kor_Hang·prob≥0.9", "G4 도박 아님", "G5 길이·한글비율",
                                 "G6 URL 정규화 첫등장", "G7 본문 첫등장", "G8 개체 언급 ≥1"])
    seen_url, seen_txt = set(), set()
    colls = collections.Counter()
    tlds = collections.Counter()
    ts_min, ts_max = None, None
    hits = []                     # (키, 제목, 날짜ord, host, tld, coll, 글자수, docid)
    df = collections.Counter()    # 제목 -> 문서 빈도
    capped = False
    shard_rows = []

    for si, path in zip([i for i in shard_idx if i < len(shards)], picked):
        pf = pq.ParquetFile(path)
        n_here = 0
        for rg in range(pf.metadata.num_row_groups):
            tb = pf.read_row_group(rg, columns=["u", "ts", "text", "lang", "prob",
                                                "collection", "filter", "robotstxt", "id"])
            d = tb.to_pydict()
            for j in range(len(d["id"])):
                G["G0 읽은 문서"] += 1
                n_here += 1
                if d["filter"][j] != "keep":
                    continue
                G["G1 filter=keep"] += 1
                if d["robotstxt"][j] != "allowed":
                    continue
                G["G2 robotstxt=allowed"] += 1
                lg, pr = d["lang"][j] or [], d["prob"][j] or []
                if not lg or lg[0] != "kor_Hang" or not pr or float(pr[0]) < MIN_PROB:
                    continue
                G["G3 kor_Hang·prob≥0.9"] += 1
                txt = d["text"][j] or ""
                if S954.GAMBLE_PAT.search(txt.encode("utf-8")):
                    continue
                G["G4 도박 아님"] += 1
                if len(txt) < MIN_CHARS or hangul_ratio(txt[:4000]) < MIN_HANGUL:
                    continue
                G["G5 길이·한글비율"] += 1
                uh = hashlib.md5(S954.norm_url(d["u"][j]).encode("utf-8")).digest()[:8]
                if uh in seen_url:
                    continue
                seen_url.add(uh)
                G["G6 URL 정규화 첫등장"] += 1
                th = hashlib.md5(txt.encode("utf-8")).digest()[:8]
                if th in seen_txt:
                    continue
                seen_txt.add(th)
                G["G7 본문 첫등장"] += 1
                ms = mentions(txt, idx)
                if not ms:
                    continue
                G["G8 개체 언급 ≥1"] += 1
                ts = d["ts"][j]
                if ts is None:
                    continue
                colls[d["collection"][j]] += 1
                host = S954.host_of(d["u"][j])
                tl = tld_of(host)
                tlds[tl] += 1
                di = ts.date()
                if ts_min is None or di < ts_min:
                    ts_min = di
                if ts_max is None or di > ts_max:
                    ts_max = di
                for title, key in ms:
                    df[title] += 1
                    if len(hits) < row_cap:
                        hits.append((key, title, di.toordinal(), host, tl,
                                     d["collection"][j], len(txt), d["id"][j]))
                    else:
                        capped = True
            if rg % 20 == 0:
                _prog(단계="build", shard=si, rowgroup=rg, 읽은문서=G["G0 읽은 문서"],
                      언급문서=G["G8 개체 언급 ≥1"], 후보짝=len(hits), 초=round(time.time() - t0, 1))
        shard_rows.append({"shard": si, "파일": Path(path).name, "문서": n_here,
                           "sha256": P._sha_file(path)})
        _prog(단계="build", shard=si, 무엇="shard 끝", 문서=n_here, 초=round(time.time() - t0, 1))

    # 🔴 §4 일반어 의심 --- 분모는 이 주행의 **정제 통과 문서**(G7)
    den_df = max(1, G["G7 본문 첫등장"])
    common = {t for t, n in df.items() if n / float(den_df) > DF_CAP}

    # G9 --- 위키 창 덮기. (키, 날짜) 캐시로 s·o 를 한 번만 만든다
    cache = {}
    out_path = SCRATCH / out_name
    n_rows = 0
    dom_rows = collections.Counter()
    g9_fail = 0
    common_rows = 0
    ent_seen = set()
    with gzip.open(str(out_path), "wt", encoding="utf-8") as f:
        for key, title, dord, host, tl, coll, nchar, docid in hits:
            e = ent.get(key)
            if e is None:
                g9_fail += 1
                continue
            ck = (key, dord)
            if ck not in cache:
                cache[ck] = window(e, dord)
            w = cache[ck]
            if w is None:
                g9_fail += 1
                continue
            s_vals, o_vals = w
            day = dt.date.fromordinal(dord).isoformat()
            row = {
                "쌍id": "hplt:%s:%s" % (key, docid),
                "원천": SRC_TAG,
                "출처": "HPLT 2.0 kor_Hang 웹문서 × wiki_daily959 상태 (973 · 문서 언급 단위)",
                "도메인": e["도메인"],
                "a_액션": {"무엇": "이 한국어 웹문서가 이 개체를 언급했다",
                        "언제": day, "개체": key, "문서": e["문서"], "언어": e["언어"],
                        "맞은 제목": title, "🔴 일반어_의심": bool(title in common),
                        "host": host, "tld": tl, "collection": coll, "글자수": nchar,
                        "문서id": docid},
                "s_상태": {"무엇": "액션 앞 90일 일별 위키 조회수", "일수": S_DAYS, "값": s_vals},
                "o_결과": {"무엇": "액션 당일~뒤 90일 일별 위키 조회수", "일수": O_DAYS, "값": o_vals},
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n_rows += 1
            dom_rows[e["도메인"]] += 1
            ent_seen.add(key)
            if title in common:
                common_rows += 1

    size = out_path.stat().st_size
    cs1 = code_stamp()
    den0 = max(1, G["G0 읽은 문서"])
    gates = collections.OrderedDict()
    prev = None
    for k, v in G.items():
        gates[k] = {"통과": v, "🔴 분모(읽은 문서)": G["G0 읽은 문서"],
                    "비율": round(v / float(den0), 6),
                    "🔴 직전 게이트에서 떨어진 수": (None if prev is None else prev - v)}
        prev = v

    return {
        "무엇": "973 --- HPLT 2.0 kor_Hang 정제 첫 실주행 → (s,a,o) 삼중쌍",
        "🔴 축": "C3 (data spec · mixture · filtering)",
        "사전등록": "docs/prereg_973_hplt_c3.md",
        "언제(시작)": dt.datetime.fromtimestamp(t0, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "언제(끝)": _now(),
        "초": round(time.time() - t0, 1),
        "🔴 다시 안 만든 바퀴(954~957)": REUSE,
        "🔴 범위": {"대상 shard 인덱스": list(shard_idx),
                 "🔴 분모: HPLT shard 전량": len(shards),
                 "읽은 shard": shard_rows,
                 "행 상한": row_cap, "🔴 상한에 걸렸나": capped,
                 "ts 범위": [str(ts_min), str(ts_max)],
                 "collection별 언급문서": dict(colls.most_common()),
                 "🔴 collection 종 수": len(colls)},
        "🔴 게이트 G1~G8": gates,
        "🔴 G9 위키 창 덮기": {
            "들어온 문서-개체 짝": len(hits),
            "떨어진 짝": g9_fail,
            "🔴 분모": len(hits),
            "비율": round(g9_fail / float(max(1, len(hits))), 6)},
        "🔴🔴 낸 삼중쌍 행 수": n_rows,
        "🔴🔴 그 행이 덮는 도메인 수": len(dom_rows),
        "🔴 도메인별 행 수": dict(dom_rows.most_common()),
        "🔴 덮는 개체 수": len(ent_seen),
        "🔴 분모: 위키 개체 전량": len(ent),
        "🔴 일반어 의심": {"제목 수": len(common),
                     "🔴 분모: 맞은 제목 전량": len(df),
                     "문턱": "DF > %g × 정제 통과 문서 %d" % (DF_CAP, G["G7 본문 첫등장"]),
                     "표시된 행": common_rows,
                     "🔴 분모: 낸 행": n_rows,
                     "제목 목록(상위 40)": [t for t, _ in
                                      sorted(((t, df[t]) for t in common),
                                             key=lambda x: -x[1])[:40]]},
        "🔴 tld 상위 15": dict(tlds.most_common(15)),
        "산출물": {"경로(저장소 밖)": str(out_path),
                "🔴 크기(바이트)": size,
                "🔴 크기(MB)": round(size / 1048576.0, 3),
                "sha256": P._sha_file(out_path),
                "🔴 100MB 벽 아래인가": bool(size < 100 * 1048576)},
        "🔴 도장": {
            "시작 code_stamp 요약": P.stamp_digest(cs0),
            "끝 code_stamp 요약": P.stamp_digest(cs1),
            "🔴 시작=끝": bool(P.stamp_digest(cs0) == P.stamp_digest(cs1)),
            "분모: 도장이 덮는 파일": len(cs1),
            "🔴 돌린 러너 전부를 덮나": {r: bool(r in cs1) for r in RAN},
            "🔴 자료 지문": {
                "wiki_daily959 파일": {Path(p).name: P._sha_file(p) for p in wiki_files},
                "HPLT shard": {r["파일"]: r["sha256"] for r in shard_rows},
                "🔴 분모: 연 자료 파일": len(wiki_files) + len(shard_rows),
                "합친 요약": P.stamp_digest(
                    {**{p: P._sha_file(p) for p in wiki_files},
                     **{r["파일"]: r["sha256"] for r in shard_rows}})},
            "🔴 F1 --- 돌린 러너 sha vs 커밋 blob": ran_vs_blob(ref)},
    }


def ran_vs_blob(ref: str) -> dict:
    """🔴 F5 --- `P._sha_file`·`P.blob_sha` 를 **부른다**(다시 안 쓴다)."""
    per, bad = {}, []
    for r in RAN:
        disk = P._sha_file(ROOT / r) if (ROOT / r).is_file() else None
        blob = P.blob_sha(ref, r)
        ok = bool(disk is not None and disk == blob)
        per[r] = {"디스크 sha256": disk, "커밋 blob sha256": blob, "일치": ok}
        if not ok:
            bad.append(r)
    fixed = bool(len(ref) == 40 and all(c in "0123456789abcdef" for c in ref.lower()))
    return {"기준 ref(준 대로)": ref, "🔴 40자 고정 sha 인가": fixed,
            "러너별": per, "🔴 분자/분모": "%d / %d" % (len(RAN) - len(bad), len(RAN)),
            "🔴 어긋난 러너": bad, "🔴 F5 통과": bool(not bad and fixed)}


# ══════════════════════════════════════════════════════════════════════
# 단계 census --- §7 원천별 분모 · leave-one-source-out
# ══════════════════════════════════════════════════════════════════════
SOURCES = collections.OrderedDict([
    ("sao941", "data/ingest/sao941/pairs.jsonl.gz"),
    ("sao959", "data/ingest/sao959/pairs.jsonl.gz"),
    ("sao962", "data/ingest/sao962/pairs.jsonl.gz"),
])


def _count(path, tagged_key=None) -> tuple:
    """행 수 · 도메인별 행 수 · `원천` 태그가 박힌 행 수."""
    dom = collections.Counter()
    n, tagged = 0, 0
    with gzip.open(str(path), "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            n += 1
            dom[d.get("도메인")] += 1
            if d.get("원천"):
                tagged += 1
    return n, dom, tagged


def stage_census(ref: str, new_path=None) -> dict:
    t0 = time.time()
    cs0 = code_stamp()
    per = collections.OrderedDict()
    files = []
    for tag, rel in SOURCES.items():
        p = ROOT / rel
        n, dom, tagged = _count(p)
        files.append(str(p))
        per[tag] = {"경로": rel, "🔴 원천은 경로에서 결정된다(손 전사 아님)": True,
                    "행": n, "도메인 수": len(dom), "도메인별": dict(dom.most_common()),
                    "🔴 `원천` 태그가 박힌 행": tagged, "🔴 분모": n}
    if new_path:
        p = Path(new_path)
        n, dom, tagged = _count(p)
        files.append(str(p))
        per[SRC_TAG] = {"경로": str(p), "🔴 원천은 경로에서 결정된다(손 전사 아님)": True,
                        "행": n, "도메인 수": len(dom), "도메인별": dict(dom.most_common()),
                        "🔴 `원천` 태그가 박힌 행": tagged, "🔴 분모": n}

    def agg(keys):
        c = collections.Counter()
        for k in keys:
            c.update(per[k]["도메인별"])
        tot = sum(c.values())
        top = c.most_common(1)[0] if c else (None, 0)
        return {"행": tot, "도메인 수": len(c),
                "최대 도메인": top[0], "최대 도메인 행": top[1],
                "🔴 최대 도메인 점유율": round(top[1] / float(max(1, tot)), 6),
                "도메인별": dict(c.most_common())}

    allk = list(per)
    full = agg(allk)
    loso = collections.OrderedDict()
    for k in allk:
        rest = [x for x in allk if x != k]
        a = agg(rest)
        loso[k] = {
            "뺀 원천": k, "남은 원천": rest,
            "남은 행": a["행"], "🔴 Δ 행": a["행"] - full["행"],
            "남은 도메인 수": a["도메인 수"], "🔴 Δ 도메인 수": a["도메인 수"] - full["도메인 수"],
            "남은 최대 도메인 점유율": a["🔴 최대 도메인 점유율"],
            "🔴 Δ 최대 도메인 점유율": round(a["🔴 최대 도메인 점유율"]
                                  - full["🔴 최대 도메인 점유율"], 6)}

    base = agg([k for k in allk if k != SRC_TAG])
    cs1 = code_stamp()
    return {
        "무엇": "973 --- 원천별 기여도의 **분모**(leave-one-source-out 을 잴 수 있는 꼴)",
        "🔴 축": "C3",
        "언제(끝)": _now(), "초": round(time.time() - t0, 1),
        "🔴 원천별": per,
        "🔴 합친 코퍼스": full,
        "🔴 HPLT 넣기 전(=941+959+962)": base,
        "🔴🔴 행/도메인 변화": {
            "행 before": base["행"], "행 after": full["행"],
            "🔴 Δ 행": full["행"] - base["행"],
            "도메인 수 before": base["도메인 수"], "도메인 수 after": full["도메인 수"],
            "🔴 Δ 도메인 수": full["도메인 수"] - base["도메인 수"],
            "최대 도메인 점유율 before": base["🔴 최대 도메인 점유율"],
            "최대 도메인 점유율 after": full["🔴 최대 도메인 점유율"],
            "🔴 Δ 최대 도메인 점유율": round(full["🔴 최대 도메인 점유율"]
                                  - base["🔴 최대 도메인 점유율"], 6)},
        "🔴 leave-one-source-out": loso,
        "🔴 아직 0 인 것": ("예측 성능의 LOSO Δ --- 학습 팔이 없다. 이 사이클은 **분모만** 만든다. "
                    "지금 낸 LOSO Δ 는 ⓐ 도메인 수 ⓑ 최대 도메인 점유율 두 자에 대한 것이다"),
        "🔴 도장": {"시작 code_stamp 요약": P.stamp_digest(cs0),
                 "끝 code_stamp 요약": P.stamp_digest(cs1),
                 "🔴 시작=끝": bool(P.stamp_digest(cs0) == P.stamp_digest(cs1)),
                 "🔴 자료 지문": {Path(x).name: P._sha_file(x) for x in files},
                 "🔴 분모: 연 자료 파일": len(files),
                 "🔴 F1 --- 돌린 러너 sha vs 커밋 blob": ran_vs_blob(ref)},
    }


# ══════════════════════════════════════════════════════════════════════
# 단계 wiring --- 배선. 🔴 **생산 함수를 태운다**(재구현 검사는 죽은 검사다 · v4.0 §3)
# ══════════════════════════════════════════════════════════════════════
def _wiring_checks(mut=None) -> collections.OrderedDict:
    """🔴 `mut` 로 생산 함수를 하나 부수면 그 줄이 **붉어져야** 한다(파괴 대조)."""
    mut = mut or ""
    f_norm_title = (lambda t: t) if mut == "norm_title" else norm_title
    f_strip = (lambda t: t) if mut == "strip_josa" else strip_josa
    f_title_ok = (lambda t: True) if mut == "title_ok" else title_ok
    f_hangul = (lambda s: 1.0) if mut == "hangul_ratio" else hangul_ratio
    f_window = (lambda e, d: None) if mut == "window" else window
    f_ment = (lambda t, i: set()) if mut == "mentions" else mentions
    f_norm_url = (lambda u: u) if mut == "norm_url" else S954.norm_url
    f_gamble = (lambda b: None) if mut == "GAMBLE_PAT" else S954.GAMBLE_PAT.search
    f_sha = (lambda p: "0" * 64) if mut == "_sha_file" else P._sha_file

    W = collections.OrderedDict()
    W["W1 괄호 주석을 뗀다"] = bool(f_norm_title("노르웨이의 숲 (소설)") == "노르웨이의 숲")
    W["W2 조사를 벗긴다 · 짧으면 안 벗긴다"] = bool(
        f_strip("오징어게임을") == "오징어게임" and f_strip("게임") == "게임")
    # 🔴 실측 대가: 한글 4자 문턱이 `원펀맨`(3자 · AN-24960) 같은 **진짜 개체도 뗀다**.
    #    사전등록에 박은 자라 안 바꾼다 --- 대신 그 대가를 검사에 적어 둔다.
    W["W3 짧은 제목은 자격 미달"] = bool(f_title_ok("오징어 게임") and not f_title_ok("보석")
                                and not f_title_ok("원펀맨") and not f_title_ok("Origi"))
    W["W4 한글비율이 갈린다"] = bool(f_hangul("가나다라") == 1.0 and f_hangul("abcd") == 0.0)

    e = {"ord": np.arange(1000, 1000 + 400, dtype=np.int64),
         "views": np.arange(400, dtype=np.int64)}
    ok_w = f_window(e, 1200)
    W["W5 창이 90+91 로 잘린다"] = bool(ok_w is not None and len(ok_w[0]) == S_DAYS
                                and len(ok_w[1]) == O_DAYS and ok_w[1][0] == 200)
    gap = {"ord": np.concatenate([np.arange(1000, 1150), np.arange(1151, 1400)]).astype(np.int64),
           "views": np.arange(399, dtype=np.int64)}
    W["W6 구멍 난 계열은 창을 안 낸다"] = bool(f_window(gap, 1200) is None)

    idx = collections.defaultdict(list)
    idx["오징어"].append((("게임",), "오징어 게임", "TEST-1"))
    idx["원펀맨"].append(((), "원펀맨", "TEST-2"))
    got = f_ment("어제 오징어 게임을 봤다. 원펀맨도 봤다.", idx)
    W["W7 언급이 잡힌다(조사 포함)"] = bool({k for _, k in got} == {"TEST-1", "TEST-2"})
    W["W8 없는 것은 안 잡힌다"] = bool(f_ment("아무 상관 없는 문장이다", idx) == set())
    W["W9 954 URL 정규화를 태운다"] = bool(
        f_norm_url("https://WWW.Example.com/a/?q=1#x") == "example.com/a")
    W["W10 954 도박 자를 태운다"] = bool(
        f_gamble("바카라 사이트".encode("utf-8")) is not None
        and f_gamble("보통 문장".encode("utf-8")) is None)
    a = SCRATCH / "_wire_a.txt"
    b = SCRATCH / "_wire_b.txt"
    a.write_text("가", encoding="utf-8")
    b.write_text("나", encoding="utf-8")
    W["W11 971 의 sha 생산 함수를 태운다"] = bool(
        f_sha(a) != f_sha(b) and len(f_sha(a)) == 64)
    W["W12 원천 태그 상수가 hplt_ko 다"] = bool(SRC_TAG == "hplt_ko")
    return W


def stage_wiring(ref: str) -> dict:
    t0 = time.time()
    cs0 = code_stamp()
    base = _wiring_checks()
    muts = ["norm_title", "strip_josa", "title_ok", "hangul_ratio", "window",
            "mentions", "norm_url", "GAMBLE_PAT", "_sha_file"]
    dest = collections.OrderedDict()
    for m in muts:
        W = _wiring_checks(m)
        red = [k for k in W if not W[k]]
        dest[m] = {"붉어진 검사": red, "수": len(red), "🔴 하나라도 붉나": bool(red)}
    cs1 = code_stamp()
    n_ok = sum(1 for v in base.values() if v)
    return {
        "무엇": "973 배선 --- 생산 함수를 태운다 + 파괴 대조",
        "🔴 축": "C3", "언제(끝)": _now(), "초": round(time.time() - t0, 1),
        "🔴 배선": base,
        "🔴 분자/분모": "%d / %d" % (n_ok, len(base)),
        "🔴 파괴 대조": dest,
        "🔴 파괴 대조 분자/분모": "%d / %d" % (
            sum(1 for v in dest.values() if v["🔴 하나라도 붉나"]), len(dest)),
        "🔴 도장": {"시작 code_stamp 요약": P.stamp_digest(cs0),
                 "끝 code_stamp 요약": P.stamp_digest(cs1),
                 "🔴 시작=끝": bool(P.stamp_digest(cs0) == P.stamp_digest(cs1)),
                 "분모: 도장이 덮는 파일": len(cs1),
                 "🔴 F1 --- 돌린 러너 sha vs 커밋 blob": ran_vs_blob(ref)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["build", "census", "wiring"])
    ap.add_argument("--ref", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--new-path", default="")
    ap.add_argument("--shards", default="")
    ap.add_argument("--row-cap", type=int, default=ROW_CAP)
    a = ap.parse_args()
    if a.stage == "build":
        sh = tuple(int(x) for x in a.shards.split(",")) if a.shards else SHARD_IDX
        r = stage_build(a.ref, shard_idx=sh, row_cap=a.row_cap)
    elif a.stage == "census":
        r = stage_census(a.ref, new_path=(a.new_path or None))
    else:
        r = stage_wiring(a.ref)
    dst = Path(a.out) if a.out else (SCRATCH / ("out973_%s.json" % a.stage))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(str(dst))


if __name__ == "__main__":
    main()
