# -*- coding: utf-8 -*-
"""1037 B부 — 시각 재부착 후 하류 재측정. 자는 1036 것 그대로(사전등록 §0-아).

  --stage repro    (ㄴ) 남기는 팔 = 1036 재현 기준선
  --stage measure  (ㄱ)버림 · (ㄷ)재부착 팔까지 전부

자 불변: y_event.npy 비트 동일 · 문서(문서id) 클러스터 10겹 GroupKFold ·
문서 클러스터 붓스트랩 1,000 · MDE 0.0427.
"""
import argparse, gzip, json, os, sys, time, hashlib, collections
import datetime as dt
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score

ROOT = Path("/Users/ax/world_model")
TF = Path("/Users/ax/wm_harvest/foundation/textfix1036")
OUT = Path("/Users/ax/wm_harvest/foundation/warc1037")
SEED = 1037
BOOT = 1000
MDE = 0.0427


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def load_base():
    rows = json.load(open(TF / "row_docid.json", encoding="utf-8"))
    y = np.load(TF / "y_event.npy")
    E = np.load(TF / "text_emb_body512.npz")
    emb = E[E.files[0]] if len(E.files) == 1 else E["emb"]
    key = {(r["개체"], r["언제"], r["문서id"]): i for i, r in enumerate(rows)}
    S = np.zeros((len(rows), 90), float)
    with gzip.open(ROOT / "data/ingest/sao973_hplt/pairs.jsonl.gz", "rt") as f:
        for line in f:
            p = json.loads(line); a = p["a_액션"]
            i = key.get((a["개체"], a["언제"], a["문서id"]))
            if i is not None:
                S[i] = p["s_상태"]["값"]
    assert np.isfinite(S).all() and np.isfinite(emb).all()
    return rows, y, emb, S


def curve_feats(S):
    L = np.log1p(np.maximum(S, 0))
    mu = L.mean(1, keepdims=True); sd = L.std(1, keepdims=True) + 1e-6
    Z = (L - mu) / sd                       # 수준 뺀 모양
    x = np.arange(90) - 44.5
    slope = (Z * x).sum(1) / (x * x).sum()
    last14 = L[:, -14:].mean(1) - L[:, :-14].mean(1)
    extra = np.column_stack([
        mu[:, 0], sd[:, 0], slope, last14,
        L.max(1) - np.median(L, 1), (S == 0).mean(1),
        np.median(L, 1), L[:, -1] - np.median(L, 1),
    ])
    return np.column_stack([Z, extra])


def cv_scores(X, y, groups, seed=SEED):
    """10겹 GroupKFold 홀드아웃 예측 점수."""
    pred = np.zeros(len(y))
    gkf = GroupKFold(n_splits=10)
    for tr, te in gkf.split(X, y, groups):
        sc = StandardScaler().fit(X[tr])
        m = LogisticRegression(max_iter=2000, C=0.1, solver="lbfgs")
        m.fit(sc.transform(X[tr]), y[tr])
        pred[te] = m.predict_proba(sc.transform(X[te]))[:, 1]
    assert np.isfinite(pred).all()
    return pred


def boot_ci(y, pa, pb, groups, n=BOOT, seed=SEED):
    """문서 클러스터 붓스트랩: AUC(b) − AUC(a) 의 95% CI."""
    rng = np.random.default_rng(seed)
    gs = np.array(groups)
    uniq = np.unique(gs)
    idxby = {g: np.where(gs == g)[0] for g in uniq}
    diffs = []
    for _ in range(n):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ii = np.concatenate([idxby[g] for g in pick])
        yy = y[ii]
        if yy.min() == yy.max():
            continue
        diffs.append(roc_auc_score(yy, pb[ii]) - roc_auc_score(yy, pa[ii]))
    d = np.array(diffs)
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), float(d.std(ddof=1))


def run_arms(name, mask, y, C, T, rows, res):
    idx = np.where(mask)[0]
    yy = y[idx]
    groups = [rows[i]["문서id"] for i in idx]
    if len(idx) < 200 or yy.min() == yy.max():
        res[name] = {"n": int(len(idx)), "실패": "표본 부족"}
        return
    out = {"n행": int(len(idx)), "n문서": int(len(set(groups))), "기저율": float(yy.mean())}
    preds = {}
    for arm, X in [("ⓐ곡선", C[idx]), ("ⓑ본문", T[idx]),
                   ("ⓒ곡선+본문", np.column_stack([C[idx], T[idx]]))]:
        p = cv_scores(X, yy, groups)
        preds[arm] = p
        out[arm] = round(float(roc_auc_score(yy, p)), 4)
    lo, hi, se = boot_ci(yy, preds["ⓐ곡선"], preds["ⓑ본문"], groups)
    out["ⓑ−ⓐ"] = round(out["ⓑ본문"] - out["ⓐ곡선"], 4)
    out["ⓑ−ⓐ CI95"] = [round(lo, 4), round(hi, 4)]
    out["ⓑ−ⓐ SE"] = round(se, 4)
    lo2, hi2, se2 = boot_ci(yy, preds["ⓐ곡선"], preds["ⓒ곡선+본문"], groups)
    out["ⓒ−ⓐ"] = round(out["ⓒ곡선+본문"] - out["ⓐ곡선"], 4)
    out["ⓒ−ⓐ CI95"] = [round(lo2, 4), round(hi2, 4)]
    out["MDE"] = MDE
    out["주판정"] = "통과" if (out["ⓑ−ⓐ"] >= MDE and lo > 0) else "못 넘었다"
    res[name] = out
    print(f"{name}: {json.dumps(out, ensure_ascii=False)}", flush=True)


