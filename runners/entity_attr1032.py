# -*- coding: utf-8 -*-
"""사이클 1032 — 개체 귀속(entity attribution) 수리: 전거 v3 + [해석] 판독 심판.

사전등록 docs/탐색/1032.md — 이 러너는 사전등록 커밋 직후 언다(조항 66 — 주행 중 수정 금지).
단계:
  --stage selftest   방향 탐침 4 + MDE 시작 관문(부칙 6 ㉰) + 규칙 합성 탐침 + 사다리 항등
  --stage split      개발/시험 분할(씨앗 1032) · 신규표본 240(씨앗 10321) · 보충 97 판독지
  --stage authority  전거 v3 위키 API 수집(장주행 · 체크포인트 · 간격 ≥1.1초)
  --stage dev        인자 격자 24 · 개발셋만 · 선택 규칙(§2-3) — 시험 id 무접촉
  --stage read       [해석] 판독 ⓒ·ⓓ·지터(claude -p · 호출 상한 1,400 강제)
  --stage judge      시험셋·신규표본 채점 · 붓스트랩 SE · MDE · 게이트
  --stage v2         (통과 시) 원장 v2 후보 재구축 + 거짓률 사영 재검

위생: CPU ≤4스레드 · 무거운 국면 전 load1>10 → 60초 재잼(until) · MPS 0 · 전 입력 읽기 전용
      (1028 v1 산출 무수정) · 산출은 wm_harvest/foundation/entity_authority(조항 73-마) ·
      콘텐츠 위생(실명·스니펫은 파일 안에만).
"""
import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMP_NUM_THREADS", "4")

FND = Path("/Users/ax/wm_harvest/foundation")
V1 = FND / "event_ledger/v1"
ENT = FND / "entity_docs"
OUT = FND / "entity_authority"
OUT.mkdir(parents=True, exist_ok=True)
V2 = OUT / "v2"

DOC = ROOT / "docs/탐색/1032.md"
STATE = OUT / "state1032.json"
PROG = OUT / "progress1032.jsonl"
SPLIT = OUT / "split1032.json"
NEWS = OUT / "newsample1032.jsonl.gz"
GOLD_SUPP = OUT / "gold_supp.jsonl"
GOLD_SUPP_TASK = OUT / "gold_supp_task.jsonl"
GOLD_NEW = {1: OUT / "gold_new_pass1.jsonl", 2: OUT / "gold_new_pass2.jsonl",
            3: OUT / "gold_new_adjud.jsonl"}
ACACHE = OUT / "authority_cache.jsonl.gz"
ASTATE = OUT / "authority_state.json"
AUTH = OUT / "authority_v3.jsonl.gz"
DEVGRID = OUT / "devgrid1032.json"
SCORE = OUT / "score1032.json"

# ── 등록 상수(§1~§3) ─────────────────────────────────────────────────────
SEED_SPLIT = 1032
SEED_NEW = 10321
SEED_NEWSHUF = 103210
SEED_BOOT = 1032
DEV_FRAC = 0.6
NEW_N = 60                       # 신뢰층 4층 × 60 = 240
BOOT_B = 10000
D_GRID = [80, 150, 250, 400, 800, 10 ** 9]       # ∞ = 10^9
D_NEAR = 80
SUF_WIN = 8
B6_GRID = [False, True]
B2_SCOPE_GRID = ["전층", "E3만"]
RECALL_FLOOR = 0.70
FALSE_CAP = 0.15                 # §4-2 거짓률 재검 문턱
CALL_CAP_TOTAL = 1400
CALL_CAPS = [("c_test", 200), ("d_test", 347), ("c_new", 150), ("d_new", 240),
             ("jit", 63), ("c_dev", 200), ("d_dev", 200)]
JIT_N = 21                       # 지터 63호출 = 21행 × 3회
MDE_REG = 0.11221                # §3 등록값(시험셋)
MDE_REG_NEW = 0.10696            # §3 등록값(신규표본)
AIM = 0.2500
SE_A_REG, SE_C_REG, SE_D_REG = 0.03354, 0.04498, 0.05611
MDE_SRC_SHA = "ece3bf7952ea975b"   # state1028.json sha16 — 생존층분모(눈금 분모) 출처
ZONE_PROMPT = 1200               # 판독 프롬프트 문서 길이
UA = "world-model-lab/1032 (research; contact alexlee@sweetspot.co.kr)"
API_GAP = 1.1
NEWS_STRATA = ["E1", "E2모호", "E2미해소", "E3"]

RE_HAN = re.compile(r"[가-힣]")
RE_SUF = re.compile(r"^\s*(모바일|온라인|리부트|리마스터|리메이크|제로|외전|극장판"
                    r"|시즌\s*\d|\d+(?![년월일])|[IVX]{1,3}(?![A-Za-z]))")
RE_JOSA = re.compile(r"^\s*(은|는|이|가|의|을|를|와|과|도|사|측)")
RE_SENT = re.compile(r"[.!?\n]")


