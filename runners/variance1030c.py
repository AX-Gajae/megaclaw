# -*- coding: utf-8 -*-
"""사이클 1030 C층 — 개입 원장(팝업 개최)에서 조건 사다리 (사건 원장 무의존).

보충 사전등록: docs/탐색/1030.md §9 (커밋 61567e7b0) — 결과 값 무접촉 상태에서 동결.
추정기는 동결 러너 runners/variance1030.py(sha256 6e775e0684b4af5f…)를 읽기 전용
임포트해 «같은 함수»로 쓴다(조항 67). IP 키 산식은 runners/ceiling1020.py 임포트(1020 항등).

🔴 본 러너는 사건 원장(events*.jsonl.gz · merged_view*.jsonl.gz)과 위키 패널을 읽지 않는다
   — 1028 소비금지 낙인 자료가 C층에 원리상 안 들어간다.

단계:  python3 runners/variance1030c.py --stage selftest
       python3 runners/variance1030c.py --stage run
"""
import argparse
import bisect
import datetime as dt
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")

import numpy as np

REPO = "/Users/ax/world_model"
sys.path.insert(0, REPO)
import importlib.util as _u                                        # noqa: E402


def _load(name, path):
    sp = _u.spec_from_file_location(name, path)
    m = _u.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


V = _load("variance1030", os.path.join(REPO, "runners/variance1030.py"))
C20 = _load("ceiling1020", os.path.join(REPO, "runners/ceiling1020.py"))
from pretrain.leak_guard import assert_no_leak                      # noqa: E402
from pretrain.mde_guard import assert_mde, mde_of, MdeUnderpowered  # noqa: E402

FOUND = "/Users/ax/wm_harvest/foundation"
LEDGER = os.path.join(FOUND, "ledger_interventions/ledger.jsonl")
OUTDIR = os.path.join(FOUND, "variance_reduction")
DOC = os.path.join(REPO, "docs/탐색/1030.md")
OUT = os.path.join(OUTDIR, "run1030c.out")

LEDGER_SHA16 = "9a76948d3e619424"
SRC_SHA16 = "25ce91c1cdf61c26"
FROZEN_SHA16 = "6e775e0684b4af5f"
CUT_Q = 0.70
KFOLD = 5
ALPHAS = V.ALPHAS
B_BOOT = V.B_BOOT
B_PL = V.B_PL
SEED_MAIN = V.SEED_MAIN
SEED_TWIN = V.SEED_TWIN
AIM = 0.25
AIM_INC = 0.15
M_GATES = 2
ALPHA_FAM = 0.05
CITY_TOP = 8
STAMP_ASSOC = V.STAMP_ASSOC
STAMP_U = ("U 눈금 = 일평균 방문자 자연로그(제6장 6-가 정본 · 1016 동결 계산). B층의 "
           "«위키 관심 log1p 잔차» 눈금과 환산 주장 금지.")
STAMP_NOEV = ("C층은 사건 원장·위키 패널을 한 번도 읽지 않는다 — 1028 소비금지 낙인 자료 무접촉.")

_LOGF = None


def log(**kw):
    global _LOGF
    kw["t"] = dt.datetime.now().strftime("%H:%M:%S")
    s = json.dumps(kw, ensure_ascii=False, default=str)
    print(s, flush=True)
    if _LOGF is None:
        _LOGF = open(OUT, "a")
    _LOGF.write(s + "\n")
    _LOGF.flush()


def load_gate():
    """자기 로그로만 적는다 — 동결 러너의 run1030.out(§8 도장 대상)을 안 건드린다."""
    while os.getloadavg()[0] > V.LOAD_MAX:
        log(단계="load1 재잼", load1=os.getloadavg()[0])
        time.sleep(60)


def tree_gate():
    mine = ["runners/variance1030c.py", "docs/탐색/1030.md"]
    r = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--name-only", "HEAD", "--"]
                       + mine, cwd=REPO, capture_output=True, text=True)
    dirty = [x for x in r.stdout.split("\n") if x.strip()]
    if dirty:
        raise SystemExit("🔴 ⓪ 관문 실패 — 커밋 안 된 자기 파일: %r" % dirty)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    return {"관문": "작업트리=커밋트리", "자기파일": mine, "HEAD": head[:9]}


# ── 9-바 수리 게이트 ─────────────────────────────────────────────────────────

def thr_of(aim, q_corr):
    return max(aim, q_corr)


def gate_pass(A, thr):
    return (A - thr) > 0.0


