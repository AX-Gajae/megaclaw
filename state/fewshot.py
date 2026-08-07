"""새 도메인에 라벨 몇 개가 필요한가 --- 노트 15의 계수 크기 가설을 실용 질문으로 바꾼다.

노트 15는 공유 헤드가 쌍 전이보다 못한 이유를 계수 크기 차이로 지목했다. 타깃 폭
계수가 도메인마다 2.4배 차이 나므로, 하나의 기울기를 강요하면 절충으로 끌려간다.

반증 조건은 '도메인별 배율 항을 두면 유의성이 돌아와야 한다'였다. 그런데 배율은
대상 도메인의 라벨이 있어야 추정할 수 있다. 그러면 '라벨 없이 예측한다'는 주장이
무너진다 --- 배율만큼은 라벨이 필요하기 때문이다.

그래서 질문을 바꾼다. **몇 개면 되는가.**

    학습     두 도메인으로 공유 방향 w 를 배운다 (헤드는 여전히 선형·공유).
    보정     대상 도메인에서 라벨 k개만 보고 배율과 절편 두 개를 맞춘다.
    검정     나머지 대상 레코드에서 잰다.

k=0은 보정 없음(노트 14~15의 설정)이다. k가 커질수록 좋아지는 곡선의 모양이
답이다. 실전에서 새 접점을 열 때 몇 건을 실측해야 모델을 쓸 수 있는지를 말해 준다.

이것은 파운데이션 모델의 표준 사용법이기도 하다 --- 공유 표현은 사전학습에서 오고,
새 과제에는 소수 예시로 맞춘다.

사용: python3 -m state.fewshot
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from .foundation import SLOTS, domains, fit, fit_new_encoder

SEED = 20260728
KS = [0, 2, 3, 5, 8, 12, 20, 30]


def calibrate(pred: np.ndarray, y: np.ndarray, idx: np.ndarray, lam: float = 6.0):
    """라벨 k개로 배율과 절편을 맞추되 **항등 보정 쪽으로 수축**시킨다.

    자유 최소제곱은 k가 작을 때 파탄난다 --- 2점에 직선을 맞추면 기울기가
    폭주해 실측에서 MAE가 8.97까지 올라갔다(보정 안 한 값 0.77). 예측과 라벨이
    같은 눈금(도메인 내 표준화)에 있으므로 기울기의 사전값은 1이다.
    수축 계수 k/(k+lam) 로 표본이 쌓일수록 자료 쪽으로 옮겨간다."""
    if len(idx) == 0:
        return pred
    w = len(idx) / (len(idx) + lam)
    x, yy = pred[idx], y[idx]
    if len(idx) >= 2 and x.std() > 1e-9:
        a_ols = float(np.cov(x, yy, bias=True)[0, 1] / (x.var() + 1e-12))
        a_ols = float(np.clip(a_ols, -3.0, 3.0))
    else:
        a_ols = 1.0
    a = w * a_ols + (1 - w) * 1.0
    b = float(yy.mean() - a * x.mean())
    return a * pred + b


def run(anchor: float = 8.0, seeds: int = 3, reps: int = 40) -> dict:
    D = domains()
    print(f"소수 예시 보정 --- 슬롯 {' · '.join(SLOTS)}")
    for k, v in D.items():
        print(f"  {k:<6} n={v['n']:>3}")

    out = {"slots": SLOTS, "ks": KS, "결과": {}}
    for tgt in D:
        src = {k: v for k, v in D.items() if k != tgt}
        yt = D[tgt]["y"]
        # 공유 방향은 한 번만 배운다 --- k와 무관하다
        preds = []
        for s in range(seeds):
            _, head = fit(src, anchor=anchor, seed=SEED + s)
            preds.append(fit_new_encoder(head, D[tgt], anchor=anchor, seed=SEED + s))
        base_pred = np.mean(preds, axis=0)

        row = {}
        for k in KS:
            errs = []
            for r in range(reps):
                rng = np.random.default_rng(SEED + 100 * r + k)
                if k == 0:
                    idx, hold = np.array([], int), np.arange(len(yt))
                else:
                    idx = rng.choice(len(yt), min(k, len(yt) - 5), replace=False)
                    hold = np.setdiff1d(np.arange(len(yt)), idx)
                p = calibrate(base_pred, yt, idx)
                # 상수 기준도 **같은 k개만** 본다. k=0이면 아무 라벨도 없으므로
                # 도메인 내 표준화 눈금의 중심 0을 쓴다. 모델과 상수가 같은
                # 정보를 갖게 해야 비교가 성립한다.
                c = float(np.median(yt[idx])) if len(idx) >= 1 else 0.0
                errs.append((float(np.abs(p[hold] - yt[hold]).mean()),
                             float(np.abs(c - yt[hold]).mean())))
            m = np.array(errs)
            row[k] = {"model": round(float(m[:, 0].mean()), 4),
                      "const": round(float(m[:, 1].mean()), 4),
                      "diff": round(float((m[:, 0] - m[:, 1]).mean()), 4),
                      "win_rate": round(float((m[:, 0] < m[:, 1]).mean()), 3)}
        out["결과"][tgt] = row
        print(f"\n[{tgt}]  k=라벨 개수")
        print(f"  {'k':>3}{'모델':>9}{'상수':>9}{'차이':>10}{'승률':>8}")
        for k in KS:
            v = row[k]
            print(f"  {k:>3}{v['model']:>9.4f}{v['const']:>9.4f}"
                  f"{v['diff']:>+10.4f}{v['win_rate']:>8.2f}")
    Path("data/state/fewshot.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
