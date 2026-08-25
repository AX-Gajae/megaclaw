# -*- coding: utf-8 -*-
"""1041 — 하류 판정: 궤적 파운데이션 h 가 곡선 특징을 넘는가 · 오염 제거 텍스트는 서는가.

두 물음을 «같은 판»에서 답한다. 자는 `runners/ab1039_ruler.py` 자구 승계(조항 66).

사전등록 (측정 전 고정):
  · 라벨/분할/붓스트랩/기준선: 1039 정본 그대로
      라벨 = 뒤 91일 3배 급등 · 분할 = G위키 md5(문서)%10 · 붓스트랩 = 위키문서 클러스터
      기준선 = ⓐ37 곡선 (1039 가 «더 강하다»고 판정한 자구 — 약한 기준선 금지)
  · 🔴 판정 대비 둘, 미리 지정한다:
      P1  Δ(ⓕ h64 + 곡선 − ⓐ37 곡선)    파운데이션이 «증분»을 주는가
      P2  Δ(ⓖ 오염제거 텍스트+곡선 − ⓐ37)  오염이 텍스트 실패의 원인이었는가
  · 오염 문턱은 **≥2회**를 정본으로 «미리» 고정(≥1·≥3 은 [관찰]).
    근거: 1041 사전 계수에서 K=249 로 1039 게이트 K≥174 를 넘는 가장 엄격한 축.
  · 반증: CI95 가 0 을 포함하면 «이 자를 못 넘었다».
  · 🔴 h 는 **얼린다**(gradient 없음). 사건 라벨을 본 적 없는 자기지도 표현이다.

씀: python3 runners/downstream1041.py
"""
import gzip
import hashlib
import json
import os

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

np.seterr(all="ignore")

ART = "/Users/ax/wm_harvest/foundation"
TFX = os.path.join(ART, "textfix1036")
TRI = os.path.join(ART, "triples")
BOOT, SEED = 1000, 1039
MENT_CANON = 2


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


rows = json.load(open(os.path.join(TFX, "row_docid.json"), encoding="utf-8"))
z = np.load(os.path.join(TRI, "sao.npz"))
Sraw = z["S"].astype(np.float64)
S = np.log1p(Sraw)
Ol = np.log1p(z["O"].astype(np.float64))
base = np.median(S, axis=1, keepdims=True)
y = ((Ol - base).max(axis=1) >= np.log(3)).astype(int)
docs = np.array([r["문서"] for r in rows])
n = len(rows)


def curve_feats(Sr):
    """1037 ⓐ 자구 — 1039 정본 기준선."""
    L = np.log1p(Sr)
    m = L.mean(1, keepdims=True)
    sd = L.std(1, keepdims=True) + 1e-9
    Zc = (L - m) / sd
    l7, l30, f30 = L[:, -7:].mean(1), L[:, -30:].mean(1), L[:, :30].mean(1)
    return np.c_[Zc, m.ravel(), sd.ravel(), l7, l30, f30, l7 - l30, l30 - f30,
                 L.max(1) - L.min(1)]


F_curve = curve_feats(Sraw)
H = np.load(os.path.join(ART, "traj", "h_sao.npz"))["H"].astype(np.float64)   # 얼린 h

# ── 오염 제거 텍스트 ───────────────────────────────────────────────────
txt = {}
for line in gzip.open(os.path.join(TFX, "doc_text.jsonl.gz"), "rt", encoding="utf-8"):
    d = json.loads(line)
    txt[d["문서id"]] = d["text"]
ment = np.array([txt.get(r["문서id"], "").count(r["문서"]) if r["문서"] else 0 for r in rows])
E = np.load(os.path.join(TFX, "text_emb_body512.npz"))["E"].astype(np.float64)
Ec = E - E.mean(0)
U, Sv, Vt = np.linalg.svd(Ec, full_matrices=False)
P = Vt[:8]
Ec = Ec - (Ec @ P.T) @ P
F_text = Ec / np.maximum(np.linalg.norm(Ec, axis=1, keepdims=True), 1e-9)


def hb(s):
    return int(hashlib.md5(str(s).encode()).hexdigest()[:8], 16) % 10


