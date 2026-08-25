#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사이클 1031 — [해석] 레인 v1 첫 사이클: 정독 쌍비교.

사전등록: docs/탐색/1031.md (실측 «전» 커밋 · 조항 66).
정본 절차: docs/루프.md 제7장 [해석] 레인 v1 (커밋 567fe5c13).

세계 명제: 「같은 IP 가 두 번 연 팝업의 결과 차이는, 사건 직전 자료를 사람처럼 읽으면 사전에 가릴 수 있다」

봉인: 판독 자료 생성기가 결과 필드를 제거한다(기계 검사) · 판독 산출을 «먼저» 커밋하고 채점은 그 뒤.
판독기: `claude -p --model sonnet` (무료 CLI 경로 · 유료 API 절대 금지 — ANTHROPIC_API_KEY 존재 시 중단).
항목마다 새 프로세스(오염 차단) · 중립 작업 디렉터리(저장소 CLAUDE.md·프로젝트 메모리 미적재) ·
도구 차단(웹검색 포함) · MCP 차단.

하위명령: build | probe | read | tri | score
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures as cf
import datetime as dt
import glob
import gzip
import hashlib
import importlib.util
import json
import math
import os
import random
import re
import subprocess
import sys

import numpy as np

# ── 경로 ─────────────────────────────────────────────────────────────────────
REPO = "/Users/ax/world_model"
F = "/Users/ax/wm_harvest/foundation"
OUT = os.path.join(F, "interp1031")
ITEMS = os.path.join(OUT, "items")
WORK = os.path.join(OUT, "work")
PAIRS1020 = os.path.join(F, "ceiling/pairs1020.json")
LEDGER = os.path.join(F, "ledger_interventions/ledger.jsonl")
EVENTS = os.path.join(F, "event_ledger/events.jsonl.gz")
SNAPDIR = os.path.join(F, "event_response/panel_snapshot")
EDOCS = os.path.join(F, "entity_docs")
R1027 = os.path.join(REPO, "runners/event_response1027.py")

# ── 사전 고정 상수 (등록문 §2~§6 — 여기 바꾸면 등록 위반) ─────────────────────
SEED = 1031
MODEL = "sonnet"
N_DOC = 8                 # 회차(사건)당 정독 발췌 상한
CALL_CAP = 560            # 총 판독기 호출 상한 (사전등록)
B_PAIRS = 30              # B층 표본 쌍 수
B_MAX_ENT = 3             # 개체 재사용 상한
B_MAX_GROUP = 6           # (도메인,유형) 군당 상한
ARMS = ("a", "b", "c")
CALL_TIMEOUT = 180
RETRY = 2
PAR = 4                   # 동시 호출 (CPU 아님 · 망 대기)

# 결과 누출 정규식 — 이 정규식에 걸리는 «발췌»는 ⓒ 자료에서 탈락시킨다(계수 게재).
RESULT_RE = re.compile(
    r"(방문객|방문자|관람객|관객수|관객\s*수|입장객|누적\s*관람|누적\s*방문|동원|"
    r"매출|억\s*원|만\s*명|천\s*명|[0-9][0-9,\.]*\s*명|명\s*돌파|흥행\s*수익|"
    r"티켓\s*판매|일평균|하루\s*평균|조회수|페이지뷰)")
# 자료 파일 전체에 대한 금칙 (원장 «결과 칸 이름»)
# 🔴 자 수리 1 (2026-08-25 · 조항 66 전후 공개): 구판 FORBID 는 과업 «문구»
#   "반응 크기"·"peak" 를 포함해 B층 과업 라벨 자신과 충돌했다(히트 270 = 30쌍×3팔×3문안 —
#   전부 자기 문구, 실제 결과 칸 히트 0). 신판은 충돌 문구를 빼고, 대신 **값 수준** 검사
#   (FORBID_VALUES — 그 항목의 실제 결과 «숫자»가 자료에 있는가)를 넣어 «더 강하게» 만든다.
FORBID = ("u_daily_visitors", "visitors_total", "sales_krw", "label_trust_grade", "lnUbar")

STAMP_SIGN = "부호 서명: 쌍 비교 «정확도»는 높을수록 좋다. ⓒ 정확도가 «낮을수록» 나쁘다."
STAMP_CAUSAL = ("인과 화법 금지 — 판독이 엮은 서사는 그 자체로 인과가 아니다(7-나 5). "
                "링크는 ⓐ시간순서·ⓑ근거sha·ⓒ대조검사 셋을 통과해야 「인과 후보」다.")


# ── 유틸 ─────────────────────────────────────────────────────────────────────
def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def now():
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def dord(s):
    y, m, d = int(s[:4]), int(s[5:7]), int(s[8:10])
    return dt.date(y, m, d).toordinal()


def load_1027():
    spec = importlib.util.spec_from_file_location("er1027", R1027)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["er1027"] = mod
    spec.loader.exec_module(mod)
    return mod


def guard_free():
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
        if os.environ.get(k):
            raise SystemExit(f"🔴 유료 API 경로 흔적({k}) — 이 사이클은 무료 CLI 경로만 쓴다. 중단.")


