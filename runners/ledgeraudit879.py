# -*- coding: utf-8 -*-
# 노트 879 — 대사기 v1: 수치 대조(사전등록 '879' · 티처 #42 원 제안 후반 · 티처 #44 픽스처)
# 눈금: (노트 수치 리터럴, 인용 산출물) 짝 — 노트 표기 자릿수 반올림 일치 ∨ 백분율(×100) 일치.
# 모집단 주 눈금 = 노트 863+ 중 실존 out*.json 인용 항목. 적합 없음 · 동결물 불변(합성은 메모리).
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("/Users/ax/world_model")

RX_OUT = re.compile(r"\bout[0-9_][A-Za-z0-9_\-]*\.json")
# 소수 리터럴: 0.xxx(x) 꼴 · xx.x(%) 꼴 — 연도/정수/노트번호는 안 잡는다
RX_LIT = re.compile(r"(?<![\d.])((?:0\.\d{2,4})|(?:\d{1,2}\.\d{1,2})(?=\s*%))")


def note_no(key, val):
    if isinstance(val, dict) and isinstance(val.get("노트"), int):
        return val["노트"]
    m = re.search(r"노트 (\d+)", key)
    return int(m.group(1)) if m else None


def flatten_nums(obj, acc):
    if isinstance(obj, dict):
        for v in obj.values():
            flatten_nums(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            flatten_nums(v, acc)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        acc.append(float(obj))
    elif isinstance(obj, str):
        for m in re.finditer(r"-?\d+\.\d+", obj):
            acc.append(float(m.group(0)))


def matches(lit_str, values):
    """노트 표기 자릿수 반올림 일치 ∨ 백분율 꼴 일치."""
    lit = float(lit_str)
    dec = len(lit_str.split(".")[1])
    for v in values:
        if abs(round(v, dec) - lit) < 10 ** (-dec) / 2:
            return True
        if abs(round(v * 100, dec) - lit) < 10 ** (-dec) / 2:
            return True
    return False


def artifact_values(name, cache):
    if name not in cache:
        p = ROOT / "runners" / name
        acc = []
        if p.exists():
            try:
                flatten_nums(json.loads(p.read_text()), acc)
            except Exception:
                pass
        cache[name] = acc
    return cache[name]


def main():
    ledger_bytes = (ROOT / "data/lab/denominator.json").read_bytes()
    ledger = json.loads(ledger_bytes)
    cache = {}

    # ── 픽스처(결과 집계 전 — 5/5 합격선) ─────────────────────────
    rc = artifact_values("out877_recheck.json", cache)
    la = artifact_values("out878_ledgeraudit.json", cache)
    fx1 = not matches("0.9999", rc)                      # 심은 참양성 → 미대응
    fx2 = matches("0.1518", rc)                          # 참음성 → 대응
    fx3 = matches("94.1", la)                            # 백분율 실물(0.9412)
    ipmap = json.loads((ROOT / "runners/out877_ipmap.json").read_text())
    rows = [r for r in ipmap["전행 표"]]
    synth = {"행": 99999, "레인": ["v2"], "상대": [{"AniList": "x", "wid": "WA-0", "sd": "2024-01-01"}],
             "IP 판정": "합성(메모리 — 동결물 불변)", "라프텔": "x"}
    def sd_missing(rws):
        return sorted(r["행"] for r in rws
                      if "v2" in r["레인"] and not any("sd" in m for m in r["상대"]))
    fx4 = 99999 not in sd_missing(rows + [synth])        # 음성 대조 합성 → 무검출
    fx5 = (sd_missing(rows) == [16, 463, 591]
           and not any("HEAD" in str(k) for k in json.loads(
               (ROOT / "runners/out877_recheck.json").read_text())))  # 승계
    fixtures = {"① 심은 참양성(0.9999 미대응)": fx1, "② 참음성(0.1518 대응)": fx2,
                "③ 백분율(94.1↔0.9412)": fx3, "④ 음성 대조 합성(무검출)": fx4,
                "⑤ 승계(sd {16,463,591}·recheck HEAD 부재)": fx5,
                "합격(5/5)": all([fx1, fx2, fx3, fx4, fx5])}

    # ── 본 측정: 노트 863+ 인용 항목의 수치 짝 대조 ────────────────
    pairs_total = pairs_unmatched = n_entries = 0
    unmatched = []
    ref_pairs = ref_unmatched = 0
    for k, v in ledger.items():
        n = note_no(k, v)
        if n is None or n < 541:
            continue
        body = k + json.dumps(v, ensure_ascii=False)
        arts = sorted({m.group(0) for m in RX_OUT.finditer(body)})
        arts = [a for a in arts if (ROOT / "runners" / a).exists()]
        if not arts:
            continue
        vals = []
        for a in arts:
            vals += artifact_values(a, cache)
        lits = sorted({m.group(1) for m in RX_LIT.finditer(body)})
        hit = [l for l in lits if matches(l, vals)]
        miss = [l for l in lits if l not in hit]
        ref_pairs += len(lits); ref_unmatched += len(miss)
        if n < 863:
            continue
        n_entries += 1
        pairs_total += len(lits); pairs_unmatched += len(miss)
        if miss:
            unmatched.append({"노트": n, "키": k[:70], "산출물": arts, "미대응": miss[:12]})
    unmatched.sort(key=lambda e: -len(e["미대응"]))

    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "입력 지문": hashlib.sha256(ledger_bytes).hexdigest()[:12],
        "눈금": "(노트 수치 리터럴, 인용 산출물) 짝 — 표기 자릿수 반올림 ∨ 백분율 일치(사전등록 879)",
        "픽스처": fixtures,
        "주 눈금(863+)": {"인용 항목": n_entries, "짝": pairs_total, "미대응": pairs_unmatched,
                      "미대응률(참고 — 판정에 안 씀)": round(pairs_unmatched / pairs_total, 4) if pairs_total else None},
        "참고(541+ 전체)": {"짝": ref_pairs, "미대응": ref_unmatched,
                        "미대응률": round(ref_unmatched / ref_pairs, 4) if ref_pairs else None},
        "눈 전수 표본(미대응 상위 ≤10)": unmatched[:10],
    }
    with open(ROOT / "runners/out879_numaudit.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    slim = dict(out)
    slim["눈 전수 표본(미대응 상위 ≤10)"] = [
        {kk: e[kk] for kk in ("노트", "키", "미대응")} for e in out["눈 전수 표본(미대응 상위 ≤10)"]]
    print(json.dumps(slim, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
