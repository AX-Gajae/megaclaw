# -*- coding: utf-8 -*-
"""997 팔 ㉡ — 🔴🔴 **「라벨 0 개 자」(가림 복원)를 «널과 함께» 세우고 그 `MDE` 를 낸다.**

사전등록 `docs/prereg_997_unsupervised_mde.md` §2·§4.

🔴 **이 자는 `y` 를 한 비트도 안 읽는다.** 읽는 것은 `(A, M)` 뿐이다.
그 사실을 **말이 아니라 계산으로** 신고한다:
  ⑤ **라벨 순열 바닥** — 라벨을 통째로 순열하고 자를 다시 돌린다.
     🔴 값이 **글자 그대로** 같아야 한다(이 자의 라벨 비트가 0 이므로).
  🔴 그 검사가 「원리상 참」이 아님을 보이려고 **라벨 누출 판**을 «같은 격자에서» 돌린다
     --- 거기서는 순열이 값을 **바꿔야** 한다. 곧 대조판이 0 도 1 도 낸다(조항 78 ㉮·㉯).
  ④ **난수 표현 바닥** — 같은 그물을 **학습 0 스텝**으로 얼려서 잰다.

산출: `runners/out997_mask.json`
사용: `M997_THREADS=5 python3 runners/mde997_mask.py`
"""
import collections
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import delta996_common as C                       # noqa: E402  🔴 등록된 자
import mde997_common as K                         # noqa: E402

#: 🔴 연기 시험은 `M997_OUT` 으로 «저장소 밖»에 쓴다(`runners/` 를 안 더럽힌다)
OUT = Path(os.environ.get("M997_OUT", "")) if os.environ.get("M997_OUT") \
    else ROOT / ("runners/out997_mask%s.json" % os.environ.get("M997_TAG", ""))


def _torch():
    import torch
    torch.set_num_threads(K.THREADS)
    return torch


class _Net:
    """입력 `2P`(값·마스크) → 폭 W × L 잔차블록 → 출력 `P`. 915 `grid915_ssl.Net` 과 같은 꼴."""

    def __init__(self, P, seed, W=K.MAE_WIDTH, L=K.MAE_DEPTH):
        torch = _torch()
        import torch.nn as nn
        torch.manual_seed(int(seed))
        self.torch, self.nn = torch, nn
        self.m = nn.Sequential()
        self.inp = nn.Linear(2 * P, W)
        self.blocks = nn.ModuleList([nn.Linear(W, W) for _ in range(L)])
        self.out = nn.Linear(W, P)
        self.act = nn.GELU()
        self.params = list(self.inp.parameters()) + \
            [q for b in self.blocks for q in b.parameters()] + \
            list(self.out.parameters())

    def fwd(self, x):
        h = self.act(self.inp(x))
        for b in self.blocks:
            h = h + self.act(b(h))
        return self.out(h)


def build_cells(data, split_seed=K.SPLIT_SEED, eval_frac=K.MASK_EVAL_FRAC):
    """🔴 `y` 를 «안 읽는다». `(A, M)` 만으로 셀을 학습/유보로 가른다."""
    doms, cols = K.col_union(data)
    P = len(cols)
    ci = {c: i for i, c in enumerate(cols)}
    rng = np.random.RandomState(int(split_seed))
    S = {}
    opened = []
    for d in doms:
        A, M, _y, _t = data.dom[d]                   # 🔴 `_y` 는 아래에서 «안 쓴다»
        opened.append("dom[%s].A" % d)
        opened.append("dom[%s].M" % d)
        n = A.shape[0]
        V = np.zeros((n, P), float)
        O = np.zeros((n, P), bool)
        nm = list(data.names.get(d) or [])
        for j, c in enumerate(nm):
            if c in ci and j < A.shape[1]:
                V[:, ci[c]] = np.asarray(A[:, j], float)
                O[:, ci[c]] = np.asarray(M[:, j], float) > 0
        O &= np.isfinite(V)
        E = O & (rng.rand(n, P) < float(eval_frac))  # 유보 셀
        TR = O & ~E                                  # 학습 셀
        # 🔴 표준화는 **학습 셀만** 본다 --- 유보 셀은 통계에도 안 들어간다
        mu = np.zeros(P)
        sd = np.ones(P)
        for j in range(P):
            v = V[TR[:, j], j]
            if len(v) >= 2:
                mu[j] = float(v.mean())
                s = float(v.std(ddof=1))
                sd[j] = s if s > 1e-12 else 1.0
        Z = (V - mu) / sd
        S[d] = {"Z": Z, "O": O, "E": E, "TR": TR, "mu": mu, "sd": sd}
    return doms, cols, S, opened


