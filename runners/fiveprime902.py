#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 **⑤′ 취합 검사를 손 절차가 아니라 러너로 만든다** --- 이슈 #140 M3.

## 왜 러너인가

`docs/루프.md` 의 ⑤′ 는 v3.1·v3.2 두 번 개정되고도 **데뷔전마다 자기 항목에 걸렸다.**
v3.2 의 첫 정식 운용(커밋 `765c7e6f6`)에서 티처 #64 M3 가 센 것:

1. **(가) 소비자 목록을 파일로 안 남겼다.** `docs/루프.md:249-253` 이 `grep -rl` 역참조로
   *"소비자 후보를 **파일로 남긴다**"* 를 요구하는데 커밋이 실은 것은 산출물 넷뿐이다.
2. 🔴 **(나) 분모가 바뀌었다.** 커밋이 *"바뀐 경로 **26**. 그중 실제로 돌린 것은 **셋**"* 이라
   적었다. **26 은 맞다.** 그러나 ⑤′ 의 대상은 「바뀐 경로」가 아니라 **역참조한 소비자 전량**
   이고, 티처가 역참조를 돌리니 **102개(그중 `.py` 52)** 였다.
   **「셋/26」과 「셋/102」는 다른 문장이다**(조항 60). ⑤′ 를 만든 목적이 정확히 이 바꿔치기다.
3. **(다) 판정 키 규약화가 0.** `docs/루프.md:256-258` 이 *"판정 키 이름을 `통과` 하나로
   규약화하라"* 고 적었는데 `runners/out899a_gates.json` 의 절 아홉 중 `통과` 키를 가진 것이
   **0개**다. 키 이름이 자리마다 다르면 **「없다」를 「통과」로 읽는 길이 영구히 열려 있다.**

**셋 다 「사람이 그때그때 하는 일」이라서 안 지켜졌다.** 그래서 러너로 내린다 ---
⓪ 관문 → 소비자 **기계 역참조** → **목록을 산출물에 남김** → 게이트 실행 → 판정 키 감사 →
도장 확인 → `quote901` 무변 확인 → D1 실측. **일곱 절 전부 `통과` 키를 갖는다.**

## 🔴 분모를 산출물에 박는다 (조항 59·60)

`1 소비자 역참조` 절은 넷을 **따로** 낸다: **바뀐 경로 수 · 역참조 소비자 수 ·
실제로 돌린 수 · 🔴 안 돌린 수**. 그리고 **안 돌린 것의 목록 전량**을 싣는다 ---
「안 돌렸다」를 「없다」로 읽을 길을 없앤다.

역참조의 **자를 셋** 쓴다(각 자의 수를 따로 적는다). 자가 하나면 그 자의 사각지대가
그대로 「없다」가 된다:

| 자 | 바늘 | 무엇을 잡나 |
|---|---|---|
| 전체 경로 | `ingest/audit.py` | 경로 문자열로 부르는 곳 |
| 파일명 | `audit.py` | 경로 없이 이름만 적은 곳 |
| 모듈 점경로 | `ingest.audit` | 🔴 `import` --- **앞의 둘이 원리상 못 잡는다** |

🔴 **`git diff --name-only` 는 한글 경로를 `"docs/\353\243..."` 로 이스케이프해서 낸다.**
그 문자열을 그대로 바늘로 쓰면 **한 곳도 안 맞고 종료 0 이 난다**(조항 59 그 자체).
그래서 `-c core.quotepath=false` 와 `-z` 를 쓴다. 실측: 이스케이프본 75 대 정상본 78.

## 쓰기

    python3 runners/fiveprime902.py --base <취합 시작 rev> [--head HEAD]
        [--tree <rev>]            # 역참조를 이 rev 의 트리에서 한다(기본: 작업 트리)
        [--ran <경로> ...]        # 이번에 실제로 다시 돌린 소비자
        [--exempt <경로>=<사유>]  # 🔴 안 돌린 `.py` 에 사유를 단다(사유 없으면 실패다)
        [--gates]                 # 게이트를 실제로 돌린다(안 주면 「안 돌렸다」로 적는다)
        [--out runners/out902b_fiveprime.json]

