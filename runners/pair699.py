"""노트 699 — 텍스트 열이 집 밖 짝으로 옮겨가나. L2 전이 · 씨앗 3."""
import json, sys
import numpy as np
sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import spearmanr
from lab import forms, loop as L, guards as G, pairs as PR, textaxes as TX
from lab.harness import load, Data

T = 2025.0
SEEDS = (0, 1, 2)
CLS = forms.REGISTRY["F18_bagboost"]["cls"]


def base():
    return {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
            **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}


def pair_titles(name):
    """짝 행 순서대로 제목 --- 행 순서가 `to_arrays` 와 같아야 한다."""
    import json as J
    from pathlib import Path
    rows = PR.build(name)
    D = Path("data/state")
    src = {}
    for f in ("manga_records.json", "app_records.json", "mobile_records.json"):
        p = D / f
        if not p.exists():
            continue
        j = J.loads(p.read_text())
        it = j.values() if isinstance(j, dict) else j
        for r in it:
            if isinstance(r, dict) and r.get("record_id"):
                src.setdefault(r["record_id"], r)
    ts = []
    for rid, r in rows.items():
        rec = src.get(rid) or {}
        ts.append(str(rec.get("title") or rec.get("name") or r.get("title") or ""))
    return rows, ts


def main():
    print("=== 판을 짓는다(텍스트 축 포함) ===", flush=True)
    d0 = load(base())                                   # 텍스트 없이
    tx = TX.build(d0, T=T)
    d1 = load({**base(), **tx})                         # 텍스트 있이
    print(json.dumps({"텍스트 축 붙은 도메인": sorted(tx.get(TX.AX, {}))},
                     ensure_ascii=False), flush=True)

    res = {}
    for name in ("KR 만화", "비게임 앱", "CN 만화"):
        src = PR.SRC_DOM[name]
        rows, ts = pair_titles(name)
        # ── 짝 제목에 직접 예측(배선 함정 회피)
        pt = TX.predict_titles(d1, src, ts, T=T)
        if "오류" in pt:
            res[name] = pt
            print(json.dumps({name: pt}, ensure_ascii=False), flush=True)
            continue
        print(json.dumps({name: {"행": len(rows), "겹침": pt["겹침"]}},
                         ensure_ascii=False, indent=1), flush=True)

        def score(data, extra_col=None, tag=""):
            names = list(data.names.get(src) or [])
            A, M, y, t = PR.to_arrays(rows, names)
            cov = None
            if extra_col is not None:
                if TX.AX not in names:
                    return {"오류": f"{TX.AX} 가 {src} 열에 없다"}
                j = names.index(TX.AX)
                A[:, j] = extra_col[0]
                M[:, j] = extra_col[1]
                cov = round(float(extra_col[1].mean()), 4)
            ok = np.isfinite(y)
            rs = []
            for s in SEEDS:
                f = G._fit_on(lambda s=s: CLS(seed=s), data, T, seed=s)
                p = np.asarray(f.predict(src, A, M, t), float)
                k = ok & np.isfinite(p)
                if k.sum() < 40 or len(np.unique(p[k])) < 3:
                    continue
                rs.append(float(spearmanr(p[k], y[k]).statistic))
            return {"팔": tag, "rho": round(float(np.mean(rs)), 4),
                    "씨앗SD": round(float(np.std(rs)), 4), "씨앗": len(rs),
                    "**텍스트 마스크 덮음**": cov, "채점행": int(ok.sum())}

        rng = np.random.default_rng(699)
        v, mk = pt["값"].copy(), pt["마스크"].copy()
        vp = v.copy(); rng.shuffle(vp)              # **위약 --- 값만 섞는다**
        arms = [score(d0, None, "없이(노트 696 재건)"),
                score(d1, (v, mk), "진짜"),
                score(d1, (vp, mk), "위약")]
        for a in arms:
            print(json.dumps({name: a}, ensure_ascii=False), flush=True)
        base_r = arms[0]["rho"]; real = arms[1]["rho"]; plac = arms[2]["rho"]
        thr = {"KR 만화": 0.025, "비게임 앱": 0.024, "CN 만화": 0.022}[name]
        res[name] = {"기준선": base_r, "진짜": real, "위약": plac,
                     "순효과": round(real - base_r, 4),
                     "**신호 몫**": round(real - plac, 4), "문턱": thr,
                     "덮음": arms[1]["**텍스트 마스크 덮음**"],
                     "겹침": pt["겹침"]["**어휘가 닿은 제목 몫**"],
                     "판정": ("**넘는다**" if real - plac > thr else "미달")}
        print(json.dumps({name: res[name]}, ensure_ascii=False, indent=1), flush=True)
    print("=== 모아서 ===", flush=True)
    print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
