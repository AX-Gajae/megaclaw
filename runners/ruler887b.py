# -*- coding: utf-8 -*-
"""노트 887 정 — **배선을 고쳐 다시 잰다**. ruler887(초판)은 **무효**다.

무엇이 틀렸나. `FF.shell(extra)` 로 아이돌에 열을 주입할 수 없다.
`lab/loop.py:640-651` 이 아이돌 열을 붙일 때 보는 것은 **달력·위키·트렌드
제공자뿐**이고, 이름이 거기 없으면 조용히 `0.5 · 마스크 0` 으로 떨어진다:

    v = calv.get(c) or wikv.get(c) or trnv.get(c)
    if v is not None: ...
    else: vv, oo = np.full(len(A), 0.5), np.zeros(len(A))   # ← 조용한 중립화

팝업(605-613)은 `byd.get(PRIMARY)` 로 extra 를 읽는데 **아이돌은 안 읽는다.**
그래서 초판의 팔 여덟이 전부 같은 예측을 냈다(후보 Δ 정확히 0.0000 · 위약 여섯이
전부 −0.0467 로 동일 — 그 −0.0467 은 열 효과가 아니라 **씨앗 수 차이**(1 대 3)다).

**내 배선 검사가 왜 못 잡았나.** 노트 359 를 인용하면서 **입력 배열**만 확인했다
(마스크 합 149/173 · 값 가짓수 9). 확인해야 했던 것은 **행렬**이다. 이번 판은
주입 후 `A[:, j]` 와 `M[:, j]` 를 원본과 대조한다.

고침: 885 `kill_vp` 선례대로 **shell 이 돌려준 뒤 행렬에 직접 붙인다.**
그리고 위약도 후보와 **같은 씨앗 셋**을 쓴다(초판은 위약만 1씨앗이라 비교 불가였다).
"""
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

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
    """학습 구간 ECDF 백분위(전이 누출 차단 · 885 ⑤ 교훈)."""
    v = np.array([x if isinstance(x, (int, float)) and not isinstance(x, bool)
                  else np.nan for x in vals], float)
    ok = np.isfinite(v)
    tr = ok & is_train
    if tr.sum() < 30 or len(np.unique(v[tr])) < 3:
        return None
    ref = np.sort(v[tr])
    out = np.full(len(v), 0.5, np.float32)
    out[ok] = np.searchsorted(ref, v[ok], side="left") / max(len(ref) - 1, 1)
    return np.clip(out, 0.0, 1.0).astype(np.float32), ok.astype(np.float32)


def inject(name, v, m):
    """shell 이 돌려준 **행렬에 직접** 붙인다(885 `kill_vp` 선례).

    그리고 **행렬 쪽을 검사한다** --- 초판이 입력만 보고 놓친 자리다.
    """
    d = FF.shell(FF.base())
    A, M, y, t = d.dom[DOM]
    assert len(v) == A.shape[0], f"길이 {len(v)} ≠ 행렬 {A.shape[0]}"
    A2 = np.hstack([np.asarray(A, float), np.asarray(v, float).reshape(-1, 1)])
    M2 = np.hstack([np.asarray(M, float), np.asarray(m, float).reshape(-1, 1)])
    d.dom[DOM] = (A2, M2, y, t)
    d.names[DOM] = list(d.names[DOM]) + [name]
    j = d.names[DOM].index(name)
    assert np.allclose(d.dom[DOM][0][:, j], v), "🔴 값이 행렬에 안 들어갔다(노트 359)"
    assert np.allclose(d.dom[DOM][1][:, j], m), "🔴 마스크가 행렬에 안 들어갔다"
    assert d.dom[DOM][0].shape[1] == len(d.names[DOM]), "열 수 ≠ 이름 수"
    return d


