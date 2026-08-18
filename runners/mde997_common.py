# -*- coding: utf-8 -*-
"""997 공용 — 🔴🔴 **`MDE`(최소검출효과)를 재는 기계 + 「라벨 0 개 자」의 배관.**

🔴 이 파일은 «측정하지 않는다». 자료를 열고, 자를 두고, 힘 곡선을 뽑는
함수만 둔다. 판정은 세 러너가 각자 자기 산출물에 낸다.

## 🔴 조항 신설 «금지» — 이미 있는 자의 «분모»를 넓힌다
등록된 자(`cluster_se` · `signflip_exact` · `holm` · `taut_scan` · `variant_grid`
· `cse_ledger` · `se_surrogate_check`)를 **`runners/delta996_common.py` 에서
그대로 가져다 쓴다.** 새로 짓지 않는다 --- 997 이 하는 일은 **그 자를
「라벨 0 개」 표본까지 «넓히는» 것**이다.

## 🔴 왜 이 사이클인가
`docs/목표.md` 「파운데이션이냐를 재는 자」 절이 적었다:
*「검출력을 «먼저» 적는다: n=93 · 군집 37 에서 BCa 폭 0.64~0.88. **잴 수 있는
최소 효과가 ρ 0.3~0.6 인 자로 판정하러 가면 안 된다**」*.
🔴 **그런데 83 사이클 동안 아무도 그 수(`MDE`)를 «재지» 않았다.**

## 🔴 「비지도」의 뜻 --- 997 이 «닫는» 하나
| | 뜻 | 915 는 | 997 은 |
|---|---|---|---|
| ① | **표본을 라벨 없이 뽑나** (어느 행이 프리텍스트에 드는가) | ✅ 지켰다 | 지킨다 |
| ② | **목적함수가 라벨을 안 쓰나** (프리텍스트 표적) | ✅ 지켰다 | 지킨다 |
| ③ | 🔴 **«자»까지 라벨을 안 쓰나** (점수를 무엇으로 매기나) | ❌ **선형 프로브 = 라벨** | 🔴 **이것을 닫는다** |

**997 이 고르는 뜻 = ③.** 까닭은 수다 --- ①②만 지키면 자가 라벨을 쓰므로
**분모가 유보 라벨 수(3,775)로 잘린다.** ③ 을 지키면 분모가 **관측 셀
(237,096 · 유보 20% ≈ 47,419)** 이 된다. 사용자의 물음(*「언제부터 이렇게
라벨링을 계속 하려는거야」*)이 겨누는 자리가 정확히 ③ 이다.

## 자 둘 (같은 세계 · 같은 12 군집)
| 자 | 쓰는 것 | 분모 | 라벨 비트 |
|---|---|---|---|
| **㉠ 라벨 프로브** | 얼린 표현 → Ridge → 유보 라벨 스피어만 | 유보 라벨 3,775 | 🔴 쓴다 |
| **㉡ 라벨 0 개 자** | 가림 복원 → 유보 «셀» 스피어만 | 유보 셀 ≈47,419 | **0 비트** |
"""
import collections
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import delta996_common as C                       # noqa: E402  🔴 등록된 자 · 읽기로만

# ── 사전등록 상수 (측정 전에 박았다) ──────────────────────────────────
NOTE = 997
PREREG = "docs/prereg_997_unsupervised_mde.md"
T_CANON = 2025.0
SEEDS = tuple(range(12))          #: `ff753.RULER_SEEDS` — 정본 12 씨앗

#: 🔴 `MDE` 의 두 인자 — 조항 66 「문턱 대신 검사를 인자화한다」
ALPHA = 0.05
POWER = 0.80
#: `z_{1-α/2} + z_{1-β}` — 해석식 `MDE_a` 의 계수. 손으로 안 적고 계산한다
Z_SUM = None                      #: `zsum()` 이 채운다

#: 🔴 힘 곡선 격자 — 「ρ 0.1 아래냐 0.3+ 냐」 분기점을 «둘 다» 촘촘히 문다
DELTA_GRID = (0.0, 0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.04,
              0.05, 0.06, 0.08, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30,
              0.40, 0.50, 0.60, 0.80)
POWER_B = 4000                    #: 힘 한 점당 모의 반복
POWER_SEED = 997

#: 🔴 분기 문턱 — 사용자/카드가 «측정 전»에 준 것. 실측으로 정하지 않는다
BRANCH_GOOD = 0.10                #: 이 아래면 「자를 세울 수 있다」
BRANCH_BAD = 0.30                 #: 이 위면 「표본이 부족한 것」

