# -*- coding: utf-8 -*-
"""노트 967 [판정] — **명제를 살려 다시 낸다, 좁혀서**.

사전등록: ``docs/prereg_967_narrowclaim.md``

966 이 낸 명제는 *「집단 관심의 기억은 90일보다 길다」* 다. 967 은 그 명제를
**내 손으로 깨 보고** 깨지지 않은 부분만 다시 낸다. 깨는 자는 셋이다 ---

* **동률평균**: 966 의 ``argsort().argsort()`` 는 동률 블록에서 **행 번호를 순위로**
  쓴다. 판의 행은 결과로 정렬돼 있으므로 **정답표가 열에 샌다**.
* **띠 안 0행은 결측**: 966 은 원천 개시일 *밖*에만 조항 59 를 적용했다.
  띠 *안*에서 0행인 것도 **0 이 아니라 결측**이다.
* **자기 열의 앞항 통제**: ``excite = recent - long`` 이므로 ``recent`` 를 안 빼면
  들뜸이 최근 수준의 대리 변수가 될 수 있다.

쓰는 법::

    python3 runners/narrow967.py --stage prop    # §A~§E 명제(빠르다)
    python3 runners/narrow967.py --stage self    # §F 자기 검사(빈 입력 심기)
    python3 runners/narrow967.py --stage board   # §G 판 24주행(약 25분)

🔴 **``_NoWrite`` 는 이제 죽은 코드가 아니다** --- 966 은 ``with _NoWrite(...): pass``
라 본문이 비었고 실제 쓰기가 ``with`` **밖**에서 났다(티처 #105 M4). 967 은 쓰기를
문지기 **안**에서 하고, 문지기가 **실제로 무는지**를 §F 가 심어서 보인다.
"""
from __future__ import annotations

import argparse
import builtins
import datetime as dt
import glob
import gzip
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
os.chdir(str(ROOT))

OUT = ROOT / "runners/out967_narrow.json"

API0 = dt.date(2015, 7, 1).toordinal()
RECENT = 90
LONG = 365
COL = "wiki_excite"
T = 2025.0
SEEDS = 12
RHO0 = 0.47034
#: 🔴 사전등록 §1-나 --- 채택 문턱 **정본**. 0.01055 는 `docs/목표.md:138` 이 철회했다.
ADOPT_T = 0.00353
DIAG_T_1COL = 0.01055        #: 진단 수치(검출 바닥)로만 쓴다
ALPHA = 0.05                 #: 사전등록 §3
DRAWS = 2000                 #: 사전등록 §3
N_MIN = 30                   #: 966 과 같은 최소 표본


# ── 쓰기 문지기 (🔴 966 의 죽은 코드를 살렸다) ─────────────────────────
class NoWrite:
    """허용한 자리 말고는 못 쓰게 막는다. **본문이 비어 있지 않다.**

    966 판은 ``builtins.open``·``io.open``·``gzip.open`` 셋만 후킹했고
    ``with`` 본문이 ``pass`` 였다. 967 은 ``Path.write_text/write_bytes/open`` 과
    ``os.open/replace/rename/remove`` 까지 물고, **실제 쓰기를 이 안에서** 한다.
    """

    def __init__(self, allow=()):
        self.allow = {str(Path(a).resolve()) for a in allow}
        self.blocked = []

    def _ok(self, p) -> bool:
        return str(Path(str(p)).resolve()) in self.allow

    def _g_open(self, orig):
        def f(file, mode="r", *a, **k):
            if any(m in str(mode) for m in ("w", "a", "x", "+")) and not self._ok(file):
                self.blocked.append(str(file))
                raise PermissionError("🔴 967 문지기: 쓰기 금지 %s" % file)
            return orig(file, mode, *a, **k)
        return f

    def _g_path_open(self, orig):
        def f(self2, mode="r", *a, **k):
            if any(m in str(mode) for m in ("w", "a", "x", "+")) and not self._ok(self2):
                self.blocked.append(str(self2))
                raise PermissionError("🔴 967 문지기: 쓰기 금지 %s" % self2)
            return orig(self2, mode, *a, **k)
        return f

    def _g_path_write(self, orig):
        def f(self2, *a, **k):
            if not self._ok(self2):
                self.blocked.append(str(self2))
                raise PermissionError("🔴 967 문지기: 쓰기 금지 %s" % self2)
            return orig(self2, *a, **k)
        return f

    def _g_os1(self, orig):
        def f(path, *a, **k):
            if not self._ok(path):
                self.blocked.append(str(path))
                raise PermissionError("🔴 967 문지기: 쓰기 금지 %s" % path)
            return orig(path, *a, **k)
        return f

    def _g_os2(self, orig):
        def f(src, dst, *a, **k):
            if not self._ok(dst):
                self.blocked.append(str(dst))
                raise PermissionError("🔴 967 문지기: 쓰기 금지 %s" % dst)
            return orig(src, dst, *a, **k)
        return f

    def __enter__(self):
        self._save = {
            "builtins.open": builtins.open, "io.open": io.open, "gzip.open": gzip.open,
            "Path.open": Path.open, "Path.write_text": Path.write_text,
            "Path.write_bytes": Path.write_bytes, "os.replace": os.replace,
            "os.rename": os.rename, "os.remove": os.remove}
        builtins.open = self._g_open(self._save["builtins.open"])
        io.open = self._g_open(self._save["io.open"])
        gzip.open = self._g_open(self._save["gzip.open"])
        Path.open = self._g_path_open(self._save["Path.open"])
        Path.write_text = self._g_path_write(self._save["Path.write_text"])
        Path.write_bytes = self._g_path_write(self._save["Path.write_bytes"])
        os.replace = self._g_os2(self._save["os.replace"])
        os.rename = self._g_os2(self._save["os.rename"])
        os.remove = self._g_os1(self._save["os.remove"])
        return self

    def __exit__(self, *e):
        builtins.open = self._save["builtins.open"]
        io.open = self._save["io.open"]
        gzip.open = self._save["gzip.open"]
        Path.open = self._save["Path.open"]
        Path.write_text = self._save["Path.write_text"]
        Path.write_bytes = self._save["Path.write_bytes"]
        os.replace = self._save["os.replace"]
        os.rename = self._save["os.rename"]
        os.remove = self._save["os.remove"]
        return False


