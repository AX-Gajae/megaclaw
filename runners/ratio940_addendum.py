# -*- coding: utf-8 -*-
"""팔 940 부속 — 🔴🔴 **사후다. 결과를 보고 넣었다.**

`runners/out940_ratio.json` 은 **사전등록한 그대로** 돌았고 **안 고친다**(증거물).
이 부속은 그 뒤에 붙인 것이고, **사전등록의 판정을 안 바꾼다.**

왜 붙이나 — 두 가지가 §B·§C 를 돌리고 나서야 드러났다.

**ㄹ. 사전등록의 주입 ㄷ 은 자기 문턱을 못 넘었다.**
   ㄷ 은 `rel_thr` 을 `T=0.0151220` 으로 심었는데 922 N2 의 상대차는 **0.0047266** 이라
   심은 문턱보다 **작다** — 그러니 갈래가 안 바뀌는 게 당연하다.
   🔴 **즉 ㄷ 은 「배선이 없다」를 보인 것이 아니라 「내가 고른 주입값이 관측값을 안 넘었다」를
   보였다.** 사전등록 §4 조건 ② 는 그래서 **미충족으로 남는다**(그 판정은 안 바꾼다).
   이 부속은 **관측값보다 작은 문턱**을 심어서 **그 갈래가 살아 있는지**를 따로 묻는다.

**ㅁ. 925 의 `r` 은 어느 판을 짝지었는지에 따라 26배 갈린다.**
   본 러너는 925 G2 의 상대차(원판 세계에서 잰 수)를 **주 판정 판 [둘 다]의 G** 와 짝지어
   `r=3.1967` 을 냈다. 🔴 **그 둘은 분모가 다른 판이다**(조항 60). 네 판 전부로 낸다.

사용: python3 runners/ratio940_addendum.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from state import ratio940                    # noqa: E402

#: 🔴 **같은 주입 드라이버를 쓴다** — 베끼지 않는다(A-4 가 잡은 「손 사본」 병을 안 되풀이한다)
import importlib.util as _ilu                 # noqa: E402
_spec = _ilu.spec_from_file_location("ratio940_run", str(ROOT / "runners/ratio940_run.py"))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
DRIVER = _mod.DRIVER

OUT = ROOT / "runners/out940_addendum.json"
SCRATCH = Path("/private/tmp/claude-501/-Users-ax-world-model/"
               "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad/g940")
#: 🔴 922 N2 의 상대차(0.0047266)**보다 작은** 문턱 — 갈래가 살아 있으면 §6-4 로 가야 한다
PLANT_BELOW = 0.001


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jload(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def run_inject(thr: float, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    outp = SCRATCH / f"out922_{tag}.json"
    env = dict(os.environ, G940_MODE="다", G940_CONST=repr(thr),
               G940_THR=repr(thr), G940_OUT=str(outp))
    env.pop("WM_ALLOW_PAID_API", None)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(DRIVER)
        drv = fh.name
    p = subprocess.run([sys.executable, drv], env=env, capture_output=True,
                       text=True)
    ok = outp.exists()
    d = json.loads(outp.read_text(encoding="utf-8")) if ok else {}
    return {
        "심은 문턱": thr, "종료코드": p.returncode,
        "🔴 산출물이 났나(종료코드를 성공으로 안 읽는다)": ok,
        "산출물": str(outp),
        "산출물에 적힌 문턱": d.get("설정", {}).get("비교가능성 문턱(상대)"),
        "N2 상대차": d.get("⑦ 판정 재료(사전등록 §6)", {}).get("N2 상대차"),
        "N2 관문 결과(불리언)": d.get("⑦ 판정 재료(사전등록 §6)", {}).get("N2 비교가능성 통과"),
        "🔴 판정문": d.get("🔴 판정 (사전등록 §6 을 기계로 적용)", {}).get("판정문"),
        "진짜 개선(일)": d.get("⑦ 판정 재료(사전등록 §6)", {}).get("진짜 개선(일)"),
    }


def part_R() -> dict:
    old = jload("runners/out922_permfix.json")
    ov = old["🔴 판정 (사전등록 §6 을 기계로 적용)"]["판정문"]
    ob = old["⑦ 판정 재료(사전등록 §6)"]["N2 비교가능성 통과"]
    rel = old["⑦ 판정 재료(사전등록 §6)"]["N2 상대차"]
    r = run_inject(PLANT_BELOW, "below")
    flipped = (r["🔴 판정문"] != ov)
    return {
        "무엇": "🔴🔴 **사후** — 관측 상대차보다 **작은** 문턱을 심으면 갈래가 바뀌나",
        "🔴 왜 이 값인가": f"922 N2 의 상대차 = {rel} 이다. 사전등록의 주입 ㄷ 은 "
                    f"{0.0151219535025886810} 을 심었는데 그건 관측값보다 **크다** — "
                    f"넘을 수 없는 문턱을 심고 「안 바뀐다」를 본 것이다. "
                    f"여기서는 {PLANT_BELOW} 을 심는다(관측값의 "
                    f"{PLANT_BELOW / rel:.3f}배)",
        "정본 판정문": ov, "정본 N2 관문 결과(불리언)": ob,
        "심은 판": r,
        "🔴🔴 갈래가 바뀌었나": flipped,
        "🔴 관문 불리언이 뒤집혔나": r["N2 관문 결과(불리언)"] != ob,
        "🔴 상대차·개선은 그대로인가(주입이 자료를 안 건드렸다는 확인)": {
            "N2 상대차 같은가": r["N2 상대차"] == rel,
            "진짜 개선 같은가": r["진짜 개선(일)"] == old["⑦ 판정 재료(사전등록 §6)"]["진짜 개선(일)"],
        },
        "🔴 이것이 사전등록 판정을 바꾸나": "🔴 **안 바꾼다.** 사전등록 §4 의 조건 ② 는 "
                            "`out940_ratio.json` 이 낸 대로 **미충족**이다. "
                            "이 부속이 답하는 것은 다른 물음이다 — "
                            "**「그 갈래가 살아 있는가」**",
        "🔴 그래서 무엇을 아나": (
            "갈래는 **살아 있다** — 관측값을 넘는 문턱을 심으면 판정문이 §6-4(판정 불능)로 간다. "
            "🔴 **그러나 그 길로 들어가려면 `comparability` 의 기본 인자를 파이썬 내부에서 "
            "바꿔야 한다**(`__kwdefaults__`). 상수 `COMPARABLE_REL` 을 고치는 길로는 "
            "원리상 못 간다(본 러너 §A-5·§B-ㄴ)"
            if flipped else
            "🔴 갈래가 **안 살아 있다** — 관측값을 넘는 문턱을 심어도 판정문이 안 바뀐다. "
            "그러면 `if` 문이 있는데도 도달 불가라는 뜻이고, 그것을 따로 물어야 한다"),
    }


def part_M() -> dict:
    """🔴 925 의 네 판으로 `r` 을 낸다 — **조항 60**(분모가 다른 판을 짝짓고 있었다)."""
    d925 = jload("runners/out925_gapsplit.json")
    g = d925["⑥ 관문 신고 (#178) — 🔴 관문마다 도달 가능 폭 ÷ 문턱"]
    g2 = g["G2"]
    m = float(g2["실측"])
    cr = float(g2["진짜 기후값 MAE"])
    판 = {"[둘 다] 주 판정 판": float(g["G1 주 판정"]["🔴 점추정 차(진짜 − 귀무)"])}
    for k, v in g["G1 병기(나머지 세 판)"].items():
        판[k] = float(v["🔴 점추정 차(진짜 − 귀무)"])
    rep = {}
    for k, G in 판.items():
        rep[k] = ratio940.sensitivity_ratio(
            f"925 G2 × {k}", rel_values=[m], G=G, cr=cr, L_used=1.0,
            used_for="🔴 아무것도 안 갈랐다 — 925 는 자기 산출물에 「이번엔 판정에 안 쓴다」라 적었다",
            note="🔴 L 을 못 쟀다(B=1). L ≥ 1 이므로 이 r 은 **하한**이다")
    rs = {k: v["🔴🔴 r = m · L_used · cr / G"] for k, v in rep.items()}
    return {
        "무엇": "🔴🔴 **사후** — 925 의 `r` 이 어느 판을 짝지었는지에 따라 얼마나 갈리나",
        "🔴 조항 60 경고": "상대차 m 은 **원판 세계의 기후값 MAE** 에서 나온 수이고, "
                    "G 는 **각 판의 진짜−귀무 점추정 차**다. 🔴 **네 판의 G 에 같은 m 을 "
                    "붙이는 것은 「같은 왜곡이 네 판에 그대로 전달된다」를 가정하는 것**이고 "
                    "그 가정은 **안 잰 것**이다(925 는 판마다 표가 다르다). "
                    "그러므로 아래 넷 중 **원판 판만이 m 과 같은 세계에서 나온 수**다",
        "판별": rep,
        "🔴 r 한눈에": rs,
        "🔴 몇 배 갈리나": max(rs.values()) / min(rs.values()),
        "🔴 본 러너가 쓴 판": "[둘 다] 주 판정 판 — r = %.6f" % rs["[둘 다] 주 판정 판"],
        "🔴 m 과 같은 세계의 판": "원판 — r = %.6f" % rs["원판"],
        "🔴 그래서 무엇을 고쳐 읽나": (
            "본 러너 §C 의 「925 G2 · r = 3.1967」은 **분모가 다른 판을 짝지은 수**다. "
            "같은 세계에서 낸 수는 **원판의 r = %.4f** 이다. "
            "🔴 **둘 다 참이고 뜻이 다르다** — 앞의 것은 「주 판정 판의 빈틈이 얼마나 좁은가」를, "
            "뒤의 것은 「원판에서 이 왜곡이 얼마나 작은가」를 말한다. "
            "**r 은 관문의 성질이 아니라 「관문 축 × 판」의 성질이다**"
            % rs["원판"]),
    }


def main() -> None:
    t0 = dt.datetime.now(dt.timezone.utc)
    R = part_R()
    M = part_M()
    out = {
        "팔": "940 부속 — 🔴🔴 **사후다. 결과를 보고 넣었다**",
        "🔴 무엇이 사후인가": [
            "ㄹ — 사전등록의 주입 ㄷ 이 관측값보다 **큰** 문턱을 심었다는 것을 "
            "**결과를 보고** 알았다. 관측값보다 작은 문턱을 새로 심는다",
            "ㅁ — 925 의 G 를 어느 판에서 읽느냐로 r 이 갈린다는 것을 "
            "**§C 를 낸 뒤에** 알았다",
        ],
        "🔴 사전등록 판정을 바꾸나": "**안 바꾼다.** `runners/out940_ratio.json` 은 안 고쳤다",
        "본 산출물 sha256(안 고쳤다는 증거)": sha(ROOT / "runners/out940_ratio.json"),
        "코드 sha256": {f: sha(ROOT / f) for f in
                      ["runners/ratio940_addendum.py", "runners/ratio940_run.py",
                       "state/ratio940.py", "state/perm922.py"]},
        "ㄹ · 관측값보다 작은 문턱을 심으면": R,
        "ㅁ · 925 의 r 은 판마다 얼마나 갈리나": M,
        "시작 UTC": t0.isoformat(),
    }
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat()
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)
    print("갈래가 바뀌었나:", R["🔴🔴 갈래가 바뀌었나"])
    print("925 r:", json.dumps(M["🔴 r 한눈에"], ensure_ascii=False))


if __name__ == "__main__":
    main()
