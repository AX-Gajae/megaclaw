# -*- coding: utf-8 -*-
"""사이클 1021 — 시간 정합 최대화: 발행일 v2(적응창·마커) + 사건-시각 추출 v0.

사전등록 docs/탐색/1021.md — 이 러너는 사전등록 커밋에서 언다(조항 66).
층 규약: v1(1015) 성공 행 불변 — v2 는 v1-null 에만. 충돌은 계수만(v1 우선).
사건: pub_time 있는 문서에서만 — 상대 날짜는 pub_time 기준 해소(크롤일 해소 금지).

단계:
  --stage selftest   방향 탐침(leak 6 + v1 4 + v2 6 + 사건 8) — 실패면 측정 없이 중단
  --stage sao        ⓐ sao973 재주행(HPLT 8샤드) — v1 재계산(정합 게이트)+v2+사건
  --stage fineweb    ⓑ FineWeb2-ko 25샤드 — rg 체크포인트+예산제(1015 미러)
  --stage discourse  ⓒ 1017 담론 수확물(로컬 파일) — 사건 추출
  --stage verify     오탐 표본 판정(G-a·G-b)
  --stage report     집계 out JSON

위생: CPU ≤5스레드(pyarrow 4·OMP 4) · 샤드 전 load1>10 → 60초 재잼(until) ·
      진행 로그 전 행 시각 칸 · 산출물은 wm_harvest(조항 73-마) · 크롤일 대체 금지.
"""
import argparse
import collections
import datetime as dt
import glob
import gzip
import hashlib
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pretrain.leak_guard import selftest as leak_selftest  # noqa: E402

os.environ.setdefault("OMP_NUM_THREADS", "4")
import pyarrow as pa                      # noqa: E402
import pyarrow.parquet as pq              # noqa: E402
pa.set_cpu_count(4)

SCRATCH = Path("/Users/ax/wm_harvest/foundation/pubdate")
V2 = SCRATCH / "v2"
FW2_OUT = V2 / "fineweb2_pubdate_v2"
EVD = Path("/Users/ax/wm_harvest/foundation/event_candidates")
for p in (V2, FW2_OUT, EVD):
    p.mkdir(parents=True, exist_ok=True)
PROG = V2 / "progress.jsonl"
VERIFY_SAMPLES = V2 / "verify_samples.jsonl"

PAIRS = ROOT / "data/ingest/sao973_hplt/pairs.jsonl.gz"
HPLT_DIR = ROOT / "data/ingest/hplt_ko"
SHARD_IDX = (0, 58, 116, 174, 232, 290, 348, 406)
FW_DIR = Path("/Users/ax/wm_harvest/fineweb2_ko")
DISC_DIR = Path("/Users/ax/wm_harvest/discourse")

V1_SAO_STATE = SCRATCH / "sao_state.json"            # 1015 실측(불변 — 정합 게이트 기준)
V1_FW_STATE = SCRATCH / "fineweb2_pubdate" / "state.json"

SAO_STATE = V2 / "sao_state_v2.json"
SAO_OUT = V2 / "sao973_pubdate_v2.jsonl.gz"
FW_STATE = V2 / "state_v2.json"

OUT_SAO = ROOT / "runners/out1021_sao.json"
OUT_FW = ROOT / "runners/out1021_fineweb.json"
OUT_DISC = ROOT / "runners/out1021_discourse.json"
OUT_VERIFY = ROOT / "runners/out1021_verify.json"
OUT_REPORT = ROOT / "runners/out1021_report.json"

# ── v1 사슬(1015 §2 그대로 — 상수·순서 불변) ─────────────────────────────
META_WIN = 4000
BODY_WIN = 200
YMIN, YMAX = 1991, 2026
CONF_V1 = {"구조화메타": 0.9, "html메타": 0.8, "url패턴": 0.7, "본문정규식": 0.5}
RE_JSONLD = re.compile(r'"datePublished"\s*:\s*"([^"]{4,40})"')
RE_OG1 = re.compile(r'article:published_time["\']?[^>]{0,120}?content\s*=\s*["\']([^"\']{4,40})', re.I)
RE_OG2 = re.compile(r'content\s*=\s*["\']([^"\']{4,40})["\'][^>]{0,120}?article:published_time', re.I)
RE_META1 = re.compile(r'<meta[^>]{0,200}?(?:name|itemprop|property)\s*=\s*["\'](?:date|pubdate|publishdate|publish[-_]date|datePublished|article[._]published)["\'][^>]{0,200}?content\s*=\s*["\']([^"\']{4,40})', re.I)
RE_META2 = re.compile(r'<time[^>]{0,200}?datetime\s*=\s*["\']([^"\']{4,40})', re.I)
RE_U_YMD_SLASH = re.compile(r'/(19\d{2}|20[0-2]\d)/(\d{1,2})/(\d{1,2})(?=[/?#.]|$)')
RE_U_YMD_SEP = re.compile(r'[/=_.-](19\d{2}|20[0-2]\d)[-._](\d{1,2})[-._](\d{1,2})(?=[/?#._-]|$)')
RE_U_YMD8 = re.compile(r'(?<!\d)(19\d{2}|20[0-2]\d)(0[1-9]|1[0-2])([0-3]\d)(?!\d)')
RE_U_QDATE = re.compile(r'[?&](?:date|dt|ymd|d)=?(19\d{2}|20[0-2]\d)[-.]?(\d{2})[-.]?(\d{2})(?!\d)')
RE_B_KO = re.compile(r'(19\d{2}|20[0-2]\d)\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일')
RE_B_SEP = re.compile(r'(?<![\d.])(19\d{2}|20[0-2]\d)\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{1,2})(?![\d.])')
RE_V_ISO = re.compile(r'^(\d{4})-(\d{2})-(\d{2})')
RE_V_DOT = re.compile(r'^(\d{4})[./](\d{1,2})[./](\d{1,2})')
RE_V_8 = re.compile(r'^(\d{4})(\d{2})(\d{2})$')

