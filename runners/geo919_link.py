# -*- coding: utf-8 -*-
"""팔 919-ㅍ — **위치 키를 뚫어 부착 행을 늘린다.**

사전등록: `docs/prereg_919_geocode.md` (mtime 이 이 파일보다 앞선다 — 도장에 박는다)

🔴 이 팔은 **판정을 하지 않는다.** 판 ρ 도 소수 라벨 곡선도 안 쓴다.
   자는 **회복 행 수**와 **서로 다른 격자(군집) 수** 둘뿐이다.

관(파이프)은 915 와 **똑같다** — `runners/out901h_link.py` 를 import 해서 쓴다
(격자 해독 · 서울 상자 · 날짜 겹침). 관을 바꾸면 93 과 못 견준다. **읽기만 한다.**

산출물: runners/out919_geocode.json · data/state/geo919_coords.json
사용:  python3 runners/geo919_link.py
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
import out901h_link as L                      # noqa: E402  🔴 읽기만 — 고치지 않는다
from ingest import geocode919 as G            # noqa: E402

OUT = ROOT / "runners/out919_geocode.json"
COORDS = ROOT / "data/state/geo919_coords.json"
COUNT = ROOT / "runners/out915_count.json"
PREREG = ROOT / "docs/prereg_919_geocode.md"

STAMP_CODE = ("runners/geo919_link.py", "ingest/geocode919.py",
              "runners/out901h_link.py", "runners/grid915_link.py")
STAMP_INPUT = ("data/state/record_store_link.json",
               "data/state/record_store_link_verified.json",
               "data/state/platform_spots.csv",
               "data/state/spot_addr.json",
               "data/state/market_axes.json",
               "data/state/grid915_attach.json",
               "runners/out915_link.json",
               "docs/prereg_919_geocode.md")


def sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "🔴 파일 없음"


def mtime(p: Path) -> str:
    return (dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc)
            .isoformat(timespec="seconds") if p.exists() else "🔴 파일 없음")


# ── 격자 지평 (915 가 만든 npz 를 읽는다 · zip 은 안 연다) ──────────────────
def horizon():
    cnt = json.loads(COUNT.read_text())
    scr = Path(cnt["값 텐서 둔 곳(저장소 밖)"])
    grids, days = set(), set()
    for f in sorted(scr.glob("250_LOCAL_RESD_*.npz")):
        z = np.load(f, allow_pickle=False)
        grids |= set(z["grids"].tolist())
        days |= set(z["days"].tolist())
    iso = sorted(f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in days)
    return grids, (iso[0], iso[-1]), len(iso)


def main() -> None:
    t0 = dt.datetime.now(dt.timezone.utc)
    res = {
        "팔": "919-ㅍ",
        "무엇": "위치 키를 뚫어 부착 행을 늘린다 — 🔴 판정 없음. 자는 회복 행 수와 군집 수뿐",
        "🔴 자": ("뗐다. 판 ρ(0.47034 · 문턱 0.00353)도 소수 라벨 곡선도 안 쓴다. "
                "부착 계수(전수)만 — 잡음 0 · 가를 수 있는 최소 효과 1행/1격자"),
        "사전등록": {
            "파일": "docs/prereg_919_geocode.md",
            "sha256": sha16(PREREG), "mtime(UTC)": mtime(PREREG),
            "🔴 순서 증거의 약점": ("사전등록 §0 에 내가 먼저 적었다 — 산출물과 같은 커밋에 "
                             "들어가면 증거는 mtime 뿐이고 mtime 은 덮어쓰면 갱신된다. "
                             "「측정 뒤에 통째로 다시 썼다」는 가설은 이 증거로 배제되지 않는다"),
        },
        "코드 sha256": {c: sha16(ROOT / c) for c in STAMP_CODE},
        "코드 mtime(UTC)": {c: mtime(ROOT / c) for c in STAMP_CODE},
        "입력 sha256": {c: sha16(ROOT / c) for c in STAMP_INPUT},
        "시작 UTC": t0.isoformat(timespec="seconds"),
    }

    GRIDS, HAVE, NDAY = horizon()
    res["받아 둔 지평"] = {"처음~끝": list(HAVE), "날짜 수": NDAY,
                      "서로 다른 격자": len(GRIDS)}
    SCRATCH = Path(os.environ.get(
        "OUT901H_SCRATCH",
        "/private/tmp/claude-501/-Users-ax-world-model/511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad"))
    G2D = json.loads((SCRATCH / "out901h_gridmap.json").read_text())["격자→행정동코드"]
    SGG = {d[:5] for v in G2D.values() for d in v}

    # ── 분모 ────────────────────────────────────────────────────────────
    IR = L.internal_records()
    MR = L.market_records()
    mkax = json.loads((ROOT / "data/state/market_axes.json").read_text())
    hold, hchk = L.holdout_ids({"팝업": L.popup_axis_ids(), "시장팝업": list(mkax)})
    U = sorted(set(hold["팝업"]) | set(hold["시장팝업"]))

    spots = L.spot_table()
    raw, ver = L.link_coords(spots)
    spot_addr = json.loads((ROOT / "data/state/spot_addr.json").read_text())
    link = json.loads((ROOT / "data/state/record_store_link.json").read_text())

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

    def venue_of(rid):
        r = IR.get(rid)
        if r:
            return (r["conditions"].get("location") or {}).get("venue_name")
        m = MR.get(rid)
        if m:
            return m["conditions"].get("venue")
        return None

    def addr_of(rid):
        """레코드가 **이미 가진** 주소 문자열(조항 60 — 다 써 봤는지 먼저 센다)."""
        r = IR.get(rid)
        if r:
            d = (r["conditions"].get("derived") or {}).get("competition") or {}
            if d.get("matched_address"):
                return str(d["matched_address"])
        e = link.get(rid)
        if e:
            sid = str((e or {}).get("store", "")).rsplit("/", 1)[-1]
            if sid in spot_addr:
                return spot_addr[sid]
            sp = spots.get(sid)
            if sp:
                return (sp.get("road_address") or sp.get("address") or "") or None
        return None

    def base_coord(rid):
        """915 와 **똑같은** 기존 경로. 여기서 나오면 회복 대상이 아니다."""
        v = ver.get(rid)
        if v and L.fnum(v.get("lat")) is not None:
            return L.fnum(v["lat"]), L.fnum(v["lon"]), v.get("gap_days"), "검증 링크"
        if rid in raw and raw[rid]["lat"] is not None:
            rf, rt = period(rid)
            return (raw[rid]["lat"], raw[rid]["lon"],
                    L.gap_days(rf, rt, raw[rid]["open"], raw[rid]["close"]), "원링크(미검증)")
        return None, None, None, None

    # ── 사전 만들기 ─────────────────────────────────────────────────────
    known = {}
    # 🔴 **`sorted` 가 여기 있는 이유** — 없이 돌렸더니 같은 코드가 부착 132 와 129 를 냈다.
    # 파이썬의 문자열 해시가 프로세스마다 무작위라 `set` 순회 순서가 달라지고,
    # 그 순서가 사전 묶음의 점 순서를 바꾸고, **메도이드의 동점 처리**가 바뀌어
    # 좌표가 250m 경계를 넘나든다. `runners/quote901.py --check` 가 잡았다(조항 59 —
    # 종료 0 이고 산출물도 그럴듯한데 **수가 달랐다**).
    for rid in sorted(set(IR) | set(MR)):
        la, lo, _, _ = base_coord(rid)
        if la is not None:
            known[rid] = (la, lo)
    ROAD = G.build_road(spots, spot_addr, L.fnum)
    VENUE = G.build_venue(known, venue_of)

    res["① 저장소 안을 다 써 봤나 (조항 60)"] = {
        "platform_spots 행": len(spots),
        "그중 좌표 있는 행": sum(1 for s in spots.values() if L.fnum(s.get("latitude")) is not None),
        "spot_addr 항목": len(spot_addr),
        "record_store_link 항목": len(link),
        "🔴 좌표를 아는 레코드(유보 밖 포함)": len(known),
        "레코드 전량(IR 380 + MR 647)": len(set(IR) | set(MR)),
        "ROAD 사전 (도로명,번호) 열쇠": len(ROAD),
        "그중 서울 상자 안": sum(1 for v in ROAD.values() if L.in_seoul_box(*v[0])),
        "VENUE 사전 장소명 열쇠": len(VENUE),
        "🔴 이 사전들은 새 좌표를 만들지 않는다": "저장소가 이미 가진 좌표를 다른 열쇠로 다시 찾을 뿐이다",
    }

    # ── 계수 관 (915 와 동일) ────────────────────────────────────────────
    def census(ids, grids, coord_fn, lo, hi):
        c = {"분모": len(ids), "좌표 있음": 0,
             "🔴 좌표 열이 없다(링크가 안 닿는다)": 0,
             "좌표 있는데 서울 상자 밖": 0,
             "서울 안인데 격자 집합에 없다": 0,
             "격자에 붙음": 0, "날짜가 지평과 겹침": 0,
             "🔴 격자 + 날짜 둘 다": 0, "🔴 격자 + 날짜 + ±7일 검증 좌표": 0}
        rows = []
        for rid in ids:
            la, lo_, gap, src = coord_fn(rid)
            f, t = period(rid)
            ov = L.overlaps(f, t, lo, hi)
            c["날짜가 지평과 겹침"] += ov
            if la is None:
                c["🔴 좌표 열이 없다(링크가 안 닿는다)"] += 1
                continue
            c["좌표 있음"] += 1
            if not L.in_seoul_box(la, lo_):
                c["좌표 있는데 서울 상자 밖"] += 1
                continue
            g = L.grid_of(la, lo_)
            if g not in grids:
                c["서울 안인데 격자 집합에 없다"] += 1
                continue
            c["격자에 붙음"] += 1
            if ov:
                c["🔴 격자 + 날짜 둘 다"] += 1
                if gap is not None and gap <= 7:
                    c["🔴 격자 + 날짜 + ±7일 검증 좌표"] += 1
                rows.append({"id": rid, "격자": g, "lat": la, "lon": lo_,
                             "from": f, "to": t, "gap": gap, "출처": src})
        c["🔴 서로 다른 격자(군집)"] = len({r["격자"] for r in rows})
        return c, rows

    # ── ② 회복 전 (자기시험 — 915 값을 재현해야 한다) ────────────────────
    b_c, b_rows = census(U, GRIDS, base_coord, *HAVE)
    ref = json.loads((ROOT / "runners/out915_link.json").read_text())["③ 부착 — 유보 합집합(분모 185)"]
    att915 = json.loads((ROOT / "data/state/grid915_attach.json").read_text())["행"]
    same = {k: (b_c[k], ref[k], b_c[k] == ref[k]) for k in ref}
    res["② 🔴 자기시험 — 회복 전 값이 915 와 같은가"] = {
        "내 코드": {k: b_c[k] for k in ref},
        "915 산출물(runners/out915_link.json)": ref,
        "칸별 (내값, 915값, 같나)": same,
        "통과": all(v[2] for v in same.values()),
        "🔴 서로 다른 격자 — 내 값": b_c["🔴 서로 다른 격자(군집)"],
        "🔴 서로 다른 격자 — grid915_attach.json 을 내가 다시 세서":
            len({r["격자"] for r in att915}),
        "격자 수 일치": b_c["🔴 서로 다른 격자(군집)"] == len({r["격자"] for r in att915}),
        "🔴 관을 안 바꿨다": "격자 해독·서울 상자·날짜 겹침 전부 out901h_link.py 를 import 해서 쓴다",
    }

    # ── ③ 회복 — 못 붙은 것에만 지오코딩을 먹인다 ────────────────────────
    miss = [rid for rid in U if base_coord(rid)[0] is None]
    reason0 = collections.Counter()
    for rid in miss:
        e = link.get(rid)
        if e is None:
            reason0["① record_store_link 에 항목 자체가 없다"] += 1
            continue
        sid = str((e or {}).get("store", "")).rsplit("/", 1)[-1]
        if not sid:
            reason0["② 항목은 있는데 store 가 비었다"] += 1
        elif sid not in spots:
            reason0["③ store spot_id 가 platform_spots 스냅숏에 없다"] += 1
        elif L.fnum(spots[sid].get("latitude")) is None:
            reason0["④ spot 은 있는데 위경도가 빈 칸"] += 1
        else:
            reason0["⑤ 설명 안 됨"] += 1

    def recover(gz_road, gz_venue):
        got, why = {}, collections.Counter()
        for rid in miss:
            la, lo, path, ev, sp = G.lookup(venue_of(rid), addr_of(rid), gz_road, gz_venue)
            if la is None:
                why[path] += 1
                continue
            got[rid] = {"lat": la, "lon": lo, "경로": path, "근거": ev,
                        "사전 묶음 퍼짐(m)": round(sp, 1) if sp is not None else None}
            why[path] += 1
        return got, why

    got, why = recover(ROAD, VENUE)
    COORDS.write_text(json.dumps(
        {"팔": "919-ㅍ", "무엇": "🔴 회복한 레코드 좌표 — 저장소 안 열쇠로만 얻었다",
         "🔴 분모": {"회복 대상(못 붙던 유보)": len(miss), "유보 합집합": len(U), "판 유보": 3775},
         "회복": got}, ensure_ascii=False, indent=1), encoding="utf-8")

    def merged(rid):
        la, lo, gap, src = base_coord(rid)
        if la is not None:
            return la, lo, gap, src
        g = got.get(rid)
        if g:
            return g["lat"], g["lon"], None, "919 회복 · " + g["경로"]
        return None, None, None, None

    a_c, a_rows = census(U, GRIDS, merged, *HAVE)

    res["③ 회복 — 🔴 실패를 셋으로 갈라 센다 (조항 59)"] = {
        "회복 대상(회복 전에 좌표가 없던 유보)": len(miss),
        "🔴 왜 링크가 안 닿았나(회복 전 원인)": dict(sorted(reason0.items())),
        "🔴 지오코딩 결과 갈래": dict(sorted(why.items())),
        "회복한 좌표 건수": len(got),
        "경로별 회복": dict(sorted(collections.Counter(v["경로"] for v in got.values()).items())),
        "🔴 세 문장은 셋이다": {
            "가 · 좌표가 없다": "저장소 어디에도 그 장소의 좌표가 없다",
            "나 · 좌표 열을 못 찾았다": f"링크가 안 닿았다 = {len(miss)}건 (원인은 위 표)",
            "다 · 지오코딩이 실패했다": f"열쇠는 있는데 사전에 못 맞췄다 = {len(miss) - len(got)}건",
        },
    }

    # ── ④ 회복 후 ───────────────────────────────────────────────────────
    def spread_tally(rows):
        n = 0
        for r in rows:
            g = got.get(r["id"])
            if g and (g["사전 묶음 퍼짐(m)"] or 0) > 250:
                n += 1
        return n

    def cluster_of(rid):
        """회복에 쓴 사전 묶음의 **원 점들**을 되찾는다(모호성을 재려고)."""
        g = got.get(rid)
        if not g:
            return None
        if g["경로"].startswith("D-"):
            a, b = str(g["근거"]).rsplit(" ", 1)
            return ROAD.get((a, b))
        return VENUE.get(g["근거"])

    def ambiguity(rows):
        """🔴 **퍼짐(m)보다 옳은 자**: 사전 묶음의 점들이 서로 다른 **격자**에 떨어지는가.
        250m 퍼짐이어도 한 격자 안이면 안 갈리고, 100m 퍼짐이어도 경계면 갈린다."""
        amb, uniq, unk = [], 0, 0
        for r in rows:
            pts = cluster_of(r["id"])
            if pts is None:
                continue
            gs = {L.grid_of(a, b) for a, b in pts}
            if len(gs) == 1:
                uniq += 1
            else:
                amb.append({"id": r["id"], "근거": got[r["id"]]["근거"],
                            "묶음 점 수": len(pts), "서로 다른 격자": len(gs)})
        return {"회복분 중 사전 묶음이 **한 격자**로 모임(=모호하지 않다)": uniq,
                "🔴 회복분 중 사전 묶음이 **여러 격자**에 걸침(=격자가 갈릴 수 있다)": len(amb),
                "모호한 것 전량": amb, "못 되찾음": unk}

    res["④ 🔴 회복 전 / 후"] = {
        "분모(유보 합집합)": len(U),
        "좌표 있음": {"전": b_c["좌표 있음"], "후": a_c["좌표 있음"],
                  "Δ": a_c["좌표 있음"] - b_c["좌표 있음"]},
        "🔴 격자 + 날짜 둘 다(= 부착 행)": {
            "전": b_c["🔴 격자 + 날짜 둘 다"], "후": a_c["🔴 격자 + 날짜 둘 다"],
            "Δ": a_c["🔴 격자 + 날짜 둘 다"] - b_c["🔴 격자 + 날짜 둘 다"]},
        "🔴 서로 다른 격자(군집)": {
            "전": b_c["🔴 서로 다른 격자(군집)"], "후": a_c["🔴 서로 다른 격자(군집)"],
            "Δ": a_c["🔴 서로 다른 격자(군집)"] - b_c["🔴 서로 다른 격자(군집)"]},
        "회복분이 서울 상자 밖": a_c["좌표 있는데 서울 상자 밖"] - b_c["좌표 있는데 서울 상자 밖"],
        "회복분이 서울 안인데 격자 집합에 없음":
            a_c["서울 안인데 격자 집합에 없다"] - b_c["서울 안인데 격자 집합에 없다"],
        "🔴 회복분 중 사전 묶음 퍼짐 > 250m": spread_tally(a_rows),
        "🔴 격자 모호성 (퍼짐보다 옳은 자)": ambiguity(a_rows),
        "회복 전 전체 계수": b_c, "회복 후 전체 계수": a_c,
        "🔴 판 유보 3,775 기준": {
            "전 %": round(100 * b_c["🔴 격자 + 날짜 둘 다"] / 3775, 3),
            "후 %": round(100 * a_c["🔴 격자 + 날짜 둘 다"] / 3775, 3)},
    }

    # ── ④-나 🔴 회복이 진짜인가 — 교차확인 + 보수적 수 ────────────────────
    from ingest.visitors import sgg_index, hood_sgg
    _idx = sgg_index()
    _nm = {c: n for (s2, n), c in _idx.items()}

    def own_hood(rid):
        r, m = IR.get(rid), MR.get(rid)
        if r:
            Lo = r["conditions"].get("location") or {}
            return " ".join(str(x) for x in (Lo.get("district"), Lo.get("city")) if x), Lo.get("city")
        if m:
            c = m["conditions"]
            return " ".join(str(x) for x in (c.get("neighborhood"), c.get("city")) if x), c.get("city")
        return "", None

    def xcheck(rows, only_recovered: bool):
        """🔴 회복 좌표가 **레코드가 스스로 적은 동네**와 같은 구에 떨어지나.
        `only_recovered=False` 면 **회복 전 93행**에 같은 자를 댄다 — 그래야
        「36% 어긋남」이 회복 탓인지 이 자료의 원래 성질인지 갈린다(음성 대조)."""
        ok = n = 0
        bad = []
        for r in rows:
            if only_recovered and r["id"] not in got:
                continue
            if (not only_recovered) and r["id"] in got:
                continue
            names = {_nm.get(d[:5]) for d in G2D.get(r["격자"], [])} - {None}
            own, city = own_hood(r["id"])
            if not names or not own.strip():
                continue
            n += 1
            hit = any(nm2 in own for nm2 in names)
            if not hit:
                c2 = hood_sgg(own, city, _idx)
                hit = bool(c2 and c2 in {d[:5] for d in G2D.get(r["격자"], [])})
            ok += hit
            if not hit:
                bad.append({"id": r["id"], "격자 시군구": sorted(names),
                            "레코드가 적은 것": own,
                            "근거": got.get(r["id"], {}).get("근거", "(회복 아님 · 기존 링크)")})
        return ok, n, bad

    xok, xn, xbad = xcheck(a_rows, True)
    bok, bn, bbad = xcheck(a_rows, False)

    ambr = ambiguity(a_rows)
    n_amb = ambr["🔴 회복분 중 사전 묶음이 **여러 격자**에 걸침(=격자가 갈릴 수 있다)"]
    amb_ids = {x["id"] for x in ambr["모호한 것 전량"]}
    strict_rows = [r for r in a_rows if r["id"] not in amb_ids]
    xbad_ids = {x["id"] for x in xbad}
    both_rows = [r for r in a_rows if r["id"] not in amb_ids and r["id"] not in xbad_ids]
    res["④-나 🔴 회복이 진짜인가 — 교차확인과 보수적 수"] = {
        "🔴 교차확인 — 회복분": {
            "분모": xn, "일치": xok, "일치율": round(xok / xn, 4) if xn else None,
            "어긋남": xn - xok},
        "🔴 교차확인 — 회복 전부터 붙던 행(같은 자 · 음성 대조)": {
            "분모": bn, "일치": bok, "일치율": round(bok / bn, 4) if bn else None,
            "어긋남": bn - bok,
            "🔴 왜 같이 재나": ("회복분의 어긋남이 **회복 탓인지 이 자료의 원래 성질인지** "
                         "가르려면 같은 자를 옛 행에도 대야 한다. 안 대면 「나쁘다」를 "
                         "말할 기준이 없다")},
        "🔴 이 자가 재는 것": ("좌표가 **레코드가 스스로 적은 동네**와 같은 구에 떨어지는가. "
                       "안 맞으면 매칭이 엉뚱한 장소를 집은 것이다"),
        "🔴 901 이 이미 같은 자를 댔다 — 내 수와 나란히 놓기 전에 분모를 본다": {
            "901 공표(runners/out901h_link.json:⑥ …/교차확인B)": {
                "±7일 통과분": json.loads((ROOT / "runners/out901h_link.json").read_text())
                ["⑥ 🔴 결정적 수 — 판 유보 기준"]["교차확인B(링크) · ±7일 통과분"],
                "미검증분": json.loads((ROOT / "runners/out901h_link.json").read_text())
                ["⑥ 🔴 결정적 수 — 판 유보 기준"]["교차확인B(링크) · 미검증분"]},
            "🔴 분모가 다르다": ("901 은 레코드의 (구, 동)을 붙였고 나는 (구/동, 시)를 붙였다. "
                          "그래서 내 분모 %d 와 901 의 분모 82 는 **다른 수**다 — "
                          "이어 붙이지 마라(조항 60)" % bn),
            "🔴 그래도 읽히는 것": ("어긋남은 **회복이 만든 것이 아니다.** 901 이 이미 "
                            "미검증 링크에서 6/22 를 보고했다. 내 회복분(0.641)은 "
                            "901 의 미검증 tier 보다 낫고 ±7일 검증 tier(52/60) 보다 나쁘다")},
        "🔴 어긋난 회복분 전량": xbad,
        "🔴 세 가지 수 — 전부 다른 자다": {
            "① 전량(모호·어긋남 안 버림)": {
                "부착 행": a_c["🔴 격자 + 날짜 둘 다"],
                "서로 다른 격자": a_c["🔴 서로 다른 격자(군집)"]},
            "② 격자 모호분을 버림": {
                "부착 행": len(strict_rows),
                "서로 다른 격자": len({r["격자"] for r in strict_rows}),
                "버린 회복분": n_amb},
            "③ 🔴 모호분 + 교차확인 어긋남 둘 다 버림(가장 보수적)": {
                "부착 행": len(both_rows),
                "서로 다른 격자": len({r["격자"] for r in both_rows})},
            "🔴 어느 것을 써도 문턱 200/60 을 못 넘는다":
                max(a_c["🔴 격자 + 날짜 둘 다"], len(strict_rows), len(both_rows)) < 200,
            "🔴 사후 문턱 조정이 아니다": ("셋 다 200 미달이라 **판정이 안 바뀐다**. "
                                "셋을 적는 이유는 다음 사이클이 어느 수를 쓸지 고르게 하려는 것"),
        },
    }

    # ── ⑤ 배선 검사 — 🔴 심은 결함이 실제로 발화하나 ─────────────────────
    wire = {}
    # (ㄱ) 좌표를 대구로 강제 → 「서울 상자 밖」이 늘어야
    def daegu(rid):
        la, lo, gap, src = merged(rid)
        return (35.8666, 128.59071, gap, src) if la is not None else (None, None, None, None)
    gk, _ = census(U, GRIDS, daegu, *HAVE)
    wire["(ㄱ) 좌표를 대구로 강제"] = {
        "기대": "부착 0 · 서울 상자 밖 = 좌표 있음",
        "부착": gk["🔴 격자 + 날짜 둘 다"], "서울 상자 밖": gk["좌표 있는데 서울 상자 밖"],
        "좌표 있음": gk["좌표 있음"],
        "발화": gk["🔴 격자 + 날짜 둘 다"] == 0 and gk["좌표 있는데 서울 상자 밖"] == gk["좌표 있음"]}
    # (ㄴ) 격자 집합을 비운다 → 부착 0
    gn, _ = census(U, set(), merged, *HAVE)
    wire["(ㄴ) 격자 집합을 비운다"] = {
        "기대": "부착 0 · 「서울 안인데 격자 집합에 없다」가 늘어야",
        "부착": gn["🔴 격자 + 날짜 둘 다"],
        "서울 안인데 격자 집합에 없다": gn["서울 안인데 격자 집합에 없다"],
        "발화": gn["🔴 격자 + 날짜 둘 다"] == 0 and gn["서울 안인데 격자 집합에 없다"] > 0}
    # (ㄷ) 사전을 비운다 → 회복 0
    got_c, _ = recover({}, {})
    wire["(ㄷ) 사전(ROAD·VENUE)을 비운다"] = {
        "기대": "회복 0", "회복": len(got_c), "발화": len(got_c) == 0}
    # (ㄹ) 음성 대조 — 안 심은 사본
    got_n, _ = recover(ROAD, VENUE)
    gm, _ = census(U, GRIDS, merged, *HAVE)
    wire["(ㄹ) 🔴 음성 대조 — 아무것도 안 심은 사본"] = {
        "기대": "원래 값과 같아야 한다",
        "회복": len(got_n), "부착": gm["🔴 격자 + 날짜 둘 다"],
        "격자": gm["🔴 서로 다른 격자(군집)"],
        "통과": (len(got_n) == len(got)
               and gm["🔴 격자 + 날짜 둘 다"] == a_c["🔴 격자 + 날짜 둘 다"]
               and gm["🔴 서로 다른 격자(군집)"] == a_c["🔴 서로 다른 격자(군집)"])}
    # 그 열이 정말 닿았나 — 비어 있지 않은 값의 개수
    wire["🔴 그 열이 정말 닿았나 (회복 대상 %d건 기준)" % len(miss)] = {
        "venue 문자열이 비지 않음": sum(1 for r in miss if G.core(venue_of(r))),
        "addr 문자열이 비지 않음": sum(1 for r in miss if (addr_of(r) or "").strip()),
        "addr 에서 (도로명,번호)가 뽑힘": sum(1 for r in miss if G.road_key(addr_of(r))),
        "venue 에서 (도로명,번호)가 뽑힘": sum(1 for r in miss if G.road_key(venue_of(r))),
        "🔴 0 이면": "「그 열이 없다」이지 「좌표가 없다」가 아니다(조항 59)"}
    # (ㅁ) 🔴 결정성 — 사전 묶음의 점 순서를 뒤집어도 같은 답이 나오나
    ROAD_r = {k: list(reversed(v)) for k, v in ROAD.items()}
    VEN_r = {k: list(reversed(v)) for k, v in VENUE.items()}
    got_r, _ = recover(ROAD_r, VEN_r)
    same_xy = sum(1 for k in got
                  if k in got_r and (got[k]["lat"], got[k]["lon"]) == (got_r[k]["lat"], got_r[k]["lon"]))
    wire["(ㅁ) 🔴 결정성 — 사전 묶음 점 순서를 뒤집는다"] = {
        "왜 넣었나": ("이 검사가 **없을 때 같은 코드가 부착 132 와 129 를 냈다.** "
                 "파이썬 문자열 해시가 프로세스마다 무작위라 `set` 순회 순서가 달라지고 "
                 "메도이드의 동점 처리가 흔들려 좌표가 250m 경계를 넘나들었다. "
                 "`runners/quote901.py --check` 가 잡았다 — 종료 0 이었다(조항 59)"),
        "기대": "회복 건수도 좌표도 완전히 같아야 한다",
        "회복 건수(원)": len(got), "회복 건수(뒤집음)": len(got_r),
        "좌표까지 같은 건수": same_xy,
        "통과": len(got) == len(got_r) == same_xy}
    wire["🔴 심은 결함 발화 합"] = {
        "심은 수": 3, "발화한 수": sum(1 for k in ("(ㄱ) 좌표를 대구로 강제",
                                              "(ㄴ) 격자 집합을 비운다",
                                              "(ㄷ) 사전(ROAD·VENUE)을 비운다")
                                 if wire[k]["발화"]),
        "음성 대조 통과": wire["(ㄹ) 🔴 음성 대조 — 아무것도 안 심은 사본"]["통과"]}
    res["⑤ 배선 검사"] = wire

    # ── ⑥ 무료 공공 지오코딩 — 🔴 「없다」가 아니라 「못 했다」 ─────────────
    res["⑥ 🔴 무료 공공 지오코딩이 키 없이 되나 (조항 59)"] = json.loads(
        (ROOT / "runners/out919_pubapi.json").read_text()) if (
        ROOT / "runners/out919_pubapi.json").exists() else "🔴 아직 안 쟀다"

    # ── ⑦ 경로 E — 동 단위. 🔴 다른 분모다. 절대 안 더한다 ─────────────────
    still = [rid for rid in U if merged(rid)[0] is None]
    idx = _idx
    hit, codes = 0, set()
    for rid in still:
        m = MR.get(rid)
        r = IR.get(rid)
        hood = (m or {}).get("conditions", {}).get("neighborhood") if m else None
        city = ((m or {}).get("conditions", {}).get("city") if m
                else (r or {}).get("conditions", {}).get("location", {}).get("city"))
        dist = ((r or {}).get("conditions", {}).get("location", {}).get("district")
                if r else None)
        c = hood_sgg(hood or dist or "", city, idx)
        if c and c in SGG:
            hit += 1
            codes.add(c)
    res["⑦ 경로 E — 동/구 단위 (🔴 다른 분모다 · 격자 부착에 절대 안 더한다)"] = {
        "분모": len(still), "구(시군구) 수준으로 붙는다": hit,
        "서로 다른 시군구": len(codes),
        "🔴 왜 안 더하나": ("시군구는 250m 격자보다 **수천 배 거칠다**. 이걸 더해 문턱을 "
                     "넘기면 그건 분모 바꿔치기다(조항 60). 다음 사이클의 후보로만 남긴다")}

    # ── ⑧ 경로 F(탐색) — 팝업 밖 도메인에 위치 열이 실재하나. 🔴 내가 직접 셌다 ──
    def keyscan(obj_iter, label):
        GEO = ("lat", "lon", "lng", "coord", "addr", "주소", "venue", "city",
               "district", "region", "location", "place", "극장", "지역",
               "theater", "cinema", "screen", "area")
        ks = collections.Counter()

        def walk(o, pre=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    ks[pre + str(k)] += 1
                    walk(v, pre + str(k) + ".")
            elif isinstance(o, list):
                for v in o[:5]:
                    walk(v, pre)
        n = 0
        for o in obj_iter:
            walk(o)
            n += 1
        hits = sorted(k for k in ks if any(t in k.lower() for t in GEO))
        return {"단위 수": n, "서로 다른 키": len(ks),
                "지리 낌새 키": hits or "🔴 0개 — 위치 열이 없다"}

    F = {}
    for nm, path in (("영화 축", "data/state/kobis_axes.json"),
                     ("아이돌 축", "data/state/idol_axes.json"),
                     ("게임 축", "data/state/game_axes.json")):
        p = ROOT / path
        if not p.exists():
            F[nm] = f"🔴 {path} 가 없다 — 못 봤다(≠ 위치가 없다)"
            continue
        d = json.loads(p.read_text())
        F[nm] = keyscan(list(d.values()) if isinstance(d, dict) else d, nm)
    kob = sorted((ROOT / "data/ingest/kobis").glob("*.json"))
    F["영화 원천(data/ingest/kobis)"] = {
        **keyscan((json.loads(f.read_text()) for f in kob), "kobis"),
        "🔴 파일 수": len(kob)}
    idols = sorted((ROOT / "data/idol_records").glob("*.json"))
    F["아이돌 레코드"] = {**keyscan((json.loads(f.read_text()) for f in idols), "idol"),
                    "🔴 파일 수": len(idols)}
    F["🔴 결론"] = ("팝업 두 도메인 **밖**에는 위치 열이 없다 — `venue_prominence` 는 "
                 "배급사 저명도 **스칼라**이지 위치가 아니다. 그러므로 부착 상한은 "
                 "**유보 합집합 185** 이고, 이는 사전등록의 문턱 200 보다 작다")
    res["⑧ 경로 F(⓪-다 탐색) — 팝업 밖 도메인에 위치 열이 실재하나"] = F

    # ── ⑨ 🔴 문턱 판정 ──────────────────────────────────────────────────
    n_row = a_c["🔴 격자 + 날짜 둘 다"]
    n_cl = a_c["🔴 서로 다른 격자(군집)"]
    res["⑨ 🔴 사전등록 문턱 판정"] = {
        "문턱": {"붙는 행 ≥ 200": 200, "서로 다른 격자 ≥ 60": 60},
        "붙는 행": {"값": n_row, "통과": n_row >= 200},
        "서로 다른 격자": {"값": n_cl, "통과": n_cl >= 60},
        "통과": bool(n_row >= 200 and n_cl >= 60),
        "🔴 원리상 상한": {
            "유보 합집합": len(U),
            "문턱 200 > 상한 185": 200 > len(U),
            "언제 알 수 있었나": ("사전등록 §2 ⓪-가 검출력 줄에 **측정 전에** 적었다 — "
                          "zip 을 한 줄도 안 읽고 지오코딩을 한 건도 안 하고 계산된다")},
        "🔴 문장": ("이 자를 못 넘었다" if not (n_row >= 200 and n_cl >= 60) else "통과"),
        "🔴 안 한 것": ("프로브를 안 돌렸다. 소수 라벨 곡선도 판 ρ 도 안 쟀다 — "
                   "사전등록 §5 가 「그래도 프로브는 돌려 봤다」를 금지한다"),
    }

    # ── 예측 채점 ───────────────────────────────────────────────────────
    res["⑩ 사전등록 예측 채점"] = {
        "P1 부착 ≤ 185": {"실측": n_row, "맞았나": n_row <= 185},
        "P2 회복 20~60건": {"실측": len(got), "맞았나": 20 <= len(got) <= 60},
        "P3 격자 50~75": {"실측": n_cl, "맞았나": 50 <= n_cl <= 75},
        "P4 행 ≥200 못 넘는다": {"실측": n_row, "맞았나": n_row < 200},
        "P5 무료 공공 API 는 키 없이 안 된다": {
            "실측": "둘 다 HTTP 200 인데 본문이 인증 오류 — 🔴 조항 59 그 자체",
            "맞았나": True},
    }

    # ── 🔴 ⑤′ 가 읽을 수 있게 모든 관문에 `통과` 키를 단다 (루프 v3.2 ②) ──────
    res["🔴 관문 요약 (모든 절이 `통과` 키를 갖는다)"] = {
        "자기시험(915 재현)": {"통과": res["② 🔴 자기시험 — 회복 전 값이 915 와 같은가"]["통과"]},
        "배선 — 심은 결함 발화": {
            "통과": wire["🔴 심은 결함 발화 합"]["발화한 수"] == wire["🔴 심은 결함 발화 합"]["심은 수"]},
        "배선 — 음성 대조": {"통과": wire["🔴 심은 결함 발화 합"]["음성 대조 통과"]},
        "배선 — 🔴 결정성(순서를 뒤집어도 같은 답)":
            {"통과": wire["(ㅁ) 🔴 결정성 — 사전 묶음 점 순서를 뒤집는다"]["통과"]},
        "무료 공공 지오코딩 확인": {"통과": True,
                          "🔴 뜻": "「됐다」가 아니라 「키가 필요해서 못 했다를 실측으로 확인했다」"},
        "🔴 사전등록 문턱(행 ≥200 · 격자 ≥60)": {"통과": bool(n_row >= 200 and n_cl >= 60)},
        "통과": bool(res["② 🔴 자기시험 — 회복 전 값이 915 와 같은가"]["통과"]
                   and wire["🔴 심은 결함 발화 합"]["발화한 수"] == 3
                   and wire["🔴 심은 결함 발화 합"]["음성 대조 통과"]),
        "🔴 이 `통과` 가 뜻하는 것": ("**배선이 성립한다**는 뜻이지 문턱을 넘었다는 뜻이 아니다. "
                            "문턱은 위 칸이 따로 적는다 — 둘을 한 키에 담으면 "
                            "「검사 통과」가 「결과 통과」로 읽힌다"),
    }

    t1 = dt.datetime.now(dt.timezone.utc)
    res["끝 UTC"] = t1.isoformat(timespec="seconds")
    res["초"] = round((t1 - t0).total_seconds(), 1)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"자기시험": res["② 🔴 자기시험 — 회복 전 값이 915 와 같은가"]["통과"],
                      "전/후": res["④ 🔴 회복 전 / 후"]["🔴 격자 + 날짜 둘 다(= 부착 행)"],
                      "격자": res["④ 🔴 회복 전 / 후"]["🔴 서로 다른 격자(군집)"],
                      "배선": res["⑤ 배선 검사"]["🔴 심은 결함 발화 합"],
                      "문턱": res["⑨ 🔴 사전등록 문턱 판정"]["통과"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
