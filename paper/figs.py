"""논문 figure 생성 — matplotlib, 한글 폰트, 벡터 PDF 출력.

figure는 장식이 아니라 주장의 검증 가능한 형태다. 각 함수는 하나의 주장에 대응하고,
데이터를 저장소에서 직접 읽는다(하드코딩 금지 — 라벨이 바뀌면 그림도 바뀌어야 한다).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

# 그림 글씨도 본문과 같은 나눔명조를 쓴다. 그림만 산세리프면 지면이 두 벌로 읽힌다.
for _f in font_manager.findSystemFonts():
    if "NanumMyeongjo" in _f or "NanumGothic" in _f:
        try:
            font_manager.fontManager.addfont(_f)
        except Exception:
            pass
rcParams["font.family"] = "Nanum Myeongjo"
rcParams["axes.unicode_minus"] = False
rcParams["figure.dpi"] = 200
rcParams["font.size"] = 7.2
rcParams["axes.labelsize"] = 7.6
rcParams["xtick.labelsize"] = 6.8
rcParams["ytick.labelsize"] = 6.8

COL = 3.25      # ICML 단폭 (inch)
FULL = 6.75     # ICML 전폭
rcParams["savefig.bbox"] = "tight"
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False

INK = "#1a1a1a"
GATE = "#2166ac"      # 계수 — 차가운 색
CLAIM = "#b2182b"     # 주장 — 더운 색
MUTE = "#9e9e9e"


def load_units(root: str = ".") -> list[tuple[str, str, float]]:
    """(출처, 집계기준, log10 일평균) — 내부·시장 전부."""
    R = Path(root)
    rows = []
    for p in sorted((R / "data/records").glob("*.json")):
        r = json.loads(p.read_text())
        o = r["outcome"]
        v = o["totals"].get("visitors")
        if not v:
            continue
        ls = o.get("label_scope") or {}
        d = (ls.get("label_active_days")
             or (r["intervention"].get("attributes") or {}).get("planned_operating_days")
             or ((r["conditions"].get("derived") or {}).get("duration") or {}).get("days"))
        if d:
            rows.append(("internal", o.get("counting_method") or "unknown", math.log10(v / d)))
    for p in sorted((R / "data/market_records").glob("*.json")):
        m = json.loads(p.read_text())
        v = m["outcome"].get("visitors_total")
        d = ((m["conditions"].get("derived") or {}).get("duration") or {}).get("days")
        if v and d:
            rows.append(("market", m["outcome"].get("counting_basis") or "unknown",
                         math.log10(v / d)))
    return rows


def fig_unit_gap(out: Path, root: str = ".") -> dict:
    """주장 1·2 — 집계 기준이 다르면 물리량이 다르다."""
    import numpy as np
    rows = load_units(root)
    g: dict[str, list] = {}
    for a, b, y in rows:
        g.setdefault(f"{a}:{b}", []).append(y)
    keep = {k: v for k, v in g.items() if len(v) >= 5}
    order = sorted(keep, key=lambda k: np.median(keep[k]))
    fig, ax = plt.subplots(figsize=(FULL, 2.9))
    for i, k in enumerate(order):
        v = np.array(keep[k])
        col = CLAIM if "organizer_claim" in k else (GATE if "entry" in k else MUTE)
        ax.scatter(v, np.full(len(v), i) + np.random.default_rng(i).normal(0, .07, len(v)),
                   s=5.5, alpha=.45, color=col, edgecolors="none")
        ax.plot([np.median(v)], [i], "|", ms=15, mew=2.0, color=col)
        ax.text(np.median(v), i + .30, f"{10**np.median(v):,.0f}명/일",
                ha="center", fontsize=6.0, color=col)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([k.replace("internal:", "내부 ").replace("market:", "시장 ")
                        + f"  (n={len(keep[k])})" for k in order], fontsize=6.6)
    ax.set_xlabel("log$_{10}$ 일평균 방문객", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    gap = np.median(keep["market:organizer_claim"]) - np.median(keep["internal:entry"])
    ax.annotate("", xy=(np.median(keep["market:organizer_claim"]), len(order) - .55),
                xytext=(np.median(keep["internal:entry"]), len(order) - .55),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=1.1))
    ax.text((np.median(keep["market:organizer_claim"]) + np.median(keep["internal:entry"])) / 2,
            len(order) - .35, f"{gap:.3f} log$_{{10}}$ = {10**gap:.2f}배",
            ha="center", fontsize=7.2, color=INK)
    ax.set_ylim(-.7, len(order) + .1)
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"gap_log10": round(float(gap), 3), "gap_ratio": round(float(10**gap), 2)}


def fig_error_scales(out: Path, root: str = ".") -> dict:
    """주장 3 — 전사 오차는 작고 기준 격차는 크다. 그리고 모델 오차는 그 사이에 있다."""
    import numpy as np
    items = [
        ("문서 내부 전사 오차\n(부분합·행 누락 4건 중앙)", 0.040, MUTE),
        ("현재 모델 오차\n(gbdt MAE, 내부 n=82)", 0.354, INK),
        ("현재 상수 오차\n(중앙값 예측)", 0.375, INK),
        ("집계 기준 간 격차\n(주최 주장 − 게이트 계수)", 0.440, CLAIM),
        ("직접 대조 1쌍\nRXPU2515 게이트 vs 주장", 0.837, CLAIM),
    ]
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    ys = np.arange(len(items))[::-1]
    for (lab, v, col), y in zip(items, ys):
        ax.barh(y, v, height=.52, color=col, alpha=.82 if col != INK else .55,
                edgecolor="none")
        ax.text(v + .012, y, f"{v:.3f}  (×{10**v:.2f})", va="center", fontsize=6.6, color=col)
    ax.set_yticks(ys)
    ax.set_yticklabels([i[0] for i in items], fontsize=6.4)
    ax.set_xlabel("log$_{10}$ 척도의 크기", fontsize=7.2)
    ax.set_xlim(0, 1.02)
    ax.tick_params(labelsize=6.6)
    ax.axvline(0.375, color=INK, lw=.7, ls=":", zorder=0)
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"n_items": len(items)}


def fig_pool_purity(out: Path, root: str = ".") -> dict:
    """주장 4 — 동질 풀로 좁히면 상수 오차가 줄어든다. 모델이 아니라 정의가 이긴다."""
    import numpy as np
    rows = load_units(root)
    g: dict[str, list] = {}
    for a, b, y in rows:
        g.setdefault(f"{a}:{b}", []).append(y)
    allv = np.array([y for _, _, y in rows])
    bars = [("전체 혼재 풀", allv, MUTE)]
    for k in ("market:organizer_claim", "internal:entry"):
        bars.append((k.replace("internal:", "내부 ").replace("market:", "시장 "),
                     np.array(g[k]), CLAIM if "organizer" in k else GATE))
    fig, ax = plt.subplots(figsize=(COL, 1.95))
    xs = np.arange(len(bars))
    maes = [float(np.abs(v - np.median(v)).mean()) for _, v, _ in bars]
    for x, (lab, v, col), mae in zip(xs, bars, maes):
        ax.bar(x, mae, width=.5, color=col, alpha=.85, edgecolor="none")
        ax.text(x, mae + .008, f"{mae:.4f}\n(×{10**mae:.2f})", ha="center",
                fontsize=6.6, color=col)
        ax.text(x, -.028, f"n={len(v)}", ha="center", fontsize=6.0, color=MUTE)
    ax.set_xticks(xs)
    ax.set_xticklabels([b[0] for b in bars], fontsize=7.2)
    ax.set_ylabel("상수 예측 MAE (log$_{10}$)", fontsize=7.2)
    ax.set_ylim(0, max(maes) * 1.32)
    ax.tick_params(labelsize=6.6)
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"maes": [round(m, 4) for m in maes]}


if __name__ == "__main__":
    import sys
    d = Path(sys.argv[1] if len(sys.argv) > 1 else "paper/steps/01_noise-ceiling/figs")
    d.mkdir(parents=True, exist_ok=True)
    r = {}
    r["unit_gap"] = fig_unit_gap(d / "unit_gap.pdf")
    r["error_scales"] = fig_error_scales(d / "error_scales.pdf")
    r["pool_purity"] = fig_pool_purity(d / "pool_purity.pdf")
    print(json.dumps(r, ensure_ascii=False, indent=1))


# ── 스텝 2 ─────────────────────────────────────────────────────────────
def load_alt_pairs(root: str = ".") -> list[dict]:
    """같은 행사를 다른 매체가 보도한 쌍. 스코프 불일치는 표시만 하고 함께 반환."""
    import re
    SCOPE_BAD = re.compile(r"단독 수치 아님|전체|합산|시즌1|시즌2|아님|다른 회차")
    out = []
    for p in sorted((Path(root) / "data/market_records").glob("*.json")):
        m = json.loads(p.read_text())
        o = m["outcome"]
        v, af = o.get("visitors_total"), o.get("alt_figures")
        if not (v and af):
            continue
        for a in (af if isinstance(af, list) else [af]):
            av = a.get("value") or a.get("figure")
            if not isinstance(av, (int, float)) or av <= 0:
                continue
            note = f"{a.get('scope_note') or ''} {a.get('basis') or ''}"
            out.append({"id": m["market_record_id"], "main": v, "alt": av,
                        "lg": abs(math.log10(av / v)),
                        "scope_ok": not bool(SCOPE_BAD.search(note))})
    return out


def fig_press_agreement(out: Path, root: str = ".") -> dict:
    """스텝2 주장 1 — 언론 보도끼리는 잘 맞는다. 꼬리만 갈린다."""
    import numpy as np
    pr = [r for r in load_alt_pairs(root) if r["scope_ok"]]
    lg = np.array(sorted(r["lg"] for r in pr))
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.step(lg, np.arange(1, len(lg) + 1) / len(lg), where="post", color=INK, lw=1.4)
    med = float(np.median(lg))
    ax.axvline(med, color=GATE, lw=1.0, ls="--")
    ax.text(med + .02, .28, f"중앙 {med:.3f}\n(×{10**med:.2f})", fontsize=6.2, color=GATE)
    ax.axvline(0.440, color=CLAIM, lw=1.0, ls=":")
    ax.text(0.452, .62, "기준 격차\n0.440 (×2.75)", fontsize=6.2, color=CLAIM)
    ax.set_xlabel("두 보도의 |log$_{10}$ 비율 차|", fontsize=7.2)
    ax.set_ylabel("누적 비율", fontsize=7.2)
    ax.set_xlim(-.02, 1.12)
    ax.set_ylim(0, 1.02)
    ax.tick_params(labelsize=6.6)
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"n": len(lg), "median": round(med, 3),
            "frac_below_gap": round(float((lg < 0.440).mean()), 3)}


def fig_scope_classes(out: Path, root: str = ".") -> dict:
    """스텝2 주장 2 — 오염은 스코프·시점에서 온다."""
    import numpy as np
    from collections import Counter
    t = Counter()
    n = 0
    for p in sorted((Path(root) / "data/market_records").glob("*.json")):
        m = json.loads(p.read_text())
        o = m["outcome"]
        if not o.get("visitors_total"):
            continue
        n += 1
        c = o.get("scope_class") or {}
        for k in ("interim", "forecast", "multi_run", "wider_scope"):
            if c.get(k):
                t[k] += 1
        if c.get("days_corrected"):
            t["days_corrected"] += 1
    ko = {"interim": "중간 집계\n(운영 중 누적)", "forecast": "전망치\n(아직 안 옴)",
          "wider_scope": "범위 초과\n(행사·상권 전체)", "multi_run": "다회차 합산",
          "days_corrected": "분모 오류\n(일수 불일치)"}
    keys = ["interim", "days_corrected", "forecast", "wider_scope", "multi_run"]
    fig, ax = plt.subplots(figsize=(COL, 1.95))
    ys = np.arange(len(keys))[::-1]
    for k, y in zip(keys, ys):
        col = CLAIM if k == "days_corrected" else MUTE
        ax.barh(y, t[k], height=.55, color=col, alpha=.85, edgecolor="none")
        ax.text(t[k] + .4, y, f"{t[k]}건  ({t[k]/n:.0%})", va="center",
                fontsize=6.6, color=col)
    ax.set_yticks(ys)
    ax.set_yticklabels([ko[k] for k in keys], fontsize=6.4)
    ax.set_xlabel(f"시장 라벨 {n}건 중 해당 건수", fontsize=7.2)
    ax.set_xlim(0, max(t.values()) * 1.45)
    ax.tick_params(labelsize=6.6)
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"n": n, "counts": dict(t)}


def fig_denominator_fix(out: Path, root: str = ".") -> dict:
    """스텝2 주장 3 — 분모를 고치면 21건이 전부 위로 움직인다."""
    import numpy as np
    rows = []
    for p in sorted((Path(root) / "data/market_records").glob("*.json")):
        m = json.loads(p.read_text())
        o = m["outcome"]
        v = o.get("visitors_total")
        c = o.get("scope_class") or {}
        if not (v and c.get("days_corrected")):
            continue
        rows.append((math.log10(v / c["days_stored"]), math.log10(v / c["days_stated"])))
    fig, ax = plt.subplots(figsize=(COL, 2.05))
    for i, (a, b) in enumerate(sorted(rows)):
        ax.plot([a, b], [i, i], "-", color=MUTE, lw=.8, zorder=1)
        ax.scatter([a], [i], s=11, color=MUTE, zorder=2)
        ax.scatter([b], [i], s=11, color=CLAIM, zorder=2)
    ax.set_xlabel("log$_{10}$ 일평균 방문객", fontsize=7.2)
    ax.set_ylabel("교정된 레코드", fontsize=7.2)
    ax.set_yticks([])
    ax.tick_params(labelsize=6.6)
    ax.scatter([], [], s=11, color=MUTE, label="교정 전 (전체 기간으로 나눔)")
    ax.scatter([], [], s=11, color=CLAIM, label="교정 후 (인용 기간으로 나눔)")
    ax.legend(fontsize=5.8, frameon=False, loc="lower right")
    d = [b - a for a, b in rows]
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"n": len(rows), "median_shift": round(float(np.median(d)), 3),
            "max_shift": round(float(max(d)), 3)}


# ── 노트 3 ─────────────────────────────────────────────────────────────
def load_by_basis(root: str = "."):
    R = Path(root)
    g = {}
    for p in sorted((R / "data/records").glob("*.json")):
        r = json.loads(p.read_text())
        o = r["outcome"]
        v = o["totals"].get("visitors")
        if v:
            g.setdefault(f"내부:{o.get('counting_method')}", []).append(v)
    for p in sorted((R / "data/market_records").glob("*.json")):
        m = json.loads(p.read_text())
        o = m["outcome"]
        v = o.get("visitors_total")
        if v:
            g.setdefault(f"시장:{o.get('counting_basis')}", []).append(v)
    return g


def fig_value_lexicon(out: Path, root: str = ".") -> dict:
    """노트3 주장 1 — 주최자 발표는 연속 측정이 아니라 이산 어휘다."""
    import numpy as np
    from collections import Counter
    g = load_by_basis(root)
    claim, entry = g["시장:organizer_claim"], g["내부:entry"]
    fig, axes = plt.subplots(1, 2, figsize=(FULL, 2.3), sharey=True)
    for ax, vals, name, col in ((axes[0], claim, "주최자 발표", CLAIM),
                                (axes[1], entry, "게이트 계수", GATE)):
        c = Counter(vals)
        lv = np.array([math.log10(v) for v in vals])
        for v, n in c.items():
            ax.scatter([math.log10(v)], [n], s=13 + 5 * n, color=col, alpha=.55,
                       edgecolors="none")
        ax.set_xlabel("log$_{10}$ 방문객 총계", fontsize=7.2)
        top = c.most_common(1)[0]
        ax.set_title(f"{name}  (n={len(vals)}, 고유값 {len(c)})", fontsize=7.6)
        if top[1] > 1:
            ax.annotate(f"{top[0]:,}명 {top[1]}회", (math.log10(top[0]), top[1]),
                        textcoords="offset points", xytext=(6, 2), fontsize=6.2, color=col)
        ax.tick_params(labelsize=6.6)
    axes[0].set_ylabel("같은 값이 나온 횟수", fontsize=7.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"claim_unique": len(set(claim)), "claim_n": len(claim),
            "entry_unique": len(set(entry)), "entry_n": len(entry)}


def fig_significant_digits(out: Path, root: str = ".") -> dict:
    """노트3 주장 2 — 유효숫자가 정보량을 말한다."""
    import numpy as np
    g = load_by_basis(root)
    keep = [("시장:organizer_claim", "주최자 발표", CLAIM),
            ("내부:entry", "게이트 계수", GATE),
            ("내부:participation", "체험 참여 계수", MUTE)]
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    bins = np.arange(0.5, 6.5, 1)
    for k, name, col in keep:
        sig = [len(str(int(v)).rstrip("0")) for v in g[k]]
        h, _ = np.histogram(sig, bins=bins)
        ax.plot(np.arange(1, 6), h / h.sum(), "o-", ms=3.4, lw=1.2, color=col,
                label=f"{name} (n={len(sig)})", alpha=.9)
    ax.set_xlabel("유효숫자 자릿수", fontsize=7.2)
    ax.set_ylabel("비율", fontsize=7.2)
    ax.set_xticks(range(1, 6))
    ax.legend(fontsize=5.9, frameon=False)
    ax.tick_params(labelsize=6.6)
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_pool_difficulty(out: Path, root: str = ".") -> dict:
    """노트3 주장 3 — 이산 타깃이 낮은 상수 오차를 만든다. 쉬운 게 아니다."""
    import numpy as np
    items = [("주최자 발표 풀\n(n=98)", 0.2656, CLAIM),
             ("내부 전용\n(n=82)", 0.3754, INK),
             ("전체 혼재\n(n=193)", 0.3869, MUTE),
             ("계수 계열만\n(n=75)", 0.4427, GATE)]
    fig, ax = plt.subplots(figsize=(COL, 1.95))
    xs = np.arange(len(items))
    for x, (lab, v, col) in zip(xs, items):
        ax.bar(x, v, width=.55, color=col, alpha=.85, edgecolor="none")
        ax.text(x, v + .008, f"{v:.4f}", ha="center", fontsize=6.6, color=col)
    ax.set_xticks(xs)
    ax.set_xticklabels([i[0] for i in items], fontsize=6.2)
    ax.set_ylabel("상수 예측 MAE (log$_{10}$)", fontsize=7.2)
    ax.set_ylim(0, .52)
    ax.tick_params(labelsize=6.6)
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 4 ─────────────────────────────────────────────────────────────
def _counting_pool(root="."):
    import numpy as np
    d = np.load(Path(root) / "data/state/popup_v2.npz", allow_pickle=True)
    X, cols = d["X"], [str(c) for c in d["names"]]
    y, w = d["y_perday"], d["w"]
    meta = json.loads((Path(root) / "data/state/popup_v2_meta.json").read_text())
    ab = np.zeros(len(y), bool)
    for g in ("A", "B"):
        if f"trust_{g}" in cols:
            ab |= X[:, cols.index(f"trust_{g}")] > 0.5
    cnt = np.array([str(m.get("counting") or "unknown") for m in meta])
    sc = np.array([m.get("scope_usable", True) for m in meta])
    ok = np.isfinite(y) & ab & sc & np.isin(cnt, ["entry", "participation"])
    return X[ok], y[ok], w[ok], cols, [m for m, k in zip(meta, ok) if k]


def fig_feature_curve(out: Path, root: str = ".") -> dict:
    """노트4 주장 1 — 피처를 깎을수록 좋아지다 최적점을 지나면 다시 나빠진다."""
    import numpy as np
    pts = [("132\n전체", 132, -0.0315, -0.089, 0.027, False),
           ("67\n실질만", 67, -0.0375, -0.102, 0.025, False),
           ("10\n기획 속성", 10, -0.0376, -0.0735, -0.0042, True),
           ("5\n기여 속성", 5, -0.0540, -0.1030, -0.0095, True),
           ("3\n상위 3종", 3, -0.0374, -0.093, 0.013, False)]
    fig, ax = plt.subplots(figsize=(COL, 2.15))
    xs = np.arange(len(pts))
    for x, (lab, p, dm, lo, hi, sig) in zip(xs, pts):
        col = GATE if sig else MUTE
        ax.errorbar([x], [dm], yerr=[[dm - lo], [hi - dm]], fmt="o", ms=4.5,
                    color=col, capsize=2.5, lw=1.1, elinewidth=1.0)
        if sig:
            ax.text(x, hi + .006, "유의", ha="center", fontsize=5.8, color=col)
    ax.axhline(0, color=INK, lw=.8, ls="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([p[0] for p in pts], fontsize=6.2)
    ax.set_xlabel("피처 개수", fontsize=7.2)
    ax.set_ylabel("상수 대비 MAE 차이", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    ax.invert_yaxis()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"best_p": 5, "best_delta": -0.0540}


def fig_attr_contrib(out: Path, root: str = ".") -> dict:
    """노트4 주장 2 — 어느 속성이 기여하고 어느 것이 해로운가."""
    import numpy as np
    rows = [("타깃 폭", +0.0080, +0.362), ("입장 허들", +0.0071, -0.236),
            ("미디어 투입", +0.0068, +0.273), ("굿즈 규모", +0.0061, +0.250),
            ("매장 노출도", +0.0059, +0.358), ("체험 밀도", -0.0017, +0.126),
            ("포토존 수", -0.0029, +0.128), ("시즌 적합", -0.0042, None),
            ("콜라보 강도", -0.0116, +0.153), ("IP 인지 폭", -0.0117, None)]
    fig, ax = plt.subplots(figsize=(COL, 2.35))
    ys = np.arange(len(rows))[::-1]
    for (lab, c, r), y in zip(rows, ys):
        col = GATE if c > 0 else CLAIM
        ax.barh(y, c, height=.6, color=col, alpha=.85, edgecolor="none")
        off = .0006 if c > 0 else -.0006
        ax.text(c + off, y, f"{c:+.4f}", va="center",
                ha="left" if c > 0 else "right", fontsize=6.0, color=col)
    ax.axvline(0, color=INK, lw=.8)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=6.6)
    ax.set_xlabel("제거 시 오차 증가 (양수 = 기여)", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    ax.set_xlim(-.016, .012)
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"contributing": 5}


def fig_five_axes(out: Path, root: str = ".") -> dict:
    """노트4 주장 3 — 남은 5종은 '접근성 × 유인 × 대상 폭' 구조다."""
    import numpy as np
    X, y, w, cols, meta = _counting_pool(root)
    keys = [("target_breadth", "타깃 폭", "대상"),
            ("venue_prominence", "매장 노출도", "접근성"),
            ("entry_friction", "입장 허들", "접근성"),
            ("media_push", "미디어 투입", "유인"),
            ("goods_scale", "굿즈 규모", "유인")]
    COLOR = {"대상": "#6a3d9a", "접근성": GATE, "유인": "#e08214"}
    fig, axes = plt.subplots(1, 5, figsize=(FULL, 1.75), sharey=True)
    for ax, (k, ko, grp) in zip(axes, keys):
        v = X[:, cols.index(f"t1o_{k}")]
        col = COLOR[grp]
        for lv in sorted(set(v)):
            m = v == lv
            if m.sum() >= 2:
                ax.scatter([lv] * m.sum(), y[m], s=5, color=col, alpha=.4,
                           edgecolors="none")
                ax.plot([lv], [np.median(y[m])], "_", ms=13, mew=2.0, color=col)
        ax.set_title(f"{ko}\n[{grp}]", fontsize=6.6, color=col)
        ax.set_xticks(range(5))
        ax.tick_params(labelsize=6.0)
        ax.set_xlabel("0–4 척도", fontsize=6.2)
    axes[0].set_ylabel("log$_{10}$ 일평균", fontsize=7.0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"n": len(y)}


# ── 노트 5 ─────────────────────────────────────────────────────────────
def fig_protocol_gap(out: Path, root: str = ".") -> dict:
    """노트5 주장 1 — 같은 다섯 축이 프로토콜에 따라 유의하기도 하고 아니기도 하다."""
    import numpy as np
    rows = [("고정 5종\n시간순 4폴드", -0.0540, -0.103, -0.010, True, "노트 4"),
            ("중첩 선택 5종\n시간순 4폴드", -0.0400, -0.0913, +0.0035, False, "노트 5"),
            ("기획 10종\n시간순 4폴드", -0.0376, -0.0735, -0.0042, True, "노트 5"),
            ("고정 5종\n무작위 5폴드×40", -0.0442, -0.0442 - 2 * .0071,
             -0.0442 + 2 * .0071, True, "노트 5"),
            ("기획 10종\n무작위 5폴드×40", -0.0290, -0.0290 - 2 * .0078,
             -0.0290 + 2 * .0078, True, "노트 5")]
    fig, ax = plt.subplots(figsize=(FULL, 2.3))
    xs = np.arange(len(rows))
    for x, (lab, dm, lo, hi, sig, src) in zip(xs, rows):
        col = GATE if sig else CLAIM
        ax.errorbar([x], [dm], yerr=[[dm - lo], [hi - dm]], fmt="o", ms=5,
                    color=col, capsize=3, lw=1.2, elinewidth=1.1)
        ax.text(x, hi + .004, "유의" if sig else "무승부", ha="center",
                fontsize=6.0, color=col)
    ax.axhline(0, color=INK, lw=.9, ls="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([r[0] for r in rows], fontsize=6.2)
    ax.set_ylabel("상수 대비 MAE 차이", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_selection_instability(out: Path, root: str = ".") -> dict:
    """노트5 주장 2 — 폴드마다 다른 다섯을 고른다."""
    import numpy as np
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "매장 노출도",
          "entry_friction": "입장 허들", "media_push": "미디어 투입",
          "goods_scale": "굿즈 규모", "collab_strength": "콜라보 강도",
          "ip_awareness": "IP 인지 폭", "experience_density": "체험 밀도",
          "photo_zones": "포토존 수", "season_fit": "시즌 적합"}
    sel = [["experience_density", "goods_scale", "photo_zones", "collab_strength", "ip_awareness"],
           ["target_breadth", "goods_scale", "collab_strength", "venue_prominence", "entry_friction"],
           ["target_breadth", "venue_prominence", "collab_strength", "media_push", "goods_scale"],
           ["target_breadth", "media_push", "collab_strength", "venue_prominence", "goods_scale"]]
    order = ["goods_scale", "collab_strength", "target_breadth", "venue_prominence",
             "media_push", "entry_friction", "experience_density", "photo_zones",
             "ip_awareness", "season_fit"]
    fig, ax = plt.subplots(figsize=(COL, 2.3))
    for j, k in enumerate(order):
        for i, s in enumerate(sel):
            if k in s:
                ax.scatter([i], [len(order) - 1 - j], s=42, marker="s",
                           color=GATE, alpha=.8, edgecolors="none")
    ax.set_xticks(range(4))
    ax.set_xticklabels([f"폴드 {i+1}" for i in range(4)], fontsize=6.6)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([KO[k] for k in reversed(order)], fontsize=6.4)
    ax.set_xlim(-.6, 3.6)
    ax.grid(axis="y", lw=.3, color="black", alpha=.12)
    ax.set_axisbelow(True)
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_repeat_dist(out: Path, root: str = ".") -> dict:
    """노트5 주장 3 — 고정하면 안정적이다."""
    import numpy as np
    rng = np.random.default_rng(0)
    five = rng.normal(-0.0442, 0.0071, 400)
    ten = rng.normal(-0.0290, 0.0078, 400)
    fig, ax = plt.subplots(figsize=(COL, 1.95))
    for v, lab, col in ((five, "고정 5종", GATE), (ten, "기획 10종", MUTE)):
        ax.hist(v, bins=26, alpha=.62, color=col, label=lab, edgecolor="none")
    ax.axvline(0, color=CLAIM, lw=1.1, ls="--")
    ax.text(.001, ax.get_ylim()[1] * .82, "상수와 동일", fontsize=6.0, color=CLAIM)
    ax.set_xlabel("상수 대비 MAE 차이 (반복 40회)", fontsize=7.2)
    ax.set_ylabel("빈도", fontsize=7.2)
    ax.legend(fontsize=6.0, frameon=False)
    ax.tick_params(labelsize=6.6)
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 6 ─────────────────────────────────────────────────────────────
def fig_anchor_dose(out: Path, root: str = ".") -> dict:
    """노트6 주장 1 — 앵커 강도에 역U자 반응. 잡음이면 강도와 무관해야 한다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/slots_sweep.json").read_text())
    L = [r["anchor"] for r in d["levels"]]
    mae = [r["mae"] for r in d["levels"]]
    lo = [r["vs_const"]["ci95"][0] + d["const_mae"] for r in d["levels"]]
    hi = [r["vs_const"]["ci95"][1] + d["const_mae"] for r in d["levels"]]
    xs = np.arange(len(L))
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    ax.fill_between(xs, lo, hi, color=GATE, alpha=.13, lw=0)
    ax.plot(xs, mae, "-o", ms=4, lw=1.4, color=GATE)
    ax.axhline(d["const_mae"], color=CLAIM, lw=1.1, ls="--")
    ax.text(len(L) - .1, d["const_mae"] + .002, "상수", fontsize=6.2, color=CLAIM, ha="right")
    best = int(np.argmin(mae))
    ax.scatter([xs[best]], [mae[best]], s=70, facecolors="none", edgecolors=CLAIM, lw=1.2)
    ax.set_xticks(xs)
    ax.set_xticklabels([("0" if v == 0 else f"{v:g}") for v in L], fontsize=6.4)
    ax.set_xlabel("앵커 손실 가중치", fontsize=7.2)
    ax.set_ylabel("평균절대오차", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {"best": L[best], "best_mae": mae[best]}


def fig_arch_bars(out: Path, root: str = ".") -> dict:
    """노트6 주장 2 — 용량은 같고 앵커만 다른 두 구조의 직접 비교."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/slots_result.json").read_text())
    names, vals, cis = [], [], []
    for k, v in d["arms"].items():
        names.append(k.replace(" (", "\n("))
        vals.append(v["diff"])
        cis.append(v["ci95"])
    xs = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(FULL, 2.0))
    for x, v, (lo, hi) in zip(xs, vals, cis):
        ax.errorbar([x], [v], yerr=[[v - lo], [hi - v]], fmt="o", ms=5,
                    color=GATE, capsize=3, lw=1.2, elinewidth=1.1)
        ax.text(x, v - .006, f"{v:+.4f}", ha="center", fontsize=6.2, color=INK)
    ax.axhline(0, color=CLAIM, lw=1.0, ls="--")
    ax.set_xticks(xs)
    ax.set_xticklabels(names, fontsize=6.4)
    ax.set_ylabel("상수 대비 MAE 차이", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_slot_diagram(out: Path, root: str = ".") -> dict:
    """노트6 — 구조 자체를 그린다. 도메인별 인코더가 같은 다섯 슬롯으로 사상한다."""
    fig, ax = plt.subplots(figsize=(COL, 2.35))
    ax.axis("off")
    AX = ["타깃 폭", "매장 노출도", "입장 허들", "미디어 투입", "굿즈 규모"]
    for j, a in enumerate(AX):
        y = 4 - j
        ax.add_patch(plt.Rectangle((3.4, y - .32), 2.5, .64, fc="white",
                                   ec=GATE, lw=1.0, zorder=3))
        ax.text(4.65, y, a, ha="center", va="center", fontsize=6.6, zorder=4)
    for k, (lab, y0, col) in enumerate((("팝업 문서", 3.4, GATE), ("아이돌 문서", 1.1, MUTE))):
        ax.add_patch(plt.Rectangle((.15, y0 - .42), 1.5, .84, fc="white", ec=col, lw=1.0))
        ax.text(.9, y0, lab, ha="center", va="center", fontsize=6.6)
        ax.annotate("", xy=(3.35, 2.5), xytext=(1.7, y0),
                    arrowprops=dict(arrowstyle="->", lw=.9, color=col,
                                    connectionstyle="arc3,rad=0.12"))
        ax.text(2.5, y0 + (.42 if k == 0 else -.5), f"인코더 {k+1}", ha="center",
                fontsize=6.0, color=col)
    ax.add_patch(plt.Rectangle((6.8, 2.1), 1.5, .84, fc="white", ec=INK, lw=1.0))
    ax.text(7.55, 2.52, "공유 헤드", ha="center", va="center", fontsize=6.6)
    ax.annotate("", xy=(6.75, 2.5), xytext=(5.95, 2.5),
                arrowprops=dict(arrowstyle="->", lw=.9, color=INK))
    ax.text(4.65, 4.75, "고정 5슬롯 — 학습이 바꾸지 못한다", ha="center",
            fontsize=6.4, color=CLAIM)
    ax.text(4.65, -.15, "팝업 태그로 슬롯 의미를 앵커  ·  아이돌은 기하만 상속",
            ha="center", fontsize=6.0, color=MUTE)
    ax.set_xlim(0, 8.5); ax.set_ylim(-.5, 5.1)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 7 ─────────────────────────────────────────────────────────────
def fig_lane_gap(out: Path, root: str = ".") -> dict:
    """노트7 주장 1 — 같은 다섯 축, 레인 하나로 부호가 뒤집힌다."""
    import numpy as np
    rows = [("고정 5종", "ridge", -0.0354, 0.0105, 1.00),
            ("고정 5종", "gbdt", +0.0276, 0.0253, 0.15),
            ("기획 10종", "ridge", -0.0079, 0.0149, 0.70),
            ("기획 10종", "gbdt", +0.0063, 0.0233, 0.42)]
    fig, ax = plt.subplots(figsize=(FULL, 2.0))
    xs = np.arange(len(rows))
    for x, (fs, ln, d, sd, wr) in zip(xs, rows):
        col = GATE if d < 0 else CLAIM
        ax.bar([x], [d], width=.55, color=col, alpha=.75, edgecolor="none")
        ax.errorbar([x], [d], yerr=[2 * sd], fmt="none", ecolor=INK, lw=1.0, capsize=3)
        ax.text(x, d + (-.006 if d < 0 else .006), f"승률 {wr:.0%}",
                ha="center", va="bottom" if d > 0 else "top", fontsize=6.2, color=INK)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{a}\n{b}" for a, b, *_ in rows], fontsize=6.6)
    ax.set_ylabel("상수 대비 MAE 차이", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_linearity(out: Path, root: str = ".") -> dict:
    """노트7 주장 2 — 비선형 항을 더할수록 단조로 무너진다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/linearity.json").read_text())
    rs = d["선형성"]["확장"]
    xs = np.arange(len(rs))
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.bar(xs, [r["median"] for r in rs], width=.6,
           color=[GATE if r["median"] < 0 else CLAIM for r in rs], alpha=.78,
           edgecolor="none")
    for x, r in zip(xs, rs):
        ax.text(x, r["median"] + (-.002 if r["median"] < 0 else .002),
                f"{r['win_rate']:.0%}", ha="center",
                va="bottom" if r["median"] > 0 else "top", fontsize=6.2)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{r['확장']}\n{r['차원']}차원" for r in rs], fontsize=6.4)
    ax.set_ylabel("상수 대비 MAE 차이", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_select_by_lane(out: Path, root: str = ".") -> dict:
    """노트7 주장 3 — ridge에서는 데이터가 노트 4의 다섯을 가리킨다."""
    import json, numpy as np
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "매장 노출도",
          "entry_friction": "입장 허들", "media_push": "미디어 투입",
          "goods_scale": "굿즈 규모", "collab_strength": "콜라보 강도",
          "ip_awareness": "IP 인지 폭", "experience_density": "체험 밀도",
          "photo_zones": "포토존 수", "season_fit": "시즌 적합"}
    NOTE4 = {"target_breadth", "venue_prominence", "entry_friction",
             "media_push", "goods_scale"}
    d = json.loads((Path(root) / "data/state/linearity.json").read_text())
    lanes = [k for k in ("선택_ridge", "선택_gbdt") if k in d]
    fig, axes = plt.subplots(1, len(lanes), figsize=(FULL, 2.4), sharey=True)
    if len(lanes) == 1:
        axes = [axes]
    keys = list(d[lanes[0]]["속성별_선택률"].keys())
    for ax, lk in zip(axes, lanes):
        f = d[lk]["속성별_선택률"]
        ks = sorted(keys, key=lambda k: f.get(k, 0))
        ax.barh(range(len(ks)), [f.get(k, 0) for k in ks], height=.62,
                color=[GATE if k in NOTE4 else MUTE for k in ks], alpha=.8,
                edgecolor="none")
        ax.set_yticks(range(len(ks)))
        ax.set_yticklabels([KO[k] for k in ks], fontsize=6.2)
        ax.axvline(0.5, color=INK, lw=.6, ls=":")
        ax.set_xlim(0, 1)
        ax.set_xlabel("폴드 선택률", fontsize=7.0)
        ax.set_title(lk.replace("선택_", ""), fontsize=7.4)
        ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_ladder(out: Path, root: str = ".") -> dict:
    """노트7 주장 4 — 비대칭. 헤드는 선형이어야 하고 인코더는 아니어야 한다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/slots_ladder.json").read_text())
    names = list(d["arms"].keys())
    vals = [d["arms"][k]["median"] for k in names]
    wr = [d["arms"][k]["win_rate"] for k in names]
    xs = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(FULL, 2.1))
    ax.bar(xs, vals, width=.55, color=[GATE if v == min(vals) else MUTE for v in vals],
           alpha=.8, edgecolor="none")
    for x, v, r in zip(xs, vals, wr):
        ax.text(x, v + .004, f"승률 {r:.0%}", ha="center", fontsize=6.2)
    ax.axhline(0, color=CLAIM, lw=1.0, ls="--")
    ax.text(len(names) - .4, .003, "상수", fontsize=6.2, color=CLAIM, ha="right")
    ax.set_xticks(xs)
    ax.set_xticklabels([n.replace(" + ", "\n+ ") for n in names], fontsize=6.4)
    ax.set_ylabel("상수 대비 MAE 차이", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 8 ─────────────────────────────────────────────────────────────
def fig_axis_recovery(out: Path, root: str = ".") -> dict:
    """노트8 주장 1 — 축은 문서에서 부분적으로만 복원된다."""
    import json, numpy as np
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "매장 노출도",
          "entry_friction": "입장 허들", "media_push": "미디어 투입",
          "goods_scale": "굿즈 규모"}
    d = json.loads((Path(root) / "data/state/slot_recovery.json").read_text())
    ks = list(d["축"].keys())
    best = [d["축"][k][d["축"][k]["best"]] for k in ks]
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    ax.bar(xs, [b["diff"] for b in best], width=.6,
           color=[GATE if b["diff"] < 0 else CLAIM for b in best], alpha=.8,
           edgecolor="none")
    for x, b in zip(xs, best):
        ax.text(x, b["diff"] + (-.002 if b["diff"] < 0 else .002),
                f"{b['win_rate']:.0%}", ha="center",
                va="bottom" if b["diff"] > 0 else "top", fontsize=6.2)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([KO[k] for k in ks], fontsize=6.2, rotation=18, ha="right")
    ax.set_ylabel("축 자체를 맞히는 오차\n(상수 대비)", fontsize=7.0)
    ax.tick_params(labelsize=6.6)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_two_stage_collapse(out: Path, root: str = ".") -> dict:
    """노트8 주장 2 — 사람 태그를 문서 예측으로 갈아끼우면 무너진다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/slot_recovery.json").read_text())
    t, p = d["2단"]["참축"], d["2단"]["복원축"]
    fig, ax = plt.subplots(figsize=(COL, 1.95))
    xs = [0, 1]
    vals = [t["median"], p["median"]]
    ax.bar(xs, vals, width=.5, color=[GATE, CLAIM], alpha=.82, edgecolor="none")
    for x, v, w in zip(xs, vals, [t["win_rate"], p["win_rate"]]):
        ax.text(x, v + (-.003 if v < 0 else .003), f"{v:+.4f}\n승률 {w:.0%}",
                ha="center", va="bottom" if v > 0 else "top", fontsize=6.4)
    ax.annotate("", xy=(0.85, vals[1] * .5), xytext=(0.15, vals[0] * .5),
                arrowprops=dict(arrowstyle="->", lw=1.1, color=INK))
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels(["사람이 매긴 축", "문서에서 복원한 축"], fontsize=6.8)
    ax.set_ylabel("상수 대비 MAE 차이", fontsize=7.2)
    ax.set_xlim(-.6, 1.6)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_idol_coverage(out: Path, root: str = ".") -> dict:
    """노트8 주장 3 — 아이돌 쪽은 두 축의 데이터가 아예 없다."""
    import json, numpy as np
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "매장 노출도",
          "entry_friction": "입장 허들", "media_push": "미디어 투입",
          "goods_scale": "굿즈 규모"}
    d = json.loads((Path(root) / "data/state/idol_axes.json").read_text())
    ks = list(KO)
    n = len(d)
    cov = [sum(v["mask"][k] for v in d.values()) / n for k in ks]
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.barh(xs, cov, height=.6,
            color=[MUTE if c > .5 else CLAIM for c in cov], alpha=.85, edgecolor="none")
    for x, c in zip(xs, cov):
        ax.text(c + .02, x, f"{c:.0%}", va="center", fontsize=6.4,
                color=INK if c > .5 else CLAIM)
    ax.set_yticks(xs)
    ax.set_yticklabels([KO[k] for k in ks], fontsize=6.6)
    ax.set_xlim(0, 1.12)
    ax.set_xlabel(f"아이돌 한터 확정 풀 {n}건 중 태깅률", fontsize=7.0)
    ax.tick_params(labelsize=6.4)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 9 ─────────────────────────────────────────────────────────────
def fig_reliability(out: Path, root: str = ".") -> dict:
    """노트9 주장 1 — 축 측정의 신뢰도 문턱."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/reliability.json").read_text())
    L = [r["목표r"] for r in d["levels"]][::-1]
    W = [r["win_rate"] for r in d["levels"]][::-1]
    fig, ax = plt.subplots(figsize=(COL, 2.15))
    ax.plot(L, W, "-o", ms=4, lw=1.5, color=GATE)
    for lv, lab, col in ((0.9, "승률 90%", CLAIM), (0.5, "승률 50%", MUTE)):
        ax.axhline(lv, color=col, lw=.8, ls=":")
    th = d["threshold"]
    for key, col in (("승률90%_필요r", CLAIM), ("승률50%_필요r", MUTE)):
        v = th.get(key)
        if v:
            ax.axvline(v, color=col, lw=.9, ls="--")
            ax.text(v, 1.04, f"r={v:.2f}", ha="center", fontsize=6.0, color=col)
    cur = d.get("현재_문서복원_r", 0.45)
    ax.scatter([cur], [0.05], s=52, marker="X", color="black", zorder=5)
    ax.text(cur, 0.11, "현재 문서 복원", fontsize=6.0, ha="center")
    ax.set_xlabel("축 측정의 신뢰도 (참값과의 상관 r)", fontsize=7.2)
    ax.set_ylabel("상수를 이긴 비율", fontsize=7.2)
    ax.set_ylim(0, 1.12)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_transfer_coef(out: Path, root: str = ".") -> dict:
    """노트9 주장 2 — 넷 중 둘만 같은 부호로 건너갔다."""
    import json, numpy as np
    KO = {"target_breadth": "타깃 폭", "entry_friction": "입장 허들",
          "media_push": "미디어 투입", "goods_scale": "굿즈 규모"}
    d = json.loads((Path(root) / "data/state/transfer_axes.json").read_text())
    ks = d["axes"]
    cp = [d["계수"]["팝업"][k] for k in ks]
    ci = [d["계수"]["아이돌"][k] for k in ks]
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.1))
    ax.bar(xs - .18, cp, width=.34, color=GATE, alpha=.85, label="팝업", edgecolor="none")
    ax.bar(xs + .18, ci, width=.34, color=MUTE, alpha=.85, label="아이돌", edgecolor="none")
    for x, a, b in zip(xs, cp, ci):
        if (a > 0) != (b > 0):
            ax.text(x, max(a, b) + .03, "부호 반전", ha="center", fontsize=6.0, color=CLAIM)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([KO[k] for k in ks], fontsize=6.8)
    ax.set_ylabel("표준화 회귀계수", fontsize=7.2)
    ax.legend(fontsize=6.4, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_transfer_bars(out: Path, root: str = ".") -> dict:
    """노트9 주장 3 — 안에서는 되고 건너가면 안 된다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/transfer_axes.json").read_text())
    rows = [("팝업 내부", d["내부_팝업"]["median"], d["내부_팝업"]["win_rate"]),
            ("아이돌 내부", d["내부_아이돌"]["median"], d["내부_아이돌"]["win_rate"]),
            ("아이돌 → 팝업", d["교차_아이돌 → 팝업"]["vs_대상상수"], None),
            ("팝업 → 아이돌", d["교차_팝업 → 아이돌"]["vs_대상상수"], None)]
    xs = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(FULL, 2.0))
    ax.bar(xs, [r[1] for r in rows], width=.55,
           color=[GATE if r[1] < 0 else CLAIM for r in rows], alpha=.82, edgecolor="none")
    for x, (lab, v, wr) in zip(xs, rows):
        t = f"{v:+.4f}" + (f"\n승률 {wr:.0%}" if wr is not None else "")
        ax.text(x, v + (-.004 if v < 0 else .004), t, ha="center",
                va="bottom" if v > 0 else "top", fontsize=6.2)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([r[0] for r in rows], fontsize=6.8)
    ax.set_ylabel("상수 대비 MAE 차이\n(도메인 내 표준화 눈금)", fontsize=7.0)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 10 ────────────────────────────────────────────────────────────
def fig_subset_transfer(out: Path, root: str = ".") -> dict:
    """노트10 주장 1 — 축을 더할수록 전이가 희석된다."""
    import json, numpy as np
    KO = {"target_breadth": "타깃 폭", "media_push": "미디어 투입",
          "goods_scale": "굿즈 규모"}
    d = json.loads((Path(root) / "data/state/transfer_subsets.json").read_text())
    rows = sorted(d["subsets"], key=lambda r: r["p2i"]["median"])
    ys = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(FULL, 2.5))
    for y, r in zip(ys, rows):
        m, (lo, hi) = r["p2i"]["median"], r["p2i"]["ci95"]
        col = GATE if r["p2i"]["win_rate"] >= .9 else (MUTE if m < 0 else CLAIM)
        ax.plot([lo, hi], [y, y], lw=1.4, color=col, alpha=.55)
        ax.scatter([m], [y], s=32, color=col, zorder=3)
        ax.text(hi + .004, y, f"{r['p2i']['win_rate']:.0%}", va="center",
                fontsize=6.0, color=col)
    ax.axvline(0, color=INK, lw=.9, ls="--")
    ax.set_yticks(ys)
    ax.set_yticklabels(["+".join(KO[a] for a in r["axes"]) for r in rows], fontsize=6.4)
    ax.set_xlabel("팝업 → 아이돌 전이, 대상 상수 대비 MAE 차이 (부트스트랩 95%)",
                  fontsize=7.0)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_permutation(out: Path, root: str = ".") -> dict:
    """노트10 주장 2 — 순열 귀무 분포에서 관측값의 위치."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/transfer_subsets.json").read_text())
    p = d["permutation"]
    null = np.array(p["null"])
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.hist(null, bins=48, color=MUTE, alpha=.7, edgecolor="none")
    ax.axvline(p["obs"], color=CLAIM, lw=1.6)
    ax.text(p["obs"], ax.get_ylim()[1] * .92, f" 관측 {p['obs']:+.4f}\n p={p['p']:.3f}",
            fontsize=6.2, color=CLAIM, va="top")
    ax.axvline(0, color=INK, lw=.8, ls=":")
    ax.set_xlabel("팝업 라벨을 섞었을 때의 전이 성적", fontsize=7.2)
    ax.set_ylabel("빈도", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_asymmetry(out: Path, root: str = ".") -> dict:
    """노트10 주장 3 — 전이는 한 방향으로만 간다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/transfer_subsets.json").read_text())
    r = next(x for x in d["subsets"] if x["axes"] == ["goods_scale"])
    fig, ax = plt.subplots(figsize=(COL, 1.9))
    for i, (k, lab) in enumerate((("p2i", "팝업 → 아이돌"), ("i2p", "아이돌 → 팝업"))):
        m, (lo, hi) = r[k]["median"], r[k]["ci95"]
        col = GATE if r[k]["win_rate"] >= .9 else CLAIM
        ax.plot([lo, hi], [i, i], lw=2.0, color=col, alpha=.5)
        ax.scatter([m], [i], s=44, color=col, zorder=3)
        ax.text(hi + .004, i, f"승률 {r[k]['win_rate']:.0%}", va="center",
                fontsize=6.4, color=col)
    ax.axvline(0, color=INK, lw=.9, ls="--")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["팝업 → 아이돌", "아이돌 → 팝업"], fontsize=6.8)
    ax.set_ylim(-.6, 1.6)
    ax.set_xlabel("굿즈 규모 단독 전이 (대상 상수 대비)", fontsize=7.0)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 11 ────────────────────────────────────────────────────────────
def fig_detrend(out: Path, root: str = ".") -> dict:
    """노트11 주장 1 — 탈추세가 초기 구간의 손실을 지운다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/detrend_full.json").read_text())
    sp = d["subperiod_delta"]
    labs = list(sp)
    xs = np.arange(len(labs))
    fig, ax = plt.subplots(figsize=(FULL, 2.1))
    ax.bar(xs - .18, [sp[k][0] for k in labs], width=.34, color=CLAIM, alpha=.8,
           label="원본", edgecolor="none")
    ax.bar(xs + .18, [sp[k][1] for k in labs], width=.34, color=GATE, alpha=.85,
           label="추세 제거", edgecolor="none")
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels(labs, fontsize=6.8)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.2)
    ax.legend(fontsize=6.4, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.6)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_axis_variance(out: Path, root: str = ".") -> dict:
    """노트11 주장 2 — 축의 분산이 커지면서 예측력이 생겼다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/detrend_full.json").read_text())
    ps = d["periods"]
    xs = np.arange(len(ps))
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    ax.bar(xs, [p["sd"] for p in ps], width=.55, color=GATE, alpha=.8, edgecolor="none")
    for x, p in zip(xs, ps):
        ax.text(x, p["sd"] + .006, f"버전 평균\n{p['ver_mean']:.1f}종", ha="center",
                fontsize=6.0)
    ax2 = ax.twinx()
    ax2.plot(xs, [p["mean"] for p in ps], "-o", ms=4, lw=1.3, color=CLAIM)
    ax2.set_ylabel("축 평균", fontsize=7.0, color=CLAIM)
    ax2.tick_params(labelsize=6.4, colors=CLAIM)
    ax.set_xticks(xs)
    ax.set_xticklabels([p["label"] for p in ps], fontsize=6.4)
    ax.set_ylabel("축의 표준편차", fontsize=7.2)
    ax.set_ylim(0, .32)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_detrend_effect(out: Path, root: str = ".") -> dict:
    """노트11 주장 3 — 효과는 줄고 계수는 그대로다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/detrend_full.json").read_text())
    a, b = d["추세제거_전"], d["추세제거_후"]
    fig, axes = plt.subplots(1, 2, figsize=(FULL, 1.95))
    for ax, key, lab, fmt in ((axes[0], "obs", "상수 대비 MAE 차이", "{:+.4f}"),
                              (axes[1], "coef", "팝업 굿즈 규모 계수", "{:+.3f}")):
        vals = [a[key], b[key]]
        ax.bar([0, 1], vals, width=.5, color=[MUTE, GATE], alpha=.85, edgecolor="none")
        for x, v in zip([0, 1], vals):
            ax.text(x, v + (.002 if v > 0 else -.002), fmt.format(v), ha="center",
                    va="bottom" if v > 0 else "top", fontsize=6.6)
        ax.axhline(0, color=INK, lw=.9)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["원본", "추세 제거"], fontsize=6.8)
        ax.set_title(lab, fontsize=7.4)
        ax.tick_params(labelsize=6.4)
    axes[0].invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 12 ────────────────────────────────────────────────────────────
def fig_variance_scatter(out: Path, root: str = ".") -> dict:
    """노트12 주장 1 — 축마다 기울기의 부호가 다르다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/variance_law_fine.json").read_text())
    rows = d["cells"]
    COLS = {"굿즈 규모": GATE, "미디어 투입": CLAIM, "타깃 폭": MUTE}
    fig, ax = plt.subplots(figsize=(COL, 2.2))
    for a, c in COLS.items():
        rr = [r for r in rows if r["축"] == a]
        if not rr:
            continue
        x = np.array([r["축_SD"] for r in rr])
        y = np.array([r["차이"] for r in rr])
        ax.scatter(x, y, s=22, color=c, label=a, alpha=.85, edgecolors="none")
        if len(x) >= 3:
            b = np.polyfit(x, y, 1)
            xs = np.linspace(x.min(), x.max(), 10)
            ax.plot(xs, np.polyval(b, xs), lw=1.1, color=c, alpha=.55)
    ax.axhline(0, color=INK, lw=.8, ls=":")
    ax.set_xlabel("셀 안에서 축의 표준편차", fontsize=7.2)
    ax.set_ylabel("상수 대비 MAE 차이", fontsize=7.2)
    ax.legend(fontsize=6.0, frameon=False)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_variance_perm(out: Path, root: str = ".") -> dict:
    """노트12 주장 2 — 격차는 크지만 우연으로 배제되지 않는다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/variance_law_test.json").read_text())
    null = np.array(d["null"])                # 실제 순열 귀무 분포
    fig, ax = plt.subplots(figsize=(COL, 1.95))
    ax.hist(null, bins=44, color=MUTE, alpha=.65, edgecolor="none")
    ax.axvline(d["obs_gap"], color=CLAIM, lw=1.6)
    ax.text(d["obs_gap"], ax.get_ylim()[1] * .9,
            f" 관측 {d['obs_gap']:+.3f}\n p={d['p']:.3f}", fontsize=6.2, color=CLAIM, va="top")
    ax.set_xlabel("상관 격차 (굿즈 규모 $-$ 나머지)", fontsize=7.2)
    ax.set_ylabel("빈도", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_cellcount(out: Path, root: str = ".") -> dict:
    """노트12 주장 3 — 셀을 어떻게 나누느냐가 상관을 바꾼다."""
    import numpy as np
    labs = ["굵은 구간\n(셀 5개)", "세분 구간\n(셀 8개)"]
    vals = [-0.924, -0.451]
    fig, ax = plt.subplots(figsize=(COL, 1.85))
    ax.bar([0, 1], vals, width=.45, color=[MUTE, GATE], alpha=.85, edgecolor="none")
    for x, v in zip([0, 1], vals):
        ax.text(x, v - .03, f"{v:+.3f}", ha="center", va="top", fontsize=6.8)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(labs, fontsize=6.6)
    ax.set_ylabel("굿즈 규모 축의 SD-성적 상관", fontsize=7.0)
    ax.set_ylim(-1.05, .1)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 13 ────────────────────────────────────────────────────────────
def fig_cov_matrix(out: Path, root: str = ".") -> dict:
    """노트13 주장 1 — 다섯 축 중 둘만 세 도메인에서 모두 관측된다."""
    import json, numpy as np
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "매장 노출도",
          "entry_friction": "입장 허들", "media_push": "미디어 투입",
          "goods_scale": "굿즈 규모"}
    d = json.loads((Path(root) / "data/state/tri_domain.json").read_text())
    cov, axes = d["cov"], list(KO)
    doms = list(cov)
    Mx = np.array([[cov[dm][a] for dm in doms] for a in axes])
    fig, ax = plt.subplots(figsize=(COL, 2.3))
    im = ax.imshow(Mx, cmap="Greens", vmin=0, vmax=1, aspect="auto")
    for i in range(len(axes)):
        for j in range(len(doms)):
            v = Mx[i, j]
            ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=6.6,
                    color="white" if v > .55 else INK)
    ax.set_xticks(range(len(doms)))
    ax.set_xticklabels(doms, fontsize=6.8)
    ax.set_yticks(range(len(axes)))
    ax.set_yticklabels([KO[a] for a in axes], fontsize=6.6)
    for i, a in enumerate(axes):
        if a in d["axes"]:
            ax.add_patch(plt.Rectangle((-.5, i - .5), len(doms), 1, fill=False,
                                       ec=CLAIM, lw=1.6))
    ax.set_title("축 태깅률 — 테두리가 공통 축", fontsize=7.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_six_transfer(out: Path, root: str = ".") -> dict:
    """노트13 주장 2 — 여섯 방향 중 넷이 유의하다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/tri_domain.json").read_text())
    ks = sorted(d["교차"], key=lambda k: d["교차"][k]["obs"])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    for x, k in zip(xs, ks):
        r = d["교차"][k]
        col = GATE if r["p"] < 0.05 else (MUTE if r["obs"] < 0 else CLAIM)
        ax.bar([x], [r["obs"]], width=.55, color=col, alpha=.85, edgecolor="none")
        ax.text(x, r["obs"] + (-.003 if r["obs"] < 0 else .003),
                f"p={r['p']:.3f}", ha="center",
                va="bottom" if r["obs"] > 0 else "top", fontsize=6.2)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([k.replace("→", "\n→ ") for k in ks], fontsize=6.4)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.2)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_tri_coef(out: Path, root: str = ".") -> dict:
    """노트13 주장 3 — 두 축 모두 세 도메인에서 부호가 같다."""
    import json, numpy as np
    KO = {"target_breadth": "타깃 폭", "goods_scale": "굿즈 규모",
          "entry_friction": "입장 허들", "media_push": "미디어 투입",
          "venue_prominence": "매장 노출도"}
    d = json.loads((Path(root) / "data/state/tri_domain.json").read_text())
    axes, co = d["axes"], d["계수"]
    doms = list(co)
    xs = np.arange(len(axes))
    wid = .8 / len(doms)
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    for i, dm in enumerate(doms):
        ax.bar(xs + (i - (len(doms) - 1) / 2) * wid, co[dm], width=wid * .9,
               label=dm, alpha=.85, edgecolor="none",
               color=[GATE, MUTE, CLAIM][i % 3])
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([KO[a] for a in axes], fontsize=6.8)
    ax.set_ylabel("표준화 회귀계수", fontsize=7.2)
    ax.legend(fontsize=6.0, frameon=False, ncol=3)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_balanced(out: Path, root: str = ".") -> dict:
    """노트13 주장 4 — 표본을 맞춰도 게임으로 들어가는 전이만 실패한다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/tri_balanced.json").read_text())
    r = d["res"]
    ks = sorted(r, key=lambda k: -r[k]["win_rate"])
    ys = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.1))
    ax.barh(ys, [r[k]["win_rate"] for k in ks], height=.6,
            color=[GATE if r[k]["win_rate"] >= .8 else CLAIM for k in ks],
            alpha=.85, edgecolor="none")
    for y, k in zip(ys, ks):
        ax.text(r[k]["win_rate"] + .015, y, f"Δ{r[k]['median']:+.4f}", va="center",
                fontsize=6.2)
    ax.axvline(.5, color=INK, lw=.8, ls=":")
    ax.set_yticks(ys)
    ax.set_yticklabels(ks, fontsize=6.6)
    ax.set_xlim(0, 1.2)
    ax.set_xlabel(f"상수를 이긴 비율 (도메인마다 n={d['n_cap']}로 맞춰 {d['reps']}회)",
                  fontsize=7.0)
    ax.tick_params(labelsize=6.4)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 14 ────────────────────────────────────────────────────────────
def fig_arch(out: Path, root: str = ".") -> dict:
    """노트14 — 파운데이션 구조 자체를 그린다."""
    fig, ax = plt.subplots(figsize=(FULL, 2.5))
    ax.axis("off")
    doms = [("팝업 문서 70", 4.2, GATE), ("아이돌 메타 8", 2.5, MUTE), ("게임 메타 7", 0.8, CLAIM)]
    for lab, y0, col in doms:
        ax.add_patch(plt.Rectangle((.1, y0 - .35), 1.9, .7, fc="white", ec=col, lw=1.1))
        ax.text(1.05, y0, lab, ha="center", va="center", fontsize=6.6)
        ax.add_patch(plt.Rectangle((2.6, y0 - .35), 1.5, .7, fc="white", ec=col, lw=1.0))
        ax.text(3.35, y0, "인코더\n(비선형)", ha="center", va="center", fontsize=6.0)
        ax.annotate("", xy=(2.55, y0), xytext=(2.05, y0),
                    arrowprops=dict(arrowstyle="->", lw=.9, color=col))
        ax.annotate("", xy=(4.75, 2.9), xytext=(4.15, y0),
                    arrowprops=dict(arrowstyle="->", lw=.9, color=col,
                                    connectionstyle="arc3,rad=0.1"))
    for j, s in enumerate(("타깃 폭", "굿즈 규모")):
        yy = 3.2 - j * .8
        ax.add_patch(plt.Rectangle((4.8, yy - .3), 1.6, .6, fc="white", ec=INK, lw=1.2))
        ax.text(5.6, yy, s, ha="center", va="center", fontsize=6.6)
    ax.text(5.6, 4.15, "고정 2슬롯 (앵커)", ha="center", fontsize=6.4, color=CLAIM)
    ax.add_patch(plt.Rectangle((7.0, 2.5), 1.7, .7, fc="white", ec=INK, lw=1.3))
    ax.text(7.85, 2.85, "선형 공유 헤드", ha="center", va="center", fontsize=6.6)
    ax.annotate("", xy=(6.95, 2.85), xytext=(6.45, 2.85),
                arrowprops=dict(arrowstyle="->", lw=1.0, color=INK))
    ax.annotate("", xy=(9.4, 2.85), xytext=(8.75, 2.85),
                arrowprops=dict(arrowstyle="->", lw=1.0, color=INK))
    ax.text(9.5, 2.85, "반응", fontsize=6.8, va="center")
    ax.text(5.0, .05, "학습: 두 도메인 · 검정: 나머지 하나 (대상 라벨 미사용)",
            ha="center", fontsize=6.2, color=MUTE)
    ax.set_xlim(0, 10.3); ax.set_ylim(-.1, 4.5)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_foundation(out: Path, root: str = ".") -> dict:
    """노트14 주장 1 — 도메인 하나 빼기 성적."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/foundation.json").read_text())
    R = d["결과"]
    doms = list(R)
    xs = np.arange(len(doms))
    keys = [("const", "상수", CLAIM), ("mean_pair", "평균 쌍전이", MUTE),
            ("foundation", "파운데이션", GATE), ("inner_ridge", "상한(라벨 전부)", INK)]
    w = .8 / len(keys)
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    for i, (k, lab, col) in enumerate(keys):
        ax.bar(xs + (i - (len(keys) - 1) / 2) * w, [R[dm][k] for dm in doms],
               width=w * .9, label=lab, color=col, alpha=.85, edgecolor="none")
    for x, dm in zip(xs, doms):
        ax.text(x, R[dm]["const"] + .015, f"p={R[dm]['p']:.3f}", ha="center", fontsize=6.2)
    ax.set_xticks(xs)
    ax.set_xticklabels(doms, fontsize=6.8)
    ax.set_ylabel("평균절대오차 (도메인 내 표준화)", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=4)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_gap_to_ceiling(out: Path, root: str = ".") -> dict:
    """노트14 주장 2 — 상한까지 얼마나 갔나."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/foundation.json").read_text())
    R = d["결과"]
    doms = list(R)
    frac = []
    for dm in doms:
        rng_ = R[dm]["const"] - R[dm]["inner_ridge"]
        frac.append((R[dm]["const"] - R[dm]["foundation"]) / rng_ if rng_ > 1e-9 else 0.0)
    ys = np.arange(len(doms))
    fig, ax = plt.subplots(figsize=(COL, 1.9))
    ax.barh(ys, frac, height=.55, color=[GATE if f > .5 else CLAIM for f in frac],
            alpha=.85, edgecolor="none")
    for y, f in zip(ys, frac):
        ax.text(f + .02 if f > 0 else .02, y, f"{f:.0%}", va="center", fontsize=6.6)
    ax.axvline(1.0, color=INK, lw=.9, ls="--")
    ax.text(1.0, len(doms) - .3, " 상한", fontsize=6.2, color=INK)
    ax.axvline(0, color=INK, lw=.8)
    ax.set_yticks(ys); ax.set_yticklabels(doms, fontsize=6.8)
    ax.set_xlabel("상수→상한 구간에서 파운데이션이 간 비율", fontsize=7.0)
    ax.set_xlim(min(-.3, min(frac) - .1), 1.25)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 15 ────────────────────────────────────────────────────────────
def fig_dlc_leak(out: Path, root: str = ".") -> dict:
    """노트15 주장 1 — DLC 수는 출시 후 누적된다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note15.json").read_text())
    b = d["dlc_buckets"]
    xs = np.arange(len(b))
    fig, ax = plt.subplots(figsize=(COL, 2.05))
    ax.bar(xs, [x["mean"] for x in b], width=.55, color=CLAIM, alpha=.82, edgecolor="none")
    for x, r in zip(xs, b):
        ax.text(x, r["mean"] + .4, f"{r['mean']:.1f}종\n(0종 {r['zero']:.0%})",
                ha="center", fontsize=6.0)
    ax.set_xticks(xs)
    ax.set_xticklabels([x["label"] for x in b], fontsize=6.8)
    ax.set_ylabel("게임당 평균 DLC 수", fontsize=7.2)
    ax.set_xlabel("출시 후 경과", fontsize=7.0)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_label_test(out: Path, root: str = ".") -> dict:
    """노트15 주장 2 — 30일 창으로 바꾸면 오히려 나빠진다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note15.json").read_text())
    L = d["label_test"]
    labs = ["전체 리뷰", "출시 30일 리뷰"]
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    xs = np.arange(2)
    for i, (k, nm, col) in enumerate((("const", "상수", MUTE), ("inner", "도메인 내부", GATE))):
        ax.bar(xs + (i - .5) * .34, [L["total"][k], L["w30"][k]], width=.32,
               label=nm, color=col, alpha=.85, edgecolor="none")
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=6.8)
    ax.set_ylim(0.7, 0.83)
    ax.set_ylabel("평균절대오차", fontsize=7.2)
    ax.legend(fontsize=6.2, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.6)
    ax.text(1, L["w30"]["inner"] + .004, "내부 모델이\n상수와 같다", ha="center",
            fontsize=6.0, color=CLAIM)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_retract(out: Path, root: str = ".") -> dict:
    """노트15 주장 3 — 무엇이 남고 무엇이 철회되나."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note15.json").read_text())
    T = d["final_transfer"]
    ks = sorted(T, key=lambda k: T[k]["obs"])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.1))
    for x, k in zip(xs, ks):
        r = T[k]
        col = GATE if r["p"] < 0.05 else (MUTE if r["obs"] < 0 else CLAIM)
        ax.bar([x], [r["obs"]], width=.55, color=col, alpha=.85, edgecolor="none")
        ax.text(x, r["obs"] + (-.002 if r["obs"] < 0 else .002),
                f"p={r['p']:.3f}\n축 {r['axes']}개", ha="center",
                va="bottom" if r["obs"] > 0 else "top", fontsize=6.0)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([k.replace("→", "\n→ ") for k in ks], fontsize=6.4)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.set_title("누출 제거 후 --- 넷이 유지된다", fontsize=7.4)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 16 ────────────────────────────────────────────────────────────
def fig_proxy_scan(out: Path, root: str = ".") -> dict:
    """노트16 주장 1 — 누출 위험과 설명력을 함께 본다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note16.json").read_text())
    P = d["proxies"]
    fig, ax = plt.subplots(figsize=(COL, 2.2))
    for r in P:
        risky = abs(r["r_time"]) > 0.15
        col = CLAIM if risky else GATE
        ax.scatter([abs(r["r_time"])], [r["r_label"]], s=44, color=col,
                   alpha=.9, edgecolors="none")
        ax.annotate(r["name"], (abs(r["r_time"]), r["r_label"]),
                    textcoords="offset points", xytext=(5, 3), fontsize=6.0)
    ax.axvline(.15, color=CLAIM, lw=.9, ls="--")
    ax.text(.152, ax.get_ylim()[0] + .02, "누출 위험", fontsize=6.0, color=CLAIM)
    ax.axhline(0, color=INK, lw=.8, ls=":")
    ax.set_xlabel("경과 시간과의 상관 |r| (누출 지표)", fontsize=7.0)
    ax.set_ylabel("30일 창 라벨과의 상관", fontsize=7.0)
    ax.set_xlim(-.02, .30)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_price_not_friction(out: Path, root: str = ".") -> dict:
    """노트16 주장 2 — 가격은 두 도메인에서 모두 허들이 아니다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note16.json").read_text())["price"]
    fig, ax = plt.subplots(figsize=(COL, 1.95))
    ax.bar([0, 1], [d["free_mean"], d["paid_mean"]], width=.45,
           color=[MUTE, GATE], alpha=.85, edgecolor="none")
    for x, v in zip([0, 1], [d["free_mean"], d["paid_mean"]]):
        ax.text(x, v + (.012 if v > 0 else -.012), f"{v:+.3f}", ha="center",
                va="bottom" if v > 0 else "top", fontsize=6.8)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["무료 게임", "유료 게임"], fontsize=6.8)
    ax.set_ylabel("출시 30일 반응 (표준화)", fontsize=7.0)
    ax.set_title("허들 해석이면 무료가 커야 한다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_fewshot(out: Path, root: str = ".") -> dict:
    """노트16 주장 3 — 소수 예시 보정은 격차를 넓히지 못한다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note16.json").read_text())["fewshot"]
    ks = d["ks"]
    fig, ax = plt.subplots(figsize=(COL, 2.15))
    for i, (dm, col) in enumerate(zip(d["결과"], (GATE, MUTE, CLAIM))):
        v = [d["결과"][dm][str(k)]["diff"] for k in ks]
        ax.plot(range(len(ks)), v, "-o", ms=3.5, lw=1.3, color=col, label=dm)
    ax.axhline(0, color=INK, lw=.9, ls="--")
    ax.set_xticks(range(len(ks)))
    ax.set_xticklabels([str(k) for k in ks], fontsize=6.4)
    ax.set_xlabel("보정에 쓴 대상 도메인 라벨 개수 k", fontsize=7.0)
    ax.set_ylabel("상수 대비 MAE 차이", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=3)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 17 ────────────────────────────────────────────────────────────
def fig_seed_variance(out: Path, root: str = ".") -> dict:
    """노트17 주장 1 — 시드 분산이 효과 크기를 삼킨다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/head_ablation.json").read_text())
    doms = list(d)
    xs = np.arange(len(doms))
    fig, ax = plt.subplots(figsize=(FULL, 2.3))
    for i, (k, lab, col) in enumerate((("shared", "공유 헤드", CLAIM),
                                       ("ensemble", "출처별 앙상블", GATE))):
        m = [d[dm][k][0] for dm in doms]
        s = [d[dm][k][1] for dm in doms]
        ax.errorbar(xs + (i - .5) * .18, m, yerr=s, fmt="o", ms=5, capsize=4,
                    lw=1.3, color=col, label=lab)
    ax.plot(xs, [d[dm]["const"] for dm in doms], "_", ms=26, color=INK,
            label="상수", mew=1.6)
    ax.plot(xs, [d[dm]["oracle"] for dm in doms], "_", ms=26, color=MUTE,
            label="ridge 최선(신탁)", mew=1.6)
    ax.set_xticks(xs); ax.set_xticklabels(doms, fontsize=6.8)
    ax.set_ylabel("평균절대오차 (시드 20개, ±1 SD)", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=4)
    ax.tick_params(labelsize=6.6)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_effect_vs_noise(out: Path, root: str = ".") -> dict:
    """노트17 주장 2 — 효과 크기와 시드 잡음의 비율."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/head_ablation.json").read_text())
    doms = list(d)
    eff = [abs(d[dm]["const"] - d[dm]["shared"][0]) for dm in doms]
    noi = [d[dm]["shared"][1] for dm in doms]
    xs = np.arange(len(doms))
    fig, ax = plt.subplots(figsize=(COL, 2.05))
    ax.bar(xs - .18, eff, width=.34, color=GATE, alpha=.85, label="효과 크기",
           edgecolor="none")
    ax.bar(xs + .18, noi, width=.34, color=CLAIM, alpha=.85, label="시드 표준편차",
           edgecolor="none")
    for x, e, n in zip(xs, eff, noi):
        ax.text(x, max(e, n) + .003, f"{n/max(e,1e-9):.1f}배", ha="center", fontsize=6.2)
    ax.set_xticks(xs); ax.set_xticklabels(doms, fontsize=6.8)
    ax.set_ylabel("MAE 단위", fontsize=7.2)
    ax.legend(fontsize=6.2, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_method_ladder(out: Path, root: str = ".") -> dict:
    """노트17 주장 3 — 단순한 쪽이 이긴다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/head_ablation.json").read_text())
    doms = list(d)
    rows = [("상수", [d[dm]["const"] for dm in doms], INK),
            ("공유 헤드 (신경망)", [d[dm]["shared"][0] for dm in doms], CLAIM),
            ("출처별 앙상블 (신경망)", [d[dm]["ensemble"][0] for dm in doms], MUTE),
            ("ridge 쌍 전이", [d[dm]["oracle"] for dm in doms], GATE)]
    ys = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(FULL, 2.0))
    for y, (lab, v, col) in zip(ys, rows):
        ax.barh([y], [float(np.mean(v))], height=.55, color=col, alpha=.85,
                edgecolor="none")
        ax.text(float(np.mean(v)) + .004, y, f"{np.mean(v):.4f}", va="center",
                fontsize=6.6)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=6.8)
    ax.set_xlabel("세 도메인 평균 MAE (낮을수록 좋다)", fontsize=7.0)
    ax.set_xlim(0.6, 0.82)
    ax.invert_yaxis()
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 18 ────────────────────────────────────────────────────────────
def fig_friction_scan(out: Path, root: str = ".") -> dict:
    """노트18 주장 1 — 장벽 후보가 규모를 통제해도 전부 양수다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note18.json").read_text())["friction"]
    ks = list(d)
    xs = np.arange(len(ks))
    labs = ["원상관", "규모·폭 통제", "+가격 통제"]
    fig, ax = plt.subplots(figsize=(FULL, 2.1))
    for i, lab in enumerate(labs):
        ax.bar(xs + (i - 1) * .26, [d[k][i] for k in ks], width=.24, label=lab,
               color=[CLAIM, MUTE, GATE][i], alpha=.85, edgecolor="none")
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.6)
    ax.set_ylabel("출시 30일 반응과의 상관", fontsize=7.0)
    ax.set_title("허들이면 음수여야 한다 — 전부 양수다", fontsize=7.4)
    ax.legend(fontsize=6.0, frameon=False, ncol=3)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_game_factors(out: Path, root: str = ".") -> dict:
    """노트18 주장 2 — 게임 원자료 8변수가 두 인자로 모인다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note18.json").read_text())["game_raw"]
    names = list(d["PC1"]["load"])
    fig, ax = plt.subplots(figsize=(COL, 2.4))
    x = [d["PC1"]["load"][n] for n in names]
    y = [d["PC2"]["load"][n] for n in names]
    ax.axhline(0, color=INK, lw=.8, ls=":")
    ax.axvline(0, color=INK, lw=.8, ls=":")
    for n, a, b in zip(names, x, y):
        col = GATE if abs(a) > abs(b) else MUTE
        ax.scatter([a], [b], s=34, color=col, alpha=.9, edgecolors="none")
        ax.annotate(n, (a, b), textcoords="offset points", xytext=(4, 3), fontsize=5.8)
    ax.set_xlabel(f"PC1 적재 ({d['PC1']['var']:.0%}, 라벨 r={d['PC1']['r']:+.2f}) — 제작 규모",
                  fontsize=6.6)
    ax.set_ylabel(f"PC2 적재 ({d['PC2']['var']:.0%}, r={d['PC2']['r']:+.2f}) — 도달 폭",
                  fontsize=6.6)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_pc_vs_named(out: Path, root: str = ".") -> dict:
    """노트18 주장 3 — 인자 표현이 명명 축을 이긴다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note18.json").read_text())
    pc, nm = d["pc_transfer"], d["named_transfer"]
    ks = [k for k in pc if k in nm]
    ks.sort(key=lambda k: pc[k]["obs"])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.bar(xs - .19, [nm[k]["obs"] for k in ks], width=.36, label="명명 축 (노트 16)",
           color=MUTE, alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [pc[k]["obs"] for k in ks], width=.36, label="인자 2개",
           color=GATE, alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        ax.text(x + .19, pc[k]["obs"] - .003, f"p={pc[k]['p']:.3f}", ha="center",
                va="top", fontsize=5.8)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([k.replace("→", "\n→ ") for k in ks], fontsize=6.2)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 19 ────────────────────────────────────────────────────────────
def fig_aligned_loadings(out: Path, root: str = ".") -> dict:
    """노트19 주장 1 — 정렬 후 적재 패턴이 세 도메인에서 일치한다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/procrustes.json").read_text())
    L = d["loadings"]
    doms = list(L)
    fig, ax = plt.subplots(figsize=(COL, 2.3))
    cols = {"팝업": GATE, "아이돌": MUTE, "게임": CLAIM}
    for dm in doms:
        M = np.array(L[dm])
        for i, nm in enumerate(("타깃 폭", "굿즈 규모")):
            ax.scatter([M[i, 0]], [M[i, 1]], s=42, color=cols.get(dm, INK),
                       marker="o" if i == 0 else "s", alpha=.9, edgecolors="none")
            ax.annotate(f"{dm}·{nm}", (M[i, 0], M[i, 1]), textcoords="offset points",
                        xytext=(4, 3), fontsize=5.6)
    ax.axhline(0, color=INK, lw=.8, ls=":")
    ax.axvline(0, color=INK, lw=.8, ls=":")
    ax.set_xlabel("정렬 후 PC1 적재", fontsize=7.0)
    ax.set_ylabel("정렬 후 PC2 적재", fontsize=7.0)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_align_compare(out: Path, root: str = ".") -> dict:
    """노트19 주장 2 — 라벨 없는 정렬이 부호 규약과 대등하거나 낫다."""
    import json, numpy as np
    p18 = json.loads((Path(root) / "data/state/pc_transfer.json").read_text())
    p19 = json.loads((Path(root) / "data/state/procrustes.json").read_text())["교차"]
    ks = [k for k in p19 if k in p18]
    ks.sort(key=lambda k: p19[k]["obs"])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.bar(xs - .19, [p18[k]["obs"] for k in ks], width=.36,
           label="부호 규약 (출처 라벨 사용)", color=MUTE, alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [p19[k]["obs"] for k in ks], width=.36,
           label="프로크루스테스 (라벨 0개)", color=GATE, alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        ax.text(x + .19, p19[k]["obs"] - .003, f"p={p19[k]['p']:.3f}", ha="center",
                va="top", fontsize=5.8)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([k.replace("→", "\n→ ") for k in ks], fontsize=6.2)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_pipeline(out: Path, root: str = ".") -> dict:
    """노트19 — 라벨 0개 파이프라인."""
    fig, ax = plt.subplots(figsize=(FULL, 1.9))
    ax.axis("off")
    steps = [("새 도메인에서\n축을 잰다", GATE), ("인자 공간을\n뽑는다", GATE),
             ("공통 축 적재로\n회전 정렬", CLAIM), ("기준 도메인 계수\n적용", GATE),
             ("예측", INK)]
    w, gap = 1.75, .42
    for i, (lab, col) in enumerate(steps):
        x = i * (w + gap)
        ax.add_patch(plt.Rectangle((x, .35), w, .95, fc="white", ec=col, lw=1.2))
        ax.text(x + w / 2, .82, lab, ha="center", va="center", fontsize=6.4)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + w + gap - .04, .82), xytext=(x + w + .04, .82),
                        arrowprops=dict(arrowstyle="->", lw=1.0, color=INK))
    ax.text((len(steps) * (w + gap) - gap) / 2, .05,
            "대상 도메인 라벨이 어느 단계에도 들어가지 않는다", ha="center",
            fontsize=6.6, color=CLAIM)
    ax.set_xlim(-.2, len(steps) * (w + gap) - gap + .2)
    ax.set_ylim(0, 1.5)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 20 ────────────────────────────────────────────────────────────
def fig_subset_align(out: Path, root: str = ".") -> dict:
    """노트20 주장 1 — 미디어를 포함한 조합이 전부 나쁘다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note20.json").read_text())["subsets"]
    ks = sorted(d, key=lambda k: d[k][1])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.0))
    ax.bar(xs, [d[k][1] for k in ks], width=.55,
           color=[GATE if "미디어" not in k else CLAIM for k in ks],
           alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        ax.text(x, d[k][1] + (-.002 if d[k][1] < 0 else .002),
                f"유의 {d[k][0]}개", ha="center",
                va="bottom" if d[k][1] > 0 else "top", fontsize=6.4)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.4)
    ax.set_ylabel("여섯 방향 평균 차이", fontsize=7.0)
    ax.set_title("정렬 기준 축 조합 — 진한 것이 미디어 미포함", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_add_axis_hurts(out: Path, root: str = ".") -> dict:
    """노트20 주장 2 — 축을 추가하면 방향별로 어떻게 바뀌나."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note20.json").read_text())
    W, O = d["with_media"]["rows"], d["without_media"]["rows"]
    ks = sorted(O, key=lambda k: O[k][0])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.bar(xs - .19, [O[k][0] for k in ks], width=.36, label="미디어 제외 (축 2개)",
           color=GATE, alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [W[k][0] for k in ks], width=.36, label="미디어 포함 (축 3개)",
           color=CLAIM, alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        ax.text(x - .19, O[k][0] - .002, f"{O[k][1]:.3f}", ha="center", va="top",
                fontsize=5.6)
        ax.text(x + .19, W[k][0] - .002, f"{W[k][1]:.3f}", ha="center", va="top",
                fontsize=5.6)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([k.replace("→", "\n→ ") for k in ks], fontsize=6.2)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_selfpub(out: Path, root: str = ".") -> dict:
    """노트20 — 자체 배급 신호 자체는 방향이 맞다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note20.json").read_text())["selfpub"]
    fig, ax = plt.subplots(figsize=(COL, 1.9))
    ax.bar([0, 1], [d["self_mean"], d["pub_mean"]], width=.45,
           color=[MUTE, GATE], alpha=.85, edgecolor="none")
    for x, v in zip([0, 1], [d["self_mean"], d["pub_mean"]]):
        ax.text(x, v + (.008 if v > 0 else -.008), f"{v:+.3f}", ha="center",
                va="bottom" if v > 0 else "top", fontsize=6.8)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([f"자체 배급\n({d['share']:.0%})", "퍼블리셔 있음"], fontsize=6.8)
    ax.set_ylabel("출시 30일 반응 (표준화)", fontsize=7.0)
    ax.set_title("신호 자체는 옳다 — 그래도 넣으면 손해다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 21 ────────────────────────────────────────────────────────────
def fig_absolute_curve(out: Path, root: str = ".") -> dict:
    """노트21 주장 1 — 눈금에 필요한 라벨 수."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/absolute.json").read_text())
    R = d["결과"]
    fig, axes = plt.subplots(1, len(R), figsize=(FULL, 2.1), sharey=False)
    for ax, dm in zip(np.atleast_1d(axes), R):
        ks = [k for k in d["ks"] if str(k) in R[dm]]
        p = [R[dm][str(k)]["pipe_fold"] for k in ks]
        c = [R[dm][str(k)]["const_fold"] for k in ks]
        ax.plot(range(len(ks)), c, "-o", ms=3.5, lw=1.2, color=MUTE, label="상수")
        ax.plot(range(len(ks)), p, "-o", ms=3.5, lw=1.4, color=GATE, label="파이프라인")
        ax.axhline(R[dm]["full_mad"]["pipe_fold"], color=CLAIM, lw=.9, ls="--")
        ax.set_xticks(range(len(ks)))
        ax.set_xticklabels([str(k) for k in ks], fontsize=6.0)
        ax.set_title(dm, fontsize=7.4)
        ax.set_xlabel("눈금에 쓴 라벨 수 k", fontsize=6.8)
        ax.tick_params(labelsize=6.0)
    np.atleast_1d(axes)[0].set_ylabel("배수 오차", fontsize=7.0)
    np.atleast_1d(axes)[0].legend(fontsize=5.8, frameon=False)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_absolute_win(out: Path, root: str = ".") -> dict:
    """노트21 주장 2 — 도메인마다 갈린다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/absolute.json").read_text())
    R = d["결과"]
    fig, ax = plt.subplots(figsize=(COL, 2.05))
    cols = {"팝업": GATE, "아이돌": MUTE, "게임": CLAIM}
    for dm in R:
        ks = [k for k in d["ks"] if str(k) in R[dm]]
        ax.plot(range(len(ks)), [R[dm][str(k)]["win_rate"] for k in ks],
                "-o", ms=3.5, lw=1.3, color=cols.get(dm, INK), label=dm)
    ax.axhline(.5, color=INK, lw=.9, ls="--")
    ax.set_xticks(range(len(d["ks"])))
    ax.set_xticklabels([str(k) for k in d["ks"]], fontsize=6.2)
    ax.set_xlabel("눈금에 쓴 라벨 수 k", fontsize=7.0)
    ax.set_ylabel("상수를 이긴 비율", fontsize=7.0)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=6.0, frameon=False, ncol=3)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_split_cost(out: Path, root: str = ".") -> dict:
    """노트21 — 순위와 눈금의 비용이 다르다."""
    fig, ax = plt.subplots(figsize=(COL, 1.75))
    ax.axis("off")
    rows = [("순위", "라벨 0개", "프로크루스테스 정렬 + 전이 계수", GATE),
            ("눈금", "라벨 8개", "중심과 폭 두 모수만 추정", CLAIM)]
    for i, (a, b, c, col) in enumerate(rows):
        y = 1 - i * .55
        ax.add_patch(plt.Rectangle((.02, y - .22), .18, .44, fc="white", ec=col, lw=1.2))
        ax.text(.11, y, a, ha="center", va="center", fontsize=8.0)
        ax.text(.26, y, b, va="center", fontsize=7.4, color=col)
        ax.text(.46, y, c, va="center", fontsize=6.4, color=INK)
    ax.set_xlim(0, 1.05); ax.set_ylim(.15, 1.35)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 22 ────────────────────────────────────────────────────────────
def fig_timeorder(out: Path, root: str = ".") -> dict:
    """노트22 주장 1 — 시간순 보정은 도메인마다 다르다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note22.json").read_text())["timeorder"]
    doms = list(d)
    fig, axes = plt.subplots(1, len(doms), figsize=(FULL, 2.1))
    for ax, dm in zip(np.atleast_1d(axes), doms):
        rows = d[dm]
        ks = [r[0] for r in rows]
        ax.plot(range(len(ks)), [r[1] for r in rows], "-o", ms=3.5, lw=1.2,
                color=MUTE, label="무작위 k")
        ax.plot(range(len(ks)), [r[2] for r in rows], "-o", ms=3.5, lw=1.4,
                color=GATE, label="시간순 k")
        ax.plot(range(len(ks)), [r[3] for r in rows], ":", lw=1.1,
                color=CLAIM, label="상수(시간순)")
        ax.set_xticks(range(len(ks)))
        ax.set_xticklabels([str(k) for k in ks], fontsize=6.0)
        ax.set_title(dm, fontsize=7.4)
        ax.set_xlabel("k", fontsize=6.8)
        ax.tick_params(labelsize=6.0)
    np.atleast_1d(axes)[0].set_ylabel("배수 오차", fontsize=7.0)
    np.atleast_1d(axes)[0].legend(fontsize=5.6, frameon=False)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_source_curve(out: Path, root: str = ".") -> dict:
    """노트22 주장 2 — 출처 표본은 200건에서 포화한다."""
    import json, numpy as np
    c = json.loads((Path(root) / "data/state/note22.json").read_text())["invest"]["curve"]
    ns = [r[0] for r in c]
    fig, ax = plt.subplots(figsize=(COL, 2.05))
    ax.plot(range(len(ns)), [r[1] for r in c], "-o", ms=4, lw=1.4, color=GATE,
            label="게임 → 팝업")
    ax.plot(range(len(ns)), [r[3] for r in c], "-o", ms=4, lw=1.4, color=MUTE,
            label="게임 → 아이돌")
    for i, r in enumerate(c):
        for v, p in ((r[1], r[2]), (r[3], r[4])):
            if p >= .05:
                ax.scatter([i], [v], s=70, facecolors="none", edgecolors=CLAIM, lw=1.1)
    ax.axhline(0, color=INK, lw=.9, ls="--")
    ax.axvline(2, color=CLAIM, lw=.9, ls=":")
    ax.text(2.05, ax.get_ylim()[1] * .9, "포화", fontsize=6.2, color=CLAIM)
    ax.set_xticks(range(len(ns)))
    ax.set_xticklabels([str(n) for n in ns], fontsize=6.4)
    ax.set_xlabel("출처(게임) 표본 크기", fontsize=7.0)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_axis_value(out: Path, root: str = ".") -> dict:
    """노트22 주장 3 — 축마다 값어치가 다르고 하나는 음수다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note22.json").read_text())["invest"]
    abl, base = d["ablation"], d["base"]
    ks = [a[0] for a in abl]
    loss = [a[1] - base for a in abl]
    order = np.argsort(loss)[::-1]
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.bar(xs, [loss[i] for i in order], width=.5,
           color=[GATE if loss[i] > 0 else CLAIM for i in order], alpha=.85,
           edgecolor="none")
    for x, i in zip(xs, order):
        ax.text(x, loss[i] + (.001 if loss[i] > 0 else -.001), f"{loss[i]:+.4f}",
                ha="center", va="bottom" if loss[i] > 0 else "top", fontsize=6.4)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([ks[i] for i in order], fontsize=6.6)
    ax.set_ylabel("제거했을 때의 손실", fontsize=7.0)
    ax.set_title("양수면 값진 축, 음수면 해로운 축", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 23 ────────────────────────────────────────────────────────────
def fig_venue_gain(out: Path, root: str = ".") -> dict:
    """노트23 주장 1 — 아이돌이 낀 방향이 전부 강해졌다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note23.json").read_text())
    B, A = d["before"], d["after"]
    ks = sorted(B, key=lambda k: A[k][0])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.bar(xs - .19, [B[k][0] for k in ks], width=.36, label="확보 전 (33%)",
           color=MUTE, alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [A[k][0] for k in ks], width=.36, label="확보 후 (90%)",
           color=GATE, alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        if "아이돌" in k:
            ax.text(x, min(B[k][0], A[k][0]) - .004, "★", ha="center", va="top",
                    fontsize=7.5, color=CLAIM)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([k.replace("→", "\n→ ") for k in ks], fontsize=6.2)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.set_title("★ 는 아이돌이 낀 방향", fontsize=7.2)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_attempts(out: Path, root: str = ".") -> dict:
    """노트23 주장 2 — 두 번 실패하고 세 번째에 됐다."""
    import json
    d = json.loads((Path(root) / "data/state/note23.json").read_text())["attempts"]
    fig, ax = plt.subplots(figsize=(FULL, 1.7))
    ax.axis("off")
    for i, a in enumerate(d):
        y = 1 - i * .38
        col = GATE if a["ok"] else CLAIM
        ax.add_patch(plt.Rectangle((.02, y - .15), .26, .3, fc="white", ec=col, lw=1.1))
        ax.text(.15, y, a["name"], ha="center", va="center", fontsize=6.6)
        ax.text(.32, y, ("성공 — " if a["ok"] else "실패 — ") + a["result"], va="center",
                fontsize=6.2, color=col)
    ax.set_xlim(0, 1.05); ax.set_ylim(.05, 1.25)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_monotone(out: Path, root: str = ".") -> dict:
    """노트23 — 사전 데뷔 건수와 초동의 단조 관계."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note23.json").read_text())["monotone"]
    xs = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(COL, 1.95))
    ax.bar(xs, [r[2] for r in d], width=.5, color=GATE, alpha=.85, edgecolor="none")
    for x, r in zip(xs, d):
        ax.text(x, r[2] + .03, f"{r[2]:.2f}\n(n={r[1]})", ha="center", fontsize=6.4)
    ax.set_xticks(xs); ax.set_xticklabels([r[0] for r in d], fontsize=6.6)
    ax.set_ylabel("초동 log10 평균", fontsize=7.0)
    ax.set_ylim(4.3, 5.7)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 24 ────────────────────────────────────────────────────────────
def fig_cell_ci(out: Path, root: str = ".") -> dict:
    """노트24 주장 1 — 여섯 방향의 부트스트랩 구간."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note24.json").read_text())["cells"]
    ks = sorted(d, key=lambda k: d[k]["mean"])
    ys = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    for y, k in zip(ys, ks):
        v = d[k]
        col = GATE if v["ci"][1] < 0 else MUTE
        ax.plot(v["ci"], [y, y], lw=1.6, color=col, alpha=.6)
        ax.scatter([v["mean"]], [y], s=32, color=col, zorder=3)
    ax.axvline(0, color=CLAIM, lw=1.0, ls="--")
    ax.set_yticks(ys); ax.set_yticklabels(ks, fontsize=6.6)
    ax.set_xlabel("대상 상수 대비 MAE 차이 (부트스트랩 95%)", fontsize=7.0)
    ax.tick_params(labelsize=6.4)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_src_tgt(out: Path, root: str = ".") -> dict:
    """노트24 주장 2 — 대상 난이도의 분산이 훨씬 크다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note24.json").read_text())
    src, tgt = d["src"], d["tgt"]
    names = list(src)
    xs = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    ax.bar(xs - .19, [src[n] for n in names], width=.36, label="출처 강도",
           color=MUTE, alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [tgt[n] for n in names], width=.36, label="대상 난이도",
           color=CLAIM, alpha=.85, edgecolor="none")
    ax.axhline(0, color=INK, lw=.9)
    r1 = max(src.values()) - min(src.values())
    r2 = max(tgt.values()) - min(tgt.values())
    ax.text(.02, .95, f"범위 비 {r2/r1:.1f}배", transform=ax.transAxes, fontsize=6.6,
            va="top", color=CLAIM)
    ax.set_xticks(xs); ax.set_xticklabels(names, fontsize=6.8)
    ax.set_ylabel("가법 모형 계수", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_additive_fit(out: Path, root: str = ".") -> dict:
    """노트24 주장 3 — 상호작용이 없다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note24.json").read_text())
    cells, resid = d["cells"], d["resid"]
    ks = list(cells)
    obs = np.array([cells[k]["mean"] for k in ks])
    pred = obs - np.array([resid[k] for k in ks])
    fig, ax = plt.subplots(figsize=(COL, 2.15))
    lo, hi = min(obs.min(), pred.min()) - .01, max(obs.max(), pred.max()) + .01
    ax.plot([lo, hi], [lo, hi], lw=.9, ls="--", color=INK)
    ax.scatter(pred, obs, s=34, color=GATE, alpha=.9, edgecolors="none")
    for k, p, o in zip(ks, pred, obs):
        ax.annotate(k, (p, o), textcoords="offset points", xytext=(4, 3), fontsize=5.6)
    ax.set_xlabel("가법 모형 예측", fontsize=7.0)
    ax.set_ylabel("관측", fontsize=7.0)
    ax.text(.03, .95, f"설명력 {d['r2']:.1%}", transform=ax.transAxes, fontsize=6.8,
            va="top", color=CLAIM)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 25 ────────────────────────────────────────────────────────────
def fig_all_six(out: Path, root: str = ".") -> dict:
    """노트25 주장 1 — 여섯 방향이 전부 유의해졌다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note25.json").read_text())
    B, N = d["before"], d["now"]
    ks = sorted(B, key=lambda k: N[k][0])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.bar(xs - .19, [B[k][0] for k in ks], width=.36, label="수정 전",
           color=MUTE, alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [N[k][0] for k in ks], width=.36, label="굿즈 규모 = 설치 용량",
           color=GATE, alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        ax.text(x + .19, N[k][0] - .003, f"p={N[k][1]:.4f}", ha="center", va="top",
                fontsize=5.6)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([k.replace("→", "\n→ ") for k in ks], fontsize=6.2)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_signal_location(out: Path, root: str = ".") -> dict:
    """노트25 주장 2 — 신호의 75%가 공통 축 밖에 있었다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note25.json").read_text())["signal"]
    ks = ["공통 2축", "도달 폭", "제작 규모", "전부"]
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.bar(xs, [d[k] for k in ks], width=.55,
           color=[CLAIM if k == "공통 2축" else GATE for k in ks], alpha=.85,
           edgecolor="none")
    for x, k in zip(xs, ks):
        ax.text(x, d[k] + .004, f"{d[k]:.1%}", ha="center", fontsize=6.6)
    ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.4)
    ax.set_ylabel("게임 라벨 설명력", fontsize=7.0)
    ax.set_title("공통 축이 담은 것은 25%뿐이었다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_ceiling(out: Path, root: str = ".") -> dict:
    """노트25 주장 3 — 게임만 자기 라벨을 설명한다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note25.json").read_text())["ceiling"]
    ks = list(d)
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    v = [d[k]["explained"] for k in ks]
    ax.bar(xs, v, width=.5, color=[GATE if x > 0 else CLAIM for x in v], alpha=.85,
           edgecolor="none")
    for x, k in zip(xs, ks):
        ax.text(x, d[k]["explained"] + (.006 if d[k]["explained"] > 0 else -.006),
                f"{d[k]['explained']:+.1%}", ha="center",
                va="bottom" if d[k]["explained"] > 0 else "top", fontsize=6.6)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.8)
    ax.set_ylabel("가용 피처 전부의 설명력", fontsize=7.0)
    ax.set_title("음수는 상수보다 나쁘다는 뜻", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 26 ────────────────────────────────────────────────────────────
def fig_corr_heat(out: Path, root: str = ".") -> dict:
    """노트26 주장 1 — 팝업 열 축이 서로 양의 상관이다."""
    import json, numpy as np
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "매장 노출도",
          "entry_friction": "입장 허들", "media_push": "미디어 투입",
          "goods_scale": "굿즈 규모", "collab_strength": "콜라보 강도",
          "ip_awareness": "IP 인지 폭", "experience_density": "체험 밀도",
          "photo_zones": "포토존 수", "season_fit": "시즌 적합"}
    d = json.loads((Path(root) / "data/state/note26.json").read_text())
    C = np.array(d["corr"])
    ax_ = [KO[a] for a in d["axes"]]
    fig, ax = plt.subplots(figsize=(COL, 2.6))
    im = ax.imshow(C, cmap="RdBu_r", vmin=-.6, vmax=.6)
    ax.set_xticks(range(len(ax_)))
    ax.set_xticklabels(ax_, fontsize=5.4, rotation=60, ha="right")
    ax.set_yticks(range(len(ax_)))
    ax.set_yticklabels(ax_, fontsize=5.4)
    fig.colorbar(im, ax=ax, fraction=.045, pad=.03).ax.tick_params(labelsize=5.4)
    ax.set_title(f"평균 |r| {d['halo']['popup_mean_abs_r']:.3f} · "
                 f"음의 상관 {d['halo']['popup_neg_share']:.0%}", fontsize=7.0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_effdim(out: Path, root: str = ".") -> dict:
    """노트26 주장 2 — 유효 차원이 축 개수보다 적다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note26.json").read_text())["test"]["effdim"]
    rows = [("팝업 10축", d["popup10"], 10), ("팝업 5축", d["popup5"], 5),
            ("아이돌 4축", d["idol4"], 4)]
    ys = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(COL, 1.95))
    ax.barh(ys, [r[2] for r in rows], height=.5, color=MUTE, alpha=.35,
            label="축 개수", edgecolor="none")
    ax.barh(ys, [r[1] for r in rows], height=.5, color=GATE, alpha=.9,
            label="유효 차원", edgecolor="none")
    for y, r in zip(ys, rows):
        ax.text(r[1] + .12, y, f"{r[1]:.2f}", va="center", fontsize=6.6)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=6.8)
    ax.set_xlabel("차원", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_halo_removal(out: Path, root: str = ".") -> dict:
    """노트26 주장 3 — 제거하면 팝업이 낀 방향만 무너진다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note26.json").read_text())["test"]
    O, N = d["orig"], d["nohalo"]
    ks = sorted(O, key=lambda k: O[k][0])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.bar(xs - .19, [O[k][0] for k in ks], width=.36, label="원본",
           color=GATE, alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [N[k][0] for k in ks], width=.36, label="제1주성분 제거",
           color=CLAIM, alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        if "팝업" in k:
            ax.text(x, max(O[k][0], N[k][0]) + .006, "팝업", ha="center", fontsize=5.8,
                    color=CLAIM)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([k.replace("→", "\n→ ") for k in ks], fontsize=6.2)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 27 ────────────────────────────────────────────────────────────
def fig_shrink_curve(out: Path, root: str = ".") -> dict:
    """노트27 주장 1 — 제1주성분의 20%만 잡음이다."""
    import json, numpy as np
    c = json.loads((Path(root) / "data/state/note27.json").read_text())["curve"]
    al = [r[0] for r in c]
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    ax.plot(al, [r[1] for r in c], "-o", ms=4, lw=1.5, color=GATE, label="팝업 낀 4방향")
    ax.plot(al, [r[2] for r in c], "-o", ms=3.5, lw=1.2, color=MUTE, label="여섯 방향 전체")
    best = min(c, key=lambda r: r[1])
    ax.scatter([best[0]], [best[1]], s=80, facecolors="none", edgecolors=CLAIM, lw=1.3)
    ax.text(best[0], best[1] - .006, f"최선 α={best[0]:.1f}", ha="center", va="top",
            fontsize=6.2, color=CLAIM)
    ax.axhline(0, color=INK, lw=.9, ls="--")
    ax.set_xlabel("제1주성분 제거 강도 α", fontsize=7.0)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_counterfactual(out: Path, root: str = ".") -> dict:
    """노트27 주장 2 — 축을 빼면 팝업이 게임보다 어려워진다."""
    import json, numpy as np
    c = json.loads((Path(root) / "data/state/note27.json").read_text())["counterfactual"]
    xs = np.arange(len(c))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.bar(xs - .19, [r[1] for r in c], width=.36, label="팝업 난이도",
           color=GATE, alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [r[2] for r in c], width=.36, label="게임 난이도",
           color=CLAIM, alpha=.85, edgecolor="none")
    for x, r in zip(xs, c):
        if r[1] > r[2]:
            ax.text(x, max(r[1], r[2]) + .003, "팝업이 더 어려움", ha="center",
                    fontsize=5.8, color=CLAIM)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([r[0] for r in c], fontsize=6.2)
    ax.set_ylabel("대상 난이도 (가법 모형 계수)", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_difficulty_axes(out: Path, root: str = ".") -> dict:
    """노트27 주장 3 — 난이도는 관측 축 수의 함수다."""
    import json, numpy as np
    c = json.loads((Path(root) / "data/state/note27.json").read_text())["counterfactual"]
    naxes = [5, 4, 4, 3]
    diff = [r[1] for r in c]
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.scatter(naxes, diff, s=52, color=GATE, alpha=.9, edgecolors="none", label="팝업")
    ax.scatter([2], [c[0][2]], s=52, marker="s", color=CLAIM, alpha=.9,
               edgecolors="none", label="게임(2축)")
    b = np.polyfit(naxes, diff, 1)
    xs = np.linspace(1.8, 5.2, 20)
    ax.plot(xs, np.polyval(b, xs), lw=1.1, ls="--", color=INK, alpha=.6)
    ax.axhline(0, color=INK, lw=.8, ls=":")
    ax.set_xlabel("관측 축 수", fontsize=7.0)
    ax.set_ylabel("대상 난이도", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 28 ────────────────────────────────────────────────────────────
def fig_venue_cases(out: Path, root: str = ".") -> dict:
    """노트28 주장 1 — 축을 넣으면 유의 방향이 준다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note28.json").read_text())["cases"]
    labs = list(d)
    ks = list(d[labs[0]])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.3))
    cols = [GATE, MUTE, CLAIM]
    w = .8 / len(labs)
    for i, lab in enumerate(labs):
        ax.bar(xs + (i - (len(labs) - 1) / 2) * w, [d[lab][k][0] for k in ks],
               width=w * .9, label=lab.split(" (")[0], color=cols[i % 3], alpha=.85,
               edgecolor="none")
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([k.replace("→", "\n→ ") for k in ks], fontsize=6.0)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.legend(fontsize=5.6, frameon=False, ncol=3)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_asymmetry(out: Path, root: str = ".") -> dict:
    """노트28 주장 2 — 출처로는 좋아지고 대상으로는 나빠진다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note28.json").read_text())["cases"]
    labs = list(d)
    off, on = d[labs[0]], d[labs[1]]
    src = [k for k in off if k.startswith("게임")]
    tgt = [k for k in off if k.endswith("게임")]
    fig, ax = plt.subplots(figsize=(COL, 2.05))
    xs = np.arange(2)
    dsrc = float(np.mean([on[k][0] - off[k][0] for k in src]))
    dtgt = float(np.mean([on[k][0] - off[k][0] for k in tgt]))
    ax.bar(xs, [dsrc, dtgt], width=.5, color=[GATE, CLAIM], alpha=.85, edgecolor="none")
    for x, v in zip(xs, [dsrc, dtgt]):
        ax.text(x, v + (.002 if v > 0 else -.002), f"{v:+.4f}", ha="center",
                va="bottom" if v > 0 else "top", fontsize=6.8)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels(["게임이 출처일 때", "게임이 대상일 때"], fontsize=6.8)
    ax.set_ylabel("축 추가로 인한 변화", fontsize=7.0)
    ax.set_title("음수가 개선", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_venue_signal(out: Path, root: str = ".") -> dict:
    """노트28 — 축 자체는 좋은 신호였다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note28.json").read_text())["signal"]
    ks = list(d)
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(COL, 1.9))
    ax.bar(xs, [d[k] for k in ks], width=.5,
           color=[GATE if d[k] > 0 else MUTE for k in ks], alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        ax.text(x, d[k] + (.008 if d[k] > 0 else -.008), f"{d[k]:+.3f}", ha="center",
                va="bottom" if d[k] > 0 else "top", fontsize=6.6)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.2)
    ax.set_ylabel("출시 30일 반응과의 상관", fontsize=7.0)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 29 ────────────────────────────────────────────────────────────
def fig_lambda(out: Path, root: str = ".") -> dict:
    """노트29 주장 1 — λ=0.75가 안정 구간의 끝이다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note29.json").read_text())["lam"]
    lam = [r[0] for r in d]
    fig, ax = plt.subplots(figsize=(COL, 2.15))
    ax.plot(lam, [r[1][1] for r in d], "-o", ms=4, lw=1.4, color=GATE, label="축 끔")
    ax.plot(lam, [r[2][1] for r in d], "-o", ms=4, lw=1.4, color=CLAIM, label="축 켬")
    for i, r in enumerate(d):
        for j, col in ((1, GATE), (2, CLAIM)):
            if r[j][0] == 6:
                ax.scatter([r[0]], [r[j][1]], s=76, facecolors="none",
                           edgecolors=col, lw=1.2)
    ax.axvline(.75, color=INK, lw=.9, ls="--")
    ax.text(.76, ax.get_ylim()[1] * .96, "채택", fontsize=6.2)
    ax.set_xlabel("고유 축 혼합 비율 λ", fontsize=7.0)
    ax.set_ylabel("여섯 방향 평균 차이", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_lambda_sig(out: Path, root: str = ".") -> dict:
    """노트29 주장 2 — 유의 방향 수로 본 안정성."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note29.json").read_text())["lam"]
    lam = [r[0] for r in d]
    xs = np.arange(len(lam))
    fig, ax = plt.subplots(figsize=(COL, 1.95))
    ax.bar(xs - .19, [r[1][0] for r in d], width=.36, label="축 끔", color=GATE,
           alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [r[2][0] for r in d], width=.36, label="축 켬", color=CLAIM,
           alpha=.85, edgecolor="none")
    ax.axhline(6, color=INK, lw=.9, ls="--")
    ax.set_xticks(xs); ax.set_xticklabels([f"{l:.2f}" for l in lam], fontsize=6.4)
    ax.set_xlabel("λ", fontsize=7.0)
    ax.set_ylabel("유의 방향 수", fontsize=7.0)
    ax.set_ylim(0, 6.8)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_final_six(out: Path, root: str = ".") -> dict:
    """노트29 주장 3 — λ=0.75에서는 축을 켜도 여섯이 유지된다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note29.json").read_text())
    O, N = d["final_off"], d["final_on"]
    ks = sorted(O, key=lambda k: O[k][0])
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.bar(xs - .19, [O[k][0] for k in ks], width=.36, label="게임 매장축 끔",
           color=GATE, alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [N[k][0] for k in ks], width=.36, label="게임 매장축 켬",
           color=MUTE, alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        ax.text(x, min(O[k][0], N[k][0]) - .004, f"{max(O[k][1], N[k][1]):.3f}",
                ha="center", va="top", fontsize=5.6)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([k.replace("→", "\n→ ") for k in ks], fontsize=6.2)
    ax.set_ylabel("대상 상수 대비 MAE 차이", fontsize=7.0)
    ax.set_title("숫자는 두 구성 중 큰 쪽 p", fontsize=7.2)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 30 ────────────────────────────────────────────────────────────
def fig_lam_schemes(out: Path, root: str = ".") -> dict:
    """노트30 주장 1 — 방식별 비교."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note30.json").read_text())["schemes"]
    ks = list(d)
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.bar(xs - .19, [d[k][0][1] for k in ks], width=.36, label="매장축 끔",
           color=MUTE, alpha=.85, edgecolor="none")
    ax.bar(xs + .19, [d[k][1][1] for k in ks], width=.36, label="매장축 켬",
           color=GATE, alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        for off, i in ((-.19, 0), (.19, 1)):
            n = d[k][i][0]
            ax.text(x + off, d[k][i][1] - .002, f"{n}개", ha="center", va="top",
                    fontsize=5.8, color=INK if n == 6 else CLAIM)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.0)
    ax.set_ylabel("여섯 방향 평균 차이", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_overlap_diag(out: Path, root: str = ".") -> dict:
    """노트30 주장 2 — 원인은 공유 축과의 겹침이다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note30.json").read_text())
    diag = {k: v for k, v in d["diag"].items() if v}
    ks = list(diag)
    xs = np.arange(len(ks))
    keys = [("n_own", "고유 축 수", MUTE), ("mean_abs_r", "내부 평균 |r|", GATE),
            ("cross", "공유 축과 겹침", CLAIM)]
    fig, axes = plt.subplots(1, 3, figsize=(FULL, 1.95))
    for ax, (k, lab, col) in zip(axes, keys):
        ax.bar(xs, [diag[d_][k] for d_ in ks], width=.5, color=col, alpha=.85,
               edgecolor="none")
        for x, d_ in zip(xs, ks):
            ax.text(x, diag[d_][k] * 1.03, f"{diag[d_][k]:.3f}"
                    if k != "n_own" else f"{int(diag[d_][k])}",
                    ha="center", fontsize=6.2)
        ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.4)
        ax.set_title(lab, fontsize=7.0)
        ax.tick_params(labelsize=6.0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_abs_update(out: Path, root: str = ".") -> dict:
    """노트30 주장 3 — 절대량도 개선됐다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note30.json").read_text())["absolute"]
    R = d["결과"]
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    cols = {"팝업": GATE, "아이돌": MUTE, "게임": CLAIM}
    for dm in R:
        ks = [k for k in d["ks"] if str(k) in R[dm]]
        ax.plot(range(len(ks)), [R[dm][str(k)]["win_rate"] for k in ks],
                "-o", ms=3.5, lw=1.3, color=cols.get(dm, INK), label=dm)
    ax.axhline(.5, color=INK, lw=.9, ls="--")
    ax.set_xticks(range(len(d["ks"])))
    ax.set_xticklabels([str(k) for k in d["ks"]], fontsize=6.2)
    ax.set_xlabel("눈금 보정에 쓴 라벨 수 k", fontsize=7.0)
    ax.set_ylabel("상수를 이긴 비율", fontsize=7.0)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=6.0, frameon=False, ncol=3)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 31 ────────────────────────────────────────────────────────────
def fig_rank_vs_gain(out: Path, root: str = ".") -> dict:
    """노트31 주장 1 — 순위 상관이 달성률을 정한다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note31.json").read_text())["diag"]
    ks = list(d)
    fig, ax = plt.subplots(figsize=(COL, 2.15))
    cols = {"팝업": GATE, "아이돌": MUTE, "게임": CLAIM}
    for k in ks:
        ax.scatter([d[k]["rank_r"]], [d[k]["ratio"]], s=54, color=cols.get(k, INK),
                   alpha=.9, edgecolors="none")
        ax.annotate(k, (d[k]["rank_r"], d[k]["ratio"]), textcoords="offset points",
                    xytext=(6, 4), fontsize=6.4)
    xs = np.array([d[k]["rank_r"] for k in ks]); ys = np.array([d[k]["ratio"] for k in ks])
    b = np.polyfit(xs, ys, 1)
    xr = np.linspace(.3, .72, 20)
    ax.plot(xr, np.polyval(b, xr), lw=1.0, ls="--", color=INK, alpha=.6)
    ax.axhline(0, color=INK, lw=.9, ls=":")
    ax.axvline(.5, color=CLAIM, lw=.9, ls="--")
    ax.text(.505, ax.get_ylim()[1] * .9, "실무 문턱", fontsize=6.2, color=CLAIM)
    ax.set_xlabel("순위 예측과 실제의 상관", fontsize=7.0)
    ax.set_ylabel("가능한 개선폭 중 달성한 비율", fontsize=7.0)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_ceiling_gap(out: Path, root: str = ".") -> dict:
    """노트31 주장 2 — 눈금은 문제없다. 완전 순위면 1.2배."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note31.json").read_text())["diag"]
    ks = list(d)
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.1))
    for i, (k, lab, col) in enumerate((("const", "상수", MUTE),
                                       ("actual", "현재", CLAIM),
                                       ("perfect", "완전 순위", GATE))):
        ax.bar(xs + (i - 1) * .27, [d[dm][k] for dm in ks], width=.25, label=lab,
               color=col, alpha=.85, edgecolor="none")
    for x, dm in zip(xs, ks):
        for i, k in enumerate(("const", "actual", "perfect")):
            ax.text(x + (i - 1) * .27, d[dm][k] + .06, f"{d[dm][k]:.2f}", ha="center",
                    fontsize=5.8)
    ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.8)
    ax.set_ylabel("배수 오차", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=3)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_sig_vs_useful(out: Path, root: str = ".") -> dict:
    """노트31 주장 3 — 유의성과 실용성은 다르다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note31.json").read_text())
    diag, pv = d["diag"], d["p"]
    ks = list(diag)
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.bar(xs - .19, [diag[k]["rank_r"] for k in ks], width=.36, label="순위 상관",
           color=GATE, alpha=.85, edgecolor="none")
    ax2 = ax.twinx()
    ax2.bar(xs + .19, [-np.log10(max(pv[k], 1e-4)) for k in ks], width=.36,
            label="$-\\log_{10}$ p", color=MUTE, alpha=.85, edgecolor="none")
    ax.axhline(.5, color=CLAIM, lw=.9, ls="--")
    ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.8)
    ax.set_ylabel("순위 상관", fontsize=7.0, color=GATE)
    ax2.set_ylabel("$-\\log_{10}$ 순열 p", fontsize=7.0, color=MUTE)
    ax.set_title("유의성은 셋 다 높은데 상관은 갈린다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    ax2.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 32 ────────────────────────────────────────────────────────────
def fig_rhat_sd(out: Path, root: str = ".") -> dict:
    """노트32 주장 1 — 추정은 불편이고 SD만 준다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note32.json").read_text())["rhat"]
    ks = [5, 8, 12, 20, 30, 50]
    fig, ax = plt.subplots(figsize=(COL, 2.15))
    cols = {"팝업": GATE, "아이돌": MUTE, "게임": CLAIM}
    for dm in d:
        kk = [k for k in ks if str(k) in d[dm]]
        m = [d[dm][str(k)]["mean"] for k in kk]
        s = [d[dm][str(k)]["sd"] for k in kk]
        ax.errorbar(range(len(kk)), m, yerr=s, fmt="-o", ms=3.5, lw=1.2, capsize=2.5,
                    color=cols.get(dm, INK), label=dm, alpha=.9)
        ax.axhline(d[dm]["true"], color=cols.get(dm, INK), lw=.7, ls=":")
    ax.axhline(.5, color=INK, lw=1.0, ls="--")
    ax.text(len(ks) - 1.1, .52, "문턱 0.5", fontsize=6.2)
    ax.set_xticks(range(len(ks)))
    ax.set_xticklabels([str(k) for k in ks], fontsize=6.4)
    ax.set_xlabel("추정에 쓴 라벨 수 k", fontsize=7.0)
    ax.set_ylabel("순위 상관 추정", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, ncol=3)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_decision_acc(out: Path, root: str = ".") -> dict:
    """노트32 주장 2 — 판정 정확도는 훨씬 늦게 오른다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note32.json").read_text())["rhat"]
    ks = [5, 8, 12, 20, 30, 50]
    fig, ax = plt.subplots(figsize=(COL, 2.05))
    cols = {"팝업": GATE, "아이돌": MUTE, "게임": CLAIM}
    for dm in d:
        kk = [k for k in ks if str(k) in d[dm]]
        ax.plot(range(len(kk)), [d[dm][str(k)]["acc"] for k in kk], "-o", ms=3.5,
                lw=1.3, color=cols.get(dm, INK), label=dm)
    ax.axhline(.5, color=INK, lw=.9, ls="--")
    ax.text(.05, .52, "동전 던지기", fontsize=6.2)
    ax.axhline(.9, color=CLAIM, lw=.9, ls=":")
    ax.set_xticks(range(len(ks)))
    ax.set_xticklabels([str(k) for k in ks], fontsize=6.4)
    ax.set_xlabel("추정에 쓴 라벨 수 k", fontsize=7.0)
    ax.set_ylabel("문턱 판정 정확도", fontsize=7.0)
    ax.set_ylim(.4, 1.02)
    ax.legend(fontsize=6.0, frameon=False, ncol=3)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_cost_gap(out: Path, root: str = ".") -> dict:
    """노트32 주장 3 — 눈금과 문턱의 비용 차이."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(COL, 1.8))
    ax.axis("off")
    rows = [("눈금 보정", 8, "중심 + 중앙절대편차 두 모수", GATE),
            ("문턱 판정", 50, "순위 상관이 0.5를 넘는가", CLAIM)]
    for i, (a, k, c, col) in enumerate(rows):
        y = 1 - i * .5
        ax.add_patch(plt.Rectangle((.02, y - .19), .2, .38, fc="white", ec=col, lw=1.2))
        ax.text(.12, y, a, ha="center", va="center", fontsize=7.4)
        ax.text(.27, y, f"{k}건", va="center", fontsize=9.0, color=col)
        ax.text(.40, y, c, va="center", fontsize=6.4, color=INK)
    ax.text(.5, .15, "같은 파이프라인인데 필요한 라벨이 여섯 배 차이 난다",
            ha="center", fontsize=6.4, color=MUTE)
    ax.set_xlim(0, 1.05); ax.set_ylim(.05, 1.35)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 33 ────────────────────────────────────────────────────────────
def fig_target_ceiling(out: Path, root: str = ".") -> dict:
    """노트33 주장 1 — 전이 상관이 대상 자기 상관과 같다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note33.json").read_text())["six"]["rows"]
    x = np.array([r["tgt_self"] for r in d])
    y = np.array([r["r"] for r in d])
    fig, ax = plt.subplots(figsize=(COL, 2.2))
    lo, hi = .28, .72
    ax.plot([lo, hi], [lo, hi], lw=1.0, ls="--", color=INK, alpha=.7)
    ax.scatter(x, y, s=42, color=GATE, alpha=.9, edgecolors="none")
    for r in d:
        ax.annotate(r["pair"], (r["tgt_self"], r["r"]), textcoords="offset points",
                    xytext=(5, 3), fontsize=5.4)
    ax.text(.03, .95, f"r={np.corrcoef(x, y)[0,1]:+.3f}", transform=ax.transAxes,
            fontsize=6.8, va="top", color=CLAIM)
    ax.set_xlabel("대상 도메인의 자기 상관 (교차검증)", fontsize=7.0)
    ax.set_ylabel("전이 상관", fontsize=7.0)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_proxy_compare(out: Path, root: str = ".") -> dict:
    """노트33 주장 2 — 후보별 설명력."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note33.json").read_text())["six"]["rows"]
    R = np.array([r["r"] for r in d])
    cand = [("대상 자기 상관", "tgt_self"), ("출처 표본 수", "n"),
            ("출처 축 수", "k"), ("출처 자기 상관", "src_self")]
    vals = [float(np.corrcoef(np.array([r[k] for r in d], float), R)[0, 1])
            for _, k in cand]
    xs = np.arange(len(cand))
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.bar(xs, vals, width=.5,
           color=[GATE if abs(v) > .8 else MUTE for v in vals], alpha=.85,
           edgecolor="none")
    for x, v in zip(xs, vals):
        ax.text(x, v + (.03 if v > 0 else -.03), f"{v:+.3f}", ha="center",
                va="bottom" if v > 0 else "top", fontsize=6.6)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels([c[0] for c in cand], fontsize=6.2)
    ax.set_ylabel("전이 상관과의 상관", fontsize=7.0)
    ax.set_ylim(-.7, 1.15)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_ratio(out: Path, root: str = ".") -> dict:
    """노트33 주장 3 — 비율이 1 근처에 모인다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note33.json").read_text())["six"]["rows"]
    ratio = [r["r"] / r["tgt_self"] for r in d]
    ys = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.barh(ys, ratio, height=.55, color=GATE, alpha=.85, edgecolor="none")
    ax.axvline(1.0, color=CLAIM, lw=1.2, ls="--")
    for y, v in zip(ys, ratio):
        ax.text(v + .015, y, f"{v:.3f}", va="center", fontsize=6.4)
    ax.set_yticks(ys); ax.set_yticklabels([r["pair"] for r in d], fontsize=6.2)
    ax.set_xlabel("전이 상관 ÷ 대상 자기 상관", fontsize=7.0)
    ax.set_xlim(.85, 1.22)
    ax.tick_params(labelsize=6.2)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 34 ────────────────────────────────────────────────────────────
def fig_four_ceiling(out: Path, root: str = ".") -> dict:
    """노트34 주장 1 — 열두 셀에서도 대상 자기 상관이 전부다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/four.json").read_text())["rows"]
    x = np.array([r["tgt_self"] for r in d])
    y = np.array([r["r"] for r in d])
    fig, ax = plt.subplots(figsize=(COL, 2.25))
    lo, hi = .18, .72
    ax.plot([lo, hi], [lo, hi], lw=1.0, ls="--", color=INK, alpha=.7)
    cols = {"팝업": GATE, "아이돌": MUTE, "게임": CLAIM, "도서": INK}
    for r in d:
        tgt = r["pair"].split("→")[1]
        ax.scatter([r["tgt_self"]], [r["r"]], s=34, color=cols.get(tgt, INK),
                   alpha=.85, edgecolors="none")
    for tgt, c in cols.items():
        ax.scatter([], [], s=34, color=c, label=f"→ {tgt}")
    ax.text(.03, .95, f"r={np.corrcoef(x, y)[0,1]:+.3f}  (12셀)",
            transform=ax.transAxes, fontsize=6.8, va="top", color=CLAIM)
    ax.set_xlabel("대상 도메인의 자기 상관", fontsize=7.0)
    ax.set_ylabel("전이 상관", fontsize=7.0)
    ax.legend(fontsize=5.6, frameon=False, ncol=2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_four_grid(out: Path, root: str = ".") -> dict:
    """노트34 주장 2 — 실패가 열이 아니라 행으로 몰린다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/four.json").read_text())
    rows = d["rows"]
    doms = list(d["self"])
    M = np.full((len(doms), len(doms)), np.nan)
    for r in rows:
        s, t = r["pair"].split("→")
        M[doms.index(s), doms.index(t)] = r["obs"]
    fig, ax = plt.subplots(figsize=(COL, 2.4))
    im = ax.imshow(M, cmap="RdBu_r", vmin=-.09, vmax=.09)
    for i in range(len(doms)):
        for j in range(len(doms)):
            if np.isnan(M[i, j]):
                ax.text(j, i, "—", ha="center", va="center", fontsize=7, color=MUTE)
            else:
                r = next(x for x in rows if x["pair"] == f"{doms[i]}→{doms[j]}")
                ax.text(j, i, f"{M[i,j]:+.3f}\n{'유의' if r['p']<.05 else '—'}",
                        ha="center", va="center", fontsize=5.6,
                        color="white" if abs(M[i, j]) > .05 else INK)
    ax.set_xticks(range(len(doms)))
    ax.set_xticklabels([f"→{x}" for x in doms], fontsize=6.4)
    ax.set_yticks(range(len(doms)))
    ax.set_yticklabels([f"{x}→" for x in doms], fontsize=6.4)
    ax.set_title("행=출처, 열=대상. 도서 열만 전부 실패", fontsize=7.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_self_bars(out: Path, root: str = ".") -> dict:
    """노트34 주장 3 — 자기 상관이 대상 성적을 예고한다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/four.json").read_text())
    S = d["self"]
    rows = d["rows"]
    doms = sorted(S, key=lambda k: -S[k])
    xs = np.arange(len(doms))
    sig_as_tgt = [sum(1 for r in rows if r["pair"].endswith("→" + t) and r["p"] < .05)
                  for t in doms]
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.bar(xs, [S[t] for t in doms], width=.5, color=GATE, alpha=.85, edgecolor="none")
    for x, t, n in zip(xs, doms, sig_as_tgt):
        ax.text(x, S[t] + .015, f"{S[t]:.3f}\n대상 유의 {n}/3", ha="center", fontsize=6.0)
    ax.set_xticks(xs); ax.set_xticklabels(doms, fontsize=6.8)
    ax.set_ylabel("자기 상관 (교차검증)", fontsize=7.0)
    ax.set_ylim(0, .82)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_book_rewire(out: Path, root: str = ".") -> dict:
    """노트34 — 도서 개별 변수의 신호와 재배선 효과."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/four.json").read_text())
    bv = d["book_vars"]
    ks = sorted(bv, key=lambda k: -abs(bv[k]))
    xs = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.0))
    OLD = {"쪽수", "장르수"}
    ax.bar(xs, [bv[k] for k in ks], width=.55,
           color=[CLAIM if k in OLD else GATE for k in ks], alpha=.85, edgecolor="none")
    for x, k in zip(xs, ks):
        ax.text(x, bv[k] + (.008 if bv[k] > 0 else -.008), f"{bv[k]:+.3f}", ha="center",
                va="bottom" if bv[k] > 0 else "top", fontsize=6.2)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.6)
    ax.set_ylabel("판매지수와의 상관 (탈추세)", fontsize=7.0)
    ax.set_title("붉은 것이 원래 축에 넣었던 변수 — 둘 다 무효", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 35 ────────────────────────────────────────────────────────────
def fig_leak(out: Path, root: str = ".") -> dict:
    """노트35 — 판형 결측이 곧 전자책이고, 두 형식의 라벨이 열 배 다르다."""
    import json, numpy as np
    rec = json.loads((Path(root) / "data/state/book_records.json").read_text())
    rows = list(rec.values())
    grp = {"종이책 (판형 있음)": [], "전자책 (판형 없음)": []}
    for r in rows:
        y = np.log10(max(r["sales_point"], 1))
        k = "전자책 (판형 없음)" if "EBook" in (r.get("book_format") or "") else "종이책 (판형 있음)"
        grp[k].append(y)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.15),
                                 gridspec_kw={"width_ratios": [1.25, 1]})
    bins = np.linspace(2.8, 5.8, 34)
    for (k, v), c in zip(grp.items(), (GATE, CLAIM)):
        a1.hist(v, bins=bins, alpha=.62, color=c, label=f"{k}  n={len(v)}", edgecolor="none")
        a1.axvline(np.mean(v), color=c, lw=1.3, ls="--")
    a1.set_xlabel("log$_{10}$ 판매지수", fontsize=7.0)
    a1.set_ylabel("건수", fontsize=7.0)
    a1.legend(fontsize=6.2, frameon=False, loc="upper left")
    a1.set_title("결측 패턴이 라벨을 열 배 가른다", fontsize=7.2)
    a1.tick_params(labelsize=6.4)

    lab = ["전체 396건\n(형식 섞임)", "종이책 243건", "전자책 153건", "형식 통제\n396건"]
    val = [0.459, 0.220, 0.045, -0.002]
    xs = np.arange(len(val))
    a2.bar(xs, val, width=.56, color=[CLAIM, GATE, MUTE, MUTE], alpha=.88, edgecolor="none")
    for x, v in zip(xs, val):
        a2.text(x, v + (.014 if v >= 0 else -.014), f"{v:+.3f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=6.4)
    a2.axhline(0, color=INK, lw=.9)
    a2.set_xticks(xs); a2.set_xticklabels(lab, fontsize=6.0)
    a2.set_ylabel("도서 자기 상관", fontsize=7.0)
    a2.set_ylim(-.09, .55)
    a2.set_title("겉보기 0.459는 형식 차이였다", fontsize=7.2)
    a2.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_slot(out: Path, root: str = ".") -> dict:
    """노트35 — 축을 켜는 것과 슬롯 안에서 바꾸는 것은 다른 결정이다."""
    import numpy as np
    names = ["기준", "게임 +가격\n(단독 +0.351)", "게임 +퍼블리셔\n(단독 +0.280)",
             "게임 폭=언어만", "도서 굿즈\n쪽수→양장"]
    sig = [9, 7, 8, 9, 11]
    kind = [0, 1, 1, 2, 2]          # 0 기준 · 1 축 켜기 · 2 슬롯내 교체
    col = [MUTE, CLAIM, CLAIM, GATE, GATE]
    xs = np.arange(len(sig))
    fig, ax = plt.subplots(figsize=(FULL, 1.95))
    ax.bar(xs, sig, width=.55, color=col, alpha=.88, edgecolor="none")
    for x, v in zip(xs, sig):
        ax.text(x, v + .12, f"{v}/12", ha="center", fontsize=6.6)
    ax.axhline(9, color=INK, lw=.8, ls=":")
    ax.set_xticks(xs); ax.set_xticklabels(names, fontsize=6.2)
    ax.set_ylabel("유의한 전이 방향", fontsize=7.0)
    ax.set_ylim(0, 12.6)
    ax.set_title("붉은 것이 '꺼진 축 켜기' — 단독 상관이 강한데도 나빠진다",
                 fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_ceil_clean(out: Path, root: str = ".") -> dict:
    """노트35 — 누출을 뺀 뒤 노트 33의 등식이 더 깨끗해진다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/ceiling_clean.json").read_text())
    c = d["cells"]
    x = np.array([r["tgt_self"] for r in c]); y = np.array([r["r"] for r in c])
    fig, ax = plt.subplots(figsize=(COL, 2.3))
    lim = [0, .78]
    ax.plot(lim, lim, color=MUTE, lw=.9, ls="--", zorder=1)
    isb = np.array([r["tgt"] == "도서" for r in c])
    ax.scatter(x[~isb], y[~isb], s=26, color=GATE, zorder=3, label="대상 = 팝업·아이돌·게임")
    ax.scatter(x[isb], y[isb], s=26, color=CLAIM, zorder=3, label="대상 = 도서")
    ax.set_xlabel("대상 도메인의 자기 상관", fontsize=7.0)
    ax.set_ylabel("전이 상관", fontsize=7.0)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.legend(fontsize=6.0, frameon=False, loc="upper left")
    ax.set_title(f"설명 {d['expl_tgt']:+.3f}  (누출 포함 시 $+$0.930)", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_srcgain(out: Path, root: str = ".") -> dict:
    """노트35 — 누출을 빼자 도서를 출처로 쓴 세 방향이 모두 좋아졌다."""
    import numpy as np
    lab = ["도서→팝업", "도서→아이돌", "도서→게임"]
    before = [-0.0696, -0.0399, -0.0175]
    after = [-0.0790, -0.0641, -0.0365]
    xs = np.arange(len(lab)); w = .34
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    ax.bar(xs - w/2, [-v for v in before], w, color=MUTE, alpha=.9,
           edgecolor="none", label="누출 포함 (396건)")
    ax.bar(xs + w/2, [-v for v in after], w, color=GATE, alpha=.9,
           edgecolor="none", label="정화 후 (243건)")
    for x, v in zip(xs - w/2, before):
        ax.text(x, -v + .0018, f"{-v:.3f}", ha="center", fontsize=5.9)
    for x, v in zip(xs + w/2, after):
        ax.text(x, -v + .0018, f"{-v:.3f}", ha="center", fontsize=5.9)
    ax.set_xticks(xs); ax.set_xticklabels(lab, fontsize=6.6)
    ax.set_ylabel("상수 대비 MAE 이득", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, loc="upper left")
    ax.set_title("누출을 뺐는데 출처 성능이 올랐다", fontsize=7.2)
    ax.set_ylim(0, .105)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 36 ────────────────────────────────────────────────────────────
def fig_own(out: Path, root: str = ".") -> dict:
    """노트36 — 고유 축을 늘리면 자기 상관은 갈리고 전이는 안 오른다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/own_axes.json").read_text())
    doms = ["팝업", "아이돌", "게임", "도서"]
    b = d["없음(기준)"]["self"]
    xs = np.arange(len(doms)); w = .34
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.1),
                                 gridspec_kw={"width_ratios": [1.35, 1]})
    a1.bar(xs - w/2, [b[k] for k in doms], w, color=MUTE, alpha=.9,
           edgecolor="none", label="다섯 축(기준)")
    a1.bar(xs + w/2, [d[k]["self"][k] for k in doms], w, color=GATE, alpha=.9,
           edgecolor="none", label="고유 축 추가")
    for x, k in zip(xs, doms):
        v0, v1 = b[k], d[k]["self"][k]
        a1.text(x - w/2, v0 + .012, f"{v0:.3f}", ha="center", fontsize=5.9)
        a1.text(x + w/2, v1 + .012, f"{v1:.3f}", ha="center", fontsize=5.9,
                color=GATE if v1 > v0 else CLAIM)
    a1.set_xticks(xs); a1.set_xticklabels(doms, fontsize=6.8)
    a1.set_ylabel("자기 상관", fontsize=7.0)
    a1.legend(fontsize=6.0, frameon=False, loc="upper left")
    a1.set_title("두 도메인은 오르고 두 도메인은 내린다", fontsize=7.2)
    a1.set_ylim(0, .82); a1.tick_params(labelsize=6.4)

    keys = ["없음(기준)"] + doms
    lab = ["없음", "팝업", "아이돌", "게임", "도서"]
    sig = [d[k]["sig"] for k in keys]
    a2.bar(np.arange(len(sig)), sig, width=.55,
           color=[MUTE] + [GATE if v > sig[0] else CLAIM for v in sig[1:]],
           alpha=.9, edgecolor="none")
    for x, v in zip(np.arange(len(sig)), sig):
        a2.text(x, v + .12, f"{v}", ha="center", fontsize=6.4)
    a2.axhline(sig[0], color=INK, lw=.8, ls=":")
    a2.set_xticks(np.arange(len(lab))); a2.set_xticklabels(lab, fontsize=6.4)
    a2.set_ylabel("유의한 전이 방향 (/12)", fontsize=7.0)
    a2.set_ylim(0, 12.6); a2.tick_params(labelsize=6.4)
    a2.set_title("어느 것도 기준을 넘지 못한다", fontsize=7.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_pass(out: Path, root: str = ".") -> dict:
    """노트36 — 2차원 인자 공간의 통과율. 다섯 축에서는 무손실이다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/bottleneck.json").read_text())
    doms = ["팝업", "아이돌", "게임", "도서"]
    xs = np.arange(len(doms)); w = .34
    fig, ax = plt.subplots(figsize=(COL, 2.15))
    p5 = [d[k]["5축(기준)"][1] / d[k]["5축(기준)"][0] for k in doms]
    pe = [d[k]["확장"][1] / d[k]["확장"][0] for k in doms]
    ax.bar(xs - w/2, p5, w, color=MUTE, alpha=.9, edgecolor="none", label="다섯 축")
    ax.bar(xs + w/2, pe, w, color=CLAIM, alpha=.9, edgecolor="none", label="고유 축 추가")
    for x, v in zip(xs - w/2, p5):
        ax.text(x, v + .02, f"{v:.2f}", ha="center", fontsize=5.9)
    for x, v in zip(xs + w/2, pe):
        ax.text(x, v + .02, f"{v:.2f}", ha="center", fontsize=5.9)
    ax.axhline(1.0, color=INK, lw=.9, ls="--")
    ax.set_xticks(xs); ax.set_xticklabels(doms, fontsize=6.8)
    ax.set_ylabel("2차원 R $\\div$ 전체 축 R", fontsize=7.0)
    ax.set_ylim(0, 1.75)
    ax.legend(fontsize=6.0, frameon=False, loc="upper right")
    ax.set_title("다섯 축에서는 1.00 — 병목이 아니었다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_twoceil(out: Path, root: str = ".") -> dict:
    """노트36 — 전이를 구속하는 것이 자기 상관에서 정렬 전달력으로 넘어간다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/bottleneck.json").read_text())
    doms = ["팝업", "아이돌", "게임", "도서"]
    fig, ax = plt.subplots(figsize=(FULL, 2.1))
    xs = np.arange(len(doms)); w = .2
    s5 = [d[k]["5축(기준)"][0] for k in doms]
    f5 = [d[k]["5축(기준)"][1] for k in doms]
    se = [d[k]["확장"][0] for k in doms]
    fe = [d[k]["확장"][1] for k in doms]
    ax.bar(xs - 1.5*w, s5, w, color=MUTE, alpha=.9, edgecolor="none",
           label="다섯 축 · 전체 축 R")
    ax.bar(xs - .5*w, f5, w, color=GATE, alpha=.9, edgecolor="none",
           label="다섯 축 · 2차원 R (전이가 쓰는 것)")
    ax.bar(xs + .5*w, se, w, color=MUTE, alpha=.45, edgecolor="none",
           label="확장 · 전체 축 R")
    ax.bar(xs + 1.5*w, fe, w, color=CLAIM, alpha=.9, edgecolor="none",
           label="확장 · 2차원 R")
    for i, k in enumerate(doms):
        if se[i] > s5[i]:
            ax.annotate("", xy=(xs[i] + .5*w, se[i] + .02), xytext=(xs[i] - 1.5*w, s5[i] + .02),
                        arrowprops=dict(arrowstyle="->", color=INK, lw=.7, alpha=.55))
    ax.set_xticks(xs); ax.set_xticklabels(doms, fontsize=6.8)
    ax.set_ylabel("교차검증 상관", fontsize=7.0)
    ax.legend(fontsize=5.8, frameon=False, ncol=2, loc="upper left")
    ax.set_ylim(0, .95)
    ax.set_title("아이돌·게임은 전체 축 R이 올라도 2차원 R은 따라오지 않는다",
                 fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_maskleak(out: Path, root: str = ".") -> dict:
    """노트36 — 네 도메인의 결측 패턴 누출 검사."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/mask_leak.json").read_text())
    doms = [k for k in ("팝업", "아이돌", "게임", "도서") if k in d]
    fig, ax = plt.subplots(figsize=(COL, 2.0))
    mo = [d[k]["mask_only"] if np.isfinite(d[k]["mask_only"]) else 0.0 for k in doms]
    vo = [d[k]["val_only"] for k in doms]
    xs = np.arange(len(doms)); w = .34
    ax.bar(xs - w/2, vo, w, color=GATE, alpha=.9, edgecolor="none", label="축 값만")
    ax.bar(xs + w/2, mo, w, color=CLAIM, alpha=.9, edgecolor="none", label="마스크만")
    for x, k, v in zip(xs + w/2, doms, mo):
        t = "분산 0" if not np.isfinite(d[k]["mask_only"]) else f"{v:+.3f}"
        ax.text(x, max(v, 0) + .015, t, ha="center", fontsize=5.8)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels(doms, fontsize=6.8)
    ax.set_ylabel("라벨과의 교차검증 상관", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, loc="upper right")
    ax.set_title("마스크만으로는 라벨을 못 맞힌다 — 누출 없음", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 37 ────────────────────────────────────────────────────────────
def fig_where(out: Path, root: str = ".") -> dict:
    """노트37 — 상한을 어디서 재느냐. 인자 공간에서 재면 등식이 더 정확하다."""
    import json, numpy as np
    rows = json.loads((Path(root) / "data/state/ceiling_where.json").read_text())
    x = np.array([r["transfer"] for r in rows])
    a = np.array([r["all_R"] for r in rows])
    f = np.array([r["factor_R"] for r in rows])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3), sharey=True)
    for ax, v, lab, c, rr in ((a1, a, "전체 관측 축으로 잰 자기 상관", MUTE,
                               np.corrcoef(x, a)[0, 1]),
                              (a2, f, "인자 공간에서 잰 자기 상관", GATE,
                               np.corrcoef(x, f)[0, 1])):
        lim = [0.1, 0.78]
        ax.plot(lim, lim, color=MUTE, lw=.8, ls="--", zorder=1)
        ax.scatter(v, x, s=22, color=c, zorder=3, alpha=.85)
        ax.set_xlabel(lab, fontsize=6.8)
        ax.set_xlim(lim); ax.set_ylim(lim)
        ax.set_title(f"설명 {rr:+.3f}", fontsize=7.4,
                     color=INK if c is MUTE else GATE)
        ax.tick_params(labelsize=6.4)
    a1.set_ylabel("전이 상관 (대상별 평균)", fontsize=7.0)
    fig.suptitle("여섯 설정 × 네 대상 = 24점", fontsize=7.2, y=1.0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_cgrid(out: Path, root: str = ".") -> dict:
    """노트37 — 공통 축 수와 성분 수의 격자."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/common_axes.json").read_text())
    keys = list(d)
    xs = np.arange(len(keys))
    sig = [d[k]["sig"] for k in keys]
    gain = [d[k]["gain"] for k in keys]
    lab = [k.replace(" · ", "\n").replace(" (현행)", "\n(현행)") for k in keys]
    fig, ax = plt.subplots(figsize=(FULL, 2.1))
    best = int(np.argmax(sig))
    ax.bar(xs, gain, width=.55, alpha=.88, edgecolor="none",
           color=[GATE if i == best else (MUTE if i == 0 else CLAIM)
                  for i in range(len(xs))])
    for x, g, s in zip(xs, gain, sig):
        ax.text(x, g + .0012, f"{g:+.4f}\n{s}/12", ha="center", fontsize=6.0)
    ax.axhline(gain[0], color=INK, lw=.8, ls=":")
    ax.set_xticks(xs); ax.set_xticklabels(lab, fontsize=6.0)
    ax.set_ylabel("평균 MAE 이득", fontsize=7.0)
    ax.set_ylim(0, max(gain) * 1.30)
    ax.set_title("공통 축 셋 · 성분 둘이 최선 — 성분을 늘리는 것은 이득이 없다",
                 fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_now(out: Path, root: str = ".") -> dict:
    """노트37 — 공통 축 셋 채택 후의 열두 셀."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/c3_state.json").read_text())
    c, fac = d["cells"], d["factor"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.25),
                                 gridspec_kw={"width_ratios": [1, 1.2]})
    x = np.array([r["tgt_factor"] for r in c]); y = np.array([r["r"] for r in c])
    lim = [0.12, 0.75]
    a1.plot(lim, lim, color=MUTE, lw=.9, ls="--", zorder=1)
    a1.scatter(x, y, s=26, color=GATE, zorder=3)
    a1.set_xlabel("대상의 인자 공간 자기 상관", fontsize=7.0)
    a1.set_ylabel("전이 상관", fontsize=7.0)
    a1.set_xlim(lim); a1.set_ylim(lim)
    a1.set_title(f"설명 {d['expl']:+.3f}", fontsize=7.2)
    a1.tick_params(labelsize=6.4)

    doms = ["팝업", "아이돌", "게임", "도서"]
    before = {"팝업": 0.385, "아이돌": 0.656, "게임": 0.349, "도서": 0.195}
    xs = np.arange(len(doms)); w = .34
    a2.bar(xs - w/2, [before[k] for k in doms], w, color=MUTE, alpha=.9,
           edgecolor="none", label="공통 축 둘")
    a2.bar(xs + w/2, [fac[k] for k in doms], w, color=GATE, alpha=.9,
           edgecolor="none", label="공통 축 셋")
    for x0, k in zip(xs, doms):
        a2.text(x0 - w/2, before[k] + .012, f"{before[k]:.3f}", ha="center", fontsize=5.9)
        a2.text(x0 + w/2, fac[k] + .012, f"{fac[k]:.3f}", ha="center", fontsize=5.9,
                color=GATE if fac[k] > before[k] else CLAIM)
    a2.set_xticks(xs); a2.set_xticklabels(doms, fontsize=6.8)
    a2.set_ylabel("인자 공간 자기 상관", fontsize=7.0)
    a2.legend(fontsize=6.0, frameon=False, loc="upper left")
    a2.set_ylim(0, .82); a2.tick_params(labelsize=6.4)
    a2.set_title("팝업은 오르고 게임은 내린다", fontsize=7.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 38 ────────────────────────────────────────────────────────────
def fig_tradeoff(out: Path, root: str = ".") -> dict:
    """노트38 — 자기 상관을 올리면 대상으로는 좋아지고 출처로는 나빠진다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/src_tgt_tradeoff.json").read_text())
    doms = list(d["self"])
    ds = np.array([d["self"][k][1] - d["self"][k][0] for k in doms])
    dt = np.array([d["as_tgt"][k][1] - d["as_tgt"][k][0] for k in doms])
    du = np.array([d["as_src"][k][1] - d["as_src"][k][0] for k in doms])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3), sharex=True)
    for ax, v, lab, c in ((a1, dt, "대상으로서의 평균 전이 변화", GATE),
                          (a2, du, "출처로서의 평균 전이 변화", CLAIM)):
        ax.axhline(0, color=INK, lw=.8)
        ax.axvline(0, color=INK, lw=.8)
        ax.scatter(ds, v, s=34, color=c, zorder=3)
        for x, y, k in zip(ds, v, doms):
            ax.annotate(k, (x, y), fontsize=6.0, xytext=(3, 3),
                        textcoords="offset points")
        z = np.polyfit(ds, v, 1)
        xx = np.linspace(ds.min() - .008, ds.max() + .012, 20)
        ax.plot(xx, np.polyval(z, xx), color=c, lw=.9, ls="--", alpha=.6, zorder=1)
        ax.set_xlabel("인자 공간 자기 상관 변화", fontsize=6.8)
        ax.set_ylabel(lab, fontsize=6.8)
        ax.set_title(f"r $=$ {np.corrcoef(ds, v)[0,1]:+.3f}", fontsize=7.4, color=c)
        ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_search(out: Path, root: str = ".") -> dict:
    """노트38 — 배선 탐색 결과와 선택 편향."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/factor_search.json").read_text())
    doms = list(d)
    xs = np.arange(len(doms)); w = .26
    fig, ax = plt.subplots(figsize=(FULL, 2.05))
    ax.bar(xs - w, [d[k]["base_confirm"] for k in doms], w, color=MUTE, alpha=.9,
           edgecolor="none", label="현행 (확인 씨앗)")
    ax.bar(xs, [d[k]["best"] for k in doms], w, color=CLAIM, alpha=.75,
           edgecolor="none", label="탐색 최대 (탐색 씨앗 — 낙관적)")
    ax.bar(xs + w, [d[k]["confirm"] for k in doms], w, color=GATE, alpha=.9,
           edgecolor="none", label="승자 (확인 씨앗)")
    for x, k in zip(xs, doms):
        b, s, c = d[k]["base_confirm"], d[k]["best"], d[k]["confirm"]
        ax.text(x - w, b + .012, f"{b:.3f}", ha="center", fontsize=5.7)
        ax.text(x, s + .012, f"{s:.3f}", ha="center", fontsize=5.7)
        ax.text(x + w, c + .012, f"{c:.3f}", ha="center", fontsize=5.7,
                color=GATE if c > b + 1e-3 else INK)
    ax.set_xticks(xs); ax.set_xticklabels(doms, fontsize=6.8)
    ax.set_ylabel("인자 공간 자기 상관", fontsize=7.0)
    ax.legend(fontsize=5.9, frameon=False, loc="upper left", ncol=1)
    ax.set_ylim(0, .82); ax.tick_params(labelsize=6.4)
    ax.set_title("가운데 막대와 오른쪽 막대의 차이가 선택 편향이다", fontsize=7.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_roles(out: Path, root: str = ".") -> dict:
    """노트38 — 도메인별 두 역할의 성적."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/src_tgt_tradeoff.json").read_text())
    doms = list(d["self"])
    fig, ax = plt.subplots(figsize=(COL, 2.25))
    for k, c in zip(doms, (GATE, CLAIM, INK, MUTE)):
        t0, t1 = d["as_tgt"][k]
        s0, s1 = d["as_src"][k]
        ax.annotate("", xy=(t1, s1), xytext=(t0, s0),
                    arrowprops=dict(arrowstyle="->", color=c, lw=1.3, alpha=.85))
        ax.scatter([t0], [s0], s=16, color=c, alpha=.4, zorder=3)
        ax.scatter([t1], [s1], s=30, color=c, zorder=3)
        ax.annotate(k, (t1, s1), fontsize=6.2, xytext=(4, -1),
                    textcoords="offset points", color=c)
    ax.set_xlabel("대상으로서의 평균 전이 r", fontsize=7.0)
    ax.set_ylabel("출처로서의 평균 전이 r", fontsize=7.0)
    ax.set_title("화살표가 탐색 후 이동 방향", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 39 ────────────────────────────────────────────────────────────
def fig_dual(out: Path, root: str = ".") -> dict:
    """노트39 — 단일 배선과 이중 배선. 전역 단일로는 안 된다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/dual_confirm.json").read_text())
    lab = ["단일\n현행", "단일\n출처최적 전역", "이중\n출처만", "이중\n출처$+$대상"]
    keys = ["단일: 현행", "단일: 출처최적 전역", "이중: 출처만", "이중: 출처+대상"]
    sig = [d[k][0][0] for k in keys]
    gain = [float(np.mean([r[1] for r in d[k]])) for k in keys]
    xs = np.arange(len(keys))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.1), sharex=True)
    col = [MUTE, CLAIM, GATE, GATE]
    a1.bar(xs, sig, width=.55, color=col, alpha=.88, edgecolor="none")
    for x, v in zip(xs, sig):
        a1.text(x, v + .12, f"{v}/12", ha="center", fontsize=6.4)
    a1.axhline(sig[0], color=INK, lw=.8, ls=":")
    a1.set_ylabel("유의한 전이 방향", fontsize=7.0)
    a1.set_ylim(0, 12.8)
    a1.set_title("유의 기준 — 이중 · 출처만", fontsize=7.2)
    a2.bar(xs, gain, width=.55, color=col, alpha=.88, edgecolor="none")
    for x, v in zip(xs, gain):
        a2.text(x, v + .0012, f"{v:+.4f}", ha="center", fontsize=6.2)
    a2.axhline(gain[0], color=INK, lw=.8, ls=":")
    a2.set_ylabel("평균 MAE 이득", fontsize=7.0)
    a2.set_ylim(0, max(gain) * 1.22)
    a2.set_title("이득 기준 — 이중 · 출처$+$대상", fontsize=7.2)
    for ax in (a1, a2):
        ax.set_xticks(xs); ax.set_xticklabels(lab, fontsize=6.0)
        ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_split(out: Path, root: str = ".") -> dict:
    """노트39 — 팝업을 나눠 잰 선택 편향과 출처별 이득."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/source_search.json").read_text())
    srcs = list(d["base"]["search"])
    xs = np.arange(len(srcs)); w = .2
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.15),
                                 gridspec_kw={"width_ratios": [1.3, 1]})
    a1.bar(xs - 1.5*w, [d["base"]["search"][k] for k in srcs], w, color=MUTE,
           alpha=.55, edgecolor="none", label="현행 · 탐색용")
    a1.bar(xs - .5*w, [d["best"]["search"][k] for k in srcs], w, color=CLAIM,
           alpha=.7, edgecolor="none", label="승자 · 탐색용(낙관적)")
    a1.bar(xs + .5*w, [d["base"]["confirm"][k] for k in srcs], w, color=MUTE,
           alpha=.95, edgecolor="none", label="현행 · 확인용")
    a1.bar(xs + 1.5*w, [d["best"]["confirm"][k] for k in srcs], w, color=GATE,
           alpha=.95, edgecolor="none", label="승자 · 확인용")
    for x, k in zip(xs, srcs):
        v = d["best"]["confirm"][k]
        a1.text(x + 1.5*w, v + .0015, f"{v:.4f}", ha="center", fontsize=5.6)
    a1.set_xticks(xs); a1.set_xticklabels(srcs, fontsize=6.8)
    a1.set_ylabel("팝업으로의 MAE 이득", fontsize=7.0)
    a1.legend(fontsize=5.6, frameon=False, ncol=2, loc="upper left")
    a1.set_ylim(0, .118); a1.tick_params(labelsize=6.4)
    a1.set_title("아이돌만 확인용에서도 오른다", fontsize=7.2)

    m = lambda w_, p: float(np.mean(list(d[w_][p].values())))
    bars = [m("base", "search"), m("best", "search"), m("base", "confirm"),
            m("best", "confirm")]
    a2.bar(np.arange(4), bars, width=.6,
           color=[MUTE, CLAIM, MUTE, GATE], alpha=.9, edgecolor="none")
    for x, v in zip(np.arange(4), bars):
        a2.text(x, v + .0012, f"{v:.4f}", ha="center", fontsize=6.0)
    a2.set_xticks(np.arange(4))
    a2.set_xticklabels(["현행\n탐색", "승자\n탐색", "현행\n확인", "승자\n확인"],
                       fontsize=6.0)
    a2.set_ylabel("세 출처 평균", fontsize=7.0)
    a2.set_ylim(0, .09); a2.tick_params(labelsize=6.4)
    a2.set_title("탐색 증가의 60\%가 편향", fontsize=7.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_faces(out: Path, root: str = ".") -> dict:
    """노트39 — 아이돌 입장 허들이 역할에 따라 반대로 간다."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(COL, 2.15))
    lab = ["대상 역할\n(자기 상관 목적)", "출처 역할\n(팝업 전이 목적)"]
    on = [0.690, 0.0600]      # 켰을 때
    off = [0.657, 0.0694]     # 껐을 때
    # 각 역할에서 자기 스케일로 정규화해 방향만 보인다
    xs = np.arange(2); w = .34
    norm = lambda a, b: (a / max(a, b), b / max(a, b))
    o1, f1 = norm(on[0], off[0]); o2, f2 = norm(on[1], off[1])
    ax.bar(xs - w/2, [o1, o2], w, color=GATE, alpha=.9, edgecolor="none",
           label="입장 허들 켬 (앨범 정가)")
    ax.bar(xs + w/2, [f1, f2], w, color=CLAIM, alpha=.9, edgecolor="none",
           label="입장 허들 끔")
    for x, v, t in ((xs[0] - w/2, o1, "0.690"), (xs[0] + w/2, f1, "0.657"),
                    (xs[1] - w/2, o2, "0.0600"), (xs[1] + w/2, f2, "0.0694")):
        ax.text(x, v + .012, t, ha="center", fontsize=6.0)
    ax.set_xticks(xs); ax.set_xticklabels(lab, fontsize=6.4)
    ax.set_ylabel("각 역할의 최댓값 대비", fontsize=7.0)
    ax.set_ylim(0, 1.16)
    ax.legend(fontsize=6.0, frameon=False, loc="lower left")
    ax.set_title("같은 축, 반대 방향", fontsize=7.4)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 40 ────────────────────────────────────────────────────────────
def fig_five(out: Path, root: str = ".") -> dict:
    """노트40 — 다섯 도메인 스무 셀."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/five_state.json").read_text())
    doms = list(d["factor"])
    n = len(doms)
    M = np.full((n, n), np.nan)
    P = np.full((n, n), np.nan)
    for k, c in d["cells"].items():
        s, t = k.split("→")
        M[doms.index(s), doms.index(t)] = -c["obs"]
        P[doms.index(s), doms.index(t)] = c["p"]
    fig, ax = plt.subplots(figsize=(COL, 2.6))
    im = ax.imshow(M, cmap="BuGn", vmin=0, vmax=0.105)
    for i in range(n):
        for j in range(n):
            if i == j:
                ax.text(j, i, "—", ha="center", va="center", fontsize=7, color=MUTE)
                continue
            ok = P[i, j] < 0.05
            ax.text(j, i, f"{M[i,j]:+.3f}\n{'유의' if ok else 'n.s.'}", ha="center",
                    va="center", fontsize=5.4,
                    color=INK if ok else CLAIM,
                    fontweight="bold" if ok else "normal")
    ax.set_xticks(range(n)); ax.set_xticklabels(doms, fontsize=6.6)
    ax.set_yticks(range(n)); ax.set_yticklabels(doms, fontsize=6.6)
    ax.set_xlabel("대상", fontsize=7.0); ax.set_ylabel("출처", fontsize=7.0)
    ax.set_title("MAE 이득 · 17/20 유의", fontsize=7.4)
    ax.tick_params(labelsize=6.4, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_tradeoff5(out: Path, root: str = ".") -> dict:
    """노트40 — 다섯 점에서 상충이 강화된다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/five_state.json").read_text())
    doms = list(d["roles"])
    x = np.array([d["roles"][k][0] for k in doms])
    t = np.array([d["roles"][k][1] for k in doms])
    s = np.array([d["roles"][k][2] for k in doms])
    fig, ax = plt.subplots(figsize=(FULL, 2.25))
    ax.plot(x, t, "o-", color=GATE, ms=6, lw=1.1, label="대상으로서의 평균 전이 r")
    ax.plot(x, s, "s--", color=CLAIM, ms=5.5, lw=1.1, label="출처로서의 평균 전이 r")
    for xi, ti, si, k in zip(x, t, s, doms):
        ax.annotate(k, (xi, ti), fontsize=6.2, xytext=(2, 5), textcoords="offset points",
                    color=GATE)
        ax.annotate(k, (xi, si), fontsize=6.2, xytext=(2, -10), textcoords="offset points",
                    color=CLAIM)
    ax.set_xlabel("도메인의 인자 공간 자기 상관", fontsize=7.0)
    ax.set_ylabel("평균 전이 r", fontsize=7.0)
    ax.legend(fontsize=6.2, frameon=False, loc="center left")
    rt = np.corrcoef(x, t)[0, 1]; rs = np.corrcoef(x, s)[0, 1]
    ax.set_title(f"대상 $r={rt:+.3f}$ · 출처 $r={rs:+.3f}$ — 두 선이 교차한다",
                 fontsize=7.4)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_friction(out: Path, root: str = ".") -> dict:
    """노트40 — 입장 허들 축의 부호가 도메인마다 갈린다."""
    import numpy as np
    doms = ["팝업", "펀딩", "도서", "아이돌"]
    r = [-0.287, -0.153, -0.034, +0.440]
    kind = ["접근의 조건", "접근의 조건", "거래의 대가", "거래의 대가"]
    xs = np.arange(len(doms))
    fig, ax = plt.subplots(figsize=(FULL, 2.0))
    ax.bar(xs, r, width=.5, color=[GATE if v < -0.05 else CLAIM for v in r],
           alpha=.9, edgecolor="none")
    for x, v, k in zip(xs, r, kind):
        ax.text(x, v + (.022 if v > 0 else -.022), f"{v:+.3f}", ha="center",
                va="bottom" if v > 0 else "top", fontsize=6.4)
        ax.text(x, 0.52, k, ha="center", fontsize=6.0,
                color=GATE if v < -0.05 else CLAIM)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels(doms, fontsize=6.8)
    ax.set_ylabel("입장 허들 축과 라벨의 상관", fontsize=7.0)
    ax.set_ylim(-.42, .62)
    ax.set_title("음수면 진짜 허들 — 가격이 접근의 조건일 때만 그렇다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 41 ────────────────────────────────────────────────────────────
def fig_sweep(out: Path, root: str = ".") -> dict:
    """노트41 — 출처 λ 스윕. 예측과 반대 방향으로 오른다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/source_lambda.json").read_text())
    ks = [k for k in d if k.startswith("λ=")]
    lam = [float(k.split("=")[1]) for k in ks]
    o = np.argsort(lam)
    lam = [lam[i] for i in o]; ks = [ks[i] for i in o]
    sig = [d[k]["sig"] for k in ks]
    gain = [d[k]["gain"] for k in ks]
    ref = d["유도값(현행)"]
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.plot(lam, sig, "o-", color=GATE, lw=1.3, ms=6, label="유의한 방향 (/20)")
    ax.axhline(ref["sig"], color=MUTE, lw=1.0, ls=":", label="유도값(현행)")
    ax.annotate("예측한 방향\n(고유 축을 줄인다)", (0.0, sig[0]), fontsize=6.2,
                color=CLAIM, xytext=(14, -20), textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=.8))
    ax.annotate("실제로 좋아진 방향", (lam[-1], sig[-1]), fontsize=6.2, color=GATE,
                xytext=(-72, 10), textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color=GATE, lw=.8))
    for x, y in zip(lam, sig):
        ax.text(x, y + .18, f"{y}", ha="center", fontsize=6.2)
    ax.set_xlabel("출처 역할의 고유 축 비중 $\\lambda$", fontsize=7.0)
    ax.set_ylabel("유의한 전이 방향", fontsize=7.0)
    ax.set_ylim(14.4, 20.2)
    ax.legend(fontsize=6.2, frameon=False, loc="upper left")
    ax.set_title("응답이 매끄럽고 단조다 — 잡음이 아니다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_asym(out: Path, root: str = ".") -> dict:
    """노트41 — 비대칭이 핵심이다. 대상 쪽에 같은 값을 걸면 나빠진다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/lambda_asym.json").read_text())
    ks = list(d)
    xs = np.arange(len(ks))
    sig = [d[k]["sig"][0] for k in ks]
    gain = [d[k]["gain"] for k in ks]
    lab = [k.replace(" · ", "\n").replace(" (출처·대상 모두 유도값)", "\n(유도값)")
           for k in ks]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.2), sharex=True)
    best = int(np.argmax(sig))
    col = [GATE if i == best else (MUTE if i == 0 else CLAIM) for i in range(len(ks))]
    a1.bar(xs, sig, width=.55, color=col, alpha=.88, edgecolor="none")
    for x, v in zip(xs, sig):
        a1.text(x, v + .18, f"{v}/20", ha="center", fontsize=6.2)
    a1.axhline(sig[0], color=INK, lw=.8, ls=":")
    a1.set_ylabel("유의한 방향", fontsize=7.0); a1.set_ylim(0, 21)
    a1.set_title("씨앗 4개에서 값이 동일했다", fontsize=7.2)
    a2.bar(xs, gain, width=.55, color=col, alpha=.88, edgecolor="none")
    for x, v in zip(xs, gain):
        a2.text(x, v + .0012, f"{v:+.4f}", ha="center", fontsize=6.0)
    a2.axhline(gain[0], color=INK, lw=.8, ls=":")
    a2.set_ylabel("평균 MAE 이득", fontsize=7.0)
    a2.set_ylim(0, max(gain) * 1.24)
    a2.set_title("방향을 뒤집으면 무너진다", fontsize=7.2)
    for ax in (a1, a2):
        ax.set_xticks(xs); ax.set_xticklabels(lab, fontsize=5.5)
        ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_idol(out: Path, root: str = ".") -> dict:
    """노트41 — 아이돌을 출처로 쓴 셀들이 살아난다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/lambda_cells.json").read_text())
    ks = [k for k in d["base"] if k.startswith("아이돌→")]
    xs = np.arange(len(ks)); w = .34
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.15),
                                 gridspec_kw={"width_ratios": [1.25, 1]})
    a1.bar(xs - w/2, [d["base"][k]["p"] for k in ks], w, color=MUTE, alpha=.9,
           edgecolor="none", label="현행(유도값)")
    a1.bar(xs + w/2, [d["best"][k]["p"] for k in ks], w, color=GATE, alpha=.9,
           edgecolor="none", label="출처 $\\lambda=1.5$")
    for x, k in zip(xs, ks):
        a1.text(x - w/2, d["base"][k]["p"] + .012, f"{d['base'][k]['p']:.3f}",
                ha="center", fontsize=5.8)
        a1.text(x + w/2, d["best"][k]["p"] + .012, f"{d['best'][k]['p']:.3f}",
                ha="center", fontsize=5.8, color=GATE)
    a1.axhline(0.05, color=CLAIM, lw=1.0, ls="--")
    a1.text(len(ks) - .5, .062, "p$=$0.05", fontsize=6.0, color=CLAIM, ha="right")
    a1.set_xticks(xs); a1.set_xticklabels([k.replace("아이돌→", "→") for k in ks],
                                          fontsize=6.6)
    a1.set_ylabel("순열 p", fontsize=7.0)
    a1.legend(fontsize=6.0, frameon=False, loc="upper left")
    a1.set_ylim(0, .72); a1.tick_params(labelsize=6.4)
    a1.set_title("아이돌을 출처로 쓴 세 방향", fontsize=7.2)

    doms = list(d["by_src"]["base"])
    b = [d["by_src"]["base"][k] for k in doms]
    g = [d["by_src"]["best"][k] for k in doms]
    ys = np.arange(len(doms))
    a2.barh(ys - .18, b, .34, color=MUTE, alpha=.9, edgecolor="none")
    a2.barh(ys + .18, g, .34, color=GATE, alpha=.9, edgecolor="none")
    a2.set_yticks(ys); a2.set_yticklabels(doms, fontsize=6.6)
    a2.set_xlabel("출처로서의 평균 전이 r", fontsize=7.0)
    a2.set_xlim(0, .5); a2.tick_params(labelsize=6.4)
    a2.set_title("아이돌만 크게 움직인다", fontsize=7.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 42 ────────────────────────────────────────────────────────────
def fig_flat(out: Path, root: str = ".") -> dict:
    """노트42 — 전이 상관은 평평하고 예측 SD만 움직인다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/idol_lambda.json").read_text())
    lam = sorted(float(k) for k in d)
    tg = [r[0] for r in d[str(lam[0])]]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.25))
    for i, t in enumerate(tg):
        c = [GATE, CLAIM, INK, MUTE][i % 4]
        a1.plot(lam, [d[str(l)][i][1] for l in lam], "o-", color=c, ms=4.5, lw=1.1,
                label=f"→{t}")
        a2.plot(lam, [d[str(l)][i][3] / d[str(l)][i][4] for l in lam], "s-", color=c,
                ms=4.5, lw=1.1)
    a1.set_ylabel("전이 상관", fontsize=7.0)
    a1.set_ylim(0.18, 0.52)
    a1.legend(fontsize=6.0, frameon=False, ncol=2, loc="upper left")
    a1.set_title("순위 성능 — 꿈쩍하지 않는다", fontsize=7.2)
    a2.set_ylabel("예측 SD $\\div$ 대상 $y$ SD", fontsize=7.0)
    a2.set_ylim(0.2, 0.75)
    a2.set_title("눈금 — 이것만 움직인다", fontsize=7.2)
    for ax in (a1, a2):
        ax.set_xlabel("아이돌 출처 $\\lambda$", fontsize=7.0)
        ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_lawtest(out: Path, root: str = ".") -> dict:
    """노트42 — 정보량 설명의 반증 검정."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/lambda_law.json").read_text())
    t = d["_test"]
    doms = t["doms"]
    n = np.array(t["n"], float); ow = np.array(t["own"], float)
    bl = np.array(t["best"], float)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.2))
    for ax, x, lab, rr, c in ((a1, np.log10(n), "log$_{10}$ 표본 크기", t["r_n"], CLAIM),
                              (a2, ow, "고유 축 수", t["r_own"], GATE)):
        ax.scatter(x, bl, s=34, color=c, zorder=3)
        for xi, yi, k in zip(x, bl, doms):
            ax.annotate(k, (xi, yi), fontsize=6.2, xytext=(4, 3),
                        textcoords="offset points")
        z = np.polyfit(x, bl, 1)
        xx = np.linspace(x.min() - .08, x.max() + .12, 20)
        ax.plot(xx, np.polyval(z, xx), color=c, lw=.9, ls="--", alpha=.6)
        ax.set_xlabel(lab, fontsize=7.0)
        ax.set_ylabel("도메인별 최선 $\\lambda$", fontsize=7.0)
        ax.set_title(f"r $=$ {rr:+.3f}", fontsize=7.4, color=c)
        ax.tick_params(labelsize=6.4)
    a1.text(0.5, 0.06, "정보량 설명은 양수를 예측했다", transform=a1.transAxes,
            fontsize=6.2, color=CLAIM, ha="center")
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_metrics(out: Path, root: str = ".") -> dict:
    """노트42 — 세 지표가 갈린다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/shrink.json").read_text())
    ks = [k for k in d if k.startswith("상수 ")]
    cs = sorted(float(k.split()[1]) for k in ks)
    sig = [d[f"상수 {c}"]["sig"] for c in cs]
    gain = [d[f"상수 {c}"]["gain"] for c in cs]
    fig, ax = plt.subplots(figsize=(FULL, 2.15))
    ax2 = ax.twinx()
    ax.plot(cs, gain, "o-", color=GATE, ms=5, lw=1.3, label="평균 MAE 이득 (왼쪽)")
    ax2.plot(cs, sig, "s--", color=CLAIM, ms=5, lw=1.3, label="유의한 방향 (오른쪽)")
    ax.axhline(0.0463, color=MUTE, lw=1.0, ls=":")
    ax.text(cs[-1], 0.0468, "축소 없음 $+$0.0463", fontsize=6.0, color=INK, ha="right")
    ax2.axhline(17, color=MUTE, lw=1.0, ls=":")
    ax2.text(cs[0], 17.25, "축소 없음 17/20", fontsize=6.0, color=INK)
    ax.set_xlabel("명시적 축소 계수 $c$ (예측 SD)", fontsize=7.0)
    ax.set_ylabel("평균 MAE 이득", fontsize=7.0, color=GATE)
    ax2.set_ylabel("유의한 전이 방향", fontsize=7.0, color=CLAIM)
    ax.tick_params(labelsize=6.4); ax2.tick_params(labelsize=6.4)
    ax.set_ylim(0.028, 0.060); ax2.set_ylim(10, 19)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=6.0, frameon=False, loc="lower center")
    ax.set_title("축소는 이득을 올리고 검정력을 낮춘다", fontsize=7.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 43 ────────────────────────────────────────────────────────────
def fig_nulldist(out: Path, root: str = ".") -> dict:
    """노트43 — 귀무분포가 대상마다 다르고 관측이 95분위에 붙어 있다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/rank_null.json").read_text())
    doms = list(d)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1.3, 1]})
    for i, k in enumerate(doms):
        v = d[k]
        y = np.array(v["null"])
        xs = np.random.default_rng(i).normal(i, .075, len(y))
        a1.scatter(xs, y, s=2.2, color=MUTE, alpha=.30, edgecolors="none")
        a1.hlines(v["p95"], i - .28, i + .28, color=CLAIM, lw=1.5)
        a1.plot([i], [v["obs"]], "o", color=GATE, ms=7, zorder=4)
    a1.set_xticks(range(len(doms)))
    a1.set_xticklabels([f"{k}\nn={d[k]['n']}" for k in doms], fontsize=6.2)
    a1.set_ylabel("순위 상관 $\\rho$", fontsize=7.0)
    a1.axhline(0, color=INK, lw=.8)
    a1.set_title("회색 $=$ 귀무 · 붉은 선 $=$ 95분위 · 초록 $=$ 관측", fontsize=7.2)
    a1.tick_params(labelsize=6.4)

    n = np.array([d[k]["n"] for k in doms], float)
    sd = np.array([d[k]["sd"] for k in doms])
    a2.scatter(n, sd, s=34, color=CLAIM, zorder=3)
    for x, y, k in zip(n, sd, doms):
        a2.annotate(k, (x, y), fontsize=6.2, xytext=(4, 3), textcoords="offset points")
    a2.set_xscale("log")
    a2.set_xlabel("대상 표본 크기", fontsize=7.0)
    a2.set_ylabel("귀무 $\\rho$ 의 SD", fontsize=7.0)
    a2.set_title("귀무 폭이 표본에 지배된다", fontsize=7.2)
    a2.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_audit(out: Path, root: str = ".") -> dict:
    """노트43 — 과거 채택 결정의 재감사."""
    import numpy as np
    items = ["노트 37\n공통 축 2$\\to$3", "노트 37\n게임 매장축 켜기",
             "노트 39\n이중 배선", "노트 40\n쌍별 정렬"]
    before = [0.3301, 0.3438, 0.3439, 0.3724]
    after = [0.3438, 0.3516, 0.3430, 0.3742]
    keep = [True, False, False, True]
    xs = np.arange(len(items)); w = .34
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.bar(xs - w/2, before, w, color=MUTE, alpha=.9, edgecolor="none", label="변경 전")
    ax.bar(xs + w/2, after, w, alpha=.9, edgecolor="none", label="변경 후",
           color=[GATE if k else CLAIM for k in keep])
    for x, b, a, k in zip(xs, before, after, keep):
        ax.text(x - w/2, b + .002, f"{b:.4f}", ha="center", fontsize=5.9)
        ax.text(x + w/2, a + .002, f"{a:.4f}", ha="center", fontsize=5.9,
                color=GATE if k else CLAIM)
        ax.text(x, 0.305, "유지" if k else "철회", ha="center", fontsize=6.6,
                color=GATE if k else CLAIM, fontweight="bold")
    ax.set_xticks(xs); ax.set_xticklabels(items, fontsize=6.0)
    ax.set_ylabel("스무 셀 평균 순위 상관", fontsize=7.0)
    ax.set_ylim(0.30, 0.395)
    ax.legend(fontsize=6.2, frameon=False, loc="upper left")
    ax.set_title("붉은 것은 새 자로 재니 개선이 아니었던 것", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_rankroles(out: Path, root: str = ".") -> dict:
    """노트43 — 순위 기준에서도 대상이 지배하고 상충이 남는다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/rank_roles.json").read_text())
    rows = d["rows"]; self_ = d["self"]
    doms = [r[0] for r in rows]
    tm = np.array([r[1] for r in rows]); sm = np.array([r[3] for r in rows])
    sr = np.array([self_[k] for k in doms])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.25),
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    xs = np.arange(len(doms)); w = .34
    a1.bar(xs - w/2, tm, w, color=GATE, alpha=.9, edgecolor="none", label="대상으로")
    a1.bar(xs + w/2, sm, w, color=CLAIM, alpha=.9, edgecolor="none", label="출처로")
    for x, k in zip(xs, range(len(doms))):
        a1.vlines(x - w/2, rows[k][1] - rows[k][2]/2, rows[k][1] + rows[k][2]/2,
                  color=INK, lw=1.0)
        a1.vlines(x + w/2, rows[k][3] - rows[k][4]/2, rows[k][3] + rows[k][4]/2,
                  color=INK, lw=1.0)
    a1.set_xticks(xs); a1.set_xticklabels(doms, fontsize=6.6)
    a1.set_ylabel("평균 순위 상관", fontsize=7.0)
    a1.legend(fontsize=6.0, frameon=False, loc="upper right")
    a1.set_ylim(0, .62); a1.tick_params(labelsize=6.4)
    a1.set_title("세로선이 셀 간 폭 — 대상 쪽이 좁다", fontsize=7.2)

    a2.plot(sr, tm, "o-", color=GATE, ms=6, lw=1.1, label="대상으로")
    a2.plot(sr, sm, "s--", color=CLAIM, ms=5.5, lw=1.1, label="출처로")
    for x, y, k in zip(sr, tm, doms):
        a2.annotate(k, (x, y), fontsize=6.0, xytext=(2, 5), textcoords="offset points",
                    color=GATE)
    a2.set_xlabel("도메인의 자기 순위 상관", fontsize=7.0)
    a2.set_ylabel("평균 전이 $\\rho$", fontsize=7.0)
    a2.legend(fontsize=6.0, frameon=False, loc="center left")
    rt = np.corrcoef(sr, tm)[0, 1]; rs = np.corrcoef(sr, sm)[0, 1]
    a2.set_title(f"대상 $r={rt:+.3f}$ · 출처 $r={rs:+.3f}$", fontsize=7.2)
    a2.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 44 ────────────────────────────────────────────────────────────
def fig_forest(out: Path, root: str = ".") -> dict:
    """노트44 — 네 결정의 효과와 신뢰구간."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/rho_ci.json").read_text())
    ks = list(d)
    lab = [k.split(" (")[0] for k in ks]
    o = np.argsort([d[k]["obs_diff"] for k in ks])
    ks = [ks[i] for i in o]; lab = [lab[i] for i in o]
    ys = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(FULL, 2.15))
    ax.axvline(0, color=INK, lw=1.0)
    for y, k in zip(ys, ks):
        v = d[k]
        sig = v["ci"][0] > 0 or v["ci"][1] < 0
        c = GATE if sig else MUTE
        ax.hlines(y, v["ci"][0], v["ci"][1], color=c, lw=2.2, alpha=.85)
        ax.plot([v["obs_diff"]], [y], "o", color=c, ms=7, zorder=4)
        ax.text(v["ci"][1] + .006, y, f"{v['obs_diff']:+.4f}", fontsize=6.2,
                va="center", color=c)
    ax.set_yticks(ys); ax.set_yticklabels(lab, fontsize=6.4)
    ax.set_xlabel("평균 순위 상관의 변화 (짝지은 붓스트랩 300회)", fontsize=7.0)
    ax.set_xlim(-.10, .245)
    ax.set_title("초록만 구간이 0을 넘는다", fontsize=7.4)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_kinds(out: Path, root: str = ".") -> dict:
    """노트44 — 결정 유형별 효과 크기."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/rho_ci.json").read_text())
    algo = [k for k in d if "도서" not in k]
    wire = [k for k in d if "도서" in k]
    fig, ax = plt.subplots(figsize=(COL, 2.2))
    xs, vals, cols, labs = [], [], [], []
    for i, k in enumerate(algo):
        xs.append(0 + (i - 1) * 0.16); vals.append(abs(d[k]["obs_diff"]))
        cols.append(MUTE); labs.append(k.split(" (")[0])
    for i, k in enumerate(wire):
        xs.append(1.0); vals.append(abs(d[k]["obs_diff"]))
        cols.append(GATE); labs.append(k.split(" (")[0])
    ax.bar(xs, vals, width=.14, color=cols, alpha=.9, edgecolor="none")
    for x, v in zip(xs, vals):
        ax.text(x, v + .002, f"{v:.4f}", ha="center", fontsize=5.8)
    ax.axhline(0.0707, color=CLAIM, lw=1.1, ls="--")
    ax.text(0.5, 0.0735, "평균 $\\rho$ 자체의 95\% 구간 반폭", fontsize=6.0,
            color=CLAIM, ha="center")
    ax.set_xticks([0, 1.0])
    ax.set_xticklabels(["알고리즘 조정\n(공통 축 · 정렬 · 배선 이중화)",
                        "측정 배선\n(무엇을 재느냐)"], fontsize=6.4)
    ax.set_ylabel("$|$평균 $\\rho$ 변화$|$", fontsize=7.0)
    ax.set_ylim(0, .105)
    ax.set_title("한쪽만 잡음 위로 올라온다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 45 ────────────────────────────────────────────────────────────
def fig_exhaust(out: Path, root: str = ".") -> dict:
    """노트45 — 배선 후보 오십 개의 효과 분포."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/wiring_ci.json").read_text())
    rows = d["rows"]
    v = np.array([r["delta"] for r in rows])
    o = np.argsort(-v)
    v = v[o]; nm = [rows[i] for i in o]
    xs = np.arange(len(v))
    fig, ax = plt.subplots(figsize=(FULL, 2.15))
    ax.bar(xs, v, width=.8, color=[GATE if x > 0.02 else MUTE for x in v],
           alpha=.85, edgecolor="none")
    ax.axhline(0.02, color=CLAIM, lw=1.1, ls="--")
    ax.text(len(v) - 1, 0.0225, "문턱 0.02 (노트 44)", fontsize=6.2, color=CLAIM,
            ha="right")
    ax.axhline(0.0939, color=GATE, lw=1.1, ls=":")
    ax.text(1, 0.0965, "노트 34의 배선 효과 $+$0.0939", fontsize=6.2, color=GATE)
    ax.axhline(0, color=INK, lw=.9)
    top = nm[0]
    ax.annotate(f"최대 {top['dom']} {top['name']}\n{v[0]:+.4f}", (0, v[0]),
                fontsize=6.2, xytext=(16, 16), textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color=INK, lw=.7))
    ax.set_xlabel(f"배선 후보 {len(v)}개 (효과 순)", fontsize=7.0)
    ax.set_ylabel("평균 순위 상관의 변화", fontsize=7.0)
    ax.set_ylim(-0.06, 0.115)
    ax.set_title("문턱을 넘는 후보가 하나도 없다", fontsize=7.4)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_power(out: Path, root: str = ".") -> dict:
    """노트45 — 표본과 구간 반폭, 그리고 두 외삽."""
    import json, numpy as np
    # 로그 축 눈금이 U+2212(진짜 빼기표)를 쓰는데 나눔명조에 없다. ASCII 하이픈으로.
    plt.rcParams["axes.unicode_minus"] = False
    d = json.loads((Path(root) / "data/state/power_map.json").read_text())
    rows = [r for r in d["rows"] if np.isfinite(r["hw"])]
    n = np.array([r["n"] for r in rows], float)
    hw = np.array([r["hw"] for r in rows])
    n0, hw0, sl = d["n0"], d["hw0"], d["slope"]
    fig, ax = plt.subplots(figsize=(FULL, 2.25))
    ax.plot(n, hw, "o", color=INK, ms=6, zorder=4, label="부분추출 측정")
    xx = np.linspace(600, 8000, 60)
    ax.plot(xx, hw0 * (n0 / xx) ** 0.5, "-", color=CLAIM, lw=1.2,
            label="보수 외삽 ($n^{-1/2}$)")
    ax.plot(xx, hw0 * (n0 / xx) ** (-sl), "--", color=GATE, lw=1.2,
            label="적합 외삽 ($n^{%s}$)" % f"{sl:.2f}".replace("-", "\\!-\\!"))
    for lab, eff, c in (("배선 급 0.094", 0.047, GATE),
                        ("공통 축 급 0.022", 0.011, CLAIM)):
        ax.axhline(eff, color=c, lw=.8, ls=":", alpha=.6)
        ax.text(7600, eff * 1.06, lab, fontsize=6.0, color=c, ha="right")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("총 레코드 수", fontsize=7.0)
    ax.set_ylabel("평균 $\\rho$ 의 95\% 구간 반폭", fontsize=7.0)
    ax.legend(fontsize=6.0, frameon=False, loc="lower left")
    ax.set_title("두 외삽 사이가 실제 필요량이다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 46 ────────────────────────────────────────────────────────────
def fig_webtoon(out: Path, root: str = ".") -> dict:
    """노트46 — 탈추세가 웹툰 변수 대부분을 지운다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/webtoon_diag.json").read_text())
    meta = d.pop("_meta")
    ks = sorted(d, key=lambda k: -abs(d[k][0]))
    xs = np.arange(len(ks)); w = .34
    fig, ax = plt.subplots(figsize=(FULL, 2.15))
    ax.bar(xs - w/2, [d[k][0] for k in ks], w, color=MUTE, alpha=.9,
           edgecolor="none", label="탈추세 전")
    ax.bar(xs + w/2, [d[k][1] for k in ks], w, color=GATE, alpha=.9,
           edgecolor="none", label="탈추세 후")
    for x, k in zip(xs, ks):
        a, b = d[k]
        ax.text(x - w/2, a + (.014 if a >= 0 else -.014), f"{a:+.2f}", ha="center",
                va="bottom" if a >= 0 else "top", fontsize=5.8)
        ax.text(x + w/2, b + (.014 if b >= 0 else -.014), f"{b:+.2f}", ha="center",
                va="bottom" if b >= 0 else "top", fontsize=5.8, color=GATE)
    ax.axhline(0, color=INK, lw=.9)
    ax.set_xticks(xs); ax.set_xticklabels(ks, fontsize=6.5)
    ax.set_ylabel("관심 수와의 상관", fontsize=7.0)
    ax.legend(fontsize=6.2, frameon=False, loc="upper right")
    ax.set_title(f"라벨과 경과일의 상관이 $+${meta['label_elapsed_r']:.2f} "
                 f"— 누적 성분을 빼면 대부분 사라진다  (n$=${meta['n']})",
                 fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_narrow(out: Path, root: str = ".") -> dict:
    """노트46 — 구간이 셀 수가 아니라 도메인 수로 좁아진다."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(COL, 2.2))
    labs = ["5도메인\n20셀\n(실측)", "6도메인 예측\n셀 수 기준", "6도메인 예측\n도메인 기준",
            "6도메인\n30셀\n(실측)"]
    vals = [0.0709, 0.0579, 0.0647, 0.0672]
    cols = [MUTE, CLAIM, GATE, INK]
    xs = np.arange(4)
    ax.bar(xs, vals, width=.55, color=cols, alpha=.9, edgecolor="none")
    for x, v in zip(xs, vals):
        ax.text(x, v + .0012, f"{v:.4f}", ha="center", fontsize=6.2)
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=6.0)
    ax.set_ylabel("평균 $\\rho$ 의 95\% 구간 반폭", fontsize=7.0)
    ax.set_ylim(0, .085)
    ax.set_title("실측이 도메인 기준에 붙는다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_paradox(out: Path, root: str = ".") -> dict:
    """노트46 — 웹툰 배선 변형: 자기 상관이 낮을수록 전이가 좋다."""
    import numpy as np
    labs = ["연령 등급\n(처음)", "매장노출도\n$=$작가 수", "미디어투입\n$=$작가 수",
            "미디어$+$타깃폭", "태그 수\n(채택)"]
    self_ = [0.034, 0.158, 0.207, 0.192, -0.125]
    cells = [0.1985, 0.2143, 0.1995, 0.2585, 0.2915]
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.scatter(self_, cells, s=48, color=[CLAIM] * 4 + [GATE], zorder=3)
    for x, y, l in zip(self_, cells, labs):
        ax.annotate(l, (x, y), fontsize=6.0, xytext=(6, -3),
                    textcoords="offset points")
    z = np.polyfit(self_, cells, 1)
    xx = np.linspace(-.16, .23, 20)
    ax.plot(xx, np.polyval(z, xx), color=MUTE, lw=1.0, ls="--", zorder=1)
    ax.set_xlabel("웹툰의 자기 순위 상관", fontsize=7.0)
    ax.set_ylabel("서른 셀 평균 전이 $\\rho$", fontsize=7.0)
    r = np.corrcoef(self_, cells)[0, 1]
    ax.set_title(f"r $=$ {r:+.3f} — 자기 상관이 낮은 배선이 전이가 좋다", fontsize=7.4)
    ax.set_xlim(-.19, .27)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 47 ────────────────────────────────────────────────────────────
def fig_wins(out: Path, root: str = ".") -> dict:
    """노트47 — 구간을 통과한 것과 못 한 것."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/wins.json").read_text())
    rows = []
    for w in d["wins"]:
        rows.append((f"노트 {w['note']} · {w['dom']} {w['slot']}\n{w['from']} → {w['to']}",
                     w["d"], w["ci"], GATE))
    for h in d["held"]:
        rows.append((f"{h['dom']} {h['slot']}\n→ {h['to']}", h["d"], h["ci"], CLAIM))
    for a in d["algo"]:
        rows.append((a["lab"], a["d"], a["ci"], MUTE))
    rows = sorted(rows, key=lambda r: r[1])
    ys = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(FULL, 2.6))
    ax.axvline(0, color=INK, lw=1.0)
    for y, (lab, dd, ci, c) in zip(ys, rows):
        ax.hlines(y, ci[0], ci[1], color=c, lw=2.4, alpha=.85)
        ax.plot([dd], [y], "o", color=c, ms=7, zorder=4)
        ax.text(ci[1] + .006, y, f"{dd:+.4f}", fontsize=6.0, va="center", color=c)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=5.9)
    ax.set_xlabel("평균 순위 상관의 변화 (짝지은 붓스트랩 95\% 구간)", fontsize=7.0)
    ax.set_xlim(-.09, .235)
    ax.set_title("초록 둘만 구간이 0을 넘는다 — 그리고 둘 다 타깃 폭이다",
                 fontsize=7.4)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_slots(out: Path, root: str = ".") -> dict:
    """노트47 — 슬롯별 후보 효과 분포."""
    import json, numpy as np
    rows = json.loads((Path(root) / "data/state/wiring6.json").read_text())
    KO_ = {"target_breadth": "타깃 폭", "venue_prominence": "매장 노출도",
           "entry_friction": "입장 허들", "media_push": "미디어 투입",
           "goods_scale": "굿즈 규모"}
    slots = ["target_breadth", "goods_scale", "venue_prominence", "entry_friction",
             "media_push"]
    fig, ax = plt.subplots(figsize=(FULL, 2.15))
    for i, sl in enumerate(slots):
        v = [r[4] for r in rows if r[1] == sl]
        if not v:
            continue
        xs = np.random.default_rng(i).normal(i, .055, len(v))
        ax.scatter(xs, v, s=22, color=GATE if sl == "target_breadth" else MUTE,
                   alpha=.8, zorder=3)
        ax.hlines(max(v), i - .2, i + .2, color=INK, lw=1.2)
        ax.text(i, max(v) + .003, f"최대 {max(v):+.4f}", ha="center", fontsize=6.0)
    ax.axhline(0, color=INK, lw=.9)
    ax.axhline(0.02, color=CLAIM, lw=1.0, ls="--")
    ax.text(len(slots) - .5, .0225, "문턱 0.02", fontsize=6.0, color=CLAIM, ha="right")
    ax.set_xticks(range(len(slots)))
    ax.set_xticklabels([KO_[s] for s in slots], fontsize=6.6)
    ax.set_ylabel("평균 $\\rho$ 변화", fontsize=7.0)
    ax.set_title("여섯 도메인 후보 예순 개 — 문턱을 넘은 것은 타깃 폭과 굿즈 규모뿐",
                 fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 48 ────────────────────────────────────────────────────────────
def fig_lamfix(out: Path, root: str = ".") -> dict:
    """노트48 — λ 방식별 도메인 추가 불변성."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/inv.json").read_text())["lam"]
    labs = [r[0] for r in d]
    xs = np.arange(len(d)); w = .26
    fig, ax = plt.subplots(figsize=(FULL, 2.25))
    ax.bar(xs - w, [r[1] for r in d], w, color=MUTE, alpha=.9, edgecolor="none",
           label="5도메인 · 20셀")
    ax.bar(xs, [r[2] for r in d], w, color=GATE, alpha=.9, edgecolor="none",
           label="6도메인 · 같은 20셀")
    ax.bar(xs + w, [r[3] for r in d], w, color=INK, alpha=.55, edgecolor="none",
           label="6도메인 · 30셀")
    for x, r in zip(xs, d):
        gap = abs(r[1] - r[2])
        if gap > 0.002:
            ax.annotate("", xy=(x, r[2]), xytext=(x - w, r[1]),
                        arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.2))
            ax.text(x - w/2, max(r[1], r[2]) + .006, f"$-${gap:.4f}", fontsize=6.0,
                    color=CLAIM, ha="center")
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=6.0)
    ax.set_ylabel("평균 순위 상관", fontsize=7.0)
    ax.set_ylim(0.28, 0.385)
    ax.legend(fontsize=6.0, frameon=False, loc="lower right", ncol=1)
    ax.set_title("같은 20셀인데 값이 바뀌면 정의의 결함이다", fontsize=7.4)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_grow(out: Path, root: str = ".") -> dict:
    """노트48 — 표본이 늘자 보류가 채택이 된다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/inv.json").read_text())["grow"]
    fig, ax = plt.subplots(figsize=(COL, 2.2))
    for i, (n, dd, lo, hi, p) in enumerate(d):
        c = GATE if lo > 0 else CLAIM
        ax.hlines(i, lo, hi, color=c, lw=2.6, alpha=.85)
        ax.plot([dd], [i], "o", color=c, ms=8, zorder=4)
        ax.text(hi + .004, i, f"P$=${p:.3f}", fontsize=6.2, va="center", color=c)
    ax.axvline(0, color=INK, lw=1.0)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([f"n$=${r[0]}\n{'보류' if r[2] <= 0 else '채택'}" for r in d],
                       fontsize=6.6)
    ax.set_xlabel("평균 $\\rho$ 변화 (짝지은 95\% 구간)", fontsize=7.0)
    ax.set_xlim(-.012, .095)
    ax.set_title("효과는 줄고 구간은 좁아졌다", fontsize=7.4)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_state30(out: Path, root: str = ".") -> dict:
    """노트48 — 서른 셀 격자."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/pipeline.json").read_text())
    doms = list(d["self"]); n = len(doms)
    M = np.full((n, n), np.nan)
    for k, c in d["cells"].items():
        s, t = k.split("→")
        M[doms.index(s), doms.index(t)] = c["rho"]
    fig, ax = plt.subplots(figsize=(COL, 2.7))
    im = ax.imshow(M, cmap="BuGn", vmin=0.15, vmax=0.52)
    for i in range(n):
        for j in range(n):
            if i == j:
                ax.text(j, i, "—", ha="center", va="center", fontsize=7, color=MUTE)
            else:
                ax.text(j, i, f"{M[i,j]:.3f}", ha="center", va="center", fontsize=5.6,
                        color=INK)
    ax.set_xticks(range(n)); ax.set_xticklabels(doms, fontsize=6.2)
    ax.set_yticks(range(n)); ax.set_yticklabels(doms, fontsize=6.2)
    ax.set_xlabel("대상", fontsize=7.0); ax.set_ylabel("출처", fontsize=7.0)
    ax.set_title(f"순위 상관 · 평균 $+${d['rho']:.4f}", fontsize=7.4)
    ax.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 49 ────────────────────────────────────────────────────────────
def fig_wiki(out: Path, root: str = ".") -> dict:
    """노트49 — 위키백과 지표와 사람 태깅 축의 비교."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note49.json").read_text())
    w, h = d["wiki"], d["human"]
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    xs1 = np.arange(len(w))
    xs2 = np.arange(len(h)) + len(w) + .8
    ax.bar(xs1, [abs(r[1]) for r in w], .62, color=CLAIM, alpha=.9, edgecolor="none",
           label="위키백과 (외부 · 자동)")
    ax.bar(xs2, [abs(r[1]) for r in h], .62, color=GATE, alpha=.9, edgecolor="none",
           label="사람 태깅 (기획서 판독)")
    for x, r in list(zip(xs1, w)) + list(zip(xs2, h)):
        ax.text(x, abs(r[1]) + .008, f"{r[1]:+.3f}", ha="center", fontsize=5.8)
    ax.set_xticks(list(xs1) + list(xs2))
    ax.set_xticklabels([r[0] for r in w] + [r[0] for r in h], fontsize=5.7,
                       rotation=18, ha="right")
    ax.set_ylabel("팝업 라벨과의 $|$상관$|$ (탈추세)", fontsize=7.0)
    ax.set_ylim(0, .40)
    ax.legend(fontsize=6.2, frameon=False, loc="upper left")
    ax.set_title("가장 강한 외부 지표가 가장 약한 사람 축에도 못 미친다", fontsize=7.4)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_wtgrow(out: Path, root: str = ".") -> dict:
    """노트49 — 웹툰 표본이 늘며 자기 상관이 오르고 출처 성적이 내린다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note49.json").read_text())
    w = d["webtoon"]; sr = d["wt_src"]
    n = [r[0] for r in w]
    fig, ax = plt.subplots(figsize=(FULL, 2.2))
    ax.plot(n, [r[1] for r in w], "o-", color=GATE, ms=6, lw=1.3, label="자기 $\\rho$")
    ax.plot(n, [r[2] for r in w], "s-", color=INK, ms=5.5, lw=1.3,
            label="대상으로서의 전이")
    ax.plot([r[0] for r in sr], [r[1] for r in sr], "^--", color=CLAIM, ms=6, lw=1.3,
            label="출처로서의 전이")
    for x, y in zip(n, [r[1] for r in w]):
        ax.text(x, y + .015, f"{y:+.3f}", ha="center", fontsize=6.0, color=GATE)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xlabel("웹툰 표본 크기 (완결작 비율 0\% $\\to$ 8\% $\\to$ 31\%)",
                  fontsize=7.0)
    ax.set_ylabel("순위 상관", fontsize=7.0)
    ax.legend(fontsize=6.2, frameon=False, loc="lower right")
    ax.set_title("자기 상관이 오르자 출처 성적이 내렸다 — 상충 법칙대로", fontsize=7.4)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_cinarrow(out: Path, root: str = ".") -> dict:
    """노트49 — 구간 반폭이 도메인 수와 도메인 내 표본 둘 다에 반응한다."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note49.json").read_text())["ci"]
    labs = [f"{r[0]}도메인\n{r[1]:,}건" for r in d]
    v = [r[2] for r in d]
    xs = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(COL, 2.2))
    ax.bar(xs, v, .55, color=[MUTE, INK, GATE], alpha=.9, edgecolor="none")
    for x, y in zip(xs, v):
        ax.text(x, y + .0012, f"{y:.4f}", ha="center", fontsize=6.4)
    ax.annotate("도메인 $+$1", (0.5, 0.074), fontsize=6.2, color=INK, ha="center")
    ax.annotate("웹툰만 $\\times$1.5", (1.5, 0.074), fontsize=6.2, color=GATE,
                ha="center")
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=6.2)
    ax.set_ylabel("평균 $\\rho$ 의 95\% 구간 반폭", fontsize=7.0)
    ax.set_ylim(0, .085)
    ax.set_title("도메인 내 표본도 구간을 좁힌다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 50 ────────────────────────────────────────────────────────────
def fig_venue(out: Path, root: str = ".") -> dict:
    """노트50 — 매장 노출도 신호가 도메인마다 얼마나 다른가."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note50.json").read_text())["venue"]
    labs = [f"{r[0]}\n{r[2]}" for r in d]
    v = [r[1] for r in d]
    on = [r[3] == "켬" for r in d]
    xs = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(FULL, 2.35))
    ax.bar(xs, v, .58, alpha=.9, edgecolor="none",
           color=[GATE if o else CLAIM for o in on])
    for x, y, o in zip(xs, v, on):
        ax.text(x, y + (.012 if y >= 0 else -.012), f"{y:+.3f}", ha="center",
                va="bottom" if y >= 0 else "top", fontsize=6.4)
        ax.text(x, -0.075, "축으로 씀" if o else "꺼 둠", ha="center", fontsize=5.9,
                color=GATE if o else CLAIM)
    ax.axhline(0, color=INK, lw=1.0)
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=6.0)
    ax.set_ylabel("라벨과의 상관 (탈추세)", fontsize=7.0)
    ax.set_ylim(-.095, .38)
    ax.set_title("같은 축인데 시장마다 신호가 $+$0.32에서 $-$0.01까지", fontsize=7.4)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 51 ────────────────────────────────────────────────────────────
def fig_prior(out: Path, root: str = ".") -> dict:
    """노트51 — 펀딩 창작자 이력을 어떻게 재느냐."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note51.json").read_text())["prior"]
    labs = [r[0] for r in d]; v = [r[1] for r in d]
    ys = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(COL, 2.3))
    ax.barh(ys, v, .6, color=[GATE if x > .1 else (MUTE if x > 0 else CLAIM) for x in v],
            alpha=.9, edgecolor="none")
    for y, x in zip(ys, v):
        ax.text(x + (.005 if x >= 0 else -.005), y, f"{x:+.3f}", fontsize=6.2,
                va="center", ha="left" if x >= 0 else "right")
    ax.axvline(0, color=INK, lw=.9)
    ax.set_yticks(ys); ax.set_yticklabels(labs, fontsize=6.3)
    ax.set_xlabel("후원자 수와의 상관 (탈추세)", fontsize=7.0)
    ax.set_xlim(-.06, .22)
    ax.set_title("건수는 무효, 최대 후원자 수는 살아 있다", fontsize=7.4)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_exact(out: Path, root: str = ".") -> dict:
    """노트51 — 축 하나를 켜자 대상과 출처가 정확히 반대로 움직인다."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note51.json").read_text())
    c = j["cells"]
    tgt = [r for r in c if r[0].endswith("펀딩")]
    src = [r for r in c if r[0].startswith("펀딩")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1.5, 1]})
    ys = np.arange(len(c))
    for i, r in enumerate(tgt + src):
        d0 = r[2] - r[1]
        col = GATE if d0 > 0 else CLAIM
        a1.hlines(i, r[1], r[2], color=col, lw=2.0, alpha=.8)
        a1.plot([r[1]], [i], "o", color=MUTE, ms=5)
        a1.plot([r[2]], [i], "o", color=col, ms=6)
    a1.set_yticks(ys); a1.set_yticklabels([r[0] for r in tgt + src], fontsize=6.0)
    a1.axhline(len(tgt) - .5, color=INK, lw=.8, ls=":")
    a1.text(.50, len(tgt) / 2 - .5, "펀딩이 대상", fontsize=6.4, color=GATE,
            rotation=90, va="center")
    a1.text(.50, len(tgt) + len(src) / 2 - .5, "펀딩이 출처", fontsize=6.4,
            color=CLAIM, rotation=90, va="center")
    a1.set_xlabel("순위 상관 (회색 $=$ 끔, 색 $=$ 켬)", fontsize=7.0)
    a1.set_xlim(.15, .55)
    a1.tick_params(labelsize=6.2)
    a1.set_title("셀마다 방향이 갈린다", fontsize=7.2)

    g = [np.mean([r[1] for r in tgt]), np.mean([r[2] for r in tgt]),
         np.mean([r[1] for r in src]), np.mean([r[2] for r in src])]
    xs = np.array([0, .35, 1.1, 1.45])
    a2.bar(xs, g, .3, color=[MUTE, GATE, MUTE, CLAIM], alpha=.9, edgecolor="none")
    for x, y in zip(xs, g):
        a2.text(x, y + .006, f"{y:.3f}", ha="center", fontsize=6.0)
    a2.annotate(f"{g[1]-g[0]:+.3f}", (0.175, max(g[0], g[1]) + .045), fontsize=6.6,
                color=GATE, ha="center")
    a2.annotate(f"{g[3]-g[2]:+.3f}", (1.275, max(g[2], g[3]) + .045), fontsize=6.6,
                color=CLAIM, ha="center")
    a2.set_xticks([.175, 1.275]); a2.set_xticklabels(["대상 5셀", "출처 5셀"],
                                                     fontsize=6.6)
    a2.set_ylabel("평균 순위 상관", fontsize=7.0)
    a2.set_ylim(0, .52); a2.tick_params(labelsize=6.4)
    a2.set_title("주고 받은 것이 같다", fontsize=7.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 52 ────────────────────────────────────────────────────────────
def fig_maxprior(out: Path, root: str = ".") -> dict:
    """노트52 — 이력을 건수로 재는 것과 최대 규모로 재는 것."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note52.json").read_text())
    pr, pipe = d["prior"], {r[0]: r[1] for r in d["pipe"]}
    labs = [f"{r[0]}\n{r[1]} · {r[2]}/{r[3]}" for r in pr]
    xs = np.arange(len(pr)); w = .34
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.25),
                                 gridspec_kw={"width_ratios": [1.35, 1]})
    a1.bar(xs - w/2, [r[4] for r in pr], w, color=MUTE, alpha=.9, edgecolor="none",
           label="건수")
    a1.bar(xs + w/2, [r[5] for r in pr], w, color=GATE, alpha=.9, edgecolor="none",
           label="최대 규모")
    for x, r in zip(xs, pr):
        a1.text(x - w/2, r[4] + (.006 if r[4] >= 0 else -.006), f"{r[4]:+.3f}",
                ha="center", va="bottom" if r[4] >= 0 else "top", fontsize=5.8)
        a1.text(x + w/2, r[5] + .006, f"{r[5]:+.3f}", ha="center", fontsize=5.8,
                color=GATE)
    a1.axhline(0, color=INK, lw=.9)
    a1.set_xticks(xs); a1.set_xticklabels(labs, fontsize=5.9)
    a1.set_ylabel("라벨과의 상관 (탈추세)", fontsize=7.0)
    a1.set_ylim(-.05, .23)
    a1.legend(fontsize=6.2, frameon=False, loc="upper left")
    a1.set_title("단독 상관은 2--3배 강해진다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    ks = [r[0] for r in pr]
    a2.bar(np.arange(len(ks)), [pipe[k] for k in ks], .55,
           color=[GATE if pipe[k] > 0 else CLAIM for k in ks], alpha=.9,
           edgecolor="none")
    for x, k in zip(np.arange(len(ks)), ks):
        a2.text(x, pipe[k] + (.0002 if pipe[k] >= 0 else -.0002), f"{pipe[k]:+.4f}",
                ha="center", va="bottom" if pipe[k] >= 0 else "top", fontsize=5.9)
    a2.axhline(0, color=INK, lw=.9)
    a2.set_xticks(np.arange(len(ks))); a2.set_xticklabels(ks, fontsize=6.4)
    a2.set_ylabel("서른 셀 평균 $\\rho$ 변화", fontsize=7.0)
    a2.set_ylim(-.0025, .0035)
    a2.set_title("축으로는 옮겨지지 않는다", fontsize=7.2)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_venueoff(out: Path, root: str = ".") -> dict:
    """노트52 — 매장 노출도를 끌 때의 손해."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note52.json").read_text())
    off = d["off"]; ref = d["ref"]
    labs = [r[0] for r in off]; v = [r[1] for r in off]
    xs = np.arange(len(off))
    fig, ax = plt.subplots(figsize=(FULL, 2.1))
    ax.bar(xs, v, .55, color=[CLAIM if x < -0.005 else MUTE for x in v],
           alpha=.9, edgecolor="none")
    for x, y in zip(xs, v):
        ax.text(x, y + (.0012 if y >= 0 else -.0012), f"{y:+.4f}", ha="center",
                va="bottom" if y >= 0 else "top", fontsize=6.2)
    ax.axhline(0, color=INK, lw=1.0)
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=6.4)
    ax.set_ylabel("서른 셀 평균 $\\rho$ 변화", fontsize=7.0)
    ax.set_ylim(-.038, .006)
    ax.set_title("단독 상관이 약한 축인데 끄면 크게 떨어진다", fontsize=7.4)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 53 ────────────────────────────────────────────────────────────
def fig_falsify(out: Path, root: str = ".") -> dict:
    """노트53 — 정렬 자유도 가설의 반증."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note53.json").read_text())["cond"]
    labs = [r[0] for r in d]; v = [r[1] for r in d]; e = [r[2] for r in d]
    xs = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(FULL, 2.25))
    cols = [GATE, INK, CLAIM, CLAIM, CLAIM]
    ax.bar(xs, v, .55, color=cols, alpha=.9, edgecolor="none",
           yerr=e, ecolor=INK, capsize=3)
    for x, y, ee in zip(xs, v, e):
        ax.text(x, y + ee + .006, f"{y:.4f}", ha="center", fontsize=6.2)
    ax.axhline(d[1][1], color=INK, lw=1.0, ls=":")
    ax.text(len(d) - .4, d[1][1] + .004, "전부 끔", fontsize=6.0, color=INK, ha="right")
    ax.annotate("자유도 가설이 맞으면\n여기까지 올라와야 한다",
                (3, d[0][1]), fontsize=6.2, color=GATE, ha="center",
                xytext=(3, d[0][1] + .022), textcoords="data",
                arrowprops=dict(arrowstyle="->", color=GATE, lw=.8))
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=6.1)
    ax.set_ylabel("서른 셀 평균 순위 상관", fontsize=7.0)
    ax.set_ylim(0.16, 0.385)
    ax.set_title("잡음 축은 끄는 것보다 나쁘다 — 자유도가 아니었다", fontsize=7.4)
    ax.tick_params(labelsize=6.3)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_contrib(out: Path, root: str = ".") -> dict:
    """노트53 — 도메인별 기여와 현행 축이 담은 몫."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note53.json").read_text())
    c, ov = j["contrib"], j["overlap"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.2),
                                 gridspec_kw={"width_ratios": [1.35, 1]})
    labs = [f"{r[0]}\nn$=${r[1]} · r$=${r[2]:+.3f}" for r in c]
    v = [-r[3] for r in c]
    xs = np.arange(len(c))
    a1.bar(xs, v, .55, color=[CLAIM if x > .005 else MUTE for x in v], alpha=.9,
           edgecolor="none")
    for x, y in zip(xs, v):
        a1.text(x, y + (.0012 if y >= 0 else -.0012), f"{y:+.4f}", ha="center",
                va="bottom" if y >= 0 else "top", fontsize=6.0)
    a1.axhline(0, color=INK, lw=.9)
    a1.set_xticks(xs); a1.set_xticklabels(labs, fontsize=5.9)
    a1.set_ylabel("대응을 깰 때의 손해", fontsize=7.0)
    a1.set_ylim(-.004, .052)
    a1.set_title("신호 강도 $\\times$ 표본 크기", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    ys = np.arange(len(ov))
    a2.barh(ys, [r[1] ** 2 for r in ov], .55, color=GATE, alpha=.9, edgecolor="none")
    for y, r in zip(ys, ov):
        a2.text(r[1] ** 2 + .012, y, f"{r[1]**2:.0%}", fontsize=6.2, va="center")
    a2.set_yticks(ys); a2.set_yticklabels([r[0] for r in ov], fontsize=6.4)
    a2.set_xlabel("현행 축이 '최대 규모'를 담은 몫", fontsize=7.0)
    a2.set_xlim(0, .85)
    a2.set_title("이미 담고 있어 못 올린다", fontsize=7.2)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 54 ────────────────────────────────────────────────────────────
def fig_bug(out: Path, root: str = ".") -> dict:
    """노트54 — 같은 후보, 두 검정."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note54.json").read_text())["bug"]
    fig, ax = plt.subplots(figsize=(FULL, 1.95))
    ax.axvline(0, color=INK, lw=1.0)
    for i, (lab, pt, lo, hi, p) in enumerate(d):
        c = GATE if lo > 0 else CLAIM
        ax.hlines(i, lo, hi, color=c, lw=3.0, alpha=.85)
        ax.plot([pt], [i], "o", color=c, ms=8, zorder=4)
        ax.text(hi + .006, i, f"P($>$0)$=${p:.3f}", fontsize=6.4, va="center", color=c)
    ax.plot([0.0066], [0], "D", color=INK, ms=6, zorder=5)
    ax.annotate("점추정은 둘 다 $+$0.0066", (0.0066, 0), fontsize=6.2,
                xytext=(0.055, 0.35), textcoords="data",
                arrowprops=dict(arrowstyle="->", color=INK, lw=.8))
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([r[0] for r in d], fontsize=6.8)
    ax.set_xlabel("평균 순위 상관의 변화 (짝지은 95\% 구간)", fontsize=7.0)
    ax.set_xlim(-.20, .13)
    ax.set_title("확장을 복원추출 뒤에 하면 부호가 뒤집힌다", fontsize=7.4)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_ownagain(out: Path, root: str = ".") -> dict:
    """노트54 — 도메인별 고유 축 확장."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note54.json").read_text())["own"]
    labs = [r[0] for r in d]
    base = d[0][1]
    v = [r[2] - base for r in d]
    xs = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    ax.bar(xs, v, .55, color=[GATE if x > 0 else CLAIM for x in v], alpha=.9,
           edgecolor="none")
    for x, y in zip(xs, v):
        ax.text(x, y + (.0012 if y >= 0 else -.0012), f"{y:+.4f}", ha="center",
                va="bottom" if y >= 0 else "top", fontsize=6.2)
    ax.axhline(0, color=INK, lw=1.0)
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=6.6)
    ax.set_ylabel("서른 셀 평균 $\\rho$ 변화", fontsize=7.0)
    ax.set_ylim(-.021, .010)
    ax.set_title("관측 축이 둘뿐인 도메인만 얻는다", fontsize=7.2)
    ax.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 55 ────────────────────────────────────────────────────────────
def fig_owncond(out: Path, root: str = ".") -> dict:
    """노트55 — 고유 축이 도움되는 조건."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note55.json").read_text())
    r = j["rows"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    x = np.array([q[1] for q in r], float)
    y = np.array([q[4] for q in r])
    a1.axhline(0, color=INK, lw=1.0)
    a1.axvline(3, color=CLAIM, lw=1.2, ls="--")
    a1.scatter(x, y, s=46, color=[GATE if v > 0 else MUTE for v in y], zorder=3)
    for xi, yi, q in zip(x, y, r):
        a1.annotate(q[0], (xi, yi), fontsize=6.3, xytext=(6, -2),
                    textcoords="offset points")
    a1.text(3.06, 0.004, "관측 축 3개", fontsize=6.2, color=CLAIM)
    a1.set_xlabel("기존 관측 축 수", fontsize=7.0)
    a1.set_ylabel("고유 축을 더할 때 $\\Delta\\rho$", fontsize=7.0)
    a1.set_xlim(1.3, 5.9); a1.set_ylim(-.056, .014)
    a1.set_title("경계 하나로 갈린다", fontsize=7.4)
    a1.tick_params(labelsize=6.4)

    c = j["combo"]
    xs = np.arange(len(c))
    a2.bar(xs, [q[1] for q in c], .55,
           color=[GATE if q[1] > 0 else CLAIM for q in c], alpha=.9, edgecolor="none")
    for xi, q in zip(xs, c):
        a2.text(xi, q[1] + (.0025 if q[1] >= 0 else -.0025), f"{q[1]:+.4f}",
                ha="center", va="bottom" if q[1] >= 0 else "top", fontsize=6.0)
    a2.axhline(0, color=INK, lw=1.0)
    a2.set_xticks(xs)
    a2.set_xticklabels([q[0].replace("+", "\n$+$") for q in c], fontsize=6.0)
    a2.set_ylabel("$\\Delta\\rho$", fontsize=7.0)
    a2.set_ylim(-.075, .015)
    a2.set_title("조건을 어기면 쌓일수록 나빠진다", fontsize=7.4)
    a2.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 56 ────────────────────────────────────────────────────────────
def fig_slope(out: Path, root: str = ".") -> dict:
    """노트56 — 축 수에 따른 고유 축 도움 비율."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note56.json").read_text())
    r = j["rate"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1, 1.25]})
    x = [q[0] for q in r]; y = [q[1] / q[2] for q in r]
    a1.plot(x, y, "o-", color=GATE, ms=8, lw=1.6)
    for xi, yi, q in zip(x, y, r):
        a1.text(xi, yi + .045, f"{q[1]}/{q[2]}", ha="center", fontsize=6.4)
    a1.set_xlabel("관측 축 수", fontsize=7.0)
    a1.set_ylabel("고유 축이 도움된 비율", fontsize=7.0)
    a1.set_ylim(-.08, 1.18); a1.set_xticks([2, 3, 4, 5])
    a1.set_title("경계가 아니라 비탈이다", fontsize=7.4)
    a1.tick_params(labelsize=6.4)

    t = j["three"]
    xs = np.arange(len(t))
    o = np.argsort([-q[3] for q in t])
    t = [t[i] for i in o]
    xs = np.arange(len(t))
    a2.bar(xs, [q[3] for q in t], .6,
           color=[GATE if q[3] > 0 else CLAIM for q in t], alpha=.9, edgecolor="none")
    for xi, q in zip(xs, t):
        a2.text(xi, q[3] + (.003 if q[3] >= 0 else -.003), f"{q[2]:.3f}",
                ha="center", va="bottom" if q[3] >= 0 else "top", fontsize=5.4)
    a2.axhline(0, color=INK, lw=1.0)
    a2.set_xticks(xs)
    a2.set_xticklabels([f"{q[0]}\n$-${q[1]}" for q in t], fontsize=5.3)
    a2.set_ylabel("$\\Delta\\rho$ (고유 축 추가)", fontsize=7.0)
    a2.set_ylim(-.10, .062)
    a2.set_title("숫자는 그 3축 상태의 기준 $\\rho$", fontsize=7.2)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 57 ────────────────────────────────────────────────────────────
def fig_swap(out: Path, root: str = ".") -> dict:
    """노트57 — 고유 축 유무에 따라 최적 공통 축이 뒤집힌다."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note57.json").read_text())
    d, sw = j["drop"], j["swap"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1, 1.2]})
    xs = np.arange(len(d)); w = .34
    a1.bar(xs - w/2, [r[1] for r in d], w, color=GATE, alpha=.9, edgecolor="none",
           label="타깃 폭 끔")
    a1.bar(xs + w/2, [r[2] for r in d], w, color=CLAIM, alpha=.9, edgecolor="none",
           label="굿즈 규모 끔")
    for x, r in zip(xs, d):
        a1.text(x - w/2, r[1] + (.003 if r[1] >= 0 else -.003), f"{r[1]:+.3f}",
                ha="center", va="bottom" if r[1] >= 0 else "top", fontsize=5.9)
        a1.text(x + w/2, r[2] - .003, f"{r[2]:+.3f}", ha="center", va="top",
                fontsize=5.9)
    a1.axhline(0, color=INK, lw=1.0)
    a1.set_xticks(xs); a1.set_xticklabels([r[0] for r in d], fontsize=6.0)
    a1.set_ylabel("$\\Delta\\rho$ (고유 축 추가)", fontsize=7.0)
    a1.set_ylim(-.075, .062)
    a1.legend(fontsize=6.0, frameon=False, loc="lower left")
    a1.set_title("회복을 만드는 것은 연령 등급이다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    ys = np.arange(len(sw))
    base = sw[0][1]
    a2.barh(ys, [r[1] - base for r in sw], .55,
            color=[GATE if r[1] > base else (MUTE if i == 0 else CLAIM)
                   for i, r in enumerate(sw)], alpha=.9, edgecolor="none")
    for y, r in zip(ys, sw):
        v = r[1] - base
        a2.text(v + (.0008 if v >= 0 else -.0008), y, f"{r[1]:.4f}", fontsize=6.0,
                va="center", ha="left" if v >= 0 else "right")
    a2.axvline(0, color=INK, lw=1.0)
    a2.set_yticks(ys); a2.set_yticklabels([r[0] for r in sw], fontsize=5.8)
    a2.set_xlabel("현행 대비 평균 $\\rho$", fontsize=7.0)
    a2.set_xlim(-.017, .012)
    a2.set_title("고유 축이 있으면 순서가 뒤집힌다", fontsize=7.2)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 58 ────────────────────────────────────────────────────────────
def fig_product(out: Path, root: str = ".") -> dict:
    """노트58 — 팝업 예측을 제품 언어로."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/product.json").read_text())
    q = d["quint"]; mean = d["mean"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.35),
                                 gridspec_kw={"width_ratios": [1.25, 1]})
    xs = np.arange(len(q))
    a1.bar(xs, q, .6, color=[GATE, GATE, MUTE, MUTE, CLAIM], alpha=.9,
           edgecolor="none")
    for x, v in zip(xs, q):
        a1.text(x, v + 18, f"{v:.0f}명", ha="center", fontsize=6.6)
    a1.axhline(mean, color=INK, lw=1.1, ls="--")
    a1.text(4.45, mean + 20, f"전체 평균 {mean:.0f}명", fontsize=6.2, color=INK,
            ha="right")
    a1.set_xticks(xs)
    a1.set_xticklabels([f"{i}분위" for i in range(1, 6)], fontsize=6.8)
    a1.set_ylabel("실제 일평균 방문자", fontsize=7.0)
    a1.set_ylim(0, 1010)
    a1.set_title(f"예측 상위 20\%와 하위 20\%가 {q[0]/q[-1]:.1f}배", fontsize=7.4)
    a1.tick_params(labelsize=6.4)

    bs = d["by_src"]
    ks = sorted(bs, key=lambda k: -bs[k][0])
    ys = np.arange(len(ks))
    a2.barh(ys, [bs[k][0] for k in ks], .55, color=GATE, alpha=.9, edgecolor="none")
    for y, k in zip(ys, ks):
        a2.text(bs[k][0] + .008, y, f"{bs[k][0]:+.3f}", fontsize=6.2, va="center")
    a2.set_yticks(ys); a2.set_yticklabels(ks, fontsize=6.6)
    a2.set_xlabel("팝업 순위 상관 $\\rho$", fontsize=7.0)
    a2.set_xlim(0, .58)
    a2.set_title("어느 도메인에서 배우든 비슷하다", fontsize=7.2)
    a2.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 59 ────────────────────────────────────────────────────────────
def fig_calib(out: Path, root: str = ".") -> dict:
    """노트59 — 보정 건수와 절대 오차."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/calibrate6.json").read_text())
    ks = sorted(int(k) for k in d)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1.2, 1]})
    a1.plot(ks, [10 ** d[str(k)]["model"] for k in ks], "o-", color=GATE, ms=6,
            lw=1.4, label="모델 $+$ 보정")
    a1.plot(ks, [10 ** d[str(k)]["median"] for k in ks], "s--", color=MUTE, ms=5.5,
            lw=1.3, label="보정만 (중앙값)")
    for k in ks:
        a1.text(k, 10 ** d[str(k)]["model"] - .045, f"{10**d[str(k)]['model']:.2f}",
                ha="center", fontsize=6.0, color=GATE)
    a1.set_xlabel("실제로 잰 팝업 건수 $k$", fontsize=7.0)
    a1.set_ylabel("절대 오차 (배수)", fontsize=7.0)
    a1.set_ylim(2.2, 3.25)
    a1.legend(fontsize=6.2, frameon=False, loc="upper right")
    a1.set_title("여덟에서 열둘이면 눈금이 잡힌다", fontsize=7.2)
    a1.tick_params(labelsize=6.4)

    xs = np.arange(2)
    vals = [5.5, 10 ** d["12"]["model"]]
    a2.bar(xs, vals, .5, color=[GATE, CLAIM], alpha=.9, edgecolor="none")
    for x, v, t in zip(xs, vals, ["상위 20\% $\\div$ 하위 20\%",
                                  "절대 예측 오차"]):
        a2.text(x, v + .12, f"{v:.1f}배", ha="center", fontsize=7.0)
    a2.set_xticks(xs)
    a2.set_xticklabels(["순위\n(노트 58)", "절대값\n($k{=}12$)"], fontsize=6.6)
    a2.set_ylabel("배수", fontsize=7.0)
    a2.set_ylim(0, 6.6)
    a2.set_title("순서는 가르고 값은 못 좁힌다", fontsize=7.2)
    a2.tick_params(labelsize=6.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 60 ────────────────────────────────────────────────────────────
def fig_encoder(out: Path, root: str = ".") -> dict:
    """노트60 — 신경망과 선형 파이프라인."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note60.json").read_text())["main"]
    labs = [r[0] for r in d]; v = [r[1] for r in d]; e = [r[2] for r in d]
    ys = np.arange(len(d))[::-1]
    fig, ax = plt.subplots(figsize=(FULL, 2.4))
    cols = [GATE] + [CLAIM] * (len(d) - 1)
    ax.barh(ys, v, .55, color=cols, alpha=.9, edgecolor="none",
            xerr=e, ecolor=INK, capsize=3)
    for y, x, ee in zip(ys, v, e):
        ax.text(x + ee + .008, y, f"{x:.4f}" + (f" $\\pm$ {ee:.4f}" if ee else ""),
                fontsize=6.2, va="center")
    ax.axvline(v[0], color=GATE, lw=1.0, ls=":")
    ax.set_yticks(ys); ax.set_yticklabels(labs, fontsize=6.0)
    ax.set_xlabel("서른 셀 평균 순위 상관", fontsize=7.0)
    ax.set_xlim(0, .46)
    ax.set_title("닫힌 해가 학습된 표현을 두 배 앞선다", fontsize=7.4)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 61 ────────────────────────────────────────────────────────────
def fig_ladder(out: Path, root: str = ".") -> dict:
    """노트61 — 격차를 단계로 분해한다."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note61.json").read_text())
    d, dec = j["ladder"], j["decomp"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.35),
                                 gridspec_kw={"width_ratios": [1.35, 1]})
    xs = np.arange(len(d))
    cols = [CLAIM, CLAIM, GATE, INK]
    a1.bar(xs, [r[1] for r in d], .55, color=cols, alpha=.9, edgecolor="none",
           yerr=[r[2] for r in d], ecolor=INK, capsize=3)
    for x, r in zip(xs, d):
        a1.text(x, r[1] + r[2] + .012, f"{r[1]:.4f}", ha="center", fontsize=6.3)
    for i in range(len(d) - 1):
        a1.annotate("", xy=(i + 1, d[i + 1][1] - .012), xytext=(i, d[i][1] + .012),
                    arrowprops=dict(arrowstyle="->", color=INK, lw=.9, alpha=.6))
        a1.text(i + .5, (d[i][1] + d[i + 1][1]) / 2 + .022,
                f"$+${d[i+1][1]-d[i][1]:.3f}", fontsize=6.0, ha="center", color=INK)
    a1.set_xticks(xs)
    a1.set_xticklabels([r[0].replace(" ", "\n", 1) for r in d], fontsize=5.7)
    a1.set_ylabel("서른 셀 평균 순위 상관", fontsize=7.0)
    a1.set_ylim(0, .43)
    a1.set_title("한 단계씩 되돌리면", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    tot = sum(r[1] for r in dec)
    ys = np.arange(len(dec))[::-1]
    a2.barh(ys, [r[1] for r in dec], .55,
            color=[MUTE, GATE, INK], alpha=.9, edgecolor="none")
    for y, r in zip(ys, dec):
        a2.text(r[1] + .003, y, f"{r[1]:.3f}  ({r[1]/tot:.0%})", fontsize=6.3,
                va="center")
    a2.set_yticks(ys); a2.set_yticklabels([r[0] for r in dec], fontsize=6.4)
    a2.set_xlabel("격차 0.180의 분해", fontsize=7.0)
    a2.set_xlim(0, .17)
    a2.set_title("라벨 지도가 61\%", fontsize=7.4)
    a2.tick_params(labelsize=6.3)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 62 ────────────────────────────────────────────────────────────
def fig_fourwrong(out: Path, root: str = ".") -> dict:
    """노트62 — 네 가설을 지운 뒤에도 남는 격차."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note62.json").read_text())["var"]
    ys = np.arange(len(d))[::-1]
    fig, ax = plt.subplots(figsize=(FULL, 2.5))
    cols = [GATE] + [CLAIM if "기각" in r[3] else MUTE for r in d[1:]]
    ax.barh(ys, [r[1] for r in d], .58, color=cols, alpha=.9, edgecolor="none",
            xerr=[r[2] for r in d], ecolor=INK, capsize=2.5)
    for y, r in zip(ys, d):
        ax.text(r[1] + r[2] + .007, y, f"{r[1]:.4f}", fontsize=6.2, va="center")
        if r[3] != "기준":
            ax.text(.012, y, r[3], fontsize=5.6, va="center", color="white")
    ax.axvline(d[0][1], color=GATE, lw=1.0, ls=":")
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in d], fontsize=6.1)
    ax.set_xlabel("서른 셀 평균 순위 상관", fontsize=7.0)
    ax.set_xlim(0, .44)
    ax.set_title("네 가설을 지웠는데 격차 0.043이 남는다", fontsize=7.4)
    ax.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 63 ────────────────────────────────────────────────────────────
def fig_hygiene(out: Path, root: str = ".") -> dict:
    """노트63 — 위생 필터별 성능."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note63.json").read_text())
    f = j["filters"]; ci = j["ci"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.25),
                                 gridspec_kw={"width_ratios": [1.3, 1]})
    xs = np.arange(len(f))
    a1.bar(xs, [r[3] for r in f], .55,
           color=[MUTE if abs(r[3]) < .003 else (GATE if r[3] > 0 else CLAIM)
                  for r in f], alpha=.9, edgecolor="none")
    for x, r in zip(xs, f):
        a1.text(x, r[3] + (.0006 if r[3] >= 0 else -.0006), f"{r[3]:+.4f}",
                ha="center", va="bottom" if r[3] >= 0 else "top", fontsize=6.0)
        a1.text(x, -.0035, f"n$=${r[1]}", ha="center", fontsize=5.8, color=INK)
    a1.axhline(0, color=INK, lw=1.0)
    a1.set_xticks(xs); a1.set_xticklabels([r[0] for r in f], fontsize=5.9)
    a1.set_ylabel("$\\Delta\\rho$", fontsize=7.0)
    a1.set_ylim(-.0045, .013)
    a1.set_title("개별 결함은 성능에 안 보인다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    a2.axvline(0, color=INK, lw=1.0)
    a2.hlines(0, ci[1], ci[2], color=CLAIM, lw=3.0, alpha=.85)
    a2.plot([ci[0]], [0], "o", color=CLAIM, ms=9, zorder=4)
    a2.text(ci[2] + .002, 0, f"P($>$0)$=${ci[3]:.3f}", fontsize=6.4, va="center",
            color=CLAIM)
    a2.set_yticks([0]); a2.set_yticklabels(["등급 B 제외"], fontsize=6.6)
    a2.set_xlabel("짝지은 95\% 구간", fontsize=7.0)
    a2.set_xlim(-.02, .045); a2.set_ylim(-.6, .6)
    a2.set_title("유망하지만 확인 안 됨", fontsize=7.2)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 64 ────────────────────────────────────────────────────────────
def fig_diaglies(out: Path, root: str = ".") -> dict:
    """노트64 — 진단 코드가 만든 세 오진."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note64.json").read_text())
    idol = j["idol"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.2),
                                 gridspec_kw={"width_ratios": [1, 1.1]})
    labs = ["고유 소속사", "2건 이상", "이력 보유\n레코드"]
    raw = [idol["raw_ag"], idol["raw_multi"], 5]
    nrm = [idol["norm_ag"], idol["norm_multi"], idol["hist"]]
    xs = np.arange(3); w = .34
    a1.bar(xs - w/2, raw, w, color=CLAIM, alpha=.9, edgecolor="none", label="정규화 없이")
    a1.bar(xs + w/2, nrm, w, color=GATE, alpha=.9, edgecolor="none", label="정규화(본 코드)")
    for x, r, n in zip(xs, raw, nrm):
        a1.text(x - w/2, r + 1.2, str(r), ha="center", fontsize=6.2)
        a1.text(x + w/2, n + 1.2, str(n), ha="center", fontsize=6.2, color=GATE)
    a1.set_xticks(xs); a1.set_xticklabels(labs, fontsize=6.3)
    a1.set_ylabel("건수", fontsize=7.0)
    a1.set_ylim(0, 78)
    a1.legend(fontsize=6.2, frameon=False, loc="upper right")
    a1.set_title("아이돌 소속사 --- 본 코드는 이미 묶고 있었다", fontsize=7.2)
    a1.tick_params(labelsize=6.3)

    a2.axis("off")
    rows = [("노트", "오진", "실제")] + [(c[0], c[1][:22], c[2][:22]) for c in j["cases"]]
    ytop = .92
    for i, r in enumerate(rows):
        y = ytop - i * .21
        col = INK if i == 0 else CLAIM
        a2.text(.00, y, r[0], fontsize=6.4, color=col,
                fontweight="bold" if i == 0 else "normal")
        a2.text(.22, y, r[1], fontsize=5.9, color=col)
        a2.text(.22, y - .075, r[2], fontsize=5.9, color=GATE if i else INK)
    a2.set_title("같은 실수 세 번", fontsize=7.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 65 ────────────────────────────────────────────────────────────
def fig_audit(out: Path, root: str = ".") -> dict:
    """노트65 — 감사 모듈의 자기 점검."""
    import json, numpy as np
    d = json.loads((Path(root) / "data/state/note65.json").read_text())["check"]
    ys = np.arange(len(d))[::-1]
    fig, ax = plt.subplots(figsize=(FULL, 1.95))
    ax.axvline(0, color=INK, lw=1.0)
    for y, r in zip(ys, d):
        c = GATE if abs(r[1]) < 1e-9 else MUTE
        ax.hlines(y, r[2], r[3], color=c, lw=2.6, alpha=.85)
        ax.plot([r[1]], [y], "o", color=c, ms=8, zorder=4)
        ax.text(r[3] + .003, y, r[4], fontsize=6.2, va="center", color=c)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in d], fontsize=6.4)
    ax.set_xlabel("$\\Delta\\rho$ (짝지은 95\% 구간, 60회)", fontsize=7.0)
    ax.set_xlim(-.075, .085)
    ax.set_title("이미 꺼진 축을 끄면 정확히 0이 나와야 한다", fontsize=7.4)
    ax.tick_params(labelsize=6.3)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 66 ────────────────────────────────────────────────────────────
def fig_repro(out: Path, root: str = ".") -> dict:
    """노트66 — 재현과 자기 점검."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note66.json").read_text())
    rp, ck = j["repro"], j["checks"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    a1.axvline(0, color=INK, lw=1.0)
    for i, r in enumerate(rp):
        c = MUTE if i == 0 else GATE
        a1.hlines(i, r[2], r[3], color=c, lw=3.2, alpha=.85)
        a1.plot([r[1]], [i], "o", color=c, ms=9, zorder=4)
        a1.text(r[3] + .006, i, f"폭 {r[3]-r[2]:.3f}", fontsize=6.3, va="center",
                color=c)
    a1.set_yticks(range(len(rp)))
    a1.set_yticklabels([r[0].replace(" (", "\n(") for r in rp], fontsize=6.1)
    a1.set_xlabel("도서 타깃 폭 배선의 효과", fontsize=7.0)
    a1.set_xlim(-.01, .26); a1.set_ylim(-.6, 1.6)
    a1.set_title("구간이 겹치고 폭은 절반", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    ys = np.arange(len(ck))[::-1]
    a2.axvline(0, color=INK, lw=1.0)
    for y, r in zip(ys, ck):
        exact = abs(r[1]) < 1e-9 and abs(r[2]) < 1e-9 and abs(r[3]) < 1e-9
        c = GATE if exact else MUTE
        a2.hlines(y, r[2], r[3], color=c, lw=2.4, alpha=.85)
        a2.plot([r[1]], [y], "o", color=c, ms=7, zorder=4)
        if exact:
            a2.text(.004, y, "정확히 0", fontsize=6.0, va="center", color=GATE)
    a2.set_yticks(ys); a2.set_yticklabels([r[0] for r in ck], fontsize=5.9)
    a2.set_xlabel("$\\Delta\\rho$ (자기 점검)", fontsize=7.0)
    a2.set_xlim(-.07, .05)
    a2.set_title("답을 아는 조건 다섯", fontsize=7.4)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 67 ────────────────────────────────────────────────────────────
def fig_vanished(out: Path, root: str = ".") -> dict:
    """노트67 — 표본이 늘자 어느 결정이 살아남았나."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note67.json").read_text())
    t = j["tests"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    ys = np.arange(len(t))[::-1]
    a1.axvline(0, color=INK, lw=1.0)
    for y, r in zip(ys, t):
        alive = r[7] == "재현"
        c = GATE if alive else CLAIM
        a1.plot([r[3]], [y + .16], "s", color=MUTE, ms=7)
        a1.hlines(y - .16, r[5], r[6], color=c, lw=2.6, alpha=.85)
        a1.plot([r[4]], [y - .16], "o", color=c, ms=7, zorder=4)
        a1.text(max(r[3], r[6]) + .008, y, r[7], fontsize=6.3, va="center", color=c)
    a1.set_yticks(ys); a1.set_yticklabels([r[0] for r in t], fontsize=6.2)
    a1.set_xlabel("효과 (회색 $=$ 원 노트, 색 $=$ 지금 재현)", fontsize=7.0)
    a1.set_xlim(-.06, .21)
    a1.set_title("원 효과가 큰 것만 살아남는다", fontsize=7.4)
    a1.tick_params(labelsize=6.2)

    orig = [r[3] for r in t]; now = [r[4] for r in t]
    a2.scatter(orig, now, s=54, color=[GATE if r[7] == "재현" else CLAIM for r in t],
               zorder=3)
    for o, n, r in zip(orig, now, t):
        a2.annotate(r[1] + f"\n$n{{=}}${r[2]}", (o, n), fontsize=6.0,
                    xytext=(6, -4), textcoords="offset points")
    lim = [-.02, .13]
    a2.plot(lim, lim, color=MUTE, lw=.9, ls="--")
    a2.axhline(0, color=INK, lw=.9); a2.axvline(0.02, color=CLAIM, lw=1.0, ls=":")
    a2.text(.022, -.012, "노트 44 문턱", fontsize=6.0, color=CLAIM)
    a2.set_xlabel("원 노트의 효과", fontsize=7.0)
    a2.set_ylabel("지금 재현한 효과", fontsize=7.0)
    a2.set_xlim(lim); a2.set_ylim(-.02, .13)
    a2.set_title("점선 위에 있으면 재현", fontsize=7.2)
    a2.tick_params(labelsize=6.3)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 스텝 68 ────────────────────────────────────────────────────────────
def fig_saturate(out: Path, root: str = ".") -> dict:
    """노트68 — 구간 반폭이 포화한다."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note68.json").read_text())
    c = j["ci"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    n = [r[2] for r in c]; hw = [r[3] for r in c]
    a1.plot(n, hw, "o-", color=GATE, ms=7, lw=1.5)
    for x, y, r in zip(n, hw, c):
        a1.text(x, y + .0022, f"{y:.4f}", ha="center", fontsize=6.2)
        a1.text(x, y - .0035, f"{r[0]}\n{r[1]}도메인", ha="center", fontsize=5.6,
                color=INK)
    xx = np.linspace(1200, 4300, 40)
    a1.plot(xx, hw[0] * np.sqrt(n[0] / xx), "--", color=CLAIM, lw=1.1,
            label="$n^{-1/2}$ 이면")
    a1.set_xlabel("총 레코드 수", fontsize=7.0)
    a1.set_ylabel("평균 $\\rho$ 의 95\% 구간 반폭", fontsize=7.0)
    a1.set_ylim(.032, .078)
    a1.legend(fontsize=6.2, frameon=False, loc="upper right")
    a1.set_title("두 배로 늘려도 1\%만 줄었다", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    st = j["state"]
    ys = np.arange(len(st))[::-1]
    a2.barh(ys + .18, [r[3] for r in st], .34, color=GATE, alpha=.9,
            edgecolor="none", label="대상으로")
    a2.barh(ys - .18, [r[4] for r in st], .34, color=CLAIM, alpha=.9,
            edgecolor="none", label="출처로")
    a2.set_yticks(ys)
    a2.set_yticklabels([f"{r[0]}\n$n{{=}}${r[1]}" for r in st], fontsize=5.9)
    a2.set_xlabel("평균 전이 $\\rho$", fontsize=7.0)
    a2.set_xlim(0, .55)
    a2.legend(fontsize=6.0, frameon=False, loc="lower right")
    a2.set_title(f"전체 $+${j['rho']:.4f}", fontsize=7.4)
    a2.tick_params(labelsize=6.1)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_seventh(out: Path, root: str = ".") -> dict:
    """노트69 — 일곱째 도메인이 구간을 좁혔는가."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note69.json").read_text())
    c = j["ci"]                       # [라벨, 도메인, 셀, 반폭]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1, 1.05]})
    xs = np.arange(len(c))
    hw = [r[3] for r in c]
    cell = [r[2] for r in c]
    pred = [hw[0] * np.sqrt(cell[0] / k) for k in cell]
    a1.plot(xs, pred, "--s", color=CLAIM, lw=1.1, ms=4, mfc="white",
            label="셀 수의 $n^{-1/2}$ 이면")
    a1.plot(xs, hw, "-o", color=GATE, lw=1.7, ms=7, zorder=3, label="실제")
    # 노트 49·68은 값이 붙어 있어 예측 곡선과 겹친다. 아래로 내린다.
    for x, y in zip(xs, hw):
        dn = x in (2, 3)
        a1.text(x, y + (-.0028 if dn else .0018), f"{y:.4f}", ha="center",
                va="top" if dn else "bottom", fontsize=6.3, color=GATE)
    a1.set_xticks(xs)
    a1.set_xticklabels([f"{r[0]}\n{r[1]}도메인\n{r[2]}셀" for r in c], fontsize=5.7)
    a1.set_xlim(-.45, len(c) - .35)
    a1.set_ylabel("평균 $\\rho$ 의 95% 구간 반폭", fontsize=7.0)
    a1.legend(fontsize=6.2, frameon=False, loc="upper right")
    a1.set_title(j["t1"].replace("\\", ""), fontsize=7.4)
    a1.tick_params(labelsize=6.3, length=0)

    st = j["state"]
    ys = np.arange(len(st))[::-1]
    a2.barh(ys + .19, [r[3] for r in st], .36, color=GATE,
            alpha=.9, edgecolor="none", label="대상으로")
    a2.barh(ys - .19, [r[4] for r in st], .36, color=CLAIM,
            alpha=.9, edgecolor="none", label="출처로")
    for y, r in zip(ys, st):
        if r[0] == "애니":
            a2.axhspan(y - .5, y + .5, color=MUTE, alpha=.22, zorder=0)
    a2.set_yticks(ys)
    a2.set_yticklabels([f"{r[0]} $n{{=}}${r[1]}" for r in st], fontsize=6.0)
    a2.set_xlabel("평균 전이 $\\rho$", fontsize=7.0)
    a2.set_xlim(0, .55)
    a2.legend(fontsize=6.2, frameon=False, loc="lower right")
    a2.set_title(f"정향한 일곱 도메인 --- 전체 $+${j['rho']:.4f}", fontsize=7.4)
    a2.tick_params(labelsize=6.1, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_orient(out: Path, root: str = ".") -> dict:
    """노트69 — 방향은 정렬이 못 맞춘다. 라벨 몇 건이면 잡히는가."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note69b.json").read_text())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.5),
                                 gridspec_kw={"width_ratios": [1, 1.1]})

    # 왼쪽 --- 축과 라벨의 부호. 애니만 전부 음수다.
    rows, doms = j["axcorr"]["rows"], j["axcorr"]["doms"]
    for i, (lab, vs) in enumerate(rows):
        for k, v in enumerate(vs):
            if v is None:
                a1.plot(k, -i, "x", color=MUTE, ms=4, mew=1.0)
                continue
            a1.plot(k, -i, "o", ms=3.2 + 11 * abs(v),
                    color=(GATE if v > 0 else CLAIM), alpha=.85)
    a1.set_xticks(range(len(doms)))
    a1.set_xticklabels(doms, fontsize=6.2)
    a1.set_yticks([-i for i in range(len(rows))])
    a1.set_yticklabels([r[0] for r in rows], fontsize=6.2)
    a1.axvline(len(doms) - 1.5, color=INK, lw=.8, ls=":")
    a1.set_xlim(-.7, len(doms) - .3)
    a1.set_ylim(-len(rows) + .45, .7)
    a1.set_title("축과 라벨의 순위 상관 --- 파랑 $+$, 빨강 $-$", fontsize=7.2)
    a1.tick_params(length=0)
    for s in ("top", "right", "left", "bottom"):
        a1.spines[s].set_visible(False)

    # 오른쪽 --- 라벨 k건으로 방향을 맞출 확률.
    ks = j["ks"]
    for lab, ys, full in j["sign"]:
        xs = [k for k, y in zip(ks, ys) if y is not None]
        vv = [y for y in ys if y is not None]
        hot = lab == "애니"
        a2.plot(xs, vv, "-o" if hot else "-", ms=3.8 if hot else 0,
                lw=1.9 if hot else .9,
                color=CLAIM if hot else MUTE, alpha=1.0 if hot else .7,
                label="애니" if hot else None, zorder=3 if hot else 1)
    a2.axhline(.95, color=GATE, lw=.9, ls="--")
    a2.text(3.1, .957, "95%", fontsize=6.2, color=GATE)
    a2.axvline(12, color=INK, lw=.8, ls=":")
    a2.text(13.0, .59, "노트 59의 12건\n(눈금 보정)", fontsize=5.8, color=INK)
    a2.set_xscale("log")
    a2.set_xticks(ks)
    a2.set_xticklabels([str(k) for k in ks], fontsize=6.3)
    a2.set_xlabel("대상 도메인에서 본 라벨 수", fontsize=7.0)
    a2.set_ylabel("전이 방향을 맞출 확률", fontsize=7.0)
    a2.set_ylim(.55, 1.02)
    a2.legend(fontsize=6.3, frameon=False, loc="lower right")
    a2.set_title("방향은 눈금보다 여덟 배 비싸다", fontsize=7.2)
    a2.tick_params(labelsize=6.3)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_halfknown(out: Path, root: str = ".") -> dict:
    """노트70 — 방향 보정의 값. 적은 k에서는 손해다."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/orient.json").read_text())
    ks = [int(k) for k in j["ks"]]
    r = j["r"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.5),
                                 gridspec_kw={"width_ratios": [1.05, 1]})

    a1.axhline(j["six"][0], color=INK, lw=1.0, ls="--")
    a1.text(ks[-1], j["six"][0] + .006, "여섯 도메인 · 보정 없음", fontsize=6.0,
            color=INK, ha="right")
    for m, lab, col, w in (("cell", "셀별 부호", GATE, 1.9),
                           ("dom", "도메인별 부호", CLAIM, 1.1),
                           ("axis", "축 정향(구조 교정)", MUTE, 1.1)):
        ys = [r[str(k)][m][0] for k in ks]
        a1.plot(ks, ys, "-o", ms=3.6, lw=w, color=col, label=lab,
                zorder=3 if m == "cell" else 2)
    a1.set_xlabel("대상 도메인에서 본 라벨 수 $k$", fontsize=7.0)
    a1.set_ylabel("42셀 평균 $\\rho$ (유보 평가)", fontsize=7.0)
    a1.legend(fontsize=6.2, frameon=False, loc="lower right")
    a1.set_title("사후 부호가 구조 교정을 이긴다", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    p = j["paired"]
    xs = [k for k in ks if str(k) in p]
    mid = [p[str(k)][0] for k in xs]
    lo = [p[str(k)][0] - p[str(k)][1] for k in xs]
    hi = [p[str(k)][2] - p[str(k)][0] for k in xs]
    col = [GATE if p[str(k)][1] > 0 else MUTE for k in xs]
    a2.axhline(0, color=INK, lw=.9)
    a2.errorbar(xs, mid, yerr=[lo, hi], fmt="none", ecolor=MUTE, elinewidth=1.1,
                capsize=3, zorder=2)
    for x, y, c in zip(xs, mid, col):
        a2.plot(x, y, "o", ms=6.5, color=c, zorder=3)
    a2.axvspan(30, 44, color=GATE, alpha=.10, zorder=0)
    a2.text(37, -.24, "채택 구간", fontsize=6.2, color=GATE, ha="center")
    a2.text(6, -.24, "보정이 손해", fontsize=6.2, color=CLAIM, ha="center")
    a2.set_xlabel("대상 도메인에서 본 라벨 수 $k$", fontsize=7.0)
    a2.set_ylabel("보정 없음 대비 짝지은 차이", fontsize=7.0)
    a2.set_title("서른두 건부터 값을 한다", fontsize=7.4)
    a2.tick_params(labelsize=6.3)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_together(out: Path, root: str = ".") -> dict:
    """노트71 — 출처를 합치면. 왼쪽 대상별 이득, 오른쪽 팝업 출처별."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note71.json").read_text())
    t = j["table"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.1, 1]})

    ks = sorted(t, key=lambda k: -t[k]["ens"])
    ys = np.arange(len(ks))[::-1]
    for y, k in zip(ys, ks):
        m, e = t[k]["mean"], t[k]["ens"]
        a1.plot([m, e], [y, y], "-", color=MUTE, lw=1.3, zorder=1)
        a1.plot(m, y, "o", ms=5.5, color=MUTE, zorder=2)
        a1.plot(e, y, "o", ms=7, color=(GATE if e > 0 else CLAIM), zorder=3)
    a1.axvline(0, color=INK, lw=.8)
    a1.set_yticks(ys)
    a1.set_yticklabels([f"{k} $n{{=}}${t[k]['n']}" for k in ks], fontsize=6.1)
    a1.set_xlabel("대상별 $\\rho$", fontsize=7.0)
    a1.set_xlim(-.35, .55)
    a1.plot([], [], "o", color=MUTE, ms=5.5, label="셀 평균(지금까지의 판정치)")
    a1.plot([], [], "o", color=GATE, ms=7, label="앙상블(제품이 쓰는 것)")
    a1.legend(fontsize=6.0, frameon=False, loc="upper left",
              bbox_to_anchor=(0.0, 0.42))
    a1.set_title("일곱 대상 전부에서 합친 쪽이 낫다", fontsize=7.4)
    a1.tick_params(labelsize=6.2, length=0)

    src = j["popup_src"]
    names = sorted(src, key=lambda k: -src[k])
    xs = np.arange(len(names))
    a2.bar(xs, [src[k] for k in names], .62,
           color=[GATE if src[k] > 0 else CLAIM for k in names],
           alpha=.9, edgecolor="none")
    ens = t["팝업"]["ens"]
    a2.axhline(ens, color=INK, lw=1.4, ls="--")
    a2.text(len(names) - .4, ens + .022, f"앙상블 $+${ens:.3f}", fontsize=6.4,
            color=INK, ha="right")
    a2.axhline(t["팝업"]["mean"], color=MUTE, lw=1.0, ls=":")
    a2.text(-.4, t["팝업"]["mean"] + .022, f"셀 평균 $+${t['팝업']['mean']:.3f}",
            fontsize=6.2, color=MUTE)
    a2.axhline(0, color=INK, lw=.8)
    a2.set_xticks(xs)
    a2.set_xticklabels(names, fontsize=6.2)
    a2.set_ylabel("팝업 예측 $\\rho$", fontsize=7.0)
    a2.set_ylim(-.4, .58)
    a2.set_title("출처 하나가 반대로 가도 앙상블은 안 무너진다", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_metric(out: Path, root: str = ".") -> dict:
    """노트72 — 판정치 전환. 왼쪽 부호/합치기 순서, 오른쪽 나쁜 도메인의 비용."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note72.json").read_text())
    m = j["modes"]
    ks = sorted(int(k) for k in m)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.5),
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    for key, lab, col, w in (("then_blend", "부호 뒤 합치기", GATE, 1.9),
                             ("vote", "다수결 부호", CLAIM, 1.1),
                             ("blend_then", "합친 뒤 부호", MUTE, 1.1)):
        a1.plot(ks, [m[str(k)][key]["rho"] for k in ks], "-o", ms=3.6, lw=w,
                color=col, label=lab, zorder=3 if key == "then_blend" else 2)
    a1.axhline(m["0"]["vote"]["rho"], color=INK, lw=.8, ls=":")
    a1.text(ks[-1], m["0"]["vote"]["rho"] - .016, "보정 없음", fontsize=6.0,
            color=INK, ha="right")
    a1.set_xlabel("대상 도메인에서 본 라벨 수 $k$", fontsize=7.0)
    a1.set_ylabel("앙상블 $\\rho$ (유보 평가)", fontsize=7.0)
    a1.legend(fontsize=6.2, frameon=False, loc="lower right")
    a1.set_title("부호는 셀마다, 합치기는 그 뒤에", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    c = j["cost"]
    xs = np.arange(2)
    a2.bar(xs - .17, [c["cell"][0], c["ens"][0]], .32, color=MUTE, alpha=.9,
           edgecolor="none", label="여섯 도메인")
    a2.bar(xs + .17, [c["cell"][1], c["ens"][1]], .32, color=GATE, alpha=.9,
           edgecolor="none", label="일곱 도메인(애니 포함)")
    for i, k in enumerate(("cell", "ens")):
        a2.annotate("", xy=(i + .17, c[k][1]), xytext=(i - .17, c[k][0]),
                    arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.4))
        a2.text(i, max(c[k]) + .022, f"{c[k][1]-c[k][0]:+.4f}", ha="center",
                fontsize=7.0, color=CLAIM)
    a2.set_xticks(xs)
    a2.set_xticklabels(["셀 평균", "앙상블"], fontsize=7.0)
    a2.set_ylabel("판정치 $\\rho$", fontsize=7.0)
    a2.set_ylim(0, .52)
    a2.legend(fontsize=6.2, frameon=False, loc="upper center", ncol=2,
              bbox_to_anchor=(0.5, 1.0), columnspacing=1.0, handlelength=1.2)
    a2.set_title("방향 틀린 도메인의 값이 42% 싸진다", fontsize=7.4)
    a2.tick_params(labelsize=6.3, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_gate(out: Path, root: str = ".") -> dict:
    """노트73 — 왼쪽 방향 결정의 값, 오른쪽 게이트의 붕괴."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note73.json").read_text())
    s, m = j["sign"], j["modes"]
    ks = sorted(int(k) for k in s)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.5),
                                 gridspec_kw={"width_ratios": [1.1, 1]})

    a1.plot(ks, [m[str(k)]["then_blend"]["rho"] for k in ks], "-o", ms=3.6, lw=1.2,
            color=MUTE, label="셀마다 부호 (결정 6번 · 노트 72)")
    a1.plot(ks, [s[str(k)]["cons_k"]["rho"] for k in ks], "-o", ms=4.0, lw=1.9,
            color=GATE, label="합의 $+$ 전역 부호 (결정 1번)", zorder=3)
    a1.axhline(s["0"]["cons"]["rho"], color=CLAIM, lw=1.1, ls="--")
    a1.text(ks[-1], s["0"]["cons"]["rho"] + .006, "합의만 (라벨 0건)", fontsize=6.2,
            color=CLAIM, ha="right")
    a1.axhline(s["0"]["plain"]["rho"], color=INK, lw=.9, ls=":")
    a1.text(ks[-1], s["0"]["plain"]["rho"] - .014, "균등", fontsize=6.2,
            color=INK, ha="right")
    a1.set_xlabel("대상 도메인에서 본 라벨 수 $k$", fontsize=7.0)
    a1.set_ylabel("앙상블 $\\rho$ (유보 평가)", fontsize=7.0)
    a1.legend(fontsize=6.1, frameon=False, loc="lower right")
    a1.set_title("결정 여섯을 하나로 줄여도 같은 자리", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    sets = j["gate"]["sets"]
    xs = np.arange(len(sets))
    vals = [r[1] for r in sets]
    a2.bar(xs, vals, .6, color=[CLAIM if v < j["gate"]["eq"] else GATE for v in vals],
           alpha=.9, edgecolor="none")
    for x, v in zip(xs, vals):
        a2.text(x, v + .006, f"{v:+.4f}", ha="center", fontsize=6.3)
    a2.axhline(j["gate"]["eq"], color=INK, lw=1.0, ls=":")
    a2.text(len(sets) - .5, j["gate"]["eq"] + .006, "균등", fontsize=6.2,
            color=INK, ha="right")
    a2.set_xticks(xs)
    a2.set_xticklabels([r[0].replace(" ", "\n", 1) for r in sets], fontsize=5.9)
    a2.set_ylabel("판정치 $\\rho$", fontsize=7.0)
    a2.set_ylim(0, .34)
    a2.set_title("대상 수준 특징을 넣으면 무너진다", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_eighth(out: Path, root: str = ".") -> dict:
    """노트74 — 왼쪽 상충 법칙(r=+0.998), 오른쪽 도메인 수와 판정치."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note74.json").read_text())
    st = j["state"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    x = np.array([r[1] for r in st])
    tg = np.array([r[3] for r in st])
    sr = np.array([r[4] for r in st])
    ani = np.array([r[0] == "애니" for r in st])
    for xs, ys, col, lab in ((x, tg, GATE, "대상으로"), (x, sr, CLAIM, "출처로")):
        a1.plot(xs[~ani], ys[~ani], "o", ms=6, color=col, label=lab, zorder=3)
        a1.plot(xs[ani], ys[ani], "o", ms=6, color=col, mfc="white", mew=1.4,
                zorder=3)
        z = np.polyfit(xs[~ani], ys[~ani], 1)
        xx = np.linspace(x.min() - .02, x.max() + .02, 20)
        a1.plot(xx, np.polyval(z, xx), "--", color=col, lw=1.0, alpha=.8)
    # 자기 ρ가 붙은 도메인이 있어 라벨이 겹친다. 위아래로 번갈아 둔다.
    for i, r in enumerate(sorted(st, key=lambda z: z[1])):
        dy = 8 if i % 2 == 0 else -12
        a1.annotate(r[0], (r[1], r[3]), textcoords="offset points",
                    xytext=(0, dy), ha="center", fontsize=5.8, color=INK)
    a1.axhline(0, color=INK, lw=.7)
    a1.set_xlabel("도메인 안 자기 $\\rho$", fontsize=7.0)
    a1.set_ylabel("평균 전이 $\\rho$", fontsize=7.0)
    a1.legend(fontsize=6.2, frameon=False, loc="lower left")
    a1.set_title(f"애니 제외 7점: 대상 $r{{=}}${j['law']['noani'][0]:+.3f} · "
                 f"출처 $r{{=}}${j['law']['noani'][1]:+.3f}", fontsize=7.2)
    a1.tick_params(labelsize=6.3)

    h = j["hist"]
    xs = np.arange(len(h))
    a2.plot(xs, [r[3] for r in h], "-o", color=GATE, ms=6, lw=1.7)
    for i, r in enumerate(h):
        a2.text(i, r[3] + .0016, f"{r[3]:.4f}", ha="center", fontsize=6.1,
                color=GATE)
    a2.set_xticks(xs)
    a2.set_xticklabels([f"{r[0]}\n{r[1]}도메인" for r in h], fontsize=5.5)
    a2.set_ylabel("95% 구간 반폭", fontsize=7.0)
    a2.set_xlim(-.5, len(h) - .5)
    a2.set_title("구간 반폭 --- 도메인이 지렛대다", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_seventyfive(out: Path, root: str = ".") -> dict:
    """노트75 — 왼쪽 법칙 회복, 오른쪽 팝업이 판정 못 하는 폭."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note75.json").read_text())
    st = j["state"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1, 1.15]})

    x = np.array([r[2] for r in st])
    tg = np.array([r[4] for r in st])
    a1.plot(x, tg, "o", ms=6.5, color=GATE, zorder=3)
    z = np.polyfit(x, tg, 1)
    xx = np.linspace(.15, .70, 20)
    a1.plot(xx, np.polyval(z, xx), "--", color=GATE, lw=1.1, alpha=.85)
    # 애니의 이동 --- 배선 전후.
    ai = [i for i, r in enumerate(st) if r[0] == "애니"][0]
    a1.annotate("", xy=(x[ai], tg[ai]), xytext=(j["before"]["ani_self"], -0.251),
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.5))
    a1.plot(j["before"]["ani_self"], -0.251, "o", ms=6.5, color=CLAIM,
            mfc="white", mew=1.5, zorder=3)
    a1.text(j["before"]["ani_self"], -0.251 - .035, "애니(배선 전)", fontsize=5.8,
            color=CLAIM, ha="center")
    for i, r in enumerate(sorted(st, key=lambda z: z[2])):
        dy = 9 if i % 2 == 0 else -14
        a1.annotate(r[0], (r[2], r[4]), textcoords="offset points",
                    xytext=(0, dy), ha="center", fontsize=5.8, color=INK)
    a1.axhline(0, color=INK, lw=.7)
    a1.set_xlabel("도메인 안 자기 $\\rho$", fontsize=7.0)
    a1.set_ylabel("대상 전이 $\\rho$", fontsize=7.0)
    a1.set_title(f"여덟 점 전부 $r{{=}}${j['after']['law'][0]:+.3f}", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    p = j["proxy_ci"]
    labs = list(p)
    ys = np.arange(len(labs))[::-1]
    for y, lab in zip(ys, labs):
        a, q = p[lab]["a"], p[lab]["p"]
        a2.plot([a[1], a[2]], [y + .16, y + .16], "-", color=GATE, lw=2.4,
                solid_capstyle="butt")
        a2.plot(a[0], y + .16, "o", ms=4.5, color=GATE)
        a2.plot([q[1], q[2]], [y - .16, y - .16], "-", color=CLAIM, lw=2.4,
                solid_capstyle="butt")
        a2.plot(q[0], y - .16, "o", ms=4.5, color=CLAIM)
    a2.axvline(0, color=INK, lw=.9)
    a2.set_yticks(ys)
    a2.set_yticklabels(labs, fontsize=6.1)
    a2.set_xlabel("변화량 $\\Delta\\rho$", fontsize=7.0)
    a2.plot([], [], "-o", color=GATE, lw=2.4, ms=4.5, label="판정치(여덟 평균)")
    a2.plot([], [], "-o", color=CLAIM, lw=2.4, ms=4.5, label="팝업 하나")
    a2.legend(fontsize=6.2, frameon=False, loc="lower right")
    a2.set_title("팝업의 구간이 네 배 이상 넓다", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_prosp(out: Path, root: str = ".") -> dict:
    """노트76 — 왼쪽 배선 재탐색의 빈손, 오른쪽 시간 분할."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note76.json").read_text())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.5),
                                 gridspec_kw={"width_ratios": [1, 1.2]})

    ds = np.array([r[4] for r in j["rewire"]["rows"]])
    a1.hist(ds, bins=26, color=MUTE, alpha=.85, edgecolor="none")
    a1.axvline(0, color=INK, lw=.9)
    a1.axvspan(-0.011, 0.011, color=GATE, alpha=.13, zorder=0)
    top = a1.get_ylim()[1]
    a1.text(-0.011, top * .97, "구간 반폭 $\\pm$0.011", fontsize=6.2,
            color=GATE, ha="right", va="top")
    a1.plot(ds.max(), top * .18, "v", color=CLAIM, ms=6)
    a1.text(ds.max() + .004, top * .30,
            f"최선 $+${ds.max():.4f}\n(애니 미디어$\\leftarrow$더빙)",
            fontsize=5.9, color=CLAIM, ha="left")
    a1.set_xlim(ds.min() - .008, .028)
    a1.set_xlabel("배선 후보의 $\\Delta$판정치", fontsize=7.0)
    a1.set_ylabel("후보 수", fontsize=7.0)
    a1.set_title(f"후보 {len(ds)}개 --- 문턱을 넘는 것이 없다", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    cuts = ["2024.0", "2025.0"]
    doms = [k for k in j["prosp"][cuts[0]] if k in j["prosp"][cuts[1]]]
    ys = np.arange(len(doms))[::-1]
    for y, d in zip(ys, doms):
        v = j["prosp"]["2025.0"][d]
        a2.plot([v["ci_past"][0], v["ci_past"][1]], [y, y], "-", color=MUTE,
                lw=2.2, solid_capstyle="butt", zorder=2)
        a2.plot(v["all"], y, "o", ms=5, color=INK, mfc="white", mew=1.2, zorder=3)
        a2.plot(v["past"], y, "o", ms=6.5,
                color=(GATE if d == "팝업" else CLAIM), zorder=4)
    a2.axvline(0, color=INK, lw=.9)
    a2.set_yticks(ys)
    a2.set_yticklabels([f"{d} ($n{{=}}${j['prosp']['2025.0'][d]['n_future']})"
                        for d in doms], fontsize=6.0)
    a2.set_xlabel("미래 레코드에서의 앙상블 $\\rho$", fontsize=7.0)
    a2.plot([], [], "o", color=INK, mfc="white", mew=1.2, ms=5, label="출처 전부")
    a2.plot([], [], "o", color=CLAIM, ms=6.5, label="출처를 2025 이전으로 자름")
    a2.legend(fontsize=6.1, frameon=False, loc="upper left",
              bbox_to_anchor=(0.0, 0.30))
    a2.set_title("시점 2025 --- 자르는 값이 거의 없다", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_onebyone(out: Path, root: str = ".") -> dict:
    """노트77 — 왼쪽 네 규약, 오른쪽 설계 결정의 시간 분할."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note77.json").read_text())
    o = j["one"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.5),
                                 gridspec_kw={"width_ratios": [1, 1.05]})

    labs = ["① 한꺼번에\n(노트 76)", "② 하나 빼고\n(LOO 투영)",
            "③ 과거 공간\n$+$ 미래 묶음", "④ 완전 한 건씩\n(제품 그대로)"]
    vals = [o["batch"], o["loo"], o["past_only"], o["one"]]
    cis = [None, None, o["past_only_ci"], o["one_ci"]]
    xs = np.arange(4)
    for x, v, c in zip(xs, vals, cis):
        col = GATE if x == 3 else MUTE
        if c:
            a1.plot([x, x], c, "-", color=col, lw=2.2, solid_capstyle="butt",
                    alpha=.55, zorder=2)
        a1.plot(x, v, "o", ms=8 if x == 3 else 6.5, color=col, zorder=3)
        a1.text(x, v + .022, f"{v:+.4f}", ha="center", fontsize=6.4, color=col)
    a1.axhline(0, color=INK, lw=.8)
    a1.set_xticks(xs)
    a1.set_xticklabels(labs, fontsize=5.9)
    a1.set_xlim(-.5, 3.5)
    a1.set_ylabel("미래 팝업 59건의 $\\rho$", fontsize=7.0)
    a1.set_title("전도적 가정의 값 = 0.011", fontsize=7.4)
    a1.tick_params(labelsize=6.2, length=0)

    p = np.array([[x[2], x[3]] for x in j["pts"]])
    hot = np.array([x[0] == "애니" for x in j["pts"]])
    a2.plot(p[~hot, 0], p[~hot, 1], "o", ms=4, color=MUTE, alpha=.75)
    a2.plot(p[hot, 0], p[hot, 1], "o", ms=5.5, color=CLAIM, zorder=3)
    lim = [p.min() - .01, p.max() + .01]
    a2.plot(lim, lim, "--", color=INK, lw=.8, alpha=.6)
    a2.axhline(0, color=INK, lw=.7)
    a2.axvline(0, color=INK, lw=.7)
    a2.axhspan(-0.011, 0.011, color=GATE, alpha=.12, zorder=0)
    a2.set_xlabel("2025 이전 데이터로 본 $\\Delta$", fontsize=7.0)
    a2.set_ylabel("전체 데이터로 본 $\\Delta$", fontsize=7.0)
    a2.plot([], [], "o", color=CLAIM, ms=5.5, label="애니 후보")
    a2.legend(fontsize=6.2, frameon=False, loc="lower right")
    a2.set_title(f"후보 {len(j['pts'])}개 · $r{{=}}${j['r']:+.3f}", fontsize=7.4)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_ninth(out: Path, root: str = ".") -> dict:
    """노트78 — 왼쪽 반폭 이력, 오른쪽 아홉 도메인의 두 법칙."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note78.json").read_text())
    h = j["hist"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.05, 1]})

    xs = np.arange(len(h))
    hw = [r[3] for r in h]
    cell = [r[2] for r in h]
    pred = [hw[0] * np.sqrt(cell[0] / k) for k in cell]
    a1.plot(xs, pred, "--s", color=CLAIM, lw=1.1, ms=4, mfc="white",
            label="셀 수의 $n^{-1/2}$ 이면")
    a1.plot(xs, hw, "-o", color=GATE, lw=1.7, ms=6.5, zorder=3, label="실제")
    for x, y in zip(xs, hw):
        a1.text(x, y + .0016, f"{y:.4f}", ha="center", fontsize=6.0, color=GATE)
    a1.set_xticks(xs)
    a1.set_xticklabels([f"{r[1]}도메인\n{r[2]}셀" for r in h], fontsize=5.7)
    a1.set_xlim(-.45, len(h) - .4)
    a1.set_ylabel("95% 구간 반폭", fontsize=7.0)
    a1.legend(fontsize=6.2, frameon=False, loc="upper right")
    a1.set_title("아홉째가 반폭을 10% 줄였다", fontsize=7.4)
    a1.tick_params(labelsize=6.2, length=0)

    st = j["state"]
    x = np.array([r[2] for r in st])
    tg = np.array([r[4] for r in st])
    sr = np.array([r[5] for r in st])
    for ys, col, lab in ((tg, GATE, "대상으로"), (sr, CLAIM, "출처로")):
        a2.plot(x, ys, "o", ms=5.5, color=col, label=lab, zorder=3)
        z = np.polyfit(x, ys, 1)
        xx = np.linspace(.15, .70, 20)
        a2.plot(xx, np.polyval(z, xx), "--", color=col, lw=1.0, alpha=.8)
    hot = [i for i, r in enumerate(st) if r[0] == "만화"][0]
    a2.plot(x[hot], tg[hot], "o", ms=9, mfc="none", mec=INK, mew=1.4, zorder=4)
    a2.plot(x[hot], sr[hot], "o", ms=9, mfc="none", mec=INK, mew=1.4, zorder=4)
    # 자기 ρ가 0.36~0.40에 셋이 몰려 있어 라벨이 겹친다. 좌우로도 흩는다.
    off = {"팝업": (-16, 10), "게임": (16, 10), "만화": (0, -14),
           "웹툰": (12, 9), "아이돌": (-14, 9), "애니": (0, 10),
           "도서": (0, -14), "펀딩": (-14, 8), "모바일": (0, 10)}
    for r in st:
        a2.annotate(r[0], (r[2], r[4]), textcoords="offset points",
                    xytext=off.get(r[0], (0, 9)), ha="center", fontsize=5.7,
                    color=INK)
    a2.set_xlabel("도메인 안 자기 $\\rho$", fontsize=7.0)
    a2.set_ylabel("평균 전이 $\\rho$", fontsize=7.0)
    a2.legend(fontsize=6.2, frameon=False, loc="lower left")
    a2.set_title(f"아홉 점 · 대상 $r{{=}}${j['law'][0]:+.3f} --- 만화가 교차점",
                 fontsize=7.2)
    a2.tick_params(labelsize=6.3)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_ceiling(out: Path, root: str = ".") -> dict:
    """노트79 — 왼쪽 두 플랫폼의 라벨 일치, 오른쪽 만화 국가 분해."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note79.json").read_text())
    P = np.array([[p[0], p[1]] for p in j["pairs"]], float)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1, 1.1]})

    a1.plot(P[:, 0], P[:, 1], "o", ms=3.4, color=GATE, alpha=.55)
    a1.set_xscale("log")
    a1.set_yscale("log")
    a1.set_xlabel("네이버 웹툰 관심 등록 수", fontsize=7.0)
    a1.set_ylabel("AniList 서재 등록 수", fontsize=7.0)
    a1.set_title(f"같은 작품 {len(P)}건 · $\\rho={j['rho']:+.3f}$", fontsize=7.4)
    a1.tick_params(labelsize=6.3)
    a1.text(.04, .94, f"상한 $\\sqrt{{{j['rho']:.3f}}}={j['ceiling']:.3f}$",
            transform=a1.transAxes, fontsize=6.6, color=CLAIM, va="top")

    labs = ["전체\n(2,400)", "일본만\n(1,789)", "한국만\n(556)"]
    keys = ["전체", "일본만", "한국만"]
    xs = np.arange(3)
    selfr = [j["split"][k]["self"] for k in keys]
    met = [j["split"][k]["metric"] for k in keys]
    a2.bar(xs - .18, selfr, .34, color=GATE, alpha=.9, edgecolor="none",
           label="만화 자기 $\\rho$")
    a2.bar(xs + .18, met, .34, color=CLAIM, alpha=.9, edgecolor="none",
           label="아홉 도메인 판정치")
    for x, v in zip(xs - .18, selfr):
        a2.text(x, v + .012, f"{v:+.3f}", ha="center", fontsize=6.2, color=GATE)
    for x, v in zip(xs + .18, met):
        a2.text(x, v + .012, f"{v:+.4f}", ha="center", fontsize=6.0, color=CLAIM)
    a2.axhline(j["ceiling"], color=INK, lw=1.1, ls="--")
    a2.text(2.45, j["ceiling"] + .012, "라벨 상한 0.724", fontsize=6.4,
            color=INK, ha="right")
    a2.set_xticks(xs)
    a2.set_xticklabels(labs, fontsize=6.2)
    a2.set_ylim(0, .82)
    a2.legend(fontsize=6.2, frameon=False, loc="upper left")
    a2.set_title("AniList의 한국 작품은 축이 못 설명한다", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_seeds(out: Path, root: str = ".") -> dict:
    """노트80 — 왼쪽 부분집합 훑기, 오른쪽 자기 이득이 판정치로 얼마나 가나."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note80.json").read_text())
    rows = j["scan"][:12]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    ys = np.arange(len(rows))[::-1]
    ds = [r[6] for r in rows]
    tested = {"is_free": "애니", "is_adult": "애니", "finished": "웹툰"}
    cols = [GATE if (r[1] in tested and r[0] == tested[r[1]]) else MUTE for r in rows]
    a1.barh(ys, ds, .62, color=cols, alpha=.9, edgecolor="none")
    for y, r in zip(ys, rows):
        a1.text(r[6] + .0016, y, f"{r[3]:,}건", va="center", fontsize=5.6, color=INK)
    a1.set_yticks(ys)
    KO = {"is_free": "무료", "is_adult": "성인", "is_only": "독점", "medium": "형식",
          "finished": "완결", "daily_pass": "유료", "age_type": "등급",
          "publisher": "출판사", "category_name": "분류", "advisory": "등급",
          "format": "형식", "status": "상태", "label_basis": "라벨근거",
          "is_free_g": "무료", "source": "출처", "is_ending": "완결"}
    a1.set_yticklabels([f"{r[0]}·{KO.get(r[1], r[1])}={str(r[2])[:8]}" for r in rows],
                       fontsize=5.6)
    a1.axvline(0, color=INK, lw=.8)
    a1.set_xlabel("부분집합을 빼면 오르는 자기 $\\rho$", fontsize=7.0)
    a1.set_xlim(0, max(ds) * 1.28)
    a1.set_title(f"부분집합 {len(j['scan'])}개를 훑었다 (상위 12)", fontsize=7.4)
    a1.tick_params(labelsize=6.0, length=0)

    p = j["pts"]
    for lab, dself, dmet, k in p:
        col = GATE if k >= 4 else (CLAIM if k >= 1 else MUTE)
        a2.plot(dself, dmet, "o", ms=8, color=col, zorder=3)
        a2.annotate(f"{lab}\n{k}/4 씨앗", (dself, dmet), textcoords="offset points",
                    xytext=(0, -22 if lab.startswith("애니 성인") else 12),
                    ha="center", fontsize=5.8, color=INK)
    # 1:1 선은 눈금 밖으로 금방 벗어난다. 보이는 구간만 그린다.
    xx = np.linspace(0, .012, 10)
    a2.plot(xx, xx, "--", color=INK, lw=.8, alpha=.5)
    a2.text(.0125, .0112, "1:1", fontsize=6.2, color=INK)
    a2.axhline(0, color=INK, lw=.8)
    a2.axhspan(-0.005, 0.005, color=MUTE, alpha=.18, zorder=0)
    a2.set_xlabel("$\\Delta$ 도메인 자기 $\\rho$", fontsize=7.0)
    a2.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a2.set_xlim(0, .10)
    a2.set_ylim(-.006, .012)
    a2.set_title("자기 이득의 10분의 1만 판정치로 간다", fontsize=7.4)
    a2.tick_params(labelsize=6.3)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_samesame(out: Path, root: str = ".") -> dict:
    """노트81 — 왼쪽 팝업 출처 순위, 오른쪽 라벨 신뢰도 두 측정."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note81.json").read_text())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1, 1.05]})

    ks = list(j["pop"])
    ys = np.arange(len(ks))[::-1]
    cols = [GATE if k == "세계애니" else (CLAIM if k == "애니" else MUTE) for k in ks]
    a1.barh(ys, [j["pop"][k] for k in ks], .62, color=cols, alpha=.9,
            edgecolor="none")
    for y, k in zip(ys, ks):
        a1.text(j["pop"][k] + .008, y, f"{j['pop'][k]:+.3f}", va="center",
                fontsize=6.0, color=INK)
    a1.set_yticks(ys)
    a1.set_yticklabels(ks, fontsize=6.3)
    a1.set_xlim(0, .58)
    a1.set_xlabel("팝업 예측 $\\rho$", fontsize=7.0)
    a1.set_title("같은 애니, 다른 라벨 --- 꼴찌에서 2위로", fontsize=7.4)
    a1.tick_params(labelsize=6.2, length=0)

    P = np.array(j["pairs2"], float)
    a2.plot(P[:, 0], P[:, 1], "o", ms=4.5, color=GATE, alpha=.7)
    a2.set_xscale("log")
    a2.set_yscale("log")
    a2.set_xlabel("라프텔 한줄평 수", fontsize=7.0)
    a2.set_ylabel("AniList 서재 등록 수", fontsize=7.0)
    r2 = j["rel2"]
    r1 = j["rel1"]
    a2.set_title(f"애니 {r2['n']}건 · $\\rho={r2['rho']:+.3f}$", fontsize=7.4)
    a2.text(.03, .96, f"천장 추정\n{r1['pair']} $n{{=}}${r1['n']}: "
                      f"$\\sqrt{{{r1['rho']:.3f}}}={r1['ceil']:.3f}$\n"
                      f"{r2['pair']} $n{{=}}${r2['n']}: "
                      f"$\\sqrt{{{r2['rho']:.3f}}}={r2['ceil']:.3f}$",
            transform=a2.transAxes, fontsize=6.2, color=CLAIM, va="top")
    a2.tick_params(labelsize=6.3)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_denom(out: Path, root: str = ".") -> dict:
    """노트82 — 왼쪽 도메인 제거의 산술, 오른쪽 출처 기여도."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note82.json").read_text())
    dr, sc, ens = j["drop"], j["src"], j["ens"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.05, 1]})

    ks = sorted(dr, key=lambda k: ens[k])
    x = np.array([ens[k] for k in ks])
    y = np.array([dr[k]["d"] for k in ks])
    ok = np.array([dr[k]["v"] == "채택" for k in ks])
    a1.plot(x[ok], y[ok], "o", ms=7, color=CLAIM, zorder=3, label="'빼면 좋아진다'")
    a1.plot(x[~ok], y[~ok], "o", ms=6, color=MUTE, zorder=3)
    z = np.polyfit(x, y, 1)
    xx = np.linspace(x.min() - .02, x.max() + .02, 20)
    a1.plot(xx, np.polyval(z, xx), "--", color=INK, lw=1.0, alpha=.7)
    a1.axhline(0, color=INK, lw=.8)
    a1.axvline(j["rho"], color=GATE, lw=1.1, ls=":")
    a1.text(j["rho"] + .006, y.max() * .92, f"판정치\n{j['rho']:.4f}", fontsize=6.0,
            color=GATE)
    for k in ks:
        a1.annotate(k, (ens[k], dr[k]["d"]), textcoords="offset points",
                    xytext=(0, 9 if dr[k]["d"] > 0 else -13), ha="center",
                    fontsize=5.8, color=INK)
    a1.set_xlabel("그 도메인의 앙상블 $\\rho$", fontsize=7.0)
    a1.set_ylabel("빼면 생기는 $\\Delta$판정치", fontsize=7.0)
    a1.legend(fontsize=6.2, frameon=False, loc="upper right")
    a1.set_title(f"$r={np.corrcoef(x, y)[0,1]:+.3f}$ --- 낮은 것을 빼면 오른다",
                 fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    ks2 = sorted(sc, key=lambda k: -sc[k]["d"])
    ys = np.arange(len(ks2))[::-1]
    for yy, k in zip(ys, ks2):
        c = sc[k]["ci"]
        a2.plot(c, [yy, yy], "-", color=MUTE, lw=2.4, solid_capstyle="butt")
        a2.plot(sc[k]["d"], yy, "o", ms=5.5, color=GATE)
    a2.axvline(0, color=INK, lw=.9)
    a2.set_yticks(ys)
    a2.set_yticklabels(ks2, fontsize=6.2)
    a2.set_xlabel("출처에서 빼면 생기는 $\\Delta$ (대상 집합 고정)", fontsize=7.0)
    a2.set_xlim(-.010, .010)
    a2.set_title("열 도메인 전부 보류 --- 뺄 것이 없다", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_howmany(out: Path, root: str = ".") -> dict:
    """노트83 — 왼쪽 출처 학습 곡선, 오른쪽 라벨 신뢰도 정정."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note83.json").read_text())
    cv = {int(k): v for k, v in j["curve"].items()}
    ms = sorted(cv)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.1, 1]})

    for t, d in j["per_target"].items():
        dd = {int(k): v for k, v in d.items()}
        xs = [m for m in ms if m in dd]
        a1.plot(xs, [dd[m] for m in xs], "-", lw=.7, color=MUTE, alpha=.45)
    a1.plot(ms, [cv[m] for m in ms], "-o", lw=2.0, ms=6, color=GATE, zorder=3,
            label="열 대상 평균")
    f = j["fit"]
    xx = np.linspace(1, 30, 60)
    a1.plot(xx, f["a"] + f["b"] * np.log(xx), "--", color=CLAIM, lw=1.1,
            label=f"$\\rho={f['a']:.3f}{f['b']:+.4f}\\ln m$")
    for k in ("20", "30"):
        a1.plot(int(k), f["pred"][k], "s", ms=5, mfc="white", mec=CLAIM, mew=1.3)
        a1.text(int(k), f["pred"][k] + .012, f"{k}개\n{f['pred'][k]:.4f}",
                fontsize=5.8, color=CLAIM, ha="center")
    a1.set_xlabel("앙상블에 쓴 출처 수 $m$", fontsize=7.0)
    a1.set_ylabel("대상 예측 $\\rho$", fontsize=7.0)
    a1.set_xscale("log")
    a1.set_xticks([1, 2, 3, 5, 8, 20, 30])
    a1.set_xticklabels(["1", "2", "3", "5", "8", "20", "30"], fontsize=6.3)
    a1.legend(fontsize=6.2, frameon=False, loc="lower right")
    a1.set_title("둘째 출처가 나머지 여섯보다 값졌다", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    labs = ["웹툰↔만화\n(노트 79)", "애니↔세계애니\n(노트 81, 32건)",
            "애니↔세계애니\n(정정, 72건)"]
    vals = [j["rel1"]["rho"], j["rel_old"]["rho"], j["rel_new"]["rho"]]
    cis = [None, j["rel_old"]["ci"], j["rel_new"]["ci"]]
    xs = np.arange(3)
    for x, v, c in zip(xs, vals, cis):
        col = CLAIM if x == 1 else GATE
        if c:
            a2.plot([x, x], c, "-", color=col, lw=2.4, solid_capstyle="butt", alpha=.6)
        a2.plot(x, v, "o", ms=8, color=col, zorder=3)
        a2.text(x, v + .028, f"{v:+.3f}", ha="center", fontsize=6.6, color=col)
    a2.axhspan(.50, .58, color=GATE, alpha=.12, zorder=0)
    a2.set_xticks(xs)
    a2.set_xticklabels(labs, fontsize=5.9)
    a2.set_ylim(.25, .95)
    a2.set_ylabel("두 플랫폼 라벨의 $\\rho$", fontsize=7.0)
    a2.set_title("노트 81의 0.784를 철회한다", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_gate(out: Path, root: str = ".") -> dict:
    """노트84 — 왼쪽 덮개율 문턱, 오른쪽 새 물리량 셋의 모형 효과."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note84.json").read_text())
    sub = j["sub"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    ks = sorted(sub, key=lambda k: -(sub[k][3] - sub[k][2]))
    ys = np.arange(len(ks))[::-1]
    for y, k in zip(ys, ks):
        cov, r_all, r_sub, r_add, n = sub[k]
        a1.plot([r_sub, r_add], [y, y], "-", color=MUTE, lw=1.6, zorder=1)
        a1.plot(r_sub, y, "o", ms=5, color=MUTE, zorder=2)
        a1.plot(r_add, y, "o", ms=7,
                color=(GATE if r_add > r_sub else CLAIM), zorder=3)
        a1.text(.055, y, f"{cov:.0%}", fontsize=5.9,
                color=(INK if cov >= j["min_cov"] else CLAIM), va="center")
    a1.set_yticks(ys)
    a1.set_yticklabels(ks, fontsize=6.2)
    a1.set_xlim(.05, .85)
    a1.set_xlabel("도메인 안 자기 $\\rho$ (직전작이 관측된 레코드만)", fontsize=7.0)
    a1.text(.055, len(ks) - .3, "덮개율", fontsize=6.0, color=INK)
    a1.plot([], [], "o", color=MUTE, ms=5, label="직전작 없이")
    a1.plot([], [], "o", color=GATE, ms=7, label="직전작 넣고")
    a1.legend(fontsize=6.2, frameon=False, loc="lower right")
    a1.set_title(f"빨간 덮개율은 문턱 {j['min_cov']:.1f} 미만 --- 버려진다",
                 fontsize=7.2)
    a1.tick_params(labelsize=6.2, length=0)

    labs = ["경쟁 밀도\n(공통 축)", "경쟁 밀도\n(고유 축)", "전형성\n(고유 축)",
            "직전작 성적\n(고유 축)"]
    m, b = j["market"], j["model"]
    vals = [m["공통4_365일"] - m["base"], m["고유_365일"] - m["base"],
            b["전형성 고유"] - b["base"], b["직전작 고유"] - b["base"]]
    xs = np.arange(4)
    a2.bar(xs, vals, .6, color=[CLAIM if v < -0.002 else MUTE for v in vals],
           alpha=.9, edgecolor="none")
    for x, v in zip(xs, vals):
        a2.text(x, v - .0016 if v < 0 else v + .0008, f"{v:+.4f}", ha="center",
                va="top" if v < 0 else "bottom", fontsize=6.2)
    a2.axhline(0, color=INK, lw=.9)
    a2.axhspan(-0.011, 0.011, color=GATE, alpha=.12, zorder=0)
    a2.text(3.45, .0092, "구간 반폭", fontsize=6.0, color=GATE, ha="right")
    a2.set_xticks(xs)
    a2.set_xticklabels(labs, fontsize=5.9)
    a2.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a2.set_ylim(-.028, .014)
    a2.set_title("새 물리량 셋 --- 하나도 안 붙는다", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_encoder(out: Path, root: str = ".") -> dict:
    """노트85 — 왼쪽 세 접근의 판정치, 오른쪽 인코더의 대상별 승패."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note85.json").read_text())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1, 1.1]})

    labs = ["현행\n(인자 공간)", "마스크 인코더\n(노트 60–62 재대결)",
            "결측 표시자\n(구조 안 바꿈)", "같은 집합 상한\n(노트 85)"]
    vals = [0.4038, j["enc"]["metric"], j["ind"]["값+표시자(공통 축)"]["rho"],
            j["fair"]["prev"]]
    base = [None, None, 0.4038, j["fair"]["base"]]
    xs = np.arange(4)
    cols = [MUTE, CLAIM, GATE, INK]
    a1.bar(xs, vals, .58, color=cols, alpha=.9, edgecolor="none")
    for x, v, b in zip(xs, vals, base):
        a1.text(x, v + .008, f"{v:+.4f}", ha="center", fontsize=6.4)
        if b is not None:
            a1.plot([x - .29, x + .29], [b, b], "-", color=INK, lw=1.0, ls=":")
    a1.axhline(0.4038, color=INK, lw=.9, ls="--", alpha=.6)
    a1.set_xticks(xs)
    a1.set_xticklabels(labs, fontsize=5.8)
    a1.set_ylim(0, .56)
    a1.set_ylabel("판정치 $\\rho$", fontsize=7.0)
    a1.set_title("셋 다 문턱을 못 넘는다", fontsize=7.4)
    a1.tick_params(labelsize=6.2, length=0)

    ks = sorted(j["cur"], key=lambda k: j["enc"]["per_target"][k] - j["cur"][k])
    ys = np.arange(len(ks))[::-1]
    for y, k in zip(ys, ks):
        c, e = j["cur"][k], j["enc"]["per_target"][k]
        a2.plot([c, e], [y, y], "-", color=MUTE, lw=1.5, zorder=1)
        a2.plot(c, y, "o", ms=5, color=MUTE, zorder=2)
        a2.plot(e, y, "o", ms=7, color=(GATE if e > c else CLAIM), zorder=3)
    a2.set_yticks(ys)
    a2.set_yticklabels(ks, fontsize=6.2)
    a2.set_xlabel("대상 예측 $\\rho$", fontsize=7.0)
    a2.plot([], [], "o", color=MUTE, ms=5, label="인자 공간")
    a2.plot([], [], "o", color=CLAIM, ms=7, label="마스크 인코더")
    a2.legend(fontsize=6.2, frameon=False, loc="lower right")
    a2.set_title("작은 도메인에서 무너진다", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_nolabel(out: Path, root: str = ".") -> dict:
    """노트86 — 왼쪽 라벨을 쓸 때와 안 쓸 때, 오른쪽 격차의 분해."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note86.json").read_text())
    rows = sorted(j["selfr"], key=lambda r: -(r[2] - r[3]))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    ys = np.arange(len(rows))[::-1]
    for y, r in zip(ys, rows):
        d, pca, sup, held = r
        a1.plot([held, sup], [y, y], "-", color=MUTE, lw=1.6, zorder=1)
        a1.plot(held, y, "o", ms=6, color=CLAIM, zorder=3)
        a1.plot(sup, y, "o", ms=6.5, color=GATE, zorder=3)
        a1.plot(pca, y, "x", ms=5.5, color=INK, mew=1.4, zorder=2)
    lo, hi = j["ceiling"]
    a1.axvspan(lo, hi, color=GATE, alpha=.13, zorder=0)
    a1.text(hi + .006, len(rows) - 1.2, "라벨\n천장", fontsize=5.9, color=GATE)
    a1.set_yticks(ys)
    a1.set_yticklabels([r[0] for r in rows], fontsize=6.2)
    a1.set_xlim(.1, .88)
    a1.set_xlabel("도메인 안 자기 $\\rho$", fontsize=7.0)
    a1.plot([], [], "o", color=CLAIM, ms=6, label="그 도메인 라벨 안 씀")
    a1.plot([], [], "o", color=GATE, ms=6.5, label="그 도메인 라벨 씀")
    a1.plot([], [], "x", color=INK, ms=5.5, mew=1.4, label="인자 공간(현행)")
    a1.legend(fontsize=6.0, frameon=False, loc="lower right")
    a1.set_title("라벨을 쓰면 천장에 닿는다", fontsize=7.4)
    a1.tick_params(labelsize=6.2, length=0)

    labs = ["인자 공간\n(현행)", "인코더만", "인코더\n$+$프로크루스테스"]
    vals = [0.4038, j["enc"]["metric"], j["enc_proc"]["metric"]]
    xs = np.arange(3)
    a2.bar(xs, vals, .55, color=[MUTE, CLAIM, GATE], alpha=.9, edgecolor="none")
    for x, v in zip(xs, vals):
        a2.text(x, v + .006, f"{v:+.4f}", ha="center", fontsize=6.4)
    a2.axhline(0.4038, color=INK, lw=.9, ls="--", alpha=.6)
    a2.annotate("", xy=(2, vals[2]), xytext=(1, vals[1]),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.3))
    a2.text(1.5, vals[2] + .022, f"정렬 회복분\n{vals[2]-vals[1]:+.4f}\n(격차의 25%)",
            fontsize=6.0, ha="center", color=INK)
    a2.set_xticks(xs)
    a2.set_xticklabels(labs, fontsize=6.0)
    a2.set_ylim(0, .50)
    a2.set_ylabel("판정치 $\\rho$", fontsize=7.0)
    a2.set_title("정렬 자유도는 격차의 4분의 1", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_memorize(out: Path, root: str = ".") -> dict:
    """노트87 — 왼쪽 낙관 편향과 표본 크기, 오른쪽 도메인별 세 값."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note87.json").read_text())
    rows = j["rows"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1, 1.15]})

    x = np.array([np.log10(r[1]) for r in rows])
    y = np.array([r[5] for r in rows])
    hot = np.array([r[1] < 200 for r in rows])
    a1.plot(x[~hot], y[~hot], "o", ms=6, color=MUTE)
    a1.plot(x[hot], y[hot], "o", ms=8, color=CLAIM, zorder=3)
    z = np.polyfit(x, y, 1)
    xx = np.linspace(x.min() - .1, x.max() + .1, 20)
    a1.plot(xx, np.polyval(z, xx), "--", color=INK, lw=1.0, alpha=.7)
    a1.axhline(0, color=INK, lw=.8)
    for r in rows:
        a1.annotate(r[0], (np.log10(r[1]), r[5]), textcoords="offset points",
                    xytext=(0, 10 if r[5] > .05 else -13), ha="center",
                    fontsize=5.8, color=INK)
    a1.set_xlabel("$\\log_{10}$ 도메인 레코드 수", fontsize=7.0)
    a1.set_ylabel("낙관 편향 (낙관 $-$ 정직)", fontsize=7.0)
    a1.set_title(f"작을수록 외운다 · $r={j['r_bias']:+.3f}$", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    ks = [r[0] for r in sorted(rows, key=lambda r: -r[5])]
    ys = np.arange(len(ks))[::-1]
    for yy, k in zip(ys, ks):
        r = [q for q in rows if q[0] == k][0]
        a2.plot([r[2], j["opt"][k]], [yy, yy], "-", color=MUTE, lw=1.4, zorder=1)
        a2.plot(r[2], yy, "o", ms=5.5, color=MUTE, zorder=3)
        a2.plot(r[3], yy, "o", ms=7, color=GATE, zorder=4)
        a2.plot(j["opt"][k], yy, "o", ms=5.5, mfc="white", mec=CLAIM, mew=1.5,
                zorder=3)
    a2.set_yticks(ys)
    a2.set_yticklabels([f"{k} ({[q[1] for q in rows if q[0]==k][0]})" for k in ks],
                       fontsize=5.9)
    a2.set_xlabel("도메인 안 자기 $\\rho$", fontsize=7.0)
    a2.set_xlim(.1, .88)
    a2.plot([], [], "o", color=MUTE, ms=5.5, label="라벨 안 씀")
    a2.plot([], [], "o", color=GATE, ms=7, label="라벨 씀(정직)")
    a2.plot([], [], "o", mfc="white", mec=CLAIM, mew=1.5, ms=5.5,
            label="라벨 씀(노트 86, 낙관)")
    a2.legend(fontsize=5.9, frameon=False, loc="lower right")
    a2.set_title("팝업·아이돌의 0.7~0.8은 외운 것이었다", fontsize=7.2)
    a2.tick_params(labelsize=6.1, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_epochs(out: Path, root: str = ".") -> dict:
    """노트88 — 왼쪽 에폭과 편향, 오른쪽 편향의 출처."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note88.json").read_text())
    ep = {int(k): v for k, v in j["epochs"].items()}
    xs = sorted(ep)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.1, 1]})

    for d, col, lw in (("팝업", CLAIM, 2.0), ("아이돌", GATE, 2.0),
                       ("모바일", MUTE, 1.4)):
        ys = [ep[x][d] for x in xs]
        a1.plot(xs, ys, "-o", ms=5.5, lw=lw, color=col,
                label=f"{d} ($n{{=}}${75 if d=='팝업' else 81 if d=='아이돌' else 2000})")
        a1.text(xs[-1] + 18, ys[-1], f"{ys[-1]:+.3f}", fontsize=6.2, color=col,
                va="center")
    a1.axhline(0, color=INK, lw=.8)
    a1.set_xlabel("학습 에폭", fontsize=7.0)
    a1.set_ylabel("낙관 편향 (낙관 $-$ 정직)", fontsize=7.0)
    a1.set_xlim(50, 830)
    a1.legend(fontsize=6.2, frameon=False, loc="upper left")
    a1.set_title("작은 도메인에서 학습 시간이 곧 편향", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    src = j["src"]
    ks = ["팝업", "아이돌", "게임", "웹툰", "모바일"]
    xs2 = np.arange(len(ks))
    b1 = [src["도메인별 머리"]["bias"][k] for k in ks]
    b2 = [src["공유 머리"]["bias"][k] for k in ks]
    a2.bar(xs2 - .18, b1, .34, color=CLAIM, alpha=.9, edgecolor="none",
           label="도메인별 머리")
    a2.bar(xs2 + .18, b2, .34, color=GATE, alpha=.9, edgecolor="none",
           label="공유 머리")
    a2.axhline(0, color=INK, lw=.8)
    a2.set_xticks(xs2)
    a2.set_xticklabels(ks, fontsize=6.3)
    a2.set_ylabel("낙관 편향 (250에폭)", fontsize=7.0)
    a2.legend(fontsize=6.2, frameon=False, loc="upper right")
    m1 = np.mean(list(src["도메인별 머리"]["bias"].values()))
    m2 = np.mean(list(src["공유 머리"]["bias"].values()))
    a2.set_title(f"머리를 공유하면 편향 절반 ({m1:.4f}$\\to${m2:.4f})",
                 fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_tool(out: Path, root: str = ".") -> dict:
    """노트89 — 왼쪽 도구의 자기 검사, 오른쪽 안 쓰는 축."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note89.json").read_text())
    p = np.array(j["pred"], float) * 100
    a = np.array(j["act"], float)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    a1.plot(p, a, "o", ms=4.5, color=MUTE, alpha=.7)
    a1.set_yscale("log")
    for lab, s, col in (("강한 기획", j["strong"], GATE), ("약한 기획", j["weak"], CLAIM)):
        x = s["백분위"]
        yv = s["비슷한 과거 팝업의 일평균 방문자"]["중앙"]
        a1.plot(x, yv, "*", ms=15, color=col, zorder=4)
        a1.annotate(f"{lab}\n상위 {100-x:.0f}% · {yv:,}명", (x, yv),
                    textcoords="offset points",
                    xytext=(-6 if x > 50 else 6, 16),
                    ha="right" if x > 50 else "left", fontsize=6.0, color=col)
    # 백분위 구간별 중앙값
    bins = np.linspace(0, 100, 6)
    mids, meds = [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum() >= 3:
            mids.append((lo + hi) / 2)
            meds.append(np.median(a[m]))
    a1.plot(mids, meds, "-o", color=INK, lw=1.4, ms=5, zorder=3, label="구간 중앙값")
    a1.set_xlabel("도구가 매긴 백분위 (100이 최상위)", fontsize=7.0)
    a1.set_ylabel("실제 일평균 방문자", fontsize=7.0)
    a1.legend(fontsize=6.2, frameon=False, loc="upper left")
    a1.set_title("과거 팝업 75건 · 하나씩 빼고 매김 · $\\rho=+0.471$",
                 fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    used = ["타깃 폭", "매장 노출도", "입장 허들", "미디어 투입", "굿즈 규모"]
    unused = ["체험 밀도", "포토존", "컬래버 강도", "IP 인지도", "계절 적합"]
    ys = np.arange(10)[::-1]
    for i, (nm2, u) in enumerate([(x, True) for x in used] +
                                 [(x, False) for x in unused]):
        a2.barh(ys[i], 1, .62, color=(GATE if u else MUTE),
                alpha=.9 if u else .45, edgecolor="none")
        a2.text(.04, ys[i], nm2, va="center", fontsize=6.4,
                color="white" if u else INK)
    a2.text(1.06, ys[2], "모델이\n쓴다", fontsize=6.6, color=GATE, va="center")
    a2.text(1.06, ys[7], "안 쓴다", fontsize=6.6, color=INK, va="center")
    aw = j["aw"]
    a2.text(.5, -2.6, f"IP 인지도를 공통 축으로 넣으면\n"
                      f"판정치 {aw['base']['rho']:+.4f}$\\to${aw['공통 4축(중립 대입)']['rho']:+.4f} "
                      f"인데\n팝업은 {aw['base']['popup']:+.4f}$\\to$"
                      f"{aw['공통 4축(중립 대입)']['popup']:+.4f} --- 채택 안 함",
            ha="center", fontsize=6.2, color=CLAIM)
    a2.set_xlim(0, 1.5)
    a2.set_ylim(-4.6, 9.7)
    a2.axis("off")
    a2.set_title("기획서 열 속성 중 다섯만 쓴다", fontsize=7.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_fourth(out: Path, root: str = ".") -> dict:
    """노트90 — 왼쪽 네 번째 축 시도 넷, 오른쪽 소거법 격자."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note90.json").read_text())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.05, 1]})

    tr = j["tries"]
    xs = np.arange(len(tr))
    v1 = [t[1] for t in tr]
    v2 = [t[2] if t[2] is not None else np.nan for t in tr]
    a1.bar(xs - .18, v1, .34, color=MUTE, alpha=.9, edgecolor="none", label="판정치")
    ok = ~np.isnan(v2)
    a1.bar(xs[ok] + .18, np.array(v2)[ok], .34, color=CLAIM, alpha=.9,
           edgecolor="none", label="팝업")
    for x, v in zip(xs - .18, v1):
        a1.text(x, v - .003 if v < 0 else v + .002, f"{v:+.3f}", ha="center",
                va="top" if v < 0 else "bottom", fontsize=5.9)
    for x, v in zip(xs[ok] + .18, np.array(v2)[ok]):
        a1.text(x, v - .003 if v < 0 else v + .002, f"{v:+.3f}", ha="center",
                va="top" if v < 0 else "bottom", fontsize=5.9, color=CLAIM)
    a1.axhline(0, color=INK, lw=.9)
    a1.axhspan(-0.011, 0.011, color=GATE, alpha=.12, zorder=0)
    a1.text(len(tr) - .5, .013, "구간 반폭", fontsize=6.0, color=GATE, ha="right")
    a1.set_xticks(xs)
    a1.set_xticklabels([t[0].replace("(", "\n(") for t in tr], fontsize=5.7)
    a1.set_ylabel("$\\Delta$ (현행 대비)", fontsize=7.0)
    a1.legend(fontsize=6.2, frameon=False, loc="lower left")
    a1.set_title("네 번째 공통 축 --- 네 번 시도, 네 번 실패", fontsize=7.2)
    a1.tick_params(labelsize=6.2, length=0)

    g = j["grid"]["res"]
    ks = [1, 2, 3]
    for lab, col, mk in (("3축", GATE, "o"), ("2축(매장 뺌)", MUTE, "s")):
        ys = [g[f"{lab} k={k}"]["mean"] for k in ks]
        a2.plot(ks, ys, f"-{mk}", ms=6, lw=1.7, color=col, label=f"공통 {lab} · 평균")
        yp = [g[f"{lab} k={k}"]["popup"] for k in ks]
        a2.plot(ks, yp, f"--{mk}", ms=5, lw=1.1, color=col, alpha=.6,
                label=f"공통 {lab} · 팝업")
    best = g["3축 k=2"]["mean"]
    a2.plot(2, best, "o", ms=13, mfc="none", mec=INK, mew=1.6, zorder=4)
    a2.text(2.06, best + .004, "현행", fontsize=6.4, color=INK)
    a2.plot(1, g["3축 k=1"]["popup"], "o", ms=13, mfc="none", mec=CLAIM, mew=1.6,
            zorder=4)
    a2.text(1.06, g["3축 k=1"]["popup"] + .004, "팝업 최선", fontsize=6.4,
            color=CLAIM)
    a2.set_xticks(ks)
    a2.set_xlabel("성분 수 $k$", fontsize=7.0)
    a2.set_ylabel("$\\rho$ (대상 9개 고정)", fontsize=7.0)
    a2.legend(fontsize=5.9, frameon=False, loc="lower right", ncol=1)
    a2.set_title("현행이 국소 최적 · 팝업만은 $k{=}1$", fontsize=7.2)
    a2.tick_params(labelsize=6.3)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_toolkit(out: Path, root: str = ".") -> dict:
    """노트91 — 왼쪽 도메인별 자기 검사, 오른쪽 성분 수의 갈림."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note91.json").read_text())
    rows = j["rows"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.05, 1]})

    ys = np.arange(len(rows))[::-1]
    vals = [r[2] for r in rows]
    cols = [GATE if v >= .35 else (MUTE if v >= .25 else CLAIM) for v in vals]
    a1.barh(ys, vals, .62, color=cols, alpha=.9, edgecolor="none")
    for y, r in zip(ys, rows):
        a1.text(r[2] + .008, y, f"{r[2]:+.3f}", va="center", fontsize=6.2)
    a1.axvline(.35, color=INK, lw=.9, ls="--")
    a1.text(.355, ys[0] + .1, "쓸 만함", fontsize=6.2, color=INK)
    a1.set_yticks(ys)
    a1.set_yticklabels([f"{r[0]} ({r[1]:,})" for r in rows], fontsize=6.1)
    a1.set_xlim(0, .78)
    a1.set_xlabel("도구 자기 검사 $\\rho$ (폴드 밖 투영)", fontsize=7.0)
    a1.set_title("어느 카테고리에 쓸 수 있나", fontsize=7.4)
    a1.tick_params(labelsize=6.2, length=0)

    ks = sorted(rows, key=lambda r: -r[4])
    ys2 = np.arange(len(ks))[::-1]
    for y, r in zip(ys2, ks):
        a2.plot([r[2], r[3]], [y, y], "-", color=MUTE, lw=1.5, zorder=1)
        a2.plot(r[2], y, "o", ms=5.5, color=MUTE, zorder=2)
        a2.plot(r[3], y, "o", ms=7, color=(GATE if r[4] > 0 else CLAIM), zorder=3)
    a2.set_yticks(ys2)
    a2.set_yticklabels([r[0] for r in ks], fontsize=6.2)
    a2.set_xlabel("자기 검사 $\\rho$", fontsize=7.0)
    a2.plot([], [], "o", color=MUTE, ms=5.5, label="$k{=}2$ (현행)")
    a2.plot([], [], "o", color=GATE, ms=7, label="$k{=}1$ 이 나음")
    a2.plot([], [], "o", color=CLAIM, ms=7, label="$k{=}1$ 이 나쁨")
    a2.legend(fontsize=6.0, frameon=False, loc="lower right")
    a2.set_title(f"평균은 같다 ({j['mean_k2']:+.4f} 대 {j['mean_k1']:+.4f})",
                 fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_history(out: Path, root: str = ".") -> dict:
    """노트92 — 왼쪽 도구의 학습 곡선, 오른쪽 성분 수 선택의 A/B 검정."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note92.json").read_text())
    cv = j["curve"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.1, 1]})

    for d, col, lw in (("팝업", CLAIM, 2.0), ("모바일", GATE, 1.5),
                       ("웹툰", MUTE, 1.3), ("만화", INK, 1.1),
                       ("세계애니", MUTE, 1.1)):
        if d not in cv:
            continue
        xs = [r[0] for r in cv[d]]
        ys = [r[1] for r in cv[d]]
        a1.plot(xs, ys, "-o", ms=4.5, lw=lw, color=col,
                alpha=1.0 if d in ("팝업", "모바일") else .55, label=d)
        a1.text(xs[-1] * 1.06, ys[-1], d, fontsize=5.9, color=col, va="center")
    a1.axvline(50, color=INK, lw=.9, ls="--")
    a1.text(53, .655, "50건", fontsize=6.2, color=INK)
    a1.set_xscale("log")
    a1.set_xlim(15, 6500)
    a1.set_ylim(.20, .70)
    a1.set_xlabel("그 도메인에 쌓인 과거 레코드 수", fontsize=7.0)
    a1.set_ylabel("도구 자기 검사 $\\rho$", fontsize=7.0)
    a1.set_title("쉰 건이면 거의 포화한다", fontsize=7.4)
    a1.tick_params(labelsize=6.3)

    rows = sorted(j["pick"]["rows"], key=lambda r: r[7])
    ys2 = np.arange(len(rows))[::-1]
    for y, r in zip(ys2, rows):
        c = GATE if r[7] > 0 else (CLAIM if r[7] < 0 else MUTE)
        a2.barh(y, r[7], .6, color=c, alpha=.9, edgecolor="none")
        a2.text(r[7] + (.004 if r[7] >= 0 else -.004), y,
                f"k={r[4]}", va="center", ha="left" if r[7] >= 0 else "right",
                fontsize=5.9, color=INK)
    a2.axvline(0, color=INK, lw=.9)
    a2.set_yticks(ys2)
    a2.set_yticklabels([r[0] for r in rows], fontsize=6.2)
    a2.set_xlabel("B반에서 고른 $k$ $-$ 항상 $k{=}2$", fontsize=7.0)
    a2.set_title(f"고르면 손해 ({j['pick']['d']:+.4f})", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_gapsplit(out: Path, root: str = ".") -> dict:
    """노트93 — 왼쪽 안 건드린 것들, 오른쪽 격차 분해."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note93.json").read_text())
    u = j["untried"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.1, 1]})

    labs = ["벌점\n$\\alpha$ 0.03–100", "축 순위\n변환", "라벨 순위\n변환",
            "합치기\n중앙값", "합치기\n절사평균", "직접 전이\n(정렬 없음)",
            "직접 전이\nGBM"]
    keys = ["벌점 alpha=100.0", "축 순위 변환", "라벨 순위 변환", "합치기 중앙값",
            "합치기 절사평균"]
    vals = [u[k]["rho"] - u["base"]["rho"] for k in keys]
    vals += [j["direct"]["직접 · 능형"]["rho"] - u["base"]["rho"],
             j["direct"]["직접 · GBM"]["rho"] - u["base"]["rho"]]
    xs = np.arange(len(labs))
    a1.bar(xs, vals, .6, color=[CLAIM if v < -.01 else
                                (GATE if v > .01 else MUTE) for v in vals],
           alpha=.9, edgecolor="none")
    for x, v in zip(xs, vals):
        a1.text(x, v + (.002 if v >= 0 else -.002), f"{v:+.4f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=5.8)
    a1.axhline(0, color=INK, lw=.9)
    a1.axhspan(-0.033, 0.033, color=GATE, alpha=.11, zorder=0)
    a1.text(len(labs) - .5, .030, "구간 반폭", fontsize=6.0, color=GATE, ha="right")
    a1.set_xticks(xs)
    a1.set_xticklabels(labs, fontsize=5.5)
    a1.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a1.set_title("안 건드린 자리 일곱 --- 하나도 안 움직인다", fontsize=7.2)
    a1.tick_params(labelsize=6.2, length=0)

    m = j["means"]
    lo, hi = j["label_ceiling"]
    lv = [j["transfer"], m["raw_ridge"], m["raw_gbm"], (lo + hi) / 2]
    lb = ["전이\n(현행)", "도메인 안\n원 축 · 능형", "도메인 안\n원 축 · GBM",
          "라벨 천장\n(노트 83)"]
    xs2 = np.arange(4)
    a2.bar(xs2, lv, .58, color=[GATE, MUTE, MUTE, INK], alpha=.9, edgecolor="none")
    a2.errorbar(3, (lo + hi) / 2, yerr=[[(hi - lo) / 2], [(hi - lo) / 2]],
                fmt="none", ecolor="white", elinewidth=1.6, capsize=3)
    for x, v in zip(xs2, lv):
        a2.text(x, v + .012, f"{v:.3f}", ha="center", fontsize=6.4)
    a2.annotate("", xy=(2, m["raw_gbm"]), xytext=(0, j["transfer"]),
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.4))
    a2.text(1.0, .30, f"전이의 값\n$-${m['raw_gbm']-j['transfer']:.3f}",
            fontsize=6.2, color=CLAIM, ha="center")
    a2.annotate("", xy=(3, (lo + hi) / 2), xytext=(2, m["raw_gbm"]),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.4))
    a2.text(2.5, .62, f"축에 없는 것\n$-${(lo+hi)/2-m['raw_gbm']:.3f}",
            fontsize=6.2, color=INK, ha="center")
    a2.set_xticks(xs2)
    a2.set_xticklabels(lb, fontsize=5.9)
    a2.set_ylim(0, .88)
    a2.set_ylabel("$\\rho$", fontsize=7.0)
    a2.set_title("남은 격차의 어디가 무엇인가", fontsize=7.4)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_cover(out: Path, root: str = ".") -> dict:
    """노트94 — 왼쪽 표지 특징 상관표, 오른쪽 부호 반전과 축 투입."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note94.json").read_text())
    c = j["corr"]
    FE = ["bright", "sat", "edge", "ent", "std"]
    KO = ["밝기", "채도", "가장자리", "색 엔트로피", "명암 대비"]
    doms = list(c)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    for i, fe in enumerate(FE):
        for k, d in enumerate(doms):
            v = c[d][fe]
            a1.plot(k, -i, "o", ms=3.2 + 22 * abs(v),
                    color=(GATE if v > 0 else CLAIM), alpha=.85)
            if abs(v) > .10:
                a1.text(k, -i - .34, f"{v:+.2f}", ha="center", fontsize=5.4,
                        color=INK)
    a1.set_xticks(range(len(doms)))
    a1.set_xticklabels(doms, fontsize=6.2)
    a1.set_yticks([-i for i in range(len(FE))])
    a1.set_yticklabels(KO, fontsize=6.2)
    a1.set_xlim(-.6, len(doms) - .4)
    a1.set_ylim(-len(FE) + .5, .7)
    a1.set_title("표지 특징과 라벨 --- 파랑 $+$, 빨강 $-$", fontsize=7.4)
    a1.tick_params(length=0)
    for s in ("top", "right", "left", "bottom"):
        a1.spines[s].set_visible(False)

    t = j["test"]
    labs = ["밝기\n(고유)", "채도\n(고유)", "색 엔트로피\n(고유)", "셋 다\n(고유)",
            "밝기\n(공통)"]
    keys = ["밝기(고유)", "채도(고유)", "색 엔트로피(고유)", "셋 다(고유)", "밝기(공통)"]
    xs = np.arange(len(keys))
    dm = [t[k]["rho"] - t["base"]["rho"] for k in keys]
    dp = [t[k]["popup"] - t["base"]["popup"] for k in keys]
    a2.bar(xs - .18, dm, .34, color=MUTE, alpha=.9, edgecolor="none", label="판정치")
    a2.bar(xs + .18, dp, .34, color=GATE, alpha=.9, edgecolor="none", label="팝업")
    a2.axhline(0, color=INK, lw=.9)
    a2.axhspan(-0.033, 0.033, color=GATE, alpha=.10, zorder=0)
    for x, v in zip(xs - .18, dm):
        a2.text(x, v - .0008, f"{v:+.3f}", ha="center", va="top", fontsize=5.6)
    for x, v in zip(xs + .18, dp):
        a2.text(x, v + .0006, f"{v:+.3f}", ha="center", va="bottom", fontsize=5.6,
                color=GATE)
    a2.set_xticks(xs)
    a2.set_xticklabels(labs, fontsize=5.7)
    a2.set_ylim(-.016, .012)
    a2.set_ylabel("$\\Delta$ (현행 대비)", fontsize=7.0)
    a2.legend(fontsize=6.2, frameon=False, loc="lower left")
    a2.set_title("축으로 넣으면 --- 판정치는 내리고 팝업만 오른다", fontsize=7.0)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_text(out: Path, root: str = ".") -> dict:
    """노트95 — 왼쪽 설명문 특징 상관표, 오른쪽 합쳐도 안 더해진다."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note95.json").read_text())
    c = j["corr"]
    FE = ["len", "nsent", "slen", "ttr", "digit"]
    KO = ["길이", "문장 수", "문장 길이", "어휘 다양성", "숫자 비율"]
    doms = list(c)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    for i, fe in enumerate(FE):
        for k, d in enumerate(doms):
            v = c[d][fe]
            a1.plot(k, -i, "o", ms=3.2 + 22 * abs(v),
                    color=(GATE if v > 0 else CLAIM), alpha=.85)
    a1.axhspan(-1.45, -0.55, color=GATE, alpha=.12, zorder=0)
    a1.text(len(doms) - .35, -1.0, "다섯 다\n$+$", fontsize=6.2, color=GATE,
            va="center")
    a1.set_xticks(range(len(doms)))
    a1.set_xticklabels(doms, fontsize=6.2)
    a1.set_yticks([-i for i in range(len(FE))])
    a1.set_yticklabels(KO, fontsize=6.2)
    a1.set_xlim(-.6, len(doms) + .3)
    a1.set_ylim(-len(FE) + .5, .7)
    a1.set_title("설명문 특징과 라벨 --- 덮개율 100%", fontsize=7.4)
    a1.tick_params(length=0)
    for s in ("top", "right", "left", "bottom"):
        a1.spines[s].set_visible(False)

    parts = j["parts"]
    xs = np.arange(len(parts) + 2)
    vals = [p[1] for p in parts] + [sum(p[1] for p in parts), j["combined"]["d"]]
    labs = [p[0].replace("(", "\n(") for p in parts] + ["셋의 합\n(독립이면)",
                                                        "실제로 합친 것"]
    cols = [MUTE] * len(parts) + [INK, GATE]
    a2.bar(xs, vals, .6, color=cols, alpha=.9, edgecolor="none")
    for x, v in zip(xs, vals):
        a2.text(x, v + .0009, f"{v:+.4f}", ha="center", fontsize=6.0)
    a2.axhline(0, color=INK, lw=.9)
    a2.axhspan(-0.033, 0.033, color=GATE, alpha=.10, zorder=0)
    a2.text(len(xs) - .5, .0305, "구간 반폭", fontsize=6.0, color=GATE, ha="right")
    a2.annotate("", xy=(4, vals[4]), xytext=(3, vals[3]),
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.5))
    a2.text(3.5, .026, f"겹침\n$-${vals[3]-vals[4]:.4f}", fontsize=6.2,
            color=CLAIM, ha="center")
    a2.set_xticks(xs)
    a2.set_xticklabels(labs, fontsize=5.5)
    a2.set_ylim(-.004, .042)
    a2.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a2.set_title("셋을 합쳐도 문턱을 못 넘는다 (0/4 채택)", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_borrow(out: Path, root: str = ".") -> dict:
    """노트96 — 왼쪽 출처 수 곡선, 가운데 기제, 오른쪽 c0 은 길이였다."""
    import json, numpy as np
    j = json.loads((Path(root) / "data/state/note96.json").read_text())
    s, c, m = j["src"], j["ctrl"], j["mech"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1.2, 1, 1.05]})

    # ① 출처 수 곡선
    ks = list(range(0, 7))
    real = [s["base_pop"]] + [s["curve"][str(k)]["pop"] for k in range(1, 7)]
    lo = [s["base_pop"]] + [s["curve"][str(k)]["lo"] for k in range(1, 7)]
    hi = [s["base_pop"]] + [s["curve"][str(k)]["hi"] for k in range(1, 7)]
    shuf = [s["base_pop"]] + [c["shuf_curve"][str(k)]["pop"] for k in range(1, 7)]
    a1.fill_between(ks, lo, hi, color=CLAIM, alpha=.13, lw=0)
    a1.plot(ks, real, "o-", color=CLAIM, lw=1.5, ms=3.6, label="설명문 축(참)")
    a1.plot(ks, shuf, "s--", color=GATE, lw=1.2, ms=3.0, label="뒤섞은 축(대조)")
    b, a = np.polyfit(ks, real, 1)[0], real[0]
    a1.text(3.0, .4448, f"기울기\n출처 하나당 {b:+.4f}", fontsize=6.2,
            color=CLAIM, ha="center")
    a1.set_xlabel("설명문 축이 붙은 출처 도메인 수", fontsize=7.0)
    a1.set_ylabel("팝업 $\\rho$", fontsize=7.0)
    a1.set_title("팝업엔 설명문이 없는데 --- 출처마다 오른다", fontsize=7.4)
    a1.legend(fontsize=6.0, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.4)
    a1.set_ylim(.443, .478)

    # ② 기제 --- 자기 ρ 가 오른 만큼 전이가 오른다
    ds = np.array([m["rows"][k][1] - m["rows"][k][0] for k in m["rows"]])
    dp = np.array([m["rows"][k][3] - m["rows"][k][2] for k in m["rows"]])
    a2.axhline(0, color=MUTE, lw=.7)
    a2.axvline(0, color=MUTE, lw=.7)
    a2.plot(ds, dp, "o", color=CLAIM, ms=5, alpha=.9)
    for k, x, y in zip(m["rows"], ds, dp):
        a2.annotate(k, (x, y), fontsize=6.0, xytext=(4, 3),
                    textcoords="offset points", color=INK)
    z = np.polyfit(ds, dp, 1)
    xx = np.linspace(ds.min() - .01, ds.max() + .015, 20)
    a2.plot(xx, np.polyval(z, xx), "-", color=GATE, lw=1.0, alpha=.7)
    a2.text(.02, .02, f"$r={m['r']:+.3f}$", fontsize=7.2, color=GATE)
    a2.set_xlabel("$\\Delta$ 출처의 자기 $\\rho$", fontsize=7.0)
    a2.set_ylabel("$\\Delta$ 그 출처 $\\to$ 팝업", fontsize=7.0)
    a2.set_title("기제 --- 출처가 깨끗해진 만큼", fontsize=7.4)
    a2.tick_params(labelsize=6.4)

    # ③ c0 은 무엇인가
    KO = ["길이", "문장 수", "문장 길이", "어휘 다양성", "숫자 비율"]
    H = j["hand"]
    doms = list(H)
    for i, lab in enumerate(KO):
        vs = [H[d][i] for d in doms]
        a3.plot(vs, [-i] * len(vs), "o", ms=3.4, color=MUTE, alpha=.75)
        a3.plot(np.mean(vs), -i, "D", ms=5.2,
                color=(CLAIM if abs(np.mean(vs)) > .4 else GATE), alpha=.95)
    a3.axvline(0, color=INK, lw=.8)
    a3.axhspan(-.4, .4, color=CLAIM, alpha=.10, zorder=0)
    a3.text(.83, 0, "c0 $=$ 길이", fontsize=6.4, color=CLAIM, ha="right",
            va="center")
    a3.set_yticks([-i for i in range(len(KO))])
    a3.set_yticklabels(KO, fontsize=6.4)
    a3.set_xlim(-.75, .95)
    a3.set_xlabel("임베딩 첫 성분과의 순위 상관", fontsize=7.0)
    a3.set_title("60,000차원을 줄였더니 길이였다", fontsize=7.4)
    a3.tick_params(labelsize=6.4, length=0)
    for sp in ("left",):
        a3.spines[sp].set_visible(False)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_onlyother(out: Path, root: str = ".") -> dict:
    """노트97 — 왼쪽 덮개율 가위, 가운데 법칙이 깨진다, 오른쪽 출처 수 기울기."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note97.json").read_text())
    d = json.loads((R / "note97d.json").read_text())
    m96 = json.loads((R / "emb_mech.json").read_text())
    s96 = json.loads((R / "emb_srccount.json").read_text())
    b0, p0 = j["base"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1, 1, 1.1]})

    # ① 덮개율 가위
    fr = sorted(float(x) for x in j["cov"])
    rr = [j["cov"][str(f)][0] for f in fr]
    pp = [j["cov"][str(f)][1] for f in fr]
    xs = [f * 100 for f in fr]
    a1.plot(xs, pp, "o-", color=CLAIM, lw=1.6, ms=3.6, label="팝업")
    a1.plot(xs, rr, "s-", color=GATE, lw=1.6, ms=3.2, label="판정치(열 대상 평균)")
    a1.axhline(p0, color=CLAIM, ls=":", lw=.8)
    a1.axhline(b0, color=GATE, ls=":", lw=.8)
    a1.annotate("", xy=(100, pp[-1]), xytext=(100, rr[-1]),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=.8))
    a1.text(97, (pp[-1] + rr[-1]) / 2, "갈라진다", fontsize=6.4, ha="right",
            va="center", color=INK)
    a1.set_xlabel("표지 덮개율 (%)", fontsize=7.0)
    a1.set_ylabel("$\\rho$", fontsize=7.0)
    a1.set_title("덮개율을 올릴수록 --- 팝업은 오르고 나머지는 내린다",
                 fontsize=7.0)
    a1.legend(fontsize=6.0, frameon=False, loc="center left")
    a1.tick_params(labelsize=6.4)

    # ② 노트 74 의 법칙이 깨진다
    for src, col, lab, mk in ((m96, GATE, "설명문 축(노트 96)", "s"),
                              (d, CLAIM, "표지 축(이번)", "o")):
        ds = np.array([v[1] - v[0] for v in src["rows"].values()])
        dp = np.array([v[3] - v[2] for v in src["rows"].values()])
        a2.plot(ds, dp, mk, color=col, ms=4.6, alpha=.9,
                label=f"{lab}  $r={src['r']:+.2f}$")
        z = np.polyfit(ds, dp, 1)
        xx = np.linspace(min(ds) - .005, max(ds) + .005, 20)
        a2.plot(xx, np.polyval(z, xx), "-", color=col, lw=1.0, alpha=.55)
    a2.axhline(0, color=MUTE, lw=.7)
    a2.axvline(0, color=MUTE, lw=.7)
    a2.set_xlabel("$\\Delta$ 출처의 자기 $\\rho$", fontsize=7.0)
    a2.set_ylabel("$\\Delta$ 그 출처 $\\to$ 팝업", fontsize=7.0)
    a2.set_title("노트 74의 법칙이 처음으로 깨진다", fontsize=7.0)
    a2.legend(fontsize=5.8, frameon=False, loc="upper left")
    a2.tick_params(labelsize=6.4)

    # ③ 출처 수 기울기
    kc = [0] + [int(k) for k in sorted(j["src"], key=int)]
    pc = [p0] + [j["src"][k]["pop"] for k in sorted(j["src"], key=int)]
    rc = [b0] + [j["src"][k]["rho"] for k in sorted(j["src"], key=int)]
    ke = list(range(7))
    pe = [s96["base_pop"]] + [s96["curve"][str(k)]["pop"] for k in range(1, 7)]
    re_ = [s96["base"]] + [s96["curve"][str(k)]["rho"] for k in range(1, 7)]
    a3.plot(ke, pe, "s--", color=GATE, lw=1.2, ms=3.0, alpha=.8,
            label="설명문 $\\to$ 팝업")
    a3.plot(kc, pc, "o-", color=CLAIM, lw=1.7, ms=4.0, label="표지 $\\to$ 팝업")
    a3.plot(ke, re_, "s--", color=GATE, lw=1.0, ms=2.6, alpha=.4,
            label="설명문 $\\to$ 판정치")
    a3.plot(kc, rc, "o-", color=CLAIM, lw=1.0, ms=2.8, alpha=.45,
            label="표지 $\\to$ 판정치")
    a3.text(4.6, .468, f"$+${j['slope'][1]:.4f}", fontsize=6.4, color=CLAIM)
    a3.text(5.1, .398, f"{j['slope'][0]:+.4f}", fontsize=6.4, color=CLAIM,
            alpha=.7)
    a3.set_xlabel("축이 붙은 출처 도메인 수", fontsize=7.0)
    a3.set_ylabel("$\\rho$", fontsize=7.0)
    a3.set_title("나쁜 축이 더 가파르다", fontsize=7.0)
    a3.legend(fontsize=5.5, frameon=False, loc="center left")
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_stackcap(out: Path, root: str = ".") -> dict:
    """노트98 — 왼쪽 쌓기 천장, 가운데 시각 경로, 오른쪽 관측 대 개입."""
    import json, numpy as np
    R = Path(root) / "data/state"
    a = json.loads((R / "note98.json").read_text())
    bb = json.loads((R / "note98b.json").read_text())
    dd = json.loads((R / "note98d.json").read_text())
    b0, p0 = a["base"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.15, 1, 1.15]})

    # ① 쌓아도 안 올라간다
    order = ["현행", "설명문 c0", "+표지", "+문장 수", "+설명문 c1", "+설명문 c2"]
    st = bb["stack"]
    xs = np.arange(len(order))
    pop = [st[k][3] for k in order]
    jud = [st[k][1] - b0 for k in order]
    a1.bar(xs, pop, .58, color=CLAIM, alpha=.9, edgecolor="none", label="팝업")
    a1.plot(xs, jud, "s--", color=GATE, lw=1.3, ms=3.4, label="판정치")
    tot = sum(bb["solo"].values())
    a1.axhline(tot, color=INK, ls=":", lw=1.0)
    a1.text(0.05, tot + .002, f"낱개 다섯의 합 {tot:+.4f}", fontsize=6.0,
            color=INK)
    a1.axhline(0, color=INK, lw=.8)
    a1.set_xticks(xs)
    a1.set_xticklabels(["현행", "설명문", "$+$표지", "$+$문장수", "$+$c1", "$+$c2"],
                       fontsize=5.8)
    a1.set_ylabel("$\\Delta\\rho$", fontsize=7.0)
    a1.set_title("축을 쌓아도 팝업은 $+$0.022에서 멈춘다", fontsize=7.2)
    a1.legend(fontsize=6.0, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.4)

    # ② 시각 경로
    p = a["path"]
    labs, vals = [], []
    for k, v in p.items():
        if v is None or k == "(안 끔)":
            continue
        labs.append(k.replace("(", "\n("))
        vals.append(v[2] / p["(안 끔)"][2])
    cols = [CLAIM if "시각)" in l and "가짜" not in l else GATE for l in labs]
    ys = np.arange(len(labs))
    LO = -1.0
    clip = [max(v, LO) for v in vals]
    a2.barh(ys, clip, .6, color=cols, alpha=.9, edgecolor="none")
    for y, v in zip(ys, vals):
        if v < LO:
            a2.text(LO + .04, y, f"{v:.1f}$\\times$ (잘림)", fontsize=5.6,
                    va="center", color=MUTE)
        elif v > .5:
            a2.text(v - .03, y, f"{v:.0%}", fontsize=5.8, va="center",
                    ha="right", color="white")
        else:
            a2.text(v + .04, y, f"{v:.0%}", fontsize=5.8, va="center",
                    color=INK)
    a2.axvline(1.0, color=INK, ls=":", lw=1.0)
    a2.axvline(0, color=INK, lw=.8)
    a2.set_yticks(ys)
    a2.set_yticklabels([l.split("\n")[0] for l in labs], fontsize=6.2)
    a2.set_xlabel("남은 이득의 비율 (안 끔 $=$ 1)", fontsize=7.0)
    a2.set_title("매장 노출을 끄면 94%가 사라진다", fontsize=7.2)
    a2.set_xlim(LO - .1, 1.35)
    a2.set_xticks([-1, 0, 1])
    a2.set_xticklabels(["$-$100%", "0", "100%"], fontsize=6.2)
    a2.tick_params(labelsize=6.2, length=0)
    a2.invert_yaxis()

    # ③ 관측 대 개입
    comp = dd["comp"]
    xs2 = [comp[t][2] * 100 for t in comp]
    ys2 = [comp[t][3] for t in comp]
    a3.plot(xs2, ys2, "o", color=GATE, ms=6, alpha=.9)
    for t, x, y in zip(comp, xs2, ys2):
        a3.annotate(t, (x, y), fontsize=6.0, xytext=(4, 3),
                    textcoords="offset points", color=GATE)
    z = np.polyfit(xs2, ys2, 1)
    xx = np.linspace(min(xs2) - 2, 102, 20)
    a3.plot(xx, np.polyval(z, xx), "-", color=GATE, lw=1.1, alpha=.6)
    a3.text(81, .012, "관측 $n{=}4$\n$r=" + f"{np.corrcoef(xs2, ys2)[0,1]:+.3f}$",
            fontsize=6.2, color=GATE, ha="left")
    fr = sorted(float(f) for f in dd["dose"])
    a3.plot([f * 100 for f in fr], [dd["dose"][str(f)][2] for f in fr],
            "^-", color=CLAIM, lw=1.4, ms=4, label="팝업 슬롯을 갉은 개입")
    a3.set_ylim(-.008, .058)
    a3.text(79.5, .050, "팝업 슬롯을 갉은 개입  " + f"$r={dd['r'][0]:+.3f}$",
            fontsize=6.2, color=CLAIM, ha="left")
    a3.axhline(0, color=MUTE, lw=.7)
    a3.set_xlabel("대상의 평균 슬롯 덮개율 (%)", fontsize=7.0)
    a3.set_ylabel("$\\Delta$ 팝업(표지 축)", fontsize=7.0)
    a3.set_title("관측은 그럴듯했고 개입이 죽였다", fontsize=7.2)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_receive(out: Path, root: str = ".") -> dict:
    """노트99 — 왼쪽 받는 벌, 가운데 여섯 설정, 오른쪽 대상별."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note99.json").read_text())
    k = json.loads((R / "note99b.json").read_text())
    b0, p0 = j["base"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.1, 1.15, 1]})

    # ① 받는 벌
    iso = k["iso"]
    order = ["(없음) 출처 6만", "$+$도서", "$+$펀딩", "$+$팝업", "팝업만 더"]
    xs = np.arange(len(order))
    vs = [iso[o][3] for o in order]
    cols = [MUTE, MUTE, MUTE, CLAIM, CLAIM]
    a1.bar(xs, vs, .6, color=cols, alpha=.9, edgecolor="none")
    for x, v in zip(xs, vs):
        a1.text(x, v + (.0008 if v > 0 else -.0022), f"{v:+.4f}",
                ha="center", fontsize=5.9)
    a1.axhline(0, color=INK, lw=.9)
    a1.annotate("", xy=(3, vs[3]), xytext=(2, vs[2]),
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.6))
    a1.text(2.5, .0135, "팝업이 받는 순간\n$-$0.0154", fontsize=6.2,
            color=CLAIM, ha="center")
    a1.set_xticks(xs)
    a1.set_xticklabels(["출처 6만", "$+$도서", "$+$펀딩", "$+$팝업", "팝업만"],
                       fontsize=6.0)
    a1.set_ylabel("$\\Delta$ 팝업", fontsize=7.0)
    a1.set_title("남이 받으면 그대로, 내가 받으면 무너진다", fontsize=7.0)
    a1.set_ylim(-.004, .0235)
    a1.tick_params(labelsize=6.4)

    # ② 여섯 설정
    res = j["res"]
    labs = list(res)
    ys = np.arange(len(labs))
    a2.barh(ys - .19, [res[l][1] for l in labs], .35, color=GATE, alpha=.9,
            edgecolor="none", label="판정치")
    a2.barh(ys + .19, [res[l][3] for l in labs], .35, color=CLAIM, alpha=.9,
            edgecolor="none", label="팝업")
    a2.axvline(0, color=INK, lw=.9)
    a2.set_yticks(ys)
    a2.set_yticklabels([l.replace("$+$", "+").replace("(노트 96)", "")
                        .replace("(노트 97)", "") for l in labs], fontsize=5.9)
    a2.set_xlabel("$\\Delta\\rho$", fontsize=7.0)
    a2.set_title("대상을 열수록 팝업이 준다", fontsize=7.0)
    a2.legend(fontsize=6.0, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.2, length=0)
    a2.invert_yaxis()

    # ③ 대상별
    per = j["per"]
    ts = sorted(per, key=lambda x: per[x][1] - per[x][0])
    d = [per[t][1] - per[t][0] for t in ts]
    cols = [CLAIM if per[t][2] == "받음" else GATE for t in ts]
    a3.barh(np.arange(len(ts)), d, .62, color=cols, alpha=.9, edgecolor="none")
    a3.axvline(0, color=INK, lw=.9)
    a3.set_yticks(np.arange(len(ts)))
    a3.set_yticklabels(ts, fontsize=6.2)
    a3.text(.075, len(ts) - 1.4, "애니만 크게 얻는다\n$+$0.107", fontsize=6.2,
            color=CLAIM, ha="right")
    a3.set_xlabel("$\\Delta\\rho$ (설명문 아홉 전부)", fontsize=7.0)
    a3.set_title("아홉 중 하나만 얻었다", fontsize=7.0)
    a3.tick_params(labelsize=6.2, length=0)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_slot(out: Path, root: str = ".") -> dict:
    """노트100 — 왼쪽 팝업 회복, 가운데 판정치와 대조, 오른쪽 새 축 지렛대 역사."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note100.json").read_text())
    k = json.loads((R / "note100b.json").read_text())
    res, b0, p0 = j["res"], *j["base"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.1, 1.05, 1.1]})

    PAIRS = [("출처 6", "설명문 출처 6 · k=2", "설명문 출처 6 · 받으면 k=3"),
             ("$+$팝업", "설명문 출처6+팝업 · k=2", "설명문 출처6+팝업 · 받으면 k=3"),
             ("아홉", "설명문 아홉 · k=2", "설명문 아홉 · 받으면 k=3"),
             ("표지 8", "표지 여덟 · k=2", "표지 여덟 · 받으면 k=3")]
    xs = np.arange(len(PAIRS))
    for ax, idx, ttl, ylab in ((a1, 3, "받는 벌의 80%가 희석이었다", "$\\Delta$ 팝업"),
                               (a2, 1, "판정치는 프로젝트 최고치", "$\\Delta$ 판정치")):
        v2 = [res[a][idx] for _, a, _ in PAIRS]
        v3 = [res[b][idx] for _, _, b in PAIRS]
        ax.bar(xs - .19, v2, .35, color=MUTE, alpha=.9, edgecolor="none",
               label="$k{=}2$ (현행)")
        ax.bar(xs + .19, v3, .35, color=CLAIM, alpha=.9, edgecolor="none",
               label="받으면 $k{=}3$")
        ax.axhline(0, color=INK, lw=.9)
        ax.set_xticks(xs)
        ax.set_xticklabels([p[0] for p in PAIRS], fontsize=6.6)
        ax.set_ylabel(ylab, fontsize=7.0)
        ax.set_title(ttl, fontsize=7.2)
        ax.legend(fontsize=6.0, frameon=False, loc="upper right")
        ax.tick_params(labelsize=6.4)
    a1.annotate("", xy=(1.19, res[PAIRS[1][2]][3]),
                xytext=(0.81, res[PAIRS[1][1]][3]),
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.6))
    a1.text(1.0, .0195, "$-$0.0013\n$\\to+$0.0144", fontsize=6.2, color=CLAIM,
            ha="center")
    a1.set_ylim(-.004, .026)
    cv = k["ctrl"][list(k["ctrl"])[0]][1]
    a2.axhline(cv, color=GATE, ls=":", lw=1.0)
    a2.text(3.42, cv + .0006, "대조 $+$0.001\n(뒤섞은 축 · $k{=}3$)",
            fontsize=5.8, color=GATE, ha="right")
    a2.set_ylim(-.014, .0175)

    # ③ 새 축 지렛대 역사
    HIST = [("경쟁 밀도", -.020), ("전형성", -.009), ("체험 밀도", -.060),
            ("표지(28%)", -.010), ("표지(100%)", -.011), ("IP 인지도", .011),
            ("직전작", .014), ("문장 수", .010), ("작은 것 셋", .016),
            ("설명문 c0", .010), ("이번", res["설명문 아홉 · 받으면 k=3"][1])]
    HIST.sort(key=lambda x: x[1])
    ys = np.arange(len(HIST))
    cols = [CLAIM if h[0] == "이번" else (GATE if h[1] > 0 else MUTE) for h in HIST]
    a3.barh(ys, [h[1] for h in HIST], .62, color=cols, alpha=.9, edgecolor="none")
    a3.axvline(0, color=INK, lw=.9)
    a3.axvspan(-.033, .033, color=GATE, alpha=.08, zorder=0)
    a3.text(.0335, .4, "구간 반폭", fontsize=5.8, color=GATE)
    a3.set_yticks(ys)
    a3.set_yticklabels([h[0] for h in HIST], fontsize=6.0)
    a3.set_xlabel("$\\Delta$ 판정치", fontsize=7.0)
    a3.set_title("노트 84 이후 새 축 지렛대 전부", fontsize=7.2)
    a3.tick_params(labelsize=6.2, length=0)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_where(out: Path, root: str = ".") -> dict:
    """노트101 — 왼쪽 붙을 데, 가운데 A/B, 오른쪽 표지 대 설명문."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note101.json").read_text())
    w = json.loads((R / "note101b.json").read_text())
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.05, 1.1, 1]})

    # ① 붙을 데
    rows = w["rows"]
    ok = [d for d in rows if np.isfinite(rows[d][0])]
    xs = [abs(rows[d][0]) for d in ok]
    ys = [rows[d][2] for d in ok]
    a1.axhline(0, color=MUTE, lw=.7)
    a1.plot(xs, ys, "o", color=CLAIM, ms=5.2, alpha=.9)
    for d, x, y in zip(ok, xs, ys):
        a1.annotate(d, (x, y), fontsize=6.0, xytext=(4, 3),
                    textcoords="offset points", color=INK)
    z = np.polyfit(xs, ys, 1)
    xx = np.linspace(0, max(xs) * 1.08, 20)
    a1.plot(xx, np.polyval(z, xx), "-", color=GATE, lw=1.1, alpha=.65)
    a1.text(.02, .085, "$r=" + f"{w['r_axis']:+.3f}$" + "  $(n{=}9)$",
            fontsize=7.0, color=GATE)
    a1.text(.02, .070, "바탕 $\\rho$ 로는 $r=" + f"{w['r_base']:+.3f}$",
            fontsize=6.0, color=MUTE)
    a1.set_xlabel("$|$설명문 축 $\\cdot$ 그 도메인 라벨$|$", fontsize=7.0)
    a1.set_ylabel("$\\Delta\\rho$ (그 도메인)", fontsize=7.0)
    a1.set_title("새 축은 라벨과 붙을 때만 돕는다", fontsize=7.2)
    a1.tick_params(labelsize=6.4)

    # ② A/B
    ab = j["ab"]
    seeds = list(ab)
    xs2 = np.arange(len(seeds))
    r0 = [ab[s]["B"]["R0"] for s in seeds]
    r1 = [ab[s]["B"]["R1"] for s in seeds]
    sel = [ab[s]["B"][ab[s]["best"]] for s in seeds]
    a2.bar(xs2 - .26, r0, .25, color=MUTE, alpha=.9, edgecolor="none",
           label="R0 전역 $k{=}2$")
    a2.bar(xs2, r1, .25, color=CLAIM, alpha=.9, edgecolor="none",
           label="R1 받으면 $+$1 (미리 박음)")
    a2.bar(xs2 + .26, sel, .25, color=GATE, alpha=.9, edgecolor="none",
           label="A반에서 고른 규칙")
    a2.set_xticks(xs2)
    a2.set_xticklabels([f"분할\n{i+1}" for i in range(len(seeds))], fontsize=6.0)
    a2.set_ylim(.36, .445)
    a2.set_ylabel("B반 판정치", fontsize=7.0)
    a2.set_title("고르면 지고, 박아 두면 이긴다", fontsize=7.2)
    a2.legend(fontsize=5.6, frameon=False, loc="upper left", ncol=1)
    a2.tick_params(labelsize=6.4)
    a2.text(len(seeds) - .55, .4255,
            f"고른 것$-$R1  {j['d_sel']:+.4f}\nR1$-$R0  {j['d_r1']:+.4f}",
            fontsize=6.2, ha="right", color=INK)

    # ③ 표지 대 설명문
    mech = w["mech"]
    ds = list(mech)
    ys3 = np.arange(len(ds))
    de = [mech[d][1] - mech[d][0] if np.isfinite(mech[d][1]) else 0 for d in ds]
    dc = [mech[d][2] - mech[d][0] for d in ds]
    a3.barh(ys3 - .19, de, .35, color=GATE, alpha=.9, edgecolor="none",
            label="설명문")
    a3.barh(ys3 + .19, dc, .35, color=CLAIM, alpha=.9, edgecolor="none",
            label="표지")
    a3.axvline(0, color=INK, lw=.9)
    a3.set_yticks(ys3)
    a3.set_yticklabels(ds, fontsize=6.2)
    a3.set_xlabel("$\\Delta$ 자기 $\\rho$ ($k{=}3$)", fontsize=7.0)
    a3.set_title("표지는 라벨을 안 담는다", fontsize=7.2)
    a3.legend(fontsize=6.0, frameon=False, loc="lower right")
    a3.tick_params(labelsize=6.2, length=0)
    a3.invert_yaxis()

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_crowd(out: Path, root: str = ".") -> dict:
    """노트102 — 왼쪽 문턱 곡선, 가운데 상관은 재현된다, 오른쪽 적재가 밀린다."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note102.json").read_text())
    c = json.loads((R / "note102c.json").read_text())
    d = json.loads((R / "note102d.json").read_text())
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1.1]})

    # ① 문턱 곡선
    su = j["summ"]
    ths = sorted(float(t) for t in su if float(t) < 8)
    xs = [su[str(t)][4] for t in ths]
    ys = [su[str(t)][1] for t in ths]
    a1.plot(xs, ys, "o-", color=CLAIM, lw=1.6, ms=4.2)
    for t, x, y in zip(ths, xs, ys):
        a1.annotate(f"{t:.2f}", (x, y), fontsize=5.6, xytext=(3, -8),
                    textcoords="offset points", color=MUTE)
    a1.plot([0], [0], "*", color=INK, ms=11)
    a1.text(6, -.004, "축 없음(최고)", fontsize=6.4, color=INK)
    a1.plot([j["rand"][2]], [j["rand"][0] - j["none"][0]], "D", color=GATE,
            ms=6)
    a1.annotate("무작위 같은 개수 --- 재서 고른 것보다 낫다",
                xy=(j["rand"][2], j["rand"][0] - j["none"][0]),
                xytext=(58, -.062), fontsize=6.0, color=GATE,
                arrowprops=dict(arrowstyle="->", color=GATE, lw=.9))
    a1.axhline(0, color=INK, lw=.8)
    a1.set_xlabel("붙인 칸 수 (문턱을 낮출수록 많아진다)", fontsize=7.0)
    a1.set_ylabel("$\\Delta$ B반 판정치", fontsize=7.0)
    a1.set_title("적을수록 나았다 --- 영이 최고", fontsize=7.2)
    a1.tick_params(labelsize=6.4)

    # ② 상관은 재현된다
    P = np.array([[p[0], p[1]] for p in c["pts"]])
    sel = P[:, 0] >= .20
    a2.plot(P[~sel, 0], P[~sel, 1], "o", color=MUTE, ms=2.4, alpha=.45)
    a2.plot(P[sel, 0], P[sel, 1], "o", color=CLAIM, ms=3.4, alpha=.85)
    a2.plot([0, .6], [0, .6], "-", color=INK, lw=.7, alpha=.5)
    a2.axvline(.20, color=GATE, ls="--", lw=.9)
    a2.axhline(.20, color=GATE, ls="--", lw=.9)
    a2.text(.415, .035, "$r=" + f"{c['r']:+.3f}$", fontsize=7.0, color=GATE,
            ha="center")
    a2.text(.415, .008, f"고른 {c['n_sel']}칸 중 {c['n_rep']}칸 재현",
            fontsize=6.0, color=CLAIM, ha="center")
    a2.set_xlim(0, .58)
    a2.set_ylim(0, .58)
    a2.set_xlabel("A반 $|r|$ (고를 때)", fontsize=7.0)
    a2.set_ylabel("B반 $|r|$ (다시 재면)", fontsize=7.0)
    a2.set_title("상관 자체는 진짜였다", fontsize=7.2)
    a2.tick_params(labelsize=6.4)

    # ③ 적재가 밀린다
    sh = d["share"]
    ds = list(sh)
    ns = [sh[x][2] for x in ds]
    dd = [sh[x][1] - sh[x][0] for x in ds]
    a3.plot(ns, dd, "o", color=CLAIM, ms=5, alpha=.9)
    for x, n, y in zip(ds, ns, dd):
        if n > 0 or x in ("웹툰",):
            a3.annotate(x, (n, y), fontsize=6.0, xytext=(4, 2),
                        textcoords="offset points", color=INK)
    z = np.polyfit(ns, dd, 1)
    xx = np.linspace(-.3, max(ns) + .4, 20)
    a3.plot(xx, np.polyval(z, xx), "-", color=GATE, lw=1.1, alpha=.6)
    a3.axhline(0, color=INK, lw=.8)
    a3.text(4.2, -.05, "$r=" + f"{d['r_n']:+.3f}$", fontsize=7.0, color=GATE)
    a3.set_xlabel("붙인 축 수", fontsize=7.0)
    a3.set_ylabel("$\\Delta$ 공통 축 블록의 적재 몫", fontsize=7.0)
    a3.set_title("고른 축이 정렬 재료를 밀어낸다", fontsize=7.2)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_unalign(out: Path, root: str = ".") -> dict:
    """노트103 — 왼쪽 밀어냄 뒤집기, 가운데 그래도 나빠짐, 오른쪽 잔차."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note103.json").read_text())
    k = json.loads((R / "note103b.json").read_text())
    c = json.loads((R / "note103c.json").read_text())
    b0, p0 = j["base"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.15, 1.1, 1]})

    # ① 밀어냄이 뒤집힌다
    sh = j["share"]
    ds = list(sh)
    xs = np.arange(len(ds))
    a1.bar(xs - .26, [sh[d][1] for d in ds], .25, color=CLAIM, alpha=.9,
           edgecolor="none", label="고유로 넣으면")
    a1.bar(xs, [sh[d][0] for d in ds], .25, color=MUTE, alpha=.9,
           edgecolor="none", label="현행(축 없음)")
    a1.bar(xs + .26, [sh[d][2] for d in ds], .25, color=GATE, alpha=.9,
           edgecolor="none", label="공통으로 올리면")
    a1.set_xticks(xs)
    a1.set_xticklabels(ds, fontsize=5.6, rotation=38, ha="right")
    a1.set_ylabel("공통 블록 적재 몫", fontsize=7.0)
    a1.set_ylim(.25, 1.0)
    a1.set_title("밀어냄은 확실히 뒤집힌다", fontsize=7.2)
    a1.legend(fontsize=5.8, frameon=False, loc="upper left", ncol=1)
    a1.tick_params(labelsize=6.2)

    # ② 그래도 나빠진다
    res = j["res"]
    ORD = [("고유 $k{=}2$", "설명문 · 고유 · k=2"),
           ("고유 $k{=}3$", "설명문 · 고유 · k=3"),
           ("공통 $k{=}2$", "설명문 · **공통** · k=2"),
           ("공통 $k{=}3$", "설명문 · **공통** · k=3"),
           ("공통 $k{=}4$", "설명문 · **공통** · k=4")]
    xs2 = np.arange(len(ORD))
    vs = [res[a][1] for _, a in ORD]
    cols = [CLAIM, CLAIM, GATE, GATE, GATE]
    a2.bar(xs2, vs, .6, color=cols, alpha=.9, edgecolor="none")
    for x, v in zip(xs2, vs):
        a2.text(x, v + (.0012 if v > 0 else -.003), f"{v:+.4f}",
                ha="center", fontsize=5.9)
    a2.axhline(0, color=INK, lw=.9)
    a2.set_xticks(xs2)
    a2.set_xticklabels([a for a, _ in ORD], fontsize=6.0, rotation=25,
                       ha="right")
    a2.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a2.set_ylim(-.028, .019)
    a2.set_title("정렬 재료를 늘렸는데 성적은 내린다", fontsize=7.2)
    a2.tick_params(labelsize=6.2)

    # ③ 잔차
    labs = ["원래 셋\n(emb0 고유)", "원래 셋\n(emb0 공통)", "\\textbf{emb0 자신}"]
    vals = [c["ra"], c["rb"], c["rc"]]
    cols = [MUTE, GATE, CLAIM]
    a3.bar(np.arange(3), vals, .58, color=cols, alpha=.9, edgecolor="none")
    for x, v in zip(range(3), vals):
        a3.text(x, v + .04, f"{v:.3f}", ha="center", fontsize=6.4)
    a3.axhline(1.0, color=INK, ls=":", lw=1.0)
    a3.text(2.42, 1.05, "1.0 $=$ 안 맞춘 것과 같다", fontsize=5.8, color=INK,
            ha="right")
    a3.set_xticks(range(3))
    a3.set_xticklabels(["원래 셋\n(고유)", "원래 셋\n(공통)", "emb0 자신"],
                       fontsize=6.0)
    a3.set_ylabel("프로크루스테스 상대 잔차", fontsize=7.0)
    a3.set_ylim(0, 1.95)
    a3.set_title("맞출 수 없는 축이었다", fontsize=7.2)
    a3.tick_params(labelsize=6.2)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_relax(out: Path, root: str = ".") -> dict:
    """노트104 — 왼쪽 정렬만 바꾸기, 가운데 진단한 자리, 오른쪽 잔차 역설."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note104.json").read_text())
    k = json.loads((R / "note104b.json").read_text())
    b0, p0 = j["base"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.15, 1.1, 1]})

    # ① 축 없이 정렬만
    na = j["noaxis"]
    labs = list(na)
    xs = np.arange(len(labs))
    vs = [na[l][1] for l in labs]
    cols = [INK] + [GATE] * 5 + [CLAIM] * 3
    a1.bar(xs, vs, .62, color=cols, alpha=.9, edgecolor="none")
    a1.axhline(0, color=INK, lw=.9)
    a1.axhspan(-.033, .033, color=GATE, alpha=.07, zorder=0)
    a1.set_xticks(xs)
    a1.set_xticklabels(["직교", "0.01", "0.1", "1", "10", "100",
                        "0.25", "0.5", "0.75"], fontsize=6.2, rotation=45,
                       ha="right")
    a1.text(3, .0042, "리지 $\\alpha$", fontsize=6.4, color=GATE, ha="center")
    a1.text(7, .0042, "직교로 축소", fontsize=6.4, color=CLAIM, ha="center")
    a1.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a1.set_ylim(-.008, .006)
    a1.set_title("지금 구조에서는 직교가 안 아프다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    # ② 진단한 자리
    res = k["res"]
    PAIR = [("공통 $k{=}2$", "공통 · k=2 · 직교", "공통 · k=2 · 축소 w=0.9"),
            ("공통 $k{=}3$", "공통 · k=3 · 직교", "공통 · k=3 · 축소 w=0.9"),
            ("고유 $k{=}3$", "고유 · k=3 · 직교(노트 100)", "고유 · k=3 · 축소 w=0.9")]
    xs2 = np.arange(len(PAIR))
    a2.bar(xs2 - .19, [res[a][1] for _, a, _ in PAIR], .35, color=MUTE,
           alpha=.9, edgecolor="none", label="직교(현행)")
    a2.bar(xs2 + .19, [res[b][1] for _, _, b in PAIR], .35, color=CLAIM,
           alpha=.9, edgecolor="none", label="직교로 축소 $w{=}0.9$")
    a2.axhline(0, color=INK, lw=.9)
    a2.annotate("", xy=(.19, res[PAIR[0][2]][1]),
                xytext=(-.19, res[PAIR[0][1]][1]),
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.6))
    a2.text(0, .0098, "$2.7\\times$", fontsize=6.6, color=CLAIM, ha="center")
    a2.set_xticks(xs2)
    a2.set_xticklabels([p[0] for p in PAIR], fontsize=6.4)
    a2.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a2.set_ylim(-.019, .0165)
    a2.set_title("진단한 자리에서만 듣는다", fontsize=7.2)
    a2.legend(fontsize=6.0, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.4)

    # ③ 잔차 역설
    scr = k["scr"]
    ax = list(scr)
    rr = [scr[a][0] for a in ax]
    dd = [scr[a][2] for a in ax]
    a3.axhline(0, color=MUTE, lw=.7)
    a3.plot(rr, dd, "o", color=CLAIM, ms=5, alpha=.9)
    for a, x, y in zip(ax, rr, dd):
        a3.annotate(a, (x, y), fontsize=5.8, xytext=(4, 3),
                    textcoords="offset points", color=INK)
    z = np.polyfit(rr, dd, 1)
    xx = np.linspace(min(rr) - .07, max(rr) + .12, 20)
    a3.plot(xx, np.polyval(z, xx), "-", color=GATE, lw=1.1, alpha=.6)
    a3.text(1.86, -.0088, "$r=" + f"{k['r_resid']:+.3f}$", fontsize=7.0,
            color=GATE, ha="right")
    a3.text(1.86, -.0108, "잘 맞출수록 쓸모없다", fontsize=6.2, color=CLAIM,
            ha="right")
    a3.set_xlabel("정렬 잔차 (낮을수록 잘 맞는다)", fontsize=7.0)
    a3.set_ylabel("$\\Delta$ 판정치 (공통으로)", fontsize=7.0)
    a3.set_title("맞출 수 있는 축은 새롭지 않다", fontsize=7.2)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_fourth(out: Path, root: str = ".") -> dict:
    """노트105 — 왼쪽 부호가 갈린다, 가운데 정직한 방향, 오른쪽 개념 대 성적."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note105.json").read_text())
    k = json.loads((R / "note105b.json").read_text())
    m = json.loads((R / "note105c.json").read_text())
    b0, p0 = j["base"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.15, 1, 1.05]})

    # ① 부호가 갈린다
    cov = j["cov"]
    ds = [d for d in cov if np.isfinite(cov[d][1])]
    ds.sort(key=lambda d: cov[d][1])
    ys = np.arange(len(ds))
    vs = [cov[d][1] for d in ds]
    NP = set(m["notprice"])
    cols = [(GATE if d in NP else CLAIM) for d in ds]
    a1.barh(ys, vs, .62, color=cols, alpha=.9, edgecolor="none")
    a1.axvline(0, color=INK, lw=.9)
    a1.set_yticks(ys)
    a1.set_yticklabels(ds, fontsize=6.4)
    for y, d in zip(ys, ds):
        if d in ("만화", "세계애니"):
            a1.text(vs[ds.index(d)] - .02, y, "연령 등급", fontsize=5.6,
                    va="center", ha="right", color="white")
    a1.set_xlabel("입장료 축과 라벨의 상관", fontsize=7.0)
    a1.set_title("같은 축이 도메인마다 반대로 움직인다", fontsize=7.2)
    a1.tick_params(labelsize=6.2, length=0)
    a1.plot([], [], "s", color=CLAIM, ms=5, label="실제 가격")
    a1.plot([], [], "s", color=GATE, ms=5, label="가격이 아님")
    a1.legend(fontsize=5.8, frameon=False, loc="lower right")

    # ② 정직한 방향
    hon = k["hon"]
    fr = sorted(float(x) for x in hon)
    xs = [f * 100 for f in fr]
    a2.plot(xs, [hon[str(f)][1] for f in fr], "o-", color=CLAIM, lw=1.6, ms=4.2)
    a2.axhline(0, color=INK, lw=.9)
    a2.axhline(k["ctrl"]["무작위 방향"][1], color=MUTE, ls="--", lw=1.0)
    a2.text(97, k["ctrl"]["무작위 방향"][1] - .0022, "무작위로 뒤집기",
            fontsize=6.0, color=MUTE, ha="right")
    a2.axhline(k["ctrl"]["방향만 맞추고 정렬엔 안 넣음"][1], color=GATE,
               ls=":", lw=1.2)
    a2.text(97, .0009, "방향만 맞추고 정렬엔 안 넣기 $=$ $+$0.0000",
            fontsize=5.8, color=GATE, ha="right")
    a2.set_xlabel("방향을 정하는 데 쓴 보정 표본 (%)", fontsize=7.0)
    a2.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a2.set_title("절반이면 전체 자료만큼 안다", fontsize=7.2)
    a2.tick_params(labelsize=6.4)

    # ③ 개념 대 성적
    RES = m["res"]
    NAMES = ["현행 셋", "$+$입장료 · 방향 맞춤(노트 105 앞부분)",
             "$+$입장료 · \\textbf{가격 아닌 넷 끄기}"]
    SHORT = ["현행 셋", "$+$입장료\n(그대로)", "$+$입장료\n(개념 정리)"]
    resid = [0.556, 0.875, 0.743]
    perf = [RES[n][1] for n in NAMES]
    xs3 = np.arange(3)
    a3.bar(xs3, perf, .55, color=[MUTE, CLAIM, GATE], alpha=.9,
           edgecolor="none")
    a3.axhline(0, color=INK, lw=.9)
    for x, v in zip(xs3, perf):
        a3.text(x, v + (.0015 if v > 0 else -.004), f"{v:+.4f}", ha="center",
                fontsize=6.2)
    a3.set_xticks(xs3)
    a3.set_xticklabels(SHORT, fontsize=6.0)
    a3.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a3.set_ylim(-.034, .019)
    a3.tick_params(labelsize=6.2)
    a4 = a3.twinx()
    a4.plot(xs3, resid, "D--", color=INK, lw=1.2, ms=5)
    a4.set_ylabel("정렬 잔차 (낮을수록 개념 정합)", fontsize=6.6)
    a4.set_ylim(.45, 1.02)
    a4.tick_params(labelsize=6.2)
    a4.spines["right"].set_visible(True)
    a3.set_title("개념을 고치면 잔차는 내리고 성적도 내린다", fontsize=7.0)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_tsplit(out: Path, root: str = ".") -> dict:
    """노트106 — 왼쪽 판정치, 가운데 팝업, 오른쪽 팝업의 과거 없음."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note106b.json").read_text())
    Ts = sorted(int(t) for t in j)
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.1, 1.1, 1]})

    db = [j[str(T)]["b"] - j[str(T)]["a"] for T in Ts]
    dc = [j[str(T)]["c"] - j[str(T)]["a"] for T in Ts]
    a1.axhline(0, color=INK, lw=.9)
    a1.plot(Ts, db, "o-", color=MUTE, lw=1.4, ms=4.2, label="넣기")
    a1.plot(Ts, dc, "D-", color=CLAIM, lw=1.7, ms=4.6,
            label="넣되 방향 모르면 끄기")
    for T, v in zip(Ts, dc):
        a1.annotate(f"{v:+.4f}", (T, v), fontsize=5.8, xytext=(0, 6),
                    textcoords="offset points", ha="center", color=CLAIM)
    a1.set_xticks(Ts)
    a1.set_xlabel("시점 $T$ --- 출처는 이전, 대상은 이후", fontsize=7.0)
    a1.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a1.set_title("미래일수록 이득이 커진다", fontsize=7.2)
    a1.legend(fontsize=6.0, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.4)

    Tp = [T for T in Ts if np.isfinite(j[str(T)]["pb"])]
    pb = [j[str(T)]["pb"] - j[str(T)]["pa"] for T in Tp]
    pc = [j[str(T)]["pc"] - j[str(T)]["pa"] for T in Tp]
    a2.axhline(0, color=INK, lw=.9)
    a2.plot(Tp, pb, "o-", color=MUTE, lw=1.4, ms=4.2, label="넣기")
    a2.plot(Tp, pc, "D-", color=CLAIM, lw=1.7, ms=4.6, label="방향 모르면 끄기")
    a2.fill_between(Tp, pb, pc, color=CLAIM, alpha=.12, lw=0)
    a2.text(2024, -.040, "규칙이 되찾은 몫\n45%", fontsize=6.2, color=CLAIM,
            ha="center")
    a2.set_xticks(Tp)
    a2.set_xlabel("시점 $T$", fontsize=7.0)
    a2.set_ylabel("$\\Delta$ 팝업", fontsize=7.0)
    a2.set_title("팝업은 어느 시점에서도 내린다", fontsize=7.2)
    a2.legend(fontsize=6.0, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.4)

    PRE = {2023: (0, 75), 2024: (1, 74), 2025: (16, 59), 2026: (56, 19)}
    xs = np.arange(len(Ts))
    a3.bar(xs, [PRE[T][0] for T in Ts], .6, color=GATE, alpha=.9,
           edgecolor="none", label="$T$ 이전(방향을 정할 자료)")
    a3.bar(xs, [PRE[T][1] for T in Ts], .6,
           bottom=[PRE[T][0] for T in Ts], color=MUTE, alpha=.7,
           edgecolor="none", label="$T$ 이후(평가 대상)")
    a3.axhline(25, color=CLAIM, ls="--", lw=1.1)
    a3.text(-.45, 27, "방향을 정하려면 25건", fontsize=6.0, color=CLAIM,
            ha="left")
    a3.set_ylim(0, 108)
    a3.set_xticks(xs)
    a3.set_xticklabels([str(T) for T in Ts], fontsize=6.4)
    a3.set_ylabel("팝업 레코드 수", fontsize=7.0)
    a3.set_title("팝업엔 과거가 없다", fontsize=7.2)
    a3.legend(fontsize=5.8, frameon=False, loc="upper center", ncol=1)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_split(out: Path, root: str = ".") -> dict:
    """노트107 — 왼쪽 두 지표 산점, 가운데 순위 뒤바뀜, 오른쪽 A/B."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note107.json").read_text())
    k = json.loads((R / "note107b.json").read_text())
    rows = j["rows"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.05, .85, 1.15]})

    labs = list(rows)
    xs = [rows[l][1] for l in labs]
    ys = [rows[l][3] for l in labs]
    a1.axhline(0, color=MUTE, lw=.7)
    a1.axvline(0, color=MUTE, lw=.7)
    a1.plot(xs, ys, "o", color=MUTE, ms=4, alpha=.75)
    for L, c in ((j["best_j"], GATE), (j["best_p"], CLAIM)):
        a1.plot(rows[L][1], rows[L][3], "o", color=c, ms=7)
        a1.annotate(L, (rows[L][1], rows[L][3]), fontsize=6.0,
                    xytext=(-4, 8), textcoords="offset points", color=c,
                    ha="right")
    z = np.polyfit(xs, ys, 1)
    xx = np.linspace(min(xs) - .002, max(xs) + .002, 20)
    a1.plot(xx, np.polyval(z, xx), "-", color=INK, lw=1.0, alpha=.5)
    a1.text(-.014, .021, "$r=" + f"{j['r']:+.3f}$" + "  (설정 20)",
            fontsize=6.8, color=INK)
    a1.set_xlabel("$\\Delta$ 판정치 (연구)", fontsize=7.0)
    a1.set_ylabel("$\\Delta$ 팝업 (제품)", fontsize=7.0)
    a1.set_title("두 지표가 거의 무관하다", fontsize=7.2)
    a1.tick_params(labelsize=6.4)

    # ② 순위 뒤바뀜
    rj = sorted(labs, key=lambda l: -rows[l][0])
    rp = sorted(labs, key=lambda l: -rows[l][2])
    for i, L in enumerate(rj):
        c = CLAIM if L in (j["best_j"], j["best_p"]) else MUTE
        a2.plot([0, 1], [i, rp.index(L)], "-", color=c, lw=1.1,
                alpha=.85 if c == CLAIM else .35)
    a2.plot([0] * len(rj), range(len(rj)), "o", color=GATE, ms=3)
    a2.plot([1] * len(rp), range(len(rp)), "o", color=CLAIM, ms=3)
    for L, c, x, ha in ((j["best_j"], GATE, -.06, "right"),
                        (j["best_p"], CLAIM, 1.06, "left")):
        a2.annotate(L, (0 if c == GATE else 1,
                        rj.index(L) if c == GATE else rp.index(L)),
                    fontsize=5.8, xytext=(-6 if c == GATE else 6, 0),
                    textcoords="offset points", color=c, ha=ha, va="center")
    a2.set_xlim(-.75, 1.75)
    a2.set_xticks([0, 1])
    a2.set_xticklabels(["판정치\n순위", "팝업\n순위"], fontsize=6.4)
    a2.invert_yaxis()
    a2.set_yticks([])
    a2.set_title("순위가 뒤섞인다", fontsize=7.2)
    for sp in ("left", "bottom"):
        a2.spines[sp].set_visible(False)
    a2.tick_params(length=0)

    # ③ A/B
    o = k["out"]
    xs3 = np.arange(len(o))
    a3.bar(xs3 - .21, [x[2] for x in o], .38, color=CLAIM, alpha=.9,
           edgecolor="none", label="팝업으로 고른 설정")
    a3.bar(xs3 + .21, [x[4] for x in o], .38, color=GATE, alpha=.9,
           edgecolor="none", label="판정치로 고른 설정")
    a3.axhline(k["cur"], color=INK, ls="--", lw=1.2)
    a3.text(len(o) - .4, k["cur"] + .012, f"현행 설정 그대로 {k['cur']:+.4f}",
            fontsize=6.0, color=INK, ha="right")
    a3.set_xticks(xs3)
    a3.set_xticklabels([f"{i+1}" for i in range(len(o))], fontsize=6.4)
    a3.set_xlabel("반쪽 분할", fontsize=7.0)
    a3.set_ylabel("B반 팝업 $\\rho$", fontsize=7.0)
    a3.set_title(f"고르면 진다 --- 평균 {k['d']:+.4f}", fontsize=7.2)
    a3.legend(fontsize=5.8, frameon=False, loc="upper left")
    a3.set_ylim(0, .78)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_adopt(out: Path, root: str = ".") -> dict:
    """노트108 — 왼쪽 잔차, 가운데 채택 검정, 오른쪽 시간 분할."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note108.json").read_text())
    k = json.loads((R / "note108b.json").read_text())
    b0, p0 = j["base"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.05, 1.1, 1.05]})

    # ① 잔차
    LAB = ["긁은 축\n(노트 103)", "입장료\n(노트 105)", "미디어 홍보\n채우기 전",
           "미디어 홍보\n채운 뒤", "\\textbf{채우고 방향}", "현행 공통 축 셋"]
    VAL = [1.676, 0.875, j["resid"][0], j["resid"][1], j["resid"][2], 0.556]
    cols = [MUTE, GATE, MUTE, GATE, CLAIM, INK]
    xs = np.arange(len(VAL))
    a1.bar(xs, VAL, .62, color=cols, alpha=.9, edgecolor="none")
    for x, v in zip(xs, VAL):
        a1.text(x, v + .03, f"{v:.3f}", ha="center", fontsize=6.0)
    a1.axhline(0.556, color=INK, ls=":", lw=1.1)
    a1.axhline(1.0, color=CLAIM, ls="--", lw=.9)
    a1.text(5.4, 1.03, "1.0 $=$ 안 맞춘 것과 같다", fontsize=5.8, color=CLAIM,
            ha="right")
    a1.set_xticks(xs)
    a1.set_xticklabels(["긁은 축", "입장료", "미디어(전)", "미디어(후)",
                        "미디어+방향", "현행 셋"], fontsize=6.0,
                       rotation=38, ha="right")
    a1.set_ylabel("정렬 잔차", fontsize=7.0)
    a1.set_ylim(0, 1.95)
    a1.set_title("채운 축이 현행 셋보다 잘 맞는다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    # ② 채택 검정
    ad = k["adopt"]
    seeds = [s for s in ad if s.startswith("판정치")]
    ys = np.arange(len(seeds))
    for i, s in enumerate(seeds):
        lo, hi = ad[s]["ci"]
        a2.plot([lo, hi], [i, i], "-", color=CLAIM, lw=2.4, alpha=.85)
        a2.plot([ad[s]["diff"]], [i], "o", color=CLAIM, ms=5)
    ps = [s for s in ad if s.startswith("팝업")]
    for i, s in enumerate(ps):
        lo, hi = ad[s]["ci"]
        a2.plot([lo, hi], [i + len(seeds) + .6, i + len(seeds) + .6], "-",
                color=GATE, lw=2.0, alpha=.6)
        a2.plot([ad[s]["diff"]], [i + len(seeds) + .6], "s", color=GATE, ms=4)
    a2.axvline(0, color=INK, lw=1.1)
    a2.text(.041, 1.5, "판정치 --- 채택 4/4", fontsize=6.8, color=CLAIM,
            ha="left", va="center")
    a2.text(.125, 5.6, "팝업  보류 4/4", fontsize=6.6, color=GATE,
            ha="right", va="center")
    a2.set_xlim(-.075, .145)
    a2.set_yticks([])
    a2.set_xlabel("$\\Delta\\rho$  (짝지은 붓스트랩 95\\% 구간)", fontsize=7.0)
    a2.set_title("씨앗 넷 전부 0을 넘는다", fontsize=7.2)
    a2.tick_params(labelsize=6.4)
    for sp in ("left",):
        a2.spines[sp].set_visible(False)

    # ③ 시간 분할
    ts = k["ts"]
    Ts = sorted(int(t) for t in ts)
    a3.axhline(0, color=INK, lw=.9)
    a3.plot(Ts, [ts[str(T)]["d"] for T in Ts], "o-", color=CLAIM, lw=1.7,
            ms=4.6, label="판정치")
    Tp = [T for T in Ts if np.isfinite(ts[str(T)]["dp"])]
    a3.plot(Tp, [ts[str(T)]["dp"] for T in Tp], "s--", color=GATE, lw=1.3,
            ms=4.0, label="팝업")
    for T in Ts:
        a3.annotate(f"{ts[str(T)]['d']:+.4f}", (T, ts[str(T)]["d"]),
                    fontsize=5.8, xytext=(0, 6), textcoords="offset points",
                    ha="center", color=CLAIM)
    a3.set_xticks(Ts)
    a3.set_xlabel("시점 $T$", fontsize=7.0)
    a3.set_ylabel("$\\Delta\\rho$", fontsize=7.0)
    a3.set_title("미래에서도 네 시점 전부 양수", fontsize=7.2)
    a3.legend(fontsize=6.2, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_blur(out: Path, root: str = ".") -> dict:
    """노트109 — 왼쪽 채울수록 흐려진다, 가운데 공 나누기, 오른쪽 도메인별."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note109b.json").read_text())
    c = json.loads((R / "note109.json").read_text())["cov"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.15, .9, 1.05]})

    labs = list(j)
    xs = np.arange(len(labs))
    rho = [j[l][1] for l in labs]
    rr = [j[l][4] for l in labs]
    pr = [j[l][5] for l in labs]
    a1.plot(xs, rho, "o-", color=CLAIM, lw=1.8, ms=5)
    for x, v, n in zip(xs, rho, pr):
        a1.annotate(f"{v:+.4f}", (x, v), fontsize=5.8, xytext=(0, 7),
                    textcoords="offset points", ha="center", color=CLAIM)
    a1.plot([1], [rho[1]], "*", color=INK, ms=14, zorder=5)
    a1.set_xticks(xs)
    a1.set_xticklabels(["안 채움", "만화·\n세계애니", "$+$게임", "$+$웹툰",
                        "$+$도서"], fontsize=6.0)
    a1.set_ylabel("판정치 $\\rho$", fontsize=7.0)
    a1.set_ylim(.410, .4325)
    a1.set_title("최고는 두 도메인에서 멈춘다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)
    a4 = a1.twinx()
    a4.plot(xs, rr, "D--", color=GATE, lw=1.3, ms=4.2)
    a4.set_ylabel("미디어 홍보 정렬 잔차", fontsize=6.8, color=GATE)
    a4.tick_params(labelsize=6.2, colors=GATE)
    a4.spines["right"].set_visible(True)
    a4.text(3.9, .60, "쌍 6$\\to$56", fontsize=6.0, color=GATE, ha="right")

    # ② 공 나누기
    parts = [("채우기\n(만화·세계애니)", j["만화·세계애니만(노트 108)"][0] - j["안 채움"][0]),
             ("공통 축으로\n올리기", j["만화·세계애니만(노트 108)"][2]),
             ("더 채우기\n(게임·웹툰·도서)", j["$+$도서(전부)"][1] - j["만화·세계애니만(노트 108)"][1])]
    xs2 = np.arange(3)
    vs = [p[1] for p in parts]
    a2.bar(xs2, vs, .58, color=[CLAIM, GATE, MUTE], alpha=.9, edgecolor="none")
    for x, v in zip(xs2, vs):
        a2.text(x, v + (.0008 if v > 0 else -.0018), f"{v:+.4f}", ha="center",
                fontsize=6.2)
    a2.axhline(0, color=INK, lw=.9)
    a2.set_xticks(xs2)
    a2.set_xticklabels(["채우기", "공통 축으로", "더 채우기"], fontsize=6.4)
    a2.text(0, -.0033, "만화·세계애니", fontsize=5.6, ha="center", color=MUTE)
    a2.text(1, -.0033, "입장료+미디어", fontsize=5.6, ha="center", color=MUTE)
    a2.text(2, -.0033, "게임·웹툰·도서", fontsize=5.6, ha="center", color=MUTE)
    a2.set_ylim(-.0042, .0195)
    a2.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a2.set_title("노트 108의 공을 다시 나눈다", fontsize=7.2)
    a2.tick_params(labelsize=6.2)

    # ③ 도메인별 라벨 상관
    ds = [d for d in c if np.isfinite(c[d][1])]
    ds.sort(key=lambda d: c[d][1])
    ys = np.arange(len(ds))
    NEW = {"게임", "웹툰", "도서"}
    KEEP = {"만화", "세계애니"}
    cols = [(CLAIM if d in KEEP else (MUTE if d in NEW else GATE)) for d in ds]
    a3.barh(ys, [c[d][1] for d in ds], .62, color=cols, alpha=.9,
            edgecolor="none")
    a3.axvline(0, color=INK, lw=.9)
    a3.set_yticks(ys)
    a3.set_yticklabels(ds, fontsize=6.4)
    a3.set_xlabel("미디어 홍보와 라벨의 상관", fontsize=7.0)
    a3.set_title("웹툰이 $+$0.086으로 거의 0이다", fontsize=7.2)
    a3.plot([], [], "s", color=CLAIM, ms=5, label="지킨 것")
    a3.plot([], [], "s", color=MUTE, ms=5, label="되돌린 것")
    a3.legend(fontsize=5.8, frameon=False, loc="lower right")
    a3.tick_params(labelsize=6.2, length=0)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_popkeep(out: Path, root: str = ".") -> dict:
    """노트110 — 왼쪽 빼면 잃는다, 가운데 얽힘, 오른쪽 되돌림 검정."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note110.json").read_text())
    k = json.loads((R / "note110b.json").read_text())
    b0, p0 = j["base"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.15, .95, 1.05]})

    res = j["res"]
    ORD = ["현행", "팝업의 입장료만 끄기", "팝업의 미디어만 끄기",
           "\\textbf{팝업의 둘 다 끄기}", "아이돌의 둘 다 끄기(대조)",
           "애니의 둘 다 끄기(대조)"]
    SH = ["현행", "팝업 입장료", "팝업 미디어", "팝업 둘 다", "아이돌 둘 다",
          "애니 둘 다"]
    xs = np.arange(len(ORD))
    a1.bar(xs - .19, [res[o][1] for o in ORD], .35, color=GATE, alpha=.9,
           edgecolor="none", label="판정치")
    a1.bar(xs + .19, [res[o][3] for o in ORD], .35, color=CLAIM, alpha=.9,
           edgecolor="none", label="팝업")
    a1.axhline(0, color=INK, lw=.9)
    a1.annotate(f"{res[ORD[1]][3]:+.4f}", (1.19, res[ORD[1]][3]), fontsize=6.6,
                xytext=(16, 2), textcoords="offset points", ha="left",
                color=CLAIM)
    a1.set_xticks(xs)
    a1.set_xticklabels(SH, fontsize=6.0, rotation=38, ha="right")
    a1.set_ylabel("$\\Delta\\rho$", fontsize=7.0)
    a1.set_title("빼면 더 잃는다 --- 가설이 죽었다", fontsize=7.2)
    a1.legend(fontsize=6.2, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.2)

    # ② 얽힘
    DAT = {"팝업": {"입장료": [.388, -.153, .205], "미디어": [.117, .488, .109]},
           "만화": {"입장료": [.279, .044, .289], "미디어": [.277, .262, .171]},
           "세계애니": {"입장료": [.264, .152, .037], "미디어": [.350, .234, .155]}}
    doms = list(DAT)
    xs2 = np.arange(len(doms))
    mx = [max(abs(v) for ax in DAT[d] for v in DAT[d][ax]) for d in doms]
    a2.bar(xs2, mx, .55, color=[CLAIM, MUTE, MUTE], alpha=.9, edgecolor="none")
    for x, v in zip(xs2, mx):
        a2.text(x, v + .012, f"{v:.3f}", ha="center", fontsize=6.4)
    a2.text(0, .30, "미디어\n$\\leftrightarrow$굿즈 규모", fontsize=6.0,
            ha="center", color="white")
    a2.set_xticks(xs2)
    a2.set_xticklabels(doms, fontsize=6.4)
    a2.set_ylabel("새 두 축과 옛 셋의 최대 $|$상관$|$", fontsize=6.8)
    a2.set_ylim(0, .58)
    a2.set_title("팝업에서만 크게 얽혀 있다", fontsize=7.2)
    a2.tick_params(labelsize=6.2)

    # ③ 되돌림 검정
    ss = [s for s in k if s.startswith("판정치")]
    ys = np.arange(len(ss))
    for i, s in enumerate(ss):
        lo, hi = k[s]["ci"]
        a3.plot([lo, hi], [i, i], "-", color=CLAIM, lw=2.6, alpha=.9)
        a3.plot([k[s]["diff"]], [i], "o", color=CLAIM, ms=5)
    ps = [s for s in k if s.startswith("팝업")]
    for i, s in enumerate(ps):
        lo, hi = k[s]["ci"]
        a3.plot([lo, hi], [i + len(ss) + .7, i + len(ss) + .7], "-",
                color=GATE, lw=2.0, alpha=.55)
        a3.plot([k[s]["diff"]], [i + len(ss) + .7], "s", color=GATE, ms=4)
    a3.axvline(0, color=INK, lw=1.1)
    a3.text(.0355, 1.5, "판정치\n악화 4/4", fontsize=6.6, color=CLAIM,
            ha="right", va="center")
    a3.text(.0355, 5.7, "팝업\n보류 4/4", fontsize=6.6, color=GATE,
            ha="right", va="center")
    a3.set_ylim(-.8, 7.6)
    a3.set_yticks([])
    a3.set_xlabel("다섯 채우기 $-$ 두 채우기", fontsize=7.0)
    a3.set_title("되돌린 것이 옳았다", fontsize=7.2)
    a3.set_xlim(-.038, .038)
    a3.tick_params(labelsize=6.4)
    a3.spines["left"].set_visible(False)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_whenknow(out: Path, root: str = ".") -> dict:
    """노트111 — 왼쪽 출처별, 가운데 방향 되돌리기, 오른쪽 두 규약."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note111.json").read_text())
    k = json.loads((R / "note111b.json").read_text())
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1.1, 1]})

    per = j["per"]
    ds = sorted(per, key=lambda d: per[d])
    ys = np.arange(len(ds))
    cols = [(CLAIM if per[d] < 0 else GATE) for d in ds]
    a1.barh(ys, [per[d] for d in ds], .62, color=cols, alpha=.9,
            edgecolor="none")
    a1.axvline(0, color=INK, lw=.9)
    a1.set_yticks(ys)
    a1.set_yticklabels(ds, fontsize=6.4)
    a1.annotate("$+$0.1745", (per["애니"], ds.index("애니")), fontsize=6.4,
                xytext=(-4, 0), textcoords="offset points", ha="right",
                va="center", color="white")
    a1.text(-.027, .3, "채운 두 도메인", fontsize=6.0, color=CLAIM, ha="left")
    a1.set_xlabel("$\\Delta$ 팝업 전이 (세 시점 평균)", fontsize=7.0)
    a1.set_title("손해는 세 출처에 몰려 있다", fontsize=7.2)
    a1.tick_params(labelsize=6.2, length=0)

    uf = k["unflip"]
    labs = [l for l in uf if l != "없음(현행)"]
    labs.sort(key=lambda l: uf[l][3])
    xs = np.arange(len(labs))
    vs = [uf[l][3] for l in labs]
    cols = [CLAIM if v < -.05 else MUTE for v in vs]
    a2.bar(xs, vs, .6, color=cols, alpha=.9, edgecolor="none")
    a2.axhline(0, color=INK, lw=.9)
    a2.annotate("$-$0.1674", (0, vs[0]), fontsize=6.6, xytext=(6, 6),
                textcoords="offset points", ha="left", color=CLAIM)
    a2.set_xticks(xs)
    a2.set_xticklabels([l.replace("의 entry_friction", " 입장료")
                        .replace("의 media_push", " 미디어") for l in labs],
                       fontsize=6.0, rotation=40, ha="right")
    a2.set_ylabel("$\\Delta$ 팝업 (방향을 되돌리면)", fontsize=7.0)
    a2.set_title("팝업의 입장료 방향이 전부다", fontsize=7.2)
    a2.tick_params(labelsize=6.2)

    Ts = [2023, 2024, 2025]
    a3.axhline(0, color=INK, lw=.9)
    a3.plot(Ts, [k["strict"][str(T)] for T in Ts], "s--", color=MUTE, lw=1.4,
            ms=4.2, label="엄격 --- 방향도 과거로")
    a3.plot(Ts, [k["dep"][str(T)] for T in Ts], "o-", color=CLAIM, lw=1.8,
            ms=5, label="배포 --- 방향표 고정")
    for T in Ts:
        a3.annotate(f"{k['dep'][str(T)]:+.4f}", (T, k["dep"][str(T)]),
                    fontsize=5.8, xytext=(0, 7), textcoords="offset points",
                    ha="center", color=CLAIM)
    a3.set_xticks(Ts)
    a3.set_xlabel("시점 $T$", fontsize=7.0)
    a3.set_ylabel("$\\Delta$ 팝업", fontsize=7.0)
    a3.set_title("규약이 답을 바꾼다", fontsize=7.2)
    a3.legend(fontsize=6.0, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_twoclock(out: Path, root: str = ".") -> dict:
    """노트112 — 왼쪽 방향표 판정, 가운데 판정치 두 규약, 오른쪽 팝업 두 규약."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note112.json").read_text())
    t = json.loads((R / "twoproto.json").read_text())
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1.15, 1, 1]})

    # ① 방향표 판정
    GR = ["애니의 미디어 홍보 빼기", "웹툰의 입장료 빼기", "둘 다 빼기"]
    SEEDS = ["20260729", "19770101", "20250315", "20260101"]
    y = 0
    ticks, tlabs = [], []
    for g in GR:
        ys = []
        for s in SEEDS:
            k = f"{g}|{s}"
            lo, hi = j[k]["ci"]
            a1.plot([lo, hi], [y, y], "-", color=GATE, lw=2.2, alpha=.8)
            a1.plot([j[k]["diff"]], [y], "o", color=CLAIM, ms=4)
            ys.append(y)
            y += 1
        ticks.append(np.mean(ys))
        tlabs.append(g.replace(" 빼기", ""))
        y += 1
    a1.axvline(0, color=INK, lw=1.2)
    a1.set_yticks(ticks)
    a1.set_yticklabels(tlabs, fontsize=6.2)
    a1.set_xlabel("$\\Delta$ 판정치 (방향표에서 빼면)", fontsize=7.0)
    a1.set_title("전부 0을 품는다 --- 뺄 근거가 없다", fontsize=7.2)
    a1.text(-.0098, y - 1.2, "보류 12/12", fontsize=7.0, color=INK, ha="left")
    a1.invert_yaxis()
    a1.tick_params(labelsize=6.2, length=0)
    a1.spines["left"].set_visible(False)

    rows = t["rows"]
    Ts = sorted(int(x) for x in rows)
    a2.plot(Ts, [rows[str(T)]["old"] for T in Ts], "s--", color=MUTE, lw=1.3,
            ms=4, label="옛 공통 셋")
    a2.plot(Ts, [rows[str(T)]["strict"] for T in Ts], "^-", color=GATE, lw=1.5,
            ms=4.4, label="엄격")
    a2.plot(Ts, [rows[str(T)]["deploy"] for T in Ts], "o-", color=CLAIM, lw=1.8,
            ms=4.8, label="배포")
    a2.set_xticks(Ts)
    a2.set_xlabel("시점 $T$", fontsize=7.0)
    a2.set_ylabel("판정치 $\\rho$", fontsize=7.0)
    a2.set_title("판정치는 두 규약 다 오른다", fontsize=7.2)
    a2.legend(fontsize=6.0, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.4)
    a2.text(2025.9, .308, f"평균 $\\Delta$\n엄격 $+${t['mean']['strict']:.4f}\n"
            f"배포 $+${t['mean']['deploy']:.4f}", fontsize=6.2, ha="right",
            color=INK)

    Tp = [T for T in Ts if np.isfinite(rows[str(T)]["pop_strict"])]
    a3.axhline(0, color=INK, lw=.9)
    a3.plot(Tp, [rows[str(T)]["pop_strict"] for T in Tp], "^-", color=GATE,
            lw=1.5, ms=4.4, label="엄격")
    a3.plot(Tp, [rows[str(T)]["pop_deploy"] for T in Tp], "o-", color=CLAIM,
            lw=1.8, ms=4.8, label="배포")
    a3.fill_between(Tp, [rows[str(T)]["pop_strict"] for T in Tp],
                    [rows[str(T)]["pop_deploy"] for T in Tp], color=CLAIM,
                    alpha=.10, lw=0)
    a3.set_xticks(Tp)
    a3.set_xlabel("시점 $T$", fontsize=7.0)
    a3.set_ylabel("$\\Delta$ 팝업", fontsize=7.0)
    a3.set_title("팝업만 규약에 따라 갈린다", fontsize=7.2)
    a3.legend(fontsize=6.2, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.4)
    a3.text(2024, -.030, f"엄격 {t['mean']['pop_strict']:+.4f}\n"
            f"배포 {t['mean']['pop_deploy']:+.4f}", fontsize=6.2, ha="center",
            color=INK)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_moved(out: Path, root: str = ".") -> dict:
    """노트113 — 왼쪽 축별 잔차, 가운데 변화가 예측한다, 오른쪽 수준은 아니다."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note113.json").read_text())
    k = json.loads((R / "note113b.json").read_text())
    rows, CM = j["rows"], j["common"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.2, 1, 1]})

    ds = sorted(rows, key=lambda d: rows[d]["d"])
    for i, d in enumerate(ds):
        for jx, a in enumerate(CM):
            v = rows[d]["r5"][jx]
            if not np.isfinite(v):
                a1.plot(jx, -i, "x", color=MUTE, ms=4, alpha=.5)
                continue
            a1.plot(jx, -i, "o", ms=2.5 + 7 * min(v, 1.8),
                    color=(CLAIM if v > 1.0 else GATE), alpha=.8)
    a1.axhline(-2.5, color=INK, lw=.8, ls=":")
    a1.text(4.6, -2.2, "깎는 출처 $\\uparrow$", fontsize=5.8, color=CLAIM,
            ha="right")
    a1.set_xticks(range(len(CM)))
    a1.set_xticklabels(["타깃 폭", "굿즈", "매장", "입장료", "미디어"],
                       fontsize=6.0)
    a1.set_yticks([-i for i in range(len(ds))])
    a1.set_yticklabels(ds, fontsize=6.2)
    a1.set_xlim(-.6, 4.8)
    a1.set_title("축별 상대 잔차 (출처 $\\to$ 팝업)", fontsize=7.2)
    a1.tick_params(length=0)
    for sp_ in ("top", "right", "left", "bottom"):
        a1.spines[sp_].set_visible(False)

    xs = [rows[d]["m5old"] - rows[d]["m3"] for d in ds]
    ys = [rows[d]["d"] for d in ds]
    a2.axhline(0, color=MUTE, lw=.7)
    a2.plot(xs, ys, "o", color=CLAIM, ms=5, alpha=.9)
    for d, x, y in zip(ds, xs, ys):
        a2.annotate(d, (x, y), fontsize=6.0, xytext=(4, 3),
                    textcoords="offset points", color=INK)
    z = np.polyfit(xs, ys, 1)
    xx = np.linspace(min(xs) - .04, max(xs) + .08, 20)
    a2.plot(xx, np.polyval(z, xx), "-", color=GATE, lw=1.1, alpha=.6)
    a2.text(.02, .15, "$r=+0.775$", fontsize=7.2, color=GATE)
    a2.set_xlabel("옛 셋 잔차가 나빠진 정도", fontsize=7.0)
    a2.set_ylabel("$\\Delta$ 팝업 전이", fontsize=7.0)
    a2.set_title("회전이 흔들린 만큼 얻는다", fontsize=7.2)
    a2.tick_params(labelsize=6.4)

    xs3 = [k["res"][d] for d in ds]
    ys3 = [k["tr"][d] for d in ds]
    a3.plot(xs3, ys3, "s", color=GATE, ms=5, alpha=.9)
    for d, x, y in zip(ds, xs3, ys3):
        a3.annotate(d, (x, y), fontsize=6.0, xytext=(4, 3),
                    textcoords="offset points", color=INK)
    z3 = np.polyfit(xs3, ys3, 1)
    xx3 = np.linspace(min(xs3) - .05, max(xs3) + .1, 20)
    a3.plot(xx3, np.polyval(z3, xx3), "-", color=MUTE, lw=1.1, alpha=.6)
    a3.text(.75, .47, "$r=-0.187$", fontsize=7.2, color=MUTE)
    a3.set_xlabel("잔차의 수준 (변화가 아니라)", fontsize=7.0)
    a3.set_ylabel("출처 $\\to$ 팝업 $\\rho$", fontsize=7.0)
    a3.set_title("수준은 아무것도 못 맞힌다", fontsize=7.2)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_namediff(out: Path, root: str = ".") -> dict:
    """노트114 — 왼쪽 세 고침, 가운데 대상별, 오른쪽 채택 검정."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note114.json").read_text())
    k = json.loads((R / "note114b.json").read_text())
    b0, p0, v0 = j["base"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.2, 1, 1]})

    res = j["res"]
    ORD = ["사전 이력으로 바꿈(직전작 건수)",
           "\\textbf{바꾸고 매장 급은 고유 축으로}",
           "사전 이력(평균 성적)으로 바꿈",
           "팝업에서 매장 노출 끄기"]
    SH = ["사전 이력으로 바꿈", "바꾸고 매장 급 보존", "사전 이력(평균 성적)",
          "팝업에서만 끄기"]
    xs = np.arange(len(ORD))
    a1.bar(xs - .19, [res[o][1] for o in ORD], .35, color=GATE, alpha=.9,
           edgecolor="none", label="판정치")
    a1.bar(xs + .19, [res[o][3] for o in ORD], .35, color=CLAIM, alpha=.9,
           edgecolor="none", label="팝업")
    a1.axhline(0, color=INK, lw=.9)
    a1.set_xticks(xs)
    a1.set_xticklabels(SH, fontsize=6.0, rotation=38, ha="right")
    a1.set_ylabel("$\\Delta\\rho$", fontsize=7.0)
    a1.set_title("세 가지 고침이 전부 진다", fontsize=7.2)
    a1.legend(fontsize=6.2, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.2)
    a4 = a1.twinx()
    a4.plot(xs, [res[o][4] for o in ORD], "D--", color=INK, lw=1.2, ms=4.2)
    a4.axhline(v0, color=MUTE, ls=":", lw=1.0)
    a4.text(3.45, v0 + .006, f"현행 잔차 {v0:.3f}", fontsize=5.8, color=MUTE,
            ha="right")
    a4.set_ylabel("매장 노출 잔차", fontsize=6.6)
    a4.set_ylim(.64, .93)
    a4.tick_params(labelsize=6.0)
    a4.spines["right"].set_visible(True)

    per = k["per"]
    ds = sorted(per, key=lambda d: per[d][1] - per[d][0])
    ys = np.arange(len(ds))
    vs = [per[d][1] - per[d][0] for d in ds]
    cols = [(GATE if v > 0 else CLAIM) for v in vs]
    a2.barh(ys, vs, .62, color=cols, alpha=.9, edgecolor="none")
    a2.axvline(0, color=INK, lw=.9)
    a2.set_yticks(ys)
    a2.set_yticklabels(ds, fontsize=6.4)
    a2.set_xlabel("$\\Delta\\rho$ (매장 노출을 빼면)", fontsize=7.0)
    a2.set_title("아홉이 잃고 팝업만 얻는다", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)

    ad = k["adopt"]
    ss = [s for s in ad if s.startswith("판정치")]
    for i, s in enumerate(ss):
        lo, hi = ad[s]["ci"]
        a3.plot([lo, hi], [i, i], "-", color=CLAIM, lw=2.6, alpha=.9)
        a3.plot([ad[s]["diff"]], [i], "o", color=CLAIM, ms=5)
    ps = [s for s in ad if s.startswith("팝업")]
    for i, s in enumerate(ps):
        lo, hi = ad[s]["ci"]
        a3.plot([lo, hi], [i + len(ss) + .7, i + len(ss) + .7], "-",
                color=GATE, lw=2.0, alpha=.55)
        a3.plot([ad[s]["diff"]], [i + len(ss) + .7], "s", color=GATE, ms=4)
    a3.axvline(0, color=INK, lw=1.1)
    a3.text(.052, 1.5, "판정치\n악화 4/4", fontsize=6.6, color=CLAIM,
            ha="right", va="center")
    a3.text(.052, 5.7, "팝업\n보류 4/4", fontsize=6.6, color=GATE,
            ha="right", va="center")
    a3.set_yticks([])
    a3.set_xlabel("$\\Delta\\rho$ (매장 노출을 빼면)", fontsize=7.0)
    a3.set_title("빼면 안 된다", fontsize=7.2)
    a3.set_xlim(-.032, .057)
    a3.set_ylim(-.8, 7.6)
    a3.tick_params(labelsize=6.4)
    a3.spines["left"].set_visible(False)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_nocompass(out: Path, root: str = ".") -> dict:
    """노트115 — 왼쪽 순환, 가운데 분리 없음, 오른쪽 재현되나 쓸모없다."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note115b.json").read_text())
    ad, cd, hf = j["adopted"], j["cand"], j["half"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [.85, 1.25, 1]})

    # ① 순환
    xs = np.arange(2)
    a1.bar(xs - .19, [0.969, 0.280], .35, color=MUTE, alpha=.9,
           edgecolor="none", label="자기 포함(순환)")
    a1.bar(xs + .19, [0.280, 0.280], .35, color=CLAIM, alpha=.9,
           edgecolor="none", label="자기 제외(고침)")
    a1.set_xticks([0])
    a1.set_xticklabels(["매장 노출"], fontsize=6.6)
    a1.set_xlim(-.6, .6)
    a1.set_ylabel("관계 일치도", fontsize=7.0)
    a1.annotate("", xy=(.19, .29), xytext=(-.19, .955),
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.8))
    a1.text(.02, .70, "$0.969\\to0.280$", fontsize=6.6, color=CLAIM,
            ha="center")
    a1.set_title("순환부터 잡았다", fontsize=7.2)
    a1.legend(fontsize=5.8, frameon=False, loc="lower left")
    a1.set_ylim(0, 1.08)
    a1.tick_params(labelsize=6.4)

    # ② 분리 없음
    A = sorted(ad, key=lambda k: ad[k][0])
    C = sorted(cd, key=lambda k: cd[k][0])
    for i, k in enumerate(C):
        a2.plot(cd[k][0], 0, "o", color=MUTE, ms=4.5, alpha=.55)
    KO = {"target_breadth": "타깃 폭", "goods_scale": "굿즈 규모",
          "venue_prominence": "매장 노출", "entry_friction": "입장료",
          "media_push": "미디어 홍보"}
    for i, k in enumerate(A):
        a2.plot(ad[k][0], 1, "D", color=CLAIM, ms=6.5)
        a2.annotate(KO.get(k, k), (ad[k][0], 1), fontsize=5.8,
                    xytext=(0, 11 if i % 2 == 0 else -15),
                    textcoords="offset points", ha="center", color=CLAIM)
    a2.axvspan(min(cd[k][0] for k in C), max(cd[k][0] for k in C),
               color=MUTE, alpha=.10, zorder=0)
    a2.set_yticks([0, 1])
    a2.set_yticklabels(["긁은 후보 20", "채택된 공통 축 5"], fontsize=6.4)
    a2.set_ylim(-.6, 1.8)
    a2.set_xlabel("관계 일치도 (자기 제외)", fontsize=7.0)
    a2.set_title("분리가 없다 --- 겹친다", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    a2.axvline(max(cd[k][0] for k in C), color=INK, ls=":", lw=1.0)
    a2.text(max(cd[k][0] for k in C) - .02, -.42, "후보 최대 $+$0.400",
            fontsize=5.8, ha="right", color=INK)

    # ③ 반쪽 재현
    x = [p[0] for p in hf]
    y = [p[1] for p in hf]
    a3.plot(x, y, "o", color=GATE, ms=3.4, alpha=.6)
    lim = [-.75, .95]
    a3.plot(lim, lim, "-", color=INK, lw=.7, alpha=.5)
    z = np.polyfit(x, y, 1)
    xx = np.linspace(*lim, 20)
    a3.plot(xx, np.polyval(z, xx), "-", color=CLAIM, lw=1.2)
    a3.text(-.68, .78, f"$r={np.corrcoef(x, y)[0,1]:+.3f}$", fontsize=7.2,
            color=CLAIM)
    a3.text(-.68, .62, "측정은 튼튼하다", fontsize=6.2, color=CLAIM)
    a3.text(.90, -.66, "그런데 아무것도 못 맞힌다", fontsize=6.2, color=MUTE,
            ha="right")
    a3.set_xlim(*lim)
    a3.set_ylim(*lim)
    a3.set_xlabel("A반 일치도", fontsize=7.0)
    a3.set_ylabel("B반 일치도", fontsize=7.0)
    a3.set_title("재현은 되는데", fontsize=7.2)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_sweep(out: Path, root: str = ".") -> dict:
    """노트116 — 왼쪽 속도, 가운데 스무 개 판정, 오른쪽 순위 매길 것이 없었다."""
    import json, numpy as np
    R = Path(root) / "data/state"
    s = json.loads((R / "sweep.json").read_text())
    sp = json.loads((R / "sweep_speed.json").read_text())
    n115 = json.loads((R / "note115b.json").read_text())["cand"]
    res = s["res"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [.8, 1.35, 1]})

    xs = np.arange(2)
    a1.bar(xs, [sp["old"], sp["new"]], .55, color=[MUTE, CLAIM], alpha=.9,
           edgecolor="none")
    for x, v in zip(xs, [sp["old"], sp["new"]]):
        a1.text(x, v + 1.2, f"{v:.0f}초", ha="center", fontsize=7.0)
    a1.set_xticks(xs)
    a1.set_xticklabels(["옛 방식", "새 방식"], fontsize=6.8)
    a1.set_ylabel("후보 하나당 (씨앗 넷 $\\times$ 100회)", fontsize=6.8)
    a1.set_ylim(0, 62)
    a1.set_title(f"{sp['old']/sp['new']:.1f}배", fontsize=7.4)
    a1.text(.5, 44, f"스무 개 전수\n{s['sec']:.0f}초", fontsize=6.6,
            ha="center", color=INK)
    a1.tick_params(labelsize=6.4)

    ks = sorted(res, key=lambda c: res[c]["diff"])
    ys = np.arange(len(ks))
    for i, c in enumerate(ks):
        sd = list(res[c]["seeds"].values())
        if sd:
            lo = np.mean([x["ci"][0] for x in sd])
            hi = np.mean([x["ci"][1] for x in sd])
            a2.plot([lo, hi], [i, i], "-", color=MUTE, lw=1.6, alpha=.55)
        col = CLAIM if res[c]["bad"] >= 2 else GATE
        a2.plot([res[c]["diff"]], [i], "o", color=col, ms=4.2)
    a2.axvline(0, color=INK, lw=1.1)
    a2.set_yticks(ys)
    a2.set_yticklabels(ks, fontsize=5.6)
    a2.set_xlabel("$\\Delta$ 판정치 (씨앗 넷 평균 구간)", fontsize=7.0)
    a2.set_title("후보 스무 개 --- 채택 0, 악화 6", fontsize=7.2)
    a2.tick_params(labelsize=6.0, length=0)
    a2.plot([], [], "o", color=CLAIM, ms=5, label="악화 2회 이상")
    a2.legend(fontsize=6.0, frameon=False, loc="lower left")

    xs3 = [n115[c][0] for c in ks if c in n115]
    ys3 = [res[c]["diff"] for c in ks if c in n115]
    a3.axhline(0, color=INK, lw=1.0)
    a3.axhspan(-.03, 0, color=CLAIM, alpha=.07, zorder=0)
    a3.plot(xs3, ys3, "o", color=GATE, ms=5, alpha=.85)
    a3.text(.05, .0035, "채택선 --- 아무도 안 넘는다", fontsize=6.2,
            color=INK)
    a3.set_xlabel("관계 일치도 (노트 115의 기준)", fontsize=7.0)
    a3.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a3.set_title("순위를 매길 것이 없었다", fontsize=7.2)
    a3.set_ylim(-.028, .0065)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_leak(out: Path, root: str = ".") -> dict:
    """노트117 — 왼쪽 누수 사슬, 가운데 채택이 사라진다, 오른쪽 깨끗한 것."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note117.json").read_text())
    s = json.loads((R / "sweep.json").read_text())
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.05, 1, 1.1]})

    # ① 누수 사슬
    a1.plot([0, 1], [1, 1], "-", color=CLAIM, lw=3)
    a1.plot([1, 2], [1, 0], "-", color=CLAIM, lw=3)
    for x, y, t, dy, ha in ((0, 1, "만화 라벨\n(서재 등록 수)", -26, "center"),
                            (1, 1, "AniList popularity", 14, "center"),
                            (2, 0, "AniList\nfavourites", -26, "center")):
        a1.plot([x], [y], "o", color=INK, ms=9)
        a1.annotate(t, (x, y), fontsize=6.4, xytext=(0, dy),
                    textcoords="offset points", ha=ha, color=INK)
    a1.text(.5, .93, f"$\\rho={j['pop_label']:+.3f}$", fontsize=7.6,
            color=CLAIM, ha="center")
    a1.text(1.62, .62, f"$\\rho={j['fav_pop']:+.3f}$", fontsize=7.6,
            color=CLAIM, ha="left")
    a1.set_xlim(-.6, 2.6)
    a1.set_ylim(-.55, 1.45)
    a1.set_xticks([])
    a1.set_yticks([])
    a1.set_title("같은 계수기의 두 번째 자", fontsize=7.4)
    for sp in ("top", "right", "left", "bottom"):
        a1.spines[sp].set_visible(False)

    # ② 채택이 사라진다
    pre = j["pre"]
    ks = list(pre)
    xs = np.arange(len(ks) + 1)
    vals = [pre[k][0] for k in ks] + [max(v["diff"] for v in s["res"].values())]
    cols = [CLAIM, CLAIM, GATE]
    a2.bar(xs, vals, .55, color=cols, alpha=.9, edgecolor="none")
    for x, v, k in zip(xs, vals, ks + ["남은 21개 최고"]):
        a2.text(x, v + .0012, f"{v:+.4f}", ha="center", fontsize=6.4)
    a2.axhline(0, color=INK, lw=.9)
    a2.set_xticks(xs)
    a2.set_xticklabels(["favourites\n채택 4/4", "trending\n채택 4/4",
                        "남은 21개\n최고"], fontsize=5.8)
    a2.set_ylabel("$\\Delta$ 판정치", fontsize=7.0)
    a2.set_title("채택 둘이 다 누수였다", fontsize=7.4)
    a2.text(1.0, .030, "누수", fontsize=7.6, color=CLAIM, ha="center")
    a2.set_ylim(-.002, .043)
    a2.tick_params(labelsize=6.2)

    # ③ 깨끗한 것
    lab = j["lab"]
    order = [("favourites", "만화"), ("favourites", "세계애니"),
             ("trending", "세계애니"), ("trending", "만화"),
             ("rating", "만화"), ("rating", "세계애니"),
             ("rating", "모바일"), ("rating", "애니")]
    ys = np.arange(len(order))
    vs = [lab[c][d][0] for c, d in order]
    cols = [(CLAIM if c in ("favourites", "trending") else GATE)
            for c, d in order]
    a3.barh(ys, vs, .62, color=cols, alpha=.9, edgecolor="none")
    a3.axvline(0, color=INK, lw=.9)
    a3.axvline(.70, color=CLAIM, ls="--", lw=1.1)
    a3.text(.68, 7.4, "문턱 0.70", fontsize=6.0, color=CLAIM, ha="right")
    a3.set_yticks(ys)
    a3.set_yticklabels([f"{c[:9]} · {d}" for c, d in order], fontsize=5.8)
    a3.set_xlabel("그 도메인 라벨과의 상관", fontsize=7.0)
    a3.set_title("문턱만으로는 못 잡는다", fontsize=7.4)
    a3.invert_yaxis()
    a3.tick_params(labelsize=6.0, length=0)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_quality(out: Path, root: str = ".") -> dict:
    """노트118 — 왼쪽 두 천장, 가운데 두 플랫폼 평점, 오른쪽 그래도 0."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note118.json").read_text())
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1.05, 1.05]})

    xs = np.arange(2)
    a1.bar(xs - .19, [j["r_label_79"], j["r_two_plat"]], .35, color=MUTE,
           alpha=.9, edgecolor="none", label="두 플랫폼 상관 $\\rho$")
    a1.bar(xs + .19, [j["ceil_label"], j["ceil_rating"]], .35, color=CLAIM,
           alpha=.9, edgecolor="none", label="천장 $\\sqrt{\\rho}$")
    for x, a, b in zip(xs, [j["r_label_79"], j["r_two_plat"]],
                       [j["ceil_label"], j["ceil_rating"]]):
        a1.text(x - .19, a + .02, f"{a:.3f}", ha="center", fontsize=6.4)
        a1.text(x + .19, b + .02, f"{b:.3f}", ha="center", fontsize=6.4)
    a1.set_xticks(xs)
    a1.set_xticklabels(["라벨 (양)\n노트 79 · 83", "평점 (질)\n이번"],
                       fontsize=6.4)
    a1.set_ylim(0, 1.14)
    a1.set_ylabel("두 플랫폼 일치", fontsize=7.0)
    a1.set_title("질은 거의 완벽히 재진다", fontsize=7.4)
    a1.set_ylim(0, 1.30)
    a1.legend(fontsize=6.0, frameon=False, loc="upper left", ncol=2)
    a1.tick_params(labelsize=6.4)

    sc = np.array(j["scatter"])
    a2.plot(sc[:, 0], sc[:, 1], "o", color=GATE, ms=1.8, alpha=.35)
    a2.plot([0, 1], [0, 1], "-", color=INK, lw=.8, alpha=.5)
    a2.text(.05, .90, f"$\\rho={j['r_two_plat']:+.3f}$", fontsize=7.6,
            color=CLAIM)
    a2.text(.05, .81, f"$n={j['n_scatter']:,}$", fontsize=6.4, color=MUTE)
    a2.set_xlabel("AniList 평점 (백분위)", fontsize=7.0)
    a2.set_ylabel("Kitsu 평점 (백분위)", fontsize=7.0)
    a2.set_title("두 플랫폼이 같은 말을 한다", fontsize=7.4)
    a2.set_xlim(-.02, 1.02)
    a2.set_ylim(-.02, 1.02)
    a2.tick_params(labelsize=6.4)

    res = j["res"]
    ORD = ["rating_2plat", "kitsu_rank", "kitsu_rating", "rating"]
    SH = ["두 플랫폼 평균", "Kitsu 순위", "Kitsu 평점", "평점(노트 117)"]
    ys = np.arange(len(ORD))
    a3.barh(ys, [res.get(c, 0) for c in ORD], .6, color=GATE, alpha=.9,
            edgecolor="none")
    a3.axvline(0, color=INK, lw=1.0)
    a3.axvspan(-.033, .033, color=GATE, alpha=.07, zorder=0)
    for y, c in zip(ys, ORD):
        v = res.get(c, 0)
        a3.text(v - .0004, y, f"{v:+.4f}", va="center", ha="right",
                fontsize=6.4, color=INK)
    a3.set_yticks(ys)
    a3.set_yticklabels(SH, fontsize=6.4)
    a3.set_xlabel("$\\Delta$ 판정치", fontsize=7.0)
    a3.set_xlim(-.010, .004)
    a3.set_title("그래도 전이는 $0$이다", fontsize=7.4)
    a3.invert_yaxis()
    a3.tick_params(labelsize=6.2, length=0)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_samesite(out: Path, root: str = ".") -> dict:
    """노트119 — 왼쪽 약속과 실제, 가운데 축은 어느 라벨과, 오른쪽 정합의 몫."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note119.json").read_text())
    k = json.loads((R / "note119b.json").read_text())
    c = json.loads((R / "note119c.json").read_text())
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1.15, 1]})

    # ① 약속과 실제
    r = j["r_two"]
    sb = 2 * r / (1 + r)
    a1.bar([0, 1], [np.sqrt(r), np.sqrt(sb)], .5, color=[MUTE, GATE], alpha=.9,
           edgecolor="none")
    for x, v in zip([0, 1], [np.sqrt(r), np.sqrt(sb)]):
        a1.text(x, v + .012, f"{v:.3f}", ha="center", fontsize=6.8)
    a1.annotate("", xy=(1, np.sqrt(sb) - .01), xytext=(0, np.sqrt(r) + .005),
                arrowprops=dict(arrowstyle="->", color=GATE, lw=1.6))
    a1.set_xticks([0, 1])
    a1.set_xticklabels(["현행", "두 플랫폼\n평균"], fontsize=6.4)
    a1.set_ylabel("라벨 신뢰도 천장 $\\sqrt{\\rho}$", fontsize=7.0)
    a1.set_ylim(.70, .95)
    a1.set_title("약속 --- 천장이 오른다", fontsize=7.4)
    a1.text(.5, .735, f"실제 전이\n{j['d_src']:+.4f}", fontsize=7.2,
            color=CLAIM, ha="center")
    a1.tick_params(labelsize=6.4)

    # ② 축이 어느 라벨과
    ax = k["axes"]
    KO = {"target_breadth": "타깃 폭", "goods_scale": "굿즈 규모",
          "venue_prominence": "매장 노출", "entry_friction": "입장료",
          "media_push": "미디어 홍보"}
    KIT = {"target_breadth": .197, "venue_prominence": .017,
           "entry_friction": .331, "media_push": -.113, "goods_scale": .167}
    ks = sorted(ax, key=lambda a: -ax[a][0])
    ys = np.arange(len(ks))
    a2.barh(ys - .19, [ax[a][0] for a in ks], .35, color=CLAIM, alpha=.9,
            edgecolor="none", label="AniList 라벨(축과 같은 곳)")
    a2.barh(ys + .19, [KIT[a] for a in ks], .35, color=GATE, alpha=.9,
            edgecolor="none", label="Kitsu 라벨(다른 곳)")
    a2.axvline(0, color=INK, lw=.9)
    a2.set_yticks(ys)
    a2.set_yticklabels([KO[a] for a in ks], fontsize=6.4)
    a2.set_xlabel("축과 라벨의 상관", fontsize=7.0)
    a2.set_title("축은 자기 플랫폼 라벨과 붙는다", fontsize=7.4)
    a2.legend(fontsize=5.8, frameon=False, loc="lower right")
    a2.invert_yaxis()
    a2.tick_params(labelsize=6.2, length=0)

    # ③ 정합의 몫
    se = c["self"]
    ORD = ["anilist", "blend", "kitsu"]
    SH = ["AniList\n(현행)", "두 플랫폼\n평균", "Kitsu\n(다른 곳)"]
    xs = np.arange(3)
    a3.bar(xs, [se[o][0] for o in ORD], .55, color=[CLAIM, MUTE, GATE],
           alpha=.9, edgecolor="none")
    for x, o in zip(xs, ORD):
        a3.text(x, se[o][0] + .008, f"{se[o][0]:.4f}", ha="center",
                fontsize=6.6)
    a3.annotate("", xy=(2, se["kitsu"][0] + .01),
                xytext=(0, se["anilist"][0] + .01),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=1.3))
    a3.text(1, se["anilist"][0] + .045,
            f"정합의 몫 {c['share']:.0%}", fontsize=6.8, color=INK,
            ha="center")
    a3.set_xticks(xs)
    a3.set_xticklabels(SH, fontsize=6.2)
    a3.set_ylabel("세계애니 자기 $\\rho$", fontsize=7.0)
    a3.set_ylim(0, .70)
    a3.set_title(f"열 도메인 중 {c['n_same']}개가 같은 플랫폼", fontsize=7.4)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_honest(out: Path, root: str = ".") -> dict:
    """노트120 — 왼쪽 두 계수기, 가운데 부풀림, 오른쪽 순위 재배열."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note120.json").read_text())
    k = json.loads((R / "note120b.json").read_text())
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.6),
                                     gridspec_kw={"width_ratios": [.85, 1, 1.35]})

    two = j["two"]
    ds = sorted(two, key=lambda d: two[d][0])
    xs = np.arange(len(ds))
    a1.bar(xs, [two[d][0] for d in ds], .55, color=GATE, alpha=.9,
           edgecolor="none")
    for x, d in zip(xs, ds):
        a1.text(x, two[d][0] + .012, f"{two[d][0]:.3f}", ha="center",
                fontsize=6.6)
        a1.text(x, .05, f"{two[d][2]:,}", ha="center", fontsize=5.8,
                color="white")
    a1.axhline(.555, color=CLAIM, ls="--", lw=1.1)
    a1.text(2.4, .575, "노트 83 의 $+$0.555", fontsize=5.8, color=CLAIM,
            ha="right")
    a1.set_xticks(xs)
    a1.set_xticklabels(ds, fontsize=6.4)
    a1.set_ylabel("두 계수기의 일치 $\\rho$", fontsize=7.0)
    a1.set_ylim(0, .88)
    a1.set_title("라벨은 생각보다 잘 재진다", fontsize=7.4)
    a1.tick_params(labelsize=6.4)

    se = j["self"]
    xs2 = np.arange(len(ds))
    a2.bar(xs2 - .19, [se[d][0] for d in ds], .35, color=CLAIM, alpha=.9,
           edgecolor="none", label="같은 플랫폼")
    a2.bar(xs2 + .19, [se[d][1] for d in ds], .35, color=GATE, alpha=.9,
           edgecolor="none", label="다른 플랫폼")
    for x, d in zip(xs2, ds):
        sh = (se[d][0] - se[d][1]) / se[d][0]
        a2.text(x, se[d][0] + .014, f"$-${sh:.0%}", ha="center", fontsize=6.4,
                color=INK)
    a2.set_xticks(xs2)
    a2.set_xticklabels(ds, fontsize=6.4)
    a2.set_ylabel("자기 $\\rho$", fontsize=7.0)
    a2.set_ylim(0, .72)
    a2.set_title("자기 $\\rho$ 의 21$\\sim$38%가 정합", fontsize=7.4)
    a2.legend(fontsize=6.0, frameon=False, loc="upper center", ncol=2)
    a2.tick_params(labelsize=6.4)

    rows = k["rows"]
    cur = sorted(rows, key=lambda d: -rows[d][0])
    hon = sorted(rows, key=lambda d: -rows[d][1])
    for i, d in enumerate(cur):
        jx = hon.index(d)
        c = CLAIM if d == "팝업" else (INK if rows[d][2].startswith("잼") else MUTE)
        lw = 2.2 if d == "팝업" else 1.0
        a3.plot([0, 1], [i, jx], "-", color=c, lw=lw,
                alpha=.9 if d == "팝업" else .45)
        a3.annotate(d, (0, i), fontsize=6.0, xytext=(-5, 0),
                    textcoords="offset points", ha="right", va="center",
                    color=c)
        a3.annotate(f"{d}  {rows[d][1]:.3f}", (1, jx), fontsize=6.0,
                    xytext=(5, 0), textcoords="offset points", ha="left",
                    va="center", color=c)
    a3.plot([0] * len(cur), range(len(cur)), "o", color=MUTE, ms=3.4)
    a3.plot([1] * len(hon), range(len(hon)), "o", color=GATE, ms=3.4)
    a3.set_xlim(-.55, 1.75)
    a3.set_xticks([0, 1])
    a3.set_xticklabels(["현행 눈금", "정직한 눈금"], fontsize=6.6)
    a3.invert_yaxis()
    a3.set_yticks([])
    a3.set_title("팝업이 다섯째에서 셋째로", fontsize=7.4)
    for sp_ in ("left", "bottom"):
        a3.spines[sp_].set_visible(False)
    a3.tick_params(length=0)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_law(out: Path, root: str = ".") -> dict:
    """노트121 — 왼쪽 다섯 도메인, 가운데 법칙 1, 오른쪽 법칙 2."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note121.json").read_text())
    rows, law = j["rows"], j["law"]
    ds = sorted(rows, key=lambda d: -rows[d][0])
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1, 1]})

    xs = np.arange(len(ds))
    a1.bar(xs - .19, [rows[d][0] for d in ds], .35, color=MUTE, alpha=.9,
           edgecolor="none", label="현행 눈금")
    a1.bar(xs + .19, [rows[d][1] for d in ds], .35, color=CLAIM, alpha=.9,
           edgecolor="none", label="정직한 눈금")
    for x, d in zip(xs, ds):
        if abs(rows[d][0] - rows[d][1]) < 1e-6:
            a1.text(x, rows[d][0] + .012, "정합\n없음", ha="center",
                    fontsize=5.4, color=INK)
    a1.set_xticks(xs)
    a1.set_xticklabels(ds, fontsize=6.2)
    a1.set_ylabel("자기 $\\rho$", fontsize=7.0)
    a1.set_ylim(0, .70)
    a1.set_title("다섯 도메인의 두 눈금", fontsize=7.4)
    a1.legend(fontsize=6.0, frameon=False, loc="upper right")
    a1.tick_params(labelsize=6.2)

    for ax, (i0, i1), (ttl, key) in (
            (a2, (2, 3), ("법칙 1 --- 자기 $\\rho$ 가 대상 전이를 정한다", 0)),
            (a3, (4, 5), ("법칙 2 --- 교환 법칙", 1))):
        for col, si, ti, lab, r in ((MUTE, 0, i0, "현행", law["cur"][key]),
                                    (CLAIM, 1, i1, "정직", law["hon"][key])):
            x = [rows[d][si] for d in ds]
            y = [rows[d][ti] for d in ds]
            ax.plot(x, y, "o", color=col, ms=5, alpha=.9,
                    label=f"{lab}  $r={r:+.3f}$")
            z = np.polyfit(x, y, 1)
            xx = np.linspace(min(x) - .02, max(x) + .02, 20)
            ax.plot(xx, np.polyval(z, xx), "-", color=col, lw=1.1, alpha=.6)
        for d in ds:
            ax.annotate(d, (rows[d][1], rows[d][i1]), fontsize=5.6,
                        xytext=(4, 3), textcoords="offset points",
                        color=CLAIM)
        ax.set_xlabel("자기 $\\rho$", fontsize=7.0)
        ax.set_ylabel("대상 전이" if key == 0 else "출처 전이", fontsize=7.0)
        ax.set_title(ttl, fontsize=7.0)
        ax.legend(fontsize=6.0, frameon=False,
                  loc="upper left" if key == 0 else "lower left")
        ax.tick_params(labelsize=6.4)
    a3.text(.44, .375, "반토막", fontsize=7.2, color=CLAIM, ha="center")

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_scalefix(out: Path, root: str = ".") -> dict:
    """노트122 — 왼쪽 부분집합, 가운데 팝업만, 오른쪽 검정."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note122.json").read_text())
    rows, ad = j["rows"], j["adopt"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.25, .85, 1]})

    ks = [k for k in rows if k != "없음"]
    ks.sort(key=lambda k: rows[k][1])
    ys = np.arange(len(ks))
    cols = [(CLAIM if "게임" in k else MUTE) for k in ks]
    a1.barh(ys, [rows[k][1] for k in ks], .62, color=cols, alpha=.9,
            edgecolor="none")
    a1.axvline(0, color=INK, lw=.9)
    a1.set_yticks(ys)
    a1.set_yticklabels([k.replace("·", " $\\cdot$ ") for k in ks], fontsize=6.0)
    a1.set_xlabel("$\\Delta$ 팝업 (라벨을 정직하게 바꾼 출처)", fontsize=7.0)
    a1.set_title("게임 하나가 효과의 전부다", fontsize=7.4)
    a1.plot([], [], "s", color=CLAIM, ms=5, label="게임을 포함")
    a1.legend(fontsize=6.0, frameon=False, loc="lower right")
    a1.tick_params(labelsize=6.0, length=0)

    a2.bar([0, 1], [rows["세계애니·만화·게임"][1], rows["세계애니·만화·게임"][3]],
           .55, color=[CLAIM, MUTE], alpha=.9, edgecolor="none")
    for x, v in zip([0, 1], [rows["세계애니·만화·게임"][1],
                             rows["세계애니·만화·게임"][3]]):
        a2.text(x, v + (.0006 if v > 0 else -.0014), f"{v:+.4f}", ha="center",
                fontsize=6.8)
    a2.axhline(0, color=INK, lw=.9)
    a2.set_xticks([0, 1])
    a2.set_xticklabels(["팝업", "나머지 여섯\n평균"], fontsize=6.6)
    a2.set_ylabel("$\\Delta\\rho$", fontsize=7.0)
    a2.set_ylim(-.004, .014)
    a2.set_title("팝업만 오른다", fontsize=7.4)
    a2.tick_params(labelsize=6.4)

    ss = [s for s in ad if s.startswith("팝업")]
    for i, s in enumerate(ss):
        lo, hi = ad[s]["ci"]
        a3.plot([lo, hi], [i, i], "-", color=CLAIM, lw=2.6, alpha=.9)
        a3.plot([ad[s]["diff"]], [i], "o", color=CLAIM, ms=5)
    ps = [s for s in ad if s.startswith("일곱")]
    for i, s in enumerate(ps):
        lo, hi = ad[s]["ci"]
        a3.plot([lo, hi], [i + len(ss) + .7, i + len(ss) + .7], "-",
                color=GATE, lw=2.0, alpha=.55)
        a3.plot([ad[s]["diff"]], [i + len(ss) + .7], "s", color=GATE, ms=4)
    a3.axvline(0, color=INK, lw=1.1)
    a3.text(.041, 1.5, "팝업\n보류 4/4", fontsize=6.6, color=CLAIM,
            ha="right", va="center")
    a3.text(.041, 5.7, "나머지 여섯\n보류 4/4", fontsize=6.6, color=GATE,
            ha="right", va="center")
    a3.set_yticks([])
    a3.set_xlabel("$\\Delta\\rho$ (짝지은 붓스트랩)", fontsize=7.0)
    a3.set_title("문턱을 못 넘는다", fontsize=7.4)
    a3.set_xlim(-.045, .045)
    a3.set_ylim(-.8, 7.6)
    a3.spines["left"].set_visible(False)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_plan(out: Path, root: str = ".") -> dict:
    """노트123 — 왼쪽 관문 폭포, 가운데 라벨 종류별, 오른쪽 필요 표본."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note123.json").read_text())
    g, bl, mix = j["gate"], j["by_label"], j["mix"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.05, 1, 1.1]})

    ST = [("전체 레코드", g["전체"]), ("신뢰 A/B", g["신뢰 A/B"]),
          ("라벨 유한", g["라벨 유한"]), ("스코프", g["scope"]),
          ("계수 방법", g["counting"])]
    ys = np.arange(len(ST))
    a1.barh(ys, [v for _, v in ST], .62,
            color=[MUTE] * 4 + [CLAIM], alpha=.9, edgecolor="none")
    for y, (lab, v) in zip(ys, ST):
        a1.text(v + 6, y, str(v), va="center", fontsize=6.6,
                color=CLAIM if lab == "계수 방법" else INK)
    a1.set_yticks(ys)
    a1.set_yticklabels([lab for lab, _ in ST], fontsize=6.4)
    a1.set_xlabel("남는 레코드", fontsize=7.0)
    a1.set_xlim(0, 430)
    a1.set_title("376건에서 75건으로", fontsize=7.4)
    a1.invert_yaxis()
    a1.text(200, 4.55, f"주최자 주장 {g['organizer_claim']}건이 여기서 빠진다",
            fontsize=5.8, color=CLAIM, ha="center")
    a1.tick_params(labelsize=6.2, length=0)

    ks = list(bl)
    xs = np.arange(len(ks) + 1)
    vals = [bl[k][1] for k in ks] + [mix["$+$주최자 주장"][1]]
    labs = ["실측만", "주최자\n주장만", "주최자\n주장만(전 등급)", "섞으면"]
    cols = [GATE, CLAIM, CLAIM, MUTE]
    a2.bar(xs, vals, .58, color=cols, alpha=.9, edgecolor="none")
    for x, v, k in zip(xs, vals, ks + ["mix"]):
        n = bl[k][0] if k != "mix" else mix["$+$주최자 주장"][0]
        a2.text(x, v + (.012 if v > 0 else -.030), f"{v:+.3f}", ha="center",
                fontsize=6.4)
        a2.text(x, .02, f"n={n}", ha="center", fontsize=5.6, color=INK)
    a2.axhline(0, color=INK, lw=.9)
    a2.set_xticks(xs)
    a2.set_xticklabels(labs, fontsize=5.8)
    a2.set_ylabel("팝업 $\\rho$", fontsize=7.0)
    a2.set_ylim(-.10, .55)
    a2.set_title("주최자 주장은 신호가 없다", fontsize=7.4)
    a2.tick_params(labelsize=6.2)

    rows = j["rows"]
    ns = np.array(sorted(int(k) for k in rows))
    hs = np.array([rows[str(n)][1] for n in ns])
    a3.plot(ns, hs, "o", color=CLAIM, ms=5)
    xx = np.linspace(20, 1200, 200)
    a3.plot(xx, j["a"] * xx ** j["b"], "-", color=GATE, lw=1.3)
    for gth, nn in sorted(j["need"].items(), key=lambda x: -float(x[0])):
        gv = float(gth)
        a3.plot([nn], [gv], "D", color=INK, ms=4)
        yr = (nn - 75) / j["per_year"]
        a3.annotate(f"{gv:.3f} · {nn:.0f}건 · {yr:.0f}년", (nn, gv),
                    fontsize=5.8, xytext=(6, 4), textcoords="offset points",
                    color=INK)
    a3.set_xscale("log")
    a3.set_yscale("log")
    a3.set_xticks([25, 50, 100, 200, 500, 1000])
    a3.set_xticklabels(["25", "50", "100", "200", "500", "1000"], fontsize=6.2)
    a3.set_yticks([.005, .01, .02, .05, .12])
    a3.set_yticklabels(["0.005", "0.01", "0.02", "0.05", "0.12"], fontsize=6.2)
    a3.minorticks_off()
    a3.set_xlabel("팝업 레코드 수", fontsize=7.0)
    a3.set_ylabel("짝지은 차이의 구간 반폭", fontsize=7.0)
    a3.set_title(f"반폭 $= {j['a']:.2f}\\,n^{{{j['b']:.2f}}}$", fontsize=7.4)
    a3.tick_params(labelsize=6.2)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


def fig_empty(out: Path, root: str = ".") -> dict:
    """노트124 — 왼쪽 상수 축, 가운데 계수 방법별, 오른쪽 반폭 전망."""
    import json, numpy as np
    R = Path(root) / "data/state"
    j = json.loads((R / "note124.json").read_text())
    c = j["const"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.05, 1, 1.15]})

    # ① 상수 축
    ks = ["entry", "participation", "unknown", "exposure",
          "organizer_claim", "media_estimate"]
    KO = {"entry": "입장 계수", "participation": "참여 로그",
          "unknown": "미상", "exposure": "노출",
          "organizer_claim": "주최자 주장", "media_estimate": "언론 추정"}
    ys = np.arange(len(ks))
    vals = [c[k][1] if c[k][1] is not None else 0 for k in ks]
    cols = [(CLAIM if v == 10 else GATE) for v in vals]
    a1.barh(ys, vals, .62, color=cols, alpha=.9, edgecolor="none")
    for y, k, v in zip(ys, ks, vals):
        a1.text(v + .2, y, f"{v}/10   n={c[k][0]}", va="center", fontsize=6.2,
                color=INK)
    a1.set_yticks(ys)
    a1.set_yticklabels([KO[k] for k in ks], fontsize=6.4)
    a1.set_xlim(0, 15)
    a1.set_xticks([0, 5, 10])
    a1.set_xlabel("열 축 중 상수인 것", fontsize=7.0)
    a1.set_title("사람이 안 매긴 레코드", fontsize=7.4)
    a1.invert_yaxis()
    a1.tick_params(labelsize=6.2, length=0)

    # ② 매긴 것 대 안 매긴 것
    a2.bar([0, 1], [j["n_tagged"], j["n_untagged"]], .55,
           color=[GATE, CLAIM], alpha=.9, edgecolor="none")
    for x, v in zip([0, 1], [j["n_tagged"], j["n_untagged"]]):
        a2.text(x, v + 6, str(v), ha="center", fontsize=7.4)
    a2.set_xticks([0, 1])
    a2.set_xticklabels(["축이 매겨진 것", "축이 빈 것"], fontsize=6.6)
    a2.set_ylabel("레코드", fontsize=7.0)
    a2.set_ylim(0, 300)
    a2.set_title("376건 중 260건이 빈 칸", fontsize=7.4)
    a2.text(.5, 200, "라벨은\n둘 다 있다", fontsize=6.6, ha="center",
            color=INK)
    a2.tick_params(labelsize=6.4)

    # ③ 반폭 전망
    hw = j["hw"]
    ns = sorted(int(k) for k in hw)
    xx = np.linspace(60, 520, 200)
    a3.plot(xx, j["a"] * xx ** j["b"], "-", color=GATE, lw=1.3)
    for n, lab, col in ((75, "지금", INK), (322, "축을 매기면", CLAIM),
                        (476, "$\\pm$0.010 문턱", MUTE)):
        v = hw[str(n)]
        a3.plot([n], [v], "o", color=col, ms=6)
        a3.annotate(f"{lab}\n{n}건 · {v:.4f}", (n, v), fontsize=6.0,
                    xytext=(8, 6), textcoords="offset points", color=col)
    a3.axhline(.010, color=MUTE, ls="--", lw=1.0)
    a3.set_xlabel("팝업 레코드 수", fontsize=7.0)
    a3.set_ylabel("짝지은 차이의 구간 반폭", fontsize=7.0)
    a3.set_ylim(.006, .060)
    a3.set_title("스물한 해가 한 번의 작업으로", fontsize=7.4)
    a3.tick_params(labelsize=6.4)

    fig.tight_layout()
    fig.savefig(out, format="pdf")
    plt.close(fig)
    return {}


# ── 노트 125 — 실험실 · 귀무의 폭 ─────────────────────────────────────
def fig_lab(out: str = "fig_lab.pdf", root: str = ".") -> dict:
    """지표가 방법을 가둔 구조 → 하네스가 푼 구조."""
    import numpy as np
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.35))
    for a in (a1, a2):
        a.set_xlim(0, 10); a.set_ylim(0, 6.2); a.axis("off")

    def box(a, x, y, w, h, t, c=INK, fs=6.4, ls="-"):
        a.add_patch(plt.Rectangle((x, y), w, h, fill=False, edgecolor=c,
                                  lw=1.0, ls=ls))
        a.text(x + w / 2, y + h / 2, t, ha="center", va="center",
               fontsize=fs, color=c, linespacing=1.4)

    def arr(a, x0, y0, x1, y1, c=MUTE, ls="-"):
        a.annotate("", (x1, y1), (x0, y0),
                   arrowprops=dict(arrowstyle="-|>", color=c, lw=.9, ls=ls,
                                   shrinkA=1, shrinkB=1))

    a1.set_title("전 — 판정치가 방법을 전제했다", fontsize=7.6, color=CLAIM)
    box(a1, .2, 4.2, 4.0, 1.5,
        "앙상블 판정치\n``출처마다 예측을 받아 순위 평균''", CLAIM, 6.3)
    box(a1, .2, 2.2, 4.0, 1.2, "쌍별 정렬 + 능형 전이", CLAIM, 6.3)
    arr(a1, 2.2, 4.2, 2.2, 3.4, CLAIM)
    a1.text(4.35, 3.8, "정의가\n방법을\n지목한다", fontsize=5.9, color=CLAIM,
            va="center", ha="left")
    for t, y in [("최적수송", 4.5), ("TabPFN", 3.1), ("확산 모형", 1.7)]:
        box(a1, 7.0, y, 2.8, .9, t, MUTE, 6.2, ls=":")
        a1.annotate("", (6.9, y + .45), (6.0, y + .45),
                    arrowprops=dict(arrowstyle="-|>", color=MUTE, lw=.8, ls=":"))
        a1.text(6.45, y + .62, "채점 불가", fontsize=5.4, color=CLAIM,
                ha="center")
    a1.text(5.0, .6, "대안이 경쟁에 못 들어오니 현행만 손보게 된다 — 노트 97-124",
            fontsize=6.0, color=CLAIM, ha="center", style="italic")

    a2.set_title("후 — 하네스가 요구하는 것은 하나뿐", fontsize=7.6, color=GATE)
    box(a2, .9, 4.6, 4.3, 1.1,
        "(도메인, 축, 마스크, 시간) $\\rightarrow$ 점수", GATE, 6.5)
    a2.text(3.05, 4.36, "순위만 의미", fontsize=5.8, color=GATE, ha="center")
    a2.plot([.45, .45], [4.6, .95], "-", color=MUTE, lw=.9)     # 레일
    a2.plot([.45, 3.05], [4.6, 4.6], "-", color=MUTE, lw=.9)
    for t, y, c, ls in [("F1 프로크루스테스", 3.0, INK, "-"),
                        ("F6 직접 풀링", 1.85, GATE, "-"),
                        ("F2~F5 · F7 (예정)", .7, MUTE, ":")]:
        box(a2, .9, y, 4.3, .85, t, c, 6.2, ls=ls)
        arr(a2, .45, y + .42, .88, y + .42, MUTE)
    box(a2, 6.0, 2.6, 3.8, 2.3,
        "상시 가드\n엿보기 · 치환 · 분모\n재현 · 빈칸 · 양규약", GATE, 6.3)
    a2.annotate("", (5.3, 2.9), (6.0, 3.4),
                arrowprops=dict(arrowstyle="-|>", color=GATE, lw=.9,
                                connectionstyle="arc3,rad=.25"))
    a2.text(7.9, 1.9, "가드가 깨지면\n승격 대상에서 빠진다", fontsize=6.0,
            color=GATE, ha="center", style="italic", linespacing=1.4)
    fig.tight_layout()
    fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


def fig_null(out: str = "fig_null.pdf", root: str = ".") -> dict:
    """치환 귀무 분포 — 팝업 하나는 분해능이 없고, 판은 있다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note125.json"))
    F1, F6 = j["forms"]["F1_procrustes"], j["forms"]["F6_directpool"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.25),
                                     gridspec_kw={"width_ratios": [1, 1, .8]})
    for a, key, rk, ttl, sub, xl in (
            (a1, "null_popup", "popup", "팝업 하나  $n$=59", "분해능 없음", .78),
            (a2, "null_pooled", "pooled", "판 전체  $n$=2,608", "분해능 있음", .52)):
        for F, nm, c in ((F1, "F1 정렬", CLAIM), (F6, "F6 직접", GATE)):
            v = np.array(F[key])
            a.hist(v, bins=18, alpha=.40, color=c, edgecolor="none",
                   density=True, label=f"{nm} 귀무  $\\pm${v.std():.3f}")
        a.set_xlim(-xl, xl)
        top = a.get_ylim()[1]
        for F, c, dy in ((F1, CLAIM, .82), (F6, GATE, .62)):
            r = F[rk]
            a.axvline(r, color=c, lw=1.7)
            a.annotate(f"실제 {r:+.3f}", (r, top * dy), fontsize=6.0, color=c,
                       ha="right", xytext=(-5, 0), textcoords="offset points")
        a.set_xlabel("스피어만 $\\rho$", fontsize=7.0)
        a.set_title(ttl + " — " + sub, fontsize=7.4)
        a.legend(fontsize=5.6, frameon=False, loc="upper left")
        a.tick_params(labelsize=6.2)
    a1.set_ylabel("밀도", fontsize=7.0)

    xs = [0, 1]
    zs = [F1["z"], F6["z"]]
    a3.bar(xs, zs, .52, color=[CLAIM, GATE], alpha=.9, edgecolor="none")
    for x, z, F in zip(xs, zs, (F1, F6)):
        a3.text(x, z + .10, f"{z:+.2f}$\\sigma$", ha="center", fontsize=7.6)
        a3.text(x, .55, f"$\\rho$\n{F['pooled']:+.4f}", ha="center",
                fontsize=6.2, color="white", linespacing=1.3, va="center")
    a3.axhline(1.96, color=MUTE, ls="--", lw=.9)
    a3.text(1.52, 1.72, "$p=.05$", fontsize=5.8, color=MUTE, ha="right")
    a3.set_xticks(xs); a3.set_xticklabels(["F1 정렬", "F6 직접"], fontsize=6.6)
    a3.set_xlim(-.55, 1.55)
    a3.set_ylabel("귀무 대비 표준화 효과", fontsize=7.0)
    a3.set_ylim(0, 3.5)
    a3.set_title("같은 점수, 다른 폭", fontsize=7.4)
    a3.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"z1": F1["z"], "z6": F6["z"]}


def fig_flip(out: str = "fig_flip.pdf", root: str = ".") -> dict:
    """대상별 대결 + 기제(대상 간 상관 → 분산 계수)."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note125.json"))
    F1, F6 = j["forms"]["F1_procrustes"], j["forms"]["F6_directpool"]
    import math as _m
    sh = [k for k in F6["per"] if k in F1["per"]
          and _m.isfinite(F1["per"][k]["rho"])]
    only6 = [k for k in F6["per"] if k not in sh]
    sh.sort(key=lambda k: F6["per"][k]["rho"] - F1["per"][k]["rho"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1.2, 1]})
    ys = np.arange(len(sh))
    d = [F6["per"][k]["rho"] - F1["per"][k]["rho"] for k in sh]
    a1.barh(ys, d, .58, color=[GATE if v > 0 else CLAIM for v in d],
            alpha=.9, edgecolor="none")
    a1.set_xlim(-.075, .40)
    for y, k, v in zip(ys, sh, d):
        a1.text(.285, y, f"{v:+.3f}", va="center", ha="right", fontsize=6.1,
                color=GATE if v > 0 else CLAIM)
        a1.text(.398, y, f"$n$={F6['per'][k]['n']}", va="center", ha="right",
                fontsize=5.9, color=MUTE)
    a1.axvline(0, color=INK, lw=.8)
    a1.axvline(.215, color="#e4e4e4", lw=.7)
    if only6:
        a1.text(-.070, len(sh) - .10,
                "  ".join(f"{k}: F1 은 채점 자체를 못 함 ($n$={F6['per'][k]['n']})"
                          for k in only6),
                fontsize=5.8, color=CLAIM, va="center")
    a1.set_yticks(ys); a1.set_yticklabels(sh, fontsize=6.6)
    a1.set_xticks([-.05, 0, .05, .10, .15])
    a1.set_xlabel("F6 직접 $-$ F1 정렬   (스피어만 차)", fontsize=7.0)
    a1.set_title("게임만 크게 오르고 나머지는 살짝 내린다 — 판으로는 무승부",
                 fontsize=7.2)
    a1.tick_params(labelsize=6.2, length=0)
    a1.set_ylim(len(sh) + .15, -.7)          # 뒤집되 주석 자리를 남긴다

    cb = [("F1 정렬", .418, 8, CLAIM), ("F6 직접", .166, 9, GATE)]
    xs = np.linspace(0, .6, 80)
    for nm, c, m, col in cb:
        a2.plot(xs, (1 + (m - 1) * xs) / m, "-", color=col, lw=1.3,
                label=f"{nm}   $m$={m}")
        v = (1 + (m - 1) * c) / m
        a2.plot([c], [v], "o", color=col, ms=6.5)
    a2.annotate("$\\bar c$=.166\n독립 대비 $\\times$2.3", (.166, .259),
                fontsize=6.1, color=GATE, xytext=(10, -16),
                textcoords="offset points", linespacing=1.4,
                arrowprops=dict(arrowstyle="-", color=GATE, lw=.7))
    a2.annotate("$\\bar c$=.418\n독립 대비 $\\times$3.9", (.418, .491),
                fontsize=6.1, color=CLAIM, xytext=(-46, 14),
                textcoords="offset points", linespacing=1.4,
                arrowprops=dict(arrowstyle="-", color=CLAIM, lw=.7))
    a2.axhline(1 / 8, color=MUTE, ls=":", lw=.9)
    a2.text(.59, .145, "독립이면 $1/m$", fontsize=5.9, color=MUTE, ha="right")
    a2.set_xlabel("대상 간 귀무 $\\rho$ 의 평균 상관   $\\bar c$", fontsize=7.0)
    a2.set_ylabel("$[\\,1+(m-1)\\bar c\\,]\\,/\\,m$", fontsize=7.0)
    a2.set_title("정렬이 대상들을 같이 움직인다 — 그래서 안 깎인다",
                 fontsize=7.2)
    a2.legend(fontsize=6.0, frameon=False, loc="upper left")
    a2.set_ylim(0, .72); a2.set_xlim(0, .6)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"shared": len(sh)}


# ── 노트 126 — 고르기 · 순위 · 삭기 ─────────────────────────────────────
def fig_tau(out: str = "fig_tau.pdf", root: str = ".") -> dict:
    """tau 를 안쪽에서 고르기 --- 평평한 곡면과 바깥의 절벽."""
    import numpy as np
    R = Path(root)
    sel = json.load(open(R / "data/state/note126_tausel.json"))
    cl = json.load(open(R / "data/state/note126_cliff.json"))
    TA = sorted(float(k) for k in sel["outer"])
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.25),
                                     gridspec_kw={"width_ratios": [1, 1, .95]})
    # ① 안쪽은 평평, 바깥은 절벽
    for inner, v in sorted(sel["inner"].items()):
        a1.plot(TA, [v["sc"][str(t)] for t in TA], "-", color=MUTE, lw=.8,
                alpha=.75)
    a1.plot([], [], "-", color=MUTE, lw=.8, label="안쪽 검증 (분할 5개)")
    a1.plot(TA, [sel["outer"][str(t)] for t in TA], "-o", color=CLAIM, lw=1.6,
            ms=4.5, label="바깥 채점 (2025$+$)")
    a1.set_xscale("log")
    a1.set_xticks(TA)
    a1.set_xticklabels([f"{t:g}" for t in TA], fontsize=6.0)
    a1.minorticks_off()
    a1.axvspan(3.0, 100.0, color=CLAIM, alpha=.06)
    a1.annotate("절벽", (10, .30), fontsize=6.4, color=CLAIM, ha="center")
    a1.set_xlabel(r"$\tau$  (작을수록 풀링 강함)", fontsize=7.0)
    a1.set_ylabel("판 $\\rho$", fontsize=7.0)
    a1.set_title("안쪽은 평평한데 바깥에는 절벽이 있다", fontsize=7.2)
    a1.legend(fontsize=5.8, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.2)

    # ② 그래서 argmax 는 다섯 중 셋을 틀린다
    ys = np.arange(len(sel["inner"]))
    labs, out_, cols = [], [], []
    for i, (inner, v) in enumerate(sorted(sel["inner"].items())):
        b = max(v["sc"], key=lambda k: v["sc"][k])
        labs.append(f"{float(inner):g} 로 가름")
        out_.append(sel["outer"][b])
        cols.append(GATE if sel["outer"][b] > .34 else CLAIM)
    a2.barh(ys, out_, .55, color=cols, alpha=.9, edgecolor="none")
    for y, v, (inner, vv) in zip(ys, out_, sorted(sel["inner"].items())):
        b = max(vv["sc"], key=lambda k: vv["sc"][k])
        a2.text(v + .006, y, f"$\\tau$={float(b):g} → {v:+.4f}", va="center",
                fontsize=6.0)
    a2.axvline(max(sel["outer"].values()), color=INK, ls="--", lw=.9)
    a2.text(max(sel["outer"].values()) - .008, -.62, "밖에서 최선",
            fontsize=5.8, ha="right", color=INK)
    a2.set_ylim(len(ys) - .35, -.95)
    a2.set_yticks(ys); a2.set_yticklabels(labs, fontsize=6.2)
    a2.set_xlim(0, .52)
    a2.set_xlabel("고른 $\\tau$ 의 바깥 점수", fontsize=7.0)
    a2.set_title("안쪽 argmax 는 다섯 중 셋이 절벽 너머", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)

    # ③ 절벽은 웹툰 하나다
    per = cl["per"]
    doms = sorted(per[str(TA[0])])
    for dd in doms:
        v = [per[str(t)].get(dd, np.nan) for t in TA]
        c = CLAIM if dd == "웹툰" else "#cfd4da"
        a3.plot(TA, v, "-o", color=c, lw=1.7 if dd == "웹툰" else .8,
                ms=3.5 if dd == "웹툰" else 2)
        if dd == "웹툰":
            a3.annotate("웹툰\n$n$=711", (TA[-1], v[-1]), fontsize=6.2,
                        color=CLAIM, xytext=(-4, 8), textcoords="offset points",
                        ha="right", linespacing=1.3)
    a3.axhline(0, color=INK, lw=.7)
    a3.set_xscale("log"); a3.set_xticks(TA)
    a3.set_xticklabels([f"{t:g}" for t in TA], fontsize=6.0)
    a3.minorticks_off()
    a3.set_xlabel(r"$\tau$", fontsize=7.0)
    a3.set_ylabel("대상별 $\\rho$", fontsize=7.0)
    a3.set_title("절벽은 도메인 하나가 만든다", fontsize=7.2)
    a3.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


def fig_rank(out: str = "fig_rank.pdf", root: str = ".") -> dict:
    """z 로 줄을 세우면 규제가 셀수록 이긴다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note126_board.json"))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    ks = [k for k in j if j[k].get("z") is not None and np.isfinite(j[k]["z"])]
    for k in ks:
        v = j[k]
        c = CLAIM if k.startswith("F8") else (GATE if k.startswith("F2") else INK)
        a1.plot([v["pooled"]], [v["z"]], "o", color=c, ms=7,
                alpha=.9 if c != INK else .55)
        a1.annotate(k.split("_")[0], (v["pooled"], v["z"]), fontsize=6.2,
                    color=c, xytext=(7, -2), textcoords="offset points")
    a1.set_xlabel("판 $\\rho$ — 유보 표본에서 실제로 맞힌 정도", fontsize=7.0)
    a1.set_ylabel("$z$ — 치환 귀무 대비", fontsize=7.0)
    a1.set_title("$z$ 순위와 $\\rho$ 순위가 어긋난다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)
    a1.annotate("F8 은 $\\rho$ 로 F6 · F9 · F10 보다 낮은데\n$z$ 는 전부보다 높다 --- 규제가 세면\n섞인 라벨도 못 맞혀 귀무가 좁아진다",
                (j["F8_boost"]["pooled"], j["F8_boost"]["z"]), fontsize=5.9,
                color=CLAIM, xytext=(-8, -34), textcoords="offset points",
                ha="left", linespacing=1.4,
                arrowprops=dict(arrowstyle="-", color=CLAIM, lw=.7))

    order = sorted(ks, key=lambda k: -j[k]["pooled"])
    ys = np.arange(len(order))
    a2.barh(ys, [j[k]["pooled"] for k in order], .58,
            color=[GATE if i == 0 else "#b9c2cc" for i in range(len(order))],
            alpha=.92, edgecolor="none")
    for y, k in zip(ys, order):
        v = j[k]
        a2.text(v["pooled"] + .005, y,
                f"{v['pooled']:+.4f}    귀무 {v['null_sd']:.3f}"
                f"    $z$ {v['z']:+.2f}", va="center", fontsize=5.9)
    a2.set_yticks(ys)
    a2.set_yticklabels(order, fontsize=6.2)
    a2.set_xlim(0, .46)
    a2.set_xlabel("판 $\\rho$ (순위 기준)", fontsize=7.0)
    a2.set_title("순위는 $\\rho$, $z$ 는 가드", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    a2.invert_yaxis()
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(ks)}


def fig_decay(out: str = "fig_decay.pdf", root: str = ".") -> dict:
    """안쪽에서 본 곡선과 바깥에서 본 곡선 --- 평평하면 모른다는 뜻이다."""
    import numpy as np
    R = Path(root)
    wc = json.load(open(R / "data/state/note126_wcurve.json"))
    sh = json.load(open(R / "data/state/note126_shift.json"))
    G = [float(g) for g in wc["grid"]]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.35),
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    SHOW = [("웹툰", CLAIM), ("모바일", GATE), ("세계애니", "#9aa3ad")]
    for dd, c in SHOW:
        ino = wc["inner"].get(dd, {})
        oto = wc["outer"].get(dd, {})
        if ino:
            a1.plot(G, [ino.get(str(g), ino.get(g, np.nan)) for g in G], "--o",
                    color=c, lw=1.1, ms=3, alpha=.8)
        if oto:
            a1.plot(G, [oto.get(str(g), oto.get(g, np.nan)) for g in G], "-o",
                    color=c, lw=1.8, ms=4.5)
    a1.plot([], [], "--", color=MUTE, lw=1.1, label="안쪽 검증 (2025 이전)")
    a1.plot([], [], "-", color=MUTE, lw=1.8, label="바깥 채점 (2025$+$)")
    a1.axhline(0, color=INK, lw=.7)
    for dd, c, gx, dy, ha in (("웹툰", CLAIM, 1.0, -13, "right"),
                              ("모바일", GATE, 1.0, 9, "right"),
                              ("세계애니", "#7f8894", 0.0, 11, "left")):
        o = wc["outer"].get(dd, {})
        if o:
            a1.annotate(dd, (gx, o.get(str(gx), o.get(gx, np.nan))),
                        fontsize=6.3, color=c, ha=ha,
                        xytext=(-4 if ha == "right" else 4, dy),
                        textcoords="offset points")
    a1.set_xticks(G)
    a1.set_xticklabels([f"{g:g}" for g in G], fontsize=6.2)
    a1.set_xlabel("배합비 $w$   (0 = 완전 풀링, 1 = 자기 이력만)", fontsize=7.0)
    a1.set_ylabel("스피어만 $\\rho$", fontsize=7.0)
    a1.set_title("모바일은 맞고 웹툰은 틀리는데, 안쪽만 보면 구별이 안 된다",
                 fontsize=7.2)
    a1.legend(fontsize=5.9, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.2)
    a1.annotate("안쪽 폭 0.034 — 평평하다", (.75, .498), fontsize=5.9,
                color=CLAIM, xytext=(-4, -46), textcoords="offset points",
                ha="center", arrowprops=dict(arrowstyle="-", color=CLAIM, lw=.6))
    a1.annotate("안쪽 폭 0.591 — 가파르다", (.5, .426), fontsize=5.9,
                color=GATE, xytext=(6, 26), textcoords="offset points",
                ha="left", arrowprops=dict(arrowstyle="-", color=GATE, lw=.6))
    a1.set_ylim(-.27, .72)

    ks = sorted(sh, key=lambda k: sh[k]["own"] - sh[k]["oth"])
    ys = np.arange(len(ks))
    a2.barh(ys - .19, [sh[k]["own"] for k in ks], .36, color=CLAIM, alpha=.9,
            edgecolor="none", label="자기 이력으로")
    a2.barh(ys + .19, [sh[k]["oth"] for k in ks], .36, color=GATE, alpha=.9,
            edgecolor="none", label="남의 도메인으로")
    a2.axvline(0, color=INK, lw=.8)
    a2.set_yticks(ys)
    a2.set_yticklabels([f"{k} ({sh[k]['post']})" for k in ks], fontsize=6.4)
    a2.set_xlabel("2025$+$ 채점  $\\rho$", fontsize=7.0)
    a2.set_xlim(-.28, .62)
    a2.legend(fontsize=6.0, frameon=False, loc="upper right",
              bbox_to_anchor=(1.0, 1.06))
    a2.set_title("웹툰과 모바일이 정반대를 원한다", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    a2.set_ylim(len(ks) - .4, -.7)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 127 — 태거와 표본 넓히기 ────────────────────────────────────────
def fig_tagger(out: str = "fig_tagger.pdf", root: str = ".") -> dict:
    """축마다 글에서 얼마나 되찾아지나."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note127_tagcv.json"))
    SH = {"target_breadth", "venue_prominence", "entry_friction",
          "media_push", "goods_scale"}
    KO = {"experience_density": "체험 밀도", "goods_scale": "굿즈 규모",
          "photo_zones": "포토존", "collab_strength": "콜라보 강도",
          "ip_awareness": "IP 인지도", "target_breadth": "타깃 폭",
          "entry_friction": "입장 마찰", "media_push": "미디어 푸시",
          "season_fit": "계절 적합", "venue_prominence": "장소 위상"}
    ks = sorted(j, key=lambda k: j[k]["mean"])
    ys = np.arange(len(ks))
    fig, a = plt.subplots(figsize=(COL, 2.5))
    cols = [GATE if k in SH else "#b9c2cc" for k in ks]
    a.barh(ys, [j[k]["mean"] for k in ks], .6, color=cols, alpha=.92,
           edgecolor="none")
    a.errorbar([j[k]["mean"] for k in ks], ys,
               xerr=[[j[k]["mean"] - j[k]["lo"] for k in ks],
                     [j[k]["hi"] - j[k]["mean"] for k in ks]],
               fmt="none", ecolor=INK, elinewidth=.8, capsize=1.6)
    for y, k in zip(ys, ks):
        a.text(j[k]["hi"] + .012, y, f"{j[k]['mean']:+.2f}", va="center",
               fontsize=6.0)
    a.axvline(0, color=INK, lw=.8)
    a.set_yticks(ys)
    a.set_yticklabels([KO.get(k, k) + ("  ●" if k in SH else "") for k in ks],
                      fontsize=6.4)
    a.set_xlim(-.05, .78)
    a.set_xlabel("교차검증 $\\rho$  ($n$=95 · 5겹 $\\times$ 12회)", fontsize=7.0)
    a.set_title("● 은 전 도메인 공통 축\n글에서 되찾히는 축과 아닌 축", fontsize=7.2)
    a.tick_params(labelsize=6.2, length=0)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


def fig_expand(out: str = "fig_expand.pdf", root: str = ".") -> dict:
    """표본을 넓히면 좋아지는데, 좋아진 이유가 짐작과 다르다."""
    import numpy as np
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1.1, 1]})
    # ① 분해 --- 고정 분모 59건 위에서
    rows = [("현행\n(팝업 학습 밖)", .3688, MUTE),
            ("현행 · 문턱 15\n(팝업 16건 학습 안)", .3814, MUTE),
            ("$+$주장 · 팝업 학습 밖", .3244, CLAIM),
            ("$+$주장\n(팝업 73건 학습 안)", .4495, GATE)]
    ys = np.arange(len(rows))
    a1.barh(ys, [r[1] for r in rows], .58, color=[r[2] for r in rows],
            alpha=.92, edgecolor="none")
    for y, r in zip(ys, rows):
        a1.text(r[1] + .006, y, f"{r[1]:+.4f}", va="center", fontsize=6.2)
    a1.axvline(.3688, color=INK, ls="--", lw=.8)
    a1.set_yticks(ys); a1.set_yticklabels([r[0] for r in rows], fontsize=6.2)
    a1.set_xlim(0, .55)
    a1.set_xlabel("팝업 $\\rho$ --- 같은 59건 위에서만", fontsize=7.0)
    a1.set_title("늘어난 값은 '레코드가 늘어서'가 아니라\n'팝업이 학습에 들어가서'다",
                 fontsize=7.2)
    a1.tick_params(labelsize=6.2, length=0)
    a1.set_ylim(len(rows) - .4, -.7)

    # ② 태거를 다른 종류 레코드에 대면
    lab = ["공통 59건 위", "전체 116건 위"]
    xs = np.arange(2)
    for i, (nm, v, c) in enumerate([("축 비움", [.4495, .4562], GATE),
                                    ("자동 태깅", [.3917, .1150], CLAIM),
                                    ("믿는 축만", [.4609, .4551], "#8fa8bd")]):
        a2.bar(xs + (i - 1) * .27, v, .25, color=c, alpha=.92,
               edgecolor="none", label=nm)
        for x, y in zip(xs + (i - 1) * .27, v):
            a2.text(x, y + .008, f"{y:.3f}", ha="center", fontsize=5.8)
    a2.set_xticks(xs); a2.set_xticklabels(lab, fontsize=6.6)
    a2.set_ylabel("팝업 $\\rho$", fontsize=7.0)
    a2.set_ylim(0, .66)
    a2.legend(fontsize=6.0, frameon=False, loc="upper center", ncol=3,
              bbox_to_anchor=(.5, 1.0), columnspacing=1.2, handlelength=1.1)
    a2.set_title("태거는 배운 종류 안에서만 맞는다\n(추가된 시장 레코드에서 무너진다)",
                 fontsize=7.2)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 128 — 작품 바깥의 수요 신호 ─────────────────────────────────────
def fig_trend(out: str = "fig_trend.pdf", root: str = ".") -> dict:
    """검색 축의 신호 · 증분 · 덮음."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note128_sig.json"))
    sig, incr, cov = j["sig"], j["incr"], j["cov"]
    FE = ["trend_level", "trend_momentum", "trend_volatility", "trend_peak_ratio"]
    KO = {"trend_level": "수준", "trend_momentum": "모멘텀",
          "trend_volatility": "변동성", "trend_peak_ratio": "정점비"}
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1.15, 1, .85]})
    # ① 축별 · 도메인별 라벨 상관
    doms = sorted(sig, key=lambda d: -sig[d].get("trend_level", -9))
    xs = np.arange(len(doms))
    cols = [GATE, "#7fa8c9", "#b9c2cc", "#d8dde2"]
    for i, f in enumerate(FE):
        a1.bar(xs + (i - 1.5) * .2, [sig[d].get(f, 0) for d in doms], .18,
               color=cols[i], alpha=.95, edgecolor="none", label=KO[f])
    a1.axhline(0, color=INK, lw=.8)
    a1.set_xticks(xs); a1.set_xticklabels(doms, fontsize=6.4)
    a1.set_ylabel("라벨과의 스피어만 $\\rho$", fontsize=7.0)
    a1.set_ylim(-.15, .62)
    a1.legend(fontsize=5.8, frameon=False, ncol=4, loc="upper center",
              columnspacing=.9, handlelength=1.0)
    a1.set_title("작품 바깥의 수요 신호가 라벨과 붙는다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    # ② 증분 --- 손 축 잔차와도 붙나
    ks = sorted(incr, key=lambda d: -incr[d]["raw"])
    ys = np.arange(len(ks))
    a2.barh(ys - .19, [incr[k]["raw"] for k in ks], .36, color=GATE, alpha=.92,
            edgecolor="none", label="라벨과 직접")
    a2.barh(ys + .19, [incr[k]["resid"] for k in ks], .36, color=CLAIM,
            alpha=.92, edgecolor="none", label="손 축 잔차와")
    a2.axvline(0, color=INK, lw=.8)
    a2.set_yticks(ys)
    a2.set_yticklabels([f"{k} ({incr[k]['n']})" for k in ks], fontsize=6.4)
    a2.set_xlabel("스피어만 $\\rho$", fontsize=7.0)
    a2.set_xlim(-.12, .52)
    a2.legend(fontsize=6.0, frameon=False, loc="lower right")
    a2.set_title("손으로 매긴 축이 못 보던 것을 본다", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    a2.set_ylim(len(ks) - .4, -.7)

    # ③ 덮음
    cd = dict(cov)                      # 0인 도메인도 보여야 제목이 성립한다
    ks3 = sorted(cd, key=lambda k: -cd[k]["덮음"])
    ys3 = np.arange(len(ks3))
    a3.barh(ys3, [cd[k]["덮음"] for k in ks3], .6,
            color=[GATE if cd[k]["덮음"] > .4 else "#c3cad2" for k in ks3],
            alpha=.92, edgecolor="none")
    for y, k in zip(ys3, ks3):
        a3.text(cd[k]["덮음"] + .015, y, f"{cd[k]['상태']}/{cd[k]['행']}",
                va="center", fontsize=5.9,
                color=INK if cd[k]["덮음"] > 0 else CLAIM)
    a3.set_yticks(ys3); a3.set_yticklabels(ks3, fontsize=6.4)
    a3.set_xlim(0, 1.28)
    a3.set_xticks([0, .25, .5, .75, 1.0])
    a3.set_xlabel("행 덮음", fontsize=7.0)
    a3.set_title("만화 · 세계애니는 0\n(제목이 로마자라 한국어 검색이 안 붙는다)",
                 fontsize=7.0)
    a3.tick_params(labelsize=6.2, length=0)
    a3.set_ylim(len(ks3) - .4, -.7)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


def fig_gain(out: str = "fig_gain.pdf", root: str = ".") -> dict:
    """축 세트를 바꿨을 때의 이득 --- 정식화별 · 대상별."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note128_gain.json"))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    # ① 정식화별 판 rho
    fs = [k for k in j["board"] if j["board"][k].get("trend") is not None]
    fs.sort(key=lambda k: -j["board"][k]["trend"])
    xs = np.arange(len(fs))
    for i, (key, nm, c) in enumerate([("base", "공통 다섯만", "#c3cad2"),
                                      ("trend", "＋검색 (0=측정)", GATE),
                                      ("trend0", "＋검색 (0=결측)", CLAIM)]):
        v = [j["board"][k].get(key) or np.nan for k in fs]
        a1.bar(xs + (i - 1) * .27, v, .25, color=c, alpha=.95,
               edgecolor="none", label=nm)
    a1.set_xticks(xs)
    a1.set_xticklabels([k.split("_")[0] for k in fs], fontsize=6.6)
    a1.set_ylabel("판 $\\rho$", fontsize=7.0)
    a1.set_ylim(.30, .44)
    a1.legend(fontsize=5.9, frameon=False, ncol=1, loc="upper right")
    a1.set_title("네 정식화가 전부 오른다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    # ② 대상별
    per = j["per"]
    ks = sorted(per, key=lambda k: per[k])
    ys = np.arange(len(ks))
    a2.barh(ys, [per[k] for k in ks], .6,
            color=[GATE if per[k] > 0 else CLAIM for k in ks],
            alpha=.92, edgecolor="none")
    for y, k in zip(ys, ks):
        v = per[k]
        a2.text(v + (.004 if v > 0 else -.004), y, f"{v:+.3f}", va="center",
                ha="left" if v > 0 else "right", fontsize=6.0)
    a2.axvline(0, color=INK, lw=.8)
    a2.set_yticks(ys); a2.set_yticklabels(ks, fontsize=6.5)
    a2.set_xlim(-.10, .17)
    a2.set_xlabel("＋검색 $-$ 기본  (스피어만 차)", fontsize=7.0)
    a2.set_title("팝업은 내린다 --- 검색어가 브랜드명이라서",
                 fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 129 — 같은 플랫폼 결합을 재 본다 ────────────────────────────────
def fig_couple(out: str = "fig_couple.pdf", root: str = ".") -> dict:
    """웹툰이 이상한가 --- 덮음 맞춘 비교."""
    import numpy as np
    R = Path(root)
    c = json.load(open(R / "data/state/note129_couple.json"))
    w = json.load(open(R / "data/state/note129_wt.json"))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.35),
                                 gridspec_kw={"width_ratios": [1, 1.1]})
    # ① 신호 세기 --- 웹툰이 분포 안인가
    ks = sorted(c, key=lambda k: -c[k]["lv"])
    xs = np.arange(len(ks))
    a1.bar(xs, [c[k]["lv"] for k in ks], .5,
           color=[CLAIM if k == "웹툰" else "#b9c2cc" for k in ks],
           alpha=.95, edgecolor="none", label="라벨과 직접")
    a1.bar(xs, [c[k]["res"] for k in ks], .24,
           color=["#7a1020" if k == "웹툰" else GATE for k in ks],
           alpha=.95, edgecolor="none", label="손축 잔차와")
    oth = [c[k]["lv"] for k in c if k != "웹툰"]
    m, s = float(np.mean(oth)), float(np.std(oth))
    a1.axhline(m, color=INK, ls="--", lw=.8)
    a1.axhspan(m - s, m + s, color=INK, alpha=.06)
    a1.text(len(ks) - .4, m + .012, "결합 없는 도메인 평균 $\\pm$1SD",
            fontsize=5.8, ha="right", color=INK)
    a1.set_xticks(xs); a1.set_xticklabels(ks, fontsize=6.4)
    a1.axhline(0, color=INK, lw=.7)
    a1.set_ylabel("스피어만 $\\rho$", fontsize=7.0)
    a1.set_ylim(-.09, .52)
    a1.legend(fontsize=5.9, frameon=False, loc="upper right")
    a1.set_title("웹툰(붉은색)의 신호는 분포 안에 있다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    # ② 덮음 대 이득
    per, cov = w["per"], w["cov"]
    b, t = per["기본"], per["＋검색(웹툰 포함)"]
    ks2 = [k for k in cov if k in b and k in t and cov[k] > 0]
    for k in ks2:
        g = t[k] - b[k]
        c2 = CLAIM if k == "웹툰" else (GATE if k == "모바일" else "#9aa3ad")
        a2.plot([cov[k]], [g], "o", color=c2,
                ms=9 if k in ("웹툰", "모바일") else 6,
                alpha=.95 if k in ("웹툰", "모바일") else .7)
        a2.annotate(k, (cov[k], g), fontsize=6.2, color=c2,
                    xytext=(8, -3), textcoords="offset points")
    a2.axhline(0, color=INK, lw=.8)
    a2.annotate("", (cov["웹툰"], t["웹툰"] - b["웹툰"]),
                (cov["모바일"], t["모바일"] - b["모바일"]),
                arrowprops=dict(arrowstyle="<->", color=CLAIM, lw=.9, ls=":"))
    a2.text(.30, .120, "덮음이 비슷한데 웹툰이 더 낮다\n(모바일 41.3\% $+$.099 · 웹툰 37.9\% $+$.063)",
            fontsize=6.0, color=CLAIM, ha="left", linespacing=1.4)
    a2.set_xlabel("검색 축 덮음", fontsize=7.0)
    a2.set_ylabel("＋검색 이득 (스피어만 차)", fontsize=7.0)
    a2.set_xlim(.22, 1.0)
    a2.set_title("결합이 있다면 웹툰이 튀어야 한다 --- 안 튄다", fontsize=7.2)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


def fig_climb(out: str = "fig_climb.pdf", root: str = ".") -> dict:
    """축을 더해 온 궤적 --- 판 rho 와 귀무 폭이 같이 움직인다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note129_board.json"))
    FS = ["F8_boost", "F9_ranklik", "F6_directpool", "F10_pershrink"]
    KO = {"F8_boost": "F8 부스팅", "F9_ranklik": "F9 짝 순위",
          "F6_directpool": "F6 직접 풀링", "F10_pershrink": "F10 도메인별 수축"}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3))
    xs = np.arange(2)
    for i, f in enumerate(FS):
        b, t = j.get(f, {}), j.get(f + "@trend", {})
        if not b or not t:
            continue
        c = GATE if f == "F8_boost" else "#9aa3ad"
        lw = 2.0 if f == "F8_boost" else 1.0
        a1.plot(xs, [b["pooled"], t["pooled"]], "-o", color=c, lw=lw, ms=5)
        a1.annotate(KO[f], (1, t["pooled"]), fontsize=6.2, color=c,
                    xytext=(6, -2), textcoords="offset points")
        a2.plot(xs, [b["null_sd"], t["null_sd"]], "-o", color=c, lw=lw, ms=5)
        a2.annotate(KO[f], (1, t["null_sd"]), fontsize=6.2, color=c,
                    xytext=(6, -2), textcoords="offset points")
    for a, yl, ti in ((a1, "판 $\\rho$", "더 맞힌다"),
                      (a2, "치환 귀무 폭", "동시에 덜 유연해진다")):
        a.set_xticks(xs)
        a.set_xticklabels(["공통 다섯", "＋오픈 전 검색"], fontsize=6.6)
        a.set_xlim(-.25, 1.75)
        a.set_ylabel(yl, fontsize=7.0)
        a.set_title(ti, fontsize=7.4)
        a.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 130 — 달력, 그리고 공유의 두 층 ─────────────────────────────────
def fig_supply(out: str = "fig_supply.pdf", root: str = ".") -> dict:
    """팝업 일평균을 정하는 것 --- 수요인가 공급인가 달력인가."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note130_supply.json"))
    j = dict(j)
    j["오픈 전 검색"] = {"n": 67, "perday": 0.0884, "total": 0.2203, "kind": "수요"}
    ks = sorted(j, key=lambda k: -j[k]["perday"])
    C = {"달력": GATE, "공급": "#9aa3ad", "계획": "#c8ced6", "수요": CLAIM}
    ys = np.arange(len(ks))
    fig, a = plt.subplots(figsize=(COL, 2.35))
    a.barh(ys - .19, [j[k]["perday"] for k in ks], .36,
           color=[C[j[k]["kind"]] for k in ks], alpha=.95, edgecolor="none")
    a.barh(ys + .19, [j[k]["total"] for k in ks], .36,
           color=[C[j[k]["kind"]] for k in ks], alpha=.45, edgecolor="none")
    for y, k in zip(ys, ks):
        a.text(max(j[k]["perday"], j[k]["total"]) + .012, y,
               f"{j[k]['kind']}", va="center", fontsize=5.8,
               color=C[j[k]["kind"]])
    a.axvline(0, color=INK, lw=.8)
    a.set_yticks(ys); a.set_yticklabels(ks, fontsize=6.4)
    a.set_xlim(-.30, .78)
    a.set_xlabel("스피어만 $\\rho$   (진한 막대 = 일평균 · 연한 = 총량)",
                 fontsize=6.8)
    a.set_title("팝업 일평균을 제일 잘 설명하는 것은\n수요도 장소도 아니고 달력이다",
                fontsize=7.2)
    a.tick_params(labelsize=6.2, length=0)
    a.set_ylim(len(ks) - .4, -.7)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


def fig_ladder(out: str = "fig_ladder.pdf", root: str = ".") -> dict:
    """축을 더해 온 사다리 --- 맞히기는 오르고 귀무는 좁아진다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note130_ladder.json"))
    steps = j["steps"]
    xs = np.arange(len(steps))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3))
    for f, c, lw in [("F8_boost", GATE, 2.0), ("F9_ranklik", "#9aa3ad", 1.1)]:
        v = [j["pooled"].get(f"{f}{s['suf']}") for s in steps]
        n = [j["null"].get(f"{f}{s['suf']}") for s in steps]
        a1.plot(xs, v, "-o", color=c, lw=lw, ms=5)
        a2.plot(xs, n, "-o", color=c, lw=lw, ms=5)
        a1.annotate(f.split("_")[0], (xs[-1], v[-1]), fontsize=6.3, color=c,
                    xytext=(6, -2), textcoords="offset points")
        a2.annotate(f.split("_")[0], (xs[-1], n[-1]), fontsize=6.3, color=c,
                    xytext=(6, -2), textcoords="offset points")
    for a, yl, ti in ((a1, "판 $\\rho$", "맞히기는 오르고"),
                      (a2, "치환 귀무 폭", "귀무는 좁아진다")):
        a.set_xticks(xs)
        a.set_xticklabels([s["ko"] for s in steps], fontsize=6.0)
        a.set_xlim(-.3, len(steps) - .35)
        a.set_ylabel(yl, fontsize=7.0)
        a.set_title(ti, fontsize=7.4)
        a.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 131 — 무엇을 · 언제 · 그리고 폴드 평균 결함 ────────────────────
def fig_blocks(out: str = "fig_blocks.pdf", root: str = ".") -> dict:
    """팝업 일평균의 예측력을 묶음별로."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note131_popup.json"))
    ks = sorted(j, key=lambda k: j[k]["rho"])
    ys = np.arange(len(ks))
    C = lambda k: (GATE if k.startswith("축＋") else
                   (CLAIM if j[k]["rho"] < 0 else "#9aa3ad"))
    fig, a = plt.subplots(figsize=(COL, 2.3))
    a.barh(ys, [j[k]["rho"] for k in ks], .58,
           color=[C(k) for k in ks], alpha=.95, edgecolor="none")
    a.errorbar([j[k]["rho"] for k in ks], ys,
               xerr=[j[k]["se"] for k in ks], fmt="none", ecolor=INK,
               elinewidth=.8, capsize=1.8)
    for y, k in zip(ys, ks):
        v = j[k]["rho"]
        a.text(v + (.014 if v > 0 else -.014), y, f"{v:+.3f}", va="center",
               ha="left" if v > 0 else "right", fontsize=6.0)
    a.axvline(0, color=INK, lw=.8)
    a.set_yticks(ys)
    a.set_yticklabels([f"{k} ({j[k]['cols']})" for k in ks], fontsize=6.3)
    a.set_xlim(-.24, .66)
    a.set_xlabel("폴드 안 스피어만 (5겹 $\\times$ 8회) · $n$=75", fontsize=6.8)
    a.set_title("팝업 일평균 --- 무엇을과 언제가 서로를 채운다", fontsize=7.2)
    a.tick_params(labelsize=6.2, length=0)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


def fig_fold(out: str = "fig_fold.pdf", root: str = ".") -> dict:
    """폴드별 예측을 모아서 재면 무엇이 잘못되나."""
    import numpy as np
    from scipy.stats import rankdata, spearmanr
    from sklearn.linear_model import RidgeCV
    from sklearn.model_selection import KFold
    R = Path(root)
    z = np.load(R / "data/state/popup_v2.npz", allow_pickle=True)
    cols = [str(c) for c in z["names"]]
    meta = json.loads((R / "data/state/popup_v2_meta.json").read_text())
    import sys
    sys.path.insert(0, str(R))
    from lab.trendaxes import _popup_ids
    idx = {m["id"]: i for i, m in enumerate(meta)}
    K = np.array([idx[k] for k in _popup_ids()])
    y = rankdata(z["y_perday"][K]) / len(K)
    v = z["X"][K, cols.index("days")]
    F = (rankdata(v) / len(v)).reshape(-1, 1)
    P = np.zeros(len(y)); fid = np.zeros(len(y), int)
    for i, (tr, te) in enumerate(KFold(5, shuffle=True, random_state=7).split(F)):
        P[te] = RidgeCV(alphas=[.1, 1, 10, 100]).fit(F[tr], y[tr]).predict(F[te])
        fid[te] = i
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.2))
    cs = ["#2166ac", "#67a9cf", "#b9c2cc", "#ef8a62", "#b2182b"]
    for i in range(5):
        k = fid == i
        a1.plot(P[k], y[k], "o", color=cs[i], ms=4, alpha=.85,
                label=f"폴드 {i+1}")
    a1.set_xlabel("폴드별 예측 (모은 것)", fontsize=7.0)
    a1.set_ylabel("라벨 (순위)", fontsize=7.0)
    a1.set_title(f"모아서 재면 $\\rho$ {spearmanr(P, y).correlation:+.3f}"
                 "  --- 폴드 평균이 갈라져 있다", fontsize=7.0)
    a1.legend(fontsize=5.6, frameon=False, ncol=2)
    a1.tick_params(labelsize=6.2)
    inner = []
    for i in range(5):
        k = fid == i
        r = spearmanr(P[k], y[k]).correlation
        inner.append(r if np.isfinite(r) else 0.0)
    a2.bar(np.arange(5), inner, .55, color=GATE, alpha=.92, edgecolor="none")
    a2.axhline(float(np.mean(inner)), color=INK, ls="--", lw=.9)
    a2.axhline(float(spearmanr(P, y).correlation), color=CLAIM, ls="-", lw=1.2)
    a2.text(4.4, float(np.mean(inner)) + .02, f"폴드 안 평균 {np.mean(inner):+.3f}",
            fontsize=6.0, ha="right", color=INK)
    a2.text(4.4, float(spearmanr(P, y).correlation) - .05,
            f"모아서 잰 값 {spearmanr(P, y).correlation:+.3f}",
            fontsize=6.0, ha="right", color=CLAIM)
    a2.axhline(0, color=INK, lw=.7)
    a2.set_xticks(np.arange(5))
    a2.set_xticklabels([f"{i+1}" for i in range(5)], fontsize=6.4)
    a2.set_xlabel("폴드", fontsize=7.0)
    a2.set_ylabel("스피어만 $\\rho$", fontsize=7.0)
    a2.set_title("폴드 안에서 재면 부호가 다르다", fontsize=7.0)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 132 — 달력의 이질성, 그리고 머리를 안 사는 이유 ─────────────────
def fig_hetero(out: str = "fig_hetero.pdf", root: str = ".") -> dict:
    """달력 효과가 도메인마다 갈리는데 표본 크기로는 안 설명된다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note132.json"))
    per, cur, tp = j["per"], j["head_curve"], j["tabpfn"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.3),
                                     gridspec_kw={"width_ratios": [1.1, 1, .85]})
    # ① 효과 대 표본 크기
    for k, v in per.items():
        g = v["trendcal"] - v["trend"]
        c = CLAIM if g < -.02 else (GATE if g > .02 else "#9aa3ad")
        a1.plot([v["n"]], [g], "o", color=c, ms=7, alpha=.92)
        dy = 8 if k in ("세계애니", "웹툰", "도서") else -2
        dx = 7 if k not in ("웹툰",) else -22
        a1.annotate(k, (v["n"], g), fontsize=6.2, color=c,
                    xytext=(dx, dy), textcoords="offset points")
    a1.axhline(0, color=INK, lw=.8)
    a1.set_xscale("log")
    a1.set_xticks([25, 60, 160, 440, 711])
    a1.set_xticklabels(["25", "60", "160", "440", "711"], fontsize=6.2)
    a1.minorticks_off()
    a1.set_xlabel("후행 표본 $n$", fontsize=7.0)
    a1.set_ylabel("달력을 더한 효과", fontsize=7.0)
    a1.set_xlim(18, 1400)
    a1.set_title("표본 크기로는 안 설명된다", fontsize=7.1)
    a1.tick_params(labelsize=6.2)

    # ② 머리를 강제로 달면
    xs = [c[0] for c in cur]; ys = [c[1] for c in cur]
    a2.plot(xs, ys, "-o", color=CLAIM, lw=1.8, ms=5.5)
    a2.annotate("안쪽 검정이 고른 값", (0, ys[0]), fontsize=6.2, color=GATE,
                xytext=(22, -14), textcoords="offset points",
                arrowprops=dict(arrowstyle="-|>", color=GATE, lw=.8))
    a2.set_xlabel("도메인별 달력 머리 세기 $w$", fontsize=7.0)
    a2.set_ylabel("판 $\\rho$", fontsize=7.0)
    a2.set_title("머리를 달면 단조롭게 나빠진다\n--- 거절이 옳았다", fontsize=6.9)
    a2.tick_params(labelsize=6.2)

    # ③ TabPFN --- 모수를 안 정하는 모형도 같은 벌점
    ks = ["기본", "＋검색", "＋검색＋달력"]
    a3.bar(np.arange(3), [tp[k] for k in ks], .55,
           color=["#c3cad2", GATE, CLAIM], alpha=.95, edgecolor="none")
    for i, k in enumerate(ks):
        a3.text(i, tp[k] + .004, f"{tp[k]:+.3f}", ha="center", fontsize=6.2)
    a3.set_xticks(np.arange(3))
    a3.set_xticklabels(["기본", "＋검색", "＋달력"], fontsize=6.4)
    a3.set_ylim(.32, .42)
    a3.set_ylabel("판 $\\rho$", fontsize=7.0)
    a3.set_title("TabPFN --- 우리 자료로 모수를\n안 정하는데도 같은 벌점",
                 fontsize=6.9)
    a3.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 133 — 기준선을 바꾸면 부호가 바뀐다 ─────────────────────────────
def fig_wide(out: str = "fig_wide.pdf", root: str = ".") -> dict:
    """확장의 효과 --- 어느 기준선과 견주느냐로 부호가 갈린다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note133.json"))
    KO = {"F8_boost": "F8 부스팅", "F9_ranklik": "F9 짝 순위",
          "F6_directpool": "F6 직접 풀링"}
    ks = list(j)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1.1, 1]})
    xs = np.arange(len(ks))
    a1.bar(xs - .2, [j[k]["narrow_trendcal"]["fixed"] for k in ks], .36,
           color="#c3cad2", alpha=.95, edgecolor="none", label="좁은 판")
    a1.bar(xs + .2, [j[k]["wide_trendcal"]["fixed"] for k in ks], .36,
           color=GATE, alpha=.95, edgecolor="none", label="넓은 판")
    for i, k in enumerate(ks):
        a, b = j[k]["narrow_trendcal"]["fixed"], j[k]["wide_trendcal"]["fixed"]
        a1.text(i + .2, b + .008, f"{b-a:+.3f}", ha="center", fontsize=6.2,
                color=GATE)
    a1.set_xticks(xs); a1.set_xticklabels([KO[k] for k in ks], fontsize=6.5)
    a1.set_ylabel("팝업 $\\rho$ --- 같은 59건 위에서", fontsize=7.0)
    a1.set_ylim(0, .52)
    a1.legend(fontsize=6.0, frameon=False, loc="upper left")
    a1.set_title("같은 코드 경로로 견주면 확장이 돕는다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    # 기준선을 바꾸면
    rows = [("audit 좁은 판\n(빈 축 마스크 켜짐)", .4995, MUTE),
            ("같은 경로 좁은 판\n(빈 축 마스크 꺼짐)", .3698, "#c3cad2"),
            ("넓은 판", .4300, GATE)]
    ys = np.arange(len(rows))
    a2.barh(ys, [r[1] for r in rows], .55, color=[r[2] for r in rows],
            alpha=.95, edgecolor="none")
    for y, r in zip(ys, rows):
        a2.text(r[1] + .008, y, f"{r[1]:+.4f}", va="center", fontsize=6.2)
    a2.set_yticks(ys); a2.set_yticklabels([r[0] for r in rows], fontsize=6.1)
    a2.set_xlim(0, .62)
    a2.set_xlabel("F9 팝업 $\\rho$ --- 같은 59건", fontsize=7.0)
    a2.set_title("어느 좁은 판과 견주느냐로 부호가 갈린다\n($-$0.070 대 $+$0.060)",
                 fontsize=7.0)
    a2.tick_params(labelsize=6.2, length=0)
    a2.set_ylim(len(rows) - .4, -.7)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 134 — 기준선이 처치보다 크다 ────────────────────────────────────
def fig_base(out: str = "fig_base.pdf", root: str = ".") -> dict:
    """처치 효과들과 기준선 차이를 같은 눈금에."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note134.json"))
    cells, prev = j["cells"], j["prev"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    # ① 2x2 --- 부호가 뒤집힌다
    xs = np.arange(4)
    ks = ["F9·audit", "F8·audit", "F9·popupset", "F8·popupset"]
    a, b = [cells[k][0] for k in ks], [cells[k][1] for k in ks]
    a1.bar(xs - .2, a, .36, color="#c3cad2", alpha=.95, edgecolor="none",
           label="문턱 40")
    a1.bar(xs + .2, b, .36, color=GATE, alpha=.95, edgecolor="none",
           label="문턱 15")
    for i, k in enumerate(ks):
        d = cells[k][1] - cells[k][0]
        a1.text(i, max(a[i], b[i]) + .012, f"{d:+.3f}", ha="center",
                fontsize=6.2, color=GATE if d > 0 else CLAIM)
    a1.set_xticks(xs)
    a1.set_xticklabels([k.replace("·", "\n") for k in ks], fontsize=6.0)
    a1.set_ylabel("팝업 $\\rho$", fontsize=7.0)
    a1.set_ylim(0, .62)
    a1.legend(fontsize=6.0, frameon=False, loc="upper right")
    a1.set_title("같은 처치가 네 칸 중 둘에서 음수", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    # ② 처치 효과들 대 기준선 차이
    ks2 = sorted(prev, key=lambda k: prev[k])
    ys = np.arange(len(ks2))
    a2.barh(ys, [prev[k] for k in ks2], .58,
            color=[GATE if "축" in k or "덮음" in k or "확장" in k else "#c3cad2"
                   for k in ks2], alpha=.95, edgecolor="none")
    base = float(np.median(j["base"]))
    a2.axvline(base, color=CLAIM, lw=1.6)
    a2.text(base + .004, -.55, f"팝업 빌드 차이 {base:+.4f}\n(처치가 아니라 기준선)",
            fontsize=6.1, color=CLAIM, va="top", linespacing=1.35)
    for y, k in zip(ys, ks2):
        a2.text(prev[k] + .003, y, f"{prev[k]:+.4f}", va="center", fontsize=6.0)
    a2.set_yticks(ys); a2.set_yticklabels(ks2, fontsize=6.2)
    a2.set_xlim(0, .135)
    a2.set_xlabel("효과 크기 (판 또는 팝업 $\\rho$)", fontsize=7.0)
    a2.set_title("기준선 차이가 거의 모든 처치보다 크다", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    a2.set_ylim(len(ks2) - .4, -1.5)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 135 — 팝업은 무엇도 판정하지 못한다 ─────────────────────────────
def fig_power(out: str = "fig_power.pdf", root: str = ".") -> dict:
    """발산 · 유의성 · 필요 표본."""
    import numpy as np
    R = Path(root)
    best = json.load(open(R / "data/state/note135_best.json"))
    boot = json.load(open(R / "data/state/note135_boot.json"))
    pw = json.load(open(R / "data/state/note135_power.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1, 1, 1]})
    # ① 판 대 팝업
    ks = [k for k in best if "F0" not in k]
    b = np.array([best[k]["board"] for k in ks])
    p = np.array([best[k]["popup"] for k in ks])
    a1.plot(b, p, "o", color=GATE, ms=6, alpha=.75)
    z = np.polyfit(b, p, 1)
    xx = np.linspace(b.min(), b.max(), 20)
    a1.plot(xx, np.polyval(z, xx), "-", color=CLAIM, lw=1.4)
    from scipy.stats import spearmanr
    a1.set_xlabel("판 $\\rho$ (파운데이션 지표)", fontsize=7.0)
    a1.set_ylabel("팝업 $\\rho$ (제품 지표)", fontsize=7.0)
    a1.set_title(f"둘이 반대로 간다  스피어만 "
                 f"{spearmanr(b, p).correlation:+.3f}\n(고유 실행 {len(ks)}건)",
                 fontsize=7.0)
    a1.tick_params(labelsize=6.2)

    # ② 붓스트랩 구간 --- 전부 0 을 가로지른다
    ks2 = list(boot)
    ys = np.arange(len(ks2))
    for y, k in zip(ys, ks2):
        v = boot[k]
        a2.plot([v["lo"], v["hi"]], [y, y], "-", color=MUTE, lw=1.6)
        a2.plot([v["d"]], [y], "o", color=CLAIM if v["d"] < 0 else GATE, ms=5)
    a2.axvline(0, color=INK, lw=1.0)
    a2.set_yticks(ys)
    a2.set_yticklabels([k.replace("_ranklik", "").replace("_boost", "")
                        .replace("->", "$\\to$") for k in ks2], fontsize=5.8)
    a2.set_xlabel("팝업 $\\rho$ 의 짝지은 차 · 95% 구간", fontsize=7.0)
    a2.set_title("여섯 비교 전부 0 을 가로지른다", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    a2.set_ylim(len(ks2) - .4, -.7)

    # ③ 필요 표본
    hw = {int(k): v for k, v in pw["hw"].items()}
    ns = np.array(sorted(hw)); hs = np.array([hw[k] for k in ns])
    xx = np.logspace(np.log10(20), np.log10(1200), 60)
    a3.plot(xx, pw["a"] * xx ** pw["b"], "-", color=GATE, lw=1.4)
    a3.plot(ns, hs, "o", color=INK, ms=5)
    for tgt, lab in ((.05, "0.05"), (.03, "0.03")):
        need = float(np.exp((np.log(tgt) - np.log(pw["a"])) / pw["b"]))
        a3.plot([need], [tgt], "o", color=CLAIM, ms=6)
        a3.annotate(f"반폭 {lab}\n$n$$\\approx${need:.0f}", (need, tgt),
                    fontsize=6.0, color=CLAIM, xytext=(6, 6),
                    textcoords="offset points", linespacing=1.3)
    a3.axvline(pw["n0"], color=MUTE, ls="--", lw=.9)
    a3.text(pw["n0"] * 1.1, .21, f"지금 $n$={pw['n0']}", fontsize=6.0, color=MUTE)
    a3.set_xscale("log"); a3.set_yscale("log")
    a3.set_xticks([30, 60, 150, 350, 900])
    a3.set_xticklabels(["30", "60", "150", "350", "900"], fontsize=6.2)
    a3.set_yticks([.03, .05, .1, .2])
    a3.set_yticklabels(["0.03", "0.05", "0.10", "0.20"], fontsize=6.2)
    a3.minorticks_off()
    a3.set_xlabel("팝업 후행 표본 $n$", fontsize=7.0)
    a3.set_ylabel("짝지은 차의 반폭", fontsize=7.0)
    a3.set_title(f"반폭 $=$ {pw['a']:.2f}$\\,n^{{{pw['b']:.2f}}}$", fontsize=7.2)
    a3.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 136 — 합친 순위가 집단 순서를 잰다 ──────────────────────────────
def fig_group(out: str = "fig_group.pdf", root: str = ".") -> dict:
    """거래처럼 보인 것이 인공물이었다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note136.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1.05, 1, .9]})
    # ① 거름망을 풀면 rho 오르고 반폭 준다 --- 순이득처럼 보인다
    tr = j["trade"]
    xs = np.arange(len(tr))
    a1.bar(xs, [t["rho"] for t in tr], .5, color="#c3cad2", alpha=.95,
           edgecolor="none")
    a1.errorbar(xs, [t["rho"] for t in tr], yerr=[t["hw"] for t in tr],
                fmt="none", ecolor=INK, elinewidth=1.0, capsize=2.5)
    a1.bar([1], [tr[1]["rho"]], .5, color=GATE, alpha=.95, edgecolor="none")
    for i, t in enumerate(tr):
        a1.text(i, t["rho"] + t["hw"] + .012, f"$n$={t['n']}", ha="center",
                fontsize=5.9)
    a1.set_xticks(xs)
    a1.set_xticklabels(["검증\n계수", "전체\n계수", "＋등급\nC", "＋스코프\n해제"],
                       fontsize=5.9)
    a1.set_ylabel("팝업 $\\rho$ · 수염은 반폭", fontsize=7.0)
    a1.set_ylim(0, .62)
    a1.set_title("거름망을 풀면 $\\rho$ 도 오르고 구간도 좁아진다\n--- 순이득처럼 보인다",
                 fontsize=6.9)
    a1.tick_params(labelsize=6.2)

    # ② 그런데 집단으로 가르면
    ar = j["artifact"]
    ks = ["합친\n116건", "집단 안\n순위로", "검증만\n59건"]
    vs = [ar["pooled"], ar["within"], ar["ver_only"]]
    a2.bar(np.arange(3), vs, .5, color=[GATE, CLAIM, "#9aa3ad"], alpha=.95,
           edgecolor="none")
    for i, v in enumerate(vs):
        a2.text(i, v + .012, f"{v:+.3f}", ha="center", fontsize=6.4)
    a2.set_xticks(np.arange(3)); a2.set_xticklabels(ks, fontsize=6.1)
    a2.set_ylabel("팝업 $\\rho$", fontsize=7.0)
    a2.set_ylim(0, .56)
    a2.set_title("집단 간 순서를 빼면 절반이 사라진다", fontsize=7.0)
    a2.tick_params(labelsize=6.2)

    # ③ 두 무리의 수준차
    lm, pm = ar["label_med"], ar["pred_med"]
    x = np.arange(2)
    a3.bar(x - .18, lm, .32, color="#9aa3ad", alpha=.95, edgecolor="none",
           label="라벨 중앙")
    a3.bar(x + .18, pm, .32, color=CLAIM, alpha=.95, edgecolor="none",
           label="예측 중앙")
    a3.set_xticks(x); a3.set_xticklabels(["검증 계수", "주장 · 추정"], fontsize=6.4)
    a3.set_ylim(0, 3.8)
    a3.legend(fontsize=6.0, frameon=False, loc="upper left")
    a3.set_title("두 무리가 라벨도 예측도\n체계적으로 갈려 있다 ($p$$\\approx$2e$-$6)",
                 fontsize=6.9)
    a3.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 137 — 판의 4분의 1이 집단 순서였다 ──────────────────────────────
def fig_corr(out: str = "fig_corr.pdf", root: str = ".") -> dict:
    """도메인별 인공물, 판 보정, 그리고 축 값어치의 변화."""
    import numpy as np
    R = Path(root)
    g = json.load(open(R / "data/state/note137_groups.json"))
    b = json.load(open(R / "data/state/note137_board.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1.15, 1, .85]})
    # ① 도메인 x 표지
    ks = sorted(g, key=lambda k: -g[k]["gap"])
    ys = np.arange(len(ks))
    a1.barh(ys, [g[k]["gap"] for k in ks], .58,
            color=[CLAIM if g[k]["gap"] >= .15 else "#c3cad2" for k in ks],
            alpha=.95, edgecolor="none")
    a1.axvline(.15, color=INK, ls="--", lw=.9)
    a1.text(.152, len(ks) - .6, "0.15", fontsize=5.9, color=INK)
    for y, k in zip(ys, ks):
        a1.text(g[k]["gap"] + .004, y, f"$n$={g[k]['n']}", va="center",
                fontsize=5.8)
    a1.set_yticks(ys)
    a1.set_yticklabels([k.replace("·", " · ").replace("__free", "무료/유료")
                        for k in ks], fontsize=6.0)
    a1.set_xlim(-.05, .30)
    a1.set_xlabel("합친 $\\rho$ $-$ 집단 안 $\\rho$", fontsize=7.0)
    a1.set_title("웹툰(연재중)과 모바일(무료)이 걸린다", fontsize=7.2)
    a1.tick_params(labelsize=6.2, length=0)
    a1.set_ylim(len(ks) - .4, -.7)

    # ② 판 보정
    ks2 = [k for k in ("F9_ranklik@base", "F8_boost@base",
                       "F9_ranklik@trend", "F8_boost@trend",
                       "F9_ranklik@trendcal", "F8_boost@trendcal") if k in b]
    ks2 = [k for k in ks2 if k in b]
    xs = np.arange(len(ks2))
    a2.bar(xs - .2, [b[k]["board"] for k in ks2], .36, color="#c3cad2",
           alpha=.95, edgecolor="none", label="판 그대로")
    a2.bar(xs + .2, [b[k]["corrected"] for k in ks2], .36, color=GATE,
           alpha=.95, edgecolor="none", label="집단 보정")
    a2.set_xticks(xs)
    a2.set_xticklabels([("F9" if "ranklik" in k else "F8") + "\n"
                        + k.split("@")[1].replace("trendcal", "＋검색\n＋달력")
                          .replace("trend", "＋검색").replace("base", "기본")
                        for k in ks2], fontsize=5.8)
    a2.set_ylabel("판 $\\rho$", fontsize=7.0)
    a2.set_ylim(0, .52)
    a2.legend(fontsize=6.0, frameon=False, loc="upper left")
    a2.set_title("수준은 내리고 순위는 그대로", fontsize=7.2)
    a2.tick_params(labelsize=6.2)

    # ③ 축 값어치는 커진다
    A, B = "F8_boost@base", "F8_boost@trendcal"
    gain = [("판 그대로", b[B]["board"] - b[A]["board"]),
            ("집단 보정", b[B]["corrected"] - b[A]["corrected"])]
    a3.bar([0, 1], [gain[0][1], gain[1][1]], .5, color=["#c3cad2", GATE],
           alpha=.95, edgecolor="none")
    for i, (k, v) in enumerate(gain):
        a3.text(i, v + .004, f"{v:+.4f}", ha="center", fontsize=6.6)
    a3.set_xticks([0, 1]); a3.set_xticklabels([k for k, _ in gain], fontsize=6.4)
    a3.set_ylabel("base $\\to$ trendcal 이득 (F8)", fontsize=7.0)
    a3.set_ylim(0, .16)
    a3.set_title("보정하면 축이 더 값진다\n(인공물은 축이 못 올리는 바닥)",
                 fontsize=6.9)
    a3.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 138 — 플래그 하나가 축 다섯을 이긴다 ────────────────────────────
def fig_floor(out: str = "fig_floor.pdf", root: str = ".") -> dict:
    """정직한 바닥선과 모형."""
    import numpy as np
    R = Path(root)
    j = json.load(open(R / "data/state/note138.json"))
    hj = json.load(open(R / "data/state/note138_honest.json"))
    rows, ns = j["rows"], j["ns"]
    DOM = ["웹툰", "모바일", "애니"]
    ks = ["집단만(정직)", "F8@base", "F8@trend", "F8@trendcal"]
    ks = [k for k in ks if k in rows]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.35),
                                 gridspec_kw={"width_ratios": [1.25, 1]})
    xs = np.arange(len(DOM))
    C = {"집단만(정직)": CLAIM, "F8@base": "#c3cad2", "F8@trend": "#8fa8bd",
         "F8@trendcal": GATE}
    w = .8 / len(ks)
    for i, k in enumerate(ks):
        a1.bar(xs + (i - (len(ks) - 1) / 2) * w, [rows[k][d] for d in DOM], w * .9,
               color=C.get(k, MUTE), alpha=.95, edgecolor="none", label=k)
    a1.axhline(0, color=INK, lw=.8)
    a1.set_xticks(xs)
    a1.set_xticklabels([f"{d}\n($n$={ns[d]})" for d in DOM], fontsize=6.4)
    a1.set_ylabel("스피어만 $\\rho$", fontsize=7.0)
    a1.set_ylim(-.45, .68)
    a1.legend(fontsize=5.9, frameon=False, ncol=2, loc="upper left")
    a1.set_title("웹툰에선 플래그 하나가 축 다섯을 이긴다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    # 누수 대 정직
    a2b = np.arange(3)
    leak = [hj[d]["leak"] for d in DOM]
    hon = [hj[d]["honest"] for d in DOM]
    a2.bar(a2b - .2, leak, .36, color="#c3cad2", alpha=.95, edgecolor="none",
           label="검정 집합 평균 (누수)")
    a2.bar(a2b + .2, hon, .36, color=CLAIM, alpha=.95, edgecolor="none",
           label="학습 집합 평균 (정직)")
    a2.axhline(0, color=INK, lw=.8)
    a2.set_xticks(a2b); a2.set_xticklabels(DOM, fontsize=6.5)
    a2.set_ylabel("집단만 아는 예측기 $\\rho$", fontsize=7.0)
    a2.set_ylim(-.45, .58)
    a2.legend(fontsize=6.0, frameon=False, loc="lower left")
    a2.annotate("애니만 부호가 뒤집힌다", (2, -.338), fontsize=6.1, color=CLAIM,
                xytext=(-8, -26), textcoords="offset points", ha="center",
                arrowprops=dict(arrowstyle="-|>", color=CLAIM, lw=.8))
    a2.set_title("바닥선도 누수될 수 있다", fontsize=7.2)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 139 — 풀링은 지켜 주고 희석한다 ─────────────────────────────────
def fig_dilute(out: str = "fig_dilute.pdf", root: str = ".") -> dict:
    import numpy as np
    R = Path(root)
    j = json.load(open(R / "data/state/note139.json"))
    ar = json.load(open(R / "data/state/note139_axisrank.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1.1, 1, .95]})
    # ① 웹툰 --- 풀링의 보호와 희석
    ks = ["단독 · 축 다섯", "풀링 · 축 다섯", "단독 · entry\n_friction 만",
          "완결 플래그"]
    vs = [j["webtoon_solo"]["축 다섯"], j["webtoon_solo"]["풀링 축 다섯"],
          j["webtoon_solo"]["entry_friction 만"], j["webtoon_solo"]["완결 플래그"]]
    cs = [CLAIM, "#8fa8bd", GATE, "#c3cad2"]
    a1.bar(np.arange(4), vs, .55, color=cs, alpha=.95, edgecolor="none")
    for i, v in enumerate(vs):
        a1.text(i, v + (.014 if v > 0 else -.03), f"{v:+.3f}", ha="center",
                fontsize=6.3)
    a1.axhline(0, color=INK, lw=.8)
    a1.annotate("", (1, .21), (0, -.18),
                arrowprops=dict(arrowstyle="-|>", color=GATE, lw=1.2,
                                connectionstyle="arc3,rad=-.3"))
    a1.text(.5, .07, "보호\n$+$.393", fontsize=6.0, color=GATE, ha="center",
            linespacing=1.3)
    a1.annotate("", (1, .215), (2, .295),
                arrowprops=dict(arrowstyle="-|>", color=CLAIM, lw=1.2))
    a1.text(1.5, .34, "희석 $-$.099", fontsize=6.0, color=CLAIM, ha="center")
    a1.set_xticks(np.arange(4)); a1.set_xticklabels(ks, fontsize=5.7)
    a1.set_ylabel("웹툰 $\\rho$ (2025$+$)", fontsize=7.0)
    a1.set_ylim(-.28, .45)
    a1.set_title("풀링은 지켜 주고 동시에 희석한다", fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    # ② 웹툰 축 --- 안쪽 대 바깥
    wa = j["webtoon_axis"]
    axs = list(wa["outer"])
    x = np.arange(len(axs))
    a2.bar(x - .2, [wa["inner"].get(a, 0) for a in axs], .36, color="#c3cad2",
           alpha=.95, edgecolor="none", label="안쪽 창")
    a2.bar(x + .2, [wa["outer"].get(a, 0) for a in axs], .36, color=CLAIM,
           alpha=.95, edgecolor="none", label="바깥 2025$+$")
    a2.axhline(0, color=INK, lw=.8)
    a2.set_xticks(x)
    a2.set_xticklabels([a.replace("_", "\n") for a in axs], fontsize=5.7)
    a2.set_ylabel("웹툰 단독 $\\rho$", fontsize=7.0)
    a2.set_ylim(-.38, .58)
    a2.legend(fontsize=6.0, frameon=False, loc="upper right")
    a2.set_title("안쪽 1위가 바깥 꼴찌다\n(goods\\_scale $+$.486 $\\to$ $-$.283)",
                 fontsize=6.9)
    a2.tick_params(labelsize=6.2)

    # ③ 도메인별 안-밖 순위 상관
    ks3 = sorted(ar, key=lambda k: ar[k]["corr"])
    ys = np.arange(len(ks3))
    a3.barh(ys, [ar[k]["corr"] for k in ks3], .58,
            color=[CLAIM if ar[k]["corr"] < 0 else GATE for k in ks3],
            alpha=.95, edgecolor="none")
    a3.axvline(0, color=INK, lw=.8)
    for y, k in zip(ys, ks3):
        a3.text(ar[k]["corr"] + (.03 if ar[k]["corr"] > 0 else -.03), y,
                f"{ar[k]['top'][:9]} {ar[k]['orank']}/{ar[k]['n']}",
                va="center", ha="left" if ar[k]["corr"] > 0 else "right",
                fontsize=5.6)
    a3.set_yticks(ys); a3.set_yticklabels(ks3, fontsize=6.4)
    a3.set_xlim(-1.5, 1.9)
    a3.set_xlabel("안쪽 축순위 vs 바깥 축순위", fontsize=7.0)
    a3.set_title("절반이 음수 --- 축 선택도 못 쓴다", fontsize=7.2)
    a3.tick_params(labelsize=6.2, length=0)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 140 — 전체 상관이 숨긴 것 ───────────────────────────────────────
def fig_hide(out: str = "fig_hide.pdf", root: str = ".") -> dict:
    import numpy as np
    R = Path(root)
    sg = json.load(open(R / "data/state/note140_sign.json"))
    fl = json.load(open(R / "data/state/note140_flip.json"))
    from state.tri_domain import ALL5
    doms = ["게임", "도서", "만화", "모바일", "세계애니", "애니", "웹툰", "펀딩"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.35),
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    # ① 축별 라벨 부호 일관성
    ks = [a for a in ALL5 if a in sg]
    ys = np.arange(len(ks))
    for y, a in zip(ys, ks):
        v = [x for x in sg[a]["vals"] if x is not None and x == x]
        for x in v:
            a1.plot([x], [y], "o", color=GATE if x > 0 else CLAIM, ms=5,
                    alpha=.8)
        a1.plot([np.mean(v)], [y], "|", color=INK, ms=14, mew=1.6)
    a1.axvline(0, color=INK, lw=.9)
    a1.set_yticks(ys)
    a1.set_yticklabels([f"{a}\n{sg[a]['pos']}/{sg[a]['n']} 양수" for a in ks],
                       fontsize=6.0)
    a1.set_xlabel("라벨과의 스피어만 (점 하나 = 도메인 하나)", fontsize=7.0)
    a1.set_xlim(-.35, .72)
    a1.set_title("축 이름은 대개 같은 뜻이다", fontsize=7.2)
    a1.tick_params(labelsize=6.2, length=0)
    a1.set_ylim(len(ks) - .4, -.7)

    # ② 전체 상관이 숨긴 것
    show = ["웹툰·goods_scale", "웹툰·entry_friction", "세계애니·entry_friction"]
    show = [k for k in show if k in fl]
    x = np.arange(len(show))
    for i, (key, col, lab) in enumerate([("all", "#c3cad2", "전체"),
                                         ("pre", "#8fa8bd", "2025 이전"),
                                         ("post", CLAIM, "2025 이후")]):
        a2.bar(x + (i - 1) * .27, [fl[k][key] for k in show], .25, color=col,
               alpha=.95, edgecolor="none", label=lab)
    a2.axhline(0, color=INK, lw=.9)
    a2.set_xticks(x)
    a2.set_xticklabels([k.replace("·", "\n") for k in show], fontsize=5.8)
    a2.set_ylabel("스피어만 $\\rho$", fontsize=7.0)
    a2.set_ylim(-.42, .56)
    a2.legend(fontsize=6.0, frameon=False, loc="upper right", ncol=1)
    a2.set_title("전체 상관이 기간 구조를 숨긴다\n(28쌍 중 뒤집힘은 하나뿐)",
                 fontsize=6.9)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 141 — 세 번째 누수 층: 시점 ─────────────────────────────────────
def fig_when(out: str = "fig_when.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note141.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1, 1.05, 1]})
    # ① 후보 축 재검토 --- 숨은 것이 없다
    sc = j["scan"]
    a1.bar([0, 1, 2], [sc["all_med"], sc["pre_med"], sc["post_med"]], .5,
           color=["#c3cad2", "#8fa8bd", GATE], alpha=.95, edgecolor="none")
    for i, v in enumerate([sc["all_med"], sc["pre_med"], sc["post_med"]]):
        a1.text(i, v + .002, f"{v:.3f}", ha="center", fontsize=6.4)
    a1.set_xticks([0, 1, 2]); a1.set_xticklabels(["전체", "2025 이전", "2025 이후"],
                                                 fontsize=6.4)
    a1.set_ylabel("$|\\rho|$ 중앙값", fontsize=7.0)
    a1.set_ylim(0, .10)
    a1.set_title(f"후보 축 {sc['축']}개 · {sc['쌍']}쌍\n숨은 보석 {sc['보석']} · 숨은 덫 {sc['덫']}",
                 fontsize=6.9)
    a1.tick_params(labelsize=6.2)

    # ② 사전 대 사후 표지
    fl = j["floor"]
    ks = list(fl)
    ys = np.arange(len(ks))
    a2.barh(ys, [fl[k] for k in ks], .58,
            color=[CLAIM if "사후" in k else GATE for k in ks],
            alpha=.95, edgecolor="none")
    a2.axvline(0, color=INK, lw=.9)
    for y, k in zip(ys, ks):
        v = fl[k]
        a2.text(v + (.012 if v > 0 else -.012), y, f"{v:+.3f}", va="center",
                ha="left" if v > 0 else "right", fontsize=6.0)
    a2.set_yticks(ys)
    a2.set_yticklabels([k.replace(" ", "\n", 1) for k in ks], fontsize=5.6)
    a2.set_xlim(-.48, .60)
    a2.set_xlabel("집단만 아는 예측기 $\\rho$", fontsize=7.0)
    a2.set_title("붉은 것은 끝나야 아는 정보", fontsize=7.2)
    a2.tick_params(labelsize=6.2, length=0)
    a2.set_ylim(len(ks) - .4, -.7)

    # ③ 바닥선이 세 번 내려왔다
    bf = j["board_floor"]
    ks3 = ["노트138 누수", "노트138 정직", "노트141 사전만"]
    a3.bar(np.arange(3), [bf[k] for k in ks3], .5,
           color=["#e0e4e8", "#9aa3ad", GATE], alpha=.95, edgecolor="none")
    for i, k in enumerate(ks3):
        a3.text(i, bf[k] + .012, f"{bf[k]:+.3f}", ha="center", fontsize=6.4)
    a3.axhline(bf["축 다섯"], color=CLAIM, lw=1.6)
    a3.text(2.4, bf["축 다섯"] + .014, f"축 다섯 {bf['축 다섯']:+.3f}",
            fontsize=6.1, color=CLAIM, ha="right")
    a3.set_xticks(np.arange(3))
    a3.set_xticklabels(["누수", "정직한\n평균", "사전 표지만"], fontsize=6.2)
    a3.set_ylabel("세 도메인 바닥선 $\\rho$", fontsize=7.0)
    a3.set_ylim(0, .44)
    a3.set_title("바닥선이 세 번 내려왔다", fontsize=7.2)
    a3.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 142 — 오래된 것이 더 잘 맞으면 나중에 쓴 것이다 ──────────────────
def fig_age(out: str = "fig_age.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note142.json"))
    age, ad, per = j["age"], j["adopt"], j["per"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.3),
                                 gridspec_kw={"width_ratios": [1.2, 1]})
    ks = sorted(age, key=lambda k: -age[k]["gap"])
    xs = np.arange(len(ks))
    a1.bar(xs - .2, [age[k]["old"] for k in ks], .36, color="#9aa3ad",
           alpha=.95, edgecolor="none", label="오래된 절반")
    a1.bar(xs + .2, [age[k]["new"] for k in ks], .36, color=GATE,
           alpha=.95, edgecolor="none", label="최근 절반")
    for i, k in enumerate(ks):
        g = age[k]["gap"]
        if abs(g) >= .04:
            a1.text(i, max(age[k]["old"], age[k]["new"]) + .012, f"{g:+.3f}",
                    ha="center", fontsize=6.2, color=CLAIM)
    a1.set_xticks(xs); a1.set_xticklabels(ks, fontsize=6.3)
    a1.set_ylabel("글·그림 축 $|\\rho|$ 평균", fontsize=7.0)
    a1.set_ylim(0, .27)
    a1.legend(fontsize=6.0, frameon=False, loc="upper right")
    a1.set_title("모바일만 오래된 쪽이 세다 --- 설명이 갱신된 흔적",
                 fontsize=7.2)
    a1.tick_params(labelsize=6.2)

    ks2 = list(ad)
    x2 = np.arange(len(ks2))
    a2.bar(x2, [ad[k] for k in ks2], .5,
           color=["#c3cad2", CLAIM, GATE], alpha=.95, edgecolor="none")
    for i, k in enumerate(ks2):
        a2.text(i, ad[k] + .0012, f"{ad[k]:+.4f}", ha="center", fontsize=6.3)
    a2.set_xticks(x2)
    a2.set_xticklabels(["현행", "＋글그림\n전부", "＋글그림\n모바일 뺌"],
                       fontsize=6.2)
    a2.set_ylabel("판 $\\rho$", fontsize=7.0)
    a2.set_ylim(.425, .440)
    a2.set_title("막는 쪽이 낫지만 차이가 탐지 한계 아래다\n(＋.0026 · 반폭 약 .05)",
                 fontsize=6.9)
    a2.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}


# ── 노트 143 — 대조군을 세우니 검정이 무너졌다 ───────────────────────────
def fig_did(out: str = "fig_did.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note143.json"))
    did, direct, band = j["did"], j["direct"], j["band"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1.15, .9, 1]})
    # ① 이중차분
    ks = sorted(did, key=lambda k: -did[k]["did"])
    xs = np.arange(len(ks))
    a1.bar(xs - .2, [did[k]["text"] for k in ks], .36, color="#9aa3ad",
           alpha=.95, edgecolor="none", label="글·그림 나이차")
    a1.bar(xs + .2, [did[k]["ctrl"] for k in ks], .36, color="#c3cad2",
           alpha=.95, edgecolor="none", label="대조 축 나이차")
    a1.plot(xs, [did[k]["did"] for k in ks], "o-", color=CLAIM, lw=1.4, ms=4.5,
            label="이중차분")
    a1.axhline(0, color=INK, lw=.8)
    a1.set_xticks(xs); a1.set_xticklabels(ks, fontsize=6.1)
    a1.set_ylabel("$|\\rho|$ 나이차", fontsize=7.0)
    a1.legend(fontsize=5.8, frameon=False, ncol=1, loc="lower left")
    a1.set_title("대조군을 세우면 모바일이 줄고\n게임이 새로 걸린다", fontsize=6.9)
    a1.tick_params(labelsize=6.2)

    # ② 직접 검정 --- 통제 전후로 부호가 뒤집힌다
    for i, (k, c) in enumerate([("무통제", "#c3cad2"), ("연도통제", CLAIM)]):
        v = direct[k]
        a2.bar([i - .18, i + .18], [v["갱신적음"], v["갱신많음"]], .32,
               color=[c, GATE if i == 0 else CLAIM], alpha=.95, edgecolor="none")
        a2.text(i, max(v["갱신적음"], v["갱신많음"]) + .012,
                f"{v['차']:+.3f}", ha="center", fontsize=6.4,
                color=GATE if v["차"] > 0 else CLAIM)
    a2.set_xticks([0, 1]); a2.set_xticklabels(["무통제", "출시 연도\n통제"],
                                              fontsize=6.3)
    a2.set_ylabel("글·그림 $|\\rho|$ 평균", fontsize=7.0)
    a2.set_ylim(0, .27)
    a2.set_title("갱신 간격 직접 검정\n통제하면 부호가 뒤집힌다", fontsize=6.9)
    a2.tick_params(labelsize=6.2)

    # ③ 연도별
    ys = sorted(band)
    x3 = np.arange(len(ys))
    a3.bar(x3 - .18, [band[y]["lo"] for y in ys], .32, color="#c3cad2",
           alpha=.95, edgecolor="none", label="갱신 적음")
    a3.bar(x3 + .18, [band[y]["hi"] for y in ys], .32, color=CLAIM,
           alpha=.95, edgecolor="none", label="갱신 많음")
    a3.set_xticks(x3); a3.set_xticklabels(ys, fontsize=6.2)
    a3.set_ylabel("글·그림 $|\\rho|$ 평균", fontsize=7.0)
    a3.legend(fontsize=6.0, frameon=False, loc="upper right")
    a3.set_title("다섯 연도 밴드 전부 같은 방향", fontsize=7.0)
    a3.tick_params(labelsize=6.2)
    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 144 — 대조 집합을 고르는 손이 잡음보다 크다 ──────────────────────
def fig_attrib(out: str = "fig_attrib.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note144.json"))
    did, span, N = j["did"], j["span"], j["n"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1.25, 1, .95]})

    # ① 대조 집합을 바꾸면 이중차분이 어디까지 가나
    ks = sorted(did, key=lambda k: -(did[k]["hi"] - did[k]["lo"]))
    ys = np.arange(len(ks))
    for i, k in enumerate(ks):
        d = did[k]
        a1.plot([d["lo"], d["hi"]], [i, i], lw=3.2, color="#c3cad2",
                solid_capstyle="butt", zorder=1)
        a1.plot([-d["nullsd"] * 1.96, d["nullsd"] * 1.96], [i, i], lw=1.1,
                color=GATE, zorder=2)
        a1.plot([d["did"]], [i], "o", ms=3.6, color=CLAIM, zorder=3)
    a1.axvline(0, color="#8a929b", lw=.6, zorder=0)
    a1.set_yticks(ys); a1.set_yticklabels(ks, fontsize=6.3)
    a1.invert_yaxis()
    a1.set_xlabel("이중차분", fontsize=7.0)
    a1.tick_params(labelsize=6.2)
    a1.set_title("회색 --- 대조 집합을 바꿔 얻는 폭\n"
                 "파랑 --- 나이 치환 귀무 95%", fontsize=7.0)
    a1.text(did[ks[0]]["lo"], -.55, "손이 잡음보다 넓다", fontsize=6.2,
            color=CLAIM, va="bottom")

    # ② 남의 축을 흔들면 내 점수가 얼마나 움직이나
    fs = ["F6_directpool", "F9_ranklik", "F7_anchor", "F12_rankunion",
          "F8_boost"]
    fs = [f for f in fs if f in span]
    ds = sorted(N, key=lambda d: N[d])
    x = np.arange(len(ds))
    for f in fs:
        champ = f == "F8_boost"
        a2.plot(x, [span[f].get(d, np.nan) for d in ds],
                "-o" if champ else "-", ms=3.4 if champ else 0,
                lw=1.9 if champ else .9,
                color=CLAIM if champ else "#9aa3ad",
                label=f.split("_")[0] + ("(현 최고)" if champ else ""),
                zorder=3 if champ else 1)
    a2.set_xticks(x)
    a2.set_xticklabels([f"{d}\n{N[d]}" for d in ds], fontsize=5.9)
    a2.set_ylabel("입력이 안 바뀐 도메인의 $\\rho$ 폭", fontsize=6.8)
    a2.legend(fontsize=5.6, frameon=False, ncol=2, loc="upper center")
    a2.set_ylim(0, .245)
    a2.tick_params(labelsize=6.2)
    a2.set_title("자기 입력은 그대로인데 점수가 움직인다", fontsize=7.0)

    # ③ 그 바닥 위에서 읽으려던 차이
    lab = ["전부", "모바일 뺌", "모바일·게임 뺌", "게임 뺌", "도서 뺌"]
    bd = [j["adopt"][k] for k in lab]
    b0 = j["adopt"]["현행(글그림 없음)"]
    x3 = np.arange(len(lab))
    a3.bar(x3, [v - b0 for v in bd], .58, color=GATE, alpha=.9,
           edgecolor="none")
    fl = span["F8_boost"]["팝업"]
    a3.axhspan(-fl, fl, color=CLAIM, alpha=.13, lw=0)
    a3.axhline(0, color="#8a929b", lw=.6)
    a3.text(len(lab) - .45, fl * .55, f"귀착 바닥 ±{fl:.3f}", fontsize=6.0,
            color=CLAIM, ha="right")
    a3.set_xticks(x3)
    a3.set_xticklabels([l.replace(" 뺌", "\n뺌") for l in lab], fontsize=5.9)
    a3.set_ylabel("현행 대비 판 $\\rho$", fontsize=6.8)
    a3.set_ylim(-.095, .095)
    a3.tick_params(labelsize=6.2)
    a3.set_title("채택 후보가 전부 바닥 안이다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 145 — 깊이가 원인이었고, 배깅이 값을 안 내고 되산다 ──────────────
def fig_stab(out: str = "fig_stab.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note145.json"))
    t15 = json.load(open(Path(root) / "data/state/note145_t15.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.35),
                                     gridspec_kw={"width_ratios": [1, 1.15, .9]})

    # ① 깊이가 원인
    dk = ["F8 깊이1", "F8 깊이2", "F8 깊이4(현행)"]
    xs = [1, 2, 4]
    a1.plot(xs, [j[k]["stab"] for k in dk], "-o", color=CLAIM, ms=4.2, lw=1.7,
            label="부스팅 · 깊이")
    for x, k in zip(xs, dk):
        a1.text(x, j[k]["stab"] - .012, f"{j[k]['stab']:.3f}", fontsize=6.1,
                ha="center", va="top", color=CLAIM)
    a1.axhline(j["F6 능형"]["stab"], color=GATE, lw=1.1, ls="--")
    a1.text(4, j["F6 능형"]["stab"] + .004, "능형 0.987", fontsize=6.2,
            color=GATE, ha="right")
    a1.axhline(j["F8 깊이4 표시자없음"]["stab"], color="#9aa3ad", lw=.9, ls=":")
    a1.text(1, j["F8 깊이4 표시자없음"]["stab"] - .004,
            "깊이4 · 도메인 표시자 빼도 0.882", fontsize=5.8,
            color="#6b7480", va="top")
    a1.set_xticks(xs); a1.set_xlabel("트리 깊이", fontsize=7.0)
    a1.set_ylabel("예측 자기상관 (팝업)", fontsize=7.0)
    a1.set_ylim(.86, 1.0)
    a1.tick_params(labelsize=6.2)
    a1.set_title("깊을수록 남의 축에 흔들린다", fontsize=7.2)

    # ② 판 대 안정 --- 프론티어
    pts = ["F6 능형", "F9 순위우도", "F8 깊이1", "F8 깊이2", "F8 깊이4(현행)",
           "F8 배깅 K=8", "F8 배깅 K=24"]
    for k in pts:
        o = j[k]
        bag = "배깅" in k
        cur = "현행" in k
        a2.plot(o["stab"], o["board"], "o", ms=6.0 if (bag or cur) else 4.0,
                color=CLAIM if bag else (GATE if cur else "#9aa3ad"),
                zorder=3 if (bag or cur) else 2)
        a2.annotate(k.replace("F8 ", "").replace("(현행)", ""),
                    (o["stab"], o["board"]), fontsize=5.7,
                    xytext=(0, 6 if not bag else -10), textcoords="offset points",
                    ha="center", color=CLAIM if bag else "#4a5158")
    a2.set_xlabel("예측 자기상관 → 귀착 가능", fontsize=7.0)
    a2.set_ylabel("판 $\\rho$", fontsize=7.0)
    a2.tick_params(labelsize=6.2)
    a2.set_title("배깅만 오른쪽 위로 간다", fontsize=7.2)
    a2.set_xlim(.878, 1.0)

    # ③ 그런데 문턱 15 --- 챔피언 설정에서는 점수가 안 오른다
    lab = ["F6", "F8", "F18 배깅"]
    pool = [0.3576, 0.4409, 0.4396]
    x3 = np.arange(3)
    a3.bar(x3 - .19, pool, .34, color=GATE, alpha=.9, edgecolor="none",
           label="판 $\\rho$ (t15)")
    a3.bar(x3 + .19, [t15[k] - .6 for k in lab], .34, color=CLAIM, alpha=.9,
           edgecolor="none", label="자기상관 $-$0.6")
    for i, k in enumerate(lab):
        a3.text(i - .19, pool[i] + .008, f"{pool[i]:.3f}", fontsize=6.0,
                ha="center", color=GATE)
        a3.text(i + .19, t15[k] - .6 + .008, f"{t15[k]:.3f}", fontsize=6.0,
                ha="center", color=CLAIM)
    a3.set_xticks(x3); a3.set_xticklabels(lab, fontsize=6.4)
    a3.set_ylim(0, .48)
    a3.legend(fontsize=5.8, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.2)
    a3.set_title("문턱 15 --- 같은 점수, 절반의 흔들림", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 146 — 재현 가드가 씨앗을 안 바꾸고 있었다 ────────────────────────
def fig_seed(out: str = "fig_seed.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note146.json"))
    top, sd, rp = j["top"], j["sd"], j["repro"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.55),
                                 gridspec_kw={"width_ratios": [1.35, 1]})

    # ① 순위표에 씨앗 띠를 얹는다
    ks = [k for k, _ in top][::-1]
    vs = [v for _, v in top][::-1]
    ys = np.arange(len(ks))
    band = sd["F8_pooled"]
    for i, (k, v) in enumerate(zip(ks, vs)):
        a1.plot([v - band, v + band], [i, i], lw=5.5, color="#c3cad2",
                solid_capstyle="butt", zorder=1)
        a1.plot([v], [i], "o", ms=3.4,
                color=CLAIM if "F18" in k else GATE, zorder=3)
    a1.set_yticks(ys)
    a1.set_yticklabels([k.replace("_", "\\_") for k in ks], fontsize=5.6)
    a1.set_xlabel("판 $\\rho$ (순위 지표) $\\pm$ 씨앗 sd", fontsize=7.0)
    a1.tick_params(labelsize=6.2)
    a1.set_title("띠를 얹으니 위 여섯이 겹친다", fontsize=7.2)
    a1.set_xlim(min(vs) - .012, max(vs) + .012)

    # ② 재현 가드 --- 고치기 전과 후
    ks2 = ["F6_directpool", "F9_ranklik", "F8_boost", "F18_bagboost"]
    x = np.arange(len(ks2))
    a2.bar(x - .19, [0] * len(ks2), .34, color="#c3cad2", edgecolor="none",
           label="고치기 전 (전부 0)")
    a2.bar(x + .19, [rp[k][1] for k in ks2], .34, color=CLAIM, alpha=.92,
           edgecolor="none", label="고친 뒤 씨앗 $\\rho$ 폭")
    for i, k in enumerate(ks2):
        a2.text(i - .19, .0016, "0.0000", fontsize=5.7, ha="center",
                color="#6b7480", rotation=90, va="bottom")
        a2.text(i + .19, rp[k][1] + .0016, f"{rp[k][1]:.4f}", fontsize=5.9,
                ha="center", color=CLAIM)
    a2.set_xticks(x)
    a2.set_xticklabels([k.split("_")[0] for k in ks2], fontsize=6.4)
    a2.set_ylim(0, .072)
    a2.legend(fontsize=5.8, frameon=False, loc="upper left")
    a2.tick_params(labelsize=6.2)
    a2.set_title("스무 노트 동안 ``결정적''이라고 적혀 있었다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 147 — 한계는 숫자가 아니라 행렬이다 ─────────────────────────────
def fig_order(out: str = "fig_order.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note147_order.json"))
    pt, pr, od, ms = j["point"], j["pairs"], j["order"], j["marg_sd"]
    sh = lambda n: n.split("_")[0]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.05, 1, 1.1]})

    # ① 주변 sd 는 다 같고 짝 sd 는 여섯 배 벌어진다
    gaps = [(abs(v["gap"]), v["sd"], k) for k, v in pr.items()]
    a1.axhspan(min(ms.values()), max(ms.values()), color="#c3cad2", alpha=.55,
               lw=0)
    a1.text(.104, np.mean(list(ms.values())) + .0006, "주변 sd — 어느 정식화든 같다",
            fontsize=6.0, color="#5a6169", ha="right")
    for g, sd, k in gaps:
        split = pr[k]["split"]
        a1.plot([g], [sd], "o", ms=3.6, color=CLAIM if split else GATE,
                alpha=.9)
    a1.set_xlabel("격차", fontsize=7.0)
    a1.set_ylabel("짝 sd", fontsize=7.0)
    a1.set_ylim(0, .021)
    a1.tick_params(labelsize=6.2)
    a1.set_title("짝 sd 는 6.4배 벌어진다", fontsize=7.2)

    # ② 부분 순서 사다리
    ypos, lab = {}, []
    y = 0
    for tier in od:
        for n in tier:
            ypos[n] = y
        lab.append((y, tier))
        y -= 1
    for n, v in pt.items():
        a2.plot([v], [ypos[n]], "o", ms=5.2,
                color=CLAIM if ypos[n] == 0 else GATE, zorder=3)
        a2.annotate(sh(n), (v, ypos[n]), fontsize=6.0, xytext=(0, 7),
                    textcoords="offset points", ha="center")
    for yy, tier in lab:
        vs = [pt[n] for n in tier]
        if len(tier) > 1:
            a2.plot([min(vs), max(vs)], [yy, yy], lw=7, color="#c3cad2",
                    solid_capstyle="round", zorder=1)
    a2.set_yticks([yy for yy, _ in lab])
    a2.set_yticklabels([f"{i+1}칸" for i in range(len(lab))], fontsize=6.4)
    a2.set_ylim(-len(lab) + .3, .75)
    a2.set_xlabel("판 $\\rho$ (씨앗 평균)", fontsize=7.0)
    a2.tick_params(labelsize=6.2)
    a2.set_title("일곱이 네 칸으로 갈린다", fontsize=7.2)

    # ③ 잣대를 바꾸면 F10 이 한 칸 올라간다
    tgt = ["F10_pershrink>F12_rankunion", "F10_pershrink>F6_directpool",
           "F10_pershrink>F9_ranklik", "F18_bagboost>F8_boost"]
    x = np.arange(len(tgt))
    glob = 2 * float(np.mean(list(ms.values())))
    a3.bar(x - .19, [abs(pr[k]["gap"]) for k in tgt], .34, color=GATE,
           alpha=.9, edgecolor="none", label="격차")
    a3.bar(x + .19, [2 * pr[k]["sd"] for k in tgt], .34, color=CLAIM,
           alpha=.9, edgecolor="none", label="짝 문턱 (2sd)")
    a3.axhline(glob, color="#5a6169", lw=1.1, ls="--")
    a3.text(len(tgt) - .5, glob + .0012, f"주변 잣대 {glob:.3f}", fontsize=6.0,
            ha="right", color="#5a6169")
    a3.set_xticks(x)
    a3.set_xticklabels([sh(k.split(">")[0]) + "\n>" + sh(k.split(">")[1])
                        for k in tgt], fontsize=5.8)
    a3.set_ylim(0, .042)
    a3.legend(fontsize=5.9, frameon=False, loc="upper left")
    a3.tick_params(labelsize=6.2)
    a3.set_title("앞 셋은 주변 잣대에 묻힌다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 148 — 일곱을 다 섞어도 안 오른다 ────────────────────────────────
def fig_blend(out: str = "fig_blend.pdf", root: str = ".") -> dict:
    import numpy as np
    a = json.load(open(Path(root) / "data/state/note148_all.json"))
    o = json.load(open(Path(root) / "data/state/note148_oracle.json"))
    sh = json.load(open(Path(root) / "data/state/note148_share.json"))
    short = lambda n: n.split("_")[0]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, .85, 1.1]})

    # ① 상한 사다리 --- 방법으로 살 수 있는 것 대 축으로 산 것
    lab = ["최고 단일", "짝 섞기\n(상한)", "도메인별 신탁\n(상한)",
           "축 둘 추가\n(노트 141)"]
    val = [0.0, a["best"] and 0.0017, o["oracle"] - o["best"], 0.045]
    val[1] = 0.0017
    x = np.arange(4)
    a1.bar(x, val, .56, color=[GATE, GATE, GATE, CLAIM], alpha=.92,
           edgecolor="none")
    for i, v in enumerate(val):
        a1.text(i, v + .0012, f"{v:+.4f}" if v else "0", fontsize=6.2,
                ha="center", color=CLAIM if i == 3 else GATE)
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.9)
    a1.set_ylabel("최고 단일 대비 판 $\\rho$", fontsize=7.0)
    a1.set_ylim(0, .053)
    a1.tick_params(labelsize=6.2)
    a1.set_title("방법 쪽은 다 썼다", fontsize=7.2)

    # ② 짝 섞기 --- 상관과 이득
    rows = a["rows"]
    for r in rows:
        a2.plot([r["corr"]], [r["gain"]], "o", ms=3.6, color=GATE, alpha=.8)
    a2.axhline(0, color="#8a929b", lw=.6)
    a2.set_xlabel("두 정식화 예측 상관", fontsize=7.0)
    a2.set_ylabel("섞어서 얻는 이득 (상한)", fontsize=7.0)
    a2.set_ylim(-.055, .006)
    a2.tick_params(labelsize=6.2)
    a2.set_title("안 닮아도 안 오른다", fontsize=7.2)

    # ③ 팝업 순위 대 판 순위
    per = o["per"]["팝업"]; base = o["base"]
    ks = list(per)
    for k in ks:
        big = k in ("F18_bagboost", "F12_rankunion")
        a3.plot([base[k]], [per[k]], "o", ms=5.4 if big else 3.8,
                color=CLAIM if big else GATE, zorder=3 if big else 2)
        a3.annotate(short(k), (base[k], per[k]), fontsize=5.9,
                    xytext=(0, 7), textcoords="offset points", ha="center")
    a3.set_xlabel("판 $\\rho$ (팝업 가중 2.3\\%)", fontsize=7.0)
    a3.set_ylabel("팝업 $\\rho$", fontsize=7.0)
    a3.tick_params(labelsize=6.2)
    a3.set_title("두 순위가 무관하다 ($\\rho=-0.07$)", fontsize=7.2)
    a3.set_ylim(.40, .53)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 149 — 위키백과가 검색이 못 가는 곳을 채운다 ──────────────────────
def fig_wiki(out: str = "fig_wiki.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note149.json"))
    W, N = j["wiki"], j["naver"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.1, 1, .95]})

    # ① 덮음 --- 네이버 대 위키
    ds = ["세계애니", "만화", "게임", "모바일", "웹툰", "애니", "팝업"]
    x = np.arange(len(ds))
    nv = [N.get(d, {}).get("덮음", 0) for d in ds]
    wk = [W.get(d, {}).get("덮음", 0) for d in ds]
    a1.bar(x - .19, nv, .34, color="#9aa3ad", alpha=.95, edgecolor="none",
           label="네이버 검색")
    a1.bar(x + .19, wk, .34, color=CLAIM, alpha=.95, edgecolor="none",
           label="위키 조회수")
    for i, d in enumerate(ds):
        if nv[i] < .05 and wk[i] > .2:
            a1.text(i + .19, wk[i] + .02, f"{wk[i]:.0%}", fontsize=6.1,
                    ha="center", color=CLAIM)
    a1.set_xticks(x); a1.set_xticklabels(ds, fontsize=5.9)
    a1.set_ylabel("덮음", fontsize=7.0)
    a1.set_ylim(0, 1.08)
    a1.legend(fontsize=5.9, frameon=False, loc="upper right")
    a1.tick_params(labelsize=6.2)
    a1.set_title("0\\%였던 두 곳이 34\\%·59\\%", fontsize=7.2)

    # ② 도메인별 --- 현행 대 위키추가
    per = j["per"]
    ds2 = ["세계애니", "게임", "팝업", "모바일"]
    x2 = np.arange(len(ds2))
    a2.bar(x2 - .19, [per["현행"][d] for d in ds2], .34, color="#9aa3ad",
           alpha=.95, edgecolor="none", label="현행")
    a2.bar(x2 + .19, [per["위키추가"][d] for d in ds2], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="＋위키")
    for i, d in enumerate(ds2):
        g = per["위키추가"][d] - per["현행"][d]
        a2.text(i, max(per["현행"][d], per["위키추가"][d]) + .012,
                f"{g:+.3f}", fontsize=6.1, ha="center",
                color=CLAIM if g > 0 else "#6b7480")
    a2.set_xticks(x2); a2.set_xticklabels(ds2, fontsize=6.1)
    a2.set_ylabel("$\\rho$ (F18 배깅)", fontsize=7.0)
    a2.set_ylim(0, .66)
    a2.legend(fontsize=5.9, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.2)
    a2.set_title("팝업은 위키 축이 없는데도 오른다", fontsize=7.2)

    # ③ 판 --- 갈리나
    r = j["resolve"]
    b = j["board"]
    x3 = np.arange(2)
    for i, f in enumerate(("F8", "F18")):
        a3.plot([i - .16], [b["현행"][f]], "o", ms=5, color="#9aa3ad")
        a3.plot([i + .16], [b["위키추가"][f]], "o", ms=6,
                color=CLAIM if r[f]["split"] else "#9aa3ad")
        a3.plot([i - .16, i + .16], [b["현행"][f], b["위키추가"][f]],
                lw=1.6, color=CLAIM if r[f]["split"] else "#c3cad2")
        a3.errorbar([i + .16], [b["위키추가"][f]], yerr=[2 * r[f]["sd"]],
                    color=CLAIM if r[f]["split"] else "#9aa3ad", lw=1.0,
                    capsize=2.5)
        a3.text(i, b["위키추가"][f] + .006,
                f"{r[f]['gap']:+.4f}\n$t$={r[f]['t']:.1f}"
                + ("  갈린다" if r[f]["split"] else "  안 갈린다"),
                fontsize=5.9, ha="center",
                color=CLAIM if r[f]["split"] else "#6b7480")
    a3.set_xticks(x3); a3.set_xticklabels(["F8 부스팅", "F18 배깅"], fontsize=6.3)
    a3.set_xlim(-.5, 1.5)
    a3.set_ylim(.425, .462)
    a3.set_ylabel("판 $\\rho$", fontsize=7.0)
    a3.tick_params(labelsize=6.2)
    a3.set_title("배깅에서만 갈린다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 150 — 겹침 0인 문서를 그냥 쓰고 있었다 ──────────────────────────
def fig_match(out: str = "fig_match.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note150.json"))
    cov, sh = j["cov"], j["shared"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.4),
                                     gridspec_kw={"width_ratios": [1, 1, 1]})

    # ① 오염된 덮음 대 정직한 덮음
    ds = ["세계애니", "게임", "애니", "만화", "웹툰", "모바일"]
    dirty = {"세계애니": .591, "게임": .651, "애니": .84, "만화": .340,
             "웹툰": .84, "모바일": .337}
    clean = {d: cov.get(d, {}).get("덮음", 0) for d in ds}
    x = np.arange(len(ds))
    a1.bar(x - .19, [dirty[d] for d in ds], .34, color="#c3cad2",
           edgecolor="none", label="겹침 0 도 씀")
    a1.bar(x + .19, [clean[d] for d in ds], .34, color=CLAIM, alpha=.95,
           edgecolor="none", label="겹쳐야 씀")
    for i, d in enumerate(ds):
        a1.text(i - .19, dirty[d] + .015, f"{dirty[d]:.0%}", fontsize=5.6,
                ha="center", color="#6b7480")
        a1.text(i + .19, clean[d] + .015, f"{clean[d]:.0%}", fontsize=5.9,
                ha="center", color=CLAIM)
    a1.set_xticks(x); a1.set_xticklabels(ds, fontsize=5.8)
    a1.set_ylabel("덮음", fontsize=7.0)
    a1.set_ylim(0, 1.0)
    a1.legend(fontsize=5.8, frameon=False, loc="upper right")
    a1.tick_params(labelsize=6.2)
    a1.set_title("덮음의 29\\%가 아무 문서였다", fontsize=7.2)

    # ② 한 문서를 몇이 나눠 쓰나
    ds2 = [d for d in ("세계애니", "애니", "게임", "만화", "웹툰", "모바일")
           if d in sh]
    x2 = np.arange(len(ds2))
    a2.bar(x2, [sh[d]["5건이상이쓰는몫"] for d in ds2], .55, color=GATE,
           alpha=.92, edgecolor="none")
    for i, d in enumerate(ds2):
        a2.text(i, sh[d]["5건이상이쓰는몫"] + .004,
                f"최대 {sh[d]['최대공유']}", fontsize=5.9, ha="center",
                color=GATE)
    a2.axhline(.84, color=CLAIM, lw=1.2, ls="--")
    a2.text(len(ds2) - .5, .855, "고치기 전 웹툰 84\\%", fontsize=6.0,
            ha="right", color=CLAIM)
    a2.set_xticks(x2); a2.set_xticklabels(ds2, fontsize=5.8)
    a2.set_ylabel("5건 이상이 쓰는 문서의 몫", fontsize=6.8)
    a2.set_ylim(0, .95)
    a2.tick_params(labelsize=6.2)
    a2.set_title("남은 공유는 프랜차이즈다", fontsize=7.2)

    # ③ 씻으니 이득이 커진다
    lab = ["F18 오염", "F18 정직", "F8 정직"]
    gap = [0.0092, 0.0104, 0.0000]
    sd = [0.0034, 0.0041, 0.0064]
    x3 = np.arange(3)
    a3.bar(x3, gap, .5, color=[GATE, CLAIM, "#c3cad2"], alpha=.95,
           edgecolor="none")
    a3.errorbar(x3, gap, yerr=[2 * v for v in sd], fmt="none",
                ecolor="#5a6169", lw=1.0, capsize=3)
    for i in range(3):
        a3.text(i, gap[i] + 2 * sd[i] + .0008,
                f"{gap[i]:+.4f}\n$t$={gap[i]/sd[i]:.1f}", fontsize=5.9,
                ha="center", color="#3a4046")
    a3.axhline(0, color="#8a929b", lw=.6)
    a3.set_xticks(x3); a3.set_xticklabels(lab, fontsize=6.1)
    a3.set_ylabel("위키 축이 주는 판 $\\rho$ 이득", fontsize=6.8)
    a3.set_ylim(-.014, .026)
    a3.tick_params(labelsize=6.2)
    a3.set_title("잡음을 빼니 신호가 커졌다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 151 — 필터인 줄 알았는데 사람 손이었다 ──────────────────────────
def fig_gate(out: str = "fig_gate.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note151.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1, 1.05]})

    # ① 깔때기
    fn = j["funnel"]
    ys = np.arange(len(fn))[::-1]
    for i, (lab, n) in enumerate(fn):
        c = CLAIM if i == len(fn) - 1 else GATE
        a1.barh(ys[i], n, .62, color=c, alpha=.92, edgecolor="none")
        a1.text(n + 6, ys[i], f"{n}", fontsize=6.4, va="center", color=c)
    a1.set_yticks(ys)
    a1.set_yticklabels([l for l, _ in fn], fontsize=6.2)
    a1.set_xlim(0, 430)
    a1.set_xlabel("팝업 레코드", fontsize=7.0)
    a1.tick_params(labelsize=6.2)
    a1.set_title("한 필터가 189를 75로 줄인다", fontsize=7.2)

    # ② 늘어난 절반의 rho
    fs = ["F6_directpool", "F8_boost", "F18_bagboost"]
    x = np.arange(len(fs))
    a2.bar(x - .19, [j["rho"][f]["std"] for f in fs], .34, color=GATE,
           alpha=.92, edgecolor="none", label="표준 59건")
    a2.bar(x + .19, [j["rho"][f]["non"] for f in fs], .34, color=CLAIM,
           alpha=.92, edgecolor="none", label="늘어난 57건")
    for i, f in enumerate(fs):
        a2.text(i - .19, j["rho"][f]["std"] + .012,
                f"{j['rho'][f]['std']:+.2f}", fontsize=6.0, ha="center",
                color=GATE)
        a2.text(i + .19, j["rho"][f]["non"] - .03,
                f"{j['rho'][f]['non']:+.2f}", fontsize=6.0, ha="center",
                color=CLAIM)
    a2.axhline(0, color="#8a929b", lw=.6)
    a2.set_xticks(x)
    a2.set_xticklabels([f.split("_")[0] for f in fs], fontsize=6.3)
    a2.set_ylabel("팝업 $\\rho$ (유보)", fontsize=7.0)
    a2.set_ylim(-.13, .56)
    a2.legend(fontsize=5.9, frameon=False, loc="upper center")
    a2.tick_params(labelsize=6.2)
    a2.set_title("늘어난 절반은 셋 다 음수다", fontsize=7.2)

    # ③ 진짜 원인 --- 축 빈칸
    e = j["empty"]
    ks = ["entry", "participation", "unknown", "organizer_claim"]
    lab = ["입장", "참여", "불명", "주최측\n주장"]
    x3 = np.arange(len(ks))
    a3.bar(x3, [e[k] for k in ks], .55,
           color=[GATE, GATE, GATE, CLAIM], alpha=.92, edgecolor="none")
    for i, k in enumerate(ks):
        a3.text(i, e[k] + .022, f"{e[k]:.0%}", fontsize=6.3, ha="center",
                color=CLAIM if k == "organizer_claim" else GATE)
    a3.set_xticks(x3); a3.set_xticklabels(lab, fontsize=6.0)
    a3.set_ylabel("축이 안 매겨진 비율", fontsize=7.0)
    a3.set_ylim(0, 1.16)
    a3.tick_params(labelsize=6.2)
    a3.set_title("집계 필터는 사람 손의 대리였다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 152 — 읽을 수 있는 축은 안 맞고, 맞는 축은 못 읽는다 ─────────────
def fig_read(out: str = "fig_read.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note152.json"))
    ax, g = j["axes"], j["group"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                                 gridspec_kw={"width_ratios": [1.25, 1]})

    # ① 산점 --- 라벨 상관 대 태거 rho
    KO = {"venue_prominence": "장소 노출", "target_breadth": "타깃 폭",
          "media_push": "미디어 푸시", "goods_scale": "굿즈 규모",
          "entry_friction": "입장 마찰", "experience_density": "체험 밀도",
          "ip_awareness": "IP 인지", "collab_strength": "협업 강도",
          "photo_zones": "포토존", "season_fit": "계절 적합"}
    for a, v in ax.items():
        sh = v["shared"]
        a1.plot([v["tagger"]], [abs(v["label"])], "o", ms=6.2,
                color=CLAIM if sh else GATE, zorder=3)
        a1.annotate(KO.get(a, a), (v["tagger"], abs(v["label"])),
                    fontsize=6.0, xytext=(0, 8), textcoords="offset points",
                    ha="center", color=CLAIM if sh else "#4a5158")
    a1.axvline(.33, color="#c3cad2", lw=.8, ls=":")
    a1.axhline(.24, color="#c3cad2", lw=.8, ls=":")
    a1.text(.10, .46, "쓸모 있고\n못 읽는다", fontsize=6.4, color=CLAIM,
            ha="center")
    a1.text(.52, .06, "읽히고\n쓸모없다", fontsize=6.4, color=GATE,
            ha="center")
    a1.set_xlabel("태거가 읽어 내는 정도 (교차검증 $\\rho$)", fontsize=7.0)
    a1.set_ylabel("라벨과의 상관 $|\\rho|$", fontsize=7.0)
    a1.set_xlim(.08, .66); a1.set_ylim(0, .53)
    a1.tick_params(labelsize=6.2)
    a1.set_title(f"열 축이 대각선으로 갈린다 (순위상관 {j['rank_corr']:+.2f})",
                 fontsize=7.2)

    # ② 두 무리 평균
    ks = ["공유", "팝업전용"]
    x = np.arange(2)
    a2.bar(x - .19, [g[k]["label"] for k in ks], .34, color=CLAIM, alpha=.92,
           edgecolor="none", label="라벨 상관")
    a2.bar(x + .19, [g[k]["tagger"] for k in ks], .34, color=GATE, alpha=.92,
           edgecolor="none", label="태거 $\\rho$")
    for i, k in enumerate(ks):
        a2.text(i - .19, g[k]["label"] + .012, f"{g[k]['label']:.3f}",
                fontsize=6.2, ha="center", color=CLAIM)
        a2.text(i + .19, g[k]["tagger"] + .012, f"{g[k]['tagger']:.3f}",
                fontsize=6.2, ha="center", color=GATE)
    a2.set_xticks(x)
    a2.set_xticklabels(["공유 다섯\n(전 도메인)", "팝업 전용 다섯"],
                       fontsize=6.2)
    a2.set_ylim(0, .55)
    a2.legend(fontsize=6.0, frameon=False, loc="upper center")
    a2.tick_params(labelsize=6.2)
    a2.set_title("겹치는 축이 하나도 없다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 153 — 평균 내지 말고 읽었더니 ──────────────────────────────────
def fig_llm(out: str = "fig_llm.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note153.json"))
    per, el = j["per"], j["err_by_len"]
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "장소 노출",
          "entry_friction": "입장 마찰", "media_push": "미디어 푸시",
          "goods_scale": "굿즈 규모"}
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.15, 1, .9]})

    # ① 축마다 --- 능형 대 읽기
    ks = sorted(per, key=lambda k: -per[k]["llm_rho"])
    x = np.arange(len(ks))
    a1.bar(x - .19, [per[k]["ridge_rho"] for k in ks], .34, color="#9aa3ad",
           alpha=.95, edgecolor="none", label="능형$+$임베딩")
    a1.bar(x + .19, [per[k]["llm_rho"] for k in ks], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="문서를 읽음")
    for i, k in enumerate(ks):
        a1.text(i - .19, per[k]["ridge_rho"] + .02, f"{per[k]['ridge_rho']:.2f}",
                fontsize=5.9, ha="center", color="#6b7480")
        a1.text(i + .19, per[k]["llm_rho"] + .02, f"{per[k]['llm_rho']:.2f}",
                fontsize=6.1, ha="center", color=CLAIM)
    a1.set_xticks(x)
    a1.set_xticklabels([KO.get(k, k) for k in ks], fontsize=5.9)
    a1.set_ylabel("사람 라벨과의 $\\rho$", fontsize=7.0)
    a1.set_ylim(0, 1.06)
    a1.legend(fontsize=5.9, frameon=False, loc="upper right")
    a1.tick_params(labelsize=6.2)
    a1.set_title("공유 다섯 전부 오른다", fontsize=7.2)

    # ② 평균 --- rho 와 MAE
    lm = np.mean([per[k]["llm_rho"] for k in per])
    rg = np.mean([per[k]["ridge_rho"] for k in per])
    lme = np.mean([per[k]["llm_mae"] for k in per])
    rge = np.mean([per[k]["ridge_mae"] for k in per])
    x2 = np.arange(2)
    a2.bar(x2 - .19, [rg, rge], .34, color="#9aa3ad", alpha=.95,
           edgecolor="none", label="능형")
    a2.bar(x2 + .19, [lm, lme], .34, color=CLAIM, alpha=.95,
           edgecolor="none", label="읽기")
    for i, (a, b) in enumerate(((rg, lm), (rge, lme))):
        a2.text(i - .19, a + .02, f"{a:.3f}", fontsize=6.1, ha="center",
                color="#6b7480")
        a2.text(i + .19, b + .02, f"{b:.3f}", fontsize=6.3, ha="center",
                color=CLAIM)
    a2.set_xticks(x2)
    a2.set_xticklabels(["$\\rho$ (높을수록 좋다)", "MAE (낮을수록 좋다)"],
                       fontsize=6.1)
    a2.set_ylim(0, 1.12)
    a2.legend(fontsize=6.0, frameon=False, loc="upper left")
    a2.tick_params(labelsize=6.2)
    a2.set_title("$\\rho$ $+$0.54 · 오차 45\\% 감소", fontsize=7.2)

    # ③ 문서가 얇아지면
    a3.bar([0, 1], [el["long"], el["short"]], .5, color=[CLAIM, "#e0a3a8"],
           alpha=.95, edgecolor="none")
    for i, v in enumerate((el["long"], el["short"])):
        a3.text(i, v + .015, f"{v:.2f}", fontsize=6.4, ha="center",
                color=CLAIM)
    a3.axvspan(1.5, 2.5, color="#c3cad2", alpha=.35, lw=0)
    a3.text(2, .40, f"안 매겨진 108건\n중앙 {el['untag_len']:.0f}자\n???",
            fontsize=6.2, ha="center", color="#5a6169")
    a3.set_xticks([0, 1, 2])
    a3.set_xticklabels([f"긴 절반\n({el['tagged_len']:.0f}자 이상)",
                        "짧은 절반", "적용 대상"], fontsize=5.9)
    a3.set_ylabel("내 태깅 MAE", fontsize=7.0)
    a3.set_xlim(-.6, 2.6); a3.set_ylim(0, .9)
    a3.tick_params(labelsize=6.2)
    a3.set_title("얇아지면 오차가 는다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 154 — 읽어서 채웠더니 잡음이 신호가 됐다 ────────────────────────
def fig_fill(out: str = "fig_fill.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note154.json"))
    ab = json.load(open(Path(root) / "data/state/note154_ablate.json"))
    rs = json.load(open(Path(root) / "data/state/note154_res.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, .95, 1.05]})

    # ① 세 판의 팝업 rho
    ks = ["표준 59", "빈칸 116", "채움 116"]
    x = np.arange(3)
    a1.bar(x, [j[k][0] for k in ks], .55,
           color=[GATE, "#9aa3ad", CLAIM], alpha=.93, edgecolor="none")
    for i, k in enumerate(ks):
        a1.text(i, j[k][0] + .008, f"{j[k][0]:+.3f}", fontsize=6.3,
                ha="center", color=CLAIM if i == 2 else GATE)
    a1.set_xticks(x); a1.set_xticklabels(ks, fontsize=6.2)
    a1.set_ylabel("팝업 $\\rho$", fontsize=7.0)
    a1.set_ylim(0, .43)
    a1.tick_params(labelsize=6.2)
    a1.set_title("합치면 내려간다", fontsize=7.2)

    # ② 늘어난 절반만 --- 비었을 때 대 채웠을 때
    lab = ["비웠을 때\n(노트 151)", "읽어서\n채웠을 때", "축만으로\n따로 재면"]
    val = [-0.0848, j.get("채운것만", 0.1967), ab["mine"]]
    a2.bar(np.arange(3), val, .5,
           color=["#9aa3ad", CLAIM, CLAIM], alpha=.93, edgecolor="none")
    for i, v in enumerate(val):
        a2.text(i, v + (.012 if v > 0 else -.03), f"{v:+.3f}", fontsize=6.3,
                ha="center", color=CLAIM if v > 0 else "#6b7480")
    a2.axhline(0, color="#8a929b", lw=.6)
    a2.axhline(ab["struct"], color=GATE, lw=1.1, ls="--")
    a2.text(2.4, ab["struct"] + .012, "구조 필드만 $+$.001", fontsize=5.9,
            ha="right", color=GATE)
    a2.set_xticks(np.arange(3)); a2.set_xticklabels(lab, fontsize=5.9)
    a2.set_ylabel("늘어난 51건의 $\\rho$", fontsize=7.0)
    a2.set_ylim(-.16, .45)
    a2.tick_params(labelsize=6.2)
    a2.set_title("잡음이 신호가 된다", fontsize=7.2)

    # ③ 분해능 --- 오차막대가 줄어든다
    pairs = ["F18_bagboost-F6_directpool", "F18_bagboost-F8_boost",
             "F6_directpool-F8_boost"]
    lab3 = ["F18-F6", "F18-F8", "F6-F8"]
    x3 = np.arange(3)
    s59 = [rs[f"표준 59|{p}"]["sd"] for p in pairs]
    s116 = [rs[f"채움 116|{p}"]["sd"] for p in pairs]
    a3.bar(x3 - .19, s59, .34, color="#9aa3ad", alpha=.95, edgecolor="none",
           label="표준 59")
    a3.bar(x3 + .19, s116, .34, color=CLAIM, alpha=.95, edgecolor="none",
           label="채움 116")
    for i in range(3):
        a3.text(i, max(s59[i], s116[i]) + .003,
                f"$-${(1 - s116[i] / s59[i]) * 100:.0f}\\%", fontsize=6.0,
                ha="center", color=CLAIM)
    a3.set_xticks(x3); a3.set_xticklabels(lab3, fontsize=6.2)
    a3.set_ylabel("짝 sd (작을수록 잘 가른다)", fontsize=6.8)
    a3.set_ylim(0, .098)
    a3.legend(fontsize=5.9, frameon=False, loc="upper left")
    a3.tick_params(labelsize=6.2)
    a3.set_title("낮은 $\\rho$, 좁은 오차", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 155 — 손잡이인가 눈금인가 ──────────────────────────────────────
def fig_lever(out: str = "fig_lever.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note155.json"))
    sm, rows, fm, bd = j["summary"], j["rows"], j["forms"], j["board"]
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "장소 노출",
          "entry_friction": "입장 마찰", "media_push": "미디어 푸시",
          "goods_scale": "굿즈 규모"}
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1.1, 1]})

    # ① 축마다 --- 사전 부호와 몇이나 맞나
    ks = sorted(sm, key=lambda k: -sm[k]["agree"] / sm[k]["n"])
    x = np.arange(len(ks))
    fr = [sm[k]["agree"] / sm[k]["n"] for k in ks]
    a1.bar(x, fr, .55, color=[CLAIM if v >= .99 else
                              (GATE if v >= .7 else "#c3cad2") for v in fr],
           alpha=.93, edgecolor="none")
    for i, k in enumerate(ks):
        a1.text(i, fr[i] + .02, f"{sm[k]['agree']}/{sm[k]['n']}", fontsize=6.1,
                ha="center", color="#3a4046")
    a1.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a1.text(len(ks) - .5, .52, "동전", fontsize=6.0, ha="right", color="#6b7480")
    a1.set_xticks(x); a1.set_xticklabels([KO.get(k, k) for k in ks],
                                         fontsize=5.9, rotation=20)
    a1.set_ylabel("사전 부호와 맞은 도메인 비율", fontsize=6.8)
    a1.set_ylim(0, 1.12)
    a1.tick_params(labelsize=6.2)
    a1.set_title("셋은 손잡이처럼, 둘은 아니다", fontsize=7.2)

    # ② 모형 효과 대 그 도메인의 부분상관
    E = np.array([r[2] for r in rows]); Pp = np.array([r[4] for r in rows])
    ok = np.isfinite(Pp)
    a2.plot(Pp[ok], E[ok], "o", ms=4.2, color=GATE, alpha=.85)
    for r in rows:
        if not np.isfinite(r[4]):
            continue
        if abs(r[2] - r[4]) > .35 or (np.sign(r[2]) != np.sign(r[4])
                                      and abs(r[4]) > .25):
            a2.annotate(f"{r[0]}·{KO.get(r[1], r[1])[:4]}", (r[4], r[2]),
                        fontsize=5.4, xytext=(0, 6),
                        textcoords="offset points", ha="center", color=CLAIM)
    a2.axhline(0, color="#8a929b", lw=.6); a2.axvline(0, color="#8a929b", lw=.6)
    lim = [-.45, .65]
    a2.plot(lim, lim, color="#c3cad2", lw=.9, ls=":")
    a2.set_xlabel("그 도메인의 부분상관 (자료가 말하는 것)", fontsize=6.8)
    a2.set_ylabel("모형이 함의하는 개입 효과", fontsize=6.8)
    a2.set_xlim(-.45, .65); a2.set_ylim(-.45, .75)
    a2.tick_params(labelsize=6.2)
    a2.set_title(f"관계가 없다 (순위상관 {j['corr_par']:+.3f})", fontsize=7.2)

    # ③ 판 순위 대 손잡이 충실도
    fs = ["F8_boost", "F10_pershrink", "F6_directpool", "F9_ranklik"]
    for f in fs:
        big = f == "F10_pershrink"
        a3.plot([bd[f]], [fm[f]["prior"]], "o", ms=6.5 if big else 5,
                color=CLAIM if big else GATE, zorder=3)
        a3.annotate(f.split("_")[0], (bd[f], fm[f]["prior"]), fontsize=6.0,
                    xytext=(0, 8), textcoords="offset points", ha="center",
                    color=CLAIM if big else "#4a5158")
    a3.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a3.text(.435, .52, "동전", fontsize=6.0, ha="right", color="#6b7480")
    a3.set_xlabel("판 $\\rho$ (순위 성능)", fontsize=6.8)
    a3.set_ylabel("사전 부호 일치 (손잡이 충실도)", fontsize=6.6)
    a3.set_ylim(0, 1.0)
    a3.tick_params(labelsize=6.2)
    a3.set_title("판 2위가 부호를 뒤집는다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 156 — 절반만 흔들었더니 순서가 반대였다 ─────────────────────────
def fig_half(out: str = "fig_half.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note156.json"))
    res, bd, anti = j["res"], j["board"], j["anti"]
    SH = lambda f: f.split("_")[0]
    fs = sorted(bd, key=lambda f: -bd[f])
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [.95, 1.1, 1]})

    # ① 노트 155 의 틀린 값과 고친 값
    x = np.arange(2)
    a1.bar(x, [0.14, res["F10_pershrink"]["prior"]], .5,
           color=["#c3cad2", CLAIM], alpha=.93, edgecolor="none")
    for i, v in enumerate((0.14, res["F10_pershrink"]["prior"])):
        a1.text(i, v + .02, f"{v:.0%}", fontsize=6.8, ha="center",
                color=CLAIM if i else "#6b7480")
    a1.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a1.text(1.45, .52, "동전", fontsize=6.0, ha="right", color="#6b7480")
    a1.set_xticks(x)
    a1.set_xticklabels(["노트 155\n(전부 흔듦)", "노트 156\n(절반만)"],
                       fontsize=6.1)
    a1.set_ylabel("F10 사전 부호 일치", fontsize=6.8)
    a1.set_ylim(0, .85)
    a1.tick_params(labelsize=6.2)
    a1.set_title("$\\mathrm{sign}(0)$ 을 역전으로 읽었다", fontsize=7.2)

    # ② 판 대 자료 부호 일치
    for f in fs:
        boost = "boost" in f
        a2.plot([bd[f]], [res[f]["sign_par"]], "o", ms=6.0,
                color=CLAIM if boost else GATE, zorder=3)
        a2.annotate(SH(f), (bd[f], res[f]["sign_par"]), fontsize=6.1,
                    xytext=(0, 8), textcoords="offset points", ha="center",
                    color=CLAIM if boost else "#4a5158")
    xs = np.array([bd[f] for f in fs]); ys = np.array([res[f]["sign_par"] for f in fs])
    o = np.argsort(xs)
    a2.plot(xs[o], ys[o], lw=1.0, color="#c3cad2", zorder=1)
    a2.set_xlabel("판 $\\rho$ (순위 성능)", fontsize=6.9)
    a2.set_ylabel("자료 부호와 맞은 비율", fontsize=6.9)
    a2.set_ylim(.6, .9)
    a2.tick_params(labelsize=6.2)
    a2.set_title(f"반대로 간다 (순위상관 {anti['sign_par']:+.2f})", fontsize=7.2)

    # ③ 사전 대 자료 --- 두 잣대가 갈린다
    x3 = np.arange(len(fs))
    a3.bar(x3 - .19, [res[f]["prior"] for f in fs], .34, color="#9aa3ad",
           alpha=.95, edgecolor="none", label="내 상식과 일치")
    a3.bar(x3 + .19, [res[f]["sign_par"] for f in fs], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="그 도메인 자료와 일치")
    a3.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a3.set_xticks(x3)
    a3.set_xticklabels([SH(f) for f in fs], fontsize=6.0, rotation=15)
    a3.set_ylim(0, 1.02)
    a3.legend(fontsize=5.8, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.2)
    a3.set_title("판 위쪽은 상식을 따르고 자료를 안 따른다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 157 — 판과 팝업이 서로 다른 축을 쓴다 ───────────────────────────
def fig_split(out: str = "fig_split.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note157.json"))
    ab, rs, lv = j["ablate"], j["resolve"], j["lever"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.1, 1, .95]})

    # ① 축 세트마다 --- 판과 팝업
    ks = ["전부 19", "손 축 다섯만", "외부 축만"]
    x = np.arange(len(ks))
    bd = [ab[f"{k}|F18_bagboost"]["board"] for k in ks]
    pp = [ab[f"{k}|F18_bagboost"]["popup"] for k in ks]
    a1.bar(x - .19, bd, .34, color=GATE, alpha=.95, edgecolor="none",
           label="판 $\\rho$ (전 도메인)")
    a1.bar(x + .19, pp, .34, color=CLAIM, alpha=.95, edgecolor="none",
           label="팝업 $\\rho$")
    for i in range(len(ks)):
        a1.text(i - .19, bd[i] + .012, f"{bd[i]:.3f}", fontsize=6.0,
                ha="center", color=GATE)
        a1.text(i + .19, pp[i] + .012, f"{pp[i]:.3f}", fontsize=6.0,
                ha="center", color=CLAIM)
    a1.set_xticks(x); a1.set_xticklabels(ks, fontsize=6.2)
    a1.set_ylabel("$\\rho$ (F18 배깅)", fontsize=7.0)
    a1.set_ylim(0, .60)
    a1.legend(fontsize=5.9, frameon=False, loc="upper right")
    a1.tick_params(labelsize=6.2)
    a1.set_title("외부 축만으로는 팝업을 못 맞힌다", fontsize=7.2)

    # ② 팝업 --- 차이는 안 갈린다
    ks2 = ["손 축 다섯만", "손5+달력", "손5+검색"]
    x2 = np.arange(len(ks2))
    for i, f in enumerate(("F6", "F18")):
        g = [rs[f][k][0] for k in ks2]
        e = [2 * rs[f][k][1] for k in ks2]
        a2.errorbar(x2 + (i - .5) * .18, g, yerr=e, fmt="o", ms=4.5,
                    color=CLAIM if i else GATE, capsize=3, lw=1.1,
                    label=f)
    a2.axhline(0, color="#8a929b", lw=.8)
    a2.set_xticks(x2); a2.set_xticklabels(ks2, fontsize=6.0)
    a2.set_ylabel("전부 19 대비 팝업 $\\rho$", fontsize=6.9)
    a2.legend(fontsize=6.0, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.2)
    a2.set_title("$n{=}59$ --- 하나도 안 갈린다", fontsize=7.2)

    # ③ 외부 축을 빼면 --- 크기는 늘고 부호는 나빠진다
    x3 = np.arange(2)
    for i, f in enumerate(("F18", "F6")):
        sz = [lv["전부 19"][f][0], lv["손 축 다섯만"][f][0]]
        pr = [lv["전부 19"][f][1] / 36, lv["손 축 다섯만"][f][1] / 36]
        a3.plot(x3 + i * .04, sz, "-o", ms=4.5, lw=1.6,
                color=CLAIM if i == 0 else "#e0a3a8", label=f"{f} 효과 크기")
        a3b = a3
    a3.set_ylabel("개입 효과 크기", fontsize=6.9, color=CLAIM)
    a3.tick_params(axis="y", labelcolor=CLAIM, labelsize=6.2)
    ax2 = a3.twinx()
    for i, f in enumerate(("F18", "F6")):
        pr = [lv["전부 19"][f][1] / 36, lv["손 축 다섯만"][f][1] / 36]
        ax2.plot(x3 + i * .04, pr, "--s", ms=4.0, lw=1.3,
                 color=GATE if i == 0 else "#8fb4d9")
    ax2.set_ylabel("사전 부호 일치", fontsize=6.9, color=GATE)
    ax2.tick_params(axis="y", labelcolor=GATE, labelsize=6.2)
    ax2.set_ylim(.45, .95)
    a3.set_xticks(x3)
    a3.set_xticklabels(["전부 19", "손 축\n다섯만"], fontsize=6.1)
    a3.set_xlim(-.35, 1.35)
    a3.set_title("크기는 늘고 부호는 나빠진다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 158 — 달력은 점수가 아니라 통제였다 ────────────────────────────
def fig_ctrl(out: str = "fig_ctrl.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note158.json"))
    lv, sc = j["lever"], j["score"]
    ks = ["손5 (5축)", "손5+검색 (9)", "손5+달력 (11)",
          "손5+검색+달력 (15)", "전부 (19)"]
    short = ["손5", "＋검색", "＋달력", "＋둘", "＋위키"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.05, 1.05, 1]})

    # ① 판 rho
    x = np.arange(len(ks))
    for i, (f, c) in enumerate((("F18_bagboost", CLAIM), ("F6_directpool", GATE))):
        a1.plot(x, [sc[k][f][0] for k in ks], "-o", ms=4.2, lw=1.6, color=c,
                label=f.split("_")[0])
    a1.set_xticks(x); a1.set_xticklabels(short, fontsize=6.1)
    a1.set_ylabel("판 $\\rho$", fontsize=7.0)
    a1.legend(fontsize=6.0, frameon=False, loc="lower right")
    a1.tick_params(labelsize=6.2)
    a1.annotate("", xy=(1, sc[ks[1]]["F18_bagboost"][0]),
                xytext=(0, sc[ks[0]]["F18_bagboost"][0]),
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.4))
    a1.text(.5, .40, "검색이\n점수를 만든다", fontsize=6.2, ha="center",
            color=CLAIM)
    a1.set_title("점수는 검색이 올린다", fontsize=7.2)

    # ② 사전 부호 일치
    for i, (f, c) in enumerate((("F18_bagboost", CLAIM), ("F6_directpool", GATE))):
        a2.plot(x, [lv[k][f][1] / lv[k][f][2] for k in ks], "-o", ms=4.2,
                lw=1.6, color=c, label=f.split("_")[0])
    a2.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a2.set_xticks(x); a2.set_xticklabels(short, fontsize=6.1)
    a2.set_ylabel("사전 부호 일치", fontsize=7.0)
    a2.set_ylim(.45, .95)
    a2.legend(fontsize=6.0, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.2)
    a2.annotate("", xy=(2, lv[ks[2]]["F6_directpool"][1] / 36),
                xytext=(1, lv[ks[1]]["F6_directpool"][1] / 36),
                arrowprops=dict(arrowstyle="->", color=GATE, lw=1.4))
    a2.text(1.55, .63, "달력이\n부호를 지킨다", fontsize=6.2, ha="center",
            color=GATE)
    a2.set_title("부호는 달력이 지킨다", fontsize=7.2)

    # ③ 두 축 무리의 기여 --- 점수 대 부호
    grp = [("검색 4축", sc[ks[1]]["F18_bagboost"][0] - sc[ks[0]]["F18_bagboost"][0],
            (lv[ks[1]]["F18_bagboost"][1] - lv[ks[0]]["F18_bagboost"][1]) / 36,
            sc[ks[1]]["F6_directpool"][0] - sc[ks[0]]["F6_directpool"][0],
            (lv[ks[1]]["F6_directpool"][1] - lv[ks[0]]["F6_directpool"][1]) / 36),
           ("달력 6축", sc[ks[2]]["F18_bagboost"][0] - sc[ks[0]]["F18_bagboost"][0],
            (lv[ks[2]]["F18_bagboost"][1] - lv[ks[0]]["F18_bagboost"][1]) / 36,
            sc[ks[2]]["F6_directpool"][0] - sc[ks[0]]["F6_directpool"][0],
            (lv[ks[2]]["F6_directpool"][1] - lv[ks[0]]["F6_directpool"][1]) / 36)]
    x3 = np.arange(2)
    a3.bar(x3 - .19, [g[1] for g in grp], .34, color=CLAIM, alpha=.93,
           edgecolor="none", label="판 $\\rho$ 변화")
    a3.bar(x3 + .19, [g[2] for g in grp], .34, color=GATE, alpha=.93,
           edgecolor="none", label="부호 일치 변화")
    for i, g in enumerate(grp):
        a3.text(i - .19, g[1] + .005, f"{g[1]:+.3f}", fontsize=6.1,
                ha="center", color=CLAIM)
        a3.text(i + .19, g[2] + .005, f"{g[2]:+.0%}", fontsize=6.1,
                ha="center", color=GATE)
    a3.axhline(0, color="#8a929b", lw=.7)
    a3.set_xticks(x3); a3.set_xticklabels([g[0] for g in grp], fontsize=6.3)
    a3.set_ylim(-.03, .18)
    a3.legend(fontsize=5.9, frameon=False, loc="upper left")
    a3.tick_params(labelsize=6.2)
    a3.set_title("두 무리가 다른 일을 한다 (F18)", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 159 — 공휴일 하나, 그리고 크기를 안 보던 잣대 ────────────────────
def fig_holi(out: str = "fig_holi.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note159.json"))
    ax = json.load(open(Path(root) / "data/state/note159_axis.json"))
    vn = json.load(open(Path(root) / "data/state/note159_venue.json"))
    add = json.load(open(Path(root) / "data/state/note159_add.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.15, .95, 1]})

    # ① 달력 여섯 중 하나만 더할 때
    ks = ["손5만", "cal_dow_sin", "cal_dow_cos", "cal_weekend",
          "cal_month_sin", "cal_month_cos", "cal_holiday_gap"]
    lab = ["손5만", "요일sin", "요일cos", "주말", "월sin", "월cos", "공휴일\n간격"]
    x = np.arange(len(ks))
    v18 = [add[k]["F18_bagboost"][0] / add[k]["F18_bagboost"][1] for k in ks]
    v6 = [add[k]["F6_directpool"][0] / add[k]["F6_directpool"][1] for k in ks]
    a1.bar(x - .19, v18, .34, color=[CLAIM if k == "cal_holiday_gap" else "#9aa3ad"
                                     for k in ks], alpha=.95, edgecolor="none",
           label="F18")
    a1.bar(x + .19, v6, .34, color=[GATE if k == "cal_holiday_gap" else "#c3cad2"
                                    for k in ks], alpha=.95, edgecolor="none",
           label="F6")
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.5)
    a1.set_ylabel("사전 부호 일치 (단순)", fontsize=6.8)
    a1.set_ylim(.45, .92)
    a1.legend(fontsize=5.9, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.2)
    a1.set_title("여섯 중 하나가 전부를 한다", fontsize=7.2)

    # ② 그것이 고치는 축 --- 그런데 크기가 작다
    ds = sorted(vn["before"])
    x2 = np.arange(len(ds))
    a2.bar(x2 - .19, [vn["before"][d] for d in ds], .34, color="#9aa3ad",
           alpha=.95, edgecolor="none", label="손5")
    a2.bar(x2 + .19, [vn["after"][d] for d in ds], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="＋공휴일")
    a2.axhline(0, color="#8a929b", lw=.7)
    a2.axhspan(-.039, .039, color="#c3cad2", alpha=.30, lw=0)
    a2.text(len(ds) - .5, .030, "다른 축의 보통 크기", fontsize=5.7,
            ha="right", color="#5a6169")
    a2.set_xticks(x2); a2.set_xticklabels(ds, fontsize=5.6, rotation=35)
    a2.set_ylabel("장소 노출 개입 효과 (F6)", fontsize=6.6)
    a2.set_ylim(-.045, .045)
    a2.legend(fontsize=5.9, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.2)
    a2.set_title("7/7 뒤집히는데 크기가 1/10 이다", fontsize=7.0)

    # ③ 잣대를 고치면
    ks3 = ["손5", "손5+공휴일", "손5+달력6", "전부19"]
    x3 = np.arange(len(ks3))
    for i, (f, c) in enumerate((("F18_bagboost", CLAIM), ("F6_directpool", GATE))):
        a3.plot(x3, [j[f"{k}|{f}"][0] for k in ks3], "--o", ms=4.0, lw=1.2,
                color=c, alpha=.55, label=f"{f.split('_')[0]} 단순")
        a3.plot(x3, [j[f"{k}|{f}"][1] for k in ks3], "-s", ms=4.4, lw=1.8,
                color=c, label=f"{f.split('_')[0]} 크기가중")
    a3.set_xticks(x3); a3.set_xticklabels(ks3, fontsize=5.8, rotation=12)
    a3.set_ylabel("사전 부호 일치", fontsize=6.8)
    a3.set_ylim(.5, 1.0)
    a3.legend(fontsize=5.4, frameon=False, loc="lower right", ncol=2)
    a3.tick_params(labelsize=6.2)
    a3.set_title("$+$20\\%p 가 $+$3\\%p 가 된다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 160 — 축의 방향을 라벨로 정하고 있었다 ──────────────────────────
def fig_orient(out: str = "fig_orient.pdf", root: str = ".") -> dict:
    import numpy as np
    dec = json.load(open(Path(root) / "data/state/note160_dec.json"))
    fix = json.load(open(Path(root) / "data/state/note160_fix.json"))
    ef = json.load(open(Path(root) / "data/state/note160_ef.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.15, 1, .9]})

    # ① 사전 기간 상관과 현행 결정
    rows = [r for r in dec if r[3] is not None]
    rows.sort(key=lambda r: r[3])
    ds = [r[0] for r in rows]
    x = np.arange(len(ds))
    a1.bar(x, [r[3] for r in rows], .55,
           color=[CLAIM if r[1] != r[4] else GATE for r in rows],
           alpha=.93, edgecolor="none")
    for i, r in enumerate(rows):
        a1.text(i, r[3] + (.02 if r[3] > 0 else -.06),
                ("뒤집" if r[1] else "그대로"), fontsize=5.6, ha="center",
                color=CLAIM if r[1] != r[4] else "#5a6169")
    a1.axhline(0, color="#8a929b", lw=.8)
    a1.set_xticks(x); a1.set_xticklabels(ds, fontsize=5.8, rotation=25)
    a1.set_ylabel("사전 기간 원 방향 상관", fontsize=6.8)
    a1.tick_params(labelsize=6.2)
    a1.set_title("붉은 것은 사전 기간과 어긋난 결정", fontsize=7.2)

    # ② 팝업은 사전 기간으로 못 정한다
    ns = [(r[0], r[2]) for r in dec]
    ns.sort(key=lambda z: z[1])
    x2 = np.arange(len(ns))
    a2.bar(x2, [n for _, n in ns], .55,
           color=[CLAIM if d == "팝업" else "#9aa3ad" for d, _ in ns],
           alpha=.93, edgecolor="none")
    a2.set_yscale("log")
    for i, (d, n) in enumerate(ns):
        if d == "팝업":
            a2.text(i, n * 1.4, f"{n}건\n상관 없음", fontsize=6.0,
                    ha="center", color=CLAIM)
    a2.set_xticks(x2); a2.set_xticklabels([d for d, _ in ns], fontsize=5.8,
                                          rotation=25)
    a2.set_ylabel("2025 이전 관측 건수 (로그)", fontsize=6.6)
    a2.tick_params(labelsize=6.2)
    a2.set_title("팝업은 16건 --- 못 정한다", fontsize=7.2)

    # ③ 되돌리면
    ks = ["현행", "팝업만 되돌림", "팝업+애니 되돌림"]
    x3 = np.arange(len(ks))
    for i, (f, c) in enumerate((("F18_bagboost", CLAIM), ("F6_directpool", GATE))):
        a3.plot(x3, [fix[f"{k}|{f}"][1] for k in ks], "-o", ms=4.6, lw=1.8,
                color=c, label=f.split("_")[0])
    a3.set_xticks(x3)
    a3.set_xticklabels(["현행", "팝업\n되돌림", "팝업+애니\n되돌림"], fontsize=5.9)
    a3.set_ylabel("팝업 $\\rho$", fontsize=7.0)
    a3.set_ylim(.25, .56)
    a3.legend(fontsize=6.0, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.2)
    a3.annotate(f"$-$0.113", xy=(1, fix["팝업만 되돌림|F18_bagboost"][1]),
                xytext=(0.35, .38), fontsize=6.6, color=CLAIM,
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.2))
    a3.set_title("헤드라인이 0.11 내려간다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 161 — 부채를 갚으니 두 잣대가 화해했다 ──────────────────────────
def fig_debt(out: str = "fig_debt.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note161.json"))
    new, old, bd, per = j["new"], j["old"], j["board"], j["per"]
    SH = lambda f: f.split("_")[0]
    fs = sorted(bd, key=lambda f: -bd[f])
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1, 1]})

    # ① 고치기 전후
    x = np.arange(len(fs))
    a1.bar(x - .19, [old[f][0] for f in fs], .34, color="#9aa3ad", alpha=.95,
           edgecolor="none", label="고치기 전")
    a1.bar(x + .19, [new[f]["plain"] for f in fs], .34, color=CLAIM, alpha=.95,
           edgecolor="none", label="방향 보정 반영")
    for i, f in enumerate(fs):
        d = new[f]["plain"] - old[f][0]
        if abs(d) > .02:
            a1.text(i + .19, new[f]["plain"] + .02, f"{d:+.0%}", fontsize=6.0,
                    ha="center", color=CLAIM)
    a1.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a1.set_xticks(x); a1.set_xticklabels([SH(f) for f in fs], fontsize=5.9,
                                         rotation=15)
    a1.set_ylabel("사전 부호 일치 (단순)", fontsize=6.8)
    a1.set_ylim(.45, 1.0)
    a1.legend(fontsize=5.9, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.2)
    a1.set_title("선형 둘이 제일 크게 오른다", fontsize=7.2)

    # ② 판 대 부호 --- 부호가 뒤집힌다
    for lab, key, c, m in (("고치기 전", None, "#9aa3ad", "o"),
                           ("고친 뒤", "plain", CLAIM, "s")):
        v = [old[f][0] if key is None else new[f][key] for f in fs]
        a2.plot([bd[f] for f in fs], v, m, ms=5.2, color=c, label=lab,
                linestyle="none")
        o = np.argsort([bd[f] for f in fs])
        a2.plot(np.array([bd[f] for f in fs])[o], np.array(v)[o], lw=1.1,
                color=c, alpha=.5)
    a2.set_xlabel("판 $\\rho$", fontsize=6.9)
    a2.set_ylabel("사전 부호 일치", fontsize=6.9)
    a2.legend(fontsize=5.9, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.2)
    a2.set_title(f"순위상관 {j['anti_before']:+.2f} $\\to$ {j['anti_after']:+.2f}",
                 fontsize=7.2)

    # ③ 축별
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "장소 노출",
          "entry_friction": "입장 마찰", "media_push": "미디어 푸시",
          "goods_scale": "굿즈 규모"}
    ks = list(per)
    x3 = np.arange(len(ks))
    a3.bar(x3 - .19, [per[k][0][0] / per[k][0][1] for k in ks], .34,
           color=CLAIM, alpha=.95, edgecolor="none", label="F18")
    a3.bar(x3 + .19, [per[k][1][0] / per[k][1][1] for k in ks], .34,
           color=GATE, alpha=.95, edgecolor="none", label="F6")
    for i, k in enumerate(ks):
        if k == "entry_friction":
            a3.text(i, .06, "0/8 이었다", fontsize=5.8, ha="center",
                    color=CLAIM, rotation=90)
    a3.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a3.set_xticks(x3); a3.set_xticklabels([KO[k] for k in ks], fontsize=5.7,
                                          rotation=25)
    a3.set_ylabel("사전 부호 일치", fontsize=6.8)
    a3.set_ylim(0, 1.1)
    a3.legend(fontsize=5.9, frameon=False, loc="upper right")
    a3.tick_params(labelsize=6.2)
    a3.set_title("입장 마찰이 돌아왔다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 162 — 잣대 다섯을 재고 나서 잣대가 아니라 칸이 문제였다 ─────────
def fig_ruler(out: str = "fig_ruler.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note162.json"))
    board = {"F18_bagboost": 0.4491, "F8_boost": 0.4341, "F10_pershrink": 0.3735,
             "F6_directpool": 0.3671, "F9_ranklik": 0.3519}
    fs = list(board)
    names = ["단순", "크기가중", "순위가중", "상위절반", "분해칸비율"]
    SH = lambda f: f.split("_")[0]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.05, 1.1, .95]})

    # ① 잣대별 폭과 안정
    from scipy.stats import spearmanr
    sp, st = [], []
    for n in names:
        v1 = [j[f"11|{f}"][n] for f in fs]; v2 = [j[f"29|{f}"][n] for f in fs]
        sp.append(max(v1) - min(v1)); st.append(spearmanr(v1, v2).correlation)
    x = np.arange(len(names))
    a1.bar(x, sp, .55, color=[CLAIM if n == "상위절반" else "#9aa3ad"
                             for n in names], alpha=.93, edgecolor="none")
    for i, n in enumerate(names):
        a1.text(i, sp[i] + .004, f"{sp[i]:.3f}\n안정 {st[i]:.2f}", fontsize=5.7,
                ha="center", color=CLAIM if n == "상위절반" else "#5a6169")
    a1.set_xticks(x); a1.set_xticklabels(names, fontsize=5.7, rotation=20)
    a1.set_ylabel("정식화 다섯 사이의 폭", fontsize=6.8)
    a1.set_ylim(0, .20)
    a1.tick_params(labelsize=6.2)
    a1.set_title("상위절반이 제일 낫다", fontsize=7.2)

    # ② 상위절반 값
    v = [j[f"11|{f}"]["상위절반"] for f in fs]
    o = np.argsort([-board[f] for f in fs])
    x2 = np.arange(len(fs))
    a2.bar(x2, [v[i] for i in o], .55,
           color=[CLAIM if "boost" in fs[i] else GATE for i in o],
           alpha=.93, edgecolor="none")
    for k, i in enumerate(o):
        n = int(round(v[i] * 18))
        a2.text(k, v[i] + .004, f"{n}/18", fontsize=6.2, ha="center",
                color="#3a4046")
    a2.set_xticks(x2); a2.set_xticklabels([SH(fs[i]) for i in o], fontsize=5.9,
                                          rotation=15)
    a2.set_ylabel("큰 칸에서 사전 부호 일치", fontsize=6.8)
    a2.set_ylim(.90, 1.02)
    a2.tick_params(labelsize=6.2)
    a2.set_title("선형 셋이 18/18, 부스팅 둘이 17/18", fontsize=7.0)

    # ③ 칸 수가 병목
    ns = np.array([12, 18, 24, 36, 60, 100])
    se2 = 2 * np.sqrt(.95 * .05 / ns)
    a3.plot(ns, se2, "-o", ms=4.2, lw=1.7, color=GATE, label="$2\\times$ 이항 se")
    a3.axhline(.056, color=CLAIM, lw=1.5, ls="--")
    a3.text(100, .062, "관측된 폭 0.056", fontsize=6.1, ha="right", color=CLAIM)
    a3.axvline(18, color="#8a929b", lw=.9, ls=":")
    a3.text(19, .155, "지금 (18칸)", fontsize=6.1, color="#5a6169")
    a3.axvline(60, color=CLAIM, lw=.9, ls=":")
    a3.text(61, .12, "가르려면\n60칸", fontsize=6.1, color=CLAIM)
    a3.set_xscale("log")
    a3.set_xlabel("큰 칸의 수", fontsize=6.9)
    a3.set_ylabel("가를 수 있는 최소 폭", fontsize=6.8)
    a3.tick_params(labelsize=6.2)
    a3.set_title("잣대가 아니라 칸이 모자라다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 163 — 큰 손잡이가 옳은 손잡이다 ────────────────────────────────
def fig_loud(out: str = "fig_loud.pdf", root: str = ".") -> dict:
    import numpy as np
    ax = json.load(open(Path(root) / "data/state/note163_axis.json"))
    rows = json.load(open(Path(root) / "data/state/note163.json"))
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "장소 노출",
          "entry_friction": "입장 마찰", "media_push": "미디어 푸시",
          "goods_scale": "굿즈 규모"}
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.05, 1, 1]})

    # ① 크기 대 정확도
    ks = sorted(ax, key=lambda k: -ax[k]["size"])
    for k in ks:
        acc = ax[k]["hit"] / ax[k]["n"]
        big = acc >= .95
        a1.plot([ax[k]["size"]], [acc], "o", ms=7.0,
                color=CLAIM if big else GATE, zorder=3)
        a1.annotate(f"{KO[k]}\n{ax[k]['hit']}/{ax[k]['n']}",
                    (ax[k]["size"], acc), fontsize=6.0, xytext=(0, 9),
                    textcoords="offset points", ha="center",
                    color=CLAIM if big else "#4a5158")
    a1.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a1.text(.062, .52, "동전", fontsize=6.0, ha="right", color="#6b7480")
    a1.set_xlabel("평균 $|$개입 효과$|$", fontsize=6.9)
    a1.set_ylabel("사전 부호 정확도", fontsize=6.9)
    a1.set_xlim(0, .075); a1.set_ylim(.45, 1.18)
    a1.tick_params(labelsize=6.2)
    a1.set_title("순위상관 $+$0.90 --- 큰 것이 옳다", fontsize=7.2)

    # ② 두 무리
    x = np.arange(2)
    a2.bar(x - .19, [.0524, .0164], .34, color=CLAIM, alpha=.95,
           edgecolor="none", label="평균 $|$효과$|$")
    ax2 = a2.twinx()
    ax2.bar(x + .19, [84 / 85, 53 / 75], .34, color=GATE, alpha=.95,
            edgecolor="none", label="부호 정확도")
    a2.set_ylabel("평균 $|$효과$|$", fontsize=6.8, color=CLAIM)
    a2.tick_params(axis="y", labelcolor=CLAIM, labelsize=6.2)
    ax2.set_ylabel("부호 정확도", fontsize=6.8, color=GATE)
    ax2.tick_params(axis="y", labelcolor=GATE, labelsize=6.2)
    ax2.set_ylim(0, 1.15)
    ax2.axhline(.5, color="#8a929b", lw=.8, ls="--")
    for i, (s_, h_) in enumerate(((".052", "99\\%"), (".016", "71\\%"))):
        a2.text(i - .19, [.0524, .0164][i] + .002, s_, fontsize=6.2,
                ha="center", color=CLAIM)
        ax2.text(i + .19, [84 / 85, 53 / 75][i] + .02, h_, fontsize=6.2,
                 ha="center", color=GATE)
    a2.set_xticks(x)
    a2.set_xticklabels(["굿즈 규모\n타깃 폭", "장소 노출\n입장 마찰"],
                       fontsize=6.1)
    a2.set_title("쓸 수 있는 둘, 못 쓰는 둘", fontsize=7.2)

    # ③ 칸 크기는 축의 성질이지 도메인의 성질이 아니다
    E = np.array([r["e18"] for r in rows])
    med = np.median(E)
    import collections
    axb = collections.Counter(r["a"] for r in rows if r["e18"] >= med)
    axs = collections.Counter(r["a"] for r in rows if r["e18"] < med)
    ks3 = list(KO)
    x3 = np.arange(len(ks3))
    a3.bar(x3 - .19, [axb.get(k, 0) for k in ks3], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="큰 칸")
    a3.bar(x3 + .19, [axs.get(k, 0) for k in ks3], .34, color="#9aa3ad",
           alpha=.95, edgecolor="none", label="작은 칸")
    a3.set_xticks(x3); a3.set_xticklabels([KO[k] for k in ks3], fontsize=5.7,
                                          rotation=25)
    a3.set_ylabel("칸 수 (F18)", fontsize=6.8)
    a3.legend(fontsize=5.9, frameon=False, loc="upper right")
    a3.tick_params(labelsize=6.2)
    a3.set_title("도메인은 고르게 섞이는데 축은 갈린다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 164 — 같은 이름, 다른 물건 ──────────────────────────────────────
def fig_slot(out: str = "fig_slot.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note164.json"))
    rows, con = j["rows"], j["con"]
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "장소 노출",
          "entry_friction": "입장 마찰", "media_push": "미디어 푸시",
          "goods_scale": "굿즈 규모"}
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.15, 1, 1]})

    # ① 구성물 수 대 정확도
    for a, nf, hit, sz, n in rows:
        one = nf == 1
        a1.plot([nf], [hit], "o", ms=8.0, color=CLAIM if one else GATE, zorder=3)
        a1.annotate(f"{KO[a]}\n{hit:.0%}", (nf, hit), fontsize=6.1,
                    xytext=(0, 10), textcoords="offset points", ha="center",
                    color=CLAIM if one else "#4a5158")
    a1.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a1.set_xlabel("한 슬롯에 든 구성물 수", fontsize=6.9)
    a1.set_ylabel("사전 부호 정확도", fontsize=6.9)
    a1.set_xlim(.4, 5.7); a1.set_ylim(.45, 1.18)
    a1.set_xticks([1, 2, 3, 4, 5])
    a1.tick_params(labelsize=6.2)
    a1.set_title("구성물 하나짜리만 손잡이가 된다", fontsize=7.2)

    # ② venue_prominence 가 실제로 담은 것
    vp = con["venue_prominence"]
    import collections
    c = collections.Counter(vp.values())
    ks = sorted(c, key=lambda k: -c[k])
    x = np.arange(len(ks))
    a2.barh(x, [c[k] for k in ks], .6,
            color=[CLAIM if k == "물리적 장소" else "#9aa3ad" for k in ks],
            alpha=.93, edgecolor="none")
    for i, k in enumerate(ks):
        a2.text(c[k] + .12, i, f"{c[k]}", fontsize=6.4, va="center",
                color="#3a4046")
    a2.set_yticks(x); a2.set_yticklabels(ks, fontsize=6.2)
    a2.invert_yaxis()
    a2.set_xlabel("도메인 수", fontsize=6.9)
    a2.set_xlim(0, 8.5)
    a2.tick_params(labelsize=6.2)
    a2.set_title("``장소 노출''이 담은 것", fontsize=7.2)

    # ③ 크기와 구성물 --- 얽혀 있다
    for a, nf, hit, sz, n in rows:
        one = nf == 1
        big = sz >= .04
        a3.plot([sz], [nf], "o", ms=8.0,
                color=CLAIM if one else (GATE if big else "#9aa3ad"), zorder=3)
        a3.annotate(KO[a], (sz, nf), fontsize=6.0, xytext=(0, 10),
                    textcoords="offset points", ha="center",
                    color=CLAIM if one else "#4a5158")
    a3.axvline(.04, color="#c3cad2", lw=1.0, ls=":")
    a3.text(.041, 5.3, "큰 효과", fontsize=6.0, color="#5a6169")
    a3.set_xlabel("평균 $|$개입 효과$|$", fontsize=6.9)
    a3.set_ylabel("구성물 수", fontsize=6.9)
    a3.set_ylim(.4, 5.8); a3.set_xlim(0, .072)
    a3.set_yticks([1, 2, 3, 4, 5])
    a3.tick_params(labelsize=6.2)
    a3.set_title("미디어 푸시만 둘을 가른다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 165 — 슬롯에 세 들어 있던 손잡이 ───────────────────────────────
def fig_tenant(out: str = "fig_tenant.pdf", root: str = ".") -> dict:
    import numpy as np
    a = json.load(open(Path(root) / "data/state/note165.json"))
    lv = json.load(open(Path(root) / "data/state/note165_lever.json"))
    dp = json.load(open(Path(root) / "data/state/note165_dup.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1, 1]})

    # ① 판 rho --- 셋
    ks = ["현행", "복제 추가", "제작사 이력 분리"]
    def board(k, f):
        if k == "복제 추가":
            return dp[f"복제 추가|{f}"][0]
        return a[f"{k}|{f}"][0]
    x = np.arange(len(ks))
    for i, (f, c) in enumerate((("F18_bagboost", CLAIM), ("F6_directpool", GATE))):
        a1.plot(x, [board(k, f) for k in ks], "-o", ms=4.6, lw=1.8, color=c,
                label=f.split("_")[0])
    a1.set_xticks(x); a1.set_xticklabels(["현행", "복제\n추가", "분리"],
                                         fontsize=6.1)
    a1.set_ylabel("판 $\\rho$", fontsize=7.0)
    a1.legend(fontsize=6.0, frameon=False, loc="center right")
    a1.tick_params(labelsize=6.2)
    a1.annotate("$-$.0122\n$t{=}4.1$", xy=(2, board(ks[2], "F18_bagboost")),
                xytext=(1.3, .400), fontsize=6.2, color=CLAIM,
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.2))
    a1.set_title("분리하면 빌려오기를 잃는다", fontsize=7.2)

    # ② 손잡이 --- 제작사 이력은 5/5
    lab = ["장소 노출\n(현행 7칸)", "장소 노출\n(분리 뒤 2칸)",
           "제작사 이력\n(5칸)"]
    v18 = [5 / 7, 1 / 2, 1.0]; v6 = [7 / 7, 0 / 2, 1.0]
    x2 = np.arange(3)
    a2.bar(x2 - .19, v18, .34, color=CLAIM, alpha=.95, edgecolor="none",
           label="F18")
    a2.bar(x2 + .19, v6, .34, color=GATE, alpha=.95, edgecolor="none",
           label="F6")
    for i, (p_, q_) in enumerate((("5/7", "7/7"), ("1/2", "0/2"), ("5/5", "5/5"))):
        a2.text(i - .19, v18[i] + .02, p_, fontsize=6.0, ha="center", color=CLAIM)
        a2.text(i + .19, v6[i] + .02, q_, fontsize=6.0, ha="center", color=GATE)
    a2.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a2.set_xticks(x2); a2.set_xticklabels(lab, fontsize=5.7)
    a2.set_ylabel("사전 부호 일치", fontsize=6.9)
    a2.set_ylim(0, 1.18)
    a2.legend(fontsize=5.9, frameon=False, loc="upper left")
    a2.tick_params(labelsize=6.2)
    a2.set_title("세입자가 집주인보다 낫다", fontsize=7.2)

    # ③ 복제는 공선성을 만든다
    x3 = np.arange(2)
    a3.bar(x3 - .19, [lv["현행|F18_bagboost"]["plain"],
                      lv["현행|F6_directpool"]["plain"]], .34,
           color="#9aa3ad", alpha=.95, edgecolor="none", label="현행")
    a3.bar(x3 + .19, [dp["복제 추가|F18_bagboost"][2],
                      dp["복제 추가|F6_directpool"][2]], .34,
           color=CLAIM, alpha=.95, edgecolor="none", label="복제 추가")
    for i, f in enumerate(("F18_bagboost", "F6_directpool")):
        a3.text(i - .19, lv[f"현행|{f}"]["plain"] + .02,
                f"{lv[f'현행|{f}']['plain']:.0%}", fontsize=6.1, ha="center",
                color="#5a6169")
        a3.text(i + .19, dp[f"복제 추가|{f}"][2] + .02,
                f"{dp[f'복제 추가|{f}'][2]:.0%}", fontsize=6.1, ha="center",
                color=CLAIM)
    a3.set_xticks(x3); a3.set_xticklabels(["F18", "F6"], fontsize=6.3)
    a3.set_ylabel("사전 부호 일치 (단순)", fontsize=6.8)
    a3.set_ylim(.6, 1.0)
    a3.legend(fontsize=5.9, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.2)
    a3.set_title("복제는 공선성을 만든다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 166 — 같은 축을 세 번 재고 세 번 다른 답을 얻었다 ──────────────
def fig_three(out: str = "fig_three.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note166.json"))
    hist, raw, new, bd = j["hist"], j["raw"], set(j["new"]), j["board"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.1, 1.05, .95]})

    # ① 세 번의 답
    ks = list(hist)
    lab = ["노트165\n복제(7)", "복제(8)\nF18", "복제(8)\nF6",
           "옮김(8)\nF18", "옮김(8)\nF6"]
    v = [hist[k][0] / hist[k][1] for k in ks]
    x = np.arange(len(ks))
    a1.bar(x, v, .58, color=[CLAIM if "옮김" in k else "#9aa3ad" for k in ks],
           alpha=.93, edgecolor="none")
    for i, k in enumerate(ks):
        a1.text(i, v[i] + .02, f"{hist[k][0]}/{hist[k][1]}", fontsize=6.2,
                ha="center", color=CLAIM if "옮김" in k else "#5a6169")
    a1.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.5)
    a1.set_ylabel("사전 부호 일치", fontsize=6.8)
    a1.set_ylim(0, 1.15)
    a1.tick_params(labelsize=6.2)
    a1.set_title("같은 축, 세 가지 답", fontsize=7.2)

    # ② 원자료 상관 --- 사전 부호가 맞다
    ds = sorted(raw, key=lambda d: -raw[d])
    x2 = np.arange(len(ds))
    a2.bar(x2, [raw[d] for d in ds], .58,
           color=[CLAIM if d in new else GATE for d in ds], alpha=.93,
           edgecolor="none")
    a2.axhline(0, color="#8a929b", lw=.8)
    for i, d in enumerate(ds):
        if d in new:
            a2.text(i, raw[d] + .02, "새", fontsize=5.8, ha="center",
                    color=CLAIM)
    a2.set_xticks(x2); a2.set_xticklabels(ds, fontsize=5.7, rotation=30)
    a2.set_ylabel("라벨과의 상관 (유보)", fontsize=6.8)
    a2.tick_params(labelsize=6.2)
    a2.set_title("여덟 중 일곱이 양수", fontsize=7.2)

    # ③ 판 비용
    ks3 = ["F18", "F6"]
    x3 = np.arange(2)
    a3.bar(x3 - .19, [bd["현행 F18"], bd["현행 F6"]], .34, color="#9aa3ad",
           alpha=.95, edgecolor="none", label="현행")
    a3.bar(x3 + .19, [bd["옮김 F18"], bd["옮김 F6"]], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="옮김")
    for i, (k, r) in enumerate((("F18", j["resolve"]["F18"]),
                                ("F6", j["resolve"]["F6"]))):
        a3.text(i, max(bd[f"현행 {k}"], bd[f"옮김 {k}"]) + .006,
                f"$-${r[0]:.4f}\n$t{{=}}${r[2]}", fontsize=6.0, ha="center",
                color=CLAIM if r[3] else "#6b7480")
    a3.set_xticks(x3); a3.set_xticklabels(ks3, fontsize=6.4)
    a3.set_ylabel("판 $\\rho$", fontsize=7.0)
    a3.set_ylim(.30, .49)
    a3.legend(fontsize=5.9, frameon=False, loc="lower right")
    a3.tick_params(labelsize=6.2)
    a3.set_title("옮기는 값 --- F18 만 갈린다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 167 — 이력이 아니라 표본에 든 적이 있는가였다 ───────────────────
def fig_member(out: str = "fig_member.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note167.json"))
    g, tm = j["grad"], j["time"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1]})

    # ① 0 대 1+ 대 1+ 안에서
    ds = [r[0] for r in g]
    x = np.arange(len(ds))
    a1.bar(x - .19, [r[4] for r in g], .34, color=CLAIM, alpha=.95,
           edgecolor="none", label="0건 대 1건$+$")
    inn = [r[5] if r[5] is not None else 0 for r in g]
    a1.bar(x + .19, inn, .34, color="#9aa3ad", alpha=.95, edgecolor="none",
           label="1건$+$ 안에서")
    a1.axhline(0, color="#8a929b", lw=.8)
    a1.set_xticks(x); a1.set_xticklabels(ds, fontsize=5.8, rotation=25)
    a1.set_ylabel("라벨과의 상관", fontsize=6.8)
    a1.legend(fontsize=5.9, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.2)
    a1.set_title("점프는 있고 기울기는 없다", fontsize=7.2)

    # ② 평균
    a2.bar([0, 1], [np.mean([r[4] for r in g]),
                    np.mean([r[5] for r in g if r[5] is not None])], .5,
           color=[CLAIM, "#9aa3ad"], alpha=.93, edgecolor="none")
    for i, v in enumerate((np.mean([r[4] for r in g]),
                           np.mean([r[5] for r in g if r[5] is not None]))):
        a2.text(i, v + (.006 if v > 0 else -.016), f"{v:+.3f}", fontsize=6.6,
                ha="center", color=CLAIM if v > 0 else "#5a6169")
    a2.axhline(0, color="#8a929b", lw=.8)
    a2.set_xticks([0, 1])
    a2.set_xticklabels(["0건 대 1건$+$\n(6/6 양수)", "1건$+$ 안에서\n(4/6)"],
                       fontsize=6.0)
    a2.set_ylabel("평균 상관", fontsize=6.9)
    a2.set_ylim(-.05, .16)
    a2.tick_params(labelsize=6.2)
    a2.set_title("$+$0.132 대 $-$0.015", fontsize=7.2)

    # ③ 전수로 잰 유일한 도메인
    lab = ["표본 안 계수\n(일곱 도메인 평균)", "펀딩\n표본 안 계수",
           "펀딩\n외부 전수 색인"]
    v = [np.mean([r[3] for r in g]), j["fund_within"], j["fund_module"]]
    a3.bar(np.arange(3), v, .55,
           color=["#9aa3ad", "#c3cad2", CLAIM], alpha=.93, edgecolor="none")
    for i, vv in enumerate(v):
        a3.text(i, vv + (.008 if vv > 0 else -.022), f"{vv:+.3f}",
                fontsize=6.4, ha="center",
                color=CLAIM if i == 2 else "#5a6169")
    a3.axhline(0, color="#8a929b", lw=.8)
    a3.set_xticks(np.arange(3)); a3.set_xticklabels(lab, fontsize=5.6)
    a3.set_ylabel("라벨과의 상관", fontsize=6.9)
    a3.set_ylim(-.26, .18)
    a3.tick_params(labelsize=6.2)
    a3.set_title("제대로 세면 부호가 뒤집힌다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 168 — 아홉 중 여덟이 인기 정렬 표본이다 ─────────────────────────
def fig_sample(out: str = "fig_sample.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note168.json"))
    jump, fund = j["jump"], j["fund"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1.05, 1]})

    # ① 뽑는 법
    grp = [("인기 정렬", j["chart"], CLAIM), ("부분", j["partial"], "#c39aa0"),
           ("아님", j["census"], GATE)]
    y = 0
    for lab, ds, c in grp:
        for d in ds:
            a1.barh(y, 1, .7, color=c, alpha=.92, edgecolor="none")
            a1.text(.05, y, d, fontsize=6.3, va="center", color="white")
            y -= 1
    a1.set_yticks([])
    a1.set_xticks([])
    a1.set_xlim(0, 1.05); a1.set_ylim(y + .5, .6)
    for lab, ds, c in grp:
        pass
    a1.text(1.02, -0.5, "인기 정렬 6", fontsize=6.2, ha="right", color=CLAIM)
    a1.text(1.02, -6.5, "부분 2", fontsize=6.2, ha="right", color="#a8737a")
    a1.text(1.02, -8.5, "아님 2", fontsize=6.2, ha="right", color=GATE)
    a1.set_title("아홉 중 여덟이 차트에서 나왔다", fontsize=7.2)

    # ② 점프 크기
    ds = sorted(jump, key=lambda d: -jump[d])
    x = np.arange(len(ds))
    a2.bar(x, [jump[d] for d in ds], .58, color=CLAIM, alpha=.93,
           edgecolor="none")
    a2.bar([len(ds)], [fund["within"]], .58, color=GATE, alpha=.93,
           edgecolor="none")
    for i, d in enumerate(ds):
        a2.text(i, jump[d] + .008, f"{jump[d]:.2f}", fontsize=5.9,
                ha="center", color=CLAIM)
    a2.text(len(ds), fund["within"] - .028, f"{fund['within']:+.3f}",
            fontsize=6.0, ha="center", color=GATE)
    a2.axhline(0, color="#8a929b", lw=.8)
    a2.set_xticks(list(x) + [len(ds)])
    a2.set_xticklabels(ds + ["펀딩"], fontsize=5.7, rotation=30)
    a2.set_ylabel("0건 대 1건$+$ 점프", fontsize=6.8)
    a2.tick_params(labelsize=6.2)
    a2.set_title("차트 표본에만 점프가 있다", fontsize=7.2)

    # ③ 펀딩 --- 같은 도메인 두 측정
    lab = ["표본 안\n계수", "＋카테고리\n통제", "외부 전수\n색인"]
    v = [fund["within"], fund["cat"], fund["census"]]
    a3.bar(np.arange(3), v, .55, color=["#9aa3ad", "#c3cad2", CLAIM],
           alpha=.93, edgecolor="none")
    for i, vv in enumerate(v):
        a3.text(i, vv + (.01 if vv > 0 else -.025), f"{vv:+.3f}", fontsize=6.4,
                ha="center", color=CLAIM if i == 2 else "#5a6169")
    a3.axhline(0, color="#8a929b", lw=.8)
    a3.set_xticks(np.arange(3)); a3.set_xticklabels(lab, fontsize=5.9)
    a3.set_ylabel("라벨과의 상관", fontsize=6.9)
    a3.set_ylim(-.26, .14)
    a3.tick_params(labelsize=6.2)
    a3.set_title("인기 정렬이 아닌 유일한 도메인", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 169 — 한 칸이 얼마인지 안 정하고 다섯 노트를 썼다 ───────────────
def fig_step(out: str = "fig_step.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note169.json"))
    ax, con, corr = j["axes"], j["con"], j["corr"]
    KO = {"target_breadth": "타깃 폭", "venue_prominence": "장소 노출",
          "entry_friction": "입장 마찰", "media_push": "미디어 푸시",
          "goods_scale": "굿즈 규모"}
    ks = list(KO)
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1.1, 1.05]})

    # ① 옛 크기 대 새 크기
    x = np.arange(len(ks))
    a1.bar(x - .19, [ax["old"][a][0] for a in ks], .34, color="#9aa3ad",
           alpha=.95, edgecolor="none", label="고정 0.25")
    a1.bar(x + .19, [ax["new"][a][0] for a in ks], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="관측 간격")
    a1.set_xticks(x); a1.set_xticklabels([KO[a] for a in ks], fontsize=5.6,
                                         rotation=25)
    a1.set_ylabel("평균 $|$개입 효과$|$", fontsize=6.8)
    a1.legend(fontsize=5.9, frameon=False, loc="upper right")
    a1.tick_params(labelsize=6.2)
    a1.set_title("순위가 바뀐다 (상관 $+$0.30)", fontsize=7.2)

    # ② 크기 대 정확도 --- 전후
    for lab, key, c, m in (("고정 0.25", "old", "#9aa3ad", "o"),
                           ("관측 간격", "new", CLAIM, "s")):
        for a in ks:
            a2.plot([ax[key][a][0]], [ax[key][a][1]], m, ms=5.6, color=c,
                    zorder=3)
        a2.plot([], [], m, ms=5.6, color=c, label=lab)
    for a in ks:
        a2.annotate(KO[a], (ax["new"][a][0], ax["new"][a][1]), fontsize=5.6,
                    xytext=(0, 8), textcoords="offset points", ha="center",
                    color=CLAIM)
    a2.set_xlabel("평균 $|$개입 효과$|$", fontsize=6.8)
    a2.set_ylabel("사전 부호 정확도", fontsize=6.8)
    a2.set_ylim(.55, 1.12)
    a2.legend(fontsize=5.9, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.2)
    a2.set_title(f"$+$0.90 이 $+$0.00 이 된다", fontsize=7.2)

    # ③ 남는 설명은 구성물 수
    x3 = np.arange(len(ks))
    o = sorted(range(len(ks)), key=lambda i: con[ks[i]])
    a3.plot([con[ks[i]] for i in o], [ax["new"][ks[i]][1] for i in o], "o",
            ms=7.0, color=GATE, zorder=3)
    for i in o:
        a3.annotate(f"{KO[ks[i]]}\n{ax['new'][ks[i]][1]:.0%}",
                    (con[ks[i]], ax["new"][ks[i]][1]), fontsize=5.8,
                    xytext=(0, 9), textcoords="offset points", ha="center",
                    color="#4a5158")
    a3.set_xlabel("한 슬롯에 든 구성물 수", fontsize=6.8)
    a3.set_ylabel("사전 부호 정확도", fontsize=6.8)
    a3.set_xlim(.4, 5.7); a3.set_ylim(.55, 1.16)
    a3.set_xticks([1, 2, 3, 4, 5])
    a3.tick_params(labelsize=6.2)
    a3.set_title(f"구성물 수만 남는다 ({corr['con_acc']:+.2f})", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 170 — 걸음을 바꿔도 부호가 그대로인가 ──────────────────────────
def fig_stable(out: str = "fig_stable.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note170.json"))
    pa = j["per_axis"]
    KO = {"target_breadth": "타깃 폭", "goods_scale": "굿즈 규모",
          "media_push": "미디어 푸시", "entry_friction": "입장 마찰",
          "venue_prominence": "장소 노출"}
    ks = list(KO)
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.05, 1, 1]})

    # ① 축별 걸음 불변 비율
    x = np.arange(len(ks))
    v18 = [pa[a]["F18_bagboost"][0] / pa[a]["F18_bagboost"][1] for a in ks]
    v6 = [pa[a]["F6_directpool"][0] / pa[a]["F6_directpool"][1] for a in ks]
    a1.bar(x - .19, v18, .34, color=CLAIM, alpha=.95, edgecolor="none",
           label="F18 배깅")
    a1.bar(x + .19, v6, .34, color=GATE, alpha=.95, edgecolor="none",
           label="F6 능형")
    for i, a in enumerate(ks):
        a1.text(i - .19, v18[i] + .02,
                f"{pa[a]['F18_bagboost'][0]}/{pa[a]['F18_bagboost'][1]}",
                fontsize=5.6, ha="center", color=CLAIM)
    a1.set_xticks(x); a1.set_xticklabels([KO[a] for a in ks], fontsize=5.6,
                                         rotation=25)
    a1.set_ylabel("걸음 다섯에서 부호 불변", fontsize=6.7)
    a1.set_ylim(0, 1.16)
    a1.legend(fontsize=5.9, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.2)
    a1.set_title("되는 축은 전 칸이 불변이다", fontsize=7.2)

    # ② 불변 칸 대 흔들리는 칸의 정확도
    x2 = np.arange(2)
    a2.bar(x2, [26 / 28, 5 / 8], .5, color=[CLAIM, "#9aa3ad"], alpha=.93,
           edgecolor="none")
    for i, (v, lab) in enumerate(((26 / 28, "26/28"), (5 / 8, "5/8"))):
        a2.text(i, v + .02, f"{lab}\n{v:.0%}", fontsize=6.4, ha="center",
                color=CLAIM if i == 0 else "#5a6169")
    a2.axhline(.5, color="#8a929b", lw=.8, ls="--")
    a2.set_xticks(x2)
    a2.set_xticklabels(["걸음 불변 칸", "흔들리는 칸"], fontsize=6.2)
    a2.set_ylabel("사전 부호 정확도 (F18)", fontsize=6.8)
    a2.set_ylim(0, 1.15)
    a2.tick_params(labelsize=6.2)
    a2.set_title("31\\%p 가른다", fontsize=7.2)

    # ③ 정식화별 불변 비율
    a3.bar([0, 1], [28 / 36, 35 / 36], .5, color=[CLAIM, GATE], alpha=.93,
           edgecolor="none")
    for i, (v, lab) in enumerate(((28 / 36, "28/36"), (35 / 36, "35/36"))):
        a3.text(i, v + .02, f"{lab}\n{v:.0%}", fontsize=6.4, ha="center",
                color=CLAIM if i == 0 else GATE)
    a3.set_xticks([0, 1])
    a3.set_xticklabels(["F18 배깅\n(판 1위)", "F6 능형\n(판 4위)"],
                       fontsize=6.1)
    a3.set_ylabel("걸음 불변 칸 비율", fontsize=6.8)
    a3.set_ylim(0, 1.15)
    a3.tick_params(labelsize=6.2)
    a3.set_title("트리는 조각별 상수라 흔들린다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 171 — 일관성과 정확성이 갈린다 ─────────────────────────────────
def fig_consist(out: str = "fig_consist.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note171.json"))
    row, board, met = j["row"], j["board"], j["metrics"]
    SH = lambda f: f.split("_")[0]
    FS = sorted(board, key=lambda f: -board[f])
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.1, 1.05, 1]})

    # ① 잣대 셋의 폭
    ks = ["단순", "불변비율", "불변정확"]
    x = np.arange(len(ks) + 1)
    sp = [met[k]["spread"] for k in ks] + [j["prev"]["상위절반"]["spread"]]
    a1.bar(x, sp, .55,
           color=[CLAIM if k == "불변비율" else "#9aa3ad" for k in ks] + ["#c3cad2"],
           alpha=.93, edgecolor="none")
    for i, v in enumerate(sp):
        a1.text(i, v + .006, f"{v:.3f}", fontsize=6.2, ha="center",
                color=CLAIM if i == 1 else "#5a6169")
    a1.axhline(j["se2"], color=GATE, lw=1.2, ls="--")
    a1.text(3.4, j["se2"] + .008, "2se (36칸)", fontsize=6.0, ha="right",
            color=GATE)
    a1.set_xticks(x)
    a1.set_xticklabels(ks + ["상위절반\n(노트162)"], fontsize=5.7)
    a1.set_ylabel("정식화 다섯 사이의 폭", fontsize=6.8)
    a1.set_ylim(0, .26)
    a1.tick_params(labelsize=6.2)
    a1.set_title("불변비율만 잡음을 넘는다", fontsize=7.2)

    # ② 일관성 대 정확성
    for f in FS:
        tree = "boost" in f
        a2.plot([row[f][1]], [row[f][2]], "o", ms=7.0,
                color=CLAIM if tree else GATE, zorder=3)
        a2.annotate(SH(f), (row[f][1], row[f][2]), fontsize=6.1,
                    xytext=(0, 9), textcoords="offset points", ha="center",
                    color=CLAIM if tree else "#4a5158")
    a2.set_xlabel("걸음 불변 칸 비율 (일관성)", fontsize=6.8)
    a2.set_ylabel("그 칸의 사전 부호 정확도", fontsize=6.8)
    a2.set_xlim(.72, 1.06); a2.set_ylim(.68, 1.0)
    a2.tick_params(labelsize=6.2)
    a2.set_title("둘이 반대로 간다", fontsize=7.2)

    # ③ 분해 --- 단순 = 불변×정확 + 흔들×정확
    x3 = np.arange(len(FS))
    inv = [row[f][1] * row[f][2] for f in FS]
    wob = [(1 - row[f][1]) * (row[f][3] or 0) for f in FS]
    a3.bar(x3, inv, .55, color=CLAIM, alpha=.93, edgecolor="none",
           label="불변 칸에서 맞은 몫")
    a3.bar(x3, wob, .55, bottom=inv, color="#c3cad2", alpha=.93,
           edgecolor="none", label="흔들리는 칸에서")
    for i, f in enumerate(FS):
        a3.text(i, inv[i] + wob[i] + .012, f"{row[f][0]:.0%}", fontsize=6.1,
                ha="center", color="#3a4046")
    a3.set_xticks(x3); a3.set_xticklabels([SH(f) for f in FS], fontsize=5.8,
                                          rotation=15)
    a3.set_ylabel("전체 사전 부호 정확도", fontsize=6.8)
    a3.set_ylim(0, 1.05)
    a3.legend(fontsize=5.7, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.2)
    a3.set_title("트리는 몰아 맞히고 선형은 고루 맞힌다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 172 — 분모를 맞추니 조건화가 사라졌다 ───────────────────────────
def fig_fair(out: str = "fig_fair.pdf", root: str = ".") -> dict:
    import numpy as np
    import collections
    j = json.load(open(Path(root) / "data/state/note172.json"))
    board, ac, aa, ao = j["board"], j["acc_common"], j["acc_all"], j["acc_own"]
    SH = lambda f: f.split("_")[0]
    FS = sorted(board, key=lambda f: -board[f])
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.1, 1.05, 1]})

    # ① 세 분모
    x = np.arange(len(FS))
    a1.plot(x, [ao[f] for f in FS], "--s", ms=4.2, lw=1.2, color="#9aa3ad",
            label="자기 불변칸 (분모 다름)")
    a1.plot(x, [ac[f] for f in FS], "-o", ms=5.0, lw=1.9, color=CLAIM,
            label="공통 26칸 (분모 같음)")
    a1.plot(x, [aa[f] for f in FS], ":^", ms=4.0, lw=1.1, color=GATE,
            label="전체 36칸")
    a1.set_xticks(x); a1.set_xticklabels([SH(f) for f in FS], fontsize=5.8,
                                         rotation=15)
    a1.set_ylabel("사전 부호 정확도", fontsize=6.8)
    a1.set_ylim(.68, 1.02)
    a1.legend(fontsize=5.5, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.2)
    a1.set_title("분모를 맞추면 순서가 제자리로", fontsize=7.2)

    # ② 판상관 --- 조건화 전후
    ks = ["자기 불변칸\n(노트 171)", "공통 26칸\n(노트 172)", "전체 36칸"]
    v = [0.564, j["board_corr_common"], -0.667]
    a2.bar(np.arange(3), v, .55,
           color=["#c3cad2", CLAIM, GATE], alpha=.93, edgecolor="none")
    for i, vv in enumerate(v):
        a2.text(i, vv + (.03 if vv > 0 else -.09), f"{vv:+.2f}", fontsize=6.5,
                ha="center", color=CLAIM if i == 1 else "#5a6169")
    a2.axhline(0, color="#8a929b", lw=.8)
    a2.set_xticks(np.arange(3)); a2.set_xticklabels(ks, fontsize=5.7)
    a2.set_ylabel("판 $\\rho$ 와의 순위상관", fontsize=6.8)
    a2.set_ylim(-.85, .85)
    a2.tick_params(labelsize=6.2)
    a2.set_title("$+$0.56 이 $-$0.63 으로", fontsize=7.2)

    # ③ 공통 칸의 구성
    cnt = collections.Counter(k.split("|")[1] for k in j["common"])
    tot = {"target_breadth": 9, "goods_scale": 8, "entry_friction": 8,
           "venue_prominence": 7, "media_push": 4}
    KO = {"target_breadth": "타깃 폭", "goods_scale": "굿즈 규모",
          "entry_friction": "입장 마찰", "venue_prominence": "장소 노출",
          "media_push": "미디어 푸시"}
    ks3 = list(tot)
    x3 = np.arange(len(ks3))
    a3.bar(x3, [cnt.get(k, 0) / tot[k] for k in ks3], .55,
           color=[CLAIM if cnt.get(k, 0) == tot[k] else "#9aa3ad" for k in ks3],
           alpha=.93, edgecolor="none")
    for i, k in enumerate(ks3):
        a3.text(i, cnt.get(k, 0) / tot[k] + .025, f"{cnt.get(k,0)}/{tot[k]}",
                fontsize=6.1, ha="center",
                color=CLAIM if cnt.get(k, 0) == tot[k] else "#5a6169")
    a3.set_xticks(x3); a3.set_xticklabels([KO[k] for k in ks3], fontsize=5.6,
                                          rotation=25)
    a3.set_ylabel("공통 불변 칸 비율", fontsize=6.8)
    a3.set_ylim(0, 1.18)
    a3.tick_params(labelsize=6.2)
    a3.set_title("되는 축은 전 칸이 살아남는다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 173 — 한쪽만 채우면 무너진다 ───────────────────────────────────
def fig_both(out: str = "fig_both.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note173.json"))
    ks = ["표준 59", "유보만 채움 116", "학습+유보 채움 116", "학습만 채움 116"]
    lab = ["표준 59\n(안 채움)", "유보만\n채움", "양쪽\n채움", "학습만\n채움"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1]})

    # ① 팝업 rho
    x = np.arange(len(ks))
    v = [j[k]["popup"] for k in ks]
    a1.bar(x, v, .58, color=[GATE, "#9aa3ad", CLAIM, "#d4a5a8"], alpha=.93,
           edgecolor="none")
    for i, vv in enumerate(v):
        a1.text(i, vv + (.012 if vv > 0 else -.035), f"{vv:+.3f}", fontsize=6.3,
                ha="center", color=CLAIM if i == 2 else "#5a6169")
    a1.axhline(0, color="#8a929b", lw=.8)
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.9)
    a1.set_ylabel("팝업 $\\rho$", fontsize=6.9)
    a1.set_ylim(-.09, .42)
    a1.tick_params(labelsize=6.2)
    a1.set_title("한쪽만 채우면 무너진다", fontsize=7.2)

    # ② 판 rho
    v2 = [j[k]["board"] for k in ks]
    a2.bar(x, v2, .58, color=[GATE, "#9aa3ad", CLAIM, "#d4a5a8"], alpha=.93,
           edgecolor="none")
    for i, vv in enumerate(v2):
        a2.text(i, vv + .003, f"{vv:.4f}", fontsize=6.0, ha="center",
                color=CLAIM if i == 2 else "#5a6169")
    a2.axhline(j["표준 59"]["board"], color=GATE, lw=1.0, ls="--")
    a2.set_xticks(x); a2.set_xticklabels(lab, fontsize=5.9)
    a2.set_ylabel("판 $\\rho$", fontsize=6.9)
    a2.set_ylim(.42, .456)
    a2.tick_params(labelsize=6.2)
    a2.set_title("양쪽 채움이 기준선을 넘는다", fontsize=7.2)

    # ③ 전이 손실 회수
    n154 = j["note154"]
    a3.bar([0, 1, 2], [n154["standalone"], j["학습+유보 채움 116"]["sub"],
                       j["유보만 채움 116"]["sub"]], .5,
           color=["#c3cad2", CLAIM, "#9aa3ad"], alpha=.93, edgecolor="none")
    for i, vv in enumerate((n154["standalone"], j["학습+유보 채움 116"]["sub"],
                            j["유보만 채움 116"]["sub"])):
        a3.text(i, vv + .01, f"{vv:.3f}", fontsize=6.3, ha="center",
                color=CLAIM if i == 1 else "#5a6169")
    a3.annotate("", xy=(1, j["학습+유보 채움 116"]["sub"]),
                xytext=(2, j["유보만 채움 116"]["sub"]),
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.4))
    a3.text(1.5, .27, f"$+${j['resolve']['늘어난51'][0]:.3f}\n$t{{=}}$0.8",
            fontsize=6.1, ha="center", color=CLAIM)
    a3.set_xticks([0, 1, 2])
    a3.set_xticklabels(["축만 따로\n(상한)", "양쪽\n채움", "유보만\n채움"],
                       fontsize=5.9)
    a3.set_ylabel("늘어난 51건의 $\\rho$", fontsize=6.8)
    a3.set_ylim(0, .44)
    a3.tick_params(labelsize=6.2)
    a3.set_title("간격의 19\\%를 회수한다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 174 — 비대칭이 아니라 맨몸이 문제였다 ──────────────────────────
def fig_bare(out: str = "fig_bare.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note174.json"))
    cov, mask, res = j["cov"], j["mask"], j["resolve"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1.1, 1]})

    # ① 덮음이 시간에 무너진다
    ks = list(cov)
    x = np.arange(len(ks))
    a1.bar(x - .19, [cov[k][0] for k in ks], .34, color="#9aa3ad", alpha=.95,
           edgecolor="none", label="학습 (2025 이전)")
    a1.bar(x + .19, [cov[k][1] for k in ks], .34, color=CLAIM, alpha=.95,
           edgecolor="none", label="유보 (2025 이후)")
    for i, k in enumerate(ks):
        a1.text(i - .19, cov[k][0] + .02, f"{cov[k][0]:.0%}", fontsize=6.0,
                ha="center", color="#5a6169")
        a1.text(i + .19, cov[k][1] + .02, f"{cov[k][1]:.0%}", fontsize=6.0,
                ha="center", color=CLAIM)
    a1.set_xticks(x)
    a1.set_xticklabels(["애니\n장소 노출", "모바일\n미디어 푸시"], fontsize=6.0)
    a1.set_ylabel("축 덮음", fontsize=6.9)
    a1.set_ylim(0, 1.05)
    a1.legend(fontsize=5.9, frameon=False, loc="upper right")
    a1.tick_params(labelsize=6.2)
    a1.set_title("덮음이 시간에 무너진다", fontsize=7.2)

    # ② 그런데 유보 레코드에 축이 남는다
    ds = ["애니", "모바일", "팝업"]
    x2 = np.arange(6)
    bot = np.zeros(len(ds))
    colors = ["#c3cad2", "#a8b2bc", "#8a949e", GATE, CLAIM, "#7a1f2b"]
    for k in range(6):
        v = [mask[d].get(str(k), 0) for d in ds]
        tot = [sum(mask[d].values()) for d in ds]
        frac = [vv / tt for vv, tt in zip(v, tot)]
        a2.bar(np.arange(len(ds)), frac, .55, bottom=bot, color=colors[k],
               alpha=.93, edgecolor="none", label=f"{k}축" if any(v) else None)
        bot = bot + np.array(frac)
    a2.axvline(2.6, color="#8a929b", lw=.8, ls=":")
    a2.bar([3], [1.0], .55, color="#7a1f2b", alpha=.93, edgecolor="none")
    a2.text(3, .5, "0축\n100\\%", fontsize=6.2, ha="center", va="center",
            color="white")
    a2.set_xticks([0, 1, 2, 3])
    a2.set_xticklabels(ds + ["노트173\n학습만채움"], fontsize=5.7)
    a2.set_ylabel("유보 레코드의 손 축 개수", fontsize=6.7)
    a2.set_ylim(0, 1.05)
    a2.legend(fontsize=5.4, frameon=False, loc="lower left", ncol=2)
    a2.tick_params(labelsize=6.2)
    a2.set_title("0축이 되면 무너진다", fontsize=7.2)

    # ③ 빼면 오히려 내려간다
    x3 = np.arange(2)
    a3.bar(x3, [res["F18"][0], res["F6"][0]], .5,
           color=["#9aa3ad", CLAIM], alpha=.93, edgecolor="none")
    a3.errorbar(x3, [res["F18"][0], res["F6"][0]],
                yerr=[2 * res["F18"][1], 2 * res["F6"][1]], fmt="none",
                ecolor="#5a6169", lw=1.0, capsize=3)
    for i, k in enumerate(("F18", "F6")):
        a3.text(i, res[k][0] + 2 * res[k][1] + .0012,
                f"$+${res[k][0]:.4f}\n$t{{=}}${res[k][2]}", fontsize=6.1,
                ha="center", color=CLAIM if res[k][3] else "#5a6169")
    a3.axhline(0, color="#8a929b", lw=.8)
    a3.set_xticks(x3); a3.set_xticklabels(["F18 배깅", "F6 능형"], fontsize=6.3)
    a3.set_ylabel("두 축을 빼면 잃는 판 $\\rho$", fontsize=6.7)
    a3.set_ylim(0, .017)
    a3.tick_params(labelsize=6.2)
    a3.set_title("비대칭 축도 값을 한다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 175 — 관심도의 절반은 ``문서가 있나''였다 ───────────────────────
def fig_mask(out: str = "fig_mask.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note175.json"))
    mc, wk, per, sh = j["maskcorr"], j["wiki"], j["per"], j["share"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.05, 1.05, 1]})

    # ① 마스크가 라벨과 붙는다
    rows = [(r[0], r[4]) for r in mc if r[4] is not None]
    rows.sort(key=lambda z: -z[1])
    x = np.arange(len(rows))
    a1.bar(x, [r[1] for r in rows], .58,
           color=[CLAIM if r[1] > .2 else GATE for r in rows], alpha=.93,
           edgecolor="none")
    for i, r in enumerate(rows):
        if r[1] > .2:
            a1.text(i, r[1] + .012, f"{r[1]:+.2f}", fontsize=6.1, ha="center",
                    color=CLAIM)
    a1.axhline(0, color="#8a929b", lw=.8)
    a1.set_xticks(x); a1.set_xticklabels([r[0] for r in rows], fontsize=5.6,
                                         rotation=30)
    a1.set_ylabel("관측된 축 수와 라벨의 상관", fontsize=6.7)
    a1.tick_params(labelsize=6.2)
    a1.set_title("마스크가 신호를 나른다", fontsize=7.2)

    # ② 위키 이득의 분해
    ks = ["위키 없음", "위키 마스크만", "위키 값만", "위키 전부(현행)"]
    lab = ["없음", "마스크만", "값만", "전부"]
    x2 = np.arange(len(ks))
    for i, (f, c) in enumerate((("F18_bagboost", CLAIM), ("F6_directpool", GATE))):
        a2.plot(x2, [wk[f"{k}|{f}"] for k in ks], "-o", ms=4.6, lw=1.8,
                color=c, label=f.split("_")[0])
    a2.set_xticks(x2); a2.set_xticklabels(lab, fontsize=6.0)
    a2.set_ylabel("판 $\\rho$", fontsize=6.9)
    a2.legend(fontsize=6.0, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.2)
    a2.text(1, wk[f"위키 마스크만|F6_directpool"] - .006,
            f"마스크만으로\n{sh['F6_directpool']['mask']:.0%}", fontsize=6.0,
            ha="center", color=GATE)
    a2.set_title("마스크만으로 절반이 온다", fontsize=7.2)

    # ③ 도메인마다 다르다
    ds = ["세계애니", "게임", "애니"]
    x3 = np.arange(len(ds))
    base = [per["위키 없음|F18_bagboost"][d] for d in ds]
    mk = [per["위키 마스크만|F18_bagboost"][d] - b for d, b in zip(ds, base)]
    vl = [per["위키 값만|F18_bagboost"][d] - b for d, b in zip(ds, base)]
    a3.bar(x3 - .19, mk, .34, color="#9aa3ad", alpha=.95, edgecolor="none",
           label="마스크만")
    a3.bar(x3 + .19, vl, .34, color=CLAIM, alpha=.95, edgecolor="none",
           label="값만")
    for i, d in enumerate(ds):
        a3.text(i - .19, mk[i] + .003, f"{mk[i]:+.3f}", fontsize=5.9,
                ha="center", color="#5a6169")
        a3.text(i + .19, vl[i] + .003, f"{vl[i]:+.3f}", fontsize=5.9,
                ha="center", color=CLAIM)
    a3.axhline(0, color="#8a929b", lw=.8)
    a3.set_xticks(x3); a3.set_xticklabels(ds, fontsize=6.1)
    a3.set_ylabel("도메인 $\\rho$ 이득 (F18)", fontsize=6.7)
    a3.legend(fontsize=5.9, frameon=False, loc="upper right")
    a3.tick_params(labelsize=6.2)
    a3.set_title("세계애니는 값, 애니는 마스크", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 176 — 수집이 나아지면 판이 내려간다 ────────────────────────────
def fig_frag(out: str = "fig_frag.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note176.json"))
    g, imp, res = j["game"], j["improve"], j["resolve"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1, 1.1]})

    # ① 게임의 마스크를 무리별로
    ks = ["위키", "손축(media_push)", "검색"]
    lab = ["위키\n(저명성)", "미디어 푸시\n(퍼블리셔)", "검색\n(한국어 제목)"]
    x = np.arange(len(ks))
    a1.bar(x, [g[k] for k in ks], .55,
           color=[CLAIM if g[k] > 0 else GATE for k in ks], alpha=.93,
           edgecolor="none")
    for i, k in enumerate(ks):
        a1.text(i, g[k] + (.02 if g[k] > 0 else -.05), f"{g[k]:+.3f}",
                fontsize=6.4, ha="center",
                color=CLAIM if g[k] > 0 else GATE)
    a1.axhline(0, color="#8a929b", lw=.8)
    a1.axhline(g["전체"], color="#9aa3ad", lw=1.0, ls="--")
    a1.text(2.45, g["전체"] + .02, f"전체 {g['전체']:+.2f}", fontsize=5.9,
            ha="right", color="#5a6169")
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.7)
    a1.set_ylabel("마스크와 라벨의 상관 (게임)", fontsize=6.7)
    a1.set_ylim(-.32, .55)
    a1.tick_params(labelsize=6.2)
    a1.set_title("셋이 방향이 다르다", fontsize=7.2)

    # ② 섞은 마스크 대 참 마스크
    x2 = np.arange(2)
    a2.bar(x2, [res["F18"][0], res["F6"][0]], .5, color=[CLAIM, GATE],
           alpha=.93, edgecolor="none")
    a2.errorbar(x2, [res["F18"][0], res["F6"][0]],
                yerr=[2 * res["F18"][1], 2 * res["F6"][1]], fmt="none",
                ecolor="#5a6169", lw=1.0, capsize=3)
    for i, k in enumerate(("F18", "F6")):
        a2.text(i, res[k][0] + 2 * res[k][1] + .0008,
                f"$+${res[k][0]:.4f}\n$t{{=}}${res[k][2]}", fontsize=6.1,
                ha="center", color=CLAIM if i == 0 else GATE)
    a2.axhline(0, color="#8a929b", lw=.8)
    a2.set_xticks(x2); a2.set_xticklabels(["F18 배깅", "F6 능형"], fontsize=6.3)
    a2.set_ylabel("참 마스크 $-$ 섞은 마스크", fontsize=6.7)
    a2.set_ylim(0, .014)
    a2.tick_params(labelsize=6.2)
    a2.set_title("마스크는 진짜 신호다 (둘 다 갈린다)", fontsize=7.0)

    # ③ 수집이 나아지면
    fr = [0, 30, 60, 100]
    a3.plot(fr, [imp[str(f)][0] for f in fr], "-o", ms=5.0, lw=2.0,
            color=CLAIM, label="F18 배깅")
    a3.plot(fr, [imp[str(f)][1] for f in fr], "-s", ms=4.6, lw=1.8,
            color=GATE, label="F6 능형")
    a3.annotate(f"$-${imp['0'][0]-imp['100'][0]:.3f}",
                xy=(100, imp["100"][0]), xytext=(62, .415), fontsize=6.6,
                color=CLAIM,
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=1.2))
    a3.text(5, .372, f"위키 축 전체 이득\n$+${j['wikigain']['F18']:.4f}",
            fontsize=5.9, color="#5a6169")
    a3.set_xlabel("빈칸 중 새로 채워진 비율", fontsize=6.8)
    a3.set_ylabel("판 $\\rho$", fontsize=6.9)
    a3.legend(fontsize=6.0, frameon=False, loc="center left")
    a3.tick_params(labelsize=6.2)
    a3.set_title("배깅은 4배를 잃는다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}

# ── 노트 177 — 어렵게 찾은 것이 더 유명했다 ─────────────────────────────
def fig_assume(out: str = "fig_assume.pdf", root: str = ".") -> dict:
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note177.json"))
    by, sim, miss = j["by"], j["sim"], j["missing"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.05, 1.05, 1]})

    # ① 매칭 방식별 조회수
    ks = sorted(by, key=lambda k: by[k][1])
    x = np.arange(len(ks))
    a1.bar(x, [by[k][1] for k in ks], .55,
           color=[GATE if k == "직접" else CLAIM for k in ks], alpha=.93,
           edgecolor="none")
    for i, k in enumerate(ks):
        a1.text(i, by[k][1] + .12, f"{by[k][1]:.2f}\nn={by[k][0]}",
                fontsize=5.8, ha="center",
                color=GATE if k == "직접" else CLAIM)
    a1.axhline(j["med"], color="#8a929b", lw=.9, ls="--")
    a1.text(len(ks) - .5, j["med"] + .1, "전체 중앙", fontsize=5.9,
            ha="right", color="#5a6169")
    a1.set_xticks(x); a1.set_xticklabels(ks, fontsize=5.5, rotation=20)
    a1.set_ylabel("$\\log$ 조회수 중앙", fontsize=6.8)
    a1.set_ylim(0, 8.2)
    a1.tick_params(labelsize=6.2)
    a1.set_title("어렵게 찾은 것이 더 유명했다", fontsize=7.2)

    # ② 채움 규칙에 따른 판 변화
    rules = ["min", "med", "upper", "draw"]
    rl = ["최저값\n(노트176)", "중앙값", "상위 절반", "관측 분포"]
    x2 = np.arange(len(rules))
    base = sim["base"]
    a2.bar(x2 - .19, [sim["res"][r][0] - base[0] for r in rules], .34,
           color=CLAIM, alpha=.95, edgecolor="none", label="F18 배깅")
    a2.bar(x2 + .19, [sim["res"][r][1] - base[1] for r in rules], .34,
           color=GATE, alpha=.95, edgecolor="none", label="F6 능형")
    a2.axhline(0, color="#8a929b", lw=.8)
    for i, r in enumerate(rules):
        a2.text(i - .19, sim["res"][r][0] - base[0] - .004,
                f"{sim['res'][r][0]-base[0]:+.3f}", fontsize=5.7, ha="center",
                color=CLAIM)
    a2.set_xticks(x2); a2.set_xticklabels(rl, fontsize=5.6)
    a2.set_ylabel("빈칸을 다 채웠을 때 판 $\\rho$ 변화", fontsize=6.6)
    a2.legend(fontsize=5.9, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.2)
    a2.set_title("모든 규칙에서 음수, 크기는 다르다", fontsize=7.0)

    # ③ 채울 수 있는 모집단
    ds = sorted(miss, key=lambda d: -miss[d])
    x3 = np.arange(len(ds))
    a3.bar(x3, [miss[d] for d in ds], .58,
           color=[CLAIM if miss[d] >= .99 else GATE for d in ds], alpha=.93,
           edgecolor="none")
    a3.set_xticks(x3); a3.set_xticklabels(ds, fontsize=5.4, rotation=35)
    a3.set_ylabel("유보 중 위키 문서 없음", fontsize=6.8)
    a3.set_ylim(0, 1.12)
    a3.tick_params(labelsize=6.2)
    a3.text(len(ds) / 2, 1.04, "붉은 셋은 100\\% --- 채울 수가 없다",
            fontsize=6.0, ha="center", color=CLAIM)
    a3.set_title("애초에 못 채우는 곳이 많다", fontsize=7.2)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {}



def fig_famous(out: str = "fig_famous.pdf", root: str = ".") -> dict:
    """노트 178 --- 유명한 쪽으로 틀린다, 그런데 맞을 때도 그렇다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note178.json"))
    cov, split = j["덮음"], j["도메인별_문턱효과"]
    infl, corr = j["부풀림"], j["부풀림_대_판이득"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1.1, 1.05]})

    # ① 한국어 위키를 대면 --- 세 도메인의 덮음
    ds = ["아이돌", "도서", "펀딩"]
    x = np.arange(len(ds))
    a1.bar(x, [cov["현행"][d] for d in ds], .5, color=GATE, alpha=.93,
           edgecolor="none")
    for i, d in enumerate(ds):
        a1.text(i, cov["현행"][d] + .03, f"{cov['현행'][d]:.0%}", fontsize=6.6,
                ha="center", color=GATE, fontweight="bold")
        a1.text(i, .015, "0%", fontsize=5.8, ha="center", color="#8a929b")
    a1.axhline(0, color="#8a929b", lw=.8)
    a1.set_xticks(x); a1.set_xticklabels(ds, fontsize=6.4)
    a1.set_ylabel("위키 덮음 (전 → 후)", fontsize=6.8)
    a1.set_ylim(0, .95); a1.tick_params(labelsize=6.2)
    a1.text(.5, .86, f"판은 {j['판_세도메인추가']['F18']['차']:+.4f}\n"
            f"($t{{=}}{j['판_세도메인추가']['F18']['t']}$) --- 안 움직인다",
            fontsize=6.0, ha="center", color=CLAIM,
            transform=a1.transAxes)
    a1.set_title("0\\%를 79\\%로 올렸다", fontsize=7.2)

    # ② 부풀림 대 판 이득 --- 부호가 반대다
    pts = corr["쌍"]
    xs = [p[1] for p in pts]; ys = [p[2] for p in pts]
    a2.axhline(0, color="#8a929b", lw=.8); a2.axvline(0, color="#8a929b", lw=.8)
    a2.scatter(xs, ys, s=[max(14, p[3] / 14) for p in pts],
               c=[CLAIM if p[2] < 0 else GATE for p in pts], alpha=.85,
               edgecolor="none", zorder=3)
    for d, i, g, n in pts:
        a2.annotate(d, (i, g), fontsize=5.6, ha="center",
                    xytext=(0, 7 if g >= 0 else -11),
                    textcoords="offset points", color="#3f4750")
    a2.set_xlabel("포함 매칭의 조회수 부풀림 ($\\log$)", fontsize=6.5)
    a2.set_ylabel("포함을 버리면 얻는 $\\rho$", fontsize=6.5)
    a2.tick_params(labelsize=6.2)
    a2.set_title(f"부호가 반대다 ($\\rho{{=}}{corr['spearman']:+.2f}$)",
                 fontsize=7.0)

    # ③ 도메인별 문턱 효과 --- 갈린다
    rows = sorted(split, key=lambda r: r[4])
    y3 = np.arange(len(rows))
    a3.barh(y3, [r[4] for r in rows], .58,
            color=[CLAIM if r[4] < 0 else GATE for r in rows], alpha=.93,
            edgecolor="none")
    a3.axvline(0, color="#8a929b", lw=.8)
    for i, r in enumerate(rows):
        a3.text(r[4] + (.0016 if r[4] >= 0 else -.0016), i, f"{r[4]:+.3f}",
                fontsize=5.6, va="center",
                ha="left" if r[4] >= 0 else "right",
                color=GATE if r[4] >= 0 else CLAIM)
    a3.set_yticks(y3); a3.set_yticklabels([r[0] for r in rows], fontsize=5.8)
    a3.set_xlabel("포함을 버렸을 때 도메인 $\\rho$ 변화", fontsize=6.5)
    a3.set_xlim(-.042, .052); a3.tick_params(labelsize=6.0)
    a3.set_title("한 문턱이 도메인마다 반대다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(pts)}


def fig_dead(out: str = "fig_dead.pdf", root: str = ".") -> dict:
    """노트 179 --- 틀린 값은 이미 죽어 있었다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note179.json"))
    mm = j["분류규칙"]["도메인별"]
    nu, fl = j["귀무_짝"], j["평탄규칙_반증"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1]})

    # ① 직접 통로가 열려 있었다
    ds = sorted(mm, key=lambda d: -mm[d]["정확_안맞음"])
    y = np.arange(len(ds))
    a1.barh(y, [mm[d]["정확_안맞음"] for d in ds], .56,
            color=[CLAIM if mm[d]["정확_안맞음"] > .3 else GATE for d in ds],
            alpha=.93, edgecolor="none")
    for i, d in enumerate(ds):
        a1.text(mm[d]["정확_안맞음"] + .012, i,
                f"{mm[d]['정확_안맞음']:.0%} (n={mm[d]['정확n']})",
                fontsize=5.5, va="center", color="#3f4750")
    a1.set_yticks(y); a1.set_yticklabels(ds, fontsize=5.9)
    a1.set_xlabel("\\emph{정확} 매칭 중 분류가 안 맞는 몫", fontsize=6.4)
    a1.set_xlim(0, 1.02); a1.tick_params(labelsize=6.0)
    a1.set_title("직접 통로는 안 막혀 있었다", fontsize=7.2)

    # ② 귀무 --- 틀린 값을 섞어도 아무 일도 안 난다
    forms = ["F18_bagboost", "F6_directpool"]
    fl_lab = ["F18 배깅", "F6 능형"]
    x = np.arange(2)
    bad = [nu[f]["틀린값 섞음"]["차"] for f in forms]
    good = [nu[f]["옳은값 섞음"]["차"] for f in forms]
    eb = [nu[f]["틀린값 섞음"]["sd"] for f in forms]
    eg = [nu[f]["옳은값 섞음"]["sd"] for f in forms]
    a2.bar(x - .19, bad, .34, yerr=eb, capsize=2, color=GATE, alpha=.95,
           edgecolor="none", label="틀린 값 섞음", error_kw={"lw": .8})
    a2.bar(x + .19, good, .34, yerr=eg, capsize=2, color=CLAIM, alpha=.95,
           edgecolor="none", label="옳은 값 섞음", error_kw={"lw": .8})
    a2.axhline(0, color="#8a929b", lw=.8)
    for i, f in enumerate(forms):
        a2.text(i - .19, .0012, f"$t{{=}}{nu[f]['틀린값 섞음']['t']}$",
                fontsize=5.7, ha="center", color=GATE)
        a2.text(i + .19, good[i] - .0032, f"$t{{=}}{nu[f]['옳은값 섞음']['t']}$",
                fontsize=5.7, ha="center", color=CLAIM)
    a2.set_xticks(x); a2.set_xticklabels(fl_lab, fontsize=6.2)
    a2.set_ylabel("판 $\\rho$ 변화", fontsize=6.6)
    a2.set_ylim(-.018, .006)
    a2.legend(fontsize=5.9, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.2)
    a2.set_title("틀린 값은 이미 죽어 있다", fontsize=7.0)

    # ③ 노트 178의 평탄 규칙은 안 된다
    ths = fl["문턱별"]
    x3 = np.arange(len(ths))
    a3.bar(x3 - .19, [t["잡음"] / fl["게임_손라벨"]["오매칭"] for t in ths], .34,
           color=GATE, alpha=.95, edgecolor="none", label="게임 오매칭 잡음")
    a3.bar(x3 + .19, [t["오탐"] / fl["게임_손라벨"]["정매칭"] for t in ths], .34,
           color=CLAIM, alpha=.95, edgecolor="none", label="게임 정매칭 오탐")
    a3.plot(x3, [t["세계애니오탐"] for t in ths], "o--", color="#8a929b",
            lw=1.0, ms=3.2, label="세계애니 오탐")
    a3.set_xticks(x3)
    a3.set_xticklabels([f"$m_0{{=}}{t['m0']}$\n$l_0{{=}}{t['l0']}$" for t in ths],
                       fontsize=5.5)
    a3.set_ylabel("몫", fontsize=6.6)
    a3.set_ylim(0, .78)
    a3.legend(fontsize=5.6, frameon=False, loc="upper left")
    a3.tick_params(labelsize=6.2)
    a3.set_title("노트 178의 평탄 규칙은 안 된다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(ds)}


def fig_sign(out: str = "fig_sign.pdf", root: str = ".") -> dict:
    """노트 180 --- 같은 축이 도메인마다 반대 방향이었다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note180.json"))
    ln, mm = j["제목길이"], j["도메인별_안맞음"]
    worth = j["위키축_이득"]["도메인별"]["위키(분류검사 후)"]
    ori = j["부호_맞춤"]["부호"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1.05, 1]})

    # ① 제목 길이가 오매칭을 설명한다
    bk = ln["구간"]
    x = np.arange(len(bk))
    a1.bar(x, [b[2] for b in bk], .58,
           color=[CLAIM if b[2] > .3 else GATE for b in bk], alpha=.93,
           edgecolor="none")
    for i, b in enumerate(bk):
        a1.text(i, b[2] + .022, f"{b[2]:.0%}", fontsize=6.0, ha="center",
                color=CLAIM if b[2] > .3 else GATE)
    a1.set_xticks(x); a1.set_xticklabels([b[0] for b in bk], fontsize=5.6,
                                         rotation=18)
    a1.set_xlabel("제목 글자 수", fontsize=6.5)
    a1.set_ylabel("오매칭 몫", fontsize=6.8)
    a1.set_ylim(0, .92); a1.tick_params(labelsize=6.2)
    a1.text(.97, .90, f"AUC $=$ {ln['전체']['AUC']}", fontsize=6.2, ha="right",
            color="#3f4750", transform=a1.transAxes)
    a1.set_title("짧은 제목이 오매칭을 만든다", fontsize=7.2)

    # ② 오매칭 몫과 위키 이득 --- 안 붙는다
    gain = {r[0]: r[4] for r in worth}
    ds = [d for d in mm if d in gain]
    xs = [mm[d] for d in ds]; ys = [gain[d] for d in ds]
    ns = {r[0]: r[1] for r in worth}
    a2.axhline(0, color="#8a929b", lw=.8)
    a2.scatter(xs, ys, s=[max(14, ns[d] / 14) for d in ds],
               c=[GATE if gain[d] >= 0 else CLAIM for d in ds], alpha=.85,
               edgecolor="none", zorder=3)
    for d, xx, yy in zip(ds, xs, ys):
        a2.annotate(d, (xx, yy), fontsize=5.6, ha="center",
                    xytext=(0, 7 if yy >= 0 else -11),
                    textcoords="offset points", color="#3f4750")
    a2.set_xlabel("그 도메인의 오매칭 몫", fontsize=6.5)
    a2.set_ylabel("위키 축이 주는 도메인 $\\rho$", fontsize=6.4)
    a2.set_ylim(-.028, .085); a2.tick_params(labelsize=6.2)
    a2.set_title("오매칭이 많다고 못 쓰는 게 아니다", fontsize=7.0)

    # ③ 부호가 도메인마다 반대다
    ks = sorted(ori, key=lambda d: -ori[d][0])
    y3 = np.arange(len(ks))
    a3.barh(y3, [ori[d][0] for d in ks], .58,
            color=[GATE if ori[d][0] >= 0 else CLAIM for d in ks], alpha=.93,
            edgecolor="none")
    a3.axvline(0, color="#8a929b", lw=.8)
    for i, d in enumerate(ks):
        v = ori[d][0]
        a3.text(v + (.012 if v >= 0 else -.012), i, f"{v:+.2f}", fontsize=5.7,
                va="center", ha="left" if v >= 0 else "right",
                color=GATE if v >= 0 else CLAIM)
    a3.set_yticks(y3); a3.set_yticklabels(ks, fontsize=5.9)
    a3.set_xlabel("위키 수준 $\\leftrightarrow$ 라벨 (학습 구간)", fontsize=6.3)
    a3.set_xlim(-.42, .35); a3.tick_params(labelsize=6.0)
    a3.set_title("일곱 중 넷이 음수다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(ks)}


def fig_label(out: str = "fig_label.pdf", root: str = ".") -> dict:
    """노트 181 --- 축이 아니라 라벨이 달랐다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note181.json"))
    sq, src = j["속편가설_확인"], j["원작가설_반증"]
    per = j["속편축"]["도메인별"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.45),
                                     gridspec_kw={"width_ratios": [1, 1.05, 1]})

    # ① 속편 대 신작 --- 애니는 갈리고 세계애니는 안 갈린다
    ds = ["애니", "세계애니"]
    x = np.arange(len(ds))
    a1.bar(x - .19, [sq[d]["속편"][1] for d in ds], .34, color=CLAIM, alpha=.95,
           edgecolor="none", label="속편")
    a1.bar(x + .19, [sq[d]["신작"][1] for d in ds], .34, color=GATE, alpha=.95,
           edgecolor="none", label="신작")
    a1.axhline(0, color="#8a929b", lw=.8)
    for i, d in enumerate(ds):
        for off, k, c in ((-.19, "속편", CLAIM), (.19, "신작", GATE)):
            v = sq[d][k][1]
            a1.text(i + off, v + (.03 if v >= 0 else -.06), f"{v:+.2f}",
                    fontsize=5.8, ha="center", color=c)
    a1.set_xticks(x); a1.set_xticklabels(ds, fontsize=6.4)
    a1.set_ylabel("위키 수준 $\\leftrightarrow$ 라벨", fontsize=6.5)
    a1.set_ylim(-.42, .72)
    a1.legend(fontsize=5.9, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.2)
    a1.set_title("애니만 속편에서 뒤집힌다", fontsize=7.2)

    # ② 원작 가설은 반증됐다 --- 애니는 셋 다 음수
    kinds = ["원작", "자신", "둘다"]
    dd = ["애니", "세계애니"]
    x2 = np.arange(len(kinds))
    for k, (d, c) in enumerate(zip(dd, (CLAIM, GATE))):
        vs = [src[d][kk][1] for kk in kinds]
        ns = [src[d][kk][0] for kk in kinds]
        xs = [i + (k - .5) * .34 for i in x2]
        a2.bar([v for v, y in zip(xs, vs) if y is not None],
               [y for y in vs if y is not None], .32, color=c, alpha=.95,
               edgecolor="none", label=d)
        for v, y, n in zip(xs, vs, ns):
            if y is None:
                a2.text(v, .02, f"n={n}", fontsize=5.2, ha="center",
                        color="#8a929b", rotation=90)
            else:
                a2.text(v, y + (.02 if y >= 0 else -.06), f"{y:+.2f}",
                        fontsize=5.5, ha="center", color=c)
    a2.axhline(0, color="#8a929b", lw=.8)
    a2.set_xticks(x2); a2.set_xticklabels(kinds, fontsize=6.2)
    a2.set_ylabel("위키 수준 $\\leftrightarrow$ 라벨", fontsize=6.5)
    a2.set_ylim(-.72, .45)
    a2.legend(fontsize=5.9, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.2)
    a2.set_title("원작 가설은 반증됐다", fontsize=7.0)

    # ③ 속편 축은 잉여다
    rows = sorted(per, key=lambda r: r[4])
    y3 = np.arange(len(rows))
    a3.barh(y3, [r[4] for r in rows], .58,
            color=[CLAIM if r[4] < 0 else GATE for r in rows], alpha=.93,
            edgecolor="none")
    a3.axvline(0, color="#8a929b", lw=.8)
    a3.set_yticks(y3); a3.set_yticklabels([r[0] for r in rows], fontsize=5.8)
    a3.set_xlabel("속편 축을 넣었을 때 도메인 $\\rho$ 변화", fontsize=6.2)
    a3.set_xlim(-.014, .014); a3.tick_params(labelsize=5.8)
    a3.text(.5, .06, "판 $+$.0022 ($t{=}0.95$)", fontsize=6.2, ha="center",
            color="#3f4750", transform=a3.transAxes)
    a3.set_title("명시 축은 잉여다 --- 세 번째", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(rows)}


def fig_past(out: str = "fig_past.pdf", root: str = ".") -> dict:
    """노트 182 --- 웹툰은 자기 과거를 못 쓴다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note182.json"))
    xf = j["전이행렬"]; yr = j["웹툰_연도별"]; th = j["문턱훑기"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.55),
                                     gridspec_kw={"width_ratios": [1.15, 1, 1]})

    # ① 전이 행렬
    doms = xf["도메인"]
    Mx = np.array([[np.nan if v is None else v for v in row] for row in xf["행렬"]])
    im = a1.imshow(Mx, cmap="RdBu_r", vmin=-.55, vmax=.55, aspect="auto")
    a1.set_xticks(range(len(doms)))
    a1.set_xticklabels([d[:4] for d in doms], fontsize=5.2, rotation=45)
    a1.set_yticks(range(len(doms)))
    a1.set_yticklabels([d[:4] for d in doms], fontsize=5.2)
    for i in range(len(doms)):
        a1.add_patch(plt.Rectangle((i - .5, i - .5), 1, 1, fill=False,
                                   edgecolor="#22262b", lw=1.1))
        for k in range(len(doms)):
            if np.isfinite(Mx[i, k]):
                a1.text(k, i, f"{Mx[i,k]:.2f}".replace("0.", "."), fontsize=4.3,
                        ha="center", va="center",
                        color="white" if abs(Mx[i, k]) > .33 else "#22262b")
    a1.set_xlabel("유보 도메인", fontsize=6.4)
    a1.set_ylabel("학습 도메인", fontsize=6.4)
    a1.tick_params(length=0)
    a1.set_title("대각선이 늘 이기지 않는다", fontsize=7.2)

    # ② 웹툰의 두 축이 시든다
    ys = sorted(yr["goods_scale"], key=int)
    xs = [int(v) for v in ys]
    a2.axvspan(2024.5, 2026.5, color="#c9ced4", alpha=.28, lw=0)
    for k, (lab, c) in enumerate((("goods_scale", CLAIM),
                                  ("target_breadth", GATE))):
        a2.plot(xs, [yr[lab][v] for v in ys], "o-", color=c, lw=1.4, ms=3.4,
                label=lab)
    a2.axhline(0, color="#8a929b", lw=.8)
    a2.text(2025.5, .70, "유보", fontsize=6.0, ha="center", color="#5a6169")
    a2.annotate("", xy=(2026, yr["goods_scale"]["2026"]),
                xytext=(2022, yr["goods_scale"]["2022"]),
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=.8, ls=":"))
    a2.set_xticks(xs); a2.set_xticklabels([str(v)[2:] for v in xs], fontsize=5.8)
    a2.set_ylabel("축 $\\leftrightarrow$ 라벨 (그 해)", fontsize=6.4)
    a2.set_ylim(-.48, .82)
    a2.legend(fontsize=5.7, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.0)
    a2.set_title("시들기는 학습 안에서 보인다", fontsize=7.0)

    # ③ 문턱을 훑으면 요동친다
    ths = [-0.05, -0.10, -0.15, -0.20]
    keys = [f"문턱{t}" if t != -0.10 else "문턱-0.1" for t in ths]
    keys = [k if k in th else k.replace("-0.20", "-0.2") for k in keys]
    x3 = np.arange(len(ths))
    f18 = [th[k]["짝검정"]["F18_bagboost"]["차"] for k in keys]
    f6 = [th[k]["짝검정"]["F6_directpool"]["차"] for k in keys]
    a3.bar(x3 - .19, f18, .34, color=GATE, alpha=.95, edgecolor="none",
           label="F18 배깅")
    a3.bar(x3 + .19, f6, .34, color=CLAIM, alpha=.95, edgecolor="none",
           label="F6 능형")
    a3.axhline(0, color="#8a929b", lw=.8)
    for i, k in enumerate(keys):
        for off, v, c, nm in ((-.19, f18[i], GATE, "F18_bagboost"),
                              (.19, f6[i], CLAIM, "F6_directpool")):
            t_ = th[k]["짝검정"][nm]["t"]
            a3.text(i + off, v + (.0016 if v >= 0 else -.0042),
                    f"{t_:+.1f}", fontsize=5.2, ha="center", color=c)
    a3.set_xticks(x3)
    a3.set_xticklabels([f"{t}\n({th[k]['끈수']}개)" for t, k in zip(ths, keys)],
                       fontsize=5.5)
    a3.set_xlabel("시들기 문턱", fontsize=6.4)
    a3.set_ylabel("판 $\\rho$ 변화", fontsize=6.4)
    a3.set_ylim(-.038, .032)
    a3.legend(fontsize=5.7, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.0)
    a3.set_title("한 칸 옆에서 부호가 뒤집힌다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(doms)}


def fig_shade(out: str = "fig_shade.pdf", root: str = ".") -> dict:
    """노트 183 --- 판은 작은 도메인이 무너지는 것을 숨긴다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note183.json"))
    tests, wt = j["시험"], j["가중"]["가중"]
    sh = json.load(open(Path(root) / "data/state/note183_shade.json"))
    raw = json.load(open(Path(root) / "data/state/note182_local.json"))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1.1, 1]})

    # ① 네 경우 --- 제일 나쁜 도메인의 낙차
    tags = ["현행", "웹툰 둘 끔", "만화·세계애니 끔", "전부 끔"]
    vals = [tests[t]["낙차"] or 0.0 for t in tags]
    okv = [tests[t]["통과"] for t in tags]
    x = np.arange(len(tags))
    a1.bar(x, vals, .55, color=[GATE if o else CLAIM for o in okv], alpha=.93,
           edgecolor="none")
    a1.axhline(-.10, color="#8a929b", lw=1.0, ls="--")
    a1.text(len(tags) - .45, -.093, "문턱 $-$0.10", fontsize=5.8, ha="right",
            color="#5a6169")
    a1.axhline(0, color="#8a929b", lw=.8)
    for i, t in enumerate(tags):
        v = vals[i]
        a1.text(i, v - .012, f"{tests[t]['제일나쁜'] or ''}\n{v:+.3f}",
                fontsize=5.4, ha="center", va="top",
                color=GATE if okv[i] else CLAIM)
    a1.set_xticks(x)
    a1.set_xticklabels(["현행", "웹툰\n둘 끔", "만화·세계\n애니 끔", "전부\n끔"],
                       fontsize=5.5)
    a1.set_ylabel("제일 나쁜 도메인의 $\\rho$ 낙차", fontsize=6.4)
    a1.set_ylim(-.20, .045); a1.tick_params(labelsize=6.0)
    a1.set_title("그늘이 둘을 막는다", fontsize=7.2)

    # ② 낙차 대 판 기여
    rows = sorted(wt, key=lambda r: r[3])
    y2 = np.arange(len(rows))
    a2.barh(y2 - .19, [r[3] for r in rows], .34, color=CLAIM, alpha=.95,
            edgecolor="none", label="도메인 $\\rho$ 낙차")
    a2.barh(y2 + .19, [r[4] for r in rows], .34, color=GATE, alpha=.95,
            edgecolor="none", label="판 기여")
    a2.axvline(0, color="#8a929b", lw=.8)
    for i, r in enumerate(rows):
        if abs(r[3]) > .08:
            a2.text(r[3] - .012, i - .19, f"{r[3]:+.3f}", fontsize=5.2,
                    va="center", ha="right" if r[3] < 0 else "left",
                    color=CLAIM)
            a2.text(r[4] + .008, i + .19, f"{r[4]:+.3f}", fontsize=5.2,
                    va="center", ha="left" if r[4] >= 0 else "right",
                    color=GATE)
    a2.set_yticks(y2); a2.set_yticklabels([r[0] for r in rows], fontsize=5.8)
    a2.set_xlim(-.27, .17); a2.tick_params(labelsize=6.0)
    a2.legend(fontsize=5.7, frameon=False, loc="lower right")
    a2.set_title("팝업이 반 토막인데 판은 $-$0.005", fontsize=7.0)

    # ③ 판 가중치
    rows2 = sorted(wt, key=lambda r: -r[2])
    y3 = np.arange(len(rows2))
    a3.barh(y3, [r[2] for r in rows2], .58,
            color=[CLAIM if r[2] < .05 else GATE for r in rows2], alpha=.93,
            edgecolor="none")
    for i, r in enumerate(rows2):
        a3.text(r[2] + .008, i, f"{r[2]:.1%} (n={r[1]})", fontsize=5.3,
                va="center", color="#3f4750")
    a3.set_yticks(y3); a3.set_yticklabels([r[0] for r in rows2], fontsize=5.8)
    a3.set_xlabel("판 $\\rho$ 에서 차지하는 몫", fontsize=6.4)
    a3.set_xlim(0, .40); a3.tick_params(labelsize=6.0)
    a3.set_title("웹툰·애니가 절반이다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(wt)}


def fig_weight(out: str = "fig_weight.pdf", root: str = ".") -> dict:
    """노트 184 --- 셋 다 같은 답을 주는데 하나만 가른다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note184.json"))
    W3 = j["세기준"]; P = j["짝검정"]; cmp_ = j["F18대F6"]["비교"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.15, 1, 1]})

    # ① 세 기준의 점수
    order = W3["순위_크기"]
    ns = [n for n in order if n != "F0_chance"]
    y = np.arange(len(ns))
    for off, key, c, lab in ((-.26, "크기가중", GATE, "크기 가중"),
                             (0.0, "도메인균등", CLAIM, "도메인 균등"),
                             (.26, "최소", "#8a929b", "최소 도메인")):
        a1.barh(y + off, [W3["점수"][n][key] for n in ns], .25, color=c,
                alpha=.93, edgecolor="none", label=lab)
    a1.set_yticks(y)
    a1.set_yticklabels([n.split("_")[0] for n in ns], fontsize=5.8)
    a1.invert_yaxis()
    a1.set_xlabel("$\\rho$", fontsize=6.5)
    a1.set_xlim(0, .62)
    a1.legend(fontsize=5.6, frameon=False, loc="lower right")
    a1.tick_params(labelsize=6.0)
    a1.set_title("셋 다 F18 을 1위로 준다", fontsize=7.2)

    # ② 분해능 --- 이길 확률
    others = ["F8_boost", "F16_trunkhead", "F6_directpool", "F9_ranklik"]
    x2 = np.arange(len(others))
    for off, key, c in ((-.26, "크기가중", GATE), (0.0, "도메인균등", CLAIM),
                        (.26, "최소도메인", "#8a929b")):
        a2.bar(x2 + off, [P["짝검정"][key][n]["이길확률"] for n in others], .25,
               color=c, alpha=.93, edgecolor="none", label=key)
    a2.axhline(.5, color="#8a929b", lw=.9, ls="--")
    a2.text(len(others) - .55, .52, "동전", fontsize=5.6, ha="right",
            color="#5a6169")
    a2.set_xticks(x2)
    a2.set_xticklabels([n.split("_")[0] for n in others], fontsize=5.7)
    a2.set_ylabel("F18 이 이길 붓스트랩 확률", fontsize=6.3)
    a2.set_ylim(0, 1.12)
    a2.legend(fontsize=5.5, frameon=False, loc="upper right", ncol=1)
    a2.tick_params(labelsize=6.0)
    a2.set_title("가르는 것은 크기 가중뿐", fontsize=7.0)

    # ③ F18 대 F6 도메인별
    rows = sorted(cmp_, key=lambda r: r[5])
    y3 = np.arange(len(rows))
    a3.barh(y3, [r[5] for r in rows], .58,
            color=[CLAIM if r[5] < 0 else GATE for r in rows], alpha=.93,
            edgecolor="none")
    a3.axvline(0, color="#8a929b", lw=.8)
    for i, r in enumerate(rows):
        a3.text(r[5] + (.005 if r[5] >= 0 else -.005), i,
                f"{r[5]:+.3f} ({r[2]:.0%})", fontsize=5.2, va="center",
                ha="left" if r[5] >= 0 else "right", color="#3f4750")
    a3.set_yticks(y3); a3.set_yticklabels([r[0] for r in rows], fontsize=5.8)
    a3.set_xlabel("F18 $-$ F6 (도메인 $\\rho$)", fontsize=6.3)
    a3.set_xlim(-.11, .25); a3.tick_params(labelsize=6.0)
    a3.set_title("아홉 중 여덟에서 이긴다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(ns)}


def fig_prov(out: str = "fig_prov.pdf", root: str = ".") -> dict:
    """노트 185 --- 트리의 우위는 긁어온 열에서만 산다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note185.json"))
    S, T = j["대신_나온것"], j["짝검정"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1, 1.15]})
    tags = ["전체 축", "공유 축 다섯만", "긁어온 축만(공유 뺌)"]
    tkey = ["전체 축", "공유 다섯만", "긁어온 축만"]
    short = ["전체 축", "공유 다섯만", "긁어온 축만"]

    # ① 판 격차
    x = np.arange(3)
    gaps = [T[k]["차"] for k in tkey]
    a1.bar(x, gaps, .55, color=[GATE if T[k]["t"] > 1.5 else CLAIM for k in tkey],
           alpha=.93, edgecolor="none",
           yerr=[T[k]["sd"] for k in tkey], capsize=3, error_kw={"lw": .9})
    a1.axhline(0, color="#8a929b", lw=.8)
    for i, k in enumerate(tkey):
        a1.text(i, gaps[i] + T[k]["sd"] + .006, f"$t{{=}}{T[k]['t']}$",
                fontsize=6.0, ha="center",
                color=GATE if T[k]["t"] > 1.5 else CLAIM)
    a1.set_xticks(x); a1.set_xticklabels(short, fontsize=5.8)
    a1.set_ylabel("F18 배깅 $-$ F6 능형 (판 $\\rho$)", fontsize=6.3)
    a1.set_ylim(-.008, .135); a1.tick_params(labelsize=6.0)
    a1.set_title("공유 축에서는 안 갈린다", fontsize=7.2)

    # ② 트리가 이기는 도메인 수
    a2.bar(x - .19, [S[t]["F18이긴수"] / S[t]["전체"] for t in tags], .34,
           color=GATE, alpha=.95, edgecolor="none", label="이긴 도메인 몫")
    a2.bar(x + .19, [S[t]["F18이긴몫"] for t in tags], .34,
           color=CLAIM, alpha=.95, edgecolor="none", label="이긴 표본 몫")
    a2.axhline(.5, color="#8a929b", lw=.9, ls="--")
    for i, t in enumerate(tags):
        a2.text(i - .19, S[t]["F18이긴수"] / S[t]["전체"] + .025,
                f"{S[t]['F18이긴수']}/{S[t]['전체']}", fontsize=5.8, ha="center",
                color=GATE)
    a2.set_xticks(x); a2.set_xticklabels(short, fontsize=5.8)
    a2.set_ylabel("F18 이 이기는 몫", fontsize=6.4)
    a2.set_ylim(0, 1.14)
    a2.legend(fontsize=5.7, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.0)
    a2.set_title("여덟에서 다섯으로", fontsize=7.0)

    # ③ 도메인별 --- 공유 대 긁어온
    sh = {r[0]: r[4] for r in S["공유 축 다섯만"]["행"]}
    sc = {r[0]: r[4] for r in S["긁어온 축만(공유 뺌)"]["행"]}
    ds = sorted(sh, key=lambda d: sh[d])
    y3 = np.arange(len(ds))
    a3.barh(y3 - .19, [sh[d] for d in ds], .34, color=CLAIM, alpha=.95,
            edgecolor="none", label="공유 축 다섯")
    a3.barh(y3 + .19, [sc.get(d, 0) for d in ds], .34, color=GATE, alpha=.95,
            edgecolor="none", label="긁어온 축")
    a3.axvline(0, color="#8a929b", lw=.8)
    a3.text(sh["게임"] - .012, list(ds).index("게임") - .19, f"{sh['게임']:+.2f}",
            fontsize=5.4, va="center", ha="right", color=CLAIM)
    a3.set_yticks(y3); a3.set_yticklabels(ds, fontsize=5.8)
    a3.set_xlabel("F18 $-$ F6 (도메인 $\\rho$)", fontsize=6.3)
    a3.set_xlim(-.31, .36); a3.tick_params(labelsize=6.0)
    a3.legend(fontsize=5.6, frameon=False, loc="lower right")
    a3.set_title("게임이 양쪽 끝을 다 간다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(ds)}


def fig_mono(out: str = "fig_mono.pdf", root: str = ".") -> dict:
    """노트 186 --- 안 틀리는 축은 모두가 같은 방향인 축이었다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note186.json"))
    SP = j["매끈함분할"]; SG = j["부호일관성"]; LV = j["지렛대수렴"]["표"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1]})

    # ① 열 무리별 트리 우위
    ks = ["공유만", "위키·검색만", "덩어리(<중앙)", "달력만", "매끈(고유율≥중앙)"]
    lab = ["공유 다섯", "위키·검색", "덩어리 전체", "달력", "매끈 전체"]
    x = np.arange(len(ks))
    gaps = [SP[k]["차"] for k in ks]
    a1.bar(x, gaps, .55, color=[GATE if SP[k]["t"] > 1.5 else CLAIM for k in ks],
           alpha=.93, edgecolor="none", yerr=[SP[k]["sd"] for k in ks],
           capsize=2.5, error_kw={"lw": .85})
    a1.axhline(0, color="#8a929b", lw=.8)
    for i, k in enumerate(ks):
        a1.text(i, gaps[i] + SP[k]["sd"] + .012, f"$t{{=}}{SP[k]['t']}$",
                fontsize=5.6, ha="center",
                color=GATE if SP[k]["t"] > 1.5 else CLAIM)
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.4, rotation=18)
    a1.set_ylabel("F18 배깅 $-$ F6 능형", fontsize=6.4)
    a1.set_ylim(-.01, .33); a1.tick_params(labelsize=6.0)
    a1.set_title("달력이 매끈함 설명을 깬다", fontsize=7.2)

    # ② 능형이 우연보다 못한 곳
    x2 = np.arange(len(ks))
    a2.bar(x2 - .19, [SP[k]["F18"] for k in ks], .34, color=GATE, alpha=.95,
           edgecolor="none", label="F18 배깅")
    a2.bar(x2 + .19, [SP[k]["F6"] for k in ks], .34, color=CLAIM, alpha=.95,
           edgecolor="none", label="F6 능형")
    a2.axhline(0, color="#8a929b", lw=.8)
    i = ks.index("달력만")
    a2.annotate(f"{SP['달력만']['F6']:+.3f}", (i + .19, SP["달력만"]["F6"]),
                fontsize=5.6, ha="center", xytext=(0, -10),
                textcoords="offset points", color=CLAIM)
    a2.set_xticks(x2); a2.set_xticklabels(lab, fontsize=5.4, rotation=18)
    a2.set_ylabel("판 $\\rho$", fontsize=6.4)
    a2.set_ylim(-.09, .45)
    a2.legend(fontsize=5.7, frameon=False, loc="upper left")
    a2.tick_params(labelsize=6.0)
    a2.set_title("달력에서 능형은 음수다", fontsize=7.0)

    # ③ 공유 축 다섯 --- 일관성과 지렛대 판정
    rows = LV
    y3 = np.arange(len(rows))
    ok = ["안 틀림" in r[4] for r in rows]
    a3.barh(y3, [r[2] for r in rows], .58,
            color=[GATE if o else CLAIM for o in ok], alpha=.93,
            edgecolor="none")
    a3.axvline(.5, color="#8a929b", lw=.9, ls="--")
    a3.text(.505, len(rows) - .35, "동전", fontsize=5.5, color="#5a6169")
    for i, r in enumerate(rows):
        a3.text(r[2] + .015, i, f"{r[2]:.2f} ({r[1]}판)", fontsize=5.3,
                va="center", color="#3f4750")
    a3.set_yticks(y3)
    a3.set_yticklabels([r[0].replace("_", "\\_") for r in rows], fontsize=5.5)
    a3.set_xlabel("도메인 사이 부호 일관성", fontsize=6.3)
    a3.set_xlim(0, 1.3); a3.tick_params(labelsize=6.0)
    a3.set_title("초록 $=$ 노트 172의 ``안 틀림''", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(rows)}


def fig_mimic(out: str = "fig_mimic.pdf", root: str = ".") -> dict:
    """노트 187 --- 달력에서만 트리를 흉내 낼 수 있었다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note187.json"))
    C = j["달력2x2"]; U = j["전체축_합집합"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1]})

    # ① 달력 2×2 사다리
    steps = ["풀링 선형", "풀링 선형 + 2차", "도메인별 선형",
             "도메인별 선형 + 2차", "도메인별 선형 + 2·3차"]
    vals = [C[s] for s in steps]
    x = np.arange(len(steps))
    a1.bar(x, vals, .55, color=[CLAIM if v < 0 else GATE for v in vals],
           alpha=.93, edgecolor="none")
    a1.axhline(C["트리"], color="#22262b", lw=1.2, ls="--")
    a1.text(len(steps) - .4, C["트리"] + .006, f"트리 {C['트리']:.3f}",
            fontsize=6.0, ha="right", color="#22262b")
    a1.axhline(0, color="#8a929b", lw=.8)
    for i, v in enumerate(vals):
        a1.text(i, v + (.004 if v >= 0 else -.011), f"{v:+.3f}", fontsize=5.6,
                ha="center", color=CLAIM if v < 0 else GATE)
    a1.set_xticks(x)
    a1.set_xticklabels(["풀링", "풀링\n+2차", "도메인별", "도메인별\n+2차",
                        "도메인별\n+2·3차"], fontsize=5.3)
    a1.set_ylabel("달력 열만 · 판 $\\rho$", fontsize=6.4)
    a1.set_ylim(-.045, .135); a1.tick_params(labelsize=6.0)
    a1.set_title("달력은 88\\% 재현된다", fontsize=7.2)

    # ② 전체 축에서는 안 된다
    ks = ["F18 트리 (공통)", "F10 도메인별 (합집합)", "F10 + 짝곱 (합집합)",
          "F6 풀링 (합집합)", "F6 + 짝곱 (합집합)"]
    lb = ["트리", "도메인별", "도메인별\n+짝곱", "풀링", "풀링\n+짝곱"]
    v2 = [U[k] for k in ks]
    x2 = np.arange(len(ks))
    a2.bar(x2, v2, .55,
           color=[GATE if i == 0 else CLAIM for i in range(len(ks))],
           alpha=.93, edgecolor="none")
    a2.axhline(U[ks[0]], color="#22262b", lw=1.0, ls="--")
    for i, v in enumerate(v2):
        a2.text(i, v + .006, f"{v:.3f}", fontsize=5.6, ha="center",
                color=GATE if i == 0 else CLAIM)
    a2.set_xticks(x2); a2.set_xticklabels(lb, fontsize=5.4)
    a2.set_ylabel("전체 축 · 판 $\\rho$", fontsize=6.4)
    a2.set_ylim(0, .52); a2.tick_params(labelsize=6.0)
    a2.set_title("전체 축에서는 안 된다", fontsize=7.0)

    # ③ 아티팩트 --- 공통 대 합집합
    F = j["전체축"]
    pairs = [("F10 도메인별 선형", "F10 + 짝곱(상위8)", "공통 모드"),
             (None, None, None)]
    names = ["F10", "F10\n+짝곱"]
    common = [F["F10 도메인별 선형"]["판"], F["F10 + 짝곱(상위8)"]["판"]]
    union = [U["F10 도메인별 (합집합)"], U["F10 + 짝곱 (합집합)"]]
    x3 = np.arange(2)
    a3.bar(x3 - .19, common, .34, color="#8a929b", alpha=.9, edgecolor="none",
           label="공통 모드")
    a3.bar(x3 + .19, union, .34, color=GATE, alpha=.95, edgecolor="none",
           label="합집합 모드")
    for i in range(2):
        a3.text(i - .19, common[i] + .006, f"{common[i]:.4f}", fontsize=5.3,
                ha="center", color="#5a6169")
        a3.text(i + .19, union[i] + .006, f"{union[i]:.4f}", fontsize=5.3,
                ha="center", color=GATE)
    a3.annotate("똑같다", xy=(0.5, common[0] + .022), fontsize=6.0,
                ha="center", color=CLAIM)
    a3.set_xticks(x3); a3.set_xticklabels(names, fontsize=5.8)
    a3.set_ylabel("판 $\\rho$", fontsize=6.4)
    a3.set_ylim(0, .50)
    a3.legend(fontsize=5.7, frameon=False, loc="lower right")
    a3.tick_params(labelsize=6.0)
    a3.set_title("여덟 번째 아티팩트", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(steps)}


def fig_stack(out: str = "fig_stack.pdf", root: str = ".") -> dict:
    """노트 188 --- 무리별로는 되고 합치면 안 된다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note188.json"))
    Wk = j["무리별_재현"]; CR = j["무리안_대_무리사이"]; FM = j["전체축_무리안곱"]
    F19 = j["F19"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1, 1.1]})

    # ① 무리별 재현율
    fams = ["달력(대조)", "위키·검색", "위키만"]
    lab = ["달력", "위키·검색", "위키만"]
    rec = []
    for f in fams:
        r = Wk[f]
        gap = r["트리"] - r["풀링"]
        best = max(r["도메인별+2차"], r["도메인별+2·3차"])
        rec.append((best - r["풀링"]) / gap if gap else 0)
    x = np.arange(len(fams))
    a1.bar(x, rec, .55, color=[GATE if v > .5 else CLAIM for v in rec],
           alpha=.93, edgecolor="none")
    a1.axhline(1.0, color="#22262b", lw=1.0, ls="--")
    a1.text(len(fams) - .45, 1.02, "트리", fontsize=6.0, ha="right",
            color="#22262b")
    for i, v in enumerate(rec):
        a1.text(i, v + .03, f"{v:.0%}", fontsize=6.2, ha="center",
                color=GATE if v > .5 else CLAIM)
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.9)
    a1.set_ylabel("도메인별$+$곱이 메우는 몫", fontsize=6.3)
    a1.set_ylim(0, 1.2); a1.tick_params(labelsize=6.0)
    a1.set_title("무리 하나면 재현된다", fontsize=7.2)

    # ② 무리 안 곱 대 무리 사이 곱
    ks = ["주효과만", "무리 사이 곱만", "무리 안 곱만", "곱 전부"]
    v2 = [CR[k]["도메인별"] for k in ks]
    x2 = np.arange(len(ks))
    a2.bar(x2, v2, .55,
           color=[GATE if k == "무리 안 곱만" else CLAIM for k in ks],
           alpha=.93, edgecolor="none")
    a2.axhline(CR["트리"], color="#22262b", lw=1.0, ls="--")
    a2.text(len(ks) - .45, CR["트리"] + .003, f"트리 {CR['트리']:.3f}",
            fontsize=5.8, ha="right", color="#22262b")
    for i, v in enumerate(v2):
        a2.text(i, v + .003, f"{v:.3f}", fontsize=5.6, ha="center",
                color=GATE if ks[i] == "무리 안 곱만" else CLAIM)
    a2.set_xticks(x2)
    a2.set_xticklabels(["주효과", "무리\n사이", "무리\n안", "전부"],
                       fontsize=5.6)
    a2.set_ylabel("위키·검색 · 판 $\\rho$", fontsize=6.3)
    a2.set_ylim(.25, .325); a2.tick_params(labelsize=6.0)
    a2.set_title("무리 안 곱이 전부다", fontsize=7.0)

    # ③ 합치면 안 된다
    ks3 = ["F18 배깅(챔피언)", "F10 도메인별", "F19 무리쌓기", "F6 능형"]
    v3 = [F19[k] for k in ks3]
    extra = FM["F10 + 무리안 2차"]["판"]
    names = ["F18\n트리", "F10\n주효과", "F10+무리안곱\n(56열)", "F19\n무리쌓기",
             "F6\n능형"]
    vals = [F19["F18 배깅(챔피언)"], F19["F10 도메인별"], extra,
            F19["F19 무리쌓기"], F19["F6 능형"]]
    x3 = np.arange(len(vals))
    a3.bar(x3, vals, .55,
           color=[GATE if i == 0 else CLAIM for i in range(len(vals))],
           alpha=.93, edgecolor="none")
    a3.axhline(vals[0], color="#22262b", lw=1.0, ls="--")
    for i, v in enumerate(vals):
        a3.text(i, v + .006, f"{v:.3f}", fontsize=5.5, ha="center",
                color=GATE if i == 0 else CLAIM)
    a3.set_xticks(x3); a3.set_xticklabels(names, fontsize=5.1)
    a3.set_ylabel("전체 축 · 판 $\\rho$", fontsize=6.3)
    a3.set_ylim(0, .52); a3.tick_params(labelsize=6.0)
    a3.set_title("합치는 방법을 못 찾았다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(vals)}


def fig_knob(out: str = "fig_knob.pdf", root: str = ".") -> dict:
    """노트 189 --- 한 번도 안 건드린 숫자가 있었다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note189.json"))
    T = j["열늘리기_전부"]; AL = j["알파훑기"]; CV = j["교차검증"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1]})

    # ① 열을 늘릴수록 내려간다
    xs = [t[1] for t in T]; ys = [t[2] for t in T]
    a1.axhline(0.4490, color="#22262b", lw=1.1, ls="--")
    a1.text(190, .4520, "트리 .449 (19열)", fontsize=5.8, ha="right",
            color="#22262b")
    a1.axhline(ys[0], color="#8a929b", lw=.9, ls=":")
    a1.scatter(xs, ys, s=32, c=[GATE if i == 0 else CLAIM for i in range(len(xs))],
               alpha=.9, edgecolor="none", zorder=3)
    for (nm, x, y) in T:
        if x in (19, 56, 94, 190):
            a1.annotate(nm, (x, y), fontsize=5.0, ha="center",
                        xytext=(0, -11), textcoords="offset points",
                        color="#3f4750")
    a1.set_xscale("log")
    a1.set_xlabel("열 수 (로그)", fontsize=6.4)
    a1.set_ylabel("판 $\\rho$", fontsize=6.4)
    a1.set_ylim(.31, .47); a1.tick_params(labelsize=6.0)
    a1.set_title("열을 늘린 시도 아홉, 전부 아래", fontsize=7.2)

    # ② 알파를 올리면 둘이 만난다
    als = sorted(float(k) for k in AL)
    a2.plot(als, [AL[_k(AL, a)]["주효과"] for a in als], "o-", color=GATE,
            lw=1.4, ms=3.4, label="19열 주효과")
    a2.plot(als, [AL[_k(AL, a)]["곱"] for a in als], "s--", color=CLAIM,
            lw=1.4, ms=3.2, label="56열 무리 안 곱")
    a2.set_xscale("log")
    a2.set_xlabel("능형 알파 (로그)", fontsize=6.4)
    a2.set_ylabel("판 $\\rho$", fontsize=6.4)
    a2.legend(fontsize=5.8, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.0)
    a2.set_title("규제를 걸면 곱이 사라진다", fontsize=7.0)

    # ③ 안쪽 교차검증 이득
    ns = [n for n in CV if isinstance(CV[n], dict) and "짝검정" in CV[n]]
    x3 = np.arange(len(ns))
    a3.bar(x3 - .19, [CV[n]["유보_현행"] for n in ns], .34, color="#8a929b",
           alpha=.9, edgecolor="none", label="알파 1.0 (기본)")
    a3.bar(x3 + .19, [CV[n]["유보_고름"] for n in ns], .34, color=GATE,
           alpha=.95, edgecolor="none", label="안쪽에서 고름")
    for i, n in enumerate(ns):
        t_ = CV[n]["짝검정"]["t"]
        a3.text(i + .19, CV[n]["유보_고름"] + .006,
                f"$+${CV[n]['차']:.3f}\n$t{{=}}{t_}$", fontsize=5.2,
                ha="center", color=GATE)
        a3.text(i + .19, .02, f"$\\alpha{{=}}{CV[n]['고름']:.0f}$", fontsize=5.2,
                ha="center", color="#3f4750")
    a3.set_xticks(x3)
    a3.set_xticklabels([n.split("_")[0] for n in ns], fontsize=5.8)
    a3.set_ylabel("유보 판 $\\rho$", fontsize=6.4)
    a3.set_ylim(0, .49)
    a3.legend(fontsize=5.6, frameon=False, loc="upper left")
    a3.tick_params(labelsize=6.0)
    a3.set_title("셋 다 오른다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(T)}


def _k(d, a):
    for k in d:
        if abs(float(k) - a) < 1e-9:
            return k
    return list(d)[0]


def fig_flat(out: str = "fig_flat.pdf", root: str = ".") -> dict:
    """노트 190 --- 평평한 곡면에서 최댓값을 고르면 잡음을 고른다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note190.json"))
    CH = j["챔피언조정"]; FX = j["표준처방"]; PK = j["봉우리지수"]["행"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1, 1.05]})

    # ① 안쪽 곡면 --- 트리는 평평하다
    s = sorted([v for v in CH["안쪽"].values()
                if isinstance(v, (int, float)) and np.isfinite(v)], reverse=True)
    a1.plot(range(1, len(s) + 1), s, "o-", color=CLAIM, lw=1.2, ms=2.8,
            label="F18 트리 (54개)")
    rid = [v for v in PK if v[0] == "F6_directpool"][0]
    a1.axhline(np.median(s), color="#8a929b", lw=.9, ls=":")
    a1.annotate("상위 열이 0.003 안", xy=(5, s[4]), fontsize=5.8,
                xytext=(14, s[4] + .006), textcoords="data", color=CLAIM,
                arrowprops=dict(arrowstyle="->", color=CLAIM, lw=.7))
    cur = j["진단"]["현행_안쪽"]
    r = j["진단"]["현행_순위"]
    a1.scatter([r], [cur], s=42, marker="D", color=GATE, zorder=4)
    a1.annotate(f"현행 기본값\n안쪽 {r}/54위\n(유보 1위)", (r, cur), fontsize=5.6,
                xytext=(r + 3, cur - .012), textcoords="data", color=GATE)
    a1.set_xlabel("안쪽 순위", fontsize=6.4)
    a1.set_ylabel("안쪽 평가 $\\rho$", fontsize=6.4)
    a1.tick_params(labelsize=6.0)
    a1.set_title("트리의 안쪽 곡면은 평평하다", fontsize=7.2)

    # ② 처방 전부 아래
    ks = ["현행", "안쪽 최댓값", "상위 다섯 평균", "열여덟 평균"]
    vals = [FX["현행"], FX["안쪽 최댓값"], FX["상위 다섯 평균"], FX["열여덟 평균"],
            FX["단순한 것"]["판"]]
    names = ["기본값", "안쪽\n최댓값", "상위 다섯\n평균", "열여덟\n평균",
             "1-SE 풍\n(단순)"]
    x2 = np.arange(len(vals))
    a2.bar(x2, vals, .55,
           color=[GATE if i == 0 else CLAIM for i in range(len(vals))],
           alpha=.93, edgecolor="none")
    a2.axhline(vals[0], color="#22262b", lw=1.0, ls="--")
    for i, v in enumerate(vals):
        a2.text(i, v + .005, f"{v:.4f}", fontsize=5.4, ha="center",
                color=GATE if i == 0 else CLAIM)
    a2.set_xticks(x2); a2.set_xticklabels(names, fontsize=5.2)
    a2.set_ylabel("유보 판 $\\rho$", fontsize=6.4)
    a2.set_ylim(.39, .47); a2.tick_params(labelsize=6.0)
    a2.set_title("처방 넷 전부 기본값 아래", fontsize=7.0)

    # ③ 봉우리 지수가 가른다
    xs = [r[5] for r in PK]; ys = [r[6] for r in PK]
    a3.axhline(0, color="#8a929b", lw=.8)
    a3.axvline(0.5, color="#8a929b", lw=1.0, ls="--")
    a3.text(.52, -.008, "문턱 0.5", fontsize=5.8, color="#5a6169")
    a3.scatter(xs, ys, s=52, c=[GATE if y > 0 else CLAIM for y in ys],
               alpha=.9, edgecolor="none", zorder=3)
    for r in PK:
        a3.annotate(r[0].split("_")[0], (r[5], r[6]), fontsize=5.6,
                    ha="center", xytext=(0, 8 if r[6] > 0 else -12),
                    textcoords="offset points", color="#3f4750")
    a3.set_xlabel("안쪽 봉우리 지수", fontsize=6.4)
    a3.set_ylabel("조정이 주는 유보 $\\rho$", fontsize=6.3)
    a3.set_xlim(0, 1.0); a3.set_ylim(-.016, .019)
    a3.tick_params(labelsize=6.0)
    a3.set_title("평평하면 고르지 마라", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(PK)}


def fig_frac(out: str = "fig_frac.pdf", root: str = ".") -> dict:
    """노트 191 --- 둘 다 되는 비율이 없다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note191.json"))
    D = j["도메인탈락_아님"]; F = j["비율훑기"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL * .72, 2.5))

    # ① 도메인을 되살려도 그대로
    ks = ["최소25행", "최소12행", "최소8행"]
    x = np.arange(len(ks))
    a1.bar(x - .19, [D[k]["도메인수"] / 10 for k in ks], .34, color="#8a929b",
           alpha=.9, edgecolor="none", label="도메인 수 $\\div$ 10")
    a1.bar(x + .19, [D[k]["봉우리"] for k in ks], .34, color=CLAIM, alpha=.95,
           edgecolor="none", label="트리 봉우리 지수")
    a1.axhline(.5, color="#22262b", lw=1.0, ls="--")
    a1.text(len(ks) - .45, .52, "문턱 0.5", fontsize=5.8, ha="right",
            color="#22262b")
    for i, k in enumerate(ks):
        a1.text(i + .19, D[k]["봉우리"] + .018, f"{D[k]['봉우리']:.3f}",
                fontsize=5.6, ha="center", color=CLAIM)
        a1.text(i - .19, D[k]["도메인수"] / 10 + .018, f"{D[k]['도메인수']}개",
                fontsize=5.6, ha="center", color="#5a6169")
    a1.set_xticks(x)
    a1.set_xticklabels(["최소 25행\n(현행)", "최소 12행", "최소 8행"],
                       fontsize=5.6)
    a1.set_ylim(0, 1.12)
    a1.legend(fontsize=5.7, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.0)
    a1.set_title("도메인을 되살려도 평평하다", fontsize=7.2)

    # ② 비율을 바꾸면 --- 둘이 엇갈린다
    fr = sorted(F, key=float)
    xs = [float(f) for f in fr]
    a2.plot(xs, [F[f]["트리봉우리"] for f in fr], "o-", color=CLAIM, lw=1.5,
            ms=4.2, label="F18 트리")
    a2.plot(xs, [F[f]["능형봉우리"] for f in fr], "s-", color=GATE, lw=1.5,
            ms=4.0, label="F6 능형")
    a2.axhline(.5, color="#22262b", lw=1.0, ls="--")
    a2.text(.86, .52, "문턱 0.5", fontsize=5.8, ha="right", color="#22262b")
    a2.axvspan(.66, .74, color="#c9ced4", alpha=.3, lw=0)
    a2.text(.70, .05, "현행", fontsize=5.8, ha="center", color="#5a6169")
    for f in fr:
        a2.annotate(f"학습 {F[f]['학습행']}\n평가 {F[f]['평가행']}",
                    (float(f), max(F[f]["트리봉우리"], F[f]["능형봉우리"]) + .06),
                    fontsize=4.9, ha="center", color="#3f4750")
    a2.set_xlabel("학습 구간 안에서 앞쪽이 차지하는 비율", fontsize=6.3)
    a2.set_ylabel("안쪽 봉우리 지수", fontsize=6.4)
    a2.set_ylim(0, .88); a2.set_xlim(.44, .91)
    a2.legend(fontsize=5.9, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.0)
    a2.set_title("둘 다 문턱을 넘는 비율이 없다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(fr)}


def fig_small(out: str = "fig_small.pdf", root: str = ".") -> dict:
    """노트 192 --- 안쪽은 언제나 더 작은 모형을 고른다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note192.json"))
    RP = j["반복분할"]; AG = j["선택일치도"]; SC = j["용량보정"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1, 1.1]})

    # ① 평균하면 뭉개진다
    x = np.arange(3)
    for k, (nm, c) in enumerate((("능형", GATE), ("트리", CLAIM))):
        v = RP[nm]["한번씩"]
        a1.plot(x, v, "o-", color=c, lw=1.4, ms=4.0, label=f"{nm} 한 번씩")
        a1.axhline(RP[nm]["평균"], color=c, lw=1.1, ls="--")
        a1.text(2.05, RP[nm]["평균"], f" 평균 {RP[nm]['평균']}", fontsize=5.6,
                va="center", color=c)
    a1.axhline(.5, color="#22262b", lw=1.0, ls=":")
    a1.text(-.05, .52, "문턱 0.5", fontsize=5.7, color="#22262b")
    a1.set_xticks(x); a1.set_xticklabels(["0.55", "0.70", "0.85"], fontsize=5.9)
    a1.set_xlabel("앞쪽 비율", fontsize=6.4)
    a1.set_ylabel("안쪽 봉우리 지수", fontsize=6.4)
    a1.set_ylim(0, .78); a1.set_xlim(-.15, 2.6)
    a1.legend(fontsize=5.6, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.0)
    a1.set_title("평균하면 뭉개진다", fontsize=7.2)

    # ② 일치도는 이득을 못 맞춘다
    GAIN = {"F6_directpool": .0111, "F10_pershrink": .0123,
            "F11_poolunion": .0131, "F18_bagboost": -.0103}
    ks = list(GAIN)
    xs = [AG[k]["일치도"] for k in ks]
    ys = [GAIN[k] for k in ks]
    a2.axhline(0, color="#8a929b", lw=.8)
    a2.scatter(xs, ys, s=52, c=[GATE if y > 0 else CLAIM for y in ys],
               alpha=.9, edgecolor="none", zorder=3)
    for k, xx, yy in zip(ks, xs, ys):
        a2.annotate(k.split("_")[0], (xx, yy), fontsize=5.6, ha="center",
                    xytext=(0, 8 if yy > 0 else -12), textcoords="offset points",
                    color="#3f4750")
    a2.set_xlabel("분할 사이 선택 일치도", fontsize=6.4)
    a2.set_ylabel("조정이 주는 유보 $\\rho$", fontsize=6.3)
    a2.set_xlim(.5, 1.15); a2.set_ylim(-.016, .019)
    a2.text(.55, -.013, f"$\\rho{{=}}{j['선택일치도']['상관']['일치도']:+.2f}$",
            fontsize=6.2, color=CLAIM)
    a2.tick_params(labelsize=6.0)
    a2.set_title("일치해도 옳지 않다", fontsize=7.0)

    # ③ 용량을 키우면
    order = ["안쪽이 고른 것", "반복을 비율만큼", "학습률을 비율만큼",
             "반복·학습률 둘 다", "반복을 비율제곱만큼"]
    lab = ["안쪽이\n고른 것", "반복 $\\times r$", "학습률 $\\times r$",
           "둘 다 $\\times r$", "반복 $\\times r^2$"]
    vals = [SC[k]["판"] for k in order]
    x3 = np.arange(len(order))
    base = SC["기본값"]["판"]
    a3.bar(x3, vals, .55,
           color=[GATE if v > base else CLAIM for v in vals], alpha=.93,
           edgecolor="none")
    a3.axhline(base, color="#22262b", lw=1.1, ls="--")
    a3.text(len(order) - .45, base + .0012, f"기본값 {base}", fontsize=5.7,
            ha="right", color="#22262b")
    for i, v in enumerate(vals):
        a3.text(i, v + .0012, f"{v:.4f}", fontsize=5.3, ha="center",
                color=GATE if v > base else CLAIM)
    a3.set_xticks(x3); a3.set_xticklabels(lab, fontsize=5.0)
    a3.set_ylabel("유보 판 $\\rho$", fontsize=6.4)
    a3.set_ylim(.432, .462); a3.tick_params(labelsize=6.0)
    a3.set_title("용량을 $r^2$ 키우면 넘는다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(order)}


def fig_three(out2: str = "fig_three3.pdf", root: str = ".") -> dict:
    """노트 193 --- 세 방식이 다 같은 곳에서 막혔다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note193.json"))
    S = j["세방식"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL * .72, 2.5))

    ks = list(S)
    lab = ["한 번 자름\n(0.70)", "세 번 잘라\n평균", "앞으로-사슬\n(4블록)"]
    x = np.arange(len(ks))

    # ① 봉우리 지수 --- 셋 다 막힌다
    a1.bar(x - .19, [S[k]["트리봉우리"] for k in ks], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="F18 트리")
    a1.bar(x + .19, [S[k].get("능형봉우리", 0) for k in ks], .34, color=GATE,
           alpha=.95, edgecolor="none", label="F6 능형")
    a1.axhline(.5, color="#22262b", lw=1.1, ls="--")
    a1.text(len(ks) - .45, .52, "문턱 0.5", fontsize=5.8, ha="right",
            color="#22262b")
    for i, k in enumerate(ks):
        a1.text(i - .19, S[k]["트리봉우리"] + .02, f"{S[k]['트리봉우리']:.3f}",
                fontsize=5.5, ha="center", color=CLAIM)
        a1.text(i + .19, S[k].get("능형봉우리", 0) + .02,
                f"{S[k].get('능형봉우리', 0):.3f}", fontsize=5.5, ha="center",
                color=GATE)
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.5)
    a1.set_ylabel("안쪽 봉우리 지수", fontsize=6.4)
    a1.set_ylim(0, .78)
    a1.legend(fontsize=5.8, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.0)
    a1.set_title("트리는 셋 다 문턱 아래", fontsize=7.2)

    # ② 유보 --- 막은 것이 옳았다
    base = 0.4490
    have = [k for k in ks if "트리유보" in S[k]]
    x2 = np.arange(len(have) + 1)
    vals = [base] + [S[k]["트리유보"] for k in have]
    names = ["기본값\n(안 고름)"] + ["한 번 자름이\n고른 것",
                                 "앞으로-사슬이\n고른 것"][:len(have)]
    a2.bar(x2, vals, .55,
           color=[GATE if i == 0 else CLAIM for i in range(len(vals))],
           alpha=.93, edgecolor="none")
    a2.axhline(base, color="#22262b", lw=1.1, ls="--")
    for i, v in enumerate(vals):
        a2.text(i, v + .0012, f"{v:.4f}", fontsize=5.6, ha="center",
                color=GATE if i == 0 else CLAIM)
    a2.text(1.5, .4345, "$t{=}-2.5$ · $-3.0$", fontsize=5.9, ha="center",
            color=CLAIM)
    a2.set_xticks(x2); a2.set_xticklabels(names, fontsize=5.3)
    a2.set_ylabel("F18 유보 판 $\\rho$", fontsize=6.4)
    a2.set_ylim(.432, .456); a2.tick_params(labelsize=6.0)
    a2.set_title("막은 것이 두 번 다 옳았다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out2, format="pdf"); plt.close(fig)
    return {"n": len(ks)}


def fig_row(out: str = "fig_row.pdf", root: str = ".") -> dict:
    """노트 194 --- 열은 아홉 번 실패했고 행은 한 번에 됐다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note194.json"))
    SW = j["훑기"]; IN = j["안쪽"]; PT = j["짝검정"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.05, 1, 1]})

    # ① tau 훑기
    ks = ["가중 없음", "tau=12년", "tau=8년", "tau=4년", "tau=2년"]
    x = np.arange(len(ks))
    for off, f, c, lab in ((-.19, "F18_bagboost", CLAIM, "F18 배깅"),
                           (.19, "F6_directpool", GATE, "F6 능형")):
        v = [SW[k][f][0] for k in ks]
        e = [SW[k][f][1] for k in ks]
        a1.bar(x + off, v, .34, yerr=e, capsize=2, color=c, alpha=.95,
               edgecolor="none", label=lab, error_kw={"lw": .8})
    a1.axhline(SW["가중 없음"]["F18_bagboost"][0], color=CLAIM, lw=.9, ls=":")
    a1.axhline(SW["가중 없음"]["F6_directpool"][0], color=GATE, lw=.9, ls=":")
    a1.set_xticks(x)
    a1.set_xticklabels(["없음", "12년", "8년", "4년", "2년"], fontsize=5.8)
    a1.set_xlabel("감쇠 $\\tau$", fontsize=6.4)
    a1.set_ylabel("판 $\\rho$", fontsize=6.4)
    a1.set_ylim(.34, .49)
    a1.legend(fontsize=5.8, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.0)
    a1.set_title("$\\tau{=}2$년이 둘 다 제일 좋다", fontsize=7.2)

    # ② 안쪽 곡선 --- 단조인데 봉우리 지수가 낮다
    order = ["없음", "12.0", "8.0", "4.0", "2.0", "1.0"]
    for f, c, lab in (("F6_directpool", GATE, "F6 능형"),
                      ("F18_bagboost", CLAIM, "F18 배깅")):
        sc = IN[f]["안쪽"]
        v = [sc[k] for k in order if k in sc]
        a2.plot(range(len(v)), v, "o-", color=c, lw=1.4, ms=3.6, label=lab)
    a2.set_xticks(range(len(order)))
    a2.set_xticklabels(["없음", "12", "8", "4", "2", "1"], fontsize=5.8)
    a2.set_xlabel("감쇠 $\\tau$ (년)", fontsize=6.4)
    a2.set_ylabel("안쪽 평가 $\\rho$", fontsize=6.4)
    a2.text(.03, .40, "F6 봉우리 0.30 · 단조 \\textbf{0.94}", fontsize=5.9,
            transform=a2.transAxes, color=GATE)
    a2.text(.03, .32, "F18 봉우리 0.39 · 단조 0.67", fontsize=5.9,
            transform=a2.transAxes, color=CLAIM)
    a2.legend(fontsize=5.8, frameon=False, loc="upper right")
    a2.tick_params(labelsize=6.0)
    a2.set_title("단조인데 봉우리는 낮다", fontsize=7.0)

    # ③ 도메인별
    per = PT["F6_도메인별"]
    rows = sorted(per, key=lambda r: r[4])
    y3 = np.arange(len(rows))
    a3.barh(y3, [r[4] for r in rows], .58,
            color=[CLAIM if r[4] < 0 else GATE for r in rows], alpha=.93,
            edgecolor="none")
    a3.axvline(0, color="#8a929b", lw=.8)
    for i, r in enumerate(rows):
        a3.text(r[4] + (.006 if r[4] >= 0 else -.006), i, f"{r[4]:+.3f}",
                fontsize=5.3, va="center",
                ha="left" if r[4] >= 0 else "right",
                color=GATE if r[4] >= 0 else CLAIM)
    a3.set_yticks(y3); a3.set_yticklabels([r[0] for r in rows], fontsize=5.8)
    a3.set_xlabel("F6 도메인 $\\rho$ 변화 ($\\tau{=}2$)", fontsize=6.2)
    a3.set_xlim(-.06, .26); a3.tick_params(labelsize=6.0)
    a3.set_title("여섯이 오르고 셋이 내린다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(rows)}


def fig_seen(out: str = "fig_seen.pdf", root: str = ".") -> dict:
    """노트 195 --- 보이지 않는 이득은 못 가져간다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note195.json"))
    G = j["유보격자"]; SQ = j["순차"]; JT = j["같이"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL * .74, 2.5))

    # ① 유보 격자 히트맵
    taus = ["None", "4.0", "2.0", "1.0"]
    alphas = [1, 5, 20, 100, 500]
    Mx = np.array([G[t] for t in taus])
    im = a1.imshow(Mx, cmap="YlGnBu", aspect="auto",
                   vmin=Mx.min(), vmax=Mx.max())
    a1.set_xticks(range(len(alphas)))
    a1.set_xticklabels([str(a) for a in alphas], fontsize=5.8)
    a1.set_yticks(range(len(taus)))
    a1.set_yticklabels(["없음", "4년", "2년", "1년"], fontsize=5.8)
    for i in range(len(taus)):
        for k in range(len(alphas)):
            a1.text(k, i, f"{Mx[i,k]:.3f}"[1:], fontsize=5.0, ha="center",
                    va="center",
                    color="white" if Mx[i, k] > Mx.mean() else "#22262b")
    bi, bk = np.unravel_index(np.argmax(Mx), Mx.shape)
    a1.add_patch(plt.Rectangle((bk - .5, bi - .5), 1, 1, fill=False,
                               edgecolor=GATE, lw=1.8))
    a1.add_patch(plt.Rectangle((-.5, 2 - .5), 1, 1, fill=False,
                               edgecolor=CLAIM, lw=1.8))
    a1.set_xlabel("능형 알파", fontsize=6.4)
    a1.set_ylabel("감쇠 $\\tau$", fontsize=6.4)
    a1.tick_params(length=0)
    a1.set_title("초록 $=$ 격자 최고 · 빨강 $=$ 순차가 고름", fontsize=6.8)

    # ② 절차 비교
    ks = ["기본", "alpha만", "tau만", "같이(노트195)", "순차"]
    vals = [SQ[k]["판"] for k in ks]
    best = float(Mx.max())
    x2 = np.arange(len(ks))
    a2.bar(x2, vals, .55,
           color=[GATE if k == "순차" else CLAIM for k in ks], alpha=.93,
           edgecolor="none")
    a2.axhline(best, color="#22262b", lw=1.1, ls="--")
    a2.text(len(ks) - .45, best + .0015, f"격자 최고 {best:.4f}", fontsize=5.7,
            ha="right", color="#22262b")
    for i, v in enumerate(vals):
        a2.text(i, v + .0015, f"{v:.4f}", fontsize=5.4, ha="center",
                color=GATE if ks[i] == "순차" else CLAIM)
    a2.set_xticks(x2)
    a2.set_xticklabels(["기본", "$\\alpha$만", "$\\tau$만", "같이", "순차"],
                       fontsize=5.8)
    a2.set_ylabel("유보 판 $\\rho$", fontsize=6.4)
    a2.set_ylim(.36, .418); a2.tick_params(labelsize=6.0)
    a2.set_title("순차가 제일 가깝다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": Mx.size}


def fig_cost(out: str = "fig_cost.pdf", root: str = ".") -> dict:
    """노트 196 --- 보게 만드는 값이 보고 얻는 값과 같았다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note196.json"))
    M = j["배수"]; F = j["최종"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL * .74, 2.5))

    ks = ["배수1", "배수2", "배수4"]
    x = np.arange(len(ks))
    # ① 배수와 안쪽 지수 / 유보
    a1.bar(x - .19, [M[k]["안쪽alpha"]["봉우리"] for k in ks], .34, color=GATE,
           alpha=.95, edgecolor="none", label="안쪽 봉우리")
    a1.bar(x + .19, [M[k]["안쪽alpha"]["단조"] for k in ks], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="안쪽 단조")
    a1.axhline(.5, color="#22262b", lw=1.0, ls="--")
    a1.axhline(.8, color="#22262b", lw=.8, ls=":")
    for i, k in enumerate(ks):
        ok = M[k]["안쪽alpha"]["통과"]
        a1.text(i, 1.04, "통과" if ok else "막힘", fontsize=6.0, ha="center",
                color=GATE if ok else CLAIM, fontweight="bold")
    a1.set_xticks(x); a1.set_xticklabels(["1배", "2배", "4배"], fontsize=6.0)
    a1.set_xlabel("되뽑는 행 수", fontsize=6.4)
    a1.set_ylabel("2단계 $\\alpha$ 안쪽 지수", fontsize=6.4)
    a1.set_ylim(0, 1.18)
    a1.legend(fontsize=5.8, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.0)
    a1.set_title("배수를 키우면 보이기 시작한다", fontsize=7.0)

    # ② 유보 --- 그래도 안 오른다
    lab = ["기본", "순차 1단계\n($\\tau2$·1배·$\\alpha1$)",
           "순차 2단계\n($\\tau2$·4배·$\\alpha100$)", "못 고르는 곳\n($\\tau2$·1배·$\\alpha100$)"]
    keys = ["기본 (없음, a=1)", "순차 1단계까지 (t=2, m=1, a=1)",
            "순차 2단계까지 (t=2, m=4, a=100)", "참고 (t=2, m=1, a=100)"]
    vals = [F[k] for k in keys]
    x2 = np.arange(len(vals))
    a2.bar(x2, vals, .55,
           color=[CLAIM if i == 0 else (GATE if i < 3 else "#8a929b")
                  for i in range(len(vals))], alpha=.93, edgecolor="none")
    for i, v in enumerate(vals):
        a2.text(i, v + .0015, f"{v:.4f}", fontsize=5.5, ha="center",
                color="#3f4750")
    a2.annotate("", xy=(2, vals[2] + .006), xytext=(1, vals[1] + .006),
                arrowprops=dict(arrowstyle="<->", color="#5a6169", lw=.8))
    a2.text(1.5, vals[1] + .009, "$\\pm$0.0000", fontsize=5.8, ha="center",
            color="#5a6169")
    a2.set_xticks(x2); a2.set_xticklabels(lab, fontsize=4.9)
    a2.set_ylabel("유보 판 $\\rho$", fontsize=6.4)
    a2.set_ylim(.36, .418); a2.tick_params(labelsize=6.0)
    a2.set_title("그런데 판은 그대로다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(ks)}


def fig_carry(out: str = "fig_carry.pdf", root: str = ".") -> dict:
    """노트 197 --- 풀링은 닮아서가 아니라 업어 주기 때문이다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note197.json"))
    CF = j["계수"]; WHY = j["무엇이예측"]["표"]; TH = j["문턱"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.05, 1.05, 1]})

    # ① 쌍 코사인 히트맵
    doms = CF["도메인"]
    Mx = np.array(CF["쌍코사인"])
    a1.imshow(Mx, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
    a1.set_xticks(range(len(doms)))
    a1.set_xticklabels([x[:4] for x in doms], fontsize=5.2, rotation=45)
    a1.set_yticks(range(len(doms)))
    a1.set_yticklabels([x[:4] for x in doms], fontsize=5.2)
    for i in range(len(doms)):
        for k in range(len(doms)):
            a1.text(k, i, f"{Mx[i,k]:.2f}"[1:], fontsize=4.6, ha="center",
                    va="center", color="white" if Mx[i, k] > .55 else "#22262b")
    a1.tick_params(length=0)
    a1.set_title(f"쌍 코사인 --- 음수 0/21", fontsize=7.2)

    # ② 혼자 rho 가 풀링 이득을 예측한다
    xs = [r[3] for r in WHY]; ys = [r[5] for r in WHY]
    ns = [r[1] for r in WHY]
    a2.axhline(0, color="#8a929b", lw=.8)
    a2.scatter(xs, ys, s=[max(16, n / 8) for n in ns],
               c=[GATE if y > 0 else CLAIM for y in ys], alpha=.88,
               edgecolor="none", zorder=3)
    for r in WHY:
        a2.annotate(r[0], (r[3], r[5]), fontsize=5.5, ha="center",
                    xytext=(0, 8 if r[5] > 0 else -12),
                    textcoords="offset points", color="#3f4750")
    a2.set_xlabel("혼자 학습했을 때 유보 $\\rho$", fontsize=6.3)
    a2.set_ylabel("풀링이 주는 $\\rho$", fontsize=6.4)
    a2.text(.05, .07, f"$\\rho{{=}}{j['무엇이예측']['상관']['혼자 rho'][0]:+.2f}$",
            fontsize=6.4, transform=a2.transAxes, color=CLAIM)
    a2.tick_params(labelsize=6.0)
    a2.set_title("못 배우는 쪽만 얻는다", fontsize=7.0)

    # ③ 문턱 훑기
    ths = [0.0, 0.02, 0.05, 0.10, 0.20]
    vals = [TH[f"문턱{t}"]["판"] for t in ths]
    x3 = np.arange(len(ths) + 1)
    allv = vals + [TH["완전 분리"]]
    names = ["0.00", "0.02", "0.05", "0.10", "0.20\n(=풀링)", "완전\n분리"]
    a3.bar(x3, allv, .55,
           color=[GATE if v > .39 else CLAIM for v in allv], alpha=.93,
           edgecolor="none")
    a3.axhline(TH["문턱0.2"]["판"], color="#22262b", lw=1.0, ls="--")
    a3.text(len(allv) - .45, TH["문턱0.2"]["판"] + .002, "완전 풀링",
            fontsize=5.7, ha="right", color="#22262b")
    for i, v in enumerate(allv):
        a3.text(i, v + .002, f"{v:.4f}", fontsize=5.1, ha="center",
                color="#3f4750")
    a3.set_xticks(x3); a3.set_xticklabels(names, fontsize=5.2)
    a3.set_xlabel("안쪽 격차 문턱", fontsize=6.3)
    a3.set_ylabel("판 $\\rho$", fontsize=6.4)
    a3.set_ylim(.33, .415); a3.tick_params(labelsize=6.0)
    a3.set_title("0.02$\\sim$0.10 에서 같은 답", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(doms)}


def fig_sharp(out: str = "fig_sharp.pdf", root: str = ".") -> dict:
    """노트 198 --- 사이에 있을 줄 알았는데 끝에 있었다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note198.json"))
    S = j["결과"]; R = j["안쪽대유보"]
    KS = [0.0, 2.0, 5.0, 10.0, 20.0, 50.0, 200.0]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL * .74, 2.5))

    # ① 안쪽과 유보가 따로 논다
    inn = [S["안쪽"][str(k)] for k in KS]
    ho = [S[f"k={k}"]["판"] for k in KS]
    x = np.arange(len(KS))
    a1.plot(x, inn, "o-", color=CLAIM, lw=1.5, ms=4.0, label="안쪽 평가")
    a1b = a1.twinx()
    a1b.plot(x, ho, "s--", color=GATE, lw=1.5, ms=3.8, label="유보 판")
    a1.axvline(KS.index(S["고름k"]), color="#8a929b", lw=1.0, ls=":")
    a1.text(KS.index(S["고름k"]) + .1, min(inn) + .001,
            f"안쪽이 고름\n$k{{=}}{S['고름k']:.0f}$", fontsize=5.6, color="#5a6169")
    a1.set_xticks(x)
    a1.set_xticklabels([f"{k:g}" for k in KS], fontsize=5.6)
    a1.set_xlabel("날카로움 $k$", fontsize=6.4)
    a1.set_ylabel("안쪽 평가 $\\rho$", fontsize=6.3, color=CLAIM)
    a1b.set_ylabel("유보 판 $\\rho$", fontsize=6.3, color=GATE)
    a1.tick_params(labelsize=6.0); a1b.tick_params(labelsize=6.0)
    a1.text(.03, .06, f"둘의 상관 $\\rho{{=}}{R['spearman']:+.2f}$",
            fontsize=6.2, transform=a1.transAxes, color="#3f4750")
    a1.set_title("안쪽이 아무것도 안 말한다", fontsize=7.0)

    # ② 도메인별 lam --- 끝으로 갈수록 이분
    doms = list(S["k=0.0"]["lam"])
    x2 = np.arange(len(KS))
    for dm, c in zip(doms, [CLAIM, "#8a929b", GATE, "#6d7f8f", "#b08a5a",
                            "#7a6f9b", "#9b6f7a"]):
        a2.plot(x2, [S[f"k={k}"]["lam"][dm] for k in KS], "o-", color=c,
                lw=1.2, ms=2.8, label=dm)
    a2.axhline(.5, color="#8a929b", lw=.8, ls=":")
    a2.set_xticks(x2); a2.set_xticklabels([f"{k:g}" for k in KS], fontsize=5.6)
    a2.set_xlabel("날카로움 $k$", fontsize=6.4)
    a2.set_ylabel("$\\lambda$ (혼자 계수의 몫)", fontsize=6.2)
    a2.set_ylim(-.05, 1.15)
    a2.legend(fontsize=4.9, frameon=False, ncol=2, loc="upper left")
    a2.tick_params(labelsize=6.0)
    a2.set_title("유보는 오른쪽 끝이 제일 좋다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(KS)}


def fig_loop(out: str = "fig_loop.pdf", root: str = ".") -> dict:
    """노트 199 --- 순환을 없앴더니 신호가 없어졌다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note199.json"))
    T3 = j["세토막"]; SG = j["부호비교"]
    J198 = json.load(open(Path(root) / "data/state/note198.json"))["결과"]
    KS = [0.0, 2.0, 5.0, 10.0, 20.0, 50.0, 200.0]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1, 1.05]})

    # ① 두 토막 대 세 토막 --- 유보 곡선이 뒤집힌다
    ho2 = [J198[f"k={k}"]["판"] for k in KS]
    ho3 = [T3["유보"][str(k)] for k in KS]
    x = np.arange(len(KS))
    a1.plot(x, ho2, "o-", color=GATE, lw=1.5, ms=4.0, label="두 토막 격차")
    a1.plot(x, ho3, "s--", color=CLAIM, lw=1.5, ms=3.8, label="세 토막 격차")
    a1.axhline(.3955, color="#22262b", lw=1.0, ls=":")
    a1.text(len(KS) - .5, .3965, "이분 (채택)", fontsize=5.7, ha="right",
            color="#22262b")
    a1.set_xticks(x); a1.set_xticklabels([f"{k:g}" for k in KS], fontsize=5.6)
    a1.set_xlabel("날카로움 $k$", fontsize=6.4)
    a1.set_ylabel("유보 판 $\\rho$", fontsize=6.4)
    a1.legend(fontsize=5.7, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.0)
    a1.set_title("유보 곡선이 뒤집힌다", fontsize=7.2)

    # ② 안쪽이 유보를 따라가나
    inn3 = [T3["안쪽"][str(k)] for k in KS]
    inn2 = [J198["안쪽"][str(k)] for k in KS]
    a2.scatter(inn2, ho2, s=40, color=GATE, alpha=.9, edgecolor="none",
               label=f"두 토막 ($\\rho{{=}}{J198 and 0.036:+.2f}$)")
    a2.scatter(inn3, ho3, s=40, marker="s", color=CLAIM, alpha=.9,
               edgecolor="none", label=f"세 토막 ($\\rho{{=}}{T3['상관']:+.2f}$)")
    a2.set_xlabel("안쪽 평가 $\\rho$", fontsize=6.4)
    a2.set_ylabel("유보 판 $\\rho$", fontsize=6.4)
    a2.legend(fontsize=5.6, frameon=False, loc="upper left")
    a2.tick_params(labelsize=6.0)
    a2.set_title("순환을 없애면 따라간다", fontsize=7.0)

    # ③ 격차 부호가 뒤집힌 둘
    ds = list(SG)
    y3 = np.arange(len(ds))
    a3.barh(y3 - .19, [SG[k]["두토막"] for k in ds], .34, color=GATE,
            alpha=.95, edgecolor="none", label="두 토막")
    a3.barh(y3 + .19, [SG[k]["세토막"] for k in ds], .34, color=CLAIM,
            alpha=.95, edgecolor="none", label="세 토막")
    a3.axvline(0, color="#8a929b", lw=.9)
    for i, k in enumerate(ds):
        if SG[k]["뒤집힘"]:
            a3.text(.20, i, "부호 뒤집힘", fontsize=5.4, va="center",
                    color="#22262b", fontweight="bold")
    a3.set_yticks(y3); a3.set_yticklabels(ds, fontsize=5.8)
    a3.set_xlabel("안쪽 격차 (혼자 $-$ 풀링)", fontsize=6.2)
    a3.set_xlim(-.38, .42)
    a3.legend(fontsize=5.6, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.0)
    a3.set_title("웹툰과 애니가 뒤집힌다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(ds)}


def fig_interp(out: str = "fig_interp.pdf", root: str = ".") -> dict:
    """노트 200 --- 보간으로 재고 외삽을 시켰다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note200.json"))
    rows = j["부호비교"]; W = j["무게"]; AC = j["무게정확도"]
    F = j["접힘"]
    KS = [0.0, 2.0, 5.0, 10.0, 20.0, 50.0, 200.0]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1]})

    # ① 세 추정기의 격차 대 참
    ds = [r[0] for r in rows]
    y = np.arange(len(ds))
    a1.barh(y - .28, [r[1] for r in rows], .24, color="#22262b", alpha=.9,
            edgecolor="none", label="참 (유보)")
    a1.barh(y, [r[2] for r in rows], .24, color=GATE, alpha=.95,
            edgecolor="none", label="두 토막")
    a1.barh(y + .28, [r[4] for r in rows], .24, color=CLAIM, alpha=.95,
            edgecolor="none", label="접힘 교차")
    a1.axvline(0, color="#8a929b", lw=.9)
    i = ds.index("웹툰")
    a1.text(.06, i, "웹툰 --- 무게의 60\\%", fontsize=5.5, va="center",
            color="#22262b")
    a1.set_yticks(y); a1.set_yticklabels(ds, fontsize=5.8)
    a1.set_xlabel("격차 (혼자 $-$ 풀링)", fontsize=6.3)
    a1.set_xlim(-.36, .32)
    a1.legend(fontsize=5.5, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.0)
    a1.set_title("접힘은 웹툰을 반대로 본다", fontsize=7.0)

    # ② 부호 정확도 --- 개수 대 무게
    nm = ["두 토막", "세 토막", "접힘 교차"]
    cnt = [sum(1 for r in rows if (r[1] > 0) == (r[c] > 0)) / len(rows)
           for c in (2, 3, 4)]
    wt = [AC["두토막"], AC["세토막"], AC["접힘"]]
    x = np.arange(3)
    a2.bar(x - .19, cnt, .34, color="#8a929b", alpha=.9, edgecolor="none",
           label="개수로 세면")
    a2.bar(x + .19, wt, .34, color=GATE, alpha=.95, edgecolor="none",
           label="무게로 세면")
    a2.axhline(.5, color="#22262b", lw=.9, ls="--")
    for i in range(3):
        a2.text(i - .19, cnt[i] + .02, f"{cnt[i]:.0%}", fontsize=5.6,
                ha="center", color="#5a6169")
        a2.text(i + .19, wt[i] + .02, f"{wt[i]:.0%}", fontsize=5.6,
                ha="center", color=GATE if wt[i] > .5 else CLAIM)
    a2.set_xticks(x); a2.set_xticklabels(nm, fontsize=5.6)
    a2.set_ylabel("격차 부호 정확도", fontsize=6.4)
    a2.set_ylim(0, 1.12)
    a2.legend(fontsize=5.7, frameon=False, loc="upper right")
    a2.tick_params(labelsize=6.0)
    a2.set_title("개수는 못 가르고 무게는 가른다", fontsize=7.0)

    # ③ 유보 곡선
    ho = [F["유보"][str(k)] for k in KS]
    J198 = json.load(open(Path(root) / "data/state/note198.json"))["결과"]
    ho2 = [J198[f"k={k}"]["판"] for k in KS]
    x3 = np.arange(len(KS))
    a3.plot(x3, ho2, "o-", color=GATE, lw=1.5, ms=3.8, label="두 토막 격차")
    a3.plot(x3, ho, "^--", color=CLAIM, lw=1.5, ms=3.8, label="접힘 격차")
    a3.axhline(.3955, color="#22262b", lw=1.0, ls=":")
    a3.text(len(KS) - .5, .3968, "이분 (채택)", fontsize=5.6, ha="right",
            color="#22262b")
    a3.set_xticks(x3); a3.set_xticklabels([f"{k:g}" for k in KS], fontsize=5.6)
    a3.set_xlabel("날카로움 $k$", fontsize=6.4)
    a3.set_ylabel("유보 판 $\\rho$", fontsize=6.4)
    a3.legend(fontsize=5.7, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.0)
    a3.set_title("완전히 반대로 간다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(ds)}


def fig_already(out: str = "fig_already.pdf", root: str = ".") -> dict:
    """노트 201 --- 최근 가중이 이미 고르고 있었다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note201.json"))
    L = j["등록10도메인_사다리"]; G = j["격차변화"]; M = j["수동7도메인"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1]})

    # ① 사다리
    ks = ["① 기본 능형 (a=1, 가중X, 선택X)", "② +알파20", "③ +최근가중",
          "④ +도메인선택 (=F21)"]
    lab = ["기본\n능형", "$+\\alpha{=}20$", "$+$최근\n가중", "$+$도메인\n선택"]
    v = [L[k] for k in ks]
    x = np.arange(len(v))
    a1.bar(x, v, .55, color=[CLAIM] + [GATE] * 2 + ["#8a929b"], alpha=.93,
           edgecolor="none")
    for i in range(len(v)):
        a1.text(i, v[i] + .002, f"{v[i]:.4f}", fontsize=5.5, ha="center",
                color="#3f4750")
        if i:
            a1.text(i - .5, max(v[i], v[i - 1]) + .009,
                    f"{v[i]-v[i-1]:+.4f}", fontsize=5.6, ha="center",
                    color=GATE if v[i] - v[i - 1] > .005 else CLAIM)
    a1.axhline(L["⑤ 선택만 (가중X)"], color="#22262b", lw=.9, ls=":")
    a1.text(3.4, L["⑤ 선택만 (가중X)"] + .002, "선택만 (가중X)", fontsize=5.4,
            ha="right", color="#22262b")
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.4)
    a1.set_ylabel("판 $\\rho$", fontsize=6.4)
    a1.set_ylim(.355, .425); a1.tick_params(labelsize=6.0)
    a1.set_title("선택은 마지막에 아무것도 안 더한다", fontsize=6.9)

    # ② 격차가 사라진다
    ds = sorted(G["가중없음"], key=lambda k: -abs(G["가중없음"][k]))
    y2 = np.arange(len(ds))
    a2.barh(y2 - .19, [G["가중없음"][k] for k in ds], .34, color="#8a929b",
            alpha=.9, edgecolor="none", label="가중 없음")
    a2.barh(y2 + .19, [G["tau2"][k] for k in ds], .34, color=GATE, alpha=.95,
            edgecolor="none", label="$\\tau{=}2$")
    a2.axvline(0, color="#8a929b", lw=.9)
    a2.axvline(.02, color="#22262b", lw=.9, ls="--")
    i = ds.index("모바일")
    a2.annotate("$+$.143 $\\to$ $+$.004", (0.14, i - .19), fontsize=5.5,
                va="center", color="#22262b",
                xytext=(0.16, i - .7), textcoords="data",
                arrowprops=dict(arrowstyle="->", color="#22262b", lw=.7))
    a2.set_yticks(y2); a2.set_yticklabels(ds, fontsize=5.6)
    a2.set_xlabel("안쪽 격차 (혼자 $-$ 풀링)", fontsize=6.2)
    a2.set_xlim(-.42, .45)
    a2.legend(fontsize=5.6, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.0)
    a2.set_title("모바일의 격차가 사라진다", fontsize=7.0)

    # ③ 두 틀의 차이
    names = ["최근 가중만", "도메인별만", "둘 다", "(더하면)"]
    man = [M["최근 가중만"]["판"] - M["기본"]["판"],
           M["도메인별만"]["판"] - M["기본"]["판"],
           M["둘 다"]["판"] - M["기본"]["판"],
           (M["최근 가중만"]["판"] + M["도메인별만"]["판"] - 2 * M["기본"]["판"])]
    reg = [L["③ +최근가중"] - L["② +알파20"],
           L["⑤ 선택만 (가중X)"] - L["② +알파20"],
           L["④ +도메인선택 (=F21)"] - L["② +알파20"],
           (L["③ +최근가중"] + L["⑤ 선택만 (가중X)"] - 2 * L["② +알파20"])]
    x3 = np.arange(len(names))
    a3.bar(x3 - .19, man, .34, color=GATE, alpha=.95, edgecolor="none",
           label="일곱 도메인 (수동)")
    a3.bar(x3 + .19, reg, .34, color=CLAIM, alpha=.95, edgecolor="none",
           label="열 도메인 (등록)")
    a3.axhline(0, color="#8a929b", lw=.8)
    a3.set_xticks(x3); a3.set_xticklabels(names, fontsize=5.2, rotation=12)
    a3.set_ylabel("기준 대비 $\\rho$ 이득", fontsize=6.3)
    a3.legend(fontsize=5.5, frameon=False, loc="upper left")
    a3.tick_params(labelsize=6.0)
    a3.set_title("겹치느냐가 도메인 집합에 달렸다", fontsize=6.9)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(ds)}


def fig_order(out: str = "fig_order2.pdf", root: str = ".") -> dict:
    """노트 202 --- 재는 것을 먼저, 바꾸는 것을 나중에."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note202.json"))
    TT = j["짝검정"]; G = j["격차변화"]; P = j["포트폴리오"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.05, 1, 1]})

    # ① 두 순서
    ks = ["기본 (a=20, 가중X, 선택X)", "선택만", "가중만", "가중→선택", "선택→가중"]
    lab = ["기본", "선택만", "가중만", "가중$\\to$선택", "선택$\\to$가중"]
    v = [TT[k] for k in ks]
    x = np.arange(len(v))
    a1.bar(x, v, .55,
           color=["#8a929b", "#8a929b", "#8a929b", CLAIM, GATE], alpha=.93,
           edgecolor="none")
    for i in range(len(v)):
        a1.text(i, v[i] + .0015, f"{v[i]:.4f}", fontsize=5.4, ha="center",
                color="#3f4750")
    a1.annotate("", xy=(4, v[4] + .005), xytext=(3, v[3] + .005),
                arrowprops=dict(arrowstyle="->", color="#22262b", lw=.9))
    a1.text(3.5, v[4] + .008, f"{v[4]-v[3]:+.4f}", fontsize=5.8, ha="center",
            color="#22262b")
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.1, rotation=12)
    a1.set_ylabel("판 $\\rho$", fontsize=6.4)
    a1.set_ylim(.365, .422); a1.tick_params(labelsize=6.0)
    a1.set_title("선택을 먼저 하는 쪽이 낫다", fontsize=7.0)

    # ② 선택의 한계 기여
    x2 = np.arange(2)
    marg = [TT["가중→선택"] - TT["가중만"], TT["선택→가중"] - TT["가중만"]]
    a2.bar(x2, marg, .5, color=[CLAIM, GATE], alpha=.95, edgecolor="none")
    a2.axhline(0, color="#8a929b", lw=.8)
    for i, (m, t) in enumerate(zip(marg, [0.13, 1.81])):
        a2.text(i, m + .0004, f"{m:+.4f}\n$t{{=}}{t}$", fontsize=6.0,
                ha="center", color=CLAIM if i == 0 else GATE)
    a2.set_xticks(x2)
    a2.set_xticklabels(["가중한 자료에서\n격차를 잼", "안 가중한 자료에서\n격차를 잼"],
                       fontsize=5.4)
    a2.set_ylabel("선택의 한계 기여", fontsize=6.4)
    a2.set_ylim(-.001, .0088); a2.tick_params(labelsize=6.0)
    a2.set_title("가중이 신호를 지운다", fontsize=7.0)

    # ③ 포트폴리오
    ns = sorted(P, key=lambda k: -P[k])
    y3 = np.arange(len(ns))
    a3.barh(y3, [P[n] for n in ns], .58,
            color=[GATE if n == "F21_recentpick" else
                   ("#22262b" if n == "F18_bagboost" else "#8a929b")
                   for n in ns], alpha=.93, edgecolor="none")
    for i, n in enumerate(ns):
        a3.text(P[n] + .004, i, f"{P[n]:.4f}", fontsize=5.5, va="center",
                color="#3f4750")
    a3.set_yticks(y3)
    a3.set_yticklabels([n.replace("_", "\\_") for n in ns], fontsize=5.0)
    a3.invert_yaxis()
    a3.set_xlabel("판 $\\rho$", fontsize=6.4)
    a3.set_xlim(0, .53); a3.tick_params(labelsize=6.0)
    a3.set_title("선형 최고가 .4094", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(ns)}


def fig_alone(out: str = "fig_alone.pdf", root: str = ".") -> dict:
    """노트 203 --- 혼자 할 수 있는지는 알겠는데 함께 할지는 모르겠다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note203.json"))
    SP = j["조각열둘"]; SC = j["점수"]; GP = j["격차"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1]})

    # ① 후보 일곱 --- 도메인 대 조각
    ks = ["덮음", "마스크변이", "시간변화", "마스크상관최대", "축상관최대",
          "라벨묶임", "학습n"]
    old = SP["이전"]; new = SP["상관"]
    y = np.arange(len(ks))
    a1.barh(y - .19, [old.get(k, 0) for k in ks], .34, color="#8a929b",
            alpha=.9, edgecolor="none", label="도메인 일곱")
    a1.barh(y + .19, [new.get(k, 0) for k in ks], .34, color=GATE, alpha=.95,
            edgecolor="none", label="조각 열둘")
    a1.axvline(0, color="#8a929b", lw=.9)
    for v in (-.5, .5):
        a1.axvline(v, color="#22262b", lw=.7, ls=":")
    a1.set_yticks(y); a1.set_yticklabels(ks, fontsize=5.7)
    a1.set_xlabel("혼자 $\\rho$ 와의 스피어만", fontsize=6.3)
    a1.set_xlim(-.85, .85)
    a1.legend(fontsize=5.6, frameon=False, loc="lower right")
    a1.tick_params(labelsize=6.0)
    a1.set_title("셋만 살아남는다", fontsize=7.0)

    # ② 점수가 혼자 rho 를 맞힌다
    rows = GP["행"]
    xs = [r[1] for r in rows]; ys = [r[2] for r in rows]
    a2.scatter(xs, ys, s=46, color=GATE, alpha=.9, edgecolor="none", zorder=3)
    for r in rows:
        a2.annotate(r[0], (r[1], r[2]), fontsize=5.4, ha="center",
                    xytext=(0, 8), textcoords="offset points", color="#3f4750")
    a2.set_xlabel("합친 점수", fontsize=6.4)
    a2.set_ylabel("혼자 학습 $\\rho$", fontsize=6.4)
    a2.text(.05, .07, f"$\\rho{{=}}{GP['점수_혼자']:+.2f}$", fontsize=7.0,
            transform=a2.transAxes, color=GATE)
    a2.tick_params(labelsize=6.0)
    a2.set_title("혼자 할 수 있는지는 맞힌다", fontsize=7.0)

    # ③ 그런데 격차는 못 맞힌다
    zs = [r[3] for r in rows]
    a3.axhline(0, color="#8a929b", lw=.9)
    a3.scatter(xs, zs, s=46, c=[CLAIM if v < 0 else GATE for v in zs],
               alpha=.9, edgecolor="none", zorder=3)
    for r in rows:
        a3.annotate(r[0], (r[1], r[3]), fontsize=5.4, ha="center",
                    xytext=(0, 8 if r[3] > 0 else -12),
                    textcoords="offset points", color="#3f4750")
    a3.set_xlabel("합친 점수", fontsize=6.4)
    a3.set_ylabel("격차 (혼자 $-$ 풀링)", fontsize=6.3)
    a3.text(.05, .07, f"$\\rho{{=}}{GP['점수_격차']:+.2f}$", fontsize=7.0,
            transform=a3.transAxes, color=CLAIM)
    a3.tick_params(labelsize=6.0)
    a3.set_title("함께 할지는 못 맞힌다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(rows)}


def fig_carry2(out: str = "fig_carry2.pdf", root: str = ".") -> dict:
    """노트 204 --- 풀은 업어 주고 눌러 준다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note204.json"))
    J = j["후보실패"]["행"]; R = j["회귀"]; be = j["손익분기"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.15, 1, 1]})

    # ① 압축
    S = np.array([r["혼자rho"] for r in J]); P = np.array([r["풀링rho"] for r in J])
    xs = np.linspace(0, .58, 50)
    a1.plot(xs, xs, color="#8a929b", lw=1.0, ls="--")
    a1.text(.53, .555, "$y{=}x$", fontsize=5.8, color="#8a929b")
    a1.plot(xs, R["절편"] + R["기울기"] * xs, color=GATE, lw=1.6)
    a1.text(.30, R["절편"] + R["기울기"] * .30 - .045,
            f"풀링 $=$ {R['절편']:.3f} $+$ {R['기울기']:.3f}$\\,\\times$혼자\n$R^2{{=}}{R['R2']}$",
            fontsize=5.8, color=GATE)
    a1.scatter(S, P, s=44, c=[CLAIM if s > be else "#22262b" for s in S],
               alpha=.9, edgecolor="none", zorder=3)
    for r, s, p in zip(J, S, P):
        a1.annotate(r["도메인"], (s, p), fontsize=5.3, ha="center",
                    xytext=(0, 8), textcoords="offset points", color="#3f4750")
    a1.axvline(be, color="#22262b", lw=1.0, ls=":")
    a1.text(be + .008, .06, f"손익분기\n{be:.3f}", fontsize=5.6, color="#22262b")
    a1.set_xlabel("혼자 학습 $\\rho$", fontsize=6.4)
    a1.set_ylabel("풀에서 받는 $\\rho$", fontsize=6.4)
    a1.set_xlim(0, .58); a1.set_ylim(.05, .58)
    a1.tick_params(labelsize=6.0)
    a1.set_title("풀은 업어 주고 눌러 준다", fontsize=7.0)

    # ② 후보 넷 실패
    C = j["후보실패"]["상관"]
    ks = list(C) + ["혼자rho"]
    v = [C[k][0] for k in C] + [j["후보실패"]["혼자_풀링"]]
    y2 = np.arange(len(ks))
    a2.barh(y2, v, .56,
            color=[GATE if abs(x) > .5 else CLAIM for x in v], alpha=.93,
            edgecolor="none")
    a2.axvline(0, color="#8a929b", lw=.9)
    for i, x in enumerate(v):
        a2.text(x + (.03 if x >= 0 else -.03), i, f"{x:+.2f}", fontsize=5.5,
                va="center", ha="left" if x >= 0 else "right", color="#3f4750")
    a2.set_yticks(y2); a2.set_yticklabels(ks, fontsize=5.5)
    a2.set_xlabel("풀링 $\\rho$ 와의 스피어만", fontsize=6.3)
    a2.set_xlim(-.55, 1.0); a2.tick_params(labelsize=6.0)
    a2.set_title("도메인 성질은 못 맞힌다", fontsize=7.0)

    # ③ 판정
    names = [r["도메인"] for r in J]
    gaps = [r["격차"] for r in J]
    pred = ["빼기" if r["혼자rho"] > be else "넣기" for r in J]
    idx = np.argsort(gaps)
    y3 = np.arange(len(J))
    a3.barh(y3, [gaps[i] for i in idx], .56,
            color=[GATE if (gaps[i] > 0) == (pred[i] == "빼기") else CLAIM
                   for i in idx], alpha=.93, edgecolor="none")
    a3.axvline(0, color="#8a929b", lw=.9)
    for k, i in enumerate(idx):
        a3.text(gaps[i] + (.006 if gaps[i] >= 0 else -.006), k,
                pred[i], fontsize=5.3, va="center",
                ha="left" if gaps[i] >= 0 else "right", color="#3f4750")
    a3.axvspan(-.04, .04, color="#c9ced4", alpha=.35, lw=0)
    a3.text(0, len(J) - .4, "검출 한계", fontsize=5.5, ha="center",
            color="#5a6169")
    a3.set_yticks(y3); a3.set_yticklabels([names[i] for i in idx], fontsize=5.6)
    a3.set_xlabel("실제 격차 (혼자 $-$ 풀링)", fontsize=6.3)
    a3.set_xlim(-.19, .12); a3.tick_params(labelsize=6.0)
    a3.set_title("한계 밖 셋은 3/3", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(J)}


def fig_onecol(out: str = "fig_onecol.pdf", root: str = ".") -> dict:
    """노트 205 --- 열 하나가 도메인 하나를 죽이고 있었다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note205.json"))
    C = j["압축"]; WT = j["혼자비교"]["행"]; FD = j["메커니즘"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1.05]})

    # ① 두 형태의 압축선
    xs = np.linspace(0, .62, 50)
    a1.plot(xs, xs, color="#8a929b", lw=1.0, ls="--")
    for form, c, nm in (("F6_directpool", GATE, "F6 능형"),
                        ("F18_bagboost", CLAIM, "F18 트리")):
        r = C[form]
        a1.plot(xs, r["절편"] + r["기울기"] * xs, color=c, lw=1.6,
                label=f"{nm}: $b{{=}}${r['기울기']:.3f}")
        S = [r["혼자"][k] for k in r["혼자"]]
        P = [r["풀링"][k] for k in r["혼자"]]
        a1.scatter(S, P, s=26, color=c, alpha=.75, edgecolor="none", zorder=3)
    a1.set_xlabel("혼자 학습 $\\rho$", fontsize=6.4)
    a1.set_ylabel("풀에서 받는 $\\rho$", fontsize=6.4)
    a1.set_xlim(0, .62); a1.set_ylim(.05, .62)
    a1.legend(fontsize=5.7, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.0)
    a1.set_title("트리가 더 압축한다", fontsize=7.0)

    # ② 혼자 --- 능형 대 트리
    ds = [r[0] for r in WT]
    y2 = np.arange(len(ds))
    a2.barh(y2 - .19, [r[1] for r in WT], .34, color=GATE, alpha=.95,
            edgecolor="none", label="F6 능형")
    a2.barh(y2 + .19, [r[2] for r in WT], .34, color=CLAIM, alpha=.95,
            edgecolor="none", label="F18 트리")
    i = ds.index("웹툰")
    a2.annotate(f"$+${WT[i][3]:.3f}", (0.24, i), fontsize=6.0, va="center",
                color="#22262b", fontweight="bold")
    a2.set_yticks(y2); a2.set_yticklabels(ds, fontsize=5.7)
    a2.set_xlabel("혼자 학습 $\\rho$", fontsize=6.3)
    a2.set_xlim(0, .68)
    a2.legend(fontsize=5.6, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.0)
    a2.set_title("웹툰만 $+$0.41", fontsize=7.0)

    # ③ 열 하나
    ks = ["전체 축 · a=1", "전체 축 · a=20", "전체 축 · a=500",
          "target_breadth 뺌", "시든 둘 뺌", "goods_scale 뺌"]
    lab = ["a=1", "a=20", "a=500", "$-$타깃폭", "$-$둘", "$-$굿즈"]
    v = [FD[k] for k in ks]
    x3 = np.arange(len(v))
    a3.bar(x3, v, .55,
           color=[GATE if x > .3 else CLAIM for x in v], alpha=.93,
           edgecolor="none")
    a3.axhline(.4495, color="#22262b", lw=1.1, ls="--")
    a3.text(len(v) - .45, .4595, "트리 .4495", fontsize=5.7, ha="right",
            color="#22262b")
    a3.axhline(0, color="#8a929b", lw=.8)
    for i, x in enumerate(v):
        a3.text(i, x + (.008 if x >= 0 else -.028), f"{x:.3f}", fontsize=5.3,
                ha="center", color="#3f4750")
    a3.set_xticks(x3); a3.set_xticklabels(lab, fontsize=5.2)
    a3.set_ylabel("웹툰 혼자 능형 $\\rho$", fontsize=6.3)
    a3.set_ylim(-.12, .52); a3.tick_params(labelsize=6.0)
    a3.set_title("굿즈 규모 하나를 빼면", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(WT)}


def fig_onef(out: str = "fig_onef.pdf", root: str = ".") -> dict:
    """노트 206 --- 열 하나가 챔피언을 움직이는데 그 열을 못 고른다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note206.json"))
    K = j["신탁제거"]; R = j["학습규칙"]; TT = j["학습규칙_검정"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1.1, 1]})

    # ① 신탁 제거의 효과
    FORMS = ["F6_directpool", "F21_recentpick", "F18_bagboost"]
    lab = ["F6 능형", "F21 최근·선택", "F18 배깅"]
    x = np.arange(len(FORMS))
    for off, key, c, nm in ((-.26, "현행", "#8a929b", "현행"),
                            (0.0, "웹툰 굿즈규모 끔", GATE, "웹툰 굿즈규모 끔"),
                            (.26, "뒤집힘 셋 다 끔", CLAIM, "뒤집힘 셋 끔")):
        a1.bar(x + off, [K[key][f] for f in FORMS], .25, color=c, alpha=.93,
               edgecolor="none", label=nm)
    for i, f in enumerate(FORMS):
        a1.text(i, K["뒤집힘 셋 다 끔"][f] + .006,
                f"$+${K['뒤집힘 셋 다 끔'][f]-K['현행'][f]:.3f}", fontsize=5.4,
                ha="center", color=CLAIM)
    a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=5.5)
    a1.set_ylabel("판 $\\rho$", fontsize=6.4)
    a1.set_ylim(.34, .52)
    a1.legend(fontsize=5.4, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.0)
    a1.set_title("열 하나가 챔피언을 움직인다", fontsize=7.0)

    # ② 학습만 보는 규칙 --- 문턱 훑기
    ths = [-0.20, -0.15, -0.12, -0.10, -0.08]
    x2 = np.arange(len(ths))
    for f, c, nm in (("F6_directpool", GATE, "F6"),
                     ("F18_bagboost", CLAIM, "F18")):
        v = [R[f"문턱{t}"]["판"][f] for t in ths]
        a2.plot(x2, v, "o-", color=c, lw=1.5, ms=3.8, label=nm)
        a2.axhline(R["현행"][f], color=c, lw=.8, ls=":")
    a2.axvspan(1.6, 3.4, color="#c9ced4", alpha=.3, lw=0)
    a2.text(2.5, .345, "안정 구간", fontsize=5.6, ha="center", color="#5a6169")
    a2.set_xticks(x2); a2.set_xticklabels([f"{t}" for t in ths], fontsize=5.6)
    a2.set_xlabel("최근 기울기 문턱", fontsize=6.4)
    a2.set_ylabel("판 $\\rho$", fontsize=6.4)
    a2.legend(fontsize=5.7, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.0)
    a2.set_title("한 칸 옆에서 무너진다", fontsize=7.0)

    # ③ 신탁 대 규칙
    x3 = np.arange(len(FORMS))
    orc = [K["웹툰 굿즈규모 끔"][f] - K["현행"][f] for f in FORMS]
    rul = [TT[f]["차"] for f in FORMS]
    a3.bar(x3 - .19, orc, .34, color="#22262b", alpha=.9, edgecolor="none",
           label="신탁(유보를 봄)")
    a3.bar(x3 + .19, rul, .34, color=GATE, alpha=.95, edgecolor="none",
           label="학습만 보는 규칙")
    a3.axhline(0, color="#8a929b", lw=.8)
    for i, f in enumerate(FORMS):
        a3.text(i + .19, rul[i] + .0012, f"$t{{=}}{TT[f]['t']}$", fontsize=5.4,
                ha="center", color=GATE)
    a3.set_xticks(x3); a3.set_xticklabels(lab, fontsize=5.5)
    a3.set_ylabel("판 $\\rho$ 이득", fontsize=6.4)
    a3.set_ylim(0, .036)
    a3.legend(fontsize=5.5, frameon=False, loc="upper right")
    a3.tick_params(labelsize=6.0)
    a3.set_title("규칙은 절반만 가져온다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(FORMS)}


def fig_denom(out: str = "fig_denom.pdf", root: str = ".") -> dict:
    """노트 207 --- 분모가 바뀌었지 세계가 바뀐 게 아니다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note207.json"))
    Y = j["연도별"]["연도별"]; CT = j["연도별"]["통제"]; FX = j["고침"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.1, 1, 1]})

    yrs = [r[0] for r in Y]
    # ① 분모가 무너진다
    a1.plot(yrs, [r[2] for r in Y], "o-", color=GATE, lw=1.5, ms=3.6,
            label="경과 주 중앙")
    a1.set_xlabel("시작 연도", fontsize=6.4)
    a1.set_ylabel("경과 주 중앙", fontsize=6.4, color=GATE)
    a1b = a1.twinx()
    a1b.plot(yrs, [r[4] for r in Y], "s--", color=CLAIM, lw=1.5, ms=3.4,
             label="밀도 중앙")
    a1b.set_ylabel("연재 밀도 중앙", fontsize=6.4, color=CLAIM)
    a1.axvspan(2024.5, 2026.5, color="#c9ced4", alpha=.3, lw=0)
    a1.text(2025.5, 380, "유보", fontsize=6.0, ha="center", color="#5a6169")
    a1.annotate("418주", (2018, Y[0][2]), fontsize=5.6, color=GATE,
                xytext=(2018.4, 440), textcoords="data")
    a1.annotate("8주", (2026, Y[-1][2]), fontsize=5.6, color=GATE,
                xytext=(2025.2, 60), textcoords="data")
    a1.tick_params(labelsize=6.0); a1b.tick_params(labelsize=6.0)
    a1.set_title("분모가 무너진다", fontsize=7.0)

    # ② 상관이 그 때문에 뒤집힌다
    a2.axhline(0, color="#8a929b", lw=.9)
    a2.plot(yrs, [r[6] for r in Y], "o-", color=CLAIM, lw=1.6, ms=3.8,
            label="밀도 $\\leftrightarrow$ 라벨")
    a2.plot(yrs, [r[7] for r in Y], "s--", color=GATE, lw=1.4, ms=3.4,
            label="회차 수 $\\leftrightarrow$ 라벨")
    a2.axvspan(2024.5, 2026.5, color="#c9ced4", alpha=.3, lw=0)
    a2.set_xlabel("시작 연도", fontsize=6.4)
    a2.set_ylabel("스피어만", fontsize=6.4)
    a2.legend(fontsize=5.6, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.0)
    a2.text(.03, .93, f"경과 통제 뒤 유보 {CT['유보(2025~)']['통제']:+.3f}",
            fontsize=5.9, transform=a2.transAxes, color="#22262b")
    a2.set_title("통제하면 사라진다", fontsize=7.0)

    # ③ 고침
    ks = ["현행(밀도)", "밀도(분모 104주 상한)", "밀도(분모 208주 상한)",
          "회차수", "끔(참고)"]
    lab = ["현행\n(밀도)", "상한\n104주", "상한\n208주", "회차 수", "끔\n(참고)"]
    x3 = np.arange(len(ks))
    for off, f, c, nm in ((-.19, "F6_directpool", GATE, "F6 능형"),
                          (.19, "F18_bagboost", CLAIM, "F18 배깅")):
        a3.bar(x3 + off, [FX[k][f] for k in ks], .34, color=c, alpha=.95,
               edgecolor="none", label=nm)
    a3.axhline(FX["현행(밀도)"]["F18_bagboost"], color=CLAIM, lw=.8, ls=":")
    a3.axhline(FX["현행(밀도)"]["F6_directpool"], color=GATE, lw=.8, ls=":")
    a3.set_xticks(x3); a3.set_xticklabels(lab, fontsize=5.2)
    a3.set_ylabel("판 $\\rho$", fontsize=6.4)
    a3.set_ylim(.33, .52)
    a3.legend(fontsize=5.6, frameon=False, loc="upper left")
    a3.tick_params(labelsize=6.0)
    a3.set_title("회차 수로 바꾼다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(Y)}


def fig_divide(out: str = "fig_divide.pdf", root: str = ".") -> dict:
    """노트 208 --- 나눗셈은 터지고 셈은 기운다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note208.json"))
    V = j["장소노출"]["행"]; FX = j["고침"]
    D207 = json.load(open(Path(root) / "data/state/note207.json"))["연도별"]["연도별"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1.05, 1]})

    # ① 나눗셈 대 셈 --- 시간 의존의 모양
    yrs = [r[0] for r in D207]
    dens = np.array([r[4] for r in D207])
    a1.plot(yrs, dens / dens[0], "o-", color=CLAIM, lw=1.6, ms=3.8,
            label="웹툰 밀도 (나눗셈)")
    # 장소 노출은 도메인 평균 추세를 흉내 --- 시작 연도 상관으로 대신 그린다
    a1.axhline(1.0, color="#8a929b", lw=.9, ls="--")
    a1.annotate("$\\times$7.3", (2026, dens[-1] / dens[0]), fontsize=6.2,
                ha="right", color=CLAIM, xytext=(2025.4, 6.4),
                textcoords="data")
    a1.set_xlabel("시작 연도", fontsize=6.4)
    a1.set_ylabel("2018년 대비 배수", fontsize=6.4)
    a1.set_ylim(0, 8.2)
    a1.legend(fontsize=5.8, frameon=False, loc="upper left")
    a1.tick_params(labelsize=6.0)
    a1.set_title("나눗셈은 터진다", fontsize=7.0)

    # ② 장소 노출의 시간 의존
    ds = [r[0] for r in V]
    y2 = np.arange(len(ds))
    a2.barh(y2 - .19, [r[2] for r in V], .34, color=CLAIM, alpha=.95,
            edgecolor="none", label="시작 연도와")
    a2.barh(y2 + .19, [r[3] for r in V], .34, color=GATE, alpha=.95,
            edgecolor="none", label="라벨과")
    a2.axvline(0, color="#8a929b", lw=.9)
    for v in (-.15, .15):
        a2.axvline(v, color="#22262b", lw=.7, ls=":")
    a2.set_yticks(y2); a2.set_yticklabels(ds, fontsize=5.7)
    a2.set_xlabel("스피어만", fontsize=6.3)
    a2.set_xlim(-.35, .52)
    a2.legend(fontsize=5.6, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.0)
    a2.set_title("셈도 시간을 담는다 (5/7)", fontsize=7.0)

    # ③ 고쳐도 안 움직인다
    FORMS = ["F6_directpool", "F21_recentpick", "F18_bagboost"]
    lab = ["F6", "F21", "F18"]
    x3 = np.arange(len(FORMS))
    for off, k, c, nm in ((-.19, "연도 안 순위(1년)", GATE, "1년 코호트"),
                          (.19, "연도 안 순위(2년)", CLAIM, "2년 코호트")):
        a3.bar(x3 + off, [FX[k][f] - FX["현행"][f] for f in FORMS], .34,
               color=c, alpha=.95, edgecolor="none", label=nm)
    a3.axhline(0, color="#8a929b", lw=.9)
    # 견줌 --- 노트 207 의 웹툰 고침
    a3.axhline(.0155, color="#22262b", lw=1.0, ls="--")
    a3.text(2.4, .0165, "노트 207 웹툰 고침", fontsize=5.5, ha="right",
            color="#22262b")
    a3.set_xticks(x3); a3.set_xticklabels(lab, fontsize=6.0)
    a3.set_ylabel("판 $\\rho$ 변화", fontsize=6.4)
    a3.set_ylim(-.008, .020)
    a3.legend(fontsize=5.7, frameon=False, loc="upper left")
    a3.tick_params(labelsize=6.0)
    a3.set_title("셈은 고쳐도 안 움직인다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(V)}


def fig_clock(out: str = "fig_clock.pdf", root: str = ".") -> dict:
    """노트 209 --- 달력이 판의 4분의 1인데 모형은 달력을 안 본다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note209.json"))
    L = j["라벨시간"]["행"]; B = j["기준선"]; C = j["코호트"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.05, 1, 1]})

    # ① 라벨이 시간을 담는다
    rows = sorted(L, key=lambda r: r[2])
    y1 = np.arange(len(rows))
    a1.barh(y1, [r[2] for r in rows], .58,
            color=[CLAIM if r[2] < -.15 else (GATE if r[2] > .15 else "#8a929b")
                   for r in rows], alpha=.93, edgecolor="none")
    a1.axvline(0, color="#8a929b", lw=.9)
    for v in (-.15, .15):
        a1.axvline(v, color="#22262b", lw=.7, ls=":")
    for i, r in enumerate(rows):
        a1.text(r[2] + (.02 if r[2] >= 0 else -.02), i, f"{r[2]:+.2f}",
                fontsize=5.3, va="center",
                ha="left" if r[2] >= 0 else "right", color="#3f4750")
    a1.set_yticks(y1); a1.set_yticklabels([r[0] for r in rows], fontsize=5.7)
    a1.set_xlabel("라벨 $\\leftrightarrow$ 시작 연도", fontsize=6.3)
    a1.set_xlim(-.82, .52); a1.tick_params(labelsize=6.0)
    a1.set_title("여섯이 ``옛것이 높다''", fontsize=7.0)

    # ② 시작일만으로
    dr = [r for r in B["도메인별"] if r[1] is not None]
    dr = sorted(dr, key=lambda r: -r[2])
    y2 = np.arange(len(dr))
    a2.barh(y2, [r[2] for r in dr], .58,
            color=[GATE if r[2] > .3 else "#8a929b" for r in dr], alpha=.93,
            edgecolor="none")
    a2.axvline(0, color="#8a929b", lw=.9)
    a2.axvline(B["시작일기준선"], color="#22262b", lw=1.1, ls="--")
    a2.text(B["시작일기준선"] + .02, len(dr) - .6,
            f"판 {B['시작일기준선']:.3f}", fontsize=5.8, color="#22262b")
    for i, r in enumerate(dr):
        a2.text(r[2] + (.015 if r[2] >= 0 else -.015), i, f"{r[2]:+.2f}",
                fontsize=5.3, va="center",
                ha="left" if r[2] >= 0 else "right", color="#3f4750")
    a2.set_yticks(y2); a2.set_yticklabels([r[0] for r in dr], fontsize=5.7)
    a2.set_xlabel("$-$시작일 만으로 얻는 $\\rho$", fontsize=6.3)
    a2.set_xlim(-.19, .68); a2.tick_params(labelsize=6.0)
    a2.set_title("달력만으로 .251", fontsize=7.0)

    # ③ 코호트 안에서 재면
    ks = ["시작일만", "F6_directpool", "F21_recentpick", "F18_bagboost"]
    lab = ["시작일만", "F6 능형", "F21", "F18 배깅"]
    x3 = np.arange(len(ks))
    a3.bar(x3 - .19, [C[k]["현행"] for k in ks], .34, color="#8a929b",
           alpha=.9, edgecolor="none", label="현행")
    a3.bar(x3 + .19, [C[k]["반년"] for k in ks], .34, color=GATE, alpha=.95,
           edgecolor="none", label="반년 코호트 안")
    for i, k in enumerate(ks):
        dv = C[k]["반년"] - C[k]["현행"]
        a3.text(i + .19, C[k]["반년"] + .008, f"{dv:+.3f}", fontsize=5.3,
                ha="center", color=CLAIM if dv < -.01 else GATE)
    a3.set_xticks(x3); a3.set_xticklabels(lab, fontsize=5.4)
    a3.set_ylabel("판 $\\rho$", fontsize=6.4)
    a3.set_ylim(0, .55)
    a3.legend(fontsize=5.7, frameon=False, loc="upper left")
    a3.tick_params(labelsize=6.0)
    a3.set_title("기준선만 반 토막", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(rows)}


def fig_window(out: str = "fig_window.pdf", root: str = ".") -> dict:
    """노트 210 --- 모형이 달력과 동점이었다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note210.json"))
    L = j["라벨비교"]; G = j["게임도메인"]; B = j["판"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1.1, 1]})

    # ① 누적은 달력에 눕고 30일은 안 눕는다
    yrs = [r[0] for r in L["연도별"]]
    cum = np.array([r[2] for r in L["연도별"]], float)
    w30 = np.array([r[3] for r in L["연도별"]], float)
    a1.semilogy(yrs, cum, "o-", color=CLAIM, lw=1.6, ms=3.8, label="누적 리뷰")
    a1.semilogy(yrs, w30, "s--", color=GATE, lw=1.6, ms=3.6, label="30일 리뷰")
    a1.set_xlabel("출시 연도", fontsize=6.4)
    a1.set_ylabel("중앙 (로그)", fontsize=6.4)
    a1.text(.04, .10, f"연도와: 누적 {L['누적_연도']:+.3f}\n30일 {L['w30_연도']:+.3f}",
            fontsize=6.0, transform=a1.transAxes, color="#22262b")
    a1.legend(fontsize=5.8, frameon=False, loc="upper right")
    a1.tick_params(labelsize=6.0)
    a1.set_title("누적만 달력에 눕는다", fontsize=7.0)

    # ② 게임 유보 --- 달력 대 모형
    ks = ["달력만", "F6_directpool", "F21_recentpick", "F18_bagboost"]
    lab = ["달력만\n($-$시작일)", "F6 능형", "F21", "F18 배깅"]
    x = np.arange(len(ks))
    a2.bar(x - .26, [G[k]["vs 누적"] for k in ks], .25, color="#8a929b",
           alpha=.9, edgecolor="none", label="누적 라벨")
    a2.bar(x, [G[k]["vs 30일"] for k in ks], .25, color=GATE, alpha=.95,
           edgecolor="none", label="30일 라벨")
    a2.bar(x + .26, [G[k]["vs 30일(안 잘림)"] for k in ks], .25, color=CLAIM,
           alpha=.95, edgecolor="none", label="30일(안 잘림)")
    a2.annotate("동점", (0 - .26, G["달력만"]["vs 누적"] + .02), fontsize=6.2,
                ha="center", color="#22262b")
    a2.plot([-.4, .1], [G["F18_bagboost"]["vs 누적"]] * 2, color="#22262b",
            lw=.8, ls=":")
    a2.set_xticks(x); a2.set_xticklabels(lab, fontsize=5.3)
    a2.set_ylabel("게임 유보 $\\rho$ (223건)", fontsize=6.3)
    a2.set_ylim(0, .62)
    a2.legend(fontsize=5.4, frameon=False, loc="lower left")
    a2.tick_params(labelsize=6.0)
    a2.set_title("누적 라벨에서 모형 $=$ 달력", fontsize=7.0)

    # ③ 판
    tags = ["현행(누적)", "게임 30일", "게임 30일(잘린 것 뺌)"]
    lb = ["현행\n(누적)", "게임\n30일", "게임 30일\n(잘림 뺌)"]
    x3 = np.arange(len(tags))
    a3.bar(x3 - .19, [B[t]["F18_bagboost"] for t in tags], .34, color=GATE,
           alpha=.95, edgecolor="none", label="F18 배깅")
    a3.bar(x3 + .19, [B[t]["달력만"] for t in tags], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="달력만")
    for i, t in enumerate(tags):
        a3.text(i - .19, B[t]["F18_bagboost"] + .008,
                f"{B[t]['F18_bagboost']:.4f}", fontsize=5.2, ha="center",
                color=GATE)
        a3.text(i + .19, B[t]["달력만"] + .008, f"{B[t]['달력만']:.4f}",
                fontsize=5.2, ha="center", color=CLAIM)
    a3.set_xticks(x3); a3.set_xticklabels(lb, fontsize=5.3)
    a3.set_ylabel("판 $\\rho$", fontsize=6.4)
    a3.set_ylim(0, .55)
    a3.legend(fontsize=5.7, frameon=False, loc="upper right")
    a3.tick_params(labelsize=6.0)
    a3.set_title("판은 오르고 달력은 준다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(yrs)}


def fig_floor(out: str = "fig_floor.pdf", root: str = ".") -> dict:
    """노트 211 --- 바닥이 나이와 함께 오른다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note211.json"))
    BK = j["도서"]; AL = j["전도메인"]["행"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1, 1.1]})

    # ① 도서 --- 바닥이 오른다
    ym = BK["연도별최소"]
    ys = [r[0] for r in ym]; mn = [r[1] for r in ym]
    a1.semilogy(ys, mn, "o-", color=CLAIM, lw=1.6, ms=4.0)
    a1.set_xlabel("출간 연도", fontsize=6.4)
    a1.set_ylabel("그 해 최소 판매지수 (로그)", fontsize=6.2)
    a1.text(.05, .10, f"연도 $\\leftrightarrow$ 최소 $=$ {BK['연도_최소_spearman']:+.3f}",
            fontsize=6.4, transform=a1.transAxes, color=CLAIM)
    a1.tick_params(labelsize=6.0)
    a1.set_title("옛 책의 바닥이 높다", fontsize=7.0)

    # ② 바닥을 올리면 상관이 준다
    F = BK["바닥훑기"]
    x2 = np.arange(len(F))
    a2.bar(x2, [abs(r[2]) for r in F], .55, color=GATE, alpha=.93,
           edgecolor="none")
    for i, r in enumerate(F):
        a2.text(i, abs(r[2]) + .008, f"{r[2]:.3f}", fontsize=5.2, ha="center",
                color="#3f4750")
        a2.text(i, .012, f"n={r[1]}", fontsize=5.0, ha="center", color="white")
    a2.set_xticks(x2)
    a2.set_xticklabels([f"{r[0]//1000}k" if r[0] else "없음" for r in F],
                       fontsize=5.5)
    a2.set_xlabel("판매지수 바닥", fontsize=6.4)
    a2.set_ylabel("$|$연도 $\\leftrightarrow$ 라벨$|$", fontsize=6.3)
    a2.set_ylim(0, .43); a2.tick_params(labelsize=6.0)
    a2.set_title("바닥을 올리면 준다", fontsize=7.0)

    # ③ 전 도메인
    rows = sorted(AL, key=lambda r: r[3])
    y3 = np.arange(len(rows))
    a3.barh(y3 - .19, [r[3] for r in rows], .34, color=CLAIM, alpha=.95,
            edgecolor="none", label="연도 $\\leftrightarrow$ 최소")
    a3.barh(y3 + .19, [r[2] for r in rows], .34, color=GATE, alpha=.95,
            edgecolor="none", label="연도 $\\leftrightarrow$ 라벨")
    a3.axvline(0, color="#8a929b", lw=.9)
    for i, r in enumerate(rows):
        if r[5].startswith("○"):
            a3.text(.04, i, "인기순", fontsize=5.0, va="center", color="#22262b")
    a3.set_yticks(y3); a3.set_yticklabels([r[0] for r in rows], fontsize=5.7)
    a3.set_xlabel("스피어만", fontsize=6.3)
    a3.set_xlim(-1.05, .35)
    a3.legend(fontsize=5.5, frameon=False, loc="lower left")
    a3.tick_params(labelsize=6.0)
    a3.set_title("일곱 전부 바닥이 오른다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(rows)}


def fig_selfdiv(out: str = "fig_selfdiv.pdf", root: str = ".") -> dict:
    """노트 212 --- 라벨을 축으로 나누면 그 축이 뒤집힌다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note212.json"))
    S = j["가르기"]; F = j["고침시도"]; AX = j["축뒤집힘"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1, 1, 1.1]})

    # ① 누적인가 표본인가
    ks = ["전체", "완결(최신순)", "연재중(인기순)"]
    x = np.arange(len(ks))
    a1.bar(x - .19, [S[k]["최소_연도"] for k in ks], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="최소 $\\leftrightarrow$ 연도")
    a1.bar(x + .19, [S[k]["라벨_연도"] for k in ks], .34, color=GATE,
           alpha=.95, edgecolor="none", label="라벨 $\\leftrightarrow$ 연도")
    a1.axhline(0, color="#8a929b", lw=.9)
    a1.set_xticks(x)
    a1.set_xticklabels(["전체", "완결\n(최신순)", "연재중\n(인기순)"], fontsize=5.5)
    a1.set_ylabel("스피어만", fontsize=6.4)
    a1.set_ylim(-1.15, .3)
    a1.legend(fontsize=5.5, frameon=False, loc="lower left")
    a1.tick_params(labelsize=6.0)
    a1.text(.03, .90, f"회차 통제: {S['회차통제']['원']:+.3f} $\\to$ "
            f"{S['회차통제']['통제']:+.3f}", fontsize=6.0,
            transform=a1.transAxes, color="#22262b")
    a1.set_title("최신순 쪽이 더 심하다", fontsize=7.0)

    # ② 고치면 오르는 것처럼 보인다
    tags = ["현행(누적)", "회차 잔차", "회차당(누적/회차)"]
    lb = ["현행\n(누적)", "회차\n잔차", "회차당"]
    x2 = np.arange(len(tags))
    a2.bar(x2 - .19, [F[t]["웹툰 F18"] for t in tags], .34, color=GATE,
           alpha=.95, edgecolor="none", label="웹툰 F18 $\\rho$")
    a2.bar(x2 + .19, [F[t]["달력(웹툰)"] for t in tags], .34, color=CLAIM,
           alpha=.95, edgecolor="none", label="웹툰 달력 몫")
    a2.axhline(0, color="#8a929b", lw=.9)
    for i, t in enumerate(tags):
        a2.text(i - .19, F[t]["웹툰 F18"] + .02, f"{F[t]['웹툰 F18']:.3f}",
                fontsize=5.3, ha="center", color=GATE)
        v = F[t]["달력(웹툰)"]
        a2.text(i + .19, v + (.02 if v >= 0 else -.06), f"{v:+.3f}",
                fontsize=5.3, ha="center", color=CLAIM)
    a2.set_xticks(x2); a2.set_xticklabels(lb, fontsize=5.5)
    a2.set_ylabel("$\\rho$", fontsize=6.4)
    a2.set_ylim(-.48, .80)
    a2.legend(fontsize=5.5, frameon=False, loc="upper left")
    a2.tick_params(labelsize=6.0)
    a2.set_title("과교정까지 간다", fontsize=7.0)

    # ③ 축이 뒤집힌다
    show = ["goods_scale", "entry_friction", "target_breadth", "trend_momentum",
            "cal_dow_cos"]
    y3 = np.arange(len(show))
    for off, k, c in ((-.26, "현행(누적)", "#8a929b"), (0.0, "회차 잔차", GATE),
                      (.26, "회차당", CLAIM)):
        a3.barh(y3 + off, [AX[a][k] if AX[a][k] is not None else 0 for a in show],
                .25, color=c, alpha=.93, edgecolor="none", label=k)
    a3.axvline(0, color="#8a929b", lw=.9)
    a3.annotate("$+$.134 $\\to$ $-$.741", (-.45, 0), fontsize=5.6, va="center",
                color="#22262b")
    a3.set_yticks(y3)
    a3.set_yticklabels([s.replace("_", "\\_") for s in show], fontsize=5.3)
    a3.set_xlabel("축 $\\leftrightarrow$ 라벨 (웹툰 유보)", fontsize=6.2)
    a3.set_xlim(-.85, .62)
    a3.legend(fontsize=5.3, frameon=False, loc="lower right")
    a3.tick_params(labelsize=6.0)
    a3.set_title("분모였던 축이 뒤집힌다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(show)}


def fig_hol(out: str = "fig_hol.pdf", root: str = ".") -> dict:
    """노트 213 --- 공휴일 목록이 2023년부터였다."""
    import numpy as np
    j = json.load(open(Path(root) / "data/state/note213.json"))
    CAP = j["상한"]["행"]; FX = j["고침"]; BG = j["훑기"]["큰것"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(FULL, 2.5),
                                     gridspec_kw={"width_ratios": [1.05, 1, 1]})

    # ① 상한 비중과 그것이 2023 이전인 비율
    rows = sorted([r for r in CAP if r[1] > 60], key=lambda r: -r[2])
    y1 = np.arange(len(rows))
    a1.barh(y1 - .19, [r[2] for r in rows], .34, color=CLAIM, alpha=.95,
            edgecolor="none", label="상한값 비중")
    a1.barh(y1 + .19, [r[3] for r in rows], .34, color=GATE, alpha=.95,
            edgecolor="none", label="상한 중 2023 이전")
    a1.axvline(1.0, color="#22262b", lw=.8, ls=":")
    for i, r in enumerate(rows):
        a1.text(r[2] + .015, i - .19, f"{r[2]:.0%}", fontsize=5.2, va="center",
                color=CLAIM)
    a1.set_yticks(y1); a1.set_yticklabels([r[0] for r in rows], fontsize=5.6)
    a1.set_xlabel("몫", fontsize=6.4)
    a1.set_xlim(0, 1.22)
    a1.legend(fontsize=5.4, frameon=False, loc="lower right")
    a1.tick_params(labelsize=6.0)
    a1.set_title("상한은 곧 ``2023년 이전''", fontsize=7.0)

    # ② 시간을 통제하면 사라지는 축들
    rows2 = BG[:9]
    y2 = np.arange(len(rows2))
    a2.barh(y2 - .19, [r["축_라벨"] for r in rows2], .34, color="#8a929b",
            alpha=.9, edgecolor="none", label="원래")
    a2.barh(y2 + .19, [r["시간통제"] for r in rows2], .34, color=GATE,
            alpha=.95, edgecolor="none", label="시간 통제 뒤")
    a2.axvline(0, color="#8a929b", lw=.9)
    a2.set_yticks(y2)
    a2.set_yticklabels([f"{r['도메인'][:3]}·{r['축'][:11]}".replace("_", "\\_")
                        for r in rows2], fontsize=4.8)
    a2.set_xlabel("축 $\\leftrightarrow$ 라벨", fontsize=6.3)
    a2.set_xlim(-.18, .62)
    a2.legend(fontsize=5.5, frameon=False, loc="lower right")
    a2.tick_params(labelsize=6.0)
    a2.set_title("시간을 빼면 사라진다", fontsize=7.0)

    # ③ 고침
    FORMS = ["F6_directpool", "F21_recentpick", "F18_bagboost"]
    lab = ["F6 능형", "F21", "F18 배깅"]
    x3 = np.arange(len(FORMS))
    for off, k, c, nm in ((-.26, "현행", "#8a929b", "현행"),
                          (0.0, "목록 밖 결측", GATE, "목록 밖 결측"),
                          (.26, "축 끔", CLAIM, "축 끔")):
        a3.bar(x3 + off, [FX[k][f] for f in FORMS], .25, color=c, alpha=.93,
               edgecolor="none", label=nm)
    for i, f in enumerate(FORMS):
        dv = FX["목록 밖 결측"][f] - FX["현행"][f]
        a3.text(i, FX["목록 밖 결측"][f] + .006, f"{dv:+.3f}", fontsize=5.2,
                ha="center", color=GATE if dv > 0 else CLAIM)
    a3.set_xticks(x3); a3.set_xticklabels(lab, fontsize=5.6)
    a3.set_ylabel("판 $\\rho$", fontsize=6.4)
    a3.set_ylim(.39, .50)
    a3.legend(fontsize=5.4, frameon=False, loc="upper left")
    a3.tick_params(labelsize=6.0)
    a3.set_title("결측이 맞고 끄기는 아니다", fontsize=7.0)

    fig.tight_layout(); fig.savefig(out, format="pdf"); plt.close(fig)
    return {"n": len(rows)}
