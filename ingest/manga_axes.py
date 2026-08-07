"""일본 만화에 다섯 축을 매긴다 --- 아홉 번째 도메인의 축 유도.

앞선 여덟 도메인의 규약을 그대로 따른다(노트 35 · 37 · 23 · 28 · 11).

축 대응물 --- **웹툰과 같은 자리에 같은 물리량을 둔다.** 두 도메인의 차이가
배선이 아니라 시장에서 오게 하려는 것이며, 노트 74에서 스팀/모바일에 같은
설계를 썼다.

    타깃 폭      **태그 수.** 웹툰과 같다.
    매장 노출도  **작가 사전 작품 수.** 표본 안에서 자기보다 먼저 시작한 것만
                 센다(노트 23).
    입장 허들    **성인 여부.** 웹툰의 유료 여부와 같은 자리.
    미디어 투입  대응 필드 없음 → 마스크 0.
    굿즈 규모    **연재 밀도**(화수 / 경과 주). 웹툰과 같다 --- 화수 그대로는
                 연재 기간에 비례해 사후 누적된다(노트 21 · 46).

**라벨은 서재 등록 수다.** 웹툰 관심 수·게임 리뷰와 같은 누적 물리량이며 연재
시작일 기준 log 경과일로 탈추세한다(노트 13).

사용: python3 -m ingest.manga_axes --write
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

SRC = Path("data/state/manga_records.json")
OUT = Path("data/state/manga_axes.json")
AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
ASOF = date(2026, 7, 29)


def scale01(v, lo, hi):
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


def weeks_since(d: str | None) -> float | None:
    try:
        days = (ASOF - date(*map(int, (d or "").split("-")))).days
        return max(days, 7) / 7.0
    except (ValueError, TypeError):
        return None


def author_prior(recs: list[dict]) -> dict[str, int | None]:
    """작가별 사전 작품 수. 자기 시작일보다 **엄격히 이전**만 센다."""
    rows = []
    for r in recs:
        d = r.get("start_date") or "9999"
        for a in (r.get("authors") or []):
            rows.append((a, d))
    out = {}
    for r in recs:
        aus = set(r.get("authors") or [])
        if not aus:
            out[r["record_id"]] = None
            continue
        d = r.get("start_date") or "9999"
        out[r["record_id"]] = sum(1 for aa, dd in rows if aa in aus and dd < d)
    return out


def derive(r: dict, n_prior: int | None) -> dict:
    a, m, why = {}, {}, {}

    nt = r.get("n_tag")
    if nt:
        a["target_breadth"] = scale01(float(nt), 3.0, 30.0)
        m["target_breadth"] = 1.0
        why["target_breadth"] = f"태그 {nt}개"
    else:
        a["target_breadth"], m["target_breadth"] = 0.0, 0.0
        why["target_breadth"] = "태그 없음"

    if n_prior is not None:
        a["venue_prominence"] = scale01(float(np.log2(n_prior + 1)), 0.0, 4.0)
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"작가 사전 작품 {n_prior}건"
    else:
        a["venue_prominence"], m["venue_prominence"] = 0.0, 0.0
        why["venue_prominence"] = "작가 정보 없음"

    # 성인 여부는 항상 채워져 오므로 False 는 **관측값**이다.
    a["entry_friction"] = 1.0 if r.get("is_adult") else 0.0
    m["entry_friction"] = 1.0
    why["entry_friction"] = "성인" if r.get("is_adult") else "전연령"

    a["media_push"], m["media_push"] = 0.0, 0.0
    why["media_push"] = "대응 필드 없음(노트 20·22)"

    ne, wk = r.get("n_chapter"), weeks_since(r.get("start_date"))
    if ne and wk:
        a["goods_scale"] = scale01(float(ne) / wk, 0.05, 1.2)
        m["goods_scale"] = 1.0
        why["goods_scale"] = f"연재 밀도 {ne}화/{wk:.0f}주"
    else:
        a["goods_scale"], m["goods_scale"] = 0.0, 0.0
        why["goods_scale"] = "화수·시작일 정보 없음"

    return {"axes": a, "mask": m, "why": why}


def drop_constant(rows: dict, tol: float = 0.05) -> list[str]:
    dropped = []
    for ax in AXES:
        v = [rows[k]["axes"][ax] for k in rows if rows[k]["mask"][ax]]
        if len(v) >= 10 and float(np.std(v)) < tol:
            for k in rows:
                rows[k]["mask"][ax] = 0.0
                rows[k]["why"][ax] += f" --- 표본 내 SD {np.std(v):.3f}로 상수, 마스크 0"
            dropped.append(ax)
    return dropped


# **일본 작품만 남긴다(노트 79).**
#
# AniList 는 한국 웹툰도 MANGA 로 분류한다. 그렇게 들어온 556건은 축이 라벨을
# 거의 설명하지 못한다 --- 자기 순위 상관이 +0.083으로 일본 작품(+0.477)의
# 6분의 1이다. 라벨이 *세계 독자*의 서재 등록 수라 한국 작품에서는 영어 번역
# 유무에 지배되는데 AniList 메타데이터가 그것을 담지 않기 때문으로 보인다.
# 빼면 판정치가 +0.3915에서 +0.4003으로 오르고 씨앗 넷 전부 채택이다.
#
# 도메인 정의와도 맞는다 --- 이 도메인은 '일본 만화'이고 한국 작품은 웹툰
# 도메인과 시장이 겹친다.
KEEP_COUNTRY = ("JP",)


def run(write: bool = False) -> dict:
    all_recs = list(json.loads(SRC.read_text()).values())
    recs = [r for r in all_recs if r.get("country") in KEEP_COUNTRY]
    print(f"국가 필터: {len(all_recs)}건 → {len(recs)}건 ({'·'.join(KEEP_COUNTRY)})")
    prior = author_prior(recs)
    rows = {}
    for r in recs:
        rows[r["record_id"]] = {
            **derive(r, prior.get(r["record_id"])),
            "y": float(np.log10(max(r["y_popularity"], 1))),
            "start_date": r["start_date"],
            "title": r.get("title"),
            "country": r.get("country")}
    dropped = drop_constant(rows)
    print(f"만화 레코드 {len(rows)}건")
    if dropped:
        print(f"상수 축 강등: {dropped}")
    print("\n=== 축별 태깅률 ===")
    for ax in AXES:
        c = sum(rows[k]["mask"][ax] for k in rows)
        v = [rows[k]["axes"][ax] for k in rows if rows[k]["mask"][ax]]
        bar = "" if not v else f"  평균 {np.mean(v):.2f}  SD {np.std(v):.2f}"
        print(f"  {ax:<20}{int(c):>4}/{len(rows)} ({c/max(1,len(rows)):.0%}){bar}")
    y = np.array([v["y"] for v in rows.values()])
    print(f"\n라벨 log10(서재 등록 수)  평균 {y.mean():.2f}  SD {y.std():.2f}  "
          f"범위 {y.min():.2f}~{y.max():.2f}")
    import collections
    c = collections.Counter(v["start_date"][:4] for v in rows.values())
    print(f"시작 연도: {min(c)}~{max(c)}  ({len(c)}개 연도)")
    print("국가:", dict(collections.Counter(v["country"] for v in rows.values())))
    if write:
        OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
        print(f"\n저장: {OUT}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    run(write=a.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
