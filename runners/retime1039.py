# -*- coding: utf-8 -*-
"""1039-나 — 「문서를 «맞는 시점»에 붙이면 텍스트가 곡선을 이기는가」

자는 새로 짜지 않는다. 1039-가(`runners/ab1039_ruler.py`)가 판정한 «정본 자»를 쓴다:
  · 라벨   y_event.npy 비트 동일 (1036·1037 이 이미 같은 것을 쓴다 — 대조로 확인)
  · 분할   md5(위키문서)%10 10겹        ← 1036 이 옳다 (1037 의 문서id 분할은 영대조 0.8352 누수)
  · 붓스트랩 위키문서 485 클러스터        ← 1036 이 옳다 (1037 의 6,564 은 SE 1.87배 낙관)
  · 팔     ⓐ곡선 단독 · ⓑ본문512 단독 · ⓒ곡선+본문 (대결 대비) ← 1037 이 옳다
  · 곡선특징 warc1037_down.curve_feats ← 1037 이 옳다 (청정 분할에서 0.6298 대 1036 의 0.5968)
  · 모형   sklearn LogisticRegression C=0.1 + StandardScaler (모형 축은 실측상 무차)

시각 처리 다섯. 자세한 등록문은 `docs/탐색/1039.md` §2.
  (ㄴ) 남김      전 행 · 창=크롤 · 라벨=크롤          기준선
  (ㄱ) 버림      발행일이 크롤 창 «안»인 행만          🔴 주판정
  (ㄷ) 곡선재부착 창=발행일 · 라벨=크롤                [진단] 곡선 팔 위약
  (ㄹ) 완전재부착 창=발행일 · 라벨=발행일               [관찰] 별개 추정량
  (ㄷ′) (ㄷ)와 같은 행 · 재부착 안 함                  표본선택 ÷ 재부착 분리
"""
import argparse, gzip, glob, json, os, time, hashlib, collections
import datetime as dt
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

