#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사이클 1034 — [해석] 레인 v3: 위약 발췌 대조(ⓓ) + 인과 체인 «대조 검사» 첫 집행.

사전등록: docs/탐색/1034.md (실측 «전» 커밋 · 조항 66).
정본 절차: docs/루프.md 제7장 [해석] 레인 (7-나 · 7-다) · 부칙 6 · 조항 59·66·67·78·79.

세계 명제(이 사이클이 «가르는» 것):
  1033 층 ㉮ 96쌍에서 「정독 발췌를 주면 «더» 못 맞힌다」(Δ=−0.1458 · p=0.0066 · 검정력 있는 관찰).
  두 읽기가 경쟁한다 —
    (A) 담론의 «내용»이 오도한다(세계의 답에 가깝다)
    (B) 발췌 «형식/파이프»(N=8 · 머리 280자 · 개체 귀속 파손)가 판독기의 주의를 뺏는다(고칠 수 있다)
  🔴 위약 발췌 대조가 이 둘을 가른다: 같은 개수·같은 길이·같은 형식인데 «관련 없는 개체»의 발췌를 준다.
    ⓓ−ⓑ ≈ ⓒ−ⓑ  → (B) 형식이 범인
    ⓓ−ⓑ ≈ 0 인데 ⓒ−ⓑ < 0 → (A) 내용이 오도

과업 2: 1033 이 낸 인과 링크 K=10 의 «반증 조건»을 실제로 실측한다(제7장 7-다 최초 실물).

봉인: ⓓ 판독 자료 생성기가 결과 필드를 코드 경로에서 분리한다(기계 검사 · rows 에서 y 제거) ·
      ⓓ 판독 산출을 «먼저» 커밋하고 채점은 그 «뒤».
인용: ⓑ·ⓒ 판독 라벨은 1033 산출을 «재사용»한다(새 호출 0). 표본도 1033 층 ㉮ 96쌍 «그대로»다.
      1033·1031·1030 산출물은 «읽기만» — 이 사이클은 자기 디렉터리 밖에 아무것도 안 쓴다.
판독기: `claude -p --model sonnet` 무료 CLI 경로만 — ANTHROPIC_API_KEY/AUTH_TOKEN/BASE_URL 이
      하나라도 있으면 중단(유료 API 절대 금지). 항목마다 새 프로세스 · 중립 작업 디렉터리 ·
      도구·MCP·슬래시 전면 차단.

하위명령: cite | build | probe | read | tri | export | score | chain | hygiene
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import time

import numpy as np

# ── 경로 ─────────────────────────────────────────────────────────────────────
REPO = "/Users/ax/world_model"
F = "/Users/ax/wm_harvest/foundation"
OUT = os.path.join(F, "interp1034")          # 🔴 이 사이클이 «쓰는» 유일한 디렉터리
ITEMS = os.path.join(OUT, "items")
WORK = os.path.join(OUT, "work")
O33 = os.path.join(F, "interp1033")          # 🔴 읽기 전용(무접촉)
I33_ITEMS = os.path.join(O33, "items")
LEDGER = os.path.join(F, "ledger_interventions/ledger.jsonl")
EDOCS = os.path.join(F, "entity_docs")
DOC = os.path.join(REPO, "docs/탐색/1034.md")
R1031 = os.path.join(REPO, "runners/interp1031.py")
R1033 = os.path.join(REPO, "runners/interp1033.py")
R1030C = os.path.join(REPO, "runners/variance1030c.py")

sys.path.insert(0, REPO)

# ── 인용하는 자·자료의 출처 (조항 66 — 잰 소스 sha · 등록 상수) ──────────────
SHA = {
    "runners/variance1030c.py":
        "b428e3afe7be6ea15c6b02d7ce2cf9c35ab414225d36fbeff1f3f43dcb65a66a",
    "runners/interp1031.py":
        "476d33941d73a7b8fb7e8159db33e93aa7dd5b0967b9e8f848a486875fbeec4c",
    "runners/interp1033.py":
        "eeb48e385a784e210570f75218c19b9fc0c2d29b290a0028c3e029d241d43948",
    "runners/out1033_readings.json":
        "f8ead94f88901d90d092c0b19b10b4dd6f5c08ad408aae679be0a37120854805",
    "runners/out1033_scored.json":
        "44ad42cc4991e20dbcdf207c3003596b839ce30f676945057c8ac7635598bf1a",
    "runners/out1033_chain.json":
        "df2e1199002028745a085a39fa3b95912f798928be0a1132b1bc5b6ab517d0ac",
    "ledger.jsonl":
        "9a76948d3e619424ceadcfb0e2c0c06eceb80992dfd36784b9cd554ed998cffd",
    "interp1033/items.json":
        "9e9adc6458be414c772d8f22af0f94c71e58435017fae1c241cfb80f31863e74",
    "interp1033/manifest.json":
        "6afb8747c1bc8080441f2af2ff503065914cf07aa7c006420634a30026a2815d",
    "interp1033/pairs1033.json":
        "6af35e489c8ec03b7d25eee5dba9685e6c9549c49fd1ff8d5520e99186236147",
    "interp1033/readings.jsonl":
        "5ca0baf647cd7d02094b5f44795477c1db316ad42232ccd7cab4c67ac82bf04b",
    "interp1033/plan.json":
        "a0d398bd775e47b1dedbbeeeb298fc13d11f30bd72e602393e406d1aa3f9ee9c",
    "interp1033/truth.json":
        "2e338565a7d783a2c966a09d0236d324347325ed6a140871ad8568f2eb641a3d",
    "interp1033/docidx1033.json":
        "6bd1598d32234ec9ed13cad3fc71dc3798c6e96c499a9921114813a60ec2756d",
}
SHA_PATH = {
    "runners/variance1030c.py": R1030C,
    "runners/interp1031.py": R1031,
    "runners/interp1033.py": R1033,
    "runners/out1033_readings.json": os.path.join(REPO, "runners/out1033_readings.json"),
    "runners/out1033_scored.json": os.path.join(REPO, "runners/out1033_scored.json"),
    "runners/out1033_chain.json": os.path.join(REPO, "runners/out1033_chain.json"),
    "ledger.jsonl": LEDGER,
    "interp1033/items.json": os.path.join(O33, "items.json"),
    "interp1033/manifest.json": os.path.join(O33, "manifest.json"),
    "interp1033/pairs1033.json": os.path.join(O33, "pairs1033.json"),
    "interp1033/readings.jsonl": os.path.join(O33, "readings.jsonl"),
    "interp1033/plan.json": os.path.join(O33, "plan.json"),
    "interp1033/truth.json": os.path.join(O33, "truth.json"),
    "interp1033/docidx1033.json": os.path.join(O33, "docidx1033.json"),
}

# 1030 §10-3 등록 실측 — 인용 대조값(재구성 항등 검사의 표적)
X_PAIRS = 735
X_GROUPS = 135

# ── 사전 고정 상수 (등록문 §2~§7 — 여기 바꾸면 등록 위반) ────────────────────
SEED = 1034            # 위약 공여자 추첨 씨앗
SEED_BOOT = 1033       # 🔴 붓스트랩 재표집 씨앗은 1033 «그대로» — 인용 항등 검사가 이 씨앗을
                       #   요구하고, ⓑⓒⓓ 세 팔이 «같은 그룹 표본»에서 재계산돼야 대비 «간»
                       #   차이의 CI 가 짝지어진다.
MODEL = "sonnet"
N_DOC = 8              # 사례당 발췌 상한 (1031→1033 승계 · ⓓ 도 «같은 수»)
N_DUMMY = 8            # 영 대조 더미 (양쪽 글자 단위 동일 · 위치 편향 재실측)
CALL_CAP = 320         # 🔴 총 판독기 호출 상한 (사전등록 수 · 기계 강제)
#   내역: 방향탐침 8 + ⓓ 96쌍×2회전 192 + 더미 8 = 208 · 3차 여유 112
DONOR_TRY = 6          # 위약 공여자 후보 (씨앗 순서 앞에서부터 이만큼 미리 길어 올린다)
B_BOOT = 2000          # 클러스터 붓스트랩 복제 (1033 승계)
BOOT_MIN = 20          # 복제 유효 최소 쌍 수 (1033 승계)
Z_MDE = 2.80158        # z(0.975)+z(0.80) — 1031→1033 산식 인용
P_D_PRIOR = 24.0 / 96  # 불일치쌍 비율 사전값 = 1033 «층 ㉮» ⓒ/ⓑ 실측 n_d=24/96
KPRIME_MIN = 6         # 🔴 이항 양측 α=0.05 가 «원리상» 유의를 낼 수 있는 최소 n (조항 78)
KPRIME_POW = 29        # 검정력 0.80 으로 |p−0.5|=0.25 를 잡는 데 필요한 n (정규 근사)
CALL_TIMEOUT = 180
RETRY = 2
PAR = 4                # 동시 호출 (CPU 아님 · 망 대기) · CPU ≤4 스레드
LOAD_MAX = 10.0

