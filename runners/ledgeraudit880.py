# -*- coding: utf-8 -*-
# 노트 880 — 대사기 v1.1(사전등록 '880' · 티처 #45 ①~⑨ 소비)
# v1(879) 대비: 짝 단위 층화 표본(다중 5+단일 5+대응 의심 10) · 눈 판정 필드 의무(판정 없인
# 저장 없음) · ±1ulp 밴드 · %p 제외 · '.json' 없는 out 인용 포섭(접두 글롭) · 자기 배제
# (감사 가족 노트 878~880·out878*~out880*) · 추출 경로 픽스처 · 864 p95 재계산·박제 ·
# 논문 번호 중복 스캔. 적합 없음 · 동결물 불변.
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("/Users/ax/world_model")

RX_OUT = re.compile(r"\bout(?:[0-9][A-Za-z0-9_\-]*|_[A-Za-z0-9_\-]+)(?:\.json)?")
RX_LIT = re.compile(r"(?<![\d.])((?:0\.\d{2,4})|(?:\d{1,2}\.\d{1,2})(?=\s*%(?!p)))")
AUDIT_NOTES = {878, 879, 880}            # 자기 배제 — 감사는 자신을 감사하지 않는다
AUDIT_OUT = ("out878", "out879", "out880")

VERDICTS = {  # 눈 판정(사전등록 ⑤) — 1단계 실표본 11짝 전수·근거는 원문 검색(2단계 커밋에 로그)
    "869|0.0069": "소음(교차 인용) — 868 하한 이동값·유의 미달 서술: out833 실측 주장 아님",
    "869|0.0076": "소음(교차 인용) — rss 자 2×rss(SE): 868 부속 정오의 자",
    "869|0.0125": "소음(교차 인용) — 868 상한 이동값",
    "869|0.018": "소음(교차 인용) — 852 씨앗 SD(허용 오차 유도 근거)",
    "869|0.02": "소음(교차 인용) — ±0.02 무근거 승계 금지 문면의 문턱",
    "871|0.0005": "소음(문턱) — 릿지 재현 판정선 |ρ−0.3393| ≤0.0005",
    "864|1.6": "**진짜 부재·박제 대상** — '전행 228 재계산 p95 1.6%' 실측 주장의 집계값이 어느 out 에도 없음(행 원자료 rel_diff 는 game_recent_utc.json 에 실재) — 본 산출물 '864 p95 박제' 절이 새 보존처",
    "863|0.05": "소음(문턱) — p95 ≤0.05 판정선",
    "864|0.34": "정당 대응 — 중앙 0.34% = out864_gate_rows 의 0.0034 실재",
    "864|2.2": "정당 대응 — p95 2.2% = out864_gate_rows 의 0.022 실재",
    "864|87.4": "정당 대응(전사층) — 0.874 가 day0b·repair 에 실재. 주장층 주의: 87.4% 는 865 가 철회한 숫자(죽은 구간 착시) — 전사 정합과 주장 유효는 다른 층",
}


def note_no(key, val):
    if isinstance(val, dict) and isinstance(val.get("노트"), int):
        return val["노트"]
    m = re.search(r"노트 (\d+)", key)
    return int(m.group(1)) if m else None


def resolve(tok):
    """인용 토큰 → 실존 산출물 파일 목록(접두 글롭 — 'out878b' → out878b_*.json)."""
    if tok.endswith(".json"):
        p = ROOT / "runners" / tok
        return [p.name] if p.exists() else []
    hits = sorted((ROOT / "runners").glob(f"{tok}*.json"))
    return [h.name for h in hits]


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
    """'raw'|'pct'|None — ±1ulp 밴드(이중 반올림 부류 포섭)."""
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


def artifact_values(names, cache):
    acc = []
    for name in names:
        if name not in cache:
            vals = []
            try:
                flatten_nums(json.loads((ROOT / "runners" / name).read_text()), vals)
            except Exception:
                pass
            cache[name] = vals
        acc += cache[name]
    return acc


