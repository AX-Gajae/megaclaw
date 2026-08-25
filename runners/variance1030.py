# -*- coding: utf-8 -*-
"""사이클 1030 — 내부 상태가 흩어짐을 설명하는가 (조건부 분산 감소).

사전등록: docs/탐색/1030.md (커밋 20bcd6072 · sha256 9b956cc53fd96f17…) — §0~§7 동결.
이 러너는 그 문서의 규칙만 집행한다. 주행 중 소스 수정 금지(조항 66).

단계:  python3 runners/variance1030.py --stage selftest
       python3 runners/variance1030.py --stage run
"""
import argparse
import bisect
import datetime as dt
import glob
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
os.environ.setdefault("NUMEXPR_NUM_THREADS", "4")

import numpy as np

REPO = "/Users/ax/world_model"
sys.path.insert(0, REPO)
from pretrain.leak_guard import assert_no_leak                      # noqa: E402
from pretrain.mde_guard import assert_mde, mde_of, MdeUnderpowered  # noqa: E402

FOUND = "/Users/ax/wm_harvest/foundation"
LEDGER_DIR = os.path.join(FOUND, "event_ledger")
IVT_LEDGER = os.path.join(FOUND, "ledger_interventions/ledger.jsonl")
PAIRS1020 = os.path.join(FOUND, "ceiling/pairs1020.json")
GRID_SOV = os.path.join(FOUND, "l1_discourse/grid_sov.jsonl.gz")
OUTDIR = os.path.join(FOUND, "variance_reduction")
SNAPDIR = os.path.join(OUTDIR, "panel_snapshot")
DOC = os.path.join(REPO, "docs/탐색/1030.md")
OUT = os.path.join(OUTDIR, "run1030.out")

# ── 사전 고정 상수 (등록문 §2~§5 — 여기 바꾸면 등록 위반) ─────────────────────
WIN_LO, WIN_HI = -30, 60             # 반응 창 91칸 (1027 §2 항등)
BASE_LO, BASE_HI = -37, -8           # 기준선 창 30일
BASE_MIN, WIN_MIN = 24, 86           # 창 결측 규칙
RESP_LO, RESP_HI = 0, 14             # 결과 R = 잔차 [0,+14] 창 평균 (§2)
CUT_Q = 0.70                         # 시간 전방 컷 = t0 70분위
HOLD_MOD = 10                        # 개체 분리: hash mod 10 >= 7
HOLD_MIN = 7
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)
CV_K = 5
B_BOOT = 2000                        # 클러스터 붓스트랩
B_PL = 1000                          # 위약 순열
SEED_MAIN = 1030
SEED_TWIN = 2030
AIM = 0.25                           # 겨냥 설명 몫 (§5-가)
AIM_INC = 0.15                       # 증분 겨냥
M_GATES = 2                          # 판정 게이트 수 (조항 79 Bonferroni)
ALPHA_FAM = 0.05
SRC_SHA16 = "25ce91c1cdf61c26"       # 눈금 출처 = ceiling1020_result.json
LOAD_MAX = 10.0

EV_SHA16 = "649a2c88664a5aba"
MV_SHA16 = "d01475447ac24e29"
IVT_SHA16 = "9a76948d3e619424"
PAIRS_SHA16 = "bf4301a67280d16e"
GRID_SHA16 = "e1ff86d4d878cf59"
PANEL_SHA16 = {
    "게임.jsonl.gz": "5f978ed4ce15d777", "도서.jsonl.gz": "524e8869a3ec236b",
    "만화.jsonl.gz": "0739ec78786110f3", "모바일.jsonl.gz": "2950379d80c6c529",
    "세계애니.jsonl.gz": "358a4df8307c89e9", "시장팝업.jsonl.gz": "3465c1183c6f03d5",
    "아이돌.jsonl.gz": "6cebc8bdfc912136", "애니.jsonl.gz": "b9f7aded35c77fe1",
    "웹툰.jsonl.gz": "3c7d2bd823c2704e", "팝업.jsonl.gz": "0ae22ab9f4c95edd",
    "펀딩.jsonl.gz": "182abc337797434f",
}
STAMP_ASSOC = ("조건부 연관 — 인과 아님. 내부 상태는 무작위 배정이 아니고, 같은 개체의 인접 "
               "사건·계절·담론·원장 구성이 혼입될 수 있다. '~가 ~를 줄였다' 화법 금지.")
STAMP_146 = ("사건 원장 v0 — 티처 #146 실측 「날짜-의미 거짓률 ~45%±7%p」 경고 병기"
             "(1028 정제판 v1 은 본 등록 시점 미커밋). 라벨 오염은 결과에 잡음을 더해 "
             "설명 몫을 아래로 민다 — 본 팔의 판정은 보수 쪽이다.")

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


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_gate():
    while os.getloadavg()[0] > LOAD_MAX:
        log(단계="load1 재잼", load1=os.getloadavg()[0])
        time.sleep(60)


def tree_gate():
    """4-나 ⓪ 관문 — 작업 트리 = 커밋된 트리 (자기 파일에 대해)."""
    mine = ["runners/variance1030.py", "docs/탐색/1030.md"]
    r = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--name-only", "HEAD", "--"]
                       + mine, cwd=REPO, capture_output=True, text=True)
    dirty = [x for x in r.stdout.split("\n") if x.strip()]
    if dirty:
        raise SystemExit("🔴 ⓪ 관문 실패 — 커밋 안 된 자기 파일: %r" % dirty)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    return {"관문": "작업트리=커밋트리", "자기파일": mine, "HEAD": head[:9]}


# ── v5.3-2 방향 탐침 (측정 «전» · 자료 없이 · 합성 t>0) ───────────────────────

def gate_pass(A, q_corr):
    """게이트 = 설명 몫 A 가 위약 보정 분위 q_corr 를 넘는가. Δ = A − q_corr."""
    return (A - q_corr) > 0.0


def direction_probe():
    t = 0.1
    cases = [("악화 극값(Δ=−2t) → 거짓", gate_pass(0.5 - 2 * t, 0.5) is False),
             ("개선 극값(Δ=+2t) → 참", gate_pass(0.5 + 2 * t, 0.5) is True),
             ("0 → 거짓(엄격 초과)", gate_pass(0.5, 0.5) is False)]
    bad = [n for n, ok in cases if not ok]
    if bad:
        raise SystemExit("🔴 방향 탐침 실패 — %r · 측정 없이 중단" % bad)
    return [{"경우": n, "기대대로": ok} for n, ok in cases]


# ── 부칙 6 ㉰ 시작 관문 — 등록문 MDE 표 파싱 + 출처 sha 실물 대조 ─────────────

MDE_ROW = re.compile(
    r"^\|\s*(G1|G2|O1|O2|O3|O4)\s*\|([^|]*)\|\s*([0-9]+)\s*\|\s*([0-9.]+)\s*\|"
    r"\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([^|]*)\|")


