"""축의 **측정 시점** --- 세 번째 누수 층.

노트 117이 누수 가드 둘을 세웠다. ① 라벨과의 상관이 0.70 이상이면 차단
② 라벨을 만든 플랫폼의 계수기에서 나온 축은 차단. 노트 141에서 셋째가
빠져 있다는 것을 알았다. **그 값을 언제 알 수 있나.**

두 사례가 있었고 둘 다 가드 둘을 통과했다.

    kitsu_rating · kitsu_rank   세계애니에서 두 기간 다 +0.41. Kitsu 는
      AniList 와 다른 플랫폼이고 라벨 상관도 0.41 이라 둘 다 통과한다.
      그런데 Kitsu 순위는 **지금 긁은 스냅샷**이다 --- 작품이 나오기 전에는
      없다. 쓰면 판이 +0.045 오른다.

    웹툰 finished              노트 138 이 ``플래그 하나가 축 다섯을
      이긴다''고 쓴 그 플래그다. 완결 여부는 **끝나야 안다.** 사전에 아는
      연령등급으로 바꾸면 +0.319 가 +0.153 이 되고 축 다섯(+0.202)이 이긴다.

그래서 축마다 시점을 적어 둔다. 적지 않은 축은 **쓰지 않는다** --- 모르면
막는 쪽이 맞다(둘 다 모르는 채로 통과했다).
"""
from __future__ import annotations

# 사전(PRE)   예측 시점에 알 수 있다. 써도 된다.
# 사후(POST)  결과가 나온 뒤에야 알 수 있다. 쓰면 안 된다.
# 정적(STATIC) 시점과 무관하다(작품 자체의 성질). 써도 된다.
PRE, POST, STATIC = "사전", "사후", "정적"

# 근거의 무게 --- 노트 143 이 셋을 갈랐다.
#   측정   자료로 직접 확인했다 (예: 검색 축은 오픈 이전 창에서만 계산)
#   구조   수집 방식에서 따라 나온다 (예: Kitsu 필드는 현재 스냅샷)
#   상식   자료 밖의 판단 (예: 앱스토어 목록은 갱신된다)
# 상식에만 기댄 항목은 뒤집힐 수 있다. 실제로 노트 142 의 판정이 노트 143
# 에서 자료 검정에 반증됐고, 그래도 막기로 한 것은 비용이 쌌기 때문이다.

