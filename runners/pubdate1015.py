# -*- coding: utf-8 -*-
"""사이클 1015 — L0 발행일 추출(L0-1 사슬) + 누수 관문 심은 키(L0-3).

정본: docs/아키텍처_결정기.md(커밋 b32e7eb5f) §L0 · 사전등록 docs/탐색/1015.md.
이 러너는 사전등록 커밋에서 언다(조항 66 — 주행 중 소스 수정 금지).

단계:
  --stage selftest  방향 탐침(측정 전) — leak_guard 합성 참/거짓 자기시험. 실패면 측정 없이 중단.
  --stage sao       ⓐ sao973 쌍 35,641행(유일 문서 26,364)의 원문(HPLT 8샤드)에 사슬 적용
  --stage plant     🔴 심은 키 — 실측 산출물에 사후 문서 1건 주입 → LeakDetected 실증
  --stage fineweb   ⓑ FineWeb2-ko 25 parquet — 샤드 단위 체크포인트+예산제(--max-seconds)
  --stage report    집계 out JSON 갱신(fineweb 진행분 반영)

위생: CPU ≤5스레드(pyarrow 4) · 각 샤드 전 load1>10 이면 60초 대기 반복(until 폴링) ·
      진행 로그 전 행 시각 칸(부칙 4 ㉰) · 산출물은 wm_harvest(저장소 밖 레인 · 조항 73-마).
"""
import argparse
import collections
import datetime as dt
import glob
import gzip
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pretrain.leak_guard import assert_no_leak, LeakDetected, selftest as leak_selftest  # noqa: E402

os.environ.setdefault("OMP_NUM_THREADS", "4")
import pyarrow as pa                      # noqa: E402
import pyarrow.parquet as pq              # noqa: E402
pa.set_cpu_count(4)

SCRATCH = Path("/Users/ax/wm_harvest/foundation/pubdate")
FW_OUT = SCRATCH / "fineweb2_pubdate"
SCRATCH.mkdir(parents=True, exist_ok=True)
FW_OUT.mkdir(parents=True, exist_ok=True)
PROG = SCRATCH / "progress.jsonl"

PAIRS = ROOT / "data/ingest/sao973_hplt/pairs.jsonl.gz"
HPLT_DIR = ROOT / "data/ingest/hplt_ko"
SHARD_IDX = (0, 58, 116, 174, 232, 290, 348, 406)      # 973 사전등록 §5 그대로 — pairs 의 원천
FW_DIR = Path("/Users/ax/wm_harvest/fineweb2_ko")

SAO_STATE = SCRATCH / "sao_state.json"
SAO_OUT = SCRATCH / "sao973_pubdate.jsonl.gz"
FW_STATE = FW_OUT / "state.json"

OUT_SAO = ROOT / "runners/out1015_sao.json"
OUT_PLANT = ROOT / "runners/out1015_plant.json"
OUT_FW = ROOT / "runners/out1015_fineweb.json"

# ── 사전등록 §2 상수 — 측정 뒤에 안 바꾼다 ──────────────────────────────
META_WIN = 4000        # ①② 메타 탐색 창(원 HTML head 근사 — 우리 원천은 추출 평문이라 희박 예상)
BODY_WIN = 200         # ④ 본문 창 — 명세 L0-1 「첫 200자」 그대로
YMIN, YMAX = 1991, 2026
CONF = {"구조화메타": 0.9, "html메타": 0.8, "url패턴": 0.7, "본문정규식": 0.5}

