# -*- coding: utf-8 -*-
"""노트 901 · 지평 팔 ②단계 — **서울 생활인구 250m 격자에 팝업이 붙는가.**

🔴 **효과는 안 잰다. 「붙는지 안 붙는지」만 센다**(887형 회피 — 축을 주입했는데
조용히 중립화되는 사고는 「붙나」를 안 물어서 난다).

여기서 하는 일
  ① 격자 ID 해독 --- 899 §6.3 이 **미확정**으로 남긴 자리다. `다사########` 를
     EPSG:5179(UTM-K) 100km 구역 원점 (900000, 1900000) + 10m 단위로 읽고,
     **저장소가 이미 가진 좌표**로 자기시험한다(알려진 세 점 + 8,594칸 전량 경계).
  ② 팝업 쪽 열쇠 전수 계수 --- **분모를 셋으로 따로**(원천 파일 · 축행 · 유보 채점행).
  ③ 매칭률 --- 좌표 → 격자, 주소/동네 → 시군구.
  ④ 날짜 겹침 --- **받아 둔 두 달**과 **원천이 가진 지평** 둘을 따로 센다.
  ⑤ 결정적 수 하나 --- 좌표 있고 · 격자에 붙고 · 날짜 겹치는 팝업.

입력
  <스크래치패드>/out901h_gridmap.json   (runners/out901h_lifepop.py 가 만든다)
  data/state/record_store_link.json · record_store_link_verified.json
  data/state/platform_spots.csv · data/state/spot_addr.json
  data/records/*.json · data/market_records/*.json · data/state/market_axes.json
  data/state/popup_v2.npz · popup_v2_meta.json

산출물: runners/out901h_link.json
사용:  python3 runners/out901h_link.py
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
SCRATCH = Path(os.environ.get(
    "OUT901H_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad"))
GRIDMAP = SCRATCH / "out901h_gridmap.json"
OUT = ROOT / "runners/out901h_link.json"

#: 🔴 **받아 둔 두 달**(runners/out901h_grid.json 실측). 원천은 더 길다(§날짜).
HAVE = ("2026-06-01", "2026-07-31")

STAMP_CODE = ("runners/out901h_link.py", "runners/out901h_lifepop.py",
              "ingest/link_audit.py", "ingest/visitors.py", "lab/popupset.py")
STAMP_INPUT = ("data/state/record_store_link.json",
               "data/state/record_store_link_verified.json",
               "data/state/platform_spots.csv",
               "data/state/spot_addr.json",
               "data/state/market_axes.json",
               "data/state/popup_v2_meta.json",
               "runners/out901h_grid.json")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "🔴 파일 없음"


def stamp() -> dict:
    return {"시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "🔴 코드 sha256(이게 자다)": {c: sha(ROOT / c) for c in STAMP_CODE},
            "🔴 입력 파일 sha256": {c: sha(ROOT / c) for c in STAMP_INPUT}}


# ── ① 격자 해독 (EPSG:5179 · GRS80 횡메르카토르) ────────────────────────────
A_ = 6378137.0
F_ = 1 / 298.257222101
E2 = 2 * F_ - F_ * F_
EP2 = E2 / (1 - E2)
LAT0, LON0, K0, FE, FN = math.radians(38.0), math.radians(127.5), 0.9996, 1e6, 2e6
#: `다사` 100km 구역의 원점(EPSG:5179 미터). 🔴 **가설이고, 아래 자기시험이 판정한다.**
SQ_E, SQ_N, CELL = 900_000.0, 1_900_000.0, 250.0


def _M(p: float) -> float:
    return A_ * ((1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256) * p
                 - (3 * E2 / 8 + 3 * E2 ** 2 / 32 + 45 * E2 ** 3 / 1024) * math.sin(2 * p)
                 + (15 * E2 ** 2 / 256 + 45 * E2 ** 3 / 1024) * math.sin(4 * p)
                 - (35 * E2 ** 3 / 3072) * math.sin(6 * p))


M0 = _M(LAT0)


def tm_fwd(lat: float, lon: float) -> tuple[float, float]:
    p, l = math.radians(lat), math.radians(lon)
    N = A_ / math.sqrt(1 - E2 * math.sin(p) ** 2)
    T = math.tan(p) ** 2
    C = EP2 * math.cos(p) ** 2
    a = (l - LON0) * math.cos(p)
    x = FE + K0 * N * (a + (1 - T + C) * a ** 3 / 6
                       + (5 - 18 * T + T * T + 72 * C - 58 * EP2) * a ** 5 / 120)
    y = FN + K0 * (_M(p) - M0 + N * math.tan(p) * (
        a ** 2 / 2 + (5 - T + 9 * C + 4 * C * C) * a ** 4 / 24
        + (61 - 58 * T + T * T + 600 * C - 330 * EP2) * a ** 6 / 720))
    return x, y


def tm_inv(x: float, y: float) -> tuple[float, float]:
    e1 = (1 - math.sqrt(1 - E2)) / (1 + math.sqrt(1 - E2))
    M = M0 + (y - FN) / K0
    mu = M / (A_ * (1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256))
    p1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
          + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
          + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
          + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    C1 = EP2 * math.cos(p1) ** 2
    T1 = math.tan(p1) ** 2
    N1 = A_ / math.sqrt(1 - E2 * math.sin(p1) ** 2)
    R1 = A_ * (1 - E2) / (1 - E2 * math.sin(p1) ** 2) ** 1.5
    D = (x - FE) / (N1 * K0)
    lat = p1 - (N1 * math.tan(p1) / R1) * (
        D * D / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * EP2) * D ** 4 / 24
        + (61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * EP2 - 3 * C1 * C1) * D ** 6 / 720)
    lon = LON0 + (D - (1 + 2 * T1 + C1) * D ** 3 / 6
                  + (5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * EP2 + 24 * T1 * T1) * D ** 5 / 120) / math.cos(p1)
    return math.degrees(lat), math.degrees(lon)


def grid_of(lat: float, lon: float) -> str:
    x, y = tm_fwd(lat, lon)
    e = int(math.floor((x - SQ_E) / CELL)) * 25
    n = int(math.floor((y - SQ_N) / CELL)) * 25
    if not (0 <= e <= 9999 and 0 <= n <= 9999):
        return "🔴 `다사` 구역 밖"          # 100km 구역을 벗어나면 이 ID 체계로 못 적는다
    return "다사%04d%04d" % (e, n)


#: 서울 외접상자 --- 격자 8,594칸 전량의 중심이 이 안에 든다(자기시험 ㄴ).
SEOUL_BOX = (37.40, 37.72, 126.74, 127.21)


def in_seoul_box(lat: float, lon: float) -> bool:
    return SEOUL_BOX[0] <= lat <= SEOUL_BOX[1] and SEOUL_BOX[2] <= lon <= SEOUL_BOX[3]


def grid_center(gid: str) -> tuple[float, float]:
    e, n = int(gid[2:6]), int(gid[6:10])
    return tm_inv(SQ_E + e * 10 + CELL / 2, SQ_N + n * 10 + CELL / 2)


# ── 자잘한 도구 ────────────────────────────────────────────────────────────
def d10(s) -> str | None:
    s = str(s or "")[:10]
    return s if len(s) == 10 and s[4] == "-" else None


def overlaps(f, t, lo, hi) -> bool:
    f, t = d10(f), d10(t) or d10(f)
    return bool(f and t and f <= hi and t >= lo)


def fnum(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


# ── ② 분모 셋 만들기 ───────────────────────────────────────────────────────
def internal_records() -> dict:
    return {json.loads(Path(f).read_text())["record_id"]: json.loads(Path(f).read_text())
            for f in sorted(glob.glob(str(ROOT / "data/records/*.json")))}


def market_records() -> dict:
    out = {}
    for f in sorted(glob.glob(str(ROOT / "data/market_records/*.json"))):
        r = json.loads(Path(f).read_text())
        out[r["market_record_id"]] = r
    return out


def popup_axis_ids() -> list[str]:
    """판이 쓰는 **넓힌 팝업 89행**의 id --- `lab/popupset.build` 의 keep 을 그대로 옮겼다."""
    from lab.popupset import COUNT_OK
    z = np.load(ROOT / "data/state/popup_v2.npz", allow_pickle=True)
    cols = [str(c) for c in z["names"]]
    X, y = z["X"], z["y_perday"]
    meta = json.loads((ROOT / "data/state/popup_v2_meta.json").read_text())
    keep = np.zeros(len(y), bool)
    for g in ("A", "B", "C", "D", "E"):
        j = cols.index(f"trust_{g}") if f"trust_{g}" in cols else None
        if j is not None:
            keep |= X[:, j] > 0.5
    keep &= np.isfinite(y)
    keep &= np.array([bool(m.get("scope_usable")) for m in meta])
    keep &= np.array([m.get("counting") in COUNT_OK for m in meta])
    return [m["id"] for m, k in zip(meta, keep) if k]


def holdout_ids(axis_ids: dict) -> dict:
    """판의 **유보 채점행**(post=True & labeled) id --- 챔피언 자료 build 를 그대로 쓴다."""
    import sys
    sys.path.insert(0, str(ROOT / "runners"))
    import ff753 as FF                                    # noqa: E402
    d0 = FF.shell(FF.base())
    out, chk = {}, {}
    for dom in ("팝업", "시장팝업"):
        k = d0.rows(dom, post=True, labeled=True, T=2025.0)
        ids = axis_ids[dom]
        chk[dom] = {"축행(자료)": int(len(k)), "축행(내 id 목록)": len(ids),
                    "길이 일치": len(k) == len(ids), "유보 채점행": int(k.sum())}
        assert len(k) == len(ids), f"🔴 {dom} 행 수 불일치 — 매칭 중단"
        out[dom] = [i for i, kk in zip(ids, k) if kk]
    return out, chk


# ── ③ 좌표 열쇠 ────────────────────────────────────────────────────────────
def spot_table() -> dict:
    return {r["spot_id"]: r for r in csv.DictReader((ROOT / "data/state/platform_spots.csv").open())}


def link_coords(spots: dict) -> tuple[dict, dict]:
    """레코드 id → 좌표. **검증(기간 겹침 ±7일) 통과분과 원(原)링크를 따로 낸다.**

    🔴 `ingest/link_audit.py:56` 은 `data/records` 만 훑는다 --- 원링크 555 중
    **MKT 가 348** 인데 감사가 그것을 한 번도 안 봤다. 여기서 같은 규칙(±7일)을
    시장팝업에도 적용해 따로 센다."""
    link = json.loads((ROOT / "data/state/record_store_link.json").read_text())
    ver = json.loads((ROOT / "data/state/record_store_link_verified.json").read_text())
    raw = {}
    for k, v in link.items():
        sid = str((v or {}).get("store", "")).rsplit("/", 1)[-1]
        sp = spots.get(sid)
        if not sp:
            continue
        la, lo = fnum(sp.get("latitude")), fnum(sp.get("longitude"))
        raw[k] = {"spot_id": sid, "lat": la, "lon": lo,
                  "addr": (sp.get("road_address") or sp.get("address") or "").strip(),
                  "open": d10(sp.get("open_date")), "close": d10(sp.get("close_date"))}
    return raw, ver


def gap_days(rf, rt, so, sc) -> int | None:
    rf, rt = d10(rf), d10(rt) or d10(rf)
    so, sc = d10(so), d10(sc) or d10(so)
    if not (rf and rt and so and sc):
        return None
    f = dt.date.fromisoformat(rf)
    t = dt.date.fromisoformat(rt)
    o = dt.date.fromisoformat(so)
    c = dt.date.fromisoformat(sc)
    return max((f - c).days if c < f else 0, (o - t).days if o > t else 0)


def _tally_prefix(ids) -> dict:
    out = {}
    for i in ids:
        k = "MKT(시장 레코드)" if str(i).startswith("MKT") else "R*(내부 레코드)"
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def main() -> None:
    res = {"노트": 901, "갈래": "지평(⓪-나) ②단계 — 붙는지만 판정",
           "🔴 자": "뗐다 — 계수와 매칭률만. 효과 추정 없음 · 채택/기각 없음",
           **stamp()}

    # ── 격자 지도 ──────────────────────────────────────────────────────
    if not GRIDMAP.exists():
        res["🔴 중단"] = f"{GRIDMAP} 이 없다 — runners/out901h_lifepop.py 를 먼저 돌려라"
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        raise SystemExit(f"🔴 {GRIDMAP} 없음")
    g2d = json.loads(GRIDMAP.read_text())["격자→행정동코드"]
    GRIDS = set(g2d)
    SGG = {d[:5] for v in g2d.values() for d in v}

    # ── ① 격자 해독 자기시험 ──────────────────────────────────────────
    known = [("성수 · 벤시몽 팝업(spot 3208)", 37.542614, 127.05308, "11200"),
             ("여의대로 108(spot 474)", 37.525436, 126.929085, "11560"),
             ("대구 중구 달구벌대로 2077(spot 2246 · 서울 밖 음성대조)",
              35.8666, 128.59071, None)]
    ktab = []
    for nm, la, lo, exp in known:
        g = grid_of(la, lo)
        got = sorted({d[:5] for d in g2d.get(g, [])})
        ktab.append({"점": nm, "격자": g, "격자가 자료에 있나": g in GRIDS,
                     "격자의 시군구": got, "기대": exp,
                     "맞나": (exp in got) if exp else (g not in GRIDS)})
    ctr = [grid_center(g) for g in GRIDS]
    lats = [c[0] for c in ctr]
    lons = [c[1] for c in ctr]
    inbox = sum(1 for a, b in ctr if 37.40 <= a <= 37.72 and 126.74 <= b <= 127.21)
    res["① 격자 ID 해독 — 🔴 899 §6.3 이 미확정으로 남긴 자리"] = {
        "가설": "`다사` = EPSG:5179 100km 구역, 원점 (900000, 1900000) · 뒤 8자리는 10m 단위 (동,북)",
        "투영": "GRS80 횡메르카토르 lat0=38 lon0=127.5 k0=0.9996 FE=1e6 FN=2e6 (직접 구현 · pyproj 없음)",
        "자기시험 ㄱ 알려진 점": ktab,
        "자기시험 ㄱ 통과": all(r["맞나"] for r in ktab),
        "자기시험 ㄴ 격자 전량 → 위경도": {
            "격자 수": len(GRIDS),
            "위도 범위": [round(min(lats), 5), round(max(lats), 5)],
            "경도 범위": [round(min(lons), 5), round(max(lons), 5)],
            "서울 외접상자 안": inbox, "밖": len(GRIDS) - inbox,
            "안 비율": round(inbox / len(GRIDS), 6)},
        "🔴 남은 사각": ("WGS84 와 Korea2000(GRS80) 을 같게 봤다 --- 250m 칸에서 무시할 만하지만 "
                      "정밀 좌표변환기로 대조하진 않았다(pyproj 없음)")}

    # ── ② 분모 ────────────────────────────────────────────────────────
    IR = internal_records()
    MR = market_records()
    mkax = json.loads((ROOT / "data/state/market_axes.json").read_text())
    axis_ids = {"팝업": popup_axis_ids(), "시장팝업": list(mkax)}
    hold, hchk = holdout_ids(axis_ids)

    DEN = {
        "팝업": {"원천 파일(data/records/*.json)": sorted(IR),
                "축행(판이 쓰는 넓힌 팝업)": axis_ids["팝업"],
                "유보 채점행": hold["팝업"]},
        "시장팝업": {"원천 파일(data/market_records/*.json)": sorted(MR),
                   "축행(data/state/market_axes.json)": axis_ids["시장팝업"],
                   "유보 채점행": hold["시장팝업"]},
    }
    res["② 분모 — 🔴 셋을 따로 센다(조항 60)"] = {
        "행 수 대조": hchk,
        "분모": {d: {k: len(v) for k, v in DEN[d].items()} for d in DEN},
        "유보 합(12도메인 3,775 중 팝업 둘)":
            len(hold["팝업"]) + len(hold["시장팝업"]),
        "대조 — runners/out900a_design.json 의 채점행": {"팝업": 65, "시장팝업": 126},
        "🔴 「팝업」 도메인은 내부 팝업만이 아니다": {
            "무엇": ("`data/state/popup_v2_meta.json` 376행의 `domain` 은 "
                   "popup_market 277 · popup_internal 99 다. 넓힌 팝업(grades A~E)은 **둘을 섞는다**."),
            "축행 89 의 id 접두": _tally_prefix(axis_ids["팝업"]),
            "유보 65 의 id 접두": _tally_prefix(hold["팝업"]),
            "🔴 그래서": ("「팝업 대 시장팝업」이 **레코드 출처로 갈리는 두 도메인이 아니다** — "
                       "MKT 레코드가 두 도메인에 **둘 다** 들어간다. 아래 계수는 그 사실 위에서 읽어라"),
            "두 도메인의 유보가 실제로 겹치는 id 수":
                len(set(hold["팝업"]) & set(hold["시장팝업"])),
        },
    }

    # ── ③ 열쇠 전수 계수 ──────────────────────────────────────────────
    spots = spot_table()
    raw, ver = link_coords(spots)
    addr_by_spot = json.loads((ROOT / "data/state/spot_addr.json").read_text())

    def period(rid):
        r = IR.get(rid)
        if r:
            p = r["conditions"].get("period") or {}
            return d10(p.get("from")), d10(p.get("to")) or d10(p.get("from"))
        m = MR.get(rid)
        if m:
            c = m["conditions"]
            return d10(c.get("period_from")), d10(c.get("period_to")) or d10(c.get("period_from"))
        a = mkax.get(rid)
        if a:
            return d10(a.get("period_from")), d10(a.get("period_from"))
        return None, None

    def keys_of(rid):
        """레코드가 **이미 가진** 열쇠를 전부 편다(조항 60: 다 써 봤는지 먼저 세라)."""
        k = {"lat": None, "lon": None, "addr": None, "city": None, "district": None,
             "venue": None, "neighborhood": None, "gap": None, "src": None}
        r, m = IR.get(rid), MR.get(rid)
        if r:
            L = r["conditions"].get("location") or {}
            k["city"], k["district"] = L.get("city"), L.get("district")
            k["venue"] = L.get("venue_name")
        if m:
            c = m["conditions"]
            k["city"], k["venue"] = c.get("city"), c.get("venue")
            k["neighborhood"] = c.get("neighborhood")
        v = ver.get(rid)
        if v and fnum(v.get("lat")) is not None:
            k.update(lat=fnum(v["lat"]), lon=fnum(v["lon"]),
                     addr=v.get("addr") or None, gap=v.get("gap_days"), src="검증 링크")
        elif rid in raw and raw[rid]["lat"] is not None:
            rf, rt = period(rid)
            g = gap_days(rf, rt, raw[rid]["open"], raw[rid]["close"])
            k.update(lat=raw[rid]["lat"], lon=raw[rid]["lon"],
                     addr=raw[rid]["addr"] or None, gap=g, src="원링크(미검증)")
        if k["addr"] is None and rid in raw:
            k["addr"] = addr_by_spot.get(raw[rid]["spot_id"]) or None
        return k

    def census(ids):
        n = len(ids)
        c = {"분모": n, "좌표(어떤 링크로든)": 0, "좌표(±7일 검증 통과)": 0,
             "좌표(미검증 · 기간 어긋남)": 0, "좌표(기간 대조 불가)": 0,
             "도로명주소": 0, "city": 0, "district(구)": 0, "neighborhood(동)": 0,
             "venue 이름": 0, "🔴 좌표도 주소도 구도 동도 없다": 0}
        for rid in ids:
            k = keys_of(rid)
            has = k["lat"] is not None
            c["좌표(어떤 링크로든)"] += has
            if has:
                if k["gap"] is None:
                    c["좌표(기간 대조 불가)"] += 1
                elif k["gap"] <= 7:
                    c["좌표(±7일 검증 통과)"] += 1
                else:
                    c["좌표(미검증 · 기간 어긋남)"] += 1
            c["도로명주소"] += bool(k["addr"])
            c["city"] += bool(k["city"])
            c["district(구)"] += bool(k["district"])
            c["neighborhood(동)"] += bool(k["neighborhood"])
            c["venue 이름"] += bool(k["venue"])
            if not (has or k["addr"] or k["district"] or k["neighborhood"] or k["city"]):
                c["🔴 좌표도 주소도 구도 동도 없다"] += 1
        return c

    res["③ 팝업 쪽 열쇠 전수 계수 — 분모별로"] = {
        d: {nm: census(ids) for nm, ids in DEN[d].items()} for d in DEN}
    res["③ 🔴 링크 감사 사각"] = {
        "record_store_link.json 총 링크": len(json.loads((ROOT / "data/state/record_store_link.json").read_text())),
        "그중 MKT 접두": sum(1 for k in json.loads((ROOT / "data/state/record_store_link.json").read_text()) if k.startswith("MKT")),
        "🔴 `ingest/link_audit.py:56` 은 `data/records` 만 훑는다":
            "그래서 record_store_link_verified.json 은 **내부 팝업만** 담는다(114건). 시장팝업 링크는 한 번도 감사된 적이 없다",
        "이 러너가 같은 ±7일 규칙을 시장팝업에도 적용했다": True}

    # ── ④ 매칭률 · ⑤ 날짜 · ⑥ 결정적 수 ───────────────────────────────
    def match(ids):
        m = {"분모": len(ids), "좌표 있음": 0, "🔴 격자에 붙음": 0,
             "안 붙음 · 서울 외접상자 **밖**(지방 팝업)": 0,
             "🔴 안 붙음 · 서울 상자 **안**인데 격자에 없다": 0,
             "격자 붙음 · ±7일 검증 통과": 0, "격자 붙음 · 미검증": 0,
             "시군구로 붙음(좌표)": 0, "주소로 시군구 붙음(좌표 없이)": 0,
             "🔴 개최 기간이 아예 없다": 0,
             "받아 둔 두 달과 날짜 겹침": 0,
             "🔴 결정적 수(좌표 · 격자 · 두 달 겹침)": 0,
             "🔴 결정적 수 · 엄격(±7일 검증 통과 좌표만)": 0,
             "참고: 좌표 · 격자 · 원천 지평(2023-01~2026-07) 안": 0,
             "교차확인A 분모(좌표 격자 & spot 주소 문자열)": 0,
             "교차확인A 일치": 0,
             "교차확인B 분모(좌표 격자 & **레코드 자신의** 구/동)": 0,
             "교차확인B 일치": 0,
             "교차확인B · ±7일 통과분 분모": 0, "교차확인B · ±7일 통과분 일치": 0,
             "교차확인B · 미검증분 분모": 0, "교차확인B · 미검증분 일치": 0,
             "🔴 교차확인B 어긋난 id(±7일 통과인데 구가 다르다)": []}
        yrs, need = {}, set()
        for rid in ids:
            k = keys_of(rid)
            f, t = period(rid)
            ov = overlaps(f, t, *HAVE)
            src_h = overlaps(f, t, "2023-01-01", "2026-07-31")
            m["받아 둔 두 달과 날짜 겹침"] += ov
            if f:
                yrs[f[:4]] = yrs.get(f[:4], 0) + 1
            else:
                m["🔴 개최 기간이 아예 없다"] += 1
            if k["lat"] is None:
                # 좌표가 없을 때 남은 길: 주소/구/동 → 시군구
                from ingest.visitors import HOOD, sgg_index, hood_sgg
                idx = sgg_index()
                c = None
                if k["district"] or k["neighborhood"]:
                    c = hood_sgg(k["neighborhood"] or "", k["city"], idx)
                    if c is None and k["district"]:
                        for (s2, n2), cc in idx.items():
                            if n2 and n2 in str(k["district"]):
                                c = cc
                                break
                if c and c in SGG:
                    m["주소로 시군구 붙음(좌표 없이)"] += 1
                continue
            m["좌표 있음"] += 1
            g = grid_of(k["lat"], k["lon"])
            hit = g in GRIDS
            m["🔴 격자에 붙음"] += hit
            if not hit:
                if in_seoul_box(k["lat"], k["lon"]):
                    m["🔴 안 붙음 · 서울 상자 **안**인데 격자에 없다"] += 1
                else:
                    m["안 붙음 · 서울 외접상자 **밖**(지방 팝업)"] += 1
            if hit:
                if k["gap"] is not None and k["gap"] <= 7:
                    m["격자 붙음 · ±7일 검증 통과"] += 1
                else:
                    m["격자 붙음 · 미검증"] += 1
                sg = {d[:5] for d in g2d[g]}
                m["시군구로 붙음(좌표)"] += 1
                # 교차확인: 좌표가 준 시군구 vs 주소 문자열이 준 시군구 이름
                from ingest.visitors import sgg_index
                idx = sgg_index()
                nm_by_code = {c: n for (s2, n), c in idx.items()}
                names = {nm_by_code.get(s) for s in sg if nm_by_code.get(s)}
                # A: 좌표 대 **같은 spot 행의 주소 문자열** --- 투영·해독을 잰다(링크는 못 잰다)
                if names and k["addr"]:
                    m["교차확인A 분모(좌표 격자 & spot 주소 문자열)"] += 1
                    m["교차확인A 일치"] += any(n in str(k["addr"]) for n in names)
                # B: 좌표 대 **레코드 자신이 적은 구/동** --- 🔴 이건 **링크가 맞나**를 잰다
                own = " ".join(str(x) for x in (k["district"], k["neighborhood"]) if x)
                if names and own.strip():
                    m["교차확인B 분모(좌표 격자 & **레코드 자신의** 구/동)"] += 1
                    hitB = any(n in own for n in names)
                    if not hitB:
                        from ingest.visitors import hood_sgg as _hs
                        c2 = _hs(k["neighborhood"] or k["district"] or "", k["city"], idx)
                        hitB = bool(c2 and c2 in sg)
                    m["교차확인B 일치"] += hitB
                    ok7 = k["gap"] is not None and k["gap"] <= 7
                    m["교차확인B · ±7일 통과분 분모" if ok7 else "교차확인B · 미검증분 분모"] += 1
                    m["교차확인B · ±7일 통과분 일치" if ok7 else "교차확인B · 미검증분 일치"] += hitB
                    if ok7 and not hitB:
                        m["🔴 교차확인B 어긋난 id(±7일 통과인데 구가 다르다)"].append(
                            {"id": rid, "격자 시군구": sorted(names), "레코드가 적은 것": own})
                if ov:
                    m["🔴 결정적 수(좌표 · 격자 · 두 달 겹침)"] += 1
                    if k["gap"] is not None and k["gap"] <= 7:
                        m["🔴 결정적 수 · 엄격(±7일 검증 통과 좌표만)"] += 1
                if src_h:
                    m["참고: 좌표 · 격자 · 원천 지평(2023-01~2026-07) 안"] += 1
                    a = dt.date.fromisoformat(max(f, "2023-01-01"))
                    b = dt.date.fromisoformat(min(t or f, "2026-07-31"))
                    while a <= b:
                        need.add(a.strftime("%Y-%m"))
                        a = (a.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        m["개최 시작 연도 분포"] = dict(sorted(yrs.items()))
        m["🔴 이걸 다 쓰려면 받아야 할 달 수(생활인구 월 파일)"] = len(need)
        m["받아야 할 달(정렬)"] = sorted(need)
        m["참고: 달 하나가 ~430MB(899 실측) → 대략 GB"] = round(len(need) * 0.435, 2)
        return m

    res["④⑤⑥ 매칭 · 날짜 · 결정적 수"] = {
        d: {nm: match(ids) for nm, ids in DEN[d].items()} for d in DEN}

    # 🔴 눈으로 본 것은 **몇 건 봤는지** 적는다(조항 60). 표본이 아니라 예시다.
    from ingest.visitors import sgg_index as _si
    _idx = _si()
    _nm = {c: n for (s2, n), c in _idx.items()}
    eye = []
    for dom in ("팝업", "시장팝업"):
        for rid in DEN[dom]["유보 채점행"]:
            if len(eye) >= 12:
                break
            k = keys_of(rid)
            if k["lat"] is None:
                continue
            g = grid_of(k["lat"], k["lon"])
            if g not in GRIDS:
                continue
            f, t = period(rid)
            eye.append({"도메인": dom, "id": rid, "좌표": [k["lat"], k["lon"]],
                        "격자": g, "격자 시군구": sorted({_nm.get(d[:5]) for d in g2d[g]}),
                        "spot 주소": k["addr"], "레코드 구/동": k["district"] or k["neighborhood"],
                        "기간": [f, t], "링크 gap(일)": k["gap"]})
    res["④ 🔴 눈으로 본 예시 — 12건만 봤다(표본이 아니다 · 조항 60)"] = eye
    # 🔴 두 도메인 유보의 **합집합**(중복 id 를 한 번만 센다) — 판 유보 3,775 대비
    uni = sorted(set(DEN["팝업"]["유보 채점행"]) | set(DEN["시장팝업"]["유보 채점행"]))
    um = match(uni)
    res["⑥ 🔴 결정적 수 — 판 유보 기준"] = {
        "팝업 두 도메인 유보 합(중복 제거)": len(uni),
        "판 유보 전체(12도메인)": 3775,
        "그중 팝업 두 도메인 비중": round(len(uni) / 3775, 4),
        "좌표 있음": um["좌표 있음"],
        "🔴 격자에 붙음": um["🔴 격자에 붙음"],
        "격자 붙음 / 팝업 유보": round(um["🔴 격자에 붙음"] / len(uni), 4),
        "격자 붙음 / 판 유보 3,775": round(um["🔴 격자에 붙음"] / 3775, 5),
        "시군구까지만 붙음(좌표 없이 주소·동으로)": um["주소로 시군구 붙음(좌표 없이)"],
        "시군구 수준 총 붙음": um["시군구로 붙음(좌표)"] + um["주소로 시군구 붙음(좌표 없이)"],
        "받아 둔 두 달과 날짜 겹침": um["받아 둔 두 달과 날짜 겹침"],
        "🔴🔴 결정적 수(좌표 · 격자 · **받아 둔 두 달** 겹침)":
            um["🔴 결정적 수(좌표 · 격자 · 두 달 겹침)"],
        "🔴🔴 결정적 수 · 엄격(±7일 검증 좌표만)":
            um["🔴 결정적 수 · 엄격(±7일 검증 통과 좌표만)"],
        "참고: 좌표 · 격자 · **원천이 가진 지평**(2023-01~2026-07) 안":
            um["참고: 좌표 · 격자 · 원천 지평(2023-01~2026-07) 안"],
        "그 지평을 채우려면 받아야 할 월 파일 수": um["🔴 이걸 다 쓰려면 받아야 할 달 수(생활인구 월 파일)"],
        "교차확인A(투영·해독)": [um["교차확인A 일치"], um["교차확인A 분모(좌표 격자 & spot 주소 문자열)"]],
        "교차확인B(링크) · ±7일 통과분":
            [um["교차확인B · ±7일 통과분 일치"], um["교차확인B · ±7일 통과분 분모"]],
        "교차확인B(링크) · 미검증분":
            [um["교차확인B · 미검증분 일치"], um["교차확인B · 미검증분 분모"]],
        "🔴 ±7일 통과인데 구가 다른 id":
            um["🔴 교차확인B 어긋난 id(±7일 통과인데 구가 다르다)"],
    }
    res["④⑤⑥ 🔴 날짜 분모 둘을 갈라 적는다"] = {
        "받아 둔 것": {"기간": list(HAVE), "출처": "runners/out901h_grid.json 실측"},
        "원천이 가진 것": {
            "기간": "2023-01 ~ 2026-07",
            "월별 파일": 43, "일별 파일": 6, "일별 범위": ["20260801", "20260806"],
            "🔴 빠진 달": [],
            "월별 포털표기 합": "20,348.8 MB (≈20.3GB)",
            "출처": ("🔴 899 인용이 아니라 **내가 오늘 다시 셌다** — "
                   "`python3 -m ingest.seoul_lifepop --list` "
                   "(2026-08-11 KST = 2026-08-10 UTC · 무료 포털 · 유료 API 아님)")},
        "🔴 그래서": "「안 붙는다」의 원인이 **자료의 성질이 아니라 내가 받은 두 달**인지 갈라야 한다"}

    res["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["④⑤⑥ 매칭 · 날짜 · 결정적 수"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
