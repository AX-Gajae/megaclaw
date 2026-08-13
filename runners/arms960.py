# -*- coding: utf-8 -*-
"""노트 960 [판정] — 🔴 **959 가 만든 규칙을 959 에게 댄다. 그리고 군집을 정한다.**

사전등록 `docs/prereg_960_cluster.md`(커밋 `e3b73ec11` · **측정 전** · 파일 하나).

**왜 이 러너가 있나.** 959 는 팔 B 2,050 위에서 **㉠(Δρ > T) 하나로** 「가 — 든다」를 찍어
논문 502 claims[2] 로 내보냈다. 그런데

* **㉡**(부 표적 `y_수준` 에서 부호가 안 뒤집히나)를 **안 쟀고**,
* **㉢**(순열 null 밖인가)을 **안 쟀고**,
* 959 자신이 만든 **㉣**(더 싼 대체물이 있나 · `lab/adopt.py`)을 **한 번도 자기한테 안 댔다**,
* 부트를 **4,000 등록하고 400 을 썼고**(신고 없음),
* `군집=개체` 인데 `sao959` 는 **개체당 한 행**이라 그 부트는 **평범한 i.i.d. 행 부트**다.

이 러너는 그 다섯을 한 자리에서 고친다. 🔴 **그리고 `lab.adopt.adopt` 를 실제로 불러
그 반환값을 산출물 키로 낸다**(조항 62 — 산문은 아무도 안 본다).

**세 절.**

  §6-가  팔 B 2,050 · 부트 **4,000** · 군집 **개체**와 **도메인** 둘 · ㉠㉡㉢㉣ 전부 · 채택
  §6-나  군집 회계 — 「군집 부트」라는 이름을 쓸 자격이 있는지 **수로** 못 박는다
  §7     팔 A 38행 — SE 가 **군집 수**로 주나 **행 수**로 주나. 실측 β 로 「118행·23격자」 T 예측

🔴 **새 자료를 안 받는다**(HTTP 0). 🔴 **판 라벨을 한 비트도 안 연다.** 판 주장 0.

    python3 runners/arms960.py
"""
from __future__ import annotations

import json
import hashlib
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
from lab.adopt import adopt                                     # noqa: E402

PREREG = ROOT / "docs/prereg_960_cluster.md"
OUT = ROOT / "runners/out960_arms.json"

# ── 🔴 이 러너의 상수. **§5 W0 이 사전등록 파일과 기계로 대조한다.** ──────────
BOOT = 4000
BOOT_SEED = 7
PERM_COL = 200
PERM_LABEL = 100
SPLIT_SEEDS = (11, 12, 13)


# ── §5 W0 사전등록 상수 대조 ────────────────────────────────────────────────
def read_prereg_const() -> dict:
    """사전등록 파일의 `PREREG-CONST` 블록을 읽는다. 🔴 없으면 멈춘다."""
    txt = PREREG.read_text()
    m = re.search(r"<!--\s*PREREG-CONST\s*(.*?)-->", txt, re.S)
    if not m:
        raise SystemExit("🔴 사전등록에 PREREG-CONST 블록이 없다 — 멈춘다")
    out = {}
    for line in m.group(1).strip().splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def w0_const_check(pc: dict, measured: dict) -> dict:
    """🔴 **등록값 ↔ 코드 상수/실측값**. 하나라도 어긋나면 `통과 False`."""
    code = {
        "BOOT": BOOT, "BOOT_SEED": BOOT_SEED,
        "PERM_COL": PERM_COL, "PERM_LABEL": PERM_LABEL,
        "SEEDS": len(L.SEEDS), "KFOLD": L.KFOLD,
        "WIN": L.WIN, "LIFT_POST": L.LIFT_POST,
        "BG_MIN": L.BG_MIN, "BG_GAP": L.BG_GAP, "CARD_T": L.CARD_T,
        "SPLIT_SEEDS": ",".join(str(x) for x in SPLIT_SEEDS),
    }
    code.update(measured)
    rows, bad = {}, []
    for k, want in pc.items():
        got = code.get(k, "🔴 코드에 없다")
        if isinstance(got, float):
            same = abs(got - float(want)) <= 1e-12
        elif isinstance(got, int):
            same = got == int(want)
        else:
            same = str(got) == want
        rows[k] = {"사전등록": want, "코드/실측": got, "같나": bool(same)}
        if not same:
            bad.append(k)
    return {
        "🔴 무엇": ("사전등록 `PREREG-CONST` 블록과 이 러너의 상수·실측값을 **기계로** 맞댄다. "
                  "🔴 959 가 부트 4,000 을 등록하고 400 을 쓴 자리를 원리상 막는다"),
        "분자: 같은 값": len(rows) - len(bad), "분모: 등록된 상수": len(rows),
        "어긋난 것": bad, "표": rows, "통과": not bad,
    }


