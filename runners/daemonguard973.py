#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""973 --- 🔴🔴 **사고 대응**: 규칙 A 가 증거를 파괴한 기전을 **심어서** 재현하고 막는다.

## 무슨 일이 났나 (실측)
데몬 커밋 **`1ea516fbad8d8b398a02a57a730f99484e973d00`**(2026-08-16T00:10:02)가
`data/lab/denominator.json` 에서 **11 줄을 지운 채** 커밋했다 → 원장 **1121 → 1120** ·
티처 #111 항목 소실. 데몬의 `PATHS` 는 `data/ingest`·`data/state` 뿐인데
**`data/lab/` 을 건드렸다.**

## 🔴 기전 (이 러너가 심어서 재현한다)
1. v4.0 **규칙 A** 는 「원장은 배관으로만 · `checkout` 금지」다. 배관으로 쓰면
   **HEAD 는 새 blob 인데 디스크와 인덱스는 옛 blob** 이다.
2. 데몬의 `_commit()` 은 `git add -- data/ingest data/state` 로 **PATHS 만 스테이지**한다.
   🔴 **그런데 다음 줄의 `git diff --cached --name-only` 에는 경로 제한이 없다.**
   그 명령은 **인덱스 ↔ HEAD 전량**을 견주므로, 배관 쓰기로 HEAD 만 앞서 나간
   `data/lab/denominator.json` 이 「스테이지된 것」 목록에 **끼어든다.**
3. 그 목록이 그대로 `git commit -- <목록>` 에 들어가 **옛 blob 이 커밋된다.**

🔴 **`PATHS` 는 `add` 에만 물고 `commit` 목록에는 안 물었다.** 그것이 이 사고다.

씀:
    python3 runners/daemonguard973.py --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import runners.predict971 as P                                    # noqa: E402

RAN = ("runners/daemonguard973.py", "runners/predict971.py")
DAEMON = "runners/harvest_daemon.py"
INCIDENT = "1ea516fbad8d8b398a02a57a730f99484e973d00"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sh(args, cwd):
    p = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def ran_vs_blob(ref: str) -> dict:
    per, bad = {}, []
    for r in RAN:
        disk = P._sha_file(ROOT / r) if (ROOT / r).is_file() else None
        blob = P.blob_sha(ref, r)
        ok = bool(disk is not None and disk == blob)
        per[r] = {"디스크 sha256": disk, "커밋 blob sha256": blob, "일치": ok}
        if not ok:
            bad.append(r)
    fixed = bool(len(ref) == 40 and all(c in "0123456789abcdef" for c in ref.lower()))
    return {"기준 ref(준 대로)": ref, "🔴 40자 고정 sha 인가": fixed, "러너별": per,
            "🔴 분자/분모": "%d / %d" % (len(RAN) - len(bad), len(RAN)),
            "🔴 어긋난 러너": bad, "🔴 F5 통과": bool(not bad and fixed)}


def incident() -> dict:
    """🔴 사고 커밋이 실제로 무엇을 건드렸나 --- git 에서 읽는다(손 전사 아님)."""
    c, o = sh(["git", "-c", "core.quotePath=false", "show", "--numstat",
               "--format=%H%n%cI%n%s", INCIDENT], ROOT)
    lines = [x for x in o.split("\n") if x.strip()]
    files = []
    for x in lines[3:]:
        m = re.match(r"^(\d+|-)\t(\d+|-)\t(.+)$", x)
        if m:
            files.append({"더한 줄": m.group(1), "지운 줄": m.group(2), "경로": m.group(3)})
    paths = [f["경로"] for f in files]
    daemon_paths = ["data/ingest", "data/state"]
    outside = [p for p in paths if not any(p.startswith(d + "/") for d in daemon_paths)]
    return {
        "🔴 사고 커밋": lines[0] if lines else None,
        "언제": lines[1] if len(lines) > 1 else None,
        "메시지": lines[2] if len(lines) > 2 else None,
        "건드린 파일": files,
        "🔴 데몬 PATHS": daemon_paths,
        "🔴🔴 PATHS 밖 파일": {"목록": outside,
                        "🔴 분자/분모": "%d / %d" % (len(outside), len(paths))},
    }


