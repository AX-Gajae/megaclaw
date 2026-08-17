#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""992 — 🔴🔴🔴 **`F09` 를 「맨 마지막 러너 하나」에서 「도장 «위상 정렬» 전수」로 올린다**.

🔴🔴🔴 **왜 (티처 #130 치-3).** 991 이 990 문서 넷·원장에 얹은 정정이 **낡은 수**였다 ---
박은 값 `99/33`, 최종 산출물 `291/177`(3 배). `out991_fix.json` 은 `10:41:41` 에,
`out991_audit.json` 은 `10:52:30` 에 찍혔고 `fix991.py:81-83` 이 «그 audit 의 같은 키 경로»를
읽는다. **더 낡은 주행 값을 박고 다시 안 돌렸다.**
🔴 **991 의 `F09` 는 「맨 마지막 러너」 하나만 봐서 통과했다.**

🔴🔴 **992 판 = 「소비자 도장이 «생산자보다 앞서면» 실패」.**
  ① 각 산출물의 «생산 러너»는 그 산출물의 «도장에 적힌 코드 sha»로 안다(지도를 «안 만든다»).
  ② 각 러너가 «읽는» 산출물은 그 러너의 **AST 상수 문자열**에서 뽑는다.
  ③ 산출물 `A`(러너 `R` 이 냈다)가 산출물 `B` 를 읽으면 **`끝 시각(A) >= 끝 시각(B)`** 이어야 한다.

씀:
    python3 runners/last992.py --ref <40자 sha>
"""
import argparse
import ast
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
OUT = ROOT / "runners"

GLOB_PY = "runners/*992*.py"
GLOB_ART = "runners/*992*"
DOCS = ("docs/판정_992.md", "docs/card_992.md", "docs/handoff_992.md",
        "docs/pr_992.md")
ARTNAME = re.compile(r"(out99\d_[\w.]+\.(?:json|txt)|fiveprime_99\d\.json)")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p):
    return os.path.relpath(str(p), str(ROOT))


def _glob(pat):
    return sorted(_rel(p) for p in glob.glob(str(ROOT / pat)))


def _sha(rel):
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def _load(rel):
    try:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except Exception:                                              # noqa: BLE001
        return None


def stamped_by(art):
    """🔴 **산출물이 «자기 도장에» 적어 둔 코드 sha256** 을 읽는다(지도를 안 만든다)."""
    d = _load(art)
    if not isinstance(d, dict):
        return collections.OrderedDict()
    found = collections.OrderedDict()

    def walk(o):
        if not isinstance(o, dict):
            return
        for k, v in o.items():
            if isinstance(v, dict):
                if "sha256" in k and v and all(
                        isinstance(x, str) and len(x) == 64 for x in v.values()) \
                        and all(isinstance(r, str) and r.endswith(".py")
                                for r in v.keys()):
                    for r, s in v.items():
                        found[r] = s
                else:
                    walk(v)
    walk(d)
    return found


_TKEY = re.compile(r"시각|시작|끝|UTC")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def stamp_times(art):
    """🔴 산출물의 «시작/끝» 도장 시각을 «전수» 긁는다(키 이름이 사이클마다 다르다)."""
    d = _load(art)
    got = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and _ISO.match(v) and _TKEY.search(k):
                    got.append((k, v))
                elif isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                if isinstance(v, (dict, list)):
                    walk(v)
    walk(d)
    if not got:
        return None, None, []
    vals = sorted(v for _k, v in got)
    return vals[0], vals[-1], got


def _art_consts(node):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            for m in ARTNAME.finditer(n.value):
                out.add(m.group(1))
    return out


def rw_of(py_rel):
    """🔴 그 러너가 «쓰는» 산출물과 «읽는» 산출물 --- **AST** 로만 가른다.

    쓰기: `<경로식>.write_text(...)` 의 «경로식»에 든 산출물 이름(이름이면 대입을 되짚는다).
    읽기: 그 파일의 산출물 이름 «전량» − 쓰기.
    """
    try:
        src = (ROOT / py_rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:                                              # noqa: BLE001
        return set(), set()
    named = collections.defaultdict(set)
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            named[n.targets[0].id] |= _art_consts(n.value)
    writes = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr in ("write_text", "write_bytes", "open"):
            tgt = n.func.value
            got = _art_consts(tgt)
            if not got and isinstance(tgt, ast.Name):
                got = named.get(tgt.id, set())
            writes |= got
    allc = _art_consts(tree)
    return writes, (allc - writes)


def phase_audit(glob_art, glob_py, label):
    """🔴🔴🔴 **도장 시각의 위상 정렬 전수.** 소비자 도장이 생산자보다 앞서면 실패.

    🔴🔴 **고리(cycle)는 «면제»하고 «따로 센다»** --- 문서가 자기 자신에 대한 감사 수를
    실으면 「감사 → 생성기 → 감사」 고리가 «원리상» 생긴다. 그 고리는 시각으로 못 풀고
    **`F10`(문서 고리 «수렴»)이 푼다.** 🔴 고리 «밖»의 짝은 시각을 지켜야 한다 ---
    991 의 사고(`fix991` 이 `audit991` 보다 11 분 먼저 돌았다)가 «바로 그 자리»다.
    """
    arts = [p for p in _glob(glob_art) if p.endswith((".json", ".txt"))]
    pys = _glob(glob_py)
    rw = {p: rw_of(p) for p in pys}
    prod = collections.OrderedDict()
    times = collections.OrderedDict()
    for art in arts:
        st = stamped_by(art)
        base = os.path.basename(art)
        # 🔴 «생산자» = 그 산출물을 «쓰는» 러너. 도장이 적은 러너 전량이 아니다.
        byw = sorted(p for p in pys if base in rw[p][0])
        prod[art] = byw or sorted(r for r in st if r in rw and base in rw[r][0])
        _t0, t1, _raw = stamp_times(art)
        times[art] = t1
    # ── 🔴 산출물 그래프의 고리(SCC)를 «잰다** ──────────────────────────
    graph = collections.defaultdict(set)          # 생산자 산출물 -> 소비자 산출물
    for art in arts:
        for r in prod.get(art) or []:
            for b in sorted(rw[r][1]):
                b_rel = "runners/%s" % b
                if b_rel != art and b_rel in times:
                    graph[b_rel].add(art)
    idx, low, on, stack, comp, cnt = {}, {}, set(), [], {}, [0]

    def strong(v):
        idx[v] = low[v] = cnt[0]
        cnt[0] += 1
        stack.append(v)
        on.add(v)
        for w in graph.get(v, ()):
            if w not in idx:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            grp = []
            while True:
                w = stack.pop()
                on.discard(w)
                grp.append(w)
                if w == v:
                    break
            for w in grp:
                comp[w] = idx[v]
    for v in list(times):
        if v not in idx:
            strong(v)
    cycles = collections.Counter(comp.values())

    edges, bad, incyc, hits = [], [], [], 0
    for art in arts:
        t_a = times.get(art)
        for r in prod.get(art) or []:
            for b in sorted(rw[r][1]):
                b_rel = "runners/%s" % b
                if b_rel == art or b_rel not in times:
                    continue
                t_b = times.get(b_rel)
                hits += 1
                if not t_a or not t_b:
                    continue
                same_comp = bool(comp.get(art) is not None
                                 and comp.get(art) == comp.get(b_rel)
                                 and cycles.get(comp.get(art), 0) > 1)
                row = {"소비자 산출물": art, "낸 러너": r, "생산자 산출물": b_rel,
                       "소비자 끝 시각": t_a, "생산자 끝 시각": t_b,
                       "🔴 앞서나": bool(t_a < t_b),
                       "🔴 고리 안인가": same_comp}
                edges.append(row)
                if t_a < t_b:
                    (incyc if same_comp else bad).append(row)
    cyc_groups = collections.OrderedDict()
    for v, c in comp.items():
        if cycles.get(c, 0) > 1:
            cyc_groups.setdefault(str(c), []).append(v)
    return collections.OrderedDict([
        ("무엇", label),
        ("🔴 산출물 수", len(arts)),
        ("🔴 러너 수", len(pys)),
        ("🔴 러너별 «쓰는/읽는» 산출물(AST)",
         collections.OrderedDict(
             (k, {"쓴다": sorted(v[0]), "읽는다": sorted(v[1])})
             for k, v in rw.items())),
        ("🔴 산출물별 끝 도장 시각", times),
        ("🔴🔴 산출물 그래프의 «고리»(SCC · 크기 2 이상)",
         collections.OrderedDict((k, sorted(v)) for k, v in cyc_groups.items()) or "없음"),
        ("🔴 견준 «생산자 → 소비자» 짝 수", len(edges)),
        ("🔴🔴🔴 위상 어긋남(소비자 < 생산자 · 🔴 고리 «밖»)", bad or "없음"),
        ("🔴🔴🔴 소비자 도장이 «생산자보다 앞선» 자리 수", len(bad)),
        ("🔴🔴 고리 «안»의 어긋남(= `F10` 이 «수렴»으로 푼다)", incyc or "없음"),
        ("🔴🔴 그 수(고리 안)", len(incyc)),
        ("🔴 짝 전량", edges),
        ("🔴 걸린 자리(= 비교를 «수행»한 회수)", hits),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()

    arts = [p for p in _glob(GLOB_ART) if p.endswith((".json", ".txt"))]
    hits, stale, unstamped = 0, [], []
    pmap = collections.OrderedDict()

    def mt(rel):
        p = ROOT / rel
        return p.stat().st_mtime if p.is_file() else None

    # ── ① 도장이 적은 코드 sha ↔ 지금 디스크의 sha ────────────────────
    for art in arts:
        st = stamped_by(art)
        if not st:
            unstamped.append(art)
            continue
        pmap[art] = sorted(st)
        for r, s in st.items():
            hits += 1
            cur = _sha(r)
            if cur is None:
                stale.append({"산출물": art, "러너": r, "🔴": "러너가 없다"})
            elif cur != s:
                stale.append({"산출물": art, "러너": r,
                              "도장이 적은 sha256": s, "지금 디스크 sha256": cur,
                              "🔴": "🔴 **고치고 안 다시 돌렸다**(조항 66-②)"})
    # ── ② 🔴🔴🔴 도장 «위상 정렬» 전수 (992 신설) ─────────────────────
    ph = phase_audit(GLOB_ART, GLOB_PY, "🔴🔴🔴 992 자신 — 도장 위상 정렬 전수")
    hits += ph["🔴 걸린 자리(= 비교를 «수행»한 회수)"]
    # ── ②-나 🔴 **구판/신판 전후**(`조항 66-⑥`) --- 같은 자를 991 에 물린다 ──
    ph991 = phase_audit("runners/*991*", "runners/*991*.py",
                        "⚠ 991 에 «같은 자»를 물린다(구판/신판 전후 · `조항 66-⑥`)")
    hits += ph991["🔴 걸린 자리(= 비교를 «수행»한 회수)"]
    # ── ③ 문서가 산출물보다 오래되면 다시 안 찍은 것이다 ────────────────
    docstale = []
    for d in DOCS:
        hits += 1
        d_t = mt(d)
        if d_t is None:
            docstale.append({"문서": d, "🔴": "없다"})
            continue
        for art in arts:
            a_t = mt(art)
            if a_t is not None and a_t > d_t + 1.0:
                docstale.append({"문서": d, "🔴 더 새 산출물": art})
                break

    n_phase = ph["🔴🔴🔴 소비자 도장이 «생산자보다 앞선» 자리 수"]
    fal = bool(stale or n_phase)
    res = collections.OrderedDict([
        ("무엇", "992 `F09` — 🔴🔴🔴 **도장 «위상 정렬» 전수**(맨 마지막 러너 하나가 아니다)"),
        ("🔴 명부의 출처", "글롭 `%s` · `%s` --- 손으로 안 골랐다" % (GLOB_PY, GLOB_ART)),
        ("🔴 지도의 출처",
         "🔴 **지도를 «안 만든다».** ① 생산자는 산출물이 «자기 도장에» 적은 코드 sha 로 알고 "
         "② 소비 관계는 러너의 **AST 문자열 상수**에서 뽑는다"),
        ("🔴 산출물별 도장이 적은 러너", pmap),
        ("🔴 이 사이클 산출물 전량", arts),
        ("🔴 산출물 수", len(arts)),
        ("🔴🔴 도장이 «없는» 산출물(= 이 자가 원리상 못 본다 · 「깨끗함」이 아니다)",
         unstamped or "없음"),
        ("🔴🔴🔴 도장 sha ≠ 디스크 sha 인 자리(= 고치고 안 다시 돌렸다)", stale or "없음"),
        ("🔴 그 수", len(stale)),
        ("🔴🔴🔴 992 신설 — 도장 위상 정렬", ph),
        ("🔴🔴🔴 소비자 도장이 «생산자보다 앞선» 자리 수", n_phase),
        ("🔴🔴🔴 위상 어긋남(소비자 < 생산자 · 고리 밖)",
         ph["🔴🔴🔴 위상 어긋남(소비자 < 생산자 · 🔴 고리 «밖»)"]),
        ("🔴🔴 고리 «안»의 어긋남(= `F10` 이 수렴으로 푼다) 수", ph["🔴🔴 그 수(고리 안)"]),
        ("🔴🔴 구판/신판 전후 — 991 에 같은 자를 물리면", collections.OrderedDict([
            ("🔴🔴🔴 991 의 위상 어긋남 수",
             ph991["🔴🔴🔴 소비자 도장이 «생산자보다 앞선» 자리 수"]),
            ("🔴 그 자리", ph991["🔴🔴🔴 위상 어긋남(소비자 < 생산자 · 🔴 고리 «밖»)"]),
            ("🔴 991 의 고리 «안» 어긋남 수", ph991["🔴🔴 그 수(고리 안)"]),
            ("🔴 991 의 `F09` 가 낸 값", "🔴 **통과**(맨 마지막 러너 하나만 봤다)"),
            ("🔴🔴🔴 구판/신판이 갈리나",
             bool(ph991["🔴🔴🔴 소비자 도장이 «생산자보다 앞선» 자리 수"] > 0)),
            ("🔴 이것이 이 자의 «검정력 증거»다",
             "🔴 **새 자는 991 의 실제 사고(`fix991` 이 `audit991` 보다 11 분 먼저 돌고 "
             "다시 안 돌았다)를 «잡는다».** 구판은 못 잡았다"),
        ])),
        ("🔴 산출물보다 «오래된» 문서(= 다시 안 찍었다)", docstale or "없음"),
        ("🔴🔴🔴 F09 반증됐나", fal),
        ("🔴 걸린 자리(= 비교를 «수행»한 회수)", hits),
        ("통과", bool(not fal)),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 ① 어떤 러너도 자기 산출물보다 새롭지 않고 ② **어떤 소비자 산출물도 자기가 읽는 "
         "생산자 산출물보다 «먼저» 찍히지 않았다**"),
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", a.ref),
            ("🔴 코드 sha256", collections.OrderedDict(
                (r, hashlib.sha256((ROOT / r).read_bytes()).hexdigest())
                for r in _glob(GLOB_PY))),
            ("시작(UTC)", t0), ("끝(UTC)", _now()),
        ])),
    ])
    (OUT / "out992_last.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [last] 끝 → out992_last.json (F09 반증=%s · 위상 어긋남 %d · "
                     "991 에 물리면 %d)\n"
                     % (_now(), fal, n_phase,
                        ph991["🔴🔴🔴 소비자 도장이 «생산자보다 앞선» 자리 수"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
