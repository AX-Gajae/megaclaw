# -*- coding: utf-8 -*-
# era 재사용 진단(노트 873 · 티처 #38 중대 1 봉합) — 동결과 분리: open('x') 없음 · 반복 실행형.
# 한 번의 빌드로 세 층을 다 본다: ① 기저 라벨(훅 정본 · era_manifest_base) ② 챔피언 전층
# (A/M/y · era_manifest) ③ NaN 정준화 diff(-nan 존재 감시). --save 로 자기서술 산출물.
# 사용: python3 runners/erascan.py [--save]
import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")


def main():
    t0 = time.time()
    import ff753 as FF
    from lab import harness as H
    from lab.eracheck import compare, compare_labels, CANON

    base = H.load()                                      # 기저 — 훅이 여기서도 발화(무음=일치)
    okb, badb = compare_labels(base, verbose=True)
    champ = FF.shell(FF.base())                          # 챔피언 구성
    okc, badc = compare(champ)

    canon = json.loads(CANON.read_text())["지문"]
    def h_canon(a):
        a = np.round(np.asarray(a, float), 6)
        a = np.where(np.isnan(a), np.nan, a)             # -nan → 정준 nan
        return hashlib.sha256(a.tobytes()).hexdigest()[:12]
    nan_diff = []
    for dom in sorted(champ.dom):
        A, M, y, _t = champ.dom[dom]
        if {"y": h_canon(y), "A": h_canon(A), "M": h_canon(M),
                "행": int(len(np.asarray(y)))} != canon.get(dom):
            nan_diff.append(dom)
    print(f"NaN 정준화 diff: {nan_diff or '없음(-nan 부재)'}", flush=True)

    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "기저 라벨": {"일치": okb, "불일치": badb},
           "챔피언 전층": {"일치": okc, "불일치": badc},
           "NaN 정준화": {"갈림": nan_diff},
           "자기서술": {"기저": "harness.load() 무 extra", "챔피언": "ff753.shell(base()) — F18 구성",
                     "해시": "sha256(round(·,6).tobytes())[:12] · 정준화 = where(isnan, nan, ·)"},
           "초": round(time.time() - t0, 1)}
    print(json.dumps({k: out[k] for k in ("기저 라벨", "챔피언 전층", "NaN 정준화", "초")},
                     ensure_ascii=False), flush=True)
    if "--save" in sys.argv:
        p = ROOT / f"runners/out_erascan_{dt.date.today()}.json"
        with open(p, "x") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        print(f"동결: {p.name}", flush=True)


if __name__ == "__main__":
    main()
