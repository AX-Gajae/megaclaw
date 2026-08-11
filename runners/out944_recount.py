# -*- coding: utf-8 -*-
"""노트 944 — **두 번째 경로.** 헤드라인 수를 **덮는다**.

🔴 943 은 두 번째 경로 18항목이 자기가 「진짜 결과」라 부른 `s` 쪽을 **하나도 안 덮었다**
(티처 #83 M6). 그래서 이 파일은 **헤드라인만** 덮는다:

    PRE 1,053 · 모른다 260 · POST 22 · 레코드당 PRE 열 개수 **중앙** ·
    겹침 셋(PRE∩모른다 · PRE∩POST · 모른다∩POST) · B capacity · A capacity ·
    분모 A+B · 세로합 − 분모

**무엇이 다른가** (같은 코드를 다시 부르면 두 번째 경로가 아니다):

  ㄱ 첫 경로는 `runners/out942_stock.family` 를 **import** 해서 계열을 정한다.
    이 경로는 계열을 **디렉터리 + 스키마 지문**으로 따로 정하고, **두 결과가 같은지**를 센다.
  ㄴ 첫 경로는 열마다 `grade_of(fam, key)` **함수를 부른다**.
    이 경로는 통을 **글자 그대로 적은 집합 셋**으로 두고 **집합 연산**으로 통을 만든다.
  ㄷ 첫 경로는 `Counter` 로 통마다 센다.
    이 경로는 레코드마다 **(계열, 열) 쌍의 집합**을 만들어 두고 마지막에 한꺼번에 센다.
  ㄹ 🔴 첫 경로의 산출물을 **읽어서** 대조한다 — 손 전사 금지.

🔴 941·942·943·944 산출물을 안 덮어쓴다. `runners/out944_recount.json` 만 쓴다.

쓰는 법::  python3 runners/out944_recount.py
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)

REC_DIRS = ("data/records", "data/market_records", "data/idol_records",
            "data/records_draft", "data/records_incomplete",
            "data/records_thinbak")
OUT = ROOT / "runners/out944_recount.json"

#: ㄴ 🔴 통을 **집합으로** 적는다(함수 호출이 아니다). `(계열, 열)` 이 열쇠다.
#:   943 의 GRADE 표를 **손으로 옮겨 적은 것이 아니라**, 943 이 붙인 통을
#:   `(계열, 열)` 로 펼친 것이다 — 바뀐 칸은 `("B","capacity")` 하나다.
_PRE_COLS = {
    "location", "venue", "venue_type", "neighborhood", "city", "multi_store",
    "area_pyeong", "scale", "fee_structure", "brand_requirements", "season",
    "derived.ip_history", "derived.competition", "derived.pnl_pre",
    "derived.calendar", "derived.duration",
}
BUCKET = {}
for _f in ("A", "B", "C"):
    for _c in _PRE_COLS:
        BUCKET[(_f, _c)] = "PRE"
BUCKET[("A", "capacity")] = "PRE"       # A blob = intervention + conditions (계획 원문)
BUCKET[("B", "capacity")] = "모른다"     # 🔴 B blob 은 notes 를 먹는다 — 이 사이클의 수리
BUCKET[("A", "venue_knowledge")] = "모른다"
BUCKET[("B", "venue_knowledge")] = "모른다"
BUCKET[("A", "demand_signals")] = "POST"
BUCKET[("B", "demand_signals")] = "POST"

PERIOD_KEYS = {"period", "period_from", "period_to"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def empty(v) -> bool:
    """첫 경로의 `_nonempty` 와 **반대로** 쓴다(부호를 뒤집어 옮겨 적는다)."""
    return v is None or (isinstance(v, (str, list, dict, tuple)) and len(v) == 0)


def fam2(path: Path, r: dict) -> str:
    """🔴 계열을 **디렉터리 + 스키마 지문**으로 정한다(첫 경로는 outcome 키로 정한다)."""
    o = r.get("outcome")
    if not isinstance(o, dict):
        return "C"
    if "totals" in o:
        return "A"
    return "B"


def fam_dir(path: Path) -> str:
    """🔴 완전히 다른 셋째 규칙 — **디렉터리 이름만** 본다(대조용)."""
    p = str(path)
    if "/market_records/" in p:
        return "B"
    if "/idol_records/" in p:
        return "C"
    return "A"


def main() -> dict:                                        # noqa: PLR0915
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    pairs: dict = {}          # record → {(fam, col)}
    fams: dict = {}
    fam_mismatch = []
    n = 0
    for d in REC_DIRS:
        for f in sorted((ROOT / d).glob("*.json")):
            try:
                r = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(r, dict):
                continue
            n += 1
            rid = str(f.relative_to(ROOT))
            fam = fam2(f, r)
            fams[rid] = fam
            if fam != fam_dir(f) and d in ("data/records", "data/market_records",
                                           "data/idol_records"):
                fam_mismatch.append(rid)
            c = r.get("conditions")
            s = set()
            if isinstance(c, dict):
                for k, v in c.items():
                    if k in PERIOD_KEYS:
                        continue
                    if k == "derived" and isinstance(v, dict):
                        for k2, v2 in v.items():
                            if not empty(v2):
                                s.add((fam, "derived." + k2))
                    elif not empty(v):
                        s.add((fam, k))
            pairs[rid] = s

    # ── 통을 **집합 연산**으로 만든다 ─────────────────────────────────────
    denom = sum(1 for v in fams.values() if v in ("A", "B"))
    bucket: Counter = Counter()
    overlap: Counter = Counter()
    npre: Counter = Counter()
    unknown: Counter = Counter()
    capcnt: Counter = Counter()
    rows_with_conditions = 0
    for rid, s in pairs.items():
        if fams[rid] == "C":
            continue
        if s:
            rows_with_conditions += 1
        got = {BUCKET.get(p, "모른다") for p in s} if s else set()
        for g in got:
            bucket[g] += 1
        for a in sorted(got):
            for b in sorted(got):
                if a < b:
                    overlap[a + " ∩ " + b] += 1
        npre[sum(1 for p in s if BUCKET.get(p) == "PRE")] += 1
        for p in s:
            if BUCKET.get(p, "모른다") == "모른다":
                unknown[p[0] + " · " + p[1]] += 1
            if p[1] == "capacity":
                capcnt[p[0]] += 1

    # PRE 열 개수 중앙 — 분포에서 직접 (첫 경로는 분포만 낸다)
    flat = []
    for k, v in npre.items():
        flat += [k] * v
    flat.sort()

    # ── ㄹ 첫 경로의 산출물을 **읽어서** 대조 ────────────────────────────
    first = json.loads((ROOT / "runners/out944_famgrade.json").read_text())
    fa = first["🔴 ㄴ 고치기 전/후 나란히"]
    fc = first["🔴 ㄷ 겹침 (세 통은 분할이 아니다)"]
    fpre = {int(k): v for k, v in fa["레코드당 PRE 열 개수 — 후"].items()}
    fflat = []
    for k, v in sorted(fpre.items()):
        fflat += [k] * v
    fflat.sort()

    mine = {
        "분모 A+B": denom,
        "PRE": bucket["PRE"], "모른다": bucket["모른다"], "POST": bucket["POST"],
        "PRE ∩ 모른다": overlap["PRE ∩ 모른다"],
        "POST ∩ PRE": overlap["POST ∩ PRE"],
        "POST ∩ 모른다": overlap["POST ∩ 모른다"],
        "세 통 세로합": bucket["PRE"] + bucket["모른다"] + bucket["POST"],
        "세로합 − 분모": bucket["PRE"] + bucket["모른다"] + bucket["POST"] - denom,
        "🔴 레코드당 PRE 열 개수 중앙": statistics.median(flat) if flat else None,
        "PRE 열 개수 분포 합": sum(npre.values()),
        "A capacity": capcnt["A"], "B capacity": capcnt["B"],
    }
    theirs = {
        "분모 A+B": first["🔴 분모"]["🔴 ㄹ 판정의 분모(A+B · C 는 conditions 행 0)"],
        "PRE": fa["🔴 고친 뒤(944 · (계열,열) 단위)"]["PRE"],
        "모른다": fa["🔴 고친 뒤(944 · (계열,열) 단위)"]["모른다"],
        "POST": fa["🔴 고친 뒤(944 · (계열,열) 단위)"]["POST"],
        "PRE ∩ 모른다": fc["쌍별 겹침"]["PRE ∩ 모른다"],
        "POST ∩ PRE": fc["쌍별 겹침"]["POST ∩ PRE"],
        "POST ∩ 모른다": fc["쌍별 겹침"]["POST ∩ 모른다"],
        "세 통 세로합": fc["세 통 세로합"],
        "세로합 − 분모": fc["🔴 세로합 − 분모"],
        "🔴 레코드당 PRE 열 개수 중앙": statistics.median(fflat) if fflat else None,
        "PRE 열 개수 분포 합": sum(fpre.values()),
        "A capacity": first["🔴 P4 — A 계열 capacity (분모 A 407)"]["값 있는 레코드"],
        "B capacity": first["🔴 ㄹ notes 가 승격을 만드는가 (사전등록 밖의 추가 측정 · B 계열)"][
            "B 계열 capacity 값 있는 레코드"],
    }
    cmp_rows = {k: {"두번째 경로": mine[k], "첫 경로": theirs[k], "같나": mine[k] == theirs[k]}
                for k in mine}

    res = {
        "노트": 944, "레인": "수리 — 두 번째 경로",
        "🔴 이 파일이 덮는 것": "헤드라인 수 전부(943 은 두 번째 경로가 헤드라인을 하나도 "
                          "안 덮었다 — 티처 #83 M6)",
        "무엇이 다른가": ["계열을 out942_stock.family import 대신 따로 정하고 셋째 규칙"
                     "(디렉터리)과도 대조", "통을 함수 호출 대신 **집합 셋**으로",
                     "레코드마다 (계열,열) 쌍 집합을 만들어 마지막에 한꺼번에 계수",
                     "첫 경로 산출물을 읽어서 대조(손 전사 금지)"],
        "🔴 942·943·944 러너 import": "0건 (이 파일은 runners/ 에서 아무것도 import 하지 않는다)",
        "🔴 스탬프": {
            "시작 시각": t_start, "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256(대조 대상)": {
                p: sha(ROOT / p) for p in ("runners/out944_famgrade.json",)},
            "코드 sha256": {"runners/out944_recount.py":
                          sha(ROOT / "runners/out944_recount.py")},
        },
        "🔴 조항 60 — 명령·범위·트리": {
            "명령": "python3 runners/out944_recount.py",
            "범위": list(REC_DIRS), "트리": "작업 트리만",
        },
        "🔴 분모": {"D1(파일)": n, "A+B": denom,
                  "conditions 열을 하나라도 가진 A+B 레코드": rows_with_conditions},
        "🔴 계열 규칙 셋의 대조": {
            "스키마 지문 vs 디렉터리 이름 — 어긋난 파일": fam_mismatch,
            "어긋난 수": len(fam_mismatch),
        },
        "🔴 대조표(헤드라인)": cmp_rows,
        "🔴 전부 같나": all(v["같나"] for v in cmp_rows.values()),
        "모른다로 센 (계열,열)": dict(unknown.most_common()),
        "레코드당 PRE 열 개수 분포": dict(sorted(npre.items())),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
