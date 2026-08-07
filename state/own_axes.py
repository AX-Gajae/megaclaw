"""대응물이 없는 축도 실을 수 있다 --- 도메인 고유 축을 늘린다.

노트 33이 확정하고 노트 35가 정화된 상태에서 재확인했다. 전이 상관은 대상
도메인의 자기 상관과 같다(설명 $+$0.983). 그러므로 남은 지렛대는 하나뿐이다 ---
각 도메인이 자기 라벨을 더 잘 설명하게 만드는 것.

그런데 지금까지 축을 다섯 개로 묶어 두었다. 도메인 간 대응물이 있어야 한다고
보았기 때문이다. 그 제약은 **공통 축에만 필요하다.**

    공통 축   프로크루스테스 정렬에 쓰인다. 도메인 간 같은 물리량이어야 한다.
              현재 타깃 폭과 굿즈 규모 둘뿐이다.
    고유 축   정렬에 쓰이지 않는다. 인자 공간을 만드는 데만 기여하고 λ로 축소된다.
              **도메인마다 개수도 종류도 달라도 된다.**

즉 대응물이 없다는 이유로 버린 정보를 고유 축으로는 실을 수 있다. 팝업이 특히
아깝다 --- 사람이 기획서를 읽고 열 개 속성을 매겼는데 다섯 개만 쓰고 있다.

**누출을 먼저 거른다.** 라벨보다 나중에 쌓이는 값은 후보에서 뺀다.

    도서 리뷰 수·별점   판매지수와 함께 판매의 함수다. 제외.
    게임 DLC 수         노트 21에서 이미 확인된 누출. 제외.

사용: python3 -m state.own_axes
"""
from __future__ import annotations

import glob
import json
from itertools import permutations
from pathlib import Path

import numpy as np

from .procrustes import align, cross, factor_space, lam_by_overlap
from .rewire_test import scale01, self_corr
from .tri_domain import ALL5, load_all

OUT = Path("data/state/own_axes.json")

# 팝업에서 축으로 안 쓰고 있는 사람 태깅 속성 다섯.
POPUP_EXTRA = ["experience_density", "photo_zones", "collab_strength",
               "ip_awareness", "season_fit"]
KO_EXTRA = {"experience_density": "체험 밀도", "photo_zones": "포토존",
            "collab_strength": "컬래버 강도", "ip_awareness": "IP 인지도",
            "season_fit": "계절 적합", "survival": "서바이벌 출신",
            "pre_debut": "사전 화제", "girl": "걸그룹", "age_rating": "연령 등급",
            "ram_gb": "최소 RAM", "n_category": "기능 수", "price": "가격",
            "pages": "쪽수", "weight": "무게"}


def popup_extra():
    """팝업 t1o_ 속성 중 축에 안 쓴 다섯. 마스크도 그대로 가져온다."""
    from .slots import load_popup
    d = np.load("data/state/popup_v2.npz", allow_pickle=True)
    cols = [str(c) for c in d["names"]]
    X = d["X"]
    # load_popup 과 같은 필터를 다시 적용해 행을 맞춘다.
    Xs, yp, w, Ap, Mp, gp, tp, _ = load_popup()
    keep = _popup_keep(d, cols)
    out = []
    for a in POPUP_EXTRA:
        ci, mi = cols.index(f"t1o_{a}"), cols.index(f"t1o_{a}_mask")
        out.append((a, X[keep][:, ci] / 4.0, X[keep][:, mi]))
    assert len(out[0][1]) == len(yp), f"행 불일치 {len(out[0][1])} vs {len(yp)}"
    return out


def _popup_keep(d, cols):
    meta = json.loads(Path("data/state/popup_v2_meta.json").read_text())
    X, y = d["X"], d["y_perday"]
    gi = {g: (cols.index(f"trust_{g}") if f"trust_{g}" in cols else None)
          for g in ("A", "B")}
    keep = np.zeros(len(y), bool)
    for g in ("A", "B"):
        if gi[g] is not None:
            keep |= X[:, gi[g]] > 0.5
    keep &= np.isfinite(y)
    keep &= np.array([bool(m.get("scope_usable")) for m in meta])
    keep &= np.array([m.get("counting") in ("entry", "participation") for m in meta])
    return keep


