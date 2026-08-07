"""노트 710 — **CN 을 씨앗 12 로 굳힌다.** 판정을 가르는 유일한 자다.

CN 은 문턱의 1.23배(0.0271 대 0.022)로 붙어 있고 노트 709 는 씨앗 3 이었다.
씨앗을 12 로 늘려 신호 몫이 문턱 위에 남나 본다 --- 내려가면 채택은 없다.

(원래 머리말) KR·CN 만화 짝을 **챔피언 판에서** 다시.

배선 검증이 판정보다 먼저다: '없이' 팔이 노트 696 재건값 안에 와야 하고,
안 오면 그 짝의 아래 숫자는 아무것도 못 말한다(노트 705 가 앱에서 이 관문을
차 0.0000 으로 통과했다).
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import spearmanr
from lab import forms, guards as G, loop as L, pairs as PR, textaxes as TX
from lab.sideaudit import champion_data

T = 2025.0
SEEDS = tuple(range(12))          # 노트 710 --- 3 → 12
CLS = forms.REGISTRY["F18_bagboost"]["cls"]

#: 짝 → (원천, 노트 696 재건 기준선, 그 씨앗SD, 문턱)
JOBS = {"CN 만화": (0.3874, 0.0109, 0.022)}     # 노트 710 --- CN 만


def with_text(tx):
    """**챔피언 껍질 안에서** 텍스트 열을 붙인다(노트 704 가 여기서 틀렸다)."""
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
    j = json.loads((Path("data/state") / "manga_records.json").read_text())
    src = {}
    for r in (j.values() if isinstance(j, dict) else j):
        if isinstance(r, dict) and r.get("record_id"):
            src.setdefault(r["record_id"], r)
    return [str((src.get(k) or {}).get("title") or "") for k in rows]


def score(data, src, rows, col=None):
    names = list(data.names.get(src) or [])
    A, M, y, t = PR.to_arrays(rows, names)
    cov = None
    if col is not None:
        if TX.AX not in names:
            return {"오류": f"{TX.AX} 가 {src} 열에 없다 --- 배선 끊김"}
        j = names.index(TX.AX)
        A[:, j], M[:, j] = col[0], col[1]
        cov = round(float(col[1].mean()), 4)
    ok = np.isfinite(y)
    rs = []
    for s in SEEDS:
        f = G._fit_on(lambda s=s: CLS(seed=s), data, T, seed=s)
        p = np.asarray(f.predict(src, A, M, t), float)
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

    out = {}
    for name, (base_rec, base_sd, thr) in JOBS.items():
        src = PR.SRC_DOM[name]
        rows = PR.build(name)
        ts = titles_for(rows)
        a0 = score(d0, src, rows, None)
        ok_wire = abs(a0["rho"] - base_rec) <= 3 * base_sd
        print(json.dumps({name: {"없이(배선 검증)": a0, "기록 기준선": base_rec,
                                 "차": round(a0["rho"] - base_rec, 4),
                                 "**배선 통과**": ok_wire}},
                         ensure_ascii=False), flush=True)
        if not ok_wire:
            out[name] = {"멈춘다": "기준선이 안 맞아 아래를 읽지 않는다",
                         "없이": a0["rho"], "기록": base_rec}
            continue
        pt = TX.predict_titles(d1, src, ts, T=T)
        if "오류" in pt:
            out[name] = pt
            print(json.dumps({name: pt}, ensure_ascii=False), flush=True)
            continue
        rng = np.random.default_rng(710)
        v, mk = pt["값"].copy(), pt["마스크"].copy()
        vp = v.copy(); rng.shuffle(vp)
        a1 = score(d1, src, rows, (v, mk))
        a2 = score(d1, src, rows, (vp, mk))
        sig = round(a1["rho"] - a2["rho"], 4)
        net = round(a1["rho"] - a0["rho"], 4)
        out[name] = {"없이": a0["rho"], "진짜": a1["rho"], "위약": a2["rho"],
                     "**신호 몫**": sig, "**순효과**": net, "문턱": thr,
                     "판정": ("**넘는다**" if sig > thr else "미달"),
                     "순효과 부호": ("양수 --- 넣으면 판이 좋아진다" if net > 0
                                else "**음수 --- 넣으면 판이 나빠진다**(채택 불가)"),
                     "겹침": pt["겹침"]["**어휘가 닿은 제목 몫**"],
                     "닿은 n-gram 중앙": pt["겹침"]["제목당 닿은 n-gram 중앙"],
                     "예측 SD": pt["겹침"]["예측 SD"],
                     "덮음": a1["텍스트 덮음"], "노트 704 신호 몫":
                     {"KR 만화": 0.0148, "CN 만화": 0.0166}[name]}
        print(json.dumps({name: out[name]}, ensure_ascii=False, indent=1), flush=True)
    print("=== 모아서 ===", flush=True)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
