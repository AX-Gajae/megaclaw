# -*- coding: utf-8 -*-
"""노트 970 — **잰 판본을 커밋으로 되돌린다** · 0.5 채움 전수 · `AXIS_MODE` · 되살린 통제로 판.

사전등록: `docs/prereg_970_recommit.md` (측정 전 단독 커밋).

🔴 **저장소 `lab/*.py` 를 한 바이트도 안 고친다.** `WIKI_DROP`/`TREND_DROP` 은
**메모리 안에서만** 비운다. `--out` 필수 · 쓰기 문지기가 그 파일 하나만 허용한다.

단계: `wiring` → `census` → `board`.
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
import re
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

#: 🔴 이 사이클에서 내가 돌린 러너 전부. F1 이 이 목록을 커밋 blob 과 대조한다.
RAN = ("runners/dropaudit969.py", "runners/metacmp969.py", "runners/recommit970.py",
       "runners/meta965.py")


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
                   os.remove, os.unlink, os.rename, os.replace)
        builtins.open = self._g_open(self._o[0])
        Path.open = self._g_path_open(self._o[1])
        Path.write_text = self._g_path_write(self._o[2])
        Path.write_bytes = self._g_path_write(self._o[3])
        os.remove = self._g_os1(self._o[4])
        os.unlink = self._g_os1(self._o[5])
        return self

    def __exit__(self, *e):
        (builtins.open, Path.open, Path.write_text, Path.write_bytes,
         os.remove, os.unlink, os.rename, os.replace) = self._o
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

    🔴 969 가 정확히 이것을 **자기 러너에서만** 빼먹었다(R3 로 남의 여섯은 봤다).
    """
    per, bad = {}, []
    for p in RAN:
        d = _sha_file(ROOT / p) if (ROOT / p).is_file() else None
        b = blob_sha(ref, p)
        ok = bool(d is not None and d == b)
        per[p] = {"디스크 sha256": d, "커밋 blob sha256": b, "일치": ok}
        if not ok:
            bad.append(p)
    return {"기준 ref": ref, "기준 커밋": _git("rev-parse", ref).decode().strip(),
            "러너별": per,
            "🔴 분자/분모": "%d / %d" % (len(RAN) - len(bad), len(RAN)),
            "🔴 어긋난 러너": bad,
            "🔴 F1 통과": bool(not bad),
            "🔴 어떤 입력이면 떨어지나":
                "러너 파일을 한 바이트만 고치고 커밋을 안 하면 그 줄이 곧 거짓이 된다"}


# ── §P 0.5 채움 전수 ─────────────────────────────────────────────────
FILL_PAT = re.compile(r"(np\.full\s*\([^)]*?,\s*\.?5\b|np\.full\s*\([^)]*?,\s*0\.5\b|"
                      r"np\.where\s*\([^\n]*?,\s*0\.5\s*\)|np\.where\s*\([^\n]*?,\s*\.5\s*\))")


def fill05_static(text: str) -> list:
    """🔴 **주어진 소스 문자열**에서 0.5 **채움** 자리를 찾는다(인자에서만 온다)."""
    out = []
    for i, ln in enumerate(text.splitlines()):
        s = ln.strip()
        if s.startswith("#"):
            continue
        if FILL_PAT.search(ln):
            out.append({"줄": i + 1, "원문": s})
    return out


def census_static() -> dict:
    """🔴 `lab/` **전량**을 훑는다. 969 는 세 파일만 하드코딩 grep 했다(티처 #108 M4)."""
    per, tot = {}, 0
    for p in sorted(glob.glob(str(ROOT / "lab/*.py"))):
        t = Path(p).read_text(encoding="utf-8")
        hits = fill05_static(t)
        if hits:
            per[str(Path(p).relative_to(ROOT))] = hits
            tot += len(hits)
    return {"파일별": per, "🔴 파일 수": len(per), "🔴 자리 수": tot,
            "🔴 969 가 훑은 파일": ["lab/wikiaxes.py", "lab/harness.py", "lab/forms.py"],
            "🔴 969 가 안 훑은 파일 중 자리가 있는 것":
                sorted(k for k in per if k not in
                       ("lab/wikiaxes.py", "lab/harness.py", "lab/forms.py"))}


