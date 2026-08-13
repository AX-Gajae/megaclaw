# -*- coding: utf-8 -*-
"""노트 959 — **배선 검사**(사전등록 §5). 🔴 **측정 전에 돌린다.**

각 검사가 `통과` 키를 낸다(958 이 데인 자리 — 키가 없으면 계수기에서 조용히 사라진다).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import runners.grow959 as G                                     # noqa: E402
import runners.layers957 as L                                   # noqa: E402

OUT = ROOT / "runners/out959_wiring.json"

#: 판 라벨 파일 — 이 사이클이 한 비트도 안 여는 것들
LABEL_HINTS = ("holdout", "유보", "label", "라벨", "denominator.json")


def sh(*cmd) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def main() -> dict:
    W: dict = {}

    tg, meta = G.targets_wide()
    W["W1 넓힌 표적이 문서 해결 수와 같은가"] = {
        "분자: 넓힌 표적": len(tg),
        "분모: 문서가 해결된 개체": meta["분모: wiki_views 파일"] - meta["문서 미해결"] - meta["못 읽은 파일"],
        "접두사를 모르는 개체": meta["🔴 접두사를 모르는 개체"],
        "시작일 없는 표적": meta["시작일 없는 표적"],
        "옛 표적(유보 잠금)": meta["옛 표적(유보 잠금)"],
        "🔴 잠금 배수": len(tg) / meta["옛 표적(유보 잠금)"],
        "통과": bool(meta["🔴 접두사를 모르는 개체"] == 0
                   and meta["시작일 없는 표적"] == 0
                   and len(tg) == meta["분모: wiki_views 파일"] - meta["문서 미해결"] - meta["못 읽은 파일"]),
    }

    # W2 — 판 라벨을 안 연다
    try:
        L.assert_no_label_files()
        no_label = True
        err = None
    except Exception as e:                                       # noqa: BLE001
        no_label, err = False, repr(e)
    # 🔴 **초판의 이 검사는 거짓 붉음을 냈다.** 낱말(`유보`·`라벨`·`label`)을 소스 전체에서
    #    찾았더니 **독스트링과 주석**에 걸렸다 — 이 러너는 그 낱말을 *설명*할 뿐 그 파일을
    #    안 연다. 「낱말이 있다」와 「파일을 연다」는 둘이다(조항 59).
    #    고친 자: **경로처럼 생긴 문자열 리터럴**만 본다.
    import re
    src = (ROOT / "runners/grow959.py").read_text()
    lits = re.findall(r'"([^"\n]*/[^"\n]*)"', src) + re.findall(r"'([^'\n]*/[^'\n]*)'", src)
    hits = sorted({s for s in lits if any(h in s for h in LABEL_HINTS)})
    W["W2 판 라벨을 여는가"] = {
        "🔴 자": "경로처럼 생긴 문자열 리터럴만 본다(초판은 낱말을 봐서 거짓 붉음을 냈다)",
        "assert_no_label_files 통과": no_label, "예외": err,
        "분모: 경로 리터럴": len(set(lits)), "경로 리터럴": sorted(set(lits)),
        "🔴 라벨 경로": hits,
        "통과": bool(no_label and not hits)}

    # W3 — 쌍 파일을 읽는 코드에 판 하네스가 있는가 (전수 grep)
    out = sh("git", "-c", "core.quotePath=false", "grep", "-l",
             "-e", "sao941", "-e", "sao959", "-e", "pairs.jsonl", "HEAD", "--", "*.py")
    files = sorted({l.split(":", 1)[1] for l in out.splitlines() if ":" in l})
    harness = [f for f in files if f.startswith(("harness/", "lab/"))]
    W["W3 쌍을 읽는 코드에 판 하네스가 있나"] = {
        "명령": "git -c core.quotePath=false grep -l -e sao941 -e sao959 -e pairs.jsonl HEAD -- '*.py'",
        "분모: 쌍을 읽는 .py": len(files), "파일": files,
        "🔴 그중 harness/ 또는 lab/": harness,
        "통과": bool(files and not harness)}

    # W4 — 옛 수확물의 기준 해시(수확 뒤에 다시 대조한다)
    W["W4 옛 wiki_daily 기준 sha256(앞16)"] = {
        "파일별": G.sha_dir(G.OLDDIR),
        "분모: 파일": len(G.sha_dir(G.OLDDIR)),
        "통과": bool(G.sha_dir(G.OLDDIR))}

    # W5 — 941 쌍 파일의 기준 해시
    W["W5 941 쌍 기준 sha256(앞16)"] = {
        "값": hashlib.sha256(G.OLDPAIRS.read_bytes()).hexdigest()[:16],
        "통과": G.OLDPAIRS.exists()}

    # W8 — 얼린 957 입력
    FR = ROOT / "data/frozen/957_inputs"
    man = json.loads((FR / "manifest.json").read_text())
    bad = []
    for rel, e in man["항목"].items():
        p = (FR / rel) if e["얼린 자리"] else (ROOT / e["원래 자리"])
        import gzip
        b = p.read_bytes()
        if p.suffix == ".gz":
            b = gzip.decompress(b)
        if hashlib.sha256(b).hexdigest() != e["🔴 내용 sha256(압축을 푼 것 · 정본)"]:
            bad.append(rel)
    W["W8 얼린 957 입력"] = {"분자: 맞은 파일": len(man["항목"]) - len(bad),
                        "분모: 명세의 파일": len(man["항목"]),
                        "어긋난 것": bad, "통과": not bad}

    # W9 — 데몬
    #: 🔴🔴 **R4(노트 966 · 티처 #104 M7)** — 이 자리는 `L.daemon_asleep()` 을 **진짜로
    #: 부르고 그 답을 버린 채** `"통과": True` 를 찍고 있었다. 조항 64 ① 의 정확한 꼴이다:
    #: 자유 이름이 하나도 판정에 안 들어가므로 **어떤 자료에서도 같은 값**이다.
    #: 저장소의 자 A 항진명제 69 중 하나이고, **진짜 측정 러너**의 자리라 값이 크다.
    _asleep = L.daemon_asleep()
    W["W9 데몬 상태"] = {
        "재웠나": _asleep,
        "🔴 무엇이면 떨어지나": "데몬이 깨어 있으면(재우지 않고 측정하면) 떨어진다",
        "통과": bool(_asleep)}

    n_pass = sum(1 for v in W.values() if v.get("통과"))
    R = {"노트": 959, "레인": "배선", "논문 스텝": 502,
         "사전등록": "docs/prereg_959_reach.md (커밋 4212af9ab)",
         "🔴 배선 검사": W,
         "🔴 분자: 통과한 검사": n_pass, "🔴 분모: 돌린 검사": len(W),
         "🔴 전부 통과": n_pass == len(W)}
    OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps(R, ensure_ascii=False, indent=1)[:3500])
    return R


if __name__ == "__main__":
    main()
