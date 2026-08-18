# -*- coding: utf-8 -*-
"""CPU 대 MPS — «진짜 이 모형»으로 재는 장치 벤치마크.

`config.MPS_MIN_WIDTH` 의 근거를 만드는 러너다. 조항 81(보고는 증거가 아니다)
때문에 /tmp 벤치를 이 파일로 승격했다 — 산출물은 ART_DIR/bench_device.json.

씀:  python3 pretrain/bench_device.py --steps 30
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import json
import os
import time

import torch

from pretrain.config import ART_DIR, PRESETS
from pretrain.model import GPT


def bench(preset, device, micro_batch, steps):
    cfg = PRESETS[preset]
    m = GPT(cfg).to(device)
    opt = m.configure_optimizer(lr=3e-4)
    x = torch.randint(0, cfg.vocab_size, (micro_batch, cfg.seq_len), device=device)
    y = torch.randint(0, cfg.vocab_size, (micro_batch, cfg.seq_len), device=device)
    for _ in range(5):                                   # 워밍업
        opt.zero_grad(set_to_none=True)
        _, loss = m(x, y)
        loss.backward()
        opt.step()
    if device == "mps":
        torch.mps.synchronize()
    t0 = time.time()
    for _ in range(steps):
        opt.zero_grad(set_to_none=True)
        _, loss = m(x, y)
        loss.backward()
        opt.step()
    if device == "mps":
        torch.mps.synchronize()
    dt = time.time() - t0
    toks = micro_batch * cfg.seq_len * steps
    return {"초": round(dt, 2), "tok_per_s": round(toks / dt, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--presets", default="nano,tiny,small")
    ap.add_argument("--micro-batch", type=int, default=16)
    a = ap.parse_args()

    rows = {}
    for p in a.presets.split(","):
        cpu = bench(p, "cpu", a.micro_batch, a.steps)
        row = {"cpu": cpu}
        if torch.backends.mps.is_available():
            mps = bench(p, "mps", a.micro_batch, a.steps)
            row["mps"] = mps
            row["mps/cpu 속도비"] = round(mps["tok_per_s"] / cpu["tok_per_s"], 2)
        rows[p] = row
    rep = {"torch": torch.__version__,
           "mps_available": torch.backends.mps.is_available(),
           "micro_batch": a.micro_batch, "steps": a.steps, "표": rows}
    os.makedirs(ART_DIR, exist_ok=True)
    out = os.path.join(ART_DIR, "bench_device.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()
