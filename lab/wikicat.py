"""문서 분류가 도메인과 맞는지 본다(노트 179).

**왜 필요한가.** 노트 150이 ``겹침 0인 1위를 그냥 쓰는 것''을 막으려고
겹침 검사를 붙였는데, **검색 통로에만 붙였다.** ``direct()'' 는 제목이
문서 이름과 정확히 같으면 무조건 붙인다 --- 그래서 웹툰 ``해귀''가
임진왜란 문서에, 도서 ``아몬드''가 벚나무속 문서에, 만화 ``Centuria''가
로마 군단 문서에 붙어 있다. 전부 score 1.0 이라 노트 178의 매칭 점수
문턱으로는 보이지 않는다.

**규칙.** 위키백과 분류를 받아서 도메인에 맞는 낱말이 하나라도 있으면
통과, 없으면(또는 분류가 아예 없으면) 결측으로 돌린다. **점수가 아니라
의미로 정한다** --- 판을 보고 문턱을 고르는 것과 성질이 다르다.

**한계.** 낱말 목록은 손으로 만든 것이라 완전하지 않다. 모바일에서
보드게임 원작(``Terra Mystica'')을 오탐하는 것이 확인된 예다."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CATS = Path("data/state/wiki_cats.json")

KEY = {
    "게임": ["video game", "비디오 게임", "게임", "컴퓨터 게임", "board game"],
    "모바일": ["video game", "게임", "board game", "mobile app", "software",
            "앱", "응용 프로그램", "애플리케이션", "card game"],
    "세계애니": ["anime", "manga", "light novel", "visual novel", "video game",
             "애니메이션", "만화", "television seasons", "episode lists",
             "animated television", "animated films", "ova"],
    "애니": ["anime", "manga", "애니메이션", "만화", "라이트 노벨", "게임",
           "video game", "웹툰", "소설", "책 시리즈", "텔레비전 애니메이션"],
    "만화": ["anime", "manga", "애니메이션", "만화", "light novel", "webtoon",
           "television seasons", "episode lists", "comics"],
    "웹툰": ["웹툰", "만화", "webtoon", "manga", "드라마", "소설", "영화",
           "애니메이션", "게임"],
    "도서": ["novel", "소설", "책", "book", "literature", "문학", "만화",
           "수필", "시집", "자서전", "영화", "에세이", "논픽션"],
    "아이돌": ["음악 그룹", "k-pop", "아이돌", "걸 그룹", "보이 그룹", "가수",
            "음반", "보이그룹", "걸그룹", "밴드"],
    "팝업": ["애니메이션", "만화", "웹툰", "게임", "음악 그룹", "k-pop", "아이돌",
           "캐릭터", "브랜드", "소설", "영화", "드라마"],
}


# **머리말만 본다**(노트 179). 분류 이름이 이 낱말로 *끝나면* 그 문서가
# 곧 그것이다 --- ``Video game genres'' 는 장르 문서고 ``Yuri (genre) anime
# and manga'' 는 유리 장르에 속한 애니다. 그냥 ``genre'' 를 담는지 보면
# 세계애니의 옳은 매칭 마흔 건이 걸린다. 끝나는지 보면 하나도 안 걸린다.
# ``낱말'''' 과 ``이름'''' 은 뺐다(노트 180). ``긴 낱말''''은 제목이 긴 정상
# 문서에 붙는 분류라 라이트 노벨 여덟 건을 잘못 걸었다. 위키낱말사전은
# 낱말이 아니라 그 이름 자체로 잡는다.
NEG_ENDS = ("genres", "장르", "terminology", "용어", "disambiguation pages",
            "동음이의어 문서", "given names", "words and phrases")


@lru_cache(maxsize=1)
def _cats() -> dict:
    return json.loads(CATS.read_text()) if CATS.exists() else {}


def matches(domain: str, page: str, lang: str = "en") -> bool | None:
    """분류가 도메인과 맞나. 분류를 아직 안 받았으면 None."""
    ks = KEY.get(domain)
    if not ks:
        return None
    cs = _cats().get(f"{lang}|{page}")
    if cs is None:
        return None
    if not cs:
        return False                      # 분류가 아예 없는 문서 --- 토막이거나 넘겨주기
    for c in cs:
        t = c.split(":", 1)[-1].strip().lower()
        if t.endswith(NEG_ENDS) or "위키낱말사전" in t:
            return False
    lo = [c.lower() for c in cs]
    return any(any(k in c for k in ks) for c in lo)
