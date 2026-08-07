"""공통 축을 늘리면 두 번째 상한이 올라가는가 --- 노트 36 가설의 직접 검정.

노트 36의 결론은 이랬다. 전이는 두 상한 중 낮은 쪽에 묶인다.

    첫째  대상 도메인의 자기 상관
    둘째  정렬이 전달할 수 있는 몫

고유 축을 늘려도 둘째가 막아 소용이 없었다. 둘째를 올리려면 **공통 축**을
늘려야 한다. 공통 축이 c개, 성분이 k개면 프로크루스테스는 c×k 적재를 맞춘다.
c < k 면 회전이 과소결정되므로 k ≤ c 여야 하고, 지금 c=2라 k=2에 묶여 있다.

**왜 c=2였나.** 다섯 축 중 셋이 어느 도메인에선가 문턱(60%) 아래였다.

    매장 노출도  팝업 100%  아이돌 90%  게임 **0%**  도서 100%
    입장 허들    팝업 100%  아이돌 **0%**  게임 **0%**  도서 100%
    미디어 투입  팝업 100%  아이돌 96%  게임 38%  도서 **0%**

게임의 0%는 관측이 없어서가 아니라 **내가 껐기 때문**이다(노트 16·25·28).
아이돌 입장 허들도 마찬가지로 채우지 않았을 뿐, 앨범 정가가 85% 있다.

    매장 노출도  게임 퍼블리셔 사전작 --- 값은 이미 있고 65%가 0보다 크다
    입장 허들    게임 가격(100%), 아이돌 앨범 정가(85%)

**노트 28과 다른 실험이다.** 그때는 공통 축이 둘인 채로 게임 매장 노출도를
*고유 축*으로 켰고 정렬 기하가 흔들려 되돌렸다. 여기서는 그 축을 *공통 축*으로
쓴다 --- 정렬에 참여하는 축이 되므로 역할이 정반대다.

사용: python3 -m state.common_axes
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np

from .procrustes import align, cross, factor_space, lam_by_overlap
from .rewire_test import IX, scale01, self_corr
from .tri_domain import ALL5, load_all

OUT = Path("data/state/common_axes.json")


def _order(p):
    return list(json.loads(Path(p).read_text()).keys())


def game_venue():
    """게임 퍼블리셔 사전작. 값은 축 JSON에 있고 마스크만 0으로 꺼져 있다.

    **0은 결측이 아니라 관측된 값이다.** 처음에 v>0 을 마스크로 썼더니 게임
    표본이 482에서 313으로 35% 줄었다. 그런데 0은 '이 퍼블리셔의 표본 내 사전
    출시작이 0건'이라는 정상값이다 --- 신인 퍼블리셔가 그만큼 많다는 뜻이지
    관측이 없다는 뜻이 아니다. 노트 35에서 도서 판형에 대해 배운 것을 게임에서
    반복할 뻔했다. 퍼블리셔 이름이 있는지로 판정한다."""
    ax = json.loads(Path("data/state/game_axes.json").read_text())
    rec = json.loads(Path("data/state/game_records.json").read_text())
    ids = _order("data/state/game_axes.json")
    v = np.array([ax[k]["axes"]["venue_prominence"] for k in ids])
    m = np.array([1.0 if ((rec.get(k) or {}).get("publishers")
                          or (rec.get(k) or {}).get("developers")) else 0.0 for k in ids])
    return v, m


def game_price():
    """게임 가격. 무료(0원)는 관측된 값이지 결측이 아니다."""
    rec = json.loads(Path("data/state/game_records.json").read_text())
    v, m = [], []
    for k in _order("data/state/game_axes.json"):
        r = rec.get(k) or {}
        if r.get("is_free"):
            v.append(0.0); m.append(1.0)
        elif r.get("price_krw"):
            v.append(float(scale01(np.log10(max(r["price_krw"], 500)), 3.0, 5.0)))
            m.append(1.0)
        else:
            v.append(0.0); m.append(0.0)
    return np.array(v), np.array(m)


def idol_price():
    """아이돌 앨범 정가. 데뷔 시점에 공표되므로 시간 인과가 성립한다."""
    alb = json.loads(Path("data/state/idol_album_meta.json").read_text())
    v, m = [], []
    for k in _order("data/state/idol_axes.json"):
        p = (alb.get(k) or {}).get("unit_price")
        if p:
            v.append(float(scale01(np.log10(max(p, 5000)), 3.9, 4.7))); m.append(1.0)
        else:
            v.append(0.0); m.append(0.0)
    return np.array(v), np.array(m)


FILL = {
    "venue": [("게임", "venue_prominence", game_venue)],
    "friction": [("게임", "entry_friction", game_price),
                 ("아이돌", "entry_friction", idol_price)],
}


def apply(doms, keys):
    out = {k: (A.copy(), M.copy(), y, t) for k, (A, M, y, t) in doms.items()}
    for key in keys:
        for dom, axis, fn in FILL[key]:
            A, M, y, t = out[dom]
            v, m = fn()
            j = IX[axis]
            A[:, j], M[:, j] = v, m
    return out


def evaluate(doms, common, k, ref="팝업", perm=1500):
    lam = lam_by_overlap(doms, common=common)
    F = {kk: factor_space(*v, lam=lam.get(kk, 0.75), common=common, k=k)
         for kk, v in doms.items()}
    G = align(F, ref, common=common, k=k)
    cells = {}
    for s, t in permutations(G, 2):
        o, p = cross(G[s]["S"], G[s]["y"], G[t]["S"], G[t]["y"], perm=perm)
        cells[f"{s}→{t}"] = {"obs": o, "p": p}
    return {"cells": cells, "n": {kk: F[kk]["n"] for kk in F},
            "sig": sum(1 for c in cells.values() if c["p"] < 0.05),
            "gain": float(np.mean([-c["obs"] for c in cells.values()]))}


C2 = ["target_breadth", "goods_scale"]
C3 = C2 + ["venue_prominence"]
C4 = C3 + ["entry_friction"]

PLAN = [("공통 2 · K=2 (현행)", (), C2, 2),
        ("공통 3 · K=2", ("venue",), C3, 2),
        ("공통 3 · K=3", ("venue",), C3, 3),
        ("공통 4 · K=2", ("venue", "friction"), C4, 2),
        ("공통 4 · K=3", ("venue", "friction"), C4, 3),
        ("공통 4 · K=4", ("venue", "friction"), C4, 4)]


def run() -> dict:
    base = load_all()
    out = {}
    print(f"{'설정':<18}{'팝업 n':>7}{'아이돌':>7}{'게임':>7}{'도서':>7}"
          f"{'자기(팝업)':>11}{'유의':>7}{'평균이득':>10}")
    for name, keys, cm, k in PLAN:
        d = apply(base, keys)
        r = evaluate(d, cm, k)
        sc = self_corr(*d["팝업"])
        out[name] = r
        n = r["n"]
        print(f"{name:<18}{n['팝업']:>7}{n['아이돌']:>7}{n['게임']:>7}{n['도서']:>7}"
              f"{sc:>11.3f}{r['sig']:>5}/12{r['gain']:>+10.4f}")
    best = max(out, key=lambda kk: (out[kk]["sig"], out[kk]["gain"]))
    print(f"\n=== 셀별 상세 (현행 → {best}) ===")
    b, a = out["공통 2 · K=2 (현행)"]["cells"], out[best]["cells"]
    for kk in b:
        f = "  ←개선" if a[kk]["p"] < 0.05 <= b[kk]["p"] else (
            "  ←악화" if b[kk]["p"] < 0.05 <= a[kk]["p"] else "")
        print(f"  {kk:<14}p {b[kk]['p']:.4f} → {a[kk]['p']:.4f}   "
              f"Δ {b[kk]['obs']:+.4f} → {a[kk]['obs']:+.4f}{f}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
