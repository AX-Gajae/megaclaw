# -*- coding: utf-8 -*-
"""노트 919 · 팔 ㅍ — **저장소 안에서 만든 오프라인 지오코더.**

사전등록 `docs/prereg_919_geocode.md` §3.

🔴 왜 오프라인인가
  · 유료 API 금지(상시). 광역 크롤 금지.
  · 무료 공공 지오코딩(도로명주소 개방 API · 국가공간정보 vworld)은
    **키가 필요해서 못 썼다**(「없다」가 아니다 · 조항 59). 실측 응답은
    `runners/out919_geocode.json:배선 ⑤ 무료 공공 지오코딩` 에 원문으로 실린다.
  · 조항 60 — **레코드가 이미 가진 열쇠를 다 써 봤는지 먼저 센다.**
    저장소 안에 (도로명주소 → 좌표) 와 (장소명 → 좌표) 쌍이 이미 있다.

여기서 만드는 사전 둘
  ROAD  : (도로명, 건물번호) → [(위도, 경도), ...]
          출처 = `data/state/platform_spots.csv` 의 road_address/address
                 + `data/state/spot_addr.json` 의 주소, 좌표는 같은 spot 행에서
  VENUE : 정규화한 장소명 → [(위도, 경도), ...]
          출처 = **이미 좌표가 붙은 레코드**(record_store_link → platform_spots)의
                 `conditions.location.venue_name` / `conditions.venue`

🔴 이 모듈은 좌표를 **만들어 내지 않는다.** 저장소가 이미 가진 좌표를
   다른 열쇠로 다시 찾을 뿐이다. 그래서 새 좌표의 정확도 상한은 원 좌표의 정확도다.
"""
from __future__ import annotations

import math
import re
import unicodedata

# ── 정규화 ────────────────────────────────────────────────────────────────
#: 층·호수처럼 250m 격자에서 무의미한 꼬리. 🔴 **지우는 것을 러너가 센다.**
_FLOOR = re.compile(
    r"(지하\s*\d+\s*층|지하\s*\d+\s*[Ff]|\d+\s*층|[Bb]\d+\s*층?|\d+\s*[Ff]\b|B\d+\b)")
_PUNCT = re.compile(r"[()\[\]{}''\"“”‘’·,/&+~\-–—:;!?@#*]+")
_WS = re.compile(r"\s+")


