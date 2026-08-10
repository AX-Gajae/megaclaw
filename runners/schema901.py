"""노트 901 ② 재고 조사 보조 — 원천별 **필드 이름과 채움 수**만 낸다.

🔴 값 분포는 여기서 안 본다(다음 단계). 여기서 내는 것은
「그 이름의 열이 원천에 정말 있나 · 몇 행이나 차 있나」뿐이다.

분모 딱지는 **D1(원천 레코드 수)** 하나만 쓴다.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")


def flat(o, pre="", out=None, depth=0):
    """중첩 dict 를 점 경로로 편다. list 는 잎으로 본다(길이만)."""
    if out is None:
        out = {}
    if depth > 4:
        return out
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{pre}.{k}" if pre else str(k)
            if isinstance(v, dict):
                flat(v, p, out, depth + 1)
            else:
                out[p] = v
    return out


def load_source(name):
    """(레코드 리스트, 분모 D1) 를 낸다."""
    if name in ("팝업", "market", "idol"):
        raise ValueError
    return None


SRC = {
    "팝업":     ("dir",  "data/records"),
    "시장팝업": ("dir",  "data/market_records"),
    "아이돌":   ("dir",  "data/idol_records"),
    "게임":     ("json", "data/state/game_records.json"),
    "도서":     ("json", "data/state/book_records.json"),
    "펀딩":     ("json", "data/state/funding_records.json"),
    "웹툰":     ("json", "data/state/webtoon_records.json"),
    "애니":     ("json", "data/state/anime_records.json"),
    "모바일":   ("json", "data/state/mobile_records.json"),
    "만화":     ("json", "data/state/manga_records.json"),
    "세계애니": ("json", "data/state/wanime_records.json"),
}


def records(dom):
    kind, p = SRC[dom]
    if kind == "dir":
        fs = sorted((ROOT / p).glob("*.json"))
        return [json.loads(f.read_text()) for f in fs], len(fs), p
    d = json.loads((ROOT / p).read_text())
    rs = list(d.values()) if isinstance(d, dict) else list(d)
    return rs, len(rs), p


def main():
    doms = sys.argv[1:] or list(SRC)
    out = {}
    for dom in doms:
        rs, n, p = records(dom)
        cnt = Counter()
        nonnull = Counter()
        for r in rs:
            f = flat(r)
            for k, v in f.items():
                cnt[k] += 1
                if v is not None and v != "" and v != [] and v != {}:
                    nonnull[k] += 1
        out[dom] = {"원천": p, "D1": n,
                    "필드": {k: [cnt[k], nonnull[k]] for k in sorted(cnt)}}
        print(f"=== {dom}  원천={p}  D1={n}  필드수={len(cnt)}")
        for k in sorted(cnt):
            print(f"   {k}\t있음={cnt[k]}\t비어있지않음={nonnull[k]}")
    (ROOT / "runners/out901_schema.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
