# -*- coding: utf-8 -*-
"""노트 971 — **유보에서 예측 성능을 잰다** · 판 도메인별 Δ · 자를 자기 러너에.

사전등록: `docs/prereg_971_holdout.md` (측정 전 단독 커밋 `42ac6b031`).

🔴 **저장소 `lab/*.py` 를 한 바이트도 안 고친다.** `WIKI_DROP`/`TREND_DROP` 은
**메모리 안에서만** 비운다. `--out` 필수 · 쓰기 문지기가 그 파일 하나만 허용한다.

🔴 **검사는 전부 「작은 최상위 함수 + 인자」 꼴이다**(조항 64 · 66-④).
970 의 `wiring(P)` 는 뿌리가 `P` 딕트 하나라 자 B 의 생성기가 유효 입력에
원리상 못 닿았고 **모른다 5/6(83.3%)** 가 났다. 여기서는 뿌리가 **스칼라**다.

단계: `wiring` → `predict` → `board`.
"""
import argparse
import builtins
import datetime as dt
import glob
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
os.chdir(str(ROOT))

T = 2025.0
SEEDS = 12
RHO0 = 0.47034252170476804
BOARD_SE = 0.000603
DIAG_NOISE_1COL = 0.01055
DIAG_OPS = 0.00353

#: 🔴 사전등록 §3-가 가 못 박은 상수. **측정 중에 안 고친다.**
N_MIN_TRAIN = 20
N_MIN_HOLD = 20
RIDGE = 1e-6
BOOT = 2000
BOOT_SEED = 971
RAND_DRAWS = 50
RAND_SEED0 = 971000

#: 🔴 이 사이클에서 내가 돌린 러너 전부. F1 이 이 목록을 커밋 blob 과 대조한다.
#: 🔴 **자기 자신이 첫째다**(조항 66-⑥).
RAN = ("runners/predict971.py", "runners/dropaudit969.py",
       "runners/meta965.py", "runners/recommit970.py")


def _now() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ── 쓰기 문지기 ───────────────────────────────────────────────────────
class NoWrite:
    def __init__(self, allow=()):
        self.allow = {str(Path(a).resolve()) for a in allow}
        self.blocked = []

    def _ok(self, p) -> bool:
        try:
            return str(Path(p).resolve()) in self.allow
        except Exception:                                          # noqa: BLE001
            return False

    def _g_open(self, orig):
        def f(file, mode="r", *a, **k):
            if any(c in str(mode) for c in "wxa+") and not self._ok(file):
                self.blocked.append(str(file))
                raise PermissionError("문지기: 쓰기 금지 %s" % file)
            return orig(file, mode, *a, **k)
        return f

    def _g_path_open(self, orig):
        def f(self2, mode="r", *a, **k):
            if any(c in str(mode) for c in "wxa+") and not self._ok(self2):
                self.blocked.append(str(self2))
                raise PermissionError("문지기: 쓰기 금지 %s" % self2)
            return orig(self2, mode, *a, **k)
        return f

    def _g_path_write(self, orig):
        def f(self2, *a, **k):
            self.blocked.append(str(self2))
            raise PermissionError("문지기: 쓰기 금지 %s" % self2)
        return f

    def _g_os1(self, orig):
        def f(path, *a, **k):
            self.blocked.append(str(path))
            raise PermissionError("문지기: 쓰기 금지 %s" % path)
        return f

    def __enter__(self):
        self._o = (builtins.open, Path.open, Path.write_text, Path.write_bytes,
                   os.remove, os.unlink)
        builtins.open = self._g_open(self._o[0])
        Path.open = self._g_path_open(self._o[1])
        Path.write_text = self._g_path_write(self._o[2])
        Path.write_bytes = self._g_path_write(self._o[3])
        os.remove = self._g_os1(self._o[4])
        os.unlink = self._g_os1(self._o[5])
        return self

    def __exit__(self, *e):
        (builtins.open, Path.open, Path.write_text, Path.write_bytes,
         os.remove, os.unlink) = self._o
        return False


# ── 도장 ─────────────────────────────────────────────────────────────
def _sha_file(p) -> str:
    """🔴 **자르지 않는다.**"""
    h = hashlib.sha256()
    with open(str(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def code_stamp() -> dict:
    """🔴 **F2** --- 내가 돌린 러너 전부 + `lab/*.py` 전량을 덮는다."""
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): _sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def stamp_digest(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True,
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def _git(*a) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotePath=false"] + list(a),
                          capture_output=True).stdout


def blob_sha(ref: str, path: str):
    """🔴 커밋된 **내용**의 sha256(= `_sha_file` 과 같은 자). git object id 가 아니다."""
    r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-p", "%s:%s" % (ref, path)],
                       capture_output=True)
    if r.returncode != 0:
        return None
    return hashlib.sha256(r.stdout).hexdigest()


