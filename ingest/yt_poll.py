"""유튜브 전향 폴링 --- 데뷔 리드타임의 관심 궤적을 **지금부터** 쌓는다 (T7).

**왜.** T7: "2026 하반기 데뷔 리드타임 --- 지금 걸어야 함". 티처 #1·#2 가 두
사이클 연속 "늦은 날수만큼 영구 소실"로 지적했다(노트 636 의 교훈과 같은 층:
앞으로만 쌓이는 것은 채굴보다 배선이 값이 크다).

**무엇을.** `data/ingest/yt_poll_targets.json` 의 대상(채널)마다:
    · RSS(키·쿼터 없음 · published 정확) 로 새 영상 목록
    · 각 영상의 읽은-시점 누적 조회수(`ingest.social.yt_meta`)
를 날짜 스탬프로 `data/ingest/youtube_poll/YYYY-MM-DD.json` 에 덧쓴다.
매일 한 번 돌면 영상별 조회수의 **일 단위 차분 곡선**이 자란다 --- wiki_after
와 같은 형태의 자료가 유튜브 채널에서 나온다.

**시간 게이트.** RSS 의 published 만 사전 정보다. 조회수는 읽은-시점 누적이라
상태 축이 아니라 **전향 라벨/곡선 재료**로만 쓴다(social.py 의 못과 동일).

**사람 게이트.** 대상 목록은 연구 결정이므로 사람이 채운다 --- 형식:
    [{"name": "표시명", "channel_id": "UC..."}, ...]
목록이 비어 있으면 아무것도 안 하고 그 사실만 적는다(빈 폴링은 소음).

돌리기:  python3 -m ingest.yt_poll        # 1회 스냅샷
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ROOT / "data/ingest/yt_poll_targets.json"
OUTDIR = ROOT / "data/ingest/youtube_poll"


def snapshot() -> dict:
    from ingest.social import yt_meta, yt_rss, SLEEP
    if not TARGETS.exists():
        return {"건너뜀": "대상 파일 없음", "경로": str(TARGETS)}
    targets = json.loads(TARGETS.read_text())
    if not targets:
        return {"건너뜀": "대상 목록 비어 있음(사람 게이트 대기)"}
    OUTDIR.mkdir(parents=True, exist_ok=True)
    today = _dt.date.today().isoformat()
    out = {"찍은 때": _dt.datetime.now().isoformat(timespec="seconds"), "대상": []}
    for t in targets:
        row = {"name": t.get("name"), "channel_id": t.get("channel_id"), "영상": []}
        try:
            vids = yt_rss(t["channel_id"])
        except Exception as e:
            row["⛔"] = f"RSS 실패: {type(e).__name__}"
            out["대상"].append(row)
            continue
        for v in vids:
            time.sleep(SLEEP)
            try:
                m = yt_meta(v.get("id") or v.get("videoId") or "")
            except Exception as e:
                m = {"id": v.get("id"), "⛔": type(e).__name__}
            # 🔴 노트 883 수리: yt_rss 는 키를 "게시"로 준다("published" 아님) —
            # 조용한 None 으로 **시간 게이트 필드가 전부 버려지고 있었다**(첫 스냅샷 실측).
            m["published(RSS)"] = v.get("게시") or v.get("published")
            row["영상"].append(m)
        out["대상"].append(row)
    # 🔴 노트 884 위생(티처 #48 M8): 자기서술 + 덮어쓰기 금지(같은 날 재실행은 이력 보존)
    import hashlib
    import subprocess
    out["시각(UTC)"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    out["git HEAD"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                     capture_output=True, text=True).stdout.strip()
    out["입력 지문"] = hashlib.sha256(
        json.dumps(targets, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
    # 🔴 노트 952 수리 --- **「하루 1점 설계」를 뗐다.**
    #
    # 사용자 지시(2026-08-12 축자): *「하루 한번만 수집한다거나 그런게 아니라
    # 모을 수 있는 모든 걸 모아」*.
    #
    # 옛 구조는 `YYYY-MM-DD.json` **한 파일을 덮어썼다.** 그래서 같은 날 몇 번을
    # 돌려도 **남는 점은 하루에 하나**였고, 조회수 차분 곡선의 해상도가 하루로
    # 고정돼 있었다(`collect.py` 가 아예 「건너뜀」으로 막고 있었다).
    # 🔴 **바깥 세계가 하루 한 번 변하는 것이 아니라 우리 파일 이름이 그랬다.**
    #
    # 이제 **회차마다 다른 파일**로 남긴다: `YYYY-MM-DDTHHMMSSZ.json`.
    # `WM_YT_DAILY=1` 을 주면 옛 동작(하루 한 파일 덮어쓰기)으로 되돌아간다 ---
    # 🔴 옛 파일 형식을 읽는 소비자가 있을 수 있어 **문을 남긴다**(있는지는 안 쟀다).
    if os.environ.get("WM_YT_DAILY") == "1":
        p = OUTDIR / f"{today}.json"
        out["🔴 적재 방식"] = "옛 하루1점(WM_YT_DAILY=1)"
    else:
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
        p = OUTDIR / f"{stamp}.json"
        out["🔴 적재 방식"] = "회차별 파일(952 --- 하루 1점 제한 제거)"
    if p.exists():
        prev = json.loads(p.read_text())
        out["이전 판 이력"] = (prev.get("이전 판 이력") or []) + [
            {k: prev.get(k) for k in ("찍은 때", "시각(UTC)", "git HEAD", "입력 지문", "보수")
             if prev.get(k) is not None}
            | {"영상 수": sum(len(r.get("영상") or []) for r in prev.get("대상") or [])}]
        if prev.get("보수"):
            out["보수"] = prev["보수"]
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return {"저장": str(p), "대상 수": len(targets),
            "영상 수": sum(len(r["영상"]) for r in out["대상"]),
            "이전 판 보존": "이전 판 이력" in out}


if __name__ == "__main__":
    print(json.dumps(snapshot(), ensure_ascii=False, indent=1))
