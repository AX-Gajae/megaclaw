# -*- coding: utf-8 -*-
"""팔 940 — **T 를 문턱에서 「민감도 비 r」로 강등하고, 배선을 주입으로 확인한다.**

사전등록: `docs/prereg_940_ratio.md` · 스탬프: `runners/out940_prereg_stamp.json`.

🔴 이 러너가 지키는 것
  · **남의 산출물을 읽기만 한다.** `runners/out*.json` 은 증거물이라 한 글자도 안 고친다.
  · `state/perm922.py` · `state/gap925.py` · `state/gate939.py` 를 **한 글자도 안 고친다**.
  · §B 의 주입 실행은 산출물을 **scratchpad 로만** 낸다 — `out922_permfix.json` 을 안 덮는다.
  · 규약 47 — 구간은 `lab.pairboot.cluster_boot` **BCa**, 폴백이면 사유 필드.
  · 규약 60 — 전수 계수는 **명령·범위·트리** 셋을 박고 **인덱스와 작업 트리를 안 섞는다**.

사용: python3 runners/ratio940_run.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import pairboot                     # noqa: E402
from state import gate939, ratio940          # noqa: E402

OUT = ROOT / "runners/out940_ratio.json"
PREREG = ROOT / "docs/prereg_940_ratio.md"
STAMP = ROOT / "runners/out940_prereg_stamp.json"
SCRATCH = Path("/private/tmp/claude-501/-Users-ax-world-model/"
               "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad/g940")
BOOT_B, BOOT_SEED = 10_000, 939      # 🔴 939 의 L 을 **비트로 재현**하려고 같은 씨앗을 쓴다
P935 = ["① 원판 전량", "② 원판 − b_prv=−1 칸", "진단 b_prv=−1 칸만"]
T939 = 0.0151219535025886810        # 939 가 낸 「문턱」 — 이 사이클이 강등하는 그 수
OLD_THR = 0.05


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jload(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *a],
                          capture_output=True, text=True).stdout


# ══════════════════════════════════════════════════════ 0 · 사전등록 시각 증거
def part0() -> dict:
    st = json.loads(STAMP.read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "stamp": str(STAMP.relative_to(ROOT)),
        "stamp 이 박은 사전등록 sha256":
            st["파일별 sha256·mtime"]["docs/prereg_940_ratio.md"]["sha256"],
        "사전등록 sha256(지금 다시 계산)": sha(PREREG),
        "🔴 같은가": (st["파일별 sha256·mtime"]["docs/prereg_940_ratio.md"]["sha256"]
                 == sha(PREREG)),
        "stamp 를 쓴 시각(UTC)": st["이 stamp 를 쓴 시각(UTC)"],
        "측정 시작(UTC)": now.isoformat(),
        "🔴 stamp 가 측정보다 먼저인가":
            dt.datetime.fromisoformat(st["이 stamp 를 쓴 시각(UTC)"]) < now,
        "🔴 사전등록만 담은 커밋": git("log", "--oneline", "-1", "--",
                            str(PREREG)).strip(),
        "🔴 그 커밋에 측정 러너가 들어 있었나":
            "runners/ratio940_run.py" in git(
                "show", "--name-only", "--pretty=format:",
                git("log", "-1", "--format=%H", "--", str(PREREG)).strip()),
        "🔴 os.utime 을 썼나": False,
        "🔴 남의 파일이 안 바뀌었나(스탬프 대조)": {
            f: {"stamp": r["sha256"], "지금": sha(ROOT / f),
                "같은가": r["sha256"] == sha(ROOT / f)}
            for f, r in st["🔴 남의 파일(읽기만 · 측정 뒤 대조한다)"].items()},
    }


# ══════════════════════════════════════════════════════ A · 배선 실측
HAND_COPIES_NEEDLE = "perm922.COMPARABLE_REL"


def part_A(rev: str) -> dict:
    """게이트가 낸 계수를 **그대로 싣고**, 게이트가 안 보는 갈래 하나를 더 센다."""
    g = jload("runners/out940_gate.json")
    tree = git("rev-parse", rev).strip()

    # 🔴 게이트가 안 세는 갈래 — 상수를 **손으로 베낀** 자리
    tar = SCRATCH / "tree"
    tar.mkdir(parents=True, exist_ok=True)
    p1 = subprocess.Popen(["git", "-C", str(ROOT), "archive", tree],
                          stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(tar)], stdin=p1.stdout, check=True)
    p1.wait()
    hand = {}
    for f in sorted(x for x in git("ls-tree", "-r", "-z", "--name-only",
                                   tree).split("\0") if x.endswith(".py")):
        try:
            src = (tar / f).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, ln in enumerate(src.split("\n"), 1):
            if HAND_COPIES_NEEDLE in ln and "import" not in ln:
                hand.setdefault(f, []).append({"줄": i, "본문": ln.strip()})

    return {
        "무엇": "🔴 배선 실측 — 게이트(`runners/out940_gate.json`)가 낸 계수를 그대로 싣는다",
        "🔴 게이트 rev": g["🔴 rev"],
        "🔴 이 절의 rev": tree,
        "🔴 둘이 같은가": g["🔴 rev"] == tree,
        "A-1 `COMPARABLE_REL` 을 import 하는 .py": {
            "🔴 세는 명령": g["1 소비자 명부 대조"]["🔴 세는 명령"],
            "🔴 범위": g["1 소비자 명부 대조"]["🔴 범위"],
            "🔴 어느 트리": g["1 소비자 명부 대조"]["🔴 어느 트리"],
            "🔴 수": g["1 소비자 명부 대조"]["실측 소비자 수"],
            "목록": sorted(g["1 소비자 명부 대조"]["실측 소비자"]),
        },
        "A-2 낱말 언급(🔴 **다른 분모**다 — 조항 60)": {
            "파일 수": g["낱말 언급(병기 · import 와 **다른 분모**)"]["파일 수"],
            "줄 수 합": g["낱말 언급(병기 · import 와 **다른 분모**)"]["줄 수 합"],
            "🔴 범위": ".py·.md·.json · 저장소 전량 · 같은 트리",
            "⚠ import 분모와 나란히 놓지 마라":
                "언급 ⊇ import. 두 수는 **다른 것을 센다**",
        },
        "A-3 🔴 관문 결과로 **분기하는** 자리": {
            "갈래 ㄱ — `if` 문(판정 갈래를 고른다)":
                g["2 분기 자리 회계"]["🔴 갈래 ㄱ — `if` 문 (판정 갈래를 고른다)"],
            "갈래 ㄴ — 내포 조건(부분집합을 만든다 · 판정에 안 쓴다고 러너가 자기 입으로 적는다)":
                g["2 분기 자리 회계"]["갈래 ㄴ — 내포 조건 (부분집합을 만든다)"],
            "갈래 ㄷ — 삼항": g["2 분기 자리 회계"]["갈래 ㄷ — 삼항"],
        },
        "A-4 🔴 게이트가 안 세는 갈래 — 상수를 **손으로 베낀** 자리": {
            "🔴 세는 명령": f"git archive {tree} | tar -x → .py 줄에 "
                      f"'{HAND_COPIES_NEEDLE}' 가 있고 'import' 가 없는 줄",
            "🔴 범위": ".py 만 · 저장소 전량",
            "🔴 어느 트리": tree,
            "실측": hand,
            "🔴 수": sum(len(v) for v in hand.values()),
            "🔴 뜻": "**단일 출처가 이미 갈라져 있다.** 상수를 고쳐도 이 사본들은 안 따라온다 — "
                  "「상수 하나를 고치면 저장소가 따라온다」는 전제가 실측으로 거짓이다",
        },
        "A-5 🔴 기본 인자 동결(게이트 3절)": {
            k: v for k, v in g["3 기본 인자 동결"].items()
            if k not in ("무엇",)},
    }


# ══════════════════════════════════════════════════════ B · 주입 시험
DRIVER = r'''
import importlib.util, json, os, sys
from pathlib import Path
ROOT = Path("/Users/ax/world_model"); sys.path.insert(0, str(ROOT))
import state.perm922 as perm922
mode = os.environ["G940_MODE"]
if mode in ("나", "다"):
    perm922.COMPARABLE_REL = float(os.environ["G940_CONST"])
if mode == "다":
    perm922.comparability.__kwdefaults__["rel_thr"] = float(os.environ["G940_THR"])
spec = importlib.util.spec_from_file_location(
    "perm922_run", str(ROOT / "runners/perm922_run.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.OUT = Path(os.environ["G940_OUT"])          # 🔴 증거물을 안 덮는다
m.main()
'''


def _run_inject(mode: str, const: float, thr: float, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    outp = SCRATCH / f"out922_{tag}.json"
    env = dict(os.environ, G940_MODE=mode, G940_CONST=repr(const),
               G940_THR=repr(thr), G940_OUT=str(outp))
    env.pop("WM_ALLOW_PAID_API", None)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(DRIVER)
        drv = fh.name
    t0 = dt.datetime.now(dt.timezone.utc)
    p = subprocess.run([sys.executable, drv], env=env, capture_output=True,
                       text=True)
    ok = outp.exists()
    d = json.loads(outp.read_text(encoding="utf-8")) if ok else {}
    return {
        "판": tag, "주입": mode,
        "종료코드": p.returncode,
        "🔴 종료코드를 성공으로 안 읽는다 — 산출물이 났나": ok,
        "산출물": str(outp),
        "초": round((dt.datetime.now(dt.timezone.utc) - t0).total_seconds(), 1),
        "산출물에 적힌 문턱": d.get("설정", {}).get("비교가능성 문턱(상대)"),
        "N2 상대차": d.get("⑦ 판정 재료(사전등록 §6)", {}).get("N2 상대차"),
        "N2 관문 결과(불리언)": d.get("⑦ 판정 재료(사전등록 §6)", {}).get("N2 비교가능성 통과"),
        "N1 상대차": d.get("⑦ 판정 재료(사전등록 §6)", {}).get("N1 상대차"),
        "🔴 판정문": d.get("🔴 판정 (사전등록 §6 을 기계로 적용)", {}).get("판정문"),
        "진짜 개선(일)": d.get("⑦ 판정 재료(사전등록 §6)", {}).get("진짜 개선(일)"),
        "N2 개선(일)": d.get("⑦ 판정 재료(사전등록 §6)", {}).get("N2 개선(일)"),
        "stderr 끝": p.stderr.strip().split("\n")[-1] if p.stderr.strip() else "",
    }


def part_B() -> dict:
    old = jload("runners/out922_permfix.json")
    oldv = {
        "산출물에 적힌 문턱": old["설정"]["비교가능성 문턱(상대)"],
        "N2 상대차": old["⑦ 판정 재료(사전등록 §6)"]["N2 상대차"],
        "N2 관문 결과(불리언)": old["⑦ 판정 재료(사전등록 §6)"]["N2 비교가능성 통과"],
        "N1 상대차": old["⑦ 판정 재료(사전등록 §6)"]["N1 상대차"],
        "🔴 판정문": old["🔴 판정 (사전등록 §6 을 기계로 적용)"]["판정문"],
        "진짜 개선(일)": old["⑦ 판정 재료(사전등록 §6)"]["진짜 개선(일)"],
        "N2 개선(일)": old["⑦ 판정 재료(사전등록 §6)"]["N2 개선(일)"],
    }
    runs = {
        "ㄱ 대조(주입 없음)": _run_inject("가", OLD_THR, OLD_THR, "ctrl"),
        "ㄴ 상수만 주입(1e-9)": _run_inject("나", 1e-9, OLD_THR, "constonly"),
        "ㄷ 기본 인자까지 주입(T=0.0151219535)":
            _run_inject("다", T939, T939, "kwdef"),
    }
    keys = ["N2 상대차", "N2 관문 결과(불리언)", "N1 상대차", "🔴 판정문",
            "진짜 개선(일)", "N2 개선(일)"]
    return {
        "무엇": "🔴 **값을 바꿔 넣고 결과가 바뀌는지** — 사전등록 §B 의 표 그대로",
        "⚠ 증거물 보호": "세 판 모두 산출물을 scratchpad 로 냈다. "
                  "`runners/out922_permfix.json` 은 **안 덮었다**",
        "옛 산출물(정본)": oldv,
        "판별": runs,
        "🔴 정본과 비트로 같은가": {
            tag: {k: (runs[tag][k] == oldv[k]) for k in keys} for tag in runs},
        "🔴🔴 무엇이 바뀌었나": {
            tag: {k: {"정본": oldv[k], "이 판": runs[tag][k]}
                  for k in keys if runs[tag][k] != oldv[k]} or "아무것도 안 바뀌었다"
            for tag in runs},
        "🔴 적히는 수 ≠ 쓰이는 수인가(ㄴ 판)": {
            "산출물에 적힌 문턱": runs["ㄴ 상수만 주입(1e-9)"]["산출물에 적힌 문턱"],
            "그런데 판정문이 바뀌었나":
                runs["ㄴ 상수만 주입(1e-9)"]["🔴 판정문"] != oldv["🔴 판정문"],
        },
    }


# ══════════════════════════════════════════════════════ C · 여섯 팔 새 양식
def slope_bca(x: np.ndarray, y: np.ndarray) -> dict:
    def stat(idx, x=x, y=y):
        xi, yi = x[idx], y[idx]
        xm = xi.mean()
        den = float(((xi - xm) ** 2).sum())
        if den <= 0:
            return float("nan")
        return float(((xi - xm) * (yi - yi.mean())).sum() / den)
    cl, cinfo = pairboot.solo_clusters(len(x))
    th, lo, hi, kind = pairboot.cluster_boot(stat, cl, B=BOOT_B, seed=BOOT_SEED)
    return {"기울기": th, "BCa 95%": [lo, hi], "구간 종류": kind,
            "🔴 폴백 사유(규약 47)": None if kind == "BCa" else kind,
            "군집 병기": cinfo, "판정": pairboot.verdict(lo, hi)}


def arms() -> dict:
    """여섯 팔의 재료를 산출물에서 **읽어서** 모은다. 없으면 None(→ 「못 잰다」)."""
    d935 = jload("runners/out935_rawpanel.json")
    d933 = jload("runners/out933_calpanel.json")
    d925 = jload("runners/out925_gapsplit.json")
    d922 = jload("runners/out922_permfix.json")
    A = {}

    recs = d935["⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다"]["기록"]
    rm = d935["② 항등 검사 (사전등록 §7-2·§7-4)"]["진짜 기준·시험 팔 MAE"]
    vd = d935["⑥ 🔴 판정용 순열"]
    for p in P935:
        y = np.asarray([r[p]["개선(일)"] for r in recs], float)
        x = np.asarray([r[p]["기준 팔 MAE"] for r in recs], float)
        sl = slope_bca(x, y)
        R = float(vd[p]["진짜"])
        A[f"935 {p}"] = {
            "rel": [r[p]["비교가능성 상대차"] for r in recs],
            "G": float((R - y).min()), "cr": float(rm[p]["기준"]),
            "L_used": max(1.0, float(sl["BCa 95%"][1])),
            "L_bca_hi": float(sl["BCa 95%"][1]), "전달률 BCa": sl,
            "used_for": "🔴 **아무것도 안 갈랐다** — 935 는 이 관문으로 부분집합을 안 만들었다"
                        "(러너가 자기 입으로 「병기 · 판정에 안 쓴다」라 적는다)",
            "출처": "runners/out935_rawpanel.json ⑤·②·⑥",
            "p": vd[p].get("🔴 순열 p = (1+k)/(1+B)"),
            "k": vd[p].get("🔴 귀무 ≥ 진짜 인 뽑기 수 k"),
        }

    r933 = d933["⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다"]["기록"]
    v933 = d933["⑥ 🔴 판정용 순열 — 판 둘"]["① [달력제거]"]
    y933 = np.asarray([r["① [달력제거]"]["개선(일)"] for r in r933], float)
    x933 = np.asarray([r["① [달력제거]"]["기준 팔 MAE"] for r in r933], float)
    A["933 전량 [달력제거]"] = {
        "rel": [r["비교가능성 상대차"] for r in r933],
        "G": float(float(v933["진짜"]) - y933.max()),
        "cr": float(x933[0]),
        "L_used": None, "L_bca_hi": None,
        "🔴 L 을 왜 못 쟀나": f"이 팔의 기준 팔 MAE 는 200뽑기 전부 같은 값이다"
                      f"(가짓수 {len(set(x933.tolist()))}) — 기울기의 분모가 0 이다. "
                      "🔴 **그것이 이 팔의 상대차가 정확히 0 인 이유이기도 하다**",
        "🔴 cr 을 어떻게 읽었나": "933 산출물에 「진짜 기준 팔 MAE」라는 이름의 필드가 **없다**. "
                        "200뽑기의 기준 팔 MAE 가 전부 같고 상대차가 정확히 0 이므로 "
                        "진짜의 기준 팔 MAE 와 같다 — 그 값을 썼다(🔴 **읽은 게 아니라 "
                        "유도했다**. 조항 59)",
        "used_for": "🔴 **아무것도 안 갈랐다** — 933 도 부분집합을 안 만들었다",
        "출처": "runners/out933_calpanel.json ⑤·⑥",
        "p": v933.get("🔴 순열 p = (1+k)/(1+B)"),
        "k": v933.get("🔴 귀무 ≥ 진짜 인 뽑기 수 k"),
    }

    g2 = d925["⑥ 관문 신고 (#178) — 🔴 관문마다 도달 가능 폭 ÷ 문턱"]["G2"]
    g1 = d925["⑥ 관문 신고 (#178) — 🔴 관문마다 도달 가능 폭 ÷ 문턱"]["G1 주 판정"]
    A["925 G2(주 판정 판 · B=1)"] = {
        "rel": [g2["실측"]],
        "G": float(g1["🔴 점추정 차(진짜 − 귀무)"]),
        "cr": float(g2["진짜 기후값 MAE"]),
        "L_used": None, "L_bca_hi": None,
        "🔴 L 을 왜 못 쟀나": "뽑기가 **하나**다(B=1) — 기울기를 낼 표본이 없다",
        "used_for": "🔴 **아무것도 안 갈랐다** — 925 는 자기 산출물에 "
                    "「이번엔 판정에 안 쓴다」라 적었다",
        "출처": "runners/out925_gapsplit.json ⑥ G1 주 판정 · G2",
        "p": None, "k": None,
    }

    R922 = float(d922["⑦ 판정 재료(사전등록 §6)"]["진짜 개선(일)"])
    cr922 = float(d922["③ 🔴 비교가능성 관문 — N2 대 진짜"]["기후값 MAE — 진짜(일)"])
    for nm, ykey, relkey in (("N2", "N2 개선(일)", "N2 상대차"),
                             ("N1", "N1 개선(일)", "N1 상대차"),
                             ("N0", "N0(판정 미사용) 개선(일)", "N0 상대차")):
        y = float(d922["⑦ 판정 재료(사전등록 §6)"][ykey])
        A[f"922 {nm}(B=1)"] = {
            "rel": [d922["⑦ 판정 재료(사전등록 §6)"][relkey]],
            "G": R922 - y, "cr": cr922,
            "L_used": None, "L_bca_hi": None,
            "🔴 L 을 왜 못 쟀나": "뽑기가 **하나**다(B=1)",
            "used_for": ("🔴 **이 팔은 실제로 갈랐다** — `perm922_run.py:433` 의 `if` 가 "
                         "N2 의 관문 결과로 §6-4(판정 불능) 갈래를 고른다"
                         if nm == "N2" else
                         "🔴 **이 팔은 판정에서 빠졌다** — 러너가 「상대차가 문턱을 넘는다」를 "
                         "이유로 병기만 했다(N0 은 애초에 심은 결함이라 판정 미사용)"),
            "출처": "runners/out922_permfix.json ③·⑤·⑦",
            "p": None, "k": None,
        }
    return A


def part_C(A: dict) -> dict:
    rep = {}
    for name, a in A.items():
        L = a["L_used"]
        lower = L is None
        note = a.get("🔴 L 을 왜 못 쟀나", "")
        if lower:
            note = (f"🔴 **L 을 못 쟀다** ({note}). L ≥ 1 이므로 L=1 로 낸 이 r 은 "
                    "**하한**이다 — 참값은 이보다 크거나 같다")
        rep[name] = ratio940.sensitivity_ratio(
            name, rel_values=a["rel"], G=a["G"], cr=a["cr"],
            L_used=1.0 if lower else L, L_bca_hi=a["L_bca_hi"],
            used_for=a["used_for"], note=note)
        rep[name]["🔴 이 r 은 하한인가(L 을 못 쟀다)"] = lower
        rep[name]["출처"] = a["출처"]
        if a.get("🔴 cr 을 어떻게 읽었나"):
            rep[name]["🔴 cr 을 어떻게 읽었나"] = a["🔴 cr 을 어떻게 읽었나"]
        if a.get("전달률 BCa"):
            rep[name]["전달률 BCa(규약 47)"] = a["전달률 BCa"]
    rs = {k: v.get("🔴🔴 r = m · L_used · cr / G") for k, v in rep.items()}
    ok = {k: v for k, v in rs.items() if v is not None}
    return {
        "무엇": "🔴 여섯 출처 · 여덟 팔을 **새 양식(규약 61)**으로 다시 신고한다",
        "팔별": rep,
        "🔴 r 한눈에": rs,
        "🔴 r ≥ 1 인 팔(기준 팔 차이 하나만으로 순위가 뒤집힐 수 있는 팔)":
            sorted(k for k, v in ok.items() if v >= 1.0),
        "🔴 r < 1 인 팔": sorted(k for k, v in ok.items() if v < 1.0),
        "🔴 못 잰 팔": sorted(k for k, v in rs.items() if v is None),
        "🔴 팔 수(분모)": len(rep),
        "🔴 r 이 몇 배 갈리나": (max(ok.values()) / min(ok.values())
                        if ok and min(ok.values()) > 0 else
                        "🔴 못 낸다 — r=0 인 팔이 있다(933 은 상대차가 정확히 0)"),
    }


# ══════════════════════════════════════════════════════ D · k·p 불변
def part_D(A: dict) -> dict:
    d939 = jload("runners/out939_threshold.json")
    a5 = d939["A-5 · 관문 재계수"]["팔별"]
    rows = {}
    for name in a5:
        rows[name] = {
            "939 옛 문턱 0.05 에서 k": a5[name]["옛 문턱 0.05"]["🔴 걸린 뽑기 k"],
            "939 새 문턱 T 에서 k": a5[name]["🔴 새 문턱 T"]["🔴 걸린 뽑기 k"],
            "939 가 낸 r(= m ÷ T_판①)": a5[name]["🔴 새 문턱 T"]["🔴 관측 최댓값 ÷ 문턱 = r"],
        }
    ps = {k: {"p": v["p"], "k": v["k"]} for k, v in A.items()
          if v.get("p") is not None}
    return {
        "무엇": "🔴 신고 양식을 바꿔도 **판정의 k·p 는 안 바뀐다** — 그 사실을 못 박는다",
        "939 의 k 표(그대로 읽었다)": rows,
        "각 팔의 순열 p·k(산출물에서 읽었다)": ps,
        "🔴 이 사이클이 p 를 다시 계산했나": False,
        "🔴 이 사이클이 어떤 뽑기를 뺐나": "0개 — **부분집합을 안 만들었다**",
        "🔴 그래서 무엇이 바뀌나": "바뀌는 것은 **「관문이 지켜 줬다」고 말할 수 있는가** 하나다. "
                        "🔴 그리고 922 에서는 그 말이 **참이다** — 거기서는 관문이 실제로 "
                        "갈래를 골랐다(§B 가 주입으로 확인한다)",
    }


# ══════════════════════════════════════════════════════ E · CP 항등식
def part_E() -> dict:
    Bs = [10, 50, 200, 1000, 5000]
    tbl = {}
    for k in (0, 1, 2):
        row = {}
        for B in Bs:
            u = gate939.cp_upper(k, B)
            row[B] = {"u": u, "1 − (1−u)^B": 1.0 - (1.0 - u) ** B}
        tbl[f"k={k}"] = row
    k0 = [tbl["k=0"][B]["1 − (1−u)^B"] for B in Bs]
    k1 = [tbl["k=1"][B]["1 − (1−u)^B"] for B in Bs]
    return {
        "무엇": "🔴 폐기의 근거 — `k=0` 에서 「B뽑기 발화확률」이 **항등식**인지 다시 센다",
        "표": tbl,
        "🔴 k=0 에서 B 를 바꿔도 같은가": max(k0) - min(k0) < 1e-12,
        "🔴 k=0 의 값": k0[0],
        "⚠ k=1 에서는 같지 않다": {"값들": k1, "폭": max(k1) - min(k1)},
        "🔴 그래서 무엇을 폐기하나": "**`k=0` 일 때의 그 한 줄**이다. k ≥ 1 에서는 정보가 있다 — "
                        "🔴 **「그 수를 늘 폐기한다」가 아니다**(939 의 병을 반대 방향으로 "
                        "되풀이하지 않는다)",
        "🔴 대수": "k=0 이면 CP 상한은 P(X≤0;B,u) = (1−u)^B = 1−conf 를 푼 수다. "
              "그러므로 1−(1−u)^B ≡ conf = 0.95 — **B 와 무관**",
    }


# ══════════════════════════════════════════════════════ F · 939 와의 대조
def part_F(A: dict, C: dict) -> dict:
    d939 = jload("runners/out939_threshold.json")
    a5 = d939["A-5 · 관문 재계수"]["팔별"]
    per939 = d939["A · 문턱"]["팔별"]
    name_map = {f"935 {p}": f"935 {p}" for p in P935}
    rows = {}
    for k, v in name_map.items():
        if v not in a5:
            continue
        r_new = C["팔별"][k].get("🔴🔴 r = m · L_used · cr / G")
        r_939 = a5[v]["🔴 새 문턱 T"]["🔴 관측 최댓값 ÷ 문턱 = r"]
        rows[k] = {
            "939 의 r (= m ÷ T_판① · **한 팔의 T 를 다섯 팔에 돌려 썼다**)": r_939,
            "🔴 새 r (= m · L_used · cr / G · **그 팔 자신의 재료로**)": r_new,
            "같은가": (r_new is not None and abs(r_new - r_939) < 1e-9),
            "비": (r_new / r_939 if r_new and r_939 else None),
        }
    # L 재현 대조
    Lrep = {}
    for p in P935:
        Lrep[f"935 {p}"] = {
            "939 가 낸 L_used": per939[p]["🔴 L_used = max(1.0, BCa 상한)"],
            "이 사이클이 다시 낸 L_used": A[f"935 {p}"]["L_used"],
            "🔴 비트로 같은가":
                per939[p]["🔴 L_used = max(1.0, BCa 상한)"] == A[f"935 {p}"]["L_used"],
            "939 가 낸 G": per939[p]["🔴 G 빈틈 = min(R − y_i)(일)"],
            "이 사이클의 G": A[f"935 {p}"]["G"],
            "🔴 G 가 비트로 같은가":
                per939[p]["🔴 G 빈틈 = min(R − y_i)(일)"] == A[f"935 {p}"]["G"],
        }
    return {
        "무엇": "🔴 939 의 r 과 새 r 을 나란히 놓는다 — **어디서 갈리나**",
        "🔴 대수 항등": "r_939 = m ÷ T_판① 이고 T_팔 = G_팔/(L_팔·cr_팔) 이므로, "
                 "**판① 에서만** r_939 = m·L·cr/G 이다. 다른 팔에서는 **남의 T** 를 쓴 수다",
        "팔별": rows,
        "L·G 재현(939 와 같은 씨앗 939 · B=10,000 · 규약 47 BCa)": Lrep,
    }


# ══════════════════════════════════════════════════════ 판정
def verdicts(A: dict, Ap: dict, B: dict, C: dict, F: dict) -> dict:
    n_imp = Ap["A-1 `COMPARABLE_REL` 을 import 하는 .py"]["🔴 수"]
    ifs = Ap["A-3 🔴 관문 결과로 **분기하는** 자리"]["갈래 ㄱ — `if` 문(판정 갈래를 고른다)"]
    if_files = sorted({x["파일"] for x in ifs})
    ctrl = B["판별"]["ㄱ 대조(주입 없음)"]
    const = B["판별"]["ㄴ 상수만 주입(1e-9)"]
    kwd = B["판별"]["ㄷ 기본 인자까지 주입(T=0.0151219535)"]
    old = B["옛 산출물(정본)"]
    P = {
        "P1 import 하는 .py 가 3~6개": {
            "실측": n_imp, "맞았나": 3 <= n_imp <= 6},
        "P2 관문으로 분기하는 파일은 perm922_run.py 하나뿐": {
            "실측": if_files,
            "맞았나": if_files == ["runners/perm922_run.py"]},
        "P3 상수만 주입하면 판정문이 **안 바뀐다**": {
            "정본 판정문": old["🔴 판정문"], "ㄴ 판정문": const["🔴 판정문"],
            "맞았나": const["🔴 판정문"] == old["🔴 판정문"]},
        "P4 그런데 산출물에 적히는 문턱은 1e-9 로 바뀐다": {
            "실측": const["산출물에 적힌 문턱"],
            "맞았나": const["산출물에 적힌 문턱"] == 1e-9},
        "P5 대조판이 정본을 비트로 재현한다": {
            "N2 상대차": ctrl["N2 상대차"] == old["N2 상대차"],
            "판정문": ctrl["🔴 판정문"] == old["🔴 판정문"],
            "진짜 개선": ctrl["진짜 개선(일)"] == old["진짜 개선(일)"],
            "맞았나": (ctrl["N2 상대차"] == old["N2 상대차"]
                    and ctrl["🔴 판정문"] == old["🔴 판정문"]
                    and ctrl["진짜 개선(일)"] == old["진짜 개선(일)"])},
        "P6 922 N1 의 상대차가 0.05 를 넘는다": {
            "실측": old["N1 상대차"], "맞았나": abs(old["N1 상대차"]) > OLD_THR,
            "⚠": "🔴 이것은 예측이 아니라 **자기 대조**다 — 스탬프에 그렇게 적어 뒀다"},
        "P7 새 r 은 판① 에서만 939 와 같다": {
            "실측": {k: v["같은가"] for k, v in F["팔별"].items()},
            "맞았나": ([k for k, v in F["팔별"].items() if v["같은가"]]
                    == ["935 ① 원판 전량"])},
        "P8 k·p 가 한 팔도 안 바뀐다": {
            "실측": "이 사이클은 p 를 다시 계산하지 않았고 뽑기를 하나도 안 뺐다",
            "맞았나": True},
    }
    hit = sum(1 for v in P.values() if v["맞았나"])

    cond1 = True            # 새 자를 쓰는 실행 경로
    cond2 = (kwd["🔴 판정문"] != old["🔴 판정문"]) or (kwd["N2 관문 결과(불리언)"]
                                                != old["N2 관문 결과(불리언)"])
    cond3 = True            # 게이트가 있다
    return {
        "🔴 미리 박은 예측 여덟의 채점": P,
        "🔴 맞은 수": f"{hit}/8",
        "🔴🔴 배선 판정(사전등록 §4 판정규칙)": {
            "① 새 자를 쓰는 실행 경로가 있나": {
                "답": cond1,
                "근거": "`runners/gate940_wiring.py` 가 `state/ratio940` 을 부르고 "
                      "`runners/ratio940_run.py` §C 가 여덟 팔을 새 자로 신고한다"},
            "② 그 경로에서 값을 바꾸면 산출물이 바뀌나": {
                "답": cond2,
                "🔴 근거": {
                    "상수만 바꿨을 때(ㄴ)": "판정문 바뀜="
                        f"{const['🔴 판정문'] != old['🔴 판정문']} · "
                        f"적힌 문턱={const['산출물에 적힌 문턱']}",
                    "기본 인자까지 바꿨을 때(ㄷ)": "판정문 바뀜="
                        f"{kwd['🔴 판정문'] != old['🔴 판정문']} · 관문 불리언 바뀜="
                        f"{kwd['N2 관문 결과(불리언)'] != old['N2 관문 결과(불리언)']}"}},
            "③ 새 소비자가 생기면 붉어지는 기계 검사가 있나": {
                "답": cond3,
                "근거": "`runners/gate940_wiring.py` 1절 — `state/ratio940.CONSUMERS` "
                      "명부와 커밋된 트리의 ast import 실측을 대조한다"},
            "🔴🔴 판정": ("**배선을 넣었다**" if (cond1 and cond2 and cond3)
                     else "🔴 **못 넣었다 — 명문화로 간다**"),
        },
    }


def main() -> None:
    t0 = dt.datetime.now(dt.timezone.utc)
    rev = git("rev-parse", "HEAD").strip()
    Ap = part_A(rev)
    Bp = part_B()
    A = arms()
    Cp = part_C(A)
    Dp = part_D(A)
    Ep = part_E()
    Fp = part_F(A, Cp)
    V = verdicts(A, Ap, Bp, Cp, Fp)

    out = {
        "팔": "940-ㄱ — 🔴 **T 를 문턱에서 민감도 비 r 로 강등하고, 배선을 주입으로 확인한다**",
        "사전등록": "docs/prereg_940_ratio.md",
        "티처": "runners/out938_teacher.json 다음의 티처 #79 · **1순위**",
        "🔴 판 ρ": "안 쓴다 — 이 물음은 판으로 못 잰다(⓪-가)",
        "🔴 이 사이클에 크기 판정이 없다":
            "새 팔을 안 쟀다 — 규율 4 의 X · Y_상한 · Y_도달 · Z 전부 **해당 없음**(빈칸 아님). "
            "병기: 935 네 판의 Z_self 1.1553 / 2.1345 / 3.0452 / 4.587 — 넷 다 1 초과이고 "
            "이 사이클이 그 수를 안 건드린다",
        "🔴 사전등록 시각 증거": part0(),
        "코드 sha256": {f: sha(ROOT / f) for f in
                      ["state/ratio940.py", "runners/ratio940_run.py",
                       "runners/gate940_wiring.py", "runners/ratio940_stamp.py",
                       "state/perm922.py", "state/gate939.py",
                       "runners/perm922_run.py"]},
        "🔴 이 러너가 안 한 것": [
            "새 순열 뽑기 — 935·933·925 는 **읽어서** 다시 셌다",
            "🔴 예외 하나: §B 가 `perm922_run.py` 를 **세 번 다시 돌렸다**(27초짜리). "
            "그것은 새 자료가 아니라 **같은 자료에 문턱만 바꿔 넣는 대조**다",
            "산출물 수정 0 — `runners/out*.json` 을 읽기만 했다",
            "`state/perm922.py`·`state/gap925.py`·`state/gate939.py` 수정 0",
            "🔴 `b_prv=−1` 칸 안 건드렸다(이슈 #187)",
            "유료 API 0",
        ],
        "A · 배선 실측": Ap,
        "B · 주입 시험": Bp,
        "C · 여덟 팔 새 양식(규약 61)": Cp,
        "D · k·p 불변": Dp,
        "E · CP 항등식": Ep,
        "F · 939 와의 대조": Fp,
        "🔴🔴 판정": V,
        "🔴 폐기 목록(state/ratio940.RETIRED)": ratio940.RETIRED,
        "🔴 옛 상수를 어떻게 했나": ratio940.OLD_CONSTANT,
        "시작 UTC": t0.isoformat(),
    }
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat()
    out["초"] = (dt.datetime.fromisoformat(out["끝 UTC"]) - t0).total_seconds()
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT, out["초"], "초")
    print(json.dumps(V["🔴🔴 배선 판정(사전등록 §4 판정규칙)"]["🔴🔴 판정"],
                     ensure_ascii=False))
    print(json.dumps({k: v["맞았나"] for k, v in
                      V["🔴 미리 박은 예측 여덟의 채점"].items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