# ── 문서 색인 ────────────────────────────────────────────────────────────────
def build_doc_index(keys, cache):
    """entity_docs 3원천 1패스 → {key: [[pub, src, doc_id], ...]}"""
    if os.path.exists(cache):
        return json.load(open(cache))
    idx = {}
    for s in ("docs_fresh.jsonl.gz", "docs_sao.jsonl.gz", "docs_fineweb.jsonl.gz"):
        with gzip.open(os.path.join(EDOCS, s), "rt") as fh:
            for l in fh:
                r = json.loads(l)
                pub = r.get("published_at")
                if not pub:
                    continue
                att = r["부착"]
                if isinstance(att, str):
                    att = ast.literal_eval(att)
                for a in att:
                    if a[0] in keys:
                        idx.setdefault(a[0], []).append([pub, s, r["doc"]])
    json.dump(idx, open(cache, "w"), ensure_ascii=False)
    return idx


def fetch_heads(want):
    """want: {(src, doc_id)} → {(src,doc_id): (head280, text_sha16)}"""
    got = {}
    bysrc = {}
    for s, d in want:
        bysrc.setdefault(s, set()).add(d)
    for s, ids in bysrc.items():
        with gzip.open(os.path.join(EDOCS, s), "rt") as fh:
            for l in fh:
                r = json.loads(l)
                if r["doc"] in ids:
                    got[(s, r["doc"])] = (r.get("head280", ""), r.get("text_sha16", ""))
    return got


def pick_docs(idx, key, before, n):
    ds = [d for d in idx.get(key, []) if d[0] < before]
    ds.sort(key=lambda x: (x[0], x[2]), reverse=True)
    seen, outl = set(), []
    for d in ds:
        if d[2] in seen:
            continue
        seen.add(d[2])
        outl.append(d)
        if len(outl) >= n * 3:      # 정규식 탈락 여유
            break
    return outl


# ── 자료 렌더 ────────────────────────────────────────────────────────────────
ASK = ('결과가 더 좋았을 쪽을 «반드시» 하나 고르라. 모른다고 답하지 말 것.\n'
       '출력은 «JSON 한 줄»만. 다른 말 금지.\n'
       '{"pick":"갑"|"을","conf":1~5,"reason":"한 줄","known":true|false}\n'
       '  conf = 확신도(1 전혀 없음 ~ 5 매우 높음)\n'
       '  known = 이 사례(개체·회차)의 «실제 결과»를 이미 알고 있다면 true.\n')

WORDING = {
    1: ("당신은 오프라인 행사 흥행을 판정하는 분석가다.\n"
        "아래 두 후보 가운데 «결과가 더 좋았던» 쪽을 고르라.\n\n"),
    2: ("다음은 한 비교 과제다. 두 항목 중 성과가 더 컸던 쪽을 판정하라.\n"
        "직관이 아니라 주어진 자료만으로 판단하되, 자료가 부족해도 반드시 한쪽을 택하라.\n\n"),
    3: ("아래 갑/을 두 사례를 비교한다. 어느 쪽이 더 성공적이었겠는가.\n\n"),
}


def render(item, arm, wording, flip):
    L, R = item["L"], item["R"]
    a, b = (R, L) if flip else (L, R)
    s = WORDING[wording]
    s += f"[과제] {item['task']}\n"
    s += f"[대상] {item['head']}\n\n"
    if arm == "a":
        if a.get("name"):
            s += f"갑: {a['name']}\n을: {b['name']}\n(그 밖의 정보는 주어지지 않는다.)\n\n"
        else:
            s += "갑: 이 대상의 한 사례\n을: 이 대상의 다른 사례\n(그 밖의 정보는 주어지지 않는다.)\n\n"
    else:
        for tag, sd in (("갑", a), ("을", b)):
            s += f"■ {tag} — 관측 조건\n"
            for k, v in sd["cond"]:
                s += f"  · {k}: {v}\n"
            if arm == "c":
                ex = sd["docs"]
                s += f"  · 사건 직전 자료(발행일 순 · 이 사례가 열리기 «전» 문서만):\n"
                if not ex:
                    s += "     (해당 없음)\n"
                for e in ex:
                    s += f"     [{e['pub']}] {e['head']}\n"
            s += "\n"
    s += ASK
    return s


# ── 판독기 호출 ──────────────────────────────────────────────────────────────
_ENV_DROP = ("NODE_OPTIONS", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID",
             "CLAUDE_JOB_DIR", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_CHILD_SESSION",
             "CLAUDE_PID", "CLAUDE_EFFORT", "CLAUDE_CODE_EXECPATH", "AI_AGENT")