def plant() -> dict:
    """🔴🔴 **심어서 잰다** --- 임시 저장소에서 규칙 A 상황을 그대로 만든다."""
    res = collections.OrderedDict()
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        sh(["git", "init", "-q", "-b", "main"], d)
        sh(["git", "config", "user.email", "t@t"], d)
        sh(["git", "config", "user.name", "t"], d)
        (d / "data/ingest").mkdir(parents=True)
        (d / "data/state").mkdir(parents=True)
        (d / "data/lab").mkdir(parents=True)
        (d / "data/lab/ledger.json").write_text("OLD\n", encoding="utf-8")
        (d / "data/ingest/a.json").write_text("1\n", encoding="utf-8")
        sh(["git", "add", "-A"], d)
        sh(["git", "commit", "-q", "-m", "base"], d)

        # ── 규칙 A: 배관으로 원장만 앞세운다(디스크·인덱스는 그대로) ──
        blob = sh(["git", "hash-object", "-w", "--stdin"], d)
        p = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=str(d),
                           input=b"NEW\n", capture_output=True)
        nb = p.stdout.decode().strip()
        env = dict(os.environ, GIT_INDEX_FILE=str(d / ".tmpidx"))
        subprocess.run(["git", "read-tree", "HEAD"], cwd=str(d), env=env,
                       capture_output=True)
        subprocess.run(["git", "update-index", "--cacheinfo",
                        "100644,%s,data/lab/ledger.json" % nb], cwd=str(d), env=env,
                       capture_output=True)
        tree = subprocess.run(["git", "write-tree"], cwd=str(d), env=env,
                              capture_output=True).stdout.decode().strip()
        head = sh(["git", "rev-parse", "HEAD"], d)[1].strip()
        newc = subprocess.run(["git", "commit-tree", tree, "-p", head, "-m", "plumb"],
                              cwd=str(d), capture_output=True).stdout.decode().strip()
        sh(["git", "update-ref", "refs/heads/main", newc], d)
        res["① 배관 쓰기 뒤 HEAD 의 원장"] = sh(
            ["git", "show", "HEAD:data/lab/ledger.json"], d)[1].strip()
        res["① 디스크의 원장"] = (d / "data/lab/ledger.json").read_text().strip()
        res["🔴 ① HEAD 와 디스크가 갈렸나"] = bool(
            res["① 배관 쓰기 뒤 HEAD 의 원장"] != res["① 디스크의 원장"])

        # ── 데몬 한 회차: 새 수집물이 생긴다 ──
        (d / "data/ingest/b.json").write_text("2\n", encoding="utf-8")
        PATHS = ["data/ingest", "data/state"]
        sh(["git", "add", "--"] + PATHS, d)
        # 🔴🔴🔴 **988 `[수리] R5`** --- `⑤′` 절 1-나 의 «순㉯»(막는 것이 아무것도 없는
        #    날 것 git 호출) 두 자리다. 985·986·987 셋 다 미뤘다.
        #    🔴 **`-c core.quotePath=false` + `-z` 로 고친다** --- 한글 경로가 8진
        #    이스케이프로 어긋나던 자리이고(조항 62 · 노트 946), 여기서 재현하는 것은
        #    「`-- PATHS` 를 안 물린 것」이지 「경로 이스케이프」가 아니므로
        #    **이 고침은 재현 대상을 한 글자도 안 바꾼다.**
        old_list = [x for x in sh(["git", "-c", "core.quotePath=false", "diff",
                                   "--cached", "--name-only", "-z"],
                                  d)[1].split("\0") if x.strip()]
        new_list = [x for x in sh(["git", "-c", "core.quotePath=false", "diff",
                                   "--cached", "--name-only", "-z", "--"]
                                  + PATHS, d)[1].split("\0") if x.strip()]
        res["② 옛 판(`diff --cached --name-only`)이 커밋에 넘기는 목록"] = old_list
        res["② 새 판(같은 명령 + `-- PATHS`)이 넘기는 목록"] = new_list
        res["🔴🔴 ② 옛 판이 PATHS 밖을 끌어들이나"] = bool(
            any(not any(x.startswith(q + "/") for q in PATHS) for x in old_list))
        res["🔴🔴 ② 새 판이 PATHS 밖을 끌어들이나"] = bool(
            any(not any(x.startswith(q + "/") for q in PATHS) for x in new_list))

        # ── 옛 판으로 커밋하면 원장이 정말 되돌아가나 ──
        sh(["git", "commit", "-q", "-m", "daemon(old)", "--"] + old_list, d)
        res["③ 옛 판으로 커밋한 뒤 HEAD 의 원장"] = sh(
            ["git", "show", "HEAD:data/lab/ledger.json"], d)[1].strip()
        res["🔴🔴🔴 ③ 원장이 옛 값으로 되돌아갔나"] = bool(
            res["③ 옛 판으로 커밋한 뒤 HEAD 의 원장"] == "OLD")
    return res