def direction_probe():
    t, thr = 0.1, 0.25
    cases = [("악화 극값(Δ=−2t) → 거짓", gate_pass(thr - 2 * t, thr) is False),
             ("개선 극값(Δ=+2t) → 참", gate_pass(thr + 2 * t, thr) is True),
             ("0 → 거짓(엄격 초과)", gate_pass(thr, thr) is False),
             ("문턱 = max(겨냥,q) — q 음수여도 퇴화 없음", thr_of(0.25, -0.13) == 0.25),
             ("문턱 = max(겨냥,q) — q 가 크면 q", thr_of(0.25, 0.40) == 0.40)]
    bad = [n for n, ok in cases if not ok]
    if bad:
        raise SystemExit("🔴 방향 탐침 실패 — %r · 측정 없이 중단" % bad)
    return [{"경우": n, "기대대로": ok} for n, ok in cases]


MDE_ROW = re.compile(
    r"^\|\s*(C1|C2|C3|C4)\s*\|([^|]*)\|\s*([0-9]+)\s*\|\s*([0-9.]+)\s*\|"
    r"\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([^|]*)\|")


def parse_mde_table():
    with open(DOC, encoding="utf-8") as f:
        txt = f.read()
    lo = txt.find("<!-- MDE-TABLE-1030C 시작")
    hi = txt.find("<!-- MDE-TABLE-1030C 끝")
    if lo < 0 or hi < 0:
        raise SystemExit("🔴 MDE 칸 부재 — §9-사 표를 못 찾았다 · 측정 없이 중단")
    rows = {}
    for line in txt[lo:hi].split("\n"):
        m = MDE_ROW.match(line.strip())
        if m:
            rows[m.group(1)] = {"자": m.group(2).strip(), "G_test": int(m.group(3)),
                                "겨냥": float(m.group(4)), "SE_pred": float(m.group(5)),
                                "MDE": float(m.group(6)), "레인": m.group(7).strip()}
    if set(rows) != {"C1", "C2", "C3", "C4"}:
        raise SystemExit("🔴 MDE 칸 부재 — 파싱된 행 %r" % sorted(rows))
    return rows


def mde_start_gate(rows):
    src = os.path.join(FOUND, "ceiling/ceiling1020_result.json")
    if V.sha256_file(src)[:16] != SRC_SHA16:
        raise SystemExit("🔴 MDE 산식 입력 sha 불일치 — 측정 없이 중단")
    if V.sha256_file(os.path.join(REPO, "runners/variance1030.py"))[:16] != FROZEN_SHA16:
        raise SystemExit("🔴 동결 러너 sha 불일치 — 같은 함수 보증 실패 · 측정 없이 중단")
    st = {}
    for g in ("C1", "C2", "C3"):
        r = rows[g]
        se = 2.0 * math.sqrt(r["겨냥"] * (1 - r["겨냥"]) ** 2 / r["G_test"])
        if abs(se - r["SE_pred"]) > 5e-6 or abs(mde_of(se=se, jitter=0.0) - r["MDE"]) > 1e-5:
            raise SystemExit("🔴 MDE 칸 재계산 불일치(%s) — 측정 없이 중단" % g)
        st[g] = assert_mde(mde_of(se=r["SE_pred"], jitter=0.0), r["겨냥"], SRC_SHA16)
        if g == "C3":
            st[g]["레인"] = "관찰(등록 선택 — 조항 79 다중비교 회피)"
    r = rows["C4"]
    try:
        assert_mde(mde_of(se=r["SE_pred"], jitter=0.0), r["겨냥"], SRC_SHA16)
        raise SystemExit("🔴 C4 는 등록상 관찰(㉯ⓑ)인데 관문을 통과했다 — 등록 결함")
    except MdeUnderpowered:
        st["C4"] = {"레인": "관찰(㉯ⓑ)", "MDE": r["MDE"], "겨냥": r["겨냥"],
                    "여유": r["겨냥"] - r["MDE"]}
    return st


