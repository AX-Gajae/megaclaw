# -*- coding: utf-8 -*-
"""노트 941(탐색) — 🔴 **새 자로 센다: (상태 s, 액션 a, 결과 o) 삼중쌍이 몇 개 나오나.**

**자가 바뀌었다**(`docs/방향.md` §1 · 2026-08-12 사용자 축자):
*「액션과 상태 그리고 결과값을 나타내는 학습쌍들을 정말 많이 수집 … 언어모델에 그냥 학습」*.
옛 자(**「판 유보 3,775 에 몇 행 붙나」**)는 **이 사이클의 자가 아니다** — 참고로만 병기한다.

이 러너가 하는 것 넷.

  **ㄱ** 저장소가 **이미** 가진 (s,a,o) 재고를 센다. 🔴 레코드 스키마가 이미
        `intervention`(a) · `conditions`(s) · `outcome`(o) 다 --- 아무도 이 이름으로 안 셌다.
  **ㄴ** **오늘 받은 것**(위키 일별 전 구간 · Steam 리뷰 본문)으로 삼중쌍을 **실제로 만든다**.
  **ㄷ** 🔴 **실물을 파일로 떨군다** --- `data/ingest/sao941/pairs.jsonl.gz`.
        「만들 수 있을 것 같다」는 성공이 아니다(조항 59).
  **ㄹ** **못 한 것**을 적는다.

🔴 **판정은 안 한다**(탐색 레인). 이 수는 다음 사이클의 **후보**일 뿐이다.

🔴 **분모를 섞지 않는다**(조항 60). 세 분모가 다르다:
  D_레코드 = 레코드 파일 · D_위키 = 위키 문서가 해결된 유보 개체 · D_스팀 = 게임 축 appid.
**서로 더하지 않는다.**
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

REC_DIRS = ("data/records", "data/market_records", "data/idol_records",
            "data/records_draft", "data/records_incomplete",
            "data/records_thinbak")
WIKI = ROOT / "data/ingest/wiki_daily"
STEAM = ROOT / "data/ingest/steam_reviews/reviews.jsonl.gz"
GREC = ROOT / "data/state/game_records.json"
OUTDIR = ROOT / "data/ingest/sao941"
OUT = ROOT / "runners/out941_sao.json"

WIN = 90            # 액션 앞뒤로 며칠을 s / o 로 쓰나
MIN_SIDE = 30       # 한쪽에 최소 며칠이 있어야 삼중쌍으로 세나


# ── ㄱ 저장소 재고 ────────────────────────────────────────────────────────
def stock() -> dict:
    n = 0
    sch = a_n = s_n = o_key = o_val = daily = full = 0
    for d in REC_DIRS:
        for f in sorted((ROOT / d).glob("*.json")):
            try:
                r = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            n += 1
            if {"intervention", "conditions", "outcome"} <= set(r):
                sch += 1
            a = bool(r.get("intervention"))
            s = bool(r.get("conditions"))
            o = r.get("outcome") or {}
            tot = o.get("totals") or {}
            ov = bool(o.get("daily")) or tot.get("visitors") is not None \
                or tot.get("sales_krw") is not None
            a_n += a
            s_n += s
            o_key += bool(o)
            o_val += ov
            daily += bool(o.get("daily"))
            full += bool(a and s and ov)
    return {
        "분모 D_레코드(파일)": n,
        "🔴 스키마가 이미 (a,s,o) 셋을 가진 파일": sch,
        "a(intervention) 값 있음": a_n,
        "s(conditions) 값 있음": s_n,
        "o(outcome) 키 있음": o_key,
        "🔴 o 에 **값**이 있음": o_val,
        "o.daily(일별 시계열)가 빈 것이 아님": daily,
        "🔴 a·s·o 셋 다 값이 있는 레코드": full,
        "🔴 그러므로 병목은 o 다": f"a {a_n} · s {s_n} · o {o_val} "
                              f"— o 가 a 의 {round(100*o_val/max(a_n,1),1)}%",
    }


def kobis_stock() -> dict:
    """🔴 **이미 저장소에 있는데 새 자로는 큰 것** --- KOBIS 일별 백필.

    `data/ingest/kobis/backfill_2023-01-01_full.json` 은 날짜마다 그날의 표를
    담는다. 각 행에 **제목 · 개봉일 · 그날의 관객수**가 있으므로
    **a(개봉 · 날짜 있음) + o(개봉 뒤 일별 관객 시계열)** 이 이미 서 있다.

    🔴 **옛 자로는 이 파일의 값이 0 이었다** --- `docs/수집계획.md` 후보 10 이
    KOBIS 되메우기의 Δ유보행을 **0** 으로 매겼다(*"유보 406/406 이 이미 붙는다.
    채우는 것은 값이 아니라 관측 밀도"*). **새 자로 다시 세면 다른 수가 나온다.**
    """
    p = ROOT / "data/ingest/kobis/backfill_2023-01-01_full.json"
    if not p.exists():
        return {"⛔": "backfill 파일 없다"}
    d = json.loads(p.read_text())
    obs: dict = {}
    rows = 0
    for day, rr in d.items():
        for r in rr:
            t, rd = r.get("제목"), r.get("개봉일")
            cells = r.get("숫자 셀(원본 순서)") or []
            if not t or len(cells) < 4:
                continue
            obs.setdefault((t, rd), []).append((day, cells[3]))
            rows += 1
    c = {"뒤 30일 이상": 0, "뒤 1~29일": 0, "뒤 0일": 0, "개봉일 없음": 0}
    for (_t, rd), v in obs.items():
        if not rd or len(rd) < 10:
            c["개봉일 없음"] += 1
            continue
        d0 = date(int(rd[:4]), int(rd[5:7]), int(rd[8:10]))
        post = [x for x in v
                if date(int(x[0][:4]), int(x[0][5:7]), int(x[0][8:10])) >= d0]
        if len(post) >= MIN_SIDE:
            c["뒤 30일 이상"] += 1
        elif post:
            c["뒤 1~29일"] += 1
        else:
            c["뒤 0일"] += 1
    return {
        "파일": str(p.relative_to(ROOT)), "바이트": p.stat().st_size,
        "날짜 수": len(d), "날짜 범위": [min(d), max(d)],
        "분모 D_KOBIS(제목,개봉일 개체)": len(obs),
        "관측 행(개체×날)": rows,
        "🔴 (a=개봉, o=뒤 30일 이상 일별 관객) 짝": c["뒤 30일 이상"],
        "덜 찬 것": c,
        "🔴 합 == 분모": sum(c.values()) == len(obs),
        "🔴 s 는 무엇인가": ("**비어 있다.** 개봉 전 상태를 이 파일은 안 담는다 --- "
                       "위키 앞창이나 예매율 같은 것을 따로 붙여야 한다. **이 사이클은 안 붙였다**"),
        "🔴 옛 자의 값": "docs/수집계획.md 후보 10 = Δ유보행 0 (순위 9위)",
    }


# ── ㄴ·ㄷ 오늘 받은 것으로 삼중쌍을 만든다 ───────────────────────────────
def _daystr(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def wiki_pairs(fp) -> dict:
    """위키 일별 계열 → 삼중쌍.

    a = 개체의 시작일(개봉·발매·개최) · s = [시작일−90, 시작일) 의 일별 조회수 ·
    o = [시작일, 시작일+90] 의 일별 조회수.

    🔴 **o 쪽이 이 저장소에 없던 것이다** — `ingest/wiki_views.py` 는 규약상
    *"시작일 당일과 이후는 한 칸도 안 본다"*.
    """
    tot = ok = no_start = short_pre = short_post = 0
    per: dict = {}
    made = 0
    for p in sorted(WIKI.glob("*.jsonl.gz")):
        dom = p.name.split(".")[0]
        c = per.setdefault(dom, {"개체": 0, "삼중쌍": 0, "시작일 없음": 0,
                                 "앞창 부족": 0, "뒤창 부족": 0})
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                tot += 1
                c["개체"] += 1
                st = r.get("시작일")
                if not st or len(st) < 10:
                    no_start += 1
                    c["시작일 없음"] += 1
                    continue
                d0 = date(int(st[:4]), int(st[5:7]), int(st[8:10]))
                # 🔴 **날짜를 읽어서 색인한다.** 첫날부터 하루씩 채우면 안 된다 ---
                # 원천이 자료 없는 날을 빠뜨리므로 계열이 밀린다(수집기 주석 참조).
                idx = {_daystr(str(d)): v
                       for d, v in zip(r["날짜"], r["조회수"])}
                pre = [(d0 - timedelta(days=k)) for k in range(WIN, 0, -1)]
                post = [(d0 + timedelta(days=k)) for k in range(0, WIN + 1)]
                sv = [idx[d] for d in pre if d in idx]
                ov = [idx[d] for d in post if d in idx]
                if len(sv) < MIN_SIDE:
                    short_pre += 1
                    c["앞창 부족"] += 1
                    continue
                if len(ov) < MIN_SIDE:
                    short_post += 1
                    c["뒤창 부족"] += 1
                    continue
                ok += 1
                c["삼중쌍"] += 1
                made += 1
                fp.write(json.dumps({
                    "쌍id": f"wiki:{r['키']}",
                    "출처": "wikimedia pageviews per-article (941 신규)",
                    "도메인": dom,
                    "a_액션": {"무엇": "개봉/발매/개최", "언제": st,
                             "개체": r["키"], "문서": r["문서"], "언어": r["언어"]},
                    "s_상태": {"무엇": f"액션 앞 {WIN}일 일별 위키 조회수",
                             "일수": len(sv), "값": sv},
                    "o_결과": {"무엇": f"액션 당일~뒤 {WIN}일 일별 위키 조회수",
                             "일수": len(ov), "값": ov},
                }, ensure_ascii=False) + "\n")
    return {
        "분모 D_위키(받은 개체)": tot,
        "🔴 삼중쌍": ok,
        "못 만든 사유": {"시작일 없음": no_start, "앞창 < 30일": short_pre,
                    "뒤창 < 30일": short_post},
        "🔴 합 == 분모": ok + no_start + short_pre + short_post == tot,
        "도메인별": per,
        "쓴 줄": made,
    }


def steam_pairs(fp) -> dict:
    """Steam 리뷰 본문 → 삼중쌍.

    a = 게임 출시(날짜 + 장르·가격·개발사) · s = 출시 **직전**에 알 수 있던 것
    (여기서는 위키 앞창이 있으면 그것, 없으면 **비어 있음**으로 적는다) ·
    o = 출시 뒤에 **사람이 쓴 말**(리뷰 본문 + 쓴 시각 + 추천 여부).

    🔴 **본문이다. 글자수·존재 이진이 아니다**(노트 896 이 잰 것은 그 대용값이었다).
    """
    if not STEAM.exists():
        return {"⛔": "reviews.jsonl.gz 없다"}
    gr = json.loads(GREC.read_text())
    # 위키 앞창(있으면 s 를 채운다)
    pre: dict = {}
    p = WIKI / "게임.jsonl.gz"
    if p.exists():
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                st = r.get("시작일")
                if not st or len(st) < 10:
                    continue
                d0 = date(int(st[:4]), int(st[5:7]), int(st[8:10]))
                idx = {_daystr(str(d)): v
                       for d, v in zip(r["날짜"], r["조회수"])}
                sv = [idx[d0 - timedelta(days=k)] for k in range(WIN, 0, -1)
                      if (d0 - timedelta(days=k)) in idx]
                if sv:
                    pre[r["키"]] = sv

    by: dict = {}
    n_rev = n_body = 0
    with gzip.open(STEAM, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            n_rev += 1
            if not r.get("본문"):
                continue
            n_body += 1
            by.setdefault(r["키"], []).append(r)

    ok = no_rel = no_rev = 0
    n_s_filled = 0
    after = 0
    for k, rows in sorted(by.items()):
        rec = gr.get(k)
        if not rec or not rec.get("release_date"):
            no_rel += 1
            continue
        rd = rec["release_date"]
        try:
            d0 = date(int(rd[:4]), int(rd[5:7]), int(rd[8:10]))
        except (ValueError, IndexError):
            no_rel += 1
            continue
        post = [r for r in rows
                if r["쓴 시각"] and date.fromtimestamp(r["쓴 시각"]) >= d0]
        if not post:
            no_rev += 1
            continue
        after += len(post)
        ok += 1
        s = pre.get(k)
        if s:
            n_s_filled += 1
        post = sorted(post, key=lambda r: r["쓴 시각"])
        fp.write(json.dumps({
            "쌍id": f"steam:{k}",
            "출처": "steam appreviews 본문 (941 신규)",
            "도메인": "게임",
            "a_액션": {"무엇": "게임 출시", "언제": rd, "개체": k,
                     "이름": rec.get("name"), "장르": rec.get("genres"),
                     "가격원": rec.get("price_krw"),
                     "개발사": rec.get("developers"),
                     "퍼블리셔": rec.get("publishers"),
                     "무료": rec.get("is_free")},
            "s_상태": ({"무엇": f"출시 앞 {WIN}일 일별 위키 조회수",
                      "일수": len(s), "값": s} if s else
                     {"무엇": "🔴 비어 있다 — 이 개체는 출시 전 상태를 못 받았다",
                      "일수": 0, "값": None}),
            "o_결과": {"무엇": "출시 뒤 사람이 쓴 리뷰 **본문**",
                     "건수": len(post),
                     "첫": time.strftime("%Y-%m-%d",
                                        time.gmtime(post[0]["쓴 시각"])),
                     "끝": time.strftime("%Y-%m-%d",
                                        time.gmtime(post[-1]["쓴 시각"])),
                     "본문": [{"때": time.strftime("%Y-%m-%d",
                                                time.gmtime(r["쓴 시각"])),
                             "추천": r["추천"], "언어": r["언어"],
                             "플레이분": r["플레이분"], "글": r["본문"]}
                            for r in post]},
        }, ensure_ascii=False) + "\n")
    return {
        "분모 D_스팀(리뷰가 온 앱)": len(by),
        "받은 리뷰 행": n_rev, "🔴 본문이 빈 것이 아닌 행": n_body,
        "🔴 삼중쌍(앱 단위)": ok,
        "그 삼중쌍이 담은 본문 건수(출시일 이후)": after,
        "그중 s 를 위키로 채운 것": n_s_filled,
        "🔴 s 가 빈 삼중쌍": ok - n_s_filled,
        "못 만든 사유": {"출시일 없음": no_rel, "출시일 이후 본문 0": no_rev},
        "🔴 합 == 분모": ok + no_rel + no_rev == len(by),
    }


def main() -> dict:
    t0 = time.time()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    pf = OUTDIR / "pairs.jsonl.gz"
    with gzip.open(pf, "wt", encoding="utf-8") as fp:
        w = wiki_pairs(fp)
        s = steam_pairs(fp)
    n_lines = 0
    with gzip.open(pf, "rt", encoding="utf-8") as f:
        for _ in f:
            n_lines += 1
    # 실물 한 건씩 뜬다 --- 산출물 안에 넣는다(조항 59)
    ex: dict = {}
    with gzip.open(pf, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            kind = r["쌍id"].split(":")[0]
            if kind in ex:
                continue
            e = json.loads(line)
            if kind == "steam":
                e["o_결과"]["본문"] = e["o_결과"]["본문"][:3]
                e["o_결과"]["🔴 여기 실은 것"] = "앞 3건만. 파일에는 전량"
            ex[kind] = e
            if len(ex) >= 2:
                break

    res = {
        "노트": 941, "레인": "탐색", "🔴 판정": "안 한다 — 다음 사이클의 후보다",
        "🔴 자": "(상태 s, 액션 a, 결과 o) 삼중쌍 수 (docs/방향.md §1 · 2026-08-12)",
        "🔴 안 쓴 자": "판 ρ · 「유보 3,775 에 붙는 행」 — 분모가 다르다(조항 60)",
        "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "초": round(time.time() - t0, 1),
        "ㄱ 저장소 재고(레코드)": stock(),
        "ㄱ2 저장소 재고(KOBIS 일별 — 🔴 옛 자로 0 점이던 것)": kobis_stock(),
        "ㄴ 위키 일별(941 신규)": w,
        "ㄷ Steam 리뷰 본문(941 신규)": s,
        "ㄹ 실물 파일": {"경로": str(pf.relative_to(ROOT)),
                    "줄 수": n_lines, "바이트": pf.stat().st_size,
                    "🔴 줄 수 == 위키 삼중쌍 + 스팀 삼중쌍":
                        n_lines == w.get("🔴 삼중쌍", 0) + s.get("🔴 삼중쌍(앱 단위)", 0)},
        "ㅁ 실물 예시": ex,
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "ㅁ 실물 예시"},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
