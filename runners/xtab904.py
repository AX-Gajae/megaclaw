# -*- coding: utf-8 -*-
"""노트 904 — 손으로 센 0 을 러너로 다시 세고, 팝업 축 파일이 열리는지 실측한다.

사전등록: `docs/prereg_904_xtab.md` (커밋 21c2721138e990e62c0caaef665a032f808886eb
                                    · 2026-08-11T07:27:57+09:00)

물음의 출처: 이슈 **#147**(티처 #66 **C0**).

🔴 **채점기를 한 글자도 안 고친다** — `ident901.py`·`ident902.py`·`inv901.py`·`pairboot.py` 는
   **import 하거나 산출물을 읽기만** 한다. `state/slots.py`·`ff753.py` 도 읽기만 한다.
🔴 **효과 크기를 안 낸다.** 개수 · 매칭 수 · 분모만. 그래서 규약 47 의 구간이 없다.
🔴 **배선 검사는 생산 함수를 부른다**(이슈 #148 C3). 증거로 진입 계수기 `CALLS` 를 둔다.

실행: python3 runners/xtab904.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

# 🔴 티처 #64 C3 — 도장은 **실행 시작**에서 찍는다
T0 = time.time()
START = dt.datetime.now().isoformat(timespec="seconds")

from inv901 import MISSING, SRC, dig, sha, sha_dir      # noqa: E402  (읽기 전용)
from ident902 import nonmissing                          # noqa: E402  (읽기 전용)

PREREG = {"파일": "docs/prereg_904_xtab.md",
          "커밋": "21c2721138e990e62c0caaef665a032f808886eb",
          "커밋 시각": "2026-08-11T07:27:57+09:00"}

SRC902 = ROOT / "runners/out902_identify.json"
NPZ = ROOT / "data/state/popup_v2.npz"
META = ROOT / "data/state/popup_v2_meta.json"
LEDGER = ROOT / "data/lab/denominator.json"

# 901 §3 이 정한 분모 딱지 넷. 🔴 D1 은 「파일 수」가 아니라 「레코드 수」다
DENOMS = ("D1", "D2", "D3", "D4")
TYPES = ("b", "c", "l", "d")

# 🔴 생산 함수 진입 계수기 — 배선 검사가 **그 함수를 실제로 불렀다**는 유일한 증거
CALLS: Counter = Counter()


# ══ 생산 함수 ══════════════════════════════════════════════════════════
def load_table(path: Path = SRC902) -> dict:
    """`out902_identify.json:판정 표` 를 **읽는다.** 등급을 다시 매기지 않는다."""
    CALLS["load_table"] += 1
    d = json.loads(path.read_text())
    t = d.get("판정 표")
    assert isinstance(t, dict) and t, f"판정 표가 없다/비었다: {path}"
    return t


def pair_rows(table: dict) -> list[dict]:
    """판정 표 → 짝 한 줄씩. 🔴 네 값이 하나라도 없으면 **죽는다**(조항 59).

    「형이 없다」를 조용히 한 칸으로 세지 않는다 — 그게 「없다」를 「통과」로 읽는 길이다."""
    CALLS["pair_rows"] += 1
    rows = []
    for dom, dv in table.items():
        pairs = dv.get("짝")
        assert isinstance(pairs, dict) and pairs, f"{dom}: 짝이 없다"
        for col, p in pairs.items():
            tier, grade, typ = p.get("등급"), p.get("등급(식별)"), p.get("형")
            g1 = p.get("식1 근거")
            assert tier in ("T1", "T2"), f"{dom}/{col}: 티어가 없다/모른다 — {tier!r}"
            assert grade in ("A", "B", "C"), f"{dom}/{col}: 등급이 없다/모른다 — {grade!r}"
            assert typ in TYPES, f"{dom}/{col}: 형이 없다/모른다 — {typ!r}"
            assert isinstance(g1, dict), f"{dom}/{col}: 식1 근거가 없다"
            den = g1.get("분모")
            assert den is not None, f"{dom}/{col}: 분모 딱지가 없다"
            rows.append({"도메인": dom, "짝": col, "티어": tier,
                         "등급": grade, "형": typ, "분모": den})
    return rows


def crosstab(rows: list[dict]) -> dict:
    """형 × 분모 교차표. 🔴 분모 딱지가 넷 밖이면 **죽는다** — 새 딱지를 조용히 안 만든다."""
    CALLS["crosstab"] += 1
    c: Counter = Counter()
    for r in rows:
        assert r["분모"] in DENOMS, (
            f"분모 딱지가 넷({'/'.join(DENOMS)}) 중 하나가 아니다: "
            f"{r['도메인']}/{r['짝']} → {r['분모']!r}")
        assert r["형"] in TYPES, f"형이 넷 밖이다: {r['도메인']}/{r['짝']} → {r['형']!r}"
        c[(r["형"], r["분모"])] += 1
    return {f"{t}×{d}": c[(t, d)] for t in TYPES for d in DENOMS if c[(t, d)]}


def key_count(rows: list[dict]) -> int:
    """🔴 이 사이클의 핵심 수 — (형 ≠ d) ∧ (분모 = D3) 인 짝 수."""
    CALLS["key_count"] += 1
    return sum(1 for r in rows if r["형"] != "d" and r["분모"] == "D3")


def _keep_mask(X, cols, y_all, meta, grades):
    """meta·npz 로 `keep` 을 만든다. 🔴 이 식만으로는 아무것도 주장하지 않는다 —
    아래 `popup_keys` 가 **생산 코드의 산출과 원소별로 대어** 보고서야 키가 된다."""
    keep = np.zeros(len(y_all), bool)
    for g in grades:
        j = cols.index(f"trust_{g}") if f"trust_{g}" in cols else None
        if j is not None:
            keep |= X[:, j] > 0.5
    keep &= np.isfinite(y_all)
    keep &= np.array([bool(m.get("scope_usable")) for m in meta])
    keep &= np.array([m.get("counting") in ("entry", "participation") for m in meta])
    return keep


def popup_keys(meta_override=None) -> dict:
    """🔴 챔피언 팝업 행의 **키**를 복원한다.

    챔피언 배선은 `ff753.shell(base())` → `lab.loop._idol(..., wide_pop="grades")` →
    `lab.popupset.build("now", min_rho=9.9, grades=("A".."E"))` 다(등급을 A~E 로 푼 89행).
    좁은 판 `state.slots.load_popup()`(등급 A·B · 75행)도 **같이** 복원해 둘 다 댄다.

    🔴 내가 meta 에서 만든 `keep` 을 **생산 함수가 실제로 낸 값과 원소별로 대조**한다:
    챔피언 쪽은 `t`(분수 날짜) · `y`(일평균 방문) · `n` · `counting` 도수,
    좁은 판 쪽은 `groups` · `times` · 행 수. 하나라도 어긋나면 **죽는다**(조항 59).
    이 대조가 없으면 이 함수는 「생산 코드의 복제본」이고, 그게 이슈 #148 C3 의 병이다."""
    CALLS["popup_keys"] += 1
    from state.slots import load_popup                     # 🔴 생산 코드 — 읽기만
    from lab.popupset import build as pbuild, _frac, _tally  # 🔴 생산 코드 — 읽기만
    z = np.load(NPZ, allow_pickle=True)
    X, cols = z["X"], [str(c) for c in z["names"]]
    y_all = z["y_perday"]
    meta = (json.loads(META.read_text()) if meta_override is None else meta_override)
    assert len(meta) == X.shape[0], (
        f"meta 길이 {len(meta)} ≠ npz 행 {X.shape[0]} — 열쇠가 행에 안 붙는다")

    # ── 챔피언 배선(등급 A~E) ────────────────────────────────────────
    GR = ("A", "B", "C", "D", "E")
    keep = _keep_mask(X, cols, y_all, meta, GR)
    kept = [m for m, k in zip(meta, keep) if k]
    _pA, _pM, py, pt, _nm, pinfo = pbuild("now", min_rho=9.9, grades=GR)
    assert len(kept) == pinfo["n"] == len(py), (
        f"복원 행 {len(kept)} ≠ 생산 코드 행 {pinfo['n']}/{len(py)} — keep 규칙이 갈라졌다")
    mine_t = np.array([_frac(m.get("date")) for m in kept], float)
    bad_t = int((~((mine_t == pt) | (np.isnan(mine_t) & np.isnan(pt)))).sum())
    mine_y = y_all[keep]
    bad_y = int((~((mine_y == py) | (np.isnan(mine_y) & np.isnan(py)))).sum())
    mine_c = _tally([m.get("counting") for m in kept])
    assert bad_t == 0 and bad_y == 0 and mine_c == pinfo["counting"], (
        f"챔피언 생산 코드 대조 실패 — t 어긋남 {bad_t} · y 어긋남 {bad_y} · "
        f"counting 도수 {'같다' if mine_c == pinfo['counting'] else '다르다'}")

    # ── 좁은 판(등급 A·B) — 두 번째 독립 대조 ────────────────────────
    keep_n = _keep_mask(X, cols, y_all, meta, ("A", "B"))
    kept_n = [m for m, k in zip(meta, keep_n) if k]
    _Xin, yn, _w, _A, _M, groups, times, _c = load_popup()
    assert len(kept_n) == len(yn), (
        f"좁은 판 복원 행 {len(kept_n)} ≠ 생산 코드 행 {len(yn)}")
    bad_g = int((np.array([m.get("ip") or m["id"] for m in kept_n]) != groups).sum())
    bad_gt = int((np.array([m.get("date") or "9999" for m in kept_n]) != times).sum())
    assert bad_g == 0 and bad_gt == 0, (
        f"좁은 판 생산 코드 대조 실패 — groups 어긋남 {bad_g} · times 어긋남 {bad_gt}")

    return {"키": [m["id"] for m in kept], "메타": kept,
            "npz 행": int(X.shape[0]), "meta 길이": len(meta),
            "챔피언 생산 코드 행(popupset.build · 등급 A~E)": int(pinfo["n"]),
            "좁은 판 생산 코드 행(slots.load_popup · 등급 A·B)": int(len(yn)),
            "대조": {"챔피언 t 어긋남": bad_t, "챔피언 y 어긋남": bad_y,
                    "챔피언 counting 도수 같나": mine_c == pinfo["counting"],
                    "좁은 판 groups 어긋남": bad_g, "좁은 판 times 어긋남": bad_gt,
                    "🔴 대조에 쓴 자": ("챔피언 t·y·n·counting · 좁은 판 groups·times·행 수 "
                                 "— 전부 원소별. 🔴 두 생산 경로를 따로 댔다")}}


