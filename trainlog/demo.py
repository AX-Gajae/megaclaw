"""데모 run 셋을 만든다 --- **뷰어가 진짜 파일을 읽는지 확인하는 자리.** 노트 912.

    python3 -m trainlog.demo

🔴 **셋 다 `데모인가: true` 로 표시된다.** 나중에 진짜 학습 기록과 섞이면 안 된다
--- 목록 화면이 이 칸으로 갈라 보여 준다.

    ① 912-demo-mlp      진짜 torch MLP 를 몇 초 학습 --- 곡선 · 뉴런 그림 · 가중치
    ② 912-demo-empty    🔴 **지표도 아키텍처도 없는 run** --- 「못 읽음」이 뜨는지
    ③ 912-demo-bigdict  torch 없이 dict 로 준 큰 그래프 --- **자르기 표시**와
                        「구조만 그렸다」가 뜨는지

⚠ CPU 를 다른 팔과 나눠 쓰므로 **아주 작게** 돌린다(12→64→8→3 · 120걸음).
"""
from __future__ import annotations

import json
import sys

from .run import Run


def demo_mlp() -> str:
    """🔴 **세 줄 사용례가 실제로 도는지**를 여기서 증명한다."""
    import torch
    import torch.nn as nn

    torch.manual_seed(0)
    g = torch.Generator().manual_seed(0)
    X = torch.randn(1536, 12, generator=g)
    W = torch.randn(12, 3, generator=g)
    y = (X @ W).argmax(dim=1)
    Xtr, ytr, Xva, yva = X[:1024], y[:1024], X[1024:], y[1024:]

    model = nn.Sequential(
        nn.Linear(12, 64), nn.ReLU(),
        nn.Linear(64, 8), nn.ReLU(),
        nn.Linear(8, 3))
    opt = torch.optim.Adam(model.parameters(), lr=0.02)
    lossf = nn.CrossEntropyLoss()

    # ── 여기가 사용례다(세 줄) ────────────────────────────────────
    with Run("912-demo-mlp", pushes="해당 없음", code=__file__,
             ruler="합성 자료 3분류 정확도 --- 🔴 **데모 전용이다.** 판 ρ 도 "
                   "소수 라벨 곡선도 아니고, 이 수로는 아무것도 주장하지 않는다",
             seed=0, demo=True,
             hparams={"lr": 0.02, "batch": 256, "steps": 120,
                      "optim": "Adam", "arch": "12-64-8-3"},
             note="노트 912 팔 ㅇ --- 뷰어가 진짜 파일을 읽는지 보는 데모") as r:
        r.arch(model)
        for step in range(1, 121):
            i = torch.randint(0, 1024, (256,), generator=g)
            opt.zero_grad()
            out = model(Xtr[i])
            loss = lossf(out, ytr[i])
            loss.backward()
            opt.step()
            if step % 2 == 0:
                with torch.no_grad():
                    vo = model(Xva)
                    r.log(step=step, split="train",
                          loss=float(loss), acc=float(
                              (out.argmax(1) == ytr[i]).float().mean()))
                    r.log(step=step, split="val",
                          loss=float(lossf(vo, yva)),
                          acc=float((vo.argmax(1) == yva).float().mean()))
        #: 학습이 끝난 **뒤의** 가중치로 아키텍처를 다시 적는다(간선 세기가 산다)
        r.arch(model)
        rid = r.run_id
    return rid


def demo_empty() -> str:
    """🔴 **아무것도 안 남긴 run.** 곡선이 「못 읽음」으로 떠야 한다."""
    with Run("912-demo-empty", pushes="해당 없음", ruler=None, demo=True,
             code=__file__,
             note="🔴 일부러 비운 run --- 지표도 아키텍처도 없다. 뷰어가 "
                  "「비었다」·「못 읽음」을 제대로 내는지 보는 음성 대조다") as r:
        rid = r.run_id
    return rid


def demo_bigdict() -> str:
    """torch 없이 **dict 로 준** 큰 그래프 --- 자르기와 「구조만」을 보여 준다."""
    graph = {
        "층": [
            {"id": "embed", "이름": "embed", "종류": "Embedding",
             "입력 뉴런 수": 256, "뉴런 수": 128, "파라미터 수": 32768},
            {"id": "hidden", "이름": "hidden", "종류": "Linear",
             "입력 뉴런 수": 128, "뉴런 수": 1024, "파라미터 수": 132096,
             "활성함수": "GELU"},
            {"id": "head", "이름": "head", "종류": "Linear",
             "입력 뉴런 수": 1024, "뉴런 수": 12, "파라미터 수": 12300},
        ],
        "간선": [["embed", "hidden"], ["hidden", "head"]],
    }
    with Run("912-demo-bigdict", pushes="해당 없음", ruler=None, demo=True,
             code=__file__,
             hparams={"note": "torch 를 안 쓰는 경로"},
             note="dict 로 준 그래프 --- 1,024뉴런 층에서 **몇 개만 그렸다**가 "
                  "화면에 뜨는지, 가중치가 없을 때 「구조만 그렸다」가 뜨는지") as r:
        r.arch(graph)
        for step in (1, 2, 3):
            r.log(step=step, split="train", loss=1.0 / step)
        rid = r.run_id
    return rid


def main() -> int:
    out = {"무엇": "노트 912 데모 run --- 전부 `데모인가: true`", "만든 것": []}
    try:
        out["만든 것"].append({"①": demo_mlp()})
    except Exception as e:
        out["만든 것"].append({"①": f"못 만들었다: {type(e).__name__}: {e}"})
    out["만든 것"].append({"②": demo_empty()})
    out["만든 것"].append({"③": demo_bigdict()})
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
