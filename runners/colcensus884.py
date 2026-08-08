# -*- coding: utf-8 -*-
# 노트 884 — 883 D 정정판(티처 #48 치명 1): 자에서 **레코드 writer(*_domain.py)** 를 뺀다.
# writer 는 records 를 만드는 코드라 필드 이름 인용이 항등식 → 883 의 "0" 은 자의 인공물이었다.
# 그리고 883 이 안 센 4 도메인(팝업·아이돌·영화·시장팝업)을 원천과 함께 넣는다.
# 원 노트 883 절 D — 미사용 열 인구조사(사전등록 '883' · T7 등록 규칙 · 규약 54)
# 원천 레코드의 필드 전수 대 **코드가 실제로 읽는 필드**를 맞춘다. 읽기만·적합 없음.
# 보수 방향: 필드 이름이 코드 어디에든 인용되면 '소비'로 센다(미사용을 과소 보고 —
# 과대 주장 금지). 상수·식별자·자유텍스트는 미사용에서 제외(축으로 못 쓴다).
import datetime as dt
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")

ROOT = Path("/Users/ax/world_model")
SRC = {  # 도메인 → 원천 레코드 파일 후보(실존만 쓴다)
    "만화": ["data/state/manga_records.json"],
    "웹툰": ["data/state/webtoon_records.json"],
    "애니": ["data/state/anime_records.json"],
    "세계애니": ["data/state/wanime_records.json"],
    "게임": ["data/state/game_records.json"],
    "도서": ["data/state/book_records.json"],
    "펀딩": ["data/state/funding_records.json"],
    "모바일": ["data/state/mobile_records.json"],
    "앱": ["data/state/app_records.json"],
    # 🔴 883 이 안 센 판 도메인 넷(티처 #48 중대 1) — 원천은 records 가 아니라 axes/meta 다
    "영화": ["data/state/kobis_axes.json"],
    "팝업": ["data/state/popup_meta.json"],
    "아이돌": ["data/state/idol_meta.json", "data/state/idol_album_meta.json"],
    "시장팝업": ["data/state/market.json"],
}
# 🔴 wfail1 교훈(구현 의심 먼저 9차): 전역 인용 검사는 판별력이 0 이었다(원천 필드 이름은
# 아무 파일에서나 인용된다 — 전 도메인 미사용 0). 자를 **그 도메인의 빌더**로 좁힌다.
DOM_CODE = {
    "만화": ["ingest/manga_axes.py", "ingest/manga_push.py"],
    "웹툰": ["ingest/webtoon_axes.py", "ingest/webtoon_more.py"],
    "애니": ["ingest/anime_axes.py", "ingest/anime_more.py"],
    "세계애니": ["ingest/wanime_axes.py"],
    "게임": ["ingest/game_axes.py", "ingest/game_friction.py", "ingest/game_recent.py"],
    "도서": ["ingest/book_axes.py"],
    "펀딩": ["ingest/funding_axes.py", "ingest/funding_creators.py"],
    "모바일": ["ingest/mobile_axes.py"],
    "앱": [],
    "영화": ["ingest/kobis.py"], "팝업": ["ingest/popup_wiki.py"], "아이돌": [], "시장팝업": [],
}
# 🔴 wfail2 교훈(구현 의심 먼저 10차): 축은 ingest 빌더만 만들지 않는다 — lab/tagaxes·
# genaxes·rawaxes 계열이 원천 레코드에서 직접 캔다(노트 324·344). wfail2 는 세계애니
# genres/n_genre/studio 를 '미사용'이라 불렀는데 provenance.py 에 tag_c2/c3_세계애니
# ('등록 시점 장르')·wa_ngenre·wa_studio 로 **이미 등재**돼 있었다. 자 범위에 lab 을 넣는다.
SHARED_CODE = ["state/tri_domain.py", "ingest/derive_features.py", "ingest/calendar_features.py",
               "ingest/attr_tagger.py", "ingest/bulk_normalize.py", "lab/provenance.py"] + \
              [f"lab/{n}" for n in ("tagaxes.py", "genaxes.py", "rawaxes.py", "animeaxes.py",
                                    "langaxes.py", "autotag.py", "fixaxes.py", "forms.py")]
ID_PAT = re.compile(r"(^|_)(id|url|uri|link|slug|code|key|hash|path|src|thumb|image|img)($|_)", re.I)


def flatten_keys(rec, prefix="", out=None, depth=0):
    if out is None:
        out = {}
    if isinstance(rec, dict) and depth <= 1:
        for k, v in rec.items():
            name = f"{prefix}{k}"
            if isinstance(v, dict) and depth == 0:
                flatten_keys(v, f"{name}.", out, depth + 1)
            else:
                out.setdefault(name, []).append(v)
    return out