# ── v2 등록 상수(§1) ─────────────────────────────────────────────────────
CONF_V2 = {"마커앵커": 0.65, "머리확장": 0.45, "꼬리": 0.40}
MARK_WIN = 1000          # ⓐ 머리·꼬리 각각 따로(이어붙임 금지)
HEAD_EXT = (200, 600)    # ⓑ v1 창과 무겹침
TAIL_WIN = 600           # ⓒ
RE_MARK = re.compile(r'(?:입력|등록|승인|작성일?|게재|송고|기사입력|발행일?)\s*[:\-–]?\s*'
                     r'(19\d{2}|20[0-2]\d)\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})')
RE_ANTI = re.compile(r'(?:ⓒ|©|\(c\)|[Cc]opyright|저작권|무단\s*전재|[Aa]ll\s*[Rr]ights)')
RE_PUBMARK = re.compile(r'(?:입력|등록|승인|작성|게재|송고|발행|기자|뉴스|게시)')

# ── 사건 v0 등록 상수(§4) ────────────────────────────────────────────────
EV_WIN = 1500
EV_VERBS = ("개봉", "발매", "출시", "오픈", "공개", "개최", "방영", "컴백", "개막",
            "발표", "런칭", "론칭", "시작", "데뷔", "발간", "개통")
RE_EV_VERB = re.compile("(" + "|".join(EV_VERBS) + ")")
RE_MD = re.compile(r'(\d{1,2})\s*월\s*(\d{1,2})\s*일')
RE_ONEUN = re.compile(r'오는\s*(\d{1,2})\s*일')
RE_NAEDAL = re.compile(r'내달\s*(\d{1,2})\s*일')
RE_IDAL = re.compile(r'이(?:달|번\s*달)\s*(\d{1,2})\s*일')
EV_MAX_DIFF = 400
EV_CAP = 5

RAN = ("runners/pubdate1021.py", "pretrain/leak_guard.py")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def code_stamp():
    return {"코드": {p: _sha16(str(ROOT / p)) for p in RAN}, "시각(UTC)": _now()}


def _prog(**kw):
    kw["시각"] = _now()
    with PROG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def load1_gate():
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


def v1_extract(url, text):
    """1015 사슬 축자 재계산 — 게이트 2(정합)의 대상."""
    win = text[:META_WIN]
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
    if "<meta" in win or "<time" in win:
        m = RE_META1.search(win) or RE_META2.search(win)
        if m:
            d = _parse_meta_value(m.group(1))
            if d:
                return d, "html메타"
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
    head = text[:BODY_WIN]
    for rx in (RE_B_KO, RE_B_SEP):
        m = rx.search(head)
        if m:
            d = _mkdate(*m.groups())
            if d:
                return d, "본문정규식"
    return None, None


def v2_extract(text):
    """§1 v2 사슬 ⓐ→ⓑ→ⓒ. (date, method, 매치구간(원문 좌표), None)|((None,)*4)."""
    n = len(text)
    # ⓐ 마커앵커 — 머리·꼬리 «각각 따로»
    for base, seg in ((0, text[:MARK_WIN]),
                      (max(0, n - MARK_WIN), text[-MARK_WIN:] if n > MARK_WIN else "")):
        if not seg:
            continue
        for m in RE_MARK.finditer(seg):
            d = _mkdate(*m.groups())
            if d:
                return d, "마커앵커", (base + m.start(), base + m.end()), None
    # ⓑ 머리확장 [200,600)
    seg = text[HEAD_EXT[0]:HEAD_EXT[1]]
    for rx in (RE_B_KO, RE_B_SEP):
        m = rx.search(seg)
        if m:
            d = _mkdate(*m.groups())
            if d:
                return d, "머리확장", (HEAD_EXT[0] + m.start(), HEAD_EXT[0] + m.end()), None
    # ⓒ 꼬리 600 — 반마커(−60,+20) 제외 후 다음 매치
    base = max(0, n - TAIL_WIN)
    seg = text[base:]
    for rx in (RE_B_KO, RE_B_SEP):
        for m in rx.finditer(seg):
            d = _mkdate(*m.groups())
            if not d:
                continue
            ctx = seg[max(0, m.start() - 60):m.end() + 20]
            if RE_ANTI.search(ctx):
                continue
            return d, "꼬리", (base + m.start(), base + m.end()), None
    return None, None, None, None


def v2_conflict(text, v1_date):
    """v1 성공 행 관찰 — v2 신규 패턴 첫 성공값과의 관계. 일치|충돌|무반응."""
    d, meth, _, _ = v2_extract(text)
    if d is None:
        return "무반응"
    return "일치" if d == v1_date else "충돌"


def other_dates(text):
    """검사 C 원료 — 머리1000·꼬리1000 창의 유효 날짜 전부(계수·min·max)."""
    n = len(text)
    segs = [text[:MARK_WIN]]
    if n > MARK_WIN:
        segs.append(text[-MARK_WIN:])
    ds = []
    for seg in segs:
        for rx in (RE_B_KO, RE_B_SEP):
            for m in rx.finditer(seg):
                d = _mkdate(*m.groups())
                if d:
                    ds.append(d)
    if not ds:
        return 0, None, None
    return len(ds), min(ds).isoformat(), max(ds).isoformat()


# ── 사건-시각 추출 v0(§4) ────────────────────────────────────────────────

def _add_months(y, m, k):
    m2 = m + k
    y += (m2 - 1) // 12
    m2 = (m2 - 1) % 12 + 1
    return y, m2


def _try_date(y, m, d):
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


