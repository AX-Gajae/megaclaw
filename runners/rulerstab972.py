# -*- coding: utf-8 -*-
"""노트 972 — 🔴🔴 **자가 자기 대상의 「나머지 내용」에 매여 있는가**를 잰다.

사전등록: `docs/prereg_972_c1null.md` §2-나 (측정 전 단독 커밋 `8675748ed`).

🔴 **티처 #110 치명 1**: `meta965._gen_pool` 의 값·열쇠 풀이 **파일 전체 AST** 에서
만들어져서, **판정과 무관한 줄**이 남의 자리 판정을 뒤집을 수 있다. 971 의
「증명된 낙하 4(30.8%)」가 커밋본에서 갈린 뿌리로 지목된 것이 이것이다.

🔴 **이 러너는 그 주장을 편들지 않는다 --- 잰다.**
같은 파일에 **`통과` 자리를 하나도 안 더하고 기존 자리의 줄 번호도 안 바꾸는** 꼬리를
**여러 판** 붙여, `file` 범위와 `func` 범위에서 **판정이 뒤집히는 판의 비율**을 센다.
분모는 **꼬리 판 수**다.

세 갈래:
- **작은 꼬리** --- 48 줄. 971 의 `+48/−4` 와 같은 크기.
- **큰 꼬리** --- 풀의 잘림(`harvest_keys` 400 · `harvest_strings` 600)을 **넘긴다.**
  🔴 넘기면 **원래 파일의 문자열이 풀에서 밀려난다** --- 가장 센 자리다.
- **주석만** --- AST 에 안 들어간다. 🔴 **음성 대조: 어떤 범위에서도 0 이어야 한다.**

🔴 **`meta965.scan_source`·`tally`·`verdict_map` 을 그대로 부른다** --- 다시 안 쓴다.
"""
import argparse
import datetime as dt
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
os.chdir(str(ROOT))

import meta965 as M                                               # noqa: E402
import predict972 as PZ                                           # noqa: E402

TARGETS = ["runners/predict971.py", "runners/recommit970.py", "runners/meta965.py"]

#: 🔴 972 수리 **직전**의 트리(PR #229 머지 커밋). **고정 sha 다.**
PREFIX_REF = "ff1ae7039a6ed38a8e2436c680c52dbbb1d42abe"
N_VARIANTS = 12          # 🔴 갈래마다 꼬리 판 수(= 분모)
SEED = 972

#: 🔴 **자가 적발.** 첫 판의 낱자에 `통`·`과` 가 들어 있어서 무작위 낱말이 실제로
#: **`"통과"` 를 만들어냈고**, 꼬리 안에 **새 검사 자리**가 생겼다. 그것이 「뒤집혔다」로
#: 잘못 세어졌다(`predict971.py:842` --- 꼬리 안의 줄). **두 낱자를 뺐고**,
#: 아래 `sweep()` 의 `set(v1) != set(v0)` 가 **자리 집합이 갈리면 그 판을 버린다.**
_ALPHA = "가나다라마바사아자차카타파하게이드묶음유보학습abcdefgh0123456789"


def _word(rng, lo=3, hi=14):
    return "".join(rng.choice(_ALPHA) for _ in range(rng.randint(lo, hi)))


def make_tail(seed, kind) -> str:
    """🔴 **`통과` 키가 0 개**이고 파일 **끝**에 붙는 꼬리. 기존 자리의 줄 번호가 안 밀린다."""
    rng = random.Random("%d|%s|%d" % (SEED, kind, seed))
    if kind == "주석만":
        return "\n" + "\n".join("# 🔴 972 음성 대조 %d --- %s" % (i, _word(rng))
                                for i in range(48)) + "\n"
    n_key = 20 if kind == "작은" else 320
    n_str = 20 if kind == "작은" else 420
    keys = ", ".join('"%s": "%s"' % (_word(rng), _word(rng)) for _ in range(n_key))
    strs = "\n".join('    "%s",' % _word(rng) for _ in range(n_str))
    return ('\n\n# ── 🔴 972 안정성 대조 꼬리(%s · 씨앗 %d) --- `통과` 키 0 개 ──\n'
            '_STAB_NOTE_%d_%s = """%s\n\n%s\n"""\n\n'
            '_STAB_TABLE_%d_%s = {%s}\n\n'
            '_STAB_LIST_%d_%s = [\n%s\n]\n\n\n'
            'def _stab_helper_%d_%s(rows, kind="%s"):\n'
            '    """%s --- 아무 데서도 안 불린다."""\n'
            '    return [{"꼴": kind, "값": r, "곁": "%s"} for r in rows]\n'
            % (kind, seed, seed, kind, _word(rng, 20, 40), _word(rng, 20, 40),
               seed, kind, keys, seed, kind, strs,
               seed, kind, _word(rng), _word(rng, 10, 30), _word(rng)))


