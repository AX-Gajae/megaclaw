#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""954 --- HPLT 2.0 `kor_Hang` **464 shard 전량** 한 번 훑기.

왜 전량인가(원장 997): 어제까지의 모든 품질 수치는 앞 4 shard = `cc22` 한 크롤의
보름치에서 나왔다. shard 가 collection 별 큰 연속 덩어리로 놓여 있어서
**앞에서 자른 표본은 원천의 성질을 말할 수 없다**(조항 60).

이 러너가 문서마다 내는 것(자는 `docs/prereg_954_dupe.md` §3 에 측정 전에 박았다):
    url_h      --- URL 문자열 그대로의 md5 앞 8바이트
    urlnorm_h  --- 정규화 URL 의 md5 앞 8바이트   ← 🔴 이것이 「중복」의 정본 자
    head_h     --- 본문 strip 후 앞 200자의 md5 앞 8바이트
    text_h     --- 본문 전문의 md5 앞 8바이트
    coll_id    --- collection 이름의 정수 부호

그리고 shard 마다 세는 것: collection · 도박 정규식 · 뉴스형 host · host 빈도 · ts 범위.

씀:
    python3 runners/dupe954_hplt_scan.py --workers 10      # 훑기(오래 걸린다)
    python3 runners/dupe954_hplt_scan.py --merge           # 취합 → runners/out954_hplt_full.json

