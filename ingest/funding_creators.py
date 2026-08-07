"""창작자 사전 이력을 전체 목록에서 만든다.

`ingest.funding_axes`가 매장 노출도를 창작자 사전 프로젝트 수로 잡았는데, 표본
안에서 세니 평균 0.01·SD 0.06으로 사실상 상수였다. 이유가 구조적이다.

    출판사·소속사   소수 주체가 다작한다. 표본 안에서도 사전 건수가 쌓인다.
    창작자          7만 명이 대부분 1건이다. 표본 147명 중 2건 이상은 12명뿐.

그러니 표본이 아니라 **전체 목록**에서 세야 한다. 목록 엔드포인트는 한 쪽에
20건씩 3,876쪽이고, 각 항목에 창작자 uuid와 시작일이 있다. 축 값에는 라벨이
전혀 들어가지 않으므로 전량을 훑어도 누출이 아니다.

`?creatorUuid=` 필터는 **무시된다**(total이 그대로고 매치가 0건이다). 노트 22에서
스팀의 `released_date_range`가 무시된 것과 같은 종류이며, 필터를 믿지 말고
받아서 직접 거르라는 규칙이 여기서도 적용된다.

사용: python3 -m ingest.funding_creators --pages 3876
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path("data/state/funding_creator_index.json")
CACHE = Path("data/state/cache_tumblbug")
API = "https://api.tumblbug.com/api/v2"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json"}
DELAY = 0.55


def _get(url: str, key: str) -> dict | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (key + ".json")
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=20) as r:
                d = json.loads(r.read().decode("utf-8", "ignore"))
            time.sleep(DELAY)
            f.write_text(json.dumps(d, ensure_ascii=False))
            return d
        except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                TimeoutError, json.JSONDecodeError):
            time.sleep(DELAY * (4 ** attempt))
    return None


def run(pages: int = 3876) -> dict:
    """창작자별 (시작일 목록)을 만든다. 축 계산은 소비 쪽에서 한다."""
    idx = json.loads(OUT.read_text()) if OUT.exists() else {}
    seen = set()
    for v in idx.values():
        seen.update(v)
    n_new = 0
    for p in range(1, pages + 1):
        d = _get(f"{API}/projects?page={p}", f"list_{p}")
        if not d:
            continue
        for c in (d.get("body", {}).get("result", {}).get("contents") or []):
            cu, sd = c.get("creatorUuid"), (c.get("fundingStartDate") or "")[:10]
            if not cu or not sd:
                continue
            idx.setdefault(cu, [])
            if sd not in idx[cu] or idx[cu].count(sd) < 1:
                idx[cu].append(sd)
                n_new += 1
        if p % 200 == 0:
            OUT.write_text(json.dumps(idx, ensure_ascii=False))
            print(f"  {p}/{pages}쪽 · 창작자 {len(idx)} · 프로젝트 {n_new}")
    OUT.write_text(json.dumps(idx, ensure_ascii=False))
    import collections
    c = collections.Counter(len(v) for v in idx.values())
    print(f"\n창작자 {len(idx)}명 · 프로젝트 {n_new}건")
    print("작품 수 분포:", dict(sorted(c.items())[:8]))
    print(f"2건 이상 창작자 {sum(n for k, n in c.items() if k > 1)}명")
    return idx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=3876)
    a = ap.parse_args()
    run(a.pages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
