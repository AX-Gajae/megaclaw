#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""996 공용 — 🔴🔴 **「정보장」 `Z_t` 을 챔피언 세계에 넣는 배관과 등록된 자.**

🔴 이 파일은 «측정하지 않는다». 자료를 열고, `Z_t` 를 짓고, 축을 덧붙이고,
등록된 자(군집 SE · 순열 · Holm)를 두고, 조항 78 ㉮·㉯ 를 «기계로» 세는
함수만 둔다. 판정은 네 러너가 각자 자기 산출물에 낸다.

🔴🔴🔴 **동결**: `runners/beta994_*.py` · `runners/gamma995_*.py` 는 한 글자도 안 고친다.
   `gamma995_masks.py`(F01 수리 마스크)를 **읽기로만** 쓴다.

## 🔴 이 사이클이 여는 물음

`docs/prereg_996_information_field.md` §0 을 보라. 한 줄로:
**「축의 «계수»가 시대에 따라 도는가 · 어느 축이 · 그것이 995 의 낙차를 얼마나 설명하나 ·
그리고 «그때 세상이 어땠나»(`Z_t`)를 넣으면 틈이 닫히나」.**

🔴 **구조적 제약**: 판 ρ 는 스피어만이라 «블록 안 순위»만 본다.
`Z_t` 가 블록 안에서 «상수»면 그 주효과는 순위를 **원리상** 못 바꾼다.
그래서 위약 둘을 «다» 잰다 — 블록 상수 주효과(항등식이어야 한다)와
행별 주효과(상호작용이 이겨야 하는 대조).
"""
import collections
import datetime as dt
import glob
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import beta994_common as B94                      # noqa: E402  🔴 동결 · 읽기로만
import gamma995_masks as MK                       # noqa: E402  🔴 동결 · F01 수리판
from lab.harness import Data                      # noqa: E402

# ── 사전등록 상수 (측정 전에 박았다) ──────────────────────────────────
NOTE = 996
SEEDS = tuple(range(12))          #: `ff753.RULER_SEEDS` — 정본 12 씨앗
T_CANON = 2025.0
NBLOCK = 5
QS = (0.2, 0.4, 0.6, 0.8)
ORIGINS = (1, 2, 3, 4)
GATES = (20, 10, 5, 3)            #: 조항 66 — 문턱 대신 검사를 인자화한다
GATE_CANON = 20
ALL5 = ("target_breadth", "venue_prominence", "entry_friction",
        "media_push", "goods_scale")

#: 🔴 등록된 자 — `score994.py:98 cluster_se` 와 «같은 꼴»(995 팔 C 가 쓴 것)
B_DOM = 2000
DOM_SEED = 994
#: 🔴 순열 자 — 996 이 «신설»한다. 씨앗을 여기 박는다
PERM_B = 2000
PERM_SEED = 996
HOLM_ALPHA = 0.05

#: 🔴 995 가 낸 수 — **참고 상수**다. 이 사이클은 이것을 «다시» 잰다
#: 🔴 열쇠 이름은 `seg_from` 이 만드는 «그 이름 그대로»여야 한다 --- 설계 팔의
#:   연기 시험이 「이름이 안 맞아 차가 −G995 로 찍히는」 것을 잡았다(비맹검 신고 S-9).
G995 = collections.OrderedDict([
    ("원점 1→원점 2", 0.074859), ("원점 2→원점 3", 0.048355),
    ("원점 3→원점 4", 0.060167), ("원점 1→원점 4", 0.183381)])
G995_SE = collections.OrderedDict([
    ("원점 1→원점 2", 0.0343719), ("원점 2→원점 3", 0.0168548),
    ("원점 3→원점 4", 0.0260194), ("원점 1→원점 4", 0.0503352)])
GAP995 = 0.183381                 #: 🔴 낙차 합 — **「학습량 몫이 섞인」 분모**다(티처 #134)
#: 🔴🔴🔴 티처 #134 실측 — `out994_ctl.json` `C3`(유보·시대 그대로 · 학습 행만
#:   19,018 → 4,556): ρ `0.470997 → 0.417725`. **`C0 − C3 = 0.053272`**
#:   ⇒ `0.183381` 의 **29.0 %**(단순 차) · **28.2 %**(log 기울기)가
#:   **정보장과 아무 상관 없는 「학습 행 수」**다.
C0_MINUS_C3 = 0.053272
LEARN_SHARE = 0.290                #: 0.053272 / 0.183381
RESID_EXPECT = 0.130               #: 🔴 예측 — 팔 0 의 잔여 낙차가 여기 근처면 29 % 가 맞다
#: 🔴 원점 지표와 학습 행의 상관 = **1.000000** ⇒ **거리와 학습량은 «완전 공선»이다.**
#:   어떤 자를 써도 관찰만으로는 못 가른다 --- **잘라서 «맞추는» 수밖에 없다**(팔 0).
TRAIN_ROWS_995 = (4556, 9116, 13671, 18225)   #: 🔴 원점별 학습 행(995 실측)
TRAIN_DOMS_995 = (7, 9, 9, 11)                #: 🔴 원점별 학습 도메인(995 실측)
BOARD_RHO_FULL = B94.BOARD_RHO_FULL
F01_DEV = MK.F01_DEV              #: 7.199316e-04
SAFE_MULT = MK.SAFE_MULT          #: 20

#: 🔴 `Z_t` 원천 — **위키 일별**. `data/ingest/wiki_daily959/*.jsonl.gz`
WIKI_DIR = ROOT / "data" / "ingest" / "wiki_daily959"
Z_MA = 30                         #: 이동평균 창(일)
#: 🔴🔴 **정직한 한계 — 측정 전에 등기한다.** 위키 pageviews 는 2015-07-01 에 시작한다.
#:   챔피언 블록 0 은 `yr < 2015.010794` 라 **덮이는 날이 0 일**이다.
Z_FIRST_DAY = 20150701
SRC = ("runners/delta996_common.py", "runners/delta996_coef.py",
       "runners/delta996_gap.py", "runners/delta996_zt.py",
       "runners/delta996_match.py", "runners/gamma995_masks.py",
       "runners/beta994_common.py", "runners/ff753.py",
       "lab/harness.py", "lab/forms.py", "lab/loop.py", "state/rank_test.py")
THREADS = collections.OrderedDict([
    (k, os.environ.get(k)) for k in
    ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")])


# ══════════════════════════════════════════════════════════════════════
# 도장 (규칙 C · 조항 66·67) — 🔴 `git` 을 한 번도 안 부른다
# ══════════════════════════════════════════════════════════════════════
def now_utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def sha_file(rel):
    p = rel if isinstance(rel, Path) else (ROOT / rel)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(str(p), "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def code_stamp():
    return collections.OrderedDict([(r, sha_file(r)) for r in SRC])


def stamp(t0, cs0, extra=None):
    cs1 = code_stamp()
    out = collections.OrderedDict([
        ("언제(시작 · UTC)", t0), ("언제(끝 · UTC)", now_utc()),
        ("🔴 코드 sha256(시작)", cs0), ("🔴 코드 sha256(끝)", cs1),
        ("🔴 시작=끝", bool(cs0 == cs1)),
        ("분모: 도장이 덮는 소스", len(cs1)),
        ("🔴 소스 sha 결측", [k for k, v in cs1.items() if v is None]),
        ("🔴 고정한 스레드", THREADS),
        ("🔴 git HEAD 스탬프", "폐기됐다 --- 긴 러너에선 「시작 시점」이라 뜻이 없다"),
    ])
    if extra:
        out.update(extra)
    return out


def prog_writer(path):
    def prog(msg):
        with open(str(path), "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (now_utc(), msg))
    return prog


# ══════════════════════════════════════════════════════════════════════
# 🔴 등록된 자 ① — 도메인 «군집» SE (995 팔 C 와 «글자 그대로 같은 꼴»)
# ══════════════════════════════════════════════════════════════════════
#: 🔴🔴 **조항 79 개정 2 (v4.15)** — 「한 사이클이 낸 `cluster_se` 칸 «전량»을 분모로 신고한다」.
#:   995 는 40 칸을 내고 25 칸이 넘었는데 **그 수가 어디에도 없었다.** 여기서 «자동으로» 센다.
_CSE_LOG = []


def cse_ledger():
    """🔴 이 주행이 낸 `cluster_se` 칸 «전량» 과 그중 2·SE 를 넘은 수."""
    n = len(_CSE_LOG)
    hit = int(sum(1 for x in _CSE_LOG if x is True))
    non = int(sum(1 for x in _CSE_LOG if x is False))
    nul = int(sum(1 for x in _CSE_LOG if x is None))
    return collections.OrderedDict([
        ("🔴 왜 이 칸이 있나", "조항 79 개정 2 --- 쪼개면 다중비교가 생긴다. "
                          "「넘은 칸」만 세고 「낸 칸 전량」을 안 세면 분모가 사라진다."),
        ("🔴🔴 분모: 이 주행이 낸 cluster_se 칸 전량", n),
        ("🔴 2·SE 를 넘은 칸", hit), ("안 넘은 칸", non),
        ("🔴 판정 불가 칸(SD=0 ⇒ SE=0 ⇒ None · ㉯-2)", nul),
        ("넘은 비율", _r(hit / n, 4) if n else None),
        ("🔴 주의", "이 수는 «변이체 격자»와 «사다리»가 낸 칸까지 «전부» 센다. "
                  "헤드라인 조각만 세는 수가 아니다 --- 그래서 분모다.")])


def cluster_se(vals, B=B_DOM, seed=DOM_SEED):
    """`vals` = {도메인: 값}. 등가중 평균의 군집 SE 를 뽑기로 낸다."""
    ds = sorted(vals)
    r = np.asarray([vals[d] for d in ds], float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return collections.OrderedDict([("도메인 수", int(len(r))),
                                        ("도메인 군집 SE", None), ("뽑기 수", 0)])
    rng = np.random.RandomState(int(seed))
    bs = np.empty(int(B))
    for b in range(int(B)):
        bs[b] = r[rng.randint(0, len(r), len(r))].mean()
    pt, se = float(r.mean()), float(bs.std(ddof=1))
    t = (pt / se) if se else None
    return collections.OrderedDict([
        ("도메인 수", int(len(r))), ("뽑기 수", int(B)),
        ("🔴 자", "score994.py:98 cluster_se · B=%d · RandomState(%d) · 등가중"
         % (B, seed)),
        ("점추정", _r(pt)), ("도메인 군집 SE", _r(se, 8)),
        ("t_clu", _r(t)),
        ("🔴🔴 2·SE 를 넘나", _cse_note(bool(abs(pt) > 2 * se) if se else None)),
        ("🔴 양측 p(정규 근사)", _r(two_sided_p(t), 8) if t is not None else None),
        ("🔴 동부호 수", "%d/%d"
         % (int(sum(1 for x in r if np.sign(x) == np.sign(pt))), len(r))),
        ("동부호 분자", int(sum(1 for x in r if np.sign(x) == np.sign(pt)))),
        ("동부호 분모", int(len(r))),
        ("2.5%", _r(float(np.percentile(bs, 2.5)))),
        ("97.5%", _r(float(np.percentile(bs, 97.5)))),
        ("도메인 사이 SD(τ̂)", _r(float(r.std(ddof=1)))),
    ])


def _cse_note(v):
    _CSE_LOG.append(v)
    return v


def two_sided_p(t):
    """정규 근사 양측 p. 🔴 자유도 보정을 «안» 한다 — 등록된 자는 이것이다."""
    if t is None or not np.isfinite(t):
        return None
    from math import erfc, sqrt
    return float(erfc(abs(float(t)) / sqrt(2.0)))


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴 등록된 자 ② — Holm 보정 (995 가 «안 했던» 것)
# ══════════════════════════════════════════════════════════════════════
def holm(pairs, alpha=HOLM_ALPHA, family=""):
    """`pairs` = [(이름, p), ...]. Holm–Bonferroni 계단 내림.

    🔴 **가족(family)과 그 크기 `m` 을 사전등록에 «먼저» 적는다.**
    995 는 조각 3·6·4 를 쪼개 놓고 보정을 «안 했다» — 반복하지 않는다.
    """
    ok = [(n, float(p)) for n, p in pairs if p is not None and np.isfinite(p)]
    m = len(ok)
    ok.sort(key=lambda x: x[1])
    rows, reject = collections.OrderedDict(), True
    for i, (n, p) in enumerate(ok):
        thr = alpha / (m - i) if m - i > 0 else alpha
        if reject and p > thr:
            reject = False
        rows[n] = collections.OrderedDict([
            ("p", _r(p, 8)), ("계단 문턱 alpha/(m-i)", _r(thr, 8)),
            ("차례 i", i), ("🔴 Holm 통과", bool(reject))])
    miss = [n for n, p in pairs if p is None or not np.isfinite(p)]
    return collections.OrderedDict([
        ("🔴 가족", family), ("분모: 가족 크기 m", m), ("alpha", alpha),
        ("🔴 p 가 결측인 검정", miss),
        ("🔴 Holm 뒤 살아남은 수", int(sum(1 for v in rows.values()
                                     if v["🔴 Holm 통과"]))),
        ("검정별", rows)])


# ══════════════════════════════════════════════════════════════════════
# 조각 분해 (조항 79) — 995 팔 C `seg_from` 과 «같은 꼴»
# ══════════════════════════════════════════════════════════════════════
SIGN_RULE = ("🔴 부호 규약 = 「뒤 − 앞」 = 「가까운 원점 − 먼 원점」 · "
             "양수 = 원점이 «가까울수록» 좋다. "
             "🔴🔴 995 산출물 §C3 의 문구 「먼 원점 − 가까운 원점」은 코드"
             "(`seg_from`: `per_by[b] − per_by[a]`)와 «반대»다 --- 티처 #134 가 잡았다.")


def seg_from(labels, per_by, B=B_DOM, seed=DOM_SEED):
    """이웃 조각 + 합. 🔴 부호 규약은 `SIGN_RULE` 그대로 = 「뒤 − 앞」.

    🔴🔴 **「합」은 조각 셋의 «항등 합»이지 넷째 검사가 아니다**(티처 #134).
    통과 «수»를 셀 때 합을 세지 마라 --- 조항 78 ㉮ 다.
    """
    rows = collections.OrderedDict()
    for i in range(len(labels) - 1):
        a, b = labels[i], labels[i + 1]
        dd = {k: (per_by[b][k] - per_by[a][k]) for k in per_by[a]
              if k in per_by[b]}
        rows["%s→%s" % (a, b)] = cluster_se(dd, B, seed)
    tot = {k: (per_by[labels[-1]][k] - per_by[labels[0]][k])
           for k in per_by[labels[0]] if k in per_by[labels[-1]]}
    rows["%s→%s" % (labels[0], labels[-1])] = cluster_se(tot, B, seed)
    return rows


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 등록된 자 ③ — 부호뒤집기 순열을 «전부 세어» 정확히 낸다 (티처 #134)
# ══════════════════════════════════════════════════════════════════════
def signflip_exact(per_dom, seg_names, max_d=22):
    """도메인마다 조각 벡터를 «통째로» 뒤집는다. `d ≤ max_d` 면 `2^d` 를 전부 센다.

    🔴 **왜 필요한가**(티처 #134): 귀무(추세 0 · 도메인 12 · 995 판정식)에서
    **조각 셋 중 «하나라도» 넘을 확률이 0.2104** 다 --- 「쪼개면 아무거나 하나는
    넘는다」가 다섯 사이클에 한 번 온다. 그래서 **이접(any)이 아니라 연언(k/k)**
    으로 채점하고 그 «정확한» p 를 헤드라인 칸에 넣는다.

    🔴 **도메인 «통째» 뒤집기**라야 조각 사이의 상관이 안 깨진다(짝을 안 깬다).
    🔴 몬테카를로가 아니다 --- `2^d` 를 전부 세므로 씨앗도 뽑기 오차도 «없다».

    `per_dom` = {도메인: [Δ_조각1, Δ_조각2, ...]}.
    """
    ds = sorted(per_dom)
    M = np.asarray([per_dom[d] for d in ds], float)
    ok = np.isfinite(M).all(axis=1)
    M, ds = M[ok], [ds[i] for i in range(len(ds)) if ok[i]]
    d, k = M.shape
    if d < 2:
        return collections.OrderedDict([("🔴 못 쟀다", "도메인이 2 미만이다"),
                                        ("분모: 도메인", int(d))])
    if d > max_d:
        return collections.OrderedDict([("🔴 못 쟀다", "d 가 %d 를 넘어 전수가 안 된다"
                                         % max_d), ("분모: 도메인", int(d))])
    MS = np.column_stack([M, M.sum(axis=1)])            # 마지막 열 = «합»
    kk = MS.shape[1]
    S = np.array([[1.0 if (i >> j) & 1 == 0 else -1.0 for j in range(d)]
                  for i in range(1 << d)])              # (2^d, d) · 첫 줄 = 전부 +1
    #: 🔴 numpy 2.0.2 + macOS Accelerate 가 `matmul` 에서 **거짓 경보**를 낸다
    #:   (`divide by zero` · `overflow` · `invalid`). 값은 멀쩡하다 --- 숨기지 않고
    #:   `einsum` 과 대조해 **최대 |차|를 산출물에 싣는다**(조항 69).
    with np.errstate(all="ignore"):
        tot = S @ MS                                    # (2^d, kk)
        sq = np.ones((1 << d, d)) @ (MS ** 2)
        chk = float(np.abs(tot - np.einsum("ij,jk->ik", S, MS)).max())
    mean = tot / d
    var = (sq - (tot ** 2) / d) / (d - 1)
    sd = np.sqrt(np.maximum(var, 0.0))
    se = sd * np.sqrt((d - 1.0) / d) / np.sqrt(d)       # 뽑기 SE 의 해석 대응물
    hit = np.abs(mean) > 2.0 * se
    seg = hit[:, :k]
    names = list(seg_names) + ["합(항등 · 통과로 안 센다)"]
    return collections.OrderedDict([
        ("🔴 자", "부호뒤집기 «전수» 2^d · 도메인 통째 뒤집기 · 판정식 |평균| > 2·SE(해석)"),
        ("🔴 몬테카를로인가", False), ("분모: 도메인 d", int(d)),
        ("분모: 부호 패턴 2^d", int(1 << d)), ("분모: 조각", int(k)),
        ("도메인", ds), ("조각 이름", names),
        ("관측 평균", [_r(x) for x in mean[0]]),
        ("관측 SE(해석)", [_r(x, 8) for x in se[0]]),
        ("관측 통과", [bool(x) for x in hit[0]]),
        ("🔴🔴 관측 통과 수 / 분모 조각", "%d/%d" % (int(seg[0].sum()), k)),
        ("🔴 p(조각 «하나라도» 넘는다)", _r(float(seg.any(axis=1).mean()), 6)),
        ("🔴🔴 p(조각 «전부» 넘는다 = 연언)", _r(float(seg.all(axis=1).mean()), 6)),
        ("🔴 p(관측만큼 «많이» 넘는다)",
         _r(float((seg.sum(axis=1) >= int(seg[0].sum())).mean()), 6)),
        ("p(합이 넘는다 · 참고 · 항등이라 통과로 안 센다)",
         _r(float(hit[:, k].mean()), 6)),
        ("🔴 티처 #134 의 귀무 실측(참고)",
         {"하나라도": 0.2104, "셋 다": 0.00275, "합": 0.0770}),
        ("🔴 BLAS 거짓 경보 대조(matmul vs einsum 최대 |차|)", chk),
        ("🔴 그 차가 0 인가", bool(chk == 0.0)),
    ])


def se_surrogate_check(vals, B=B_DOM, seed=DOM_SEED, tol=0.05):
    """🔴 `signflip_exact` 가 쓰는 «해석 SE» 가 등록된 «뽑기 SE» 와 맞나.

    안 맞으면 순열 p 를 못 믿는다 --- 반증조건으로 등록한다.
    """
    r = np.asarray([vals[d] for d in sorted(vals)], float)
    r = r[np.isfinite(r)]
    d = len(r)
    if d < 2:
        return collections.OrderedDict([("🔴 못 쟀다", "도메인이 2 미만")])
    an = float(r.std(ddof=1) * np.sqrt((d - 1.0) / d) / np.sqrt(d))
    bo = cluster_se(vals, B, seed)["도메인 군집 SE"]
    rel = abs(an - bo) / bo if bo else None
    return collections.OrderedDict([
        ("해석 SE", _r(an, 8)), ("등록된 뽑기 SE", _r(bo, 8)),
        ("🔴 상대 차", _r(rel, 6)), ("허용", tol),
        ("🔴 통과", bool(rel is not None and rel <= tol))])


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 `Z_t` — 「그때 세상이 어땠나」
# ══════════════════════════════════════════════════════════════════════
def _day_to_yr(d):
    d = int(d)
    return d // 10000 + ((d // 100) % 100 - 1) / 12.0 + (d % 100 - 1) / 365.0


_ZCACHE = {}


def zraw(wdir=WIKI_DIR):
    """🔴 위키 일별 원자료를 «한 번만» 읽는다 — (info, days, yrs, z).

    `z` = log(그날 활성 문서당 평균 조회수). 이동평균은 부르는 쪽이 고른다.
    """
    key = str(wdir)
    if key in _ZCACHE:
        return _ZCACHE[key]
    files = sorted(glob.glob(str(Path(wdir) / "*.jsonl.gz")))
    tot, act = collections.Counter(), collections.Counter()
    shas, nrec = collections.OrderedDict(), 0
    for p in files:
        shas[os.path.basename(p)] = sha_file(Path(p))
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                nrec += 1
                for d, v in zip(r.get("날짜") or [], r.get("조회수") or []):
                    if v is None:
                        continue
                    tot[d] += float(v)
                    act[d] += 1
    days = np.asarray(sorted(tot), dtype=np.int64)
    yrs = np.asarray([_day_to_yr(d) for d in days], float)
    raw = np.asarray([tot[int(d)] / max(act[int(d)], 1) for d in days], float)
    z = np.log(np.maximum(raw, 1e-9))
    info = collections.OrderedDict([
        ("🔴 원천", str(Path(wdir).relative_to(ROOT))),
        ("분모: 파일", len(files)), ("분모: 개체 레코드", int(nrec)),
        ("파일 sha256", shas),
        ("첫 날", int(days[0])), ("끝 날", int(days[-1])),
        ("분모: 덮는 날", int(len(days))),
        ("첫 날(연)", _r(float(yrs[0]))), ("끝 날(연)", _r(float(yrs[-1]))),
        ("문서당 평균 조회수 범위", [_r(float(raw.min()), 3), _r(float(raw.max()), 3)]),
        ("🔴🔴 정직한 한계", "위키 pageviews 는 2015-07-01 에 «시작»한다. "
                       "챔피언 블록 0(yr < 2015.010794)은 덮는 날이 0 이다 --- ㉯ 로 등기."),
    ])
    _ZCACHE[key] = (info, days, yrs, z)
    return _ZCACHE[key]


def to_cdf(v):
    """[0,1] 로 «경험 CDF» 를 태운다 — 챔피언 축 규약(백분위·중립 0.5)에 맞춘다."""
    order = np.argsort(v)
    return v[order], (np.arange(len(v)) + 0.5) / len(v)


def zseries(wdir=WIKI_DIR, ma=Z_MA):
    """🔴 **위키 전체 집계.** 날마다 「활성 문서당 평균 조회수」의 로그 → 30일 이동평균.

    🔴 **왜 「합」이 아니라 「문서당 평균」인가**: 합은 «문서가 몇 개 들어왔나»에
    끌려간다(문서는 시간이 갈수록 는다) — 그러면 `Z_t` 가 「시대」가 아니라
    「자료 수집 이력」이 된다. 문서당 평균은 그 편향을 뺀다.

    돌려주는 것 = (info, days, yrs, ma_z, cdf_x, cdf_y).
    """
    info0, days, yrs, z = zraw(wdir)
    k = int(ma)
    mz = np.convolve(z, np.ones(k) / k, mode="same") if k > 1 else z
    cdf_x, cdf_y = to_cdf(mz)
    info = collections.OrderedDict(info0)
    info["이동평균 창(일)"] = k
    return info, days, yrs, mz, cdf_x, cdf_y


def z_row(yr, yrs, mz, cdf_x, cdf_y):
    """행별 `Z` — 그 행의 연도에서 «선형 보간» 한 뒤 경험 CDF 를 태운다.

    돌려주는 것 = (값 in [0,1] · 중립 0.5, 표시자 0/1).
    """
    yr = np.asarray(yr, float)
    ok = np.isfinite(yr) & (yr >= yrs[0]) & (yr <= yrs[-1])
    v = np.full(len(yr), 0.5)
    if ok.any():
        raw = np.interp(yr[ok], yrs, mz)
        v[ok] = np.interp(raw, cdf_x, cdf_y)
    return v, ok.astype(float)


def z_block(yr, edges, yrs, mz, cdf_x, cdf_y, nblock=NBLOCK):
    """🔴 **블록 상수 `Z`** — 그 블록이 덮는 날들의 평균. 위약 팔이 쓴다.

    블록 «안»에서 상수이므로 그 주효과는 **블록 안 순위를 원리상 못 바꾼다**.
    """
    yr = np.asarray(yr, float)
    v = np.full(len(yr), 0.5)
    m = np.zeros(len(yr))
    for k in range(nblock):
        sel = np.isfinite(yr) & (yr >= edges[k]) & (yr < edges[k + 1])
        if not sel.any():
            continue
        dsel = (yrs >= edges[k]) & (yrs < edges[k + 1])
        if not dsel.any():
            continue                      # 그 블록을 덮는 위키 날이 «없다»
        v[sel] = float(np.interp(float(mz[dsel].mean()), cdf_x, cdf_y))
        m[sel] = 1.0
    return v, m


def block_const_table(edges, yrs, mz, cdf_x, cdf_y, nblock=NBLOCK):
    out = collections.OrderedDict()
    for k in range(nblock):
        dsel = (yrs >= edges[k]) & (yrs < edges[k + 1])
        out["블록 %d" % k] = collections.OrderedDict([
            ("덮는 위키 날", int(dsel.sum())),
            ("Z(블록 상수 · CDF)",
             _r(float(np.interp(float(mz[dsel].mean()), cdf_x, cdf_y)))
             if dsel.any() else None)])
    return out


# ══════════════════════════════════════════════════════════════════════
# 🔴 축을 «덧붙인다» — 챔피언 설계행렬에 닿는 유일한 통로
# ══════════════════════════════════════════════════════════════════════
def augment(d0, cols):
    """`cols` = OrderedDict 이름 → {도메인: (값, 표시자)}. 새 `Data` 를 돌려준다.

    🔴 **왜 「모든 도메인에」 넣어야 하나**: `lab/forms.py:197 AXIS_MODE='common'`
    이라 `axis_order()` 는 **12 도메인이 전부 가진 축만** 돌려준다. 한 도메인이라도
    빠뜨리면 그 열은 설계행렬에 **한 칸도 안 닿는다** — 노트 887·888 이 그 병으로
    무효가 됐다(`runners/hole888.py`). 이 함수는 그래서 «전 도메인»에 넣는다.
    """
    dom, names = {}, {}
    for d in sorted(d0.dom):
        A, M, y, t = d0.dom[d]
        nm = list(d0.names.get(d) or list(ALL5))
        av, mv = [np.asarray(A, float)], [np.asarray(M, float)]
        for nme, per in cols.items():
            v, mk = per[d]
            av.append(np.asarray(v, float).reshape(-1, 1))
            mv.append(np.asarray(mk, float).reshape(-1, 1))
            nm.append(nme)
        dom[d] = (np.column_stack(av), np.column_stack(mv),
                  np.asarray(y, float), t)
        names[d] = nm
    return Data(dom, names, {d: np.asarray(d0.yr[d]) for d in d0.dom})


def axis_cols(d0, d):
    """도메인 `d` 의 축 다섯 (값·표시자). 값은 `_feat` 규약대로 중립 0.5 대입."""
    nm = list(d0.names.get(d) or list(ALL5))
    A, M, y, t = d0.dom[d]
    V, O = [], []
    for a in ALL5:
        if a in nm:
            j = nm.index(a)
            o = np.asarray(M, float)[:, j] > 0
            V.append(np.where(o, np.asarray(A, float)[:, j], 0.5))
            O.append(o.astype(float))
        else:
            V.append(np.full(len(y), 0.5))
            O.append(np.zeros(len(y)))
    return np.column_stack(V), np.column_stack(O)


def zcols(d0, doms, mode, edges, zs, seed=996):
    """🔴🔴 `Z` 열 짓기. `mode` 넷 — 사전등록 §3 에 그대로 적혀 있다.

    | mode | 무엇 | 왜 |
    |---|---|---|
    | `주효과행` | `Z_wiki` 한 열(행별 날짜) | 위약 ㉡ — 상호작용이 «이겨야» 하는 대조 |
    | `주효과블록` | `Z_wiki` 한 열(블록 상수) | 위약 ㉠ — **원리상 블록 안 순위를 못 바꾼다** |
    | `상호작용` | `Z_wiki`(행별) + `ZX_<축>` 다섯 | 🔴 처치 |
    | `양성대조` | `Y_leak` 한 열(라벨 순위) | 🔴 **배선이 닿나** — 안 오르면 팔 C 는 미측정 |
    """
    _info, _days, yrs, mz, cx, cy = zs
    cols = collections.OrderedDict()
    if mode == "양성대조":
        per = {}
        for d in doms:
            y = np.asarray(d0.dom[d][2], float)
            ok = np.isfinite(y)
            v = np.full(len(y), 0.5)
            if ok.any():
                from scipy.stats import rankdata
                v[ok] = rankdata(y[ok]) / float(ok.sum())
            per[d] = (v, ok.astype(float))
        cols["Y_leak"] = per
        return cols
    zper = {}
    for d in doms:
        yr = np.asarray(d0.yr[d], float)
        if mode == "주효과블록":
            zper[d] = z_block(yr, edges, yrs, mz, cx, cy)
        else:
            zper[d] = z_row(yr, yrs, mz, cx, cy)
    cols["Z_wiki"] = zper
    if mode == "상호작용":
        for ai, a in enumerate(ALL5):
            per = {}
            for d in doms:
                V, O = axis_cols(d0, d)
                zv, zm = zper[d]
                mk = (O[:, ai] > 0) & (zm > 0)
                #: 🔴 «중심»을 뺀 곱 — 부호가 뜻을 갖게 한다. 결측은 중립 0.5
                v = np.full(len(zv), 0.5)
                v[mk] = (V[mk, ai] - 0.5) * (zv[mk] - 0.5) + 0.5
                per[d] = (v, mk.astype(float))
            cols["ZX_%s" % a] = per
    return cols


def zcov_ledger(d0, doms, blk, zs):
    """🔴🔴 **`Z` 덮음 장부** — 조항 59. 「없다」와 「못 봤다」와 「쟀는데 버렸다」는 셋이다."""
    _i, _d, yrs, mz, cx, cy = zs
    per, tot = collections.OrderedDict(), collections.OrderedDict()
    for k in range(NBLOCK):
        n = c = 0
        for d in doms:
            yr = np.asarray(d0.yr[d], float)
            m = np.asarray(blk[d][k], bool)
            v, mk = z_row(yr, yrs, mz, cx, cy)
            n += int(m.sum())
            c += int((m & (mk > 0)).sum())
        tot["블록 %d" % k] = collections.OrderedDict([
            ("행", n), ("Z 가 있는 행", c),
            ("덮음", _r(c / n, 6) if n else None)])
    for d in doms:
        yr = np.asarray(d0.yr[d], float)
        v, mk = z_row(yr, yrs, mz, cx, cy)
        per[d] = [int((np.asarray(blk[d][k], bool) & (mk > 0)).sum())
                  for k in range(NBLOCK)]
    return collections.OrderedDict([
        ("🔴 블록별", tot), ("도메인별 Z 있는 행", per),
        ("🔴🔴 블록 0 덮음이 0 인가(㉯-1 로 등기했다)",
         bool(tot["블록 0"]["Z 가 있는 행"] == 0))])


# ══════════════════════════════════════════════════════════════════════
# 능형 — 팔 A·B 의 «대리 세계»
# ══════════════════════════════════════════════════════════════════════
def ridge(X, y, alpha):
    """중심을 뺀 능형. 절편은 «벌하지 않는다»."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    mx, my = X.mean(0), y.mean()
    Xc, yc = X - mx, y - my
    G = Xc.T @ Xc + float(alpha) * np.eye(X.shape[1])
    b = np.linalg.solve(G, Xc.T @ yc)
    return b, float(my - mx @ b)


def cell_beta(V, O, yv, alpha, sd=None):
    """한 칸(블록 × 도메인)의 축 다섯 계수. `sd` 를 주면 «그 눈금»으로 표준화한다.

    🔴 `sd` 를 밖에서 주는 까닭: 조각(블록 쌍) 검정에서 두 블록이 **같은 눈금**을
    써야 순열이 «정확»해진다(순열은 눈금을 안 바꾼다).
    """
    from scipy.stats import rankdata
    n = len(yv)
    yy = rankdata(yv) / float(n)
    s = np.asarray(sd, float) if sd is not None else V.std(0)
    s = np.where(s > 1e-12, s, 1.0)
    Xs = V / s
    b, _c = ridge(Xs, yy, alpha)
    return b


def estimable(O, gate, V=None, minuniq=3):
    """축마다 「이 칸에서 계수를 «잴 수 있나»」. 🔴 조항 59 — 못 재는 것과 0 은 다르다."""
    out = []
    for j in range(O.shape[1]):
        n = int((O[:, j] > 0).sum())
        u = 0 if V is None else int(len(np.unique(V[O[:, j] > 0, j])))
        out.append(bool(n >= gate and (V is None or u >= minuniq)))
    return out


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 조항 78 — ㉮·㉯ 를 «기계로» 센다 (손 라벨은 무효다)
# ══════════════════════════════════════════════════════════════════════
def variant_grid(base, seed=996):
    """🔴 **표준 변이체 격자** — 세 팔이 «같은» 격자를 쓴다(조항 78 개정 2).

    `base` = {조각 이름: {도메인: 값}}.
    🔴 **격자에 「참을 내는」 변이체와 「거짓을 내는」 변이체가 «둘 다» 있어야**
    ㉯ 계수가 뜻을 갖는다. 995 는 위약을 **리터럴**로 지어 대조가 언제나 참이었다
    (티처 #134) --- 여기 격자는 **전부 자료를 실제로 흩는다**.

    🔴🔴 **설계 팔이 연기 시험에서 찾은 것**: 등록된 자 `cluster_se` 는
    「모든 도메인이 «똑같이» 움직인 입력」(SD=0 ⇒ SE=0)에서 **`None` 을 낸다** ---
    곧 **원리상 통과시키지 못한다**. 그래서 「상수」 변이체 «옆에» 「상수+잡음」을 둔다.
    """
    rs = np.random.RandomState(int(seed))

    def mk(fn):
        return collections.OrderedDict(
            [(k, {d: fn(v) for d, v in vv.items()}) for k, vv in base.items()])

    return [
        ("실측", base),
        ("전부 0", mk(lambda x: 0.0)),
        ("부호 뒤집기", mk(lambda x: -float(x))),
        ("전부 +0.5 상수(🔴 SD=0 ⇒ 등록된 자가 None 을 낸다)", mk(lambda x: 0.5)),
        ("+0.5 에 N(0,0.01) 잡음", mk(lambda x: 0.5 + float(rs.normal(0, 0.01)))),
        ("0 에 N(0,0.2) 잡음", mk(lambda x: float(rs.normal(0, 0.2)))),
        ("🔴 자료를 «실제로» 흩은 위약(도메인 통째 부호 무작위 · RandomState(%d))" % seed,
         mk(lambda x: float(x) * (1.0 if rs.rand() < 0.5 else -1.0))),
    ]


def taut_scan(claims, variants, label="", controls=()):
    """`claims` = [(이름, f(state)->bool)] · `variants` = [(변이체 이름, state)].

    각 주장을 **모든 변이체**에서 다시 계산한다.
      · 전부 참  ⇒ ㉮ (원리상 못 떨어진다)
      · 전부 거짓 ⇒ ㉯ (원리상 못 통과시킨다)
    🔴 **분자는 「0」을 낼 수 있어야 한다** — 그래서 대조 둘을 «일부러» 넣는다
    (하나는 늘 참 · 하나는 늘 거짓). 대조는 분자에서 «뺀다».
    """
    rows = collections.OrderedDict()
    a_n = b_n = 0
    for nm, fn in claims:
        vals = []
        for vn, st in variants:
            try:
                vals.append(bool(fn(st)))
            except Exception as e:                      # noqa: BLE001
                vals.append("못 쟀다: %s" % type(e).__name__)
        bools = [v for v in vals if isinstance(v, bool)]
        isa = bool(bools) and all(bools)
        isb = bool(bools) and not any(bools)
        rows[nm] = collections.OrderedDict([
            ("변이체별", collections.OrderedDict(
                [(variants[i][0], vals[i]) for i in range(len(variants))])),
            ("🔴 ㉮(전부 참)", isa), ("🔴 ㉯(전부 거짓)", isb)])
        a_n += int(isa)
        b_n += int(isb)
    #: 🔴🔴 **대조판은 「리터럴」이면 안 된다**(티처 #134 · 995 팔 B·C 가 그랬다:
    #:   `probe(..., True, True, ...)` 가 언제나 참이었다). 대조도 **자료에서
    #:   계산한 주장**이어야 하고, 같은 변이체 격자에서 다시 돈다.
    ctl = collections.OrderedDict()
    for nm, fn in controls:
        vals = []
        for vn, st in variants:
            try:
                vals.append(bool(fn(st)))
            except Exception as e:                      # noqa: BLE001
                vals.append("못 쟀다: %s" % type(e).__name__)
        bools = [v for v in vals if isinstance(v, bool)]
        ctl[nm] = collections.OrderedDict([
            ("변이체별", collections.OrderedDict(
                [(variants[i][0], vals[i]) for i in range(len(variants))])),
            ("🔴 ㉮(전부 참)", bool(bools) and all(bools)),
            ("🔴 ㉯(전부 거짓)", bool(bools) and not any(bools))])
    return collections.OrderedDict([
        ("🔴 무엇", label),
        ("분모: 검사한 주장", len(claims)),
        ("분모: 변이체", len(variants)),
        ("변이체 목록", [v[0] for v in variants]),
        ("🔴🔴 기계가 센 ㉮ 분자", int(a_n)),
        ("🔴🔴 기계가 센 ㉯ 분자", int(b_n)),
        ("🔴 대조판 --- «자료에서 계산한» 주장이다(리터럴 아님)", ctl),
        ("🔴 대조 ㉮ 분자", int(sum(1 for v in ctl.values() if v["🔴 ㉮(전부 참)"]))),
        ("🔴 대조 ㉯ 분자", int(sum(1 for v in ctl.values() if v["🔴 ㉯(전부 거짓)"]))),
        ("🔴🔴 계수가 「0」을 낼 수 있나(본 주장에서)", bool(a_n == 0 or b_n == 0)),
        ("주장별", rows)])
