"""지역 방문자 축 — 문턱을 넘은 첫 상태 축이고, **닫혔다**(노트 668·674).

.. warning::

   **이 축은 서랍에 있다. 다시 돌리기 전에 노트 668·674 를 읽는다.**

   신호 몫 **+0.0064 > 문턱 0.0045** 로 이 판 최초로 위약을 이긴 상태 축이다
   (노트 662). 그런데 **순효과는 +0.0016** 이라 채택이 아니고, 행을 늘리는 두
   길이 **둘 다 측정으로 닫혔다**:

   ⒜ **학습/유보 경계 이동 기각**(노트 668). ``T=2026`` 에서 순효과가 7.2배
      (+0.0115 · 12/12) 오르고 되뽑기 문턱 0.0125 대비 비가 0.36 → 0.92 로
      좋아졌는데 **위약이 −0.0048 → +0.0074 로 부호가 뒤집혀** 신호 몫이
      0.64배로 줄었다. 원인은 **시장팝업 유보 40행** --- 진짜의 87% · 위약의
      76% 를 내고 40행 ρ 의 표본 SD 0.158 안에서 둘이 구별되지 않는다.
      **같은 행을 학습으로 옮기는 것은 자를 부러뜨려 자를 통과하는 일이다.**

   ⒝ **덮음 확장 기각**(노트 674). 세 번째 도메인 후보인 아이돌은 덮음
      31/281 = 0.110 이고, 31건을 눈으로 가르면 **유효 13 · 시간 게이트 위반
      12**(데뷔 *이후* 팝업 개최지 --- 라벨은 데뷔주 초동이다) **· 위양성 6**
      으로 **유효 덮음 0.046** 이다(게이트 0.7 의 15분의 1).
      **판의 열한 도메인 중 장소를 가진 것은 팝업 계열 둘이 전부다.**

   **닫은 것은 축이 아니라 지금 자료에서의 확장 경로다.** KOPIS 로 공연
   도메인이 서면 장소를 가진 세 번째 도메인이 생기고, 그때 다시 연다.
   다시 열 때 **`_mkt_place` 의 매칭 근거를 표본 20건 눈으로 확인한다** ---
   노트 674 가 자유 텍스트에서 위양성 19% 를 쟀다(``hood_sgg`` 가 부분
   문자열로 붙어 멤버 이름 '미아' 를 강북구 미아동으로 읽었다). 시장팝업은
   구조화된 필드를 쓰므로 위험이 낮지만 **안 쟀다.**

--- 아래는 축을 세울 때의 기록이다 ---

상태층에서 **처음으로 스케일이 맞는** 신호(노트 641).

노트 638 이 날씨 축을 재고 떨어뜨렸다(팝업 −0.0283 · 12/12 음수). 그 실패를
해부하면 원인 후보가 셋이었고, 그중 **하나는 자료 자체의 성질**이었다 ---
팝업 66행 중 54행이 서울이라 *지역 차가 아예 없었다*. 평년 날씨는 사실상
``cal_month_*`` 의 복사본이 됐다.

이 축은 그 지점이 다르다. 시군구 분포가 **성동구 21 · 영등포구 12 · 강남구 7
· 중구 5** 로 실제로 갈린다. 그리고 자릿수가 맞는다 --- `data/encoder/README.md`
가 popga 프록시 실패의 원인으로 적은 *"모집단 스케일 불일치(조회 중앙값 86명
대 실제 방문 수천~수만)"* 가 여기서는 성동구 하루 **외지인 36만 명**이다.

**시간 게이트.** 오픈 **이전** 창만 본다. 운영 기간 중의 값은 두 이유로 안
쓴다 --- ① 기획 시점에 모른다 ② 팝업 자신이 그 숫자에 기여하므로 역인과다.

축 셋(``AXES`` 로 줄일 수 있다).

    vis_out    오픈 이전 30일 **외지인** 일평균 --- 그 동네의 외부 유입 규모
    vis_mom    최근 30일 / 그 이전 60일 비율 --- **그 동네가 뜨고 있나**
    vis_share  외지인 / (현지인+외지인) --- 관광지성. 사는 곳인가 오는 곳인가

**왜 외지인인가.** 그 동네에 사는 사람이 아니라 밖에서 온 사람이 팝업을 찾는다.
현지인은 분모 쪽(``vis_share``)으로만 쓴다.

**축을 줄일 수 있게 해 둔 이유.** 노트 638 의 위약이 가르는 것이 *"신호가
틀렸나, 열을 더한 것이 문제인가"* 다. 후자라면 축 수 자체가 비용이므로
``AXES=("vis_out",)`` 처럼 하나만 넣고 재야 한다.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from ingest.visitors import ADDR, LINK, RECS, sgg_index, sgg_of, series

META = Path("data/state/popup_v2_meta.json")

#: 몇 개를 넣나. 측정할 때 바꾼다.
AXES = ("vis_out", "vis_mom", "vis_share")

NEAR = 30        # 오픈 직전 창(일)
FAR = 90         # 비교 창의 끝 --- [open-FAR, open-NEAR) 가 '그 이전'
MIN_DAYS = 15    # 창 안에 관측이 이만큼은 있어야 쓴다


def _parse(s) -> date | None:
    if not isinstance(s, str) or len(s) < 8:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _mean(ser: dict, a: date, b: date) -> tuple:
    """[a, b) 구간 평균과 관측 일수."""
    v = [ser[k] for k in ((a + timedelta(days=i)).strftime("%Y%m%d")
                          for i in range((b - a).days)) if k in ser]
    return (float(np.mean(v)) if v else np.nan), len(v)


def _pct(v: np.ndarray, ok: np.ndarray) -> np.ndarray:
    """관측된 값만으로 백분위. 동률은 평균 순위로(노트 292)."""
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


#: 어느 도메인에 붙나. **시장팝업을 더했다**(노트 660).
#:
#: 노트 641 은 팝업 89행에만 붙였다 --- `_ids()['팝업']` 만 읽었기 때문이다.
#: 그런데 시장팝업 249행도 장소가 있다: `record_store_link` 에 121건이고
#: 도로명주소로 시군구가 **107건** 붙는다. 날짜는 `data/records` 가 아니라
#: **`data/state/market_axes.json` 의 `period_from`** 에 249건 전부 있다.
#:
#: 노트 641 에서 팝업 1열이 +0.009 로 이 판의 유일한 양수였는데 89행이라
#: 열값(ρ 0.02~0.025)에 묻혔다. 노트 650 이 *두꺼운 도메인은 벌고 얇은
#: 도메인은 낸다* 를 쟀으므로 세 배 두꺼운 도메인을 같이 붙여 본다.
DOMS = ("팝업", "시장팝업")

#: 시장팝업 날짜 저장소 --- 레코드 파일이 없어서 여기서 읽는다
MKT = Path("data/state/market_axes.json")
#: 시장팝업 **원천** --- 기사에서 만든 레코드. `venue`·`neighborhood`·`city` 가 있다
MKT_RAW = Path("data/market_records")


def _mkt_place(rid: str, idx: dict, cache: dict = {}):
    """시장팝업 시군구 --- 도로명주소가 없으니 원천 텍스트에서 찾는다(노트 661).

    순서: ① `venue`·`neighborhood`·`city` 에 **시군구 이름이 직접** 들어 있나
    ② 없으면 `neighborhood` 의 **동 이름**을 `HOOD` 표로 구에 매핑한다.

    노트 660 이 시장팝업 덮음 0.43 을 손해의 원인으로 특정했고, 위약이 그
    증거였다(값을 섞으면 −0.0227 → +0.0151 로 나아진다). 남은 125건 중
    **91건이 서울**이고 `neighborhood` 가 동 이름이라 표 하나로 붙는다.
    """
    from ingest.visitors import hood_sgg
    if not cache:
        for f in MKT_RAW.glob("*.json"):
            try:
                j = json.loads(f.read_text())
            except Exception:
                continue
            cache[j.get("market_record_id")] = (j.get("conditions") or {})
    cond = cache.get(rid)
    if not cond:
        return None, "원천없음"
    for txt in (cond.get("neighborhood"), cond.get("venue"), cond.get("city")):
        if not isinstance(txt, str):
            continue
        for (_sd, nm), cd in idx.items():
            if nm and len(nm) >= 2 and nm in txt:
                return cd, "시군구이름"
    c = hood_sgg(cond.get("neighborhood"), cond.get("city"), idx)
    if c:
        return c, "동이름"
    # ③ `city` 만으로 시군구가 정해지는 곳(노트 662). **광역시는 안 붙인다** —
    #    구가 여러 개라 대표 구를 넣으면 방문자 값이 틀린 구에서 온다.
    from ingest.visitors import city_sgg
    c = city_sgg(cond.get("city"), idx)
    if c:
        return c, "city만"
    # `venue` 에서 동 단서를 한 번 더 (스타필드 하남 · 신세계 센텀시티 …)
    c = hood_sgg(cond.get("venue"), cond.get("city"), idx)
    if c:
        return c, "venue동"
    c = city_sgg(cond.get("venue"), idx)
    return (c, "venue시") if c else (None, "위치없음")


def _dates_of(dom: str, ids: list, smeta: dict) -> list:
    """도메인별 시작일. **시장팝업은 저장소가 다르다.**"""
    if dom == "시장팝업":
        mk = json.loads(MKT.read_text()) if MKT.exists() else {}
        return [_parse((mk.get(k) or {}).get("period_from")) for k in ids]
    out = []
    for rid in ids:
        p = Path(RECS) / f"{rid}.json"
        rec = json.loads(p.read_text()) if p.exists() else {}
        out.append(_parse(smeta.get(rid)) or _parse(
            ((rec.get("conditions") or {}).get("period") or {}).get("from")))
    return out


def build(report: bool = False, axes: tuple = None) -> dict:
    """{축이름: {도메인: (값, 표시자)}} — 팝업 · 시장팝업."""
    axes = axes or AXES
    from .trendaxes import _ids
    allids = _ids() or {}
    if not allids.get("팝업"):
        return {}
    out_ser, loc_ser = series("2"), series("1")     # 외지인 · 현지인
    if not out_ser:
        return {}
    idx = sgg_index()
    link = json.loads(Path(LINK).read_text()) if Path(LINK).exists() else {}
    addr = json.loads(Path(ADDR).read_text()) if Path(ADDR).exists() else {}
    smeta = {}
    if META.exists():
        smeta = {m["id"]: m.get("date") for m in json.loads(META.read_text())}

    out: dict = {nm: {} for nm in ("vis_out", "vis_mom", "vis_share")}
    rep: dict = {}
    for dom in DOMS:
        ids = allids.get(dom) or []
        if not ids:
            continue
        why: dict = {}
        src: dict = {}

        def note(k, _w=why):
            _w[k] = _w.get(k, 0) + 1

        starts = _dates_of(dom, ids, smeta)
        vals = np.full((len(ids), 3), np.nan)
        for i, rid in enumerate(ids):
            p = Path(RECS) / f"{rid}.json"
            rec = json.loads(p.read_text()) if p.exists() else {}
            code, how = sgg_of(rid, idx, link, addr, rec)
            if not code and dom == "시장팝업":
                code, how = _mkt_place(rid, idx)     # 노트 661
            src[how] = src.get(how, 0) + 1
            if not code or code not in out_ser:
                note("시군구없음")
                continue
            start = starts[i]
            if start is None:
                note("시작일없음")
                continue
            near, n1 = _mean(out_ser[code], start - timedelta(days=NEAR), start)
            far, n2 = _mean(out_ser[code], start - timedelta(days=FAR),
                            start - timedelta(days=NEAR))
            if n1 < MIN_DAYS:
                note("창부족")
                continue
            loc, _ = _mean(loc_ser.get(code, {}),
                           start - timedelta(days=NEAR), start)
            vals[i, 0] = near
            vals[i, 1] = (near / far) if (n2 >= MIN_DAYS and far and far > 0) else np.nan
            vals[i, 2] = ((near / (near + loc))
                          if np.isfinite(loc) and (near + loc) else np.nan)

        for j, nm in enumerate(("vis_out", "vis_mom", "vis_share")):
            if nm not in axes:
                continue
            col = vals[:, j]
            ok = np.isfinite(col)
            if ok.sum() < 30 or len(np.unique(col[ok])) < 3:
                note(f"{nm}·행부족({int(ok.sum())})")
                continue
            # **백분위는 도메인 안에서 매긴다.** 도메인을 합쳐 매기면 지역
            # 분포 차이가 도메인 지시자로 새어 든다(노트 646 이 잰 기제).
            out[nm][dom] = (_pct(col, ok), ok.astype(np.float32))
        rep[dom] = {"행": len(ids),
                    "덮음": round(float(np.isfinite(vals[:, 0]).mean()), 3),
                    "코드출처": src, "빠진사유": why}

    out = {k: v for k, v in out.items() if v}
    if report:
        print(json.dumps({"축": list(out), "도메인별": rep},
                         ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    build(report=True)
