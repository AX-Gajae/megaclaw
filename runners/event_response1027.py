# -*- coding: utf-8 -*-
"""사이클 1027 — 사건 반응 함수 도서관 v0 (사전등록: docs/탐색/1027.md — 실측 «전» 커밋).

유형별 평균 관심 곡선([-30,+60] · log1p 기준선 잔차) · 개체 클러스터 붓스트랩 띠 ·
위약(무사건 시점)=MDE · 조항 79 Bonferroni(m=6) · 정직 낙인(조건부 연관 — 인과 아님) ·
이중 정렬(발표 vs 사건일) 관찰 · 개입(팝업개최) [관찰] 병기.

위생: CPU ≤5스레드 · load1>10 대기 · 전 입력 읽기 전용 · wiki_daily 는 시작 때 사본 격리 ·
주행 중 소스 수정 금지(자기 sha 전후 대조) · 유료 API·네트워크 0.
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")
import datetime as dt
import gzip
import hashlib
import json
import math
import re
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from pretrain.leak_guard import assert_no_leak
from pretrain.mde_guard import assert_mde, mde_of, MdeUnderpowered

REPO = "/Users/ax/world_model"
LEDGER = "/Users/ax/wm_harvest/foundation/event_ledger"
OUTDIR = "/Users/ax/wm_harvest/foundation/event_response"
SNAPDIR = os.path.join(OUTDIR, "panel_snapshot")
DOC = os.path.join(REPO, "docs/탐색/1027.md")
OUT = os.path.join(OUTDIR, "run1027.out")

# ── 사전 고정 상수 (등록문 §2~§4 — 여기 바꾸면 등록 위반) ─────────────────────
WIN_LO, WIN_HI = -30, 60            # 반응 창 91칸
BASE_LO, BASE_HI = -37, -8          # 기준선 창 30일
BASE_MIN, WIN_MIN = 24, 86          # 창 결측 규칙
PLACEBO_DIST = 45                   # 원장 전 시각과 ±45일
PLACEBO_M = 8                       # 개체당 위약 t0
SEED_MAIN, SEED_TWIN = 1027, 2027
B_REP = 1000                        # 위약 복제·붓스트랩
ALPHA, M_TYPES = 0.05, 6            # 조항 79 Bonferroni
AIM = 0.2231                        # 겨냥 효과 (log1p · ×1.25)
SRC1018 = "ebb1f7e320dd456d"        # placebo_seed1018.json sha16 (등록 출처)
JUDGED = ["출시", "개최", "시작", "발표", "공개", "개봉"]
OBSERVED = ["방영", "데뷔", "컴백"]
EV_SHA16 = "649a2c88664a5aba"
MV_SHA16 = "d01475447ac24e29"
STAMP_EXO = ("조건부 연관 — 인과 아님. 사건은 무작위 배정이 아니고, 같은 개체의 인접 사건·"
             "계절·담론이 혼입될 수 있다. '~가 ~를 올렸다' 화법 금지.")
STAMP_IVT = ("개입(팝업개최) [관찰] — 형상만. 반사실 띠는 1018 몫: 시장팝업·팝업 공여 풀 0"
             "(1018 §9 −85건) · 개별 효과 MDE 0.977 미달.")
STAMP_COMP = "사건 등가중 평균 — 다사건 개체가 무겁다(원장 구성 조건부)."

D_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def log(**kw):
    kw["시각"] = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with open(OUT, "a") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_ord(s):
    m = D_RE.match(s or "")
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).toordinal()
    except ValueError:
        return None


def load_gate():
    while os.getloadavg()[0] > 10:
        log(단계="load관문", load1=os.getloadavg()[0], 대기초=60)
        time.sleep(60)


# ── v5.3-2 방향 탐침 (측정 «전» · 합성 t>0) ──────────────────────────────────

def gate_g1(peak, q):
    """G1: Δ=peak−q — Δ>0 통과. 악화 방향 −(피크가 위약 보정 분위 이하 = 소음과 못 가름)."""
    return (peak - q) > 0.0


def gate_g0(med, thr):
    """G0 0-중심(양쪽): |med| ≤ thr 통과. 위반 = 설계 결함."""
    return abs(med) <= thr


def direction_probe():
    t = 0.1
    ok = (gate_g1(0.0 + (-2 * t) + t, t) is False and gate_g1(t + 2 * t, t) is True and
          gate_g0(+2 * t, t) is False and gate_g0(-2 * t, t) is False and
          gate_g0(0.0, t) is True)
    if not ok:
        log(단계="방향탐침", 판정="결함 — 측정 없이 중단")
        raise SystemExit("방향 탐침 결함")
    log(단계="방향탐침", 판정="통과", 합성t=t)


# ── 부칙 6 ㉰ 시작 관문 — 등록문 MDE 칸 파싱 + 출처 sha 실물 대조 ─────────────

def mde_start_gate():
    src = "/Users/ax/wm_harvest/foundation/l3_counterfactual/placebo_seed1018.json"
    real = sha256_file(src)[:16]
    if real != SRC1018:
        raise SystemExit("MDE 출처 sha 불일치: %s ≠ %s" % (real, SRC1018))
    with open(DOC) as f:
        doc = f.read()
    if SRC1018 not in doc or ("%.4f" % AIM) not in doc:
        raise SystemExit("등록문에 MDE 출처 sha 또는 겨냥 칸 부재")
    rows = re.findall(r"^\s*\|\s*(\S+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", doc, re.M)
    reg = {r[0]: (int(r[1]), float(r[2]), float(r[3])) for r in rows}
    stamps = {}
    for g in JUDGED:
        if g not in reg:
            raise SystemExit("등록문 MDE 표에 유형 부재: %s" % g)
        n_ent, mde_reg, aim_reg = reg[g]
        recompute = mde_of(0.4885 / math.sqrt(n_ent), 0.0228)
        if abs(recompute - mde_reg) > 5e-4 or abs(aim_reg - AIM) > 1e-9:
            raise SystemExit("등록 MDE 산식 불일치 %s: %r vs %r" % (g, mde_reg, recompute))
        stamps[g] = assert_mde(mde_reg, AIM, SRC1018)   # 어긋나면 예외 → 측정 없이 중단
    for g in OBSERVED:
        if g not in reg:
            raise SystemExit("등록문 관찰 강등 표에 유형 부재: %s" % g)
    log(단계="MDE시작관문", 판정="통과", 유형수=len(stamps))
    return stamps


# ── 자기시험 — 합성 패널에서 잔차 추출이 기대대로인가 ────────────────────────

def selftest():
    o0 = dt.date(2020, 1, 1).toordinal()
    vals = np.full(200, 100.0)
    t0 = o0 + 100
    vals[100] = 100.0 * math.e  # d0 에 ×e 스파이크 (조회 원눈금)
    curve, base_used, nb, nw = extract_curve(vals, o0, t0)
    exp0 = math.log1p(100 * math.e) - math.log1p(100)
    ok = (curve is not None and abs(curve[0 - WIN_LO] - exp0) < 1e-9 and
          abs(curve[-1]) < 1e-12 and nb == 30 and nw == 91 and
          base_used == t0 - 8)
    if not ok:
        raise SystemExit("자기시험 결함 — 잔차 추출")
    log(단계="자기시험", 판정="통과", d0잔차=round(curve[0 - WIN_LO], 6))


# ── 곡선 추출 ────────────────────────────────────────────────────────────────

def extract_curve(vals, o0, t0):
    """vals: 개체의 일별 조회 (o0 기준 · NaN=결측). 반환: (91칸 잔차, 기준선 실사용 최대 ordinal, n_base, n_win)."""
    n = len(vals)
    bi0, bi1 = t0 + BASE_LO - o0, t0 + BASE_HI - o0
    wi0, wi1 = t0 + WIN_LO - o0, t0 + WIN_HI - o0
    if bi0 < 0 or wi1 >= n:
        return None, None, 0, 0
    base = vals[bi0:bi1 + 1]
    win = vals[wi0:wi1 + 1]
    nb = int(np.sum(~np.isnan(base)))
    nw = int(np.sum(~np.isnan(win)))
    if nb < BASE_MIN or nw < WIN_MIN:
        return None, None, nb, nw
    lbase = np.log1p(base)
    mu = float(np.nanmean(lbase))
    curve = np.log1p(win) - mu
    idx = np.where(~np.isnan(base))[0]
    base_used = t0 + BASE_LO + int(idx[-1])
    return curve, base_used, nb, nw


def peak_of(curve):
    a = np.abs(np.where(np.isnan(curve), -np.inf, curve))
    i = int(np.argmax(a))          # 동률 시 이른 날
    return i + WIN_LO, float(curve[i])


def halflife_of(curve, pd_, pv):
    if not np.isfinite(pv) or pv == 0:
        return None
    half = abs(pv) / 2.0
    for tau in range(1, WIN_HI - pd_ + 1):
        v = curve[pd_ + tau - WIN_LO]
        if np.isfinite(v) and abs(v) <= half:
            return tau
    return ">창끝"


def mean_curve(S, C):
    """S: 곡선 합(일별) · C: 곡선 수(일별) → 평균 (0 나눗셈 → NaN)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(C > 0, S / np.where(C > 0, C, 1), np.nan)


