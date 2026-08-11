# -*- coding: utf-8 -*-
"""노트 908-ㄷ 측정 — **도메인 가중을 배우게 하면 판이 오르나.**

사전등록 `docs/prereg_908c_pooling.md`(sha256 을 산출물에 박는다) · 구현
`lab/mixture908.py` · 산출물 `runners/out908c_pooling.json`.

순서(어기면 이 팔은 무효다): 사전등록 → **배선 검사 셋** → 측정 → 판정.
🔴 배선이 안 닫히면 측정 안 한다(노트 897: *"조각이 판에 안 닿는다"*).

파이프에 안 건다(노트 888 병 의 SIGPIPE 자백) --- 파일로 받는다.
`timeout` 명령이 없으므로 **파이썬 안에서** 예산을 본다.
"""
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import ff753 as FF                                             # noqa: E402
from dose896 import EXPECT_POOLED_K1_S0, THRESH                # noqa: E402
from ruler890 import EXPECT_K1_S0                              # noqa: E402
from lab.harness import Data, MIN_TRAIN, evaluate              # noqa: E402
from lab.mixture908 import Mixture                             # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = Path(os.environ.get("NN908C_OUT", ROOT / "runners/out908c_pooling.json"))
LOG = Path(os.environ.get("NN908C_LOG", ROOT / "runners/out908c_log.txt"))
PREREG = ROOT / "docs/prereg_908c_pooling.md"
T = 2025.0
SEEDS = (0, 1, 2)
PLACEBO_DRAWS = (9081, 9082, 9083)
PERM_DRAWS = (7081, 7082, 7083)
ULP_TOL = 8
BUDGET_S = float(os.environ.get("NN908C_BUDGET", 6000))
N_HOLDOUT = 3775
N_DOM = 12

A0, A1, A2, A3, A4, A5 = (
    "A0 챔피언", "A1 표 갱신", "A2 불확실도 가중(Kendall+18)",
    "A3 group-DRO(Sagawa+20)", "A4 계층 축소(Efron–Morris 75)",
    "A5 스태킹·도메인 게이팅(Wolpert 92 · Jacobs+91)")
ARMS = [(A0, "off"), (A1, "table"), (A2, "uncert"),
        (A3, "dro"), (A4, "shrink"), (A5, "stack")]
CONST, NOIDOL = "결함ㄱ 상수 w=1", "결함ㄴ 아이돌 w≈0"

t0 = time.time()
_log = open(LOG, "w", buffering=1)


def say(s):
    print(s, flush=True)
    _log.write(f"[{time.time()-t0:7.1f}s] {s}\n")


