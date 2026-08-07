# 노트 834(부) — 유튜브 초안 신원 검증판 (티처 #6 마감 · 성공 기준: 채널명 파싱 ≥20/23)
import json, re, sys, time, urllib.parse
sys.path.insert(0, "/Users/ax/world_model")
from ingest.social import _get, SLEEP

def norm(s):
    return re.sub(r"[^0-9a-z가-힣]", "", str(s or "").lower())

draft = json.load(open("/Users/ax/world_model/data/ingest/yt_poll_targets_draft.json"))
ok_name = 0
for row in draft:
    cid = row.get("channel_id")
    if not cid:
        row["신원"] = "채널 미발견"
        continue
    try:
        h = _get("https://www.youtube.com/feeds/videos.xml?channel_id=" + cid)
        head = h.split("<entry>")[0]
        m = re.search(r"<title>([^<]+)</title>", head)
        cname = m.group(1).strip() if m else None
        pubs = re.findall(r"<published>([^<]+)</published>", h)
        latest = max(pubs) if pubs else None
        row["채널명"] = cname
        row["최근 게시"] = latest[:10] if latest else None
        gn, cn = norm(row["name"]), norm(cname)
        match = bool(cn) and (gn in cn or cn in gn or
                              len(set(gn) & set(cn)) / max(len(set(gn)), 1) > 0.6)
        row["신원"] = "일치" if match else "**불일치 의심 — 사람 확인 필수**"
        ok_name += bool(cname)
    except Exception as e:
        row["신원"] = f"⛔ {type(e).__name__}"
    time.sleep(SLEEP)
    print(f"{row['name']}: 채널명={row.get('채널명')} · 최근={row.get('최근 게시')} · {row['신원']}", flush=True)
json.dump(draft, open("/Users/ax/world_model/data/ingest/yt_poll_targets_draft.json", "w"),
          ensure_ascii=False, indent=1)
mism = sum(1 for r in draft if "불일치" in str(r.get("신원")))
print(f"완료 — 채널명 파싱 {ok_name}/23 · 불일치 의심 {mism}", flush=True)