def _log(**kw):
    kw["t"] = dt.datetime.now().isoformat(timespec="seconds")
    line = json.dumps(kw, ensure_ascii=False)
    with open(PROG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def load1_gate(cap=10.0):
    while True:
        try:
            l1 = os.getloadavg()[0]
        except OSError:
            return
        if l1 <= cap:
            return
        _log(단계="load1관문", load1=round(l1, 2), 대기="60s")
        time.sleep(60)


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def code_stamp():
    return {"러너sha256": _sha256(__file__),
            "입력sha16": {n: _sha256(p)[:16] for n, p in [
                ("g1p_sample", V1 / "g1p_sample.jsonl.gz"),
                ("rows_ruled", V1 / "rows_ruled.jsonl.gz"),
                ("zones1028", V1 / "zones1028.jsonl.gz"),
                ("state1028", V1 / "state1028.json"),
                ("names1024", ENT / "names1024.jsonl.gz")]},
            "시각": dt.datetime.now().isoformat(timespec="seconds")}


def st_load():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def st_save(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


# ── 정규화 ───────────────────────────────────────────────────────────────
def norm_keep(s):
    """NFC + 길이보존 소문자화(등록 §2-2 부분열 탐색용 — 위치 사상 보존)."""
    s = unicodedata.normalize("NFC", s)
    out = []
    for ch in s:
        c = ch.lower()
        out.append(c if len(c) == 1 else ch)
    return "".join(out)


def is_han(s):
    return bool(RE_HAN.search(s))


# ── 1028 자료 재구성 ─────────────────────────────────────────────────────
_CACHE = {}


def load_world():
    """생존 배정행 전량 + zone + 1028 표본/라벨. 결정론 · 읽기 전용."""
    if "w" in _CACHE:
        return _CACHE["w"]
    import runners.event_refine1028 as e28
    import runners.event_ledger1026 as e26
    load1_gate()
    rows, ladder, wmap = e28.consumed_rows()
    ruled = {}
    for line in gzip.open(V1 / "rows_ruled.jsonl.gz", "rt", encoding="utf-8"):
        o = json.loads(line)
        ruled[(o["출처군"], o["문서id"], o["event_time"], o["event_type"])] = o
    zones = {}
    for line in gzip.open(V1 / "zones1028.jsonl.gz", "rt", encoding="utf-8"):
        o = json.loads(line)
        zones[(o["src"], o["doc"])] = o["zone"]
    alive = []
    for key in sorted(rows):
        r = rows[key]
        rec = ruled[(r["_src"], r["문서id"], r["event_time"], r["event_type"])]
        if rec["판정"] != "생존":
            continue
        norm = e26.TYPE_MAP.get(r["event_type"], "기타")
        grp = e26.TYPE_GROUP.get(norm, "기타")
        for ax, k, tier, nm in r["_asg"]:
            alive.append({
                "rowid": "|".join([r["_src"], r["문서id"], r["event_time"],
                                   r["event_type"], ax]),
                "출처군": r["_src"], "문서id": r["문서id"], "event_time": r["event_time"],
                "원유형": r["event_type"], "정규유형": norm, "층": r["_src"] + "|" + grp,
                "ax": ax, "키": k, "신뢰층": tier, "개체원명": nm,
                "위키문서": wmap.get(k) if k else None,
                "스팬": rec["스팬"], "pub_time": r["pub_time"], "날짜꼴": r["날짜꼴"],
                "conf": r["conf"]})
    assert len(alive) == 28835, "생존 배정행 %d ≠ 28835" % len(alive)
    docent = collections.defaultdict(set)
    for a in alive:
        docent[(a["출처군"], a["문서id"])].add(a["ax"])
    for a in alive:
        a["문서내개체수"] = len(docent[(a["출처군"], a["문서id"])])
    _CACHE["w"] = (alive, zones, wmap, ladder)
    return _CACHE["w"]


def sample865():
    """1028 표본 865 + 최종 라벨(일치 또는 3차)."""
    S = [json.loads(l) for l in gzip.open(V1 / "g1p_sample.jsonl.gz", "rt", encoding="utf-8")]
    L1 = {json.loads(l)["id"]: json.loads(l) for l in open(V1 / "g1p_labels_pass1.jsonl", encoding="utf-8")}
    L2 = {json.loads(l)["id"]: json.loads(l) for l in open(V1 / "g1p_labels_pass2.jsonl", encoding="utf-8")}
    AD = {json.loads(l)["id"]: json.loads(l) for l in open(V1 / "g1p_labels_adjud.jsonl", encoding="utf-8")}
    fin = {}
    for o in S:
        i = o["id"]
        fin[i] = AD[i] if i in AD else (L1[i] if L1[i]["라벨"] == L2[i]["라벨"] else None)
        assert fin[i] is not None, "1028 라벨 미해소 %s" % i
        o["ax"] = o["개체키"] or ("raw:" + o["개체원명"].casefold())
        o["rowid"] = "|".join([o["출처군"], o["문서id"], o["event_time"], o["원유형"], o["ax"]])
        o["_1028"] = fin[i]
    return S


def gold_map(S):
    """§1-2 축 사영 + §1-3 보충. 반환 id→'참'/'거짓'/'미판정'/None(보충 미완)."""
    supp = {}
    if GOLD_SUPP.exists():
        for l in open(GOLD_SUPP, encoding="utf-8"):
            o = json.loads(l)
            supp[o["id"]] = o["귀속"]
    g = {}
    for o in S:
        lab, sub = o["_1028"]["라벨"], o["_1028"]["부표"]
        if lab == "참":
            g[o["id"]] = "참"
        elif lab == "거짓" and sub == "ⓔ":
            g[o["id"]] = "거짓"
        else:
            g[o["id"]] = supp.get(o["id"])
    return g


# ── 전거 v3 ──────────────────────────────────────────────────────────────
_LASTCALL = [0.0]


def api(lang, params, tries=3):
    p = dict(params)
    p.update({"action": "query", "format": "json", "formatversion": "1", "maxlag": "5"})
    url = "https://%s.wikipedia.org/w/api.php?%s" % (lang, urllib.parse.urlencode(p))
    for i in range(tries):
        gap = API_GAP - (time.time() - _LASTCALL[0])
        if gap > 0:
            time.sleep(gap)
        _LASTCALL[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
            if "error" in d:
                raise RuntimeError(str(d["error"])[:200])
            return d
        except Exception as e:            # noqa: BLE001
            if i == tries - 1:
                return {"_err": "%s: %s" % (type(e).__name__, str(e)[:200])}
            time.sleep(2.0 * (2 ** i))
    return {"_err": "unreachable"}


def cache_append(recs):
    with gzip.open(ACACHE, "at", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def authority():
    alive, zones, wmap, _ = load_world()
    names = {}
    for line in gzip.open(ENT / "names1024.jsonl.gz", "rt", encoding="utf-8"):
        o = json.loads(line)
        names[o["키"]] = o
    keys = sorted({a["키"] for a in alive if a["키"]})
    raws = sorted({a["개체원명"] for a in alive if not a["키"] and a["개체원명"]})
    var_of = {}
    for k in keys:
        var_of[k] = [v["v"] for v in names[k]["vars"]]
    allvars = sorted({v for k in keys for v in var_of[k]} | set(raws))
    st = json.loads(ASTATE.read_text(encoding="utf-8")) if ASTATE.exists() else {
        "A1": {}, "A2": {}, "A3": {}, "A4": {}, "done": [], "calls": 0, "err": 0}
    _log(단계="authority", 키=len(keys), raw=len(raws), 변형=len(allvars),
         이미={k: len(st[k]) for k in ("A1", "A2", "A3", "A4")})

    # A1/A2 — 표제어 배치(50)
    titles = [names[k]["w"] for k in keys]
    todo = [t for t in titles if t not in st["A1"]]
    for i in range(0, len(todo), 50):
        batch = todo[i:i + 50]
        for lang in ("ko", "en"):
            miss = [t for t in batch if t not in st["A1"]]
            if not miss:
                break
            d = api(lang, {"prop": "redirects|langlinks", "titles": "|".join(miss),
                           "rdlimit": "max", "rdnamespace": "0",
                           "lllimit": "max", "lllang": "ko"})
            st["calls"] += 1
            if "_err" in d:
                st["err"] += 1
                continue
            cache_append([{"call": "A1A2", "lang": lang, "titles": miss, "resp": d}])
            for pg in d.get("query", {}).get("pages", []):
                t = pg.get("title")
                if "missing" in pg:
                    continue
                st["A1"][t] = sorted({r["title"] for r in pg.get("redirects", [])})
                st["A2"][t] = sorted({ll.get("*") or ll.get("title") or ""
                                      for ll in pg.get("langlinks", [])} - {""})
            for t in d.get("query", {}).get("normalized", []):
                pass
        ASTATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        _log(단계="authority/A1A2", 진행="%d/%d" % (min(i + 50, len(todo)), len(todo)),
             호출=st["calls"])

    # A3/A4 — 변형별 막음 후보
    for j, v in enumerate(allvars):
        if v in st["A3"] and v in st["A4"]:
            continue
        lang = "ko" if is_han(v) else "en"
        if v not in st["A3"]:
            d = api(lang, {"list": "allpages", "apprefix": v, "aplimit": "500",
                           "apnamespace": "0", "apfilterredir": "all"})
            st["calls"] += 1
            if "_err" in d:
                st["err"] += 1
                st["A3"][v] = []
            else:
                cache_append([{"call": "A3", "lang": lang, "v": v, "resp": d}])
                st["A3"][v] = sorted({p["title"] for p in d.get("query", {}).get("allpages", [])})
        if v not in st["A4"]:
            d = api(lang, {"list": "search", "srsearch": 'intitle:"%s"' % v,
                           "srlimit": "50", "srnamespace": "0"})
            st["calls"] += 1
            if "_err" in d:
                st["err"] += 1
                st["A4"][v] = []
            else:
                cache_append([{"call": "A4", "lang": lang, "v": v, "resp": d}])
                st["A4"][v] = sorted({p["title"] for p in d.get("query", {}).get("search", [])})
        if j % 25 == 0:
            ASTATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
            _log(단계="authority/A3A4", 진행="%d/%d" % (j, len(allvars)),
                 호출=st["calls"], 오류=st["err"])
            load1_gate()
    ASTATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    build_authority(st, keys, raws, var_of, names)


def build_authority(st, keys, raws, var_of, names):
    """ALIAS/BLOCK 사전 확정(§2-1)."""
    import runners.entity_join1024 as e24
    ban = set(getattr(e24, "BAN_COMMON", set()))
    n_alias = n_block = 0
    with gzip.open(AUTH, "wt", encoding="utf-8") as f:
        for k in keys:
            w = names[k]["w"]
            base_vars = list(var_of[k])
            red = st["A1"].get(w, [])
            lang = st["A2"].get(w, [])
            alias = []
            seen = set()
            for v in base_vars + red + lang:
                v2 = unicodedata.normalize("NFC", (v or "")).strip()
                if len(v2.replace(" ", "")) < 2 or v2.replace(" ", "").isdigit():
                    continue
                if v2 in ban:
                    continue
                if v2.casefold() in seen:
                    continue
                seen.add(v2.casefold())
                alias.append(v2)
            redset = {r.casefold() for r in red} | {w.casefold()}
            block = set()
            for v in base_vars:
                cand = set(st["A3"].get(v, [])) | set(st["A4"].get(v, []))
                vl = v.casefold()
                for T in cand:
                    Tl = T.casefold()
                    if Tl in redset or Tl == vl:
                        continue
                    if vl in Tl and len(Tl) > len(vl):
                        block.add(T)
            n_alias += len(alias)
            n_block += len(block)
            f.write(json.dumps({"키": k, "w": w, "alias": alias,
                                "block": sorted(block)}, ensure_ascii=False) + "\n")
        for nm in raws:
            cand = set(st["A3"].get(nm, [])) | set(st["A4"].get(nm, []))
            nl = nm.casefold()
            block = sorted({T for T in cand if nl in T.casefold() and len(T) > len(nm)})
            f.write(json.dumps({"키": None, "raw": nm, "alias": [nm],
                                "block": block}, ensure_ascii=False) + "\n")
    _log(단계="authority/사전", 키=len(keys), raw=len(raws),
         별칭합=n_alias, 막음합=n_block, 호출=st["calls"], 오류=st["err"])


def load_authority():
    A = {}
    R = {}
    for line in gzip.open(AUTH, "rt", encoding="utf-8"):
        o = json.loads(line)
        if o.get("키"):
            A[o["키"]] = o
        else:
            R[o["raw"]] = o
    return A, R


# ── ⓑ 전거 v3 규칙 ───────────────────────────────────────────────────────
def variants_for(a, A, R):
    if a["키"]:
        o = A.get(a["키"])
        vs = list(o["alias"]) if o else []
        if a["개체원명"]:
            vs = [a["개체원명"]] + [v for v in vs if v != a["개체원명"]]
        return vs, (o["block"] if o else [])
    nm = a["개체원명"] or ""
    o = R.get(nm)
    return ([nm] if nm else []), (o["block"] if o else [])


def occurrences(zl, zone, v):
    """v 의 (경계 통과 여부, 위치) 목록. 길이보존 소문자 zl 에서 탐색."""
    vl = norm_keep(v)
    if not vl:
        return []
    out = []
    st = 0
    while True:
        p = zl.find(vl, st)
        if p < 0:
            break
        st = p + 1
        ok = True
        if is_han(v):
            if p > 0 and RE_HAN.match(zone[p - 1] if p - 1 < len(zone) else " "):
                ok = False
        else:
            for q in (p - 1, p + len(vl)):
                if 0 <= q < len(zone) and re.match(r"[A-Za-z0-9]", zone[q]):
                    ok = False
            if len(v.replace(" ", "")) <= 4 and zone[p:p + len(vl)] != v:
                ok = False
        out.append((ok, p, len(vl), v))
    return out


def eval_row(a, zone, zl, A, R, D, b6, b2scope):
    """행 하나에 ⓑ 규칙 적용 → (keep, 사유, dist, tier변형, 애매여부)."""
    vs, block = variants_for(a, A, R)
    s, e, vs_, ve = a["스팬"]
    cands = []
    for v in vs:
        for ok, p, L, vv in occurrences(zl, zone, v):
            dist = max(0, s - (p + L), p - e)
            cands.append((dist, not ok, p, L, vv))
    if not cands:
        return 0, "재정위실패", None, None, False
    cands.sort()
    # B4: 경계 통과 출현 우선(같은 거리대) — 통과분 중 최근접, 없으면 전체 최근접
    okc = [c for c in cands if not c[1]]
    pick = okc[0] if okc else cands[0]
    dist, bad, p, L, vv = pick
    reasons = []
    if bad:
        reasons.append("B1")
    # B3 동음이의 접미
    suf = zone[p + L:p + L + SUF_WIN]
    if RE_SUF.match(suf):
        reasons.append("B3")
    # B2 부분열 차단(막음 사전) — 키 있는 층만(§6) · 적용층 인자
    use_b2 = bool(a["키"]) and (b2scope == "전층" or a["신뢰층"] == "E3")
    if use_b2 and block:
        vl = norm_keep(vv)
        for T in block:
            Tl = norm_keep(T)
            if vl not in Tl:
                continue
            q = zl.find(Tl)
            while q >= 0:
                if q <= p and p + L <= q + len(Tl):
                    reasons.append("B2")
                    break
                q = zl.find(Tl, q + 1)
            if reasons and reasons[-1] == "B2":
                break
    # B5 주체 근접
    if dist > D:
        reasons.append("B5")
    # B6 주어 표지
    weak = False
    if b6:
        tail = zone[p + L:p + L + 6]
        head = zone[:p]
        m = RE_SENT.search(head[::-1])
        at_head = (head.strip() == "") or (m is not None and head[len(head) - m.start():].strip() == "")
        weak = not (RE_JOSA.match(tail) or at_head)
        if weak and dist > D_NEAR:
            reasons.append("B6")
    keep = 0 if reasons else 1
    only_b5 = (reasons == ["B5"])
    amb = False
    if keep == 1 and (dist > D_NEAR or a["문서내개체수"] >= 2):
        amb = True
    if keep == 0 and only_b5:
        amb = True
    return keep, "+".join(reasons) if reasons else "유지", dist, vv, amb


def arm_b(rows, zones, A, R, D, b6, b2scope):
    out = {}
    for a in rows:
        zone = zones[(a["출처군"], a["문서id"])]
        zl = norm_keep(zone)
        out[a["rowid"]] = eval_row(a, zone, zl, A, R, D, b6, b2scope)
    return out


# ── 자(정밀도·재현율·F1) ─────────────────────────────────────────────────
def stratified_pr(items, weights):
    """items: [(층, gold, keep)] gold∈{'참','거짓'} · weights: 층→W."""
    per = collections.defaultdict(lambda: [0, 0, 0, 0])   # n, keep, keep∧참, 참
    for st, g, kp in items:
        c = per[st]
        c[0] += 1
        c[1] += kp
        c[2] += kp and g == "참"
        c[3] += (g == "참")
    tot = sum(weights[s] for s in per)
    if tot == 0:
        return None
    pn = pd = rn = rd = 0.0
    for s, c in per.items():
        w = weights[s] / tot
        pn += w * c[2] / c[0]
        pd += w * c[1] / c[0]
        rn += w * c[2] / c[0]
        rd += w * c[3] / c[0]
    P = pn / pd if pd > 0 else None
    Rc = rn / rd if rd > 0 else None
    F = (2 * P * Rc / (P + Rc)) if (P and Rc and P + Rc > 0) else None
    return {"정밀도": P, "재현율": Rc, "F1": F, "n": sum(c[0] for c in per.values()),
            "유지": sum(c[1] for c in per.values()), "참": sum(c[3] for c in per.values())}


def boot_delta(items_a, items_c, weights, B=BOOT_B, seed=SEED_BOOT):
    """층 내 행 붓스트랩 — 같은 재표집을 두 팔에 적용(쌍 상관 반영)."""
    by = collections.defaultdict(list)
    for i, (st, g, kp) in enumerate(items_a):
        by[st].append(i)
    rng = random.Random(seed)
    ds = []
    for _ in range(B):
        idx = []
        for st, ii in by.items():
            idx.extend(rng.choices(ii, k=len(ii)))
        ra = stratified_pr([items_a[i] for i in idx], weights)
        rc = stratified_pr([items_c[i] for i in idx], weights)
        if ra and rc and ra["정밀도"] is not None and rc["정밀도"] is not None:
            ds.append(rc["정밀도"] - ra["정밀도"])
    if not ds:
        return None
    m = sum(ds) / len(ds)
    sd = math.sqrt(sum((d - m) ** 2 for d in ds) / max(1, len(ds) - 1))
    ds.sort()
    return {"SE": sd, "평균": m, "ci95": [ds[int(0.025 * len(ds))], ds[int(0.975 * len(ds))]],
            "B": len(ds)}


# ── 판독 (claude -p) ─────────────────────────────────────────────────────
PROMPT = """아래는 한국어 웹문서의 앞부분이다. 물음 하나에만 답하라.
[문서]
{zone}
[개체] {ent}
[날짜] {date}   [사건유형] {ty}
물음: 이 문서는 «{ent}»을(를) 위 날짜의 «{ty}» 사건의 주체로 다루는가?
- 그 사건의 주체가 다른 개체(확장판·후속작·별개 작품, 그룹의 멤버 개인·유닛, 다른 회사·다른 IP)면 «아니오».
- 배경 언급·비교·목록 나열·유통사 언급뿐이면 «아니오».
답: 「예」 「아니오」 「모름」 중 낱말 하나만 출력하라.
"""


def make_prompt(a, zone):
    ent = a["개체원명"] or a["위키문서"] or ""
    return PROMPT.format(zone=zone[:ZONE_PROMPT], ent=ent,
                         date=a["event_time"], ty=a["정규유형"])


def parse_verdict(s):
    s = (s or "").strip()
    if "아니오" in s:
        return "아니오"
    if "모름" in s:
        return "모름"
    if "예" in s:
        return "예"
    return "파싱실패"


def call_claude(prompt, timeout=180):
    try:
        p = subprocess.run(["claude", "-p"], input=prompt.encode("utf-8"),
                           capture_output=True, timeout=timeout)
        return parse_verdict(p.stdout.decode("utf-8", "replace"))
    except Exception as e:      # noqa: BLE001
        return "파싱실패"


def read_batch(tag, rows, zones, cap, st, workers=4):
    """판독 실행 — 체크포인트(파일 append) · 전역 상한 강제."""
    path = OUT / ("verdicts_%s.jsonl" % tag)
    done = {}
    if path.exists():
        for l in open(path, encoding="utf-8"):
            o = json.loads(l)
            done[o["rowid"] + "#" + str(o.get("rep", 0))] = o["판정"]
    todo = [a for a in rows if (a["rowid"] + "#0") not in done]
    used = st.setdefault("calls", {})
    budget = min(cap - len(done), CALL_CAP_TOTAL - sum(used.values()))
    todo = todo[:max(0, budget)]
    _log(단계="read/" + tag, 대상=len(rows), 이미=len(done), 실행=len(todo),
         상한=cap, 전역사용=sum(used.values()))
    from concurrent.futures import ThreadPoolExecutor
    if todo:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(call_claude, make_prompt(a, zones[(a["출처군"], a["문서id"])])): a
                    for a in todo}
            from concurrent.futures import as_completed
            with open(path, "a", encoding="utf-8") as f:
                for i, fu in enumerate(as_completed(futs)):
                    a = futs[fu]
                    v = fu.result()
                    done[a["rowid"] + "#0"] = v
                    f.write(json.dumps({"rowid": a["rowid"], "rep": 0, "판정": v},
                                       ensure_ascii=False) + "\n")
                    f.flush()
                    if (i + 1) % 25 == 0:
                        _log(단계="read/" + tag, 진행="%d/%d" % (i + 1, len(todo)))
    used[tag] = len(done)
    st_save(st)
    return {k.split("#")[0]: v for k, v in done.items() if k.endswith("#0")}


# ── selftest ─────────────────────────────────────────────────────────────
def parse_doc_mde():
    """등록문 §3 의 MDE 칸 파싱(부칙 6 ㉰)."""
    txt = DOC.read_text(encoding="utf-8")
    got = {}
    for key, rx in (("SE_A", r"SE_ⓐ\s*([\d.]+)"), ("SE_C", r"SE_ⓒ\s*([\d.]+)"),
                    ("SE_D", r"SE_Δ\s*([\d.]+)"), ("MDE", r"MDE = 2×max\(SE_Δ, J\) = ([\d.]+)"),
                    ("AIM", r"겨냥 \|Δ\| = \+([\d.]+)"),
                    ("MDE_NEW", r"사전 MDE = \*\*([\d.]+)"),
                    ("RECALL", r"시험셋 재현율 ≥ ([\d.]+)"),
                    ("CAP", r"\*\*총 ([\d,]+)회\*\*")):
        m = re.search(rx, txt)
        got[key] = m.group(1).replace(",", "") if m else None
    return got


def mde_start_gate():
    from pretrain.mde_guard import assert_mde, mde_of
    g = parse_doc_mde()
    miss = [k for k, v in g.items() if v is None]
    if miss:
        raise SystemExit("🔴 등록문 MDE 칸 파싱 실패: %r — 측정 없이 중단" % miss)
    chk = {"SE_A": SE_A_REG, "SE_C": SE_C_REG, "SE_D": SE_D_REG, "MDE": MDE_REG,
           "AIM": AIM, "MDE_NEW": MDE_REG_NEW, "RECALL": RECALL_FLOOR,
           "CAP": CALL_CAP_TOTAL}
    bad = {k: (g[k], chk[k]) for k in chk if abs(float(g[k]) - float(chk[k])) > 1e-9}
    if bad:
        raise SystemExit("🔴 등록문↔러너 상수 불일치 %r — 측정 없이 중단(조항 66)" % bad)
    if abs(mde_of(SE_D_REG, 0.0) - MDE_REG) > 1e-5:
        raise SystemExit("🔴 MDE 산식 불일치 — 측정 없이 중단(부칙 6 ㉮)")
    stamp = assert_mde(MDE_REG, AIM, MDE_SRC_SHA)
    _log(단계="selftest/MDE관문", 판정="통과", **{k: str(v) for k, v in stamp.items()})
    return stamp


def _synth_rows(n, gold_true, keep_fn, layer="fineweb2|출시군"):
    return [(layer, "참" if gold_true(i) else "거짓", keep_fn(i)) for i in range(n)]


def selftest():
    fails = []
    stamp = mde_start_gate()
    W = {"fineweb2|출시군": 1000}
    # 탐침 ① 전 행 참 · 임의 차단 → 정밀도 1.0 · 재현율 < 1
    r = stratified_pr(_synth_rows(100, lambda i: True, lambda i: int(i % 3 != 0)), W)
    if not (abs(r["정밀도"] - 1.0) < 1e-9 and r["재현율"] < 1.0):
        fails.append("탐침① %r" % r)
    # 탐침 ② 전 행 거짓 · 전차단 → 재현율 정의불가
    r2 = stratified_pr(_synth_rows(50, lambda i: False, lambda i: 0), W)
    if r2["재현율"] is not None or r2["정밀도"] is not None:
        fails.append("탐침② %r" % r2)
    # 탐침 ③ ⓐ 재현율 ≡ 1.0
    r3 = stratified_pr(_synth_rows(80, lambda i: i % 2 == 0, lambda i: 1), W)
    if abs(r3["재현율"] - 1.0) > 1e-9:
        fails.append("탐침③ %r" % r3)
    # 탐침 ④ keep 뒤집기 → Δ정밀도 부호 반대
    base = _synth_rows(120, lambda i: i % 4 != 0, lambda i: 1)
    good = _synth_rows(120, lambda i: i % 4 != 0, lambda i: int(i % 4 != 0))
    bad = _synth_rows(120, lambda i: i % 4 != 0, lambda i: int(i % 4 == 0))
    dg = stratified_pr(good, W)["정밀도"] - stratified_pr(base, W)["정밀도"]
    db = stratified_pr(bad, W)["정밀도"] - stratified_pr(base, W)["정밀도"]
    if not (dg > 0 > db):
        fails.append("탐침④ %.4f/%.4f" % (dg, db))

    # 규칙 합성 탐침 — 발화해야/하면 안 되는 예
    A = {"K1": {"키": "K1", "w": "마비노기", "alias": ["마비노기", "Mabinogi"],
                "block": ["마비노기 모바일", "마비노기 영웅전"]},
         "K2": {"키": "K2", "w": "에이티즈", "alias": ["에이티즈", "ATEEZ"], "block": []}}
    R = {"연기": {"raw": "연기", "alias": ["연기"], "block": []}}

    def mk(ax, key, nm, tier, span, docn=1):
        return {"rowid": "x", "출처군": "t", "문서id": "d", "event_time": "2024-01-01",
                "원유형": "출시", "정규유형": "출시", "층": "fineweb2|출시군", "ax": ax,
                "키": key, "신뢰층": tier, "개체원명": nm, "위키문서": None,
                "스팬": span, "pub_time": "2023-12-01", "날짜꼴": "절대_년월일",
                "문서내개체수": docn}
    cases = [
        # (이름, zone, 행, D, b6, 기대 keep, 기대 사유 포함)
        ("B2 확장판 차단", "마비노기 모바일이 1월 1일 출시된다.",
         mk("K1", "K1", "마비노기", "E3", [10, 15, 16, 18]), 400, False, 0, "B2"),
        ("B2 비발화(본편)", "마비노기가 1월 1일 업데이트를 출시한다.",
         mk("K1", "K1", "마비노기", "E3", [6, 11, 20, 22]), 400, False, 1, None),
        ("B1 합성어 파묻힘", "슈퍼마비노기라는 말이 1월 1일 나왔다.",
         mk("K1", "K1", "마비노기", "E1", [14, 19, 24, 26]), 400, False, 0, "B1"),
        ("B3 접미(표제어 없음)", "에이티즈 시즌 2 가 1월 1일 시작한다.",
         mk("K2", "K2", "에이티즈", "E1", [12, 17, 22, 24]), 400, False, 0, "B3"),
        ("B5 원거리 차단", "에이티즈" + "가" + " " * 300 + "1월 1일 출시.",
         mk("K2", "K2", "에이티즈", "E3", [305, 310, 311, 313]), 80, False, 0, "B5"),
        ("B5 근거리 유지", "에이티즈가 1월 1일 출시한다.",
         mk("K2", "K2", "에이티즈", "E3", [7, 12, 13, 15]), 80, False, 1, None),
        ("재정위 실패", "전혀 다른 문서다. 1월 1일.",
         mk("K2", "K2", "에이티즈", "E3", [12, 17, 18, 19]), 400, False, 0, "재정위실패"),
    ]
    for nm, zone, a, D, b6, exp_keep, exp_r in cases:
        keep, why, dist, vv, amb = eval_row(a, zone, norm_keep(zone), A, R, D, b6, "전층")
        if keep != exp_keep or (exp_r and exp_r not in why):
            fails.append("규칙탐침 %s → keep=%d why=%s" % (nm, keep, why))
    # 사다리 항등(1028 28,835)
    alive, zones, wmap, ladder = load_world()
    if len(alive) != 28835:
        fails.append("사다리 %d" % len(alive))
    tiers = collections.Counter(a["신뢰층"] for a in alive)
    exp_t = {"E1": 5726, "E2모호": 2976, "E2미해소": 7475, "E3": 12658}
    if dict(tiers) != exp_t:
        fails.append("신뢰층 %r" % dict(tiers))
    S = sample865()
    if len(S) != 865:
        fails.append("표본 %d" % len(S))
    aliveid = {a["rowid"] for a in alive}
    lost = [o["id"] for o in S if o["rowid"] not in aliveid]
    if lost:
        fails.append("표본 rowid 미대응 %d (%r)" % (len(lost), lost[:3]))
    if fails:
        _log(단계="selftest", 판정="실패", 실패=fails)
        raise SystemExit("🔴 selftest 실패 — 측정 없이 중단: %r" % fails)
    _log(단계="selftest", 판정="통과", 탐침=4, 규칙탐침=len(cases),
         생존배정행=len(alive), 표본=len(S), MDE=stamp)
    st = st_load()
    st["selftest"] = {"통과": True, "MDE": {k: str(v) for k, v in stamp.items()},
                      "규칙탐침": len(cases), "도장": code_stamp()}
    st_save(st)


# ── split ────────────────────────────────────────────────────────────────
def split():
    alive, zones, wmap, _ = load_world()
    S = sample865()
    by = collections.defaultdict(list)
    for o in S:
        by[o["층"]].append(o["id"])
    rng = random.Random(SEED_SPLIT)
    dev, test = {}, {}
    for stw in sorted(by):
        ids = sorted(by[stw])
        nd = int(round(len(ids) * DEV_FRAC))
        d = set(rng.sample(ids, nd))
        dev[stw] = sorted(d)
        test[stw] = [i for i in ids if i not in d]
    W = json.loads((V1 / "state1028.json").read_text(encoding="utf-8"))["rules"]["생존층분모"]
    SPLIT.write_text(json.dumps({"dev": dev, "test": test, "W": W, "씨앗": SEED_SPLIT},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    # 보충 판독지(97) — 귀속 축 전용
    smap = {o["id"]: o for o in S}
    need = [o for o in S if not (o["_1028"]["라벨"] == "참"
                                 or (o["_1028"]["라벨"] == "거짓" and o["_1028"]["부표"] == "ⓔ"))]
    arow = {a["rowid"]: a for a in alive}
    with open(GOLD_SUPP_TASK, "w", encoding="utf-8") as f:
        for o in sorted(need, key=lambda x: x["id"]):
            a = arow[o["rowid"]]
            zone = zones[(a["출처군"], a["문서id"])]
            f.write(json.dumps({"id": o["id"], "층": o["층"], "신뢰층": o["신뢰층"],
                                "개체": o["개체원명"] or o["위키문서"],
                                "위키문서": o["위키문서"], "event_time": o["event_time"],
                                "정규유형": o["정규유형"], "1028라벨": o["_1028"],
                                "zone": zone}, ensure_ascii=False) + "\n")
    # 신규 표본 240
    used = {o["rowid"] for o in S}
    pool = collections.defaultdict(list)
    for a in alive:
        if a["rowid"] in used:
            continue
        pool[a["신뢰층"]].append(a)
    rng2 = random.Random(SEED_NEW)
    items = []
    for tier in NEWS_STRATA:
        ps = sorted(pool[tier], key=lambda a: (a["문서id"], a["ax"], a["event_time"], a["정규유형"]))
        pick = ps if len(ps) <= NEW_N else rng2.sample(ps, NEW_N)
        pick = sorted(pick, key=lambda a: (a["문서id"], a["ax"], a["event_time"], a["정규유형"]))
        for a in pick:
            zone = zones[(a["출처군"], a["문서id"])]
            s, e, vs_, ve = a["스팬"]
            items.append({"id": "N%03d" % (len(items) + 1), "rowid": a["rowid"],
                          "신뢰층": tier, "층": a["층"], "출처군": a["출처군"],
                          "문서id": a["문서id"], "개체": a["개체원명"] or a["위키문서"],
                          "위키문서": a["위키문서"], "event_time": a["event_time"],
                          "정규유형": a["정규유형"], "원유형": a["원유형"],
                          "pub_time": a["pub_time"],
                          "스니펫": zone[max(0, s - 150):ve + 150], "zone": zone})
    with gzip.open(NEWS, "wt", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    order = [it["id"] for it in items]
    random.Random(SEED_NEWSHUF).shuffle(order)
    st = st_load()
    st["split"] = {"개발": sum(len(v) for v in dev.values()),
                   "시험": sum(len(v) for v in test.values()),
                   "보충대상": len(need), "신규표본": len(items),
                   "신규층별": dict(collections.Counter(i["신뢰층"] for i in items)),
                   "pass2_order": order}
    st_save(st)
    _log(단계="split", 개발=st["split"]["개발"], 시험=st["split"]["시험"],
         보충대상=len(need), 신규표본=len(items))


# ── dev ──────────────────────────────────────────────────────────────────
def _items(rows_by_id, ids, gold, keeps):
    out = []
    for i in ids:
        a = rows_by_id[i]
        g = gold.get(i)
        if g not in ("참", "거짓"):
            continue
        out.append((a["층"], g, keeps[a["rowid"]][0]))
    return out


def dev_stage():
    alive, zones, wmap, _ = load_world()
    S = sample865()
    sp = json.loads(SPLIT.read_text(encoding="utf-8"))
    W = sp["W"]
    gold = gold_map(S)
    devids = [i for v in sp["dev"].values() for i in v]
    smap = {o["id"]: o for o in S}
    arow = {a["rowid"]: a for a in alive}
    rows_by_id = {i: arow[smap[i]["rowid"]] for i in devids}
    A, R = load_authority()
    devrows = [rows_by_id[i] for i in devids]
    grid = []
    for D in D_GRID:
        for b6 in B6_GRID:
            for sc in B2_SCOPE_GRID:
                keeps = arm_b(devrows, zones, A, R, D, b6, sc)
                it = _items(rows_by_id, devids, gold, keeps)
                r = stratified_pr(it, W)
                grid.append({"D": D, "B6": b6, "B2층": sc, **{k: r[k] for k in
                            ("정밀도", "재현율", "F1", "n", "유지", "참")}})
    ok = [g for g in grid if g["재현율"] is not None and g["재현율"] >= RECALL_FLOOR
          and g["F1"] is not None]
    if not ok:
        pick = None
    else:
        pick = sorted(ok, key=lambda g: (-g["F1"], g["D"], g["B6"],
                                         0 if g["B2층"] == "off" else 1,
                                         0 if g["B2층"] == "전층" else 1))[0]
    # ⓐ 개발셋 기준선
    base = stratified_pr([(rows_by_id[i]["층"], gold[i], 1) for i in devids
                          if gold.get(i) in ("참", "거짓")], W)
    DEVGRID.write_text(json.dumps({"격자": grid, "선택": pick, "기준선ⓐ개발": base,
                                   "재현율하한": RECALL_FLOOR}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    st = st_load()
    st["dev"] = {"선택": pick, "기준선ⓐ개발": base, "격자수": len(grid)}
    st_save(st)
    _log(단계="dev", 격자=len(grid), 선택=pick, 기준선=base)


# ── read ─────────────────────────────────────────────────────────────────
def read_stage():
    alive, zones, wmap, _ = load_world()
    S = sample865()
    sp = json.loads(SPLIT.read_text(encoding="utf-8"))
    st = st_load()
    pick = st["dev"]["선택"]
    if not pick:
        raise SystemExit("🔴 dev 선택 없음 — read 불가")
    A, R = load_authority()
    smap = {o["id"]: o for o in S}
    arow = {a["rowid"]: a for a in alive}
    testids = [i for v in sp["test"].values() for i in v]
    devids = [i for v in sp["dev"].values() for i in v]
    news = [json.loads(l) for l in gzip.open(NEWS, "rt", encoding="utf-8")]
    sets = {
        "test": [arow[smap[i]["rowid"]] for i in sorted(testids)],
        "dev": [arow[smap[i]["rowid"]] for i in sorted(devids)],
        "new": [arow[n["rowid"]] for n in news]}
    caps = dict(CALL_CAPS)
    for tag, rows in (("test", sets["test"]), ("new", sets["new"]), ("dev", sets["dev"])):
        keeps = arm_b(rows, zones, A, R, pick["D"], pick["B6"], pick["B2층"])
        amb = [a for a in rows if keeps[a["rowid"]][4]]
        amb.sort(key=lambda a: (a["층"], a["문서id"], a["ax"], a["정규유형"]))
        st.setdefault("애매", {})[tag] = {"전체": len(rows), "애매": len(amb),
                                          "상한": caps["c_" + tag]}
        st_save(st)
        read_batch("c_" + tag, amb, zones, caps["c_" + tag], st)
        dall = sorted(rows, key=lambda a: (a["층"], a["문서id"], a["ax"], a["정규유형"]))
        read_batch("d_" + tag, dall, zones, caps["d_" + tag], st)
    # 지터 — 판독한 행 중 21행 × 추가 2회
    vt = OUT / "verdicts_c_test.jsonl"
    judged = [json.loads(l)["rowid"] for l in open(vt, encoding="utf-8")] if vt.exists() else []
    rng = random.Random(SEED_BOOT)
    jt = sorted(set(judged))
    jt = jt if len(jt) <= JIT_N else rng.sample(jt, JIT_N)
    path = OUT / "verdicts_jit.jsonl"
    have = collections.Counter()
    if path.exists():
        for l in open(path, encoding="utf-8"):
            have[json.loads(l)["rowid"]] += 1
    used = st.setdefault("calls", {})
    n = 0
    with open(path, "a", encoding="utf-8") as f:
        for rid in jt:
            for rep in (1, 2):
                if have[rid] >= 2:
                    continue
                if sum(used.values()) + n >= CALL_CAP_TOTAL or n >= caps["jit"]:
                    break
                a = arow[rid]
                v = call_claude(make_prompt(a, zones[(a["출처군"], a["문서id"])]))
                f.write(json.dumps({"rowid": rid, "rep": rep, "판정": v},
                                   ensure_ascii=False) + "\n")
                f.flush()
                n += 1
                have[rid] += 1
    used["jit"] = used.get("jit", 0) + n
    st_save(st)
    _log(단계="read/지터", 행=len(jt), 추가호출=n, 총호출=sum(used.values()))


# ── judge ────────────────────────────────────────────────────────────────
def load_verdicts(tag):
    p = OUT / ("verdicts_%s.jsonl" % tag)
    d = {}
    if p.exists():
        for l in open(p, encoding="utf-8"):
            o = json.loads(l)
            if o.get("rep", 0) == 0:
                d[o["rowid"]] = o["판정"]
    return d


def gold_new():
    """신규표본 240 gold — 이중 판독 + 3차."""
    out, agree = {}, {"3분류": [0, 0], "2분류": [0, 0]}
    if not GOLD_NEW[1].exists() or not GOLD_NEW[2].exists():
        return None, None
    L1 = {json.loads(l)["id"]: json.loads(l)["귀속"] for l in open(GOLD_NEW[1], encoding="utf-8")}
    L2 = {json.loads(l)["id"]: json.loads(l)["귀속"] for l in open(GOLD_NEW[2], encoding="utf-8")}
    AD = {}
    if GOLD_NEW[3].exists():
        AD = {json.loads(l)["id"]: json.loads(l)["귀속"] for l in open(GOLD_NEW[3], encoding="utf-8")}
    for i in sorted(set(L1) & set(L2)):
        agree["3분류"][1] += 1
        agree["3분류"][0] += int(L1[i] == L2[i])
        b1 = "참" if L1[i] == "참" else "비참"
        b2 = "참" if L2[i] == "참" else "비참"
        agree["2분류"][1] += 1
        agree["2분류"][0] += int(b1 == b2)
        out[i] = L1[i] if L1[i] == L2[i] else AD.get(i)
    return out, agree


def arms_for(rows, zones, A, R, pick, vc, vd, keeps=None):
    """팔 넷의 keep 사전(rowid→0/1) + ⓑ 사유."""
    keeps = keeps or arm_b(rows, zones, A, R, pick["D"], pick["B6"], pick["B2층"])
    a = {r["rowid"]: 1 for r in rows}
    b = {r["rowid"]: keeps[r["rowid"]][0] for r in rows}
    c = dict(b)
    n_ov = collections.Counter()
    for r in rows:
        v = vc.get(r["rowid"])
        if v == "예":
            c[r["rowid"]] = 1
        elif v == "아니오":
            c[r["rowid"]] = 0
        elif v is not None:
            n_ov["모름/실패"] += 1
        if v is not None and c[r["rowid"]] != b[r["rowid"]]:
            n_ov["뒤집힘"] += 1
    d = {}
    for r in rows:
        v = vd.get(r["rowid"])
        d[r["rowid"]] = 0 if v == "아니오" else 1
    return {"ⓐ": a, "ⓑ": b, "ⓒ": c, "ⓓ": d}, keeps, dict(n_ov)


def score_set(rows, gold_by_row, W, arms):
    res = {}
    for nm, kp in arms.items():
        items = [(r["층"], gold_by_row[r["rowid"]], kp[r["rowid"]]) for r in rows
                 if gold_by_row.get(r["rowid"]) in ("참", "거짓")]
        res[nm] = stratified_pr(items, W)
    return res


def jitter_J(rows, arms_c, vc, W, gold_by_row, arms_a):
    """지터 J — 재호출 불일치율의 Δ정밀도 SD 환산(붓스트랩 2,000)."""
    p = OUT / "verdicts_jit.jsonl"
    if not p.exists():
        return None, None
    reps = collections.defaultdict(list)
    for l in open(p, encoding="utf-8"):
        o = json.loads(l)
        reps[o["rowid"]].append(o["판정"])
    flips = tot = 0
    for rid, vs in reps.items():
        base = vc.get(rid)
        for v in vs:
            tot += 1
            flips += int(v != base)
    if tot == 0:
        return None, None
    q = flips / tot
    rng = random.Random(SEED_BOOT)
    vals = []
    judged = [r for r in rows if r["rowid"] in vc]
    for _ in range(2000):
        kp = dict(arms_c)
        for r in judged:
            if rng.random() < q:
                alt = rng.choice(["예", "아니오", "모름"])
                kp[r["rowid"]] = 1 if alt == "예" else (0 if alt == "아니오" else kp[r["rowid"]])
        ic = [(r["층"], gold_by_row[r["rowid"]], kp[r["rowid"]]) for r in rows
              if gold_by_row.get(r["rowid"]) in ("참", "거짓")]
        ia = [(r["층"], gold_by_row[r["rowid"]], arms_a[r["rowid"]]) for r in rows
              if gold_by_row.get(r["rowid"]) in ("참", "거짓")]
        rc, ra = stratified_pr(ic, W), stratified_pr(ia, W)
        if rc and ra and rc["정밀도"] is not None and ra["정밀도"] is not None:
            vals.append(rc["정밀도"] - ra["정밀도"])
    if len(vals) < 2:
        return q, None
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
    return q, sd


def judge():
    from pretrain.mde_guard import mde_of
    alive, zones, wmap, _ = load_world()
    S = sample865()
    sp = json.loads(SPLIT.read_text(encoding="utf-8"))
    W = sp["W"]
    st = st_load()
    pick = st["dev"]["선택"]
    A, R = load_authority()
    gold = gold_map(S)
    smap = {o["id"]: o for o in S}
    arow = {a["rowid"]: a for a in alive}
    out = {"선택인자": pick, "도장": code_stamp(), "호출": st.get("calls", {}),
           "애매": st.get("애매", {})}

    for setname in ("test", "dev"):
        ids = sorted([i for v in sp[setname].values() for i in v])
        rows = [arow[smap[i]["rowid"]] for i in ids]
        gbr = {smap[i]["rowid"]: gold.get(i) for i in ids}
        arms, keeps, ov = arms_for(rows, zones, A, R, pick,
                                   load_verdicts("c_" + setname), load_verdicts("d_" + setname))
        res = score_set(rows, gbr, W, arms)
        out[setname] = {"n": len(rows), "팔": res, "판독덮음": ov,
                        "gold분포": dict(collections.Counter(gbr.values()))}
        # 층별·신뢰층별 관찰
        for axis in ("층", "신뢰층"):
            tab = {}
            for lv in sorted({r[axis] for r in rows}):
                sub = [r for r in rows if r[axis] == lv]
                tab[lv] = {nm: stratified_pr(
                    [(r["층"], gbr[r["rowid"]], kp[r["rowid"]]) for r in sub
                     if gbr.get(r["rowid"]) in ("참", "거짓")], W)
                    for nm, kp in arms.items()}
            out[setname]["by_" + axis] = tab
        if setname == "test":
            ia = [(r["층"], gbr[r["rowid"]], arms["ⓐ"][r["rowid"]]) for r in rows
                  if gbr.get(r["rowid"]) in ("참", "거짓")]
            ic = [(r["층"], gbr[r["rowid"]], arms["ⓒ"][r["rowid"]]) for r in rows
                  if gbr.get(r["rowid"]) in ("참", "거짓")]
            ib = [(r["층"], gbr[r["rowid"]], arms["ⓑ"][r["rowid"]]) for r in rows
                  if gbr.get(r["rowid"]) in ("참", "거짓")]
            out["주대비"] = {"Δ정밀도_ⓒ−ⓐ": (res["ⓒ"]["정밀도"] - res["ⓐ"]["정밀도"])
                            if res["ⓒ"]["정밀도"] is not None else None,
                            "붓스트랩": boot_delta(ia, ic, W),
                            "관찰_Δⓑ−ⓐ": (res["ⓑ"]["정밀도"] - res["ⓐ"]["정밀도"]),
                            "관찰_붓스트랩ⓑ": boot_delta(ia, ib, W)}
            q, J = jitter_J(rows, arms["ⓒ"], load_verdicts("c_test"), W, gbr, arms["ⓐ"])
            se = out["주대비"]["붓스트랩"]["SE"] if out["주대비"]["붓스트랩"] else None
            out["주대비"]["지터"] = {"재호출불일치율": q, "J(정밀도환산SD)": J}
            if se:
                mde = mde_of(se, J or 0.0)
                out["주대비"]["MDE실측"] = mde
                out["주대비"]["MDE등록"] = MDE_REG
                out["주대비"]["여유"] = abs(out["주대비"]["Δ정밀도_ⓒ−ⓐ"]) - mde
            # 재현율 게이트
            out["재현율게이트"] = {nm: {"재현율": res[nm]["재현율"],
                                     "통과": (res[nm]["재현율"] is not None
                                            and res[nm]["재현율"] >= RECALL_FLOOR)}
                                for nm in ("ⓑ", "ⓒ", "ⓓ")}
            # 민감도 — 보충 97 양극단
            sens = {}
            supp_ids = [i for i in ids if gold.get(i) not in ("참", "거짓")
                        or (smap[i]["_1028"]["라벨"] != "참"
                            and not (smap[i]["_1028"]["라벨"] == "거짓"
                                     and smap[i]["_1028"]["부표"] == "ⓔ"))]
            for assume in ("참", "거짓"):
                g2 = dict(gbr)
                for i in supp_ids:
                    g2[smap[i]["rowid"]] = assume
                ra = stratified_pr([(r["층"], g2[r["rowid"]], arms["ⓐ"][r["rowid"]])
                                    for r in rows], W)
                rc = stratified_pr([(r["층"], g2[r["rowid"]], arms["ⓒ"][r["rowid"]])
                                    for r in rows], W)
                sens[assume] = {"ⓐ": ra, "ⓒ": rc,
                                "Δ": rc["정밀도"] - ra["정밀도"] if rc["정밀도"] is not None else None}
            out["민감도_보충97"] = {"대상": len(supp_ids), **sens}

    # 신규표본
    gn, agree = gold_new()
    if gn:
        news = [json.loads(l) for l in gzip.open(NEWS, "rt", encoding="utf-8")]
        rows = [arow[n["rowid"]] for n in news]
        nmap = {n["id"]: n["rowid"] for n in news}
        gbr = {nmap[i]: v for i, v in gn.items() if i in nmap}
        WN = {"E1": 5726, "E2모호": 2976, "E2미해소": 7475, "E3": 12658}
        arms, keeps, ov = arms_for(rows, zones, A, R, pick,
                                   load_verdicts("c_new"), load_verdicts("d_new"))
        res = {}
        for nm, kp in arms.items():
            items = [(r["신뢰층"], gbr.get(r["rowid"]), kp[r["rowid"]]) for r in rows
                     if gbr.get(r["rowid"]) in ("참", "거짓")]
            res[nm] = stratified_pr(items, WN)
        ia = [(r["신뢰층"], gbr.get(r["rowid"]), arms["ⓐ"][r["rowid"]]) for r in rows
              if gbr.get(r["rowid"]) in ("참", "거짓")]
        ic = [(r["신뢰층"], gbr.get(r["rowid"]), arms["ⓒ"][r["rowid"]]) for r in rows
              if gbr.get(r["rowid"]) in ("참", "거짓")]
        out["new"] = {"n": len(rows), "팔": res, "일치율": agree, "판독덮음": ov,
                      "gold분포": dict(collections.Counter(gbr.values())),
                      "Δ정밀도_ⓒ−ⓐ": (res["ⓒ"]["정밀도"] - res["ⓐ"]["정밀도"])
                      if res["ⓒ"]["정밀도"] is not None else None,
                      "붓스트랩": boot_delta(ia, ic, WN), "MDE등록": MDE_REG_NEW}
    else:
        out["new"] = {"미측정": "신규표본 gold 미완"}
    SCORE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    st["judge"] = {"완료": True}
    st_save(st)
    _log(단계="judge", 주대비=out.get("주대비"), 재현율게이트=out.get("재현율게이트"))


# ── v2 ───────────────────────────────────────────────────────────────────
def v2_stage():
    import runners.event_refine1028 as e28
    alive, zones, wmap, _ = load_world()
    st = st_load()
    pick = st["dev"]["선택"]
    A, R = load_authority()
    V2.mkdir(parents=True, exist_ok=True)
    load1_gate()
    keeps = arm_b(alive, zones, A, R, pick["D"], pick["B6"], pick["B2층"])
    kept = [a for a in alive if keeps[a["rowid"]][0]]
    why = collections.Counter(keeps[a["rowid"]][1] for a in alive)
    assigns = [(a["ax"], a["키"], a["신뢰층"], a["개체원명"], a["정규유형"], a["원유형"],
                dt.date.fromisoformat(a["event_time"]), a["문서id"], a["출처군"],
                a["conf"], a["pub_time"]) for a in kept]
    events = e28.merge_events(assigns, 3, "EV2-", wmap)
    for e in events:
        e["정제"] = "G1p-1028규칙+귀속1032(%s)" % json.dumps(pick, ensure_ascii=False)
    with gzip.open(V2 / "events_v2.jsonl.gz", "wt", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    # 거짓률 사영 재검(§4-2)
    S = sample865()
    sp = json.loads(SPLIT.read_text(encoding="utf-8"))
    keptid = {a["rowid"] for a in kept}
    W2 = collections.Counter(a["층"] for a in kept)
    recheck = {}
    for setname, ids in (("시험셋", sorted(i for v in sp["test"].values() for i in v)),
                         ("전865", sorted(o["id"] for o in S))):
        smap = {o["id"]: o for o in S}
        per = collections.defaultdict(lambda: [0, 0, 0])
        for i in ids:
            o = smap[i]
            if o["rowid"] not in keptid:
                continue
            lab = o["_1028"]["라벨"]
            c = per[o["층"]]
            c[0] += 1
            c[1] += int(lab == "거짓")
            c[2] += int(lab == "참")
        tot = sum(W2[s] for s in per)
        p = 0.0
        for s, c in per.items():
            if c[1] + c[2] == 0:
                continue
            p += (W2[s] / tot) * c[1] / (c[1] + c[2])
        recheck[setname] = {"p_hat": p, "표본": sum(c[0] for c in per.values()),
                            "층수": len(per), "문턱": FALSE_CAP,
                            "통과": p <= FALSE_CAP}
    meta = {"선택인자": pick, "배정행_v1": len(alive), "배정행_v2": len(kept),
            "유일사건_v1": 19507, "유일사건_v2": len(events),
            "차단사유": dict(why.most_common()),
            "신뢰층_v2": dict(collections.Counter(e["신뢰층"] for e in events)),
            "유형_v2": dict(collections.Counter(e["정규유형"] for e in events)),
            "시대_v2": dict(collections.Counter(e["event_time"][:4] for e in events)),
            "거짓률재검": recheck, "도장": code_stamp(),
            "낙인": "원장 v2 «후보» — 1028 소비금지 낙인 해제는 별도 사이클(§4-2)"}
    (V2 / "meta1032.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    _log(단계="v2", 배정행=len(kept), 유일사건=len(events), 거짓률재검=recheck)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["selftest", "split", "authority", "dev", "read", "judge", "v2"])
    a = ap.parse_args()
    t0 = time.time()
    {"selftest": selftest, "split": split, "authority": authority, "dev": dev_stage,
     "read": read_stage, "judge": judge, "v2": v2_stage}[a.stage]()
    _log(단계=a.stage, 끝="%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
