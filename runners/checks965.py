# -*- coding: utf-8 -*-
"""🔴🔴 노트 965 — **964 가 남긴 못 떨어지는 검사를 고친 판 · 소비자를 AST 로 해소 · 도메인 자**.

🔴 **`runners/checks964.py` 와 `runners/out964_checks.json` 은 964 의 증거물이라 안 고친다**
(사전등록 §4). 963 이 동결물 `triples962.py` 에 쓴 방식 그대로 — **고친 판은 새 러너**다.

무엇을 내나 (사전등록 §8 예고와 같은 순서):

  §-1  이 러너의 성질 — 🔴 **문장이 아니라 코드를 잰다**(964 C1 의 고친 판)
  §1   `lab.adopt.rulers` 소비자를 **AST 로 실제 해소**한다 — **저장소 전량**이 분모다 (2순위)
  §2   별칭 소비자(`rulers as new_rulers`)를 스키마 대조 **안으로** 넣는다 (2순위)
  §3   W10 고침의 **검정력** — 🔴 **무작위 인자가 판정을 무나**를 964 판과 나란히 잰다 (1순위 C3)
  §4   ⑤′ 산출물과 964 판정문의 수를 **기계로** 대조한다 (2순위)
  §5   K1·K2 를 **실질 계수**로 다시 센다 — 🔴 「실행됐다」가 아니라 「떨어뜨렸다」 (1순위)
  §6   🔴 **도메인 수를 재는 자리에 자를 세운다** — 티처 #102 의 심기 ⓓ 를 문다 (3순위)
  절 회계 — 🔴 964 는 `len(red) == len(secs) - n_ok` 였다(**같은 집합의 분할** · 티처 #103 C2).
          여기는 **「붉은 절이 하나라도 있으면 떨어진다」**로 간다.
"""
from __future__ import annotations

import argparse
import ast
import collections
import datetime as dt
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "runners/out965_checks.json"
D964 = ROOT / "docs/판정/964.md"
FP964 = ROOT / "runners/out964_fiveprime.json"

# 🔴 965 가 손대기 **전** 트리 — `#222` 머지 커밋. §7 이 여기서 산출물을 꺼내 본다.
REV_BEFORE = "f8ef5c417"


# ══════════════════════════════════════════════════════════════════════════
# §1 🔴🔴 `lab.adopt.rulers` 소비자를 **AST 로 해소**한다 (티처 #103 M2 · 2순위)
# ══════════════════════════════════════════════════════════════════════════
def resolve_rulers(src: str):
    """한 파일이 **`lab.adopt.rulers` 를 정말 부르나**를 AST 로 판정한다.

    964 의 `_consumers()` 는 **정규식** `re.search(r"\\brulers\\s*\\(", src)` 였다.
    그러면 셋을 원리상 못 가른다:

      ① `C.rulers()` — `lab/calib.py:193` 의 **다른 함수**
      ② `def rulers(pred)` — **지역 정의**(`runners/cal691.py:60`)
      ③ `rulers` 라는 **지역 변수**(`runners/fiveprime902.py`)

    그리고 반대로 **별칭**(`from lab.adopt import rulers as new_rulers`)은
    정규식이 잡더라도 **이름이 달라서 스키마 대조가 놓친다**(티처 #103 M2).
    """
    tree = ast.parse(src)
    bound, modalias, local_def, local_var = set(), set(), set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            if n.module == "lab.adopt":
                for a in n.names:
                    if a.name == "rulers":
                        bound.add(a.asname or a.name)
                    elif a.name == "*":
                        bound.add("rulers")
            elif n.module == "lab":
                for a in n.names:
                    if a.name == "adopt":
                        modalias.add(a.asname or a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name == "lab.adopt":
                    modalias.add(a.asname or "lab")
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "rulers":
            local_def.add("rulers")
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                for x in ast.walk(t):
                    if isinstance(x, ast.Name) and x.id == "rulers":
                        local_var.add("rulers")

    live = bound - local_def - local_var
    calls, other = [], []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Name) and f.id in live:
            calls.append({"줄": n.lineno, "꼴": "이름 호출", "이름": f.id})
        elif isinstance(f, ast.Attribute) and f.attr == "rulers":
            base = f.value
            root = base.id if isinstance(base, ast.Name) else None
            if root in modalias or (isinstance(base, ast.Attribute)
                                    and getattr(base.value, "id", None) == "lab"
                                    and base.attr == "adopt"):
                calls.append({"줄": n.lineno, "꼴": "속성 호출", "이름": ast.unparse(f)})
            else:
                other.append({"줄": n.lineno, "꼴": "🔴 **다른 함수**의 `.rulers()`",
                              "이름": ast.unparse(f)[:60]})
        elif isinstance(f, ast.Name) and f.id == "rulers":
            other.append({"줄": n.lineno, "꼴": ("🔴 **지역 `def rulers`**" if local_def
                                               else "🔴 **지역 변수 `rulers`**"), "이름": "rulers"})
    return {
        "🔴 진짜 소비자인가": bool(calls),
        "묶인 이름": sorted(bound), "🔴 별칭인가": bool(bound - {"rulers"}),
        "모듈 별칭": sorted(modalias),
        "지역 def": sorted(local_def), "지역 변수": sorted(local_var),
        "진짜 호출": calls, "🔴 거짓 양성이 될 호출": other,
    }


