"""팝업 장소의 **평년 날씨**를 긁는다 — 실측은 일부러 안 쓴다(노트 638).

사용자가 상태층을 이렇게 정의했다: *"그 시기의 그 지역 날씨라던가 분위기는
어떻고 어떤 이슈가 있었는지, 등이 전부 상태가 된다."* 노트 632가 상태의 세
게이트(시간 · 주체 · 감도)를 세웠고, 노트 637이 날씨를 **첫 후보**로 꼽았다 —
기존 축과 겹침이 제일 작고(검색 0.0204 · 위키 0.0086이 이미 "관심" 축을
차지했다) 수집 비용이 제일 싸다.

**이 모듈의 핵심 결정은 하나다 — 실측 날씨를 안 쓴다.**

날씨는 둘로 갈린다.

  실측   팝업이 열린 그 20일 동안 실제로 며칠 비가 왔나.
  평년   그 자리 · 그 시기에 **보통** 며칠 비가 오나.

실측이 방문객을 더 잘 설명할 것은 거의 확실하다. 그런데 쓰면 안 된다. 이 판이
푸는 문제는 *"기획서와 계약서를 보고 결과를 맞힌다"* 이고, 기획 시점에 3주 뒤
날씨는 **아무도 모른다**. 실측을 넣으면 노트 546 · 552의 시간 게이트를 정면으로
어긴다 — 판이 오르더라도 그것은 미래를 본 값이다. 이 실험실이 460노트 동안
반복해서 당한 것이 정확히 이것이라(타깃 분모 오염 · 공간 링크 36% 오연결)
**올라간 뒤에 발견하는 쪽**은 다시 하지 않는다.

평년값은 기획자가 실제로 쓰는 정보다. *"장마철이라 사람이 덜 오겠지"* 는
기획서를 쓰는 시점에 할 수 있는 판단이고, 그것이 축이 나를 신호다.

**연도 누출도 막는다.** 20xx년 팝업의 평년값은 **그 해 이전 10년**으로만
만든다(``CLIM_YEARS``). 2024년 팝업이 2025년 기온을 보면 그것도 미래다.

**원천.** Open-Meteo 아카이브(ERA5 재분석). 키가 필요 없고 1940년부터 있으며
한국을 덮는다. 기상청 ASOS(data.go.kr)가 더 정밀하지만 ``.env`` 에 서비스 키가
없고 발급은 사람이 해야 한다 — ERA5 격자(~25km)는 어차피 서울 안의 성수 대
잠실을 못 가르므로 이 용도에는 충분하다.

**격자.** 좌표를 소수 1자리(~11km)로 반올림해 묶는다. ERA5 자체 해상도보다
촘촘하므로 정보를 안 버리고, 서울 팝업 수백 건이 격자 서너 개로 접힌다.

쓰는 법::

    python3 -m ingest.weather --geo      # BQ 좌표를 로컬로 (SELECT 만)
    python3 -m ingest.weather --pull     # 격자별 일별 시계열 받기
    python3 -m ingest.weather --report   # 덮음 확인
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data/state/spot_geo.json"          # {spot_id: [lat, lon]}
CACHE = ROOT / "data/state/weather"              # 격자별 일별 시계열
LINK = ROOT / "data/state/record_store_link.json"

API = "https://archive-api.open-meteo.com/v1/archive"

#: **쓰는 것만 받는다.** 처음에 다섯 변수 × 21년을 한 번에 달라고 했다가
#: 격자 하나 받고 **429** 로 막혔다 --- Open-Meteo 는 요청을 건수가 아니라
#: 일수 × 변수로 가중한다. 축이 실제로 쓰는 것은 기온과 강수 둘뿐이다
#: (``wx_wind`` 는 채택 전에 뺐다). 무게가 5분의 2로 준다.
DAILY = ["temperature_2m_mean", "precipitation_sum"]

#: 평년을 몇 해로 만드나. 팝업 연도 **이전** 이 해 만큼.
CLIM_YEARS = 10
#: 받아 둘 범위. 팝업 레코드가 2023~2026년이므로 제일 이른 평년은 2013년이다.
#: 넉넉히 잡을 이유가 없다 --- 범위가 곧 요청 무게다.
PULL_FROM = "2013-01-01"

#: 도시 → 대표 좌표. **스팟 좌표가 없을 때 쓴다.**
#:
#: 격자를 안 낮춘다. ERA5 해상도가 ~25km 라 서울 안에서 성수와 잠실은
#: **어차피 같은 값**이고, 그래서 도시 단위는 이 축에서 정보 손실이 아니다.
#: 스팟 링크는 팝업 89행 중 43행뿐인데 ``conditions.location.city`` 는
#: 66행에 있다 --- 정밀도를 안 잃고 덮음이 는다.
CITY = {
    "서울": (37.5665, 126.9780), "부산": (35.1796, 129.0756),
    "인천": (37.4563, 126.7052), "대구": (35.8714, 128.6014),
    "대전": (36.3504, 127.3845), "광주": (35.1595, 126.8526),
    "울산": (35.5384, 129.3114), "수원": (37.2636, 127.0286),
    "고양": (37.6584, 126.8320), "성남": (37.4200, 127.1265),
    "용인": (37.2411, 127.1776), "김포": (37.6152, 126.7156),
    "하남": (37.5392, 127.2148), "파주": (37.7599, 126.7800),
    "남양주": (37.6360, 127.2165), "안양": (37.3943, 126.9568),
    "경주": (35.8562, 129.2247), "제주": (33.4996, 126.5312),
    "강릉": (37.7519, 128.8761), "전주": (35.8242, 127.1480),
    "천안": (36.8151, 127.1139), "청주": (36.6424, 127.4890),
    "상해": (31.2304, 121.4737), "도쿄": (35.6762, 139.6503),
}

#: 표기 흔들림을 하나로. ``서울특별시`` · ``서울시`` · ``서울/대구`` 가 다
#: 서울이다.
_CITY_FIX = {"서울특별시": "서울", "서울시": "서울", "서울/대구": "서울",
             "고양시": "고양", "성남시": "성남", "수원시": "수원",
             "부산광역시": "부산", "인천광역시": "인천", "상하이": "상해"}


def city_geo(name) -> tuple | None:
    """도시 이름 → 좌표. 못 찾으면 None."""
    if not isinstance(name, str):
        return None
    s = _CITY_FIX.get(name.strip(), name.strip())
    if s in CITY:
        return CITY[s]
    for k in CITY:                      # ``성남시 분당`` 같은 꼬리표
        if s.startswith(k):
            return CITY[k]
    return None

GRID = 1        # 좌표 반올림 자릿수 — ~11km, ERA5 해상도보다 촘촘하다


def gridkey(lat: float, lon: float) -> str:
    return f"{round(lat, GRID):.1f}_{round(lon, GRID):.1f}"


# ── ① 좌표를 로컬로 ────────────────────────────────────────────
def pull_geo() -> dict:
    """``stg_sophy.platform_spots`` 에서 좌표만 **SELECT** 해 로컬에 둔다.

    GCP 는 읽기 전용이다(상시 조항). 축은 이 로컬 파일만 읽는다 — 판을 돌릴
    때마다 BQ 를 때리면 재현이 안 된다.
    """
    sql = ("SELECT spot_id, latitude, longitude FROM `sweetspot-ax.stg_sophy.platform_spots` "
           "WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    out = subprocess.check_output(
        ["bq", "query", "--project_id=sweetspot-ax", "--use_legacy_sql=false",
         "--format=json", "--max_rows=99999", sql], text=True)
    rows = json.loads(out)
    geo = {str(r["spot_id"]): [float(r["latitude"]), float(r["longitude"])]
           for r in rows}
    GEO.parent.mkdir(parents=True, exist_ok=True)
    GEO.write_text(json.dumps(geo, ensure_ascii=False))
    print(json.dumps({"좌표": len(geo), "격자": len({gridkey(*v) for v in geo.values()})},
                     ensure_ascii=False))
    return geo


def geo() -> dict:
    return json.loads(GEO.read_text()) if GEO.exists() else {}


def spot_of(rid: str, link: dict | None = None) -> str | None:
    """레코드 → spot_id. ``record_store_link`` 는 ``/popup/2246`` 꼴로 담는다."""
    link = link if link is not None else (
        json.loads(LINK.read_text()) if LINK.exists() else {})
    s = (link.get(rid) or {}).get("store") or ""
    return s.rsplit("/", 1)[-1] if s else None


def latlon_of(rid: str, link: dict, g: dict, rec: dict | None = None) -> tuple:
    """레코드 → (위도, 경도, 출처). **좌표 결정은 여기 한 곳에만 적는다.**

    노트 359 가 남긴 교훈이 이것이다 --- 같은 거름망이 두 군데 적혀 있으면
    갈라진다. 받는 쪽(``pull_all``)과 쓰는 쪽(``lab/weatheraxes``)이 서로
    다른 격자를 고르면 축은 조용히 결측이 된다.

    순서: 스팟 좌표 → 레코드의 ``conditions.location.city``.
    """
    sid = spot_of(rid, link)
    if sid and sid in g:
        lat, lon = g[sid]
        return float(lat), float(lon), "spot"
    if rec is None:
        p = Path("data/records") / f"{rid}.json"
        rec = json.loads(p.read_text()) if p.exists() else {}
    loc = ((rec.get("conditions") or {}).get("location") or {})
    c = city_geo(loc.get("city"))
    if c:
        return c[0], c[1], "city"
    return (None, None, "없음")


# ── ② 격자별 일별 시계열 ───────────────────────────────────────
def pull_grid(lat: float, lon: float, start: str = PULL_FROM,
              end: str | None = None) -> dict:
    """한 격자의 일별 시계열. 이미 받았으면 안 받는다."""
    key = gridkey(lat, lon)
    p = CACHE / f"{key}.json"
    if p.exists():
        return json.loads(p.read_text())
    from datetime import date, timedelta
    # ERA5 는 5일쯤 지연된다. 넉넉히 열흘 뒤로 물린다.
    end = end or (date.today() - timedelta(days=10)).isoformat()
    q = urllib.parse.urlencode({
        "latitude": round(lat, GRID), "longitude": round(lon, GRID),
        "start_date": start, "end_date": end,
        "daily": ",".join(DAILY), "timezone": "Asia/Seoul"})
    # **429 는 정상 응답으로 다룬다.** 무료 몫은 분·시 단위로 차므로
    # 기다리면 열린다 --- 여기서 포기하면 격자가 통째로 빈다.
    d = None
    for wait in (0, 20, 45, 90, 180):
        if wait:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(f"{API}?{q}", timeout=180) as r:
                d = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    if d is None:
        raise RuntimeError(f"{key}: 429 가 안 풀렸다")
    if "daily" not in d:
        raise RuntimeError(f"{key}: {d.get('reason') or d}")
    CACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d["daily"], ensure_ascii=False))
    return d["daily"]


def wanted(rids=None) -> dict:
    """축이 쓸 격자. ``latlon_of`` 하나만 본다(받는 쪽과 쓰는 쪽을 붙여 둔다)."""
    g = geo()
    link = json.loads(LINK.read_text()) if LINK.exists() else {}
    if rids is None:
        from lab import trendaxes as ta
        ta.set_wide(False)
        ta.set_grades(("A", "B", "C", "D", "E"))
        rids = (ta._ids() or {}).get("팝업") or list(link)
    want: dict[str, tuple] = {}
    for rid in rids:
        lat, lon, _src = latlon_of(rid, link, g)
        if lat is not None:
            want[gridkey(lat, lon)] = (lat, lon)
    return want


def pull_all(sleep: float = 1.2) -> dict:
    """레코드가 실제로 쓰는 격자만 받는다."""
    want = wanted()
    done, fail = 0, {}
    for k, (lat, lon) in sorted(want.items()):
        if (CACHE / f"{k}.json").exists():
            done += 1
            continue
        try:
            pull_grid(lat, lon)
            done += 1
            time.sleep(sleep)
        except Exception as e:
            fail[k] = f"{type(e).__name__}: {e}"
    print(json.dumps({"격자": len(want), "받음": done, "실패": fail},
                     ensure_ascii=False, indent=1))
    return want


def report() -> None:
    g, link = geo(), json.loads(LINK.read_text()) if LINK.exists() else {}
    have = sum(1 for rid in link
               if (spot_of(rid, link) or "") in g)
    cached = len(list(CACHE.glob("*.json"))) if CACHE.exists() else 0
    print(json.dumps({"링크된 레코드": len(link), "좌표 있음": have,
                      "받은 격자": cached}, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", action="store_true")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.geo:
        pull_geo()
    if a.pull:
        pull_all()
    if a.report or not (a.geo or a.pull):
        report()
