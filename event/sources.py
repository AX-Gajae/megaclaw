"""원천 읽기 — 다섯 칸(개체·도메인·시각·무슨 일·값 전/후)과 **두 시각**을 만든다.

🔴 시간 게이트(사전등록 §3): 행마다 `t_occur`(일어난 시각)과 `t_observe`(우리가 처음
알 수 있었던 시각)를 **다른 칸**에 적는다. `t_observe` 를 독립적으로 못 얻어 `t_occur`
로 대신 채웠으면 `사후_동일시각=True` 를 단다 — 그 행은 ③ 의 전향 가능 집합에서 뺀다.

🔴 `ingest.doc_select.is_pre_open()` 을 **부르지 않는다**(날짜를 못 읽으면 통과시키는
경로다 — 906·907 이 걸린 자리). 날짜 파싱 실패는 통과가 아니라 `None` 이고 따로 센다.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 영화 일별 표의 숫자 셀 순서 — `data/ingest/kobis/2026-08-09.json` 의 `열 이름 핀`
KOBIS_CELLS = ["순위", "매출액", "누적매출액", "관객수", "누적관객수", "스크린수", "상영횟수"]

#: 🔴 추적 열 = C1 슬롯의 두 번째 축. **카나리아 한 개를 일부러 섞는다**(W-D).
KOBIS_TRACK = ["스크린수", "상영횟수", "순위", "매출액", "관객수", "개봉일"]
CANARY_COL = "존재하지_않는_열_카나리아910"

#: 물질적 변화 문턱 — 사전등록 §4 에서 값을 보기 전에 고정했다
MAT_ABS = 5
MAT_REL = 0.10


def sha256(p: str | Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime_utc(p: str | Path) -> str:
    return datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).isoformat()


def _parse_day(s):
    """🔴 못 읽으면 통과가 아니라 None."""
    if not isinstance(s, str):
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _to_iso(d) -> str | None:
    if d is None:
        return None
    if isinstance(d, date):
        return d.isoformat()
    return str(d)


# ---------------------------------------------------------------- 영화 일별 표
def load_kobis_panel() -> dict:
    """일별 박스오피스 전량 → 개체(제목)별 시계열.

    반환 `{"panel": {제목: [(날짜, {열: 값}, 개봉일)]}, "inputs": {...}, "obs": {날짜: t_observe}}`
    """
    inputs, obs_by_date = {}, {}
    rows_by_date: dict[str, list] = {}

    backfills = [
        ROOT / "data/ingest/kobis/backfill_2023-01-01_full.json",
        ROOT / "data/ingest/kobis/backfill_2026-05-04_90d.json",
    ]
    for p in backfills:
        if not p.exists():
            raise FileNotFoundError(f"{p} 이 없다 — 「없다」가 아니라 「못 읽었다」")
        inputs[str(p.relative_to(ROOT))] = {"sha256": sha256(p), "mtime(UTC)": mtime_utc(p)}
        d = json.loads(p.read_text())
        for dt, rows in d.items():
            rows_by_date.setdefault(dt, []).extend(rows)
            #: 🔴 백필은 수집 스탬프가 파일에 없다 → 파일 mtime 이 t_observe 다(독립적으로 얻는다)
            obs_by_date.setdefault(dt, mtime_utc(p))

    for p in sorted(glob.glob(str(ROOT / "data/ingest/kobis/20*.json"))):
        p = Path(p)
        inputs[str(p.relative_to(ROOT))] = {"sha256": sha256(p), "mtime(UTC)": mtime_utc(p)}
        d = json.loads(p.read_text())
        dt = d.get("date")
        rows = d.get("rows", [])
        rows_by_date.setdefault(dt, []).extend(rows)
        obs_by_date[dt] = d.get("시각(UTC)") or mtime_utc(p)

    panel: dict[str, list] = {}
    n_rows = 0
    for dt in sorted(rows_by_date):
        seen = set()
        for r in rows_by_date[dt]:
            n_rows += 1
            title = r.get("제목")
            if title is None:
                continue
            if title in seen:      # 같은 날 같은 제목 두 번 → 첫 판만
                continue
            seen.add(title)
            cells = r.get("셀")
            if not isinstance(cells, dict):
                raw = r.get("숫자 셀(원본 순서)") or []
                cells = {k: (raw[i] if i < len(raw) else None)
                         for i, k in enumerate(KOBIS_CELLS)}
            panel.setdefault(title, []).append((dt, cells, r.get("개봉일")))

    for t in panel:
        panel[t].sort(key=lambda x: x[0])

    return {"panel": panel, "inputs": inputs, "obs_by_date": obs_by_date,
            "총 관측(행)": n_rows, "고유 날짜": len(rows_by_date), "고유 제목": len(panel)}


def kobis_d3_holdout() -> dict:
    """🔴 D3(판 채점 유보) 영화 406 을 **손으로 안 옮기고 다시 계산**한다(W-E).

    규칙은 `state/tri_domain.py:182` 의 `_from_axes_json(kobis_axes.json, "release_date")`
    와 `lab/harness.Data.rows(post=True, labeled=True, T=2025.0)` 다.
    """
    import calendar
    p = ROOT / "data/state/kobis_axes.json"
    ax = json.loads(p.read_text())
    keys, names = set(), {}
    for k, v in ax.items():
        rd, y = v.get("release_date"), v.get("y")
        if not rd or y is None:
            continue
        dd = _parse_day(rd)
        if dd is None:
            continue
        yf = dd.year + (dd.timetuple().tm_yday - 1) / (366 if calendar.isleap(dd.year) else 365)
        if yf >= 2025.0:
            #: 🔴 902·908d 가 걸린 자리 — 축 키는 `KOBIS-<movieCd>` 다
            keys.add(k.replace("KOBIS-", ""))
            names[k.replace("KOBIS-", "")] = v.get("name")
    return {"경로": str(p.relative_to(ROOT)), "sha256": sha256(p), "D2": len(ax),
            "D3": len(keys), "키": keys, "제목": names,
            "라벨창 마지막 일차": {k.replace("KOBIS-", ""): v.get("마지막 관측일차")
                            for k, v in ax.items()}}


# ---------------------------------------------------------------- 유튜브 폴
def load_youtube_poll() -> dict:
    inputs, snaps = {}, []
    for p in sorted(glob.glob(str(ROOT / "data/ingest/youtube_poll/*.json"))):
        p = Path(p)
        inputs[str(p.relative_to(ROOT))] = {"sha256": sha256(p), "mtime(UTC)": mtime_utc(p)}
        d = json.loads(p.read_text())
        t = d.get("시각(UTC)") or mtime_utc(p)
        vids = {}
        for tgt in d.get("대상", []):
            for v in tgt.get("영상", []):
                vids[v["id"]] = {"제목": v.get("제목"), "채널": v.get("채널"),
                                 "게시일": v.get("게시일") or v.get("published(RSS)"),
                                 "조회수": v.get("조회수_읽은시점"),
                                 "그룹": tgt.get("name")}
        snaps.append((t, vids))
    snaps.sort(key=lambda x: x[0])
    return {"inputs": inputs, "snaps": snaps}


# ---------------------------------------------------------------- 레코드 저장소
DOMAIN_SOURCES = {
    "팝업": ("data/records", "dir"),
    "시장팝업": ("data/market_records", "dir"),
    "아이돌": ("data/idol_records", "dir"),
    "게임": ("data/state/game_records.json", "file"),
    "도서": ("data/state/book_records.json", "file"),
    "펀딩": ("data/state/funding_records.json", "file"),
    "웹툰": ("data/state/webtoon_records.json", "file"),
    "애니": ("data/state/anime_records.json", "file"),
    "모바일": ("data/state/mobile_records.json", "file"),
    "만화": ("data/state/manga_records.json", "file"),
    "세계애니": ("data/state/wanime_records.json", "file"),
    "영화": ("data/ingest/kobis/axes_raw_897.jsonl", "jsonl"),
}

#: 도메인별 「기간 사건」 — (사건 이름, 레코드 안의 날짜 경로)
PERIOD_EVENTS = {
    "팝업": [("팝업.개시", "conditions.period.from"), ("팝업.종료", "conditions.period.to")],
    "시장팝업": [("시장팝업.개시", "conditions.period_from"),
             ("시장팝업.종료", "conditions.period_to")],
    "아이돌": [("아이돌.데뷔", "debut_date")],
}


def _raw_decode_stream(txt: str) -> list:
    """🔴 `axes_raw_897.jsonl` 은 값 안에 개행이 있다 — 줄 단위로 읽으면 깨진다."""
    dec, out, i, n = json.JSONDecoder(), [], 0, len(txt)
    while i < n:
        while i < n and txt[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        obj, i = dec.raw_decode(txt, i)
        out.append(obj)
    return out


#: 도메인별 「결과 창이 열리는 날」 — C7 슬롯의 시각 상한(🔴 결정 시각이 아니다)
WINDOW_START = {
    "팝업": "conditions.period.from", "시장팝업": "conditions.period_from",
    "아이돌": "debut_date", "게임": "release_date", "도서": "pub_date",
    "펀딩": "start_date", "웹툰": "start_date", "애니": "start_date",
    "모바일": "release_date", "만화": "start_date", "세계애니": "start_date",
    "영화": "개봉일",
}


def _dig(o, path):
    cur = o
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def load_records(domain: str) -> dict:
    """D1(원천 파일/레코드) 을 읽는다. 🔴 못 읽으면 「0」이 아니라 「못 읽었다」."""
    rel, kind = DOMAIN_SOURCES[domain]
    p = ROOT / rel
    if not p.exists():
        return {"경로": rel, "상태": "🔴 못 읽었다 — 경로가 없다", "레코드": [], "D1": None,
                "inputs": {}}
    inputs, recs = {}, []
    if kind == "dir":
        fs = sorted(glob.glob(str(p / "*.json")))
        mt = mtime_utc(p)
        for f in fs:
            recs.append(json.loads(Path(f).read_text()))
        inputs[rel] = {"파일 수": len(fs), "디렉터리 mtime(UTC)": mt,
                       "sha256(파일명 목록)": hashlib.sha256(
                           "\n".join(os.path.basename(x) for x in fs).encode()).hexdigest()}
        obs = max((mtime_utc(f) for f in fs), default=mt)
    elif kind == "file":
        obj = json.loads(p.read_text())
        recs = obj if isinstance(obj, list) else list(obj.values())
        inputs[rel] = {"sha256": sha256(p), "mtime(UTC)": mtime_utc(p)}
        obs = mtime_utc(p)
    else:  # jsonl — 🔴 값 안에 개행이 있는 행이 있다. splitlines() 로 읽으면 깨진다
        recs = _raw_decode_stream(p.read_text())
        inputs[rel] = {"sha256": sha256(p), "mtime(UTC)": mtime_utc(p)}
        obs = mtime_utc(p)
    return {"경로": rel, "상태": "읽었다", "레코드": recs, "D1": len(recs),
            "inputs": inputs, "t_observe": obs}


def load_popup_visitor() -> dict:
    p = ROOT / "data/state/popup_visitor_daily.jsonl"
    if not p.exists():
        return {"상태": "🔴 못 읽었다", "행": [], "inputs": {}}
    rows = [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
    return {"상태": "읽었다", "행": rows,
            "inputs": {str(p.relative_to(ROOT)): {"sha256": sha256(p),
                                                  "mtime(UTC)": mtime_utc(p)}}}


def load_seal() -> dict:
    fs = sorted(glob.glob(str(ROOT / "cycle_log/forward/ip/seal_*.json")))
    if not fs:
        return {"상태": "🔴 못 읽었다 — 봉인 파일이 없다", "행": 0, "inputs": {}}
    p = Path(fs[-1])
    d = json.loads(p.read_text())
    return {"상태": "읽었다", "봉인일": d.get("봉인일"), "봉인 시각": d.get("봉인 시각"),
            "행": d.get("행"), "창(개월)": 24,
            "inputs": {str(p.relative_to(ROOT)): {"sha256": sha256(p),
                                                  "mtime(UTC)": mtime_utc(p)}}}
