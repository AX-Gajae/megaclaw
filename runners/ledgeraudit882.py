# -*- coding: utf-8 -*-
# 노트 882 — 대사기 v1.2.1(사전등록 '882' · 티처 #47 (i)(iv) 소비 — 신규 기능 금지·정정만)
# v1.2(881) 대비: ① 기계-눈 불일치 수 필드(우연 대응+state 재분류 — 산문 유도 금지)
# ② RX_STATE 부류 일반화 — bare state 인용 포섭(실존 파일명 목록 스캔·특례 폐지) +
#   .jsonl/.npy 인용은 '검색 불능' 목록으로 값화(침묵 배제 금지 — 규약 54 자기 위반 봉합).
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("/Users/ax/world_model")

RX_OUT = re.compile(r"\bout(?:[0-9][A-Za-z0-9_\-]*|_[A-Za-z0-9_\-]+)(?:\.json)?")
RX_STATE = re.compile(r"data/state/[A-Za-z0-9_\-.]+\.[a-z]{2,5}")
STATE_NAMES = sorted(f.name for f in (ROOT / "data/state").iterdir()
                     if f.suffix in (".json", ".jsonl", ".npy"))  # bare 인용 포섭(부류 일반 — 특례 폐지)
RX_LIT = re.compile(r"(?<![\d.])((?:0\.\d{2,4})|(?:\d{1,2}\.\d{1,2})(?=\s*%(?!p)))")
AUDIT_NOTES = {878, 879, 880, 881, 882}
AUDIT_OUT = ("out878", "out879", "out880", "out881", "out882")

CATS = ("교차 인용", "문턱", "진짜 부재", "state 보존", "정당 대응", "우연 대응")
VERDICTS = {  # 눈 판정 — 1단계 사이드카(out882_sample.json) 실표본 16짝 전수 · 근거는 원문/산출물 검색
    "869|0.0069": {"부류": "교차 인용", "근거": "868 하한 이동값 — out833 실측 주장 아님(880 재검 승계)"},
    "869|0.0076": {"부류": "교차 인용", "근거": "rss 자 2×rss(SE) — 868 부속 정오"},
    "869|0.0125": {"부류": "교차 인용", "근거": "868 상한 이동값"},
    "869|0.018": {"부류": "교차 인용", "근거": "852 씨앗 SD"},
    "869|0.02": {"부류": "교차 인용", "근거": "±0.02 승계 금지 문면"},
    "871|0.0005": {"부류": "문턱", "근거": "릿지 재현 판정선 |ρ−0.3393| ≤0.0005"},
    "863|0.05": {"부류": "문턱", "근거": "p95 ≤0.05 판정선"},
    "864|1.6": {"부류": "state 보존", "근거": "game_recent_utc.json diff 요약 p95 0.015529… — 감사 우주 확장이 적중(#46 치명 봉합 실물)"},
    "864|0.34": {"부류": "정당 대응", "근거": "gate_rows 0.0034 실재"},
    "864|2.2": {"부류": "정당 대응", "근거": "gate_rows 0.022 실재"},
    "864|87.4": {"부류": "정당 대응", "근거": "day0b·repair 0.874 실재(전사층 — 주장층 철회는 866 교정 반영: 사유는 '독립 증거 5점 복권' 후 계수·상한 미확정)"},
    "867|17.0": {"부류": "정당 대응", "근거": "out866_census_erratum 에 17.0 실재(측정구간 일-입도 8.1~17.0% 서술의 출처)"},
    "867|8.1": {"부류": "정당 대응", "근거": "erratum 에 8.1 실재(실측 하한 1,033 ≈ 8.1%)"},
    "868|0.02": {"부류": "우연 대응", "근거": "노트의 ±0.02 문턱 ↔ 산출물 밴드 적중은 0.0125(이동 상한 — 다른 수) 뿐 — 2자리 리터럴 ±1ulp(±0.01) 밴드의 인공물 실증"},
    "868|0.10": {"부류": "정당 대응", "근거": "부트SD 0.0983/0.1033 의 반올림 인용('부트SD 0.10 대비') — 밴드의 설계 목적대로"},
    "876|0.75": {"부류": "정당 대응", "근거": "채택 설정 (0.75,10) — 0.75 정확 실재"},
}


def note_no(key, val):
    if isinstance(val, dict) and isinstance(val.get("노트"), int):
        return val["노트"]
    m = re.search(r"노트 (\d+)", key)
    return int(m.group(1)) if m else None


def resolve(tok):
    if tok.endswith(".json"):
        p = ROOT / "runners" / tok
        return [p.name] if p.exists() else []
    return [h.name for h in sorted((ROOT / "runners").glob(f"{tok}*.json"))]


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