def call_reader(prompt):
    env = {k: v for k, v in os.environ.items() if k not in _ENV_DROP}
    env["OMP_NUM_THREADS"] = "1"
    cmd = ["claude", "-p", "--model", MODEL, "--disable-slash-commands",
           "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--disallowed-tools", "WebSearch WebFetch Bash Read Glob Grep Task Edit Write"]
    last = ""
    for _ in range(RETRY + 1):
        try:
            p = subprocess.run(cmd, input=prompt.encode("utf-8"), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, cwd=WORK, env=env, timeout=CALL_TIMEOUT)
            txt = p.stdout.decode("utf-8", "replace").strip()
            last = txt
            m = re.search(r"\{.*\}", txt, re.S)
            if m:
                try:
                    j = json.loads(m.group(0))
                except Exception:
                    j = None
                if j and str(j.get("pick", "")).strip() in ("갑", "을"):
                    return {"pick": str(j["pick"]).strip(),
                            "conf": j.get("conf"), "reason": str(j.get("reason", ""))[:300],
                            "known": bool(j.get("known", False)), "raw_ok": True}
        except subprocess.TimeoutExpired:
            last = "TIMEOUT"
    return {"pick": None, "conf": None, "reason": "", "known": None, "raw_ok": False,
            "raw": last[:300]}


