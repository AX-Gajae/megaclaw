# -*- coding: utf-8 -*-
"""노트 961 [판정] · 🔴 **사후(post-hoc) 곁 측정 — 사전등록에 없다. 그렇게 읽어라.**

**왜 이걸 돌리나.** `curve961.py` 의 닻 ① 이 예상 밖의 수를 냈다:

    실제 941 표(464행 · 9열) · 🔴 **배경 풀 3,896**  →  Δρ = **−0.005928** · T 0.007622 · **나 — 못 가른다**
    960 이 같은 자리에서 낸 값                        →  Δρ = **−0.007687** · T 0.006557 · **다 — 뺀다**

같은 464행 · 같은 9열 · 같은 부트(4,000 · 씨앗 7) · 같은 코드다. **다른 것은 하나뿐이다**:
`runners/post960.py:72` 가 464 팔을 만들 때 `L.WIKI = data/ingest/wiki_daily`(**941 배경**)를 썼고
`curve961.py` 는 `data/ingest/wiki_daily959`(**959 배경 · 3,896 개체**)를 쓴다.

🔴 **층 ③ 은 「도메인 배경 대비 편차」다 — 배경 풀을 갈면 x3 의 모든 원소가 바뀐다.**

이 러너는 **다른 것을 전부 같게 두고 배경 풀만 갈아** 그 차이를 못 박는다.

    python3 runners/post961.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))

import numpy as np                                              # noqa: E402

import runners.layers957 as L                                   # noqa: E402
from runners.grow959 import build_arms_fast, OUTDIR, PAIRDIR    # noqa: E402
from runners.curve961 import boot_se, T_of, BOOT                # noqa: E402

OUT = ROOT / "runners/out961_post.json"
PAIRS941 = ROOT / "data/ingest/sao941/pairs.jsonl.gz"
BG941 = ROOT / "data/ingest/wiki_daily"
BG959 = OUTDIR


def arm_on(bg: Path, pairs_path: Path, coords, lp) -> dict:
    L.WIKI = bg
    L.PAIRS = pairs_path
    wd = L.load_wiki_daily()
    rows = build_arms_fast(wd, coords, lp, L.load_pairs())["B"]
    doms = sorted({r["도메인"] for r in rows})
    for r in rows:
        r["xd"] = [1.0 if r["도메인"] == d else 0.0 for d in doms]
    y = np.asarray([r["y_들림"] for r in rows], dtype=float)
    g = np.asarray([r["개체"] for r in rows])
    dm = np.asarray([r["도메인"] for r in rows])
    ra, _, Pa = L.rho_of(L.mat(rows, "x1", "xd"), y, g)
    rb, _, Pb = L.rho_of(L.mat(rows, "x1", "xd", "x3"), y, g)
    be = boot_se(Pa, Pb, y, g, why=f"{bg.name} 개체")
    bd = boot_se(Pa, Pb, y, dm, why=f"{bg.name} 도메인")
    Te, Td = T_of(be["SE"]), T_of(bd["SE"])
    x3 = L.mat(rows, "x3")
    return {
        "배경 디렉터리": bg.name,
        "🔴 배경 풀 개체 수": int(sum(len(v) for v in wd["일별"].values())),
        "분모: 행": len(rows), "지시자 열": len(doms),
        "도메인별 행": dict(Counter(dm.tolist())),
        "🔴 x3 행렬 sha256(앞16)": hashlib.sha256(x3.tobytes()).hexdigest()[:16],
        "x3 열 평균": [float(v) for v in x3.mean(0)],
        "ρ(①+지시자)": ra, "ρ(①+지시자+③)": rb, "🔴 Δρ": rb - ra,
        "SE(개체)": be["SE"], "T(개체)": Te,
        "SE(도메인)": bd["SE"], "T(도메인)": Td,
        "부트 성공/요청": [be["재표집 성공"], be["요청"]],
        "판정(개체 T)": L.verdict(rb - ra, Te),
        "판정(도메인 T)": L.verdict(rb - ra, Td),
        "🔴 여유(|Δρ|/T 개체)": abs(rb - ra) / Te,
    }


def main() -> dict:
    t0 = time.time()
    coords = L.load_coords()
    lp = L.load_lifepop()
    a = arm_on(BG941, PAIRS941, coords, lp)     # 960 이 쓴 배경
    b = arm_on(BG959, PAIRS941, coords, lp)     # 961 이 쓴 배경
    same_rows = a["분모: 행"] == b["분모: 행"] == 464
    R = {
        "노트": 961, "레인": "판정",
        "🔴🔴 이것은 사후다": ("사전등록 `docs/prereg_961_curve.md` 에 없다. "
                       "`curve961.py` 의 닻 ① 이 960 의 수와 어긋나서 **원인을 못 박으려고** 뒤에 돌렸다. "
                       "🔴 **판정을 여기서 세우지 마라 — 이것은 진단이다**"),
        "🔴 무엇을 재나": "464행 · 9열 · 같은 쌍 표 · 같은 부트를 두고 **배경 풀만** 941(813) ↔ 959(3,896) 로 간다",
        "🔴 새 자료": "0 — HTTP 호출 0",
        "가 · 배경 = 941 (960 이 쓴 것)": a,
        "나 · 배경 = 959 (961 이 쓴 것)": b,
        "🔴🔴 배경만 갈았을 때": {
            "행이 같나": bool(same_rows),
            "지시자 열이 같나": bool(a["지시자 열"] == b["지시자 열"]),
            "도메인 구성이 같나": bool(a["도메인별 행"] == b["도메인별 행"]),
            "🔴 x3 이 다른가(sha256)": bool(a["🔴 x3 행렬 sha256(앞16)"] != b["🔴 x3 행렬 sha256(앞16)"]),
            "Δρ(941 배경)": a["🔴 Δρ"], "Δρ(959 배경)": b["🔴 Δρ"],
            "🔴 차": b["🔴 Δρ"] - a["🔴 Δρ"],
            "판정(941 배경 · 개체 T)": a["판정(개체 T)"],
            "판정(959 배경 · 개체 T)": b["판정(개체 T)"],
            "🔴 판정이 바뀌나": bool(a["판정(개체 T)"] != b["판정(개체 T)"]),
            "여유(941)": a["🔴 여유(|Δρ|/T 개체)"], "여유(959)": b["🔴 여유(|Δρ|/T 개체)"],
        },
        "🔴 960 이 적은 값": {"Δρ": -0.007687, "T": 0.006557, "판정": "다 — 뺀다", "여유": 1.172},
        "⚠ 이 자가 못 보는 것": ("배경 풀을 갈면 **배경의 크기와 배경의 내용이 같이** 바뀐다 — "
                       "813 → 3,896 은 개체 수도 늘고 도메인별 구성도 바뀐다. **둘을 못 가른다**"),
        "초": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    return R


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: v for k, v in r.items()
                      if not k.startswith(("가 ·", "나 ·"))}, ensure_ascii=False, indent=1))
