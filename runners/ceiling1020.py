# -*- coding: utf-8 -*-
"""1020 — 예측 가능성 «천장» 실측: 같은 IP 반복 개최의 U(일평균 방문자) 흩어짐.

사전등록: docs/탐색/1020.md (커밋 ef736c266 — 실측 «전» 고정). 레인 [탐색·관찰] — 판 무접촉.
입력: wm_harvest/foundation/ledger_interventions/ledger.jsonl (1016 정본 · sha256 검증).
산출: wm_harvest/foundation/ceiling/{ceiling1020_result.json, pairs1020.json, run1020.out}
위생: 실명은 pairs1020.json 에만(결과 JSON 은 익명 그룹 id) · 네트워크 0 · CPU 전용 · py3.9.
"""
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time

LEDGER = "/Users/ax/wm_harvest/foundation/ledger_interventions/ledger.jsonl"
LEDGER_SHA_REG = "9a76948d3e619424ceadcfb0e2c0c06eceb80992dfd36784b9cd554ed998cffd"
OUTDIR = "/Users/ax/wm_harvest/foundation/ceiling"
B = 10000
SEED = 1020
QS = (0.05, 0.25, 0.50, 0.75, 0.95)
PIN_NORM_CONST = 0.248140  # mean_tau phi(Phi^-1(tau)) — §4 ⓐ
SE_MIN_PAIRS = 5           # §3 — n_쌍 < 5 층은 「표본 부족」 낙인

sys.path.insert(0, "/Users/ax/world_model")
from pretrain.mde_guard import mde_of, assert_mde, MdeUnderpowered  # noqa: E402


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


# ── §2 IP 정규화키 — derive_features._ipkey_mkt/_int 자구 이식 («같은 자») ──
def ipkey_mkt(ip_name, brand):
    k = (ip_name or brand or "").strip()
    return re.sub(r"\(.*?\)", "", k).split(" X ")[0].split("X")[0].strip()


def ipkey_int(ip_name, brand):
    k = (ip_name or brand or "")
    return k.replace("unresolved:", "").strip()


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return None
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def quantile(xs, q):
    """선형 보간(널리 쓰는 기본형) — 러너 세부(사전등록 산식의 구현 선택, 게재)."""
    s = sorted(xs)
    n = len(s)
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    return s[lo] + (pos - lo) * (s[hi] - s[lo])


def sd(xs):
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def stat_block(ds):
    """§3 게재 통계 — ds = 부호 있는 d 목록."""
    if not ds:
        return {"n_쌍": 0}
    ab = [abs(d) for d in ds]
    md = median(ab)
    out = {
        "n_쌍": len(ds),
        "mean_d(표류)": sum(ds) / len(ds),
        "SD_d": sd(ds),
        "median_abs_d": md,
        "MAD": median([abs(a - median(ds)) for a in ds]),
        "x배_눈금": math.exp(md),
        "sigma_med(정본)": md / (math.sqrt(2) * 0.674490),
        "sigma_SD(참고)": (sd(ds) / math.sqrt(2)) if sd(ds) is not None else None,
    }
    return out


def pinball_emp(eps_pool):
    """§4 ⓑ — 대칭화 ε̂ 풀의 경험 분위수에 대한 경험 핀볼 평균."""
    tot = 0.0
    for t in QS:
        qv = quantile(eps_pool, t)
        tot += sum(max(t * (x - qv), (t - 1) * (x - qv)) for x in eps_pool) / len(eps_pool)
    return tot / len(QS)


def conversions(ds):
    """§4 천장 환산 — ds 층의 d 목록."""
    ab = [abs(d) for d in ds]
    md = median(ab)
    m_eps = md / math.sqrt(2)
    sym = [s * d / math.sqrt(2) for d in ds for s in (1.0, -1.0)]
    mdape_emp = median([abs(1.0 - math.exp(-e)) for e in sym])
    sig_med = md / (math.sqrt(2) * 0.674490)
    sig_sd = (sd(ds) / math.sqrt(2)) if sd(ds) is not None else None
    return {
        "m_eps(=median|d|/√2)": m_eps,
        "MdAPE_하한(경험 대칭화·정본)": mdape_emp,
        "MdAPE_하한(폐형 e^m−1·참고)": math.exp(m_eps) - 1.0,
        "핀볼_하한ⓐ(0.248140×σ_med)": PIN_NORM_CONST * sig_med,
        "핀볼_하한ⓐ(0.248140×σ_SD·참고)": (PIN_NORM_CONST * sig_sd) if sig_sd is not None else None,
        "핀볼_하한ⓑ(경험)": pinball_emp(sym),
    }


