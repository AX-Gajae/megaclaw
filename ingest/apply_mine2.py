"""재채굴 결과 적용 — 없던 라벨을 새로 붙인다.

기존 라벨을 고치는 것(apply_relabel)과 다르다. 여기서는 **비어 있던 자리를 채우므로**
잘못 붙이면 그 레코드가 통째로 거짓 정답지가 된다. 그래서 조건을 좁게 건다:

  found=true 이고 visitors 가 있어야 한다. 매출만 있으면 매출만 붙인다.
  origin='measured' 가 아니면 등급을 올리지 않는다(derived → E, unknown → E).
  일별 계열이 있고 합이 총계와 맞으면 A, 그 외 measured는 B.

이번 라운드가 밝힌 것 — 이전 채굴 실패의 원인은 '문서를 못 읽어서'가 아니었다:
  · MCP는 pptx **차트 XML을 구조적으로 못 본다**. 축 라벨과 계열명만 돌려주고
    데이터 값을 전부 누락한다. RCPU2410의 13일치 입장 9,567명이 차트 안에 있었고,
    REST+unzip 후 ppt/charts/chart1.xml의 c:val 파싱으로만 복원됐다.
  · MCP는 xlsx를 좌표 없는 쉼표 뭉치로 뱉는다. 이전 패스는 그걸 '표가 깨졌다'고
    판정하고 포기했는데, RCCP2517의 13일 일별표는 그 출력 안에 처음부터 있었다.
병목은 판독 접근이 아니라 **파싱 끈기**였다.

사용:
  python3 -m ingest.apply_mine2            # 무엇이 붙는지
  python3 -m ingest.apply_mine2 --write    # 적용
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

MINE = Path("cycle_log/mine2")
RECORDS = Path("data/records")
STAMP = "mine2 (2026-07-28)"
UNIT = {"entry": "entry", "participation": "participation", "exposure": "exposure",
        "purchase": "purchase", "digital_proxy": "unknown"}


def grade_of(res: dict, daily_ok: bool) -> tuple[str, str]:
    o = res.get("origin")
    if o != "measured":
        return "E", f"origin={o} — 실측이 아니므로 평가 풀에서 제외"
    if not res.get("instrument"):
        return "E", "measured라 했으나 계측 도구가 명시되지 않음"
    if daily_ok:
        return "A", f"실측 확정 — 계측 {res['instrument'][:60]} · 일별 계열이 총계와 일치"
    return "B", f"실측 확정 — 계측 {res['instrument'][:60]} · 일별 계열 없음/불일치"


def plan(res: dict, rec: dict) -> dict:
    o = rec["outcome"]
    act = {"code": res["code"], "adds": [], "grade": None}
    if not res.get("found"):
        act["skip"] = res.get("missing") or "found=false"
        return act
    v, s = res.get("visitors"), res.get("sales_krw")
    # 필드별로 판단한다. 매출이 이미 있다는 이유로 새 방문 라벨까지 버리면 안 된다.
    if v and o["totals"].get("visitors"):
        act["skip"] = f"방문 라벨이 이미 있음({o['totals']['visitors']:,}) — 덮어쓰지 않는다"
        return act

    daily = [d for d in (res.get("daily") or []) if d.get("date")]
    dsum = sum(d.get("visitors") or 0 for d in daily)
    daily_ok = bool(v and dsum and abs(dsum - v) / v <= 0.02)

    if v:
        g, why = grade_of(res, daily_ok)
        act["grade"], act["why"] = g, why
        act["adds"].append(f"visitors {v:,} ({res.get('counting')}/{res.get('origin')}) 등급 {g}")
    if s and not o["totals"].get("sales_krw"):
        act["adds"].append(f"sales_krw {s:,.0f}")
    if daily:
        act["adds"].append(f"daily {len(daily)}행"
                           + (f" (합 {dsum:,} — 총계와 일치)" if daily_ok else ""))
    if res.get("legs"):
        act["adds"].append(f"레그 {len(res['legs'])}건 기록")
    if not act["adds"]:
        act["skip"] = "붙일 수치가 없음"
    return act


def apply(rec: dict, res: dict, act: dict) -> None:
    o = rec["outcome"]
    t = o.setdefault("totals", {})
    if res.get("visitors"):
        t["visitors"] = res["visitors"]
        o["counting_method"] = UNIT.get(res.get("counting") or "", "unknown")
        o["counting_detail"] = res.get("counting")
        o["label_trust"] = {"grade": act["grade"], "why": act["why"]}
        if res.get("instrument"):
            o["measurement_instrument"] = res["instrument"]
    if res.get("sales_krw") and not t.get("sales_krw"):
        t["sales_krw"] = res["sales_krw"]
    if res.get("daily"):
        o["daily"] = res["daily"]
    if res.get("legs"):
        o["legs"] = res["legs"]
    o.setdefault("provenance", {}).update(
        {"source": STAMP, "evidence": str(res.get("evidence") or "")[:600],
         "column_quote": str(res.get("column_quote") or "")[:200],
         "docs_opened": res.get("docs_opened")})
    o.setdefault("label_history", []).append(
        {"at": STAMP, "action": "mine", "changes": act["adds"],
         "origin": res.get("origin"), "instrument": res.get("instrument"),
         "evidence": str(res.get("evidence") or "")[:400]})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    files = sorted(MINE.glob("*.json"))
    if not files:
        print("재채굴 결과 없음")
        return 0
    done, skipped = [], []
    for f in files:
        res = json.loads(f.read_text())
        p = RECORDS / f"{res['code']}.json"
        if not p.exists():
            continue
        rec = json.loads(p.read_text())
        act = plan(res, rec)
        if act.get("skip"):
            skipped.append((act["code"], act["skip"]))
            continue
        done.append(act)
        if a.write:
            apply(rec, res, act)
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    nv = sum(1 for x in done if x["grade"])
    print(json.dumps({"결과 파일": len(files), "적용": len(done),
                      "방문 라벨 신규": nv, "건너뜀": len(skipped),
                      "기록": bool(a.write)}, ensure_ascii=False))
    for x in done:
        print(f"\n■ {x['code']}")
        for s in x["adds"]:
            print(f"   {s}")
    if skipped:
        print("\n■ 건너뜀")
        for c, why in skipped:
            print(f"   {c:10s} {why[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
