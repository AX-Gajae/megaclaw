# 노트 821 — 경쟁 베이스라인 (사전등록: prereg821.md)
import json, sys, time
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import pairs as PR

t0 = time.time()
data = FF.shell(FF.base())
src = PR.SRC_DOM["KR 만화"]; names = list(data.names.get(src) or [])
recs = PR.build("KR 만화")
A, M, y, t = PR.to_arrays(recs, names)
X = np.nan_to_num(np.hstack([A, M, np.asarray(t, float)[:, None]]), nan=0.5)
fin = np.isfinite(y)
years = np.array([int(str((r.get("start_date") or "0000"))[:4] or 0) for r in recs.values()])
months = np.array([int((str(r.get("start_date") or "0000-00"))[5:7] or 0) for r in recs.values()])
dates = np.array([str(r.get("start_date") or "") for r in recs.values()])
ev = np.flatnonzero(fin & (years >= 2025))
pool = np.flatnonzero(fin & (years < 2025) & (years > 0))
wiring = {"행": int(len(y)), "y유한": int(fin.sum()), "열": int(X.shape[1]),
          "살아있는 축": int((M.mean(axis=0) > 0).sum()),
          "평가": int(len(ev)), "풀": int(len(pool))}
print(json.dumps({"배선": wiring}, ensure_ascii=False), flush=True)
assert wiring == {"행": 1716, "y유한": 1716, "열": 73, "살아있는 축": 4,
                  "평가": 322, "풀": 1394}, "배선 불일치 — 갈래 1"

def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    return float(spearmanr(p[ok], yy[ok])[0])

out = {}

# ⑴ 단일 축 그대로 (판정은 target_breadth 만 · 나머지는 참고)
AXN = ["target_breadth", "venue_prominence", "entry_friction", "goods_scale"]
single = {}
for a in AXN:
    j = names.index(a)
    obs = M[ev, j] > 0
    p = np.where(obs, A[ev, j], np.nan)
    single[a] = round(rho(p, y[ev]), 4)
out["⑴ 단일 축"] = single

# ⑵a 분기(계절) 평균 사상 — 풀에서만 배운다
q_of = lambda mm: np.clip((mm - 1) // 3 + 1, 1, 4)
qp, qe = q_of(months[pool]), q_of(months[ev])
qmean = {q: float(np.mean(y[pool][qp == q])) for q in (1, 2, 3, 4) if (qp == q).any()}
p = np.array([qmean.get(q, np.nan) for q in qe])
out["⑵a 분기 평균"] = round(rho(p, y[ev]), 4)

# ⑵b 시작일 순위(최근성)
ordv = np.argsort(np.argsort(dates[ev]))
out["⑵b 시작일 순위"] = round(rho(ordv.astype(float), y[ev]), 4)

# ⑶ 릿지 — 알파는 풀 안 5-fold 로만
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
alphas = [0.1, 1.0, 10.0, 100.0, 1000.0]
best_a, best_s = None, -9
for a in alphas:
    ss = []
    for tr, te in KFold(5, shuffle=True, random_state=0).split(pool):
        m = Ridge(alpha=a).fit(X[pool[tr]], y[pool[tr]])
        ss.append(rho(m.predict(X[pool[te]]), y[pool[te]]))
    s = float(np.mean(ss))
    if s > best_s:
        best_a, best_s = a, s
m = Ridge(alpha=best_a).fit(X[pool], y[pool])
p_r = m.predict(X[ev])
out["⑶ 릿지"] = {"alpha": best_a, "풀 CV": round(best_s, 4), "평가 ρ": round(rho(p_r, y[ev]), 4)}

# 릿지 위약 — 풀 라벨 셔플 6뽑기 (규약 20)
plc = []
for d in range(6):
    r2 = np.random.default_rng(8210 + d)
    ysh = y[pool].copy(); r2.shuffle(ysh)
    mp_ = Ridge(alpha=best_a).fit(X[pool], ysh)
    plc.append(rho(mp_.predict(X[ev]), y[ev]))
out["⑶ 위약(6)"] = {"평균": round(float(np.mean(plc)), 4), "최대": round(float(np.max(plc)), 4)}

# 원인 가르기: t 열 빼고 재적합 + 계수 상위
Xnt = X[:, :-1]
mnt = Ridge(alpha=best_a).fit(Xnt[pool], y[pool])
out["⑶ 릿지(t 제외)"] = round(rho(mnt.predict(Xnt[ev]), y[ev]), 4)
coef = np.abs(m.coef_)
top = np.argsort(-coef)[:6]
lab = names + [f"mask:{n}" for n in names] + ["t"]
out["⑶ 계수 상위"] = [(lab[i] if i < len(lab) else str(i), round(float(m.coef_[i]), 3)) for i in top]

# 판정 (갈래 2/3/4)
cands = dict(single)
cands["분기"] = out["⑵a 분기 평균"]; cands["시작일"] = out["⑵b 시작일 순위"]
cands["릿지"] = out["⑶ 릿지"]["평가 ρ"]
judged = {"target_breadth": single["target_breadth"], "분기": cands["분기"],
          "시작일": cands["시작일"], "릿지": cands["릿지"]}
best_name = max(judged, key=lambda k: judged[k] if np.isfinite(judged[k]) else -9)
best = judged[best_name]
CH = 0.2958
if out["⑶ 위약(6)"]["평균"] >= out["⑶ 릿지"]["평가 ρ"]:
    verdict = "1.배선/위약 — 릿지가 위약만 못함"
elif best >= 0.25:
    verdict = f"2.베이스라인 승 ({best_name} {best:+.4f} ≥ 0.25) — 전이 실질 우위 0"
elif best <= 0.05:
    verdict = "3.전이 승 — 0.2958 은 진짜"
else:
    gap = CH - best
    verdict = (f"4.중간 ({best_name} {best:+.4f}) — 우위 {gap:+.4f} "
               + ("≥ 0.025 유의" if gap >= 0.025 else "< 0.025 동급 — 서사 약화"))
out["**판정**"] = verdict
out["참고"] = {"전이(816)": "0.2958 ± 0.0200", "TabPFN800(816)": 0.3383}
out["초"] = round(time.time() - t0, 1)
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out821.json", "w"), ensure_ascii=False, indent=1)