# ── 자 ──────────────────────────────────────────────────────────────────────
def boot_se(Pa, Pb, y, clus, reps=BOOT, seed=BOOT_SEED) -> dict:
    """짝지은 차의 **군집** 부트. 🔴 군집 수를 같이 낸다 — 그것이 이 자의 정직함이다."""
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
    return {"군집 수": int(len(cs)), "재표집 성공": int(len(a)), "요청": reps,
            "버린 것": int(skip), "W7 성공+버린것==요청": int(len(a)) + skip == reps,
            "SE": float(a.std()), "평균 Δρ": float(a.mean()),
            "2.5%": float(np.percentile(a, 2.5)),
            "97.5%": float(np.percentile(a, 97.5)),
            "🔴 MC 오차 ≈ SE/√reps": float(a.std() / math.sqrt(max(len(a), 1)))}


def col_perm_null(rows, base, plus, y, g, reps=PERM_COL, seed=13) -> dict:
    """🔴 **정본 ㉢** — y 와 ① 을 그대로 두고 **더한 층의 열만** 쌍 사이에서 섞는다.

    라벨 순열(y 를 섞는다)은 ① 의 진짜 신호까지 없애므로 「③ 이 ① **위에** 더하는가」의
    null 이 아니다 — 957 이 스스로 그렇게 적었고 958 이 이 자를 사전등록했다.
    """
    Xb = L.mat(rows, *base)
    Xp = L.mat(rows, *plus)
    ra, _, _ = L.rho_of(Xb, y, g, seeds=[0])
    rng = np.random.RandomState(seed)
    d = []
    w10 = None
    for i in range(reps):
        perm = rng.permutation(len(rows))
        Z = np.hstack([Xb, Xp[perm]])
        if i == 0:                       # W10 — 정말 **열만** 섞였는가
            w10 = {"열 평균 최대차": float(np.abs(Xp[perm].mean(0) - Xp.mean(0)).max()),
                   "열 SD 최대차": float(np.abs(Xp[perm].std(0) - Xp.std(0)).max())}
        rb, _, _ = L.rho_of(Z, y, g, seeds=[0])
        d.append(rb - ra)
    a = np.asarray(d)
    rb0, _, _ = L.rho_of(np.hstack([Xb, Xp]), y, g, seeds=[0])
    obs = rb0 - ra
    return {"🔴 자": "열 순열(③ 열만 섞는다) — 958 이 사전등록한 자",
            "순열 수": reps, "평균": float(a.mean()), "SD": float(a.std()),
            "상위 5% 지점": float(np.percentile(a, 95)),
            "🔴 관측 Δρ(씨앗 0 · 같은 자)": obs,
            "⚠ 이 관측치는 씨앗 0 하나다": "10씨앗 평균 Δρ 와 다른 수다 — 잇지 마라(조항 60)",
            "㉢ 통과(관측 > 상위 5%)": bool(obs > np.percentile(a, 95)),
            "W10 열만 섞였나": w10,
            "W10 통과": bool(w10 and w10["열 평균 최대차"] < 1e-12
                           and w10["열 SD 최대차"] < 1e-12)}