def parse_mde_table():
    with open(DOC, encoding="utf-8") as f:
        txt = f.read()
    lo = txt.find("<!-- MDE-TABLE-1030 시작")
    hi = txt.find("<!-- MDE-TABLE-1030 끝")
    if lo < 0 or hi < 0:
        raise SystemExit("🔴 MDE 칸 부재 — 등록문에서 표를 못 찾았다 · 측정 없이 중단")
    rows = {}
    for line in txt[lo:hi].split("\n"):
        m = MDE_ROW.match(line.strip())
        if m:
            rows[m.group(1)] = {"자": m.group(2).strip(), "G_test": int(m.group(3)),
                                "겨냥": float(m.group(4)), "SE_pred": float(m.group(5)),
                                "MDE": float(m.group(6)), "레인": m.group(7).strip()}
    if set(rows) != {"G1", "G2", "O1", "O2", "O3", "O4"}:
        raise SystemExit("🔴 MDE 칸 부재 — 파싱된 행 %r" % sorted(rows))
    return rows


def mde_start_gate(rows):
    src = os.path.join(FOUND, "ceiling/ceiling1020_result.json")
    if sha256_file(src)[:16] != SRC_SHA16:
        raise SystemExit("🔴 MDE 산식 입력 sha 불일치 — 측정 없이 중단")
    stamps = {}
    for g in ("G1", "G2"):
        r = rows[g]
        se = 2.0 * math.sqrt(r["겨냥"] * (1 - r["겨냥"]) ** 2 / r["G_test"])
        if abs(se - r["SE_pred"]) > 5e-6 or abs(mde_of(se=se, jitter=0.0) - r["MDE"]) > 1e-5:
            raise SystemExit("🔴 MDE 칸 재계산 불일치(%s) — 측정 없이 중단" % g)
        stamps[g] = assert_mde(mde_of(se=r["SE_pred"], jitter=0.0), r["겨냥"], SRC_SHA16)
    for g in ("O1", "O2", "O3", "O4"):
        r = rows[g]
        try:
            assert_mde(mde_of(se=r["SE_pred"], jitter=0.0), r["겨냥"], SRC_SHA16)
            raise SystemExit("🔴 %s 는 등록상 관찰(㉯ⓑ)인데 관문을 통과했다 — 등록 결함" % g)
        except MdeUnderpowered:
            stamps[g] = {"레인": "관찰(㉯ⓑ)", "MDE": r["MDE"], "겨냥": r["겨냥"],
                         "여유": r["겨냥"] - r["MDE"]}
    return stamps


# ── 능형회귀 (사전 고정 추정기) ──────────────────────────────────────────────

def wmean(x, w):
    return float(np.sum(w * x) / np.sum(w))


def wvar(x, w):
    ws = np.sum(w)
    m = np.sum(w * x) / ws
    return float(np.sum(w * (x - m) ** 2) / ws)


def wmedian_abs(x, w):
    a = np.abs(x)
    o = np.argsort(a)
    a, ww = a[o], w[o]
    c = np.cumsum(ww) / np.sum(ww)
    i = int(np.searchsorted(c, 0.5))
    return float(a[min(i, len(a) - 1)])


def eq_weights(ent_idx):
    """개체 등가중 — w_i = 1/n(개체) · 합 1 로 정규화."""
    cnt = np.bincount(ent_idx)
    w = 1.0 / cnt[ent_idx].astype(np.float64)
    return w / w.sum()


def ridge_fit(X, y, w, alpha):
    Xw = X * w[:, None]
    A = X.T.dot(Xw) + alpha * np.eye(X.shape[1])
    b = X.T.dot(w * y)
    return np.linalg.solve(A, b)


def prep_cols(Xtr, w):
    """train 가중 평균·표준편차 → (mu, sd, keep)."""
    mu = (Xtr * w[:, None]).sum(axis=0) / w.sum()
    sd = np.sqrt(((Xtr - mu) ** 2 * w[:, None]).sum(axis=0) / w.sum())
    keep = sd > 1e-12
    sd = np.where(keep, sd, 1.0)
    return mu, sd, keep


def fit_predict(Xtr, ytr, wtr, Xte, alpha):
    if Xtr.shape[1] == 0:
        yb = wmean(ytr, wtr)
        return np.full(Xte.shape[0], yb), yb
    mu, sd, keep = prep_cols(Xtr, wtr)
    Ztr = ((Xtr - mu) / sd)[:, keep]
    Zte = ((Xte - mu) / sd)[:, keep]
    yb = wmean(ytr, wtr)
    beta = ridge_fit(Ztr, ytr - yb, wtr, alpha)
    return Zte.dot(beta) + yb, yb


def choose_alpha(Xtr, ytr, wtr, ent_tr, seed):
    """train «안에서만» 개체-그룹 5겹 CV → α 하나."""
    ents = np.unique(ent_tr)
    fold = {}
    for e in ents:
        h = int(hashlib.sha256(("%d|%d" % (seed, int(e))).encode()).hexdigest()[:8], 16)
        fold[int(e)] = h % CV_K
    fv = np.array([fold[int(e)] for e in ent_tr])
    best, best_v = ALPHAS[0], None
    for a in ALPHAS:
        res = np.zeros(len(ytr))
        for k in range(CV_K):
            m = fv != k
            if m.sum() < 5 or (~m).sum() < 1:
                continue
            wsub = wtr[m] / wtr[m].sum()
            pr, _ = fit_predict(Xtr[m], ytr[m], wsub, Xtr[~m], a)
            res[~m] = ytr[~m] - pr
        v = wvar(res, wtr)
        if best_v is None or v < best_v:
            best, best_v = a, v
    return best, best_v


# ── 사다리 계산 ─────────────────────────────────────────────────────────────

class Ladder(object):
    """블록 누적 사다리. blocks = [(이름, 열인덱스배열), …] · L1 은 blocks[0]."""

    def __init__(self, X, y, ent, tr, te, blocks, seed):
        self.X, self.y, self.ent = X, y, ent
        self.tr, self.te = tr, te
        self.blocks = blocks
        self.wtr = eq_weights(ent[tr])
        self.wte = eq_weights(ent[te])
        self.seed = seed
        self.alphas = {}
        self.cum = {}
        cols = []
        for name, idx in blocks:
            cols = cols + list(idx)
            self.cum[name] = np.array(sorted(set(cols)), dtype=int)

    def resid(self, upto, Xsrc=None, alpha=None):
        X = self.X if Xsrc is None else Xsrc
        c = self.cum[upto]
        Xtr, Xte = X[np.ix_(self.tr, c)], X[np.ix_(self.te, c)]
        if alpha is None:
            if upto not in self.alphas:
                self.alphas[upto] = choose_alpha(Xtr, self.y[self.tr], self.wtr,
                                                 self.ent[self.tr], self.seed)[0]
            alpha = self.alphas[upto]
        pr, _ = fit_predict(Xtr, self.y[self.tr], self.wtr, Xte, alpha)
        return self.y[self.te] - pr

    def resid_L0(self):
        return self.y[self.te] - wmean(self.y[self.tr], self.wtr)