def match_kind(lit_str, values):
    lit = float(lit_str)
    dec = len(lit_str.split(".")[1])
    ulp = 10 ** (-dec)
    kind = None
    for v in values:
        if abs(v - lit) <= ulp:
            return "raw"
        if abs(v * 100 - lit) <= ulp:
            kind = "pct"
    return kind


_vals_cache = {}


def file_values(path):
    key = str(path)
    if key not in _vals_cache:
        acc = []
        try:
            flatten_nums(json.loads(Path(path).read_text()), acc)
        except Exception:
            pass
        _vals_cache[key] = acc
    return _vals_cache[key]


def build_pairs(key, val, n):
    """한 대장 항목 → 짝 목록(픽스처 (e′)가 같은 경로를 지난다)."""
    body = key + json.dumps(val, ensure_ascii=False)
    arts = sorted({f for m in RX_OUT.finditer(body) for f in resolve(m.group(0))
                   if not f.startswith(AUDIT_OUT)})
    cited = {m.group(0) for m in RX_STATE.finditer(body)}
    cited |= {f"data/state/{nm}" for nm in STATE_NAMES if nm in body}   # bare 포섭
    states, unsearchable = [], []
    for s2 in sorted(cited):
        if not (ROOT / s2).exists():
            continue
        (states if s2.endswith(".json") else unsearchable).append(s2)
    if not arts:
        return []
    vals = []
    for a in arts:
        vals += file_values(ROOT / "runners" / a)
    out = []
    for lit in sorted(set(RX_LIT.findall(body))):
        kind = match_kind(lit, vals)
        state_hits = []
        if kind is None:                      # 감사 우주 확장 — '진짜 부재' 전 state 검색
            for s in states:
                if match_kind(lit, file_values(ROOT / s)):
                    state_hits.append(s)
        out.append({"노트": n, "키": key[:60], "리터럴": lit, "대응": kind,
                    "산출물": arts, "state 적중": state_hits,
                    "state 우주": states, "검색 불능(state)": unsearchable})
    return out


