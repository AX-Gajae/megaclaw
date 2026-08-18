# -*- coding: utf-8 -*-
"""공용 설정 · 경로 · 시간 블록 · 장치 선택.

시간 블록은 챔피언 절단(`lab/harness.py` 계보 · 연도 실수 넷)을 그대로 쓴다 —
사전학습 말뭉치를 「시대」로 자를 수 있어야 월드모델의 시간 방향 실험
(원점 이동 · Z_t · 망각)이 몸통 층에서도 선다.
"""
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── 경로 ──────────────────────────────────────────────────────────────
FW2_DIR = "/Users/ax/wm_harvest/fineweb2_ko"
ART_DIR = os.environ.get("WM_FOUNDATION_DIR", "/Users/ax/wm_harvest/foundation")
TOKENIZER_DIR = os.path.join(ART_DIR, "tokenizer")
TOKENS_DIR = os.path.join(ART_DIR, "tokens")
CKPT_DIR = os.path.join(ART_DIR, "ckpt")

# ── 시간 블록 (챔피언 절단 · 노트 982~996 과 같은 수) ─────────────────
BLOCK_CUTS = [2015.010794, 2019.27089, 2022.0854, 2024.477187]


def year_to_block(y):
    """연도 실수 → 블록 0..4."""
    b = 0
    for c in BLOCK_CUTS:
        if y >= c:
            b += 1
    return b


def dump_year(dump):
    """`CC-MAIN-2013-20` → 2013.375 (ISO 주 → 연도 실수). 못 읽으면 None."""
    try:
        parts = dump.split("-")
        yr, wk = int(parts[-2]), int(parts[-1])
        if not (2000 <= yr <= 2100 and 1 <= wk <= 53):
            return None
        return yr + (wk - 0.5) / 52.0
    except Exception:
        return None


# ── 모형 크기 ─────────────────────────────────────────────────────────
@dataclass
class ModelConfig:
    vocab_size: int = 32768
    d_model: int = 512
    n_layer: int = 8
    n_head: int = 8
    seq_len: int = 1024
    dropout: float = 0.0
    rope_base: float = 10000.0

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        return ModelConfig(**{k: d[k] for k in d if k in ModelConfig.__dataclass_fields__})


PRESETS = {
    # 이름   (연기·단위시험용)      비고
    "nano":  ModelConfig(d_model=256,  n_layer=4,  n_head=4,  seq_len=512),
    # ↓ 실측 GPU 이득 구간(폭 ≥ 512)에 들어가는 첫 크기 — 본 사전학습의 기본
    "tiny":  ModelConfig(d_model=512,  n_layer=8,  n_head=8,  seq_len=1024),
    "small": ModelConfig(d_model=768,  n_layer=12, n_head=12, seq_len=1024),
    "base":  ModelConfig(d_model=1024, n_layer=16, n_head=16, seq_len=1024),
}

# ── 장치 선택 — 실측으로 정한 문턱 (2026-08-18 · M4 Pro · torch 2.8.0) ─
#   폭 256·배치 256 : CPU 0.19s vs MPS 0.22s → CPU 가 빠르다 (0.85×)
#   폭 512·배치1024 : CPU 1.63s vs MPS 0.44s → MPS 3.66×
#   폭1024·배치4096 : CPU 24.77s vs MPS 7.51s → MPS 3.30×
#   → 문턱은 「폭 512」. `pretrain/bench_device.py` 로 언제든 다시 잰다.
MPS_MIN_WIDTH = 512


def pick_device(cfg, explicit=None):
    """장치를 «재서 정한 문턱»으로 고른다. explicit 이 있으면 그대로."""
    import torch
    if explicit and explicit != "auto":
        return explicit
    if torch.backends.mps.is_available() and cfg.d_model >= MPS_MIN_WIDTH:
        return "mps"
    return "cpu"


def amp_ctx(device, mode="bf16"):
    """autocast 컨텍스트. 못 쓰면 nullcontext 로 무해하게 물러선다."""
    import contextlib
    import torch
    if mode == "none" or device == "cpu":
        return contextlib.nullcontext()
    try:
        return torch.autocast(device_type=device, dtype=torch.bfloat16)
    except Exception:
        return contextlib.nullcontext()