def consumers_section():
    py = sorted(p for p in ROOT.rglob("*.py")
                if ".claude" not in p.parts and "node_modules" not in p.parts)
    textual, real, fp, err = [], [], [], {}
    detail = collections.OrderedDict()
    for p in py:
        rel = str(p.relative_to(ROOT))
        try:
            src = p.read_text(encoding="utf-8")
        except Exception as e:                                     # noqa: BLE001
            err[rel] = str(e)
            continue
        if not re.search(r"\brulers\s*\(", src):
            continue
        textual.append(rel)
        try:
            v = resolve_rulers(src)
        except SyntaxError as e:
            err[rel] = "SyntaxError: %s" % e
            continue
        detail[rel] = v
        (real if v["🔴 진짜 소비자인가"] else fp).append(rel)
    runners_only = [r for r in textual if r.startswith("runners/")]
    return {
        "🔴 무엇": ("964 의 `_consumers()` 는 **정규식**이었다(티처 #103 M2). 여기는 **AST 로 해소**하고 "
                 "🔴 **분모를 `runners/` 가 아니라 저장소 전량으로** 넓힌다(티처 #103 m5: "
                 "V4′ 는 `runners/` 밖을 안 봤고 「전수」라는 말이 틀렸다)"),
        "🔴 분모 ① 저장소 `.py` 전량": len(py),
        "🔴 분모 ② 본문에 `rulers(` 가 있는 `.py`(정규식 · 964 의 자)": len(textual),
        "그중 `runners/` 안(964 의 분모)": len(runners_only),
        "🔴 분자: AST 로 해소한 **진짜** `lab.adopt.rulers` 소비자": len(real),
        "진짜 소비자": real,
        "🔴 거짓 양성(정규식은 물고 AST 는 안 문다)": len(fp),
        "거짓 양성 목록": fp,
        "🔴 거짓 양성 비율": (round(len(fp) / len(textual), 4) if textual else None),
        "🔴 별칭으로 부르는 소비자": [r for r in real if detail[r]["🔴 별칭인가"]],
        "🔴🔴 티처 #103 은 3 이라 했다 — 왜 다른가(조항 60: 분모가 다르다)": (
            "티처는 **수리 전 rev `62c50d380` 의 `runners/` 10개**를 해소했다. "
            "지금 트리에는 **`checks964.py`(964 가 만들었다)와 `checks965.py`(내가 만든다)가 더 있다.** "
            "🔴 **내 것을 빼면 4 · 964 것까지 빼면 3 — 티처의 수와 맞는다.** 두 수는 다른 트리의 수다"),
        "🔴 내가 이 사이클에 만든 것을 뺀 수": len([r for r in real if "965" not in r]),
        "파싱 실패": err or "없음",
        "칸별": detail,
        "통과": bool(real) and len(real) < len(textual),
        "🔴 이 절의 `통과` 가 뜻하는 것": ("AST 해소가 **실제로 무언가를 걸러냈나** — 진짜 소비자가 "
                              "하나 이상이고 정규식 분모보다 **작아야** 한다. 둘이 같으면 "
                              "AST 를 쓴 값이 0 이다"),
    }


# ══════════════════════════════════════════════════════════════════════════
# §2 별칭 소비자를 스키마 대조 안으로 (티처 #103 M2 · 커버리지 2/3 였다)
# ══════════════════════════════════════════════════════════════════════════
def alias_coverage(real, detail):
    """964 의 `_scan_source` 는 `func.id == "rulers"` 만 잡아 **별칭 소비자를 놓쳤다**."""
    old = [r for r in real if not detail[r]["🔴 별칭인가"]]
    return {
        "🔴 무엇": ("964 의 스키마 대조는 `func.id == \"rulers\"` 만 잡았다 — "
                 "`rulers as new_rulers` 로 부르는 소비자가 **원리상 사정권 밖**이었다"),
        "🔴 분모: 진짜 소비자": len(real),
        "964 의 자로 덮이는 수(이름이 그대로 `rulers` 인 것만)": len(old),
        "🔴 964 의 커버리지": ("%d/%d" % (len(old), len(real))) if real else "모른다",
        "🔴 965 의 자로 덮이는 수(별칭 포함)": len(real),
        "🔴 늘어난 소비자": [r for r in real if detail[r]["🔴 별칭인가"]],
        "통과": len(real) > len(old) if real else False,
        "🔴 이 절의 `통과` 가 뜻하는 것": "별칭 해소가 **실제로 소비자를 더 찾았나**",
    }


