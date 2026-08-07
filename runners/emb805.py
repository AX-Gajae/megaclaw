"""노트 805 — **동결 임베딩 병기.** 제목 → MiniLM → PCA8(학습만) → TabPFN concat.

도메인 셋(시장팝업·도서·게임 — 제목이 판 행과 정렬되는 곳만). 팔: A 기준 ·
B 병기 · C 위약 6(임베딩 행 섞기). 자 셋: 도메인 2σ · 2×뽑기SD · 위약 6/6.
"""
import json
import sys
import time

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/"
                   "ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from ingest.news_counts import titles

SEEDS = (0, 1, 2, 3)
DRAWS = 6
T = 2025.0
DOMS = ("시장팝업", "도서", "게임")
SIG2 = {"시장팝업": 0.0233, "도서": 0.0205, "게임": 0.0195}
K = 8


def embed_titles(ts):
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2",
                            device="cpu")
    return np.asarray(m.encode([t or "" for t in ts], batch_size=64,
                               show_progress_bar=False), float)


def pca_fit(Etr, k=K):
    """PCA 를 **학습 행에서만** 적합(노트 645). (평균, 성분) 을 돌려준다."""
    mu = Etr.mean(axis=0)
    U, S, Vt = np.linalg.svd(Etr - mu, full_matrices=False)
    return mu, Vt[:k]


def main():
    t0 = time.time()
    data = FF.shell(FF.base())
    from tabpfn import TabPFNRegressor

    wire, packs = {}, {}
    for d in DOMS:
        yr = np.asarray(data.yr[d], float)
        A, M, y, t = data.dom[d]
        y = np.asarray(y, float)
        ts = list(titles(d))
        ok_align = len(ts) == len(y)
        fin = np.isfinite(yr) & np.isfinite(y)
        ktr, kho = fin & (yr < T), fin & (yr >= T)
        wire[d] = {"제목": len(ts), "판 행": len(y), "정렬": ok_align,
                   "학습": int(ktr.sum()), "유보": int(kho.sum()),
                   "빈 제목": sum(1 for x in ts if not x)}
        if not ok_align:
            continue
        X = np.nan_to_num(np.hstack([A, M, np.asarray(t, float)[:, None]]),
                          nan=0.5)
        E = embed_titles(ts)
        mu, W = pca_fit(E[ktr])                     # 🔴 학습만
        E8 = (E - mu) @ W.T
        #: 눈금을 축과 맞춘다(0~1 근처) --- 학습 분포로 백분위화 대신 표준화
        s8 = E8[ktr].std(axis=0)
        s8[s8 < 1e-9] = 1.0
        E8 = (E8 - E8[ktr].mean(axis=0)) / s8 * 0.15 + 0.5
        packs[d] = (X, E8, y, ktr, kho)
    print(json.dumps({"배선": wire}, ensure_ascii=False), flush=True)

    res = {}
    for d, (X, E8, y, ktr, kho) in packs.items():
        Xb = np.hstack([X, E8])
        base, emb = [], []
        for s in SEEDS:
            for arm, XX, acc in (("A", X, base), ("B", Xb, emb)):
                m = TabPFNRegressor(device="cpu", random_state=s)
                m.fit(XX[ktr], y[ktr])
                p = np.asarray(m.predict(XX[kho]), float)
                acc.append(float(spearmanr(p, y[kho]).statistic))
        plac = []
        for i in range(DRAWS):
            rng = np.random.default_rng(8050 + i)
            E8s = E8.copy()
            idx = np.arange(len(E8s))
            rng.shuffle(idx)
            E8s = E8s[idx]                          # 행 통째 섞기(값만 · 노트 335)
            Xp = np.hstack([X, E8s])
            m = TabPFNRegressor(device="cpu", random_state=i)
            m.fit(Xp[ktr], y[ktr])
            p = np.asarray(m.predict(Xp[kho]), float)
            plac.append(float(spearmanr(p, y[kho]).statistic))
        a, b, pv = map(np.array, (base, emb, plac))
        diff = float(b.mean() - a.mean())
        psd = float(pv.std(ddof=1))
        thr = max(SIG2[d], 2 * psd)
        verdict = ("모" if (pv.max() - pv.min()) > 3 * abs(diff) and abs(diff) < thr
                   else "좋" if diff > thr and b.mean() > pv.max()
                   else "해" if diff < -thr
                   else "없")
        res[d] = {"A 기준": round(float(a.mean()), 4),
                  "A SD": round(float(a.std(ddof=1)), 4),
                  "B 병기": round(float(b.mean()), 4),
                  "B SD": round(float(b.std(ddof=1)), 4),
                  "**B−A**": round(diff, 4),
                  "위약 6": [round(float(x), 4) for x in pv],
                  "위약 평균": round(float(pv.mean()), 4),
                  "뽑기 SD": round(psd, 5),
                  "문턱(max(2σ, 2×뽑기SD))": round(thr, 4),
                  "위약 전부보다 큰가": bool(b.mean() > pv.max()),
                  "**판정**": verdict}
        print(f"[{d}] A {a.mean():.4f} → B {b.mean():.4f} · 차 {diff:+.4f} · "
              f"문턱 {thr:.4f} · {verdict} · {round(time.time()-t0,1)}초",
              flush=True)

    goods = [d for d in res if res[d]["**판정**"] == "좋"]
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "도메인별": res,
        "**(좋) 도메인**": goods or "없음",
        "**종합: 둘 이상 (좋) --- A1 확인 등록**": bool(len(goods) >= 2),
        "**종합: A1 제목 수준 기각**": bool(len(goods) < 2),
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
