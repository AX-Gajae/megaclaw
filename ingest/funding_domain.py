"""다섯 번째 도메인 --- 크라우드펀딩. 텀블벅 공개 API에서 축과 라벨을 모은다.

노트 34에서 한 번 시도했다가 ``텀블벅은 SPA''로 접었다. SPA면 뒤에 JSON API가
있다는 뜻이므로 다시 봤고, 세 엔드포인트가 열려 있었다.

    /api/v2/projects?page=N            목록 (77,515건, 3,876쪽)
    /api/v2/project/{uuid}             상세
    /api/v2/project/{uuid}/rewards     리워드 단계 --- 금액·수량 제한·후원자 수

**이 도메인이 필요한 이유가 둘이다.**

첫째, 노트 39가 이중 배선으로 11/12를 얻었는데 이득의 거의 전부가 아이돌
하나에서 나왔다. 다섯째 도메인이 없으면 아이돌 특수 현상인지 알 수 없다.

둘째, **입장 허들 축을 처음으로 제대로 잰다.** 노트 9는 아이돌 앨범 가격,
노트 16은 게임 가격, 노트 34는 도서 정가로 시도했고 셋 다 허들이 아니라 규모
신호였다. 크라우드펀딩의 **최저 후원 금액**은 다르다 --- 참여하려면 반드시
내야 하는 최소 금액이고, 그 위의 리워드 구성과 독립적으로 정해진다.

축 대응물:

    타깃 폭      **수량 제한 없는 리워드의 비율.** 한정 수량만 걸면 닿을 수 있는
                 사람이 정해지고, 무제한이면 열려 있다. 게임의 지원 언어 수,
                 도서의 판형과 같은 자리다.
    매장 노출도  창작자의 사전 프로젝트 수. 표본 안에서 시간 인과로 센다
                 (아이돌 소속사·도서 출판사와 같은 계산, 노트 23).
    입장 허들    **최저 리워드 금액.** 이 도메인의 핵심 기여다.
    미디어 투입  대응 필드 없음 → 마스크 0.
    굿즈 규모    리워드 단계 수. '닿으면 무엇을 얻나'의 폭.

**라벨은 후원자 수(pledgedCount)다.** 모금액이 아니라 사람 수를 쓰는 이유는
팝업의 일평균 방문자와 **같은 물리량**이기 때문이다 --- 몇 명이 반응했나.
모금액을 쓰면 리워드 단가가 라벨에 섞여 입장 허들 축과 순환한다.

**누출 주의.** `backersCount`(리워드별 후원자 수), `percentage`(달성률),
`likedCountCache`(좋아요)는 전부 캠페인 종료 후에 확정된다. 축에 쓰지 않는다.
`limit`과 `money`는 캠페인 시작 전 창작자가 정하는 값이라 안전하다.

사용:
  python3 -m ingest.funding_domain --want 400
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path("data/state/funding_records.json")
CACHE = Path("data/state/cache_tumblbug")
API = "https://api.tumblbug.com/api/v2"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json", "Accept-Language": "ko-KR,ko;q=0.9"}
DELAY = 0.9
RETRY = 3


def _get(url: str, key: str) -> dict | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (key + ".json")
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink()
    for attempt in range(RETRY):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=20) as r:
                d = json.loads(r.read().decode("utf-8", "ignore"))
            time.sleep(DELAY)
            f.write_text(json.dumps(d, ensure_ascii=False))
            return d
        except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                TimeoutError, json.JSONDecodeError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code in (404, 500):
                return None
            time.sleep(DELAY * (4 ** attempt))
    return None


def list_pages(pages) -> list[dict]:
    """목록에서 **종료된** 프로젝트만 모은다. 진행 중인 것은 라벨이 미완이다."""
    out = []
    for p in pages:
        d = _get(f"{API}/projects?page={p}", f"list_{p}")
        if not d:
            continue
        for c in (d.get("body", {}).get("result", {}).get("contents") or []):
            if c.get("isEnded") and c.get("pledgedCount"):
                out.append(c)
    return out


def rewards(uuid: str) -> list[dict] | None:
    d = _get(f"{API}/project/{uuid}/rewards", f"rw_{uuid}")
    if not d:
        return None
    r = d.get("body", {}).get("result")
    return r if isinstance(r, list) else None


def build(c: dict, rw: list[dict]) -> dict | None:
    money = [x.get("money") for x in rw if x.get("money")]
    if not money:
        return None
    # limit 이 None 이면 수량 무제한이다. 창작자가 시작 전에 정한다.
    unlimited = sum(1 for x in rw if not x.get("limit"))
    return {"record_id": f"FUND-{c['id'][:8]}",
            "uuid": c["id"], "permalink": c.get("permalink"),
            "title": c.get("title"),
            "creator_uuid": c.get("creatorUuid"),
            "creator": c.get("creatorName"),
            "category": c.get("category"),
            "category_name": c.get("categoryName"),
            "start_date": (c.get("fundingStartDate") or "")[:10],
            "end_date": (c.get("endDate") or "")[:10],
            "adult_only": bool(c.get("isOnlyAdult")),
            # ── 라벨 ── 후원자 수. 팝업 일평균 방문자와 같은 물리량이다.
            "y_backers": int(c["pledgedCount"]),
            "amount": c.get("amount"),
            # ── 축 재료 ── 전부 캠페인 시작 전에 정해지는 값이다.
            "n_reward": len(rw),
            "min_price": int(min(money)),
            "max_price": int(max(money)),
            "n_unlimited": unlimited,
            "unlimited_ratio": round(unlimited / len(rw), 4),
            "n_delivery": sum(1 for x in rw if x.get("addressNeeded"))}


def run(want: int = 400, stride: int = 37) -> dict:
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    # 50쪽부터 종료 프로젝트가 나온다. 넓게 훑어 연도와 분야를 섞는다 ---
    # 한 구간만 쓰면 축의 변별력이 떨어진다(노트 11).
    # **보폭은 want 에 맞춰 정한다**(노트 374). 옛 코드는 고정 보폭으로 훑다가
    # 후보가 차면 멈췄다 --- ``--want 2000 --stride 7'' 로 돌리면 앞쪽 쪽만
    # 보고 끝난다. 그러면 표본이 목록 앞부분에 몰리는데, **목록 순서가 후원자
    # 수와 상관이 있다**(옛 400 대 새 450 의 라벨 중앙 1.95 대 2.46,
    # 맨휘트니 $p=3\times10^{-13}$). 연도 분포는 멀쩡해 보여서 안 걸렸다.
    #
    # 한 쪽에서 종료 프로젝트가 대략 스물이 나오므로 필요한 쪽 수는
    # ``want/20`` 이고, 보폭을 그에 맞추면 **전 구간을 고르게** 훑는다.
    need = max(1, int(want / 20 * 1.3))
    stride = max(1, min(stride, (3876 - 50) // need))
    pages = list(range(50, 3876, stride))
    print(f"텀블벅 수집 --- 목록 {len(pages)}쪽 훑기 (기수집 {len(prev)})")
    cands = []
    for i, p in enumerate(pages, 1):
        cands += list_pages([p])
        if len(cands) >= want * 1.15:
            break
        if i % 20 == 0:
            print(f"  목록 {i}/{len(pages)}쪽 · 종료 프로젝트 {len(cands)}건")
    print(f"후보 {len(cands)}건")

    for i, c in enumerate(cands, 1):
        rid = f"FUND-{c['id'][:8]}"
        if rid in prev:
            continue
        rw = rewards(c["id"])
        if not rw:
            continue
        rec = build(c, rw)
        if rec:
            prev[rid] = rec
        # **자주 쓴다**(노트 374). 40건마다 쓰면 중간에 죽을 때 그만큼 잃는다 ---
        # 리워드 호출은 캐시되지만 레코드는 안 남는다.
        if i % 10 == 0:
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
            if i % 100 == 0:
                print(f"  {i}/{len(cands)} 처리 · 채택 {len(prev)}", flush=True)
        if len(prev) >= want:
            break
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))

    import collections

    import numpy as np
    yr = collections.Counter(v["start_date"][:4] for v in prev.values())
    y = np.log10(np.maximum([v["y_backers"] for v in prev.values()], 1))
    print(f"\n총 {len(prev)}건")
    print("연도:", dict(sorted(yr.items())))
    print("분야:", dict(collections.Counter(v["category"] for v in prev.values())
                      .most_common(8)))
    print(f"라벨 log10(후원자 수)  평균 {y.mean():.2f}  SD {y.std():.2f}  "
          f"범위 {y.min():.2f}~{y.max():.2f}")
    for k in ("min_price", "n_reward", "unlimited_ratio", "creator_uuid"):
        c = sum(1 for v in prev.values() if v.get(k) is not None)
        print(f"  {k:<18}{c:>4}/{len(prev)} ({c/max(1,len(prev)):.0%})")
    return prev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--want", type=int, default=400)
    ap.add_argument("--stride", type=int, default=37)
    a = ap.parse_args()
    run(a.want, a.stride)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
