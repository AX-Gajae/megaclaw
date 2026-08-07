"""웹툰에 다섯 축을 매긴다 --- 여섯 번째 도메인의 축 유도.

앞선 다섯 도메인의 규약을 그대로 따른다.

  · 근거 없는 축은 0으로 채우지 않고 마스크 0으로 남긴다.
  · **0이 결측인지 관측값인지 명시한다.** 노트 35(도서 판형)와 노트 37(게임
    퍼블리셔 이력)에서 두 번 당했다.
  · 작가 체급을 손으로 매기지 않는다. 표본 안에서 시간 인과로 센다(노트 23).
  · 넣은 뒤 검정한다. 의미로 판단할 수 있는 것은 후보 자격까지다(노트 28).

축 대응물:

    타깃 폭      **큐레이션 태그 수.** 연령 등급으로 시작했다가 검정에서 바꿨다
                 (노트 46). 게임의 장르 수, 도서의 장르 수와 같은 자리다.
    매장 노출도  **주당 연재 요일 수.** 플랫폼이 준 자리의 수이며, 아이돌 소속사
                 사전 데뷔·도서 출판사 이력과 같은 자리다. 작가 사전 연재 수도
                 후보지만 표본 안 중복이 적으면 상수가 된다(노트 40의 펀딩 사례).
    입장 허들    유료 여부(dailyPass). 무료가 대부분이라 분산이 작을 수 있다.
    미디어 투입  대응 필드 없음 → 마스크 0.
    굿즈 규모    **참여 작가 수.** 연재 밀도로 시작했다가 검정에서 바꿨다
                 (노트 48). 밀도도 탈추세하면 무효였고 작가 수만 살아남았다.

**라벨은 관심 등록 수다.** 팝업 일평균 방문자, 펀딩 후원자와 같은 물리량이다.
연재 시작부터 누적되므로 게임 리뷰·도서 판매지수와 같은 구조이며 시작일 기준
log 경과일로 탈추세한다(노트 13).

사용: python3 -m ingest.webtoon_axes --write
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

SRC = Path("data/state/webtoon_records.json")
OUT = Path("data/state/webtoon_axes.json")
AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
ASOF = date(2026, 7, 29)


def scale01(v, lo, hi):
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


def weeks_since(d: str) -> float | None:
    try:
        days = (ASOF - date(*map(int, d.split("-")))).days
        return max(days, 7) / 7.0
    except (ValueError, TypeError):
        return None


def _norm(s: str | None) -> str:
    return "".join(c for c in (s or "").lower() if c.isalnum())


def artist_prior(recs: list[dict]) -> dict[str, int]:
    """작가별 사전 연재 수. 각 시작일보다 엄격히 이전만 센다.

    **작가 전원으로 매칭한다.** 처음에는 첫 번째 작가만 봤는데, 웹툰은 글작가와
    그림작가가 따로인 경우가 절반이 넘어(900건 중 454건이 2인 이상) 매칭을
    놓친다. 전원으로 넓히니 이력 있는 레코드가 84건에서 135건으로, 라벨과의
    상관이 +0.064에서 +0.099로 올랐다(노트 54).

    이름은 정규화한다 --- 아이돌 소속사에서 'SM'과 'SM엔터테인먼트'가 따로
    세어진 것과 같은 결함을 미리 막는다(노트 52)."""
    rows = []
    for r in recs:
        d = r.get("start_date") or "9999"
        for a in (r.get("artists") or []):
            if _norm(a):
                rows.append((_norm(a), d))
    out = {}
    for r in recs:
        arts = {_norm(a) for a in (r.get("artists") or []) if _norm(a)}
        if not arts:
            out[r["record_id"]] = None
            continue
        d = r.get("start_date") or "9999"
        out[r["record_id"]] = sum(1 for aa, dd in rows if aa in arts and dd < d)
    return out


def derive(r: dict, n_prior: int | None) -> dict:
    a, m, why = {}, {}, {}

    # ── 타깃 폭 ── **큐레이션 태그 수.** 연령 등급을 먼저 넣었다가 바꿨다.
    #
    # 연령 등급은 '몇 명에게 닿을 수 있게 만들었나'의 가장 직접적인 표기처럼
    # 보였다. 검정에서 무효였다 --- 탈추세 라벨과 +0.103이고, 축으로 쓰면 웹툰
    # 자기 순위 상관이 +0.034에 그친다. 태그 수로 바꾸면 자기 상관은 오히려
    # -0.125로 내려가는데 **서른 셀 평균 전이가 +0.1985에서 +0.2915로 오른다**
    # (노트 46). 노트 40의 상충 법칙 --- 자기 라벨에 잘 맞을수록 남에게 못
    # 옮겨진다 --- 이 여기서 가장 극단적으로 나타난다.
    #
    # 의미로는 연령 등급이 맞아 보였고 검정은 태그 수를 골랐다. 노트 28·34·35에
    # 세 번 적은 규칙 그대로다.
    nt = r.get("n_tag")
    if nt:
        a["target_breadth"] = scale01(float(nt), 3.0, 14.0)
        m["target_breadth"] = 1.0
        why["target_breadth"] = f"큐레이션 태그 {nt}개"
    else:
        a["target_breadth"], m["target_breadth"] = 0.0, 0.0
        why["target_breadth"] = "태그 없음"

    # ── 매장 노출도 ── 주당 연재 요일 수. 1~3일을 0~1로.
    # 요일 수를 먼저 보되 **작가 사전 연재 수와 합친다.** 요일 수만 쓰면 주 1회가
    # 표준이라 거의 상수가 된다(115건 중 109건). 둘 다 '플랫폼이 준 자리'를 재며
    # 앞선 도메인의 소속사·출판사·퍼블리셔 이력과 같은 계산이다(노트 23).
    nd = r.get("n_day")
    if nd and n_prior is not None:
        a["venue_prominence"] = float(np.average(
            [scale01(float(nd), 1.0, 3.0),
             scale01(float(np.log2(n_prior + 1)), 0.0, 3.0)], weights=[0.5, 1.0]))
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"주 {nd}회 · 작가 사전 연재 {n_prior}건"
    elif nd:
        a["venue_prominence"] = scale01(float(nd), 1.0, 3.0)
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"주 {nd}회 연재 ({','.join(r.get('days') or [])})"
    elif n_prior is not None:
        a["venue_prominence"] = scale01(float(np.log2(n_prior + 1)), 0.0, 3.0)
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"연재 요일 없음 --- 작가 사전 연재 {n_prior}건으로 대체"
    else:
        a["venue_prominence"], m["venue_prominence"] = 0.0, 0.0
        why["venue_prominence"] = "요일·작가 정보 없음"

    # ── 입장 허들 ── 유료 여부. **False 는 관측값이다**(무료).
    a["entry_friction"] = 1.0 if r.get("daily_pass") else 0.0
    m["entry_friction"] = 1.0
    why["entry_friction"] = "매일+ 유료" if r.get("daily_pass") else "무료"

    # ── 미디어 투입 ── 대응 필드 없음.
    a["media_push"], m["media_push"] = 0.0, 0.0
    why["media_push"] = "대응 필드 없음 (노트 20·22에서 도메인 간 정의 불일치)"

    # ── 굿즈 규모 ── **참여 작가 수.** 연재 밀도로 시작했다가 바꿨다(노트 48).
    #
    # 회차 수는 연재 기간에 비례해 사후 누적되므로(노트 21의 DLC와 같은 구조)
    # 경과 주로 나눈 밀도를 썼다. 그런데 밀도도 탈추세하면 -0.11로 사실상
    # 무효였고, 탈추세를 이기고 남은 유일한 변수가 **작가 수**였다(+0.28).
    #
    # 물리적으로는 '제작 투입'인데 굿즈 규모 슬롯의 뜻('닿으면 무엇을 얻나')과
    # 완전히 겹치지는 않는다. 글작가·그림작가·원작자가 따로 붙을수록 작화와
    # 서사에 들어간 손이 많다는 뜻이므로 독자가 받는 것의 양에 가깝다고 본다.
    # 다만 이것은 사후 해석이고, 채택 근거는 검정이다 --- 서른 셀 평균 순위
    # 상관이 +0.2933에서 +0.3189로 오르고 짝지은 95% 구간이
    # [+0.0034, +0.0365]로 0을 넘는다.
    #
    # **표본 418건일 때는 보류했던 후보다.** 그때는 효과가 +0.0355로 더 컸는데
    # 구간이 [-0.0027, +0.0741]로 0을 포함했다. 완결작을 넣어 553건이 되자
    # 효과는 줄고 구간이 좁아져 통과했다.
    # **노트 72에서 연재 밀도로 되돌렸다.** 노트 48이 작가 수로 바꿨던 결정인데,
    # 노트 67이 표본 세 배에서 그 결정이 사라졌음을 확인했고, 노트 71이 판정치를
    # 앙상블로 바꾸자 **되돌리는 쪽이 채택**됐다(+0.0132 [+0.0005, +0.0313],
    # 씨앗 넷 전부). 효과가 작아 문턱 근처이므로 씨앗을 바꿔 확인한 뒤 적용한다.
    ne, wk = r.get("n_episode"), weeks_since(r.get("start_date"))
    if ne and wk:
        a["goods_scale"] = scale01(float(ne) / wk, 0.3, 1.5)
        m["goods_scale"] = 1.0
        why["goods_scale"] = f"연재 밀도 {ne}화/{wk:.0f}주"
    else:
        a["goods_scale"], m["goods_scale"] = 0.0, 0.0
        why["goods_scale"] = "회차·시작일 정보 없음"

    return {"axes": a, "mask": m, "why": why}


def drop_constant(rows: dict, tol: float = 0.05) -> list[str]:
    """표본 내 표준편차가 tol 미만인 축을 마스크 0으로 내린다.

    **일반 규약으로 둘 만하다.** 상수 축은 정보가 없을 뿐 아니라 도메인 내
    표준화에서 0으로 나눈다. 웹툰에서 두 축이 걸렸다 --- 유료 여부는 표본
    115건이 전부 무료이고, 연재 요일 수는 109건이 주 1회다. 값이 있다고 축이
    되는 것이 아니라 **변해야 축이 된다**(노트 11).
    """
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
            "y": float(np.log10(max(r["y_favorite"], 1))),
            "start_date": r["start_date"],
            "title": r.get("title"),
            "finished": r.get("finished")}
    dropped = drop_constant(rows)
    print(f"웹툰 레코드 {len(rows)}건")
    if dropped:
        print(f"상수 축 강등: {dropped}")
    print("\n=== 축별 태깅률 ===")
    for ax in AXES:
        c = sum(rows[k]["mask"][ax] for k in rows)
        v = [rows[k]["axes"][ax] for k in rows if rows[k]["mask"][ax]]
        bar = "" if not v else f"  평균 {np.mean(v):.2f}  SD {np.std(v):.2f}"
        print(f"  {ax:<20}{int(c):>4}/{len(rows)} ({c/max(1,len(rows)):.0%}){bar}")
    y = np.array([v["y"] for v in rows.values()])
    print(f"\n라벨 log10(관심 수)  평균 {y.mean():.2f}  SD {y.std():.2f}  "
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
