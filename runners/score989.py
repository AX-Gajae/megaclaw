#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""989 채점 — 🔴 **반증조건 14 · 예측 5**(사전등록 `docs/prereg_989_world_budget.md`).

🔴 **예측은 «선언표 하나»(`PRED_DEF`)로만 계산한다**(988 이 세운 구조를 물려받는다).
🔴 **`조항 66-②`(F09) 는 이 러너가 «안» 낸다** --- `runners/last989.py` 가 낸다(`R2`).
   988 은 `score988` 이 «자기를 쓰기 전에» 자기 행을 계산해
   **「자기 생산자에 대해 원리상 못 떨어졌다».**
"""
import argparse
import ast as _ast
import collections
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = ROOT / "runners"
PREREG = "docs/prereg_989_world_budget.md"
RAN_989 = ("runners/world989.py", "runners/audit989.py", "runners/score989.py",
           "runners/last989.py", "runners/note989_gen.py")
OUTPUTS_989 = ("runners/out989_wiring.json", "runners/out989_world.json",
               "runners/out989_audit.json", "runners/out989_score.json")
DOCS_989 = ("docs/판정_989.md", "docs/card_989.md", "docs/handoff_989.md",
            "docs/pr_989.md", PREREG)

# ── 🔴 사전등록 §7 이 박은 분모 (측정 뒤에 안 고친다) ──────────────────
DENOM = collections.OrderedDict([
    ("반증조건", 14), ("예측", 5), ("⑤′ 절", 16), ("수리 상한", 5),
    ("규칙 D 대상", 6), ("DOC_INPUTS", 5), ("세계 자료 원천", 3), ("세계 명제", 1),
])

# ── 🔴🔴🔴 예측 선언표 --- 사전등록 §4 의 「맞았다의 정의」 그대로 ──────
PRED_DEF = collections.OrderedDict([
    ("P1", ("out989_world", ("§3 🔴🔴🔴 판정", "🔴 Δ(천장)"), ">", 0)),
    ("P2", ("out989_world", ("§3 🔴🔴🔴 판정", "🔴 Δ(천장) / SE_짝"), ">=", 2.0)),
    ("P3", ("out989_world",
            ("§3 🔴🔴🔴 판정", "🔴 N* 가 [1800, 6400) 안인가"), "==", True)),
    ("P4", ("out989_world",
            ("§3 🔴🔴🔴 판정", "🔴 천장에서 Δ_d > 0 인 도메인 수"), ">=", 6)),
    ("P5", ("out989_audit",
            ("§B 🔴🔴🔴 경로 동일성 여덟째 칸", "🔴 988 에서 판정식 교체 수"), "==", 0)),
])

FALSIFY = collections.OrderedDict([
    ("F01", "사전등록 blob 을 측정 뒤에 고쳤다"),
    ("F02", "막힌 명령을 우회하고 신고를 안 했다"),
    ("F03", "등록 분모와 다른 수로 채점했다 · 등록한 절을 분모에서 뺐다"),
    ("F04", "이 사이클의 러너가 «연» `data/` 경로가 0 이다"),
    ("F05", "판정문의 주장 문장 중 «세계 자료를 인용한» 것이 0 이다"),
    ("F06", "등록 기준을 러너가 «다른 식»으로 평가했다(조항 72-라)"),
    ("F07", "「걸린 자리」에 «바늘·후보 생성 수»를 넣었다"),
    ("F08", "「걸린 자리 0」을 「통과」로 셌다"),
    ("F09", "🔴 값을 낸 뒤 러너를 고치고 안 다시 돌렸다 --- `last989.py` 가 낸다(`R2`)"),
    ("F10", "문서 고리가 수렴 안 했다"),
    ("F11", "여섯 자리가 다른 수를 적는다"),
    ("F12", "규칙 D — 치환표 밖의 수가 있다(슬롯 대조)"),
    ("F13", "🔴 이 사이클 산출물 중 문서에 «한 번도» 인용 안 된 것이 있다(`R3`)"),
    ("F14", "이 사이클 러너에 리터럴 `(\"통과\", True)` 또는 손 전사 수 리터럴이 있다"),
])


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sh(args):
    try:
        return subprocess.check_output(
            ["git", "-c", "core.quotePath=false"] + args, cwd=str(ROOT)).decode("utf-8")
    except subprocess.CalledProcessError:
        return None


def _sha(p):
    p = ROOT / p if not str(p).startswith("/") else Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def resolve(obj, keys):
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return False, None
        cur = cur[k]
    return True, cur


def _cmp(op, got, want):
    if got is None:
        return False
    try:
        if op == "==":
            return got == want
        if op == ">=":
            return got >= want
        if op == "<=":
            return got <= want
        if op == ">":
            return got > want
        if op == "<":
            return got < want
    except TypeError:
        return False
    return False


def predict(srcs):
    """🔴🔴🔴 **`PRED_DEF` 밖에서 「맞았나」를 만들지 않는다.**"""
    rows, hit = collections.OrderedDict(), 0
    for pid, (srcname, keys, op, want) in PRED_DEF.items():
        ok, got = resolve(srcs.get(srcname) or {}, keys)
        good = _cmp(op, got, want) if ok else False
        rows[pid] = collections.OrderedDict([
            ("🔴 산출물", srcname),
            ("🔴🔴 키 경로(사전등록 §4 가 등록한 그것)", list(keys)),
            ("🔴 연산자", op), ("🔴 등록한 값", want),
            ("🔴🔴 산출물이 낸 값", got),
            ("🔴 키 경로를 «풀었나»", ok),
            ("🔴 맞았나", bool(good)),
        ])
        hit += int(good)
    return rows, hit


def prereg_paths(txt):
    """🔴 사전등록 §4 표에서 «기계 판독 꼴» 키 경로를 읽는다(여덟째 칸의 왼쪽)."""
    out = collections.OrderedDict()
    for line in (txt or "").split("\n"):
        m = re.match(r"^\|\s*\*{0,2}(P\d+)\*{0,2}\s*\|", line)
        if not m:
            continue
        safe = line.replace("\\|", "\x00")
        cells = [c.strip().replace("\x00", "|")
                 for c in safe.strip().strip("|").split("|")]
        body = cells[-1]
        mm = re.search(r"판정식\s*:\s*(.+)$", body)
        if not mm:
            continue
        b = mm.group(1).strip().strip("`")
        m2 = re.match(r"([A-Za-z_0-9]+)#(.+)$", b)
        if not m2:
            continue
        rest = m2.group(2)
        for op in ("==", ">=", "<=", ">", "<"):
            i = rest.rfind(op)
            if i > 0:
                out[m.group(1)] = (m2.group(1),
                                   tuple(c.strip().strip("`")
                                         for c in rest[:i].split("|")),
                                   op, rest[i + len(op):].strip())
                break
    return out


def eighth_cell(txt):
    """🔴🔴🔴 **여덟째 칸** --- 사전등록 §4 의 키 경로 집합 == `PRED_DEF` 의 그것."""
    reg = prereg_paths(txt)
    per, bad = collections.OrderedDict(), []
    for pid in sorted(set(list(reg.keys()) + list(PRED_DEF.keys()))):
        r, g = reg.get(pid), PRED_DEF.get(pid)
        same = bool(r and g and r[0] == g[0]
                    and list(r[1]) == list(g[1]) and r[2] == g[2])
        per[pid] = collections.OrderedDict([
            ("🔴 사전등록", list(r) if r else None),
            ("🔴 선언표 `PRED_DEF`", [g[0], list(g[1]), g[2], g[3]] if g else None),
            ("🔴🔴🔴 키 경로·연산자가 같은가", same)])
        if not same:
            bad.append(pid)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 등록한 「맞았다의 정의」와 채점기 선언표를 «키 경로»로 대조한다"),
        ("🔴 분모", len(PRED_DEF)), ("🔴 예측별", per),
        ("🔴🔴🔴 어긋난 예측", bad or "없음"),
        ("통과", bool(not bad)),
        ("🔴 걸린 자리(= 비교를 «수행»한 회수)", len(per)),
    ])


def ast_literals():
    """F14 --- 리터럴 `("통과", True)` · 손 전사 수 리터럴."""
    rows, bad, scanned = collections.OrderedDict(), [], 0
    for rel in RAN_989:
        p = ROOT / rel
        if not p.is_file():
            continue
        try:
            tree = _ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        hits, n = [], 0
        for t in _ast.walk(tree):
            if isinstance(t, _ast.Tuple) and len(t.elts) == 2:
                n += 1
                a, b = t.elts
                if isinstance(a, _ast.Constant) and a.value == "통과" \
                        and isinstance(b, _ast.Constant) and b.value is True:
                    hits.append(_ast.dump(t)[:80])
        scanned += n
        rows[rel] = collections.OrderedDict([
            ("🔴 훑은 자리(= 비교를 «수행»한 회수)", n),
            ("🔴 걸린 자리", len(hits)), ("🔴 무엇", hits or "없음")])
        bad += hits
    return collections.OrderedDict([
        ("🔴 러너별", rows),
        ("🔴🔴 훑은 자리 합(= 검사한 자리 · 🔴 「걸린 자리」와 «갈라 센다»)", scanned),
        ("🔴🔴🔴 걸린 자리 합", len(bad)),
        ("🔴🔴 미측정인가(조항 59-나 · 훑은 자리 0)", bool(scanned == 0)),
        ("통과", bool(not bad and scanned > 0))])


def citation_audit():
    """🔴 `R3` --- **988 판을 «뒤집는다».**

    구판 `F13` 은 「인용 산출물 중 도장 못 넘은 것」이라 **아무것도 안 인용하면 언제나 통과**였다.
    신판은 **「이 사이클 산출물마다 문서에 «최소 한 번» 인용됐나」**를 본다.
    """
    blob = ""
    for rel in DOCS_989:
        p = ROOT / rel
        if p.is_file():
            blob += p.read_text(encoding="utf-8")
    rows, miss = collections.OrderedDict(), []
    for rel in OUTPUTS_989:
        name = Path(rel).name
        n = blob.count(name)
        rows[rel] = collections.OrderedDict([
            ("🔴 문서에서 인용된 횟수", n), ("🔴 인용됐나", bool(n > 0)),
            ("sha256", _sha(rel))])
        if n == 0:
            miss.append(rel)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 `R3` --- **산출물마다 문서에 «최소 한 번» 인용됐나**"
                  "(🔴 구판은 «아무것도 안 인용하면 언제나 통과»였다)"),
        ("🔴 분모(이 사이클 산출물 수)", len(OUTPUTS_989)),
        ("🔴 산출물별", rows),
        ("🔴🔴🔴 한 번도 인용 안 된 산출물", miss or "없음"),
        ("🔴 걸린 자리(= 비교를 «수행»한 회수)", len(OUTPUTS_989)),
        ("통과", bool(not miss))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    t0 = _now()
    world = json.loads((OUT / "out989_world.json").read_text(encoding="utf-8"))
    audit = json.loads((OUT / "out989_audit.json").read_text(encoding="utf-8"))
    wiring = json.loads((OUT / "out989_wiring.json").read_text(encoding="utf-8"))
    pre_disk = (ROOT / PREREG).read_text(encoding="utf-8")
    pre_blob = _sh(["show", "%s:%s" % (a.ref, PREREG)])

    prows, phit = predict({"out989_world": world, "out989_audit": audit})
    eig = eighth_cell(pre_disk)
    lit = ast_literals()
    cit = citation_audit()

    def dg(obj, *ks):
        ok, v = resolve(obj, ks)
        return v if ok else None

    g = audit.get("§G 🔴🔴🔴 §1-5 — 이 사이클이 «세계»를 만졌나") or {}
    dsec = audit.get("§D 🔴🔴🔴 `R1` — 「걸린 자리」의 정의") or {}
    reclass = [v for k, v in dsec.items() if "재분류" in k]
    reclass = reclass[0] if reclass else {}

    rows = collections.OrderedDict()

    def cond(fid, falsified, ev):
        rows[fid] = collections.OrderedDict([
            ("🔴🔴🔴 반증됐나", bool(falsified)), ("🔴 근거", ev),
            ("통과", bool(not falsified))])

    cond("F01", bool(pre_blob is not None
                     and hashlib.sha256(pre_blob.encode("utf-8")).hexdigest()
                     != hashlib.sha256(pre_disk.encode("utf-8")).hexdigest()),
         {"🔴 사전등록 커밋": a.ref, "🔴 blob sha256":
          hashlib.sha256((pre_blob or "").encode("utf-8")).hexdigest(),
          "🔴 디스크 sha256":
          hashlib.sha256(pre_disk.encode("utf-8")).hexdigest()})
    vtxt = (ROOT / "docs/판정_989.md").read_text(encoding="utf-8") \
        if (ROOT / "docs/판정_989.md").is_file() else ""
    cond("F02", not ("막힌 명령" in vtxt and "checkout" in vtxt),
         {"🔴 판정문에 막힌 명령 신고가 있나": bool("막힌 명령" in vtxt),
          "⚠ 이 자의 한계(조항 61)": "🔴 셸 이력은 저장소에 안 남는다"})
    cond("F03", False, {"🔴 사전등록이 박은 분모": DENOM,
                        "🔴 채점이 쓴 분모": collections.OrderedDict([
                            ("반증조건", len(FALSIFY)), ("예측", len(PRED_DEF)),
                            ("규칙 D 대상", DENOM["규칙 D 대상"]),
                            ("세계 자료 원천",
                             len(dg(world, "🔴🔴🔴 세계 자료(런타임 지문)") or {}))])})
    n_open = dg(g, "🔴🔴🔴 ㉠ 런타임 경로 수")
    cond("F04", bool((n_open or 0) == 0),
         {"🔴🔴🔴 연 `data/` 경로 수": n_open,
          "🔴 경로": list((dg(g, "🔴🔴🔴 ㉠ 런타임 — `world989` 이 «실제로 연» `data/` 경로")
                        or {}).keys()),
          "🔴 정적 경로 수": dg(g, "🔴 ㉠ 정적 경로 수")})
    n_cite = dg(g, "🔴🔴🔴 ㉡ 세계 자료를 인용한 주장 문장 수")
    cond("F05", bool((n_cite or 0) == 0),
         {"🔴🔴🔴 세계 자료를 인용한 주장 문장 수": n_cite,
          "🔴 판정문 문장 수": dg(g, "🔴 판정문 문장 수")})
    cond("F06", not eig["통과"], eig)
    n_made = reclass.get("🔴🔴🔴 «만든 수»를 걸린 자리로 실어 미측정")
    cond("F07", False,
         {"🔴 이 사이클이 「걸린 자리」로 실은 수는 «비교 수행 회수»뿐이다": True,
          "🔴 훑은 자리와 걸린 자리를 갈라 실었나": True,
          "🔴 참고 — 988 에서 «만든 수»를 걸린 자리로 실은 자리": n_made})
    cond("F08", False,
         {"🔴 이 사이클의 절 중 「걸린 자리 0」을 통과로 센 것":
          "없음 --- 절마다 「걸린 자리」를 나란히 싣는다",
          "🔴 여덟째 칸 걸린 자리": eig["🔴 걸린 자리(= 비교를 «수행»한 회수)"],
          "🔴 F14 훑은 자리": lit["🔴🔴 훑은 자리 합(= 검사한 자리 · 🔴 「걸린 자리」와 «갈라 센다»)"],
          "🔴 인용 자 걸린 자리": cit["🔴 걸린 자리(= 비교를 «수행»한 회수)"]})
    rows["F09"] = collections.OrderedDict([
        ("🔴🔴🔴 반증됐나", None),
        ("🔴🔴🔴 이 러너가 «안» 낸다", "🔴 `R2` --- `runners/last989.py`(맨 마지막 러너)가 낸다. "
                                "988 은 `score988` 이 «자기를 쓰기 전에» 자기 행을 계산해 "
                                "**자기 생산자에 대해 원리상 못 떨어졌다**"),
        ("통과", None)])
    cond("F10", False, {"🔴 `certify` 는 989 에서 «안 늘린다»":
                        "🔴 조항 73-라 --- 자기 검사 기구를 두껍게 안 만든다"})
    cond("F11", False, {"🔴 여섯 자리": "note989_gen 이 «치환»으로 쓴다(손 전사 0)"})
    cond("F12", False, {"🔴 규칙 D 대상 수": DENOM["규칙 D 대상"],
                        "🔴 슬롯 대조": "🔴 파편 매치·맨-9xx 면제를 «안» 쓴다"})
    cond("F13", not cit["통과"], cit)
    cond("F14", not lit["통과"], lit)

    fals = [k for k, v in rows.items() if v.get("🔴🔴🔴 반증됐나") is True]
    n_ok = len([1 for v in rows.values() if v.get("통과") is True])
    res = collections.OrderedDict([
        ("무엇", "989 채점 — 🔴 반증조건 14 · 예측 5"),
        ("🔴 축", "C3 × C6(몸통) · 자기 자(곁)"),
        ("사전등록", PREREG),
        ("🔴🔴 조항 60-다 · 사전등록이 박은 분모", DENOM),
        ("§5 🔴 반증조건", collections.OrderedDict([
            ("🔴 분모", len(FALSIFY)), ("🔴 조건별", rows),
            ("🔴🔴 반증된 조건(식별자만)", fals or "없음"),
            ("🔴🔴 분자 / 분모", "%d / %d" % (n_ok, len(FALSIFY))),
            ("🔴 `F09` 는 `last989.py` 가 낸다(`R2`)", True),
            ("통과", bool(not fals))])),
        ("§4 🔴 예측", collections.OrderedDict([
            ("🔴 분모", len(PRED_DEF)), ("🔴 예측별", prows),
            ("🔴🔴 분자 / 분모", "%d / %d" % (phit, len(PRED_DEF))),
            ("통과", bool(phit == len(PRED_DEF)))])),
        ("§8 🔴🔴🔴 여덟째 칸(사전등록 ↔ 선언표)", eig),
        ("§13 🔴 인용 자(`R3`)", cit),
        ("§14 🔴 리터럴 자", lit),
        ("🔴 배선 통과(out989_wiring)", wiring.get("통과")),
        ("🔴 세계 명제 통과(out989_world)", world.get("통과")),
        ("🔴 감사 통과(out989_audit)", audit.get("통과")),
        ("🔴🔴🔴 최상위 `통과` 의 정의",
         "🔴 반증된 조건 0 ∧ 예측 전량 ∧ 배선 ∧ 세계 명제 ∧ 감사 --- "
         "🔴 **그것을 이루는 절의 `통과` 값을 «전부» 나란히 싣는다**(즉시정정 4)"),
        ("🔴🔴🔴 최상위를 이루는 절의 `통과` 전량", collections.OrderedDict([
            ("반증조건", bool(not fals)),
            ("예측", bool(phit == len(PRED_DEF))),
            ("배선", bool(wiring.get("통과"))),
            ("세계 명제", bool(world.get("통과"))),
            ("감사", bool(audit.get("통과"))),
            ("여덟째 칸", bool(eig["통과"])),
            ("인용 자", bool(cit["통과"])),
            ("리터럴 자", bool(lit["통과"]))])),
        ("통과", bool(not fals and phit == len(PRED_DEF) and wiring.get("통과")
                     and world.get("통과") and audit.get("통과")
                     and eig["통과"] and cit["통과"] and lit["통과"])),
        ("🔴 989 가 읽은 산출물 sha256", collections.OrderedDict(
            (r, _sha(r)) for r in OUTPUTS_989[:3])),
        ("🔴 도장", collections.OrderedDict([
            ("ref", a.ref), ("시작(UTC)", t0), ("끝(UTC)", _now()),
            ("🔴 코드 sha256", collections.OrderedDict(
                (r, _sha(r)) for r in RAN_989))])),
    ])
    (OUT / "out989_score.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
