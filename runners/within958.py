# -*- coding: utf-8 -*-
"""노트 958 [판정] — 🔴 **모형을 고정하고 채점만 좁히는 within/between 분해.**

사전등록 `docs/prereg_958_within.md`(커밋 `8cf3c3a8b` · **측정 전** · 파일 하나).

**왜 다시 재나.** 957 의 헤드라인 「③ 이득의 **전부**가 도메인 사이」의 근거
`+0.001635` 를 만든 `layers957.py:666` 이 **도메인 부분집합에서 모형을 다시 적합한다**
(`one` → `rho_of` → `oof`). 그 수는 분해가 아니라 **표본 크기 실험**이다.
🔴 옳은 자는 **팔 전량에서 한 번만 적합하고 채점만 묶음 안으로 좁히는 것**이다(티처 #96 C1).

자 셋
  · **자 A(정본)** 고정 모형 · 묶음 안 채점 · 쌍 가중 → `Δρ_within`
  · **자 B(탐색 팔)** 켄달 일치쌍(C−D) **짝 단위** 분해 — 안/사이가 항등으로 더해진다
  · **곁들이** 묶음마다 재적합(= 957 의 수) — 🔴 **이름을 「표본 크기 실험」으로 바꿨다**

🔴 입력은 **`data/frozen/957_inputs/`** — 957 이 실제로 쓴 blob 을 얼린 것이다(V1 이 해시로 본다).
🔴 이 파일은 판 라벨을 한 비트도 안 연다(`assert_no_label_files`).

사용: python3 runners/within958.py
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
np.seterr(all="ignore")

import runners.layers957 as L                                   # noqa: E402
from lab.adopt import adopt                                     # noqa: E402

FROZEN = ROOT / "data/frozen/957_inputs"
OUT = ROOT / "runners/out958_within.json"

# 🔴 입력을 얼린 것으로 갈아 끼운다 — 데몬이 다시 써도 958 의 수는 안 움직인다.
L.WIKI = FROZEN / "wiki_daily"
L.ATT = FROZEN / "grid915_attach.json"
L.GEO = FROZEN / "geo919_coords.json"
# pairs 와 lifepop 은 머지 뒤 main 의 것과 **바이트가 같다**(명세가 해시로 박았다) — 그대로 쓴다.

BOOT_W = 2000
COLPERM = 200
N_MIN = 20                      # 자유파라미터 (사전등록 §4) — 1·10·20 을 전부 낸다
SHARE_T = 0.15                  # 자 B 안쪽 몫 문턱 (사전등록 §4)


# ── m1 처방 · 내용 해시 ─────────────────────────────────────────────────────
def content_sha(p: Path) -> str:
    """🔴 **압축을 푼 내용**의 sha256. 옛 `layers957.sha()` 는 gzip mtime 까지 해싱한다(m1)."""
    b = p.read_bytes()
    if p.suffix == ".gz":
        b = gzip.decompress(b)
    return hashlib.sha256(b).hexdigest()


# ── 자 A · 고정 모형 · 묶음 안 채점 ─────────────────────────────────────────
class FitCounter:
    """V2 — 묶음 루프가 모형을 다시 적합하는지 **센다**(산문이 아니라 계수기)."""

    def __init__(self):
        self.n = 0
        self._orig = None

    def __enter__(self):
        self._orig = L.ridge_fit
        outer = self

        def counted(*a, **k):
            outer.n += 1
            return outer._orig(*a, **k)
        L.ridge_fit = counted
        return self

    def __exit__(self, *a):
        L.ridge_fit = self._orig


def fixed_preds(rows: list[dict], base: list[str], plus: list[str]) -> dict:
    """🔴 팔 전량에서 **한 번만** 적합한다. 이 두 벡터는 그 뒤 다시 안 만든다."""
    y = np.asarray([r["y_들림"] for r in rows], dtype=float)
    g = np.asarray([r["개체"] for r in rows])
    r1, sd1, P1 = L.rho_of(L.mat(rows, *base), y, g)
    r2, sd2, P2 = L.rho_of(L.mat(rows, *(base + plus)), y, g)
    return {"y": y, "g": g, "P1": P1, "P2": P2,
            "ρ(기준) 합산": r1, "ρ(더한 것) 합산": r2, "🔴 합산 Δρ": r2 - r1,
            "씨앗 SD(기준)": sd1, "씨앗 SD(더한 것)": sd2}


def within_stat(y, P1, P2, grp, idx, n_min: int) -> dict:
    """묶음 안으로 **채점만** 좁힌다. 분자·분모를 한 줄에 하나씩 낸다."""
    per, num, den, skipped = {}, 0.0, 0, {}
    for gg in sorted(set(grp[idx])):
        sel = idx[grp[idx] == gg]
        n = len(sel)
        if n < n_min or len(set(y[sel])) < 3:
            skipped[str(gg)] = n
            continue
        a = float(spearmanr(P1[sel], y[sel]).statistic)
        b = float(spearmanr(P2[sel], y[sel]).statistic)
        if math.isnan(a) or math.isnan(b):
            skipped[str(gg)] = n
            continue
        per[str(gg)] = {"쌍": n, "ρ(기준)": a, "ρ(더한 것)": b, "Δρ": b - a}
        num += n * (b - a)
        den += n
    return {"분자: 쌍 가중 Δρ 합": num, "분모: 쓴 쌍": den,
            "🔴 Δρ_within (쌍 가중 안쪽 평균)": (num / den) if den else float("nan"),
            "묶음 단순평균 Δρ": (float(np.mean([v["Δρ"] for v in per.values()]))
                            if per else float("nan")),
            "묶음 수": len(per), "묶음별": per,
            f"안 쟀다(쌍 {n_min} 미만 또는 y 동점)": skipped}


def within_boot(y, P1, P2, grp, clus, n_min: int, reps=BOOT_W, seed=7) -> dict:
    """🔴 결론이 걸린 수의 SE — 군집 재표집. **모형은 안 다시 적합한다**(채점만)."""
    rng = np.random.RandomState(seed)
    cs = np.unique(clus)
    pos = {c: np.where(clus == c)[0] for c in cs}
    d, fail = [], 0
    for _ in range(reps):
        pick = rng.choice(len(cs), len(cs), replace=True)
        ii = np.concatenate([pos[cs[j]] for j in pick])
        w = within_stat(y, P1, P2, grp, ii, n_min)
        v = w["🔴 Δρ_within (쌍 가중 안쪽 평균)"]
        if math.isnan(v):
            fail += 1
            continue
        d.append(v)
    d = np.asarray(d)
    return {"재표집 성공": int(len(d)), "요청": reps, "실패": fail,
            "SE": float(d.std()), "평균": float(d.mean()),
            "2.5%": float(np.percentile(d, 2.5)), "97.5%": float(np.percentile(d, 97.5))}


# ── 자 B · 켄달 일치쌍 짝 단위 분해 ─────────────────────────────────────────
def kendall_split(y, P1, P2, grp) -> dict:
    """🔴 스피어만과 달리 **짝 단위로 더해진다** — 안 + 사이 = 전체가 항등이다."""
    n = len(y)
    iu, ju = np.triu_indices(n, 1)
    sy = np.sign(y[iu] - y[ju])
    tie = sy == 0
    c1 = np.sign(P1[iu] - P1[ju]) * sy
    c2 = np.sign(P2[iu] - P2[ju]) * sy
    gain = (c2 - c1)
    same = grp[iu] == grp[ju]
    ok = ~tie
    win = ok & same
    bet = ok & ~same

    def blk(m, name):
        cnt = int(m.sum())
        s = float(gain[m].sum())
        return {f"분자: {name} 차(C−D)": s, f"분모: {name} 짝": cnt,
                f"{name} 짝당": (s / cnt) if cnt else float("nan"),
                f"{name} C−D(기준)": float(c1[m].sum()), f"{name} C−D(더한 것)": float(c2[m].sum())}
    tot = float(gain[ok].sum())
    r = {**blk(win, "안"), **blk(bet, "사이"),
         "분자: 전체 차(C−D)": tot, "분모: 전체 짝(y 동점 뺀 것)": int(ok.sum()),
         "전체 짝당": tot / int(ok.sum()) if ok.sum() else float("nan"),
         "🔴 안쪽 몫 = 안쪽 차 ÷ 전체 차": (float(gain[win].sum()) / tot) if tot else float("nan"),
         "짝당 안쪽 ÷ 짝당 바깥쪽": ((float(gain[win].sum()) / max(int(win.sum()), 1)) /
                             (float(gain[bet].sum()) / max(int(bet.sum()), 1))
                             if bet.sum() and gain[bet].sum() else float("nan")),
         "y 동점으로 뺀 짝": int(tie.sum()),
         "V4 짝 회계 = C(n,2)": bool(int(win.sum()) + int(bet.sum()) + int(tie.sum())
                                  == n * (n - 1) // 2),
         }
    # 🔴 §4 — 동점을 안 빼고도 낸다
    win2, bet2 = same, ~same
    t2 = float(gain.sum())
    r["동점을 안 뺐을 때 안쪽 몫"] = (float(gain[win2].sum()) / t2) if t2 else float("nan")
    return r


# ── 본체 ───────────────────────────────────────────────────────────────────
def main() -> dict:
    t0 = dt.datetime.now(dt.timezone.utc)
    pairs = L.load_pairs()
    wd = L.load_wiki_daily()
    coords = L.load_coords()
    lp = L.load_lifepop()
    L.assert_no_label_files()

    built = L.build_arms(wd, coords, lp, pairs)
    A, B = built["A"], built["B"]

    R: dict = {
        "노트": 958, "레인": "판정",
        "사전등록": "docs/prereg_958_within.md (커밋 8cf3c3a8b · 측정 전 · 파일 하나)",
        "논문 스텝": 501,
        "시작(UTC)": t0.isoformat(),
        "🔴 무엇을 재나": "957 의 「③ 이득의 전부가 도메인 사이」를 정본 자로 다시 잰다 — "
                    "모형을 팔 전량에서 한 번만 적합하고 채점만 묶음 안으로 좁힌다",
        "🔴 자 정본": "자 A = 고정 모형 · 묶음 안 채점 · 쌍 가중 Δρ_within (사전등록 §2)",
        "🔴 판을 뗐다": "판 ρ 0.47034 · 유보 3,775 를 한 번도 안 건드린다 — 판 주장 0",
        "🔴 쓴 코드 sha256(앞16)": {p: L.sha(ROOT / p) for p in
                                ("runners/within958.py", "runners/layers957.py",
                                 "runners/out901h_link.py")},
    }

    # ── V1 입력 · 🔴 m1 처방 = **내용 해시** ────────────────────────────────
    man = json.loads((FROZEN / "manifest.json").read_text())
    v1, bad = {}, []
    for rel, e in man["항목"].items():
        p = (FROZEN / rel) if e["얼린 자리"] else (ROOT / e["원래 자리"])
        got = content_sha(p)
        okk = got == e["🔴 내용 sha256(압축을 푼 것 · 정본)"]
        v1[rel] = {"읽은 자리": str(p.relative_to(ROOT)), "내용 sha256(앞16)": got[:16], "일치": okk}
        if not okk:
            bad.append(rel)
    R["§5 V1 입력이 957 이 쓴 그것인가"] = {
        "🔴 자": "내용 sha256(압축을 푼 것) — 옛 sha() 는 gzip mtime 까지 해싱한다(m1)",
        "분자: 해시가 맞은 파일": len(v1) - len(bad), "분모: 명세의 파일": len(v1),
        "어긋난 것": bad, "파일별": v1, "통과": not bad}
    R["🔴 데몬을 재웠나(launchctl 에서 읽는다)"] = L.daemon_asleep()

    # ── 자 A ────────────────────────────────────────────────────────────────
    M: dict = {}
    for tag, rows, base, plus, gkey, ckey in (
            ("팔 B · ① → ①+③ (도메인)", B, ["x1"], ["x3"], "도메인", "개체"),
            ("팔 A · ① → ①+② (좌표원천)", A, ["x1"], ["x2"], "좌표원천", "격자"),
            ("팔 A · ① → ①+② (도메인)", A, ["x1"], ["x2"], "도메인", "격자")):
        F = fixed_preds(rows, base, plus)
        grp = np.asarray([str(r[gkey]) for r in rows])
        clus = np.asarray([str(r[ckey]) for r in rows])
        idx = np.arange(len(rows))
        with FitCounter() as fc:                      # V2 — 채점 루프는 적합을 안 부른다
            w = within_stat(F["y"], F["P1"], F["P2"], grp, idx, N_MIN)
            kd = kendall_split(F["y"], F["P1"], F["P2"], grp)
        bs = within_boot(F["y"], F["P1"], F["P2"], grp, clus, N_MIN)
        T = max(L.CARD_T, 2 * bs["SE"])
        dw = w["🔴 Δρ_within (쌍 가중 안쪽 평균)"]
        ent = {
            "무엇": tag, "묶음 열": gkey, "분모: 쌍 전량": len(rows),
            "군집 열(SE)": ckey, "군집 수": int(len(set(clus))),
            "ρ(기준) 합산": F["ρ(기준) 합산"], "ρ(더한 것) 합산": F["ρ(더한 것) 합산"],
            "🔴 합산 Δρ": F["🔴 합산 Δρ"],
            "씨앗 SD(기준)": F["씨앗 SD(기준)"], "씨앗 SD(더한 것)": F["씨앗 SD(더한 것)"],
            "🔴 자 A · 고정 모형 · 묶음 안": w,
            "🔴 SE_boot(Δρ_within)": bs["SE"], "부트 95% 구간": [bs["2.5%"], bs["97.5%"]],
            "재표집 성공/요청": [bs["재표집 성공"], bs["요청"]],
            "🔴 문턱 T = max(0.00353, 2·SE)": T,
            "🔴 카드 문턱 0.00353 이 이겼나": bool(L.CARD_T >= 2 * bs["SE"]),
            "🔴🔴 D3 판정(Δρ_within)": L.verdict(dw, T),
            "🔴 Δρ_within ÷ 합산 Δρ": (dw / F["🔴 합산 Δρ"]) if F["🔴 합산 Δρ"] else float("nan"),
            "🔴 D1-ㄱ 안쪽이 합산의 10% 이상인가": bool(
                dw > 0 and abs(dw) >= 0.10 * abs(F["🔴 합산 Δρ"])),
            "🔴 자 B · 켄달 짝 단위": kd,
            "🔴 D1-ㄴ 안쪽 몫 ≥ 15% 인가": bool(kd["🔴 안쪽 몫 = 안쪽 차 ÷ 전체 차"] >= SHARE_T),
            "V2 채점 루프의 ridge_fit 호출 수(0 이어야 한다)": fc.n,
            "V5 자 A 와 자 B 의 부호가 같은가": bool(
                np.sign(dw) == np.sign(kd["안 짝당"])),
        }
        ent["🔴🔴 D1 「전부 도메인 사이」를 철회하나"] = bool(
            ent["🔴 D1-ㄱ 안쪽이 합산의 10% 이상인가"] or ent["🔴 D1-ㄴ 안쪽 몫 ≥ 15% 인가"])
        # §4 — N_min 쓸기
        sw = {}
        for nm in (1, 10, 20):
            ww = within_stat(F["y"], F["P1"], F["P2"], grp, idx, nm)
            sw[f"N_min={nm}"] = {
                "Δρ_within": ww["🔴 Δρ_within (쌍 가중 안쪽 평균)"],
                "묶음 수": ww["묶음 수"], "분모: 쓴 쌍": ww["분모: 쓴 쌍"],
                "D1-ㄱ": bool(ww["🔴 Δρ_within (쌍 가중 안쪽 평균)"] > 0
                            and abs(ww["🔴 Δρ_within (쌍 가중 안쪽 평균)"])
                            >= 0.10 * abs(F["🔴 합산 Δρ"]))}
        ent["§4 N_min 쓸기"] = sw
        ent["§4 🔴 N_min 이 D1 판정을 바꾸나"] = bool(
            len({v["D1-ㄱ"] for v in sw.values()}) > 1)
        # §4 — 안쪽 몫 문턱 쓸기
        sh = kd["🔴 안쪽 몫 = 안쪽 차 ÷ 전체 차"]
        ent["§4 안쪽 몫 문턱 쓸기"] = {f"{t:.0%}": bool(sh >= t) for t in (0.05, 0.15, 0.25, 0.50)}
        ent["§4 🔴 몫 문턱이 D1 을 정하나"] = bool(
            len({bool(sh >= t) for t in (0.05, 0.15, 0.25, 0.50)}) > 1)
        # §4 — 군집 열을 바꾸면
        alt = "도메인" if ckey != "도메인" else "개체"
        bs2 = within_boot(F["y"], F["P1"], F["P2"], grp,
                          np.asarray([str(r[alt]) for r in rows]), N_MIN, reps=500, seed=17)
        T2 = max(L.CARD_T, 2 * bs2["SE"])
        ent["§4 군집 열을 바꾸면"] = {
            "바꾼 열": alt, "SE": bs2["SE"], "T": T2, "판정": L.verdict(dw, T2),
            "🔴 판정이 바뀌나": L.verdict(dw, T2) != L.verdict(dw, T)}
        ent["_F"] = F
        ent["_grp"] = grp
        M[tag] = ent
    R["§6 자 A · 고정 모형 within/between"] = {k: {kk: vv for kk, vv in v.items()
                                                if not kk.startswith("_")}
                                          for k, v in M.items()}

    # ── D2 · 도메인 지시자 (㉰ · 사전등록 §6) ────────────────────────────────
    def one_full(rows, base, plus, clus_key):
        """팔 **전량**에서 적합한다 — 부분집합 재적합이 아니다."""
        y = np.asarray([r["y_들림"] for r in rows], dtype=float)
        g = np.asarray([r["개체"] for r in rows])
        clus = np.asarray([str(r[clus_key]) for r in rows])
        ra, _, Pa = L.rho_of(L.mat(rows, *base), y, g)
        rb, _, Pb = L.rho_of(L.mat(rows, *(base + plus)), y, g)
        se = L.boot_se(Pa, Pb, y, clus)["SE"]
        T = max(L.CARD_T, 2 * se)
        return {"분모: 쌍": len(rows), "ρ(기준)": ra, "ρ(더한 것)": rb, "Δρ": rb - ra,
                "SE": se, "T": T, "판정": L.verdict(rb - ra, T)}

    doms = sorted({r["도메인"] for r in B})
    for r in B:
        r["xd"] = [1.0 if r["도메인"] == d else 0.0 for d in doms]
    d2a = one_full(B, ["x1"], ["xd"], "개체")
    d2b = one_full(B, ["x1", "xd"], ["x3"], "개체")
    R["§6 ㉰ 도메인 지시자 (사전등록 · 957 은 사후였다)"] = {
        "도메인 수(열)": len(doms), "① → +지시자": d2a, "①+지시자 → +③": d2b,
        "🔴🔴 D2 「③ 의 정보는 도메인 이름표로 대체 가능하다」를 싣나": bool(
            d2a["판정"].startswith("가") and not d2b["판정"].startswith("가")),
    }

    # ── ㉮ 열 순열 null (사전등록 §6) ────────────────────────────────────────
    def col_perm(rows, base, plus, reps=COLPERM, seed=13):
        y = np.asarray([r["y_들림"] for r in rows], dtype=float)
        g = np.asarray([r["개체"] for r in rows])
        Xb, Xp = L.mat(rows, *base), L.mat(rows, *plus)
        ra, _, _ = L.rho_of(Xb, y, g, seeds=[0])
        rng = np.random.RandomState(seed)
        d = []
        for _ in range(reps):
            Z = np.hstack([Xb, Xp[rng.permutation(len(rows))]])
            rb, _, _ = L.rho_of(Z, y, g, seeds=[0])
            d.append(rb - ra)
        d = np.asarray(d)
        rb0, _, _ = L.rho_of(np.hstack([Xb, Xp]), y, g, seeds=[0])
        return {"순열 수": reps, "평균": float(d.mean()), "SD": float(d.std()),
                "상위 5% 지점": float(np.percentile(d, 95)),
                "기준 ρ(씨앗 0)": ra, "관측 Δρ(씨앗 0 · 같은 자)": rb0 - ra,
                "🔴 관측이 상위 5% 밖인가": bool((rb0 - ra) > float(np.percentile(d, 95)))}

    cp = col_perm(B, ["x1"], ["x3"])
    b3 = M["팔 B · ① → ①+③ (도메인)"]
    R["§6 ㉮ 열 순열 null (사전등록 · 957 은 사후였다)"] = {
        "왜": "라벨 순열은 y 를 섞어 ①의 진짜 신호까지 없앤다 — 「③ 이 ① 위에 더하는가」의 null 이 아니다",
        "팔": "B", **cp,
        "🔴🔴 D5 ㉢(열 순열 상위 5% 밖)": cp["🔴 관측이 상위 5% 밖인가"],
        "㉠ 합산 Δρ > T_합산": None}

    # D5 — 합산 자리의 ㉠·㉡ 은 957 산출물의 값을 그대로 쓴다(재현 확인만)
    o957 = json.loads((ROOT / "runners/out957_layers.json").read_text())
    b957 = o957["§6 측정 · 주 표적 y_들림"]["B-③ 무관 배경"]
    R["§6 ㉮ 열 순열 null (사전등록 · 957 은 사후였다)"]["㉠ 합산 Δρ > T_합산"] = b957["㉠ Δρ > T"]
    R["§6 D5 층 ③ 을 s 에 넣나"] = {
        "㉠ 합산 Δρ > T": b957["㉠ Δρ > T"],
        "㉡ 부 표적 부호 유지": b957["㉡ 부 표적에서 부호가 안 뒤집힌다"],
        "㉢ 열 순열 상위 5% 밖(958 이 사전등록한 자)": cp["🔴 관측이 상위 5% 밖인가"],
        "㉢ 라벨 순열 밖(957 의 자)": b957["㉢ 순열 상위 5% 밖"],
        "🔴🔴 채택(㉠㉡㉢)": bool(b957["㉠ Δρ > T"] and b957["㉡ 부 표적에서 부호가 안 뒤집힌다"]
                          and cp["🔴 관측이 상위 5% 밖인가"]),
        "🔴 자를 바꿔 초록이 됐나": bool(cp["🔴 관측이 상위 5% 밖인가"]
                              and not b957["㉢ 순열 상위 5% 밖"]),
        # ── 🔴🔴 961 R3 — `lab.adopt.adopt` 배선 ───────────────────────────
        # 959 가 경고했다: *「`within958.py` 를 `lab.adopt.adopt` 에 배선하라 —
        # 안 하면 `채택=true` 가 머지로 되살아난다」*. 🔴 **그 경고대로 됐다**:
        # #216 이 머지되며 위의 `채택(㉠㉡㉢) = true` 가 main 에 올라왔다.
        # 이 파일은 **㉰ 도메인 지시자를 이미 재 놓고도**(위 §6 ㉰) 그 값을
        # 채택 판정에 안 먹였다 — ㉣(더 싼 대체물)이 원리상 안 걸렸다.
        # 🔴 961 의 `adopt()` 는 3값이라 「못 가른다」가 「통과」로 안 샌다(조항 59).
        "🔴🔴 채택(㉠㉡㉢㉣) — lab.adopt.adopt": adopt(
            sum_pass=bool(b957["㉠ Δρ > T"]),
            sub_sign_pass=bool(b957["㉡ 부 표적에서 부호가 안 뒤집힌다"]),
            perm_pass=bool(cp["🔴 관측이 상위 5% 밖인가"]),
            alt_delta=d2a["Δρ"], alt_T=d2a["T"],
            layer_on_alt_delta=d2b["Δρ"], layer_on_alt_T=d2b["T"]),
        "🔴 위 「채택(㉠㉡㉢)」은 ㉣ 을 안 본 옛 값이다": (
            "인용하지 마라 — 정본은 바로 위 `채택(㉠㉡㉢㉣)` 이다(조항 62: 부르는 쪽이 답을 키로 낸다)"),
    }

    # ── §7 곁들이 · 표본 크기 실험 (= 957 의 수) ────────────────────────────
    def refit_group(rows, base, plus, gkey, n_min=N_MIN):
        per, num, den = {}, 0.0, 0
        for gg in sorted({str(r[gkey]) for r in rows}):
            sub = [r for r in rows if str(r[gkey]) == gg]
            if len(sub) < n_min:
                per[gg] = {"쌍": len(sub), "🔴 안 쟀다": f"쌍 {n_min} 미만"}
                continue
            y = np.asarray([r["y_들림"] for r in sub], dtype=float)
            g = np.asarray([r["개체"] for r in sub])
            ra, _, _ = L.rho_of(L.mat(sub, *base), y, g)
            rb, _, _ = L.rho_of(L.mat(sub, *(base + plus)), y, g)
            ntr = len(sub) - int(math.ceil(len(sub) / L.KFOLD))
            per[gg] = {"쌍": len(sub), "Δρ": rb - ra,
                       "🔴 한 겹의 훈련 행 수(대략)": ntr,
                       "열 수": int(L.mat(sub, *(base + plus)).shape[1])}
            num += len(sub) * (rb - ra)
            den += len(sub)
        return {"🔴 이것은 분해가 아니다": "묶음 부분집합에서 모형을 **다시 적합**한다 — "
                                 "「작은 표본으로도 그 층을 배울 수 있는가」를 잰다",
                "분자: 쌍 가중 Δρ 합": num, "분모: 쓴 쌍": den,
                "묶음 안 평균 Δρ(= 957 의 헤드라인 수)": (num / den) if den else float("nan"),
                "묶음별": per}

    R["§7 곁들이 · 표본 크기 실험 (판정 아님 · 957 의 수)"] = {
        "팔 B · 도메인": refit_group(B, ["x1"], ["x3"], "도메인"),
        "팔 A · 좌표원천": refit_group(A, ["x1"], ["x2"], "좌표원천", n_min=10),
    }

    # ── §5 나머지 배선 검사 ────────────────────────────────────────────────
    W: dict = {}
    W["V1 입력 해시"] = {"통과": R["§5 V1 입력이 957 이 쓴 그것인가"]["통과"]}
    W["V2 채점 루프가 모형을 다시 적합하지 않는다"] = {
        "분자: ridge_fit 호출 수": sum(M[k]["V2 채점 루프의 ridge_fit 호출 수(0 이어야 한다)"]
                                for k in M),
        "분모: 채점한 팔": len(M), "통과": all(
            M[k]["V2 채점 루프의 ridge_fit 호출 수(0 이어야 한다)"] == 0 for k in M)}
    wb = M["팔 B · ① → ①+③ (도메인)"]["🔴 자 A · 고정 모형 · 묶음 안"]
    W["V3 분모 합"] = {
        "분자: 묶음에 쓴 쌍": wb["분모: 쓴 쌍"],
        "분모: 팔 B 쌍 전량": len(B),
        "N_min 미달로 뺀 쌍": sum(wb[f"안 쟀다(쌍 {N_MIN} 미만 또는 y 동점)"].values()),
        "통과": wb["분모: 쓴 쌍"] + sum(
            wb[f"안 쟀다(쌍 {N_MIN} 미만 또는 y 동점)"].values()) == len(B)}
    kb = M["팔 B · ① → ①+③ (도메인)"]["🔴 자 B · 켄달 짝 단위"]
    W["V4 켄달 짝 회계"] = {"안": kb["분모: 안 짝"], "사이": kb["분모: 사이 짝"],
                      "y 동점": kb["y 동점으로 뺀 짝"],
                      "C(n,2)": len(B) * (len(B) - 1) // 2,
                      "통과": kb["V4 짝 회계 = C(n,2)"]}
    W["V5 자 A 와 자 B 의 방향"] = {
        "팔별": {k: M[k]["V5 자 A 와 자 B 의 부호가 같은가"] for k in M},
        "통과": all(M[k]["V5 자 A 와 자 B 의 부호가 같은가"] for k in M)}

    # V6 심은 열 — y 에서 만든 열을 ③ 자리에 넣는다
    rng = np.random.RandomState(3)
    yB = np.asarray([r["y_들림"] for r in B], dtype=float)
    for i, r in enumerate(B):
        r["xseed"] = [float(yB[i]) + 0.05 * rng.randn()] * 1
    Fs = fixed_preds(B, ["x1"], ["xseed"])
    grpB = np.asarray([str(r["도메인"]) for r in B])
    ws = within_stat(Fs["y"], Fs["P1"], Fs["P2"], grpB, np.arange(len(B)), N_MIN)
    W["V6 심은 열"] = {"Δρ_within(심은 열)": ws["🔴 Δρ_within (쌍 가중 안쪽 평균)"],
                   "합산 Δρ(심은 열)": Fs["🔴 합산 Δρ"],
                   "통과": bool(ws["🔴 Δρ_within (쌍 가중 안쪽 평균)"] > 0.10)}

    # V7 🔴 m5 — 사실상 전부 가려진 격자 (마스킹 `*` 는 0 으로 접혔다)
    gz = {}
    for gid, tab in lp.items():
        cells = 0
        zeros = 0
        for _, row in tab.items():
            cells += len(row)
            zeros += sum(1 for v in row if float(v) == 0.0)
        gz[gid] = {"칸": cells, "0 인 칸": zeros, "0 비율": zeros / cells if cells else 0.0}
    used = defaultdict(int)
    for r in A:
        used[r["격자"]] += 1
    heavy = {g: {"쌍": n, "0 비율": gz.get(g, {}).get("0 비율")}
             for g, n in used.items() if gz.get(g, {}).get("0 비율", 0) > 0.5}
    W["V7 🔴 m5 사실상 전부 가려진 격자"] = {
        "🔴 이 검사는 통과/불통과가 아니라 수를 낸다": True,
        "무엇": "생활인구 적재가 마스킹 `*`(≤3)을 0 으로 접는다 — 0 비율이 그 격자가 얼마나 가려졌나다",
        "분자: 0 비율 > 50% 인 격자를 쓰는 쌍": sum(v["쌍"] for v in heavy.values()),
        "분모: 팔 A 쌍": len(A),
        "그 격자": heavy,
        "팔 A 격자별 0 비율": {g: round(gz.get(g, {}).get("0 비율", float("nan")), 6)
                        for g in sorted(used)},
        "🔴 티처 m5 가 지목한 격자": {"다사61004900": gz.get("다사61004900", {}).get("0 비율")},
    }

    # V8 o 누출 없음 (957 W7 재현)
    import copy
    p2 = copy.deepcopy(pairs)
    r8 = np.random.RandomState(5)
    for p in p2:
        if "o_결과" in p and isinstance(p["o_결과"].get("값"), list):
            p["o_결과"]["값"] = list(r8.rand(len(p["o_결과"]["값"])) * 100)
    b2 = L.build_arms(wd, coords, lp, p2)
    same = (len(b2["B"]) == len(B)) and all(
        b2["B"][i]["x1"] == B[i]["x1"] and b2["B"][i]["x3"] == B[i]["x3"]
        for i in range(len(B)))
    W["V8 o 누출 없음"] = {"o 를 난수로 바꿔도 x1·x3 이 같다": bool(same), "통과": bool(same)}
    W["V9 데몬을 재웠나"] = {"재웠나": R["🔴 데몬을 재웠나(launchctl 에서 읽는다)"],
                      "통과": R["🔴 데몬을 재웠나(launchctl 에서 읽는다)"]}
    W["통과 수"] = sum(1 for k, v in W.items() if isinstance(v, dict) and v.get("통과") is True)
    W["분모: 검사 수"] = sum(1 for k, v in W.items() if isinstance(v, dict) and "통과" in v)
    R["§5 배선 검사"] = W

    # ── §10 예측 채점 — 🔴 산문이 아니라 산출물 키에서 읽는다 ────────────────
    bA = M["팔 A · ① → ①+② (좌표원천)"]
    dwB = b3["🔴 자 A · 고정 모형 · 묶음 안"]["🔴 Δρ_within (쌍 가중 안쪽 평균)"]
    dwA = bA["🔴 자 A · 고정 모형 · 묶음 안"]["🔴 Δρ_within (쌍 가중 안쪽 평균)"]
    shB = b3["🔴 자 B · 켄달 짝 단위"]["🔴 안쪽 몫 = 안쪽 차 ÷ 전체 차"]
    Q = {
        "Q1 자 A 팔 B: Δρ_within > 0 이고 합산의 10% 이상": {
            "값": dwB, "맞았나": b3["🔴 D1-ㄱ 안쪽이 합산의 10% 이상인가"],
            "🔴 티처가 이미 낸 수라 맞히면 0 점": True},
        "Q2 자 B 안쪽 몫이 30~60%": {"값": shB, "맞았나": bool(0.30 <= shB <= 0.60),
                              "🔴 티처가 이미 낸 수라 맞히면 0 점": True},
        "Q3 🔴 Δρ_within 에 SE 를 붙이면 「나 — 못 가른다」": {
            "값": b3["🔴🔴 D3 판정(Δρ_within)"], "SE": b3["🔴 SE_boot(Δρ_within)"],
            "T": b3["🔴 문턱 T = max(0.00353, 2·SE)"],
            "맞았나": b3["🔴🔴 D3 판정(Δρ_within)"].startswith("나")},
        "Q4 팔 A Δρ_within(좌표원천) 이 음수": {"값": dwA, "맞았나": bool(dwA < 0)},
        "Q5 ①+지시자 → +③ 가 「다」 또는 「나」": {
            "값": d2b["판정"], "맞았나": not d2b["판정"].startswith("가")},
        "Q6 열 순열 null 로도 ㉢ 통과": {"값": cp["🔴 관측이 상위 5% 밖인가"],
                              "맞았나": cp["🔴 관측이 상위 5% 밖인가"]},
        "Q7 N_min 을 1 로 내려도 D1 판정 칸이 안 바뀐다": {
            "값": b3["§4 🔴 N_min 이 D1 판정을 바꾸나"],
            "맞았나": not b3["§4 🔴 N_min 이 D1 판정을 바꾸나"]},
        "Q8 V7 이 마스킹 50% 넘는 격자를 쓰는 쌍을 1 이상 낸다": {
            "값": W["V7 🔴 m5 사실상 전부 가려진 격자"]["분자: 0 비율 > 50% 인 격자를 쓰는 쌍"],
            "맞았나": bool(W["V7 🔴 m5 사실상 전부 가려진 격자"][
                "분자: 0 비율 > 50% 인 격자를 쓰는 쌍"] >= 1)},
    }
    Q["분자: 맞은 예측"] = sum(1 for k, v in Q.items() if isinstance(v, dict) and v.get("맞았나"))
    Q["분모: 예측"] = sum(1 for k, v in Q.items() if isinstance(v, dict) and "맞았나" in v)
    R["§10 예측 채점"] = Q

    # ── 🔴 산문 주장 = 산출물 키 (노트가 이 키에서 읽는다) ────────────────────
    R["🔴 산문 주장 = 산출물 키"] = {
        "957 의 「③ 이득의 전부가 도메인 사이」를 철회하나":
            b3["🔴🔴 D1 「전부 도메인 사이」를 철회하나"],
        "헤드라인 수 Δρ_within 을 0 과 가를 수 있나":
            not b3["🔴🔴 D3 판정(Δρ_within)"].startswith("나"),
        "③ 의 정보는 도메인 이름표로 대체 가능하다":
            R["§6 ㉰ 도메인 지시자 (사전등록 · 957 은 사후였다)"][
                "🔴🔴 D2 「③ 의 정보는 도메인 이름표로 대체 가능하다」를 싣나"],
        "팔 A 의 +0.070089 가 좌표 원천 사이의 것인가":
            bool(dwA < 0),
        "층 ③ 을 s 에 넣나": R["§6 D5 층 ③ 을 s 에 넣나"]["🔴🔴 채택(㉠㉡㉢)"],
        "카드 문턱 0.00353 을 이 자에서 쓸 수 있나":
            b3["🔴 카드 문턱 0.00353 이 이겼나"],
        "데몬을 재웠나": R["🔴 데몬을 재웠나(launchctl 에서 읽는다)"],
        "판 ρ 를 움직였나": False,
        "새 원천을 받았나": False,
    }
    # 🔴 티처 #96 M4 처방 — **모든 절이 `통과` 키를 갖는다.**
    #    957 의 `W9` 가 `통과` 키를 안 써서 **계수기에서 조용히 사라졌고** 배선 분모가
    #    9 에서 8 로 줄었다. ⑤′ 절 3 도 「`통과` 키가 없으면 **모른다**」로 센다 —
    #    **「모른다」를 「통과」로 읽지 않게 하려면 판정을 키로 내야 한다**(조항 59).
    R["§5 V1 입력이 957 이 쓴 그것인가"]["통과"] = R["§5 V1 입력이 957 이 쓴 그것인가"]["통과"]
    R["§5 배선 검사"]["통과"] = bool(W["통과 수"] == W["분모: 검사 수"])
    R["§6 자 A · 고정 모형 within/between"]["통과"] = bool(
        all(v["V2 채점 루프의 ridge_fit 호출 수(0 이어야 한다)"] == 0 for v in M.values()))
    R["§6 ㉰ 도메인 지시자 (사전등록 · 957 은 사후였다)"]["통과"] = bool(
        R["§6 ㉰ 도메인 지시자 (사전등록 · 957 은 사후였다)"][
            "🔴🔴 D2 「③ 의 정보는 도메인 이름표로 대체 가능하다」를 싣나"])
    R["§6 ㉮ 열 순열 null (사전등록 · 957 은 사후였다)"]["통과"] = bool(
        cp["🔴 관측이 상위 5% 밖인가"])
    R["§6 D5 층 ③ 을 s 에 넣나"]["통과"] = bool(R["§6 D5 층 ③ 을 s 에 넣나"]["🔴🔴 채택(㉠㉡㉢)"])
    R["§7 곁들이 · 표본 크기 실험 (판정 아님 · 957 의 수)"]["통과"] = None   # 🔴 판정 아님
    R["§10 예측 채점"]["통과"] = bool(Q["분자: 맞은 예측"] == Q["분모: 예측"])
    R["🔴 산문 주장 = 산출물 키"]["통과"] = None                              # 🔴 대조기가 본다
    R["🔴 절 회계"] = {
        "분자: `통과` 키를 가진 절": sum(1 for v in R.values()
                                if isinstance(v, dict) and "통과" in v),
        "분모: 절(dict 인 최상위 칸)": sum(1 for v in R.values() if isinstance(v, dict)),
        "🔴 `통과` 가 None 인 절(판정 아님을 명시한 것)": sum(
            1 for v in R.values() if isinstance(v, dict) and v.get("통과", 0) is None),
        "🔴 왜 세나": "957 의 W9 가 `통과` 키를 안 써서 계수기에서 조용히 사라졌다(티처 #96 M4). "
                 "「모른다」를 「통과」로 읽지 않으려면 판정을 키로 내야 한다",
        "통과": True}
    R["끝(UTC)"] = dt.datetime.now(dt.timezone.utc).isoformat()
    R["🔴 걸린 시간(초)"] = (dt.datetime.fromisoformat(R["끝(UTC)"]) - t0).total_seconds()
    OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    return R


if __name__ == "__main__":
    r = main()
    print(json.dumps(r["🔴 산문 주장 = 산출물 키"], ensure_ascii=False, indent=1))
    print(json.dumps(r["§10 예측 채점"], ensure_ascii=False, indent=1)[:1200])
