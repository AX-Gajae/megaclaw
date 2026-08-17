#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""987 배관 커밋기 — 🔴 규칙 A: `checkout` 없이 가지에 쓴다.

`git show <ref>:<path>` → 고치기 → `hash-object -w` → 임시 인덱스에 `read-tree`
+ `update-index --cacheinfo` → `write-tree` → `commit-tree -p` → `update-ref`.

씀:
    python3 runners/plumb987.py --branch note/987-… --msg-file /tmp/m.txt <경로> …
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
BR = "refs/heads/note/987-ceiling-identity-fixed-ref"


def _g(args, env=None, binary=False):
    p = subprocess.run(["git", "-c", "core.quotePath=false"] + args, cwd=str(ROOT),
                       capture_output=True, env=env)
    if p.returncode != 0:
        raise RuntimeError("git %s -> %d: %s" % (args[:2], p.returncode,
                                                 p.stderr.decode("utf-8", "replace")[:400]))
    return p.stdout if binary else p.stdout.decode("utf-8")


def commit(branch, paths, msg_file):
    head = _g(["rev-parse", branch]).strip()
    idx = tempfile.NamedTemporaryFile(delete=False, suffix=".idx").name
    os.unlink(idx)
    env = dict(os.environ, GIT_INDEX_FILE=idx)
    _g(["read-tree", head], env=env)
    added, removed = [], []
    for rel in paths:
        p = ROOT / rel
        if not p.is_file():
            _g(["update-index", "--force-remove", "--", rel], env=env)
            removed.append(rel)
            continue
        blob = _g(["hash-object", "-w", "--", str(p)]).strip()
        mode = "100755" if os.access(str(p), os.X_OK) else "100644"
        _g(["update-index", "--add", "--cacheinfo", "%s,%s,%s" % (mode, blob, rel)], env=env)
        added.append(rel)
    tree = _g(["write-tree"], env=env).strip()
    os.unlink(idx)
    new = _g(["commit-tree", tree, "-p", head, "-F", msg_file]).strip()
    _g(["update-ref", branch, new, head])
    return {"branch": branch, "before": head, "after": new, "tree": tree,
            "added": added, "removed": removed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default=BR)
    ap.add_argument("--msg-file", required=True)
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args()
    r = commit(a.branch, a.paths, a.msg_file)
    print("%s  %s -> %s  (+%d/-%d)" % (r["branch"], r["before"][:9], r["after"][:9],
                                       len(r["added"]), len(r["removed"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
