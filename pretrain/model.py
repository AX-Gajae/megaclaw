# -*- coding: utf-8 -*-
"""디코더 전용 트랜스포머 LM — RoPE · RMSNorm · SDPA · 임베딩 묶기.

설계 근거(전부 표준 · 특이 선택 없음):
  · pre-norm + RMSNorm       — 작은 규모에서 안정
  · RoPE                     — 위치 파라미터 0 · seq 연장 여지
  · F.scaled_dot_product_attention(is_causal=True) — MPS 에서 동작(torch 2.8)
  · lm_head 는 wte 와 가중치 공유 — 32k 어휘에서 파라미터 절약
  · init: N(0, 0.02) · 잔차 출력층은 0.02/√(2·n_layer)  (GPT-2 계보)
"""
import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from pretrain.config import ModelConfig


class RMSNorm(nn.Module):
    def __init__(self, d, eps=1e-5):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x):
        # fp32 로 분산을 재고 원래 dtype 으로 돌아온다(bf16 autocast 안전)
        dt = x.dtype
        x = x.float()
        x = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return (x * self.weight.float()).to(dt)


def _rope_tables(d_head, max_seq, base):
    inv = 1.0 / (base ** (torch.arange(0, d_head, 2).float() / d_head))
    t = torch.arange(max_seq).float()
    freqs = torch.outer(t, inv)                       # (T, Dh/2)
    cos = torch.cat([freqs.cos(), freqs.cos()], dim=-1)   # (T, Dh)
    sin = torch.cat([freqs.sin(), freqs.sin()], dim=-1)
    return cos, sin


def _rotate_half(x):
    h = x.shape[-1] // 2
    return torch.cat([-x[..., h:], x[..., :h]], dim=-1)


def _apply_rope(q, k, cos, sin):
    # q, k: (B, H, T, Dh) · cos/sin: (T, Dh)
    T = q.shape[-2]
    c = cos[:T].to(q.dtype)[None, None]
    s = sin[:T].to(q.dtype)[None, None]
    return q * c + _rotate_half(q) * s, k * c + _rotate_half(k) * s


class Attention(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        assert cfg.d_model % cfg.n_head == 0
        self.n_head = cfg.n_head
        self.d_head = cfg.d_model // cfg.n_head
        self.qkv = nn.Linear(cfg.d_model, 3 * cfg.d_model, bias=False)
        self.proj = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
        self.dropout = cfg.dropout

    def forward(self, x, cos, sin):
        B, T, C = x.shape
        q, k, v = self.qkv(x).split(C, dim=2)
        q = q.view(B, T, self.n_head, self.d_head).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.d_head).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.d_head).transpose(1, 2)
        q, k = _apply_rope(q, k, cos, sin)
        y = F.scaled_dot_product_attention(
            q, k, v, is_causal=True,
            dropout_p=self.dropout if self.training else 0.0)
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.proj(y)


class MLP(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.up = nn.Linear(cfg.d_model, 4 * cfg.d_model, bias=False)
        self.down = nn.Linear(4 * cfg.d_model, cfg.d_model, bias=False)

    def forward(self, x):
        return self.down(F.gelu(self.up(x), approximate="tanh"))


class Block(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.ln1 = RMSNorm(cfg.d_model)
        self.attn = Attention(cfg)
        self.ln2 = RMSNorm(cfg.d_model)
        self.mlp = MLP(cfg)

    def forward(self, x, cos, sin):
        x = x + self.attn(self.ln1(x), cos, sin)
        x = x + self.mlp(self.ln2(x))
        return x


class GPT(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.wte = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.blocks = nn.ModuleList([Block(cfg) for _ in range(cfg.n_layer)])
        self.ln_f = RMSNorm(cfg.d_model)
        cos, sin = _rope_tables(cfg.d_model // cfg.n_head, cfg.seq_len, cfg.rope_base)
        self.register_buffer("rope_cos", cos, persistent=False)
        self.register_buffer("rope_sin", sin, persistent=False)
        self.apply(self._init)
        # 잔차 출력층 스케일 다운
        for name, p in self.named_parameters():
            if name.endswith("proj.weight") or name.endswith("down.weight"):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * cfg.n_layer))

    def _init(self, m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)

    def forward(self, idx, targets=None):
        assert idx.shape[1] <= self.cfg.seq_len, "seq_len 초과"
        x = self.wte(idx)
        for blk in self.blocks:
            x = blk(x, self.rope_cos, self.rope_sin)
        x = self.ln_f(x)
        logits = F.linear(x, self.wte.weight)          # 묶인 lm_head
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)).float(),
                targets.reshape(-1), ignore_index=-1)
        return logits, loss

    # ── 크기 · 옵티마이저 ─────────────────────────────────────────────
    def n_params(self, non_embedding=True):
        n = sum(p.numel() for p in self.parameters())
        if non_embedding:
            n -= self.wte.weight.numel()
        return n

    def configure_optimizer(self, lr, weight_decay=0.1, betas=(0.9, 0.95)):
        decay, nodecay = [], []
        for p in self.parameters():
            if not p.requires_grad:
                continue
            (decay if p.dim() >= 2 else nodecay).append(p)
        groups = [
            {"params": decay, "weight_decay": weight_decay},
            {"params": nodecay, "weight_decay": 0.0},
        ]
        return torch.optim.AdamW(groups, lr=lr, betas=betas, eps=1e-8)
