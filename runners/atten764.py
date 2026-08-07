"""노트 764 — **감쇠량이 해로움을 설명하나.** 창 안 백분위 축. 판 적합 없음."""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
from scipy.stats import rankdata, spearmanr

import ff753 as FF

T = 2025.0
MIN = 20
#: 노트 762 의 신호 몫(창 안 백분위 축)
SIG = {"웹툰": -0.0397, "도서": -0.0546, "시장팝업": 0.0446, "모바일": 0.0110,
       "펀딩": -0.0049, "애니": 0.0032, "세계애니": -0.0061, "만화": 0.0060,
       "게임": -0.0060, "팝업": -0.0034, "아이돌": 0.0008}
#: 노트 756 의 전 구간 백분위 축 상관(대조)
OLD = {"웹툰": (0.082, 0.022), "시장팝업": (-0.034, -0.121), "도서": (-0.020, -0.110),
       "애니": (0.077, 0.020), "모바일": (-0.017, 0.006), "게임": (0.021, 0.013),
       "만화": (0.051, -0.026), "세계애니": (0.053, -0.013), "아이돌": (0.125, 0.046),
       "팝업": (-0.310, 0.142), "펀딩": (0.004, -0.069)}


def main():
    yrs, sd, days, ck = FF.spread_series()
    d0 = FF.shell({})
    rows = {}
    for dm in sorted(d0.dom):
        y = np.asarray(d0.yr[dm], float)
        lab = np.asarray(d0.dom[dm][2], float)
        n = min(len(y), len(lab))
        y, lab = y[:n], lab[:n]
        m = np.isfinite(y) & (y >= yrs[0]) & np.isfinite(lab)
        if m.sum() < 2 * MIN:
            continue
        j = np.clip(np.searchsorted(yrs, y[m]), 0, len(sd) - 1)
        raw = sd[j]
        yy, ll = y[m], lab[m]
        tr, te = yy < T, yy >= T
        if tr.sum() < MIN or te.sum() < MIN:
            continue
        # **창 안 백분위** --- 노트 761 과 같은 변환
        p = np.zeros(len(yy))
        p[tr] = rankdata(raw[tr]) / tr.sum()
        p[te] = rankdata(raw[te]) / te.sum()
        a = float(spearmanr(p[tr], ll[tr]).statistic)
        b = float(spearmanr(p[te], ll[te]).statistic)
        rows[dm] = {"학습 상관": round(a, 3), "유보 상관": round(b, 3),
                    "**감쇠량 |학습|−|유보|**": round(abs(a) - abs(b), 3),
                    "부호 갈림": bool(np.sign(a) != np.sign(b)),
                    "학습 행": int(tr.sum()), "유보 행": int(te.sum()),
                    "신호 몫": SIG.get(dm),
                    "전구간 축 상관(노트 756)": list(OLD.get(dm, ())) or None}
    ks = list(rows)
    att = [rows[k]["**감쇠량 |학습|−|유보|**"] for k in ks]
    sig = [rows[k]["신호 몫"] for k in ks]
    r_as = spearmanr(att, sig)
    order = sorted(ks, key=lambda k: -rows[k]["**감쇠량 |학습|−|유보|**"])
    rank = {k: i + 1 for i, k in enumerate(order)}
    tr_abs = [abs(rows[k]["학습 상관"]) for k in ks]
    # 창 안 백분위가 상관을 바꿨나(틀림 조건)
    diff = [abs(rows[k]["학습 상관"] - OLD[k][0]) for k in ks if k in OLD]
    flip = [k for k in ks if rows[k]["부호 갈림"]]
    print(json.dumps({
        "도메인별": {k: rows[k] for k in order},
        "**감쇠 순위**": {k: rank[k] for k in order},
        "**감쇠량 ↔ 신호 몫 스피어만**": round(float(r_as.statistic), 3),
        "p": round(float(r_as.pvalue), 4),
        "웹툰 감쇠 순위": rank.get("웹툰"), "도서 감쇠 순위": rank.get("도서"),
        "학습 |상관| 중앙값": round(float(np.median(tr_abs)), 3),
        "부호 갈림": f"{len(flip)}/{len(ks)}", "갈리는 도메인": sorted(flip),
        "**창 안 백분위가 학습 상관을 바꿨나(중앙 절대차)**":
            round(float(np.median(diff)), 3),
        "판정 (가) 스피어만 ≤ −0.4 이고 웹툰·도서 감쇠 상위 4":
            bool(r_as.statistic <= -0.4 and rank.get("웹툰", 99) <= 4
                 and rank.get("도서", 99) <= 4),
        "판정 (나) −0.4 < 스피어만 < 0": bool(-0.4 < r_as.statistic < 0),
        "판정 (다) 스피어만 ≥ 0 → 감쇠도 아니다": bool(r_as.statistic >= 0),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
