# -*- coding: utf-8 -*-
"""사전학습 루프 — MPS/CPU 자동 · bf16 · 체크포인트/재개 · 시대 필터.

씀(연기):
  python3 pretrain/train.py --preset nano --steps 40 --device cpu \
      --index /Users/ax/wm_harvest/foundation/tokens/index.json --name smoke
씀(본 · 하네스가 긴 작업을 죽이므로 반드시 nohup):
  nohup python3 pretrain/train.py --preset tiny --steps 20000 --name tiny-b1 \
      > /Users/ax/wm_harvest/foundation/ckpt/tiny-b1.log 2>&1 & disown

시대 필터: --max-block 2  →  블록 0·1·2 로만 학습(2022.09 이전 웹).
재개:      --resume auto  →  <out>/latest.pt 에서 이어 돈다. 배치 열은
           (seed, step) 유도라 재개 뒤에도 «같은 자료 열»을 밟는다.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import json
import math
import os
import signal
import time

import torch

from pretrain.config import (PRESETS, CKPT_DIR, TOKENS_DIR, ModelConfig,
                             pick_device, amp_ctx)
from pretrain.data import Batcher
from pretrain.model import GPT


def lr_at(step, base_lr, warmup, total, min_ratio=0.1):
    if step < warmup:
        return base_lr * (step + 1) / max(1, warmup)
    t = (step - warmup) / max(1, total - warmup)
    t = min(1.0, max(0.0, t))
    return base_lr * (min_ratio + (1 - min_ratio) * 0.5 * (1 + math.cos(math.pi * t)))


def atomic_save(obj, path):
    tmp = path + ".tmp"
    torch.save(obj, tmp)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="tiny", choices=sorted(PRESETS))
    ap.add_argument("--index", default=os.path.join(TOKENS_DIR, "index.json"))
    ap.add_argument("--name", required=True)
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--micro-batch", type=int, default=16)
    ap.add_argument("--accum", type=int, default=4)
    ap.add_argument("--seq", type=int, default=0, help="0 = preset 값")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--amp", default="bf16", choices=["bf16", "none"])
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--warmup", type=int, default=200)
    ap.add_argument("--min-lr-ratio", type=float, default=0.1)
    ap.add_argument("--weight-decay", type=float, default=0.1)
    ap.add_argument("--clip", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--max-block", type=int, default=-1, help="-1 = 전 블록")
    ap.add_argument("--log-every", type=int, default=10)
    ap.add_argument("--ckpt-every", type=int, default=200)
    ap.add_argument("--eval-every", type=int, default=0, help="0 = 안 한다")
    ap.add_argument("--eval-batches", type=int, default=8)
    ap.add_argument("--resume", default="none", help="none | auto | <경로>")
    ap.add_argument("--threads", type=int, default=0, help="CPU torch 스레드(0=기본)")
    a = ap.parse_args()

    cfg = PRESETS[a.preset]
    if a.seq:
        cfg = ModelConfig(**{**cfg.to_dict(), "seq_len": a.seq})
    torch.manual_seed(a.seed)
    if a.threads:
        torch.set_num_threads(a.threads)

    out = os.path.join(CKPT_DIR, a.name)
    if a.resume == "none" and os.path.exists(os.path.join(out, "latest.pt")):
        raise SystemExit("🔴 %s/latest.pt 가 이미 있다 — 이어 돌리려면 --resume auto, "
                         "새로 하려면 다른 --name (조용한 덮어쓰기 금지 · 적대 검증)" % out)
    os.makedirs(out, exist_ok=True)
    metrics_path = os.path.join(out, "metrics.jsonl")
    progress_path = os.path.join(out, "progress.txt")

    max_block = None if a.max_block < 0 else a.max_block
    data = Batcher(a.index, split="train", max_block=max_block,
                   seq=cfg.seq_len, seed=a.seed)
    vs = data.index["vocab_size"]
    cfg = ModelConfig(**{**cfg.to_dict(), "vocab_size": vs})
    val = None
    if a.eval_every:
        try:
            val = Batcher(a.index, split="val", max_block=max_block,
                          seq=cfg.seq_len, seed=a.seed + 1)
        except RuntimeError:
            val = None                      # val 샤드가 없으면 조용히 끈다(기록은 남긴다)

    device = pick_device(cfg, a.device)
    model = GPT(cfg).to(device)
    opt = model.configure_optimizer(lr=a.lr, weight_decay=a.weight_decay)

    start_step = 0
    if a.resume != "none":
        path = os.path.join(out, "latest.pt") if a.resume == "auto" else a.resume
        if os.path.exists(path):
            ck = torch.load(path, map_location=device, weights_only=False)
            model.load_state_dict(ck["model"])
            opt.load_state_dict(ck["opt"])
            start_step = ck["step"]
            print("재개: %s → step %d" % (path, start_step), flush=True)
        elif a.resume != "auto":
            raise SystemExit("🔴 재개 체크포인트가 없다: %s" % path)

    if start_step >= a.steps:
        # 🔴 적대 검증: 끝난 러닝을 재기동하면 루프가 0 회 돌아 UnboundLocalError 로
        #    죽었다(크론·재기동 래퍼가 no-op 대신 실패). 조용히 성공으로 끝낸다.
        print(json.dumps({"이미 끝남": start_step, "요청 steps": a.steps},
                         ensure_ascii=False), flush=True)
        return

    stop = {"now": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__("now", True))

    tokens_per_step = a.micro_batch * a.accum * cfg.seq_len
    meta = {"preset": a.preset, "cfg": cfg.to_dict(), "device": device,
            "params_non_emb": model.n_params(True), "params_total": model.n_params(False),
            "tokens_per_step": tokens_per_step, "max_block": a.max_block,
            "train_tokens_pool": data.total_tokens, "args": vars(a)}
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: meta[k] for k in
                      ("device", "params_total", "tokens_per_step", "train_tokens_pool")},
                     ensure_ascii=False), flush=True)

    model.train()
    t_win, tok_win = time.time(), 0
    mf = open(metrics_path, "a", encoding="utf-8")
    for step in range(start_step, a.steps):
        lr = lr_at(step, a.lr, a.warmup, a.steps, a.min_lr_ratio)
        for g in opt.param_groups:
            g["lr"] = lr
        opt.zero_grad(set_to_none=True)
        loss_acc = 0.0
        for micro in range(a.accum):
            x, y = data.batch(a.micro_batch, step * a.accum + micro)
            x, y = x.to(device), y.to(device)
            with amp_ctx(device, a.amp):
                _, loss = model(x, y)
            (loss / a.accum).backward()
            loss_acc += loss.item() / a.accum
        torch.nn.utils.clip_grad_norm_(model.parameters(), a.clip)
        opt.step()
        tok_win += tokens_per_step

        if (step + 1) % a.log_every == 0 or step + 1 == a.steps:
            dt = time.time() - t_win
            rec = {"step": step + 1, "loss": round(loss_acc, 4), "lr": round(lr, 6),
                   "tok_per_s": round(tok_win / max(dt, 1e-9), 1),
                   "t": round(time.time(), 1)}
            mf.write(json.dumps(rec) + "\n")
            mf.flush()
            with open(progress_path, "w") as pf:
                pf.write("step %d/%d loss %.4f tok/s %.0f device %s\n"
                         % (step + 1, a.steps, loss_acc, rec["tok_per_s"], device))
            t_win, tok_win = time.time(), 0

        if val is not None and a.eval_every and (step + 1) % a.eval_every == 0:
            model.eval()
            with torch.no_grad():
                vl = 0.0
                for vb in range(a.eval_batches):
                    vx, vy = val.batch(a.micro_batch, vb)
                    vx, vy = vx.to(device), vy.to(device)
                    with amp_ctx(device, a.amp):
                        _, l = model(vx, vy)
                    vl += l.item() / a.eval_batches
            model.train()
            mf.write(json.dumps({"step": step + 1, "val_loss": round(vl, 4)}) + "\n")
            mf.flush()

        if (step + 1) % a.ckpt_every == 0 or step + 1 == a.steps or stop["now"]:
            atomic_save({"model": model.state_dict(), "opt": opt.state_dict(),
                         "step": step + 1, "cfg": cfg.to_dict(), "args": vars(a)},
                        os.path.join(out, "latest.pt"))
        if stop["now"]:
            print("SIGTERM — step %d 에서 저장하고 멈춘다" % (step + 1), flush=True)
            break

    mf.close()
    summary = {"done_step": min(step + 1, a.steps) if a.steps else 0,
               "final_loss": round(loss_acc, 4), "device": device,
               "ckpt": os.path.join(out, "latest.pt")}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