# ══════════════════════════════════════════════════════════════════════════
# §3 🔴🔴 W10 고침의 검정력 — **무작위 인자가 판정을 무나** (1순위 C3)
# ══════════════════════════════════════════════════════════════════════════
def w10_power(n=2000, seed=965):
    """🔴 티처 #103 이 964 의 「True 508 / False 1,492」를 분해했다:
    **op0(변조 없음) 508 → True 508 · op1/op2/op3 1,492 → True 0.**
    즉 **판정을 오로지 「손으로 변조했나」가 결정하고 무작위 인자는 하나도 안 물었다.**

    🔴 그래서 여기는 **딕트를 한 번도 안 건드린다.** 오직 **`rulers()` 의 인자만** 무작위로 갈고,
    두 판을 나란히 돌린다:

      **964 판** `w10_check(rt_i, lambda: rulers(**args_i))` — `rt_i` 가 그 호출의 반환값 그 자체
      **965 판** `w10_check(disk, lambda: rulers(**args_i))` — `disk` 는 **한 번 고정한 산출물**

    964 판이 `n/n` True 이고 965 판이 그보다 작으면, **무작위 인자가 이제 판정을 문다.**
    """
    from lab.adopt import rulers                                   # noqa: PLC0415
    from runners.curve961 import w10_check                         # noqa: PLC0415
    rng = random.Random(seed)

    def args():
        return dict(sum_delta=rng.uniform(-0.1, 0.1), sum_T=rng.uniform(1e-4, 0.05),
                    sub_delta=rng.uniform(-0.05, 0.05), sub_T=rng.uniform(1e-4, 0.05),
                    perm_obs=rng.uniform(-0.05, 0.1), perm_p95=rng.uniform(-0.01, 0.05),
                    card_T=0.00353)

    disk_args = args()
    disk = rulers(**disk_args)
    old_true = new_true = 0
    new_vals = collections.Counter()
    for _ in range(n):
        a = args()
        rt = rulers(**a)
        if w10_check(rt, lambda a=a: rulers(**a))["통과"]:
            old_true += 1
        v = w10_check(disk, lambda a=a: rulers(**a))["통과"]
        new_vals[v] += 1
        if v:
            new_true += 1

    # 🔴 손 심기 셋도 그대로 확인한다(964 가 하던 것 — 없애지 않는다)
    from runners.curve961 import RULERS_NEED                       # noqa: PLC0415
    plant = {}
    ren = dict(disk)
    # 🔴 `w10_check` 는 **자기가 내는 키**를 ② 의 분모에서 뺀다(965). 그러니 심기는
    #   반드시 **`RULERS_NEED` 안의 키**를 건드려야 진짜 심기다 — 안 그러면 심어도 안 문다.
    k0 = RULERS_NEED[0]
    ren["🔴 이름을 갈았다"] = ren.pop(k0)
    plant["① 키 이름을 간다"] = w10_check(ren, lambda: rulers(**disk_args))["통과"]
    swp = dict(disk)
    swp[k0] = "🔴 값을 바꿔치기했다"
    plant["② 값을 바꿔치기한다"] = w10_check(swp, lambda: rulers(**disk_args))["통과"]
    from runners.curve961 import RULERS_3VAL_KEYS                  # noqa: PLC0415
    bad = dict(disk)
    bad[RULERS_3VAL_KEYS[0]] = "3값 밖"
    plant["③ 3값 밖의 값을 싣는다"] = w10_check(bad, lambda: rulers(**disk_args))["통과"]
    plant["⓪ 무변조(같은 인자)"] = w10_check(disk, lambda: rulers(**disk_args))["통과"]

    return {
        "🔴 무엇": ("**딕트를 한 번도 안 건드리고 `rulers()` 의 인자만 무작위로 간다.** "
                 "티처 #103 이 964 의 하네스에서 「무작위 인자가 하나도 안 문다」를 보였다"),
        "뽑기 수": n, "씨앗": seed,
        "🔴 964 판(`rt` 를 넘긴다) True": old_true,
        "🔴 965 판(디스크 산출물을 넘긴다) True": new_true,
        "965 판 값 분포": {str(k): v for k, v in new_vals.items()},
        "🔴 무작위 인자가 판정을 무나(964 판)": old_true != n,
        "🔴 무작위 인자가 판정을 무나(965 판)": 0 < new_true < n or new_true == 0,
        "🔴🔴 965 판이 내는 값의 가짓수(무변조 True + 무작위 인자)":
            len({plant["⓪ 무변조(같은 인자)"]} | set(new_vals)),
        "🔴 964 판이 내는 값의 가짓수": 1,
        "손 심기(964 가 하던 것 — 없애지 않았다)": plant,
        "통과": bool(old_true == n and new_true < n
                   and plant["⓪ 무변조(같은 인자)"] is True
                   and not plant["① 키 이름을 간다"]
                   and not plant["② 값을 바꿔치기한다"]
                   and not plant["③ 3값 밖의 값을 싣는다"]),
        "🔴 이 절의 `통과` 가 뜻하는 것": ("① 964 판은 무작위 인자 전수에서 **늘 True**(항진명제) · "
                              "② 965 판은 **True 가 아닌 뽑기가 있다**(인자가 문다) · "
                              "③ 손 심기 셋은 여전히 떨어진다"),
    }


# ══════════════════════════════════════════════════════════════════════════
# §4 ⑤′ 산출물 ↔ 964 판정문 기계 대조 (티처 #103 M3 · 2순위)
# ══════════════════════════════════════════════════════════════════════════
FIVEPRIME_CLAIMS = [
    {"이름": "역참조 소비자 수", "정규식": r"역참조 소비자 \*\*(\d+)\*\*",
     "키": ["1 소비자 역참조", "🔴 분모 ② 역참조 소비자 수"]},
    {"이름": "안 돌린 수", "정규식": r"나머지 \*\*(\d+)\*\* 에 \*\*사유를 안 달았다",
     "키": ["1 소비자 역참조", "🔴 분모 ④ 안 돌린 수"]},
    {"이름": "다시 돌린 수(321행)", "정규식": r"다시 돌린 것 \*\*(\d+)\*\*",
     "키": ["1 소비자 역참조", "🔴 분모 ③ 실제로 돌린 수"]},
    {"이름": "다시 돌린 수(357행)", "정규식": r"중 \*\*(\d+)\*\* 만 다시 돌렸고",
     "키": ["1 소비자 역참조", "🔴 분모 ③ 실제로 돌린 수"]},
    {"이름": "게이트 생산자 수", "정규식": r"게이트 생산자 \*\*(\d+)\*\*",
     "키": ["2 게이트", "🔴 게이트 생산자 수(분모)"]},
]


