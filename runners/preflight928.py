# -*- coding: utf-8 -*-
"""노트 887 — **9/28 수확 프리플라이트**(티처 #51 F10·F12·F13).

동결물은 수정 금지라 `harvest885_nation.harvest()` 안에 sha 대조를 넣을 수 없다
(그 파일은 개봉 전에 얼었다). 그래서 **별도 파일**로 닫는다.

닫는 구멍 셋:
  F10  채점기가 annex7·seal·자기 sha 를 **기록만 하고 대조하지 않는다** ---
       9/28 까지 동결물이 표류하면 조용히 채점된다.
  F12  생존 라벨이 전부 같으면 `spearmanr → nan` 이고 `verdict` 가
       `nan > b` · `nan < -b` 둘 다 False 라 **조용히 '없다'** 를 낸다.
  F13  annex8 ㅁ 이 *"셋의 검열 집합은 같은 규칙"* 이라 적었는데 실제로는 **둘**이다
       (harvest844b 는 검열 집합을 안 만든다 · 진단 전용).

    python3 runners/preflight928.py        # 언제나 실행 가능(라벨 무접촉)

**이 파일은 판정하지 않는다.** 9/28 에 채점기를 돌리기 전에 켜는 경고등이다.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
KD = ROOT / "cycle_log/forward/kobis"

#: annex8 ㄷ 가 박은 기대 sha --- 여기 손으로 옮겨 적지 않는다. annex8 에서 **읽는다**.
A8 = KD / "annex8_2026-08-09.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]


def main():
    out, bad = {}, []
    a8 = json.loads(A8.read_text())
    wire = a8["ㄷ. 배선 증거(annex7 이 인라인으로 안 남긴 것 — 티처 #50 M5)"]
    exp = {**wire["생산자 sha256"], **wire["입력 sha256"]}
    now = {
        "annex7_885.py": sha(ROOT / "runners/annex7_885.py"),
        "harvest885_nation.py(채점기 정본)": sha(ROOT / "runners/harvest885_nation.py"),
        "band886.py": sha(ROOT / "runners/band886.py"),
        "annex7": sha(KD / "annex7_2026-08-09.json"),
        "seal": sha(KD / "seal_2026-08-08.json"),
    }
    drift = {k: {"동결 시점": exp[k], "지금": now[k]} for k in exp if exp.get(k) != now.get(k)}
    out["F10 — 동결물 sha 대조"] = {"기대(annex8 ㄷ)": exp, "지금": now,
                              "표류": drift or "없음", "통과": not drift}
    if drift:
        bad.append("F10 동결물이 표류했다")

    # F12 --- 라벨 퇴화 시 조용한 '없다' 를 막는다
    import harvest885_nation as HN
    import numpy as np
    rows = json.loads((KD / "annex7_2026-08-09.json").read_text())["예측 팔(자루 평균 순위)"]
    rn = [r["국적 팔 순위"] for r in rows]
    rc = [r["대조 순위"] for r in rows]
    y_flat = [1.0] * len(rn)                      # 전부 같은 라벨(퇴화)
    d_rho, _, _ = HN.stat_rho(rn, rc, y_flat)
    d_err, _, _ = HN.stat_err(rn, rc, y_flat)
    degenerate = not np.isfinite(d_rho)
    out["F12 — 라벨 퇴화 경보"] = {
        "전부 같은 라벨일 때 Δρ": (None if degenerate else round(d_rho, 4)),
        "그때 Δ|err|": round(d_err, 4),
        "🔴 위험": ("Δρ 가 nan 이면 `verdict` 가 nan>b·nan<−b 둘 다 False 라 **조용히 '없다'** 를 낸다"
                 if degenerate else "이번 입력에서는 퇴화 안 함"),
        "9/28 조치": "생존 라벨의 값 가짓수가 **1 이면 채점하지 말고 '모른다'로 적는다**(사람 판단 아님 — 규칙)",
        "통과": True}

    # F13 --- 검열 집합 회계 정정
    src = {}
    for f in ("harvest844.py", "harvest844b.py", "harvest885_nation.py"):
        s = (ROOT / "runners" / f).read_text()
        src[f] = {"CENSOR_MIN 규칙 사용": ("CENSOR_MIN" in s),
                  "label_from_daily 사용": ("label_from_daily" in s),
                  "검열 집합 생성": ("censored" in s)}
    n_cens = sum(1 for v in src.values() if v["검열 집합 생성"])
    out["F13 — 검열 집합은 셋이 아니라 둘"] = {
        "파일별": src, "검열 집합을 만드는 파일 수": n_cens,
        "annex8 ㅁ 문면": "'셋의 검열 집합은 같은 규칙에서 나온다'",
        "정정": ("**둘이다.** harvest844b 는 검열 집합을 만들지 않는다(진단 전용 · 날짜 범위도 다르다). "
               "844 ↔ 885_nation 두 개가 `label_from_daily` 를 공유해 구조적으로 동일하다."),
        "통과": n_cens == 2}
    if n_cens != 2:
        bad.append(f"검열 집합 생성 파일 {n_cens} ≠ 2")

    # 채점기 받아들임 시험
    try:
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            HN.selftest()
        out["채점기 --selftest"] = {"통과": True}
    except Exception as e:
        out["채점기 --selftest"] = {"통과": False, "오류": f"{type(e).__name__}: {e}"}
        bad.append("채점기 selftest 실패")

    out["9/28 실행 순서(annex8 ㅁ)"] = [
        "python3 runners/preflight928.py            # ← 먼저 켠다(887 신설)",
        "python3 runners/harvest844.py --harvest",
        "python3 runners/harvest844b.py",
        "python3 runners/harvest885_nation.py --harvest",
        "그리고 **annex9 ㄷ 판독 조항**을 함께 읽는다 — '없다'는 음성이 아니라 무정보다",
    ]
    out["지문"] = {"git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                            capture_output=True, text=True).stdout.strip()}
    out["🔴 종합"] = "이륙 가능" if not bad else f"보류 — {bad}"
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    main()
