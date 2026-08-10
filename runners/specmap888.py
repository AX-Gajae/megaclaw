# -*- coding: utf-8 -*-
"""노트 888 갑 — **SPEC 슬롯 지도**(측정 전 · 적합 없음 · 규약 55 도달 가능성 계산).

티처 #52 e11 이 지적한 것을 내 손으로 전수 확인한다.

챔피언 `F18_bagboost` 에서 **도메인 전용 정보가 판에 들어가는 통로는 도메인당
정확히 한 칸**이다(`SPEC` · `lab/forms.py:517-548`). 그 한 칸은 **학습
|spearman(y)| argmax** 로 정해진다. 여기서 묻는 것:

  ㄱ. 도메인마다 후보가 몇 개나 있고 1·2·3위의 학습 |r| 차가 얼마인가
  ㄴ. 그 순위가 **유보에서 뒤집히는가**(학습 argmax 가 잘못 고르고 있는가)
  ㄷ. 슬롯이 **빈 도메인**이 몇 개인가
  ㄹ. K 를 2·3 으로 늘리면 **들어올 열이 실제로 있는가**(도달 가능성)

**유보 라벨은 진단 표기에만 쓰고 어떤 선택에도 안 쓴다** --- 고르기는 전부
학습만으로 한다(누출 금지). 이 파일은 판정하지 않는다.
"""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")
import ff753 as FF  # noqa: E402
from lab.forms import ALL5, REGISTRY  # noqa: E402

ROOT = Path("/Users/ax/world_model")
T = 2025.0
CLS = REGISTRY["F18_bagboost"]["cls"]
TOPN = 4


def main():
    d = FF.shell(FF.base())
    doms = sorted(d.dom)
    maxdom, minobs = CLS.SPEC_MAXDOM, CLS.SPEC_MINOBS

    # 학습/유보 마스크
    tr, ho = {}, {}
    for dd in doms:
        yr = np.asarray(d.yr[dd], float)
        y = np.asarray(d.dom[dd][2], float)
        tr[dd] = np.isfinite(yr) & (yr < T) & np.isfinite(y)
        ho[dd] = np.isfinite(yr) & (yr >= T) & np.isfinite(y)

    # `_spec_pick` 과 **같은 규칙**으로 전용 축 집합을 만든다(학습 행만)
    cnt = {}
    for dd in doms:
        A, M, y, t = d.dom[dd]
        Atr, Mtr = A[tr[dd]], M[tr[dd]]
        for j, a in enumerate(list(d.names.get(dd) or ALL5)):
            if Mtr[:, j].sum() >= minobs:
                cnt[a] = cnt.get(a, 0) + 1
    excl = {a for a, c in cnt.items() if c <= maxdom}

    rows, empty, flip = {}, [], []
    for dd in doms:
        A, M, y, t = d.dom[dd]
        nm = list(d.names.get(dd) or ALL5)
        cands = []
        for j, a in enumerate(nm):
            if a not in excl:
                continue
            o_tr = (M[:, j] > 0) & tr[dd]
            if o_tr.sum() < minobs or len(np.unique(A[o_tr, j])) < 3:
                continue
            r_tr = spearmanr(A[o_tr, j], y[o_tr]).correlation
            if not np.isfinite(r_tr):
                continue
            o_ho = (M[:, j] > 0) & ho[dd]
            r_ho = (float(spearmanr(A[o_ho, j], y[o_ho]).correlation)
                    if o_ho.sum() >= 8 and len(np.unique(A[o_ho, j])) >= 3 else None)
            cands.append({"축": a, "학습 |r|": round(abs(float(r_tr)), 4),
                          "학습 r": round(float(r_tr), 4),
                          "유보 r": (None if r_ho is None or not np.isfinite(r_ho)
                                   else round(r_ho, 4)),
                          "학습 n": int(o_tr.sum()), "유보 n": int(o_ho.sum())})
        cands.sort(key=lambda x: -x["학습 |r|"])
        rows[dd] = {"후보 수": len(cands), "상위": cands[:TOPN]}
        if not cands:
            empty.append(dd)
        # 1위와 2위의 유보 부호가 반대이고 2위 |유보 r| 이 더 크면 '뒤집힘'
        if len(cands) >= 2:
            a, b = cands[0], cands[1]
            if (a["유보 r"] is not None and b["유보 r"] is not None
                    and np.sign(a["학습 r"]) * a["유보 r"] < np.sign(b["학습 r"]) * b["유보 r"]):
                flip.append({"도메인": dd, "1위": a["축"], "2위": b["축"],
                             "학습 |r| 차": round(a["학습 |r|"] - b["학습 |r|"], 4),
                             "1위 방향맞춘 유보 r": round(np.sign(a["학습 r"]) * a["유보 r"], 4),
                             "2위 방향맞춘 유보 r": round(np.sign(b["학습 r"]) * b["유보 r"], 4)})

    n_ge2 = sum(1 for dd in doms if rows[dd]["후보 수"] >= 2)
    n_ge3 = sum(1 for dd in doms if rows[dd]["후보 수"] >= 3)
    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "왜": ("측정 전 도달 가능성(규약 55). SPEC 은 도메인당 한 칸이고 학습 |r| argmax 로 정해진다 — "
              "K 를 늘릴 자리가 실제로 있나, 그리고 argmax 가 유보에서 뒤집히나."),
        "규칙(= `_spec_pick` 과 동일)": {"SPEC_MAXDOM": maxdom, "SPEC_MINOBS": minobs,
                                  "전용 축 집합 크기": len(excl)},
        "🔴 슬롯이 빈 도메인": empty,
        "🔴 K 도달 가능성": {"후보 ≥2 인 도메인": n_ge2, "후보 ≥3 인 도메인": n_ge3,
                     "K=2 로 늘 때 새로 들어올 열 수": n_ge2,
                     "K=3 로 늘 때 새로 들어올 열 수": n_ge2 + n_ge3},
        "🔴 학습 argmax 가 유보에서 뒤집히는 도메인": flip,
        "도메인별": rows,
        "⚠ 유보 r 의 용도": "**진단 표기 전용.** 어떤 선택에도 안 쓴다(고르기는 학습만).",
    }
    with open(ROOT / "runners/out888_specmap.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "도메인별"},
                     ensure_ascii=False, indent=1))
    print("\n=== 도메인별 상위 후보 ===")
    for dd in doms:
        r = rows[dd]
        head = " · ".join(f"{c['축']}({c['학습 |r|']:.3f}→유보 {c['유보 r']})"
                          for c in r["상위"][:3]) or "없음"
        print(f"  {dd:8s} 후보 {r['후보 수']:2d} | {head}")


if __name__ == "__main__":
    main()
