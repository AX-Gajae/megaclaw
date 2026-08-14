# -*- coding: utf-8 -*-
"""노트 969 — **「쟀는데 설정이 버렸다」**. `WIKI_DROP` / `TREND_DROP` 감사.

사전등록: `docs/prereg_969_dropped.md` (커밋 `5ad33ee76` · 측정 전 단독 커밋).

🔴 **저장소 `lab/loop.py` 를 한 바이트도 안 고친다.** `WIKI_DROP` 은 **메모리 안에서만**
(`L.WIKI_DROP = ()`) 비우고, 주행 시작·끝의 소스 sha256 을 산출물에 박아 증명한다(F5).

🔴 **`--out` 필수.** 쓰기 문지기가 그 파일 하나만 허용한다.

단계: `wiring` → `drop` → `prop` → `game`. 각 산출물이 **시작·끝 시각(UTC)** 과
**시작·끝 `code_stamp`** 를 싣는다(F2 · F8 · §Z 를 주행 사이로 확장).
"""
import argparse
import builtins
import collections
import datetime as dt
import glob
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
os.chdir(str(ROOT))

API0 = dt.date(2015, 7, 1).toordinal()
RECENT = 90
LONG = 365
T = 2025.0
RHO0 = 0.47034252170476804
BOARD_SE = 0.000603
DIAG_NOISE_1COL = 0.01055
DIAG_OPS = 0.00353
ALPHA = 0.05
N_MIN = 30
DRAWS = 50000                #: 🔴 사전등록 §3 이 정한 뽑기 수
PERM_SEED = 12345            #: 🔴 사전등록 §3 이 정한 씨앗


