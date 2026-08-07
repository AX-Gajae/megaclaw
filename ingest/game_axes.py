"""게임 도메인에 다섯 축을 매긴다 --- 세 번째 도메인의 축 유도.

팝업·아이돌과 같은 규약을 지킨다.

  · 근거가 없는 축은 0으로 채우지 않고 마스크 0으로 남긴다.
  · 퍼블리셔 체급을 손으로 매기지 않는다. 각 출시 시점보다 **엄격히 이전**의
    같은 퍼블리셔 실적으로 사전 통계를 만든다.
  · 축 이름과 다른 것을 넣지 않는다. 예측이 좋아져도 전이 해석이 망가진다
    (노트 11에서 걸그룹 여부를 타깃 폭에 넣지 않은 이유와 같다).

축 대응물:

    타깃 폭      지원 언어 수 --- 몇 개 나라 사람이 이해할 수 있게 만들었나.
                 장르 수와 플랫폼 수를 보조로 쓴다.
    매장 노출도  스토어 내 노출 데이터가 공개되지 않는다 → 마스크 0
    입장 허들    **비움** --- 가격은 허들이 아니라 규모 신호였다(무료가 오히려
                 반응이 작다). 아이돌과 같은 결과다.
    미디어 투입  퍼블리셔 사전 실적(시간 인과) + 자체 배급 여부
    굿즈 규모    최소 설치 용량 --- 콘텐츠 분량. 규모 인자에 실린다

**주의 --- 입장 허들의 함정.** 아이돌에서 앨범 가격을 입장 허들로 넣었다가 부호가
뒤집혔다(노트 9). 가격이 진입 비용이 아니라 규모 신호였기 때문이다. 게임에서는
무료 배포가 존재하므로 가격이 진짜 허들 축을 갖는다 --- 0원과 7만원의 차이는
규모가 아니라 접근성이다. 다만 유료 구간 안에서는 여전히 규모 신호가 섞이므로,
가격을 그대로 쓰지 않고 **무료 여부와 유료 내 가격 순위를 나눠** 기록한다.

사용: python3 -m ingest.game_axes --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

SRC = Path("data/state/game_records.json")
OUT = Path("data/state/game_axes.json")
AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]


def scale01(v, lo, hi):
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


def publisher_prior(recs: list[dict]) -> dict[str, dict]:
    """퍼블리셔별 사전 실적. 각 출시일보다 엄격히 이전의 같은 퍼블리셔 작품만 쓴다."""
    rows = []
    for r in recs:
        for p in (r.get("publishers") or []):
            rows.append((p.strip(), r["release_date"], r["y_raw"], r["record_id"]))
    out = {}
    for r in recs:
        past = [y for p, d, y, _ in rows
                if p in [x.strip() for x in (r.get("publishers") or [])]
                and d < r["release_date"] and y > 0]
        out[r["record_id"]] = {"n_prior": len(past),
                               "log_mean": float(np.mean(np.log10(past))) if past else None}
    return out


def derive(r: dict, prior: dict) -> dict:
    a, m, why = {}, {}, {}

    # ── 타깃 폭 ── 지원 언어 수가 주 신호. 장르·플랫폼 수를 보조로 쓴다.
    nl, ng, npl = r.get("n_lang") or 0, len(r.get("genres") or []), r.get("n_platform") or 0
    parts, w = [], []
    if nl > 0:
        parts.append(scale01(np.log2(nl), 0.0, 5.0)); w.append(1.0)   # 1~32개 언어
    if ng > 0:
        parts.append(scale01(ng, 1, 6)); w.append(0.5)
    if npl > 0:
        parts.append(scale01(npl, 1, 3)); w.append(0.4)
    if parts:
        a["target_breadth"] = float(np.average(parts, weights=w)); m["target_breadth"] = 1.0
        why["target_breadth"] = f"언어 {nl}개 · 장르 {ng}개 · 플랫폼 {npl}개"
    else:
        a["target_breadth"], m["target_breadth"] = 0.0, 0.0
        why["target_breadth"] = "언어·장르 정보 없음"

    # ── 매장 노출도 ── 퍼블리셔의 유통력.
    #
    # 스토어 내 노출 자체는 공개되지 않지만, 이 축이 재는 것은 '접근 경로를 얼마나
    # 확보했는가'다. 게임에서 그것은 퍼블리셔가 확보하는 스토어 노출·번들·세일
    # 자리이고, 관측 가능한 대리는 **퍼블리셔의 사전 출시 이력**이다.
    #
    # 아이돌의 매장 노출도가 '소속사 사전 데뷔 건수'이므로 **같은 물리량**이다
    # (노트 23의 기준: 측정 도구가 아니라 기능이 같아야 한다).
    #
    # 노트 20에서 자체 배급 여부를 '미디어 투입'에 넣었다가 전이가 나빠져 되돌렸다.
    # 기능이 달랐기 때문이다 --- 자체 배급은 홍보 물량이 아니라 유통 구조다.
    # 여기가 제자리다. 창 라벨과 r=+0.279, 커버리지 100%, 라벨 불필요.
    pp = prior.get(r["record_id"], {})
    n_prior = pp.get("n_prior")
    if n_prior is not None:
        def _n(x):
            return "".join(c for c in (x or "").lower() if c.isalnum())
        self_pub = ({_n(x) for x in (r.get("publishers") or [])}
                    == {_n(x) for x in (r.get("developers") or [])})
        base_v = float(np.log2(n_prior + 1))
        v = base_v * 0.5 if self_pub else base_v + 1.0
        # **노트 28에서 껐다가 노트 37에서 다시 켠다.**
        #
        # 노트 28 당시에는 이 축을 *고유 축*으로 넣었다. 정렬에 참여하지 않으면서
        # 인자 공간의 기하만 흔들어 유의 방향이 6개에서 5개로 떨어졌다. 그래서
        # 껐고 판단은 옳았다.
        #
        # 노트 37에서는 이 축을 **공통 축**으로 쓰며 켰다. 유의 방향이 9에서
        # 10으로, 평균 이득이 +0.0480에서 +0.0529로 올랐기 때문이다.
        #
        # **노트 43에서 다시 껐다.** 그 판정이 MAE 기준이었고, 눈금에 둔감한
        # 순위 기준으로 다시 재니 반대였다 --- 이 축을 끄면 게임을 대상으로 한
        # 네 셀이 전부 좋아진다(아이돌→게임 +0.302→+0.374, 펀딩→게임
        # +0.309→+0.353). 스무 셀 평균 순위 상관이 0.3438에서 0.3516으로 오른다.
        # 게임을 출처로 쓴 셀은 거의 변하지 않는다.
        #
        # 공통 축 목록에서 빼는 것은 아니다. 다른 세 도메인은 이 축을 관측하며
        # 쌍별 정렬(노트 40)이 도메인별 관측 차이를 허용하므로, 게임만 두 축으로
        # 정렬하면 된다. 노트 28의 원래 판단이 옳았던 셈이다.
        #
        # **0은 결측이 아니다.** 처음에 값이 0보다 큰 것만 마스크 1로 두었더니
        # 표본이 482에서 313으로 줄었다. 0은 '표본 내 사전 출시작이 0건'이라는
        # 관측된 값이다 --- 노트 35에서 도서 판형으로 배운 것을 반복할 뻔했다.
        a["venue_prominence"] = scale01(v, 0.0, 6.0)
        m["venue_prominence"] = 0.0
        why["venue_prominence"] = (f"퍼블리셔 사전 출시 {n_prior}건, "
                                   f"{'자체 배급' if self_pub else '별도 퍼블리셔'}")
    else:
        a["venue_prominence"], m["venue_prominence"] = 0.0, 0.0
        why["venue_prominence"] = "퍼블리셔 정보 없음"

    # ── 입장 허들 ── **가격으로 잴 수 없다. 비운다.**
    #
    # 처음에는 무료 여부를 주 신호로, 유료 구간 가격을 보조로 넣었다. 30일 창
    # 라벨로 검정하니 두 가정이 모두 틀렸다.
    #
    #   무료 여부 vs 창 라벨   r=-0.111  (무료 평균 -0.244, 유료 +0.051)
    #   유료 내 가격 vs 창 라벨 r=+0.303
    #
    # 허들 해석이 맞다면 무료 게임의 반응이 커야 하는데 오히려 작다. 그리고
    # 유료 구간 안에서 비쌀수록 반응이 크다. 둘 다 '가격 = 규모 신호'를 가리킨다.
    # 아이돌에서 앨범 가격이 허들이 아니라 규모였던 것(노트 9)과 같은 결과이며,
    # 두 도메인에서 독립적으로 확인된 셈이다.
    a["entry_friction"], m["entry_friction"] = 0.0, 0.0
    why["entry_friction"] = "가격은 허들이 아니라 규모 신호 — 대응 측정 없음"

    # ── 미디어 투입 ── 두 신호를 결합한다.
    #
    # 퍼블리셔 사전 실적이 가장 강하지만(창 라벨과 r=+0.338) 표본의 38%에만 있다.
    # 나머지 62%를 마스크 0으로 두면 이 축이 공통 축에서 빠지고, 그러면
    # 프로크루스테스 정렬의 적재 행렬이 2×2로 여유가 없어진다(노트 19의 한계).
    #
    # 사전작이 없을 때는 **자체 배급 여부**로 대신한다. 퍼블리셔가 따로 붙었다는
    # 것 자체가 홍보 투입의 신호다. 커버리지 100%이고 방향도 맞는다.
    #   자체 배급 218건 평균 반응 -0.138 · 퍼블리셔 있음 216건 +0.139 (r=-0.139)
    p = prior.get(r["record_id"], {})
    if p.get("log_mean") is not None:
        a["media_push"] = scale01(p["log_mean"], 2.0, 6.0); m["media_push"] = 1.0
        why["media_push"] = f"동일 퍼블리셔 사전작 {p['n_prior']}건 평균 log10 {p['log_mean']:.2f}"
    else:
        def _n(x):
            return "".join(c for c in (x or "").lower() if c.isalnum())
        self_pub = ({_n(x) for x in (r.get("publishers") or [])}
                    == {_n(x) for x in (r.get("developers") or [])})
        # **마스크는 0으로 둔다.** 자체 배급 여부는 방향이 맞고(창 라벨과 r=-0.139)
        # 커버리지 100%지만, 이것으로 미디어 투입을 채우자 도메인 간 전이가
        # 나빠졌다 --- 유의 방향 5개에서 4개로, 평균 차이 -0.0527에서 -0.0466으로,
        # 팝업→게임은 p=0.019에서 0.154로.
        #
        # 원인은 정의의 불일치다. 세 도메인의 '미디어 투입'이 서로 다른 것을 잰다.
        #   팝업   기획서에 적힌 홍보 계획을 사람이 0~4로 매김
        #   아이돌 서바이벌 출신 + 데뷔 전 화제 + 소속사 사전 실적
        #   게임   퍼블리셔 사전 실적 + 자체 배급 여부
        # 정렬 축에서 빼도 인자 공간을 통해 영향이 남으므로 축 자체를 비운다.
        # 값은 기록해 두되(나중에 정의를 정합화하면 되살린다) 마스크는 0이다.
        a["media_push"] = 0.25 if self_pub else 0.55
        m["media_push"] = 0.0
        why["media_push"] = ("사전작 없음 — " + ("자체 배급" if self_pub else "별도 퍼블리셔")
                             + " (정의 불일치로 마스크 0, 노트 20)")

    # ── 굿즈 규모 ── **누출이므로 쓰지 않는다.**
    #
    # 처음에는 DLC 수를 앨범 버전 수와 같은 자리로 놓았다. 노트 13이 적은 반증
    # 조건(출시 30일 창 라벨로 바꾸면 설명력이 올라야 한다)을 실행했더니 오히려
    # 나빠졌고, 추적하니 원인이 여기였다. Steam appdetails 의 dlc 목록은
    # **현재** DLC이지 출시 시점 DLC가 아니다.
    #
    #     출시 1년 미만  평균 3.09종 (40%가 0종)
    #     1~4년        평균 6.05종
    #     4년 이상      평균 17.24종
    #
    # 성공한 게임이 DLC를 더 낸다 --- 역인과다. 전체 리뷰와의 상관 +0.180이
    # 30일 창 리뷰와는 +0.084로 반토막 난다. 팝업에서 결과보고서의 일별 표로
    # 운영일수를 세면 누출이라 했던 것과 같은 구조다.
    #
    # 출시 시점 에디션 수(디럭스·컬렉터)를 따로 수집하기 전까지 이 축은 비운다.
    # 측정: **최소 설치 용량**. '닿으면 무엇을 얻는가'의 게임 대응물은 콘텐츠
    # 분량이고, 그것을 가장 직접 재는 것이 용량이다.
    #
    # 경로가 두 번 바뀌었다. DLC 수는 누출이었고(노트 15), 대체한 Steam 기능 수는
    # 누출은 없지만 노트 18의 인자 분석에서 **폭 인자**에 실렸다 --- 언어 수·플랫폼
    # 수와 같은 자리다. 그래서 공통 축 둘이 게임에서는 둘 다 폭이 되어 규모 인자가
    # 통째로 빠졌고, 게임 라벨의 예측 신호 중 공통 축이 담은 비율이 25%뿐이었다.
    #
    #   공통 2축(기능 수 기준)          설명  3.0%
    #   제작 규모(사양·가격·연령)         설명 12.6%
    #   저장 공간 단독                  설명 11.2%
    #
    # 저장 공간은 규모 인자에 실리고 출시 시점에 확정되며 누출이 없다.
    disk = ((r.get("_friction") or {}).get("disk_gb"))
    nc = r.get("n_category")
    if disk:
        a["goods_scale"] = scale01(float(np.log2(max(disk, 0.1))), -2.0, 8.0)  # 0.25GB~256GB
        m["goods_scale"] = 1.0
        why["goods_scale"] = f"최소 설치 용량 {disk:g}GB"
    elif nc:
        a["goods_scale"] = scale01(np.log2(nc + 1), 1.0, 5.0)
        m["goods_scale"] = 1.0
        why["goods_scale"] = f"용량 미상 — Steam 기능 {nc}개로 대체"
    else:
        a["goods_scale"], m["goods_scale"] = 0.0, 0.0
        why["goods_scale"] = "용량·기능 정보 없음"

    return {"axes": a, "mask": m, "why": why}


def run(write: bool = False) -> dict:
    recs = list(json.loads(SRC.read_text()).values())
    # 사양 파싱 결과를 레코드에 붙인다 --- 굿즈 규모가 최소 설치 용량을 쓴다
    fp = Path("data/state/game_friction.json")
    fric = json.loads(fp.read_text()) if fp.exists() else {}
    for r in recs:
        r["_friction"] = fric.get(r["record_id"]) or {}
    prior = publisher_prior(recs)
    rows = {}
    for r in recs:
        rows[r["record_id"]] = {**derive(r, prior),
                                "y": float(np.log10(max(r["y_raw"], 1))),
                                "release_date": r["release_date"],
                                "publisher": (r.get("publishers") or ["?"])[0],
                                "name": r.get("name")}
    print(f"게임 레코드 {len(rows)}건")
    print("\n=== 축별 태깅률 ===")
    for ax in AXES:
        c = sum(rows[k]["mask"][ax] for k in rows)
        v = [rows[k]["axes"][ax] for k in rows if rows[k]["mask"][ax]]
        bar = "" if not v else f"  평균 {np.mean(v):.2f}  SD {np.std(v):.2f}"
        print(f"  {ax:<20}{int(c):>4}/{len(rows)} ({c/max(1,len(rows)):.0%}){bar}")
    y = np.array([v["y"] for v in rows.values()])
    print(f"\n라벨 log10(리뷰)  평균 {y.mean():.2f}  SD {y.std():.2f}  "
          f"범위 {y.min():.2f}~{y.max():.2f}")
    import collections
    print("연도:", dict(sorted(collections.Counter(
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
