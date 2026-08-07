"""상충의 반대편을 쓴다 --- 팝업을 대상으로 고정하고 나머지 셋을 출처로 최적화한다.

노트 38이 상충을 밝혔다. 한 도메인의 인자 공간 자기 상관을 올리면 그 도메인은
대상으로서 좋아지고($r=+$0.966) 출처로서 나빠진다($r=-$0.870).

제품 쪽에서는 이 상충이 문제가 아니라 **기회**다. 팝업은 대상으로만 쓴다 ---
다른 도메인에서 배워 팝업을 예측하는 것이 목적이고, 팝업으로 남을 가르칠 일이
없다. 그러니 아이돌·게임·도서는 자기 라벨을 잘 맞히는 배선이 아니라
**팝업으로 잘 옮겨지는 배선**을 골라야 한다.

**여기서 선택 편향이 훨씬 위험해진다.** 노트 38의 목적함수는 도메인 자기
라벨이었고 팝업 라벨과 무관했다. 이번 목적함수는 팝업 전이 성적이므로 팝업
라벨을 직접 본다. 후보를 많이 보고 최댓값을 고르면 팝업 라벨에 과적합된다.

그래서 팝업을 둘로 나눈다.

    탐색용  배선을 고를 때만 쓴다.
    확인용  고른 뒤 한 번만 쓴다. 여기 성적이 진짜 값이다.

분할은 개장 연도로 층화한다 --- 시장이 커져 왔으므로 연도가 한쪽에 몰리면
난이도가 달라진다(노트 11).

사용: python3 -m state.source_search
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from .factor_search import CAND, COLS, build
from .procrustes import align, factor_space, lam_by_overlap
from .tri_domain import KO, load_all

OUT = Path("data/state/source_search.json")
SEED = 20260729
# 팝업을 뺀 나머지 전부. 다섯째 도메인이 들어오면 자동으로 늘어난다(노트 40).
SOURCES = ("아이돌", "게임", "도서", "펀딩")


def split_popup(t, frac=0.5):
    """개장 연도로 층화해 팝업을 반으로 나눈다."""
    rng = np.random.default_rng(SEED)
    idx = np.arange(len(t))
    a, b = [], []
    for yr in np.unique(t[np.isfinite(t)]):
        g = idx[t == yr]
        g = rng.permutation(g)
        cut = int(round(len(g) * frac))
        a += list(g[:cut]); b += list(g[cut:])
    nan = idx[~np.isfinite(t)]
    a += list(nan[::2]); b += list(nan[1::2])
    return np.array(sorted(a)), np.array(sorted(b))


def transfer_gain(doms, part, ref="팝업"):
    """세 출처에서 팝업의 지정 부분집합으로 옮긴 평균 MAE 이득."""
    lam = lam_by_overlap(doms)
    F = {k: factor_space(*v, lam=lam.get(k, 0.75)) for k, v in doms.items()}
    G = align(F, ref)
    St, yt = G[ref]["S"], G[ref]["y"]
    if part is not None:
        St, yt = St[part], yt[part]
    base = np.abs(np.median(yt) - yt).mean()
    out = {}
    for s in SOURCES:
        if s not in G:
            continue
        m = Ridge(alpha=1.0).fit(G[s]["S"], G[s]["y"])
        out[s] = float(base - np.abs(m.predict(St) - yt).mean())
    return out


def search(base, part, rounds=3):
    """세 출처의 배선을 좌표 상승으로 고른다. 목적은 팝업 탐색용 이득 평균."""
    cur = base
    best = float(np.mean(list(transfer_gain(cur, part).values())))
    trace = [("현행", best)]
    for _ in range(rounds):
        moved = False
        for dom in SOURCES:
            if dom not in cur or dom not in CAND:
                continue
            pool = COLS[dom]()
            for slot, opts in CAND[dom].items():
                for name in opts:
                    if name is not None and name not in pool:
                        continue
                    trial = dict(cur)
                    trial[dom] = build(dom, cur, {slot: name}, pool)
                    g = float(np.mean(list(transfer_gain(trial, part).values())))
                    if g > best + 1e-5:
                        best, cur, moved = g, trial, True
                        trace.append((f"{dom} {KO[slot]} ← {name}", g))
        if not moved:
            break
    return cur, best, trace


def run() -> dict:
    base = load_all()
    tpop = base["팝업"][3]
    a, b = split_popup(tpop)
    print(f"팝업 {len(tpop)}건 → 탐색용 {len(a)} · 확인용 {len(b)}")

    g0a = transfer_gain(base, a)
    g0b = transfer_gain(base, b)
    print(f"\n현행   탐색용 {np.mean(list(g0a.values())):+.4f}   "
          f"확인용 {np.mean(list(g0b.values())):+.4f}")

    win, best, trace = search(base, a)
    g1a = transfer_gain(win, a)
    g1b = transfer_gain(win, b)
    print(f"승자   탐색용 {np.mean(list(g1a.values())):+.4f}   "
          f"확인용 {np.mean(list(g1b.values())):+.4f}")
    print(f"선택 편향(탐색 증가 − 확인 증가) "
          f"{(np.mean(list(g1a.values())) - np.mean(list(g0a.values()))) - (np.mean(list(g1b.values())) - np.mean(list(g0b.values()))):+.4f}")

    print("\n=== 채택 경로 ===")
    for name, v in trace[1:]:
        print(f"  {name:<28}{v:+.4f}")
    if len(trace) == 1:
        print("  변화 없음")

    print(f"\n=== 출처별 팝업 이득 ===")
    print(f"  {'출처':<7}{'현행 탐색':>10}{'승자 탐색':>10}{'현행 확인':>10}{'승자 확인':>10}")
    for s in g0a:
        print(f"  {s:<7}{g0a[s]:>+10.4f}{g1a[s]:>+10.4f}{g0b[s]:>+10.4f}{g1b[s]:>+10.4f}")

    out = {"n": {"search": len(a), "confirm": len(b)},
           "base": {"search": g0a, "confirm": g0b},
           "best": {"search": g1a, "confirm": g1b},
           "trace": [(n, round(v, 5)) for n, v in trace]}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
