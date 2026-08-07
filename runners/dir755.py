"""노트 755 — **축↔라벨 방향이 학습과 유보에서 뒤집히나.** 판을 안 적합한다.

노트 754 가 장의 전국 시간축이 판을 해친다(−0.0192)를 확정했다. 기제 후보는
**방향 뒤집힘**이다 --- 학습에서 배운 부호를 유보에서 거꾸로 쓰는 것(노트 604 계열).
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
from scipy.stats import rankdata, spearmanr

import ff753 as FF
from lab import loop as L

T = 2025.0
MIN = 20
#: 노트 754 의 판 기여(대조용)
CONTRIB = {"웹툰": -0.00853, "시장팝업": -0.00423, "도서": -0.00395, "애니": -0.00127,
           "모바일": -0.00114, "펀딩": 0.00107, "게임": -0.00059, "세계애니": -0.00041,
           "만화": -0.00041, "팝업": 0.00023, "아이돌": 0.00008}


def main():
    yrs, sd, days, ck = FF.spread_series()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    rows = {}
    for dm in doms:
        y = np.asarray(d0.yr[dm], float)
        # 라벨: `dom` 튜플의 마지막이 라벨 벡터다(판이 쓰는 것)
        lab = np.asarray(d0.dom[dm][2], float)
        n = min(len(y), len(lab))
        y, lab = y[:n], lab[:n]
        m = np.isfinite(y) & (y >= yrs[0]) & np.isfinite(lab)
        v = np.full(n, np.nan)
        if m.sum():
            j = np.clip(np.searchsorted(yrs, y[m]), 0, len(sd) - 1)
            v[m] = sd[j]
        tr = m & (y < T)
        te = m & (y >= T)
        if tr.sum() < MIN or te.sum() < MIN:
            rows[dm] = {"건너뜀": f"학습 {int(tr.sum())} · 유보 {int(te.sum())}"}
            continue
        r_tr = spearmanr(v[tr], lab[tr])
        r_te = spearmanr(v[te], lab[te])
        a, b = float(r_tr.statistic), float(r_te.statistic)
        rows[dm] = {"학습 상관": round(a, 3), "유보 상관": round(b, 3),
                    "**부호 갈림**": bool(np.sign(a) != np.sign(b)),
                    "학습 행": int(tr.sum()), "유보 행": int(te.sum()),
                    "판 기여": CONTRIB.get(dm)}
    ok = {k: v for k, v in rows.items() if "**부호 갈림**" in v}
    flip = [k for k, v in ok.items() if v["**부호 갈림**"]]
    tr_abs = [abs(v["학습 상관"]) for v in ok.values()]
    # 부호 갈림 ↔ 판 기여
    fl = [1 if ok[k]["**부호 갈림**"] else 0 for k in ok]
    ct = [ok[k]["판 기여"] for k in ok]
    r_fc = spearmanr(fl, ct) if len(ok) > 3 else None
    print(json.dumps({
        "도메인별": dict(sorted(ok.items(), key=lambda x: x[1]["판 기여"])),
        "건너뜀": {k: v for k, v in rows.items() if "건너뜀" in v},
        "라벨 위치": "dom[dm][2] --- (n,) 실수 · 로그 척도로 보인다",
        "**부호 갈림**": f"{len(flip)}/{len(ok)}",
        "갈리는 도메인": sorted(flip),
        "**웹툰·도서가 갈리나**": {d: ok[d]["**부호 갈림**"] for d in ("웹툰", "도서")
                            if d in ok},
        "학습 |상관| 중앙값": round(float(np.median(tr_abs)), 3),
        "학습 |상관| 최대": round(float(np.max(tr_abs)), 3),
        "**부호 갈림 ↔ 판 기여 스피어만**":
            round(float(r_fc.statistic), 3) if r_fc else None,
        "판정 (가) 갈림 ≥ 6/11 이고 웹툰·도서 갈림":
            bool(len(flip) >= 6 and all(ok.get(d, {}).get("**부호 갈림**")
                                        for d in ("웹툰", "도서") if d in ok)),
        "판정 (나) 갈림 ≤ 4": bool(len(flip) <= 4),
        "판정 (다) 학습 |상관| 최대 > 0.15": bool(np.max(tr_abs) > 0.15),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
