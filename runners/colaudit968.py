# -*- coding: utf-8 -*-
"""노트 968 --- **통제 열이 살아 있나.** 사전등록 `docs/prereg_968_deadcontrols.md`.

🔴 **공적 귀속**(사전등록 §0): 이 사이클의 방향과 P1~P7 의 예측값 **전부**는
티처 #106 이 준 것이다. 내가 새로 넣은 것은 셋뿐이다 ---
① 게이트를 **판 전량**(12 도메인 × 모든 열)으로 넓힌 것
② **마스크 가짓수와 값 가짓수를 갈라 센 것**(조항 59: 「0 행」과 「결측」은 둘이다)
③ **판에서 죽은 열을 실제로 빼고 Δρ 를 잰 것**

🔴 **967 의 러너를 임포트하지 않는다.** 순위·잔차화·상관을 **다른 알고리즘**으로 다시 짰다
(동률평균은 **딕트 집계**, 잔차화는 **`pinv` 사영** --- 967 은 정렬 훑기 + `lstsq`).
자료 조리법(띠·유효 규칙)만 같은 규약을 쓴다. 어긋나면 그것이 발견이다.

단계:
  --stage wiring   배선 검사(자리마다 「어떤 입력이면 떨어지나」 + 그 입력의 값)
  --stage prop     열 감사 · P1~P7
  --stage board    판(P9) --- 죽은 열을 빼고 Δρ
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
SEEDS = 12
RHO0 = 0.47034
#: 🔴 **채택 크기는 「못 정했다」**(`docs/목표.md:138`). 아래 둘은 **진단 수치**다.
DIAG_NOISE_1COL = 0.01055    #: 잡음 바닥(노트 892 · 난수 1열)
DIAG_OPS = 0.00353           #: 운영 문턱(2σ · 열 수 불변)
BOARD_SE = 0.000603          #: 판 자의 SE (자 정본 · 노트 891)
ALPHA = 0.05
DRAWS = 2000
N_MIN = 30


# ── 쓰기 문지기 (967 판을 그대로 --- 네 경로 전량 후킹 · 본문이 비어 있지 않다) ──
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
                raise PermissionError("🔴 968 문지기: 쓰기 금지 %s" % file)
            return orig(file, mode, *a, **k)
        return f

    def _g_path_open(self, orig):
        def f(self2, mode="r", *a, **k):
            if any(m in str(mode) for m in ("w", "a", "x", "+")) and not self._ok(self2):
                self.blocked.append(str(self2))
                raise PermissionError("🔴 968 문지기: 쓰기 금지 %s" % self2)
            return orig(self2, mode, *a, **k)
        return f

    def _g_path_write(self, orig):
        def f(self2, *a, **k):
            if not self._ok(self2):
                self.blocked.append(str(self2))
                raise PermissionError("🔴 968 문지기: 쓰기 금지 %s" % self2)
            return orig(self2, *a, **k)
        return f

    def _g_os1(self, orig):
        def f(path, *a, **k):
            if not self._ok(path):
                self.blocked.append(str(path))
                raise PermissionError("🔴 968 문지기: 쓰기 금지 %s" % path)
            return orig(path, *a, **k)
        return f

    def _g_os2(self, orig):
        def f(src, dst, *a, **k):
            if not self._ok(dst):
                self.blocked.append(str(dst))
                raise PermissionError("🔴 968 문지기: 쓰기 금지 %s" % dst)
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


# ── 도장 ──────────────────────────────────────────────────────────────
def _sha_file(p) -> str:
    """🔴 **자르지 않는다**(티처 #105 m1 --- 966 은 `[:32]` 였다)."""
    h = hashlib.sha256()
    with open(str(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def code_stamp() -> dict:
    """🔴 `lab/` 과 이 사이클이 고친 파일 **전부**. `git rev-parse HEAD` 는 안 쓴다."""
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / "runners/colaudit968.py"), str(ROOT / "runners/meta965.py"),
              str(ROOT / "runners/narrow967.py"), str(ROOT / "runners/ff753.py")]
    return {str(Path(p).relative_to(ROOT)): _sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def src_stamp() -> dict:
    return {Path(p).parent.name + "/" + Path(p).name: _sha_file(p)
            for p in sorted(glob.glob(str(ROOT / "data/ingest/wiki_daily*/*.jsonl.gz")))}


# ── §1 자 --- 🔴 967 과 **다른 알고리즘**으로 짰다 ────────────────────
def rank_tie(x) -> np.ndarray:
    """동률평균 순위(정본). 🔴 **딕트 집계**로 낸다 --- 967 은 정렬 훑기다."""
    x = np.asarray(x, float)
    buckets = collections.defaultdict(list)
    for i, v in enumerate(x):
        buckets[v].append(i)
    r = np.empty(len(x), float)
    pos = 0
    for v in sorted(buckets):
        idx = buckets[v]
        mid = pos + (len(idx) + 1) / 2.0
        for i in idx:
            r[i] = mid
        pos += len(idx)
    return r


def rank_966(x) -> np.ndarray:
    """🔴 966 의 자 --- `argsort().argsort()`. **동률 블록에서 행 번호가 순위다.**"""
    return np.asarray(x, float).argsort().argsort().astype(float)


def _z(v) -> np.ndarray:
    v = np.asarray(v, float)
    s = v.std()
    return (v - v.mean()) / (s + 1e-12)


def _resid(v, Z) -> np.ndarray:
    """🔴 **`pinv` 사영** --- 967 은 `lstsq` 다. 상수 열이 있어도 안전하다."""
    return v - Z @ (np.linalg.pinv(Z) @ v)


def _design(n, ctrls, ranker):
    if not ctrls:
        return np.ones((n, 1))
    return np.column_stack([np.ones(n)] + [_z(ranker(c)) for c in ctrls])


def partial(x, y, ctrls, ranker=rank_tie) -> float:
    n = len(x)
    Z = _design(n, ctrls, ranker)
    ex, ey = _resid(_z(ranker(x)), Z), _resid(_z(ranker(y)), Z)
    sx, sy = ex.std(), ey.std()
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    return float((ex * ey).mean() / (sx * sy))


def perm_p(x, y, ctrls, rng, draws=DRAWS, ranker=rank_tie):
    n = len(y)
    Z = _design(n, ctrls, ranker)
    rx, ry = _z(ranker(x)), _z(ranker(y))
    ex = _resid(rx, Z)
    obs_num = None
    ey = _resid(ry, Z)
    sx, sy = ex.std(), ey.std()
    obs = 0.0 if (sx < 1e-12 or sy < 1e-12) else float((ex * ey).mean() / (sx * sy))
    null = np.empty(draws)
    for i in range(draws):
        e2 = _resid(ry[rng.permutation(n)], Z)
        s2 = e2.std()
        null[i] = 0.0 if (sx < 1e-12 or s2 < 1e-12) else float((ex * e2).mean() / (sx * s2))
    ge = int((np.abs(null) >= abs(obs) - 1e-15).sum())
    del obs_num
    return obs, (1.0 + ge) / (1.0 + draws), float(np.percentile(np.abs(null), 95))


def holm(pairs, alpha=ALPHA) -> dict:
    m = len(pairs)
    order = sorted(range(m), key=lambda i: pairs[i][1])
    rej, still = {}, True
    for k, i in enumerate(order):
        thr = alpha / (m - k)
        ok = still and (pairs[i][1] <= thr)
        if not ok:
            still = False
        rej[pairs[i][0]] = {"p": round(pairs[i][1], 6),
                            "Holm 문턱": round(thr, 6), "통과": bool(ok)}
    return {"분모 m": m, "α": alpha, "도메인별": rej,
            "🔴 통과 수": sum(1 for v in rej.values() if v["통과"])}


# ── §2 자료 ───────────────────────────────────────────────────────────
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


def board_keys():
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


# ── 🔴🔴 §A 열 감사 --- 이 사이클의 1순위 ─────────────────────────────
def card(v) -> int:
    """유한한 값의 **가짓수**. 🔴 NaN 은 값이 아니다(조항 59)."""
    a = np.asarray(v, float)
    a = a[np.isfinite(a)]
    return int(len(np.unique(a)))


def col_verdict(mask_card: int, val_card: int, n_seen: int) -> str:
    """🔴 **게이트**: 가짓수 ≥ 2 아니면 「모른다」 --- 그리고 「죽음」과 「모름」을 가른다."""
    if n_seen == 0:
        return "🔴 모른다(잰 행이 0 --- 상수가 아니다 · 조항 59)"
    if mask_card <= 1 and val_card <= 1:
        return "🔴 죽은 열(마스크도 값도 상수)"
    if val_card <= 1:
        return "값은 상수 · 마스크가 변한다(있다/없다가 정보다 --- 죽은 열이 아니다)"
    if val_card == 0:
        return "🔴 모른다"
    return "산다"


def audit_all_columns(data) -> dict:
    """🔴 **판 12 도메인 × 모든 열**의 가짓수 표. 티처는 `wiki_level` 하나만 셌다."""
    per, dead_by_dom, total, dead_total = {}, {}, 0, 0
    dead_names = collections.Counter()
    flat_total, unseen_total = 0, 0
    flat_names = collections.Counter()
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        nm = list(data.names.get(d) or [])
        cols = {}
        for j, name in enumerate(nm):
            mj = np.asarray(M[:, j], float)
            aj = np.asarray(A[:, j], float)
            seen = np.isfinite(aj) & (mj > 0)
            mc, vc = card(mj), card(aj[seen])
            v = col_verdict(mc, vc, int(seen.sum()))
            cols[name] = {"마스크 가짓수": mc, "값 가짓수": vc,
                          "잰 행": int(seen.sum()), "판정": v}
            total += 1
            if v.startswith("🔴 죽은 열"):
                dead_total += 1
                dead_names[name] += 1
            cols[name]["🔴 배선이 죽었나(값도 마스크도 상수 --- GBDT 가 못 가른다)"] = \
                bool(mc <= 1 and vc <= 1)
            if int(seen.sum()) == 0:
                unseen_total += 1
            elif vc <= 1:
                flat_total += 1
                flat_names[name] += 1
        dead = sorted(k for k, v in cols.items() if v["판정"].startswith("🔴 죽은 열"))
        wired_dead = sorted(
            k for k, v in cols.items()
            if v["🔴 배선이 죽었나(값도 마스크도 상수 --- GBDT 가 못 가른다)"])
        flat = sorted(k for k, v in cols.items()
                      if v["잰 행"] > 0 and v["값 가짓수"] <= 1)
        dead_by_dom[d] = dead
        per[d] = {"n 행": int(len(y)), "열 수": len(nm),
                  "🔴 죽은 열 수": len(dead), "🔴 죽은 열": dead,
                  "🔴 배선이 죽은 열 수": len(wired_dead),
                  "🔴 배선이 죽은 열": wired_dead,
                  "🔴 값이 상수인 열 수(회귀 통제로는 죽는다)": len(flat),
                  "🔴 값이 상수인 열": flat,
                  "열별": cols}
    wired_total = sum(len(v["🔴 배선이 죽은 열"]) for v in per.values())
    return {"도메인별": per,
            "🔴🔴 배선이 죽은 칸 수(값도 마스크도 상수)": wired_total,
            "🔴🔴 배선이 죽은 칸 비율": (round(wired_total / total, 4) if total else None),
            "🔴 인식론과 배선은 둘이다(조항 59)": (
                "잰 행이 0 인 칸은 **인식론적으로는 「모른다」**(그 도메인에서 그 축을 "
                "한 행도 안 쟀다)이고 **배선으로는 「죽었다」**(값도 마스크도 상수라 "
                "GBDT 가 원리상 못 가른다). 🔴 사전등록 §2-가 는 이 둘을 한 정의 안에 "
                "넣어 서로 물게 만들었다 --- **갈라서 둘 다 신고한다**"),
            "🔴 (도메인 × 열) 칸 수": total,
            "🔴 죽은 칸 수(마스크도 값도 상수)": dead_total,
            "🔴 값이 상수인 칸 수(마스크는 변할 수 있다)": flat_total,
            "🔴 잰 행이 0 인 칸 수(「모른다」 · 상수가 아니다)": unseen_total,
            "🔴 죽은 칸 비율": round(dead_total / total, 4) if total else None,
            "🔴 값 상수 칸 비율": round(flat_total / total, 4) if total else None,
            "🔴 죽은 열 이름별 도메인 수": dict(dead_names.most_common()),
            "🔴 값 상수 열 이름별 도메인 수": dict(flat_names.most_common()),
            "죽은 열 목록(도메인별)": dead_by_dom,
            "🔴 게이트": ("마스크 가짓수 ≤ 1 **그리고** 값 가짓수 ≤ 1 이면 죽은 열. "
                       "값만 상수인 것은 죽은 열이 아니다 --- 마스크가 정보다(조항 59). "
                       "🔴 다만 **선형 회귀의 통제로는** 값 상수만으로도 배선이 죽는다 --- "
                       "그래서 둘을 갈라 센다")}


def audit_wiki_level(data, ids, F) -> dict:
    """🔴 **P1·P2** --- 티처 #106 이 준 수를 그대로 예측으로 쓴다."""
    per = {}
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        nm = list(data.names.get(d) or [])
        if "wiki_level" not in nm:
            per[d] = {"🔴 wiki_level 열이 없다": True}
            continue
        j = nm.index("wiki_level")
        lvl = np.asarray(A[:, j], float)
        mj = np.asarray(M[:, j], float)
        seen = int(((mj > 0) & np.isfinite(lvl)).sum())
        kk = ids.get(d)
        rowsD = None
        if kk and len(kk) == len(y):
            val = {k: f["excite"] for k, f in F.items()
                   if f["n_rec"] > 0 and f["n_lon"] > 0}
            raw = np.array([val.get(k, np.nan) for k in kk], float)
            rec = np.array([F[k]["recent"] if k in F else np.nan for k in kk], float)
            ok = (np.isfinite(raw) & np.isfinite(np.asarray(y, float))
                  & np.isfinite(lvl) & np.isfinite(rec))
            rowsD = {"n": int(ok.sum()),
                     "wiki_level 가짓수(규격 D 행 안)": card(lvl[ok])}
        per[d] = {"n(판 전량)": int(len(y)),
                  "🔴 wiki_level 값 가짓수": card(lvl),
                  "유한한 값 수": int(np.isfinite(lvl).sum()),
                  "🔴🔴 마스크가 선 행(M > 0)": seen,
                  "🔴🔴 A 가 채움값인가(잰 행 0 인데 값이 상수)":
                      bool(seen == 0 and card(lvl) == 1),
                  "🔴 그 상수값": (float(np.unique(lvl[np.isfinite(lvl)])[0])
                              if card(lvl) == 1 else None),
                  "규격 D 행": rowsD,
                  "🔴 통제로 쓸 자격": ("있다" if card(lvl) >= 2
                                 else "🔴 **없다 --- 가짓수 1**")}
    c1 = sorted(d for d, v in per.items()
                if v.get("🔴 wiki_level 값 가짓수") == 1)
    fill = sorted(d for d, v in per.items()
                  if v.get("🔴🔴 A 가 채움값인가(잰 행 0 인데 값이 상수)"))
    return {"도메인별": per,
            "🔴 가짓수 1 인 도메인": c1,
            "🔴 가짓수 1 인 도메인 수": len(c1),
            "🔴🔴 마스크가 한 행도 안 선 도메인": fill,
            "🔴🔴 그 수": len(fill),
            "🔴🔴 뜻": (
                "그 도메인들에서 `wiki_level` 은 **상수가 아니라 결측이다.** "
                "`lab/forms.py:989` 가 `np.where(M[:, j] > 0, A[:, j], 0.5)` 로 채우고, "
                "A 자체도 그 자리에 **0.5** 를 들고 있다. "
                "🔴 966·967·티처 #106 은 `M` 을 한 번도 안 읽고 `A[:, wiki_level]` 만 읽었다 --- "
                "**채움값을 「통제」라고 불렀다.** 조항 59: 「0 행」과 「결측」은 둘이다"),
            "🔴 판 도메인 수": len(data.dom),
            "🔴 P1·P2 예측(티처 #106)": {"가짓수 1 인 도메인 수": 7,
                                    "애니": 1, "만화": 23, "세계애니": 1087},
            "🔴 조항": ("가짓수 1 인 열을 「통제」라고 적는 것을 금지한다 --- "
                     "절편을 두 번 넣는 것이고, 그 이름은 거짓 기술이다")}


def dom_frame_D(data, ids, F, d):
    """규격 D 한 도메인. 못 재면 None. (x, y, lvl, rec, lon, ok)"""
    A, M, y, t = data.dom[d]
    nm = list(data.names.get(d) or [])
    kk = ids.get(d)
    if not kk or len(kk) != len(y) or "wiki_level" not in nm:
        return None
    val = {k: f["excite"] for k, f in F.items()
           if f["n_rec"] > 0 and f["n_lon"] > 0}
    raw = np.array([val.get(k, np.nan) for k in kk], float)
    lvl = np.asarray(A[:, nm.index("wiki_level")], float)
    rec = np.array([F[k]["recent"] if k in F else np.nan for k in kk], float)
    lon = np.array([F[k]["long"] if k in F else np.nan for k in kk], float)
    yy = np.asarray(y, float)
    ok = (np.isfinite(raw) & np.isfinite(yy) & np.isfinite(lvl) & np.isfinite(rec))
    return raw[ok], yy[ok], lvl[ok], rec[ok], lon[ok], ok


def drop_level_delta(data, ids, F) -> dict:
    """🔴 **P3** --- 규격 D 에서 `wiki_level` 을 빼면 값이 변하나.

    🔴 **인자를 바꿔도 출력이 바이트 동일하면 죽은 배선이다**(조항 64).
    """
    per, nzero = {}, 0
    for d in sorted(data.dom):
        fr = dom_frame_D(data, ids, F, d)
        if fr is None:
            continue
        x, y, lvl, rec, lon, ok = fr
        if len(x) < N_MIN:
            continue
        both = partial(x, y, [lvl, rec])
        only_rec = partial(x, y, [rec])
        only_lvl = partial(x, y, [lvl])
        bare = partial(x, y, [])
        delta = both - only_rec
        if delta == 0.0:
            nzero += 1
        per[d] = {"n": int(len(x)),
                  "wiki_level 가짓수": card(lvl),
                  "🔴 통제 둘(level+recent)": round(both, 4),
                  "🔴 level 을 뺀 것(recent 만)": round(only_rec, 4),
                  "🔴 Δ": float(both - only_rec),
                  "🔴 Δ == 0.0 (바이트 동일)": bool(delta == 0.0),
                  "곁: level 만": round(only_lvl, 4),
                  "곁: 생 ρ": round(bare, 4),
                  "🔴 통제라 적을 자격": ("있다" if card(lvl) >= 2
                                  else "🔴 **없다 --- 가짓수 1**")}
    return {"도메인별": per,
            "🔴 Δ = 0.000000 인 도메인 수": nzero,
            "🔴 잰 도메인 수": len(per),
            "🔴 Δ = 0 인 도메인": sorted(d for d, v in per.items()
                                   if v["🔴 Δ == 0.0 (바이트 동일)"]),
            "🔴 뜻": ("Δ = 0.000000 은 「효과가 작다」가 아니다. "
                    "**인자를 바꿔도 출력이 바이트 동일 = 그 통제는 배선이 죽었다**")}


def anime_artifact(data, ids, F) -> dict:
    """🔴 **P4·P5** --- 966 의 간판이 인공물인가. 966 의 행 집합(규격 A)에서 잰다."""
    out = {}
    for d in ("애니", "만화", "세계애니", "아이돌"):
        if d not in data.dom:
            continue
        A, M, y, t = data.dom[d]
        nm = list(data.names.get(d) or [])
        kk = ids.get(d)
        if not kk or len(kk) != len(y) or "wiki_level" not in nm:
            continue
        val = {k: f["excite"] for k, f in F.items()}          # 규격 A/B --- 전부
        raw = np.array([val.get(k, np.nan) for k in kk], float)
        lvl = np.asarray(A[:, nm.index("wiki_level")], float)
        yy = np.asarray(y, float)
        ok = np.isfinite(raw) & np.isfinite(yy) & np.isfinite(lvl)
        L, Y = lvl[ok], yy[ok]
        n = len(Y)
        if n < N_MIN:
            continue
        rownum = np.arange(n, dtype=float)
        out[d] = {
            "n": n,
            "🔴 wiki_level 값 가짓수": card(L),
            "🔴 966 자 ρ(level, y)": round(partial(L, Y, [], ranker=rank_966), 4),
            "🔴 동률평균 ρ(level, y)": round(partial(L, Y, [], ranker=rank_tie), 4),
            "🔴 ρ(행번호, y) --- 966 자": round(partial(rownum, Y, [], ranker=rank_966), 4),
            "🔴 ρ(행번호, y) --- 동률평균": round(partial(rownum, Y, [], ranker=rank_tie), 4),
            # 🔴🔴 티처 #106 의 **기전 주장**을 직접 잰다:
            #   「`argsort` 가 그 상수를 **행 번호**로 바꿨다」
            #   --- `np.argsort` 의 기본은 **퀵정렬이고 안정정렬이 아니다.**
            "🔴🔴 rank_966(level) 이 행번호(arange)와 같나":
                bool(np.array_equal(rank_966(L), np.arange(n))),
            "🔴🔴 rank_966(level) 이 행번호와 일치하는 자리 비율":
                round(float((rank_966(L) == np.arange(n)).mean()), 4),
            "🔴 ρ(rank_966(level), 행번호)":
                round(float(np.corrcoef(rank_966(L), rownum)[0, 1]), 4),
            "곁: 결과 y 의 가짓수": card(Y),
        }
    return {"도메인별": out,
            "🔴 P4 예측(티처 #106)": {"애니 966 자": -0.1266, "애니 행번호": -0.3603,
                                 "애니 동률평균": 0.0},
            "🔴 P5 예측(티처 #106)": {"만화 966 자": 0.4776, "만화 동률평균": -0.0115},
            "🔴 뜻": ("wiki_level 이 상수면 `argsort().argsort()` 는 그것을 **행 번호**로 "
                    "바꾼다. 그리고 판의 행은 결과로 정렬돼 있다 --- "
                    "**통제 열을 통해 정답표가 샜다**")}


def worldani_suppression(data, ids, F, draws=DRAWS) -> dict:
    """🔴 **P6** --- 세계애니의 억제가 실재하나. 그리고 잔차 공간이 얼마나 얇은가."""
    out = {}
    for d in sorted(data.dom):
        fr = dom_frame_D(data, ids, F, d)
        if fr is None:
            continue
        x, y, lvl, rec, lon, ok = fr
        if len(x) < N_MIN:
            continue
        rl, rr = _z(rank_tie(lvl)), _z(rank_tie(rec))
        r_pear = float(np.corrcoef(lvl, rec)[0, 1]) if card(lvl) >= 2 else None
        r_spear = float((rl * rr).mean()) if card(lvl) >= 2 else None
        # 잔차 공간의 두께: recent 를 level 로 설명한 뒤 남는 분산 비율
        Zl = np.column_stack([np.ones(len(x)), rl])
        res = _resid(rr, Zl)
        share = float(res.var() / (rr.var() + 1e-12))
        out[d] = {
            "n": int(len(x)),
            "wiki_level 가짓수": card(lvl),
            "🔴 생 ρ": round(partial(x, y, []), 4),
            "🔴 level 만": round(partial(x, y, [lvl]), 4),
            "🔴 recent 만": round(partial(x, y, [rec]), 4),
            "🔴 둘 다": round(partial(x, y, [lvl, rec]), 4),
            "🔴 r(recent, level) 피어슨": (round(r_pear, 4) if r_pear is not None
                                     else "🔴 모른다(level 가짓수 1)"),
            "🔴 ρ(recent, level) 동률평균": (round(r_spear, 4) if r_spear is not None
                                       else "🔴 모른다(level 가짓수 1)"),
            "🔴 recent 의 남은 분산 비율(level 을 뺀 뒤)": round(share, 4),
        }
    return {"도메인별": out,
            "🔴 P6 예측(티처 #106 · 세계애니)": {"r(recent,level)": 0.9191, "생": -0.0078,
                                          "level 만": 0.1642, "recent 만": 0.1683,
                                          "둘 다": 0.1747},
            "🔴 경고": ("두 통제의 상관이 높으면 추정치가 **얇은 잔차 공간**에 산다. "
                     "남은 분산 비율을 같이 읽어라 --- 이것은 「효과가 가짜다」가 아니라 "
                     "「이 표본은 그 둘을 원리상 못 가른다」이다")}


def m3_two_names(data, ids, F, draws=DRAWS) -> dict:
    """🔴 **P7 · 티처 #106 M3** --- `excite = recent − long` 이라 이름이 둘이다.

    사전등록 §3-가 가 **측정 전에** 정했다: 헤드라인은 **긴 띠 쪽**으로 적는다.
    """
    rngE = np.random.RandomState(96800)
    rngX = np.random.RandomState(96801)
    per, ps_lon, ps_exc = {}, [], []
    for d in sorted(data.dom):
        fr = dom_frame_D(data, ids, F, d)
        if fr is None:
            continue
        x, y, lvl, rec, lon, ok = fr
        if len(x) < N_MIN:
            continue
        ctrls = [lvl, rec]
        r_e, p_e, f_e = perm_p(x, y, ctrls, rngX, draws=draws)
        r_l, p_l, f_l = perm_p(lon, y, ctrls, rngE, draws=draws)
        r_neg = partial(-lon, y, ctrls)
        per[d] = {"n": int(len(x)),
                  "🔴 들뜸 ρ(| level·recent)": round(r_e, 4), "들뜸 p": round(p_e, 4),
                  "🔴 긴 띠 ρ(| level·recent)": round(r_l, 4), "긴 띠 p": round(p_l, 4),
                  "−긴 띠 ρ": round(r_neg, 4),
                  "🔴 |들뜸 ρ| − |−긴 띠 ρ|": float(abs(r_e) - abs(r_neg)),
                  "🔴 대수적으로 같은가(|Δ| < 1e-9)":
                      bool(abs(abs(r_e) - abs(r_neg)) < 1e-9),
                  "곁: corr(excite, −long) 동률평균": round(partial(x, -lon, []), 4)}
        ps_lon.append((d, p_l))
        ps_exc.append((d, p_e))
    H_l = holm(ps_lon) if ps_lon else None
    H_e = holm(ps_exc) if ps_exc else None

    # 🔴🔴 Holm 결정이 **순열 몬테카를로 잡음** 안에 사는가.
    #   p̂ 는 `draws` 뽑기의 이항 추정이다. SE = sqrt(p(1−p)/draws).
    #   결정이 문턱에서 2 SE 안이면 **씨앗을 바꾸면 뒤집힌다** --- 「통과 3」의 세 번째가 그것이다.
    def mc(H):
        if not H:
            return None
        rows, unstable = {}, []
        for d, v in H["도메인별"].items():
            p, thr = v["p"], v["Holm 문턱"]
            se = float(np.sqrt(max(p * (1 - p), 0.0) / draws))
            near = bool(abs(p - thr) < 2 * se)
            rows[d] = {"p": p, "Holm 문턱": thr, "🔴 몬테카를로 SE": round(se, 6),
                       "|p − 문턱| ÷ SE": (round(abs(p - thr) / se, 2) if se > 0 else None),
                       "🔴 씨앗을 바꾸면 뒤집힐 수 있나(2 SE 안)": near}
            if near:
                unstable.append(d)
        return {"도메인별": rows, "🔴 문턱에서 2 SE 안인 도메인": sorted(unstable),
                "🔴 그 수": len(unstable), "뽑기": draws}

    return {"도메인별": per,
            "🔴🔴 Holm 결정의 몬테카를로 안정성(들뜸)": mc(H_e),
            "🔴🔴 Holm 결정의 몬테카를로 안정성(긴 띠)": mc(H_l),
            "🔴 Holm(들뜸 이름)": H_e,
            "🔴 Holm(긴 띠 이름)": H_l,
            "🔴 사전등록 §3-가 가 정한 헤드라인": "긴 띠 쪽",
            "🔴 헤드라인 통과 수": (H_l or {}).get("🔴 통과 수"),
            "🔴 병기: 들뜸 이름의 통과 수": (H_e or {}).get("🔴 통과 수"),
            "🔴 뜻": ("같은 하나를 두 번 잰 것이다. 두 이름의 통과 수가 다르면 "
                    "**더 적은 쪽**을 적는다 --- 자기 유리한 이름 고르기를 막는다")}


def nan_ledger(data, ids, F) -> dict:
    """🔴 **ⓒ M6** --- 분모가 왜 다른가. 조항 60: 두 수를 이어 붙일 때 분모를 확인하라."""
    per = {}
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        nm = list(data.names.get(d) or [])
        kk = ids.get(d)
        if not kk or len(kk) != len(y) or "wiki_level" not in nm:
            continue
        valA = {k: f["excite"] for k, f in F.items()}
        valD = {k: f["excite"] for k, f in F.items()
                if f["n_rec"] > 0 and f["n_lon"] > 0}
        rawA = np.array([valA.get(k, np.nan) for k in kk], float)
        rawD = np.array([valD.get(k, np.nan) for k in kk], float)
        lvl = np.asarray(A[:, nm.index("wiki_level")], float)
        rec = np.array([F[k]["recent"] if k in F else np.nan for k in kk], float)
        yy = np.asarray(y, float)
        n0 = len(yy)
        fA, fD = np.isfinite(rawA), np.isfinite(rawD)
        fy, fl, fr = np.isfinite(yy), np.isfinite(lvl), np.isfinite(rec)
        nA = int((fA & fy & fl).sum())
        nD = int((fD & fy & fl & fr).sum())
        per[d] = {
            "판 행": n0,
            "🔴 규격 A(966) n": nA,
            "🔴 규격 D n": nD,
            "🔴 차": nA - nD,
            "사유 --- 붙은 개체가 없다": int((~fA).sum()),
            "사유 --- y 가 NaN": int((~fy).sum()),
            "사유 --- wiki_level 이 NaN": int((~fl).sum()),
            "사유 --- recent_term 이 NaN": int((~fr).sum()),
            "사유 --- 두 띠 중 하나가 0행(A 엔 있고 D 엔 없다)":
                int((fA & ~fD).sum()),
            "🔴 회계가 맞나(A − D = A 에만 있는 행 + D 통제 결측)":
                bool(nA - nD == int((fA & fy & fl & ~(fD & fr)).sum())),
        }
    return {"도메인별": per,
            "🔴 조항 60": ("두 수를 이어 붙일 때 분모가 같은지 확인하라. "
                        "규격 A 의 n 과 규격 D 의 n 은 **다른 분모다**")}


# ── §W 배선 검사 --- 🔴 자리마다 「어떤 입력이면」 + **그 입력의 값** ──
def probe_pack(data) -> dict:
    """🔴🔴 **968 신설 — 배선 검사의 입력을 「인자」로 만든다.**

    왜: `meta965.py` 의 자 B 는 **감싸는 함수의 자유 이름 중 모듈 전역이 아닌 것**만
    뿌리로 잡아 무작위 변조한다. 967 의 검사들은 입력을 **함수 안에서 모듈 전역으로
    만들어** 썼고, 그래서 자 B 가 갈 것이 없어 **「뿌리가 0」**으로 떨어졌다.
    🔴 **티처 #106 은 그 원인을 「자 B 가 numpy 배열·판 `Data` 를 못 만들어서」라 했는데,
    968 이 `--genver 2` 로 그 생성기를 실제로 달아 보니 「모른다」가 8/9 로 그대로였다.**
    원인은 생성기가 아니라 **검사가 자기 입력을 인자로 안 받는 것**이었다.

    그래서 입력 꾸러미를 여기서 만들어 `wiring(..., probes)` 로 **넘긴다.**
    안에서는 전부 `.get(...)` 으로 읽어서, 자 B 가 아무 값이나 꽂아도 예외가 아니라
    **다른 값**이 나온다 --- 그래야 「떨어진다」를 볼 수 있다.
    """
    d0 = "세계애니" if "세계애니" in data.dom else (sorted(data.dom)[0] if data.dom else None)
    real = np.zeros(10)
    if d0 is not None:
        nm0 = list(data.names.get(d0) or [])
        if "wiki_level" in nm0:
            real = np.asarray(data.dom[d0][0][:, nm0.index("wiki_level")], float)
    n = 200
    return {
        "열": collections.OrderedDict([
            ("실제(세계애니 wiki_level)", real),
            ("빈 배열", np.array([], float)),
            ("상수 열(0.5 × 100)", np.full(100, 0.5)),
            ("전부 NaN(100)", np.full(100, np.nan)),
            ("난수 100", np.random.RandomState(1).rand(100)),
            ("두 값만(0.5 · 0.7)", np.array([0.5] * 50 + [0.7] * 50)),
        ]),
        "게이트 사례": collections.OrderedDict([
            ("마스크 상수 · 값 상수 · 잰 행 100", (1, 1, 100)),
            ("마스크 변함 · 값 상수 · 잰 행 100", (2, 1, 100)),
            ("마스크 상수 · 값 셋 · 잰 행 100", (1, 3, 100)),
            ("🔴 잰 행 0", (1, 0, 0)),
        ]),
        "결과 y": np.arange(n, dtype=float)[::-1],
        "상수 열": np.full(n, 0.5),
        "난수 열": np.random.RandomState(7).rand(n),
        "난수 x": np.random.RandomState(11).rand(n),
        "난수 y": np.random.RandomState(12).rand(n),
        "다른 난수 통제": np.random.RandomState(13).rand(n),
        "판": data,
        "원천 sha": src_stamp(),
    }


def _as_arr(v, fallback):
    """probes 에서 꺼낸 것이 배열이 아니면 되도록 배열로 만든다(예외 대신 다른 값)."""
    try:
        a = np.asarray(v, float).ravel()
        if a.size == 0:
            return np.asarray(fallback, float)
        return a
    except Exception:                                              # noqa: BLE001
        return np.asarray(fallback, float)


def wiring(data, ids, F, probes) -> dict:
    """조항 64 개정 2: ⑤ 어떤 입력 + 그 값 · ⑦ 빈 입력을 반드시 넣는다 · ⑧ 분자도 입력별로.

    🔴 **입력은 전부 `probes`(인자)에서 온다** --- 자 B 가 갈 뿌리다.
    """
    W = {}
    P = probes if isinstance(probes, dict) else {}

    # W1 --- 가짓수 세는 자가 진짜 세는가
    cols = P.get("열")
    cols = cols if isinstance(cols, dict) else {}
    vals = {str(k): card(v) for k, v in cols.items()}
    W["W1 가짓수 자"] = {
        "🔴 입력별 값": vals,
        "🔴 어떤 입력이면 떨어지나":
            "상수 열 · 전부 NaN · 빈 배열 --- 가짓수 ≤ 1. **`probes[\"열\"]` 을 갈면 값이 변한다**",
        "🔴 분자(입력별)": vals,
        "통과": bool(vals.get("난수 100", 0) > 1
                    and vals.get("상수 열(0.5 × 100)", -1) == 1
                    and vals.get("전부 NaN(100)", -1) == 0
                    and vals.get("빈 배열", -1) == 0
                    and vals.get("두 값만(0.5 · 0.7)", -1) == 2),
    }

    # W2 --- 게이트가 「죽음」과 「모름」을 가르는가
    cases = P.get("게이트 사례")
    cases = cases if isinstance(cases, dict) else {}
    vs = {}
    for k, v in cases.items():
        try:
            vs[str(k)] = col_verdict(*[int(x) for x in v])
        except Exception:                                          # noqa: BLE001
            vs[str(k)] = "🔴 못 읽었다(사례 꼴이 아니다)"
    W["W2 게이트"] = {
        "🔴 입력별 값": vs,
        "🔴 어떤 입력이면 떨어지나":
            "「마스크 변함 · 값 상수」와 「잰 행 0」에서 **죽은 열이 아니다**로 갈린다",
        "🔴 분자(입력별)": {"사례 수": len(vs)},
        "통과": bool(
            vs.get("마스크 상수 · 값 상수 · 잰 행 100", "").startswith("🔴 죽은 열")
            and not vs.get("마스크 변함 · 값 상수 · 잰 행 100", "🔴 죽은 열"
                           ).startswith("🔴 죽은 열")
            and vs.get("🔴 잰 행 0", "").startswith("🔴 모른다")),
    }

    # W3 --- 동률평균과 966 자가 상수 열에서 갈리는가
    yv = _as_arr(P.get("결과 y"), np.arange(200, dtype=float)[::-1])
    const = _as_arr(P.get("상수 열"), np.full(len(yv), 0.5))[:len(yv)]
    rnd = _as_arr(P.get("난수 열"), np.random.RandomState(7).rand(len(yv)))[:len(yv)]
    if len(const) != len(yv):
        const = np.resize(const, len(yv))
    if len(rnd) != len(yv):
        rnd = np.resize(rnd, len(yv))
    r966 = partial(const, yv, [], ranker=rank_966)
    rtie = partial(const, yv, [], ranker=rank_tie)
    W["W3 두 자"] = {
        "🔴 입력별 값": {
            "상수 열 --- 966 자": round(r966, 4),
            "상수 열 --- 동률평균": round(rtie, 4),
            "난수 열 --- 966 자": round(partial(rnd, yv, [], ranker=rank_966), 4),
            "난수 열 --- 동률평균": round(partial(rnd, yv, [], ranker=rank_tie), 4),
            "🔴 빈 입력(길이 2 상수) --- 동률평균":
                round(partial(np.full(2, 0.5), np.array([1.0, 2.0]), [],
                              ranker=rank_tie), 4),
            "곁: 쓴 열의 가짓수": card(const)},
        "🔴 어떤 입력이면 떨어지나":
            ("**상수 열**에서 966 자는 0 에서 멀고 동률평균은 정확히 0 --- 그 차가 이 검사다. "
             "`probes[\"상수 열\"]` 을 난수로 갈면 두 자가 같아져 **떨어진다**"),
        "🔴 분자(입력별)": {"상수 열에서 두 자의 차": float(abs(r966 - rtie))},
        "통과": bool(abs(rtie) < 1e-12 and abs(r966) > 0.5),
    }

    # W4 --- `pinv` 잔차화가 상수 통제를 무시하는가
    x = _as_arr(P.get("난수 x"), np.random.RandomState(11).rand(len(yv)))
    yy = _as_arr(P.get("난수 y"), np.random.RandomState(12).rand(len(yv)))
    oth = _as_arr(P.get("다른 난수 통제"), np.random.RandomState(13).rand(len(yv)))
    m = min(len(x), len(yy), len(oth), len(const), len(rnd))
    x, yy, oth = x[:m], yy[:m], oth[:m]
    c2, r2 = const[:m], rnd[:m]
    a = partial(x, yy, [c2, r2])
    b = partial(x, yy, [r2])
    c = partial(x, yy, [oth, r2])
    W["W4 상수 통제는 배선이 죽는다"] = {
        "🔴 입력별 값": {"상수+난수 통제": round(a, 6), "난수 통제만": round(b, 6),
                    "🔴 다른 난수+난수 통제(음성 대조)": round(c, 6), "쓴 행": int(m)},
        "🔴 어떤 입력이면 떨어지나":
            "통제 하나를 **난수**로 바꾸면 값이 변한다(음성 대조). **상수**로 바꾸면 안 변한다",
        "🔴 분자(입력별)": {"|상수+난수 − 난수만|": float(abs(a - b)),
                       "|다른난수+난수 − 난수만|": float(abs(c - b))},
        "🔴 엄한 자 --- 정확히 같은가(a == b)": bool(a == b),
        "🔴 무른 자 --- 기계 오차 이내인가(|a−b| < 1e-12)": bool(abs(a - b) < 1e-12),
        "🔴🔴 정직 신고": (
            "**이 자리를 측정 뒤에 고쳤다.** 처음 판은 `a == b`(정확히 같음)를 요구했고 "
            "**떨어졌다** --- `|a−b| = 1.39e-17`. 967 과 티처 #106 은 `lstsq` 를 써서 "
            "**정확히 0** 을 봤는데, 나는 `pinv` 사영을 써서 **1e-17 이 남는다**. "
            "🔴 **「Δ = 0.000000 · 바이트 동일」은 구현에 딸린 성질이다.** 실질은 안 바뀐다"
            "(1e-17 은 어떤 눈금에서도 뜻이 없다). 그래서 통과 자를 기계 오차로 무르고 "
            "**엄한 자의 결과를 같이 싣는다** --- 지우지 않는다"),
        "통과": bool(abs(a - b) < 1e-12 and abs(c - b) > 1e-9),
    }

    # W5 --- 실제 판에서 죽은 열이 실제로 있나(빈 입력 대조 포함)
    board = P.get("판")
    try:
        aud = audit_all_columns(board)
    except Exception:                                              # noqa: BLE001
        aud = audit_all_columns(type(data)(dom={}, names={}))
    empty = type(data)(dom={}, names={})
    aud0 = audit_all_columns(empty)
    W["W5 판 전량 감사"] = {
        "🔴 입력별 값": {
            "실제 판 --- 죽은 칸 수": aud["🔴 죽은 칸 수(마스크도 값도 상수)"],
            "실제 판 --- 배선이 죽은 칸 수": aud["🔴🔴 배선이 죽은 칸 수(값도 마스크도 상수)"],
            "실제 판 --- 칸 수": aud["🔴 (도메인 × 열) 칸 수"],
            "🔴 빈 판(dom={}) --- 칸 수": aud0["🔴 (도메인 × 열) 칸 수"],
            "🔴 빈 판 --- 배선이 죽은 칸 수":
                aud0["🔴🔴 배선이 죽은 칸 수(값도 마스크도 상수)"]},
        "🔴 어떤 입력이면 떨어지나":
            "빈 판(`dom={}`)을 먹이면 칸 수도 죽은 칸 수도 **0**. `probes[\"판\"]` 이 뿌리다",
        "🔴 분자(입력별)": {
            "실제": aud["🔴🔴 배선이 죽은 칸 수(값도 마스크도 상수)"],
            "빈 판": aud0["🔴🔴 배선이 죽은 칸 수(값도 마스크도 상수)"]},
        "통과": bool(aud["🔴 (도메인 × 열) 칸 수"] > 0
                    and aud0["🔴 (도메인 × 열) 칸 수"] == 0),
    }

    # W6 --- 원천 대조(F6) 가 진짜 무는가
    s1 = P.get("원천 sha")
    s1 = s1 if isinstance(s1, dict) else {}
    s2 = dict(s1)
    planted = dict(s2, **{sorted(s2)[0]: "심은값"}) if s2 else {"x": "심은값"}
    W["W6 원천 대조"] = {
        "🔴 입력별 값": {"같은 sha 둘": bool(s1 == s2),
                    "🔴 한 글자 심었을 때": bool(s1 == planted)},
        "🔴 어떤 입력이면 떨어지나":
            "sha 하나만 바꿔도 대조가 **거짓**이 된다. `probes[\"원천 sha\"]` 가 뿌리다",
        "🔴 분자(입력별)": {"원천 파일 수": len(s1)},
        "통과": bool(len(s1) > 0 and s1 == s2 and s1 != planted),
    }
    W["🔴 자리 수"] = len([k for k in W if k.startswith("W")])
    W["🔴 통과 수"] = sum(1 for k, v in W.items()
                       if isinstance(v, dict) and v.get("통과") is True)
    return W


# ── §B 판 --- 🔴 P9 죽은 열을 빼고 Δρ ────────────────────────────────
def board_drop_dead(data) -> dict:
    from lab.board import board as B
    from lab.harness import Data
    aud = audit_all_columns(data)
    #: 🔴🔴 **사전등록 P9 를 고쳤다 --- 정직 신고.**
    #: 사전등록 §2-가 의 「죽은 열」은 `mask_card ≤ 1 그리고 val_card ≤ 1` 인데,
    #: 같은 절이 「`val_card = 0` 은 「모른다」로 적는다」고도 적었다. **두 문장이 서로 문다.**
    #: 코드가 「모른다」를 먼저 잡아 **죽은 열 = 0** 이 됐고, 0 개를 빼는 팔은
    #: 아무것도 안 빼는 팔이라 **항진명제**다(조항 64).
    #: → **배선 기준**(값도 마스크도 상수 = GBDT 가 원리상 못 가른다)으로 뺀다.
    #: 인식론적으로는 여전히 「모른다」이고, 그것은 판정문에 따로 적는다.
    drop = {d: set(aud["도메인별"][d]["🔴 배선이 죽은 열"]) for d in aud["도메인별"]}
    ndrop = sum(len(v) for v in drop.values())
    t0 = time.time()
    b0 = B(data, seeds=SEEDS, T=T)
    t1 = time.time()
    dom2, names2 = {}, {}
    for d in data.dom:
        A, M, y, t = data.dom[d]
        nm = list(data.names.get(d) or [])
        keep = [j for j, name in enumerate(nm) if name not in drop.get(d, set())]
        dom2[d] = (A[:, keep], M[:, keep], y, t)
        names2[d] = [nm[j] for j in keep]
    d2 = Data(dom=dom2, names=names2)
    b1 = B(d2, seeds=SEEDS, T=T)
    t2 = time.time()
    delta = b1["판"] - b0["판"]
    return {"🔴 무엇을 뺐나": ("**배선이 죽은 열** --- 값 가짓수 ≤ 1 **그리고** 마스크 "
                        "가짓수 ≤ 1. GBDT 가 원리상 못 가르는 열이다"),
            "🔴🔴 사전등록 P9 를 고쳤다(정직 신고)": (
                "사전등록 §2-가 가 「죽은 열」과 「모른다」를 한 정의 안에 넣어 서로 물게 "
                "만들었고, 코드가 「모른다」를 먼저 잡아 죽은 열이 0 이 됐다. 0 개를 빼는 "
                "팔은 항진명제라(조항 64) **배선 기준으로 바꿔 다시 뺐다.** "
                "🔴 이것은 측정 뒤의 변경이다 --- 지우지 않고 신고한다"),
            "🔴 인식론적으로 「모른다」인 칸 수(같은 칸들)":
                aud["🔴 잰 행이 0 인 칸 수(「모른다」 · 상수가 아니다)"],
            "🔴 뺀 열 수(도메인 × 열 칸)": ndrop,
            "뺀 열(도메인별)": {d: sorted(v) for d, v in drop.items() if v},
            "기준선": {"판": b0["판"], "SD": b0["SD"], "SE": b0["SE"]},
            "처리": {"판": b1["판"], "SD": b1["SD"], "SE": b1["SE"]},
            "🔴 기준선이 정본 0.47034 를 재현하나": {
                "정본": RHO0, "실측": round(b0["판"], 6),
                "차": round(abs(b0["판"] - RHO0), 6),
                "통과": bool(abs(b0["판"] - RHO0) < 5e-4)},
            "🔴 Δρ": round(delta, 6),
            "🔴 판정(Δρ ± SE)": "%+.6f ± %.6f" % (delta, BOARD_SE),
            "🔴 |Δρ| < SE 인가": bool(abs(delta) < BOARD_SE),
            "🔴 채택 크기": ("**못 정했다**(`docs/목표.md:138`). "
                        "0.01055(잡음 바닥)와 0.00353(운영 문턱)은 **둘 다 진단 수치**다"),
            "곁: 진단 수치 --- 잡음 바닥": DIAG_NOISE_1COL,
            "곁: 진단 수치 --- 운영 문턱": DIAG_OPS,
            "도메인별": {d: {"기준선": round(b0["도메인"].get(d, (float("nan"),))[0], 4),
                         "처리": round(b1["도메인"].get(d, (float("nan"),))[0], 4),
                         "Δ": round(b1["도메인"].get(d, (float("nan"),))[0]
                                    - b0["도메인"].get(d, (float("nan"),))[0], 4)}
                     for d in sorted(set(b0["도메인"]) & set(b1["도메인"]))},
            "초": {"기준선": round(t1 - t0, 1), "처리": round(t2 - t1, 1)}}


def board_arm_diag(data) -> dict:
    """🔴🔴 **P9 의 팔이 무엇을 쟀는지 사후 진단한다** --- 판 주행 없이.

    실측(주행 1): 배선이 죽은 301 칸을 빼니 판이 **0.470343 → 0.264062
    (Δρ = −0.206281)** 로 무너졌다. 사전등록은 `|Δρ| < SE` 를 예측했다.
    🔴 **그러나 이것은 「죽은 열이 정보를 나른다」가 아니다.**

    `lab/forms.py:197` 의 `AXIS_MODE = "common"` 때문에 축 목록은
    **전 도메인 이름의 교집합**이다. 도메인마다 **다른** 열을 빼면 교집합이 무너진다.
    🔴 **내 팔은 「죽은 열을 뺐다」가 아니라 「축 목록을 무너뜨렸다」였다 --- 조항 62.**

    그리고 **옳은 팔(전 도메인에서 같은 열을 뺀다)은 뺄 것이 0 개다** ---
    12 도메인 전부에서 잰 행이 0 인 열 이름이 **하나도 없다.**
    → **판에서 「죽은 열을 빼는」 실험은 이 판의 구조상 못 한다. 그것이 답이다.**
    """
    from lab import forms as FM
    from lab.harness import Data
    aud = audit_all_columns(data)
    drop = {d: set(aud["도메인별"][d]["🔴 배선이 죽은 열"]) for d in aud["도메인별"]}
    before = FM.axis_order(data)
    names2 = {d: [n for n in (data.names.get(d) or []) if n not in drop.get(d, set())]
              for d in data.dom}
    d2 = Data(dom=dict(data.dom), names=names2)
    after = FM.axis_order(d2)
    allnames = set()
    for d in data.dom:
        allnames |= set(data.names.get(d) or [])
    gone = sorted(n for n in allnames
                  if all(n in drop.get(d, set()) or n not in (data.names.get(d) or [])
                         for d in data.dom))
    return {
        "🔴 lab/forms.py 의 AXIS_MODE": FM.AXIS_MODE,
        "🔴 뜻": ("`common` 이면 축 목록은 **전 도메인 이름의 교집합**이다. "
               "도메인마다 다른 열을 빼면 교집합이 무너진다"),
        "🔴 공통 축 수(원판)": len(before),
        "🔴 공통 축 수(배선 죽은 열을 뺀 뒤)": len(after),
        "공통 축(뺀 뒤)": after,
        "🔴🔴 그래서 P9 의 팔은 무엇을 쟀나":
            ("「죽은 열을 뺐을 때의 Δρ」가 **아니다.** 「공통 축이 36 에서 %d 로 "
             "줄었을 때의 Δρ」다. 사전등록이 선언한 것과 코드가 잰 것이 다르다 --- "
             "**조항 62. 내가 나에게서 잡았다**" % len(after)),
        "🔴🔴 옳은 팔은 뺄 것이 0 개다": {
            "12 도메인 전부에서 잰 행이 0 인 열 이름": gone,
            "그 수": len(gone),
            "🔴 뜻": ("모든 열은 **적어도 한 도메인에서는 살아 있다.** "
                   "그러므로 「전 도메인에서 같은 죽은 열을 뺀다」는 팔은 "
                   "**아무것도 안 빼는 팔**이고, 그것을 돌리는 것은 항진명제다(조항 64). "
                   "🔴 **판에서 「죽은 열을 빼는」 실험은 이 판의 구조상 못 한다.**")},
        "🔴 P9 판정": ("**틀렸다 --- 그리고 못 잰다.** 예측은 `|Δρ| < SE` 였고 실측은 "
                   "Δρ = −0.206281 이지만, 그 수는 죽은 열의 값이 아니라 "
                   "**축 목록 붕괴의 값**이다. 이 물음은 이 판에서 원리상 못 묻는다"),
    }


# ── 본선 ──────────────────────────────────────────────────────────────
def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", default="prop",
                    choices=["wiring", "prop", "board", "boarddiag"])
    ap.add_argument("--draws", type=int, default=DRAWS)
    a = ap.parse_args()
    outp = Path(a.out).resolve()
    t0 = time.time()

    R = {"노트": 968, "레인": "판정",
         "사전등록": "docs/prereg_968_deadcontrols.md",
         "물음": "판과 967 의 규격이 「통제」라고 부른 열이 실제로 통제인가",
         "단계": a.stage,
         "🔴 공적 귀속": ("방향과 P1~P7 의 예측값은 **티처 #106 이 준 것**이다. "
                     "내 것은 P8(자 기계화)·P9(판에서 죽은 열 빼기)와 "
                     "「마스크/값 가짓수를 가른 정의」뿐이다"),
         "🔴 시작 --- 코드 sha256(자르지 않았다)": code_stamp(),
         "🔴 시작 --- 원천 sha256": src_stamp(),
         "🔴 시작 시각(UTC)": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}

    recs = load_series()
    F, why = feats(recs)
    R["§0 자료"] = {"원천 개체": len(recs), "유효 개체": len(F), "무효 사유": why,
                 "규격 D 행(두 띠 모두 실자료)":
                     sum(1 for f in F.values() if f["n_rec"] > 0 and f["n_lon"] > 0)}

    data, ids = board_keys()
    R["§0 판"] = {"도메인": len(data.dom), "유보 합": int(sum(data.weights(T).values())),
                "통과": bool(int(sum(data.weights(T).values())) == 3775)}

    if a.stage == "wiring":
        R["§W 배선"] = wiring(data, ids, F, probe_pack(data))
    if a.stage == "prop":
        R["🔴🔴 §A 판 전량 열 감사"] = audit_all_columns(data)
        R["🔴🔴 §B wiki_level 감사(P1·P2)"] = audit_wiki_level(data, ids, F)
        R["🔴🔴 §C level 을 빼면 변하나(P3)"] = drop_level_delta(data, ids, F)
        R["🔴🔴 §D 966 간판이 인공물인가(P4·P5)"] = anime_artifact(data, ids, F)
        R["🔴 §E 세계애니 억제와 공선성(P6)"] = worldani_suppression(
            data, ids, F, draws=a.draws)
        R["🔴 §F 이름이 둘이다(P7 · M3)"] = m3_two_names(data, ids, F, draws=a.draws)
        R["§G NaN 회계(M6 · 조항 60)"] = nan_ledger(data, ids, F)
    if a.stage == "board":
        R["🔴 §H 판(P9)"] = board_drop_dead(data)
    if a.stage == "boarddiag":
        R["🔴🔴 §H2 P9 의 팔이 무엇을 쟀나(사후 진단)"] = board_arm_diag(data)

    # 🔴 F6 --- 끝에서 sha 를 **다시 떠** 시작 값과 대조한다(티처 #106 M7)
    end_src, end_code = src_stamp(), code_stamp()
    R["🔴🔴 §Z 단계 사이 원천 대조(F6)"] = {
        "원천 파일 수(시작)": len(R["🔴 시작 --- 원천 sha256"]),
        "원천 파일 수(끝)": len(end_src),
        "🔴 원천이 그대로인가": bool(end_src == R["🔴 시작 --- 원천 sha256"]),
        "🔴 달라진 원천": sorted(k for k in set(end_src) | set(R["🔴 시작 --- 원천 sha256"])
                          if end_src.get(k) != R["🔴 시작 --- 원천 sha256"].get(k)),
        "🔴 코드가 그대로인가": bool(end_code == R["🔴 시작 --- 코드 sha256(자르지 않았다)"]),
        "🔴 달라진 코드": sorted(k for k in set(end_code) | set(R["🔴 시작 --- 코드 sha256(자르지 않았다)"])
                          if end_code.get(k) != R["🔴 시작 --- 코드 sha256(자르지 않았다)"].get(k)),
        "🔴 왜": ("966·967 은 도장을 **시작에만** 찍고 끝에서 대조하지 않았다. "
               "967 의 측정 창 안에 데몬 쓰기와 967 자신의 수리 커밋이 둘 다 떨어졌고 "
               "**어느 자도 안 물었다**(티처 #106 M7)"),
    }
    R["초"] = round(time.time() - t0, 1)
    R["🔴 끝 시각(UTC)"] = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with NoWrite(allow=[outp]):
        outp.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", outp)
    return R


if __name__ == "__main__":
    main()
