"""제작사 고정효과 R² 0.3865 가 표본 안 값인가 --- 유보에서 다시 잰다."""
import json, sys
import numpy as np
sys.path.insert(0,"/Users/ax/world_model")
from serve.ipmodel import pairs, feats, SAFE_COLS, T_SPLIT

_,_,pr = pairs()
y,yr,st,X = [],[],[],[]
for m,a in pr:
    v,t = feats(m, dirty=False); pop=float(a.get("y_popularity") or 0)
    if not np.isfinite(t) or pop<=0: continue
    y.append(np.log10(pop)); yr.append(t); st.append(str(a.get("studio_name") or ""))
    X.append(v[list(SAFE_COLS)])
y,yr,st,X = np.array(y), np.array(yr), np.array(st), np.array(X)
tr,te = yr<T_SPLIT, yr>=T_SPLIT

def r2(yt, pred):
    ss_t=((yt-yt.mean())**2).sum(); return 1 - ((yt-pred)**2).sum()/ss_t

# ① 표본 안 (노트 692 가 쟀던 것) --- 전 행에서 제작사 평균
uq,inv = np.unique(st, return_inverse=True)
pred_in = np.array([y[inv==i].mean() for i in inv])
print(f"① 표본 안 제작사 R² = {r2(y,pred_in):.4f}  (제작사 {len(uq)}곳 · 행 {len(y)} · 자유도 {len(uq)/len(y):.1%})")

# ② 유보 --- **학습 행에서만** 제작사 평균을 만들고 유보에 쓴다(노트 645)
gm = y[tr].mean()
mean_tr = {}
for s in np.unique(st[tr]):
    m = (st==s)&tr
    if m.sum()>=1: mean_tr[s]=y[m].mean()
pred_te = np.array([mean_tr.get(s, gm) for s in st[te]])
seen = np.array([s in mean_tr for s in st[te]])
print(f"② 유보 제작사 R² = {r2(y[te],pred_te):+.4f}  (유보 {te.sum()}행 · 학습에서 본 제작사 {seen.sum()}/{te.sum()})")
# 본 제작사만
if seen.sum()>=20:
    print(f"   학습에서 본 것만: R² = {r2(y[te][seen],pred_te[seen]):+.4f} (n={seen.sum()})")
# ③ 견줌: 만화 특징 단독 유보 R²
from sklearn.ensemble import HistGradientBoostingRegressor
g=HistGradientBoostingRegressor(max_iter=200,max_depth=3,learning_rate=0.06,random_state=0)
g.fit(X[tr],y[tr])
print(f"③ 만화 특징 단독 유보 R² = {r2(y[te], g.predict(X[te])):+.4f}")
# ④ 노트 692 가 쟀던 만화 라벨 단독(표본 안)도 다시
mp=[]
for m,a in pr:
    v,t=feats(m,dirty=True); pop=float(a.get("y_popularity") or 0)
    if not np.isfinite(t) or pop<=0: continue
    mp.append(v[10])   # 인기 로그
mp=np.array(mp)
sl=np.polyfit(mp,y,1)
print(f"④ 표본 안 만화 인기 단독 R² = {r2(y,np.polyval(sl,mp)):.4f}  (노트 692 의 0.4412)")
sl2=np.polyfit(mp[tr],y[tr],1)
print(f"   같은 것 유보 = {r2(y[te],np.polyval(sl2,mp[te])):+.4f}")