def load_pub():
    """WARC 회수 발행일 + 기존 v1/v2 층."""
    pub = {}
    p = OUT / "warc_pub.jsonl"
    if p.exists():
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            if r.get("published_at"):
                pub[r["문서id"]] = (r["published_at"], "warc:" + r["method"])
    return pub


def load_panel():
    """위키 일별 패널: 키 → (첫날 ordinal, 값 배열)."""
    import glob
    panel = {}
    for fp in glob.glob(str(ROOT / "data/ingest/wiki_daily959/*.jsonl.gz")):
        for line in gzip.open(fp, "rt"):
            o = json.loads(line)
            days = o.get("날짜"); vals = o.get("값") or o.get("조회수") or o.get("views")
            if not days or not vals:
                continue
            d0 = dt.date(int(str(days[0])[:4]), int(str(days[0])[4:6]), int(str(days[0])[6:8]))
            arr = np.zeros(len(days), float)
            arr[:len(vals)] = vals[:len(days)]
            panel[o["키"]] = (d0.toordinal(), np.asarray(days), arr)
    return panel


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", default="measure")
    a = ap.parse_args()
    t0 = time.time()
    rows, y, emb, S = load_base()
    C = curve_feats(S)
    T = emb
    print(f"행 {len(rows):,} · 곡선특징 {C.shape} · 본문 {T.shape} · 기저 {y.mean():.6f}", flush=True)
    res = {"코드sha": {p: sha16(ROOT / p) for p in ["runners/warc1037_down.py", "runners/warc1037_fetch.py"]},
           "입력sha": {"y_event.npy": sha16(TF / "y_event.npy"),
                       "text_emb_body512.npz": sha16(TF / "text_emb_body512.npz"),
                       "row_docid.json": sha16(TF / "row_docid.json")}}
    run_arms("(ㄴ)남김 = 1036 재현", np.ones(len(y), bool), y, C, T, rows, res)
    if a.stage == "repro":
        (OUT / "down_repro.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{time.time()-t0:.0f}s", flush=True); return

    pub = load_pub()
    print(f"WARC 발행일 {len(pub):,} 문서", flush=True)
    # 층 병합: WARC 우선, 없으면 기존 v1, 그다음 v2
    v1 = json.load(open("/Users/ax/wm_harvest/foundation/pubdate/sao_state.json", encoding="utf-8"))["문서"]
    v2 = json.load(open("/Users/ax/wm_harvest/foundation/pubdate/v2/sao_state_v2.json", encoding="utf-8"))["문서"]
    def pubof(d):
        if d in pub: return pub[d]
        a1 = v1.get(d, {}).get("published_at")
        if a1: return (a1[:10], "v1")
        a2 = v2.get(d, {}).get("v2")
        if a2: return (str(a2)[:10], "v2")
        return (None, None)

    pd_row = []; diff = []
    for r in rows:
        p, m = pubof(r["문서id"])
        pd_row.append(p)
        diff.append(None if not p else (dt.date.fromisoformat(r["언제"]) - dt.date.fromisoformat(p)).days)
    res["발행일 붙은 행"] = int(sum(1 for p in pd_row if p))
    inwin = np.array([d is not None and 0 <= d <= 90 for d in diff])
    res["창안 행"] = int(inwin.sum())
    run_arms("(ㄱ)버림 = 창안만", inwin, y, C, T, rows, res)

    # (ㄷ) 재부착 — 패널에서 발행일 기준 s 재산출
    panel = load_panel()
    print(f"패널 키 {len(panel):,}", flush=True)
    S2 = S.copy(); ok = np.zeros(len(rows), bool)
    for i, r in enumerate(rows):
        p = pd_row[i]
        if not p or r["개체"] not in panel:
            continue
        d0ord, days, vals = panel[r["개체"]]
        pdt = dt.date.fromisoformat(p)
        want = [int((pdt - dt.timedelta(days=90 - k)).strftime("%Y%m%d")) for k in range(90)]
        pos = np.searchsorted(days, want)
        if pos[0] < 0 or pos[-1] >= len(days) or not (days[pos] == want).all():
            continue
        S2[i] = vals[pos]; ok[i] = True
    res["재부착 성공 행"] = int(ok.sum())
    print(f"재부착 성공 {ok.sum():,}", flush=True)
    C2 = curve_feats(S2)
    run_arms("(ㄷ)재부착", ok, y, C2, T, rows, res)
    run_arms("(ㄷ′)같은 행·재부착 안 함", ok, y, C, T, rows, res)
    (OUT / "down_measure.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)
    print(f"{time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
