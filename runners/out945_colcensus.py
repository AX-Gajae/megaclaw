# -*- coding: utf-8 -*-
"""노트 945(**탐색 레인**) — `dataset_v2` 가 132열을 짓는데 판은 몇 열을 쓰나. 소비자 전수.

🔴 **탐색 레인이다. 판정하지 않는다.** 넷만 적는다:
무엇을 했나 · 무엇이 나왔나 · **분모** · 못 한 것 (`docs/루프.md` 레인 표).
🔴 **판 ρ 를 부르지 않는다.** 이건 배선을 세는 일이지 성능을 재는 일이 아니다.

## 물음 (티처 #84 C2 가 남긴 것)

`state/dataset_v2.py` 가 132열을 지어 `data/state/popup_v2.npz` 에 넣는다.
`state/slots.py:63-68` 이 그중 `t1o_*` **다섯 쌍**을 앵커 타깃 `A`·`M` 으로 뽑고,
`state/tri_domain.py:107` 이 `X` 를(=나머지 전부) **버린다** → 판에 드는 것은 다섯 축뿐이다.
**나머지는 왜 지어지고 누가 읽나?**

## 어떻게 세나 (세 갈래 · 서로 겹칠 수 있다 — 겹침을 따로 신고한다)

  ㄱ **판 경로**: `tri_domain.load_all()` 이 실제로 들고 가는 열 — `slots.AXES` 로 기계 판정.
  ㄴ **narrow 경로**: `slots.load_popup(narrow=True)` 의 `pick` 목록 — 코드를 **실행해서** 받는다.
  ㄷ **이름 경로**: 저장소의 `.py` 전체에 열 이름을 **문자열로** 물린다.
     🔴 이름 상당수가 f-string 으로 **생성**되므로(`f"t1_{k}"`), 못 잡는 것이 있다.
     그래서 **접미/접두를 뗀 밑동**(`t1_host_daily_traffic` → `host_daily_traffic`)도 따로 센다.
  ㄹ 🔴 **생성 이름 경로**(초판이 빠뜨렸다): `.py` 안의 f-string 리터럴 `f"trust_{g}"` 을
     정규식 `trust_[A-Za-z0-9_]+` 로 바꿔 열 이름에 물린다. 이것이 없으면
     `trust_A~E` 다섯이 「아무도 안 읽는다」로 **틀리게** 떨어진다
     (실제로는 `state/slots.py:49-56` 이 **행을 고르는 데** 쓴다).
     ⚠ `f"{k}_mask"` 같은 것은 `*_mask` 를 **전부** 물어 과잉 매칭한다 — 따로 신고한다.

쓰는 법::  python3 runners/out945_colcensus.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
OUT = ROOT / "runners/out945_colcensus.json"
NPZ = ROOT / "data/state/popup_v2.npz"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def py_files() -> list:
    """저장소가 **추적하는** `.py` 전량. 작업 트리 기준(조항 60)."""
    r = subprocess.run(["git", "ls-files", "*.py"], capture_output=True, text=True)
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def stem_of(col: str) -> str:
    """열 이름의 **밑동** — 접두(t1_/t1o_/t1b_/cal_/trend_/cat_/unit_/trust_)와 `_mask` 를 뗀다."""
    s = col[:-5] if col.endswith("_mask") else col
    for p in ("t1o_", "t1b_", "t1_", "cal_", "trend_", "cat_", "unit_", "trust_"):
        if s.startswith(p):
            return s[len(p):]
    return s


def main() -> dict:                                       # noqa: PLR0915
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    import numpy as np
    d = np.load(NPZ, allow_pickle=True)
    cols = [str(c) for c in d["names"]]
    block = json.loads(str(d["block"]))

    # ── ㄱ 판 경로 ────────────────────────────────────────────────────────
    from state.slots import AXES
    board_cols = [f"t1o_{a}" for a in AXES] + [f"t1o_{a}_mask" for a in AXES]
    board_axes = list(AXES)

    # ── ㄴ narrow 경로 — 코드를 실행해서 받는다 ────────────────────────────
    from state.slots import load_popup
    _Xin, _y, _w, _A, _M, _g, _t, narrow_cols = load_popup()
    narrow = set(narrow_cols)

    # ── ㄷ 이름 경로 ──────────────────────────────────────────────────────
    files = py_files()
    text = {f: (ROOT / f).read_text(errors="ignore") for f in files if (ROOT / f).exists()}
    lit: dict = {}
    stem_hit: dict = {}
    for c in cols:
        pat = re.compile(r"(?<![\w])" + re.escape(c) + r"(?![\w])")
        hits = sorted(f for f, t in text.items() if pat.search(t))
        lit[c] = hits
        st = stem_of(c)
        spat = re.compile(r"(?<![\w])" + re.escape(st) + r"(?![\w])")
        stem_hit[c] = sorted(f for f, t in text.items() if spat.search(t))

    # ── ㄹ 생성 이름 경로 — f-string 리터럴을 정규식으로 ────────────────────
    FSTR = re.compile(r"""f(['"])([A-Za-z0-9_{}]*?)\1""")
    #: 🔴 **접두가 3글자 미만인 f-string 은 버린다.** `f"p{k}_{d}_{i}"` 같은 것이
    #:    `prior_n_log`·`pnl_pre_total_mask` 를 물어 거짓 양성을 낸다(초판이 그랬다).
    MIN_PREFIX = 3
    gen_hit: dict = {c: [] for c in cols}
    gen_wide: dict = {c: [] for c in cols}      # 접두가 짧다 = 과잉 매칭 위험
    dropped_weak = Counter()
    for f, t in text.items():
        pats = set()
        for _q, body in FSTR.findall(t):
            if "{" not in body:
                continue
            rx = re.sub(r"\{[^{}]*\}", "\x00", body)
            prefix = rx.split("\x00")[0]
            pats.add((body, "^" + re.escape(rx).replace("\x00", "[A-Za-z0-9_]+") + "$",
                      len(prefix) >= MIN_PREFIX))
        for body, rx, strong in pats:
            cre = re.compile(rx)
            for c in cols:
                if cre.match(c):
                    (gen_hit if strong else gen_wide)[c].append(f + " :: f" + body)
                    if not strong:
                        dropped_weak[f + " :: f" + body] += 1

    # ── 갈래 다섯으로 가른다 ──────────────────────────────────────────────
    GEN = ("state/dataset_v2.py", "state/slots.py", "state/tri_domain.py")
    buckets: dict = {"판이 읽는다": [], "narrow(slots 실험)만 읽는다": [],
                     "다른 코드가 이름으로 읽는다": [],
                     "생성된 이름으로만 읽힌다(행 거르기 등)": [],
                     "🔴 아무도 안 읽는다": []}
    detail: dict = {}
    for c in cols:
        others = [f for f in lit[c] if f not in GEN]
        stem_others = [f for f in stem_hit[c] if f not in GEN]
        gens = sorted({g for g in gen_hit[c] if g.split(" :: ")[0] not in GEN})
        if c in board_cols:
            b = "판이 읽는다"
        elif c in narrow:
            b = "narrow(slots 실험)만 읽는다"
        elif others:
            b = "다른 코드가 이름으로 읽는다"
        elif gens:
            b = "생성된 이름으로만 읽힌다(행 거르기 등)"
        else:
            b = "🔴 아무도 안 읽는다"
        buckets[b].append(c)
        detail[c] = {"갈래": b, "판": c in board_cols, "narrow": c in narrow,
                     "이름이 뜨는 .py(생성 셋 제외)": others,
                     "생성 이름이 뜨는 곳(생성 셋 제외)": gens,
                     "과잉 매칭 f-string 수": len(gen_wide[c]),
                     "밑동이 뜨는 .py(생성 셋 제외)": stem_others,
                     "블록": next((k for k, v in block.items()
                                 if k != "mask" and cols.index(c) in v), None)}

    # 「아무도 안 읽는다」 중에서 **밑동은 뜨는 것** — 생성된 이름이라 못 잡았을 수 있다
    nobody = buckets["🔴 아무도 안 읽는다"]
    nobody_stem = [c for c in nobody if detail[c]["밑동이 뜨는 .py(생성 셋 제외)"]]

    # 겹침 — 넷은 서로 겹친다. 뺄셈 대신 **합집합과 교집합을 다 적는다**(조항 60)
    board_set = set(board_cols)
    name_set = {c for c in cols if detail[c]["이름이 뜨는 .py(생성 셋 제외)"]}
    gen_set = {c for c in cols if detail[c]["생성 이름이 뜨는 곳(생성 셋 제외)"]}
    overlap = {
        "판(10) ∩ narrow(70)": len(board_set & narrow),
        "판 ∩ 이름": len(board_set & name_set),
        "판 ∩ 생성이름": len(board_set & gen_set),
        "narrow ∩ 이름": len(narrow & name_set),
        "narrow ∩ 생성이름": len(narrow & gen_set),
        "이름 ∩ 생성이름": len(name_set & gen_set),
        "🔴 판 ∪ narrow ∪ 이름 ∪ 생성이름": len(board_set | narrow | name_set | gen_set),
        "🔴 넷 다 아닌 열": len(set(cols) - (board_set | narrow | name_set | gen_set)),
        "각 통의 크기": {"판": len(board_set), "narrow": len(narrow),
                    "이름": len(name_set), "생성이름": len(gen_set)},
    }

    # 접두별 요약
    def pre(c):
        for p in ("prior_", "t1o_", "t1b_", "t1_", "cal_", "trend_", "comp_",
                  "pnl_", "cat_", "unit_", "trust_"):
            if c.startswith(p):
                return p
        return "(기타)"

    bypre: dict = {}
    for c in cols:
        k = pre(c)
        bypre.setdefault(k, Counter())[detail[c]["갈래"]] += 1

    # 이름을 가장 많이 읽는 파일
    reader = Counter()
    for c in cols:
        for f in detail[c]["이름이 뜨는 .py(생성 셋 제외)"]:
            reader[f] += 1

    res = {
        "노트": 945, "레인": "🔴 탐색 — **판정하지 않는다**",
        "물음": "dataset_v2 가 132열을 짓는데 판은 5축만 쓴다 — 나머지는 왜 지어지고 누가 읽나",
        "🔴 판 ρ": "부르지 않았다(배선을 세는 일이지 성능을 재는 일이 아니다)",
        "🔴 스탬프": {
            "시작 시각": t_start,
            "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256": {
                "data/state/popup_v2.npz": sha(NPZ),
                "state/dataset_v2.py": sha(ROOT / "state/dataset_v2.py"),
                "state/slots.py": sha(ROOT / "state/slots.py"),
                "state/tri_domain.py": sha(ROOT / "state/tri_domain.py"),
            },
            "코드 sha256": {"runners/out945_colcensus.py":
                          sha(ROOT / "runners/out945_colcensus.py")},
        },
        "🔴 조항 60 — 명령·범위·트리": {
            "명령": "python3 runners/out945_colcensus.py",
            "범위(열)": f"popup_v2.npz 의 names 전량 {len(cols)}",
            "범위(코드)": f"git ls-files '*.py' = {len(files)} 파일",
            "트리": "작업 트리(git ls-files 로 추적 목록만). 인덱스와 안 섞는다",
        },
        "🔴 분모": {
            "dataset_v2 가 짓는 열": len(cols),
            "행": int(d["X"].shape[0]),
            "블록(dataset_v2.block_index)": {k: len(v) for k, v in block.items()},
            "훑은 .py 파일": len(files),
        },
        "🔴 갈래 넷": {k: len(v) for k, v in buckets.items()},
        "🔴 겹침": overlap,
        "판": {"판이 실제로 드는 축": board_axes, "그 축이 쓰는 npz 열": board_cols,
              "열 수": len(board_cols), "축 수": len(board_axes)},
        "narrow(slots 실험 입력)": {"열 수": len(narrow_cols),
                                "판 축과 겹치는 열": sorted(board_set & narrow)},
        "🔴 아무도 안 읽는 열": nobody,
        "🔴 그중 밑동은 다른 .py 에 뜨는 열(생성된 이름일 수 있다)": nobody_stem,
        "🔴 접두 3글자 미만이라 **버린** f-string 상위 8(거짓 양성 원천)":
            dict(dropped_weak.most_common(8)),
        "생성된 이름으로만 읽히는 열": {
            c: detail[c]["생성 이름이 뜨는 곳(생성 셋 제외)"]
            for c in buckets["생성된 이름으로만 읽힌다(행 거르기 등)"]},
        "접두별 갈래": {k: dict(v) for k, v in bypre.items()},
        "열 이름을 가장 많이 읽는 .py 상위 12": dict(reader.most_common(12)),
        "열별 상세": detail,
        "🔴 못 한 것": [
            "f-string 으로 **생성되는** 이름은 문자열 grep 이 못 잡는다 — 밑동 검색으로 "
            "보완했지만 밑동이 흔한 낱말(days·family)이면 거짓 양성이 난다",
            "`.py` 만 훑었다 — 노트(`docs/*.md`)·JSON 설정은 안 셌다",
            "「읽는다」를 **이름이 뜬다**로 정의했다 — 실제로 그 열의 값을 쓰는지는 안 봤다",
            "🔴 판 ρ 를 안 불렀다(일부러). 열을 빼거나 더했을 때의 효과는 이 러너 밖이다",
        ],
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "열별 상세"},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
