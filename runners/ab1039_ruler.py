# -*- coding: utf-8 -*-
"""1039-가 — 두 자 대조 (조항 66).

같은 물음에 두 값이 나와 있다:
  1036(exp1036cv.py)   ⓐ0.5994 ⓒ0.5992 Δ−0.0002  SE .0322  「못 갈랐다」
  1037(warc1037_down)  ⓐ0.6522 ⓑ0.5716 Δ−0.0806  SE .0135  「곡선이 이긴다」

두 러너를 나란히 놓고 자구를 축별로 갈라 각 축이 Δ 를 얼마나 옮기는지 실측한다.
축: ① 사건 라벨 ② 분할 단위 ③ 팔(대비) 정의 ④ 붓스트랩 클러스터 단위 ⑤ 모형/정칙화

새 측정이 아니라 «이미 있는 두 자»의 분해다. 자료·라벨·임베딩은 손대지 않는다.
"""
import json, hashlib, time, sys, collections
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold

np.seterr(all="ignore")
TF = "/Users/ax/wm_harvest/foundation/textfix1036"
TRI = "/Users/ax/wm_harvest/foundation/triples"
OUTP = "/Users/ax/wm_harvest/foundation/warc1039"
SEED = 1039
BOOT = 1000


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def fast_auc(y, s):
    o = np.argsort(s, kind="mergesort")
    t = y[o]
    n1 = t.sum(); n0 = len(t) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    # 동률 평균 순위
    ss = s[o]
    r = np.empty(len(ss), float)
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[i:j + 1] = (i + j) / 2.0 + 1.0
        i = j + 1
    return (r[t == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


# ── 자료 ─────────────────────────────────────────────────────────────
z = np.load(f"{TRI}/sao.npz")
rows = json.load(open(f"{TF}/row_docid.json", encoding="utf-8"))
doms = json.load(open(f"{TRI}/domains.json", encoding="utf-8"))
Sraw = z["S"].astype(np.float64); Oraw = z["O"].astype(np.float64)
S = np.log1p(Sraw); O = np.log1p(Oraw)
base = np.median(S, axis=1, keepdims=True)

# ① 사건 라벨 — 두 자가 같은 y 를 쓰는가
y36 = ((O - base).max(axis=1) >= np.log(3)).astype(np.uint8)     # exp1036cv.py 자구
y37 = np.load(f"{TF}/y_event.npy").astype(np.uint8)              # warc1037_down.py 가 쓴 파일
y_raw = (Oraw.max(axis=1) >= 3 * np.median(Sraw, axis=1)).astype(np.uint8)  # 1037 이 시도한 재구성
LAB = {
    "y(1036 러너 자구, log1p 공간)": float(y36.mean()),
    "y_event.npy(1037 이 쓴 파일)": float(y37.mean()),
    "원공간 재구성 max(o)>=3*med(s)": float(y_raw.mean()),
    "1036자구 == y_event.npy 비트동일": bool(np.array_equal(y36, y37)),
    "원공간재구성 == y_event.npy 일치율": float((y_raw == y37).mean()),
}
y = y37.astype(int)

ents = np.array([r["개체"] for r in rows])
docs = np.array([r["문서"] for r in rows])       # 위키 문서 — 곡선(s,o)의 주인 (1035)
dids = np.array([r["문서id"] for r in rows])     # 웹 문서 — 본문/임베딩의 주인
dom = z["dom_id"]; year = z["year"].astype(np.float64); doy = z["doy"].astype(np.float64)

# ── 특징 ─────────────────────────────────────────────────────────────
Sc = S - base
DOM = np.zeros((len(S), len(doms))); DOM[np.arange(len(S)), dom] = 1
COV = np.c_[DOM, np.sin(2 * np.pi * doy / 365), np.cos(2 * np.pi * doy / 365), (year - 2013) / 10, base]
F_curve36 = np.c_[Sc, COV]                       # 1036 ⓐ


def curve_feats(Sr):                             # 1037 ⓐ (warc1037_down.py 자구 그대로)
    L = np.log1p(np.maximum(Sr, 0))
    mu = L.mean(1, keepdims=True); sd = L.std(1, keepdims=True) + 1e-6
    Z = (L - mu) / sd
    x = np.arange(90) - 44.5
    slope = (Z * x).sum(1) / (x * x).sum()
    last14 = L[:, -14:].mean(1) - L[:, :-14].mean(1)
    extra = np.column_stack([mu[:, 0], sd[:, 0], slope, last14,
                             L.max(1) - np.median(L, 1), (Sr == 0).mean(1),
                             np.median(L, 1), L[:, -1] - np.median(L, 1)])
    return np.column_stack([Z, extra])


F_curve37 = curve_feats(Sraw)
F_text = np.load(f"{TF}/text_emb_body512.npz")["E"].astype(np.float64)
uent = np.unique(ents)
ENT1H = np.zeros((len(rows), len(uent)))         # 영대조: 개체 ID 만
ENT1H[np.arange(len(rows)), np.searchsorted(uent, ents)] = 1

ARMS = {
    "ⓐ36 곡선(1036 자구: Sc90+도메인+계절+수준)": F_curve36,
    "ⓐ37 곡선(1037 자구: 모양Z90+요약8)": F_curve37,
    "ⓑ 본문512 단독": F_text,
    "ⓒ36 = ⓐ36 + 본문512": np.c_[F_curve36, F_text],
    "ⓒ37 = ⓐ37 + 본문512": np.c_[F_curve37, F_text],
    "ⓔ 개체ID one-hot 704 (영대조)": ENT1H,
}

# ── ② 분할 단위 ──────────────────────────────────────────────────────
def hb(s):
    return int(hashlib.md5(str(s).encode()).hexdigest()[:8], 16) % 10


SPLITS = {}
g = np.array([hb(d) for d in docs])
SPLITS["G위키 = md5(문서)%10 (1036)"] = [(np.where(g != k)[0], np.where(g == k)[0]) for k in range(10)]
SPLITS["G웹 = GroupKFold(문서id) (1037)"] = list(GroupKFold(n_splits=10).split(F_text, y, dids))


def leak_table():
    out = {}
    for name, folds in SPLITS.items():
        a = b = tot = 0
        for tr, te in folds:
            ds = set(docs[tr]); es = set(ents[tr]); tot += len(te)
            a += sum(1 for i in te if docs[i] in ds)
            b += sum(1 for i in te if ents[i] in es)
        out[name] = {"시험행": tot, "train 과 위키문서 공유": round(a / tot, 4),
                     "train 과 개체 공유": round(b / tot, 4),
                     "겹 크기": [int(len(te)) for _, te in folds]}
    return out


def cv(X, folds, C=0.1):
    p = np.zeros(len(y))
    for tr, te in folds:
        sc = StandardScaler().fit(X[tr])
        m = LogisticRegression(max_iter=2000, C=C, solver="lbfgs")
        m.fit(sc.transform(X[tr]), y[tr])
        p[te] = m.predict_proba(sc.transform(X[te]))[:, 1]
    assert np.isfinite(p).all()
    return p


# ── ④ 붓스트랩 클러스터 단위 ─────────────────────────────────────────
CLU = {"위키문서 485 (1036)": docs, "웹문서id 6564 (1037)": dids, "개체 704 (참고)": ents}


def boot(pa, pb, clus, n=BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    u = np.unique(clus); idx = {c: np.where(clus == c)[0] for c in u}
    d = []
    for _ in range(n):
        pick = rng.choice(u, size=len(u), replace=True)
        ii = np.concatenate([idx[c] for c in pick])
        yy = y[ii]
        if yy.min() == yy.max():
            continue
        d.append(fast_auc(yy, pb[ii]) - fast_auc(yy, pa[ii]))
    d = np.array(d)
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), float(d.std(ddof=1))


def main():
    t0 = time.time()
    rep = {"코드sha": {"runners/ab1039_ruler.py": sha16("/Users/ax/world_model/runners/ab1039_ruler.py"),
                       "runners/exp1036cv.py": sha16("/Users/ax/world_model/runners/exp1036cv.py"),
                       "runners/warc1037_down.py": sha16("/Users/ax/world_model/runners/warc1037_down.py")},
           "입력sha": {p: sha16(f"{TF}/{p}") for p in ["y_event.npy", "text_emb_body512.npz", "row_docid.json"]}
                     | {"sao.npz": sha16(f"{TRI}/sao.npz")},
           "①라벨": LAB,
           "②분할 누수": leak_table(),
           "분모": {"행": len(rows), "위키문서": len(set(docs)), "웹문서id": len(set(dids)),
                    "개체": len(set(ents)), "(개체,언제) 유일": len(set(zip(ents.tolist(), np.array([r['언제'] for r in rows]).tolist())))}}
    print(json.dumps(rep["①라벨"], ensure_ascii=False, indent=1), flush=True)
    print(json.dumps(rep["②분할 누수"], ensure_ascii=False, indent=1), flush=True)

    preds = {}; auc = {}
    for sname, folds in SPLITS.items():
        for aname, X in ARMS.items():
            p = cv(X, folds); preds[(sname, aname)] = p
            auc[(sname, aname)] = round(float(fast_auc(y, p)), 4)
            print(f"  [{sname}] {aname:<44} AUC {auc[(sname,aname)]:.4f}  ({time.time()-t0:.0f}s)", flush=True)
    rep["③팔×②분할 AUC"] = {s: {a: auc[(s, a)] for a in ARMS} for s in SPLITS}

    CON = [("Δ_대결(1037 헤드라인)", "ⓐ37 곡선(1037 자구: 모양Z90+요약8)", "ⓑ 본문512 단독"),
           ("Δ_대결(1036 곡선자구로)", "ⓐ36 곡선(1036 자구: Sc90+도메인+계절+수준)", "ⓑ 본문512 단독"),
           ("Δ_증분(1036 헤드라인)", "ⓐ36 곡선(1036 자구: Sc90+도메인+계절+수준)", "ⓒ36 = ⓐ36 + 본문512"),
           ("Δ_증분(1037 곡선자구로)", "ⓐ37 곡선(1037 자구: 모양Z90+요약8)", "ⓒ37 = ⓐ37 + 본문512")]
    out = {}
    for sname in SPLITS:
        for cname, A, B in CON:
            row = {"Δ": round(auc[(sname, B)] - auc[(sname, A)], 4)}
            for cl, cv_ in CLU.items():
                lo, hi, se = boot(preds[(sname, A)], preds[(sname, B)], cv_)
                row[cl] = {"CI95": [round(lo, 4), round(hi, 4)], "SE": round(se, 4), "MDE(2SE)": round(2 * se, 4)}
            out[f"{sname} | {cname}"] = row
            print(f"  {sname} | {cname}: Δ={row['Δ']:+.4f} " +
                  " ".join(f"[{k.split()[0]} SE {row[k]['SE']:.4f}]" for k in CLU), flush=True)
    rep["④대비×붓스트랩단위"] = out
    import os
    os.makedirs(OUTP, exist_ok=True)
    json.dump(rep, open(f"{OUTP}/ruler_ab.json", "w"), ensure_ascii=False, indent=1)
    print(f"\n총 {time.time()-t0:.0f}s → {OUTP}/ruler_ab.json", flush=True)


if __name__ == "__main__":
    main()
