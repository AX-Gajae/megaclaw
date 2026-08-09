# -*- coding: utf-8 -*-
"""노트 887 — **자를 처음 제대로 잰다**: 열 채택의 짝 군집 부트스트랩(837 미결 ① 이행).

사전등록: 대장 `**사전등록** 887 …`.

무엇이 새로운가. 규약 47 은 **모델 짝 비교**에서 상수 자(0.262/√n)를 금지하고
군집 부트 구간으로 바꿨는데, **열 채택 경로는 아직 상수 0.0045 를 쓴다**. 그 상수는
유보 3,369행·11도메인 시대 값이고 분모만 3,775 로 갈아끼워져 있었다(886). 여기서
`lab/pairboot` 를 **열 채택에 처음** 적용한다 --- 재적합 없이 유보 행을 군집 단위로
재표집해 **짝 Δ** 의 분포를 낸다.

갑(도달 가능성 산술)은 사전등록에서 이미 끝났다 --- 판 ρ 는 유보 가중 평균이라
아이돌 열이 판 문턱을 넘으려면 도메인 Δ ≥ 0.3331 이 필요하다(역대 최대 1열 효과의
5.8배). 그래서 **판정은 도메인 수준**에서 하고 판 Δ 는 병기만 한다.
"""
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")
import ff753 as FF  # noqa: E402
from lab import guards as G, idolset, pairboot as PB  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

ROOT = Path("/Users/ax/world_model")
CLS = REGISTRY["F18_bagboost"]["cls"]
T = 2025.0
DOM = "아이돌"
SEEDS = (0, 1, 2)
PLACEBO = (8870, 8871, 8872, 8873, 8874, 8875)
B = 10_000
OLD_THRESH = 0.0045


def rho(p, y):
    ok = np.isfinite(p) & np.isfinite(y)
    return float(spearmanr(p[ok], y[ok])[0]) if ok.sum() >= 20 else float("nan")


def train_pct(vals, is_train):
    """**학습 구간 ECDF** 로 백분위를 매긴다(전이 누출 차단 · 885 ⑤ 교훈).

    `rawaxes._num` 은 전 행 rankdata 라 유보를 본다. 여기서는 학습에서 만든
    분포에 유보를 **끼워 넣는다**.
    """
    v = np.array([x if isinstance(x, (int, float)) and not isinstance(x, bool)
                  else np.nan for x in vals], float)
    ok = np.isfinite(v)
    tr = ok & is_train
    if tr.sum() < 30 or len(np.unique(v[tr])) < 3:
        return None
    ref = np.sort(v[tr])
    out = np.full(len(v), 0.5, np.float32)
    out[ok] = np.searchsorted(ref, v[ok], side="left") / max(len(ref) - 1, 1)
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    return out, ok.astype(np.float32)


