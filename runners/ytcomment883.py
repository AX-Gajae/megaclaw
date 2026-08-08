# -*- coding: utf-8 -*-
# 노트 883 절 C — 키리스 댓글 시각 노크(사전등록 '883' · T3 문면 근거 검증)
# 정상 공개 경로만: 워치 페이지 → ytcfg 의 공개 INNERTUBE 키 + ytInitialData 의 댓글 연속 토큰
#              → youtubei/v1/next 1회. 표본 3편 · 예의 1.5초.
# 🔴 경계(사전등록): 차단이면 거기서 멈춘다 — 프록시 회전·CAPTCHA 우회·탐지 회피 없음.
import datetime as dt
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
from ingest.social import UA, SLEEP, yt_rss  # noqa: E402

ROOT = Path("/Users/ax/world_model")
NEXT = "https://www.youtube.com/youtubei/v1/next?key={}"


def get(url):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "ignore")


def post(url, payload):
    body = json.dumps(payload).encode()
    h = dict(UA); h["Content-Type"] = "application/json"
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(url, data=body, headers=h), timeout=60).read().decode("utf-8", "ignore"))


def knock(vid):
    """한 영상 → 댓글 시각 목록(정상 경로) · 실패 사유를 값으로."""
    out = {"id": vid}
    try:
        h = get(f"https://www.youtube.com/watch?v={vid}")
    except Exception as e:
        out["단계"] = "워치 페이지"; out["⛔"] = type(e).__name__; return out
    key = re.search(r'"INNERTUBE_API_KEY":"([\w-]+)"', h)
    ver = re.search(r'"INNERTUBE_CLIENT_VERSION":"([\d.]+)"', h)
    if not key:
        out["단계"] = "ytcfg 키"; out["⛔"] = "INNERTUBE_API_KEY 부재"; return out
    # 댓글 섹션 연속 토큰 — itemSectionRenderer 안의 continuation
    toks = re.findall(r'"continuationCommand":\{"token":"([^"]{40,})"', h)
    if not toks:
        out["단계"] = "연속 토큰"; out["⛔"] = "토큰 부재(댓글 꺼짐 가능)"; return out
    out["토큰 후보"] = len(toks)
    ctx = {"context": {"client": {"clientName": "WEB",
                                 "clientVersion": ver.group(1) if ver else "2.20240101.00.00",
                                 "hl": "ko", "gl": "KR"}}}
    for i, tk in enumerate(toks[:6]):          # 댓글 섹션 토큰이 몇 번째인지 모른다 — 앞쪽만 시도
        time.sleep(SLEEP)
        try:
            j = post(NEXT.format(key.group(1)), {**ctx, "continuation": tk})
        except Exception as e:
            out["단계"] = f"next({i})"; out["⛔"] = type(e).__name__; continue
        # 🔴 wfail1 교훈(구현 의심 먼저 8차): 최신 유튜브는 댓글을 publishedTimeText 가
        # 아니라 frameworkUpdates.entityBatchUpdate 의 commentEntityPayload 로 준다.
        muts = (j.get("frameworkUpdates", {}).get("entityBatchUpdate", {}).get("mutations", []))
        ce = [m["payload"]["commentEntityPayload"] for m in muts
              if "commentEntityPayload" in (m.get("payload") or {})]
        rows = [{"시각(상대)": c.get("properties", {}).get("publishedTime"),
                 "작성자": (c.get("author") or {}).get("displayName"),
                 "좋아요": (c.get("toolbar") or {}).get("likeCountNotliked"),
                 "답글수": (c.get("toolbar") or {}).get("replyCount")}
                for c in ce if c.get("properties", {}).get("publishedTime")]
        if rows:
            out["성공 토큰 index"] = i
            out["댓글 시각 건수"] = len(rows)
            out["댓글 표본"] = rows[:12]
            out["mutations"] = len(muts)
            return out
        out.setdefault("빈 응답 index", []).append(i)
    out.setdefault("⛔", "댓글 시각 0건")
    return out


def main():
    # 표본 3편 — 폴링 대상 채널의 RSS 최신에서(우리 자료와 같은 우주)
    tg = json.loads((ROOT / "data/ingest/yt_poll_targets.json").read_text())
    vids = []
    for t in tg[:3]:
        time.sleep(SLEEP)
        try:
            r = yt_rss(t["channel_id"])
            if r:
                vids.append({"채널": t["name"], "id": r[0]["id"], "게시": r[0]["게시"]})
        except Exception as e:
            vids.append({"채널": t["name"], "⛔": type(e).__name__})
    res = [knock(v["id"]) if v.get("id") else v for v in vids]
    ok = sum(r.get("댓글 시각 건수", 0) for r in res)
    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "눈금": "댓글 published 시각 ≥10건 파싱 = 성공(사전등록 883 C)",
        "시각 입도(한계 명기)": "commentEntityPayload.publishedTime 은 **상대 표현**('1일 전')이라 스냅샷 날짜와 합쳐 절대화한다 — 최근 창은 일 단위, 오래된 댓글은 연 단위로 거칠다. 전향 폴링과 결합할 때만 일 단위 유입률이 정확하다",
        "경계": "정상 공개 경로만 — 프록시/우회/회피 없음. 차단이면 멈춘다",
        "표본": vids, "결과": res, "총 파싱 건수": ok,
        "판정": "성공 — 키리스 댓글 시각 파싱됨(T3 '막혔다' 문면 반증)" if ok >= 10
                else "실패 — 키리스로 안 열림(T3 문면을 측정으로 확정)",
    }
    with open(ROOT / "runners/out883_ytcomment.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "결과"}, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1)[:1200], flush=True)


if __name__ == "__main__":
    main()