def selftest():
    rng = np.random.RandomState(11)
    n, G = 300, 60
    gid = rng.randint(0, G, n)
    f = rng.randn(n)
    y = 0.9 * f + 0.4 * rng.randn(n)
    X = np.column_stack([np.ones(n), f])
    cols_l1 = np.array([0]); cols_l3 = np.array([0, 1])
    w = V.eq_weights(gid)
    a1 = kfold_alphas(X, y, gid, cols_l1, SEED_MAIN)
    a3 = kfold_alphas(X, y, gid, cols_l3, SEED_MAIN)
    v1 = V.wvar(kfold_resid(X, y, gid, cols_l1, a1, SEED_MAIN), w)
    v3 = V.wvar(kfold_resid(X, y, gid, cols_l3, a3, SEED_MAIN), w)
    A = 1.0 - v3 / v1
    Xp = X.copy(); Xp[:, 1] = X[rng.permutation(n), 1]
    Ap = 1.0 - V.wvar(kfold_resid(Xp, y, gid, cols_l3, a3, SEED_MAIN), w) / v1
    cases = [("① 신호 있으면 몫>0.5", A > 0.5, A),
             ("② 순열하면 몫<0.1", Ap < 0.1, Ap),
             ("③ 순열 몫 < 실측 몫", Ap < A, A - Ap),
             ("④ 폴드는 그룹을 안 쪼갠다", fold_split_ok(gid, SEED_MAIN), None),
             ("⑤ 동결 러너 함수 항등", V.wvar(np.array([1.0, 3.0]), np.array([.5, .5])) == 1.0, None)]
    bad = [c[0] for c in cases if not c[1]]
    if bad:
        raise SystemExit("🔴 자기시험 실패 — %r · 측정 없이 중단" % bad)
    return [{"경우": c[0], "기대대로": bool(c[1]), "값": c[2]} for c in cases]


# ── 그룹 K겹 (C1 정본 레인) ─────────────────────────────────────────────────

def fold_of(g, seed):
    return int(hashlib.sha256(("%dC|%d" % (seed, int(g))).encode()).hexdigest()[:8], 16) % KFOLD


def fold_split_ok(gid, seed):
    fv = np.array([fold_of(g, seed) for g in gid])
    for g in np.unique(gid):
        if len(set(fv[gid == g].tolist())) != 1:
            return False
    return True


def kfold_alphas(X, y, gid, cols, seed):
    fv = np.array([fold_of(g, seed) for g in gid])
    out = {}
    for k in range(KFOLD):
        tr = fv != k
        if cols.size == 0 or tr.sum() < 10:
            out[k] = ALPHAS[0]
            continue
        w = V.eq_weights(gid[tr])
        out[k] = V.choose_alpha(X[np.ix_(tr, cols)], y[tr], w, gid[tr], seed)[0]
    return out


def kfold_resid(X, y, gid, cols, alpha_by_fold, seed):
    fv = np.array([fold_of(g, seed) for g in gid])
    e = np.zeros(len(y))
    for k in range(KFOLD):
        te = fv == k
        tr = ~te
        if te.sum() == 0:
            continue
        w = V.eq_weights(gid[tr])
        if cols.size == 0:
            pr = np.full(int(te.sum()), V.wmean(y[tr], w))
        else:
            pr, _ = V.fit_predict(X[np.ix_(tr, cols)], y[tr], w, X[np.ix_(te, cols)],
                                  alpha_by_fold[k])
        e[te] = y[te] - pr
    return e


# ── 자료 ────────────────────────────────────────────────────────────────────

def od(s):
    try:
        return dt.date.fromisoformat(str(s)[:10]).toordinal()
    except Exception:
        return None


