# -*- coding: utf-8 -*-
"""노트 895 · 4단계 --- **A·B·C 채점**. 요청 0건.

사전등록: `docs/prereg_895_textmass.md` v3 · 원장 「**사전등록** 텍스트 존재량의 자」.
정답지: `runners/out895_truth.json`(v2b·느슨) · 자: `out895_r1/r3wiki/r3namu/r2full`.

🔴 **구간법은 사전등록대로 BCa 하나다** --- `lab/pairboot.cluster_boot`(규약 47 ·
B=10,000 · 씨앗 895). 작품이 단독 클러스터이므로 **⚠ 무군집**(행 부트와 동일 · 폭 과소
방향)을 병기한다. 코드가 `percentile(폴백)` 을 돌려주면 **그 문자열을 그대로 산출물에
적는다** --- 폴백을 조용히 BCa 라 부르지 않는다.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from lab.pairboot import cluster_boot                      # noqa: E402  규약 47

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out895_score.json"
KO = ("AniList native(한글)", "AniList synonyms(한글)")
FIELD = "v2b·느슨"            # 정답지 정본
B_PASS = None                 # 아래에서 정답지 산출물의 통과선을 **읽어** 채운다


# ── 통계 ────────────────────────────────────────────────────────────
def rank(xs):
    xs = np.asarray(xs, float)
    order = np.argsort(xs, kind="mergesort")
    r = np.empty(len(xs))
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = rank(a), rank(b)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def auc(pos, neg, tie=0.5):
    if not len(pos) or not len(neg):
        return float("nan")
    p, n = np.asarray(pos, float)[:, None], np.asarray(neg, float)[None, :]
    return float(((p > n).sum() + tie * (p == n).sum()) / (p.size * n.size))


def partial_spearman(y, x, ctrls):
    """순위 잔차 회귀 편상관. y·x 를 순위화하고 통제(순위·원핫)로 회귀해 잔차 상관."""
    Y, X = rank(y), rank(x)
    C = np.column_stack([np.ones(len(Y))] + list(ctrls))
    def resid(v):
        beta, *_ = np.linalg.lstsq(C, v, rcond=None)
        return v - C @ beta
    ry, rx = resid(Y), resid(X)
    if ry.std() == 0 or rx.std() == 0:
        return float("nan")
    return float(np.corrcoef(ry, rx)[0, 1])


def boot(stat_of_idx, n, seed=895):
    """규약 47 BCa. 작품이 단독 클러스터 --- 무군집 병기 의무."""
    clusters = [np.array([i]) for i in range(n)]
    th, lo, hi, kind = cluster_boot(lambda idx: stat_of_idx(idx.astype(int)),
                                    clusters, B=10_000, seed=seed)
    return {"점추정": round(float(th), 4), "lo": round(float(lo), 4),
            "hi": round(float(hi), 4), "구간 종류": kind,
            "⚠ 무군집": "작품 단독 클러스터 = 행 부트와 동일(폭 과소 방향 · 규약 47 병기)"}


# ── 자료 ────────────────────────────────────────────────────────────
def load():
    t = json.loads((ROOT / "runners/out895_truth.json").read_text(encoding="utf-8"))
    works = {w["key"]: w for w in t["작품"]}
    R = {}
    for f, key in (("r1", "r1"), ("r3wiki", "r3wiki"),
                   ("r3namu", "r3namu"), ("r2full", "r2")):
        R[key] = json.loads((ROOT / f"runners/out895_{f}.json").read_text(encoding="utf-8"))["값"]
    B = t["🔴 B 의 통과선"]
    return works, R, t, B


def ruler_values(works, R):
    """자마다 {key: 점수 or None(판정 불가)}. 🔴 판정 불가를 0 으로 읽지 않는다."""
    V = {}
    V["R1 정확구문(네이버 news)"] = {
        k: (v["total"] if v["상태"] == "잼" else None) for k, v in R["r1"].items()}
    V["R2 베이스모델 탐침"] = {
        k: (v["안다"] if v["상태"] == "잼" else None) for k, v in R["r2"].items()}
    V["R3a 나무위키 바이트"] = {
        k: (v["바이트"] if v["상태"] == "잼" else None) for k, v in R["r3namu"].items()}
    V["R3b 위키백과 바이트"] = {
        k: (v["바이트"] if v["상태"] == "잼" else None) for k, v in R["r3wiki"].items()}
    comb = {}
    for k in V["R3a 나무위키 바이트"]:
        a, b = V["R3a 나무위키 바이트"][k], V["R3b 위키백과 바이트"].get(k)
        comb[k] = None if (a is None or b is None) else math.log1p(a) + math.log1p(b)
    V["R3 문서 존재·길이(나무+위키)"] = comb
    return V


def grade(name, vals, works, thresh):
    """A·B·C 한 자를 채점한다. **모집단은 사전등록 그대로.**"""
    pop = [k for k in vals if k in works]
    real = [k for k in pop if not works[k]["음성"] and works[k]["질의출처"] in KO]
    fake = [k for k in pop if works[k]["음성"]]
    rep = {"자": name, "모집단": {"한글 질의 실물": len(real), "음성": len(fake)}}

    # ── A ────────────────────────────────────────────────────────
    ra = [k for k in real if vals[k] is not None]
    fa = [k for k in fake if vals[k] is not None]
    rep["A · 판정 불가"] = {"실물": len(real) - len(ra), "음성": len(fake) - len(fa)}
    if ra and fa:
        rv = [vals[k] for k in ra]
        fv = [vals[k] for k in fa]
        arr = np.array(rv + fv, float)
        nr = len(rv)
        rep["A"] = {
            "AUC(타이 0.5)": round(auc(rv, fv), 4),
            "🔴 AUC(타이는 최악 순위 = 실물에 불리)": round(auc(rv, fv, tie=0.0), 4),
            "부트": boot(lambda idx: auc(arr[idx[idx < nr]], arr[idx[idx >= nr]]),
                        len(arr)) if len(arr) > 5 else None,
            "보조 · max(음성)": round(float(max(fv)), 4),
            "보조 · 실물 10분위수": round(float(np.percentile(rv, 10)), 4),
            "보조 통과": bool(max(fv) < np.percentile(rv, 10)),
            "실물 중앙값": round(float(np.median(rv)), 4),
            "음성 중앙값": round(float(np.median(fv)), 4),
        }
        # 🔴 부트는 층화(실물/음성 각각)로 다시 --- 위 한 줄은 섞인 재표집이라 편향된다
        rep["A"]["부트(층화 · 정본)"] = strat_boot_auc(rv, fv)
        a_auc = rep["A"]["AUC(타이 0.5)"]
        a_lo = rep["A"]["부트(층화 · 정본)"]["lo"]
        rep["A 통과"] = bool(a_auc >= 0.85 and a_lo > 0.70)
        # 🔴 M8(티처 #58) --- 62 인가 58 인가. **정본은 62**(근거는 아래 필드) ·
        #    58(정답지 값 있는 부분집합)판을 **지우지 말고 나란히** 낸다.
        rep["🔴 A · 분모 62 대 58 병기"] = a_denoms(ra, fa, vals, works)
    else:
        rep["A"] = "판정 불가(값이 없다)"
        rep["A 통과"] = None

    # ── B ────────────────────────────────────────────────────────
    bkeys = [k for k in ra + fa if works[k][FIELD] is not None]
    if len(bkeys) > 5:
        x = np.array([vals[k] for k in bkeys], float)
        y = np.array([works[k][FIELD] for k in bkeys], float)
        rep["B"] = {"n": len(bkeys), "스피어만": round(spearman(x, y), 4),
                    "부트": boot(lambda idx: spearman(x[idx], y[idx]), len(x)),
                    "통과선": thresh}
        rep["B 통과"] = bool(rep["B"]["스피어만"] >= thresh)
        # 실물만 / 음성 제외판도 병기(조항 60)
        rk = [k for k in bkeys if not works[k]["음성"]]
        if len(rk) > 5:
            rep["B · 실물만"] = {"n": len(rk), "스피어만": round(spearman(
                [vals[k] for k in rk], [works[k][FIELD] for k in rk]), 4)}
    else:
        rep["B"] = "판정 불가"
        rep["B 통과"] = None

    # ── C ── 편상관: 실물만(음성엔 층·원산국이 없다) ─────────────
    ck = [k for k in ra if works[k][FIELD] is not None]
    if len(ck) > 8:
        x = np.array([vals[k] for k in ck], float)
        y = np.array([works[k][FIELD] for k in ck], float)
        w = rank([works[k]["어절수"] for k in ck])
        kr = np.array([1.0 if works[k]["country"] == "KR" else 0.0 for k in ck])
        s1 = np.array([1.0 if works[k]["층"] == "상" else 0.0 for k in ck])
        s2 = np.array([1.0 if works[k]["층"] == "중" else 0.0 for k in ck])
        C = [w, kr, s1, s2]
        rep["C"] = {
            "n": len(ck),
            "통제": "질의 어절수(순위) · 원산국 KR/비KR · 층 상/중(하가 기준)",
            "원산국 분포": dict(Counter(works[k]["country"] for k in ck)),
            "무편상관 스피어만(참고)": round(spearman(x, y), 4),
            "🔴 편상관": round(partial_spearman(y, x, C), 4),
            "부트": boot(lambda idx: partial_spearman(
                y[idx], x[idx], [c[idx] for c in C]), len(x)),
        }
        lo, hi = rep["C"]["부트"]["lo"], rep["C"]["부트"]["hi"]
        rep["C 통과"] = bool(not (lo <= 0 <= hi))
        rep["C 판정"] = "승" if lo > 0 else ("패" if hi < 0 else "판정 불능")
    else:
        rep["C"] = "판정 불가(n 부족)"
        rep["C 통과"] = None

    rep["🔴 A·B·C 셋 다"] = bool(rep.get("A 통과") and rep.get("B 통과") and rep.get("C 통과"))
    return rep


def a_denoms(ra, fa, vals, works):
    """🔴 **A 의 분모를 못 박는다 --- 62 다.** (티처 #58 M8 · 사전등록 문면이 스스로 어긋났다)

    사전등록 180행은 「한글 질의 실물 **62**(값 있음 58) + 음성 20」, 208행은 「정본 채점
    모집단 = 한글 질의 실물 **58** + 음성 20」이라 적었다. **정본은 62 다** ---

      ① 그 4건은 **정답지의 결측**이지 자의 결측이 아니다. A 가 묻는 것은 *"자가 음성을
         가르는가"* 라서 **자의 값만 있으면 재진다**. 정답지 값으로 4건을 떨어뜨리면
         **결과에 조건을 붙여 표본을 고르는 것**(selection on outcome)이고, 그것은 v3 이
         「고친 것 ①」에서 스스로 이름 붙여 피한 바로 그 병이다.
      ② 180행이 **정의**이고 208행은 그 요약이다 --- 180행은 62 와 58 을 **둘 다** 적고
         층 27·20·11 · 원산국 KR45·JP12·CN1(합 **62**)로 모집단을 서술한다. 208행의 58 은
         B 의 통과선(천장 n=78)을 이어 적으면서 분모를 옮겨 적은 것이다.
      ③ 구현이 그렇게 서 있다 --- `score895.py:118` 은 62, B(:152)·C(:170)는 58.

    🔴 **그래서 조항 60**: A 의 분모(62)와 B·C·천장의 분모(58 + 음성 20 = 78)는 **다른
    수다.** 두 수를 한 문장에 잇지 마라. 아래에 **두 판을 다 낸다** --- 58 판이 궁금한
    것은 *"정답지가 있는 칸에서만 보면 자가 달라 보이나"* 이고, 그건 민감도이지 정본이 아니다.
    """
    ra58 = [k for k in ra if works[k][FIELD] is not None]
    rv62, rv58 = [vals[k] for k in ra], [vals[k] for k in ra58]
    fv = [vals[k] for k in fa]
    out = {
        "🔴 정본": "62 (등록 모집단 전수 · 근거는 이 함수의 docstring 과 사전등록 v3 정정 칸)",
        "🔴 조항 60": "A 의 분모 62 와 B·C·천장의 분모 78(=58+20)은 다른 수다 --- 잇지 마라",
    }
    for tag, rvx in (("정본 · 분모 62(자 값 있는 실물 전수)", rv62),
                     ("병기 · 분모 58(정답지 값도 있는 부분집합)", rv58)):
        if not rvx or not fv:
            out[tag] = "판정 불가(값이 없다)"
            continue
        a = round(auc(rvx, fv), 4)
        lo = strat_boot_auc(rvx, fv)["lo"]
        out[tag] = {
            "n(실물)": len(rvx), "n(음성)": len(fv),
            "AUC(타이 0.5)": a,
            "AUC(타이 최악)": round(auc(rvx, fv, tie=0.0), 4),
            "부트(층화) 하한": lo,
            "A 통과(≥0.85 그리고 하한>0.70)": bool(a >= 0.85 and lo > 0.70),
            "양수 비율(=민감도 · 음성이 전부 0 일 때 AUC=0.5+0.5×이 값)":
                f"{sum(1 for v in rvx if v)}/{len(rvx)} = {round(sum(1 for v in rvx if v)/len(rvx), 4)}",
        }
    p62 = out["정본 · 분모 62(자 값 있는 실물 전수)"]
    p58 = out["병기 · 분모 58(정답지 값도 있는 부분집합)"]
    if isinstance(p62, dict) and isinstance(p58, dict):
        out["🔴 판정이 바뀌나"] = (
            "아니다" if p62["A 통과(≥0.85 그리고 하한>0.70)"] == p58["A 통과(≥0.85 그리고 하한>0.70)"]
            else "🔴 바뀐다 --- 분모 하나로 A 판정이 뒤집힌다. 정본(62)을 따르고 이 사실을 원장에 박아라")
    return out


def strat_boot_auc(rv, fv, B=10000, seed=895):
    """실물·음성을 **각각** 재표집한다(A 의 정본 구간). BCa 는 두 군 구조에서
    `cluster_boot` 한 벌로 못 쓰므로 **percentile 을 쓰고 사유를 적는다.**"""
    rng = np.random.default_rng(seed)
    r, f = np.asarray(rv, float), np.asarray(fv, float)
    es = np.array([auc(r[rng.integers(0, len(r), len(r))],
                       f[rng.integers(0, len(f), len(f))]) for _ in range(B)])
    return {"lo": round(float(np.percentile(es, 2.5)), 4),
            "hi": round(float(np.percentile(es, 97.5)), 4),
            "구간 종류": "percentile(층화 2표본)",
            "🔴 폴백 사유": ("AUC 는 실물·음성 **두 표본**의 통계라 `cluster_boot` 의 "
                        "한 벌 재표집(BCa)이 군 비율을 흔들어 편향된다. 사전등록의 "
                        "'퇴화하면 폴백 + 사유 명기' 조항을 적용해 **층화 percentile** 을 "
                        "썼다. B·C 는 사전등록대로 BCa 다.")}


def diagnostics(works, R, V):
    """🔴 채점 뒤에 남는 물음들. **요청 0건.** 조항 60 대로 갈라 적는다."""
    pop = [k for k in V["R3a 나무위키 바이트"] if k in works]
    real = [k for k in pop if not works[k]["음성"] and works[k]["질의출처"] in KO]
    fake = [k for k in pop if works[k]["음성"]]
    namu = V["R3a 나무위키 바이트"]
    wiki = V["R3b 위키백과 바이트"]
    r1 = V["R1 정확구문(네이버 news)"]
    r2 = V["R2 베이스모델 탐침"]
    d = {}

    has = [k for k in real if namu[k] and namu[k] > 0]
    d["🔴 A 가 왜 안 넘는가 --- 특이도는 만점, 민감도가 모자란다"] = {
        "음성 20 중 나무위키 문서 있는 것": sum(1 for k in fake if namu[k] and namu[k] > 0),
        "한글 질의 실물 중 문서 있는 것": f"{len(has)}/{len(real)}",
        "민감도": round(len(has) / len(real), 4),
        "산식": ("음성이 전부 0 이면 AUC = 0.5 + 0.5×민감도 다. **AUC ≥ 0.85 는 민감도 "
               "≥ 0.70 과 같은 말**이고, 실측 민감도가 그 아래다."),
        "AUC 0.85 를 넘기려면 더 필요한 작품 수": max(0, math.ceil(0.70 * len(real)) - len(has)),
        # 🔴 M8 병기 --- 분모를 58(정답지 값 있는 부분집합)로 바꿔 세면 이렇다. 정본은 62.
        "🔴 분모 58 로 세면(병기 · 정본 아님)": {
            "민감도": (lambda r58: f"{sum(1 for k in r58 if namu[k] and namu[k] > 0)}/{len(r58)} = "
                             f"{round(sum(1 for k in r58 if namu[k] and namu[k] > 0)/len(r58), 4)}")(
                [k for k in real if works[k][FIELD] is not None]),
            "⚠": "A 의 정본 분모는 62 다(a_denoms() docstring). 이 줄은 티처 #58 M8 의 병기다",
        },
    }
    miss = [k for k in real if not namu[k]]
    d["나무위키 0 인 실물 21건은 정말 0 인가"] = {
        "n": len(miss),
        "그중 위키백과 문서가 있는 것": sum(1 for k in miss if wiki.get(k)),
        "그중 네이버 정확구문 > 0": sum(1 for k in miss if r1.get(k)),
        "그중 정답지 > 0": sum(1 for k in miss if works[k][FIELD]),
        "🔴 뜻": ("나무위키 404 는 **문서 없음**과 **표제어 불일치**를 못 가른다. "
               "위 셋 중 하나라도 양수면 그 작품엔 한국어 텍스트가 있는데 나무위키 "
               "URL 이 우리 이름과 안 맞은 것일 수 있다 --- **그 칸이 민감도의 상한을 쥔다**."),
        "예시": [{"key": k, "질의": works[k]["질의"], "위키": wiki.get(k),
                "네이버": r1.get(k), "정답지": works[k][FIELD]} for k in miss[:6]],
    }
    hi = sorted([k for k in fake if r1.get(k)], key=lambda k: -r1[k])[:5]
    d["🔴 R1 이 A 에서 죽는 이유 --- 음성 구절이 뉴스에 실제로 있다"] = {
        "음성 20 중 정확구문 > 0": sum(1 for k in fake if r1.get(k)),
        "상위 5": [{"질의": works[k]["질의"], "네이버 news total": r1[k]} for k in hi],
        "실물 10분위수": 0.0 if not real else round(float(np.percentile(
            [r1[k] for k in real if r1[k] is not None], 10)), 4),
        "뜻": ("음성 질의는 **흔한 한국어 어절로 지어진 구절**이라 따옴표를 씌워도 "
              "뉴스 본문에 그대로 등장한다. 정확 구문은 **날조 작품**을 거르지 못한다."),
    }
    d["🔴 나무위키 존재율을 갈라 본다(조항 60)"] = {
        "층": {s: f"{sum(1 for k in real if works[k]['층'] == s and namu[k])}/"
                 f"{sum(1 for k in real if works[k]['층'] == s)}"
              for s in ("상", "중", "하")},
        "원산국": {c: f"{sum(1 for k in real if works[k]['country'] == c and namu[k])}/"
                   f"{sum(1 for k in real if works[k]['country'] == c)}"
                for c in ("KR", "JP", "CN")},
        "질의출처": {s: f"{sum(1 for k in real if works[k]['질의출처'] == s and namu[k])}/"
                   f"{sum(1 for k in real if works[k]['질의출처'] == s)}" for s in KO},
    }
    jp = [k for k in real if works[k]["country"] == "JP"]
    d["티처 #56 3순위 팔 --- 한글 질의 JP 롱테일"] = {
        "n": len(jp), "⚠": "칸이 작아 부분 검정만 된다(사전등록에 그렇게 적혀 있다)",
        "나무위키 존재": f"{sum(1 for k in jp if namu[k])}/{len(jp)}",
        "KR 대조": f"{sum(1 for k in real if works[k]['country'] == 'KR' and namu[k])}/"
                 f"{sum(1 for k in real if works[k]['country'] == 'KR')}",
        "R2 안다 비율 JP": round(sum(r2[k] for k in jp if r2[k] is not None) / max(1, len(jp)), 4),
    }
    # 정답지 변형에 대한 B 의 민감도
    sens = {}
    for f2 in ("v2b·느슨", "v1b·느슨", "v2b·엄격", "v1b·엄격"):
        row = {}
        for name in ("R1 정확구문(네이버 news)", "R3a 나무위키 바이트",
                     "R3 문서 존재·길이(나무+위키)", "R2 베이스모델 탐침"):
            ks = [k for k in real + fake
                  if V[name].get(k) is not None and works[k][f2] is not None]
            row[name] = {"n": len(ks), "ρ": round(spearman(
                [V[name][k] for k in ks], [works[k][f2] for k in ks]), 4)}
        sens[f2] = row
    d["🔴 B 는 정답지 변형에 견디는가"] = sens

    # 🔴 인계 카드의 n=11 주장을 220 전량으로 다시 잰다
    allreal = [k for k in works if not works[k]["음성"] and r2.get(k) is not None]
    def rate(ks):
        return f"{sum(r2[k] for k in ks)}/{len(ks)}" if ks else "0/0"
    d["🔴 카드의 「베이스는 상위권을 안다」(n=11)를 220 으로 다시 쟀다"] = {
        "카드가 적은 것(n=11)": "상 4/4 · 중 0/3 · 하 1/4",
        "실측(실물 200)": {s2: rate([k for k in allreal if works[k]["층"] == s2])
                       for s2 in ("상", "중", "하")},
        "실측(한글 질의 실물만)": {s2: rate([k for k in allreal if works[k]["층"] == s2
                                    and works[k]["질의출처"] in KO])
                          for s2 in ("상", "중", "하")},
        "음성 20": rate([k for k in works if works[k]["음성"] and r2.get(k) is not None]),
        "🔴 뜻": ("**계단이 안 재현된다.** 200 전량에서 상 0.582 대 중 0.463 · 하 0.470 이고, "
               "한글 질의 안에서는 **하(0.538)가 중(0.400)보다 높다**. 티처 #56 이 "
               "*'외부 코퍼스 수확과 로컬 베이스 모델이 독립된 두 자로 같은 것을 잰다'* 의 "
               "근거로 인용한 그 계단은 **n=11 의 성질**이었다(조항 60). "
               "남는 것은 **실물/음성 구별**뿐이다 --- 실물 0.505 대 음성 0.05."),
    }
    return d


def main():
    works, R, truth, Bth = load()
    thresh = Bth["🔴 통과선 = 천장 × 0.60"]
    V = ruler_values(works, R)
    rep = {"사전등록": "docs/prereg_895_textmass.md v3",
           "정답지 정본": FIELD,
           "🔴 분모 정본(티처 #58 M8)": {
               "A": "한글 질의 실물 **62**(등록 모집단 전수) + 음성 20",
               "B · C · 천장 · 통과선": "한글 질의 실물 **58**(정답지 값 있음) + 음성 20 = **78**",
               "왜": ("결측 4건은 정답지의 결측이지 자의 결측이 아니다 --- A 는 자의 값만 "
                    "있으면 재지고, 정답지 값으로 떨어뜨리면 결과에 조건을 붙여 표본을 "
                    "고르는 것이다(v3 「고친 것 ①」이 이름 붙여 피한 병). B·C·천장은 "
                    "정답지 값이 정의상 필요하므로 58 이다."),
               "🔴 조항 60": "이 두 수를 한 문장에 잇지 마라. 두 판의 값은 자마다 「🔴 A · 분모 62 대 58 병기」 칸에 다 있다.",
               "사전등록 문면": "180행 62(값 있음 58) · 208행 58 --- 어긋났던 것을 v3 정정 칸에서 못 박았다",
           },
           "B 통과선(정답지 산출물에서 **읽었다**)": thresh,
           "천장": Bth,
           "요청 총계(세어서)": sum(
               1 for _ in (ROOT / "runners/out895_reqlog.jsonl").open(encoding="utf-8")),
           "자": {}}
    for name, vals in V.items():
        rep["자"][name] = grade(name, vals, works, thresh)

    # 🔴 R2 는 요청 0 이라 220 전량이 있다 --- 전 표본 보조 채점(조항 60: 갈라 적는다)
    r2 = V["R2 베이스모델 탐침"]
    allr = [k for k in r2 if not works[k]["음성"] and r2[k] is not None]
    allf = [k for k in r2 if works[k]["음성"] and r2[k] is not None]
    by = {}
    for src in sorted({works[k]["질의출처"] for k in allr}):
        ks = [k for k in allr if works[k]["질의출처"] == src]
        by[src] = {"n": len(ks), "안다 비율": round(sum(r2[k] for k in ks) / len(ks), 4)}
    rep["🔴 R2 보조 · 전 표본 220"] = {
        "실물 안다 비율": round(sum(r2[k] for k in allr) / len(allr), 4),
        "음성 안다 비율": round(sum(r2[k] for k in allf) / len(allf), 4),
        "AUC(음성<실물 · 전 표본)": round(
            auc([r2[k] for k in allr], [r2[k] for k in allf]), 4),
        "질의출처별 안다 비율": by,
        "층별 안다 비율(한글 질의 실물만)": {
            s: round(sum(r2[k] for k in allr
                         if works[k]["층"] == s and works[k]["질의출처"] in KO)
                     / max(1, sum(1 for k in allr if works[k]["층"] == s
                                  and works[k]["질의출처"] in KO)), 4)
            for s in ("상", "중", "하")},
    }
    rep["🔴 진단"] = diagnostics(works, R, V)
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    for n, r in rep["자"].items():
        print(f"{n}: A={r.get('A 통과')} B={r.get('B 통과')} C={r.get('C 통과')} "
              f"셋다={r['🔴 A·B·C 셋 다']}")
    print(json.dumps(rep["🔴 R2 보조 · 전 표본 220"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
