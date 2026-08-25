# -*- coding: utf-8 -*-
"""기준 변수 하네스 v0 — 개입 특징 → «일평균 방문자» (사이클 1038).

왜 방문자인가(재논의 금지):
  `docs/아키텍처_결정기.md` §L2-4 가 효용 정본을 **일평균 방문자**로 «측정 전에» 고정했다.
  1038 이 그 선택을 실측으로 뒷받침했다 — 방문자·매출 둘 다 있는 92건의 **객단가가
  832원 ~ 23,286,957원(27,995배)** 로 흩어진다. 매출 = 방문자 × (28,000배로 흔들리는 것)
  이므로, 매출을 표적으로 삼으면 **원리상 못 맞히는 인자**를 맞히려 드는 것이다.
  객단가는 «예측 대상»이 아니라 «사용자가 넣는 손잡이»다.

🔴 이 모듈이 «주장하지 않는» 것:
  · 인과가 아니다. 개입은 무작위 배정이 아니다(조항 60). 조건부 연관까지만.
  · 1038-나 판정: 구조 특징(장소·도시·기간·태그) 12개로는 **기준선을 못 넘었다**
    (L1 회귀 log MAE 0.9898 vs 전체 중앙값 0.9181 · Δ +0.0726 CI95 [-0.0204,+0.1638]).
    누락 인자는 「누가 여는가」로 진단됐다 — 계수 상위가 전부 장소·기간이고 브랜드가 없다.
  · 브랜드 특징(1038-다)이 그 진단의 검정이다. 못 넘으면 «못 넘었다»로 적는다.

자(ruler) — 바꾸지 마라. 바꾸면 1038 과 비교가 죽는다:
  표적 log(일평균 방문자) · LOO · 기준선 = 전체 중앙값(MAE 최적) · 붓스트랩 4,000
  적합은 **L1(중앙값 회귀)** — 채점이 MAE 이므로 손실도 MAE 여야 한다(1038-가 사고).

씀:
    python3 -m harness.basevar             # 적합 + LOO 판정
    python3 -m harness.basevar --predict '{"venue_type":"백화점 팝업존","city":"서울특별시",...}'
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import glob
import hashlib
import json
import os
import re
from collections import Counter

import numpy as np

np.seterr(all="ignore")   # ⚠ 이 기계: numpy2.0.2+Accelerate 가 무해한 matmul 에도
                          #   divide-by-zero/overflow 를 올린다(einsum 과 비트 동일 확인).
                          #   경고로 수치 판정 금지 — 대신 아래에서 isfinite 로 «검사»한다.

REC_DIR = "/Users/ax/world_model/data/records"
ART = os.environ.get("WM_FOUNDATION_DIR", "/Users/ax/wm_harvest/foundation")
BRANDFEAT = os.path.join(ART, "brandfeat1038.jsonl")
BOOT_SEED = 10382
BOOT_B = 4000


def _sha16(path):
    """조항 66 — 산출물이 자기 출처를 대게 한다."""
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


# ── 자료 ──────────────────────────────────────────────────────────────
def load_rows():
    """레코드 → (코드, 일평균방문자, 조건, 개입). 방문자·일수 둘 다 있는 것만."""
    out = []
    for p in sorted(glob.glob(os.path.join(REC_DIR, "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        o = d.get("outcome") or {}
        t = o.get("totals") or {}
        cd = d.get("conditions") or {}
        per = cd.get("period") or {}
        daily = [r for r in (o.get("daily") or [])
                 if isinstance(r, dict) and r.get("visitors") is not None]
        if daily:
            v = sum(float(r["visitors"]) for r in daily)
            days = float(len(daily))
            src = "daily"
        elif t.get("visitors") is not None:
            v, days, src = float(t["visitors"]), per.get("days"), "totals"
        else:
            continue
        if not v or not days or v <= 0:
            continue
        out.append({"code": os.path.basename(p)[:-5], "vpd": v / float(days),
                    "days": float(days), "src": src,
                    "cond": cd, "iv": d.get("intervention") or {}})
    return out


def load_brandfeat():
    """1038-다: concept 텍스트에서 LLM 이 뽑은 «개최 전» 브랜드 특징."""
    m = {}
    if not os.path.exists(BRANDFEAT):
        return m
    for l in open(BRANDFEAT, encoding="utf-8"):
        try:
            d = json.loads(l)
        except Exception:
            continue
        if d.get("code") and "오류" not in d:
            m[d["code"]] = d
    return m


# ── 특징 ──────────────────────────────────────────────────────────────
def build_X(rows, bf, use_brand=True):
    n = len(rows)
    cols, names = [], []

    def loc(r):
        return (r["cond"].get("location") or {})

    def per(r):
        return (r["cond"].get("period") or {})

    def onehot(fn, topk, tag):
        vals = [fn(r) for r in rows]
        top = [k for k, _ in Counter([v for v in vals if v]).most_common(topk)]
        M = np.zeros((n, len(top)))
        for i, v in enumerate(vals):
            if v in top:
                M[i, top.index(v)] = 1
        return M, ["%s=%s" % (tag, t) for t in top]

    cols.append(np.log([r["days"] for r in rows])[:, None]); names.append("log(운영일수)")
    for fn, k, tag in ((lambda r: (loc(r).get("venue_type") or "").split("(")[0].strip(), 3, "장소"),
                       (lambda r: loc(r).get("city"), 2, "도시")):
        M, nm = onehot(fn, k, tag); cols.append(M); names += nm
    mon = np.array([int((per(r).get("from") or "2020-01-01")[5:7]) for r in rows])
    cols.append(np.c_[np.sin(2 * np.pi * mon / 12), np.cos(2 * np.pi * mon / 12)])
    names += ["월sin", "월cos"]
    tags = [" ".join((r["iv"].get("staging_tags") or [])) for r in rows]
    TOP = [t for t, _ in Counter(re.findall(r"[가-힣A-Za-z/]+", " ".join(tags))).most_common(4)]
    cols.append(np.array([[1.0 if t in tg else 0.0 for t in TOP] for tg in tags]))
    names += ["태그:%s" % t for t in TOP]

    if use_brand and bf:
        # 🔴 1038-다 — 「누가 여는가」. 결측은 «중앙 3»으로 채우되 지시자를 «반드시» 동반한다
        #    (조항 59 형 — 0 채움 금지).
        rec = np.array([float(bf.get(r["code"], {}).get("인지도") or 3) for r in rows])
        miss = np.array([0.0 if r["code"] in bf else 1.0 for r in rows])
        ip = np.array([1.0 if bf.get(r["code"], {}).get("유명IP결합") else 0.0 for r in rows])
        exp = np.array([1.0 if bf.get(r["code"], {}).get("체험형") else 0.0 for r in rows])
        cols.append(np.c_[rec, miss, ip, exp])
        names += ["인지도(1-5)", "인지도결측", "유명IP결합", "체험형"]
        M, nm = onehot(lambda r: bf.get(r["code"], {}).get("카테고리"), 4, "카테고리")
        cols.append(M); names += nm

    X = np.hstack(cols)
    assert np.isfinite(X).all(), "🔴 특징에 비유한 값"
    return X, names


# ── 적합 (L1 = 중앙값 회귀) ────────────────────────────────────────────
def l1fit(Z, y, lam, iters=60):
    w = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ y)
    for _ in range(iters):
        wt = 1.0 / np.maximum(np.abs(Z @ w - y), 0.05)
        A = (Z * wt[:, None]).T @ Z + lam * np.eye(Z.shape[1])
        try:
            w2 = np.linalg.solve(A, (Z * wt[:, None]).T @ y)
        except Exception:
            break
        if not np.isfinite(w2).all():
            break
        if np.abs(w2 - w).max() < 1e-8:
            return w2
        w = w2
    return w


def _std(X, m):
    mu, sd = X[m].mean(0), X[m].std(0)
    k = sd > 1e-8
    return np.c_[(X[:, k] - mu[k]) / sd[k], np.ones(len(X))], mu, sd, k


def loo(X, y, lam):
    n = len(y)
    p = np.zeros(n)
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        Z, _, _, _ = _std(X, m)
        p[i] = Z[i] @ l1fit(Z[m], y[m], lam)
    return p


def judge(rows, X, names, y, label):
    """자 정본 — 바꾸지 마라."""
    n = len(y)
    best = None
    for lam in (5, 15, 40, 100, 250, 600):
        p = loo(X, y, lam)
        e = np.abs(p - y).mean()
        if best is None or e < best[0]:
            best = (e, p, lam)
    _, pred, lam = best
    base = np.array([np.median(np.delete(y, i)) for i in range(n)])
    e_m, e_b = np.abs(pred - y), np.abs(base - y)
    rng = np.random.default_rng(BOOT_SEED)
    d = np.array([(e_m[s].mean() - e_b[s].mean())
                  for s in (rng.integers(0, n, n) for _ in range(BOOT_B))])
    lo, hi = np.percentile(d, [2.5, 97.5])
    verdict = ("모형이 낫다(0 배제)" if hi < 0 else
               ("🔴 이 자를 못 넘었다(0 포함)" if lo <= 0 <= hi else "🔴 기준선이 낫다"))
    return {"레인": label, "n": n, "특징수": X.shape[1], "lam": lam,
            "log MAE(모형)": round(float(e_m.mean()), 4),
            "log MAE(기준선=전체 중앙값)": round(float(e_b.mean()), 4),
            "×2 이내(모형)": round(float(np.mean(e_m < np.log(2))), 4),
            "×2 이내(기준선)": round(float(np.mean(e_b < np.log(2))), 4),
            "Δ": round(float(d.mean()), 4), "SE": round(float(d.std()), 4),
            "CI95": [round(float(lo), 4), round(float(hi), 4)],
            "판정": verdict, "붓스트랩": {"B": BOOT_B, "seed": BOOT_SEED}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ART, "basevar1038.json"))
    a = ap.parse_args()
    rows = load_rows()
    bf = load_brandfeat()
    y = np.log(np.array([r["vpd"] for r in rows]))
    print("표본 %d · 일평균방문자 중앙 %,.0f명/일 · 브랜드특징 %d건"
          .replace("%,", "%") % (len(rows), np.exp(np.median(y)), len(bf)))
    res = []
    for label, ub in (("A 구조 특징만 (1038-나 재현)", False),
                      ("B + 브랜드 특징 (1038-다)", True)):
        if ub and not bf:
            print("  [%s] 건너뜀 — 브랜드 특징 파일 없음 (없다≠못읽었다)" % label)
            continue
        X, names = build_X(rows, bf, use_brand=ub)
        r = judge(rows, X, names, y, label)
        res.append(r)
        print("\n[%s] 특징 %d" % (label, r["특징수"]))
        print("   모형   log MAE %.4f · ×2 이내 %.1f%%" % (r["log MAE(모형)"], 100 * r["×2 이내(모형)"]))
        print("   기준선 log MAE %.4f · ×2 이내 %.1f%%" % (r["log MAE(기준선=전체 중앙값)"], 100 * r["×2 이내(기준선)"]))
        print("   Δ %+.4f  SE %.4f  CI95 [%+.4f,%+.4f]  → %s"
              % (r["Δ"], r["SE"], r["CI95"][0], r["CI95"][1], r["판정"]))
    out = {"판": "기준 변수 하네스 v0 (1038)", "표본": len(rows),
           "표적": "log(일평균 방문자) — L2-4 정본",
           "레인": res,
           "출처(조항 66)": {"records": len(glob.glob(os.path.join(REC_DIR, '*.json'))),
                          "brandfeat.sha16": _sha16(BRANDFEAT),
                          "self.sha16": _sha16(os.path.abspath(__file__))},
           "🔴 안 주장하는 것": ["인과 아님(개입 무작위 아님)", "매출 예측 아님(객단가 27,995배)"]}
    json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
    print("\n→ %s" % a.out)


if __name__ == "__main__":
    main()