def _dig(obj, keys):
    for k in keys:
        if not isinstance(obj, dict) or k not in obj:
            return None, "키 없음: %s" % k
        obj = obj[k]
    return obj, None


def fiveprime_section():
    if not (D964.exists() and FP964.exists()):
        return {"🔴 왜 `통과` 키를 안 내나": "판정문이나 ⑤′ 산출물이 없다 — 모른다"}
    doc = D964.read_text(encoding="utf-8")
    fp = json.loads(FP964.read_text(encoding="utf-8"))
    rows, bad = [], []
    for c in FIVEPRIME_CLAIMS:
        m = re.search(c["정규식"], doc)
        got, why = _dig(fp, c["키"])
        said = int(m.group(1)) if m else None
        ok = (said is not None and got is not None and said == got)
        rows.append({"이름": c["이름"], "판정문이 적은 수": said,
                     "⑤′ 산출물의 수": got, "출처 키": "/".join(c["키"]),
                     "왜 못 읽었나": why, "🔴 맞나": ok})
        if not ok:
            bad.append(c["이름"])
    # 🔴 자기모순 — 같은 문서가 같은 수를 둘로 적는다
    a = re.search(FIVEPRIME_CLAIMS[2]["정규식"], doc)
    b = re.search(FIVEPRIME_CLAIMS[3]["정규식"], doc)
    contra = bool(a and b and a.group(1) != b.group(1))
    return {
        "🔴 무엇": ("964 는 「⑤′ 산출물은 사정권 밖」이라 **산문 대조기의 등록부에서 뺐고** "
                 "🔴 **정확히 그 사각에서 넷이 틀렸다**(티처 #103 M3). 965 가 등록부에 넣는다"),
        "🔴 분모: 등록한 주장": len(FIVEPRIME_CLAIMS),
        "🔴 분자: 산출물과 맞는 주장": len(FIVEPRIME_CLAIMS) - len(bad),
        "🔴 어긋난 주장": bad or "없음",
        "표": rows,
        "🔴 판정문 자기모순(같은 수를 둘로 적었나)": contra,
        "🔴 이 절의 `통과` 가 뜻하는 것": ("**965 의 대조기가 어긋남을 실제로 잡았나** — 964 판정문의 "
                              "네 수는 티처가 이미 틀렸다고 못 박았다. 🔴 **여기서 `통과` 는 "
                              "「판정문이 맞다」가 아니라 「내 대조기가 그 어긋남을 본다」**다"),
        "통과": len(bad) > 0 and contra,
    }


# ══════════════════════════════════════════════════════════════════════════
# §5 K1·K2 를 **실질 계수**로 다시 센다 (티처 #103 C4·M1 · 1순위)
# ══════════════════════════════════════════════════════════════════════════
def knob_reflects(func, param, pass_expr_src=None):
    """🔴 **자 D — 노브 되비추기.** 심기가 그 함수의 **매개변수를 뒤집는 것**이고,
    그 매개변수가 `통과` 식에 **직접** 나타나면 그 심기는 **코드를 안 문다**.
    `통과` 가 **정의상** 뒤집히기 때문이다(티처 #103 C4 의 K2).
    """
    src = ROOT / "runners/checks964.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef,)) and n.name == func:
            for d in ast.walk(n):
                if isinstance(d, ast.Dict):
                    for k, v in zip(d.keys, d.values):
                        if isinstance(k, ast.Constant) and k.value == "통과":
                            names = {x.id for x in ast.walk(v) if isinstance(x, ast.Name)}
                            return {"함수": func, "노브": param,
                                    "`통과` 식": ast.unparse(v)[:120],
                                    "🔴 노브가 `통과` 식에 직접 나오나": param in names}
    return {"함수": func, "노브": param, "🔴": "그 함수의 `통과` 식을 못 찾았다"}


