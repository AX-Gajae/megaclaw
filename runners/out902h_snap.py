"""지평 902 — **우리가 이미 매일 쌓고 있는 것이 무엇을 열었나** (⓪-나 · 안쪽 지평).

티처 #64 M10 은 *「날짜별 스냅숏을 이미 매일 모으고 있고 그게 W4 를 여는 기제인데
재고 조사가 「안 뒤진 원천」 목록에조차 안 넣었다」* 라고 **지적만 했다.**
🔴 **그 스냅숏이 실제로 무엇을 여는지는 아무도 안 쟀다.** 이 러너가 센다.

**판정 어법(미리 고정)**
  · 효과를 재지 않는다. 「무엇이 있나」와 「그게 무엇을 여나」까지다(887형 회피).
  · 열면 「연다 · N개 · 분모 M · 어느 열」. 안 열면 「무엇이 없어서 안 여나」.
  · 수마다 분모를 명시한다(조항 60).
  · 「없다」/「못 봤다」/「못 읽었다」를 가른다(조항 59).

**측정 다섯**
  ① 날짜별로 갈라 쌓이는 것 전수 — 파일·행·날짜 범위·도메인·언제부터
  ② 개체 키와 **2회 이상 나타나는 개체 수**(분모 명시) — 그게 패널의 정의다
  ③ 🔴 **개입 값(901 의 T1 열)이 시점 사이에 바뀐 개체** — 핵심
  ④ 성장률과 도달 시점
  ⑤ 판 유보(D3)와의 교집합

읽기 전용이다. `ingest/**` 를 고치지 않는다 — 세기만 한다.
"""
from __future__ import annotations

import collections
import datetime as dt
import glob
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runners/out902h_snap.json"
SELF = Path(__file__).resolve()


def sha(p) -> str:
    p = Path(p)
    if not p.exists():
        return "없음"
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# 🔴 **`stamp()` 은 실행 「시작」에서 부른다**(티처 #64 C3 — 901 이 끝에서 불러
#    116.9초 실행의 시작==끝이 됐다). `git HEAD` 는 판정에 안 쓴다(v3.2).
INPUTS = [
    "data/ingest/kobis/2026-08-01.json",
    "data/ingest/kobis/2026-08-08.json",
    "data/ingest/kobis/2026-08-09.json",
    "data/ingest/kobis/2026-08-10.json",
    "data/ingest/kobis/backfill_2023-01-01_full.json",
    "data/ingest/kobis/backfill_2026-05-04_90d.json",
    "data/ingest/kobis/axes_raw_897.jsonl",
    "data/ingest/youtube_poll/2026-08-09.json",
    "data/ingest/youtube_poll/2026-08-10.json",
    "data/ingest/youtube_poll/2026-08-11.json",
    "data/ingest/yt_poll_targets.json",
    "data/state/popup_visitor_daily.jsonl",
    "data/state/popup_visitor_daily_log.jsonl",
    "data/state/collect_log.jsonl",
    "data/state/kobis_axes.json",
    "runners/out901_identify.json",
    "ingest/collect.py",
    "ingest/cycle_open.py",
]


def stamp() -> dict:
    return {
        "시작 시각": dt.datetime.now().isoformat(timespec="seconds"),
        "코드 sha256": {"runners/out902h_snap.py": sha(SELF)},
        "입력 sha256": {p: sha(ROOT / p) for p in INPUTS},
    }


CELLS = ["순위", "매출액", "누적매출액", "관객수", "누적관객수", "스크린수", "상영횟수"]


def mtime(p) -> str:
    p = ROOT / p
    return dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="minutes") \
        if p.exists() else "없음"


