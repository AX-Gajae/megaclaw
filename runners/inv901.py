"""노트 901 ② 재고 조사 + ④ 배선 검사.

사전등록: `docs/prereg_901_intervention.md` (커밋 ae0ed6c49 · 2026-08-11T03:21:42+09:00)

🔴 **효과 크기를 안 낸다.** 여기서 나오는 수는 개수 · 값 가짓수 · 결측 수 · 분모뿐이다.
🔴 **분모 딱지**: D1 원천 레코드 수 · D2 축행 수 · D3 판 채점 유보행 수 ·
   D4 챔피언 배선 도메인 행 수. 딱지가 다른 두 수를 안 이어 붙인다.

실행: python3 runners/inv901.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

T0 = time.time()
START = dt.datetime.now().isoformat(timespec="seconds")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha_dir(d: Path) -> tuple[str, int]:
    """디렉터리 전량의 결합 sha256(파일명 정렬) + 파일 수."""
    h = hashlib.sha256()
    fs = sorted(d.glob("*.json"))
    for f in fs:
        h.update(f.name.encode())
        h.update(sha(f).encode())
    return h.hexdigest(), len(fs)


# ── 원천 정의 ──────────────────────────────────────────────────────────
# (도메인, 원천 종류, 경로, 축 파일, 결과 필드)
SRC = {
    "팝업":     ("dir",  "data/records",                     None,
                 ["outcome.totals.visitors", "outcome.totals.sales_krw",
                  "outcome.totals.rev_mm_recognized"]),
    "시장팝업": ("dir",  "data/market_records",              "data/state/market_axes.json",
                 ["outcome.visitors_total", "outcome.sales_krw"]),
    "아이돌":   ("dir",  "data/idol_records",                "data/state/idol_axes.json",
                 ["chodong"]),
    "게임":     ("json", "data/state/game_records.json",     "data/state/game_axes.json",
                 ["y_w30", "y_raw"]),
    "도서":     ("json", "data/state/book_records.json",     "data/state/book_axes.json",
                 ["sales_point"]),
    "펀딩":     ("json", "data/state/funding_records.json",  "data/state/funding_axes.json",
                 ["y_backers"]),
    "웹툰":     ("json", "data/state/webtoon_records.json",  "data/state/webtoon_axes.json",
                 ["y_favorite"]),
    "애니":     ("json", "data/state/anime_records.json",    "data/state/anime_axes.json",
                 ["y_review"]),
    "모바일":   ("json", "data/state/mobile_records.json",   "data/state/mobile_axes.json",
                 ["y_rating_count"]),
    "만화":     ("json", "data/state/manga_records.json",    "data/state/manga_axes.json",
                 ["y_popularity"]),
    "세계애니": ("json", "data/state/wanime_records.json",   "data/state/wanime_axes.json",
                 ["y_popularity"]),
    # 🔴 영화만 결과가 **다른 파일**에 있다(`kobis_axes.json` 의 `y`).
    #    `load_records` 가 `code` 로 붙여 넣는다 — 「같은 레코드」의 뜻을
    #    영화에서만 **두 파일의 결합**으로 넓힌 것이고, 그 사실을 산출물에 적는다.
    "영화":     ("jsonl", "data/ingest/kobis/axes_raw_897.jsonl", "data/state/kobis_axes.json",
                 ["_y_from_axes"]),
}

# ── 후보 열 — 사전등록 §2 의 기준과 경계 규칙으로 등급을 매긴다 ────────
# (열, 등급, 형, 이유)   형: b=이진/범주 · c=연속 · l=리스트(길이) · d=날짜
CAND = {
"팝업": [
 ("intervention.attributes.entry_friction",  "T1","c","입장 허들 — 운영자 설계(사람 태그)"),
 ("intervention.attributes.goods_scale",     "T1","c","굿즈 규모 — 운영자 설계"),
 ("intervention.attributes.media_push",      "T1","c","미디어 투입 — 운영자 설계"),
 ("intervention.attributes.target_breadth",  "T1","c","타깃 폭 — 운영자 설계"),
 ("intervention.attributes.photo_zones",     "T1","c","포토존 수 — 운영자 설계"),
 ("intervention.attributes.giveaway_qty",    "T1","c","증정품 수량 — 운영자 설계"),
 ("intervention.attributes.staff_count",     "T1","c","투입 인력 — 운영자 설계"),
 ("intervention.attributes.operating_hours_per_day","T1","c","일 운영시간 — 운영자 설계"),
 ("intervention.attributes.planned_operating_days","T1","c","계획 운영일수 — 운영자 설계"),
 ("intervention.attributes.capacity_per_session","T1","c","회당 수용 — 운영자 설계"),
 ("intervention.attributes.area_sqm",        "T1","c","면적 — 운영자 결정(경계 규칙: 면적=T1)"),
 ("intervention.attributes.experience_density","T1","c","체험 밀도 — 운영자 설계"),
 ("intervention.attributes.unit_minutes",    "T1","c","1인 체류 설계 — 운영자 설계"),
 ("intervention.attributes.throughput_units","T1","c","처리량 설계 — 운영자 설계"),
 ("intervention.attributes.collab_strength", "T2","c","협업 강도 — 계약 산물(경계: 퍼블리셔 규칙 준용)"),
 ("intervention.attributes.ip_awareness",    "T3","c","IP 인지도 — 개입이 아니라 사전 상태"),
 ("intervention.attributes.season_fit",      "T3","c","계절 적합 — 자연·외생"),
 ("intervention.attributes.venue_prominence","T2","c","매장 노출도 — 장소 선택은 운영자지만 노출도는 장소의 성질"),
 ("intervention.attributes.host_daily_traffic","T3","c","숙주 유동 — 자연·외생"),
 ("intervention.experience_elements",        "T1","l","체험 요소 목록 — 운영자 설계"),
 ("intervention.promotions",                 "T1","l","프로모션 목록 — 운영자 설계"),
 ("intervention.staging_tags",               "T1","l","연출 태그 — 운영자 설계"),
 ("conditions.fee_structure.type",           "T1","b","수수료 구조 — 계약 설계(운영자·건물주 공동 결정)"),
 ("conditions.scale.store_count",            "T1","c","매장 수 — 경계 규칙: 매장 수=T1"),
 ("conditions.area_pyeong",                  "T1","c","면적(평) — 경계 규칙: 면적=T1"),
 ("conditions.period.days",                  "T1","c","기간 길이 — 경계 규칙: 기간=T1"),
 ("conditions.capacity.access_type",         "T1","b","입장 방식(예약/개방) — 운영자 설계"),
 ("conditions.location.venue_type",          "T2","b","장소 유형 — 고름은 운영자, 성질은 장소의 것"),
 ("conditions.season",                       "T3","b","계절 — 자연·외생(제외 목록 3)"),
 ("conditions.derived.competition.comp_within_500m_open","T3","c","경쟁 — 자연·외생(교란 후보)"),
 ("conditions.derived.ip_history.prior_count","T3","c","IP 이력 — 개입이 아니라 사전 상태(교란 후보)"),
 ("outcome.plan_visitors_expected",          "T3","c","계획 방문자 — 기대치이지 개입이 아니다"),
 ("intervention.attributes.없는열_카나리아", "CAN","c","🔴 카나리아 — 이 이름은 원천에 없어야 한다"),
],
"시장팝업": [
 ("intervention.is_free_entry",       "T1","b","무료입장 — 운영자 결정"),
 ("intervention.reservation_required","T1","b","예약 필수 — 운영자 결정"),
 ("intervention.promotions",          "T1","l","프로모션 목록 — 운영자 설계"),
 ("intervention.experience_elements", "T1","l","체험 요소 — 운영자 설계"),
 ("conditions.multi_store",           "T1","b","다점포 — 경계 규칙: 다점포=T1"),
 ("conditions.area_pyeong",           "T1","c","면적 — 경계 규칙: 면적=T1"),
 ("conditions.derived.duration.days", "T1","c","기간 길이 — 경계 규칙: 기간=T1"),
 ("conditions.venue_type",            "T2","b","장소 유형 — 팝업과 같은 이유"),
 ("ip_or_collab",                     "T2","b","IP/협업 — 계약 산물"),
 ("category",                         "T3","b","카테고리 — 정체성 고정(제외 목록 4)"),
 ("conditions.derived.ip_history.prior_count","T3","c","IP 이력 — 사전 상태(교란 후보)"),
 ("intervention.없는열_카나리아",     "CAN","b","🔴 카나리아"),
],
"아이돌": [
 ("member_count",   "T1","c","멤버 수 — 기획사 결정"),
 ("survival_show",  "T1","b","서바이벌 출신 — 기획사 결정"),
 ("debut_album",    "T2","b","데뷔 앨범 — 결정이지만 레코드 정체성에 붙는다"),
 ("agency",         "T2","b","소속사 — 경계 규칙: 퍼블리셔·소속사=T2"),
 ("pre_debut_signals.preorder","T3","c","선주문 — 결과의 선행 관측이지 개입이 아니다"),
 ("pre_debut_signals.teaser_views","T3","c","티저 조회 — 관객 반응(결과)"),
 ("pre_debut_signals.showcase_scale","T1","b","쇼케이스 규모 — 기획사 결정"),
 ("gender",         "T3","b","성별 구성 — 정체성 고정"),
 ("is_group",       "T3","b","그룹 여부 — 정체성 고정"),
 ("없는열_카나리아","CAN","b","🔴 카나리아"),
],
"게임": [
 ("price_krw",  "T1","c","가격 — 경계 규칙: 가격=T1"),
 ("is_free",    "T1","b","무료 여부 — 가격 결정의 이진형"),
 ("n_dlc",      "T1","c","DLC 수 — 퍼블리셔 결정"),
 ("n_lang",     "T1","c","지원 언어 수 — 경계 규칙: 언어=T1"),
 ("n_platform", "T1","c","지원 플랫폼 수 — 경계 규칙: 플랫폼=T1"),
 ("n_category", "T2","c","스팀 카테고리 수 — 일부는 기능 신고, 일부는 플랫폼 부여"),
 ("publishers", "T2","b","퍼블리셔 — 경계 규칙: 퍼블리셔=T2"),
 ("developers", "T2","b","개발사 — 퍼블리셔 준용"),
 ("genres",     "T3","l","장르 — 정체성 고정"),
 ("release_date","T1","d","출시일 — 시점 선택은 운영자 결정. ⚠ 탈추세 변수로 이미 소비된다"),
 ("없는열_카나리아","CAN","c","🔴 카나리아"),
],
"도서": [
 ("price",       "T1","c","정가 — 경계 규칙: 가격=T1"),
 ("pages",       "T1","c","면수 — 출판사·저자 결정"),
 ("book_format", "T1","b","판형/제본 — 출판사 결정"),
 ("height_mm",   "T1","c","판형 높이 — 출판사 결정"),
 ("width_mm",    "T1","c","판형 너비 — 출판사 결정"),
 ("weight_g",    "T1","c","무게 — 사양의 결과이나 사양은 운영자 결정"),
 ("publisher",   "T2","b","출판사 — 퍼블리셔 규칙 준용"),
 ("genre",       "T3","b","장르 — 정체성 고정"),
 ("pub_date",    "T1","d","출간일 — 시점 선택. ⚠ 탈추세 변수"),
 ("rating",      "T3","c","평점 — 결과(관객 반응)"),
 ("review_count","T3","c","리뷰 수 — 결과"),
 ("없는열_카나리아","CAN","c","🔴 카나리아"),
],
"펀딩": [
 ("min_price",      "T1","c","최저 후원액 — 경계 규칙: 최저 후원액=T1"),
 ("max_price",      "T1","c","최고 후원액 — 운영자 설계"),
 ("n_reward",       "T1","c","리워드 단계 수 — 운영자 설계"),
 ("n_delivery",     "T1","c","배송 옵션 수 — 운영자 설계"),
 ("n_unlimited",    "T1","c","무제한 리워드 수 — 운영자 설계"),
 ("unlimited_ratio","T1","c","무제한 비율 — 위의 파생이지만 원천 열이다"),
 ("amount",         "T3","c","목표/모금액 — 결과 또는 결과 파생(확인 필요)"),
 ("adult_only",     "T1","b","성인 전용 설정 — 운영자 결정"),
 ("category",       "T2","b","카테고리 — 경계 규칙: 플랫폼에서 고르는 것이면 T2"),
 ("creator",        "T2","b","창작자 — 퍼블리셔 규칙 준용"),
 ("start_date",     "T1","d","시작일 — 시점 선택. ⚠ 탈추세 변수"),
 ("end_date",       "T1","d","종료일 — 캠페인 길이 결정"),
 ("없는열_카나리아","CAN","c","🔴 카나리아"),
],
"웹툰": [
 ("daily_pass", "T1","b","기다리면무료 등 과금 장치 — 플랫폼·작가 결정"),
 ("n_day",      "T1","c","주간 연재 요일 수 — 운영자 결정"),
 ("n_episode",  "T1","c","회차 수 — 운영자 결정. ⚠ 시간에 따라 자란다(사전성 위태)"),
 ("n_tag",      "T1","c","태그 수 — 운영자가 붙인다"),
 ("n_artist",   "T1","c","참여 작가 수 — 운영자 결정"),
 ("level",      "T2","b","등급/레벨 — 플랫폼 부여 가능"),
 ("age_type",   "T3","b","연령등급 — 경계 규칙: 제3자 심의면 T3"),
 ("finished",   "T3","b","완결 여부 — 결과 이후 상태"),
 ("artists",    "T2","b","작가 — 퍼블리셔 규칙 준용"),
 ("start_date", "T1","d","연재 시작일 — 시점 선택. ⚠ 탈추세 변수"),
 ("없는열_카나리아","CAN","c","🔴 카나리아"),
],
"애니": [
 ("is_free",     "T1","b","무료 공개 — 플랫폼·판권자 결정"),
 ("is_dubbed",   "T1","b","더빙 — 운영자 결정"),
 ("is_only",     "T1","b","독점 — 계약 결정"),
 ("price",       "T1","c","가격 — 경계 규칙: 가격=T1"),
 ("n_episode",   "T1","c","회차 수 — 제작 결정"),
 ("n_tag",       "T1","c","태그 수 — 운영자가 붙인다"),
 ("is_original", "T2","b","오리지널 여부 — 정체성에 가깝다"),
 ("production",  "T2","b","제작사 — 퍼블리셔 규칙 준용"),
 ("age",         "T3","b","연령등급 — 제3자 심의"),
 ("genres",      "T3","l","장르 — 정체성 고정"),
 ("medium",      "T3","b","매체 — 정체성 고정"),
 ("avg_rating",  "T3","c","평점 — 결과"),
 ("없는열_카나리아","CAN","c","🔴 카나리아"),
],
"모바일": [
 ("price",     "T1","c","가격 — 경계 규칙: 가격=T1"),
 ("n_lang",    "T1","c","지원 언어 수 — 경계 규칙: 언어=T1"),
 ("n_device",  "T1","c","지원 기기 수 — 경계 규칙: 지원기기=T1"),
 ("n_shot",    "T1","c","스토어 스크린샷 수 — 운영자가 올린다"),
 ("size_mb",   "T1","c","앱 용량 — 개발 결정"),
 ("n_genre",   "T2","c","장르 수 — 스토어에서 고른다"),
 ("advisory",  "T3","b","연령 고지 — 제3자/플랫폼 부여"),
 ("artist",    "T2","b","퍼블리셔 — 경계 규칙"),
 ("updated",   "T3","d","마지막 갱신 — 결과 이후에도 움직인다(사전성 불충족)"),
 ("release_date","T1","d","출시일 — 시점 선택. ⚠ 탈추세 변수"),
 ("없는열_카나리아","CAN","c","🔴 카나리아"),
],
"만화": [
 ("n_chapter","T1","c","화수 — 출판 결정. ⚠ 시간에 따라 자란다"),
 ("n_volume", "T1","c","권수 — 출판 결정. ⚠ 시간에 따라 자란다"),
 ("n_tag",    "T1","c","태그 수 — 운영자·이용자가 붙인다(귀속 불명 → 아래 주석)"),
 ("format",   "T2","b","형식 — 정체성에 가깝다"),
 ("status",   "T3","b","연재 상태 — 결과 이후 상태"),
 ("is_adult", "T3","b","성인물 — 플랫폼 분류"),
 ("authors",  "T2","b","작가 — 퍼블리셔 규칙 준용"),
 ("country",  "T3","b","국적 — 정체성 고정"),
 ("start_date","T1","d","연재 시작일 — 시점 선택. ⚠ 탈추세 변수"),
 ("없는열_카나리아","CAN","c","🔴 카나리아"),
],
"세계애니": [
 ("n_episode","T1","c","회차 수 — 제작 결정"),
 ("duration", "T1","c","1화 길이 — 제작 결정"),
 ("n_tag",    "T1","c","태그 수"),
 ("format",   "T2","b","형식(TV/극장/OVA) — 유통 결정에 가깝다"),
 ("source",   "T3","b","원작 유형 — 정체성 고정"),
 ("studios",  "T2","b","스튜디오 — 퍼블리셔 규칙 준용"),
 ("is_adult", "T3","b","성인물 — 플랫폼 분류"),
 ("country",  "T3","b","국적 — 정체성 고정"),
 ("start_date","T1","d","방영 시작일 — 시점 선택. ⚠ 탈추세 변수"),
 ("없는열_카나리아","CAN","c","🔴 카나리아"),
],
"영화": [
 ("배급사",  "T2","b","배급사 — 경계 규칙: 퍼블리셔=T2"),
 ("개봉일",  "T1","d","개봉일 — 시점 선택은 배급사 결정. ⚠ 탈추세 변수"),
 ("등급",    "T3","b","상영등급 — 영등위 심의(제3자) → 경계 규칙대로 T3"),
 ("장르",    "T3","b","장르 — 정체성 고정"),
 ("국적 후보","T3","b","국적 — 정체성 고정"),
 ("없는열_카나리아","CAN","b","🔴 카나리아"),
],
}

# 반복 단위(식2 용) — 「같은 IP/브랜드/창작자」의 조작적 키
UNIT = {
 "팝업":     "entities.brand_key",
 "시장팝업": "brand",
 "아이돌":   "agency",
 "게임":     "publishers",
 "도서":     "publisher",
 "펀딩":     "creator_uuid",
 "웹툰":     "artists",
 "애니":     "production",
 "모바일":   "artist_id",
 "만화":     "authors",
 "세계애니": "studio_name",
 "영화":     "배급사",
}
DATEK = {
 "팝업": "conditions.period.from", "시장팝업": "conditions.period_from",
 "아이돌": "debut_date", "게임": "release_date", "도서": "pub_date",
 "펀딩": "start_date", "웹툰": "start_date", "애니": "start_date",
 "모바일": "release_date", "만화": "start_date", "세계애니": "start_date",
 "영화": "개봉일",
}

MISSING = object()


def dig(r, path):
    cur = r
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return MISSING
    return cur


def hashable(v):
    if isinstance(v, list):
        return ("<list>", len(v))
    if isinstance(v, dict):
        return ("<dict>", len(v))
    return v


def load_records(kind, p):
    fp = ROOT / p
    if kind == "dir":
        fs = sorted(fp.glob("*.json"))
        return [json.loads(f.read_text()) for f in fs]
    if kind == "jsonl":
        rs = [json.loads(l) for l in open(fp) if l.strip()]
        if "kobis" in p:      # 🔴 영화만 결과가 다른 파일에 있다 — code 로 붙인다
            ax = json.loads((ROOT / "data/state/kobis_axes.json").read_text())
            for r in rs:
                a = ax.get("KOBIS-" + str(r.get("code")))
                r["_y_from_axes"] = (a or {}).get("y")
        return rs
    d = json.loads(fp.read_text())
    return list(d.values()) if isinstance(d, dict) else list(d)


def main():
    out = {"노트": 901, "사전등록 커밋": "ae0ed6c49799011efab8614c7f7171ae08c7a6bb",
           "사전등록 시각": "2026-08-11T03:21:42+09:00",
           "시작 시각": START,
           "코드 sha256": {"runners/inv901.py": sha(Path(__file__))},
           "🔴 효과 크기": "없음 — 개수·값 가짓수·결측·분모만 낸다"}

    # ── 배선 W-A · W-B · W-E ──────────────────────────────────────────
    wiring = {}
    inputs = {}
    for dom, (kind, p, axp, _o) in SRC.items():
        fp = ROOT / p
        if kind == "dir":
            h, n = sha_dir(fp)
            inputs[p] = {"sha256(결합)": h, "파일 수": n}
        else:
            inputs[p] = {"sha256": sha(fp)}
        if axp:
            inputs[axp] = {"sha256": sha(ROOT / axp)}

    # W-A: 축 파일 경로가 tri_domain 이 실제로 읽는 경로와 같은가
    import state.tri_domain as TD
    td_src = Path(TD.__file__).read_text()
    wa = {}
    for dom, (_k, _p, axp, _o) in SRC.items():
        if not axp:
            wa[dom] = "축 파일 없음(팝업은 npz 경로)"
            continue
        name = Path(axp).name
        in_code = name in td_src
        same = (ROOT / axp).resolve() == (ROOT / "data/state" / name).resolve()
        assert same, f"W-A 경로 대조 실패 {axp}"
        wa[dom] = {"tri_domain.py 에 이 파일명이 있나": in_code,
                   "resolve() 대조": "일치"}
    wiring["W-A 원천 지문·경로"] = wa

    # W-B/W-E: D2 · D3 · D4
    import ff753 as FF
    d0 = FF.shell(FF.base())
    W = d0.weights(2025.0)
    d2 = {}
    for dom, (_k, _p, axp, _o) in SRC.items():
        if axp:
            d2[dom] = len(json.loads((ROOT / axp).read_text()))
    d4 = {d: len(d0.dom[d][2]) for d in d0.dom}
    d3 = {d: int(W[d]) for d in W}
    s3 = sum(d3.values())
    wiring["W-E D3 합"] = s3
    wiring["W-E 대조"] = ("3775 와 일치" if s3 == 3775
                        else f"🔴 3775 와 다르다 ({s3}) — 맞추지 않고 적는다")
    # 🔴 D3 는 두 배선에서 다른 값이 나온다 — 그 사실을 산출물에 박는다
    from lab import harness as HN
    raw = HN.load()
    d3_raw = {d: int(raw.rows(d, post=True, labeled=True, T=2025.0).sum())
              for d in raw.dom}
    wiring["🔴 D3 는 배선에 따라 다르다"] = {
        "챔피언 배선 ff753.shell(base())": {"합": s3, "도메인별": d3},
        "생 harness.load()": {"합": sum(d3_raw.values()), "도메인별": d3_raw},
        "차": {d: d3_raw[d] - d3.get(d, 0) for d in d3_raw if d3_raw[d] != d3.get(d, 0)},
        "뜻": "판 정본 3,775 는 **챔피언 배선** 값이다. 생 load() 로 세면 다른 수가 나온다 — 인용할 때 배선을 병기해야 한다",
    }
    wiring["W-B D2 대 D4"] = {
        d: {"D2 축행": d2.get(d), "D4 도메인 행": d4.get(d),
            "같나": (d2.get(d) == d4.get(d))} for d in sorted(d4)}

    # ── ② 재고 조사 ──────────────────────────────────────────────────
    inv = {}
    canary = {}
    for dom, (kind, p, axp, outs) in SRC.items():
        recs = load_records(kind, p)
        D1 = len(recs)
        cols = {}
        for name, tier, typ, why in CAND[dom]:
            vals = [dig(r, name) for r in recs]
            present = sum(1 for v in vals if v is not MISSING)
            nonnull = [v for v in vals
                       if v is not MISSING and v is not None and v != "" and v != []]
            uniq = Counter(hashable(v) for v in nonnull)
            rec = {"등급": tier, "형": typ, "이유": why,
                   "분모": "D1", "D1": D1,
                   "열 있음": present, "비결측": len(nonnull),
                   "결측(=D1-비결측)": D1 - len(nonnull),
                   "값 가짓수": len(uniq)}
            if present == 0:
                rec["🔴 판정"] = "열 없음 — 「0」이 아니라 「그 이름의 열이 원천에 없다」"
            if typ in ("b", "l") and uniq:
                top = uniq.most_common()
                rec["최소 빈도 값의 행 수"] = top[-1][1]
                rec["상위 5 값"] = [[str(k), v] for k, v in top[:5]]
            elif typ == "c" and uniq:
                rec["최소 빈도 값의 행 수"] = uniq.most_common()[-1][1]
            if name.endswith("카나리아"):
                canary[dom] = rec
            else:
                cols[name] = rec
        # 결과 변수
        oc = {}
        for o in outs:
            vs = [dig(r, o) for r in recs]
            oc[o] = {"분모": "D1", "D1": D1,
                     "비결측": sum(1 for v in vs
                                 if v is not MISSING and v is not None and v != "")}
        # 반복 단위(식2)
        uk, dk = UNIT[dom], DATEK[dom]
        ukeys = []
        for r in recs:
            v = dig(r, uk)
            if isinstance(v, list):
                v = v[0] if v else None
            ukeys.append(None if v in (MISSING, None, "", []) else str(v))
        cu = Counter(k for k in ukeys if k)
        rep_units = {k: v for k, v in cu.items() if v >= 2}
        # 「사전 관측이 있는 레코드」 = 같은 단위에 **더 이른 날짜 + 결과 비결측** 레코드가 있는 행
        dts = [str(dig(r, dk) or "")[:10] for r in recs]
        okout = []
        for r in recs:
            has = False
            for o in outs:
                v = dig(r, o)
                if v is not MISSING and v is not None and v != "":
                    has = True
            okout.append(has)
        prior = 0
        for i, k in enumerate(ukeys):
            if not k or not dts[i]:
                continue
            for j, k2 in enumerate(ukeys):
                if j != i and k2 == k and dts[j] and dts[j] < dts[i] and okout[j]:
                    prior += 1
                    break
        inv[dom] = {"원천": p, "분모 D1": D1,
                    "분모 D2 축행": d2.get(dom), "분모 D3 유보(챔피언)": d3.get(dom),
                    "분모 D4 도메인행": d4.get(dom),
                    "열": cols, "결과 변수": oc,
                    "식2 반복 단위": {
                        "단위 키": uk, "날짜 키": dk,
                        "단위 수(비결측)": len(cu),
                        "레코드 2건 이상인 단위 수": len(rep_units),
                        "🔴 같은 단위의 더 이른 결과 관측이 있는 레코드 수": prior,
                        "분모": "D1", "D1": D1}}
        print(f"{dom}\tD1={D1}\t열 {len(cols)}\t사전관측 있는 행 {prior}", flush=True)

    # W-C / W-D
    wiring["W-C 고른 열이 원천에 있나"] = {
        dom: {n: v["열 있음"] for n, v in inv[dom]["열"].items()}
        for dom in inv}
    wiring["W-D 카나리아"] = {}
    for dom, rec in canary.items():
        ok = rec["열 있음"] == 0 and "🔴 판정" in rec
        assert ok, f"W-D 카나리아 실패 {dom}: 없는 열이 「열 없음」으로 안 나왔다"
        wiring["W-D 카나리아"][dom] = {"열 있음": rec["열 있음"],
                                      "판정": rec.get("🔴 판정"), "통과": True}
    wiring["W-D 통과"] = all(v["통과"] for v in wiring["W-D 카나리아"].values())

    out["입력 sha256"] = inputs
    out["배선 검사"] = wiring
    out["재고"] = inv
    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["초"] = round(time.time() - T0, 1)
    (ROOT / "runners/out901_inventory.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("완료 →", ROOT / "runners/out901_inventory.json")


if __name__ == "__main__":
    main()
