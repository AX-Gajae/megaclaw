"""시군구 **일별 방문자수**를 긁는다 — 상태층에서 처음으로 스케일이 맞는 신호(노트 641).

한국관광공사가 이동통신(KT) 기반으로 만든 것을 공공데이터포털이 연다.
``apis.data.go.kr/B551011/DataLabService``.

**왜 이게 다른가.** `data/encoder/README.md` 가 popga 행동 데이터를 프록시로
쓰려다 실패한 원인을 이렇게 적었다 --- *"모집단 스케일 불일치: 조회 중앙값
86명 대 실제 방문 수천~수만"*. 이 원천은 성동구 하루 **외지인 36만 명**이다.
팝업 방문 수천~수만과 **같은 자릿수**다. 상태층 후보 중 스케일이 맞는 첫
신호다.

세 구분이 따로 온다 --- ``현지인(a)`` · ``외지인(b)`` · ``외국인(c)``.
팝업에 쓸 것은 **외지인**이다. 그 동네에 사는 사람이 아니라 **밖에서 온
사람**이 팝업을 찾는다.

**시간 게이트.** 일 단위라 오픈 이전 창만 잘라 쓰면 통과한다(노트 149 규약).
운영 기간 중의 값은 **안 쓴다** --- 기획 시점에 모르고, 게다가 팝업 자신이
그 숫자에 기여하므로 역인과다.

**확인한 사실**(2026-08-05 직접 호출):

    범위          2020-01-01 ~ (일 단위)
    단위          시군구 264개 × 3구분 = 하루 792행 (광역은 51행)
    쪽 크기       numOfRows=10000 통과
    한도          개발계정 1,000 호출/일
    지역 필터     ``areaCd`` · ``signguCd`` 는 **안 먹는다**(코드계가 안 맞음).
                  전국을 통째로 받아 로컬에서 거른다 --- 어차피 그게 더 싸다.

쓰는 법::

    python3 -m ingest.visitors --pull 2022-01 2026-08
    python3 -m ingest.visitors --report
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/state/visitors"
API = "https://apis.data.go.kr/B551011/DataLabService"
OP = "locgoRegnVisitrDDList"          # 시군구. 광역은 metcoRegnVisitrDDList
PAGE = 10000
DIV = {"1": "현지인", "2": "외지인", "3": "외국인"}


def _key() -> str:
    k = os.environ.get("DATA_GO_KR_KEY")
    if k:
        return k
    p = ROOT / ".env"
    kv = dict(l.strip().split("=", 1) for l in p.read_text().splitlines()
              if "=" in l and not l.startswith("#"))
    k = kv.get("DATA_GO_KR_KEY")
    if not k:
        raise RuntimeError("DATA_GO_KR_KEY 없음 — .env 에 넣어라")
    return k


def _call(start: str, end: str, page: int = 1, op: str = OP) -> dict:
    q = urllib.parse.urlencode({
        "serviceKey": _key(), "MobileOS": "ETC", "MobileApp": "worldmodel",
        "_type": "json", "numOfRows": PAGE, "pageNo": page,
        "startYmd": start, "endYmd": end})
    req = urllib.request.Request(f"{API}/{op}?{q}", headers={"User-Agent": "curl/8"})
    t = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
    d = json.loads(t)
    if "response" not in d:
        raise RuntimeError(str(d)[:200])
    return d["response"]["body"]


def pull_month(ym: str, op: str = OP) -> int:
    """한 달을 통째로 받아 캐시. 이미 있으면 안 받는다."""
    import calendar
    y, m = int(ym[:4]), int(ym[5:7])
    p = CACHE / f"{ym}.json"
    if p.exists():
        return len(json.loads(p.read_text()))
    s = f"{y:04d}{m:02d}01"
    e = f"{y:04d}{m:02d}{calendar.monthrange(y, m)[1]:02d}"
    rows, page = [], 1
    while True:
        b = _call(s, e, page, op)
        it = b.get("items")
        it = it.get("item", []) if isinstance(it, dict) else []
        if isinstance(it, dict):
            it = [it]
        # **필요한 네 칸만 남긴다.** 원문을 다 두면 달마다 수십 MB 다.
        rows += [(x["signguCode"], x["baseYmd"], x["touDivCd"], float(x["touNum"]))
                 for x in it if x.get("signguCode")]
        got, tot = page * PAGE, int(b.get("totalCount") or 0)
        if got >= tot or not it:
            break
        page += 1
        time.sleep(0.3)
    CACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rows, ensure_ascii=False))
    return len(rows)


def months(a: str, b: str) -> list[str]:
    y, m = int(a[:4]), int(a[5:7])
    y2, m2 = int(b[:4]), int(b[5:7])
    out = []
    while (y, m) <= (y2, m2):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def pull(a: str, b: str) -> dict:
    done, fail = {}, {}
    for ym in months(a, b):
        try:
            done[ym] = pull_month(ym)
        except Exception as e:
            fail[ym] = f"{type(e).__name__}: {e}"[:120]
        time.sleep(0.3)
    print(json.dumps({"받은 달": len(done), "총 행": sum(done.values()),
                      "실패": fail}, ensure_ascii=False, indent=1))
    return done


def names() -> dict:
    """시군구 코드 → 이름. API 응답에서 그대로 만든다."""
    b = _call("20250401", "20250401", 1)
    it = b["items"]["item"]
    return {x["signguCode"]: x["signguNm"] for x in it}


# ── 레코드 → 시군구 코드 ───────────────────────────────────────
#
# **결정은 여기 한 곳에만 적는다**(노트 359 · 638 과 같은 규약). 받는 쪽과
# 쓰는 쪽이 서로 다른 코드를 고르면 축은 조용히 결측이 된다.
#
# 이름만으로는 안 된다 --- ``중구`` 는 여섯 곳, ``서구`` 는 다섯 곳이다.
# 그래서 **시도까지 같이** 봐야 한다. 도로명주소가 그것을 통째로 준다:
# ``서울특별시 성동구 아차산로…``.

SIDO = {"11": "서울", "26": "부산", "27": "대구", "28": "인천", "29": "광주",
        "30": "대전", "31": "울산", "36": "세종", "41": "경기", "43": "충북",
        "44": "충남", "46": "전남", "47": "경북", "48": "경남", "50": "제주",
        "51": "강원", "52": "전북"}
ADDR = ROOT / "data/state/spot_addr.json"
LINK = ROOT / "data/state/record_store_link.json"
RECS = ROOT / "data/records"


def _sido_of(addr: str) -> str | None:
    """주소 앞머리 → 시도 두 자리."""
    for k, v in SIDO.items():
        if addr.startswith(v):
            return k
    return None


def sgg_index() -> dict:
    """(시도2, 시군구명) → 코드. 캐시가 있으면 API 를 안 부른다."""
    p = CACHE / "_names.json"
    if p.exists():
        nm = json.loads(p.read_text())
    else:
        nm = names()
        CACHE.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(nm, ensure_ascii=False))
    return {(c[:2], n): c for c, n in nm.items()}


def sgg_of(rid: str, idx: dict, link: dict, addr: dict,
           rec: dict | None = None) -> tuple:
    """레코드 → (시군구코드, 출처). 순서: 도로명주소 → district → city."""
    if rec is None:
        p = RECS / f"{rid}.json"
        rec = json.loads(p.read_text()) if p.exists() else {}
    # ① 도로명주소 --- 시도까지 같이 오므로 동명 이구가 안 헷갈린다
    s = (link.get(rid) or {}).get("store") or ""
    sid = s.rsplit("/", 1)[-1] if s else None
    a = addr.get(sid or "")
    if a:
        sd = _sido_of(a)
        parts = a.split()
        for tok in parts[1:3]:
            if sd and (sd, tok) in idx:
                return idx[(sd, tok)], "주소"
        # ``성남시 분당구`` 처럼 두 칸이 합쳐 한 시군구인 경우
        if sd and len(parts) >= 3 and (sd, parts[1] + " " + parts[2]) in idx:
            return idx[(sd, parts[1] + " " + parts[2])], "주소"
    # ② 레코드의 district / city
    loc = ((rec.get("conditions") or {}).get("location") or {})
    dist, city = (loc.get("district") or ""), (loc.get("city") or "")
    sd = None
    for k, v in SIDO.items():
        if city.startswith(v):
            sd = k
            break
    for (s2, n), c in idx.items():
        if n and n in dist and (sd is None or s2 == sd):
            return c, "district"
    for (s2, n), c in idx.items():
        if n and city and (city.startswith(n) or n.startswith(city)) and len(city) >= 2:
            return c, "city"
    return None, "없음"


def series(div: str = "2") -> dict:
    """{시군구코드: {날짜: 방문자수}}. 기본은 **외지인**."""
    out: dict = {}
    # ``_names.json`` 은 코드표라 모양이 다르다 --- 밑줄로 시작하는 것은 뺀다
    for p in sorted(CACHE.glob("[0-9]*.json")):
        for sg, ymd, dv, num in json.loads(p.read_text()):
            if dv == div:
                out.setdefault(sg, {})[ymd] = num
    return out


def report() -> None:
    fs = sorted(CACHE.glob("[0-9]*.json")) if CACHE.exists() else []
    n = sum(len(json.loads(p.read_text())) for p in fs)
    print(json.dumps({"달": len(fs), "행": n,
                      "범위": [fs[0].stem, fs[-1].stem] if fs else None},
                     ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", nargs=2, metavar=("YYYY-MM", "YYYY-MM"))
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.pull:
        pull(*a.pull)
    if a.report or not a.pull:
        report()


#: **동·지역명 → 시군구.** 손으로 적었고 라벨을 안 본다 --- 지리다(노트 661).
#:
#: 시장팝업은 기사에서 만든 레코드라 도로명주소가 없다. 대신 `neighborhood` 에
#: **동 이름**이 들어 있다(성수동 · 여의도 · 잠실 · 한남동…). 남은 125건 중
#: **91건이 서울**이므로 서울만 적어도 덮음이 크게 오른다.
#:
#: 구 경계에 걸친 동네는 **대표 구**로 넣는다. 방문자 자료가 구 단위이므로
#: 이 근사가 값을 바꿀 수 있다 --- 사각으로 적어 둔다.
HOOD = {
    "덕양구": "고양시 덕양구",
    "장안구": "수원시 장안구",
    "동탄": "화성시",
    "센텀": "해운대구",
    "강남": "강남구",
    # 서울
    "성수": "성동구", "성수동": "성동구", "서울숲": "성동구", "뚝섬": "성동구",
    "여의도": "영등포구", "영등포": "영등포구",
    "잠실": "송파구", "석촌": "송파구",
    "한남": "용산구", "한남동": "용산구", "이태원": "용산구", "용산": "용산구",
    "삼성동": "강남구", "청담": "강남구", "청담동": "강남구", "압구정": "강남구",
    "신사": "강남구", "신사동": "강남구", "가로수길": "강남구", "역삼": "강남구",
    "논현": "강남구", "대치": "강남구", "코엑스": "강남구", "삼성": "강남구",
    "명동": "중구", "을지로": "중구", "충무로": "중구", "동대문": "중구",
    "홍대": "마포구", "합정": "마포구", "연남": "마포구", "연남동": "마포구",
    "망원": "마포구", "상수": "마포구", "서교": "마포구", "공덕": "마포구",
    "신촌": "서대문구", "이대": "서대문구", "연희": "서대문구",
    "종로": "종로구", "인사동": "종로구", "익선동": "종로구", "삼청동": "종로구",
    "북촌": "종로구", "광화문": "종로구", "낙원": "종로구", "서촌": "종로구",
    "노원": "노원구", "강동": "강동구", "천호": "강동구",
    "목동": "양천구", "여의": "영등포구", "당산": "영등포구",
    "건대": "광진구", "성수2": "성동구", "구의": "광진구",
    "왕십리": "성동구", "금호": "성동구",
    "가산": "금천구", "구로": "구로구", "신도림": "구로구",
    "사당": "동작구", "노량진": "동작구", "흑석": "동작구",
    "서초": "서초구", "방배": "서초구", "반포": "서초구", "양재": "서초구",
    "잠원": "서초구", "교대": "서초구",
    "미아": "강북구", "수유": "강북구", "쌍문": "도봉구",
    "은평": "은평구", "연신내": "은평구", "불광": "은평구",
    "관악": "관악구", "신림": "관악구", "샤로수길": "관악구",
    "중랑": "중랑구", "면목": "중랑구", "성북": "성북구", "성신여대": "성북구",
    "청량리": "동대문구", "회기": "동대문구", "신설동": "동대문구",
    "마곡": "강서구", "화곡": "강서구", "김포공항": "강서구",
    "송리단길": "송파구", "가락": "송파구", "문정": "송파구",
    # 경기·기타 (city 가 같이 오므로 시도로 갈린다)
    "판교": "성남시 분당구", "분당": "성남시 분당구", "정자": "성남시 분당구",
    "일산": "고양시 일산동구", "화정": "고양시 덕양구",
    "미사": "하남", "스타필드": "하남",
    "광교": "수원시 영통구", "영통": "수원시 영통구",
    "해운대": "해운대구", "서면": "부산진구", "전포": "부산진구",
    "광안리": "수영구", "남포": "중구",
}


def hood_sgg(neighborhood, city, idx: dict):
    """동 이름 → 시군구 코드. `city` 로 시도를 좁힌다(동명이구 방지)."""
    if not isinstance(neighborhood, str):
        return None
    sd = None
    if isinstance(city, str):
        for k, v in SIDO.items():
            if city.startswith(v):
                sd = k
                break
    txt = neighborhood.strip()
    for key in sorted(HOOD, key=len, reverse=True):
        if key in txt:
            nm = HOOD[key]
            for (s2, n), c in idx.items():
                if n == nm and (sd is None or s2 == sd):
                    return c
            for (s2, n), c in idx.items():     # 시도가 안 맞으면 이름만
                if n == nm:
                    return c
    return None


#: **`city` 만으로 시군구가 정해지는 곳.** 시 자체가 시군구 단위인 곳만 적는다.
#:
#: 노트 662 --- 하남시 · 여주시 · 용인시 · 화성시는 `city` 로 정확히 붙는다.
#: **광역시는 여기 안 넣는다** --- 부산 · 대구 · 광주 · 인천은 구가 여러 개라
#: `city` 만으로 못 정한다. 대표 구를 억지로 넣으면 방문자 값이 **틀린 구**에서
#: 오고, 그건 근사가 아니라 오류다. 노트 661 이 잰 것(덮음이 부호를 뒤집는다)의
#: 반대를 자기 손으로 만드는 일이다 --- **덮음을 올리려고 값을 틀리게 하지 않는다.**
CITY_ONLY = {
    "하남": "하남시", "여주": "여주시", "이천": "이천시", "안성": "안성시",
    "평택": "평택시", "파주": "파주시", "김포": "김포시", "광주시": "광주시",
    "구리": "구리시", "남양주": "남양주시", "양평": "양평군", "가평": "가평군",
    "밀양": "밀양시", "경주": "경주시", "강릉": "강릉시", "속초": "속초시",
    "춘천": "춘천시", "원주": "원주시", "전주": "전주시", "군산": "군산시",
    "목포": "목포시", "여수": "여수시", "순천": "순천시", "포항": "포항시",
    "구미": "구미시", "김해": "김해시", "양산": "양산시", "진주": "진주시",
    "통영": "통영시", "거제": "거제시", "제주": "제주시", "서귀포": "서귀포시",
    "세종": "세종특별자치시", "천안": "천안시", "아산": "아산시",
    "청주": "청주시", "충주": "충주시", "공주": "공주시", "논산": "논산시",
    "익산": "익산시", "정읍": "정읍시", "나주": "나주시", "광양": "광양시",
    "안동": "안동시", "경산": "경산시", "영주": "영주시", "상주": "상주시",
    "사천": "사천시", "고성": "고성군",
    # 구가 있는 시 --- `venue`/`nb` 로 못 좁히면 시 전체 대표를 쓰지 않는다.
    # 다만 방문자 자료가 이들을 **시 단위로도** 담으므로 그 코드를 쓴다.
    "수원": "수원시", "고양": "고양시", "성남": "성남시", "용인": "용인시",
    "화성": "화성시", "안산": "안산시", "안양": "안양시", "부천": "부천시",
    "의정부": "의정부시", "시흥": "시흥시", "광명": "광명시",
}


def city_sgg(city, idx: dict):
    """`city` → 시군구 코드. **광역시는 None** (구를 못 정한다 · 노트 662)."""
    if not isinstance(city, str):
        return None
    t = city.strip()
    # 광역시·특별시는 구가 여러 개라 city 만으로 못 정한다
    for wide in ("서울", "부산", "대구", "인천", "광주광역", "대전", "울산"):
        if t.startswith(wide):
            return None
    for key in sorted(CITY_ONLY, key=len, reverse=True):
        if key in t:
            nm = CITY_ONLY[key]
            for (_s, n), c in idx.items():
                if n == nm:
                    return c
    return None