#: 🔴 라벨 0 개 자의 설정 — 915 `grid915_ssl.py` 와 «같은 꼴»(가림 복원)
MASK_EVAL_FRAC = 0.20             #: 관측 셀 중 유보로 뗄 몫
MASK_P = 0.25                     #: 학습 중 입력에서 가리는 몫
MAE_WIDTH = 256
MAE_DEPTH = 2
MAE_STEPS = int(os.environ.get("M997_STEPS", "3000"))   #: 🔴 915 `grid915_ssl.STEPS` 와 같은 값
MAE_BATCH = 256
SPLIT_SEED = 9970                 #: 유보 셀 쪼개기 씨앗 — 모든 팔이 «같은» 쪼갬을 쓴다
SHAM_SEEDS = tuple(range(12))     #: 위약(참 효과 0) 짝의 씨앗

#: 🔴 조항 76 — «어림 금지 · 적합 하나를 재서» 정했다. 아래 실측표는 사전등록 §6 에 있다
#:   토치 적합 1500 스텝: 2→2.75s · 4→2.78s · 5→2.94s · 8→3.41s · 10→4.06s ⇒ **무릎은 2**
THREADS = int(os.environ.get("M997_THREADS", "2"))


def zsum():
    """`z_{1-α/2} + z_{1-β}` — 🔴 손으로 안 적는다(조항 78 ㉮ 회피)."""
    global Z_SUM
    if Z_SUM is None:
        try:
            from scipy.stats import norm
            Z_SUM = float(norm.ppf(1 - ALPHA / 2) + norm.ppf(POWER))
        except Exception:                                   # noqa: BLE001
            from statistics import NormalDist
            n = NormalDist()
            Z_SUM = float(n.inv_cdf(1 - ALPHA / 2) + n.inv_cdf(POWER))
    return Z_SUM


def _r(x, n=6):
    return C._r(x, n)


def sha_file(rel):
    return C.sha_file(rel)