class Sentinel:
    """🔴🔴 **파수병** --- `np.full`/`np.where` 로 실제로 0.5 를 채운 **줄**을 센다.

    정적 grep 은 「있다」만 말한다. 챔피언 판에서 **도는가**는 돌려 봐야 안다.
    """

    def __init__(self):
        self.hits = collections.Counter()

    def _rec(self, depth=2):
        try:
            f = sys._getframe(depth)
        except ValueError:
            return
        for _ in range(12):
            if f is None:
                return
            fn = str(f.f_code.co_filename)
            if fn.startswith(str(ROOT)) and "/lab/" in fn:
                self.hits[str(Path(fn).relative_to(ROOT)) + ":" + str(f.f_lineno)] += 1
                return
            f = f.f_back

    def __enter__(self):
        self._full, self._where = np.full, np.where
        of, ow, rec = self._full, self._where, self._rec

        def full(shape, fill_value=None, *a, **k):
            try:
                if fill_value is not None and np.isscalar(fill_value) \
                        and float(fill_value) == 0.5:
                    rec(2)
            except Exception:                                      # noqa: BLE001
                pass
            return of(shape, fill_value, *a, **k)

        def where(cond, *a, **k):
            try:
                for v in a[:2]:
                    if np.isscalar(v) and float(v) == 0.5:
                        rec(2)
                        break
            except Exception:                                      # noqa: BLE001
                pass
            return ow(cond, *a, **k)

        np.full, np.where = full, where
        return self

    def __exit__(self, *e):
        np.full, np.where = self._full, self._where
        return False


# ── 판 자료 ──────────────────────────────────────────────────────────
def build(drop_wiki: bool, drop_trend: bool):
    """🔴 `drop_*=False` 면 그 손잡이를 **메모리 안에서만** 비운다."""
    import ff753 as FF
    from lab import loop as L
    keep = (tuple(L.WIKI_DROP), tuple(L.TREND_DROP))
    try:
        if not drop_wiki:
            L.WIKI_DROP = ()
        if not drop_trend:
            L.TREND_DROP = ()
        data = FF.shell(FF.base())
    finally:
        L.WIKI_DROP, L.TREND_DROP = keep
    return data


# ── §X AXIS_MODE ─────────────────────────────────────────────────────
def axis_census(don, doff) -> dict:
    """🔴🔴 여덟째 손잡이. **`common` 이 무엇을 조용히 버리는가.**"""
    from lab import forms as FM
    src = (ROOT / "lab/forms.py").read_text(encoding="utf-8").splitlines()
    asg = [{"파일": "lab/forms.py", "줄": i + 1, "원문": ln.strip()}
           for i, ln in enumerate(src) if re.match(r"\s*AXIS_MODE\s*=", ln)]
    users = []
    for p in sorted(glob.glob(str(ROOT / "lab/*.py"))) + \
            sorted(glob.glob(str(ROOT / "runners/*.py"))):
        try:
            t = Path(p).read_text(encoding="utf-8")
        except Exception:                                          # noqa: BLE001
            continue
        for i, ln in enumerate(t.splitlines()):
            if "AXIS_MODE" in ln or "axis_order" in ln:
                users.append({"파일": str(Path(p).relative_to(ROOT)), "줄": i + 1,
                              "원문": ln.strip()[:160]})

    def per_dom(data):
        return {d: list(data.names.get(d) or []) for d in sorted(data.dom)}

    out = {}
    for tag, data in (("현행(WIKI_DROP 그대로)", don), ("DROP 비움", doff)):
        pd = per_dom(data)
        com = FM.axis_order(data, "common")
        uni = FM.axis_order(data, "union")
        out[tag] = {
            "도메인 수": len(pd),
            "도메인별 축 수": {d: len(v) for d, v in pd.items()},
            "🔴 common 축 수": len(com),
            "🔴 union 축 수": len(uni),
            "common 축": com,
            "🔴 union 에만 있는 축": sorted(set(uni) - set(com)),
            "🔴 도메인별 축 이름이 전부 같은가": bool(len({tuple(v) for v in pd.values()}) == 1),
        }
    out["🔴 대입 자리"] = asg
    out["🔴 읽는/부르는 자리"] = users
    out["🔴🔴 뜻"] = (
        "`AXIS_MODE` 는 저장소에서 **`lab/forms.py` 한 곳에서만** 대입되고 값은 둘뿐이다"
        "(`common`·`union`). `common` 은 **전 도메인 이름의 교집합**이라 "
        "**게임 전용 축 넷(가격·연령등급·램·카테고리 수)을 모든 도메인의 설계행렬에서 "
        "조용히 뺀다**(`axis_order` 독스트링이 그렇게 적고 있다). "
        "🔴 **`WIKI_DROP` 과 같은 종이고 표면은 더 넓다 --- 티처 #108.**")
    return out


