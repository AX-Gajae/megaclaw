# -*- coding: utf-8 -*-
"""노트 887 정오 — **규약 47 위반 자가 적발**: BCa 를 안 쓰고 순 percentile 을 썼다.

규약 47 문면: *"구간 BCa 95%(자코나이프 가속 · **실패/퇴화 시 percentile 폴백 명기**)"*.
`ruler887b.py:199-200` 은 `np.percentile(a, 2.5/97.5)` 를 직접 불렀고 폴백 선언도 없다.
`lab/pairboot.cluster_boot` 가 바로 그 일을 하라고 있는 함수인데 안 썼다.

여기서 **판정이 걸린 유일한 팔**(아이돌 `versions`)만 다시 잰다 — 나머지는 Δ 가
정확히 0 이라 어떤 구간 방법으로도 0 을 문다. 기준선 + versions = 씨앗 3 × 2 = 6 적합.
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
import ruler887b as R  # noqa: E402
from lab import guards as G, idolset, pairboot as PB  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

ROOT = Path("/Users/ax/world_model")
CLS = REGISTRY["F18_bagboost"]["cls"]
T = 2025.0
DOM = "아이돌"
SEEDS = (0, 1, 2)


def main():
    t0 = time.time()
    d0 = FF.shell(FF.base())
    rows = idolset._rows(wide_post=True)
    am = json.load(open(ROOT / "data/state/idol_album_meta.json"))
    ids = [r.get("record_id") for r in rows]
    yrs = np.array([float(str(r["debut_date"])[:4]) for r in rows])
    v, m = R.train_pct([am.get(i, {}).get("versions") for i in ids], yrs < T)

    post = np.isfinite(np.asarray(d0.yr[DOM], float)) & (np.asarray(d0.yr[DOM], float) >= T)
    y = np.asarray(d0.dom[DOM][2], float)[post]

    def preds(data, tag):
        ps = []
        for s in SEEDS:
            f = G._fit_on(lambda s=s: CLS(seed=s), data, T, seed=s)
            A, M, yy, t = data.slice(DOM, post)
            ps.append(np.asarray(f.predict(DOM, A, M, t), float))
            print(f"  {tag} 씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)
        return PB.rank_ensemble(ps)

    p_base = preds(d0, "없이")
    p_ver = preds(R.inject("idol_versions", v, m), "versions")

    grp = [rows[k].get("group_name") for k in np.where(post)[0]]
    clusters, wire = PB.clusters_of(grp)

    def stat(idx):
        idx = np.asarray(idx, int)
        ok = np.isfinite(y[idx])
        if ok.sum() < 8:
            return np.nan
        a, b = p_ver[idx][ok], p_base[idx][ok]
        yy = y[idx][ok]
        if len(np.unique(yy)) < 3:
            return np.nan
        return float(spearmanr(a, yy)[0] - spearmanr(b, yy)[0])

    pt, lo, hi, kind = PB.cluster_boot(stat, clusters, B=10_000, seed=887)
    old = {"lo": -0.1790, "hi": 0.2483, "점추정": 0.0278}
    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "왜": ("규약 47 자가 적발 — ruler887b 가 BCa 대신 순 percentile 을 썼고 폴백 선언도 없었다. "
              "판정이 걸린 유일한 팔(versions)만 `lab/pairboot.cluster_boot` 로 다시 잰다."),
        "군집": wire,
        "🔴 BCa(규약 47 정본)": {"점추정": round(pt, 4), "lo": round(lo, 4), "hi": round(hi, 4),
                          "종류": kind, "판정": PB.verdict(lo, hi)},
        "옛 percentile(ruler887b)": {**old, "판정": PB.verdict(old["lo"], old["hi"])},
        "판정이 바뀌었나": PB.verdict(lo, hi) != PB.verdict(old["lo"], old["hi"]),
        "초": round(time.time() - t0, 1),
    }
    with open(ROOT / "runners/out887c_bca.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