def code_text(paths):
    txt = []
    for p in paths:
        f = ROOT / p
        if f.exists():
            txt.append(f.read_text(errors="ignore"))
    return "\n".join(txt)


def main():
    board_names = {}
    try:
        from lab import sideaudit
        d = sideaudit.champion_data()
        board_names = {k: list(v) for k, v in d.names.items()}
    except Exception as e:
        board_names = {"⛔": type(e).__name__}

    doms = {}
    for dom, paths in SRC.items():
        CODE = code_text(DOM_CODE.get(dom, []) + SHARED_CODE)
        files = [p for p in paths if (ROOT / p).exists()]
        if not files:
            doms[dom] = {"원천 없음": paths}
            continue
        vals = {}
        n_rows = 0
        for p in files:
            raw = json.loads((ROOT / p).read_text())
            recs = list(raw.values()) if isinstance(raw, dict) else raw
            n_rows += len(recs)
            for r in recs:
                if isinstance(r, dict):
                    for k, vv in flatten_keys(r).items():
                        vals.setdefault(k, []).extend(vv)
        rows = []
        for f, vs in vals.items():
            nonnull = [v for v in vs if v not in (None, "", [], {})]
            fill = len(nonnull) / max(n_rows, 1)
            try:
                nuniq = len({json.dumps(v, ensure_ascii=False, sort_keys=True) for v in nonnull})
            except Exception:
                nuniq = len({str(v) for v in nonnull})
            avglen = (sum(len(str(v)) for v in nonnull[:400]) / max(min(len(nonnull), 400), 1))
            # 코드가 이 필드 이름을 인용하나(보수적 — 부분 이름도 인용으로 센다)
            leaf = f.split(".")[-1]
            cited = bool(re.search(rf'["\']{re.escape(leaf)}["\']', CODE))
            rows.append({"필드": f, "채움": round(fill, 4), "값 가짓수": nuniq,
                         "평균 길이": round(avglen, 1), "코드 인용": cited,
                         "표본": [str(v)[:40] for v in nonnull[:3]]})
        excl, unused = [], []
        for r in rows:
            if r["코드 인용"]:
                continue
            if r["값 가짓수"] <= 1:
                excl.append({**r, "제외": "상수(값 가짓수 ≤1)"}); continue
            if ID_PAT.search(r["필드"].split(".")[-1]):
                excl.append({**r, "제외": "식별자류"}); continue
            if r["평균 길이"] > 80:
                excl.append({**r, "제외": "자유 텍스트(평균 길이 >80)"}); continue
            if r["채움"] < 0.30:
                excl.append({**r, "제외": "채움 <0.30"}); continue
            unused.append(r)
        unused.sort(key=lambda r: -r["채움"])
        doms[dom] = {
            "원천": files, "행": n_rows, "필드 수": len(rows),
            "빌더 인용됨": sum(1 for r in rows if r["코드 인용"]),
            "자 범위 파일": [p for p in DOM_CODE.get(dom, []) if (ROOT / p).exists()],
            "미사용 후보(제외 후)": len(unused),
            "미사용 후보": unused[:40],
            "제외 요약": dict(Counter(e["제외"] for e in excl)),
            "판 특징 수": len(board_names.get(dom, [])),
        }

    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "자 범위(writer 제외)": {d: DOM_CODE.get(d, []) + SHARED_CODE for d in SRC},
        "883 대비": "자에서 *_domain.py(레코드 writer) 제거 + 미계수 4 도메인 추가. 883 의 0 은 인용 항등식의 인공물",
        "눈금": "미사용 = 원천 필드 중 **그 도메인의 빌더+공유 조립 코드**에 이름이 인용되지 않고, 상수·식별자·자유텍스트·채움<0.30 이 아닌 것(사전등록 883 D · 보수 방향)",
        "한계": "① 이름 인용 검사는 여전히 보수적이라 미사용을 **과소** 보고한다(별칭 소비를 소비로 셈) — wfail1(전역 자)에서는 판별력이 0 이었다 ② 시간 게이트는 이 러너가 판정하지 않는다 — 후속 눈/적대 검증 몫",
        "도메인": doms,
        "판 특징 이름(참고)": board_names,
    }
    with open(ROOT / "runners/out884_colcensus_fix.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    slim = {k: v for k, v in out.items() if k not in ("도메인", "판 특징 이름(참고)")}
    slim["요약"] = {dom: {kk: v.get(kk) for kk in ("행", "필드 수", "빌더 인용됨", "미사용 후보(제외 후)")}
                  for dom, v in doms.items()}
    print(json.dumps(slim, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
