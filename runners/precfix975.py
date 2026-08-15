#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""975 --- 974 의 **정밀도 헤드라인·구간·복제**를 고쳐 다시 낸다 (티처 #113 1순위).

🔴 **새 라벨을 안 붙인다.** 974 의 같은 표본 696 행 · 같은 라벨을 쓴다. 바뀌는 것은 **추정량**이다.

- **ⓐ** 헤드라인을 **층가중**으로. `0.754310` 은 **「층 무시 값」**으로 강등한다.
  근거: 표본이 **등할당 층화**(층마다 100)인데 층 점유가 다르다 --- 다중·en 은 모집단
  **2.27%** 인데 표본 **14.80%** 다. 🔴 **974 자신의 유효 삼중쌍이 이미 층가중을 쓴다.**
- **ⓑ** **제목-군집 붓스트랩** --- 696 행이 제목 **164 개**에서 나온다. CP 는 독립 696 시행
  가정이라 폭이 좁다. **DEFF 를 같이 낸다.**
- **ⓒ** **개체 키 복제**를 접는다 --- 라벨 단위는 **(문서id, 제목) 짝**이다.

씀:
    python3 runners/precfix975.py --stage precfix --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for p in (str(ROOT), str(ROOT / "runners")):
    if p not in sys.path:
        sys.path.insert(0, p)

import runners.predict971 as P                    # noqa: E402
import precision974 as PR                         # noqa: E402

RAN = ("runners/precfix975.py", "runners/precision974.py", "runners/predict971.py")
OUT = ROOT / "runners"
SEED = 975
BOOT = 4000
GEN = "거짓·일반어(그 문서의 일반어 뜻)"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_stamp() -> dict:
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def stamp_block(ref, cs0, cs1, t0):
    ds = {"out974_sample.json": P._sha_file(str(OUT / "out974_sample.json")),
          "out974_labels.json": P._sha_file(str(OUT / "out974_labels.json")),
          "out974_precision.json": P._sha_file(str(OUT / "out974_precision.json")),
          "out974_wiring.json": P._sha_file(str(OUT / "out974_wiring.json"))}
    runner, ok = {}, 0
    for r in RAN:
        disk = P._sha_file(str(ROOT / r))
        try:
            cm = hashlib.sha256(subprocess.check_output(
                ["git", "show", "%s:%s" % (ref, r)], cwd=str(ROOT))).hexdigest()
        except Exception:                                          # noqa: BLE001
            cm = None
        runner[r] = {"디스크 sha256": disk, "커밋 blob sha256": cm, "일치": disk == cm}
        ok += 1 if disk == cm else 0
    return {
        "언제(시작)": t0, "언제(끝)": _now(),
        "시작 code_stamp 요약": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "끝 code_stamp 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
        "🔴 시작=끝": cs0 == cs1,
        "분모: 도장이 덮는 파일": len(cs1),
        "🔴 자료 지문": ds, "분모: 연 자료 파일": len(ds),
        "🔴 F1 기준 ref(준 대로)": ref,
        "🔴 40자 고정 sha 인가": bool(re.fullmatch(r"[0-9a-f]{40}", ref or "")),
        "🔴 기준 ref 가 0000…0000 인가": bool(re.fullmatch(r"0{40}", ref or "")),
        "러너별": runner, "🔴 분자/분모": "%d / %d" % (ok, len(RAN)),
        "🔴 F5 통과": ok == len(RAN) and bool(re.fullmatch(r"[0-9a-f]{40}", ref or ""))
        and not re.fullmatch(r"0{40}", ref or ""),
    }