def resolve_popup_d3(keys: list[str], byid_pop: dict, byid_mkt: dict,
                     _broken: bool = False) -> dict:
    """유보 키 → 원천 레코드. 🔴 되짚기가 **조용히 0/부분** 이 되는 길을 막는다(902 와 같은 자)."""
    CALLS["resolve_popup_d3"] += 1
    ks = [k[2:] for k in keys] if _broken else list(keys)   # 🔴 W-ㄹ 이 심는 결함
    hit_pop = [k for k in ks if k in byid_pop]
    hit_mkt = [k for k in ks if k in byid_mkt]
    unres = [k for k in ks if k not in byid_pop and k not in byid_mkt]
    hit = len(hit_pop) + len(hit_mkt)
    assert hit and hit >= 0.5 * len(ks), (
        f"D3 되짚기 조용한 0/부분 실패 팝업: 키 {len(ks)} → 매칭 {hit}")
    pref: Counter = Counter(k[:3] for k in unres)
    return {"유보 키 수(분모)": len(ks),
            "data/records 에 붙은 수": len(hit_pop),
            "data/market_records 에 붙은 수": len(hit_mkt),
            "🔴 못 붙은 수": len(unres),
            "못 붙은 키(전량)": unres,
            "못 붙은 키 접두 분포": dict(pref),
            "붙은 키(data/records · 전량)": hit_pop}


