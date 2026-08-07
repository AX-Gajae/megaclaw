"""팝업 표본을 넓히는 세 가지 방식을 **재서** 고른다.

노트 124가 ``빈 260건을 매기면 팝업이 75에서 322로''라고 적었다. 저장소를
열어 보니 그 계산에 조건이 하나 빠져 있었다. 빈 260건은 거의 전부
organizer\\_claim(247)과 media\\_estimate(13)이고, 그 둘은 **계수 방법
필터가 이미 걸러 내고 있다.** 축을 매기는 것만으로 들어오는 것은 17건뿐이다.

    현행    grade A·B · scope · counting in (entry, participation)      n=91
    +태깅   위 조건 그대로, 빈 축만 자동 태거로 채움                    n=91 (축 17건 회복)
    +주장   counting 필터를 풀어 organizer\\_claim 까지                  n=~340

셋째가 노트 124가 실제로 말한 것이고, 그건 태깅 문제가 아니라 **라벨 품질**
문제다. 주최자가 주장한 방문자 수를 믿을 수 있는지는 아직 아무도 안 쟀다.
여기서 잰다.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

AXES = ["experience_density", "goods_scale", "photo_zones", "collab_strength",
        "ip_awareness", "target_breadth", "entry_friction", "media_push",
        "season_fit", "venue_prominence"]
SHARED = ["target_breadth", "venue_prominence", "entry_friction",
          "media_push", "goods_scale"]
TAGS = Path("data/state/autotag_popup.json")
NPZ = Path("data/state/popup_v2.npz")
META = Path("data/state/popup_v2_meta.json")
COUNT_OK = ("entry", "participation")


def build(mode: str = "now", root: str = ".", grades=("A", "B"),
          min_rho: float = 0.0, scope: bool = True) -> tuple:
    """(A, M, y, t, 축이름) --- 공유 축 다섯만 돌려준다(하네스 규약).

    mode  now   현행
          tag   빈 축을 자동 태거로 채움 (계수 필터는 그대로)
          claim 계수 필터를 풀고 자동 태거도 씀
    min_rho 를 주면 그 이하로 재현되는 축은 **채우지 않는다**(마스크 0).
    """
    R = Path(root)
    z = np.load(R / NPZ, allow_pickle=True)
    cols = [str(c) for c in z["names"]]
    X, y, w = z["X"], z["y_perday"], z["w"]
    meta = json.loads((R / META).read_text())
    tg = json.loads((R / TAGS).read_text()) if (R / TAGS).exists() else {"pred": {}}
    rel = {a: tg.get("cv", {}).get(a, {}).get("rho", 0.0) for a in AXES}

    keep = np.zeros(len(y), bool)
    for g in grades:
        j = cols.index(f"trust_{g}") if f"trust_{g}" in cols else None
        if j is not None:
            keep |= X[:, j] > 0.5
    keep &= np.isfinite(y)
    if scope:
        keep &= np.array([bool(m.get("scope_usable")) for m in meta])
    if mode != "claim":
        keep &= np.array([m.get("counting") in COUNT_OK for m in meta])
    else:
        keep &= np.array([m.get("counting") not in (None, "") for m in meta])

    A = np.zeros((len(y), len(SHARED)), np.float32)
    M = np.zeros((len(y), len(SHARED)), np.float32)
    for j, a in enumerate(SHARED):
        A[:, j] = X[:, cols.index(f"t1o_{a}")] / 4.0
        M[:, j] = X[:, cols.index(f"t1o_{a}_mask")]

    # 열 축이 전부 같으면 사람이 안 매긴 것이다(노트 124) --- 마스크를 내린다
    V = np.column_stack([X[:, cols.index(f"t1o_{a}")] for a in AXES])
    empty = V.std(1) < 1e-9
    M[empty] = 0.0

    filled = 0
    if mode in ("tag", "claim"):
        for i, m in enumerate(meta):
            if not empty[i]:
                continue
            p = tg["pred"].get(m.get("id"))
            if not p:
                continue
            for j, a in enumerate(SHARED):
                if rel.get(a, 0.0) < min_rho:
                    continue
                A[i, j] = p[a] / 4.0
                M[i, j] = 1.0
            filled += 1

    t = np.array([_frac(m.get("date")) for m in meta], float)
    return (A[keep], M[keep], y[keep], t[keep], list(SHARED),
            {"n": int(keep.sum()), "filled": filled,
             "empty_kept": int((empty & keep).sum()),
             "counting": _tally([m.get("counting") for m, k in zip(meta, keep) if k])})


def _frac(s) -> float:
    if not s:
        return np.nan
    try:
        y_, m_, d_ = str(s)[:10].split("-")
        return int(y_) + (int(m_) - 1) / 12 + (int(d_) - 1) / 365.25
    except Exception:
        return np.nan


def _tally(v) -> dict:
    out = {}
    for x in v:
        out[str(x)] = out.get(str(x), 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))
