"""출시 후 감쇠가 도메인을 넘나 — T3 두 번째 측정(노트 656).

**노트 655 가 잡은 무효 설계를 피한다.** 순위 지표에서 단일 특성의 전이는
부호가 전부이므로, 값을 옮기는 설계는 자동으로 무효다(전이/자기 비가 정확히
+1.00 으로 나온다). 그래서 **빼 놓은 도메인의 부호를 나머지가 맞히나**로만 잰다.
그리고 일치율은 **행 가중과 도메인 수를 같이** 적는다.

**관문 ③을 같이 잰다.** 감쇠 모수가 기존 위키 축 셋의 재인코딩이면 무엇이
나오든 무효다 — 출시 전 램프가 정확히 그래서 닫혔다(|r| 0.89~0.94).
결측 덩어리를 벗기고 잰다(노트 653).
"""
import glob
import json

import numpy as np
from scipy.stats import spearmanr

from lab import loop as L, trendaxes as ta

ta.set_wide(False); ta.set_grades(("A", "B", "C", "D", "E"))
from lab.harness import load           # noqa: E402
from lab.trendaxes import _ids         # noqa: E402

MIN_DAYS = 45


def fits():
    """레코드별 감쇠 모수. **규모를 없앤다** --- 안 그러면 wiki_level 사본."""
    out = {}
    for p in glob.glob("data/state/wiki_after/*.json"):
        try:
            j = json.load(open(p))
        except Exception:
            continue
        days = j.get("days") or []
        if len(days) < MIN_DAYS:
            continue
        v = np.array([x[1] for x in days], float)
        if v.mean() <= 0:
            continue
        v = v / v.mean()                                  # 규모 제거
        y = np.log(np.maximum(v, 1e-3))
        t = np.arange(len(y), dtype=float)
        # 감쇠율(하루당 log 변화) --- 음수면 잊혀 간다
        rate = float(np.polyfit(t, y, 1)[0])
        # 반감기: 첫 7일 평균의 절반으로 떨어지는 날
        head = v[:7].mean()
        hit = np.where(v <= head / 2)[0]
        half = float(hit[0]) if len(hit) else float(len(v))
        # 꼬리 두께: 뒤 30일 평균 / 앞 7일 평균
        tail = float(v[-30:].mean() / max(head, 1e-9))
        out[j.get("record_id") or p.split("/")[-1][:-5]] = (rate, half, tail)
    return out


F = fits()
print(json.dumps({"모양 맞춘 레코드": len(F), "최소일": MIN_DAYS},
                 ensure_ascii=False), flush=True)

d, ids = load(), _ids()
NAMES = ("감쇠율", "반감기", "꼬리")
for k, nm in enumerate(NAMES):
    data = {}
    for dom, keys in ids.items():
        if dom not in d.dom:
            continue
        _A, _M, y, _t = d.dom[dom]
        n = min(len(keys), len(y))
        xs, ys = [], []
        for i in range(n):
            if keys[i] in F and np.isfinite(y[i]):
                xs.append(F[keys[i]][k]); ys.append(float(y[i]))
        if len(xs) >= 40:
            data[dom] = (np.array(xs), np.array(ys))
    if len(data) < 4:
        print(json.dumps({nm: f"도메인 부족 {len(data)}"}, ensure_ascii=False), flush=True)
        continue
    own = {dm: float(spearmanr(*v).statistic) for dm, v in data.items()}
    okw = totw = 0
    okd = 0
    rows = []
    for dm in sorted(data, key=lambda x: -len(data[x][0])):
        others = [o for o in data if o != dm]
        num = sum(np.sign(own[o]) * len(data[o][0]) for o in others)
        pred = np.sign(num)
        hit = bool(pred == np.sign(own[dm]))
        w = len(data[dm][0])
        okw += hit * w; totw += w; okd += hit
        rows.append((dm, w, round(own[dm], 4), "맞음" if hit else "틀림"))
    print(json.dumps({nm: {"행 가중 일치": round(okw / totw, 3),
                           "도메인 일치": f"{okd}/{len(data)}",
                           "도메인별": rows}}, ensure_ascii=False), flush=True)

# 관문 ③ --- 기존 위키 축과 겹치나
from lab.guards import _drop_mode      # noqa: E402
w = L._wikisub()
print("\n관문 ③ — 감쇠 모수 ↔ 기존 위키 축", flush=True)
for k, nm in enumerate(NAMES):
    for ax in sorted(w):
        out = []
        for dom, (v, m) in w[ax].items():
            keys = ids.get(dom) or []
            n = min(len(v), len(keys))
            aa, bb = [], []
            for i in range(n):
                if m[i] > 0 and keys[i] in F:
                    aa.append(F[keys[i]][k]); bb.append(float(v[i]))
            if len(aa) >= 50:
                a2, b2 = _drop_mode(np.array(aa), np.array(bb))
                if a2 is None or len(np.unique(a2)) < 3:
                    continue
                r = spearmanr(a2, b2).statistic
                if np.isfinite(r) and abs(r) >= 0.5:
                    out.append((dom, round(float(r), 2)))
        if out:
            print(f"  {nm} ↔ {ax:16s} " + " · ".join(f"{a}{b:+.2f}" for a, b in out),
                  flush=True)
print("  (|r| 0.5 이상만 찍는다 · 0.85 넘으면 무효)", flush=True)
