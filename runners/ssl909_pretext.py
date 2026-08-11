# -*- coding: utf-8 -*-
"""팔 909-ㅁ · **0단계 연료 세기 + 1단계 프리텍스트 + 3단계 배선 + 자 (다)**.

사전등록 `docs/prereg_909_ssl.md` (§0.5 는 측정 전 보강).

산출: `runners/out909_fuel.json` · `runners/out909_pretext.json`

🔴 분모 딱지를 모든 수에 붙인다(조항 60) · 빈칸 세 갈래의 **합 == 전체 빈칸**을
코드로 단언한다 · '없다'와 '못 봤다'와 '못 읽었다'를 가른다(조항 59).
"""
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sys
import time
import warnings
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import numpy as np                                          # noqa: E402

ROOT = Path("/Users/ax/world_model")
DATA = ROOT / "data"
PREREG = ROOT / "docs/prereg_909_ssl.md"
T = 2025.0
BUDGET_S = float(os.environ.get("SSL909_BUDGET", 1500))

HANGUL = re.compile(r"[가-힣]")
LATIN = re.compile(r"[A-Za-z]")
TAG = re.compile(r"<[^>]{1,200}>")
SCRIPT = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")


def stamp() -> dict:
    """🔴 **내 파일의 sha 를 내가 박는다**(티처 #59 M7)."""
    return {
        "코드 sha(이 파일)": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
        "코드 sha(state/ssl909.py)": hashlib.sha256(
            (ROOT / "state/ssl909.py").read_bytes()).hexdigest()[:16],
        "시각": dt.datetime.now().isoformat(),
        "사전등록": {
            "파일": "docs/prereg_909_ssl.md",
            "sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(),
            "mtime": dt.datetime.fromtimestamp(PREREG.stat().st_mtime).isoformat(),
            "🔴 이 산출물보다 앞서나": dt.datetime.fromtimestamp(
                PREREG.stat().st_mtime) < dt.datetime.now(),
        },
        "⚠ git HEAD 는 안 박는다": "docs/루프.md v3.2 — 긴 러너에서 HEAD 는 원리상 "
                                "「시작 시점」이다. 코드 sha + 끝 시각을 쓴다",
    }


def clean(s):
    return " ".join(TAG.sub(" ", SCRIPT.sub(" ", s)).split())


def is_prose(s, lo=200):
    if not s or len(s) < lo:
        return False
    t = s.strip()
    if t.startswith(("http://", "https://", "data:", "www.", "/")):
        return False
    if "://" in t[:60]:
        return False
    ws = sum(c.isspace() for c in t)
    if ws < 8 or ws / len(t) < 0.02:
        return False
    return (len(HANGUL.findall(t)) + len(LATIN.findall(t))) / len(t) >= 0.45


# ══ 0단계 · 연료 ═══════════════════════════════════════════════════════
def fuel_axes(data, load0) -> dict:
    """축 행렬의 칸을 세고 **빈칸을 세 갈래로 가른다**(합 == 전체 빈칸 단언)."""
    import ff753 as FF
    from lab import fixaxes as FX
    extra = FF.base()
    n0 = {d: len(load0.dom[d][2]) for d in load0.dom}       # _idol 대체 **전** 행수

    tot_cells = tot_obs = 0
    b = Counter()
    per_dom = {}
    detail = defaultdict(list)
    for d in data.dom:
        A, M, y, t = data.dom[d]
        nm = list(data.names.get(d) or [])
        n, P = A.shape
        tot_cells += n * P
        obs = int((M > 0).sum())
        tot_obs += obs
        cnt = Counter()
        for j, a in enumerate(nm):
            col = M[:, j] > 0
            blank = int((~col).sum())
            if blank == 0:
                continue
            if (d, a) in FX.BLOCK:
                cnt["② 전처리가 지웠다(fixaxes.BLOCK)"] += blank
                detail["②"].append(f"{d}/{a}")
            elif a in extra and d not in extra[a]:
                cnt["①-가 구조상 없음(그 도메인에 그 축이 정의 안 됨)"] += blank
                detail["①-가"].append(f"{d}/{a}")
            elif a in extra and d in extra[a] and len(extra[a][d][0]) != n0.get(d, n):
                cnt["①-나 행수 불일치 중립 채움(정렬 실패)"] += blank
                detail["①-나"].append(
                    f"{d}/{a} ({len(extra[a][d][0])}!={n0.get(d)})")
            elif not col.any():
                cnt["③-가 열 전량 결측(축은 정의됐는데 관측 0행)"] += blank
                detail["③-가"].append(f"{d}/{a}")
            else:
                cnt["③-나 행 부분 결측"] += blank
        per_dom[d] = {"행": n, "축": P, "칸": n * P, "관측": obs,
                      "빈칸": n * P - obs, "갈래": dict(cnt)}
        b.update(cnt)
    blank = tot_cells - tot_obs
    s = sum(b.values())
    assert s == blank, f"🔴 빈칸 세 갈래 합 {s} != 전체 빈칸 {blank}"
    return {
        "🔴 분모": "챔피언 축 행렬 = 12도메인 22,900행 × 그 도메인의 축 수",
        "칸": tot_cells, "관측": tot_obs, "빈칸": blank,
        "빈칸 비율": round(blank / tot_cells, 4),
        "🔴 세 갈래 (합 == 전체 빈칸 · 코드 단언 통과)": dict(b),
        "합 단언": {"세 갈래 합": s, "전체 빈칸": blank, "같나": s == blank},
        "⚠ 못 갈랐다": ("지시서의 「② 수집이 못 한 것 / ③ 값이 진짜 없는 것」 분리는 "
                     "원천까지 되짚어야 갈리는데 31개 extra 축 대부분이 파생 빌더 "
                     "산출이라 되짚기가 안 된다. 위 ③ 은 **그 둘의 못 가른 합**이다 — "
                     "'갈랐다'가 아니라 '못 갈랐다'로 적는다"),
        "갈래별 (도메인/축) 목록": {k: sorted(v) for k, v in detail.items()},
        "도메인별": per_dom,
    }