def stamp(t0, extra=None):
    d = collections.OrderedDict([
        ("노트", NOTE),
        ("사전등록", collections.OrderedDict([
            ("파일", PREREG), ("sha256", sha_file(PREREG))])),
        ("코드 sha256", collections.OrderedDict([
            (f, sha_file("runners/" + f)) for f in (
                "mde997_common.py", "mde997_probe.py", "mde997_mask.py",
                "mde997_gate.py")])),
        ("빌린 자 sha256", collections.OrderedDict([
            ("runners/delta996_common.py", sha_file("runners/delta996_common.py"))])),
        ("끝 시각(UTC)", C.now_utc()),
        ("걸린 초", round(time.time() - t0, 2)),
        ("스레드", THREADS),
    ])
    if extra:
        d.update(extra)
    return d


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 `MDE` — 정의와 기계
# ══════════════════════════════════════════════════════════════════════
MDE_DEF = collections.OrderedDict([
    ("🔴 무엇", "`MDE`(최소검출효과) = 「등록된 검정이 힘 %.2f 로 기각하는 «참 효과» "
              "Δρ 의 최솟값」. 자와 표본이 정해지면 «자료를 보기 전에» 정해지는 수다." % POWER),
    ("🔴 왜 이 사이클의 유일한 필수 산출인가",
     "915 가 `k=16` 최고 SSL 0.1719 를 라벨 순열 바닥 0.1708 «옆»에서 얻고 멈췄다. "
     "그것이 「실패」인지 「미측정」인지는 `MDE` 를 알아야 갈린다 --- "
     "`MDE` 가 그 차(0.0011)보다 크면 그 주행은 «아무것도 재지 않은 것»이다."),
    ("(가) 해석식 `MDE_a`",
     "`MDE_a = (z_{1-α/2} + z_{1-β}) · SE_0`. `SE_0` = 귀무(참 효과 0)에서 "
     "등록된 통계량의 표준오차. α=%.2f 양측 · 힘=%.2f." % (ALPHA, POWER)),
    ("(나) 모의 `MDE_s` — 🔴 헤드라인",
     "참 효과 δ 를 격자 위에 놓고, **위약(참 효과 0)에서 «실제로 잰» 도메인별 잔차**를 "
     "다시 뽑아 δ 를 더한 뒤, **등록된 검정을 그대로** %d 번 돌려 경험력 Π(δ) 를 얻는다. "
     "`MDE_s` = Π(δ) ≥ %.2f 인 «최소» 격자점. 격자 사이는 선형 보간해 병기한다." % (POWER_B, POWER)),
    ("🔴 왜 (나) 가 헤드라인인가",
     "군집 d=12 에서 정규 근사가 얼마나 틀리는지를 «모르는 채» (가) 만 내면 "
     "그 자체가 미측정이다. 둘의 비 `MDE_s / MDE_a` 를 칸으로 낸다."),
    ("🔴 등록된 검정(기각 규칙) --- 넷으로 «인자화»한다(조항 66)",
     "㉠ `|Δ̄| > 2·SE`(등가중 도메인 평균 · `delta996_common.cluster_se` 꼴) · "
     "㉡ 부호뒤집기 «전수» 2^d 순열 p ≤ %.2f(`signflip_exact` 꼴) · "
     "㉢ 정규근사 양측 p ≤ %.2f(`two_sided_p` 꼴) · ㉠∧㉡ 연언. "
     "🔴 **헤드라인은 ㉠** --- 990~996 이 세계 명제를 «실제로» 판정한 규칙이 그것이다."
     % (ALPHA, ALPHA)),
    ("🔴🔴 왜 연언이 헤드라인이 «아닌가» --- 설계 팔이 연기 시험에서 찾은 것",
     "d=12 에서 등록된 부호뒤집기 규칙은 **큰 효과에서 힘을 «잃는다»**. "
     "효과가 커지면 도메인을 k 개 뒤집은 패턴도 `|평균| > 2·SE` 를 만족해 발화 패턴이 "
     "늘고 p 가 올라간다. 균질 효과의 극한에서 발화 수는 k∈{0,1,2}(와 대칭)의 "
     "2·(1+12+66)=158 → p=0.0386 «또는» k=3 까지 포함한 598 → p=0.146 이고, "
     "그 갈림이 `|12-2k| > (4/√12)·√(k(12-k))` 의 k=3 에서 **6 대 6.0 의 칼날 위**다. "
     "🔴 곧 순열 p 의 힘은 δ 에 «단조가 아니다». 이 사실 자체를 산출물에 칸으로 낸다 "
     "--- 조항 79 개정 3 이 헤드라인 칸으로 요구한 자의 성질이다."),
    ("🔴 잔차 풀은 어디서 오나",
     "「위약 짝」 --- 참 효과가 «구성상» 0 인 두 팔의 차. 자마다 다르다: "
     "㉠ 전량 = 학습 행을 씨앗별로 반씩 갈라 두 프로브를 적합한 차 · "
     "㉠ 소수 = 같은 k 를 두 번 독립으로 뽑은 차 · "
     "㉡ = 같은 설정을 씨앗만 바꿔 두 번 학습한 차. **전부 자료를 실제로 흩는다** "
     "--- 리터럴 위약이 아니다(조항 78 재개정 1)."),
    ("🔴 재표집 꼴", "헤드라인 = «도메인 짝지어»(도메인 d 의 잔차는 d 자신의 위약 값에서만 "
                 "뽑는다 --- 이분산을 보존). 민감도 = «통째 풀»(도메인을 교환가능으로 본다)."),
    ("🔴 이 정의가 못 하는 것",
     "① 잔차 풀이 위약 «짝»에서 오므로 두 팔의 «공통» 성분(같은 자료를 봤다)이 상쇄돼 "
     "`MDE` 를 «낙관»할 수 있다. ② δ 를 「도메인마다 같은 값」으로 더한다 --- "
     "효과가 도메인마다 갈리면 실제 힘은 더 낮다. **둘 다 반증조건으로 등록한다.**"),
])


def _signflip_S(d):
    """`2^d × d` 부호 패턴. 🔴 `delta996_common.signflip_exact` 와 «같은 꼴»."""
    i = np.arange(1 << d, dtype=np.int64)[:, None]
    j = np.arange(d, dtype=np.int64)[None, :]
    return np.where((i >> j) & 1 == 0, 1.0, -1.0)


