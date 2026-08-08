# -*- coding: utf-8 -*-
# 노트 878 — 주장-산출물 대사기 v0(사전등록 '878' · 티처 #42 879 앞당김 · 티처 #43 제안 3)
# 적합 없음 — 대장(541+)의 경로 인용 실존(L1) · runners/out*.json 자기서술(L2) ·
# 받아들임 픽스처 3(규약 7: recheck HEAD 부재 · ipmap 참음성 · v2 레인 sd 누락 {16,463,591}).
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("/Users/ax/world_model")

PATH_PATTERNS = [
    r"runners/[A-Za-z0-9_.]+\.(?:py|json)",
    r"\bout\d{3}[A-Za-z0-9_]*\.json",
    r"lab/[A-Za-z0-9_]+\.py",
    r"ingest/[A-Za-z0-9_]+\.py",
    r"serve/[A-Za-z0-9_/.]*[A-Za-z0-9_]\.(?:py|html)",
    r"paper/steps/[0-9]+_[A-Za-z0-9_]+",
    r"data/(?:lab|state)/[A-Za-z0-9_./]+\.[a-z]{2,5}",
]
RX = re.compile("|".join(f"(?:{p})" for p in PATH_PATTERNS))
RX_NUM = re.compile(r"[ρΔ]|rho|0\.\d{3,4}")


def note_no(key, val):
    if isinstance(val, dict) and isinstance(val.get("노트"), int):
        return val["노트"]
    m = re.search(r"노트 (\d+)", key)
    return int(m.group(1)) if m else None


def resolve(p):
    """인용 문자열 → 저장소 경로(맨 out*.json 은 runners/ 에 산다)."""
    if p.startswith("out"):
        p = f"runners/{p}"
    return p


def main():
    ledger = json.load(open(ROOT / "data/lab/denominator.json"))

    # ── L1: 노트 541+ 의 경로 인용 실존 ────────────────────────────
    cited, missing, notes_with_path, notes_measured_no_path = {}, {}, 0, []
    n_pop = 0
    for k, v in ledger.items():
        n = note_no(k, v)
        if n is None or n < 541:
            continue
        n_pop += 1
        body = k + json.dumps(v, ensure_ascii=False)
        paths = sorted({resolve(m.group(0).rstrip(".")) for m in RX.finditer(body)})
        if paths:
            notes_with_path += 1
        elif RX_NUM.search(body):
            notes_measured_no_path.append({"노트": n, "키": k[:60]})
        for p in paths:
            cited.setdefault(p, []).append(n)
            if not (ROOT / p).exists():
                missing.setdefault(p, []).append(n)
    n_paths = len(cited)
    l1 = {"모집단(노트 항목 541+)": n_pop, "경로 인용 항목": notes_with_path,
          "고유 경로": n_paths, "누락 경로": len(missing),
          "경로 누락률": round(len(missing) / n_paths, 4) if n_paths else None,
          "누락 목록(노트 병기)": {p: sorted(set(ns))[:6] for p, ns in sorted(missing.items())},
          "눈 검증 표본(최대 10)": sorted(missing)[:10]}

    # ── L2: runners/out*.json 자기서술(시각·HEAD) ──────────────────
    outs = sorted((ROOT / "runners").glob("out*.json"))
    no_utc, no_head, bad_parse = [], [], []
    for f in outs:
        try:
            o = json.loads(f.read_text())
        except Exception as e:
            bad_parse.append({"파일": f.name, "오류": type(e).__name__})
            continue
        keys = list(o.keys()) if isinstance(o, dict) else []
        if not any("시각" in str(kk) for kk in keys):
            no_utc.append(f.name)
        if not any("HEAD" in str(kk) for kk in keys):
            no_head.append(f.name)
    n_ok = len(outs) - len(bad_parse)
    l2 = {"대상": len(outs), "파싱 실패(결손 아님·별도 칸)": bad_parse,
          "시각 결손": len(no_utc), "HEAD 결손": len(no_head),
          "HEAD 결손률": round(len(no_head) / n_ok, 4) if n_ok else None,
          "시각 결손률": round(len(no_utc) / n_ok, 4) if n_ok else None,
          "HEAD 결손 목록": no_head, "시각 결손 목록": no_utc}

    # ── L3: 받아들임 픽스처(규약 7 — 877 실물) ─────────────────────
    fx_a = "out877_recheck.json" in no_head
    fx_b = ("out877_ipmap.json" not in no_head) and ("out877_ipmap.json" not in no_utc)
    ipmap = json.load(open(ROOT / "runners/out877_ipmap.json"))
    v2_no_sd = sorted(r["행"] for r in ipmap["전행 표"]
                      if "v2" in r["레인"] and not any("sd" in m for m in r["상대"]))
    fx_c = v2_no_sd == [16, 463, 591]
    l3 = {"(a) recheck HEAD 부재 검출": fx_a, "(b) ipmap 참음성": fx_b,
          "(c) v2 레인 sd 누락 행": v2_no_sd, "(c) 판정({16,463,591} 일치)": fx_c,
          "합격(3/3)": fx_a and fx_b and fx_c}

    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "눈금": "누락의 단위는 경로(규약 52 — 노트 단위는 목록만)",
        "유령 처방(문서 절 — 측정 아님)": {
            "처방": "티처 #42·#43 — '878 = 785 서랍 ② 열 분해(만화 3열 중 어느 열이 냈나)'",
            "소진 실측": ["786 고르기 사전등록", "787 mg_nauthor +0.0272(뽑기 6 굳힘)",
                       "788 집 밖 KR +0.0248(0.0002 미달·서랍·규약 39)",
                       "793~796 CN 기준선 고고학(규약 44)", "799 게임·도서 1열(규약 45)"],
            "남은 재개 조건": "785 ①(KR 만화 행 ≥3,369 — T7 대기)뿐"},
        "L1 경로 대응": l1, "L2 자기서술": l2, "L3 픽스처": l3,
        "참고 통계(판정에 안 씀)": {"수치 무늬 있는데 경로 인용 0 인 항목": len(notes_measured_no_path),
                            "비율(대 모집단)": round(len(notes_measured_no_path) / n_pop, 4) if n_pop else None,
                            "목록(앞 15)": notes_measured_no_path[:15]},
    }
    with open(ROOT / "runners/out878_ledgeraudit.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    slim = {k: v for k, v in out.items() if k not in ("L1 경로 대응",)}
    slim["L1 요약"] = {k: v for k, v in l1.items() if "목록" not in k and "표본" not in k}
    slim["L1 눈 검증 표본"] = l1["눈 검증 표본(최대 10)"]
    print(json.dumps(slim, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
