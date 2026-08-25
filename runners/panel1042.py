# -*- coding: utf-8 -*-
"""1042 — P1 을 «분모를 키워» 다시 묻는다: 궤적 파운데이션이 곡선 특징에 증분을 주는가.

1041 §5-1: P1 은 네 레인 전부 부호가 양수인데 CI 가 0 을 포함했다. K=249 에서
MDE(2SE)≈0.037, 효과 +0.024 → **K≈600 이 필요**하다. 패널에 창 보유 개체 2,912 가 있다.

🔴 **인코더 누수 차단이 이 사이클의 핵심 설계다.**
`pretrain/traj.py` 인코더는 라벨을 안 봤지만 «궤적»은 봤다. 그러므로 평가는
**인코더의 검증 개체(개체 분리 · seed 1041 로 뽑힌 582개)로만** 한다.
학습 개체로 평가하면 h 에 유리하게 기울고, 그건 1035 가 겪은 누수와 같은 형태다.

사전등록 (측정 전 고정):
  · 표적/라벨: 1039~1041 정본 — 뒤 91일에 앞 90일 «중앙값»의 3배 이상 되는 날이 있는가
  · 표본: 인코더 val 개체만 · 개체당 창은 STRIDE=91 로 «겹치지 않게» 뽑는다
    (겹친 창은 라벨이 서로 새므로 독립이 아니다)
  · 분할: 10겹 GroupKFold(개체) — 같은 개체 창이 양쪽에 걸리면 누수
  · 붓스트랩: **개체** 클러스터 · B=1000 · seed 1039
  · 기준선: ⓐ37 곡선 자구 (1039 정본 · 약한 기준선 금지)
  · 🔴 판정 대비 하나: P1 = Δ(곡선+h64 − 곡선). 나머지는 [관찰].
  · 반증: CI95 가 0 을 포함하면 «이 자를 못 넘었다».
  · 검정력 사전 계산: K≈580 이면 MDE ≈ 0.0524·√(485/580) ≈ 0.048 … 🔴 1041 효과(+0.024)의
    2배다. **그러므로 K 만으로는 부족할 수 있고, 창 수가 늘어 SE 가 줄기를 기대한다.**
    (SE 는 클러스터 수와 클러스터 «안» 창 수 둘 다에 달렸다 — 후자가 1041 보다 훨씬 크다)

씀: python3 runners/panel1042.py
"""
import hashlib
import json
import os

import numpy as np
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

np.seterr(all="ignore")

ART = "/Users/ax/wm_harvest/foundation"
TRAJ = os.path.join(ART, "traj")
CTX, LAB_H = 90, 91
STRIDE = 91          # 🔴 겹치지 않게
BOOT, SEED = 1000, 1039
ENC_SEED = 1041      # pretrain/traj.py 의 SEED — val 개체를 «같은 자구»로 되뽑는다