WHEN = {
    # 손으로 매긴 축 --- 기획서에서 읽는다
    "target_breadth": (PRE, "기획서 태깅"),
    "venue_prominence": (PRE, "기획서 태깅"),
    "entry_friction": (PRE, "기획서 태깅"),
    "media_push": (PRE, "기획서 태깅"),
    # 도메인 전용 범주 축(노트 285 · 309) --- 둘 다 등록 시점에 정해진다
    "mkt_cat": (PRE, "시장 팝업 업종 --- 기획 시점"),
    "fund_cat": (PRE, "펀딩 범주 --- 프로젝트 등록 시"),
    "anime_medium": (PRE, "애니 매체 --- 제작 단계 결정(노트 321)"),
    # 원천 레코드에서 캐낸 전용 축 열(노트 324) --- 전부 출시/등록 시점 확정
    "mob_advisory": (PRE, "모바일 연령 등급 --- 출시 시점"),
    "mob_ngenre": (PRE, "모바일 장르 수 --- 출시 시점"),
    "mob_nlang": (PRE, "모바일 지원 언어 수 --- 출시 시점"),
    "wt_agetype": (PRE, "웹툰 이용 등급 --- 연재 시작 시점"),
    "ani_quarter": (PRE, "애니 방영 분기 --- 편성 시점"),
    "ani_studio": (PRE, "애니 제작사 --- 제작 시점"),
    "wa_ngenre": (PRE, "세계애니 장르 수 --- 등록 시점"),
    "wa_source": (PRE, "세계애니 원작 매체 --- 기획 시점"),
    "wa_studio": (PRE, "세계애니 제작사 --- 제작 시점"),
    "fund_maxprice": (PRE, "펀딩 최고 후원가 --- 등록 시점"),
    "goods_scale": (PRE, "기획서 태깅"),
    # 게임 전용
    "price": (PRE, "출시 시점 확정"),
    "age_rating": (PRE, "출시 시점 확정"),
    "ram_gb": (PRE, "출시 시점 확정"),
    "n_category": (PRE, "출시 시점 확정"),
    # 검색 --- 오픈 이전 창에서만 계산(노트 128)
    "trend_level": (PRE, "오픈 이전 12주"),
    "trend_momentum": (PRE, "오픈 이전 12주"),
    "trend_volatility": (PRE, "오픈 이전 12주"),
    "trend_peak_ratio": (PRE, "오픈 이전 12주"),
    # 위키 조회수 --- 시작일 이전 90일 창에서만 계산(노트 149).
    # **Kitsu 축과 결정적으로 다른 점**: Kitsu 는 지금 긁은 스냅샷이라 오픈
    # 전에 존재하지 않았고, 위키 조회수는 날짜별 시계열이라 오픈 이전만
    # 잘라낼 수 있다. 잘라낸 것이 창의 정의 자체다.
    "wiki_level": (PRE, "시작일 이전 90일"),
    "wiki_momentum": (PRE, "시작일 이전 90일"),
    "wiki_volatility": (PRE, "시작일 이전 90일"),
    "wiki_peak_ratio": (PRE, "시작일 이전 90일"),
    # 태그 내용 --- 사후 표지를 거른 뒤의 큐레이션 태그(노트 255).
    # 지금 긁은 스냅샷이라 창을 잘라낼 수 없지만, 쌓이는 것이라면 옛 작품이
    # 태그가 더 많아야 하는데 태그 수가 연도와 +0.369 다(노트 239) --- 누적이
    # 아니라 태깅 체계의 시대 효과다. 쌓이는 유일한 표지인 ``완결''은
    # tagaxes.POSTHOC 에서 뺐다(붙은 1,271건이 전부 finished=True).
    "tag_c1_웹툰": (PRE, "출시 시점 큐레이션 태그 (완결 표지 제외)"),
    "tag_c3_웹툰": (PRE, "출시 시점 큐레이션 태그 (완결 표지 제외)"),
    "tag_c2_애니": (PRE, "기획 시점 태그 · 장르 · 매체"),
    "tag_c3_애니": (PRE, "기획 시점 태그 · 장르 · 매체"),
    # ── 노트 549 에서 **미등록 일곱**을 채웠다 ────────────────────────────
    #
    # ``g_when`` 이 ``사후 (도메인,축) 11쌍`` 으로 **떨어지고 있었다.** 규약이
    # ``적지 않은 축은 쓰지 않는다`` 이므로 미등록은 곧 사후 판정이다.
    # 원인은 새 축이 아니라 **장부가 코드 뒤에 처졌다**는 것이다 ---
    # ``tagaxes.SPEC`` 이 노트 344 · 345 에서 웹툰 $(1,3,\textbf{4})$ ·
    # 모바일 $(2,3,\textbf{1})$ · 세계애니 신규로 넓어졌고 ``genaxes`` 가
    # 노트 419 에서 들어왔는데, 여기를 같이 안 고쳤다. 노트 546 과 같은 종류다.
    #
    # **추정하지 않고 노트 239 의 누적 검사를 다시 돌렸다**(토큰 수가 연도와
    # 어떻게 붙나 --- 음수로 크면 옛 작품이 더 많다 = 쌓인다 = 사후):
    #
    #     모바일(genres+langs)   **+0.0023**   평평하다
    #     세계애니(genres)        $-0.0900$
    #     애니(tags+genres)      $-0.2557$    **이미 PRE 로 등록된 것**
    #     웹툰(tags)             $+0.5635$
    #     gen 갈래 수            $-0.04 \sim +0.19$ (다섯 도메인)
    #
    # 새로 다는 것이 전부 **이미 통과한 애니($-0.2557$)보다 순하다.** 근거의
    # 무게는 ``측정``이다.
    "tag_c4_웹툰": (PRE, "출시 시점 큐레이션 태그 (노트 345 · 완결 표지 제외)"),
    "tag_c1_모바일": (PRE, "출시 시점 장르 · 지원 언어 (노트 344)"),
    "tag_c2_모바일": (PRE, "출시 시점 장르 · 지원 언어"),
    "tag_c3_모바일": (PRE, "출시 시점 장르 · 지원 언어"),
    "tag_c2_세계애니": (PRE, "등록 시점 장르 (노트 344)"),
    "tag_c3_세계애니": (PRE, "등록 시점 장르"),
    # 공유 갈래 눈금(노트 419). 갈래는 기획 단계에 정해지고 누적 무늬가 없다.
    # ``wa_ngenre`` · ``mob_ngenre`` 가 같은 필드로 이미 PRE 다.
    "gen": (PRE, "갈래 --- 기획 시점 (도메인 가로지르는 공유 눈금)"),
    # 연재 요일 · 연령 등급 · 작가 수 --- 연재 시작에 정해진다(노트 260).
    # daily_pass 는 finished 와 +0.841 이라 뺐다.
    #
    # **이 사전 판정이 두 해 동안 틀려 있었다**(노트 546). ``days`` 는 API 의
    # 현재 스냅샷이고, 매일+ 로 옮겨간 작품은 요일 로스터에서 빠지면서
    # 월요일로 떨어진다 --- 완결·매일+ 조각만 월요일 27.5%(나머지 둘은 균등
    # 14.5%)다. 그래서 ``meta_c3_웹툰`` 이 사실상 ``월요일이냐''(적재 0.900)
    # 였고, 유보에서 **월요일↔매일+ +0.4688 · 매일+↔완결 +0.8619** ---
    # **위에서 손으로 뺀 그 열이 이 성분을 통해 돌아와 있었다.**
    # 이 파일 맨 위 독스트링이 ``웹툰 finished'' 를 이 층을 만든 두 사례 중
    # 하나로 적고 있다는 점에서 값이 두 번 청구된 셈이다.
    #
    # 노트 547 에서 ``tagaxes.STALE`` 로 **오염된 1,978행에서만 days 를
    # 마스킹**했다. 고친 뒤 meta_c3 의 완결 상관이 +0.3303 -> **+0.0299**
    # 다. 판은 0.4908 -> **0.4812** 로 내려갔고 그것이 새 기준선이다 ---
    # 성능 하락이 아니라 그동안의 과대 보고다(노트 306 과 같은 처분).
    "meta_c0_웹툰": (PRE, "연령 등급 · 작가 수 · 연재 요일(매일+ 행 제외)"),
    "meta_c3_웹툰": (PRE, "연령 등급 · 작가 수 · 연재 요일(매일+ 행 제외)"),
    # 팝업 전용 --- 프로젝트 레코드의 ``conditions'' 는 계약 · 기획 시점에
    # 확정되는 조건이다(노트 276). 넷이 하나였던 경쟁 열에서는 장소에
    # **쌓이는** ``이전 개최''를 안 고르고 동시 개최(1km)를 골랐다 ---
    # ``ingest/competition.py`` 가 오픈 **이전에 이미 열려 있던** 팝업만 센다.
    # 넷 다 연도 순위 상관이 |·|<0.13 이라 가드 쌓임의 문턱에서 멀다.
    # ``기간 일수''는 검사를 통과했는데도 뺐다 --- 라벨 y_perday 의 **분모**다
    # (``state/dataset_v2.py`` 가 이미 그렇게 적어 뒀다).
    "pop_comp": (PRE, "기획 시점 1km 내 동시 개최 수"),
    "pop_wkend": (PRE, "기간에서 계산 --- 주말 비중"),
    "pop_holid": (PRE, "기간에서 계산 --- 연휴 일수"),
    "pop_stores": (PRE, "계약 매장 수"),
    # 달력 --- 날짜에서 계산(노트 130)
    "cal_dow_sin": (PRE, "날짜"), "cal_dow_cos": (PRE, "날짜"),
    "cal_weekend": (PRE, "날짜"), "cal_month_sin": (PRE, "날짜"),
    "cal_month_cos": (PRE, "날짜"), "cal_holiday_gap": (PRE, "날짜"),
    # 집단 표지(노트 138) --- 여기가 갈린다
    "grp": (PRE, "도메인마다 다름 --- grpaxes.SPEC 참고"),
    # 후보 축(노트 116)
    "emb0": (STATIC, "설명문"), "emb1": (STATIC, "설명문"),
    "emb2": (STATIC, "설명문"), "emb3": (STATIC, "설명문"),
    "emb4": (STATIC, "설명문"), "emb5": (STATIC, "설명문"),
    "emb6": (STATIC, "설명문"), "emb7": (STATIC, "설명문"),
    "txt_len": (STATIC, "설명문"), "txt_nsent": (STATIC, "설명문"),
    "txt_slen": (STATIC, "설명문"), "txt_ttr": (STATIC, "설명문"),
    "txt_digit": (STATIC, "설명문"),
    "img_bright": (STATIC, "표지"), "img_sat": (STATIC, "표지"),
    "img_edge": (STATIC, "표지"), "img_ent": (STATIC, "표지"),
    "img_std": (STATIC, "표지"), "imgpc0": (STATIC, "표지"),
    "imgpc1": (STATIC, "표지"),
    # **사후** --- 쓰면 안 된다
    "rating": (POST, "현재 평점 스냅샷"),
    "kitsu_rating": (POST, "Kitsu 현재 평점"),
    "kitsu_rank": (POST, "Kitsu 현재 순위"),
    "rating_2plat": (POST, "두 플랫폼 현재 평점"),
    "favourites": (POST, "현재 즐겨찾기 수 (노트 117 이 이미 차단)"),
    "trending": (POST, "현재 급상승 (노트 117)"),
    "popularity": (POST, "현재 인기 (노트 117)"),
}

