"""전국 상태 축 채택 검사 — **판으로 잰다**(노트 646).

앞선 세 번(날씨 · 위약 · 방문자)은 전부 팝업 89행에서 쟀고 전부 떨어졌다.
그런데 위약이 진짜보다 더 나빴으므로 그 실패는 축이 아니라 **행 수**의
문제였다. 팝업은 판 21,672행의 0.4% 라 판이 −0.0018 밖에 안 움직인다.

이번 축은 다르다 --- **열한 도메인 전부에 붙는다.** 그래서 시험대가
팝업 89행이 아니라 **판 3,369 유보행**이고, 문턱이 자별 2σ = **0.0045** 다.

미리 적어 둔다.

  ① 기대: 작다. `cal_*` 가 이미 요일 · 계절 · 공휴일을 나른다. 이 축은 그
     **잔차**만 쓰므로 남은 것은 '예정에서 벗어난 정도' 뿐이다.
  ② 그래도 재는 이유: 그 잔차가 곧 사용자가 말한 상태다 --- 날씨 · 사건 ·
     경기 · 분위기가 섞인 값. 그리고 이번엔 **행이 얇지 않다.**
  ③ 반증 조건: 판 Δρ ≥ +0.0045 이면 상태층 축이 판을 움직인 **첫 사례**다.
     못 넘으면 못 넘었다고 적는다.
  ④ 덮음이 도메인마다 다르다(팝업 1.00 ~ 만화 0.19). 그래서 **도메인별로도
     본다** --- 덮인 도메인이 벌고 안 덮인 도메인이 내는 무늬면 노트 413 과
     같은 기제다.
"""
import json

import numpy as np

from lab import forms, loop as L
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12
AX = ("nat_flow", "nat_mom")


def arm(with_nat: bool):
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        if with_nat:
            from lab.natsaxes import build as nb
            w = nb()
            if not w:
                raise SystemExit("전국 축이 비었다 — 측정 중단")
            e.update(w)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def check(data) -> dict:
    """축이 **어느 도메인에** 실제로 붙었나."""
    out = {}
    for dom, (A, M, _y, _t) in data.dom.items():
        nm = data.names.get(dom, [])
        for w in AX:
            if w in nm:
                j = nm.index(w)
                ok = M[:, j] > 0
                out.setdefault(w, {})[dom] = int(ok.sum())
    return out


def per_seed(data):
    board, per = [], {}
    for s in range(SEEDS):
        sc = evaluate(lambda s=s: CLS(seed=s), data)
        board.append(float(data.pooled(sc)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return np.array(board), {k: np.array(v) for k, v in per.items()}


d0 = arm(False)
b0, p0 = per_seed(d0)
print(json.dumps({"없이 판": round(float(b0.mean()), 4)}, ensure_ascii=False), flush=True)

d1 = arm(True)
print(json.dumps({"붙었나": check(d1)}, ensure_ascii=False), flush=True)
b1, p1 = per_seed(d1)

diff = b1 - b0
out = {"판": {"없이": round(float(b0.mean()), 4), "있고": round(float(b1.mean()), 4),
             "차": round(float(diff.mean()), 4),
             "씨앗SE": round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 4),
             "양수": f"{int((diff > 0).sum())}/{len(diff)}",
             "문턱(표본2σ)": 0.0045}}
dom = {}
for k in sorted(set(p0) & set(p1)):
    if len(p0[k]) == len(p1[k]):
        dd = p1[k] - p0[k]
        dom[k] = {"차": round(float(dd.mean()), 4),
                  "양수": f"{int((dd > 0).sum())}/{len(dd)}"}
out["도메인별"] = dom
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
