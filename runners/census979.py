#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""979 — 🔴 **수리 3 의 검정력**: 항진명제 census 를 `통과` 키 **밖으로** 넓혔다.

노트 978 은 「🔴 유보는 한 줄도 안 만졌다」를 `ruler978.py:444·792·878` 에서
**리터럴 `= True`** 로 적었다. 🔴 그 셋은 **키에 「통과」라는 글자가 없어서**
옛 census 가 **원리상 못 봤다**(티처 #117 치-7).

이 러너는 셋을 나란히 낸다:
  ① `meta965.passkey_census` — `통과` 키 세 갈래(정확·접미·포함)
  ② 🔴 `meta965.literal_claim_census`(979 신설) — **키 이름을 안 본다**
  ③ 세 축 12 칸 전수(`scorefix978.census_axes` 를 979 파일에 건다)

씀:
    python3 runners/census979.py --stage census --ref <40자 sha>
"""
import argparse
import ast
import collections
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                               # noqa: E402
import meta965 as M                               # noqa: E402
import scorefix978 as S8                          # noqa: E402

RAN = ("runners/census979.py", "runners/meta965.py", "runners/ledger.py",
       "runners/predict971.py")
OUT = ROOT / "runners"

MINE = ("runners/ruler979.py", "runners/house979.py", "runners/note979_gen.py",
        "runners/census979.py")
CENSUS_FILES = MINE + ("runners/ledger.py", "runners/meta965.py")
#: 🔴 **검정력 대조** — 옛 census 가 못 본 그 파일에 새 자를 건다.
POWER_FILES = ("runners/ruler978.py",)
KNOWN = (444, 792, 878)


def stage_census(ref):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = LG.code_stamp(RAN)
    out = collections.OrderedDict()
    out["무엇"] = ("979 §4 수리 3 — 🔴 **항진명제 census 를 `통과` 키 밖으로**. "
                 "옛 census 가 원리상 못 보던 리터럴 참 주장을 센다")
    out["🔴 축"] = "자기 자(수리 레인)"

    # ── ① 검정력 — 노트 978 러너의 세 자리를 잡나 ──────────────
    pw = collections.OrderedDict()
    for rel in POWER_FILES:
        src = (ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        old = M.passkey_census(rel, tree)
        new = M.literal_claim_census(rel, tree)
        lines = [int(x.split(":")[1].split(" ")[0]) for x in new["🔴 그 자리 목록"]]
        hit = [n for n in KNOWN if n in lines]
        pw[rel] = collections.OrderedDict([
            ("🔴 옛 census — `통과` 키 분모(정확/접미/포함)",
             [old["🔴 분모(정확 일치 · 965 판)"], old["🔴 분모(접미 일치 · 971 판)"],
              old["🔴 분모(포함 일치 · 975 판)"]]),
            ("🔴🔴 새 census — 키 이름을 안 본 리터럴 참 자리", new[
                "🔴🔴🔴 그중 값이 리터럴 `True` 인 자리(= 근거 없는 주장 후보)"]),
            ("🔴🔴 그중 조건 가지 밖(무조건 참)", new[
                "🔴🔴🔴 그중 **조건 가지 밖**(무조건 참) 자리"]),
            ("🔴 그 자리 목록", new["🔴 그 자리 목록"]),
            ("🔴🔴🔴 티처 #117 이 지목한 세 줄을 잡나",
             "%d / %d" % (len(hit), len(KNOWN))),
            ("🔴 지목된 줄", list(KNOWN)),
            ("🔴 잡은 줄", hit),
            ("🔴🔴 옛 자가 그 셋을 볼 수 있었나", False),
            ("🔴 왜", "그 셋의 키는 「🔴 유보는 한 줄도 안 만졌다」다 — "
                   "「통과」라는 글자가 없어서 세 갈래 전부 원리상 못 본다"),
        ])
    out["🔴🔴🔴 수리 3 의 검정력 — 노트 978 러너에 새 자를 건다"] = collections.OrderedDict(
        list(pw.items()) + [
            ("통과", bool(all(v["🔴🔴🔴 티처 #117 이 지목한 세 줄을 잡나"]
                            == "%d / %d" % (len(KNOWN), len(KNOWN))
                            for v in pw.values()))),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **새 자가 지목된 세 줄을 전부 잡는다** = 수리 3 이 실물이다")])

    # ── ② 이 사이클 러너 전량 ────────────────────────────────
    mine = collections.OrderedDict()
    n_lit = n_pass = n_uncond = 0
    for rel in CENSUS_FILES:
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        new = M.literal_claim_census(rel, tree)
        old = M.passkey_census(rel, tree)
        mine[rel] = collections.OrderedDict([
            ("🔴 리터럴 참 자리(`통과` 키 밖)", new[
                "🔴🔴🔴 그중 값이 리터럴 `True` 인 자리(= 근거 없는 주장 후보)"]),
            ("🔴🔴 그중 조건 가지 밖(무조건 참)", new[
                "🔴🔴🔴 그중 **조건 가지 밖**(무조건 참) 자리"]),
            ("🔴 조건 가지 안(가지가 자다)", new["🔴 그중 조건 가지 안(가지가 자다) 자리"]),
            ("🔴 무조건 참 자리 목록", new["🔴 무조건 참 자리 목록"]),
            ("🔴 `통과` 키 분모(포함 일치)", old["🔴 분모(포함 일치 · 975 판)"]),
        ])
        n_uncond += new["🔴🔴🔴 그중 **조건 가지 밖**(무조건 참) 자리"]
        n_lit += new["🔴🔴🔴 그중 값이 리터럴 `True` 인 자리(= 근거 없는 주장 후보)"]
        n_pass += old["🔴 분모(포함 일치 · 975 판)"]
    out["🔴🔴🔴 이 사이클 러너 — 리터럴 참 주장 census"] = collections.OrderedDict([
        ("파일별", mine),
        ("🔴 분모: 훑은 파일", len(CENSUS_FILES)),
        ("🔴🔴 리터럴 참 자리 합(`통과` 키 밖)", n_lit),
        ("🔴🔴🔴 그중 조건 가지 밖(무조건 참) 합", n_uncond),
        ("🔴 `통과` 키 자리 합(포함 일치)", n_pass),
        ("🔴🔴 자기 적발", "🔴 **이 사이클 러너에도 리터럴 참 주장이 남아 있다.** "
                      "🔴 **분모를 안 줄이고 그대로 적는다** — 조건 가지 안과 밖을 "
                      "갈라서 둘 다 센다(조항 60)"),
        ("통과", bool(n_uncond == 0 and n_pass > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **이 사이클 러너에 「조건 가지 밖의 무조건 참 주장」이 없다.** "
         "🔴 분모가 0 이면 실패다"),
    ])

    # ── ③ 세 축 12 칸 전수 ───────────────────────────────────
    out["🔴🔴🔴 세 축 12 칸 전수(항진명제 census)"] = S8.census_axes(CENSUS_FILES)

    out["통과"] = bool(
        out["🔴🔴🔴 수리 3 의 검정력 — 노트 978 러너에 새 자를 건다"]["통과"]
        and out["🔴🔴🔴 이 사이클 러너 — 리터럴 참 주장 census"]["통과"]
        and out["🔴🔴🔴 세 축 12 칸 전수(항진명제 census)"]["통과"])
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = "세 절이 다 초록이다"
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out979_census.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["census"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_census(a.ref)
    print(json.dumps({k: v for k, v in r.items()
                      if not str(k).startswith("🔴🔴🔴")},
                     ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