def extract_events(text, pub, ent_rx, title=None, cnt=None):
    """«미래 사건 예고» 후보. pub 없으면 해소 불가 — 아무것도 안 뽑는다(등록 §4)."""
    if cnt is None:
        cnt = collections.Counter()
    if pub is None:
        return [], cnt
    zone = text[:EV_WIN]
    matches = []          # (start, end, 꼴, date|None, conf, 해소)
    for rx, kind in ((RE_B_KO, "절대_년월일"), (RE_B_SEP, "절대_구분자")):
        for m in rx.finditer(zone):
            d = _mkdate(*m.groups())
            if d:
                matches.append((m.start(), m.end(), kind, d, 0.6, "불요"))
    for m in RE_ONEUN.finditer(zone):
        day = int(m.group(1))
        d = _try_date(pub.year, pub.month, day)
        if d is None or d < pub:
            y2, m2 = _add_months(pub.year, pub.month, 1)
            d = _try_date(y2, m2, day)
        if d:
            matches.append((m.start(), m.end(), "오는D일", d, 0.5, "pub기준"))
    for m in RE_NAEDAL.finditer(zone):
        y2, m2 = _add_months(pub.year, pub.month, 1)
        d = _try_date(y2, m2, int(m.group(1)))
        if d:
            matches.append((m.start(), m.end(), "내달D일", d, 0.5, "pub기준"))
    for m in RE_IDAL.finditer(zone):
        d = _try_date(pub.year, pub.month, int(m.group(1)))
        if d:
            matches.append((m.start(), m.end(), "이달D일", d, 0.5, "pub기준"))
    taken = [(s, e) for s, e, *_ in matches]
    for m in RE_MD.finditer(zone):        # ㉰ 연도무 — 절대형 꼬리와 겹치면 건너뜀
        s, e = m.start(), m.end()
        if any(not (e <= ts or s >= te) for ts, te in taken):
            continue
        pre = zone[max(0, s - 8):s]
        if re.search(r'(19|20)\d{2}\s*년\s*$', pre):
            continue
        d = _try_date(pub.year, int(m.group(1)), int(m.group(2)))
        reso = "pub연도"
        if d is not None and (d - pub).days < -45:
            d = _try_date(pub.year + 1, int(m.group(1)), int(m.group(2)))
            reso = "pub연도+1"
            cnt["연도해소+1"] += 1
        if d:
            matches.append((s, e, "연도무MD", d, 0.4, reso))
    # 우선순위: 등록 순(절대→상대→연도무) · 겹침 제거 후 판별
    out, used = [], []
    matches.sort(key=lambda x: ({"절대_년월일": 0, "절대_구분자": 0, "오는D일": 1,
                                 "내달D일": 1, "이달D일": 1, "연도무MD": 2}[x[2]], x[0]))
    for s, e, kind, d, conf, reso in matches:
        if any(not (e <= us or s >= ue) for us, ue in used):
            continue
        used.append((s, e))
        if zone[max(0, s - 6):s].find("지난") >= 0:
            cnt["지난제외"] += 1
            continue
        vm = RE_EV_VERB.search(zone[e:e + 40])
        if not vm:
            cnt["무동사"] += 1
            continue
        diff = (d - pub).days
        if diff <= 0:
            cnt["과거당일제외"] += 1
            continue
        if diff > EV_MAX_DIFF:
            cnt["400일초과제외"] += 1
            continue
        if len(out) >= EV_CAP:
            cnt["문서상한넘침"] += 1
            continue
        win = zone[max(0, s - 80):e + 80] + (" " + title if title else "")
        ents = []
        for em in ent_rx.finditer(win):
            if em.group(0) not in ents:
                ents.append(em.group(0))
            if len(ents) >= 3:
                break
        out.append({"event_time": d.isoformat(), "event_type": vm.group(1),
                    "날짜꼴": kind, "해소": reso, "diff일": diff,
                    "개체": ents, "conf": conf})
        cnt["후보"] += 1
        cnt["type:" + vm.group(1)] += 1
        cnt["꼴:" + kind] += 1
        cnt["ev연도:" + str(d.year)] += 1
        if ents:
            cnt["개체매칭행"] += 1
    return out, cnt


_ENT_RX = None


def ent_regex():
    global _ENT_RX
    if _ENT_RX is None:
        from runners.discourse1017 import names_1017
        names, _src = names_1017()
        keep = [n for n in names if 2 <= len(n) <= 30]
        keep.sort(key=len, reverse=True)
        _ENT_RX = re.compile("|".join(re.escape(n) for n in keep))
        _prog(단계="개체명단", 전체=len(names), 매칭명단=len(keep), 제외=len(names) - len(keep))
    return _ENT_RX


# ── 저수지 표본(§2 — 층화 k=120 · 씨앗 1021) ────────────────────────────

class Reservoir:
    def __init__(self, k, key, state=None):
        self.k = k
        self.rng = random.Random("1021|" + key)
        self.n = state["n"] if state else 0
        self.buf = state["buf"] if state else []
        if state and "rng" in state:
            self.rng.setstate(tuple_state(state["rng"]))

    def offer(self, make):
        self.n += 1
        if len(self.buf) < self.k:
            self.buf.append(make())
            return True
        j = self.rng.randrange(self.n)
        if j < self.k:
            self.buf[j] = make()
            return True
        return False

    def dump(self):
        st = self.rng.getstate()
        return {"n": self.n, "buf": self.buf,
                "rng": [st[0], list(st[1]), st[2]]}


def tuple_state(s):
    return (s[0], tuple(s[1]), s[2])


# ── 방향 탐침(측정 전) ───────────────────────────────────────────────────