def main():
    ledger_bytes = (ROOT / "data/lab/denominator.json").read_bytes()
    ledger = json.loads(ledger_bytes)

    # ── 픽스처 ────────────────────────────────────────────────────
    fx = {}
    rc = file_values(ROOT / "runners/out877_recheck.json")
    la = file_values(ROOT / "runners/out878_ledgeraudit.json")
    fx["(f1a) 심은 참양성"] = match_kind("0.9999", rc) is None
    fx["(f1b) 참음성"] = match_kind("0.1518", rc) == "raw"
    fx["(f1c) 백분율"] = match_kind("94.1", la) == "pct"
    ipm = json.loads((ROOT / "runners/out877_ipmap.json").read_text())
    def sd_missing(rows):
        return sorted(r["행"] for r in rows
                      if "v2" in r["레인"] and not any("sd" in m for m in r["상대"]))
    def deep_has(obj, tok, dd=0):
        if dd > 2 or not isinstance(obj, (dict, list)):
            return False
        it = obj.values() if isinstance(obj, dict) else obj[:50]
        if isinstance(obj, dict) and any(tok in str(k) for k in obj):
            return True
        return any(deep_has(v, tok, dd + 1) for v in it)
    fx["(f1d) sd·HEAD 승계(깊이2)"] = (sd_missing(ipm["전행 표"]) == [16, 463, 591]
        and not deep_has(json.loads((ROOT / "runners/out877_recheck.json").read_text()), "HEAD"))
    synth_row = {"행": 99999, "레인": ["v2"], "상대": [{"wid": "WA-0", "sd": "2024-01-01"}]}
    fx["(f2) 음성 대조 합성(무검출)"] = 99999 not in sd_missing(ipm["전행 표"] + [synth_row])
    # (f3) state 재분류 실물 — 노트 864 실항목을 build_pairs 로
    f3 = False
    for k, v in ledger.items():
        if note_no(k, v) == 864 and "명단은 있으나" in k:
            ps = build_pairs(k, v, 864)
            tgt = [p for p in ps if p["리터럴"] == "1.6"]
            f3 = bool(tgt) and tgt[0]["대응"] is None and \
                any("game_recent_utc" in s for s in tgt[0]["state 적중"])
    fx["(f3) 864|1.6 state 재분류"] = f3
    # (f4) (e′) 합성 본문이 실제 파이프라인을 지난다
    lit876 = None
    for v in file_values(ROOT / "runners/out876_goldaudit.json"):
        s = f"{v:.3f}".rstrip("0")
        if re.fullmatch(r"0\.\d{2,3}", s) and 0 < v < 1:
            lit876 = s
            break
    synth_pairs = build_pairs(f"합성 시험(노트 866) {lit876} 가 out876_goldaudit 에", {}, 866)
    fx["(f4) (e′) 합성 파이프라인"] = any(
        p["리터럴"] == lit876 and p["대응"] and "out876_goldaudit.json" in p["산출물"]
        for p in synth_pairs)

    # ── 본 대조 ───────────────────────────────────────────────────
    pairs = []
    for k, v in ledger.items():
        n = note_no(k, v)
        if n is None or n < 863 or n in AUDIT_NOTES:
            continue
        pairs += build_pairs(k, v, n)
    miss = [p for p in pairs if p["대응"] is None and not p["state 적중"]]
    state_re = [p for p in pairs if p["대응"] is None and p["state 적중"]]
    raw_m = [p for p in pairs if p["대응"] == "raw"]
    pct_m = [p for p in pairs if p["대응"] == "pct"]

    # 표본: 층화 미대응(다중 5 + 단일 5) + pct 전부(≤5) + raw 5(2자리 리터럴 우선 — 충돌 위험 큰 쪽)
    by_note = {}
    for p in miss:
        by_note.setdefault(p["노트"], []).append(p)
    multi = [p for _n, ps in sorted(by_note.items(), key=lambda x: -len(x[1]))
             if len(ps) >= 2 for p in ps][:5]
    single = [ps[0] for _n, ps in sorted(by_note.items(), key=lambda x: -x[0])
              if len(ps) == 1][:5]
    raw_s = sorted(raw_m, key=lambda p: len(p["리터럴"]))[:5]
    sample = multi + single + pct_m[:5] + raw_s + state_re
    keyed = {f"{p['노트']}|{p['리터럴']}": p for p in sample}

    missing_v = [kk for kk in keyed if kk not in VERDICTS]
    if missing_v:
        side = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "성격": "1단계 표본 사이드카('w' — 성장물 아님·판정 전 표본의 기계적 보존)",
                "표본": [keyed[kk] for kk in sorted(keyed)]}
        json.dump(side, open(ROOT / "runners/out882_sample.json", "w"),
                  ensure_ascii=False, indent=1)
        print(json.dumps({"판정 필요": sorted(missing_v)}, ensure_ascii=False), flush=True)
        raise SystemExit("눈 판정 없인 저장 없음 — out882_sample.json 을 보고 VERDICTS 를 채워라")
    for kk, p in keyed.items():
        p["판정"] = VERDICTS[kk]
        assert VERDICTS[kk]["부류"] in CATS
    counts = {c: sum(1 for p in keyed.values() if p["판정"]["부류"] == c) for c in CATS}
    fx["(f5) 부류 계수 합 = 표본"] = sum(counts.values()) == len(keyed)
    fx["(g2) bare 포섭(870→kobis_axes)"] = any(
        p["노트"] == 870 and "data/state/kobis_axes.json" in p.get("state 우주", [])
        for p in pairs)
    fx["(g3) 검색 불능 값화(≥1)"] = any(p["검색 불능(state)"] for p in pairs)
    fx["(g4) 사이드카(out873_hook)"] = bool(resolve("out873_hook.json"))

    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "입력 지문": hashlib.sha256(ledger_bytes).hexdigest()[:12],
        "눈금": "v1.1 + 감사 우주 확장(미대응 → 인용 state 평탄화 검색) · 부류 집계 필드(산문 금지)",
        "픽스처": {**fx, "합격(5부류)": all(fx.values())},
        "모집단(863+·자기 배제)": {"짝": len(pairs), "미대응(state 후)": len(miss),
                             "state 재분류": len(state_re), "raw": len(raw_m), "pct": len(pct_m)},
        "부류 계수(집계 필드 — 산문 금지)": counts,
        "기계-눈 불일치 수(우연 대응+state 재분류)": counts["우연 대응"] + counts["state 보존"],
        "검색 불능(state) 목록": sorted({u for p2 in pairs for u in p2["검색 불능(state)"]}),
        "state 재분류 목록": state_re,
        "판정 표본": sorted(keyed.values(), key=lambda p: (p["노트"], p["리터럴"])),
    }
    with open(ROOT / "runners/out882_numaudit121.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    slim = dict(out)
    slim["판정 표본"] = [{kk: p[kk] for kk in ("노트", "리터럴", "대응", "state 적중")}
                     | {"부류": p["판정"]["부류"]} for p in out["판정 표본"]]
    slim.pop("state 재분류 목록")
    print(json.dumps(slim, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
