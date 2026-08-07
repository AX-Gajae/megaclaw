"""검정으로 고른 배선을 실제로 갈아 끼우고 전이까지 확인한다.

`state.wiring_search`가 도메인마다 각 축 슬롯에 무엇이 가장 강한 신호인지 쟀다.
그 결과 두 가지가 드러났다.

  게임  입장 허들(가격 r=+0.351)과 매장 노출도(퍼블리셔 사전작 r=+0.280)를
        **내가 꺼 놓았다**. 노트 16·25는 가격이 허들이 아니라 규모 신호라서,
        노트 28은 퍼블리셔 이력이 정렬 기하를 흔들어서 껐다. 둘 다 세 도메인
        시절의 판단이고, 그때는 '자기 상관이 전이를 지배한다'(노트 33)는 렌즈가
        없었다. 자기 상관을 올리는 축을 끄는 것은 이제 손해일 수 있다.

  도서  굿즈 규모에 넣은 쪽수가 r=-0.015로 무효인데, 같은 유형의 **양장 여부**가
        r=+0.296이다.

이 모듈은 축 행렬을 직접 갈아 끼워 변형마다 두 값을 잰다.

  · 도메인별 자기 상관 --- 노트 33이 전이 상한이라고 밝힌 값
  · 열두 방향 전이     --- 유의 개수와 평균 이득

원본 축 JSON은 건드리지 않는다. 채택이 정해진 뒤에 ingest 쪽을 고친다.

사용: python3 -m state.rewire_test
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

from .procrustes import align, cross, factor_space, lam_by_overlap
from .tri_domain import ALL5, detrend, load_all, z

SEED = 20260728
IX = {a: i for i, a in enumerate(ALL5)}


def scale01(v, lo, hi):
    return np.clip((np.asarray(v, float) - lo) / (hi - lo), 0.0, 1.0)


def _game_order():
    """게임 축 JSON의 레코드 순서 --- 열 교체는 이 순서에 맞춰야 한다."""
    return list(json.loads(Path("data/state/game_axes.json").read_text()).keys())


def _book_order():
    return list(json.loads(Path("data/state/book_axes.json").read_text()).keys())


def game_price_col():
    """게임 가격 → 입장 허들. 무료는 0원으로 관측된 값이다(결측 아님)."""
    rec = json.loads(Path("data/state/game_records.json").read_text())
    v, m = [], []
    for k in _game_order():
        r = rec.get(k) or {}
        if r.get("is_free"):
            v.append(0.0); m.append(1.0)
        elif r.get("price_krw"):
            v.append(float(scale01(np.log10(max(r["price_krw"], 500)), 3.0, 5.0)))
            m.append(1.0)
        else:
            v.append(0.0); m.append(0.0)
    return np.array(v), np.array(m)


def game_venue_col():
    """게임 퍼블리셔 사전작 --- 값은 이미 축 JSON에 기록돼 있고 마스크만 0이다."""
    ax = json.loads(Path("data/state/game_axes.json").read_text())
    v = np.array([ax[k]["axes"]["venue_prominence"] for k in _game_order()])
    return v, np.where(v > 0, 1.0, 0.0)


def book_hardcover_col():
    """도서 양장 여부 → 굿즈 규모. 쪽수(r=-0.015)를 대체한다."""
    rec = json.loads(Path("data/state/book_records.json").read_text())
    v = np.array([1.0 if "Hardcover" in ((rec.get(k) or {}).get("book_format") or "")
                  else 0.0 for k in _book_order()])
    return v, np.ones(len(v))


def game_breadth_lang():
    """게임 타깃 폭을 **지원 언어만**으로. 장르 수·플랫폼 수는 부호가 반대다.

    현재 배선은 셋을 모두 양의 방향으로 합친다. 그런데 라벨과의 상관은
    지원 언어 +0.176, 장르 수 -0.153, 플랫폼 수 -0.141 --- 뒤 둘이 앞 하나를
    상쇄한다. 같은 슬롯 안에서 구성만 바꾸므로 축 집합은 그대로다."""
    rec = json.loads(Path("data/state/game_records.json").read_text())
    v = np.array([float(scale01((rec.get(k) or {}).get("n_lang") or 1, 1.0, 29.0))
                  for k in _game_order()])
    return v, np.ones(len(v))


def book_breadth_trim():
    """도서 타깃 폭을 **판형만**으로. 장르 수(r=-0.079)를 뺀다."""
    rec = json.loads(Path("data/state/book_records.json").read_text())
    v, m = [], []
    for k in _book_order():
        r = rec.get(k) or {}
        h, w = r.get("height_mm"), r.get("width_mm")
        if not h and not w:
            v.append(0.0); m.append(0.0); continue
        parts, wt = [], []
        if h:
            parts.append(1.0 - float(scale01(h, 180.0, 280.0))); wt.append(1.0)
        if w:
            parts.append(1.0 - float(scale01(w, 120.0, 200.0))); wt.append(0.7)
        v.append(float(np.average(parts, weights=wt))); m.append(1.0)
    return np.array(v), np.array(m)


def apply(doms, spec):
    """축 행렬을 복사해 지정한 열만 교체한다."""
    out = {k: (A.copy(), M.copy(), y, t) for k, (A, M, y, t) in doms.items()}
    for dom, axis, fn in spec:
        if dom not in out:
            continue
        A, M, y, t = out[dom]
        v, m = fn()
        j = IX[axis]
        A[:, j], M[:, j] = v, m
    return out


def self_corr(A, M, y, t):
    """도메인이 자기 관측 축으로 자기 라벨을 얼마나 맞히나(5폴드 교차검증).

    노트 33이 전이 상한이라고 밝힌 값이며 노트 34가 배선으로 바뀜을 보였다."""
    cols = [j for j in range(A.shape[1]) if M[:, j].mean() >= 0.6]
    if not cols:
        return float("nan")
    keep = M[:, cols].all(1)
    if keep.sum() < 25:
        return float("nan")
    Z = np.column_stack([z(detrend(A[keep][:, j], t[keep])) for j in cols])
    yy = z(detrend(y[keep], t[keep]))
    pr = np.zeros(len(yy))
    for tr, te in KFold(5, shuffle=True, random_state=SEED).split(Z):
        pr[te] = Ridge(alpha=1.0).fit(Z[tr], yy[tr]).predict(Z[te])
    return float(np.corrcoef(pr, yy)[0, 1])


def evaluate(doms, ref="팝업", perm=1500):
    lam = lam_by_overlap(doms)
    F = {k: factor_space(*v, lam=lam.get(k, 0.75)) for k, v in doms.items()}
    G = align(F, ref)
    sc = {k: self_corr(*v) for k, v in doms.items()}
    cells = {}
    for s, t in permutations(G, 2):
        o, p = cross(G[s]["S"], G[s]["y"], G[t]["S"], G[t]["y"], perm=perm)
        cells[f"{s}→{t}"] = {"obs": o, "p": p}
    sig = sum(1 for c in cells.values() if c["p"] < 0.05)
    gain = float(np.mean([-c["obs"] for c in cells.values()]))
    return {"self": sc, "cells": cells, "sig": sig, "gain": gain, "lam": lam}


VARIANTS = {
    "기준(현재)": [],
    "게임 +입장허들(가격)": [("게임", "entry_friction", game_price_col)],
    "게임 +매장노출도(퍼블리셔)": [("게임", "venue_prominence", game_venue_col)],
    "게임 +둘 다": [("게임", "entry_friction", game_price_col),
                 ("게임", "venue_prominence", game_venue_col)],
    "도서 굿즈=양장": [("도서", "goods_scale", book_hardcover_col)],
    "게임 폭=언어만": [("게임", "target_breadth", game_breadth_lang)],
    "도서 폭=판형만": [("도서", "target_breadth", book_breadth_trim)],
    "도서 굿즈=양장 + 게임 폭=언어": [("도서", "goods_scale", book_hardcover_col),
                            ("게임", "target_breadth", game_breadth_lang)],
    "슬롯내 교체 전부": [("도서", "goods_scale", book_hardcover_col),
                  ("게임", "target_breadth", game_breadth_lang),
                  ("도서", "target_breadth", book_breadth_trim)],
    "슬롯내 + 축 켜기": [("도서", "goods_scale", book_hardcover_col),
                   ("게임", "target_breadth", game_breadth_lang),
                   ("도서", "target_breadth", book_breadth_trim),
                   ("게임", "entry_friction", game_price_col),
                   ("게임", "venue_prominence", game_venue_col)],
}


def run() -> dict:
    base = load_all()
    out = {}
    print(f"{'변형':<24}{'팝업':>7}{'아이돌':>7}{'게임':>7}{'도서':>7}"
          f"{'유의':>7}{'평균이득':>10}")
    for name, spec in VARIANTS.items():
        r = evaluate(apply(base, spec))
        out[name] = {k: v for k, v in r.items() if k != "lam"}
        s = r["self"]
        print(f"{name:<24}{s['팝업']:>7.3f}{s['아이돌']:>7.3f}{s['게임']:>7.3f}"
              f"{s['도서']:>7.3f}{r['sig']:>5}/12{r['gain']:>+10.4f}")
    print("\n=== 셀별 상세 ===")
    best = max(out, key=lambda k: (out[k]["sig"], out[k]["gain"]))
    print(f"(기준 → {best})")
    b, a = out["기준(현재)"]["cells"], out[best]["cells"]
    for k in b:
        f = "  ←개선" if a[k]["p"] < 0.05 <= b[k]["p"] else (
            "  ←악화" if b[k]["p"] < 0.05 <= a[k]["p"] else "")
        print(f"  {k:<14}p {b[k]['p']:.4f} → {a[k]['p']:.4f}   "
              f"Δ {b[k]['obs']:+.4f} → {a[k]['obs']:+.4f}{f}")
    Path("data/state/rewire_test.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
