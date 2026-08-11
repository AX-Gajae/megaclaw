#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[탐색] 947 — **npz 두 이름을 누가 섞어 쓰는가** (티처 #86 3순위).

🔴 **사실 관계는 다시 안 잰다.** 티처와 주 세션이 이미 두 번 쟀다:
추적 `.npz` **10 전량**에서 ``zipfile.namelist()``(``X.npy``)와
``numpy.load().files``(``X``)가 완전히 갈리고, 모든 파일에서
``|zip−numpy| = |numpy−zip| = 전체 크기`` — git 의 215 와 **같은 서명**이다.

남은 물음은 하나: **누가 두 판독기를 섞어 쓰는가.** 그것을 **데이터 흐름**으로 따라간다.

| 절 | 무엇 |
|---|---|
| 가 | 판독기 등기부 — `.py` 전량에서 zip 쪽 / numpy 쪽 / **둘 다** |
| 나 | 🔴 **섞어 쓰는 파일**을 한 줄씩 — 같은 파일 안에서 두 이름이 만나나 |
| 다 | 🔴 **NFC/NFD** — 추적 경로에서 정규화가 갈리는 자리와 그것을 막는 코드 |

🔴 **규칙 1**: 이 산출물의 수치는 이 사이클의 결론·원장 표제·커밋/PR 제목에
**안 들어간다.** 다음 사이클의 후보가 될 뿐이다. 🔴 **판 ρ 를 안 부른다.**
"""
from __future__ import annotations

import ast
import collections
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab import keyspace as ks                                    # noqa: E402

OUT = ROOT / "runners" / "exp947_npzflow.json"

#: zip 쪽 이름 공간(`X.npy`)을 읽는 표현
ZIP_PAT = re.compile(r"\.namelist\(\)|ZipFile\(")
#: numpy 쪽 이름 공간(`X`)을 읽는 표현
NPY_PAT = re.compile(r"\.files\b|np\.load\(|numpy\.load\(|savez")


def readers() -> dict:
    pys = sorted(ks.git_paths("ls-files", "--", "*.py"))
    zip_only, npy_only, both, rows = [], [], [], {}
    for rel in pys:
        try:
            src = (ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        z = [i for i, ln in enumerate(src.split("\n"), 1) if ZIP_PAT.search(ln)]
        n = [i for i, ln in enumerate(src.split("\n"), 1) if NPY_PAT.search(ln)]
        if z and n:
            both.append(rel)
            rows[rel] = {"zip 쪽 줄": z, "numpy 쪽 줄": n}
        elif z:
            zip_only.append(rel)
        elif n:
            npy_only.append(rel)
    return {
        "검사": "가 판독기 등기부 — 누가 어느 이름 공간을 읽나",
        "🔴 분모 훑은 .py": len(pys),
        # 🔴 키 이름을 셋 다 「그 목록」으로 쓰면 **JSON 이 하나로 덮어쓴다** ---
        #    이 세션이 티처 #86 을 검증할 때 실제로 그렇게 「NUL 0」을 얻었다(조항 59).
        "🔴 zip 쪽만(`namelist()` → `X.npy`)": len(zip_only), "zip 쪽만 목록": zip_only,
        "🔴 numpy 쪽만(`np.load().files` → `X`)": len(npy_only),
        "numpy 쪽만 목록(앞 20)": npy_only[:20],
        "🔴🔴 둘 다 쓰는 파일": len(both), "둘 다 쓰는 파일 목록": both,
        "둘 다 쓰는 파일의 줄": rows,
        "⚠ 이 자는 텍스트다": ("정규식이라 **주석·문자열도 센다**. 아래 「나」 절이 "
                       "AST 로 다시 본다 — 두 자의 차가 이 절의 값이다(조항 60)"),
        "통과": True,
    }


def mixed_flow(files) -> dict:
    """🔴 **같은 함수 안에서** 두 이름 공간이 만나나 — AST 로 본다."""
    rows, danger = {}, []
    for rel in files:
        try:
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = ast.dump(fn)
            z = "namelist" in body or "ZipFile" in body
            n = ("files" in body and "load" in body) or "savez" in body
            if z and n:
                rows.setdefault(rel, []).append(fn.name)
                danger.append("%s:%s" % (rel, fn.name))
    return {
        "검사": "나 🔴 같은 함수 안에서 두 이름이 만나나(AST)",
        "🔴 분모 둘 다 쓰는 파일": len(files),
        "🔴 같은 **함수** 안에서 만나는 자리": len(danger),
        "자리": danger or "없음",
        "파일별 함수": rows or "없음",
        "🔴 뜻": ("0 이면 「오늘 살아 있는 소비자는 0」(티처·주 세션 실측과 같다). "
               "🔴 **그것은 「못 걸린다」가 아니라 「안 걸렸다」다** — 두 판독기가 "
               "**우연히** 같은 쪽을 쓰고 있을 뿐이고, 막는 코드는 저장소에 **0** 이다"),
        "🔴 남은 물음(다음 사이클 후보)": (
            "`lab.keyspace.npz_names` 는 zip 쪽을 읽고 `.npy` 를 **떼어** numpy 쪽 이름으로 "
            "맞춘다(`keyspace.py:187`). 그런데 **그 정규화를 안 지나는 소비자**가 "
            "numpy 쪽만 54 파일이다 — 둘이 만나는 날 그 54 가 분모다"),
        "통과": True,
    }


def nfc_nfd() -> dict:
    """🔴 NFC/NFD — 오늘 0/0 인 이유가 **APFS 덕이지 코드 덕이 아니다**(티처 #86 덤)."""
    paths = ks.git_paths("ls-files")
    split = sorted(p for p in paths if unicodedata.normalize("NFC", p)
                   != unicodedata.normalize("NFD", p))
    #: 🔴 **심은 키** — NFD 판 이름이 디스크 집합에 있나
    seed = split[0] if split else None
    nfd_hit = None
    if seed:
        nfd = unicodedata.normalize("NFD", seed)
        nfd_hit = (nfd in paths)
    #: 🔴 정규화를 **막는 코드**가 저장소에 있나 --- 있다/없다가 아니라 **세어서** 적는다
    import subprocess
    g = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotePath=false",
                        "grep", "-lz", "-e", "unicodedata.normalize", "--", "*.py"],
                       capture_output=True)
    guard = sorted(x for x in g.stdout.decode("utf-8", "replace").split("\0") if x)
    return {
        "검사": "다 🔴 NFC/NFD — 오늘의 0 은 파일시스템 덕이다",
        "🔴 분모 추적 경로": len(paths),
        "🔴 NFC ≠ NFD 인 경로": len(split),
        "예시 다섯": split[:5],
        "🔴 심은 키(NFD 판이 추적 집합에 있나)": {
            "심은 것": seed, "🔴 있나": nfd_hit,
            "뜻": ("False 면 **이 파일시스템(APFS)이 NFC 를 돌려주므로** 오늘의 0/0 이 "
                  "참이다. 🔴 다르게 정규화하는 데서 clone 하면 이 수 자리에서 "
                  "같은 병이 난다 — 막는 코드는 오늘 저장소에 **0**"),
        },
        "🔴 `unicodedata.normalize` 를 쓰는 `.py`": guard or
            "🔴 **0** --- 경로 이름 공간에 정규화 판독기가 없다(다음 사이클 후보)",
        "🔴 그중 경로 이름 공간을 지키는 것": (
            [x for x in guard if x in ("lab/keyspace.py", "lab/gitcall.py")] or
            "🔴 **0** --- 있는 것들은 **본문 텍스트**용이지 경로용이 아니다"),
        "통과": True,
    }


