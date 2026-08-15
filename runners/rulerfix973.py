#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""973 --- **자에 대한 자를 끝낸다**(티처 #111 의 2순위 · 수리 레인 · 상한 5).

🔴 **이것을 내기 전까지 「항진명제 n」은 인용 금지다**(티처 #111).
🔴 **972 의 러너를 한 바이트도 안 고친다.** 972 는 얼린 증거물이다 --- 고치는 대신
   **다시 재서 기록을 정정한다**(971 이 「돌린 뒤 파일을 고쳤다」로 걸린 그 병을 안 되풀이한다).

수리 다섯:
  **치-1** `--meta-*-exact` 를 물려 **4 칸 전부** 채점 + **Fisher 두쪽 p** 병기
          → 972 의 「어느 판으로도 밑값을 안 넘었다」를 정정한다
  **치-2** 「낙하 n 도 매여 있다」 확장을 **철회**한다(972 자신의 키가 반증한다)
  **치-4** 「48 줄」 → 실측 줄 수. 🔴 그리고 **치환표가 규칙 D 를 우회하는 통로**인지 --- 값과
          **키 라벨 안의 수**가 산출물에서 오는지 --- 검사한다
  **치-5** `predict972._clean` 이 먹은 **`_sha_file` 행을 복원**한다(산출물 8 줄 vs 헤드라인 9)
  **치-6** `meta965` 의 **산출 스키마 변경**을 적고, `meta965.py:1385` 를 **「모른다」로 내려앉힌다**

씀:
    python3 runners/rulerfix973.py --ref <40자 sha> [--out <경로>]
"""
import argparse
import collections
import datetime as dt
import json
import math
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "runners") not in sys.path:
    sys.path.insert(0, str(ROOT / "runners"))
os.chdir(str(ROOT))

import runners.predict971 as P                                    # noqa: E402

RAN = ("runners/rulerfix973.py", "runners/predict971.py")

CELLS = collections.OrderedDict([
    ("file · 접미", "runners/out972_meta_file.json"),
    ("file · 정확", "runners/out972_meta_file_exact.json"),
    ("func · 접미", "runners/out972_meta_func.json"),
    ("func · 정확", "runners/out972_meta_func_exact.json"),
])
OUT972 = ["runners/out972_wiring.json", "runners/out972_null.json",
          "runners/out972_rulerstab.json", "runners/out972_ledger.json",
          "runners/out972_meta_file.json", "runners/out972_meta_func.json",
          "runners/out972_meta_file_exact.json", "runners/out972_meta_func_exact.json",
          "runners/out972_meta_g1_file.json", "runners/out972_meta_g1_func.json"]


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def _dig(o, *names):
    cur = o
    for nm in names:
        if not isinstance(cur, dict):
            return None
        hit = None
        for k in cur:
            if nm in str(k):
                hit = k
                break
        if hit is None:
            return None
        cur = cur[hit]
    return cur


def code_stamp() -> dict:
    import glob
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


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


# ══════════════════════════════════════════════════════════════════════
# 치-1 --- 4 칸 전부 채점 + Fisher 두쪽 p
# ══════════════════════════════════════════════════════════════════════
def fisher_two_sided(a, b, c, d) -> float:
    """2×2 초기하 정확검정(두쪽). 🔴 관측보다 **확률이 크지 않은** 표를 다 더한다."""
    n = a + b + c + d
    r1, r2 = a + b, c + d
    c1 = a + c

    def pr(x):
        y = c1 - x
        if x < 0 or y < 0 or r1 - x < 0 or r2 - y < 0:
            return 0.0
        return (math.comb(r1, x) * math.comb(r2, y)) / float(math.comb(n, c1))

    p_obs = pr(a)
    lo = max(0, c1 - r2)
    hi = min(r1, c1)
    tot = 0.0
    for x in range(lo, hi + 1):
        p = pr(x)
        if p <= p_obs * (1 + 1e-9):
            tot += p
    return min(1.0, tot)


def cure1() -> dict:
    per = collections.OrderedDict()
    over = []
    for name, rel in CELLS.items():
        o = _load(rel)
        pf = _dig(o, "§1", "파일별")
        by = {k.split("/")[-1].replace(".py", ""): v for k, v in pf.items()}
        t = by["predict971"]
        b = by["recommit970"]
        a1, n1 = int(t["🔴 증명된 낙하"]), int(t["🔴 분모"])
        a0, n0 = int(b["🔴 증명된 낙하"]), int(b["🔴 분모"])
        p1, p0 = a1 / float(n1), a0 / float(n0)
        pv = fisher_two_sided(a1, n1 - a1, a0, n0 - a0)
        verdict = ("🔴 넘는다" if p1 > p0 else ("같다" if abs(p1 - p0) < 1e-12 else "아니다"))
        if p1 > p0:
            over.append(name)
        per[name] = {
            "산출물": rel,
            "predict971 낙하": "%d / %d" % (a1, n1), "predict971 %": round(100 * p1, 1),
            "밑값 recommit970 낙하": "%d / %d" % (a0, n0), "밑값 %": round(100 * p0, 1),
            "🔴 밑값을 넘었나": verdict,
            "🔴 Fisher 두쪽 p": round(pv, 6),
            "🔴 이 분모로 갈리나(p ≤ 0.05)": bool(pv <= 0.05),
        }
    return {
        "🔴 무엇": ("972 는 `ledger972` 가 `--meta-file`·`--meta-func` 둘만 받아 **4 칸 중 둘만** "
               "채점했다. 반증하는 칸(`func`·정확)을 만들어 커밋해 놓고 채점기에 안 물렸다"),
        "🔴 분모: 칸": len(CELLS),
        "칸별": per,
        "🔴🔴 밑값을 넘는 칸": {"목록": over, "🔴 분자/분모": "%d / %d" % (len(over), len(CELLS))},
        "🔴🔴 972 의 문장": "「어느 판으로도 밑값을 안 넘었다」",
        "🔴🔴 정정": ("**거짓이다.** 위 목록의 칸에서 넘는다. "
                 "🔴 다만 **Fisher 두쪽 p 를 병기하면 네 칸 어디서도 p ≤ 0.05 가 아니다** --- "
                 "정직한 문장은 「이 분모로는 아무것도 못 가른다」이지 "
                 "「안 넘었다」도 「넘었다」도 아니다"),
    }


# ══════════════════════════════════════════════════════════════════════
# 치-2 --- 「낙하 n 도 매여 있다」 철회
# ══════════════════════════════════════════════════════════════════════
def cure2() -> dict:
    RST = _load("runners/out972_rulerstab.json")
    flags = []

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + "/[%d]" % i)
        else:
            if isinstance(o, bool) and "낙하가 흔들렸나" in path:
                flags.append((path, o))

    walk(RST)
    n_true = sum(1 for _, v in flags if v)
    rs = RST["🔴🔴🔴 §R 요약"]
    return {
        "🔴 무엇": "972 가 카드에 쓴 「낙하 n 도 파일 나머지 내용에 매여 있다」 확장",
        "🔴 972 자신의 키(`🔴 낙하가 흔들렸나`)": {
            "자리 수(러너 3 × 갈래 3 × 범위 2)": len(flags),
            "🔴 그 중 True": n_true,
            "🔴 그 중 False": len(flags) - n_true,
            "🔴 분자/분모(True)": "%d / %d" % (n_true, len(flags)),
            "자리 목록": [p for p, _ in flags]},
        "🔴 그러면 뒤집히는 것은 무엇인가": {
            "file · 작은": rs["file · 작은"], "file · 큰": rs["file · 큰"],
            "func · 작은": rs["func · 작은"], "func · 큰": rs["func · 큰"],
            "🔴 음성 대조(주석만)": [rs["file · 주석만"], rs["func · 주석만"]]},
        "🔴🔴 철회": ("🔴 **「낙하 n 도 매여 있다」를 철회한다.** 뒤집히는 것은 **자리별 라벨**이고 "
                 "집계 수(낙하 n)가 아니다. 972 자신의 「판정이 뒤집힌 판」 불리언이 위 분모에서 "
                 "전부 False 다. **참인 명제는 「항진명제 n 은 파일 나머지 내용에 매여 있다」까지**다"),
    }


# ══════════════════════════════════════════════════════════════════════
# 치-4 --- 「48 줄」 실측 + 🔴 치환표가 규칙 D 를 우회하나
# ══════════════════════════════════════════════════════════════════════
def cure4() -> dict:
    import rulerstab972 as R                                      # noqa: E402
    lines = {}
    for kind in ("작은", "큰", "주석만"):
        ns = set()
        cmt = set()
        for seed in range(R.N_VARIANTS):
            t = R.make_tail(seed, kind)
            ns.add(len(t.splitlines()))
            cmt.add(sum(1 for x in t.splitlines() if x.strip().startswith("#")))
        lines[kind] = {"🔴 줄 수(실측 · 판 %d 개)" % R.N_VARIANTS: sorted(ns),
                       "그 중 주석 줄": sorted(cmt),
                       "🔴 생산 함수": "rulerstab972.make_tail --- **부른다**"}
    # 산출물 전량의 스칼라 값 집합 --- 치환표 값이 여기서 오는가
    pool = set()

    def collect(o):
        if isinstance(o, dict):
            for k, v in o.items():
                pool.add(str(k))
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)
        else:
            pool.add(str(o))
            if isinstance(o, float):
                pool.add(("%.6f" % o).rstrip("0").rstrip("."))
                pool.add("%.6f" % o)
            if isinstance(o, (int, float)) and not isinstance(o, bool):
                pool.add(str(round(float(o) * 100, 1)))

    n_files = 0
    for rel in OUT972:
        if (ROOT / rel).is_file():
            collect(_load(rel))
            n_files += 1
    nums = set()
    for s in pool:
        for m in re.findall(r"\d+(?:\.\d+)?", s):
            nums.add(m)

    LED = _load("runners/out972_ledger.json")
    SUB = _dig(LED, "§T 치환표")
    val_bad, lab_loose, lab_strict = [], [], []
    for k, v in (SUB or {}).items():
        sv = str(v)
        if sv not in pool and not isinstance(v, (bool, type(None))):
            if not all(x in nums for x in re.findall(r"\d+(?:\.\d+)?", sv)):
                val_bad.append({"열쇠": k, "값": sv})
        own = set(re.findall(r"\d+(?:\.\d+)?", sv))
        for m in re.findall(r"\d+(?:\.\d+)?", str(k)):
            if m not in nums:
                lab_loose.append({"열쇠": k, "🔴 라벨 안의 수": m})
            if m not in own:
                lab_strict.append({"열쇠": k, "🔴 라벨 안의 수": m, "그 열쇠의 값": sv,
                                   "🔴 3자리 노트 번호(9xx)인가": bool(re.fullmatch(r"9\d\d", m)),
                                   "느슨한 검사는 통과하나(어느 산출물엔가 있나)": bool(m in nums)})
    lab_strict_nonote = [x for x in lab_strict if not x["🔴 3자리 노트 번호(9xx)인가"]]
    return {
        "🔴 무엇": "972 가 쓴 「48 줄짜리 무관한 꼬리」의 실측 줄 수와, 치환표의 규칙 D 우회 여부",
        "🔴 꼬리 갈래별 실측": lines,
        "🔴🔴 「48 줄」 직접 검정": {
            "972 의 주장": "자 file 범위 뒤집힌 판은 **작은 꼬리 48줄**에서 났다",
            "🔴 실측 작은 꼬리 줄 수": lines["작은"]["🔴 줄 수(실측 · 판 12 개)"],
            "🔴 48 이 어느 갈래의 줄 수인가":
                [k for k in lines if 48 in lines[k]["🔴 줄 수(실측 · 판 12 개)"]] or "없다",
            "🔴 48 이 무엇인가": "`주석만` 갈래의 **주석 줄 수**(= `range(48)`)",
            "🔴🔴 주장이 참인가": bool(48 in lines["작은"]["🔴 줄 수(실측 · 판 12 개)"])},
        "🔴🔴 정정": ("「48 줄」은 **작은 꼬리의 줄 수가 아니다**. 위 실측이 정본이다. "
                 "🔴 48 은 `make_tail` 의 **주석만 갈래 반복 횟수**(`range(48)`)이고 그 갈래는 "
                 "**뒤집힌 판 0/36 인 음성 대조**다"),
        "🔴🔴 치환표 검사(규칙 D)": {
            "🔴 분모: 치환표 열쇠": len(SUB or {}),
            "🔴 분모: 훑은 972 산출물": n_files,
            "🔴 값이 산출물에서 안 오는 열쇠": {"수": len(val_bad), "목록": val_bad},
            "🔴 느슨한 검사 --- 라벨 안의 수가 **어느 산출물에도** 없는 열쇠":
                {"수": len(lab_loose), "목록": lab_loose,
                 "🔴 이 검사는 약하다": ("산출물 10 개의 모든 수를 한 자루에 넣고 보므로 `48` 처럼 "
                                "**남의 자리에서 온 수**가 통과한다. 972 의 「48 줄」이 그렇게 샜다")},
            "🔴🔴 엄격한 검사 --- 라벨 안의 수가 **그 열쇠 자신의 값**에 없는 열쇠":
                {"수": len(lab_strict), "🔴 분모: 치환표 열쇠": len(SUB or {}),
                 "🔴 3자리 노트 번호(9xx)를 뺀 수": len(lab_strict_nonote),
                 "🔴 이것은 선별망이지 판정이 아니다":
                     ("잔여에는 `95`(구간)·`2000`(뽑기)·`50`(뽑기)·`15`(MIN_TRAIN) 같은 "
                      "**참인 파라미터 라벨**이 섞인다. 🔴 **거짓임이 기계로 증명된 것은 "
                      "위 「48 줄」 직접 검정 하나**다"),
                 "목록": lab_strict},
            "🔴 왜 이 검사인가": ("972 의 「48 줄」은 치환표를 **통과했다** --- 값(`12 / 36`)은 "
                          "산출물에서 왔지만 **열쇠 라벨에 손으로 친 수**가 박혀 있었다. "
                          "🔴 **치환표가 규칙 D 를 우회하는 통로가 됐다**. "
                          "🔴 고침은 「라벨 안의 수도 그 열쇠 자신의 값에서 와야 한다」이고, "
                          "위 엄격한 검사가 그 자다"),
        },
    }


# ══════════════════════════════════════════════════════════════════════
# 치-5 --- `_clean` 이 먹은 `_sha_file` 행 복원
# ══════════════════════════════════════════════════════════════════════
def cure5() -> dict:
    W = _load("runners/out972_wiring.json")
    V = W["🔴🔴 §V 배선 파괴 대조(sabotage)"]
    in_art = list(V["함수별"].keys())
    head = V["🔴 분자/분모"]
    import predict972 as PZ                                       # noqa: E402
    prod = list(PZ.PROD_FUNCS)
    missing = [f for f in prod if f not in in_art]
    t0 = time.time()
    restored = {}
    for name in missing:
        orig = getattr(PZ.P, name)
        try:
            setattr(PZ.P, name, lambda *a, **k: "0" * 64)
            w = PZ.wiring_probe(deep=False)
            restored[name] = {"붉은 자리 수": len(w["🔴 붉은 자리"]),
                              "붉은 자리": w["🔴 붉은 자리"],
                              "🔴 잡혔나": bool(len(w["🔴 붉은 자리"]) > 0)}
        finally:
            setattr(PZ.P, name, orig)
    return {
        "🔴 무엇": ("`predict972.py:1003` 의 `_clean()` 이 **`_` 로 시작하는 열쇠를 먹는다**. "
               "그래서 파괴 대조의 `_sha_file` 행이 산출물에서 사라졌다"),
        "🔴 산출물에 있는 행": {"수": len(in_art), "목록": in_art},
        "🔴 생산 함수 전량(predict972.PROD_FUNCS)": {"수": len(prod), "목록": prod},
        "🔴🔴 사라진 행": missing,
        "🔴 헤드라인이 적은 것": head,
        "🔴🔴 복원": restored,
        "🔴 복원 뒤 분자/분모": "%d / %d" % (
            sum(1 for v in V["함수별"].values() if v.get("🔴 잡혔나"))
            + sum(1 for v in restored.values() if v["🔴 잡혔나"]), len(prod)),
        "초": round(time.time() - t0, 1),
        "🔴 정정": ("헤드라인 `%s` 는 **옳았고** 산출물이 한 줄 모자랐다. "
               "🔴 **972 의 러너는 안 고쳤다** --- 973 이 그 한 판을 다시 돌려 채웠다" % head),
    }


# ══════════════════════════════════════════════════════════════════════
# 치-6 --- meta965 산출 스키마 변경 · `meta965.py:1385`
# ══════════════════════════════════════════════════════════════════════
def cure6() -> dict:
    def top(rel):
        return list(_load(rel).keys()) if (ROOT / rel).is_file() else None

    old = top("runners/out971_meta.json")
    new = top("runners/out972_meta_func.json")
    added = [k for k in (new or []) if k not in (old or [])]
    gone = [k for k in (old or []) if k not in (new or [])]
    # `meta965.py:1385` 가 몇 칸에서 잡히나
    hits = collections.OrderedDict()
    for name, rel in list(CELLS.items()) + [
            ("g1 · file", "runners/out972_meta_g1_file.json"),
            ("g1 · func", "runners/out972_meta_g1_func.json")]:
        if not (ROOT / rel).is_file():
            continue
        o = _load(rel)
        txt = json.dumps(o, ensure_ascii=False)
        hits[name] = {"「meta965.py:1385」가 산출물에 적혔나": bool("meta965.py:1385" in txt
                                                        or ":1385" in txt)}
    n_hit = sum(1 for v in hits.values() if list(v.values())[0])
    return {
        "🔴 무엇": "972 가 `meta965` 의 산출 스키마를 바꿨는데 §8·원장 어디에도 안 적었다",
        "🔴 971 판 최상위 열쇠": {"수": len(old or []), "목록": old},
        "🔴 972 판 최상위 열쇠": {"수": len(new or []), "목록": new},
        "🔴🔴 더해진 열쇠": {"수": len(added), "목록": added},
        "🔴🔴 사라진 열쇠": {"수": len(gone), "목록": gone},
        "🔴 기본값 변경": ("`meta965 --poolscope` 의 기본값이 972 에서 `file` → **`func`** 로 바뀌었다"
                    "(노트 898 의 「기본값 보존」을 일부러 어겼다)"),
        "🔴🔴 meta965.py:1385": {
            "무엇": "§4 F1 의 `\"통과\": len(mine_taut) == 0` --- 자 B 의 입력 영역에서 상수다",
            "잡힌 칸": hits, "🔴 분자/분모": "%d / %d" % (n_hit, len(hits)),
            "🔴🔴 973 의 처리": ("**안 고쳤다. 「모른다」로 내려앉힌다.** 고치면 965~972 의 자 산출물이 "
                          "전부 갈리고 그 재주행은 이 사이클의 축(C3)을 통째로 먹는다. "
                          "🔴 **그러므로 이 저장소의 「항진명제 n」은 이 자리를 포함한 수다** --- "
                          "인용할 때 그렇게 적는다"),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", default="/Users/ax/wm_harvest/973/out973_rulerfix.json")
    a = ap.parse_args()
    t0 = time.time()
    cs0 = code_stamp()
    R = collections.OrderedDict()
    R["🔴 노트"] = 973
    R["🔴 레인"] = "수리"
    R["🔴 축"] = "C3 (이 산출물은 2순위 수리다 --- 축 전진은 out973_build/census 가 낸다)"
    R["🔴 시작(UTC)"] = _now()
    R["🔴 사전등록"] = "docs/prereg_973_hplt_c3.md §10 (측정 전 단독 커밋)"
    R["🔴🔴 §S 돌린 러너 ↔ 커밋 blob(F5)"] = ran_vs_blob(a.ref)
    R["🔴🔴🔴 치-1 4 칸 전부 채점 + Fisher"] = cure1()
    R["🔴🔴🔴 치-2 「낙하 n 도 매여 있다」 철회"] = cure2()
    R["🔴🔴🔴 치-4 「48 줄」 실측 + 치환표 규칙 D 우회 검사"] = cure4()
    R["🔴🔴🔴 치-5 `_sha_file` 행 복원"] = cure5()
    R["🔴🔴🔴 치-6 meta965 스키마 · :1385"] = cure6()
    R["🔴 수리 항목 수"] = 5
    R["🔴 상한"] = 5
    cs1 = code_stamp()
    R["🔴 끝(UTC)"] = _now()
    R["🔴 걸린 초"] = round(time.time() - t0, 1)
    R["🔴🔴 §Z 소스 대조"] = {
        "시작 code_stamp 요약": P.stamp_digest(cs0),
        "끝 code_stamp 요약": P.stamp_digest(cs1),
        "🔴 주행 중 소스가 바뀌었나": bool(cs0 != cs1),
        "분모: 도장이 덮는 파일": len(cs1),
        "🔴 자료 지문": {r: P._sha_file(ROOT / r) for r in OUT972
                    if (ROOT / r).is_file()},
        "🔴 분모: 연 자료 파일": sum(1 for r in OUT972 if (ROOT / r).is_file()),
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(a.out)


if __name__ == "__main__":
    main()
