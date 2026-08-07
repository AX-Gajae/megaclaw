"""도서 도메인에 다섯 축을 매긴다 --- 네 번째 도메인의 축 유도.

앞선 세 도메인에서 확립한 규약을 그대로 따른다.

  · 근거가 없는 축은 0으로 채우지 않고 마스크 0으로 남긴다.
  · 출판사 체급을 손으로 매기지 않는다. 각 출간 시점보다 **엄격히 이전**의
    같은 출판사 출간 실적으로 사전 통계를 만든다(시간 인과, 라벨 불필요).
  · 축 이름과 다른 것을 넣지 않는다. 넣은 뒤 전이가 유지되는지 반드시 검정한다
    (노트 28 --- 의미로 판단할 수 있는 것은 후보 자격까지다).

축 대응물 --- 앞선 도메인과 **같은 물리량**으로 맞춘다.

    타깃 폭      판형 --- 작은 판형은 문고본·실용서이고 대중을 향한다.
    매장 노출도  출판사 사전 출간 건수 --- 유통 자리 확보력.
                 아이돌의 소속사 사전 데뷔 건수와 같은 계산이다(노트 23).
    입장 허들    정가. **다만 기대는 낮다** --- 아이돌(노트 9)과 게임(노트 16)에서
                 가격은 허들이 아니라 규모 신호였다. 세 번째 확인이 된다.
    미디어 투입  대응 필드 없음 → 마스크 0.
                 노트 20·22에서 이 축은 도메인마다 다른 물리량을 재어 해로웠다.
    굿즈 규모    **양장 여부**. 쪽수는 라벨과 r=-0.015로 무효였다(노트 34).
                 같은 유형 후보 중 양장이 +0.296으로 가장 강하다.

**전자책을 제외한다 --- 결측 누출 때문이다(노트 35).**

수집한 396건 중 153건이 전자책이고, 전자책에는 판형이 아예 없다. 즉 판형 결측이
곧 전자책 여부이며 두 형식의 판매지수는 log 평균 4.30 대 3.31로 열 배 차이 난다.
판형을 쓰는 축은 물리량을 재는 척하면서 매체 형식을 맞히게 된다. 실제로 형식별
평균을 빼면 도서 자기 상관이 0.459에서 -0.002로 사라졌다. 부분집합 안에서 재면
종이책 0.220, 전자책 0.045다.

종이책만 남기면 243건이 되고 판형 관측률이 99.6%로 올라 누출이 없어진다.
Kaufman(2012)이 분류한 '결측 패턴이 정보를 담는' 누출의 사례다.

**라벨은 판매지수(Sales Point)다.** 누적 판매에 근거하므로 출간 후 경과 시간에
따라 커진다 --- 게임 리뷰와 같은 구조이며, 출간일 기준 log 탈추세가 필수다
(노트 13에서 달력 연도를 쓰면 부호가 뒤집힘을 확인했다).

사용: python3 -m ingest.book_axes --write
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

SRC = Path("data/state/book_records.json")
OUT = Path("data/state/book_axes.json")
AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
ASOF = date(2026, 7, 28)


def scale01(v, lo, hi):
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


def norm_pub(p: str | None) -> str | None:
    if not p:
        return None
    return "".join(c for c in p.lower() if c.isalnum()) or None


def publisher_prior(recs: list[dict]) -> dict[str, int]:
    """출판사별 사전 출간 건수. 각 출간일보다 엄격히 이전만 센다."""
    rows = [(norm_pub(r.get("publisher")), (r.get("pub_date") or "9999")[:10])
            for r in recs]
    rows = [t for t in rows if t[0]]
    out = {}
    for r in recs:
        p = norm_pub(r.get("publisher"))
        if not p:
            out[r["record_id"]] = None
            continue
        d = (r.get("pub_date") or "9999")[:10]
        out[r["record_id"]] = sum(1 for pp, dd in rows if pp == p and dd < d)
    return out


def derive(r: dict, n_prior: int | None) -> dict:
    a, m, why = {}, {}, {}

    # ── 타깃 폭 ── **판형**이 주 신호. 장르 수는 무효였다.
    #
    # 처음에는 장르 수로 잡았는데 라벨과의 상관이 -0.073으로 사실상 0이었다.
    # 개별 변수를 훑으니 판형이 가장 강했다 --- 높이 -0.282, 너비 -0.221.
    # 작은 판형은 문고본·실용서이고 대중을 향한다. 큰 판형은 전문서·양장본이다.
    # 즉 판형은 '몇 명에게 닿을 수 있게 만들었나'를 재며 타깃 폭 자리다.
    h_mm, w_mm, ng = r.get("height_mm"), r.get("width_mm"), r.get("n_genre") or 0
    parts, wt = [], []
    if h_mm:
        parts.append(1.0 - scale01(float(h_mm), 180.0, 280.0)); wt.append(1.0)
    if w_mm:
        parts.append(1.0 - scale01(float(w_mm), 120.0, 200.0)); wt.append(0.7)
    if ng:
        parts.append(scale01(float(np.log2(ng + 1)), 0.0, 3.5)); wt.append(0.3)
    if parts:
        a["target_breadth"] = float(np.average(parts, weights=wt))
        m["target_breadth"] = 1.0
        why["target_breadth"] = f"판형 {w_mm}x{h_mm}mm · 장르 {ng}개"
    else:
        a["target_breadth"], m["target_breadth"] = 0.0, 0.0
        why["target_breadth"] = "판형·장르 정보 없음"

    # ── 매장 노출도 ── 출판사 사전 출간 건수. 라벨이 필요 없다.
    if n_prior is not None:
        a["venue_prominence"] = scale01(float(np.log2(n_prior + 1)), 0.0, 5.0)
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"동일 출판사 사전 출간 {n_prior}건 (표본 내)"
    else:
        a["venue_prominence"], m["venue_prominence"] = 0.0, 0.0
        why["venue_prominence"] = "출판사 정보 없음"

    # ── 입장 허들 ── 정가. 앞선 두 도메인에서 실패했으므로 검정 후 판단한다.
    pr = r.get("price")
    if pr:
        a["entry_friction"] = scale01(float(np.log10(max(pr, 1000))), 3.7, 4.7)
        m["entry_friction"] = 1.0
        why["entry_friction"] = f"정가 {pr:,}원 (규모 신호일 가능성 --- 검정 필요)"
    else:
        a["entry_friction"], m["entry_friction"] = 0.0, 0.0
        why["entry_friction"] = "가격 정보 없음"

    # ── 미디어 투입 ── 대응 필드 없음.
    a["media_push"], m["media_push"] = 0.0, 0.0
    why["media_push"] = "대응 필드 없음 (노트 20·22에서 이 축은 도메인 간 정의 불일치)"

    # ── 굿즈 규모 ── **양장 여부**. 쪽수는 무효였다(노트 34: r=-0.015).
    #
    # 게임에서 최소 설치 용량이 잘 작동했으므로 쪽수도 같은 논리로 갈 줄 알았다.
    # 콘텐츠 분량이라는 점은 같은데 결과가 달랐다. 같은 유형 후보를 전부 재니
    # 양장 여부가 +0.296으로 가장 강했고, 열두 셀 유의가 9에서 11로 올랐다.
    # 다만 그 11은 전자책이 섞인 상태의 값이라 형식 누출을 포함한다 --- 전자책을
    # 뺀 뒤에는 9/12이고 평균 이득만 +0.0441에서 +0.0473으로 오른다(노트 35).
    fmt = r.get("book_format") or ""
    a["goods_scale"] = 1.0 if "Hardcover" in fmt else 0.0
    m["goods_scale"] = 1.0
    why["goods_scale"] = f"{'양장' if a['goods_scale'] else '무선'} ({fmt or '형식 미상'})"

    return {"axes": a, "mask": m, "why": why}


def run(write: bool = False) -> dict:
    allr = list(json.loads(SRC.read_text()).values())
    # 전자책 제외 --- 판형 결측이 형식을 누출한다(노트 35).
    recs = [r for r in allr if "EBook" not in (r.get("book_format") or "")]
    print(f"전자책 {len(allr) - len(recs)}건 제외 (결측 누출), 종이책 {len(recs)}건")
    prior = publisher_prior(recs)
    rows = {}
    for r in recs:
        rows[r["record_id"]] = {
            **derive(r, prior.get(r["record_id"])),
            "y": float(np.log10(max(r["sales_point"], 1))),
            "pub_date": r["pub_date"],
            "publisher": r.get("publisher"),
            "title": r.get("title")}
    print(f"도서 레코드 {len(rows)}건")
    print("\n=== 축별 태깅률 ===")
    for ax in AXES:
        c = sum(rows[k]["mask"][ax] for k in rows)
        v = [rows[k]["axes"][ax] for k in rows if rows[k]["mask"][ax]]
        bar = "" if not v else f"  평균 {np.mean(v):.2f}  SD {np.std(v):.2f}"
        print(f"  {ax:<20}{int(c):>4}/{len(rows)} ({c/max(1,len(rows)):.0%}){bar}")
    y = np.array([v["y"] for v in rows.values()])
    print(f"\n라벨 log10(판매지수)  평균 {y.mean():.2f}  SD {y.std():.2f}  "
          f"범위 {y.min():.2f}~{y.max():.2f}")
    import collections
    print("연도:", dict(sorted(collections.Counter(
        v["pub_date"][:4] for v in rows.values()).items())))
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
