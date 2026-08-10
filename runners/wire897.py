"""노트 897 · 0단계 **배선 그래프** — 조각이 서로 닿는가를 **세어서** 답한다.

*"연결돼 있나"* 를 눈으로 읽지 않는다. 저장소 전 `.py` 를 AST 로 파싱해
**누가 누구를 반입하나**를 세고, 축 이름(`field_spread_ff` · `text_nn`)이 같은
파일에 함께 나타나는 일이 있는지도 센다.

산출물 `runners/out897_graph.json` 을 그림이 읽는다(손 전사 금지 · 루프 ⑥).
"""
from __future__ import annotations

import ast
import collections
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()
OUT = ROOT / "runners/out897_graph.json"

SKIP = {".git", "paper/build", "data", "node_modules", ".venv"}

#: 0단계가 세라고 한 조각들
PIECES = ["state.fieldmodel", "state.shared_encoder", "state.foundation",
          "state.encoder", "state.masked_encoder", "state.transfer_eval",
          "state.slots", "state.fewshot", "lab.textnn", "lab.joint",
          "state.tri_domain", "lab.forms", "lab.harness"]

AXES = ["field_spread_ff", "text_nn"]


def stamp() -> dict:
    h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                       capture_output=True, text=True).stdout.strip()
    return {"git HEAD": h, "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "코드 sha(wire897.py)": hashlib.sha256(ME.read_bytes()).hexdigest()[:16]}


def scan():
    files, edges = [], collections.defaultdict(set)
    for dp, dns, fns in os.walk(ROOT):
        rel = os.path.relpath(dp, ROOT)
        if any(rel == s or rel.startswith(s + os.sep) for s in SKIP):
            dns[:] = []
            continue
        dns[:] = [d for d in dns if not d.startswith(".")]
        files += [os.path.join(dp, f) for f in fns if f.endswith(".py")]
    txt = {}
    for p in files:
        rel = os.path.relpath(p, ROOT)
        mod = rel[:-3].replace("/", ".")
        try:
            src = Path(p).read_text(encoding="utf8")
            tree = ast.parse(src)
        except Exception:
            continue
        txt[mod] = src
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    edges[mod].add(a.name)
            elif isinstance(n, ast.ImportFrom):
                base = n.module or ""
                if n.level:
                    pkg = mod.rsplit(".", 1)[0]
                    base = (pkg + "." + base).strip(".") if base else pkg
                edges[mod].add(base)
                for a in n.names:
                    edges[mod].add(base + "." + a.name)
    return len(files), edges, txt


def main():
    nfile, edges, txt = scan()
    rev = {t: set() for t in PIECES}
    for m, ds in edges.items():
        for d in ds:
            for t in PIECES:
                if d == t or d.startswith(t + "."):
                    rev[t].add(m)
    callers = {t: sorted(rev[t]) for t in PIECES}

    #: 🔴 핵심 물음 — **장 인코더와 텍스트 인코더를 같이 부르는 파일이 있나**
    fm = set(callers["state.fieldmodel"])
    tn = set(callers["lab.textnn"])
    se = set(callers["state.shared_encoder"]) | set(callers["state.foundation"])
    ax_files = {a: sorted(m for m, s in txt.items() if a in s) for a in AXES}

    out = {
        "stamp": stamp(), "파이썬 파일 수": nfile,
        "조각별 호출자": callers,
        "조각별 호출자 수": {t: len(v) for t, v in callers.items()},
        "🔴 아무도 안 부르는 조각": [t for t, v in callers.items() if not v],
        "🔴 장 ∩ 텍스트(같은 파일이 둘 다 반입)": sorted(fm & tn),
        "🔴 장 ∩ 공유인코더·파운데이션": sorted(fm & se),
        "축 이름이 나오는 파일": ax_files,
        "🔴 두 축 이름이 같이 나오는 파일":
            sorted(set(ax_files["field_spread_ff"]) & set(ax_files["text_nn"])),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: out[k] for k in out if k.startswith("🔴")},
                     ensure_ascii=False, indent=1))
    print("→", OUT)


if __name__ == "__main__":
    main()
