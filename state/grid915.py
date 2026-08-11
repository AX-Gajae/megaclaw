# -*- coding: utf-8 -*-
"""팔 915-ㅋ · 격자 시공간 장 — **라벨 0비트**로 만드는 기질.

🔴 사전등록 `docs/prereg_915_grid.md` §4.1 규율
  · 이 모듈은 **판 라벨을 한 비트도 안 연다.** `assert_no_label_files()` 가
    「내가 연 파일 목록」에 라벨 파일이 없음을 **코드로 단언**한다.
  · 값은 `생활인구합계` 하나. 격자 단위로 **행정동을 넘어 합산된 것**이다(ingest/lifepop915.py).
  · 마스킹 `*` 는 0 으로 접혔다 — 「0 이었다」가 아니라 「≤3 이라 가려졌다」.

만드는 것(전부 **스크래치패드** · 저장소 밖)
  field.npy   (격자 8,880 × 날짜 577 × 시각 24) float32
  obs.npy     (격자 × 날짜) bool — 그 날 그 격자에 행이 있었나
  index.json  격자 목록 · 날짜 목록 · 이웃 색인
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
SCR = Path(os.environ.get(
    "G915_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad")) / "g915"

#: 🔴 이 모듈이 **절대 안 여는** 파일들. 라벨이 여기 있다.
LABEL_FILES = ("popup_v2.npz", "popup_v2_meta.json", "market_axes.json",
               "denominator.json", "kobis_axes.json", "y_perday")


def assert_no_label_files(opened: list[str]) -> None:
    """🔴 라벨 0비트 단언 — 연 파일 목록에 라벨 파일이 하나라도 있으면 죽는다."""
    bad = [o for o in opened for t in LABEL_FILES if t in o]
    if bad:
        raise AssertionError(f"🔴 라벨 파일을 열었다 — 프리텍스트가 오염됐다: {bad}")


def build(force: bool = False) -> dict:
    """달별 npz 19개를 하나의 (격자 × 날짜 × 시각) 장으로 잇는다."""
    opened = [str(p) for p in sorted(SCR.glob("250_LOCAL_RESD_*.npz"))]
    assert_no_label_files(opened)                       # 🔴 라벨 0비트
    fp, op, ix = SCR / "field.npy", SCR / "obs.npy", SCR / "index.json"
    if fp.exists() and ix.exists() and not force:
        return json.loads(ix.read_text())

    grids: set[str] = set()
    days: list[str] = []
    for f in opened:
        z = np.load(f, allow_pickle=False)
        grids |= set(z["grids"].tolist())
        days += z["days"].tolist()
    G = sorted(grids)
    D = sorted(set(days))
    gi = {g: i for i, g in enumerate(G)}
    di = {d: i for i, d in enumerate(D)}
    assert len(days) == len(D), "🔴 날짜가 달 사이에 겹친다 — 분모가 무너진다"

    F = np.lib.format.open_memmap(fp, mode="w+", dtype=np.float32,
                                  shape=(len(G), len(D), 24))
    for f in opened:
        z = np.load(f, allow_pickle=False)
        rg = [gi[g] for g in z["grids"].tolist()]
        rd = [di[d] for d in z["days"].tolist()]
        V = z["V"]
        F[np.ix_(rg, rd)] = V
    F.flush()
    OB = (F.sum(axis=2) > 0)
    np.save(op, OB)

    # 이웃 색인 — `다사EEEENNNN` 의 EEEE/NNNN 은 10m 단위 · 칸 간격 25(=250m)
    ecoord = np.array([int(g[2:6]) for g in G])
    ncoord = np.array([int(g[6:10]) for g in G])
    key = {(int(e), int(n)): i for i, (e, n) in enumerate(zip(ecoord, ncoord))}
    NB = np.full((len(G), 8), -1, np.int32)
    for i, (e, n) in enumerate(zip(ecoord, ncoord)):
        for j, (de, dn) in enumerate(((-25, -25), (-25, 0), (-25, 25), (0, -25),
                                      (0, 25), (25, -25), (25, 0), (25, 25))):
            NB[i, j] = key.get((int(e) + de, int(n) + dn), -1)
    np.save(SCR / "nb.npy", NB)

    meta = {"격자 수": len(G), "날짜 수": len(D), "시각 수": 24,
            "칸 = 격자×날짜×시각": int(len(G) * len(D) * 24),
            "🔴 관측된 (격자,날짜)": int(OB.sum()),
            "🔴 안 관측된 (격자,날짜)": int(OB.size - OB.sum()),
            "관측 비율": round(float(OB.mean()), 6),
            "이웃 8칸이 다 있는 격자": int((NB >= 0).all(1).sum()),
            "이웃이 하나도 없는 격자": int((NB < 0).all(1).sum()),
            "field.npy 바이트": int(fp.stat().st_size),
            "격자": G, "날짜": D,
            "🔴 라벨 0비트": "이 장을 만들며 연 파일은 달별 npz 19개뿐이다(assert_no_label_files)",
            "연 파일": opened}
    ix.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta


def load():
    meta = json.loads((SCR / "index.json").read_text())
    F = np.load(SCR / "field.npy", mmap_mode="r")
    OB = np.load(SCR / "obs.npy")
    NB = np.load(SCR / "nb.npy")
    return meta, F, OB, NB


if __name__ == "__main__":
    m = build()
    print(json.dumps({k: v for k, v in m.items()
                      if k not in ("격자", "날짜", "연 파일")}, ensure_ascii=False, indent=1))