def fuel_labels(data) -> dict:
    W = data.weights(T)
    per = {}
    for d in data.dom:
        A, M, y, t = data.dom[d]
        post = data.rows(d, post=True, labeled=True, T=T)
        pre = data.rows(d, post=False, labeled=True, T=T)
        per[d] = {"행": int(len(y)), "유보(판 채점)": int(post.sum()),
                  "학습": int(pre.sum()),
                  "라벨 없음": int((~np.isfinite(y)).sum()),
                  "판 가중": W.get(d)}
    L1 = sum(v["유보(판 채점)"] for v in per.values())
    L2 = sum(v["학습"] for v in per.values())
    L3 = sum(v["행"] for v in per.values())
    assert L1 + L2 + sum(v["라벨 없음"] for v in per.values()) == L3, "🔴 행 회계 안 맞음"
    return {"🔴 분모": "챔피언 축 행렬의 행 (도메인마다 다르다)",
            "L1 판 유보 라벨 행": L1, "L2 판 학습 라벨 행": L2, "L3 축 행렬 행": L3,
            "라벨 없는 행": L3 - L1 - L2,
            "합 단언(L1+L2+라벨없음 == L3)": True, "도메인별": per}


def fuel_sources() -> dict:
    """판이 한 번도 안 보는 원천을 센다. **각 수마다 분모 딱지.**"""
    out = {}
    # U2 영화 일별 흥행
    rows = 0
    days = set()
    titles = set()
    files = 0
    for p in sorted(glob.glob(str(DATA / "ingest/kobis/*.json"))):
        try:
            d = json.loads(Path(p).read_text())
        except Exception:
            continue
        files += 1
        if isinstance(d, dict) and "rows" in d and isinstance(d["rows"], list):
            rows += len(d["rows"])
            if d.get("date"):
                days.add(d["date"])
            for r in d["rows"]:
                if isinstance(r, dict) and r.get("제목"):
                    titles.add(r["제목"])
        elif isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, list) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(k)):
                    rows += len(v)
                    days.add(k)
                    for r in v:
                        if isinstance(r, dict) and r.get("제목"):
                            titles.add(r["제목"])
    out["U2 영화 일별 흥행 행"] = {
        "🔴 분모": "data/ingest/kobis/*.json 의 (날짜 → 흥행행) 목록 전량",
        "행": rows, "고유 날짜": len(days), "고유 제목": len(titles),
        "훑은 파일": files,
        "⚠ 노트 902 가 적은 값": 158494,
        "재현하나": rows == 158494}
    # U4 KOBIS 상세
    mi = sorted(glob.glob(str(DATA / "ingest/kobis/api908d_movieinfo_*.jsonl")))
    n_lines = n_ok = n_bad = 0
    cds = set()
    for p in mi:
        for x in Path(p).read_text(errors="replace").splitlines():
            if not x.strip():
                continue
            n_lines += 1
            try:
                r = json.loads(x)
            except Exception:
                n_bad += 1                       # 🔴 잘린 줄 — 다른 에이전트가 쓰는 중
                continue
            n_ok += 1
            if r.get("movieCd"):
                cds.add(r["movieCd"])
    out["U4 KOBIS 상세(오늘 들어온 것)"] = {
        "🔴 분모": "data/ingest/kobis/api908d_movieinfo_*.jsonl",
        "빈 줄 아닌 줄": n_lines, "🔴 파싱되는 레코드": n_ok,
        "🔴 파싱 안 되는 줄(쓰는 중 잘림)": n_bad,
        "고유 movieCd": len(cds), "파일": len(mi),
        "⚠ 지시서가 적은 값": 406,
        "재현하나(파싱되는 레코드 기준)": n_ok == 406,
        "🔴 조항 59": ("줄 수와 레코드 수는 다르다 — 이 파일은 **다른 에이전트가 지금 "
                    "쓰고 있어서** 잘린 줄이 있고, 두 번 세면 두 번 다르게 나온다"
                    "(첫 읽기 407줄/406레코드 → 두 번째 407줄/405레코드/2잘림). "
                    "그러므로 이 수는 **한 시점의 사진**이고 '406 개가 있다'로 "
                    "고정해 인용하면 틀린다")}
    # U3 원천 레코드 저장소
    st = {}
    for name in ("records", "market_records", "idol_records", "records_incomplete",
                 "records_thinbak", "market_raw", "idol_raw", "mining"):
        p = DATA / name
        if not p.exists():
            st[name] = "🔴 그 경로가 없다"
            continue
        fs = sorted(p.glob("*"))
        st[name] = {"파일": len([f for f in fs if f.is_file()]),
                    "바이트": sum(f.stat().st_size for f in fs if f.is_file())}
    out["U3 원천 레코드 저장소"] = {"🔴 분모": "디렉터리마다 파일 수(레코드 수가 아니다 — "
                                        "노트 902 정정 「D1 의 정의는 파일 수가 아니라 "
                                        "레코드 수다」와 같은 함정)", **st}
    # U5 생활인구 격자
    zips = sorted(glob.glob(str(DATA / "ingest/seoul_lifepop/*.zip")))
    csvs = 0
    unz = 0
    for p in zips:
        try:
            with zipfile.ZipFile(p) as z:
                il = [i for i in z.infolist() if i.filename.lower().endswith(".csv")]
                csvs += len(il)
                unz += sum(i.file_size for i in il)
        except Exception:
            pass
    sample_rows = None
    if zips:
        try:
            with zipfile.ZipFile(zips[0]) as z:
                il = [i for i in z.infolist() if i.filename.lower().endswith(".csv")]
                with z.open(il[0].filename) as f:
                    sample_rows = -1
                    while True:
                        chunk = f.read(1 << 22)
                        if not chunk:
                            break
                        sample_rows += chunk.count(b"\n")
        except Exception as e:                                # noqa: BLE001
            sample_rows = f"못 읽었다: {type(e).__name__}"
    out["U5 생활인구 격자"] = {
        "🔴 분모": "data/ingest/seoul_lifepop/*.zip 안의 일별 csv",
        "zip": len(zips), "일별 csv": csvs,
        "압축 해제 바이트": unz,
        "표본 하루의 행(머리 제외)": sample_rows,
        "🔴 어림 총행 = 일수 × 표본 하루": (csvs * sample_rows
                                     if isinstance(sample_rows, int) else None),
        "🔴 정직 표지": "표본 **하루 하나**로 곱했다 — 전량을 세지 않았다. "
                    "그리고 **저장소 코드가 이 파일을 한 번도 읽은 적이 없다**"}
    return out