STAMP_SIGN = ("부호 서명: 쌍 비교 «정확도»는 높을수록 좋다. 주대비 Δ_D = acc(ⓓ) − acc(ⓑ) 이고 "
              "Δ_D < 0 이면 「위약 «발췌 형식» 자체가 해롭다」 쪽이다. "
              "🔴 위약 발췌가 ⓒ 만큼 해로우면 (B) 형식/파이프가 범인이다. "
              "부호를 뒤집어 읽는 순간 이 사이클은 무효다.")
STAMP_CAUSAL = ("인과 화법 금지 — 판독이 엮은 서사는 그 자체로 인과가 아니다(7-나 5). "
                "링크는 ⓐ시간순서·ⓑ근거sha·ⓒ대조검사 셋을 «전부» 통과해야 「인과 후보」다.")
STAMP_CONF = ("확신도는 받되 «가중 금지» — 1031 불변 · 1033 «역행» 2사이클 연속 실측. "
              "확신도는 [관찰] 칸으로만 게재한다.")
STAMP_GRADE = ("등급 [관찰] — K=10 소표본. 「판정」으로 승격 금지(사전 명기). "
               "체인 대조 검사의 이항 검정은 n<%d 에서 «원리상» 유의를 못 낸다(조항 78)." % KPRIME_MIN)


# ── 유틸 ─────────────────────────────────────────────────────────────────────
def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


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


def load_gate():
    while os.getloadavg()[0] > LOAD_MAX:
        print("[대기] load1=%.2f > %.1f" % (os.getloadavg()[0], LOAD_MAX), flush=True)
        time.sleep(20)


def tree_gate():
    """4-나 ⓪ 관문 — 작업 트리 = 가지의 커밋된 트리 (자기 파일 한정)."""
    mine = ["runners/interp1034.py", "docs/탐색/1034.md"]
    r = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--name-only", "HEAD", "--"]
                       + mine, cwd=REPO, capture_output=True, text=True)
    dirty = [x for x in r.stdout.split("\n") if x.strip()]
    if dirty:
        raise SystemExit("🔴 ⓪ 관문 실패 — 커밋 안 된 자기 파일: %r" % dirty)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    return {"관문": "작업트리=커밋트리", "자기파일": mine, "HEAD": head[:9]}


def src_gate():
    """조항 66 — 인용하는 모든 소스·자료의 sha 실물 대조. 어긋나면 측정 없이 중단."""
    got, bad = {}, {}
    for k, want in SHA.items():
        g = sha256_file(SHA_PATH[k])
        got[k] = g[:16]
        if g != want:
            bad[k] = g
    if bad:
        raise SystemExit("🔴 인용 소스 sha 불일치 — 측정 없이 중단: %r" % bad)
    return got


def guard_free():
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
        if os.environ.get(k):
            raise SystemExit("🔴 유료 API 경로 흔적(%s) — 이 사이클은 무료 CLI 경로만 쓴다. 중단." % k)


def mcnemar_mde(n_d, n):
    return Z_MDE * math.sqrt(n_d) / n if n else None


def binom_p(k, n):
    """이항 정확검정 양측 (p0=0.5) — 1033 산식 인용."""
    if not n:
        return None
    p = 0.0
    base = math.comb(n, k) * 0.5 ** n
    for i in range(n + 1):
        pi = math.comb(n, i) * 0.5 ** n
        if pi <= base + 1e-12:
            p += pi
    return round(min(1.0, p), 6)


# ── 판독기 호출 (1033 과 «같은» 명령줄 · 작업 디렉터리만 자기 것) ────────────
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
                    return {"pick": str(j["pick"]).strip(), "conf": j.get("conf"),
                            "reason": str(j.get("reason", ""))[:300],
                            "known": bool(j.get("known", False)), "raw_ok": True}
        except subprocess.TimeoutExpired:
            last = "TIMEOUT"
    return {"pick": None, "conf": None, "reason": "", "known": None, "raw_ok": False,
            "raw": last[:300]}


# ══ 공통 적재 (1033 산출물 «읽기만») ═════════════════════════════════════════
def load33():
    I33 = _load("interp1033", R1033)
    items = {it["iid"]: it for it in json.load(open(os.path.join(O33, "items.json")))}
    man33 = {(m["iid"], m["arm"], m["pass_"]): m
             for m in json.load(open(os.path.join(O33, "manifest.json")))}
    pl = {q["pid"]: q for q in json.load(open(os.path.join(O33, "pairs1033.json")))}
    R33 = {}
    for l in open(os.path.join(O33, "readings.jsonl")):
        r = json.loads(l)
        R33[(r["iid"], r["arm"], r["pass_"])] = r
    return I33, items, man33, pl, R33


def stratum_A(items, pl):
    """🔴 표본 인용 — 1033 §7-보 ㉢ 의 층 ㉮ 정의 그대로(양측 t0 이전 문서 ≥1건).
    재구성이 아니라 «되읽기»다: 판단은 봉인 시점 pairs1033.json 에서만 나온다."""
    sel = []
    for iid, it in sorted(items.items()):
        if it["kind"] != "pair":
            continue
        q = pl[it["meta"]["pid"]]
        if q["n_predoc_L"] >= 1 and q["n_predoc_R"] >= 1:
            sel.append(iid)
    return sel


def resolve(R, man, iid, arm, I33):
    """🔴 1033 채점기의 최종 라벨 결정 규칙을 «글자 그대로» 옮긴 것(조항 67).
    2회전 일치 → 그 값 · 불일치 → 3차 다수결 · 3차 없음 → 회전 1(없으면 2)."""
    cs, bad, known = [], 0, False
    for p in (1, 2):
        r = R.get((iid, arm, p))
        if not r:
            continue
        if not r["raw_ok"]:
            bad += 1
        cs.append(I33.canon(r, man[(iid, arm, p)]))
        if r.get("known"):
            known = True
    if len(cs) == 2 and cs[0] is not None and cs[0] == cs[1]:
        return dict(fin=cs[0], agree=True, tri=False, nofb=False, bad=bad, known=known)
    r3 = R.get((iid, arm, 3))
    if r3:
        c3 = I33.canon(r3, man[(iid, arm, 3)])
        if r3.get("known"):
            known = True
        votes = [x for x in cs + [c3] if x]
        return dict(fin=(max(set(votes), key=votes.count) if votes else None),
                    agree=False, tri=True, nofb=False, bad=bad, known=known)
    fin = cs[0] if cs and cs[0] else (cs[1] if len(cs) > 1 else None)
    return dict(fin=fin, agree=False, tri=False, nofb=True, bad=bad, known=known)


