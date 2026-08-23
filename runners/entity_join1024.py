# -*- coding: utf-8 -*-
"""사이클 1024 — 문서-개체 합류 확충: 전거 매칭 v2 (자료층만 · 판 무접촉).

사전등록: docs/탐색/1024.md (커밋 664c5b0c3 — 이 러너는 그 등록의 집행부다).
단계(순서 강제):
  --stage selftest   방향 탐침(합성) — 어긋나면 측정 없이 중단
  --stage names      명단·변형 전거(§1·§2) → names1024.jsonl.gz
  --stage fresh      ⓐ 신선 스냅숏 복사 + 재매칭(제목+본문)
  --stage sao        ⓒ sao973 dated 원문(HPLT 8샤드) 재매칭
  --stage fineweb    ⓑ FineWeb 25샤드 재매칭 — RG 단위 체크포인트 · --max-seconds 예산
  --stage gate       오탐 게이트(§3) — 층별 전수 계수·격리 판정·표본 반출
  --stage index      개체 색인·G1~G4·재시험 입구(§5·§6) → meta1024.json

위생: CPU ≤6스레드(pyarrow 4) · 무거운 국면 전 load1>10 이면 60초 대기 반복 ·
원본 무수정(신선은 스냅숏 복사본만) · 산출물은 wm_harvest(저장소 밖).
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
import shutil
import sys
import threading
import time
import unicodedata
import zlib
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
os.environ.setdefault("OMP_NUM_THREADS", "4")

OUT = Path("/Users/ax/wm_harvest/foundation/entity_docs")
OUT.mkdir(parents=True, exist_ok=True)
SNAP = OUT / "snapshot_in"
FW_PARTS = OUT / "fineweb_parts"
RUNLOG = OUT / "run1024.out"

PANEL_DIR = ROOT / "data/ingest/wiki_daily959"
DOMS = ["게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "팝업", "펀딩"]
LEDGER = Path("/Users/ax/wm_harvest/foundation/ledger_interventions/ledger.jsonl")
LEDGER_SHA_1016 = "9a76948d"          # 1016 도장 앞 8 — 대조(불일치 = 중단)
PAIRS_SAO = ROOT / "data/ingest/sao973_hplt/pairs.jsonl.gz"
HPLT_DIR = ROOT / "data/ingest/hplt_ko"
SHARD_IDX = (0, 58, 116, 174, 232, 290, 348, 406)   # 1015 그대로
FW_DIR = Path("/Users/ax/wm_harvest/fineweb2_ko")
PUB_V1 = Path("/Users/ax/wm_harvest/foundation/pubdate/fineweb2_pubdate")
PUB_V2 = Path("/Users/ax/wm_harvest/foundation/pubdate/v2/fineweb2_pubdate_v2")
SAO_PUB_V1 = Path("/Users/ax/wm_harvest/foundation/pubdate/sao973_pubdate.jsonl.gz")
SAO_PUB_V2 = Path("/Users/ax/wm_harvest/foundation/pubdate/v2/sao973_pubdate_v2.jsonl.gz")
PAIRS_1022 = Path("/Users/ax/wm_harvest/foundation/state_engine/pairs_index.jsonl.gz")
DISCOURSE = Path("/Users/ax/wm_harvest/discourse")
FRESH_DIRS = ["bing_news", "news_rss", "dcinside", "theqoo", "ruliweb", "instiz",
              "daum_news", "dogdrip"]

MATCH_WIN_PAST = 2000     # §4 — 1019 미러
MATCH_WIN_FRESH = 4000
CTX_WIN = 120             # §2-2 문맥 창
SNIP_WIN = 60             # §3 표본 스니펫
CATALOG_MAX = 30          # §3 카탈로그 관문
A_CAP = 0.10              # §3 층별 강오탐 상한
B_CAP_T2 = 0.85           # §3 T2 무신호 상한
FP_N = 120                # §3 층당 표본
YMIN, YMAX = 1995, 2026   # §4 발행 연도 유효창
FRESH_DIFF_MAX = 2        # §4 신선 차이일 ≤ +2
SE_BASE, N_BASE = 0.000544, 676   # §6 — 1022 유문서 SE 실측·쌍수

# ── 1017/1023 KEYWORDS 49 (동결 사본 — runners/discourse1017.py 그대로) ──────
KEYWORDS = ["웹툰", "웹소설", "팝업스토어", "팝업 스토어", "아이돌 데뷔", "콜라보",
            "굿즈", "IP 라이선스", "캐릭터 IP", "애니메이션 개봉", "단행본", "정주행",
            "콘서트", "팬덤", "스토어 오픈", "네이버웹툰", "카카오웹툰", "카카오페이지",
            "웹툰 원작", "드라마화", "애니화", "영화화", "웹소설 원작", "코믹스",
            "굿즈 완판", "오픈런", "팝업 오픈", "콜라보 카페", "컬래버레이션",
            "케이팝", "K팝", "아이돌 컴백", "데뷔 무대", "쇼케이스", "팬미팅",
            "팬사인회", "월드투어", "돔투어", "빌보드 차트", "음원차트",
            "게임 출시", "신작 게임", "사전예약", "스팀 출시", "콘솔 출시",
            "e스포츠", "서브컬처", "캐릭터 굿즈", "피규어"]

# ── §2-2 도메인 낱말(이름 == 이것 → T3) ─────────────────────────────────────
DOM_WORDS = {"게임", "도서", "만화", "모바일", "애니", "웹툰", "팝업", "펀딩", "아이돌",
             "드라마", "영화", "소설", "음악", "앨범", "만화책", "애니메이션"}

# ── §2-2 도메인 문맥 어휘(일반어 — T3 문맥 신호·검사 B) ─────────────────────
DOM_CTX = {
    "게임": ["게임", "출시", "스팀", "플레이", "유저", "콘솔", "업데이트", "패치", "DLC",
             "e스포츠", "그래픽", "장르"],
    "도서": ["소설", "작가", "출간", "베스트셀러", "독자", "출판", "서점", "도서", "책이"],
    "만화": ["만화", "코믹스", "단행본", "연재", "작가", "애니", "원작", "완결"],
    "모바일": ["앱", "어플", "모바일", "게임", "다운로드", "출시", "구글플레이", "앱스토어",
               "이용자", "업데이트"],
    "세계애니": ["애니", "애니메이션", "방영", "극장판", "성우", "만화", "원작", "더빙",
                 "일본", "시즌"],
    "시장팝업": ["팝업", "팝업스토어", "콜라보", "굿즈", "브랜드", "매장", "오픈", "행사",
                 "백화점", "더현대"],
    "아이돌": ["아이돌", "그룹", "컴백", "앨범", "데뷔", "멤버", "무대", "케이팝", "K팝",
               "음반", "콘서트", "뮤직비디오", "차트", "팬"],
    "애니": ["애니", "애니메이션", "방영", "극장판", "성우", "더빙", "원작", "시즌"],
    "웹툰": ["웹툰", "연재", "작가", "네이버", "카카오", "회차", "원작", "드라마화", "완결"],
    "팝업": ["팝업", "팝업스토어", "오픈", "굿즈", "콜라보", "매장", "행사", "전시"],
    "펀딩": ["펀딩", "크라우드", "후원", "텀블벅", "와디즈", "프로젝트", "목표액"],
}

# ── §2-2 일반어 차단 목록(사전 커밋 — 한국어 일반명사·흔한 낱말) ────────────
BAN_COMMON = {
    "시간", "사람", "사랑", "친구", "가족", "엄마", "아빠", "마음", "세상", "하루", "오늘",
    "내일", "어제", "우리", "이야기", "여름", "겨울", "가을", "봄날", "마녀", "천사", "악마",
    "괴물", "유령", "전설", "영웅", "여왕", "왕자", "공주", "기사", "마법", "마법사", "하늘",
    "바다", "바람", "구름", "별빛", "달빛", "햇살", "나무", "정원", "학교", "회사", "병원",
    "경찰", "군대", "전쟁", "평화", "혁명", "비밀", "약속", "기억", "희망", "절망", "행복",
    "불행", "운명", "기적", "시작", "여행", "모험", "귀환", "복수", "배신", "심판", "구원",
    "부활", "각성", "진화", "변신", "도전", "승리", "패배", "인생", "청춘", "소년", "소녀",
    "남자", "여자", "아이", "어른", "노인", "의사", "선생", "학생", "천재", "바보", "거짓말",
    "진실", "정의", "자유", "고백", "이별", "만남", "인연", "동물", "고양이", "강아지",
    "호랑이", "사자", "늑대", "여우", "토끼", "새벽", "아침", "점심", "저녁", "무기", "방패",
    "갑옷", "왕국", "제국", "도시", "마을", "시장", "골목", "지하", "천국", "지옥", "낙원",
    "미래", "과거", "현재", "역사", "신화", "전투", "사냥", "낚시", "요리", "운동", "축제",
    "공연", "무대", "연극", "뮤지컬", "오디션", "데뷔", "은퇴", "졸업", "입학", "취업",
    "결혼", "이혼", "출산", "죽음", "탄생", "정국", "고수", "보석", "가면", "그림자", "불꽃",
    "폭풍", "번개", "천둥", "안개", "노을", "무지개", "열쇠", "일기", "편지", "선물", "약국",
    "식당", "카페", "호텔", "극장", "박물관", "도서관", "정상", "한계", "본능", "감정",
    "이성", "논리", "사고", "지식", "지혜", "용기", "공포", "분노", "슬픔", "기쁨",
}

_HANG = re.compile(r"[가-힣]")
_LAT = re.compile(r"[A-Za-z]")
_PAREN_TAIL = re.compile(r"\s*\([^)]*\)\s*$")
_SEP = re.compile(r"\s*[:\-–—!?]\s*")
_WS = re.compile(r"\s+")


# ── 공용 ────────────────────────────────────────────────────────────────────
def _prog(**kw):
    kw["시각"] = dt.datetime.now().isoformat(timespec="seconds")
    with open(RUNLOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def _sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()[:16]


def load1_gate():
    while True:
        l1 = os.getloadavg()[0]
        if l1 <= 10:
            return l1
        _prog(무엇="load1 대기", load1=round(l1, 2))
        time.sleep(60)


def norm_nfc(s):
    return unicodedata.normalize("NFC", s or "")


def norm_fold(s):
    return norm_nfc(s).casefold()


def gz_rows(path):
    """gzip jsonl — 잘린 꼬리 멤버는 그 지점부터 버림. 반환 (rows, truncated)."""
    rows, trunc = [], False
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    rows.append(json.loads(ln))
                except Exception:
                    trunc = True
    except (EOFError, OSError):
        trunc = True
    return rows, trunc


def _is_hang(c):
    return "가" <= c <= "힣"


def _ascii_alnum(c):
    return c.isascii() and c.isalnum()


def parse_date(s):
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s))
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


# ── §1·§2 명단·변형 ─────────────────────────────────────────────────────────
def load_panel():
    panel = {}
    for d in DOMS:
        for ln in gzip.open(PANEL_DIR / (d + ".jsonl.gz"), "rt", encoding="utf-8"):
            r = json.loads(ln)
            panel[r["키"]] = {"dom": d, "w": r["문서"], "lang": r.get("언어")}
    return panel


def load_records():
    def _j(p):
        p = ROOT / p
        return json.load(open(p, encoding="utf-8")) if p.exists() else {}
    return {"WT": _j("data/state/webtoon_records.json"), "GAME": _j("data/state/game_records.json"),
            "BOOK": _j("data/state/book_records.json"), "AN": _j("data/state/anime_records.json"),
            "MG": _j("data/state/manga_records.json"), "MB": _j("data/state/mobile_records.json"),
            "WA": _j("data/state/wanime_records.json"), "FUND": _j("data/state/funding_records.json")}


def aliases_for(key, panel, recs, cnt):
    """§1-2·3 — 키 결합 별칭 (문자열, 출처클래스) 목록."""
    out = []
    pre = key.split("-")[0]
    r = None
    if pre in recs and key in recs[pre]:
        r = recs[pre][key]
    elif pre == "IDOL":
        p = ROOT / "data/idol_records" / (key + ".json")
        if p.exists():
            r = json.load(open(p, encoding="utf-8"))
            for f, c in (("group_name", "rec_title"), ("group_name_en", "rec_en")):
                if r.get(f):
                    out.append((r[f], c))
            return out
    elif pre.startswith("MKT"):
        p = ROOT / "data/market_records" / (key + ".json")
        if p.exists():
            r = json.load(open(p, encoding="utf-8"))
            nm = r.get("ip_or_collab") or r.get("brand") or r.get("event_name")
            if nm:
                out.append((nm, "rec_title"))
            return out
    elif pre.startswith("R"):
        p = ROOT / "data/records" / (key + ".json")
        if p.exists():
            r = json.load(open(p, encoding="utf-8"))
            nm = (r.get("entities") or {}).get("brand_key") or \
                 (r.get("intervention") or {}).get("brand_name")
            if nm:
                out.append((nm, "rec_title"))
            return out
    if r:
        nm = r.get("title") or r.get("이름") or r.get("name")
        if nm:
            out.append((nm, "rec_title"))
        if r.get("english"):
            out.append((r["english"], "rec_en"))
        if r.get("native"):
            out.append((r["native"], "rec_native"))
        for s in (r.get("synonyms") or []):
            if isinstance(s, str) and s:
                out.append((s, "rec_syn"))
                cnt["synonym행"] += 1
    return out


def name_gate(s):
    """이름 관문 — 반환 정규화 NFC strip 또는 None."""
    s = _WS.sub(" ", norm_nfc(s or "").strip())
    if not s or s.casefold() in ("null", "none", "unresolved"):
        return None
    if len(s.replace(" ", "")) < 2:
        return None
    if re.fullmatch(r"[\d\s.,-]+", s):
        return None
    return s


def paren_tokens(w):
    m = re.search(r"\(([^)]*)\)\s*$", w)
    if not m:
        return []
    toks = []
    for t in re.split(r"[\s·,/]+", m.group(1)):
        t = t.strip()
        if len(t) >= 2 and not re.fullmatch(r"\d+", t) and "년" not in t and "월" not in t:
            toks.append(t)
    return toks


def tier_of(v, cls):
    """§2-2 — 결정론 티어."""
    if cls == "full":
        return 1
    if cls.endswith("head"):
        return 3
    ns = v.replace(" ", "")
    L = len(ns)
    if ns in BAN_COMMON or ns in DOM_WORDS or ns in _KW_SET:
        t = 3
    elif L >= 5:
        t = 1
    elif L >= 3:
        t = 2
    else:
        t = 3
    if cls.endswith("nospace"):
        t = max(t, 2)
    return t


_KW_SET = {k.replace(" ", "") for k in KEYWORDS}


def variants_of(key, w, cls_prefix=""):
    """§2-1 변형 사슬 — (변형문자열, 클래스) 목록. w 는 이름 관문 통과 문자열."""
    out = []
    base = _WS.sub(" ", _PAREN_TAIL.sub("", w).strip())
    if cls_prefix == "" and base != w:
        out.append((w, "full"))
    b = name_gate(base)
    if b:
        out.append((b, cls_prefix + "base" if cls_prefix else "base"))
        noc = name_gate(_WS.sub(" ", _SEP.sub(" ", b)))
        if noc and noc != b:
            out.append((noc, (cls_prefix or "") + "nocolon"))
        for src in ([b] + ([noc] if noc and noc != b else [])):
            if " " in src and _HANG.search(src):
                nsp = src.replace(" ", "")
                if len(nsp) >= 2:
                    out.append((nsp, (cls_prefix or "") + "nospace"))
        m = re.split(r":|\s-\s", b, maxsplit=1)
        if len(m) > 1:
            h = name_gate(m[0])
            if h and len(h.replace(" ", "")) >= 3 and h != b:
                out.append((h, (cls_prefix or "") + "head"))
    return out


def build_names(write=True):
    """--stage names — 결정론 명단·변형 전거."""
    if LEDGER.exists():
        led_sha = hashlib.sha256(open(LEDGER, "rb").read()).hexdigest()
        if not led_sha.startswith(LEDGER_SHA_1016):
            raise SystemExit("시대 결함: ledger sha " + led_sha[:16])
    panel = load_panel()
    recs = load_records()
    cnt = collections.Counter()
    # 원장 별칭 — page 정확 일치 → 개체
    page2keys = collections.defaultdict(list)
    for k, v in panel.items():
        page2keys[v["w"]].append(k)
    ledger_alias = collections.defaultdict(list)
    n_pg = n_hit = 0
    if LEDGER.exists():
        for ln in open(LEDGER, encoding="utf-8"):
            try:
                r = json.loads(ln)
            except Exception:
                continue
            wr = (r.get("source") or {}).get("wiki_resolution")
            pg = wr.get("page") if isinstance(wr, dict) else (wr if isinstance(wr, str) else None)
            if not pg:
                continue
            n_pg += 1
            pg = norm_nfc(pg).strip()
            if pg in page2keys:
                n_hit += 1
                w = (r.get("A") or {}).get("what") or {}
                for nm in (w.get("ip_name"), w.get("brand")):
                    nm = name_gate(nm)
                    if nm:
                        for k in page2keys[pg]:
                            ledger_alias[k].append(nm)
    ents = {}
    for key, v in sorted(panel.items()):
        w = name_gate(v["w"]) or v["w"]
        vars_ = list(variants_of(key, w))
        seen = {x[0] for x in vars_}
        al = aliases_for(key, panel, recs, cnt)
        for k2 in (ledger_alias.get(key) or []):
            al.append((k2, "ledger"))
        for nm, cls in al:
            nm = name_gate(nm)
            if nm is None:
                cnt["별칭 이름불가"] += 1
                continue
            for vv, vc in variants_of(key, nm, cls_prefix="alias_"):
                if vv not in seen:
                    seen.add(vv)
                    vars_.append((vv, cls + "|" + vc))
            cnt["별칭편입" if cls != "ledger" else "원장별칭편입"] += 1
        rows = []
        for vv, vc in vars_:
            t = tier_of(vv, vc.split("|")[-1])
            rows.append({"v": vv, "cls": vc, "tier": t})
            cnt["티어T%d" % t] += 1
        ents[key] = {"dom": v["dom"], "w": v["w"], "vars": rows,
                     "ptoks": paren_tokens(v["w"])}
    cnt.update({"패널": len(panel), "원장 page 행": n_pg, "원장 page 패널일치 행": n_hit,
                "변형 총": sum(len(e["vars"]) for e in ents.values())})
    if write:
        with gzip.open(OUT / "names1024.jsonl.gz", "wt", encoding="utf-8") as f:
            for key, e in ents.items():
                f.write(json.dumps({"키": key, **e}, ensure_ascii=False) + "\n")
        json.dump(dict(cnt), open(OUT / "names1024_counts.json", "w"),
                  ensure_ascii=False, indent=1)
        _prog(단계="names", **{k: v for k, v in cnt.items()})
    return ents, cnt


# ── 매처 ────────────────────────────────────────────────────────────────────
class Matcher:
    def __init__(self, ents):
        self.ents = ents
        self.vars = []          # (form, key, tier, cls, latin_short, hang)
        self.buckets = collections.defaultdict(list)
        self.sigs = {}
        kw_f = [norm_fold(k) for k in KEYWORDS]
        for key, e in ents.items():
            sig = [norm_fold(x) for x in e["ptoks"]]
            sig += [norm_fold(x) for x in DOM_CTX.get(e["dom"], [])]
            sig += kw_f
            self.sigs[key] = sig
            for r in e["vars"]:
                v = r["v"]
                has_h = bool(_HANG.search(v))
                latin_only = (not has_h) and bool(_LAT.search(v))
                lat_short = latin_only and len(v.replace(" ", "")) <= 4
                form = v if lat_short else norm_fold(v)
                idx = len(self.vars)
                self.vars.append((form, key, r["tier"], r["cls"], lat_short, has_h,
                                  latin_only))
                self.buckets[norm_fold(form)[:2]].append(idx)
        self.bkeys = set(self.buckets)

    @staticmethod
    def _bounded_find(t, v, latin):
        """라틴은 단어 경계(앞뒤 8출현까지) · 그 외 첫 출현. 반환 pos 또는 -1."""
        if not latin:
            return t.find(v)
        st = 0
        for _ in range(8):
            p = t.find(v, st)
            if p < 0:
                return -1
            ok0 = p == 0 or not _ascii_alnum(t[p - 1])
            e = p + len(v)
            ok1 = e >= len(t) or not _ascii_alnum(t[e])
            if ok0 and ok1:
                return p
            st = p + 1
        return -1

    def match(self, t_norm, t_fold):
        tb = {t_fold[i:i + 2] for i in range(len(t_fold) - 1)}
        cand = []
        for b in tb & self.bkeys:
            cand.extend(self.buckets[b])
        hits = {}          # key -> [tier, cls, B, A]
        t3_pend = []
        for i in cand:
            form, key, tier, cls, lat_short, has_h, latin_only = self.vars[i]
            t = t_norm if lat_short else t_fold
            p = self._bounded_find(t, form, latin_only)
            if p < 0:
                continue
            a = 1 if (has_h and p > 0 and _is_hang(t[p - 1])) else 0
            w0 = t_fold[max(0, p - CTX_WIN):p + len(form) + CTX_WIN]
            ctx = 0
            for s in self.sigs[key]:
                if s in w0:
                    ctx = 1
                    break
            rec = (tier, cls, 0 if ctx else 1, a, p, form)
            if tier == 3:
                t3_pend.append((key, rec))
                continue
            old = hits.get(key)
            if old is None or rec[0] < old[0]:
                hits[key] = rec
        n_t3_rej = 0
        for key, rec in t3_pend:
            ok = rec[2] == 0 or key in hits          # 문맥 신호 ∨ 같은 개체 T1/T2
            if not ok:
                n_t3_rej += 1
                continue
            old = hits.get(key)
            if old is None or rec[0] < old[0]:
                hits[key] = (rec[0], rec[1], 0, rec[3], rec[4], rec[5])
        return hits, n_t3_rej


# ── §3 오탐 표본(결정론 bottom-k 저수지) ───────────────────────────────────
class Reservoir:
    def __init__(self, state=None):
        self.s = state if state else {}

    def add(self, src, tier, doc_key, ent, form, a, b, snip):
        st = "%s|T%d" % (src, tier)
        h = zlib.crc32(("1024|%s|%s|%s" % (st, doc_key, ent)).encode("utf-8"))
        lst = self.s.setdefault(st, [])
        lst.append([h, {"층": st, "doc": doc_key, "개체": ent, "변형": form,
                        "A": a, "B": b, "스니펫": snip}])
        if len(lst) > FP_N * 2:
            lst.sort(key=lambda x: x[0])
            del lst[FP_N:]

    def final(self):
        out = []
        for st in sorted(self.s):
            lst = sorted(self.s[st], key=lambda x: x[0])[:FP_N]
            out.extend(x[1] for x in lst)
        return out


def snip_of(t_norm, p, form):
    return t_norm[max(0, p - SNIP_WIN):p + len(form) + SNIP_WIN]


def emit(fh, fh_nopub, src, doc_key, pub, meta, hits, t_norm, agg, res):
    """매칭 문서 1건 기록 + 층 계수 + 표본."""
    ents = []
    for key, (tier, cls, b, a, p, form) in sorted(hits.items()):
        ents.append([key, tier, cls, b, a])
        st = agg["층"].setdefault("%s|T%d" % (src, tier), [0, 0, 0])
        st[0] += 1
        st[1] += a
        st[2] += b
        res.add(src, tier, doc_key, key, form, a, b, snip_of(t_norm, p, form))
    layer = "엔진" if pub else "null"
    catalog = 1 if len(ents) > CATALOG_MAX else 0
    row = {"doc": doc_key, "원천": src, "published_at": pub, **meta,
           "층": layer, "catalog": catalog, "개체수": len(ents), "부착": ents,
           "text_sha16": hashlib.sha256(t_norm.encode("utf-8")).hexdigest()[:16],
           "head280": t_norm[:280]}
    (fh if pub else fh_nopub).write(json.dumps(row, ensure_ascii=False) + "\n")
    agg["문서" if pub else "null문서"] += 1
    if catalog:
        agg["카탈로그"] += 1
    agg["부착"] += len(ents)


# ── §4 ⓐ 신선 ──────────────────────────────────────────────────────────────
def fresh_pub(body_row, list_row, crawl):
    """발행일 사슬 — (date|None, src). §4: 본문 메타 > RSS · 연도창 · 차이일≤+2."""
    for s, tag in ((body_row or {}).get("pub_time"), "body_meta"), \
                  ((list_row or {}).get("published_at"), "rss"):
        d = parse_date(s)
        if d is None:
            continue
        if d.year < YMIN or d.year > YMAX:
            continue
        if crawl and (d - crawl).days > FRESH_DIFF_MAX:
            continue
        return d, tag
    return None, None


def stage_fresh(ents):
    load1_gate()
    if SNAP.exists():
        shutil.rmtree(SNAP)
    SNAP.mkdir(parents=True)
    snap_files = []
    for d in FRESH_DIRS + ["bodies"]:
        (SNAP / d).mkdir()
        for p in sorted(glob.glob(str(DISCOURSE / d / "*.jsonl.gz"))):
            q = SNAP / d / Path(p).name
            shutil.copy2(p, q)
            snap_files.append({"파일": d + "/" + Path(p).name, "sha16": _sha16(q)})
    _prog(단계="fresh", 무엇="스냅숏", 파일수=len(snap_files))
    m = Matcher(ents)
    res = Reservoir()
    agg = {"층": {}, "문서": 0, "null문서": 0, "카탈로그": 0, "부착": 0,
           "목록행": 0, "본문행": 0, "잘림파일": 0, "T3기각": 0}
    bodies = {}
    for p in sorted(glob.glob(str(SNAP / "bodies" / "*.jsonl.gz"))):
        rows, tr = gz_rows(p)
        agg["잘림파일"] += int(tr)
        for r in rows:
            for u in (r.get("url"), r.get("url_수집원본")):
                if u:
                    bodies[u] = r
        agg["본문행"] += len(rows)
    docs = {}
    for d in FRESH_DIRS:
        for p in sorted(glob.glob(str(SNAP / d / "*.jsonl.gz"))):
            rows, tr = gz_rows(p)
            agg["잘림파일"] += int(tr)
            agg["목록행"] += len(rows)
            for r in rows:
                u = r.get("url")
                if not u:
                    continue
                b = bodies.get(u)
                ru = (b or {}).get("url") or u
                docs.setdefault(ru, [r, b])
    fh = gzip.open(OUT / "docs_fresh.jsonl.gz", "wt", encoding="utf-8")
    fh_n = gzip.open(OUT / "docs_fresh_nopub.jsonl.gz", "wt", encoding="utf-8")
    n_scan = 0
    for ru, (lr, br) in sorted(docs.items()):
        n_scan += 1
        crawl = parse_date((lr or {}).get("crawled_at") or (br or {}).get("crawled_at"))
        parts = [(lr or {}).get("제목") or "", (lr or {}).get("본문") or "",
                 (br or {}).get("본문") or ""]
        t_norm = norm_nfc(" ⸱ ".join(x for x in parts if x))[:MATCH_WIN_FRESH]
        if len(t_norm) < 2:
            continue
        t_fold = t_norm.casefold()
        hits, n3 = m.match(t_norm, t_fold)
        agg["T3기각"] += n3
        if not hits:
            continue
        pub, psrc = fresh_pub(br, lr, crawl)
        dk = hashlib.sha256(ru.encode("utf-8")).hexdigest()[:16]
        meta = {"pub_src": psrc, "crawl": crawl.isoformat() if crawl else None,
                "차이일": (pub - crawl).days if (pub and crawl) else None,
                "src2": (lr or {}).get("원천")}
        emit(fh, fh_n, "fresh", dk, pub.isoformat() if pub else None, meta,
             hits, t_norm, agg, res)
    fh.close()
    fh_n.close()
    agg["스캔문서"] = n_scan
    json.dump({"agg": {k: v for k, v in agg.items() if k != "층"}, "층": agg["층"],
               "표본": res.final(), "스냅숏": snap_files},
              open(OUT / "state_fresh.json", "w"), ensure_ascii=False)
    _prog(단계="fresh", **{k: v for k, v in agg.items() if k != "층"})
    print(json.dumps({k: v for k, v in agg.items() if k != "층"}, ensure_ascii=False))


# ── §4 ⓒ sao ───────────────────────────────────────────────────────────────
def sao_dated():
    docs = {}
    for ln in gzip.open(SAO_PUB_V1, "rt", encoding="utf-8"):
        r = json.loads(ln)
        did, pub, diff = r["문서id"], r["published_at"], r.get("차이일")
        if pub and did not in docs and (diff is None or diff <= 0):
            docs[did] = (pub, r.get("method"), r.get("confidence"), r.get("crawl"), diff, "v1")
    for ln in gzip.open(SAO_PUB_V2, "rt", encoding="utf-8"):
        r = json.loads(ln)
        did, pub, diff = r["문서id"], r["published_at"], r.get("차이일")
        if pub and did not in docs and (diff is None or diff <= 0):
            docs[did] = (pub, r.get("method"), r.get("confidence"), None, diff, "v2")
    return docs


def stage_sao(ents):
    import pyarrow.parquet as pq
    import pyarrow as pa
    pa.set_cpu_count(4)
    pa.set_io_thread_count(2)
    dated = sao_dated()
    y_bad = {d for d, v in dated.items()
             if not (YMIN <= int(v[0][:4]) <= YMAX)}
    for d in y_bad:
        del dated[d]
    m = Matcher(ents)
    res = Reservoir()
    agg = {"층": {}, "문서": 0, "null문서": 0, "카탈로그": 0, "부착": 0, "T3기각": 0,
           "dated": len(dated), "연도창밖": len(y_bad), "스캔": 0, "원문발견": 0}
    shards = sorted(glob.glob(str(HPLT_DIR / "train-*-of-00464.parquet")))
    picked = [shards[i] for i in SHARD_IDX if i < len(shards)]
    fh = gzip.open(OUT / "docs_sao.jsonl.gz", "wt", encoding="utf-8")
    fh_n = gzip.open(OUT / "docs_sao_nopub.jsonl.gz", "wt", encoding="utf-8")
    seen = set()
    for path in picked:
        load1_gate()
        pf = pq.ParquetFile(path)
        for rg in range(pf.metadata.num_row_groups):
            tb = pf.read_row_group(rg, columns=["id", "text"])
            d = tb.to_pydict()
            for j in range(len(d["id"])):
                agg["스캔"] += 1
                did = d["id"][j]
                if did not in dated or did in seen:
                    continue
                seen.add(did)
                agg["원문발견"] += 1
                pub, meth, conf, crawl, diff, layer = dated[did]
                t_norm = norm_nfc((d["text"][j] or ""))[:MATCH_WIN_PAST]
                t_fold = t_norm.casefold()
                hits, n3 = m.match(t_norm, t_fold)
                agg["T3기각"] += n3
                if not hits:
                    continue
                meta = {"pub_method": meth, "pub_conf": conf, "crawl": crawl,
                        "차이일": diff, "pub_layer": layer}
                emit(fh, fh_n, "sao", did, pub, meta, hits, t_norm, agg, res)
        _prog(단계="sao", 샤드=Path(path).name, 누적원문=agg["원문발견"],
              누적문서=agg["문서"])
    fh.close()
    fh_n.close()
    json.dump({"agg": {k: v for k, v in agg.items() if k != "층"}, "층": agg["층"],
               "표본": res.final()}, open(OUT / "state_sao.json", "w"), ensure_ascii=False)
    _prog(단계="sao", **{k: v for k, v in agg.items() if k != "층"})
    print(json.dumps({k: v for k, v in agg.items() if k != "층"}, ensure_ascii=False))


# ── §4 ⓑ fineweb ───────────────────────────────────────────────────────────
def fw_pub_map(shard_stem):
    """v1 ∪ v2(머리확장 제외) · 차이일≤0 · 연도창."""
    mp = {}
    cnt = collections.Counter()
    p1 = PUB_V1 / (shard_stem + ".pub.jsonl.gz")
    p2 = PUB_V2 / (shard_stem + ".pub2.jsonl.gz")
    for path, layer in ((p1, "v1"), (p2, "v2")):
        if not path.exists():
            continue
        for ln in gzip.open(path, "rt", encoding="utf-8"):
            r = json.loads(ln)
            pub = r.get("published_at")
            if not pub:
                continue
            if layer == "v2" and r.get("method") == "머리확장":
                cnt["v2 머리확장 제외"] += 1
                continue
            diff = r.get("차이일")
            if diff is not None and diff > 0:
                cnt["차이일>0 제외"] += 1
                continue
            if not (YMIN <= int(pub[:4]) <= YMAX):
                cnt["연도창밖 제외"] += 1
                continue
            if r["id"] in mp:
                continue
            mp[r["id"]] = (pub, r.get("method"), r.get("confidence"),
                           r.get("crawl"), diff, layer)
            cnt["dated " + layer] += 1
    return mp, cnt


def stage_fineweb(ents, max_seconds):
    import pyarrow.parquet as pq
    import pyarrow as pa
    import pyarrow.compute as pc
    pa.set_cpu_count(4)
    pa.set_io_thread_count(2)
    t0 = time.time()
    FW_PARTS.mkdir(exist_ok=True)
    stp = OUT / "state_fineweb.json"
    st = json.loads(stp.read_text()) if stp.exists() else \
        {"완료샤드": [], "진행": None, "계수": {}, "층": {}, "표본": {}, "T3기각": 0,
         "부착": 0, "문서": 0, "카탈로그": 0, "스캔": 0, "dated행": 0}
    m = Matcher(ents)
    res = Reservoir(st["표본"])
    shards = sorted(glob.glob(str(FW_DIR / "*.parquet")))
    for path in shards:
        stem = Path(path).stem
        if stem in st["완료샤드"]:
            continue
        load1_gate()
        mp, pcnt = fw_pub_map(stem)
        for k, v in pcnt.items():
            st["계수"][k] = st["계수"].get(k, 0) + (v if st["진행"] is None or
                                                   st["진행"].get("샤드") != stem else 0)
        idset = pa.array(list(mp))
        pf = pq.ParquetFile(path)
        rg0 = 0
        part = FW_PARTS / (stem + ".jsonl.gz")
        if st["진행"] and st["진행"].get("샤드") == stem:
            rg0 = st["진행"]["rg다음"]
        elif part.exists():
            part.unlink()
        pending = {}
        lock = threading.Lock()

        def _read(k):
            tb = pf.read_row_group(k, columns=["id", "text"])
            mask = pc.is_in(tb.column("id"), value_set=idset)
            tb = tb.filter(mask)
            ids = tb.column("id").to_pylist()
            txt = pc.utf8_slice_codeunits(tb.column("text"), 0, MATCH_WIN_PAST).to_pylist()
            with lock:
                pending[k] = (ids, txt, tb.num_rows)

        nrg = pf.metadata.num_row_groups
        if rg0 < nrg:
            th = threading.Thread(target=_read, args=(rg0,))
            th.start()
        for rg in range(rg0, nrg):
            th.join()
            ids, txt, _n = pending.pop(rg)
            if rg + 1 < nrg:
                th = threading.Thread(target=_read, args=(rg + 1,))
                th.start()
            n_scan = pf.metadata.row_group(rg).num_rows
            fh = gzip.open(part, "ab")
            buf = []
            for j in range(len(ids)):
                did = ids[j]
                pub, meth, conf, crawl, diff, layer = mp[did]
                t_norm = norm_nfc(txt[j] or "")
                t_fold = t_norm.casefold()
                hits, n3 = m.match(t_norm, t_fold)
                st["T3기각"] += n3
                if not hits:
                    continue
                ents_r = []
                for key, (tier, cls, b, a, p, form) in sorted(hits.items()):
                    ents_r.append([key, tier, cls, b, a])
                    lk = "fineweb|T%d" % tier
                    row3 = st["층"].setdefault(lk, [0, 0, 0])
                    row3[0] += 1
                    row3[1] += a
                    row3[2] += b
                    res.add("fineweb", tier, did, key, form, a, b,
                            snip_of(t_norm, p, form))
                catalog = 1 if len(ents_r) > CATALOG_MAX else 0
                st["문서"] += 1
                st["부착"] += len(ents_r)
                st["카탈로그"] += catalog
                buf.append(json.dumps(
                    {"doc": did, "원천": "fineweb", "published_at": pub,
                     "pub_method": meth, "pub_conf": conf, "crawl": crawl,
                     "차이일": diff, "pub_layer": layer, "층": "엔진",
                     "catalog": catalog, "개체수": len(ents_r), "부착": ents_r,
                     "text_sha16": hashlib.sha256(t_norm.encode()).hexdigest()[:16],
                     "head280": t_norm[:280]}, ensure_ascii=False))
            fh.write(("\n".join(buf) + "\n").encode("utf-8") if buf else b"")
            fh.close()
            st["스캔"] += n_scan
            st["dated행"] += len(ids)
            st["진행"] = {"샤드": stem, "rg다음": rg + 1}
            st["표본"] = res.s
            stp.write_text(json.dumps(st, ensure_ascii=False))
            if time.time() - t0 > max_seconds:
                _prog(단계="fineweb", 무엇="예산 소진 — 같은 호출 반복으로 재개",
                      샤드=stem, rg=rg + 1, 문서=st["문서"], 부착=st["부착"])
                print(json.dumps({"fineweb": "부분", "샤드": stem, "rg": rg + 1,
                                  "완료샤드": len(st["완료샤드"])}, ensure_ascii=False))
                return "부분"
        st["완료샤드"].append(stem)
        st["진행"] = None
        stp.write_text(json.dumps(st, ensure_ascii=False))
        _prog(단계="fineweb", 샤드완료=stem, 누적문서=st["문서"], 누적부착=st["부착"],
              스캔=st["스캔"], dated=st["dated행"])
    print(json.dumps({"fineweb": "완료", "완료샤드": len(st["완료샤드"]),
                      "문서": st["문서"], "부착": st["부착"]}, ensure_ascii=False))
    return "완료"


# ── §3 gate ─────────────────────────────────────────────────────────────────
def stage_gate():
    stf = json.loads((OUT / "state_fineweb.json").read_text())
    if len(stf["완료샤드"]) != 25:
        raise SystemExit("fineweb 미완 — gate 불가")
    # 부분 파일 → 단일 gz(멀티멤버 결합 = 유효 gzip)
    with open(OUT / "docs_fineweb.jsonl.gz", "wb") as w:
        for p in sorted(glob.glob(str(FW_PARTS / "*.jsonl.gz"))):
            with open(p, "rb") as r:
                shutil.copyfileobj(r, w)
    strata = {}
    samples = []
    for name in ("state_fresh.json", "state_sao.json"):
        s = json.loads((OUT / name).read_text())
        for k, v in s["층"].items():
            strata[k] = [strata.get(k, [0, 0, 0])[i] + v[i] for i in range(3)]
        samples.extend(s["표본"])
    for k, v in stf["층"].items():
        strata[k] = [strata.get(k, [0, 0, 0])[i] + v[i] for i in range(3)]
    samples.extend(Reservoir(stf["표본"]).final())
    table, quarantine = {}, []
    for k in sorted(strata):
        n, a, b = strata[k]
        arate = a / n if n else None
        brate = b / n if n else None
        tier = k.split("|")[1]
        verdicts = []
        if n < 30:
            verdicts.append("표본부족(n<30) — 미판정")
        else:
            if arate is not None and arate > A_CAP:
                verdicts.append("A>10% 격리")
            if tier == "T2" and brate is not None and brate > B_CAP_T2:
                verdicts.append("T2 B>85% 격리")
        if any("격리" in v for v in verdicts):
            quarantine.append(k)
        table[k] = {"n부착": n, "A": a, "B": b,
                    "A율": round(arate, 4) if arate is not None else None,
                    "B율": round(brate, 4) if brate is not None else None,
                    "판정": verdicts or ["통과"]}
    out = {"층표": table, "격리": quarantine, "상한": {"A": A_CAP, "T2_B": B_CAP_T2},
           "표본수": len(samples)}
    json.dump(out, open(OUT / "fp_gate1024.json", "w"), ensure_ascii=False, indent=1)
    with gzip.open(OUT / "fp_samples.jsonl.gz", "wt", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    _prog(단계="gate", 격리=quarantine, 층수=len(table))
    print(json.dumps(out["층표"], ensure_ascii=False, indent=1))
    print("격리:", quarantine)


# ── §5·§6 index ─────────────────────────────────────────────────────────────
def _iter_docs(engine_only=True):
    files = ["docs_fresh.jsonl.gz", "docs_sao.jsonl.gz", "docs_fineweb.jsonl.gz"]
    if not engine_only:
        files += ["docs_fresh_nopub.jsonl.gz", "docs_sao_nopub.jsonl.gz"]
    for fn in files:
        p = OUT / fn
        if not p.exists():
            continue
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for ln in f:
                yield json.loads(ln)


def stage_index():
    gate = json.loads((OUT / "fp_gate1024.json").read_text())
    quar = set(gate["격리"])
    panel = load_panel()
    epoch = dt.date(1970, 1, 1)

    def build(net):
        ent_dates = collections.defaultdict(list)
        ent_src = collections.defaultdict(collections.Counter)
        g4_null = g4_diff = 0
        seen_docs = set()
        for r in _iter_docs(engine_only=True):
            dk = r["원천"] + "|" + r["doc"]
            if dk in seen_docs:          # 하드킬 재개 시 RG 중복 방어
                continue
            seen_docs.add(dk)
            if r["층"] != "엔진" or not r["published_at"]:
                g4_null += 1
                continue
            diff = r.get("차이일")
            lim = FRESH_DIFF_MAX if r["원천"] == "fresh" else 0
            if diff is not None and diff > lim:
                g4_diff += 1
                continue
            if net and r.get("catalog"):
                continue
            d = parse_date(r["published_at"])
            if d is None:
                g4_null += 1
                continue
            dd = (d - epoch).days
            for key, tier, cls, b, a in r["부착"]:
                if net and ("%s|T%d" % (r["원천"], tier)) in quar:
                    continue
                ent_dates[key].append(dd)
                ent_src[key]["%s|T%d" % (r["원천"], tier)] += 1
        return ent_dates, ent_src, g4_null, g4_diff

    net_d, net_s, g4n, g4d = build(net=True)
    gross_d, _, _, _ = build(net=False)
    with gzip.open(OUT / "entity_pub_dates.jsonl.gz", "wt", encoding="utf-8") as f:
        for key in sorted(net_d):
            ds = sorted(net_d[key])
            f.write(json.dumps(
                {"키": key, "도메인": panel[key]["dom"], "n": len(ds),
                 "원천티어": dict(net_s[key]),
                 "dates": [(epoch + dt.timedelta(days=x)).isoformat() for x in ds]},
                ensure_ascii=False) + "\n")

    def stats(ed):
        cov = len(ed)
        ns = sorted(len(v) for v in ed.values())
        med = ns[len(ns) // 2] if ns else 0
        return cov, med

    cov_net, med_net = stats(net_d)
    cov_g, med_g = stats(gross_d)
    # G1·재시험 입구 — 1022 동결 val 격자
    val = []
    for ln in gzip.open(PAIRS_1022, "rt", encoding="utf-8"):
        r = json.loads(ln)
        if r["분할"] == "val":
            val.append((r["개체"], parse_date(r["t"])))
    import bisect
    net_sorted = {k: sorted(v) for k, v in net_d.items()}
    gross_sorted = {k: sorted(v) for k, v in gross_d.items()}
    n_cov = n_cov_g = 0
    npre = []
    ent_val_cov = set()
    for key, t in val:
        ds = net_sorted.get(key)
        td = (t - epoch).days
        k = bisect.bisect_left(ds, td) if ds else 0
        if ds and k > 0:
            n_cov += 1
            ent_val_cov.add(key)
        dg = gross_sorted.get(key)
        if dg and bisect.bisect_left(dg, td) > 0:
            n_cov_g += 1
        npre.append(k)
    npre_pos = sorted(x for x in npre if x > 0)
    se_est = SE_BASE * (N_BASE / n_cov) ** 0.5 if n_cov else None
    doms_cov = collections.Counter(panel[k]["dom"] for k in net_d)
    doms_all = collections.Counter(v["dom"] for v in panel.values())
    meta = {
        "G1": {"val쌍": len(val), "유문서쌍(순)": n_cov, "유문서쌍(격리전)": n_cov_g,
               "비율": round(n_cov / len(val), 4) if val else None,
               "기준선": 0.134, "겨냥": 0.50, "판정": None,
               "유문서 val개체": len(ent_val_cov)},
        "G2": {"유문서 개체(순)": cov_net, "개체당 중앙(순)": med_net,
               "격리·카탈로그 전(gross)": {"개체": cov_g, "중앙": med_g},
               "기준선 중앙": 3, "겨냥": 30, "판정": None,
               "개체 덮개율(순)": round(cov_net / len(panel), 4)},
        "G3": {"격리": gate["격리"], "층표": gate["층표"]},
        "G4": {"엔진층 pub null": g4n, "차이일 위반": g4d, "판정": None},
        "재시험입구": {"n'": n_cov, "1022 기준": N_BASE,
                       "배율": round(n_cov / N_BASE, 2),
                       "n_pre 중앙(유문서쌍)": npre_pos[len(npre_pos) // 2] if npre_pos else 0,
                       "SE 산술환산": se_est, "MDE 환산": 2 * se_est if se_est else None,
                       "1022 선계산 MDE": 0.00034},
        "도메인별 유문서 개체": {d: [doms_cov.get(d, 0), doms_all[d]] for d in DOMS},
    }
    ladder = {}
    for name in ("state_fresh.json", "state_sao.json"):
        p = OUT / name
        if p.exists():
            ladder[name] = json.loads(p.read_text())["agg"]
    stf = json.loads((OUT / "state_fineweb.json").read_text())
    ladder["fineweb"] = {k: stf[k] for k in
                         ("스캔", "dated행", "문서", "부착", "카탈로그", "T3기각")}
    ladder["fineweb_pub계수"] = stf["계수"]
    meta["사다리"] = ladder
    meta["G1"]["판정"] = "통과" if meta["G1"]["비율"] is not None and meta["G1"]["비율"] >= 0.50 else "미달"
    meta["G2"]["판정"] = "통과" if med_net >= 30 else "미달"
    meta["G4"]["판정"] = "통과" if (g4n == 0 and g4d == 0) else "위반"
    assert g4n == 0 and g4d == 0, "G4 위반 — 엔진층 시간표 규격"
    # 시대 sha
    shas = {"panel": {d: _sha16(PANEL_DIR / (d + ".jsonl.gz")) for d in DOMS},
            "sao_pub_v1": _sha16(SAO_PUB_V1), "sao_pub_v2": _sha16(SAO_PUB_V2),
            "pairs_1022": _sha16(PAIRS_1022),
            "ledger": _sha16(LEDGER) if LEDGER.exists() else None,
            "러너": _sha16(__file__)}
    meta["시대sha16"] = shas
    meta["끝시각"] = dt.datetime.now().isoformat(timespec="seconds")
    json.dump(meta, open(OUT / "meta1024.json", "w"), ensure_ascii=False, indent=1)
    _prog(단계="index", G1=meta["G1"]["비율"], G2중앙=med_net, 개체덮개=meta["G2"]["개체 덮개율(순)"],
          재시험n=n_cov)
    print(json.dumps(meta, ensure_ascii=False, indent=1)[:4000])


# ── selftest ────────────────────────────────────────────────────────────────
def stage_selftest():
    ents = {
        "T-LONG": {"dom": "웹툰", "w": "가나다라마바 (웹툰)", "ptoks": ["웹툰"],
                   "vars": [{"v": "가나다라마바 (웹툰)", "cls": "full", "tier": 1},
                            {"v": "가나다라마바", "cls": "base", "tier": 1}]},
        "T-MED": {"dom": "게임", "w": "가람나무", "ptoks": [],
                  "vars": [{"v": "가람나무", "cls": "base", "tier": 2}]},
        "T-SHORT": {"dom": "아이돌", "w": "손별 (그룹)", "ptoks": ["그룹"],
                    "vars": [{"v": "손별", "cls": "base", "tier": 3}]},
        "T-LAT": {"dom": "아이돌", "w": "IVE", "ptoks": [],
                  "vars": [{"v": "IVE", "cls": "base", "tier": 2}]},
        "T-NSP": {"dom": "만화", "w": "마루 아래 거인", "ptoks": [],
                  "vars": [{"v": "마루 아래 거인", "cls": "base", "tier": 1},
                           {"v": "마루아래거인", "cls": "nospace", "tier": 2}]},
    }
    m = Matcher(ents)
    ok = []

    def chk(name, cond):
        ok.append((name, bool(cond)))

    h, _ = m.match(*2 * (norm_fold("오늘 가나다라마바 3화가 올라왔다"),))
    chk("① T1 참 매칭", "T-LONG" in h and h["T-LONG"][0] == 1)
    h, _ = m.match(*2 * (norm_fold("신작 가람나무 리뷰"),))
    chk("① T2 참 매칭", "T-MED" in h)
    t = norm_nfc("Well DRIVE fast and give me time")
    h, _ = m.match(t, t.casefold())
    chk("② 라틴 L≤4 대소문자·경계", "T-LAT" not in h)
    t = norm_nfc("그룹 IVE 컴백 무대")
    h, _ = m.match(t, t.casefold())
    chk("② 라틴 정상 매칭", "T-LAT" in h)
    t = norm_fold("최고수준의 가람나무 전략")
    h, _ = m.match(t, t)
    chk("③ 한글 파묻힘 fpA=0(가람나무 앞 공백)", h["T-MED"][3] == 0)
    t = norm_fold("일류가람나무라는 합성어")
    h, _ = m.match(t, t)
    chk("③ 한글 앞붙음 fpA=1", "T-MED" in h and h["T-MED"][3] == 1)
    t = norm_fold("손별이라는 말이 문맥 없이 나온다")
    h, n3 = m.match(t, t)
    chk("④ T3 무문맥 기각", "T-SHORT" not in h and n3 >= 1)
    t = norm_fold("그룹 손별이 데뷔 무대를 가졌다")
    h, _ = m.match(t, t)
    chk("④ T3 유문맥 부착", "T-SHORT" in h)
    t = norm_fold("만화 마루아래거인 단행본")
    h, _ = m.match(t, t)
    chk("⑦ nospace 변형", "T-NSP" in h and h["T-NSP"][0] == 2)
    d, src = fresh_pub({"pub_time": "1970-01-01T09:00:00+09:00"},
                       {"published_at": None}, dt.date(2026, 8, 24))
    chk("⑤ 에포크 발행일 → null층", d is None)
    d, src = fresh_pub({"pub_time": "2026-09-30T00:00:00Z"}, {}, dt.date(2026, 8, 24))
    chk("⑤ 미래 발행일(>crawl+2) → null층", d is None)
    d, src = fresh_pub({"pub_time": "2026-08-23T10:00:00Z"}, {}, dt.date(2026, 8, 24))
    chk("⑤ 정상 발행일 채택", d == dt.date(2026, 8, 23))
    n = 1000
    a20 = {"n부착": n, "A": 200, "B": 0}
    a05 = {"n부착": n, "A": 50, "B": 0}
    chk("⑥ 합성 A율 20% → 격리", (a20["A"] / n) > A_CAP)
    chk("⑥ 합성 A율 5% → 통과", (a05["A"] / n) <= A_CAP)
    allok = all(x[1] for x in ok)
    out = {"검사": [{"이름": k, "통과": v} for k, v in ok], "전부통과": allok}
    json.dump(out, open(OUT / "selftest1024.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if not allok:
        raise SystemExit("방향 탐침 실패 — 측정 없이 중단")


def load_ents():
    ents = {}
    for ln in gzip.open(OUT / "names1024.jsonl.gz", "rt", encoding="utf-8"):
        r = json.loads(ln)
        ents[r["키"]] = {"dom": r["dom"], "w": r["w"], "vars": r["vars"],
                         "ptoks": r["ptoks"]}
    return ents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["selftest", "names", "fresh", "sao", "fineweb", "gate", "index"])
    ap.add_argument("--max-seconds", type=float, default=480)
    a = ap.parse_args()
    _prog(단계=a.stage, 무엇="시작")
    if a.stage == "selftest":
        stage_selftest()
    elif a.stage == "names":
        build_names(write=True)
    elif a.stage == "fresh":
        stage_fresh(load_ents())
    elif a.stage == "sao":
        stage_sao(load_ents())
    elif a.stage == "fineweb":
        stage_fineweb(load_ents(), a.max_seconds)
    elif a.stage == "gate":
        stage_gate()
    elif a.stage == "index":
        stage_index()
    _prog(단계=a.stage, 무엇="끝")


if __name__ == "__main__":
    main()
