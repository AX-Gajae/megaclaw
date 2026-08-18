# -*- coding: utf-8 -*-
"""FineWeb2-ko → 시대별(dump) uint16 토큰 샤드 + index.json.

전략 — «dump 당 문서 상한»(균형 표집):
  96 개 크롤 체크포인트마다 최대 N 문서씩 뽑는다. 비례가 아니라 «균형»인 이유:
  시간 방향 실험(블록 ≤ b 학습 → 블록 > b 평가)은 시대마다 자료가 고르게
  있어야 검정력이 산다. dump 두께 차가 실측 98.9 배라 비례로 뽑으면
  2023 년이 판을 다 먹는다.

효율 — 행그룹 선(先)검사:
  `dump` 열(전량 압축 8MB · 2.8 초)만 먼저 읽어 그 행그룹에 «아직 상한이 안 찬
  dump» 가 있는지 보고, 있을 때만 `text` 를 읽는다. 60.8M 행 중 ~2% 만 뽑으므로
  본문 읽기가 그 근처로 준다.

검증 분할: md5(id) 의 하위 3 자리 < val_permille → val (기본 5/1000).

씀:
  python3 pretrain/tokenize_corpus.py --docs-per-dump 14000
  (기본이면 ≈ 96 dump × 14k 문서 × ~880 tok ≈ 1.2B 토큰 · uint16 ≈ 2.4 GB)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import glob
import hashlib
import json
import os
import time
import unicodedata

import numpy as np
import pyarrow.parquet as pq

from pretrain.config import FW2_DIR, TOKENIZER_DIR, TOKENS_DIR, dump_year, year_to_block


def md5_permille(s):
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16) % 1000


class ShardWriter:
    """dump 하나 = (train.bin, val.bin) 한 쌍 — 열린 채로 덧쓴다."""

    def __init__(self, out_dir, dump):
        self.dump = dump
        self.paths = {sp: os.path.join(out_dir, "%s.%s.bin" % (dump, sp))
                      for sp in ("train", "val")}
        self.fh = {sp: open(p, "wb") for sp, p in self.paths.items()}
        self.n_tokens = {"train": 0, "val": 0}
        self.n_bytes = {"train": 0, "val": 0}
        self.n_docs = {"train": 0, "val": 0}

    def add(self, split, ids, nbytes):
        arr = np.asarray(ids, dtype=np.uint16)
        arr.tofile(self.fh[split])
        self.n_tokens[split] += len(arr)
        self.n_bytes[split] += nbytes
        self.n_docs[split] += 1

    def close(self):
        for f in self.fh.values():
            f.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs-per-dump", type=int, default=14000)
    ap.add_argument("--val-permille", type=int, default=5)
    ap.add_argument("--tokenizer", default=os.path.join(TOKENIZER_DIR, "tokenizer.json"))
    ap.add_argument("--out", default=TOKENS_DIR)
    ap.add_argument("--progress", default=os.path.join(TOKENS_DIR, "progress.txt"))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    idx_path = os.path.join(a.out, "index.json")
    if os.path.exists(idx_path) and not a.force:
        raise SystemExit("🔴 index.json 이 이미 있다 — 다시 만들려면 --force")

    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(a.tokenizer)
    eot = tok.token_to_id("<|endoftext|>")
    assert eot is not None, "🔴 <|endoftext|> 가 토크나이저에 없다"
    vocab = tok.get_vocab_size()
    assert vocab <= 65536, "🔴 uint16 초과 어휘"

    os.makedirs(a.out, exist_ok=True)
    files = sorted(glob.glob(os.path.join(FW2_DIR, "*.parquet")))
    assert files, "🔴 FineWeb2 파일이 없다"

    cap = a.docs_per_dump
    taken = {}                                    # dump → 뽑은 문서 수(합계)
    writers = {}
    t0 = time.time()
    rg_seen = rg_read = 0

    def prog(msg):
        with open(a.progress, "w", encoding="utf-8") as f:
            f.write("%s | %.0fs | rg %d/%d 읽음 | dumps %d\n"
                    % (msg, time.time() - t0, rg_read, rg_seen, len(taken)))

    for fi, fp in enumerate(files):
        pf = pq.ParquetFile(fp)
        for rg in range(pf.metadata.num_row_groups):
            rg_seen += 1
            # ① 선검사 — dump 열만
            dumps_col = pf.read_row_group(rg, columns=["dump"]).column("dump").to_pylist()
            need_rows = [i for i, d in enumerate(dumps_col) if taken.get(d, 0) < cap]
            if not need_rows:
                continue
            rg_read += 1
            # ② 본문 읽기 — 필요한 행만 골라 담는다
            tbl = pf.read_row_group(rg, columns=["text", "id"])
            texts = tbl.column("text")        # Arrow 열 그대로 — 필요한 행만 꺼낸다
            ids_ = tbl.column("id")
            batch, meta = [], []
            for i in need_rows:
                d = dumps_col[i]
                if taken.get(d, 0) >= cap:
                    continue
                s = texts[i].as_py()
                if not s:
                    continue
                taken[d] = taken.get(d, 0) + 1
                batch.append(unicodedata.normalize("NFC", s))
                meta.append((d, ids_[i].as_py()))
            del tbl, texts, ids_
            if not batch:
                continue
            encs = tok.encode_batch(batch)
            for (d, doc_id), s, e in zip(meta, batch, encs):
                if d not in writers:
                    writers[d] = ShardWriter(a.out, d)
                split = "val" if md5_permille(str(doc_id)) < a.val_permille else "train"
                writers[d].add(split, list(e.ids) + [eot],
                               len(s.encode("utf-8", "ignore")))
        prog("파일 %d/%d" % (fi + 1, len(files)))
        # 🔴 적대 검증: 조기 종료는 «본 적 있는» dump 만 세므로 dump-major 배열에서
        #    뒤에 처음 나오는 dump 를 유실할 수 있다(모의에서 96 중 6 유실).
        #    선검사 덕에 전체 훑기가 싸다(실측 567 초) — 조기 종료를 없앤다.

    # ── index.json ────────────────────────────────────────────────────
    shards = []
    for d, w in sorted(writers.items()):
        w.close()
        y = dump_year(d)
        blk = year_to_block(y) if y is not None else -1
        for sp in ("train", "val"):
            if w.n_tokens[sp] == 0:
                os.remove(w.paths[sp])
                continue
            shards.append({
                "path": os.path.basename(w.paths[sp]), "dump": d,
                "year": (round(y, 4) if y is not None else None), "block": blk,
                "split": sp, "n_tokens": w.n_tokens[sp],
                "n_bytes": w.n_bytes[sp], "n_docs": w.n_docs[sp]})
    index = {
        "tokenizer": os.path.abspath(a.tokenizer), "vocab_size": vocab,
        "eot_id": eot, "docs_per_dump_cap": cap, "val_permille": a.val_permille,
        "made_seconds": round(time.time() - t0, 1),
        "rowgroups": {"본": rg_seen, "text 까지 읽음": rg_read},
        "shards": shards}
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)

    tot = sum(s["n_tokens"] for s in shards)
    summary = {"dumps": len(writers), "shards": len(shards),
               "n_tokens": tot, "GiB(uint16)": round(tot * 2 / 2 ** 30, 2),
               "seconds": index["made_seconds"], "index": idx_path}
    prog("끝")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
