#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""975 --- **채점기의 분모를 고친다** ① 대상을 넷 전부로 ② 값 일치 → **출처 키 경로 일치**.

🔴 **974 가 걸린 자리 둘**(티처 #113 3순위 ⓐⓑ):
  ⓐ `numaudit` 대상이 **판정문·논문 둘뿐**이었다 --- **틀린 수(카드의 「W 8/8」)가
     정확히 안 보는 쪽에 있었다.** 이제 **넷 전부**(판정문·논문·**카드**·**원장**)를 본다.
  ⓑ 채점이 **「이 수가 산출물 어딘가에 있나」**였다. 그 허용집합은 **정수 0~999 의 90.1%**
     를 담아 🔴 **`525 → 524` 를 원리상 못 잡는다.** 이제 **「이 수가 그 자리가 선언한
     출처 키 경로의 값과 같나」**를 묻는다.

씀:
    python3 runners/ledger975.py --stage f5       --ref <40자 sha>
    python3 runners/ledger975.py --stage numaudit --ref <40자 sha>
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

RAN = ("runners/ledger975.py", "runners/predict971.py")
OUT = ROOT / "runners"
ART = "out975_*.json"
SLOTS = OUT / "out975_slots.json"

NUMPAT = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
ALLOW_CTX = (
    ("노트 번호·사이클 번호", re.compile(r"(?:노트|티처 #|사이클|PR #|#)\s*\d+")),
    ("연도·날짜·시각", re.compile(r"\d{4}-\d{2}-\d{2}|\d{4}년|\d{2}:\d{2}")),
    ("절 번호", re.compile(r"§\s*\d+(?:\.\d+)?|v\d+\.\d+")),
    ("사전등록 딱지", re.compile(r"[PAHWVDERC]\d+")),
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
def _norm(x: str) -> str:
    x = x.replace(",", "")
    if "." in x:
        x = x.rstrip("0").rstrip(".")
    return x or "0"


def artifact_numbers(glob_pat=ART) -> set:
    """🔴 **974 판 채점기** --- 산출물 어딘가에 나오는 수의 집합. 여기 남겨 두는 이유는
    **새 채점기와 나란히 세우기 위해서**다(조항 66-③: 자를 고치면 전후를 같이 싣는다)."""
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

    for p in sorted(glob.glob(str(OUT / glob_pat))):
        try:
            add(json.loads(Path(p).read_text(encoding="utf-8")))
        except Exception:                                          # noqa: BLE001
            pass
    return S


def resolve(path):
    """🔴 **975 판 채점기의 핵** --- `[파일, 키, 키, …]` 를 산출물에서 실제로 따라간다."""
    if not path:
        return None, "빈 경로"
    f = OUT / path[0]
    if not f.is_file():
        return None, "산출물이 없다: %s" % path[0]
    cur = json.loads(f.read_text(encoding="utf-8"))
    for k in path[1:]:
        if isinstance(cur, dict):
            if k not in cur:
                return None, "키가 없다: %s" % k
            cur = cur[k]
        elif isinstance(cur, list):
            try:
                cur = cur[int(k)]
            except Exception:                                      # noqa: BLE001
                return None, "자리가 없다: %s" % k
        else:
            return None, "더 못 들어간다: %s" % k
    return cur, None


def render(v):
    """산출물 값 하나를 **본문에 실을 문자열**로. 여기 말고 다른 데서 안 만든다."""
    if isinstance(v, bool):
        return "참" if v else "거짓"
    if isinstance(v, float):
        return ("%.6f" % v).rstrip("0").rstrip(".") if abs(v) < 1e15 else repr(v)
    if isinstance(v, int):
        return "{:,}".format(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(render(x) for x in v) + "]"
    return str(v)


# ══════════════════════════════════════════════════════════════════════
def keypath_control() -> dict:
    """🔴 **수리 2 의 양성 대조** --- `525 → 524` 를 두 채점기에 걸어 본다."""
    S = artifact_numbers()
    ints = [str(i) for i in range(1000)]
    in_S = sum(1 for i in ints if i in S)
    # 974 판: 값이 집합에 있으면 통과
    old_catches = "524" not in S
    # 975 판: 그 자리가 선언한 키 경로의 값과 견준다
    path = ["out974_precision.json", "🔴🔴 ① 층화 표본 전체(층 무시)", "참"]
    val, err = resolve(path)
    new_ok = (err is None and render(val) == "525")
    new_catches = (err is None and render(val) != "524")
    return {
        "🔴 정수 0~999 중 허용집합에 든 것": in_S,
        "분모": len(ints),
        "🔴 비율": round(in_S / float(len(ints)), 4),
        "🔴 티처 #113 이 신고한 비율": 0.901,
        "🔴 `524` 가 허용집합에 있나": "524" in S,
        "🔴🔴 974 판(값 집합 일치)이 `525 → 524` 를 잡나": old_catches,
        "🔴 975 판이 쓰는 키 경로": path,
        "🔴 그 경로가 실제로 내는 값": render(val) if err is None else err,
        "🔴 그 값이 `525` 인가": new_ok,
        "🔴🔴 975 판(출처 키 경로 일치)이 `525 → 524` 를 잡나": new_catches,
        "🔴🔴 고침이 물었나": bool(new_catches and not old_catches),
    }


# ══════════════════════════════════════════════════════════════════════
def stage_f5(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    rows = collections.OrderedDict()
    num = den = 0
    for p in sorted(glob.glob(str(OUT / ART))):
        name = Path(p).name
        if name == "out975_slots.json":
            continue
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
        "무엇": "975 --- F5 를 산출물 전량에 채점한다",
        "🔴 채점 대상 글롭": ART,
        "🔴🔴 F5 분자/분모(전량)": "%d / %d" % (num, den),
        "🔴 전량 통과인가": num == den,
        "산출물별": rows,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out975_f5.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
def stage_numaudit(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    S = artifact_numbers()
    man = json.loads(SLOTS.read_text(encoding="utf-8")) if SLOTS.is_file() else {}
    files = man.get("파일별", {})
    per = collections.OrderedDict()
    tot = miss_old = miss_new = 0
    bad_slot = 0
    for rel, info in files.items():
        p = Path(info["절대경로"]) if info.get("절대경로") else (ROOT / rel)
        if not p.is_file():
            per[rel] = {"🔴 파일이 없다": True}
            continue
        src = p.read_text(encoding="utf-8")
        spans = []
        for sl in info["슬롯"]:
            val, err = resolve(sl["키 경로"])
            ok = (err is None and render(val) == sl["값"])
            if not ok:
                bad_slot += 1
            spans.append((sl["시작"], sl["끝"], ok, sl))
        allow = []
        for _why, pat in ALLOW_CTX:
            for m in pat.finditer(src):
                allow.append((m.start(), m.end()))
        found, m_old, m_new = 0, [], []
        for m in NUMPAT.finditer(src):
            if any(a <= m.start() and m.end() <= b for a, b in allow):
                continue
            found += 1
            if _norm(m.group()) not in S:
                m_old.append({"수": m.group(),
                              "맥락": re.sub(r"\s+", " ",
                                           src[max(0, m.start() - 40):m.end() + 40])})
            cov = [sp for sp in spans if sp[0] <= m.start() and m.end() <= sp[1]]
            if not cov or not cov[0][2]:
                m_new.append({"수": m.group(),
                              "왜": ("슬롯 밖(손으로 적은 수)" if not cov
                                    else "슬롯의 키 경로가 그 값을 안 낸다"),
                              "맥락": re.sub(r"\s+", " ",
                                           src[max(0, m.start() - 40):m.end() + 40])})
        tot += found
        miss_old += len(m_old)
        miss_new += len(m_new)
        per[rel] = {
            "🔴 센 수(딱지·연도·절번호 뺀)": found,
            "🔴 슬롯 수": len(spans),
            "🔴 키 경로가 안 맞는 슬롯": sum(1 for sp in spans if not sp[2]),
            "🔴 974 판(값 집합)이 못 찾는 수": len(m_old),
            "🔴🔴 975 판(출처 키 경로)이 못 찾는 수": len(m_new),
            "974 판 목록": m_old[:40],
            "🔴 975 판 목록": m_new[:60],
        }
    out = {
        "무엇": "975 --- 본문 **넷 전부**의 모든 수가 **출처 키 경로**에서 나오는지 훑는다",
        "🔴 974 의 대상": ["판정문", "논문"],
        "🔴 975 의 대상": list(files),
        "🔴 분모: 대상 파일": len(files),
        "🔴 산출물에서 모은 수의 가짓수(974 판 허용집합)": len(S),
        "🔴🔴 974 판 분자/분모": "%d / %d" % (miss_old, tot),
        "🔴🔴🔴 975 판 분자/분모(출처 키 경로가 없는 수 / 센 수)": "%d / %d" % (miss_new, tot),
        "🔴 통과(975 판 · 하나도 없어야 한다)": miss_new == 0,
        "🔴 키 경로가 안 맞는 슬롯(전체)": bad_slot,
        "🔴 수리 2 양성 대조": keypath_control(),
        "파일별": per,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out975_numaudit.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["f5", "numaudit"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_f5(a.ref) if a.stage == "f5" else stage_numaudit(a.ref)
    print(json.dumps({k: v for k, v in r.items() if k not in ("파일별", "산출물별")},
                     ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
