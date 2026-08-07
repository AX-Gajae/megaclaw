# 노트 836 — 축 수집(코드 매핑 → 상세 4필드) · 사전등록 835 수정판의 선고정 규칙
# 예산: 고유 날짜 614 + 상세 ≤897 ≈ 1,511 요청 × 1.5초 ≈ 38분 · 증분 저장 · 재시도 0
import datetime as dt
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
sys.path.insert(0, "/Users/ax/world_model")
from ingest.kobis import UA, URL, SLEEP, movie_detail

t0 = time.time()
FR = json.load(open("/Users/ax/world_model/data/ingest/kobis/threshold897_frozen.json"))
OUT_P = Path("/Users/ax/world_model/data/ingest/kobis/axes_raw_897.jsonl")
done_keys = set()
if OUT_P.exists():
    for line in OUT_P.open():
        try:
            r = json.loads(line)
            done_keys.add((r["제목"], r["개봉일"]))
        except Exception:
            pass
print(f"이미 수집 {len(done_keys)}", flush=True)

# 날짜 → 그 날짜가 첫 관측일인 영화들
by_date = {}
for m in FR["명단"]:
    if (m["제목"], m["개봉일"]) in done_keys:
        continue
    by_date.setdefault(m["첫 관측일"], []).append(m)

def daily_codes(date):
    data = urllib.parse.urlencode({
        "loadEnd": "0", "searchType": "search",
        "sSearchFrom": date, "sSearchTo": date,
        "sMultiMovieYn": "", "sRepNationCd": "", "sWideAreaCd": ""}).encode()
    req = urllib.request.Request(URL, data=data,
        headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    out = {}
    for tr in re.split(r"<tr[^>]*>", body)[1:]:
        mc = re.search(r"mstView\('movie','(\d+)'\)", tr)
        mt = None
        for cand in re.finditer(r'title="([^"]{1,80})"', tr):
            if not re.fullmatch(r"[\d,.]+", cand.group(1).strip()):
                mt = cand.group(1)
                break
        md = re.search(r"(20\d{2}-\d{2}-\d{2})", tr)
        if mc and mt:
            out[(mt, md.group(1) if md else None)] = mc.group(1)
    return out

n_req = 0
with OUT_P.open("a") as fout:
    for date in sorted(by_date):
        try:
            codes = daily_codes(date)
        except Exception as e:
            print(f"⛔ {date}: {type(e).__name__}", flush=True)
            time.sleep(SLEEP)
            continue
        n_req += 1
        time.sleep(SLEEP)
        for m in by_date[date]:
            key = (m["제목"], m["개봉일"])
            code = codes.get(key) or codes.get((m["제목"], None))
            row = dict(m)
            if not code:
                row["⛔"] = "코드 미매핑"
            else:
                try:
                    row.update(movie_detail(code))
                    n_req += 1
                except Exception as e:
                    row["⛔"] = f"상세 실패 {type(e).__name__}"
                time.sleep(SLEEP)
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            fout.flush()
        if n_req % 100 < 3:
            print(f"  요청 {n_req} · {time.time()-t0:.0f}s", flush=True)
print(f"완료 — 요청 {n_req} · {time.time()-t0:.0f}s", flush=True)