def signflip_p_batch(M, S=None):
    """`M` = (d, R) 도메인×반복. 반복마다 「전수 부호뒤집기」 p 를 «한꺼번에» 낸다.

    🔴 등록된 자 `signflip_exact` 를 반복 4000 번 부르면 파이썬 루프가 터진다.
    그래서 «같은 식»을 벡터로 쓰고, **관측 자료에서 등록된 자와 값이 같은지
    코드로 대조한다**(`signflip_selfcheck`). 자가 자기 출처를 못 대면 자가 아니다(조항 66).
    """
    M = np.asarray(M, float)
    d, R = M.shape
    if S is None:
        S = _signflip_S(d)
    with np.errstate(all="ignore"):
        tot = S @ M                                  # (2^d, R)
        sq = np.ones((1 << d, 1)) @ (M ** 2).sum(axis=0, keepdims=True)
        mean = tot / d
        var = (sq - (tot ** 2) / d) / (d - 1)
        sd = np.sqrt(np.maximum(var, 0.0))
        se = sd * np.sqrt((d - 1.0) / d) / np.sqrt(d)
        hit = np.abs(mean) > 2.0 * se                # (2^d, R)
    return hit.mean(axis=0), hit[0], mean[0], se[0]


def signflip_selfcheck(vals):
    """🔴 빠른 판이 «등록된 자»와 글자 그대로 같은 수를 내나 --- 계산으로 대조."""
    ds = sorted(vals)
    v = np.array([[vals[d]] for d in ds], float).T.reshape(len(ds), 1)
    p, hit, mean, se = signflip_p_batch(v)
    ref = C.signflip_exact({d: [float(vals[d])] for d in ds}, ["대비"])
    got = ref.get("🔴🔴 p(조각 «전부» 넘는다 = 연언)")
    return collections.OrderedDict([
        ("빠른 판 p", _r(float(p[0]), 8)),
        ("등록된 자 p(`signflip_exact`)", got),
        ("차", _r(abs(float(p[0]) - float(got)), 12) if got is not None else None),
        ("🔴 같은가", bool(got is not None
                        and abs(float(p[0]) - float(got)) < 1e-12)),
        ("빠른 판 평균", _r(float(mean[0]))),
        ("등록된 자 평균", (ref.get("관측 평균") or [None])[0]),
        ("빠른 판 SE", _r(float(se[0]), 8)),
        ("등록된 자 SE", (ref.get("관측 SE(해석)") or [None])[0]),
    ])


def two_sided_p_np(t):
    from math import erfc, sqrt
    return float(erfc(abs(float(t)) / sqrt(2.0)))