def scan(rel, src, scope, genver=2, passkey="suffix", slicer="new"):
    """🔴 `meta965` 의 생산 함수를 **그대로 부른다.**"""
    M.GENVER, M.PASSKEY, M.SLICER, M.POOLSCOPE = genver, passkey, slicer, scope
    ns, err = M.import_ns(rel)
    rng = random.Random(M.SEED)
    with M._NoWrite():
        rows = M.scan_source(rel, src, ns, rng)
    return rows, err


_BASE = {}


def base_scan(rel, src, scope):
    if (rel, scope) not in _BASE:
        _BASE[(rel, scope)] = scan(rel, src, scope)
    return _BASE[(rel, scope)]


def sweep(rel, src, scope, kind) -> dict:
    """🔴 꼬리 `N_VARIANTS` 판. **분모는 판 수다.**"""
    r0, _e0 = base_scan(rel, src, scope)
    v0, t0 = M.verdict_map(r0), M.tally(r0)
    flipped_runs, all_flips, drops, dropped_runs = 0, {}, [], []
    for s in range(N_VARIANTS):
        r1, _e1 = scan(rel, src + make_tail(s, kind), scope)
        v1, t1 = M.verdict_map(r1), M.tally(r1)
        if set(v1) != set(v0):
            #: 🔴 꼬리가 **새 검사 자리를 만들면** 그 판은 「무관한 꼬리」가 아니다. 버린다.
            dropped_runs.append({"씨앗": s, "늘어난 자리": sorted(set(v1) - set(v0)),
                                 "없어진 자리": sorted(set(v0) - set(v1))})
            continue
        drops.append(t1["🔴 증명된 낙하"])
        f = {k: [v0.get(k), v1.get(k)] for k in set(v0) | set(v1) if v0.get(k) != v1.get(k)}
        if f:
            flipped_runs += 1
            all_flips.setdefault("씨앗 %d" % s, f)
    n_ok = len(drops)
    return {
        "범위": scope, "꼬리 갈래": kind, "🔴 분모(꼬리 판 수)": N_VARIANTS,
        "🔴 자리가 늘어 버린 판": dropped_runs or "없음",
        "🔴 셈에 쓴 판 수": n_ok,
        "커밋본 계수": t0,
        "🔴🔴 판정이 하나라도 뒤집힌 판": flipped_runs,
        "🔴🔴 분자/분모": "%d / %d" % (flipped_runs, n_ok),
        "🔴 뒤집힌 자리(판별)": all_flips or "없음",
        "🔴 꼬리판 낙하 값의 범위": [min(drops), max(drops)] if drops else None,
        "커밋본 낙하": t0["🔴 증명된 낙하"],
        "🔴 낙하가 흔들렸나": bool(drops and (min(drops) != t0["🔴 증명된 낙하"]
                                    or max(drops) != t0["🔴 증명된 낙하"])),
    }