# 집단 표지는 도메인마다 시점이 다르다
GROUP_WHEN = {
    "웹툰": (POST, "finished --- 완결 여부는 끝나야 안다"),
    "모바일": (PRE, "가격 --- 출시 시점 확정"),
    "애니": (PRE, "매체 --- 기획 시점 확정"),
    "세계애니": (PRE, "포맷 --- 기획 시점 확정"),
    "만화": (PRE, "국가 --- 기획 시점 확정"),
    "게임": (PRE, "무료 여부 --- 출시 시점"),
    "펀딩": (PRE, "카테고리 --- 개설 시점"),
    "도서": (PRE, "출판사 --- 출간 시점"),
}


# (축, 도메인) 예외 --- 시점은 축의 성질만이 아니다(노트 142).
# 앱스토어 설명·스크린샷은 계속 갱신되므로 모바일에서는 글·그림 축이 사후다.
# 실측: 오래된 절반의 |r| 평균이 0.224, 최근 절반이 0.129 (차 +0.095).
# 나머지 일곱 도메인은 차가 ±0.02 안이다 --- 애니 시놉시스·책 소개·펀딩
# 페이지는 안 바뀐다.
# 근거의 무게를 구분한다(노트 143). 자료로 확인한 것과 상식으로 판단한 것은
# 다르다 --- 모바일의 나이차는 실재하지만(이중차분 +0.059) 기제가 설명문
# 갱신이라는 직접 증거는 반증됐다(출시 연도를 통제하니 부호가 뒤집혔다).
# 그래도 막는 것은 ``모르면 막는다''(노트 141)와 상식에 기댄 것이고,
# 비용이 판 +0.006 뿐이다.
# ── 채우는 쪽 표(노트 264) ─────────────────────────────────────────────
#
# ``WHEN`` 은 축 **이름**에 뜻을 붙인다. 그런데 손 축 다섯은 도메인마다 **다른
# 원본 필드**로 채워지고, 노트 262 · 263이 그 틈에서 새는 축을 둘 찾았다 ---
# 웹툰 ``entry_friction`` 이 ``daily_pass``(완결 표지)였고 ``goods_scale`` 이
# ``n_episode``(연재 중 쌓임)였다. 이름만 보는 표로는 못 잡는다.
#
# 그래서 (도메인, 축) --> 원본 필드를 적어 둔다. 가드 **쌓임**(g_accrual)이
# 이 표를 읽어 레코드에서 그 필드를 꺼내 두 가지를 잰다:
#   1. 연도와의 순위 상관 --- 쌓이는 양은 옛것일수록 크다
#   2. 유보 평균 / 학습 평균 --- 쌓이는 양은 최근이 작다
# 라벨을 안 본다.
SOURCE = {
    ("웹툰", "target_breadth"): "n_tag",
    ("웹툰", "venue_prominence"): "n_day",
    ("웹툰", "entry_friction"): "daily_pass",     # 막힘(노트 262)
    ("웹툰", "goods_scale"): "n_episode",          # 막힘(노트 263)
    ("애니", "target_breadth"): "age",
    ("애니", "entry_friction"): "price",
    ("애니", "media_push"): "is_dubbed",
    ("모바일", "target_breadth"): "n_lang",
    ("모바일", "entry_friction"): "price",
    ("모바일", "media_push"): "n_shot",
    ("모바일", "goods_scale"): "size",
    ("도서", "entry_friction"): "price",
    ("펀딩", "entry_friction"): "min_price",
    ("만화", "target_breadth"): "n_tag",
    ("만화", "entry_friction"): "is_adult",
    ("만화", "goods_scale"): "n_chapter",
    ("세계애니", "target_breadth"): "n_tag",
    ("세계애니", "entry_friction"): "is_adult",
    ("세계애니", "goods_scale"): "n_episode",
    ("게임", "n_category"): "n_category",
    ("게임", "goods_scale"): "n_category",
    ("모바일", "goods_scale"): "size_mb",
    ("도서", "goods_scale"): "book_format",
    ("도서", "target_breadth"): "n_genre",
    ("펀딩", "target_breadth"): "n_reward",
    ("펀딩", "goods_scale"): "n_reward",
    ("만화", "goods_scale"): "n_chapter",
    ("애니", "target_breadth"): "age",
    ("애니", "goods_scale"): None,     # 대응물 없음 --- 마스크 0
}