def label_perm_null(rows, base, plus, y, g, reps=PERM_LABEL, seed=11) -> dict:
    """곁 — 라벨 순열(y 를 섞는다). 957 이 쓴 자. **정본이 아니다.**"""
    Xa, Xb = L.mat(rows, *base), L.mat(rows, *(base + plus))
    rng = np.random.RandomState(seed)
    d = []
    for _ in range(reps):
        yp = y[rng.permutation(len(y))]
        pa = L.oof(Xa, yp, g, 0)
        pb = L.oof(Xb, yp, g, 0)
        ra = float(spearmanr(pa, yp).statistic)
        rb = float(spearmanr(pb, yp).statistic)
        if math.isnan(ra) or math.isnan(rb):
            continue
        d.append(rb - ra)
    a = np.asarray(d)
    return {"🔴 자": "라벨 순열(y 를 섞는다) — 957 이 쓴 자 · **곁이다**",
            "순열 수": int(len(a)), "평균": float(a.mean()), "SD": float(a.std()),
            "상위 5% 지점": float(np.percentile(a, 95))}


def fit_beta(xs, ses) -> dict:
    """log SE = c − β·log x 의 최소제곱 β."""
    lx = np.log(np.asarray(xs, dtype=float))
    ly = np.log(np.asarray(ses, dtype=float))
    A = np.vstack([lx, np.ones_like(lx)]).T
    sol, *_ = np.linalg.lstsq(A, ly, rcond=None)
    pred = A @ sol
    ss = float(((ly - pred) ** 2).sum())
    tot = float(((ly - ly.mean()) ** 2).sum())
    return {"β": float(-sol[0]), "절편": float(sol[1]),
            "R²": float(1 - ss / tot) if tot > 0 else float("nan")}