# ══ cite — 표본·라벨 인용 + 항등 검사 (판독기 호출 0 · 결과 «집계»만 만진다) ══
def cmd_cite(args):
    os.makedirs(OUT, exist_ok=True)
    t0 = now()
    gate0 = tree_gate()
    srcs = src_gate()
    I33, items, man33, pl, R33 = load33()
    SYM = stratum_A(items, pl)
    truth = json.load(open(os.path.join(O33, "truth.json")))

    fin, agr = {}, {}
    for iid in SYM:
        for arm in ("b", "c"):
            v = resolve(R33, man33, iid, arm, I33)
            fin[(iid, arm)] = v["fin"]
            agr[(iid, arm)] = v["agree"]

    def acc(arm):
        n = ok = 0
        for iid in SYM:
            f = fin.get((iid, arm))
            if f is None:
                continue
            n += 1
            ok += int(f == truth[iid])
        return ok, n, (round(ok / float(n), 4) if n else None)

    def mcnemar(a1, a2):
        b = c = npair = 0
        for iid in SYM:
            f1, f2 = fin.get((iid, a1)), fin.get((iid, a2))
            if f1 is None or f2 is None:
                continue
            npair += 1
            o1, o2 = int(f1 == truth[iid]), int(f2 == truth[iid])
            if o1 and not o2:
                b += 1
            elif o2 and not o1:
                c += 1
        nd = b + c
        if nd == 0 or npair == 0:
            return dict(b=b, c=c, n_d=nd, 짝분모=npair, p=None, MDE=None, Δacc=0.0)
        return dict(b=b, c=c, n_d=nd, 짝분모=npair, p=round(binom_p(b, nd), 5),
                    MDE=round(mcnemar_mde(nd, npair), 4),
                    Δacc=round((b - c) / float(npair), 4))

    pmeta = {}
    for iid in SYM:
        pmeta[iid] = items[iid]["meta"]

    def cluster(a1, a2):
        rows = []
        for iid in SYM:
            f1, f2 = fin.get((iid, a1)), fin.get((iid, a2))
            if f1 is None or f2 is None:
                continue
            m = pmeta[iid]
            rows.append((m["key_L"], m["key_R"],
                         int(f1 == truth[iid]) - int(f2 == truth[iid])))
        keys = sorted(set([r[0] for r in rows] + [r[1] for r in rows]))
        ki = {k: i for i, k in enumerate(keys)}
        rng = np.random.RandomState(SEED_BOOT)
        boots = []
        for _ in range(B_BOOT):
            pick = set(rng.randint(0, len(keys), len(keys)).tolist())
            s2 = [r[2] for r in rows if ki[r[0]] in pick and ki[r[1]] in pick]
            if len(s2) >= BOOT_MIN:
                boots.append(float(np.mean(s2)))
        return dict(IP그룹=len(keys), 유효복제=len(boots),
                    Δacc=round(float(np.mean([r[2] for r in rows])), 4),
                    클러스터SE=(round(float(np.std(boots, ddof=1)), 4) if len(boots) > 1 else None))

    okb, nb, ab = acc("b")
    okc, nc, ac = acc("c")
    mine = {
        "b.맞음": okb, "b.n": nb, "b.정확도": ab,
        "b.일치율": round(sum(1 for i in SYM if agr[(i, "b")]) / float(len(SYM)), 4),
        "c.맞음": okc, "c.n": nc, "c.정확도": ac,
        "c.일치율": round(sum(1 for i in SYM if agr[(i, "c")]) / float(len(SYM)), 4),
        "n": len(SYM),
    }
    mc = mcnemar("c", "b")
    cl = cluster("c", "b")
    for k in ("b", "c", "n_d", "p", "MDE", "Δacc"):
        mine["ⓒ−ⓑ." + k] = mc[k]
    for k in ("IP그룹", "유효복제", "클러스터SE"):
        mine["ⓒ−ⓑ 클러스터." + k] = cl[k]

    # 🔴 인용 대조값 — out1033_scored.json 의 「층 ㉮」 행에서 «읽어» 온다(손 전사 0)
    s33 = json.load(open(os.path.join(REPO, "runners/out1033_scored.json")))
    row = [t for t in s33["표"] if t["표본"].startswith("층 ㉮")][0]
    want = {
        "b.맞음": row["b"]["맞음"], "b.n": row["b"]["n"], "b.정확도": row["b"]["정확도"],
        "b.일치율": row["b"]["일치율"],
        "c.맞음": row["c"]["맞음"], "c.n": row["c"]["n"], "c.정확도": row["c"]["정확도"],
        "c.일치율": row["c"]["일치율"], "n": row["n"],
    }
    for k in ("b", "c", "n_d", "p", "MDE", "Δacc"):
        want["ⓒ−ⓑ." + k] = row["ⓒ−ⓑ"][k]
    for k in ("IP그룹", "유효복제", "클러스터SE"):
        want["ⓒ−ⓑ 클러스터." + k] = row["ⓒ−ⓑ 클러스터"][k]

    bad = {k: (mine[k], want[k]) for k in want if mine[k] != want[k]}
    if bad:
        raise SystemExit("🔴 표본·라벨 인용이 1033 게재값과 항등이 아니다 — 측정 없이 중단: %r" % bad)

    n = len(SYM)
    mde_reg = mcnemar_mde(P_D_PRIOR * n, n)
    out = {"사이클": 1034, "시작": t0, "끝": now(), "⓪ 관문": gate0,
           "러너sha256": sha256_file(os.path.abspath(__file__)),
           "인용소스sha16": srcs,
           "표본": {"정의": "1033 층 ㉮ 「양측 t0 이전 문서 ≥1건」 — 재구성 0 · 되읽기만",
                   "n_쌍": n, "iid": SYM,
                   "IP그룹": len(set([pmeta[i]["key_L"] for i in SYM]
                                    + [pmeta[i]["key_R"] for i in SYM])),
                   "고유record": len(set([pmeta[i]["rid_L"] for i in SYM]
                                        + [pmeta[i]["rid_R"] for i in SYM])),
                   "ⓒ 발췌수 (L,R) 최소": min(min(len(items[i]["L"]["docs"]),
                                                len(items[i]["R"]["docs"])) for i in SYM),
                   "ⓒ 발췌수 (L,R) 최대": max(max(len(items[i]["L"]["docs"]),
                                                len(items[i]["R"]["docs"])) for i in SYM)},
           "인용 항등 검사": {"칸수": len(want), "불일치": len(bad),
                            "판정": "%d/%d 정확 일치" % (len(want), len(want)),
                            "나의 재계산": mine, "1033 게재값": want},
           "MDE": {"주대비 ⓓ−ⓑ 등록": round(mde_reg, 4),
                   "산식": "Δacc_MDE = %.5f·√n_d / n" % Z_MDE,
                   "불일치쌍_사전값": round(P_D_PRIOR, 4),
                   "출처": "1033 층 ㉮ ⓒ/ⓑ 실측 n_d=24/96 (out1033_scored.json sha256 %s)"
                          % SHA["runners/out1033_scored.json"],
                   "1033 층 ㉮ 실측 MDE(인용)": row["ⓒ−ⓑ"]["MDE"],
                   "🔴 정직 신고": "n=96 은 1033 이 고정한 층 ㉮ 전량이다. 이 자·이 예산에서 "
                                 "MDE 는 ≈0.143 이고 그보다 «작은» 차는 원리상 못 가른다(조항 78)."},
           "호출계획": {"상한": CALL_CAP, "탐침": 8, "ⓓ 판독": 2 * n, "더미": N_DUMMY,
                      "3차 여유": CALL_CAP - 8 - 2 * n - N_DUMMY},
           "부호서명": STAMP_SIGN, "인과화법": STAMP_CAUSAL, "확신도": STAMP_CONF, "등급": STAMP_GRADE}
    json.dump(out, open(os.path.join(OUT, "cite1034.json"), "w"), ensure_ascii=False, indent=1)
    pr = dict(out)
    pr["표본"] = dict(out["표본"])
    print(json.dumps({k: v for k, v in pr.items() if k != "인용 항등 검사"},
                     ensure_ascii=False, indent=1))
    print("인용 항등 검사: %s · 불일치 %d" % (out["인용 항등 검사"]["판정"], len(bad)))


# ══ build — 위약 발췌 ⓓ 생성 + 봉인 검사 (판독기 호출 0 · 결과 «무접촉») ══════
def rows_meta():
    """🔴 봉인 §1 — build 경로가 결과(y)를 «못 보게» 한다.
    variance1030c.build_rows() 산출에서 y 를 제거하고, 제거를 기계로 확인한다."""
    C30 = _load("variance1030c", R1030C)
    rows, lad, _m = C30.build_rows()
    out = []
    for r in rows:
        d = {k: v for k, v in r.items() if k not in ("y",)}
        out.append(d)
    for d in out:
        if "y" in d:
            raise SystemExit("🔴 봉인 위반 — build 경로에 y 가 남았다")
    return out, lad