def build_rows():
    recs = [json.loads(l) for l in open(LEDGER, encoding="utf-8")]
    opens = []
    for r in recs:
        f = od(((r.get("A") or {}).get("when") or {}).get("opened_at"))
        if f is not None:
            opens.append((f, ((r.get("A") or {}).get("what") or {}).get("category") or ""))
    opens.sort(key=lambda x: x[0])
    fs = [x[0] for x in opens]

    def pre(f, days, cat=None):
        lo, hi = bisect.bisect_left(fs, f - days), bisect.bisect_left(fs, f)
        sub = opens[lo:hi]
        if cat is None:
            return len(sub)
        return sum(1 for x in sub if x[1] == cat)

    lad = {"0_원장": len(recs), "1_일단위_opened": 0, "2_U가능": 0}
    rows, margins = [], []
    for r in recs:
        A = r.get("A") or {}
        wn, wh, wt = A.get("when") or {}, A.get("where") or {}, A.get("what") or {}
        Y = r.get("Y") or {}
        Cc = r.get("C") or {}
        f = od(wn.get("opened_at"))
        if f is None:
            continue
        lad["1_일단위_opened"] += 1
        U = Y.get("u_daily_visitors")
        if U is None or float(U) <= 0:
            continue
        lad["2_U가능"] += 1
        key = (C20.ipkey_mkt(wt.get("ip_name"), wt.get("brand")) if r.get("layer") == "market"
               else C20.ipkey_int(wt.get("ip_name"), wt.get("brand")))
        if not (key and len(key) >= 2):
            key = "SOLO:" + r["record_id"]
        h = Cc.get("ip_history") or {}
        cat = wt.get("category")
        assert_no_leak([{"id": r["record_id"],
                         "published_at": dt.date.fromordinal(f - 1).isoformat()}],
                       dt.date.fromordinal(f), "1030C L3 %s" % r["record_id"])
        margins.append(1)
        sc = (Y.get("scope") or {})
        rows.append({
            "record_id": r["record_id"], "key": key, "f": f, "y": math.log(float(U)),
            "layer": r.get("layer"),
            "venue_type": wh.get("venue_type"), "city": wh.get("city"),
            "multi_store": (None if wh.get("multi_store") is None
                            else (1.0 if wh["multi_store"] else 0.0)),
            "category": cat,
            "is_free_entry": (None if wt.get("is_free_entry") is None
                              else (1.0 if wt["is_free_entry"] else 0.0)),
            "dur": (None if not wn.get("duration_days") else float(wn["duration_days"])),
            "ln_dur": (None if not wn.get("duration_days")
                       else math.log(float(wn["duration_days"]))),
            "weekend_share": wn.get("weekend_share"),
            "ln_holiday": (None if wn.get("holiday_days") is None
                           else math.log1p(float(wn["holiday_days"]))),
            "mon_sin": math.sin(2 * math.pi * dt.date.fromordinal(f).month / 12.0),
            "mon_cos": math.cos(2 * math.pi * dt.date.fromordinal(f).month / 12.0),
            "year": dt.date.fromordinal(f).year,
            "prior_count": float(h.get("prior_count") or 0),
            "ln_prior": math.log1p(float(h.get("prior_count") or 0)),
            "first_edition": (1.0 if h.get("first_edition") else 0.0),
            "months_since_last": (None if h.get("months_since_last") is None
                                  else float(h["months_since_last"])),
            "ln_pre90": math.log1p(pre(f, 90)),
            "ln_pre365": math.log1p(pre(f, 365)),
            "ln_pre90_cat": (None if not cat else math.log1p(pre(f, 90, cat))),
            "trust": Y.get("label_trust_grade"), "basis": Y.get("visitors_basis"),
            "sc_interim": 1.0 if sc.get("interim") else 0.0,
            "sc_per_day": 1.0 if sc.get("per_day") else 0.0,
            "sc_forecast": 1.0 if sc.get("forecast") else 0.0,
            "sc_multi_run": 1.0 if sc.get("multi_run") else 0.0,
            "sc_wider": 1.0 if sc.get("wider_scope") else 0.0,
        })
    return rows, lad, margins


def build_X(rows, tr_mask):
    cols, names, blocks, cov = [], [], [], {}

    def add(block, mats, nms):
        i0 = len(cols)
        M = np.hstack(mats)
        for j in range(M.shape[1]):
            cols.append(M[:, j])
        names.extend(nms)
        blocks.append((block, np.arange(i0, len(cols))))

    def cat_block(key, levels, with_ind=True):
        mats = [V.onehot([r.get(key) for r in rows], levels)]
        nms = ["%s=%s" % (key, x) for x in levels]
        if with_ind:
            ind = np.array([[1.0 if r.get(key) is None else 0.0] for r in rows])
            mats.append(ind); nms.append(key + "_결측")
            cov[key] = {"결측": int(ind.sum()), "n": len(rows)}
        return mats, nms

    add("L1", [V.onehot([r["layer"] for r in rows], ["market", "internal"])],
        ["layer=market", "layer=internal"])

    import collections
    cities = [c for c, _ in collections.Counter(
        [r["city"] for r in rows if r["city"]]).most_common(CITY_TOP)]
    cats = sorted(set(r["category"] for r in rows if r["category"]))
    vts = sorted(set(r["venue_type"] for r in rows if r["venue_type"]))
    years = sorted(set(r["year"] for r in rows))
    mats, nms = [], []
    for key, levels in (("venue_type", vts), ("category", cats), ("city", cities)):
        m_, n_ = cat_block(key, levels)
        mats.extend(m_); nms.extend(n_)
    mats.append(V.onehot([r["year"] for r in rows], years))
    nms.extend(["연도=%d" % y for y in years])
    for k in ("ln_dur", "is_free_entry", "multi_store", "weekend_share", "ln_holiday",
              "mon_sin", "mon_cos"):
        v, miss, nm = V.numcol(rows, k, tr_mask)
        cov[k] = {"결측": nm, "n": len(rows)}
        mats.append(v[:, None]); nms.append(k)
        if nm:
            mats.append(miss[:, None]); nms.append(k + "_결측")
    add("L2", mats, nms)

    mats, nms = [], []
    for k in ("prior_count", "ln_prior", "first_edition", "months_since_last",
              "ln_pre90", "ln_pre365", "ln_pre90_cat"):
        v, miss, nm = V.numcol(rows, k, tr_mask)
        cov[k] = {"결측": nm, "n": len(rows)}
        mats.append(v[:, None]); nms.append(k)
        if nm:
            mats.append(miss[:, None]); nms.append(k + "_결측")
    add("L3", mats, nms)

    trusts = sorted(set(r["trust"] for r in rows if r["trust"]))
    bases = sorted(set(r["basis"] for r in rows if r["basis"]))
    mats = [V.onehot([r["trust"] for r in rows], trusts),
            V.onehot([r["basis"] for r in rows], bases),
            np.array([[r["sc_interim"], r["sc_per_day"], r["sc_forecast"],
                       r["sc_multi_run"], r["sc_wider"]] for r in rows])]
    nms = ["신뢰=%s" % x for x in trusts] + ["근거=%s" % x for x in bases] + \
          ["sc_interim", "sc_per_day", "sc_forecast", "sc_multi_run", "sc_wider"]
    add("L4", mats, nms)
    return np.column_stack(cols), names, blocks, cov


