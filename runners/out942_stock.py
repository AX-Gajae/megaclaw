# -*- coding: utf-8 -*-
"""노트 942(수리) — **o 검출기를 스키마별로 가르고 저장소 재고를 다시 센다.**

티처 #81 C1: `runners/out941_sao.py:67` 이 결과값(o) 유무를
`outcome.daily` / `outcome.totals.visitors` / `outcome.totals.sales_krw`
**하나의 스키마로만** 판정한다. 그래서

  · `data/market_records` **647** 은 `outcome.totals` 키가 아예 없어 전부 자동 0점
  · `data/idol_records` **282** 는 `outcome` 키 자체가 없어 통째로 0점

🔴 **「내가 아는 스키마」로 시작하지 않는다**(조항 60 · 티처 #81 자가 적발).
이 러너는 **ㄱ 에서 키 분포를 전수 집계**하고 **그 표를 보고 나서** ㄴ 에서 검출기를 가른다.

  **ㄱ** 레코드성 원천 전부의 **키 분포 전수 집계** → `runners/out942_schema_census.json`
  **ㄴ** 스키마별 o 검출기 · 🔴 **옛 검출기와 새 검출기를 같은 순회에서 둘 다** 돌린다
  **ㄷ** a / s / o 의 **분모와 교집합을 도메인별로**
  **ㄹ** 🔴 941 이 아예 안 본 원천 — `data/state/*_records.json` 아홉 저장소

🔴 **분모를 안 섞는다**(조항 60). 두 분모다:
  **D1 = 파일 하나가 레코드 하나**인 여섯 디렉터리 (941 이 센 그 분모)
  **D2 = 저장소 하나에 레코드 여럿**인 `data/state/*_records.json` 아홉
**서로 더하지 않는다.** 더한 수를 쓰려면 그 자리에서 분모를 다시 적는다.

🔴 941 산출물(`runners/out941_*.json` · `data/ingest/sao941/`)은 **동결물 — 안 건드린다.**

쓰는 법::  python3 runners/out942_stock.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

#: D1 — 파일 하나 = 레코드 하나 (941 의 REC_DIRS 와 **같은 목록**이어야 대조가 성립한다)
REC_DIRS = ("data/records", "data/market_records", "data/idol_records",
            "data/records_draft", "data/records_incomplete",
            "data/records_thinbak")

#: D2 — 저장소 하나에 레코드 여럿. 🔴 941 의 `stock()` 은 이것을 **한 줄도 안 봤다**.
STORES = {
    "data/state/anime_records.json": "애니",
    "data/state/app_records.json": "앱(구 모바일)",
    "data/state/book_records.json": "도서",
    "data/state/funding_records.json": "펀딩",
    "data/state/game_records.json": "게임",
    "data/state/manga_records.json": "만화",
    "data/state/mobile_records.json": "모바일",
    "data/state/wanime_records.json": "세계애니",
    "data/state/webtoon_records.json": "웹툰",
}

OUT = ROOT / "runners/out942_stock.json"
CENSUS = ROOT / "runners/out942_schema_census.json"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _nonempty(v) -> bool:
    """🔴 「값이 있다」의 뜻을 한 곳에서 정한다. None·''·[]·{} 는 없다로 친다.

    0 과 False 는 **있다**로 친다(관객 0 명도 결과다).
    """
    if v is None:
        return False
    if isinstance(v, (str, list, dict, tuple)) and len(v) == 0:
        return False
    return True


# ── ㄱ 키 분포 전수 집계 ──────────────────────────────────────────────────
def census() -> dict:
    """🔴 어떤 스키마가 있는지 **먼저 센다.** 이 표를 보고 ㄴ 의 검출기를 짰다."""
    out: dict = {"D1(파일=레코드)": {}, "D2(저장소=레코드 여럿)": {}}
    for d in REC_DIRS:
        top: Counter = Counter()
        oc: Counter = Counter()
        oshape: Counter = Counter()
        n = 0
        for f in sorted((ROOT / d).glob("*.json")):
            try:
                r = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            n += 1
            if not isinstance(r, dict):
                oshape["최상위가 dict 가 아님"] += 1
                continue
            top.update(r.keys())
            o = r.get("outcome")
            if o is None and "결과" in r:
                o = r.get("결과")
            if isinstance(o, dict):
                oshape["outcome 이 dict"] += 1
                oc.update(o.keys())
            elif o is None:
                oshape["🔴 outcome/결과 키 없음"] += 1
            else:
                oshape[f"outcome 이 {type(o).__name__}"] += 1
        out["D1(파일=레코드)"][d] = {
            "파일": n,
            "최상위 키 분포": dict(top.most_common()),
            "outcome 모양": dict(oshape),
            "outcome 하위 키 분포": dict(oc.most_common()),
        }
    for p, dom in STORES.items():
        d = json.loads((ROOT / p).read_text())
        c: Counter = Counter()
        for v in d.values():
            if isinstance(v, dict):
                c.update(v.keys())
        out["D2(저장소=레코드 여럿)"][p] = {
            "도메인": dom, "레코드": len(d), "바이트": (ROOT / p).stat().st_size,
            "키 분포": dict(c.most_common()),
            "🔴 outcome/결과 키": [k for k in c if k in ("outcome", "결과")],
            "🔴 y_ 로 시작하는 열": [k for k in c if k.startswith("y_")],
        }
    return out


# ── ㄴ 검출기 ────────────────────────────────────────────────────────────
def o_old(r: dict) -> bool:
    """🔴 941 의 검출기를 **글자 그대로** 옮긴 것 (out941_sao.py:65-68).

    비교 기준선이므로 고치지 않는다.
    """
    o = r.get("outcome") or {}
    tot = o.get("totals") or {}
    return bool(o.get("daily")) or tot.get("visitors") is not None \
        or tot.get("sales_krw") is not None


#: ㄱ 의 census 표에서 **읽어서** 만든 스키마별 결과 열 목록.
#: 🔴 기본 인자로 넣지 않는다 — 940 이 기본값 동결로 「고쳤는데 불변」이었다.
O_KEYS = {
    "A_팝업(outcome.totals)": {
        "경로": [("outcome", "daily"), ("outcome", "totals", "visitors"),
               ("outcome", "totals", "sales_krw"),
               ("outcome", "totals", "sales_amount_krw"),
               ("outcome", "totals", "visitors_total")],
    },
    "B_시장(평평한 outcome)": {
        "경로": [("outcome", "visitors_total"), ("outcome", "sales_krw")],
    },
    "C_아이돌(outcome 없음)": {
        "경로": [("chodong",), ("chart_peak",), ("mv_24h",)],
    },
}


#: 🔴 **내가 같은 함정에 한 번 빠졌다(자가 적발).** 첫 판에서 D2 의 결과 열을
#: `y_` 로 시작하는 이름으로만 잡았더니 `book_records.json` **396 이 전부 0** 이 나왔다 —
#: 도서의 라벨은 `y_*` 가 아니라 **`sales_point`** 다(`lab/sideaudit.py:388` ·
#: `lab/rawaxes.py:10`). 티처 #81 C1 이 지적한 바로 그 병(스키마 하나만 보는 검출기)을
#: **그것을 고치는 러너 안에서** 재현한 것이다. 열 이름을 **census 표에서 읽어** 메운다.
O_EXTRA = {"도서": ("sales_point",)}


def dig(r: dict, path):
    cur = r
    for k in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def family(r: dict) -> str:
    """🔴 레코드 **자신이 가진 키**로 계열을 정한다. 디렉터리 이름으로 안 정한다."""
    o = r.get("outcome")
    if isinstance(o, dict):
        return "A_팝업(outcome.totals)" if "totals" in o else "B_시장(평평한 outcome)"
    return "C_아이돌(outcome 없음)"


def o_new(r: dict) -> tuple:
    fam = family(r)
    hit = [".".join(p) for p in O_KEYS[fam]["경로"] if _nonempty(dig(r, p))]
    return bool(hit), fam, hit


def a_of(r: dict, fam: str) -> bool:
    if fam == "C_아이돌(outcome 없음)":
        return _nonempty(r.get("debut_date"))
    return _nonempty(r.get("intervention"))


def s_of(r: dict, fam: str) -> bool:
    if fam == "C_아이돌(outcome 없음)":
        return any(_nonempty(r.get(k)) for k in
                   ("agency", "member_count", "gender", "is_group",
                    "survival_show", "pre_debut_note"))
    return _nonempty(r.get("conditions"))


def d1_stock() -> dict:
    """🔴 옛 검출기와 새 검출기를 **같은 순회·같은 파일 집합**에서 둘 다 돌린다."""
    n = 0
    per: dict = {}
    fam_c: Counter = Counter()
    fam_old: Counter = Counter()
    fam_new: Counter = Counter()
    old_n = new_n = 0
    a_all = s_all = full_old = full_new = 0
    keyhit: Counter = Counter()
    flip: list = []
    idol: Counter = Counter()
    mkt: Counter = Counter()
    schema3 = 0
    for d in REC_DIRS:
        p = per.setdefault(d, {"파일": 0, "a": 0, "s": 0, "o_옛": 0, "o_새": 0,
                               "a·s·o(옛)": 0, "a·s·o(새)": 0, "계열": Counter()})
        for f in sorted((ROOT / d).glob("*.json")):
            try:
                r = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            n += 1
            p["파일"] += 1
            if {"intervention", "conditions", "outcome"} <= set(r):
                schema3 += 1
            ov_old = o_old(r)
            ov_new, fam, hit = o_new(r)
            a = a_of(r, fam)
            s = s_of(r, fam)
            fam_c[fam] += 1
            fam_old[fam] += ov_old
            fam_new[fam] += ov_new
            p["계열"][fam] += 1
            p["a"] += a
            p["s"] += s
            p["o_옛"] += ov_old
            p["o_새"] += ov_new
            p["a·s·o(옛)"] += bool(a and s and ov_old)
            p["a·s·o(새)"] += bool(a and s and ov_new)
            old_n += ov_old
            new_n += ov_new
            a_all += a
            s_all += s
            full_old += bool(a and s and ov_old)
            full_new += bool(a and s and ov_new)
            keyhit.update(hit)
            if ov_old != ov_new:
                flip.append({"파일": str(f.relative_to(ROOT)), "계열": fam,
                             "옛": ov_old, "새": ov_new, "걸린 열": hit})
            if fam == "C_아이돌(outcome 없음)":
                for k in ("debut_date", "chodong", "chart_peak", "mv_24h",
                          "found_chodong"):
                    idol[k] += _nonempty(r.get(k))
                idol["결과 하나라도(chodong|chart_peak|mv_24h)"] += ov_new
                idol["chodong|chart_peak 만"] += bool(
                    _nonempty(r.get("chodong")) or _nonempty(r.get("chart_peak")))
            if fam == "B_시장(평평한 outcome)":
                o = r.get("outcome") or {}
                mkt["outcome.totals 키 있음"] += ("totals" in o)
                mkt["visitors_total"] += _nonempty(o.get("visitors_total"))
                mkt["sales_krw"] += _nonempty(o.get("sales_krw"))
                mkt["둘 중 하나"] += ov_new
                mkt["둘 다"] += bool(_nonempty(o.get("visitors_total"))
                                   and _nonempty(o.get("sales_krw")))
    for v in per.values():
        v["계열"] = dict(v["계열"])
    return {
        "🔴 분모 D1(파일)": n,
        "스키마가 (a,s,o) 셋을 가진 파일": schema3,
        "계열 분포": dict(fam_c),
        "🔴 합 == 분모": sum(fam_c.values()) == n,
        "a 값 있음": a_all,
        "s 값 있음": s_all,
        "🔴 o 값 있음 — 옛 검출기(941)": old_n,
        "🔴 o 값 있음 — 새 검출기(942)": new_n,
        "🔴 a·s·o 셋 다 — 옛": full_old,
        "🔴 a·s·o 셋 다 — 새": full_new,
        "계열별 o(옛/새)": {k: {"옛": fam_old[k], "새": fam_new[k]} for k in fam_c},
        "🔴 반증 조건 1 — A계열(팝업)은 옛==새 여야 한다":
            fam_old["A_팝업(outcome.totals)"] == fam_new["A_팝업(outcome.totals)"],
        "🔴 뒤집힌 파일 수": len(flip),
        "🔴 뒤집힘 == 새−옛": len(flip) == new_n - old_n,
        "뒤집힌 것 앞 3건": flip[:3],
        "걸린 결과 열 분포(새)": dict(keyhit.most_common()),
        "디렉터리별": per,
        "아이돌 열별": dict(idol),
        "시장 열별": dict(mkt),
    }


def d2_stock() -> dict:
    """🔴 941 이 **한 줄도 안 본** 원천. 판 12도메인이 실제로 쓰는 저장소다.

    (`lab/calaxes.py:40-47` · `lab/grpaxes.py:23-30` 이 이 파일들을 읽는다)
    """
    per: dict = {}
    tot = tot_a = tot_o = tot_ao = 0
    DATE = ("start_date", "release_date", "pub_date")
    for p, dom in STORES.items():
        d = json.loads((ROOT / p).read_text())
        ys: Counter = Counter()
        n = a_n = o_n = ao = 0
        datekey: Counter = Counter()
        for v in d.values():
            if not isinstance(v, dict):
                continue
            n += 1
            yk = [k for k in v if k.startswith("y_")] + \
                [k for k in O_EXTRA.get(dom, ()) if k in v]
            o = any(_nonempty(v.get(k)) for k in yk)
            for k in yk:
                ys[k] += _nonempty(v.get(k))
            dk = [k for k in DATE if _nonempty(v.get(k))]
            a = bool(dk)
            for k in dk:
                datekey[k] += 1
            a_n += a
            o_n += o
            ao += bool(a and o)
        per[dom] = {"파일": p, "레코드": n, "a(액션 날짜 있음)": a_n,
                    "o(y_* 값 있음)": o_n, "a∩o": ao,
                    "결과 열": dict(ys), "날짜 열": dict(datekey)}
        tot += n
        tot_a += a_n
        tot_o += o_n
        tot_ao += ao
    return {
        "🔴 분모 D2(저장소 레코드)": tot,
        "a(액션 날짜)": tot_a, "o(y_* 값)": tot_o, "a∩o": tot_ao,
        "저장소별": per,
        "🔴 이 o 는 D1 의 o 와 종류가 다르다": (
            "D1 의 o 는 `outcome.daily` 일별 **시계열**이거나 총합 스칼라다. "
            "D2 의 o 는 **스칼라 라벨 하나**(y_review·y_backers·y_positive…)다. "
            "🔴 **두 수를 더해서 「(s,a,o) 삼중쌍」이라 부르면 종류를 섞는 것이다**(조항 60)."),
        "🔴 s 는 세지 않았다": (
            "D2 의 나머지 열이 전부 s 후보이지만 **액션 시점 전에 알 수 있었는지**를 "
            "이 러너는 못 가른다(예: avg_rating 은 사후값이다). 그래서 s 는 **안 셌다** — "
            "「0」이 아니라 **안 잰 것**이다(조항 59)."),
    }


def main() -> dict:
    t0 = time.time()
    cen = census()
    CENSUS.write_text(json.dumps(cen, ensure_ascii=False, indent=1))
    d1 = d1_stock()
    d2 = d2_stock()
    tree = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"],
                           capture_output=True, text=True).stdout
    res = {
        "노트": 942, "레인": "수리",
        "무엇": "o 검출기를 스키마별로 갈라 저장소 재고를 다시 센다 (티처 #81 C1)",
        "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "초": round(time.time() - t0, 1),
        "🔴 조항 60 — 명령·범위·트리": {
            "명령": "python3 runners/out942_stock.py",
            "범위": {"D1": list(REC_DIRS), "D2": list(STORES)},
            "트리": tree,
            "작업 트리 깨끗함": dirty.strip() == "",
            "🔴 깨끗하지 않으면 여기 전량": dirty.splitlines(),
        },
        "🔴 안 부른 자": "판 ρ · 문턱 0.00353 — 이 사이클은 예측 성능을 안 잰다",
        "ㄱ 키 분포 전수(파일)": {
            "경로": str(CENSUS.relative_to(ROOT)),
            "요약": {k: {kk: {"레코드": vv.get("파일", vv.get("레코드")),
                            "outcome 모양": vv.get("outcome 모양"),
                            "y_ 열": vv.get("🔴 y_ 로 시작하는 열")}
                       for kk, vv in v.items()} for k, v in cen.items()},
        },
        "ㄴ·ㄷ D1 재고(옛/새 나란히)": d1,
        "ㄹ D2 재고 — 🔴 941 이 안 본 원천": d2,
        "🔴 분모를 잇지 마라": (
            f"D1 {d1['🔴 분모 D1(파일)']} 과 D2 {d2['🔴 분모 D2(저장소 레코드)']} 는 "
            "다른 분모다. 「157 → 555」는 **둘 다 D1 분모 위의 수**이고, "
            "D2 는 그 위에 더하는 것이 아니라 **따로 신고**한다."),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("ㄱ 키 분포 전수(파일)",)},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
