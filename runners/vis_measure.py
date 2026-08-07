"""방문자 축 채택 검사 — 챔피언 대 챔피언+방문자, 씨앗 12 짝뽑기(노트 641).

노트 638 의 날씨와 **같은 저울**로 잰다. 다른 것은 자료뿐이다.

날씨가 떨어진 자리에서 이 축이 다른 점 셋을 미리 적어 둔다(사전등록).

  ① **지역이 갈린다.** 날씨는 66행 중 54행이 서울 하나라 지역 차가 없었다.
     이 축은 성동구 21 · 영등포구 12 · 강남구 7 · 중구 5 로 갈린다.
  ② **자릿수가 맞는다.** popga 프록시가 실패한 원인이 모집단 스케일이었는데
     (조회 중앙값 86명 대 방문 수천~수만) 성동구 하루 외지인은 36만 명이다.
  ③ **축끼리 안 겹친다.** 날씨는 |r| 0.72~0.76 이었고 여기는 0.03~0.24 다.

**그래도 예측은 보수적으로 적는다.** 팝업은 89행이고 노트 638 이 열을 39→42 로
늘린 것만으로 −0.0283 을 봤다. 위약이 그 원인을 아직 안 갈랐으므로, 이 축도
같은 차원 비용을 낸다면 신호가 좋아도 못 넘을 수 있다. 그래서 **축 셋과 축
하나(vis_out)** 를 둘 다 잰다 --- 차원 비용이 원인이면 하나짜리가 덜 나쁘다.
"""
import json

import numpy as np

from lab import forms, loop as L
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12


def arm(axes=None):
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        if axes is not None:
            from lab.visitoraxes import build as vb
            w = vb(axes=axes)
            if not w:
                raise SystemExit("방문자 축이 비었다 — 측정 중단")
            e.update(w)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def check(data, axes) -> dict:
    A, M, _, _ = data.dom["팝업"]
    nm = data.names["팝업"]
    out = {"행": int(len(A)), "열": int(A.shape[1])}
    for w in axes:
        if w not in nm:
            out[w] = "열 없음"
            continue
        j = nm.index(w)
        ok = M[:, j] > 0
        out[w] = {"관측": int(ok.sum()),
                  "값 가짓수": int(len(np.unique(A[ok, j]))) if ok.any() else 0}
    return out


def per_seed(data):
    b, p = [], []
    for s in range(SEEDS):
        sc = evaluate(lambda s=s: CLS(seed=s), data)
        b.append(float(data.pooled(sc)))
        x = sc.get("팝업")
        p.append(float(x) if x is not None and np.isfinite(x) else np.nan)
    return np.array(b), np.array(p)


THREE = ("vis_out", "vis_mom", "vis_share")
ONE = ("vis_out",)

base = arm(None)
b0, p0 = per_seed(base)
print(json.dumps({"없이": {"판": round(float(b0.mean()), 4),
                          "팝업": round(float(np.nanmean(p0)), 4)}},
                 ensure_ascii=False), flush=True)

out = {}
for lbl, axes in (("방문자3", THREE), ("방문자1", ONE)):
    d = arm(axes)
    chk = check(d, axes)
    print(json.dumps({f"{lbl} 붙었나": chk}, ensure_ascii=False), flush=True)
    if any(chk.get(w) == "열 없음" or (isinstance(chk.get(w), dict) and chk[w]["관측"] == 0)
           for w in axes):
        print(f"**{lbl}: 열이 중립화됐다 — 건너뛴다**", flush=True)
        continue
    b1, p1 = per_seed(d)
    for nm, a, b in (("판", b0, b1), ("팝업", p0, p1)):
        diff = b - a
        ok = np.isfinite(diff)
        out[f"{nm}·{lbl}"] = {
            "없이": round(float(np.nanmean(a)), 4),
            "있고": round(float(np.nanmean(b)), 4),
            "차": round(float(np.nanmean(diff)), 4),
            "씨앗SE": round(float(np.nanstd(diff, ddof=1) / np.sqrt(ok.sum())), 4),
            "양수": f"{int((diff[ok] > 0).sum())}/{int(ok.sum())}"}
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)

print(json.dumps({"주의": "씨앗 SE 는 재현성이다(노트 613). 판 문턱 표본 2σ=0.0045"},
                 ensure_ascii=False), flush=True)