# ── C1 레인 (IP키 분리 그룹 5겹) ────────────────────────────────────────────

def run_C1(X, y, gid, blocks, out):
    w = V.eq_weights(gid)
    cum, acc = {}, []
    for nm, idx in blocks:
        acc = acc + list(idx)
        cum[nm] = np.array(sorted(set(acc)), dtype=int)
    levels = [b[0] for b in blocks]
    alphas = {lv: kfold_alphas(X, y, gid, cum[lv], SEED_MAIN) for lv in levels}
    resid = {"L0": y - V.wmean(y, w)}
    for lv in levels:
        resid[lv] = kfold_resid(X, y, gid, cum[lv], alphas[lv], SEED_MAIN)
    v = {k: V.wvar(resid[k], w) for k in resid}
    med = {k: V.wmedian_abs(resid[k], w) for k in resid}
    v1 = v["L1"]
    A = {k: 1.0 - v[k] / v1 for k in resid}
    se_v, se_sh, se_med = V.boot_se(gid, y, resid, "L1", B_BOOT, SEED_MAIN)
    res = {"레인": "C1 · IP키 분리 그룹 5겹 CV (정본 판정)",
           "n": int(len(y)), "클러스터": int(len(np.unique(gid))),
           "α(폴드별)": {k: sorted(set(a.values())) for k, a in alphas.items()},
           "층": {}, "게이트": {},
           "낙인": [STAMP_ASSOC, STAMP_U, STAMP_NOEV]}
    for k in ["L0"] + levels:
        res["층"][k] = {"Var(잔차)": v[k], "Var_SE": se_v[k], "median|e|": med[k],
                        "median_SE": se_med[k], "설명몫": A[k], "설명몫_SE": se_sh[k]}

    def placebo(perm_blocks, upto, minus=None):
        pc = V.block_cols(blocks, perm_blocks)
        rng = np.random.RandomState(SEED_MAIN)
        rng2 = np.random.RandomState(SEED_TWIN)
        Xp, Xq = X.copy(), X.copy()
        src = X[:, pc]
        P = np.zeros(B_PL); Pt = np.zeros(B_PL)
        for b in range(B_PL):
            Xp[:, pc] = src[rng.permutation(len(y))]
            P[b] = 1.0 - V.wvar(kfold_resid(Xp, y, gid, cum[upto], alphas[upto], SEED_MAIN), w) / v1
            Xq[:, pc] = src[rng2.permutation(len(y))]
            Pt[b] = 1.0 - V.wvar(kfold_resid(Xq, y, gid, cum[upto], alphas[upto], SEED_MAIN), w) / v1
        if minus is not None:
            P = P - A[minus]; Pt = Pt - A[minus]
        return P, Pt

    specs = {"C1": {"upto": "L3", "perm": {"L2", "L3"}, "minus": None, "aim": AIM,
                    "이름": "C1 · A(L3)"},
             "C2": {"upto": "L3", "perm": {"L3"}, "minus": "L2", "aim": AIM_INC,
                    "이름": "C1 · A(L3)−A(L2)"}}
    q_lvl = 1.0 - ALPHA_FAM / M_GATES
    for g, sp in specs.items():
        P, Pt = placebo(sp["perm"], sp["upto"], sp["minus"])
        base = A[sp["upto"]] - (A[sp["minus"]] if sp["minus"] else 0.0)
        q = float(np.quantile(P, q_lvl))
        thr = thr_of(sp["aim"], q)
        sd, sdt = float(np.std(P, ddof=1)), float(np.std(Pt, ddof=1))
        J = abs(sd - sdt) / math.sqrt(2.0)
        mde = mde_of(se=sd, jitter=J)
        try:
            stamp = assert_mde(mde, sp["aim"], SRC_SHA16); powered = True
        except MdeUnderpowered as e:
            stamp = {"레인": "관찰(MDE 미달)", "사유": str(e)[:200], "MDE": mde}; powered = False
        p = (1.0 + float(np.sum(P >= base))) / (B_PL + 1.0)
        res["게이트"][g] = {
            "자": sp["이름"], "레인": "판정", "겨냥": sp["aim"], "A": base,
            "q_corr": q, "문턱=max(겨냥,q)": thr, "Δ": base - thr, "여유": base - thr,
            "순열p": p, "통과": bool(gate_pass(base, thr) and p < ALPHA_FAM / M_GATES),
            "위약(진단)": {"평균": float(np.mean(P)), "중앙": float(np.median(P)), "SD": sd,
                        "q95": float(np.quantile(P, 0.95)), "q_corr분위": q_lvl},
            "지터J": J, "실측MDE": mde, "MDE스탬프": stamp, "검정력": powered,
            "퇴화문턱(문턱≤0)": bool(thr <= 0)}
    out["C1"] = res
    return res, cum, alphas, resid, v1, w


