# -*- coding: utf-8 -*-
"""수리 1007 보충 — «쌍둥이 제외» 4수의 출처 산출물 (티처 #142 지적 1-㉮ · 조항 81 해소).

왜 있는가: docs/탐색/1007.md §7 의 쌍둥이 수치 4종(MdAPE_M′ 0.7171 · Δ −0.0482 ·
SE 0.0615 · 덮개율 0.6143)은 보고에만 있고 커밋된 러너·산출물 어디에도 없었다
(조항 81 「보고에만 있는 수」 · 조항 66 — 언 러너 c9be5c2c1d52cbb7 에 seed [1007,1] ·
쌍둥이 로직 부재). 티처 #142 가 «풀 쪽 cos≥0.9999 제거 · val 70 유지 · B1 무변 ·
seed [1007,1] · B=10,000» 재구성으로 4칸 전부 비트 일치를 확인했다 — 이 러너는 그
재구성 레시피를 그대로 커밋해 수의 출처를 만든다.

레시피(#142 0절 1 · 판정 아님 — §7 과 같은 «관찰» 지위):
  · val 70 유지 · B1(기후값) 무변 — 1007 언 러너와 같은 정의
  · 각 val 개체에서 같은 도메인 train 풀 쪽의 cos ≥ 0.9999 개체(쌍둥이 «후보»)를
    풀에서 제거한 뒤 top-K(K=12) 가중 분위수로 M′ 재계산
  · Δ′ = MdAPE_M′ − MdAPE_B1 · SE′ = 짝지은 개체 붓스트랩 B=10,000 · seed [1007, 1]
  · 덮개율′ = M′ q10~q90 이 Y 를 덮는 비율
  · 🔴 cos≥0.9999 는 «작품 동일성»의 후보 자이지 정의가 아니다(#142 ⑥-1 ㉮ —
    정의 사전등록은 쌍둥이 필터 백테스트 사이클 몫). 이 산출물은 판정을 바꾸지 않는다.

씀: python3 runners/twin1007_supp.py            # → runners/out1007_twin_supp.json
"""
import hashlib
import json
import os
import time

import numpy as np

TRI = "/Users/ax/wm_harvest/foundation/triples"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out1007_twin_supp.json")
K = 12                       # 1007 판정 K 그대로
TWIN_COS = 0.9999            # 쌍둥이 «후보» 자 (#142 재구성 레시피 그대로)
B_BOOT = 10000
SEED = [1007, 1]             # 🔴 §7 이 보고한 씨앗 — 이제 커밋된 코드에 있다
QS = [0.10, 0.25, 0.50, 0.75, 0.90]

# 티처 #142(=1007 §7 보고값) — 비트 대조 목표 (반올림 자리 = §7 게재 자리)
T142 = {"MdAPE_M′": 0.7171, "Δ′": -0.0482, "SE′": 0.0615, "덮개율′": 0.6143}


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def wquant(vals, wts, qs):
    """1007 언 러너와 같은 정의(역CDF 계단 · 결정적)."""
    v = np.asarray(vals, dtype=np.float64)
    w = np.asarray(wts, dtype=np.float64)
    if w.sum() <= 0:
        w = np.ones_like(w)
    o = np.argsort(v)
    v, w = v[o], w[o]
    cw = np.cumsum(w) / w.sum()
    return [float(v[np.searchsorted(cw, q, side="left").clip(0, len(v) - 1)]) for q in qs]