# ── §B 판 --- 🔴 되살린 통제로 24 주행(짝지은 12 씨앗) ────────────────
def board_pair(don, doff, seeds=SEEDS) -> dict:
    """🔴🔴 **968 이 「못 묻는 물음」이라 한 자리와 다르다.**

    968 의 P9 는 **열을 뺐다** --- 도메인마다 다른 열을 빼니 `common` 교집합이
    36 → 1 로 무너졌다. **여기서는 열을 하나도 안 뺀다.** `WIKI_DROP` 은
    `lab/harness.py:241` 이 **이름을 남긴 채 값만 0.5/마스크0 으로** 채우기
    때문에, 손잡이를 비워도 **축 이름 집합이 안 바뀐다**(§X 가 그것을 잰다).
    그래서 이 팔은 **물을 수 있는 물음**이다.
    """
    from lab.board import evaluate
    from lab import forms as FM
    cls = FM.REGISTRY["F18_bagboost"]["cls"]
    a0, a1, rows = [], [], []
    t0 = time.time()
    for s in range(seeds):
        v0 = float(don.pooled(evaluate(lambda s=s: cls(seed=s), don, T=T), T=T))
        v1 = float(doff.pooled(evaluate(lambda s=s: cls(seed=s), doff, T=T), T=T))
        a0.append(v0)
        a1.append(v1)
        rows.append({"씨앗": s, "기준선(현행)": round(v0, 6),
                     "처리(DROP 비움)": round(v1, 6), "차": round(v1 - v0, 6)})
    x0, x1 = np.array(a0), np.array(a1)
    d = x1 - x0
    wins = int((d > 0).sum())
    sd_d = float(d.std(ddof=1))
    se_d = sd_d / float(np.sqrt(len(d)))
    return {
        "주행 수": 2 * seeds,
        "씨앗": list(range(seeds)),
        "짝별": rows,
        "기준선(현행)": {"판": float(x0.mean()), "SD": float(x0.std(ddof=1)),
                   "SE": float(x0.std(ddof=1) / np.sqrt(len(x0)))},
        "처리(DROP 비움)": {"판": float(x1.mean()), "SD": float(x1.std(ddof=1)),
                       "SE": float(x1.std(ddof=1) / np.sqrt(len(x1)))},
        "🔴 기준선이 정본 0.47034 를 재현하나": {
            "정본": RHO0, "실측": round(float(x0.mean()), 6),
            "차": round(abs(float(x0.mean()) - RHO0), 6),
            "통과": bool(abs(float(x0.mean()) - RHO0) < 5e-4)},
        "🔴🔴 Δρ(짝지은 C-B)": round(float(d.mean()), 6),
        "🔴 짝 SD": round(sd_d, 6),
        "🔴 짝 SE": round(se_d, 6),
        "🔴🔴 판정(Δρ ± 짝 SE)": "%+.6f ± %.6f" % (float(d.mean()), se_d),
        "🔴 이긴 씨앗": "%d / %d" % (wins, seeds),
        "🔴 |Δρ| 가 짝 SE 의 몇 배인가": round(abs(float(d.mean())) / se_d, 2) if se_d else None,
        "🔴 채택 크기": ("**못 정했다**(`docs/목표.md:138` 은 공동주어다). "
                    "0.01055(잡음 바닥)·0.00353(운영 문턱)은 **둘 다 진단 수치**다"),
        "곁: 진단 수치": {"잡음 바닥": DIAG_NOISE_1COL, "운영 문턱": DIAG_OPS,
                    "판 SE 정본": BOARD_SE},
        "🔴 노트 350 이 잰 것과의 대조": (
            "노트 350 은 **빼는 방향**으로 C-B = **+0.0033(SD 0.0042 · 10/12)** 을 얻었다. "
            "이 팔은 **되살리는 방향**이라 부호가 뒤집혀야 한다. "
            "🔴 그러나 노트 350 은 위키 **넷**만 뺐고 도서·검색@팝업은 노트 351 이라 "
            "**분모가 다르다**(조항 60) --- 여기는 위키 다섯 + 검색 하나를 한꺼번에 되살린다"),
        "초": round(time.time() - t0, 1),
    }


