"""세계 애니(AniList)에 다섯 축을 매긴다 --- 열 번째 도메인.

노트 80이 부분집합 처방을 닫았고 노트 76이 배선을 닫았다. 남은 지렛대는 도메인
하나뿐이라 열째를 넣는다 --- 셀 70$\\to$90.

**같은 매체를 두 플랫폼이 다르게 잰다.** 애니(라프텔)는 한국 구독자의 한줄평
수이고 이것은 세계 이용자의 서재 등록 수다. 노트 79가 웹툰/만화에서 같은 구조를
썼고, 그 덕에 \\textbf{라벨 신뢰도를 한 번 더} 잰다.

축 대응물 --- 만화(노트 78)와 같은 자리에 같은 물리량을 둔다.

    타깃 폭      태그 수
    매장 노출도  제작사 사전 작품 수(표본 안 시간 인과)
    입장 허들    성인물 여부
    미디어 투입  대응 필드 없음 → 마스크 0
    굿즈 규모    총 분량(화수 $\\times$ 편당 길이). **완결작만 관측**으로 둔다
                 --- 연재중이면 사후에 늘어나 노트 21의 DLC 구조가 된다.

**라벨은 서재 등록 수다.** 방영 시작일 기준 log 경과일로 탈추세한다.
**일본 작품만 남긴다**(노트 79의 규약).

사용: python3 -m ingest.wanime_axes --write
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

SRC = Path("data/state/wanime_records.json")
OUT = Path("data/state/wanime_axes.json")
AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
KEEP_COUNTRY = ("JP",)


def scale01(v, lo, hi):
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


def studio_prior(recs: list[dict]) -> dict[str, int | None]:
    rows = []
    for r in recs:
        d = r.get("start_date") or "9999"
        for s in (r.get("studios") or []):
            rows.append((s, d))
    out = {}
    for r in recs:
        ss = set(r.get("studios") or [])
        if not ss:
            out[r["record_id"]] = None
            continue
        d = r.get("start_date") or "9999"
        out[r["record_id"]] = sum(1 for aa, dd in rows if aa in ss and dd < d)
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
        a["venue_prominence"] = scale01(float(np.log2(n_prior + 1)), 0.0, 5.0)
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"제작사 사전 작품 {n_prior}건"
    else:
        a["venue_prominence"], m["venue_prominence"] = 0.0, 0.0
        why["venue_prominence"] = "제작사 정보 없음"

    a["entry_friction"] = 1.0 if r.get("is_adult") else 0.0
    m["entry_friction"] = 1.0
    why["entry_friction"] = "성인물" if r.get("is_adult") else "전연령"

    a["media_push"], m["media_push"] = 0.0, 0.0
    why["media_push"] = "대응 필드 없음(노트 20·22)"

    # 총 분량. **완결작만 관측**으로 둔다 --- 연재중이면 사후에 늘어난다.
    ne, du = r.get("n_episode"), r.get("duration")
    if ne and du and r.get("status") == "FINISHED":
        a["goods_scale"] = scale01(float(np.log10(max(ne * du, 1))), 2.0, 4.0)
        m["goods_scale"] = 1.0
        why["goods_scale"] = f"총 {ne}화 × {du}분"
    else:
        a["goods_scale"], m["goods_scale"] = 0.0, 0.0
        why["goods_scale"] = ("연재중 --- 사후 누적이라 관측 안 함(노트 21)"
                              if r.get("status") != "FINISHED" else "화수·길이 없음")

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
    allr = list(json.loads(SRC.read_text()).values())
    recs = [r for r in allr if r.get("country") in KEEP_COUNTRY]
    print(f"국가 필터: {len(allr)}건 → {len(recs)}건")
    prior = studio_prior(recs)
    rows = {}
    for r in recs:
        rows[r["record_id"]] = {
            **derive(r, prior.get(r["record_id"])),
            "y": float(np.log10(max(r["y_popularity"], 1))),
            "start_date": r["start_date"], "title": r.get("title")}
    dropped = drop_constant(rows)
    print(f"세계애니 레코드 {len(rows)}건")
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
    print(f"방영 연도: {min(c)}~{max(c)}")
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