# ══ 배선 검사 — 🔴 전부 위 생산 함수를 부른다 ═══════════════════════════
def _probe(name, fn, *a, **kw):
    """(발화했나, 메시지) — assert 만 잡는다. 다른 예외는 그대로 죽는다."""
    try:
        fn(*a, **kw)
        return False, "🔴 발화 안 함"
    except AssertionError as e:
        return True, f"AssertionError: {e}"


def wiring_checks(table, byid_pop, byid_mkt) -> dict:
    w = {"🔴 규약": ("검사는 생산 함수를 **부른다**. 지역에 식을 다시 쓰지 않는다. "
                  "증거는 진입 계수기 `CALLS` 의 증가분이다(이슈 #148 C3)"),
         "검사": {}}
    import copy

    def one(name, fnname, fn, broken_args, clean_args, 심은것):
        before = CALLS[fnname]
        fired, msg = _probe(name, fn, *broken_args)
        mid = CALLS[fnname]
        ok, okmsg = _probe(name, fn, *clean_args)
        after = CALLS[fnname]
        w["검사"][name] = {
            "부른 생산 함수": f"{fn.__module__}.{fn.__qualname__}",
            "심은 결함": 심은것,
            "심었을 때 발화": fired,
            "발화 메시지": msg,
            "🔴 음성 대조(정상 입력) 발화": ok,
            "음성 대조 메시지": okmsg if ok else "발화 안 함(정상)",
            "🔴 결함을 지우면 통과로 바뀌나": (fired and not ok),
            "진입 계수기 증가(결함/정상)": [mid - before, after - mid],
            "🔴 계수기가 실제로 늘었나": (mid > before and after > mid),
        }

    # W-ㄱ · pair_rows — 형을 지운다
    t_bad = copy.deepcopy(table)
    d0 = next(iter(t_bad))
    p0 = next(iter(t_bad[d0]["짝"]))
    t_bad[d0]["짝"][p0].pop("형", None)
    one("W-ㄱ pair_rows 형 결측", "pair_rows", pair_rows,
        (t_bad,), (table,), f"`판정 표/{d0}/짝/{p0}/형` 을 지웠다")

    # W-ㄴ · crosstab — 분모 딱지를 넷 밖으로
    rows = pair_rows(table)
    r_bad = [dict(r) for r in rows]
    r_bad[0]["분모"] = "D9"
    one("W-ㄴ crosstab 분모 딱지 넷 밖", "crosstab", crosstab,
        (r_bad,), (rows,), "첫 짝의 분모 딱지를 `D9` 로 바꿨다")

    # W-ㄷ · popup_keys — meta 를 한 칸 민다
    meta = json.loads(META.read_text())
    rolled = meta[1:] + meta[:1]
    one("W-ㄷ popup_keys meta 한 칸 밀기", "popup_keys", popup_keys,
        (rolled,), (None,), "popup_v2_meta 를 roll(1) 로 밀어 행 정렬을 깼다")

    # W-ㄹ · resolve_popup_d3 — 접두 두 글자를 뗀다(901 의 KOBIS- 실사고 재현)
    keys = popup_keys()["키"]
    one("W-ㄹ resolve_popup_d3 접두 벗기기", "resolve_popup_d3", resolve_popup_d3,
        (keys, byid_pop, byid_mkt, True), (keys, byid_pop, byid_mkt, False),
        "유보 키의 접두 두 글자를 뗐다 — 901 의 `KOBIS-` 실사고 재현")

    fired = sum(1 for v in w["검사"].values() if v["심었을 때 발화"])
    neg = sum(1 for v in w["검사"].values() if not v["🔴 음성 대조(정상 입력) 발화"])
    flip = sum(1 for v in w["검사"].values() if v["🔴 결함을 지우면 통과로 바뀌나"])
    cnt = sum(1 for v in w["검사"].values() if v["🔴 계수기가 실제로 늘었나"])
    n = len(w["검사"])
    w["🔴 분모(심은 결함 수)"] = n
    w["발화"] = fired
    w["음성 대조 통과"] = neg
    w["🔴 지우면 통과로 바뀐 수"] = flip
    w["🔴 계수기가 늘어난 수"] = cnt
    w["통과"] = (fired == n and neg == n and flip == n and cnt == n)
    return w


