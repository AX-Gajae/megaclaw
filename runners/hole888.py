# -*- coding: utf-8 -*-
"""노트 888 을 — 아이돌 주입 구멍 수리의 **배선 검사**(적합 안 돌림).

갑: 수리 전/후 `FF.shell(FF.base())` 를 **비트 대조**한다. 같으면 판은 정의상 같다.
을: 합성 아이돌 열을 `extra` 로 넣어 수리 전 중립(0.5/0) → 수리 후 실값을 확인한다.
"""
import hashlib
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")
import ff753 as FF  # noqa: E402
from lab import idolset  # noqa: E402

DOM = idolset.DOM


def digest(d):
    """전 도메인 (A, M, y, t) + 이름의 sha256. 부동소수는 바이트 그대로 본다."""
    h = hashlib.sha256()
    for k in sorted(d.dom):
        A, M, y, t = d.dom[k]
        for arr in (A, M, y, t):
            a = np.ascontiguousarray(np.asarray(arr, float))
            h.update(str(a.shape).encode())
            h.update(a.tobytes())
        h.update(("|".join(map(str, d.names[k]))).encode())
    return h.hexdigest()[:16]


def per_dom(d):
    return {k: (d.dom[k][0].shape, len(d.names[k])) for k in sorted(d.dom)}


def main():
    base = FF.base()
    d0 = FF.shell(base)

    # 을 — 합성 아이돌 열. 이름은 base 에 없는 것으로 둔다.
    n = d0.dom[DOM][0].shape[0]
    rng = np.random.default_rng(888)
    v = rng.random(n)
    m = np.ones(n)
    probe = {**base, "probe888": {DOM: (v, m)}}
    d1 = FF.shell(probe)
    j = list(d1.names[DOM]).index("probe888")
    col, msk = d1.dom[DOM][0][:, j], d1.dom[DOM][1][:, j]
    reaches = bool(np.allclose(col, v) and np.allclose(msk, m))
    neutral = bool(np.allclose(col, 0.5) and np.allclose(msk, 0.0))

    # 팝업은 같은 주입이 닿는가 — 비대칭의 대조군
    PRIMARY = "팝업"
    vp = rng.random(d0.dom[PRIMARY][0].shape[0])
    mp = np.ones(len(vp))
    d2 = FF.shell({**base, "probe888p": {PRIMARY: (vp, mp)}})
    jp = list(d2.names[PRIMARY]).index("probe888p")
    pop_reaches = bool(np.allclose(d2.dom[PRIMARY][0][:, jp], vp))

    out = {
        "판_해시": digest(d0),
        "도메인_모양": {k: list(v) for k, v in per_dom(d0).items()},
        "을_아이돌_주입": {"닿는다": reaches, "중립화됐다": neutral,
                    "열_인덱스": int(j), "행": int(n)},
        "대조_팝업_주입": {"닿는다": pop_reaches},
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    main()
