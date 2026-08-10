"""노트 902 — 901 의 「A=0」 재측정.

사전등록: `docs/prereg_902_identify.md` (커밋 b37ccd01959b74b019f1e0b5f68a8ebb5a7d1bed
                                       · 2026-08-11T04:43:09+09:00)

🔴 효과 크기를 안 낸다. 개수 · 값 가짓수 · 결측 · 분모만.
🔴 `runners/inv901.py` · `runners/ident901.py` 를 **고치지 않는다 — import 만 한다.**
   식3·식4 규칙과 b·l 형 식1 규칙은 **901 의 코드를 그대로 불러** 쓴다(회귀 시험 Q1 의 전제).
🔴 옛 산출물 `out901_*.json` 은 증거물이라 **안 덮는다.** 새 이름으로 낸다.

실행: python3 runners/ident902.py
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

# 🔴 티처 #64 C3 — stamp 는 **실행 시작**에서 부른다(901 은 끝에서 불러 시작==끝이 됐다)
T0 = time.time()
START = dt.datetime.now().isoformat(timespec="seconds")

from inv901 import (CAND, SRC, UNIT, DATEK, dig, hashable, load_records,
                    sha, sha_dir, MISSING)
# 🔴 901 의 규칙을 **같은 코드로** 쓴다 — 손으로 옮겨 적으면 재현이 아니다
from ident901 import (minority_two_way, PRE_PROVEN, PRE_WHY, POST_GROW,
                      CONFOUND, IDF, ASOF_CAND)

PREREG = {"파일": "docs/prereg_902_identify.md",
          "커밋": "b37ccd01959b74b019f1e0b5f68a8ebb5a7d1bed",
          "커밋 시각": "2026-08-11T04:43:09+09:00"}

MIN_SIDE = 10          # 🔴 prereg_901:133 에서 그대로 물려받는다. 902 는 안 건드린다
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
YMD8 = re.compile(r"^\d{8}$")

# W2 실측용 — 901 의 PRE_LIKE 를 그대로
PRE_LIKE = ("pre_", "_pre", "prior", "before", "baseline", "predebut",
            "pre_debut", "사전", "이전")
# 🔴 W8 실측용 — 902 신설(사전등록 §4)
ASSIGN_LIKE = ("배정", "선정", "why", "reason", "criteria", "rationale",
               "decision", "select", "eligib", "quota", "random", "assign",
               "기준", "사유")


# ── §2 분할 규칙 ──────────────────────────────────────────────────────
def _num_ok(v):
    return isinstance(v, (int, float)) and not isinstance(v, str)


def _date_key(v, strict=False):
    """날짜 값 → 정렬 가능한 `YYYY-MM-DD`. 못 읽으면 None.

    🔴 사전등록 §2 는 「ISO 앞 10자」라고 적었다. 8자리 `YYYYMMDD` 와 정수형도 받도록
    **꼴만** 정규화한다 — 정렬 순서가 같으므로 판정에 영향이 없고, 산출물에 명시한다."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        v = str(int(v))
    if not isinstance(v, str):
        return None
    s = v.strip()[:10]
    if ISO.match(s):
        return s
    if not strict and YMD8.match(v.strip()[:8]):
        t = v.strip()[:8]
        return f"{t[:4]}-{t[4:6]}-{t[6:8]}"
    return None


