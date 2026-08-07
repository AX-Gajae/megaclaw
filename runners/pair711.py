"""노트 711 — 앱 짝을 **씨앗 12** 로. 채택 후보의 마지막 문.

노트 710 이 CN 에서 씨앗 3 → 12 로 신호 몫이 5분의 1이 되는 것을 쟀고 원인이
**위약 팔**이었다. 앱의 +0.1094 도 씨앗 3 이므로 같은 함정일 수 있다.

**씨앗별 rho 를 전부 찍는다** --- 위약이 씨앗 몇에서 수렴하나가 다음 짝 실험의
씨앗 수를 정한다. 그리고 씨앗 3 묶음 넷으로 나눠 **노트 709 가 우연히 어느
묶음을 뽑았나**를 본다.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import spearmanr
from lab import forms, guards as G, loop as L, pairs as PR, textaxes as TX
from lab.sideaudit import champion_data

T = 2025.0
SEEDS = tuple(range(12))
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
NAME = "비게임 앱"
SRC = PR.SRC_DOM[NAME]
BASE_REC, BASE_SD, THR = 0.4968, 0.0106, 0.024


def with_text(tx):
    from lab import genaxes, grpaxes

    def ex():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
        e.update(grpaxes.build())
        e.update(tx)
        return e
    return L._idol(lambda: ex(), mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def titles_for(rows):
    from pathlib import Path
    D = Path("data/state")
    src = {}
    for f in ("app_records.json", "mobile_records.json"):
        p = D / f
        if not p.exists():
            continue
        j = json.loads(p.read_text())
        for r in (j.values() if isinstance(j, dict) else j):
            if isinstance(r, dict) and r.get("record_id"):
                src.setdefault(r["record_id"], r)
    return [str((src.get(k) or {}).get("title")
                or (src.get(k) or {}).get("name") or "") for k in rows]


def per_seed(data, rows, col=None):
    """**씨앗별 rho 를 다 돌려준다** --- 평균만 보면 수렴을 못 본다."""
    names = list(data.names.get(SRC) or [])
    A, M, y, t = PR.to_arrays(rows, names)
    cov = None
    if col is not None:
        if TX.AX not in names:
            return {"오류": f"{TX.AX} 가 {SRC} 열에 없다 --- 배선 끊김"}
        j = names.index(TX.AX)
        A[:, j], M[:, j] = col[0], col[1]
        cov = round(float(col[1].mean()), 4)
    ok = np.isfinite(y)
    rs = []
    for s in SEEDS:
        f = G._fit_on(lambda s=s: CLS(seed=s), data, T, seed=s)
        p = np.asarray(f.predict(SRC, A, M, t), float)
        k = ok & np.isfinite(p)
        rs.append(float(spearmanr(p[k], y[k]).statistic)
                  if k.sum() >= 40 and len(np.unique(p[k])) >= 3 else np.nan)
        print(f"    씨앗 {s}: {rs[-1]:.4f}", flush=True)
    a = np.array(rs, float)
    return {"씨앗별": [round(x, 4) for x in rs],
            "rho": round(float(np.nanmean(a)), 4),
            "씨앗SD": round(float(np.nanstd(a)), 4),
            "누적평균": [round(float(np.nanmean(a[:i + 1])), 4)
                     for i in range(len(a))],
            "텍스트 덮음": cov, "채점행": int(ok.sum()), "열 수": len(names)}


def main():
    print("=== 챔피언 판을 짓는다 ===", flush=True)
    d0 = champion_data()
    tx = TX.build(d0, T=T)
    d1 = with_text(tx)
    rows = PR.build(NAME)
    ts = titles_for(rows)
    print(json.dumps({"짝 행": len(rows), "제목 있음": sum(1 for x in ts if x)},
                     ensure_ascii=False), flush=True)

    print("  [없이]", flush=True)
    a0 = per_seed(d0, rows, None)
    wire = abs(a0["rho"] - BASE_REC) <= 3 * BASE_SD
    print(json.dumps({"없이": {k: v for k, v in a0.items() if k != "누적평균"},
                      "기록 기준선": BASE_REC,
                      "차": round(a0["rho"] - BASE_REC, 4),
                      "**배선 통과**": wire}, ensure_ascii=False), flush=True)
    if not wire:
        print(json.dumps({"멈춘다": "기준선이 안 맞아 아래를 읽지 않는다"},
                         ensure_ascii=False), flush=True)
        return

    pt = TX.predict_titles(d1, SRC, ts, T=T)
    rng = np.random.default_rng(711)
    v, mk = pt["값"].copy(), pt["마스크"].copy()
    vp = v.copy(); rng.shuffle(vp)
    print("  [진짜]", flush=True)
    a1 = per_seed(d1, rows, (v, mk))
    print("  [위약]", flush=True)
    a2 = per_seed(d1, rows, (vp, mk))

    r1 = np.array(a1["씨앗별"], float); r2 = np.array(a2["씨앗별"], float)
    sig = round(float(np.nanmean(r1) - np.nanmean(r2)), 4)
    net = round(float(np.nanmean(r1) - a0["rho"]), 4)
    # 씨앗 3 묶음 넷 --- 노트 709 가 우연히 어느 묶음을 뽑았나
    chunks = [round(float(np.nanmean(r1[i:i + 3]) - np.nanmean(r2[i:i + 3])), 4)
              for i in range(0, 12, 3)]
    # 두 팔이 짝지어져 있나(노트 629)
    m = np.isfinite(r1) & np.isfinite(r2)
    pair_r = (round(float(np.corrcoef(r1[m], r2[m])[0, 1]), 3)
              if m.sum() > 2 else None)
    out = {"없이": a0["rho"], "진짜": a1["rho"], "위약": a2["rho"],
           "**신호 몫**": sig, "**순효과**": net, "문턱": THR,
           "판정": ("**넘는다**" if sig > THR else "미달"),
           "씨앗 3 묶음 넷의 신호 몫": chunks,
           "묶음 폭": round(max(chunks) - min(chunks), 4),
           "진짜↔위약 씨앗별 상관": pair_r,
           "위약 누적평균": a2["누적평균"],
           "진짜 씨앗SD": a1["씨앗SD"], "위약 씨앗SD": a2["씨앗SD"],
           "겹침": pt["겹침"]["**어휘가 닿은 제목 몫**"],
           "노트 707 신호 몫(씨앗 3)": 0.1094}
    print("=== 모아서 ===", flush=True)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