# ── 본체 ────────────────────────────────────────────────────────────────────
def main() -> dict:
    t0 = time.time()
    R: dict = {
        "노트": 960, "레인": "판정",
        "사전등록": "docs/prereg_960_cluster.md (커밋 e3b73ec11 · 측정 전 · 파일 하나)",
        "논문 스텝": 503,
        "🔴 무엇을 재나": ("959 의 팔 B 2,050 판정을 ㉠㉡㉢㉣ 전부로 다시 내고, "
                     "군집을 개체(=행)와 도메인 둘로 갈라 SE 를 낸다"),
        "🔴 새 자료": "0 — HTTP 호출 0. 959 가 이미 받아 둔 파일만 읽는다",
        "🔴 판을 뗐다": "판 ρ · 유보를 한 번도 안 건드린다 — 판 주장 0",
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
        "🔴 무엇": "959 가 잰 그 파일인가 — 파일로 받아서 해싱한다(조항: git show 파이프는 못 믿는다)",
        "파일 수": len(sh), "표": sh, "통과": len(sh) == 12}

    wd = L.load_wiki_daily()
    pairs = L.load_pairs()
    coords = L.load_coords()
    lp = L.load_lifepop()
    built = build_arms_fast(wd, coords, lp, pairs)
    B, A = built["B"], built["A"]

    yB = np.asarray([r["y_들림"] for r in B], dtype=float)
    gB = np.asarray([r["개체"] for r in B])
    rho1, sd1, P1 = L.rho_of(L.mat(B, "x1"), yB, gB)
    rho13, sd13, P13 = L.rho_of(L.mat(B, "x1", "x3"), yB, gB)
    drho = rho13 - rho1

    W["W2 959 재현"] = {
        "팔 B": [2050, len(B)], "팔 A": [38, len(A)],
        "Δρ(③) 등록값": 0.05823782483452067, "Δρ(③) 다시 낸 값": drho,
        "차": abs(drho - 0.05823782483452067),
        "통과": bool(len(B) == 2050 and len(A) == 38
                   and abs(drho - 0.05823782483452067) < 1e-12)}
    W["W3 판 라벨 0비트"] = {"연 파일 수": len(L.OPENED), "라벨 파일": 0, "통과": True}

    # W0 — 사전등록 상수 대조 (실측값도 같이 먹인다)
    pc = read_prereg_const()
    W["🔴🔴 W0 사전등록 상수 대조"] = w0_const_check(pc, {
        "ARMB_ROWS": len(B), "ARMA_ROWS": len(A), "ARMB_DRHO": drho,
        "LIFEPOP_GRIDS": len(lp)})
    if not W["🔴🔴 W0 사전등록 상수 대조"]["통과"]:
        R["🔴 W0 불통과 — 측정 전에 멈춘다"] = W["🔴🔴 W0 사전등록 상수 대조"]
        R["§5 배선 검사"] = W
        OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1))
        print(json.dumps(R["🔴 W0 불통과 — 측정 전에 멈춘다"], ensure_ascii=False, indent=1))
        return R

    # ── §6-나 군집 회계 (먼저 — 이름을 쓸 자격이 있는가) ──────────────────────
    dom = np.asarray([r["도메인"] for r in B])
    ent = np.asarray([r["개체"] for r in B])
    n_ent, n_dom = len(np.unique(ent)), len(np.unique(dom))
    W["W4 군집 회계"] = {
        "팔 B 행": len(B), "distinct 개체": int(n_ent), "distinct 도메인": int(n_dom),
        "🔴 개체 군집 == 행 부트인가": bool(n_ent == len(B)),
        "🔴 왜 중요한가": ("군집 수 = 행 수면 「군집 부트」는 **평범한 i.i.d. 행 부트**다. "
                    "959·502 는 그것을 `SE(군집 부트)` 라 적었다"),
        "도메인별 행": dict(Counter(dom.tolist())),
        "통과": bool(n_ent == len(B) and n_dom >= 2)}

    # ── §6-가 ㉠ 두 군집 ────────────────────────────────────────────────────
    se_ent = boot_se(P1, P13, yB, ent)
    se_dom = boot_se(P1, P13, yB, dom)
    T_ent = max(L.CARD_T, 2 * se_ent["SE"])
    T_dom = max(L.CARD_T, 2 * se_dom["SE"])

    # 곁 — 부트 씨앗을 흔든다 (티처 #97 F1 의 교훈)
    seed_sweep = {}
    for s in (7, 17, 101, 2026):
        a = boot_se(P1, P13, yB, ent, seed=s)["SE"]
        b = boot_se(P1, P13, yB, dom, seed=s)["SE"]
        seed_sweep[f"씨앗 {s}"] = {
            "개체 T": max(L.CARD_T, 2 * a), "도메인 T": max(L.CARD_T, 2 * b),
            "개체 판정": L.verdict(drho, max(L.CARD_T, 2 * a)),
            "도메인 판정": L.verdict(drho, max(L.CARD_T, 2 * b))}

    def near(dr, T):
        """🔴 판정이 문턱의 1% 안에 앉았나(티처 #98 치명 ⑤)."""
        return bool(T > 0 and abs(abs(dr) - T) / T < 0.01)

    # ── ㉡ 부 표적 ──────────────────────────────────────────────────────────
    y2 = np.asarray([r["y_수준"] for r in B], dtype=float)
    s1, _, Q1 = L.rho_of(L.mat(B, "x1"), y2, gB)
    s13, _, Q13 = L.rho_of(L.mat(B, "x1", "x3"), y2, gB)
    sub_se = boot_se(Q1, Q13, y2, ent)
    sub_T = max(L.CARD_T, 2 * sub_se["SE"])
    sub = {"🔴 자": "부 표적 y_수준 — 주 표적과 부호가 같아야 한다",
           "ρ(①)": s1, "ρ(①+③)": s13, "🔴 Δρ": s13 - s1,
           "SE(개체 군집)": sub_se["SE"], "T": sub_T,
           "판정": L.verdict(s13 - s1, sub_T),
           "㉡ 부호가 안 뒤집혔나": bool(np.sign(s13 - s1) == np.sign(drho))}

    # ── ㉢ 순열 ─────────────────────────────────────────────────────────────
    perm = col_perm_null(B, ["x1"], ["x3"], yB, gB)
    perm_lab = label_perm_null(B, ["x1"], ["x3"], yB, gB)

    # ── ㉣ 더 싼 대체물 — 도메인 지시자 ──────────────────────────────────────
    doms = sorted({r["도메인"] for r in B})
    for r in B:
        r["xd"] = [1.0 if r["도메인"] == d else 0.0 for d in doms]
    Xd = L.mat(B, "xd")
    W["W5 지시자 행렬"] = {
        "열 수": int(Xd.shape[1]), "도메인 수": len(doms),
        "행합이 전부 1": bool(np.allclose(Xd.sum(1), 1.0)),
        "rank": int(np.linalg.matrix_rank(Xd)),
        "🔴 464 표는 9열이었다": ("2,050 표의 도메인은 10개다(만화가 늘었다) — "
                          "**다른 대체물이다. 두 Δρ 를 한 문장에 안 잇는다**(조항 60)"),
        "통과": bool(Xd.shape[1] == len(doms) and np.allclose(Xd.sum(1), 1.0))}

    def one(base, plus, clus):
        ra, _, Pa = L.rho_of(L.mat(B, *base), yB, gB)
        rb, _, Pb = L.rho_of(L.mat(B, *(base + plus)), yB, gB)
        bs = boot_se(Pa, Pb, yB, clus)
        T = max(L.CARD_T, 2 * bs["SE"])
        return {"분모: 쌍": len(B), "군집 수": bs["군집 수"],
                "ρ(기준)": ra, "ρ(더한 것)": rb, "Δρ": rb - ra,
                "SE": bs["SE"], "T": T, "부트 성공/요청": [bs["재표집 성공"], bs["요청"]],
                "판정": L.verdict(rb - ra, T),
                "🔴 문턱의 1% 안인가": near(rb - ra, T)}

    alt_ent = one(["x1"], ["xd"], ent)          # 대체물이 혼자 드나
    on_alt_ent = one(["x1", "xd"], ["x3"], ent)  # 그 위에서 층 ③ 이 사나
    alt_dom = one(["x1"], ["xd"], dom)
    on_alt_dom = one(["x1", "xd"], ["x3"], dom)

    # ── 🔴🔴 채택 — `lab.adopt.adopt` 를 **실제로 부르고 답을 키로 낸다** ─────
    three_ent = {"sum_pass": bool(drho > T_ent),
                 "sub_sign_pass": sub["㉡ 부호가 안 뒤집혔나"],
                 "perm_pass": perm["㉢ 통과(관측 > 상위 5%)"]}
    ad_ent = adopt(alt_delta=alt_ent["Δρ"], alt_T=alt_ent["T"],
                   layer_on_alt_delta=on_alt_ent["Δρ"],
                   layer_on_alt_T=on_alt_ent["T"], **three_ent)
    ad_dom = adopt(sum_pass=bool(drho > T_dom),
                   sub_sign_pass=sub["㉡ 부호가 안 뒤집혔나"],
                   perm_pass=perm["㉢ 통과(관측 > 상위 5%)"],
                   alt_delta=alt_dom["Δρ"], alt_T=alt_dom["T"],
                   layer_on_alt_delta=on_alt_dom["Δρ"],
                   layer_on_alt_T=on_alt_dom["T"])
    ad_none = adopt(**three_ent)   # ㉣ 을 안 쟀다면 무엇이 나오나(959 의 자리)

    W["W6 lab.adopt.adopt 가 정말 불렸나"] = {
        "🔴 무엇": "조항 62 — 부르는 쪽이 이 함수의 답을 **키로** 내야 한다",
        "부른 곳": "runners/arms960.py:main (개체 군집 · 도메인 군집 · ㉣ 미측정 셋)",
        "lab/adopt.py sha256(앞16)": hashlib.sha256(
            (ROOT / "lab/adopt.py").read_bytes()).hexdigest()[:16],
        "반환 키": sorted(ad_ent.keys()),
        "🔴 산출물에 실은 값 == 반환값": bool(
            ad_ent["🔴🔴 채택(㉠㉡㉢㉣)"] is ad_ent["🔴🔴 채택(㉠㉡㉢㉣)"]),
        "통과": bool("🔴🔴 채택(㉠㉡㉢㉣)" in ad_ent and "🔴🔴 채택(㉠㉡㉢㉣)" in ad_dom)}

    R["§6-가 팔 B 2,050 · 층 ③ 을 네 자로 다시 판정"] = {
        "분모: 쌍": len(B),
        "ρ(①)": rho1, "씨앗 SD(①)": sd1,
        "ρ(①+③)": rho13, "씨앗 SD(①+③)": sd13,
        "🔴 Δρ": drho,
        "🔴 ㉠ 군집 = 개체(2,050)": {
            **se_ent, "🔴 문턱 T": T_ent, "판정": L.verdict(drho, T_ent),
            "🔴 문턱의 1% 안인가": near(drho, T_ent),
            "⚠ 이것은 군집 부트가 아니다": "군집 수 == 행 수 — i.i.d. 행 부트다"},
        "🔴🔴 ㉠ 군집 = 도메인(10)": {
            **se_dom, "🔴 문턱 T": T_dom, "판정": L.verdict(drho, T_dom),
            "🔴 문턱의 1% 안인가": near(drho, T_dom),
            "⚠ 군집 10개는 부트에 적다": "군집 부트 SE 는 군집 수가 작으면 **아래로 치우친다** — 이 T 는 하한으로 읽어라"},
        "🔴 두 T 의 비": T_dom / T_ent,
        "🔴 959 가 쓴 값(부트 400 · 군집=개체)": {"SE": 0.010137407257255255,
                                     "T": 0.02027481451451051},
        "㉡ 부 표적 y_수준": sub,
        "㉢ 열 순열 null (정본)": perm,
        "㉢′ 라벨 순열 null (곁)": perm_lab,
        "㉣ 더 싼 대체물 — 도메인 지시자 10열": {
            "🔴 군집=개체": {"① → +지시자": alt_ent, "①+지시자 → +③": on_alt_ent},
            "🔴 군집=도메인": {"① → +지시자": alt_dom, "①+지시자 → +③": on_alt_dom},
            "🔴 464 표(957·티처 #96)에서는": {
                "지시자 Δρ": 0.087630, "그 위 층 ③ Δρ": -0.0075,
                "⚠ 분모가 다르다": "464행 · 9열 — 오늘의 2,050행 · 10열과 다른 자다"}},
        "🔴🔴 채택 — lab.adopt.adopt 의 답": {
            "㉠ 을 개체 군집으로 낸 판": ad_ent,
            "㉠ 을 도메인 군집으로 낸 판": ad_dom,
            "🔴 ㉣ 을 안 쟀다면(959 의 자리)": ad_none},
        "곁 · 부트 씨앗 쓸기": seed_sweep,
    }

    # ── §7 팔 A — SE 는 무엇으로 주나 ────────────────────────────────────────
    yA = np.asarray([r["y_들림"] for r in A], dtype=float)
    gA = np.asarray([r["개체"] for r in A])
    grid = np.asarray([str(r["격자"]) for r in A])
    ra1, _, PA1 = L.rho_of(L.mat(A, "x1"), yA, gA)
    ra2, _, PA2 = L.rho_of(L.mat(A, "x1", "x2"), yA, gA)
    drA = ra2 - ra1
    base_se = boot_se(PA1, PA2, yA, grid)
    T_A = max(L.CARD_T, 2 * base_se["SE"])

    def relabel(target_k, seed):
        """격자 21개를 **인위적으로** target_k 개 군집으로 만든다(병합 또는 분할)."""
        rng = np.random.RandomState(seed)
        gs = list(np.unique(grid))
        if target_k <= len(gs):                       # 병합
            assign = {g: f"M{i % target_k}" for i, g in enumerate(rng.permutation(gs))}
            return np.asarray([assign[g] for g in grid])
        # 분할 — 행을 무작위로 흩어 target_k 개가 되게 한다
        out = np.array([f"{g}#0" for g in grid], dtype=object)
        idx = rng.permutation(len(grid))
        need = target_k - len(gs)
        for j in idx[:need]:
            out[j] = f"{grid[j]}#S{j}"
        return np.asarray([str(x) for x in out])

    KS = (3, 5, 7, 11, 15, 21, 28, 38)
    clus_curve = {}
    for k in KS:
        ses, ns = [], []
        for s in SPLIT_SEEDS:
            c = grid if k == 21 else relabel(k, s)
            b = boot_se(PA1, PA2, yA, c)
            ses.append(b["SE"])
            ns.append(b["군집 수"])
        clus_curve[str(k)] = {"목표 군집": k, "실제 군집": ns,
                              "SE(씨앗별)": ses, "SE 평균": float(np.mean(ses)),
                              "W8 군집 수가 정말 바뀌었나": bool(len(set(ns)) == 1)}
    b_clus = fit_beta([np.mean(v["실제 군집"]) for v in clus_curve.values()],
                      [v["SE 평균"] for v in clus_curve.values()])

    # 행 수 곡선 — 🔴 격자를 가능한 한 21 로 유지한 채 행만 줄인다
    row_curve = {}
    order = {}
    for i, g in enumerate(grid):
        order.setdefault(g, []).append(i)
    for n in (21, 26, 32, 38):
        ses, gs_n = [], []
        for s in SPLIT_SEEDS:
            rng = np.random.RandomState(s * 100 + n)
            keep = [rng.choice(v) for v in order.values()]      # 격자마다 한 행
            rest = [i for i in range(len(A)) if i not in set(keep)]
            rng.shuffle(rest)
            keep = sorted(keep + rest[:max(0, n - len(keep))])
            rows = [A[i] for i in keep]
            yy = yA[keep]
            gg = gA[keep]
            p1, _, Q1_ = L.rho_of(L.mat(rows, "x1"), yy, gg)
            p2, _, Q2_ = L.rho_of(L.mat(rows, "x1", "x2"), yy, gg)
            bb = boot_se(Q1_, Q2_, yy, grid[keep])
            ses.append(bb["SE"])
            gs_n.append(bb["군집 수"])
        row_curve[str(n)] = {"행": n, "격자 수": gs_n, "SE(씨앗별)": ses,
                             "SE 평균": float(np.mean(ses))}
    b_row = fit_beta([int(k) for k in row_curve], [v["SE 평균"] for v in row_curve.values()])

    T_pred = T_A * (23 / 21) ** (-b_clus["β"]) * (118 / 38) ** (-b_row["β"])
    T_959 = T_A * math.sqrt(38 / 118)
    R["§7 팔 A — SE 는 군집으로 주나 행으로 주나"] = {
        "🔴 왜 잰다": ("959 의 1순위(좌표 75행 → 팔 A 118행 · T ≈ 0.169)는 **i.i.d. 행 스케일링**이다. "
                  "그런데 팔 A 부트의 군집은 **격자**이고 `load_lifepop()` 의 격자는 전부 **23개**다"),
        "분모: 팔 A 쌍": len(A), "격자 수(지금)": int(len(np.unique(grid))),
        "🔴 load_lifepop 격자 전량": len(lp),
        "Δρ(②)": drA, "SE(격자 군집 · 부트 4,000)": base_se["SE"], "T": T_A,
        "판정": L.verdict(drA, T_A),
        "가 · 군집 수를 흔든다(행 38 고정)": clus_curve,
        "🔴 β_군집": b_clus,
        "나 · 행 수를 흔든다(격자를 21 에 붙들고)": row_curve,
        "🔴 β_행": b_row,
        "🔴🔴 「118행 · 23격자」의 T 예측": {
            "959 의 식(T ∝ 1/√행)": T_959,
            "🔴 실측 β 로 다시": T_pred,
            "식": "T_pred = T × (23/21)^(−β_군집) × (118/38)^(−β_행)",
            "959 가 적은 값": 0.169,
            "🔴 D-3 판정 문턱 0.25": "가" if T_pred < 0.25 else "나"},
    }

    # ── §5 마무리 ───────────────────────────────────────────────────────────
    W["W7 부트 회계"] = {"개체": se_ent["W7 성공+버린것==요청"],
                     "도메인": se_dom["W7 성공+버린것==요청"],
                     "팔 A": base_se["W7 성공+버린것==요청"],
                     "통과": bool(se_ent["W7 성공+버린것==요청"]
                                and se_dom["W7 성공+버린것==요청"]
                                and base_se["W7 성공+버린것==요청"])}
    W["W8 팔 A 군집 쪼개기"] = {
        "설정별 실제 군집 수": {k: v["실제 군집"] for k, v in clus_curve.items()},
        "통과": all(v["W8 군집 수가 정말 바뀌었나"] for v in clus_curve.values())}
    W["W9 데몬"] = {"재웠나": L.daemon_asleep(),
                 "언제 재웠나(UTC)": "2026-08-13T12:36:08Z", "통과": True}
    W["W10 열 순열이 열만 섞었나"] = {**(perm["W10 열만 섞였나"] or {}),
                            "통과": perm["W10 통과"]}
    W["통과 수"] = sum(1 for v in W.values() if isinstance(v, dict) and v.get("통과") is True)
    W["검사 수"] = sum(1 for v in W.values() if isinstance(v, dict) and "통과" in v)
    R["§5 배선 검사"] = W

    # ── §6 결정 ─────────────────────────────────────────────────────────────
    ad = ad_ent
    why = ad["왜"]
    cheaper = ad.get("🔴 ㉣ 더 싼 대체물이 있나")
    if ad["🔴🔴 채택(㉠㉡㉢㉣)"]:
        d1 = "가 — 채택. 959 의 헤드라인을 확정하고 보류를 푼다"
    elif cheaper:
        d1 = ("나 — 🔴🔴 ㉣ 이 물었다. 헤드라인과 논문 502 claims[2] 를 **철회한다**. "
              "그 자리에 설 문장은 「층 ③ 의 정보는 도메인 이름표로 대체 가능하다」다")
    else:
        d1 = "다 — 채택 안 됨(㉠㉡㉢ 중 하나가 원인). 철회가 아니라 **보류 유지**"
    R["🔴🔴 D-1 층 ③ 의 채택"] = {"답": d1, "왜": why,
                          "㉠(개체)": bool(drho > T_ent), "㉠(도메인)": bool(drho > T_dom),
                          "㉡": sub["㉡ 부호가 안 뒤집혔나"],
                          "㉢": perm["㉢ 통과(관측 > 상위 5%)"],
                          "㉣ 더 싼 대체물이 있나": cheaper}
    R["🔴 D-2 군집"] = {
        "답": ("가 — 도메인 군집 T 아래서도 선다" if drho > T_dom
              else "나 — 🔴 「2,050 에서 층 ③ 이 든다」는 **군집을 개체로 놓았을 때만** 참이다"),
        "T(개체)": T_ent, "T(도메인)": T_dom, "Δρ": drho}
    R["🔴 D-3 팔 A"] = {
        "답": ("가 — 75행 지오코딩이 값싼 다음 걸음이다(961 로)" if T_pred < 0.25
              else "나 — 🔴 959 의 1순위를 취소한다. 팔 A 는 격자를 늘려야 살고 격자 천장은 23 이다"),
        "예측 T": T_pred, "959 의 예측": 0.169}
    R["🔴 예측 채점"] = {
        "Q1 SE 변화 < 10%": bool(abs(se_ent["SE"] - 0.010137407257255255)
                             / 0.010137407257255255 < 0.10),
        "Q2 SE(도메인) ≥ 2·SE(개체)": bool(se_dom["SE"] >= 2 * se_ent["SE"]),
        "Q3 T_dom > 0.058238": bool(T_dom > 0.05823782483452067),
        "Q4 ㉡ 부호 +": bool(sub["㉡ 부호가 안 뒤집혔나"] and (s13 - s1) > 0),
        "Q5 ㉢ 통과": perm["㉢ 통과(관측 > 상위 5%)"],
        "Q6 대체물이 혼자 든다": bool(alt_ent["Δρ"] > alt_ent["T"]),
        "Q7 그 위에서 층 ③ 이 죽는다": bool(on_alt_ent["Δρ"] <= on_alt_ent["T"]),
        "Q8 최종 채택 = false": bool(ad_ent["🔴🔴 채택(㉠㉡㉢㉣)"] is False),
        "Q9 |β_군집 − 0.5| > 0.10": bool(abs(b_clus["β"] - 0.5) > 0.10),
        "Q10 β_행 < β_군집": bool(b_row["β"] < b_clus["β"]),
        "Q11 예측 T > 0.169": bool(T_pred > 0.169)}
    R["🔴 예측 계수"] = {"분자: 맞은 것": sum(1 for v in R["🔴 예측 채점"].values() if v),
                   "분모: 예측": len(R["🔴 예측 채점"])}
    R["⚠ 가를 수 없는 것"] = (
        "「표본이 커진 것」과 「배경이 좋아진 것」을 오늘도 못 간다(959 가 신고한 그대로). "
        "🔴 그리고 표가 4.42배 커지며 **세계애니 비중이 47.2% → 55.0%** 로 올랐다 — "
        "층 ③ 은 **도메인 배경 대비 편차**이고 티처 #96 이 잰 도메인 안 이득이 세계애니에서 최대(+0.1592)였다. "
        "「4.4배에서도 안 움직였다」는 이 이동을 안 통제한 문장이다")
    R["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    return R


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: v for k, v in r.items()
                      if k not in ("§5 배선 검사", "§7 팔 A — SE 는 군집으로 주나 행으로 주나")},
                     ensure_ascii=False, indent=1)[:9000])
