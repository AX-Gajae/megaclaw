"""노트 796 — **노트 586 채택을 되돌리면 노트 577 의 세 값이 나오나.**

노트 794 가 출처 추적으로 원인을 찾았다: `pairs.BASELINE` 이 KR·앱은 노트 586
채택 **후**, CN 은 노트 577 채택 **전** 에서 왔다. **그것은 문서 증거다.**
여기서 측정 증거를 만든다.

되돌릴 것 둘(커밋 `bc0b19860` 이 넣은 것):
  ① `lab/forms.py`  `OOC_DROP = ()`  →  `("entry_friction",)`
  ② `lab/loop.py`   `fixaxes.orient` 두 자리  →  없음

🔴 **파일을 안 고친다.** `OOC_DROP` 은 클래스 속성이고 `orient` 는 늦은 임포트라
둘 다 메모리에서 되돌릴 수 있다. 진단이지 챔피언 변경이 아니다.

**못박은 셋(결과 보기 전)**: KR 0.6374 · 앱 0.2897 · CN 0.3094, 각각 ±0.02.
"""
import json
import sys
import time

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/"
                   "ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")

SEEDS = tuple(range(12))
T = 2025.0
#: 노트 577 의 전이값. **결과 보기 전에 못박았다.**
TARGET = {"KR 만화": 0.6374, "비게임 앱": 0.2897, "CN 만화": 0.3094}
TOL = 0.02
#: 노트 793 이 잰 지금 값 --- 대조군
NOW = {"KR 만화": 0.6850, "비게임 앱": 0.4916, "CN 만화": 0.3872}


def measure(tag: str, revert: bool) -> dict:
    """짝 셋을 씨앗 열둘로 잰다. `revert` 면 노트 586 이전으로 되돌린다."""
    import importlib
    from lab import fixaxes, forms, guards as G, pairs as PR

    cls = forms.REGISTRY["F18_bagboost"]["cls"]
    old_drop = cls.OOC_DROP
    old_orient = fixaxes.orient
    if revert:
        cls.OOC_DROP = ("entry_friction",)          # ① 되돌림
        fixaxes.orient = lambda data: data          # ② 되돌림(늦은 임포트라 먹는다)
    try:
        #: 판 Data 를 **이 팔 안에서** 새로 만든다 --- orient 가 Data 를 바꾼다
        for m in ("ff753",):
            if m in sys.modules:
                importlib.reload(sys.modules[m])
        import ff753 as FF
        data = FF.shell(FF.base())
        names0 = list(data.names.get("만화") or [])
        arr = {}
        for nm in PR.PAIRS:
            src = PR.SRC_DOM[nm]
            names = list(data.names.get(src) or [])
            A, M, y, t = PR.to_arrays(PR.build(nm), names)
            arr[nm] = (src, A, M, y, t)
        got = {nm: [] for nm in arr}
        for s in SEEDS:
            f = G._fit_on(lambda s=s: cls(seed=s), data, T, seed=s)
            for nm, (src, A, M, y, t) in arr.items():
                p = np.asarray(f.predict(src, A, M, t), float)
                ok = np.isfinite(p) & np.isfinite(y)
                got[nm].append(float(spearmanr(p[ok], y[ok]).statistic))
            print(f"  [{tag}] 씨앗 {s} · " +
                  " · ".join(f"{nm} {got[nm][-1]:+.4f}" for nm in arr), flush=True)
    finally:
        cls.OOC_DROP = old_drop
        fixaxes.orient = old_orient
    out = {}
    for nm, v in got.items():
        a = np.array(v, float)
        out[nm] = {"평균": round(float(a.mean()), 4),
                   "SD": round(float(a.std(ddof=1)), 4),
                   "최소": round(float(a.min()), 4), "최대": round(float(a.max()), 4)}
    out["_배선"] = {"OOC_DROP": list(cls.OOC_DROP if not revert
                                   else ("entry_friction",)),
                  "orient 껐나": revert, "만화 열": len(names0)}
    return out


def main():
    t0 = time.time()
    now = measure("지금", revert=False)
    print(json.dumps({"① 지금": {k: v for k, v in now.items() if k != "_배선"}},
                     ensure_ascii=False), flush=True)
    rev = measure("되돌림", revert=True)
    print(json.dumps({"② 되돌림": {k: v for k, v in rev.items() if k != "_배선"}},
                     ensure_ascii=False), flush=True)

    hit, det = {}, {}
    for nm, tg in TARGET.items():
        v = rev[nm]["평균"]
        det[nm] = {"되돌림": v, "노트 577 목표": tg, "차": round(v - tg, 4),
                   "**±0.02 안**": bool(abs(v - tg) <= TOL),
                   "지금": now[nm]["평균"], "지금−되돌림": round(now[nm]["평균"] - v, 4)}
        hit[nm] = det[nm]["**±0.02 안**"]
    ga = all(hit.values())
    gb = bool(hit["KR 만화"] and hit["비게임 앱"] and not hit["CN 만화"])
    gc = bool(not ga and not gb)
    #: 대조 --- 지금 팔이 노트 793 을 재현하나(배선이 안 흔들렸다는 증거)
    ctrl = {nm: {"지금": now[nm]["평균"], "노트 793": NOW[nm],
                 "차": round(now[nm]["평균"] - NOW[nm], 4),
                 "0.01 안": bool(abs(now[nm]["평균"] - NOW[nm]) <= 0.01)}
            for nm in TARGET}
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "🔴 못박은 목표": TARGET, "허용": TOL,
        "대조(지금 팔이 노트 793 을 재현하나)": ctrl,
        "짝별": det,
        "**판정 (가) 셋 다 맞음 --- 출처 설명 확정**": ga,
        "**판정 (나) KR·앱만 맞음 --- CN 은 다른 이유**": gb,
        "**판정 (다) 되돌림 복원 실패 --- 판정 미룸**": gc,
        "배선": {"지금": now["_배선"], "되돌림": rev["_배선"]},
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