# ① 구조화 메타(JSON-LD·OG)
RE_JSONLD = re.compile(r'"datePublished"\s*:\s*"([^"]{4,40})"')
RE_OG1 = re.compile(r'article:published_time["\']?[^>]{0,120}?content\s*=\s*["\']([^"\']{4,40})', re.I)
RE_OG2 = re.compile(r'content\s*=\s*["\']([^"\']{4,40})["\'][^>]{0,120}?article:published_time', re.I)
# ② HTML 메타
RE_META1 = re.compile(r'<meta[^>]{0,200}?(?:name|itemprop|property)\s*=\s*["\'](?:date|pubdate|publishdate|publish[-_]date|datePublished|article[._]published)["\'][^>]{0,200}?content\s*=\s*["\']([^"\']{4,40})', re.I)
RE_META2 = re.compile(r'<time[^>]{0,200}?datetime\s*=\s*["\']([^"\']{4,40})', re.I)
# ③ URL 패턴
RE_U_YMD_SLASH = re.compile(r'/(19\d{2}|20[0-2]\d)/(\d{1,2})/(\d{1,2})(?=[/?#.]|$)')
RE_U_YMD_SEP = re.compile(r'[/=_.-](19\d{2}|20[0-2]\d)[-._](\d{1,2})[-._](\d{1,2})(?=[/?#._-]|$)')
RE_U_YMD8 = re.compile(r'(?<!\d)(19\d{2}|20[0-2]\d)(0[1-9]|1[0-2])([0-3]\d)(?!\d)')
RE_U_QDATE = re.compile(r'[?&](?:date|dt|ymd|d)=?(19\d{2}|20[0-2]\d)[-.]?(\d{2})[-.]?(\d{2})(?!\d)')
# ④ 본문 정규식(첫 200자 · 한국어 날짜형 포함)
RE_B_KO = re.compile(r'(19\d{2}|20[0-2]\d)\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일')
RE_B_SEP = re.compile(r'(?<![\d.])(19\d{2}|20[0-2]\d)\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{1,2})(?![\d.])')
# ①② 값 문자열 → 날짜
RE_V_ISO = re.compile(r'^(\d{4})-(\d{2})-(\d{2})')
RE_V_DOT = re.compile(r'^(\d{4})[./](\d{1,2})[./](\d{1,2})')
RE_V_8 = re.compile(r'^(\d{4})(\d{2})(\d{2})$')

RAN = ("runners/pubdate1015.py", "pretrain/leak_guard.py")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def code_stamp():
    """v3.2 규약 — git HEAD 스탬프 아님: 잰 «코드 파일 sha» + 시각."""
    return {"코드": {p: _sha16(str(ROOT / p)) for p in RAN}, "시각(UTC)": _now()}


def _prog(**kw):
    kw["시각"] = _now()                      # 부칙 4 ㉰ — 전 행 시각 칸
    with PROG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def load1_gate():
    """load1 > 10 이면 60초 간격 재잼 반복(until 폴링) — 통과까지."""
    while True:
        l1 = os.getloadavg()[0]
        if l1 <= 10.0:
            return l1
        _prog(단계="load1대기", load1=round(l1, 2))
        time.sleep(60)


def _mkdate(y, m, d):
    y, m, d = int(y), int(m), int(d)
    if not (YMIN <= y <= YMAX):
        return None
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


def _parse_meta_value(v):
    v = v.strip()
    for rx in (RE_V_ISO, RE_V_DOT, RE_V_8):
        m = rx.match(v)
        if m:
            return _mkdate(*m.groups())
    m = RE_B_KO.match(v)
    if m:
        return _mkdate(*m.groups())
    return None


def extract_pubdate(url, text):
    """L0-1 사슬 ①→②→③→④→⑤. (date|None, 방법|None) — ⑤ 실패 = (None, None) = «못 읽었다»."""
    win = text[:META_WIN]
    # ① 구조화 메타
    if '"datePublished"' in win:
        m = RE_JSONLD.search(win)
        if m:
            d = _parse_meta_value(m.group(1))
            if d:
                return d, "구조화메타"
    if "article:published_time" in win:
        m = RE_OG1.search(win) or RE_OG2.search(win)
        if m:
            d = _parse_meta_value(m.group(1))
            if d:
                return d, "구조화메타"
    # ② HTML 메타
    if "<meta" in win or "<time" in win:
        m = RE_META1.search(win) or RE_META2.search(win)
        if m:
            d = _parse_meta_value(m.group(1))
            if d:
                return d, "html메타"
    # ③ URL 패턴
    if url:
        try:
            u = unquote(url)
        except Exception:
            u = url
        for rx in (RE_U_YMD_SLASH, RE_U_YMD_SEP, RE_U_QDATE, RE_U_YMD8):
            m = rx.search(u)
            if m:
                d = _mkdate(*m.groups())
                if d:
                    return d, "url패턴"
    # ④ 본문 정규식 — 첫 200자 · 첫 일치
    head = text[:BODY_WIN]
    for rx in (RE_B_KO, RE_B_SEP):
        m = rx.search(head)
        if m:
            d = _mkdate(*m.groups())
            if d:
                return d, "본문정규식"
    # ⑤ 실패 = null = «못 읽었다» (크롤일 대체 금지 — 조항 59)
    return None, None


