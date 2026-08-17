#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""989 `R2` — 🔴🔴🔴 **맨 마지막 러너**. `조항 66-②`(`F09`)를 «여기서만» 낸다.

🔴 **왜.** 988 은 `score988` 이 **자기를 쓰기 «전에» 자기 행을 계산**해서
   **「자기 생산자에 대해 원리상 못 떨어졌다」** --- `out988_table.json` 이 기록한
   `out988_score.json` 지문(`d5f09e0e…`)과 최종 트리 실제 지문(`9209ab54…`)이 «다르다».
🔴 **989 판**: 이 러너가 **모든 산출물과 모든 러너를 «맨 나중에»** 훑는다.
   **이 러너 자신은 `통과` 키를 내지 않는 산출물을 안 만든다** --- 자기 지문도 싣는다.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
OUT = ROOT / "runners"

RUNNERS = ("runners/world989.py", "runners/audit989.py", "runners/score989.py",
           "runners/last989.py", "runners/note989_gen.py")
OUTPUTS = ("runners/out989_wiring.json", "runners/out989_world.json",
           "runners/out989_audit.json", "runners/out989_score.json")
DOCS = ("docs/판정_989.md", "docs/card_989.md", "docs/handoff_989.md",
        "docs/pr_989.md")

#: 🔴🔴🔴 **러너 → 그 러너가 «만드는» 산출물.**
#: 🔴 **구판(첫 주행)은 「모든 러너 × 모든 산출물」을 견줬다** --- `audit989.py` 가
#: `out989_wiring.json` 보다 나중이라고 떨어뜨리는데 **그 러너는 그 산출물을 «안 만든다».**
#: 🔴 **신판은 「생산자」만 견준다.** 자를 고쳤고 구판/신판을 둘 다 싣는다(`조항 66-③`).
PRODUCES = collections.OrderedDict([
    ("runners/world989.py", ("runners/out989_wiring.json", "runners/out989_world.json")),
    ("runners/audit989.py", ("runners/out989_audit.json",)),
    ("runners/score989.py", ("runners/out989_score.json",)),
    ("runners/last989.py", ()),
    ("runners/note989_gen.py", ()),
])


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(rel):
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def _mtime(rel):
    p = ROOT / rel
    return p.stat().st_mtime if p.is_file() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()

    run_m = collections.OrderedDict((r, _mtime(r)) for r in RUNNERS)
    out_m = collections.OrderedDict((r, _mtime(r)) for r in OUTPUTS)
    doc_m = collections.OrderedDict((r, _mtime(r)) for r in DOCS)

    # ── ① 러너가 «산출물보다 나중에» 고쳐졌나 ─────────────────────
    stale, stale_old = [], []
    for r, tm in run_m.items():
        if tm is None:
            continue
        for o, to in out_m.items():
            if to is not None and tm > to + 1.0:
                stale_old.append({"러너": r, "산출물": o,
                                  "🔴 러너가 더 나중": round(tm - to, 1)})
                if o in PRODUCES.get(r, ()):
                    stale.append({"러너": r, "🔴 그 러너가 «만드는» 산출물": o,
                                  "🔴 러너가 더 나중(초)": round(tm - to, 1)})
    # ── ② 문서가 «채점 산출물보다 나중에» 다시 찍혔나 ─────────────
    sc = out_m.get("runners/out989_score.json")
    doc_stale = [d for d, tm in doc_m.items()
                 if tm is not None and sc is not None and tm < sc - 1.0]
    # ── ③ 산출물이 기록한 자기 코드 지문 == 디스크 지문 ────────────
    fp = collections.OrderedDict()
    for o in OUTPUTS:
        p = ROOT / o
        if not p.is_file():
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        rec = ((obj.get("🔴 도장") or {}).get("🔴 코드 sha256(끝)")
               or (obj.get("🔴 도장") or {}).get("🔴 코드 sha256") or {})
        bad = collections.OrderedDict()
        for rel, want in (rec or {}).items():
            got = _sha(rel)
            if want and got and want != got:
                bad[rel] = {"산출물이 기록한 것": want, "🔴 디스크": got}
        fp[o] = collections.OrderedDict([
            ("🔴 기록한 러너 수", len(rec or {})),
            ("🔴🔴🔴 지문이 다른 러너", bad or "없음")])

    n_bad = sum(0 if v["🔴🔴🔴 지문이 다른 러너"] == "없음"
                else len(v["🔴🔴🔴 지문이 다른 러너"]) for v in fp.values())
    fals = bool(stale or doc_stale or n_bad)
    res = collections.OrderedDict([
        ("무엇", "989 `R2` — 🔴🔴🔴 **맨 마지막 러너**가 `조항 66-②`(`F09`)를 낸다"),
        ("🔴 왜 `score989` 가 «안» 내나",
         "🔴 988 은 `score988` 이 «자기를 쓰기 전에» 자기 행을 계산해 "
         "**자기 생산자에 대해 원리상 못 떨어졌다**"),
        ("🔴 러너 mtime", collections.OrderedDict(
            (k, (None if v is None else round(v, 1))) for k, v in run_m.items())),
        ("🔴 산출물 mtime", collections.OrderedDict(
            (k, (None if v is None else round(v, 1))) for k, v in out_m.items())),
        ("🔴🔴 ① «자기가 만드는» 산출물보다 나중에 고쳐진 러너(신판)", stale or "없음"),
        ("⚠ ① 구판(모든 러너 × 모든 산출물 · 🔴 «생산자가 아닌» 짝까지 센다)",
         stale_old or "없음"),
        ("🔴 러너 → 산출물 지도", collections.OrderedDict(
            (k, list(v)) for k, v in PRODUCES.items())),
        ("🔴🔴 ② 채점 산출물보다 «먼저» 찍힌 문서", doc_stale or "없음"),
        ("🔴🔴 ③ 산출물이 기록한 코드 지문 ↔ 디스크", fp),
        ("🔴🔴🔴 ③ 지문이 다른 러너 수", n_bad),
        ("🔴 걸린 자리(= 비교를 «수행»한 회수)",
         len(RUNNERS) * len(OUTPUTS) + len(DOCS) + sum(v["🔴 기록한 러너 수"]
                                                       for v in fp.values())),
        ("🔴🔴🔴 F09 반증됐나", fals),
        ("통과", bool(not fals)),
        ("🔴 이 러너 자신의 sha256", _sha("runners/last989.py")),
        ("🔴 도장", collections.OrderedDict([
            ("ref", a.ref), ("끝(UTC)", _now()),
            ("🔴 코드 sha256(끝)", collections.OrderedDict(
                (r, _sha(r)) for r in RUNNERS))])),
    ])
    (OUT / "out989_last.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