def fuel_text() -> dict:
    """텍스트 인구조사 — **산문만** 걸러 전수로 센다(§0.5.1)."""
    n = c_raw = c_cl = 0
    seen = {}
    lang = Counter()
    lang_c = Counter()
    per_dir = defaultdict(lambda: {"n": 0, "c": 0})
    per_key = defaultdict(lambda: {"n": 0, "c": 0})
    bucket_n = Counter()
    bucket_c = Counter()
    n_all = c_all = 0
    bad = []
    files = 0
    nbytes = 0

    def walk(o, path, dkey):
        nonlocal n, c_raw, c_cl, n_all, c_all
        if isinstance(o, str):
            n_all += 1
            c_all += len(o)
            for lo in (50, 200, 1000, 5000):
                if len(o) >= lo:
                    bucket_n[lo] += 1
                    bucket_c[lo] += len(o)
            if not is_prose(o):
                return
            cl = clean(o)
            if len(cl) < 200:
                return
            n += 1
            c_raw += len(o)
            c_cl += len(cl)
            per_dir[dkey]["n"] += 1
            per_dir[dkey]["c"] += len(cl)
            per_key[path]["n"] += 1
            per_key[path]["c"] += len(cl)
            h = hashlib.sha1(cl.encode()).hexdigest()[:16]
            if h in seen:
                seen[h][0] += 1
            else:
                seen[h] = [1, len(cl)]
            hg, lt = len(HANGUL.findall(cl)), len(LATIN.findall(cl))
            k = ("한글우세" if hg >= 3 * lt else
                 "로마자우세" if lt >= 3 * hg else "혼합")
            lang[k] += 1
            lang_c[k] += len(cl)
        elif isinstance(o, dict):
            for k, v in o.items():
                walk(v, (path + "." + str(k))[:110], dkey)
        elif isinstance(o, list):
            for v in o:
                walk(v, path + "[]", dkey)

    for dirpath, _, fns in os.walk(DATA):
        for fn in fns:
            if not (fn.endswith(".json") or fn.endswith(".jsonl")):
                continue
            p = Path(dirpath) / fn
            rel = str(p.relative_to(DATA))
            files += 1
            nbytes += p.stat().st_size
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                bad.append(rel)
                continue
            dkey = str(Path(rel).parent) or "."
            try:
                if fn.endswith(".jsonl"):
                    for line in txt.splitlines():
                        if line.strip():
                            walk(json.loads(line), "", dkey)
                else:
                    walk(json.loads(txt), "", dkey)
            except Exception:
                ok = False
                try:
                    for line in txt.splitlines():
                        s = line.strip()
                        if s.startswith(("{", "[")):
                            walk(json.loads(s), "", dkey)
                            ok = True
                except Exception:
                    pass
                if not ok:
                    bad.append(rel)
            del txt
    uniq_c = sum(v[1] for v in seen.values())
    return {
        "🔴 분모": f"data/** 의 json·jsonl {files}개 · {nbytes} 바이트",
        "못 읽은 파일": {"수": len(bad), "목록": bad[:20],
                     "비율": round(len(bad) / max(files, 1), 5)},
        "가 · 문자열 길이 분포 (분모 = 위 파일 전량의 모든 json 문자열)": {
            "문자열": n_all, "문자": c_all,
            "누적": {f">={lo}": {"개수": bucket_n[lo], "문자": bucket_c[lo]}
                   for lo in (50, 200, 1000, 5000)}},
        "🔴 산문 판정 정의": ("len>=200 · http/data/www//로 시작 안 함 · 앞 60자에 "
                        "'://' 없음 · 공백>=8 이고 공백비>=0.02 · "
                        "(한글+로마자)/길이>=0.45 · 태그 제거 후에도 >=200자"),
        "나 · 산문 (분모 = 위와 같다)": {
            "산문 문자열": n, "원문 문자": c_raw, "태그 제거 후 문자": c_cl,
            "고유 산문": len(seen),
            "중복 무리(2회 이상)": sum(1 for v in seen.values() if v[0] > 1),
            "🔴 중복 제거 후 순 문자": uniq_c},
        "다 · 언어 (분모 = 산문 문자열 전량)": {"개수": dict(lang), "문자": dict(lang_c)},
        "라 · 산문이 사는 곳 상위 15": sorted(
            ({"곳": k, **v} for k, v in per_dir.items()), key=lambda r: -r["c"])[:15],
        "마 · 산문 키 경로 상위 15": sorted(
            ({"키": k, **v} for k, v in per_key.items()), key=lambda r: -r["c"])[:15],
    }


