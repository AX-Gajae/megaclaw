#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""978 — **수리 다섯의 증거**와 **정정 다섯의 증거**를 한 산출물로 낸다.

🔴 **수리는 다섯이고 상한도 다섯이다. 안 묶었다.**
🔴 **정정 다섯(사전등록 §9)은 수리로 안 센다.**

씀:
    python3 runners/scorefix978.py --stage fix --ref <40자 sha>
"""
import argparse
import ast
import builtins
import collections
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                               # noqa: E402
import meta965 as M                               # noqa: E402

RAN = ("runners/scorefix978.py", "runners/ledger.py", "runners/meta965.py",
       "runners/ruler978.py", "runners/predict971.py")
OUT = ROOT / "runners"

#: 🔴 977 이 머지된 `main` 커밋 — 「고치기 전」 blob 을 여기서 꺼낸다(대조).
BEFORE_REF = "63485e11b5a726234dd9ef7dd30e4a7a5ef65ae6"
#: 🔴 심기를 얹을 **실제 러너 크기** 호스트(수리 2). 977 은 62 줄짜리에 심었다.
BIG_HOST = "runners/alpha977.py"

PASSKEYS = ("contains", "exact", "suffix")
SCOPES = ("file", "func")
GENVERS = (1, 2)

REPAIRS = [
    "1. 🔴🔴 **`--passkey` 축을 V2·V3 에 넣었다** — 977 은 `poolscope`(file↔func)와 "
    "`genver` 만 쓸었는데 티처 #116 이 12 조합 전수로 재니 **그 둘은 수를 안 움직이고** "
    "`--passkey` 만 움직인다(contains 10 ↔ exact 0 ↔ suffix 0). "
    "978 은 **`passkey × poolscope × genver` 12 칸 전수**로 낸다.",
    "2. 🔴🔴 **심기를 실제 러너 크기(≥1,000 줄) 파일에 얹어 천장을 깼다** — 977 의 심은 "
    "파일은 **62 줄**인데 인용 대상은 **1,186 줄**(19 배)이고 네 칸이 전부 4/4 라 "
    "**분해능이 0** 이었다. 같은 심기 여덟을 진짜 러너 소스에 얹어 12 칸에서 다시 잰다.",
    "3. 🔴🔴 **`meta965.py:1385` 를 고쳤다** — 972~977 **일곱 사이클** 미이행. §4 F1 의 "
    "판정을 `f1_counts`(세기)와 `f1_verdict`(판정)로 가르고, 판정을 **정수 둘의 함수**로 "
    "낮춘 뒤 허용값 `F1_ALLOWED_TAUT` 를 전역으로 올렸다. 🔴 **빈 분모로 통과하던 "
    "fail-open 도 같이 닫았다**(`n_denom > 0`).",
    "4. 🔴🔴 **`numaudit` 에 한글 수사를 태웠다** — 977 의 「본문 **넷** 0 / 370」이 "
    "판정문·카드·원장 셋을 그대로 통과했다. `NUMPAT` 은 아라비아 숫자만 본다.",
    "5. 🔴🔴 **배선 W 를 `select()` 밖으로 냈다** — 977 의 W1~W4 는 전부 `select()` "
    "하나를 물었고, **문턱 판정을 전부 지는 이중 붓스트랩 SE 코드 · `over_seeds` · "
    "`score()` 균등 팔에는 검사가 0 개**였다.",
]
CORRECTIONS = [
    "1. 🔴 977 의 **「본문 넷」을 「다섯」으로 정정한다** — `numaudit` 분모는 다섯이고 "
    "194+71+51+25+29 = 370 이다.",
    "2. 🔴 977 의 **붓스트랩 뽑기 수를 신고한다** — 사전등록 §3 은 400 인데 코드·산출물은 "
    "200 이었고 사유가 어디에도 없다. **모든 문턱 판정이 그 SE 위에 섰다.**",
    "3. 🔴 976 의 **밑판 P 학습 행 수 두 값을 게재한다** — 37,535 는 **겹 0 의 행 수**이고 "
    "37,531 은 **겹 평균**이다. 977 사전등록 §11-4 가 등록했는데 다섯 본문에서 0 회였다.",
    "4. 🔴 **`paper/steps/977_alpha/meta.json` 의 `\"sent\"` 를 사실에 맞춘다** — "
    "저장소는 `false` 인데 논문은 실제로 나갔다.",
    "5. 🔴 **논문 claim #7 의 「제대로 내려간다」를 철회한다** — 977 판정문은 "
    "「자기 표준오차의 두 배를 못 넘는다」로 정직한데 claim 층에만 자백이 안 실렸다.",
]


def _blob(ref, rel):
    try:
        return subprocess.check_output(["git", "show", "%s:%s" % (ref, rel)],
                                       cwd=str(ROOT)).decode("utf-8")
    except Exception:                                              # noqa: BLE001
        return ""


def _load(name):
    p = OUT / name if not str(name).startswith("/") else Path(name)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


# ══════════════════════════════════════════════════════════════════════
# 🔴 수리 1 + 2 — V2·V3 를 **세 축 12 칸**에서 · **두 호스트**에서
# ══════════════════════════════════════════════════════════════════════
def _scan_planted(src, seed=None):
    """심은 소스를 훑어 `{함수: 잡은 자}` 를 낸다."""
    ns = {"__builtins__": builtins}
    try:
        exec(compile(ast.parse(src), "<심은 키>", "exec"), ns)      # noqa: S102
    except Exception as e:                                         # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)
    with M._NoWrite():
        rows = M.scan_source("<심은 키>", src, ns,
                             random.Random(seed if seed is not None else M.SEED))
    by = collections.defaultdict(list)
    for r in rows:
        by[r["함수"]].append(r)
    return by, None


def v2v3_axes(host_name, src):
    """🔴 `passkey × poolscope × genver` **12 칸 전수**에서 검정력·거짓 양성."""
    tab = collections.OrderedDict()
    old = (M.PASSKEY, M.POOLSCOPE, M.GENVER)
    try:
        for pk in PASSKEYS:
            for sc in SCOPES:
                for gv in GENVERS:
                    M.PASSKEY, M.POOLSCOPE, M.GENVER = pk, sc, gv
                    by, err = _scan_planted(src)
                    key = "passkey=%s · poolscope=%s · genver=%d" % (pk, sc, gv)
                    if err:
                        tab[key] = {"🔴 훑기 실패": err, "통과": False}
                        continue
                    caught, missed = collections.OrderedDict(), []
                    for fn, want in M.PLANTED.items():
                        got = sorted({z for r in by.get(fn, []) for z in r["🔴 잡은 자"]})
                        caught[fn] = {"기대한 자": want, "잡은 자": got or "없음",
                                      "잡았나": bool(got),
                                      "기대한 자가 잡았나": want in got}
                        if not got:
                            missed.append(fn)
                    fps = collections.OrderedDict()
                    for fn in M.NEGATIVE:
                        got = sorted({z for r in by.get(fn, []) for z in r["🔴 잡은 자"]})
                        fps[fn] = {"잡은 자": got or "없음", "거짓 양성인가": bool(got)}
                    n_fp = sum(1 for v in fps.values() if v["거짓 양성인가"])
                    n_site = sum(len(by.get(fn, [])) for fn in
                                 list(M.PLANTED) + list(M.NEGATIVE))
                    tab[key] = {
                        "🔴 검정력 분자/분모": "%d / %d" % (
                            len(M.PLANTED) - len(missed), len(M.PLANTED)),
                        "🔴 거짓 양성 분자/분모": "%d / %d" % (n_fp, len(M.NEGATIVE)),
                        "🔴 훑은 자리 수(심은 여덟 함수 안)": n_site,
                        "못 잡은 심기": missed or "없음",
                        "심은 키별": caught, "음성 대조별": fps,
                        "통과": bool((not missed) and n_fp == 0),
                    }
    finally:
        M.PASSKEY, M.POOLSCOPE, M.GENVER = old
    pw = {k: v.get("🔴 검정력 분자/분모") for k, v in tab.items()}
    fp = {k: v.get("🔴 거짓 양성 분자/분모") for k, v in tab.items()}
    site = {k: v.get("🔴 훑은 자리 수(심은 여덟 함수 안)") for k, v in tab.items()}

    def _byaxis(vals, idx, names):
        o = collections.OrderedDict()
        for n in names:
            sub = {k: v for k, v in vals.items() if k.split(" · ")[idx].endswith(str(n))}
            o[str(n)] = sorted(set(str(v) for v in sub.values()))
        return o
    return {
        "🔴 호스트": host_name,
        "🔴 호스트 줄 수": src.count("\n") + 1,
        "칸별": tab,
        "🔴🔴 12 칸 검정력": pw,
        "🔴🔴 12 칸 거짓 양성": fp,
        "🔴🔴 12 칸 훑은 자리 수": site,
        "🔴🔴🔴 검정력의 서로 다른 값": sorted(set(str(v) for v in pw.values())),
        "🔴🔴🔴 분해능(검정력이 서로 다른 값의 가짓수)": len(set(str(v) for v in pw.values())),
        "🔴 축별 — passkey": _byaxis(pw, 0, PASSKEYS),
        "🔴 축별 — poolscope": _byaxis(pw, 1, SCOPES),
        "🔴 축별 — genver": _byaxis(pw, 2, GENVERS),
        "🔴🔴 자리 수의 서로 다른 값": sorted(set(str(v) for v in site.values())),
        "통과": bool(len(tab) == len(PASSKEYS) * len(SCOPES) * len(GENVERS)),
        "🔴 이 절의 `통과` 가 뜻하는 것": "12 칸을 **전부 돌렸다**(값이 무엇이든 적는다)",
    }


CENSUS_FILES = ("runners/ruler978.py", "runners/ledger.py",
                "runners/scorefix978.py", "runners/meta965.py")


def census_axes(rels=CENSUS_FILES):
    """🔴🔴 **수리 1 (둘째 반쪽)** — 세 축 12 칸에서 **이 사이클 러너 전량**을 훑는다.

    티처 #116 이 실측한 것: `poolscope` 는 항진명제 수를 **10↔10 으로 안 움직이고**
    `genver` 도 0~1 이동인데 **`passkey` 는 contains 10 ↔ exact 0 ↔ suffix 0** 이다.
    🔴 **977 은 수를 안 움직이는 두 축만 쓸었다.** 여기서 세 축을 다 쓴다.
    """
    ns_cache = {}
    for rel in rels:
        ns_cache[rel] = M.import_ns(rel)[0]
    tab = collections.OrderedDict()
    old = (M.PASSKEY, M.POOLSCOPE, M.GENVER)
    try:
        for pk in PASSKEYS:
            for sc in SCOPES:
                for gv in GENVERS:
                    M.PASSKEY, M.POOLSCOPE, M.GENVER = pk, sc, gv
                    per, n_site, n_taut, n_prose = collections.OrderedDict(), 0, 0, 0
                    for rel in rels:
                        src = (ROOT / rel).read_text(encoding="utf-8")
                        with M._NoWrite():
                            rows = M.scan_source(rel, src, ns_cache[rel],
                                                 random.Random(M.SEED))
                        taut = [r for r in rows if r["🔴 항진명제인가"]]
                        #: 🔴 `contains` 갈래는 **`통과` 라는 낱말이 든 설명 키**까지 센다
                        #: (예: `"🔴 이 절의 `통과` 가 뜻하는 것"`). 그것은 **검사가 아니라
                        #: 글**이다. 🔴 **분모를 안 줄이고 갈라서 둘 다 적는다**(조항 60).
                        prose = [r for r in taut
                                 if re.match(r"^\s*['\"]", r["표현식"])]
                        per[rel] = {
                            "자리": len(rows), "항진명제": len(taut),
                            "🔴 그중 설명 문자열": len(prose),
                            "🔴 정직한 항진명제": len(taut) - len(prose),
                            "자리 목록(항진)": [r["자리"] for r in taut][:12],
                        }
                        n_site += len(rows)
                        n_taut += len(taut)
                        n_prose += len(prose)
                    tab["passkey=%s · poolscope=%s · genver=%d" % (pk, sc, gv)] = {
                        "🔴 자리 합": n_site, "🔴 항진명제 합": n_taut,
                        "🔴 설명 문자열 합": n_prose,
                        "🔴🔴 정직한 항진명제 합": n_taut - n_prose,
                        "파일별": per,
                    }
    finally:
        M.PASSKEY, M.POOLSCOPE, M.GENVER = old

    def _axis(idx, names, key):
        o = collections.OrderedDict()
        for n in names:
            sub = [v[key] for k, v in tab.items()
                   if k.split(" · ")[idx].endswith(str(n))]
            o[str(n)] = sorted(set(sub))
        return o
    return {
        "🔴 훑은 파일": list(rels),
        "칸별": tab,
        "🔴🔴 12 칸 자리 수": {k: v["🔴 자리 합"] for k, v in tab.items()},
        "🔴🔴 12 칸 항진명제 수": {k: v["🔴 항진명제 합"] for k, v in tab.items()},
        "🔴🔴 12 칸 정직한 항진명제 수": {k: v["🔴🔴 정직한 항진명제 합"]
                                for k, v in tab.items()},
        "🔴🔴🔴 축별 자리 수 — passkey": _axis(0, PASSKEYS, "🔴 자리 합"),
        "🔴🔴🔴 축별 자리 수 — poolscope": _axis(1, SCOPES, "🔴 자리 합"),
        "🔴🔴🔴 축별 자리 수 — genver": _axis(2, GENVERS, "🔴 자리 합"),
        "🔴🔴 축별 항진명제 — passkey": _axis(0, PASSKEYS, "🔴 항진명제 합"),
        "🔴🔴 축별 항진명제 — poolscope": _axis(1, SCOPES, "🔴 항진명제 합"),
        "🔴🔴 축별 항진명제 — genver": _axis(2, GENVERS, "🔴 항진명제 합"),
        "통과": bool(len(tab) == len(PASSKEYS) * len(SCOPES) * len(GENVERS)),
        "🔴 이 절의 `통과` 가 뜻하는 것": "세 축 12 칸을 **전부** 돌렸다",
    }


def big_host_src():
    """🔴 수리 2 — **실제 러너 소스에 심기 여덟을 얹는다**(≥1,000 줄)."""
    host = (ROOT / BIG_HOST).read_text(encoding="utf-8")
    planted = M.PLANTED_SRC.split('"""', 2)[-1]      # 앞머리 주석을 뗀다
    return host + "\n\n# ── 🔴 978 수리 2: 심기 여덟을 실제 러너 소스에 얹는다 ──\n" + planted


