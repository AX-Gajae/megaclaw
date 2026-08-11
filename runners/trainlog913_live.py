"""🔴 **실물 코드 · 실물 자료로 몇 초 돌려** 실시간 갱신을 실증한다. 노트 913 팔 ㅈ.

    python3 -m runners.trainlog913_live [걸음수]

# 무엇을 돌리나 --- **데모가 아니다**

`state/masked_encoder.py` 의 `Net` **그대로**(고치지 않았다)를
`data/state/popup_table.npz` 의 `X` **그대로** 넣어 **복원 손실만** 줄인다.

    입력   popup_table.npz 의 X (372행 × 15열) --- 열마다 표준화
    구조   state.masked_encoder.Net(d_in=15, k=2, h=32) --- 인코더 15→32→16→2 · 디코더 2→16→15
    손실   복원 MSE 하나뿐

# 🔴 이 run 이 **주장하지 않는 것**

- **라벨 `y` 를 한 번도 안 본다.** 그래서 판 ρ 도, 소수 라벨 곡선도, 어떤 성적도
  여기서 안 나온다. `자` 를 비워 두었고 화면에 **🔴 자 없음**으로 뜬다.
- 이 손실 곡선은 **「학습이 돌면 화면이 자라나」를 보이려고** 남긴 것이다.
  자료에 대한 주장이 아니다.
- 🔴 **`state/` 를 한 글자도 안 고쳤다.** import 해서 쓰기만 한다.
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import torch

from state.masked_encoder import Net
from trainlog import Run

DATA = "data/state/popup_table.npz"


def main(steps: int = 1200) -> int:
    d = np.load(DATA, allow_pickle=True)
    X = np.asarray(d["X"], dtype=np.float64)
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    Xt = torch.tensor(X, dtype=torch.float32)
    torch.manual_seed(0)
    net = Net(d_in=X.shape[1], k=2, h=32)
    opt = torch.optim.Adam(net.parameters(), lr=3e-3)
    t0 = time.time()
    with Run("popup 표 복원(state.masked_encoder.Net)",
             pushes="해당 없음", ruler=None, demo=False, trained=True,
             seed=0, code=[__file__, "state/masked_encoder.py"], data=[DATA],
             hparams={"d_in": int(X.shape[1]), "k": 2, "h": 32, "lr": 3e-3,
                      "steps": steps, "optim": "Adam",
                      "손실": "복원 MSE 하나뿐(라벨을 안 본다)"},
             note=("노트 913 팔 ㅈ --- **실물 코드(state.masked_encoder.Net)** 를 "
                   "**실물 자료(data/state/popup_table.npz 의 X)** 로 몇 초 돌렸다. "
                   "🔴 **라벨 y 를 한 번도 안 본다** --- 복원 손실만 줄인다. "
                   "그래서 이 곡선으로는 아무것도 주장하지 않는다(자 없음). "
                   "화면이 도는 중에 자라는지 보려고 남긴 기록이다"),
             flush_every=1, flush_secs=0.05) as r:
        r.arch(net)
        for step in range(1, int(steps) + 1):
            opt.zero_grad()
            z, xh = net(Xt)
            loss = ((xh - Xt) ** 2).mean()
            loss.backward()
            opt.step()
            if step % 5 == 0:
                r.log(step=step, split="train",
                      recon_mse=loss.detach().item(),
                      z_std=z.detach().std().item())
        rid, n = r.run_id, r._n
    print(json.dumps({"run_id": rid, "지표 줄 수": n,
                      "초": round(time.time() - t0, 2),
                      "🔴 무엇을 안 봤나": "라벨 y --- 복원 손실만 줄였다"},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 1200))