def stage_selftest():
    r = leak_selftest()
    # v1 사슬 4(1015 미러)
    d1, m1 = v1_extract("http://x.kr/2020/03/05/a", "본문에 날짜 없음 " * 20)
    d2, m2 = v1_extract("http://x.kr/a", "2019년 7월 3일 입력 기사 본문 " + "채움 " * 100)
    d3, m3 = v1_extract("http://x.kr/a", "날짜가 전혀 없는 본문 " * 50)
    d4, m4 = v1_extract("http://x.kr/a", "채움 " * 200 + "2019년 7월 3일")
    v1p = {
        "url참": d1 == dt.date(2020, 3, 5) and m1 == "url패턴",
        "본문참": d2 == dt.date(2019, 7, 3) and m2 == "본문정규식",
        "무날짜null": d3 is None,
        "200자밖null": d4 is None,
    }
    # v2 합성 6
    pad = "채움글 " * 80                                   # ≈320자 — v1 창 밖
    t_mark = pad + "본문. " + "채움 " * 200 + "기사입력 2021-03-04 12:00"
    a1 = v2_extract(t_mark)
    t_forge = "2020.3.4 " + "채움 " * 300 + "끝머리 입력"    # 머리에 날짜·꼬리에 마커 — 이어붙이면 위조됨
    a2 = v2_extract(t_forge)
    t_head = pad + "2018년 5월 6일 공지 " + "채움 " * 300
    a3 = v2_extract(t_head)
    t_tail = "채움 " * 400 + "작성글 2017.11.22 목록"
    a4 = v2_extract(t_tail)
    t_anti = "채움 " * 400 + "ⓒ 2017.11.22 무단전재 금지"
    a5 = v2_extract(t_anti)
    c1 = v2_conflict("2020년 1월 2일 " + pad + " " + "채움 " * 300 + "입력 2021.5.6",
                     dt.date(2020, 1, 2))
    v2p = {
        "마커앵커 참": a1[0] == dt.date(2021, 3, 4) and a1[1] == "마커앵커",
        "경계위조 거짓(꼬리마커+머리날짜 비결합)": not (a2[0] == dt.date(2020, 3, 4) and a2[1] == "마커앵커"),
        "머리확장 참": a3[0] == dt.date(2018, 5, 6) and a3[1] == "머리확장",
        "꼬리 참": a4[0] == dt.date(2017, 11, 22) and a4[1] == "꼬리",
        "꼬리 반마커 거짓": a5[0] is None,
        "v1우선 충돌 계수": c1 == "충돌",
    }
    # 사건 합성 8
    rx = re.compile("아이유|르세라핌")                      # 탐침용 명단(실주행은 names_1017)
    pub = dt.date(2026, 3, 2)
    e1, _ = extract_events("영화가 2026년 9월 10일 개봉 예정이다", pub, rx)
    e2, _ = extract_events("아이유 신곡이 오는 15일 발매된다", pub, rx)
    e3, _ = extract_events("팝업이 내달 3일 오픈한다", pub, rx)
    e4, _ = extract_events("행사는 이달 20일 개최", pub, rx)
    e5, _ = extract_events("드라마는 1월 5일 공개된다", dt.date(2026, 11, 20), rx)
    e6, _ = extract_events("2026년 9월 10일 개최 행사", None, rx)
    c6 = collections.Counter()
    e7, c6 = extract_events("지난 3월 2일 개최됐다", dt.date(2026, 8, 1), rx, cnt=c6)
    c7 = collections.Counter()
    e8, c7 = extract_events("2020년 1월 1일 개봉했던 영화", pub, rx, cnt=c7)
    evp = {
        "절대 참": len(e1) == 1 and e1[0]["event_time"] == "2026-09-10" and e1[0]["event_type"] == "개봉",
        "오는D일 해소": len(e2) == 1 and e2[0]["event_time"] == "2026-03-15" and e2[0]["개체"] == ["아이유"],
        "내달 해소": len(e3) == 1 and e3[0]["event_time"] == "2026-04-03",
        "이달 해소": len(e4) == 1 and e4[0]["event_time"] == "2026-03-20",
        "연도무 +1년 해소": len(e5) == 1 and e5[0]["event_time"] == "2027-01-05",
        "pub무 → 0": e6 == [],
        "「지난」 제외": e7 == [] and c6["지난제외"] == 1,
        "과거 제외": e8 == [] and c7["과거당일제외"] == 1,
    }
    ok = r["전부_기대대로"] and all(v1p.values()) and all(v2p.values()) and all(evp.values())
    out = {"단계": "selftest(방향 탐침 — 측정 전)", "leak_guard": r["전부_기대대로"],
           "v1 사슬 4": v1p, "v2 합성 6": v2p, "사건 합성 8": evp,
           "전부_기대대로": ok, "도장": code_stamp()}
    (V2 / "selftest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    _prog(단계="selftest", 전부_기대대로=ok)
    print(json.dumps({"selftest": ok, "v1": v1p, "v2": v2p, "ev": evp}, ensure_ascii=False))
    if not ok:
        raise SystemExit("«측정 없이 중단» — 방향 탐침 실패")
    return out


# ── ⓐ sao973 재주행 ─────────────────────────────────────────────────────

def _load_pair_docs():
    docs = set()
    rows = 0
    with gzip.open(str(PAIRS), "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            docs.add(d["a_액션"]["문서id"])
            rows += 1
    return docs, rows


def _res_load(st, key):
    return Reservoir(120, key, st.get("표본", {}).get(key))


def stage_sao(max_seconds):
    t0 = time.time()
    ent = ent_regex()
    docset, n_rows = _load_pair_docs()
    st = {"완료샤드": [], "문서": {}, "사건계수": {}, "표본": {}}
    if SAO_STATE.exists():
        st = json.loads(SAO_STATE.read_text(encoding="utf-8"))
    res = {p: _res_load(st, "sao|" + p) for p in CONF_V2}
    evcnt = collections.Counter(st.get("사건계수", {}))
    shards = sorted(glob.glob(str(HPLT_DIR / "train-*-of-00464.parquet")))
    picked = [(i, shards[i]) for i in SHARD_IDX if i < len(shards)]
    _prog(단계="sao", 무엇="시작", 유일문서=len(docset), 행=n_rows, 완료샤드=len(st["완료샤드"]))
    ev_f = gzip.open(str(EVD / "sao973.events.jsonl.gz"), "at", encoding="utf-8")
    try:
        for si, path in picked:
            name = Path(path).name
            if name in st["완료샤드"]:
                continue
            if time.time() - t0 > max_seconds:
                _prog(단계="sao", 무엇="예산 소진 — 같은 호출 반복으로 재개")
                print(json.dumps({"sao": "부분", "완료샤드": len(st["완료샤드"])}, ensure_ascii=False))
                return "부분"
            load1_gate()
            pf = pq.ParquetFile(path)
            for rg in range(pf.metadata.num_row_groups):
                d = pf.read_row_group(rg, columns=["id", "u", "ts", "text"]).to_pydict()
                for j in range(len(d["id"])):
                    did = d["id"][j]
                    if did not in docset or did in st["문서"]:
                        continue
                    text = d["text"][j] or ""
                    url = d["u"][j] or ""
                    ts = d["ts"][j]
                    crawl = ts.date() if ts else None
                    v1d, v1m = v1_extract(url, text)
                    rec = {"v1": v1d.isoformat() if v1d else None, "v1m": v1m,
                           "v2": None, "v2m": None, "충돌": None}
                    pub = v1d
                    if v1d is not None:
                        rec["충돌"] = v2_conflict(text, v1d)
                    else:
                        d2, m2, span, _ = v2_extract(text)
                        if d2 is not None:
                            rec["v2"], rec["v2m"] = d2.isoformat(), m2
                            pub = d2
                            diff = (d2 - crawl).days if crawl else None
                            rec["차이일"] = diff

                            def make(_did=did, _d2=d2, _m2=m2, _span=span,
                                     _text=text, _crawl=crawl, _diff=diff):
                                s, e = _span
                                snip = _text[max(0, s - 60):e + 60].replace("\n", " ")
                                od = other_dates(_text)
                                return {"층": "sao|" + _m2, "문서id": _did,
                                        "snippet": snip,
                                        "published_at": _d2.isoformat(),
                                        "crawl": _crawl.isoformat() if _crawl else None,
                                        "diff": _diff,
                                        "반마커": bool(RE_ANTI.search(snip)),
                                        "발행마커": bool(RE_PUBMARK.search(snip)),
                                        "타날짜n": od[0], "타날짜min": od[1], "타날짜max": od[2]}
                            res[m2].offer(make)
                    if pub is not None:
                        evs, evcnt = extract_events(text, pub, ent, cnt=evcnt)
                        for ev in evs:
                            ev2 = dict(ev)
                            ev2.update({"출처": "sao973", "문서id": did,
                                        "pub_time": pub.isoformat()})
                            ev_f.write(json.dumps(ev2, ensure_ascii=False) + "\n")
                    st["문서"][did] = rec
            st["완료샤드"].append(name)
            st["사건계수"] = dict(evcnt)
            st["표본"] = {k: r.dump() for k, r in res.items()}
            ev_f.flush()
            SAO_STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
            _prog(단계="sao", 샤드=name, 누적문서=len(st["문서"]), 초=round(time.time() - t0, 1))
    finally:
        ev_f.close()
    # 8/8 완료 — 정합(게이트 2) + 집계 + v2 행 산출
    v1st = json.loads(V1_SAO_STATE.read_text(encoding="utf-8"))["문서"]
    mismatch = 0
    for did, old in v1st.items():
        new = st["문서"].get(did)
        if new is None or new["v1"] != old["published_at"] or (new["v1m"] or None) != (old["method"] or None):
            mismatch += 1
    meth_v1 = collections.Counter((r["v1m"] or "null") for r in st["문서"].values())
    meth_v2 = collections.Counter(r["v2m"] for r in st["문서"].values() if r["v2m"])
    confl = collections.Counter(r["충돌"] for r in st["문서"].values() if r["충돌"])
    n_v2 = 0
    diffs, post = [], 0
    with gzip.open(str(SAO_OUT), "wt", encoding="utf-8") as f:
        for did, r in st["문서"].items():
            if r["v2"]:
                n_v2 += 1
                f.write(json.dumps({"문서id": did, "published_at": r["v2"],
                                    "method": r["v2m"], "confidence": CONF_V2[r["v2m"]],
                                    "층": "v2", "차이일": r.get("차이일")},
                                   ensure_ascii=False) + "\n")
                if r.get("차이일") is not None:
                    diffs.append(r["차이일"])
                    if r["차이일"] > 0:
                        post += 1

    def _q(v, q):
        if not v:
            return None
        s = sorted(v)
        k = (len(s) - 1) * q
        lo, hi = int(k), min(int(k) + 1, len(s) - 1)
        return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)

    den = len(docset)
    ok_v1 = sum(n for m, n in meth_v1.items() if m != "null")
    with VERIFY_SAMPLES.open("a", encoding="utf-8") as vf:
        for k, r in res.items():
            for it in r.buf:
                vf.write(json.dumps(it, ensure_ascii=False) + "\n")
    out = {
        "사이클": 1021, "단계": "ⓐ sao973 v2 재주행", "사전등록": "docs/탐색/1021.md §1~§4",
        "분모": {"행": n_rows, "유일 문서": den, "완주샤드": len(st["완료샤드"])},
        "게이트2(v1 불변 정합)": {"문서별 불일치": mismatch, "통과": mismatch == 0,
                                  "v1 방법별(재계산)": dict(meth_v1)},
        "v2 층": {"성공 문서": n_v2, "분모(v1-null)": meth_v1.get("null", 0),
                  "방법별": {m: {"성공": n, "분모": den, "율": round(n / den, 4)}
                             for m, n in meth_v2.most_common()},
                  "차이일": {"n": len(diffs), "중앙": _q(diffs, 0.5), "q25": _q(diffs, 0.25),
                             "q75": _q(diffs, 0.75), "diff>0": post,
                             "diff>0율": round(post / len(diffs), 4) if diffs else None}},
        "🔴 커버리지(문서 단위 · 분모 병기)": {
            "v1": {"성공": ok_v1, "분모": den, "율": round(ok_v1 / den, 4)},
            "v1∪v2": {"성공": ok_v1 + n_v2, "분모": den, "율": round((ok_v1 + n_v2) / den, 4)}},
        "충돌(v1 성공 행 관찰 — v1 우선)": dict(confl),
        "사건 후보 계수": dict(evcnt),
        "산출물": {"v2 행": {"경로": str(SAO_OUT), "sha256_16": _sha16(str(SAO_OUT))},
                   "사건": str(EVD / "sao973.events.jsonl.gz")},
        "도장": code_stamp(),
    }
    OUT_SAO.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog(단계="sao", 무엇="완료", 커버리지=out["🔴 커버리지(문서 단위 · 분모 병기)"])
    print(json.dumps({"sao": "완료", "게이트2": mismatch == 0,
                      "커버리지": out["🔴 커버리지(문서 단위 · 분모 병기)"]}, ensure_ascii=False))
    return "완료"


# ── ⓑ FineWeb2-ko ───────────────────────────────────────────────────────

FW_SAVE_EVERY = 200


def _fw_state():
    if FW_STATE.exists():
        return json.loads(FW_STATE.read_text(encoding="utf-8"))
    return {"샤드": {}, "표본": {}, "사건계수": {}}


def stage_fineweb(max_seconds, max_shards):
    t0 = time.time()
    ent = ent_regex()
    st = _fw_state()
    res = {p: _res_load(st, "fineweb|" + p) for p in CONF_V2}
    evcnt = collections.Counter(st.get("사건계수", {}))
    v1ref = json.loads(V1_FW_STATE.read_text(encoding="utf-8"))["샤드"]
    shards = sorted(glob.glob(str(FW_DIR / "*.parquet")))
    _prog(단계="fineweb", 무엇="시작", 전체샤드=len(shards),
          완료샤드=sum(1 for v in st["샤드"].values() if v.get("완료")))
    ev_f = gzip.open(str(EVD / "fineweb2.events.jsonl.gz"), "at", encoding="utf-8")

    def _save():
        st["표본"] = {k: r.dump() for k, r in res.items()}
        st["사건계수"] = dict(evcnt)
        ev_f.flush()
        FW_STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")

    try:
        for path in shards:
            name = Path(path).name
            s = st["샤드"].get(name)
            if s and s.get("완료"):
                continue
            if max_shards and sum(1 for v in st["샤드"].values() if v.get("완료")) >= max_shards:
                break
            if time.time() - t0 > max_seconds:
                break
            load1_gate()
            if s is None:
                s = {"rg_다음": 0, "행": 0, "v1방법": {}, "v2방법": {}, "널": 0,
                     "충돌": {}, "차이히스토": {}, "크롤이후": 0, "완료": False, "초": 0.0}
                st["샤드"][name] = s
            pf = pq.ParquetFile(path)
            n_rg = pf.metadata.num_row_groups
            out_path = FW2_OUT / (name.replace(".parquet", "") + ".pub2.jsonl.gz")
            t_sh = time.time()
            fo = gzip.open(str(out_path), "at", encoding="utf-8")
            try:
                for rg in range(s["rg_다음"], n_rg):
                    if time.time() - t0 > max_seconds:
                        break
                    d = pf.read_row_group(rg, columns=["id", "url", "date", "text"]).to_pydict()
                    for j in range(len(d["id"])):
                        s["행"] += 1
                        text = d["text"][j] or ""
                        v1d, v1m = v1_extract(d["url"][j] or "", text)
                        pub = v1d
                        if v1d is not None:
                            s["v1방법"][v1m] = s["v1방법"].get(v1m, 0) + 1
                            c = v2_conflict(text, v1d)
                            s["충돌"][c] = s["충돌"].get(c, 0) + 1
                        else:
                            d2, m2, span, _ = v2_extract(text)
                            if d2 is None:
                                s["널"] += 1
                            else:
                                pub = d2
                                s["v2방법"][m2] = s["v2방법"].get(m2, 0) + 1
                                crawl = (d["date"][j] or "")[:10]
                                diff = None
                                try:
                                    diff = (d2 - dt.date.fromisoformat(crawl)).days
                                except ValueError:
                                    pass
                                if diff is not None:
                                    k = str(diff)
                                    s["차이히스토"][k] = s["차이히스토"].get(k, 0) + 1
                                    if diff > 0:
                                        s["크롤이후"] += 1
                                fo.write(json.dumps(
                                    {"id": d["id"][j], "published_at": d2.isoformat(),
                                     "method": m2, "confidence": CONF_V2[m2],
                                     "층": "v2", "crawl": crawl, "차이일": diff},
                                    ensure_ascii=False) + "\n")

                                def make(_id=d["id"][j], _d2=d2, _m2=m2, _span=span,
                                         _text=text, _crawl=crawl, _diff=diff):
                                    ss, ee = _span
                                    snip = _text[max(0, ss - 60):ee + 60].replace("\n", " ")
                                    od = other_dates(_text)
                                    return {"층": "fineweb|" + _m2, "문서id": _id,
                                            "snippet": snip, "published_at": _d2.isoformat(),
                                            "crawl": _crawl, "diff": _diff,
                                            "반마커": bool(RE_ANTI.search(snip)),
                                            "발행마커": bool(RE_PUBMARK.search(snip)),
                                            "타날짜n": od[0], "타날짜min": od[1],
                                            "타날짜max": od[2]}
                                res[m2].offer(make)
                        if pub is not None:
                            evs, evcnt = extract_events(text, pub, ent, cnt=evcnt)
                            for ev in evs:
                                ev2 = dict(ev)
                                ev2.update({"출처": "fineweb2", "문서id": d["id"][j],
                                            "pub_time": pub.isoformat()})
                                ev_f.write(json.dumps(ev2, ensure_ascii=False) + "\n")
                    s["rg_다음"] = rg + 1
                    if (rg + 1) % FW_SAVE_EVERY == 0:
                        s["초"] = round(s["초"] + (time.time() - t_sh), 1)
                        t_sh = time.time()
                        fo.flush()
                        _save()
                        _prog(단계="fineweb", 샤드=name, rg=rg + 1, 전체rg=n_rg,
                              행=s["행"], 널=s["널"], 초누적=s["초"])
            finally:
                fo.close()
            s["초"] = round(s["초"] + (time.time() - t_sh), 1)
            if s["rg_다음"] >= n_rg:
                s["완료"] = True
                ref = v1ref.get(name, {})
                s["게이트2"] = (s["v1방법"] == ref.get("방법") and
                                s["행"] == ref.get("행"))
                _prog(단계="fineweb", 샤드=name, 무엇="샤드 완료", 행=s["행"],
                      v1정합=s["게이트2"], v2추출=sum(s["v2방법"].values()), 초누적=s["초"])
            _save()
        n_done = sum(1 for v in st["샤드"].values() if v.get("완료"))
        _prog(단계="fineweb", 무엇="호출 끝", 완료샤드=n_done, 초=round(time.time() - t0, 1))
        print(json.dumps({"fineweb": {"완료샤드": n_done}}, ensure_ascii=False))
        return n_done
    finally:
        ev_f.close()


# ── ⓒ 1017 담론 — 사건 추출 ─────────────────────────────────────────────

def stage_discourse():
    ent = ent_regex()
    files = sorted(glob.glob(str(DISC_DIR / "*" / "*.jsonl.gz")))
    evcnt = collections.Counter()
    n_rows = n_pub = 0
    ev_n = 0
    with gzip.open(str(EVD / "discourse1017.events.jsonl.gz"), "wt", encoding="utf-8") as ev_f:
        for path in files:
            src = Path(path).parent.name
            with gzip.open(path, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    n_rows += 1
                    pub = None
                    pa_ = (r.get("published_at") or "")[:10]
                    try:
                        pub = dt.date.fromisoformat(pa_)
                    except ValueError:
                        pass
                    if pub is None:
                        continue
                    n_pub += 1
                    title = r.get("제목") or ""
                    body = r.get("본문") or ""
                    text = (title + " " + body).strip()
                    evs, evcnt = extract_events(text, pub, ent, title=title, cnt=evcnt)
                    did = hashlib.sha1((r.get("url") or title).encode("utf-8")).hexdigest()[:16]
                    for ev in evs:
                        ev2 = dict(ev)
                        ev2.update({"출처": "discourse1017/" + src, "문서id": did,
                                    "pub_time": pub.isoformat()})
                        ev_f.write(json.dumps(ev2, ensure_ascii=False) + "\n")
                        ev_n += 1
    out = {"사이클": 1021, "단계": "ⓒ 1017 담론 사건 추출",
           "파일": {Path(p).parent.name + "/" + Path(p).name: _sha16(p) for p in files},
           "분모": {"행": n_rows, "pub 있음": n_pub},
           "사건 후보 계수": dict(evcnt), "사건 행": ev_n,
           "산출물": str(EVD / "discourse1017.events.jsonl.gz"), "도장": code_stamp()}
    OUT_DISC.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog(단계="discourse", 행=n_rows, pub=n_pub, 사건=ev_n)
    print(json.dumps({"discourse": {"행": n_rows, "pub": n_pub, "사건": ev_n}}, ensure_ascii=False))


# ── 오탐 검증(§2) ────────────────────────────────────────────────────────

def stage_verify():
    seen = {}
    for line in VERIFY_SAMPLES.open(encoding="utf-8"):
        it = json.loads(line)
        seen[(it["층"], it["문서id"])] = it       # 재개 중복 — (층,문서id) 유일화(등록)
    strata = collections.defaultdict(list)
    for it in seen.values():
        strata[it["층"]].append(it)
    per = {}
    isolated = []
    for k, items in sorted(strata.items()):
        n = len(items)
        a = sum(1 for i in items if i["diff"] is not None and i["diff"] > 2)
        b = sum(1 for i in items if i["반마커"])
        strong = sum(1 for i in items
                     if (i["diff"] is not None and i["diff"] > 2) or i["반마커"])
        amb = sum(1 for i in items
                  if not ((i["diff"] is not None and i["diff"] > 2) or i["반마커"])
                  and not i["발행마커"])
        c_lo = sum(1 for i in items if i["타날짜n"] > 0 and i["타날짜min"]
                   and i["published_at"] < i["타날짜min"])
        c_hi = sum(1 for i in items if i["타날짜n"] > 0 and i["타날짜max"]
                   and i["published_at"] > i["타날짜max"])
        verdict = None
        if n >= 30:
            verdict = (strong / n) <= 0.10
            if not verdict:
                isolated.append(k)
        per[k] = {"n": n, "검사A(diff>2)": a, "검사B(반마커)": b,
                  "강오탐(A∪B)": strong, "강오탐률": round(strong / n, 4) if n else None,
                  "애매(마커무)": amb, "애매율": round(amb / n, 4) if n else None,
                  "검사C(관찰)": {"min미만": c_lo, "max초과": c_hi},
                  "판정(G-a ≤10%)": ("미판정(n<30)" if n < 30 else ("통과" if verdict else "격리"))}
    # G-b — v2 전량 diff>0 (원천별)
    gb = {}
    if OUT_SAO.exists():
        so = json.loads(OUT_SAO.read_text(encoding="utf-8"))
        d = so["v2 층"]["차이일"]
        gb["sao"] = {"diff>0": d["diff>0"], "n": d["n"],
                     "율": d["diff>0율"], "판정(≤4.0%)": (d["diff>0율"] or 0) <= 0.04}
    st = _fw_state()
    done = [v for v in st["샤드"].values() if v.get("완료")]
    if done:
        n_v2 = sum(sum(v["v2방법"].values()) for v in done)
        n_diff = sum(sum(v["차이히스토"].values()) for v in done)
        post = sum(v["크롤이후"] for v in done)
        rate = round(post / n_diff, 4) if n_diff else None
        gb["fineweb"] = {"diff>0": post, "n": n_diff, "v2성공": n_v2,
                         "율": rate, "판정(≤4.0%)": (rate or 0) <= 0.04}
    for srcname, g in gb.items():
        if not g["판정(≤4.0%)"]:
            isolated.append(srcname + "|전층(G-b)")
    out = {"사이클": 1021, "단계": "오탐 검증(§2)", "표본(유일화 후)": {k: v["n"] for k, v in per.items()},
           "층별": per, "G-b(diff>0 ≤4.0% · 원천별)": gb,
           "격리 목록": isolated, "도장": code_stamp()}
    OUT_VERIFY.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog(단계="verify", 격리=isolated)
    print(json.dumps({"verify": {"층별판정": {k: v["판정(G-a ≤10%)"] for k, v in per.items()},
                                 "G-b": {k: v["판정(≤4.0%)"] for k, v in gb.items()},
                                 "격리": isolated}}, ensure_ascii=False))


# ── 집계 ────────────────────────────────────────────────────────────────

def stage_report():
    st = _fw_state()
    done = {k: v for k, v in st["샤드"].items() if v.get("완료")}
    part = {k: v for k, v in st["샤드"].items() if not v.get("완료")}
    iso = []
    if OUT_VERIFY.exists():
        iso = json.loads(OUT_VERIFY.read_text(encoding="utf-8"))["격리 목록"]

    rows = sum(v["행"] for v in done.values())
    v1ok = sum(sum(v["v1방법"].values()) for v in done.values())
    v2meth = collections.Counter()
    confl = collections.Counter()
    hist = collections.Counter()
    post = 0
    for v in done.values():
        for m, n in v["v2방법"].items():
            v2meth[m] += n
        for m, n in v["충돌"].items():
            confl[m] += n
        for k, n in v["차이히스토"].items():
            hist[int(k)] += n
        post += v["크롤이후"]
    v2ok = sum(v2meth.values())
    v2net = v2ok - sum(n for m, n in v2meth.items() if "fineweb|" + m in iso)
    if any(x.startswith("fineweb|전층") for x in iso):
        v2net = 0

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

    gate2 = all(v.get("게이트2") for v in done.values()) if done else None
    fw = {
        "완료 샤드": len(done), "부분 샤드": len(part), "행(분모·완주)": rows,
        "게이트2(v1 불변 정합 — 25샤드 방법별·행 일치)": gate2,
        "커버리지(행)": {
            "v1": {"성공": v1ok, "분모": rows, "율": round(v1ok / rows, 4) if rows else None},
            "v2 층": {m: {"성공": n, "분모": rows, "율": round(n / rows, 4)}
                      for m, n in v2meth.most_common()},
            "v1∪v2": {"성공": v1ok + v2ok, "분모": rows,
                      "율": round((v1ok + v2ok) / rows, 4) if rows else None},
            "v1∪v2(격리 후 순)": {"성공": v1ok + v2net, "분모": rows,
                                   "율": round((v1ok + v2net) / rows, 4) if rows else None,
                                   "겨냥(≥0.170)": (rows > 0 and (v1ok + v2net) / rows >= 0.170)}},
        "충돌(v1 성공 행 관찰 — v1 우선)": dict(confl),
        "v2 차이일": {"n": sum(hist.values()), "중앙": _hq(0.5), "q25": _hq(0.25),
                      "q75": _hq(0.75), "p10": _hq(0.10), "p90": _hq(0.90),
                      "diff>0": post,
                      "diff>0율": round(post / sum(hist.values()), 4) if hist else None},
        "사건계수": st.get("사건계수", {}),
        "샤드별": {k: {"행": v["행"], "v1": sum(v["v1방법"].values()),
                       "v2": sum(v["v2방법"].values()), "게이트2": v.get("게이트2"),
                       "초": v["초"]} for k, v in sorted(done.items())},
        "부분 샤드 상태": {k: {"rg_다음": v["rg_다음"], "행": v["행"]} for k, v in part.items()},
        "재개법": "python3 runners/pubdate1021.py --stage fineweb --max-seconds N — 상태 " + str(FW_STATE),
    }
    out = {"사이클": 1021, "사전등록": "docs/탐색/1021.md", "격리 목록": iso,
           "fineweb": fw, "도장": code_stamp()}
    OUT_FW.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"report": {"완료샤드": len(done), "게이트2": gate2,
                                 "커버리지": fw["커버리지(행)"].get("v1∪v2(격리 후 순)")}},
                     ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["selftest", "sao", "fineweb", "discourse", "verify", "report"])
    ap.add_argument("--max-seconds", type=float, default=520.0)
    ap.add_argument("--max-shards", type=int, default=0)
    a = ap.parse_args()
    if a.stage == "selftest":
        stage_selftest()
    elif a.stage == "sao":
        stage_selftest()
        stage_sao(a.max_seconds)
    elif a.stage == "fineweb":
        stage_selftest()
        stage_fineweb(a.max_seconds, a.max_shards)
    elif a.stage == "discourse":
        stage_selftest()
        stage_discourse()
    elif a.stage == "verify":
        stage_verify()
    elif a.stage == "report":
        stage_report()


if __name__ == "__main__":
    main()
