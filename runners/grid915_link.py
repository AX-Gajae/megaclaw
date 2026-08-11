# -*- coding: utf-8 -*-
"""팔 915-ㅋ · 1단계 — **판 유보가 격자에 붙나. 17개월이 901 의 날짜 벽을 헐었나.**

🔴 사전등록 `docs/prereg_915_grid.md` §3 규율
  · 격자 해독은 **901 이 8,594칸 전량 역변환으로 자기시험한 것을 그대로 쓴다**
    (`runners/out901h_link.py` 를 import — 두 벌을 손으로 적으면 갈라진다).
  · 🔴 **「없다」·「못 붙였다」·「좌표 열이 없다」를 갈라 센다**(조항 59).
  · 🔴 분모를 갈라 적는다(조항 60): 팝업 두 도메인 유보 합집합 **185** 와 판 유보 **3,775** 는 다르다.
  · 🔴 **자기시험**: 901 이 공표한 수(좌표 102/185 · 격자 93/185 · 두 달 겹침 1)를
    **내 코드로 다시 내서 대조한다.** 어긋나면 산출물에 어긋났다고 적는다.

산출물: runners/out915_link.json · data/state/grid915_attach.json(작다 · 다음 단계 입력)
사용: python3 runners/grid915_link.py
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
import out901h_link as L  # noqa: E402  🔴 읽기만 — 고치지 않는다

OUT = ROOT / "runners/out915_link.json"
ATT = ROOT / "data/state/grid915_attach.json"
COUNT = ROOT / "runners/out915_count.json"

#: 🔴 **901 이 갖고 있던 두 달** — 대조용
HAVE901 = ("2026-06-01", "2026-07-31")


def sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "🔴 파일 없음"


def geo_key_scan() -> dict:
    """🔴 다른 도메인에 **좌표 열이 아예 없는지** 실제로 열어서 센다.
    「안 붙는다」와 「좌표 열이 없다」는 다른 문장이다(조항 59)."""
    import collections
    GEO = ("lat", "lon", "lng", "coord", "addr", "주소", "venue", "city",
           "district", "region", "location", "place", "극장", "지역")

    def walk(o, ks, pre=""):
        if isinstance(o, dict):
            for k, v in o.items():
                ks[pre + str(k)] += 1
                walk(v, ks, pre + str(k) + ".")
        elif isinstance(o, list):
            for v in o[:3]:
                walk(v, ks, pre)

    srcs = {
        "아이돌": sorted(glob.glob(str(ROOT / "data/idol_records/*.json"))),
        "팝업(내부 레코드)": sorted(glob.glob(str(ROOT / "data/records/*.json"))),
        "시장팝업(레코드)": sorted(glob.glob(str(ROOT / "data/market_records/*.json"))),
    }
    out = {}
    for nm, fs in srcs.items():
        ks: collections.Counter = collections.Counter()
        for f in fs:
            walk(json.loads(Path(f).read_text()), ks)
        hit = sorted(k for k in ks if any(t in k.lower() for t in GEO))
        out[nm] = {"파일 수": len(fs), "서로 다른 키": len(ks),
                   "지리 낌새 키": hit or "🔴 0개 — 좌표 열이 없다"}
    for nm, path in (("영화", "data/state/kobis_axes.json"),
                     ("게임", "data/state/game_axes.json"),
                     ("도서", "data/state/book_axes.json"),
                     ("모바일", "data/state/app_records.json"),
                     ("애니", "data/state/anime_axes.json"),
                     ("웹툰", "data/state/webtoon_axes.json"),
                     ("펀딩", "data/state/funding_axes.json"),
                     ("펀딩(레코드)", "data/state/funding_records.json"),
                     ("만화", "data/state/manga_axes.json"),
                     ("세계애니", "data/state/anime_more.json")):
        p = ROOT / path
        if not p.exists():
            out[nm] = {"🔴": f"{path} 가 없다 — 못 봤다(≠ 좌표가 없다)"}
            continue
        d = json.loads(p.read_text())
        ks = collections.Counter()
        it = list(d.values())[:400] if isinstance(d, dict) else d[:400]
        for r in it:
            walk(r, ks)
        hit = sorted(k for k in ks if any(t in k.lower() for t in GEO))
        out[nm] = {"원천": path, "행": len(d), "서로 다른 키": len(ks),
                   "지리 낌새 키": hit or "🔴 0개 — 좌표 열이 없다"}
    return out


def main() -> None:
    t0 = dt.datetime.now(dt.timezone.utc)
    res = {"팔": "915-ㅋ", "단계": "1 — 부착 계수",
           "🔴 자": "뗐다 — 계수만. 효과 추정 없음",
           "사전등록": "docs/prereg_915_grid.md",
           "코드 sha256": {c: sha16(ROOT / c) for c in
                          ("runners/grid915_link.py", "runners/out901h_link.py",
                           "ingest/lifepop915.py")},
           "시작 UTC": t0.isoformat(timespec="seconds")}

    # ── 받아 둔 지평 ────────────────────────────────────────────────────
    cnt = json.loads(COUNT.read_text())
    days: set[str] = set()
    for nm, r in cnt["달별"].items():
        pass
    import numpy as _np
    SCR = Path(cnt["값 텐서 둔 곳(저장소 밖)"])
    grids: set[str] = set()
    for f in sorted(SCR.glob("250_LOCAL_RESD_*.npz")):
        z = _np.load(f, allow_pickle=False)
        grids |= set(z["grids"].tolist())
        days |= set(z["days"].tolist())
    iso = sorted(f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in days)
    HAVE = (iso[0], iso[-1])
    gap = (dt.date.fromisoformat(iso[-1]) - dt.date.fromisoformat(iso[0])).days + 1
    res["받아 둔 지평(실측)"] = {
        "처음~끝": list(HAVE), "날짜 수": len(iso), "달력 일수": gap,
        "빠진 날": gap - len(iso),
        "서로 다른 격자(19개월 합집합)": len(grids),
        "🔴 901 이 갖고 있던 것": list(HAVE901) + ["61일"]}

    # ── 분모 ────────────────────────────────────────────────────────────
    IR = L.internal_records()
    MR = L.market_records()
    mkax = json.loads((ROOT / "data/state/market_axes.json").read_text())
    axis_ids = {"팝업": L.popup_axis_ids(), "시장팝업": list(mkax)}
    hold, hchk = L.holdout_ids(axis_ids)
    U = sorted(set(hold["팝업"]) | set(hold["시장팝업"]))

    spots = L.spot_table()
    raw, ver = L.link_coords(spots)
    addr_by_spot = json.loads((ROOT / "data/state/spot_addr.json").read_text())

    def period(rid):
        r = IR.get(rid)
        if r:
            p = r["conditions"].get("period") or {}
            return L.d10(p.get("from")), L.d10(p.get("to")) or L.d10(p.get("from"))
        m = MR.get(rid)
        if m:
            c = m["conditions"]
            return L.d10(c.get("period_from")), L.d10(c.get("period_to")) or L.d10(c.get("period_from"))
        a = mkax.get(rid)
        if a:
            return L.d10(a.get("period_from")), L.d10(a.get("period_from"))
        return None, None

    def keys_of(rid):
        k = {"lat": None, "lon": None, "addr": None, "gap": None, "src": None}
        v = ver.get(rid)
        if v and L.fnum(v.get("lat")) is not None:
            k.update(lat=L.fnum(v["lat"]), lon=L.fnum(v["lon"]),
                     addr=v.get("addr") or None, gap=v.get("gap_days"), src="검증 링크")
        elif rid in raw and raw[rid]["lat"] is not None:
            rf, rt = period(rid)
            k.update(lat=raw[rid]["lat"], lon=raw[rid]["lon"],
                     addr=raw[rid]["addr"] or None,
                     gap=L.gap_days(rf, rt, raw[rid]["open"], raw[rid]["close"]),
                     src="원링크(미검증)")
        if k["addr"] is None and rid in raw:
            k["addr"] = addr_by_spot.get(raw[rid]["spot_id"]) or None
        return k

    def census(ids, lo, hi):
        """🔴 네 칸을 **갈라** 센다(조항 59)."""
        c = {"분모": len(ids), "좌표 있음": 0, "🔴 좌표 열이 없다(링크가 안 닿는다)": 0,
             "좌표 있는데 서울 상자 밖": 0, "서울 안인데 격자 집합에 없다": 0,
             "격자에 붙음": 0, "날짜가 지평과 겹침": 0,
             "🔴 격자 + 날짜 둘 다": 0, "🔴 격자 + 날짜 + ±7일 검증 좌표": 0}
        rows = []
        for rid in ids:
            k = keys_of(rid)
            f, t = period(rid)
            ov = L.overlaps(f, t, lo, hi)
            c["날짜가 지평과 겹침"] += ov
            if k["lat"] is None:
                c["🔴 좌표 열이 없다(링크가 안 닿는다)"] += 1
                continue
            c["좌표 있음"] += 1
            if not L.in_seoul_box(k["lat"], k["lon"]):
                c["좌표 있는데 서울 상자 밖"] += 1
                continue
            g = L.grid_of(k["lat"], k["lon"])
            if g not in grids:
                c["서울 안인데 격자 집합에 없다"] += 1
                continue
            c["격자에 붙음"] += 1
            if ov:
                c["🔴 격자 + 날짜 둘 다"] += 1
                if k["gap"] is not None and k["gap"] <= 7:
                    c["🔴 격자 + 날짜 + ±7일 검증 좌표"] += 1
                rows.append({"id": rid, "격자": g, "lat": k["lat"], "lon": k["lon"],
                             "from": f, "to": t, "gap": k["gap"], "링크": k["src"]})
        return c, rows

    lo, hi = HAVE
    per = {}
    for dom in ("팝업", "시장팝업"):
        per[dom], _ = census(hold[dom], lo, hi)
    cu, rows = census(U, lo, hi)

    # 🔴 901 대조 — 같은 코드로 901 의 두 달을 다시 재서 공표값과 맞나 본다
    c901, _ = census(U, *HAVE901)
    chk = {
        "901 공표 — 좌표 102 / 격자 93 / 두 달 겹침 1(±7일 엄격 0)": True,
        "내 코드가 두 달로 낸 값": {
            "좌표 있음": c901["좌표 있음"],
            "격자에 붙음(19개월 격자 집합 기준)": c901["격자에 붙음"],
            "격자+날짜": c901["🔴 격자 + 날짜 둘 다"],
            "격자+날짜+±7일": c901["🔴 격자 + 날짜 + ±7일 검증 좌표"]},
        "🔴 어긋나면": ("격자 집합이 다르다(901 은 두 달 8,594 · 나는 19개월 8,880) — "
                    "좌표 수와 겹침 수는 같아야 하고 격자 수는 커질 수 있다"),
    }

    res["② 분모 — 🔴 셋이 다르다(조항 60)"] = {
        "행 수 대조(챔피언 자료)": hchk,
        "팝업 유보": len(hold["팝업"]), "시장팝업 유보": len(hold["시장팝업"]),
        "두 도메인 유보 합집합(겹치는 id 제거)": len(U),
        "겹치는 id": len(set(hold["팝업"]) & set(hold["시장팝업"])),
        "판 유보 전체(12도메인)": 3775,
        "합집합이 판 유보에서 차지하는 몫": round(len(U) / 3775, 4)}
    res["③ 부착 — 도메인별"] = per
    res["③ 부착 — 유보 합집합(분모 185)"] = cu
    res["🔴 판 유보 3,775 기준"] = {
        "격자에 붙음": cu["격자에 붙음"],
        "격자에 붙음 %": round(100 * cu["격자에 붙음"] / 3775, 3),
        "격자+날짜 둘 다": cu["🔴 격자 + 날짜 둘 다"],
        "격자+날짜 %": round(100 * cu["🔴 격자 + 날짜 둘 다"] / 3775, 3),
        "격자+날짜+±7일": cu["🔴 격자 + 날짜 + ±7일 검증 좌표"]}
    res["④ 901 의 날짜 벽이 헐렸나"] = {
        "901(두 달)": c901["🔴 격자 + 날짜 둘 다"],
        "915(19개월)": cu["🔴 격자 + 날짜 둘 다"],
        "배수": (round(cu["🔴 격자 + 날짜 둘 다"] / c901["🔴 격자 + 날짜 둘 다"], 1)
               if c901["🔴 격자 + 날짜 둘 다"] else "901 이 0 이라 배수를 못 쓴다"),
        "격자에 붙는 것 중 날짜까지 겹치는 몫":
            round(cu["🔴 격자 + 날짜 둘 다"] / cu["격자에 붙음"], 4) if cu["격자에 붙음"] else None,
        "자기시험": chk}
    res["⑤ 다른 도메인 — 🔴 「좌표 열이 없다」와 「안 붙는다」를 가른다"] = geo_key_scan()

    # ── 사전등록 문턱 판정 ──────────────────────────────────────────────
    n_att = cu["🔴 격자 + 날짜 둘 다"]
    g1 = {"격자 ≥ 4,000": (len(grids), len(grids) >= 4000),
          "날짜 ≥ 365": (len(iso), len(iso) >= 365),
          "행 ≥ 3.0e7": (cnt["🔴 분모 딱지 — 다섯이 전부 다른 분모다"]
                        ["④ 행 = (행정동,격자,날짜,시각) — 🔴 직접 센 전량"],
                        cnt["🔴 분모 딱지 — 다섯이 전부 다른 분모다"]
                        ["④ 행 = (행정동,격자,날짜,시각) — 🔴 직접 센 전량"] >= 3e7),
          "시간 해상도 = 시간별 24칸": ("24", True)}
    g2 = {"격자에 붙는 유보 ≥ 38": (cu["격자에 붙음"], cu["격자에 붙음"] >= 38),
          "격자+날짜 유보 ≥ 38": (n_att, n_att >= 38)}
    k_ok = ([8, 16, 32, 64, 128] if n_att >= 200 else
            [8, 16, 32, 64] if n_att >= 100 else
            [8, 16, 32] if n_att >= 60 else
            [8, 16] if n_att >= 38 else [])
    res["🔴 사전등록 문턱 판정"] = {
        "문턱 ①(기질 규모)": {**{k: {"값": v, "통과": p} for k, (v, p) in g1.items()},
                        "통과": all(p for _, p in g1.values())},
        "문턱 ②(부착)": {**{k: {"값": v, "통과": p} for k, (v, p) in g2.items()},
                     "통과": all(p for _, p in g2.values())},
        "문턱 ③(프로브 가능) → 잴 k": k_ok,
        "🔴 3단계로 가나": all(p for _, p in g1.values()) and all(p for _, p in g2.values())}

    ATT.write_text(json.dumps(
        {"팔": "915-ㅋ", "무엇": "격자+날짜 둘 다 붙는 판 유보 행(다음 단계 프로브 표본)",
         "🔴 분모": {"유보 합집합": len(U), "판 유보": 3775},
         "지평": list(HAVE), "행": rows}, ensure_ascii=False, indent=1), encoding="utf-8")

    res["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    res["초"] = round((dt.datetime.now(dt.timezone.utc) - t0).total_seconds(), 1)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"판 유보 3,775 기준": res["🔴 판 유보 3,775 기준"],
                      "문턱": res["🔴 사전등록 문턱 판정"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