# ── 방향 탐침(측정 전) — 조항 66 규격 ────────────────────────────────────

def stage_selftest():
    r = leak_selftest()
    # 사슬 자체의 합성 탐침 — 참 방향(심은 날짜가 잡혀야) · 거짓 방향(날짜 없는 본문서 null 이어야)
    d1, m1 = extract_pubdate("http://x.kr/2020/03/05/a", "본문에 날짜 없음 " * 20)
    d2, m2 = extract_pubdate("http://x.kr/a", "2019년 7월 3일 입력 기사 본문 " + "채움 " * 100)
    d3, m3 = extract_pubdate("http://x.kr/a", "날짜가 전혀 없는 본문 " * 50)
    d4, m4 = extract_pubdate("http://x.kr/a", "채움 " * 200 + "2019년 7월 3일")  # 200자 밖 → null 이어야
    probe = {
        "url패턴 참": {"실측": [str(d1), m1], "기대대로": d1 == dt.date(2020, 3, 5) and m1 == "url패턴"},
        "본문 한국어형 참": {"실측": [str(d2), m2], "기대대로": d2 == dt.date(2019, 7, 3) and m2 == "본문정규식"},
        "무날짜 → null": {"실측": [str(d3), m3], "기대대로": d3 is None and m3 is None},
        "200자 밖 → null(창 준수)": {"실측": [str(d4), m4], "기대대로": d4 is None and m4 is None},
    }
    ok = r["전부_기대대로"] and all(v["기대대로"] for v in probe.values())
    out = {"단계": "selftest(방향 탐침 — 측정 전)", "leak_guard": r, "사슬 합성 탐침": probe,
           "전부_기대대로": ok, "도장": code_stamp()}
    _prog(단계="selftest", 전부_기대대로=ok)
    print(json.dumps({"selftest": ok}, ensure_ascii=False))
    if not ok:
        raise SystemExit("«측정 없이 중단» — 방향 탐침 실패")
    return out


# ── ⓐ sao973 ────────────────────────────────────────────────────────────

