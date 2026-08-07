"""노트 705 — 앱 짝을 **챔피언 판에서** 다시. 노트 704 의 유일한 무효 팔.

배선 검증이 판정보다 먼저다: '없이' 팔이 **0.4968 ± 0.0106** 안에 와야 하고,
안 오면 그 아래 숫자는 아무것도 못 말한다.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import spearmanr
from lab import forms, guards as G, loop as L, pairs as PR, textaxes as TX
from lab.sideaudit import champion_data

T = 2025.0
SEEDS = (0, 1, 2)
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
NAME = "비게임 앱"
SRC = PR.SRC_DOM[NAME]
BASE_REC = 0.4968          # 노트 696 재건값
BASE_SD = 0.0106
THR = 0.024


def with_text(tx):
    """**챔피언 껍질 안에서** 텍스트 열을 붙인다.

    노트 704 가 여기서 틀렸다 --- `load(base())` 로 지으면 `_idol(mode='cut',
    wide_post=True, wide_pop='grades')` 껍질이 없고, 그러면 앱 짝 기준선이
    0.4968 에서 **0.0848** 로 떨어진다. 그 위에서 잰 증분은 '챔피언 위에 더한
    것' 이 아니라 **빠진 축을 대신 메운 것**이다.
    """
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


def score(data, rows, col=None):
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
        if k.sum() < 40 or len(np.unique(p[k])) < 3:
            continue
        rs.append(float(spearmanr(p[k], y[k]).statistic))
    return {"rho": round(float(np.mean(rs)), 4),
            "씨앗SD": round(float(np.std(rs)), 4), "씨앗": len(rs),
            "열 수": len(names), "텍스트 덮음": cov, "채점행": int(ok.sum())}


def main():
    print("=== 챔피언 판을 짓는다 ===", flush=True)
    d0 = champion_data()
    tx = TX.build(d0, T=T)
    print(json.dumps({"텍스트 축 붙은 도메인": sorted(tx.get(TX.AX, {}))},
                     ensure_ascii=False), flush=True)
    d1 = with_text(tx)

    rows = PR.build(NAME)
    ts = titles_for(rows)
    print(json.dumps({"짝 행": len(rows), "제목 있음": sum(1 for t in ts if t)},
                     ensure_ascii=False), flush=True)

    # ── 배선 검증이 먼저다
    a0 = score(d0, rows, None)
    ok_wire = abs(a0["rho"] - BASE_REC) <= 3 * BASE_SD
    print(json.dumps({"없이(배선 검증)": a0, "기록 기준선": BASE_REC,
                      "차": round(a0["rho"] - BASE_REC, 4),
                      "**배선 통과**": ok_wire}, ensure_ascii=False), flush=True)
    if not ok_wire:
        print(json.dumps({"멈춘다": "기준선이 안 맞으므로 아래를 읽지 않는다 "
                                 "--- 노트 704 에서 이것을 못 보고 문턱 9배를 "
                                 "채택 후보로 올릴 뻔했다"},
                         ensure_ascii=False, indent=1), flush=True)
        return

    pt = TX.predict_titles(d1, SRC, ts, T=T)
    if "오류" in pt:
        print(json.dumps(pt, ensure_ascii=False), flush=True)
        return
    print(json.dumps({"겹침": pt["겹침"]}, ensure_ascii=False, indent=1), flush=True)

    rng = np.random.default_rng(705)
    v, mk = pt["값"].copy(), pt["마스크"].copy()
    vp = v.copy(); rng.shuffle(vp)
    a1 = score(d1, rows, (v, mk))
    a2 = score(d1, rows, (vp, mk))
    print(json.dumps({"진짜": a1, "위약": a2}, ensure_ascii=False), flush=True)
    sig = round(a1["rho"] - a2["rho"], 4)
    net = round(a1["rho"] - a0["rho"], 4)
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "없이": a0["rho"], "진짜": a1["rho"], "위약": a2["rho"],
        "**신호 몫**": sig, "**순효과**": net, "문턱": THR,
        "판정": ("**넘는다**" if sig > THR else "미달"),
        "순효과 부호": ("양수 --- 넣으면 판이 좋아진다" if net > 0
                   else "**음수 --- 넣으면 판이 나빠진다**(채택 불가)"),
        "겹침": pt["겹침"]["**어휘가 닿은 제목 몫**"],
        "덮음": a1["텍스트 덮음"],
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
