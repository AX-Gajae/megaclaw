# -*- coding: utf-8 -*-
"""노트 945 — ⑤′ 절 4 의 「도장 없음」이 **정말 도장이 없는 것인가**를 센다.

🔴 티처 #84 M4: *「재현했다」고 쓰려면 코드를 커밋하라*. `docs/수리/945.md` §7′ 의
「118 중 29 는 한 겹 아래에 도장이 있다 · 정말 없는 것은 89」가 이 러너의 산출물이다.

## 무엇을 세나

`runners/fiveprime902.py:373` 이 `keys = [k for k in d if any(w in k for w in want)]`
로 **최상위 키만** 본다(`want = ("시각", "sha256")`). 941~945 의 러너는 도장을
`"🔴 스탬프"` **밑에 한 겹** 넣는다 → 도장이 있는데도 「없음」으로 세어진다.

같은 규칙(`want`)을 **한 겹 아래까지** 적용해 다시 센다. 🔴 `fiveprime902.py` 는
**안 고친다** — 세어서 드러내는 것이 이 러너의 일이다(수리 레인은 한 사이클에 하나).

쓰는 법::  python3 runners/out945_stampscan.py
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
OUT = ROOT / "runners/out945_stampscan.json"
WANT = ("시각", "sha256")      # 🔴 fiveprime902.py:359 와 **같은** 낱말


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def top_keys(d: dict) -> list:
    """검출기가 지금 하는 것 — 최상위만."""
    return [k for k in d if any(w in k for w in WANT)]


def nested_keys(d: dict) -> dict:
    """한 겹 아래. `{바깥키: [도장키...]}`."""
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            ks = [kk for kk in v if any(w in kk for w in WANT)]
            if ks:
                out[k] = ks
    return out


def main() -> dict:
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    files = sorted((ROOT / "runners").glob("out*.json"))
    top_ok, nested_only, none_at_all, unreadable = [], [], [], []
    where: dict = {}
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:                                   # noqa: BLE001
            unreadable.append(rel + " :: " + type(e).__name__)
            continue
        if not isinstance(d, dict):
            none_at_all.append(rel)
            continue
        if top_keys(d):
            top_ok.append(rel)
            continue
        nk = nested_keys(d)
        if nk:
            nested_only.append(rel)
            where[rel] = nk
        else:
            none_at_all.append(rel)

    res = {
        "노트": 945, "레인": "🔴 수리 — ⑤′ 절 4 의 수를 다시 센다",
        "물음": "⑤′ 가 「도장 없음」이라 센 산출물이 정말 도장이 없나",
        "🔴 스탬프": {
            "시작 시각": t_start,
            "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256": {"runners/fiveprime902.py": sha(ROOT / "runners/fiveprime902.py")},
            "코드 sha256": {"runners/out945_stampscan.py":
                          sha(ROOT / "runners/out945_stampscan.py")},
        },
        "🔴 조항 60 — 명령·범위·트리": {
            "명령": "python3 runners/out945_stampscan.py",
            "범위": "runners/out*.json 전량",
            "트리": "작업 트리만",
        },
        "🔴 분모 — runners/out*.json": len(files),
        "최상위에 도장이 있다(검출기가 세는 것)": len(top_ok),
        "🔴 한 겹 아래에만 도장이 있다(거짓 음성)": len(nested_only),
        "🔴 정말 아무 도장도 없다": len(none_at_all),
        "못 읽었다": unreadable or "없음",
        "🔴 검출기가 「없음」으로 세는 수(= 거짓음성 + 진짜없음)":
            len(nested_only) + len(none_at_all),
        "거짓 음성 목록": nested_only,
        "거짓 음성이 도장을 숨긴 바깥 키": where,
        "🔴 못 한 것": [
            "`fiveprime902.py` 를 **안 고쳤다** — 수리 레인은 한 사이클에 하나(규칙 4)",
            "두 겹 아래는 안 봤다 — 한 겹만 내려갔다",
            "`runners/` 밖의 산출물은 안 봤다(검출기와 같은 범위를 썼다)",
        ],
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("거짓 음성 목록", "거짓 음성이 도장을 숨긴 바깥 키")},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
