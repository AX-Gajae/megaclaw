"""펀딩을 **목록 전체에서 균일 무작위로** 뽑는다(노트 374).

**왜 다시 뽑나.** 기존 400건은 ``funding_domain.run`` 이 목록 앞에서부터
채운 것이고, 텀블벅 목록은 **인기순으로 정렬돼 있다** --- 캐시된 3,875쪽
77,495건에서 쪽 번호와 라벨(log10 후원자)의 순위 상관이 $-0.3666$ 이다
(쪽 50\\~161 중앙 2.56 대 쪽 531\\~753 중앙 1.93). 400건은 쪽 50\\~753,
곧 **위에서 19\\%** 에서 왔다.

그래서 표본을 늘리면 늘어난 쪽이 체계적으로 다른 모집단이 됐다 --- 옛 400
대 새 180 의 라벨 중앙이 2.14 대 2.46 이고 맨휘트니 $p=1.5\\times10^{-13}$
이다. **연도 분포는 두 번 다 멀쩡했다**(20\\% 대 19\\%) --- 대표성을 연도로만
확인하면 안 걸린다.

수집 정렬이 과제를 정한 네 번째 도메인이다(도서 베스트셀러 노트 209 · 269,
모바일 인기 차트, 만화 인기순 노트 365, 그리고 여기).

**고침.** 목록은 이미 다 캐시돼 있다(3,875쪽 · 종료+후원자 있음 75,434건 ·
그중 2025년 이후 13,030건). 목록 호출 없이 **균일 무작위**로 뽑아 리워드만
받는다. 씨앗을 박아 재현 가능하게 둔다(노트 367).

사용: python3 -m ingest.funding_sample --n 2000 [--seed 374]
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

from .funding_domain import CACHE, build, rewards

# **챔피언 파일을 안 건드린다**(노트 374) --- 균일 표본은 따로 쌓고,
# 다 모인 뒤에 짝으로 재고 나서 바꾼다.
OUT = Path("data/state/funding_uniform.json")

POOL = Path("data/state/funding_pool.json")


def pool() -> list[dict]:
    """캐시된 목록에서 자격 있는 프로젝트 전부. 쪽 번호도 같이 남긴다."""
    if POOL.exists():
        return json.loads(POOL.read_text())
    out = []
    for f in sorted(CACHE.glob("list_*.json")):
        m = re.search(r"list_(\d+)", f.name)
        if not m:
            continue
        p = int(m.group(1))
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        for c in (d.get("body", {}).get("result", {}).get("contents") or []):
            if c.get("isEnded") and c.get("pledgedCount"):
                c["_page"] = p
                out.append(c)
    POOL.write_text(json.dumps(out, ensure_ascii=False))
    return out


def run(n: int = 2000, seed: int = 374) -> dict:
    cands = pool()
    print(f"풀 {len(cands)}건 (쪽 {min(c['_page'] for c in cands)}"
          f"~{max(c['_page'] for c in cands)})", flush=True)
    rng = random.Random(seed)
    pick = rng.sample(cands, min(n * 2, len(cands)))   # 리워드 실패분 여유
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    got = 0
    for i, c in enumerate(pick, 1):
        if len(prev) >= n:
            break
        rid = f"FUND-{c['id'][:8]}"
        if rid in prev:
            continue
        rw = rewards(c["id"])
        if not rw:
            continue
        rec = build(c, rw)
        if rec:
            rec["_page"] = c["_page"]
            prev[rid] = rec
            got += 1
        if got and got % 10 == 0:
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
            if got % 200 == 0:
                print(f"  {got}건 추가 · 누적 {len(prev)}", flush=True)
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
    print(f"완료: {len(prev)}건", flush=True)
    return prev


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=374)
    a = ap.parse_args()
    run(a.n, a.seed)