def agg(curves):
    A = np.array(curves)
    M = ~np.isnan(A)
    return np.where(M, A, 0.0).sum(axis=0), M.sum(axis=0)


def main():
    t_start = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    my_sha = sha256_file(os.path.abspath(__file__))
    if os.path.exists(OUT):
        os.rename(OUT, OUT + ".prev." + str(int(time.time())))
    log(단계="시작", 러너sha256=my_sha, 시각0=t_start, load1=os.getloadavg()[0])
    load_gate()
    direction_probe()
    mde_start_stamps = mde_start_gate()
    selftest()

    # 원장 sha 대조 (조항 66)
    ev_sha = sha256_file(os.path.join(LEDGER, "events.jsonl.gz"))
    mv_sha = sha256_file(os.path.join(LEDGER, "merged_view.jsonl.gz"))
    if ev_sha[:16] != EV_SHA16 or mv_sha[:16] != MV_SHA16:
        raise SystemExit("원장 sha 불일치 — 등록과 다른 원장이다")

    # wiki_daily 사본 격리 (살아있는 파일 절연)
    os.makedirs(SNAPDIR, exist_ok=True)
    import glob
    snap_shas = {}
    for src in sorted(glob.glob("/Users/ax/world_model/data/ingest/wiki_daily/*.jsonl.gz")):
        dst = os.path.join(SNAPDIR, os.path.basename(src))
        shutil.copy2(src, dst)
        snap_shas[os.path.basename(src)] = sha256_file(dst)[:16]
    log(단계="패널사본", 파일수=len(snap_shas))

    # ── 패널 적재 (ko 우선 · 한 개체 한 곡선) ──
    panel = {}      # 키 -> (o0, vals np.array, 문서, 언어, 도메인)
    doc2key = {}
    for f in sorted(glob.glob(os.path.join(SNAPDIR, "*.jsonl.gz"))):
        dom = os.path.basename(f).split(".")[0]
        with gzip.open(f, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                k, lang = r["키"], r.get("언어")
                if k in panel and (panel[k][3] == "ko" or lang != "ko"):
                    continue
                ords, vs = [], []
                for x, v in zip(r["날짜"], r["조회수"]):
                    try:
                        o = dt.date(x // 10000, (x // 100) % 100, x % 100).toordinal()
                    except ValueError:
                        continue
                    ords.append(o); vs.append(float(v))
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
    log(단계="패널", 개체=len(panel), 문서색인=len(doc2key))

    # ── 원장 적재 + 조인 + 사다리 ──
    rows = []                      # (사건id, 패널키, t0, pub_ord, 유형, 신뢰층, 개입?)
    ev_by_ent = {}                 # 패널키 -> [전 원장 ordinal] (±45 규칙용 · 사건+개입)
    lad = {"사건": {"0_원장": 0, "1_일단위시각": 0, "2_곡선가용": 0, "3_창완비": 0},
           "개입": {"0_원장": 0, "1_일단위시각": 0, "2_곡선가용": 0, "3_창완비": 0}}
    lad_tc = {}                    # (유형|신뢰층) -> {2_곡선가용, 3_창완비}
    with gzip.open(os.path.join(LEDGER, "merged_view.jsonl.gz"), "rt") as fh:
        for line in fh:
            r = json.loads(line)
            ivt = r.get("원장구분") == "개입"
            side = "개입" if ivt else "사건"
            lad[side]["0_원장"] += 1
            t0 = to_ord(r.get("event_time"))
            if t0 is None:
                continue
            lad[side]["1_일단위시각"] += 1
            k, d = r.get("개체키"), r.get("위키문서")
            pk = k if k in panel else (doc2key.get(d) if (d and not ivt) else None)
            if ivt and k not in panel:
                pk = None
            if pk is None:
                continue
            lad[side]["2_곡선가용"] += 1
            g = "개입:팝업개최" if ivt else r.get("정규유형")
            key = "%s|%s" % (g, r.get("신뢰층"))
            lad_tc.setdefault(key, {"2_곡선가용": 0, "3_창완비": 0})["2_곡선가용"] += 1
            rows.append((r.get("사건id"), pk, t0, to_ord(r.get("최초pub_time") or ""), g,
                         r.get("신뢰층"), ivt))
            ev_by_ent.setdefault(pk, []).append(t0)
    log(단계="조인", 행=len(rows), 사다리=lad)

    # ── 실제 곡선 추출 (event_time 정렬) + leak 스탬프 ──
    curves = {}                    # 유형 -> {개체 -> [곡선,...]}
    leak_n, leak_margin_min = 0, None
    for eid, pk, t0, pub, g, tier, ivt in rows:
        o0, vals = panel[pk][0], panel[pk][1]
        c, base_used, nb, nw = extract_curve(vals, o0, t0)
        if c is None:
            continue
        st = assert_no_leak([{"id": eid, "published_at": dt.date.fromordinal(base_used)}],
                            dt.date.fromordinal(t0), tag="1027 기준선/" + g)
        leak_n += 1
        m = st["여유일"]
        leak_margin_min = m if leak_margin_min is None else min(leak_margin_min, m)
        side = "개입" if ivt else "사건"
        lad[side]["3_창완비"] += 1
        lad_tc["%s|%s" % (g, tier)]["3_창완비"] += 1
        curves.setdefault(g, {}).setdefault(pk, []).append(c)
    log(단계="곡선", leak스탬프=leak_n, 최소여유일=leak_margin_min,
        유형수=len(curves), 사다리=lad)

    # ── 이중 정렬 관찰 (최초pub_time) ──
    pub_curves, pub_lad = {}, {}
    for eid, pk, t0, pub, g, tier, ivt in rows:
        if ivt or pub is None:
            continue
        pub_lad.setdefault(g, {"pub시각": 0, "창완비": 0})["pub시각"] += 1
        c, base_used, nb, nw = extract_curve(panel[pk][1], panel[pk][0], pub)
        if c is None:
            continue
        assert_no_leak([{"id": eid, "published_at": dt.date.fromordinal(base_used)}],
                       dt.date.fromordinal(pub), tag="1027 pub기준선/" + g)
        pub_lad[g]["창완비"] += 1
        pub_curves.setdefault(g, []).append(c)

    # ── 위약 적격일 (개체별 · 벡터화) ──
    load_gate()
    elig = {}
    for pk, (o0, vals, _d, _l, _dom) in panel.items():
        pres = (~np.isnan(vals)).astype(np.int32)
        cs = np.concatenate([[0], np.cumsum(pres)])
        n = len(vals)
        lo, hi = o0 + 37, o0 + n - 1 - 60
        if hi < lo:
            elig[pk] = np.array([], dtype=np.int64); continue
        t = np.arange(lo, hi + 1)
        i = t - o0
        nb = cs[i + BASE_HI + 1] - cs[i + BASE_LO]
        nw = cs[i + WIN_HI + 1] - cs[i + WIN_LO]
        ok = (nb >= BASE_MIN) & (nw >= WIN_MIN)
        for e in set(ev_by_ent.get(pk, [])):
            ok &= np.abs(t - e) >= PLACEBO_DIST
        elig[pk] = t[ok]
    log(단계="위약적격", 적격개체=sum(1 for v in elig.values() if len(v)),
        적격일합=int(sum(len(v) for v in elig.values())))

    # ── 위약 곡선 (씨앗별 개체당 M=8) ──
    def placebo_curves(seed):
        rng = np.random.default_rng(seed)
        out = {}
        for pk in sorted(panel):
            days = elig[pk]
            if len(days) == 0:
                continue
            pick = rng.choice(days, size=min(PLACEBO_M, len(days)), replace=False)
            cs_ = []
            for t0 in sorted(int(x) for x in pick):
                c, base_used, nb, nw = extract_curve(panel[pk][1], panel[pk][0], t0)
                if c is None:
                    continue      # 적격 계산과 동치라 원리상 없음 — 있으면 계수
                assert_no_leak([{"id": "%s@%d" % (pk, t0),
                                 "published_at": dt.date.fromordinal(base_used)}],
                               dt.date.fromordinal(t0), tag="1027 위약기준선")
                cs_.append(c)
            if cs_:
                out[pk] = np.array(cs_)
        return out
    plc = {SEED_MAIN: placebo_curves(SEED_MAIN), SEED_TWIN: placebo_curves(SEED_TWIN)}
    log(단계="위약곡선", 씨앗1027개체=len(plc[SEED_MAIN]), 씨앗2027개체=len(plc[SEED_TWIN]),
        곡선합1027=int(sum(len(v) for v in plc[SEED_MAIN].values())))

    # ── 유형별 통계 ──
    load_gate()
    all_types = sorted(curves.keys())
    q_idx = math.ceil(B_REP * (1 - ALPHA / M_TYPES)) - 1     # 992번째 (0기반 991)
    library, placebo_out = {}, {SEED_MAIN: {}, SEED_TWIN: {}}
    probe_cnt = {"악화참": 0, "개선거짓": 0, "퇴화문턱": 0}
    for g in all_types:
        ents = sorted(curves[g])
        w = np.array([len(curves[g][pk]) for pk in ents], dtype=float)
        n_ev, n_ent = int(w.sum()), len(ents)
        # 실제 평균 곡선 (사건 등가중)
        S_all, C_all = agg([c for pk in ents for c in curves[g][pk]])
        mc = mean_curve(S_all, C_all)
        pd_, pv = peak_of(mc)
        hl = halflife_of(mc, pd_, pv)
        # 클러스터 붓스트랩 띠
        Sc = np.array([agg(curves[g][pk])[0] for pk in ents])
        Cc = np.array([agg(curves[g][pk])[1] for pk in ents], dtype=float)
        rng = np.random.default_rng(SEED_MAIN)
        boots = np.empty((B_REP, WIN_HI - WIN_LO + 1))
        for b in range(B_REP):
            idx = rng.integers(0, n_ent, n_ent)
            boots[b] = mean_curve(Sc[idx].sum(axis=0), Cc[idx].sum(axis=0))
        band_lo = np.nanpercentile(boots, 2.5, axis=0)
        band_hi = np.nanpercentile(boots, 97.5, axis=0)
        # 위약 복제 (씨앗별)
        stats = {}
        for seed in (SEED_MAIN, SEED_TWIN):
            pool = plc[seed]
            have = [pk for pk in ents if pk in pool]
            cover_ev = float(w[[ents.index(pk) for pk in have]].sum() / w.sum()) if n_ev else 0.0
            P = np.full((len(have), PLACEBO_M, WIN_HI - WIN_LO + 1), np.nan)
            cnts = np.zeros(len(have), dtype=np.int64)
            for i, pk in enumerate(have):
                a = pool[pk]
                P[i, :len(a)] = a
                cnts[i] = len(a)
            ww = np.array([w[ents.index(pk)] for pk in have], dtype=float)
            rng2 = np.random.default_rng(seed)
            peaks = np.empty(B_REP)
            for b in range(B_REP):
                ks = rng2.integers(0, cnts)
                sel = P[np.arange(len(have)), ks]
                mask = ~np.isnan(sel)
                num = (np.where(mask, sel, 0.0) * ww[:, None]).sum(axis=0)
                den = (mask * ww[:, None]).sum(axis=0)
                curve_b = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
                _pd, _pv = peak_of(curve_b)
                peaks[b] = abs(_pv)
            # 0-중심: 개별 위약 곡선의 후창 [0,+60] 평균
            post = []
            for i in range(len(have)):
                for j in range(cnts[i]):
                    post.append(float(np.nanmean(P[i, j, -WIN_LO:])))
            post = np.array(post)
            stats[seed] = {"peaks": peaks, "post": post, "cover_ev": cover_ev,
                           "N_pool": int(cnts.sum())}
            placebo_out[seed][g] = {
                "위약풀_개체": len(have), "위약풀_곡선": int(cnts.sum()),
                "사건가중_커버": round(cover_ev, 4),
                "피크분포": {"평균": round(float(peaks.mean()), 5),
                             "SD": round(float(peaks.std(ddof=1)), 5),
                             "q50": round(float(np.quantile(peaks, .5)), 5),
                             "q95": round(float(np.quantile(peaks, .95)), 5),
                             "q_corr(1-0.05/6)": round(float(np.sort(peaks)[q_idx]), 5)},
                "후창평균": {"중앙값": round(float(np.median(post)), 5),
                             "SD": round(float(post.std(ddof=1)), 5), "N": len(post)}}
        pk1 = stats[SEED_MAIN]["peaks"]
        sd1, sd2 = float(pk1.std(ddof=1)), float(stats[SEED_TWIN]["peaks"].std(ddof=1))
        J = abs(sd1 - sd2) / math.sqrt(2)
        q_corr = float(np.sort(pk1)[q_idx])
        post1 = stats[SEED_MAIN]["post"]
        med = float(np.median(post1))
        se_med = 1.2533 * float(post1.std(ddof=1)) / math.sqrt(len(post1))
        zero_ok = gate_g0(med, 2 * se_med)
        # 판정 (사전 고정 사슬)
        is_j = g in JUDGED
        peak_abs = abs(pv)
        verdicts, mde_stamp = [], None
        if stats[SEED_MAIN]["N_pool"] < 50:
            verdict = "미판정(위약 부족)"
        elif stats[SEED_MAIN]["cover_ev"] < 0.8:
            verdict = "미판정(위약 대표성)"
        elif not zero_ok:
            verdict = "미판정(설계 결함 — 위약 비중심)"
        elif q_corr <= 0:
            verdict = "미판정(퇴화 문턱)"; probe_cnt["퇴화문턱"] += 1
        else:
            mde_real = mde_of(max(sd1, 1e-12), J)
            plc_sha = None  # 파일 sha 는 아래에서 기입 (파일 저장 후 재호출)
            if not is_j:
                verdict = "관찰(사전 강등)" if g in OBSERVED else "관찰(개입 병기)"
            else:
                # 실효 검출한계
                if q_corr > AIM:
                    verdict = "관찰(실효 검출한계 겨냥 초과)"
                else:
                    verdict = "판정대기"   # MDE 실측 관문 후 확정 (아래)
            verdicts = [("G1", peak_abs - q_corr)]
            mde_stamp = {"MDE실측": round(mde_real, 5), "SD1027": round(sd1, 5),
                         "SD2027": round(sd2, 5), "J": round(J, 5)}
        # 자료 탐침 (실측 문턱)
        if q_corr > 0:
            if gate_g1(q_corr + (-2 * q_corr), q_corr):
                probe_cnt["악화참"] += 1
            if not gate_g1(q_corr + (+2 * q_corr), q_corr):
                probe_cnt["개선거짓"] += 1
        if 2 * se_med > 0:
            if gate_g0(2 * (2 * se_med), 2 * se_med) or gate_g0(-2 * (2 * se_med), 2 * se_med):
                probe_cnt["악화참"] += 1
            if not gate_g0(0.0, 2 * se_med):
                probe_cnt["개선거짓"] += 1
        library[g] = {
            "레인": "판정" if is_j else "관찰",
            "n_사건": n_ev, "n_개체": n_ent,
            "평균곡선": [None if not np.isfinite(x) else round(float(x), 4) for x in mc],
            "띠_q2.5": [None if not np.isfinite(x) else round(float(x), 4) for x in band_lo],
            "띠_q97.5": [None if not np.isfinite(x) else round(float(x), 4) for x in band_hi],
            "창": [WIN_LO, WIN_HI],
            "피크": {"일": pd_, "크기": round(pv, 5), "절대": round(peak_abs, 5)},
            "반감기": hl,
            "위약": {"q_corr": round(q_corr, 5), "여유(Δ=피크절대-q_corr)": round(peak_abs - q_corr, 5),
                     "0중심": {"med": round(med, 5), "2SE_med": round(2 * se_med, 5),
                               "통과": bool(zero_ok)}},
            "MDE": mde_stamp, "판정": verdict,
            "낙인": [STAMP_IVT if g.startswith("개입") else STAMP_EXO, STAMP_COMP],
        }
        log(단계="유형", 유형=g, n=n_ev, 개체=n_ent, 피크일=pd_, 피크=round(pv, 4),
            q_corr=round(q_corr, 4), 판정=verdict)

    # pub 정렬 곡선 게재 (관찰)
    pub_out = {}
    for g, cs_ in sorted(pub_curves.items()):
        S, C = agg(cs_)
        mc = mean_curve(S, C)
        pd_, pv = peak_of(mc)
        pub_out[g] = {"n_창완비": pub_lad[g]["창완비"], "n_pub시각": pub_lad[g]["pub시각"],
                      "평균곡선": [None if not np.isfinite(x) else round(float(x), 4) for x in mc],
                      "피크": {"일": pd_, "크기": round(pv, 5)}, "낙인": [STAMP_EXO, "pub_time 정렬 — 발표 담론 개시 근사 · 관찰"]}

    # ── 위약 파일 저장 → sha → MDE 실측 관문 → 판정 확정 ──
    for seed, name in ((SEED_MAIN, "placebo_seed1027.json"), (SEED_TWIN, "placebo_seed2027.json")):
        with open(os.path.join(OUTDIR, name), "w") as f:
            json.dump({"씨앗": seed, "개체당M": PLACEBO_M, "거리규칙": PLACEBO_DIST,
                       "B": B_REP, "유형별": placebo_out[seed]}, f, ensure_ascii=False, indent=1)
    plc_sha = sha256_file(os.path.join(OUTDIR, "placebo_seed1027.json"))[:16]
    for g in all_types:
        e = library[g]
        if e["판정"] != "판정대기":
            continue
        try:
            st = assert_mde(e["MDE"]["MDE실측"], AIM, plc_sha)
            e["MDE"]["관문"] = st
            e["판정"] = "유의(위약 보정 분위 밖)" if e["위약"]["여유(Δ=피크절대-q_corr)"] > 0 \
                else "MDE(%.4f) 미만" % e["MDE"]["MDE실측"]
        except MdeUnderpowered as ex:
            e["MDE"]["관문"] = "MdeUnderpowered: %s" % ex
            e["판정"] = "관찰 강등 — MDE(%.4f) 미만 화법" % e["MDE"]["MDE실측"]
        log(단계="판정", 유형=g, 판정=e["판정"])

    with open(os.path.join(OUTDIR, "library_v0.json"), "w") as f:
        json.dump({"판": "사건 반응 함수 도서관 v0", "사전등록": "docs/탐색/1027.md",
                   "정렬": "event_time", "눈금": "log1p 잔차(기준선 t0-37..t0-8)",
                   "유형별": library, "pub정렬_관찰": pub_out}, f, ensure_ascii=False, indent=1)

    t_end = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    my_sha2 = sha256_file(os.path.abspath(__file__))
    meta = {"러너sha256": my_sha, "러너sha_전후일치": my_sha == my_sha2,
            "시작": t_start, "끝": t_end,
            "입력sha16": {"events.jsonl.gz": ev_sha[:16], "merged_view.jsonl.gz": mv_sha[:16],
                          "placebo_seed1018.json": SRC1018, "wiki_daily사본": snap_shas},
            "분모사다리": lad, "유형x신뢰층": lad_tc, "pub정렬사다리": pub_lad,
            "leak스탬프": {"n": leak_n, "최소여유일": leak_margin_min},
            "자료탐침(㉰악화참·㉱개선거짓)": probe_cnt,
            "MDE시작관문": {g: s for g, s in mde_start_stamps.items()},
            "상수": {"창": [WIN_LO, WIN_HI], "기준선": [BASE_LO, BASE_HI],
                     "완비": [BASE_MIN, WIN_MIN], "위약거리": PLACEBO_DIST, "M": PLACEBO_M,
                     "B": B_REP, "겨냥": AIM, "Bonferroni_m": M_TYPES, "씨앗": [SEED_MAIN, SEED_TWIN]}}
    with open(os.path.join(OUTDIR, "meta1027.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    log(단계="완료", 끝=t_end, 러너sha_전후일치=my_sha == my_sha2)
    print(json.dumps({"완료": True, "사다리": lad, "탐침": probe_cnt}, ensure_ascii=False))


if __name__ == "__main__":
    main()
