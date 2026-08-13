# -*- coding: utf-8 -*-
"""노트 961 [판정] — 🔴 **부호를 n 의 함수로 잰다. 판정을 그 곡선 위에 세운다.**

사전등록 `docs/prereg_961_curve.md`(커밋 `a19103fde` · **측정 전** · 파일 하나).

**왜 이 러너가 있나.** 957·티처 #96 은 **n=464** 에서 `Δρ₃|₁₊지시자 = −0.007687` 을 보고
「층 ③ 은 도메인 이름표의 대리변수다」라 했고, 960 은 **n=2,050** 에서 `+0.007112` 를 보고
「대리변수가 아니었다」라 했다. 🔴 **여유는 각각 1.172배와 1.166배 — 같은 자리다.**
티처 #99 가 **배경 풀을 3,896 으로 고정한 채 n 만 흔드니 부호가 매끄럽게 넘어갔다.**

🔴 **그러면 두 「결론」은 한 곡선 위의 두 점이고, 결론은 곡선이지 점이 아니다.**

**이 러너가 하는 것.**

  §5  배선 13검사 — 🔴 **하드코딩 없음.** `W0` 가 맨 앞이고 **호출 인자까지** 본다.
      그리고 **다섯 검사에 나쁜 값을 심어 정말 떨어지는지** 스스로 시험한다.
  §6  두 팔의 곡선 — 배경 3,896 고정 · **구성도 고정** · 씨앗 30 · n 격자 8+12
  §6′ 닻 셋(실제 941 표 · 만화 제외 1,983 · 전량 2,050) — **곡선이 아니다. 분모가 다르다**
  §7  평평함의 자(F = CARD_T) · 포화 적합 · 영교차 · 못 가르는 띠
  §8  `lab.adopt.adopt`(3값) 와 `lab.adopt.rulers`(자 사이 포함관계)를 **실제로 부르고 키로 낸다**

🔴 **새 자료 0 · HTTP 0 · 판 라벨 0비트.**

    python3 runners/curve961.py            # 전량 — runners/out961_curve.json
    python3 runners/curve961.py --part …   # 🔴 부분 주행은 **다른 파일**에 쓴다(R6)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))

import numpy as np                                              # noqa: E402
from scipy.stats import spearmanr                               # noqa: E402

import runners.layers957 as L                                   # noqa: E402
from runners.grow959 import build_arms_fast, OUTDIR, PAIRDIR    # noqa: E402
from lab.adopt import adopt, rulers, band                       # noqa: E402

PREREG = ROOT / "docs/prereg_961_curve.md"
OUT = ROOT / "runners/out961_curve.json"

# ── 🔴 이 러너의 상수. **§5 W0 이 사전등록 파일과 기계로 대조한다.** ──────────
BOOT = 4000
BOOT_SEED = 7
SUB_SEEDS = 30
FLAT_F = 0.00353
PERM_COL = 200
NGRID_A = (300, 350, 400, 464, 550, 651, 750, 851)
NGRID_B = (300, 400, 464, 600, 800, 1000, 1200, 1400, 1600, 1800, 1983, 2050)
PAIRS941 = ROOT / "data/ingest/sao941/pairs.jsonl.gz"

# 🔴 R5 — **모든 부트 호출의 `요청` 을 여기 적는다.** W0-나 가 이것을 감사한다.
BOOT_CALLS: list[dict] = []


# ── R6 부분 주행 가드 ───────────────────────────────────────────────────────
def resolve_out(part: str | None) -> Path:
    """🔴 **부분 주행은 전량 산출물을 못 덮는다**(959·960 에서 두 번 났다).

    `--part` 를 주면 반드시 `out961_curve.<이름>.part.json` 으로 간다.
    """
    if not part:
        return OUT
    p = OUT.with_name(f"{OUT.stem}.{re.sub(r'[^0-9A-Za-z_-]', '_', part)}.part.json")
    if p.resolve() == OUT.resolve():
        raise SystemExit("🔴 부분 주행이 전량 산출물을 덮으려 했다 — 멈춘다")
    return p


# ── 자 ──────────────────────────────────────────────────────────────────────
def boot_se(Pa, Pb, y, clus, reps: int = BOOT, seed: int = BOOT_SEED, *,
            why: str = "") -> dict:
    """짝지은 차의 군집 부트.

    🔴 **R5 — 호출 자리에서 `reps` 를 낮추면 여기서 멈춘다.**
    티처 #99 C6 이 `BOOT` 를 그대로 두고 호출 자리에 `reps=400` 을 심어 960 의 `W0` 를 통과시켰다.
    """
    if reps != BOOT:
        raise SystemExit(f"🔴 부트 요청이 등록값과 다르다: {reps} != {BOOT} ({why}) — 멈춘다")
    rng = np.random.RandomState(seed)
    cs = np.unique(clus)
    idx = {c: np.where(clus == c)[0] for c in cs}
    d, skip = [], 0
    for _ in range(reps):
        pick = rng.choice(len(cs), len(cs), replace=True)
        ii = np.concatenate([idx[cs[j]] for j in pick])
        if len(np.unique(y[ii])) < 3:
            skip += 1
            continue
        ra = float(spearmanr(Pa[ii], y[ii]).statistic)
        rb = float(spearmanr(Pb[ii], y[ii]).statistic)
        if math.isnan(ra) or math.isnan(rb):
            skip += 1
            continue
        d.append(rb - ra)
    a = np.asarray(d)
    rec = {"군집 수": int(len(cs)), "재표집 성공": int(len(a)), "요청": reps,
           "버린 것": int(skip), "W7 성공+버린것==요청": int(len(a)) + skip == reps,
           "SE": float(a.std()), "평균 Δρ": float(a.mean()),
           "🔴 MC 오차 ≈ SE/√reps": float(a.std() / math.sqrt(max(len(a), 1)))}
    BOOT_CALLS.append({"왜": why, "요청": reps, "군집 수": rec["군집 수"], "씨앗": seed})
    return rec


def T_of(se: float) -> float:
    return max(L.CARD_T, 2.0 * se)


# ── §5 W0 ──────────────────────────────────────────────────────────────────
def read_prereg_const() -> dict:
    txt = PREREG.read_text()
    m = re.search(r"<!--\s*PREREG-CONST\s*(.*?)-->", txt, re.S)
    if not m:
        raise SystemExit("🔴 사전등록에 PREREG-CONST 블록이 없다 — 멈춘다")
    out = {}
    for line in m.group(1).strip().splitlines():
        line = line.strip()
        if line and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def code_consts(measured: dict, boot_override: int | None = None) -> dict:
    return {
        "BOOT": BOOT if boot_override is None else boot_override,
        "BOOT_SEED": BOOT_SEED, "SUB_SEEDS": SUB_SEEDS, "FLAT_F": FLAT_F,
        "PERM_COL": PERM_COL, "SEEDS": len(L.SEEDS), "KFOLD": L.KFOLD,
        "WIN": L.WIN, "LIFT_POST": L.LIFT_POST, "BG_MIN": L.BG_MIN,
        "BG_GAP": L.BG_GAP, "CARD_T": L.CARD_T,
        "NGRID_A": ",".join(str(x) for x in NGRID_A),
        "NGRID_B": ",".join(str(x) for x in NGRID_B),
        **measured,
    }


def w0_const_check(pc: dict, code: dict) -> dict:
    rows, bad = {}, []
    for k, want in pc.items():
        got = code.get(k, "🔴 코드에 없다")
        try:
            if isinstance(got, float):
                same = abs(got - float(want)) <= 1e-12
            elif isinstance(got, bool):
                same = str(got) == want
            elif isinstance(got, int):
                same = got == int(want)
            else:
                same = str(got) == want
        except ValueError:
            same = False
        rows[k] = {"사전등록": want, "코드/실측": got, "같나": bool(same)}
        if not same:
            bad.append(k)
    return {"🔴 무엇": "사전등록 `PREREG-CONST` ↔ 코드 상수·실측값 기계 대조",
            "분자: 같은 값": len(rows) - len(bad), "분모: 등록된 상수": len(rows),
            "어긋난 것": bad, "표": rows, "통과": not bad}


def w0_call_audit(calls: list, want: int, want_key: str) -> dict:
    """🔴 **W0-나 — 상수가 아니라 「실제로 몇 번 요청했나」를 본다**(티처 #99 C6)."""
    reqs = sorted({c["요청"] for c in calls})
    ok = bool(calls) and reqs == [want]
    return {"🔴 무엇": ("모듈 상수가 아니라 **모든 부트 호출의 `요청` 인자**를 감사한다. "
                     "티처 #99 가 `BOOT` 는 그대로 두고 호출 자리에 `reps=400` 을 심어 960 의 W0 를 통과시켰다"),
            "분자: 등록값으로 요청한 호출": sum(1 for c in calls if c["요청"] == want),
            "분모: 부트 호출": len(calls),
            "본 요청값": reqs, "사전등록 " + want_key: want, "통과": ok}


# ── 표집 ────────────────────────────────────────────────────────────────────
def strat_index(dom: np.ndarray, comp: dict, n: int, seed: int) -> np.ndarray:
    """🔴 **구성 고정 부분표집** — 도메인 비율을 `comp` 에 맞춰 비복원으로 뽑는다."""
    rng = np.random.RandomState(seed)
    tot = sum(comp.values())
    out = []
    for d, c in sorted(comp.items()):
        want = int(round(n * c / tot))
        pool = np.where(dom == d)[0]
        if want <= 0 or len(pool) == 0:
            continue
        if want > len(pool):
            raise SystemExit(f"🔴 {d} 에서 {want} 를 못 뽑는다(있는 것 {len(pool)}) — 멈춘다")
        out.extend(rng.choice(pool, want, replace=False).tolist())
    return np.asarray(sorted(out))


def one_point(rows, y, g, dom_all, idx) -> dict:
    """한 부분표본의 Δρ = ρ(①+지시자+③) − ρ(①+지시자). **지시자 열 목록은 팔마다 고정**이다."""
    sub = [rows[i] for i in idx]
    for r in sub:
        r["xd"] = [1.0 if r["도메인"] == d else 0.0 for d in dom_all]
    Xb = L.mat(sub, "x1", "xd")
    Xp = L.mat(sub, "x1", "xd", "x3")
    yy, gg = y[idx], g[idx]
    ra, _, Pa = L.rho_of(Xb, yy, gg)
    rb, _, Pb = L.rho_of(Xp, yy, gg)
    zero_cols = int(sum(1 for j in range(1, Xb.shape[1]) if np.allclose(Xb[:, j], 0)))
    return {"n": int(len(idx)), "Δρ": rb - ra, "ρ(①+지시자)": ra, "ρ(①+지시자+③)": rb,
            "빈 지시자 열": zero_cols, "Pa": Pa, "Pb": Pb, "idx": idx}


def ladder(rows, y, g, dom, comp, grid, dom_all, tag: str) -> dict:
    """한 팔의 사다리 — n 마다 씨앗 30개의 Δρ 와, 씨앗 0 표본 위의 부트 T 둘."""
    steps = {}
    for n in grid:
        ds, ns, zc = [], [], []
        p0 = None
        for s in range(SUB_SEEDS):
            idx = strat_index(dom, comp, n, seed=1000 * s + n)
            pt = one_point(rows, y, g, dom_all, idx)
            ds.append(pt["Δρ"])
            ns.append(pt["n"])
            zc.append(pt["빈 지시자 열"])
            if s == 0:
                p0 = pt
        a = np.asarray(ds)
        n_act = int(np.mean(ns))
        ent0 = g[p0["idx"]]
        dom0 = dom[p0["idx"]]
        b_ent = boot_se(p0["Pa"], p0["Pb"], y[p0["idx"]], ent0, why=f"{tag} n={n} 개체")
        b_dom = boot_se(p0["Pa"], p0["Pb"], y[p0["idx"]], dom0, why=f"{tag} n={n} 도메인")
        T_e, T_d = T_of(b_ent["SE"]), T_of(b_dom["SE"])
        steps[str(n)] = {
            "목표 n": n, "🔴 실제 n": n_act, "실제 n 이 씨앗마다 같나": bool(len(set(ns)) == 1),
            "분자: 씨앗": len(ds), "분모: 등록 씨앗": SUB_SEEDS,
            "🔴 m(n) 씨앗 평균 Δρ": float(a.mean()),
            "씨앗 SD": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "🔴 se(n) = SD/√씨앗": float(a.std(ddof=1) / math.sqrt(len(a))) if len(a) > 1 else 0.0,
            "씨앗 최소": float(a.min()), "씨앗 최대": float(a.max()),
            "씨앗 중 양수": int((a > 0).sum()),
            "빈 지시자 열(씨앗별 최대)": int(max(zc)),
            "🔴 T(군집=개체 · i.i.d. 행 부트)": T_e,
            "🔴 T(군집=도메인)": T_d,
            "SE(개체)": b_ent["SE"], "SE(도메인)": b_dom["SE"],
            "군집 수(개체/도메인)": [b_ent["군집 수"], b_dom["군집 수"]],
            "부트 성공/요청": [b_ent["재표집 성공"], b_ent["요청"]],
            "판정(개체 T)": L.verdict(float(a.mean()), T_e),
            "판정(도메인 T)": L.verdict(float(a.mean()), T_d),
            "🔴 문턱의 1% 안인가(개체)": bool(T_e > 0 and abs(abs(a.mean()) - T_e) / T_e < 0.01),
            "⚠ 부트는 씨앗 0 표본 하나 위에서만 돈다": True,
        }
    return steps


# ── §7 평평함 ───────────────────────────────────────────────────────────────
def flatness(steps: dict) -> dict:
    ks = sorted(steps, key=lambda x: int(x))
    n = np.asarray([steps[k]["🔴 실제 n"] for k in ks], dtype=float)
    m = np.asarray([steps[k]["🔴 m(n) 씨앗 평균 Δρ"] for k in ks])
    se = np.asarray([steps[k]["🔴 se(n) = SD/√씨앗"] for k in ks])
    ln = np.log(n)
    slopes = {}
    flat = []
    for i in range(len(ks) - 1):
        dl = ln[i + 1] - ln[i]
        s = (m[i + 1] - m[i]) / dl
        ss = math.sqrt(se[i] ** 2 + se[i + 1] ** 2) / dl
        is_flat = bool(abs(s) < FLAT_F and abs(s) < 1.96 * ss)
        slopes[f"{ks[i]}→{ks[i+1]}"] = {
            "기울기 s (Δρ / ln n)": float(s), "se(s)": float(ss),
            "|s| < F": bool(abs(s) < FLAT_F), "95% 구간이 0 을 품나": bool(abs(s) < 1.96 * ss),
            "🔴 평평한가(둘 다)": is_flat}
        flat.append(is_flat)
    start = None
    for i in range(len(flat)):
        if all(flat[i:]):
            start = int(n[i])
            break
    # 포화 적합 m = a − b n^(−1/2)
    A = np.vstack([np.ones_like(n), -1.0 / np.sqrt(n)]).T
    sol, *_ = np.linalg.lstsq(A, m, rcond=None)
    rng = np.random.RandomState(101)
    boots = []
    for _ in range(1000):
        mm = m + rng.normal(0, np.maximum(se, 1e-12))
        s2, *_ = np.linalg.lstsq(A, mm, rcond=None)
        boots.append(s2[0])
    ba = np.asarray(boots)
    lo, hi = float(np.percentile(ba, 2.5)), float(np.percentile(ba, 97.5))
    # 영교차
    cross = None
    for i in range(len(m) - 1):
        if m[i] <= 0 < m[i + 1] or m[i] >= 0 > m[i + 1]:
            t = -m[i] / (m[i + 1] - m[i])
            cross = float(math.exp(ln[i] + t * (ln[i + 1] - ln[i])))
            break
    band_e = [int(n[i]) for i in range(len(ks))
              if steps[ks[i]]["판정(개체 T)"].startswith("나")]
    band_d = [int(n[i]) for i in range(len(ks))
              if steps[ks[i]]["판정(도메인 T)"].startswith("나")]
    return {
        "🔴 자": f"|s| < F(={FLAT_F}) **그리고** 95% 구간이 0 을 품는다 — 둘 다여야 평평하다",
        "칸 사이 기울기": slopes,
        "분자: 평평한 칸": int(sum(flat)), "분모: 칸": len(flat),
        "🔴🔴 평평 시작점 n(그 뒤 전부 평평)": start,
        "🔴🔴 평평해지는 n 이 있나": bool(start is not None),
        "포화 적합 m = a − b·n^(−1/2)": {
            "â(점근값)": float(sol[0]), "b̂": float(sol[1]),
            "â 95% 구간(씨앗잡음 부트 1,000)": [lo, hi],
            "🔴 구간이 0 을 품나": bool(lo <= 0 <= hi),
            "⚠ 이 적합은 곁이다": "판정에 안 쓴다 — 곡선의 모양을 적기 위한 것"},
        "🔴 영교차 n*(선형 보간 · log n 위)": cross,
        "🔴 못 가르는 띠(개체 T)": band_e,
        "🔴 못 가르는 띠(도메인 T)": band_d,
        "판정(개체 T) 칸별": {k: steps[k]["판정(개체 T)"] for k in ks},
        "판정(도메인 T) 칸별": {k: steps[k]["판정(도메인 T)"] for k in ks},
    }


# ── ㉢ 순열 null(자 사이 포함관계용) ─────────────────────────────────────────
def col_perm_null(rows, base, plus, y, g, reps=PERM_COL, seed=13) -> dict:
    Xb = L.mat(rows, *base)
    Xp = L.mat(rows, *plus)
    ra, _, _ = L.rho_of(Xb, y, g, seeds=[0])
    rng = np.random.RandomState(seed)
    d = []
    for _ in range(reps):
        perm = rng.permutation(len(rows))
        rb, _, _ = L.rho_of(np.hstack([Xb, Xp[perm]]), y, g, seeds=[0])
        d.append(rb - ra)
    a = np.asarray(d)
    rb0, _, _ = L.rho_of(np.hstack([Xb, Xp]), y, g, seeds=[0])
    obs = rb0 - ra
    p95 = float(np.percentile(a, 95))
    return {"순열 수": reps, "평균": float(a.mean()), "SD": float(a.std()),
            "상위 5% 지점": p95, "🔴 관측 Δρ(씨앗 0)": obs,
            "㉢ 통과(관측 > 상위 5%)": bool(obs > p95),
            "⚠ 씨앗 0 하나다": "10씨앗 평균과 다른 수다 — 잇지 마라(조항 60)"}


# ── 본체 ────────────────────────────────────────────────────────────────────
def main(part: str | None = None) -> dict:
    t0 = time.time()
    out_path = resolve_out(part)
    R: dict = {
        "노트": 961, "레인": "판정",
        "사전등록": "docs/prereg_961_curve.md (커밋 a19103fde · 측정 전 · 파일 하나)",
        "논문 스텝": 504,
        "🔴 무엇을 재나": "Δρ₃|₁₊지시자 를 **n 의 함수**로. 배경 풀 3,896 고정 · 구성 고정 · 씨앗 30",
        "🔴 새 자료": "0 — HTTP 호출 0",
        "🔴 판을 뗐다": "판 ρ · 유보를 한 번도 안 건드린다 — 판 주장 0",
        "산출물": str(out_path.relative_to(ROOT)),
        "부분 주행인가": bool(part),
    }
    W: dict = {}

    # ── 입력 ────────────────────────────────────────────────────────────────
    L.WIKI = OUTDIR
    L.PAIRS = PAIRDIR / "pairs.jsonl.gz"
    L.assert_no_label_files()
    sh = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16]
          for p in sorted(OUTDIR.glob("*.jsonl.gz"))}
    sh["sao959/pairs.jsonl.gz"] = hashlib.sha256(
        (PAIRDIR / "pairs.jsonl.gz").read_bytes()).hexdigest()[:16]
    W["W1 입력 sha256(앞16)"] = {
        "🔴 무엇": "959 가 잰 그 파일인가 — 파일로 받아서 해싱한다",
        "파일 수": len(sh), "표": sh, "통과": len(sh) == 12}

    wd = L.load_wiki_daily()
    pairs = L.load_pairs()
    coords = L.load_coords()
    lp = L.load_lifepop()
    built = build_arms_fast(wd, coords, lp, pairs)
    B = built["B"]
    yB = np.asarray([r["y_들림"] for r in B], dtype=float)
    gB = np.asarray([r["개체"] for r in B])
    domB = np.asarray([r["도메인"] for r in B])
    comp_B = dict(Counter(domB.tolist()))
    doms_B = sorted(comp_B)

    # 941 표 — **같은 배경(959)** 위의 464행
    L.PAIRS = PAIRS941
    p941 = L.load_pairs()
    b941 = build_arms_fast(wd, coords, lp, p941)
    B941 = b941["B"]
    comp_941 = dict(Counter([r["도메인"] for r in B941]))
    doms_941 = sorted(comp_941)

    # ── 🔴🔴 W0 — **맨 앞이다**(W2 앞) ───────────────────────────────────────
    pc = read_prereg_const()
    # 🔴 배경 풀 = 일별 표에 실린 **개체** 수(도메인별 개체를 합친다).
    #    ⚠ 초판은 `len(wd)`(= {"일별","시작일"} 두 키) 를 썼고 **W0 가 측정 전에 멈춰 세웠다**.
    #    사전등록값 3896 은 안 건드렸다 — 고친 것은 **재는 식**이다(그 사실을 판정문에 신고한다).
    bgpool = sum(len(v) for v in wd["일별"].values())
    measured = {"ARMB_ROWS": len(B), "ARM941_ROWS": len(B941), "BGPOOL": bgpool,
                "BOOT_REQ": BOOT}
    W["🔴🔴 W0-가 사전등록 상수 대조"] = w0_const_check(pc, code_consts(measured))
    if not W["🔴🔴 W0-가 사전등록 상수 대조"]["통과"]:
        R["🔴 W0 불통과 — 측정 전에 멈춘다"] = W["🔴🔴 W0-가 사전등록 상수 대조"]
        R["§5 배선 검사"] = W
        out_path.write_text(json.dumps(R, ensure_ascii=False, indent=1))
        print(json.dumps(R["🔴 W0 불통과 — 측정 전에 멈춘다"], ensure_ascii=False, indent=1))
        return R

    # W-BG — 배경이 정말 고정인가
    x3_full = L.mat(B, "x3")
    idx_probe = strat_index(domB, comp_B, 800, seed=0)
    sub_probe = [B[i] for i in idx_probe]
    x3_sub = L.mat(sub_probe, "x3")
    W["🔴 W-BG 배경 풀 고정"] = {
        "🔴 무엇": "행을 부분표집해도 `x3`(도메인 배경 대비 편차)가 한 원소도 안 바뀌나",
        "배경 개체 수": bgpool,
        "전량 x3 sha256(앞16)": hashlib.sha256(x3_full.tobytes()).hexdigest()[:16],
        "부분표본 x3 최대 어긋남": float(np.abs(x3_sub - x3_full[idx_probe]).max()),
        "통과": bool(np.abs(x3_sub - x3_full[idx_probe]).max() == 0.0 and bgpool == 3896)}

    # W2 — 960 재현
    for r in B:
        r["xd"] = [1.0 if r["도메인"] == d else 0.0 for d in doms_B]
    ra_full, _, Pa_full = L.rho_of(L.mat(B, "x1", "xd"), yB, gB)
    rb_full, _, Pb_full = L.rho_of(L.mat(B, "x1", "xd", "x3"), yB, gB)
    d_full = rb_full - ra_full
    W["W2 960 재현(전량 2,050·10열)"] = {
        "960 이 낸 값": 0.007111895407650559, "다시 낸 값": d_full,
        "차": abs(d_full - 0.007111895407650559),
        "팔 B 행": [2050, len(B)], "941 행": [464, len(B941)],
        "통과": bool(len(B) == 2050 and len(B941) == 464
                   and abs(d_full - 0.007111895407650559) < 1e-12)}

    # W3 — 🔴 진짜 grep (상수 아니다)
    LABELS = ("판", "verdict", "유보", "holdout", "denominator")
    hits = [o for o in L.OPENED if any(t in o for t in L.LABEL_FILES)]
    W["🔴 W3 판 라벨 파일을 열었나"] = {
        "🔴 무엇": "`L.OPENED`(실제로 연 경로 전량)를 `L.LABEL_FILES` 로 **grep 한다** — 상수가 아니다",
        "분자: 라벨에 걸린 경로": len(hits), "분모: 연 경로": len(L.OPENED),
        "라벨 바늘": list(L.LABEL_FILES), "곁 바늘(신고용)": list(LABELS),
        "걸린 것": hits, "통과": bool(len(hits) == 0 and len(L.OPENED) > 0)}

    # ── §6 두 팔의 곡선 ─────────────────────────────────────────────────────
    lad_A = ladder(B, yB, gB, domB, comp_941, NGRID_A, doms_941, "㉠")
    lad_B = ladder(B, yB, gB, domB, comp_B, NGRID_B, doms_B, "㉡")

    # W4 — 구성이 정말 고정됐나
    def comp_err(comp, grid, lad):
        tot = sum(comp.values())
        worst = 0.0
        for n in grid:
            idx = strat_index(domB, comp, n, seed=0)
            c = Counter(domB[idx].tolist())
            for d, v in comp.items():
                worst = max(worst, abs(c.get(d, 0) / len(idx) - v / tot))
        return worst
    eA, eB = comp_err(comp_941, NGRID_A, lad_A), comp_err(comp_B, NGRID_B, lad_B)
    W["🔴 W4 구성 고정"] = {
        "🔴 무엇": "각 부분표집의 도메인 비율이 팔의 등록 구성과 얼마나 어긋나나(반올림 오차만 남아야 한다)",
        "㉠ 최대 비율 오차": eA, "㉡ 최대 비율 오차": eB,
        "㉠ 구성(464)": comp_941, "㉡ 구성(2,050)": comp_B,
        "통과": bool(eA < 0.01 and eB < 0.01)}
    W["W5 지시자 행렬"] = {
        "㉠ 열 수": len(doms_941), "㉡ 열 수": len(doms_B),
        "㉠ 빈 열(최대)": max(v["빈 지시자 열(씨앗별 최대)"] for v in lad_A.values()),
        "㉡ 빈 열(최대)": max(v["빈 지시자 열(씨앗별 최대)"] for v in lad_B.values()),
        "🔴 두 팔의 열 수가 다르다": "9 vs 10 — 절대값을 한 문장에 안 잇는다(조항 60)",
        "통과": bool(len(doms_941) == 9 and len(doms_B) == 10)}
    W["W8 씨앗 회계"] = {
        "🔴 무엇": "씨앗 수가 등록값이고, **천장 칸은 표가 하나라 분산이 0** 인가",
        "㉠ 씨앗": [v["분자: 씨앗"] for v in lad_A.values()],
        "㉡ 씨앗": [v["분자: 씨앗"] for v in lad_B.values()],
        "🔴 ㉡ 천장(2050) 씨앗 SD": lad_B["2050"]["씨앗 SD"],
        "통과": bool(all(v["분자: 씨앗"] == SUB_SEEDS for v in lad_A.values())
                   and all(v["분자: 씨앗"] == SUB_SEEDS for v in lad_B.values())
                   and lad_B["2050"]["씨앗 SD"] == 0.0)}

    # ── §6′ 닻 셋 ───────────────────────────────────────────────────────────
    def anchor(rows, dom_list, tag):
        for r in rows:
            r["xd"] = [1.0 if r["도메인"] == d else 0.0 for d in dom_list]
        y = np.asarray([r["y_들림"] for r in rows], dtype=float)
        g = np.asarray([r["개체"] for r in rows])
        dm = np.asarray([r["도메인"] for r in rows])
        ra, _, Pa = L.rho_of(L.mat(rows, "x1", "xd"), y, g)
        rb, _, Pb = L.rho_of(L.mat(rows, "x1", "xd", "x3"), y, g)
        be = boot_se(Pa, Pb, y, g, why=f"닻 {tag} 개체")
        bd = boot_se(Pa, Pb, y, dm, why=f"닻 {tag} 도메인")
        Te, Td = T_of(be["SE"]), T_of(bd["SE"])
        return {"분모: 행": len(rows), "지시자 열": len(dom_list), "🔴 Δρ": rb - ra,
                "T(개체)": Te, "T(도메인)": Td,
                "판정(개체 T)": L.verdict(rb - ra, Te),
                "판정(도메인 T)": L.verdict(rb - ra, Td),
                "🔴 여유(|Δρ|/T 개체)": abs(rb - ra) / Te}
    B1983 = [r for r in B if r["도메인"] != "만화"]
    R["§6′ 닻 셋 — 🔴 곡선이 아니다. 셋 다 분모가 다르다(조항 60)"] = {
        "① 실제 941 표(464행 · 9열 · 959 배경)": anchor(B941, doms_941, "941"),
        "② 만화 제외 전량(1,983행 · 9열)": anchor(B1983, sorted({r["도메인"] for r in B1983}), "1983"),
        "③ 전량(2,050행 · 10열)": anchor(B, doms_B, "2050"),
        "⚠ 왜 잇지 않나": ("① 은 다른 쌍 표에서 온 464행이고 ② 는 2,050 에서 한 도메인을 통째로 뺀 것이며 "
                     "③ 은 전량이다. **표집 설계가 셋 다 다르다**"),
        "🔴 티처 #99 의 사다리가 섞은 것": ("티처 표의 464·651·850 은 **㉠ 계열(464 구성)**이고 "
                                "1,983 은 **만화 제외 전량**이며 2,050 은 **전량**이다 — 세 설계를 한 표에 놓았다"),
    }

    # ── §8 자들 — 포함관계 · 채택(3값) ───────────────────────────────────────
    r1, _, P1 = L.rho_of(L.mat(B, "x1"), yB, gB)
    r13, _, P13 = L.rho_of(L.mat(B, "x1", "x3"), yB, gB)
    drho = r13 - r1
    be3 = boot_se(P1, P13, yB, gB, why="㉠ 층③ 개체")
    bd3 = boot_se(P1, P13, yB, domB, why="㉠ 층③ 도메인")
    T_e3, T_d3 = T_of(be3["SE"]), T_of(bd3["SE"])
    y2 = np.asarray([r["y_수준"] for r in B], dtype=float)
    s1, _, Q1 = L.rho_of(L.mat(B, "x1"), y2, gB)
    s13, _, Q13 = L.rho_of(L.mat(B, "x1", "x3"), y2, gB)
    bsub = boot_se(Q1, Q13, y2, gB, why="㉡ 부표적 개체")
    perm = col_perm_null(B, ["x1"], ["x3"], yB, gB)
    rt = rulers(sum_delta=drho, sum_T=T_e3, sub_delta=s13 - s1, sub_T=T_of(bsub["SE"]),
                perm_obs=perm["🔴 관측 Δρ(씨앗 0)"], perm_p95=perm["상위 5% 지점"],
                card_T=L.CARD_T)

    ra_alt, _, Pa_alt = L.rho_of(L.mat(B, "x1"), yB, gB)
    b_alt = boot_se(Pa_alt, Pa_full, yB, gB, why="㉣ 대체물 개체")
    b_altd = boot_se(Pa_alt, Pa_full, yB, domB, why="㉣ 대체물 도메인")
    alt_T_e, alt_T_d = T_of(b_alt["SE"]), T_of(b_altd["SE"])
    b_on = boot_se(Pa_full, Pb_full, yB, gB, why="㉣ 그 위 층③ 개체")
    b_ond = boot_se(Pa_full, Pb_full, yB, domB, why="㉣ 그 위 층③ 도메인")
    on_T_e, on_T_d = T_of(b_on["SE"]), T_of(b_ond["SE"])
    three = {"sum_pass": bool(drho > T_e3),
             "sub_sign_pass": bool(np.sign(s13 - s1) == np.sign(drho)),
             "perm_pass": perm["㉢ 통과(관측 > 상위 5%)"]}
    ad_ent = adopt(alt_delta=ra_full - r1, alt_T=alt_T_e,
                   layer_on_alt_delta=d_full, layer_on_alt_T=on_T_e, **three)
    ad_dom = adopt(sum_pass=bool(drho > T_d3), sub_sign_pass=three["sub_sign_pass"],
                   perm_pass=three["perm_pass"],
                   alt_delta=ra_full - r1, alt_T=alt_T_d,
                   layer_on_alt_delta=d_full, layer_on_alt_T=on_T_d)

    # W6 — 🔴 반환값이 정말 실렸나(항진명제 아니다)
    carried = {k: ad_ent[k] for k in ad_ent}
    W["🔴 W6 lab.adopt 의 반환값이 그대로 실렸나"] = {
        "🔴 무엇": "산출물에 실은 dict 를 `adopt()` 를 **다시 불러** 키별로 대조한다(`x is x` 아니다)",
        "lab/adopt.py sha256(앞16)": hashlib.sha256((ROOT / "lab/adopt.py").read_bytes()).hexdigest()[:16],
        "분자: 값이 같은 키": sum(1 for k, v in adopt(
            alt_delta=ra_full - r1, alt_T=alt_T_e, layer_on_alt_delta=d_full,
            layer_on_alt_T=on_T_e, **three).items() if carried.get(k) == v),
        "분모: 키": len(ad_ent),
        "3값이 정말 셋 다 나오나(도메인 판)": ad_dom.get("🔴 ㉣ 더 싼 대체물이 있나(3값)"),
        "통과": bool(all(carried.get(k) == v for k, v in adopt(
            alt_delta=ra_full - r1, alt_T=alt_T_e, layer_on_alt_delta=d_full,
            layer_on_alt_T=on_T_e, **three).items()))}
    W["🔴 W10 자 사이 포함관계"] = {**rt, "통과": bool("🔴🔴 ㉢ ⊂ ㉠ (㉠ 통과 ⟹ ㉢ 통과)" in rt)}
    W["W7 부트 회계"] = {
        "분자: 회계가 맞는 호출": sum(1 for c in BOOT_CALLS if c["요청"] == BOOT),
        "분모: 부트 호출": len(BOOT_CALLS),
        "통과": bool(len(BOOT_CALLS) > 0)}
    W["🔴🔴 W0-나 부트 호출 인자 감사"] = w0_call_audit(BOOT_CALLS, BOOT, "BOOT")
    W["🔴 W9 데몬"] = {
        "🔴 무엇": "`L.daemon_asleep()` 을 **그대로** 통과 값으로 쓴다 — 상수가 아니다",
        "재웠나": L.daemon_asleep(), "언제 재웠나(UTC)": "2026-08-13T13:52:59Z",
        "통과": bool(L.daemon_asleep())}
    W["🔴 W11 부분 주행 가드"] = {
        "🔴 무엇": "`--part` 를 주면 전량 산출물을 원리상 못 덮는다(959·960 에서 두 번 났다)",
        "이번 주행 산출물": str(out_path.name), "부분인가": bool(part),
        "가드 시험(--part 로 OUT 을 노려도 다른 이름이 나오나)":
            str(resolve_out("시험").name) != OUT.name,
        "통과": bool(str(resolve_out("시험").name) != OUT.name
                   and (out_path == OUT) == (not part))}

    # ── §5′ 🔴 심어서 떨어뜨리기 ────────────────────────────────────────────
    plant = {}
    plant["W0-가 에 BOOT=4001 을 심는다"] = not w0_const_check(
        pc, code_consts(measured, boot_override=4001))["통과"]
    plant["W0-나 에 요청=400 호출을 심는다"] = not w0_call_audit(
        BOOT_CALLS + [{"왜": "심은 것", "요청": 400, "군집 수": 0, "씨앗": 0}], BOOT, "BOOT")["통과"]
    plant["W3 에 라벨 경로를 심는다"] = bool(
        [o for o in (L.OPENED + [str(ROOT / "data/lab/denominator.json")])
         if any(t in o for t in L.LABEL_FILES)])
    bad = dict(ad_ent)
    bad["🔴🔴 채택(㉠㉡㉢㉣)"] = not bad["🔴🔴 채택(㉠㉡㉢㉣)"]
    plant["W6 에 딴 값을 심는다"] = not all(
        bad.get(k) == v for k, v in ad_ent.items())
    try:
        boot_se(P1, P13, yB, gB, reps=400, why="심은 것")
        plant["🔴 부트 호출 자리에 reps=400 을 심는다"] = False
    except SystemExit:
        plant["🔴 부트 호출 자리에 reps=400 을 심는다"] = True
    try:
        resolve_out("x")
        plant["W11 에 부분 주행으로 OUT 을 노린다"] = str(resolve_out("x")) != str(OUT)
    except SystemExit:
        plant["W11 에 부분 주행으로 OUT 을 노린다"] = True
    W["🔴🔴 §5′ 심어서 떨어뜨리기"] = {
        "🔴 무엇": "나쁜 값을 심으면 정말 떨어지나 — **떨어질 수 없는 검사는 검사가 아니다**(티처 #99 C5)",
        "표": plant, "분자: 정말 떨어진 것": sum(1 for v in plant.values() if v),
        "분모: 심은 것": len(plant), "통과": all(plant.values())}

    W["통과 수"] = sum(1 for v in W.values() if isinstance(v, dict) and v.get("통과") is True)
    W["검사 수"] = sum(1 for v in W.values() if isinstance(v, dict) and "통과" in v)
    R["§5 배선 검사"] = W

    # ── §7 평평함 ──────────────────────────────────────────────────────────
    fA, fB = flatness(lad_A), flatness(lad_B)
    R["§6-가 팔 ㉠ — 464 구성 · 9열 · n 300~851"] = {
        "🔴 구성": comp_941, "지시자 열": len(doms_941), "칸": lad_A}
    R["§6-나 팔 ㉡ — 2,050 구성 · 10열 · n 300~2,050"] = {
        "🔴 구성": comp_B, "지시자 열": len(doms_B), "칸": lad_B}
    R["§7-가 평평함 · 팔 ㉠"] = fA
    R["§7-나 평평함 · 팔 ㉡"] = fB

    R["§8 자들 — 문턱 · 포함관계 · 채택(3값)"] = {
        "🔴 자별 문턱과 포함관계": rt,
        "㉠ 층 ③(전량 · 지시자 없이)": {"Δρ": drho, "T(개체)": T_e3, "T(도메인)": T_d3,
                            "판정(개체)": L.verdict(drho, T_e3),
                            "판정(도메인)": L.verdict(drho, T_d3)},
        "㉡ 부 표적 y_수준": {"Δρ": s13 - s1, "T": T_of(bsub["SE"]),
                       "부호 유지": three["sub_sign_pass"]},
        "㉢ 열 순열 null": perm,
        "㉣ 대체물(도메인 지시자 10열)": {
            "대체물 혼자": {"Δρ": ra_full - r1, "T(개체)": alt_T_e, "T(도메인)": alt_T_d},
            "그 위 층 ③": {"Δρ": d_full, "T(개체)": on_T_e, "T(도메인)": on_T_d}},
        "🔴🔴 채택 — lab.adopt.adopt(3값)": {
            "군집 = 개체": ad_ent, "군집 = 도메인": ad_dom,
            "🔴 960 은 이 자리에서 두 하위검사가 둘 다 「못 가른다」인데 `채택=true` 를 냈다":
                "961 의 3값이 그것을 「모른다 → 보류」로 바꾼다"},
    }

    # ── §9 판정 — 🔴 구간과 곡선으로 ────────────────────────────────────────
    def span(steps, key):
        ks = sorted(steps, key=lambda x: int(x))
        out = {"다 — 뺀다": [], "나 — 못 가른다": [], "가 — 든다": []}
        for k in ks:
            v = steps[k][key]
            out["다 — 뺀다" if v.startswith("다") else
                ("가 — 든다" if v.startswith("가") else "나 — 못 가른다")].append(
                steps[k]["🔴 실제 n"])
        return out
    R["🔴🔴 D-1 「층 ③ 은 도메인 이름표의 대리변수인가」 — **구간으로 답한다**"] = {
        "🔴 답의 꼴": "가/나 하나로 안 찍는다. **n 의 구간**으로 적는다",
        "팔 ㉠(464 구성 · 9열) · 개체 T": span(lad_A, "판정(개체 T)"),
        "팔 ㉠ · 도메인 T": span(lad_A, "판정(도메인 T)"),
        "팔 ㉡(2,050 구성 · 10열) · 개체 T": span(lad_B, "판정(개체 T)"),
        "팔 ㉡ · 도메인 T": span(lad_B, "판정(도메인 T)"),
        "🔴 영교차 n*": {"㉠": fA["🔴 영교차 n*(선형 보간 · log n 위)"],
                    "㉡": fB["🔴 영교차 n*(선형 보간 · log n 위)"]},
    }
    R["🔴🔴 D-2 「평평해지는 n 이 있나」"] = {
        "자": f"|s| < {FLAT_F} **그리고** 95% 구간이 0 을 품는다",
        "㉠": {"있나": fA["🔴🔴 평평해지는 n 이 있나"], "시작점": fA["🔴🔴 평평 시작점 n(그 뒤 전부 평평)"],
              "평평한 칸": f"{fA['분자: 평평한 칸']}/{fA['분모: 칸']}"},
        "㉡": {"있나": fB["🔴🔴 평평해지는 n 이 있나"], "시작점": fB["🔴🔴 평평 시작점 n(그 뒤 전부 평평)"],
              "평평한 칸": f"{fB['분자: 평평한 칸']}/{fB['분모: 칸']}"},
        "🔴 없으면 원장에 박을 문장": "이 자로는 「층 ③ 이 도메인 이름표의 대리변수인가」를 물을 수 없다",
    }
    R["🔴 D-3 501 claims[4] 와 503 의 대체 문장"] = {
        "🔴 둘 다 이미 원장 1013 에서 「못 가른다」로 내렸다": "측정 전 커밋 9e7913342",
        "이 측정이 그 하향을 뒤집나": "아래 예측 채점과 D-1·D-2 로 결정한다",
    }

    # ── §10 예측 채점 ──────────────────────────────────────────────────────
    an = R["§6′ 닻 셋 — 🔴 곡선이 아니다. 셋 다 분모가 다르다(조항 60)"]
    mB = {k: v["🔴 m(n) 씨앗 평균 Δρ"] for k, v in lad_B.items()}
    mA = {k: v["🔴 m(n) 씨앗 평균 Δρ"] for k, v in lad_A.items()}
    ksA = sorted(mA, key=lambda x: int(x))
    ksB = sorted(mB, key=lambda x: int(x))
    upA = sum(1 for i in range(len(ksA) - 1) if mA[ksA[i + 1]] > mA[ksA[i]])
    upB = sum(1 for i in range(len(ksB) - 1) if mB[ksB[i + 1]] > mB[ksB[i]])
    lo, hi = fB["포화 적합 m = a − b·n^(−1/2)"]["â 95% 구간(씨앗잡음 부트 1,000)"]
    xstar = fB["🔴 영교차 n*(선형 보간 · log n 위)"]
    Q = {
        "Q1 전량 Δρ == 960 값": bool(abs(d_full - 0.007111895407650559) < 1e-12),
        "Q2 실제 941 표 Δρ < 0": bool(an["① 실제 941 표(464행 · 9열 · 959 배경)"]["🔴 Δρ"] < 0),
        "Q3 만화 제외 1,983 Δρ > 0": bool(an["② 만화 제외 전량(1,983행 · 9열)"]["🔴 Δρ"] > 0),
        "Q4 ㉠ 단조 증가 7/7 이상": bool(upA >= 7),
        "Q5 ㉡ 단조 증가 10/11 이상": bool(upB >= 10),
        "Q6 ㉡ m(300) < 0": bool(mB[ksB[0]] < 0),
        "Q7 평평해지는 n 이 없다(㉡)": bool(not fB["🔴🔴 평평해지는 n 이 있나"]),
        "Q8 â 95% 구간이 0 을 안 품는다(㉡)": bool(not (lo <= 0 <= hi)),
        "Q9 영교차 n* ∈ [600,1400](㉡)": bool(xstar is not None and 600 <= xstar <= 1400),
        "Q10 도메인 T 아래 두 팔 전 구간 「못 가른다」": bool(
            all(v["판정(도메인 T)"].startswith("나") for v in lad_A.values())
            and all(v["판정(도메인 T)"].startswith("나") for v in lad_B.values())),
        "Q11 ㉢ 문턱이 사실상 0(|상위5%| < CARD_T)": bool(rt["🔴 ㉢ 의 문턱이 사실상 0 인가"]),
        "Q12 심어서 떨어뜨리기 전부 떨어진다": bool(all(plant.values())),
    }
    R["🔴 예측 채점"] = Q
    R["🔴 예측 계수"] = {"분자: 맞은 것": sum(1 for v in Q.values() if v), "분모: 예측": len(Q)}
    R["⚠ 가를 수 없는 것"] = {
        "① 부분표집 ≠ 더 큰 표": "n>2,050 은 이 자료에 없다. 곡선을 밖으로 늘려 읽지 마라",
        "② 두 팔은 구성도 열 수도 다르다": "높이 차를 「구성 효과」로 읽을 수 없다 — 지시자 열이 9 vs 10 이다",
        "③ 부트는 각 칸의 씨앗 0 표본 하나 위에서만 돈다": "T 자체의 씨앗 변동은 안 쟀다",
        "④ 「평평하다」는 관측 구간 안의 진술": "300 ≤ n ≤ 2,050",
    }
    R["초"] = round(time.time() - t0, 1)
    out_path.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    return R


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default=None, help="🔴 부분 주행 — 전량 산출물을 안 덮는다")
    a = ap.parse_args()
    r = main(a.part)
    print(json.dumps({k: v for k, v in r.items()
                      if not k.startswith("§6-") and k != "§5 배선 검사"},
                     ensure_ascii=False, indent=1)[:12000])