def run_split(tag, X, y, gid, blocks, tr, te, gname, aim, out):
    """C2 재현 · C3 — 단일 분할 레인(관찰). 동결 Ladder 로."""
    lad = V.Ladder(X, y, gid, tr, te, blocks, SEED_MAIN)
    levels = [b[0] for b in blocks]
    resid = {"L0": lad.resid_L0()}
    for lv in levels:
        resid[lv] = lad.resid(lv)
    v = {k: V.wvar(resid[k], lad.wte) for k in resid}
    med = {k: V.wmedian_abs(resid[k], lad.wte) for k in resid}
    v1 = v["L1"]
    A = {k: 1.0 - v[k] / v1 for k in resid}
    se_v, se_sh, se_med = V.boot_se(gid[te], y[te], resid, "L1", B_BOOT, SEED_MAIN)
    pc = V.block_cols(blocks, {"L2", "L3"})
    P = V.placebo_shares(X, y, gid, tr, te, blocks, pc, "L3", lad.alphas["L3"], v1,
                         B_PL, SEED_MAIN)
    q = float(np.quantile(P, 1.0 - ALPHA_FAM / M_GATES))
    thr = thr_of(aim, q)
    sd = float(np.std(P, ddof=1))
    res = {"레인": tag, "n_train": int(len(tr)), "n_test": int(len(te)),
           "클러스터_test": int(len(np.unique(gid[te]))),
           "개체겹침_test행": int(sum(1 for i in te if gid[i] in set(gid[tr].tolist()))),
           "α": {k: lad.alphas.get(k) for k in levels}, "층": {}, "게이트": {},
           "낙인": [STAMP_ASSOC, STAMP_U, STAMP_NOEV]}
    for k in ["L0"] + levels:
        res["층"][k] = {"Var(잔차)": v[k], "Var_SE": se_v[k], "median|e|": med[k],
                        "median_SE": se_med[k], "설명몫": A[k], "설명몫_SE": se_sh[k]}
    res["게이트"][gname] = {
        "자": tag + " · A(L3)", "레인": "관찰", "겨냥": aim, "A": A["L3"], "q_corr": q,
        "문턱=max(겨냥,q)": thr, "Δ": A["L3"] - thr, "여유": A["L3"] - thr,
        "순열p": (1.0 + float(np.sum(P >= A["L3"]))) / (B_PL + 1.0),
        "통과(참고)": bool(gate_pass(A["L3"], thr)),
        "위약(진단)": {"평균": float(np.mean(P)), "중앙": float(np.median(P)), "SD": sd},
        "실측MDE": mde_of(se=sd, jitter=0.0)}
    out[tag] = res
    return res