def power_curve(pool_by_dom, doms, grid=DELTA_GRID, B=POWER_B, seed=POWER_SEED,
                paired=True):
    """🔴 힘 곡선 --- 위약에서 «실제로 잰» 잔차를 다시 뽑아 δ 를 더하고 등록된 검정을 돌린다.

    `pool_by_dom` = {도메인: [위약 Δ, ...]}. 반환: 격자점마다 세 검정의 힘.
    """
    ds = [d for d in doms if len(pool_by_dom.get(d, [])) > 0]
    d = len(ds)
    if d < 2:
        return collections.OrderedDict([("🔴 못 쟀다", "도메인이 2 미만이다")])
    per = [np.asarray(pool_by_dom[x], float) for x in ds]
    per = [p[np.isfinite(p)] for p in per]
    flat = np.concatenate(per)
    grand = float(flat.mean())
    per_c = [p - grand for p in per]                 # 🔴 풀 전체 평균으로 중심
    flat_c = flat - grand
    rng = np.random.RandomState(int(seed))
    S = _signflip_S(d)
    #: 🔴 모든 격자점이 «같은» 잔차 뽑기를 쓴다 --- δ 만 달라진다(공통 난수)
    if paired:
        E = np.stack([per_c[i][rng.randint(0, len(per_c[i]), B)]
                      for i in range(d)])            # (d, B)
    else:
        E = flat_c[rng.randint(0, len(flat_c), (d, B))]
    rows = collections.OrderedDict()
    pw = collections.OrderedDict([("🔴 ㉠ 2·SE(헤드라인)", []), ("㉡ 순열만", []),
                                  ("㉢ 정규근사 p", []), ("㉠∧㉡ 연언", [])])
    for g in grid:
        p, hit0, mean0, se0 = signflip_p_batch(E + float(g), S)
        a = hit0                                     # |평균| > 2·SE
        b = p <= ALPHA
        with np.errstate(all="ignore"):
            t = np.where(se0 > 0, mean0 / np.where(se0 > 0, se0, 1.0), np.nan)
        c = np.array([(two_sided_p_np(x) <= ALPHA) if np.isfinite(x) else False
                      for x in t])
        rows["δ=%.4f" % g] = collections.OrderedDict([
            ("🔴 힘 ㉠ 2·SE", _r(float(a.mean()), 5)),
            ("힘 ㉡ 순열만", _r(float(b.mean()), 5)),
            ("힘 ㉢ 정규근사 p", _r(float(c.mean()), 5)),
            ("힘 ㉠∧㉡ 연언", _r(float((a & b).mean()), 5)),
            ("모의 평균 Δ̄", _r(float(mean0.mean()))),
            ("모의 SE 중앙값", _r(float(np.median(se0)), 8)),
            ("모의 순열 p 중앙값", _r(float(np.median(p)), 6))])
        pw["🔴 ㉠ 2·SE(헤드라인)"].append(float(a.mean()))
        pw["㉡ 순열만"].append(float(b.mean()))
        pw["㉢ 정규근사 p"].append(float(c.mean()))
        pw["㉠∧㉡ 연언"].append(float((a & b).mean()))

    def _mde(vals):
        g = np.asarray(grid, float)
        v = np.asarray(vals, float)
        ix = np.where(v >= POWER)[0]
        if len(ix) == 0:
            return None, None, "🔴 격자 최대 δ=%.2f 에서도 힘이 %.3f 라 못 넘었다" % (
                g[-1], v[-1])
        i = int(ix[0])
        if i == 0:
            return float(g[0]), float(g[0]), "격자 첫 점에서 이미 넘었다"
        x0, x1, y0, y1 = g[i - 1], g[i], v[i - 1], v[i]
        itp = float(x0 + (POWER - y0) * (x1 - x0) / (y1 - y0)) if y1 > y0 else float(g[i])
        return float(g[i]), itp, "격자점 %d 에서 처음 넘었다" % i

    mde = collections.OrderedDict()
    for k, v in pw.items():
        a, b, note = _mde(v)
        va = np.asarray(v, float)
        imax = int(va.argmax())
        mde[k] = collections.OrderedDict([
            ("🔴 MDE_s(격자점)", _r(a) if a is not None else None),
            ("MDE_s(선형 보간)", _r(b) if b is not None else None),
            ("메모", note),
            ("격자 안 최대 힘", _r(float(va.max()), 5)),
            ("그 δ", _r(float(np.asarray(grid, float)[imax]))),
            ("🔴 힘이 δ 에 단조인가", bool(np.all(np.diff(va) >= -1e-9))),
            ("🔴 마지막 격자점의 힘", _r(float(va[-1]), 5))])
    #: 🔴 해석식 --- 귀무(δ=0) 모의에서 잰 통계량의 SD 를 `SE_0` 로 쓴다
    p0, h0, m0, s0 = signflip_p_batch(E, S)
    se0 = float(np.median(s0))
    return collections.OrderedDict([
        ("🔴 재표집 꼴", "도메인 짝지어" if paired else "통째 풀"),
        ("분모: 도메인 d", d), ("도메인", ds),
        ("분모: 위약 값 수(도메인별)", {ds[i]: int(len(per[i])) for i in range(d)}),
        ("분모: 모의 반복 B", int(B)), ("씨앗", int(seed)),
        ("풀 평균(뺀 값)", _r(grand)),
        ("귀무 δ=0 에서 잰 것", collections.OrderedDict([
            ("모의 Δ̄ 의 SD = `SE_0`", _r(float(m0.std(ddof=1)), 8)),
            ("등록된 자가 쓰는 해석 SE 의 중앙값", _r(se0, 8)),
            ("🔴 1종 오류(연언)", _r(float((h0 & (p0 <= ALPHA)).mean()), 5)),
            ("🔴 1종 오류(2·SE 만)", _r(float(h0.mean()), 5)),
            ("🔴 1종 오류(순열만)", _r(float((p0 <= ALPHA).mean()), 5)),
            ("🔴 이름 규약", "「1종 오류」는 δ=0 격자점의 기각률이다 --- 위약 잔차 풀이 "
                         "참으로 0 중심이라는 «가정» 위에 선다(풀 평균을 뺐다)")])),
        ("🔴 해석식 MDE_a", collections.OrderedDict([
            ("z 합", _r(zsum(), 8)),
            ("SE_0(모의 Δ̄ 의 SD)", _r(float(m0.std(ddof=1)), 8)),
            ("🔴 MDE_a", _r(zsum() * float(m0.std(ddof=1))))])),
        ("🔴🔴 MDE_s", mde),
        ("🔴 MDE_s / MDE_a",
         _r(mde["🔴 ㉠ 2·SE(헤드라인)"]["MDE_s(선형 보간)"]
            / (zsum() * float(m0.std(ddof=1))))
         if mde["🔴 ㉠ 2·SE(헤드라인)"]["MDE_s(선형 보간)"] is not None
         and float(m0.std(ddof=1)) > 0 else None),
        ("힘 곡선", rows),
    ])