def _load_pairs():
    rows = []
    with gzip.open(str(PAIRS), "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            a = d["a_액션"]
            rows.append((d["쌍id"], a["문서id"], a.get("host"), a["언제"]))
    return rows


def stage_sao(max_seconds):
    t0 = time.time()
    pairs_sha = _sha16(str(PAIRS))
    rows = _load_pairs()
    docset = {r[1] for r in rows}
    st = {"완료샤드": [], "문서": {}}
    if SAO_STATE.exists():
        st = json.loads(SAO_STATE.read_text(encoding="utf-8"))
    shards = sorted(glob.glob(str(HPLT_DIR / "train-*-of-00464.parquet")))
    picked = [(i, shards[i]) for i in SHARD_IDX if i < len(shards)]
    _prog(단계="sao", 무엇="시작", 행=len(rows), 유일문서=len(docset), pairs_sha=pairs_sha,
          완료샤드=len(st["완료샤드"]))
    for si, path in picked:
        name = Path(path).name
        if name in st["완료샤드"]:
            continue
        if time.time() - t0 > max_seconds:
            _prog(단계="sao", 무엇="예산 소진 — 체크포인트 후 종료(같은 호출 반복으로 재개)")
            SAO_STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
            print(json.dumps({"sao": "부분", "완료샤드": len(st["완료샤드"])}, ensure_ascii=False))
            return "부분"
        load1_gate()
        pf = pq.ParquetFile(path)
        n_scan, n_hit = 0, 0
        for rg in range(pf.metadata.num_row_groups):
            tb = pf.read_row_group(rg, columns=["id", "u", "ts", "text"])
            d = tb.to_pydict()
            for j in range(len(d["id"])):
                n_scan += 1
                did = d["id"][j]
                if did not in docset or did in st["문서"]:
                    continue
                n_hit += 1
                ts = d["ts"][j]
                pub, method = extract_pubdate(d["u"][j] or "", d["text"][j] or "")
                st["문서"][did] = {
                    "published_at": pub.isoformat() if pub else None,
                    "method": method,
                    "confidence": CONF.get(method) if method else None,
                    "crawl": ts.date().isoformat() if ts else None,
                }
        st["완료샤드"].append(name)
        SAO_STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        _prog(단계="sao", 샤드=name, 스캔=n_scan, 대상문서=n_hit, 누적추출문서=len(st["문서"]),
              초=round(time.time() - t0, 1))
    # 8/8 완료 → 행별 산출 + 집계
    docs = st["문서"]
    n_lines = 0
    meth_doc = collections.Counter()
    diffs_all, diffs_by = [], collections.defaultdict(list)
    year_hist = collections.Counter()
    post_crawl = 0
    with gzip.open(str(SAO_OUT), "wt", encoding="utf-8") as f:
        for pid, did, host, when in rows:
            rec = docs.get(did)
            if rec is None:
                row = {"쌍id": pid, "문서id": did, "published_at": None, "method": "원문미발견",
                       "confidence": None, "crawl": when, "차이일": None}
            else:
                diff = None
                if rec["published_at"]:
                    p = dt.date.fromisoformat(rec["published_at"])
                    c = dt.date.fromisoformat(rec["crawl"])
                    diff = (p - c).days
                row = {"쌍id": pid, "문서id": did, "published_at": rec["published_at"],
                       "method": rec["method"], "confidence": rec["confidence"],
                       "crawl": rec["crawl"], "차이일": diff}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n_lines += 1
    # 문서 단위 집계(유일 문서 기준)
    n_missing = len(docset) - len(docs)
    for did, rec in docs.items():
        meth_doc[rec["method"] or "null"] += 1
        if rec["published_at"]:
            p = dt.date.fromisoformat(rec["published_at"])
            c = dt.date.fromisoformat(rec["crawl"])
            diff = (p - c).days
            diffs_all.append(diff)
            diffs_by[rec["method"]].append(diff)
            year_hist[p.year] += 1
            if diff > 0:
                post_crawl += 1

    def _q(v, q):
        if not v:
            return None
        s = sorted(v)
        k = (len(s) - 1) * q
        lo, hi = int(k), min(int(k) + 1, len(s) - 1)
        return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)

    den_doc = len(docset)
    den_row = len(rows)
    ok_doc = sum(n for m, n in meth_doc.items() if m != "null")
    # 행 단위 성공(문서 결과를 행으로 전개)
    ok_row = sum(1 for _, did, _, _ in rows
                 if docs.get(did) and docs[did]["published_at"])
    out = {
        "사이클": 1015, "단계": "ⓐ sao973 발행일 추출", "사전등록": "docs/탐색/1015.md §2·§3",
        "원천": {"pairs": str(PAIRS.relative_to(ROOT)), "sha256_16": pairs_sha,
                 "행(분모)": den_row, "유일 문서(분모)": den_doc,
                 "HPLT 샤드": [n for n in st["완료샤드"]], "샤드 수": len(st["완료샤드"])},
        "🔴 추출률(분모 병기)": {
            "문서 단위": {"성공": ok_doc, "분모": den_doc, "율": round(ok_doc / den_doc, 4)},
            "행 단위": {"성공": ok_row, "분모": den_row, "율": round(ok_row / den_row, 4)},
            "원문미발견 문서": n_missing,
        },
        "방법별(문서 단위 · 분모=유일 문서 26,364)": {
            m: {"성공": n, "분모": den_doc, "율": round(n / den_doc, 4)}
            for m, n in sorted(meth_doc.items(), key=lambda x: -x[1])},
        "차이일(published_at − crawl · 문서 단위)": {
            "n": len(diffs_all), "중앙": _q(diffs_all, 0.5),
            "q25": _q(diffs_all, 0.25), "q75": _q(diffs_all, 0.75),
            "p10": _q(diffs_all, 0.10), "p90": _q(diffs_all, 0.90),
            "크롤 이후 발행(diff>0 · 의심 계수)": post_crawl,
            "방법별 중앙": {m: _q(v, 0.5) for m, v in diffs_by.items()},
        },
        "발행 연도 히스토그램(계수)": dict(sorted(year_hist.items())),
        "995 주장 대조(관찰 — 게이트 아님)": {
            "995 «본문 최신 날짜 − ts» 중앙(cc22 884/928)": -674,
            "995 «언급 언제 − 사건 날짜» 중앙(34,225행)": -808,
            "본 측정 «published_at − crawl» 중앙": _q(diffs_all, 0.5),
            "주의": "셋은 서로 다른 자다 — 방향(발행이 크롤보다 앞) 일치 여부만 본다",
        },
        "산출물(저장소 밖 레인 · 조항 73-마)": {
            "경로": str(SAO_OUT), "행": n_lines, "크기(바이트)": SAO_OUT.stat().st_size,
            "sha256_16": _sha16(str(SAO_OUT))},
        "도장": code_stamp(),
    }
    OUT_SAO.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog(단계="sao", 무엇="완료", 추출률_문서=out["🔴 추출률(분모 병기)"]["문서 단위"]["율"],
          초=round(time.time() - t0, 1))
    print(json.dumps({"sao": "완료", "추출률(문서)": out["🔴 추출률(분모 병기)"]["문서 단위"],
                      "중앙 차이일": _q(diffs_all, 0.5)}, ensure_ascii=False))
    return "완료"


