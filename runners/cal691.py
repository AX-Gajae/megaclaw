"""노트 691 — 능력 자 둘: 캘리브레이션 + 80% 구간 덮음.

라벨은 이미 log10 · 예보는 도메인 안 백분위 꼴이므로 **등백분위 사상**으로
라벨 자리로 되돌린다. **분위표는 학습 행에서만**(노트 645).
"""
import json, sys
import numpy as np
sys.path.insert(0, "/Users/ax/world_model")
from lab import forms
from lab.harness import load, Data, MIN_TRAIN

T = 2025.0
SEEDS = 4
WIN = 0.05          # 구간을 만들 예보 백분위 창
LO, HI = 10.0, 90.0  # 80% 구간


def one(seed: int, data: Data, rng: np.random.Generator):
    """도메인 → {진짜 자, 위약 자}."""
    cls = forms.REGISTRY["F18_bagboost"]["cls"]
    train, tmask = {}, {}
    for d in data.dom:
        k = (np.isfinite(data.yr[d]) & (data.yr[d] < T)
             & np.isfinite(data.dom[d][2]))
        if k.sum() >= MIN_TRAIN:
            train[d] = data.slice(d, k); tmask[d] = k
    f = cls(seed=seed)
    f.fit(Data(train, data.names, {d: data.yr[d][tmask[d]] for d in train}))

    out = {}
    for d in data.dom:
        if d not in train:
            continue
        # ---- 학습 쪽 예보(분위표를 만드는 데만 쓴다)
        At, Mt, yt, tt = train[d]
        try:
            pt = np.asarray(f.predict(d, At, Mt, tt), float)
        except Exception:
            continue
        okt = np.isfinite(pt) & np.isfinite(yt)
        if okt.sum() < 50:
            continue
        pt, yt = pt[okt], yt[okt]

        # ---- 유보 쪽
        post = np.isfinite(data.yr[d]) & (data.yr[d] >= T)
        Ap, Mp, yp, tp = data.slice(d, post)
        try:
            pp = np.asarray(f.predict(d, Ap, Mp, tp), float)
        except Exception:
            continue
        okp = np.isfinite(pp) & np.isfinite(yp)
        if okp.sum() < 20:
            continue
        pp, yp = pp[okp], yp[okp]

        # **배선 검사** --- 유보 채점 행수가 harness 와 같나
        n_expect = int(data.rows(d, post=True, labeled=True, T=T).sum())

        def rulers(pred):
            """예보(백분위 꼴) → 자들."""
            # 등백분위 사상: 학습 예보의 백분위 → 학습 라벨의 같은 백분위
            r = np.searchsorted(np.sort(pt), pred, side="right") / len(pt)
            r = np.clip(r, 1e-6, 1 - 1e-6)
            yhat = np.quantile(yt, r)
            err = yhat - yp
            mae = float(np.median(np.abs(err)))
            dec = float(np.mean(np.abs(err) > 1.0))
            # 기울기: 실제 ~ 예측
            if np.std(yhat) > 1e-9:
                slope = float(np.polyfit(yhat, yp, 1)[0])
            else:
                slope = float("nan")
            # 80% 구간: 학습에서 같은 예보 백분위 창의 라벨 10~90분위
            rt = np.searchsorted(np.sort(pt), pt, side="right") / len(pt)
            cov, wid = [], []
            for rr, yy in zip(r, yp):
                m = np.abs(rt - rr) <= WIN
                if m.sum() < 15:
                    continue
                lo, hi = np.percentile(yt[m], [LO, HI])
                cov.append(lo <= yy <= hi); wid.append(hi - lo)
            return {"중앙절대오차": round(mae, 4),
                    "자릿수오차비율": round(dec, 4),
                    "기울기": round(slope, 4) if np.isfinite(slope) else None,
                    "구간덮음": round(float(np.mean(cov)), 4) if cov else None,
                    "구간폭": round(float(np.median(wid)), 3) if wid else None}

        real = rulers(pp)
        # **위약** --- 값만 도메인 안에서 섞는다(노트 335)
        sh = pp.copy(); rng.shuffle(sh)
        plac = rulers(sh)
        out[d] = {"유보": int(len(yp)), "harness유보": n_expect,
                  "배선일치": len(yp) == n_expect,
                  "라벨자리폭": round(float(yt.max() - yt.min()), 3),
                  "진짜": real, "위약": plac}
    return out


def main():
    data = load()
    per = {}
    for s in range(SEEDS):
        rng = np.random.default_rng(1000 + s)
        r = one(s, data, rng)
        print(json.dumps({"씨앗": s, "도메인수": len(r)}, ensure_ascii=False), flush=True)
        for d, v in r.items():
            per.setdefault(d, []).append(v)
    # 씨앗 평균 + SD
    agg = {}
    for d, vs in per.items():
        a = {"유보": vs[0]["유보"], "harness유보": vs[0]["harness유보"],
             "배선일치": all(v["배선일치"] for v in vs),
             "라벨자리폭": vs[0]["라벨자리폭"]}
        for arm in ("진짜", "위약"):
            a[arm] = {}
            for kk in vs[0][arm]:
                xs = [v[arm][kk] for v in vs if v[arm][kk] is not None]
                if xs:
                    a[arm][kk] = round(float(np.mean(xs)), 4)
                    a[arm][kk + "SD"] = round(float(np.std(xs, ddof=1)), 4) if len(xs) > 1 else None
        agg[d] = a
    # 판 가중 = 채점 유보 행수
    W = {d: agg[d]["유보"] for d in agg}
    tot = sum(W.values())
    board = {}
    for arm in ("진짜", "위약"):
        board[arm] = {}
        for kk in ("중앙절대오차", "자릿수오차비율", "기울기", "구간덮음", "구간폭"):
            num = sum(agg[d][arm].get(kk, 0) * W[d] for d in agg if kk in agg[d][arm])
            den = sum(W[d] for d in agg if kk in agg[d][arm])
            board[arm][kk] = round(num / den, 4) if den else None
    # 예측 ②: 자릿수오차비율 ↔ 라벨자리폭 스피어만
    from scipy.stats import spearmanr
    ds = sorted(agg)
    r2 = spearmanr([agg[d]["라벨자리폭"] for d in ds],
                   [agg[d]["진짜"]["자릿수오차비율"] for d in ds])
    print(json.dumps({"판": board, "가중합": tot,
                      "자리폭↔자릿수오차 스피어만": [round(float(r2.statistic), 3),
                                              round(float(r2.pvalue), 4), len(ds)],
                      "도메인별": agg}, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