# ── §W 배선 검사 --- 🔴 입력은 전부 `probes`(인자)에서 온다 ──────────
def probe_pack() -> dict:
    return {
        "0.5 있는 소스": "x = np.full(len(A), 0.5)\ny = np.where(m, A, 0.5)\n",
        "0.5 없는 소스": "x = np.full(len(A), 0.0)\ny = A * 0.5\n",
        "주석뿐인 소스": "# np.full(len(A), 0.5)\n",
        "sha 짝(같다)": ("aa" * 32, "aa" * 32),
        "sha 짝(다르다)": ("aa" * 32, "bb" * 32),
        "축 이름(교집합 있음)": {"A": ["x", "y", "z"], "B": ["x", "z", "w"]},
        "축 이름(교집합 없음)": {"A": ["x"], "B": ["y"]},
        "짝 차(3승 1패)": [0.1, 0.2, -0.3, 0.4],
    }


def wiring(P) -> dict:
    """🔴 **자유 이름 0** --- 전부 `P` 에서 온다(조항 66-④ · 968 R1 이 잡은 병)."""
    W = {}

    n_yes = len(fill05_static(P["0.5 있는 소스"]))
    n_no = len(fill05_static(P["0.5 없는 소스"]))
    n_cm = len(fill05_static(P["주석뿐인 소스"]))
    W["W1 0.5 채움 탐지기"] = {
        "🔴 분자/분모": {"있는 소스에서 찾은 줄": n_yes, "없는 소스": n_no, "주석뿐": n_cm},
        "🔴 어떤 입력이면 떨어지나":
            "`np.full(...,0.0)` 이나 `A*0.5` 를 **채움으로 세면** 없는 소스가 0 이 아니게 된다",
        "통과": bool(n_yes == 2 and n_no == 0 and n_cm == 0),
    }

    s_eq, s_ne = P["sha 짝(같다)"], P["sha 짝(다르다)"]
    W["W2 sha 대조기"] = {
        "🔴 분자/분모": {"같은 짝": bool(s_eq[0] == s_eq[1]),
                    "다른 짝": bool(s_ne[0] == s_ne[1])},
        "🔴 어떤 입력이면 떨어지나": "한 글자만 달라도 거짓이 되어야 한다. 잘라 비교하면 안 떨어진다",
        "통과": bool(s_eq[0] == s_eq[1] and s_ne[0] != s_ne[1]),
    }

    def _inter(per):
        ks = sorted(per)
        return [a for a in per[ks[0]] if all(a in per[k] for k in ks)]
    i_yes, i_no = _inter(P["축 이름(교집합 있음)"]), _inter(P["축 이름(교집합 없음)"])
    W["W3 축 교집합"] = {
        "🔴 분자/분모": {"교집합 있음": i_yes, "교집합 없음": i_no},
        "🔴 어떤 입력이면 떨어지나": "도메인 하나가 이름 하나만 잃어도 교집합이 줄어야 한다",
        "통과": bool(i_yes == ["x", "z"] and i_no == []),
    }

    dd = np.asarray(P["짝 차(3승 1패)"], float)
    W["W4 짝 승수"] = {
        "🔴 분자/분모": {"이김": int((dd > 0).sum()), "짝 수": int(len(dd))},
        "🔴 어떤 입력이면 떨어지나": "부호를 뒤집으면 승수가 3 에서 1 로 바뀌어야 한다",
        "통과": bool(int((dd > 0).sum()) == 3 and int((-dd > 0).sum()) == 1),
    }

    W["🔴 자리 수"] = len([k for k in W if k.startswith("W")])
    W["🔴 통과 수"] = sum(1 for k, v in W.items()
                       if isinstance(v, dict) and v.get("통과") is True)
    W["🔴 분자/분모(요약)"] = "%d / %d" % (W["🔴 통과 수"], W["🔴 자리 수"])
    return W


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["wiring", "census", "board"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", default="note/969-dropped-by-design")
    ap.add_argument("--seeds", type=int, default=SEEDS)
    a = ap.parse_args()

    out_path = Path(a.out)
    if not out_path.is_absolute():
        out_path = ROOT / "runners" / out_path
    t_start, cs0 = _now(), code_stamp()
    t0 = time.time()
    R = {"🔴 단계": a.stage, "🔴 시작(UTC)": t_start,
         "🔴 사전등록": "docs/prereg_970_recommit.md (측정 전 단독 커밋)"}

    with NoWrite(allow=[str(out_path)]) as G:
        R["🔴🔴 §S 내가 돌린 러너 ↔ 커밋 blob(F1)"] = ran_vs_blob(a.ref)
        if a.stage == "wiring":
            R["§W 배선"] = wiring(probe_pack())
            R["🔴🔴 §P 0.5 채움 --- 정적 전수(lab 전량)"] = census_static()
        elif a.stage == "census":
            sen = Sentinel()
            with sen:
                don = build(drop_wiki=True, drop_trend=True)
                from lab.board import evaluate
                from lab import forms as FM
                cls = FM.REGISTRY["F18_bagboost"]["cls"]
                sc = evaluate(lambda: cls(seed=0), don, T=T)
                one = float(don.pooled(sc, T=T))
            doff = build(drop_wiki=False, drop_trend=False)
            stat = census_static()
            live = dict(sorted(sen.hits.items()))
            allstat = sorted("%s:%d" % (f, h["줄"])
                             for f, hs in stat["파일별"].items() for h in hs)
            R["🔴🔴 §P 0.5 채움 --- 정적 전수(lab 전량)"] = stat
            R["🔴🔴 §P2 0.5 채움 --- 챔피언 판에서 **실제로 돈 줄**"] = {
                "🔴 파수병": ("`np.full`/`np.where` 를 감싸 채움값이 0.5 일 때 **호출한 줄**을 "
                          "센다. 자료 짓기 + 챔피언 한 주행(씨앗 0)을 덮는다"),
                "🔴 돈 줄": live,
                "🔴 분자/분모": "%d / %d" % (len(live), len(allstat)),
                "🔴 정적으로는 있는데 **안 돈 줄**": [x for x in allstat if x not in live],
                "곁: 그 주행의 판 점수(씨앗 0)": round(one, 6),
            }
            R["🔴🔴 §X AXIS_MODE 전수(여덟째 손잡이)"] = axis_census(don, doff)
        elif a.stage == "board":
            don = build(drop_wiki=True, drop_trend=True)
            doff = build(drop_wiki=False, drop_trend=False)
            R["🔴🔴 §B 판 --- 되살린 통제로 24 주행"] = board_pair(don, doff, a.seeds)
            R["🔴 §X 축 이름이 안 바뀌는가(이 팔이 물을 수 있는 물음인 근거)"] = \
                axis_census(don, doff)
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
    with open(str(out_path), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1)
    print("wrote", out_path, R["🔴 걸린 초"], "s  시작", t_start, "끝", t_end)


if __name__ == "__main__":
    main()