def cv(X, mask, C=0.1):
    """mask 부분표본 안에서 10겹 CV. 분할은 위키문서 해시(1039 정본)."""
    idx = np.where(mask)[0]
    g = np.array([hb(d) for d in docs[idx]])
    p = np.full(n, np.nan)
    for k in range(10):
        te = idx[g == k]
        tr = idx[g != k]
        if len(te) == 0 or len(np.unique(y[tr])) < 2:
            continue
        sc = StandardScaler().fit(X[tr])
        m = LogisticRegression(C=C, max_iter=2000).fit(sc.transform(X[tr]), y[tr])
        p[te] = m.decision_function(sc.transform(X[te]))
    return p


def boot(pa, pb, mask):
    rng = np.random.default_rng(SEED)
    sub = np.where(mask & ~np.isnan(pa) & ~np.isnan(pb))[0]
    cl = docs[sub]
    u = np.array(sorted(set(cl)))
    idx = {c: sub[cl == c] for c in u}
    out = []
    for _ in range(BOOT):
        sel = np.concatenate([idx[c] for c in rng.choice(u, len(u))])
        yy = y[sel]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        out.append(fast_auc(yy, pa[sel]) - fast_auc(yy, pb[sel]))
    d = np.array(out)
    return (float(d.mean()), float(d.std()),
            float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), len(u))


def run(mask, tag):
    arms = {"ⓐ37 곡선": F_curve,
            "ⓕ h64(얼림)": H,
            "ⓕ+ 곡선+h64": np.c_[F_curve, H],
            "ⓑ 본문512": F_text,
            "ⓖ 곡선+본문512": np.c_[F_curve, F_text]}
    pred, auc = {}, {}
    for k, X in arms.items():
        assert np.isfinite(X).all(), "🔴 비유한 %s" % k
        pred[k] = cv(X, mask)
        auc[k] = round(float(fast_auc(y[mask], pred[k][mask])), 4)
    print("\n[%s]  행 %d · 위키문서 %d · 기저율 %.3f"
          % (tag, mask.sum(), len(set(docs[mask])), y[mask].mean()))
    for k, v in auc.items():
        print("   %-18s %.4f" % (k, v))
    res = {"행": int(mask.sum()), "위키문서": len(set(docs[mask])),
           "기저율": round(float(y[mask].mean()), 4), "AUC": auc, "대비": {}}
    for name, a, b in (("P1 Δ(곡선+h64 − 곡선)", "ⓕ+ 곡선+h64", "ⓐ37 곡선"),
                       ("   Δ(h64 단독 − 곡선)", "ⓕ h64(얼림)", "ⓐ37 곡선"),
                       ("P2 Δ(곡선+본문 − 곡선)", "ⓖ 곡선+본문512", "ⓐ37 곡선"),
                       ("   Δ(본문 단독 − 곡선)", "ⓑ 본문512", "ⓐ37 곡선")):
        m, s, lo, hi, K = boot(pred[a], pred[b], mask)
        v = "✅ 0 배제" if not (lo <= 0 <= hi) else "🔴 못 넘었다"
        print("   %-24s Δ %+.4f  SE %.4f  CI95 [%+.4f,%+.4f]  K=%d  %s"
              % (name, m, s, lo, hi, K, v))
        res["대비"][name.strip()] = {"Δ": round(m, 4), "SE": round(s, 4),
                                    "CI95": [round(lo, 4), round(hi, 4)], "K": K, "판정": v}
    return res


def main():
    print("행 %d · 위키문서 %d · 기저율 %.3f · h %s"
          % (n, len(set(docs)), y.mean(), list(H.shape)))
    out = {"판": "1041 하류 판정", "자": "ab1039_ruler 자구 승계",
           "출처": {"self": sha16(os.path.abspath(__file__)),
                  "h": sha16(os.path.join(ART, "traj", "h_sao.npz")),
                  "ckpt": sha16(os.path.join(ART, "traj", "traj_v0.pt")),
                  "sao": sha16(os.path.join(TRI, "sao.npz"))},
           "레인": {}}
    out["레인"]["전체(오염 포함)"] = run(np.ones(n, bool), "전체 — 오염 포함")
    out["레인"]["정본 오염제거 ≥2회"] = run(ment >= MENT_CANON, "정본 — 개체명 ≥2회")
    for thr in (1, 3):
        out["레인"]["[관찰] ≥%d회" % thr] = run(ment >= thr, "[관찰] — 개체명 ≥%d회" % thr)
    json.dump(out, open(os.path.join(ART, "downstream1041.json"), "w"),
              ensure_ascii=False, indent=1)
    print("\n→ %s/downstream1041.json" % ART)


if __name__ == "__main__":
    main()