# ── 🔴 심은 키 — 실측 산출물에 사후 문서 1건 주입 ───────────────────────

def stage_plant():
    if not SAO_OUT.exists():
        raise SystemExit("«미측정» — sao 산출물이 없다. --stage sao 먼저.")
    rows = []
    with gzip.open(str(SAO_OUT), "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["published_at"]:
                rows.append({"id": d["문서id"], "published_at": d["published_at"]})
    max_pub = max(r["published_at"] for r in rows)
    as_of = (dt.date.fromisoformat(max_pub) + dt.timedelta(days=1)).isoformat()
    out = {"사이클": 1015, "단계": "🔴 심은 키(L0-3 붉히기)", "입력": "sao973_pubdate.jsonl.gz 의 발행일 실측행",
           "n_실측입력": len(rows), "max_published_at(실측)": max_pub, "as_of": as_of}
    # 참 쪽 — 실측 그대로면 통과 스탬프
    try:
        stamp = assert_no_leak(rows, as_of, tag="1015 심은키-참(실측 그대로)")
        out["참(실측 그대로)"] = {"판정": "통과", "스탬프": stamp}
        ok_true = True
    except LeakDetected as e:
        out["참(실측 그대로)"] = {"판정": "🔴 예상밖 중단", "메시지": str(e)[:400]}
        ok_true = False
    # 거짓 쪽 — 사후 문서 1건 주입 → 붉어져야 한다
    planted = rows + [{"id": "PLANTED-1015-사후문서", "published_at":
                       (dt.date.fromisoformat(as_of) + dt.timedelta(days=10)).isoformat()}]
    try:
        assert_no_leak(planted, as_of, tag="1015 심은키-거짓(사후 1건 주입)")
        out["거짓(사후 주입)"] = {"판정": "🔴 안 붉어짐 — 관문 실패"}
        ok_false = False
    except LeakDetected as e:
        out["거짓(사후 주입)"] = {"판정": "LeakDetected(붉어짐)", "메시지": str(e)[:400]}
        ok_false = True
    # 거짓 쪽 2 — null 1건 주입(발행일 미상도 못 들어온다)
    try:
        assert_no_leak(rows + [{"id": "PLANTED-1015-null", "published_at": None}], as_of,
                       tag="1015 심은키-null")
        out["거짓(null 주입)"] = {"판정": "🔴 안 붉어짐 — 관문 실패"}
        ok_null = False
    except LeakDetected as e:
        out["거짓(null 주입)"] = {"판정": "LeakDetected(붉어짐)", "메시지": str(e)[:400]}
        ok_null = True
    out["게이트 1(심은 키 붉어짐)"] = bool(ok_true and ok_false and ok_null)
    out["도장"] = code_stamp()
    OUT_PLANT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog(단계="plant", 게이트1=out["게이트 1(심은 키 붉어짐)"])
    print(json.dumps({"plant": out["게이트 1(심은 키 붉어짐)"]}, ensure_ascii=False))


# ── ⓑ FineWeb2-ko — 샤드 체크포인트 + 예산제 ────────────────────────────

FW_SAVE_EVERY = 200      # rowgroup 마다가 아니라 200 rg 마다 상태 저장


def _fw_state():
    if FW_STATE.exists():
        return json.loads(FW_STATE.read_text(encoding="utf-8"))
    return {"샤드": {}}


def stage_fineweb(max_seconds, max_shards):
    t0 = time.time()
    st = _fw_state()
    shards = sorted(glob.glob(str(FW_DIR / "*.parquet")))
    _prog(단계="fineweb", 무엇="시작", 전체샤드=len(shards),
          완료샤드=sum(1 for v in st["샤드"].values() if v.get("완료")))
    done_now = 0
    for path in shards:
        name = Path(path).name
        s = st["샤드"].get(name)
        if s and s.get("완료"):
            continue
        n_done_total = sum(1 for v in st["샤드"].values() if v.get("완료"))
        if max_shards and n_done_total >= max_shards:
            break
        if time.time() - t0 > max_seconds:
            break
        load1_gate()
        if s is None:
            s = {"rg_다음": 0, "행": 0, "방법": {}, "널": 0, "차이히스토": {}, "연도": {},
                 "크롤이후": 0, "완료": False, "초": 0.0}
            st["샤드"][name] = s
        pf = pq.ParquetFile(path)
        n_rg = pf.metadata.num_row_groups
        out_path = FW_OUT / (name.replace(".parquet", "") + ".pub.jsonl.gz")
        t_sh = time.time()
        fo = gzip.open(str(out_path), "at", encoding="utf-8")   # 재개 시 gzip 멀티멤버 이어쓰기
        try:
            for rg in range(s["rg_다음"], n_rg):
                if time.time() - t0 > max_seconds:
                    break
                tb = pf.read_row_group(rg, columns=["id", "url", "date", "text"])
                d = tb.to_pydict()
                for j in range(len(d["id"])):
                    s["행"] += 1
                    pub, method = extract_pubdate(d["url"][j] or "", d["text"][j] or "")
                    if pub is None:
                        s["널"] += 1
                        continue
                    s["방법"][method] = s["방법"].get(method, 0) + 1
                    crawl = (d["date"][j] or "")[:10]
                    diff = None
                    try:
                        diff = (pub - dt.date.fromisoformat(crawl)).days
                    except ValueError:
                        pass
                    if diff is not None:
                        k = str(diff)
                        s["차이히스토"][k] = s["차이히스토"].get(k, 0) + 1
                        if diff > 0:
                            s["크롤이후"] += 1
                    s["연도"][str(pub.year)] = s["연도"].get(str(pub.year), 0) + 1
                    fo.write(json.dumps({"id": d["id"][j], "published_at": pub.isoformat(),
                                         "method": method, "confidence": CONF[method],
                                         "crawl": crawl, "차이일": diff},
                                        ensure_ascii=False) + "\n")
                s["rg_다음"] = rg + 1
                if (rg + 1) % FW_SAVE_EVERY == 0:
                    s["초"] = round(s["초"] + (time.time() - t_sh), 1)
                    t_sh = time.time()
                    fo.flush()
                    FW_STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
                    _prog(단계="fineweb", 샤드=name, rg=rg + 1, 전체rg=n_rg, 행=s["행"],
                          널=s["널"], 초누적=s["초"])
        finally:
            fo.close()
        s["초"] = round(s["초"] + (time.time() - t_sh), 1)
        if s["rg_다음"] >= n_rg:
            s["완료"] = True
            done_now += 1
            _prog(단계="fineweb", 샤드=name, 무엇="샤드 완료", 행=s["행"], 널=s["널"],
                  추출=s["행"] - s["널"], 초누적=s["초"])
        FW_STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    n_done = sum(1 for v in st["샤드"].values() if v.get("완료"))
    _prog(단계="fineweb", 무엇="호출 끝", 완료샤드=n_done, 이번완료=done_now,
          초=round(time.time() - t0, 1))
    print(json.dumps({"fineweb": {"완료샤드": n_done, "이번호출완료": done_now}}, ensure_ascii=False))
    return n_done


def stage_report():
    st = _fw_state()
    done = {k: v for k, v in st["샤드"].items() if v.get("완료")}
    part = {k: v for k, v in st["샤드"].items() if not v.get("완료")}

    def _agg(items):
        rows = sum(v["행"] for v in items.values())
        nul = sum(v["널"] for v in items.values())
        meth = collections.Counter()
        hist = collections.Counter()
        years = collections.Counter()
        post = 0
        for v in items.values():
            for m, n in v["방법"].items():
                meth[m] += n
            for k, n in v["차이히스토"].items():
                hist[int(k)] += n
            for y, n in v["연도"].items():
                years[y] += n
            post += v.get("크롤이후", 0)
        ok = rows - nul

        def _hq(q):
            tot = sum(hist.values())
            if tot == 0:
                return None
            tgt = tot * q
            c = 0
            for k in sorted(hist):
                c += hist[k]
                if c >= tgt:
                    return k
            return None
        return {"행(분모)": rows, "추출 성공": ok, "널(«못 읽었다»)": nul,
                "추출률": round(ok / rows, 4) if rows else None,
                "방법별(분모=행)": {m: {"성공": n, "분모": rows, "율": round(n / rows, 4)}
                                    for m, n in meth.most_common()},
                "차이일(published−crawl)": {"n": sum(hist.values()), "중앙": _hq(0.5),
                                            "q25": _hq(0.25), "q75": _hq(0.75),
                                            "p10": _hq(0.10), "p90": _hq(0.90),
                                            "크롤 이후 발행(diff>0)": post},
                "발행 연도(계수)": dict(sorted(years.items()))}

    per_shard = {k: {"행(분모)": v["행"], "추출": v["행"] - v["널"],
                     "추출률": round((v["행"] - v["널"]) / v["행"], 4) if v["행"] else None,
                     "초": v["초"]} for k, v in sorted(done.items())}
    out = {
        "사이클": 1015, "단계": "ⓑ FineWeb2-ko 발행일 추출(체크포인트+예산제)",
        "사전등록": "docs/탐색/1015.md §2·§3", "원천": str(FW_DIR),
        "전체 샤드(분모)": 25, "완료 샤드": len(done), "부분 샤드": len(part),
        "게이트 2(≥5 샤드 완주)": len(done) >= 5,
        "완주 샤드 집계": _agg(done) if done else None,
        "샤드별": per_shard,
        "부분 샤드 상태": {k: {"rg_다음": v["rg_다음"], "행": v["행"]} for k, v in part.items()},
        "재개법": "python3 runners/pubdate1015.py --stage fineweb --max-seconds N --max-shards M — 상태 " + str(FW_STATE),
        "산출물(저장소 밖 레인)": {"디렉토리": str(FW_OUT),
                                   "행별 파일": "«추출 성공 행만» 게재(등록 결정 — 널 행은 집계 분모로 보존 · 전 행 − 게재 행 = 널)"},
        "도장": code_stamp(),
    }
    OUT_FW.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"report": {"완료샤드": len(done),
                                 "게이트2": out["게이트 2(≥5 샤드 완주)"]}}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["selftest", "sao", "plant", "fineweb", "report"])
    ap.add_argument("--max-seconds", type=float, default=480.0)
    ap.add_argument("--max-shards", type=int, default=0)     # 0 = 무제한(예산 내)
    a = ap.parse_args()
    if a.stage == "selftest":
        out = stage_selftest()
        (SCRATCH / "selftest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    elif a.stage == "sao":
        stage_selftest()          # 방향 탐침은 매 주행 시작 때 — 실패면 측정 없이 중단
        stage_sao(a.max_seconds)
    elif a.stage == "plant":
        stage_plant()
    elif a.stage == "fineweb":
        stage_selftest()
        stage_fineweb(a.max_seconds, a.max_shards)
    elif a.stage == "report":
        stage_report()


if __name__ == "__main__":
    main()