def ran_vs_blob(ref: str) -> dict:
    """🔴🔴 **F1** --- 내가 돌린 러너 전부의 디스크 sha 를 커밋 blob 과 대조한다.

    🔴 **`--ref` 는 고정 sha 여야 한다**(티처 #109 m2) --- 움직이는 가지 이름을 주면
    세 산출물의 기준 커밋이 서로 다른 것을 가리킨다.
    """
    per, bad = {}, []
    for p in RAN:
        d = _sha_file(ROOT / p) if (ROOT / p).is_file() else None
        b = blob_sha(ref, p)
        ok = bool(d is not None and d == b)
        per[p] = {"디스크 sha256": d, "커밋 blob sha256": b, "일치": ok}
        if not ok:
            bad.append(p)
    fixed = bool(len(ref) >= 7 and all(c in "0123456789abcdef" for c in ref.lower()))
    return {"기준 ref(준 대로)": ref,
            "🔴 F11 --- ref 가 고정 sha 인가(움직이는 가지 이름이 아닌가)": fixed,
            "기준 커밋": _git("rev-parse", ref).decode().strip(),
            "러너별": per,
            "🔴 분자/분모": "%d / %d" % (len(RAN) - len(bad), len(RAN)),
            "🔴 어긋난 러너": bad,
            "🔴 F1 통과": bool(not bad and fixed),
            "🔴 어떤 입력이면 떨어지나":
                "러너 파일을 한 바이트만 고치고 커밋을 안 하면 그 줄이 곧 거짓이 된다. "
                "`--ref` 에 가지 이름을 주면 F11 이 떨어진다"}


# ══════════════════════════════════════════════════════════════════════
# 자·모형 — 🔴 유보 예측
# ══════════════════════════════════════════════════════════════════════
def spear(a, b) -> float:
    """스피어만. 🔴 `state.rank_test.spearman` 과 같은 자를 쓴다."""
    from state.rank_test import spearman
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 3:
        return float("nan")
    return float(spearman(a[ok], b[ok]))


def card(v) -> int:
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    return int(len(np.unique(np.round(v, 12))))


def fit_predict(Xtr, ytr, Xho, lam=RIDGE):
    """🔴🔴 **유보의 어떤 통계도 안 받는다** --- 인자에 `y_ho` 가 **없다**.

    학습 평균·SD 로 표준화하고 능형 최소제곱으로 계수를 얻어 유보에 적용한다.
    """
    Xtr = np.asarray(Xtr, float).reshape(len(Xtr), -1)
    Xho = np.asarray(Xho, float).reshape(len(Xho), -1)
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0)
    sd = np.where(sd > 0, sd, 1.0)
    Ztr = np.hstack([np.ones((len(Xtr), 1)), (Xtr - mu) / sd])
    Zho = np.hstack([np.ones((len(Xho), 1)), (Xho - mu) / sd])
    y = np.asarray(ytr, float)
    G = Ztr.T @ Ztr + lam * np.eye(Ztr.shape[1])
    beta = np.linalg.solve(G, Ztr.T @ y)
    return Zho @ beta, beta


# ── 배선 검사 --- 🔴 전부 「작은 최상위 함수 + 스칼라 인자」 ──────────
def w1_split(n_tr, n_ho, n_both, n_fin):
    """W1 학습/유보 분할기 --- 겹치지 않고 유한 행을 덮는가."""
    return {
        "🔴 입력별 값": {"학습": n_tr, "유보": n_ho, "겹침": n_both, "유한 행": n_fin},
        "🔴 어떤 입력이면 떨어지나":
            "겹침이 1 이라도 있으면 떨어진다. 학습+유보가 유한 행과 다르면 떨어진다",
        "통과": bool(n_both == 0 and n_tr + n_ho == n_fin and n_tr > 0 and n_ho > 0),
    }


def w2_recover(rho_signal, rho_noise, thr_hi, thr_lo):
    """W2 적합기 양성/음성 대조 --- 심은 신호는 잡고 순수 잡음은 못 잡는가."""
    return {
        "🔴 입력별 값": {"심은 신호 유보 ρ": rho_signal, "순수 잡음 유보 ρ": rho_noise,
                    "양성 문턱": thr_hi, "음성 문턱": thr_lo},
        "🔴 어떤 입력이면 떨어지나":
            "신호를 상수 열로 바꾸면 양성이 문턱 아래로 내려가 떨어진다. "
            "잡음 열에 결과를 섞으면 음성이 문턱 위로 올라가 떨어진다",
        "통과": bool(rho_signal > thr_hi and abs(rho_noise) < thr_lo),
    }


def w3_leak(max_abs_diff, tol):
    """🔴🔴 W3 누출 --- **유보 결과를 통째로 갈아도 예측이 안 바뀌는가.**

    이 검사가 이 사이클의 심장이다. 970 까지의 모든 ρ 는 같은 자료 안의 연관이라
    이 물음 자체가 없었다.
    """
    return {
        "🔴 입력별 값": {"y_유보 를 갈았을 때 예측의 최대 절대차": max_abs_diff, "허용": tol},
        "🔴 어떤 입력이면 떨어지나":
            "적합에 유보 행을 한 줄이라도 넣으면 예측이 갈려 최대 절대차가 커지고 떨어진다",
        "통과": bool(max_abs_diff <= tol),
    }


