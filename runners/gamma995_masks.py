#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""995 — 🔴 **`F01` 정정 얹기**. 챔피언 유보 마스크를 `lab/harness.py` 에 맞춘다.

🔴🔴🔴 **`runners/beta994_*.py` 는 동결이다. 한 글자도 안 고친다.** 그래서 «새 파일»이다.

## 무엇이 틀렸나 (994 가 짚었다 · 사전등록 §1)

| | |
|---|---|
| `beta994_common.py:189 canon_masks` | 유보 마스크가 `labeled()` = `isfinite(y) & isfinite(yr)` 를 쓴다 |
| `beta994_common.py:158 blocks` | 블록 마스크도 `labeled()` 를 쓴다 |
| 🔴 `lab/harness.py:320` | `post = np.isfinite(data.yr[d]) & (data.yr[d] >= T)` — **`isfinite(y)` 가 «없다»** |
| `lab/harness.py:309` | 학습 마스크는 `isfinite(yr) & (yr < T) & isfinite(y)` — **학습 쪽은 «있다»** |
| `lab/forms.py:1140 BagBoost.predict` | **배치 «안»에서** 순위를 매긴다 ⇒ **배치가 바뀌면 남은 행의 예측이 바뀐다** |

🔴 **그래서 고칠 자리는 「유보 쪽」뿐이다. 학습 쪽은 994 와 «같게» 둔다.**
🔴 **블록 절단 분위도 994 와 «같게» 둔다** — 절단을 바꾸면 994 와 비교가 안 된다
(조항 66 — 자 수리 시 구판/신판 전후를 낸다. 한 번에 둘을 바꾸면 무엇이 움직였는지 못 센다).

## 🔴 규칙 D — 이탈 크기

