# -*- coding: utf-8 -*-
"""노트 943 — 🔴 **두 번째 경로.** `out943_axis.py` 를 **한 줄도 import 하지 않는다.**

## 왜 이 파일이 있나

티처 #82 M1: 942 의 사전등록이 *「두 번째 경로로 세지 않으면 무효」*라 못 박았는데
**그 코드가 저장소에 없었다.** 노트는 「jq 로 돌렸다」고 적었지만 티처가 커밋 diff·
`runners/`·`docs/`·저장소 전체 grep 을 훑어도 **0건**이었다.
그래서 943 은 두 번째 경로를 **파일로 남긴다.** 이 파일이 그것이다.

## 어떻게 다른 경로인가 (같은 코드를 두 번 부르면 두 번째 경로가 아니다)

| | `out943_axis.py` | 🔴 이 파일 |
|---|---|---|
| 942 함수 | `import` 해서 호출 | **안 부른다** — 942 의 정의를 **문장으로 읽고 새로 짠다** |
| 순회 | `Path.glob` 디렉터리별 | **`os.walk`** 로 트리 전체를 훑고 경로로 거른다 |
| 집계 | 루프 안에서 `+=` | 레코드마다 **표식 튜플**을 모아 **끝에서 `Counter`** 로 센다 |
| 값 꺼내기 | `dig(r, path)` | **재귀 워커**가 `dict` 를 평평하게 펴서 점경로로 조회 |
| 대조 | — | `runners/out943_axis.json` 을 **읽어서** 수를 하나씩 맞춘다 |

🔴 **불일치가 하나라도 있으면 사전등록 반증조건 2 에 걸려 943 은 무효다.**

쓰는 법::  python3 runners/out943_recount.py
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out943_recount.json"
REF = ROOT / "runners/out943_axis.json"

#: 942 가 D1 로 삼은 여섯 디렉터리 (이름만 옮긴다 — 코드를 import 하지 않는다)
D1 = {"data/records", "data/market_records", "data/idol_records",
      "data/records_draft", "data/records_incomplete", "data/records_thinbak"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def flatten(o, prefix="", out=None) -> dict:
    """🔴 dict 를 **점경로 → 값** 으로 평평하게 편다(`dig` 와 다른 방식).

    list 는 안 편다 — 942 의 `_nonempty` 가 list 를 값으로 보기 때문이다.
    """
    if out is None:
        out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            key = f"{prefix}{k}"
            out[key] = v
            if isinstance(v, dict):
                flatten(v, key + ".", out)
    return out


def has(flat: dict, dotted: str) -> bool:
    """942 의 `_nonempty` 를 **문장으로 읽고 다시 쓴 것**: None·''·[]·{} 만 없다."""
    v = flat.get(dotted, None)
    if v is None:
        return False
    if isinstance(v, (str, list, dict, tuple)):
        return len(v) > 0
    return True


def mark(r: dict) -> tuple:
    """레코드 하나 → 표식 튜플. 🔴 센 것은 끝에서 `Counter` 가 한다."""
    flat = flatten(r)
    # 계열 — 942 의 `family()` 를 문장으로 읽고 다시 씀
    oc = r.get("outcome")
    if isinstance(oc, dict):
        fam = "A" if "totals" in oc else "B"
    else:
        fam = "C"

    # o — 942 의 새 검출기 (스키마별 결과 열)
    if fam == "A":
        o = any(has(flat, k) for k in
                ("outcome.daily", "outcome.totals.visitors", "outcome.totals.sales_krw",
                 "outcome.totals.sales_amount_krw", "outcome.totals.visitors_total"))
    elif fam == "B":
        o = any(has(flat, k) for k in ("outcome.visitors_total", "outcome.sales_krw"))
    else:
        o = any(has(flat, k) for k in ("chodong", "chart_peak", "mv_24h"))

    # a(942) — 「칸이 있다」
    a_old = has(flat, "debut_date") if fam == "C" else has(flat, "intervention")
    # a(943) — 🔴 「시점이 있다」
    a_new = has(flat, {"A": "conditions.period.from",
                       "B": "conditions.period_from",
                       "C": "debut_date"}[fam])
    # s(942) — conditions **칸**이 있다
    idol_s = ("agency", "member_count", "gender", "is_group",
              "survival_show", "pre_debut_note")
    if fam == "C":
        s_old = s_new = any(has(flat, k) for k in idol_s)
    else:
        s_old = has(flat, "conditions")
        c = r.get("conditions")
        # 🔴 첫 판에서 여기를 `has(flat, k)` 로 썼다가 **틀렸다**(s=261 · 첫 경로 1,314).
        # `flatten` 은 conditions 하위를 `conditions.<키>` 로 펴므로 접두사가 필요하다.
        # 두 번째 경로가 잡은 것은 **두 번째 경로 자신의 버그**였고, 그게 대조의 값이다.
        s_new = isinstance(c, dict) and any(
            has(flat, "conditions." + k) for k in c
            if k not in ("period", "period_from", "period_to"))
    return (fam, bool(a_old), bool(a_new), bool(s_old), bool(s_new), bool(o))


def main() -> dict:
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    marks: list = []
    files: list = []
    for base, dirs, names in os.walk(ROOT / "data"):
        rel = str(Path(base).relative_to(ROOT))
        if rel not in D1:
            continue
        for nm in sorted(names):
            if not nm.endswith(".json"):
                continue
            p = Path(base) / nm
            try:
                r = json.loads(p.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(r, dict):
                continue
            files.append(str(p.relative_to(ROOT)))
            marks.append(mark(r))

    c = Counter(marks)
    n = len(marks)

    def tot(idx):
        return sum(v for k, v in c.items() if k[idx])

    def by_fam(idx):
        out: Counter = Counter()
        for k, v in c.items():
            if k[idx]:
                out[k[0]] += v
        return dict(out)

    got = {
        "분모 D1": n,
        "계열": dict(Counter(k[0] for k in marks)),
        "a(942·칸)": tot(1),
        "a(943·시점)": tot(2),
        "s(942·칸)": tot(3),
        "s(943·값+period 제거)": tot(4),
        "o(942 새 검출기)": tot(5),
        "o ∧ a(시점)": sum(v for k, v in c.items() if k[5] and k[2]),
        "a·s·o(942)": sum(v for k, v in c.items() if k[1] and k[3] and k[5]),
        "a·s·o(943)": sum(v for k, v in c.items() if k[2] and k[4] and k[5]),
        "계열별 a(943)": by_fam(2),
        "계열별 o∧a(시점)": {f: sum(v for k, v in c.items()
                                 if k[0] == f and k[5] and k[2])
                          for f in ("A", "B", "C")},
    }

    # ── 🔴 대조 ─────────────────────────────────────────────────────────
    ref = json.loads(REF.read_text())
    side = ref["🔴 ㄴ·ㄷ 고치기 전/후 나란히"]
    wire = ref["🔴 ㄱ 배선 검사 — 942 의 함수를 import 해서 호출한 값(고치기 전)"]
    famref = {"A_팝업(outcome.totals)": "A", "B_시장(평평한 outcome)": "B",
              "C_아이돌(outcome 없음)": "C"}
    cmp_ = {
        "분모 D1": (got["분모 D1"], ref["🔴 분모 D1(파일)"]),
        "a(942)": (got["a(942·칸)"], side["a — 942(intervention 칸 존재)"]),
        "a(943)": (got["a(943·시점)"], side["a — 943(액션 **시점**)"]),
        "s(942)": (got["s(942·칸)"], side["s — 942(conditions **칸**이 있다)"]),
        "s(943)": (got["s(943·값+period 제거)"],
                   side["s — 943ㄴ(거기서 period_* 를 a 로 옮김)"]),
        "o": (got["o(942 새 검출기)"], side["o — 942 새 검출기(안 건드림)"]),
        "o∧a(시점)": (got["o ∧ a(시점)"], side["o ∧ a(시점)"]),
        "a·s·o(942)": (got["a·s·o(942)"], side["a·s·o — 942"]),
        "a·s·o(943)": (got["a·s·o(943)"], side["a·s·o — 943"]),
        "942 러너가 적은 a": (got["a(942·칸)"], wire["a(942)"]),
        "942 러너가 적은 s": (got["s(942·칸)"], wire["s(942)"]),
        "942 러너가 적은 a·s·o": (got["a·s·o(942)"], wire["a·s·o(942)"]),
    }
    for kk, vv in ref["계열별 a(942/943)"].items():
        cmp_[f"계열 {famref[kk]} 의 a(943)"] = (got["계열별 a(943)"][famref[kk]], vv["943"])
    for kk, vv in ref["계열별 o∧a(시점)"].items():
        cmp_[f"계열 {famref[kk]} 의 o∧a"] = (got["계열별 o∧a(시점)"][famref[kk]], vv)

    diff = {k: {"두 번째 경로": a, "첫 경로": b} for k, (a, b) in cmp_.items() if a != b}

    res = {
        "노트": 943, "무엇": "🔴 두 번째 경로 — out943_axis.py 를 import 하지 않고 다시 센다",
        "🔴 스탬프": {
            "시작 시각": t_start,
            "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256(첫 경로 산출물)": sha(REF),
            "코드 sha256": {"runners/out943_recount.py": sha(ROOT / "runners/out943_recount.py")},
            "🔴 이 파일이 import 한 저장소 모듈": [],
        },
        "🔴 조항 60 — 명령·범위": {
            "명령": "python3 runners/out943_recount.py",
            "범위": sorted(D1),
            "실제로 연 파일 수": len(files),
        },
        "두 번째 경로가 센 값": got,
        "🔴 대조(두 번째 경로 vs 첫 경로)": {k: {"두 번째": a, "첫": b, "같다": a == b}
                                    for k, (a, b) in cmp_.items()},
        "🔴 대조 항목 수(분모)": len(cmp_),
        "🔴 어긋난 항목": diff,
        "통과": not diff,
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