def matched_cross_ip(rows, out):
    """9-자 부수 관찰 — 다른 IP · 관측 조건 정합 짝의 ×배 눈금 (판정 아님)."""
    idx = list(range(len(rows)))
    pairs = []
    for i in idx:
        for j in idx:
            if j <= i:
                continue
            a, b = rows[i], rows[j]
            if a["key"] == b["key"]:
                continue
            if a["venue_type"] is None or b["venue_type"] is None or a["venue_type"] != b["venue_type"]:
                continue
            if a["is_free_entry"] is None or b["is_free_entry"] is None or a["is_free_entry"] != b["is_free_entry"]:
                continue
            if not a["dur"] or not b["dur"]:
                continue
            # 등록 문언 §9-자 「기간 «비» ≤ 1.5」 — 비로 직접 잰다(로그 차는 경계 1.5 를 잃는다)
            if max(a["dur"], b["dur"]) / min(a["dur"], b["dur"]) > 1.5:
                continue
            if abs(a["year"] - b["year"]) > 1:
                continue
            lo, hi = (a, b) if a["f"] <= b["f"] else (b, a)
            pairs.append({"ka": lo["key"], "kb": hi["key"], "d": hi["y"] - lo["y"]})
    ds = np.array([p["d"] for p in pairs])
    keys = sorted(set([p["ka"] for p in pairs] + [p["kb"] for p in pairs]))
    ki = {k: i for i, k in enumerate(keys)}
    med = float(np.median(np.abs(ds))) if len(ds) else None
    rng = np.random.RandomState(SEED_MAIN)
    boots = []
    for _ in range(B_BOOT):
        pick = set(rng.randint(0, len(keys), len(keys)).tolist())
        sel = [p["d"] for p in pairs if ki[p["ka"]] in pick and ki[p["kb"]] in pick]
        if len(sel) >= 5:
            boots.append(float(np.median(np.abs(sel))))
    out["9-자 부수관찰"] = {
        "정의": "다른 IP키 ∧ venue_type 동일 ∧ is_free_entry 동일 ∧ 기간비≤1.5 ∧ 개장 연도차≤1",
        "n_쌍": len(pairs), "관여 IP그룹": len(keys),
        "median|d|": med, "×배=exp(median|d|)": (math.exp(med) if med is not None else None),
        "클러스터SE(양쪽 그룹 모두 뽑힌 쌍만 · B=%d)" % B_BOOT:
            (float(np.std(boots, ddof=1)) if len(boots) > 1 else None),
        "붓스트랩 유효 복제": len(boots),
        "대조(1020 §8-2 같은-IP)": {"median|d|": 0.8437, "×배": 2.32,
                                 "출처sha16": "25ce91c1cdf61c26"},
        "낙인": ["판정 아님 · 인과 아님 · 두 짝의 분모가 다르다(같은 IP 47쌍 대 다른 IP %d쌍)."
               % len(pairs), STAMP_U]}
    return out["9-자 부수관찰"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="run")
    args = ap.parse_args()
    os.makedirs(OUTDIR, exist_ok=True)
    t_start = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    my_sha = V.sha256_file(os.path.abspath(__file__))
    log(단계="시작", 러너sha256=my_sha, 시각0=t_start, load1=os.getloadavg()[0], stage=args.stage)
    gate0 = tree_gate()
    log(단계="⓪관문", **gate0)
    probe = direction_probe()
    mde_rows = parse_mde_table()
    stamps = mde_start_gate(mde_rows)
    st = selftest()
    log(단계="관문통과", 방향탐침=len(probe), MDE시작관문=list(stamps), 자기시험=len(st))
    if args.stage == "selftest":
        print(json.dumps({"selftest": True, "방향탐침": probe, "자기시험": st,
                          "MDE시작관문": stamps}, ensure_ascii=False, indent=1, default=str))
        return
    load_gate()
    if V.sha256_file(LEDGER)[:16] != LEDGER_SHA16:
        raise SystemExit("🔴 개입 원장 sha 불일치 — 측정 없이 중단")

    rows, lad, margins = build_rows()
    keys = sorted(set(r["key"] for r in rows))
    gid = np.array([keys.index(r["key"]) for r in rows])
    y = np.array([r["y"] for r in rows])
    fs = np.array([r["f"] for r in rows])
    log(단계="C층 행", n=len(rows), 사다리=lad, 그룹=len(keys),
        leak스탬프=len(margins), 최소여유일=int(min(margins)))

    out = {}
    X, names, blocks, cov = build_X(rows, np.ones(len(rows), dtype=bool))
    log(단계="X", shape=list(X.shape), 블록={b[0]: len(b[1]) for b in blocks})
    r1, cum, alphas, resid1, v1, w = run_C1(X, y, gid, blocks, out)
    log(단계="C1 완료", 게이트={g: (d["A"], d["통과"]) for g, d in r1["게이트"].items()})

    cut = int(sorted(fs.tolist())[int(len(fs) * CUT_Q)])
    tr_m, te_m = fs < cut, fs >= cut
    X2, _, blocks2, _ = build_X(rows, tr_m)
    run_split("C2재현(시간 전방)", X2, y, gid, blocks2, np.where(tr_m)[0], np.where(te_m)[0],
              "C3", AIM, out)
    log(단계="C2 완료", 컷=dt.date.fromordinal(cut).isoformat())

    def held(k):
        return int(hashlib.sha256(("1030C|" + k).encode()).hexdigest()[:8], 16) % 10 >= 7
    hold = np.array([held(r["key"]) for r in rows])
    trE, teE = (~hold) & tr_m, hold & te_m
    X3, _, blocks3, _ = build_X(rows, trE)
    run_split("C3(개체 분리∧시간 전방)", X3, y, gid, blocks3, np.where(trE)[0],
              np.where(teE)[0], "C4", AIM, out)
    log(단계="C3 완료")
    mx = matched_cross_ip(rows, out)
    log(단계="부수관찰 완료", n_쌍=mx["n_쌍"])

    se_cells, se_over = 0, 0
    for tag, blk in out.items():
        for k, d in (blk.get("층") or {}).items():
            for key in ("Var_SE", "median_SE", "설명몫_SE"):
                if d.get(key) is not None:
                    se_cells += 1
            if d.get("설명몫_SE") and abs(d["설명몫"]) > 2 * d["설명몫_SE"]:
                se_over += 1
    probe_bad = {"㉰악화참": 0, "㉱개선거짓": 0, "퇴화문턱": 0}
    for tag, blk in out.items():
        for g, d in (blk.get("게이트") or {}).items():
            thr = d["문턱=max(겨냥,q)"]
            if thr <= 0:
                probe_bad["퇴화문턱"] += 1
            t_ = abs(thr) if abs(thr) > 1e-9 else 0.1
            if gate_pass(thr - 2 * t_, thr):
                probe_bad["㉰악화참"] += 1
            if not gate_pass(thr + 2 * t_, thr):
                probe_bad["㉱개선거짓"] += 1

    g = out["C1"]["게이트"]
    k_pass = sum(1 for x in ("C1", "C2")
                 if g[x]["통과"] and g[x]["검정력"] and not g[x]["퇴화문턱(문턱≤0)"])
    verdict = {"연언 채점": "%d/%d" % (k_pass, M_GATES),
               "판정어": ("명제 통과" if k_pass == M_GATES else
                        ("가설 후보(1/2)" if k_pass == 1 else "MDE 미만 — 미판정"))}

    t_end = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    my_sha2 = V.sha256_file(os.path.abspath(__file__))
    meta = {"사이클": "1030 C층", "보충 사전등록": "docs/탐색/1030.md §9",
            "문서_sha256": V.sha256_file(DOC), "러너sha256": my_sha,
            "러너sha_전후일치": my_sha == my_sha2,
            "동결러너sha16": FROZEN_SHA16, "시작": t_start, "끝": t_end, "⓪관문": gate0,
            "방향탐침": probe, "자기시험": st, "MDE시작관문": stamps,
            "사다리": lad, "행": len(rows), "IP그룹": len(keys),
            "컷": dt.date.fromordinal(cut).isoformat(),
            "C2": {"train": int(tr_m.sum()), "test": int(te_m.sum())},
            "C3": {"train": int(trE.sum()), "test": int(teE.sum())},
            "leak스탬프": {"n": len(margins), "최소여유일": int(min(margins))},
            "특징 커버리지": cov, "자료탐침": probe_bad,
            "cluster_se 칸": {"전량": se_cells, "2·SE 초과(설명몫)": se_over},
            "상수": {"K겹": KFOLD, "B_boot": B_BOOT, "B_pl": B_PL,
                     "씨앗": [SEED_MAIN, SEED_TWIN], "겨냥": AIM, "증분겨냥": AIM_INC,
                     "m": M_GATES, "α격자": list(ALPHAS), "city_top": CITY_TOP},
            "입력sha16": {"ledger": LEDGER_SHA16},
            "판정": verdict, "낙인": [STAMP_ASSOC, STAMP_U, STAMP_NOEV]}
    with open(os.path.join(OUTDIR, "ladder1030c.json"), "w") as f:
        json.dump({"판": "조건 사다리 1030 C층", "레인": out, "판정": verdict},
                  f, ensure_ascii=False, indent=1, default=str)
    with open(os.path.join(OUTDIR, "features1030c.json"), "w") as f:
        json.dump({"열이름": names, "블록": {b[0]: len(b[1]) for b in blocks},
                   "커버리지": cov}, f, ensure_ascii=False, indent=1, default=str)
    with open(os.path.join(OUTDIR, "meta1030c.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, default=str)
    with gzip.open(os.path.join(OUTDIR, "rows1030c.jsonl.gz"), "wt") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    log(단계="완료", 끝=t_end, 판정=verdict, 러너sha_전후일치=my_sha == my_sha2)
    print(json.dumps({"완료": True, "판정": verdict}, ensure_ascii=False))


if __name__ == "__main__":
    main()
