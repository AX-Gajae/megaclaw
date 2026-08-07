"""노트 789 — **도메인을 묶을 수 있나.** 쌍별 전이로 잰다(군집을 먼저 안 정한다).

🔴 트랙이 적은 설계(모양으로 군집 → 무리 안 부호 일치)는 **순환**이다 ---
노트 657 이 *부호가 모양으로 정해진다* 를 이미 쟀다. 그래서 바꾼다:

  **A 의 학습 행을 감쇠율 5분위로 갈라 칸마다 라벨 백분위 중앙값을 적고**
  (A 의 계단 함수), 그 계단을 **B 의 감쇠율**에 먹여 **B 안에서** 스피어만을
  잰다. 계단은 A 의 라벨로만 만들고 채점은 B 의 라벨로 하므로 순환이 아니다.

자는 **쌍마다 B 의 라벨을 200번 섞은 순열 영분포의 2σ** 다(노트 335 --- 값만
섞고 관측 무늬는 그대로).

**배선 검사**: 감쇠율 정의가 노트 657 의 삼분위 무늬(게임 U · 모바일 U ·
애니 U · 웹툰 역U · 세계애니 단조)를 **넷 이상** 재현해야 통과다.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/"
                   "ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF

ROOT = Path("/Users/ax/world_model")
AFTER = ROOT / "data/state/wiki_after"
AXD = ROOT / "data/state"
#: 도메인 → 축 파일(행 순서가 판과 같다는 것을 확인했다)
AX = {"애니": "anime_axes", "웹툰": "webtoon_axes", "세계애니": "wanime_axes",
      "모바일": "mobile_axes", "게임": "game_axes", "만화": "manga_axes",
      "도서": "book_axes", "펀딩": "funding_axes", "시장팝업": "market_axes"}
#: 🔴 아이돌은 축파일 81 대 판 173 으로 어긋나고 표본도 미달 --- **측정 전에 뺐다**
DAYS = 45           # 노트 656 이 모양을 맞춘 길이
MINROW = 60         # 노트 657 과 같은 문턱(5분위당 12행)
NBIN = 5
NPERM = 200
T = 2025.0
SEED = 0
#: 노트 657 이 적은 무늬 --- 배선 검사의 정답표
SHAPE657 = {"게임": "U", "모바일": "U", "애니": "U", "웹툰": "역U",
            "세계애니": "단조"}


#: 🔴 노트 789 --- **정의 후보 넷을 결과 보기 전에 못박았다**(대장 참조).
#: 고르는 자는 **노트 657 무늬 재현 수**이고 전이 점수와 무관하다.
DEFS = ("A_log45", "B_meanslope", "C_log30", "D_ratio7")


def decay_rate(days, how="A_log45"):
    v = np.array([x[1] for x in days], float)
    v = np.clip(v, 0, None)
    if how == "A_log45":
        v = v[:45]
        if len(v) < 45:
            return np.nan
        y = np.log1p(v)
    elif how == "C_log30":
        v = v[:30]
        if len(v) < 30:
            return np.nan
        y = np.log1p(v)
    elif how == "B_meanslope":
        v = v[:45]
        if len(v) < 45:
            return np.nan
        mu = v.mean()
        if mu <= 0:
            return np.nan
        y = v / mu                      # **규모를 나눠 없앤다**
    elif how == "D_ratio7":
        v = v[:45]
        if len(v) < 45:
            return np.nan
        a, b = v[:7].mean(), v[-7:].mean()
        return float((np.log1p(b) - np.log1p(a)) / 38.0)
    else:
        raise ValueError(how)
    x = np.arange(len(y), dtype=float)
    if not np.isfinite(y).all() or y.std() == 0:
        return np.nan
    return float(np.polyfit(x, y, 1)[0])


def load_g(how="A_log45"):
    """레코드 id → 감쇠율."""
    out = {}
    for p in AFTER.glob("*.json"):
        try:
            j = json.loads(p.read_text())
        except Exception:
            continue
        d = j.get("days") or []
        if len(d) >= DAYS:
            g = decay_rate(d, how)
            if np.isfinite(g):
                out[j.get("record_id") or p.stem] = g
    return out


def shape_of(gs, ys):
    """삼분위 감쇠율 중앙값 → 'U' · '역U' · '단조'."""
    q = np.quantile(ys, [1 / 3, 2 / 3])
    lo, mid, hi = (gs[ys <= q[0]], gs[(ys > q[0]) & (ys <= q[1])], gs[ys > q[1]])
    m = [float(np.median(a)) if len(a) else np.nan for a in (lo, mid, hi)]
    if not all(np.isfinite(m)):
        return "?", m
    if m[1] < m[0] and m[1] < m[2]:
        return "U", m
    if m[1] > m[0] and m[1] > m[2]:
        return "역U", m
    return "단조", m


def stair(g, y, nbin=NBIN):
    """**A 의 계단** --- 감쇠율 5분위 칸마다 라벨 백분위 중앙값."""
    edges = np.quantile(g, np.linspace(0, 1, nbin + 1)[1:-1])
    idx = np.searchsorted(edges, g, side="right")
    yp = rankdata(y) / len(y)
    med = np.array([np.median(yp[idx == k]) if (idx == k).any() else np.nan
                    for k in range(nbin)])
    if not np.isfinite(med).all():           # 빈 칸이 있으면 앞뒤로 채운다
        ok = np.flatnonzero(np.isfinite(med))
        med = np.interp(np.arange(nbin), ok, med[ok])
    return edges, med


def apply_stair(edges, med, g):
    return med[np.searchsorted(edges, g, side="right")]


def build_dom(g_all, d0):
    dom, wire = {}, {}
    for k, f in AX.items():
        if k not in d0.dom:
            continue
        ids = list(json.loads((AXD / f"{f}.json").read_text()))
        A, M, y, t = d0.dom[k]
        if len(ids) != len(y):
            wire[k] = {"⛔": f"축파일 {len(ids)} 대 판 {len(y)}"}
            continue
        gg = np.array([g_all.get(r, np.nan) for r in ids], float)
        keep = np.isfinite(gg) & np.isfinite(y) & (np.asarray(t, float) < T)
        wire[k] = {"판 행": len(y), "감쇠율 있음": int(np.isfinite(gg).sum()),
                   "학습 & 있음": int(keep.sum())}
        if keep.sum() >= MINROW:
            dom[k] = (gg[keep], np.asarray(y, float)[keep])
    return dom, wire


def pick_def(d0):
    """🔴 **노트 657 무늬를 가장 많이 재현하는 정의를 고른다.**"""
    tab = {}
    for how in DEFS:
        dom, _ = build_dom(load_g(how), d0)
        shp = {k: shape_of(*dom[k])[0] for k in dom}
        hit = sum(1 for k, s in shp.items() if s == SHAPE657.get(k))
        tab[how] = {"도메인": len(dom), "모양": shp, "맞은 수": hit}
        print(f"  [{how}] 맞은 수 {hit}/5 · {shp}", flush=True)
    best = [h for h in DEFS if tab[h]["맞은 수"] >= 4]      # 순서가 곧 우선순위
    if best:
        best.sort(key=lambda h: (-tab[h]["맞은 수"], DEFS.index(h)))
    return (best[0] if best else None), tab


def main():
    t0 = time.time()
    d0 = FF.shell(FF.base())
    print("=== 정의 후보 넷(노트 657 재현) ===", flush=True)
    how, tab = pick_def(d0)
    print(json.dumps({"🔴 고른 정의": how or "없음 --- 재현 불가",
                      "표": tab}, ensure_ascii=False, indent=1), flush=True)
    if how is None:
        print(json.dumps({
            "중단": "🔴 **노트 657 재현 불가** --- 후보 넷 중 ≥4 를 맞추는 정의가 없다. "
                    "전이를 재지 않는다(사전등록).",
            "초": round(time.time() - t0, 1)}, ensure_ascii=False), flush=True)
        return
    g_all = load_g(how)
    rng = np.random.default_rng(SEED)
    dom, wire = build_dom(g_all, d0)
    print(json.dumps({"감쇠율 캐시": len(g_all), "배선": wire,
                      "쓰는 도메인": {k: len(v[0]) for k, v in dom.items()}},
                     ensure_ascii=False), flush=True)

    # ── 🔴 배선 검사 --- 노트 657 재현 ────────────────────────────
    shp = {}
    for k, (g, y) in dom.items():
        s, m = shape_of(g, y)
        shp[k] = {"모양": s, "삼분위 중앙값": [round(x, 6) for x in m],
                  "657": SHAPE657.get(k, "(없음)"),
                  "맞나": s == SHAPE657.get(k)}
    hit = sum(1 for k, v in shp.items() if v["맞나"])
    print(json.dumps({"🔴 배선 검사(657 재현)": shp, "맞은 수": hit,
                      "**통과(≥4)**": hit >= 4}, ensure_ascii=False,
                     indent=1), flush=True)
    if hit < 4:
        print(json.dumps({"중단": "감쇠율 정의가 노트 657 과 다르다 --- 판정 안 함"},
                         ensure_ascii=False), flush=True)
        return

    # ── 쌍별 전이 ────────────────────────────────────────────────
    names = sorted(dom)
    stairs = {k: stair(*dom[k]) for k in names}
    res, cells = {}, {}
    for a in names:
        e, m = stairs[a]
        for b in names:
            gb, yb = dom[b]
            pred = apply_stair(e, m, gb)
            if len(np.unique(pred)) < 2:
                cells[f"{a}→{b}"] = {"rho": None, "왜": "예측이 상수"}
                continue
            rho = float(spearmanr(pred, yb).statistic)
            null = np.empty(NPERM)
            for i in range(NPERM):                # 🔴 B 의 라벨만 섞는다
                null[i] = spearmanr(pred, rng.permutation(yb)).statistic
            sd = float(null.std(ddof=1)); mu = float(null.mean())
            thr = mu + 2 * sd
            cells[f"{a}→{b}"] = {
                "rho": round(rho, 4), "영평균": round(mu, 4),
                "영2σ 문턱": round(thr, 4), "**넘나**": bool(rho > thr),
                "z": round((rho - mu) / sd, 2) if sd else None,
                "B 행": len(yb)}
    for k, v in cells.items():
        if v.get("rho") is not None:
            print(f"  {k:22s} rho {v['rho']:+.4f} · 문턱 {v['영2σ 문턱']:+.4f} · "
                  f"z {v['z']:+.2f} · {'넘음' if v['**넘나**'] else '.'}", flush=True)

    # ── 무리 --- **양방향**만 무리다(사전등록) ────────────────────
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ab = cells.get(f"{a}→{b}", {}); ba = cells.get(f"{b}→{a}", {})
            if ab.get("**넘나**") and ba.get("**넘나**"):
                pairs.append((a, b, ab["rho"], ba["rho"]))
    # 연결 성분으로 무리를 만든다
    par = {k: k for k in names}
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for a, b, *_ in pairs:
        par[find(a)] = find(b)
    grp = {}
    for k in names:
        grp.setdefault(find(k), []).append(k)
    clusters = [v for v in grp.values() if len(v) >= 2]

    self_only = [c for c in names if cells.get(f"{c}→{c}", {}).get("rho")]
    crossed = [k for k, v in cells.items()
               if v.get("**넘나**") and k.split("→")[0] != k.split("→")[1]]
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "도메인": names, "행": {k: len(dom[k][0]) for k in names},
        "🔴 배선 검사 맞은 수": hit,
        "자기 전이(A→A · 참고)": {c: cells[f"{c}→{c}"]["rho"] for c in self_only},
        "쌍별": cells,
        "**문턱 넘은 교차 순서쌍**": crossed or "없음",
        "**양방향 쌍**": [f"{a}↔{b}" for a, b, *_ in pairs] or "없음",
        "**무리**": clusters or "없음",
        "판정 (가) 무리 하나 이상(2도메인 이상)": bool(clusters),
        "판정 (나) 넘는 쌍은 있으나 양방향 0": bool(crossed and not pairs),
        "판정 (다) 넘는 쌍 0": bool(not crossed),
        "예측 ① 교차 넘는 순서쌍 ≤5": len(crossed) <= 5,
        "예측 ② 애니↔세계애니가 최고": None,
        "예측 ③ 게임은 어디로도 전이 안 됨":
            not any(k for k in crossed if k.startswith("게임")
                    or k.endswith("게임")),
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