def ape(pred, actual):
    pred = np.asarray(pred, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    return np.abs(pred - actual) / np.maximum(actual, 1.0)


def main():
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S")
    src = {"sao.npz": sha16(TRI + "/sao.npz"),
           "meta.jsonl": sha16(TRI + "/meta.jsonl"),
           "text_emb_qwen05b.npz": sha16(TRI + "/text_emb_qwen05b.npz"),
           "domains.json": sha16(TRI + "/domains.json"),
           "러너 자신": sha16(os.path.abspath(__file__))}
    z = np.load(TRI + "/sao.npz")
    O = z["O"].astype(np.float64)
    meta = [json.loads(l) for l in open(TRI + "/meta.jsonl", encoding="utf-8")]
    doms = json.load(open(TRI + "/domains.json", encoding="utf-8"))
    E = np.load(TRI + "/text_emb_qwen05b.npz")["E"].astype(np.float64)
    first = {}
    for i, m in enumerate(meta):
        k = m["개체"]
        if k not in first or m["언제"] < meta[first[k]]["언제"]:
            first[k] = i                    # 동률 언제는 앞 행(결정적) — 언 러너와 동일

    Y = {k: float(O[i][:90].sum()) for k, i in first.items()}
    pool = {d: [] for d in doms}
    evals = []
    for k, i in sorted(first.items()):
        if meta[i]["분할"] == "train":
            pool[meta[i]["도메인"]].append(k)
        else:
            evals.append(k)
    En = E / np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-12)

    rows = []
    n_top1_gt = 0                           # 관찰 — top1 cos > 0.9999 (§7 보고 30)
    n_removed_any = 0                       # 관찰 — 쌍둥이 후보가 1+ 제거된 val 수
    for k in evals:
        i = first[k]
        d = meta[i]["도메인"]
        cand = pool[d]
        sims = En[[first[c] for c in cand]] @ En[i]
        if float(np.max(sims)) > TWIN_COS:
            n_top1_gt += 1
        keep = sims < TWIN_COS              # 🔴 풀 쪽 cos≥0.9999 제거
        if int((~keep).sum()) > 0:
            n_removed_any += 1
        vy = np.array([Y[c] for c in cand])[keep]
        sims_k = sims[keep]
        order = np.argsort(-sims_k)[:K]
        w = np.maximum(sims_k[order], 0.0)
        q = wquant(vy[order], w, QS)
        qb = wquant(np.array([Y[c] for c in cand]), np.ones(len(cand)), QS)  # B1 무변
        rows.append({"개체": k, "도메인": d, "Y": Y[k], "제거된 쌍둥이 후보": int((~keep).sum()),
                     "M′_q50": q[2], "M′_q10": q[0], "M′_q90": q[4], "B1_q50": qb[2]})

    ya = np.array([r["Y"] for r in rows])
    ape_m2 = ape([r["M′_q50"] for r in rows], ya)
    ape_b1 = ape([r["B1_q50"] for r in rows], ya)
    n_ape0 = int((ape_m2 == 0.0).sum())     # 관찰 — 제외 «후» APE 정확 0
    cov2 = float(np.mean([(r["M′_q10"] <= r["Y"] <= r["M′_q90"]) for r in rows]))

    rng = np.random.default_rng(SEED)
    n = len(rows)
    deltas = np.empty(B_BOOT)
    for b in range(B_BOOT):
        ii = rng.integers(0, n, size=n)
        deltas[b] = np.median(ape_m2[ii]) - np.median(ape_b1[ii])
    md_m2 = float(np.median(ape_m2))
    md_b1 = float(np.median(ape_b1))
    delta = md_m2 - md_b1
    se = float(deltas.std(ddof=1))

    got = {"MdAPE_M′": round(md_m2, 4), "Δ′": round(delta, 4),
           "SE′": round(se, 4), "덮개율′": round(cov2, 4)}
    match = {kk: bool(got[kk] == T142[kk]) for kk in T142}

    out = {
        "지위": ("관찰(판정 아님) — 1007 §7 쌍둥이 4수의 «출처 산출물» · 티처 #142 지적 1-㉮ "
              "(조항 81 해소). cos≥0.9999 는 작품 동일성의 «후보» 자다 — 정의 사전등록은 "
              "쌍둥이 필터 백테스트 사이클(#142 ⑥-1) 몫"),
        "시각": {"시작": t_start, "끝": time.strftime("%Y-%m-%dT%H:%M:%S")},
        "잰 소스 (조항 66)": src,
        "레시피": {"풀 쪽 제거 자": "cos ≥ %s (val 70 유지 · B1 무변)" % TWIN_COS,
                "K": K, "B": B_BOOT, "seed": SEED},
        "분모": {"val": n, "쌍둥이 후보 1+ 제거된 val": n_removed_any,
               "top1 cos>0.9999 (§7 보고 30)": n_top1_gt,
               "제외 후 APE 정확 0 (참고 — §7 의 17 은 제외 «전» 계수)": n_ape0},
        "4수 (6자리)": {"MdAPE_M′": round(md_m2, 6), "MdAPE_B1(무변)": round(md_b1, 6),
                      "Δ′": round(delta, 6), "SE′": round(se, 6), "덮개율′": round(cov2, 6)},
        "🔴 비트 대조 — 티처 #142(=§7 게재 자리)": {
            "목표": T142, "실측": got, "일치": match,
            "전 칸 일치": bool(all(match.values()))},
        "개체별 (관찰)": rows,
        "판 넷": "무접촉 — 전이 모형·scoreboard·리더보드 이 러너는 안 만진다",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"4수": got, "일치": match, "전 칸": all(match.values())},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
