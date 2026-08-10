"""경계 이동 — 노트 668. 네 팔 × T=2026. **T 를 evaluate 와 pooled 에 같이 넘긴다.**"""
import json
import numpy as np
from lab import forms, loop as L, guards as G
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12
AX = "vis_out"
T = 2026.0


def _shuf(v, m, rng):
    v = np.asarray(v, float).copy()
    idx = np.flatnonzero(np.asarray(m) > 0)
    v[idx] = v[rng.permutation(idx)]
    return v


def arm(mode):
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        if mode == "없이":
            return e
        from lab import visitoraxes as V
        old = V.DOMS
        V.DOMS = ("팝업",) if mode == "팝업만" else ("팝업", "시장팝업")
        try:
            w = V.build(axes=(AX,))
        finally:
            V.DOMS = old
        if not w:
            raise SystemExit(f"{mode}: 축이 비었다")
        if mode == "위약":
            rng = np.random.default_rng(668)
            w = {k: {d: (_shuf(v[0], v[1], rng), v[1]) for d, v in byd.items()}
                 for k, byd in w.items()}
        e.update(w)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def where(data):
    out = {}
    for dom, (A, M, _y, _t) in data.dom.items():
        nm = data.names.get(dom, [])
        if AX in nm:
            j = nm.index(AX)
            n = int((M[:, j] > 0).sum())
            if n:
                out[dom] = n
    return out


def per_seed(data):
    b, per = [], {}
    for s in range(SEEDS):
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        b.append(float(data.pooled(sc, T=T)))          # ← 노트 668 의 고침
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return np.array(b), {k: np.array(v) for k, v in per.items()}


def preds(data, seed=0):
    """도메인 → (예측, 라벨). 되뽑기 문턱을 재는 데 쓴다."""
    f = G._fit_on(lambda: CLS(seed=seed), data, T, seed=seed)
    out = {}
    for d in data.dom:
        p, y = G._predict_post(f, data, d, T)
        if p is None:
            continue
        ok = np.isfinite(p) & np.isfinite(y)
        if ok.sum() >= 20:
            out[d] = (np.asarray(p)[ok], np.asarray(y)[ok])
    return out


def boot_thr(pa, pb, B=400, seed=668):
    """도메인 안에서 행을 되뽑기해 **짝 Δρ 의 2σ** 를 잰다."""
    from scipy.stats import rankdata
    rng = np.random.default_rng(seed)
    doms = [d for d in pa if d in pb and len(pa[d][0]) == len(pb[d][0])]
    out = []
    for _ in range(B):
        na = nb = den = 0.0
        for d in doms:
            n = len(pa[d][0])
            i = rng.integers(0, n, n)
            for src, acc in ((pa, "a"), (pb, "b")):
                p, y = src[d]
                pp, yy = p[i], y[i]
                if len(np.unique(yy)) < 3:
                    r = np.nan
                else:
                    r = float(np.corrcoef(rankdata(pp), rankdata(yy))[0, 1])
                if acc == "a":
                    ra = r
                else:
                    rb = r
            if np.isfinite(ra) and np.isfinite(rb):
                na += ra * n; nb += rb * n; den += n
        if den:
            out.append(nb / den - na / den)
    a = np.array(out)
    return {"되뽑기 SD": round(float(a.std(ddof=1)), 5),
            "**2σ 문턱**": round(2 * float(a.std(ddof=1)), 4),
            "B": len(a), "도메인": len(doms)}


d0 = arm("없이")
b0, p0 = per_seed(d0)
print(json.dumps({"없이 판(T=2026)": round(float(b0.mean()), 4),
                  "씨앗SD": round(float(b0.std(ddof=1)), 4)}, ensure_ascii=False), flush=True)
q0 = preds(d0)
out = {}
for mode in ("팝업만", "팝업+시장", "위약"):
    d = arm(mode)
    print(json.dumps({f"{mode} 붙은 곳": where(d)}, ensure_ascii=False), flush=True)
    b1, p1 = per_seed(d)
    diff = b1 - b0
    out[mode] = {"판": round(float(b1.mean()), 4), "차": round(float(diff.mean()), 4),
                 "씨앗SE": round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 4),
                 "양수": f"{int((diff > 0).sum())}/{len(diff)}"}
    out[mode + "·도메인"] = {k: round(float((p1[k] - p0[k]).mean()), 4)
                           for k in p0 if k in p1 and len(p0[k]) == len(p1[k])}
    if mode == "팝업+시장":
        out["**되뽑기 문턱**"] = boot_thr(q0, preds(d))
        # 🔴 규약 47 금지 형태(상수/√n)지만 **자로 안 쓴다** — 바로 윗줄의 `되뽑기 문턱`
        # 이 판정에 쓰이는 자이고 이 값은 **어림이 얼마나 틀리는지 보이려고** 같이 찍는다.
        # 실측: 어림 0.0073 대 되뽑기 0.0125 = **1.7배** — √n 은 폭을 과소평가한다
        # (유보가 줄면 도메인 가중이 소수 도메인으로 몰려 잡음이 √n 보다 빨리 큰다).
        # 노트 893 이 원장에 올렸다. 역사로 둔다 — 이 줄이 곧 그 반례다.
        out["어림 배율값"] = round(0.0045 * (3369 / 1287) ** 0.5, 4)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
sig = out["팝업+시장"]["차"] - out["위약"]["차"]
print(json.dumps({"**신호 몫(③−④)**": round(sig, 4),
                  "**순효과(③−①)**": out["팝업+시장"]["차"],
                  "T=2025 신호 몫": 0.0064, "T=2025 순효과": 0.0016},
                 ensure_ascii=False), flush=True)
