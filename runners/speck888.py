# -*- coding: utf-8 -*-
"""노트 888 병 — 특기 칸 K=1·2·3. **배선 검사 먼저, 그 다음 짝 측정.**"""
import hashlib, json, sys, time
import numpy as np
sys.path.insert(0, "/Users/ax/world_model"); sys.path.insert(0, "/Users/ax/world_model/runners")
import ff753 as FF                                            # noqa: E402
from lab import guards as G                                   # noqa: E402
from lab.forms import REGISTRY                                # noqa: E402
from lab.harness import evaluate                              # noqa: E402

CLS = REGISTRY["F18_bagboost"]["cls"]
T = 2025.0
SEEDS = (0, 1, 2)


def klass(k):
    return type(f"F18_K{k}", (CLS,), {"SPEC_K": k})


def wiring(data):
    """K=1 이 옛 경로와 비트 동일인가 + 폭 불변식."""
    out = {}
    ref = None
    for k in (1, 2, 3):
        f = G._fit_on(lambda k=k: klass(k)(seed=0), data, T, seed=0)
        widths, digs = {}, hashlib.sha256()
        for d in sorted(data.dom):
            A, M, y, t = data.dom[d]
            C = f._spec_col(d, A, M, data.names.get(d))
            widths[d] = int(C.shape[1])
            digs.update(np.ascontiguousarray(C.astype(float)).tobytes())
        ws = sorted(set(widths.values()))
        out[f"K={k}"] = {"폭": ws, "폭_불변": len(ws) == 1,
                         "기대폭": 2 * k, "해시": digs.hexdigest()[:16]}
        if k == 1:
            ref = out["K=1"]["해시"]
    out["K=1_해시"] = ref
    return out


def main():
    t0 = time.time()
    data = FF.shell(FF.base())
    res = {"배선": wiring(data)}
    print(json.dumps(res["배선"], ensure_ascii=False, indent=1), flush=True)
    bad = [k for k, v in res["배선"].items() if isinstance(v, dict) and not v["폭_불변"]]
    if bad:
        print("🔴 폭 불변식 깨짐:", bad); return res
    arms = {}
    for k in (1, 2, 3):
        cls = klass(k)
        vals, per = [], {}
        for s in SEEDS:
            sc = evaluate(lambda s=s, cls=cls: cls(seed=s), data, T=T)
            vals.append(float(data.pooled(sc, T=T)))
            for kk, v in sc.items():
                if np.isfinite(v):
                    per.setdefault(kk, []).append(float(v))
            print(f"  K={k} 씨앗 {s} 판 {vals[-1]:.4f} ({time.time()-t0:.0f}s)", flush=True)
        arms[f"K={k}"] = {"씨앗별": vals, "판": float(np.mean(vals)),
                          "SD": float(np.std(vals, ddof=1)),
                          "도메인": {kk: float(np.mean(a)) for kk, a in per.items()}}
    b = np.array(arms["K=1"]["씨앗별"])
    for k in (2, 3):
        a = np.array(arms[f"K={k}"]["씨앗별"])
        dd = a - b                                   # **짝** --- 같은 씨앗끼리
        arms[f"K={k}"]["짝Δ"] = {"평균": float(dd.mean()),
                                "씨앗별": [float(x) for x in dd],
                                "양수": int((dd > 0).sum()), "총": len(dd)}
    res["팔"] = arms
    json.dump(res, open("/Users/ax/world_model/runners/out888_speck.json", "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: {"판": v["판"], "짝Δ": v.get("짝Δ")} for k, v in arms.items()},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
