# -*- coding: utf-8 -*-
# 노트 878 배선 수리판(티처 #44 중대 4·경미 1) — 사전등록 878 문면 그대로의 추출기.
# v0(ledgeraudit878.py)의 이탈 둘을 고친다: ① out\d{3} 이 out_* 날짜 이름을 못 봄 ·
#   data/(lab|state) 만 구현(문면은 data/*) · runners 하이픈 없음 ② L2 '최상위 키' 휴리스틱이
#   행-수준 시각(out864_gate_rows)을 결손으로 오검(위양성 1). 자는 사전등록 것 그대로 — 배선만 수리.
# v0 산출물(out878_ledgeraudit.json)은 동결 유지(wfail 아님 — 추출기 조건부 값으로 병기).
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("/Users/ax/world_model")

PATH_PATTERNS = [
    r"runners/[A-Za-z0-9_\-.]+\.(?:py|json)",
    r"\bout[0-9][A-Za-z0-9_\-]*\.json",
    r"\bout_[A-Za-z0-9_\-]+\.json",
    r"lab/[A-Za-z0-9_]+\.py",
    r"ingest/[A-Za-z0-9_]+\.py",
    r"serve/[A-Za-z0-9_/.]*[A-Za-z0-9_]\.(?:py|html)",
    r"paper/steps/[0-9]+_[A-Za-z0-9_]+",
    r"data/[A-Za-z0-9_\-./]+\.[a-z]{2,5}",
]
RX = re.compile("|".join(f"(?:{p})" for p in PATH_PATTERNS))

# 날짜 이름 산출물의 노트 배속(티처 #44 재계산 규칙 — 필자 노트 기준)
DATED_NOTE = {"out_erascan_2026-08-08.json": 873, "out_hooktest_2026-08-08.json": 873,
              "out_hooktest_2026-08-08_v873.json": 873, "out_snapcheck_2026-08-08.json": 875,
              "out_erafreeze_2026-08-08.json": 875}


def note_no(key, val):
    if isinstance(val, dict) and isinstance(val.get("노트"), int):
        return val["노트"]
    m = re.search(r"노트 (\d+)", key)
    return int(m.group(1)) if m else None


def resolve(p):
    if p.startswith("out"):
        p = f"runners/{p}"
    return p


def has_field(obj, token, depth=0):
    """최상위 + 2단 중첩까지 — 사전-속-목록-속-사전(out864_gate_rows 의 행)이 2단이다.
    1단 판(wfail1)이 그 행 시각을 못 봤다 — '구현 의심 먼저' 6차."""
    if depth > 2 or not isinstance(obj, (dict, list)):
        return False
    items = obj.values() if isinstance(obj, dict) else obj[:50]
    if isinstance(obj, dict) and any(token in str(k) for k in obj):
        return True
    return any(has_field(v, token, depth + 1) for v in items)


def main():
    ledger_bytes = (ROOT / "data/lab/denominator.json").read_bytes()
    ledger = json.loads(ledger_bytes)

    # ── L1(문면 정합 추출기) ──────────────────────────────────────
    cited, missing = {}, {}
    n_pop = notes_with_path = 0
    for k, v in ledger.items():
        n = note_no(k, v)
        if n is None or n < 541:
            continue
        n_pop += 1
        body = k + json.dumps(v, ensure_ascii=False)
        paths = sorted({resolve(m.group(0).rstrip(".")) for m in RX.finditer(body)})
        if paths:
            notes_with_path += 1
        for p in paths:
            cited.setdefault(p, []).append(n)
            if not (ROOT / p).exists():
                missing.setdefault(p, []).append(n)
    l1 = {"고유 경로": len(cited), "누락 경로": len(missing),
          "경로 누락률": round(len(missing) / len(cited), 4) if cited else None,
          "누락 목록(노트 병기)": {p: sorted(set(ns))[:6] for p, ns in sorted(missing.items())},
          "v0 병기": "1/145 = 0.69%(out878_ledgeraudit.json — 추출기 조건부 값)"}

    # ── L2(행-수준 보정 병기) ─────────────────────────────────────
    outs = sorted(f for f in (ROOT / "runners").glob("out*.json")
                  if not f.name.startswith("out878"))  # 자기(v0·b·wfail 사이드카) 제외 — 모집단은 878 이전 세계
    no_utc_top, no_utc_deep, no_head_deep, era_rows = [], [], [], []
    for f in outs:
        try:
            o = json.loads(f.read_text())
        except Exception:
            continue
        top_utc = isinstance(o, dict) and any("시각" in str(k) for k in o)
        deep_utc = has_field(o, "시각")
        deep_head = has_field(o, "HEAD")
        if not top_utc:
            no_utc_top.append(f.name)
        if not deep_utc:
            no_utc_deep.append(f.name)
        if not deep_head:
            no_head_deep.append(f.name)
        m = re.match(r"out(\d{3})", f.name)
        nt = int(m.group(1)) if m else DATED_NOTE.get(f.name)
        era_rows.append({"파일": f.name, "노트": nt, "utc": deep_utc, "head": deep_head})
    n = len(era_rows)
    l2 = {"대상": n, "HEAD 결손": len(no_head_deep), "HEAD 결손률": round(len(no_head_deep) / n, 4),
          "시각 결손(최상위 자·v0)": len(no_utc_top), "시각 결손(행-수준 보정)": len(no_utc_deep),
          "시각 결손률(보정)": round(len(no_utc_deep) / n, 4),
          "위양성 교정": [f for f in no_utc_top if f not in no_utc_deep]}

    # ── 시대 표(그림의 원자료 — 손 수치 금지) ─────────────────────
    def era_of(nt):
        return None if nt is None else ("<863" if nt < 863 else "863-875" if nt <= 875 else "876+")
    eras = {}
    for r in era_rows:
        e = era_of(r["노트"])
        if e is None:
            continue
        c = eras.setdefault(e, {"n": 0, "utc": 0, "head": 0})
        c["n"] += 1; c["utc"] += int(r["utc"]); c["head"] += int(r["head"])
    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "입력 지문": hashlib.sha256(ledger_bytes).hexdigest()[:12],
        "성격": "878 배선 수리판 — 자는 사전등록 그대로 · v0 병기 · 시대 표는 그림 원자료",
        "L1": l1, "L2": l2, "시대 표": eras, "배속 규칙": DATED_NOTE,
        "노트 배속 불능(시대 표 제외)": [r["파일"] for r in era_rows if r["노트"] is None],
    }
    with open(ROOT / "runners/out878b_ledgeraudit.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
