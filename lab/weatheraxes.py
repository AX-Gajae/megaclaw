"""날씨 축 — **평년값만** 쓴다(노트 638).

노트 637이 상태층 후보 넷을 값어치 순으로 세웠고 날씨가 첫째였다. 이유는
성능 기대가 아니라 **겹침**이다. 지금 판의 관심 축은 검색(0.0204)과
위키(0.0086)가 차지하고 있고 둘 다 *사람들이 이 IP 를 얼마나 찾아봤나* 를
잰다. 날씨는 그것과 다른 것을 잰다 — *그 자리 · 그 시기가 나가 놀 만한가.*
노트 614의 m_eff 계산이 말한 것이 이것이다: 자를 더 놓아도 **같은 것을 재면**
독립 눈금은 안 는다.

**왜 실측이 아니라 평년인가.** ``ingest/weather`` 의 독스트링에 길게 적었고
요지는 하나다 — 기획 시점에 3주 뒤 날씨는 아무도 모른다. 실측을 넣으면 판이
오르더라도 미래를 본 값이다.

**그래서 이 축이 기대할 수 있는 것은 작다.** 정직하게 미리 적어 둔다.

  ① 평년값은 사실상 **좌표별 계절성**이고, 계절은 ``cal_month_sin/cos`` 가
     이미 나른다. 새로 나르는 것은 둘뿐이다 — **지역 차**(서울 대 부산 대
     제주)와 **비선형**(``wx_harsh`` 는 여름과 겨울에 **둘 다** 높다. 주기
     좌표는 그 U자를 못 만든다).
  ② 그런데 팝업 대부분이 서울이면 지역 차가 거의 없다. 그러면 남는 것은
     비선형 하나다.

즉 **판 문턱 0.0045를 넘을 것 같지 않다.** 그래도 재는 이유는 노트 632의
게이트 ③(감도)이 *재기 전에는 모른다*고 못박았기 때문이고, 넘든 못 넘든
"상태층 축을 하나 만들어 게이트 셋을 다 통과시켰다"는 사실 자체가 지금까지
없던 것이기 때문이다. 못 넘으면 못 넘었다고 적는다.

축 셋.

    wx_temp    기간 평년 평균기온
    wx_rain    기간 평년 강수확률 (일강수 1mm 넘는 날의 비율)
    wx_harsh   쾌적 이탈 — mean(max(0, |T-18| - 5)). 혹서와 혹한이 같이 높다

넷째 후보였던 ``wx_wind`` 는 뺐다. ERA5 격자 바람은 도심 체감과 거의 무관해서
**신호가 있다면 그것은 지형이지 날씨가 아니다** — 노트 276의 겹말 가드를
채택 전에 스스로 적용한 것이다.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from ingest.weather import CACHE, CLIM_YEARS, geo, gridkey, latlon_of

R = Path("data/records")
LINK = Path("data/state/record_store_link.json")
META = Path("data/state/popup_v2_meta.json")

#: 기간 길이를 어디서 찾나. 위에서부터 있는 것을 쓴다. 스키마가 판마다 조금씩
#: 달라서 하나만 박아 두면 조용히 전부 결측이 된다 — 실제로 어느 경로가
#: 맞았는지는 ``build(report=True)`` 가 찍는다.
DAY_PATHS = [
    "conditions.period.days",
    "conditions.derived.duration.days",
    "conditions.derived.duration.planned_operating_days",
]
END_PATHS = ["conditions.period.to"]
START_PATHS = ["conditions.period.from"]

WIN = 3              # 평년을 모을 때 날짜 앞뒤 창(일)
RAIN_MM = 1.0        # 이 이상이면 "비 온 날"
COMFORT = 18.0       # 쾌적 중심 기온
BAND = 5.0           # 이 밖으로 나간 만큼만 벌점


def _get(o, path: str):
    for k in path.split("."):
        if not isinstance(o, dict):
            return None
        o = o.get(k)
    return o


def _first(d: dict, paths: list[str]):
    for p in paths:
        v = _get(d, p)
        if v is not None:
            return v, p
    return None, None


def _parse(s) -> date | None:
    if not isinstance(s, str) or len(s) < 8:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _series(key: str) -> dict | None:
    """격자의 일별 시계열을 ``(월,일,연) → (기온, 강수)`` 로 뒤집는다."""
    p = CACHE / f"{key}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    t, pr = d.get("temperature_2m_mean") or [], d.get("precipitation_sum") or []
    out = {}
    for i, ds in enumerate(d.get("time") or []):
        y, m, dd = int(ds[:4]), int(ds[5:7]), int(ds[8:10])
        tv = t[i] if i < len(t) else None
        pv = pr[i] if i < len(pr) else None
        if tv is None:
            continue
        out[(m, dd, y)] = (float(tv), float(pv) if pv is not None else 0.0)
    return out


def _clim(ser: dict, start: date, days: int) -> tuple | None:
    """팝업 기간의 평년값. **연도 누출을 막는다** — 그 해 이전 10년만 본다.

    날짜를 정확히 맞추지 않고 **앞뒤 ``WIN`` 일 창**으로 모은다. 기후학의
    평년값이 원래 그렇게 정의되고, 실질적인 이유가 하나 더 있다 --- 하루짜리
    팝업은 정확 매칭이면 표본이 10개(10년)뿐이라 평년이 아니라 잡음이다.
    창을 주면 같은 하루도 70개로 선다. 창은 **과거 연도 안에서만** 넓히므로
    누출이 아니다.
    """
    lo, hi = start.year - CLIM_YEARS, start.year - 1
    temps, rains = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        for off in range(-WIN, WIN + 1):
            dd = d + timedelta(days=off)
            for y in range(lo, hi + 1):
                v = ser.get((dd.month, dd.day, y))
                if v is None:        # 2월 29일 · 범위 밖
                    continue
                temps.append(v[0])
                rains.append(v[1])
    if len(temps) < 30:
        return None
    t = np.asarray(temps)
    return (float(t.mean()),
            float((np.asarray(rains) > RAIN_MM).mean()),
            float(np.maximum(0.0, np.abs(t - COMFORT) - BAND).mean()))


def _pct(v: np.ndarray, ok: np.ndarray) -> np.ndarray:
    """관측된 값만으로 백분위. 동률은 평균 순위로 묶는다(노트 292)."""
    from scipy.stats import rankdata
    out = np.zeros(len(v), np.float32)
    if ok.sum() < 3:
        return out
    r = rankdata(v[ok]) - 1.0
    out[ok] = (r / max(ok.sum() - 1, 1)).astype(np.float32)
    n_in, n_out = len(np.unique(v[ok])), len(np.unique(out[ok]))
    if n_out != n_in:
        raise AssertionError(f"_pct 가 동률을 깼다: {n_in} → {n_out}")
    return out


def build(report: bool = False) -> dict:
    """{축이름: {"팝업": (값, 표시자)}} — 팝업 전용.

    시장팝업은 뺐다. ``record_store_link`` 가 팝가 매물(``/popup/<id>``)만
    잇고 시장 레코드는 거기에 안 들어 있다 — 좌표가 없으면 날씨도 없다.
    """
    from .trendaxes import _ids
    ids = (_ids() or {}).get("팝업")
    if not ids:
        return {}
    g = geo()
    link = json.loads(LINK.read_text()) if LINK.exists() else {}
    smeta = {}
    if META.exists():
        smeta = {m["id"]: m.get("date") for m in json.loads(META.read_text())}

    vals = np.full((len(ids), 3), np.nan)
    why: dict[str, int] = {}
    hit_path: dict[str, int] = {}
    cache: dict[str, dict | None] = {}

    def note(k):
        why[k] = why.get(k, 0) + 1

    src: dict[str, int] = {}
    for i, rid in enumerate(ids):
        p = R / f"{rid}.json"
        rec = json.loads(p.read_text()) if p.exists() else {}
        lat, lon, how = latlon_of(rid, link, g, rec)
        src[how] = src.get(how, 0) + 1
        if lat is None:
            note("좌표없음")
            continue
        key = gridkey(lat, lon)
        if key not in cache:
            cache[key] = _series(key)
        ser = cache[key]
        if not ser:
            note("격자미수집")
            continue
        start = _parse(smeta.get(rid)) or _parse(_first(rec, START_PATHS)[0])
        if start is None:
            note("시작일없음")
            continue
        n, path = _first(rec, DAY_PATHS)
        if isinstance(n, (int, float)) and n >= 1:
            days = int(min(n, 180))
            hit_path[path] = hit_path.get(path, 0) + 1
        else:
            end, ep = _first(rec, END_PATHS)
            e = _parse(end)
            if e and e >= start:
                days = min((e - start).days + 1, 180)
                hit_path[ep] = hit_path.get(ep, 0) + 1
            else:
                note("기간없음")
                continue
        c = _clim(ser, start, days)
        if c is None:
            note("평년부족")
            continue
        vals[i] = c

    out = {}
    for j, nm in enumerate(("wx_temp", "wx_rain", "wx_harsh")):
        col = vals[:, j]
        ok = np.isfinite(col)
        if ok.sum() < 30 or len(np.unique(col[ok])) < 3:
            note(f"{nm}·행부족({int(ok.sum())})")
            continue
        out[nm] = {"팝업": (_pct(col, ok), ok.astype(np.float32))}
    if report:
        cov = float(np.isfinite(vals[:, 0]).mean())
        print(json.dumps({"행": len(ids), "덮음": round(cov, 3),
                          "축": list(out), "좌표출처": src,
                          "기간경로": hit_path, "빠진사유": why},
                         ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    build(report=True)
