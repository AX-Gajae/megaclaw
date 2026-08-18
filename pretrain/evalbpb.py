# -*- coding: utf-8 -*-
"""체크포인트 평가 — 시대(블록)별 bpb(bits per byte).

bpb 를 쓰는 까닭: 토크나이저가 달라도 비교가 서는 «라벨 0 비트» 자다.
  bpb(블록) = 평균 nll(nats/token) / ln2 × (그 블록 val 의 tokens/bytes)

시간 방향 평가: --max-block 2 로 학습한 모형을 여기서 «전 블록»에 대해 재면
「과거로 학습한 몸통이 미래 텍스트를 얼마나 놓치는가」가 블록별 표로 나온다.

씀:
  python3 pretrain/evalbpb.py --ckpt <…>/latest.pt --windows-per-shard 8
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import json
import math
import os

import torch

from pretrain.config import TOKENS_DIR, ModelConfig, pick_device, amp_ctx
from pretrain.data import Batcher
from pretrain.model import GPT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--index", default=os.path.join(TOKENS_DIR, "index.json"))
    ap.add_argument("--device", default="auto")
    ap.add_argument("--micro-batch", type=int, default=16)
    ap.add_argument("--windows-per-shard", type=int, default=8)
    ap.add_argument("--amp", default="bf16", choices=["bf16", "none"])
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    ck = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    cfg = ModelConfig.from_dict(ck["cfg"])
    device = pick_device(cfg, a.device)
    model = GPT(cfg).to(device)
    model.load_state_dict(ck["model"])
    model.eval()

    val = Batcher(a.index, split="val", max_block=None, seq=cfg.seq_len)
    # 🔴 적대 검증: 샤드 «전체» bytes/token 을 창 표본 nll 에 곱하면 블록마다
    #    부호가 다른 왜곡(실측 −0.37%~+0.66%)이 생긴다 — 이 도구의 목적이
    #    블록 «간» 비교라 치명. 창의 토큰을 되돌려 «그 창의 바이트»로 잰다.
    tokz = None
    tk_path = val.index.get("tokenizer")
    if tk_path and os.path.exists(tk_path):
        from tokenizers import Tokenizer
        tokz = Tokenizer.from_file(tk_path)
    per_block = {}                      # block → [sum_nll, n_tokens, n_bytes(실측)]
    buf_x, buf_y, buf_b = [], [], []

    def flush():
        if not buf_x:
            return
        x = torch.stack(buf_x).to(device)
        y = torch.stack(buf_y).to(device)
        with torch.no_grad():
            with amp_ctx(device, a.amp):
                logits, _ = model(x)
            nll = torch.nn.functional.cross_entropy(
                logits.view(-1, logits.size(-1)).float(), y.reshape(-1),
                reduction="none").view(y.shape)
        for i, b in enumerate(buf_b):
            s = per_block.setdefault(b, [0.0, 0, 0])
            s[0] += float(nll[i].sum())
            s[1] += int(nll.shape[1])
            if tokz is not None:
                ids = [int(t) for t in y[i].tolist()]
                s[2] += len(tokz.decode(ids).encode("utf-8", "ignore"))
        del buf_x[:], buf_y[:], buf_b[:]

    for block, x, y in val.fixed_windows(max_windows_per_shard=a.windows_per_shard):
        buf_x.append(x)
        buf_y.append(y)
        buf_b.append(block)
        if len(buf_x) >= a.micro_batch:
            flush()
    flush()

    table = {}
    for b in sorted(per_block):
        nll_sum, n_tok, n_byt = per_block[b]
        nll_tok = nll_sum / max(1, n_tok)
        bpt = nll_tok / math.log(2)                      # bits per token
        if n_byt > 0:
            bpb = (nll_sum / math.log(2)) / n_byt        # 🔴 창 «실측» 바이트
            src = "창 실측 바이트"
        else:
            bpb = bpt / max(1e-9, val.bytes_per_token(b))
            src = "⚠ 샤드 평균 근사(토크나이저 없음)"
        table["블록 %d" % b] = {
            "평가 토큰": n_tok, "평가 바이트(실측)": n_byt,
            "nll/token": round(nll_tok, 4), "bits/token": round(bpt, 4),
            "bpb": round(bpb, 4), "bpb 출처": src}
    rep = {"ckpt": os.path.abspath(a.ckpt), "step": ck.get("step"),
           "device": device, "표": table}
    out = a.out or (a.ckpt + ".bpb.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()
