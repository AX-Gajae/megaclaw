# -*- coding: utf-8 -*-
"""1037 A부 «신판» — 403 차단 수리 + 크롤 층화 순서.

구판 runners/warc1037_fetch.py (sha 0f8a04bf66959d65) 가 낸 것:
  실제로 받아본 문서 2,092 — 전부 ㉣2022-40 한 덩이. 나머지 17,997 은 HTTP 403.
  ⓐ 동시 12 가 data.commoncrawl.org 의 속도 제한을 때렸고
  ⓑ 구판이 403 을 «영구 실패»로 보고 즉시 포기했다(재시도 안 함) —
     403 은 「없다」가 아니라 「못 봤다」다(조항 59).
  ⓒ 좌표 파일 순서대로 돌아 한 크롤에 몰렸다(조항 60 위반).

신판이 고치는 것 — 자는 안 건드린다(발행일 사슬·온전성·충돌 규칙 전부 구판 그대로 import):
  ① 동시 3 · 요청 간 간격
  ② 403 = 속도 제한 → «전역 냉각»(모든 실 정지) 후 재시도 (60·180·420·900초)
  ③ 크롤 덩이 라운드로빈 + D3 실험문서 우선 — 잘려도 다섯 덩이 다 덮인다
"""
import json, gzip, time, threading, collections, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request, urllib.error

sys.path.insert(0, "/Users/ax/world_model/runners")
import warc1037_fetch as F          # 자(발행일 사슬)는 구판에서 그대로 물려쓴다

OUT = Path("/Users/ax/wm_harvest/foundation/warc1037")
TF = Path("/Users/ax/wm_harvest/foundation/textfix1036")
CONC = 3
GAP = 0.35
COOL = [60, 180, 420, 900]
_lock = threading.Lock()
_cool = threading.Event(); _cool.set()          # set = 통행 가능
_cool_lv = [0]
_stat = collections.Counter()


def cooldown():
    with _lock:
        if not _cool.is_set():
            return
        lv = min(_cool_lv[0], len(COOL) - 1)
        secs = COOL[lv]
        _cool_lv[0] += 1
        _cool.clear()
        _stat[f"냉각{secs}s"] += 1
        print(f"  🔴 403 — 전역 냉각 {secs}s (누적 {_cool_lv[0]})", flush=True)
    time.sleep(secs)
    _cool.set()


def one(rec, idx, out):
    fname = rec["f"].split("/")[-1]
    path = idx.get(fname)
    if not path:
        return {"문서id": rec["문서id"], "단계": "S2", "실패": "경로없음"}
    url = F.BASE + path
    o, s = int(rec["o"]), int(rec["s"])
    hdr = {"Range": f"bytes={o}-{o+s-1}", "User-Agent": F.UA, "Accept-Encoding": "identity"}
    raw = None; last = None
    for att in range(6):
        _cool.wait()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=90) as r:
                if r.status != 206:
                    last = f"HTTP{r.status}"; time.sleep(2 ** att); continue
                raw = r.read()
            if len(raw) != s:
                last = f"바이트불일치({len(raw)}≠{s})"; raw = None; time.sleep(2 ** att); continue
            with _lock:
                _cool_lv[0] = max(0, _cool_lv[0] - 1)     # 성공하면 냉각 단계 되돌린다
            break
        except urllib.error.HTTPError as e:
            last = f"HTTP{e.code}"
            _stat[last] += 1
            if e.code == 403:
                cooldown(); continue
            if e.code in (404, 416):
                return {"문서id": rec["문서id"], "단계": "S3", "실패": last, "재시도": att}
            time.sleep(2 ** att)
        except Exception as e:
            last = type(e).__name__; _stat[last] += 1; time.sleep(2 ** att)
    if raw is None:
        return {"문서id": rec["문서id"], "단계": "S3", "실패": last or "재시도소진", "재시도": 6}
    try:
        buf = gzip.decompress(raw)
    except Exception as e:
        return {"문서id": rec["문서id"], "단계": "S4", "실패": f"gunzip:{type(e).__name__}"}
    if len(buf) < int(rec["rs"]) * 0.3:
        return {"문서id": rec["문서id"], "단계": "S4", "실패": f"작음({len(buf)}<{rec['rs']})"}
    try:
        wtype, body, hh = F.parse_warc(buf)
    except Exception as e:
        return {"문서id": rec["문서id"], "단계": "S5", "실패": f"warc:{e}"}
    if wtype != "response":
        return {"문서id": rec["문서id"], "단계": "S5", "실패": f"타입:{wtype}"}
    if not body:
        return {"문서id": rec["문서id"], "단계": "S5", "실패": "본문0바이트"}
    html = F.decode(body)
    cands = F.candidates(html, rec["u"], rec["ts"])
    val, meth, conf, conflict = F.pick(cands)
    r = {"문서id": rec["문서id"], "단계": "S6" if val else "S6실패",
         "warc바이트": len(buf), "html글자": len(html),
         "링크수": html.count("<a href") + html.count("<A HREF"),
         "published_at": val, "method": meth, "confidence": conf, "충돌": conflict,
         "후보": {k: v[0] for k, v in cands.items()},
         "crawl_ts": rec["ts"], "u": rec["u"], "crawl덩이": rec.get("덩이")}
    if not val:
        r["실패"] = "날짜없음" if not cands else "날짜불온전"
    return r