def main():
    t0 = time.time()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    w = d0.weights(T)
    tot = sum(w.values())

    # ── 배선 검사(노트 359: `_idol` 조용한 중립화) ────────────────
    rows = idolset._rows(wide_post=True)
    n_board = len(d0.dom[DOM][2])
    assert len(rows) == n_board, f"행 {len(rows)} ≠ 판 {n_board}"
    am = json.load(open(ROOT / "data/state/idol_album_meta.json"))
    ids = [r.get("record_id") for r in rows]
    yrs = np.array([float(str(r["debut_date"])[:4]) for r in rows])
    is_tr = yrs < T
    yrs_dat = np.asarray(d0.yr[DOM], float)
    assert np.allclose(np.floor(yrs_dat), yrs), "행↔레코드 연도 대조 실패"

    cand = {}
    for f in ("versions", "unit_price"):
        raw = [am.get(i, {}).get(f) for i in ids]
        built = train_pct(raw, is_tr)
        assert built is not None, f"{f} 코딩 실패"
        v, m = built
        cand[f] = (v, m, raw)
        print(f"배선 {f}: 마스크 합 {int(m.sum())}/{len(m)} · 값 가짓수 {len(np.unique(v[m > 0]))} "
              f"· 유보 마스크 {int(m[~is_tr].sum())}/{int((~is_tr).sum())}", flush=True)
        assert m.sum() > 0 and len(np.unique(v[m > 0])) > 1, "조용한 중립화 — 노트 359"

    def extra_of(v, m, name):
        return {name: {dd: ((v, m) if dd == DOM else
                            (np.full(len(d0.dom[dd][2]), 0.5, np.float32),
                             np.zeros(len(d0.dom[dd][2]), np.float32))) for dd in doms}}

    # ── 팔별 유보 예측 수집(재적합은 여기서만) ─────────────────────
    post = {dd: (np.isfinite(np.asarray(d0.yr[dd], float))
                 & (np.asarray(d0.yr[dd], float) >= T)) for dd in doms}
    yho = {dd: np.asarray(d0.dom[dd][2], float)[post[dd]] for dd in doms}

    def run(data, seeds, tag):
        per = {dd: [] for dd in doms}
        for s in seeds:
            f = G._fit_on(lambda s=s: CLS(seed=s), data, T, seed=s)
            for dd in doms:
                A, M, y, t = data.slice(dd, post[dd])
                try:
                    p = np.asarray(f.predict(dd, A, M, t), float)
                except Exception:
                    p = np.full(int(post[dd].sum()), np.nan)
                per[dd].append(p)
            print(f"  {tag} 씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)
        return {dd: PB.rank_ensemble(per[dd]) if len(per[dd]) > 1 else per[dd][0]
                for dd in doms}

    arms = {}
    arms["① 없이"] = run(d0, SEEDS, "없이")
    for f in ("versions", "unit_price"):
        v, m, _ = cand[f]
        arms[f"② {f}"] = run(FF.shell({**FF.base(), **extra_of(v, m, f"idol_{f}")}),
                             SEEDS, f)
    rs = np.random.default_rng(887)
    v0, m0, _ = cand["versions"]
    for i, ps in enumerate(PLACEBO):
        r2 = np.random.default_rng(ps)
        idx = np.where(m0 > 0)[0]
        vsh = v0.copy()
        vsh[idx] = v0[idx][r2.permutation(len(idx))]      # 값만 섞고 무늬 보존(335)
        arms[f"③ 위약{i+1}"] = run(FF.shell({**FF.base(), **extra_of(vsh, m0, "idol_pl")}),
                                 (0,), f"위약{i+1}")

    # ── 짝 군집 부트스트랩 ───────────────────────────────────────
    # 아이돌은 그룹명 프랜차이즈 군집 · 나머지는 단독(병기 의무)
    grp = [r.get("group_name") for r in rows]
    cl_idol, wire_idol = PB.clusters_of([grp[k] for k in np.where(post[DOM])[0]])
    cl_other = {dd: PB.clusters_of(None, n=int(post[dd].sum()))[0]
                for dd in doms if dd != DOM}
    cl = {DOM: cl_idol, **cl_other}

    def board_of(pick, armp):
        num = den = 0.0
        for dd in doms:
            r = rho(armp[dd][pick[dd]], yho[dd][pick[dd]])
            if np.isfinite(r):
                num += r * w[dd]
                den += w[dd]
        return num / den if den else float("nan")

    rng = np.random.default_rng(8877)
    base = arms["① 없이"]
    out_arms = {}
    for name, ap in arms.items():
        if name == "① 없이":
            continue
        dom_pt = rho(ap[DOM], yho[DOM]) - rho(base[DOM], yho[DOM])
        brd_pt = board_of({dd: np.arange(int(post[dd].sum())) for dd in doms}, ap) - \
            board_of({dd: np.arange(int(post[dd].sum())) for dd in doms}, base)
        bs_d, bs_b = np.empty(B), np.empty(B)
        for b in range(B):
            pick = {}
            for dd in doms:
                cc = cl[dd]
                sel = rng.integers(0, len(cc), len(cc))
                pick[dd] = np.concatenate([cc[i] for i in sel])
            bs_d[b] = (rho(ap[DOM][pick[DOM]], yho[DOM][pick[DOM]])
                       - rho(base[DOM][pick[DOM]], yho[DOM][pick[DOM]]))
            bs_b[b] = board_of(pick, ap) - board_of(pick, base)
        def ci(a, pt):
            a = a[np.isfinite(a)]
            return {"점추정": round(pt, 4), "SD": round(float(a.std(ddof=1)), 5),
                    "2σ": round(2 * float(a.std(ddof=1)), 4),
                    "lo(2.5%)": round(float(np.percentile(a, 2.5)), 4),
                    "hi(97.5%)": round(float(np.percentile(a, 97.5)), 4),
                    "유실": B - len(a)}
        cd, cb = ci(bs_d, dom_pt), ci(bs_b, brd_pt)
        out_arms[name] = {
            "도메인 Δ": cd, "판 Δ": cb,
            "규약 47 판정(도메인)": PB.verdict(cd["lo(2.5%)"], cd["hi(97.5%)"]),
            "규약 47 판정(판 · 병기만)": PB.verdict(cb["lo(2.5%)"], cb["hi(97.5%)"])}
        print(f"{name}: 도메인 Δ {cd['점추정']:+.4f} [{cd['lo(2.5%)']:+.4f},{cd['hi(97.5%)']:+.4f}] "
              f"{out_arms[name]['규약 47 판정(도메인)']} · 판 Δ {cb['점추정']:+.5f}", flush=True)

    idn = {dd: np.arange(int(post[dd].sum())) for dd in doms}
    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "배선": {"판 아이돌 행": n_board, "유보": int(post[DOM].sum()),
               "versions 마스크": int(cand["versions"][1].sum()),
               "unit_price 마스크": int(cand["unit_price"][1].sum()),
               "🔴 인구조사가 적은 채움": 0.4314,
               "🔴 실측 채움": round(float(cand["versions"][1].mean()), 4),
               "배율": round(float(cand["versions"][1].mean()) / 0.4314, 3),
               "군집(아이돌)": wire_idol,
               "⚠ 나머지 11도메인": "단독 클러스터(제목 원천 미배선) — 행 부트와 동일 · **폭 과소 방향**(규약 47 병기 의무)"},
        "기준선": {"판(없이)": round(board_of(idn, base), 4),
                "아이돌(없이)": round(rho(base[DOM], yho[DOM]), 4),
                "아이돌 가중": round(w[DOM] / tot, 4)},
        "자(837 미결 ① — 여기서 처음 잰다)": {
            "옛 상수 문턱": OLD_THRESH,
            "판 Δ 부트 2σ(위약 평균)": None, "도메인 Δ 부트 2σ(위약 평균)": None,
            "요구 도메인 Δ(= 옛 문턱/가중)": round(OLD_THRESH / (w[DOM] / tot), 4)},
        "팔": out_arms,
        "초": round(time.time() - t0, 1),
    }
    pl = [v for k, v in out_arms.items() if k.startswith("③")]
    out["자(837 미결 ① — 여기서 처음 잰다)"]["판 Δ 부트 2σ(위약 평균)"] = round(
        float(np.mean([x["판 Δ"]["2σ"] for x in pl])), 4)
    out["자(837 미결 ① — 여기서 처음 잰다)"]["도메인 Δ 부트 2σ(위약 평균)"] = round(
        float(np.mean([x["도메인 Δ"]["2σ"] for x in pl])), 4)
    out["자(837 미결 ① — 여기서 처음 잰다)"]["위약 보정(CI 가 0 을 무는가)"] = {
        k: v["규약 47 판정(도메인)"] for k, v in out_arms.items() if k.startswith("③")}
    with open(ROOT / "runners/out887_ruler.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "팔"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
