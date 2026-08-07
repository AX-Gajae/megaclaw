"""아이돌 도메인 레코드 편입 — 수집 JSONL → data/idol_records/ + 라벨 신뢰등급.

팝업 도메인에서 확립한 규칙을 그대로 이식한다:
  · 중복제거: 정규화 그룹명 + 데뷔일(±14일) 기준, 풍부한 행 우선
  · 라벨 단위 명시: chodong_basis(hanteo/circle/namu/press) — **계열 혼용 금지**
  · 신뢰등급 A~E:
      A  한터 공식 인증/정확 정수 + 언론 1차 인용
      B  hanteo 계열 정확 정수(언론 전재)
      C  namu 마스킹 하한값("83,5**") 또는 press 반올림("8만장")
      D  circle 주간(달력주 — 초동 정의와 어긋남) / 계열 불명
      E  추정·전망 표현
  · 스코프 오염 차단: 누적 판매량·컴백작 수치가 데뷔작에 귀속된 행은 거부

사용: python3 -m ingest.idol_layer
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path

RAW = Path("data/idol_raw/wave_a_rows.jsonl")
OUT = Path("data/idol_records")

MASK_PAT = re.compile(r"\*\*|하한값|끝 ?2ㅈ|마스킹")
CUM_PAT = re.compile(r"누적|연간 총|월간 판매|총 판매량\D*\d{6,}")
PRESS_ROUND = re.compile(r"\d+만\s*장|약 \d")


def norm_name(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", str(s))
    s = re.sub(r"\(.*?\)", "", s)
    return re.sub(r"[^0-9A-Za-z가-힣]", "", s).lower()


def grade(row: dict) -> tuple[str, str]:
    basis = str(row.get("chodong_basis") or "unknown").lower()
    note = str(row.get("chodong_note") or "") + str(row.get("notes") or "")
    quote = str(row.get("chodong_source_quote") or "")
    if MASK_PAT.search(note):
        return "C", "마스킹 하한값(끝자리 비공개)"
    if basis == "hanteo":
        exact = bool(re.search(r"\d{1,3}(,\d{3})+장|\d{4,}장", quote))
        return ("B", "한터 계열 정확 정수(언론 전재)") if exact else ("C", "한터 계열이나 정수 불명확")
    if basis == "namu":
        return "C", "위키 전사(한터 기준)"
    if basis == "circle":
        return "D", "써클 주간 — 달력주라 7일 초동 정의와 어긋남"
    if basis == "press":
        return ("C", "언론 반올림 표기") if PRESS_ROUND.search(quote) else ("C", "언론 인용")
    return "D", "계열 불명"


def suspicious(row: dict) -> str | None:
    blob = str(row.get("chodong_note") or "") + str(row.get("notes") or "")
    q = str(row.get("chodong_source_quote") or "")
    if CUM_PAT.search(q):
        return "인용문이 누적 판매량 계열"
    return None


def main() -> int:
    if not RAW.exists():
        print(f"입력 없음: {RAW}")
        return 1
    rows, bad = [], 0
    for line in RAW.read_text().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            bad += 1
    print(f"파싱: {len(rows)}행 (실패 {bad})")

    # 중복제거 — 그룹명+데뷔일, 라벨 있는 행 우선
    def rich(r):
        return (bool(r.get("chodong")) * 4 + bool(r.get("chodong_source_url")) * 2
                + bool(r.get("debut_date")) + bool(r.get("member_count")))
    rows.sort(key=rich, reverse=True)
    kept: list[dict] = []
    for r in rows:
        n, d = norm_name(r.get("group_name")), r.get("debut_date")
        dup = None
        for k in kept:
            if norm_name(k.get("group_name")) != n or not n:
                continue
            kd = k.get("debut_date")
            if d and kd:
                try:
                    if abs((date.fromisoformat(d) - date.fromisoformat(kd)).days) <= 14:
                        dup = k
                        break
                except ValueError:
                    pass
            else:
                dup = k
                break
        if dup:
            for f in ("chodong", "chodong_source_url", "member_count", "survival_show",
                      "mv_24h", "chart_peak", "agency"):
                if not dup.get(f) and r.get(f):
                    dup[f] = r[f]
        else:
            kept.append(r)
    print(f"중복제거: {len(rows)} → {len(kept)}")

    OUT.mkdir(parents=True, exist_ok=True)
    from collections import Counter
    gd, rejected, seq = Counter(), 0, 0
    for r in kept:
        if not r.get("group_name") or r.get("is_group") is False:
            continue
        seq += 1
        rid = f"IDOL-{(r.get('debut_date') or '0000')[:4]}-{seq:04d}"
        rec = dict(r)
        rec["record_id"] = rid
        rec["tier"] = "idol_debut"
        rec["ingested_from"] = "crawl wave-A (2026-07-27)"
        if r.get("chodong"):
            s = suspicious(r)
            if s:
                rec["chodong"] = None
                rec["label_reject"] = s
                rejected += 1
            else:
                g, why = grade(r)
                rec["label_trust"] = {"grade": g, "why": why, "basis": r.get("chodong_basis")}
                gd[g] += 1
        (OUT / f"{rid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    print(json.dumps({"편입": seq, "라벨 보유": sum(gd.values()), "신뢰등급": dict(gd),
                       "스코프 거부": rejected}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
