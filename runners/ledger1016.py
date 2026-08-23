# -*- coding: utf-8 -*-
"""1016 — L2 개입 원장 정본화 러너 (사전등록 docs/탐색/1016.md 커밋 063388586 «후» 작성).

읽기: data/market_records · data/records · data/state/wiki_views · data/state/wiki_after ·
      data/ingest/wiki_daily · ingest/derive_features.HOLIDAYS  (records 원본 무수정)
쓰기: /Users/ax/wm_harvest/foundation/ledger_interventions/{ledger.jsonl, meta.json,
      alias_check_sample.json, run1016.out}
규칙은 전부 사전등록 §1~§5 의 것 — 여기서 새로 정하지 않는다.
"""
import gzip
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime, timedelta
from glob import glob

REPO = "/Users/ax/world_model"
OUT = "/Users/ax/wm_harvest/foundation/ledger_interventions"
sys.path.insert(0, REPO)
from ingest.derive_features import HOLIDAYS  # 원장 파생값을 만든 그 표(«같은 자»)

# ---------- 날짜 ----------
DAY_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
MON_RE = re.compile(r"^(\d{4})-(\d{2})$")


def parse_day(s):
    if not isinstance(s, str):
        return None
    m = DAY_RE.match(s.strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def precision(s):
    if isinstance(s, str) and DAY_RE.match(s.strip()):
        return "day" if parse_day(s) else "none"
    if isinstance(s, str) and MON_RE.match(s.strip()):
        return "month"
    return "none"


def valid_ymd(y, mo, d, y_lo=2000, y_hi=2099):
    if not (y_lo <= y <= y_hi and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    try:
        return date(y, mo, d)
    except ValueError:
        return None


# ---------- announced_at 사슬 (사전등록 §2) ----------
URL_PATH_RE = re.compile(r"(20\d{2})[/\-.](\d{1,2})[/\-.](\d{1,2})")
DIGIT_RUN_RE = re.compile(r"\d+")
BODY_RE = re.compile(r"(?<!\d)(20\d{2})[.년/\-]\s?(\d{1,2})[.월/\-]\s?(\d{1,2})일?(?!\d)")


def cands_from_url(u):
    out = []
    if not isinstance(u, str):
        return out
    for m in URL_PATH_RE.finditer(u):
        d = valid_ymd(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            out.append(d)
    for m in DIGIT_RUN_RE.finditer(u):
        r = m.group(0)
        if len(r) in (8, 12, 14):
            d = valid_ymd(int(r[:4]), int(r[4:6]), int(r[6:8]), 2015, 2027)
            if d:
                out.append(d)
    return out


def cands_from_body(t):
    out = []
    if not isinstance(t, str):
        return out
    for m in BODY_RE.finditer(t):
        d = valid_ymd(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            out.append(d)
    return out


def announced_market(rec, opened):
    """반환: (announced_at|None, source|None, reason|None, 후보수)"""
    o = rec.get("outcome", {})
    cands = []  # (date, step, field)
    for fld in ("visitors_source_date", "sales_source_date"):
        d = parse_day(o.get(fld))
        if d:
            cands.append((d, 1, "outcome." + fld))
    d = parse_day(rec.get("outcome_source_date"))
    if d:
        cands.append((d, 1, "outcome_source_date"))
    for i, af in enumerate(o.get("alt_figures") or []):
        d = parse_day(af.get("source_date") if isinstance(af, dict) else None)
        if d:
            cands.append((d, 1, "alt_figures[%d].source_date" % i))
    for i, ad in enumerate(rec.get("additional_sources") or []):
        d = parse_day(ad.get("date") if isinstance(ad, dict) else None)
        if d:
            cands.append((d, 1, "additional_sources[%d].date" % i))
    for fld in ("visitors_source_url", "sales_source_url"):
        for d in cands_from_url(o.get(fld)):
            cands.append((d, 2, "outcome." + fld))
    for d in cands_from_url(rec.get("outcome_source_url")):
        cands.append((d, 2, "outcome_source_url"))
    for i, af in enumerate(o.get("alt_figures") or []):
        if isinstance(af, dict):
            for d in cands_from_url(af.get("source_url")):
                cands.append((d, 2, "alt_figures[%d].source_url" % i))
    for i, ad in enumerate(rec.get("additional_sources") or []):
        if isinstance(ad, dict):
            for d in cands_from_url(ad.get("url")):
                cands.append((d, 2, "additional_sources[%d].url" % i))
    for fld in ("visitors_source_quote", "sales_source_quote", "counting_basis_note"):
        for d in cands_from_body(o.get(fld)):
            cands.append((d, 3, "outcome." + fld))
    for d in cands_from_body(rec.get("notes")):
        cands.append((d, 3, "notes"))

    if opened is None:
        return None, None, "no_opened_at", len(cands)
    if not cands:
        return None, None, "no_candidate", 0
    valid = [c for c in cands if opened - timedelta(days=730) <= c[0] < opened]
    if valid:
        d, step, field = sorted(valid, key=lambda x: (x[0], x[1], x[2]))[0]
        return d, {"step": step, "field": field}, None, len(cands)
    before = [c for c in cands if c[0] < opened]
    return None, None, ("out_of_window" if before else "all_on_or_after_open"), len(cands)


def internal_body_cands(rec, opened):
    """내부층 사슬③ 상당 후보 계수(채택 안 함 — 사전등록 §2)."""
    if opened is None:
        return 0
    texts = [
        (rec.get("outcome") or {}).get("source"),
        (rec.get("provenance") or {}).get("notes"),
        (rec.get("intervention") or {}).get("concept"),
    ]
    n = 0
    for t in texts:
        for d in cands_from_body(t):
            if opened - timedelta(days=730) <= d < opened:
                n += 1
    return n


# ---------- 파생 ----------
def weekend_holiday(f, t):
    dur = (t - f).days + 1
    wk = 0
    hol = 0
    d = f
    while d <= t:
        if d.weekday() >= 5:
            wk += 1
        if d.isoformat() in HOLIDAYS:
            hol += 1
        d += timedelta(days=1)
    return dur, round(wk / dur, 4), hol


# ---------- 별칭 정규화 (사전등록 §5) ----------
PUNCT = "·.,'\"!?~&*+_/\\-:;’‘“”"
BRACKETS = [("(", ")"), ("[", "]"), ("〈", "〉"), ("《", "》"), ("「", "」"), ("『", "』"), ("<", ">")]
LATIN_IN_PAREN = re.compile(r"^(.*?)\(([A-Za-z0-9 .:'&\-]+)\)\s*$")


def r1(s):
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"\s+", "", s)
    return "".join(ch for ch in s if ch not in PUNCT)


def r2_strip_brackets(s):
    prev = None
    while prev != s:
        prev = s
        for a, b in BRACKETS:
            s = re.sub(re.escape(a) + r"[^" + re.escape(a + b) + r"]*" + re.escape(b), "", s)
    return s


def stage_keys(name, k):
    """단계 k 까지의 누적 후보 키 집합(길이<2 키 제외)."""
    out = set()
    if not isinstance(name, str) or not name.strip():
        return out
    s = name.strip()
    if k >= 0:
        out.add(s)  # 정확(원문 그대로)
    if k >= 1:
        out.add(r1(s))
    if k >= 2:
        out.add(r1(r2_strip_brackets(s)))
    if k >= 3:
        left = re.split(r"[:：]", s, 1)[0]
        out.add(r1(left))
    if k >= 4:
        m = LATIN_IN_PAREN.match(s)
        if m:
            out.add(r1(m.group(1)))
            out.add(r1(m.group(2)))
    return {x for x in out if len(x) >= 2}


# ---------- 적재 ----------
def load_dir(d):
    out = []
    for f in sorted(glob(os.path.join(d, "*.json"))):
        with open(f) as fh:
            out.append((os.path.basename(f)[:-5], f, json.load(fh)))
    return out


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    log = []

    def say(*a):
        s = " ".join(str(x) for x in a)
        log.append(s)
        print(s)

    mk = load_dir(os.path.join(REPO, "data/market_records"))
    rc = load_dir(os.path.join(REPO, "data/records"))
    say("D0 전량: 시장 %d · 내부 %d · 합 %d" % (len(mk), len(rc), len(mk) + len(rc)))

    # ---- 레코드 정규화 뷰 ----
    rows = []
    for rid, path, r in mk:
        c = r.get("conditions", {})
        o = r.get("outcome", {})
        f_raw, t_raw = c.get("period_from"), c.get("period_to")
        f, t = parse_day(f_raw), parse_day(t_raw)
        dv = c.get("derived") or {}
        dur = dv.get("duration") or {}
        lt = o.get("label_trust") or {}
        sc = o.get("scope_class")
        rows.append(dict(
            rid=rid, path=path, layer="market", raw=r,
            f=f, t=t, f_raw=f_raw, prec=precision(f_raw),
            visitors=o.get("visitors_total"), sales=o.get("sales_krw"),
            grade=lt.get("grade"), usable=(sc or {}).get("usable") if isinstance(sc, dict) else None,
            scope=sc, category=r.get("category"),
            name_a=r.get("ip_or_collab"), name_b=r.get("brand"),
            ip_hist=dv.get("ip_history"),
            dur_pre=dur.get("days"), wk_pre=dur.get("weekend_share"), hol_pre=dur.get("holiday_days"),
            city=c.get("city"), venue=c.get("venue"), venue_type=c.get("venue_type"),
            area=c.get("area_pyeong"), multi=c.get("multi_store"),
            brand=r.get("brand"),
            exp=(r.get("intervention") or {}).get("experience_elements"),
            promo=(r.get("intervention") or {}).get("promotions"),
            free=(r.get("intervention") or {}).get("is_free_entry"),
            resv=(r.get("intervention") or {}).get("reservation_required"),
            vbasis=o.get("counting_basis"),
            vs_url=o.get("visitors_source_url"), vs_date=o.get("visitors_source_date"),
            ss_url=o.get("sales_source_url"), ss_date=o.get("sales_source_date"),
            extracted_at=r.get("ingested_from"), docs_n=None,
        ))
    for rid, path, r in rc:
        c = r.get("conditions", {})
        o = r.get("outcome", {})
        per = c.get("period") or {}
        f_raw, t_raw = per.get("from"), per.get("to")
        f, t = parse_day(f_raw), parse_day(t_raw)
        dv = c.get("derived") or {}
        dur = dv.get("duration") or {}
        lt = o.get("label_trust") if isinstance(o.get("label_trust"), dict) else {}
        loc = c.get("location") or {}
        tot = o.get("totals") or {}
        rows.append(dict(
            rid=rid, path=path, layer="internal", raw=r,
            f=f, t=t, f_raw=f_raw, prec=precision(f_raw),
            visitors=tot.get("visitors"), sales=tot.get("sales_krw"),
            grade=(lt or {}).get("grade"), usable=None,
            scope=o.get("label_scope") if isinstance(o.get("label_scope"), dict) else None,
            category=None,
            name_a=(r.get("entities") or {}).get("brand_key"),
            name_b=(r.get("intervention") or {}).get("brand_name"),
            ip_hist=dv.get("ip_history"),
            dur_pre=dur.get("days") if dur.get("days") is not None else per.get("days"),
            wk_pre=dur.get("weekend_share"), hol_pre=dur.get("holiday_days"),
            city=loc.get("city"), venue=loc.get("venue_name"), venue_type=loc.get("venue_type"),
            area=c.get("area_pyeong"), multi=None,
            brand=(r.get("intervention") or {}).get("brand_name"),
            exp=(r.get("intervention") or {}).get("experience_elements"),
            promo=(r.get("intervention") or {}).get("promotions"),
            free=None, resv=None,
            vbasis=o.get("counting_method") if o.get("counting_method") is not None else o.get("counting_basis"),
            vs_url=None, vs_date=None, ss_url=None, ss_date=None,
            extracted_at=(r.get("provenance") or {}).get("extracted_at"),
            docs_n=len(r.get("docs") or []),
        ))

    # ---- announced_at ----
    ann_fill = {"market": 0, "internal": 0}
    reasons = {}
    leads = []
    int_body_cands = 0
    for w in rows:
        if w["layer"] == "market":
            a, src, reason, ncand = announced_market(w["raw"], w["f"])
            w["ann"], w["ann_src"], w["ann_reason"] = a, src, reason
            if a:
                ann_fill["market"] += 1
                leads.append((w["f"] - a).days)
            else:
                reasons[reason] = reasons.get(reason, 0) + 1
        else:
            w["ann"], w["ann_src"], w["ann_reason"] = None, None, "no_public_source"
            reasons["no_public_source"] = reasons.get("no_public_source", 0) + 1
            int_body_cands += 1 if internal_body_cands(w["raw"], w["f"]) > 0 else 0
    n_mk, n_rc, n_all = len(mk), len(rc), len(rows)
    d1d_all = sum(1 for w in rows if w["prec"] == "day")
    say("announced_at 채움: 시장 %d/%d (%.1f%%) · 내부 0/%d(no_public_source 사전 고정) · 합 %d/%d (%.1f%%) · /D1d %d/%d"
        % (ann_fill["market"], n_mk, 100.0 * ann_fill["market"] / n_mk, n_rc,
           ann_fill["market"], n_all, 100.0 * ann_fill["market"] / n_all, ann_fill["market"], d1d_all))
    say("null 사유 분해:", json.dumps(reasons, ensure_ascii=False))
    say("내부층 사슬③ 상당 후보 보유 레코드(채택 안 함):", int_body_cands)
    lead_dist = {}
    if leads:
        leads.sort()
        qq = lambda p: leads[min(len(leads) - 1, int(p * len(leads)))]
        bins = [(1, 3), (4, 7), (8, 14), (15, 30), (31, 90), (91, 365), (366, 730)]
        lead_dist = {
            "n": len(leads), "min": leads[0], "q25": qq(0.25), "median": qq(0.5),
            "q75": qq(0.75), "max": leads[-1],
            "bins": {"%d-%d" % (a, b): sum(1 for x in leads if a <= x <= b) for a, b in bins},
        }
        say("lead_days 분포:", json.dumps(lead_dist, ensure_ascii=False))

    # ---- 파생(기간·경쟁밀도) ----
    for w in rows:
        f, t = w["f"], w["t"]
        dur = w["dur_pre"]
        wk, hol = w["wk_pre"], w["hol_pre"]
        if f and t and t >= f:
            cdur, cwk, chol = weekend_holiday(f, t)
            if dur is None:
                dur = cdur
            if wk is None:
                wk = cwk
            if hol is None:
                hol = chol
        w["dur"], w["wk"], w["hol"] = dur, wk, hol
        w["u"] = None
        if (w["visitors"] is not None and f and t and isinstance(dur, (int, float)) and dur >= 1):
            try:
                w["u"] = round(float(w["visitors"]) / float(dur), 3)
            except (TypeError, ValueError, ZeroDivisionError):
                w["u"] = None
    day_rows = [w for w in rows if w["f"]]
    ivals = [(w["f"], w["t"] if (w["t"] and w["t"] >= w["f"]) else w["f"], w["category"], id(w)) for w in day_rows]
    for w in rows:
        if not w["f"]:
            w["cd_cat"], w["cd_any"] = None, None
            continue
        f = w["f"]
        t = w["t"] if (w["t"] and w["t"] >= f) else f
        any_n = 0
        cat_n = 0
        for (f2, t2, cat2, oid) in ivals:
            if oid == id(w):
                continue
            if f2 <= t and f <= t2:
                any_n += 1
                if w["category"] is not None and cat2 == w["category"]:
                    cat_n += 1
        w["cd_any"] = any_n
        w["cd_cat"] = cat_n if w["category"] is not None else None

    # ---- 분모 사다리·교차표 ----
    def ladder(sub):
        d0 = len(sub)
        d1 = sum(1 for w in sub if w["f_raw"])
        d1d = sum(1 for w in sub if w["prec"] == "day")
        d2 = [w for w in sub if w["f_raw"] and (w["visitors"] is not None or w["sales"] is not None)]
        d3 = [w for w in d2 if w["grade"] in ("A", "B")]
        d4 = [w for w in d3 if w["usable"] is True]
        return d0, d1, d1d, len(d2), len(d3), len(d4)

    lad = {}
    for nm, sub in (("market", [w for w in rows if w["layer"] == "market"]),
                    ("internal", [w for w in rows if w["layer"] == "internal"]),
                    ("합", rows)):
        lad[nm] = ladder(sub)
        say("사다리[%s] D0=%d D1시점=%d (D1d일단위=%d) D2결과=%d D3 A/B=%d D4 usable∩A/B=%d"
            % ((nm,) + lad[nm]))

    def xcell(sub):
        allc = len(sub)
        ab = sum(1 for w in sub if w["grade"] in ("A", "B"))
        abu = sum(1 for w in sub if w["grade"] in ("A", "B") and w["usable"] is True)
        u = sum(1 for w in sub if w["u"] is not None)
        return allc, ab, abu, u

    xtab = {}
    for nm, sub in (("market", [w for w in rows if w["layer"] == "market"]),
                    ("internal", [w for w in rows if w["layer"] == "internal"]),
                    ("합", rows)):
        xtab[nm] = {
            "D0": xcell(sub),
            "D1d": xcell([w for w in sub if w["prec"] == "day"]),
            "D1d∩결과": xcell([w for w in sub if w["prec"] == "day" and (w["visitors"] is not None or w["sales"] is not None)]),
            "D1d∩방문자": xcell([w for w in sub if w["prec"] == "day" and w["visitors"] is not None]),
        }
        for k, v in xtab[nm].items():
            say("교차[%s][%s] 전체=%d A/B=%d A/B∩usable=%d U계산가능=%d" % ((nm, k) + v))
    ucnt = sum(1 for w in rows if w["u"] is not None)
    unonint = sum(1 for w in rows if w["u"] is not None and not (
        isinstance(w["scope"], dict) and (w["scope"].get("interim") or w["scope"].get("per_day") or w["scope"].get("forecast"))))
    say("U 계산 가능: %d/%d · 그중 interim/per_day/forecast 아님 %d" % (ucnt, n_all, unonint))

    # ---- 별칭 해소 ----
    wiki_pages = {}  # page -> True
    direct = {}      # rid -> page
    for fp in glob(os.path.join(REPO, "data/state/wiki_views/*.json")):
        with open(fp) as fh:
            v = json.load(fh)
        if v.get("page"):
            wiki_pages[v["page"]] = True
            direct[v.get("record_id")] = v["page"]
    say("위키 명단 W(유일 문서): %d" % len(wiki_pages))
    ledger_ids = {w["rid"] for w in rows}
    baseline = {rid: pg for rid, pg in direct.items() if rid in ledger_ids}
    say("기준선 직접 키 해소: %d/%d (%.1f%%)" % (len(baseline), n_all, 100.0 * len(baseline) / n_all))

    # 위키 키 색인(단계 누적)
    widx = [dict() for _ in range(5)]  # stage k -> key -> set(pages)
    for pg in wiki_pages:
        for k in range(5):
            for key in stage_keys(pg, k):
                widx[k].setdefault(key, set()).add(pg)

    new_matches = []  # (rid, layer, name_used, which(R0a/R0b), page, stage)
    ambiguous = 0
    stage_new = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    which_cnt = {"R0a": 0, "R0b": 0}
    for w in rows:
        if w["rid"] in baseline:
            w["resolved"] = baseline[w["rid"]]
            w["resolved_how"] = "direct"
            continue
        name, which = (w["name_a"], "R0a") if (isinstance(w["name_a"], str) and w["name_a"].strip()) else (w["name_b"], "R0b")
        w["resolved"], w["resolved_how"] = None, None
        if not (isinstance(name, str) and name.strip()):
            continue
        final_keys = stage_keys(name, 4)
        docs = set()
        for key in final_keys:
            docs |= widx[4].get(key, set())
        if len(docs) >= 2:
            ambiguous += 1
            continue
        if len(docs) == 1:
            pg = next(iter(docs))
            att = None
            for k in range(5):
                hit = set()
                for key in stage_keys(name, k):
                    hit |= widx[k].get(key, set())
                if pg in hit:
                    att = k
                    break
            w["resolved"], w["resolved_how"] = pg, "name_R%d_%s" % (att, which)
            new_matches.append((w["rid"], w["layer"], name, which, pg, att))
            stage_new[att] += 1
            which_cnt[which] += 1
    n_expand = len(baseline) + len(new_matches)
    say("이름 확장 신규 일치: %d (정확R0=%d R1=%d R2=%d R3=%d R4=%d · R0a %d/R0b %d) · 모호 불채택 %d"
        % (len(new_matches), stage_new[0], stage_new[1], stage_new[2], stage_new[3], stage_new[4],
           which_cnt["R0a"], which_cnt["R0b"], ambiguous))
    say("확장 해소 합: %d → %d /%d (%.1f%% → %.1f%%)"
        % (len(baseline), n_expand, n_all, 100.0 * len(baseline) / n_all, 100.0 * n_expand / n_all))

    # 참양성 표본 검사(규칙 검증 · 시드 1016)
    random.seed(1016)
    sample = random.sample(new_matches, min(20, len(new_matches)))
    checks = []
    n_pass = 0
    for (rid, layer, name, which, pg, att) in sample:
        a_keys = stage_keys(name, att)
        p_keys = stage_keys(pg, att)
        ca = len(a_keys & p_keys) > 0                     # ⓐ 귀속 규칙 재적용 재현
        docs = set()
        for key in stage_keys(name, 4):
            docs |= widx[4].get(key, set())
        cb = docs == {pg}                                 # ⓑ 양방향(최종 누적) 유일성
        cc = all(len(k) >= 2 for k in (a_keys & p_keys))  # ⓒ 키 길이 관문
        ok = ca and cb and cc
        n_pass += 1 if ok else 0
        checks.append({"record_id": rid, "layer": layer, "record_name": name, "which": which,
                       "wiki_page": pg, "rule": "R%d" % att,
                       "ⓐ재현": ca, "ⓑ유일": cb, "ⓒ키길이": cc, "통과": ok})
    say("참양성 표본 검사: %d/%d 통과 (시드 1016 · 규칙 검증)" % (n_pass, len(sample)))
    with open(os.path.join(OUT, "alias_check_sample.json"), "w") as fh:
        json.dump(checks, fh, ensure_ascii=False, indent=1)

    # ---- 삼중 조건 분모 ----
    doc_curves = {}  # 문서 -> [set(dates)]
    for fp in glob(os.path.join(REPO, "data/ingest/wiki_daily/*.jsonl.gz")):
        with gzip.open(fp, "rt") as fh:
            for line in fh:
                d = json.loads(line)
                pg = d.get("문서")
                if not pg or not d.get("날짜"):
                    continue
                doc_curves.setdefault(pg, []).append({int(x) for x in d["날짜"]})
    say("wiki_daily 문서 곡선: 문서 %d · 행 %d" % (len(doc_curves), sum(len(v) for v in doc_curves.values())))

    def dset(days):
        return {int(x[0]) for x in (days or [])}

    def cover(dates, f0, f1, need):
        n = 0
        d = f0
        while d <= f1:
            if int(d.strftime("%Y%m%d")) in dates:
                n += 1
            d += timedelta(days=1)
        return n >= need

    def triple_ok(w):
        if w["prec"] != "day":
            return False
        f = w["f"]
        pre0, pre1 = f - timedelta(days=90), f - timedelta(days=1)
        post0, post1 = f, f + timedelta(days=90)
        pg = w.get("resolved")
        if pg:
            for ds in doc_curves.get(pg, []):
                if cover(ds, pre0, pre1, 85) and cover(ds, post0, post1, 86):
                    return True
        vp = os.path.join(REPO, "data/state/wiki_views", w["rid"] + ".json")
        ap = os.path.join(REPO, "data/state/wiki_after", w["rid"] + ".json")
        if os.path.exists(vp) and os.path.exists(ap):
            with open(vp) as fh:
                v = json.load(fh)
            with open(ap) as fh:
                a = json.load(fh)
            if v.get("page") and cover(dset(v.get("days")), pre0, pre1, 85) \
               and cover(dset(a.get("days")), post0, post1, 86):
                return True
        return False

    def triple_count(pred):
        sel = [w for w in rows if pred(w) and triple_ok(w)]
        return (len(sel),
                sum(1 for w in sel if w["visitors"] is not None),
                sum(1 for w in sel if w["sales"] is not None),
                sum(1 for w in sel if w["layer"] == "market"))

    pre_n = triple_count(lambda w: w["rid"] in baseline)
    post_n = triple_count(lambda w: w.get("resolved") is not None)
    say("삼중 조건 «전»(직접 해소만): %d (방문자 %d · 매출 %d · 시장 %d · 내부 %d) [1013: 118]"
        % (pre_n[0], pre_n[1], pre_n[2], pre_n[3], pre_n[0] - pre_n[3]))
    say("삼중 조건 «후»(이름 확장 포함): %d (방문자 %d · 매출 %d · 시장 %d · 내부 %d)"
        % (post_n[0], post_n[1], post_n[2], post_n[3], post_n[0] - post_n[3]))

    # ---- 원장 기록 ----
    ledger_path = os.path.join(OUT, "ledger.jsonl")
    fills = {}
    with open(ledger_path, "w") as fh:
        for w in rows:
            f, t = w["f"], w["t"]
            lead = (f - w["ann"]).days if (w["ann"] and f) else None
            rec = {
                "record_id": w["rid"], "layer": w["layer"], "사건유형": "팝업개최",
                "A": {
                    "when": {
                        "announced_at": w["ann"].isoformat() if w["ann"] else None,
                        "announced_at_source": w["ann_src"],
                        "announced_null_reason": w["ann_reason"],
                        "opened_at": f.isoformat() if f else (w["f_raw"] if w["prec"] == "month" else None),
                        "closed_at": t.isoformat() if t else None,
                        "date_precision": w["prec"],
                        "lead_days": lead,
                        "duration_days": w["dur"],
                        "weekend_share": w["wk"],
                        "holiday_days": w["hol"],
                    },
                    "where": {"city": w["city"], "venue": w["venue"], "venue_type": w["venue_type"],
                              "area_pyeong": w["area"], "multi_store": w["multi"]},
                    "what": {"brand": w["brand"], "ip_name": w["name_a"], "category": w["category"],
                             "experience_elements": w["exp"], "promotions": w["promo"],
                             "is_free_entry": w["free"], "reservation_required": w["resv"]},
                },
                "C": {"ip_history": w["ip_hist"], "comp_density_same_cat": w["cd_cat"],
                      "comp_density_any": w["cd_any"], "s_disc": None, "s_disc_status": "L1_pending"},
                "Y": {"visitors_total": w["visitors"], "visitors_basis": w["vbasis"],
                      "sales_krw": w["sales"], "label_trust_grade": w["grade"],
                      "usable": w["usable"], "scope": w["scope"], "u_daily_visitors": w["u"]},
                "source": {"path": os.path.relpath(w["path"], REPO), "extracted_at": w["extracted_at"],
                           "visitors_source": {"url": w["vs_url"], "date": w["vs_date"]},
                           "sales_source": {"url": w["ss_url"], "date": w["ss_date"]},
                           "wiki_resolution": ({"page": w.get("resolved"), "how": w.get("resolved_how")}
                                               if w.get("resolved") else None),
                           "docs_n": w["docs_n"]},
            }
            missing = []

            def walk(obj, pre):
                for k, v in obj.items():
                    p = pre + "." + k if pre else k
                    if isinstance(v, dict) and k not in ("ip_history", "scope", "announced_at_source",
                                                         "visitors_source", "sales_source", "wiki_resolution"):
                        walk(v, p)
                    elif v is None and k not in ("s_disc", "announced_null_reason"):
                        missing.append(p)
            walk(rec["A"], "A")
            walk(rec["C"], "C")
            walk(rec["Y"], "Y")
            rec["missing"] = missing
            for m in missing:
                fills[m] = fills.get(m, 0) + 1
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    n_lines = sum(1 for _ in open(ledger_path))
    lsha = sha256_file(ledger_path)
    say("원장: %s · %d 행 · sha256 %s" % (ledger_path, n_lines, lsha))
    fill_tbl = {k: n_all - v for k, v in sorted(fills.items())}
    say("필드 채움(비-null /%d): %s" % (n_all, json.dumps(fill_tbl, ensure_ascii=False)))

    # ---- 스탬프 ----
    def git(*a):
        return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True).stdout.strip()

    head = git("rev-parse", "HEAD")
    porc = git("status", "--porcelain", "--", "data/market_records", "data/records",
               "data/state/wiki_views", "data/state/wiki_after", "data/ingest/wiki_daily")
    rsha = sha256_file(os.path.abspath(__file__))
    end = datetime.now().isoformat(timespec="seconds")
    say("스탬프: HEAD %s · 계수 대상 porcelain %s · 러너 sha256 %s · 끝 %s"
        % (head[:12], "0행" if not porc else "🔴 " + porc.replace("\n", " | "), rsha[:16], end))

    meta = {
        "cycle": 1016, "end_at": end, "git_head": head,
        "porcelain_measured_dirs": porc, "runner_sha256": rsha,
        "ledger_sha256": lsha, "ledger_lines": n_lines,
        "ladder": {k: dict(zip(["D0", "D1", "D1d", "D2", "D3_AB", "D4_usableAB"], v)) for k, v in lad.items()},
        "xtab": {k: {r: dict(zip(["전체", "AB", "AB_usable", "U가능"], c)) for r, c in v.items()} for k, v in xtab.items()},
        "announced": {"fill_market": ann_fill["market"], "n_market": n_mk, "n_all": n_all,
                      "d1d_all": d1d_all, "reasons": reasons, "lead_days": lead_dist,
                      "internal_body_cands_records": int_body_cands},
        "U": {"computable": ucnt, "non_interim": unonint},
        "alias": {"W": len(wiki_pages), "baseline_direct": len(baseline),
                  "new_by_stage": stage_new, "new_total": len(new_matches),
                  "ambiguous_rejected": ambiguous, "which": which_cnt,
                  "expanded_total": n_expand, "sample_pass": [n_pass, len(sample)]},
        "triple": {"pre_direct": pre_n, "post_expanded": post_n,
                   "criteria": "day-from ∧ pre[f-90,f-1]≥85 ∧ post[f,f+90]≥86"},
        "fill_nonnull": fill_tbl,
    }
    with open(os.path.join(OUT, "meta.json"), "w") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "run1016.out"), "w") as fh:
        fh.write("\n".join(log) + "\n")
    say("meta.json · run1016.out 기록 완료")


if __name__ == "__main__":
    main()
