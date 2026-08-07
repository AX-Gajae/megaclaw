# 노트 829 — 유튜브 대상 초안(절 A: 데뷔 완료 23팀 · 기계 검증 포함)
import json, re, sys, time
sys.path.insert(0, "/Users/ax/world_model")
from ingest.social import _get, yt_rss, SLEEP
import urllib.parse

teams = []
for l in open("/Users/ax/world_model/ingest/idol_2026_predebut_signals.jsonl"):
    r = json.loads(l)
    teams.append({"name": r["group_name"], "debut": r.get("debut_date"),
                  "notes": (r.get("notes") or "")[:40]})
out = []
for t in teams:
    q = f"{t['name']} 아이돌 official"
    row = dict(t)
    try:
        h = _get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q))
        m = re.search(r'"channelId":"(UC[\w-]{22})"', h)
        cid = m.group(1) if m else None
        row["channel_id"] = cid
        if cid:
            time.sleep(SLEEP)
            try:
                feed = yt_rss(cid)
                row["rss_check"] = {"영상 수(RSS)": len(feed),
                    "최근": (feed[0].get("published") if feed else None),
                    "채널명": (feed[0].get("author") if feed and feed[0].get("author") else None)}
                row["확신"] = "높음" if feed else "중간(RSS 빈 채널)"
            except Exception as e:
                row["rss_check"] = {"⛔": type(e).__name__}
                row["확신"] = "낮음"
        else:
            row["확신"] = "낮음(채널 미발견)"
    except Exception as e:
        row["⛔"] = type(e).__name__
        row["확신"] = "낮음"
    row["절"] = "A(데뷔후곡선)"
    out.append(row)
    print(f"{t['name']}: {row.get('channel_id')} · {row.get('확신')}", flush=True)
    time.sleep(SLEEP)
json.dump(out, open("/Users/ax/world_model/data/ingest/yt_poll_targets_draft.json", "w"),
          ensure_ascii=False, indent=1)
ok = sum(1 for r in out if r.get("확신") == "높음")
print(f"완료 — 확신 높음 {ok}/{len(out)}", flush=True)