def sha16(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def fast_auc(y, s):
    o = np.argsort(s)
    t = y[o]
    n1 = t.sum()
    n0 = len(t) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    return (np.arange(1, len(t) + 1)[t == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


class Enc(nn.Module):
    def __init__(s_, d):
        super().__init__()
        s_.c = nn.ModuleList([nn.Conv1d(1, 16, k, padding=k // 2) for k in (3, 7, 15, 31)])
        s_.g = nn.GRU(64, d, batch_first=True)
        s_.head = nn.Linear(d, 30)

    def enc(s_, x):
        h = torch.cat([torch.relu(c(x.unsqueeze(1))[:, :, :x.shape[1]]) for c in s_.c], 1)
        o, _ = s_.g(h.transpose(1, 2))
        return o[:, -1]


def curve_feats(Sr):
    L = np.log1p(Sr)
    m = L.mean(1, keepdims=True)
    sd = L.std(1, keepdims=True) + 1e-9
    Zc = (L - m) / sd
    l7, l30, f30 = L[:, -7:].mean(1), L[:, -30:].mean(1), L[:, :30].mean(1)
    return np.c_[Zc, m.ravel(), sd.ravel(), l7, l30, f30, l7 - l30, l30 - f30,
                 L.max(1) - L.min(1)]


def main():
    z = np.load(os.path.join(TRAJ, "windows.npz"), allow_pickle=True)
    ENT_ALL = z["ENT"]
    ents = np.unique(ENT_ALL)
    rng = np.random.default_rng(ENC_SEED)
    va_e = set(rng.choice(ents, max(1, len(ents) // 5), replace=False).tolist())
    print("인코더 val 개체 %d / 전체 %d — 이 개체로만 평가한다" % (len(va_e), len(ents)))

    # 패널을 다시 읽어 «겹치지 않는» CTX+91 창을 val 개체에서만 뽑는다
    import gzip
    PANEL = "/Users/ax/world_model/data/ingest/wiki_daily959"
    DOMS = ("팝업", "시장팝업", "웹툰", "애니", "게임", "도서", "만화", "모바일",
            "아이돌", "세계애니", "펀딩")
    ser = {}
    for dom in DOMS:
        p = os.path.join(PANEL, "%s.jsonl.gz" % dom)
        if not os.path.exists(p):
            continue
        for line in gzip.open(p, "rt", encoding="utf-8"):
            r = json.loads(line)
            ser.setdefault((dom, r["문서"]), {}).update(
                dict(zip([str(x) for x in r["날짜"]], r["조회수"])))
    days = sorted({d for s in ser.values() for d in s})
    dix = {d: i for i, d in enumerate(days)}
    keys = sorted(ser)          # 🔴 traj.build 와 «같은 정렬» — 개체 색인이 일치해야 한다
    X, ENT = [], []
    for i, k in enumerate(keys):
        if i not in va_e:
            continue
        row = np.full(len(days), np.nan, np.float32)
        for d, v in ser[k].items():
            row[dix[d]] = v
        for t0 in range(0, len(days) - CTX - LAB_H, STRIDE):
            w = row[t0:t0 + CTX + LAB_H]
            if np.isnan(w).any():
                continue
            X.append(w); ENT.append(i)
    X = np.asarray(X, np.float32)
    ENT = np.asarray(ENT)
    Sr = X[:, :CTX].astype(np.float64)
    Ofut = X[:, CTX:].astype(np.float64)
    L = np.log1p(Sr)
    base = np.median(L, axis=1, keepdims=True)
    y = ((np.log1p(Ofut) - base).max(axis=1) >= np.log(3)).astype(int)
    print("창 %d · 개체 %d · 기저율 %.3f  (겹침 없음 STRIDE=%d)"
          % (len(X), len(set(ENT.tolist())), y.mean(), STRIDE))

    ck = torch.load(os.path.join(TRAJ, "traj_v0.pt"), map_location="cpu")
    net = Enc(ck["d"]); net.load_state_dict(ck["sd"]); net.eval()
    Ln = (L - L.mean(1, keepdims=True)) / (L.std(1, keepdims=True) + 1e-6)
    with torch.no_grad():
        H = net.enc(torch.tensor(Ln, dtype=torch.float32)).numpy().astype(np.float64)
    F = curve_feats(Sr)
    arms = {"ⓐ37 곡선": F, "ⓕ h64(얼림)": H, "ⓕ+ 곡선+h64": np.c_[F, H]}
    gkf = GroupKFold(n_splits=10)
    pred, auc = {}, {}
    for k, Xa in arms.items():
        assert np.isfinite(Xa).all(), "🔴 비유한 %s" % k
        p = np.zeros(len(y))
        for tr, te in gkf.split(Xa, y, ENT):
            sc = StandardScaler().fit(Xa[tr])
            m = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(Xa[tr]), y[tr])
            p[te] = m.decision_function(sc.transform(Xa[te]))
        pred[k] = p
        auc[k] = round(float(fast_auc(y, p)), 4)
        print("   %-16s %.4f" % (k, auc[k]))

    rngb = np.random.default_rng(SEED)
    u = np.unique(ENT)
    idx = {c: np.where(ENT == c)[0] for c in u}

    def boot(a, b):
        out = []
        for _ in range(BOOT):
            sel = np.concatenate([idx[c] for c in rngb.choice(u, len(u))])
            yy = y[sel]
            if yy.sum() == 0 or yy.sum() == len(yy):
                continue
            out.append(fast_auc(yy, pred[a][sel]) - fast_auc(yy, pred[b][sel]))
        d = np.array(out)
        return (float(d.mean()), float(d.std()),
                float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))

    print("\n[붓스트랩 %d · 개체 %d 클러스터 · seed %d]" % (BOOT, len(u), SEED))
    res = {}
    for name, a, b in (("🔴 P1 Δ(곡선+h64 − 곡선)", "ⓕ+ 곡선+h64", "ⓐ37 곡선"),
                       ("[관찰] Δ(h64 단독 − 곡선)", "ⓕ h64(얼림)", "ⓐ37 곡선")):
        m, s, lo, hi = boot(a, b)
        v = "✅ 0 배제" if not (lo <= 0 <= hi) else "🔴 이 자를 못 넘었다"
        print("  %-26s Δ %+.4f  SE %.4f  CI95 [%+.4f,%+.4f]  %s" % (name, m, s, lo, hi, v))
        res[name] = {"Δ": round(m, 4), "SE": round(s, 4),
                     "CI95": [round(lo, 4), round(hi, 4)], "판정": v}
    out = {"판": "1042 — P1 재검(분모 확대)", "창": int(len(X)), "개체": int(len(u)),
           "기저율": round(float(y.mean()), 4), "STRIDE": STRIDE,
           "🔴 누수 차단": "인코더 val 개체(seed %d)로만 평가 — 학습 개체 제외" % ENC_SEED,
           "AUC": auc, "대비": res,
           "1041 비교": {"K": 249, "P1": 0.0239, "MDE": 0.037},
           "출처": {"self": sha16(os.path.abspath(__file__)),
                  "ckpt": sha16(os.path.join(TRAJ, "traj_v0.pt")),
                  "windows": sha16(os.path.join(TRAJ, "windows.npz"))}}
    json.dump(out, open(os.path.join(ART, "panel1042.json"), "w"), ensure_ascii=False, indent=1)
    print("\n→ %s/panel1042.json" % ART)


if __name__ == "__main__":
    main()