def w4_card(c_const, c_vary, gate):
    """W4 가짓수 게이트(조항 65-④) --- 상수 열은 통제로 못 쓴다."""
    return {
        "🔴 입력별 값": {"상수 열 가짓수": c_const, "변하는 열 가짓수": c_vary, "게이트": gate},
        "🔴 어떤 입력이면 떨어지나":
            "0.5 채움 열(가짓수 1)이 게이트를 넘으면 떨어진다. 게이트를 1 로 낮춰도 떨어진다",
        "통과": bool(c_const < gate <= c_vary),
    }


def w5_pool(pooled, pooled_flip, lo, hi):
    """W5 묶음 가중 --- 구간 안에 있고 **가중을 뒤바꾸면 값이 움직이는가**.

    🔴 가중을 안 보는 자(단순 평균)는 `pooled == pooled_flip` 이 되어 떨어진다.
    """
    return {
        "🔴 입력별 값": {"묶음": pooled, "가중 뒤바꾼 묶음": pooled_flip,
                    "구성 최소": lo, "구성 최대": hi},
        "🔴 어떤 입력이면 떨어지나":
            "가중을 무시하고 단순 평균을 내면 두 값이 같아져 떨어진다. "
            "구간 밖 값을 내도 떨어진다",
        "통과": bool(lo <= pooled <= hi and lo <= pooled_flip <= hi
                    and pooled != pooled_flip),
    }


def w6_boot(cover_true, cover_false, b_draws, b_min):
    """W6 짝 붓스트랩 --- 참값은 덮고 멀리 옮긴 값은 안 덮는가."""
    return {
        "🔴 입력별 값": {"참값을 덮나": cover_true, "옮긴 값을 덮나": cover_false,
                    "뽑기": b_draws, "최소 뽑기": b_min},
        "🔴 어떤 입력이면 떨어지나":
            "구간을 (−∞, ∞) 로 넓히면 옮긴 값도 덮여 떨어진다. 뽑기가 최소 아래면 떨어진다",
        "통과": bool(cover_true and not cover_false and b_draws >= b_min),
    }


def w7_spear(r_up, r_down, r_flat_is_nan):
    """W7 스피어만 --- 단조 증가 1 · 단조 감소 −1 · 상수는 NaN."""
    return {
        "🔴 입력별 값": {"증가": r_up, "감소": r_down, "상수가 NaN 인가": r_flat_is_nan},
        "🔴 어떤 입력이면 떨어지나":
            "부호를 뒤집으면 증가/감소가 바뀌어 떨어진다. 상수 열에서 0 을 내면 떨어진다",
        "통과": bool(abs(r_up - 1.0) < 1e-9 and abs(r_down + 1.0) < 1e-9 and r_flat_is_nan),
    }


def w8_sha(eq_same, eq_diff, n_hex):
    """W8 sha 대조기 --- 한 글자만 달라도 갈리는가 · 자르지 않았는가."""
    return {
        "🔴 입력별 값": {"같은 짝": eq_same, "다른 짝": eq_diff, "16진 길이": n_hex},
        "🔴 어떤 입력이면 떨어지나":
            "sha 를 앞 12 자로 잘라 비교하면 길이가 64 가 아니라 떨어진다",
        "통과": bool(eq_same and not eq_diff and n_hex == 64),
    }


def w9_domgate(n_pass, n_dom, min_tr, min_ho):
    """W9 도메인 게이트 --- 사전등록이 못 박은 문턱 그대로인가."""
    return {
        "🔴 입력별 값": {"통과 도메인": n_pass, "판 도메인": n_dom,
                    "학습 문턱": min_tr, "유보 문턱": min_ho},
        "🔴 어떤 입력이면 떨어지나":
            "문턱을 사전등록의 20/20 에서 옮기면 떨어진다. 통과가 판 도메인보다 많으면 떨어진다",
        "통과": bool(0 < n_pass <= n_dom and min_tr == N_MIN_TRAIN and min_ho == N_MIN_HOLD),
    }


