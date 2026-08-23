# -*- coding: utf-8 -*-
"""내재 상태 엔진 v0 — 사이클 1022 (사전등록 docs/탐색/1022.md §1~§8 의 코드).

물음(조항 73): 시점 t 이전 발행 문서 시퀀스를 «학습된» 인코더로 압축한 상태가,
고정 감쇠 평균(1019 s_disc · τ=90)이 담는 것 이상으로 미래 위키 곡선(91일)의 정보를 담는가.

팔 셋(§2 · 짝지은 씨앗 K=4):
  ⓐ 곡선만(현행 Transition 축소판 — hidden 128)
  ⓑ 곡선 + 고정 s_disc(τ=90 · 1019 §2 산식 미러 · PCA8 은 train 유문서 쌍에서만 적합)
  ⓒ 곡선 + 학습 인코더(문서 임베딩 시퀀스 최근 16 · pub 순 · Δt 부호화 → GRU(32) → 상태 벡터)

출력·손실 = 현행 규격(91×5 분위수 · softplus 간격 · 핀볼 — pretrain/transition.py 항등).
전 특징은 t 이전 발행·관측만 — 쌍마다 leak_guard(§6). 판 무접촉 · CPU 전용.

자기시험: python3 pretrain/state_engine.py --selftest
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import bisect
import datetime as dt
import gzip
import hashlib
import json
import os
import re

import numpy as np

# ── 사전 고정 상수 (§1·§2 — 사전등록 커밋 01903d326 과 일치해야 한다) ──────────
PANEL_DIR = "/Users/ax/world_model/data/ingest/wiki_daily959"
FND = "/Users/ax/wm_harvest/foundation"
META_PATH = os.path.join(FND, "triples", "meta.jsonl")
EMB_PATH = os.path.join(FND, "triples", "text_emb_qwen05b.npz")
SAO_PATH = os.path.join(FND, "triples", "sao.npz")
PUB_V1 = os.path.join(FND, "pubdate", "sao973_pubdate.jsonl.gz")
PUB_V2 = os.path.join(FND, "pubdate", "v2", "sao973_pubdate_v2.jsonl.gz")
REPORT_PATH = os.path.join(FND, "transition", "report.json")
ROSTER = "/Users/ax/world_model/data/lab/val_ext_roster.json"
OUT_DIR = os.path.join(FND, "state_engine")

SHA_SAO = "f120013017dcf512"          # §8 시대 — sao.npz(챔피언 report.json 기재와 동일)
SHA_REPORT = "6dfb0a4ff2935de0"       # §3 앵커 — transition/report.json (assert_epoch)

DOMS = ["게임", "도서", "만화", "모바일", "세계애니", "시장팝업",
        "아이돌", "애니", "웹툰", "팝업", "펀딩"]   # 패널 파일명 사전순 (§1)
T_SPLIT = dt.date(2025, 1, 1).toordinal()          # 시간 전방 분할점
TAU = 90.0                                          # 1019 정본 τ
N_SEQ = 16                                          # ⓒ 시퀀스 상한
SEEDS = [0, 1, 2, 3]                                # 짝지은 씨앗 K=4
STEPS = 3000
BATCH = 256
HIDDEN = 128
LR = 1e-3
QS = [0.05, 0.25, 0.50, 0.75, 0.95]
PARAM_CAP = 300000
PRE, POST = 90, 91


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def _to_ord(x):
    s = str(x)
    return dt.date(int(s[:4]), int(s[4:6]), int(s[6:8])).toordinal()


_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def _iso_ord(s):
    m = _ISO.match(s.strip()) if isinstance(s, str) else None
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).toordinal()
    except ValueError:
        return None


def ent_bucket(ent):
    return int(hashlib.md5(ent.encode("utf-8")).hexdigest()[:8], 16) % 10


# ── 자료 구축 (§1) ────────────────────────────────────────────────────
def load_panel():
    """패널 곡선 → {키: (dom_id, ord0, vals(np, NaN=결측))} + 파일 sha 목록."""
    ents, shas = {}, {}
    for i, dom in enumerate(DOMS):
        p = os.path.join(PANEL_DIR, dom + ".jsonl.gz")
        shas[dom + ".jsonl.gz"] = sha16(p)
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                k = r["키"]
                o = [_to_ord(x) for x in r["날짜"]]
                lo, hi = o[0], o[-1]
                vals = np.full(hi - lo + 1, np.nan, dtype=np.float64)
                vals[np.asarray(o) - lo] = np.asarray(r["조회수"], dtype=np.float64)
                ents[k] = (i, lo, vals)
    return ents, shas


def load_docs():
    """개체별 문서 (pub_ord 오름차순 · emb 행 번호) + 배제 계수(조항 59).

    셀↔문서id: meta.jsonl 행 텍스트 안 32-hex(사전 검증 10,654/10,654 일치 — §0).
    발행일: v1(문서id) ∪ v2(문서id · v1 null 보충) · pub > crawl 은 오탐 제외(1015 §7 미러).
    """
    hexre = re.compile(r"\b[0-9a-f]{32}\b")
    v1, v2 = {}, {}
    with gzip.open(PUB_V1, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["문서id"] not in v1:
                v1[r["문서id"]] = r["published_at"]
    with gzip.open(PUB_V2, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            v2[r["문서id"]] = r["published_at"]
    per_ent = {}
    cnt = {"셀": 0, "hex부재": 0, "발행일null(배제)": 0, "pub>crawl(오탐 배제)": 0,
           "개체내 문서id 중복(접힘)": 0, "채택": 0}
    seen = set()
    with open(META_PATH, encoding="utf-8") as f:
        for row_i, line in enumerate(f):
            m = json.loads(line)
            cnt["셀"] += 1
            h = hexre.search(m["텍스트"])
            if not h:
                cnt["hex부재"] += 1
                continue
            did = h.group(0)
            pub = v1.get(did) or v2.get(did)
            if not pub:
                cnt["발행일null(배제)"] += 1
                continue
            po = _iso_ord(pub)
            co = _iso_ord(m["언제"])
            if po is None:
                cnt["발행일null(배제)"] += 1
                continue
            if co is not None and po > co:
                cnt["pub>crawl(오탐 배제)"] += 1
                continue
            key = (m["개체"], did)
            if key in seen:
                cnt["개체내 문서id 중복(접힘)"] += 1
                continue
            seen.add(key)
            per_ent.setdefault(m["개체"], []).append((po, row_i, pub, did))
            cnt["채택"] += 1
    for e in per_ent:
        per_ent[e].sort()
    return per_ent, cnt


def month_firsts(lo, hi):
    d = dt.date.fromordinal(lo)
    y, m = d.year, d.month
    cur = dt.date(y, m, 1)
    while cur.toordinal() <= hi:
        if cur.toordinal() >= lo:
            yield cur.toordinal()
        m += 1
        if m > 12:
            m, y = 1, y + 1
        cur = dt.date(y, m, 1)


def build_pairs(ents, docs):
    """월 격자 쌍 + 분할(개체 분리 ∧ 시간 전방 — 이중) + 접두사 길이. (§1)"""
    roster = set()
    if os.path.exists(ROSTER):
        roster = set(json.load(open(ROSTER)).get("개체", []))
    keys = sorted(ents.keys())
    pairs = []          # (ent_i, t_ord, split(0=tr,1=va), n_pre)
    ladder = {"패널 개체": len(keys), "격자 쌍": 0, "train": 0, "val": 0,
              "폐기 사분면": 0, "train 유문서(pre-t≥1)": 0, "val 유문서(pre-t≥1)": 0,
              "roster n": len(roster)}
    for ei, k in enumerate(keys):
        dom_i, lo, vals = ents[k]
        isval = (ent_bucket(k) == 0) or (k in roster)
        dl = docs.get(k, [])
        pubs = [d[0] for d in dl]
        for t in month_firsts(lo + PRE, lo + len(vals) - 1 - POST + 1):
            w = vals[t - PRE - lo: t + POST - lo]
            if len(w) != PRE + POST or np.isnan(w).any():
                continue
            ladder["격자 쌍"] += 1
            if isval and t >= T_SPLIT:
                sp = 1
            elif (not isval) and t < T_SPLIT:
                sp = 0
            else:
                ladder["폐기 사분면"] += 1
                continue
            n_pre = bisect.bisect_left(pubs, t)   # published_at < t (엄격)
            pairs.append((ei, t, sp, n_pre))
            ladder["train" if sp == 0 else "val"] += 1
            if n_pre > 0:
                ladder[("train" if sp == 0 else "val") + " 유문서(pre-t≥1)"] += 1
    return keys, pairs, ladder


def leak_stamps(keys, ents, docs, pairs):
    """§6 — 사용 쌍 전수 leak_guard (문서·곡선). 집계 + 대표 스탬프 반환."""
    from pretrain.leak_guard import assert_no_leak
    n_doc = n_curve = 0
    min_margin_doc, min_margin_curve = None, None
    rep = None
    for ei, t, sp, n_pre in pairs:
        k = keys[ei]
        as_of = dt.date.fromordinal(t).isoformat()
        if n_pre > 0:
            rows = [{"id": d[3], "published_at": d[2]} for d in docs[k][:n_pre]]
            st = assert_no_leak(rows, as_of, tag="1022 문서 ent=%s t=%s" % (k, as_of))
            n_doc += 1
            if st["여유일"] is not None and (min_margin_doc is None or st["여유일"] < min_margin_doc):
                min_margin_doc = st["여유일"]
            if rep is None:
                rep = st
        rows = [{"id": "curve|%d" % o,
                 "published_at": dt.date.fromordinal(o).isoformat()}
                for o in range(t - PRE, t)]
        st = assert_no_leak(rows, as_of, tag="1022 곡선 ent=%s t=%s" % (k, as_of))
        n_curve += 1
        if min_margin_curve is None or st["여유일"] < min_margin_curve:
            min_margin_curve = st["여유일"]
    return {"문서 검사 쌍(유문서)": n_doc, "곡선 검사 쌍": n_curve, "위반": 0,
            "최소 여유일(문서)": min_margin_doc, "최소 여유일(곡선)": min_margin_curve,
            "대표 스탬프(문서·실측 반환값)": rep}


def build_features(keys, ents, pairs):
    """곡선·조건·표적 텐서 (§1 — transition.SAO 미러)."""
    n = len(pairs)
    Sc = np.zeros((n, PRE), dtype=np.float32)
    R = np.zeros((n, POST), dtype=np.float32)
    C = np.zeros((n, len(DOMS) + 4), dtype=np.float32)
    base = np.zeros((n, 1), dtype=np.float32)
    split = np.zeros(n, dtype=np.int64)
    ent_i = np.zeros(n, dtype=np.int64)
    for i, (ei, t, sp, n_pre) in enumerate(pairs):
        dom_i, lo, vals = ents[keys[ei]]
        w = np.log1p(vals[t - PRE - lo: t + POST - lo])
        b = w[:PRE].mean()
        Sc[i] = w[:PRE] - b
        R[i] = w[PRE:] - b
        base[i, 0] = b
        d = dt.date.fromordinal(t)
        doy = d.timetuple().tm_yday
        C[i, dom_i] = 1.0
        C[i, len(DOMS)] = np.sin(2 * np.pi * doy / 365.0)
        C[i, len(DOMS) + 1] = np.cos(2 * np.pi * doy / 365.0)
        C[i, len(DOMS) + 2] = (d.year - 2013.0) / 10.0
        C[i, len(DOMS) + 3] = b
        split[i] = sp
        ent_i[i] = ei
    return {"Sc": Sc, "R": R, "C": C, "base": base, "split": split, "ent_i": ent_i}


def build_disc_features(keys, docs, pairs, emb, train_mask):
    """ⓑ 특징 12 (§2) — s_disc(τ90)·PCA8(train 유문서 쌍 적합)·스칼라 4 + z 표준화(train 통계).

    반환: F_b (n,12) float32 · pca 정보(설명분산 등) · ⓒ 스칼라 (n,2) 원시.
    """
    n = len(pairs)
    dated = [i for i, (ei, t, sp, np_) in enumerate(pairs) if np_ > 0]
    S = np.zeros((len(dated), emb.shape[1]), dtype=np.float32)
    scal = np.zeros((n, 4), dtype=np.float64)    # has_disc, log1p n_pre, log1p W, log1p Δt_last
    for j, i in enumerate(dated):
        ei, t, sp, n_pre = pairs[i]
        dl = docs[keys[ei]][:n_pre]
        d_ord = np.array([d[0] for d in dl], dtype=np.float64)
        rows = np.array([d[1] for d in dl], dtype=np.int64)
        delta = np.maximum(t - d_ord, 1.0)
        w = np.exp2(-delta / TAU)
        W = w.sum()
        S[j] = (w[:, None] * emb[rows].astype(np.float64)).sum(0) / W
        scal[i] = [1.0, np.log1p(n_pre), np.log1p(W), np.log1p(t - d_ord.max())]
    tr_dated = [j for j, i in enumerate(dated) if train_mask[i]]
    if len(tr_dated) >= 16:
        M = S[tr_dated].astype(np.float64)
        mu = M.mean(0)
        cov = (M - mu).T @ (M - mu) / max(len(M) - 1, 1)
        evals, evecs = np.linalg.eigh(cov)
        order = np.argsort(evals)[::-1][:8]
        comp = evecs[:, order]
        expl = float(evals[order].sum() / max(evals.sum(), 1e-12))
    else:  # 원리상 도달 안 해야 — 실측 게재용
        mu = S.mean(0) if len(S) else np.zeros(emb.shape[1])
        comp = np.zeros((emb.shape[1], 8))
        expl = 0.0
    P = np.zeros((n, 8), dtype=np.float64)
    if len(dated):
        P[np.array(dated)] = (S.astype(np.float64) - mu) @ comp
    F = np.concatenate([scal, P], axis=1)
    trF = F[train_mask]
    m, s = trF.mean(0), trF.std(0, ddof=0)
    s[s < 1e-6] = 1.0        # 수치상 영-분산(영-고유방향 포함) — 증폭 금지
    Fz = ((F - m) / s).astype(np.float32)
    return Fz, {"PCA8 설명분산비": expl, "PCA 적합 쌍(train 유문서)": len(tr_dated),
                "유문서 쌍": len(dated)}, scal[:, :2].copy()


# ── 모형 (§2 — Transition 축소판 미러) ─────────────────────────────────
def make_torch():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class Trunk(nn.Module):
        def __init__(self, d_in, hidden=HIDDEN, horizon=POST):
            super().__init__()
            self.horizon = horizon
            self.net = nn.Sequential(
                nn.Linear(d_in, hidden), nn.GELU(),
                nn.Linear(hidden, hidden), nn.GELU(),
                nn.Linear(hidden, horizon * 5))

        def forward(self, x):
            raw = self.net(x).view(-1, self.horizon, 5)
            q50 = raw[..., 0]
            g = F.softplus(raw[..., 1:5]) + 1e-4
            q25, q05 = q50 - g[..., 0], q50 - g[..., 0] - g[..., 1]
            q75, q95 = q50 + g[..., 2], q50 + g[..., 2] + g[..., 3]
            return torch.stack([q05, q25, q50, q75, q95], dim=-1)

    class SeqEncoder(nn.Module):
        """ⓒ — emb896→proj32 ⊕ Δt 2 → GRU(32) 마지막 은닉. 무문서→0 벡터."""
        def __init__(self, d_emb=896, d_proj=32, d_dt=2, d_h=32):
            super().__init__()
            self.proj = nn.Linear(d_emb, d_proj)
            self.gru = nn.GRU(d_proj + d_dt, d_h, batch_first=True)
            self.d_h = d_h

        def forward(self, seq_emb, seq_dt, lengths):
            B = seq_emb.shape[0]
            state = torch.zeros(B, self.d_h)
            has = lengths > 0
            if has.any():
                idx = torch.where(has)[0]
                x = torch.cat([self.proj(seq_emb[idx]), seq_dt[idx]], dim=-1)
                packed = nn.utils.rnn.pack_padded_sequence(
                    x, lengths[idx].cpu(), batch_first=True, enforce_sorted=False)
                _, h = self.gru(packed)
                state[idx] = h[-1]
            return state

    def pinball_loss(pred, target):
        t = target.unsqueeze(-1)
        losses = []
        for j, q in enumerate(QS):
            e = t[..., 0] - pred[..., j]
            losses.append(torch.maximum(q * e, (q - 1) * e).mean())
        return sum(losses) / len(QS)

    return torch, Trunk, SeqEncoder, pinball_loss


def pinball_cells(pred, target):
    """쌍별 핀볼(91×5 전 셀 평균) — numpy · transition.pinball 평균과 항등(자기시험 ㉠)."""
    t = target[..., None]
    qs = np.asarray(QS, dtype=np.float64)
    e = t - pred
    cell = np.maximum(qs * e, (qs - 1) * e)
    return cell.mean(axis=(1, 2))


def coverage_pairs(pred, target):
    return ((target >= pred[..., 0]) & (target <= pred[..., 4])).mean(axis=1)


def gather_seq(pairs, keys, docs, emb, idx, t_arr):
    """배치 idx 의 ⓒ 시퀀스 텐서 (B,N_SEQ,896)·Δt(B,N_SEQ,2)·길이."""
    B = len(idx)
    se = np.zeros((B, N_SEQ, emb.shape[1]), dtype=np.float32)
    sd = np.zeros((B, N_SEQ, 2), dtype=np.float32)
    ln = np.zeros(B, dtype=np.int64)
    for b, i in enumerate(idx):
        ei, t, sp, n_pre = pairs[i]
        if n_pre == 0:
            continue
        dl = docs[keys[ei]][:n_pre][-N_SEQ:]
        ln[b] = len(dl)
        for j, d in enumerate(dl):
            se[b, j] = emb[d[1]]
            delta = max(t - d[0], 1)
            sd[b, j, 0] = np.log1p(delta) / 10.0
            sd[b, j, 1] = 2.0 ** (-delta / TAU)
    return se, sd, ln


def train_arm(arm, seed, feat, extra, seq_ctx, threads=4):
    """한 팔·한 씨앗 학습(고정 3,000 스텝) → val 예측 (n_val,91,5)·파라미터 수·모형."""
    torch, Trunk, SeqEncoder, pinball_loss = make_torch()
    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    tr = np.where(feat["split"] == 0)[0]
    va = np.where(feat["split"] == 1)[0]
    d_extra = 0 if arm == "a" else (extra.shape[1] if arm == "b" else 2 + 32)
    d_in = PRE + feat["C"].shape[1] + d_extra
    trunk = Trunk(d_in)
    mods = [trunk]
    enc = None
    if arm == "c":
        enc = SeqEncoder()
        mods.append(enc)
    params = [p for m in mods for p in m.parameters()]
    n_par = sum(p.numel() for p in params)
    assert n_par <= PARAM_CAP, "파라미터 상한 초과 %d" % n_par
    opt = torch.optim.Adam(params, lr=LR)
    pairs, keys, docs, emb, c_scal = seq_ctx
    for step in range(STEPS):
        rng = np.random.default_rng([seed, step])
        ii = tr[rng.integers(0, len(tr), size=BATCH)]
        xs = [feat["Sc"][ii], feat["C"][ii]]
        if arm == "b":
            xs.append(extra[ii])
        x = torch.from_numpy(np.concatenate(xs, axis=1))
        if arm == "c":
            se, sd, ln = gather_seq(pairs, keys, docs, emb, ii, None)
            st = enc(torch.from_numpy(se), torch.from_numpy(sd), torch.from_numpy(ln))
            x = torch.cat([x, torch.from_numpy(c_scal[ii].astype(np.float32)), st], dim=1)
        pred = trunk(x)
        loss = pinball_loss(pred, torch.from_numpy(feat["R"][ii]))
        opt.zero_grad()
        loss.backward()
        opt.step()
    # val 예측 (배치 · eval)
    for m in mods:
        m.eval()
    preds = []
    with torch.no_grad():
        for s0 in range(0, len(va), 1024):
            ii = va[s0:s0 + 1024]
            xs = [feat["Sc"][ii], feat["C"][ii]]
            if arm == "b":
                xs.append(extra[ii])
            x = torch.from_numpy(np.concatenate(xs, axis=1))
            if arm == "c":
                se, sd, ln = gather_seq(pairs, keys, docs, emb, ii, None)
                st = enc(torch.from_numpy(se), torch.from_numpy(sd), torch.from_numpy(ln))
                x = torch.cat([x, torch.from_numpy(c_scal[ii].astype(np.float32)), st], dim=1)
            preds.append(trunk(x).numpy())
    return np.concatenate(preds, 0), n_par, mods


# ── 통계 (§3·§4) ─────────────────────────────────────────────────────
def cluster_boot_se(vals, clusters, B, seed):
    """개체 클러스터 붓스트랩 — 재추출 평균의 SD."""
    uc = np.unique(clusters)
    sums = np.zeros(len(uc))
    cnts = np.zeros(len(uc))
    inv = {c: i for i, c in enumerate(uc)}
    for v, c in zip(vals, clusters):
        sums[inv[c]] += v
        cnts[inv[c]] += 1
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(uc), size=(B, len(uc)))
    bs = sums[pick].sum(1) / cnts[pick].sum(1)
    return float(bs.std(ddof=1))


def sd_cl(vals, clusters):
    """클러스터 평균들의 SD(ddof=1)."""
    uc = np.unique(clusters)
    means = np.array([vals[clusters == c].mean() for c in uc])
    return float(means.std(ddof=1))


# ── 자기시험 ─────────────────────────────────────────────────────────
def selftest():
    out = {"자기시험": "pretrain/state_engine.py", "경우": []}
    ok = True
    # ㉠ 핀볼 항등 — transition.pinball(스칼라 평균) vs pinball_cells 평균
    import torch
    from pretrain.transition import pinball as t_pinball
    rng = np.random.default_rng(7)
    pred = np.sort(rng.normal(size=(13, POST, 5)), axis=-1).astype(np.float32)
    tgt = rng.normal(size=(13, POST)).astype(np.float32)
    a = float(t_pinball(torch.from_numpy(pred), torch.from_numpy(tgt)))
    b = float(pinball_cells(pred.astype(np.float64), tgt.astype(np.float64)).mean())
    good = abs(a - b) < 1e-5
    ok &= good
    out["경우"].append({"이름": "㉠ 핀볼 항등(transition.pinball)", "차": a - b, "기대대로": good})
    # 덮개율 — 전부 안/전부 밖
    inside = np.zeros((3, POST, 5)); inside[..., 0] = -9; inside[..., 4] = 9
    z = np.zeros((3, POST))
    good = coverage_pairs(inside, z).mean() == 1.0 and coverage_pairs(-inside, z + 99).mean() == 0.0
    ok &= good
    out["경우"].append({"이름": "덮개율 양극", "기대대로": bool(good)})
    # s_disc 가중 — 가까운 문서가 이긴다(τ 감쇠 방향)
    w1, w2 = 2.0 ** (-1 / TAU), 2.0 ** (-900 / TAU)
    good = w1 > w2 * 100
    ok &= good
    out["경우"].append({"이름": "감쇠 방향(Δ1 ≫ Δ900)", "기대대로": bool(good)})
    # 클러스터 SE — 상수면 0
    se = cluster_boot_se(np.ones(50), np.arange(50) % 5, 200, 1)
    good = se == 0.0
    ok &= good
    out["경우"].append({"이름": "클러스터 SE(상수=0)", "기대대로": bool(good)})
    out["전부_기대대로"] = bool(ok)
    return out


if __name__ == "__main__":
    print(json.dumps(selftest(), ensure_ascii=False, indent=1, default=str))
