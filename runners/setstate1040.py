# -*- coding: utf-8 -*-
"""1040 — 표현 교체: 문서 «한 편» → 개체-시점의 문서 «집합»(시간 가중).

왜: 1036~1039 가 텍스트를 열다섯 번(임베더 5 × 시각처리 3) 시험해 전부 곡선에 졌다.
1039 결론 — 「세 시각 처리 전부에서 ⓑ 가 .51~.57 → 시각이 아니라 «표현»이 병목」.
지금까지 «전부» 문서 한 편 → 벡터 하나 → 평균풀. 사용자가 처음부터 지적한 형태다:
  「문서 하나를 임베딩하는 걸로는 내재 상태를 못 담는다」

이 러너가 바꾸는 것은 **오직 표현 한 축**이다. 자·분할·붓스트랩·라벨은
`runners/ab1039_ruler.py` 자구를 그대로 물려쓴다(조항 66 — 자를 새로 짜지 않는다).

  s_disc(e,t,τ) = Σ_{d∋e, time(d)≤t} w(t−time(d))·v_d / Σ w      w(Δ)=2^(−Δ/τ)
  τ 격자 {30,90,180,365} «사전 고정» (docs/아키텍처_결정기.md §L1-3 규약)
  정본 τ=90 을 «미리» 지정 · 나머지는 [관찰] · 뒤집힘 지점 게재

사전등록(측정 전 고정):
  · 표적/라벨: 1039 정본 그대로 (뒤 91일 3배 급등 · 기저 25.7%)
  · 분할: G위키 = md5(문서)%10 — 1039 가 «옳다»고 판정한 쪽
  · 붓스트랩: 위키문서 485 클러스터 · B=1000 · seed 1039 자구
  · 기준선: ⓐ37 곡선(1039 가 «더 강하다»고 판정한 자구) — 약한 기준선 금지
  · 🔴 판정 대비는 **ⓓ − ⓑ**(집합 대 단일)이다. 이것이 표현 축을 «홀로» 가른다.
    ⓓ − ⓐ 는 부차 관찰(곡선 대 텍스트는 이미 1039 가 답했다).
  · 반증: ⓓ−ⓑ 의 CI95 가 0 을 포함하면 «집합으로 바꿔도 이 자를 못 넘었다».

씀: python3 runners/setstate1040.py
"""
import gzip
import hashlib
import json
import os
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

np.seterr(all="ignore")   # ⚠ 이 기계 Accelerate 가짜 경고 — isfinite 로 검사한다

ART = "/Users/ax/wm_harvest/foundation"
TFX = os.path.join(ART, "textfix1036")
TRI = os.path.join(ART, "triples")
PAIRS = "/Users/ax/world_model/data/ingest/sao973_hplt/pairs.jsonl.gz"
TAUS = [30, 90, 180, 365]
TAU_CANON = 90
BOOT, SEED = 1000, 1039