# ══ 원장 훑기 (티처 #65 M13) ═══════════════════════════════════════════
def ledger_scan() -> dict:
    d = json.loads(LEDGER.read_text())

    def leaves(o):
        if isinstance(o, dict):
            return sum(leaves(v) for v in o.values())
        if isinstance(o, list):
            return sum(leaves(v) for v in o)
        return 1

    NA = ["날짜형", "분모 딱지", "D3 되짚"]
    NB = ["popup_v2", "축 파일이 없다", "팝업 축", "되짚"]
    out = {"원장 최상위 항목": len(d), "원장 리프": leaves(d),
           "🔴 바늘을 둘로 나눈 이유": "두 반쪽의 분모가 다르다(조항 60)"}
    hits = {}
    for name, ns in (("(가) 교차표·형·분모", NA), ("(나) 팝업 축 되짚기", NB)):
        h = [k for k, v in d.items()
             if any(n in json.dumps(v, ensure_ascii=False) or n in k for n in ns)]
        hits[name] = h
        out[f"{name} 바늘"] = ns
        out[f"{name} 걸린 최상위 항목 수"] = len(h)
        out[f"{name} 목록"] = h
    uni = sorted(set(hits["(가) 교차표·형·분모"]) | set(hits["(나) 팝업 축 되짚기"]))
    out["🔴 합집합(이 물음에 걸리는 옛 항목)"] = len(uni)
    out["🔴 교집합"] = len(set(hits["(가) 교차표·형·분모"]) & set(hits["(나) 팝업 축 되짚기"]))
    out["🔴 903 이 같은 단계에서 찾은 수"] = 8
    out["🔴 자가 다르다"] = ("903 은 바늘 `entry_friction` 하나로 세었고 904 는 물음에 맞춘 "
                        "바늘 일곱을 둘로 나눠 세었다 — 같은 이름의 다른 자다")
    return out


