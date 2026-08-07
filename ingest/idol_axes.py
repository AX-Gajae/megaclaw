"""아이돌 도메인에 팝업의 다섯 축을 매긴다 --- 그리고 매길 수 없는 것을 정직하게 남긴다.

노트 4~7이 남긴 다섯 축은 팝업 어휘로 쓰여 있지만 형태는 도메인 불변이다.

    타깃 폭        대상이 얼마나 넓은가
    매장 노출도     그 대상이 닿기 얼마나 쉬운 자리인가
    입장 허들       닿는 데 무엇을 치러야 하는가
    미디어 투입     닿으라고 얼마나 밀었는가
    굿즈 규모       닿으면 무엇을 얻는가

아이돌 데뷔로 옮기면 이렇게 된다.

    타깃 폭      그룹 구성과 대중 노출 경로 (성별 구성, 인원, 서바이벌 출신 여부)
    매장 노출도  소속사가 확보하는 유통·음방 자리
    입장 허들    앨범 단품 정가 (알라딘 상품 페이지에서 수집)
    미디어 투입  데뷔 전 홍보 물량과 화제
    굿즈 규모    앨범 버전 수 (알라딘 상품 제목의 버전 표기)

처음 유도했을 때 입장 허들과 굿즈 규모는 태깅률이 0%였다. 아이돌 레코드에 앨범
가격도 버전 수도 없었기 때문이다. 노트 8이 이것을 수집 과제로 지정했고,
ingest/idol_album_meta.py 로 81건 중 69건(85%)을 채웠다.

근거가 없는 축은 0으로 채우지 않고 마스크로 남긴다 --- 팝업 쪽 규약과 같다.
없는 것을 있는 척하면 전이 실험이 거짓말을 한다.

**소속사 체급을 손으로 매기지 않는다.** 'SM은 4점, 신생사는 0점' 식의 사전 등급은
내가 아는 것을 데이터에 주입하는 것이고, 검정할 수 없다. 대신 각 데뷔 시점보다
**엄격히 이전**의 같은 소속사 데뷔 실적으로 사전 통계를 만든다. 시간 인과적이고
누출이 없으며, 소속사가 처음 등장하면 값이 없다(마스크 0).

사용:
  python3 -m ingest.idol_axes            # 진단
  python3 -m ingest.idol_axes --write    # data/state/idol_axes.json 저장
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

REC = Path("data/idol_records")
OUT = Path("data/state/idol_axes.json")
ALBUM = Path("data/state/idol_album_meta.json")

AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]


def norm_agency(a: str | None) -> str | None:
    """'SM Entertainment' / 'SM 엔터테인먼트' / 'SM' 을 하나로 묶는다.
    정규화 전 205개 고유값 중 상당수가 같은 회사의 표기 차이였다."""
    if not a:
        return None
    s = re.sub(r"\(.*?\)", "", a)
    s = re.sub(r"엔터테인먼트|Entertainment|엔터|주식회사|㈜", "", s, flags=re.I)
    s = re.sub(r"[\s/·,]+", "", s).strip().upper()
    return s or None


def agency_prior(recs: list[dict]) -> dict[str, dict]:
    """소속사별 사전 실적 --- 각 레코드 시점보다 엄격히 이전 데뷔만 쓴다."""
    rows = [(norm_agency(r.get("agency")), (r.get("debut_date") or "9999")[:10],
             r.get("chodong"), r["record_id"]) for r in recs]
    rows = [t for t in rows if t[0]]
    out = {}
    for ag, dt, _, rid in rows:
        past = [c for a, d, c, _ in rows
                if a == ag and d < dt and isinstance(c, (int, float)) and c > 0]
        out[rid] = {"n_prior": len(past),
                    "log_mean": float(np.mean(np.log10(past))) if past else None}
    return out


def scale01(v, lo, hi):
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


def derive(r: dict, prior: dict, alb: dict | None = None) -> dict:
    """다섯 축 각각에 (값, 마스크)를 낸다. 근거 없는 축은 마스크 0으로 남긴다."""
    a, m, why = {}, {}, {}

    # ── 타깃 폭 ── 인원이 많을수록, 서바이벌 출신일수록 대상 폭이 넓다고 본다.
    # 서바이벌은 데뷔 전에 이미 지상파/케이블 대중 노출을 거친 경로다.
    mc, sv, gd = r.get("member_count"), r.get("survival_show"), r.get("gender")
    parts, w = [], []
    if isinstance(mc, int) and mc > 0:
        parts.append(scale01(mc, 1, 9)); w.append(1.0)
    if sv is not None:
        parts.append(1.0 if sv else 0.0); w.append(1.0)
    if gd:
        parts.append({"coed": 1.0, "boy": 0.5, "girl": 0.5}.get(gd, 0.5)); w.append(0.5)
    if parts:
        a["target_breadth"] = float(np.average(parts, weights=w))
        m["target_breadth"] = 1.0
        why["target_breadth"] = f"인원={mc} 서바이벌={bool(sv)} 성별={gd}"
    else:
        a["target_breadth"], m["target_breadth"] = 0.0, 0.0
        why["target_breadth"] = "구성 정보 없음"

    # ── 매장 노출도 ── 소속사가 확보하는 유통·음방 자리. 손으로 매긴 체급이 아니라
    # 시간 인과 통계다.
    #
    # 두 신호를 결합한다. 사전작의 **초동 평균**이 더 강하지만(r=+0.519) 커버리지가
    # 33%뿐이고 라벨에 의존한다. 사전 데뷔 **건수**는 라벨이 필요 없고 커버리지
    # 90%이며 단조 관계가 뚜렷하다 --- 첫 데뷔 소속사 log10 4.70, 1건 경험 5.22,
    # 2건 이상 5.34 (r=+0.209). 노트 22가 이 축을 최우선 확보 대상으로 지목했다.
    p = prior.get(r["record_id"], {})
    if p.get("log_mean") is not None:
        # log10 2.5~6.0 구간을 0~1로. 하한은 관측 최소(772장), 상한은 최대(182만).
        a["venue_prominence"] = scale01(p["log_mean"], 2.5, 6.0)
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"동일 소속사 사전 데뷔 {p['n_prior']}건 평균 log10 {p['log_mean']:.2f}"
    elif p.get("n_prior") is not None:
        # 사전작은 있는데 초동이 없거나, 사전작이 아예 없는 경우. 건수만으로 잡는다.
        a["venue_prominence"] = scale01(float(np.log2(p["n_prior"] + 1)), 0.0, 3.0)
        m["venue_prominence"] = 1.0
        why["venue_prominence"] = f"사전 데뷔 {p['n_prior']}건 (초동 미상 — 건수로 대체)"
    else:
        a["venue_prominence"], m["venue_prominence"] = 0.0, 0.0
        why["venue_prominence"] = "소속사 정보 없음"

    # ── 입장 허들 ── 대응물이 없다.
    # 처음에는 앨범 정가를 여기 넣었는데 노트 9의 전이 검정에서 부호가 뒤집혔다
    # (팝업 -0.201 대 아이돌 +0.229). 확인해 보니 아이돌에서 가격은 진입 비용이
    # 아니라 규모 신호였다 --- 버전 수가 늘수록 평균가가 오르고(13,495→18,157→
    # 19,693원) 가격과 초동의 상관도 +0.262로 양이다. 비싼 앨범은 두꺼운 포토북이다.
    # 그래서 가격을 굿즈 규모로 옮기고 이 축은 다시 비운다. 팬클럽 가입 비용이나
    # 예약 경쟁 구조 같은 진짜 진입 비용을 따로 수집해야 한다.
    am = (alb or {}).get(r["record_id"]) or {}
    # ── 입장 허들 ── **앨범 정가.** 노트 38에서 굿즈 규모에서 떼어 여기로 옮겼다.
    #
    # 처음에는 '앨범 가격은 규모 신호'라고 보아 굿즈 규모에 버전 수와 함께 넣었다.
    # 인자 공간 자기 상관을 목표로 배선을 탐색하니 둘을 분리하는 쪽이 나았다 ---
    # 아이돌 인자 공간 자기 상관이 0.537에서 0.572로(확인 씨앗 기준), 열두 셀
    # 평균 이득이 +0.0529에서 +0.0547로 올랐다. 정가와 버전 수는 상관이 +0.198로
    # 낮아 서로 다른 것을 재고 있었고, 한 축에 묶으면 둘 다 흐려졌다.
    up0 = am.get("unit_price")
    if up0:
        a["entry_friction"] = scale01(float(np.log10(max(up0, 5000))), 3.9, 4.7)
        m["entry_friction"] = 1.0
        why["entry_friction"] = f"앨범 정가 {up0:,}원"
    else:
        a["entry_friction"], m["entry_friction"] = 0.0, 0.0
        why["entry_friction"] = "앨범 정가 미수집"

    # ── 미디어 투입 ── 서바이벌 노출 + 데뷔 전 화제 기록 + 소속사 사전 실적.
    parts, w = [], []
    if sv is not None:
        parts.append(1.0 if sv else 0.0); w.append(1.0)
    pds = r.get("pre_debut_signals")
    if pds:
        parts.append(1.0); w.append(0.7)
    elif r.get("pre_debut_note"):
        parts.append(0.5); w.append(0.4)
    if p.get("log_mean") is not None:
        parts.append(scale01(p["log_mean"], 2.5, 6.0)); w.append(0.6)
    if parts:
        a["media_push"] = float(np.average(parts, weights=w))
        m["media_push"] = 1.0
        why["media_push"] = f"서바이벌={bool(sv)} 사전화제={bool(pds)} 소속사사전={p.get('n_prior', 0)}건"
    else:
        a["media_push"], m["media_push"] = 0.0, 0.0
        why["media_push"] = "홍보 관련 정보 없음"

    # ── 굿즈 규모 ── 앨범 버전 수. '닿으면 무엇을 얻는가'의 아이돌 대응물이다.
    # 버전이 많을수록 팬이 모을 것이 많다. 1~8종을 로그 눈금으로 편다 ---
    # 1종과 2종의 차이가 7종과 8종의 차이보다 크다.
    # **정가는 여기서 뺐다**(노트 38). 입장 허들로 옮겼다.
    nv = am.get("versions")
    if nv:
        a["goods_scale"] = scale01(float(np.log2(nv)), 0.0, 3.0)
        m["goods_scale"] = 1.0
        why["goods_scale"] = f"앨범 버전 {nv}종"
    else:
        a["goods_scale"], m["goods_scale"] = 0.0, 0.0
        why["goods_scale"] = "버전 수 미해결 — " + str(am.get("why") or "미수집")

    return {"axes": a, "mask": m, "why": why}


def run(write: bool = False) -> dict:
    recs = [json.loads(f.read_text()) for f in sorted(REC.glob("*.json"))]
    prior = agency_prior(recs)
    pool = [r for r in recs if r.get("chodong_basis_resolved") == "hanteo"]
    alb = json.loads(ALBUM.read_text()) if ALBUM.exists() else {}
    print(f"한터 확정 풀 {len(pool)}건 / 전체 {len(recs)}건 / 앨범 메타 {len(alb)}건")

    rows = {}
    for r in pool:
        rows[r["record_id"]] = {**derive(r, prior, alb),
                                "y": float(np.log10(r["chodong"])),
                                "debut_date": (r.get("debut_date") or "")[:10],
                                "agency_norm": norm_agency(r.get("agency")),
                                "group": r.get("group_name")}
    print("\n=== 축별 태깅률 ===")
    for ax in AXES:
        c = sum(rows[k]["mask"][ax] for k in rows)
        v = [rows[k]["axes"][ax] for k in rows if rows[k]["mask"][ax]]
        bar = "" if not v else f"  평균 {np.mean(v):.2f}  SD {np.std(v):.2f}"
        print(f"  {ax:<20}{int(c):>4}/{len(rows)} ({c/len(rows):.0%}){bar}")
    miss = [ax for ax in AXES if sum(rows[k]["mask"][ax] for k in rows) == 0]
    print(f"\n전면 결측 축: {miss or '없음'}")
    if miss:
        print("  → 전이 실험은 나머지 축으로만 가능하다. 이 축들은 수집 과제다.")
    if write:
        OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
        print(f"\n저장: {OUT} ({len(rows)}건)")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    run(write=a.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
