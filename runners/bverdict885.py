# -*- coding: utf-8 -*-
# 노트 885 병③ — B 판정 필드 소급(티처 #49 치명 2)
# out884_colcensus_fix.json 의 미사용 후보 49행 전건에 부류+사유를 붙인다.
# 부류: SPEC소진 · 장부소진 · 별칭 · 라벨 · 식별자 · 텍스트 · 사후 · 수집메타 · 신규
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
from lab import rawaxes as RA  # noqa: E402

ROOT = Path("/Users/ax/world_model")
BOARD = ["팝업", "아이돌", "게임", "도서", "펀딩", "웹툰", "애니", "모바일",
         "만화", "세계애니", "영화", "시장팝업"]

#: 눈 판정 — (도메인, 필드) → (부류, 사유). 전건 기재 의무(판정 없인 저장 없음).
V = {
    ("만화", "mean_score"): ("사후", "읽은 시점 누적 평점 — 출시 시점 미확정"),
    ("만화", "n_author"): ("장부소진", "노트 787 `mg_nauthor` 로 측정 — 집안 +0.0272 · 788 집 밖 KR +0.0248(문턱 0.025 에 0.0002 미달·서랍·재개 조건 KR 행 ≥3,369)"),
    ("만화", "n_volume"): ("사후", "최종 권수는 결과다(노트 775 가 같은 이유로 기각 — 오래 갈수록 성공)"),
    ("웹툰", "age_rank"): ("별칭", "🔴 티처 #49 M4 — `age_type` 의 숫자 표기. 교차표 완전 일대일(ALL,0)/(RATE_12,1)/(RATE_15,2) · SPEC 에 `wt_agetype` 등재"),
    ("애니", "avg_rating"): ("사후", "읽은 시점 누적 평점"),
    ("애니", "is_free"): ("장부소진", "노트 780 `gm_free` 계열로 게임에서 측정 — 애니 쪽은 775 목록"),
    ("애니", "is_ending"): ("사후", "완결 여부는 결과(노트 775 가 눈으로 기각)"),
    ("세계애니", "native"): ("텍스트", "일본어 원제 — 노트 719 '텍스트 열은 판 안 열이 아니다'"),
    ("세계애니", "english"): ("텍스트", "영문 제목 — 동일"),
    ("세계애니", "mean_score"): ("사후", "AniList 읽은 시점 누적 평점"),
    ("도서", "isbn"): ("식별자", "고유 식별자"),
    ("도서", "pages"): ("장부소진", "노트 780 `bk_pages` 로 측정(도서 3열 — 799 에서 도서 닫음)"),
    ("도서", "genre"): ("텍스트", "장르 리스트 원문(144값) — 태그 내용 계열은 tag_c* 가 덮는다"),
    ("도서", "review_count"): ("라벨", "리뷰 수는 결과 지표"),
    ("도서", "weight_g"): ("장부소진", "노트 780 `bk_weight` 로 측정"),
    ("펀딩", "uuid"): ("식별자", "고유 식별자"),
    ("펀딩", "permalink"): ("식별자", "URL"),
    ("펀딩", "category_name"): ("별칭", "`category` 의 표시명 — fundaxes 가 `category` 를 읽어 fund_cat 을 만든다(92값은 20값의 세분)"),
    ("펀딩", "end_date"): ("사후", "종료일 — cal_* 가 시작일을 덮고 종료는 결과 구간"),
    ("펀딩", "adult_only"): ("장부소진", "축 코드가 정확 인용(884 부칙 눈 검증)"),
    ("펀딩", "amount"): ("라벨", "모금액 = 라벨"),
    ("펀딩", "n_delivery"): ("장부소진", "🔴 티처 #49 M5 지적 — 대장 실측: '펀딩 category(현행) +0.1946 > n_delivery +0.0927' 로 이미 재고 밀렸다"),
    ("펀딩", "_page"): ("수집메타", "수집 페이지 번호"),
    ("모바일", "updated"): ("사후", "최근 갱신일 — 출시 후 변한다"),
    ("모바일", "avg_rating"): ("사후", "읽은 시점 평점"),
    ("모바일", "n_device"): ("신규(측정 완료·미달)", "884 1순위 — 신호 몫 −0.0004 · 위약 6/6 실패 · 유보 441행에서 최빈 127 이 97.7%(사실상 상수) → 서랍"),
    ("영화", "국적"): ("신규(측정 완료·재현 중)", "884 병기 +0.0654 = 2σ 5.0배 · 885 에서 씨앗 0·1·2 재현·분해"),
    ("영화", "상영등급 원문"): ("별칭", "kobis_axes 의 why 가 entry_friction='등급 12세이상관람가' — 이미 접힘"),
    ("영화", "검열(개봉+14 미달)"): ("사후", "관측 창 플래그 — 라벨 품질 메타"),
    ("영화", "마지막 관측일차"): ("사후", "관측 길이 — 라벨 계열"),
    ("팝업", "raw"): ("라벨", "y 원값"),
    ("아이돌", "ip"): ("수집메타", "그룹 식별자 — 세계의 사실이 아니라 매칭 키(티처 #49 M5)"),
    ("아이돌", "raw"): ("라벨", "y 원값"),
    ("아이돌", "group"): ("텍스트", "그룹명"),
    ("아이돌", "album"): ("텍스트", "앨범명"),
    ("아이돌", "why"): ("텍스트", "사유 문장"),
    ("아이돌", "matched_title"): ("수집메타", "매처 출력"),
    ("아이돌", "n_hits"): ("수집메타", "🔴 매처가 몇 건 맞췄나 — 유명할수록 커질 소지(누출 의심·티처 #49 M5)"),
    ("아이돌", "needs_review"): ("수집메타", "사람 검토 플래그"),
    ("아이돌", "근거"): ("텍스트", "매칭 근거 문장 — 세계의 사실이 아니라 파이프라인 설명"),
    ("아이돌", "versions"): ("🔴 신규(미측정)", "앨범 버전 수 — 발매 시점 확정 사실(티처 #49 M5: 884 가 잘못 뺐다)"),
    ("아이돌", "unit_price"): ("🔴 신규(미측정)", "단가 37값 — 발매 시점 확정(티처 #49 M5)"),
    ("앱", "updated"): ("사후", "갱신일"),
    ("앱", "y_rating_count"): ("라벨", "y_ 접두"),
    ("앱", "avg_rating"): ("사후", "읽은 시점 평점"),
    ("앱", "artist"): ("신규(판 밖)", "개발사 1,321값 — 시간 게이트 통과이나 **앱은 판 도메인이 아니라 집 밖 짝**"),
    ("앱", "n_device"): ("신규(판 밖)", "지원 기기 수 — 동일(짝 전용)"),
    ("앱", "n_lang"): ("장부소진", "SPEC `mob_nlang`"),
    ("앱", "price"): ("장부소진", "게임 전용 축 `price` 로 등재"),
    ("앱", "size_mb"): ("장부소진", "노트 775 목록"),
    ("앱", "n_genre"): ("장부소진", "SPEC `mob_ngenre`"),
    ("앱", "genres"): ("텍스트", "장르 리스트"),
    ("앱", "n_shot"): ("수집메타", "스크린샷 수"),
    ("앱", "advisory"): ("장부소진", "SPEC `mob_advisory`"),
    ("앱", "langs"): ("텍스트", "언어 리스트"),
    ("앱", "_genre"): ("수집메타", "수집 분류"),
    ("앱", "_list_release"): ("수집메타", "수집 목록 메타"),
}


