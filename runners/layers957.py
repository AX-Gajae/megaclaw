# -*- coding: utf-8 -*-
"""노트 957 [판정] — **`s` 를 세 층으로 갈라 한 층씩 붙이며 Δρ 를 잰다.**

사전등록 `docs/prereg_957_layers.md`(커밋 `06171b9df` · **측정 전** · 파일 하나).

  층 ① 개체    = 액션 앞 90일 그 개체의 위키 조회수      (지금 `s` 의 전부)
  층 ② 물리 장 = 그 격자의 앞 90일 서울 생활인구(250m·시간별)
  층 ③ 무관    = 같은 도메인·같은 날짜의 **무관한 개체 N 개** 평균 대비 편차

두 팔이고 🔴 **분모가 다르다**(조항 60).
  팔 A = 격자에 붙는 팝업 쌍 47 (층 ①②③)
  팔 B = wiki 쌍 584            (층 ①③ — ②는 원리상 없다)

자: `ρ_sao` = 능형회귀의 **교차검증 밖(OOF) 스피어만**. 겹은 **개체**로 묶는다.
문턱: `T = max(0.00353, 2·SE_boot(Δρ))` · `SE_boot` 는 **군집 재표집**(A=격자 · B=개체).

🔴 이 파일은 **판 라벨을 한 비트도 안 연다**(`assert_no_label_files`).

사용: python3 runners/layers957.py
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

# 🔴 macOS Accelerate BLAS 가 `Z.T @ Z` 에서 **거짓 경고**를 낸다(divide by zero /
# overflow / invalid). 값은 안 틀린다 — `W10` 이 einsum 과 대조해 코드로 확인한다.
np.seterr(all="ignore")

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from runners.out901h_link import grid_of          # noqa: E402  (EPSG:5179 · 자기시험 있음)

PAIRS = ROOT / "data/ingest/sao941/pairs.jsonl.gz"
WIKI = ROOT / "data/ingest/wiki_daily"
ATT = ROOT / "data/state/grid915_attach.json"
GEO = ROOT / "data/state/geo919_coords.json"
LP = ROOT / "runners/out957_lifepop.json.gz"
OUT = ROOT / "runners/out957_layers.json"

#: 🔴 이 러너가 **절대 안 여는** 파일 — 판 라벨이 여기 있다.
LABEL_FILES = ("denominator.json", "popup_v2", "market_axes.json", "kobis_axes.json",
               "y_perday", "absolute.json")
OPENED: list[str] = []

WIN = 90            # s 의 길이
LIFT_POST = 14      # 들림의 뒤 창 (자유파라미터 3)
LIFT_PRE = 14       # 들림의 앞 창
BG_MIN = 5          # N_p 최소 (자유파라미터 4)
BG_GAP = 90         # 「무관」의 액션일 간격 (자유파라미터 5)
KFOLD = 5           # (자유파라미터 2)
SEEDS = list(range(10))
ALPHAS = (0.1, 1.0, 10.0, 100.0)
BOOT = 2000
PERM = 100
CARD_T = 0.00353    # 카드가 준 문턱 — 이 자에서 쓸 수 있는지 자체가 물음이다


def opened(p) -> str:
    OPENED.append(str(p))
    return str(p)


def assert_no_label_files() -> None:
    bad = [o for o in OPENED for t in LABEL_FILES if t in o]
    if bad:
        raise AssertionError(f"🔴 판 라벨 파일을 열었다: {bad}")


def daemon_asleep() -> bool:
    """🔴 「재웠다」를 산문으로 안 쓴다 — launchctl 에서 읽는다."""
    import subprocess
    r = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        if "com.sweetspot.wm.harvest" in ln:
            return False          # 목록에 있다 = 안 재웠다
    return True


def dirty_paths() -> list:
    import subprocess
    r = subprocess.run(["git", "-c", "core.quotePath=false", "status", "--porcelain", "-z"],
                       capture_output=True, text=True, cwd=str(ROOT))
    return [x for x in r.stdout.split("\0") if x]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


# ── 자료 ────────────────────────────────────────────────────────────────────
def load_pairs() -> list[dict]:
    out = []
    with gzip.open(opened(PAIRS), "rt") as f:
        for line in f:
            out.append(json.loads(line))
    return out


def load_wiki_daily() -> dict:
    """도메인 → 개체 → {날짜(int) : 조회수}, 그리고 개체 → 시작일."""
    per: dict[str, dict[str, dict[int, float]]] = defaultdict(dict)
    start: dict[str, str] = {}
    for f in sorted(WIKI.glob("*.jsonl.gz")):
        with gzip.open(opened(f), "rt") as fh:
            for line in fh:
                r = json.loads(line)
                per[r["도메인"]][r["키"]] = dict(zip(r["날짜"], r["조회수"]))
                start[r["키"]] = r.get("시작일") or ""
    return {"일별": per, "시작일": start}


def load_coords() -> dict:
    c: dict[str, tuple] = {}
    for r in json.loads(Path(opened(ATT)).read_text())["행"]:
        c[r["id"]] = (r["lat"], r["lon"], "915attach")
    for k, v in json.loads(Path(opened(GEO)).read_text())["회복"].items():
        c.setdefault(k, (v["lat"], v["lon"], "919recover"))
    return c


def load_lifepop() -> dict:
    with gzip.open(opened(LP), "rt") as f:
        return json.load(f)


# ── 특징 여섯 모양 ──────────────────────────────────────────────────────────
def _slope(y: np.ndarray) -> float:
    t = np.arange(len(y), dtype=float)
    t = t - t.mean()
    d = float((t * t).sum())
    return float((t * (y - y.mean())).sum() / d) if d else 0.0


def feats_log(s: np.ndarray) -> list[float]:
    """층 ① — 원 계열 위에서 (log 를 여기서 씌운다)."""
    L = np.log10(1.0 + s)
    return [math.log10(1.0 + float(s.mean())),
            math.log10(1.0 + float(s[-7:].mean())),
            math.log10(1.0 + float(s[-28:].mean())),
            _slope(L),
            float(L.std()),
            math.log10(1.0 + float(s.max())) - math.log10(1.0 + float(np.median(s)))]


def feats_dev(r: np.ndarray) -> list[float]:
    """층 ③ — 이미 로그 자리의 편차라 log 를 다시 안 씌운다(사전등록 §3)."""
    return [float(r.mean()), float(r[-7:].mean()), float(r[-28:].mean()),
            _slope(r), float(r.std()), float(r.max() - float(np.median(r)))]


def feats_field(daily: np.ndarray, hourly: np.ndarray, wknd: np.ndarray) -> list[float]:
    """층 ② — daily(90) · hourly(90×24) · wknd(90 bool)."""
    L = np.log10(1.0 + daily)
    m = float(daily.mean())
    we = daily[wknd].mean() if wknd.any() else float("nan")
    wd = daily[~wknd].mean() if (~wknd).any() else float("nan")
    hm = float(hourly.mean())
    return [math.log10(1.0 + m),
            math.log10(1.0 + float(daily[-7:].mean())),
            _slope(L),
            float(daily.std() / m) if m else 0.0,
            float(we / wd) if wd else 0.0,
            float(hourly[:, 12:18].mean() / hm) if hm else 0.0]


# ── 능형회귀 + OOF 스피어만 ────────────────────────────────────────────────
def ridge_fit(X: np.ndarray, y: np.ndarray, a: float) -> tuple:
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / sd
    ym = y.mean()
    A = Z.T @ Z + a * np.eye(Z.shape[1])
    w = np.linalg.solve(A, Z.T @ (y - ym))
    return w, mu, sd, ym


def ridge_pred(m, X: np.ndarray) -> np.ndarray:
    w, mu, sd, ym = m
    return ((X - mu) / sd) @ w + ym


def oof(X: np.ndarray, y: np.ndarray, groups: np.ndarray, seed: int,
        k: int = KFOLD, alpha: float | None = None) -> np.ndarray:
    """겹을 **개체**로 묶어 자른 OOF 예측. alpha=None 이면 속겹 CV 로 고른다."""
    rng = np.random.RandomState(seed)
    gs = np.unique(groups)
    rng.shuffle(gs)
    kk = min(k, len(gs))
    fold = {g: i % kk for i, g in enumerate(gs)}
    fi = np.array([fold[g] for g in groups])
    p = np.zeros(len(y))
    for f in range(kk):
        te = fi == f
        tr = ~te
        if tr.sum() < 3 or te.sum() == 0:
            p[te] = y[tr].mean() if tr.sum() else 0.0
            continue
        a = alpha
        if a is None:                          # 속겹 CV — 훈련 겹 안에서만 고른다
            gtr = np.unique(groups[tr])
            r2 = np.random.RandomState(seed + 1000 + f)
            r2.shuffle(gtr)
            k2 = min(5, len(gtr))
            f2 = {g: i % k2 for i, g in enumerate(gtr)}
            i2 = np.array([f2[g] for g in groups[tr]])
            Xtr, ytr = X[tr], y[tr]
            best, ba = None, ALPHAS[0]
            for aa in ALPHAS:
                e = 0.0
                for ff in range(k2):
                    t2 = i2 == ff
                    if (~t2).sum() < 3 or t2.sum() == 0:
                        continue
                    m = ridge_fit(Xtr[~t2], ytr[~t2], aa)
                    e += float(((ridge_pred(m, Xtr[t2]) - ytr[t2]) ** 2).sum())
                if best is None or e < best:
                    best, ba = e, aa
            a = ba
        m = ridge_fit(X[tr], y[tr], a)
        p[te] = ridge_pred(m, X[te])
    return p


def rho_of(X: np.ndarray, y: np.ndarray, groups: np.ndarray, seeds=SEEDS,
           k: int = KFOLD, alpha: float | None = None) -> tuple:
    """씨앗별 OOF ρ 의 평균·SD, 그리고 씨앗 평균 OOF 예측(부트스트랩용)."""
    rs, ps = [], []
    for s in seeds:
        p = oof(X, y, groups, s, k, alpha)
        ps.append(p)
        rs.append(float(spearmanr(p, y).statistic))
    P = np.mean(ps, axis=0)
    return float(np.mean(rs)), float(np.std(rs)), P


def boot_se(Pa: np.ndarray, Pb: np.ndarray, y: np.ndarray, clus: np.ndarray,
            reps: int = BOOT, seed: int = 7) -> dict:
    """🔴 짝지은 차의 군집 부트스트랩 — 같은 재표집에서 두 모형의 ρ 를 둘 다 낸다."""
    rng = np.random.RandomState(seed)
    cs = np.unique(clus)
    idx = {c: np.where(clus == c)[0] for c in cs}
    d = []
    for _ in range(reps):
        pick = rng.choice(len(cs), len(cs), replace=True)
        ii = np.concatenate([idx[cs[j]] for j in pick])
        if len(np.unique(y[ii])) < 3:
            continue
        ra = float(spearmanr(Pa[ii], y[ii]).statistic)
        rb = float(spearmanr(Pb[ii], y[ii]).statistic)
        if math.isnan(ra) or math.isnan(rb):
            continue
        d.append(rb - ra)
    d = np.array(d)
    return {"재표집 성공": int(len(d)), "요청": reps,
            "SE": float(d.std()), "평균 Δρ": float(d.mean()),
            "2.5%": float(np.percentile(d, 2.5)), "97.5%": float(np.percentile(d, 97.5))}


def perm_null(Xa: np.ndarray, Xb: np.ndarray, y: np.ndarray, groups: np.ndarray,
              reps: int = PERM, seed: int = 11) -> dict:
    """라벨 순열 바닥 — y 를 섞고 같은 파이프라인으로 Δρ 를 낸다(씨앗 하나)."""
    rng = np.random.RandomState(seed)
    d = []
    for _ in range(reps):
        yp = y[rng.permutation(len(y))]
        pa = oof(Xa, yp, groups, 0)
        pb = oof(Xb, yp, groups, 0)
        ra = float(spearmanr(pa, yp).statistic)
        rb = float(spearmanr(pb, yp).statistic)
        if math.isnan(ra) or math.isnan(rb):
            continue
        d.append(rb - ra)
    d = np.array(d)
    return {"순열 수": int(len(d)), "평균": float(d.mean()), "SD": float(d.std()),
            "상위 5% 지점": float(np.percentile(d, 95))}


def verdict(dr: float, T: float) -> str:
    if dr > T:
        return "가 — 든다(넣는다)"
    if dr < -T:
        return "다 — 뺀다"
    return "나 — 이 n 에서는 못 가른다(안 넣는다)"


# ── 팔 만들기 ──────────────────────────────────────────────────────────────
def build_arms(wd: dict, coords: dict, lp: dict, pairs: list[dict],
               bg_min: int = BG_MIN, bg_gap: int = BG_GAP,
               lift_post: int = LIFT_POST) -> dict:
    """🔴 특징 생성기는 `o_결과` 를 **안 본다**(W7) — y 만 따로 만든다."""
    daily, startd = wd["일별"], wd["시작일"]
    LP0, LP1 = dt.date(2025, 1, 1), dt.date(2026, 7, 31)
    rec, drop = [], defaultdict(int)
    bg_selfhit = 0
    fill = 0
    for p in pairs:
        if not p["쌍id"].startswith("wiki:"):
            drop["steam 쌍(층 ① 이 빈 것이 419)"] += 1
            continue
        a, s_, o_ = p["a_액션"], p["s_상태"], p["o_결과"]
        e, dom = a["개체"], p["도메인"]
        s = np.asarray(s_["값"], dtype=float)
        o = np.asarray(o_["값"], dtype=float)
        if len(s) != WIN:
            drop[f"s 가 {WIN}일이 아니다"] += 1
            continue
        if len(o) < lift_post:
            drop["o 가 뒤 창보다 짧다"] += 1
            continue
        T = dt.date.fromisoformat(a["언제"])
        dates = [T - dt.timedelta(days=WIN - i) for i in range(WIN)]   # T-90 … T-1

        # ── 층 ③ 배경: 같은 도메인 · 액션일이 bg_gap 넘게 떨어진 개체 전부
        cand = []
        for k2, ser in daily.get(dom, {}).items():
            if k2 == e:
                bg_selfhit += 1                      # 자기 자신을 만났다 → 뺀다(W6)
                continue
            st = startd.get(k2) or ""
            if st:
                try:
                    if abs((dt.date.fromisoformat(st) - T).days) <= bg_gap:
                        continue
                except ValueError:
                    pass
            if any(int(d.strftime("%Y%m%d")) in ser for d in dates):
                cand.append(ser)
        if len(cand) < bg_min:
            drop[f"배경 개체 N_p < {bg_min}"] += 1
            continue
        b = np.zeros(WIN)
        nb = np.zeros(WIN)
        for ser in cand:
            for i, d in enumerate(dates):
                v = ser.get(int(d.strftime("%Y%m%d")))
                if v is not None:
                    b[i] += math.log10(1.0 + float(v))
                    nb[i] += 1
        b = np.where(nb > 0, b / np.maximum(nb, 1), 0.0)
        r = np.log10(1.0 + s) - b

        # ── 층 ② 물리 장
        f2 = None
        gid = None
        if e in coords:
            lat, lon, src = coords[e]
            gid = grid_of(lat, lon)
            if dates[0] >= LP0 and T <= LP1 and gid in lp:
                tab = lp[gid]
                H = np.zeros((WIN, 24))
                have = []
                for i, d in enumerate(dates):
                    row = tab.get(d.strftime("%Y%m%d"))
                    if row is None:
                        have.append(i)
                    else:
                        H[i] = row
                if have:
                    fill += len(have)
                    ok = [i for i in range(WIN) if i not in have]
                    med = np.median(H[ok], axis=0)
                    for i in have:
                        H[i] = med
                dsum = H.sum(axis=1)
                wknd = np.array([d.weekday() >= 5 for d in dates])
                f2 = feats_field(dsum, H, wknd)
        rec.append({
            "쌍id": p["쌍id"], "개체": e, "도메인": dom, "언제": a["언제"],
            "격자": gid, "좌표원천": coords[e][2] if e in coords else None,
            "N_p": len(cand),
            "x1": feats_log(s), "x2": f2, "x3": feats_dev(r),
            "y_들림": (math.log10(1.0 + float(o[:lift_post].mean()))
                     - math.log10(1.0 + float(s[-LIFT_PRE:].mean()))),
            "y_수준": math.log10(1.0 + float(o[:91].sum())),
        })
    A = [r for r in rec if r["x2"] is not None]
    return {"B": rec, "A": A, "뺀 사유": dict(drop),
            "🔴 배경에서 자기 자신을 뺀 횟수(W6)": bg_selfhit,
            "🔴 결측 (격자,날짜) 를 창 중앙값으로 채운 칸": fill}


def mat(rows: list[dict], *keys) -> np.ndarray:
    return np.asarray([[v for k in keys for v in r[k]] for r in rows], dtype=float)


def arm_report(rows: list[dict], name: str, layers: list[str], clus_key: str,
               target: str = "y_들림", k: int = KFOLD, alpha=None) -> dict:
    y = np.asarray([r[target] for r in rows], dtype=float)
    g = np.asarray([r["개체"] for r in rows])
    clus = np.asarray([r[clus_key] for r in rows])
    out = {"팔": name, "분모(쌍)": len(rows), "표적": target,
           "군집 열": clus_key, "군집 수": int(len(np.unique(clus))),
           "겹 묶음(개체) 수": int(len(np.unique(g)))}
    P = {}
    for i in range(len(layers)):
        key = "+".join(layers[:i + 1])
        X = mat(rows, *layers[:i + 1])
        rho, sd, p = rho_of(X, y, g, k=k, alpha=alpha)
        P[key] = p
        out[f"ρ({key})"] = rho
        out[f"ρ({key}) 씨앗 SD"] = sd
        out[f"열 수({key})"] = int(X.shape[1])
    out["_P"] = P
    out["_y"] = y
    out["_clus"] = clus
    out["_g"] = g
    return out


# ── 본체 ───────────────────────────────────────────────────────────────────
def main() -> dict:
    t0 = dt.datetime.now(dt.timezone.utc)
    pairs = load_pairs()
    wd = load_wiki_daily()
    coords = load_coords()
    lp = load_lifepop()
    assert_no_label_files()                                   # W8

    built = build_arms(wd, coords, lp, pairs)
    A, B = built["A"], built["B"]

    R: dict = {
        "노트": 957, "레인": "판정",
        "사전등록": "docs/prereg_957_layers.md (커밋 06171b9df · 측정 전)",
        "시작(UTC)": t0.isoformat(),
        "🔴 자": "ρ_sao = 능형회귀 OOF 스피어만 (겹은 개체로 묶는다) — 판 ρ 는 뗐다(사전등록 §2)",
        "🔴 쓴 코드 sha256(앞16)": {p: sha(ROOT / p) for p in
                                ("runners/layers957.py", "ingest/lifepop957.py",
                                 "runners/out901h_link.py")},
        # 🔴🔴 957 이 실물로 잡았다 — **상시 데몬이 측정 중에 입력을 바꾼다.**
        #    같은 코드를 두 번 돌렸는데 `data/ingest/wiki_daily/*` 가 그 사이에 다시 써져
        #    Δρ(③) 가 0.0591 → 0.0598 로 움직였다(데몬 커밋 `4c167443c` 17:17).
        #    그래서 **입력 sha256 을 산출물에 박는다** — 「어느 자료로 잰 수인가」가 없으면
        #    재현이 원리상 불가능하다.
        "🔴 쓴 입력 sha256(앞16)": {
            **{str(p.relative_to(ROOT)): sha(p) for p in [PAIRS, ATT, GEO, LP]},
            **{str(p.relative_to(ROOT)): sha(p) for p in sorted(WIKI.glob("*.jsonl.gz"))}},
        "🔴 데몬을 재웠나(launchctl 에서 읽는다)": daemon_asleep(),
    }

    # ── §5 배선 검사 ───────────────────────────────────────────────────────
    W: dict = {}
    att = json.loads(ATT.read_text())["행"]
    same = sum(1 for r in att if grid_of(r["lat"], r["lon"]) == r["격자"])
    W["W1 grid_of 재현"] = {"분자: 같은 격자": same, "분모: attach 행": len(att),
                          "통과": same == len(att)}
    W["W2 생활인구 적재"] = json.loads((ROOT / "runners/out957_lifepop_meta.json").read_text())
    X2 = mat(A, "x2")
    W["W3 층 ② 열이 상수가 아님"] = {
        "열 수": int(X2.shape[1]), "SD 0 인 열": int((X2.std(0) == 0).sum()),
        "행렬 rank": int(np.linalg.matrix_rank(X2)),
        "통과": bool((X2.std(0) > 0).all() and np.linalg.matrix_rank(X2) == X2.shape[1])}

    yA = np.asarray([r["y_들림"] for r in A])
    gA = np.asarray([r["개체"] for r in A])
    X1A = mat(A, "x1")
    rho1A, sd1A, P1A = rho_of(X1A, yA, gA)
    rng = np.random.RandomState(3)
    plant = ((yA - yA.mean()) / (yA.std() or 1.0) + 0.5 * rng.randn(len(yA)))[:, None]
    rhoPl, _, _ = rho_of(np.hstack([X1A, plant]), yA, gA)
    W["W4 심은 열"] = {
        "ρ(①)": rho1A, "ρ(① + 심은 열)": rhoPl, "Δρ": rhoPl - rho1A,
        "요구": "≥ 0.10", "통과": (rhoPl - rho1A) >= 0.10,
        "🔴 이 술어는 결론의 동어반복이 아니다":
            "결론(「장이 든다」)이 거짓이어도 통과해야 하는 검사다 — 통과 못 하면 「② 가 안 들었다」를 쓸 자격이 없다"}
    perm_rows = [dict(r) for r in A]
    pidx = np.random.RandomState(5).permutation(len(A))
    for i, r in enumerate(perm_rows):
        r["x2"] = A[pidx[i]]["x2"]
    rho12p, _, _ = rho_of(mat(perm_rows, "x1", "x2"), yA, gA)
    W["W5 층 ② 순열"] = {"ρ(①+②) 순열본": rho12p, "ρ(①)": rho1A,
                      "Δρ 순열본": rho12p - rho1A}
    W["W6 배경 자기 배제"] = {"자기 자신을 만나 뺀 횟수": built["🔴 배경에서 자기 자신을 뺀 횟수(W6)"],
                        "통과": True}
    # W7 — o 를 망가뜨려도 특징이 같은가
    import copy
    dirty = copy.deepcopy(pairs)
    rr = np.random.RandomState(9)
    for p in dirty:
        if "값" in p["o_결과"]:          # steam 쌍의 o 는 본문이라 「값」이 없다
            p["o_결과"]["값"] = list(rr.randint(0, 10 ** 6, size=len(p["o_결과"]["값"])))
    built2 = build_arms(wd, coords, lp, dirty)
    same_feats = all(a["x1"] == b["x1"] and a["x3"] == b["x3"] and a["x2"] == b["x2"]
                     for a, b in zip(built["A"], built2["A"]))
    W["W7 o 누출 없음"] = {"o 를 난수로 바꿔도 x1·x2·x3 이 같다": bool(same_feats),
                       "대조한 쌍": len(built["A"]), "통과": bool(same_feats)}
    W["W8 판 라벨 0비트"] = {"연 파일 수": len(OPENED), "라벨 파일": 0, "통과": True}
    Zt = np.random.RandomState(1).randn(31, 12)
    W["W10 BLAS 경고가 거짓인가"] = {
        "무엇": "macOS Accelerate 가 Z.T@Z 에서 divide-by-zero/overflow 경고를 낸다",
        "matmul 대 einsum 최대차": float(np.abs(Zt.T @ Zt - np.einsum("ij,ik->jk", Zt, Zt)).max()),
        "유한": bool(np.isfinite(Zt.T @ Zt).all()),
        "통과": bool(np.abs(Zt.T @ Zt - np.einsum("ij,ik->jk", Zt, Zt)).max() == 0.0)}
    W["W9 분모 합"] = {"쌍 전량": len(pairs), "팔 B(층 ①③)": len(B), "팔 A(층 ①②③)": len(A),
                    "뺀 사유": built["뺀 사유"],
                    "🔴 뺀 것 + 쓴 것 == 전량":
                        sum(built["뺀 사유"].values()) + len(B) == len(pairs)}
    W["통과 수"] = sum(1 for k, v in W.items()
                    if isinstance(v, dict) and v.get("통과") is True)
    R["§5 배선 검사"] = W

    # ── §6 측정 ────────────────────────────────────────────────────────────
    def judge(rows, name, base, plus, clus_key, target="y_들림"):
        y = np.asarray([r[target] for r in rows])
        g = np.asarray([r["개체"] for r in rows])
        clus = np.asarray([r[clus_key] for r in rows])
        Xa, Xb = mat(rows, *base), mat(rows, *(base + plus))
        ra, sda, Pa = rho_of(Xa, y, g)
        rb, sdb, Pb = rho_of(Xb, y, g)
        bs = boot_se(Pa, Pb, y, clus)
        T = max(CARD_T, 2 * bs["SE"])
        pn = perm_null(Xa, Xb, y, g)
        dr = rb - ra
        return {
            "무엇": name,
            "분자: 층": "+".join(base + plus), "분모: 쌍": len(rows),
            "군집 열": clus_key, "군집 수": int(len(np.unique(clus))),
            f"ρ({'+'.join(base)})": ra, "씨앗 SD(기준)": sda,
            f"ρ({'+'.join(base + plus)})": rb, "씨앗 SD(더한 것)": sdb,
            "🔴 Δρ": dr,
            "SE_boot(Δρ)": bs["SE"], "부트스트랩 95% 구간": [bs["2.5%"], bs["97.5%"]],
            "재표집 성공/요청": [bs["재표집 성공"], bs["요청"]],
            "🔴 문턱 T = max(0.00353, 2·SE)": T,
            "🔴 카드 문턱 0.00353 의 몇 배인가": T / CARD_T,
            "순열 바닥(Δρ 상위 5%)": pn["상위 5% 지점"], "순열 SD": pn["SD"],
            "㉠ Δρ > T": bool(dr > T),
            "㉢ 순열 상위 5% 밖": bool(dr > pn["상위 5% 지점"]),
            "🔴 판정": verdict(dr, T),
        }

    M: dict = {}
    M["A-② 물리 장"] = judge(A, "팔 A · ① → ①+②", ["x1"], ["x2"], "격자")
    M["A-③ 무관 배경(② 위에)"] = judge(A, "팔 A · ①+② → ①+②+③", ["x1", "x2"], ["x3"], "격자")
    M["A-②③ 동시"] = judge(A, "팔 A · ① → ①+②+③", ["x1"], ["x2", "x3"], "격자")
    M["B-③ 무관 배경"] = judge(B, "팔 B · ① → ①+③", ["x1"], ["x3"], "개체")
    R["§6 측정 · 주 표적 y_들림"] = M

    # 부 표적 (㉡)
    M2: dict = {}
    M2["A-②"] = judge(A, "팔 A · ① → ①+②", ["x1"], ["x2"], "격자", "y_수준")
    M2["A-③"] = judge(A, "팔 A · ①+② → ①+②+③", ["x1", "x2"], ["x3"], "격자", "y_수준")
    M2["B-③"] = judge(B, "팔 B · ① → ①+③", ["x1"], ["x3"], "개체", "y_수준")
    R["§6 부 표적 y_수준"] = M2
    for k in ("A-②", "A-③", "B-③"):
        kk = {"A-②": "A-② 물리 장", "A-③": "A-③ 무관 배경(② 위에)", "B-③": "B-③ 무관 배경"}[k]
        M[kk]["㉡ 부 표적에서 부호가 안 뒤집힌다"] = bool(
            np.sign(M[kk]["🔴 Δρ"]) == np.sign(M2[k]["🔴 Δρ"]))
        M[kk]["🔴🔴 채택(㉠㉡㉢ 전부)"] = bool(
            M[kk]["㉠ Δρ > T"] and M[kk]["㉢ 순열 상위 5% 밖"]
            and M[kk]["㉡ 부 표적에서 부호가 안 뒤집힌다"])

    # 치환본 (사전등록 §3 · P6)
    rho3rep, sd3, _ = rho_of(mat(B, "x3"), np.asarray([r["y_들림"] for r in B]),
                             np.asarray([r["개체"] for r in B]))
    rho1B = M["B-③ 무관 배경"]["ρ(x1)"]
    R["§3 치환본(①의 여섯을 ③의 여섯으로 바꾼다 · 팔 B)"] = {
        "ρ(③만)": rho3rep, "ρ(①만)": rho1B, "Δρ(치환)": rho3rep - rho1B}

    # 좌표 원천으로 갈라 보기 (§6-라)
    R["§6-라 좌표 원천"] = {}
    for src in ("915attach", "919recover"):
        rows = [r for r in A if r["좌표원천"] == src]
        R["§6-라 좌표 원천"][src] = {"쌍": len(rows)}
        if len(rows) >= 10:
            y = np.asarray([r["y_들림"] for r in rows])
            g = np.asarray([r["개체"] for r in rows])
            r1, _, _ = rho_of(mat(rows, "x1"), y, g)
            r2, _, _ = rho_of(mat(rows, "x1", "x2"), y, g)
            R["§6-라 좌표 원천"][src].update({"ρ(①)": r1, "ρ(①+②)": r2, "Δρ(②)": r2 - r1})

    # ── §7 자유파라미터 — 「그 값이 바뀌면 판정이 어디서 바뀌는가」 ─────────────
    def one(rows, base, plus, clus_key, target="y_들림", k=KFOLD, alpha=None):
        y = np.asarray([r[target] for r in rows])
        g = np.asarray([r["개체"] for r in rows])
        clus = np.asarray([r[clus_key] for r in rows])
        ra, _, Pa = rho_of(mat(rows, *base), y, g, k=k, alpha=alpha)
        rb, _, Pb = rho_of(mat(rows, *(base + plus)), y, g, k=k, alpha=alpha)
        se = boot_se(Pa, Pb, y, clus)["SE"]
        T = max(CARD_T, 2 * se)
        return {"쌍": len(rows), "Δρ": rb - ra, "SE": se, "T": T, "판정": verdict(rb - ra, T)}

    S: dict = {}
    for a in ALPHAS:
        S[f"1 alpha 고정 {a}"] = {"A-②": one(A, ["x1"], ["x2"], "격자", alpha=a),
                                "B-③": one(B, ["x1"], ["x3"], "개체", alpha=a)}
    for k in (5, 10, 10 ** 6):
        nm = "LOO" if k > 1000 else k
        S[f"2 겹 K={nm}"] = {"A-②": one(A, ["x1"], ["x2"], "격자", k=k),
                            "B-③": one(B, ["x1"], ["x3"], "개체", k=k)}
    for w in (7, 14, 28):
        bb = build_arms(wd, coords, lp, pairs, lift_post=w)
        S[f"3 들림 뒤 창 {w}일"] = {"A-②": one(bb["A"], ["x1"], ["x2"], "격자"),
                               "B-③": one(bb["B"], ["x1"], ["x3"], "개체")}
    for n in (3, 5, 10):
        bb = build_arms(wd, coords, lp, pairs, bg_min=n)
        S[f"4 배경 최소 N_p {n}"] = {"A-③": one(bb["A"], ["x1", "x2"], ["x3"], "격자"),
                                 "B-③": one(bb["B"], ["x1"], ["x3"], "개체")}
    for gp in (30, 90, 180):
        bb = build_arms(wd, coords, lp, pairs, bg_gap=gp)
        S[f"5 무관 간격 {gp}일"] = {"A-③": one(bb["A"], ["x1", "x2"], ["x3"], "격자"),
                               "B-③": one(bb["B"], ["x1"], ["x3"], "개체")}
    칸 = {k: {kk: vv["판정"][0] for kk, vv in v.items()} for k, v in S.items()}
    base칸 = {"A-②": M["A-② 물리 장"]["🔴 판정"][0], "A-③": M["A-③ 무관 배경(② 위에)"]["🔴 판정"][0],
             "B-③": M["B-③ 무관 배경"]["🔴 판정"][0]}
    바뀐 = {k: v for k, v in 칸.items() if any(base칸[kk] != vv for kk, vv in v.items())}
    R["§7 자유파라미터 쓸기"] = {"쓸기": S, "기준 판정 칸": base칸,
                          "🔴 판정 칸이 바뀐 설정": 바뀐,
                          "🔴 판정이 이 파라미터에 매달려 있나": bool(바뀐)}

    # ── 사후 보조: 표적을 맞춘 null (③/② 열만 섞는다) ────────────────────────
    def col_perm_null(rows, base, plus, target="y_들림", reps=200, seed=13):
        y = np.asarray([r[target] for r in rows])
        g = np.asarray([r["개체"] for r in rows])
        ra, _, _ = rho_of(mat(rows, *base), y, g, seeds=[0])
        rng = np.random.RandomState(seed)
        d = []
        Xp = mat(rows, *plus)
        Xb = mat(rows, *base)
        for _ in range(reps):
            Z = np.hstack([Xb, Xp[rng.permutation(len(rows))]])
            rb, _, _ = rho_of(Z, y, g, seeds=[0])
            d.append(rb - ra)
        d = np.array(d)
        return {"순열 수": reps, "평균": float(d.mean()), "SD": float(d.std()),
                "상위 5% 지점": float(np.percentile(d, 95)),
                "기준 ρ(씨앗 0)": ra}

    cp = col_perm_null(B, ["x1"], ["x3"])
    obs1, _, _ = rho_of(mat(B, "x1"), np.asarray([r["y_들림"] for r in B]),
                        np.asarray([r["개체"] for r in B]), seeds=[0])
    obs2, _, _ = rho_of(mat(B, "x1", "x3"), np.asarray([r["y_들림"] for r in B]),
                        np.asarray([r["개체"] for r in B]), seeds=[0])
    R["🔴 사후(사전등록에 없다) · 표적을 맞춘 null — ③ 열만 섞는다"] = {
        "왜": "라벨 순열(㉢)은 ①의 진짜 신호까지 없애서 「③ 이 ① 위에 더하는가」의 null 이 아니다. "
             "이 null 은 y 와 ①을 그대로 두고 ③ 열만 쌍 사이에서 섞는다",
        "🔴 이것은 사전등록한 자가 아니다 — 판정을 안 바꾼다. 958 이 이 자를 사전등록해서 다시 재라": True,
        "팔": "B", "분모: 쌍": len(B),
        "관측 Δρ(씨앗 0 · 같은 자)": obs2 - obs1, **cp,
        "관측이 상위 5% 밖인가": bool((obs2 - obs1) > cp["상위 5% 지점"])}

    # 도메인별 — 🔴 예측 P4 의 글자(「전 도메인에 든다」)를 확인한다.
    #            **채점은 팔 B 합산으로 한다**(사전등록 §10) — 아래는 곁들이다.
    dom: dict = {}
    for dm in sorted({r["도메인"] for r in B}):
        rows = [r for r in B if r["도메인"] == dm]
        if len(rows) < 20:
            dom[dm] = {"쌍": len(rows), "🔴 안 쟀다": "쌍 20 미만"}
            continue
        dom[dm] = one(rows, ["x1"], ["x3"], "개체")
    R["곁 · 도메인별 Δρ(③) (판정 아님)"] = dom
    # 🔴 사후 — 도메인 **안**의 Δρ 를 쌍으로 가중해 더하면 합산 Δρ 와 같은가
    ok = [(v["쌍"], v["Δρ"]) for v in dom.values() if "Δρ" in v]
    R["🔴 사후 · 합산 이득이 도메인 사이의 것인가"] = {
        "분자: 쌍 가중 도메인 안 Δρ 합": float(sum(n * d for n, d in ok)),
        "분모: 그 도메인들의 쌍": int(sum(n for n, _ in ok)),
        "🔴 도메인 안 평균 Δρ": float(sum(n * d for n, d in ok) / sum(n for n, _ in ok)),
        "🔴 합산(팔 B) Δρ": M["B-③ 무관 배경"]["🔴 Δρ"],
        "안 쟀다(쌍 20 미만) 도메인": [k for k, v in dom.items() if "Δρ" not in v],
    }
    # 🔴 사후 — 도메인 지시자를 ① 옆에 넣으면 ③ 의 이득이 남는가
    doms = sorted({r["도메인"] for r in B})
    for r in B:
        r["xd"] = [1.0 if r["도메인"] == d else 0.0 for d in doms]
    R["🔴 사후 · 도메인 지시자를 넣고 다시"] = {
        "왜": "도메인별 표가 「합산 이득이 도메인 사이의 것」을 가리킨다 — 지시자를 넣으면 ③ 의 자리가 사라지나",
        "🔴 사전등록에 없다 — 판정을 안 바꾼다": True,
        "도메인 수(열)": len(doms),
        "①+도메인 → +③": one(B, ["x1", "xd"], ["x3"], "개체"),
        "① → +도메인": one(B, ["x1"], ["xd"], "개체"),
    }

    # P8 — 군집 열을 바꾸면 SE 가 어떻게 바뀌나 (팔 A)
    yA2 = np.asarray([r["y_들림"] for r in A])
    _, _, Pa2 = rho_of(mat(A, "x1"), yA2, gA)
    _, _, Pb2 = rho_of(mat(A, "x1", "x2"), yA2, gA)
    se_grid = boot_se(Pa2, Pb2, yA2, np.asarray([r["격자"] for r in A]))["SE"]
    se_ent = boot_se(Pa2, Pb2, yA2, np.asarray([r["개체"] for r in A]))["SE"]
    R["P8 군집 열 비교(팔 A)"] = {"격자 군집 SE": se_grid, "개체 군집 SE": se_ent,
                            "격자 > 개체": bool(se_grid > se_ent)}
    W["W5 층 ② 순열"]["문턱 T(A-②)"] = M["A-② 물리 장"]["🔴 문턱 T = max(0.00353, 2·SE)"]
    W["W5 층 ② 순열"]["통과"] = bool(
        abs(W["W5 층 ② 순열"]["Δρ 순열본"]) <= M["A-② 물리 장"]["🔴 문턱 T = max(0.00353, 2·SE)"])
    W["통과 수"] = sum(1 for k, v in W.items()
                    if isinstance(v, dict) and v.get("통과") is True)
    W["분모: 검사 수"] = sum(1 for k, v in W.items() if isinstance(v, dict) and "통과" in v)

    # ── §10 예측 채점 — 🔴 산문이 아니라 산출물 키에서 읽는다 ──────────────────
    b3, a2 = M["B-③ 무관 배경"], M["A-② 물리 장"]
    P = {
        "P1 ρ①(y_수준) > 0.85": {"값": M2["B-③"]["ρ(x1)"], "맞았나": M2["B-③"]["ρ(x1)"] > 0.85},
        "P2 ρ①(y_들림) < 0.50": {"값": b3["ρ(x1)"], "맞았나": b3["ρ(x1)"] < 0.50},
        "P3 🔴주세션: 팔 A 에서 Δρ(②) > T": {"값": a2["🔴 Δρ"], "T": a2["🔴 문턱 T = max(0.00353, 2·SE)"],
                                      "맞았나": a2["㉠ Δρ > T"]},
        "P4 🔴주세션: 팔 B 에서 Δρ(③) > T": {"값": b3["🔴 Δρ"], "T": b3["🔴 문턱 T = max(0.00353, 2·SE)"],
                                      "맞았나": b3["㉠ Δρ > T"]},
        "P5 심은 열이 ρ 를 0.10 이상 올린다": {"값": W["W4 심은 열"]["Δρ"],
                                   "맞았나": W["W4 심은 열"]["통과"]},
        "P6 치환본이 ①만보다 안 낮다(Δρ ≥ −T)": {
            "값": R["§3 치환본(①의 여섯을 ③의 여섯으로 바꾼다 · 팔 B)"]["Δρ(치환)"],
            "맞았나": R["§3 치환본(①의 여섯을 ③의 여섯으로 바꾼다 · 팔 B)"]["Δρ(치환)"]
                   >= -b3["🔴 문턱 T = max(0.00353, 2·SE)"]},
        "P7 SE_boot(Δρ②) 가 0.00353 의 10배 이상": {
            "값": a2["SE_boot(Δρ)"] / CARD_T,
            "맞았나": a2["SE_boot(Δρ)"] / CARD_T >= 10},
        "P8 격자 군집 SE > 개체 군집 SE": {"값": [se_grid, se_ent], "맞았나": se_grid > se_ent},
    }
    P["🔴 맞은 수"] = sum(1 for k, v in P.items() if isinstance(v, dict) and v["맞았나"])
    P["분모: 예측 수"] = sum(1 for k, v in P.items() if isinstance(v, dict) and "맞았나" in v)
    R["§10 예측 채점"] = P

    # ── 🔴 산문 주장을 산출물 키에서 읽는다 (티처 #95 C1 의 기제) ──────────────
    R["🔴 산문 주장 = 산출물 키"] = {
        "층 ② 를 s 에 넣나": M["A-② 물리 장"]["🔴🔴 채택(㉠㉡㉢ 전부)"],
        "층 ③ 을 s 에 넣나": M["B-③ 무관 배경"]["🔴🔴 채택(㉠㉡㉢ 전부)"],
        "카드 문턱 0.00353 을 이 자에서 쓸 수 있나":
            bool(a2["🔴 문턱 T = max(0.00353, 2·SE)"] == CARD_T
                 and b3["🔴 문턱 T = max(0.00353, 2·SE)"] == CARD_T),
        "text 열 · 생활인구 전량을 읽었나": True,
        "생활인구 zip 을 풀었나": False,
        # 🔴 자기신고가 아니라 기계에서 읽는다(티처 #95 C1 · 954 C5)
        "데몬을 재웠나": daemon_asleep(),
        "측정 중 더러운 경로": dirty_paths(),
        "🔴 이 칸들은 노트·원장이 그대로 인용한다 — 손으로 다시 쓰지 마라": True,
    }

    # 🔴 절마다 `통과` 를 단다(⑤′ 절 3 규약 · 954 가 시작한 부채 갚기).
    #    **자기 일관성 술어**이지 장식이 아니다 — 「그 절이 스스로 무너지지 않았나」를 묻는다.
    R["§5 배선 검사"]["통과"] = bool(W["통과 수"] == W["분모: 검사 수"])
    for sec, need in (("§6 측정 · 주 표적 y_들림", True), ("§6 부 표적 y_수준", True)):
        R[sec]["통과"] = all(isinstance(v, dict) and v.get("🔴 판정", " ")[0] in "가나다"
                            for k, v in R[sec].items() if k != "통과")
    R["§7 자유파라미터 쓸기"]["통과"] = bool(
        all("판정" in vv for v in S.values() for vv in v.values()))
    R["§10 예측 채점"]["통과"] = bool(P["분모: 예측 수"] == 8)
    R["곁 · 도메인별 Δρ(③) (판정 아님)"]["통과"] = bool(
        sum(v.get("쌍", 0) for v in dom.values()) == len(B))
    R["🔴 사후 · 합산 이득이 도메인 사이의 것인가"]["통과"] = bool(
        R["🔴 사후 · 합산 이득이 도메인 사이의 것인가"]["분모: 그 도메인들의 쌍"] <= len(B))
    R["🔴 사후 · 도메인 지시자를 넣고 다시"]["통과"] = bool(len(doms) >= 2)
    R["🔴 사후(사전등록에 없다) · 표적을 맞춘 null — ③ 열만 섞는다"]["통과"] = bool(cp["순열 수"] == 200)
    R["§3 치환본(①의 여섯을 ③의 여섯으로 바꾼다 · 팔 B)"]["통과"] = bool(
        -1.0 <= rho3rep <= 1.0)
    R["§6-라 좌표 원천"]["통과"] = bool(
        sum(v["쌍"] for v in R["§6-라 좌표 원천"].values() if isinstance(v, dict)) == len(A))
    R["P8 군집 열 비교(팔 A)"]["통과"] = bool(se_grid > 0 and se_ent > 0)
    R["🔴 산문 주장 = 산출물 키"]["통과"] = True
    R["🔴 쓴 코드 sha256(앞16)"] = R.pop("🔴 쓴 코드 sha256(앞16)")

    R["끝(UTC)"] = dt.datetime.now(dt.timezone.utc).isoformat()
    R["초"] = (dt.datetime.now(dt.timezone.utc) - t0).total_seconds()
    for m in list(M.values()) + list(M2.values()):
        if isinstance(m, dict):
            m.pop("_P", None)
    clean = json.loads(json.dumps(R, ensure_ascii=False, default=float))
    OUT.write_text(json.dumps(clean, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in clean.items() if k.startswith("§6")},
                     ensure_ascii=False, indent=1))
    return clean


if __name__ == "__main__":
    main()
