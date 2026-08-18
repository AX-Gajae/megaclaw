# -*- coding: utf-8 -*-
"""토큰 샤드 로더 — uint16 bin + index.json · 시대(블록) 필터 · 결정론 배치.

index.json 스키마(경로는 index 파일 기준 상대):
{
 "tokenizer": "…/tokenizer.json", "vocab_size": 32768, "eot_id": 0,
 "shards": [
   {"path": "CC-MAIN-2013-20.train.bin", "dump": "CC-MAIN-2013-20",
    "year": 2013.375, "block": 0, "split": "train",
    "n_tokens": 123456, "n_bytes": 456789, "n_docs": 1234}, …]
}

결정론: 배치는 (seed, step) 에서 «유도»된다 — RNG 상태를 저장할 필요가 없어
재개(resume)가 자동으로 같은 배치 열을 밟는다.

시대 필터: max_block 을 주면 «그 블록 이하» 샤드만 학습에 쓴다 —
「블록 ≤ b 로 학습해 블록 > b 를 평가」하는 시간 방향 사전학습이 이 한 줄로 선다.
"""
import json
import os
from typing import Optional

import numpy as np
import torch


class Batcher:
    def __init__(self, index_path, split="train", max_block=None, seq=1024, seed=1234):
        self.seq = int(seq)
        self.seed = int(seed)
        base = os.path.dirname(os.path.abspath(index_path))
        with open(index_path, encoding="utf-8") as f:
            self.index = json.load(f)
        self.shards = []
        self.mms = []
        sizes = []
        for sh in self.index["shards"]:
            if sh["split"] != split:
                continue
            if max_block is not None and sh["block"] > max_block:
                continue
            if sh["n_tokens"] < self.seq + 1:
                continue                     # 창 하나도 못 뽑는 샤드는 뺀다
            p = os.path.join(base, sh["path"])
            mm = np.memmap(p, dtype=np.uint16, mode="r")
            assert len(mm) == sh["n_tokens"], (
                "🔴 index 와 파일 길이 불일치: %s (%d != %d)" % (p, len(mm), sh["n_tokens"]))
            self.shards.append(sh)
            self.mms.append(mm)
            sizes.append(sh["n_tokens"])
        if not self.shards:
            raise RuntimeError("🔴 조건에 맞는 샤드가 0 개다 (split=%s max_block=%s)"
                               % (split, max_block))
        sizes = np.asarray(sizes, dtype=np.float64)
        self.mass = sizes / sizes.sum()      # 토큰 질량 비례 표집
        self.total_tokens = int(sizes.sum())

    def blocks(self):
        return sorted(set(sh["block"] for sh in self.shards))

    def batch(self, batch_size, step):
        """(seed, step) 결정론 배치 → (x, y) int64 텐서."""
        rng = np.random.default_rng([self.seed, int(step)])
        sh_ids = rng.choice(len(self.shards), size=batch_size, p=self.mass)
        xs = np.empty((batch_size, self.seq), dtype=np.int64)
        ys = np.empty((batch_size, self.seq), dtype=np.int64)
        for i, si in enumerate(sh_ids):
            mm = self.mms[si]
            off = int(rng.integers(0, len(mm) - self.seq))   # high 배타 — 마지막 창 포함
            win = np.asarray(mm[off:off + self.seq + 1], dtype=np.int64)
            xs[i] = win[:-1]
            ys[i] = win[1:]
        return torch.from_numpy(xs), torch.from_numpy(ys)

    # ── 평가용: 고정 창을 앞에서부터 stride=seq 로 끊어 낸다 ──────────
    def fixed_windows(self, max_windows_per_shard=None):
        """[(block, x, y)] 제너레이터 — 평가는 표집이 아니라 «고정 창»으로."""
        for sh, mm in zip(self.shards, self.mms):
            n_all = (len(mm) - 1) // self.seq
            if max_windows_per_shard is not None and max_windows_per_shard < n_all:
                # 🔴 적대 검증: 앞쪽 창만 뜨면 표본이 문서 앞부분으로 치우친다 — 고르게 편다
                idxs = np.linspace(0, n_all - 1, max_windows_per_shard).astype(int)
            else:
                idxs = np.arange(n_all)
            for w in idxs:
                off = int(w) * self.seq
                win = np.asarray(mm[off:off + self.seq + 1], dtype=np.int64)
                yield sh["block"], torch.from_numpy(win[:-1]), torch.from_numpy(win[1:])

    def bytes_per_token(self, block=None):
        """bpb 환산용 — (해당 블록) 샤드들의 n_bytes / n_tokens."""
        tb = [(sh["n_tokens"], sh["n_bytes"]) for sh in self.shards
              if block is None or sh["block"] == block]
        t = sum(a for a, _ in tb)
        b = sum(c for _, c in tb)
        return (b / t) if t else float("nan")