def cmd_build(args):
    os.makedirs(ITEMS, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    t0 = now()
    gate0 = tree_gate()
    srcs = src_gate()
    mysha = sha256_file(os.path.abspath(__file__))
    load_gate()

    I31 = _load("interp1031", R1031)
    I33, items33, man33, pl, _R33 = load33()
    SYM = stratum_A(items33, pl)
    cite = json.load(open(os.path.join(OUT, "cite1034.json")))
    if cite["표본"]["iid"] != SYM:
        raise SystemExit("🔴 표본이 cite 와 다르다 — 중단")

    rows, lad = rows_meta()
    key_of = {r["record_id"]: r["key"] for r in rows}
    idx = json.load(open(os.path.join(O33, "docidx1033.json")))
    led = {}
    for l in open(LEDGER):
        r = json.loads(l)
        led[r["record_id"]] = r
    open_of = {k: v["A"]["when"]["opened_at"] for k, v in led.items()}

    # ── 공여자 풀 (사전 고정) ────────────────────────────────────────────────
    pool = sorted([rid for rid in idx if rid in key_of and rid in open_of])

    seal = dict(위약후보=0, 정규식탈락=0, 본문결측=0, t0이후=0, 채택=0,
                값금칙_탈락발췌=0, 값금칙히트=0, 금칙히트=0,
                본문sha_겹침_탈락=0, 겹침_관여항목=0,
                공여자_부족_재추첨=0, 공여자_실패_사이드=0)

    def donor_order(pid, side, ban_rid, ban_key):
        cand = [d for d in pool if d not in ban_rid and key_of[d] not in ban_key]
        cand.sort(key=lambda d: hashlib.sha256(
            ("%d|%s|%s|%s" % (SEED, pid, side, d)).encode()).hexdigest())
        return cand

    # 1단계 — 각 사이드의 공여자 후보 DONOR_TRY 개와 그 후보 문서를 한 번에 긁는다
    plan = {}
    want_docs = set()
    for iid in SYM:
        it = items33[iid]
        m = it["meta"]
        ban_rid = {m["rid_L"], m["rid_R"]}
        ban_key = {m["key_L"], m["key_R"]}
        for side in ("L", "R"):
            k = len(it[side]["docs"])
            t0x = open_of[m["rid_" + side]]
            cands = donor_order(m["pid"], side, ban_rid, ban_key)[:DONOR_TRY]
            per = []
            for d in cands:
                before = min(open_of[d], t0x)
                ds = I31.pick_docs(idx, d, before, N_DOC)
                per.append((d, ds))
                for pub, src, did in ds:
                    want_docs.add((src, did))
            plan[(iid, side)] = dict(k=k, t0x=t0x, cands=per)
    print("[build] 후보 문서 %d 건 머리 채취 시작 %s" % (len(want_docs), now()), flush=True)
    heads = I31.fetch_heads(want_docs)
    print("[build] 머리 채취 끝 %s · 획득 %d" % (now(), len(heads)), flush=True)

    # 값 수준 금칙 — 그 «항목»의 실제 결과 숫자 (1033 자 수리 2 판 인용·재사용)
    def val_strings(iid):
        vs = set()
        m = items33[iid]["meta"]
        for rid in (m["rid_L"], m["rid_R"]):
            Y = led[rid]["Y"]
            for v in (Y.get("u_daily_visitors"), Y.get("visitors_total"), Y.get("sales_krw")):
                if v is None:
                    continue
                n_ = int(round(float(v)))
                for t in (str(n_), "{:,}".format(n_), str(v)):
                    if len(re.sub(r"\D", "", t)) >= 3:
                        vs.add(t)
        return vs

    # 2단계 — 사이드마다 「k건을 채우는 첫 공여자」를 취한다
    # 🔴 자 수리 1 (조항 66 · 판독 «전» · 결과 무접촉): 구판은 공여자 «개체»만 갈랐다. 그런데
    #   부착이 다대다라 «다른 개체»의 문서가 진짜 발췌와 «같은 본문»(text_sha16 동일)일 수 있고,
    #   구판 실행에서 실제로 11건이 걸려 §5-2 ⑤ 「발췌 sha 겹침 0」이 «측정 없이 중단»을 냈다.
    #   신판은 그 문서를 «뽑는 자리»에서 떨어뜨린다 — 등록 규칙의 «강화»이지 완화가 아니다
    #   (위약이 진짜 담론을 조금도 못 나르게 만든다). 탈락 수와 관여 항목 수를 게재한다.
    placebo, donor_pick = {}, {}
    for iid in SYM:
        vs0 = val_strings(iid)
        real_sha = set(e["sha16"] for e in items33[iid]["L"]["docs"]) | \
            set(e["sha16"] for e in items33[iid]["R"]["docs"])
        hit0 = seal["본문sha_겹침_탈락"]
        used = set()
        for side in ("L", "R"):
            pl_ = plan[(iid, side)]
            k, t0x = pl_["k"], pl_["t0x"]
            got = None
            for d, ds in pl_["cands"]:
                if d in used:
                    continue
                outl = []
                for pub, src, did in ds:
                    seal["위약후보"] += 1
                    if pub >= t0x:
                        seal["t0이후"] += 1
                        continue
                    hd, tsha = heads.get((src, did), ("", ""))
                    if not hd:
                        seal["본문결측"] += 1
                        continue
                    hd = hd.replace("\n", " ").strip()[:280]
                    if I31.RESULT_RE.search(hd):
                        seal["정규식탈락"] += 1
                        continue
                    if any(v in hd for v in vs0):
                        seal["값금칙_탈락발췌"] += 1
                        continue
                    if tsha in real_sha:          # 🔴 자 수리 1 — 진짜 발췌와 «같은 본문» 배제
                        seal["본문sha_겹침_탈락"] += 1
                        continue
                    outl.append(dict(pub=pub, head=hd, sha16=tsha,
                                     src=src.split("_")[1].split(".")[0]))
                    if len(outl) >= k:
                        break
                if len(outl) >= k:
                    got = (d, outl[:k])
                    break
                seal["공여자_부족_재추첨"] += 1
            if got is None:
                seal["공여자_실패_사이드"] += 1
                raise SystemExit("🔴 위약 공여자 실패 — %s/%s (후보 %d 전부 k=%d 미달). "
                                 "등록 규칙상 이 사이드는 만들 수 없다." % (iid, side, DONOR_TRY, k))
            used.add(got[0])
            donor_pick[(iid, side)] = got[0]
            placebo[(iid, side)] = got[1]
            seal["채택"] += len(got[1])
        if seal["본문sha_겹침_탈락"] > hit0:
            seal["겹침_관여항목"] += 1

    # ── ⓓ 항목 조립 (cond 는 ⓑ·ⓒ 와 «글자 단위로» 같다 — 발췌만 위약으로 바꾼다) ──
    items, dmeta = [], {}
    for iid in SYM:
        s = items33[iid]
        it = dict(iid=iid, kind="pair", task=s["task"], head=s["head"],
                  L=dict(cond=s["L"]["cond"], docs=placebo[(iid, "L")]),
                  R=dict(cond=s["R"]["cond"], docs=placebo[(iid, "R")]),
                  meta=dict(pid=s["meta"]["pid"]))
        items.append(it)
        dmeta[iid] = dict(donor_L=donor_pick[(iid, "L")], donor_R=donor_pick[(iid, "R")])

    dummies = []
    for i, it in enumerate(items[:N_DUMMY]):
        dummies.append(dict(iid="Z%02d" % i, kind="dummy", task=it["task"], head=it["head"],
                            L=dict(cond=it["L"]["cond"], docs=it["L"]["docs"]),
                            R=dict(cond=it["L"]["cond"], docs=it["L"]["docs"]),
                            meta=dict(src_iid=it["iid"])))
    all_items = items + dummies

    # ── 제시 순서 — 🔴 1033 manifest 의 flip 을 «인용»한다 ────────────────────
    #    같은 씨앗·같은 항목·정답 독립이고, ⓑⓒⓓ 세 팔이 «같은 순서»를 받으므로
    #    순서가 팔 «간» 대비를 교란할 수 없다. 회전 2 는 회전 1 의 정확한 반전(1033 성질 승계).
    flip = {}
    for iid in SYM:
        for p in (1, 2, 3):
            flip["%s|%d" % (iid, p)] = man33[(iid, "c", p)]["flip"]
    for d in dummies:
        for p in (1, 2, 3):
            flip["%s|%d" % (d["iid"], p)] = flip["%s|%d" % (d["meta"]["src_iid"], p)]
    inv = sum(1 for iid in SYM if flip["%s|1" % iid] != flip["%s|2" % iid])

    # ── 렌더 — 🔴 1033 의 render 를 «임포트해» 쓴다(조항 67 · 형식 글자 단위 항등) ──
    man, difflines = [], []
    for it in all_items:
        vs = val_strings(it["iid"]) if it["kind"] == "pair" else set()
        for p in (1, 2, 3):
            txt = I33.render(it, "c", p, flip["%s|%d" % (it["iid"], p)])
            low = txt.lower()
            for f in I31.FORBID:
                if f.lower() in low:
                    seal["금칙히트"] += 1
            for v in vs:
                if v in txt:
                    seal["값금칙히트"] += 1
            fp = os.path.join(ITEMS, "%s_d_p%d.txt" % (it["iid"], p))
            with open(fp, "w") as fh:
                fh.write(txt)
            man.append(dict(iid=it["iid"], kind=it["kind"], arm="d", pass_=p,
                            flip=flip["%s|%d" % (it["iid"], p)], sha256=sha256_text(txt),
                            n_doc_L=len(it["L"]["docs"]), n_doc_R=len(it["R"]["docs"])))
            # ⓒ 대 ⓓ 문면 대조 — 다른 줄은 «발췌 줄»뿐이어야 한다
            if it["kind"] == "pair":
                cpath = os.path.join(I33_ITEMS, "%s_c_p%d.txt" % (it["iid"], p))
                a = open(cpath).read().split("\n")
                b = txt.split("\n")
                same_len = (len(a) == len(b))
                diff = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
                nonexc = [i for i in diff if not a[i].startswith("     [")]
                difflines.append(dict(iid=it["iid"], pass_=p, 줄수동일=same_len,
                                      다른줄=len(diff), 발췌아닌_다른줄=len(nonexc)))

    bad_fmt = [d for d in difflines if (not d["줄수동일"]) or d["발췌아닌_다른줄"] > 0]
    if bad_fmt:
        raise SystemExit("🔴 형식 항등 실패 — ⓒ 와 ⓓ 가 발췌 «밖»에서 다르다: %r" % bad_fmt[:5])

    # ── 위약 무관성 기계 검사 ────────────────────────────────────────────────
    chk = dict(공여자_진짜개체와_겹침=0, 공여자_IP그룹_겹침=0, 발췌sha_겹침=0,
               발췌수_불일치=0, 공여자_좌우동일=0, t0이후_위반=0)
    len_c, len_d = [], []
    src_c, src_d = {}, {}
    for iid in SYM:
        s = items33[iid]
        m = s["meta"]
        for side in ("L", "R"):
            d = donor_pick[(iid, side)]
            if d in (m["rid_L"], m["rid_R"]):
                chk["공여자_진짜개체와_겹침"] += 1
            if key_of[d] in (m["key_L"], m["key_R"]):
                chk["공여자_IP그룹_겹침"] += 1
            csall = set(e["sha16"] for e in s["L"]["docs"]) | set(e["sha16"] for e in s["R"]["docs"])
            ds = set(e["sha16"] for e in placebo[(iid, side)])
            chk["발췌sha_겹침"] += len(ds & csall)
            if len(placebo[(iid, side)]) != len(s[side]["docs"]):
                chk["발췌수_불일치"] += 1
            for e in placebo[(iid, side)]:
                if e["pub"] >= open_of[m["rid_" + side]]:
                    chk["t0이후_위반"] += 1
                len_d.append(len(e["head"]))
                src_d[e["src"]] = src_d.get(e["src"], 0) + 1
            for e in s[side]["docs"]:
                len_c.append(len(e["head"]))
                src_c[e["src"]] = src_c.get(e["src"], 0) + 1
        if donor_pick[(iid, "L")] == donor_pick[(iid, "R")]:
            chk["공여자_좌우동일"] += 1
    if any(v for k, v in chk.items()):
        raise SystemExit("🔴 위약 무관성 검사 실패 — 측정 없이 중단: %r" % chk)

    n = len(items)
    planned = 8 + 2 * n + len(dummies)
    mde_reg = mcnemar_mde(P_D_PRIOR * n, n)
    from pretrain.mde_guard import assert_mde, MdeGateError
    try:
        st = assert_mde(mde_reg, 0.1458, SHA["runners/out1033_scored.json"][:32])
        st["결과"] = "통과(겨냥 ≥ MDE)"
    except MdeGateError as e:
        st = {"결과": "미달", "사유": str(e), "MDE": mde_reg, "겨냥 효과": 0.1458,
              "낙인": "부칙 6 ㉯ — [판정] 레인 금지. 본 대비는 [해석] 레인이고 판정 게이트가 "
                     "아니다(등록). 해상도 부족을 수로 게재한다."}

    meta = {"사이클": 1034, "시작": t0, "끝": now(), "러너sha256": mysha,
            "러너sha_전후일치": (mysha == sha256_file(os.path.abspath(__file__))),
            "⓪ 관문": gate0, "인용소스sha16": srcs, "문서_sha256": sha256_file(DOC),
            "봉인": {"y제거_기계확인": True,
                    "낙인": "build 경로는 variance1030c.build_rows() 산출에서 y 를 «제거한» "
                           "사본만 본다. truth 파일은 build 가 열지 않는다.",
                    **seal},
            "판독기": {"모델": MODEL, "경로": "claude -p (무료 CLI)", "유료API": False,
                     "도구차단": True, "MCP차단": True, "항목마다_새_프로세스": True,
                     "1033 대비 차이": "작업 디렉터리만 자기 것(무접촉). 명령줄·모델·차단목록 동일."},
            "표본": {"n_쌍": n, "정의": "1033 층 ㉮ 96쌍 인용", "더미": len(dummies)},
            "위약 규칙": {"공여자 풀": len(pool),
                       "추첨": "sha256(\"%d|<pid>|<side>|<rid_D>\") 오름차순 · 앞에서부터 "
                              "k건을 채우는 첫 공여자" % SEED,
                       "후보 상한": DONOR_TRY,
                       "발췌 규칙": "1031 pick_docs 그대로 · 발행일 내림차순 · 머리 280자 · N=%d"
                                  % N_DOC,
                       "시간 절단": "pub < min(공여자 t0, 제시 사례 t0) — 두 조건 «모두»",
                       "제외": "진짜 두 개체(record) · 그 두 IP그룹 · 좌우 공여자 서로 다름"},
            "위약 무관성 검사": {**chk, "판정": "6/6 통과 · 위반 0",
                             "자 수리 1": "구판(sha256 4ecec4dbf0c1f448…)은 공여자 «개체»만 갈랐고 본문 sha 겹침 11 로 «측정 없이 중단»했다. 신판은 진짜 발췌와 같은 본문(text_sha16)을 «뽑는 자리»에서 떨어뜨린다 — 규칙 강화 · 판독 0 상태에서 고쳤다(결과 무접촉)."},
            "형식 항등 검사": {"항목×문안": len(difflines),
                            "줄수 동일": sum(1 for d in difflines if d["줄수동일"]),
                            "발췌 «밖» 다른 줄": sum(d["발췌아닌_다른줄"] for d in difflines),
                            "발췌 줄 평균 차이": round(
                                sum(d["다른줄"] for d in difflines) / float(len(difflines)), 2),
                            "낙인": "ⓒ 와 ⓓ 프롬프트는 «발췌 줄»에서만 다르다(기계 확인)."},
            "형식 대칭 [관찰]": {
                "머리 길이 평균 ⓒ": round(sum(len_c) / float(len(len_c)), 1),
                "머리 길이 평균 ⓓ": round(sum(len_d) / float(len(len_d)), 1),
                "발췌 수 ⓒ": len(len_c), "발췌 수 ⓓ": len(len_d),
                "원천 분포 ⓒ": src_c, "원천 분포 ⓓ": src_d},
            "제시 순서": {"출처": "1033 manifest 인용(같은 씨앗·같은 항목·정답 독립)",
                       "회전2=회전1 반전 항목 수": inv, "표본 n": n},
            "호출": {"상한": CALL_CAP, "계획": planned, "3차 여유": CALL_CAP - planned,
                    "내역": "탐침 8 + ⓓ %d×2회전 %d + 더미 %d" % (n, 2 * n, len(dummies))},
            "MDE": {"주대비 ⓓ−ⓑ 등록": round(mde_reg, 4),
                   "산식": "Δacc_MDE = %.5f·√n_d / n" % Z_MDE,
                   "불일치쌍_사전값": round(P_D_PRIOR, 4),
                   "출처": "1033 층 ㉮ ⓒ/ⓑ 실측 n_d=24/96",
                   "부칙 6": st},
            "부호서명": STAMP_SIGN, "인과화법": STAMP_CAUSAL, "확신도": STAMP_CONF,
            "등급": STAMP_GRADE, "C층 사다리": lad}
    json.dump(meta, open(os.path.join(OUT, "build_meta.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), ensure_ascii=False)
    json.dump(all_items, open(os.path.join(OUT, "items.json"), "w"), ensure_ascii=False)
    json.dump({k[0] + "|" + k[1]: v for k, v in donor_pick.items()},
              open(os.path.join(OUT, "donors.json"), "w"), ensure_ascii=False)
    json.dump(dict(sym=SYM, dummies=[d["iid"] for d in dummies], flip=flip,
                   meta={i: items33[i]["meta"] for i in SYM}),
              open(os.path.join(OUT, "plan.json"), "w"), ensure_ascii=False)
    json.dump(dict(meta=meta, manifest=man),
              open(os.path.join(REPO, "runners/out1034_prereg.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=1))


# ══ probe — 측정 «전» 방향 탐침 (8호출 · 1033 문안 그대로) ═══════════════════
def cmd_probe(args):
    guard_free()
    os.makedirs(WORK, exist_ok=True)
    I33 = _load("interp1033", R1033)
    tasks = []
    for i in range(4):
        tasks.append(dict(pid="POS%d" % i, kind="pos", truth="갑", prompt=(
            I33.WORDING[1] + "[과제] 두 사례의 결과 비교\n[대상] 시험용 사례\n\n"
            "■ 사례 갑 — 관측 조건\n  · 비고: 이 사례가 «더 좋은 결과»를 냈다고 자료에 명시되어 있다\n\n"
            "■ 사례 을 — 관측 조건\n  · 비고: 이 사례가 «더 나쁜 결과»를 냈다고 자료에 명시되어 있다\n\n"
            + I33.ASK)))
        tasks.append(dict(pid="NUL%d" % i, kind="null", truth=None, prompt=(
            I33.WORDING[1] + "[과제] 두 사례의 결과 비교\n[대상] 시험용 사례\n\n"
            "■ 사례 갑 — 관측 조건\n  · 비고: 정보 없음\n\n"
            "■ 사례 을 — 관측 조건\n  · 비고: 정보 없음\n\n" + I33.ASK)))
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


# ══ read / tri ══════════════════════════════════════════════════════════════
def _do_read(job):
    iid, arm, p = job
    fp = os.path.join(ITEMS, "%s_%s_p%d.txt" % (iid, arm, p))
    txt = open(fp).read()
    r = call_reader(txt)
    r.update(iid=iid, arm=arm, pass_=p, item_sha256=sha256_text(txt), ts=now())
    return r


def _probe_calls():
    p = os.path.join(OUT, "probe.json")
    return json.load(open(p))["호출"] if os.path.exists(p) else 0


def _spent():
    path = os.path.join(OUT, "readings.jsonl")
    n = sum(1 for _ in open(path)) if os.path.exists(path) else 0
    return n + _probe_calls()


def _run_jobs(jobs, outpath, spent_before):
    if spent_before + len(jobs) > CALL_CAP:
        raise SystemExit("🔴 호출 상한 초과 — 사전등록 %d · 이미 %d · 요청 %d"
                         % (CALL_CAP, spent_before, len(jobs)))
    res = []
    with open(outpath, "a") as fh:
        with cf.ThreadPoolExecutor(max_workers=PAR) as ex:
            for i, r in enumerate(ex.map(_do_read, jobs)):
                res.append(r)
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                fh.flush()
                if (i + 1) % 40 == 0:
                    print("  %d/%d  %s" % (i + 1, len(jobs), now()), flush=True)
    return res


def cmd_read(args):
    guard_free()
    load_gate()
    plan = json.load(open(os.path.join(OUT, "plan.json")))
    path = os.path.join(OUT, "readings.jsonl")
    done = set()
    if os.path.exists(path):
        for l in open(path):
            r = json.loads(l)
            done.add((r["iid"], r["arm"], r["pass_"]))
    jobs = []
    for iid in plan["sym"]:
        for p in (1, 2):
            jobs.append((iid, "d", p))
    for z in plan["dummies"]:
        jobs.append((z, "d", 1))
    jobs = [j for j in jobs if j not in done]
    print("[read] 남은 호출 %d · 이미 %d · 시작 %s" % (len(jobs), len(done), now()), flush=True)
    _run_jobs(jobs, path, len(done) + _probe_calls())
    print("[read] 끝 %s" % now())


def cmd_tri(args):
    guard_free()
    I33 = _load("interp1033", R1033)
    man = {(m["iid"], m["arm"], m["pass_"]): m
           for m in json.load(open(os.path.join(OUT, "manifest.json")))}
    path = os.path.join(OUT, "readings.jsonl")
    R = {}
    for l in open(path):
        r = json.loads(l)
        R[(r["iid"], r["arm"], r["pass_"])] = r
    need = []
    for (iid, arm, p), r in list(R.items()):
        if p != 1 or iid.startswith("Z"):
            continue
        r2 = R.get((iid, arm, 2))
        if not r2:
            continue
        c1, c2 = I33.canon(r, man[(iid, arm, 1)]), I33.canon(r2, man[(iid, arm, 2)])
        if c1 is None or c2 is None or c1 != c2:
            if (iid, arm, 3) not in R:
                need.append((iid, arm, 3))
    need.sort(key=lambda t: t[0])
    spent = _spent()
    room = CALL_CAP - spent
    skipped, need = need[room:], need[:room]
    print("[tri] 3차 필요 %d · 예산 여유 %d · 실시 %d · 미실시 %d"
          % (len(need) + len(skipped), room, len(need), len(skipped)), flush=True)
    json.dump(dict(시각=now(), 필요=len(need) + len(skipped), 실시=len(need),
                   미실시=[list(x) for x in skipped]),
              open(os.path.join(OUT, "tri_budget.json"), "w"), ensure_ascii=False, indent=1)
    if need:
        _run_jobs(need, path, spent)
    print("[tri] 끝 %s" % now())


# ══ export — 봉인 판독 산출 (정답 대조 «전» 커밋) ════════════════════════════
def cmd_export(args):
    R = []
    for l in open(os.path.join(OUT, "readings.jsonl")):
        r = json.loads(l)
        R.append(dict(iid=r["iid"], arm=r["arm"], pass_=r["pass_"], pick=r["pick"],
                      conf=r["conf"], known=r["known"], raw_ok=r["raw_ok"],
                      item_sha256=r["item_sha256"], ts=r["ts"]))
    meta = json.load(open(os.path.join(OUT, "build_meta.json")))
    pp = os.path.join(OUT, "probe.json")
    probe = json.load(open(pp)) if os.path.exists(pp) else None
    if probe:
        probe = {k: v for k, v in probe.items() if k != "원문"}
    tb = os.path.join(OUT, "tri_budget.json")
    json.dump({"주의": "봉인 판독 산출 — 정답 대조 «전» 커밋(제7장 7-나 ①). 실명·발췌 없음.",
               "시각": now(), "판독": len(R), "호출상한": CALL_CAP,
               "총호출": len(R) + _probe_calls(), "방향탐침": probe,
               "봉인": meta["봉인"], "판독기": meta["판독기"], "표본": meta["표본"],
               "위약 규칙": meta["위약 규칙"], "위약 무관성 검사": meta["위약 무관성 검사"],
               "형식 항등 검사": meta["형식 항등 검사"], "MDE": meta["MDE"],
               "3차 예산": (json.load(open(tb)) if os.path.exists(tb) else None),
               "판독원문": R},
              open(os.path.join(REPO, "runners/out1034_readings.json"), "w"),
              ensure_ascii=False, indent=1)
    print("판독 수 %d · 총호출 %d / %d" % (len(R), len(R) + _probe_calls(), CALL_CAP))


# ══ score — 주대비 ⓓ−ⓑ + (A)/(B) 해석 문언 ══════════════════════════════════
def cmd_score(args):
    I33, items33, man33, pl, R33 = load33()
    plan = json.load(open(os.path.join(OUT, "plan.json")))
    SYM = plan["sym"]
    dummies = plan["dummies"]
    pmeta = plan["meta"]
    truth = json.load(open(os.path.join(O33, "truth.json")))
    man34 = {(m["iid"], m["arm"], m["pass_"]): m
             for m in json.load(open(os.path.join(OUT, "manifest.json")))}
    R34 = {}
    for l in open(os.path.join(OUT, "readings.jsonl")):
        r = json.loads(l)
        R34[(r["iid"], r["arm"], r["pass_"])] = r

    fin, agr, badparse, tri_used, nofb, known_flags = {}, {}, 0, 0, set(), {}
    for iid in SYM:
        for arm in ("b", "c"):
            v = resolve(R33, man33, iid, arm, I33)
            fin[(iid, arm)], agr[(iid, arm)] = v["fin"], v["agree"]
        v = resolve(R34, man34, iid, "d", I33)
        fin[(iid, "d")], agr[(iid, "d")] = v["fin"], v["agree"]
        badparse += v["bad"]
        tri_used += int(v["tri"])
        if v["nofb"]:
            nofb.add(iid)
        if v["known"]:
            known_flags[iid] = True

    def acc(sel, arm):
        n = ok = 0
        for iid in sel:
            f = fin.get((iid, arm))
            if f is None:
                continue
            n += 1
            ok += int(f == truth[iid])
        return ok, n, (round(ok / float(n), 4) if n else None)

    def mcnemar(sel, a1, a2):
        b = c = npair = 0
        for iid in sel:
            f1, f2 = fin.get((iid, a1)), fin.get((iid, a2))
            if f1 is None or f2 is None:
                continue
            npair += 1
            o1, o2 = int(f1 == truth[iid]), int(f2 == truth[iid])
            if o1 and not o2:
                b += 1
            elif o2 and not o1:
                c += 1
        nd = b + c
        if nd == 0 or npair == 0:
            return dict(b=b, c=c, n_d=nd, 짝분모=npair, p=None, MDE=None, Δacc=0.0)
        return dict(b=b, c=c, n_d=nd, 짝분모=npair, p=round(binom_p(b, nd), 5),
                    MDE=round(mcnemar_mde(nd, npair), 4),
                    Δacc=round((b - c) / float(npair), 4))

    def cluster(sel, a1, a2):
        """IP그룹 클러스터 붓스트랩 — 1030 §9-자 규칙 · 1033 씨앗 그대로.
        Δ 와 «백분위 95% 신뢰구간»을 함께 낸다."""
        rows = []
        for iid in sel:
            f1, f2 = fin.get((iid, a1)), fin.get((iid, a2))
            if f1 is None or f2 is None:
                continue
            m = pmeta[iid]
            rows.append((m["key_L"], m["key_R"],
                         int(f1 == truth[iid]) - int(f2 == truth[iid])))
        if not rows:
            return None
        keys = sorted(set([r[0] for r in rows] + [r[1] for r in rows]))
        ki = {k: i for i, k in enumerate(keys)}
        rng = np.random.RandomState(SEED_BOOT)
        boots = []
        for _ in range(B_BOOT):
            pick = set(rng.randint(0, len(keys), len(keys)).tolist())
            s2 = [r[2] for r in rows if ki[r[0]] in pick and ki[r[1]] in pick]
            if len(s2) >= BOOT_MIN:
                boots.append(float(np.mean(s2)))
        ci = ([round(float(np.percentile(boots, 2.5)), 4),
               round(float(np.percentile(boots, 97.5)), 4)] if len(boots) > 1 else None)
        return dict(IP그룹=len(keys), 유효복제=len(boots), 짝=len(rows),
                    Δacc=round(float(np.mean([r[2] for r in rows])), 4),
                    클러스터SE=(round(float(np.std(boots, ddof=1)), 4) if len(boots) > 1 else None),
                    CI95=ci, CI가_0을_포함=(None if ci is None else bool(ci[0] <= 0.0 <= ci[1])))

    tab = {}
    for arm in ("b", "c", "d"):
        ok, n, a = acc(SYM, arm)
        tab[arm] = dict(맞음=ok, n=n, 정확도=a, 우연대비p=binom_p(ok, n) if n else None,
                        일치율=round(sum(1 for i in SYM if agr[(i, arm)]) / float(len(SYM)), 4))
    con = {}
    for nm, a1, a2 in (("ⓓ−ⓑ (주대비)", "d", "b"), ("ⓒ−ⓑ (1033 인용·재계산)", "c", "b"),
                       ("ⓒ−ⓓ (차의 차 = 내용 몫)", "c", "d")):
        con[nm] = dict(McNemar=mcnemar(SYM, a1, a2), 클러스터=cluster(SYM, a1, a2))

    # ── 🔴 사전 고정 해석 문언 집행 (기계 판정 · 골대 이동 금지) ─────────────
    dD = con["ⓓ−ⓑ (주대비)"]["McNemar"]["Δacc"]
    mdeD = con["ⓓ−ⓑ (주대비)"]["McNemar"]["MDE"]
    dC = con["ⓒ−ⓑ (1033 인용·재계산)"]["McNemar"]["Δacc"]
    cdCI = con["ⓒ−ⓓ (차의 차 = 내용 몫)"]["클러스터"]["CI95"]
    cd0 = con["ⓒ−ⓓ (차의 차 = 내용 몫)"]["클러스터"]["CI가_0을_포함"]
    cond_B = bool(cd0) and (dD < 0) and (mdeD is not None and abs(dD) >= mdeD)
    cond_A = (mdeD is not None and abs(dD) < mdeD) and (cd0 is False)
    if cond_B and not cond_A:
        verdict = "(B) 형식/파이프가 범인"
        text = ("🔴 「형식/파이프가 범인 — 담론 «내용»의 유해성은 미확인 · 발췌 규칙 수리가 다음이다.」 "
                "관련 없는 개체의 발췌를 같은 개수·같은 길이·같은 형식으로 줘도 정확도가 "
                "같은 크기로 내려갔고(ⓓ−ⓑ = %s · 실측 MDE %s), ⓒ 와 ⓓ 의 차는 0 과 구별되지 "
                "않는다(95%% CI %s). 1033 층 ㉮ 의 −0.1458 을 「담론이 오도한다」로 읽는 것을 금한다."
                % (dD, mdeD, cdCI))
    elif cond_A and not cond_B:
        verdict = "(A) 담론 내용이 오도한다"
        text = ("🔴 「이 자료의 담론 «내용»이 이 과업에서 오도한다(귀속 파손 교란 병기 — 1028 낙인).」 "
                "위약 발췌는 해롭지 않은데(ⓓ−ⓑ = %s · |Δ| < 실측 MDE %s) 진짜 발췌만 해로웠고, "
                "ⓒ 와 ⓓ 의 차는 0 을 제외한다(95%% CI %s). "
                "🔴 그래도 «세계»에 대한 판정이 아니다 — 이 자료·이 판독기·이 발췌 규칙의 부호다."
                % (dD, mdeD, cdCI))
    else:
        verdict = "미판정"
        text = ("🔴 「미판정 — (A)도 (B)도 사전 고정 조건을 채우지 못했다.」 "
                "ⓓ−ⓑ = %s (실측 MDE %s) · ⓒ−ⓑ = %s · ⓒ−ⓓ 95%% CI %s (0 포함 = %s). "
                "부칙 6 ㉱ 화법: null 은 「효과 없음」이 아니라 「실측 MDE 미만」이다."
                % (dD, mdeD, dC, cdCI, cd0))

    dz = [R34.get((z, "d", 1)) for z in sorted(dummies)]
    dz = [x for x in dz if x]
    z_gap = sum(1 for x in dz if x["pick"] == "갑")
    late = {}
    for arm in ("b", "c", "d"):
        sel = [i for i in SYM if fin.get((i, arm))]
        k = sum(1 for i in sel if fin[(i, arm)] == "R")
        late[arm] = dict(R선택=k, n=len(sel), 비율=round(k / float(len(sel)), 4) if sel else None,
                         이항p=binom_p(k, len(sel)))
    late["정답_R비율"] = round(sum(1 for i in SYM if truth[i] == "R") / float(len(SYM)), 4)

    conf = {}
    for arm, RR in (("b", R33), ("c", R33), ("d", R34)):
        cc = {}
        for i in SYM:
            r = RR.get((i, arm, 1))
            if r and r.get("conf") is not None:
                cc[str(r["conf"])] = cc.get(str(r["conf"]), 0) + 1
        conf[arm] = cc

    def subtab(sel, name):
        t = dict(표본=name, n=len(sel))
        if not sel:
            t["낙인"] = "분모 0 — 미측정(조항 59)"
            return t
        for arm in ("b", "c", "d"):
            ok, n, a = acc(sel, arm)
            t[arm] = dict(맞음=ok, n=n, 정확도=a)
        t["ⓓ−ⓑ"] = mcnemar(sel, "d", "b")
        t["ⓒ−ⓓ"] = mcnemar(sel, "c", "d")
        return t

    out = dict(시각=now(), 러너sha256=sha256_file(os.path.abspath(__file__)),
               문서_sha256=sha256_file(DOC),
               표본=dict(n=len(SYM), 정의="1033 층 ㉮ 96쌍 인용",
                        IP그룹=len(set([pmeta[i]["key_L"] for i in SYM]
                                      + [pmeta[i]["key_R"] for i in SYM]))),
               판독총호출=len(R34) + _probe_calls(), 호출상한=CALL_CAP,
               새호출=len(R34), 인용라벨_새호출=0,
               파싱실패=badparse, 삼차판독=tri_used, 삼차미실시=len(nofb),
               부호서명=STAMP_SIGN, 인과화법=STAMP_CAUSAL, 확신도=STAMP_CONF, 등급=STAMP_GRADE,
               정확도표=tab, 대비=con,
               주대비판정=dict(판정=verdict, 문언=text,
                             사전고정조건=dict(
                                 B="CI(ⓒ−ⓓ) ∋ 0 ∧ Δ_D<0 ∧ |Δ_D| ≥ 실측 MDE(ⓓ−ⓑ)",
                                 A="|Δ_D| < 실측 MDE(ⓓ−ⓑ) ∧ CI(ⓒ−ⓓ) ∌ 0",
                                 그외="미판정"),
                             조건실측=dict(cond_B=cond_B, cond_A=cond_A,
                                        Δ_D=dD, MDE_D=mdeD, Δ_C=dC,
                                        CI_CD=cdCI, CI_CD_0포함=cd0)),
               영대조_위치편향=dict(더미=len(dz), 갑선택=z_gap,
                                  비율=round(z_gap / float(len(dz)), 4) if dz else None,
                                  이항p=binom_p(z_gap, len(dz)) if dz else None,
                                  낙인="양쪽이 «글자 단위로 동일»한 항목 — 정답 없음. 위치 편향만 잰다. "
                                       "1033 은 24/24 「갑」(p=1.19e-7)."),
               늦은쪽쏠림_관찰=late,
               확신도_관찰=dict(분포=conf, 낙인=STAMP_CONF),
               민감도=[subtab([i for i in SYM if i not in known_flags], "오염 자진신고 제외"),
                     subtab([i for i in SYM if i not in nofb], "3차 미실시 제외")],
               오염=dict(자진신고_항목수=len(known_flags)))
    json.dump(out, open(os.path.join(OUT, "scored.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(out, open(os.path.join(REPO, "runners/out1034_scored.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


# ══ chain — 🔴 인과 체인 «대조 검사» 첫 집행 (7-다 · 판독기 호출 0) ══════════
def cmd_chain(args):
    t0 = now()
    srcs = src_gate()
    C30 = _load("variance1030c", R1030C)
    rows, lad, _m = C30.build_rows()

    # ① 동결 함수 «인용» — 1030 §10-3 정합 규칙 그대로(조항 67)
    frozen = C30.matched_cross_ip(rows, {})
    if frozen["n_쌍"] != X_PAIRS or frozen["관여 IP그룹"] != X_GROUPS:
        raise SystemExit("🔴 인용 불일치 — 1030 §10-3 등록 %d쌍/%d그룹 대 실측 %d/%d"
                         % (X_PAIRS, X_GROUPS, frozen["n_쌍"], frozen["관여 IP그룹"]))

    # ② 같은 술어로 짝의 «행 인덱스»를 얻는다 (1033 scout 와 글자 그대로 같은 술어)
    pairs = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            if a["key"] == b["key"]:
                continue
            if a["venue_type"] is None or b["venue_type"] is None or a["venue_type"] != b["venue_type"]:
                continue
            if a["is_free_entry"] is None or b["is_free_entry"] is None or a["is_free_entry"] != b["is_free_entry"]:
                continue
            if not a["dur"] or not b["dur"]:
                continue
            if max(a["dur"], b["dur"]) / min(a["dur"], b["dur"]) > 1.5:
                continue
            if abs(a["year"] - b["year"]) > 1:
                continue
            lo, hi = (a, b) if a["f"] <= b["f"] else (b, a)
            pairs.append((lo, hi, hi["y"] - lo["y"]))
    if len(pairs) != X_PAIRS:
        raise SystemExit("🔴 짝 재구성이 동결 함수와 항등이 아니다: %d ≠ %d" % (len(pairs), X_PAIRS))

    # ③ record 별 「t0 이전 담론 수」 — 1033 scout 의 «같은 식»(중복 제거 없음)
    idx = json.load(open(os.path.join(O33, "docidx1033.json")))
    open_of = {}
    for l in open(LEDGER):
        r = json.loads(l)
        open_of[r["record_id"]] = r["A"]["when"]["opened_at"]
    npre = {}
    for r in rows:
        rid = r["record_id"]
        npre[rid] = len([x for x in idx.get(rid, []) if x[0] < open_of[rid]])
    y_of = {r["record_id"]: r["y"] for r in rows}

    # ④ 대조군 — 「그 선행(t0 이전 담론)이 «없던» 유사 개체」
    ctrl = {}
    for lo, hi, d in pairs:
        if d == 0.0:
            continue
        for me, ot in ((lo, hi), (hi, lo)):
            if npre[me["record_id"]] >= 1 and npre[ot["record_id"]] == 0:
                ctrl.setdefault(me["record_id"], []).append(
                    dict(상대=ot["record_id"],
                         무담론쪽이_이김=bool(y_of[ot["record_id"]] > y_of[me["record_id"]])))

    # ⑤ 링크별 대조 검사
    chain33 = json.load(open(os.path.join(REPO, "runners/out1033_chain.json")))
    items33 = {it["iid"]: it for it in json.load(open(os.path.join(O33, "items.json")))}
    truth = json.load(open(os.path.join(O33, "truth.json")))

    links, cnt = [], dict(확증=0, 반증=0, 역방향반증=0, 미검_검정력0=0, 형식미달_분모0=0)
    pooled = []
    for lk in chain33["링크"]:
        iid = lk["항목"]
        m = items33[iid]["meta"]
        rid_win = m["rid_L"] if truth[iid] == "L" else m["rid_R"]
        cs = ctrl.get(rid_win, [])
        kp = len(cs)
        k0 = sum(1 for c in cs if c["무담론쪽이_이김"])
        pooled += [c["무담론쪽이_이김"] for c in cs]
        p = binom_p(k0, kp) if kp else None
        ratio = (round(k0 / float(kp), 4) if kp else None)
        if kp == 0:
            v, why = "형식미달_분모0", "대조군 0 — 이 링크의 반증 조건은 실측 «불가능»하다(조항 59)"
            cnt["형식미달_분모0"] += 1
        elif kp < KPRIME_MIN:
            v, why = ("미검_검정력0",
                      "K′=%d < %d — 이항 양측 α=0.05 가 «원리상» 유의를 못 낸다(조항 78)" % (kp, KPRIME_MIN))
            cnt["미검_검정력0"] += 1
        elif p < 0.05 and ratio < 0.5:
            v, why = "확증", "무담론 쪽이 이긴 비율 %.4f 가 0.5 와 유의하게 다르고 «작다» (p=%s)" % (ratio, p)
            cnt["확증"] += 1
        elif p < 0.05 and ratio > 0.5:
            v, why = ("역방향반증",
                      "무담론 쪽이 «더» 이겼다(비율 %.4f · p=%s) — 링크 방향과 반대" % (ratio, p))
            cnt["역방향반증"] += 1
        else:
            v, why = "반증", "무담론 쪽이 이긴 비율 %s 가 0.5 와 «다르지 않다» (p=%s) — 등록 문언대로 반증" % (ratio, p)
            cnt["반증"] += 1
        links.append(dict(링크id=lk["링크id"], 항목=iid,
                          기제유형=lk["기제유형"], 기제문장sha16=lk["기제문장sha16"],
                          근거문서sha_수=len(lk["근거문서sha"]),
                          시간순서검사="통과(1033 8-가 t0이후 0 인용)",
                          반증조건=lk["반증조건"],
                          대조군_K프라임=kp, 무담론쪽이_이긴_수=k0, 비율=ratio, 이항p=p,
                          검정력_충분=(kp >= KPRIME_POW), 판정=v, 사유=why))

    pk, pn = sum(1 for x in pooled if x), len(pooled)
    # [관찰] 모집단 판 — 727 유효 짝 중 «정확히 한쪽만» 담론이 있는 비대칭 짝 전량
    asym = []
    for lo, hi, d in pairs:
        if d == 0.0:
            continue
        a0, b0 = npre[lo["record_id"]], npre[hi["record_id"]]
        if (a0 == 0) != (b0 == 0):
            zero, one = (lo, hi) if a0 == 0 else (hi, lo)
            asym.append(bool(y_of[zero["record_id"]] > y_of[one["record_id"]]))
    ak, an = sum(1 for x in asym if x), len(asym)

    conf = cnt["확증"]
    out = {"시각": t0, "끝": now(), "규격": "docs/루프.md 7-다 chain v0 — 대조 검사 «첫 집행»",
           "러너sha256": sha256_file(os.path.abspath(__file__)), "인용소스sha16": srcs,
           "인용": {"링크 출처": "runners/out1033_chain.json sha256 %s"
                              % SHA["runners/out1033_chain.json"],
                   "대조군 틀": "1030 §10-3 동결 함수 variance1030c.matched_cross_ip (조항 67)",
                   "항등검사": {"n_쌍": len(pairs), "등록": X_PAIRS,
                              "관여 IP그룹": frozen["관여 IP그룹"], "판정": "일치"}},
           "대조 검사 규격(사전 고정)": {
               "대조군": "링크의 «이긴 쪽» 개체와 정합(같은 장소유형·같은 무료입장·기간비≤1.5·"
                       "연도차≤1 · 다른 IP)하면서 t0 이전 담론이 «0건»인 상대 전부",
               "통계": "무담론 쪽이 이긴 비율 대 0.5 · 이항 정확검정 양측 α=0.05",
               "판정": {"확증": "K′≥%d ∧ p<0.05 ∧ 비율<0.5" % KPRIME_MIN,
                       "반증": "K′≥%d ∧ p≥0.05 (등록 문언 그대로)" % KPRIME_MIN,
                       "역방향반증": "K′≥%d ∧ p<0.05 ∧ 비율>0.5" % KPRIME_MIN,
                       "미검_검정력0": "0<K′<%d — 원리상 유의 불가(조항 78)" % KPRIME_MIN,
                       "형식미달_분모0": "K′=0 — 실측 불가"},
               "검정력": "|p−0.5|=0.25 를 검정력 0.80 으로 잡으려면 K′≈%d 이 필요하다" % KPRIME_POW},
           "링크 수": len(links), "계수": cnt,
           "🔴 확증 링크 비율": "%d / %d" % (conf, len(links)),
           "미검(별도 계수)": cnt["미검_검정력0"] + cnt["형식미달_분모0"],
           "형식 미달": cnt["형식미달_분모0"],
           "[관찰] 링크 합산": dict(대조쌍=pn, 무담론쪽이_이김=pk,
                                  비율=(round(pk / float(pn), 4) if pn else None),
                                  이항p=(binom_p(pk, pn) if pn else None),
                                  검정력_충분=(pn >= KPRIME_POW),
                                  낙인="링크끼리 개체를 공유할 수 있어 독립이 아니다 — [관찰]"),
           "[관찰] 모집단 비대칭 짝 전량": dict(
               짝=an, 무담론쪽이_이김=ak, 비율=(round(ak / float(an), 4) if an else None),
               이항p=(binom_p(ak, an) if an else None), 검정력_충분=(an >= KPRIME_POW),
               낙인="727 유효 짝 중 «정확히 한쪽만» t0 이전 담론이 있는 짝 전량. "
                    "반증 조건의 «모집단 판»이다 — 링크별 K′ 가 작은 것을 보완한다. [관찰]"),
           "낙인": [STAMP_CAUSAL, STAMP_GRADE,
                   "🔴 확증 링크만 「인과 후보」다. 나머지는 «서사»로 적는다(7-나 5).",
                   "🔴 이 산출은 [관찰] 등급이다 — K=10 소표본. 「판정」 승격 금지(사전 명기)."],
           "링크": links}
    json.dump(out, open(os.path.join(OUT, "chain1034.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(out, open(os.path.join(REPO, "runners/out1034_chain.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "링크"}, ensure_ascii=False, indent=1))
    for l in links:
        print("  %s %s K′=%d k0=%d 비율=%s p=%s → %s"
              % (l["링크id"], l["항목"], l["대조군_K프라임"], l["무담론쪽이_이긴_수"],
                 l["비율"], l["이항p"], l["판정"]))


# ══ hygiene — 커밋되는 산출물의 실명·record_id 전수 검사 ═════════════════════
def cmd_hygiene(args):
    names = set()
    rids = set()
    for l in open(LEDGER):
        r = json.loads(l)
        rids.add(r["record_id"])
        wt = (r.get("A") or {}).get("what") or {}
        for v in (wt.get("ip_name"), wt.get("brand")):
            if v and len(str(v)) >= 2:
                names.add(str(v))
    targets = [p for p in ("runners/out1034_prereg.json", "runners/out1034_readings.json",
                           "runners/out1034_scored.json", "runners/out1034_chain.json",
                           "docs/탐색/1034.md")
               if os.path.exists(os.path.join(REPO, p))]
    res = {}
    for t in targets:
        txt = open(os.path.join(REPO, t)).read()
        hit_r = sorted({x for x in rids if x in txt})
        hit_n = sorted({x for x in names if x in txt})
        res[t] = dict(record_id_히트=len(hit_r), 실명_히트=len(hit_n),
                      record_id_예=hit_r[:5], 실명_예=hit_n[:5],
                      sha256=sha256_file(os.path.join(REPO, t))[:16])
    out = dict(시각=now(), 원장_record=len(rids), 원장_실명=len(names), 대상=len(targets), 결과=res,
               판정=("통과 — 히트 0" if all(v["record_id_히트"] == 0 and v["실명_히트"] == 0
                                          for v in res.values()) else "🔴 위반"))
    json.dump(out, open(os.path.join(OUT, "hygiene.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cite", "build", "probe", "read", "tri",
                                    "export", "score", "chain", "hygiene"])
    a = ap.parse_args()
    {"cite": cmd_cite, "build": cmd_build, "probe": cmd_probe, "read": cmd_read,
     "tri": cmd_tri, "export": cmd_export, "score": cmd_score, "chain": cmd_chain,
     "hygiene": cmd_hygiene}[a.cmd](a)
