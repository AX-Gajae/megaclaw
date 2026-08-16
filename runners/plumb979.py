# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""979 — 🔴 규칙 A 배관 커밋. `checkout` 을 안 쓴다.

  python3 runners/plumb979.py --branch note/979-... --msg <파일> <경로>...

디스크의 <경로> 를 blob 으로 굽고, 가지 끝 트리에 얹어 새 커밋을 만든 뒤 ref 를 옮긴다.
🔴 작업 트리·인덱스를 안 만진다(데몬과 안 부딪힌다).
"""
import argparse
import os
import subprocess
import sys
import tempfile

ROOT = os.environ.get("WM_ROOT", "/Users/ax/world_model")


def g(*a, **k):
    return subprocess.check_output(["git"] + list(a), cwd=ROOT, **k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", required=True)
    ap.add_argument("--msg", required=True)
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args()
    ref = "refs/heads/" + a.branch
    parent = g("rev-parse", ref).decode().strip()
    idx = tempfile.NamedTemporaryFile(suffix=".idx", delete=False).name
    os.unlink(idx)
    env = dict(os.environ, GIT_INDEX_FILE=idx)
    g("read-tree", parent, env=env)
    for p in a.paths:
        full = os.path.join(ROOT, p)
        if not os.path.isfile(full):
            g("update-index", "--force-remove", p, env=env)
            continue
        sha = g("hash-object", "-w", "--", full).decode().strip()
        mode = "100755" if os.access(full, os.X_OK) else "100644"
        g("update-index", "--add", "--cacheinfo", "%s,%s,%s" % (mode, sha, p),
          env=env)
    tree = g("write-tree", env=env).decode().strip()
    os.unlink(idx)
    if tree == g("rev-parse", parent + "^{tree}").decode().strip():
        print("NOCHANGE", parent)
        return 0
    with open(a.msg, "rb") as f:
        msg = f.read()
    new = subprocess.check_output(
        ["git", "commit-tree", tree, "-p", parent], cwd=ROOT,
        input=msg).decode().strip()
    g("update-ref", ref, new, parent)
    print(new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