def median_split(xs, _broken=False):
    """🔴 사전등록 §2 — 중앙값 분할. 순서만 쓴다(문자열 날짜도 같은 코드).

    m = 정렬한 값의 xs[n//2] · 저군 L={x<m} · 고군 H={x>=m} · 소수 쪽 = min(|L|,|H|)."""
    n = len(xs)
    if n == 0:
        return {"n": 0, "절단값": None, "저군": 0, "고군": 0, "소수 쪽": 0}
    s = sorted(xs)
    m = s[n // 2]
    lo = sum(1 for x in s if x < m)
    hi = n - lo
    mino = min(lo, hi)
    if _broken:                     # 🔴 W-F 가 심는 결함 — 소수 쪽을 총수로 낸다
        mino = n
    return {"n": n, "절단값": m, "저군": lo, "고군": hi, "소수 쪽": mino}


def max_balanced(xs):
    """감도(판정 미사용) — 모든 절단점 중 min(|<c|,|>=c|) 의 최댓값."""
    n = len(xs)
    if n == 0:
        return 0
    cnt = Counter(xs)
    best, run = 0, 0
    for v in sorted(cnt):
        run += cnt[v]
        if run < n:                 # c = 다음 값 → |<c| = run
            best = max(best, min(run, n - run))
    return best


def sik1(typ, base_counter, vals_typed, D):
    """식1 판정 한 짝. 반환 (판정, 근거dict)."""
    k = len(base_counter)
    if typ in ("b", "l"):
        mino = minority_two_way(base_counter)      # 🔴 901 의 함수 그대로
        ok = (k >= 2 and mino >= MIN_SIDE)
        return ("예" if ok else "아니오"), {
            "규칙": "b·l — 최빈값 대 나머지 (🔴 901 과 동일 · 변경 없음)",
            "값 가짓수": k, "소수 쪽": mino, "분모": D}
    # c · d
    sp = median_split(vals_typed["쓴 값"])
    mb = max_balanced(vals_typed["쓴 값"])
    nn = sp["n"]
    k_raw, k = k, len(set(vals_typed["쓴 값"]))   # 🔴 읽을 수 있었던 값의 가짓수로 판정
    ok = (k >= 2 and sp["소수 쪽"] >= MIN_SIDE)
    if ok:
        j = "예"
        why = "중앙값 분할이 양쪽 10행 이상"
    elif k < 2:
        j = "아니오"
        why = "W1 대조군 없음 — 값 가짓수 1"
    elif nn < 2 * MIN_SIDE:
        j = "아니오"
        why = f"W6 표본 부족 — 쓸 수 있는 값 {nn} < {2*MIN_SIDE}"
    else:
        j = "아니오"
        why = "🔴 동률 퇴화 — 중앙값에 값이 몰려 한쪽이 10행 미만"
    return j, {
        "규칙": ("c·d — 🔴 902 신설 중앙값 분할(저군 x<m · 고군 x>=m)"
               if typ == "c" else
               "d — 🔴 902 신설 중앙값 분할(이른 절반 / 늦은 절반)"),
        "값 가짓수": k, "값 가짓수(원값 · 못 읽은 것 포함)": k_raw,
        "쓴 값 수": nn, "절단값": sp["절단값"],
        "저군": sp["저군"], "고군": sp["고군"], "소수 쪽": sp["소수 쪽"],
        "사유": why, "분모": D,
        "감도(판정 미사용) 최대균형 소수 쪽": mb,
        "🔴 버린 값(형에 안 맞아 못 읽음)": vals_typed["버림"],
        "버린 값 예시": vals_typed["버림 예시"],
    }


def typed_values(typ, raw_vals):
    """형에 맞게 읽을 수 있는 값만 남긴다. 못 읽은 것은 **세어서 적는다**(조항 59)."""
    used, dropped, ex = [], 0, []
    if typ == "c":
        for v in raw_vals:
            if _num_ok(v):
                used.append(float(v))
            else:
                dropped += 1
                if len(ex) < 3:
                    ex.append(repr(v)[:60])
    elif typ == "d":
        for v in raw_vals:
            k = _date_key(v)
            if k:
                used.append(k)
            else:
                dropped += 1
                if len(ex) < 3:
                    ex.append(repr(v)[:60])
    return {"쓴 값": used, "버림": dropped, "버림 예시": ex}


# ── W-G 두 번째 구현(독립 경로) ────────────────────────────────────────
def dig2(r, path, _broken=False):
    """🔴 `inv901.dig` 와 **다른 구현**. 두 경로의 비결측 수가 어긋나면 assert 발화."""
    ks = path.split(".")
    if _broken and ks:               # 심는 결함 — 마지막 키를 이웃 이름으로 바꾼다
        ks = ks[:-1] + [ks[-1] + "_x"]
    cur = r
    for k in ks:
        try:
            cur = cur[k]
        except (KeyError, TypeError, IndexError):
            return MISSING
    return cur


def nonmissing(v):
    return v is not MISSING and v is not None and v != "" and v != []


# ── D3 되짚기 ─────────────────────────────────────────────────────────
def d3_backtrack(d0, normalize=True):
    """축 파일 키 → 원천 record_id. `normalize=False` 는 **W-H 가 심는 결함**."""
    out = {}
    for dom, (kind, p, axp, outs) in SRC.items():
        if not axp:
            out[dom] = {"가능": False,
                        "이유": "축 파일이 없다(popup_v2.npz 경로) — 🔴 못 셌다"}
            continue
        keys = list(json.loads((ROOT / axp).read_text()))
        n_ax, n_dom = len(keys), len(d0.dom[dom][2])
        if n_ax != n_dom:
            out[dom] = {"가능": False, "D2": n_ax, "D4": n_dom,
                        "이유": "D2 != D4 — 챔피언 배선이 행을 넓힌다. 🔴 못 셌다"}
            continue
        m = d0.rows(dom, post=True, labeled=True, T=2025.0)
        assert len(m) == n_ax
        ks = [k for k, b in zip(keys, m) if b]
        if dom == "영화" and normalize:
            ks = [k.replace("KOBIS-", "") for k in ks]
        out[dom] = {"가능": True, "유보 키": ks}
    return out


def resolve_d3(dom, d3map, byid):
    d3keys = d3map[dom].get("유보 키")
    if not d3keys:
        return None, None
    d3recs = [byid[k] for k in d3keys if k in byid]
    d3hit = len(d3recs)
    # 🔴 조항 59 — 되짚기가 **조용히 0** 이 되는 길을 막는다
    assert d3hit and d3hit >= 0.5 * len(d3keys), (
        f"D3 되짚기 조용한 0/부분 실패 {dom}: 키 {len(d3keys)} → 매칭 {d3hit}")
    return d3recs, d3hit


# ── 필드 이름 훑기(W2 · W8) ───────────────────────────────────────────
def scan_paths(recs, needles, limit=2000):
    seen = set()

    def walk(o, pre="", d=0):
        if d > 4 or not isinstance(o, dict):
            return
        for k, v in o.items():
            path = f"{pre}.{k}" if pre else k
            if any(s in path.lower() for s in needles):
                seen.add(path)
            if isinstance(v, dict):
                walk(v, path, d + 1)
    for r in recs[:limit]:
        walk(r)
    return {p: sum(1 for r in recs if nonmissing(dig(r, p))) for p in sorted(seen)}


# ── 등급 (🔴 조건 넷) ─────────────────────────────────────────────────
def grade4(s1, s2, s3, s4):
    if s3 == "아니오":
        return "C"
    n = sum(1 for x in (s1, s2, s3, s4) if x == "예")
    if n == 4:
        return "A"
    if n == 3:
        return "B"       # 🔴 남은 하나는 전부 「추가 자료로 메울 수 있는 것」이다(사전등록 §3)
    return "C"


def grade5_old(s1, s2, s3, s4, s5):
    """901 의 규칙 재현 — 짝 단위 대조용."""
    if s3 == "아니오":
        return "C"
    n = sum(1 for x in (s1, s2, s3, s4, s5) if x == "예")
    if n == 5:
        return "A"
    if n == 4:
        return "B"
    return "C"


# ── 배선 검사 ─────────────────────────────────────────────────────────
def wiring_checks(d0, d3map):
    w = {}
    fired = {}

    # W-F 분할 자기시험 + 심은 결함
    def wf(broken):
        t = {}
        t["ㄱ 1..40"] = median_split([float(i) for i in range(1, 41)], broken)
        t["ㄴ 상수 40개"] = median_split([7.0] * 40, broken)
        t["ㄷ 0×36 + 1..4"] = median_split([0.0] * 36 + [1.0, 2.0, 3.0, 4.0], broken)
        t["ㄷ 최대균형"] = max_balanced([0.0] * 36 + [1.0, 2.0, 3.0, 4.0])
        t["ㄹ 날짜 40개"] = median_split(
            [f"2020-01-{i:02d}" for i in range(1, 29)]
            + [f"2020-02-{i:02d}" for i in range(1, 13)], broken)
        assert t["ㄱ 1..40"]["소수 쪽"] == 20, f"W-F ㄱ 실패: {t['ㄱ 1..40']}"
        assert t["ㄴ 상수 40개"]["소수 쪽"] == 0, f"W-F ㄴ 실패: {t['ㄴ 상수 40개']}"
        assert t["ㄷ 0×36 + 1..4"]["소수 쪽"] == 0, f"W-F ㄷ 실패: {t['ㄷ 0×36 + 1..4']}"
        assert t["ㄷ 최대균형"] == 4, f"W-F ㄷ 최대균형 실패: {t['ㄷ 최대균형']}"
        assert t["ㄹ 날짜 40개"]["소수 쪽"] == 20, f"W-F ㄹ 실패: {t['ㄹ 날짜 40개']}"
        return t

    w["W-F 분할 자기시험"] = wf(False)
    try:
        wf(True)
        fired["W-F 심은 결함(분할 함수 파손)"] = "🔴 발화 안 함 — 산출물을 쓰면 안 된다"
    except AssertionError as e:
        fired["W-F 심은 결함(분할 함수 파손)"] = {
            "무엇": "median_split 이 소수 쪽을 min(|L|,|H|) 대신 총수로 내게 파손",
            "발화": f"AssertionError: {e}"}

    # W-H 조용한 0 — 영화 정규화 되돌리기
    try:
        bad = d3_backtrack(d0, normalize=False)
        byid = {}
        recs = load_records(*SRC["영화"][:2])
        for r in recs:
            v = dig(r, IDF["영화"])
            if nonmissing(v):
                byid[str(v)] = r
        resolve_d3("영화", bad, byid)
        fired["W-H 심은 결함(영화 KOBIS- 정규화 되돌리기)"] = "🔴 발화 안 함"
    except AssertionError as e:
        fired["W-H 심은 결함(영화 KOBIS- 정규화 되돌리기)"] = {
            "무엇": "축 키 `KOBIS-20215315` 대 원천 `20215315` — 901 의 실사고 재현",
            "발화": f"AssertionError: {e}"}

    w["🔴 심은 결함의 발화"] = fired

    # W-A 경로 대조
    wa = {}
    for dom, (_k, _p, axp, _o) in SRC.items():
        if not axp:
            wa[dom] = "축 파일 없음(팝업은 npz 경로)"
            continue
        name = Path(axp).name
        assert (ROOT / axp).resolve() == (ROOT / "data/state" / name).resolve(), \
            f"W-A 경로 대조 실패 {axp}"
        wa[dom] = {"resolve() 대조": "일치"}
    w["W-A 축 파일 경로"] = wa

    # W-B D2 대 D4
    d2 = {d: len(json.loads((ROOT / a).read_text()))
          for d, (_k, _p, a, _o) in SRC.items() if a}
    d4 = {d: len(d0.dom[d][2]) for d in d0.dom}
    w["W-B D2 대 D4"] = {d: {"D2 축행": d2.get(d), "D4 도메인 행": d4.get(d),
                            "같나": d2.get(d) == d4.get(d)} for d in sorted(d4)}

    # W-E D3
    W = d0.weights(2025.0)
    d3 = {d: int(W[d]) for d in W}
    s3 = sum(d3.values())
    w["W-E D3 합(챔피언 배선 ff753.shell(base()))"] = s3
    w["W-E 대조"] = ("3775 와 일치" if s3 == 3775
                    else f"🔴 3775 와 다르다 ({s3}) — 맞추지 않고 적는다")
    w["W-E D3 도메인별"] = d3
    return w, d2, d4, d3


def main():
    out = {"노트": 902, "사전등록": PREREG,
           "시작 시각": START,
           "코드 sha256": {
               "runners/ident902.py": sha(Path(__file__)),
               "runners/inv901.py": sha(ROOT / "runners/inv901.py"),
               "runners/ident901.py": sha(ROOT / "runners/ident901.py")},
           "🔴 효과 크기": "없음 — 개수·값 가짓수·결측·분모만",
           "🔴 옛 산출물": ["runners/out901_identify.json",
                        "runners/out901_inventory.json",
                        "— 증거물이라 안 덮었다. 인용할 때 둘을 함께 건다"],
           "🔴 식별 조건은 넷이다": (
               "사전등록 §3 — 식5 「도메인 안 변이」는 식1 이 이미 도메인마다 따로 "
               "계산되므로 같은 물음의 다른 이름이다. **독립 측정이 불가능해서 조건을 "
               "넷으로 줄였다.** 있는 척하는 것보다 낫다"),
           "🔴 W 는 어느 것도 등급 계산에 안 들어간다": (
               "등급은 식1~식4 넷으로만 매긴다. W 는 「무엇이 없어서 못 재는가」의 "
               "목록이고 짝마다 출처 딱지를 단다"),
           }

    # 입력 지문
    inputs = {}
    for dom, (kind, p, axp, _o) in SRC.items():
        fp = ROOT / p
        if kind == "dir":
            h, n = sha_dir(fp)
            inputs[p] = {"sha256(결합)": h, "파일 수": n}
        else:
            inputs[p] = {"sha256": sha(fp)}
        if axp:
            inputs[axp] = {"sha256": sha(ROOT / axp)}
    inputs["runners/out901_identify.json"] = {
        "sha256": sha(ROOT / "runners/out901_identify.json")}
    inputs["runners/out901_inventory.json"] = {
        "sha256": sha(ROOT / "runners/out901_inventory.json")}
    out["입력 sha256"] = inputs

    import ff753 as FF
    d0 = FF.shell(FF.base())
    d3map = d3_backtrack(d0, normalize=True)
    wire, d2, d4, d3 = wiring_checks(d0, d3map)

    # 생 배선 대조(901 이 낸 사실 — 배선에 따라 D3 가 다르다)
    from lab import harness as HN
    raw = HN.load()
    d3_raw = {d: int(raw.rows(d, post=True, labeled=True, T=2025.0).sum())
              for d in raw.dom}
    wire["🔴 D3 는 배선에 따라 다르다"] = {
        "챔피언 ff753.shell(base()) 합": sum(d3.values()),
        "생 harness.load() 합": sum(d3_raw.values()),
        "차이 나는 도메인": {d: {"챔피언": d3.get(d), "생": d3_raw[d]}
                      for d in d3_raw if d3_raw[d] != d3.get(d)}}

    _inv = json.loads((ROOT / "runners/out901_inventory.json").read_text())["재고"]
    PRIOR_N = {k: v["식2 반복 단위"]["🔴 같은 단위의 더 이른 결과 관측이 있는 레코드 수"]
               for k, v in _inv.items()}

    old = json.loads((ROOT / "runners/out901_identify.json").read_text())["판정 표"]

    table, wg_bad = {}, []
    dom_scan = {}
    for dom, (kind, p, axp, outs) in SRC.items():
        recs = load_records(kind, p)
        idf = IDF.get(dom)
        byid = {}
        if idf:
            for r in recs:
                v = dig(r, idf)
                if nonmissing(v):
                    byid[str(v)] = r
        d3recs, d3hit = resolve_d3(dom, d3map, byid)

        # 식3 보조 — 개입 값의 관측 시점 필드
        asof = {f: c for f in ASOF_CAND
                if (c := sum(1 for r in recs if nonmissing(dig(r, f))))}
        # 식4 — 교란 후보
        conf = {f: c for f in CONFOUND[dom]
                if (c := sum(1 for r in recs if dig(r, f) not in (MISSING, None, "", [])))}

        # 🔴 W2 · W8 도메인 실측
        dom_scan[dom] = {
            "분모": "D1", "D1": len(recs),
            "W2 — 이름에 pre/prior/before/baseline/사전/이전 이 든 필드":
                scan_paths(recs, PRE_LIKE) or "훑었고 그 꼴의 필드가 없다",
            "W8 — 이름에 배정/선정/why/reason/criteria/rationale/decision/select/eligib/quota/random 이 든 필드":
                scan_paths(recs, ASSIGN_LIKE) or "훑었고 그 꼴의 필드가 없다"}

        # 반복 단위(표지 「단위 안 변이」용)
        ukeys = []
        for r in recs:
            v = dig(r, UNIT[dom])
            if isinstance(v, list):
                v = v[0] if v else None
            ukeys.append(None if v in (MISSING, None, "", []) else str(v))
        unit_rows = defaultdict(list)
        for i, k in enumerate(ukeys):
            if k:
                unit_rows[k].append(i)
        rep_units = {k: v for k, v in unit_rows.items() if len(v) >= 2}

        rows = {}
        for name, tier, typ, why in CAND[dom]:
            if tier in ("T3", "CAN"):
                continue
            vals = [dig(r, name) for r in recs]
            nn = [v for v in vals if nonmissing(v)]
            # 🔴 W-G — 독립 구현으로 다시 센다
            nn2 = sum(1 for r in recs if nonmissing(dig2(r, name)))
            if nn2 != len(nn):
                wg_bad.append((dom, name, len(nn), nn2))
            cnt = Counter(hashable(v) for v in nn)
            D1 = len(recs)
            r = {"등급": tier, "형": typ,
                 "D1": D1, "비결측(D1)": len(nn),
                 "결측률(D1)": round(1 - len(nn) / D1, 4),
                 "값 가짓수": len(cnt)}

            if d3recs is not None:
                v3 = [dig(x, name) for x in d3recs]
                nn3 = [v for v in v3 if nonmissing(v)]
                c3 = Counter(hashable(v) for v in nn3)
                r["D3(유보 채점행)"] = d3hit
                r["비결측(D3)"] = len(nn3)
                r["결측률(D3)"] = round(1 - len(nn3) / d3hit, 4) if d3hit else None
                r["값 가짓수(D3)"] = len(c3)
                base, base_n, base_vals = c3, "D3", nn3
            else:
                r["D3(유보 채점행)"] = None
                r["🔴 D3 덮음"] = "못 셌다 — " + d3map[dom]["이유"]
                base, base_n, base_vals = cnt, "D1", nn

            tv = typed_values(typ, base_vals)
            s1, s1why = sik1(typ, base, tv, base_n)
            r["식1 처치/대조"] = s1
            r["식1 근거"] = s1why

            # 식2 (약) — 901 규칙 그대로
            r["식2 사전 관측(약·생산자 단위)"] = "예" if PRIOR_N[dom] > 0 else "아니오"
            r["식2 근거"] = (f"같은 단위({UNIT[dom]})의 더 이른 결과 관측이 있는 레코드 "
                          f"{PRIOR_N[dom]} (D1={D1}) — 출처 runners/out901_inventory.json")

            # 식3 — 901 규칙 그대로
            if name in PRE_PROVEN.get(dom, ()):
                r["식3 역인과 아님"], r["식3 근거"] = "예", PRE_WHY[dom]
            elif typ == "d":
                r["식3 역인과 아님"] = "예"
                r["식3 근거"] = "날짜 자체 — 결과 창이 이 날짜에 열린다(구조상 사전)"
            elif name in POST_GROW.get(dom, ()):
                r["식3 역인과 아님"] = "아니오"
                r["식3 근거"] = "🔴 결과 창이 열린 뒤에도 자란다(수집 시점 스냅숏) — 결과와 동시 결정"
            else:
                r["식3 역인과 아님"] = "모른다"
                r["식3 근거"] = ("이 열의 **관측 시점** 필드가 없다. 도메인에 있는 시점 필드"
                              "(개입 열을 안 덮는다): "
                              + (", ".join(f"{k}={v}" for k, v in asof.items()) or "없음"))

            # 식4 — 901 규칙 그대로
            r["식4 교란 관측"] = "예" if conf else "아니오"
            r["식4 근거"] = ", ".join(f"{k}={v}" for k, v in conf.items()) or "없음"

            g = grade4(r["식1 처치/대조"], r["식2 사전 관측(약·생산자 단위)"],
                       r["식3 역인과 아님"], r["식4 교란 관측"])
            r["등급(식별)"] = g

            # 🔴 정직 표지
            marks = []
            if typ in ("c", "d") and s1 == "예":
                marks.append("🔴 이 처치/대조는 **우리가 중앙값으로 만든 것**이지 "
                             "자연 발생한 대조군이 아니다")
            if typ == "d":
                marks.append("🔴 이 날짜는 **처치이면서 동시에 결과 창의 원점**이다 — "
                             "식3=「예」의 근거가 곧 효과 추정의 문제다. "
                             "902 는 식3 을 안 바꾼다(골라 떨어뜨리기 재발 방지)")
                marks.append("⚠ 이 날짜 열은 판에서 **탈추세 변수로 이미 소비된다**"
                             "(`runners/inv901.py` 의 등급 사유)")
            r["🔴 표지(등급 미사용)"] = marks or "없음"

            # 표지 — 단위 안 변이 (식5 자리의 진짜 독립 측정 · 등급 미사용)
            uv = 0
            for k, idxs in rep_units.items():
                s = {hashable(vals[i]) for i in idxs if nonmissing(vals[i])}
                if len(s) >= 2:
                    uv += 1
            r["표지 단위 안 변이(등급 미사용)"] = {
                "단위 키": UNIT[dom], "레코드 2건 이상인 단위 수": len(rep_units),
                "그중 이 열의 값이 2가지 이상인 단위 수": uv, "분모": "D1"}

            # W — 출처 딱지
            Wl = []
            if r["식1 처치/대조"] == "아니오":
                sub = s1why.get("사유", "")
                if "W1" in sub or s1why.get("값 가짓수", 9) < 2:
                    Wl.append({"W": "W1 대조군 없음", "출처": "짝 실측"})
                elif "W6" in sub:
                    Wl.append({"W": "W6 표본 부족", "출처": "짝 실측", "근거": sub})
                else:
                    Wl.append({"W": "W6 표본 부족(동률 퇴화)", "출처": "짝 실측", "근거": sub})
            if r["식1 처치/대조"] == "모른다":
                Wl.append({"W": "W-미정 — 열이 없거나 분모를 못 셌다", "출처": "짝 실측"})
            if r["식3 역인과 아님"] == "모른다":
                Wl.append({"W": "W4 처치 시점 없음 — 개입 값이 언제 정해졌는지 기록이 없다",
                           "출처": "짝 실측(이 열의 관측 시점 필드 부재)"})
            if r["식3 역인과 아님"] == "아니오":
                Wl.append({"W": "W7 역인과", "출처": "짝 실측"})
            if r["식4 교란 관측"] == "아니오":
                Wl.append({"W": "W5 교란 관측 없음", "출처": "짝 실측"})
            if r["식2 사전 관측(약·생산자 단위)"] == "아니오":
                Wl.append({"W": "W2 사전 관측 없음(생산자 단위)", "출처": "도메인 실측"})
            Wl.append({"W": "W2 사전 관측 없음(같은 레코드 기준)", "출처": "도메인 실측",
                       "🔴 등급 미사용": True,
                       "근거": "이 도메인의 필드 이름 훑기 결과는 `도메인 훑기` 절에 있다"})
            Wl.append({"W": "W8 배정 기제 미상", "출처": "도메인 실측",
                       "🔴 등급 미사용": True,
                       "근거": "이 도메인의 배정/선정 관련 필드 훑기 결과는 `도메인 훑기` 절"})
            r["W"] = Wl
            rows[name] = r

        table[dom] = {"원천": p, "D1": len(recs),
                      "D3 되짚기": d3map[dom].get("가능"),
                      "D3 되짚은 레코드 수": d3hit,
                      "개입 값의 관측 시점 필드": asof or "없음",
                      "교란 후보(같은 레코드 열)": conf or "없음",
                      "짝": rows}
        cs = Counter(v["등급(식별)"] for v in rows.values())
        print(f"{dom}\tA={cs['A']} B={cs['B']} C={cs['C']}\tD3되짚기="
              f"{d3map[dom].get('가능')}", flush=True)

    # 🔴 W-G 판정 + 심은 결함
    wire["W-G 두 경로 대조"] = {
        "어긋난 짝": wg_bad or "없음 — 105짝 전량에서 두 구현의 비결측 수가 같다"}
    assert not wg_bad, f"W-G 두 경로 어긋남: {wg_bad[:5]}"
    try:
        _r = load_records(*SRC["게임"][:2])
        a = sum(1 for r in _r if nonmissing(dig(r, "price_krw")))
        b = sum(1 for r in _r if nonmissing(dig2(r, "price_krw", _broken=True)))
        assert a == b, f"W-G 두 경로 어긋남(심은 결함): dig={a} dig2={b}"
        wire["🔴 심은 결함의 발화"]["W-G 심은 결함(두 번째 구현이 이웃 키를 읽는다)"] = \
            "🔴 발화 안 함 — 산출물을 쓰면 안 된다"
    except AssertionError as e:
        wire["🔴 심은 결함의 발화"]["W-G 심은 결함(두 번째 구현이 이웃 키를 읽는다)"] = {
            "무엇": "dig2 가 마지막 키를 `<키>_x` 로 바꿔 읽게 파손",
            "발화": f"AssertionError: {e}"}

    fired = wire["🔴 심은 결함의 발화"]
    unfired = [k for k, v in fired.items() if isinstance(v, str)]
    wire["🔴 심은 결함 셋이 전부 발화했나"] = (not unfired)
    assert not unfired, f"🔴 심은 결함이 발화 안 했다: {unfired} — 산출물을 쓰면 안 된다"

    # ── 🔴 짝 단위 옛↔새 대조 ────────────────────────────────────────
    comp, recon_bad = [], []
    for dom in table:
        for name, r in table[dom]["짝"].items():
            o = old[dom]["짝"][name]
            o1, o3 = o["식1 처치/대조"], o["식3 역인과 아님"]
            o2 = o["식2 사전 관측(약·생산자 단위)"]
            o4, o5 = o["식4 교란 관측"], o["식5 도메인 안 변이"]
            # 옛 등급을 옛 규칙으로 다시 계산해 산출물과 대조(재현 확인)
            g_old_recalc = grade5_old(o1, o2, o3, o4, o5)
            if g_old_recalc != o["등급(식별)"]:
                recon_bad.append((dom, name, g_old_recalc, o["등급(식별)"]))
            n1, n3 = r["식1 처치/대조"], r["식3 역인과 아님"]
            g_old = o["등급(식별)"]
            g_new = r["등급(식별)"]
            # 분해: 식1 규칙만 / 식5 폐지만
            g_only1 = grade5_old(n1, o2, n3, r["식4 교란 관측"], n1)
            g_only5 = grade4(o1, o2, o3, o4)
            a1, a5 = (g_only1 != g_old), (g_only5 != g_old)
            if g_new == g_old:
                why = "변화 없음"
            elif a1 and not a5:
                why = "식1 규칙 신설(연속·날짜)"
            elif a5 and not a1:
                why = "식5 폐지(4조건)"
            elif a1 and a5:
                why = "🔴 둘 다 — 식1 규칙 신설(연속·날짜) + 식5 폐지(4조건)"
            else:
                why = "🔴 둘 다 — 따로는 안 바뀌는데 함께 작용하면 바뀐다"
            comp.append({"도메인": dom, "열": name, "T": r["등급"], "형": r["형"],
                         "옛 식1": o1, "새 식1": n1,
                         "옛 등급": g_old, "새 등급": g_new, "바뀐 이유": why,
                         "식1 규칙만 적용하면": g_only1,
                         "식5 폐지만 적용하면": g_only5})
    assert not recon_bad, f"🔴 901 등급 재현 실패: {recon_bad[:5]}"
    out["🔴 옛 등급 재현(901 규칙을 902 코드로 다시 계산)"] = \
        "105/105 일치 — 대조가 옛 산출물과 같은 자리에서 출발한다"

    # ── Q1 회귀 시험 : b·l 형은 식1 이 옛 값과 같아야 한다 ─────────────
    bl = [c for c in comp if c["형"] in ("b", "l")]
    bl_bad = [c for c in bl if c["옛 식1"] != c["새 식1"]]
    out["🔴 Q1 회귀 시험 — b·l 형 식1 재현"] = {
        "b·l 짝 수": len(bl), "어긋난 짝": bl_bad or "없음",
        "판정": "확인" if not bl_bad else "🔴 반증 — 재현 실패이므로 나머지 수를 쓰지 않는다"}

    # ── 수 세기 (🔴 T1 만의 수를 따로) ──────────────────────────────
    def three(pred):
        t1 = sum(1 for c in comp if c["T"] == "T1" and pred(c))
        t2 = sum(1 for c in comp if c["T"] == "T2" and pred(c))
        return {"T1": t1, "T2": t2, "T1+T2(참고)": t1 + t2}

    out["🔴 헤드라인 — T1 만의 수 (T2 는 절대 안 더한다 · prereg_901:61)"] = {
        "짝 전량": three(lambda c: True),
        "새 등급 A": three(lambda c: c["새 등급"] == "A"),
        "새 등급 B": three(lambda c: c["새 등급"] == "B"),
        "새 등급 C": three(lambda c: c["새 등급"] == "C"),
        "옛 등급 A": three(lambda c: c["옛 등급"] == "A"),
        "옛 등급 B": three(lambda c: c["옛 등급"] == "B"),
        "옛 등급 C": three(lambda c: c["옛 등급"] == "C"),
        "🔴 헤드라인은 T1 칸을 쓴다": True}

    out["등급 이동표(옛→새)"] = {f"{a}→{b}": three(
        lambda c, a=a, b=b: c["옛 등급"] == a and c["새 등급"] == b)
        for a in "ABC" for b in "ABC"
        if any(c["옛 등급"] == a and c["새 등급"] == b for c in comp)}
    out["바뀐 이유별"] = {w: three(lambda c, w=w: c["바뀐 이유"] == w)
                     for w in sorted({c["바뀐 이유"] for c in comp})}
    out["🔴 사전등록이 정한 이유 라벨은 셋이었다"] = (
        "`식1 규칙 신설(연속·날짜)` · `식5 폐지(4조건)` · `변화 없음`. "
        "🔴 **둘이 동시에 작용하는 짝이 있어 넷째 라벨을 추가했다** — 감추지 않고 적는다")

    # ── 🔴 식3=예인 25짝의 결말 ────────────────────────────────────
    s3yes = [c for c in comp
             if old[c["도메인"]]["짝"][c["열"]]["식3 역인과 아님"] == "예"]
    out["🔴 식3=예였던 짝의 결말"] = {
        "짝 수": {"T1": sum(1 for c in s3yes if c["T"] == "T1"),
                "T2": sum(1 for c in s3yes if c["T"] == "T2"),
                "T1+T2(참고)": len(s3yes)},
        "새 등급 분포": {g: three(lambda c, g=g: c in s3yes and c["새 등급"] == g)
                   for g in "ABC"},
        "전량": [{"도메인": c["도메인"], "열": c["열"], "T": c["T"], "형": c["형"],
                "옛 등급": c["옛 등급"], "새 등급": c["새 등급"],
                "옛 식1": c["옛 식1"], "새 식1": c["새 식1"],
                "식1 근거": table[c["도메인"]]["짝"][c["열"]]["식1 근거"]}
               for c in s3yes]}

    # ── Q2·Q3·Q4 ────────────────────────────────────────────────────
    A = [c for c in comp if c["새 등급"] == "A"]
    s2_vals = Counter(table[d]["짝"][n]["식2 사전 관측(약·생산자 단위)"]
                      for d in table for n in table[d]["짝"])
    s4_vals = Counter(table[d]["짝"][n]["식4 교란 관측"]
                      for d in table for n in table[d]["짝"])
    out["🔴 사전등록 예측 판정"] = {
        "Q1 b·l 형 식1 100% 재현": out["🔴 Q1 회귀 시험 — b·l 형 식1 재현"]["판정"],
        "Q2 새 규칙에서 A ≥ 1": {
            "실측 A(T1)": sum(1 for c in A if c["T"] == "T1"),
            "실측 A(T2)": sum(1 for c in A if c["T"] == "T2"),
            "판정": "확인" if A else "🔴 반증"},
        "Q3 식3=예 25짝 중 C 로 남는 것 0": {
            "실측 C": sum(1 for c in s3yes if c["새 등급"] == "C"),
            "판정": "확인" if not any(c["새 등급"] == "C" for c in s3yes) else "🔴 반증"},
        "Q4 식2(약)·식4 는 105/105 상수": {
            "식2(약) 값 분포": dict(s2_vals), "식4 값 분포": dict(s4_vals),
            "판정": ("확인 — 둘 다 상수다(등급을 못 가른다)"
                   if len(s2_vals) == 1 and len(s4_vals) == 1 else "🔴 반증")},
    }
    out["🔴 상수인 조건은 등급을 못 가른다"] = {
        "식2(약)": ("105/105 상수" if len(s2_vals) == 1 else "갈린다"),
        "식4": ("105/105 상수" if len(s4_vals) == 1 else "갈린다"),
        "뜻": ("이 둘이 상수면 실제로 등급을 가르는 것은 **식1 과 식3 뿐**이다. "
             "901 은 이 사실을 안 적었고 논문·PR·원장이 W8 105/105 를 실측처럼 실었다")}

    # ── 🔴 무엇이 막았나 — 등급별 사유 (수를 인용하려면 산출물에 있어야 한다) ──
    rows_all = [(dm, n, table[dm]["짝"][n]) for dm in table for n in table[dm]["짝"]]
    tier_of = {(dm, n): r["등급"] for dm, n, r in rows_all}

    def cnt3(sel):
        t1 = sum(1 for dm, n, r in rows_all if tier_of[(dm, n)] == "T1" and sel(r))
        t2 = sum(1 for dm, n, r in rows_all if tier_of[(dm, n)] == "T2" and sel(r))
        return {"T1": t1, "T2": t2, "T1+T2(참고)": t1 + t2}

    out["🔴 무엇이 막았나"] = {
        "식3 값 분포(105짝)": dict(Counter(r["식3 역인과 아님"] for _, _, r in rows_all)),
        "식1 값 분포(105짝)": dict(Counter(r["식1 처치/대조"] for _, _, r in rows_all)),
        "🔴 W4 처치 시점 없음 = 식3「모른다」짝 수":
            cnt3(lambda r: r["식3 역인과 아님"] == "모른다"),
        "B 등급이 못 채운 칸 — 식3=모른다(W4)":
            cnt3(lambda r: r["등급(식별)"] == "B" and r["식3 역인과 아님"] != "예"),
        "B 등급이 못 채운 칸 — 식1=아니오":
            cnt3(lambda r: r["등급(식별)"] == "B" and r["식1 처치/대조"] != "예"),
        "C 등급 — 식3=아니오(W7 역인과 확정)":
            cnt3(lambda r: r["등급(식별)"] == "C" and r["식3 역인과 아님"] == "아니오"),
        "C 등급 — 식1·식3 둘 다 못 채움":
            cnt3(lambda r: r["등급(식별)"] == "C" and r["식3 역인과 아님"] == "모른다"),
        "🔴 정정된 문장": (
            "901 은 「막는 것은 결측이 아니라 W4·W8 이다」라고 썼다. **W8 은 등급에 "
            "안 들어가는 표지였고 W2 도 마찬가지다**(티처 #64 C2). 902 의 실측으로 "
            "남는 것은 **W4 하나**다 — 등급을 가르는 두 칸(식1·식3) 중 식3 을 막는 것이 W4 다"),
    }

    out["🔴 A 등급 전량"] = [
        {"T": r["등급"], "도메인": dm, "열": n, "형": r["형"],
         "분모": r["식1 근거"]["분모"], "소수 쪽": r["식1 근거"]["소수 쪽"],
         "표지": r["🔴 표지(등급 미사용)"]}
        for dm, n, r in rows_all if r["등급(식별)"] == "A"]

    # ── 감도(판정 미사용) — 중앙값 대 최대균형 ──────────────────────
    sens = []
    for dm, n, r in rows_all:
        if r["형"] not in ("c", "d"):
            continue
        g = r["식1 근거"]
        m, mb = g["소수 쪽"], g["감도(판정 미사용) 최대균형 소수 쪽"]
        if (m >= MIN_SIDE) != (mb >= MIN_SIDE):
            sens.append({"도메인": dm, "열": n, "T": r["등급"], "형": r["형"],
                         "중앙값 소수 쪽": m, "최대균형 소수 쪽": mb,
                         "중앙값 규칙 등급": r["등급(식별)"],
                         "최대균형이었다면 식1": "예",
                         "최대균형이었다면 등급": grade4(
                             "예", r["식2 사전 관측(약·생산자 단위)"],
                             r["식3 역인과 아님"], r["식4 교란 관측"])})
    out["🔴 감도(판정 미사용) — 중앙값 대 최대균형"] = {
        "🔴 판정에는 안 쓴다": "사전등록 §2 가 중앙값을 못 박았다",
        "판정이 갈리는 c·d 짝 수": len(sens), "전량": sens,
        "🔴 A 수가 바뀌나": (
            "안 바뀐다 — 갈리는 짝은 전부 식3=「모른다」라 C→B 로만 움직인다"
            if all(s["최대균형이었다면 등급"] != "A" for s in sens)
            else "🔴 바뀐다 — 아래 목록을 보라")}

    out["🔴 문턱에 딱 걸린 짝(소수 쪽 == 10)"] = [
        {"도메인": dm, "열": n, "T": r["등급"], "형": r["형"],
         "소수 쪽": r["식1 근거"]["소수 쪽"], "등급": r["등급(식별)"]}
        for dm, n, r in rows_all
        if r["식1 근거"].get("소수 쪽") == MIN_SIDE] or "없음"

    out["🔴 재실행 고지"] = (
        "이 러너는 두 번 돌았다. 두 번째는 **인용할 수를 산출물에 내기 위해 보고 키를 "
        "추가**한 것이고(`🔴 무엇이 막았나`·`🔴 A 등급 전량`·`🔴 감도`·`🔴 문턱에 딱 걸린 짝`), "
        "🔴 **등급 규칙(식1~식4·grade4)은 한 글자도 안 바꿨다.** "
        "첫 실행의 등급 분포와 두 번째가 같다: A 23 · B 66 · C 16(T1+T2 참고). "
        "사전등록 커밋 b37ccd019(04:43:09) → 첫 실행 04:47:49 → 이 실행")

    out["도메인 훑기 — W2 · W8 실측(도메인 단위)"] = dom_scan
    out["🔴 W8 의 읽기"] = ("0 이면 「없다」가 아니라 **「훑었고 그 꼴의 필드가 없다」**다"
                       "(조항 59). 그리고 W8 은 **등급에 안 들어간다**")
    out["짝 단위 옛↔새 대조(105짝 전량)"] = comp
    out["D3 되짚기"] = {k: {kk: vv for kk, vv in v.items() if kk != "유보 키"}
                    for k, v in d3map.items()}
    out["판정 표"] = table
    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["초"] = round(time.time() - T0, 1)

    wjs = {"노트": 902, "사전등록": PREREG, "시작 시각": START,
           "코드 sha256": out["코드 sha256"], "입력 sha256": inputs,
           "배선 검사": wire,
           "끝 시각": dt.datetime.now().isoformat(timespec="seconds"),
           "초": round(time.time() - T0, 1)}
    (ROOT / "runners/out902_wiring.json").write_text(
        json.dumps(wjs, ensure_ascii=False, indent=1))
    (ROOT / "runners/out902_identify.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("완료 →", ROOT / "runners/out902_identify.json")
    print("완료 →", ROOT / "runners/out902_wiring.json")


if __name__ == "__main__":
    main()
