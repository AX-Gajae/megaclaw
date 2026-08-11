"""🔴 **작은 트랜스포머를 실제로 학습시키며 노드별 그래디언트를 남긴다.** 노트 913 팔 ㅈ.

    python3 -m runners.trainlog913_tblock [걸음수]

# 무엇을 왜

뷰어가 **임의 그래프**(잔차·분기·합류·헤드)를 진짜로 그리는지, 그리고 **노드별
상태**가 그래프 위에 얹히는지를 재려면 그런 그래프를 가진 run 이 하나 있어야
한다. 이 저장소에는 트랜스포머가 없다(`grep MultiheadAttention` → `harness/`
하나뿐이고 모형이 아니다). 그래서 **여기서 하나 짓는다.**

    입력   data/state/popup_table.npz 의 X (372행 × 15열) --- 실물 자료다
           열 15개를 **길이 15의 토큰열**로 본다(값 하나가 토큰 하나)
    구조   Linear(1→32) + 위치 임베딩 → 블록 하나 → Linear(32→1) 복원
           블록 = LayerNorm → 헤드 4개(Q·K·V) → concat → 투영 → **잔차**
                  → LayerNorm → FFN(32→64→32) → **잔차**
    손실   복원 MSE 하나뿐

# 🔴 주장하지 않는 것

- **라벨 `y` 를 한 번도 안 본다.** 성적이 아니다. `자` 를 비웠다(화면에 🔴 자 없음).
- 이 구조가 이 자료에 맞다고 주장하지 않는다. **뷰어를 재려고 만든 그래프**다.
- 🔴 `state/` · `lab/` 를 한 글자도 안 고쳤다.

# 🔴 왜 헤드를 `nn.MultiheadAttention` 으로 안 썼나

`torch.fx.symbolic_trace(nn.MultiheadAttention(...))` 은 **터진다**
(`TraceError: symbolically traced variables cannot be used as inputs to control
flow`). `nn.TransformerEncoderLayer` 도 터진다(`RuntimeError: input to
_none_or_dtype()`). 이 러너가 실제로 확인한다(`_fx_probe()`). fx 가 터지면
간선은 **가정**이 되고, 노트 912 가 밟은 함정(활성함수 자리에서 사슬이 끊겨 간선이
사라짐)이 다시 열린다. 그래서 헤드를 **머리마다 Linear 셋**으로 손으로 짰다 ---
융합 판과 수학은 같고, **fx 가 헤드를 노드로 본다**.

🔴 그러므로 이 run 의 그림에 보이는 헤드는 **우리가 그렇게 짠 결과**이지
`nn.MultiheadAttention` 을 그린 것이 아니다.
"""
from __future__ import annotations

import json
import math
import sys
import time

import numpy as np
import torch
import torch.nn as nn

from trainlog import Run

DATA = "data/state/popup_table.npz"
D, NH, DH, DFF = 32, 4, 8, 64


class Head(nn.Module):
    """어텐션 헤드 하나 --- Q·K·V 를 **따로** 가진다(fx 가 노드로 보게)."""

    def __init__(self, d: int = D, dh: int = DH):
        super().__init__()
        self.q = nn.Linear(d, dh)
        self.k = nn.Linear(d, dh)
        self.v = nn.Linear(d, dh)
        self.dh = dh

    def forward(self, x):
        q, k, v = self.q(x), self.k(x), self.v(x)
        a = (q @ k.transpose(-2, -1)) / math.sqrt(self.dh)
        return a.softmax(-1) @ v


class Block(nn.Module):
    """트랜스포머 블록 하나 --- 잔차 둘 · LayerNorm 둘 · 멀티헤드 · FFN."""

    def __init__(self, d: int = D, nh: int = NH, dh: int = DH, dff: int = DFF):
        super().__init__()
        self.ln1 = nn.LayerNorm(d)
        self.heads = nn.ModuleList([Head(d, dh) for _ in range(nh)])
        self.proj = nn.Linear(nh * dh, d)
        self.ln2 = nn.LayerNorm(d)
        self.ff1 = nn.Linear(d, dff)
        self.act = nn.GELU()
        self.ff2 = nn.Linear(dff, d)

    def forward(self, x):
        h = torch.cat([hd(self.ln1(x)) for hd in self.heads], dim=-1)
        x = x + self.proj(h)                      # 잔차 ①
        return x + self.ff2(self.act(self.ff1(self.ln2(x))))   # 잔차 ②


