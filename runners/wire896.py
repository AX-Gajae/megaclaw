# -*- coding: utf-8 -*-
"""노트 896 배선 검사 — **주입한 열이 정말 모형에 닿았나**(도메인별).

🔴 887 이 여기서 죽었다: 12도메인 중 아이돌만 축 주입이 **조용히 중립화**됐고
그것을 판정 뒤에 알았다. `dose896.stageB` 의 배선 칸은 **주입 전** 배열만 본다 ---
이 파일은 **주입 뒤의 `Data`** 를 열어 `names` 에 축이 실렸는지, `_feat` 가 값·표시자
두 열을 낼 자리에 관측이 있는지를 도메인마다 센다.

**별도 파일인 이유**: `dose896.py` 를 고치면 이미 나온 `out896_armA/armB.json` 에
박힌 코드 sha256 이 그 파일과 안 맞게 된다(티처 #58 M6 의 반대 방향 사고).
동결물은 안 건드린다.

산출물 `runners/out896_wiring.json`.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import hashlib                                                  # noqa: E402
import json                                                     # noqa: E402
import sys                                                      # noqa: E402
from pathlib import Path                                        # noqa: E402

import numpy as np                                              # noqa: E402

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import ff753 as FF                                              # noqa: E402
from dose896 import T, _pct_axis, coverage, doses, stamp        # noqa: E402

ROOT = Path("/Users/ax/world_model")
AX = "dose896"


def main():
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    post = {k: (np.isfinite(np.asarray(d0.yr[k], float))
                & (np.asarray(d0.yr[k], float) >= T)) for k in doms}
    dz = doses(d0)
    cov = {nm: coverage(d0, v, post) for nm, v in dz.items()}
    out = {"무엇": "주입 뒤 Data 를 열어 축이 정말 닿았는지 도메인마다 센다(887 재발 감시)",
           "축 이름": AX}
    for nm, ax in dz.items():
        keep = {k for k in doms if cov[nm][k]["채택"]}
        real = _pct_axis(ax, post, keep=keep)
        d1 = FF.shell({**FF.base(),
                       AX: {k: (np.asarray(v, np.float32), np.asarray(m, np.float32))
                            for k, (v, m) in real.items()}})
        rep = {}
        for k in doms:
            nm1 = list(d1.names.get(k) or [])
            nm0 = list(d0.names.get(k) or [])
            j = nm1.index(AX) if AX in nm1 else None
            A, M = d1.dom[k][0], d1.dom[k][1]
            te = post[k]
            obs = int((M[:, j][te] > 0).sum()) if j is not None else 0
            uq = int(len(np.unique(A[:, j][M[:, j] > 0]))) if j is not None else 0
            rep[k] = {"names 에 실렸나": j is not None,
                      "열 폭 증가": len(nm1) - len(nm0),
                      "유보 관측": obs, "유보 행": int(te.sum()),
                      "관측분 값 가짓수": uq,
                      "등록된 배제(사전등록 ⓓ)": k not in keep,
                      "🔴 채택인데 안 닿음(887 형)":
                          bool(k in keep and (j is None or obs == 0 or uq < 2))}
        h = hashlib.sha256()
        for k in sorted(real):
            h.update(np.ascontiguousarray(np.asarray(real[k][0], np.float32)).tobytes())
        rep["주입 열 값 sha256"] = h.hexdigest()[:16]
        rep["🔴 887 형 중립화 도메인"] = [k for k in doms
                                  if rep[k]["🔴 채택인데 안 닿음(887 형)"]]
        rep["채택 도메인"] = sorted(keep)
        out[nm] = rep
    out.update(stamp())
    (ROOT / "runners/out896_wiring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    for nm in dz:
        print(nm, "중립화", out[nm]["🔴 887 형 중립화 도메인"],
              "· 채택", out[nm]["채택 도메인"], flush=True)


if __name__ == "__main__":
    main()