# ══════════════════════════════════════════════════════════════════════
def stage_fix(ref):
    t0 = LG.now()
    cs0 = LG.code_stamp(RAN)

    # ── 수리 1 · 2 ────────────────────────────────────────────
    small = v2v3_axes("977 판 심은 소스(`meta965.PLANTED_SRC`)", M.PLANTED_SRC)
    big_src = big_host_src()
    big = v2v3_axes("978 판 — `%s` 에 얹었다" % BIG_HOST, big_src)
    census = census_axes()
    r1 = {
        "🔴 무엇": ("977 은 `poolscope × genver` **네 칸**만 쓸었다. 978 은 "
                 "`passkey × poolscope × genver` **12 칸 전수**로 낸다"),
        "🔴🔴🔴 이 사이클 러너 전량의 12 칸 전수(항진명제 census)": census,
        "🔴🔴 어느 축이 수를 움직이나": {
            "passkey": bool(len(set(tuple(v) for v in
                                    census["🔴🔴🔴 축별 자리 수 — passkey"].values())) > 1),
            "poolscope": bool(len(set(tuple(v) for v in
                                      census["🔴🔴🔴 축별 자리 수 — poolscope"].values())) > 1),
            "genver": bool(len(set(tuple(v) for v in
                                   census["🔴🔴🔴 축별 자리 수 — genver"].values())) > 1),
        },
        "🔴🔴🔴 작은 호스트(977 과 같은 심은 소스)": small,
        "🔴🔴 977 이 쓴 축": ["poolscope", "genver"],
        "🔴🔴 977 이 안 쓴 축": ["passkey"],
        "🔴🔴 passkey 가 수를 움직이나": bool(
            len(set(tuple(v) for v in small["🔴 축별 — passkey"].values())) > 1),
        "🔴🔴 poolscope 가 수를 움직이나": bool(
            len(set(tuple(v) for v in small["🔴 축별 — poolscope"].values())) > 1),
        "🔴🔴 genver 가 수를 움직이나": bool(
            len(set(tuple(v) for v in small["🔴 축별 — genver"].values())) > 1),
        "통과": bool(small["통과"]),
        "🔴 이 절의 `통과` 가 뜻하는 것": "세 축 12 칸을 전부 돌렸다",
    }
    r2 = {
        "🔴 무엇": ("977 의 심은 파일은 **%d 줄**인데 인용 대상은 **%d 줄**이었다. "
                 "같은 심기를 진짜 러너 소스에 얹어 12 칸에서 다시 잰다"
                 % (small["🔴 호스트 줄 수"], big["🔴 호스트 줄 수"])),
        "🔴 작은 호스트 줄 수": small["🔴 호스트 줄 수"],
        "🔴 큰 호스트 줄 수": big["🔴 호스트 줄 수"],
        "🔴 배수": round(big["🔴 호스트 줄 수"] / float(small["🔴 호스트 줄 수"]), 4),
        "🔴🔴🔴 큰 호스트 12 칸": big,
        "🔴🔴 작은 호스트의 분해능": small["🔴🔴🔴 분해능(검정력이 서로 다른 값의 가짓수)"],
        "🔴🔴 큰 호스트의 분해능": big["🔴🔴🔴 분해능(검정력이 서로 다른 값의 가짓수)"],
        "🔴🔴🔴 호스트를 키우면 검정력이 바뀌나": bool(
            small["🔴🔴 12 칸 검정력"] != big["🔴🔴 12 칸 검정력"]),
        "🔴🔴 호스트를 키우면 거짓 양성이 바뀌나": bool(
            small["🔴🔴 12 칸 거짓 양성"] != big["🔴🔴 12 칸 거짓 양성"]),
        "통과": bool(big["통과"]),
        "🔴 이 절의 `통과` 가 뜻하는 것": "큰 호스트에서도 12 칸을 전부 돌렸다",
    }

    # ── 수리 3 — `meta965.py:1385` ────────────────────────────
    before = _blob(BEFORE_REF, "runners/meta965.py")
    after = (ROOT / "runners/meta965.py").read_text(encoding="utf-8")
    ns, _e = M.import_ns("runners/meta965.py")

    def _scan_self(src, tag):
        with M._NoWrite():
            rows = M.scan_source("runners/meta965.py@" + tag, src, ns,
                                 random.Random(M.SEED))
        taut = [r for r in rows if r["🔴 항진명제인가"]]
        return rows, taut

    rows_b, taut_b = _scan_self(before, "before")
    rows_a, taut_a = _scan_self(after, "after")
    site_a = [r for r in rows_a if r["함수"] == "f1_verdict"]
    r3 = {
        "🔴 무엇": ("972~977 **일곱 사이클** 미이행. §4 F1 의 `통과` 가 자 B 에게 "
                 "**항진명제**로 잡혔다"),
        "🔴 고치기 전 ref": BEFORE_REF,
        "🔴🔴 고치기 전 항진명제 수": len(taut_b),
        "🔴 고치기 전 항진명제 자리": [r["자리"] for r in taut_b] or "없음",
        "🔴 고치기 전 그 자리의 표현식": (taut_b[0]["표현식"] if taut_b else "없음"),
        "🔴 고치기 전 자 B 판정": (taut_b[0]["자 B"].get("판정") if taut_b else None),
        "🔴🔴 고친 뒤 항진명제 수": len(taut_a),
        "🔴 고친 뒤 항진명제 자리": [r["자리"] for r in taut_a] or "없음",
        "🔴🔴🔴 고친 뒤 그 판정 자리": [
            {"자리": r["자리"], "표현식": r["표현식"],
             "자 B 판정": r["자 B"].get("판정"),
             "🔴 상수인가": r["자 B"].get("🔴 상수인가"),
             "🔴 서로 다른 값": r["자 B"].get("서로 다른 값"),
             "🔴 성공 호출": r["자 B"].get("성공 호출")} for r in site_a],
        "🔴 세 걸음을 다 적는다(중간 판도 상수였다)": (
            "① 행 목록을 받는 순수 함수로 뺐다 → 자 B 가 「상수 False — 모른다」로 옮겼을 뿐 "
            "**상수인 것은 그대로**였다. ② 정수 둘의 함수로 낮췄다 → `n_taut == 0` 이 "
            "생성기의 `randint(-999,999)` 아래에서 **1,999 번에 한 번**만 참이라 여전히 "
            "상수 False. ③ 허용값을 전역 `F1_ALLOWED_TAUT` 로 올려 `n_taut <= 허용` 으로 "
            "바꾸니 **떨어진다**(서로 다른 값 2)"),
        "🔴 빈 분모 fail-open 을 같이 닫았다": {
            "🔴 분모 0 · 항진 0 에서 옛 판": True,
            "🔴 분모 0 · 항진 0 에서 새 판": M.f1_verdict(0, 0)["통과"],
            "🔴 분모 29 · 항진 0 에서 새 판": M.f1_verdict(29, 0)["통과"],
            "🔴 분모 29 · 항진 1 에서 새 판": M.f1_verdict(29, 1)["통과"],
        },
        "🔴 `F1_ALLOWED_TAUT` 가 소스에 있나": bool("F1_ALLOWED_TAUT" in after),
        "🔴 고치기 전 소스에 있었나": bool("F1_ALLOWED_TAUT" in before),
        "통과": bool(len(taut_a) == 0 and len(taut_b) > 0),
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "🔴 **같은 자·같은 씨앗·같은 입력에서 고치기 전은 항진명제를 내고 고친 뒤는 0 이다**"),
    }

    # ── 수리 4 — `numaudit` 한글 수사 (양성 대조) ──────────────
    j977 = (ROOT / "docs/판정_977.md").read_text(encoding="utf-8")
    nu977 = _load("out977_numaudit.json")
    n_body_977 = nu977.get("🔴 분모: 대상 파일")
    kr_real = LG.audit_korean(j977, {"본문": n_body_977 or 5})
    #: 🔴 **음성 대조** — 같은 문서에서 그 수사를 참값으로 고친 **사본**
    fixed = j977.replace("본문 넷", "본문 다섯")
    kr_fixed = LG.audit_korean(fixed, {"본문": n_body_977 or 5})
    #: 🔴 **976·977 판(아라비아 숫자만)** 은 같은 자리를 못 본다
    old_sees = bool(LG.NUMPAT.search("본문 넷"))
    new_sees = bool(LG.KNUMPAT.search("본문 넷"))
    r4 = {
        "🔴 무엇": "977 의 「본문 넷」이 판정문·카드·원장 셋을 그대로 통과했다",
        "🔴 977 `numaudit` 이 적은 대상 파일 수(= 참값)": n_body_977,
        "🔴🔴 977 판정문에서 새 자가 잡은 어긋난 수사": kr_real["🔴🔴 등록된 참값과 다른 수사"],
        "🔴 그 자리": kr_real["🔴 어긋난 자리"],
        "🔴🔴 고친 사본에서 새 자가 잡은 수": kr_fixed["🔴🔴 등록된 참값과 다른 수사"],
        "🔴 센 한글 수사(977 판정문)": kr_real["🔴 센 한글 수사"],
        "🔴 수사별": dict(kr_real["수사별"]),
        "🔴🔴 976·977 판(`NUMPAT`)이 「본문 넷」을 보나": old_sees,
        "🔴🔴 978 판(`KNUMPAT`)이 「본문 넷」을 보나": new_sees,
        "🔴 등록한 수사 낱말": dict(LG.KOR_NUM),
        "통과": bool(kr_real["🔴🔴 등록된 참값과 다른 수사"] == 1
                   and kr_fixed["🔴🔴 등록된 참값과 다른 수사"] == 0
                   and (not old_sees) and new_sees),
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "🔴 **새 자는 977 이 놓친 그 자리를 잡고, 고친 사본에서는 안 짖는다** "
            "(양성 대조 + 음성 대조)"),
    }

    # ── 수리 5 — 배선 W 를 `select()` 밖으로 ──────────────────
    w = _load("out978_wiring.json")
    w977 = _load("out977_wiring.json")
    #: 🔴🔴 **반증조건 4 를 측정이 다 끝난 뒤에 다시 센다.** 배선의 W10 은 배선이
    #: **먼저** 도므로 그때 있던 파일만 본다 — 그것은 순서 때문에 생기는 구멍이다.
    #: 🔴 이 절은 `scorefix` 가 **마지막에** 돌면서 산출물 전량을 다시 읽는다.
    RULER_NAMES = ("R_pool 묶음", "R_eq 균등", "R_z 순열SE 역가중", "R_iv SE² 역가중")
    fc4 = collections.OrderedDict()
    n_all = n_ok4 = 0
    for p in sorted((ROOT / "runners").glob("out978_*.json")):
        if p.name in ("out978_slots.json", "out978_f5.json",
                      "out978_numaudit.json", "out978_control.json",
                      "out978_scorefix.json"):
            continue
        txt = p.read_text(encoding="utf-8")
        got = sum(1 for nm in RULER_NAMES if nm in txt)
        fc4[p.name] = "%d / %d" % (got, len(RULER_NAMES))
        n_all += 1
        n_ok4 += 1 if got == len(RULER_NAMES) else 0
    r5 = {
        "🔴🔴🔴 반증조건 4 — 자 넷이 격자 stage 밖에서도 다 나오나(측정 뒤 재채점)": {
            "산출물별": fc4,
            "🔴 분자/분모": "%d / %d" % (n_ok4, n_all),
            "🔴 왜 여기서 다시 세나": (
                "배선은 측정보다 **먼저** 도므로 W10 은 그때 있던 파일만 본다. "
                "이 절은 `scorefix` 가 **마지막에** 돌면서 전량을 다시 읽는다"),
            "통과": bool(n_all > 0 and n_ok4 == n_all),
        },
        "🔴 977 W 분자/분모": w977.get("🔴 W 분자/분모(통과)"),
        "🔴 977 구성상 참인 검사": w977.get("🔴🔴🔴 W 구성상 참인 검사 분자/분모"),
        "🔴 977 정직한 W": w977.get("🔴🔴 정직한 W 분자/분모(구성상 참을 뺀다)"),
        "🔴 978 W 분자/분모": w.get("🔴 W 분자/분모(통과)"),
        "🔴🔴 978 구성상 참인 검사": w.get("🔴🔴🔴 W 구성상 참인 검사 분자/분모"),
        "🔴🔴 978 정직한 W": w.get("🔴🔴 정직한 W 분자/분모(구성상 참을 뺀다)"),
        "🔴🔴 977 의 W 가 문 것": w.get("🔴 977 의 W 가 문 것"),
        "통과": bool(w.get("🔴 W 분자/분모(통과)") is not None),
        "🔴 이 절의 `통과` 가 뜻하는 것": "978 배선 산출물이 실제로 났다",
    }

    # ── 🔴 정정 다섯 (수리로 안 센다) ──────────────────────────
    g977 = _load("out977_grid.json")
    d977 = _load("out977_destroy.json")
    prereg977 = (ROOT / "docs/prereg_977_alpha.md").read_text(encoding="utf-8")
    m400 = re.search(r"이중 붓스트랩[^\n]*?(\d{3}) 뽑기", prereg977)
    sc976 = _load("out976_scaling.json")
    fold_rows = (sc976.get("🔴 사다리(밑판 P 구성 · 학습 행 수만 바꾼다)", {})
                 .get("전량", {}))
    bodies_977 = ["docs/판정_977.md", "docs/card_977.md", "docs/ledger_977.json",
                  "paper/steps/977_alpha/body.tex",
                  "paper/steps/977_alpha/meta.json"]
    hit37 = collections.OrderedDict()
    for rel in bodies_977:
        p = ROOT / rel
        txt = p.read_text(encoding="utf-8") if p.is_file() else ""
        hit37[rel] = sum(txt.count(z) for z in ("37,535", "37535", "37,531", "37531"))
    #: 🔴 **977 이 커밋한 판**에서 읽는다 — 978 이 이 파일을 고쳐도 「고치기 전」이 안 흔들린다.
    _mb = _blob(BEFORE_REF, "paper/steps/977_alpha/meta.json")
    meta977 = json.loads(_mb) if _mb else {}
    meta977_disk = _load(str(ROOT / "paper/steps/977_alpha/meta.json"))
    claims = meta977.get("claims") or []
    corr = collections.OrderedDict()
    corr["정정 1 — 「본문 넷」 → 「다섯」"] = {
        "🔴 977 이 적은 말": "본문 넷",
        "🔴 `numaudit` 의 참값(대상 파일 수)": n_body_977,
        "🔴 파일별 센 수": {k: v.get("🔴 센 수(면제 뺀)")
                      for k, v in (nu977.get("파일별") or {}).items()},
        "🔴 그 합": sum(v.get("🔴 센 수(면제 뺀)", 0)
                     for v in (nu977.get("파일별") or {}).values()),
        "🔴 977 이 적은 분모": nu977.get("🔴🔴🔴 976 판 분자/분모(본문이 출처를 못 대는 수 / 센 수)"),
        "통과": bool(n_body_977 == 5),
        "🔴 이 절의 `통과` 가 뜻하는 것": "🔴 **참값은 다섯이다**",
    }
    corr["정정 2 — 붓스트랩 400 → 200 신고"] = {
        "🔴 977 사전등록 §3 이 적은 뽑기": int(m400.group(1)) if m400 else None,
        "🔴 977 코드·산출물이 쓴 뽑기(격자)": g977.get("붓스트랩 뽑기"),
        "🔴 977 코드·산출물이 쓴 뽑기(파괴)": d977.get("붓스트랩 뽑기"),
        "🔴 977 이 그 차이를 어디엔가 적었나": bool(
            re.search(r"200", prereg977) and re.search(r"뽑기.*200", prereg977)),
        "🔴🔴 그 SE 위에 선 판정": "977 의 모든 문턱 판정(채택 2/12 · D4 문턱 · LOSO)",
        "🔴 978 이 쓴 뽑기": 400,
        "통과": bool(m400 and g977.get("붓스트랩 뽑기") != int(m400.group(1))),
        "🔴 이 절의 `통과` 가 뜻하는 것": "🔴 **등록값과 실제가 갈렸음을 산출물이 스스로 적는다**",
    }
    corr["정정 3 — 976 밑판 P 학습 행 수 두 값"] = {
        "🔴 두 값": [37535, 37531],
        "🔴 977 사전등록 §11-4 가 등록했나": bool("37,535" in prereg977),
        "🔴🔴 977 의 다섯 본문에서 나온 횟수": hit37,
        "🔴🔴 그 합": sum(hit37.values()),
        "🔴🔴🔴 왜 두 값인가(976 산출물에서 읽는다)": {
            "겹별 학습 행": fold_rows.get("겹별 학습 행"),
            "겹 평균": fold_rows.get("실제 학습 행(겹 평균)"),
            "🔴 37,535 는": "겹 0 의 학습 행 수",
            "🔴 37,531 은": "다섯 겹의 평균",
        },
        "통과": bool(sum(hit37.values()) == 0),
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "🔴 **977 이 등록해 놓고 본문 다섯 어디에도 안 적었다** — 여기서 게재한다"),
    }
    corr["정정 4 — 논문 `meta.json` 의 `sent`"] = {
        "🔴 저장소가 적은 값": meta977.get("sent"),
        "🔴 그 값을 어디서 읽었나": "%s:paper/steps/977_alpha/meta.json" % BEFORE_REF,
        "🔴 978 이 고친 뒤 디스크 값": meta977_disk.get("sent"),
        "🔴 실제로 나갔나": True,
        "🔴 왜 갈렸나": ("`paper.harness send` 가 `meta.json` 을 통째로 다시 쓰면서 "
                    "슬롯 오프셋을 밀어서, 977 은 **채점된 판을 커밋하고 send 가 덧쓴 "
                    "판은 안 커밋했다**"),
        "🔴 978 이 하는 일": "send 뒤 다시 채점하고 **그 판을 커밋한다**",
        "통과": bool(meta977.get("sent") is False),
        "🔴 이 절의 `통과` 가 뜻하는 것": "🔴 **어긋남이 실제로 저장소에 있다**",
    }
    claim7 = claims[6] if len(claims) >= 7 else ""
    corr["정정 5 — 논문 claim #7 철회"] = {
        "🔴 977 의 claim #7": claim7,
        "🔴 977 판정문이 같은 자리에 적은 말": (
            "자기 표준오차의 두 배를 못 넘는다"
            if "표준오차" in j977 or "SE" in j977 else "확인 못 함"),
        "🔴 그 Δ 와 SE": {
            "Δ": (d977.get("🔴🔴🔴 판정 — 90 행이 1,710 행보다 자를 더 움직이나", {})
                  .get("u=3", {}).get("🔴 균등 자 D4 Δ")),
            "SE": (d977.get("🔴🔴🔴 판정 — 90 행이 1,710 행보다 자를 더 움직이나", {})
                   .get("u=3", {}).get("🔴 균등 자 D4 SE")),
            "🔴 문턱 둘을 넘나": (
                d977.get("🔴🔴🔴 판정 — 90 행이 1,710 행보다 자를 더 움직이나", {})
                .get("u=3", {}).get("🔴🔴 균등 자 D4 가 문턱 둘을 넘나")),
        },
        "🔴 철회 문구": ("「제대로 내려간다」를 철회한다. 참인 문장은 "
                    "「부호는 음수이나 자기 표준오차의 두 배를 못 넘는다」까지다"),
        "통과": bool("제대로 내려간다" in claim7),
        "🔴 이 절의 `통과` 가 뜻하는 것": "🔴 **철회 대상 문장이 실제로 논문에 있다**",
    }

    out = collections.OrderedDict()
    out["무엇"] = "978 — 수리 다섯(사전등록 §8)과 정정 다섯(§9)의 증거"
    out["🔴 축"] = "자기 자(수리 레인)"
    out["🔴 노트 번호"] = 978
    out["🔴🔴🔴 수리 1 — `--passkey` 축을 V2·V3 에"] = r1
    out["🔴🔴🔴 수리 2 — 심기를 ≥1,000 줄 파일에"] = r2
    out["🔴🔴🔴 수리 3 — `meta965.py:1385`(일곱 사이클째)"] = r3
    out["🔴🔴🔴 수리 4 — `numaudit` 에 한글 수사"] = r4
    out["🔴🔴 수리 5 — 배선 W 를 `select()` 밖으로"] = r5
    out["🔴 수리 계수(부풀리지 않는다)"] = {
        "🔴 이 사이클의 수리": REPAIRS,
        "🔴 분자/분모": "%d / %d" % (len(REPAIRS), 5),
        "🔴 묶었나": False,
        "🔴 상한을 넘었나": bool(len(REPAIRS) > 5),
        "통과": bool(len(REPAIRS) <= 5),
    }
    out["🔴🔴🔴 정정 다섯(수리로 안 센다)"] = corr
    out["🔴 정정 계수"] = {
        "🔴 이 사이클의 정정": CORRECTIONS,
        "🔴 정정 수": len(CORRECTIONS),
        "🔴 정정을 수리로 세면": len(REPAIRS) + len(CORRECTIONS),
        "🔴 갈라 놓은 자리": "docs/prereg_978_ruler.md §8(수리) / §9(정정) — 측정 전 단독 커밋",
        "🔴 게재한 정정 분자/분모": "%d / %d" % (
            sum(1 for v in corr.values() if v.get("통과")), len(corr)),
    }
    out["🔴 이 사이클이 **안 한** 수리"] = [
        "🔴 **HPLT 464 shard 중 여덟만 읽은 것은 973 그대로다** — 늘리지 않았다.",
        "🔴 **개체 키 복제(제목 하나에 키 둘)를 안 고쳤다** — 974 부터 그대로다.",
        "🔴 **개체 묶음 OOF 가 시간 방향을 안 본다** — 티처 #115 중대 지적이고 이 사이클도 0.",
        "🔴 **`⑤′ 취합 검사`** — 열두 사이클째.",
    ]
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out978_scorefix.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["fix"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_fix(a.ref)
    print(json.dumps({k: v for k, v in r.items()
                      if not str(k).startswith("🔴🔴🔴")},
                     ensure_ascii=False, indent=1, default=str)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