class TabFormer(nn.Module):
    def __init__(self, T: int, d: int = D):
        super().__init__()
        self.tok = nn.Linear(1, d)
        self.pos = nn.Embedding(T, d)
        self.block = Block(d)
        self.out = nn.Linear(d, 1)
        #: 🔴 버퍼로 둔다 --- `forward` 안에서 `torch.arange(x.shape[1])` 를 부르면
        #: `torch.fx` 가 심볼 모양에서 터진다(그러면 간선이 **가정**으로 떨어진다).
        self.register_buffer("ids", torch.arange(T))

    def forward(self, x):                         # x: (N, T)
        h = self.tok(x.unsqueeze(-1)) + self.pos(self.ids)
        return self.out(self.block(h)).squeeze(-1)


def _fx_probe() -> dict:
    """🔴 **fx 함정을 실측한다** --- 융합 어텐션은 정말 추적이 안 되나."""
    import torch.fx as fx
    out = {}
    for 이름, mk in (("nn.MultiheadAttention",
                     lambda: nn.MultiheadAttention(D, NH, batch_first=True)),
                    ("nn.TransformerEncoderLayer",
                     lambda: nn.TransformerEncoderLayer(D, NH, DFF,
                                                        batch_first=True)),
                    ("이 러너의 Block(손으로 짠 헤드)", lambda: Block())):
        try:
            g = fx.symbolic_trace(mk()).graph
            out[이름] = {"추적됨": True, "노드 수": len(list(g.nodes))}
        except Exception as e:
            out[이름] = {"추적됨": False,
                        "왜": f"{type(e).__name__}: {str(e)[:120]}"}
    return out


def main(steps: int = 4000) -> int:
    d = np.load(DATA, allow_pickle=True)
    X = np.asarray(d["X"], dtype=np.float64)
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    Xt = torch.tensor(X, dtype=torch.float32)
    T = Xt.shape[1]
    torch.manual_seed(0)
    net = TabFormer(T)
    opt = torch.optim.Adam(net.parameters(), lr=2e-3)
    #: 🔴 노드 이름은 **`arch.json` 의 층 id 와 같아야** 그래프에 얹힌다.
    노드 = {n: m for n, m in net.named_modules() if n and not list(m.children())}
    t0 = time.time()
    with Run("popup 표를 토큰열로 본 트랜스포머 블록 하나",
             pushes="해당 없음", ruler=None, demo=False, trained=True,
             seed=0, code=[__file__], data=[DATA],
             hparams={"d": D, "헤드 수": NH, "헤드 폭": DH, "FFN": DFF,
                      "토큰 수(=열 수)": int(T), "lr": 2e-3, "steps": steps,
                      "optim": "Adam", "손실": "복원 MSE 하나뿐(라벨을 안 본다)"},
             note=("노트 913 팔 ㅈ --- 뷰어가 **잔차·분기·합류·헤드**를 실제로 "
                   "그리는지와 **노드별 grad_norm 이 그래프 위에 얹히는지**를 재려고 "
                   "지은 트랜스포머 블록 하나. 자료는 실물(popup_table.npz 의 X)이고 "
                   "🔴 **라벨 y 를 한 번도 안 본다** --- 복원 손실만 줄인다. "
                   "이 곡선으로는 아무것도 주장하지 않는다"),
             flush_every=1, flush_secs=0.05) as r:
        a = r.arch(net)
        for step in range(1, int(steps) + 1):
            opt.zero_grad()
            xh = net(Xt)
            loss = ((xh - Xt) ** 2).mean()
            loss.backward()
            #: 🔴 **재는 것만 적는다.** grad 가 None 인 모듈은 **안 적는다**
            #: --- 0 으로 적으면 「안 배운다」는 거짓 신호가 된다.
            if step % 25 == 0:
                for 이름, m in 노드.items():
                    gs = [p.grad for p in m.parameters(recurse=False)
                          if p.grad is not None]
                    if not gs:
                        continue
                    gn = float(torch.sqrt(sum((g ** 2).sum() for g in gs)))
                    pn = float(torch.sqrt(sum(
                        (p.detach() ** 2).sum()
                        for p in m.parameters(recurse=False))))
                    r.log_node(step=step, node=이름, grad_norm=gn, param_norm=pn)
            opt.step()
            if step % 5 == 0:
                r.log(step=step, split="train", recon_mse=loss.detach().item())
        r.arch(net)                     # 학습 끝난 가중치로 다시 적는다
        rid, n, nn_ = r.run_id, r._n, r._nn
    print(json.dumps({
        "run_id": rid, "지표 줄 수": n, "노드 지표 줄 수": nn_,
        "층 수": len(a.get("층") or []), "간선 수": len(a.get("간선") or []),
        "간선 출처": a.get("간선 출처"),
        "총 파라미터": a.get("총 파라미터"),
        "초": round(time.time() - t0, 2),
        "🔴 fx 실측": _fx_probe(),
        "🔴 무엇을 안 봤나": "라벨 y --- 복원 손실만 줄였다",
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 4000))
