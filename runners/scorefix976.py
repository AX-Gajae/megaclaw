#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""976 — **수리 다섯의 증거**를 한 산출물로 낸다(사전등록 §10).

🔴 **수리는 다섯이고 상한도 다섯이다. 안 묶었다.**
🔴 **정정 다섯(§9)은 수리로 안 센다** — 975 가 측정 전에 갈라 놓아 티처 #114 가 정당하다고
   판정했다. 그 꼴을 따른다.

씀:
    python3 runners/scorefix976.py --stage fix --ref <40자 sha>
"""
import argparse
import ast
import collections
import glob
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                               # noqa: E402
import meta965 as M                               # noqa: E402

RAN = ("runners/scorefix976.py", "runners/ledger.py", "runners/meta965.py",
       "runners/predict971.py")
OUT = ROOT / "runners"

RUNNERS_976 = ["runners/c6_976.py", "runners/ledger.py",
               "runners/note976_gen.py", "runners/scorefix976.py"]
RUNNERS_975 = ["runners/c4_975.py", "runners/ledger975.py",
               "runners/note975_gen.py", "runners/precfix975.py",
               "runners/scorefix975.py"]

REPAIRS = [
    "1. 🔴 **채점기를 일회용 파일에서 꺼냈다** — 공유 `runners/ledger.py` 하나로. "
    "노트 976 은 `ledger976.py` 를 만들지 않았다.",
    "2. 🔴🔴 **슬롯 검사가 문서 본문을 읽는다** — 노트 975 판은 매니페스트 값과 키 경로 "
    "값을 견주어 `txt == txt` 였다(항진명제).",
    "3. 🔴 **양성 대조를 진짜로 심었다** — 무리 A(슬롯 안)·B(슬롯 밖)·C(면제 자리).",
    "4. 🔴 **`ALLOW_CTX` 를 줄이고 「안 세는 자리」를 판정문에 명시한다** — "
    "`맨-9xx` 규칙을 지웠다(그 규칙이 `1,000 중 901` 을 면제했다).",
    "5. 🔴 **`meta965 --passkey` 기본값을 `exact` → `contains` 로 올렸다** — "
    "기본값 `exact` 에서 노트 975 자신의 러너가 전부 분모 영이었다.",
]
CORRECTIONS = [
    "1. 노트 975 의 **요인 순위(스팬 내림차순)를 철회한다** — 스팬은 수준 수에 단조다.",
    "2. 노트 975 의 **「요인 하나만 흔들었나」는 설정 사전에서만 참**이었다 — "
    "자료 지문으로 다시 셌다.",
    "3. 노트 975 의 **SE 는 정본 자 요건 ② 가 아니다** — 이중 붓스트랩으로 갈아 끼웠다.",
    "4. **「노트 975 판이 `525 → 524` 를 잡는다」는 항진명제였다** — 심어서 다시 쟀다.",
    "5. 노트 975 의 **밑판이 생산 설정이 아니었다**(λ 를 하나로 얼렸다) — 속겹 CV 로 갈아 끼웠다.",
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
            "🔴 exact 분모가 0(= 965 판 채점이 죽었다)":
                c["🔴🔴 정확 일치 분모가 0 인가(= 이 파일에서 965 판 채점은 죽었다)"],
            "🔴 contains 분모도 0 인가": c["🔴🔴 포함 일치 분모도 0 인가"],
        }
        n0e += 1 if per[rel]["🔴 exact 분모가 0(= 965 판 채점이 죽었다)"] else 0
        n0c += 1 if per[rel]["🔴 contains 분모도 0 인가"] else 0
    return per, n0e, n0c


def stage_fix(ref):
    t0 = LG.now()
    cs0 = LG.code_stamp(RAN)

    # ── 수리 1 ────────────────────────────────────────────────
    disp = sorted(Path(p).name for p in glob.glob(str(OUT / "ledger[0-9][0-9][0-9].py")))
    r1 = {
        "🔴 일회용 채점기(`runners/ledgerNNN.py`)": disp,
        "🔴 분모: 일회용 벌 수": len(disp),
        "🔴 공유 파일": "runners/ledger.py",
        "🔴 976 이 만든 일회용 채점기": (
            1 if (OUT / "ledger976.py").is_file() else 0),
        "🔴 976 산출물이 실제로 부르는 채점기": "runners/ledger.py",
        "🔴 뜻": ("수리가 일회용 파일에 살면 대물림이 안 된다 — "
               "티처 #114 실측 공유 코드 착지 3/5"),
    }

    # ── 수리 2 — 항진명제를 실물로 보인다 ────────────────────────
    path = ["out976_factors.json", "🔴 자료", "base 행(= 유보 전량)"]
    val, err = LG.resolve(path)
    txt = LG.render(val) if err is None else "?"
    pre, post = "유보 행은 ", " 이다.\n"
    bad = LG._bump_last_digit(txt) or txt
    slots = [{"키 경로": path, "값": txt,
              "시작": len(pre), "끝": len(pre) + len(txt)}]
    src_ok = pre + txt + post
    src_bad = pre + bad + post
    S = LG.artifact_numbers("out976_*.json")
    a_ok = LG.audit_text(src_ok, slots, S)
    a_bad = LG.audit_text(src_bad, slots, S)
    b_ok = LG.audit_975(src_ok, slots, S)
    b_bad = LG.audit_975(src_bad, slots, S)
    r2 = {
        "🔴 대조 글(맞는 것)": src_ok.strip(),
        "🔴 대조 글(한 자리를 바꾼 것)": src_bad.strip(),
        "🔴 키 경로": path,
        "🔴 그 경로가 내는 값": txt,
        "975 판이 맞는 글에서 잡는 수": len(b_ok["🔴 975 판이 못 찾는 수"]),
        "🔴🔴 975 판이 바꾼 글에서 잡는 수": len(b_bad["🔴 975 판이 못 찾는 수"]),
        "976 판이 맞는 글에서 잡는 수": len(a_ok["🔴🔴 976 판이 못 찾는 수"]),
        "🔴🔴 976 판이 바꾼 글에서 잡는 수": len(a_bad["🔴🔴 976 판이 못 찾는 수"]),
        "🔴🔴🔴 975 판은 본문에 매여 있나": bool(
            len(b_ok["🔴 975 판이 못 찾는 수"]) != len(b_bad["🔴 975 판이 못 찾는 수"])),
        "🔴🔴🔴 976 판은 본문에 매여 있나": bool(
            len(a_ok["🔴🔴 976 판이 못 찾는 수"]) != len(a_bad["🔴🔴 976 판이 못 찾는 수"])),
    }

    # ── 수리 4 — ALLOW_CTX 축소 ────────────────────────────────
    probe = "허용집합은 1,000 중 901 이다."
    sp975, _w975 = LG.allow_spans(probe, LG.ALLOW_CTX_975)
    sp976, _w976 = LG.allow_spans(probe, LG.ALLOW_CTX)

    def exempted(spans, s, tgt):
        for m in LG.NUMPAT.finditer(s):
            if m.group() == tgt:
                return any(a <= m.start() and m.end() <= b for a, b in spans)
        return None
    r4 = {
        "🔴 면제 규칙 수(975 판)": len(LG.ALLOW_CTX_975),
        "🔴 면제 규칙 수(976 판)": len(LG.ALLOW_CTX),
        "🔴 지운 규칙": "맨-9xx — `(?<![\\d.,])9[0-9]{2}(?![\\d.,])`",
        "🔴 좁힌 규칙": "사전등록 딱지 — 아무 글자+숫자 → 등록된 접두어(P·W·E·C·R·F·V·D·H)만",
        "🔴 대조 글": probe,
        "🔴🔴 975 판이 `901` 을 면제하나": exempted(sp975, probe, "901"),
        "🔴🔴 976 판이 `901` 을 면제하나": exempted(sp976, probe, "901"),
        "🔴 뜻": ("맨-9xx 규칙은 **900~999 를 통째로** 면제해서 "
               "수리 2 의 헤드라인 자신(「1,000 중 901」)을 안 셌다"),
    }

    # ── 수리 5 — passkey 기본값 ────────────────────────────────
    per976, n0e976, n0c976 = _census(RUNNERS_976)
    per975, n0e975, n0c975 = _census(RUNNERS_975)
    src = (ROOT / "runners/meta965.py").read_text(encoding="utf-8")
    m = re.search(r'add_argument\("--passkey",\s*default="([a-z]+)"', src)
    r5 = {
        "🔴🔴 `--passkey` 기본값": (m.group(1) if m else "?"),
        "🔴 975 까지의 기본값": "exact",
        "🔴🔴 기본값을 바꿨다": bool(m and m.group(1) == "contains"),
        "🔴 노트 898 규칙을 일부러 어겼다": True,
        "🔴 975 러너별 분모": per975,
        "🔴🔴 975 러너에서 `exact` 분모가 0 인 파일": "%d / %d" % (n0e975, len(RUNNERS_975)),
        "🔴 975 러너에서 `contains` 분모도 0 인 파일": "%d / %d" % (n0c975, len(RUNNERS_975)),
        "🔴 976 러너별 분모": per976,
        "🔴🔴 976 러너에서 `exact` 분모가 0 인 파일": "%d / %d" % (n0e976, len(RUNNERS_976)),
        "🔴🔴 976 러너에서 `contains` 분모가 0 인 파일": "%d / %d" % (n0c976, len(RUNNERS_976)),
    }

    out = {
        "무엇": "976 — 수리 다섯의 증거(사전등록 §10) · 정정 다섯은 따로 센다(§9)",
        "🔴 수리 1 — 채점기를 일회용 파일에서 꺼냈다": r1,
        "🔴🔴 수리 2 — 슬롯 검사가 문서 본문을 읽는다": r2,
        "🔴 수리 3 — 양성 대조": {
            "산출물": "runners/out976_control.json",
            "🔴 왜": "975 사전등록 §8 E4 가 등록만 하고 안 만들었다"},
        "🔴🔴 수리 4 — `ALLOW_CTX` 축소": r4,
        "🔴🔴 수리 5 — `meta965 --passkey` 기본값": r5,
        "🔴 수리 계수(부풀리지 않는다)": {
            "🔴 이 사이클의 수리": REPAIRS,
            "🔴 분자/분모": "%d / %d" % (len(REPAIRS), 5),
            "🔴 묶었나": False,
            "🔴 상한을 넘었나": len(REPAIRS) > 5,
        },
        "🔴 정정 계수(수리로 안 센다)": {
            "🔴 이 사이클의 정정": CORRECTIONS,
            "🔴 정정 수": len(CORRECTIONS),
            "🔴 정정을 수리로 세면": len(REPAIRS) + len(CORRECTIONS),
            "🔴 갈라 놓은 자리": "docs/prereg_976_c6.md §9(정정) / §10(수리) — 측정 전 단독 커밋",
        },
        "🔴 이 사이클이 **안 한** 수리": [
            "🔴 `meta965` 가 죽은 검사를 못 잡는 문제(티처 #114 3순위 ⓔ) — 수리 상한을 넘어서 안 했다",
            "🔴 `§3 V2·V3` 범위별 검정력 — **다섯 사이클째** · 「항진명제 n」 인용 금지 유효",
            "🔴 `meta965.py:1385` — **네 사이클째**",
        ],
    }
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN)
    (OUT / "out976_scorefix.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["fix"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_fix(a.ref)
    print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