def train_net(S, doms, P, seed, steps, extra=None, track=None):
    """가림 복원 사전학습. `extra` = {도메인: (n,1) 추가 입력열} --- 누출 대조판만 쓴다."""
    torch = _torch()
    net = _Net(P + (1 if extra is not None else 0), seed)
    Zs = np.vstack([S[d]["Z"] for d in doms])
    TRs = np.vstack([S[d]["TR"] for d in doms]).astype(np.float32)
    if extra is not None:
        Zs = np.hstack([Zs, np.vstack([extra[d] for d in doms])])
        TRs = np.hstack([TRs, np.ones((TRs.shape[0], 1), np.float32)])
    Zt = torch.tensor(np.nan_to_num(Zs, nan=0.0, posinf=0.0, neginf=0.0),
                      dtype=torch.float32)
    Mt = torch.tensor(TRs, dtype=torch.float32)
    Pw = Zt.shape[1]
    opt = torch.optim.Adam(net.params, lr=1e-3)
    rs = np.random.RandomState(int(seed) + 5000)
    n = Zt.shape[0]
    losses = []
    ckpt = sorted(set(int(x) for x in (track or [])))
    tracked = collections.OrderedDict()
    if 0 in ckpt:
        tracked[0] = None                             # 아래에서 채운다
    for st in range(int(steps)):
        idx = torch.tensor(rs.randint(0, n, K.MAE_BATCH), dtype=torch.long)
        z, m = Zt[idx], Mt[idx]
        drop = torch.tensor(
            (rs.rand(K.MAE_BATCH, Pw) < K.MASK_P).astype(np.float32))
        vis = m * (1.0 - drop)
        tgt = m * drop                                # 이번 스텝의 복원 표적
        x = torch.cat([z * vis, vis], dim=1)
        pred = net.fwd(x)[:, :P] if extra is not None else net.fwd(x)
        tt = tgt[:, :P]
        loss = ((pred - z[:, :P]) ** 2 * tt).sum() / torch.clamp(tt.sum(), min=1.0)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if st % 100 == 0 or st == int(steps) - 1:
            losses.append(round(float(loss.item()), 6))
        if ckpt and (st + 1) in ckpt:
            tracked[st + 1] = score_ruler(net, S, doms, P, extra=extra)[0]
    if 0 in tracked and tracked[0] is None:
        tracked[0] = score_ruler(_Net(Pw, seed), S, doms, P, extra=extra)[0]
    return (net, losses, tracked) if track else (net, losses)


