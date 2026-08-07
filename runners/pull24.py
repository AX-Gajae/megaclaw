"""24건 전수 판독 — 텍스트만 뽑는다(읽기 전용). 라벨은 쓰지 않는다."""
import json, urllib.request, urllib.error
from pathlib import Path
from ingest.doc_extract import DriveText

SP = Path('/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad')
OUT = SP / "txt24"; OUT.mkdir(exist_ok=True)
docs = json.load(open(SP / "reallogs.json"))
dt = DriveText()
tok = dt.token()

def meta(fid):
    u = f"https://www.googleapis.com/drive/v3/files/{fid}?fields=mimeType,size,name&supportsAllDrives=true"
    req = urllib.request.Request(u, headers={"Authorization": f"Bearer {tok}"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

rep = []
for n, (rid, title, fid) in enumerate(docs, 1):
    dst = OUT / f"{rid}__{fid}.txt"
    if dst.exists():
        rep.append((rid, title, "캐시", dst.stat().st_size)); continue
    try:
        m = meta(fid)
    except Exception as e:
        rep.append((rid, title, "메타실패:" + type(e).__name__, 0)); continue
    mime, size = m.get("mimeType", ""), int(m.get("size") or 0)
    txt, how = dt.text_of(mime, fid, size)
    dst.write_text(txt or "")
    rep.append((rid, title, how, len(txt or "")))
    print(f"{n:>3d}/{len(docs)} {rid} {how:>14s} {len(txt or ''):>8d}  {title[:50]}", flush=True)

json.dump(rep, open(SP / "pull24_report.json", "w"), ensure_ascii=False)
ok = sum(1 for r in rep if r[3] > 200)
print(f"\n텍스트 확보(200자 초과): {ok}/{len(rep)}")
