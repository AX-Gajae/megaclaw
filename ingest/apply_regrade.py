"""등급 검증 결과 적용 — 등급을 올리는 것은 평가 풀을 바꾸는 일이다.

라벨을 고치는 것보다 조심해야 한다. 값이 틀리면 그 한 건이 틀리지만, 등급을 잘못 올리면
그 라벨이 평가 풀에 들어와 **모든 측정이 오염된다**. 그래서 승급 조건을 좁게 건다:

  origin='measured' 이고 instrument(계측 도구)가 명시돼야 한다.
  derived·reused·unknown은 현 등급 유지.
  resolved=false도 현 등급 유지.

등급 제안은 에이전트가 하지만 우리가 검산한다:
  measured + 일별 완결 + 계측 도구 명시           → A 허용
  measured + 계측 단위에 가정(1인당 vs 1팀당 등)   → B 상한
  그 외                                          → 유지

강등도 한다. 검증에서 derived로 판명됐는데 현재 A·B면 내린다 — 승급만 하는 검증은
평가 풀을 한 방향으로만 부풀린다.

사용:
  python3 -m ingest.apply_regrade            # 무엇이 어떻게 바뀌는지
  python3 -m ingest.apply_regrade --write    # 적용
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RESULTS = Path("cycle_log/regrade")
RECORDS = Path("data/records")
STAMP = "regrade R1 (2026-07-28)"
ORDER = ["A", "B", "C", "D", "E"]


def decide(res: dict, rec: dict) -> dict:
    o = rec["outcome"]
    cur = (o.get("label_trust") or {}).get("grade")
    ls = o.get("label_scope") or {}
    act = {"code": res["code"], "cur": cur, "new": cur, "why": "", "changed": False}

    if not res.get("resolved"):
        act["why"] = f"미확정 — {str(res.get('missing') or '')[:90]}"
        return act

    origin = res.get("origin")
    if origin in ("derived", "reused"):
        # 강등: 유도치인데 A·B면 평가 풀에서 빼야 한다
        if cur in ("A", "B"):
            act["new"] = "E"
            act["why"] = f"{origin}로 확정 — 평가 풀에서 제외"
        else:
            act["why"] = f"{origin}로 확정 — 현 등급 {cur} 유지"
    elif origin == "measured":
        if not res.get("instrument"):
            act["why"] = "measured라 했으나 계측 도구가 없음 — 유지"
        else:
            complete = ls.get("sum_agrees") is True
            prop = res.get("proposed_grade")
            cap = "A" if complete else "B"
            new = prop if prop in ORDER else cap
            if ORDER.index(new) < ORDER.index(cap):   # 제안이 상한보다 높으면 상한으로
                new = cap
            if ORDER.index(new) < ORDER.index(cur or "E"):
                act["new"] = new
                act["why"] = (f"측정 확정 — 계측 {res['instrument'][:50]}"
                              f"{' · 일별 완결' if complete else ' · 일별 불완결이라 B 상한'}")
            else:
                act["why"] = f"측정 확정이나 제안 등급 {new} 이 현 등급 {cur} 보다 낮음 — 유지"
    else:
        act["why"] = "origin=unknown — 유지"

    act["changed"] = act["new"] != act["cur"]
    return act


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    files = sorted(RESULTS.glob("*.result.json"))
    if not files:
        print("등급 검증 결과 없음 — 에이전트 산출을 기다린다")
        return 0
    ups, downs, keeps = [], [], []
    for f in files:
        res = json.loads(f.read_text())
        p = RECORDS / f"{res['code']}.json"
        if not p.exists():
            continue
        rec = json.loads(p.read_text())
        act = decide(res, rec)
        if not act["changed"]:
            keeps.append(act)
            continue
        (ups if ORDER.index(act["new"]) < ORDER.index(act["cur"] or "E") else downs).append(act)
        if a.write:
            tr = rec["outcome"].setdefault("label_trust", {})
            tr["regraded_from"] = act["cur"]
            tr["grade"] = act["new"]
            tr["why"] = act["why"]
            rec["outcome"].setdefault("label_history", []).append(
                {"at": STAMP, "action": "regrade",
                 "changes": [f"등급 {act['cur']} → {act['new']}"],
                 "verdict": act["why"], "origin": res.get("origin"),
                 "instrument": res.get("instrument"),
                 "column_quote": str(res.get("column_quote") or "")[:200],
                 "evidence": str(res.get("evidence") or "")[:400]})
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=1))

    print(json.dumps({"결과 파일": len(files), "승급": len(ups), "강등": len(downs),
                      "유지": len(keeps), "기록": bool(a.write)}, ensure_ascii=False))
    for tag, rows in (("승급", ups), ("강등", downs)):
        if rows:
            print(f"\n■ {tag}")
            for x in rows:
                print(f"   {x['code']:10s} {x['cur']} → {x['new']}   {x['why'][:90]}")
    if keeps:
        print("\n■ 유지")
        for x in keeps:
            print(f"   {x['code']:10s} {x['cur']}   {x['why'][:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