def idol_extra():
    """데뷔 전에 관측 가능한 것만. 서바이벌 출신·사전 화제·성별."""
    ax = json.loads(Path("data/state/idol_axes.json").read_text())
    recs = {}
    for f in glob.glob("data/idol_records/*.json"):
        r = json.loads(Path(f).read_text())
        recs[r["record_id"]] = r
    ids = list(ax.keys())   # tri_domain 과 같은 행 집합이어야 한다
    out = []
    for name, fn in (("survival", lambda r: 1.0 if r.get("survival_show") else 0.0),
                     ("pre_debut", lambda r: 1.0 if r.get("pre_debut_signals") else 0.0),
                     ("girl", lambda r: 1.0 if r.get("gender") == "girl" else 0.0)):
        v = np.array([fn(recs.get(k, {})) for k in ids])
        out.append((name, v, np.ones(len(v))))
    return out


def game_extra():
    """출시 전 스토어에서 볼 수 있는 것만. DLC 수는 노트 21의 누출이라 제외."""
    ax = json.loads(Path("data/state/game_axes.json").read_text())
    rec = json.loads(Path("data/state/game_records.json").read_text())
    fr = json.loads(Path("data/state/game_friction.json").read_text())
    ids = list(ax.keys())   # tri_domain 과 같은 행 집합이어야 한다
    out = []
    v = np.array([float(scale01(np.log10(max((rec.get(k) or {}).get("price_krw") or 1, 1)),
                                0.0, 5.0)) for k in ids])
    m = np.array([1.0 if ((rec.get(k) or {}).get("price_krw")
                          or (rec.get(k) or {}).get("is_free")) else 0.0 for k in ids])
    out.append(("price", v, m))
    v = np.array([float(scale01((fr.get(k) or {}).get("required_age") or 0, 0.0, 18.0))
                  for k in ids])
    out.append(("age_rating", v, np.array([1.0 if fr.get(k) else 0.0 for k in ids])))
    v = np.array([float(scale01(np.log2(max((fr.get(k) or {}).get("ram_gb") or 1, 1)),
                                0.0, 5.0)) for k in ids])
    out.append(("ram_gb", v, np.array([1.0 if (fr.get(k) or {}).get("ram_gb") else 0.0
                                       for k in ids])))
    v = np.array([float(scale01((rec.get(k) or {}).get("n_category") or 0, 0.0, 20.0))
                  for k in ids])
    out.append(("n_category", v, np.ones(len(v))))
    return out


def book_extra():
    """리뷰 수·별점은 판매의 함수라 제외. 쪽수와 무게만."""
    ax = json.loads(Path("data/state/book_axes.json").read_text())
    rec = json.loads(Path("data/state/book_records.json").read_text())
    ids = list(ax.keys())
    out = []
    v = np.array([float(scale01(np.log2(max((rec.get(k) or {}).get("pages") or 8, 8)),
                                5.0, 10.0)) for k in ids])
    out.append(("pages", v, np.array([1.0 if (rec.get(k) or {}).get("pages") else 0.0
                                      for k in ids])))
    v = np.array([float(scale01((rec.get(k) or {}).get("weight_g") or 0, 100.0, 900.0))
                  for k in ids])
    out.append(("weight", v, np.array([1.0 if (rec.get(k) or {}).get("weight_g") else 0.0
                                       for k in ids])))
    return out


def funding_extra():
    """펀딩 고유 축. 리워드 구성에서 나오는 것들 --- 라벨(후원자 수)보다
    앞서 정해지므로 누출이 아니다."""
    ax = json.loads(Path("data/state/funding_axes.json").read_text())
    rec = json.loads(Path("data/state/funding_records.json").read_text())
    ids = list(ax.keys())
    f = lambda k: rec.get(k) or {}
    out = []
    out.append(("max_price", [scale01(np.log10(max(f(k).get("max_price") or 1000, 1000)),
                                      4.0, 6.5) for k in ids],
                [1.0 if f(k).get("max_price") else 0.0 for k in ids]))
    out.append(("delivery_ratio", [(f(k).get("n_delivery") or 0) /
                                   max(f(k).get("n_reward") or 1, 1) for k in ids],
                [1.0 if f(k).get("n_reward") else 0.0 for k in ids]))
    out.append(("adult", [1.0 if f(k).get("adult_only") else 0.0 for k in ids],
                [1.0] * len(ids)))
    return out


