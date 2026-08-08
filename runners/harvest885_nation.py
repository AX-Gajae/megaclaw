# -*- coding: utf-8 -*-
"""노트 886 — **국적 팔(annex7) 수확 채점기**. 첫 봉인작 개봉(8/11) 전에 커밋한다.

왜 이 파일이 있나. 885 는 annex7 로 국적 팔을 얼렸지만 **그것을 읽는 코드가
없었다**(티처 #50 C2 · 내 검산: `grep -rn annex7 --include=*.py` → 자기 자신뿐).
harvest844 의 `arms` 와 사이드카 harvest844b 의 `ladder()` 는 둘 다 annex3/4/5 를
하드코딩한다. harvest844 는 동결물(수정 금지)이므로 새 파일이어야 한다.

    python3 runners/harvest885_nation.py --selftest   # 언제나 허용(라벨 무접촉)
    python3 runners/harvest885_nation.py --harvest    # 2026-09-28 이후에만

규율(844 지문 사슬):
  · 라벨 규칙은 harvest844 에서 **import** 한다 — 복사하지 않는다(복사는 표류의 씨앗).
  · 통계·밴드 정의는 이 파일이 유일한 정본이고 annex8 이 이 파일의 sha 를 박는다.
  · 이 파일은 라벨이 생기기 전에 커밋된다. 이후 수정은 지문 사슬 위반이다.
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")
import harvest844 as H844  # noqa: E402  (모듈은 __main__ 가드가 있어 import 안전)
from ingest.kobis import fetch_daily  # noqa: E402
# ↑ harvest844 는 `fetch_daily` 를 **함수 안에서** import 한다 — `H844.fetch_daily` 는
#   존재하지 않는다. 그대로 흉내 냈으면 9/28 에 AttributeError 로 죽었을 것이다
#   (886 받아들임 시험이 잡았다).

ROOT = Path("/Users/ax/world_model")
KD = ROOT / "cycle_log/forward/kobis"
A7 = KD / "annex7_2026-08-09.json"
SEAL = KD / "seal_2026-08-08.json"
HARVEST_NOT_BEFORE = dt.date(2026, 9, 28)
NPERM = 200_000
PERM_SEED = 886
MIN_EFF = 10          # annex7 문면: 유효 < 10 이면 보류
TAU_FRAC = 0.5        # '의미 있는 크기' = 완벽예측 천장의 절반 (886 에서 동결)


# ────────────────────────────────────────────────────────────────
# 통계 정의 — 이 세 함수가 정본이다(annex8 은 이 파일의 sha 를 박는다)
# ────────────────────────────────────────────────────────────────
def rerank(vals):
    """생존 집합 안에서 1..m 으로 다시 매긴다(작을수록 좋음)."""
    a = np.asarray(vals, float)
    return a.argsort().argsort() + 1


def stat_rho(rn, rc, y):
    """1차(annex7 문면) — Δρ = ρ(국적, y) − ρ(대조, y). 순위는 작을수록 좋으므로 -rank."""
    rho_n = float(spearmanr([-x for x in rn], y)[0])
    rho_c = float(spearmanr([-x for x in rc], y)[0])
    return rho_n - rho_c, rho_n, rho_c


def stat_err(rn, rc, y):
    """2차(886 사전등록) — Δ|err| = mean|r_대조 − r_라벨| − mean|r_국적 − r_라벨|.

    양수 = 국적 팔이 라벨에 더 가깝다. ρ 차와 달리 **천장이 두 팔의 상관에 눌리지
    않는다**(886 갑①: ρ 차는 완벽 예측에서도 1 − 0.899 = 0.101 이 상한이다).
    """
    ry = rerank([-v for v in y])            # 라벨 큰 쪽이 1위
    rn_, rc_ = rerank(rn), rerank(rc)
    en = np.abs(rn_ - ry)
    ec = np.abs(rc_ - ry)
    return float((ec - en).mean()), int((ec > en).sum()), int((ec < en).sum())


def perm_bands(rn, rc, n=NPERM, seed=PERM_SEED):
    """생존 집합 위에서 라벨을 순열해 두 통계의 귀무 밴드를 낸다(재량 0).

    H0: 라벨이 두 팔 모두와 무관. 라벨 주변분포는 순위 치환군.
    """
    m = len(rn)
    rn_, rc_ = rerank(rn), rerank(rc)
    a, b = -rn_.astype(float), -rc_.astype(float)
    az = (a - a.mean()) / a.std()
    bz = (b - b.mean()) / b.std()
    w = az - bz
    base = np.arange(1.0, m + 1)
    rs = np.random.default_rng(seed)
    d_rho = np.empty(n)
    d_err = np.empty(n)
    for i in range(n):
        y = rs.permutation(base)
        yz = (y - y.mean()) / y.std()
        d_rho[i] = (w @ yz) / m
        ry = rerank(-y)
        d_err[i] = (np.abs(rc_ - ry) - np.abs(rn_ - ry)).mean()
    # 완벽예측 천장(= 두 팔이 얼마나 다른가) 과 그 절반인 τ
    ceil_rho, _, _ = stat_rho(rn_, rc_, -rn_.astype(float))
    ceil_err, _, _ = stat_err(rn_, rc_, -rn_.astype(float))
    return {
        "m": m, "순열 표본": n, "씨앗": seed,
        "1차 Δρ": {"SD": round(float(d_rho.std(ddof=1)), 6),
                  "2σ 밴드": round(2 * float(d_rho.std(ddof=1)), 4),
                  "97.5분위": round(float(np.quantile(d_rho, 0.975)), 4),
                  "완벽예측 천장": round(ceil_rho, 4)},
        "2차 Δ|err|": {"SD": round(float(d_err.std(ddof=1)), 6),
                     "2σ 밴드": round(2 * float(d_err.std(ddof=1)), 4),
                     "97.5분위": round(float(np.quantile(d_err, 0.975)), 4),
                     "완벽예측 천장": round(ceil_err, 4),
                     "τ(의미 있는 크기 = 천장×0.5)": round(TAU_FRAC * ceil_err, 4)},
    }


def verdict(d_err, bands, m_eff):
    """규약 45 갈래 넷 — 서로 겹치지 않고 남김이 없다. 재량 0."""
    b = bands["2차 Δ|err|"]["2σ 밴드"]
    tau = bands["2차 Δ|err|"]["τ(의미 있는 크기 = 천장×0.5)"]
    if m_eff < MIN_EFF:
        return "모른다", f"유효 {m_eff} < {MIN_EFF} — annex7 동결 문면대로 보류"
    if b >= tau:
        return "모른다", (f"검열 후 밴드 {b} ≥ τ {tau} — 이 생존 집합은 의미 있는 크기조차 "
                       f"못 가른다(출력 부족)")
    if d_err > b:
        return "좋다", (f"Δ|err| {d_err} > 밴드 {b} — **영화 국적은 전향에서도 산다**. "
                     f"규약 12 의 '집 밖'을 전향 봉인으로 대체 채택할지는 별도 사전등록")
    if d_err < -b:
        return "해롭다", (f"Δ|err| {d_err} < −밴드 {b} — 885 의 집안 통과를 "
                       f"**판 안 과적합**으로 재분류한다")
    return "없다", (f"|Δ|err|| ≤ 밴드 {b} 이고 밴드 < τ {tau} — 의미 있는 크기였다면 "
                  f"발화했을 자인데 안 났다. **집안 전용**으로 확정하고 서빙에 안 올린다")


# ────────────────────────────────────────────────────────────────
def _load_arms():
    a7 = json.loads(A7.read_text())
    rows = a7["예측 팔(자루 평균 순위)"]
    nat = {r["code"]: r["국적 팔 순위"] for r in rows}
    ctl = {r["code"]: r["대조 순위"] for r in rows}
    return a7, rows, nat, ctl


def selftest():
    """받아들임 시험 — 라벨 무접촉. 배선·자·밴드가 살아 있나만 본다."""
    a7, rows, nat, ctl = _load_arms()
    seal = json.loads(SEAL.read_text())
    v1 = {w["code"]: w["예측 순위"] for w in seal["작품"]}
    codes = [r["code"] for r in rows]
    same = sum(1 for c in codes if v1[c] == ctl[c])

    # harvest844 와 같은 라벨 규칙을 쓰는가 — 판-내 아카이브로 재현(봉인 라벨 무접촉)
    B1 = json.load(open(ROOT / "data/ingest/kobis/backfill_2023-01-01_full.json"))
    B2 = json.load(open(ROOT / "data/ingest/kobis/backfill_2026-05-04_90d.json"))
    daily = {**B1, **B2}
    KA = json.load(open(ROOT / "data/state/kobis_axes.json"))
    n_tot = n_match = n_cens = 0
    for row in KA.values():
        y, last = H844.label_from_daily(daily, row["name"], row["release_date"])
        if y is None:
            continue
        n_tot += 1
        if last < H844.CENSOR_MIN:
            n_cens += 1
        if abs(y - row["y"]) < 1e-9:
            n_match += 1
    ref = H844.selftest()          # 동결 채점기와 **같은 수**가 나와야 한다

    bands = perm_bands([nat[c] for c in codes], [ctl[c] for c in codes], n=40_000)
    out = {
        "라벨 규칙 출처": f"harvest844.label_from_daily (import · K_WINDOW {H844.K_WINDOW} · "
                     f"CENSOR_MIN {H844.CENSOR_MIN})",
        "판-내 라벨 재현": {"행": n_tot, "일치": n_match, "검열 재계산": n_cens,
                     "동결 채점기(harvest844)": {"행": ref["행"], "일치": ref["라벨 일치"],
                                            "검열 재계산": ref["검열 재계산"]},
                     "🔴 동결 채점기와 같은가": (n_tot == ref["행"] and n_match == ref["라벨 일치"]
                                       and n_cens == ref["검열 재계산"])},
        "fetch_daily 배선": callable(fetch_daily),
        "봉인 편수": len(codes),
        "🔴 대조 팔 = seal v1": f"{same}/{len(codes)}",
        "대조 팔 배선 통과": same == len(codes),
        "밴드(40k 시험 순열)": bands,
        "갈래 시연": {
            "완벽예측이면": verdict(bands["2차 Δ|err|"]["완벽예측 천장"], bands, len(codes))[0],
            "0 이면": verdict(0.0, bands, len(codes))[0],
            "완벽 반대면": verdict(-bands["2차 Δ|err|"]["완벽예측 천장"], bands, len(codes))[0],
            "유효 9 면": verdict(99.0, bands, 9)[0],
        },
        "🔴 1차(Δρ)는 양성이 도달 가능한가": (bands["1차 Δρ"]["완벽예측 천장"]
                                  > bands["1차 Δρ"]["2σ 밴드"]),
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    assert same == len(codes), "대조 팔이 seal v1 과 다르다 — annex7 폐기 사유"
    assert out["판-내 라벨 재현"]["🔴 동결 채점기와 같은가"], "라벨 규칙이 harvest844 와 갈라졌다"
    assert callable(fetch_daily), "9/28 소급 fetch 경로가 죽어 있다"
    assert out["갈래 시연"] == {"완벽예측이면": "좋다", "0 이면": "없다",
                            "완벽 반대면": "해롭다", "유효 9 면": "모른다"}, "갈래가 안 붙는다"
    print("\n받아들임 시험 통과", flush=True)
    return out


def harvest(fetch=True):
    today = dt.date.today()
    if today < HARVEST_NOT_BEFORE:
        raise SystemExit(f"수확 금지 — {HARVEST_NOT_BEFORE} 이후에만(오늘 {today})")
    a7, rows, nat, ctl = _load_arms()
    seal = json.loads(SEAL.read_text())
    films = seal["작품"]

    days_needed = set()
    for m in films:
        od = dt.date.fromisoformat(m["개봉일"])
        for k in range(0, H844.K_WINDOW + 1):
            days_needed.add((od + dt.timedelta(days=k)).isoformat())
    daily, cache = {}, ROOT / "data/ingest/kobis"
    for day in sorted(days_needed):
        p = cache / f"{day}.json"
        if p.exists():
            daily[day] = json.loads(p.read_text())["rows"]
        elif fetch:
            daily[day] = fetch_daily(day)
            p.write_text(json.dumps({"date": day, "rows": daily[day]},
                                    ensure_ascii=False, indent=1))
            time.sleep(1.5)          # 공개 문 예절(829 KOBIS 선례 · harvest844 와 동일)

    labels, censored = {}, []
    for m in films:
        y, last = H844.label_from_daily(daily, m["제목"], m["개봉일"])
        if y is None or last < H844.CENSOR_MIN:
            censored.append(m["제목"])
        else:
            labels[m["code"]] = y

    codes = [c for c in labels if c in nat]
    m_eff = len(codes)
    res = {"유효": m_eff, "검열": censored,
           "생존 code": sorted(codes),
           "라벨 규칙 출처": "harvest844.label_from_daily(import)"}
    if m_eff >= 3:
        rn = [nat[c] for c in codes]
        rc = [ctl[c] for c in codes]
        y = [labels[c] for c in codes]
        d_rho, rho_n, rho_c = stat_rho(rn, rc, y)
        d_err, win, lose = stat_err(rn, rc, y)
        bands = perm_bands(rn, rc)          # 생존 집합에서 다시 계산 — 재량 0
        v, why = verdict(round(d_err, 4), bands, m_eff)
        res.update({
            "1차(annex7 문면 · 보고 의무)": {
                "ρ 국적 팔": round(rho_n, 4), "ρ 대조 팔": round(rho_c, 4),
                "Δρ": round(d_rho, 4), "밴드 2σ": bands["1차 Δρ"]["2σ 밴드"],
                "밴드 밖인가": abs(d_rho) > bands["1차 Δρ"]["2σ 밴드"],
                "🔴 이 통계의 한계": ("완벽 예측에서도 Δρ 상한이 "
                              f"{bands['1차 Δρ']['완벽예측 천장']} 라 밴드 "
                              f"{bands['1차 Δρ']['2σ 밴드']} 를 넘을 수 없다(886 갑① · annex8 정오 ㄱ). "
                              "이 줄은 **보고용**이고 판정은 2차가 한다.")},
            "2차(886 사전등록 · 판정 담당)": {
                "Δ|err|": round(d_err, 4), "국적 팔이 가까운 편수": win,
                "대조 팔이 가까운 편수": lose,
                "밴드 2σ": bands["2차 Δ|err|"]["2σ 밴드"],
                "τ": bands["2차 Δ|err|"]["τ(의미 있는 크기 = 천장×0.5)"]},
            "밴드(생존 집합 재계산)": bands,
            "갈래": v, "왜": why,
        })
    else:
        res["갈래"], res["왜"] = "모른다", f"유효 {m_eff} < 3 — 상관을 못 낸다"
    res["지문"] = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "annex7 sha": hashlib.sha256(A7.read_bytes()).hexdigest()[:12],
        "seal sha": hashlib.sha256(SEAL.read_bytes()).hexdigest()[:12],
        "채점기 sha": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    with open(KD / f"harvest_nation_{today.isoformat()}.json", "x") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--harvest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.harvest:
        harvest()
    else:
        print("사용: --selftest(언제나) 또는 --harvest(2026-09-28 이후)")
