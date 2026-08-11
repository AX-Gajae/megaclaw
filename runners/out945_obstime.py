# -*- coding: utf-8 -*-
"""노트 945(**수리 레인**) — `git_add_times()` 의 `or` 를 `min` 으로. 전/후를 나란히 낸다.

## 무엇이 틀렸나 (티처 #84 C1)

`runners/out944b_obstime.py:135-158` 은 `HEAD` 지도와 `--all` 지도를 **둘 다** 만든다
(docstring `:139` 이 「`--all` 로 돌려서 다른 갈래의 스냅샷도 센다」고 적는다).
그런데 `:329`·`:397-398` 이 **`git_head.get(x) or git_all.get(x)`** 로 HEAD 를 먼저 쓴다.
캐시 전량이 HEAD 의 `2026-08-07T23:05:58` **한 커밋에 재추가**돼 있어서
**`or` 의 오른쪽이 한 번도 안 켜진다** → 944 의 「git 범위 = HEAD 25,372/25,372」.

**고침**: 두 값이 다 있으면 **이른 쪽**을 쓴다(`min`). 그것이 진짜 최초추가다.

## 이 러너가 내는 것

  ① 같은 실행 안에서 **`or`(전)** 과 **`min`(후)** 을 **둘 다** 계산해 나란히 낸다.
  ② 만화 두 점의 **출처 커밋이 서로 다른 쌍**을 전/후로 센다 (사전등록 P1/P1′).
  ③ 두 커밋 간격 중앙 · mtime 간격 중앙 (P2/P2′).
  ④ `git최초커밋 − mtime` 분포 전/후 (P3).
  ⑤ 🔴 **고친 뒤에도 mtime 만 아는 파일 수** — 디스크에 있으나 `--all` 이 모르는 캐시 파일 (P4).
  ⑥ `min` 이 HEAD 쪽을 고른 수 (P5 · 항등적으로 0 이어야 한다).
  ⑦ 🔴 **clone 해도 사는 근거 파일** `data/state/obs_time945_gitmap.json` 을 떨군다 —
     `archive/pre-github` 를 origin 이 **거부**했으므로(147MB blob) 지도 자체를 커밋한다.

🔴 941~944 산출물은 동결이다. 이 러너는 `runners/out945_obstime.json` 과
   `data/state/obs_time945_gitmap.json` 만 쓴다. 944 의 어떤 파일도 안 건드린다.
🔴 스탬프 넷: 시작 · 끝 · 입력 sha256 · 코드 sha256. `git rev-parse HEAD` 는 안 쓴다.

쓰는 법::  python3 runners/out945_obstime.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
OUT = ROOT / "runners/out945_obstime.json"
GITMAP = ROOT / "data/state/obs_time945_gitmap.json"
CACHEMAP = ROOT / "data/state/obs_time945_cachemap.json"

STORES = {
    "data/state/manga_records.json": "만화",
    "data/state/webtoon_records.json": "웹툰",
    "data/state/anime_records.json": "애니",
    "data/state/wanime_records.json": "세계애니",
    "data/state/funding_records.json": "펀딩",
    "data/state/mobile_records.json": "모바일",
    "data/state/app_records.json": "앱",
    "data/state/game_records.json": "게임",
    "data/state/book_records.json": "도서",
}

#: 944 와 **같은** 조인 규칙을 쓴다 — 이 사이클이 바꾸는 것은 시각의 **출처 선택**뿐이다.
DIRECT_JOIN = {
    "게임": [("data/state/cache_steam", "app_{appid}.json"),
            ("data/state/cache_steamspy", "{record_id}.json")],
    "모바일": [("data/state/cache_mobile", "app_{app_id}.json")],
    "앱": [("data/state/cache_mobile", "app_{app_id}.json")],
    "애니": [("data/state/cache_anime", "ep_{item_id}.json")],
    "웹툰": [("data/state/cache_webtoon", "asc_{title_id}.json")],
    "도서": [("data/state/cache_bookpage", "{record_id}.html"),
            ("data/state/cache_aladin_book", "item_{item_id}.html")],
    "펀딩": [("data/state/cache_fundpage", "{record_id}.html")],
}

PAGE_JOIN = {
    "만화": (["data/state/cache_manga", "data/state/cache_manga_below",
             "data/state/cache_manga_mid", "data/state/cache_manga_deep",
             "data/state/cache_manga_recent", "data/state/cache_manga_below_pre"],
            "anilist", "media_id"),
    "세계애니": (["data/state/cache_wanime", "data/state/cache_wanime_deep"],
              "anilist", "media_id"),
    "펀딩": (["data/state/cache_tumblbug"], "tumblbug", "uuid"),
}

PAGE_O = {"anilist": ("popularity", "favourites", "meanScore"),
          "tumblbug": ("amount", "percentage")}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def to_epoch(isostr: str) -> float:
    return dt.datetime.fromisoformat(isostr).timestamp()


def dist(xs: list, unit: str = "h") -> dict:
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "최소": round(min(xs), 2), "중앙": round(statistics.median(xs), 2),
            "최대": round(max(xs), 2), "평균": round(statistics.mean(xs), 2),
            "음수": sum(1 for x in xs if x < 0), "단위": unit}


def git_add_times() -> tuple:
    """캐시 파일이 **처음 커밋된 시각** 두 지도(HEAD · --all).

    944 와 **같은 명령**을 쓴다 — 고치는 것은 이 함수가 아니라 **소비 쪽의 우선순위**다.
    각 지도 안에서는 이미 「가장 이른 것」을 고른다(944 도 그랬다).
    """
    out: dict = {}
    for scope in ("HEAD", "--all"):
        cmd = ["git", "log", "--format=\x01%aI", "--name-only", "--diff-filter=A"]
        if scope == "--all":
            cmd.insert(2, "--all")
        cmd += ["--", "data/state/cache_*"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        cur = None
        m: dict = {}
        for line in r.stdout.splitlines():
            if line.startswith("\x01"):
                cur = line[1:]
            elif line.strip():
                if line not in m or cur < m[line]:
                    m[line] = cur
        out[scope] = m
    return out["HEAD"], out["--all"]


def git_add_commits() -> tuple:
    """⑦ 용 — 경로 → (**가장 이른** 추가 커밋 hash, 시각) · 그리고 그 커밋이 origin/main 에 있나.

    `git_add_times()` 와 **다른 것을 반환한다**(시각이 아니라 커밋). 지도 자체를 파일로
    떨궈 clone 에서도 살리기 위해서다.
    """
    r = subprocess.run(
        ["git", "log", "--all", "--format=\x01%H %aI", "--name-only",
         "--diff-filter=A", "--", "data/state/cache_*"],
        capture_output=True, text=True, timeout=1800)
    cur = ("", "")
    m: dict = {}
    for line in r.stdout.splitlines():
        if line.startswith("\x01"):
            h, t = line[1:].split(" ", 1)
            cur = (h, t)
        elif line.strip():
            if line not in m or cur[1] < m[line][1]:
                m[line] = cur
    in_main = set()
    for h in {v[0] for v in m.values()}:
        rc = subprocess.run(["git", "merge-base", "--is-ancestor", h, "origin/main"],
                            capture_output=True).returncode
        if rc == 0:
            in_main.add(h)
    return m, in_main


def pick_old(head: dict, allm: dict, key: str):
    """🔴 **고친 것** — 둘 다 있으면 **이른 쪽**. 없으면 있는 쪽. 둘 다 없으면 None.

    반환: (시각ISO 또는 None, 범위표)
    """
    a, b = head.get(key), allm.get(key)
    if a and b:
        return (a, "둘 다(HEAD 채택)") if a <= b else (b, "둘 다(--all 채택)")
    if a:
        return a, "HEAD 만"
    if b:
        return b, "--all 만"
    return None, "🔴 미추적"


def pick_or(head: dict, allm: dict, key: str):
    """944 가 쓰던 것 — `head or all`. 재현용으로 **그대로** 둔다."""
    return head.get(key) or allm.get(key)


def page_obs(kind: str, blob) -> list:
    keys = PAGE_O[kind]
    res = []
    try:
        rows = (blob["data"]["Page"]["media"] if kind == "anilist"
                else blob["body"]["result"]["contents"])
    except (KeyError, TypeError):
        return res
    if not isinstance(rows, list):
        return res
    for m in rows:
        if isinstance(m, dict) and "id" in m:
            res.append((m["id"], {k: m.get(k) for k in keys if m.get(k) is not None}))
    return res


def main() -> dict:                                       # noqa: PLR0912, PLR0915
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    git_head, git_all = git_add_times()

    # ── ⑤·⑥ 지도 자체의 전/후 ────────────────────────────────────────────
    both = set(git_head) & set(git_all)
    earlier_in_all = [k for k in both if git_all[k] < git_head[k]]
    head_wins = [k for k in both if git_head[k] < git_all[k]]      # P5 — 0 이어야 한다
    disk = [str(p.relative_to(ROOT))
            for d in sorted((ROOT / "data/state").glob("cache_*")) if d.is_dir()
            for p in sorted(d.iterdir()) if p.is_file()]
    disk_set = set(disk)
    only_mtime_after = sorted(disk_set - set(git_all))              # P4
    only_mtime_before = sorted(disk_set - set(git_head) - set(git_all))
    map_stat = {
        "HEAD 지도 크기": len(git_head), "--all 지도 크기": len(git_all),
        "둘 다 든 경로": len(both),
        "🔴 --all 이 더 이른 경로(= or 이 버리던 것)": len(earlier_in_all),
        "🔴 P5 HEAD 가 더 이른 경로": len(head_wins),
        "HEAD 만 든 경로": len(set(git_head) - set(git_all)),
        "--all 만 든 경로": len(set(git_all) - set(git_head)),
        "디스크 캐시 파일": len(disk),
        "🔴 P4 고친 뒤에도 mtime 만 아는 파일": len(only_mtime_after),
        "(참고) 고치기 전 mtime 만 알던 파일": len(only_mtime_before),
        "HEAD 지도의 서로 다른 커밋 시각": len(set(git_head.values())),
        "--all 지도의 서로 다른 커밋 시각": len(set(git_all.values())),
    }

    # ── 목록 페이지 → id → [(mtime, 값, 경로)] ──────────────────────────────
    page_seq: dict = defaultdict(dict)
    for dom, (dirs, kind, _idk) in PAGE_JOIN.items():
        seq = page_seq[dom]
        for d in dirs:
            dp = ROOT / d
            if not dp.exists():
                continue
            for f in sorted(dp.glob("*.json")):
                try:
                    blob = json.loads(f.read_text())
                except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                    continue
                mt = round(f.stat().st_mtime)
                rel = str(f.relative_to(ROOT))
                for i, ov in page_obs(kind, blob):
                    seq.setdefault(i, []).append((mt, ov, rel))

    # ── ① 레코드마다 시각 · 전후 두 값 ────────────────────────────────────
    mtime_cache: dict = {}

    def mt_of(f: Path) -> int:
        s = str(f)
        if s not in mtime_cache:
            mtime_cache[s] = round(f.stat().st_mtime)
        return mtime_cache[s]

    tot = tot_any = 0
    scope_before: Counter = Counter()
    scope_after: Counter = Counter()
    changed_rec = 0
    lag_before, lag_after = [], []
    gitmap_rec: dict = {}
    per: dict = {}
    for path, dom in STORES.items():
        d = json.loads((ROOT / path).read_text())
        recs = [v for v in d.values() if isinstance(v, dict)]
        tot += len(recs)
        n_any = n_chg = 0
        for v in recs:
            pts = []
            for cdir, pat in DIRECT_JOIN.get(dom, []):
                try:
                    nm = pat.format(**v)
                except (KeyError, IndexError):
                    continue
                f = ROOT / cdir / nm
                if f.exists():
                    pts.append((mt_of(f), cdir + "/" + nm, "직접"))
            if dom in PAGE_JOIN:
                key = v.get(PAGE_JOIN[dom][2])
                for ts, _ov, src in page_seq[dom].get(key, []):
                    pts.append((ts, src, "목록"))
            if not pts:
                continue
            pts.sort()
            n_any += 1
            src = pts[0][1]
            g_before = pick_or(git_head, git_all, src)
            g_after, scope = pick_old(git_head, git_all, src)
            scope_before["HEAD" if git_head.get(src) else
                         ("--all" if git_all.get(src) else "🔴 미추적")] += 1
            scope_after[scope] += 1
            if g_before != g_after:
                n_chg += 1
            if g_before:
                lag_before.append((to_epoch(g_before) - pts[0][0]) / 3600)
            if g_after:
                lag_after.append((to_epoch(g_after) - pts[0][0]) / 3600)
            gitmap_rec[v.get("record_id")] = {
                "도": dom, "출처": src, "mtime": iso(pts[0][0]),
                "git최초커밋(고친 뒤)": g_after, "범위": scope,
                "git최초커밋(944 · or)": g_before,
            }
        tot_any += n_any
        changed_rec += n_chg
        per[dom] = {"레코드(분모)": len(recs), "시각이 붙은 레코드": n_any,
                    "🔴 전/후가 다른 레코드": n_chg}

    # ── ②·③ 만화 두 점 ───────────────────────────────────────────────────
    mg = json.loads((ROOT / "data/state/manga_records.json").read_text())
    mg_recs = [v for v in mg.values() if isinstance(v, dict)]
    pair_n = 0
    diff_commit_before = diff_commit_after = 0
    untracked_pair = 0
    gap_git, gap_mtime = [], []
    for v in mg_recs:
        rows = page_seq["만화"].get(v.get("media_id"), [])
        if not rows:
            continue
        rows = sorted(rows, key=lambda x: x[0])
        if len({t for t, _, _ in rows}) < 2:
            continue
        a, b = rows[0], rows[-1]
        o1, o2 = a[1].get("popularity"), b[1].get("popularity")
        if o1 is None or o2 is None or o1 == o2:
            continue
        pair_n += 1
        c1b = pick_or(git_head, git_all, a[2])
        c2b = pick_or(git_head, git_all, b[2])
        c1a, _s1 = pick_old(git_head, git_all, a[2])
        c2a, _s2 = pick_old(git_head, git_all, b[2])
        diff_commit_before += bool(c1b and c2b and c1b != c2b)
        diff_commit_after += bool(c1a and c2a and c1a != c2a)
        if not (c1a and c2a):
            untracked_pair += 1
        if c1a and c2a:
            gap_git.append((to_epoch(c2a) - to_epoch(c1a)) / 3600)
        gap_mtime.append((b[0] - a[0]) / 3600)

    pairs = {
        "분모 — popularity 가 달라진 만화 레코드": pair_n,
        "🔴 P1′ 전(or) 출처가 다른 커밋": diff_commit_before,
        "🔴 P1  후(min) 출처가 다른 커밋": diff_commit_after,
        "두 출처 중 하나라도 미추적": untracked_pair,
        "🔴 P2  두 커밋 간격(시간)": dist(gap_git),
        "🔴 P2′ mtime 간격(시간)": dist(gap_mtime),
    }

    # ── ⑦ clone 해도 사는 근거 파일 ───────────────────────────────────────
    gm_meta = {
        "노트": 945, "레인": "수리",
        "무엇": "D2 아홉 저장소 레코드의 **git 최초추가 시각**(--all 포함) 지도",
        "🔴 왜 이 파일인가": "티처 #84 는 `archive/pre-github` 를 origin 에 밀면 근거가 산다고 "
                        "처방했다. 밀어 봤더니 **GitHub 이 거부했다**(pre-receive: "
                        "data/state/funding_pool.json 142.97MB > 100MB 한도). "
                        "그래서 브랜치 대신 **지도 자체를 커밋한다** — 이 파일은 clone 에 산다",
        "만든 시각": t_start, "만든 러너": "runners/out945_obstime.py",
        "분모": tot, "실린 레코드": len(gitmap_rec),
    }
    GITMAP.write_text(json.dumps({"_meta": gm_meta, "레코드": gitmap_rec},
                                 ensure_ascii=False, indent=0))

    # ⑦′ 🔴 캐시 파일 전량의 최초추가 지도 — **archive/pre-github 의 정보 백업**.
    add_c, in_main = git_add_commits()
    commits = sorted({v for v in add_c.values()}, key=lambda x: x[1])
    cidx = {c[0]: i for i, c in enumerate(commits)}
    cm_files: dict = {}
    for p, (h, _t) in add_c.items():
        fp = ROOT / p
        cm_files[p] = [cidx[h], mt_of(fp) if fp.exists() else None]
    outside = sum(1 for h, _t in add_c.values() if h not in in_main)
    CACHEMAP.write_text(json.dumps({
        "_meta": {
            "노트": 945, "레인": "수리", "만든 시각": t_start,
            "만든 러너": "runners/out945_obstime.py",
            "무엇": "data/state/cache_* 전량의 **git 최초추가 커밋**(모든 ref 기준) + mtime",
            "🔴 왜": f"이 지도의 {outside}/{len(add_c)} 은 **origin/main 에 없는 커밋**을 "
                  "가리킨다 — 그 커밋들은 로컬 `archive/pre-github` 에만 있고 "
                  "GitHub 이 그 브랜치를 100MB 한도로 **거부**했다. 이 파일이 그 "
                  "정보의 clone 가능한 사본이다",
            "읽는 법": "파일[경로] = [커밋목록 인덱스, mtime(epoch초)]",
            "파일 수": len(add_c),
            "🔴 origin/main 밖 커밋을 가리키는 파일": outside,
        },
        "커밋목록": [{"h": h, "t": t, "origin/main 에 있나": h in in_main}
                 for h, t in commits],
        "파일": cm_files,
    }, ensure_ascii=False, indent=0))
    map_stat["🔴 최초추가가 origin/main 밖 커밋인 파일"] = outside
    map_stat["최초추가 커밋 수(모든 ref)"] = len(commits)
    map_stat["그중 origin/main 에 있는 커밋"] = sum(
        1 for h, _t in commits if h in in_main)

    res = {
        "노트": 945, "레인": "🔴 수리",
        "물음": "`git_head or git_all` 을 `min` 으로 고치면 무엇이 달라지나",
        "🔴 스탬프": {
            "시작 시각": t_start,
            "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256(저장소 아홉)": {k: sha(ROOT / k) for k in STORES},
            "코드 sha256": {"runners/out945_obstime.py":
                          sha(ROOT / "runners/out945_obstime.py")},
        },
        "🔴 조항 60 — 명령·범위·트리": {
            "명령": "python3 runners/out945_obstime.py",
            "범위(저장소)": list(STORES),
            "범위(git)": "git log [--all] --diff-filter=A -- data/state/cache_*",
            "트리": "작업 트리만 읽는다(인덱스와 안 섞는다). 커밋 시각만 이력에서 읽는다",
        },
        "🔴 지도 전/후": map_stat,
        "🔴 레코드 전/후": {
            "분모 D2": tot, "시각이 붙은 레코드": tot_any,
            "🔴 git 시각이 달라진 레코드": changed_rec,
            "범위 분포(944 · or)": dict(scope_before),
            "범위 분포(945 · min)": dict(scope_after),
            "git−mtime 시차(944 · or)": dist(lag_before),
            "🔴 P3 git−mtime 시차(945 · min)": dist(lag_after),
            "저장소별": per,
        },
        "🔴 만화 두 점": pairs,
        "떨군 산출물": {
            str(GITMAP.relative_to(ROOT)): {"레코드": len(gitmap_rec),
                                            "바이트": GITMAP.stat().st_size},
            str(CACHEMAP.relative_to(ROOT)): {"파일": len(cm_files),
                                              "바이트": CACHEMAP.stat().st_size},
        },
        "🔴 못 한 것": [
            f"`--all` 이 모르는 디스크 캐시 파일 {len(only_mtime_after)}개는 "
            "고친 뒤에도 mtime 이 유일한 근거다 — 이 러너는 그것을 세기만 한다",
            "`archive/pre-github` 는 origin 이 거부했다(147MB blob) — 밀지 못했다",
        ],
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