def source_check() -> dict:
    """🔴 `harvest_daemon.py` 가 실제로 고쳐졌나 --- 소스에서 읽는다."""
    src = (ROOT / DAEMON).read_text(encoding="utf-8")
    i = src.find('"diff", "--cached"')
    seg = src[i:i + 160] if i >= 0 else ""
    return {
        "파일": DAEMON,
        "🔴 `diff --cached` 에 경로 제한이 붙었나": bool("PATHS" in seg.split("[1]")[0]),
        "그 자리 원문": (seg.split("[1]")[0] if i >= 0 else "🔴 못 찾았다"),
        "🔴 `staged` 를 PATHS 로 한 번 더 거르나": bool("_only_paths" in src),
        "sha256": P._sha_file(ROOT / DAEMON),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", default="/Users/ax/wm_harvest/973/out973_daemonguard.json")
    a = ap.parse_args()
    R = collections.OrderedDict()
    R["🔴 노트"] = 973
    R["🔴 레인"] = "수리"
    R["🔴🔴🔴 무엇"] = ("🔴 **v4.0 규칙 A 가 증거를 파괴했다.** 규칙 A(배관만·checkout 금지)를 "
                  "지키면 HEAD 와 디스크·인덱스가 갈리고, 데몬의 `_commit()` 이 그 차이를 "
                  "쓸어 담는다. **v4.0 이 등록된 지 두 사이클 만에 자기 규칙이 물었다.**")
    R["🔴 시작(UTC)"] = _now()
    R["🔴🔴 §S 돌린 러너 ↔ 커밋 blob(F5)"] = ran_vs_blob(a.ref)
    R["🔴🔴 §I 사고 실측"] = incident()
    R["🔴🔴🔴 §X 심어서 재현"] = plant()
    R["🔴🔴 §G 고침이 소스에 있나"] = source_check()
    R["🔴 고침 둘"] = {
        "① `docs/루프.md` 규칙 A": "「배관으로 원장을 쓴 뒤 디스크 사본을 그 커밋본으로 되맞춘다」를 더한다",
        "② `runners/harvest_daemon.py`": ("`git diff --cached --name-only` 에 `-- PATHS` 를 물리고, "
                                        "`staged` 를 PATHS 로 **한 번 더** 거른다(두 겹)"),
        "🔴 못 한 것": ("돌고 있는 데몬(PID 70251)은 **옛 코드를 메모리에 들고 있다** --- "
                   "규칙 B 때문에 안 죽였다. 고침은 **다음 기동부터** 문다. "
                   "🔴 그때까지는 「배관으로 main 을 움직인 뒤 디스크를 되맞춘다」가 유일한 방패다"),
    }
    R["🔴 끝(UTC)"] = _now()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(a.out)


if __name__ == "__main__":
    main()