def main():
    t0 = time.time()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    w = d0.weights(T)
    tot = sum(w.values())

    rows = idolset._rows(wide_post=True)
    n_board = len(d0.dom[DOM][2])
    assert len(rows) == n_board, f"행 {len(rows)} ≠ 판 {n_board}"
    am = json.load(open(ROOT / "data/state/idol_album_meta.json"))
    ids = [r.get("record_id") for r in rows]
    yrs = np.array([float(str(r["debut_date"])[:4]) for r in rows])
    is_tr = yrs < T
    assert np.allclose(np.floor(np.asarray(d0.yr[DOM], float)), yrs), "행↔레코드 연도 대조 실패"

    cand = {}
    for f in ("versions", "unit_price"):
        v, m = train_pct([am.get(i, {}).get(f) for i in ids], is_tr)
        cand[f] = (v, m)

    # 🔴 초판이 못 잡은 자리 --- 행렬 검사로 배선을 증명한다
    wire = {}
    for f in ("versions", "unit_price"):
        v, m = cand[f]
        d = inject(f"idol_{f}", v, m)
        j = d.names[DOM].index(f"idol_{f}")
        wire[f] = {"판 열 수": d.dom[DOM][0].shape[1],
                   "행렬 값 가짓수": int(len(np.unique(d.dom[DOM][0][:, j]))),
                   "행렬 마스크 합": float(d.dom[DOM][1][:, j].sum()),
                   "입력과 일치": True}
        print(f"배선(행렬) {f}: 열 {wire[f]['판 열 수']} · 값 가짓수 "
              f"{wire[f]['행렬 값 가짓수']} · 마스크 {wire[f]['행렬 마스크 합']:.0f}", flush=True)
    # 대조군: 초판 경로(shell extra)가 정말 중립화되는가 --- 무효 증명을 코드로 남긴다
    vv, mm = cand["versions"]
    d_old = FF.shell({**FF.base(), "idol_versions": {
        dd: ((vv, mm) if dd == DOM else
             (np.full(len(d0.dom[dd][2]), 0.5, np.float32),
              np.zeros(len(d0.dom[dd][2]), np.float32))) for dd in doms}})
    jo = list(d_old.names[DOM]).index("idol_versions")
    neutralized = bool(d_old.dom[DOM][1][:, jo].sum() == 0)
    print(f"🔴 초판 경로(shell extra) 중립화 확인: 마스크 합 "
          f"{d_old.dom[DOM][1][:, jo].sum():.0f} · 중립화={neutralized}", flush=True)

    post = {dd: (np.isfinite(np.asarray(d0.yr[dd], float))
                 & (np.asarray(d0.yr[dd], float) >= T)) for dd in doms}
    yho = {dd: np.asarray(d0.dom[dd][2], float)[post[dd]] for dd in doms}

    def run(data, tag):
        per = {dd: [] for dd in doms}
        for s in SEEDS:
            fit = G._fit_on(lambda s=s: CLS(seed=s), data, T, seed=s)
            for dd in doms:
                A, M, y, t = data.slice(dd, post[dd])
                try:
                    p = np.asarray(fit.predict(dd, A, M, t), float)
                except Exception:
                    p = np.full(int(post[dd].sum()), np.nan)
                per[dd].append(p)
            print(f"  {tag} 씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)
        return {dd: PB.rank_ensemble(per[dd]) for dd in doms}

    arms = {"① 없이": run(d0, "없이")}
    for f in ("versions", "unit_price"):
        v, m = cand[f]
        arms[f"② {f}"] = run(inject(f"idol_{f}", v, m), f)
    v0, m0 = cand["versions"]
    idx = np.where(m0 > 0)[0]
    for i, ps in enumerate(PLACEBO):
        r2 = np.random.default_rng(ps)
        vsh = v0.copy()
        vsh[idx] = v0[idx][r2.permutation(len(idx))]      # 값만 섞고 무늬 보존(335)
        arms[f"③ 위약{i+1}"] = run(inject("idol_pl", vsh, m0), f"위약{i+1}")

    grp = [rows[k].get("group_name") for k in np.where(post[DOM])[0]]
    cl_idol, wire_idol = PB.clusters_of(grp)
    cl = {DOM: cl_idol,
          **{dd: PB.clusters_of(None, n=int(post[dd].sum()))[0] for dd in doms if dd != DOM}}

    def board_of(pick, ap):
        num = den = 0.0
        for dd in doms:
            r = rho(ap[dd][pick[dd]], yho[dd][pick[dd]])
            if np.isfinite(r):
                num += r * w[dd]
                den += w[dd]
        return num / den if den else float("nan")

    idn = {dd: np.arange(int(post[dd].sum())) for dd in doms}
    rng = np.random.default_rng(8877)
    base = arms["① 없이"]
    b0 = board_of(idn, base)
    out_arms = {}
    for name, ap in arms.items():
        if name == "① 없이":
            continue
        dom_pt = rho(ap[DOM], yho[DOM]) - rho(base[DOM], yho[DOM])
        brd_pt = board_of(idn, ap) - b0
        bs_d, bs_b = np.empty(B), np.empty(B)
        for b in range(B):
            pick = {}
            for dd in doms:
                cc = cl[dd]
                pick[dd] = np.concatenate([cc[i] for i in rng.integers(0, len(cc), len(cc))])
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
        out_arms[name] = {"도메인 Δ": cd, "판 Δ": cb,
                          "규약 47 판정(도메인)": PB.verdict(cd["lo(2.5%)"], cd["hi(97.5%)"]),
                          "규약 47 판정(판 · 병기만)": PB.verdict(cb["lo(2.5%)"], cb["hi(97.5%)"])}
        print(f"{name}: 도메인 Δ {cd['점추정']:+.4f} [{cd['lo(2.5%)']:+.4f},{cd['hi(97.5%)']:+.4f}] "
              f"{out_arms[name]['규약 47 판정(도메인)']} · 판 Δ {cb['점추정']:+.5f}", flush=True)

    pl = [v for k, v in out_arms.items() if k.startswith("③")]
    pl_dom = [v["도메인 Δ"]["점추정"] for v in pl]
    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "🔴 초판 무효 사유": {
            "무엇": "`FF.shell(extra)` 로는 아이돌에 열을 주입할 수 없다(lab/loop.py:640-651 — 달력·위키·트렌드 제공자만 본다)",
            "증거": f"초판 경로로 주입하면 마스크 합 {d_old.dom[DOM][1][:, jo].sum():.0f} (중립화={neutralized})",
            "초판 증상": "후보 Δ 정확히 0.0000(CI 폭 0) · 위약 여섯이 전부 −0.0467 로 동일(씨앗 수 1 대 3 의 인공물)",
            "왜 내 배선 검사가 못 잡았나": "노트 359 를 인용하면서 **입력 배열**만 봤다. 봐야 했던 것은 **행렬**이다",
            "이번 고침": "shell 이 돌려준 뒤 행렬에 직접 붙이고(885 kill_vp 선례) A[:,j]·M[:,j] 를 원본과 대조",
            "초판 산출물": "runners/out887_ruler.json — **무효로 보존**(wfail 보존 관례)"},
        "배선(행렬 검사)": {**wire, "군집(아이돌)": wire_idol,
                     "⚠ 나머지 11도메인": "단독 클러스터 — 행 부트와 동일 · **폭 과소 방향**(규약 47 병기 의무)"},
        "기준선": {"판(없이)": round(b0, 4), "아이돌(없이)": round(rho(base[DOM], yho[DOM]), 4),
                "아이돌 가중": round(w[DOM] / tot, 4)},
        "자(837 미결 ① — 여기서 처음 잰다)": {
            "옛 상수 문턱": OLD_THRESH,
            "요구 도메인 Δ(= 옛 문턱/가중)": round(OLD_THRESH / (w[DOM] / tot), 4),
            "위약 도메인 Δ 점추정 여섯": pl_dom,
            "위약 도메인 Δ 뽑기 SD": round(float(np.std(pl_dom, ddof=1)), 5),
            "위약 판 Δ 부트 2σ(평균)": round(float(np.mean([v["판 Δ"]["2σ"] for v in pl])), 4),
            "위약 도메인 Δ 부트 2σ(평균)": round(float(np.mean([v["도메인 Δ"]["2σ"] for v in pl])), 4),
            "위약 보정(CI 가 0 을 무는가)": {k: v["규약 47 판정(도메인)"]
                                    for k, v in out_arms.items() if k.startswith("③")}},
        "팔": out_arms,
        "초": round(time.time() - t0, 1),
    }
    with open(ROOT / "runners/out887b_ruler.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "팔"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
