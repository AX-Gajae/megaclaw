# -*- coding: utf-8 -*-
"""노트 971 **탐색 레인** — 유보 예측으로 재려면 어느 도메인이 몇 행을 내는가.

🔴 **결과(y)와 x 의 관계는 한 글자도 안 본다.** 행 수와 결측 사유만 센다 ---
사전등록 ⓪-가-1 「검출력 줄」을 **측정 전에** 채우려고 만든 자다.
🔴 **판정 레인이 아니다**(레인 규칙 1: 이 결과는 사이클 결론에 안 들어간다).
`--out` 필수.
"""
import argparse
import datetime as dt
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

T = 2025.0
N_MIN_TRAIN = 20
N_MIN_HOLD = 20


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    import dropaudit969 as D9
    data, ids = D9.build(drop_wiki=True, drop_trend=True)
    F, why = D9.feats(D9.load_series())
    out = {"🔴 노트": 971, "🔴 레인": "탐색",
           "🔴 시작(UTC)": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "🔴 이 자가 안 보는 것": "결과(y)와 x 의 관계. 행 수와 결측 사유만 센다",
           "feats 제외 사유": why, "F 키 수": len(F)}
    per, w = {}, data.weights(T)
    val = {k: f["excite"] for k, f in F.items() if f["n_rec"] > 0 and f["n_lon"] > 0}
    for d in sorted(data.dom):
        A, M, y, _t = data.dom[d]
        yr, nm, kk = data.yr[d], list(data.names.get(d) or []), ids.get(d)
        row = {"판 행": int(len(y)),
               "학습(yr<T · y유한)": int((np.isfinite(yr) & (yr < T) & np.isfinite(y)).sum()),
               "유보(yr>=T · y유한)": int((np.isfinite(yr) & (yr >= T) & np.isfinite(y)).sum()),
               "판 가중(weights)": w.get(d),
               "wiki_level 열 있나": bool("wiki_level" in nm),
               "ids 길이 일치": bool(bool(kk) and len(kk) == len(y))}
        if kk and len(kk) == len(y) and "wiki_level" in nm:
            j = nm.index("wiki_level")
            raw = np.array([val.get(k, np.nan) for k in kk], float)
            lvl = np.asarray(A[:, j], float)
            rec = np.array([F[k]["recent"] if k in F else np.nan for k in kk], float)
            ok = np.isfinite(raw) & np.isfinite(y) & np.isfinite(lvl) & np.isfinite(rec)
            pre, post = np.isfinite(yr) & (yr < T), np.isfinite(yr) & (yr >= T)
            n_h = int((ok & post).sum())
            row["규격D 행(전량)"] = int(ok.sum())
            row["🔴 규격D ∩ 학습"] = int((ok & pre).sum())
            row["🔴🔴 규격D ∩ 유보"] = n_h
            row["🔴 유보 스피어만 SE 근사 1/sqrt(n-1)"] = \
                (round(1.0 / np.sqrt(n_h - 1), 4) if n_h > 1 else None)
            row["🔴 가를 수 있는 최소 효과(2 SE)"] = \
                (round(2.0 / np.sqrt(n_h - 1), 4) if n_h > 1 else None)
        else:
            row["규격D 행(전량)"] = 0
            row["🔴 규격D ∩ 학습"] = 0
            row["🔴🔴 규격D ∩ 유보"] = 0
        per[d] = row
    out["도메인별"] = per
    tot_h = sum(v["🔴🔴 규격D ∩ 유보"] for v in per.values())
    tot_t = sum(v["🔴 규격D ∩ 학습"] for v in per.values())
    good = [d for d, v in per.items()
            if v["🔴🔴 규격D ∩ 유보"] >= N_MIN_HOLD and v["🔴 규격D ∩ 학습"] >= N_MIN_TRAIN]
    ns = [per[d]["🔴🔴 규격D ∩ 유보"] for d in good]
    out["🔴 합계"] = {
        "🔴 분모 ① 판 도메인": len(per),
        "🔴 분모 ② 학습 20 · 유보 20 을 둘 다 채우는 도메인": good, "그 수": len(good),
        "규격D ∩ 유보 전량(12 도메인)": tot_h, "규격D ∩ 학습 전량(12 도메인)": tot_t,
        "규격D ∩ 유보(그 7 도메인)": int(sum(ns)),
        "규격D ∩ 학습(그 7 도메인)": int(sum(per[d]["🔴 규격D ∩ 학습"] for d in good)),
        "🔴🔴 묶음 보수적 SE 근사 sqrt(Σn²/(n−1))/Σn":
            round(float(np.sqrt(sum(n * n / (n - 1.0) for n in ns)) / sum(ns)), 4),
        "🔴🔴 묶음에서 가를 수 있는 최소 효과(2 SE · 짝 안 지음 상한)":
            round(float(2 * np.sqrt(sum(n * n / (n - 1.0) for n in ns)) / sum(ns)), 4)}
    out["🔴 끝(UTC)"] = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    out["🔴 걸린 초"] = round(time.time() - t0, 1)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", a.out, out["🔴 합계"]["그 수"], "도메인")


if __name__ == "__main__":
    main()