# ══ build ════════════════════════════════════════════════════════════════════
def cmd_build(args):
    os.makedirs(ITEMS, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    t0 = now()
    mysha = sha256_file(os.path.abspath(__file__))
    er = load_1027()

    pj = json.load(open(PAIRS1020))
    pairs = pj["pairs"]
    led = {}
    rids = set()
    for p in pairs:
        rids.add(p["rid_a"]); rids.add(p["rid_b"])
    for l in open(LEDGER):
        r = json.loads(l)
        if r["record_id"] in rids:
            led[r["record_id"]] = r

    # 패널 (B층)
    key2dom, panel = {}, {}
    for pth in sorted(glob.glob(os.path.join(SNAPDIR, "*.jsonl.gz"))):
        dom = os.path.basename(pth).split(".")[0]
        with gzip.open(pth, "rt") as fh:
            for l in fh:
                r = json.loads(l)
                key2dom[r["키"]] = dom
                panel[r["키"]] = (r["날짜"], r["조회수"])

    keys = set(rids) | set(panel)
    idx = build_doc_index(keys, os.path.join(OUT, "docidx.json"))

    # ── A층 항목 ────────────────────────────────────────────────────────────
    def cond_of(rec):
        w, wh, wt, c = rec["A"]["when"], rec["A"]["where"], rec["A"]["what"], rec["C"]
        def s(v):
            return "미상" if v is None else v
        return [("개최 시기", w["opened_at"][:7]),
                ("기간(일)", s(w["duration_days"])),
                ("주말 비중", s(w["weekend_share"])),
                ("공휴일 수", s(w["holiday_days"])),
                ("장소유형", s(wh["venue_type"])),
                ("도시", s(wh["city"])),
                ("다점포", s(wh["multi_store"])),
                ("면적(평)", s(wh["area_pyeong"])),
                ("카테고리", s(wt["category"])),
                ("무료입장", s(wt["is_free_entry"])),
                ("예약필요", s(wt["reservation_required"])),
                ("직전 개최 수", s(c["ip_history"]["prior_count"])),
                ("첫 회 여부", s(c["ip_history"]["first_edition"]))]

    want = set()
    A_raw = []
    for i, p in enumerate(pairs):
        ra, rb = p["rid_a"], p["rid_b"]
        A, B = led[ra], led[rb]
        oa, ob = A["A"]["when"]["opened_at"], B["A"]["when"]["opened_at"]
        da = pick_docs(idx, ra, oa, N_DOC)
        db = pick_docs(idx, rb, ob, N_DOC)
        for d in da + db:
            want.add((d[1], d[2]))
        name = A["A"]["what"]["ip_name"] or A["A"]["what"]["brand"] or p["key"]
        A_raw.append(dict(iid=f"A{i:03d}", g=p["g"], key=p["key"], name=name,
                          ra=ra, rb=rb, oa=oa, ob=ob, da=da, db=db,
                          truth=("R" if p["d"] > 0 else "L"), d_abs=abs(p["d"])))

    # ── B층 항목 ────────────────────────────────────────────────────────────
    ev_ok = {}
    b_denom = dict(원장=0, 패널키없음=0, 창불비=0, 문서0=0, 가용=0)
    dense = {}
    with gzip.open(EVENTS, "rt") as fh:
        for l in fh:
            r = json.loads(l)
            b_denom["원장"] += 1
            k = r["개체키"]
            if k not in panel:
                b_denom["패널키없음"] += 1
                continue
            if k not in dense:
                ds, vs = panel[k]
                o = [dord(str(x)[:4] + "-" + str(x)[4:6] + "-" + str(x)[6:8]) for x in ds]
                o0, o1 = o[0], o[-1]
                arr = np.full(o1 - o0 + 1, np.nan)
                for oo, vv in zip(o, vs):
                    arr[oo - o0] = float(vv)
                dense[k] = (arr, o0)
            arr, o0 = dense[k]
            t = dord(r["event_time"])
            curve, _, nb, nw = er.extract_curve(arr, o0, t)
            if curve is None:
                b_denom["창불비"] += 1
                continue
            nd = len([d for d in idx.get(k, []) if d[0] < r["event_time"]])
            if nd == 0:
                b_denom["문서0"] += 1
                continue
            pd_, pv = er.peak_of(curve)
            b_denom["가용"] += 1
            ev_ok.setdefault((key2dom[k], r["정규유형"]), []).append(
                dict(k=k, t=r["event_time"], eid=r["사건id"], tier=r["신뢰층"],
                     yego=r.get("예고"), wiki=r.get("위키문서") or k, peak=abs(pv)))

    rng = random.Random(SEED)
    cand = []
    for (dom, typ), evs in sorted(ev_ok.items()):
        evs = sorted(evs, key=lambda e: e["eid"])
        for i in range(len(evs)):
            for j in range(i + 1, len(evs)):
                if evs[i]["k"] == evs[j]["k"]:
                    continue
                cand.append((dom, typ, evs[i], evs[j]))
    rng.shuffle(cand)
    used_eid, ent_cnt, used_entpair, grp_cnt = set(), {}, set(), {}
    B_raw = []
    n_tie = 0
    for dom, typ, e1, e2 in cand:
        if len(B_raw) >= B_PAIRS:
            break
        if e1["eid"] in used_eid or e2["eid"] in used_eid:
            continue
        if ent_cnt.get(e1["k"], 0) >= B_MAX_ENT or ent_cnt.get(e2["k"], 0) >= B_MAX_ENT:
            continue
        ep = tuple(sorted((e1["k"], e2["k"])))
        if ep in used_entpair:
            continue
        if grp_cnt.get((dom, typ), 0) >= B_MAX_GROUP:
            continue
        if e1["peak"] == e2["peak"]:
            n_tie += 1
            continue
        used_eid.add(e1["eid"]); used_eid.add(e2["eid"])
        ent_cnt[e1["k"]] = ent_cnt.get(e1["k"], 0) + 1
        ent_cnt[e2["k"]] = ent_cnt.get(e2["k"], 0) + 1
        used_entpair.add(ep); grp_cnt[(dom, typ)] = grp_cnt.get((dom, typ), 0) + 1
        # 시간 오름차순 = L
        if e1["t"] > e2["t"]:
            e1, e2 = e2, e1
        d1 = pick_docs(idx, e1["k"], e1["t"], N_DOC)
        d2 = pick_docs(idx, e2["k"], e2["t"], N_DOC)
        for d in d1 + d2:
            want.add((d[1], d[2]))
        B_raw.append(dict(iid=f"B{len(B_raw):03d}", dom=dom, typ=typ, e1=e1, e2=e2,
                          d1=d1, d2=d2, truth=("L" if e1["peak"] > e2["peak"] else "R"),
                          d_abs=abs(e1["peak"] - e2["peak"])))

    heads = fetch_heads(want)

    # ── 항목 조립 + 봉인 정규식 ─────────────────────────────────────────────
    seal = dict(발췌후보=0, 정규식탈락=0, 채택=0, t0이후=0, 금칙히트=0)

    def mk_docs(ds, before):
        outl = []
        for pub, src, did in ds:
            seal["발췌후보"] += 1
            if pub >= before:
                seal["t0이후"] += 1
                continue
            h, tsha = heads.get((src, did), ("", ""))
            if not h:
                continue
            h = h.replace("\n", " ").strip()[:280]
            if RESULT_RE.search(h):
                seal["정규식탈락"] += 1
                continue
            outl.append(dict(pub=pub, head=h, sha16=tsha, src=src.split("_")[1].split(".")[0]))
            seal["채택"] += 1
            if len(outl) >= N_DOC:
                break
        return outl

    items, truth = [], {}
    for a in A_raw:
        it = dict(iid=a["iid"], layer="A", task="같은 개체가 두 번 연 「팝업 개최」 두 회차의 결과 비교",
                  head=f"{a['name']} (팝업 개최)",
                  L=dict(cond=cond_of(led[a["ra"]]), docs=mk_docs(a["da"], a["oa"])),
                  R=dict(cond=cond_of(led[a["rb"]]), docs=mk_docs(a["db"], a["ob"])),
                  meta=dict(g=a["g"], key=a["key"], ra=a["ra"], rb=a["rb"]))
        items.append(it)
        truth[a["iid"]] = a["truth"]
    for b in B_raw:
        def bc(e):
            return [("도메인", b["dom"]), ("사건 유형", b["typ"]),
                    ("사건 시기", e["t"][:7]), ("사전 예고", e["yego"] or "미상"),
                    ("원장 신뢰층", e["tier"])]
        it = dict(iid=b["iid"], layer="B",
                  task=f"같은 도메인·같은 유형(「{b['typ']}」) 두 사건의 관심 반응 크기 비교",
                  head=f"{b['dom']} · {b['typ']}",
                  L=dict(name=b["e1"]["wiki"], cond=[("대상", b["e1"]["wiki"])] + bc(b["e1"]),
                         docs=mk_docs(b["d1"], b["e1"]["t"])),
                  R=dict(name=b["e2"]["wiki"], cond=[("대상", b["e2"]["wiki"])] + bc(b["e2"]),
                         docs=mk_docs(b["d2"], b["e2"]["t"])),
                  meta=dict(dom=b["dom"], typ=b["typ"], eid1=b["e1"]["eid"], eid2=b["e2"]["eid"]))
        items.append(it)
        truth[b["iid"]] = b["truth"]

    # 순서 배정 (봉인 · 정답 무관)
    order = {}
    for it in items:
        for p in (1, 2, 3):
            r2 = random.Random(f"{SEED}|{it['iid']}|{p}")
            if p == 2:
                order[f"{it['iid']}|2"] = not order[f"{it['iid']}|1"]
            else:
                order[f"{it['iid']}|{p}"] = (r2.random() < 0.5)

    # 값 수준 금칙 (자 수리 1) — 그 항목의 «실제 결과 숫자»가 자료에 나타나면 봉인 파손
    def val_strings(it):
        vs = set()
        if it["layer"] == "A":
            for rid in (it["meta"]["ra"], it["meta"]["rb"]):
                Y = led[rid]["Y"]
                for v in (Y.get("u_daily_visitors"), Y.get("visitors_total"), Y.get("sales_krw")):
                    if v is None:
                        continue
                    n = int(round(float(v)))
                    for t in (str(n), f"{n:,}", str(v)):
                        if len(re.sub(r"\D", "", t)) >= 3:
                            vs.add(t)
            for a2 in A_raw:
                if a2["iid"] == it["iid"]:
                    vs.add(f"{a2['d_abs']:.3f}")
        else:
            for b2 in B_raw:
                if b2["iid"] == it["iid"]:
                    for e in (b2["e1"], b2["e2"]):
                        vs.add(f"{e['peak']:.3f}")
                        vs.add(f"{e['peak']:.4f}")
        return vs

    # 🔴 자 수리 2 (조항 66 전후 공개): 구판은 값 금칙을 «세기만» 했다(히트 9 — 전수 확인 결과
    #   전부 우연한 부분문자열: 쇼핑 상세문 "503677"⊃"367" · "정가 4,000원" · 날짜 "07.25.2019"⊃"5.2019").
    #   신판은 세는 데 그치지 않고 **그 발췌를 떨어뜨린 뒤 재검사**해 히트 0 을 요구한다.
    seal["값금칙_탈락발췌"] = 0
    for it in items:
        vstr0 = val_strings(it)
        for sd in (it["L"], it["R"]):
            keep = []
            for e in sd["docs"]:
                if any(v in e["head"] for v in vstr0):
                    seal["값금칙_탈락발췌"] += 1
                    seal["채택"] -= 1
                else:
                    keep.append(e)
            sd["docs"] = keep

    # 자료 파일 기록 + 금칙 검사
    seal["값금칙히트"] = 0
    man = []
    for it in items:
        vstr = val_strings(it)
        for arm in ARMS:
            for p in (1, 2, 3):
                txt = render(it, arm, p, order[f"{it['iid']}|{p}"])
                low = txt.lower()
                for f in FORBID:
                    if f.lower() in low:
                        seal["금칙히트"] += 1
                for v in vstr:
                    if v in txt:
                        seal["값금칙히트"] += 1
                fp = os.path.join(ITEMS, f"{it['iid']}_{arm}_p{p}.txt")
                with open(fp, "w") as fh:
                    fh.write(txt)
                man.append(dict(iid=it["iid"], layer=it["layer"], arm=arm, pass_=p,
                                flip=order[f"{it['iid']}|{p}"], sha256=sha256_text(txt),
                                n_doc_L=len(it["L"]["docs"]), n_doc_R=len(it["R"]["docs"])))

    A_docboth = sum(1 for it in items if it["layer"] == "A" and it["L"]["docs"] and it["R"]["docs"])
    B_docboth = sum(1 for it in items if it["layer"] == "B" and it["L"]["docs"] and it["R"]["docs"])

    def mde_bin(n):
        return 0.5 + 2.8016 * 0.5 / math.sqrt(n)

    meta = dict(사이클=1031, 시작=t0, 끝=now(), 러너sha256=mysha,
                러너sha_전후일치=(mysha == sha256_file(os.path.abspath(__file__))),
                입력sha256=dict(pairs1020=sha256_file(PAIRS1020), ledger=sha256_file(LEDGER),
                                events=sha256_file(EVENTS), r1027=sha256_file(R1027)),
                판독기=dict(모델=MODEL, 경로="claude -p (무료 CLI)", 유료API=False),
                호출상한=CALL_CAP,
                A층=dict(쌍=len([1 for it in items if it['layer'] == 'A']), 양측유문서=A_docboth),
                B층=dict(쌍=len([1 for it in items if it['layer'] == 'B']),
                         양측유문서=B_docboth, 분모=b_denom, 동률제외=n_tie),
                봉인=seal, 부호서명=STAMP_SIGN, 인과화법=STAMP_CAUSAL,
                MDE=dict(단일팔_이항_n47=round(mde_bin(47), 4),
                         단일팔_이항_n30=round(mde_bin(30), 4),
                         주대비_McNemar_공식="Δacc_MDE = 2.8016·√n_d / n  (n_d=불일치쌍)",
                         주대비_예시_n47={str(nd): round(2.8016 * math.sqrt(nd) / 47, 4)
                                          for nd in (8, 12, 16, 20, 24, 30)}),
                낙인=dict(B층="사건 원장 v0(1026) — 1028 v1 미커밋. 티처 #146: 원장 라벨의 "
                              "날짜-의미 거짓률 ~45%±7%p(판독자 1인·n=50) 낙인 병기. B층은 [관찰]."))
    json.dump(meta, open(os.path.join(OUT, "build_meta.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), ensure_ascii=False)
    json.dump(items, open(os.path.join(OUT, "items.json"), "w"), ensure_ascii=False)
    json.dump(truth, open(os.path.join(OUT, "truth.json"), "w"), ensure_ascii=False)
    # 저장소 커밋용(무명·무발췌) 사전등록 산출
    json.dump(dict(meta=meta, manifest=man),
              open(os.path.join(REPO, "runners/out1031_prereg.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=1))


# ══ probe ═══════════════════════════════════════════════════════════════════
def cmd_probe(args):
    guard_free()
    os.makedirs(WORK, exist_ok=True)
    # 양성 대조 4 (자료가 답을 명시) · 영 대조 4 (양쪽 동일)
    tasks = []
    for i in range(4):
        tasks.append(dict(pid=f"POS{i}", kind="pos", truth="L", prompt=(
            WORDING[1] + "[과제] 두 사례의 결과 비교\n[대상] 시험용 사례\n\n"
            "■ 갑 — 관측 조건\n  · 비고: 이 사례가 «더 좋은 결과»를 냈다고 자료에 명시되어 있다\n\n"
            "■ 을 — 관측 조건\n  · 비고: 이 사례가 «더 나쁜 결과»를 냈다고 자료에 명시되어 있다\n\n" + ASK)))
        tasks.append(dict(pid=f"NUL{i}", kind="null", truth=None, prompt=(
            WORDING[1] + "[과제] 두 사례의 결과 비교\n[대상] 시험용 사례\n\n"
            "■ 갑 — 관측 조건\n  · 비고: 정보 없음\n\n"
            "■ 을 — 관측 조건\n  · 비고: 정보 없음\n\n" + ASK)))
    res = []
    with cf.ThreadPoolExecutor(max_workers=PAR) as ex:
        for t, r in zip(tasks, ex.map(lambda t: call_reader(t["prompt"]), tasks)):
            res.append(dict(pid=t["pid"], kind=t["kind"], truth=t["truth"], **r))
    pos = [r for r in res if r["kind"] == "pos"]
    nul = [r for r in res if r["kind"] == "null"]
    out = dict(시각=now(), 호출=len(res),
               양성대조_정답=sum(1 for r in pos if r["pick"] == "갑"), 양성대조_n=len(pos),
               영대조_갑선택=sum(1 for r in nul if r["pick"] == "갑"), 영대조_n=len(nul),
               파싱실패=sum(1 for r in res if not r["raw_ok"]), 원문=res)
    json.dump(out, open(os.path.join(OUT, "probe.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "원문"}, ensure_ascii=False, indent=1))


# ══ read ════════════════════════════════════════════════════════════════════
def _do_read(job):
    iid, arm, p = job
    fp = os.path.join(ITEMS, f"{iid}_{arm}_p{p}.txt")
    txt = open(fp).read()
    r = call_reader(txt)
    r.update(iid=iid, arm=arm, pass_=p, item_sha256=sha256_text(txt), ts=now())
    return r


def _run_jobs(jobs, outpath, spent_before):
    if spent_before + len(jobs) > CALL_CAP:
        raise SystemExit(f"🔴 호출 상한 초과 — 사전등록 {CALL_CAP} · 이미 {spent_before} · 요청 {len(jobs)}")
    res = []
    with open(outpath, "a") as fh:
        with cf.ThreadPoolExecutor(max_workers=PAR) as ex:
            for i, r in enumerate(ex.map(_do_read, jobs)):
                res.append(r)
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                fh.flush()
                if (i + 1) % 25 == 0:
                    print(f"  {i+1}/{len(jobs)}", flush=True)
    return res


def cmd_read(args):
    guard_free()
    items = json.load(open(os.path.join(OUT, "items.json")))
    path = os.path.join(OUT, "readings.jsonl")
    done = set()
    if os.path.exists(path):
        for l in open(path):
            r = json.loads(l)
            done.add((r["iid"], r["arm"], r["pass_"]))
    jobs = [(it["iid"], arm, p) for it in items for arm in ARMS for p in (1, 2)
            if (it["iid"], arm, p) not in done]
    print(f"[read] 남은 호출 {len(jobs)} · 이미 {len(done)} · 시작 {now()}", flush=True)
    _run_jobs(jobs, path, len(done) + _probe_calls())
    print(f"[read] 끝 {now()}")


def _probe_calls():
    p = os.path.join(OUT, "probe.json")
    return json.load(open(p))["호출"] if os.path.exists(p) else 0


def cmd_tri(args):
    """이중 판독 불일치 → 3차 판독."""
    guard_free()
    man = {(m["iid"], m["arm"], m["pass_"]): m for m in json.load(open(os.path.join(OUT, "manifest.json")))}
    path = os.path.join(OUT, "readings.jsonl")
    R = {}
    for l in open(path):
        r = json.loads(l)
        R[(r["iid"], r["arm"], r["pass_"])] = r
    need = []
    for (iid, arm, p), r in list(R.items()):
        if p != 1:
            continue
        r2 = R.get((iid, arm, 2))
        if not r2:
            continue
        c1 = canon(r, man[(iid, arm, 1)])
        c2 = canon(r2, man[(iid, arm, 2)])
        if c1 is None or c2 is None or c1 != c2:
            if (iid, arm, 3) not in R:
                need.append((iid, arm, 3))
    # 🔴 등록 보정 (2026-08-25 11:2x · 방향 탐침 «후» · 실판독 «전» · §6 보정 1):
    #   방향 탐침에서 판독기의 «갑» 위치 편향이 4/4 로 드러났다 → 정보가 없는 팔(특히 A층 ⓐ)은
    #   회전 1·2 가 정본 좌표에서 «구조적으로» 불일치한다. 3차 판독 예산(90)이 모자랄 수 있으므로
    #   배분 우선순위를 여기서 «먼저» 고정한다: 주대비 우선 — A층 ⓒ→ⓑ→ⓐ, B층 ⓒ→ⓑ→ⓐ (군 내 iid 오름차순).
    #   예산 소진 후 미해소 항목은 «회전 1 정본 좌표»를 최종으로 쓴다(순서 동전이 씨앗 기반이고
    #   정답과 독립이므로 편향 없는 동전과 동치) · 「3차 미실시」로 계수하고 민감도(제외 재계산) 병기.
    PRIO = {("A", "c"): 0, ("A", "b"): 1, ("A", "a"): 2, ("B", "c"): 3, ("B", "b"): 4, ("B", "a"): 5}
    need.sort(key=lambda t: (PRIO[(t[0][0], t[1])], t[0]))
    spent = sum(1 for _ in open(path)) + _probe_calls()
    room = CALL_CAP - spent
    skipped = need[room:]
    need = need[:room]
    print(f"[tri] 3차 필요 {len(need) + len(skipped)} · 예산 여유 {room} · 실시 {len(need)} · 미실시 {len(skipped)}", flush=True)
    json.dump(dict(시각=now(), 필요=len(need) + len(skipped), 실시=len(need),
                   미실시=[list(x) for x in skipped]),
              open(os.path.join(OUT, "tri_budget.json"), "w"), ensure_ascii=False, indent=1)
    if need:
        _run_jobs(need, path, spent)
    print(f"[tri] 끝 {now()}")


def canon(r, m):
    """판독 pick(갑/을) → 정본 좌표(L/R). flip=True 면 갑=R."""
    if r["pick"] is None:
        return None
    if m["flip"]:
        return "R" if r["pick"] == "갑" else "L"
    return "L" if r["pick"] == "갑" else "R"


# ══ score ═══════════════════════════════════════════════════════════════════
def cmd_score(args):
    truth = json.load(open(os.path.join(OUT, "truth.json")))
    items = {it["iid"]: it for it in json.load(open(os.path.join(OUT, "items.json")))}
    man = {(m["iid"], m["arm"], m["pass_"]): m for m in json.load(open(os.path.join(OUT, "manifest.json")))}
    R = {}
    for l in open(os.path.join(OUT, "readings.jsonl")):
        r = json.loads(l)
        R[(r["iid"], r["arm"], r["pass_"])] = r

    fin, agree, tri_used, badparse, known_flags = {}, {}, 0, 0, {}
    nofb = set()
    for iid in items:
        for arm in ARMS:
            c = []
            for p in (1, 2):
                r = R.get((iid, arm, p))
                if not r:
                    continue
                if not r["raw_ok"]:
                    badparse += 1
                cc = canon(r, man[(iid, arm, p)])
                c.append(cc)
                if r.get("known"):
                    known_flags[(iid, arm)] = True
            if len(c) == 2 and c[0] is not None and c[0] == c[1]:
                agree[(iid, arm)] = True
                fin[(iid, arm)] = c[0]
            else:
                agree[(iid, arm)] = False
                r3 = R.get((iid, arm, 3))
                if r3:
                    tri_used += 1
                    c3 = canon(r3, man[(iid, arm, 3)])
                    if r3.get("known"):
                        known_flags[(iid, arm)] = True
                    votes = [x for x in c + [c3] if x]
                    fin[(iid, arm)] = max(set(votes), key=votes.count) if votes else None
                else:
                    # §6 보정 1: 3차 미실시 → 회전 1 정본 좌표 (씨앗 동전 = 정답 독립)
                    fin[(iid, arm)] = c[0] if c and c[0] else (c[1] if len(c) > 1 else None)
                    nofb.add((iid, arm))
            # 확신도(1차 판독 정본)
    def conf_of(iid, arm):
        r = R.get((iid, arm, 1))
        return r.get("conf") if r else None

    def acc(sel, arm):
        n = ok = 0
        for iid in sel:
            f = fin.get((iid, arm))
            if f is None:
                continue
            n += 1
            ok += int(f == truth[iid])
        return ok, n, (ok / n if n else None)

    A_all = [i for i in items if items[i]["layer"] == "A"]
    A_doc = [i for i in A_all if items[i]["L"]["docs"] and items[i]["R"]["docs"]]
    B_all = [i for i in items if items[i]["layer"] == "B"]
    B_doc = [i for i in B_all if items[i]["L"]["docs"] and items[i]["R"]["docs"]]

    def mcnemar(sel, a1, a2):
        b = c = 0
        for iid in sel:
            f1, f2 = fin.get((iid, a1)), fin.get((iid, a2))
            if f1 is None or f2 is None:
                continue
            o1, o2 = int(f1 == truth[iid]), int(f2 == truth[iid])
            if o1 == 1 and o2 == 0:
                b += 1
            elif o1 == 0 and o2 == 1:
                c += 1
        nd = b + c
        if nd == 0:
            return dict(b=b, c=c, n_d=0, p=None, MDE=None)
        p = 0.0
        for k in range(nd + 1):
            pk = math.comb(nd, k) * 0.5 ** nd
            if pk <= math.comb(nd, b) * 0.5 ** nd + 1e-12:
                p += pk
        return dict(b=b, c=c, n_d=nd, p=round(min(1.0, p), 5),
                    MDE=round(2.8016 * math.sqrt(nd) / len(sel), 4))

    def table(sel, name):
        t = dict(표본=name, n=len(sel))
        for arm in ARMS:
            ok, n, a = acc(sel, arm)
            t[arm] = dict(맞음=ok, n=n, 정확도=(round(a, 4) if a is not None else None),
                          일치율=round(sum(1 for i in sel if agree.get((i, arm))) / len(sel), 4))
        t["ⓒ−ⓑ"] = mcnemar(sel, "c", "b")
        t["ⓑ−ⓐ"] = mcnemar(sel, "b", "a")
        return t

    # 오염 민감도
    known_items = sorted({i for (i, a) in known_flags})
    def table_clean(sel, name):
        return table([i for i in sel if i not in known_items], name)

    # 확신도 상위층 (사후선택 낙인)
    def hi(sel, arm):
        return [i for i in sel if (conf_of(i, arm) or 0) >= 4]

    out = dict(시각=now(), 러너sha256=sha256_file(os.path.abspath(__file__)),
               판독총호출=len(R) + _probe_calls(), 호출상한=CALL_CAP,
               파싱실패=badparse, 삼차판독=tri_used,
               부호서명=STAMP_SIGN, 인과화법=STAMP_CAUSAL,
               표=[table(A_all, "A층 전량(47쌍)"), table(A_doc, "A층 양측유문서(주대비)"),
                   table(B_all, "B층 전량"), table(B_doc, "B층 양측유문서")],
               오염=dict(자진신고_항목수=len(known_items),
                         민감도_제외후=[table_clean(A_doc, "A층 양측유문서(오염제외)"),
                                        table_clean(B_all, "B층 전량(오염제외)")]),
               삼차미실시=dict(항목팔수=len(nofb),
                               낙인="예산 소진 — 회전 1 정본 좌표로 대체(정답 독립 동전)",
                               민감도_제외후=[table([i for i in A_all if (i, "c") not in nofb and (i, "b") not in nofb],
                                                    "A층 3차미실시 제외")]),
               확신도상위_관찰=dict(
                   낙인="사후선택 — [관찰] 등급",
                   A층_c_conf4이상=len(hi(A_doc, "c")),
                   A층_c_conf4이상_정확도=(lambda s: (round(acc(s, "c")[2], 4) if acc(s, "c")[1] else None))(hi(A_doc, "c"))),
               )
    json.dump(out, open(os.path.join(OUT, "scored.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(out, open(os.path.join(REPO, "runners/out1031_scored.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


def cmd_export(args):
    """저장소 커밋용 봉인 판독 산출(무명·무발췌 · 정답 무포함)."""
    R = []
    for l in open(os.path.join(OUT, "readings.jsonl")):
        r = json.loads(l)
        R.append(dict(iid=r["iid"], arm=r["arm"], pass_=r["pass_"], pick=r["pick"],
                      conf=r["conf"], known=r["known"], raw_ok=r["raw_ok"],
                      item_sha256=r["item_sha256"], ts=r["ts"]))
    meta = json.load(open(os.path.join(OUT, "build_meta.json")))
    probe = json.load(open(os.path.join(OUT, "probe.json"))) if os.path.exists(os.path.join(OUT, "probe.json")) else None
    if probe:
        probe = {k: v for k, v in probe.items() if k != "원문"}
    json.dump(dict(주의="봉인 판독 산출 — 정답 대조 «전» 커밋(제7장 7-나 ①). 실명·발췌 없음.",
                   시각=now(), 판독=len(R), 호출상한=CALL_CAP,
                   방향탐침=probe, 봉인=meta["봉인"], 판독기=meta["판독기"], 판독원문=R),
              open(os.path.join(REPO, "runners/out1031_readings.json"), "w"),
              ensure_ascii=False, indent=1)
    print("판독 수", len(R))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "probe", "read", "tri", "score", "export"])
    a = ap.parse_args()
    {"build": cmd_build, "probe": cmd_probe, "read": cmd_read,
     "tri": cmd_tri, "score": cmd_score, "export": cmd_export}[a.cmd](a)