**두 규약의 차는 `7.199316e-04` 다.** (`웹툰 +0.004388` · `게임 −0.000745` 가 만든 수)
🔴 **`0.000e+00` 이 «아니다»** — 그건 「각 규약이 자기 기대를 재현한 잔차」다(사전등록 §9-5).
"""
import collections

import numpy as np

F01_DEV = 7.199316e-04     #: 🔴 사전등록 §9-5 · §9-6 — 측정 전에 박았다
SAFE_MULT = 20             #: 🔴 사전등록 §9-6 안전 배수 문턱


def labeled(d0, d):
    """994 와 «같은» 정의 — 학습 쪽에만 쓴다."""
    y = np.asarray(d0.dom[d][2], float)
    yr = np.asarray(d0.yr[d], float)
    return np.isfinite(y) & np.isfinite(yr)


def yr_ok(d0, d):
    """🔴 **수리판 유보 정의** — `lab/harness.py:320` 과 «같다». `isfinite(y)` 를 «안» 더한다."""
    return np.isfinite(np.asarray(d0.yr[d], float))


def canon_masks_fixed(d0, doms, T=2025.0):
    """정본 원점 — 🔴 **학습은 994 와 같고 유보만 harness 에 맞춘다.**"""
    tr, ho = {}, {}
    for d in doms:
        yr = np.asarray(d0.yr[d], float)
        tr[d] = labeled(d0, d) & (yr < T)          # harness:309 와 같다
        ho[d] = yr_ok(d0, d) & (yr >= T)           # 🔴 harness:320 와 같다
    return tr, ho


def canon_masks_old(d0, doms, T=2025.0):
    """구판 — `beta994_common.canon_masks` 와 «글자 그대로» 같다(견주기용)."""
    tr, ho = {}, {}
    for d in doms:
        yr = np.asarray(d0.yr[d], float)
        lb = labeled(d0, d)
        tr[d] = lb & (yr < T)
        ho[d] = lb & (yr >= T)
    return tr, ho


def cuts_994(d0, doms, qs=(0.2, 0.4, 0.6, 0.8)):
    """🔴 절단은 994 와 «같은 방법»으로 낸다 — 전 도메인 «라벨 행» yr 의 분위."""
    allyr = np.concatenate([np.asarray(d0.yr[d], float)[labeled(d0, d)]
                            for d in doms])
    return [float(np.quantile(allyr, q)) for q in qs], allyr


def blocks_fixed(d0, doms, qs=(0.2, 0.4, 0.6, 0.8), nblock=5):
    """블록 — **절단은 994 와 같다.** 🔴 **유보 쪽 블록만 `isfinite(y)` 를 뺀다.**

    돌려주는 것 = (정보, 학습블록, 🔴 유보블록, 절단 가장자리).
    """
    cuts, allyr = cuts_994(d0, doms, qs)
    edges = [-1e9] + cuts + [1e9]
    tr_blk, ho_blk = {}, {}
    for d in doms:
        yr = np.asarray(d0.yr[d], float)
        lb = labeled(d0, d)
        ok = yr_ok(d0, d)
        tr_blk[d] = [(yr >= edges[k]) & (yr < edges[k + 1]) & lb
                     for k in range(nblock)]
        ho_blk[d] = [(yr >= edges[k]) & (yr < edges[k + 1]) & ok
                     for k in range(nblock)]
    info = collections.OrderedDict([
        ("분위", list(qs)), ("절단(yr)", [round(c, 6) for c in cuts]),
        ("전량 라벨 행", int(len(allyr))),
        ("🔴 절단은 994 와 같은 방법으로 냈다", True),
        ("학습 블록별 행", [int(sum(int(tr_blk[d][k].sum()) for d in doms))
                      for k in range(nblock)]),
        ("🔴 유보 블록별 행(수리판)",
         [int(sum(int(ho_blk[d][k].sum()) for d in doms)) for k in range(nblock)]),
        ("도메인별 학습 블록 행", collections.OrderedDict(
            [(d, [int(tr_blk[d][k].sum()) for k in range(nblock)]) for d in doms])),
        ("🔴 도메인별 유보 블록 행(수리판)", collections.OrderedDict(
            [(d, [int(ho_blk[d][k].sum()) for k in range(nblock)]) for d in doms])),
    ])
    return info, tr_blk, ho_blk, edges


def train_mask_lt(tr_blk, doms, k):
    """학습 = 블록 `< k` 합집합 (994 와 같다)."""
    return {d: np.logical_or.reduce(tr_blk[d][:k]) for d in doms}


def mask_diff_table(d0, doms, T=2025.0, qs=(0.2, 0.4, 0.6, 0.8), nblock=5):
    """🔴🔴 **조항 66 — 자를 고쳤으면 「구판/신판 전후」를 낸다.**"""
    tr_n, ho_n = canon_masks_fixed(d0, doms, T)
    tr_o, ho_o = canon_masks_old(d0, doms, T)
    _i, tr_b, ho_b, _e = blocks_fixed(d0, doms, qs, nblock)
    per = collections.OrderedDict()
    for d in doms:
        per[d] = collections.OrderedDict([
            ("정본 유보 구판", int(ho_o[d].sum())),
            ("정본 유보 신판", int(ho_n[d].sum())),
            ("🔴 차", int(ho_n[d].sum()) - int(ho_o[d].sum())),
            ("정본 학습 구판", int(tr_o[d].sum())),
            ("정본 학습 신판", int(tr_n[d].sum())),
            ("🔴 학습 차(0 이어야 한다)",
             int(tr_n[d].sum()) - int(tr_o[d].sum())),
            ("블록별 유보 신판", [int(ho_b[d][k].sum()) for k in range(nblock)]),
            ("블록별 학습 신판", [int(tr_b[d][k].sum()) for k in range(nblock)]),
        ])
    tot_o = sum(int(ho_o[d].sum()) for d in doms)
    tot_n = sum(int(ho_n[d].sum()) for d in doms)
    return collections.OrderedDict([
        ("🔴 무엇", "F01 정정 --- 유보 마스크에서 isfinite(y) 를 뺐다. "
                  "학습 마스크는 안 건드렸다(harness:309 가 그렇다)."),
        ("도메인별", per),
        ("정본 유보 합 구판", tot_o), ("정본 유보 합 신판", tot_n),
        ("🔴🔴 정본 유보 합 차", tot_n - tot_o),
        ("🔴 학습 합 차(0 이어야 한다)",
         sum(int(tr_n[d].sum()) for d in doms) - sum(int(tr_o[d].sum()) for d in doms)),
        ("🔴 갈린 도메인", [d for d in doms
                       if int(ho_n[d].sum()) != int(ho_o[d].sum())]),
        ("🔴 갈린 도메인 수", int(sum(1 for d in doms
                                if int(ho_n[d].sum()) != int(ho_o[d].sum())))),
        ("🔴 사전등록에 박은 이탈 크기(판 ρ 차)", F01_DEV),
    ])


def score_gate(d0, f, hmask, doms, gate, spearmanr=None):
    """`beta994_common.score` 와 «같되» **`MIN_SCORE` 를 인자로 받는다**.

    🔴 조항 66 — **문턱을 박지 말고 검사를 인자화하라.**
    """
    if spearmanr is None:
        from scipy.stats import spearmanr as _sp
        spearmanr = _sp
    out, drop = collections.OrderedDict(), collections.OrderedDict()
    if f is None:
        for d in doms:
            drop[d] = "학습부족 --- 쟀는데 설정이 버렸다"
        return out, drop
    for d in doms:
        m = np.asarray(hmask.get(d), bool) if hmask.get(d) is not None else None
        if m is None or int(m.sum()) == 0:
            drop[d] = "0 행"
            continue
        A_, M_, y_, t_ = d0.slice(d, m)
        if len(y_) < gate:
            drop[d] = "행부족 --- 쟀는데 설정이 버렸다"
            continue
        p = np.asarray(f.predict(d, A_, M_, t_), float)
        ok = np.isfinite(p) & np.isfinite(y_)
        if int(ok.sum()) < gate:
            drop[d] = "결측 --- 예측이 유한한 행이 게이트 미만"
            continue
        rho = float(spearmanr(p[ok], y_[ok])[0])
        if not np.isfinite(rho):
            drop[d] = "결측 --- rho 가 유한하지 않다"
            continue
        out[d] = {"rho": rho, "n": int(ok.sum()), "n(유보 행 전량)": int(len(y_))}
    return out, drop
