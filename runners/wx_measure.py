"""날씨 축 채택 검사 — 챔피언 대 챔피언+날씨, 씨앗 12 짝뽑기.

**두 팔을 같은 방식으로 짓는다.** 추가 축을 만드는 함수를 `_idol` 에
**호출 가능한 채로** 넘긴다 — `_idol` 이 먼저 `set_grades(A~E)` 를 하고
그 다음에 축을 짓기 때문이다. 딕셔너리로 넘기면 등급이 바뀌기 **전**의
행 목록으로 축이 지어진다.

**그리고 붙었는지를 먼저 본다.** `_idol` 은 `len(v[0]) != len(pA)` 면 그 열을
0.5·마스크 0 으로 **조용히 중립화**한다. 그러면 "효과 없음"이 나오는데 그것은
날씨가 안 통해서가 아니라 축이 안 붙어서다 — 노트 359 가 걸린 자리다.
내 사전 예측이 "못 넘는다" 이므로 **이 오류는 내 예측을 거짓으로 확증한다.**
그래서 측정보다 먼저 검사한다.
"""
import json

import numpy as np

from lab import forms, loop as L
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12
WX = ("wx_temp", "wx_rain", "wx_harsh")


def arm(with_wx: bool):
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        if with_wx:
            from lab.weatheraxes import build as wxb
            w = wxb()
            if not w:
                raise SystemExit("날씨 축이 비었다 — 측정 중단")
            e.update(w)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def check(data) -> dict:
    """날씨 열이 팝업 행렬에 **실제로** 붙었나."""
    A, M, y, t = data.dom["팝업"]
    nm = data.names["팝업"]
    out = {"팝업 행": int(len(A)), "팝업 열": int(A.shape[1])}
    for w in WX:
        if w not in nm:
            out[w] = "열 없음"
            continue
        j = nm.index(w)
        ok = M[:, j] > 0
        out[w] = {"관측": int(ok.sum()),
                  "값 가짓수": int(len(np.unique(A[ok, j]))) if ok.any() else 0}
    return out


def per_seed(data):
    board, pop = [], []
    for s in range(SEEDS):
        sc = evaluate(lambda s=s: CLS(seed=s), data)
        board.append(float(data.pooled(sc)))
        v = sc.get("팝업")
        pop.append(float(v) if v is not None and np.isfinite(v) else np.nan)
    return np.array(board), np.array(pop)


d0 = arm(False)
d1 = arm(True)

chk = check(d1)
print(json.dumps({"붙었나": chk}, ensure_ascii=False, indent=1), flush=True)
if any(chk.get(w) == "열 없음" or (isinstance(chk.get(w), dict)
                                  and chk[w]["관측"] == 0) for w in WX):
    raise SystemExit("**날씨 열이 중립화됐다.** 행 수가 안 맞는다 — 측정해도 뜻이 없다")

# 팝업 행렬이 이미 나르는 것과 겹치나. 챔피언의 추가 축 여섯 종류는 팝업을
# 하나도 안 덮으므로(측정 확인) 견줄 상대는 popupset 이 지은 열들이다.
A1, M1, _, _ = d1.dom["팝업"]
nm1 = d1.names["팝업"]
from scipy.stats import spearmanr        # noqa: E402
rows = []
for w in WX:
    jw = nm1.index(w)
    for j, other in enumerate(nm1):
        if other in WX:
            continue
        b = (M1[:, jw] > 0) & (M1[:, j] > 0)
        if b.sum() < 25 or len(np.unique(A1[b, j])) < 3:
            continue
        r = spearmanr(A1[b, jw], A1[b, j]).statistic
        if np.isfinite(r):
            rows.append((w, other, round(float(r), 3), int(b.sum())))
rows.sort(key=lambda x: -abs(x[2]))
print(json.dumps({"팝업 열과의 겹침 상위": rows[:14]}, ensure_ascii=False), flush=True)

b0, p0 = per_seed(d0)
b1, p1 = per_seed(d1)

out = {}
for nm, a, b in (("판", b0, b1), ("팝업", p0, p1)):
    d = b - a
    ok = np.isfinite(d)
    out[nm] = {"없이": round(float(np.nanmean(a)), 4),
               "있고": round(float(np.nanmean(b)), 4),
               "차": round(float(np.nanmean(d)), 4),
               "씨앗SE": round(float(np.nanstd(d, ddof=1) / np.sqrt(ok.sum())), 4),
               "양수": f"{int((d[ok] > 0).sum())}/{int(ok.sum())}"}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
print(json.dumps({"주의": "씨앗 SE 는 재현성 구간이다(노트 613). 판 채택 문턱은 표본 2σ = 0.0045"},
                 ensure_ascii=False), flush=True)