🔴 조항 59: 종료코드가 아니라 **연 파일 수와 행 수**를 산출물에 적는다.
🔴 조항 60: 모든 비율에 분모를 같은 자리에 적는다.
"""
import argparse
import collections
import hashlib
import json
import os
import pathlib
import pickle
import re
import sys
import time

import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
SRC = pathlib.Path("data/ingest/hplt_ko")
SCRATCH = pathlib.Path("/Users/ax/wm_harvest/954/scan")   # 🔴 저장소 밖(100MB 벽 · 데몬)

# ---------------------------------------------------------------- 자(ruler)

# 🔴 도박 정규식 --- 내 자다. 어제 조사관의 정규식은 저장소에 없어서 못 쓴다.
#    그래서 **같은 정규식을 전량과 cc22 앞 4 shard 양쪽에 대서 내부적으로만 견준다**(P4).
GAMBLE_PAT = re.compile(
    "|".join([
        "바카라", "카지노", "토토사이트", "사설토토", "안전놀이터", "먹튀검증", "먹튀사이트",
        "슬롯머신", "온라인슬롯", "홀덤사이트", "바둑이게임", "사다리게임", "파워볼",
        "스포츠토토", "배팅사이트", "베팅사이트", "메이저놀이터", "먹튀폴리스",
    ]).encode("utf-8"))

# 뉴스·연예형 host --- 역시 내 자다(어제의 8.9% 는 남의 자다 · 직접 빼지 않는다)
NEWS_PAT = re.compile(
    r"(?:^|\.)(?:news|newsis|yna|yonhapnews|chosun|donga|joins|joongang|hani|khan|"
    r"mk|mt|edaily|etnews|inews24|nocutnews|ohmynews|pressian|seoul|segye|kmib|kukinews|"
    r"hankookilbo|hankyung|sedaily|fnnews|asiae|ajunews|newdaily|dailian|breaknews|"
    r"osen|dispatch|xportsnews|tvreport|starnews|isplus|sportsseoul|sportschosun|"
    r"sportsq|mydaily|newsen|tenasia|wowtv|heraldcorp|imbc|sbs|kbs|jtbc|ytn|mbn|tvchosun)"
    r"(?:\.|$)|news")


def norm_url(u):
    """🔴 사전등록 §3 자 ② --- 글자 그대로 옮긴다."""
    i = u.find("://")
    if i >= 0:
        u = u[i + 3:]
    for cut in ("?", "#"):
        j = u.find(cut)
        if j >= 0:
            u = u[:j]
    j = u.find("/")
    if j < 0:
        host, path = u, ""
    else:
        host, path = u[:j], u[j:]
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    k = host.rfind(":")
    if k > 0 and host[k + 1:].isdigit():
        host = host[:k]
    path = path.rstrip("/")
    return host + (path if path else "/")


def host_of(u):
    i = u.find("://")
    if i >= 0:
        u = u[i + 3:]
    j = u.find("/")
    if j >= 0:
        u = u[:j]
    u = u.split("?")[0].lower()
    if u.startswith("www."):
        u = u[4:]
    k = u.rfind(":")
    if k > 0 and u[k + 1:].isdigit():
        u = u[:k]
    return u


def h64(b):
    return int.from_bytes(hashlib.md5(b).digest()[:8], "little")


def head200(b):
    """text.strip()[:200] --- ⚠ 바이트 strip 후 앞 200자다(200자 ≤ 800바이트).
    유니코드 전용 공백(\\u3000 등)에서 str.strip 과 어긋날 수 있다. **양쪽 자료에
    같은 함수를 쓴다** --- 견주는 것은 두 코퍼스이지 이 함수의 절대값이 아니다."""
    s = b.strip()
    return s[:800].decode("utf-8", "ignore")[:200]


# ---------------------------------------------------------------- 한 shard

def scan_shard(path, sid):
    t0 = time.time()
    pf = pq.ParquetFile(path)
    n = pf.metadata.num_rows
    url_h = np.empty(n, dtype=np.uint64)
    urn_h = np.empty(n, dtype=np.uint64)
    hed_h = np.empty(n, dtype=np.uint64)
    txt_h = np.empty(n, dtype=np.uint64)
    coll_ix = np.empty(n, dtype=np.int32)
    colls = {}
    coll_names = []
    hosts = collections.Counter()
    gamble = 0
    newsish = 0
    empty_text = 0
    tsmin = None
    tsmax = None
    i = 0
    for batch in pf.iter_batches(batch_size=4096,
                                 columns=["u", "text", "collection", "ts"]):
        urls = batch.column("u").to_pylist()
        texts = pc.cast(batch.column("text"), "binary").to_pylist()
        cols = batch.column("collection").to_pylist()
        ts = batch.column("ts").to_pylist()
        for u, t, c, tv in zip(urls, texts, cols, ts):
            u = u or ""
            t = t or b""
            url_h[i] = h64(u.encode("utf-8"))
            urn_h[i] = h64(norm_url(u).encode("utf-8"))
            hed_h[i] = h64(head200(t).encode("utf-8"))
            txt_h[i] = h64(t)
            ci = colls.get(c)
            if ci is None:
                ci = colls[c] = len(coll_names)
                coll_names.append(c)
            coll_ix[i] = ci
            hh = host_of(u)
            hosts[hh] += 1
            if GAMBLE_PAT.search(t):
                gamble += 1
            if NEWS_PAT.search(hh):
                newsish += 1
            if not t:
                empty_text += 1
            if tv is not None:
                if tsmin is None or tv < tsmin:
                    tsmin = tv
                if tsmax is None or tv > tsmax:
                    tsmax = tv
            i += 1
    assert i == n, (i, n)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    np.savez(SCRATCH / ("s%03d.npz" % sid), url_h=url_h, urn_h=urn_h,
             hed_h=hed_h, txt_h=txt_h, coll_ix=coll_ix,
             coll_names=np.array(coll_names, dtype=object))
    rec = {
        "shard": sid, "행": int(n), "collection별": {coll_names[k]: int((coll_ix == k).sum())
                                                     for k in range(len(coll_names))},
        "도박": int(gamble), "뉴스형host": int(newsish), "빈본문": int(empty_text),
        "ts최소": str(tsmin), "ts최대": str(tsmax), "초": round(time.time() - t0, 1),
    }
    with (SCRATCH / ("s%03d.json" % sid)).open("w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)
    with (SCRATCH / ("h%03d.pkl" % sid)).open("wb") as f:
        pickle.dump(dict(hosts), f, protocol=4)
    return rec


def worker(args):
    path, sid = args
    try:
        return scan_shard(path, sid)
    except Exception as e:  # 🔴 실패를 성공으로 읽지 않는다(조항 59)
        return {"shard": sid, "실패": repr(e)[:300]}


def run(workers, limit):
    files = sorted(SRC.glob("train-*-of-00464.parquet"))
    jobs = []
    for p in files:
        sid = int(p.name.split("-")[1])
        if (SCRATCH / ("s%03d.npz" % sid)).exists() and \
           (SCRATCH / ("h%03d.pkl" % sid)).exists():
            continue
        jobs.append((p, sid))
    if limit:
        jobs = jobs[:limit]
    print("대상 shard %d (전체 %d · 이미 있음 %d)" % (len(jobs), len(files), len(files) - len(jobs)),
          flush=True)
    t0 = time.time()
    if workers <= 1:
        for k, j in enumerate(jobs):
            r = worker(j)
            print("%d/%d %s" % (k + 1, len(jobs), r.get("초", r.get("실패"))), flush=True)
    else:
        import multiprocessing as mp
        with mp.Pool(workers) as pool:
            for k, r in enumerate(pool.imap_unordered(worker, jobs, chunksize=1)):
                if k % 10 == 0 or "실패" in r:
                    el = time.time() - t0
                    print("%d/%d · %.0fs · 남은 추정 %.0fs · %s"
                          % (k + 1, len(jobs), el,
                             el / max(k + 1, 1) * (len(jobs) - k - 1),
                             r.get("실패", "")), flush=True)
    print("끝 %.1fs" % (time.time() - t0), flush=True)


# ---------------------------------------------------------------- 취합

def merge():
    t0 = time.time()
    files = sorted(SRC.glob("train-*-of-00464.parquet"))
    sids = [int(p.name.split("-")[1]) for p in files]
    recs, missing = [], []
    for sid in sids:
        p = SCRATCH / ("s%03d.json" % sid)
        if not p.exists():
            missing.append(sid)
            continue
        recs.append(json.loads(p.read_text(encoding="utf-8")))
    N = sum(r["행"] for r in recs)

    coll_tot = collections.Counter()
    for r in recs:
        for k, v in r["collection별"].items():
            coll_tot[k] += v
    gam = sum(r["도박"] for r in recs)
    news = sum(r["뉴스형host"] for r in recs)
    cc22 = [r for r in recs if r["shard"] < 4]
    N4 = sum(r["행"] for r in cc22)

    # host 빈도 취합
    hosts = collections.Counter()
    for sid in [r["shard"] for r in recs]:
        with (SCRATCH / ("h%03d.pkl" % sid)).open("rb") as f:
            hosts.update(pickle.load(f))
    top = hosts.most_common(60)
    kin_rank = None
    for rank, (h, c) in enumerate(hosts.most_common(), 1):
        if h == "kin.naver.com":
            kin_rank = (rank, c)
            break

    # 해시 배열 취합 --- 정확중복 · 교차 collection
    txt = np.empty(N, dtype=np.uint64)
    urn = np.empty(N, dtype=np.uint64)
    hed = np.empty(N, dtype=np.uint64)
    cid = np.empty(N, dtype=np.int16)
    cmap, cnames = {}, []
    off = 0
    for r in recs:
        sid = r["shard"]
        z = np.load(SCRATCH / ("s%03d.npz" % sid), allow_pickle=True)
        n = len(z["txt_h"])
        txt[off:off + n] = z["txt_h"]
        urn[off:off + n] = z["urn_h"]
        hed[off:off + n] = z["hed_h"]
        names = list(z["coll_names"])
        loc = z["coll_ix"]
        remap = np.empty(len(names), dtype=np.int16)
        for k, nm in enumerate(names):
            if nm not in cmap:
                cmap[nm] = len(cnames)
                cnames.append(nm)
            remap[k] = cmap[nm]
        cid[off:off + n] = remap[loc]
        off += n
    assert off == N, (off, N)

    def dup_stats(arr, label, with_cross=True):
        order = np.argsort(arr, kind="stable")
        a = arr[order]
        newgrp = np.empty(len(a), dtype=bool)
        newgrp[0] = True
        np.not_equal(a[1:], a[:-1], out=newgrp[1:])
        gstart = np.flatnonzero(newgrp)
        gsize = np.diff(np.append(gstart, len(a)))
        multi = gsize > 1
        n_groups = int(multi.sum())
        docs_in = int(gsize[multi].sum())
        excess = docs_in - n_groups
        out = {
            "자": label,
            "🔴 분모(문서 전량)": int(len(a)),
            "군(크기>1) 수": n_groups,
            "군에 속한 문서 수": docs_in,
            "군에 속한 문서 비율": round(docs_in / len(a), 6),
            "초과분(=문서-군)": excess,
            "초과분 비율": round(excess / len(a), 6),
            "⚠ 두 정의는 다르다": "「군에 속한 문서」와 「초과분」을 이어 붙이지 마라(원장 998)",
            # 🔴 판정 키 규약(⑤′ 절 3) --- 이 절의 `통과` 는 **자기 일관성**이다:
            #    군에 속한 문서 ≥ 군 수 이고, 두 수가 분모를 안 넘는가.
            "통과": bool(docs_in >= n_groups and docs_in <= len(a)),
        }
        if with_cross:
            c = cid[order]
            cross_g = cross_docs = 0
            idx = gstart[multi]
            sz = gsize[multi]
            for s, l in zip(idx, sz):
                seg = c[s:s + l]
                if seg[0] != seg[-1] or np.any(seg != seg[0]):
                    cross_g += 1
                    cross_docs += int(l)
            out["🔴 교차 collection 군 수"] = int(cross_g)
            out["🔴 교차 collection 군의 문서 수"] = int(cross_docs)
            out["🔴 교차 collection 문서 비율"] = round(cross_docs / len(a), 6)
            out["통과"] = bool(out["통과"] and cross_docs <= docs_in and cross_g <= n_groups)
        return out

    res = {
        "무엇": "HPLT 2.0 kor_Hang 464 shard 전량 훑기",
        "언제(시작)": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
        "🔴 규약 60 --- 명령·범위·트리": {
            "명령": "python3 runners/dupe954_hplt_scan.py --workers N ; --merge",
            "범위": "data/ingest/hplt_ko/train-*-of-00464.parquet (git 비추적 · .gitignore:33)",
            "트리": "작업 트리 디스크 파일",
            "통과": True,          # 세 칸이 다 차 있다
        },
        "🔴 분모 --- 연 shard": len(recs),
        "🔴 분모 --- 못 연 shard": missing,
        "🔴 분모 --- 문서 전량": int(N),
        # 🔴 자료 지도는 절 안에 넣고 절에 `통과`(합 == 분모)를 단다 --- ⑤′ 절 3
        "collection별": {
            "수": dict(coll_tot.most_common()),
            "🔴 합": int(sum(coll_tot.values())),
            "🔴 분모(문서 전량)": int(N),
            "통과": bool(sum(coll_tot.values()) == N),
        },
        "collection 수": len(coll_tot),
        "🔴 최대 collection 비율": round(max(coll_tot.values()) / N, 6),
        "도박(내 자)": {
            "전량 적중": int(gam), "🔴 분모": int(N), "비율": round(gam / N, 6),
            "cc22 앞 4 shard 적중": int(sum(r["도박"] for r in cc22)),
            "🔴 cc22 분모": int(N4),
            "cc22 비율": round(sum(r["도박"] for r in cc22) / N4, 6),
            "⚠": "어제의 3.869%/3.818% 와 직접 빼지 마라 --- 정규식이 다르다(조항 60)",
            "통과": bool(gam <= N and sum(r["도박"] for r in cc22) <= N4),
        },
        "뉴스형 host(내 자)": {
            "전량 적중": int(news), "🔴 분모": int(N), "비율": round(news / N, 6),
            "cc22 적중": int(sum(r["뉴스형host"] for r in cc22)),
            "🔴 cc22 분모": int(N4),
            "cc22 비율": round(sum(r["뉴스형host"] for r in cc22) / N4, 6),
            "통과": bool(news <= N and sum(r["뉴스형host"] for r in cc22) <= N4),
        },
        "host 상위 60": [{"host": h, "문서": c, "비율": round(c / N, 6)} for h, c in top],
        "🔴 kin.naver.com 순위": ({"순위": kin_rank[0], "문서": kin_rank[1],
                                   "비율": round(kin_rank[1] / N, 6),
                                   "통과": True}      # 찾았다
                                  if kin_rank else {"🔴": "없다 --- 「못 찾았다」가 아니라 "
                                                          "전량 host 목록에 없다",
                                                    "통과": False}),
        "서로 다른 host 수": len(hosts),
        "정확중복 --- 전문": dup_stats(txt, "전문 md5 앞 8바이트"),
        "정확중복 --- 정규화 URL": dup_stats(urn, "정규화 URL md5 앞 8바이트"),
        "앞머리 공유 --- 앞 200자": dup_stats(hed, "본문 앞 200자 md5 앞 8바이트"),
        "⚠ 64비트 해시 충돌 기대치": round(N * N / 2 / 2 ** 64, 8),
        "빈 본문": sum(r["빈본문"] for r in recs),
        "ts 최소": min(r["ts최소"] for r in recs if r["ts최소"] != "None"),
        "ts 최대": max(r["ts최대"] for r in recs if r["ts최대"] != "None"),
        "코드 sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "끝(UTC)": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "취합 초": round(time.time() - t0, 1),
        "통과": len(missing) == 0,
    }
    out = REPO / "runners" / "out954_hplt_full.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items()
                      if k in ("🔴 분모 --- 연 shard", "🔴 분모 --- 문서 전량",
                               "collection 수", "통과")}, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    os.chdir(REPO)
    if a.merge:
        return merge()
    run(a.workers, a.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