def score_ruler(net, S, doms, P, extra=None):
    """🔴 자 ㉡ --- 유보 «셀» 을 복원하고 (도메인, 열)별 스피어만 → 도메인 점수."""
    torch = _torch()
    per_dom, detail = {}, collections.OrderedDict()
    for d in doms:
        Z, TR, E = S[d]["Z"], S[d]["TR"], S[d]["E"]
        vis = TR.astype(np.float32)
        z = np.nan_to_num(Z, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        if extra is not None:
            z = np.hstack([z, extra[d].astype(np.float32)])
            vis = np.hstack([vis, np.ones((vis.shape[0], 1), np.float32)])
        x = torch.tensor(np.hstack([z * vis, vis]), dtype=torch.float32)
        with torch.no_grad():
            pr = net.fwd(x).numpy()[:, :P]
        rho, wt = [], []
        for j in range(P):
            k = np.where(E[:, j])[0]
            if len(k) < 5:
                continue
            r = K.sp(pr[k, j], Z[k, j])
            if np.isfinite(r):
                rho.append(r)
                wt.append(len(k))
        if not rho:
            per_dom[d] = float("nan")
            detail[d] = {"🔴 못 쟀다": "유보 셀이 선 열이 없다"}
            continue
        rho, wt = np.array(rho), np.array(wt, float)
        per_dom[d] = float((rho * wt).sum() / wt.sum())
        detail[d] = collections.OrderedDict([
            ("잰 열 수", int(len(rho))), ("유보 셀 수", int(wt.sum())),
            ("도메인 점수(셀수 가중)", K._r(per_dom[d]))])
    return per_dom, detail


def main():
    t0 = time.time()
    out = collections.OrderedDict()
    out["무엇"] = ("997 팔 ㉡ · 🔴 「라벨 0 개 자」(가림 복원) + 바닥 둘(난수 표현 · "
                 "라벨 순열) + 그 자의 `MDE`")
    out["🔴 「비지도」의 뜻 --- 997 이 닫는 하나"] = collections.OrderedDict([
        ("고른 것", "③ «자»까지 라벨을 안 쓴다"),
        ("왜", "①(표본을 라벨 없이 뽑는다)·②(목적함수가 라벨을 안 쓴다)는 915 가 이미 "
              "지켰다. 그런데도 분모가 유보 라벨 3,775 로 잘린 것은 «자»가 라벨을 "
              "썼기 때문이다. 사용자의 물음이 겨누는 자리가 ③ 이다."),
        ("이 러너에서 ③ 이 지켜지는 증거", "라벨 순열 바닥이 «글자 그대로» 같은 값을 낸다 "
                                "--- 아래 칸에서 계산으로 신고한다")])
    out["🔴🔴 `MDE` 정의"] = K.MDE_DEF

    data = K.load()
    doms, cols, S, opened = build_cells(data)
    P = len(cols)
    n_obs = int(sum(int(S[d]["O"].sum()) for d in doms))
    n_ev = int(sum(int(S[d]["E"].sum()) for d in doms))
    n_tr = int(sum(int(S[d]["TR"].sum()) for d in doms))
    lab_ho = int(sum(data.weights(K.T_CANON).values()))
    out["분모 --- 🔴 이것이 ③ 을 고르는 «이유»다"] = collections.OrderedDict([
        ("도메인", len(doms)), ("열(합집합)", P), ("행", int(sum(
            data.dom[d][0].shape[0] for d in doms))),
        ("관측 셀", n_obs), ("학습 셀", n_tr), ("🔴 유보 셀 = ㉡ 의 분모", n_ev),
        ("🔴 유보 라벨 = ㉠ 의 분모", lab_ho),
        ("🔴 배수(㉡ 분모 / ㉠ 분모)", K._r(n_ev / lab_ho) if lab_ho else None),
        ("군집(둘 다 같다)", len(doms))])

    # ── 팔 ──────────────────────────────────────────────────────────
    arms = collections.OrderedDict()
    trained, rand = {}, {}
    for sd in K.SHAM_SEEDS:
        net, ls = train_net(S, doms, P, sd, K.MAE_STEPS)
        trained[sd] = score_ruler(net, S, doms, P)[0]
        net0 = _Net(P, sd)                            # 🔴 바닥 ④ --- 학습 0 스텝
        rand[sd] = score_ruler(net0, S, doms, P)[0]
        if sd == K.SHAM_SEEDS[0]:
            arms["손실 곡선(씨앗 %d)" % sd] = ls
        print("  씨앗 %d 끝 · %.0f초" % (sd, time.time() - t0), flush=True)

    # ── 🔴 조항 79 --- 헤드라인을 «조각»으로: 스텝 사다리 0 → S/4 → S/2 → S ──
    lad = [0, K.MAE_STEPS // 4, K.MAE_STEPS // 2, K.MAE_STEPS]
    _n, _l, tracked = train_net(S, doms, P, K.SHAM_SEEDS[0], K.MAE_STEPS,
                                track=lad)
    per_by = collections.OrderedDict(
        [("스텝%d" % k, tracked[k]) for k in lad if k in tracked])
    out["🔴 조항 79 조각 — 스텝 사다리(씨앗 %d)" % K.SHAM_SEEDS[0]] = \
        collections.OrderedDict([
            ("사다리", lad),
            ("단계별 도메인 점수", collections.OrderedDict(
                [(k, {d: K._r(v[d]) for d in doms}) for k, v in per_by.items()])),
            ("🔴 조각(이웃 차 + 합 · `delta996_common.seg_from`)",
             C.seg_from(list(per_by), per_by)),
            ("🔴 부호뒤집기 «전수» 순열(조각 셋)", C.signflip_exact(
                {d: [per_by[list(per_by)[i + 1]][d] - per_by[list(per_by)[i]][d]
                     for i in range(len(per_by) - 1)] for d in doms},
                ["%s→%s" % (list(per_by)[i], list(per_by)[i + 1])
                 for i in range(len(per_by) - 1)])),
            ("🔴 연언 채점(조항 79 개정 1)", "산출물의 「관측 통과 수 / 분모 조각」 칸을 보라 "
                                  "--- 일부만 넘으면 «명제»가 아니라 가설 후보다")])

    def avg(dd):
        return {d: float(np.nanmean([dd[s][d] for s in K.SHAM_SEEDS]))
                for d in doms}

    tr_m, rd_m = avg(trained), avg(rand)
    arms["㉡-1 학습 그물(씨앗 평균)"] = {d: K._r(tr_m[d]) for d in doms}
    arms["㉡-2 난수 표현 바닥 ④(씨앗 평균)"] = {d: K._r(rd_m[d]) for d in doms}
    out["팔"] = arms

    head = {d: tr_m[d] - rd_m[d] for d in doms}
    out["🔴 헤드라인 대비 ㉡ = 학습 − 난수표현"] = C.cluster_se(head)
    out["🔴 부호뒤집기 «전수» 순열"] = C.signflip_exact({d: [head[d]] for d in doms},
                                              ["㉡ 학습−난수"])
    out["🔴 빠른 순열판이 등록된 자와 같은가"] = K.signflip_selfcheck(head)
    out["🔴 해석 SE 대 등록된 뽑기 SE"] = C.se_surrogate_check(head)

    # ── 바닥 ⑤ 라벨 순열 --- 🔴 «글자 그대로» 같아야 한다 ────────────────
    dperm = K.load(perm_label_seed=997)
    doms2, cols2, S2, _ = build_cells(dperm)
    net_p, _ = train_net(S2, doms2, P, K.SHAM_SEEDS[0], K.MAE_STEPS)
    perm_sc = score_ruler(net_p, S2, doms2, P)[0]
    base_sc = trained[K.SHAM_SEEDS[0]]
    dmax = max(abs(perm_sc[d] - base_sc[d]) for d in doms)
    out["🔴🔴 바닥 ⑤ 라벨 순열 (자 ㉡ · 라벨 0 비트)"] = collections.OrderedDict([
        ("무엇", "라벨 `y` 를 도메인마다 통째로 순열하고 자를 처음부터 다시 돌렸다"),
        ("순열 씨앗", 997),
        ("도메인별 차 |순열 − 원본|", {d: K._r(abs(perm_sc[d] - base_sc[d]), 12)
                              for d in doms}),
        ("🔴 최대 |차|", K._r(dmax, 12)),
        ("🔴🔴 글자 그대로 같은가(=라벨 비트 0)", bool(dmax == 0.0)),
        ("🔴 이 검사가 «원리상 참»이 아님의 증거", "아래 「라벨 누출 대조판」이 같은 격자에서 "
                                     "«거짓»을 낸다")])

    # ── 🔴 대조판 --- 라벨을 «일부러» 넣으면 순열이 값을 바꿔야 한다 ──────
    def yin(dd):
        e = {}
        for d in doms:
            y = np.asarray(dd.dom[d][2], float)
            r = K.rank01(y)
            e[d] = np.nan_to_num(r, nan=0.0).reshape(-1, 1)
        return e

    lk0, _ = train_net(S, doms, P, K.SHAM_SEEDS[0], K.MAE_STEPS, extra=yin(data))
    sc0 = score_ruler(lk0, S, doms, P, extra=yin(data))[0]
    lk1, _ = train_net(S2, doms2, P, K.SHAM_SEEDS[0], K.MAE_STEPS,
                       extra=yin(dperm))
    sc1 = score_ruler(lk1, S2, doms2, P, extra=yin(dperm))[0]
    lmax = max(abs(sc1[d] - sc0[d]) for d in doms)
    out["🔴🔴 라벨 누출 대조판 (같은 격자 · 라벨을 «입력열»로 넣었다)"] = \
        collections.OrderedDict([
            ("도메인별 차 |순열 − 원본|", {d: K._r(abs(sc1[d] - sc0[d]), 12) for d in doms}),
            ("🔴 최대 |차|", K._r(lmax, 12)),
            ("🔴 글자 그대로 같은가", bool(lmax == 0.0)),
            ("🔴🔴 대조가 뒤집혔나(누출판은 달라야 한다)", bool(lmax > 0.0))])

    # ── 위약 짝 --- 참 효과 «구성상» 0 ────────────────────────────────
    pairs = [(K.SHAM_SEEDS[i], K.SHAM_SEEDS[i + 1])
             for i in range(0, len(K.SHAM_SEEDS) - 1, 2)]
    pool = {d: [] for d in doms}
    for a, b in pairs:
        for d in doms:
            v = trained[a][d] - trained[b][d]
            if np.isfinite(v):
                pool[d] += [float(v), float(-v)]     # 🔴 귀무는 부호 대칭이다
    out["위약 짝(참 효과 구성상 0)"] = collections.OrderedDict([
        ("무엇", "같은 설정 · 씨앗만 다른 두 학습 그물의 차"),
        ("짝", ["%d-%d" % p for p in pairs]),
        ("🔴 부호 대칭 증대", "귀무 분포는 0 둘레 대칭이므로 각 값의 ± 를 둘 다 넣는다"),
        ("도메인별 값 수", {d: len(pool[d]) for d in doms}),
        ("도메인별 SD", {d: K._r(float(np.std(pool[d], ddof=1))) for d in doms})])

    # ── 🔴🔴 `MDE` ──────────────────────────────────────────────────
    pc = K.power_curve(pool, doms)
    pc2 = K.power_curve(pool, doms, paired=False)
    out["🔴🔴🔴 MDE (자 ㉡ · 라벨 0 개 자)"] = pc
    out["MDE 민감도(통째 풀 재표집)"] = collections.OrderedDict([
        ("MDE_s", pc2.get("🔴🔴 MDE_s")), ("MDE_a", pc2.get("🔴 해석식 MDE_a"))])
    hm = pc["🔴🔴 MDE_s"]["🔴 ㉠ 2·SE(헤드라인)"]["MDE_s(선형 보간)"]
    out["🔴🔴🔴 분기"] = K.branch(hm)

    obs = float(np.nanmean([head[d] for d in doms]))
    out["🔴 관측 효과 대 MDE"] = collections.OrderedDict([
        ("관측 헤드라인 효과 Δ̄", K._r(obs)),
        ("MDE_s(헤드라인)", K._r(hm) if hm is not None else None),
        ("🔴 Z = MDE / 관측 효과", K._r(hm / abs(obs)) if hm and obs else None),
        ("🔴 뜻", "Z > 1 이면 이 자는 이 효과를 «원리상» 못 잡는다"
                "(`docs/목표.md` 오라클 천장 규율의 «분모를 넓힌» 것)")])

    # ── 조항 78 ㉮·㉯ --- 🔴 «기계로» 센다 ────────────────────────────
    base = collections.OrderedDict([("㉡ 학습−난수", head)])

    def _mean(st):
        v = np.array([st["㉡ 학습−난수"][d] for d in doms], float)
        return float(np.nanmean(v))

    def _se(st):
        v = np.array([st["㉡ 학습−난수"][d] for d in doms], float)
        v = v[np.isfinite(v)]
        if len(v) < 2:
            return float("nan")
        return float(v.std(ddof=1) * np.sqrt((len(v) - 1.0) / len(v))
                     / np.sqrt(len(v)))

    claims = [
        ("헤드라인이 2·SE 를 넘는다", lambda st: abs(_mean(st)) > 2 * _se(st)),
        ("헤드라인이 양수다", lambda st: _mean(st) > 0),
        ("동부호가 9/12 이상이다", lambda st: sum(
            1 for d in doms if np.sign(st["㉡ 학습−난수"][d]) == np.sign(_mean(st))) >= 9),
        ("|Δ̄| 가 MDE 를 넘는다",
         lambda st: (hm is not None) and abs(_mean(st)) > hm),
        ("부호뒤집기 순열 p ≤ α", lambda st: float(K.signflip_p_batch(
            np.array([[st["㉡ 학습−난수"][d]] for d in doms], float))[0][0]) <= K.ALPHA),
    ]
    controls = [
        ("대조(늘 참이어야) — 도메인 수가 2 이상이다", lambda st: len(st["㉡ 학습−난수"]) >= 2),
        ("대조(늘 거짓이어야) — |Δ̄| 가 자기 자신보다 크다",
         lambda st: abs(_mean(st)) > abs(_mean(st))),
    ]
    out["🔴🔴 조항 78 ㉮·㉯ (기계)"] = C.taut_scan(
        claims, C.variant_grid(base, seed=997), label="자 ㉡ 헤드라인", controls=controls)

    out["🔴 조항 79 개정 2 — cluster_se 칸 전량"] = C.cse_ledger()
    out["🔴 라벨 0 비트 단언"] = collections.OrderedDict([
        ("자 ㉡ 이 연 것", sorted(set(opened))[:6] + ["… 총 %d" % len(set(opened))]),
        ("🔴 `y` 를 읽은 곳", "자 ㉡ 의 어느 함수도 `dom[d][2]` 를 안 읽는다 "
                        "--- 누출 «대조판»만 일부러 읽는다"),
        ("🔴 그 증거", "위 「바닥 ⑤ 라벨 순열」의 최대 |차| = 0")])
    out.update(K.stamp(t0))
    h = K.json_dump(OUT, out)
    print("→ %s  sha256 %s  %.1f분" % (OUT, h[:16], (time.time() - t0) / 60.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