def _sha_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _d2o(n) -> int:
    n = int(n)
    return dt.date(n // 10000, (n // 100) % 100, n % 100).toordinal()


# ── §1 자 ─────────────────────────────────────────────────────────────
def rank_avg(x) -> np.ndarray:
    """🔴 **동률평균 순위**(이 실험실의 정본 · 카드 2026-08-10)."""
    x = np.asarray(x, float)
    n = len(x)
    order = np.argsort(x, kind="mergesort")
    sx = x[order]
    r = np.empty(n, float)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sx[j + 1] == sx[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def rank_966(x) -> np.ndarray:
    """🔴 966 의 자 --- ``argsort().argsort()``. **동률 블록에서 행 번호가 순위다.**"""
    return np.asarray(x, float).argsort().argsort().astype(float)


def _z(v) -> np.ndarray:
    v = np.asarray(v, float)
    return (v - v.mean()) / (v.std() + 1e-12)


def _resid(v, Z) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(Z, v, rcond=None)
    return v - Z @ beta


def _corr_resid(rx, ry, Z) -> float:
    ex, ey = _resid(rx, Z), _resid(ry, Z)
    sx, sy = ex.std(), ey.std()
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    return float((ex * ey).mean() / (sx * sy))


def _design(n, ctrls, ranker):
    return (np.column_stack([np.ones(n)] + [_z(ranker(c)) for c in ctrls])
            if ctrls else np.ones((n, 1)))


def partial(x, y, ctrls, ranker=rank_avg) -> float:
    """통제 여러 개를 뺀 부분 스피어만. `ctrls` 가 비면 그냥 스피어만."""
    n = len(x)
    return _corr_resid(_z(ranker(x)), _z(ranker(y)), _design(n, ctrls, ranker))


def perm_p(x, y, ctrls, rng, draws=DRAWS, ranker=rank_avg) -> tuple:
    """라벨 순열 양측 p. 돌려주는 것: (관측 ρ, p, 바닥 |ρ| 95%).

    🔴 **순위는 한 번만 낸다** --- ``rank(y[perm]) == rank(y)[perm]`` 이므로
    순열마다 다시 매기는 것과 **비트로 같다**(그리고 2,000배 빠르다).
    """
    n = len(y)
    Z = _design(n, ctrls, ranker)
    rx, ry = _z(ranker(x)), _z(ranker(y))
    obs = _corr_resid(rx, ry, Z)
    null = np.empty(draws)
    for i in range(draws):
        null[i] = _corr_resid(rx, ry[rng.permutation(n)], Z)
    ge = int((np.abs(null) >= abs(obs) - 1e-15).sum())
    return obs, (1.0 + ge) / (1.0 + draws), float(np.percentile(np.abs(null), 95))


def holm(pairs, alpha=ALPHA) -> dict:
    """Holm–Bonferroni. `pairs` = [(이름, p), ...]. 🔴 **사전등록 §3 이 정한 자.**"""
    m = len(pairs)
    order = sorted(range(m), key=lambda i: pairs[i][1])
    rej, still = {}, True
    for rank, i in enumerate(order):
        thr = alpha / (m - rank)
        ok = still and (pairs[i][1] <= thr)
        if not ok:
            still = False
        rej[pairs[i][0]] = {"p": round(pairs[i][1], 6),
                            "Holm 문턱": round(thr, 6), "통과": bool(ok)}
    return {"분모 m": m, "α": alpha, "도메인별": rej,
            "🔴 통과 수": sum(1 for v in rej.values() if v["통과"])}


# ── §2 자료 ───────────────────────────────────────────────────────────
def load_series() -> dict:
    """966 의 ``load_series`` 와 **같은 조리법**(비트 대조를 위해)."""
    recs = {}
    for base in ("wiki_daily", "wiki_daily959"):
        for p in sorted(glob.glob(str(ROOT / "data/ingest" / base / "*.jsonl.gz"))):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for line in f:
                    r = json.loads(line)
                    k = r["키"]
                    if k in recs and len(recs[k]["날짜"]) >= len(r["날짜"]):
                        continue
                    r["_원천"] = base
                    recs[k] = r
    return recs


def feats(recs: dict, *, leak: bool = False) -> tuple:
    """🔴 **두 띠의 항을 따로 낸다.** 966 은 차이 하나만 냈다.

    돌려주는 것: (`키` → dict, 진단). dict 에는
    ``recent``·``long``·``excite966``·``n_rec``·``n_lon`` 이 들어간다.
    ``n_lon == 0`` 이면 ``long`` 은 **결측**이다(조항 59 를 띠 **안**에도).
    """
    F, diag = {}, {"쓴 최대날짜 − 시작일(일)": [], "무효 사유": {}}
    for k, r in recs.items():
        s = r.get("시작일")
        if not s:
            diag["무효 사유"]["시작일 없음"] = diag["무효 사유"].get("시작일 없음", 0) + 1
            continue
        s0 = dt.date(*map(int, s.split("-"))).toordinal()
        if s0 - RECENT - LONG < API0:
            diag["무효 사유"]["긴 띠가 원천 개시일 밖"] = \
                diag["무효 사유"].get("긴 띠가 원천 개시일 밖", 0) + 1
            continue
        if not r["날짜"]:
            diag["무효 사유"]["자료 0행"] = diag["무효 사유"].get("자료 0행", 0) + 1
            continue
        dd = np.array([_d2o(x) for x in r["날짜"]])
        vv = np.asarray(r["조회수"], float)
        hi = s0 + RECENT if leak else s0 - 1
        m_rec = (dd >= s0 - RECENT) & (dd <= hi)
        m_lon = (dd >= s0 - RECENT - LONG) & (dd <= s0 - RECENT - 1)
        used = dd[m_rec | m_lon]
        if len(used):
            diag["쓴 최대날짜 − 시작일(일)"].append(int(used.max() - s0))
        rec_t = float(np.log1p(vv[m_rec].sum() / RECENT))
        lon_t = float(np.log1p(vv[m_lon].sum() / LONG))
        F[k] = {"recent": rec_t, "long": lon_t, "excite966": rec_t - lon_t,
                "n_rec": int(m_rec.sum()), "n_lon": int(m_lon.sum())}
    return F, diag


def spec_val(F: dict, spec: str) -> dict:
    """규격별 `키` → 들뜸 값. 규격 C·D 는 **두 띠 모두 실자료**인 행만 남긴다."""
    if spec in ("A", "B", "C"):
        return {k: f["excite966"] for k, f in F.items()}
    if spec == "D":
        return {k: f["excite966"] for k, f in F.items()
                if f["n_rec"] > 0 and f["n_lon"] > 0}
    raise ValueError(spec)


SPEC = {
    "A": {"자": "argsort(966)", "행": "966 유효 전부(띠 안 0행 = 0)",
          "통제": ["wiki_level"]},
    "B": {"자": "동률평균", "행": "966 유효 전부(띠 안 0행 = 0)",
          "통제": ["wiki_level"]},
    "C": {"자": "동률평균", "행": "966 유효 전부(띠 안 0행 = 0)",
          "통제": ["wiki_level", "recent_term"]},
    "D": {"자": "동률평균", "행": "🔴 **두 띠 모두 실자료 1행 이상**",
          "통제": ["wiki_level", "recent_term"]},
}


def board_keys() -> tuple:
    import ff753 as FF
    from lab import wikiaxes as WA, trendaxes as TA, idolset as IS
    data = FF.shell(FF.base())
    ids = WA._ids()
    ids["영화"] = list(json.loads((ROOT / "data/state/kobis_axes.json")
                                 .read_text(encoding="utf-8")))
    TA.set_wide(False)
    TA.set_grades(("A", "B", "C", "D", "E"))
    ids["팝업"] = list(TA._popup_ids())
    ids["아이돌"] = [r.get("record_id") or r.get("id")
                  for r in IS._rows(mode_wide=True, wide_post=True)]
    return data, ids


def dom_frame(data, ids, F, spec, d):
    """도메인 한 개의 (x, y, 통제들, ok 마스크). 못 재면 None."""
    A, M, y, t = data.dom[d]
    nm = list(data.names.get(d) or [])
    kk = ids.get(d)
    if not kk or len(kk) != len(y) or "wiki_level" not in nm:
        return None
    val = spec_val(F, spec)
    raw = np.array([val.get(k, np.nan) for k in kk], float)
    lvl = A[:, nm.index("wiki_level")].astype(float)
    rec = np.array([F[k]["recent"] if k in F else np.nan for k in kk], float)
    ok = np.isfinite(raw) & np.isfinite(np.asarray(y, float)) & np.isfinite(lvl)
    if "recent_term" in SPEC[spec]["통제"]:
        ok &= np.isfinite(rec)
    ctrls = [lvl[ok]] + ([rec[ok]] if "recent_term" in SPEC[spec]["통제"] else [])
    return raw[ok], np.asarray(y, float)[ok], ctrls, ok, rec[ok], lvl[ok]


# ── §A 행 순서가 정답표다 ─────────────────────────────────────────────
def sec_A(data) -> dict:
    """🔴 P1 --- **판의 행 번호가 결과와 완전상관인가.**"""
    out = {}
    for d in sorted(data.dom):
        y = np.asarray(data.dom[d][2], float)
        idx = np.arange(len(y), dtype=float)
        out[d] = {"n": int(len(y)),
                  "ρ(행번호, 결과 y)": round(partial(idx, y, []), 4)}
    worst = [d for d, v in out.items() if abs(v["ρ(행번호, 결과 y)"]) >= 0.9999]
    return {"도메인별": out,
            "🔴 |ρ| ≥ 0.9999 인 도메인": sorted(worst),
            "🔴 분자": len(worst), "🔴 분모: 도메인": len(out),
            "🔴 무엇이면 떨어지나(어떤 입력이면)": (
                "행을 무작위로 섞은 결과 y 를 넣으면 |ρ| 가 0 근처로 떨어져야 한다"),
            "심기: 결과 y 를 섞었을 때 |ρ| 최댓값": None,
            "통과": None}


def sec_A_plant(data, rng) -> dict:
    mx = 0.0
    for d in sorted(data.dom):
        y = np.asarray(data.dom[d][2], float)
        ys = y[rng.permutation(len(y))]
        mx = max(mx, abs(partial(np.arange(len(y), dtype=float), ys, [])))
    return round(float(mx), 4)


# ── §C 결측 회계 ──────────────────────────────────────────────────────
def sec_C(F: dict) -> dict:
    """🔴 P3 --- 966 의 「유효」 안에 **날조된 0.0** 이 몇인가."""
    n = len(F)
    both0 = sum(1 for f in F.values() if f["n_rec"] == 0 and f["n_lon"] == 0)
    lon0 = sum(1 for f in F.values() if f["n_lon"] == 0)
    rec0 = sum(1 for f in F.values() if f["n_rec"] == 0)
    ident = sum(1 for f in F.values()
                if f["n_lon"] == 0 and f["n_rec"] > 0
                and abs(f["excite966"] - f["recent"]) < 1e-12)
    return {"🔴 분모: 966 의 유효 개체": n,
            "🔴 두 띠 모두 0행(excite 가 날조된 0.0)": both0,
            "🔴 긴 띠 0행": lon0,
            "최근 띠 0행": rec0,
            "🔴 긴 띠만 0행 → excite ≡ recent_term": ident,
            "회계: 긴 띠 0행 − 두 띠 0행": lon0 - both0,
            "🔴 두 띠 모두 실자료 있는 행": sum(
                1 for f in F.values() if f["n_rec"] > 0 and f["n_lon"] > 0),
            "🔴 사전등록 §2 문구와 코드가 갈렸다": (
                "사전등록은 「그 개체에 자료가 1행 이상」인데 966 코드는 "
                "`if not r[\"날짜\"]` 라 **띠 밖 아무 데나** 1행이면 통과시킨다(조항 62)")}


def sec_C2(data, ids, F) -> dict:
    """🔴 P4 --- **도메인마다** 띠 안 0행이 몇인가. 966 은 전체 합만 봤다."""
    out = {}
    for d in sorted(data.dom):
        kk = ids.get(d)
        y = data.dom[d][2]
        if not kk or len(kk) != len(y):
            continue
        ks = [k for k in kk if k in F]
        if not ks:
            continue
        lon0 = sum(1 for k in ks if F[k]["n_lon"] == 0)
        rec0 = sum(1 for k in ks if F[k]["n_rec"] == 0)
        both = sum(1 for k in ks if F[k]["n_rec"] > 0 and F[k]["n_lon"] > 0)
        out[d] = {"부착(966 유효)": len(ks),
                  "🔴 긴 띠 0행": lon0,
                  "긴 띠 0행 비율(%)": round(100.0 * lon0 / len(ks), 1),
                  "최근 띠 0행": rec0,
                  "🔴 두 띠 모두 실자료": both}
    return {"도메인별": out,
            "🔴 뜻": ("긴 띠 0행 비율이 높은 도메인일수록 966 의 `excite` 가 "
                    "**최근 수준의 대리 변수**다 --- 아이돌이 그 자리다")}


# ── §B·§D 규격 사다리 ─────────────────────────────────────────────────
def ladder(data, ids, F, draws=DRAWS, seed=967) -> dict:
    out = {}
    for spec in ("A", "B", "C", "D"):
        rng = np.random.RandomState(seed)
        ranker = rank_966 if spec == "A" else rank_avg
        per, ps = {}, []
        for d in sorted(data.dom):
            fr = dom_frame(data, ids, F, spec, d)
            if fr is None:
                continue
            x, y, ctrls, ok, rec, lvl = fr
            if len(x) < N_MIN:
                per[d] = {"n": int(len(x)), "🔴 잰다": False,
                          "왜": "n < %d --- 못 잰다(조항 59)" % N_MIN}
                continue
            rho, p, floor = perm_p(x, y, ctrls, rng, draws=draws, ranker=ranker)
            per[d] = {"n": int(len(x)), "🔴 잰다": True,
                      "🔴 ρ(부분)": round(rho, 4), "p(순열 양측)": round(p, 4),
                      "순열 바닥 |ρ| 95%": round(floor, 4),
                      "바닥을 넘었나": bool(abs(rho) > floor),
                      "곁: 생 ρ(들뜸↔결과)": round(partial(x, y, [], ranker=ranker), 4),
                      "곁: corr(들뜸, recent_term)": round(
                          partial(x, rec, [], ranker=ranker), 4),
                      "곁: ρ(wiki_level ↔ 결과)": round(
                          partial(lvl, y, [], ranker=ranker), 4)}
            ps.append((d, p))
        live = {d: v for d, v in per.items() if v.get("🔴 잰다")}
        H = holm(ps) if ps else {"분모 m": 0, "🔴 통과 수": 0, "도메인별": {}}
        pos = [d for d, v in live.items() if v["🔴 ρ(부분)"] > 0]
        neg = [d for d, v in live.items() if v["🔴 ρ(부분)"] < 0]
        hp = [d for d in H["도메인별"] if H["도메인별"][d]["통과"]]
        out[spec] = {
            "규격": SPEC[spec], "도메인별": per,
            "🔴 분모 사다리": {"판 도메인": len(data.dom), "잰 도메인": len(live),
                         "바닥 넘음": sum(1 for v in live.values() if v["바닥을 넘었나"]),
                         "🔴 Holm 통과": len(hp)},
            "🔴 부호 +": len(pos), "🔴 부호 −": len(neg),
            "🔴 Holm": H,
            "🔴 Holm 통과 도메인": sorted(hp),
            "🔴 Holm 통과한 음수 도메인": sorted(set(hp) & set(neg)),
            "🔴 잰 개체 합": int(sum(v["n"] for v in live.values())),
            "순열 뽑기": draws, "씨앗": seed}
    return out


def _rank966_z(x):
    """🔴 966 의 ``_rank`` **축자 복사**(비트 재현용)."""
    x = np.asarray(x, float)
    o = x.argsort().argsort().astype(float)
    return (o - o.mean()) / (o.std() + 1e-12)


def _partial966(x, y, z) -> float:
    """🔴 966 의 ``_partial`` **축자 복사**(비트 재현용)."""
    rx, ry, rz = _rank966_z(x), _rank966_z(y), _rank966_z(z)
    rx = rx - rz * float((rx * rz).mean())
    ry = ry - rz * float((ry * rz).mean())
    return float((rx * ry).mean() / (rx.std() * ry.std() + 1e-12))


def repro_966(data, ids, F) -> dict:
    """🔴 966 의 §4 를 **비트로** 다시 낸다(자·씨앗·뽑기 수 전부 966 그대로)."""
    rng = np.random.RandomState(966)
    per = {}
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        nm = list(data.names.get(d) or [])
        kk = ids.get(d)
        if not kk or len(kk) != len(y) or "wiki_level" not in nm:
            continue
        val = {k: f["excite966"] for k, f in F.items()}
        raw = np.array([val.get(k, np.nan) for k in kk], float)
        lvl = A[:, nm.index("wiki_level")].astype(float)
        ok = np.isfinite(raw) & np.isfinite(np.asarray(y, float)) & np.isfinite(lvl)
        if ok.sum() < 30:
            per[d] = {"n": int(ok.sum()), "🔴 잰다": False}
            continue
        x, yy, zz = raw[ok], np.asarray(y, float)[ok], lvl[ok]
        r_par = _partial966(x, yy, zz)
        null = np.array([_partial966(x, yy[rng.permutation(len(yy))], zz)
                         for _ in range(1000)])
        fl = float(np.percentile(np.abs(null), 95))
        per[d] = {"n": int(ok.sum()), "🔴 잰다": True,
                  "🔴 들뜸 ↔ 결과(수준을 뺀 뒤)": round(r_par, 4),
                  "순열 바닥 |ρ| 95%": round(fl, 4),
                  "🔴 바닥을 넘었나": bool(abs(r_par) > fl)}
    live = {d: v for d, v in per.items() if v.get("🔴 잰다")}
    return {"도메인별": per, "🔴 잰 도메인": len(live),
            "🔴 바닥을 넘은 도메인": sum(1 for v in live.values() if v["🔴 바닥을 넘었나"]),
            "🔴 부호 +": sum(1 for v in live.values()
                          if v["🔴 들뜸 ↔ 결과(수준을 뺀 뒤)"] > 0),
            "🔴 부호 −": sum(1 for v in live.values()
                          if v["🔴 들뜸 ↔ 결과(수준을 뺀 뒤)"] < 0),
            "🔴 잰 개체 합": int(sum(v["n"] for v in live.values())),
            "자": "argsort(966) · 씨앗 966 · 뽑기 1000 --- 966 과 같다"}


# ── §E 긴 띠 자체 ─────────────────────────────────────────────────────
def sec_E(data, ids, F, draws=DRAWS) -> dict:
    """🔴 P7 --- 수준과 최근항을 뺀 뒤 **긴 띠 자체**가 결과를 어떻게 예측하나."""
    rng = np.random.RandomState(9670)
    per, ps = {}, []
    for d in sorted(data.dom):
        fr = dom_frame(data, ids, F, "D", d)
        if fr is None:
            continue
        x, y, ctrls, ok, rec, lvl = fr
        if len(x) < N_MIN:
            continue
        kk = ids[d]
        lon = np.array([F[k]["long"] if k in F else np.nan for k in kk], float)[ok]
        rho, p, fl = perm_p(lon, y, ctrls, rng, draws=draws)
        per[d] = {"n": int(len(x)), "🔴 ρ(long_term ↔ 결과 | 수준·최근항)": round(rho, 4),
                  "p": round(p, 4), "바닥 |ρ| 95%": round(fl, 4)}
        ps.append((d, p))
    neg = [d for d, v in per.items() if v["🔴 ρ(long_term ↔ 결과 | 수준·최근항)"] < 0]
    return {"도메인별": per, "🔴 음수 도메인": sorted(neg),
            "🔴 분모: 잰 도메인": len(per), "🔴 Holm": holm(ps) if ps else None,
            "🔴 뜻": ("같은 최근 수준이면 오랜 기저가 두꺼울수록 결과가 나쁘다 --- "
                    "들뜸이 양수인 것과 같은 기전이다")}


# ── §F 자기 검사 · 🔴 **빈 입력을 심는다** ────────────────────────────
def make_extra(data, ids, val: dict, *, detach: bool = False) -> tuple:
    """열을 만든다. 🔴 **``constant`` 노브가 없다** --- 966 의 ``constant=True`` 는
    입력을 버리고 ``np.full(n, 0.5)`` 를 냈다. 그래서 **어떤 val 에서도 같은 값**이
    나왔고 W3 이 원리상 못 떨어졌다. 967 은 **오직 ``val`` 에서만** 열을 만든다.
    """
    byd, att = {}, {}
    for d in sorted(data.dom):
        n = len(data.dom[d][2])
        kk = ids.get(d)
        v = np.full(n, 0.5)
        o = np.zeros(n)
        if kk and len(kk) == n:
            raw = np.array([val.get(k, np.nan) for k in kk], float)
            if detach:
                raw = np.roll(raw, 1)
            ok = np.isfinite(raw)
            if ok.sum() >= 2:
                r = rank_avg(raw[ok])           # 🔴 동률평균
                v[ok] = r / (ok.sum() + 1.0)
                o[ok] = 1.0
            att[d] = int(ok.sum())
        else:
            att[d] = 0
        byd[d] = (v, o)
    return {COL: byd}, att


def _uniq(ex) -> int:
    return len({round(float(x), 9) for d in ex[COL]
                for x, o in zip(*ex[COL][d]) if o > 0})


def _att_doms(ex) -> int:
    return sum(1 for d in ex[COL] if float(np.asarray(ex[COL][d][1]).sum()) > 0)


def self_checks(recs, data, ids, F, diag) -> dict:
    """🔴 **검사마다 「어떤 입력이면 떨어지나」를 실제 입력으로 심어서 보인다.**

    966 의 W3·W4 는 **빈 dict 하나로 잡혔다**(티처 #105 C1). 967 의 자리마다
    ``val={}``·전부 0 인 열·난수 열 셋을 먹여 **값이 실제로 변하는지**를 낸다.
    """
    import ff753 as FF
    from lab import forms
    from lab.harness import evaluate

    val = {k: f["excite966"] for k, f in F.items()}
    rng = np.random.RandomState(967)
    PLANT = {
        "실제 val": val,
        "🔴 빈 dict": {},
        "🔴 전부 0 인 val": {k: 0.0 for k in val},
        "난수 val": {k: float(rng.rand()) for k in val},
        "최근항만인 val": {k: F[k]["recent"] for k in F},
    }
    W = {}

    # W1′ 누출
    gaps = diag["쓴 최대날짜 − 시작일(일)"]
    _, ldg = feats(recs, leak=True)
    lg = ldg["쓴 최대날짜 − 시작일(일)"]
    W["W1′ 누출 없음(F5)"] = {
        "분모: 유효 개체": len(gaps),
        "🔴 분자: 시작일 이후 날짜를 쓴 개체": int(sum(1 for g in gaps if g >= 0)),
        "쓴 최대날짜 − 시작일의 최댓값(일)": (int(max(gaps)) if gaps else None),
        "🔴 어떤 입력이면 떨어지나": "leak=True 로 만든 계열(시작일+90 까지 먹는다)",
        "그 입력에서의 값": int(sum(1 for g in lg if g >= 0)),
        "통과": (sum(1 for g in gaps if g >= 0) == 0
               and sum(1 for g in lg if g >= 0) > 0)}

    # W2′ 부착 --- 🔴 빈 dict 를 먹이면 떨어져야 한다
    hold = json.loads((ROOT / "runners/out941_holdout.json")
                      .read_text(encoding="utf-8"))["유보키"]

    def _att(v):
        per, tot, nd = {}, 0, 0
        for d in sorted(hold):
            n = sum(1 for k in hold[d] if k in v)
            per[d] = {"부착": n, "유보": len(hold[d])}
            tot += n
            nd += (n > 0)
        return per, tot, nd

    per, tot, nd = _att(val)
    plant2 = {nm: _att(v)[1] for nm, v in PLANT.items()}
    W["W2′ 유보 부착"] = {
        "도메인별": per, "🔴 분자: 부착 유보 행": tot, "🔴 분모: 유보": 3775,
        "부착률(%)": round(100.0 * tot / 3775, 2),
        "🔴 붙은 도메인": nd, "전체 도메인": 12,
        "🔴 어떤 입력이면 떨어지나": "val={} (빈 dict) --- 부착이 0 이 된다",
        "심은 입력별 부착 행": plant2,
        "통과": tot > 0 and nd >= 2 and plant2["🔴 빈 dict"] == 0}

    # W3′ 열이 상수가 아니다 --- 🔴 **오직 val 에서만 열을 만든다**
    uniq = {nm: _uniq(make_extra(data, ids, v)[0]) for nm, v in PLANT.items()}
    W["W3′ 열이 상수가 아니다(조항 64)"] = {
        "🔴 분자: 서로 다른 값 가짓수(실제 val)": uniq["실제 val"],
        "🔴 어떤 입력이면 떨어지나": (
            "val={} → 가짓수 0 · 전부 0 인 val → 가짓수 1 · "
            "난수 val 은 실제 val 과 **다른** 가짓수를 내야 한다"),
        "심은 입력별 가짓수": uniq,
        "🔴 966 판은 여기서 넷 다 1 을 냈다": (
            "`constant=True` 가 입력을 버리고 np.full(n,0.5) 를 냈다"),
        "통과": (uniq["실제 val"] >= 100 and uniq["🔴 빈 dict"] == 0
               and uniq["🔴 전부 0 인 val"] == 1
               and uniq["난수 val"] != uniq["실제 val"])}

    # W4′ 열이 판에 실제로 붙었나 --- 🔴 이름이 아니라 **부착**을 잰다
    exr, attr = make_extra(data, ids, val)
    d2 = FF.shell({**FF.base(), **exr})
    named = sorted(d for d in d2.dom if COL in (d2.names.get(d) or []))
    plant4 = {nm: _att_doms(make_extra(data, ids, v)[0]) for nm, v in PLANT.items()}
    W["W4′ 열이 판에 붙었다"] = {
        "🔴 분자: 열이 **부착 행을 가진** 도메인": _att_doms(exr),
        "곁: 열 **이름**이 있는 도메인": len(named),
        "분모: 도메인": len(d2.dom),
        "기준선 열 수(도서)": len(data.names["도서"]),
        "처리 열 수(도서)": len(d2.names["도서"]),
        "🔴 어떤 입력이면 떨어지나": (
            "val={} --- **이름은 그대로 12/12 에 붙지만** 부착 도메인이 0 이 된다. "
            "966 의 W4 는 이름만 봐서 빈 dict 에서도 통과 True 였다"),
        "심은 입력별 부착 도메인": plant4,
        "통과": (_att_doms(exr) >= 2 and plant4["🔴 빈 dict"] == 0
               and len(d2.names["도서"]) - len(data.names["도서"]) == 1)}

    # W5′ 그 열이 모형에 닿았다 --- 빈 dict 로도 심는다
    cls = forms.REGISTRY["F18_bagboost"]["cls"]
    sc0 = evaluate(lambda: cls(seed=0), d2, T=T)
    r2 = np.random.RandomState(9671)
    shuf = {COL: {}}
    for d in sorted(data.dom):
        v, o = exr[COL][d]
        p = r2.permutation(len(v))
        shuf[COL][d] = (np.asarray(v)[p], np.asarray(o)[p])
    d3 = FF.shell({**FF.base(), **shuf})
    sc1 = evaluate(lambda: cls(seed=0), d3, T=T)
    moved = sorted(d for d in sc0 if d in sc1 and np.isfinite(sc0[d])
                   and np.isfinite(sc1[d]) and abs(sc0[d] - sc1[d]) > 1e-12)
    ee, _ = make_extra(data, ids, {})
    d4 = FF.shell({**FF.base(), **ee})
    sc2 = evaluate(lambda: cls(seed=0), d4, T=T)
    r3 = np.random.RandomState(9671)
    shufe = {COL: {}}
    for d in sorted(data.dom):
        v, o = ee[COL][d]
        p = r3.permutation(len(v))
        shufe[COL][d] = (np.asarray(v)[p], np.asarray(o)[p])
    d5 = FF.shell({**FF.base(), **shufe})
    sc3 = evaluate(lambda: cls(seed=0), d5, T=T)
    moved_e = sorted(d for d in sc2 if d in sc3 and np.isfinite(sc2[d])
                     and np.isfinite(sc3[d]) and abs(sc2[d] - sc3[d]) > 1e-12)
    W["W5′ 그 열이 모형에 닿았다"] = {
        "🔴 분자: 열만 섞었을 때 점수가 변한 도메인": len(moved),
        "분모: 점수가 난 도메인": len([d for d in sc0 if np.isfinite(sc0[d])]),
        "변한 도메인": moved,
        "판 ρ(씨앗0 · 원본)": round(float(d2.pooled(sc0, T=T)), 6),
        "판 ρ(씨앗0 · 그 열만 섞음)": round(float(d3.pooled(sc1, T=T)), 6),
        "🔴 어떤 입력이면 떨어지나": (
            "val={} 로 만든 열은 전부 중립 0.5·표시자 0 이라 섞어도 점수가 안 변한다"),
        "그 입력에서 변한 도메인 수": len(moved_e),
        "통과": len(moved) >= 1 and len(moved_e) == 0}

    # W6′ 행 정렬
    dex, _ = make_extra(data, ids, val, detach=True)
    tot_rows = int(sum(len(data.dom[d][2]) for d in data.dom))
    same = sum(1 for d in exr[COL]
               for a, b in zip(exr[COL][d][0], dex[COL][d][0]) if abs(a - b) < 1e-12)
    ee2, _ = make_extra(data, ids, {}, detach=True)
    same_e = sum(1 for d in ee[COL]
                 for a, b in zip(ee[COL][d][0], ee2[COL][d][0]) if abs(a - b) < 1e-12)
    W["W6′ 행 정렬이 진짜다"] = {
        "🔴 분자: 한 칸 밀어도 같은 값인 행": same, "분모: 전체 행": tot_rows,
        "🔴 어떤 입력이면 떨어지나": "val={} --- 전부 중립이라 밀어도 전 행이 같다",
        "그 입력에서의 분자": same_e,
        "통과": same < tot_rows and same_e == tot_rows}

    # W7′ 🔴 문지기가 진짜로 무나 --- 966 의 죽은 `_NoWrite` 를 살렸다
    probe = ROOT / "runners/_967_should_not_exist.tmp"
    bit = {}
    with NoWrite(allow=[OUT]) as g:
        for nm, fn in (("builtins.open", lambda: open(str(probe), "w")),
                       ("Path.write_text", lambda: probe.write_text("x")),
                       ("Path.open", lambda: probe.open("w")),
                       ("gzip.open", lambda: gzip.open(str(probe), "wt"))):
            try:
                fn()
                bit[nm] = "🔴 안 물었다"
            except PermissionError:
                bit[nm] = "물었다"
        try:
            with open(str(OUT), "a", encoding="utf-8"):
                pass
            bit["허용한 자리(음성 대조)"] = "통과했다"
        except PermissionError:
            bit["허용한 자리(음성 대조)"] = "🔴 잘못 물었다"
    W["W7′ 쓰기 문지기가 진짜로 문다"] = {
        "심은 쓰기별 결과": bit,
        "막힌 경로 수": len(g.blocked),
        "🔴 어떤 입력이면 떨어지나": (
            "허용 목록 밖 경로에 쓰기를 시도했는데 예외가 안 나면 · "
            "또는 허용한 자리가 막히면"),
        "🔴 966 은 이 자리가 죽어 있었다": (
            "`with _NoWrite(allow=[outp]): pass` --- 본문이 비었고 실제 쓰기는 with 밖"),
        "통과": (all(v == "물었다" for k, v in bit.items() if k != "허용한 자리(음성 대조)")
               and bit["허용한 자리(음성 대조)"] == "통과했다")}
    if probe.exists():
        probe.unlink()

    n_ok = sum(1 for v in W.values() if v.get("통과") is True)
    return {"검사": W, "🔴 분자: 통과": n_ok, "🔴 분모: 돌린 검사": len(W),
            "부착 도메인별": attr,
            "🔴 심은 입력 다섯": sorted(PLANT),
            "🔴 조항 64 개정이 요구하는 것": (
                "「무엇이면 떨어지나」가 아니라 **「어떤 입력이면 떨어지나」** 를 적고 "
                "그 입력을 실제로 먹여 값을 낸다. 순수함수의 손 인자(노브)는 심기가 아니다")}


def audit_966(data, ids, F) -> dict:
    """🔴 P8 --- 966 의 W3·W4 가 **빈 dict 에서도 통과 True** 인지 직접 돌린다."""
    import ff753 as FF
    import longmem966 as L
    val = {k: f["excite966"] for k, f in F.items()}
    R = {}
    rng = np.random.RandomState(9672)
    for nm, v in (("실제 val", val), ("🔴 빈 dict", {}),
                  ("🔴 전부 0 인 val", {k: 0.0 for k in val}),
                  ("난수 val", {k: float(rng.rand()) for k in val}),
                  ("최근항만인 val", {k: F[k]["recent"] for k in F})):
        ex, att = L.make_extra(data, ids, v)
        cex, _ = L.make_extra(data, ids, v, constant=True)
        uniq = len({round(float(x), 9) for d in ex[L.COL]
                    for x, o in zip(*ex[L.COL][d]) if o > 0})
        cuniq = len({round(float(x), 9) for d in cex[L.COL]
                     for x, o in zip(*cex[L.COL][d]) if o > 0})
        # 🔴 966 의 통과식을 **축자로** 다시 쓴다(longmem966.py:252·262)
        w3 = bool(uniq >= 100 and cuniq == 1)
        d2 = FF.shell({**FF.base(), **ex})
        inn = sorted(d for d in d2.dom if L.COL in (d2.names.get(d) or []))
        w4 = bool(len(inn) == len(d2.dom)
                  and len(d2.names["도서"]) - len(data.names["도서"]) == 1)
        R[nm] = {"966 W3 분자(가짓수)": uniq, "966 W3 심은 상수판 가짓수": cuniq,
                 "🔴 966 W3 통과": w3,
                 "966 W4 열 이름이 붙은 도메인": len(inn), "분모: 도메인": len(d2.dom),
                 "🔴 966 W4 통과": w4,
                 "부착 행 합": int(sum(att.values()))}
    return {"입력별": R,
            "🔴 966 W4 가 빈 dict 에서도 통과하나": R["🔴 빈 dict"]["🔴 966 W4 통과"],
            "🔴 966 W3 이 빈 dict 에서도 통과하나": R["🔴 빈 dict"]["🔴 966 W3 통과"],
            "🔴 966 W3 의 심은 상수판이 입력에 의존하나": (
                len({r["966 W3 심은 상수판 가짓수"] for r in R.values()}) > 1),
            "🔴 966 W3 의 분자가 입력에 의존하나": (
                len({r["966 W3 분자(가짓수)"] for r in R.values()}) > 1),
            "🔴 티처 #105 C1 을 내가 다시 센 결과": (
                "**절반만 맞다.** W4 는 빈 dict 에서도 통과 True 다 --- 참. "
                "그러나 W3 은 빈 dict 에서 **떨어진다**(분자 가짓수가 0 이 되어 "
                "`uniq >= 100` 이 거짓). 죽어 있는 것은 W3 의 **심은 falsifier**"
                "(`constant=True` 가 입력을 버리고 np.full(n,0.5) 를 낸다)이지 "
                "W3 의 통과식 전체가 아니다. 🔴 그리고 「분자 3,353 이 값에 안 "
                "의존한다」는 **비지 않은** 입력에 한해 참이다 --- 전부 0 인 val 도 "
                "난수 val 도 3,353 인 이유는 `argsort().argsort()` 가 동률을 안 "
                "다뤄 **어떤 입력에서도 서로 다른 순위 n 개**를 내기 때문이다")}


# ── §G 판 ─────────────────────────────────────────────────────────────
def measure_board(data, ids, F) -> dict:
    import ff753 as FF
    from lab.board import board as B
    val = {k: f["excite966"] for k, f in F.items()
           if f["n_rec"] > 0 and f["n_lon"] > 0}      # 🔴 규격 D 의 행만
    ex, att = make_extra(data, ids, val)
    t0 = time.time()
    b0 = B(data, seeds=SEEDS, T=T)
    t1 = time.time()
    d2 = FF.shell({**FF.base(), **ex})
    b1 = B(d2, seeds=SEEDS, T=T)
    t2 = time.time()
    delta = b1["판"] - b0["판"]
    dom = {d: {"기준선": round(b0["도메인"].get(d, (float("nan"),))[0], 4),
               "처리": round(b1["도메인"].get(d, (float("nan"),))[0], 4),
               "Δ": round(b1["도메인"].get(d, (float("nan"),))[0]
                          - b0["도메인"].get(d, (float("nan"),))[0], 4)}
           for d in sorted(set(b0["도메인"]) & set(b1["도메인"]))}
    return {"열": "규격 D 의 행만 붙인 wiki_excite(동률평균)",
            "부착 도메인별": att,
            "기준선": {"판": b0["판"], "SD": b0["SD"], "SE": b0["SE"]},
            "처리": {"판": b1["판"], "SD": b1["SD"], "SE": b1["SE"]},
            "🔴 기준선이 정본 0.47034 를 재현하나": {
                "정본": RHO0, "실측": round(b0["판"], 6),
                "차": round(abs(b0["판"] - RHO0), 6),
                "통과": bool(abs(b0["판"] - RHO0) < 5e-4)},
            "🔴 Δρ": round(delta, 6),
            "🔴 채택 문턱(정본)": ADOPT_T,
            "곁: 진단 수치(검출 바닥 · 채택 문턱 아님)": DIAG_T_1COL,
            "🔴 Δρ ÷ 문턱": round(delta / ADOPT_T, 4),
            "🔴 이 자를 넘었나": bool(delta >= ADOPT_T),
            "도메인별": dom,
            "초": {"기준선": round(t1 - t0, 1), "처리": round(t2 - t1, 1)}}


# ── 본선 ──────────────────────────────────────────────────────────────
def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--stage", default="prop",
                    choices=["prop", "self", "board", "all"])
    ap.add_argument("--draws", type=int, default=DRAWS)
    a = ap.parse_args()
    outp = Path(a.out).resolve()
    t0 = time.time()

    srcs = sorted(glob.glob(str(ROOT / "data/ingest/wiki_daily*/*.jsonl.gz")))
    R = {"노트": 967, "레인": "판정",
         "사전등록": "docs/prereg_967_narrowclaim.md",
         "명제": ("집단 관심의 기억은 90일보다 길다 --- 좁혀서 다시 낸다"),
         "단계": a.stage,
         "🔴 코드 sha256": _sha_file(__file__),
         "🔴 966 러너 sha256": _sha_file(ROOT / "runners/longmem966.py"),
         "원천 파일 수": len(srcs),
         "원천 파일 sha256": {Path(p).parent.name + "/" + Path(p).name: _sha_file(p)
                        for p in srcs}}

    recs = load_series()
    F, diag = feats(recs)
    R["§1 특징"] = {"원천 개체": len(recs), "🔴 유효 개체(966 과 같은 규칙)": len(F),
                 "무효 사유": diag["무효 사유"]}

    data, ids = board_keys()
    R["§0 판 재현"] = {"도메인": len(data.dom),
                   "유보 합": int(sum(data.weights(T).values())),
                   "통과": int(sum(data.weights(T).values())) == 3775}

    if a.stage in ("prop", "all"):
        rngA = np.random.RandomState(96700)
        sA = sec_A(data)
        sA["심기: 결과 y 를 섞었을 때 |ρ| 최댓값"] = sec_A_plant(data, rngA)
        sA["통과"] = bool(sA["🔴 분자"] >= 1
                        and sA["심기: 결과 y 를 섞었을 때 |ρ| 최댓값"] < 0.5)
        R["§A 판의 행 순서가 정답표다(P1)"] = sA
        R["§C 결측 회계(P3)"] = sec_C(F)
        R["§C2 도메인별 결측 회계(P4)"] = sec_C2(data, ids, F)
        R["§B·D 규격 사다리(P2·P4·P5·P6)"] = ladder(data, ids, F, draws=a.draws)
        R["§A2 966 §4 비트 재현"] = repro_966(data, ids, F)
        R["§E 긴 띠 자체(P7)"] = sec_E(data, ids, F, draws=a.draws)
    if a.stage in ("self", "all"):
        R["§F 자기 검사(빈 입력 심기)"] = self_checks(recs, data, ids, F, diag)
        R["§F2 966 의 W3·W4 감사(P8)"] = audit_966(data, ids, F)
    if a.stage in ("board", "all"):
        R["§G 판(P10)"] = measure_board(data, ids, F)

    R["초"] = round(time.time() - t0, 1)
    R["🔴 끝 시각(UTC)"] = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    # 🔴 쓰기를 문지기 **안**에서 한다(966 은 밖에서 했다).
    with NoWrite(allow=[outp]):
        outp.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(R, ensure_ascii=False, indent=1)[:3000])
    return R


if __name__ == "__main__":
    main()
