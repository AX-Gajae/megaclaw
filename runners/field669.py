"""노트 669 — 사전학습의 **표본 구성**도 누출이었나. 고침 전/후를 같은 씨앗으로.

재는 것 셋(사전등록):
  ① `field()` 가 고르는 **동네 수**와 빠진 동네가 어디인가
  ② `horizons()` 표가 바뀌나 (특히 h=30 의 0.037)
  ③ **검증 R²** 가 바뀌나 (+0.1639) · **위약**도 같이

**위약을 여기서 정의한다.** 원래 −0.0206 은 대장에 숫자만 있고 **설계가 없다** ---
그러면 재현이 안 된다. 여기서 정하고 적는다: **목표를 동네 안에서 시간축으로
섞는다**(관측 무늬 유지 · 노트 335 의 이 과제 판). 그러면 이웃·과거 무늬가
실어 나르는 정보만 사라지고 결측 무늬와 분포는 그대로다.
"""
import json
import numpy as np
from pathlib import Path
import state.fieldmodel as F

TRAIN_END = F.TRAIN_END


# ── ① 동네 고르기 ─────────────────────────────────────────────
def codes_of(stats_end):
    from ingest.visitors import series
    ser = series("2")
    days = sorted({d for v in ser.values() for d in v})
    pick = days if stats_end is None else [d for d in days if d <= stats_end]
    pset = set(pick)
    return sorted(c for c in ser
                  if sum(1 for d in ser[c] if d in pset) > len(pick) * 0.9), len(days), len(pick)


old, nd, _ = codes_of(None)              # 고침 전 --- 전 구간 덮음
new, _, npk = codes_of(TRAIN_END)        # 고침 후 --- 학습 구간 덮음
only_old = sorted(set(old) - set(new))
only_new = sorted(set(new) - set(old))
print(json.dumps({"① 동네 고르기": {
    "전 구간 날": nd, "학습 구간 날": npk,
    "고침 전 동네": len(old), "고침 후 동네": len(new),
    "고침 전에만 있던 동네": only_old[:20], "그 수": len(only_old),
    "고침 후에만 있던 동네": only_new[:20], "그 수": len(only_new)}},
    ensure_ascii=False, indent=1), flush=True)

# ── ② 지평 표 ─────────────────────────────────────────────────
def horizons_with(stats_end, hs=(1, 3, 7, 14, 30, 60, 90, 180)):
    _c, _d, X = F.field(stats_end=stats_end)
    out = {}
    for h in hs:
        a, b = X[:, :-h].ravel(), X[:, h:].ravel()
        ok = np.isfinite(a) & np.isfinite(b)
        out[h] = round(float(np.corrcoef(a[ok], b[ok])[0, 1] ** 2), 4)
    return out


h_old = horizons_with(None)
h_new = horizons_with(TRAIN_END)
print(json.dumps({"② 지속성 R2": {"고침 전(전 구간 통계)": h_old,
                                "고침 후(학습 구간 통계)": h_new,
                                "h=30 차": round(h_new[30] - h_old[30], 4)}},
                 ensure_ascii=False, indent=1), flush=True)

# ── ③ 검증 R² 와 위약 ─────────────────────────────────────────
def pretrain_with(mode: str, seed: int = 0):
    """mode: '고침후' · '고침전'(동네를 전 구간으로) · '위약'(목표를 시간축으로 섞음)."""
    orig = F.field

    def patched(div="2", stats_end=None):
        if mode == "고침전":
            # **동네 고르기만 전 구간으로 되돌린다.** 정규화 통계는 그대로
            # 학습 구간이다 --- 그래야 바뀐 것이 *표본 구성* 하나로 좁혀진다.
            codes_full, _n, _p = codes_of(None)
            from ingest.visitors import series
            ser = series(div)
            days = sorted({dd for v in ser.values() for dd in v})
            M = np.full((len(codes_full), len(days)), np.nan)
            di = {dd: i for i, dd in enumerate(days)}
            for r, cc in enumerate(codes_full):
                for dd, v in ser[cc].items():
                    M[r, di[dd]] = v
            Xf = np.log10(np.where(M > 0, M, np.nan))
            import datetime
            fit = np.array([dd <= stats_end for dd in days]) if stats_end else \
                np.array([True] * len(days))
            Xf = Xf - np.nanmean(Xf[:, fit], axis=1, keepdims=True)
            dow = np.array([datetime.date(int(dd[:4]), int(dd[4:6]),
                                          int(dd[6:8])).weekday() for dd in days])
            for w in range(7):
                m = dow == w
                Xf[:, m] -= np.nanmean(Xf[:, m & fit], axis=1, keepdims=True)
            Xf = Xf - np.nanmean(Xf, axis=0, keepdims=True)
            return codes_full, days, Xf
        c, d, X = orig(div, stats_end=stats_end)
        if mode == "위약":
            # **목표를 동네 안에서 시간축으로 섞는다** --- 관측 무늬는 그대로
            rng = np.random.default_rng(669)
            Y = X.copy()
            for i in range(Y.shape[0]):
                ok = np.flatnonzero(np.isfinite(Y[i]))
                if len(ok) > 2:
                    Y[i, ok] = Y[i, rng.permutation(ok)]
            return c, d, Y
        return c, d, X

    F.field = patched
    try:
        r = F.pretrain(seed=seed)
    finally:
        F.field = orig
    if "이력" in r:
        r["**최종 검증 R2**"] = r["이력"][-1]["검증 R2(지속성 대비)"]
        r.pop("이력", None)
    r.pop("해석", None)
    return r


for mode in ("고침후", "고침전", "위약"):
    print(json.dumps({f"③ {mode}": pretrain_with(mode)}, ensure_ascii=False,
                     indent=1), flush=True)