def stage_precfix(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    smp = json.loads((OUT / "out974_sample.json").read_text(encoding="utf-8"))
    lab = json.loads((OUT / "out974_labels.json").read_text(encoding="utf-8"))
    old = json.loads((OUT / "out974_precision.json").read_text(encoding="utf-8"))
    w974 = json.loads((OUT / "out974_wiring.json").read_text(encoding="utf-8"))
    Lb = {x["쌍id"]: x["라벨"] for x in lab["라벨"]}
    rows = [r for r in smp["표본 행"] if r["쌍id"] in Lb]
    N = smp["🔴 분모: 973 이 낸 행 전량"]
    strat_all = smp["🔴 층별 전량"]
    strata = sorted(strat_all)
    Nh = {h: strat_all[h]["전량 행"] for h in strata}

    def hit(pid):
        return 1 if Lb.get(pid) == "참" else 0

    # ── ⓐ 층가중 대 층 무시 ─────────────────────────────────────────────
    by_h = collections.defaultdict(list)
    for r in rows:
        by_h[r["층"]].append(r["쌍id"])
    ph = {h: (sum(hit(i) for i in v) / float(len(v))) for h, v in by_h.items()}
    nh = {h: len(v) for h, v in by_h.items()}
    kh = {h: sum(hit(i) for i in v) for h, v in by_h.items()}
    p_strat = sum(Nh[h] * ph[h] for h in strata) / float(N)
    k_all = sum(hit(r["쌍id"]) for r in rows)
    p_naive = k_all / float(len(rows))
    occ = {h: {"모집단 비율": round(Nh[h] / float(N), 6),
               "표본 비율": round(nh[h] / float(len(rows)), 6),
               "🔴 표본/모집단 배": round((nh[h] / float(len(rows)))
                                    / (Nh[h] / float(N)), 4)}
           for h in strata}

    # ── ⓑ 제목-군집 붓스트랩 ─────────────────────────────────────────────
    cl = collections.defaultdict(list)
    for r in rows:
        cl[r["맞은 제목"]].append(r)
    titles = sorted(cl)
    rng = np.random.default_rng(SEED)

    def est(sample_rows):
        """(층 무시, 층가중) 두 추정량을 한 되뽑기에서 같이 낸다."""
        k = n = 0
        kk = collections.Counter()
        nn = collections.Counter()
        for r in sample_rows:
            h = r["층"]
            b = hit(r["쌍id"])
            k += b
            n += 1
            kk[h] += b
            nn[h] += 1
        naive = k / float(n) if n else float("nan")
        num = den = 0.0
        for h in strata:
            if nn[h]:
                num += Nh[h] * (kk[h] / float(nn[h]))
                den += Nh[h]
        strat = num / den if den else float("nan")
        return naive, strat, den == float(N)

    bc_naive, bc_strat, full = [], [], 0
    for _ in range(BOOT):
        pick = rng.integers(0, len(titles), len(titles))
        srows = [r for j in pick for r in cl[titles[j]]]
        a, b, f = est(srows)
        bc_naive.append(a)
        bc_strat.append(b)
        full += 1 if f else 0
    bs_naive, bs_strat = [], []
    for _ in range(BOOT):
        pick = rng.integers(0, len(rows), len(rows))
        srows = [rows[j] for j in pick]
        a, b, _f = est(srows)
        bs_naive.append(a)
        bs_strat.append(b)
    bc_naive = np.asarray(bc_naive, float)
    bc_strat = np.asarray(bc_strat, float)
    bs_naive = np.asarray(bs_naive, float)
    bs_strat = np.asarray(bs_strat, float)

    def q(a):
        return [round(float(np.percentile(a, 2.5)), 6),
                round(float(np.percentile(a, 97.5)), 6)]

    cp_naive = PR.cp_ci(k_all, len(rows))
    deff_naive = float(bc_naive.var(ddof=1) / bs_naive.var(ddof=1))
    deff_strat = float(bc_strat.var(ddof=1) / bs_strat.var(ddof=1))
    ci_c_naive, ci_c_strat = q(bc_naive), q(bc_strat)
    w_cp = cp_naive[1] - cp_naive[0]
    w_cl = ci_c_naive[1] - ci_c_naive[0]

    eff_point = p_strat * N
    eff_ci = [round(ci_c_strat[0] * N, 1), round(ci_c_strat[1] * N, 1)]

    # ── ⓒ 개체 키 복제 ──────────────────────────────────────────────────
    pair = collections.defaultdict(list)
    for r in rows:
        pair[(r["문서id"], r["맞은 제목"])].append(r)
    multi = {k2: v for k2, v in pair.items()
             if len({r["개체"] for r in v}) > 1}
    dup_rows = [r for v in multi.values() for r in v]
    dup_lab = collections.Counter(Lb[r["쌍id"]] for r in dup_rows)
    uniq = [v[0] for v in pair.values()]
    k_u = sum(hit(r["쌍id"]) for r in uniq)
    p_u = k_u / float(len(uniq))
    by_hu = collections.defaultdict(list)
    for r in uniq:
        by_hu[r["층"]].append(r["쌍id"])
    ph_u = {h: (sum(hit(i) for i in v) / float(len(v))) for h, v in by_hu.items()}
    p_strat_u = sum(Nh[h] * ph_u[h] for h in strata) / float(N)

    out = {
        "무엇": "975 --- 974 정밀도의 헤드라인·구간·복제를 고쳐 다시 낸다",
        "🔴 축": "C3 의 자를 고친다(축 전진은 C4 가 한다)",
        "사전등록": "docs/prereg_975_c4.md §5",
        "🔴 새 라벨 0": "974 의 같은 표본 696 행 · 같은 라벨. 바뀐 것은 추정량뿐이다.",
        "🔴 분모: 라벨한 행": len(rows),
        "🔴 분모: 973 이 낸 행 전량": N,
        "🔴🔴🔴 ⓐ 헤드라인 정정": {
            "🔴🔴 정본(층가중)": round(p_strat, 6),
            "🔴 강등(층 무시 · 974 헤드라인)": round(p_naive, 6),
            "차": round(p_strat - p_naive, 6),
            "🔴 974 가 이미 층가중을 쓴 자리":
                old["🔴🔴 ② 유효 삼중쌍"]["비율"],
            "🔴 그 값과 이번 층가중이 같은가":
                abs(old["🔴🔴 ② 유효 삼중쌍"]["비율"] - p_strat) < 1e-5,
            "층별 참/분모": {h: "%d / %d" % (kh[h], nh[h]) for h in strata},
            "층별 정밀도": {h: round(ph[h], 6) for h in strata},
            "층별 모집단 행": Nh,
            "🔴 층 점유(등할당이 만든 뒤틀림)": occ,
        },
        "🔴🔴🔴 ⓑ 제목-군집 붓스트랩": {
            "군집 = 맞은 제목": len(titles),
            "🔴 행/제목": round(len(rows) / float(len(titles)), 4),
            "뽑기": BOOT, "씨앗": SEED,
            "🔴🔴 층가중 정밀도 95% 군집 구간": ci_c_strat,
            "🔴🔴 층 무시 정밀도 95% 군집 구간": ci_c_naive,
            "🔴 974 가 쓴 CP 구간(독립 696 시행 가정)": list(cp_naive),
            "🔴🔴 폭 배(군집 / CP · 층 무시)": round(w_cl / w_cp, 4),
            "🔴🔴 폭 배(군집 / CP · 층가중)": round(
                (ci_c_strat[1] - ci_c_strat[0]) / w_cp, 4),
            "🔴🔴 DEFF(층 무시)": round(deff_naive, 4),
            "🔴🔴 DEFF(층가중)": round(deff_strat, 4),
            "🔴 네 층이 다 찬 뽑기": full, "분모: 뽑기": BOOT,
            "단순 되뽑기 구간(층 무시)": q(bs_naive),
            "단순 되뽑기 구간(층가중)": q(bs_strat),
        },
        "🔴🔴🔴 ⓑ′ 유효 삼중쌍 다시": {
            "🔴🔴 점추정(층가중 × 35,641)": round(eff_point, 1),
            "🔴🔴 95% 군집 구간": eff_ci,
            "🔴 974 가 신고한 구간(못 쓴다)":
                old["🔴🔴 ② 유효 삼중쌍"]["95% 붓스트랩 구간"],
            "🔴 974 점추정": old["🔴🔴 ② 유효 삼중쌍"]["점추정"],
            "🔴 점추정은 그대로인가":
                abs(round(eff_point, 1) - old["🔴🔴 ② 유효 삼중쌍"]["점추정"]) <= 0.2,
        },
        "🔴🔴🔴 ⓒ 개체 키 복제": {
            "🔴 (문서id, 제목) 짝": len(pair),
            "🔴 행": len(rows),
            "🔴 한 짝을 여러 개체가 나눠 쓴 짝": len(multi),
            "🔴 그 짝이 덮는 행": len(dup_rows),
            "🔴 표본에서의 비율": round(len(dup_rows) / float(len(rows)), 6),
            "🔴 그 행들의 라벨": dict(dup_lab),
            "🔴 그 행들의 정밀도": round(
                dup_lab.get("참", 0) / float(len(dup_rows)), 6) if dup_rows else None,
            "🔴🔴 복제를 접은 정밀도(층 무시)": round(p_u, 6),
            "🔴🔴 복제를 접은 정밀도(층가중)": round(p_strat_u, 6),
            "🔴 층 무시 값이 얼마나 내려가나": round(p_u - p_naive, 6),
            "🔴 층가중 값이 얼마나 내려가나": round(p_strat_u - p_strat, 6),
            "🔴 복제를 접은 유효 삼중쌍": round(p_strat_u * N, 1),
        },
        "🔴 ⓓ 카드 정정 --- 배선 W": {
            "🔴 974 카드가 적은 값": "8/8",
            "🔴 974 산출물이 적은 값": w974["🔴 W 분자/분모"],
            "🔴 False 인 칸": [k2 for k2, v2 in w974["W"].items() if v2 is not True],
            "🔴 카드가 틀렸나": w974["🔴 W 분자/분모"] != "8 / 8",
        },
        "🔴 ⓔ 라벨을 붙인 자 --- 정정": {
            "카드·판정문·논문이 적은 값": "한 사람",
            "🔴 산출물이 적은 값": lab["🔴 라벨을 붙인 자"],
        },
        "씨앗": SEED,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out975_precfix.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["precfix"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = {"precfix": stage_precfix}[a.stage](a.ref)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