def sha16(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def fast_auc(y, s):
    o = np.argsort(s)
    t = y[o]
    n1 = t.sum()
    n0 = len(t) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    return (np.arange(1, len(t) + 1)[t == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


# ── 자료 (1039 자구) ───────────────────────────────────────────────────
rows = json.load(open(os.path.join(TFX, "row_docid.json"), encoding="utf-8"))
z = np.load(os.path.join(TRI, "sao.npz"))
doms = json.load(open(os.path.join(TRI, "domains.json"), encoding="utf-8"))
Sraw = z["S"].astype(np.float64)
O = z["O"].astype(np.float64)
S = np.log1p(Sraw)
Ol = np.log1p(O)
base = np.median(S, axis=1, keepdims=True)
y = ((Ol - base).max(axis=1) >= np.log(3)).astype(int)
Sc = S - base
docs = np.array([r["문서"] for r in rows])
dids = np.array([r["문서id"] for r in rows])
when = np.array([r["언제"] for r in rows])
n = len(rows)

dom, year, doy = z["dom_id"], z["year"].astype(np.float64), z["doy"].astype(np.float64)
DOM = np.zeros((n, len(doms)))
DOM[np.arange(n), dom] = 1
COV = np.c_[DOM, np.sin(2 * np.pi * doy / 365), np.cos(2 * np.pi * doy / 365),
            (year - 2013) / 10, base]


def curve_feats(Sr):
    """1037 ⓐ 자구 — 1039 가 «더 강한 기준선»으로 판정한 쪽."""
    L = np.log1p(Sr)
    m = L.mean(1, keepdims=True)
    sd = L.std(1, keepdims=True) + 1e-9
    Zc = (L - m) / sd
    last7 = L[:, -7:].mean(1)
    last30 = L[:, -30:].mean(1)
    first30 = L[:, :30].mean(1)
    summ = np.c_[m.ravel(), sd.ravel(), last7, last30, first30,
                 last7 - last30, last30 - first30, L.max(1) - L.min(1)]
    return np.c_[Zc, summ]


F_curve37 = curve_feats(Sraw)


# ── 문서 임베딩 → docid 사전 ───────────────────────────────────────────
E = np.load(os.path.join(TFX, "text_emb_body512.npz"))["E"].astype(np.float64)
doc_emb = {}
for i, r in enumerate(rows):
    doc_emb.setdefault(r["문서id"], E[i])
# 🔴 정규화 — 1036 §5: 원시 무작위쌍 코사인 0.9643. 집합 «합»에서는 치명적이다
#    (평균 방향이 문서 수에 비례해 쌓여 「문서가 많다」만 남는다)
M = np.stack([doc_emb[k] for k in doc_emb])
mu_e = M.mean(0)
U, Sv, Vt = np.linalg.svd(M - mu_e, full_matrices=False)
TOPK = 8
P = Vt[:TOPK]
for k in doc_emb:
    v = doc_emb[k] - mu_e
    v = v - (v @ P.T) @ P
    doc_emb[k] = v / max(np.linalg.norm(v), 1e-9)


# ── 개체 → 그 개체를 언급한 문서 전부 (시각 포함) ──────────────────────
ent_docs = {}
for line in gzip.open(PAIRS, "rt", encoding="utf-8"):
    a = json.loads(line)["a_액션"]
    ent_docs.setdefault(a.get("문서", ""), set()).add((a["문서id"], a["언제"]))

# 회수 발행일(1037) — 있으면 그 시각을 쓴다
pub = {}
wp = os.path.join(ART, "warc1037", "warc_pub.jsonl")
if os.path.exists(wp):
    for line in open(wp, encoding="utf-8"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        k = d.get("문서id") or d.get("id")
        p = d.get("published_at") or d.get("pub")
        if k and p:
            pub[k] = str(p)[:10]
sys.stderr.write("발행일 회수 사전 %d건\n" % len(pub))


def d2i(s):
    try:
        return np.datetime64(str(s)[:10]).astype("datetime64[D]").astype(int)
    except Exception:
        return None


def build_set_state(tau, use_pub):
    """s_disc(e,t,τ). 🔴 time(d) ≤ t 만 — 미래 문서 금지."""
    Xs = np.zeros((n, E.shape[1]))
    cnt = np.zeros(n)
    for i in range(n):
        t = d2i(when[i])
        pool = ent_docs.get(docs[i], ())
        num = np.zeros(E.shape[1])
        den = 0.0
        c = 0
        for did, w_when in pool:
            ts = pub.get(did) if use_pub else None
            td = d2i(ts) if ts else d2i(w_when)
            if td is None or t is None or td > t:
                continue
            w = 2.0 ** (-(t - td) / float(tau))
            v = doc_emb.get(did)
            if v is None:
                continue
            num += w * v
            den += w
            c += 1
        if den > 0:
            Xs[i] = num / den
        cnt[i] = c
    return Xs, cnt


def hb(s):
    return int(hashlib.md5(str(s).encode()).hexdigest()[:8], 16) % 10


g = np.array([hb(d) for d in docs])
FOLDS = [(np.where(g != k)[0], np.where(g == k)[0]) for k in range(10)]


def cv(X, C=0.1):
    p = np.zeros(n)
    for tr, te in FOLDS:
        sc = StandardScaler().fit(X[tr])
        m = LogisticRegression(C=C, max_iter=2000).fit(sc.transform(X[tr]), y[tr])
        p[te] = m.decision_function(sc.transform(X[te]))
    return p


def boot(pa, pb, clus):
    rng = np.random.default_rng(SEED)
    u = np.array(sorted(set(clus)))
    idx = {c: np.where(clus == c)[0] for c in u}
    out = []
    for _ in range(BOOT):
        sel = np.concatenate([idx[c] for c in rng.choice(u, len(u))])
        yy = y[sel]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        out.append(fast_auc(yy, pa[sel]) - fast_auc(yy, pb[sel]))
    d = np.array(out)
    return float(d.mean()), float(d.std()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main():
    F_single = np.stack([doc_emb[r["문서id"]] for r in rows])   # ⓑ 단일 문서(정규화)
    arms = {"ⓐ37 곡선(정본 기준선)": F_curve37,
            "ⓑ 단일 문서512(정규화)": F_single}
    meta = {}
    for tau in TAUS:
        Xs, cnt = build_set_state(tau, use_pub=False)
        arms["ⓓ 집합상태 τ=%d(크롤시각)" % tau] = Xs
        meta["τ=%d" % tau] = {"문서수 중앙": float(np.median(cnt)), "평균": round(float(cnt.mean()), 2),
                              "0건 행": int((cnt == 0).sum())}
    if pub:
        Xp, cp = build_set_state(TAU_CANON, use_pub=True)
        arms["ⓔ 집합상태 τ=%d(발행일)" % TAU_CANON] = Xp
        meta["발행일 τ=90"] = {"문서수 중앙": float(np.median(cp)), "0건 행": int((cp == 0).sum())}
    pred, auc = {}, {}
    for k, X in arms.items():
        assert np.isfinite(X).all(), "🔴 비유한: %s" % k
        pred[k] = cv(X)
        auc[k] = round(float(fast_auc(y, pred[k])), 4)
    print("행 %d · 위키문서 %d · 기저율 %.3f\n" % (n, len(set(docs)), y.mean()))
    print("집합 크기:", json.dumps(meta, ensure_ascii=False))
    print("\n%-34s %s" % ("팔", "AUC"))
    for k, v in auc.items():
        print("  %-32s %.4f" % (k, v))
    CANON = "ⓓ 집합상태 τ=%d(크롤시각)" % TAU_CANON
    SINGLE = "ⓑ 단일 문서512(정규화)"
    CURVE = "ⓐ37 곡선(정본 기준선)"
    print("\n[붓스트랩 %d · 위키문서 485 클러스터 · seed %d]" % (BOOT, SEED))
    con = [("🔴 판정 Δ(ⓓτ90 − ⓑ단일) = 표현 축", CANON, SINGLE)]
    for tau in TAUS:
        if tau != TAU_CANON:
            con.append(("[관찰] Δ(ⓓτ%d − ⓑ단일)" % tau, "ⓓ 집합상태 τ=%d(크롤시각)" % tau, SINGLE))
    if pub:
        con.append(("[관찰] Δ(ⓔ발행일 − ⓓ크롤)", "ⓔ 집합상태 τ=%d(발행일)" % TAU_CANON, CANON))
    con.append(("[부차] Δ(ⓓτ90 − ⓐ곡선)", CANON, CURVE))
    out = {}
    for name, a, b in con:
        m, s, lo, hi = boot(pred[a], pred[b], docs)
        v = "✅ 0 배제" if not (lo <= 0 <= hi) else "🔴 이 자를 못 넘었다"
        print("  %-36s Δ %+.4f  SE %.4f  CI95 [%+.4f,%+.4f]  %s" % (name, m, s, lo, hi, v))
        out[name] = {"Δ": round(m, 4), "SE": round(s, 4), "CI95": [round(lo, 4), round(hi, 4)], "판정": v}
    rep = {"판": "1040 표현 교체 — 문서 집합 상태", "행": n, "위키문서": len(set(docs)),
           "기저율": round(float(y.mean()), 4), "τ격자": TAUS, "정본τ": TAU_CANON,
           "집합크기": meta, "AUC": auc, "대비": out,
           "자": "runners/ab1039_ruler.py 자구 승계 (분할 G위키 · 붓스트랩 위키문서 · 기준선 ⓐ37)",
           "출처": {"self": sha16(os.path.abspath(__file__)),
                  "emb": sha16(os.path.join(TFX, "text_emb_body512.npz")),
                  "sao": sha16(os.path.join(TRI, "sao.npz"))}}
    json.dump(rep, open(os.path.join(ART, "setstate1040.json"), "w"), ensure_ascii=False, indent=1)
    print("\n→ %s/setstate1040.json" % ART)


if __name__ == "__main__":
    main()