def share(v_k, v_1):
    return 1.0 - v_k / v_1


# ── 자료 적재 ───────────────────────────────────────────────────────────────

def to_ord(s):
    try:
        return dt.date.fromisoformat(str(s)[:10]).toordinal()
    except Exception:
        return None


def load_panel():
    panel, doc2key = {}, {}
    for f in sorted(glob.glob(os.path.join(SNAPDIR, "*.jsonl.gz"))):
        base = os.path.basename(f)
        if sha256_file(f)[:16] != PANEL_SHA16.get(base):
            raise SystemExit("🔴 패널 사본 sha 불일치: %s" % base)
        dom = base.split(".")[0]
        with gzip.open(f, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                k, lang = r["키"], r.get("언어")
                if k in panel and (panel[k][3] == "ko" or lang != "ko"):
                    continue
                ords, vs = [], []
                for x, v in zip(r["날짜"], r["조회수"]):
                    try:
                        ords.append(dt.date(x // 10000, (x // 100) % 100, x % 100).toordinal())
                        vs.append(float(v))
                    except ValueError:
                        continue
                if not ords:
                    continue
                o0, o1 = min(ords), max(ords)
                vals = np.full(o1 - o0 + 1, np.nan)
                for o, v in zip(ords, vs):
                    vals[o - o0] = v
                panel[k] = (o0, vals, r.get("문서"), lang, dom)
                d = r.get("문서")
                if d and (d not in doc2key or lang == "ko"):
                    doc2key[d] = k
    return panel, doc2key


def load_grid_sov():
    gs = {}
    with gzip.open(GRID_SOV, "rt") as fh:
        for line in fh:
            r = json.loads(line)
            gs.setdefault(r["개체"], []).append(
                (r["as_of"], r.get("SoV_90"), r.get("W_ent_90")))
    for v in gs.values():
        v.sort()
    return gs


def curve_of(vals, o0, t0):
    n = len(vals)
    bi0, bi1 = t0 + BASE_LO - o0, t0 + BASE_HI - o0
    wi0, wi1 = t0 + WIN_LO - o0, t0 + WIN_HI - o0
    if bi0 < 0 or wi1 >= n:
        return None
    base = vals[bi0:bi1 + 1]
    win = vals[wi0:wi1 + 1]
    nb = int(np.sum(~np.isnan(base)))
    nw = int(np.sum(~np.isnan(win)))
    if nb < BASE_MIN or nw < WIN_MIN:
        return None
    lbase = np.log1p(base)
    mu = float(np.nanmean(lbase))
    sd = float(np.nanstd(lbase))
    idx = np.where(~np.isnan(base))[0]
    xs = idx.astype(np.float64)
    ys = lbase[idx]
    slope = float(np.polyfit(xs, ys, 1)[0]) * 30.0 if len(idx) >= 2 else 0.0
    curve = np.log1p(win) - mu
    return {"curve": curve, "base_mu": mu, "base_sd": sd, "base_slope": slope,
            "base_used": t0 + BASE_LO + int(idx[-1]), "nb": nb, "nw": nw}


def wnanmean(a):
    m = ~np.isnan(a)
    return float(a[m].mean()) if m.any() else None


# ── B층 행 만들기 ───────────────────────────────────────────────────────────

TYPES = ["출시", "개최", "시작", "발표", "공개", "개봉", "데뷔", "방영", "컴백"]
TRUSTS = ["E1", "E2모호", "E2미해소", "E3"]


def build_rows_B(panel, doc2key, gs):
    """사건 원장 v0 → 창 완비 행 + t0 이전 특징. 개입은 본 등록 모집단 밖(§1 정찰 기준)."""
    ev_all = []          # (t0, 유형, 개체키)
    with gzip.open(os.path.join(LEDGER_DIR, "events.jsonl.gz"), "rt") as fh:
        raw = []
        for line in fh:
            r = json.loads(line)
            t0 = to_ord(r.get("event_time"))
            if t0 is None:
                continue
            raw.append(r)
            ev_all.append((t0, r.get("정규유형"), r.get("개체키")))
    ev_all.sort(key=lambda x: x[0])
    all_ord = [x[0] for x in ev_all]
    by_type = {}
    by_ent = {}
    for t0, g, k in ev_all:
        by_type.setdefault(g, []).append(t0)
        by_ent.setdefault(k, []).append((t0, g))
    for v in by_type.values():
        v.sort()
    for v in by_ent.values():
        v.sort()

    lad = {"0_원장": len(raw), "1_일단위시각": len(raw), "2_곡선가용": 0, "3_창완비": 0}
    rows = []
    leak_margin = []
    for r in raw:
        t0 = to_ord(r.get("event_time"))
        k, docname = r.get("개체키"), r.get("위키문서")
        pk = k if k in panel else (doc2key.get(docname) if docname else None)
        if pk is None:
            continue
        lad["2_곡선가용"] += 1
        o0, vals, pdoc, lang, dom = panel[pk]
        c = curve_of(vals, o0, t0)
        if c is None:
            continue
        lad["3_창완비"] += 1
        cur = c["curve"]
        R = wnanmean(cur[RESP_LO - WIN_LO:RESP_HI - WIN_LO + 1])
        if R is None:
            continue
        runup7 = wnanmean(cur[-7 - WIN_LO:-1 - WIN_LO + 1])
        pre30 = wnanmean(cur[-30 - WIN_LO:-8 - WIN_LO + 1])
        # 경쟁 밀도 (엄격 t0 이전 30일)
        lo, hi = t0 - 30, t0
        c_all = bisect.bisect_left(all_ord, hi) - bisect.bisect_left(all_ord, lo)
        tt = by_type.get(r.get("정규유형"), [])
        c_typ = bisect.bisect_left(tt, hi) - bisect.bisect_left(tt, lo)
        # 직전 사건 이력
        mine = by_ent.get(k, [])
        mo = [x[0] for x in mine]
        i_lt = bisect.bisect_left(mo, t0)
        h90 = i_lt - bisect.bisect_left(mo, t0 - 90)
        h365 = i_lt - bisect.bisect_left(mo, t0 - 365)
        h365t = sum(1 for (o, g) in mine[bisect.bisect_left(mo, t0 - 365):i_lt]
                    if g == r.get("정규유형"))
        gap = (t0 - mo[i_lt - 1]) if i_lt > 0 else None
        prev_day = mo[i_lt - 1] if i_lt > 0 else None
        pub = to_ord(r.get("최초pub_time") or "")
        lead = (t0 - pub) if (pub is not None and pub < t0) else None
        # SoV 격자 (마지막 as_of < t0)
        sov = logw = None
        sov_asof = None
        gv = gs.get(pdoc) if pdoc else None
        if gv:
            iso = dt.date.fromordinal(t0).isoformat()
            j = bisect.bisect_left([x[0] for x in gv], iso)
            if j > 0:
                sov_asof, s_, w_ = gv[j - 1]
                if s_ is not None:
                    sov = float(s_)
                if w_ is not None:
                    logw = math.log1p(float(w_))
        # leak 스탬프 — 실제로 쓴 «가장 늦은» 입력일
        used = [c["base_used"], t0 - 1]
        if prev_day is not None:
            used.append(prev_day)
        if pub is not None:
            used.append(pub)
        if sov_asof is not None:
            used.append(to_ord(sov_asof))
        latest = max(used)
        assert_no_leak([{"id": r.get("사건id"), "published_at":
                         dt.date.fromordinal(latest).isoformat()}],
                       dt.date.fromordinal(t0), "1030 L3 특징 %s" % r.get("사건id"))
        leak_margin.append(t0 - latest)
        rows.append({
            "id": r.get("사건id"), "pk": pk, "ent": k, "t0": t0, "유형": r.get("정규유형"),
            "층": r.get("신뢰층"), "dom": dom, "R": R,
            "comp30_type": math.log1p(c_typ), "comp30_all": math.log1p(c_all),
            "hist90": math.log1p(h90), "hist365": math.log1p(h365),
            "hist365_type": math.log1p(h365t),
            "gap_prev": (math.log1p(gap) if gap is not None else None),
            "lead": (math.log1p(lead) if lead is not None else None),
            "sov90": sov, "logW90": logw,
            "base_mu": c["base_mu"], "base_sd": c["base_sd"], "base_slope": c["base_slope"],
            "runup7": runup7, "pre30": pre30,
            "문서수": math.log1p(float(r.get("문서수") or 0)),
            "행수": math.log1p(float(r.get("행수") or 0)),
            "conf_max": float(r.get("conf_max") or 0.0),
            "예고": r.get("예고"), "year": dt.date.fromordinal(t0).year,
        })
    return rows, lad, leak_margin


def onehot(vals, levels):
    X = np.zeros((len(vals), len(levels)))
    for i, v in enumerate(vals):
        if v in levels:
            X[i, levels.index(v)] = 1.0
    return X


def numcol(rows, key, tr_mask):
    """결측 = train 중앙값 대입 + 결측 지시자(조항 59 — 0 대입 금지)."""
    raw = np.array([np.nan if r.get(key) is None else float(r[key]) for r in rows])
    miss = np.isnan(raw)
    tr_ok = (~miss) & tr_mask
    med = float(np.median(raw[tr_ok])) if tr_ok.any() else 0.0
    out = np.where(miss, med, raw)
    return out, miss.astype(float), int(miss.sum())


def build_X_B(rows, tr_mask, with_entity):
    ents = sorted(set(r["ent"] for r in rows))
    doms = sorted(set(r["dom"] for r in rows))
    years = sorted(set(r["year"] for r in rows))
    cols, names, blocks = [], [], []
    cov = {}

    def add(block, mat, nms):
        i0 = len(cols)
        for j in range(mat.shape[1]):
            cols.append(mat[:, j])
        names.extend(nms)
        blocks.append((block, np.arange(i0, len(cols))))

    # L1
    m1 = [onehot([r["유형"] for r in rows], TYPES)]
    n1 = ["유형=%s" % t for t in TYPES]
    if with_entity:
        tr_ents = set(r["ent"] for r, m in zip(rows, tr_mask) if m)
        m1.insert(0, onehot([r["ent"] for r in rows], ents))
        n1 = ["개체=%d" % i for i in range(len(ents))] + n1
        unseen = np.array([[0.0 if r["ent"] in tr_ents else 1.0] for r in rows])
        m1.append(unseen)
        n1 = n1 + ["미지개체"]
    add("L1", np.hstack(m1), n1)
    # L2
    add("L2", np.hstack([onehot([r["dom"] for r in rows], doms),
                         onehot([r["year"] for r in rows], years)]),
        ["도메인=%s" % d for d in doms] + ["연도=%d" % y for y in years])
    # L3a
    keys3a = ["comp30_type", "comp30_all", "hist90", "hist365", "hist365_type",
              "gap_prev", "lead", "sov90", "logW90"]
    mats, nms = [], []
    for k in keys3a:
        v, miss, nm = numcol(rows, k, tr_mask)
        cov[k] = {"결측": nm, "n": len(rows)}
        mats.append(v[:, None]); nms.append(k)
        if k in ("gap_prev", "sov90"):
            mats.append(miss[:, None]); nms.append(k + "_결측")
    add("L3a", np.hstack(mats), nms)
    # L3b
    keys3b = ["base_mu", "base_sd", "base_slope", "runup7", "pre30"]
    mats, nms = [], []
    for k in keys3b:
        v, miss, nm = numcol(rows, k, tr_mask)
        cov[k] = {"결측": nm, "n": len(rows)}
        mats.append(v[:, None]); nms.append(k)
    add("L3b", np.hstack(mats), nms)
    # L4
    mats = [onehot([r["층"] for r in rows], TRUSTS),
            onehot([r["예고"] for r in rows], ["예고", "동시"])]
    nms = ["층=%s" % t for t in TRUSTS] + ["예고=예고", "예고=동시"]
    for k in ("문서수", "행수", "conf_max"):
        v, miss, nm = numcol(rows, k, tr_mask)
        mats.append(v[:, None]); nms.append(k)
    add("L4", np.hstack(mats), nms)

    X = np.column_stack(cols)
    return X, names, blocks, cov


# ── 판정 기계 (위약 순열 · 붓스트랩 · 게이트) ────────────────────────────────

def block_cols(blocks, names_wanted):
    c = []
    for nm, idx in blocks:
        if nm in names_wanted:
            c.extend(list(idx))
    return np.array(sorted(set(c)), dtype=int)


def placebo_shares(X, y, ent, tr, te, blocks, perm_cols, upto, alpha, v1, B, seed):
    """perm_cols 를 «전 표본»에서 행 단위 동시 순열 → 같은 α 로 재적합 → 설명 몫 분포."""
    n = X.shape[0]
    lad = Ladder(X, y, ent, tr, te, blocks, seed)
    Xp = X.copy()
    src = X[:, perm_cols]
    out = np.zeros(B)
    rng = np.random.RandomState(seed)
    for b in range(B):
        Xp[:, perm_cols] = src[rng.permutation(n)]
        e = lad.resid(upto, Xsrc=Xp, alpha=alpha)
        out[b] = share(wvar(e, lad.wte), v1)
    return out


def boot_se(ent_te, y_te, resid_map, v1_key, B, seed):
    """개체 클러스터 붓스트랩 — test 클러스터만 재표집(적합은 고정)."""
    ents = np.unique(ent_te)
    idx_by = {int(e): np.where(ent_te == e)[0] for e in ents}
    rng = np.random.RandomState(seed)
    keys = list(resid_map.keys())
    acc = {k: [] for k in keys}
    acc_sh = {k: [] for k in keys}
    acc_med = {k: [] for k in keys}
    for b in range(B):
        pick = rng.randint(0, len(ents), len(ents))
        idx, gid = [], []
        for j, pi in enumerate(pick):
            ii = idx_by[int(ents[pi])]
            idx.extend(ii.tolist()); gid.extend([j] * len(ii))
        idx = np.array(idx); gid = np.array(gid)
        w = eq_weights(gid)
        v = {k: wvar(resid_map[k][idx], w) for k in keys}
        for k in keys:
            acc[k].append(v[k])
            acc_sh[k].append(1.0 - v[k] / v[v1_key] if v[v1_key] > 0 else np.nan)
            acc_med[k].append(wmedian_abs(resid_map[k][idx], w))
    return ({k: float(np.std(acc[k], ddof=1)) for k in keys},
            {k: float(np.nanstd(acc_sh[k], ddof=1)) for k in keys},
            {k: float(np.std(acc_med[k], ddof=1)) for k in keys})


def run_regime(tag, X, y, ent, tr, te, blocks, gates, seed, twin, out):
    """한 홀드아웃 레인의 사다리 + 위약 + 붓스트랩."""
    lad = Ladder(X, y, ent, tr, te, blocks, seed)
    levels = [b[0] for b in blocks]
    resid = {"L0": lad.resid_L0()}
    for lv in levels:
        resid[lv] = lad.resid(lv)
    v = {k: wvar(resid[k], lad.wte) for k in resid}
    med = {k: wmedian_abs(resid[k], lad.wte) for k in resid}
    v1 = v["L1"]
    A = {k: share(v[k], v1) for k in resid}
    se_v, se_sh, se_med = boot_se(ent[te], y[te], resid, "L1", B_BOOT, seed)
    res = {"레인": tag, "n_train": int(len(tr)), "n_test": int(len(te)),
           "개체_train": int(len(np.unique(ent[tr]))), "개체_test": int(len(np.unique(ent[te]))),
           "α": {k: lad.alphas.get(k) for k in levels},
           "층": {}, "게이트": {}, "낙인": [STAMP_ASSOC, STAMP_146]}
    for k in ["L0"] + levels:
        res["층"][k] = {"Var(잔차)": v[k], "Var_SE": se_v[k], "median|e|": med[k],
                        "median_SE": se_med[k], "설명몫": A[k], "설명몫_SE": se_sh[k]}
    # 위약
    q_lvl = 1.0 - ALPHA_FAM / M_GATES
    for gname, spec in gates.items():
        upto, perm, aim, lane = spec["upto"], spec["perm"], spec["aim"], spec["lane"]
        pc = block_cols(blocks, perm)
        alpha = lad.alphas[upto]
        P = placebo_shares(X, y, ent, tr, te, blocks, pc, upto, alpha, v1, B_PL, seed)
        Pt = placebo_shares(X, y, ent, tr, te, blocks, pc, upto, alpha, v1, B_PL, twin)
        # 증분 게이트: 순열은 «증분 블록만» → 밑층 몫 A[minus] 는 불변이라 그대로 뺀다
        if spec.get("minus") is not None:
            base = A[upto] - A[spec["minus"]]
            P = P - A[spec["minus"]]
            Pt = Pt - A[spec["minus"]]
        else:
            base = A[upto]
        q = float(np.quantile(P, q_lvl))
        sd, sdt = float(np.std(P, ddof=1)), float(np.std(Pt, ddof=1))
        J = abs(sd - sdt) / math.sqrt(2.0)
        mde = mde_of(se=sd, jitter=J)
        stamp = None
        try:
            stamp = assert_mde(mde, AIM if aim == "AIM" else AIM_INC, SRC_SHA16)
            powered = True
        except MdeUnderpowered as e:
            powered = False
            stamp = {"레인": "관찰(MDE 미달)", "사유": str(e)[:200], "MDE": mde}
        pval = (1.0 + float(np.sum(P >= base))) / (B_PL + 1.0)
        med_p = float(np.median(P))
        se_med_p = 1.2533 * sd / math.sqrt(B_PL)
        zero_ok = abs(med_p) <= 2 * se_med_p
        res["게이트"][gname] = {
            "자": upto + ("" if spec.get("minus") is None else " − " + spec["minus"]),
            "레인": lane, "A": base, "q_corr": q, "Δ": base - q, "여유": base - q,
            "통과": bool(gate_pass(base, q)), "순열p": pval,
            "위약": {"평균": float(np.mean(P)), "SD": sd, "중앙": med_p, "q50": float(np.median(P)),
                     "q95": float(np.quantile(P, 0.95)), "q_corr분위": q_lvl},
            "지터J": J, "실측MDE": mde, "MDE스탬프": stamp, "검정력": powered,
            "0중심게이트": bool(zero_ok),
            "퇴화문턱(문턱≤0)": bool(q <= 0),
            "실효검출한계_겨냥초과": bool(q > (AIM if aim == "AIM" else AIM_INC)),
        }
    out[tag] = res
    return res


# ── A층 (1020 짝 · LOGO) ────────────────────────────────────────────────────

def build_A():
    recs = {}
    for line in open(IVT_LEDGER, encoding="utf-8"):
        r = json.loads(line)
        recs[r["record_id"]] = r
    opens = []
    for r in recs.values():
        f = to_ord((r["A"]["when"] or {}).get("opened_at"))
        if f is not None:
            opens.append((f, (r["A"]["what"] or {}).get("category") or ""))
    opens.sort(key=lambda x: x[0])
    fs = [x[0] for x in opens]

    def pre90(f):
        return bisect.bisect_left(fs, f) - bisect.bisect_left(fs, f - 90)

    pairs = json.load(open(PAIRS1020, encoding="utf-8"))["pairs"]
    rows = []
    margins = []
    for p in pairs:
        ra, rb = recs[p["rid_a"]], recs[p["rid_b"]]
        wa, wb = ra["A"]["when"] or {}, rb["A"]["when"] or {}
        fa, fb = to_ord(wa.get("opened_at")), to_ord(wb.get("opened_at"))
        ha = (ra["C"].get("ip_history") or {})
        hb = (rb["C"].get("ip_history") or {})
        pa, pb = pre90(fa), pre90(fb)
        assert_no_leak([{"id": p["rid_b"], "published_at":
                         dt.date.fromordinal(fb - 1).isoformat()}],
                       dt.date.fromordinal(fb), "1030 A층 %s" % p["rid_b"])
        margins.append(1)
        da, db = wa.get("duration_days"), wb.get("duration_days")
        rows.append({
            "g": p["g"], "d": float(p["d"]), "AB": 1.0 if p.get("AB") else 0.0,
            "clean": 1.0 if p.get("clean") else 0.0, "layer": p.get("layer"),
            "vt_same": (None if p.get("vt_same") is None else (1.0 if p["vt_same"] else 0.0)),
            "ln_dur_ratio": (None if p.get("dur_ratio") in (None, 0) else math.log(float(p["dur_ratio"]))),
            "fe_same": (None if p.get("fe_same") is None else (1.0 if p["fe_same"] else 0.0)),
            "mon_sin": math.sin(2 * math.pi * dt.date.fromordinal(fb).month / 12.0),
            "mon_cos": math.cos(2 * math.pi * dt.date.fromordinal(fb).month / 12.0),
            "ln_gap": math.log1p(max(fb - fa, 0)),
            "d_ln_dur": (None if (not da or not db) else math.log(float(db)) - math.log(float(da))),
            "d_weekend": (None if (wa.get("weekend_share") is None or wb.get("weekend_share") is None)
                          else float(wb["weekend_share"]) - float(wa["weekend_share"])),
            "d_holiday": (None if (wa.get("holiday_days") is None or wb.get("holiday_days") is None)
                          else float(wb["holiday_days"]) - float(wa["holiday_days"])),
            "pc_later": float(hb.get("prior_count") or 0),
            "ln_pc_later": math.log1p(float(hb.get("prior_count") or 0)),
            "d_pc": float((hb.get("prior_count") or 0) - (ha.get("prior_count") or 0)),
            "msl_later": (None if hb.get("months_since_last") is None else float(hb["months_since_last"])),
            "ln_pre90_later": math.log1p(pb),
            "d_pre90": float(pb - pa),
        })
    return rows, margins


def build_X_A(rows, tr_mask):
    cols, names, blocks = [], [], []

    def add(block, mats, nms):
        i0 = len(cols)
        M = np.hstack(mats)
        for j in range(M.shape[1]):
            cols.append(M[:, j])
        names.extend(nms)
        blocks.append((block, np.arange(i0, len(cols))))

    add("L1", [np.zeros((len(rows), 0))], [])           # 짝짓기가 개체를 이미 뺐다
    mats, nms = [], []
    for k in ("vt_same", "ln_dur_ratio", "fe_same", "mon_sin", "mon_cos", "ln_gap",
              "d_ln_dur", "d_weekend", "d_holiday"):
        v, miss, nm = numcol(rows, k, tr_mask)
        mats.append(v[:, None]); nms.append(k)
        if nm:
            mats.append(miss[:, None]); nms.append(k + "_결측")
    mats.append(onehot([r["layer"] for r in rows], ["mm", "ii", "mi"]))
    nms.extend(["layer=mm", "layer=ii", "layer=mi"])
    add("L2", mats, nms)
    mats, nms = [], []
    for k in ("pc_later", "ln_pc_later", "d_pc", "msl_later", "ln_pre90_later", "d_pre90"):
        v, miss, nm = numcol(rows, k, tr_mask)
        mats.append(v[:, None]); nms.append(k)
        if nm:
            mats.append(miss[:, None]); nms.append(k + "_결측")
    add("L3", mats, nms)
    add("L4", [np.array([[r["AB"], r["clean"]] for r in rows])], ["AB", "clean"])
    return np.column_stack(cols), names, blocks


def logo_alphas(X, y, gid, cols, seed):
    """각 LOGO 폴드의 «train 안에서만» 그룹 5겹 CV 로 α 를 고른다(등록 §4 문언 그대로).
    반환 = {그룹: α} — 위약은 이 α 벡터를 그대로 재사용한다."""
    out = {}
    for g in np.unique(gid):
        tr = gid != g
        if cols.size == 0:
            out[int(g)] = ALPHAS[0]
            continue
        w = eq_weights(gid[tr])
        a, _ = choose_alpha(X[np.ix_(tr, cols)], y[tr], w, gid[tr], seed)
        out[int(g)] = a
    return out


def logo_resid(X, y, gid, cols, alpha_by_fold):
    e = np.zeros(len(y))
    for g in np.unique(gid):
        te = gid == g
        tr = ~te
        w = eq_weights(gid[tr])
        if cols.size == 0:
            pr = np.full(int(te.sum()), wmean(y[tr], w))
        else:
            pr, _ = fit_predict(X[np.ix_(tr, cols)], y[tr], w, X[np.ix_(te, cols)],
                                alpha_by_fold[int(g)])
        e[te] = y[te] - pr
    return e


def run_A(out):
    rows, margins = build_A()
    gid_lab = sorted(set(r["g"] for r in rows))
    gid = np.array([gid_lab.index(r["g"]) for r in rows])
    y = np.array([r["d"] for r in rows])
    tr_all = np.ones(len(rows), dtype=bool)
    X, names, blocks = build_X_A(rows, tr_all)
    w = eq_weights(gid)
    v1 = wvar(y, w)                       # L1 = d 자체 (짝짓기가 개체를 뺐다)
    cum, cols = {}, []
    for nm, idx in blocks:
        cols = cols + list(idx)
        cum[nm] = np.array(sorted(set(cols)), dtype=int)
    alphas, resid, v, A, medm = {}, {"L1": y - wmean(y, w)}, {}, {}, {}
    v["L1"] = v1
    A["L1"] = 0.0
    medm["L1"] = wmedian_abs(resid["L1"], w)
    for nm in ("L2", "L3", "L4"):
        alphas[nm] = logo_alphas(X, y, gid, cum[nm], SEED_MAIN)
        resid[nm] = logo_resid(X, y, gid, cum[nm], alphas[nm])
        v[nm] = wvar(resid[nm], w)
        A[nm] = share(v[nm], v1)
        medm[nm] = wmedian_abs(resid[nm], w)
    se_v, se_sh, se_med = boot_se(gid, y, resid, "L1", B_BOOT, SEED_MAIN)
    # 위약 — L2∪L3 순열 (A(L3) 대응)
    pc = block_cols(blocks, {"L2", "L3"})
    P = np.zeros(B_PL)
    rng = np.random.RandomState(SEED_MAIN)
    src = X[:, pc]
    Xp = X.copy()
    for b in range(B_PL):
        Xp[:, pc] = src[rng.permutation(len(rows))]
        P[b] = share(wvar(logo_resid(Xp, y, gid, cum["L3"], alphas["L3"]), w), v1)  # α 재사용
    q = float(np.quantile(P, 1.0 - ALPHA_FAM / M_GATES))
    sd = float(np.std(P, ddof=1))
    out["A층"] = {
        "레인": "A층 · 1020 짝 47 · LOGO · [관찰](㉯ⓑ)",
        "n_쌍": len(rows), "n_그룹": len(gid_lab),
        "α(폴드별)": {k: sorted(set(v.values())) for k, v in alphas.items()},
        "층": {k: {"Var(잔차)": v[k], "Var_SE": se_v[k], "median|e|": medm[k],
                   "median_SE": se_med[k], "설명몫": A[k], "설명몫_SE": se_sh[k]}
              for k in ("L1", "L2", "L3", "L4")},
        "O4": {"A": A["L3"], "q_corr": q, "Δ": A["L3"] - q, "여유": A["L3"] - q,
               "통과(참고)": bool(gate_pass(A["L3"], q)),
               "순열p": (1.0 + float(np.sum(P >= A["L3"]))) / (B_PL + 1.0),
               "위약SD": sd, "실측MDE": mde_of(se=sd, jitter=0.0),
               "레인": "관찰 — 판정 아님(사전등록 ㉯ⓑ)"},
        "×배 눈금(참고)": {"median|d| 실측": medm["L1"],
                        "exp(median|d|)": math.exp(medm["L1"])},
        "낙인": [STAMP_ASSOC, "A층은 n=47·그룹 32 — 사전등록에서 [관찰]로 강등됐다(부칙 6 ㉯ⓑ)."],
    }
    return out["A층"]


def lobo(tag, X, y, ent, tr, te, blocks, upto, out):
    """leave-one-block-out — «관찰만»(사후 선택 금지)."""
    lad = Ladder(X, y, ent, tr, te, blocks, SEED_MAIN)
    full = lad.resid(upto)
    v_full = wvar(full, lad.wte)
    v1 = wvar(lad.resid("L1"), lad.wte)
    base = share(v_full, v1)
    res = {}
    order = [b[0] for b in blocks]
    upto_i = order.index(upto)
    keep_all = lad.cum[upto]
    for nm, idx in blocks[1:upto_i + 1]:
        cols = np.array([c for c in keep_all if c not in set(idx.tolist())], dtype=int)
        Xtr, Xte = X[np.ix_(tr, cols)], X[np.ix_(te, cols)]
        pr, _ = fit_predict(Xtr, y[tr], lad.wtr, Xte, lad.alphas[upto])
        res[nm] = {"설명몫(그 블록 제외)": share(wvar(y[te] - pr, lad.wte), v1),
                   "몫 손실": base - share(wvar(y[te] - pr, lad.wte), v1)}
    # L3a 안의 특징군 (관찰)
    out[tag] = {"기준 설명몫": base, "블록 제외": res}
    return out[tag]


def selftest():
    """합성 자료 — 신호가 있으면 몫 > 0(참) · 순열하면 ≈ 0(거짓)."""
    rng = np.random.RandomState(7)
    n, G = 600, 40
    ent = rng.randint(0, G, n)
    f = rng.randn(n)
    y = 0.8 * f + 0.5 * rng.randn(n) + 0.3 * rng.randn(G)[ent]
    X = np.column_stack([onehot(list(ent), list(range(G))), f])
    blocks = [("L1", np.arange(0, G)), ("L3", np.array([G]))]
    tr = np.where(np.arange(n) < 400)[0]
    te = np.where(np.arange(n) >= 400)[0]
    lad = Ladder(X, y, ent, tr, te, blocks, SEED_MAIN)
    v1 = wvar(lad.resid("L1"), lad.wte)
    A = share(wvar(lad.resid("L3"), lad.wte), v1)
    Xp = X.copy()
    Xp[:, G] = X[rng.permutation(n), G]
    Ap = share(wvar(lad.resid("L3", Xsrc=Xp, alpha=lad.alphas["L3"]), lad.wte), v1)
    cases = [("① 신호 있으면 몫>0.3", A > 0.3, A),
             ("② 순열하면 몫≈0(<0.1)", Ap < 0.1, Ap),
             ("③ 순열 몫 < 실측 몫", Ap < A, A - Ap),
             ("④ 가중 분산 항등", abs(wvar(np.array([1.0, 3.0]), np.array([0.5, 0.5])) - 1.0) < 1e-12, None),
             ("⑤ 개체 등가중 합=1", abs(eq_weights(np.array([0, 0, 1])).sum() - 1.0) < 1e-12, None)]
    bad = [c[0] for c in cases if not c[1]]
    if bad:
        raise SystemExit("🔴 자기시험 실패 — %r · 측정 없이 중단" % bad)
    return [{"경우": c[0], "기대대로": bool(c[1]), "값": c[2]} for c in cases]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="run")
    args = ap.parse_args()
    os.makedirs(OUTDIR, exist_ok=True)
    t_start = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    my_sha = sha256_file(os.path.abspath(__file__))
    log(단계="시작", 러너sha256=my_sha, 시각0=t_start, load1=os.getloadavg()[0], stage=args.stage)

    gate0 = tree_gate()
    log(단계="⓪관문", **gate0)
    probe = direction_probe()
    mde_rows = parse_mde_table()
    mde_stamps = mde_start_gate(mde_rows)
    st = selftest()
    log(단계="관문통과", 방향탐침=len(probe), MDE시작관문=list(mde_stamps), 자기시험=len(st))
    if args.stage == "selftest":
        print(json.dumps({"selftest": True, "방향탐침": probe, "자기시험": st,
                          "MDE시작관문": mde_stamps}, ensure_ascii=False, indent=1, default=str))
        return
    load_gate()

    for p, s16 in ((os.path.join(LEDGER_DIR, "events.jsonl.gz"), EV_SHA16),
                   (os.path.join(LEDGER_DIR, "merged_view.jsonl.gz"), MV_SHA16),
                   (IVT_LEDGER, IVT_SHA16), (PAIRS1020, PAIRS_SHA16), (GRID_SOV, GRID_SHA16)):
        if sha256_file(p)[:16] != s16:
            raise SystemExit("🔴 입력 sha 불일치: %s" % p)
    log(단계="입력sha 대조", 통과=True)

    panel, doc2key = load_panel()
    gs = load_grid_sov()
    log(단계="패널", 개체=len(panel), 문서색인=len(doc2key), 격자개체=len(gs))

    rows, lad_B, leak_margin = build_rows_B(panel, doc2key, gs)
    log(단계="B층 행", n=len(rows), 사다리=lad_B,
        leak스탬프=len(leak_margin), 최소여유일=int(min(leak_margin)))

    t0s = np.array([r["t0"] for r in rows])
    cut = int(sorted(t0s)[int(len(t0s) * CUT_Q)])   # §4 컷 = t0 70분위(하위 보간)
    ents_lab = sorted(set(r["ent"] for r in rows))
    ent = np.array([ents_lab.index(r["ent"]) for r in rows])
    y = np.array([r["R"] for r in rows])

    out = {}
    # ── H-T (정본 판정) ──
    tr_m = t0s < cut
    te_m = t0s >= cut
    X, names, blocks, cov = build_X_B(rows, tr_m, with_entity=True)
    tr, te = np.where(tr_m)[0], np.where(te_m)[0]
    gates_HT = {
        "G1": {"upto": "L3b", "perm": {"L2", "L3a", "L3b"}, "aim": "AIM", "lane": "판정"},
        "G2": {"upto": "L3a", "perm": {"L2", "L3a"}, "aim": "AIM", "lane": "판정"},
        "O1": {"upto": "L3a", "minus": "L2", "perm": {"L3a"}, "aim": "INC", "lane": "관찰"},
        "O2": {"upto": "L3b", "minus": "L3a", "perm": {"L3b"}, "aim": "INC", "lane": "관찰"},
    }
    log(단계="H-T 시작", n_train=int(tr_m.sum()), n_test=int(te_m.sum()),
        컷=dt.date.fromordinal(cut).isoformat())
    run_regime("B층 H-T(시간 전방·개체 공유)", X, y, ent, tr, te, blocks, gates_HT,
               SEED_MAIN, SEED_TWIN, out)
    log(단계="H-T 완료", 게이트=list(gates_HT))
    lobo_out = {}
    lobo("B층 H-T", X, y, ent, tr, te, blocks, "L3b", lobo_out)

    # ── H-E (개체 분리 ∧ 시간 전방 · 관찰) ──
    def held(k):
        return int(hashlib.sha256(("1030|" + k).encode()).hexdigest()[:8], 16) % HOLD_MOD >= HOLD_MIN
    hold = np.array([held(r["ent"]) for r in rows])
    trE_m = (~hold) & (t0s < cut)
    teE_m = hold & (t0s >= cut)
    XE, namesE, blocksE, covE = build_X_B(rows, trE_m, with_entity=False)
    gates_HE = {"O3": {"upto": "L3b", "perm": {"L2", "L3a", "L3b"}, "aim": "AIM", "lane": "관찰"}}
    log(단계="H-E 시작", n_train=int(trE_m.sum()), n_test=int(teE_m.sum()))
    run_regime("B층 H-E(개체 분리∧시간 전방)", XE, y, ent, np.where(trE_m)[0],
               np.where(teE_m)[0], blocksE, gates_HE, SEED_MAIN, SEED_TWIN, out)
    log(단계="H-E 완료")

    # ── A층 ──
    a = run_A(out)
    log(단계="A층 완료", n_쌍=a["n_쌍"])

    # ── 조항 79: cluster_se 칸 전량 분모 ──
    se_cells, se_over = 0, 0
    for tag, blk in out.items():
        for k, d in (blk.get("층") or {}).items():
            for key in ("Var_SE", "median_SE", "설명몫_SE"):
                if d.get(key) is not None:
                    se_cells += 1
            if d.get("설명몫_SE") and abs(d["설명몫"]) > 2 * d["설명몫_SE"]:
                se_over += 1
    # 자료 탐침 (측정 «후»)
    probe_bad = {"㉰악화참": 0, "㉱개선거짓": 0, "퇴화문턱": 0, "퇴화문턱_게이트": []}
    for tag, blk in out.items():
        for g, d in (blk.get("게이트") or {}).items():
            thr = d["q_corr"]
            if thr <= 0:
                probe_bad["퇴화문턱"] += 1
                probe_bad["퇴화문턱_게이트"].append(g)
            t_ = abs(thr) if abs(thr) > 1e-9 else 0.1
            if gate_pass(thr - 2 * t_, thr):
                probe_bad["㉰악화참"] += 1
            if not gate_pass(thr + 2 * t_, thr):
                probe_bad["㉱개선거짓"] += 1

    ht = out["B층 H-T(시간 전방·개체 공유)"]
    k_pass = sum(1 for g in ("G1", "G2")
                 if ht["게이트"][g]["통과"] and ht["게이트"][g]["검정력"]
                 and not ht["게이트"][g]["실효검출한계_겨냥초과"]
                 and not ht["게이트"][g]["퇴화문턱(문턱≤0)"])
    verdict = {"연언 채점": "%d/%d" % (k_pass, M_GATES),
               "판정어": ("명제 통과" if k_pass == M_GATES else
                        ("가설 후보(1/2)" if k_pass == 1 else "MDE 미만 — 미판정"))}

    t_end = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    my_sha2 = sha256_file(os.path.abspath(__file__))
    meta = {"사이클": 1030, "사전등록": "docs/탐색/1030.md",
            "사전등록_sha256": sha256_file(DOC), "러너sha256": my_sha,
            "러너sha_전후일치": my_sha == my_sha2, "시작": t_start, "끝": t_end,
            "⓪관문": gate0, "방향탐침": probe, "자기시험": st, "MDE시작관문": mde_stamps,
            "B층 사다리": lad_B, "B층 행": len(rows), "B층 개체": len(ents_lab),
            "컷": dt.date.fromordinal(cut).isoformat(),
            "H-T": {"train": int(tr_m.sum()), "test": int(te_m.sum()),
                    "개체_test": int(len(set(ent[te].tolist())))},
            "H-E": {"train": int(trE_m.sum()), "test": int(teE_m.sum()),
                    "개체_test": int(len(set(ent[np.where(teE_m)[0]].tolist())))},
            "leak스탬프": {"n": len(leak_margin), "최소여유일": int(min(leak_margin))},
            "특징 커버리지": cov, "자료탐침": probe_bad,
            "cluster_se 칸": {"전량": se_cells, "2·SE 초과(설명몫)": se_over},
            "상수": {"창": [WIN_LO, WIN_HI], "기준선": [BASE_LO, BASE_HI],
                     "결과창": [RESP_LO, RESP_HI], "완비": [BASE_MIN, WIN_MIN],
                     "B_boot": B_BOOT, "B_pl": B_PL, "씨앗": [SEED_MAIN, SEED_TWIN],
                     "겨냥": AIM, "증분겨냥": AIM_INC, "m": M_GATES, "α격자": list(ALPHAS)},
            "입력sha16": {"events": EV_SHA16, "merged_view": MV_SHA16, "ledger": IVT_SHA16,
                          "pairs1020": PAIRS_SHA16, "grid_sov": GRID_SHA16,
                          "패널사본": PANEL_SHA16},
            "판정": verdict, "낙인": [STAMP_ASSOC, STAMP_146]}

    with open(os.path.join(OUTDIR, "ladder1030.json"), "w") as f:
        json.dump({"판": "조건 사다리 1030", "레인": out, "판정": verdict},
                  f, ensure_ascii=False, indent=1, default=str)
    with open(os.path.join(OUTDIR, "features1030.json"), "w") as f:
        json.dump({"열이름_HT": names, "블록": {b[0]: len(b[1]) for b in blocks},
                   "커버리지": cov, "leave_one_block_out(관찰)": lobo_out},
                  f, ensure_ascii=False, indent=1, default=str)
    with open(os.path.join(OUTDIR, "meta1030.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, default=str)
    with gzip.open(os.path.join(OUTDIR, "rows1030.jsonl.gz"), "wt") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    log(단계="완료", 끝=t_end, 판정=verdict, 러너sha_전후일치=my_sha == my_sha2)
    print(json.dumps({"완료": True, "판정": verdict}, ensure_ascii=False))


if __name__ == "__main__":
    main()
