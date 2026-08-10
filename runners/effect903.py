"""노트 903 — A 등급 짝 둘의 **효과와 위약**. 채점기는 한 글자도 안 고친다.

사전등록: `docs/prereg_903_effect.md` (커밋 2bd5532f4836df0c1ee11583fe33d5a3c3d3532e
                                     · 2026-08-11T06:30:52+09:00)

🔴 이 러너는 등급을 다시 매기지 않는다. `runners/ident901.py` · `runners/ident902.py` 를
   **import 만** 한다(`median_split` · `sik1` · `typed_values` · `d3_backtrack` ·
   `resolve_d3` · `MIN_SIDE`). 900·901·902 세 사이클이 전부 채점 규칙을 다뤘다 —
   이번엔 **그 자로 재는** 사이클이다(티처 #65 ⑧ · 이슈 #145).

🔴 구간은 규약 47 — `lab.pairboot.cluster_boot` 의 BCa. 반환 종류 문자열을 그대로 싣는다.
🔴 `stamp` 는 **실행 시작**에서 찍는다(시작 ≠ 끝 · 티처 #64 C3).

실행: python3 runners/effect903.py       (산출물 runners/out903_effect.json)
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

# 🔴 도장은 실행 시작에서
T0 = time.time()
START = dt.datetime.now().isoformat(timespec="seconds")

from inv901 import SRC, dig, load_records, sha, sha_dir, MISSING   # noqa: E402
from ident902 import (MIN_SIDE, d3_backtrack, median_split,        # noqa: E402
                      resolve_d3, sik1, typed_values)
from lab import pairboot as PB                                     # noqa: E402

PREREG = {"파일": "docs/prereg_903_effect.md",
          "커밋": "2bd5532f4836df0c1ee11583fe33d5a3c3d3532e",
          "커밋 시각": "2026-08-11T06:30:52+09:00"}

K_SEEDS = 12          # 사전등록 §5 — 씨앗 널 K=12 (판 씨앗 0~11 과 같은 수 · K≥6)
REPS = 200            # 씨앗당 반복 → 위약 분포 2,400
B_BOOT = 10_000       # 규약 47 기본
BOOT_SEED = 903
MIN_PAIRED = 20       # 사전등록 §8 W-ㄹ 게이트


# ── 효과 크기 — Cliff's δ = 2·AUC − 1 ────────────────────────────────
def cliffs_delta(lo_v: np.ndarray, hi_v: np.ndarray) -> float:
    """δ = P(고군>저군) − P(고군<저군). 동률은 어느 쪽도 안 센다."""
    na, nb = len(lo_v), len(hi_v)
    if na == 0 or nb == 0:
        return float("nan")
    a = np.sort(lo_v)
    less = np.searchsorted(a, hi_v, side="left")     # a < b
    lesseq = np.searchsorted(a, hi_v, side="right")  # a <= b
    greater = na - lesseq                            # a > b
    return float((less - greater).sum() / (na * nb))


def make_stat(grp: np.ndarray, y: np.ndarray):
    """cluster_boot 이 부를 통계 — 인덱스 배열 → δ."""
    def stat(idx):
        g = grp[idx]
        v = y[idx]
        return cliffs_delta(v[~g], v[g])
    return stat


# ── 팔 하나의 자료 ────────────────────────────────────────────────────
def arm_popup(_broken_outcome=False):
    """ㄴ) 팝업 `entry_friction` → `outcome.totals.visitors`. 🔴 분모 D1(원천 레코드)."""
    recs = load_records("dir", "data/records")
    col = "intervention.attributes.entry_friction"
    ycol = "outcome.totals.visitors_TYPO" if _broken_outcome else "outcome.totals.visitors"
    tv_all = [dig(r, col) for r in recs]                       # 380 (결측 포함)
    yv_all = [dig(r, ycol) for r in recs]
    title = [(r.get("entities") or {}).get("brand_key") or "" for r in recs]
    return {"도메인": "팝업", "열": col, "형": "c", "결과": ycol,
            "분모 딱지": "D1 (원천 레코드 수)", "분모 값": len(recs),
            "처치 전량": tv_all, "결과 전량": yv_all, "제목 전량": title,
            "제목 원천": "entities.brand_key"}


_D0 = {}


def board():
    """챔피언 배선 `ff753.shell(base())` — 한 번만 싣는다(같은 객체를 재사용)."""
    if "d0" not in _D0:
        import ff753 as FF
        _D0["d0"] = FF.shell(FF.base())
    return _D0["d0"]


def arm_movie(normalize=True):
    """ㄱ) 영화 `개봉일` → kobis_axes 의 y. 🔴 분모 D3(판 채점 유보 · 챔피언 배선)."""
    d0 = board()
    d3map = d3_backtrack(d0, normalize=normalize)
    recs_all = load_records("jsonl", "data/ingest/kobis/axes_raw_897.jsonl")
    byid = {str(r.get("code")): r for r in recs_all}
    recs, hit = resolve_d3("영화", d3map, byid)      # 🔴 조용한 0 을 assert 로 막는다
    tv_all = [r.get("개봉일") for r in recs]
    yv_all = [r.get("_y_from_axes") for r in recs]
    title = [r.get("제목") or "" for r in recs]
    return {"도메인": "영화", "열": "개봉일", "형": "d", "결과": "kobis_axes.json 의 y",
            "분모 딱지": "D3 (판 채점 유보 · 챔피언 배선 ff753.shell(base()))",
            "분모 값": hit, "D3 되짚기": f"{hit}/{len(d3map['영화']['유보 키'])}",
            "처치 전량": tv_all, "결과 전량": yv_all, "제목 전량": title,
            "제목 원천": "제목"}


def _num(v):
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and v is not MISSING)


def paired(arm, split_min=True):
    """짝 행(처치·결과 둘 다 관측) + 902 규칙의 분할. `split_min=False` 는 W-ㄱ 결함."""
    typ = arm["형"]
    tv, yv = arm["처치 전량"], arm["결과 전량"]
    tvt = typed_values(typ, tv)                       # 902 코드 그대로
    ok_t = [i for i, v in enumerate(tv)
            if len(typed_values(typ, [v])["쓴 값"]) == 1]
    idx = [i for i in ok_t if _num(yv[i])]
    vals_paired = [typed_values(typ, [tv[i]])["쓴 값"][0] for i in idx]
    sp = median_split(tvt["쓴 값"])                    # 🔴 식1 과 같은 분할(전 관측 값)
    cut = sp["절단값"]
    if not split_min:                                 # W-ㄱ 심는 결함 — 절단을 최소값으로
        cut = min(tvt["쓴 값"])
    grp = np.array([v >= cut for v in vals_paired], bool)
    return {"짝 인덱스": idx, "짝 처치값": vals_paired,
            "짝 결과": np.array([float(yv[i]) for i in idx], float),
            "고군 마스크": grp, "절단값": cut, "분할(식1 과 같은 값)": sp,
            "제목": [arm["제목 전량"][i] for i in idx]}


# ── 배선 검사 — 🔴 심어서 발화를 확인한다 (넷) ────────────────────────
def wiring_checks():
    w = {}

    # W-ㄱ 분할 함수 파손 → 한 군이 0 행
    pu = arm_popup()
    good = paired(pu, split_min=True)
    bad = paired(pu, split_min=False)
    def gate_side(p):
        lo = int((~p["고군 마스크"]).sum()); hi = int(p["고군 마스크"].sum())
        return (lo >= MIN_SIDE and hi >= MIN_SIDE), lo, hi
    g_ok, lo0, hi0 = gate_side(good)
    g_bad, lo1, hi1 = gate_side(bad)
    w["W-ㄱ 분할 함수 파손"] = {
        "심은 것": "median_split 의 절단값을 최소값으로 바꿔 저군을 0 행으로",
        "게이트": f"양쪽 ≥ MIN_SIDE({MIN_SIDE})",
        "정상(음성 대조)": {"저군": lo0, "고군": hi0, "게이트 통과": g_ok},
        "심은 뒤": {"저군": lo1, "고군": hi1, "게이트 통과": g_bad},
        "🔴 발화": (not g_bad) and g_ok}

    # W-ㄴ 위약 셔플이 실제로 안 섞임(항등 순열)
    y, grp = good["짝 결과"], good["고군 마스크"]
    real = cliffs_delta(y[~grp], y[grp])
    rng = np.random.default_rng(0)
    ds_ok = [float(cliffs_delta(y[p][~grp], y[p][grp]))
             for p in (rng.permutation(len(y)) for _ in range(50))]
    ident = np.arange(len(y))
    ds_bad = [float(cliffs_delta(y[ident][~grp], y[ident][grp])) for _ in range(50)]
    def gate_shuf(ds):
        return (len(set(np.round(ds, 12))) >= 2
                and abs(float(np.mean(ds)) - real) > 1e-12)
    w["W-ㄴ 위약 셔플 무효화"] = {
        "심은 것": "순열을 항등으로 바꿔 위약이 진짜를 그대로 베끼게",
        "게이트": "위약 δ 의 값 가짓수 ≥ 2 그리고 위약 평균 ≠ 진짜 δ",
        "진짜 δ": round(real, 6),
        "정상(음성 대조)": {"값 가짓수": len(set(np.round(ds_ok, 12))),
                        "위약 평균": round(float(np.mean(ds_ok)), 6),
                        "게이트 통과": gate_shuf(ds_ok)},
        "심은 뒤": {"값 가짓수": len(set(np.round(ds_bad, 12))),
                 "위약 평균": round(float(np.mean(ds_bad)), 6),
                 "게이트 통과": gate_shuf(ds_bad)},
        "🔴 발화": (not gate_shuf(ds_bad)) and gate_shuf(ds_ok)}

    # W-ㄷ 영화 키 정규화 되돌리기 → 되짚기 조용한 0
    try:
        arm_movie(normalize=True)
        neg = "통과(정상 배선에서 assert 안 남)"
        neg_ok = True
    except AssertionError as e:
        neg, neg_ok = f"🔴 정상에서 발화했다: {e}", False
    fired, seen = False, None
    try:
        arm_movie(normalize=False)
    except AssertionError as e:
        fired, seen = True, str(e)[:200]
    w["W-ㄷ 키 정규화 되돌리기"] = {
        "심은 것": "d3_backtrack(normalize=False) — `KOBIS-` 접두 제거를 생략",
        "게이트": "resolve_d3 의 조용한 0/부분 실패 assert",
        "정상(음성 대조)": neg,
        "심은 뒤 본 것": seen,
        "🔴 발화": fired and neg_ok}

    # W-ㄹ 결과 열 오타 → 짝 0 행 (🔴 조항 59 — 빈 것을 부정으로 읽는 길)
    pb = arm_popup(_broken_outcome=True)
    bad4 = paired(pb)
    n_ok, n_bad = len(good["짝 인덱스"]), len(bad4["짝 인덱스"])
    w["W-ㄹ 결과 열 오타"] = {
        "심은 것": "결과 열 이름을 `outcome.totals.visitors_TYPO` 로",
        "게이트": f"짝 행 ≥ {MIN_PAIRED}",
        "정상(음성 대조)": {"짝 행": n_ok, "게이트 통과": n_ok >= MIN_PAIRED},
        "심은 뒤": {"짝 행": n_bad, "게이트 통과": n_bad >= MIN_PAIRED},
        "🔴 발화": (n_bad < MIN_PAIRED) and (n_ok >= MIN_PAIRED)}

    w["🔴 심은 결함 수"] = 4
    w["🔴 발화한 수"] = sum(1 for k, v in w.items()
                        if isinstance(v, dict) and v.get("🔴 발화"))
    w["통과"] = (w["🔴 발화한 수"] == 4)
    return w


# ── 위약 셋 ───────────────────────────────────────────────────────────
def placebos(arm, p, real_delta):
    """사전등록 §5 — 위약 ①값 셔플 ②무작위 중앙값 분할 ③전 행 셔플."""
    y, grp = p["짝 결과"], p["고군 마스크"]
    n = len(y)
    typ = arm["형"]
    tvt_all = typed_values(typ, arm["처치 전량"])["쓴 값"]
    real_sp = p["분할(식1 과 같은 값)"]
    vals_paired = p["짝 처치값"]

    d1, d2 = [], []                     # 위약 ① · ② 의 δ
    per_seed1, per_seed2 = [], []
    sp2_same = 0                        # 위약 ② 가 진짜 분할을 재현한 횟수
    sik3_yes, sp3_same = 0, 0           # 위약 ③ 식1=예 / 소수 쪽 재현
    n3 = 0
    base_counter = Counter(v for v in arm["처치 전량"] if _num(v) or isinstance(v, str))

    for s in range(K_SEEDS):
        rng = np.random.default_rng(9030000 + s)
        a1, a2 = [], []
        for _ in range(REPS):
            # ① 결과 셔플
            per = rng.permutation(n)
            a1.append(cliffs_delta(y[per][~grp], y[per][grp]))
            # ② 처치 열 안 셔플 → **같은 median_split 규칙**으로 다시 가른다
            perm_vals = [vals_paired[i] for i in rng.permutation(n)]
            shuffled_col = [tvt_all[i] for i in rng.permutation(len(tvt_all))]
            sp2 = median_split(shuffled_col)
            if (sp2["절단값"] == real_sp["절단값"] and sp2["저군"] == real_sp["저군"]
                    and sp2["고군"] == real_sp["고군"]
                    and sp2["소수 쪽"] == real_sp["소수 쪽"]):
                sp2_same += 1
            g2 = np.array([v >= sp2["절단값"] for v in perm_vals], bool)
            a2.append(cliffs_delta(y[~g2], y[g2]))
            # ③ 전 행 셔플(결측 포함) → 식1 을 902 코드로 다시 판정
            raw = list(arm["처치 전량"])
            order = rng.permutation(len(raw))
            sraw = [raw[i] for i in order]
            tvt3 = typed_values(typ, sraw)
            j3, why3 = sik1(typ, Counter(sraw if typ == "b" else []), tvt3,
                            arm["분모 딱지"])
            n3 += 1
            if j3 == "예":
                sik3_yes += 1
            if why3["소수 쪽"] == real_sp["소수 쪽"]:
                sp3_same += 1
        d1 += a1
        d2 += a2
        per_seed1.append(float(np.nanmean(a1)))
        per_seed2.append(float(np.nanmean(a2)))

    d1 = np.asarray(d1, float)
    d2 = np.asarray(d2, float)
    tot = K_SEEDS * REPS

    def summ(d, label):
        return {"반복 수": int(np.isfinite(d).sum()), "평균": round(float(np.nanmean(d)), 6),
                "SD": round(float(np.nanstd(d)), 6),
                "|δ| 95분위": round(float(np.nanpercentile(np.abs(d), 95)), 6),
                "5분위": round(float(np.nanpercentile(d, 5)), 6),
                "95분위": round(float(np.nanpercentile(d, 95)), 6),
                "🔴 진짜 |δ| 를 넘은 위약 비율(경험적 p)":
                    round(float(np.mean(np.abs(d) >= abs(real_delta))), 6),
                "이름": label}

    missing = sum(1 for v in arm["처치 전량"] if not _num(v) and
                  not (isinstance(v, str) and v))
    out = {
        "🔴 씨앗 수 K": K_SEEDS, "씨앗당 반복": REPS, "총 반복": tot,
        "위약 ① 값 셔플(결과를 섞는다)": summ(d1, "①"),
        "위약 ② 무작위 중앙값 분할(처치 열 안 셔플)": summ(d2, "②"),
        "🔴 위약 ② 가 진짜 분할(절단값·저군·고군·소수 쪽)을 재현한 횟수":
            {"재현": sp2_same, "분모": tot,
             "재현율": round(sp2_same / tot, 6)},
        "씨앗 널(K=12)": {
            "위약 ① 씨앗별 평균의 SD": round(float(np.std(per_seed1)), 6),
            "위약 ② 씨앗별 평균의 SD": round(float(np.std(per_seed2)), 6),
            "위약 ① 씨앗별 평균": [round(x, 6) for x in per_seed1],
            "위약 ② 씨앗별 평균": [round(x, 6) for x in per_seed2]},
    }
    if missing == 0:
        out["위약 ③ 전 행 셔플"] = {
            "🔴 해당 없음(② 와 동일)": "이 팔은 처치 열 결측이 0 이라 「전 행」과 「짝 행」이 같은 집합이다 — **안 한 것이 아니라 같은 것이다**(조항 59)",
            "식1=예 / 분모": f"{sik3_yes}/{n3}",
            "소수 쪽 재현 / 분모": f"{sp3_same}/{n3}"}
    else:
        out["위약 ③ 전 행 셔플(결측 포함)"] = {
            "🔴 δ 는 안 낸다": "전 행 셔플은 짝 행 수를 바꾼다 — 분모가 달라 ①② 의 δ 와 안 잇는다(조항 60)",
            "처치 열 결측 행": missing,
            "식1=예": sik3_yes, "분모": n3,
            "식1=예 비율": round(sik3_yes / n3, 6),
            "소수 쪽 재현": sp3_same, "소수 쪽 재현율": round(sp3_same / n3, 6)}
    return out


# ── 팔 하나를 끝까지 ──────────────────────────────────────────────────
def run_arm(arm, judge: bool, note: str):
    p = paired(arm)
    y, grp = p["짝 결과"], p["고군 마스크"]
    n = len(y)
    lo_n, hi_n = int((~grp).sum()), int(grp.sum())

    # 🔴 게이트 — 측정 전에 실제로 본다(조항 59)
    gates = {f"짝 행 ≥ {MIN_PAIRED}": n >= MIN_PAIRED,
             f"양쪽 ≥ MIN_SIDE({MIN_SIDE})": lo_n >= MIN_SIDE and hi_n >= MIN_SIDE}
    assert all(gates.values()), f"{arm['도메인']} 게이트 실패: {gates}"

    real = cliffs_delta(y[~grp], y[grp])

    # 규약 47 — cluster_boot BCa
    clusters, wire = PB.clusters_of(p["제목"])
    est, blo, bhi, kind = PB.cluster_boot(make_stat(grp, y), clusters,
                                          B=B_BOOT, seed=BOOT_SEED)
    vd = PB.verdict(blo, bhi)

    pl = placebos(arm, p, real)
    p95 = pl["위약 ② 무작위 중앙값 분할(처치 열 안 셔플)"]["|δ| 95분위"]
    cond_a = vd in ("승", "패")
    cond_b = abs(real) > p95

    res = {
        "도메인": arm["도메인"], "열": arm["열"], "형": arm["형"], "결과": arm["결과"],
        "🔴 분모 딱지": arm["분모 딱지"], "분모 값": arm["분모 값"],
        "짝 행": n, "저군": lo_n, "고군": hi_n, "절단값": p["절단값"],
        "🔴 분할은 902 의 median_split 을 그대로 부른다": True,
        "게이트": gates,
        "효과 크기 Cliff's δ (저군 대 고군 · 양수=고군이 크다)": round(real, 6),
        "저군 결과 중앙값": round(float(np.median(y[~grp])), 4),
        "고군 결과 중앙값": round(float(np.median(y[grp])), 4),
        "🔴 구간(규약 47 · lab.pairboot.cluster_boot)": {
            "점추정": round(est, 6), "lo": round(blo, 6), "hi": round(bhi, 6),
            "🔴 종류": kind,
            "🔴 폴백 사유": ("없음 — BCa" if kind == "BCa"
                        else f"BCa 아님: `cluster_boot` 이 `{kind}` 를 냈다(규약 47 의 등록된 폴백)"),
            "B": B_BOOT, "씨앗": BOOT_SEED,
            "군집 병기": wire, "군집 원천": arm["제목 원천"],
            "판정(pairboot.verdict)": vd},
        "위약": pl,
        "🔴 판정 조건 (가) 구간이 0 을 안 문다": cond_a,
        "🔴 판정 조건 (나) |δ| > 위약 ② 의 |δ| 95분위": cond_b,
        "위약 ② |δ| 95분위": p95,
        # 🔴 사후 서술(판정에 안 쓴다) — 「힘을 안 준다」를 수로 바꾼다
        "🔴 이 설계가 잴 수 있는 최소 효과(MDE · 사후 서술 · 판정 미사용)": {
            "탐지 문턱 = 위약 ② |δ| 95분위": p95,
            "위약 ② SD": pl["위약 ② 무작위 중앙값 분할(처치 열 안 셔플)"]["SD"],
            "MDE(검정력 80% 근사 = 문턱 + 0.84·SD)":
                round(p95 + 0.84 * pl["위약 ② 무작위 중앙값 분할(처치 열 안 셔플)"]["SD"], 6),
            "실측 |δ| / MDE": round(abs(real) / (p95 + 0.84 * pl[
                "위약 ② 무작위 중앙값 분할(처치 열 안 셔플)"]["SD"]), 4),
            "⚠ 근사다": "정규 근사이고 순열 널의 꼬리를 액면 그대로 믿지 않는다"},
        "🔴 이 팔로 판정하나": judge,
        "표지": note,
    }
    if judge:
        res["🔴 판정"] = (
            "효과를 쟀다 — (가)(나) 둘 다 참. 🔴 그러나 **채택이 아니라 후보다**(노트 133)"
            if (cond_a and cond_b) else
            "🔴 「효과가 없다」가 아니라 **「A 등급이 효과를 잴 힘을 안 준다」**이다. "
            "그때 다음 사이클은 채점기가 아니라 **표본**으로 간다 (사전등록 §6 의 어법 그대로)")
    else:
        res["🔴 판정"] = ("측정했으나 판정 안 함 — 구조적 교란(처치가 곧 결과 창의 원점). "
                       "사전등록 §3 · 이슈 #145 ④")
    return res, p


def main():
    out = {"노트": 903, "사전등록": PREREG, "시작 시각": START,
           "🔴 채점기 무접촉": "ident901.py · ident902.py 를 import 만 했다. "
                          "등급 규칙 · 식1~식5 · 문턱 10 · max_balanced() 한 글자도 안 고쳤다",
           "🔴 자를 뗐다(⓪-가)": "판 ρ 와 채택 문턱은 이번 판정에 안 썼다 — 재는 것이 "
                            "「팔 사이의 판 차」가 아니라 「한 도메인 안 두 군의 결과 차」다. "
                            "대신 Cliff's δ + 규약 47 BCa + 위약 분포를 자로 썼다",
           "코드 sha256": {"runners/effect903.py": sha(Path(__file__)),
                          "runners/ident902.py": sha(ROOT / "runners/ident902.py"),
                          "runners/ident901.py": sha(ROOT / "runners/ident901.py"),
                          "runners/inv901.py": sha(ROOT / "runners/inv901.py"),
                          "lab/pairboot.py": sha(ROOT / "lab/pairboot.py")}}

    h, nf = sha_dir(ROOT / "data/records")
    out["입력 sha256"] = {
        "data/records": {"sha256(결합)": h, "파일 수": nf},
        "data/ingest/kobis/axes_raw_897.jsonl":
            {"sha256": sha(ROOT / "data/ingest/kobis/axes_raw_897.jsonl")},
        "data/state/kobis_axes.json":
            {"sha256": sha(ROOT / "data/state/kobis_axes.json")}}

    print("배선 검사…", flush=True)
    out["🔴 배선 검사(심어서 확인 · 넷)"] = wiring_checks()
    assert out["🔴 배선 검사(심어서 확인 · 넷)"]["통과"], \
        "🔴 배선 검사가 다 발화하지 않았다 — 측정으로 못 넘어간다"

    print("팔 ㄴ 팝업…", flush=True)
    pu = arm_popup()
    r_pu, p_pu = run_arm(pu, judge=True,
                         note="🔴 D1 분모라 판 유보 위에 서지 않는다 — 팝업은 축 파일이 없어"
                              " D3 되짚기가 원리상 불가능하다. 판 ρ 의 유보 3,775 와 안 잇는다(조항 60)")

    print("팔 ㄱ 영화…", flush=True)
    mv = arm_movie()
    r_mv, p_mv = run_arm(mv, judge=False,
                         note="🔴 이슈 #145 ① 이 지정했으나 ④ 가 빼라는 「날짜형 9」의 하나다. "
                              "재되 판정 안 한다")

    # 🔴 P4 — 창 절단을 주장이 아니라 측정으로
    KA = json.loads((ROOT / "data/state/kobis_axes.json").read_text())
    recs_all = load_records("jsonl", "data/ingest/kobis/axes_raw_897.jsonl")
    byid = {str(r.get("code")): r for r in recs_all}
    d3map = d3_backtrack(board())
    recs, _ = resolve_d3("영화", d3map, byid)
    idx = p_mv["짝 인덱스"]
    lastobs, cens = [], []
    for i in idx:
        a = KA.get("KOBIS-" + str(recs[i].get("code"))) or {}
        lastobs.append(a.get("마지막 관측일차"))
        cens.append(bool(a.get("검열(개봉+14 미달)")))
    g = p_mv["고군 마스크"]
    lo_l = [v for v, m in zip(lastobs, g) if not m and v is not None]
    hi_l = [v for v, m in zip(lastobs, g) if m and v is not None]
    lo_c = [c for c, m in zip(cens, g) if not m]
    hi_c = [c for c, m in zip(cens, g) if m]
    out["🔴 P4 창 절단 — 주장이 아니라 측정"] = {
        "무엇": "영화 y 는 `개봉+0~20일 창의 마지막 누적`(runners/build836.py:89)이라 "
              "늦게 개봉한 영화는 창이 덜 찬다. 그것을 `마지막 관측일차` 로 직접 잰다",
        "저군(이른 개봉) 마지막 관측일차 평균": round(float(np.mean(lo_l)), 4),
        "고군(늦은 개봉) 마지막 관측일차 평균": round(float(np.mean(hi_l)), 4),
        "차(고−저)": round(float(np.mean(hi_l)) - float(np.mean(lo_l)), 4),
        "저군 n": len(lo_l), "고군 n": len(hi_l),
        "저군 검열(개봉+14 미달) 비율": round(sum(lo_c) / len(lo_c), 6),
        "고군 검열(개봉+14 미달) 비율": round(sum(hi_c) / len(hi_c), 6),
        "마지막 관측일차 대 y 스피어만(짝 406)": None,
    }
    from scipy.stats import spearmanr
    okl = [(v, yy) for v, yy in zip(lastobs, p_mv["짝 결과"]) if v is not None]
    rho = float(spearmanr([a for a, _ in okl], [b for _, b in okl]).correlation)
    out["🔴 P4 창 절단 — 주장이 아니라 측정"]["마지막 관측일차 대 y 스피어만(짝 406)"] = round(rho, 6)
    out["🔴 P4 창 절단 — 주장이 아니라 측정"]["P4 판정"] = (
        "확인 — 늦은 개봉군의 창이 덜 찼다(차 < 0)"
        if float(np.mean(hi_l)) < float(np.mean(lo_l)) else
        "🔴 반증 — 차가 0 이거나 부호가 반대다. 사전등록 §3 의 「구조적 교란」 주장이 "
        "이 자료에서 이 자로는 반증된다")

    # 🔴 부차 결과 둘 — 사전등록 §3 에서 **판정 미사용**으로 미리 못 박은 것
    sec = {"🔴 판정에 안 쓴다":
           "사전등록 §3 — 분모가 다르므로 1차 결과(짝 95)의 수와 **안 잇는다**(조항 60). "
           "🔴 「1차가 널이라 여기서 뭘 찾았다」로 읽으면 그게 사후 부분집합이다"}
    for ycol in ("outcome.totals.sales_krw", "outcome.totals.rev_mm_recognized"):
        a = arm_popup()
        a["결과"] = ycol
        a["결과 전량"] = [dig(r, ycol) for r in load_records("dir", "data/records")]
        q = paired(a)
        yy, gg = q["짝 결과"], q["고군 마스크"]
        lo_n, hi_n = int((~gg).sum()), int(gg.sum())
        row = {"짝 행": len(yy), "저군": lo_n, "고군": hi_n}
        if len(yy) >= MIN_PAIRED and lo_n >= MIN_SIDE and hi_n >= MIN_SIDE:
            dd = cliffs_delta(yy[~gg], yy[gg])
            cl, wr = PB.clusters_of(q["제목"])
            e, l, h, kd = PB.cluster_boot(make_stat(gg, yy), cl, B=B_BOOT, seed=BOOT_SEED)
            row |= {"δ": round(dd, 6), "lo": round(l, 6), "hi": round(h, 6),
                    "🔴 종류": kd, "판정(pairboot.verdict)": PB.verdict(l, h),
                    "군집 병기": wr}
        else:
            row["🔴 못 쟀다"] = (f"게이트 미달 — 짝 행 {len(yy)} · 저군 {lo_n} · 고군 {hi_n}. "
                            "「효과 0」이 아니라 **못 쟀다**(조항 59)")
        sec[ycol] = row
    out["🔴 부차 결과(팝업 · 판정 미사용)"] = sec

    out["팔 ㄴ 팝업 entry_friction (판정을 진다)"] = r_pu
    out["팔 ㄱ 영화 개봉일 (재되 판정 안 한다)"] = r_mv

    # 사전등록 예측 판정
    pl_pu = r_pu["위약"]
    pl_mv = r_mv["위약"]
    out["🔴 사전등록 예측 판정"] = {
        "P1 팝업 δ 부호는 음수": {
            "실측 δ": r_pu["효과 크기 Cliff's δ (저군 대 고군 · 양수=고군이 크다)"],
            "판정": ("확인" if r_pu["효과 크기 Cliff's δ (저군 대 고군 · 양수=고군이 크다)"] < 0
                   else "🔴 반증 — 부호가 양수다"),
            "⚠ 자가 다르다": "노트 583 의 부호는 **판 라벨 · 하네스 0~1 열**에 대한 것이고 "
                        "903 은 **원천 원값 · 원 방문자 수**다. 같은 이름의 다른 자다"},
        "P2 위약 ② 가 진짜 분할을 100% 재현": {
            "팝업": pl_pu["🔴 위약 ② 가 진짜 분할(절단값·저군·고군·소수 쪽)을 재현한 횟수"],
            "영화": pl_mv["🔴 위약 ② 가 진짜 분할(절단값·저군·고군·소수 쪽)을 재현한 횟수"],
            "판정": None},
        "P3 위약 ③ 팝업 식1=예 100%": None,
        "P4 영화 창 절단": out["🔴 P4 창 절단 — 주장이 아니라 측정"]["P4 판정"],
        "P5 위약 ① 과 ② 는 구별 안 된다": None,
    }
    pr = out["🔴 사전등록 예측 판정"]
    pr["P2 위약 ② 가 진짜 분할을 100% 재현"]["판정"] = (
        "확인" if (pl_pu["🔴 위약 ② 가 진짜 분할(절단값·저군·고군·소수 쪽)을 재현한 횟수"]["재현율"] == 1.0
                and pl_mv["🔴 위약 ② 가 진짜 분할(절단값·저군·고군·소수 쪽)을 재현한 횟수"]["재현율"] == 1.0)
        else "🔴 반증 — 재현율이 100% 가 아니다")
    k3 = [k for k in pl_pu if k.startswith("위약 ③")][0]
    pr["P3 위약 ③ 팝업 식1=예 100%"] = {
        "실측": pl_pu[k3],
        "판정": ("확인" if pl_pu[k3].get("식1=예 비율") == 1.0 else "🔴 반증")}
    def p5(pl):
        a = pl["위약 ① 값 셔플(결과를 섞는다)"]
        b = pl["위약 ② 무작위 중앙값 분할(처치 열 안 셔플)"]
        ok = (a["5분위"] <= b["95분위"] <= a["95분위"]
              and a["5분위"] <= b["5분위"] <= a["95분위"])
        return {"① 5~95분위": [a["5분위"], a["95분위"]],
                "② 5~95분위": [b["5분위"], b["95분위"]],
                "① SD": a["SD"], "② SD": b["SD"],
                "판정": "확인" if ok else "🔴 반증 — 사전등록 규칙대로면 두 분포가 갈린다"}
    pr["P5 위약 ① 과 ② 는 구별 안 된다"] = {
        "🔴 사전등록이 팔을 안 지정했다 — 둘 다 낸다": True,
        "팝업": p5(pl_pu), "영화": p5(pl_mv),
        "🔴 자가 적발 — 이 사전등록 규칙은 거의 퇴화다":
            "규칙이 「② 의 95분위가 ① 의 5~95분위 안에 드나」인데, 두 분포가 **같은 법**이면 "
            "②의 95분위는 ①의 95분위 근처에 떨어지고 **경계를 넘을 확률이 대략 절반**이다. "
            "즉 이 규칙은 동전 던지기에 가깝다. 🔴 **규칙을 안 바꾸고 결과를 그대로 싣는다** — "
            "바꾸면 그게 사후 규칙 변경이다. 다음 사이클이 고칠 항목이다"}

    out["🔴 헤드라인"] = {
        "판정을 지는 팔": "팝업 entry_friction (D1 · 짝 95)",
        "판정": r_pu["🔴 판정"],
        "효과 크기 δ": r_pu["효과 크기 Cliff's δ (저군 대 고군 · 양수=고군이 크다)"],
        "구간": [r_pu["🔴 구간(규약 47 · lab.pairboot.cluster_boot)"]["lo"],
               r_pu["🔴 구간(규약 47 · lab.pairboot.cluster_boot)"]["hi"]],
        "구간 종류": r_pu["🔴 구간(규약 47 · lab.pairboot.cluster_boot)"]["🔴 종류"],
        "🔴 A 등급은 처치–결과 관계에 대해 0비트를 나른다": {
            "무엇": "`runners/ident902.py` 의 식1(`sik1`)과 `median_split` 은 **인자에 결과가 없다** — "
                  "값의 **다중집합**만 본다. 그래서 처치 열을 어떻게 섞어도 절단값·저군·고군·소수 쪽이 "
                  "그대로이고 등급도 그대로다",
            "🔴 이것은 항등식이다": "그리고 그 사실을 **알고도 쟀다** — 팝업 2400/2400 · 영화 2400/2400. "
                            "티처 M5 의 병은 항등식을 **증거로 판 것**이었지 항등식을 잰 것이 아니다. "
                            "여기서는 **항등식이라는 것 자체가 결론**이다",
            "뜻": "「A 21」은 **자료가 개입을 식별한다**는 말이 아니라 **그 열의 값이 골고루 퍼져 있다**는 말이다. "
                 "티처 M1·M2·M5 가 각각 다른 각도에서 가리킨 것이 같은 하나였다",
            "🔴 노트 887 과 같은 꼴": "「위약이 아무것도 안 했다 — 문턱은 위약으로 잴 수 있는 물건이 아니었다」. "
                             "**A 등급도 위약으로 잴 수 있는 물건이 아니다**"},
        "🔴 A 등급이 위약으로 안 깨진다":
            "위약 ②·③ 이 진짜 분할을 그대로 재현한다 — `median_split` 과 식1 은 **결과를 한 번도 안 본다**. "
            "그래서 **A 등급은 위약으로 잴 수 있는 물건이 아니다**(노트 887 이 문턱에서 겪은 것과 같은 꼴)",
    }

    # 🔴 다중성 — 이 사이클이 낸 δ 를 **세어서** 적는다(고른 것이 아니라)
    allest = [("1차 · 팝업 visitors (판정)", r_pu["🔴 구간(규약 47 · lab.pairboot.cluster_boot)"]["판정(pairboot.verdict)"]),
              ("1차 · 영화 개봉일 (판정 안 함)", r_mv["🔴 구간(규약 47 · lab.pairboot.cluster_boot)"]["판정(pairboot.verdict)"]),
              ("부차 · 팝업 sales_krw (판정 미사용)", sec["outcome.totals.sales_krw"].get("판정(pairboot.verdict)", "못 쟀다")),
              ("부차 · 팝업 rev_mm_recognized (판정 미사용)", sec["outcome.totals.rev_mm_recognized"].get("판정(pairboot.verdict)", "못 쟀다"))]
    out["🔴 다중성 — 이 사이클이 낸 구간 전량"] = {
        "낸 구간 수": len(allest),
        "전량": [{"이름": a, "verdict": b} for a, b in allest],
        "0 을 안 문 것": [a for a, b in allest if b in ("승", "패")],
        "🔴 그 하나는 판정 미사용 팔이다":
            "`outcome.totals.sales_krw` δ={δ} [{lo},{hi}] 는 **짝 {n}**(D1 380 중)이고 "
            "사전등록 §3 이 **측정 전에** 「부차 · 판정 미사용」으로 못 박은 것이다. ".format(
                δ=sec["outcome.totals.sales_krw"].get("δ"),
                lo=sec["outcome.totals.sales_krw"].get("lo"),
                hi=sec["outcome.totals.sales_krw"].get("hi"),
                n=sec["outcome.totals.sales_krw"].get("짝 행")) +
            "🔴 **이 사이클의 결론에 안 넣는다** — 넣으면 그게 사후 부분집합이다(티처 #60 M2 가 걸린 병). "
            "🔴 그리고 그 35 는 **매출을 보고한 팝업만** 남은 것이라 보고 선택이 그대로 살아 있다. "
            "**다음 사이클의 후보이지 이번 판정이 아니다**",
        "다중성 보정": "🔴 안 했다 — 안 한 것이지 필요 없는 것이 아니다. 구간 넷 중 하나가 0 밖인 것은 "
                  "α=0.05 에서 우연으로도 흔하다(1−0.95⁴ ≈ 0.19)"}

    out["🔴 못 잰 것 (「없다」가 아니다)"] = [
        "팝업의 D3 되짚기 — 축 파일이 없어(popup_v2.npz 경로) **원리상 불가능**하다. 「0」이 아니라 「못 셌다」",
        "팝업 `sales_krw`(짝 35)·`rev_mm_recognized`(짝 89) 두 결과 — 부차 측정이고 분모가 달라 1차 수와 안 이었다",
        "날짜형 나머지 8 짝 — 사전등록 §3 대로 **안 쟀다**",
        "교란 통제 — 어느 팔도 공변량을 하나도 안 넣었다. δ 는 **조건 없는 두 군 차**다",
        "노트 468(규모가 부호를 바꾼다)이 말하는 **비단조** — 중앙값 한 번의 분할로는 못 본다",
    ]

    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["걸린 초"] = round(time.time() - T0, 1)
    (ROOT / "runners/out903_effect.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out["🔴 헤드라인"], ensure_ascii=False, indent=1))
    print("→ runners/out903_effect.json")


if __name__ == "__main__":
    main()
