# -*- coding: utf-8 -*-
# 노트 871 P1 — era manifest 정본 동결 + comparator 검증 + 릿지 산출물(869 무보존 정오)
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

ROOT = Path("/Users/ax/world_model")


def main():
    t0 = time.time()
    import ff753 as FF
    from lab.eracheck import fingerprint, compare
    from lab import pairs as PR

    data = FF.shell(FF.base())
    fp = fingerprint(data)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    canon = {"시대": "837+kobis(영화 12도메인)", "git HEAD": head,
             "동결(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "필자": "runners/eramanifest871.py(시대 교체 시 새 러너로 재동결 — 덮어쓰기 금지)",
             "지문": fp}
    with open(ROOT / "data/lab/era_manifest.json", "x") as fh:
        json.dump(canon, fh, ensure_ascii=False, indent=1)
    ok, bad = compare(data)                              # 방금 동결 → 일치 자명(배선 검증)
    # 독립 재빌드 대조(진짜 시험 — 캐시 아닌 새 빌드)
    data2 = FF.shell(FF.base())
    ok2, bad2 = compare(data2)
    print(f"comparator: 동일 객체 {ok} · 재빌드 {ok2} {bad2}", flush=True)

    # ── 릿지 산출물 동결(869 인라인 실행의 무보존 정오) ───────────
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import KFold

    def rho(p, yy):
        okm = np.isfinite(p) & np.isfinite(yy)
        return float(spearmanr(p[okm], yy[okm])[0])

    src = PR.SRC_DOM["KR 만화"]
    names = list(data.names.get(src) or [])
    recs = PR.build("KR 만화")
    A, M, y, t = PR.to_arrays(recs, names)
    X = np.nan_to_num(np.hstack([A, M, np.asarray(t, float)[:, None]]), nan=0.5)
    fin = np.isfinite(y)
    years = np.array([int(str((r.get("start_date") or "0000"))[:4] or 0) for r in recs.values()])
    ev = np.flatnonzero(fin & (years >= 2025))
    pool = np.flatnonzero(fin & (years < 2025) & (years > 0))
    best_a, best_s = None, -9
    for a in (0.1, 1.0, 10.0, 100.0, 1000.0):
        ss = []
        for tr, te in KFold(5, shuffle=True, random_state=0).split(pool):
            m = Ridge(alpha=a).fit(X[pool[tr]], y[pool[tr]])
            ss.append(rho(m.predict(X[pool[te]]), y[pool[te]]))
        s = float(np.mean(ss))
        if s > best_s:
            best_a, best_s = a, s
    m = Ridge(alpha=best_a).fit(X[pool], y[pool])
    r = rho(m.predict(X[ev]), y[ev])
    ridge = {"α": best_a, "평가 ρ": round(r, 4), "833 기록": 0.3393, "names": len(names),
             "평가": int(len(ev)), "학습": int(len(pool)),
             "판정": ("정오 완료 — 재현" if abs(r - 0.3393) <= 0.0005 else f"구현 의심 — |Δ| {abs(r-0.3393):.4f}")}
    out = {"comparator": {"동일 객체": ok, "재빌드": ok2, "불일치": bad2},
           "릿지": ridge, "manifest 도메인": len(fp), "초": round(time.time() - t0, 1)}
    with open(ROOT / "runners/out871_ridge.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
