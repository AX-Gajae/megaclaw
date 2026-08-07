"""애니메이션에 다섯 축을 매긴다 --- 일곱 번째 도메인의 축 유도.

앞선 여섯 도메인의 규약을 그대로 따른다.

  · 근거 없는 축은 0으로 채우지 않고 마스크 0으로 남긴다.
  · **0이 결측인지 관측값인지 명시한다.** 노트 35(도서 판형)와 노트 37(게임
    퍼블리셔 이력)에서 두 번 당했다.
  · 체급을 손으로 매기지 않는다. 표본 안에서 시간 인과로 센다(노트 23).
  · 값이 있다고 축이 되는 것이 아니라 **변해야 축이 된다**. 상수는 강등한다.
  · 넣은 뒤 검정한다. 의미로 판단할 수 있는 것은 후보 자격까지다(노트 28).

축 대응물:

    타깃 폭      **연령 등급(노트 75).** 태그 수로 시작했다가 배선 탐색에서
                 바꿨다. 부호가 다른 도메인과 반대인데, 닿는 폭을 일반 인구가
                 아니라 **플랫폼 인구** 기준으로 재기 때문이다.
    매장 노출도  **제작사 사전 작품 수.** 아이돌 소속사 사전 데뷔·도서 출판사
                 이력·웹툰 작가 사전 연재와 같은 자리다. 공개일보다 엄격히
                 이전만 센다.
    입장 허들    **1화 대여가.** 무료면 0원이며 **관측된 0**이다. 웹툰의 유료
                 여부, 펀딩의 최소 리워드가와 같은 자리다.
    미디어 투입  **더빙 + 독점/오리지널.** 한국어 더빙은 유통사가 추가로 쓴
                 돈이고, 독점 확보도 마찬가지다. 앞선 여섯 중 미디어 투입에
                 실제 값이 들어가는 것은 팝업 다음으로 처음이다.
    굿즈 규모    **대응물 없음(노트 75).** 시리즈 순번은 '무엇을 얻나'가 아니라
                 '얼마나 늦었나'였다. 마스크 0으로 둔다.

**라벨은 한줄평 수다.** 게임 리뷰 총계·도서 판매지수와 같은 누적 물리량이며,
1화가 라프텔에 올라온 날 기준 log 경과일로 탈추세한다(노트 13).

사용: python3 -m ingest.anime_axes --write
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

SRC = Path("data/state/anime_records.json")
OUT = Path("data/state/anime_axes.json")
AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
ASOF = date(2026, 7, 29)


def scale01(v, lo, hi):
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


def _norm(s: str | None) -> str:
    """제작사 이름 정규화. 노트 52에서 'SM'과 'SM엔터테인먼트'가 따로 세어졌다."""
    return "".join(c for c in (s or "").lower() if c.isalnum())


def prior_count(recs: list[dict], key: str) -> dict[str, int | None]:
    """같은 키(제작사·시리즈)를 공유하며 **자기보다 먼저 공개된** 작품 수.

    시간 인과를 지킨다 --- 노트 23의 규약이다. 사후 누적을 축으로 쓰면 노트 21의
    DLC 수와 같은 누출이 되는데, 엄격히 이전만 세면 공개 시점에 이미 정해진
    값이라 누출이 아니다."""
    rows = []
    for r in recs:
        k = _norm(str(r.get(key) or "")) if key != "series_id" else str(r.get(key) or "")
        if k and k != "None":
            rows.append((k, r.get("start_date") or "9999"))
    out = {}
    for r in recs:
        k = _norm(str(r.get(key) or "")) if key != "series_id" else str(r.get(key) or "")
        if not k or k == "None":
            out[r["record_id"]] = None
            continue
        d = r.get("start_date") or "9999"
        out[r["record_id"]] = sum(1 for kk, dd in rows if kk == k and dd < d)
    return out


def derive(r: dict, n_studio: int | None, n_series: int | None) -> dict:
    a, m, why = {}, {}, {}

    # ── 타깃 폭 ── **연령 등급.** 태그 수로 시작했다가 노트 75에서 바꿨다.
    #
    # 웹툰에서 태그 수가 연령 등급을 이겼길래(노트 46) 그대로 베꼈는데, 애니는
    # 배선 탐색을 한 번도 안 한 유일한 도메인이었다. 앙상블 자로 후보 열을
    # 돌리니 연령 등급이 Δ+0.0312(씨앗 넷 전부 채택)이고, 애니 앙상블이
    # -0.258에서 -0.012로 올라온다. 노트 69가 "방향이 뒤집혔다"고 부른 것이
    # 실은 **배선을 안 고른 것**이었다.
    #
    # **부호가 다른 도메인과 반대라는 점을 밝혀 둔다.** 다른 여섯에서 타깃 폭은
    # '몇 명에게 닿게 만들었나'이고 연령 등급이 높을수록 좁아진다. 애니는
    # 반대다 --- 라프텔은 유료 애니 구독 서비스라 주 이용자가 성인이고,
    # 전체 이용가는 아동 대상이라 한줄평을 쓰는 층과 멀다. **닿는 폭을 일반
    # 인구가 아니라 플랫폼 인구 기준으로 재면 부호가 뒤집힌다.**
    ag = r.get("age")
    if ag is not None:
        a["target_breadth"] = scale01(float(ag), 0.0, 19.0)
        m["target_breadth"] = 1.0
        why["target_breadth"] = f"연령 등급 {ag} (플랫폼 인구 기준)"
    else:
        a["target_breadth"], m["target_breadth"] = 0.0, 0.0
        why["target_breadth"] = "연령 등급 없음"

    # ── 매장 노출도 ── 제작사 사전 작품 수. 표본 안 시간 인과로 센다.
    if n_studio is not None:
        a["venue_prominence"] = scale01(float(np.log2(n_studio + 1)), 0.0, 5.0)
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"제작사 '{r.get('production')}' 사전 작품 {n_studio}건"
    else:
        a["venue_prominence"], m["venue_prominence"] = 0.0, 0.0
        why["venue_prominence"] = "제작사 정보 없음"

    # ── 입장 허들 ── 1화 대여가. **0원은 관측값이다**(무료 제공).
    p = r.get("price")
    if p is None:
        a["entry_friction"], m["entry_friction"] = 0.0, 0.0
        why["entry_friction"] = "가격 정보 없음"
    else:
        a["entry_friction"] = scale01(float(p), 0.0, 1500.0)
        m["entry_friction"] = 1.0
        why["entry_friction"] = f"1화 대여 {p}원" if p else "무료"

    # ── 미디어 투입 ── 더빙 + 독점/오리지널. 셋 다 유통사가 쓴 돈이다.
    # False 는 전부 **관측값**이다 --- 필드가 항상 채워져 온다.
    dub = bool(r.get("is_dubbed"))
    excl = bool(r.get("is_only")) or bool(r.get("is_original"))
    a["media_push"] = 0.5 * dub + 0.5 * excl
    m["media_push"] = 1.0
    why["media_push"] = ("더빙" if dub else "자막만") + (" · 독점/오리지널" if excl else "")

    # ── 굿즈 규모 ── **대응물 없음(노트 75).**
    #
    # 시리즈 사전 작품 수를 넣었는데 노트 69가 뜻을 잘못 짚었음을 밝혔다 ---
    # 굿즈 규모 슬롯은 '닿으면 무엇을 얻나'인데 '몇 번째 시즌인가'는 '얼마나
    # 늦었나'다. 화수로 바꿔도 나빠지고(Δ-0.0131) 태그 수도 미미하다.
    # 근거 없는 축은 0으로 채우지 않고 마스크 0으로 둔다는 규약대로 끈다 ---
    # 타깃 폭 재배선과 함께 Δ+0.0680(씨앗 넷 전부 채택)이다.
    a["goods_scale"], m["goods_scale"] = 0.0, 0.0
    why["goods_scale"] = (f"대응물 없음 --- 시리즈 순번({n_series}건)은 "
                          "'무엇을 얻나'가 아니라 '얼마나 늦었나'다(노트 69·75)")

    return {"axes": a, "mask": m, "why": why}


def drop_constant(rows: dict, tol: float = 0.05) -> list[str]:
    """표본 내 표준편차가 tol 미만인 축을 마스크 0으로 내린다(웹툰과 같은 규약)."""
    dropped = []
    for ax in AXES:
        v = [rows[k]["axes"][ax] for k in rows if rows[k]["mask"][ax]]
        if len(v) >= 10 and float(np.std(v)) < tol:
            for k in rows:
                rows[k]["mask"][ax] = 0.0
                rows[k]["why"][ax] += f" --- 표본 내 SD {np.std(v):.3f}로 상수, 마스크 0"
            dropped.append(ax)
    return dropped


def run(write: bool = False) -> dict:
    recs = list(json.loads(SRC.read_text()).values())
    studio = prior_count(recs, "production")
    series = prior_count(recs, "series_id")
    rows = {}
    for r in recs:
        rows[r["record_id"]] = {
            **derive(r, studio.get(r["record_id"]), series.get(r["record_id"])),
            "y": float(np.log10(max(r["y_review"], 1))),
            "start_date": r["start_date"],
            "title": r.get("title"),
            "medium": r.get("medium")}
    dropped = drop_constant(rows)
    print(f"애니 레코드 {len(rows)}건")
    if dropped:
        print(f"상수 축 강등: {dropped}")
    print("\n=== 축별 태깅률 ===")
    for ax in AXES:
        c = sum(rows[k]["mask"][ax] for k in rows)
        v = [rows[k]["axes"][ax] for k in rows if rows[k]["mask"][ax]]
        bar = "" if not v else f"  평균 {np.mean(v):.2f}  SD {np.std(v):.2f}"
        print(f"  {ax:<20}{int(c):>4}/{len(rows)} ({c/max(1,len(rows)):.0%}){bar}")
    y = np.array([v["y"] for v in rows.values()])
    print(f"\n라벨 log10(한줄평 수)  평균 {y.mean():.2f}  SD {y.std():.2f}  "
          f"범위 {y.min():.2f}~{y.max():.2f}")
    import collections
    print("공개 연도:", dict(sorted(collections.Counter(
        v["start_date"][:4] for v in rows.values()).items())))
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
