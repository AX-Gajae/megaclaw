"""IP 조인 --- 팝업 두 층을 잇는 키(노트 291).

`ingest/derive_features.py` 가 두 층(내부 프로젝트 · 시장 크롤링)을 이어
`ip_history.prior_count` 를 만드는데, 조인이 **문자열 완전일치**라 내부
48/380 · 시장 60/647 만 이어진다. 노트 291이 넓혀 보고 잰 결과를 여기에
코드로 남긴다. **적용(파생 필드 재생성)은 하네스의 KIOF 전향 사이클이
끝난 뒤에 한다** --- 두 트랙의 자료를 동시에 바꾸는 일이라서다.

    규칙                다른 IP   내부      시장
    완전일치(지금)          23    48/380   60/647
    정규화                23    48       60
    **정규화 + 접두사**     40    70       97      <- 노트 291 채택 후보
    정규화 + 포함           46    78      105      <- 오탐 섞임

**포함까지 가면 안 된다.** ``이마트'' 가 *도드람한돈브랜드유튜버정육왕콘텐츠
협업**이마트**푸드마켓고덕점연계* 에 우연히 들어 있고 ``하리보'' 가 브랜드를
열거한 문장에 들어 있다. **접두사로 좁히면 그런 것이 사라지고** 진짜는
남는다 --- 포켓몬→포켓몬고 · 주술회전→주술회전2기 · 귀멸의칼날→
귀멸의칼날무한성편 · 마비노기→마비노기모바일 · 산리오→산리오캐릭터즈.

라벨을 한 번도 안 본다(이름 문자열만 쓴다).
"""
from __future__ import annotations

import re
import unicodedata

_STRIP = re.compile(r"[^0-9A-Za-z가-힣ぁ-んァ-ン一-龥]")
_PAREN = re.compile(r"\(.*?\)|\[.*?\]")
_COLLAB = re.compile(r"\s*[xX×]\s*")
MIN_PREFIX = 3          # 이보다 짧은 키로는 접두사 매칭을 안 한다


def norm(s: str | None) -> str:
    """표기 차이를 걷어낸 키. 괄호 · 콜라보 뒷부분 · 기호 제거."""
    s = unicodedata.normalize("NFKC", s or "")
    s = _PAREN.sub(" ", s)
    s = _COLLAB.split(s)[0]
    return _STRIP.sub("", s).lower()


def key_internal(rec: dict) -> str:
    """내부 프로젝트 레코드의 IP 키(`derive_features._ipkey_int` 와 같다)."""
    e = rec.get("entities") or {}
    k = (e.get("brand_key") or (rec.get("intervention") or {}).get("brand_name")
         or "")
    return k.replace("unresolved:", "").strip()


def key_market(rec: dict) -> str:
    """시장 레코드의 IP 키(`derive_features._ipkey_mkt` 와 같다)."""
    k = (rec.get("ip_or_collab") or rec.get("brand") or "").strip()
    return re.sub(r"\(.*?\)", "", k).split(" X ")[0].split("X")[0].strip()


def same_ip(a: str, b: str, *, loose: bool = True) -> bool:
    """두 정규화 키가 같은 IP 인가.

    ``loose=False`` 면 완전일치(지금 판의 동작). 기본은 접두사까지 본다.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    if not loose:
        return False
    return ((len(a) >= MIN_PREFIX and b.startswith(a))
            or (len(b) >= MIN_PREFIX and a.startswith(b)))