def left():
    return BUDGET_S - (time.time() - t0)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _j(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


REPORT = {
    "노트": "908-ㄷ",
    "무엇": "도메인 가중을 손으로 안 적고 배운다 --- 타 분야 방법론 이식(아키텍처 §10)",
    "사전등록": {"파일": "docs/prereg_908c_pooling.md", "sha256": sha(PREREG),
               "🔴 커밋은 주 세션이 한다": "이 팔은 git add·커밋을 안 했다"},
    "코드 sha256": {"lab/mixture908.py": sha(ROOT / "lab/mixture908.py"),
                   "runners/nn908c_pooling.py": sha(__file__)},
    "🔴 git HEAD 스탬프를 안 쓴다": (
        "루프 v3.2 --- 긴 러너에서 HEAD 는 원리상 「시작 시점」이다. "
        "코드 sha + 끝 시각으로 대신한다"),
    "들여온 출처(주장이 아니라 후보 · §10.2)": [
        "ㄱ Kendall·Gal·Cipolla, Multi-Task Learning Using Uncertainty to Weigh "
        "Losses, CVPR 2018 pp.7482-7491 【검색 스니펫만 --- 초록도 못 봤다】",
        "ㄴ Sagawa·Koh·Hashimoto·Liang, Distributionally Robust Neural Networks "
        "for Group Shifts, ICLR 2020 (arXiv:1911.08731) 【초록】 "
        "🔴 자료별 n·집단 수는 **못 읽었다**(초록에 없고 PDF 파싱 실패)",
        "ㄷ Wolpert, Stacked Generalization, Neural Networks 5(2):241-259, 1992 "
        "【검색 스니펫만】",
        "ㄹ Efron·Morris, Data Analysis Using Stein's Estimator, JASA 70(350), "
        "1975 【검색 스니펫만】 --- 그쪽 조건 타자 18명 × 45타석",
        "ㅁ Jacobs·Jordan·Nowlan·Hinton, Adaptive Mixtures of Local Experts, "
        "Neural Computation 3(1):79-87, 1991 【검색 스니펫만】",
    ],
    "🔴 인용을 근거로 판정하지 않는다": (
        "위 다섯의 어떤 수도 우리 결론에 안 들어간다. 판단 근거는 아래 실측뿐이다"),
    "⚠ 쫓아가 본 거짓 경보 하나(조항 59 --- '못 봤다'가 아니라 '봤고 아니었다')": (
        "A4·A5 의 local 전문가(Ridge)가 돌 때 sklearn/utils/extmath.py:203 이 "
        "'divide by zero / overflow / invalid value encountered in matmul' 을 "
        "수백 번 낸다. 설계행렬을 직접 재 보니 **전 도메인 비유한 0칸 · max|X| = 1.0 · "
        "Ridge 계수 최대 0.63** 이고, 순수 난수 (406,88)@(88,) 행렬곱도 같은 경고를 "
        "내면서 결과는 전부 유한하다(numpy 2.0.2 · macOS). **numpy/BLAS 의 헛 경보이고 "
        "우리 수는 안 다쳤다.** 다음 세션이 이 경고를 보고 없는 버그를 쫓지 않게 적는다"),
}


def dump(status=None):
    if status:
        REPORT["상태"] = status
    REPORT.setdefault("상태", "진행 중")
    REPORT["끝 시각(UTC)"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    REPORT["걸린 시간(초)"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(REPORT, ensure_ascii=False, indent=1, default=_j))


# ── 자료 ───────────────────────────────────────────────────────────────
say("자료를 만든다")
D = FF.shell(FF.base())
DOMS = sorted(D.dom)
W = D.weights(T)
TOT = sum(W.values())
NTR = {d: int((np.isfinite(D.yr[d]) & (D.yr[d] < T)
               & np.isfinite(D.dom[d][2])).sum()) for d in DOMS}
NPOST = {d: int((np.isfinite(D.yr[d]) & (D.yr[d] >= T)).sum()) for d in DOMS}
NPOST_LAB = {d: int((np.isfinite(D.yr[d]) & (D.yr[d] >= T)
                     & np.isfinite(D.dom[d][2])).sum()) for d in DOMS}


def train_data():
    """`fit` 이 실제로 받는 것과 **같은 것**(하네스 deploy 갈래 복사)."""
    tr, yr = {}, {}
    for d in D.dom:
        k = (np.isfinite(D.yr[d]) & (D.yr[d] < T) & np.isfinite(D.dom[d][2]))
        if k.sum() >= MIN_TRAIN:
            tr[d] = D.slice(d, k)
            yr[d] = np.asarray(D.yr[d])[k]
    return Data(tr, D.names, yr)


#: 🔴 A1 의 표는 **오늘 세어서** 넣는다(손 전사 금지 · 조항 60). 라벨은 안 본다 ---
#: 유보 **행 수**만 센다.
Mixture.TRAINW_TODAY = dict(NPOST)

CHAMP_TRAINW = dict(Mixture.TRAINW)
_Ttr = sum(NTR.values()); _Tte = sum(CHAMP_TRAINW.get(d, 0) for d in DOMS)
CHAMP_WEFF = {}
for d in DOMS:
    st = NTR[d] / max(1, _Ttr)
    se = CHAMP_TRAINW.get(d, 0) / max(1, _Tte)
    r = (se / st) if st > 0 else 1.0
    CHAMP_WEFF[d] = min(max(r, 0.2), 1.0)

REPORT["0. 판이 무엇인가(오늘 실측)"] = {
    "도메인 수": len(DOMS), "도메인": DOMS,
    "채점 가중(라벨 있는 유보행)": W, "가중 합": TOT,
    "정규 가중": {d: round(W[d] / TOT, 6) for d in W},
    "유보 전행": NPOST, "유보 라벨 있는 행": NPOST_LAB, "학습행": NTR,
    "🔴 합 == 분모 단언": {
        "Σ채점가중 == 3775": TOT == N_HOLDOUT,
        "도메인 수 == 12": len(DOMS) == N_DOM,
        "Σ정규가중 == 1(1e-12)": abs(sum(W[d] / TOT for d in W) - 1.0) < 1e-12,
        "Σ학습행": sum(NTR.values()),
        "Σ유보전행": sum(NPOST.values()),
        "Σ유보라벨행": sum(NPOST_LAB.values()),
        "🔴 유보 전행 합 != 채점 가중 합(분모가 둘이다)":
            sum(NPOST.values()) != TOT,
    },
}
assert TOT == N_HOLDOUT, f"🔴 유보 분모가 {TOT} --- 3775 가 아니다"
assert len(DOMS) == N_DOM, "🔴 도메인 수가 12 가 아니다"

FIND1 = {
    "어디": "lab/forms.py:916 F18_bagboost.TRAINW (+ :651 의 .get(d, 0) · :919 CLIP)",
    "표에 있는 도메인 수": len(CHAMP_TRAINW),
    "🔴 표에 없는 도메인": [d for d in DOMS if d not in CHAMP_TRAINW],
    "그래서 생기는 실효 학습 가중(오늘 실측)":
        {d: round(v, 6) for d, v in sorted(CHAMP_WEFF.items())},
    "영화가 받는 값": round(CHAMP_WEFF["영화"], 6),
    "영화의 판 정규가중": round(W["영화"] / TOT, 6),
    "영화 학습행": NTR["영화"],
    "왜 0.2 인가": ("TRAINW 에 이름이 없어 se=0 → w=0 → CLIP 하한 0.2. "
                 "측정이 정한 값이 아니라 **표에 이름이 없어서** 나온 값이다. "
                 "노트 514 가 이 표를 채택할 때 판은 11도메인이었고 영화는 나중에 왔다"),
    "🔴 표 안에 분모가 둘 섞여 있다(조항 60)": {
        "표의 웹툰": CHAMP_TRAINW.get("웹툰"),
        "오늘 웹툰 유보 전행": NPOST["웹툰"],
        "오늘 웹툰 라벨 있는 유보행(= 판 가중)": NPOST_LAB["웹툰"],
        "나머지 칸이 라벨 있는 행과 일치하나":
            {d: (CHAMP_TRAINW[d] == NPOST_LAB[d]) for d in sorted(CHAMP_TRAINW)},
    },
    "이 팔이 고치지 않는다": "찾은 것이지 이 팔이 고칠 것이 아니다 --- 주 세션·이슈로",
}
REPORT["1. 🔴 재기 전에 코드를 읽어서 찾은 것 --- 은퇴한 손 표"] = FIND1
say(json.dumps(FIND1, ensure_ascii=False))
dump()


# ── 측정 도구 ───────────────────────────────────────────────────────────
def run(mode, seed, force_w=None, perm=None, lam_override=None, tag=""):
    holder = {}

    def _f():
        m = Mixture(seed=seed)
        m.POOL_MODE = mode
        if force_w is not None:
            m.FORCE_W = dict(force_w)
        if perm is not None:
            m.PERM_SEED = int(perm)
        if lam_override is not None:
            m.LAM_OVERRIDE = dict(lam_override)
        holder["m"] = m
        return m
    ts = time.time()
    sc = evaluate(_f, D, T=T)
    board = float(D.pooled(sc, T=T))
    rep = getattr(holder.get("m"), "pool_report", {})
    say(f"  {tag or mode} 씨앗 {seed} 판 {board:.6f} "
        f"아이돌 {sc.get('아이돌', float('nan')):.4f} ({time.time()-ts:.0f}s)")
    return sc, board, rep


# ── 배선 검사 ───────────────────────────────────────────────────────────
say("배선 검사 ① --- off 모드가 챔피언과 같은가")
sc0, b0, rep0 = run("off", 0, tag="배선① off")
ulp = (b0 - EXPECT_POOLED_K1_S0) / math.ulp(EXPECT_POOLED_K1_S0)
same12 = {d: (sc0.get(d) == EXPECT_K1_S0[d]) for d in EXPECT_K1_S0}
WIRE = {"① off 를 껐을 때 판이 챔피언과 같은가": {
    "판": b0,
    "기대 판(dose896.EXPECT_POOLED_K1_S0 에서 **읽음** · 손 전사 아님)":
        EXPECT_POOLED_K1_S0,
    "부동소수 정확일치": b0 == EXPECT_POOLED_K1_S0,
    "차(ULP)": ulp, "통과(|ULP| ≤ 8)": abs(ulp) <= ULP_TOL,
    "소수 넷째 자리까지 같은가": round(b0, 4) == round(EXPECT_POOLED_K1_S0, 4),
    "12도메인 정확일치(ruler890.EXPECT_K1_S0 에서 읽음)": all(same12.values()),
    "어긋난 도메인": [d for d, v in same12.items() if not v],
}}
say(json.dumps(WIRE["① off 를 껐을 때 판이 챔피언과 같은가"], ensure_ascii=False))
assert abs(ulp) <= ULP_TOL, "🔴 off 모드가 챔피언과 다르다 --- 중단"
assert all(same12.values()), "🔴 12도메인이 정본과 다르다 --- 중단"

say("배선 검사 ② --- 심은 결함 둘이 발화하나")
W_CONST = {d: 1.0 for d in DOMS}
W_NOIDOL = {d: (1e-6 if d == "아이돌" else 1.0) for d in DOMS}
sc_c, b_c, rep_c = run("force", 0, force_w=W_CONST, tag=CONST)
sc_n, b_n, rep_n = run("force", 0, force_w=W_NOIDOL, tag=NOIDOL)
WIRE["② 심은 결함이 발화하나"] = {
    "ㄱ 전 도메인 w=1.0 상수": {
        "판": b_c, "A0 대비 Δ": b_c - b0, "발화(판이 움직였다)": b_c != b0,
        "도메인 Δ": {d: round(sc_c.get(d, float("nan")) - sc0.get(d, float("nan")), 6)
                  for d in DOMS},
        "🔴 이 팔은 눈금 대조군이기도 하다": (
            "질량만 Σnw=Σn 으로 맞추고 **구성은 안 바꾼다**. 챔피언의 실효 가중은 "
            "만화 0.253·영화 0.2·세계애니 0.628 때문에 총 질량이 더 작다 --- "
            "HistGradientBoosting 의 l2_regularization 은 그 눈금에 민감하다"),
    },
    "ㄴ 아이돌 w≈0": {
        "판": b_n, "A0 대비 Δ": b_n - b0,
        "아이돌 ρ": sc_n.get("아이돌"), "A0 아이돌 ρ": sc0.get("아이돌"),
        "아이돌 Δ": sc_n.get("아이돌", float("nan")) - sc0.get("아이돌", float("nan")),
        "발화(아이돌이 움직였다)": sc_n.get("아이돌") != sc0.get("아이돌"),
    },
}
say(json.dumps(WIRE["② 심은 결함이 발화하나"], ensure_ascii=False))
assert b_c != b0, "🔴 상수 가중이 판을 안 움직인다 --- 집계기가 모형에 안 닿는다"
assert sc_n.get("아이돌") != sc0.get("아이돌"), \
    "🔴 아이돌 가중을 0 으로 해도 아이돌이 안 움직인다 --- 중단"

say("배선 검사 ③ --- 가중 벡터 합")
_w = rep_c.get("가중 몫(합=1)", {})
_s = float(sum(_w.values())) if _w else float("nan")
WIRE["③ 도메인 가중 벡터를 찍는다 --- 합이 1 인가"] = {
    "상수 팔의 가중 몫": {d: round(v, 8) for d, v in _w.items()},
    "합(반올림 없이 더한 값)": _s, "합 == 1 (1e-12)": abs(_s - 1.0) < 1e-12,
    "Σ nᵈ·w_d": rep_c.get("Σ nᵈ·w_d"), "Σ nᵈ": rep_c.get("Σ nᵈ"),
    "둘이 같은가(1e-6)": abs(float(rep_c.get("Σ nᵈ·w_d", 0))
                        - float(rep_c.get("Σ nᵈ", 1))) < 1e-6,
    "도메인 수": len(_w),
}
say(json.dumps(WIRE["③ 도메인 가중 벡터를 찍는다 --- 합이 1 인가"], ensure_ascii=False))
assert _w and abs(_s - 1.0) < 1e-12, "🔴 가중 합이 1 이 아니다"
assert len(_w) == N_DOM, "🔴 가중 벡터가 12칸이 아니다"
REPORT["2. 배선 검사 셋(측정 전에 닫는다)"] = WIRE
dump()


# ── 본 측정 ────────────────────────────────────────────────────────────
say("본 측정 --- 여섯 팔 × 씨앗 3")
RES = {A0: {"POOL_MODE": "off", "씨앗": {0: {"판": b0, "ρ": sc0}},
            "학습 보고(씨앗0)": rep0},
       CONST: {"POOL_MODE": "force", "씨앗": {0: {"판": b_c, "ρ": sc_c}},
               "학습 보고(씨앗0)": rep_c},
       NOIDOL: {"POOL_MODE": "force", "씨앗": {0: {"판": b_n, "ρ": sc_n}},
                "학습 보고(씨앗0)": rep_n}}
for name, mode in ARMS:
    RES.setdefault(name, {"POOL_MODE": mode, "씨앗": {}})
    for s in SEEDS:
        if s in RES[name]["씨앗"]:
            continue
        if left() < 400:
            RES[name].setdefault("🔴 못 잰 씨앗", []).append(s)
            say(f"  예산 부족 --- {name} 씨앗 {s} **안 쟀다**")
            continue
        sc, b, rep = run(mode, s, tag=name)
        RES[name]["씨앗"][s] = {"판": b, "ρ": sc}
        if s == 0:
            RES[name]["학습 보고(씨앗0)"] = rep
    dump()
REPORT["6. 팔별 원자료"] = RES


def paired(arm, base=A0):
    ss = sorted(set(RES[arm]["씨앗"]) & set(RES[base]["씨앗"]))
    if not ss:
        return {"🔴 못 잼": "겹치는 씨앗이 없다"}
    d = [RES[arm]["씨앗"][s]["판"] - RES[base]["씨앗"][s]["판"] for s in ss]
    lv = [RES[arm]["씨앗"][s]["판"] for s in ss]
    dom = {}
    for k in DOMS:
        v = np.array([RES[arm]["씨앗"][s]["ρ"].get(k, np.nan)
                      - RES[base]["씨앗"][s]["ρ"].get(k, np.nan) for s in ss], float)
        dom[k] = float(np.nanmean(v)) if np.isfinite(v).any() else float("nan")
    n = len(ss)
    sd = float(np.std(d, ddof=1)) if n > 1 else float("nan")
    lvsd = float(np.std(lv, ddof=1)) if n > 1 else float("nan")
    se = (sd / math.sqrt(n)) if n > 1 else float("nan")
    m = float(np.mean(d))
    contrib = {k: float(dom[k] * W[k] / TOT) for k in dom}
    ssum = float(np.nansum(list(contrib.values())))
    order = sorted(contrib, key=lambda z: -abs(contrib[z])
                   if np.isfinite(contrib[z]) else 0)
    worst = {k: float(np.mean([RES[arm]["씨앗"][s]["ρ"].get(k, np.nan) for s in ss]))
             for k in DOMS}
    wk = min(worst, key=lambda z: worst[z])
    return {
        "씨앗": ss, "씨앗별 판 Δ": {str(s): round(x, 7) for s, x in zip(ss, d)},
        "짝 판 Δ": m, "짝SD": sd, "짝SE": se,
        "|Δ|/SE": (abs(m) / se) if (se and np.isfinite(se) and se > 0) else None,
        "양수": f"{int(sum(1 for x in d if x > 0))}/{n}",
        "수준SD": lvsd,
        "짝SD/수준SD(890 병기 의무)": (sd / lvsd) if (lvsd and np.isfinite(lvsd)
                                                and lvsd > 0) else None,
        "🔴 문턱 +0.00353 을 넘나": bool(m >= THRESH),
        "판정": ("채택 제안" if (m >= THRESH and all(x > 0 for x in d))
               else ("기각" if m <= -THRESH else "🔴 이 자를 못 넘었다")),
        "도메인 Δ 12칸(|Δ| 내림차순)": {k: round(dom[k], 6)
                              for k in sorted(dom, key=lambda z: -abs(dom[z])
                                              if np.isfinite(dom[z]) else 0)},
        "도메인 판 기여(Δ×정규가중)": {k: round(contrib[k], 7) for k in order},
        "기여 합": ssum, "🔴 기여 합 == 짝 판 Δ 인가(1e-9)": abs(ssum - m) < 1e-9,
        "아이돌 도메인 Δ": round(dom.get("아이돌", float("nan")), 6),
        "아이돌 판 기여": round(contrib.get("아이돌", float("nan")), 7),
        "아이돌 기여 순위(|기여| 내림차순 · 12칸 중)": 1 + order.index("아이돌"),
        "이 팔의 최악 도메인(씨앗평균 ρ)": {"도메인": wk, "ρ": round(worst[wk], 6)},
        "이 팔의 12도메인 ρ(씨앗평균)": {k: round(worst[k], 6) for k in sorted(worst)},
    }


REPORT["3. 판정 --- A0 대비 짝"] = {a: paired(a) for a in RES if a != A0}
REPORT["3b. 상수 팔 대비(눈금 교락을 뗀다 · 씨앗0만)"] = {
    a: paired(a, base=CONST) for a, m in ARMS if m in ("table", "uncert", "dro")}
REPORT["3c. A1 대비(영화 교락을 뗀다)"] = {
    a: paired(a, base=A1) for a, m in ARMS
    if m in ("uncert", "dro", "shrink", "stack")}
dump()


# ── 위약 ───────────────────────────────────────────────────────────────
say("위약 --- 배운 벡터의 **값 집합은 그대로 두고 배정만 흩는다**")
PLAC = {}


def shuffle_map(vec, draw):
    rng = np.random.default_rng(draw)
    keys = sorted(vec)
    perm = list(rng.permutation(keys))
    return {k: float(vec[p]) for k, p in zip(keys, perm)}


# 학습 가중 층 위약 --- A2
rep_a2 = RES.get(A2, {}).get("학습 보고(씨앗0)", {})
vec_a2 = rep_a2.get("학습 가중 w(정규화 뒤 · Σnw=Σn)")
rows = []
if vec_a2:
    for dr in PLACEBO_DRAWS:
        if left() < 200:
            rows.append({"뽑기": dr, "🔴 못 함": "예산 부족"})
            continue
        shuf = shuffle_map(vec_a2, dr)
        sc, b, _ = run("force", 0, force_w=shuf, tag=f"위약 A2 {dr}")
        rows.append({"뽑기": dr, "재배정 w": shuf, "판": b, "A0 대비 Δ": b - b0,
                     "아이돌 Δ": sc.get("아이돌", float("nan"))
                     - sc0.get("아이돌", float("nan"))})
else:
    rows.append({"🔴 못 함": "A2 의 학습 벡터가 없다"})
_ds = [r["A0 대비 Δ"] for r in rows if "A0 대비 Δ" in r]
PLAC[A2] = {"뽑기": rows, "평균 Δ": float(np.mean(_ds)) if _ds else None,
            "최대 |Δ|": float(np.max(np.abs(_ds))) if _ds else None}
dump()

# 예측 층 위약 --- A4 의 λ
rep_a4 = RES.get(A4, {}).get("학습 보고(씨앗0)", {})
vec_a4 = rep_a4.get("λ")
rows = []
if vec_a4:
    for dr in PLACEBO_DRAWS:
        if left() < 200:
            rows.append({"뽑기": dr, "🔴 못 함": "예산 부족"})
            continue
        shuf = shuffle_map(vec_a4, dr + 1)
        sc, b, _ = run("shrink", 0, lam_override=shuf, tag=f"위약 A4 λ {dr}")
        rows.append({"뽑기": dr, "재배정 λ": shuf, "판": b, "A0 대비 Δ": b - b0})
else:
    rows.append({"🔴 못 함": "A4 의 λ 가 없다"})
_ds = [r["A0 대비 Δ"] for r in rows if "A0 대비 Δ" in r]
PLAC[A4] = {"뽑기": rows, "평균 Δ": float(np.mean(_ds)) if _ds else None,
            "최대 |Δ|": float(np.max(np.abs(_ds))) if _ds else None}
REPORT["4. 위약(배정만 흩는다)"] = PLAC
dump()


# ── 라벨 순열 selectivity ───────────────────────────────────────────────
say("라벨 순열 selectivity --- 학습 라벨을 섞어도 같은 벡터가 나오나")


def sp_pair(a, b, keys):
    x = np.array([a[k] for k in keys], float)
    y = np.array([b[k] for k in keys], float)
    if len(np.unique(x)) < 2 or len(np.unique(y)) < 2:
        return None
    x = rankdata(x); y = rankdata(y)
    x = x - x.mean(); y = y - y.mean()
    den = float(np.sqrt((x * x).sum() * (y * y).sum()))
    return float((x * y).sum() / den) if den > 0 else None


TD = train_data()
SEL = {}
for arm, mode in [(A2, "uncert"), (A3, "dro")]:
    real = (RES.get(arm, {}).get("학습 보고(씨앗0)", {})
            .get("학습 가중 w(정규화 뒤 · Σnw=Σn)"))
    if not real:
        SEL[arm] = {"🔴 못 함": "실제 벡터가 없다"}
        continue
    rows = []
    for ps in PERM_DRAWS:
        if left() < 120:
            rows.append({"뽑기": ps, "🔴 못 함": "예산 부족"})
            continue
        ts = time.time()
        m = Mixture(seed=0)
        m.POOL_MODE = mode
        m.PERM_SEED = ps
        m.pool_report = {}
        capped = m._traincap(TD)
        ntr = {d: int(len(capped.dom[d][2])) for d in sorted(capped.dom)}
        w = m._normalize(m._learn(TD, ntr), ntr)
        r = sp_pair(real, w, sorted(real))
        rows.append({"뽑기": ps, "가중": {d: round(v, 6) for d, v in sorted(w.items())},
                     "실제와의 스피어만": r, "초": round(time.time() - ts, 1)})
        say(f"  {arm} 라벨순열 {ps} → ρ(실제, 순열) = {r}")
    rs = [x["실제와의 스피어만"] for x in rows if x.get("실제와의 스피어만") is not None]
    SEL[arm] = {"실제 가중": real, "순열 뽑기": rows,
                "평균 ρ(실제,순열)": float(np.mean(rs)) if rs else None,
                "🔴 라벨을 안 읽고 있나(평균 ρ > 0.8 이면 그렇다)":
                    bool(rs and float(np.mean(rs)) > 0.8),
                "무엇을 섞었나": "학습 라벨만 --- 유보는 만지지도 않는다. "
                            "바깥 적합은 진짜 라벨로 하고 **가중을 정하는 단계만** 섞는다"}
    dump()

for arm, mode in [(A4, "shrink"), (A5, "stack")]:
    real = RES.get(arm, {}).get("학습 보고(씨앗0)", {}).get("λ")
    if not real:
        SEL[arm] = {"🔴 못 함": "실제 λ 가 없다"}
        continue
    rows = []
    for ps in PERM_DRAWS[:2]:
        if left() < 250:
            rows.append({"뽑기": ps, "🔴 못 함": "예산 부족 --- 안 쟀다"})
            continue
        sc, b, rep = run(mode, 0, perm=ps, tag=f"선택성 {arm} 순열 {ps}")
        lam = rep.get("λ", {})
        rows.append({"뽑기": ps, "λ": lam, "판": b, "A0 대비 Δ": b - b0,
                     "실제와의 스피어만": sp_pair(real, lam, sorted(real))
                     if lam else None})
    rs = [x["실제와의 스피어만"] for x in rows if x.get("실제와의 스피어만") is not None]
    SEL[arm] = {"실제 λ": real, "순열 뽑기": rows,
                "평균 ρ(실제,순열)": float(np.mean(rs)) if rs else None,
                "🔴 라벨을 안 읽고 있나(평균 ρ > 0.8 이면 그렇다)":
                    bool(rs and float(np.mean(rs)) > 0.8)}
    dump()
REPORT["5. 라벨 순열 selectivity"] = SEL


# ── 누출 · 요약 ────────────────────────────────────────────────────────
REPORT["7. 🔴 유보 누출 --- 팔마다 명시"] = {
    A0: "안 봄(챔피언 그대로)",
    A1: "🔴 유보의 **행 수**만 봤다(라벨 y 는 한 번도 안 봄). 챔피언 TRAINW 가 하던 "
        "그대로다(노트 514: '유보 행 수만 쓰고 라벨은 안 본다 --- 채점 목적함수의 "
        "정의다'). 이것조차 누출로 보는 독자는 A1 을 빼고 읽어라",
    A2: "유보를 한 비트도 안 봄 --- σ̂ 는 학습 안쪽 검증(2024~2025)에서만 왔다",
    A3: "유보를 한 비트도 안 봄 --- q 는 학습 안쪽 검증에서만 왔다",
    A4: "유보를 한 비트도 안 봄 --- κ·λ 는 학습 안쪽 검증에서만 왔다",
    A5: "유보를 한 비트도 안 봄 --- λ 12칸은 학습 안쪽 검증에서만 왔다",
    "구조적 방어": "fit(train) 이 받는 Data 에는 유보 행이 **존재하지 않는다**"
                "(lab/harness.py:305 가 yr<T 로 자른다). 그래도 fit 첫 줄에서 "
                "전 도메인 max(yr) < 2025.0 을 단언한다",
    "각 팔이 fit 에서 본 최대 연도":
        {a: RES.get(a, {}).get("학습 보고(씨앗0)", {})
            .get("누출 방어", {}).get("본 최대 연도") for a, _ in ARMS},
}

SUM = {}
for a, _m in ARMS:
    if a == A0:
        continue
    p = REPORT["3. 판정 --- A0 대비 짝"].get(a, {})
    SUM[a] = {"짝 판 Δ": p.get("짝 판 Δ"), "양수": p.get("양수"),
              "짝SE": p.get("짝SE"), "판정": p.get("판정"),
              "아이돌 도메인 Δ": p.get("아이돌 도메인 Δ"),
              "아이돌 판 기여": p.get("아이돌 판 기여")}
base_idol_contrib = None
REPORT["8. 한 눈에"] = {
    "문턱": THRESH, "씨앗": list(SEEDS),
    "🔴 문턱을 넘은 팔": [a for a in SUM
                   if SUM[a].get("짝 판 Δ") is not None
                   and SUM[a]["짝 판 Δ"] >= THRESH],
    "팔별": SUM,
    "🔴 아이돌이 판에서 차지하는 몫은 안 변한다": (
        f"판 정규가중 {round(W['아이돌']/TOT, 5)} --- 이 팔은 **자를 안 만졌다**. "
        f"아이돌 하나로 문턱을 넘으려면 도메인 Δ 가 "
        f"{round(THRESH / (W['아이돌']/TOT), 4)} 필요하다"),
    "씨앗 수 한계": "3씨앗이다. 노트 890 의 12씨앗 자(2σ=0.0011)보다 둔하다",
}
dump("끝")
say(json.dumps(REPORT["8. 한 눈에"], ensure_ascii=False))
say("끝")


# ── 2단계 ──────────────────────────────────────────────────────────────
#: 🔴 **1단계 결과를 본 뒤에 붙인 코드다**(사전등록 §5.5 · 사후임을 못박는다).
#: 판정 규칙은 안 바꾼다 --- §5 의 *"문턱을 넘는 팔이 나오면 그 팔만 씨앗 3·4·5 를
#: 더 돌린다"* 를 **이행**하고 위약 뽑기를 **늘리기만** 한다.
#: `NN908C_STAGE=2` 로만 돈다. 산출물은 `runners/out908c_seed6.json`(1단계 파일을
#: 덮지 않는다 --- 1단계는 그 자체로 증거물이다).
if os.environ.get("NN908C_STAGE") == "2":
    OUT2 = Path(ROOT / "runners/out908c_seed6.json")
    #: 1단계 산출물은 **증거물이라 안 덮는다** --- 2단계는 `NN908C_OUT` 을 딴 데로
    #: 돌리고 `NN908C_BUDGET=1` 로 1단계 측정을 건너뛴 채 돈다(배선 검사 셋은
    #: 예산 게이트 앞이라 그대로 다시 닫힌다 --- 재현 확인을 겸한다).
    prev = json.loads(Path(ROOT / "runners/out908c_pooling.json").read_text())
    for nm in (A0, A2):
        src = prev["6. 팔별 원자료"][nm]
        RES[nm] = {"POOL_MODE": src.get("POOL_MODE"),
                   "씨앗": {int(s): v for s, v in src["씨앗"].items()},
                   "학습 보고(씨앗0)": src.get("학습 보고(씨앗0)")}
    say(f"2단계 --- 1단계에서 읽어 온 씨앗: "
        f"{sorted(RES[A0]['씨앗'])} / {sorted(RES[A2]['씨앗'])}")
    _rb = RES[A0]["씨앗"][0]["판"]
    R2_WIRE = {"1단계 A0 씨앗0 판(산출물에서 읽음)": _rb,
               "2단계에서 다시 잰 배선① 판": b0,
               "🔴 재현되나(부동소수 정확일치)": _rb == b0,
               "차": _rb - b0}
    say(json.dumps(R2_WIRE, ensure_ascii=False))
    R2 = {
        "노트": "908-ㄷ 2단계",
        "🔴 사후임을 못박는다": (
            "이 산출물은 1단계(out908c_pooling.json)를 **읽고 나서** 만든 것이다. "
            "사전등록 §5.5 가 그 사실과 예측을 미리 적었다. 판정 규칙은 불변"),
        "사전등록 sha256(2단계 절을 붙인 뒤)": sha(PREREG),
        "사전등록 sha256(1단계 실행 때 · 산출물에서 읽음)":
            prev.get("사전등록", {}).get("sha256"),
        "코드 sha256(1단계 실행 때 · 산출물에서 읽음)":
            prev.get("코드 sha256", {}).get("runners/nn908c_pooling.py"),
        "코드 sha256(지금 · 2단계를 붙인 뒤)": sha(__file__),
        "lab/mixture908.py sha256": sha(ROOT / "lab/mixture908.py"),
        "1단계 3씨앗 A2": prev["3. 판정 --- A0 대비 짝"][A2],
        "1단계 재현 확인(배선①)": R2_WIRE,
    }
    SEEDS2 = (3, 4, 5)
    S2 = {A0: {}, A2: {}}
    for nm, md in [(A0, "off"), (A2, "uncert")]:
        for s in SEEDS2:
            sc, b, rep = run(md, s, tag=f"2단계 {nm}")
            S2[nm][s] = {"판": b, "ρ": sc}
            if nm == A2 and s == 3:
                R2["A2 학습 가중(씨앗3)"] = rep.get("학습 가중 w(정규화 뒤 · Σnw=Σn)")
        OUT2.write_text(json.dumps(R2, ensure_ascii=False, indent=1, default=_j))
    for nm in (A0, A2):
        for s, v in S2[nm].items():
            RES[nm]["씨앗"][s] = v
    R2["6씨앗 A2(A0 대비 짝)"] = paired(A2)
    R2["씨앗별 판(6씨앗)"] = {
        nm: {str(s): RES[nm]["씨앗"][s]["판"] for s in sorted(RES[nm]["씨앗"])}
        for nm in (A0, A2)}

    # 위약을 씨앗 1 로 넓힌다
    vec = (RES[A2].get("학습 보고(씨앗0)", {})
           .get("학습 가중 w(정규화 뒤 · Σnw=Σn)"))
    b0s1 = RES[A0]["씨앗"][1]["판"]
    rows2 = []
    for dr in PLACEBO_DRAWS:
        shuf = shuffle_map(vec, dr)
        sc, b, _ = run("force", 1, force_w=shuf, tag=f"2단계 위약 A2 씨앗1 {dr}")
        rows2.append({"뽑기": dr, "판": b, "A0(씨앗1) 대비 Δ": b - b0s1})
    old = prev["4. 위약(배정만 흩는다)"][A2]["뽑기"]
    alld = ([r["A0 대비 Δ"] for r in old if "A0 대비 Δ" in r]
            + [r["A0(씨앗1) 대비 Δ"] for r in rows2])
    eff = R2["6씨앗 A2(A0 대비 짝)"]["짝 판 Δ"]
    R2["위약 --- 6뽑기 2씨앗"] = {
        "씨앗0 뽑기(1단계)": old, "씨앗1 뽑기(2단계)": rows2,
        "여섯 Δ": alld, "평균": float(np.mean(alld)),
        "SD": float(np.std(alld, ddof=1)), "최대": float(np.max(alld)),
        "효과(6씨앗 짝 Δ)": eff,
        "🔴 판정 규칙 --- 위약 평균 < 효과의 절반인가":
            bool(abs(float(np.mean(alld))) < abs(eff) / 2),
        "효과 / 위약SD": float(eff / np.std(alld, ddof=1)),
        "위약 뽑기 중 효과보다 큰 것": int(sum(1 for x in alld if x >= eff)),
    }
    R2["🔴 6씨앗 판정"] = {
        "짝 판 Δ": eff, "문턱": THRESH,
        "넘나": bool(eff >= THRESH),
        "양수": R2["6씨앗 A2(A0 대비 짝)"]["양수"],
        "판정": R2["6씨앗 A2(A0 대비 짝)"]["판정"],
        "2단계 예측(사전등록 §5.5) 대 실측": {
            "예측": "+0.001 ~ +0.005 로 **줄어든다**", "실측": eff,
            "예측 구간 안인가": bool(0.001 <= eff <= 0.005),
            "3씨앗보다 줄었나": bool(eff < prev["3. 판정 --- A0 대비 짝"][A2]["짝 판 Δ"]),
        },
    }
    R2["끝 시각(UTC)"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    OUT2.write_text(json.dumps(R2, ensure_ascii=False, indent=1, default=_j))
    say(json.dumps(R2["🔴 6씨앗 판정"], ensure_ascii=False))
    say(json.dumps(R2["위약 --- 6뽑기 2씨앗"]["🔴 판정 규칙 --- 위약 평균 < 효과의 절반인가"],
                   ensure_ascii=False))
    say("2단계 끝")
