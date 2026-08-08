# -*- coding: utf-8 -*-
# 노트 885 — 영화 `국적` 재현·분해(사전등록 '885' · 티처 #49 설계)
# 갑: 분모 837 정본(3,775) → 영화 2σ 0.0137 · 영화 씨앗 SD 첫 측정
# 을: 팔 7 — 없이3 · 진짜3 · 값셔플6 · 행셔플3 · 학습만_cat 3 · 원핫1 · vp제거2
# 병: 세 기준선 병기 · 국적별 표 · 파싱 쓰레기 정정 전/후
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")
import ff753 as FF  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402
from lab.harness import evaluate  # noqa: E402

ROOT = Path("/Users/ax/world_model")
CLS = REGISTRY["F18_bagboost"]["cls"]
T = 2025.0
DOM = "영화"
SEEDS3 = (0, 1, 2)
S0 = (0,)
BASE_OK = (0.455, 0.485)
MIN_GROUP = 20
TWO_SIGMA = round(0.0045 * (3775 / 406) ** 0.5, 4)     # 837 정본 분모 — 0.0137
VAL_PLACEBO = (8850, 8851, 8852, 8853, 8854, 8855)
ROW_PLACEBO = (8860, 8861, 8862)
#: 파싱 쓰레기(티처 #49 e1) — 국적이 아니다
JUNK = {"전체관람가", "청소년관람불가", "예술영화", "드라마", "12세이상관람가", "15세이상관람가"}


def board(data, seeds):
    vals, per = [], {}
    for s in seeds:
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc, T=T)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return {"판": float(np.mean(vals)), "판 씨앗별": [round(v, 4) for v in vals],
            "도메인": {k: float(np.mean(a)) for k, a in per.items()},
            "도메인 씨앗별": {k: [round(x, 4) for x in a] for k, a in per.items()}}


def cat_axis(raw, order_pos):
    v = np.array([order_pos.get(x, 0.5) for x in raw], np.float32)
    m = np.array([1.0 if x in order_pos else 0.0 for x in raw], np.float32)
    return v, m


