"""노트 760 — **공변량 이동인가.** 축의 값 분포가 학습과 유보에서 다른가. 판 적합 없음."""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
from scipy.stats import rankdata, spearmanr

import ff753 as FF

T = 2025.0
CONTRIB = {"웹툰": -0.00914, "시장팝업": -0.00369, "도서": -0.00262, "애니": -0.00139,
           "펀딩": 0.00074, "모바일": -0.00072, "만화": -0.00053, "팝업": 0.00050,
           "게임": -0.00040, "세계애니": -0.00034, "아이돌": 0.00004}


def main():
    yrs, sd, days, ck = FF.spread_series()
    r_t = spearmanr(yrs, sd)
    yint = np.floor(yrs).astype(int)
    byyear = {int(y): round(float(np.median(sd[yint == y])), 5)
              for y in sorted(set(yint.tolist()))}
    d0 = FF.shell({})
    rows = {}
    for dm in sorted(d0.dom):
        y = np.asarray(d0.yr[dm], float)
        ok = np.isfinite(y) & (y >= yrs[0])
        if ok.sum() < 20:
            continue
        j = np.clip(np.searchsorted(yrs, y[ok]), 0, len(sd) - 1)
        pct = rankdata(sd[j]) / ok.sum()
        yy = y[ok]
        tr, te = yy < T, yy >= T
        if tr.sum() < 10 or te.sum() < 10:
            continue
        q_tr = np.percentile(pct[tr], [25, 50, 75])
        q_te = np.percentile(pct[te], [25, 50, 75])
        lo = max(q_tr[0], q_te[0]); hi = min(q_tr[2], q_te[2])
        ov = max(0.0, hi - lo) / max(q_te[2] - q_te[0], 1e-9)
        rows[dm] = {"학습 백분위 사분위": [round(float(x), 3) for x in q_tr],
                    "유보 백분위 사분위": [round(float(x), 3) for x in q_te],
                    "**유보 중앙 − 0.5**": round(float(q_te[1] - 0.5), 3),
                    "**겹침 비율**": round(float(ov), 3),
                    "학습 행": int(tr.sum()), "유보 행": int(te.sum()),
                    "판 기여": CONTRIB.get(dm)}
    dev = {k: abs(v["**유보 중앙 − 0.5**"]) for k, v in rows.items()}
    far = [k for k, v in dev.items() if v >= 0.20]
    signs = {k: np.sign(rows[k]["**유보 중앙 − 0.5**"]) for k in rows}
    same = len({s for s in signs.values() if s != 0}) == 1
    ct = [rows[k]["판 기여"] for k in rows]
    dv = [dev[k] for k in rows]
    r_dc = spearmanr(dv, ct) if len(rows) > 3 else None
    print(json.dumps({
        "**원천 계열 ↔ 날짜 스피어만**": round(float(r_t.statistic), 3),
        "p": round(float(r_t.pvalue), 8),
        "연도별 원천 중앙값": byyear,
        "도메인별": dict(sorted(rows.items(), key=lambda x: -dev[x[0]])),
        "**유보 중앙이 0.5 에서 0.20 이상 벗어난 도메인**": f"{len(far)}/{len(rows)}",
        "그 목록": sorted(far),
        "**벗어남 방향이 다 같나**": bool(same),
        "겹침 비율 중앙값": round(float(np.median(
            [v["**겹침 비율**"] for v in rows.values()])), 3),
        "**벗어남 ↔ 판 기여 스피어만**": round(float(r_dc.statistic), 3) if r_dc else None,
        "판정 (가) 벗어난 도메인 ≥ 6": bool(len(far) >= 6),
        "판정 (나) ≤ 5": bool(len(far) <= 5),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