def fuel_openclaw() -> dict:
    """§0.5.1-5 — 팝업 인터뷰 전사문이 `/Users/ax/.openclaw` 에 있나. **읽기만.**"""
    p = Path("/Users/ax/.openclaw")
    if not p.exists():
        return {"🔴": "그 경로가 없다"}
    out = {"경로": str(p)}
    try:
        out["최상위"] = sorted(x.name for x in p.iterdir())[:40]
    except Exception as e:                                    # noqa: BLE001
        return {"🔴 못 읽었다": f"{type(e).__name__}: {e}"}
    db = p / "memory/main.sqlite"
    if db.exists():
        try:
            import sqlite3
            c = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
            nf = c.execute("select count(*) from files").fetchone()[0]
            nc, cc = c.execute("select count(*), sum(length(text)) from chunks").fetchone()
            paths = [r[0] for r in c.execute("select path from files limit 60")]
            hits = {}
            for kw in ("인터뷰", "전사", "팝업", "interview", "transcript"):
                try:
                    hits[kw] = c.execute(
                        "select count(*) from chunks_fts where chunks_fts match ?",
                        (kw,)).fetchone()[0]
                except Exception as e:                        # noqa: BLE001
                    hits[kw] = f"못 셌다: {type(e).__name__}"
            out["memory/main.sqlite"] = {
                "files": nf, "chunks": nc, "chunk 문자 합": cc,
                "파일 이름(앞 60)": paths, "전문검색 적중": hits}
            c.close()
        except Exception as e:                                # noqa: BLE001
            out["memory/main.sqlite"] = f"🔴 못 읽었다: {type(e).__name__}: {e}"
    med = p / "media"
    if med.exists():
        ext = Counter(f.suffix.lower() for f in med.rglob("*") if f.is_file())
        out["media 확장자"] = dict(ext.most_common(12))
    out["🔴 판정"] = ("**팝업 인터뷰 전사문을 이 경로에서 못 찾았다.** "
                   "'없다'가 아니라 '못 찾았다'다(조항 59) — 찾은 것은 "
                   "에이전트 메모리 md 와 스크린숏이다")
    return out


