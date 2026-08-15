#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""974 --- **채점기를 채점 대상에 맞춘다**(티처 #112 2순위 ①②).

🔴 973 이 걸린 자리 둘:
  ① 채점기가 **남은 치환 슬롯만** 봤다(`assert not re.findall(r"@@[A-Z_\\\\]+@@", src)`)
     → **본문에 손으로 박은 리터럴 45 개(종류 31)를 못 봤다**.
     이 러너는 **본문의 모든 수**를 뽑아 **산출물에서 나오는 수인지** 훑는다.
  ② **F5 를 산출물 일부에만 채점했다** --- `out973_wiring.json` 이 스스로
     `기준 ref 0000…0000 · 0/3 · F5 False` 를 적었는데 ledger 는 **3/3 ✅** 로 적었다
     (wiring 을 분모에서 뺐다 · 전량이면 **15/18**). 이 러너는 **`out974_*.json` 전량**에 건다.

씀:
    python3 runners/ledger974.py --stage f5       --ref <40자 sha>
    python3 runners/ledger974.py --stage numaudit --ref <40자 sha> --files a.md b.md
"""
import argparse
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import runners.predict971 as P                    # noqa: E402

RAN = ("runners/ledger974.py", "runners/predict971.py")
OUT = ROOT / "runners"
ART = "out974_*.json"

# 🔴 「수」로 안 세는 것 --- 측정 전에 못 박고, **분모와 함께 적는다**
NUMPAT = re.compile(r"\d[\d,]*(?:\.\d+)?")
ALLOW_CTX = (
    ("노트 번호·사이클 번호", re.compile(r"(?:노트|티처 #|사이클|PR #|#)\s*\d+")),
    ("연도·날짜·시각", re.compile(r"\d{4}-\d{2}-\d{2}|\d{4}년|\d{2}:\d{2}")),
    ("절 번호", re.compile(r"§\s*\d+(?:\.\d+)?|v\d+\.\d+")),
    ("사전등록 딱지", re.compile(r"[PAHWVDE]\d+")),
)


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_stamp():
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def stamp_block(ref, cs0, cs1, t0):
    runner, ok = {}, 0
    for r in RAN:
        disk = P._sha_file(str(ROOT / r))
        try:
            cm = hashlib.sha256(subprocess.check_output(
                ["git", "show", "%s:%s" % (ref, r)], cwd=str(ROOT))).hexdigest()
        except Exception:                                          # noqa: BLE001
            cm = None
        runner[r] = {"디스크 sha256": disk, "커밋 blob sha256": cm, "일치": disk == cm}
        ok += 1 if disk == cm else 0
    return {
        "언제(시작)": t0, "언제(끝)": _now(),
        "시작 code_stamp 요약": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "끝 code_stamp 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
        "🔴 시작=끝": cs0 == cs1, "분모: 도장이 덮는 파일": len(cs1),
        "🔴 F1 기준 ref(준 대로)": ref,
        "🔴 40자 고정 sha 인가": bool(re.fullmatch(r"[0-9a-f]{40}", ref or "")),
        "🔴 기준 ref 가 0000…0000 인가": bool(re.fullmatch(r"0{40}", ref or "")),
        "러너별": runner, "🔴 분자/분모": "%d / %d" % (ok, len(RAN)),
        "🔴 F5 통과": ok == len(RAN) and bool(re.fullmatch(r"[0-9a-f]{40}", ref or ""))
        and not re.fullmatch(r"0{40}", ref or ""),
    }


# ══════════════════════════════════════════════════════════════════════
# ② F5 를 **산출물 전량**에
# ══════════════════════════════════════════════════════════════════════
def stage_f5(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    rows = collections.OrderedDict()
    num = den = 0
    for p in sorted(glob.glob(str(OUT / ART))):
        name = Path(p).name
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception as e:                                     # noqa: BLE001
            rows[name] = {"🔴 읽기 실패": str(e)}
            den += 1
            continue
        st = d.get("🔴 도장")
        den += 1
        if not isinstance(st, dict):
            rows[name] = {"🔴 도장이 없다": True, "F5": False}
            continue
        ok = bool(st.get("🔴 F5 통과"))
        num += 1 if ok else 0
        rows[name] = {
            "F5": ok, "분자/분모": st.get("🔴 분자/분모"),
            "기준 ref": st.get("🔴 F1 기준 ref(준 대로)"),
            "40자 고정 sha 인가": st.get("🔴 40자 고정 sha 인가"),
            "🔴 0000…0000 인가": st.get("🔴 기준 ref 가 0000…0000 인가"),
            "시작=끝": st.get("🔴 시작=끝"),
            "도장이 덮는 파일": st.get("분모: 도장이 덮는 파일"),
        }
    out = {
        "무엇": "974 --- F5 를 **산출물 전량**에 채점한다(973 은 분모에서 뺐다)",
        "🔴 채점 대상 글롭": ART,
        "🔴🔴 F5 분자/분모(전량)": "%d / %d" % (num, den),
        "🔴 전량 통과인가": num == den,
        "산출물별": rows,
        "🔴 973 이 적은 것": "3 / 3 ✅ (wiring 을 분모에서 뺐다)",
        "🔴 티처 #112 가 전량으로 다시 센 것": "15 / 18",
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out974_f5.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# ① 본문의 **모든 수**가 산출물에서 나오는가
# ══════════════════════════════════════════════════════════════════════
def _norm(x: str) -> str:
    x = x.replace(",", "")
    if "." in x:
        x = x.rstrip("0").rstrip(".")
    return x or "0"


def artifact_numbers() -> set:
    """산출물 전량에서 **나올 수 있는 수**를 모은다 --- 값이든 문자열 속이든."""
    S = set()

    def add(v):
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            s = ("%r" % v) if isinstance(v, float) else str(v)
            S.add(_norm(s))
            if isinstance(v, float):
                for k in range(0, 7):
                    S.add(_norm("%.*f" % (k, v)))
                S.add(_norm("%.1f" % (100.0 * v)))
                S.add(_norm("%.2f" % (100.0 * v)))
                S.add(_norm("%.4f" % (100.0 * v)))
        elif isinstance(v, str):
            for m in NUMPAT.findall(v):
                S.add(_norm(m))
        elif isinstance(v, dict):
            for k, x in v.items():
                add(k)
                add(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                add(x)

    for p in sorted(glob.glob(str(OUT / ART))):
        try:
            add(json.loads(Path(p).read_text(encoding="utf-8")))
        except Exception:                                          # noqa: BLE001
            pass
    return S


def stage_numaudit(ref: str, files) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    S = artifact_numbers()
    per = collections.OrderedDict()
    tot = miss_tot = 0
    kinds = collections.Counter()
    for rel in files:
        p = ROOT / rel
        if not p.is_file():
            per[rel] = {"🔴 파일이 없다": True}
            continue
        src = p.read_text(encoding="utf-8")
        allow_spans = []
        for _why, pat in ALLOW_CTX:
            for m in pat.finditer(src):
                allow_spans.append((m.start(), m.end()))
        found, missing = 0, []
        for m in NUMPAT.finditer(src):
            if any(a <= m.start() and m.end() <= b for a, b in allow_spans):
                continue
            found += 1
            if _norm(m.group()) not in S:
                ctx = re.sub(r"\s+", " ", src[max(0, m.start() - 40):m.end() + 40])
                missing.append({"수": m.group(), "맥락": ctx})
                kinds[_norm(m.group())] += 1
        tot += found
        miss_tot += len(missing)
        per[rel] = {
            "🔴 센 수(딱지·연도·절번호 뺀)": found,
            "🔴 산출물에서 안 나오는 수": len(missing),
            "비율": round(len(missing) / float(found), 6) if found else None,
            "목록": missing[:60],
        }
    out = {
        "무엇": "974 --- 본문의 **모든 수**가 산출물에서 나오는지 훑는다(규칙 D)",
        "🔴 973 의 채점기가 본 것": "남은 치환 슬롯 `@@X@@` 뿐 --- 손 리터럴은 못 봤다",
        "🔴 산출물에서 모은 수의 가짓수": len(S),
        "🔴 대상 파일": list(files),
        "🔴🔴 전체 분자/분모(안 나오는 수 / 센 수)": "%d / %d" % (miss_tot, tot),
        "🔴 통과(하나도 없어야 한다)": miss_tot == 0,
        "🔴 안 나오는 수의 종류": len(kinds),
        "종류별": dict(kinds.most_common(40)),
        "파일별": per,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out974_numaudit.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["f5", "numaudit"])
    ap.add_argument("--ref", default="")
    ap.add_argument("--files", nargs="*", default=[])
    a = ap.parse_args()
    r = stage_f5(a.ref) if a.stage == "f5" else stage_numaudit(a.ref, a.files)
    print(json.dumps({k: v for k, v in r.items() if k not in ("파일별", "산출물별")},
                     ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