def main() -> int:
    if OUT.exists():
        OUT.unlink()
    t0 = dt.datetime.now(dt.timezone.utc)
    r = readers()
    res = collections.OrderedDict()
    res["무엇"] = "[탐색] 947 — npz 두 이름을 누가 섞어 쓰는가 + NFC/NFD"
    res["🔴 규칙 1"] = ("이 산출물의 수치는 이 사이클의 결론·원장 표제·커밋/PR 제목에 "
                    "**안 들어간다**. 다음 사이클의 후보가 될 뿐이다")
    res["🔴 안 한 것"] = ("**사실 관계를 다시 재지 않았다** — 추적 `.npz` 10 전량의 두 이름은 "
                     "티처와 주 세션이 이미 두 번 쟀다. 여기서는 **흐름만** 본다")
    res["가 판독기 등기부"] = r
    res["나 섞어 쓰는 자리"] = mixed_flow(r["둘 다 쓰는 파일 목록"])
    res["다 NFC/NFD"] = nfc_nfd()
    res["🔴 스탬프"] = {
        "시각(UTC · 시작)": t0.isoformat(timespec="seconds"),
        "시각(UTC · 끝)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "🔴 코드 sha256": __import__("hashlib").sha256(
            Path(__file__).read_bytes()).hexdigest(),
    }
    res["통과"] = None                      # 🔴 탐색은 판정하지 않는다
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1)[:3500])
    print("산출물: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