🔴 **`timeout` 은 이 환경에 없다(rc=127).** 이 러너는 `subprocess` 의 `timeout=` 만 쓴다.
"""
import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "runners/out902b_fiveprime.json"

#: 🔴 **이 러너가 자기 판정에 쓰는 코드** --- 도장 ④ 가 이것들의 sha256 이다.
STAMP_CODE = ["runners/fiveprime902.py", "runners/quote901.py"]

#: 판정 키 감사의 **필수** 대상. 남의 소유라 고치지 않고 **읽는 쪽에서** 「모른다」로 센다.
KEYAUDIT_MUST = ["runners/out899a_gates.json"]


# ── 도장 ────────────────────────────────────────────────────────────────
def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def stamp(inputs) -> dict:
    """🔴 **실행 「시작」에서 부른다**(티처 #64 C3).

    노트 901 실물: `out899a_gates.py` 가 `stamp_close(stamp())` 로 **끝에서 둘 다** 불러서
    **116.9초 실행의 시작 == 끝**이었다. 「시작 시각」이 실은 끝 시각이었다.
    코드 sha 도 끝에서 읽히면 **실행에 쓰인 코드가 아니라 끝난 뒤의 코드**를 증언한다.
    """
    head = _git(["rev-parse", "HEAD"])[1].strip()
    return {
        "시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "🔴 코드 sha256(이게 자다)": {c: (sha(ROOT / c) if (ROOT / c).exists() else "🔴 파일 없음")
                              for c in STAMP_CODE},
        "🔴 입력 산출물 sha256": {i: (sha(ROOT / i) if (ROOT / i).exists() else "🔴 파일 없음")
                          for i in inputs},
        "⚠ git HEAD(시작 시점 · 판정에 쓰지 마라)": head,
    }


def stamp_close(st: dict, t0: float) -> dict:
    st["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    st["초"] = round(time.time() - t0, 1)
    return st


def _git(args, timeout=600):
    r = subprocess.run(["git", "-C", str(ROOT)] + args,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


# ── ⓪ 관문 ──────────────────────────────────────────────────────────────
def gate_worktree() -> dict:
    """`git status --porcelain` 이 비어야 ⑤′ 를 시작한다. 900 은 정확히 여기서 샜다."""
    rc, out, err = _git(["status", "--porcelain"])
    dirty = [l for l in out.split("\n") if l.strip()]
    return {
        "검사": "⓪ 관문 --- 작업 트리가 비었나(⑤′ 는 커밋된 트리를 검사한다)",
        "git status --porcelain 종료": rc,
        "더러운 경로 수": len(dirty),
        "더러운 경로": dirty or "없음",
        "⚠": ("🔴 안 비었다 --- ⑤′ 는 실패다. 이 목록을 보고서에 그대로 싣는다"
              if dirty else "비었다"),
        "통과": (rc == 0) and (not dirty),
    }


# ── 1 소비자 역참조 ─────────────────────────────────────────────────────
def _needles(paths):
    """🔴 자 셋. 하나만 쓰면 그 자의 사각지대가 그대로 「없다」가 된다."""
    full = sorted(set(paths))
    base = sorted(set(os.path.basename(p) for p in paths))
    mod = sorted(set(p[:-3].replace("/", ".") for p in paths if p.endswith(".py")))
    return {"전체 경로": full, "파일명": base, "모듈 점경로": mod}


def _grep_l(needles, tree=None):
    """`git grep -lF` 로 역참조한다. 🔴 못 돌면 빈 목록이 아니라 예외를 들고 온다."""
    if not needles:
        return [], {"rc": None, "왜": "바늘이 0개다 --- 「소비자 없음」이 아니다"}
    # 🔴 `--untracked` 는 rev 와 못 섞인다(`fatal: … no such path in the working tree`).
    #    작업 트리를 볼 때만 붙인다 --- 안 붙이면 아직 커밋 안 된 소비자가 **조용히 사라진다**.
    args = ["grep", "-lF"] + ([] if tree else ["--untracked"])
    for n in needles:
        args += ["-e", n]
    if tree:
        args += [tree]
    rc, out, err = _git(args, timeout=900)
    if rc not in (0, 1):                      # 0=맞음 1=하나도 안 맞음 그 밖=고장
        raise RuntimeError("git grep 종료 %d: %s" % (rc, err[:400]))
    files = []
    for l in out.split("\n"):
        l = l.strip()
        if not l:
            continue
        if tree and l.startswith(tree + ":"):
            l = l[len(tree) + 1:]
        files.append(l)
    return sorted(set(files)), {"rc": rc, "바늘 수": len(needles)}


def backref(base, head, tree, ran, exempt) -> dict:
    rc, out, err = _git(["-c", "core.quotepath=false", "diff", "--name-only", "-z",
                         "%s..%s" % (base, head)])
    if rc != 0:
        return {"검사": "1 소비자 역참조", "🔴 예외": "git diff 종료 %d: %s" % (rc, err[:300]),
                "통과": False}
    changed = sorted(p for p in out.split("\0") if p)
    nd = _needles(changed)

    # 🔴 **음성 대조** --- `-c core.quotepath=false` 를 **안 쓴** 바늘로도 한 번 센다.
    #    한글 경로가 `"docs/\353\243…"` 로 이스케이프되어 **한 곳도 안 맞는데 종료 0** 이
    #    나는 길이 실재한다. 그 차를 수로 남기지 않으면 다음 사람이 또 밟는다.
    rc_q, out_q, _ = _git(["diff", "--name-only", "%s..%s" % (base, head)])
    esc = sorted(p for p in out_q.split("\n") if p.strip())
    esc_hit, _m = _grep_l(sorted(set(esc)), tree)

    per, cons = {}, set()
    for label, ns in nd.items():
        got, meta = _grep_l(ns, tree)
        per[label] = {"바늘 수": len(ns), "소비자 수": len(got),
                      "그중 .py": len([g for g in got if g.endswith(".py")]), **meta}
        cons |= set(got)
    consumers = sorted(cons)
    py = [c for c in consumers if c.endswith(".py")]

    ran = sorted(set(ran))
    ran_in = [r for r in ran if r in cons]
    ran_out = [r for r in ran if r not in cons]
    notrun = [c for c in consumers if c not in set(ran)]
    notrun_py = [c for c in notrun if c.endswith(".py")]
    notrun_other = [c for c in notrun if not c.endswith(".py")]
    no_reason = [c for c in notrun_py if c not in exempt]

    return {
        "검사": "1 소비자 역참조 --- 🔴 사람이 고르지 않는다(`docs/루프.md:249-253`)",
        "취합 시작(base)": base, "머리(head)": head,
        "역참조한 트리": tree or "작업 트리",
        # ── 🔴 분모 넷을 나란히 박는다 (조항 60) ──────────────────────
        "🔴 분모 ① 바뀐 경로 수": len(changed),
        "🔴 분모 ② 역참조 소비자 수": len(consumers),
        "🔴 분모 ②-py 역참조 소비자 중 .py": len(py),
        "🔴 분모 ③ 실제로 돌린 수": len(ran_in),
        "🔴 분모 ④ 안 돌린 수": len(notrun),
        "🔴 분모 ④-py 안 돌린 .py 수": len(notrun_py),
        "🔴 분모 ④-사유없음 안 돌린 .py 중 사유 없는 것": len(no_reason),
        "⚠ 분모 ① 과 ② 는 다른 자다": (
            "「돌린 셋 / 바뀐 경로 %d」과 「돌린 셋 / 소비자 %d」는 다른 문장이다. "
            "⑤′ 의 대상은 ② 다(티처 #64 M3 나)." % (len(changed), len(consumers))),
        "🔴 음성 대조(quotepath 를 안 끈 바늘)": {
            "왜": "`git diff --name-only` 는 한글 경로를 이스케이프한다 --- 그 바늘은 한 곳도 "
                  "안 맞는데 **종료 0** 이 난다(조항 59 그 자체)",
            "이스케이프된 경로 수": len([p for p in esc if p.startswith('"')]),
            "이스케이프 바늘로 센 소비자 수": len(esc_hit),
            "정상 바늘(전체 경로)로 센 소비자 수": per["전체 경로"]["소비자 수"],
            "🔴 차(이스케이프 때문에 사라지는 소비자 수)":
                per["전체 경로"]["소비자 수"] - len(esc_hit),
        },
        "바뀐 경로": changed,
        "자별 역참조": per,
        "역참조 소비자(전량)": consumers,
        "돌렸다": ran_in,
        "⚠ 돌렸다고 적었지만 소비자 목록에 없는 것": ran_out or "없음",
        "🔴 안 돌렸다(= 「없다」가 아니다 · 조항 59)": notrun_py,
        "안 돌렸다(비 .py · 실행 대상 아님)": notrun_other,
        "안 돌린 .py 의 사유": {k: v for k, v in exempt.items() if k in set(notrun_py)},
        "🔴 사유 없이 안 돌린 .py": no_reason,
        "통과": (not no_reason),
        "⚠ 통과의 뜻": ("역참조 소비자 중 **실행 가능한 `.py` 가 전부 다시 돌았거나 "
                   "사유가 등록됐나**. 「안 돌렸다」가 하나라도 사유 없이 남으면 실패다"),
    }


# ── 2 게이트 ────────────────────────────────────────────────────────────
def gate_roster(tree) -> dict:
    """🔴 **게이트 명부를 손으로 나열하지 마라**(`docs/루프.md:254-258`).

    「허가 목록이 곧 검사 목록」병을 피하려면 명부가 **기계로** 나와야 한다.
    자: `"통과"` 를 **키로 내는** `.py` 전량. 새 게이트를 넣는 사람이 이 줄을 몰라도 잡힌다.
    """
    got, meta = _grep_l(['"통과":', "'통과':", '"통과" :'], tree)
    return sorted(p for p in got if p.endswith(".py")), meta


def run_gates(do_run, tree, consumers, ran_hand=()) -> dict:
    roster, meta = gate_roster(tree)
    # 🔴 무엇을 왜 안 돌리는지 **여기 적는다**. 안 적으면 「없다」가 된다.
    #    🔴 사유 하나는 **기계로 나온다**: 이번 취합의 역참조에 안 걸린 게이트는
    #    ⑤′ 의 대상이 아니다. 사람이 손으로 봐주는 사유가 아니라 1 절의 결과다.
    skip = {p: "이번 취합의 소비자가 아니다(1 절 역참조에 안 걸렸다)"
            for p in roster if p not in set(consumers)}
    skip.update({
        "runners/out899a_gates.py": (
            "다른 팔 소유 · 돌리면 `runners/out899a_gates.json` 을 덮어써서 동시에 도는 팔의 "
            "산출물을 깨뜨린다. 대신 **3 절이 그 산출물을 읽어 판정 키를 감사한다**"),
    })
    # 손으로 다시 돌린 게이트(`--ran`)도 「돌렸다」다 --- 안 세면 「안 돌렸다」가 부풀고,
    # 부푼 분모도 분모 바꿔치기다(조항 60).
    ran = [p for p in ran_hand if p in set(roster)]
    results, exc = {}, {}
    if do_run:
        t = time.time()
        try:
            r = subprocess.run([sys.executable, "-m", "ingest.audit", "--json"],
                               cwd=str(ROOT), capture_output=True, text=True, timeout=1800)
            if r.returncode != 0:
                exc["ingest/audit.py"] = "종료 %d · %s" % (r.returncode, r.stderr[-400:])
            else:
                d = json.loads(r.stdout)
                # 🔴 손 나열 금지 --- `통과` 키를 가진 절을 **전부 자동 수집**한다
                results = {k: v["통과"] for k, v in d.items()
                           if isinstance(v, dict) and "통과" in v}
                ran.append("ingest/audit.py")
        except Exception as e:                                    # noqa: BLE001
            exc["ingest/audit.py"] = "%s: %s" % (type(e).__name__, e)
        results["_초"] = round(time.time() - t, 1)
    ran = sorted(set(ran))
    notrun = [p for p in roster if p not in set(ran)]
    no_reason = [p for p in notrun if p not in skip]
    failed = [k for k, v in results.items() if v is False]
    return {
        "검사": "2 게이트 --- 🔴 명부를 기계로 뽑는다(손 나열 금지)",
        "명부를 어떻게 뽑았나": '`git grep -lF -e \'"통과":\'` 로 **`통과` 를 키로 내는 `.py` 전량**',
        "🔴 게이트 생산자 수(분모)": len(roster),
        "🔴 그중 이번 취합의 소비자인 것": len([p for p in roster if p in set(consumers)]),
        "게이트 생산자": roster,
        "🔴 돌린 수": len(ran), "돌렸다": ran,
        "🔴 안 돌린 수": len(notrun),
        "🔴 안 돌렸다(= 「없다」가 아니다)": notrun,
        "안 돌린 사유": {k: v for k, v in skip.items() if k in set(notrun)},
        "🔴 사유 없이 안 돌린 것": no_reason,
        "돌린 게이트의 절별 판정": results or "안 돌렸다(--gates 를 안 줬다)",
        "🔴 실패한 절": failed or "없음",
        "🔴 예외": exc or "없음",
        "통과": bool(do_run) and (not failed) and (not exc) and (not no_reason),
    }


# ── 3 판정 키 규약 ──────────────────────────────────────────────────────
def keyaudit(extra) -> dict:
    """🔴 **`통과` 키가 없는 절을 「모른다」로 세어 드러낸다**(`docs/루프.md:256-258`).

    대상 파일은 **남의 소유라 고치지 않는다.** 고치는 대신 **읽는 쪽에서** 센다 ---
    900 의 첫 훑기가 동적 게이트 다섯에서 전부 `None` 을 받고도 초록이었던 길이 그것이다.
    🔴 `None` 은 「통과」가 아니라 **「모른다」**다(조항 59).
    """
    per, tot, has, unk = {}, 0, 0, 0
    for rel in list(dict.fromkeys(KEYAUDIT_MUST + list(extra))):
        p = ROOT / rel
        if not p.exists():
            per[rel] = {"🔴": "그 파일이 없다(「절이 없다」가 아니다)"}
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:                                    # noqa: BLE001
            per[rel] = {"🔴": "못 읽었다: %s" % e}
            continue
        # 🔴 **도장은 절이 아니다.** `코드 sha256`·`시각` 같은 도장 dict 를 절로 세면
        #    분모가 부풀고, 그러면 「모른다 10/10」이 티처가 손으로 센 **9** 와 어긋난다.
        #    분모를 부풀리는 것도 분모 바꿔치기다(조항 60).
        stampish = sorted(k for k, v in d.items()
                          if isinstance(v, dict) and any(w in k for w in ("sha256", "시각")))
        secs = {k: v for k, v in d.items()
                if isinstance(v, dict) and k not in set(stampish)}
        ok = sorted(k for k, v in secs.items() if "통과" in v)
        no = sorted(k for k in secs if k not in set(ok))
        # 절이 아닌 최상위 불리언(판정처럼 보이는 것)도 드러낸다
        loose = sorted(k for k, v in d.items() if isinstance(v, bool))
        per[rel] = {
            "🔴 절 수(분모)": len(secs),
            "`통과` 키가 있는 절": len(ok), "그 목록": ok or "없음",
            "🔴 `통과` 키가 없는 절 = 모른다": len(no), "모른다 목록": no,
            "⚠ 절 밖의 최상위 판정 불리언(규약 밖)": loose or "없음",
            "⚠ 절로 세지 않은 도장 dict": stampish or "없음",
            "통과": (len(no) == 0),
        }
        tot += len(secs)
        has += len(ok)
        unk += len(no)
    return {
        "검사": "3 판정 키 규약 --- `통과` 하나로 규약화됐나",
        "🔴 왜 읽는 쪽에서 하나": "대상 산출물은 남의 소유다. 고치지 않고 **세어 드러낸다**",
        "🔴 절 수 합(분모)": tot,
        "`통과` 키가 있는 절 합": has,
        "🔴 모른다(=`통과` 키 없음) 합": unk,
        "파일별": per,
        "통과": (tot > 0 and unk == 0),
        "⚠ 통과의 뜻": "🔴 `통과 == False` 는 「게이트가 실패했다」가 아니라 **「판정을 못 읽는다」**다",
    }


# ── 4 도장 확인 ─────────────────────────────────────────────────────────
def stamp_audit() -> dict:
    """🔴 `git HEAD` 스탬프는 판정에 쓰지 않는다(v3.2 가 폐기). 도장 넷을 본다."""
    want = ("시각", "sha256")
    rows, nost, bad = {}, [], []
    for p in sorted((ROOT / "runners").glob("out*.json")):
        rel = p.relative_to(ROOT).as_posix()
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:                                    # noqa: BLE001
            rows[rel] = {"🔴": "못 읽었다: %s" % type(e).__name__}
            bad.append(rel)
            continue
        if not isinstance(d, dict):
            rows[rel] = {"⚠": "최상위가 dict 가 아니다"}
            nost.append(rel)
            continue
        keys = [k for k in d if any(w in k for w in want)]
        t_open = [k for k in d if "시각" in k and "시작" in k]
        t_shut = [k for k in d if "시각" in k and "끝" in k]
        if not keys:
            nost.append(rel)
            continue
        rows[rel] = {"도장 키": keys,
                     "시작 시각": (d[t_open[0]] if t_open else "🔴 없다"),
                     "끝 시각": (d[t_shut[0]] if t_shut else "🔴 없다"),
                     "초": d.get("초", "모른다"),
                     "시작<끝": ((d[t_open[0]] < d[t_shut[0]]) if (t_open and t_shut) else None)}
    # 🔴 **초 단위 도장에서 「시작 == 끝」은 두 가지다**: ① 901 의 그 병(긴 실행인데 끝에서
    #    둘 다 찍었다) ② 진짜로 1초 안에 끝난 실행. 둘을 갈라 센다 --- 안 가르면 이 절이
    #    영구 False 게이트가 되고, 그러면 아무도 안 본다.
    def _long(v):
        s = v.get("초")
        return isinstance(s, (int, float)) and s > 1.5
    same = [k for k, v in rows.items() if v.get("시작<끝") is False and _long(v)]
    short = [k for k, v in rows.items() if v.get("시작<끝") is False and not _long(v)]
    return {
        "검사": "4 도장 확인 --- ① 시작 ② 끝 ③ 입력 sha ④ 코드 sha",
        "🔴 훑은 산출물 수(분모)": len(list((ROOT / "runners").glob("out*.json"))),
        "도장이 있는 산출물 수": len(rows) - len(bad),
        "🔴 도장이 하나도 없는 산출물 수": len(nost),
        "🔴 도장이 하나도 없는 산출물": nost,
        "🔴 못 읽은 산출물": bad or "없음",
        "🔴 시작 == 끝 인데 초 > 1.5 인 산출물(901 의 그 병)": same or "없음",
        "⚠ 시작 == 끝 이지만 1.5초 안에 끝난 산출물(병 아님)": short or "없음",
        "도장별": rows,
        "통과": (not same) and (not bad),
        "⚠": ("도장 없음을 「실패」로 세지 않는다 --- 옛 산출물이 많다. **수를 드러내는 것**이 이 절의 일이다"),
    }


# ── 5 quote901 기존 동작 무변 ───────────────────────────────────────────
#: 🔴 이슈 #140 M4 --- `--selftest` 를 JSON 산출물로 내되 **기존 동작을 하나도 바꾸지 마라**.
#: 「안 바꿨다」를 말로 하면 그게 바로 이 사이클이 걸린 병이다. **바꾸기 전 동작을 기록해
#: 두고 대조한다** --- 기준본은 `git show <rev>:runners/quote901.py`.
_SCRUB = re.compile(r"(/[^\s'\"]*/)?(tmp|T/)[A-Za-z0-9_]{6,}")


#: 🔴 `--selftest` 는 **자기 파일 위치 기준**으로 산출물 경로를 정한다. 기준본은 임시
#: 디렉터리에서 돌므로 그 한 줄이 반드시 다르다 --- 코드가 같아도 다르다.
#: ⚠ 이 규칙은 수리 B 가 보고에 *"「산출물: …」 한 줄을 떼고 견줬다"* 라고 적었지만
#: **실제로는 안 걸려 있었다**(주 세션이 5절·5-나가 False 로 뒤집힌 것을 보고 잡았다).
#: 🔴 **「고쳤다」와 「고쳐졌다」는 둘이다** --- 그래서 아래 `_OUTLINE` 이 실물이고,
#: 음성 대조(안 바꾼 사본이 통과하나)가 이 규칙의 시험이다.
_OUTLINE = re.compile(r"^산출물: .*$", re.M)


def _scrub(s: str) -> str:
    """🔴 실행마다/자리마다 달라지는 것만 지운다. **그 밖은 한 글자도 안 건드린다.**

    지우는 것 둘: ① 임시 디렉터리 이름 ② `--selftest` 의 「산출물:」 경로 한 줄.
    """
    return _OUTLINE.sub("산출물: <경로>", _SCRUB.sub("<TMP>", s))


def quote_regress(ref, now=None) -> dict:
    """🔴 `now` 로 **딴 파일을 심어 이 절이 실제로 붉어지는지** 확인한다(검정력 측정).

    티처 #64 m4 --- *"자기시험 3점의 검정력이 사실상 0"* 이었다(원점을 1km 옮겨도 통과).
    **시험을 세울 때 「무엇을 못 가르는지」를 먼저 재라.** 그래서 심는 길을 열어 둔다.
    """
    import tempfile
    rc, src, err = _git(["show", "%s:runners/quote901.py" % ref])
    if rc != 0:
        return {"검사": "5 quote901 무변", "🔴 예외": "기준본을 못 꺼냈다: %s" % err[:200],
                "통과": False}
    with tempfile.TemporaryDirectory() as td:
        old = Path(td) / "quote_old.py"
        old.write_text(src, encoding="utf-8")
        j = Path(td) / "t.json"
        j.write_text(json.dumps({"수": 633, "널": None, "묶음": {"가/나": 2}},
                                ensure_ascii=False), encoding="utf-8")
        cases = [
            ("값", [str(j), "수"]),
            ("--cite", ["--cite", str(j), "수"]),
            ("--check 맞음", ["--check", "633", str(j), "수"]),
            ("🔴 --check 어긋남", ["--check", "629", str(j), "수"]),
            ("🔴 파일 없다", [str(Path(td) / "없다.json"), "수"]),
            ("🔴 JSON 아니다", [str(old), "수"]),
            ("🔴 키 없다", [str(j), "없는키"]),
            ("🔴 null", [str(j), "널"]),
            ("🔴 키 경로 없음", [str(j)]),
            ("--list", ["--list", str(j)]),
            ("🔴 구분자 품은 키", [str(j), "묶음/가/나"]),
            ("--help", ["--help"]),
            ("--selftest", ["--selftest"]),
        ]
        # 🔴 **작업본을 저장소에서 그대로 돌리면 안 된다**(티처 #65 M16).
        #    `--selftest` 는 **자기 파일 위치 기준**으로 `runners/out902b_selftest.json` 을
        #    **쓴다**(도장에 시각이 들어가 내용이 매번 바뀐다). 그래서 ⑤′ 를 돌리는 것만으로
        #    작업 트리가 더러워지고 --- 🔴 **⓪ 관문(트리가 비어야 한다)을 5절이 깨뜨렸다.**
        #    실측: 커밋된 ⓪ 의 더러운 7 안에 `out902b_selftest.json` 이 있었다.
        #    그래서 **작업본도 사본을 임시 디렉터리에 두고 돌린다** --- 기준본과 같은 조건이 되고
        #    저장소는 안 더러워진다. ⚠ 그 대가로 산출물 경로가 둘 다 임시라 `_scrub` 이
        #    양쪽을 `<경로>` 로 뭉갠다(그 사각지대는 아래 `⚠ 못 재는 것` 에 적었다).
        if now:
            new = Path(now)
            _new_tmp = None
        else:
            _new_tmp = tempfile.mkdtemp(prefix="fp902new_")
            new = Path(_new_tmp) / "quote901.py"
            new.write_text((ROOT / "runners/quote901.py").read_text(), encoding="utf-8")
        diff, per = [], {}
        for name, argv in cases:
            a = subprocess.run([sys.executable, str(old)] + argv,
                               cwd=str(ROOT), capture_output=True, text=True, timeout=300)
            b = subprocess.run([sys.executable, str(new)] + argv,
                               cwd=str(ROOT), capture_output=True, text=True, timeout=300)
            # 🔴 임시 디렉터리 이름은 **매 실행 다르다**. 그걸 안 지우면 「달라졌다」가
            #    영원히 참이 되어 이 절이 아무것도 못 잰다. 무엇을 지웠는지 여기 적는다.
            ao, bo = _scrub(a.stdout), _scrub(b.stdout)
            ae, be = _scrub(a.stderr), _scrub(b.stderr)
            note = ""
            if name == "--selftest":
                # 🔴 **한쪽만 떼면 안 된다.** 초판은 `bo`(작업본)에서만 「산출물:」 줄을
                #    떼었는데, 기준본이 이미 새 판이면 **양쪽 다 그 줄을 찍으므로**
                #    비대칭이 생겨 「달라졌다」가 영원히 참이 된다(주 세션이 실측으로 잡았다).
                #    이제 `_scrub` 이 **양쪽 모두** `산출물: <경로>` 로 정규화한다.
                # 🔴 그리고 그 경로는 **자기 파일 위치 기준**이라 기준본(임시 디렉터리)과
                #    작업본(저장소)이 원리상 다르다 --- 코드가 같아도 다르다.
                note = ("🔴 `산출물:` 경로 한 줄을 **양쪽 다** `<경로>` 로 정규화하고 견줬다 "
                        "--- 그 경로는 자기 파일 위치 기준이라 기준본과 작업본이 원리상 다르다")
            same = (a.returncode == b.returncode and ao == bo and ae == be)
            per[name] = {"기준 종료": a.returncode, "지금 종료": b.returncode,
                         "stdout 같나": ao == bo, "stderr 같나": ae == be,
                         "같나": same, **({"⚠": note} if note else {})}
            if not same:
                diff.append(name)
        if _new_tmp:
            shutil.rmtree(_new_tmp, ignore_errors=True)
        return {
            "검사": "5 quote901 기존 동작 무변 --- 기준본 대 작업본",
            "기준본": "git show %s:runners/quote901.py" % ref,
            "작업본": (now or "runners/quote901.py"),
            "🔴 견준 가짓수(분모)": len(cases),
            "🔴 같은 것": len(cases) - len(diff),
            "🔴 다른 것": diff or "없음",
            "가짓수별": per,
            "⚠ 지운 것": ("임시 디렉터리 이름과 `--selftest` 의 「산출물:」 경로 **한 줄**. "
                          "그 밖은 한 글자도 안 지웠다"),
            "🔴 ⚠ 못 재는 것": ("`--selftest` 가 **어느 파일에 쓰는지**가 바뀌어도 이 시험은 "
                            "못 잡는다 --- 양쪽 경로를 `<경로>` 로 뭉개기 때문이다(티처 #65 M15). "
                            "그 사각지대를 5-나 에 심어서 재야 한다(아직 안 했다)"),
            "통과": (not diff),
        }


#: 🔴 **이 시험이 무엇을 못 가르는지 먼저 잰다**(티처 #64 m4). 「안 바꿨다」를 증명하려면
#: 그 시험이 **바꿨을 때 붉어진다**는 것부터 보여야 한다.
MUTANTS = [
    ("종료 코드 갈래를 흔든다(E_MISMATCH 6→7)",
     "E_OK, E_NOFILE, E_NOTJSON, E_NOKEY, E_NULL, E_MISMATCH = 0, 2, 3, 4, 5, 6",
     "E_OK, E_NOFILE, E_NOTJSON, E_NOKEY, E_NULL, E_MISMATCH = 0, 2, 3, 4, 5, 7"),
    ("--cite 의 출처 꼴에서 백틱을 뗀다",
     'cite = "`%s:%s`" % (a.file, a.sep.join(path))',
     'cite = "%s:%s" % (a.file, a.sep.join(path))'),
    ("--check 를 관대하게 만든다(어긋나도 안 죽는다)",
     "        if not same:\n            die(E_MISMATCH,",
     "        if False:\n            die(E_MISMATCH,"),
]


def quote_power(ref) -> dict:
    """🔴 이 무변 시험이 **실제로 붉어지나**(검정력)를 심어서 잰다.

    ⚠ **씨앗은 기준본이어야 한다**(티처 #65 C1 수리의 곁가지 · 주 세션 실측).
    작업본을 씨앗으로 쓰면 「안 바꾼 사본」이 **기준본과 실제로 달라서**
    음성 대조가 영원히 False 가 된다 --- 그러면 이 절도 아무것도 못 잰다.
    「안 바꿨으면 통과」가 성립하려면 사본이 **견줄 대상과 같은 판**이어야 한다.
    """
    import tempfile
    rc0, base_src, err0 = _git(["show", "%s:runners/quote901.py" % ref])
    if rc0 != 0 or not base_src.strip():
        return {"검사": "5-나 심어서 확인", "🔴 예외": "씨앗(기준본)을 못 꺼냈다: %s" % err0[:200],
                "통과": False}
    src = base_src
    rows, missed, unplanted = {}, [], []
    with tempfile.TemporaryDirectory() as td:
        for name, old, new in MUTANTS:
            if old not in src:
                unplanted.append(name)
                rows[name] = {"🔴": "못 심었다 --- 그 문자열이 없다(「잡았다」가 아니다 · 조항 59)"}
                continue
            p = Path(td) / ("m%d.py" % len(rows))
            p.write_text(src.replace(old, new), encoding="utf-8")
            r = quote_regress(ref, str(p))
            caught = not r["통과"]
            rows[name] = {"잡았나": caught, "붉어진 가짓수": r["🔴 다른 것"]}
            if not caught:
                missed.append(name)
        ctl = Path(td) / "ctl.py"
        ctl.write_text(src, encoding="utf-8")
        c = quote_regress(ref, str(ctl))
    return {
        "검사": "5-나 🔴 **심어서 확인** --- 이 무변 시험이 실제로 붉어지나(검정력)",
        "🔴 심은 가짓수(분모)": len(MUTANTS),
        "🔴 잡은 수": len(MUTANTS) - len(missed) - len(unplanted),
        "🔴 놓친 것": missed or "없음",
        "🔴 못 심은 것(=「잡았다」가 아니다)": unplanted or "없음",
        "심은 것별": rows,
        "음성 대조(안 바꾼 사본)": {"통과": c["통과"], "다른 것": c["🔴 다른 것"]},
        "통과": (not missed) and (not unplanted) and c["통과"],
    }


# ── 6 D1 실측 (이슈 #140 M6) ────────────────────────────────────────────
def d1_census() -> dict:
    """🔴 사전등록 `docs/prereg_901_intervention.md:101` 은 **D1 = 원천 「파일 수」**라 적었다.

    그 정의가 맞는 도메인은 셋뿐이다. **사전등록은 증거물이라 고치지 않는다** ---
    대신 **세어서 산출물에 남기고** 정정문을 원장으로 보낸다.

    🔴 `SRC` 표를 **손으로 옮겨 적지 않는다** --- `runners/inv901.py` 를 `ast` 로 읽는다
    (import 하면 그 러너의 무거운 본문이 돈다).
    """
    src_py = (ROOT / "runners/inv901.py").read_text(encoding="utf-8")
    tree = ast.parse(src_py)
    SRC = None
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(
                getattr(t, "id", None) == "SRC" for t in n.targets):
            SRC = ast.literal_eval(n.value)
    if SRC is None:
        return {"검사": "6 D1 실측", "🔴": "`runners/inv901.py` 에서 SRC 를 못 찾았다", "통과": False}

    rows, multi, single, exc = {}, [], [], {}
    for dom, (kind, p, _ax, _o) in SRC.items():
        fp = ROOT / p
        try:
            if kind == "dir":
                fs = sorted(fp.glob("*.json"))
                nf, nr = len(fs), len(fs)          # dir 은 파일 하나 = 레코드 하나
            elif kind == "jsonl":
                nf = 1
                nr = sum(1 for l in open(fp, encoding="utf-8") if l.strip())
            else:
                nf = 1
                d = json.loads(fp.read_text(encoding="utf-8"))
                nr = len(d) if isinstance(d, (dict, list)) else 0
        except Exception as e:                                    # noqa: BLE001
            exc[dom] = "%s: %s" % (type(e).__name__, e)
            continue
        rows[dom] = {"원천 종류": kind, "원천": p, "원천 파일 수": nf, "레코드 수": nr,
                     "🔴 「파일 수」 정의가 맞나": (nf == nr)}
        (multi if nf > 1 else single).append(dom)
    return {
        "검사": "6 D1 실측 --- 사전등록의 「원천 파일 수」가 실제와 맞나(이슈 #140 M6)",
        "🔴 사전등록은 고치지 않는다": "`docs/prereg_901_intervention.md` 는 증거물이다. 정정문으로 닫는다",
        "🔴 도메인 수(분모)": len(SRC),
        "🔴 파일이 여럿인 도메인 수": len(multi), "그 목록": sorted(multi),
        "🔴 파일이 하나인 도메인 수": len(single), "그 목록": sorted(single),
        "🔴 「파일 수 == 레코드 수」가 성립하는 도메인 수": len([d for d in rows if rows[d]["🔴 「파일 수」 정의가 맞나"]]),
        "도메인별": rows,
        "🔴 예외": exc or "없음",
        "🔴 정정문(원장용)": (
            "정정 — `docs/prereg_901_intervention.md:101` 의 **D1 = 「원천 파일 수」**는 틀렸다. "
            "그 정의가 맞는 도메인은 **셋**(디렉터리 원천: 팝업·시장팝업·아이돌)뿐이고 "
            "나머지 **아홉**은 원천이 **파일 하나**다. 실제로 측정된 D1 은 "
            "**전 도메인에서 레코드 수**이며, 구현이 그렇게 적혀 있다"
            "(`runners/inv901.py:6` *「D1 원천 레코드 수」* · `:392` `D1 = len(recs)`). "
            "🔴 **사전등록 파일은 증거물이라 고치지 않는다** --- 이 정정문이 딱지의 정본이다."),
        "통과": (not exc) and (len(rows) == len(SRC)),
    }


# ── 엮기 ────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(prog="fiveprime902.py", description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True, help="취합 시작 rev")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--tree", default=None, help="역참조를 이 rev 트리에서 한다(기본 작업 트리)")
    ap.add_argument("--ran", action="append", default=[], help="이번에 실제로 다시 돌린 소비자 경로")
    ap.add_argument("--exempt", action="append", default=[], help="경로=사유")
    ap.add_argument("--keyaudit", action="append", default=[], help="판정 키를 감사할 산출물 추가")
    ap.add_argument("--gates", action="store_true", help="게이트를 실제로 돌린다")
    # 🔴 **기준본이 `HEAD` 면 이 절은 원리상 아무것도 못 잰다**(티처 #65 C1).
    #    ⑤′ 는 **⑤ 취합 뒤**에 돌므로 그때 HEAD 는 이미 **그 편집을 담은 커밋**이다.
    #    실측: 커밋된 실행의 기준본이 `0c323056c`(= `quote901.py` 를 고친 그 커밋)라
    #    작업본과 **바이트 동일**이었고 13/13 이 나왔다. 진짜 편집 전 rev(`6a27a645f`)로
    #    돌리면 **12/13 · 다른 것 `--selftest`** 다.
    #    🔴 티처 #64 M4 의 「16/16」이 「13/13」으로 **얼굴만 바꿔 재발**했다.
    #    그래서 기본값을 **취합 시작 rev(`--base`)** 로 바꾼다 --- 그게 「편집 전」이다.
    ap.add_argument("--quote-ref", default=None,
                    help="quote901 기준본 rev(기본: --base = 취합 시작 rev)")
    ap.add_argument("--quote-now", default=None,
                    help="🔴 작업본 대신 이 파일을 견준다 --- **심어서 검정력을 재는** 자리")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    a = ap.parse_args(argv)

    if a.quote_ref is None:
        a.quote_ref = a.base          # 🔴 위 주석 참조 --- HEAD 는 자기 자신이다

    t0 = time.time()
    exempt = {}
    for e in a.exempt:
        k, _, v = e.partition("=")
        exempt[k.strip()] = v.strip() or "🔴 사유가 비었다"
    st = stamp(KEYAUDIT_MUST + list(a.keyaudit))       # 🔴 시작에서 찍는다

    ran = list(a.ran)
    if a.gates:
        ran.append("ingest/audit.py")

    res = {"무엇": "⑤′ 취합 검사 러너 --- 이슈 #140 M3·M4·M6",
           "🔴 규약": [
               "① 소비자는 **기계 역참조**로 뽑고 **목록을 이 파일에 남긴다**",
               "② 🔴 분모 넷을 나란히 박는다 --- 바뀐 경로 · 역참조 소비자 · 돌린 것 · **안 돌린 것**",
               "③ 모든 절이 `통과` 키를 갖는다. 없는 절을 소비할 땐 **「모른다」로 센다**",
               "④ 「안 돌렸다」는 「없다」가 아니다(조항 59)",
           ]}
    res["⓪ 관문(작업 트리)"] = gate_worktree()
    try:
        res["1 소비자 역참조"] = backref(a.base, a.head, a.tree, ran, exempt)
    except Exception as e:                                        # noqa: BLE001
        res["1 소비자 역참조"] = {"🔴 예외": "%s: %s" % (type(e).__name__, e), "통과": False}
    _cons = res["1 소비자 역참조"].get("역참조 소비자(전량)", [])
    res["2 게이트"] = run_gates(a.gates, a.tree,
                             _cons if isinstance(_cons, list) else [], ran)
    res["3 판정 키 규약"] = keyaudit(a.keyaudit)
    res["4 도장 확인"] = stamp_audit()
    res["5 quote901 무변"] = quote_regress(a.quote_ref, a.quote_now)
    res["5-나 무변 시험의 검정력(심어서 확인)"] = quote_power(a.quote_ref)
    res["6 D1 실측"] = d1_census()

    secs = {k: v for k, v in res.items() if isinstance(v, dict) and "통과" in v}
    fail = sorted(k for k, v in secs.items() if not v["통과"])
    res["🔴 절 수(분모)"] = len(secs)
    res["🔴 `통과` 키를 가진 절"] = len(secs)
    res["🔴 실패한 절"] = fail or "없음"
    res["통과"] = (not fail)
    res.update(stamp_close(st, t0))

    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    # 화면 요약은 **절만** 줄인다(도장 dict 를 줄이면 도장이 빈 것처럼 보인다)
    print(json.dumps({k: ({kk: vv for kk, vv in v.items()
                           if kk.startswith(("🔴", "통과", "검사"))}
                          if (isinstance(v, dict) and "통과" in v) else v)
                      for k, v in res.items()}, ensure_ascii=False, indent=1))
    print("산출물: %s" % a.out)
    return 0 if res["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
