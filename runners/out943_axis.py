# -*- coding: utf-8 -*-
"""노트 943(수리) — **`a` 를 「시점이 붙은 액션」으로 다시 정의하고 D1 을 다시 센다.**

티처 #82 C1: `runners/out942_stock.py:196-199` 의 `a_of()` 가 A·B 계열 1,054 에서
`intervention` dict 가 **비어 있지 않다**만 본다 — **시점이 없다.**
같은 파일 `:308` 의 `d2_stock()` 은 a 를 **날짜**로 정의한다.
**한 러너 안에 a 의 정의가 둘**이었다.

이 러너가 하는 것 넷:

  **ㄱ** 🔴 **배선 검사** — 942 의 `a_of`·`s_of`·`o_new`·`family` 를 **import 해서 호출**해
        `a 1,328 · s 1,315 · 셋 다 732` 를 **같은 순회에서** 재현한다(고치기 **전**).
  **ㄴ** `a` 를 **날짜**로 재정의(A `conditions.period.from` · B `conditions.period_from` ·
        C `debut_date`)하고 D1 1,336 을 **계열별·디렉터리별**로 다시 센다.
  **ㄷ** 🔴 `period_*` 를 `s` 에서 **빼내 `a` 로 옮긴다.** 옮긴 뒤 s 가 얼마로 줄어드는지 신고.
  **ㄹ** 🔴 `conditions` 의 열을 **하나씩** 「액션 앞에 알 수 있었나」로 판정
        (**PRE · POST · 모른다** 세 통 · 못 가르면 **모른다**로 센다 — 조항 59).

🔴 **941·942 산출물은 동결물이다 — 안 덮어쓴다.** 이 러너는 `runners/out943_axis.json` 만 쓴다.
🔴 **판 ρ 는 안 부른다.** 이 사이클은 예측 성능을 안 잰다.
🔴 스탬프는 **시작 시각 · 끝 시각 · 입력 sha256 · 코드 sha256** 넷이다.
   `git rev-parse HEAD` 는 **루프 v3.2 가 폐기했다**(`docs/루프.md:443-448`) — 안 쓴다.

사전등록: `docs/prereg_943_actiontime.md` (측정 **전** 커밋 `b576f7768`)

쓰는 법::  python3 runners/out943_axis.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

#: D1 — 파일 하나 = 레코드 하나 (941·942 와 **같은 목록**이어야 대조가 성립한다)
REC_DIRS = ("data/records", "data/market_records", "data/idol_records",
            "data/records_draft", "data/records_incomplete",
            "data/records_thinbak")

OUT = ROOT / "runners/out943_axis.json"

#: 🔴 액션의 **시점** 경로. 계열마다 다르다. 이것이 이 수리의 전부다.
A_TIME_PATH = {
    "A_팝업(outcome.totals)": ("conditions", "period", "from"),
    "B_시장(평평한 outcome)": ("conditions", "period_from"),
    "C_아이돌(outcome 없음)": ("debut_date",),
}

#: 🔴 `s` 에서 빼서 `a` 로 옮기는 열. 「액션이 언제였나」이지 「액션 앞 상태」가 아니다.
PERIOD_KEYS = {"period", "period_from", "period_to"}


# ── 열 단위 판정표 ───────────────────────────────────────────────────────
#: 🔴 근거의 **종류**를 적는다. 사전등록 §2-3 의 규칙을 그대로 옮긴 것이다.
#:   ㄱ 코드가 액션 날짜 **이전으로 자르는 것이 원문에 보인다**  → PRE
#:   ㄴ 액션 날짜·기간·계획 텍스트의 **결정론적 함수**            → PRE
#:   ㄷ 계획서·계약서 원문에 속한 열(문서 근거)                   → PRE
#:   ㄹ 값·출처가 **액션 시작 뒤에 관측된 것**이라고 스스로 말한다 → POST
#:   ㅁ 근거 없음                                                → 🔴 모른다
#: 🔴 **표에 없는 열은 자동으로 「모른다」다**(새 열이 조용히 PRE 가 되는 길을 막는다).
GRADE = {
    # ── A·B 공통/계획 원문 ────────────────────────────────────────────
    "location": ("PRE", "ㄷ", "장소는 계약·기획 시점에 확정 — lab/provenance.py:131-133(노트 276)"),
    "venue": ("PRE", "ㄷ", "〃"),
    "venue_type": ("PRE", "ㄷ", "〃"),
    "neighborhood": ("PRE", "ㄷ", "〃"),
    "city": ("PRE", "ㄷ", "〃"),
    "multi_store": ("PRE", "ㄷ", "〃"),
    "area_pyeong": ("PRE", "ㄷ", "〃"),
    "scale": ("PRE", "ㄷ", "〃 — 계약 매장 수 · lab/provenance.py:141 pop_stores=PRE"),
    "fee_structure": ("PRE", "ㄷ", "계약 조건"),
    "brand_requirements": ("PRE", "ㄷ", "계약 조건"),
    "season": ("PRE", "ㄴ", "기간의 결정론적 함수"),
    "capacity": ("PRE", "ㄴ", "ingest/derive_features.py:98 capacity_upgrade — 입력 blob 이 "
                             "intervention+conditions(derived 제외)뿐"),
    # ── derived 하위 (열별로 따로 판정한다) ───────────────────────────
    "derived.ip_history": ("PRE", "ㄱ", "ingest/derive_features.py:130 `e[0] < open_from`"),
    "derived.competition": ("PRE", "ㄱ", "ingest/competition.py:136-138 `s.open < d <= s.close` · "
                                         "`s.close < d` · lab/provenance.py:134"),
    "derived.pnl_pre": ("PRE", "ㄱ", "ingest/pnl_features.py:73-76 cutoff=오픈월 1일, "
                                     "`period_start < cutoff`. 🔴 티처 #82 는 '사후 파생으로 "
                                     "**보인다**'고 했는데 코드는 앞으로 자른다"),
    "derived.calendar": ("PRE", "ㄴ", "ingest/calendar_features.py:73 calendar_features(from,to)"),
    "derived.duration": ("PRE", "ㄴ", "ingest/derive_features.py:80 duration_features(from,to) · "
                                      "lab/provenance.py:139-140 pop_wkend·pop_holid=PRE"),
    # ── 사후 ──────────────────────────────────────────────────────────
    "demand_signals": ("POST", "ㄹ", "ingest/apply_external_labels.py:75-78 — '역검색 외부 보도"
                                     "(2026-07-27)' 이고 값이 「행사 시작 1시간 전 대기 행렬」·"
                                     "「7000장 2분 만에 조기 마감」 = **행사 중/후 관측**"),
    # ── 모른다 ────────────────────────────────────────────────────────
    "venue_knowledge": ("모른다", "ㅁ", "ingest/venue_knowledge.py 는 누출 차단 설계를 "
                                      "docstring 에 적는다(장소 문자열만 질의). 그러나 "
                                      "**관측 시각이 없고**(태깅 2026-07-28) 코드에 액션 날짜 "
                                      "컷이 없다 → 내 사전등록 규칙으로는 ㅁ. 🔴 '없다'가 "
                                      "아니라 '못 가른다'"),
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dir_digest(d: str) -> dict:
    """🔴 입력 sha256 을 **실제로 계산한다**(942 는 sha() 를 정의만 하고 호출 0회였다).

    디렉터리마다 `sha256(파일명 + 파일sha)` 을 정렬 순으로 이어 다시 sha256 한다.
    """
    h = hashlib.sha256()
    n = 0
    for f in sorted((ROOT / d).glob("*.json")):
        h.update(f.name.encode())
        h.update(sha(f).encode())
        n += 1
    return {"파일": n, "sha256(파일명+파일sha 이어붙임)": h.hexdigest()}


def _nonempty(v) -> bool:
    """942 의 `_nonempty` 와 **글자 그대로 같은 뜻**이어야 대조가 성립한다."""
    if v is None:
        return False
    if isinstance(v, (str, list, dict, tuple)) and len(v) == 0:
        return False
    return True


def dig(r: dict, path):
    cur = r
    for k in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def a_time(r: dict, fam: str) -> bool:
    """🔴 **이 사이클의 수리 그 자체.** a = 액션의 **시점**이 있다."""
    return _nonempty(dig(r, A_TIME_PATH[fam]))


def s_moved(r: dict, fam: str, s_old_C, drop_period: bool = True) -> bool:
    """🔴 `period_*` 를 뺀 `s`. A·B 는 conditions 에서 기간 열을 지우고 본다.

    🔴 `drop_period=False` 로 부르면 **기간 열을 그대로 둔 채** 「값이 있다」만 본다.
    942 의 `s_of` 는 `_nonempty(dict)` 라 **키가 하나라도 있으면** 참이었다 —
    즉 942→943 의 차는 ①키→값 ②기간 열 제거, **둘**이다.
    이 인자가 그 둘을 갈라 준다(안 가르면 어느 쪽이 s 를 줄였는지 모른다).
    """
    if fam == "C_아이돌(outcome 없음)":
        return s_old_C(r)
    c = r.get("conditions")
    if not isinstance(c, dict):
        return _nonempty(c)
    return any(_nonempty(v) for k, v in c.items()
               if not (drop_period and k in PERIOD_KEYS))


def grade_of(key: str) -> tuple:
    """표에 없으면 🔴 **모른다**. (새 열이 조용히 PRE 가 되는 길을 막는다.)

    🔴🔴 **이 함수는 틀렸다 — 노트 944 가 고쳤다(티처 #83 C1).**

    **열 이름만** 받는데 같은 러너의 `colcnt`(:196)는 이미 `(fam, key)` 로 센다 —
    **한 검출기, 두 스키마**(942 의 병)를 그것을 고치는 러너가 자기 판정표에 남겼다.
    실제로 `GRADE["capacity"]=PRE`(:81)의 근거 `derive_features.py:98` 은
    **A 계열 경로(:150-152)에만 참**이고, B 계열은 `:170-172` 에서
    `blob = json.dumps(iv) + str(r.get("notes"))` 로 **행사 뒤 보도 요약**을 먹는다.

    고친 뒤: **모른다 90 → 260**(분모 A+B 1,054 · B `capacity` 170 이 옮겨 간다).
    PRE 1,053 · POST 22 는 안 움직인다.

    🔴 **정본은 `runners/out944_famgrade.py` 의 `grade_new(fam, key)` 다.**
    이 함수는 **동작을 안 바꾼다** — `runners/out943_axis.json` 이 동결물이고
    944 의 배선 검사가 그 json 을 재현하는 데 이 함수를 쓴다. 고치면 동결물이 깨진다.
    새로 세려면 944 의 러너를 써라.
    """
    return GRADE.get(key, ("모른다", "ㅁ", "🔴 판정표에 없는 열 — 안 가른 것이다(조항 59)"))


def main() -> dict:
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # ── ㄱ 배선 검사: 942 의 함수를 **import 해서 호출**한다 ──────────────
    from runners.out942_stock import (a_of as a_942, s_of as s_942,   # noqa: PLC0415
                                      o_new as o_942, family as fam_942)

    n = 0
    fam_c: Counter = Counter()
    per: dict = {}
    # 고치기 전(942)
    a_old = s_old = o_n = full_old = 0
    # 고친 뒤(943)
    a_new = s_new = full_new = o_and_time = 0
    s_val_only = 0        # 🔴 키→값 만 고치고 기간 열은 **그대로 둔** s (분해용)
    s_only_period = []    # 기간 열 제거 **때문에** 떨어진 레코드
    fam_a_old: Counter = Counter()
    fam_a_new: Counter = Counter()
    fam_o_time: Counter = Counter()
    # 반증 조건 3 — 계열이 엇갈린 경로를 갖는가
    cross = {"A 에 평평한 period_from": 0, "B 에 중첩 period.from": 0}
    # ㄹ 열 판정
    colcnt: Counter = Counter()          # (계열, 열) → 값 있는 레코드 수
    bucket_rec: Counter = Counter()      # 통 → 그 통의 열을 하나라도 가진 레코드 수
    pre_per_rec: Counter = Counter()     # PRE 열 개수 분포
    unknown_keys: Counter = Counter()
    a_time_missing: Counter = Counter()  # 시점 없는 레코드가 어느 디렉터리인가

    for d in REC_DIRS:
        p = per.setdefault(d, {"파일": 0, "계열": Counter(),
                               "a(942·칸 존재)": 0, "a(943·시점)": 0,
                               "s(942)": 0, "s(943·period 뺌)": 0,
                               "o(942 새 검출기)": 0, "o∧a(시점)": 0,
                               "a·s·o(942)": 0, "a·s·o(943)": 0})
        for f in sorted((ROOT / d).glob("*.json")):
            try:
                r = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(r, dict):
                continue
            n += 1
            p["파일"] += 1
            fam = fam_942(r)
            fam_c[fam] += 1
            p["계열"][fam] += 1

            ao = a_942(r, fam)
            so = s_942(r, fam)
            ov, _f2, _hit = o_942(r)
            an = a_time(r, fam)
            sn = s_moved(r, fam, lambda rr: s_942(rr, "C_아이돌(outcome 없음)"))
            sv = s_moved(r, fam, lambda rr: s_942(rr, "C_아이돌(outcome 없음)"),
                         drop_period=False)
            s_val_only += sv
            if sv and not sn:
                s_only_period.append(str(f.relative_to(ROOT)))

            a_old += ao; s_old += so; o_n += ov
            a_new += an; s_new += sn
            full_old += bool(ao and so and ov)
            full_new += bool(an and sn and ov)
            o_and_time += bool(ov and an)
            fam_a_old[fam] += ao
            fam_a_new[fam] += an
            fam_o_time[fam] += bool(ov and an)
            p["a(942·칸 존재)"] += ao
            p["a(943·시점)"] += an
            p["s(942)"] += so
            p["s(943·period 뺌)"] += sn
            p["o(942 새 검출기)"] += ov
            p["o∧a(시점)"] += bool(ov and an)
            p["a·s·o(942)"] += bool(ao and so and ov)
            p["a·s·o(943)"] += bool(an and sn and ov)
            if not an:
                a_time_missing[d + " · " + fam] += 1

            c = r.get("conditions")
            if isinstance(c, dict):
                if fam.startswith("A") and _nonempty(c.get("period_from")):
                    cross["A 에 평평한 period_from"] += 1
                if fam.startswith("B") and _nonempty(dig(r, ("conditions", "period", "from"))):
                    cross["B 에 중첩 period.from"] += 1
                seen = set()
                npre = 0
                for k, v in c.items():
                    if k in PERIOD_KEYS:
                        colcnt[(fam, k + "  → a 로 옮김")] += _nonempty(v)
                        continue
                    if k == "derived" and isinstance(v, dict):
                        for k2, v2 in v.items():
                            key = "derived." + k2
                            g, src, _why = grade_of(key)
                            colcnt[(fam, key + f"  [{g}·{src}]")] += _nonempty(v2)
                            if _nonempty(v2):
                                seen.add(g)
                                npre += (g == "PRE")
                                if g == "모른다":
                                    unknown_keys[key] += 1
                        continue
                    g, src, _why = grade_of(k)
                    colcnt[(fam, k + f"  [{g}·{src}]")] += _nonempty(v)
                    if _nonempty(v):
                        seen.add(g)
                        npre += (g == "PRE")
                        if g == "모른다":
                            unknown_keys[k] += 1
                for g in seen:
                    bucket_rec[g] += 1
                pre_per_rec[npre] += 1

    for v in per.values():
        v["계열"] = dict(v["계열"])

    # ── 스탬프 ──────────────────────────────────────────────────────────
    inputs = {d: dir_digest(d) for d in REC_DIRS}
    frozen = {p: sha(ROOT / p) for p in
              ("runners/out941_sao.json", "runners/out942_stock.json",
               "runners/out942_schema_census.json")
              if (ROOT / p).exists()}
    code = {p: sha(ROOT / p) for p in
            ("runners/out943_axis.py", "runners/out942_stock.py",
             "runners/out941_sao.py")}

    res = {
        "노트": 943, "레인": "수리",
        "무엇": "a 를 「시점이 붙은 액션」으로 다시 정의하고 D1 을 다시 센다 (티처 #82 C1·C2)",
        "사전등록": "docs/prereg_943_actiontime.md (커밋 b576f7768 · 측정 전)",
        "🔴 스탬프(루프 v3.2 — git HEAD 안 쓴다)": {
            "시작 시각": t_start,
            "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256(D1 디렉터리별)": inputs,
            "입력 sha256(동결 산출물)": frozen,
            "코드 sha256": code,
        },
        "🔴 조항 60 — 명령·범위": {
            "명령": "python3 runners/out943_axis.py",
            "범위": list(REC_DIRS),
            "🔴 인덱스와 작업 트리를 섞지 않았다": "파일 시스템의 작업 트리만 읽는다",
        },
        "🔴 안 부른 자": "판 ρ · 문턱 0.00353 — 이 사이클은 예측 성능을 안 잰다",

        "🔴 분모 D1(파일)": n,
        "계열 분포": dict(fam_c),
        "🔴 합 == 분모": sum(fam_c.values()) == n,

        "🔴 ㄱ 배선 검사 — 942 의 함수를 import 해서 호출한 값(고치기 전)": {
            "a(942)": a_old, "s(942)": s_old, "o(942 새 검출기)": o_n,
            "a·s·o(942)": full_old,
            "🔴 942 산출물과 같은가": None,   # 아래에서 채운다
        },

        "🔴 ㄴ·ㄷ 고치기 전/후 나란히": {
            "a — 942(intervention 칸 존재)": a_old,
            "a — 943(액션 **시점**)": a_new,
            "a 차": a_new - a_old,
            "s — 942(conditions **칸**이 있다)": s_old,
            "s — 943ㄱ(칸→**값**만 고침 · 기간 열은 그대로)": s_val_only,
            "s — 943ㄴ(거기서 period_* 를 a 로 옮김)": s_new,
            "s 차(942→943 전체)": s_new - s_old,
            "🔴 s 차 분해 — ①칸→값": s_val_only - s_old,
            "🔴 s 차 분해 — ②period_* 제거": s_new - s_val_only,
            "🔴 period_* 제거 **때문에** 떨어진 레코드": s_only_period,
            "o — 942 새 검출기(안 건드림)": o_n,
            "o ∧ a(시점)": o_and_time,
            "a·s·o — 942": full_old,
            "a·s·o — 943": full_new,
            "a·s·o 차": full_new - full_old,
        },
        "계열별 a(942/943)": {k: {"942": fam_a_old[k], "943": fam_a_new[k]} for k in fam_c},
        "계열별 o∧a(시점)": dict(fam_o_time),
        "🔴 시점 없는 레코드(어디에 몰리나)": dict(a_time_missing.most_common()),
        "디렉터리별": per,

        "🔴 반증 조건 3 — 계열 경로가 엇갈리나(둘 다 0 이어야 한다)": cross,

        "🔴 ㄹ conditions 열 단위 판정 (PRE / POST / 모른다)": {
            "판정 규칙": {
                "ㄱ": "코드가 액션 날짜 이전으로 자르는 것이 원문에 보인다 → PRE",
                "ㄴ": "액션 날짜·기간·계획 텍스트의 결정론적 함수 → PRE",
                "ㄷ": "계획서·계약서 원문에 속한 열(문서 근거) → PRE",
                "ㄹ": "값·출처가 액션 시작 뒤 관측이라고 스스로 말한다 → POST",
                "ㅁ": "근거 없음 → 🔴 모른다(‘없다’가 아니다 · 조항 59)",
                "🔴 표에 없는 열": "자동으로 모른다",
            },
            "열별 근거": {k: {"통": v[0], "근거종류": v[1], "근거": v[2]}
                       for k, v in GRADE.items()},
            "🔴 열별 레코드 수(계열 · 값 있는 것만)":
                {f"{f} · {k}": v for (f, k), v in
                 sorted(colcnt.items(), key=lambda x: (x[0][0], -x[1])) if v},
            "🔴 그 통의 열을 하나라도 가진 레코드 수": dict(bucket_rec),
            "🔴 레코드당 PRE 열 개수 분포": dict(sorted(pre_per_rec.items())),
            "🔴 모른다로 센 열(레코드 수)": dict(unknown_keys.most_common()),
        },
    }

    # 동결 산출물과 대조 (배선 검사 — 942 가 **적었던 수**와 내가 **다시 부른 값**)
    fz = ROOT / "runners/out942_stock.json"
    if fz.exists():
        z = json.loads(fz.read_text())["ㄴ·ㄷ D1 재고(옛/새 나란히)"]
        res["🔴 ㄱ 배선 검사 — 942 의 함수를 import 해서 호출한 값(고치기 전)"][
            "🔴 942 산출물과 같은가"] = {
            "942 가 적은 a": z["a 값 있음"], "지금 부른 a": a_old,
            "942 가 적은 s": z["s 값 있음"], "지금 부른 s": s_old,
            "942 가 적은 o(새)": z["🔴 o 값 있음 — 새 검출기(942)"], "지금 부른 o": o_n,
            "942 가 적은 a·s·o(새)": z["🔴 a·s·o 셋 다 — 새"], "지금 부른 a·s·o": full_old,
            "🔴 넷 다 같은가": (z["a 값 있음"] == a_old and z["s 값 있음"] == s_old
                          and z["🔴 o 값 있음 — 새 검출기(942)"] == o_n
                          and z["🔴 a·s·o 셋 다 — 새"] == full_old),
        }

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