def main():
    ledger_bytes = (ROOT / "data/lab/denominator.json").read_bytes()
    ledger = json.loads(ledger_bytes)
    cache = {}

    # ── 픽스처 (a)~(e) — 사전등록 고정 ─────────────────────────────
    fx = {}
    rc = artifact_values(["out877_recheck.json"], cache)
    la = artifact_values(["out878_ledgeraudit.json"], cache)
    fx["(a1) 심은 참양성"] = match_kind("0.9999", rc) is None
    fx["(a2) 참음성"] = match_kind("0.1518", rc) == "raw"
    fx["(a3) 백분율"] = match_kind("94.1", la) == "pct"
    ipm = json.loads((ROOT / "runners/out877_ipmap.json").read_text())
    sdm = sorted(r["행"] for r in ipm["전행 표"]
                 if "v2" in r["레인"] and not any("sd" in m for m in r["상대"]))
    def deep_has(obj, tok, d=0):
        if d > 2 or not isinstance(obj, (dict, list)):
            return False
        it = obj.values() if isinstance(obj, dict) else obj[:50]
        if isinstance(obj, dict) and any(tok in str(k) for k in obj):
            return True
        return any(deep_has(v, tok, d + 1) for v in it)
    fx["(a4) 승계 sd·HEAD(깊이 2)"] = (sdm == [16, 463, 591]) and not deep_has(
        json.loads((ROOT / "runners/out877_recheck.json").read_text()), "HEAD")
    fx["(b) 이중 반올림 82.4↔0.8235"] = match_kind("82.4", [0.8235]) == "pct"
    body878 = ""
    for k, v in ledger.items():
        if note_no(k, v) == 878 and "판정" in k:
            body878 = k + json.dumps(v, ensure_ascii=False)
    fx["(c) 실추출 94.1"] = "94.1" in RX_LIT.findall(body878)
    fx["(d) 자기 배제"] = True   # 아래 모집단 구축 후 검증·갱신
    corr = ""
    for k, v in ledger.items():
        if "정정(티처 #44)" in k:
            corr = k + json.dumps(v, ensure_ascii=False)
    fx["(e) .json 없는 인용 포섭"] = any(
        resolve(m.group(0)) for m in RX_OUT.finditer(corr) if "878b" in m.group(0))

    # ── 본 대조(자기 배제 적용) ───────────────────────────────────
    pairs = []          # (노트, 키, 리터럴, kind, arts)
    for k, v in ledger.items():
        n = note_no(k, v)
        if n is None or n < 863 or n in AUDIT_NOTES:
            continue
        body = k + json.dumps(v, ensure_ascii=False)
        arts = sorted({f for m in RX_OUT.finditer(body) for f in resolve(m.group(0))
                       if not f.startswith(AUDIT_OUT)})
        if not arts:
            continue
        vals = artifact_values(arts, cache)
        for lit in sorted(set(RX_LIT.findall(body))):
            pairs.append({"노트": n, "키": k[:60], "리터럴": lit,
                          "대응": match_kind(lit, vals), "산출물": arts})
    fx["(d) 자기 배제"] = not any(p["노트"] in AUDIT_NOTES or
                              any(a.startswith(AUDIT_OUT) for a in p["산출물"]) for p in pairs)
    fixtures_ok = all(fx.values())

    miss = [p for p in pairs if p["대응"] is None]
    pct_only = [p for p in pairs if p["대응"] == "pct"]
    by_note = {}
    for p in miss:
        by_note.setdefault(p["노트"], []).append(p)
    multi = [p for n, ps in sorted(by_note.items(), key=lambda x: -len(x[1]))
             if len(ps) >= 2 for p in ps][:5]
    single = [ps[0] for n, ps in sorted(by_note.items(), key=lambda x: -x[0])
              if len(ps) == 1][:5]
    suspects = pct_only[:10]
    sample = multi + single + suspects

    # 눈 판정 의무 — 표본 전건에 VERDICTS 가 있어야 저장한다
    keyed = {f"{p['노트']}|{p['리터럴']}": p for p in sample}
    missing_verdicts = [kk for kk in keyed if kk not in VERDICTS]
    if missing_verdicts:
        print(json.dumps({"표본(판정 필요)": [
            {**keyed[kk], "키": keyed[kk]["키"][:50]} for kk in missing_verdicts]},
            ensure_ascii=False, indent=1), flush=True)
        raise SystemExit("눈 판정 없인 저장 없음 — VERDICTS 를 채우고 재실행(사전등록 ⑤)")
    for kk, p in keyed.items():
        p["판정"] = VERDICTS[kk]

    # ── 864 p95 재계산·박제 ───────────────────────────────────────
    u = json.loads((ROOT / "data/state/game_recent_utc.json").read_text())
    rel = sorted(v["rel_diff"] for v in u["행"].values() if v.get("rel_diff") is not None)
    # 🔴 wfail1 교훈(구현 의심 7차): 백분위수도 눈금이다 — 최근접 순위 p95=1.7%, 선형 보간
    # p95=1.55%→1.6%. 864 문면 1.6 은 선형 보간(np.percentile 기본) 정의였다. 두 정의 병기,
    # 박제 판정은 원 정의(선형) 기준. 집계 눈금(백분위 정의)도 규약 52 등록 대상 — 실물 2호.
    idx = max(0, min(len(rel) - 1, round(0.95 * (len(rel) - 1))))
    h = 0.95 * (len(rel) - 1)
    lo, hi = int(h), min(int(h) + 1, len(rel) - 1)
    p95_lin = rel[lo] + (h - lo) * (rel[hi] - rel[lo])
    restore = {"모집단": len(rel),
               "p95 선형보간(864 원 정의)": round(p95_lin, 6), "선형 %": round(p95_lin * 100, 1),
               "p95 최근접순위(wfail1 정의)": round(rel[idx], 6), "최근접 %": round(rel[idx] * 100, 1),
               "864 문면": 1.6, "박제(원 정의 반올림 일치)": round(p95_lin * 100, 1) == 1.6,
               "중앙": round(rel[len(rel) // 2], 6),
               "눈금 조항": "집계값 박제는 백분위수 정의까지 복원해야 한다(규약 52 실물 2호)",
               "출처": "data/state/game_recent_utc.json 행(228) — 집계값의 새 보존처는 본 산출물"}

    # ── 논문 번호 중복 스캔 ───────────────────────────────────────
    nums = {}
    for mj in sorted((ROOT / "paper/steps").glob("*/meta.json")):
        try:
            nums.setdefault(json.loads(mj.read_text()).get("n"), []).append(mj.parent.name)
        except Exception:
            pass
    dups = {str(n): ds for n, ds in nums.items() if len(ds) > 1}

    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "입력 지문": hashlib.sha256(ledger_bytes).hexdigest()[:12],
        "눈금": "짝 단위 · ±1ulp 밴드 · %p 제외 · '.json' 없는 인용 접두 글롭 · 자기 배제(878~880)",
        "픽스처": {**fx, "합격(5부류)": fixtures_ok},
        "모집단(863+·자기 배제)": {"짝": len(pairs), "미대응": len(miss), "pct 단독 대응": len(pct_only)},
        "층화 표본(판정 필드 포함)": {"다중-미스 5": multi, "단일-미스 5": single,
                              "대응 의심 10": suspects},
        "864 p95 박제": restore,
        "논문 번호 중복(유산 포함 — 문서)": dups,
        "문서 절": "v1/v1.1 은 전사층 전용 — 티처 #44 참양성 2건(figure 모순·시대 라벨)은 주장층이라 범위 밖(주장층 도구는 미건조)",
    }
    with open(ROOT / "runners/out880_numaudit11.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    slim = dict(out)
    slim["층화 표본(판정 필드 포함)"] = {g: [{kk: p[kk] for kk in ("노트", "리터럴", "대응", "판정")}
                                    for p in ps] for g, ps in out["층화 표본(판정 필드 포함)"].items()}
    print(json.dumps(slim, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
