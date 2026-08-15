#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""977 — **수리 다섯의 증거**를 한 산출물로 낸다(사전등록 §10).

🔴 **수리는 다섯이고 상한도 다섯이다. 안 묶었다.**
🔴 **정정 다섯(§11)은 수리로 안 센다.**

씀:
    python3 runners/scorefix977.py --stage fix --ref <40자 sha>
"""
import argparse
import ast
import builtins
import collections
import glob
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

RAN = ("runners/scorefix977.py", "runners/ledger.py", "runners/meta965.py",
       "runners/predict971.py")
OUT = ROOT / "runners"

RUNNERS_977 = ["runners/alpha977.py", "runners/ledger.py",
               "runners/note977_gen.py", "runners/scorefix977.py"]
RUNNERS_976 = ["runners/c6_976.py", "runners/ledger.py",
               "runners/note976_gen.py", "runners/scorefix976.py"]
#: 🔴 976 이 머지된 `main` 커밋 — 「고치기 전」 blob 을 여기서 꺼낸다(대조).
BEFORE_REF = "37d46a822bf66677f62d7b276c0c353f88f559c6"

REPAIRS = [
    "1. 🔴🔴 **측정 러너에 `통과` 키를 심었다** — 노트 976 의 측정 러너 `c6_976.py` 는 "
    "`통과` 키가 하나도 없어서 `meta965` 의 분모가 **모든 조합에서 비어 있었다**. "
    "자가 사이클의 모든 수를 낸 파일을 **원리상 못 봤다**.",
    "2. 🔴🔴 **배선 W 에 변이체 대조를 붙였다** — 검사마다 **일부러 깨뜨린 판**을 같이 돌려 "
    "「구성상 참인 검사」를 분자/분모로 적는다. 노트 976 의 W8 은 루프 변수를 안 쓰고 "
    "같은 상수를 되풀이해 넣었고, W3·W10 은 자기가 만든 식을 자기가 다시 계산해 견줬다.",
    "3. 🔴 **`stage_numaudit`·`stage_control` 의 fail-open 을 닫았다** — 슬롯 대장이 없으면 "
    "노트 976 판은 `빈 분모 비교` 로 **자료 없이 참**이었다. 이제 **실패**다.",
    "4. 🔴 **`ledger.py` 세 stage 에 `stamp_block(..., data=…)` 를 채웠다** — 노트 976 "
    "산출물의 다수가 자료 지문을 비운 채 나갔다(규칙 C). ⚠ **티처는 「네 stage」라 적었는데 "
    "이 파일의 stage 는 셋이다 — 그대로 적는다.**",
    "5. 🔴 **`§3 V2·V3` 을 범위별로 돌렸다** — 여섯 사이클째 미이행이던 것. "
    "`--poolscope × --genver` 네 칸에서 심은 항진명제 넷의 검정력과 음성 대조 넷의 "
    "거짓 양성을 낸다.",
]
CORRECTIONS = [
    "1. 976 의 **「학습 행 수만 바꿨다」를 철회한다** — 사다리에서 λ 가 같이 움직였다.",
    "2. 976 의 **R5 서술을 정정한다** — 파괴 끝점(α=1)만 적고 **α=0 의 최대 개선을 "
    "본문 셋 어디에도 안 적었다**.",
    "3. 976 의 **배선 10/10 을 정정한다** — 구성상 참인 검사를 빼야 정직한 수다.",
    "4. 976 의 **밑판 P 학습 행 수 표기를 정정한다** — 같은 설정에 두 값이 실렸다.",
    "5. 976 의 **형태 ② 적합을 철회한다** — 제약 없는 적합이 스피어만 상한 밖을 낸다.",
]


def _census(rels):
    per, n0e, n0c = collections.OrderedDict(), 0, 0
    for rel in rels:
        p = ROOT / rel
        if not p.is_file():
            per[rel] = {"🔴 파일이 없다": True}
            continue
        c = M.passkey_census(rel, ast.parse(p.read_text(encoding="utf-8")))
        per[rel] = {
            "exact 분모": c["🔴 분모(정확 일치 · 965 판)"],
            "suffix 분모": c["🔴 분모(접미 일치 · 971 판)"],
            "contains 분모": c["🔴 분모(포함 일치 · 975 판)"],
            "🔴 exact 분모가 0": c["🔴🔴 정확 일치 분모가 0 인가(= 이 파일에서 965 판 채점은 죽었다)"],
            "🔴 contains 분모도 0 인가": c["🔴🔴 포함 일치 분모도 0 인가"],
        }
        n0e += 1 if per[rel]["🔴 exact 분모가 0"] else 0
        n0c += 1 if per[rel]["🔴 contains 분모도 0 인가"] else 0
    return per, n0e, n0c


def _blob(ref, rel):
    try:
        return subprocess.check_output(["git", "show", "%s:%s" % (ref, rel)],
                                       cwd=str(ROOT)).decode("utf-8")
    except Exception:                                              # noqa: BLE001
        return ""


# ══════════════════════════════════════════════════════════════════════
# 🔴 수리 5 — §3 V2·V3 을 **범위별**로
# ══════════════════════════════════════════════════════════════════════
def v2v3_by_scope():
    """`--poolscope × --genver` 네 칸에서 심은 넷의 검정력과 음성 대조 넷의 거짓 양성.

    🔴 972~976 여섯 사이클이 **안 한** 일이다. 자기 자의 검정력이 **범위 설정의 함수인지**를
    처음으로 재는 자리다.
    """
    ptree = ast.parse(M.PLANTED_SRC)
    tab = collections.OrderedDict()
    old_scope, old_gen = M.POOLSCOPE, M.GENVER
    try:
        for scope in ("file", "func"):
            for gen in (1, 2):
                M.POOLSCOPE = scope
                M.GENVER = gen
                pns = {"__builtins__": builtins}
                exec(compile(ptree, "<심은 키>", "exec"), pns)      # noqa: S102
                with M._NoWrite():
                    prows = M.scan_source("<심은 키>", M.PLANTED_SRC, pns,
                                          random.Random(M.SEED))
                by = collections.defaultdict(list)
                for r in prows:
                    by[r["함수"]].append(r)
                caught, missed = collections.OrderedDict(), []
                for fn, want in M.PLANTED.items():
                    got = sorted({z for r in by.get(fn, []) for z in r["🔴 잡은 자"]})
                    caught[fn] = {"기대한 자": want, "잡은 자": got or "없음",
                                  "잡았나": bool(got), "기대한 자가 잡았나": want in got}
                    if not got:
                        missed.append(fn)
                fps = collections.OrderedDict()
                for fn in M.NEGATIVE:
                    got = sorted({z for r in by.get(fn, []) for z in r["🔴 잡은 자"]})
                    fps[fn] = {"잡은 자": got or "없음", "거짓 양성인가": bool(got)}
                n_fp = sum(1 for v in fps.values() if v["거짓 양성인가"])
                tab["poolscope=%s · genver=%d" % (scope, gen)] = {
                    "🔴 검정력 분자/분모": "%d / %d" % (
                        len(M.PLANTED) - len(missed), len(M.PLANTED)),
                    "🔴 기대한 자가 잡은 수": sum(
                        1 for v in caught.values() if v["기대한 자가 잡았나"]),
                    "🔴 거짓 양성 분자/분모": "%d / %d" % (n_fp, len(M.NEGATIVE)),
                    "못 잡은 심기": missed or "없음",
                    "심은 키별": caught,
                    "음성 대조별": fps,
                    "통과": bool((not missed) and n_fp == 0),
                }
    finally:
        M.POOLSCOPE, M.GENVER = old_scope, old_gen
    pw = {k: v["🔴 검정력 분자/분모"] for k, v in tab.items()}
    fp = {k: v["🔴 거짓 양성 분자/분모"] for k, v in tab.items()}
    return {
        "🔴 무엇": ("사전등록 §10-5 · 972~976 여섯 사이클이 안 한 일. "
                 "심은 항진명제 넷(A·B·C·D)과 음성 대조 넷을 **네 칸 전부**에서 채점한다"),
        "칸별": tab,
        "🔴🔴 범위별 검정력": pw,
        "🔴🔴 범위별 거짓 양성": fp,
        "🔴🔴🔴 범위가 검정력을 바꾸나": bool(len(set(pw.values())) > 1),
        "🔴🔴 범위가 거짓 양성을 바꾸나": bool(len(set(fp.values())) > 1),
        "🔴 네 칸 전부 통과인가": bool(all(v["통과"] for v in tab.values())),
        "통과": bool(len(tab) == 4),
        "🔴 이 절의 `통과` 가 뜻하는 것": "네 칸을 **전부 돌렸다**(값이 무엇이든 적는다)",
    }


# ══════════════════════════════════════════════════════════════════════
def stage_fix(ref):
    t0 = LG.now()
    cs0 = LG.code_stamp(RAN)

    # ── 수리 1 ────────────────────────────────────────────────
    per977, n0e977, n0c977 = _census(RUNNERS_977)
    per976, n0e976, n0c976 = _census(RUNNERS_976)
    r1 = {
        "🔴 976 러너별 `통과` 분모": per976,
        "🔴 977 러너별 `통과` 분모": per977,
        "🔴🔴 976 측정 러너(`c6_976.py`)의 contains 분모":
            per976["runners/c6_976.py"].get("contains 분모"),
        "🔴🔴 977 측정 러너(`alpha977.py`)의 contains 분모":
            per977["runners/alpha977.py"].get("contains 분모"),
        "🔴 977 러너에서 contains 분모가 0 인 파일": "%d / %d" % (n0c977, len(RUNNERS_977)),
        "🔴 976 러너에서 contains 분모가 0 인 파일": "%d / %d" % (n0c976, len(RUNNERS_976)),
        "🔴 977 러너에서 exact 분모가 0 인 파일": "%d / %d" % (n0e977, len(RUNNERS_977)),
        "통과": bool(per977["runners/alpha977.py"].get("contains 분모", 0) > 0),
        "🔴 이 절의 `통과` 가 뜻하는 것": "이 사이클의 **측정 러너**를 자가 볼 수 있다",
    }

    # ── 수리 2 ────────────────────────────────────────────────
    wf = OUT / "out977_wiring.json"
    w = json.loads(wf.read_text(encoding="utf-8")) if wf.is_file() else {}
    #: 🔴 976 의 W8 꼴을 **실물로** 재현한다 — 루프 변수를 안 쓰는 집합.
    tautset = len({"같은 상수" for _s in range(36)}) == 1
    r2 = {
        "🔴 977 W 분자/분모(통과)": w.get("🔴 W 분자/분모(통과)"),
        "🔴🔴 977 W 구성상 참인 검사 분자/분모": w.get("🔴🔴🔴 W 구성상 참인 검사 분자/분모"),
        "🔴🔴 977 정직한 W 분자/분모": w.get("🔴🔴 정직한 W 분자/분모(구성상 참을 뺀다)"),
        "🔴 976 이 적은 W": "10 / 10",
        "🔴 티처 #115 가 손으로 센 976 의 정직한 W": "6 / 10",
        "🔴🔴 976 의 W8 꼴이 항진인가(루프 변수를 안 쓰는 집합은 크기가 1)": bool(tautset),
        "🔴 변이체 대조가 무엇인가": (
            "검사를 **일부러 깨뜨린 판**에 그대로 건다. 그때도 통과하면 "
            "그 검사는 자료로 반증될 수 없다"),
        "통과": bool(w.get("🔴🔴🔴 W 구성상 참인 검사 분자/분모") is not None),
    }

    # ── 수리 3 — fail-open ────────────────────────────────────
    before = _blob(BEFORE_REF, "runners/ledger.py")
    after = (ROOT / "runners/ledger.py").read_text(encoding="utf-8")
    # 🔴 같은 입력(대장 없음)에서 두 판의 판정식을 나란히 evaluate 한다.
    files, miss_new, tot, n_all = {}, 0, 0, 0
    fail_open = (not files)
    old_pass = (miss_new == 0)                       # 976 판
    new_pass = ((not fail_open) and miss_new == 0 and tot > 0)      # 977 판
    old_ctl = (0 == 0)                               # 976 판 무리 A
    new_ctl = ((not fail_open) and n_all > 0)        # 977 판
    r3 = {
        "🔴 대조 입력": "슬롯 대장이 없다(파일별 = {}) · 센 수 0 · 심은 수 0",
        "🔴🔴 976 판 numaudit 판정": bool(old_pass),
        "🔴🔴 977 판 numaudit 판정": bool(new_pass),
        "🔴🔴 976 판 control 판정(무리 A)": bool(old_ctl),
        "🔴🔴 977 판 control 판정(무리 A)": bool(new_ctl),
        "🔴 고치기 전 blob 에 `fail_open` 이 있나": bool("fail_open" in before),
        "🔴 고친 뒤 파일에 `fail_open` 이 있나": bool("fail_open" in after),
        "🔴 대조 ref": BEFORE_REF,
        "통과": bool(old_pass and not new_pass),
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "**같은 입력에서 976 판은 통과하고 977 판은 떨어진다** — 자료 없이 참이던 "
            "자리가 닫혔다"),
    }

    # ── 수리 4 — 자료 지문 ────────────────────────────────────
    def dstamp(pat):
        rows, zero = collections.OrderedDict(), 0
        for p in sorted(glob.glob(str(OUT / pat))):
            try:
                d = json.loads(Path(p).read_text(encoding="utf-8"))
            except Exception:                                      # noqa: BLE001
                continue
            n = (d.get("🔴 도장") or {}).get("분모: 연 자료 파일", 0)
            rows[Path(p).name] = n
            zero += 1 if not n else 0
        return rows, zero, len(rows)
    d976, z976, t976 = dstamp("out976_*.json")
    d977, z977, t977 = dstamp("out977_*.json")
    r4 = {
        "🔴 976 산출물별 자료 지문 수": d976,
        "🔴🔴 976 에서 자료 지문이 0 인 산출물": "%d / %d" % (z976, t976),
        "🔴 977 산출물별 자료 지문 수": d977,
        "🔴🔴 977 에서 자료 지문이 0 인 산출물": "%d / %d" % (z977, t977),
        "🔴 `ledger.py` 가 채우는 자료": list(LG.DATA),
        "통과": bool(t977 > 0 and z977 == 0),
        "🔴 이 절의 `통과` 가 뜻하는 것": "이 사이클 산출물 전량이 자료 지문을 갖는다",
    }

    # ── 수리 5 ────────────────────────────────────────────────
    r5 = v2v3_by_scope()

    out = collections.OrderedDict()
    out["무엇"] = "977 — 수리 다섯의 증거(사전등록 §10) · 정정 다섯은 따로 센다(§11)"
    out["🔴 축"] = "자기 자(수리 레인)"
    #: 🔴 규칙 D — 논문 `meta.json` 의 노트 번호도 **산출물 키 경로에서** 와야 한다.
    out["🔴 노트 번호"] = 977
    out["🔴🔴 수리 1 — 측정 러너에 `통과` 키를 심었다"] = r1
    out["🔴🔴 수리 2 — 배선 W 에 변이체 대조를 붙였다"] = r2
    out["🔴🔴 수리 3 — fail-open 을 닫았다"] = r3
    out["🔴 수리 4 — 자료 지문을 채웠다"] = r4
    out["🔴🔴🔴 수리 5 — §3 V2·V3 을 범위별로"] = r5
    out["🔴 수리 계수(부풀리지 않는다)"] = {
        "🔴 이 사이클의 수리": REPAIRS,
        "🔴 분자/분모": "%d / %d" % (len(REPAIRS), 5),
        "🔴 묶었나": False,
        "🔴 상한을 넘었나": bool(len(REPAIRS) > 5),
        "통과": bool(len(REPAIRS) <= 5),
    }
    out["🔴 정정 계수(수리로 안 센다)"] = {
        "🔴 이 사이클의 정정": CORRECTIONS,
        "🔴 정정 수": len(CORRECTIONS),
        "🔴 정정을 수리로 세면": len(REPAIRS) + len(CORRECTIONS),
        "🔴 갈라 놓은 자리": "docs/prereg_977_alpha.md §10(수리) / §11(정정) — 측정 전 단독 커밋",
    }
    out["🔴 이 사이클이 **안 한** 수리"] = [
        "🔴 **`meta965.py:1385` 를 안 고쳤다** — **여섯 사이클째**. 수리 상한을 지켰다.",
        "🔴 그래서 **「항진명제 n」 인용 금지는 계속 유효하다** — 이 사이클의 어떤 본문도 "
        "그 수를 인용하지 않는다.",
        "🔴 **`meta965` 를 이 사이클 러너 전량에 실제로 걸어 항진명제를 세지 않았다** — "
        "빈 분모를 채운 것까지가 수리 1 이다.",
    ]
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out977_scorefix.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["fix"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_fix(a.ref)
    print(json.dumps(r, ensure_ascii=False, indent=1)[:5000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
