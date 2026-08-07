"""도메인마다 역할별 배선을 두 벌 준다 --- 가르칠 때와 배울 때 다르게 잰다.

노트 38이 상충을 밝혔다. 한 도메인의 인자 공간 자기 상관을 올리면 대상으로서
좋아지고($r=+$0.966) 출처로서 나빠진다($r=-$0.870). 노트 39는 그 상충을
피하는 대신 **이용한다** --- 도메인마다 축을 한 벌이 아니라 두 벌 만든다.

    출처용  이 도메인이 남을 가르칠 때 쓴다. 팝업 전이 성적으로 골랐다.
    대상용  이 도메인을 예측할 때 쓴다. 자기 상관으로 골랐다(노트 38).

셀 (출처 s → 대상 t)마다 s는 출처용, t는 대상용을 쓴다. 나머지 둘은 λ 유도에만
들어가므로 기본 배선을 쓴다.

**전역 단일 배선으로는 안 된다.** 출처용 배선을 네 도메인 전부에 일괄 적용하면
유의 10/12에 이득 $+$0.0513으로 현행($+$0.0547)보다 나쁘다. 역할별로 나눠야
11/12에 $+$0.0594가 된다. 상충이 실재하므로 한 배선으로 두 역할을 다 잘할 수
없다는 뜻이다.

가장 뚜렷한 사례가 아이돌 입장 허들이다. 노트 38이 자기 상관을 근거로 켰고
(앨범 정가, 대상 전이 $+$0.657$\to+$0.690), 노트 39가 출처 전이를 근거로 껐다
(팝업 이득 $+$0.0600$\to+$0.0694). **같은 축이 역할에 따라 반대 방향이다.**

사용: python3 -m state.dual
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np

from .factor_search import COLS, build
from .procrustes import align, cross, factor_space, lam_by_overlap
from .tri_domain import load_all

OUT = Path("data/state/dual.json")

# ── 출처용 배선 ──────────────────────────────────────────────────────────
# 팝업을 대상으로 고정하고 좌표 상승으로 골랐다. 팝업을 탐색용 38건과 확인용
# 37건으로 나눠 선택 편향을 쟀다(+0.0038, 확인용 순증 +0.0025).
SRC_WIRING = {
    "아이돌": {"entry_friction": None,          # 노트 38이 켠 것을 출처용으로는 끈다
             "target_breadth": "서바이벌 출신"},  # 이미 대중에 닿아 있는 정도
    "도서": {"target_breadth": "판형 높이만"},
}

# ── 대상용 배선 ──────────────────────────────────────────────────────────
# 인자 공간 자기 상관으로 골랐다(노트 38). 아이돌 것은 이미 ingest 에 반영돼
# 기본 배선이 됐고, 게임 것은 그때 상충 때문에 보류했다가 여기서 대상용으로만 쓴다.
TGT_WIRING = {
    "게임": {"target_breadth": "언어 수", "goods_scale": "기능 수"},
}


def wire(base, spec):
    d = dict(base)
    for dom, w in spec.items():
        d[dom] = build(dom, d, w, COLS[dom]())
    return d


def transfer_pair(base=None, src_lam=None, perm=4000):
    """다섯 도메인 · 쌍별 정렬 · 역할별 λ 로 스무 셀을 잰다(노트 40·41).

    이것이 현재의 정본 파이프라인이다.

      · 정렬은 쌍마다 둘이 함께 관측한 공통 축으로 한다(노트 40).
      · λ 는 출처·대상 모두 겹침 유도값이다. 노트 41이 출처 λ=1.5로 키웠다가
        노트 42에서 철회했다 --- 전이 상관이 λ에 반응하지 않았다.
    """
    from .procrustes import SRC_LAM, align_pair
    base = base or load_all()
    sl = src_lam if src_lam is not None else SRC_LAM
    lam0 = lam_by_overlap(base)
    Fs = {k: factor_space(*v, lam=(lam0.get(k, 0.75) if sl is None else sl))
          for k, v in base.items()}
    Ft = {k: factor_space(*v, lam=lam0.get(k, 0.75)) for k, v in base.items()}
    cells = {}
    for s, t in permutations(base, 2):
        r = align_pair(Fs[s], Ft[t])
        if r is None:
            continue
        o, p = cross(r[0], Fs[s]["y"], Ft[t]["S"], Ft[t]["y"], perm=perm)
        cells[f"{s}→{t}"] = {"obs": o, "p": p, "shared": len(r[1])}
    return {"cells": cells,
            "sig": sum(1 for c in cells.values() if c["p"] < 0.05),
            "gain": float(np.mean([-c["obs"] for c in cells.values()]))}


def transfer(base=None, use_tgt=False, perm=4000, ref="팝업"):
    """셀마다 역할에 맞는 배선으로 인자 공간을 새로 만든다.

    use_tgt --- 대상용 배선까지 쓸지. 유의 기준으로는 출처용만 쓰는 쪽이 낫다
    (11/12 대 10/12). 이득 기준으로는 반대다(+0.0594 대 +0.0605)."""
    base = base or load_all()
    S = wire(base, SRC_WIRING)
    T = wire(base, TGT_WIRING) if use_tgt else base
    cells = {}
    for s, t in permutations(base, 2):
        d = {k: (S[k] if k == s else T[k] if k == t else base[k]) for k in base}
        lam = lam_by_overlap(d)
        F = {k: factor_space(*v, lam=lam.get(k, 0.75)) for k, v in d.items()}
        G = align(F, ref)
        o, p = cross(G[s]["S"], G[s]["y"], G[t]["S"], G[t]["y"], perm=perm)
        cells[f"{s}→{t}"] = {"obs": o, "p": p}
    return {"cells": cells,
            "sig": sum(1 for c in cells.values() if c["p"] < 0.05),
            "gain": float(np.mean([-c["obs"] for c in cells.values()]))}


def run() -> dict:
    base = load_all()
    out = {}
    for label, kw in (("단일 배선(현행)", None), ("이중 배선 · 출처만", False),
                      ("이중 배선 · 출처+대상", True)):
        if kw is None:
            S = T = base
            cells = {}
            for s, t in permutations(base, 2):
                lam = lam_by_overlap(base)
                F = {k: factor_space(*v, lam=lam.get(k, 0.75)) for k, v in base.items()}
                G = align(F, "팝업")
                o, p = cross(G[s]["S"], G[s]["y"], G[t]["S"], G[t]["y"], perm=4000)
                cells[f"{s}→{t}"] = {"obs": o, "p": p}
            r = {"cells": cells,
                 "sig": sum(1 for c in cells.values() if c["p"] < 0.05),
                 "gain": float(np.mean([-c["obs"] for c in cells.values()]))}
        else:
            r = transfer(base, use_tgt=kw)
        out[label] = r
        print(f"{label:<22}유의 {r['sig']}/12   평균이득 {r['gain']:+.4f}")

    print("\n=== 셀별 (단일 → 이중 출처만) ===")
    a, b = out["단일 배선(현행)"]["cells"], out["이중 배선 · 출처만"]["cells"]
    for k in a:
        f = "  ←개선" if b[k]["p"] < 0.05 <= a[k]["p"] else (
            "  ←악화" if a[k]["p"] < 0.05 <= b[k]["p"] else "")
        print(f"  {k:<14}p {a[k]['p']:.4f} → {b[k]['p']:.4f}   "
              f"Δ {a[k]['obs']:+.4f} → {b[k]['obs']:+.4f}{f}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