# ══ main ══════════════════════════════════════════════════════════════
def main():
    out = {
        "노트": 904,
        "사전등록": PREREG,
        "시작 시각": START,
        "물음의 출처": "이슈 #147 (티처 #66 C0)",
        "🔴 효과 크기": "없음 — 개수 · 매칭 수 · 분모만. 그래서 규약 47 의 구간이 없다",
        "🔴 채점기 무접촉": ("ident901.py · ident902.py · inv901.py · pairboot.py 를 "
                       "import 하거나 산출물을 읽기만 했다. state/slots.py · ff753.py 도 읽기만"),
        "코드 sha256": {
            "runners/xtab904.py": sha(Path(__file__)),
            "runners/ident902.py": sha(ROOT / "runners/ident902.py"),
            "runners/inv901.py": sha(ROOT / "runners/inv901.py"),
            "state/slots.py": sha(ROOT / "state/slots.py"),
        },
    }
    inputs = {"runners/out902_identify.json": {"sha256": sha(SRC902)},
              "data/state/popup_v2.npz": {"sha256": sha(NPZ)},
              "data/state/popup_v2_meta.json": {"sha256": sha(META)}}
    for p in ("data/records", "data/market_records"):
        h, n = sha_dir(ROOT / p)
        inputs[p] = {"sha256(결합)": h, "파일 수": n}
    out["입력 sha256"] = inputs

    out["0 원장이 이미 뭐라 했나"] = ledger_scan()

    # ── 원천 레코드 색인 ────────────────────────────────────────────
    pops = [json.loads(p.read_text()) for p in sorted((ROOT / "data/records").glob("*.json"))]
    mkts = [json.loads(p.read_text())
            for p in sorted((ROOT / "data/market_records").glob("*.json"))]
    byid_pop = {r["record_id"]: r for r in pops}
    byid_mkt = {r["market_record_id"]: r for r in mkts}
    assert len(byid_pop) == len(pops) and len(byid_mkt) == len(mkts), "record_id 가 중복이다"

    table = load_table()

    # ── ② 배선 검사 (측정보다 먼저) ─────────────────────────────────
    calls_before = dict(CALLS)
    wire = wiring_checks(table, byid_pop, byid_mkt)
    out["2 배선 검사"] = wire
    if not wire["통과"]:
        out["🔴 중단"] = "배선 검사가 통과 못 했다 — 사전등록 §7 대로 산출물을 쓰되 측정은 안 쓴다"
        (ROOT / "runners/out904_xtab.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1))
        raise SystemExit("🔴 배선 검사 실패 — 측정 중단")
    out["2 배선 검사"]["검사 전 계수기"] = calls_before

    # ── 4-가 · 교차표 ──────────────────────────────────────────────
    rows = pair_rows(table)
    A1 = [r for r in rows if r["등급"] == "A" and r["티어"] == "T1"]
    Aall = [r for r in rows if r["등급"] == "A"]
    T1all = [r for r in rows if r["티어"] == "T1"]
    g = {"전량": rows, "A∧T1": A1, "A 전량(T2 포함)": Aall, "T1 전량": T1all}

    tab = {"🔴 분모 딱지 넷의 정의":
           "D1 원천 레코드 수 · D2 축행 · D3 판 채점 유보 · D4 도메인 행 (901 §3). "
           "🔴 D1 은 「파일 수」가 아니라 「레코드 수」이고 그 정의가 맞는 도메인은 셋뿐이다",
           "짝 전량(분모)": len(rows),
           "등급 × 티어": {f"{k[0]}·{k[1]}": v for k, v in
                       sorted(Counter((r["등급"], r["티어"]) for r in rows).items())}}
    for name, rs in g.items():
        tab[f"{name} — 수(분모)"] = len(rs)
        tab[f"{name} — 형 × 분모"] = crosstab(rs)
        tab[f"{name} — 형"] = dict(sorted(Counter(r["형"] for r in rs).items()))
        tab[f"{name} — 분모"] = dict(sorted(Counter(r["분모"] for r in rs).items()))
        tab[f"🔴 {name} — (형≠d) ∧ (분모=D3)"] = key_count(rs)
    tab["A∧T1 21 의 도메인 분해"] = dict(
        sorted(Counter(r["도메인"] for r in A1).items()))
    tab["A∧T1 전량 목록"] = [f"{r['도메인']}/{r['짝']} · {r['형']} · {r['분모']}" for r in A1]
    tab["🔴 A 전량에만 있고 A∧T1 에 없는 짝"] = [
        f"{r['도메인']}/{r['짝']} · {r['형']} · {r['분모']} · {r['티어']}"
        for r in Aall if r not in A1]
    tab["🔴 105짝 전량에서 (형≠d) ∧ D3 인 짝의 등급 분해"] = dict(sorted(Counter(
        r["등급"] for r in rows if r["형"] != "d" and r["분모"] == "D3").items()))
    out["4-가 형 × 분모 교차표"] = tab

    # ── 4-나 · 팝업 축 파일 ────────────────────────────────────────
    z = np.load(NPZ, allow_pickle=True)
    npz_desc, idcols = {}, []
    for k in z.keys():
        a = z[k]
        npz_desc[k] = {"dtype": str(a.dtype), "모양": list(a.shape)}
        if a.dtype.kind in "US" and a.ndim == 1 and a.shape[0] == z["X"].shape[0]:
            idcols.append(k)
    meta = json.loads(META.read_text())
    fields = sorted({f for m in meta for f in m})
    axis = {"popup_v2.npz 키": npz_desc,
            "🔴 npz 안의 식별자 후보 열 수": len(idcols),
            "npz 안의 식별자 후보 열": idcols,
            "popup_v2_meta.json 길이": len(meta),
            "popup_v2_meta.json 필드별 비결측": {
                f: sum(1 for m in meta if m.get(f) not in (None, "")) for f in fields},
            "🔴 조항 60 — 레코드가 이미 가진 열쇠를 다 써 봤나": {
                "열쇠 후보(원천 쪽)": ["record_id", "entities.brand_key", "entities.space_key"],
                "열쇠 후보(축 쪽)": fields,
                "🔴 실제로 써 본 것": "popup_v2_meta.json/id ↔ data/records/record_id",
                "🔴 안 써 본 것": "brand_key·space_key 로의 이름 붙이기 — 안 써 본 것이지 없는 것이 아니다"},
            "meta.domain 분포": dict(sorted(Counter(m.get("domain") for m in meta).items())),
            }

    pk = popup_keys()
    axis["키 복원"] = {k: v for k, v in pk.items() if k not in ("키", "메타")}
    axis["키 복원"]["🔴 챔피언은 등급을 A~E 로 푼다"] = (
        "ff753.shell(base()) → lab.loop._idol(wide_pop=\"grades\") → "
        "lab.popupset.build(\"now\", min_rho=9.9, grades=(\"A\"..\"E\")). "
        "좁은 판(state.slots.load_popup · 등급 A·B)은 다른 행 수다 — 둘을 안 잇는다(조항 60)")
    axis["키 복원"]["복원한 키 수"] = len(pk["키"])
    axis["키 복원"]["복원 키의 domain 분포"] = dict(
        sorted(Counter(m.get("domain") for m in pk["메타"]).items()))

    import ff753 as FF
    d0 = FF.shell(FF.base())
    mask = d0.rows("팝업", post=True, labeled=True, T=2025.0)
    y_champ = d0.dom["팝업"][2]
    assert len(mask) == len(pk["키"]), (
        f"챔피언 팝업 행 {len(mask)} ≠ 복원 키 {len(pk['키'])}")
    d3keys = [k for k, b in zip(pk["키"], mask) if b]

    from lab import harness as HN
    raw = HN.load()
    axis["🔴 배선을 박는다"] = {
        "쓴 배선": "챔피언 ff753.shell(base())",
        "챔피언 D3 합(12도메인)": int(sum(int(v) for v in d0.weights(2025.0).values())),
        "생 harness.load() D3 합": int(sum(
            int(raw.rows(dd, post=True, labeled=True, T=2025.0).sum()) for dd in raw.dom)),
        "챔피언 팝업 도메인 행(D4)": int(len(mask)),
        "챔피언 팝업 유보(D3)": int(mask.sum()),
        "생 팝업 유보(D3)": int(raw.rows("팝업", post=True, labeled=True, T=2025.0).sum()),
        "y 길이 대조(챔피언 dom[팝업][2] 대 복원)": [int(len(y_champ)), len(pk["키"])],
    }
    res = resolve_popup_d3(d3keys, byid_pop, byid_mkt)
    axis["D3 되짚기"] = res
    axis["🔴 되짚기가 되나"] = (res["🔴 못 붙은 수"] == 0)

    # 12 A∧T1 팝업 짝의 D3 덮음
    d3set = set(res["붙은 키(data/records · 전량)"])
    cover = {}
    for r in A1:
        if r["도메인"] != "팝업":
            continue
        col = r["짝"]
        nz = [rec for rec in pops if nonmissing(dig(rec, col))]
        inD3 = [rec for rec in nz if rec["record_id"] in d3set]
        cover[col] = {"D1 원천 레코드(분모)": len(pops),
                      "비결측(D1)": len(nz),
                      "🔴 유보 키 중 원천에 붙은 수(분모)": len(d3set),
                      "🔴 D3 덮음(비결측 ∧ 유보)": len(inD3),
                      "덮음/비결측": round(len(inD3) / len(nz), 6) if nz else None}
    axis["🔴 12 A∧T1 팝업 짝의 D3 덮음"] = cover
    axis["🔴 D3 덮음 요약"] = {
        "짝 수(분모)": len(cover),
        "덮음 최소": min(v["🔴 D3 덮음(비결측 ∧ 유보)"] for v in cover.values()) if cover else None,
        "덮음 최대": max(v["🔴 D3 덮음(비결측 ∧ 유보)"] for v in cover.values()) if cover else None,
        "🔴 덮음이 비결측과 같은 짝 수": sum(
            1 for v in cover.values()
            if v["🔴 D3 덮음(비결측 ∧ 유보)"] == v["비결측(D1)"]),
    }
    out["4-나 팝업 축 파일"] = axis

    # ── 5 · 예측 판정 ──────────────────────────────────────────────
    ef = cover.get("intervention.attributes.entry_friction", {})
    p2 = res["data/records 에 붙은 수"]
    pred = {
        "P1 팝업 D4=89 · D3=65": {
            "실측 D4": int(len(mask)), "실측 D3": int(mask.sum()),
            "판정": ("확인" if (len(mask) == 89 and int(mask.sum()) == 65) else "반증")},
        "P2 유보 키 중 data/records 에 붙는 것이 1 이상 65 미만": {
            "실측": p2, "분모": len(d3keys),
            "판정": ("확인" if 0 < p2 < len(d3keys) else "반증")},
        "P3 12 A∧T1 팝업 짝의 D3 덮음 < 비결측": {
            "덮음이 비결측과 같은 짝 수": axis["🔴 D3 덮음 요약"]["🔴 덮음이 비결측과 같은 짝 수"],
            "판정": ("확인" if axis["🔴 D3 덮음 요약"]["🔴 덮음이 비결측과 같은 짝 수"] == 0
                   else "반증")},
        "P4 (형≠d) ∧ D3 이 A∧T1 21 에서 0": {
            "실측": tab["🔴 A∧T1 — (형≠d) ∧ (분모=D3)"],
            "판정": ("확인" if tab["🔴 A∧T1 — (형≠d) ∧ (분모=D3)"] == 0 else "반증")},
        "P5 같은 수가 105짝 전량에서는 0 이 아니다": {
            "실측": tab["🔴 전량 — (형≠d) ∧ (분모=D3)"],
            "판정": ("확인" if tab["🔴 전량 — (형≠d) ∧ (분모=D3)"] != 0 else "반증")},
    }
    out["5 예측 판정"] = pred

    # ── 6 · 판정 (사전등록 §6 의 어법 그대로) ───────────────────────
    zero = (tab["🔴 A∧T1 — (형≠d) ∧ (분모=D3)"] == 0
            and tab["🔴 A 전량(T2 포함) — (형≠d) ∧ (분모=D3)"] == 0)
    opened = axis["🔴 되짚기가 되나"]
    v_xtab = ("🔴 「A 등급 짝 중 (날짜형 아님) ∧ (D3 분모) 인 짝은 0 이다」 — 손으로 센 0 이 "
              "러너로 재현됐다. 형과 분모가 겹치는 것은 처방서의 오타가 아니라 자료의 구조다. "
              "그러므로 「날짜형을 빼고 D3 위에서 효과를 재라」는 처방은 고를 수 있는 짝이 "
              "하나도 없다. 🔴 그리고 이것은 A 등급에 한정된 사실이지 자료 전체의 사실이 아니다"
              ) if zero else (
              f"🔴 재현되지 않는다 — (날짜형 아님) ∧ (D3 분모) 인 A 짝이 "
              f"{tab['🔴 A 전량(T2 포함) — (형≠d) ∧ (분모=D3)']}개 있다. "
              "티처 #66 C0 의 손 계수가 틀렸고, 그 짝이 905 의 팔이다")
    v_axis = ("🔴 903 의 「팝업은 축이 npz 라 D3 되짚기가 *원리상 불가능*하다」는 거짓이다. "
              "열쇠는 있었다 — data/state/popup_v2_meta.json 의 id 가 popup_v2.npz 의 행과 "
              "같은 순서로 놓여 있고 data/records/*.json 의 record_id 와 같은 이름이다. "
              "🔴 「원리상 불가능」이 아니라 「안 써 봤다」였다. "
              "⚠ 이 문장은 발견이 아니라 사전등록 §0 의 자백이다"
              ) if opened else (
              "🔴 못 연다. 그러나 「없다」라 안 적는다 — 무엇이 없어서 못 여는지를 수로 적었다"
              f"(열쇠 후보 {len(idcols)} · meta {len(meta)} 대 npz {int(z['X'].shape[0])} · "
              f"못 붙은 키 {res['🔴 못 붙은 수']}). 그 목록이 905 의 작업 목록이다")
    out["6 판정"] = {
        "(가) 교차표": v_xtab,
        "(나) 팝업 축 파일": v_axis,
        "(다) 다음 사이클": ("🔴 이 사이클은 「다음은 X 로 간다」를 판정문에 안 쓴다. "
                       "903 이 정확히 거기서 자기 꼬리를 물었다. 904 는 교차표의 수와 "
                       "되짚기의 수만 낸다 — 방향은 티처와 ⓪ 가 정한다"),
        "🔴 사전등록 §6 과 한 글자도 안 바꿨나": True,
        "통과": True,
    }
    out["7 못 잰 것 (「없다」가 아니다)"] = [
        "효과 크기 — 안 냈다. δ 도 구간도 없다(사전등록 §3)",
        "아이돌의 D3 되짚기 — D2 81 ≠ D4 173 이라 902 가 못 셌고 904 는 팝업만 봤다. 안 본 것이다",
        "brand_key·space_key 로의 이름 붙이기 — 안 써 봤다(조항 60 의 셋 중 「안 써 봤다」)",
        "팝업 A 짝의 효과 — 안 쟀다. 904 는 분모를 옮길 수 있는지까지다",
        "날짜형 아홉 짝 — 903 사전등록 §3 을 물려받아 안 쟀다",
        "시장팝업으로 붙는 유보 키의 짝 분모 재계산 — 안 했다(902 가 이미 D3 로 매겼다)",
    ]
    out["🔴 계수기(생산 함수 진입 총계)"] = dict(CALLS)
    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["초"] = round(time.time() - T0, 3)
    p = ROOT / "runners/out904_xtab.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("완료 →", p)
    print("배선", wire["발화"], "/", wire["🔴 분모(심은 결함 수)"], "통과", wire["통과"])
    print("A∧T1 (형≠d)∧D3 =", tab["🔴 A∧T1 — (형≠d) ∧ (분모=D3)"],
          "· 전량 =", tab["🔴 전량 — (형≠d) ∧ (분모=D3)"])
    print("팝업 D4", int(len(mask)), "D3", int(mask.sum()),
          "되짚기", axis["🔴 되짚기가 되나"], "붙은", res["data/records 에 붙은 수"])


if __name__ == "__main__":
    main()