# ``venue_prominence`` 는 대개 **n_prior**(창작자의 사전 작품 수)로 채우는데
# 그것은 레코드 필드가 아니라 표본 안에서 시간 인과로 세는 파생량이라 가드가
# 못 읽는다(도서 · 펀딩 · 모바일 · 만화 · 세계애니). 사전성은 계산 방식이
# 보장한다 --- ``그 작품 이전''만 센다. 아이돌 · 게임의 ``log_mean`` 도 같다.
DERIVED = {("도서", "venue_prominence"), ("펀딩", "venue_prominence"),
           ("모바일", "venue_prominence"), ("만화", "venue_prominence"),
           ("세계애니", "venue_prominence"), ("아이돌", "venue_prominence"),
           ("게임", "media_push"), ("아이돌", "media_push"),
           # 제작사 사전 작품 수 --- 표본 안 시간 인과로 센다(그 작품 이전만)
           ("애니", "venue_prominence"),
           # 합성 --- 여러 필드의 가중 평균이라 한 필드로 못 잡는다
           ("게임", "target_breadth"),      # 언어 수 · 장르 수 · 플랫폼 수
           ("아이돌", "target_breadth"),     # 인원 · 서바이벌 여부 · 성별
           ("아이돌", "entry_friction"),     # 앨범 정가(am.unit_price)
           ("아이돌", "goods_scale")}        # 앨범 버전 수(am.versions)