def main():
    t0 = time.strftime("%Y-%m-%dT%H:%M:%S")
    log = []

    def say(*a):
        s = " ".join(str(x) for x in a)
        log.append(s)
        print(s)

    led_sha = sha256_file(LEDGER)
    if led_sha != LEDGER_SHA_REG:
        say("🔴 원장 sha 불일치 — 측정 없이 중단:", led_sha)
        return 2
    self_sha = sha256_file(os.path.abspath(__file__))
    say("입력 원장 sha256", led_sha)
    say("러너 sha256", self_sha)

    rows = []
    with open(LEDGER) as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    # ── 분모 사다리 ──
    u_rows = [r for r in rows if r["Y"].get("u_daily_visitors") is not None]
    ladder = {
        "원장": len(rows),
        "U_가능": {"합": len(u_rows),
                 "시장": sum(1 for r in u_rows if r["layer"] == "market"),
                 "내부": sum(1 for r in u_rows if r["layer"] == "internal")},
    }
    groups = {}
    n_key = 0
    for r in u_rows:
        w = r["A"]["what"]
        k = (ipkey_mkt(w.get("ip_name"), w.get("brand")) if r["layer"] == "market"
             else ipkey_int(w.get("ip_name"), w.get("brand")))
        if len(k) >= 2:
            n_key += 1
            groups.setdefault(k, []).append(r)
    multi = {k: sorted(v, key=lambda r: (r["A"]["when"]["opened_at"] or "", r["record_id"]))
             for k, v in groups.items() if len(v) >= 2}
    ladder["키2이상_재구성"] = n_key
    ladder["그룹"] = len(groups)
    ladder["반복_그룹"] = len(multi)
    ladder["반복_그룹_레코드"] = sum(len(v) for v in multi.values())

    # prior_count 교차 검산(§2 관찰): U-집합 안 선행 수 ≤ 원장 prior_count
    n_pc, n_ok = 0, 0
    for k, v in groups.items():
        opens = [r["A"]["when"]["opened_at"] for r in v]
        for r in v:
            ih = r["C"].get("ip_history") or {}
            pc = ih.get("prior_count")
            if pc is None:
                continue
            n_pc += 1
            ahead = sum(1 for o in opens if o and r["A"]["when"]["opened_at"] and o < r["A"]["when"]["opened_at"])
            if ahead <= pc:
                n_ok += 1
    ladder["prior_count_정합(선행수≤pc)"] = {"대상": n_pc, "만족": n_ok}

    # ── 쌍 구성 (§2) ──
    gkeys = sorted(multi.keys())
    gid = {k: "G%02d" % (i + 1) for i, k in enumerate(gkeys)}
    pairs, n_overlap = [], 0
    comp = {"mm": 0, "ii": 0, "mi": 0}
    for k in gkeys:
        v = multi[k]
        for a, b in itertools.combinations(v, 2):  # v 는 시간순 — a 가 전, b 가 후
            fa, ta = a["A"]["when"]["opened_at"], a["A"]["when"].get("closed_at") or a["A"]["when"]["opened_at"]
            fb, tb = b["A"]["when"]["opened_at"], b["A"]["when"].get("closed_at") or b["A"]["when"]["opened_at"]
            if not (ta < fb or tb < fa):
                n_overlap += 1
                continue
            d = math.log(b["Y"]["u_daily_visitors"]) - math.log(a["Y"]["u_daily_visitors"])
            vt_a, vt_b = a["A"]["where"].get("venue_type"), b["A"]["where"].get("venue_type")
            du_a, du_b = a["A"]["when"].get("duration_days"), b["A"]["when"].get("duration_days")
            fe_a, fe_b = a["A"]["what"].get("is_free_entry"), b["A"]["what"].get("is_free_entry")
            ratio = (max(du_a, du_b) / min(du_a, du_b)) if (du_a and du_b) else None
            def _cleanflag(r):
                sc = r["Y"].get("scope")
                return not (isinstance(sc, dict) and any(sc.get(x) is True for x in ("interim", "per_day", "forecast")))
            ih_b = b["C"].get("ip_history") or {}
            pairs.append({
                "g": gid[k], "key": k, "rid_a": a["record_id"], "rid_b": b["record_id"],
                "layer": ("mm" if a["layer"] == b["layer"] == "market" else
                          "ii" if a["layer"] == b["layer"] == "internal" else "mi"),
                "d": d, "lnUbar": 0.5 * (math.log(a["Y"]["u_daily_visitors"]) + math.log(b["Y"]["u_daily_visitors"])),
                "vt_same": (vt_a == vt_b) if (vt_a and vt_b) else None,
                "dur_ratio": ratio,
                "fe_same": (fe_a == fe_b) if (fe_a is not None and fe_b is not None) else None,
                "AB": (a["Y"].get("label_trust_grade") in ("A", "B") and b["Y"].get("label_trust_grade") in ("A", "B")),
                "clean": _cleanflag(a) and _cleanflag(b),
                "pc_later": ih_b.get("prior_count"),
            })
            comp[pairs[-1]["layer"]] += 1
    ladder["쌍_전체(겹침 포함)"] = len(pairs) + n_overlap
    ladder["기간_겹침_제외"] = n_overlap
    ladder["쌍(S0)"] = len(pairs)
    ladder["층_조합"] = comp

    # ── 층 배정 (§2 격자) ──
    def in_s1(p):
        return p["vt_same"] is True
    def in_s2(p):
        return in_s1(p) and p["dur_ratio"] is not None and p["dur_ratio"] <= 1.5
    def in_s3(p):
        return in_s2(p) and p["fe_same"] is True
    def in_d(p):
        return (p["vt_same"] is False) or (p["dur_ratio"] is not None and p["dur_ratio"] > 1.5)

    strata = {"S0": pairs,
              "S1": [p for p in pairs if in_s1(p)],
              "S2": [p for p in pairs if in_s2(p)],
              "S3": [p for p in pairs if in_s3(p)],
              "D": [p for p in pairs if in_d(p)]}
    undet = [p for p in pairs if not in_d(p) and not in_s2(p)]
    ladder["판정불가(유사도 못 가름)"] = len(undet)

    variants = {"전량": lambda p: True, "AB": lambda p: p["AB"]}
    tab = {}
    for sname, sp in strata.items():
        for vname, vf in variants.items():
            ds = [p["d"] for p in sp if vf(p)]
            blk = stat_block(ds)
            blk["n_그룹"] = len(set(p["g"] for p in sp if vf(p)))
            tab["%s_%s" % (sname, vname)] = blk
    tab["S0_clean"] = stat_block([p["d"] for p in pairs if p["clean"]])
    tab["S0_clean"]["n_그룹"] = len(set(p["g"] for p in pairs if p["clean"]))

    # ── 붓스트랩 (그룹 클러스터 · B=10,000 · seed=1020) ──
    rng = random.Random(SEED)
    by_g = {}
    for p in pairs:
        by_g.setdefault(p["g"], []).append(p)
    glist = sorted(by_g.keys())
    keys_boot = [("S0", "전량"), ("S0", "AB"), ("S1", "전량"), ("S2", "전량"), ("S3", "전량"), ("D", "전량")]
    acc = {k: {"med": [], "sd": []} for k in keys_boot}
    acc_diff, acc_tail = [], []
    skip = {k: 0 for k in keys_boot}
    skip_diff = skip_tail = 0
    for _ in range(B):
        samp = [by_g[glist[rng.randrange(len(glist))]] for _ in range(len(glist))]
        bp = [p for grp in samp for p in grp]
        for (sn, vn) in keys_boot:
            sel = [p["d"] for p in bp
                   if (sn == "S0" or (sn == "S1" and in_s1(p)) or (sn == "S2" and in_s2(p))
                       or (sn == "S3" and in_s3(p)) or (sn == "D" and in_d(p)))
                   and (vn == "전량" or p["AB"])]
            if len(sel) < 2:
                skip[(sn, vn)] += 1
                continue
            acc[(sn, vn)]["med"].append(median([abs(d) for d in sel]))
            acc[(sn, vn)]["sd"].append(sd(sel))
        s2 = [p["d"] for p in bp if in_s2(p)]
        dd = [p["d"] for p in bp if in_d(p)]
        if len(s2) >= 2 and len(dd) >= 2:
            acc_diff.append(median([abs(d) for d in s2]) - median([abs(d) for d in dd]))
        else:
            skip_diff += 1
        if len(bp) >= 4:
            cut = median([p["lnUbar"] for p in bp])
            lo = [abs(p["d"]) for p in bp if p["lnUbar"] <= cut]
            hi = [abs(p["d"]) for p in bp if p["lnUbar"] > cut]
            if lo and hi:
                acc_tail.append(median(lo) - median(hi))
            else:
                skip_tail += 1
        else:
            skip_tail += 1
    boot = {}
    for k in keys_boot:
        name = "%s_%s" % k
        n_real = tab[name]["n_쌍"]
        boot[name] = {
            "SE_median_abs_d": sd(acc[k]["med"]),
            "SE_SD_d": sd(acc[k]["sd"]),
            "결측_반복": skip[k],
            "낙인": ("표본 부족(n_쌍<%d)" % SE_MIN_PAIRS) if n_real < SE_MIN_PAIRS else None,
        }
    boot["S2−D_median_abs_d_차"] = {"차(실측)": (tab["S2_전량"]["median_abs_d"] - tab["D_전량"]["median_abs_d"])
                                   if tab["S2_전량"]["n_쌍"] and tab["D_전량"]["n_쌍"] else None,
                                   "SE": sd(acc_diff), "결측_반복": skip_diff}

    # ── §4 천장 환산 (S0 전량 정본 · AB·S2 병기) ──
    conv = {"S0_전량(정본)": conversions([p["d"] for p in pairs])}
    if tab["S0_AB"]["n_쌍"] >= 2:
        conv["S0_AB(병기)"] = conversions([p["d"] for p in pairs if p["AB"]])
    if tab["S2_전량"]["n_쌍"] >= 2:
        conv["S2_유사층(병기)"] = conversions([p["d"] for p in strata["S2"]])

    # ── §5 MDE 상한 표 + 자기 적용 ──
    c0 = conv["S0_전량(정본)"]
    mde_table = []
    for (자, 현, 눈금, 출처, ceiling) in [
        ("자 A 핀볼(위키 관심 log1p — 눈금 다름·관찰)", 0.07242, "log1p 관심", "9d424ee035e07154",
         c0["핀볼_하한ⓑ(경험)"]),
        ("MdAPE 집계(위키 관심 — 눈금 다름·관찰)", 0.057, "관심 MdAPE", "docs/탐색/1007.md:191",
         c0["MdAPE_하한(경험 대칭화·정본)"]),
        ("MdAPE 웹툰(위키 관심 — 눈금 다름·관찰)", 0.2345, "관심 MdAPE", "afd0346a490c8876",
         c0["MdAPE_하한(경험 대칭화·정본)"]),
    ]:
        mde_table.append({"자": 자, "현 성적": 현, "현 성적 출처": 출처,
                          "천장(U 눈금 환산)": ceiling,
                          "남은 방(=MDE 상한)": 현 - ceiling})
    se_med_s0 = boot["S0_전량"]["SE_median_abs_d"]
    aim = tab["S0_전량"]["median_abs_d"]
    try:
        stamp = assert_mde(mde_of(se=se_med_s0, jitter=0.0), aim, "9a76948d3e619424")
        낙인 = None
    except MdeUnderpowered as e:
        stamp = {"예외": str(e)}
        낙인 = "«미판정» — 실측 흩어짐 < 자기 MDE"
    mde_self = {"MDE(=2×SE_cl(median|d|,S0))": 2.0 * se_med_s0, "겨냥(=median|d| 실측)": aim,
                "스탬프": stamp, "낙인": 낙인}

    # ── §6 부수 관찰 ──
    cut = median([p["lnUbar"] for p in pairs])
    lo = [abs(p["d"]) for p in pairs if p["lnUbar"] <= cut]
    hi = [abs(p["d"]) for p in pairs if p["lnUbar"] > cut]

    def spearman(xs, ys):
        def rk(v):
            s = sorted(range(len(v)), key=lambda i: v[i])
            r = [0.0] * len(v)
            i = 0
            while i < len(s):
                j = i
                while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
                    j += 1
                for t in range(i, j + 1):
                    r[s[t]] = (i + j) / 2.0 + 1
                i = j + 1
            return r
        rx, ry = rk(xs), rk(ys)
        mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
        num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
        return num / den if den else None

    tails = {"분할점_lnUbar_중앙값": cut,
             "하위(실패쪽)": {"n": len(lo), "median_abs_d": median(lo)},
             "상위(성공쪽)": {"n": len(hi), "median_abs_d": median(hi)},
             "차(하위−상위)": median(lo) - median(hi),
             "차_SE(그룹 붓스트랩)": sd(acc_tail), "결측_반복": skip_tail,
             "Spearman(lnUbar,|d|)": spearman([p["lnUbar"] for p in pairs], [abs(p["d"]) for p in pairs])}

    pc_bins = {"1": [], "2-3": [], ">=4": [], "0(불일치 관찰)": [], "결측": []}
    for p in pairs:
        pc = p["pc_later"]
        b_ = ("결측" if pc is None else "0(불일치 관찰)" if pc == 0 else
              "1" if pc == 1 else "2-3" if pc <= 3 else ">=4")
        pc_bins[b_].append(abs(p["d"]))
    pc_tab = {k: {"n_쌍": len(v), "median_abs_d": median(v)} for k, v in pc_bins.items()}

    # ── 산출 ──
    os.makedirs(OUTDIR, exist_ok=True)
    t1 = time.strftime("%Y-%m-%dT%H:%M:%S")
    result = {"사전등록": "docs/탐색/1020.md (커밋 ef736c266)", "레인": "[탐색·관찰] — 판 무접촉",
              "잰 소스(조항 66)": {"러너 sha256": self_sha, "원장 sha256": led_sha,
                                "시작": t0, "끝": t1, "B": B, "seed": SEED,
                                "분위수 보간": "선형(위치 q(n−1))"},
              "분모_사다리": ladder, "층별_통계": tab, "붓스트랩": boot,
              "천장_환산": conv, "MDE_상한_표": mde_table, "MDE_자기_적용": mde_self,
              "꼬리_관찰": tails, "prior_count_추이": pc_tab}
    with open(os.path.join(OUTDIR, "ceiling1020_result.json"), "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUTDIR, "pairs1020.json"), "w") as f:
        json.dump({"주의": "실명 포함 — 이 파일 밖 인용 금지(위생)", "gid_key": {gid[k]: k for k in gkeys},
                   "pairs": pairs}, f, ensure_ascii=False, indent=1)
    say(json.dumps({k: v for k, v in result.items() if k not in ("층별_통계",)},
                   ensure_ascii=False)[:200])
    say("층별 요약:")
    for name in ("S0_전량", "S0_AB", "S0_clean", "S1_전량", "S2_전량", "S3_전량", "D_전량"):
        say(" ", name, json.dumps(tab[name], ensure_ascii=False))
    with open(os.path.join(OUTDIR, "run1020.out"), "w") as f:
        f.write("\n".join(log) + "\n")
    print("완료 — 결과:", os.path.join(OUTDIR, "ceiling1020_result.json"))
    return 0


if __name__ == "__main__":
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = "4"
    sys.exit(main())
