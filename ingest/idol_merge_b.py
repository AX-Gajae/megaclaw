"""아이돌 W-B 병합 — 초동 라벨 보강 + 사전 신호를 기존 250 레코드에 합류.

라벨: 기존이 없으면 채우고, 있으면 교차검증 기록(계열이 다르면 덮어쓰지 않음).
신호: 데뷔 전 시점 정보만(누출 차단) — preorder/teaser/sns/showcase/buzz.

사용: python3 -m ingest.idol_merge_b
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

REC = Path("data/idol_records")
LOG = Path("cycle_log/idol_merge_b.jsonl")


def norm(s) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", str(s))
    s = re.sub(r"\(.*?\)", "", s)
    return re.sub(r"[^0-9A-Za-z가-힣]", "", s).lower()


def grade(row: dict) -> tuple[str, str]:
    """basis 필드가 자유서술로 오는 경우가 있어 키워드로 판정(W-C 대응)."""
    basis = str(row.get("chodong_basis") or "unknown").lower()
    note = str(row.get("chodong_note") or "")
    blob = basis + " " + note
    if "닐슨" in blob or "빌보드" in blob or "미국" in blob:
        return "E", "해외 집계(국내 초동과 계열 상이) — 앵커 사용 주의"
    if "하한값" in note or "**" in note or "마스킹" in note:
        return "C", "마스킹 하한값"
    if "hanteo" in blob or "한터" in blob:
        return "B", "한터 계열"
    if "namu" in blob or "나무위키" in blob or "위키" in blob:
        return "C", "위키 전사"
    if "circle" in blob or "써클" in blob or "가온" in blob:
        return "D", "써클 주간(정의 상이)"
    if "press" in blob or "언론" in blob or "보도" in blob:
        return "C", "언론 인용"
    return "D", "계열 불명"


import sys
LABEL_FILE = sys.argv[1] if len(sys.argv) > 1 else "data/idol_raw/wave_b_labels.jsonl"


def main() -> int:
    recs = {}
    for p in REC.glob("*.json"):
        r = json.loads(p.read_text())
        recs[norm(r.get("group_name"))] = (p, r)

    log = open(LOG, "a")
    filled = cross = newrec = sig = 0
    # ── 라벨 ──
    for line in Path(LABEL_FILE).read_text().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not row.get("chodong"):
            continue
        k = norm(row.get("group_name"))
        if k not in recs:
            rid = f"IDOL-{(row.get('debut_date') or '0000')[:4]}-B{newrec:03d}"
            rec = dict(row)
            rec.update({"record_id": rid, "tier": "idol_debut",
                        "ingested_from": "crawl wave-B (2026-07-27)"})
            g, why = grade(row)
            rec["label_trust"] = {"grade": g, "why": why, "basis": row.get("chodong_basis")}
            p = REC / f"{rid}.json"
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
            recs[k] = (p, rec)
            newrec += 1
            continue
        p, r = recs[k]
        if not r.get("chodong"):
            r["chodong"] = row["chodong"]
            for f in ("chodong_basis", "chodong_note", "chodong_source_quote",
                      "chodong_source_url", "chodong_source_date", "debut_album"):
                if row.get(f):
                    r[f] = row[f]
            g, why = grade(row)
            r["label_trust"] = {"grade": g, "why": why, "basis": row.get("chodong_basis")}
            p.write_text(json.dumps(r, ensure_ascii=False, indent=2))
            filled += 1
        else:
            diff = abs(r["chodong"] - row["chodong"]) / max(1, r["chodong"])
            log.write(json.dumps({"group": row.get("group_name"), "existing": r["chodong"],
                                   "wave_b": row["chodong"], "diff": round(diff, 3),
                                   "basis_existing": r.get("chodong_basis"),
                                   "basis_b": row.get("chodong_basis")}, ensure_ascii=False) + "\n")
            if diff > 0.10:
                cross += 1
    # ── 사전 신호 ──
    for line in Path("data/idol_raw/wave_b_signals.jsonl").read_text().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        k = norm(row.get("group_name"))
        if k not in recs:
            continue
        p, r = recs[k]
        pre = {f: row.get(f) for f in ("preorder", "teaser_views", "sns_followers_debut",
                                        "showcase_scale", "predebut_buzz_note")
               if row.get(f)}
        if not pre:
            continue
        pre["source"] = "crawl wave-B (데뷔 전 시점 정보만)"
        r["pre_debut_signals"] = pre
        p.write_text(json.dumps(r, ensure_ascii=False, indent=2))
        sig += 1

    recs2 = [json.loads(p.read_text()) for p in REC.glob("*.json")]
    lab = [r for r in recs2 if r.get("chodong")]
    with_sig = [r for r in recs2 if r.get("pre_debut_signals")]
    both = [r for r in recs2 if r.get("chodong") and r.get("pre_debut_signals")]
    print(json.dumps({"라벨 충전": filled, "신규 레코드": newrec, "교차 불일치": cross,
                       "신호 적재": sig, "─": "─",
                       "총 레코드": len(recs2), "초동 라벨": len(lab),
                       "사전신호 보유": len(with_sig), "라벨+신호 동시": len(both)},
                      ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
