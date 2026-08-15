# -*- coding: utf-8 -*-
"""노트 972 — **C1 상태→예측** · 예측 팔에 **진짜 귀무 하나** · 배선이 **생산 함수를 태운다**.

사전등록: `docs/prereg_972_c1null.md` (측정 전 단독 커밋 `8675748ed`).

🔴 **`runners/predict971.py` 를 한 바이트도 안 고친다.** 971 의 생산 함수를
**임포트해서 부른다** — 971 의 배선은 자기 안에서 다시 짜서 「9/9 인데 생산 함수 일곱을
동시에 부숴도 9/9」였다(티처 #110 중대 1). 🔴 **다시 쓴 자는 죽은 자다.**

단계: `wiring` → `null`.
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

import predict971 as P                                            # noqa: E402

# ── 사전등록 §3 이 못 박은 상수 ──────────────────────────────────────
PERM_B = 4000            # §3-가·나 순열 뽑기
PERM_SEED = 972
BOOTB = 2000             # §3-다 붓스트랩 뽑기
BOOT_SEED = 972
RAND_DRAWS = 2000        # §3-마 팔 R 뽑기
SIDE_MIN_TRAIN = 15      # §3-바 곁 팔(판 `lab/harness.MIN_TRAIN` 과 같은 값)

#: 🔴 **이 사이클에서 내가 돌린 러너 전부**(규칙 C · 티처 #110 중-14).
#: 971 은 7 중 **4** 만 넣었다. 🔴 **자기 자신이 첫째다**(조항 66-⑥).
RAN = ("runners/predict972.py",
       "runners/rulerstab972.py",
       "runners/ledger972.py",
       "runners/meta965.py",
       "runners/predict971.py",
       "runners/dropaudit969.py",
       "runners/recommit970.py")

#: 🔴 **생산 함수 목록** — 배선의 **얕은 자리**(W1~W8)가 이것들을 *태워야* 한다.
#: 파괴 대조가 하나씩 상수로 망가뜨리고 **붉어지는 자리 수**를 센다.
#: 🔴 `arms` 는 여기 없다 — **깊은 자리 W10·W11 에서만** 태우고 그 자리는 판 자료를
#: 두 번 지어야 해서 파괴 대조에 못 넣는다(주행 시간). **그 사실을 산출물에 적는다.**
PROD_FUNCS = ("frames", "pooled_delta", "boot_ci", "fit_predict",
              "spear", "card", "_sha_file", "blob_sha", "stamp_digest")


def _now() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ══════════════════════════════════════════════════════════════════════
# 도장 — 🔴 규칙 C: 러너 전부 + **자료 입력** + 시작·끝 두 번
# ══════════════════════════════════════════════════════════════════════
READ_LOG: list = []


class ReadTap:
    """🔴 **972 신설** --- 주행 중 실제로 **읽은** 파일을 기록한다.

    971 의 `code_stamp` 은 `lab/*.py` 와 러너 넷뿐이라 **`data/` 가 0 개**였다
    (티처 #110 중-14). 자료가 갈리면 수가 갈리는데 도장이 그것을 안 덮었다.
    🔴 **추측으로 목록을 적지 않는다 --- 열리는 것을 잡는다.**
    """

    def __enter__(self):
        self._o = (builtins.open, Path.open)
        import numpy as _np
        self._nl = _np.load

        def f(file, mode="r", *a, **k):
            READ_LOG.append(str(file))
            return self._o[0](file, mode, *a, **k)

        def g(self2, mode="r", *a, **k):
            READ_LOG.append(str(self2))
            return self._o[1](self2, mode, *a, **k)

        def h(file, *a, **k):
            READ_LOG.append(str(file))
            return self._nl(file, *a, **k)

        builtins.open, Path.open, _np.load = f, g, h
        return self

    def __exit__(self, *e):
        import numpy as _np
        builtins.open, Path.open = self._o
        _np.load = self._nl
        return False


def data_inputs() -> dict:
    """🔴 주행 중 읽힌 `data/` 파일 전량의 sha256. **분모를 같이 낸다.**"""
    out = {}
    for s in set(READ_LOG):
        try:
            p = Path(s).resolve()
        except Exception:                                          # noqa: BLE001
            continue
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            continue
        if str(rel).startswith("data/"):
            out[str(rel)] = P._sha_file(p)                    # 🔴 971 의 생산 함수
    return out


DATA_LIST_CAP = 1000     # 🔴 이보다 많으면 파일별 목록 대신 **디렉터리 롤업**을 싣는다


def data_seal() -> dict:
    """🔴 규칙 C 의 자료 지문. **합친 요약은 전량을 덮고**, 목록은 크기를 지킨다.

    🔴 첫 판은 파일별 sha 를 전량 실었고 **산출물 하나가 1.7 MB** 였다(자료 **11,303** 개 ---
    `data/state/wiki_views` 만 10,960 개). **대용량 git 반입 금지** 제약에 걸린다.
    그래서 **합친 요약(전량을 덮는다) + 디렉터리 롤업**으로 바꾸고, 파일별 전량은
    `DATA_LIST_CAP` 아래일 때만 싣는다. 🔴 **덮는 범위는 안 줄었다 --- 싣는 꼴만 줄었다.**
    """
    dat = data_inputs()
    roll = {}
    for k in sorted(dat):
        d = "/".join(k.split("/")[:2]) if k.count("/") >= 2 else k
        roll.setdefault(d, []).append(dat[k])
    return {
        "🔴 무엇": ("주행 중 **실제로 열린** `data/` 파일 전량의 sha256. "
               "🔴 목록을 추측으로 안 적는다 --- `open`·`Path.open`·`np.load` 를 잡아 "
               "**열리는 것을 기록**한다"),
        "🔴 분모: 자료 파일 수": len(dat),
        "🔴🔴 합친 요약(전량을 덮는다)": P.stamp_digest(dat),
        "🔴 디렉터리별 롤업": {d: {"파일 수": len(v), "합친 sha256":
                                hashlib.sha256("".join(sorted(v)).encode()).hexdigest()}
                       for d, v in sorted(roll.items())},
        "파일별 sha256(자르지 않았다)":
            (dat if len(dat) <= DATA_LIST_CAP else
             "🔴 %d 개라 안 싣는다(상한 %d) --- 위 「합친 요약」이 전량을 덮는다"
             % (len(dat), DATA_LIST_CAP)),
    }


def code_stamp() -> dict:
    """🔴 **F2 확대** --- `lab/*.py` 전량 + **내가 돌린 러너 전부**.

    🔴 **자료는 여기 안 넣는다.** 자료 지문은 `data_inputs()` 로 **끝에 한 번** 낸다 ---
    시작 시점에는 아직 아무 자료도 안 읽었으므로 시작·끝 대조가 **원리상 언제나 갈린다**.
    971 의 잘못은 「자료가 도장에 없다」였고, 그것은 **§D 로 고친다**(규칙 C).
    """
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def ran_vs_blob(ref: str) -> dict:
    """🔴🔴 **F1** --- 돌린 러너 전부의 디스크 sha 를 커밋 blob 과 대조한다.

    🔴 `P._sha_file`·`P.blob_sha` 를 **부른다**(다시 안 쓴다).
    """
    per, bad = {}, []
    for p in RAN:
        d = P._sha_file(ROOT / p) if (ROOT / p).is_file() else None
        b = P.blob_sha(ref, p)
        ok = bool(d is not None and d == b)
        per[p] = {"디스크 sha256": d, "커밋 blob sha256": b, "일치": ok}
        if not ok:
            bad.append(p)
    fixed = bool(len(ref) >= 7 and all(c in "0123456789abcdef" for c in ref.lower()))
    return {"기준 ref(준 대로)": ref,
            "🔴 F11 --- ref 가 고정 sha 인가": fixed,
            "기준 커밋": subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", ref],
                capture_output=True).stdout.decode().strip(),
            "러너별": per,
            "🔴 분자/분모": "%d / %d" % (len(RAN) - len(bad), len(RAN)),
            "🔴 어긋난 러너": bad,
            "🔴 F1 통과": bool(not bad and fixed),
            "🔴 어떤 입력이면 떨어지나":
                "러너를 한 바이트만 고치고 커밋을 안 하면 그 줄이 곧 거짓이 된다. "
                "`--ref` 에 가지 이름을 주면 F11 이 떨어진다"}


# ══════════════════════════════════════════════════════════════════════
# 합성 판 --- W1 이 **`P.frames` 를 실제로 태우려면** 판 `Data` 가 필요하다
# ══════════════════════════════════════════════════════════════════════
def synth_board(n=200, n_ho=60, seed=972, with_small=True):
    """🔴 합성 규격 D 판. `P.frames` 의 인자 규격을 그대로 맞춘다."""
    from lab.harness import Data
    st = np.random.RandomState(seed)
    dom, names, yr, ids, F = {}, {}, {}, {}, {}

    def _one(tag, m, m_ho):
        keys = ["%s%d" % (tag, i) for i in range(m)]
        lvl = st.rand(m)
        rec = st.rand(m)
        exc = st.randn(m)
        y = 0.7 * exc + 0.3 * lvl + 0.2 * st.randn(m)
        years = np.where(np.arange(m) >= (m - m_ho), 2025.5, 2024.0)
        A = np.column_stack([lvl])
        M = np.ones_like(A)
        dom[tag] = (A, M, y, years)
        names[tag] = ["wiki_level"]
        yr[tag] = years
        ids[tag] = keys
        for i, k in enumerate(keys):
            F[k] = {"recent": float(rec[i]), "long": float(rec[i] - exc[i]),
                    "excite": float(exc[i]), "n_rec": 1, "n_lon": 1}

    _one("큰", n, n_ho)
    if with_small:
        _one("작은", 25, 5)               # 🔴 유보 5 --- 게이트 20 에서 떨어져야 한다
    return Data(dom=dom, names=names, yr=yr), ids, F


def _fp(o) -> str:
    """지문. 🔴 `P.stamp_digest` 를 **부른다**."""
    def _c(x):
        if isinstance(x, dict):
            return {str(k): _c(v) for k, v in x.items() if not str(k).startswith("_")}
        if isinstance(x, (list, tuple)):
            return [_c(v) for v in x]
        if isinstance(x, np.ndarray):
            return [round(float(v), 12) for v in np.ravel(x)]
        if isinstance(x, (np.floating, float)):
            return round(float(x), 12)
        if isinstance(x, (np.integer, int)):
            return int(x)
        if isinstance(x, (str, bool)) or x is None:
            return x
        return str(x)
    return P.stamp_digest(_c(o))


# ── 배선 자리 --- 🔴 전부 「작은 최상위 함수 + 스칼라 인자」 ──────────
def w1_frames(n_pass, n_skip, overlap, tr_n, ho_n, tot_fin, gate_msg_ok):
    """W1 분할 --- 🔴 **`P.frames` 를 불러서** 잰다(971 은 손으로 배열을 셌다)."""
    return {
        "🔴 입력별 값": {"게이트 통과 도메인": n_pass, "뺀 도메인": n_skip,
                    "학습∩유보": overlap, "학습": tr_n, "유보": ho_n,
                    "유한 행": tot_fin, "뺀 사유가 게이트를 말하나": gate_msg_ok},
        "🔴 태우는 생산 함수": "predict971.frames",
        "🔴 어떤 입력이면 떨어지나":
            "`frames` 가 학습/유보를 겹치게 나누면 겹침이 0 이 아니라 떨어진다. "
            "게이트를 안 걸면 작은 도메인이 통과해 뺀 도메인이 0 이 되어 떨어진다. "
            "`frames` 를 상수로 망가뜨리면 통과 도메인이 1 이 아니라 떨어진다",
        "통과": bool(n_pass == 1 and n_skip == 1 and overlap == 0
                    and tr_n > 0 and ho_n > 0 and tr_n + ho_n == tot_fin
                    and gate_msg_ok),
    }


def w2_recover(rho_signal, rho_noise, thr_hi, thr_lo):
    """W2 적합기 양성/음성 --- `P.fit_predict` 를 태운다."""
    return {
        "🔴 입력별 값": {"심은 신호 유보 ρ": rho_signal, "순수 잡음 유보 ρ": rho_noise,
                    "양성 문턱": thr_hi, "음성 문턱": thr_lo},
        "🔴 태우는 생산 함수": "predict971.fit_predict · predict971.spear",
        "🔴 어떤 입력이면 떨어지나":
            "`fit_predict` 를 상수로 망가뜨리면 양성이 문턱 아래로 내려가 떨어진다",
        "통과": bool(rho_signal > thr_hi and abs(rho_noise) < thr_lo),
    }


def w3_leak(ho_diff, tr_diff, tol, tr_min):
    """🔴🔴 W3 누출 --- **양방향**.

    971 은 음성 방향(유보를 갈아도 안 변한다)만 봤다. 🔴 **그래서 `fit_predict` 를
    상수 0 으로 망가뜨려도 초록이었다**(티처 #110 치-6). 여기서는 **양성 방향**도 본다:
    **학습 결과를 갈면 예측이 반드시 변해야 한다.**
    """
    return {
        "🔴 입력별 값": {"y_유보 를 갈았을 때 최대 절대차": ho_diff, "허용": tol,
                    "🔴 y_학습 을 갈았을 때 최대 절대차": tr_diff, "최소 요구": tr_min},
        "🔴 태우는 생산 함수": "predict971.fit_predict",
        "🔴 어떤 입력이면 떨어지나":
            "적합에 유보 행을 넣으면 음성 방향이 커져 떨어진다. "
            "🔴 `fit_predict` 를 상수 0 으로 망가뜨리면 **양성 방향이 0 이 되어 떨어진다** "
            "--- 971 의 W3 은 이 방향이 없어서 그 망가뜨림에도 초록이었다",
        "통과": bool(ho_diff <= tol and tr_diff > tr_min),
    }


def w4_card(c_const, c_vary, gate):
    """W4 가짓수 게이트(조항 65-④) --- `P.card` 를 태운다."""
    return {
        "🔴 입력별 값": {"상수 열 가짓수": c_const, "변하는 열 가짓수": c_vary, "게이트": gate},
        "🔴 태우는 생산 함수": "predict971.card",
        "🔴 어떤 입력이면 떨어지나": "`card` 가 상수 열에 2 이상을 내면 떨어진다",
        "통과": bool(c_const < gate <= c_vary),
    }


def w5_pool(pooled, pooled_flip, den, den_flip, lo, hi):
    """W5 묶음 가중 --- 🔴 **`P.pooled_delta` 를 부른다**(971 은 안에서 다시 짰다)."""
    return {
        "🔴 입력별 값": {"묶음": pooled, "가중 뒤바꾼 묶음": pooled_flip,
                    "분모": den, "뒤바꾼 분모": den_flip, "구성 최소": lo, "구성 최대": hi},
        "🔴 태우는 생산 함수": "predict971.pooled_delta",
        "🔴 어떤 입력이면 떨어지나":
            "`pooled_delta` 가 가중을 무시하고 단순 평균을 내면 두 값이 같아져 떨어진다. "
            "분모가 유보 행 합이 아니면 두 분모가 같지 않아 떨어진다",
        "통과": bool(lo <= pooled <= hi and lo <= pooled_flip <= hi
                    and pooled != pooled_flip and den == den_flip),
    }


def w6_boot(cover_true, cover_false, se, b_draws, b_min):
    """W6 짝 붓스트랩 --- 🔴 **`P.boot_ci` 를 부른다**(971 은 안에서 다시 짰다)."""
    return {
        "🔴 입력별 값": {"참값을 덮나": cover_true, "멀리 옮긴 값을 덮나": cover_false,
                    "붓스트랩 SD": se, "뽑기": b_draws, "최소 뽑기": b_min},
        "🔴 태우는 생산 함수": "predict971.boot_ci",
        "🔴 어떤 입력이면 떨어지나":
            "`boot_ci` 가 구간을 (−∞, ∞) 로 넓히면 옮긴 값도 덮여 떨어진다. "
            "SD 를 0 으로 내면 떨어진다",
        "통과": bool(cover_true and not cover_false and se is not None and se > 0
                    and b_draws >= b_min),
    }


def w7_spear(r_up, r_down, r_flat_is_nan):
    """W7 스피어만 --- `P.spear` 를 태운다."""
    return {
        "🔴 입력별 값": {"증가": r_up, "감소": r_down, "상수가 NaN 인가": r_flat_is_nan},
        "🔴 태우는 생산 함수": "predict971.spear",
        "🔴 어떤 입력이면 떨어지나": "부호를 뒤집으면 증가/감소가 바뀌어 떨어진다",
        "통과": bool(abs(r_up - 1.0) < 1e-9 and abs(r_down + 1.0) < 1e-9 and r_flat_is_nan),
    }


def w8_sha(eq_same, eq_diff, n_hex, blob_eq, dig_same, dig_diff):
    """W8 sha --- 🔴 **`P._sha_file`·`P.blob_sha`·`P.stamp_digest` 를 부른다**."""
    return {
        "🔴 입력별 값": {"같은 파일 짝": eq_same, "다른 파일 짝": eq_diff, "16진 길이": n_hex,
                    "디스크 = 커밋 blob": blob_eq,
                    "같은 딕트 요약 일치": dig_same, "다른 딕트 요약 갈림": dig_diff},
        "🔴 태우는 생산 함수": "predict971._sha_file · blob_sha · stamp_digest",
        "🔴 어떤 입력이면 떨어지나":
            "`_sha_file` 을 앞 12 자로 자르면 길이가 64 가 아니라 떨어진다. "
            "`stamp_digest` 를 상수로 망가뜨리면 다른 딕트가 안 갈려 떨어진다",
        "통과": bool(eq_same and not eq_diff and n_hex == 64 and blob_eq
                    and dig_same and dig_diff),
    }


def w10_idem(fp_a, fp_b, fp_data_a, fp_data_b):
    """🔴🔴 **조항 67 ① 멱등성** --- 같은 팔을 두 번 지어 지문이 같은가.

    🔴 971 이 조항 67 을 **문장으로** 만들고 러너로 안 내렸다. 그 사이 `dropaudit969.build()`
    의 곁수효는 **그대로 살아 있었다**(티처 #110). **두 번 지으면 갈린다** --- 이 자리가
    그것을 원리상 잡는다.
    """
    return {
        "🔴 입력별 값": {"팔 지문 1차": fp_a, "팔 지문 2차": fp_b,
                    "자료 지문 1차": fp_data_a, "자료 지문 2차": fp_data_b},
        "🔴 어떤 입력이면 떨어지나":
            "짓는 함수에 **복원 없는 곁수효**가 있으면 두 번째가 다른 설정에서 지어져 "
            "지문이 갈리고 떨어진다. 🔴 **전례 없는 새 대조에서도 발화한다**",
        "통과": bool(fp_a == fp_b and fp_data_a == fp_data_b),
    }


def w11_order(fp_fwd, fp_rev):
    """🔴🔴 **조항 67 ② 순서 불변** --- 짓는 순서를 뒤집어도 지문이 같은가."""
    return {
        "🔴 입력별 값": {"정순 지문": fp_fwd, "역순 지문": fp_rev},
        "🔴 어떤 입력이면 떨어지나":
            "도메인 하나의 적합이 **앞 도메인이 남긴 상태**를 보면 순서를 뒤집을 때 갈려 "
            "떨어진다(공유 난수 흐름·전역 캐시). 🔴 **전례 없는 새 대조에서도 발화한다**",
        "통과": bool(fp_fwd == fp_rev),
    }


#: 🔴 **972 수리 4 의 「전」 판** --- `dropaudit969.build()` 이 곁수효를 복원 안 하던 커밋.
#: PR #229 머지 커밋(972 사전등록 **직전**의 트리). **고정 sha 다.**
PREFIX_REF = "ff1ae7039a6ed38a8e2436c680c52dbbb1d42abe"


def w12_side(wide_before, wide_after, grades_before, grades_after,
             old_wide=None, old_grades=None, old_bites=None):
    """🔴🔴 **W12 곁수효** --- `dropaudit969.build()` 가 전역 설정을 되돌리는가.

    🔴 **972 수리 4.** 971 은 이 지뢰를 **문서로 적발하고 코드는 안 고쳤다**.
    """
    return {
        "🔴 입력별 값": {"WIDE 전": wide_before, "WIDE 후": wide_after,
                    "GRADES 전": list(grades_before), "GRADES 후": list(grades_after)},
        "🔴🔴 수리 **전** blob 을 같은 자로 재니": {
            "🔴 기준 커밋(고정 sha)": PREFIX_REF,
            "GRADES 후": (list(old_grades) if old_grades is not None else None),
            "WIDE 후": old_wide,
            "🔴🔴 곁수효가 남나(수리 전)": old_bites,
        },
        "🔴 어떤 입력이면 떨어지나":
            "`build()` 안의 `TA.set_wide(False)`·`set_grades(...)` 를 **복원 없이** 두면 "
            "`GRADES` 가 ('A','B') → ('A','B','C','D','E') 로 남아 떨어진다. "
            "🔴 **수리 전 blob 을 같은 자로 재서 그 자리가 실제로 붉다는 것을 같이 낸다** --- "
            "**양쪽 방향으로 발화하는 자다**",
        "통과": bool(wide_before == wide_after and tuple(grades_before) == tuple(grades_after)
                    and old_bites is True),
    }


def _old_build_bites():
    """🔴 수리 **전** `dropaudit969.build()` 를 커밋 blob 에서 살려 곁수효를 실측한다."""
    import types
    from lab import trendaxes as TA
    r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-p",
                        "%s:runners/dropaudit969.py" % PREFIX_REF], capture_output=True)
    if r.returncode != 0:
        return None, None, None
    keep_w, keep_g = TA.WIDE, tuple(TA.GRADES)
    try:
        mod = types.ModuleType("dropaudit969_pre972")
        mod.__dict__["__file__"] = str(ROOT / "runners/dropaudit969.py")
        exec(compile(r.stdout.decode("utf-8"),
                     "dropaudit969_pre972", "exec"), mod.__dict__)
        mod.build(drop_wiki=True, drop_trend=True)
        w, g = TA.WIDE, tuple(TA.GRADES)
        bites = bool(w != keep_w or g != keep_g)
        return w, g, bites
    except Exception as e:                                         # noqa: BLE001
        return None, ("%s: %s" % (type(e).__name__, e),), None
    finally:
        TA.set_grades(keep_g)
        TA.set_wide(keep_w)


# ══════════════════════════════════════════════════════════════════════
def wiring_probe(deep=True) -> dict:
    """🔴 배선. **전부 `P.<생산함수>` 를 부른다** --- 다시 안 쓴다."""
    W = {}
    st = np.random.RandomState(7)

    # ── W1 --- 🔴 `P.frames` 를 태운다
    data, ids, F = synth_board()
    per, skipped = P.frames(data, ids, F)
    if per:
        d0 = sorted(per)[0]
        tr, ho = per[d0]["tr"], per[d0]["ho"]
        ov = int((tr & ho).sum())
        fin = int((tr | ho).sum())
        ntr, nho = int(tr.sum()), int(ho.sum())
    else:
        ov, fin, ntr, nho = -1, -1, -1, -1
    W["W1 분할(P.frames)"] = w1_frames(
        len(per), len(skipped), ov, ntr, nho, fin,
        bool(skipped and all("게이트" in v for v in skipped.values())))

    # ── W2 / W3 --- `P.fit_predict`
    n = 400
    x, z = st.randn(n), st.randn(n)
    ys = 2.0 * x + 0.3 * st.randn(n)
    yn = st.randn(n)
    itr, iho = np.arange(n) < 300, np.arange(n) >= 300
    ps, _ = P.fit_predict(np.c_[x[itr], z[itr]], ys[itr], np.c_[x[iho], z[iho]])
    pn, _ = P.fit_predict(np.c_[z[itr]], yn[itr], np.c_[z[iho]])
    W["W2 적합기 양성/음성(P.fit_predict)"] = w2_recover(
        round(P.spear(ps, ys[iho]), 6), round(P.spear(pn, yn[iho]), 6), 0.8, 0.25)

    p_a, _ = P.fit_predict(np.c_[x[itr], z[itr]], ys[itr], np.c_[x[iho], z[iho]])
    ys_ho = ys.copy()
    ys_ho[iho] = st.permutation(ys_ho[iho]) * 17.0 + 999.0
    p_ho, _ = P.fit_predict(np.c_[x[itr], z[itr]], ys_ho[itr], np.c_[x[iho], z[iho]])
    ys_tr = ys.copy()
    ys_tr[itr] = st.permutation(ys_tr[itr]) * 17.0 + 999.0
    p_tr, _ = P.fit_predict(np.c_[x[itr], z[itr]], ys_tr[itr], np.c_[x[iho], z[iho]])
    W["W3 🔴🔴 누출 --- 양방향(P.fit_predict)"] = w3_leak(
        float(np.max(np.abs(p_a - p_ho))), float(np.max(np.abs(p_a - p_tr))), 1e-12, 1e-6)

    # ── W4 --- `P.card`
    W["W4 가짓수 게이트(P.card)"] = w4_card(P.card(np.full(50, 0.5)), P.card(st.randn(50)), 2)

    # ── W5 --- 🔴 `P.pooled_delta`
    fake = {"A": {"유보 행": 100, "ρ": {"C": 0.30, "B": 0.20}},
            "B": {"유보 행": 50, "ρ": {"C": 0.50, "B": 0.20}},
            "C": {"유보 행": 25, "ρ": {"C": 0.40, "B": 0.20}}}
    flip = {"A": {"유보 행": 25, "ρ": fake["A"]["ρ"]},
            "B": {"유보 행": 50, "ρ": fake["B"]["ρ"]},
            "C": {"유보 행": 100, "ρ": fake["C"]["ρ"]}}
    pv, den = P.pooled_delta(fake, "C", "B")
    pf, denf = P.pooled_delta(flip, "C", "B")
    W["W5 묶음 가중(P.pooled_delta)"] = w5_pool(
        round(float(pv), 9), round(float(pf), 9), int(den), int(denf), 0.10, 0.30)

    # ── W6 --- 🔴 `P.boot_ci`
    m = 300
    yb = st.randn(m)
    pb = yb + 1.4 * st.randn(m)
    pc = yb + 1.0 * st.randn(m)
    fake6 = {"A": {"유보 행": m, "예측": {"B": pb, "C": pc}, "_yho": yb,
                   "ρ": {"C": P.spear(pc, yb), "B": P.spear(pb, yb)}}}
    ci = P.boot_ci(fake6, seed=972, B=400)
    lo, hi = ci["🔴 95% 구간"]
    true_d = P.spear(pc, yb) - P.spear(pb, yb)
    W["W6 짝 붓스트랩(P.boot_ci)"] = w6_boot(
        bool(lo <= true_d <= hi), bool(lo <= true_d + 5.0 <= hi),
        ci["🔴 짝 SE(붓스트랩 SD)"], 400, 100)

    # ── W7 --- `P.spear`
    a = np.arange(30, dtype=float)
    W["W7 스피어만(P.spear)"] = w7_spear(
        round(P.spear(a, a), 9), round(P.spear(a, -a), 9),
        bool(not np.isfinite(P.spear(np.full(30, 1.0), a))))

    # ── W8 --- 🔴 `P._sha_file` · `P.blob_sha` · `P.stamp_digest`
    f1 = str(ROOT / "runners/predict971.py")
    f2 = str(ROOT / "runners/predict972.py")
    h1, h1b, h2 = P._sha_file(f1), P._sha_file(f1), P._sha_file(f2)
    bl = P.blob_sha("HEAD", "runners/predict971.py")
    d1 = P.stamp_digest({"a": 1, "b": 2})
    d2 = P.stamp_digest({"a": 1, "b": 2})
    d3 = P.stamp_digest({"a": 1, "b": 3})
    W["W8 sha(P._sha_file·blob_sha·stamp_digest)"] = w8_sha(
        bool(h1 == h1b), bool(h1 == h2), len(h1), bool(h1 == bl),
        bool(d1 == d2), bool(d2 != d3))

    # ── W10 / W11 / W12 --- 🔴 조항 67 + 곁수효 (진짜 판이 필요하다)
    if deep:
        from lab import trendaxes as TA
        from lab.harness import fingerprint
        import dropaudit969 as D9
        w_before, g_before = TA.WIDE, tuple(TA.GRADES)
        da, ia = D9.build(drop_wiki=True, drop_trend=True)
        w_after, g_after = TA.WIDE, tuple(TA.GRADES)
        db, ib = D9.build(drop_wiki=True, drop_trend=True)
        recs = D9.load_series()
        FF, _why = D9.feats(recs)
        fpa, fpb = fingerprint(da)["_전체"], fingerprint(db)["_전체"]

        old_draws = P.RAND_DRAWS
        P.RAND_DRAWS = 5                    # 🔴 배선용 --- 값이 아니라 **일치**를 본다
        try:
            pa, _s1 = P.frames(da, ia, FF)
            pb2, _s2 = P.frames(db, ib, FF)
            rng1 = np.random.RandomState(P.BOOT_SEED)
            for d in sorted(pa):
                pa[d].update(P.arms(pa[d], rng1))
            rng2 = np.random.RandomState(P.BOOT_SEED)
            for d in sorted(pb2):
                pb2[d].update(P.arms(pb2[d], rng2))
            rng3 = np.random.RandomState(P.BOOT_SEED)
            pc3, _s3 = P.frames(da, ia, FF)
            for d in sorted(pc3, reverse=True):        # 🔴 **역순으로 짓는다**
                pc3[d].update(P.arms(pc3[d], rng3))
        finally:
            P.RAND_DRAWS = old_draws

        def _rho(pp):
            return {d: {k: (None if not np.isfinite(v) else round(float(v), 12))
                        for k, v in pp[d]["ρ"].items()} for d in sorted(pp)}
        W["W10 🔴🔴 멱등성(조항 67 ①)"] = w10_idem(_fp(_rho(pa)), _fp(_rho(pb2)), fpa, fpb)
        W["W11 🔴🔴 순서 불변(조항 67 ②)"] = w11_order(_fp(_rho(pa)), _fp(_rho(pc3)))
        ow, og, obites = _old_build_bites()
        W["W12 🔴🔴 곁수효(dropaudit969.build)"] = w12_side(
            w_before, w_after, g_before, g_after, ow, og, obites)

    W["🔴 자리 수"] = sum(1 for k, v in W.items() if isinstance(v, dict) and "통과" in v)
    W["🔴 통과 수"] = sum(1 for k, v in W.items()
                       if isinstance(v, dict) and v.get("통과") is True)
    W["🔴 분자/분모(요약)"] = "%d / %d" % (W["🔴 통과 수"], W["🔴 자리 수"])
    W["🔴 붉은 자리"] = [k for k, v in W.items()
                    if isinstance(v, dict) and "통과" in v and v.get("통과") is not True]
    W["🔴 W9 를 지웠다"] = (
        "971 의 `w9_domgate(7, 12, N_MIN_TRAIN, N_MIN_HOLD)` 는 **7·12 가 리터럴**이고 "
        "`min_tr == N_MIN_TRAIN` 이 **같은 상수를 자기와 비교**한다 --- 어떤 입력에도 안 "
        "떨어지면서 그 사이클이 측정으로 내세우는 두 수를 검사 없이 단언했다. "
        "🔴 971 이 같은 사이클에 만든 **조항 66-⑨ 의 교과서적 사례**라 **지웠다**")
    return W


def sabotage_matrix() -> dict:
    """🔴🔴 **배선이 죽었는지 잰다** --- 생산 함수를 하나씩 망가뜨리고 붉어지는 자리를 센다.

    🔴 티처 #110 실측: 971 의 배선은 **일곱을 동시에 부숴도 9/9** 였다.
    """
    base = wiring_probe(deep=False)
    n_sites = base["🔴 자리 수"]
    out = {}
    for name in PROD_FUNCS:
        orig = getattr(P, name)

        def _stub(*a, **k):
            if name == "frames":
                return {}, {}
            if name == "pooled_delta":
                return 0.0, 0.0
            if name == "boot_ci":
                return {"뽑기": 0, "씨앗": 0, "성공 뽑기": 0,
                        "🔴 짝 SE(붓스트랩 SD)": 0.0,
                        "🔴 95% 구간": [-1e9, 1e9], "🔴 아래끝 > 0": False}
            if name == "fit_predict":
                x = a[2] if len(a) > 2 else k.get("Xho")
                m = len(np.asarray(x, float).reshape(len(x), -1))
                return np.zeros(m), np.zeros(1)
            if name in ("spear",):
                return 0.0
            if name == "card":
                return 2
            if name in ("_sha_file", "blob_sha", "stamp_digest"):
                return "0" * 64
            if name == "arms":
                return {}
            return None
        try:
            setattr(P, name, _stub)
            w = wiring_probe(deep=False)
            out[name] = {"붉은 자리 수": len(w["🔴 붉은 자리"]),
                         "붉은 자리": w["🔴 붉은 자리"],
                         "🔴 잡혔나": bool(len(w["🔴 붉은 자리"]) > 0)}
        except Exception as e:                                     # noqa: BLE001
            out[name] = {"붉은 자리 수": None, "🔴 잡혔나": True,
                         "🔴 터졌다(이것도 잡은 것이다)": "%s: %s" % (type(e).__name__, e)}
        finally:
            setattr(P, name, orig)
    caught = sum(1 for v in out.values() if v["🔴 잡혔나"])
    return {
        "🔴 무엇": ("생산 함수를 **하나씩** 상수로 망가뜨리고 배선이 붉어지는지 센다. "
               "🔴 붉어지지 않는 함수는 **배선이 원리상 안 태우는 함수**다"),
        "🔴 성한 배선 자리 수(deep 제외)": n_sites,
        "함수별": out,
        "🔴 분자/분모": "%d / %d" % (caught, len(PROD_FUNCS)),
        "🔴 971 밑값": "생산 함수 일곱을 **동시에** 부숴도 9/9 였다(티처 #110 중대 1)",
        "🔴 이 대조가 못 덮는 것": ("`predict971.arms` --- **깊은 자리 W10·W11 에서만** 태운다. "
                          "그 자리는 판 자료를 두 번 지어야 해서 파괴 대조 열 판을 못 돌린다"),
        "통과": bool(caught == len(PROD_FUNCS)),
        "🔴 어떤 입력이면 떨어지나":
            "배선 자리가 생산 함수를 안 부르고 **안에서 다시 짜면** 그 함수를 망가뜨려도 "
            "안 붉어져 떨어진다",
    }


# ══════════════════════════════════════════════════════════════════════
# §N 예측 팔 --- 🔴 진짜 귀무
# ══════════════════════════════════════════════════════════════════════
def build_per(rand_draws=RAND_DRAWS, min_train=None):
    """🔴 971 의 생산 함수만으로 유보 예측 팔을 짓는다."""
    import dropaudit969 as D9
    old_r, old_t = P.RAND_DRAWS, P.N_MIN_TRAIN
    P.RAND_DRAWS = rand_draws
    if min_train is not None:
        P.N_MIN_TRAIN = min_train
    try:
        data, ids = D9.build(drop_wiki=True, drop_trend=True)
        recs = D9.load_series()
        F, why = D9.feats(recs)
        per, skipped = P.frames(data, ids, F)
        rng = np.random.RandomState(P.BOOT_SEED)
        for d in sorted(per):
            per[d].update(P.arms(per[d], rng))
    finally:
        P.RAND_DRAWS, P.N_MIN_TRAIN = old_r, old_t
    return data, per, skipped, why


def _ctl_cols(v):
    """그 도메인이 **실제로 쓴** 통제 열(이름은 `arms` 가 기록한 것을 쓴다)."""
    lut = {"wiki_level": v["lvl"], "recent_term": v["rec"]}
    return [lut[nm] for nm in v["🔴 쓴 통제"]]


def perm_null(per, B=PERM_B, seed=PERM_SEED) -> dict:
    """🔴🔴 **정본 자 (사전등록 §3-가)** --- 유보 결과 순열 귀무.

    도메인 **안에서** `y_ho` 를 섞는다. 예측 `pB`·`pC` 는 **학습에서만** 적합돼 고정이므로
    섞기는 **결과와 예측의 짝만** 깬다. 🔴 무작위 열 귀무(중심 −0.0056)와 달리 **중심이 0** 이다.
    """
    doms = [d for d in sorted(per) if per[d]["예측"]["B"] is not None]
    obs, _den = P.pooled_delta(per, "C(통제+들뜸)", "B(통제만)")
    obs_pos = sum(1 for d in doms
                  if per[d]["ρ"]["C(통제+들뜸)"] - per[d]["ρ"]["B(통제만)"] > 0)
    rng = np.random.RandomState(seed)
    dd, allpos, npos = [], 0, []
    for _ in range(B):
        num = den = 0.0
        pos = 0
        for d in doms:
            v = per[d]
            y = v["_yho"]
            yp = y[rng.permutation(len(y))]
            rb = P.spear(v["예측"]["B"], yp)
            rc = P.spear(v["예측"]["C"], yp)
            if np.isfinite(rb) and np.isfinite(rc):
                num += (rc - rb) * len(y)
                den += len(y)
                if rc - rb > 0:
                    pos += 1
        if den:
            dd.append(num / den)
            npos.append(pos)
            if pos == len(doms):
                allpos += 1
    a = np.array(dd, float)
    ge = int((a >= obs).sum())
    p = (ge + 1) / float(len(a) + 1)
    # 🔴🔴 975 수리 --- 974 판은 `p_sign = (allpos + 1) / (B + 1)` 이었다.
    # 그것은 **귀무가 7/7 을 낼 확률**이고 **관측 양수 수(4/7)를 한 번도 안 본다** ---
    # 자료와 무관하게 통과한다(티처 #113 중대). 이제 **관측 이상인 뽑기**를 센다.
    npos_a = np.array(npos)
    ge_pos = int((npos_a >= obs_pos).sum())
    p_sign = (ge_pos + 1) / float(len(a) + 1)
    p_sign_974 = (allpos + 1) / float(len(a) + 1)
    ge5 = int((np.array(npos) >= 5).sum())
    return {
        "🔴 실측 묶음 Δ": round(float(obs), 6),
        "🔴 실측 양수 도메인": "%d / %d" % (obs_pos, len(doms)),
        "뽑기": B, "씨앗": seed, "성공 뽑기": len(a),
        "귀무 중심(평균)": round(float(a.mean()), 6),
        "귀무 SD": round(float(a.std(ddof=1)), 6),
        "귀무 95 분위": round(float(np.percentile(a, 95)), 6),
        "🔴 Δ ≥ 실측 인 뽑기": ge,
        "🔴🔴🔴 순열 p(단측 · 사전등록 §3-가 정본 자)": round(p, 6),
        "🔴🔴 채택(p ≤ 0.05)": bool(p <= 0.05),
        "🔴🔴 부호 일관성 --- 전 도메인 양수인 뽑기": allpos,
        "🔴 부호 일관성 --- 관측(%d) 이상 양수인 뽑기" % obs_pos: ge_pos,
        "🔴🔴🔴 부호 일관성 p(975 수리 · 관측 양수 수를 본다)": round(p_sign, 6),
        "🔴🔴 부호 일관성 채택(p ≤ 0.05)": bool(p_sign <= 0.05),
        "🔴 974 판 부호 일관성 p(전 도메인 양수 · 자료와 무관)": round(p_sign_974, 6),
        "🔴 974 판이 냈을 채택": bool(p_sign_974 <= 0.05),
        "🔴 975 수리가 판정을 뒤집었나": bool((p_sign <= 0.05) != (p_sign_974 <= 0.05)),
        "🔴 참고: 971 의 조건 ⑤(≥5 양수)가 귀무에서 통과하는 비율":
            round(100.0 * ge5 / float(len(a)), 1),
        "🔴 뜻": ("971 은 ⑤를 「7 중 ≥5」로 못 박았다. 🔴 **그 문턱은 귀무에서 위 비율로 "
               "그냥 통과한다** --- 자기 결과를 과소평가한 것이다. **7/7 은 다른 수다**"),
    }


def boot3(per, B=BOOTB, seed=BOOT_SEED) -> dict:
    """🔴 폭 셋 (사전등록 §3-다) --- 유보만 · **학습만** · **이중**."""
    doms = [d for d in sorted(per) if per[d]["예측"]["B"] is not None]
    pre = {d: {"cols": _ctl_cols(per[d]), "exc": per[d]["exc"],
               "y": per[d]["y"], "tr": per[d]["tr"], "ho": per[d]["ho"],
               "yho": per[d]["_yho"], "pB": per[d]["예측"]["B"],
               "pC": per[d]["예측"]["C"]} for d in doms}

    def _run(kind):
        rng = np.random.RandomState(seed)
        out = []
        for _ in range(B):
            num = den = 0.0
            for d in doms:
                q = pre[d]
                tr, ho = q["tr"], q["ho"]
                if kind == "유보만":
                    pB, pC = q["pB"], q["pC"]
                else:
                    ntr = int(tr.sum())
                    it = rng.randint(0, ntr, ntr)
                    ytr = q["y"][tr][it]
                    Xb = np.column_stack([c[tr][it] for c in q["cols"]])
                    Xh = np.column_stack([c[ho] for c in q["cols"]])
                    Xb2 = np.column_stack([c[tr][it] for c in q["cols"]] + [q["exc"][tr][it]])
                    Xh2 = np.column_stack([c[ho] for c in q["cols"]] + [q["exc"][ho]])
                    pB, _ = P.fit_predict(Xb, ytr, Xh)
                    pC, _ = P.fit_predict(Xb2, ytr, Xh2)
                nh = len(q["yho"])
                if kind == "학습만":
                    yb, ib = q["yho"], np.arange(nh)
                else:
                    ib = rng.randint(0, nh, nh)
                    yb = q["yho"][ib]
                rb = P.spear(pB[ib], yb)
                rc = P.spear(pC[ib], yb)
                if np.isfinite(rb) and np.isfinite(rc):
                    num += (rc - rb) * nh
                    den += nh
            if den:
                out.append(num / den)
        a = np.array(out, float)
        lo, hi = np.percentile(a, [2.5, 97.5])
        return {"성공 뽑기": len(a),
                "🔴 짝 SD": round(float(a.std(ddof=1)), 6),
                "🔴 95% 구간": [round(float(lo), 6), round(float(hi), 6)],
                "🔴 아래끝 > 0": bool(lo > 0)}

    r = {"뽑기": B, "씨앗": seed,
         "① 유보만(971 판)": _run("유보만"),
         "② 🔴 학습만 재표집": _run("학습만"),
         "③ 🔴🔴 이중(학습 + 유보) --- **판정에 쓰는 폭**": _run("이중")}
    r["🔴 971 이 쓴 폭"] = "① 뿐이다 --- 「적합을 고정했을 때」의 폭(조항 61)"
    return r


def leave_one_out(per) -> dict:
    """🔴 잎-하나-빼기 (사전등록 §3-라) --- **필수 병기**."""
    doms = [d for d in sorted(per) if per[d]["예측"]["B"] is not None]
    full, den = P.pooled_delta(per, "C(통제+들뜸)", "B(통제만)")
    rows = {}
    for d in doms:
        sub = {k: v for k, v in per.items() if k != d}
        v2, den2 = P.pooled_delta(sub, "C(통제+들뜸)", "B(통제만)")
        dd = per[d]["ρ"]["C(통제+들뜸)"] - per[d]["ρ"]["B(통제만)"]
        contrib = dd * per[d]["유보 행"] / float(den)
        rows[d] = {"유보 행": per[d]["유보 행"], "학습 행": per[d]["학습 행"],
                   "이 도메인 Δ": round(float(dd), 6),
                   "🔴 묶음 Δ 기여": round(float(contrib), 6),
                   "🔴 기여 %": round(100.0 * contrib / float(full), 1),
                   "🔴 이것을 빼면 묶음 Δ": round(float(v2), 6),
                   "빼고 난 유보 행 합": int(den2)}
    worst = min(rows, key=lambda k: rows[k]["🔴 이것을 빼면 묶음 Δ"])
    top = max(rows, key=lambda k: rows[k]["🔴 기여 %"])
    return {"묶음 Δ(전량)": round(float(full), 6), "유보 행 합": int(den),
            "도메인별": rows,
            "🔴 최대 기여 도메인": top, "🔴 그 기여 %": rows[top]["🔴 기여 %"],
            "🔴 빼면 가장 낮아지는 도메인": worst,
            "🔴🔴 잎-하나-빼기 최소값": rows[worst]["🔴 이것을 빼면 묶음 Δ"]}


def arm_floor(per, draws) -> dict:
    """🔴 팔 R --- 무작위 열 뽑기별 묶음 Δ 의 95 분위(이 자로 직접 잰 잡음 바닥)."""
    doms = [d for d in sorted(per) if per[d]["예측"]["B"] is not None]
    n = min(len(per[d]["_rs"]) for d in doms)
    rdel = []
    for i in range(n):
        num = den = 0.0
        for d in doms:
            b = per[d]["ρ"]["B(통제만)"]
            r = per[d]["_rs"][i]
            if np.isfinite(b) and np.isfinite(r):
                num += (r - b) * per[d]["유보 행"]
                den += per[d]["유보 행"]
        if den:
            rdel.append(num / den)
    a = np.array(rdel, float)
    return {"뽑기": n, "씨앗 시작": P.RAND_SEED0,
            "중앙값": round(float(np.median(a)), 6),
            "🔴 95 분위": round(float(np.percentile(a, 95)), 6),
            "최대": round(float(a.max()), 6),
            "🔴 971 의 50 뽑기 값": 0.016593,
            "🔴 첫 50 뽑기만 다시 낸 값": round(
                float(np.percentile(a[:50], 95)), 6) if n >= 50 else None}


def assoc_fix(per) -> dict:
    """🔴🔴 3순위 --- **`abs()` 를 뗀다** · **학습 행 안의 연관 ρ 를 낸다**(러너가 0 개였다)."""
    doms = [d for d in sorted(per) if per[d]["예측"]["B"] is not None]
    rows = {}
    num_s = num_a = den = 0.0
    for d in doms:
        v = per[d]
        n = float(v["유보 행"])
        a_ho = P.spear(v["exc"][v["ho"]], v["y"][v["ho"]])
        a_tr = P.spear(v["exc"][v["tr"]], v["y"][v["tr"]])       # 🔴 **새로 내는 수**
        rows[d] = {"유보 행": int(n), "학습 행": v["학습 행"],
                   "🔴 학습 안 연관 ρ": round(float(a_tr), 6),
                   "🔴 유보 안 연관 ρ": round(float(a_ho), 6),
                   "🔴 부호가 갈리나(학습 vs 유보)": bool(np.sign(a_tr) != np.sign(a_ho)),
                   "ρ_A(들뜸만 예측)": round(float(v["ρ"]["A(들뜸만)"]), 6),
                   "Δ(C−B)": round(float(v["ρ"]["C(통제+들뜸)"] - v["ρ"]["B(통제만)"]), 6)}
        num_s += a_ho * n
        num_a += abs(a_ho) * n
        den += n
    signed = num_s / den
    absol = num_a / den
    dpred, _ = P.pooled_delta(per, "C(통제+들뜸)", "B(통제만)")
    flip = [d for d in rows if rows[d]["🔴 부호가 갈리나(학습 vs 유보)"]]
    flip_rows = sum(rows[d]["유보 행"] for d in flip)
    neg_ho = [d for d in rows if rows[d]["🔴 유보 안 연관 ρ"] < 0]
    return {
        "도메인별": rows,
        "🔴 유보 행 가중 연관 ρ --- **부호 있음**": round(float(signed), 6),
        "🔴 유보 행 가중 |연관 ρ| --- 971 이 쓴 수": round(float(absol), 6),
        "묶음 Δρ_pred": round(float(dpred), 6),
        "🔴🔴 971 헤드라인 「연관이 예측보다 몇 배」 --- `abs()` 판": round(absol / dpred, 2),
        "🔴🔴 정정 --- **부호를 살린 판**": round(signed / dpred, 2),
        "🔴 유보 연관이 음수인 도메인": {"목록": neg_ho,
                              "유보 행": sum(rows[d]["유보 행"] for d in neg_ho),
                              "유보 행 %": round(100.0 * sum(
                                  rows[d]["유보 행"] for d in neg_ho) / den, 1)},
        "🔴🔴 971 이 「부호가 뒤집힌다」고 적은 셋": ["도서", "세계애니", "시장팝업"],
        "🔴🔴 실측 --- **학습 연관과 유보 연관의 부호가 갈리는 도메인**": {
            "목록": sorted(flip), "수": len(flip),
            "유보 행": flip_rows, "유보 행 %": round(100.0 * flip_rows / den, 1)},
        "🔴 왜 971 이 틀렸나": ("971 은 `ρ_A`(들뜸만으로 낸 **유보 예측**)와 유보 연관을 견줬는데 "
                       "`|ρ_A| = |유보 연관|` 이 7/7 이고 `ρ_A > 0` 도 7/7 이라 "
                       "**뒤집힘을 원리상 못 본다**. 🔴 **훈련 행 안의 연관을 내는 커밋된 "
                       "러너가 0 개였다** --- 이 절이 그것을 낸다"),
    }


def pooled_mde(per) -> dict:
    """🔴 3순위 --- 사전등록 §4-가 공식의 **실값**(원장의 「약 0.090」)."""
    doms = [d for d in sorted(per) if per[d]["예측"]["B"] is not None]
    ns = [float(per[d]["유보 행"]) for d in doms]
    s = sum(n * n / (n - 1.0) for n in ns)
    se = float(np.sqrt(s) / sum(ns))
    return {"공식": "√(Σ nᵢ²/(nᵢ−1)) / Σ nᵢ",
            "도메인별 유보 행": {d: int(n) for d, n in zip(doms, ns)},
            "Σ nᵢ": int(sum(ns)),
            "🔴 묶음 SE(짝 안 지음 상한)": round(se, 6),
            "🔴🔴 2 SE --- **원장이 「약 0.090」이라 적은 수**": round(2 * se, 6),
            "🔴 971 이 적은 것": "약 0.090 (사전등록의 「≈ 0.045 → ≈ 0.090」을 손으로 옮겼다)"}


def stage_null(side=True) -> dict:
    t0 = time.time()
    data, per, skipped, why = build_per(RAND_DRAWS)
    doms = [d for d in sorted(per) if per[d]["예측"]["B"] is not None]
    dpred, den = P.pooled_delta(per, "C(통제+들뜸)", "B(통제만)")
    dalone, _ = P.pooled_delta(per, "A(들뜸만)", "B(통제만)")
    perm = perm_null(per)
    R = {
        "🔴 사전등록 상수": {"T": P.T, "학습 문턱": P.N_MIN_TRAIN, "유보 문턱": P.N_MIN_HOLD,
                      "능형 λ": P.RIDGE, "순열 뽑기": PERM_B, "순열 씨앗": PERM_SEED,
                      "붓스트랩 뽑기": BOOTB, "붓스트랩 씨앗": BOOT_SEED,
                      "무작위 열 뽑기": RAND_DRAWS, "무작위 열 씨앗 시작": P.RAND_SEED0},
        "🔴 분모 ① 판 도메인": len(data.dom),
        "🔴 분모 ② 게이트 통과 도메인": len(per),
        "🔴 분모 ③ 유보 행 합": int(den),
        "🔴 분모 ④ 학습 행 합": int(sum(v["학습 행"] for v in per.values())),
        "🔴 뺀 도메인과 사유": skipped,
        "🔴🔴 묶음 Δρ_pred(C−B)": round(float(dpred), 6),
        "🔴 묶음 Δ(A−B)": round(float(dalone), 6),
        "🔴 971 과의 차(묶음 Δ)": round(abs(float(dpred) - 0.025527), 9),
        "🔴🔴🔴 §3-가 정본 자 --- 유보 결과 순열 귀무": perm,
        "🔴🔴 §3-다 폭 셋": boot3(per),
        "🔴🔴 §3-라 잎-하나-빼기": leave_one_out(per),
        "🔴 §3-마 팔 R %d 뽑기" % RAND_DRAWS: arm_floor(per, RAND_DRAWS),
        "🔴🔴 3순위 --- 연관 정정과 학습 연관": assoc_fix(per),
        "🔴 3순위 --- 묶음 최소검출효과 실값": pooled_mde(per),
        "도메인별 Δ": {d: {"유보 행": per[d]["유보 행"], "학습 행": per[d]["학습 행"],
                       "ρ_B": round(per[d]["ρ"]["B(통제만)"], 6),
                       "ρ_C": round(per[d]["ρ"]["C(통제+들뜸)"], 6),
                       "🔴 Δ": round(per[d]["ρ"]["C(통제+들뜸)"]
                                    - per[d]["ρ"]["B(통제만)"], 6),
                       "🔴 쓴 통제": per[d]["🔴 쓴 통제"]} for d in doms},
    }
    if side:
        # 🔴 §3-바 곁 팔 --- 판 `MIN_TRAIN = 15`. **판정에 안 쓴다.**
        _d2, per2, sk2, _w2 = build_per(50, min_train=SIDE_MIN_TRAIN)
        d2, den2 = P.pooled_delta(per2, "C(통제+들뜸)", "B(통제만)")
        R["🔴 §3-바 곁 팔(MIN_TRAIN=15 · **판정에 안 쓴다**)"] = {
            "🔴 왜 곁인가": ("분모가 다르면 다른 수다(조항 60). 주 판정은 20/20 이라야 "
                       "971 과 대조된다"),
            "게이트 통과 도메인": len(per2),
            "새로 들어온 도메인": sorted(set(per2) - set(per)),
            "유보 행 합": int(den2),
            "학습 행 합": int(sum(v["학습 행"] for v in per2.values())),
            "묶음 Δρ_pred": round(float(d2), 6),
            "뺀 도메인과 사유": sk2,
        }
    R["초"] = round(time.time() - t0, 1)
    return R


# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["wiring", "null"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", required=True, help="🔴 **고정 sha**")
    a = ap.parse_args()

    out_path = Path(a.out)
    if not out_path.is_absolute():
        out_path = ROOT / "runners" / out_path
    t_start = _now()
    t0 = time.time()
    R = {"🔴 노트": 972, "🔴 레인": "판정", "🔴 축": "C1 상태→예측", "🔴 단계": a.stage,
         "🔴 시작(UTC)": t_start,
         "🔴 사전등록": "docs/prereg_972_c1null.md (측정 전 단독 커밋 8675748ed "
                   "· 2026-08-15T13:44:57Z)"}

    with ReadTap():
        cs0 = code_stamp()
        R["🔴🔴 §S 내가 돌린 러너 ↔ 커밋 blob(F1)"] = ran_vs_blob(a.ref)
        if a.stage == "wiring":
            R["§W 배선 --- 🔴 생산 함수를 태운다"] = wiring_probe(deep=True)
            R["🔴🔴 §V 배선 파괴 대조(sabotage)"] = sabotage_matrix()
        else:
            R["🔴🔴🔴 §N 유보 예측 --- 진짜 귀무"] = stage_null()
        cs1 = code_stamp()

    t_end = _now()
    R["🔴 끝(UTC)"] = t_end
    R["🔴 걸린 초"] = round(time.time() - t0, 1)
    seal = data_seal()
    R["🔴🔴 §D 자료 입력 지문(규칙 C · 971 은 0 개였다)"] = seal
    R["🔴🔴 §Z 소스 대조"] = {
        "시작 code_stamp 요약": P.stamp_digest(cs0),
        "끝 code_stamp 요약": P.stamp_digest(cs1),
        "🔴 주행 중 소스가 바뀌었나": bool(cs0 != cs1),
        "🔴 바뀐 파일": sorted(k for k in set(cs0) | set(cs1) if cs0.get(k) != cs1.get(k)),
        "🔴 잰 소스 sha(전량 · 자르지 않았다)": cs1,
        "🔴 F2 --- code_stamp 가 내가 돌린 러너 전부를 덮는가": {
            "돌린 러너": list(RAN),
            "덮은 러너": [r for r in RAN if r in cs1],
            "분자/분모": "%d / %d" % (len([r for r in RAN if r in cs1]), len(RAN)),
            "통과": bool(all(r in cs1 for r in RAN)),
        },
        "🔴🔴 F3 --- 도장이 **자료 입력**을 덮는가(규칙 C · 971 은 0 개)": {
            "자료 파일 수": seal["🔴 분모: 자료 파일 수"],
            "합친 요약": seal["🔴🔴 합친 요약(전량을 덮는다)"],
            "🔴 어떤 입력이면 떨어지나":
                "`ReadTap` 을 안 걸거나 `data/` 밖만 읽으면 0 이 되어 떨어진다",
            "통과": bool(seal["🔴 분모: 자료 파일 수"] > 0),
        },
    }

    def _clean(o):
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items() if not str(k).startswith("_")
                    and not str(k).startswith("ρ_R(")}
        if isinstance(o, list):
            return [_clean(v) for v in o]
        if isinstance(o, np.ndarray):
            return [float(v) for v in o]
        if isinstance(o, (np.floating, np.integer)):
            return float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return o

    with open(str(out_path), "w", encoding="utf-8") as f:
        json.dump(_clean(R), f, ensure_ascii=False, indent=1)
    print("wrote", out_path, R["🔴 걸린 초"], "s  시작", t_start, "끝", t_end)


if __name__ == "__main__":
    main()
