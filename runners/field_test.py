"""유동인구 장에 **확산항이 있나** — 태풍 비유의 검증 가능한 부분.

사용자 가설: 사람들의 심리는 유체 같고, 한 곳에서 생긴 것이 주변으로 전이된다.

그 가설에서 **지금 자료로 잴 수 있는 조각**은 이것이다:

    어제 옆 동네의 이상치가 오늘 우리 동네를 예측하는가 --- 우리 동네의
    어제를 이미 아는데도?

되면 확산항이 실재한다. 안 되면 동네들이 서로 독립이라 '장' 이 아니라 그냥
264개의 따로 도는 시계열이다.

**이상치를 어떻게 만드나.** 원값을 그대로 쓰면 안 된다 --- 강남구가 늘 크고
일요일이 늘 크므로 그 둘만으로 상관이 잔뜩 나온다. 그래서 셋을 뺀다.

  ① 동네 수준   log 값에서 그 동네 평균을 뺀다
  ② 요일        요일 평균을 뺀다
  ③ **전국 공통 충격**  그날 전국 평균을 뺀다 --- 명절·연휴·날씨는 전국이
                 같이 움직인다. 이걸 안 빼면 **공통 요인이 확산으로 보인다.**
                 이게 이 검사에서 제일 중요한 통제다.

거리는 spot 좌표로 만든 동네 무게중심에서 잰다(``spot_geo`` + ``spot_addr``).
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")


def load_field():
    from ingest.visitors import series
    ser = series("2")                       # 외지인
    days = sorted({d for v in ser.values() for d in v})
    codes = sorted(c for c in ser if len(ser[c]) > len(days) * 0.9)
    M = np.full((len(codes), len(days)), np.nan)
    di = {d: i for i, d in enumerate(days)}
    for r, c in enumerate(codes):
        for d, v in ser[c].items():
            M[r, di[d]] = v
    return codes, days, M


def anomalies(M, days):
    """log → 동네·요일·**전국 공통 충격** 제거."""
    import datetime
    X = np.log10(np.where(M > 0, M, np.nan))
    X = X - np.nanmean(X, axis=1, keepdims=True)            # ① 동네
    dow = np.array([datetime.date(int(d[:4]), int(d[4:6]), int(d[6:8])).weekday()
                    for d in days])
    for w in range(7):                                       # ② 요일
        m = dow == w
        X[:, m] -= np.nanmean(X[:, m], axis=1, keepdims=True)
    X = X - np.nanmean(X, axis=0, keepdims=True)             # ③ 전국 공통 충격
    return X, dow


def centroids(codes):
    """spot 좌표 → 동네 무게중심."""
    from ingest.visitors import SIDO, sgg_index
    geo = json.loads((ROOT / "data/state/spot_geo.json").read_text())
    addr = json.loads((ROOT / "data/state/spot_addr.json").read_text())
    idx = sgg_index()
    acc = defaultdict(list)
    for sid, a in addr.items():
        if sid not in geo:
            continue
        sd = next((k for k, v in SIDO.items() if a.startswith(v)), None)
        if not sd:
            continue
        for tok in a.split()[1:3]:
            if (sd, tok) in idx:
                acc[idx[(sd, tok)]].append(geo[sid])
                break
    return {c: (float(np.mean([p[0] for p in v])), float(np.mean([p[1] for p in v])))
            for c, v in acc.items() if len(v) >= 3}


def km(a, b):
    dy = (a[0] - b[0]) * 111.0
    dx = (a[1] - b[1]) * 111.0 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def main():
    codes, days, M = load_field()
    X, _ = anomalies(M, days)
    cen = centroids(codes)
    keep = [i for i, c in enumerate(codes) if c in cen]
    X, codes = X[keep], [codes[i] for i in keep]
    print(json.dumps({"동네": len(codes), "날": len(days),
                      "관측": int(np.isfinite(X).sum())}, ensure_ascii=False), flush=True)

    # ── ① 공간 상관이 거리에 따라 줄어드나 (같은 날)
    D = np.array([[km(cen[a], cen[b]) for b in codes] for a in codes])
    Xc = np.where(np.isfinite(X), X, 0.0)
    C = np.corrcoef(Xc)
    iu = np.triu_indices(len(codes), 1)
    d, c = D[iu], C[iu]
    bins = [(0, 10), (10, 25), (25, 50), (50, 100), (100, 200), (200, 1000)]
    print("── 같은 날 공간 상관 (전국 공통 충격 제거 후)", flush=True)
    for lo, hi in bins:
        m = (d >= lo) & (d < hi)
        if m.sum() > 20:
            print(f"   {lo:>4}~{hi:<4}km  쌍 {int(m.sum()):>6}  평균 r {c[m].mean():+.4f}",
                  flush=True)

    # ── ② 확산: 어제 이웃이 오늘 나를 예측하나 (내 어제를 통제하고)
    NEAR = 25.0
    nb = [(D[i] < NEAR) & (np.arange(len(codes)) != i) for i in range(len(codes))]
    y, x_self, x_nb = [], [], []
    for i in range(len(codes)):
        if nb[i].sum() == 0:
            continue
        mine = X[i]
        near = np.nanmean(X[nb[i]], axis=0)
        ok = np.isfinite(mine[1:]) & np.isfinite(mine[:-1]) & np.isfinite(near[:-1])
        y.append(mine[1:][ok]); x_self.append(mine[:-1][ok]); x_nb.append(near[:-1][ok])
    y = np.concatenate(y); x_self = np.concatenate(x_self); x_nb = np.concatenate(x_nb)
    A1 = np.c_[np.ones_like(y), x_self]
    A2 = np.c_[np.ones_like(y), x_self, x_nb]
    b1, *_ = np.linalg.lstsq(A1, y, rcond=None)
    b2, *_ = np.linalg.lstsq(A2, y, rcond=None)
    r1 = 1 - ((y - A1 @ b1) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    r2 = 1 - ((y - A2 @ b2) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    # 계수의 표준오차
    res = y - A2 @ b2
    s2 = (res ** 2).sum() / (len(y) - 3)
    cov = s2 * np.linalg.inv(A2.T @ A2)
    se = math.sqrt(cov[2, 2])
    print(json.dumps({
        "── 확산 회귀": f"오늘(나) ~ 어제(나) + 어제(반경{int(NEAR)}km 이웃 평균)",
        "표본": int(len(y)),
        "어제(나) 계수": round(float(b2[1]), 4),
        "어제(이웃) 계수": round(float(b2[2]), 4),
        "이웃 계수 SE": round(se, 4),
        "t": round(float(b2[2] / se), 1),
        "R2 나만": round(float(r1), 4),
        "R2 이웃 추가": round(float(r2), 4),
        "R2 증분": round(float(r2 - r1), 5)}, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
