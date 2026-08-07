"""크라우드펀딩에 다섯 축을 매긴다 --- 다섯 번째 도메인의 축 유도.

앞선 네 도메인에서 확립한 규약을 그대로 따른다.

  · 근거가 없는 축은 0으로 채우지 않고 마스크 0으로 남긴다.
  · **0이 결측인지 관측값인지 여기서 명시한다.** 노트 35(도서 판형)와
    노트 37(게임 퍼블리셔 이력)에서 같은 실수를 두 번 했다. 추측하지 않는다.
  · 창작자 체급을 손으로 매기지 않는다. 각 프로젝트 시작보다 **엄격히 이전**의
    같은 창작자 프로젝트 수로 사전 통계를 만든다(시간 인과, 라벨 불필요).
  · 축 이름과 다른 것을 넣지 않는다. 넣은 뒤 검정한다(노트 28·34·35).

축 대응물:

    타깃 폭      **수량 제한 없는 리워드의 비율.** 한정 수량만 걸면 닿을 수 있는
                 사람 수가 위에서 잘리고, 무제한이면 열려 있다.
    매장 노출도  창작자 사전 프로젝트 수.
    입장 허들    **최저 리워드 금액.** 참여의 하한이며 이 도메인의 핵심 기여다.
                 앞선 세 도메인에서 가격은 전부 규모 신호였다(노트 9·16·34).
                 여기서는 구조적으로 다르다 --- 최저 금액은 리워드 구성의
                 상한과 독립적으로 정해진다.
    미디어 투입  대응 필드 없음 → 마스크 0.
    굿즈 규모    리워드 단계 수.

**라벨은 후원자 수다.** 팝업 일평균 방문자와 같은 물리량이라 도메인 간 비교가
가장 자연스럽다. 캠페인 기간이 대개 30일 안팎으로 고정이라 누적 편향이
게임 리뷰만큼 심하지 않지만, 시장 자체가 커져 왔으므로 **시작 연도**로
탈추세한다(팝업·아이돌과 같은 처리).

사용: python3 -m ingest.funding_axes --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

SRC = Path("data/state/funding_records.json")
OUT = Path("data/state/funding_axes.json")
AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]


def scale01(v, lo, hi):
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


IDX = Path("data/state/funding_creator_index.json")


def creator_prior(recs: list[dict]) -> dict[str, int]:
    """창작자별 사전 프로젝트 수. 각 시작일보다 엄격히 이전만 센다.

    **표본 안에서 세면 안 된다.** 출판사·소속사는 소수 주체가 다작해 표본
    안에서도 사전 건수가 쌓이는데, 창작자는 7만 명이 대부분 1건이라 표본 147명
    중 2건 이상이 12명뿐이었다. 축이 평균 0.01·SD 0.06으로 사실상 상수가 된다.

    그래서 `ingest.funding_creators`가 전체 목록(3,876쪽)에서 만든 색인을 쓴다.
    색인이 없으면 **마스크 0으로 남긴다** --- 0으로 채우지 않는다."""
    idx = json.loads(IDX.read_text()) if IDX.exists() else None
    if not idx:
        return {r["record_id"]: None for r in recs}
    out = {}
    for r in recs:
        c = r.get("creator_uuid")
        d = r.get("start_date") or "9999"
        if not c or c not in idx:
            out[r["record_id"]] = None
            continue
        out[r["record_id"]] = sum(1 for dd in idx[c] if dd < d)
    return out


def derive(r: dict, n_prior: int | None) -> dict:
    a, m, why = {}, {}, {}

    # ── 타깃 폭 ── 수량 제한 없는 리워드의 비율.
    #
    # 리워드마다 창작자가 수량 상한을 걸 수 있다. 전부 한정이면 아무리 반응이
    # 좋아도 정해진 수 이상 닿지 못하고, 무제한이면 열려 있다. 게임의 지원
    # 언어 수, 도서의 판형과 같은 자리다.
    # **비율 0은 관측값이다** --- '리워드 전부가 한정 수량'이라는 뜻이다.
    ur = r.get("unlimited_ratio")
    if ur is not None and r.get("n_reward"):
        a["target_breadth"] = float(ur)
        m["target_breadth"] = 1.0
        why["target_breadth"] = (f"무제한 리워드 {r['n_unlimited']}/{r['n_reward']}단계")
    else:
        a["target_breadth"], m["target_breadth"] = 0.0, 0.0
        why["target_breadth"] = "리워드 정보 없음"

    # ── 매장 노출도 ── 창작자 사전 프로젝트 수. **0은 관측값이다**(신인).
    if n_prior is not None:
        a["venue_prominence"] = scale01(float(np.log2(n_prior + 1)), 0.0, 4.0)
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"동일 창작자 사전 프로젝트 {n_prior}건 (표본 내)"
    else:
        a["venue_prominence"], m["venue_prominence"] = 0.0, 0.0
        why["venue_prominence"] = "창작자 식별 불가"

    # ── 입장 허들 ── 최저 리워드 금액. 이 도메인의 핵심 기여다.
    mp = r.get("min_price")
    if mp:
        a["entry_friction"] = scale01(float(np.log10(max(mp, 1000))), 3.0, 5.0)
        m["entry_friction"] = 1.0
        why["entry_friction"] = f"최저 후원 {mp:,}원"
    else:
        a["entry_friction"], m["entry_friction"] = 0.0, 0.0
        why["entry_friction"] = "리워드 금액 없음"

    # ── 미디어 투입 ── 대응 필드 없음.
    a["media_push"], m["media_push"] = 0.0, 0.0
    why["media_push"] = "대응 필드 없음 (노트 20·22에서 도메인 간 정의 불일치)"

    # ── 굿즈 규모 ── 리워드 단계 수.
    nr = r.get("n_reward")
    if nr:
        a["goods_scale"] = scale01(float(np.log2(nr)), 0.0, 4.0)   # 1~16단계
        m["goods_scale"] = 1.0
        why["goods_scale"] = f"리워드 {nr}단계"
    else:
        a["goods_scale"], m["goods_scale"] = 0.0, 0.0
        why["goods_scale"] = "리워드 없음"

    return {"axes": a, "mask": m, "why": why}


def run(write: bool = False) -> dict:
    recs = list(json.loads(SRC.read_text()).values())
    prior = creator_prior(recs)
    rows = {}
    for r in recs:
        rows[r["record_id"]] = {
            **derive(r, prior.get(r["record_id"])),
            "y": float(np.log10(max(r["y_backers"], 1))),
            "start_date": r["start_date"],
            "creator": r.get("creator"),
            "category": r.get("category"),
            "title": r.get("title")}
    print(f"크라우드펀딩 레코드 {len(rows)}건")
    print("\n=== 축별 태깅률 ===")
    for ax in AXES:
        c = sum(rows[k]["mask"][ax] for k in rows)
        v = [rows[k]["axes"][ax] for k in rows if rows[k]["mask"][ax]]
        bar = "" if not v else f"  평균 {np.mean(v):.2f}  SD {np.std(v):.2f}"
        print(f"  {ax:<20}{int(c):>4}/{len(rows)} ({c/max(1,len(rows)):.0%}){bar}")
    y = np.array([v["y"] for v in rows.values()])
    print(f"\n라벨 log10(후원자 수)  평균 {y.mean():.2f}  SD {y.std():.2f}  "
          f"범위 {y.min():.2f}~{y.max():.2f}")
    import collections
    print("연도:", dict(sorted(collections.Counter(
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