def norm(s) -> str:
    """유니코드 정규화 + 구두점 → 공백 + 공백 압축. **소문자화는 안 한다**(한글이라 무의미)."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = _PUNCT.sub(" ", s)
    return _WS.sub(" ", s).strip()


def core(s) -> str:
    """정규화 + 층 표기 제거. 「더현대 서울 지하 2층 아이코닉존」 → 「더현대 서울 아이코닉존」."""
    s = norm(s)
    s = _FLOOR.sub(" ", s)
    return _WS.sub(" ", s).strip()


#: 도로명 + 건물번호. 「연무장길 65」·「여의대로 108」·「경강로2046번길 5」
_ROAD = re.compile(r"([가-힣A-Za-z0-9]*?[가-힣](?:대로|로|길))\s*(\d+(?:-\d+)?)(?!\s*[층호])")


def road_key(s):
    """문자열에서 (도로명, 건물번호) 를 뽑는다. 없으면 None."""
    m = _ROAD.search(norm(s))
    return (m.group(1), m.group(2)) if m else None


# ── 좌표 묶음 다루기 ──────────────────────────────────────────────────────
def haversine_m(a, b) -> float:
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000.0 * math.asin(min(1.0, math.sqrt(h)))


def spread_m(pts) -> float:
    """묶음 안 최대 쌍거리(m). 🔴 이 값이 250 을 넘으면 **250m 격자에서 갈릴 수 있다** —
    러너가 그 건수를 따로 센다."""
    if len(pts) < 2:
        return 0.0
    return max(haversine_m(pts[i], pts[j])
               for i in range(len(pts)) for j in range(i + 1, len(pts)))


def medoid(pts):
    """묶음의 대표점 = **메도이드**(다른 점까지 거리 합이 최소인 실제 점).
    🔴 평균을 안 쓰는 이유: 평균은 **어느 실측 좌표도 아닌 점**을 만들어 격자를 옮길 수 있다."""
    if len(pts) == 1:
        return pts[0]
    # 🔴 **동점을 좌표 자체로 깬다.** 안 깨면 `min` 이 「먼저 온 점」을 고르고,
    # 그 순서가 파이썬 문자열 해시(프로세스마다 무작위)에 딸려 흔들린다 —
    # 실제로 같은 코드가 부착 **132 와 129** 를 냈다(919 가 자기 산출물로 적발).
    return min(pts, key=lambda p: (sum(haversine_m(p, q) for q in pts), p))


# ── 사전 만들기 ───────────────────────────────────────────────────────────
def build_road(spots: dict, spot_addr: dict, fnum) -> dict:
    """(도로명, 번호) → [(lat, lon)]. **좌표가 있는 spot 행만** 쓴다."""
    out: dict = {}
    for sid, row in spots.items():
        la, lo = fnum(row.get("latitude")), fnum(row.get("longitude"))
        if la is None or lo is None:
            continue
        for src in (row.get("road_address"), row.get("address"), spot_addr.get(sid)):
            k = road_key(src)
            if k:
                out.setdefault(k, []).append((la, lo))
    return out


def build_venue(known_coords: dict, venue_of) -> dict:
    """정규화 장소명 → [(lat, lon)]. `known_coords` 는 **좌표가 이미 붙은 레코드 전량**
    (유보 밖 레코드도 쓴다 — 사전은 크면 클수록 좋고, **채점행이 아니라 사전**이다)."""
    out: dict = {}
    for rid, (la, lo) in known_coords.items():
        nm = core(venue_of(rid))
        if len(nm) >= 2:
            out.setdefault(nm, []).append((la, lo))
    return out


# ── 조회 ──────────────────────────────────────────────────────────────────
#: 부분일치에서 이만큼 짧은 열쇠는 안 쓴다(「성수」가 아무 데나 걸린다)
MIN_SUB = 5


def lookup(venue: str, addr: str, ROAD: dict, VENUE: dict):
    """레코드의 열쇠 → (lat, lon, 경로, 근거, spread_m). 못 찾으면 (None, None, 사유, ...).

    🔴 **경로 우선순위를 코드로 못 박는다**(사후에 고르면 그게 사후 부분집합이다):
      D-주소 : 주소 문자열의 (도로명,번호) → ROAD          — 가장 촘촘
      D-장소 : 장소명 안의 (도로명,번호) → ROAD            — 「LECT 성수 (연무장길 65)」
      B-정확 : 장소명 core 정확일치 → VENUE
      B-부분 : 장소명 core 부분일치 · **유일할 때만** → VENUE
    """
    k = road_key(addr)
    if k and k in ROAD:
        pts = ROAD[k]
        la, lo = medoid(pts)
        return la, lo, "D-주소(도로명+건물번호)", f"{k[0]} {k[1]}", spread_m(pts)

    k = road_key(venue)
    if k and k in ROAD:
        pts = ROAD[k]
        la, lo = medoid(pts)
        return la, lo, "D-장소명 안의 도로명", f"{k[0]} {k[1]}", spread_m(pts)

    c = core(venue)
    if c and c in VENUE:
        pts = VENUE[c]
        la, lo = medoid(pts)
        return la, lo, "B-장소명 정확일치", c, spread_m(pts)

    if len(c) >= MIN_SUB:
        cand = [g for g in VENUE if len(g) >= MIN_SUB and (g in c or c in g)]
        if len(cand) == 1:
            pts = VENUE[cand[0]]
            la, lo = medoid(pts)
            return la, lo, "B-장소명 부분일치(유일)", cand[0], spread_m(pts)
        if len(cand) > 1:
            return None, None, "🔴 부분일치 후보가 여럿이라 안 골랐다", "|".join(cand[:4]), None

    if not c:
        return None, None, "🔴 장소명 열 자체가 비었다", "", None
    return None, None, "🔴 사전에 없다", c, None