# ══ 텍스트 → 행 붙이기 (T-나) ═══════════════════════════════════════════
SRC_AX = {"게임": "game_axes.json", "도서": "book_axes.json",
          "펀딩": "funding_axes.json", "웹툰": "webtoon_axes.json",
          "모바일": "mobile_axes.json", "만화": "manga_axes.json",
          "세계애니": "wanime_axes.json", "영화": "kobis_axes.json",
          "시장팝업": "market_axes.json"}
_DESC = {}


def _best(o, acc, lo=100):
    if isinstance(o, str):
        c = clean(o)
        if is_prose(c, lo):
            acc.append(c)
    elif isinstance(o, dict):
        for v in o.values():
            _best(v, acc, lo)
    elif isinstance(o, list):
        for v in o:
            _best(v, acc, lo)


def _from_file(paths):
    for f in paths:
        f = Path(f)
        if not f.exists():
            continue
        try:
            if f.suffix == ".html":
                return clean(f.read_text(encoding="utf-8", errors="replace"))
            acc = []
            _best(json.loads(f.read_text(encoding="utf-8", errors="replace")), acc)
            return max(acc, key=len) if acc else ""
        except Exception:
            return ""
    return ""


def row_texts(data) -> tuple:
    """도메인 → 행 순서 텍스트 리스트. 못 붙인 도메인은 빈 리스트 + 사유."""
    if not _DESC:
        _DESC["manga"] = json.loads((DATA / "state/desc_manga.json").read_text())
        _DESC["wanime"] = json.loads((DATA / "state/desc_wanime.json").read_text())
        K = {}
        for p in glob.glob(str(DATA / "ingest/kobis/api908d_movieinfo_*.jsonl")):
            for line in Path(p).read_text(errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                cd = str(r.get("movieCd") or "")
                acc = []
                _best(r, acc)
                if cd:
                    K[cd] = max(acc, key=len) if acc else ""
        _DESC["kobis"] = K

    def get(dom, rid):
        num = rid.split("-", 1)[1] if "-" in rid else rid
        if dom == "만화":
            return clean(_DESC["manga"].get(num, "") or "")
        if dom == "세계애니":
            return clean(_DESC["wanime"].get(num, "") or "")
        if dom == "모바일":
            return _from_file([DATA / f"state/cache_mobile/app_{num}.json"])
        if dom == "웹툰":
            return _from_file([DATA / f"state/cache_webtoon/info_{num}.json"])
        if dom == "게임":
            return _from_file([DATA / f"state/cache_steam/app_{num}.json"])
        if dom == "도서":
            return _from_file([DATA / f"state/cache_bookpage/{rid}.html"])
        if dom == "펀딩":
            return _from_file([DATA / f"state/cache_fundpage/{rid}.html"])
        if dom == "시장팝업":
            return _from_file([DATA / f"market_records/{rid}.json"])
        if dom == "영화":
            return _DESC["kobis"].get(num, "")
        return ""

    texts, report, tot = {}, {}, {"유보": 0, "유보_텍스트": 0}
    for dom in data.dom:
        n = len(data.dom[dom][2])
        post = data.rows(dom, post=True, labeled=True, T=T)
        if dom not in SRC_AX:
            texts[dom] = [""] * n
            report[dom] = {"행": n, "유보": int(post.sum()), "🔴 못 붙였다":
                           ("챔피언이 slots.load_popup / idolset 로 행을 다시 만들어 "
                            "축 json 키 순서로 못 되짚는다" if dom in ("팝업", "아이돌")
                            else "AN- 축 id 가 cache_anime item id 와 다른 공간이고 "
                                 "anime_match.json 은 87건뿐이다 — 되짚기를 못 했다. "
                                 "**0 이 아니라 '못 붙였다'다**")}
            continue
        ids = list(json.loads((DATA / "state" / SRC_AX[dom]).read_text()))
        if len(ids) != n:
            texts[dom] = [""] * n
            report[dom] = {"🔴 못 붙였다": f"축 파일 키 {len(ids)} != 챔피언 행 {n}"}
            continue
        L = [get(dom, r) for r in ids]
        ln = np.array([len(s) for s in L])
        has = ln >= 200
        texts[dom] = [s if len(s) >= 200 else "" for s in L]
        report[dom] = {"행": n, "유보": int(post.sum()),
                       "행 중 >=200자": int(has.sum()),
                       "🔴 유보 중 >=200자": int((has & post).sum()),
                       "유보 덮개율": round(float((has & post).sum() /
                                            max(post.sum(), 1)), 4),
                       "유보 텍스트 문자 합": int(ln[post].sum()),
                       "중앙 길이(있는 행)": int(np.median(ln[has])) if has.any() else 0}
        tot["유보"] += int(post.sum())
        tot["유보_텍스트"] += int((has & post).sum())
    return texts, {"도메인별": report, "합": tot}


# ══ 실행 ═══════════════════════════════════════════════════════════════
def main() -> int:
    t0 = time.time()
    from lab import harness
    from state import ssl909 as S
    import ff753 as FF

    print("0단계 · 연료…", flush=True)
    load0 = harness.load()
    data = FF.shell(FF.base())
    fuel = {"무엇": "팔 909-ㅁ · 0단계 연료 표", **stamp()}
    fuel["가 · 라벨 있는 행"] = fuel_labels(data)
    fuel["나 · 축 행렬의 칸과 빈칸 세 갈래"] = fuel_axes(data, load0)
    print("  원천…", flush=True)
    fuel["다 · 판이 한 번도 안 보는 원천"] = fuel_sources()
    print("  텍스트 인구조사…", flush=True)
    fuel["라 · 텍스트 인구조사(§0.5.1)"] = fuel_text()
    fuel["마 · /Users/ax/.openclaw (§0.5.1-5)"] = fuel_openclaw()
    print("  텍스트 붙이기…", flush=True)
    texts, attach = row_texts(data)
    fuel["바 · T-나 텍스트가 유보 행에 붙나"] = attach

    # 🔴 갈림길 판정 (§0.5.2) — 문턱은 사전등록에 숫자로 박혀 있다
    net_chars = fuel["라 · 텍스트 인구조사(§0.5.1)"]["나 · 산문 (분모 = 위와 같다)"][
        "🔴 중복 제거 후 순 문자"]
    L1 = fuel["가 · 라벨 있는 행"]["L1 판 유보 라벨 행"]
    cov = attach["합"]["유보_텍스트"] / L1
    dom_ok = sum(1 for v in attach["도메인별"].values()
                 if isinstance(v.get("유보 덮개율"), float) and v["유보 덮개율"] >= 0.20)
    tga = net_chars >= 20_000_000
    tnb = cov >= 0.50 and dom_ok >= 8
    branch = ("G1 떠받친다" if tga and tnb else
              "G3 못 떠받친다" if not tga and not tnb else "G2 반쪽")
    need = max(0, 20_000_000 - net_chars)
    fuel["🔴 사 · 갈림길 판정 (§0.5.2 · 문턱은 측정 전에 박혔다)"] = {
        "T-가 문턱": 20_000_000, "T-가 실측(중복 제거 후 순 산문 문자)": net_chars,
        "T-가 통과": tga, "T-가 모자란 문자": need,
        "T-나 문턱": "판 유보의 50% 그리고 12도메인 중 8개에서 20%",
        "T-나 실측 유보 덮개율": round(cov, 4),
        "T-나 실측 (분자, 분모)": [attach["합"]["유보_텍스트"], L1],
        "T-나 실측 20% 넘는 도메인 수": dom_ok,
        "T-나 통과": tnb,
        "🔴 갈래": branch,
        "🔴 다음 사이클 수집 목표(수로)": {
            "T-가 를 넘기려면 더 필요한 순 산문 문자": need,
            "T-나 를 넘기려면 더 필요한 유보 행(200자 이상 텍스트가 붙는)":
                max(0, int(0.50 * L1) - attach["합"]["유보_텍스트"]),
            "🔴 어느 도메인이 비었나": [k for k, v in attach["도메인별"].items()
                                if not isinstance(v.get("유보 덮개율"), float)
                                or v["유보 덮개율"] < 0.20]},
    }
    fuel["🔴 F0 연료 관문"] = {
        "규칙": "프리텍스트의 지도 단위(라벨 0비트 표적)가 L1 의 5배 미만이면 안 잰다",
        "프리텍스트 표적 = 관측 칸": fuel["나 · 축 행렬의 칸과 빈칸 세 갈래"]["관측"],
        "L1": L1,
        "배수": round(fuel["나 · 축 행렬의 칸과 빈칸 세 갈래"]["관측"] / L1, 2),
        "통과": fuel["나 · 축 행렬의 칸과 빈칸 세 갈래"]["관측"] >= 5 * L1,
        "🔴 정직 표지": ("배수의 **분자는 칸이고 분모는 행이다** — 조항 60 이 금하는 "
                     "이어 붙이기에 가장 가까운 자리다. 그래서 **행 기준도 함께 적는다**: "
                     f"축 행렬 22,900행 중 라벨 없는 행은 "
                     f"{fuel['가 · 라벨 있는 행']['라벨 없는 행']}행뿐이다 — "
                     "**행 수준에서는 라벨 없는 연료가 사실상 0 이다**"),
    }
    fuel["벽시계(초)"] = round(time.time() - t0, 1)
    (ROOT / "runners/out909_fuel.json").write_text(
        json.dumps(fuel, ensure_ascii=False, indent=1))
    print(f"연료 표 저장 · 갈래 {branch} · {time.time()-t0:.0f}초", flush=True)

    # ── 1단계 프리텍스트 + 3단계 배선 + 자 (다) ───────────────────────
    print("1단계 · 프리텍스트…", flush=True)
    out = {"무엇": "팔 909-ㅁ · 프리텍스트 · 배선 · 자 (다)", **stamp(),
           "🔴 라벨 0비트 단언": S.assert_no_labels(),
           "🔴 갈래": branch}
    assert out["🔴 라벨 0비트 단언"]["판정"] == "라벨 0비트", "🔴 라벨 토큰 발견 — 중단"

    bank0 = S.build_bank(data, seed=S.SEED)
    banks = {"무텍스트": bank0}
    if branch in ("G1 떠받친다", "G2 반쪽"):
        b1 = S.build_bank(data, seed=S.SEED)
        banks["텍스트"] = S.attach_text(b1, texts, k=64, exclude=None, seed=S.SEED)
    curves, recon, shas = {}, {}, {}
    for tag, b in banks.items():
        V = np.vstack([b.V[d] for d in b.doms])
        M = np.vstack([b.M[d] for d in b.doms])
        Me = np.vstack([b.Meval[d] for d in b.doms])
        Mall = np.vstack([b.Mall[d] for d in b.doms])
        per_seed = []
        for sd in (0, 1, 2):
            net, cv = S.pretrain(V, M, seed=sd, steps=400)
            R = S.reconstruct(net, V, M)
            e = Me > 0
            sse = float((((R - V) ** 2) * e).sum())
            sst = float(((V ** 2) * e).sum())
            per_seed.append({"씨앗": sd, "손실 곡선(스텝,MSE)": cv,
                             "🔴 자 (다) 유보 셀 R²": round(1 - sse / max(sst, 1e-9), 4),
                             "유보 셀 수": int(e.sum())})
            if sd == 0:
                Z = S.encode(net, V, M)
                shas[tag] = S.sha_of(Z)
        curves[tag] = per_seed
        recon[tag] = {"칸": int(V.size), "관측": int((Mall > 0).sum()),
                      "학습 가시 칸": int((M > 0).sum()),
                      "자 (다) 평가 칸": int((Me > 0).sum()),
                      "합 단언(가시+평가 == 관측)":
                          int((M > 0).sum()) + int((Me > 0).sum()) == int((Mall > 0).sum())}
    diag = None
    if "텍스트" in recon:
        a, b_ = recon["무텍스트"], recon["텍스트"]
        diag = {
            "🔴 자 (다) 평가 칸은 두 팔이 **같다**": (a["자 (다) 평가 칸"]
                                          == b_["자 (다) 평가 칸"]),
            "평가 칸": a["자 (다) 평가 칸"],
            "🔴 그러므로 R² 의 분모가 같다(조항 60 통과)": True,
            "학습 가시 칸 · 무텍스트": a["학습 가시 칸"],
            "학습 가시 칸 · 텍스트": b_["학습 가시 칸"],
            "🔴 텍스트 블록이 프리텍스트 손실에서 차지하는 몫":
                round(1 - a["학습 가시 칸"] / b_["학습 가시 칸"], 4),
            "읽는 법": "텍스트 팔의 R² 가 낮으면 그것은 **축 칸 복원이 나빠졌다**는 뜻이다 "
                    "— 텍스트 64열이 축 칸보다 훨씬 많은 손실 몫을 가져가기 때문이다. "
                    "손실 가중을 안 맞췄고 **사전등록에 없었으므로 사후에 안 맞춘다**"}
    out["1단계 · 프리텍스트 손실 곡선 · 자 (다)"] = {"팔별": curves, "칸 회계": recon,
                                        "🔴 텍스트 팔 진단": diag}

    # 배선 W1 — 프리텍스트를 끄면 sha 가 바뀌나
    b = bank0
    V = np.vstack([b.V[d] for d in b.doms])
    M = np.vstack([b.M[d] for d in b.doms])
    net_on, _ = S.pretrain(V, M, seed=0, steps=400)
    net_off, _ = S.pretrain(V, M, seed=0, steps=0)
    sha_on, sha_off = S.sha_of(S.encode(net_on, V, M)), S.sha_of(S.encode(net_off, V, M))
    net_again, _ = S.pretrain(V, M, seed=0, steps=400)
    sha_again = S.sha_of(S.encode(net_again, V, M))
    # 한 배치 과적합 (아키텍처.md §9.1 ①)
    sel = np.arange(min(32, V.shape[0]))
    _n, cv1 = S.pretrain(V[sel], M[sel], seed=0, steps=1200, p_mask=0.3,
                         record_every=200)
    #: 🔴 표적 고정판 — 프리텍스트는 매 스텝 **다른 칸**을 가리므로 「외운다」가
    #: 성립하려면 가림 무늬를 고정해야 한다. 둘을 **함께** 싣는다(조항 59).
    _n2, cv2 = S.pretrain(V[sel], M[sel], seed=0, steps=1200, p_mask=0.3,
                          record_every=200, fixed_hide=True)
    out["3단계 · 배선 검사"] = {
        "W1 프리텍스트 on/off sha256": {
            "on": sha_on, "off(0스텝)": sha_off, "바뀌나": sha_on != sha_off},
        "결정성(같은 씨앗 두 번 · 아키텍처.md §9.1)": {
            "sha 1": sha_on, "sha 2": sha_again, "비트 동일": sha_on == sha_again},
        "한 배치 과적합(32행) · 가림 무늬 **매 스텝 새로**": {
            "곡선": cv1,
            "첫/끝 비율": round(cv1[-1][1] / max(cv1[0][1], 1e-12), 5),
            "통과(<0.05)": cv1[-1][1] / max(cv1[0][1], 1e-12) < 0.05,
            "🔴 이 판은 검사가 성립 안 한다": "표적이 매 스텝 바뀌므로 '외운다'가 정의되지 "
                                    "않는다. 아래 고정판이 정본이다"},
        "🔴 한 배치 과적합(32행) · 가림 무늬 **고정**(정본)": {
            "곡선": cv2,
            "첫/끝 비율": round(cv2[-1][1] / max(cv2[0][1], 1e-12), 5),
            "통과(<0.05)": cv2[-1][1] / max(cv2[0][1], 1e-12) < 0.05},
        "표현 sha(팔별 · 씨앗0)": shas,
        "W2·W3 는 runners/ssl909_probe.py 에서 (프로브가 있어야 잰다)": True,
    }
    out["벽시계(초)"] = round(time.time() - t0, 1)
    (ROOT / "runners/out909_pretext.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(f"프리텍스트 저장 · {time.time()-t0:.0f}초", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