np.seterr(all="ignore")
ROOT = "/Users/ax/world_model"
TF = "/Users/ax/wm_harvest/foundation/textfix1036"
TRI = "/Users/ax/wm_harvest/foundation/triples"
W37 = "/Users/ax/wm_harvest/foundation/warc1037"
OUTP = "/Users/ax/wm_harvest/foundation/warc1039"
SEED = 1039
BOOT = 1000
# 등록 게이트 (docs/탐색/1039.md §2-다) — 측정 «전» 커밋
GATE_K = 174        # (ㄱ) 팔의 위키문서 클러스터 하한 → MDE ≤ 0.0875
GATE_ROWS = 3000    # 1037 G-A2 승계
SE_ANCHOR = 0.0262  # 1039-가 실측: Δ_대결 SE (K=485 위키문서)
K_ANCHOR = 485


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def fast_auc(y, s):
    o = np.argsort(s, kind="mergesort"); t = y[o]; ss = s[o]
    n1 = t.sum(); n0 = len(t) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    r = np.empty(len(ss), float); i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[i:j + 1] = (i + j) / 2.0 + 1.0; i = j + 1
    return (r[t == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def curve_feats(Sr):
    """warc1037_down.py 자구 그대로."""
    L = np.log1p(np.maximum(Sr, 0))
    mu = L.mean(1, keepdims=True); sd = L.std(1, keepdims=True) + 1e-6
    Z = (L - mu) / sd
    x = np.arange(Sr.shape[1]) - (Sr.shape[1] - 1) / 2.0
    slope = (Z * x).sum(1) / (x * x).sum()
    last14 = L[:, -14:].mean(1) - L[:, :-14].mean(1)
    extra = np.column_stack([mu[:, 0], sd[:, 0], slope, last14,
                             L.max(1) - np.median(L, 1), (Sr == 0).mean(1),
                             np.median(L, 1), L[:, -1] - np.median(L, 1)])
    return np.column_stack([Z, extra])


def label_of(Sr, Or):
    """정본 라벨 조리법. 1039-가에서 y_event.npy 와 «비트 동일» 확인."""
    b = np.median(np.log1p(Sr), axis=1, keepdims=True)
    return ((np.log1p(Or) - b).max(axis=1) >= np.log(3)).astype(int)


def hb(s):
    return int(hashlib.md5(str(s).encode()).hexdigest()[:8], 16) % 10


def load_panel():
    panel = {}
    for fp in sorted(glob.glob(f"{ROOT}/data/ingest/wiki_daily959/*.jsonl.gz")):
        for line in gzip.open(fp, "rt"):
            o = json.loads(line)
            days = o.get("날짜"); vals = o.get("값") or o.get("조회수") or o.get("views")
            if not days or not vals:
                continue
            arr = np.zeros(len(days), float); arr[:len(vals)] = vals[:len(days)]
            panel[o["키"]] = (np.asarray(days, dtype=np.int64), arr)
    return panel


def window(panel, ent, anchor, back, fwd):
    """[anchor-back, anchor-1] 과 [anchor, anchor+fwd-1] 을 뽑는다. 못 덮으면 None."""
    if ent not in panel:
        return None
    days, vals = panel[ent]
    want = np.array([int((anchor + dt.timedelta(days=k)).strftime("%Y%m%d"))
                     for k in range(-back, fwd)], dtype=np.int64)
    pos = np.searchsorted(days, want)
    if pos[-1] >= len(days) or not (days[pos] == want).all():
        return None
    v = vals[pos]
    return v[:back], v[back:]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", default="measure")
    a = ap.parse_args(); t0 = time.time()
    os.makedirs(OUTP, exist_ok=True)
    rows = json.load(open(f"{TF}/row_docid.json", encoding="utf-8"))
    z = np.load(f"{TRI}/sao.npz")
    S = z["S"].astype(np.float64); O = z["O"].astype(np.float64)
    y = np.load(f"{TF}/y_event.npy").astype(int)
    T = np.load(f"{TF}/text_emb_body512.npz")["E"].astype(np.float64)
    ents = np.array([r["개체"] for r in rows]); docs = np.array([r["문서"] for r in rows])
    dids = np.array([r["문서id"] for r in rows])
    doms = json.load(open(f"{TRI}/domains.json", encoding="utf-8"))
    dom = z["dom_id"]
    grp = np.array([hb(d) for d in docs])
    uent = np.unique(ents)
    ENT = np.zeros((len(rows), len(uent))); ENT[np.arange(len(rows)), np.searchsorted(uent, ents)] = 1

    rep = {"코드sha": {p: sha16(f"{ROOT}/{p}") for p in
                       ["runners/retime1039.py", "runners/ab1039_ruler.py", "runners/warc1037_down.py"]},
           "입력sha": {"y_event.npy": sha16(f"{TF}/y_event.npy"),
                       "text_emb_body512.npz": sha16(f"{TF}/text_emb_body512.npz"),
                       "row_docid.json": sha16(f"{TF}/row_docid.json"),
                       "sao.npz": sha16(f"{TRI}/sao.npz"),
                       "warc_pub.jsonl": sha16(f"{W37}/warc_pub.jsonl")},
           "게이트등록": {"K하한(위키문서)": GATE_K, "행하한": GATE_ROWS,
                          "SE앵커": SE_ANCHOR, "K앵커": K_ANCHOR, "목표MDE": 0.0875}}

    # ── 배선 검사 ────────────────────────────────────────────────
    W = {}
    W["라벨 재현 == y_event.npy 비트동일"] = bool(np.array_equal(label_of(S, O), y))
    panel = load_panel()
    W["패널 키"] = len(panel)
    W["개체 패널 덮개"] = f"{sum(1 for e in uent if e in panel)}/{len(uent)}"
    ok = tot = 0
    for i in range(0, len(rows), 13):
        w = window(panel, rows[i]["개체"], dt.date.fromisoformat(rows[i]["언제"]), 90, 91)
        if w is None:
            continue
        tot += 1; ok += int(np.array_equal(w[0], S[i]) and np.array_equal(w[1], O[i]))
    W["G0 크롤시각 재산출 (s,o) 비트동일"] = f"{ok}/{tot}"
    rep["배선"] = W
    print(json.dumps(W, ensure_ascii=False), flush=True)
    assert W["라벨 재현 == y_event.npy 비트동일"] and ok == tot and tot > 500, "배선 실패"
    if a.stage == "wire":
        json.dump(rep, open(f"{OUTP}/retime_wire.json", "w"), ensure_ascii=False, indent=1)
        return

    # ── 발행일 층 병합 (WARC 우선 · v1 보충) ────────────────────
    pub, src = {}, {}
    n_warc = 0
    for line in open(f"{W37}/warc_pub.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r.get("published_at"):
            pub[r["문서id"]] = r["published_at"][:10]; src[r["문서id"]] = "warc:" + str(r.get("method")); n_warc += 1
    n_v1 = 0
    v1p = "/Users/ax/wm_harvest/foundation/pubdate/sao_state.json"
    if os.path.exists(v1p):
        v1 = json.load(open(v1p, encoding="utf-8")).get("문서", {})
        for d, o in v1.items():
            p = o.get("published_at")
            if p and d not in pub:
                pub[d] = str(p)[:10]; src[d] = "v1"; n_v1 += 1
    else:
        print("🔴 v1 층 파일 없음 — 「못 읽었다」", flush=True)
    v2p = "/Users/ax/wm_harvest/foundation/pubdate/v2/sao_state_v2.json"
    rep["발행일 층"] = {"WARC 문서": n_warc, "v1 보충 문서": n_v1, "합 문서": len(pub),
                        "v2 파일": "있음" if os.path.exists(v2p) else "🔴 없다(못 읽었다) — 안 씀"}
    print(json.dumps(rep["발행일 층"], ensure_ascii=False), flush=True)

    pdrow = np.array([pub.get(r["문서id"]) for r in rows], dtype=object)
    haspub = np.array([p is not None for p in pdrow])
    diff = np.array([np.nan if p is None else
                     (dt.date.fromisoformat(rows[i]["언제"]) - dt.date.fromisoformat(p)).days
                     for i, p in enumerate(pdrow)], dtype=float)
    inwin = haspub & (diff >= 0) & (diff <= 90)
    rep["행 계수"] = {"전체": len(rows), "발행일 붙은 행": int(haspub.sum()),
                      "창 «안»": int(inwin.sum()), "창 «밖»": int((haspub & ~inwin).sum()),
                      "창밖 비율(발행일 있는 행 중)": round(float((haspub & ~inwin).sum() / max(1, haspub.sum())), 4),
                      "크롤−발행 중앙일": float(np.nanmedian(diff))}
    print(json.dumps(rep["행 계수"], ensure_ascii=False), flush=True)

    # ── 재부착: 발행일 기준 (s,o) ────────────────────────────────
    S2 = S.copy(); O2 = O.copy(); reok = np.zeros(len(rows), bool)
    rng0 = np.random.default_rng(SEED)
    Sp = S.copy(); plok = np.zeros(len(rows), bool)     # 위약: 무작위 시점
    offs = np.array([d for d in diff if np.isfinite(d)])
    for i, r in enumerate(rows):
        if pdrow[i] is None:
            continue
        w = window(panel, r["개체"], dt.date.fromisoformat(pdrow[i]), 90, 91)
        if w is None:
            continue
        S2[i], O2[i] = w[0], w[1]; reok[i] = True
    for i, r in enumerate(rows):
        if not reok[i]:
            continue
        for _ in range(6):    # 위약: 같은 오프셋 분포에서 뽑은 «다른» 시점
            d = float(rng0.choice(offs))
            w = window(panel, r["개체"], dt.date.fromisoformat(rows[i]["언제"]) - dt.timedelta(days=int(d)), 90, 91)
            if w is not None:
                Sp[i] = w[0]; plok[i] = True; break
    rep["재부착"] = {"성공 행": int(reok.sum()), "발행일 있는 행 중": round(float(reok.sum() / max(1, haspub.sum())), 4),
                     "위약 성공 행": int(plok.sum())}
    y_pub = label_of(S2, O2)
    print(json.dumps(rep["재부착"], ensure_ascii=False), flush=True)

    C1 = curve_feats(S); C2 = curve_feats(S2); Cp = curve_feats(Sp)

    # ── 자 ───────────────────────────────────────────────────────
    def cv(X, yy, idx):
        p = np.zeros(len(idx))
        for k in range(10):
            te = np.where(grp[idx] == k)[0]; tr = np.where(grp[idx] != k)[0]
            if len(te) == 0 or len(tr) == 0 or yy[tr].min() == yy[tr].max():
                p[te] = yy[tr].mean() if len(tr) else 0.5
                continue
            sc = StandardScaler().fit(X[tr])
            m = LogisticRegression(max_iter=2000, C=0.1, solver="lbfgs")
            m.fit(sc.transform(X[tr]), yy[tr])
            p[te] = m.predict_proba(sc.transform(X[te]))[:, 1]
        assert np.isfinite(p).all()
        return p

    def boot(yy, pa, pb, clus, n=BOOT):
        rng = np.random.default_rng(SEED)
        u = np.unique(clus); ix = {c: np.where(clus == c)[0] for c in u}; d = []
        for _ in range(n):
            ii = np.concatenate([ix[c] for c in rng.choice(u, size=len(u), replace=True)])
            if yy[ii].min() == yy[ii].max():
                continue
            d.append(fast_auc(yy[ii], pb[ii]) - fast_auc(yy[ii], pa[ii]))
        d = np.array(d)
        return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), float(d.std(ddof=1))

    res = {}

    def run(name, mask, Cx, yy_full, note=""):
        idx = np.where(mask)[0]
        if len(idx) < 200:
            res[name] = {"n행": int(len(idx)), "실패": "표본 부족"}; return
        yy = yy_full[idx]
        if yy.min() == yy.max():
            res[name] = {"n행": int(len(idx)), "실패": "단일 클래스"}; return
        cl = docs[idx]; K = len(set(cl))
        o = {"등급": note, "n행": int(len(idx)), "위키문서 K": K, "웹문서id": int(len(set(dids[idx]))),
             "기저율": round(float(yy.mean()), 4),
             "예상MDE(√앵커)": round(SE_ANCHOR * np.sqrt(K_ANCHOR / K) * 2, 4)}
        P = {}
        for arm, X in [("ⓐ곡선", Cx[idx]), ("ⓑ본문512", T[idx]),
                       ("ⓒ곡선+본문", np.column_stack([Cx[idx], T[idx]])),
                       ("ⓔ개체ID(영대조)", ENT[idx])]:
            P[arm] = cv(X, yy, idx); o[arm] = round(float(fast_auc(yy, P[arm])), 4)
        lo, hi, se = boot(yy, P["ⓐ곡선"], P["ⓑ본문512"], cl)
        o["Δ대결(ⓑ−ⓐ)"] = round(o["ⓑ본문512"] - o["ⓐ곡선"], 4)
        o["Δ대결 CI95"] = [round(lo, 4), round(hi, 4)]; o["Δ대결 SE"] = round(se, 4)
        o["실측MDE(2SE)"] = round(2 * se, 4)
        lo2, hi2, se2 = boot(yy, P["ⓐ곡선"], P["ⓒ곡선+본문"], cl)
        o["Δ증분(ⓒ−ⓐ)"] = round(o["ⓒ곡선+본문"] - o["ⓐ곡선"], 4)
        o["Δ증분 CI95"] = [round(lo2, 4), round(hi2, 4)]; o["Δ증분 SE"] = round(se2, 4)
        # 도메인별 Δ대결 (조항: 미달 시 병기 의무)
        dd = {}
        for k, dn in enumerate(doms):
            m2 = dom[idx] == k
            if m2.sum() >= 100 and 0 < yy[m2].mean() < 1:
                dd[dn] = round(float(fast_auc(yy[m2], P["ⓑ본문512"][m2]) - fast_auc(yy[m2], P["ⓐ곡선"][m2])), 4)
        o["도메인별 Δ대결"] = dd
        res[name] = o
        print(f"{name}: {json.dumps(o, ensure_ascii=False)}", flush=True)

    allm = np.ones(len(rows), bool)
    run("(ㄴ)남김 = 전 행 · 창=크롤 · 라벨=크롤", allm, C1, y, "기준선")
    run("(ㄱ)버림 = 발행일이 창 «안» 인 행", inwin, C1, y, "🔴 주판정")
    run("(ㄷ)곡선재부착 = 창=발행일 · 라벨=크롤", reok, C2, y, "[진단] 곡선 위약")
    run("(ㄷ′)같은 행 · 재부착 안 함", reok, C1, y, "표본선택 대조")
    run("(ㄷ″)위약재부착 = 무작위 시점", reok & plok, Cp, y, "[영대조]")
    run("(ㄹ)완전재부착 = 창·라벨 둘 다 발행일", reok, C2, y_pub, "[관찰] 별개 추정량")

    # ── 게이트 ───────────────────────────────────────────────────
    g = res.get("(ㄱ)버림 = 발행일이 창 «안» 인 행", {})
    K = g.get("위키문서 K", 0); N = g.get("n행", 0)
    rep["게이트 판정"] = {"K": K, "K하한": GATE_K, "행": N, "행하한": GATE_ROWS,
                          "판정": "통과 → 주판정" if (K >= GATE_K and N >= GATE_ROWS)
                                  else "🔴 미달 → 주판정 «안 낸다». 팔은 [관찰] 로만 적는다"}
    print(json.dumps(rep["게이트 판정"], ensure_ascii=False), flush=True)

    # ── 선택 편향표 ──────────────────────────────────────────────
    cw = np.array([r["글자수"] for r in rows], float)
    hosts = np.array([r["host"] for r in rows])

    def prof(m):
        return {"행": int(m.sum()), "위키문서": int(len(set(docs[m]))), "기저율": round(float(y[m].mean()), 4),
                "글자수 중앙": float(np.median(cw[m])),
                "도메인 상위3": [f"{doms[k]} {int((dom[m]==k).sum())}"
                                 for k in np.argsort(-np.bincount(dom[m], minlength=len(doms)))[:3]],
                "host 상위3": [f"{h} {c}" for h, c in collections.Counter(hosts[m]).most_common(3)]}
    rep["선택 편향"] = {"(ㄱ) 창안": prof(inwin), "(ㄱ) 여집합": prof(~inwin),
                        "(ㄷ) 재부착 성공": prof(reok), "(ㄷ) 여집합": prof(~reok)}
    rep["팔"] = res
    json.dump(rep, open(f"{OUTP}/retime_measure.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rep["선택 편향"], ensure_ascii=False, indent=1), flush=True)
    print(f"\n총 {time.time()-t0:.0f}s → {OUTP}/retime_measure.json", flush=True)


if __name__ == "__main__":
    main()