def main():
    cen = json.load(open(ROOT / "runners/out884_colcensus_fix.json"))
    spec = {(d, f) for d, _a, _r, f, _c, _n in RA.SPEC}
    rows, missing = [], []
    for dom, v in cen["도메인"].items():
        for r in v.get("미사용 후보", []):
            leaf = r["필드"].split(".")[-1]
            key = (dom, leaf)
            if key in spec:
                cat, why = "SPEC소진", f"rawaxes.SPEC 등재"
            elif key in V:
                cat, why = V[key]
            else:
                cat, why = None, None
                missing.append(f"{dom}.{leaf}")
            rows.append({"도메인": dom, "판 도메인": dom in BOARD, "필드": r["필드"],
                         "채움": r["채움"], "값 가짓수": r["값 가짓수"],
                         "부류": cat, "사유": why, "표본": r["표본"][:2]})
    if missing:
        print(json.dumps({"판정 없는 행": missing}, ensure_ascii=False), flush=True)
        raise SystemExit("눈 판정 없인 저장 없음 — V 를 채워라(881 양식)")
    from collections import Counter
    cnt = Counter(r["부류"] for r in rows)
    new_board = [r for r in rows if r["부류"].startswith(("신규", "🔴 신규")) and r["판 도메인"]]
    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "왜": "티처 #49 치명 2 — 884 B 절이 판정 필드를 산출물에 안 남겨 '신규 13'이 재구성 불가였다",
        "행": len(rows), "부류 계수": dict(cnt),
        "🔴 판 도메인 신규": [{k: r[k] for k in ("도메인", "필드", "채움", "부류", "사유")}
                       for r in new_board],
        "판 도메인 신규 수": len(new_board),
        "전체 표": rows,
    }
    with open(ROOT / "runners/out885_bverdict.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "전체 표"},
                     ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