def main():
    t0 = time.time()
    DS = ROOT / "data/state"
    ax = json.loads((DS / "kobis_axes.json").read_text())
    ids = list(ax)
    yrs = [(ax[k].get("release_date") or "")[:4] for k in ids]
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    n_board = len(d0.dom[DOM][2])

    def build(raw, min_group=MIN_GROUP, train_only=False, onehot_col=None):
        """집단 크기 순 0~1. train_only 면 학습 구간(연도<2025)으로만 센다."""
        pool = [x for x, y in zip(raw, yrs) if (not train_only or (y and int(y) < 2025))]
        c = Counter(x for x in pool if x not in (None, ""))
        big = [u for u, n in c.items() if n >= min_group]
        if len(big) < 2:
            return None
        order = sorted(big, key=lambda u: -c[u])
        if onehot_col is not None:                       # 순서 무관: 그 범주만 1
            pos = {u: (1.0 if u == onehot_col else 0.0) for u in order}
        else:
            pos = {u: i / max(1, len(order) - 1) for i, u in enumerate(order)}
        return cat_axis(raw, pos) + (order, c)

    raw_all = [(ax[k] or {}).get("국적") for k in ids]
    raw_clean = [None if (x in JUNK) else x for x in raw_all]
    junk_n = sum(1 for x in raw_all if x in JUNK)

    def axis_for(v, m, name="film_nation", row_shuffle_seed=None, val_shuffle_seed=None):
        vv, mm = np.asarray(v, np.float32).copy(), np.asarray(m, np.float32).copy()
        if val_shuffle_seed is not None:                 # 값만 섞는다(마스크 무늬 보존)
            rng = np.random.default_rng(val_shuffle_seed)
            ii = np.flatnonzero(mm > 0)
            sh = vv[ii].copy(); rng.shuffle(sh); vv[ii] = sh
        if row_shuffle_seed is not None:                 # (v,m) 쌍째 이동 — 정렬까지 깬다
            rng = np.random.default_rng(row_shuffle_seed)
            pi = rng.permutation(len(vv))
            vv, mm = vv[pi], mm[pi]
        per = {}
        for dd in doms:
            nn = len(d0.dom[dd][2])
            per[dd] = (vv, mm) if dd == DOM else (np.full(nn, 0.5, np.float32),
                                                  np.zeros(nn, np.float32))
        return {name: per}

    got = build(raw_clean)
    if got is None or len(raw_clean) != n_board:
        raise SystemExit(f"배선 실패 — 원천 {len(raw_clean)} 대 판 {n_board}")
    v, m, order, cnt = got
    ho = [i for i, y in enumerate(yrs) if y and int(y) >= 2025]
    tr = [i for i, y in enumerate(yrs) if y and int(y) < 2025]
    tbl = [{"국적": u, "n_학습": sum(1 for i in tr if raw_clean[i] == u),
            "n_유보": sum(1 for i in ho if raw_clean[i] == u),
            "코드": round(float(v[[i for i in range(len(v)) if raw_clean[i] == u][0]]), 4)}
           for u in order]
    wire = {"원천 행": len(raw_clean), "판 행": n_board, "마스크율": round(float(m.mean()), 4),
            "실효 범주": len(order), "파싱 쓰레기 정정": junk_n, "국적별 표": tbl,
            "학습 406 대조": {"학습": len(tr), "유보": len(ho)}}
    print(json.dumps({"배선": wire}, ensure_ascii=False), flush=True)

    b0 = board(d0, SEEDS3)
    if not (BASE_OK[0] <= b0["판"] <= BASE_OK[1]):
        raise SystemExit(f"기준선 이탈 {b0['판']:.4f}")
    seed_sd = float(np.std(b0["도메인 씨앗별"][DOM], ddof=1))
    print(json.dumps({"① 없이": {"판": round(b0["판"], 4), DOM: round(b0["도메인"][DOM], 4),
                                "씨앗별": b0["도메인 씨앗별"][DOM], "씨앗 SD": round(seed_sd, 5)}},
                     ensure_ascii=False), flush=True)

    def arm(label, extra, seeds):
        s = board(FF.shell({**FF.base(), **extra}), seeds)
        print(f"  {label}: {s['도메인'][DOM]:.4f} (판 {s['판']:.4f})", flush=True)
        return s

    real = arm("② 진짜(씨앗3)", axis_for(v, m), SEEDS3)
    valp = [arm(f"③ 값셔플 {ps}", axis_for(v, m, val_shuffle_seed=ps), S0) for ps in VAL_PLACEBO]
    rowp = [arm(f"④ 행셔플 {ps}", axis_for(v, m, row_shuffle_seed=ps), S0) for ps in ROW_PLACEBO]
    g_tr = build(raw_clean, train_only=True)
    tr_arm = arm("⑤ 학습만 _cat(씨앗3)", axis_for(g_tr[0], g_tr[1]), SEEDS3) if g_tr else None
    g_oh = build(raw_clean, onehot_col=order[0])
    oh_arm = arm(f"⑥ 원핫({order[0]})", axis_for(g_oh[0], g_oh[1]), S0) if g_oh else None
    got_junk = build(raw_all)
    junk_arm = arm("⑧ 파싱 정정 전", axis_for(got_junk[0], got_junk[1]), S0) if got_junk else None

    # 🔴 배선 검사에서 잡음: venue_prominence 는 FF.base() 에 없다(5 핵심 축은 다른 경로).
    # 키를 빼는 방식은 **조용한 무작동**이었다(노트 359 부류) — 마스크 0 으로 끈다.
    def kill_vp(data):
        names = list(data.names[DOM])
        if "venue_prominence" not in names:
            return None
        j = names.index("venue_prominence")
        # 🔴 wfail(1차 크래시): dom 튜플은 4개다(A, M, y, t) — 3개로 언패킹해 터졌다.
        tup = list(data.dom[DOM])
        A, M = np.array(tup[0], copy=True), np.array(tup[1], copy=True)
        M[:, j] = 0.0
        A[:, j] = 0.5
        tup[0], tup[1] = A, M
        data.dom[DOM] = tuple(tup)
        return j
    dvp0 = FF.shell(FF.base()); j0 = kill_vp(dvp0)
    dvp1 = FF.shell({**FF.base(), **axis_for(v, m)}); j1 = kill_vp(dvp1)
    if j0 is None or j1 is None:
        vp0 = vp1 = None
        print("  ⑦ vp 팔 불가 — venue_prominence 열 없음(사전등록 (라): 뺀 사실을 산출물에)", flush=True)
    else:
        vp0 = board(dvp0, S0); vp1 = board(dvp1, S0)
        print(f"  ⑦a vp 끈 기준선(열 {j0}): {vp0['도메인'][DOM]:.4f}", flush=True)
        print(f"  ⑦b vp 끈 뒤 + 국적: {vp1['도메인'][DOM]:.4f}", flush=True)

    vmean = float(np.mean([s["도메인"][DOM] for s in valp]))
    vsd = float(np.std([s["도메인"][DOM] for s in valp], ddof=1))
    rmean = float(np.mean([s["도메인"][DOM] for s in rowp]))
    share = float(real["도메인"][DOM] - vmean)
    per_seed = [x - vmean for x in real["도메인 씨앗별"][DOM]]
    crit = {"① 씨앗3평균 ≥ max(2σ,2×뽑기SD,2×씨앗SD)":
            share >= max(TWO_SIGMA, 2 * vsd, 2 * seed_sd),
            "② 위약 6/6": bool(real["도메인"][DOM] > max(s["도메인"][DOM] for s in valp)),
            "③ 씨앗 셋 각각 > 2σ": all(x > TWO_SIGMA for x in per_seed)}
    verdict = ("(가) 재현 — 집안 통과 확정(채택은 규약 12 로 불가: 영화는 집 밖 짝 없음)"
               if all(crit.values()) else
               "(다) 해롭다" if (share < 0 and abs(share) > TWO_SIGMA) else
               "(나) 미재현 — 884 의 +0.0654 를 씨앗 요행으로 강등·서랍")

    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "학습측 재료 지문": {d: hashlib.sha256(np.ascontiguousarray(
            np.asarray(d0.dom[d][2], float)).tobytes()).hexdigest()[:12] for d in doms},
        "자": {"그 도메인 2σ(837 정본 3,775 분모)": TWO_SIGMA,
              "884 의 자(은퇴 분모 3,369)": 0.0130, "영화 씨앗 SD": round(seed_sd, 5)},
        "배선": wire,
        "세 기준선": {"없이": round(b0["도메인"][DOM], 4), "값셔플 평균": round(vmean, 4),
                  "행셔플 평균": round(rmean, 4),
                  "판정 분모": "값셔플(884 와 같은 자 — 사전 고정)"},
        "팔": {
            "① 없이(씨앗3)": {"값": round(b0["도메인"][DOM], 4), "씨앗별": b0["도메인 씨앗별"][DOM]},
            "② 진짜(씨앗3)": {"값": round(real["도메인"][DOM], 4),
                          "씨앗별": real["도메인 씨앗별"][DOM],
                          "판": round(real["판"], 4), "판 변화": round(real["판"] - b0["판"], 4)},
            "③ 값셔플 6": [round(s["도메인"][DOM], 4) for s in valp],
            "④ 행셔플 3": [round(s["도메인"][DOM], 4) for s in rowp],
            "⑤ 학습만 _cat(씨앗3)": (None if not tr_arm else
                {"값": round(tr_arm["도메인"][DOM], 4), "실효 범주": len(g_tr[2]),
                 "진짜와 차": round(tr_arm["도메인"][DOM] - real["도메인"][DOM], 4)}),
            "⑥ 원핫": (None if not oh_arm else
                {"값": round(oh_arm["도메인"][DOM], 4),
                 "순서형과 차": round(oh_arm["도메인"][DOM] - real["도메인"][DOM], 4)}),
            "⑦ vp": ({"팔 불가": "venue_prominence 열 없음 — 사전등록 (라)"} if vp0 is None else
                    {"vp 끈 기준선": round(vp0["도메인"][DOM], 4),
                     "vp 끈 뒤+국적": round(vp1["도메인"][DOM], 4),
                     "vp 없을 때 이득": round(vp1["도메인"][DOM] - vp0["도메인"][DOM], 4),
                     "vp 있을 때 이득(대조)": round(real["도메인"][DOM] - b0["도메인"][DOM], 4)}),
            "⑧ 파싱 정정 전(씨앗0)": (None if not junk_arm else
                {"값": round(junk_arm["도메인"][DOM], 4), "실효 범주": len(got_junk[2])}),
        },
        "신호 몫(값셔플 분모)": round(share, 4),
        "씨앗별 신호 몫": [round(x, 4) for x in per_seed],
        "뽑기 SD": round(vsd, 5), "2×뽑기SD": round(2 * vsd, 4), "2×씨앗SD": round(2 * seed_sd, 4),
        "재현 기준 셋": crit, "갈래": verdict, "초": round(time.time() - t0, 1),
    }
    with open(ROOT / "runners/out885_nation.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: val for k, val in out.items()
                      if k not in ("학습측 재료 지문", "배선")}, ensure_ascii=False, indent=1),
          flush=True)


if __name__ == "__main__":
    main()
