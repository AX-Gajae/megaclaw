# -*- coding: utf-8 -*-
"""KOPIS 공연예술통합전산망 --- **13번째 도메인(공연)** 수집기 (노트 953 [탐색]).

🔴 **키는 저장소에 없다.** `/Users/ax/wm_harvest/keys.json#kopis.키` 에서 읽는다.
키 문자열은 **소스·산출물·노트·커밋 메시지 어디에도 안 쓴다** --- 로그에 남는 URL 도
`service=` 를 지우고 찍는다.

**왜 이 원천인가**
  · `pblprfr/{mt20id}` 상세에 `pcseguidance`(티켓가격)·`prfcast`·`sty` --- **s 자리가 통째로**
  · `boxoffice`·`prfsts*` 가 **(a → o) 시계열** --- `docs/목표.md` ③ 은 오늘 값이 0 이다
  · `prfplc/{mt10id}` 에 `la`/`lo` --- 🔴 `data/ingest/seoul_lifepop` 격자 인구와 **위치로 붙는다**

**제약(가이드 v5.0 실측)**
  · `stdate`~`eddate` **최대 31일** · `rows` **최대 100** · `cpage` 페이징 · 응답 **XML** · **HTTP**
  · `afterdate=YYYYMMDD` 로 증분 수집 --- 상시 데몬에 맞는다
  · 🔴 키 유효기간 1년 · **3개월 미사용 시 승인 자동 취소** --- 등기부에 켜서 돌아야 키가 안 죽는다
  · 🔴 **일일 호출 상한은 못 찾았다**(「없다」가 아니라 **「안 쟀다」**) --- 간격을 둔다

🔴 **파서를 op 별로 가른다.** `prfstsCate`·`prfstsArea` 는 루트가 `dbs` 가 아니라
**`prfsts`** 이고 자식이 `prfst` 다. 루트 이름으로 판정하면 **행이 멀쩡히 있는데 붉다**
--- 「자가 붉다」와 「자료가 없다」는 둘이다(조항 59).

    python3 -m ingest.kopis953                      # 증분(데몬용) --- afterdate 최근 창
    python3 -m ingest.kopis953 --backfill 20250801 20260811
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "data/ingest/kopis"
KEYFILE = Path("/Users/ax/wm_harvest/keys.json")
BASE = "http://www.kopis.or.kr/openApi/restful"

#: 🔴 **예의**다. 일일 상한을 모르므로 보수적으로 둔다(위 독스트링).
SLEEP = 0.34
TIMEOUT = 30

#: op → (루트 태그, 자식 태그). 🔴 op 별로 가른다 --- 주 세션의 자가 여기서 틀렸다.
SHAPE = {
    "pblprfr": ("dbs", "db"),
    "prfplc": ("dbs", "db"),
    "boxoffice": ("boxofs", "boxof"),
    # 🔴 **953 자가 적발.** 파라미터(`ststype=day`)는 고쳐 놓고 **꼴은 안 고쳤다** ---
    #    루트가 `prfsts`/`prfst` 인데 `dbs`/`db` 로 세어 **행 0 · 오류 0** 을 냈다.
    #    「자료가 없다」로 보이지만 실은 **자가 0 을 낸 것**이다(조항 59 · 이 파일이 두 줄 위에서
    #    같은 말을 하고 있었는데 내가 그 줄에 안 걸렸다).
    "prfstsTotal": ("prfsts", "prfst"),
    "prfstsCate": ("prfsts", "prfst"),
    "prfstsArea": ("prfsts", "prfst"),
    "mnfct": ("dbs", "db"),
    "prfawad": ("dbs", "db"),
    "prffest": ("dbs", "db"),
}


def _key() -> str:
    return json.loads(KEYFILE.read_text(encoding="utf-8"))["kopis"]["키"]


def _safe(url: str) -> str:
    """🔴 로그·산출물에 남길 URL --- 키를 지운다."""
    return url.replace(_key(), "<키>")


def call(op: str, params: dict, path: str = "") -> tuple:
    """(루트 Element 또는 None, 오류문자열 또는 None). 🔴 **HTTP 200 을 성공으로 안 읽는다.**"""
    q = dict(params)
    q["service"] = _key()
    url = "%s/%s%s?%s" % (BASE, op, ("/" + path if path else ""),
                          urllib.parse.urlencode(q))
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            raw = r.read()
    except Exception as e:                                        # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, str(e)[:120])
    try:
        root = ET.fromstring(raw)
    except Exception as e:                                        # noqa: BLE001
        return None, "XML 파싱 실패: %s / 앞 120바이트 %r" % (type(e).__name__, raw[:120])
    # 🔴 KOPIS 는 오류도 **200 + `<dbs><db>` 꼴**로 낸다 --- 겉이 정상 응답과 똑같다
    if root.tag in ("returnReason", "OpenAPI_ServiceResponse", "error"):
        return None, "오류응답 <%s> %s" % (root.tag, "".join(root.itertext())[:160])
    # 🔴🔴 **여기가 함정이다.** `boxoffice?ststype=day&date=…` 는
    #     `<dbs><db><returncode>01</returncode><errmsg>INVALID REQUEST PARAMETER ERROR</errmsg></db></dbs>`
    #     를 낸다. 자식을 세기만 하면 **행 1 = 「산다」**로 읽힌다 --- 주 세션의 표가
    #     `boxoffice` 를 🟢 「db 1」로 적은 것이 **바로 이 오류 행 하나**였다.
    #     티처 #91 M1 의 `rc99` 와 같은 병: **오류를 자료로 셌다**(조항 59).
    rc = root.find(".//returncode")
    if rc is not None:
        msg = root.find(".//errmsg")
        return None, "🔴 오류 행(returncode=%s · errmsg=%s) --- **자료가 아니다**" % (
            (rc.text or "").strip(), (msg.text or "").strip() if msg is not None else "")
    return root, None


def call_retry(op: str, params: dict, path: str = "", tries: int = 4) -> tuple:
    """🔴 **HTTP 400 은 질의어의 속성이 아니라 「너무 빨리 불렀다」의 속성이었다**(953 실측).

    첫 주행에서 13 창 중 **11 이 400** 이었는데, 같은 질의를 잠시 뒤 손으로 다시 부르니
    **200 + 자료**였다. 「막혔다」와 「빨랐다」는 둘이다 --- 티처 #91 M1 의 `rc99` 와 같은 자리다.
    그래서 **물러섰다 다시 부른다**. 그래도 안 되면 **「못 받았다」로 적는다**(「없다」가 아니다).
    """
    last = None
    for i in range(tries):
        root, err = call(op, params, path)
        if err is None:
            return root, None, i
        last = err
        time.sleep(SLEEP * (2 ** i) + 1.0)
    return None, last, tries


def rows(root, op: str) -> list:
    """루트에서 행을 뽑는다. 🔴 **루트 이름으로 판정하지 않는다** --- 자식을 센다."""
    _, child = SHAPE.get(op, ("dbs", "db"))
    out = []
    for el in root.findall(".//" + child):
        d = {}
        for c in el:
            d[c.tag] = (c.text or "").strip()
        if d:
            out.append(d)
    return out


def _windows(start: str, end: str, span: int = 31) -> list:
    """🔴 **31일 최대**. 창을 겹치지 않게 자른다."""
    s = dt.datetime.strptime(start, "%Y%m%d").date()
    e = dt.datetime.strptime(end, "%Y%m%d").date()
    out = []
    while s <= e:
        t = min(s + dt.timedelta(days=span - 1), e)
        out.append((s.strftime("%Y%m%d"), t.strftime("%Y%m%d")))
        s = t + dt.timedelta(days=1)
    return out


def _write_gz(path: Path, records: list) -> int:
    """🔴 `.part` 에 쓰고 `os.replace` --- 941 의 병(`"wt"` 는 여는 순간 자른다)을 안 되풀이한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    with gzip.open(part, "wt", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(part, path)
    return len(records)


def _read_gz(path: Path) -> list:
    if not path.exists():
        return []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return [json.loads(x) for x in f if x.strip()]
    except Exception:                                             # noqa: BLE001
        # 🔴 「0 행」과 「못 읽었다」는 둘이다 --- 부르는 쪽이 판단하게 터뜨린다
        raise


def _merge_write(path: Path, records: list, key: str) -> dict:
    """🔴 **덮어쓰지 않고 합친다.** 표본을 매 회차 새로 뜨면 파일 행 수가 **줄 수 있고**,
    그러면 래칫 ④ 가 **참인 뒷걸음질과 표본 흔들림을 구별 못 한다**. 수집은 **쌓는 것**이다."""
    old = {}
    err = None
    try:
        for r in _read_gz(path):
            k = r.get(key)
            if k:
                old[k] = r
    except Exception as e:                                        # noqa: BLE001
        err = "%s: %s --- 🔴 「0 행」이 아니다" % (type(e).__name__, str(e)[:80])
    new = {r[key]: r for r in records if r.get(key)}
    add = [k for k in new if k not in old]
    merged = dict(old)
    merged.update(new)
    _write_gz(path, list(merged.values()))
    return {"기존": len(old), "이번": len(new), "새로 는 것": len(add), "합친 뒤": len(merged),
            "🔴 기존 파일 오류": err or "없음"}


def sweep_pblprfr(start: str, end: str, log: list) -> dict:
    """공연 목록 전수. 🔴 **분모: 내가 실제로 받은 행**이다."""
    seen, dup, pages, errs, retried = {}, 0, 0, [], 0
    for (s, e) in _windows(start, end):
        cp = 1
        while True:
            root, err, tr = call_retry("pblprfr",
                                       {"stdate": s, "eddate": e, "cpage": cp, "rows": 100})
            pages += 1 + tr
            retried += tr
            if err:
                errs.append({"창": [s, e], "cpage": cp, "🔴 오류": err,
                             "🔴 다시 부른 횟수": tr})
                break
            rs = rows(root, "pblprfr")
            for r in rs:
                k = r.get("mt20id")
                if not k:
                    continue
                if k in seen:
                    dup += 1
                else:
                    seen[k] = r
            log.append({"창": [s, e], "cpage": cp, "행": len(rs)})
            time.sleep(SLEEP)
            if len(rs) < 100:
                break
            cp += 1
            if cp > 400:                     # 🔴 안전판. 걸리면 산출물에 적는다
                errs.append({"창": [s, e], "🔴": "cpage 400 안전판에 걸렸다"})
                break
    return {"공연": seen, "중복행": dup, "페이지 호출": pages,
            "🔴 물러섰다 다시 부른 횟수": retried, "🔴 오류": errs}


def _series_only(a) -> int:
    """🔴 절 4-나·5 만 다시 잰다 --- `prfstsTotal` 의 **꼴**을 953 이 스스로 틀렸기 때문이다."""
    op = ROOT / a.out
    res = json.loads(op.read_text(encoding="utf-8"))
    start, end = res["창"]["시작"], res["창"]["끝"]
    res["🔴 부분 재측정(자가 적발)"] = {
        "언제": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "무엇을 다시 쟀나": ["4-나 (a→o) 시계열", "5 통계(prfsts*)"],
        "🔴 왜": ("`SHAPE['prfstsTotal']` 이 `dbs/db` 였는데 실제 응답은 `prfsts/prfst` 라 "
               "**행 0 · 오류 0** 이 나왔다. 파라미터는 고쳐 놓고 **꼴은 안 고쳤다** --- "
               "「자료가 없다」가 아니라 **자가 0 을 낸 것**이다(조항 59)"),
        "🔴 안 다시 잰 절": ["1 공연 목록", "2 상세 표본", "3 공연장", "4-가 boxoffice"],
        "🔴 그래서": "위 넷의 수는 **앞 주행의 것**이고 시각이 다르다. 이어 붙여 읽지 마라(조항 60)",
        "통과": True,
    }
    series, serr = [], []
    for (s_, e_) in _windows(start, end):
        root, err, tr = call_retry("prfstsTotal", {"stdate": s_, "eddate": e_, "ststype": "day"})
        time.sleep(SLEEP)
        if err:
            serr.append({"창": [s_, e_], "🔴": err})
            continue
        series.extend(rows(root, "prfstsTotal"))
    days = sorted({r.get("prfdt") for r in series if r.get("prfdt")})
    res["4-나 (a→o) 시계열(prfstsTotal · ststype=day)"] = {
        "🔴 분모(창)": len(_windows(start, end)), "🔴 실패한 창": len(serr),
        "실패 예": serr[:3] or "없음",
        "받은 행": len(series), "서로다른 날": len(days),
        "첫 날": days[0] if days else "없음", "끝 날": days[-1] if days else "없음",
        "열이름": sorted(series[0].keys()) if series else "없음",
        "표본(첫 행)": series[0] if series else "없음",
        "쓴 행": _write_gz(OUTDIR / "prfsts_day.jsonl.gz", series),
        "🔴 이것이 왜 (a→o) 인가": ("`prfdt`(날)마다 `prfcnt`(공연 수)·`prfprocnt`(작품 수)·"
                            "`amount`(판매액)·`nmrs`(관객수)가 있다 --- **결과가 시간 위에 있다**"),
        "🔴 한계": "공연 **한 건별**이 아니라 **전국 합계**다. 개체별 (a→o) 는 아직 못 받았다",
        "통과": len(series) > 0,
    }
    st = {}
    for op_ in ("prfstsTotal", "prfstsCate", "prfstsArea"):
        q = {"stdate": start, "eddate": _windows(start, end)[0][1]}
        if op_ == "prfstsTotal":
            q["ststype"] = "day"
        root, err = call(op_, q)
        time.sleep(SLEEP)
        if err:
            st[op_] = {"🔴 오류": err, "통과": False}
            continue
        rs = rows(root, op_)
        st[op_] = {"루트 태그": root.tag, "🔴 기대 루트": SHAPE[op_][0], "행": len(rs),
                   "첫 행 키": sorted(rs[0].keys()) if rs else "없음",
                   "통과": len(rs) > 0}
    st["통과"] = all(v.get("통과") for k, v in st.items() if isinstance(v, dict))
    st["🔴 부기"] = res["5 통계(prfsts*)"].get("🔴 부기", "")
    res["5 통계(prfsts*)"] = st
    op.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", op, "(부분 재측정) 시계열", len(series), "행 ·", len(days), "일")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", nargs=2, metavar=("STDATE", "EDDATE"))
    ap.add_argument("--detail-sample", type=int, default=200)
    ap.add_argument("--box-days", type=int, default=60)
    # 🔴 953 자가 적발 --- 기본값이 `runners/out953_kopis.json` 이었고 **상시 데몬이 그 자리를 덮어썼다**.
    #    `runners/out*.json` 은 **사이클의 측정 증거물**이다. 소유자가 둘인 파일은 언젠가 덮어써진다.
    ap.add_argument("--out", default="data/state/kopis953_last.json")
    ap.add_argument("--only-series", action="store_true",
                    help="🔴 절 4-나·5 만 다시 잰다(자가 적발 뒤 재측정 · 앞 절은 기존 산출물에서 이어받는다)")
    a = ap.parse_args(argv)

    t0 = time.time()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    if a.only_series:
        # 🔴 **자가 적발 뒤 재측정.** 앞 절은 **다시 안 부른다**(예의 · 그리고 같은 수를 두 번 받을 이유가 없다).
        #    어느 절이 언제 재어졌는지를 산출물에 **글자로** 남긴다 --- 「한 트리」 규율과 같은 뜻이다.
        return _series_only(a)

    res = {"무엇": "KOPIS 수집 — 노트 953 [탐색] · 13번째 도메인 후보",
           "시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "🔴 키": "저장소 밖(%s#kopis.키) — 문자열은 어디에도 안 쓴다" % KEYFILE,
           "🔴 분모 규약": "여기 수는 전부 **내가 받은 XML 행**이다. 남이 신고한 수가 아니다(조항 60)"}

    if a.backfill:
        start, end = a.backfill
    else:                         # 증분 --- 최근 31일
        end = dt.date.today().strftime("%Y%m%d")
        start = (dt.date.today() - dt.timedelta(days=30)).strftime("%Y%m%d")
    res["창"] = {"시작": start, "끝": end, "31일 창 수": len(_windows(start, end)),
                "통과": True}      # 🔴 953 --- 모든 절이 `통과` 키를 갖는다(루프.md:256)

    # ── 1 공연 목록 ────────────────────────────────────────────────
    log = []
    sw = sweep_pblprfr(start, end, log)
    perf = sw.pop("공연")
    old = {}
    try:
        for r in _read_gz(OUTDIR / "pblprfr.jsonl.gz"):
            if r.get("mt20id"):
                old[r["mt20id"]] = r
    except Exception as e:                                        # noqa: BLE001
        res["⚠ 기존 파일"] = "🔴 못 읽었다: %s — 「0 행」이 아니다" % type(e).__name__
    merged = dict(old)
    merged.update(perf)
    res["1 공연 목록(pblprfr)"] = dict(sw, **{
        "🔴 서로다른 mt20id(이번 수확)": len(perf),
        "기존 파일에 있던 것": len(old),
        "합친 뒤": len(merged),
        "쓴 행": _write_gz(OUTDIR / "pblprfr.jsonl.gz", list(merged.values())),
        "페이지 기록": log[:6] + (["…(%d개 생략)" % max(0, len(log) - 6)] if len(log) > 6 else []),
        "통과": len(perf) > 0,
    })

    # ── 2 상세 표본 ────────────────────────────────────────────────
    ids = sorted(perf)
    step = max(1, len(ids) // max(1, a.detail_sample))
    samp = ids[::step][:a.detail_sample]
    det, derr, has = [], [], {"pcseguidance": 0, "prfcast": 0, "sty": 0, "relates": 0}
    for i in samp:
        root, err = call("pblprfr", {}, path=i)
        time.sleep(SLEEP)
        if err:
            derr.append({"mt20id": i, "🔴": err})
            continue
        rs = rows(root, "pblprfr")
        if not rs:
            derr.append({"mt20id": i, "🔴": "행 0"})
            continue
        d = rs[0]
        det.append(d)
        for k in has:
            if str(d.get(k, "")).strip():
                has[k] += 1
    res["2 상세 표본(pblprfr/{mt20id})"] = {
        "🔴 분모(표본)": len(samp), "받은 것": len(det), "🔴 실패": len(derr),
        "실패 예": derr[:5] or "없음",
        "🔴 s 자리 채움": {k: {"수": v, "비율": round(v / len(det), 4) if det else None}
                       for k, v in has.items()},
        "🔴 파일(합쳐서 쓴다)": _merge_write(OUTDIR / "detail.jsonl.gz", det, "mt20id"),
        "🔴 표본법": "정렬한 mt20id 를 **등간격**으로 뽑았다(무작위가 아니다 — 대표성은 안 쟀다)",
        "통과": len(det) > 0,
    }

    # ── 3 공연장 + 좌표 ────────────────────────────────────────────
    plc, perr, cp = [], [], 1
    while True:
        root, err = call("prfplc", {"cpage": cp, "rows": 100})
        time.sleep(SLEEP)
        if err:
            perr.append({"cpage": cp, "🔴": err})
            break
        rs = rows(root, "prfplc")
        plc.extend(rs)
        if len(rs) < 100 or cp >= 60:
            break
        cp += 1
    pdet, latlon, pderr = [], 0, []
    pids = [p.get("mt10id") for p in plc if p.get("mt10id")]
    pstep = max(1, len(pids) // 300)
    for i in pids[::pstep][:300]:
        root, err = call("prfplc", {}, path=i)
        time.sleep(SLEEP)
        if err:
            pderr.append({"mt10id": i, "🔴": err})
            continue
        rs = rows(root, "prfplc")
        if not rs:
            pderr.append({"mt10id": i, "🔴": "행 0"})
            continue
        d = rs[0]
        pdet.append(d)
        if str(d.get("la", "")).strip() and str(d.get("lo", "")).strip():
            latlon += 1
    res["3 공연장(prfplc)"] = {
        "목록 행": len(plc), "🔴 목록 오류": perr or "없음",
        "🔴 상세 분모(표본)": len(pdet), "🔴 la·lo 둘 다 있는 시설": latlon,
        "비율": round(latlon / len(pdet), 4) if pdet else None,
        "상세 실패": len(pderr), "실패 예": pderr[:3] or "없음",
        "seatscale 있는 것": sum(1 for d in pdet if str(d.get("seatscale", "")).strip()),
        "🔴 파일(합쳐서 쓴다)": _merge_write(OUTDIR / "prfplc.jsonl.gz", pdet, "mt10id"),
        "통과": len(pdet) > 0,
    }

    # ── 4 (a → o) 시계열 ───────────────────────────────────────────
    # 🔴 **`boxoffice` 는 내 손에서 안 열렸다.** 파라미터 여섯 벌을 다 `returncode=01
    #    INVALID REQUEST PARAMETER` 로 되돌려준다. 「없다」가 아니라 **「못 열었다」**로 적는다.
    #    그리고 🔴 **주 세션 표의 `boxoffice 🟢 db 1` 은 바로 그 오류 행 하나였다**.
    box_try = [{"ststype": "day", "date": "20260810"},
               {"ststype": "day", "date": "20260810", "catecode": "AAAA"},
               {"ststype": "day", "date": "20260810", "area": "11"},
               {"ststype": "week", "date": "20260803"},
               {"ststype": "month", "date": "202607"}]
    box_res = []
    for p in box_try:
        _, err = call("boxoffice", p)
        time.sleep(SLEEP)
        box_res.append({"질의": p, "결과": err or "🟢 자료"})
    res["4-가 boxoffice --- 🔴 못 열었다"] = {
        "🔴 시도": box_res,
        "🔴 「없다」가 아니다": "파라미터를 못 맞췄다. 가이드의 필수 인자를 아직 못 찾았다",
        "🔴 물려받지 마라": ("주 세션 표의 `boxoffice 🟢 db 1` 은 **오류 행 하나**였다 --- "
                      "`<dbs><db><returncode>01</returncode>…` 를 자료로 셌다(티처 #91 M1 과 같은 병)"),
        "통과": any(r["결과"] == "🟢 자료" for r in box_res),
    }

    # 🔴 대신 **열린 문**: `prfstsTotal` 은 `ststype=day` 를 주면 **날짜별 행**을 낸다 ---
    #    `prfdt`(날) · `prfcnt`(공연 수) · `amount`(판매액) · `nmrs`(관객수). 이게 (a→o) 다.
    series, serr = [], []
    for (s, e) in _windows(start, end):
        root, err, tr = call_retry("prfstsTotal", {"stdate": s, "eddate": e, "ststype": "day"})
        time.sleep(SLEEP)
        if err:
            serr.append({"창": [s, e], "🔴": err})
            continue
        series.extend(rows(root, "prfstsTotal"))
    days = sorted({r.get("prfdt") for r in series if r.get("prfdt")})
    res["4-나 (a→o) 시계열(prfstsTotal · ststype=day)"] = {
        "🔴 분모(창)": len(_windows(start, end)), "🔴 실패한 창": len(serr),
        "실패 예": serr[:3] or "없음",
        "받은 행": len(series), "서로다른 날": len(days),
        "첫 날": days[0] if days else "없음", "끝 날": days[-1] if days else "없음",
        "열이름": sorted(series[0].keys()) if series else "없음",
        "쓴 행": _write_gz(OUTDIR / "prfsts_day.jsonl.gz", series),
        "🔴 이것이 왜 (a→o) 인가": ("`prfdt`(날)마다 `prfcnt`(공연 수)·`prfprocnt`(작품 수)·"
                            "`amount`(판매액)·`nmrs`(관객수)가 있다 --- **결과가 시간 위에 있다**"),
        "🔴 한계": "공연 **한 건별**이 아니라 **전국 합계**다. 개체별 (a→o) 는 아직 못 받았다",
        "통과": len(series) > 0,
    }

    # ── 5 통계 셋 --- 🔴 op 별 파서 ────────────────────────────────
    st = {}
    for op in ("prfstsTotal", "prfstsCate", "prfstsArea"):
        q = {"stdate": start, "eddate": _windows(start, end)[0][1]}
        if op == "prfstsTotal":
            q["ststype"] = "day"          # 🔴 없으면 returncode=01 --- 「없다」가 아니다
        root, err = call(op, q)
        time.sleep(SLEEP)
        if err:
            st[op] = {"🔴 오류": err, "통과": False}
            continue
        rs = rows(root, op)
        st[op] = {"루트 태그": root.tag, "🔴 기대 루트": SHAPE[op][0], "행": len(rs),
                  "첫 행 키": sorted(rs[0].keys()) if rs else "없음",
                  "통과": len(rs) > 0}
    st["통과"] = all(v.get("통과") for k, v in st.items() if isinstance(v, dict))
    st["🔴 부기"] = ("주 세션의 자는 `root.tag.startswith('db')` 라 `prfstsCate`·`prfstsArea` 를 "
                   "붉게 찍었다. **행은 멀쩡히 있다** — 「자가 붉다」와 「자료가 없다」는 둘이다(조항 59)")
    res["5 통계(prfsts*)"] = st

    res["초"] = round(time.time() - t0, 1)
    res["끝시각(UTC)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    op = ROOT / a.out
    op.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", op, res["초"], "초")
    print("   공연", res["1 공연 목록(pblprfr)"]["합친 뒤"],
          "· 상세", res["2 상세 표본(pblprfr/{mt20id})"]["받은 것"],
          "· 시설좌표", res["3 공연장(prfplc)"]["🔴 la·lo 둘 다 있는 시설"],
          "· (a→o)", res["4-나 (a→o) 시계열(prfstsTotal · ststype=day)"]["받은 행"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