def webtoon_extra():
    """웹툰 고유 축. 연령 등급과 태그 수는 타깃 폭 후보였다가 밀린 것들이다."""
    ax = json.loads(Path("data/state/webtoon_axes.json").read_text())
    rec = json.loads(Path("data/state/webtoon_records.json").read_text())
    ids = list(ax.keys())
    w = lambda k: rec.get(k) or {}
    out = []
    out.append(("age", [(w(k).get("age_rank") or 0) / 3.0 for k in ids],
                [1.0 if w(k).get("age_rank") is not None else 0.0 for k in ids]))
    out.append(("n_tag", [scale01(w(k).get("n_tag") or 0, 3, 14) for k in ids],
                [1.0 if w(k).get("n_tag") else 0.0 for k in ids]))
    out.append(("n_episode", [scale01(np.log2(max(w(k).get("n_episode") or 1, 1)), 0, 9)
                              for k in ids],
                [1.0 if w(k).get("n_episode") else 0.0 for k in ids]))
    out.append(("n_day", [scale01(w(k).get("n_day") or 1, 1, 3) for k in ids],
                [1.0 if w(k).get("n_day") else 0.0 for k in ids]))
    return out


EXTRA = {"팝업": popup_extra, "아이돌": idol_extra, "게임": game_extra,
         "도서": book_extra, "펀딩": funding_extra, "웹툰": webtoon_extra}


def extend(doms, which):
    """지정한 도메인에 고유 축을 덧붙인다. 축 이름 목록도 함께 낸다."""
    out, names = {}, {}
    for k, (A, M, y, t) in doms.items():
        names[k] = list(ALL5)
        if k not in which:
            out[k] = (A, M, y, t)
            continue
        cols = EXTRA[k]()
        A2 = np.column_stack([A] + [c[1] for c in cols])
        M2 = np.column_stack([M] + [c[2] for c in cols])
        names[k] = list(ALL5) + [c[0] for c in cols]
        out[k] = (A2, M2, y, t)
    return out, names


def evaluate(doms, names, ref="팝업", perm=1500):
    lam = lam_by_overlap(doms, names=names)
    F = {k: factor_space(*v, lam=lam.get(k, 0.75), names=names[k])
         for k, v in doms.items()}
    G = align(F, ref)
    sc = {k: self_corr(*v) for k, v in doms.items()}
    cells = {}
    for s, t in permutations(G, 2):
        o, p = cross(G[s]["S"], G[s]["y"], G[t]["S"], G[t]["y"], perm=perm)
        cells[f"{s}→{t}"] = {"obs": o, "p": p}
    return {"self": sc, "cells": cells,
            "sig": sum(1 for c in cells.values() if c["p"] < 0.05),
            "gain": float(np.mean([-c["obs"] for c in cells.values()])),
            "n": {k: F[k]["n"] for k in F}, "lam": lam}


def run() -> dict:
    base = load_all()
    combos = [(), ("팝업",), ("아이돌",), ("게임",), ("도서",),
              ("팝업", "아이돌", "게임", "도서")]
    out = {}
    print(f"{'고유 축 추가':<20}{'팝업':>7}{'아이돌':>7}{'게임':>7}{'도서':>7}"
          f"{'유의':>7}{'평균이득':>10}")
    for c in combos:
        d, nm = extend(base, set(c))
        r = evaluate(d, nm)
        key = "없음(기준)" if not c else "+".join(c)
        out[key] = {k: v for k, v in r.items() if k != "lam"}
        s = r["self"]
        print(f"{key:<20}{s['팝업']:>7.3f}{s['아이돌']:>7.3f}{s['게임']:>7.3f}"
              f"{s['도서']:>7.3f}{r['sig']:>5}/12{r['gain']:>+10.4f}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