def branch(mde_s):
    """🔴 카드가 «측정 전»에 준 분기표. 실측으로 문턱을 정하지 않는다."""
    if mde_s is None:
        return collections.OrderedDict([
            ("🔴 판정", "못 잰다 --- 격자 안에서 힘 %.2f 에 못 닿았다" % POWER),
            ("뜻", "표본이 부족한 것. 자를 못 만든다. 자료 수집이 선결")])
    if mde_s < BRANCH_GOOD:
        v = ("🔴 `ρ %.2f` 아래" % BRANCH_GOOD,
             "자를 세울 수 있다 → 비지도를 «진짜로» 재 볼 수 있다")
    elif mde_s >= BRANCH_BAD:
        v = ("🔴 여전히 `ρ %.2f+`" % BRANCH_BAD,
             "표본이 부족한 것. 자를 못 만든다. 자료 수집이 선결")
    else:
        v = ("사이(%.2f ≤ MDE < %.2f)" % (BRANCH_GOOD, BRANCH_BAD),
             "🔴 카드의 분기표에 «없는» 칸이다 --- 998 사전등록에서 갈라야 한다")
    return collections.OrderedDict([
        ("MDE_s(헤드라인 ㉠ 2·SE · 보간)", _r(mde_s)),
        ("🔴 판정", v[0]), ("뜻", v[1]),
        ("분기 문턱(측정 전에 박은 것)",
         {"좋음": BRANCH_GOOD, "나쁨": BRANCH_BAD})])


# ══════════════════════════════════════════════════════════════════════
# 자료 --- 🔴 ㉡ 은 이 아래 어느 함수도 `y` 를 «열지 않는다»
# ══════════════════════════════════════════════════════════════════════
def load(perm_label_seed=None):
    """챔피언 세계를 연다. `perm_label_seed` 가 있으면 **라벨만** 순열한다.

    🔴 라벨 순열 바닥(⑤)의 «기계»다 --- ㉡ 은 `y` 를 안 읽으므로 값이
    **글자 그대로** 안 변해야 하고, ㉠ 은 무너져야 한다.
    """
    #: 🔴 `lab/trendaxes.py:117` 이 `data/state/popup_v2.npz` 를 **상대경로**로 연다
    #:   --- 어느 디렉터리에서 띄우든 같은 값이 나오게 여기서 못박는다
    os.chdir(str(ROOT))
    import ff753 as FF
    data = FF.shell(FF.base())
    if perm_label_seed is not None:
        rng = np.random.RandomState(int(perm_label_seed))
        for d in list(data.dom):
            A, M, y, t = data.dom[d]
            yp = np.array(y, float, copy=True)
            fin = np.where(np.isfinite(yp))[0]
            yp[fin] = yp[fin][rng.permutation(len(fin))]
            data.dom[d] = (A, M, yp, t)
        data.yr = {}
        data.__post_init__()
    return data


def col_union(data):
    doms = list(data.dom)
    cols = []
    for d in doms:
        for c in (data.names.get(d) or []):
            if c not in cols:
                cols.append(c)
    return doms, cols


def sp(a, b):
    """스피어만. 🔴 `ff753`/`ssl909_probe` 와 «같은 꼴»(동률 평균)."""
    from scipy.stats import spearmanr
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 5 or len(np.unique(a[ok])) < 3 or len(np.unique(b[ok])) < 3:
        return float("nan")
    return float(spearmanr(a[ok], b[ok]).statistic)


def rank01(v):
    from scipy.stats import rankdata
    v = np.asarray(v, float)
    r = np.full(len(v), np.nan)
    ok = np.isfinite(v)
    if ok.sum() >= 2:
        r[ok] = (rankdata(v[ok]) - 1.0) / (ok.sum() - 1.0)
    return r


def inject(pred, truth, lam):
    """🔴 신호 주입 --- 순위 공간에서 예측을 «참»쪽으로 λ 만큼 끈다.

    `λ=0` 이면 원 예측 · `λ=1` 이면 완전 예측. **실현된 효과 δ 는 그 결과의
    스피어만 차로 «재서» 쓴다** --- λ 를 δ 로 부르지 않는다.
    """
    return (1.0 - float(lam)) * rank01(pred) + float(lam) * rank01(truth)


def json_dump(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, indent=1, default=float)
    p.write_text(txt, encoding="utf-8")
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()