# ── ① 재고 ────────────────────────────────────────────────────────────────
def inventory() -> dict:
    inv = {}

    # 1) 영화 — 일별 박스오피스
    kd = sorted(p for p in glob.glob(str(ROOT / "data/ingest/kobis/*.json"))
                if os.path.basename(p)[:4].isdigit())
    inv["영화 일별 박스오피스"] = {
        "도메인": "영화(12번째 채점 도메인)",
        "🔴 이 원천은 셋으로 나뉜다": "날짜별 파일 · 90일 백필 · 전체 백필 — 셋이 같은 표를 담는다",
        "날짜별 파일(`data/ingest/kobis/YYYY-MM-DD.json`)": {
            "파일 수": len(kd),
            "파일": [os.path.basename(p) for p in kd],
            "파일별 rows": {os.path.basename(p): len(json.loads(Path(p).read_text())["rows"]) for p in kd},
            "행 합": sum(len(json.loads(Path(p).read_text())["rows"]) for p in kd),
            "언제부터": mtime("data/ingest/kobis/2026-08-01.json"),
            "늘리는 것": "`ingest/collect.py` COLLECTORS['kobis'] — `cycle_open` ① 수집이 부른다",
        },
        "백필 `backfill_2026-05-04_90d.json`": {
            "일수": len(json.loads((ROOT / "data/ingest/kobis/backfill_2026-05-04_90d.json").read_text())),
            "언제": mtime("data/ingest/kobis/backfill_2026-05-04_90d.json"),
        },
        "백필 `backfill_2023-01-01_full.json`": {
            "일수": len(json.loads((ROOT / "data/ingest/kobis/backfill_2023-01-01_full.json").read_text())),
            "언제": mtime("data/ingest/kobis/backfill_2023-01-01_full.json"),
        },
    }

    # 2) 유튜브 폴
    yd = sorted(glob.glob(str(ROOT / "data/ingest/youtube_poll/*.json")))
    inv["유튜브 폴"] = {
        "도메인": "🔴 12 채점 도메인 중 어디에도 안 들어간다 — 대상은 **아이돌 17그룹**의 채널이다",
        "파일 수": len(yd),
        "파일": [os.path.basename(p) for p in yd],
        "언제부터": mtime("data/ingest/youtube_poll/2026-08-09.json"),
        "늘리는 것": "`ingest/collect.py` COLLECTORS['yt_poll'] · 하루 1점(같은 날 재실행은 건너뜀)",
        "🔴 설계 한계": "하루 1점만 남긴다 — 같은 날 다시 돌리면 **앞선 스냅숏을 덮어쓴다**(collect.py 주석)",
    }

    # 3) 팝업 방문자 일별
    pv = [json.loads(l) for l in (ROOT / "data/state/popup_visitor_daily.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    pl = [json.loads(l) for l in (ROOT / "data/state/popup_visitor_daily_log.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    inv["팝업 방문자 일별"] = {
        "도메인": "팝업",
        "행": len(pv),
        "🔴 스냅숏 시각 가짓수": len({r.get("_스냅샷(UTC)") for r in pv}),
        "스냅숏 시각": sorted({r.get("_스냅샷(UTC)") for r in pv}),
        "로그 행": len(pl),
        "로그 시각 범위": [pl[0]["시각(UTC)"], pl[-1]["시각(UTC)"]],
        "로그 신규 행 합": sum(r.get("신규 행", 0) for r in pl),
        "🔴 읽는 법": "로그는 33회 찍혔지만 **첫 회 48행 뒤 전부 신규 0** — "
                    "여러 번 **찍었을 뿐** 여러 시점을 **담고 있지 않다**",
        "늘리는 것": "`ingest/collect.py` COLLECTORS['popupsnap'](BQ 읽기 전용)",
    }

    # 4) 수집 장부
    cl = [json.loads(l) for l in (ROOT / "data/state/collect_log.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    inv["수집 장부(collect_log)"] = {
        "도메인": "메타(자료 아님)",
        "행": len(cl),
        "시각 범위": [cl[0]["시각(UTC)"], cl[-1]["시각(UTC)"]],
        "수집기별 회수": dict(collections.Counter(r["이름"] for r in cl)),
    }

    # 5) 시군구 방문자 월별 — 날짜별로 갈리지만 **매일 안 는다**
    vf = sorted(p for p in glob.glob(str(ROOT / "data/state/visitors/*.json"))
                if os.path.basename(p)[:4].isdigit())
    inv["시군구 방문자 월별(`data/state/visitors`)"] = {
        "도메인": "공간 보조(채점 도메인 아님)",
        "파일 수": len(vf),
        "날짜 범위": [os.path.basename(vf[0])[:-5], os.path.basename(vf[-1])[:-5]] if vf else [],
        "🔴 매일 느나": "아니다 — 파일 mtime 이 전부 2026-08-05 하루다(1회 백필)",
        "mtime 가짓수": len({dt.date.fromtimestamp(os.path.getmtime(p)).isoformat() for p in vf}),
    }

    # 6) 생활인구 — 901 이 이미 쟀다
    lp = sorted(glob.glob(str(ROOT / "data/ingest/seoul_lifepop/*.zip")))
    inv["서울 생활인구 월별(zip)"] = {
        "도메인": "공간 보조",
        "파일 수": len(lp),
        "🔴 매일 느나": "아니다 — 손으로 두 달 받았다(노트 901 이 실측)",
    }

    # 7) 🔴 **T1 열이 사는 원천은 날짜별로 안 갈린다** — 이게 판정의 축이다
    stores = {}
    for d in ("data/records", "data/market_records", "data/idol_records"):
        ps = glob.glob(str(ROOT / d / "*.json"))
        stores[d] = {"파일 수": len(ps),
                     "mtime 날짜 가짓수": len({dt.date.fromtimestamp(os.path.getmtime(p)).isoformat() for p in ps}),
                     "mtime 날짜": sorted({dt.date.fromtimestamp(os.path.getmtime(p)).isoformat() for p in ps})}
    for f in ("data/state/game_records.json", "data/state/book_records.json",
              "data/state/funding_records.json", "data/state/webtoon_records.json",
              "data/state/anime_records.json", "data/state/mobile_records.json",
              "data/state/manga_records.json", "data/state/wanime_records.json"):
        stores[f] = {"파일 수": 1, "mtime": mtime(f)}
    inv["🔴 대조군 — 901 의 T1 열이 사는 원천"] = {
        "무엇": "12도메인의 레코드 저장소. **개입 값(T1)은 전부 여기 있다**",
        "날짜별로 갈리나": "🔴 아니다 — 파일 하나에 레코드 하나(또는 도메인 하나에 파일 하나)이고 "
                      "**날짜 축이 없다**. 같은 레코드의 두 번째 판이 없다",
        "저장소별": stores,
    }
    return inv


# ── ② · ③ 영화 일별 판 ────────────────────────────────────────────────────
def movie_panel() -> tuple[dict, dict]:
    panel = collections.defaultdict(dict)      # 제목 -> 날짜 -> 값
    src = collections.Counter()
    dup = collections.Counter()

    def add(date, rows, tag):
        for r in rows:
            cells = dict(zip(CELLS, r["숫자 셀(원본 순서)"]))
            t = r["제목"]
            if date in panel[t]:
                dup[tag] += 1
            panel[t][date] = {"개봉일": r.get("개봉일"), **cells,
                              "_출처": tag, "_셀수": len(r["숫자 셀(원본 순서)"])}
            src[tag] += 1

    for p, tag in [("data/ingest/kobis/backfill_2023-01-01_full.json", "백필_전체"),
                   ("data/ingest/kobis/backfill_2026-05-04_90d.json", "백필_90일")]:
        for k, v in json.loads((ROOT / p).read_text()).items():
            add(k, v, tag)
    daily_titles, daily_dates = set(), set()
    for p in sorted(glob.glob(str(ROOT / "data/ingest/kobis/*.json"))):
        if not os.path.basename(p)[:4].isdigit():
            continue
        d = json.loads(Path(p).read_text())
        add(d["date"], d["rows"], "날짜별파일")
        daily_titles |= {r["제목"] for r in d["rows"]}
        daily_dates.add(d["date"])

    dates = sorted({dd for m in panel.values() for dd in m})
    d0, d1 = dt.date.fromisoformat(dates[0]), dt.date.fromisoformat(dates[-1])
    span = (d1 - d0).days + 1
    missing = [(d0 + dt.timedelta(days=i)).isoformat() for i in range(span)
               if (d0 + dt.timedelta(days=i)).isoformat() not in set(dates)]

    ge2 = [t for t, m in panel.items() if len(m) >= 2]
    obs = [len(m) for m in panel.values()]

    def changed(col, entities, strict=True):
        """`strict`: 결측(None)을 값 가짓수에서 뺀다 — 결측↔값은 「바뀌었다」가 아니다."""
        n = 0
        for t in entities:
            vs = {panel[t][d].get(col) for d in panel[t]}
            if strict:
                vs = {v for v in vs if v is not None}
            if len(vs) > 1:
                n += 1
        return n

    # 개체 성장 — 달마다 처음 나타난 제목 수
    first = {}
    for t, m in panel.items():
        first[t] = min(m)
    permonth = collections.Counter(v[:7] for v in first.values())

    ent = {
        "개체 키": "제목(문자열)",
        "🔴 키의 한계": "일별 표에 `movieCd` 가 없다 — 제목이 유일한 키다. "
                    "같은 제목의 재개봉이 한 개체로 뭉친다(아래 「개봉일이 바뀐 개체」가 그 표지다)",
        "총 관측(행)": sum(src.values()),
        "출처별 행": dict(src),
        "🔴 (제목,날짜) 중복 덮어쓰기": dict(dup),
        "고유 날짜": len(dates),
        "날짜 범위": [dates[0], dates[-1]],
        "달력 일수": span,
        "🔴 빠진 날": {"수": len(missing), "목록": missing},
        "고유 제목(분모)": len(panel),
        "🔴 2회 이상 나타난 제목": len(ge2),
        "2회 이상 비율": round(len(ge2) / len(panel), 4),
        "관측 수 중앙값": sorted(obs)[len(obs) // 2],
        "관측 수 최대": max(obs),
        "달마다 처음 나타난 제목 수(최근 12달)": dict(sorted(permonth.items())[-12:]),
        "날짜별파일 4개만 볼 때": {
            "날짜": sorted(daily_dates),
            "고유 제목": len(daily_titles),
            "그중 그 4일 안에서 2회+": sum(
                1 for t in daily_titles if len(set(panel[t]) & daily_dates) >= 2),
        },
    }

    chg = {
        "분모(2회 이상 관측된 제목)": len(ge2),
        "열별 · 값이 바뀐 개체 수(결측 제외)": {c: changed(c, ge2) for c in ["개봉일"] + CELLS},
        "열별 · 값이 바뀐 개체 수(결측 포함)": {c: changed(c, ge2, strict=False) for c in ["개봉일"] + CELLS},
    }
    return panel, {"② 개체": ent, "③ 값 변화": chg}


# ── ② · ③ 유튜브 폴 ───────────────────────────────────────────────────────
def yt_panel() -> dict:
    snap = {}
    for p in sorted(glob.glob(str(ROOT / "data/ingest/youtube_poll/*.json"))):
        d = json.loads(Path(p).read_text())
        day = os.path.basename(p)[:-5]
        m = {}
        for t in d["대상"]:
            for v in (t.get("영상") or []):
                m[v["id"]] = {"채널": t["channel_id"], "그룹": t["name"],
                              "제목": v.get("제목"), "게시일": v.get("게시일"),
                              "조회수": v.get("조회수_읽은시점")}
        snap[day] = m
    cnt = collections.Counter(i for m in snap.values() for i in m)
    ge2 = [i for i, c in cnt.items() if c >= 2]

    def changed(col, strict=True):
        out = []
        for i in ge2:
            vs = [snap[d][i].get(col) for d in sorted(snap) if i in snap[d]]
            if strict:
                vs = [v for v in vs if v is not None]
            if len(set(vs)) > 1:
                out.append(i)
        return out

    def missing(col):
        return [i for i in ge2
                if any(snap[d][i].get(col) is None for d in snap if i in snap[d])]

    title_chg = changed("제목")
    null_reads = missing("제목")
    return {
        "② 개체": {
            "개체 키": "영상 id(YouTube videoId) · 상위 키는 channel_id",
            "스냅숏(날짜) 수": len(snap),
            "날짜": sorted(snap),
            "스냅숏별 영상 관측": {d: len(m) for d, m in snap.items()},
            "고유 영상 id(분모)": len(cnt),
            "🔴 2회 이상 나타난 영상": len(ge2),
            "3회 전부 나타난 영상": sum(1 for c in cnt.values() if c == len(snap)),
            "고유 채널": len({v["채널"] for m in snap.values() for v in m.values()}),
            "🔴 창이 굴러간다": "채널마다 최신 15개만 담는다 — 고유 id %d 중 %d 만 3회 다 있다"
                          % (len(cnt), sum(1 for c in cnt.values() if c == len(snap))),
        },
        "③ 값 변화": {
            "분모(2회 이상 나타난 영상)": len(ge2),
            "값이 바뀐 영상(결측 제외 · 엄격)": {
                c: len(changed(c)) for c in ("제목", "게시일", "조회수", "채널")},
            "값이 바뀐 영상(결측 포함)": {
                c: len(changed(c, strict=False)) for c in ("제목", "게시일", "조회수", "채널")},
            "🔴 결측(=못 읽었다)이 있는 영상": {
                c: len(missing(c)) for c in ("제목", "게시일", "조회수")},
            "🔴 조항 59": "결측 포함으로 세면 제목 변화가 6, 결측을 빼면 **1** 이다. "
                       "차이 5는 「바뀌었다」가 아니라 **한 스냅숏에서 못 읽었다**(제목·조회수가 동시에 null). "
                       "장부의 「255 영상관측」은 이 5를 **관측으로 센다**",
            "🔴 못 읽은 영상 전량(id)": null_reads,
            "🔴 제목이 실제로 바뀐 영상 전량(id · 값)": {
                i: [(d, snap[d][i]["제목"]) for d in sorted(snap)
                    if i in snap[d] and snap[d][i].get("제목") is not None]
                for i in title_chg},
        },
    }


# ── ② 팝업 방문자 ─────────────────────────────────────────────────────────
def popup_panel() -> dict:
    rows = [json.loads(l) for l in (ROOT / "data/state/popup_visitor_daily.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()]
    eng = collections.Counter(r["engagement_id"] for r in rows)
    return {
        "② 개체": {
            "개체 키": "engagement_id(팝업) · 행 키는 visitor_daily_id = engagement_id + '_' + visit_date",
            "행(분모)": len(rows),
            "고유 engagement_id": len(eng),
            "🔴 2회 이상 나타난 engagement_id": sum(1 for v in eng.values() if v >= 2),
            "engagement 별 행 수": dict(eng.most_common()),
            "visit_date 범위": [min(r["visit_date"] for r in rows), max(r["visit_date"] for r in rows)],
            "🔴 스냅숏 시각 가짓수": len({r.get("_스냅샷(UTC)") for r in rows}),
            "🔴 읽는 법": "같은 팝업이 여러 **방문일**에 나타난다(결과의 시계열). "
                        "그러나 **스냅숏 시각은 하나뿐**이라 「같은 값을 두 시점에 다시 읽은」 적은 0회다",
        },
        "③ 값 변화": {
            "🔴 못 잰다": "스냅숏 시각이 1가지라 시점 사이 변화를 정의할 수 없다. "
                       "「없다」가 아니라 **잴 대상이 없다**",
            "열 목록": sorted(set(rows[0].keys())),
            "🔴 개입 열이 있나": "없다 — 전부 결과(방문자·예약·노쇼·워크인)와 출처 메타다. "
                          "901 의 팝업 T1 25열 중 이 표에 있는 것 0",
        },
    }


# ── ⑤ 판 유보(D3) 교집합 ──────────────────────────────────────────────────
def d3_intersections(panel) -> dict:
    sys.path.insert(0, str(ROOT / "runners"))
    import numpy as np                                     # noqa: E402
    import ff753 as FF                                     # noqa: E402
    d0 = FF.shell(FF.base())
    res = {}

    # 영화 — 축 키가 `KOBIS-<code>` 다(901 이 조용한 0 에 걸린 자리)
    keys = list(json.loads((ROOT / "data/state/kobis_axes.json").read_text()))
    m = d0.rows("영화", post=True, labeled=True, T=2025.0)
    assert len(keys) == len(m) == len(d0.dom["영화"][2]), "🔴 영화 D2 != D4 — 중단"
    d3 = [k.replace("KOBIS-", "") for k, b in zip(keys, m) if b]
    ax = {}
    # 🔴 `splitlines()` 는 ` `·`\x0b` 에서도 자른다 — 제목·요약에 그런 문자가 있어
    #    줄이 쪼개져 JSON 이 깨졌다(첫 판이 실제로 여기서 죽었다). `\n` 으로만 자른다.
    for l in (ROOT / "data/ingest/kobis/axes_raw_897.jsonl").read_text(encoding="utf-8").split("\n"):
        if l.strip():
            r = json.loads(l)
            if r.get("code"):
                ax[r["code"]] = r
    hit = [k for k in d3 if k in ax]
    assert len(hit) == len(d3), f"🔴 D3 되짚기 조용한 0/부분 실패 영화: {len(d3)} → {len(hit)}"
    d3t = {ax[k]["제목"] for k in hit}
    ge2 = {t for t, mm in panel.items() if len(mm) >= 2}
    on = d3t & set(panel)
    on2 = d3t & ge2

    def chg(col, ents):
        n = 0
        for t in ents:
            vs = {panel[t][d].get(col) for d in panel[t]}
            vs = {v for v in vs if v is not None}
            if len(vs) > 1:
                n += 1
        return n

    # 🔴 「처치 시점」이 실제로 라벨 창 **안**에 있나 — 라벨은 개봉+20일 누적관객이다
    #    (`runners/build836.py:111` · `runners/harvest844.py:35`).
    win = {"분모(D3 · 2회+ 관측)": len(on2), "라벨 창": "개봉일 ~ 개봉일+20일",
           "창 안에 스크린수 변화가 1회 이상 있는 개체": 0,
           "창 안 스크린수 변화 사건 수(합)": 0,
           "창 안 관측일 수 중앙값": None,
           "🔴 창 안 관측이 0인 개체": 0}
    ndays = []
    for t in on2:
        rel = None
        for d in panel[t]:
            rel = rel or panel[t][d].get("개봉일")
        if not rel:
            continue
        try:
            r0 = dt.date.fromisoformat(rel)
        except Exception:
            continue
        ds = sorted(d for d in panel[t]
                    if r0 <= dt.date.fromisoformat(d) <= r0 + dt.timedelta(days=20))
        ndays.append(len(ds))
        if not ds:
            win["🔴 창 안 관측이 0인 개체"] += 1
            continue
        vs = [panel[t][d].get("스크린수") for d in ds]
        vs = [v for v in vs if v is not None]
        ev = sum(1 for a, b in zip(vs, vs[1:]) if a != b)
        if ev:
            win["창 안에 스크린수 변화가 1회 이상 있는 개체"] += 1
            win["창 안 스크린수 변화 사건 수(합)"] += ev
    win["창 안 관측일 수 중앙값"] = sorted(ndays)[len(ndays) // 2] if ndays else None
    win["🔴 읽는 법"] = ("스냅숏 사이의 변화는 처치 시점을 **[t, t+1] 로 묶어 준다** — "
                    "901 이 W4 로 적은 「언제 정해졌는지 기록이 없다」가 이 열에서는 없어진다. "
                    "⚠ 다만 **W8(배정 기제)은 그대로다** — 누가 왜 스크린을 늘렸는지는 여전히 없고, "
                    "스크린수는 직전 흥행에 반응하므로 **동시성**이 남는다. 효과는 안 쟀다")

    res["영화"] = {
        "🔴 라벨 창 안의 처치 시점": win,
        "D2(축행)": len(keys), "D4(도메인 행)": len(d0.dom["영화"][2]),
        "🔴 D3(판 채점 유보)": int(m.sum()),
        "D3 → 원천 되짚기": f"{len(hit)}/{len(d3)}",
        "D3 고유 제목(분모)": len(d3t),
        "🔴 일별 판에 있는 D3 제목": len(on),
        "🔴 그중 2회 이상 관측": len(on2),
        "그중 스크린수가 바뀐 개체": chg("스크린수", on2),
        "그중 상영횟수가 바뀐 개체": chg("상영횟수", on2),
        "그중 개봉일이 바뀐 개체": chg("개봉일", on2),
        "🔴 날짜별 파일 4개(2026-08)에 있는 D3 제목": len(
            d3t & {t for t in panel if set(panel[t]) & {"2026-08-01", "2026-08-08",
                                                        "2026-08-09", "2026-08-10"}}),
        "판 유보 3,775 대비": round(len(on) / 3775, 5),
    }

    # 팝업 — 901h 와 같은 배선
    from lab.popupset import COUNT_OK                        # noqa: E402
    z = np.load(ROOT / "data/state/popup_v2.npz", allow_pickle=True)
    cols = [str(c) for c in z["names"]]
    X, y = z["X"], z["y_perday"]
    meta = json.loads((ROOT / "data/state/popup_v2_meta.json").read_text())
    keep = np.zeros(len(y), bool)
    for g in "ABCDE":
        if f"trust_{g}" in cols:
            keep |= X[:, cols.index(f"trust_{g}")] > 0.5
    keep &= np.isfinite(y)
    keep &= np.array([bool(mm.get("scope_usable")) for mm in meta])
    keep &= np.array([mm.get("counting") in COUNT_OK for mm in meta])
    pids = [mm["id"] for mm, k in zip(meta, keep) if k]
    kp = d0.rows("팝업", post=True, labeled=True, T=2025.0)
    assert len(kp) == len(pids), "🔴 팝업 축행 길이 불일치 — 중단"
    hold = {i for i, b in zip(pids, kp) if b}
    rows = [json.loads(l) for l in (ROOT / "data/state/popup_visitor_daily.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()]
    eng = {r["engagement_id"] for r in rows}
    d1 = {os.path.basename(p)[:-5] for p in glob.glob(str(ROOT / "data/records/*.json"))}
    res["팝업"] = {
        "D1(원천 레코드)": len(d1), "D2(축행)": len(pids), "🔴 D3(유보)": int(kp.sum()),
        "방문자 일별의 고유 engagement(분모)": len(eng),
        "🔴 D3 유보와의 교집합": sorted(eng & hold),
        "D3 교집합 수": len(eng & hold),
        "D2 축행과의 교집합 수": len(eng & set(pids)),
        "D1 과의 교집합": sorted(eng & d1),
        "🔴 D1 에도 없는 engagement": sorted(eng - d1),
    }

    # 아이돌 — 🔴 901 과 같은 이유로 D3 를 못 되짚는다
    tg = json.loads((ROOT / "data/ingest/yt_poll_targets.json").read_text())
    names = {t["name"] for t in tg}
    recs = [json.loads(Path(p).read_text(encoding="utf-8"))
            for p in glob.glob(str(ROOT / "data/idol_records/*.json"))]
    byname = {}
    for r in recs:
        if r.get("group_name"):
            byname[str(r["group_name"])] = r
    matched = sorted(n for n in names if n in byname)
    lab = [n for n in matched if byname[n].get("chodong") not in (None, "")]
    axn = list(json.loads((ROOT / "data/state/idol_axes.json").read_text()))
    ki = d0.rows("아이돌", post=True, labeled=True, T=2025.0)
    res["아이돌(유튜브 폴 대상)"] = {
        "D1(idol_records)": len(recs),
        "D2(idol_axes)": len(axn), "D4(도메인 행)": len(d0.dom["아이돌"][2]),
        "🔴 D3(유보)": int(ki.sum()),
        "🔴 D3 되짚기": "못 한다 — D2 %d != D4 %d 라 축 키를 행에 못 맞춘다"
                    "(901 `ident901.py:137-140` 와 같은 이유). 「없다」가 아니라 **못 셌다**"
                    % (len(axn), len(d0.dom["아이돌"][2])),
        "유튜브 폴 대상(분모)": len(names),
        "🔴 그중 idol_records(D1 %d)에 group_name 으로 붙는 것" % len(recs): len(matched),
        "붙는 이름": matched,
        "🔴 안 붙는 이름": sorted(names - set(byname)),
        "붙는 것 중 라벨(chodong) 있는 것": len(lab),
        "⚠ 단서": "이름 문자열 일치다. 노트 834 가 이 17 중 여럿을 「불일치 의심 — 사람 확인 필수」로 "
                "표시해 두었다(`yt_poll_targets.json`) — **신원 확인은 안 했다**",
    }
    return res


# ── ④ 성장률 ─────────────────────────────────────────────────────────────
def growth(mp: dict, yt: dict) -> dict:
    cl = [json.loads(l) for l in (ROOT / "data/state/collect_log.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    by = collections.defaultdict(list)
    for r in cl:
        by[r["이름"]].append(r)

    # 🔴 장부의 kobis 「흥행행」이 실제로 무엇을 세고 있나 — 직접 재현한다
    def kobis_obs(d):
        if isinstance(d, dict):
            for v in d.values():
                if isinstance(v, list):
                    return len(v)
        return 0
    per = {}
    for p in sorted(glob.glob(str(ROOT / "data/ingest/kobis/*.json"))):
        n = os.path.basename(p)
        if n.startswith(("backfill", "threshold")):
            continue
        d = json.loads(Path(p).read_text())
        firstlist = next((k for k, v in d.items() if isinstance(v, list)), None)
        per[n] = {"collect.py 가 세는 수": kobis_obs(d), "그 수의 정체": firstlist,
                  "실제 rows": len(d.get("rows", []))}

    dailies = mp["② 개체"]["날짜별파일 4개만 볼 때"]["날짜"]
    return {
        "장부(collect_log) 기록": {
            k: {"회수": len(v),
                "판정": dict(collections.Counter(x["판정"] for x in v)),
                "델타 합": sum(x["델타"] for x in v),
                "단위": v[0]["단위"],
                "성장 사건": [{"시각": x["시각(UTC)"][:16], "델타": x["델타"],
                            "before→after": [x["before"], x["after"]]}
                           for x in v if x["델타"]]}
            for k, v in by.items()},
        "🔴 장부의 kobis 「흥행행」은 흥행행이 아니다": {
            "무엇": "`ingest/collect.py:_kobis_obs` 가 dict 를 훑어 **처음 만난 리스트**의 길이를 낸다. "
                  "새 판 파일은 키 순서가 `… '열 이름 핀'(7개) … 'rows'` 라서 **7 을 낸다**",
            "파일별": per,
            "장부의 마지막 after": by["kobis"][-1]["after"] if by.get("kobis") else None,
            "내가 같은 함수로 다시 센 합": sum(v["collect.py 가 세는 수"] for v in per.values()),
            "실제 rows 합": sum(v["실제 rows"] for v in per.values()),
            "🔴 결과": "하루 +1파일이 장부엔 **+7**로 찍힌다(실제 95~114행). "
                    "판정(성장/무성장)의 **부호는 맞고 크기가 ~14배 틀리다**. "
                    "같은 날 파일이 **안에서** 자라면(행 추가) 장부는 **무성장**으로 읽는다",
            "⚠ 내가 안 한 것": "🔴 `ingest/**` 는 내 파일이 아니라 **고치지 않았다** — 세어서 적기만 했다",
        },
        "실측 속도": {
            "영화 일별 파일": {
                "관측 기간": [dailies[0], dailies[-1]] if dailies else [],
                "파일/일": 1,
                "파일별 rows": {k: v["실제 rows"] for k, v in per.items()},
                "행/일(평균)": round(sum(v["실제 rows"] for v in per.values()) / len(per), 1),
                "🔴 월 환산(행)": round(30 * sum(v["실제 rows"] for v in per.values()) / len(per)),
                "달마다 처음 나타난 제목 수(최근 12달)":
                    mp["② 개체"]["달마다 처음 나타난 제목 수(최근 12달)"]},
            "유튜브 폴": {"관측/일": 255, "🔴 월 환산": 30 * 255,
                     "🔴 개체는 안 는다": "채널 17 고정 · 채널당 최신 15개 창이 굴러간다"},
            "팝업 방문자": {"관측/일": 0, "연속 무성장": len(by.get("popupsnap", [])),
                      "사유": "원천이 2026-08-05 21분 단일 소급 적재 뒤 동결(노트 673)"},
        },
        "🔴 「언제 901 이 필요하다고 한 것에 닿나」": {
            "901 이 필요하다고 한 것": "W4(개입 값의 **처치 시점**) · W8(배정 기제)",
            "🔴 도달 조건": "스냅숏이 W4 를 여는 것은 **그 스냅숏이 T1 열을 다시 읽고, 값이 바뀔 때**뿐이다",
            "🔴 지금 도는 수집기 셋 중 T1 열을 다시 읽는 것": 0,
            "근거": "kobis 일별 표에는 영화 T1 둘(`개봉일`·`배급사`) 중 `배급사` 가 없고 `개봉일` 은 "
                  "재개봉 말고는 안 바뀐다 · yt_poll 은 아이돌 T1 다섯 중 0개를 담는다 · "
                  "popupsnap 은 팝업 T1 25 중 0개를 담는다",
            "🔴 그래서 도달 시점": "**없다 — 이 속도로는 영영 안 닿는다.** 시간이 모자란 게 아니라 "
                            "**T1 열을 다시 읽는 수집기가 0개**다. 하루를 더 기다려도 같은 열이 안 늘어난다",
        },
    }


def main() -> None:
    st = stamp()                                   # 🔴 실행 **시작**에서 부른다
    out = {"노트": 902, "자리": "루프 v3 ⓪-나(지평 · 안쪽)",
           "성격": "🔴 무엇이 있나 · 그게 무엇을 여나 까지. **효과는 안 잰다**(887형 회피)",
           **st}

    out["① 재고"] = inventory()
    panel, mp = movie_panel()
    out["②③ 영화 일별 박스오피스"] = mp
    yt = yt_panel()
    out["②③ 유튜브 폴"] = yt
    out["②③ 팝업 방문자 일별"] = popup_panel()
    out["④ 성장률"] = growth(mp, yt)
    out["⑤ 판 유보(D3) 교집합"] = d3_intersections(panel)

    # ── ⑥ 판정 ──────────────────────────────────────────────────────────
    t1 = {d: sorted({k.split("→")[0].strip() for k in v["짝"]})
          for d, v in json.loads((ROOT / "runners/out901_identify.json").read_text())["판정 표"].items()}
    kd_cols = ["제목", "개봉일"] + CELLS
    yt_cols = ["id", "제목", "채널", "게시일", "조회수_읽은시점", "published(RSS)"]
    out["🔴 T1 열 겹침 — 스냅숏이 담는 열 ∩ 901 이 T1 로 센 열"] = {
        "영화": {"901 T1(분모)": t1["영화"], "일별 표의 열": kd_cols,
               "🔴 겹치는 T1": sorted(set(t1["영화"]) & set(kd_cols)),
               "🔴 안 담기는 T1": sorted(set(t1["영화"]) - set(kd_cols))},
        "아이돌": {"901 T1(분모)": t1["아이돌"], "yt 폴의 열": yt_cols,
                "🔴 겹치는 T1": sorted(set(t1["아이돌"]) & set(yt_cols))},
        "팝업": {"901 T1 수(분모)": len(t1["팝업"]),
               "방문자 일별의 열": sorted(json.loads(
                   (ROOT / "data/state/popup_visitor_daily.jsonl")
                   .read_text(encoding="utf-8").splitlines()[0]).keys()),
               "🔴 겹치는 T1": sorted(set(t1["팝업"]) & set(json.loads(
                   (ROOT / "data/state/popup_visitor_daily.jsonl")
                   .read_text(encoding="utf-8").splitlines()[0]).keys()))},
    }

    # ── ⑥ 판정 ──────────────────────────────────────────────────────────
    mv = out["⑤ 판 유보(D3) 교집합"]["영화"]
    out["🔴 ⑥ 판정 — W4 를 여나"] = {
        "가 · 901 이 센 T1 열에 대해서는": {
            "판정": "🔴 **안 연다**",
            "무엇이 없어서": "🔴 **T1 열을 다시 읽는 수집기가 0개다.** 도는 수집기 셋(kobis·yt_poll·popupsnap) "
                       "중 어느 것도 `data/records`·`data/market_records`·`data/idol_records`·"
                       "`data/state/*_records.json` 를 다시 읽지 않는다. 그 저장소들의 파일 mtime 이 "
                       "전부 2026-07-27~08-01 하루씩이다 — **같은 레코드의 두 번째 판이 저장소에 0개**다",
            "열 겹침(분모 = 901 T1 열 수)": {
                "영화 2 중 겹치는 것 1(`개봉일`)": "그런데 개봉일은 **재개봉 6개 말고는 안 바뀐다**"
                                       "(분모 D3 2회+ 404)",
                "아이돌 5 중 0": "yt_poll 은 조회수·제목만 담는다",
                "팝업 25 중 0": "방문자 일별은 전부 결과 열이다",
            },
            "🔴 시간이 해결하나": "아니다. 하루를 더 기다려도 **같은 열이 안 늘어난다** — "
                          "모자란 것은 관측 일수가 아니라 **다시 읽는 열**이다",
        },
        "나 · 🔴 그런데 901 이 T1 로 세지 **않은** 열 하나가 열려 있다": {
            "판정": "🔴 **연다**",
            "얼마나": "**404개 · 분모 406(영화 D3 유보) · 판 유보 3,775 기준 %s**"
                   % mv["판 유보 3,775 대비"],
            "어느 열": "`스크린수` · `상영횟수` — 일별 박스오피스 표의 열. "
                    "배급/상영 결정이고 **개체 안에서 날마다 바뀐다**",
            "처치 시점": "스냅숏 사이 변화로 **[t, t+1] 로 묶인다**. "
                     "라벨 창(개봉+20일) 안에서 변하는 개체 %d / 분모 %d"
                     % (mv["🔴 라벨 창 안의 처치 시점"]["창 안에 스크린수 변화가 1회 이상 있는 개체"],
                        mv["🔴 라벨 창 안의 처치 시점"]["분모(D3 · 2회+ 관측)"]),
            "🔴 왜 901 이 못 봤나": "901 의 영화 원천이 `axes_raw_897.jsonl`(영화당 **한 행**)이라 "
                            "일별 표의 열이 재고에 **한 번도 안 들어갔다**. "
                            "`inv901.py:76` 이 그 파일 하나만 가리킨다. "
                            "그래서 영화 T1 이 `개봉일`·`배급사` **둘뿐**이었다",
            "⚠ 남는 것": "W8(배정 기제)은 그대로다 — 누가 왜 스크린을 늘렸는지 기록이 없고, "
                     "스크린수는 직전 흥행에 반응하므로 **동시성**이 남는다. "
                     "🔴 **효과는 한 번도 안 쟀다**",
        },
        "다 · 다른 둘": {
            "유튜브 폴": "🔴 **안 연다** — 아이돌 T1 5열 중 0열을 담는다. "
                    "제목이 바뀐 영상 1(분모 255)은 실물이지만 **901 의 T1 이 아니다**. "
                    "게다가 D3 되짚기가 아이돌에서 **불가**(D2 81 ≠ D4 173) — 「없다」가 아니라 못 셌다",
            "팝업 방문자 일별": "🔴 **안 연다** — 스냅숏 시각이 **1가지**라 시점 사이 변화를 "
                        "정의할 자체가 없다. 로그 33회는 **찍은 횟수**이지 시점 수가 아니다. "
                        "게다가 담는 열이 전부 결과다. D3 유보 65 와의 교집합 **2**",
        },
        "라 · 티처 #64 M10 에 대한 답": "🔴 **「그 스냅숏이 W4 를 여는 기제다」는 절반만 맞다.** "
                            "기제는 있고(일별 표가 개체를 1,302일 다시 읽는다) 실제로 여는 열도 있다"
                            "(스크린수·상영횟수 · D3 404/406). 🔴 **그러나 901 이 W4 로 지목한 열들에 대해서는 "
                            "안 연다 — 그 열이 사는 저장소를 아무도 다시 안 읽는다.** "
                            "그리고 탐색 팔의 가격표(39~139개월)는 **틀리지 않았다**: "
                            "이 스냅숏은 그 가격을 깎지 않는다. 다만 **가격이 0인 팔이 하나 있었다** — "
                            "이미 받아 둔 158,494행이다",
    }

    out["🔴 ⑦ 못 한 것 · 확인 못 한 것 (전량)"] = {
        "효과 추정": "🔴 **안 했다**(887형 회피). 「무엇이 있나 · 무엇을 여나」까지다",
        "스크린수가 개입인가": "🔴 **판정 안 했다.** 901 의 사전등록 T1 정의를 이 열에 적용한 적이 없다 — "
                       "그건 902 본 사이클(#139 재측정)의 물음이지 지평의 물음이 아니다",
        "영화 개체 키": "🔴 제목 문자열이다. `movieCd` 가 일별 표에 없다 — 동명이인(재개봉)이 뭉친다. "
                  "표지로 「개봉일이 바뀐 개체 26(결측 제외) / 95(결측 포함)」를 남겼다",
        "아이돌 D3 교집합": "🔴 **못 셌다** — D2 81 ≠ D4 173. D1 282 기준 12/17 만 냈다",
        "유튜브 대상 신원": "🔴 **확인 안 했다.** `yt_poll_targets.json` 이 17 중 여럿을 "
                     "「불일치 의심 — 사람 확인 필수」로 적어 두었다(노트 834)",
        "collect.py 의 kobis 계수 결함": "🔴 **고치지 않았다** — `ingest/**` 는 내 파일이 아니다. 세어서 적었다",
        "눈으로 본 것": "🔴 유튜브 제목 변화 예시 **3건** · 팝업 방문자 행 **2건** · "
                  "영화 일별 행 **1건**. 나머지 수는 전부 전수 계산이다",
        "BQ/원천 재조회": "🔴 **안 했다**(읽기 전용 · 유료 API 금지 · 광역 크롤 금지). 저장소만 셌다",
        "빠진 6일(2026-08-02~07)": "🔴 **되메울 수 있는지 안 봤다.** KOBIS 는 소급 조회가 되는 원천이지만"
                            "(백필 둘이 증거다) 이번에 안 불렀다",
        "시군구 방문자 78파일 · 생활인구 zip 2": "🔴 **내용을 안 열었다.** 「매일 안 는다」만 mtime 으로 확인했다",
    }

    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["초"] = round((dt.datetime.fromisoformat(out["끝 시각"])
                      - dt.datetime.fromisoformat(st["시작 시각"])).total_seconds(), 1)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("썼다:", OUT, "· 초", out["초"])


if __name__ == "__main__":
    main()