def wiring_probe() -> dict:
    """🔴 배선 검사를 **실제 자료 없이** 심은 입력만으로 돌린다."""
    rng = np.random.RandomState(7)
    W = {}

    # W1 --- 분할기
    yr = np.array([2020.0, 2021.5, 2024.9, 2025.0, 2026.2, np.nan])
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    fin = np.isfinite(yr) & np.isfinite(y)
    tr = fin & (yr < T)
    ho = fin & (yr >= T)
    W["W1 학습/유보 분할기"] = w1_split(int(tr.sum()), int(ho.sum()),
                                   int((tr & ho).sum()), int(fin.sum()))

    # W2 --- 양성/음성 대조 (심은 자료)
    n = 400
    x = rng.randn(n)
    z = rng.randn(n)
    ys = 2.0 * x + 0.3 * rng.randn(n)                     # 신호
    yn = rng.randn(n)                                      # 잡음
    itr, iho = np.arange(n) < 300, np.arange(n) >= 300
    ps, _ = fit_predict(np.c_[x[itr], z[itr]], ys[itr], np.c_[x[iho], z[iho]])
    pn, _ = fit_predict(np.c_[z[itr]], yn[itr], np.c_[z[iho]])
    W["W2 적합기 양성/음성 대조"] = w2_recover(round(spear(ps, ys[iho]), 6),
                                       round(spear(pn, yn[iho]), 6), 0.8, 0.25)

    # W3 --- 🔴🔴 누출: 유보 결과를 통째로 갈아도 예측이 안 바뀌어야 한다
    p_a, _ = fit_predict(np.c_[x[itr], z[itr]], ys[itr], np.c_[x[iho], z[iho]])
    p_b, _ = fit_predict(np.c_[x[itr], z[itr]], ys[itr], np.c_[x[iho], z[iho]])
    ys2 = ys.copy()
    ys2[iho] = rng.permutation(ys2[iho]) * 17.0 + 999.0
    p_c, _ = fit_predict(np.c_[x[itr], z[itr]], ys2[itr], np.c_[x[iho], z[iho]])
    W["W3 🔴🔴 누출 --- 유보 결과를 갈아도 예측이 같은가"] = w3_leak(
        float(np.max(np.abs(np.r_[p_a - p_b, p_a - p_c]))), 1e-12)

    # W4 --- 가짓수 게이트
    W["W4 가짓수 게이트(조항 65-④)"] = w4_card(card(np.full(50, 0.5)),
                                        card(rng.randn(50)), 2)

    # W5 --- 묶음 가중
    vals = {"A": 0.10, "B": 0.30, "C": 0.20}
    wts = {"A": 100, "B": 50, "C": 25}
    wts_flip = {"A": 25, "B": 50, "C": 100}

    def _pw(w):
        return sum(vals[k] * w[k] for k in vals) / float(sum(w.values()))
    W["W5 묶음 가중"] = w5_pool(round(_pw(wts), 9), round(_pw(wts_flip), 9),
                            min(vals.values()), max(vals.values()))

    # W6 --- 짝 붓스트랩
    d = rng.randn(200) * 0.05 + 0.10
    bs = np.array([d[rng.randint(0, 200, 200)].mean() for _ in range(600)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    W["W6 짝 붓스트랩"] = w6_boot(bool(lo <= 0.10 <= hi), bool(lo <= 5.0 <= hi), 600, 100)

    # W7 --- 스피어만
    a = np.arange(30, dtype=float)
    flat = spear(np.full(30, 1.0), a)
    W["W7 스피어만"] = w7_spear(round(spear(a, a), 9), round(spear(a, -a), 9),
                            bool(not np.isfinite(flat)))

    # W8 --- sha
    h1 = hashlib.sha256(b"abc").hexdigest()
    h2 = hashlib.sha256(b"abc").hexdigest()
    h3 = hashlib.sha256(b"abd").hexdigest()
    W["W8 sha 대조기"] = w8_sha(bool(h1 == h2), bool(h1 == h3), len(h1))

    # W9 --- 도메인 게이트
    W["W9 도메인 게이트"] = w9_domgate(7, 12, N_MIN_TRAIN, N_MIN_HOLD)

    W["🔴 자리 수"] = sum(1 for k, v in W.items() if isinstance(v, dict) and "통과" in v)
    W["🔴 통과 수"] = sum(1 for k, v in W.items()
                       if isinstance(v, dict) and v.get("통과") is True)
    W["🔴 분자/분모(요약)"] = "%d / %d" % (W["🔴 통과 수"], W["🔴 자리 수"])
    W["🔴 붉은 자리"] = [k for k, v in W.items()
                    if isinstance(v, dict) and "통과" in v and v.get("통과") is not True]
    return W


# ══════════════════════════════════════════════════════════════════════
# §H 예측 팔
# ══════════════════════════════════════════════════════════════════════
def frames(data, ids, F):
    """도메인별 (학습, 유보) 틀. 🔴 **결과는 채점에만 쓰고 게이트에는 안 쓴다.**"""
    out, skipped = {}, {}
    val = {k: f["excite"] for k, f in F.items() if f["n_rec"] > 0 and f["n_lon"] > 0}
    for d in sorted(data.dom):
        A, M, y, _t = data.dom[d]
        nm = list(data.names.get(d) or [])
        kk = ids.get(d)
        if not kk or len(kk) != len(y) or "wiki_level" not in nm:
            skipped[d] = "규격 D 틀 없음(ids 길이 불일치 또는 wiki_level 열 없음)"
            continue
        j = nm.index("wiki_level")
        exc = np.array([val.get(k, np.nan) for k in kk], float)
        lvl = np.asarray(A[:, j], float)
        rec = np.array([F[k]["recent"] if k in F else np.nan for k in kk], float)
        yy = np.asarray(y, float)
        yr = data.yr[d]
        ok = (np.isfinite(exc) & np.isfinite(yy) & np.isfinite(lvl)
              & np.isfinite(rec) & np.isfinite(yr))
        tr = ok & (yr < T)
        ho = ok & (yr >= T)
        if tr.sum() < N_MIN_TRAIN or ho.sum() < N_MIN_HOLD:
            skipped[d] = "학습 %d / 유보 %d --- 게이트 20/20 미달" % (tr.sum(), ho.sum())
            continue
        out[d] = {"exc": exc, "lvl": lvl, "rec": rec, "y": yy, "tr": tr, "ho": ho}
    return out, skipped


def arms(fr, rng):
    """도메인 하나에서 네 팔의 유보 예측을 낸다. 🔴 **통제 게이트는 학습 행에서만 센다.**"""
    tr, ho = fr["tr"], fr["ho"]
    ctl, names, dropped = [], [], []
    for nmc, v in (("wiki_level", fr["lvl"]), ("recent_term", fr["rec"])):
        c = card(v[tr])
        if c >= 2:
            ctl.append(v)
            names.append(nmc)
        else:
            dropped.append({"열": nmc, "학습 행 가짓수": c,
                            "판정": "🔴 통제로 못 쓴다(가짓수 < 2) --- 조항 65-④"})
    yho = fr["y"][ho]
    ytr = fr["y"][tr]
    res = {"🔴 쓴 통제": names, "🔴 뺀 통제": dropped,
           "학습 행": int(tr.sum()), "유보 행": int(ho.sum())}

    def _p(cols):
        if not cols:
            return None
        Xtr = np.column_stack([c[tr] for c in cols])
        Xho = np.column_stack([c[ho] for c in cols])
        p, _b = fit_predict(Xtr, ytr, Xho)
        return p

    pB = _p(ctl)
    pC = _p(ctl + [fr["exc"]])
    pA = _p([fr["exc"]])
    res["예측"] = {"B": pB, "C": pC, "A": pA}
    res["ρ"] = {"B(통제만)": (spear(pB, yho) if pB is not None else float("nan")),
                "C(통제+들뜸)": spear(pC, yho),
                "A(들뜸만)": spear(pA, yho)}
    # 🔴 음성 대조 R --- 무작위 열 RAND_DRAWS 뽑기
    rs = []
    for i in range(RAND_DRAWS):
        st = np.random.RandomState(RAND_SEED0 + i)
        noise = st.randn(len(fr["y"]))
        pR = _p(ctl + [noise])
        rs.append(spear(pR, yho))
    res["ρ_R(무작위 열 %d 뽑기)" % RAND_DRAWS] = [round(float(v), 6) for v in rs]
    res["_yho"] = yho
    res["_rs"] = rs
    # 🔴 곁 --- 같은 유보 행에서 잰 **연관**(예측이 아니다)
    res["곁: 유보 행 안의 연관 ρ(들뜸↔결과)"] = round(spear(fr["exc"][ho], yho), 6)
    res["곁: 전 행 연관 ρ(969 규격 D 꼴 · 편상관 아님)"] = round(
        spear(fr["exc"][fr["tr"] | fr["ho"]], fr["y"][fr["tr"] | fr["ho"]]), 6)
    return res


def pooled_delta(per, key_c, key_b):
    """유보 채점 행 수 가중 묶음 Δ. 🔴 **분모는 유보 행 합이다.**"""
    num = den = 0.0
    for d, v in per.items():
        w = float(v["유보 행"])
        a, b = v["ρ"][key_c], v["ρ"][key_b]
        if np.isfinite(a) and np.isfinite(b):
            num += (a - b) * w
            den += w
    return (num / den if den else float("nan")), den


def boot_ci(per, seed=BOOT_SEED, B=BOOT):
    """🔴 짝지은 붓스트랩 --- 유보 행을 도메인 안에서 되뽑아 **같은 적합**으로 Δ 를 다시 낸다.

    🔴 **한계(조항 61)**: 이 폭은 「적합을 고정했을 때」의 폭이다. **학습 재표집은 안 했다.**
    """
    rng = np.random.RandomState(seed)
    doms = sorted(per)
    keep = [d for d in doms if per[d]["예측"]["B"] is not None]
    out = []
    for _ in range(B):
        num = den = 0.0
        for d in keep:
            v = per[d]
            n = len(v["_yho"])
            idx = rng.randint(0, n, n)
            yb = v["_yho"][idx]
            rb = spear(v["예측"]["B"][idx], yb)
            rc = spear(v["예측"]["C"][idx], yb)
            if np.isfinite(rb) and np.isfinite(rc):
                num += (rc - rb) * n
                den += n
        if den:
            out.append(num / den)
    a = np.array(out, float)
    lo, hi = (np.percentile(a, [2.5, 97.5]) if len(a) > 10 else (np.nan, np.nan))
    return {"뽑기": B, "씨앗": seed, "성공 뽑기": int(len(a)),
            "🔴 짝 SE(붓스트랩 SD)": round(float(a.std(ddof=1)), 6) if len(a) > 2 else None,
            "🔴 95% 구간": [round(float(lo), 6), round(float(hi), 6)],
            "🔴 아래끝 > 0": bool(np.isfinite(lo) and lo > 0),
            "🔴 한계(조항 61)": ("유보 행만 되뽑는다 --- **학습 재표집은 안 했다**. "
                          "그러므로 이 폭은 「적합을 고정했을 때」의 폭이고, "
                          "적합의 변동은 이 안에 **안 들어 있다**")}


def verdict(dpred, floor_repo, floor_arm, ci_lo_pos, n_pos, n_dom):
    """🔴🔴 사전등록 §7-가 채택 조건 **다섯**. 측정 전에 못 박았다."""
    c1 = bool(dpred > 0)
    c2 = bool(dpred >= floor_repo)
    c3 = bool(dpred >= floor_arm)
    c4 = bool(ci_lo_pos)
    c5 = bool(n_pos >= 5 and n_dom >= 5)
    return {
        "🔴 입력별 값": {"Δρ_pred": dpred, "저장소 잡음 바닥(0.01055)": floor_repo,
                    "이 자로 잰 잡음 바닥(팔 R 95 분위)": floor_arm,
                    "붓스트랩 아래끝 > 0": ci_lo_pos,
                    "Δ > 0 인 도메인": n_pos, "도메인 수": n_dom},
        "조건별": {"① Δ > 0": c1, "② Δ ≥ 0.01055": c2, "③ Δ ≥ 팔 R 95 분위": c3,
                "④ 붓스트랩 아래끝 > 0": c4, "⑤ 7 중 ≥ 5 도메인 양수": c5},
        "🔴 분자/분모": "%d / 5" % sum([c1, c2, c3, c4, c5]),
        "🔴 어떤 입력이면 떨어지나":
            "Δ 를 0 이하로 내리면 ①이, 잡음 바닥을 Δ 위로 올리면 ②③이, "
            "구간 아래끝을 0 아래로 내리면 ④가, 양수 도메인을 4 이하로 줄이면 ⑤가 떨어진다",
        "통과": bool(c1 and c2 and c3 and c4 and c5),
    }


def stage_predict(seeds_unused=None) -> dict:
    import dropaudit969 as D9
    t0 = time.time()
    data, ids = D9.build(drop_wiki=True, drop_trend=True)
    recs = D9.load_series()
    F, why = D9.feats(recs)
    per, skipped = frames(data, ids, F)
    rng = np.random.RandomState(BOOT_SEED)
    for d in sorted(per):
        per[d].update(arms(per[d], rng))

    dpred, den = pooled_delta(per, "C(통제+들뜸)", "B(통제만)")
    dalone, _ = pooled_delta(per, "A(들뜸만)", "B(통제만)")
    ci = boot_ci(per)

    # 🔴 팔 R --- 뽑기별 묶음 Δ 를 만들어 95 분위를 낸다(이 자로 직접 잰 잡음 바닥)
    rdel = []
    for i in range(RAND_DRAWS):
        num = den2 = 0.0
        for d in sorted(per):
            v = per[d]
            b = v["ρ"]["B(통제만)"]
            r = v["_rs"][i]
            if np.isfinite(b) and np.isfinite(r):
                num += (r - b) * v["유보 행"]
                den2 += v["유보 행"]
        if den2:
            rdel.append(num / den2)
    rarr = np.array(rdel, float)
    floor_arm = float(np.percentile(rarr, 95)) if len(rarr) else float("nan")

    dom_delta = {}
    n_pos = 0
    for d in sorted(per):
        v = per[d]
        dd = v["ρ"]["C(통제+들뜸)"] - v["ρ"]["B(통제만)"]
        dom_delta[d] = {
            "유보 행": v["유보 행"], "학습 행": v["학습 행"],
            "ρ_B(통제만)": round(v["ρ"]["B(통제만)"], 6),
            "ρ_C(통제+들뜸)": round(v["ρ"]["C(통제+들뜸)"], 6),
            "ρ_A(들뜸만)": round(v["ρ"]["A(들뜸만)"], 6),
            "🔴 Δ(C−B)": round(float(dd), 6),
            "🔴 이 도메인 최소 가를 수 있는 효과(2 SE)":
                round(2.0 / np.sqrt(v["유보 행"] - 1), 4),
            "🔴 쓴 통제": v["🔴 쓴 통제"], "🔴 뺀 통제": v["🔴 뺀 통제"],
            "곁: 유보 안 연관 ρ": v["곁: 유보 행 안의 연관 ρ(들뜸↔결과)"],
            "곁: 전 행 연관 ρ": v["곁: 전 행 연관 ρ(969 규격 D 꼴 · 편상관 아님)"],
            "팔 R 무작위 열 Δ 중앙값":
                round(float(np.median([r - v["ρ"]["B(통제만)"] for r in v["_rs"]])), 6),
        }
        if dd > 0:
            n_pos += 1

    V = verdict(round(float(dpred), 6), DIAG_NOISE_1COL, round(floor_arm, 6),
                ci["🔴 아래끝 > 0"], n_pos, len(per))

    assoc_ho = {d: dom_delta[d]["곁: 유보 안 연관 ρ"] for d in dom_delta}
    assoc_all = {d: dom_delta[d]["곁: 전 행 연관 ρ"] for d in dom_delta}
    return {
        "🔴 사전등록 상수": {"T": T, "학습 문턱": N_MIN_TRAIN, "유보 문턱": N_MIN_HOLD,
                      "능형 λ": RIDGE, "붓스트랩 뽑기": BOOT, "붓스트랩 씨앗": BOOT_SEED,
                      "무작위 열 뽑기": RAND_DRAWS, "무작위 열 씨앗 시작": RAND_SEED0},
        "🔴 분모 ① 판 도메인": len(data.dom),
        "🔴 분모 ② 게이트 통과 도메인": len(per),
        "🔴 분모 ③ 유보 행 합": int(den),
        "🔴 분모 ④ 학습 행 합": int(sum(v["학습 행"] for v in per.values())),
        "🔴 뺀 도메인과 사유": skipped,
        "feats 제외 사유(원천 쪽)": why,
        "도메인별": dom_delta,
        "🔴🔴 묶음 Δρ_pred(C−B)": round(float(dpred), 6),
        "🔴 묶음 Δ(A−B · 들뜸만 − 통제만)": round(float(dalone), 6),
        "🔴 짝지은 붓스트랩": ci,
        "🔴🔴 이 자로 잰 잡음 바닥(팔 R %d 뽑기)" % RAND_DRAWS: {
            "중앙값": round(float(np.median(rarr)), 6) if len(rarr) else None,
            "95 분위": round(float(floor_arm), 6),
            "최대": round(float(rarr.max()), 6) if len(rarr) else None,
            "🔴 뜻": ("무작위 열 하나를 통제에 더했을 때 유보 예측이 **우연히** 얼마나 "
                   "좋아지는가. 🔴 저장소가 물려쓰던 0.01055 는 **판 ρ 의** 바닥이라 "
                   "이 자의 바닥이 아니다 --- 여기서 직접 잰다"),
        },
        "🔴🔴🔴 판정 --- 사전등록 §7-가 채택 조건 다섯": V,
        "🔴 Δ > 0 인 도메인": "%d / %d" % (n_pos, len(per)),
        "🔴🔴 연관 vs 예측": {
            "유보 행 안의 연관 ρ(도메인별)": assoc_ho,
            "전 행 연관 ρ(도메인별)": assoc_all,
            "🔴 뜻": ("969~970 이 낸 모든 수는 위 두 줄의 종류다 --- **같은 자료 안의 연관**. "
                   "위의 Δρ_pred 는 **적합이 한 번도 못 본 행에서** 잰 것이라 종류가 다르다"),
        },
        "초": round(time.time() - t0, 1),
    }


# ══════════════════════════════════════════════════════════════════════
# §B 판 --- 🔴 970 이 버린 `sc` 를 안 버린다
# ══════════════════════════════════════════════════════════════════════
def stage_board(seeds=SEEDS) -> dict:
    """🔴🔴 970 의 `board_pair()` 는 `evaluate()` 의 `sc` 를 `pooled()` 에 인라인으로
    넣고 **버렸다**(970 자기 적발). 여기서는 팔별·도메인별로 남긴다.
    """
    import dropaudit969 as D9
    from lab.harness import evaluate
    from lab import forms as FM
    t0 = time.time()
    don, _ = D9.build(drop_wiki=True, drop_trend=True)
    doff, _ = D9.build(drop_wiki=False, drop_trend=False)
    cls = FM.REGISTRY["F18_bagboost"]["cls"]
    a0, a1, rows = [], [], []
    p0, p1 = {}, {}
    for s in range(seeds):
        sc0 = evaluate(lambda s=s: cls(seed=s), don, T=T)
        sc1 = evaluate(lambda s=s: cls(seed=s), doff, T=T)
        v0 = float(don.pooled(sc0, T=T))
        v1 = float(doff.pooled(sc1, T=T))
        a0.append(v0)
        a1.append(v1)
        for d, v in sc0.items():
            p0.setdefault(d, []).append(float(v))
        for d, v in sc1.items():
            p1.setdefault(d, []).append(float(v))
        rows.append({"씨앗": s, "기준선(현행)": round(v0, 6),
                     "처리(DROP 비움)": round(v1, 6), "차": round(v1 - v0, 6)})
    x0, x1 = np.array(a0), np.array(a1)
    d = x1 - x0
    sd_d = float(d.std(ddof=1))
    se_d = sd_d / float(np.sqrt(len(d)))
    w = don.weights(T)

    dom = {}
    zero = []
    for k in sorted(set(p0) | set(p1)):
        v0 = np.array(p0.get(k, []), float)
        v1 = np.array(p1.get(k, []), float)
        if len(v0) != len(v1) or not len(v0):
            dom[k] = {"🔴 못 잰다": "두 팔의 씨앗 수가 다르다(%d 대 %d)" % (len(v0), len(v1))}
            continue
        dd = v1 - v0
        s_d = float(dd.std(ddof=1)) if len(dd) > 1 else float("nan")
        dom[k] = {
            "판 가중(유보 채점 행)": w.get(k),
            "기준선(현행) 평균": round(float(v0.mean()), 6),
            "처리(DROP 비움) 평균": round(float(v1.mean()), 6),
            "🔴 Δ(도메인)": round(float(dd.mean()), 6),
            "🔴 짝 SD": round(s_d, 6),
            "🔴 짝 SE": round(s_d / np.sqrt(len(dd)), 6) if len(dd) > 1 else None,
            "🔴 이긴 씨앗": "%d / %d" % (int((dd > 0).sum()), len(dd)),
            "🔴 정확히 0 인가(두 DROP 이 안 닿는가)": bool(np.all(dd == 0.0)),
        }
        if np.all(dd == 0.0):
            zero.append(k)
    return {
        "주행 수": 2 * seeds,
        "짝별": rows,
        "기준선(현행)": {"판": float(x0.mean()), "SD": float(x0.std(ddof=1)),
                   "SE": float(x0.std(ddof=1) / np.sqrt(len(x0)))},
        "처리(DROP 비움)": {"판": float(x1.mean()), "SD": float(x1.std(ddof=1)),
                       "SE": float(x1.std(ddof=1) / np.sqrt(len(x1)))},
        "🔴 기준선이 정본을 재현하나": {
            "정본": RHO0, "실측": float(x0.mean()),
            "차": abs(float(x0.mean()) - RHO0),
            "통과": bool(abs(float(x0.mean()) - RHO0) < 5e-4)},
        "🔴🔴 Δρ(짝지은 C−B)": round(float(d.mean()), 6),
        "🔴 짝 SD": round(sd_d, 6), "🔴 짝 SE": round(se_d, 6),
        "🔴🔴 판정(Δρ ± 짝 SE)": "%+.6f ± %.6f" % (float(d.mean()), se_d),
        "🔴 |Δρ| ÷ 짝 SE": round(abs(float(d.mean())) / se_d, 2) if se_d else None,
        "🔴 이긴 씨앗": "%d / %d" % (int((d > 0).sum()), seeds),
        "🔴 970 과의 대조": {"970 Δρ": -0.002962, "970 짝 SE": 0.000973,
                       "🔴 Δρ 차": round(abs(float(d.mean()) - (-0.002962)), 6)},
        "🔴🔴 도메인별 Δ --- 970 이 버린 것": dom,
        "🔴 Δ 가 정확히 0 인 도메인": {"목록": zero, "🔴 분자/분모":
                                "%d / %d" % (len(zero), len(dom))},
        "🔴 채택 크기": ("**못 정했다**. 0.01055(잡음 바닥)·0.00353(운영 문턱)은 "
                    "**둘 다 진단 수치**다 --- 판정은 `Δρ ± 짝 SE` 로만 적는다(조항 61)"),
        "초": round(time.time() - t0, 1),
    }


# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["wiring", "predict", "board"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", required=True,
                    help="🔴 **고정 sha** --- 움직이는 가지 이름을 주면 F11 이 떨어진다")
    ap.add_argument("--seeds", type=int, default=SEEDS)
    a = ap.parse_args()

    out_path = Path(a.out)
    if not out_path.is_absolute():
        out_path = ROOT / "runners" / out_path
    t_start, cs0 = _now(), code_stamp()
    t0 = time.time()
    R = {"🔴 노트": 971, "🔴 레인": "판정", "🔴 단계": a.stage, "🔴 시작(UTC)": t_start,
         "🔴 사전등록": "docs/prereg_971_holdout.md (측정 전 단독 커밋 42ac6b031)"}

    with NoWrite(allow=[str(out_path)]) as G:
        R["🔴🔴 §S 내가 돌린 러너 ↔ 커밋 blob(F1)"] = ran_vs_blob(a.ref)
        if a.stage == "wiring":
            R["§W 배선"] = wiring_probe()
        elif a.stage == "predict":
            R["🔴🔴🔴 §H 유보 예측"] = stage_predict()
        elif a.stage == "board":
            R["🔴🔴 §B 판 --- 되살린 통제로 24 주행(도메인별 Δ 포함)"] = stage_board(a.seeds)
        R["🔴 문지기가 막은 쓰기"] = sorted(set(G.blocked))

    cs1, t_end = code_stamp(), _now()
    R["🔴 끝(UTC)"] = t_end
    R["🔴 걸린 초"] = round(time.time() - t0, 1)
    R["🔴🔴 §Z 소스 대조"] = {
        "시작 code_stamp 요약": stamp_digest(cs0),
        "끝 code_stamp 요약": stamp_digest(cs1),
        "🔴 주행 중 소스가 바뀌었나": bool(cs0 != cs1),
        "🔴 바뀐 파일": sorted(k for k in set(cs0) | set(cs1) if cs0.get(k) != cs1.get(k)),
        "🔴 잰 소스 sha(전량 · 자르지 않았다)": cs1,
        "🔴 F2 --- code_stamp 가 내가 돌린 러너 전부를 덮는가": {
            "돌린 러너": list(RAN),
            "덮은 러너": [r for r in RAN if r in cs1],
            "분자/분모": "%d / %d" % (len([r for r in RAN if r in cs1]), len(RAN)),
            "통과": bool(all(r in cs1 for r in RAN)),
        },
    }

    def _clean(o):
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items() if not str(k).startswith("_")}
        if isinstance(o, list):
            return [_clean(v) for v in o]
        if isinstance(o, np.ndarray):
            return [float(v) for v in o]
        if isinstance(o, (np.floating, np.integer)):
            return float(o)
        return o

    with open(str(out_path), "w", encoding="utf-8") as f:
        json.dump(_clean(R), f, ensure_ascii=False, indent=1)
    print("wrote", out_path, R["🔴 걸린 초"], "s  시작", t_start, "끝", t_end)


if __name__ == "__main__":
    main()
