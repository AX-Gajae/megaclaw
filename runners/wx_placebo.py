"""원인 가르기 — 날씨가 나쁜가, 아니면 **열을 더한 것**이 나쁜가(노트 133).

날씨 축 셋을 넣으니 팝업이 0.3880 -> 0.3597 (12/12 음수) 로 내려갔다. 원인이
둘이다.

  ① **틀린 신호** --- 평년 날씨가 방문과 반대로 움직여 모형을 오도한다.
  ② **차원 비용** --- 89행짜리 도메인에 열을 39 -> 42 로 늘린 것 자체가
     해롭다. 무엇을 넣든 똑같이 내려간다.

가르는 법은 하나다. **값만 섞은 위약**을 같은 자리에 넣는다(노트 335 의
열 위약 관례). 열 수도 관측 무늬도 그대로고 값의 짝만 깨진다.

  위약도 똑같이 내려가면   → ② 차원 비용. 날씨는 무죄다.
  위약은 안 내려가면       → ① 날씨가 실제로 틀린 신호를 넣었다.
"""
import json

import numpy as np

from lab import forms, loop as L
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12
WX = ("wx_temp", "wx_rain", "wx_harsh")


def arm(mode: str):
    """mode: 없이 | 날씨 | 위약"""
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        if mode != "없이":
            from lab.weatheraxes import build as wxb
            w = wxb()
            if mode == "위약":
                # **관측 무늬는 그대로 두고 값만 섞는다.** 마스크를 건드리면
                # 표시자가 곧 정보가 돼서 위약이 위약이 아니게 된다(노트 335).
                rng = np.random.default_rng(640)
                w = {k: {d: (_shuf(v[0], v[1], rng), v[1])
                         for d, v in byd.items()} for k, byd in w.items()}
            e.update(w)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def _shuf(v, m, rng):
    v = np.asarray(v, float).copy()
    ok = np.asarray(m) > 0
    idx = np.flatnonzero(ok)
    v[idx] = v[rng.permutation(idx)]
    return v


def per_seed(data):
    b, p = [], []
    for s in range(SEEDS):
        sc = evaluate(lambda s=s: CLS(seed=s), data)
        b.append(float(data.pooled(sc)))
        x = sc.get("팝업")
        p.append(float(x) if x is not None and np.isfinite(x) else np.nan)
    return np.array(b), np.array(p)


res = {}
for m in ("없이", "날씨", "위약"):
    b, p = per_seed(arm(m))
    res[m] = (b, p)
    print(json.dumps({m: {"판": round(float(np.nanmean(b)), 4),
                          "팝업": round(float(np.nanmean(p)), 4)}},
                     ensure_ascii=False), flush=True)

out = {}
for nm, i in (("판", 0), ("팝업", 1)):
    base = res["없이"][i]
    for m in ("날씨", "위약"):
        d = res[m][i] - base
        ok = np.isfinite(d)
        out[f"{nm}·{m}"] = {
            "차": round(float(np.nanmean(d)), 4),
            "씨앗SE": round(float(np.nanstd(d, ddof=1) / np.sqrt(ok.sum())), 4),
            "양수": f"{int((d[ok] > 0).sum())}/{int(ok.sum())}"}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
