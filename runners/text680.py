"""노트 680 — **제목 텍스트만으로 판의 얼마를 맞히나.** GBDT 를 안 돌린다.

문자 n-gram TF-IDF → 능형회귀. **학습 구간에서만 적합하고 유보에서 채점**한다.
도메인을 섞지 않는다(제목 길이·언어가 도메인 지시자가 되는 것을 막는다 · 사각 ①).
"""
import json
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge

from ingest.news_counts import SRC

S = Path("data/state")

#: 판 ρ **정본** --- 12도메인 · 유보 3,775 · 씨앗 0~11(노트 837 재기선 · `docs/용어.md`).
#: 🔴 이 자리는 **판정이지 기록이 아니다.** 아래 `비` 는 이 러너를 돌릴 때마다 오늘
#: 자료로 새로 계산되므로, 나누는 수도 **오늘의 정본**이어야 짝이 맞는다(조항 60 ---
#: 두 수를 이어 붙일 때 분모가 같은지 본다. 분자는 12도메인 유보에서 나온다).
#: 노트 680 이 인쇄한 「챔피언 판 0.4689」와 그 비(0.51)는 **11도메인 시대의 값이고
#: 837 재기선으로 은퇴했다** --- 그 기록은 노트 680 · 논문 132 · 원장에 남아 있고
#: 여기서 되살리지 않는다(옛 분모로 나눈 비는 오늘 분자와 분모가 다르다).
BOARD_RHO = 0.4710


def data():
    from lab import loop as L
    e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
         **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
    return L._idol(lambda: e, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def titles(dom):
    """레코드 id → 제목. `_ids()` 순서에 맞춰 리스트로."""
    from lab.trendaxes import _ids
    f, fld = SRC.get(dom, (None, None))
    if not f or not (S / f).exists():
        return None
    recs = json.loads((S / f).read_text())
    ids = _ids().get(dom) or []
    if isinstance(recs, dict):
        return [str((recs.get(k) or {}).get(fld) or "") for k in ids]
    return None


d = data()
out, rep = {}, {}
num = den = 0.0
for dom in d.dom:
    ts = titles(dom)
    if ts is None:
        rep[dom] = "제목 원천 없음"
        continue
    y = d.dom[dom][2]
    yr = d.yr[dom]
    n = min(len(ts), len(y), len(yr))
    ts, y, yr = ts[:n], y[:n], yr[:n]
    has = np.array([len(t.strip()) >= 2 for t in ts])
    tr = has & np.isfinite(y) & np.isfinite(yr) & (yr < 2025.0)
    te = has & np.isfinite(y) & np.isfinite(yr) & (yr >= 2025.0)
    if tr.sum() < 100 or te.sum() < 20:
        rep[dom] = f"행부족 학습{int(tr.sum())}/유보{int(te.sum())}"
        continue
    V = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4),
                        min_df=3, max_features=40000, sublinear_tf=True)
    Xtr = V.fit_transform([ts[i] for i in np.flatnonzero(tr)])
    Xte = V.transform([ts[i] for i in np.flatnonzero(te)])
    ytr = y[tr]
    # 라벨을 도메인 안 순위로 (스피어만 판정과 맞춘다)
    from scipy.stats import rankdata
    r = rankdata(ytr) / len(ytr)
    m = Ridge(alpha=1.0).fit(Xtr, r)
    p = m.predict(Xte)
    rho = float(spearmanr(p, y[te]).statistic)
    if not np.isfinite(rho):
        rep[dom] = "rho NaN"
        continue
    w = int(te.sum())
    out[dom] = {"rho": round(rho, 4), "학습": int(tr.sum()), "유보": w,
                "어휘": Xtr.shape[1]}
    num += rho * w; den += w
    rep[dom] = "ok"

print(json.dumps({"도메인별": out, "빠짐": {k: v for k, v in rep.items() if v != "ok"},
                  "**텍스트만 판 rho**": round(num / den, 4) if den else None,
                  "채점 유보 합": int(den),
                  "챔피언 판(정본 · 12도메인 · 유보 3,775 · 노트 837)": BOARD_RHO,
                  "비": round((num / den) / BOARD_RHO, 3) if den else None},
                 ensure_ascii=False, indent=1), flush=True)

# 판정이 양성이면 상위 n-gram 을 눈으로 (사각 ②)
if den and (num / den) >= 0.10:
    print("\n상위 n-gram — 사후 정보인지 눈으로 본다:", flush=True)
    for dom in list(out)[:4]:
        ts = titles(dom)
        y = d.dom[dom][2]; yr = d.yr[dom]
        n = min(len(ts), len(y), len(yr)); ts, y, yr = ts[:n], y[:n], yr[:n]
        has = np.array([len(t.strip()) >= 2 for t in ts])
        tr = has & np.isfinite(y) & np.isfinite(yr) & (yr < 2025.0)
        V = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3,
                            max_features=40000, sublinear_tf=True)
        X = V.fit_transform([ts[i] for i in np.flatnonzero(tr)])
        from scipy.stats import rankdata
        m = Ridge(alpha=1.0).fit(X, rankdata(y[tr]) / tr.sum())
        nm = np.array(V.get_feature_names_out())
        o = np.argsort(m.coef_)
        print(f"  {dom} 상위+: {list(nm[o[-12:]][::-1])}")
        print(f"  {dom} 상위-: {list(nm[o[:8]])}")
