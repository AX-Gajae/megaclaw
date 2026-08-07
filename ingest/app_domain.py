"""열두 번째 도메인 --- **비게임 앱**(노트 397의 전이 시험용).

노트 380이 잰 것이 이 파일의 이유다: **판은 새 도메인을 못 맞힌다.**
도메인 하나를 빼고 나머지 열로 그 도메인의 ρ 를 맞히면 |오차| 가
0.177 인데, 도메인 ρ 자체의 평균절대편차가 0.155 라 **중앙값을 부르는
것과 다를 바 없다.** 그때 남긴 것이 ``새 도메인 하나를 통째로 모아
예언과 대조한다''였다.

**왜 비게임 앱인가.** 라벨이 평가 참여자 수라 모바일 게임과 같은
물리량이고(같은 자 --- 노트 377의 계수 기준 문제를 안 만든다), 축 다섯이
같은 필드에서 나오며, 그런데 **모집단이 다르다** --- 생산성 · 교육 ·
금융 · 사진 같은 열아홉 갈래이고 게임이 한 건도 없다. IP 파운데이션이
전이한다면 여기서도 순위를 매길 수 있어야 한다.

**핵심은 학습에 안 넣는 것이다.** `F18.predict` 는 도메인 원핫을 쓰는데
모르는 도메인이면 원핫이 전부 0 이다 --- 그러면 열한 도메인에서 배운
공유 계수만으로 예측한다. 그것이 ``새 도메인 전이''의 정확한 정의다.

**표본은 차트다** --- 모바일 게임 도메인과 같은 한계이고, 같은 한계를
쓰는 것이 비교에 낫다(노트 371).

    python3 -m ingest.app_domain --want 1200
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .mobile_domain import _get, build

OUT = Path("data/state/app_records.json")
CK = Path("data/state/app_records.jsonl")
# 비게임 갈래만. 6014(게임)를 뺀 나머지 --- 6000 대와 6008~6018.
GENRES = [6000, 6001, 6002, 6003, 6004, 6005, 6006, 6007, 6008, 6009,
          6010, 6011, 6012, 6013, 6015, 6016, 6017, 6018, 6020, 6021, 6023]
# 인기 차트만 쓰면 2025년 이후가 100개 중 16개뿐이라 유보가 안 찬다.
# **신규 목록 셋을 같이 훑는다** --- 다른 도메인의 2025+ 유보와 견줄 수 있는
# 모집단이 그쪽이다. 목록 항목에 `im:releaseDate` 가 이미 있어 상세를 받기
# 전에 연도를 안다.
CHARTS = ("topfreeapplications", "toppaidapplications", "topgrossingapplications",
          "newapplications", "newfreeapplications", "newpaidapplications")


def chart_ids() -> list[tuple[str, int]]:
    out, seen = [], set()
    for g in GENRES:
        for c in CHARTS:
            d = _get(f"https://itunes.apple.com/kr/rss/{c}/limit=100/genre={g}/json",
                     f"app12_{c}_{g}")
            for e in (((d or {}).get("feed") or {}).get("entry") or []):
                i = ((e.get("id") or {}).get("attributes") or {}).get("im:id")
                if i and i not in seen:
                    seen.add(i)
                    rel = (e.get("im:releaseDate") or {}).get("label", "")[:10]
                    out.append((i, g, rel))
            time.sleep(0.25)
        print(f"  갈래 {g} · 누적 {len(out)}", flush=True)
    return out


def run(want: int = 1200) -> dict:
    ids = chart_ids()
    print(f"비게임 앱 후보 {len(ids)} · 목표 {want}", flush=True)
    done = {}
    if CK.exists():
        for line in CK.read_text().splitlines():
            try:
                o = json.loads(line)
                done[o["record_id"]] = o
            except Exception:
                pass
    ck = CK.open("a")
    n = 0
    for aid, g, rel in ids:
        rid = f"MB-{aid}"
        if rid in done or len(done) >= want:
            continue
        r = build(aid)
        if r:
            r["record_id"] = f"AP-{aid}"          # 모바일과 안 겹치게
            r["_genre"] = g                        # 출처 좌표(노트 383)
            r["_list_release"] = rel
            done[r["record_id"]] = r
            ck.write(json.dumps(r, ensure_ascii=False) + "\n")
            ck.flush()
            n += 1
            if n % 50 == 0:
                OUT.write_text(json.dumps(done, ensure_ascii=False))
                post = sum(1 for v in done.values()
                           if (v.get("release_date") or "0") >= "2025")
                print(f"  {len(done)}/{want} · 2025+ {post}", flush=True)
        time.sleep(0.2)
    OUT.write_text(json.dumps(done, ensure_ascii=False))
    post = sum(1 for v in done.values() if (v.get("release_date") or "0") >= "2025")
    print(f"끝: {len(done)}건 · 2025+ {post}", flush=True)
    return {"n": len(done), "post2025": post}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--want", type=int, default=1200)
    a = ap.parse_args()
    run(a.want)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