def k1_k2_recount(ctx):
    from runners.checks964 import w3_double_prime, w6_prime         # noqa: PLC0415
    recs = ctx["complete"]

    # ── K1′ — 🔴 **진짜 함수에** 먹인다 (964 는 세 칸을 인라인 산술로 셌다) ──
    def call(rs):
        return w3_double_prime(rs)["통과"]
    dropped = [dict(d) for d in recs]
    dropped[0].pop("도메인", None)
    inflate = [dict(d, **{"도메인": "게임"}) for d in recs]         # 칸을 하나로 몰아준다
    tiny = [dict(recs[0])]                                          # 리스트를 1개로
    trials = collections.OrderedDict([
        ("⓪ 무변조", call(recs)),
        ("① 레코드 하나에서 `도메인` 키를 뗀다", call(dropped)),
        ("② 도메인 값을 전부 「게임」으로 몬다(칸 부풀리기)", call(inflate)),
        ("③ 레코드 리스트를 1개로 줄인다", call(tiny)),
    ])
    bit = [k for k, v in trials.items() if k != "⓪ 무변조" and v is not True]
    k1_expr = None
    tree = ast.parse((ROOT / "runners/checks964.py").read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and k.value == "🔴 빨개졌나":
                    if "plant_a" in ast.unparse(v):
                        k1_expr = v
    conj = [ast.unparse(x)[:70] for x in _conjuncts(k1_expr)] if k1_expr is not None else []
    called = [c for c in conj if "plant_" in c]

    K1 = {
        "🔴 무엇": ("964 의 K1 은 「🔴 빨개졌나」를 **5개 연언**으로 냈는데 그중 **셋이 "
                 "`w3_double_prime()` 을 안 부르는 인라인 산술**이다(티처 #103 M1). "
                 "🔴 **진짜 함수에 먹여 다시 센다**"),
        "964 의 연언 조각": conj,
        "🔴 분모: 연언 조각": len(conj),
        "🔴 분자: 진짜 함수를 부르는 조각": len(called),
        "🔴 인라인 산술 조각": len(conj) - len(called),
        "🔴🔴 진짜 함수에 먹인 결과": trials,
        "🔴 분모: 심어 본 것(무변조 제외)": len(trials) - 1,
        "🔴 분자: **실제로 떨어뜨린 것**": len(bit),
        "떨어뜨린 심기": bit,
        "🔴 964 는 이 자리를 5/5 초록으로 셌다": "실질은 %d/%d" % (len(bit), len(trials) - 1),
        "통과": trials["⓪ 무변조"] is True and len(bit) >= 1,
        "🔴 이 절의 `통과` 가 뜻하는 것": "무변조는 초록이고 **적어도 하나의 심기가 실제로 떨어뜨린다**",
    }

    # ── K2′ — 🔴 **노브 되비추기**. 심기가 아니다 ────────────────────────
    good, bad = w6_prime(ctx, include_app_lines=False), w6_prime(ctx, include_app_lines=True)
    diff = [k for k in good if k in bad and good[k] != bad[k]]
    K2 = {
        "🔴 무엇": ("티처 #103 C4: `include_app_lines` 를 뒤집으면 **바뀐 출력 키가 딱 하나** — "
                 "그 노브를 되비추는 칸이고 계산된 수는 전부 바이트 동일한데 판정식이 "
                 "`(not include_app_lines) and …` 라 **정의상 뒤집힌다**"),
        "🔴 노브를 뒤집었을 때 바뀐 출력 키": diff,
        "🔴 바뀐 키 수": len(diff),
        "🔴 `통과` 를 뺀 바뀐 키 수(티처 #103 C4 의 「딱 1개」)": len([k for k in diff if k != "통과"]),
        "🔴 계산된 수는 바이트 동일한가":
            all(good[k] == bad[k] for k in good
                if k not in diff and isinstance(good.get(k), (int, float))),
        "자 D(노브 되비추기)": knob_reflects("w6_prime", "include_app_lines"),
        "🔴 그래서": ("**K2 는 심기가 아니다.** 같은 함수의 판정식이 그 노브를 직접 읽으므로 "
                  "**코드를 안 물고도 뒤집힌다** — 964 의 심은 키 9/9 는 **실질 8/9**"),
        # 🔴 초판은 `len(diff) <= 2 and <정적 AST 사실>` 이라 **뿌리를 거의 안 물었다** —
        #   `runners/meta965.py` 의 자 B 가 상수로 잡아 줬다(F1). **실측 수로 다시 건다.**
        "통과": (len([k for k in diff if k != "통과"]) == 1 and "통과" in diff
               and all(good[k] == bad[k] for k in good
                       if k not in diff and isinstance(good.get(k), (int, float)))
               and knob_reflects("w6_prime", "include_app_lines")
               .get("🔴 노브가 `통과` 식에 직접 나오나") is True),
        "🔴 이 절의 `통과` 가 뜻하는 것": ("**K2 가 심기가 아님을 기계가 보인다** — 바뀐 키가 거의 없고 "
                              "노브가 판정식에 직접 나온다"),
    }
    return K1, K2


def _conjuncts(node):
    if isinstance(node, ast.Call) and node.args:
        return _conjuncts(node.args[0])
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        out = []
        for v in node.values:
            out.extend(_conjuncts(v))
        return out
    return [node]


# ══════════════════════════════════════════════════════════════════════════
# §6 🔴🔴 도메인 자 — 티처 #102 의 심기 ⓓ(도메인 뒤 11 → 1)를 문다 (3순위)
# ══════════════════════════════════════════════════════════════════════════
def domain_ruler(dom_before: dict, dom_after: dict):
    """🔴 **962·963·964 어디에도 도메인을 재는 `통과` 키가 없었다.**

    그래서 티처 #102 가 「도메인 뒤 11 → 1」을 심었을 때 **아무 검사도 안 물었다**
    (티처 #103 M4). 여기가 그 자리다 — 자를 **먼저** 세운다. 🔴 **수집은 안 한다.**

    셋을 본다: ① 뒤의 도메인 수가 앞보다 안 줄었나 ② **앞의 도메인이 전부 뒤에 있나**
    (집합 포함 — 수만 보면 도메인을 갈아치워도 안 걸린다) ③ Δ 를 낸다.
    """
    b, a = set(dom_before), set(dom_after)
    lost = sorted(b - a)
    gained = sorted(a - b)
    return {
        "🔴 무엇": "**도메인 자** — 수·집합 포함·Δ 셋을 같이 낸다(조항 62: 차집합은 홀로 못 선다)",
        "앞 도메인 수": len(b), "뒤 도메인 수": len(a),
        "🔴 Δ": len(a) - len(b),
        "🔴 사라진 도메인(앞 − 뒤)": lost or "없음",
        "🔴 새로 생긴 도메인(뒤 − 앞)": gained or "없음",
        "앞": sorted(b), "뒤": sorted(a),
        "🔴 무엇이면 떨어지나": ("뒤의 도메인 수가 앞보다 작거나, **앞의 도메인이 하나라도 뒤에서 "
                        "사라지면** 떨어진다. 🔴 티처 #102 의 심기 ⓓ(뒤를 1개로)가 여기 걸린다"),
        "통과": len(a) >= len(b) and not lost,
    }


def domain_section():
    from runners.checks964 import redenominate                      # noqa: PLC0415
    tab, ctx = redenominate()      # 🔴 `redenominate()` 는 **둘**을 낸다
    dom = tab["🔴 도메인"]
    before, after = dom["앞"], dom["뒤"]
    real = domain_ruler(before, after)

    # 🔴 심기 ⓓ — 티처 #102 가 심은 것을 **그대로** 심는다: 뒤를 한 도메인으로 뭉갠다
    one = {"게임": sum(after.values())}
    planted_d = domain_ruler(before, one)
    # 🔴 심기 ⓔ — 수는 같은데 **이름을 갈아치운다**(수만 보는 자는 원리상 못 본다)
    swapped = {("바뀐_%s" % k): v for k, v in after.items()}
    planted_e = domain_ruler(before, swapped)

    bit = [n for n, v in (("ⓓ 뒤를 한 도메인으로 뭉갠다", planted_d),
                          ("ⓔ 수는 같고 이름만 갈아치운다", planted_e))
           if v["통과"] is not True]
    return {
        "🔴 무엇": ("티처 #103 3순위: 「도메인 수를 재는 자리에 **자를 먼저 세워라**」. "
                 "🔴 **이 사이클은 새 수집을 안 한다** — 자만 세운다(사전등록 §4)"),
        "🔴🔴 실측(지금 자료)": real,
        "🔴 심기 ⓓ(티처 #102 가 심었고 964 까지 아무도 안 물었다)": planted_d,
        "🔴 심기 ⓔ(수는 같고 이름만 다르다 — 수만 보는 자는 원리상 못 본다)": planted_e,
        "🔴 분모: 심은 수": 2, "🔴 분자: **떨어뜨린 것**": len(bit),
        "떨어뜨린 심기": bit,
        "🔴 도메인 Δ": real["🔴 Δ"],
        "통과": real["통과"] is True and len(bit) == 2,
        "🔴 이 절의 `통과` 가 뜻하는 것": ("실측이 초록이고 **심은 둘이 모두 떨어진다** — "
                              "자가 실제로 문다는 뜻이다"),
    }, ctx


# ══════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════
# §7 🔴🔴 고친 W10 이 첫 주행에서 **묵은 산출물**을 잡았다 (1순위 C3 의 실물 성과)
# ══════════════════════════════════════════════════════════════════════════
def stale_artifact_section():
    """🔴🔴 **이 절이 이 사이클의 실물 성과다.**

    964 판 W10 은 `w10_check(rt, …)` 였다 — `rt` 가 같은 호출의 반환값이라 **디스크에 실린
    산출물을 원리상 안 본다.** 965 가 「`out961_curve.json` 을 다시 읽어 견주게」 고치고
    `curve961.py` 를 다시 돌리자 **첫 주행에서 붉었다.**

    🔴 **왜냐하면 `main` 에 커밋돼 있던 `out961_curve.json` 의 W10 칸은 「961 시대 `rulers()`」가
    낸 것**이고, 963 이 `#219`·`#220` 을 흡수하며 `rulers()` 를 **962 관측판**으로 갈면서
    **키 이름이 통째로 바뀌었는데 그 산출물을 아무도 다시 안 냈다.**
    즉 **커밋된 산출물과 커밋된 코드가 갈라져 있었고 964 까지 아무 검사도 그것을 못 봤다.**

    이 절은 그 사실을 **커밋에서 다시 꺼내** 못 박는다 — 산출물을 다시 냈어도 남는다.
    """
    import subprocess                                              # noqa: PLC0415
    from lab.adopt import rulers                                   # noqa: PLC0415
    from runners.curve961 import W10_SEC, RULERS_NEED              # noqa: PLC0415
    try:
        raw = subprocess.run(["git", "-c", "core.quotePath=false", "show",
                              "%s:runners/out961_curve.json" % REV_BEFORE],
                             cwd=str(ROOT), capture_output=True, check=True).stdout
        prev = json.loads(raw.decode("utf-8"))["§5 배선 검사"][W10_SEC]
    except Exception as e:                                         # noqa: BLE001
        return {"🔴 왜 `통과` 키를 안 내나": "%s: %s" % (type(e).__name__, e)}
    now = rulers(sum_delta=0.05, sum_T=0.02, sub_delta=0.005, sub_T=0.02,
                 perm_obs=0.05, perm_p95=-0.0005, card_T=0.00353)
    missing = [k for k in RULERS_NEED if k not in prev]
    return {
        "🔴 무엇": ("`%s` 에 커밋돼 있던 `out961_curve.json` 의 W10 칸이 **지금 `rulers()` 가 내는 "
                 "키를 갖고 있나** — 964 판은 이것을 **원리상 못 물었다**" % REV_BEFORE),
        "🔴 커밋된 산출물의 W10 키": sorted(prev),
        "🔴 지금 `rulers()` 가 내는 키": sorted(now),
        "🔴 분모: `rulers()` 가 내야 할 키(`RULERS_NEED`)": len(RULERS_NEED),
        "🔴 분자: 커밋된 산출물에 **없는** 키": len(missing),
        "🔴 없는 키": missing,
        "🔴 겹치는 키": sorted(set(prev) & set(now)),
        "🔴 그래서": ("**커밋된 산출물과 커밋된 코드가 갈라져 있었다.** 963 의 머지가 `rulers()` 를 "
                  "962 관측판으로 갈면서 키 이름이 통째로 바뀌었고 **그 산출물을 아무도 다시 안 냈다.** "
                  "🔴 964 의 W10 은 `rt` 를 자기 자신과 견주었으므로 **이 갈라짐을 원리상 못 봤다**"),
        "🔴 커밋된 산출물이 지금 코드와 맞나": len(missing) == 0,
        "🔴 무엇이면 떨어지나": ("커밋된 산출물이 지금 `rulers()` 와 **맞아떨어지면** 이 절이 붉다 — "
                        "그러면 내가 잡았다고 주장한 갈라짐이 **없었다는 뜻**이기 때문이다"),
        "통과": len(missing) > 0 and sorted(prev) != sorted(now),
        "🔴 이 절의 `통과` 가 뜻하는 것": ("🔴 **§4 와 같은 문법이다** — 여기서 `통과` 는 "
                              "「산출물이 맞다」가 아니라 **「내 자가 그 갈라짐을 실제로 본다」**다. "
                              "🔴 커밋 `%s` 에 묶인 사실이라 **산출물을 다시 내도 안 바뀐다**"
                              % REV_BEFORE),
    }


# ══════════════════════════════════════════════════════════════════════════
# §8 🔴🔴 F1 이 참이다 — 그 키를 **실제 꼴의 입력**으로도 재 본다
# ══════════════════════════════════════════════════════════════════════════
def f1_probe():
    """🔴🔴 **자기 기계가 자기를 잡았다.**

    `runners/meta965.py` 의 §4(F1) 가 내는 `통과` 식 `len(mine_taut) == 0` 을
    **자 B 가 상수로 판정했다.** 사전등록 §2 **F1** 이 정한 뜻에서 **이 사이클은 실패다.**

    🔴 **판정을 뒤집지 않는다.** 다만 **같은 식에 「실제 꼴」의 입력을 먹이면 어떻게 되는지**를
    기계로 재서 나란히 싣는다 — 966 이 이 둘을 보고 정하라.

    ⚠ **이 절은 F1 을 무효로 만들지 않는다.** 962 는 5/5 라 하고 실측 2/5, 963 은 7/7 → 5/7,
    964 는 9/9 → 실질 8/9 였다. **「내 판단으로는 괜찮다」가 바로 그 셋이 한 말이다.**
    """
    def expr(all_rows):
        mine = [r for r in all_rows
                if r["파일"] in ("runners/meta965.py", "runners/checks965.py")]
        mine_taut = [r for r in mine if r["🔴 항진명제인가"]]
        return len(mine_taut) == 0

    cases = collections.OrderedDict([
        ("① 내 파일에 항진명제가 **없다**",
         [{"파일": "runners/meta965.py", "🔴 항진명제인가": False}]),
        ("② 내 파일에 항진명제가 **있다**",
         [{"파일": "runners/meta965.py", "🔴 항진명제인가": True}]),
        ("③ 남의 파일에만 있다",
         [{"파일": "runners/checks963.py", "🔴 항진명제인가": True}]),
        ("④ 빈 목록", []),
    ])
    vals = collections.OrderedDict((k, expr(v)) for k, v in cases.items())
    return {
        "🔴 무엇": ("`runners/meta965.py` §4 의 `통과` 식을 **실제 꼴의 입력**으로 먹인다. "
                 "자 B 의 생성기는 `r[\"파일\"]` 이 정확히 그 두 경로여야 하는 조건을 "
                 "거의 못 맞춘다 — **생성기의 사각지대**인지 **진짜 항진명제**인지가 물음이다"),
        "실측": vals,
        "🔴 이 식이 내는 값의 가짓수": len(set(vals.values())),
        "🔴🔴 그래도 F1 은 참이다": ("사전등록 §2 F1 은 **「전수/무작위 변조에서 상수를 내면 실패」**라 "
                          "적었고 자 B 는 상수라 했다. 🔴 **판정을 안 뒤집는다** — "
                          "「내 판단으로는 괜찮다」가 962·963·964 가 한 바로 그 말이다"),
        "🔴 966 이 할 일": ("자 B 에 **꼴을 아는 생성기**를 달아라 — 그 자리가 읽는 열쇠뿐 아니라 "
                     "**그 자리가 견주는 값**(경로 문자열 등)까지 겨눠야 한다"),
        "통과": len(set(vals.values())) >= 2,
        "🔴 이 절의 `통과` 가 뜻하는 것": "**실제 꼴의 입력에서 이 식이 두 값을 다 낸다**(상수가 아니다)",
    }


def _path_literals(tree):
    """🔴🔴 **조항 63** — 「이 코드가 어느 파일을 여나」를 소스 문자열 **전량**에서 찾으면
    **자기 검사의 이름표가 자기를 문다.**

    실제로 이 러너의 첫 판이 그 병에 걸렸다: §-1 의 칸 이름이
    `"🔴 판 라벨 파일(`denominator.json`)을 여나"` 라서 **문자열 전량 훑기가 자기 이름표를
    물고 「판을 연다」로 붉어졌다.** 🔴 **바늘이 제 짚더미를 물었다 — 962 W8 · 963 이 기소한 그 병.**

    그래서 **경로가 되는 자리만** 본다: `ROOT / "…"` · `Path("…")` · `open("…")`.
    """
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            if isinstance(n.right, ast.Constant) and isinstance(n.right.value, str):
                out.append(n.right.value)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id in ("Path", "open") and n.args \
                and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[0].value, str):
            out.append(n.args[0].value)
    return out