# **마스크 0** --- 그 도메인에 대응 필드가 아예 없어 축이 꺼져 있다.
# 노트 20 · 22가 ``도메인 간 정의 불일치''로 남긴 자리다. 가드가 볼 것이 없다.
MASKED = {("웹툰", "media_push"), ("도서", "media_push"),
          ("펀딩", "media_push"), ("만화", "media_push"),
          ("세계애니", "media_push"),
          # 게임 가격은 허들이 아니라 규모 신호라 껐다(노트 9와 같은 결론)
          ("게임", "entry_friction"),
          ("게임", "venue_prominence")}

# 레코드 파일 --- 가드가 원본 필드를 꺼내 볼 곳
RECORDS = {"웹툰": "webtoon_records.json", "애니": "anime_records.json",
           "모바일": "mobile_records.json", "도서": "book_records.json",
           "펀딩": "funding_records.json", "만화": "manga_records.json",
           "세계애니": "wanime_records.json", "게임": "game_records.json",
           "아이돌": "idol_records.json"}


DOMAIN_POST = {
    "모바일": ({"emb", "txt_", "img_", "imgpc"},
             "앱스토어 목록은 갱신된다 [상식 · 자료 검정은 반증됨]"),
}


def when_in(axis: str, domain: str) -> tuple:
    """도메인까지 보고 시점을 정한다."""
    spec = DOMAIN_POST.get(domain)
    if spec and any(axis.startswith(p) for p in spec[0]):
        return POST, spec[1]
    return when(axis)


def when(axis: str) -> tuple:
    """(시점, 근거). 등록 안 된 축은 사후로 본다 --- 모르면 막는다."""
    return WHEN.get(axis, (POST, "등록되지 않은 축 --- 모르면 막는다"))


def usable(axis: str) -> bool:
    return when(axis)[0] != POST


def audit(names, domain: str | None = None) -> dict:
    """축 목록을 훑어 사후인 것을 골라낸다. 도메인을 주면 예외까지 본다."""
    bad = {}
    for a in names:
        w, why = (when_in(a, domain) if domain else when(a))
        if w == POST:
            bad[a] = why
    return bad


def audit_data(names_by_domain: dict) -> dict:
    """{도메인: 축목록} 을 통째로 --- 도메인별 예외를 반영한다."""
    out = {}
    for d, nm in names_by_domain.items():
        b = audit(nm, d)
        if b:
            out[d] = b
    return out
