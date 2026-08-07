"""모바일 게임에 다섯 축을 매긴다 --- 여덟 번째 도메인의 축 유도.

앞선 일곱 도메인의 규약을 그대로 따른다.

  · 근거 없는 축은 0으로 채우지 않고 마스크 0으로 남긴다.
  · **0이 결측인지 관측값인지 명시한다**(노트 35 · 37).
  · 체급을 손으로 매기지 않고 표본 안에서 시간 인과로 센다(노트 23).
  · 값이 있다고 축이 되는 것이 아니라 **변해야 축이 된다**. 상수는 강등한다.
  · 넣은 뒤 검정한다(노트 28).

**축 배선을 스팀 게임과 일부러 같게 맞춘다.** 게임 도메인은 노트 13 이후 여러
번 검정을 거쳐 언어+장르+플랫폼 → 언어 수, 설치 용량 → 굿즈 규모로 정착했다.
같은 배선을 모바일에 그대로 걸면 **두 도메인의 차이가 배선이 아니라 시장에서
온다**는 것이 보장된다 --- 노트 51 · 52가 시장 성질과 배선 효과를 못 가른
문제를 여기서 미리 막는다.

    타깃 폭      **지원 언어 수.** 스팀 게임과 같은 자리.
    매장 노출도  **개발사 사전 출시작 수.** 자기보다 먼저 나온 것만 센다.
    입장 허들    **가격.** 무료가 대부분이면 상수로 강등된다.
    미디어 투입  **스크린샷 수.** 스토어 페이지에 들인 손이다.
    굿즈 규모    **앱 용량.** 스팀의 설치 용량과 같은 자리.

**라벨은 평가 참여자 수다.** 스팀 리뷰 총계와 같은 누적 물리량이며 출시일 기준
log 경과일로 탈추세한다(노트 13).

사용: python3 -m ingest.mobile_axes --write
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

SRC = Path("data/state/mobile_records.json")
OUT = Path("data/state/mobile_axes.json")
AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
ASOF = date(2026, 7, 29)


def scale01(v, lo, hi):
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


def artist_prior(recs: list[dict]) -> dict[str, int | None]:
    """개발사별 사전 출시작 수. 자기 출시일보다 **엄격히 이전**만 센다."""
    rows = [(r.get("artist_id"), r.get("release_date") or "9999")
            for r in recs if r.get("artist_id")]
    out = {}
    for r in recs:
        a = r.get("artist_id")
        if not a:
            out[r["record_id"]] = None
            continue
        d = r.get("release_date") or "9999"
        out[r["record_id"]] = sum(1 for aa, dd in rows if aa == a and dd < d)
    return out


def derive(r: dict, n_prior: int | None) -> dict:
    a, m, why = {}, {}, {}

    # ── 타깃 폭 ── 지원 언어 수. 스팀 게임과 같은 배선이다.
    nl = r.get("n_lang")
    if nl:
        a["target_breadth"] = scale01(float(nl), 1.0, 30.0)
        m["target_breadth"] = 1.0
        why["target_breadth"] = f"지원 언어 {nl}개"
    else:
        a["target_breadth"], m["target_breadth"] = 0.0, 0.0
        why["target_breadth"] = "언어 정보 없음"

    # ── 매장 노출도 ── 개발사 사전 출시작 수. 표본 안 시간 인과로 센다.
    if n_prior is not None:
        a["venue_prominence"] = scale01(float(np.log2(n_prior + 1)), 0.0, 4.0)
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"개발사 '{r.get('artist')}' 사전 출시 {n_prior}건"
    else:
        a["venue_prominence"], m["venue_prominence"] = 0.0, 0.0
        why["venue_prominence"] = "개발사 정보 없음"

    # ── 입장 허들 ── 가격. **0원은 관측값이다**(무료 배포).
    p = r.get("price")
    if p is None:
        a["entry_friction"], m["entry_friction"] = 0.0, 0.0
        why["entry_friction"] = "가격 정보 없음"
    else:
        a["entry_friction"] = scale01(float(p), 0.0, 15.0)
        m["entry_friction"] = 1.0
        why["entry_friction"] = f"{p:.2f} 달러" if p else "무료"

    # ── 미디어 투입 ── 스크린샷 수. 스토어 페이지에 들인 손.
    ns = r.get("n_shot")
    if ns:
        a["media_push"] = scale01(float(ns), 3.0, 20.0)
        m["media_push"] = 1.0
        why["media_push"] = f"스크린샷 {ns}장"
    else:
        a["media_push"], m["media_push"] = 0.0, 0.0
        why["media_push"] = "스크린샷 없음"

    # ── 굿즈 규모 ── 앱 용량. 스팀의 설치 용량과 같은 자리.
    sz = r.get("size_mb")
    if sz:
        a["goods_scale"] = scale01(float(np.log10(max(sz, 1.0))), 1.0, 3.6)
        m["goods_scale"] = 1.0
        why["goods_scale"] = f"용량 {sz:.0f}MB"
    else:
        a["goods_scale"], m["goods_scale"] = 0.0, 0.0
        why["goods_scale"] = "용량 정보 없음"

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


def run(write: bool = False) -> dict:
    recs = list(json.loads(SRC.read_text()).values())
    prior = artist_prior(recs)
    rows = {}
    for r in recs:
        rows[r["record_id"]] = {
            **derive(r, prior.get(r["record_id"])),
            "y": float(np.log10(max(r["y_rating_count"], 1))),
            "release_date": r["release_date"],
            "title": r.get("title")}
    dropped = drop_constant(rows)
    print(f"모바일 레코드 {len(rows)}건")
    if dropped:
        print(f"상수 축 강등: {dropped}")
    print("\n=== 축별 태깅률 ===")
    for ax in AXES:
        c = sum(rows[k]["mask"][ax] for k in rows)
        v = [rows[k]["axes"][ax] for k in rows if rows[k]["mask"][ax]]
        bar = "" if not v else f"  평균 {np.mean(v):.2f}  SD {np.std(v):.2f}"
        print(f"  {ax:<20}{int(c):>4}/{len(rows)} ({c/max(1,len(rows)):.0%}){bar}")
    y = np.array([v["y"] for v in rows.values()])
    print(f"\n라벨 log10(평가 수)  평균 {y.mean():.2f}  SD {y.std():.2f}  "
          f"범위 {y.min():.2f}~{y.max():.2f}")
    import collections
    print("출시 연도:", dict(sorted(collections.Counter(
        v["release_date"][:4] for v in rows.values()).items())))
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