def self_check() -> dict:
    """🔴🔴 **972 가 자기 수리로 항진명제를 「만들었나」 「드러냈나」.**

    현행 자로 `meta965.py` 의 **수리 전 blob** 과 **수리 후 디스크**를 둘 다 훑는다.
    🔴 수리 전에도 붉으면 **972 가 드러낸 것**이고, 수리 전에 안 붉으면 **972 가 만든 것**이다.
    **어느 쪽이든 그대로 적는다.**
    """
    import subprocess
    rel = "runners/meta965.py"
    r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-p",
                        "%s:%s" % (PREFIX_REF, rel)], capture_output=True)
    old_src = r.stdout.decode("utf-8") if r.returncode == 0 else None
    now_src = (ROOT / rel).read_text(encoding="utf-8")
    out = {"🔴 기준 커밋(수리 전 · 고정 sha)": PREFIX_REF,
           "🔴 한계": ("훑는 소스는 수리 전 blob 이지만 이름 공간(`import_ns`)은 **지금 "
                   "디스크의 모듈**이다 --- 자 B 의 전역 그루터기가 그만큼 다르다")}
    for scope in ("file", "func"):
        a = {}
        if old_src is not None:
            ro, _ = scan(rel, old_src, scope)
            a["수리 전 blob"] = M.tally(ro)
        rn, _ = scan(rel, now_src, scope)
        a["수리 후 디스크"] = M.tally(rn)
        a["🔴 항진명제가 늘었나"] = bool(
            old_src is not None
            and len(a["수리 후 디스크"]["🔴 항진명제"]) > len(a["수리 전 blob"]["🔴 항진명제"]))
        out[scope] = a
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", required=True, help="🔴 **고정 sha**")
    a = ap.parse_args()
    out_path = Path(a.out)
    if not out_path.is_absolute():
        out_path = ROOT / "runners" / out_path

    t_start = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.time()
    R = {"🔴 노트": 972, "🔴 레인": "판정", "🔴 축": "C1 상태→예측(자의 재현성)",
         "🔴 시작(UTC)": t_start,
         "🔴 사전등록": "docs/prereg_972_c1null.md §2-나 (측정 전 단독 커밋 8675748ed)",
         "🔴 무엇": ("판정과 무관한 꼬리를 **여러 판** 붙였을 때 자의 판정이 뒤집히는 "
                 "**판의 비율**. 🔴 `file` 범위(965~971)와 `func` 범위(972 수리)를 나란히"),
         "🔴 설정": {"꼬리 판 수(갈래마다)": N_VARIANTS, "씨앗": SEED,
                  "genver": 2, "passkey": "suffix", "slicer": "new"}}
    with PZ.ReadTap():
        cs0 = PZ.code_stamp()
        R["🔴🔴 §S 내가 돌린 러너 ↔ 커밋 blob(F1)"] = PZ.ran_vs_blob(a.ref)
        per = {}
        for rel in TARGETS:
            src = (ROOT / rel).read_text(encoding="utf-8")
            e = {}
            for kind in ("작은", "큰", "주석만"):
                e[kind] = {"file 범위(965~971)": sweep(rel, src, "file", kind),
                           "func 범위(972 수리)": sweep(rel, src, "func", kind)}
            per[rel] = {
                "커밋본 줄 수": len(src.splitlines()),
                "커밋본 sha256": PZ.P._sha_file(ROOT / rel),
                "🔴 커밋 blob sha256": PZ.P.blob_sha(a.ref, rel),
                "🔴🔴 커밋본 낙하 --- 범위별": {
                    "file(965~971)": M.tally(base_scan(rel, src, "file")[0]),
                    "func(972 수리)": M.tally(base_scan(rel, src, "func")[0])},
                "꼬리 갈래별": e,
            }
        R["🔴🔴🔴 §R 자 안정성"] = per

        # 🔴 요약 --- 손으로 안 센다
        s = {}
        for scope_key in ("file 범위(965~971)", "func 범위(972 수리)"):
            for kind in ("작은", "큰", "주석만"):
                num = sum(per[r]["꼬리 갈래별"][kind][scope_key]["🔴🔴 판정이 하나라도 뒤집힌 판"]
                          for r in TARGETS)
                den = sum(per[r]["꼬리 갈래별"][kind][scope_key]["🔴 셈에 쓴 판 수"]
                          for r in TARGETS)
                s["%s · %s" % (scope_key.split(" ")[0], kind)] = "%d / %d" % (num, den)
        f_all = sum(int(v.split(" / ")[0]) for k, v in s.items()
                    if k.startswith("file") and "주석만" not in k)
        u_all = sum(int(v.split(" / ")[0]) for k, v in s.items()
                    if k.startswith("func") and "주석만" not in k)
        c_all = sum(int(v.split(" / ")[0]) for k, v in s.items() if "주석만" in k)
        s["🔴🔴 file 범위 뒤집힌 판 합(주석만 제외)"] = f_all
        s["🔴🔴 func 범위 뒤집힌 판 합(주석만 제외)"] = u_all
        s["🔴 음성 대조(주석만) 합 --- 0 이어야 한다"] = c_all
        s["🔴🔴 P4 --- file 범위에서 하나 이상 뒤집혔나"] = bool(f_all > 0)
        s["🔴🔴 P5 --- func 범위에서 하나도 안 뒤집혔나"] = bool(u_all == 0)
        s["🔴🔴 범위를 바꾸는 것만으로 낙하가 갈리나"] = {
            r: {"file": per[r]["🔴🔴 커밋본 낙하 --- 범위별"]["file(965~971)"]["🔴 증명된 낙하"],
                "func": per[r]["🔴🔴 커밋본 낙하 --- 범위별"]["func(972 수리)"]["🔴 증명된 낙하"]}
            for r in TARGETS}
        R["🔴🔴🔴 §R 요약"] = s
        R["🔴🔴🔴 §Y 972 가 자기 수리로 항진명제를 만들었나 드러냈나"] = self_check()
        cs1 = PZ.code_stamp()

    t_end = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    seal = PZ.data_seal()    # 🔴 규칙 C --- 자료 지문은 **끝에 한 번**
    R["🔴 끝(UTC)"] = t_end
    R["🔴 걸린 초"] = round(time.time() - t0, 1)
    R["🔴🔴 §Z 소스 대조"] = {
        "시작 code_stamp 요약": PZ.P.stamp_digest(cs0),
        "끝 code_stamp 요약": PZ.P.stamp_digest(cs1),
        "🔴 주행 중 소스가 바뀌었나": bool(cs0 != cs1),
        "🔴 바뀐 파일": sorted(k for k in set(cs0) | set(cs1) if cs0.get(k) != cs1.get(k)),
        "🔴 잰 소스 sha(전량 · 자르지 않았다)": cs1,
        "🔴🔴 §D 자료 입력 지문(규칙 C)": seal,
    }
    Path(out_path).write_text(json.dumps(R, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    print("wrote", out_path, R["🔴 걸린 초"], "s")


if __name__ == "__main__":
    main()