def main():
    idx, _ = F.build_index()
    recs = {r["문서id"]: r for r in F.load_coords() if "CC-MAIN-" in r["f"]}
    rows = json.load(open(TF / "row_docid.json", encoding="utf-8"))
    d3 = set(r["문서id"] for r in rows)

    outp = OUT / "warc_pub.jsonl"
    done = set()
    keep = []
    if outp.exists():
        for line in open(outp, encoding="utf-8"):
            r = json.loads(line)
            # 「못 봤다」(403·503·끊김·재시도소진)는 «안 한 것»으로 되돌린다 — 조항 59
            if r["단계"] == "S3" and str(r.get("실패", "")).startswith(("HTTP403", "HTTP5", "Remote", "재시도")):
                continue
            keep.append(line); done.add(r["문서id"])
        with open(outp, "w", encoding="utf-8") as f:
            f.writelines(keep)
    print(f"보존 {len(done):,} · 되돌린 것 {23382-len(done):,}", flush=True)

    todo = [r for d, r in recs.items() if d not in done]
    # 크롤 덩이 라운드로빈 · D3 우선
    buck = collections.defaultdict(lambda: ([], []))
    for r in todo:
        buck[r["덩이"]][0 if r["문서id"] in d3 else 1].append(r)
    order = []
    for prio in (0, 1):
        ks = sorted(buck)
        i = 0
        while True:
            added = False
            for k in ks:
                lst = buck[k][prio]
                if i < len(lst):
                    order.append(lst[i]); added = True
            if not added:
                break
            i += 1
    print(f"할 것 {len(order):,} · 덩이 {dict(collections.Counter(r['덩이'] for r in order))}", flush=True)

    f = open(outp, "a", encoding="utf-8")
    t0 = time.time(); n = [0]; ok = [0]
    def work(r):
        time.sleep(GAP)
        res = one(r, idx, outp)
        with _lock:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            n[0] += 1
            if res.get("published_at"):
                ok[0] += 1
            if n[0] % 200 == 0:
                f.flush()
                el = time.time() - t0
                print(f"  {n[0]:,}/{len(order):,} · 발행일 {ok[0]:,} · {el:.0f}s · "
                      f"{n[0]/max(el,1):.1f}/s · {dict(_stat)}", flush=True)
    with ThreadPoolExecutor(max_workers=CONC) as ex:
        list(ex.map(work, order))
    f.close()
    print(f"끝 {n[0]:,} · 발행일 {ok[0]:,} · {time.time()-t0:.0f}s · {dict(_stat)}", flush=True)


if __name__ == "__main__":
    main()
