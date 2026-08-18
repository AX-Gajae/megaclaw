# -*- coding: utf-8 -*-
"""한국어 32k ByteLevel-BPE 토크나이저 학습 — FineWeb2-ko 표본에서.

왜 32k 를 새로 훈련하나(기계에 있는 XLM-R 250k · Qwen3 151k 를 안 쓰고):
  임베딩 파라미터 = 어휘 × d_model. d=512 에서 250k 어휘면 임베딩만 128M —
  모형 몸통(25M)의 5 배가 어휘에 먹힌다. 한국어 전용 32k 면 16.8M 으로 끝나고
  토큰 id 가 65,535 아래라 «uint16» 저장이 서서 디스크가 절반이 된다.

씀:
  python3 pretrain/tok_train.py --sample-bytes 1500000000 --vocab 32768
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import glob
import json
import os
import time
import unicodedata

import pyarrow.parquet as pq

from pretrain.config import FW2_DIR, TOKENIZER_DIR


def sample_texts(files, per_file_bytes, batch_rows=2048):
    """파일마다 행그룹을 골고루 건너뛰며 per_file_bytes 만큼 뽑는다."""
    for fp in files:
        pf = pq.ParquetFile(fp)
        n_rg = pf.metadata.num_row_groups
        stride = max(1, n_rg // 8)          # 파일당 최대 ~8 행그룹 — 시기 편향 완화
        got = 0
        for rg in range(0, n_rg, stride):
            if got >= per_file_bytes:
                break
            tbl = pf.read_row_group(rg, columns=["text"])
            for chunk in tbl.column("text").chunks:
                for v in chunk:
                    s = v.as_py()
                    if not s:
                        continue
                    got += len(s.encode("utf-8", "ignore"))
                    yield s
                    if got >= per_file_bytes:
                        break
                if got >= per_file_bytes:
                    break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-bytes", type=float, default=1.5e9)
    ap.add_argument("--vocab", type=int, default=32768)
    ap.add_argument("--out", default=TOKENIZER_DIR)
    a = ap.parse_args()

    from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders, normalizers

    files = sorted(glob.glob(os.path.join(FW2_DIR, "*.parquet")))
    assert files, "🔴 FineWeb2 파일이 없다: %s" % FW2_DIR
    per_file = int(a.sample_bytes / len(files))

    tok = Tokenizer(models.BPE(unk_token=None))
    tok.normalizer = normalizers.NFC()                    # 한글 조합 통일
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(
        vocab_size=a.vocab, min_frequency=2, show_progress=False,
        special_tokens=["<|endoftext|>"],
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet())

    t0 = time.time()
    tok.train_from_iterator(sample_texts(files, per_file), trainer=trainer)
    train_s = time.time() - t0

    os.makedirs(a.out, exist_ok=True)
    out_path = os.path.join(a.out, "tokenizer.json")
    tok.save(out_path)

    # ── 검증: 왕복(roundtrip) + 압축률을 «학습에 안 쓴» 표본에서 잰다 ──
    probe = []
    pf = pq.ParquetFile(files[-1])
    tbl = pf.read_row_group(pf.metadata.num_row_groups - 1, columns=["text"])
    for chunk in tbl.column("text").chunks:
        for v in chunk:
            s = v.as_py()
            if s:
                probe.append(s)
            if len(probe) >= 2000:
                break
        if len(probe) >= 2000:
            break
    probe_bytes = sum(len(s.encode("utf-8", "ignore")) for s in probe)
    encs = tok.encode_batch(probe)
    probe_tokens = sum(len(e.ids) for e in encs)
    # 왕복: NFC 정규화 뒤 원문과 같아야 한다(ByteLevel 은 무손실)
    rt_fail = 0
    for s, e in zip(probe[:200], encs[:200]):
        if tok.decode(e.ids) != unicodedata.normalize("NFC", s):
            rt_fail += 1

    rep = {
        "tokenizer": out_path,
        "vocab_size": tok.get_vocab_size(),
        "eot_id": tok.token_to_id("<|endoftext|>"),
        "train_seconds": round(train_s, 1),
        "sample_bytes": int(a.sample_bytes),
        "probe_docs": len(probe),
        "tok_per_byte": round(probe_tokens / max(1, probe_bytes), 4),
        "roundtrip_fail(200 중)": rt_fail,
    }
    with open(os.path.join(a.out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()
