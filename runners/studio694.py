"""노트 694 을 — 제작사가 만화 특징에 이미 담겨 있나. 564 짝."""
import json, sys
import numpy as np
sys.path.insert(0,"/Users/ax/world_model")
from sklearn.ensemble import HistGradientBoostingRegressor
from scipy.stats import spearmanr
from serve.ipmodel import pairs, feats, SAFE_COLS, T_SPLIT, BOOT

_,_,pr = pairs()
X,y,yr,st = [],[],[],[]
for m,a in pr:
    v,t = feats(m, dirty=False)
    pop = float(a.get("y_popularity") or 0)
    if not np.isfinite(t) or pop <= 0: continue
    X.append(v[list(SAFE_COLS)]); y.append(np.log10(pop)); yr.append(t)
    st.append(str(a.get("studio_name") or ""))
X,y,yr,st = np.array(X), np.array(y), np.array(yr), np.array(st)
tr,te = yr < T_SPLIT, yr >= T_SPLIT
print(f"배선: 짝 {len(y)} · 학습 {tr.sum()} · 유보 {te.sum()} · 제작사 이름 있는 행 {(st!='').sum()}", flush=True)

# **제작사 체급을 라벨 없이** --- 학습 행의 제작 편수만(노트 645)
from collections import Counter
cnt = Counter(st[tr][st[tr]!=""])
top10 = {s for s,_ in cnt.most_common(10)}
print("학습 상위 10곳:", [(s,c) for s,c in cnt.most_common(10)], flush=True)
def studio_cols(names):
    return np.column_stack([
        np.log10([cnt.get(s,0)+1 for s in names]),      # 학습 편수 로그
        [1.0 if s in top10 else 0.0 for s in names]])   # 상위 10곳인가

SC = studio_cols(st)
rng = np.random.default_rng(23)

def run(Xa, tag):
    rs, bs = [], []
    for s in range(3):
        g = HistGradientBoostingRegressor(max_iter=200, max_depth=3,
                                          learning_rate=0.06, random_state=s)
        g.fit(Xa[tr], y[tr]); p = g.predict(Xa[te])
        rs.append(float(spearmanr(p, y[te]).statistic))
        if s == 0:
            for _ in range(BOOT):
                i = rng.integers(0, len(p), len(p))
                if len(np.unique(y[te][i])) > 2:
                    bs.append(spearmanr(p[i], y[te][i]).statistic)
    out = {"팔": tag, "스피어만": round(float(np.mean(rs)),4),
           "씨앗SD": round(float(np.std(rs)),4), "열": Xa.shape[1],
           "부트2σ": round(float(2*np.std(bs)),4) if bs else None}
    print(json.dumps(out, ensure_ascii=False), flush=True)
    return out

A = run(X, "물음A 만화 특징만(기획 시점)")
B = run(np.hstack([X, SC]), "물음B + 제작사 2열(제작사 결정 뒤)")
# **위약** --- 제작사 값만 짝 안에서 섞는다
SCp = SC.copy(); rng.shuffle(SCp)
P = run(np.hstack([X, SCp]), "위약 제작사 값만 섞음")
# 열 하나 더한 차원 효과를 따로 --- 난수 2열
R = run(np.hstack([X, rng.normal(size=(len(y),2))]), "대조 난수 2열")

print(json.dumps({"B - A": round(B["스피어만"]-A["스피어만"],4),
                  "위약 - A": round(P["스피어만"]-A["스피어만"],4),
                  "난수 - A": round(R["스피어만"]-A["스피어만"],4),
                  "부트2σ": A["부트2σ"],
                  "판정": ("제작사가 더한다" if B["스피어만"]-A["스피어만"] > (A["부트2σ"] or 9)
                          else "**부트2σ 안 — 제작사는 만화 특징에 이미 담겨 있다**")},
                 ensure_ascii=False, indent=1), flush=True)