def _now() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ── 쓰기 문지기(967·968 판) ───────────────────────────────────────────
class NoWrite:
    def __init__(self, allow=()):
        self.allow = {str(Path(a).resolve()) for a in allow}
        self.blocked = []

    def _ok(self, p) -> bool:
        try:
            return str(Path(str(p)).resolve()) in self.allow
        except Exception:                                          # noqa: BLE001
            return False

    def _g_open(self, orig):
        def f(file, mode="r", *a, **k):
            if any(m in str(mode) for m in ("w", "a", "x", "+")) and not self._ok(file):
                self.blocked.append(str(file))
                raise PermissionError("🔴 969 문지기: 쓰기 금지 %s" % file)
            return orig(file, mode, *a, **k)
        return f

    def _g_path_open(self, orig):
        def f(self2, mode="r", *a, **k):
            if any(m in str(mode) for m in ("w", "a", "x", "+")) and not self._ok(self2):
                self.blocked.append(str(self2))
                raise PermissionError("🔴 969 문지기: 쓰기 금지 %s" % self2)
            return orig(self2, mode, *a, **k)
        return f

    def _g_path_write(self, orig):
        def f(self2, *a, **k):
            if not self._ok(self2):
                self.blocked.append(str(self2))
                raise PermissionError("🔴 969 문지기: 쓰기 금지 %s" % self2)
            return orig(self2, *a, **k)
        return f

    def _g_os1(self, orig):
        def f(path, *a, **k):
            if not self._ok(path):
                self.blocked.append(str(path))
                raise PermissionError("🔴 969 문지기: 쓰기 금지 %s" % path)
            return orig(path, *a, **k)
        return f

    def _g_os2(self, orig):
        def f(src, dst, *a, **k):
            if not self._ok(dst):
                self.blocked.append(str(dst))
                raise PermissionError("🔴 969 문지기: 쓰기 금지 %s" % dst)
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
        for k, v in self._save.items():
            mod, at = k.rsplit(".", 1)
            setattr({"builtins": builtins, "io": io, "gzip": gzip,
                     "Path": Path, "os": os}[mod], at, v)
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
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / "runners/dropaudit969.py"), str(ROOT / "runners/meta965.py"),
              str(ROOT / "runners/colaudit968.py"), str(ROOT / "runners/ff753.py")]
    return {str(Path(p).relative_to(ROOT)): _sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def src_stamp() -> dict:
    return {Path(p).parent.name + "/" + Path(p).name: _sha_file(p)
            for p in sorted(glob.glob(str(ROOT / "data/ingest/wiki_daily*/*.jsonl.gz")))}


def stamp_digest(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True,
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


# ── 자 ───────────────────────────────────────────────────────────────
def rank_tie(x) -> np.ndarray:
    """동률평균 순위. 🔴 **누적합 훑기** --- 968 은 딕트 집계 · 967 은 정렬 훑기다."""
    x = np.asarray(x, float)
    n = len(x)
    if n == 0:
        return np.empty(0, float)
    o = np.argsort(x, kind="mergesort")
    xs = x[o]
    r = np.empty(n, float)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and xs[j + 1] == xs[i]:
            j += 1
        r[o[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def rank_966(x) -> np.ndarray:
    return np.asarray(x, float).argsort().argsort().astype(float)


def card(v) -> int:
    """유한한 값의 **가짓수**. 🔴 NaN 은 값이 아니다(조항 59)."""
    a = np.asarray(v, float)
    a = a[np.isfinite(a)]
    return int(len(np.unique(a)))


def _z(v) -> np.ndarray:
    v = np.asarray(v, float)
    return (v - v.mean()) / (v.std() + 1e-12)


def _design(n, ctrls, ranker):
    if not ctrls:
        return np.ones((n, 1))
    return np.column_stack([np.ones(n)] + [_z(ranker(c)) for c in ctrls])


def _resid(v, Z, Zp=None):
    Zp = np.linalg.pinv(Z) if Zp is None else Zp
    return v - Z @ (Zp @ v)


def partial(x, y, ctrls, ranker=rank_tie) -> float:
    n = len(x)
    Z = _design(n, ctrls, ranker)
    ex, ey = _resid(_z(ranker(x)), Z), _resid(_z(ranker(y)), Z)
    sx, sy = ex.std(), ey.std()
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    return float((ex * ey).mean() / (sx * sy))


def perm_p(x, y, ctrls, rng, draws=DRAWS, ranker=rank_tie, batch=2000):
    """순열 p. 🔴 **묶음 처리** --- 50,000 뽑기를 실용 시간에 낸다. 결과는 뽑기별 루프와 같다."""
    n = len(y)
    Z = _design(n, ctrls, ranker)
    Zp = np.linalg.pinv(Z)
    rx, ry = _z(ranker(x)), _z(ranker(y))
    ex = _resid(rx, Z, Zp)
    ey = _resid(ry, Z, Zp)
    sx, sy = ex.std(), ey.std()
    obs = 0.0 if (sx < 1e-12 or sy < 1e-12) else float((ex * ey).mean() / (sx * sy))
    ge = 0
    done = 0
    while done < draws:
        b = min(batch, draws - done)
        P = np.empty((n, b))
        for c in range(b):
            P[:, c] = ry[rng.permutation(n)]
        E2 = P - Z @ (Zp @ P)
        s2 = E2.std(axis=0)
        num = (ex[:, None] * E2).mean(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            nulls = np.where((sx < 1e-12) | (s2 < 1e-12), 0.0, num / (sx * s2 + 1e-300))
        ge += int((np.abs(nulls) >= abs(obs) - 1e-15).sum())
        done += b
    p = (1.0 + ge) / (1.0 + draws)
    se = float(np.sqrt(max(p * (1 - p), 0.0) / draws))
    return obs, p, se, ge


def holm(pairs, alpha=ALPHA) -> dict:
    m = len(pairs)
    order = sorted(range(m), key=lambda i: pairs[i][1])
    rej, still = {}, True
    for k, i in enumerate(order):
        thr = alpha / (m - k)
        ok = still and (pairs[i][1] <= thr)
        if not ok:
            still = False
        rej[pairs[i][0]] = {"p": round(pairs[i][1], 7),
                            "Holm 문턱": round(thr, 6), "통과": bool(ok)}
    return {"분모 m": m, "α": alpha, "도메인별": rej,
            "🔴 통과 수": sum(1 for v in rej.values() if v["통과"])}


# ── 자료 ─────────────────────────────────────────────────────────────
def _d2o(n) -> int:
    n = int(n)
    return dt.date(n // 10000, (n // 100) % 100, n % 100).toordinal()


def load_series() -> dict:
    recs = {}
    for base in ("wiki_daily", "wiki_daily959"):
        for p in sorted(glob.glob(str(ROOT / "data/ingest" / base / "*.jsonl.gz"))):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for line in f:
                    r = json.loads(line)
                    k = r["키"]
                    if k in recs and len(recs[k]["날짜"]) >= len(r["날짜"]):
                        continue
                    recs[k] = r
    return recs


def feats(recs: dict) -> tuple:
    F, why = {}, collections.Counter()
    for k, r in recs.items():
        s = r.get("시작일")
        if not s:
            why["시작일 없음"] += 1
            continue
        s0 = dt.date(*map(int, s.split("-"))).toordinal()
        if s0 - RECENT - LONG < API0:
            why["긴 띠가 원천 개시일 밖"] += 1
            continue
        if not r["날짜"]:
            why["자료 0행"] += 1
            continue
        dd = np.array([_d2o(x) for x in r["날짜"]])
        vv = np.asarray(r["조회수"], float)
        m_rec = (dd >= s0 - RECENT) & (dd <= s0 - 1)
        m_lon = (dd >= s0 - RECENT - LONG) & (dd <= s0 - RECENT - 1)
        rec_t = float(np.log1p(vv[m_rec].sum() / RECENT))
        lon_t = float(np.log1p(vv[m_lon].sum() / LONG))
        F[k] = {"recent": rec_t, "long": lon_t, "excite": rec_t - lon_t,
                "n_rec": int(m_rec.sum()), "n_lon": int(m_lon.sum())}
    return F, dict(why)


def build(drop_wiki: bool, drop_trend: bool):
    """🔴 **판 자료를 짓는다.** `drop_wiki=False` 면 `WIKI_DROP` 을 **메모리 안에서만** 비운다."""
    import ff753 as FF
    from lab import loop as L, wikiaxes as WA, trendaxes as TA, idolset as IS
    keep = (tuple(L.WIKI_DROP), tuple(L.TREND_DROP))
    try:
        if not drop_wiki:
            L.WIKI_DROP = ()
        if not drop_trend:
            L.TREND_DROP = ()
        data = FF.shell(FF.base())
    finally:
        L.WIKI_DROP, L.TREND_DROP = keep
    ids = WA._ids()
    ids["영화"] = list(json.loads((ROOT / "data/state/kobis_axes.json")
                                 .read_text(encoding="utf-8")))
    TA.set_wide(False)
    TA.set_grades(("A", "B", "C", "D", "E"))
    ids["팝업"] = list(TA._popup_ids())
    ids["아이돌"] = [r.get("record_id") or r.get("id")
                  for r in IS._rows(mode_wide=True, wide_post=True)]
    return data, ids


# ── 🔴🔴🔴 §A 세 갈래 감사 --- 조항 59 의 **셋째 갈래** ──────────────
def branch3(seen_on: int, seen_off: int) -> str:
    """🔴 **조항 59 셋째 갈래.** 「0 행」·「결측」·**「쟀는데 설정이 버렸다」**를 가른다.

    - `seen_on`  : 현행 설정(`WIKI_DROP` 그대로)에서 마스크가 선 행
    - `seen_off` : 설정을 비운 뒤 마스크가 선 행
    """
    if seen_on > 0:
        return "산다(쟀고 판이 쓴다)"
    if seen_off > 0:
        return "🔴🔴 쟀는데 설정이 버렸다(셋째 갈래)"
    return "🔴 0 행 --- 진짜로 안 쟀다"


def _cols_of(data, d):
    A, M, y, t = data.dom[d]
    return list(data.names.get(d) or []), np.asarray(A, float), np.asarray(M, float), y


def audit_cells(don, doff) -> dict:
    """🔴 **판 전량 (도메인 × 열)** 을 세 갈래로 센다. 🔴 손으로 안 센다."""
    per, rows = {}, []
    for d in sorted(don.dom):
        nm_on, A_on, M_on, y = _cols_of(don, d)
        nm_off, A_off, M_off, _ = _cols_of(doff, d)
        cols = {}
        for j, name in enumerate(nm_on):
            seen_on = int(((M_on[:, j] > 0) & np.isfinite(A_on[:, j])).sum())
            if name in nm_off:
                k = nm_off.index(name)
                seen_off = int(((M_off[:, k] > 0) & np.isfinite(A_off[:, k])).sum())
                card_off = card(A_off[M_off[:, k] > 0, k])
            else:
                seen_off, card_off = 0, 0
            v = branch3(seen_on, seen_off)
            cols[name] = {
                "잰 행(현행)": seen_on,
                "🔴 잰 행(DROP 비움)": seen_off,
                "🔴 값 가짓수(DROP 비움 · 마스크 안)": card_off,
                "값 가짓수(현행 · 전량)": card(A_on[:, j]),
                "갈래": v}
            rows.append((d, name, seen_on, seen_off, card_off, v))
        per[d] = cols
    tot = len(rows)
    b_alive = [r for r in rows if r[5].startswith("산다")]
    b_drop = [r for r in rows if "설정이 버렸다" in r[5]]
    b_zero = [r for r in rows if "0 행" in r[5]]
    return {
        "도메인별": per,
        "🔴🔴 세 갈래 회계": {
            "칸 전량": tot,
            "산다": len(b_alive),
            "🔴🔴 쟀는데 설정이 버렸다": len(b_drop),
            "🔴 0 행 --- 진짜로 안 쟀다": len(b_zero),
            "회계가 맞나": bool(len(b_alive) + len(b_drop) + len(b_zero) == tot),
            "🔴 잰 행이 0 인 칸(현행)": len(b_drop) + len(b_zero)},
        "🔴🔴 버린 칸 목록": sorted([{"도메인": r[0], "열": r[1],
                                "🔴 살아나는 행": r[3], "🔴 값 가짓수": r[4]}
                               for r in b_drop],
                              key=lambda z: -z["🔴 살아나는 행"]),
        "🔴🔴 버린 실측 행 합": int(sum(r[3] for r in b_drop)),
        "🔴 P3 예측(티처 #107)": {"잰 행 0 인 칸": 301, "버린 칸": 21, "버린 행": 3279},
    }


def audit_wiki_level(don, doff, ids, F) -> dict:
    """🔴 **P1·P2** --- 티처 #107 의 네 도메인 표를 **내가 직접** 다시 센다."""
    per = {}
    for d in sorted(don.dom):
        nm_on, A_on, M_on, y = _cols_of(don, d)
        nm_off, A_off, M_off, _ = _cols_of(doff, d)
        if "wiki_level" not in nm_on:
            per[d] = {"🔴 wiki_level 열이 없다": True}
            continue
        j, k = nm_on.index("wiki_level"), nm_off.index("wiki_level")
        on_seen = int(((M_on[:, j] > 0) & np.isfinite(A_on[:, j])).sum())
        off_m = M_off[:, k] > 0
        off_seen = int((off_m & np.isfinite(A_off[:, k])).sum())
        per[d] = {
            "n(판 전량)": int(len(y)),
            "잰 행(현행)": on_seen,
            "🔴🔴 잰 행(WIKI_DROP 비움)": off_seen,
            "🔴🔴 값 가짓수(WIKI_DROP 비움 · 마스크 안)": card(A_off[off_m, k]),
            "값 가짓수(현행 · 전량 --- 966·967·968 이 읽은 것)": card(A_on[:, j]),
            "갈래": branch3(on_seen, off_seen),
            "🔴 통제로 쓸 자격(현행)": "있다" if card(A_on[M_on[:, j] > 0, j]) >= 2 else "🔴 **없다**",
            "🔴 통제로 쓸 자격(비움)": "있다" if card(A_off[off_m, k]) >= 2 else "🔴 **없다**",
        }
    return {"도메인별": per,
            "🔴 P1·P2 예측(티처 #107)": {
                "애니": {"행": 403, "가짓수": 372},
                "시장팝업": {"행": 83, "가짓수": 81},
                "웹툰": {"행": 52, "가짓수": 52},
                "도서": {"행": 25, "가짓수": 23}},
            "🔴 P4 예측(티처 #107)": "펀딩 실측 2행(`wikiaxes.build` 의 `<20` 게이트) · 영화는 `_ids()` 에 없다"}


def knob_census() -> dict:
    """🔴 ㉣ **같은 일을 하는 손잡이 셋을 전수로 센다**(`lab/sideaudit.py:_handled` 가 이미 안다)."""
    out = {"DOMDROP": {}, "BLOCK": [], "WIKI_DROP": [], "TREND_DROP": [], "CAL_KEEP": [],
           "RAW_KEEP": [], "TREND_ZERO_FALSE": []}
    try:
        from lab.forms import REGISTRY
        dm_kind = collections.Counter()
        dm_per = {}
        _MISS = object()
        for nmf, spec in REGISTRY.items():
            cls = spec.get("cls")
            dm = getattr(cls, "DOMAX", _MISS)
            if dm is _MISS:
                kind = "🔴 DOMAX 속성이 **아예 없다**"
            elif isinstance(dm, dict) and not dm:
                kind = "빈 dict"
            elif isinstance(dm, dict):
                kind = "🔴 찬 dict(%d)" % len(dm)
            else:
                kind = "dict 가 아니다(%s)" % type(dm).__name__
            dm_kind[kind] += 1
            dm_per[nmf] = kind
            dd = getattr(cls, "DOMDROP", None)
            if isinstance(dd, dict) and dd:
                out["DOMDROP"][nmf] = {k: list(v) for k, v in dd.items()}
        out["🔴 레지스트리 형식 수"] = len(REGISTRY)
        out["🔴🔴 DOMAX 갈래별 형식 수(P13)"] = dict(dm_kind)
        out["🔴 DOMAX 형식별"] = dm_per
        out["🔴🔴 P13 정밀화"] = (
            "티처 #107 은 「레지스트리 **23 형식 전부** `DOMAX = {}`」라 했다. "
            "🔴 **실측은 그렇지 않다** --- `DOMAX` 속성을 가진 형식은 **2 개뿐**이고 "
            "나머지 **21 개는 속성 자체가 없다**(`_domax` 메서드도 없다). "
            "✅ **결론(`lab/forms.py:989` 는 죽은 코드)은 그대로 옳다** --- "
            "그 줄에 닿을 수 있는 형식 둘이 **둘 다 `DOMAX = {}`** 라서 `if self.DOMAX:` 가 늘 거짓이다. "
            "**이름이 틀렸고 수가 틀렸고 결론은 맞다.**")
    except Exception as e:                                         # noqa: BLE001
        out["DOMDROP 실패"] = repr(e)
    try:
        from lab.fixaxes import BLOCK
        out["BLOCK"] = sorted([list(x) for x in BLOCK])
    except Exception as e:                                         # noqa: BLE001
        out["BLOCK 실패"] = repr(e)
    try:
        from lab import loop as L
        out["WIKI_DROP"] = list(L.WIKI_DROP)
        out["TREND_DROP"] = list(L.TREND_DROP)
        out["CAL_KEEP"] = list(L.CAL_KEEP)
        out["RAW_KEEP"] = list(L.RAW_KEEP)
        out["TREND_ZERO_FALSE"] = list(L.TREND_ZERO_FALSE)
    except Exception as e:                                         # noqa: BLE001
        out["loop 실패"] = repr(e)
    out["🔴 뜻"] = ("같은 일(축을 도메인에서 뺀다)을 하는 손잡이가 **다섯 이상**이고 "
                 "층이 다르다(모형층 `DOMDROP` · 자료층 `BLOCK` · 축층 `*_DROP`/`*_KEEP`). "
                 "🔴 `lab/sideaudit.py:_handled()` 는 셋만 읽는다 --- `CAL_KEEP`·`RAW_KEEP` 은 안 읽는다")
    return out


def forms989() -> dict:
    """🔴 **P13 · 곁** --- `lab/forms.py:989` 가 죽은 코드인가. 0.5 는 어디서 오나."""
    import re
    src = (ROOT / "lab/forms.py").read_text(encoding="utf-8").splitlines()
    hit989 = src[988] if len(src) > 988 else ""
    def _grep(path, pat):
        t = (ROOT / path).read_text(encoding="utf-8").splitlines()
        return [{"줄": i + 1, "원문": ln.strip()}
                for i, ln in enumerate(t) if re.search(pat, ln)]
    return {
        "lab/forms.py:989 원문": hit989.strip(),
        "🔴 `_domax` 를 부르는 자리": _grep("lab/forms.py", r"_domax"),
        "🔴 0.5 채움이 실제로 있는 자리": {
            "lab/wikiaxes.py": _grep("lab/wikiaxes.py", r"0\.5"),
            "lab/harness.py": _grep("lab/harness.py", r"0\.5"),
            "lab/forms.py": _grep("lab/forms.py", r"0\.5"),
        },
        "🔴 뜻": ("조항 65-③ 과 966 논문 초록이 인용한 `lab/forms.py:989` 는 "
                "`if self.DOMAX:` 안에서만 도는데 그 줄에 닿는 형식 둘이 **둘 다 `DOMAX = {}`** 다 --- "
                "**죽은 코드**"),
        "🔴🔴 `WIKI_DROP` 이 실제로 떨어지는 자리": {
            "파일": "lab/harness.py:241",
            "원문": "cols.append(np.full((len(A), 1), 0.5))",
            "기전": ("`WIKI_DROP` 은 축 dict 에서 그 도메인의 항목을 **아예 뺀다**(`loop._wikisub`). "
                   "그러면 `harness.py` 의 `d in byd` 가 거짓이 되어 **경고도 없이** 값 0.5 · 마스크 0 으로 채운다 "
                   "(`quiet` 도 아니고 `d in byd` 가 거짓이라 `_warn` 자체를 안 탄다). "
                   "🔴 **그래서 `A[:, wiki_level]` 은 상수 0.5 이고 `M[:, wiki_level]` 은 전부 0 이다.** "
                   "966·967·968·티처 #106 은 `A` 만 읽고 그것을 「통제」라 불렀다"),
        },
        "🔴 0.5 채움 자리는 둘이 아니라 여럿이다(티처 #107 정밀화)": {
            "티처가 든 둘": ["lab/wikiaxes.py:192", "lab/harness.py:241"],
            "🔴 내가 더 찾은 산 자리": [
                "lab/forms.py:163·166 --- `_feat()` 의 중립 대입(노트 85). 여러 형식이 쓴다",
                "lab/forms.py:607 · 1406 · 1428 · 1540·1542 · 1751·1753 --- 다른 형식들의 같은 관례"],
            "층이 다르다": ("`wikiaxes:192` 는 **도메인 안 결측**(`<20` 게이트를 통과한 도메인의 빈 개체) · "
                       "`harness:241` 은 **도메인 통째 결측**(`WIKI_DROP` 이 만드는 것) · "
                       "`forms:163/166` 은 **모형이 다시 한 번** 메우는 자리"),
        },
        "🔴 `<20` 게이트(P4)": {
            "파일": "lab/wikiaxes.py:189", "원문": "if np.isfinite(raw).sum() < 20: continue",
            "뜻": "실측이 20 개 미만인 도메인은 축을 **아예 안 만든다** --- 그것도 `harness:241` 로 떨어진다"},
    }


def history() -> dict:
    """🔴🔴 **F1** --- `WIKI_DROP` 이 왜 있는지 사료로 확인한다. **지우기 전에 한다.**"""
    def _git(*a):
        r = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotePath=false"] + list(a),
                           capture_output=True)
        return r.stdout.decode("utf-8", "replace")
    out = {}
    for name in ("WIKI_DROP", "TREND_DROP"):
        log = _git("log", "-S", name, "--oneline", "--date=iso", "--", "lab/loop.py")
        lines = [x for x in log.splitlines() if x.strip()]
        out[name] = {"도입/변경 커밋 수": len(lines), "커밋": lines[-8:]}
        if lines:
            first = lines[-1].split()[0]
            out[name]["🔴 최초 커밋 전문"] = _git("show", "--stat",
                                            "--format=%H%n%ci%n%s%n%n%b", first)[:3000]
    # 원장이 진짜 사료다
    led = json.loads((ROOT / "data/lab/denominator.json").read_text(encoding="utf-8"))
    keys = [k for k in led if ("위키" in k and "잘라" in k) or "검색" in k or "달력" in k]
    out["🔴🔴 원장 항목(사료)"] = {k: led[k] for k in keys[:6]}
    return out


# ── 🔴 §B 명제 --- 규격 D 를 `WIKI_DROP` 비운 채로 다시 잰다 ─────────
def dom_frame_D(data, ids, F, d):
    A, M, y, t = data.dom[d]
    nm = list(data.names.get(d) or [])
    kk = ids.get(d)
    if not kk or len(kk) != len(y) or "wiki_level" not in nm:
        return None
    j = nm.index("wiki_level")
    val = {k: f["excite"] for k, f in F.items() if f["n_rec"] > 0 and f["n_lon"] > 0}
    raw = np.array([val.get(k, np.nan) for k in kk], float)
    lvl = np.asarray(A[:, j], float)
    msk = np.asarray(M[:, j], float) > 0
    rec = np.array([F[k]["recent"] if k in F else np.nan for k in kk], float)
    lon = np.array([F[k]["long"] if k in F else np.nan for k in kk], float)
    yy = np.asarray(y, float)
    ok = (np.isfinite(raw) & np.isfinite(yy) & np.isfinite(lvl) & np.isfinite(rec))
    return raw[ok], yy[ok], lvl[ok], rec[ok], lon[ok], msk[ok], ok


def prop(data, ids, F, tag, draws=DRAWS) -> dict:
    """규격 D. 🔴 **두 이름(긴 띠 · 들뜸)을 반드시 병기**하고 **Holm(m=10)** 을 낸다.

    🔴 통제 열은 **가짓수 ≥ 2 게이트**를 통과해야 설계에 들어간다(조항 65-④).
    """
    rng_l = np.random.RandomState(PERM_SEED)
    rng_e = np.random.RandomState(PERM_SEED + 1)
    per, ps_l, ps_e = {}, [], []
    for d in sorted(data.dom):
        fr = dom_frame_D(data, ids, F, d)
        if fr is None:
            continue
        x, y, lvl, rec, lon, msk, ok = fr
        if len(x) < N_MIN:
            continue
        c_lvl, c_rec = card(lvl), card(rec)
        ctrls, names, dropped = [], [], []
        for nmc, v, c in (("wiki_level", lvl, c_lvl), ("recent_term", rec, c_rec)):
            if c >= 2:
                ctrls.append(v)
                names.append(nmc)
            else:
                dropped.append({"열": nmc, "가짓수": c,
                                "판정": "🔴 통제로 못 쓴다(가짓수 < 2) --- 조항 65-④"})
        r_l, p_l, se_l, ge_l = perm_p(lon, y, ctrls, rng_l, draws=draws)
        r_e, p_e, se_e, ge_e = perm_p(x, y, ctrls, rng_e, draws=draws)
        per[d] = {
            "n": int(len(x)),
            "🔴 쓴 통제": names, "🔴 뺀 통제": dropped,
            "wiki_level 가짓수(규격 D 행 안)": c_lvl,
            "🔴 wiki_level 마스크가 선 행(규격 D 행 안)": int(msk.sum()),
            "🔴 긴 띠 ρ": round(r_l, 6), "긴 띠 p": round(p_l, 7),
            "긴 띠 MC SE": round(se_l, 7), "긴 띠 k(귀무 ≥ 관측)": ge_l,
            "🔴 들뜸 ρ": round(r_e, 6), "들뜸 p": round(p_e, 7),
            "들뜸 MC SE": round(se_e, 7), "들뜸 k(귀무 ≥ 관측)": ge_e,
        }
        ps_l.append((d, p_l))
        ps_e.append((d, p_e))
    H_l = holm(ps_l) if ps_l else None
    H_e = holm(ps_e) if ps_e else None

    def mc(H, key):
        if not H:
            return None
        rows, near = {}, []
        for d, v in H["도메인별"].items():
            se = per[d][key]
            p, thr = v["p"], v["Holm 문턱"]
            n2 = bool(abs(p - thr) < 2 * se)
            rows[d] = {"p": p, "Holm 문턱": thr, "MC SE": se,
                       "|p − 문턱| ÷ SE": (round(abs(p - thr) / se, 2) if se > 0 else None),
                       "🔴 씨앗을 바꾸면 뒤집힐 수 있나(2 SE 안)": n2}
            if n2:
                near.append(d)
        return {"도메인별": rows, "🔴 2 SE 안": sorted(near), "🔴 그 수": len(near)}

    return {
        "🔴 설정": tag, "뽑기": draws, "씨앗": PERM_SEED, "N_MIN": N_MIN,
        "도메인별": per,
        "🔴🔴 Holm(긴 띠 이름 --- 사전등록이 정한 주 이름)": H_l,
        "🔴🔴 Holm(들뜸 이름 --- 병기)": H_e,
        "🔴 통과 수(긴 띠)": (H_l or {}).get("🔴 통과 수"),
        "🔴 통과 수(들뜸)": (H_e or {}).get("🔴 통과 수"),
        "🔴 MC 안정성(긴 띠)": mc(H_l, "긴 띠 MC SE"),
        "🔴 MC 안정성(들뜸)": mc(H_e, "들뜸 MC SE"),
    }


# ── §W 배선 검사 --- 🔴 입력은 전부 `probes`(인자)에서 온다 ──────────
def probe_pack() -> dict:
    """🔴 티처 #107 의 진단(「뿌리가 0 --- 자유 이름이 전부 모듈 전역」)에 대한 공학적 답.

    검사가 자기 입력을 **인자로 받게** 만든다. 자 B 가 여기 값을 아무렇게나 갈면
    예외가 아니라 **다른 값**이 나와야 「떨어진다」를 볼 수 있다.
    """
    n = 200
    return {
        "세갈래 사례": collections.OrderedDict([
            ("현행 0 · 비움 403", (0, 403)),
            ("현행 0 · 비움 0", (0, 0)),
            ("현행 100 · 비움 100", (100, 100)),
            ("🔴 빈 입력(0 · 0)", (0, 0)),
        ]),
        "열": collections.OrderedDict([
            ("빈 배열", np.array([], float)),
            ("상수 열(0.5 × 100)", np.full(100, 0.5)),
            ("전부 NaN(100)", np.full(100, np.nan)),
            ("난수 100", np.random.RandomState(1).rand(100)),
            ("두 값만", np.array([0.5] * 50 + [0.7] * 50)),
        ]),
        "결과 y": np.arange(n, dtype=float)[::-1],
        "상수 열": np.full(n, 0.5),
        "난수 열": np.random.RandomState(7).rand(n),
        "난수 x": np.random.RandomState(11).rand(n),
        "난수 y": np.random.RandomState(12).rand(n),
        "순열 뽑기": 400,
        "Holm 사례": [("a", 0.0001), ("b", 0.004), ("c", 0.02), ("d", 0.9)],
    }


def _arr(v, fb):
    try:
        a = np.asarray(v, float).ravel()
        return a if a.size else np.asarray(fb, float)
    except Exception:                                              # noqa: BLE001
        return np.asarray(fb, float)


def wiring(probes) -> dict:
    """조항 64 개정 2 · 65. 🔴 **자리마다 「어떤 입력이면 떨어지나」 + 그 입력의 값.**"""
    W = {}
    P = probes if isinstance(probes, dict) else {}

    # W1 --- 🔴🔴 셋째 갈래가 진짜로 셋으로 갈리는가
    cases = P.get("세갈래 사례")
    cases = cases if isinstance(cases, dict) else {}
    vs = {}
    for k, v in cases.items():
        try:
            vs[str(k)] = branch3(*[int(x) for x in v])
        except Exception:                                          # noqa: BLE001
            vs[str(k)] = "🔴 못 읽었다"
    W["W1 조항 59 셋째 갈래"] = {
        "🔴 입력별 값": vs,
        "🔴 분자(입력별)": {"서로 다른 갈래 수": len(set(vs.values()))},
        "🔴 어떤 입력이면 떨어지나":
            ("`probes[\"세갈래 사례\"]` 의 「현행 0 · 비움 403」을 「현행 0 · 비움 0」으로 갈면 "
             "**같은 갈래로 뭉개져 통과가 False 가 된다**"),
        "통과": bool(
            "설정이 버렸다" in vs.get("현행 0 · 비움 403", "")
            and "0 행" in vs.get("현행 0 · 비움 0", "")
            and vs.get("현행 100 · 비움 100", "").startswith("산다")
            and len(set(vs.values())) == 3),
    }

    # W2 --- 가짓수 자
    cols = P.get("열")
    cols = cols if isinstance(cols, dict) else {}
    vals = {str(k): card(v) for k, v in cols.items()}
    W["W2 가짓수 자"] = {
        "🔴 입력별 값": vals,
        "🔴 분자(입력별)": vals,
        "🔴 어떤 입력이면 떨어지나":
            "`probes[\"열\"][\"난수 100\"]` 을 상수 열로 갈면 가짓수가 1 이 되어 떨어진다",
        "통과": bool(vals.get("난수 100", 0) > 1 and vals.get("상수 열(0.5 × 100)", -1) == 1
                    and vals.get("전부 NaN(100)", -1) == 0 and vals.get("빈 배열", -1) == 0
                    and vals.get("두 값만", -1) == 2),
    }

    # W3 --- 동률평균과 966 자가 상수 열에서 갈리는가
    yv = _arr(P.get("결과 y"), np.arange(200, dtype=float)[::-1])
    const = np.resize(_arr(P.get("상수 열"), np.full(len(yv), 0.5)), len(yv))
    rnd = np.resize(_arr(P.get("난수 열"), np.random.RandomState(7).rand(len(yv))), len(yv))
    r966 = partial(const, yv, [], ranker=rank_966)
    rtie = partial(const, yv, [], ranker=rank_tie)
    W["W3 두 자"] = {
        "🔴 입력별 값": {"상수 열 --- 966 자": round(r966, 6),
                    "상수 열 --- 동률평균": round(rtie, 6),
                    "난수 열 --- 966 자": round(partial(rnd, yv, [], ranker=rank_966), 6),
                    "난수 열 --- 동률평균": round(partial(rnd, yv, [], ranker=rank_tie), 6)},
        "🔴 분자(입력별)": {"두 자의 차(상수 열)": float(abs(r966 - rtie))},
        "🔴 어떤 입력이면 떨어지나":
            "`probes[\"상수 열\"]` 을 난수로 갈면 두 자가 같아져 떨어진다",
        "통과": bool(abs(rtie) < 1e-12 and abs(r966) > 0.5),
    }

    # W4 --- 🔴 순열 p 가 뽑기 수에 반응하는가(MC SE 가 √draws 로 준다)
    xr = _arr(P.get("난수 x"), np.random.RandomState(11).rand(200))
    yr = _arr(P.get("난수 y"), np.random.RandomState(12).rand(200))
    m = min(len(xr), len(yr))
    xr, yr = xr[:m], yr[:m]
    dr = int(P.get("순열 뽑기") or 400)
    o1, p1, se1, k1 = perm_p(xr, yr, [], np.random.RandomState(3), draws=dr, batch=200)
    o2, p2, se2, k2 = perm_p(xr, yr, [], np.random.RandomState(3), draws=dr * 4, batch=200)
    W["W4 순열 뽑기 수"] = {
        "🔴 입력별 값": {"뽑기 %d" % dr: {"p": round(p1, 5), "MC SE": round(se1, 6), "k": k1},
                    "뽑기 %d" % (dr * 4): {"p": round(p2, 5), "MC SE": round(se2, 6), "k": k2},
                    "관측 ρ(둘 다 같아야 한다)": [round(o1, 9), round(o2, 9)]},
        "🔴 분자(입력별)": {"SE 비(작은쪽/큰쪽)": round(se1 / (se2 + 1e-18), 3)},
        "🔴 어떤 입력이면 떨어지나":
            ("`probes[\"순열 뽑기\"]` 를 0 이나 음수로 갈면 뽑기가 안 돌아 SE 비가 무너진다. "
             "또 관측 ρ 가 뽑기 수에 따라 달라지면 순열이 관측을 오염시킨 것이다"),
        "통과": bool(abs(o1 - o2) < 1e-12 and 1.6 < se1 / (se2 + 1e-18) < 2.6),
    }

    # W5 --- Holm 이 진짜 계단인가
    hc = P.get("Holm 사례")
    hc = list(hc) if isinstance(hc, (list, tuple)) else []
    pairs = [(str(a), float(b)) for a, b in hc]
    H = holm(pairs) if pairs else None
    H0 = holm([(a, 0.9) for a, _ in pairs]) if pairs else None
    H1 = holm([(a, 1e-9) for a, _ in pairs]) if pairs else None
    #: 🔴🔴 **정직 신고** --- 처음 이 자리는 「통과 수 == 2」라는 **리터럴**이었고
    #: 그것은 **내가 손으로 센 수였고 틀렸다**(기계는 3 을 낸다: 0.02 ≤ α/2 = 0.025).
    #: 배선 검사가 **첫 주행에서 나를 물었다.** 리터럴을 지우고 **입력에서 계산되는
    #: 성질**로 바꿨다 --- 조항 64(「리터럴 `통과` 는 검사가 아니다」)의 뜻 그대로다.
    ok5 = None
    if H:
        srt = sorted(pairs, key=lambda z: z[1])
        m = len(srt)
        thr_ok = all(H["도메인별"][d]["Holm 문턱"] == round(ALPHA / (m - k), 6)
                     for k, (d, _) in enumerate(srt))
        seq = [H["도메인별"][d]["통과"] for d, _ in srt]
        mono = all(not (seq[i] and not seq[i - 1]) for i in range(1, m))
        step = all(H["도메인별"][d]["통과"] == (p <= H["도메인별"][d]["Holm 문턱"] and
                                            all(seq[:k]))
                   for k, (d, p) in enumerate(srt))
        ok5 = bool(thr_ok and mono and step
                   and H0["🔴 통과 수"] == 0 and H1["🔴 통과 수"] == m)
    W["W5 Holm"] = {
        "🔴 입력별 값": {"준 사례": H, "전부 p=0.9": H0["🔴 통과 수"] if H0 else None,
                    "전부 p=1e−9": H1["🔴 통과 수"] if H1 else None},
        "🔴 분자(입력별)": {"통과 수(준 사례)": (H or {}).get("🔴 통과 수"),
                     "m": (H or {}).get("분모 m"),
                     "문턱이 α/(m−k) 인가": thr_ok if H else None},
        "🔴 어떤 입력이면 떨어지나":
            ("`probes[\"Holm 사례\"]` 를 전부 0.9 로 갈면 통과 수가 **0** · 전부 1e−9 로 갈면 **m** 이다. "
             "그 둘이 안 나오거나 계단이 단조가 아니면 떨어진다"),
        "🔴🔴 정직 신고": ("이 자리는 처음에 「통과 수 == 2」라는 **리터럴**이었다 --- "
                     "**내가 손으로 센 수였고 틀렸다**(기계는 3). 배선 검사가 첫 주행에서 나를 물었고, "
                     "리터럴을 **입력에서 계산되는 성질**로 바꿨다(조항 64)"),
        "통과": bool(ok5),
    }

    # W6 --- 🔴 `build(drop_wiki=False)` 가 저장소를 안 건드리는가 · 되돌리는가
    from lab import loop as L
    before = _sha_file(ROOT / "lab/loop.py")
    keep = tuple(L.WIKI_DROP)
    try:
        L.WIKI_DROP = ()
        inside = tuple(L.WIKI_DROP)
    finally:
        L.WIKI_DROP = keep
    after = _sha_file(ROOT / "lab/loop.py")
    W["W6 저장소 무변"] = {
        "🔴 입력별 값": {"주행 전 lab/loop.py sha256": before,
                    "주행 후 lab/loop.py sha256": after,
                    "메모리 안에서 비웠을 때": list(inside),
                    "되돌린 뒤": list(L.WIKI_DROP)},
        "🔴 분자(입력별)": {"sha 같은가": bool(before == after)},
        "🔴 어떤 입력이면 떨어지나":
            "`lab/loop.py` 를 실제로 고치면 두 sha 가 갈려 떨어진다(F5)",
        "통과": bool(before == after and inside == () and tuple(L.WIKI_DROP) == keep
                    and len(keep) == 5),
    }

    W["🔴 통과 수"] = sum(1 for k, v in W.items()
                       if isinstance(v, dict) and v.get("통과") is True)
    W["🔴 자리 수"] = sum(1 for k, v in W.items() if isinstance(v, dict) and "통과" in v)
    return W


# ── 게임 --- 🔴 3순위 ────────────────────────────────────────────────
def game_close(data, ids, F, draws) -> dict:
    """🔴 **게임을 한 번에 닫는다.** 두 이름 · 여러 씨앗 · MC SE 병기."""
    fr = dom_frame_D(data, ids, F, "게임")
    if fr is None:
        return {"🔴 못 쟀다": "게임 규격 D 틀을 못 만들었다"}
    x, y, lvl, rec, lon, msk, ok = fr
    ctrls = [c for c, nm in ((lvl, "wiki_level"), (rec, "recent_term")) if card(c) >= 2]
    used = [nm for c, nm in ((lvl, "wiki_level"), (rec, "recent_term")) if card(c) >= 2]
    out = {"n": int(len(x)), "🔴 쓴 통제": used,
           "wiki_level 가짓수": card(lvl), "🔴 뽑기": draws}
    for nm, v, sd in (("긴 띠", lon, PERM_SEED), ("들뜸", x, PERM_SEED + 1)):
        r, p, se, k = perm_p(v, y, ctrls, np.random.RandomState(sd), draws=draws)
        out[nm] = {"ρ": round(r, 6), "p": round(p, 7), "MC SE": round(se, 7),
                   "k(귀무 ≥ 관측)": k,
                   "Holm 3위 문턱 0.00625 통과": bool(p <= 0.00625),
                   "|p − 0.00625| ÷ SE": (round(abs(p - 0.00625) / se, 2) if se > 0 else None)}
    out["🔴 예측(티처 #107)"] = {"들뜸 200,000 기준값 p": 0.005185,
                            "긴 띠 p": "≈0.0200 · 문턱에서 4.5 SE",
                            "씨앗 300개 통과율": "176/300 = 58.7%(2,000 뽑기)"}
    out["🔴 968 의 산수 정정"] = {
        "968 이 적은 필요 뽑기": 32000,
        "🔴 SE = 문턱/4 에 필요한 뽑기(p̂=0.009)":
            int(round(0.009 * (1 - 0.009) / (0.00625 / 4) ** 2)),
        "🔴 SE = 문턱/4 에 필요한 뽑기(p=0.005185)":
            int(round(0.005185 * (1 - 0.005185) / (0.00625 / 4) ** 2)),
        "🔴 32,000 은 SE = 문턱의 몇 분의 1인가":
            round(0.00625 / float(np.sqrt(0.009 * (1 - 0.009) / 32000)), 1)}
    return out


# ── main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["wiring", "drop", "prop", "game"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--draws", type=int, default=DRAWS)
    a = ap.parse_args()

    out_path = Path(a.out)
    if not out_path.is_absolute():
        out_path = ROOT / "runners" / out_path
    t_start, cs0 = _now(), code_stamp()
    t0 = time.time()
    R = {"🔴 단계": a.stage, "🔴 시작(UTC)": t_start,
         "🔴 사전등록": "docs/prereg_969_dropped.md (5ad33ee76 · 측정 전 단독 커밋)"}

    with NoWrite(allow=[str(out_path)]) as G:
        if a.stage == "wiring":
            R["§W 배선"] = wiring(probe_pack())
            R["§K 손잡이 전수(㉣)"] = knob_census()
            R["§F forms.py:989(P13 · 곁)"] = forms989()
        else:
            don, ids = build(drop_wiki=True, drop_trend=True)
            doff, _ = build(drop_wiki=False, drop_trend=False)
            recs = load_series()
            F, why = feats(recs)
            R["§0 자료"] = {"원천 레코드": len(recs), "특징 낸 키": len(F), "버린 사유": why,
                         "판 도메인": sorted(don.dom), "원천 sha 수": len(src_stamp())}
            if a.stage == "drop":
                R["🔴🔴 §A 판 전량 세 갈래 감사(P3)"] = audit_cells(don, doff)
                R["🔴🔴 §B wiki_level 도메인별(P1·P2·P4)"] = audit_wiki_level(don, doff, ids, F)
                R["🔴🔴 §H 사료 --- WIKI_DROP 은 왜 있나(F1)"] = history()
            elif a.stage == "prop":
                R["🔴 §C 명제 --- 현행(WIKI_DROP 그대로)"] = prop(don, ids, F, "현행", a.draws)
                R["🔴🔴 §D 명제 --- WIKI_DROP 비움"] = prop(doff, ids, F, "WIKI_DROP=() · TREND_DROP=()", a.draws)
            elif a.stage == "game":
                R["🔴 §G 게임 --- 현행"] = game_close(don, ids, F, a.draws)
                R["🔴🔴 §G2 게임 --- DROP 비움"] = game_close(doff, ids, F, a.draws)
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
        "🔴 뜻": ("F3·F5·F8. 이 요약을 다른 산출물과 대조하면 **주행 사이** 표류도 잡힌다 --- "
                "968 의 §Z 는 주행 안만 봐서 교차 표류를 원리상 못 봤다"),
    }
    with open(str(out_path), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1)
    print("wrote", out_path, R["🔴 걸린 초"], "s  시작", t_start, "끝", t_end)


if __name__ == "__main__":
    main()
