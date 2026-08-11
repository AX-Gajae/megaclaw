# -*- coding: utf-8 -*-
"""팔 909-ㅁ · 자 (나) 의 **기준선을 오늘 다시 잰다**.

사전등록 `docs/prereg_909_ssl.md` §3 (나) 는 노트 696 의 기록값
(KR 0.6831 · 앱 0.4968 · CN 0.3874)을 기준선으로 쓰되 *"오늘 다시 안 잰다"* 고
적었다 — 챔피언 적합 하나가 이 기계에서 **316초**이기 때문이다.

이 파일은 그 한계를 **한 씨앗만큼** 줄인다: 챔피언을 **한 번만** 적합하고
세 짝 전부에 예측한다(`lab/pairs.score` 는 짝마다 다시 적합한다 — 3배 비싸다).

🔴 씨앗 하나다. 씨앗 폭이 아니라 **같은 날 같은 파이프의 닻**이다.
🔴 읽기만 한다 — `lab/` 도 `state/` 도 안 고친다.

산출: `runners/out909_pairbase.json`
"""
import datetime as dt
import hashlib
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import numpy as np                                     # noqa: E402
from scipy.stats import spearmanr                      # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out909_pairbase.json"
SEED = 0
T = 2025.0


def sha_self() -> str:
    """🔴 내 파일의 sha 를 내가 박는다(티처 #59 M7)."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]


def main() -> int:
    t0 = time.time()
    from lab import forms, guards as G, pairs
    from lab.sideaudit import champion_data

    data = champion_data()
    t_data = time.time() - t0
    cls = forms.REGISTRY["F18_bagboost"]["cls"]
    t1 = time.time()
    f = G._fit_on(lambda: cls(seed=SEED), data, T, seed=SEED)
    t_fit = time.time() - t1

    res = {}
    for nm in ("KR 만화", "CN 만화", "비게임 앱"):
        try:
            rows = pairs.build(nm)                      # 시험 ① — 행수 불일치면 예외
        except Exception as e:
            res[nm] = {"오류": f"{type(e).__name__}: {e}"}
            continue
        src = pairs.SRC_DOM[nm]
        names = list(data.names.get(src) or [])
        A, M, y, t = pairs.to_arrays(rows, names)
        p = np.asarray(f.predict(src, A, M, t), float)
        ok = np.isfinite(y) & np.isfinite(p)
        res[nm] = {
            "원천 도메인": src,
            "행": len(rows), "기대 행": pairs.PAIRS[nm][2],
            "행수 일치(시험 ①)": len(rows) == pairs.PAIRS[nm][2],
            "채점 행": int(ok.sum()),
            "rho(씨앗 0)": round(float(spearmanr(p[ok], y[ok]).statistic), 4),
            "🔴 노트 696 기록값": {"KR 만화": 0.6831, "CN 만화": 0.3874,
                                 "비게임 앱": 0.4968}[nm],
            "축 덮개율(짝)": round(float(M.mean()), 4),
        }
    out = {
        "무엇": "자 (나) 집 밖 짝 — 챔피언 기준선 (씨앗 0 · 같은 날 닻)",
        "사전등록": {"파일": "docs/prereg_909_ssl.md",
                    "sha256": hashlib.sha256(
                        (ROOT / "docs/prereg_909_ssl.md").read_bytes()).hexdigest(),
                    "mtime": dt.datetime.fromtimestamp(
                        (ROOT / "docs/prereg_909_ssl.md").stat().st_mtime).isoformat()},
        "시각": dt.datetime.now().isoformat(),
        "코드 sha(자기 파일)": sha_self(),
        "씨앗": [SEED],
        "⚠ 한계": "씨앗 하나다 — 씨앗 SD 를 못 낸다. 노트 696 의 씨앗SD "
                 "(KR 0.0075 · 앱 0.0069 · CN 0.0066)를 빌려 쓰지 않는다(조항 60).",
        "벽시계(초)": {"champion_data": round(t_data, 1), "챔피언 적합": round(t_fit, 1),
                     "합": round(time.time() - t0, 1)},
        "결과": res,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