def self_section():
    """🔴 964 의 §-1 은 `"통과": True` 리터럴이었다(티처 #103 C1).
    여기는 **자기 소스를 AST 로 재서** 낸다 — 코드를 고치면 값이 바뀐다."""
    src = (ROOT / "runners/checks965.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    paths = _path_literals(tree)
    board = [c for c in paths if "denominator" in c]
    ingest = [c for c in paths if "data/ingest" in c]
    writes = [ast.unparse(n)[:80] for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr in ("write_text", "write_bytes", "dump")]
    # 🔴 음성 대조 — 이 자가 100% 말고 다른 답을 낼 수 있나(조항 63 ②)
    probe = _path_literals(ast.parse('x = ROOT / "data/lab/denominator.json"'))
    return {
        "🔴 무엇": ("964 의 §-1 은 `\"무엇이면 떨어지나\": \"<문장>\", \"통과\": True` 였다 — "
                 "🔴 **그 문장을 평가하는 코드가 없었다**(티처 #103 C1). "
                 "여기는 **자기 소스의 경로 자리를 AST 로 잰다**"),
        "🔴 분모: 경로 리터럴 자리": len(paths),
        "경로 리터럴": sorted(set(paths)),
        "🔴 판 라벨 파일(`denominator.json`)을 여나": bool(board),
        "🔴 새 자료를 만드나(`data/ingest` 경로를 쓰나)": bool(ingest),
        "쓰는 자리": writes,
        "🔴 음성 대조(이 자가 다른 답을 낼 수 있나 — 조항 63 ②)": {
            "심은 소스": 'x = ROOT / "data/lab/denominator.json"',
            "이 자가 잡나": any("denominator" in c for c in probe)},
        "🔴🔴 자가 적발": ("이 절의 **첫 판**은 소스의 **문자열 전량**을 훑었고 "
                    "**자기 칸 이름표**(`denominator.json`·`data/ingest` 가 그 안에 있다)를 물어 "
                    "🔴 **붉게 나왔다.** 조항 63 그 자체 — **바늘이 제 짚더미를 물었다.** "
                    "경로가 되는 자리만 보게 고쳤다"),
        "🔴 무엇이면 떨어지나": ("이 러너가 판 파일을 열거나 `data/ingest` 에 쓰면 떨어진다. "
                        "🔴 **음성 대조가 그 자가 실제로 물 수 있음을 보인다**"),
        "통과": (not board) and (not ingest) and len(writes) >= 1
               and any("denominator" in c for c in probe),
    }


def main():
    t0 = dt.datetime.now(dt.timezone.utc)
    R = collections.OrderedDict()
    R["노트"] = 965
    R["레인"] = "수리"
    R["사전등록"] = "docs/prereg_965_metataut.md (측정 전 단독 커밋)"
    R["시작(UTC)"] = t0.isoformat()
    R["§-1 이 러너의 성질 — 🔴 **코드를 잰다**(964 C1 의 고친 판)"] = self_section()

    con = consumers_section()
    R["§1 🔴🔴 `lab.adopt.rulers` 소비자 — **AST 해소 · 저장소 전량**"] = con
    R["§2 별칭 소비자를 스키마 대조 안으로"] = alias_coverage(
        con["진짜 소비자"], con["칸별"])
    R["§3 🔴🔴 W10 고침의 검정력 — 무작위 **인자**가 판정을 무나"] = w10_power()
    R["§4 ⑤′ 산출물 ↔ 964 판정문 기계 대조"] = fiveprime_section()

    dsec, ctx = domain_section()
    K1, K2 = k1_k2_recount(ctx)
    R["§5-가 K1 실질 계수 — 🔴 **진짜 함수에 먹인다**"] = K1
    R["§5-나 K2 는 심기가 아니다 — 🔴 **노브 되비추기**"] = K2
    R["§6 🔴🔴 도메인 자 — 심기 ⓓ 를 문다"] = dsec
    R["§7 🔴🔴 고친 W10 이 **묵은 산출물**을 잡았다 — 커밋에서 다시 꺼내 못 박는다"] = \
        stale_artifact_section()
    R["§8 🔴🔴 F1 이 참이다 — 자기 기계가 자기를 잡았다(판정을 안 뒤집는다)"] = f1_probe()

    R["끝(UTC)"] = dt.datetime.now(dt.timezone.utc).isoformat()
    R["코드 sha256"] = hashlib.sha256(
        (ROOT / "runners/checks965.py").read_bytes()).hexdigest()

    secs = collections.OrderedDict(
        (k, v) for k, v in R.items() if isinstance(v, dict) and "통과" in v)
    red = [k for k, v in secs.items() if v["통과"] is not True]
    R["🔴 절 회계"] = {
        "분자: 통과한 절": len(secs) - len(red),
        "분모: `통과` 키를 가진 절": len(secs),
        "🔴 붉은 절": red or "없음",
        # 🔴 964 는 `len(red) == len(secs) - n_ok` 였다 — **같은 집합의 분할이라 원리상 참**
        #    (티처 #103 C2). 여기는 **붉은 절이 하나라도 있으면 떨어진다**.
        "🔴 964 는 무엇이었나": ("`len(red) == len(secs) - n_ok` — 🔴 **같은 집합의 분할을 견주므로 "
                        "어떤 입력에서도 참**이다. 965 의 메타 검사(자 B)가 뿌리 `R` 을 "
                        "무작위로 갈아 상수임을 확인했다"),
        "🔴 이 절의 `통과` 가 뜻하는 것": "**붉은 절이 하나도 없나**",
        "통과": not red,
    }
    return R


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    res = main()
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", a.out)
