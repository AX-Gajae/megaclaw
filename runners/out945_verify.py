# -*- coding: utf-8 -*-
"""노트 945 **두 번째 경로** — 945 의 수를 **다른 규칙 둘**로 다시 센다.

🔴 티처 #84 M7 이 944 의 두 번째 경로를 걸었다: `fam2()` 가 첫 경로를 **글자 그대로 옮긴 것**
이었고 받은 `path` 인자를 **한 번도 안 썼다**. 이 러너는 그 둘을 안 한다.

## 규칙이 어떻게 다른가

| | 첫 경로(`out945_obstime.py`) | 🔴 이 러너 |
|---|---|---|
| 최초추가 시각 | `git log --all --name-only` **한 번**을 벌크 파싱 | **파일마다 `git log` 를 따로** 돌려 마지막 줄을 읽는다 |
| 「추적됨」 판정 | `--diff-filter=A` 이력에 이름이 있나 | 🔴 **`git ls-tree -r` 로 모든 ref 의 끝 트리**를 훑어 이름이 있나 |
| 만화 쌍 | 저장소 레코드를 돌며 조인 | 🔴 **캐시 파일 쪽에서** id→(파일,값) 을 세워 뒤집는다 |

두 경로가 다른 답을 내면 **어긋난 채로 신고한다**(빈 목록도 남긴다 — 티처 #84 m4).

쓰는 법::  python3 runners/out945_verify.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import statistics
import subprocess
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
OUT = ROOT / "runners/out945_verify.json"
FIRST = ROOT / "runners/out945_obstime.json"

MANGA_DIRS = ["data/state/cache_manga", "data/state/cache_manga_below",
              "data/state/cache_manga_mid", "data/state/cache_manga_deep",
              "data/state/cache_manga_recent", "data/state/cache_manga_below_pre"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def to_epoch(s: str) -> float:
    return dt.datetime.fromisoformat(s).timestamp()


def first_add_per_file(rel: str):
    """🔴 규칙 A — **파일 하나에 `git log` 하나.** 마지막 줄이 가장 오래된 추가다.

    `rel` 은 실제로 명령에 들어간다(944 의 안 쓰이는 인자를 되풀이하지 않는다).
    """
    r = subprocess.run(
        ["git", "log", "--all", "--diff-filter=A", "--format=%aI", "--", rel],
        capture_output=True, text=True, timeout=300)
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return lines[-1] if lines else None


def tracked_by_lstree() -> set:
    """🔴 규칙 B — 「추적됨」을 이력이 아니라 **모든 ref 의 끝 트리**에서 센다."""
    refs = subprocess.run(["git", "for-each-ref", "--format=%(refname)"],
                          capture_output=True, text=True, timeout=300).stdout.split()
    seen: set = set()
    for ref in refs:
        r = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref,
                            "--", "data/state/"], capture_output=True, text=True,
                           timeout=600)
        for ln in r.stdout.splitlines():
            if ln.startswith("data/state/cache_"):
                seen.add(ln)
    return seen


def main() -> dict:
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    first = json.loads(FIRST.read_text())

    # ── 규칙 C — 캐시 파일 쪽에서 id → [(mtime, popularity, 경로)] 를 세운다 ──
    by_id: dict = defaultdict(list)
    nfile = 0
    for d in MANGA_DIRS:
        dp = ROOT / d
        if not dp.exists():
            continue
        for f in sorted(dp.glob("*.json")):
            nfile += 1
            try:
                blob = json.loads(f.read_text())
                media = blob["data"]["Page"]["media"]
            except (json.JSONDecodeError, OSError, KeyError, TypeError,
                    UnicodeDecodeError):
                continue
            if not isinstance(media, list):
                continue
            mt = round(f.stat().st_mtime)
            rel = str(f.relative_to(ROOT))
            for m in media:
                if isinstance(m, dict) and "id" in m:
                    by_id[m["id"]].append((mt, m.get("popularity"), rel))

    mg = json.loads((ROOT / "data/state/manga_records.json").read_text())
    live_ids = {v["media_id"] for v in mg.values()
                if isinstance(v, dict) and v.get("media_id") is not None}

    # ── 규칙 A 를 쌍의 출처 파일에만(전수) 돌린다 ─────────────────────────
    pairs = []
    src_needed: set = set()
    for i, rows in by_id.items():
        if i not in live_ids:
            continue
        rows = sorted(rows)
        if len({t for t, _, _ in rows}) < 2:
            continue
        a, b = rows[0], rows[-1]
        if a[1] is None or b[1] is None or a[1] == b[1]:
            continue
        pairs.append((i, a, b))
        src_needed.add(a[2])
        src_needed.add(b[2])

    add_a: dict = {}
    for rel in sorted(src_needed):
        add_a[rel] = first_add_per_file(rel)

    diff_commit = 0
    gap_git, gap_mtime = [], []
    for _i, a, b in pairs:
        c1, c2 = add_a.get(a[2]), add_a.get(b[2])
        if c1 and c2:
            diff_commit += (c1 != c2)
            gap_git.append((to_epoch(c2) - to_epoch(c1)) / 3600)
        gap_mtime.append((b[0] - a[0]) / 3600)

    # ── 규칙 B — 추적 집합 ────────────────────────────────────────────────
    lstree = tracked_by_lstree()
    disk = {str(p.relative_to(ROOT))
            for d in sorted((ROOT / "data/state").glob("cache_*")) if d.is_dir()
            for p in sorted(d.iterdir()) if p.is_file()}
    only_mtime_b = sorted(disk - lstree)

    def med(xs):
        return round(statistics.median(xs), 2) if xs else None

    mine = {
        "쌍(분모)": len(pairs),
        "출처가 다른 커밋": diff_commit,
        "두 커밋 간격 중앙(시간)": med(gap_git),
        "mtime 간격 중앙(시간)": med(gap_mtime),
        "mtime 만 아는 파일": len(only_mtime_b),
        "연 만화 페이지 파일": nfile,
        "쌍의 출처 파일(서로 다른)": len(src_needed),
        "ls-tree 추적 집합 크기": len(lstree),
    }
    theirs = {
        "쌍(분모)": first["🔴 만화 두 점"]["분모 — popularity 가 달라진 만화 레코드"],
        "출처가 다른 커밋": first["🔴 만화 두 점"]["🔴 P1  후(min) 출처가 다른 커밋"],
        "두 커밋 간격 중앙(시간)": first["🔴 만화 두 점"]["🔴 P2  두 커밋 간격(시간)"]["중앙"],
        "mtime 간격 중앙(시간)": first["🔴 만화 두 점"]["🔴 P2′ mtime 간격(시간)"]["중앙"],
        "mtime 만 아는 파일": first["🔴 지도 전/후"]["🔴 P4 고친 뒤에도 mtime 만 아는 파일"],
    }
    mismatch = [k for k, v in theirs.items() if mine.get(k) != v]

    res = {
        "노트": 945, "레인": "🔴 수리 — 두 번째 경로",
        "물음": "945 의 수가 **다른 규칙**으로도 같은가",
        "🔴 스탬프": {
            "시작 시각": t_start,
            "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256": {
                "data/state/manga_records.json": sha(ROOT / "data/state/manga_records.json"),
                "runners/out945_obstime.json": sha(FIRST),
            },
            "코드 sha256": {"runners/out945_verify.py":
                          sha(ROOT / "runners/out945_verify.py")},
        },
        "🔴 조항 60 — 명령·범위·트리": {
            "명령": "python3 runners/out945_verify.py",
            "범위": MANGA_DIRS + ["data/state/manga_records.json", "data/state/cache_*"],
            "트리": "작업 트리(디스크) + 모든 ref 의 끝 트리(ls-tree). 인덱스는 안 본다",
        },
        "🔴 두 번째 경로": mine,
        "🔴 첫 경로": theirs,
        "🔴 어긋난 항목": mismatch,
        "🔴 규칙 차이": {
            "A": "파일마다 git log 를 따로(첫 경로는 벌크 한 번)",
            "B": "ls-tree 로 모든 ref 의 끝 트리(첫 경로는 --diff-filter=A 이력)",
            "C": "캐시 파일 쪽에서 id 를 세워 뒤집는다(첫 경로는 레코드 쪽에서 조인)",
        },
        "🔴 규칙 B 의 한계(실측)": {
            "끝 트리에 있으나 디스크에 없는 캐시 경로": len(lstree - disk),
            "설명": "규칙 B 는 **끝 트리**만 본다 — 도중에 지워진 파일은 못 본다. "
                  "규칙 A(이력)와 답이 같으면 '지워진 캐시 파일이 없다'는 뜻이다",
        },
        "🔴 못 한 것": [
            "쌍의 출처가 아닌 캐시 파일에는 규칙 A(파일마다 git log)를 안 돌렸다 — "
            "54,876 전량에 돌리면 명령 5만 번이라 이 사이클에서 안 했다",
        ],
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
