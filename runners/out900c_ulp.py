# -*- coding: utf-8 -*-
"""수리 C · 미결 ①(이슈 #131) — **1 ULP 의 진짜 원인을 잰다.**

## 무엇이 미결이었나

`runners/out899a_gates.py` 의 ALLOW 가 `runners/text680.py` 를 **🔴미결**로 표시하면서
이렇게 적었다:

> 오늘 씨앗0 `0.4731063028988083` 이 `EXPECT_POOLED_K1_S0`(`0.4731063028988084`)와
> **1 ULP 다르다** --- 같은 수인데 **누적 순서가 다르다**

그 문장은 **가설이었고 아무도 재지 않았다.** 이 파일이 잰다(조항 59 --- 「고쳤다」와
「돌려 봤다」는 다른 문장이고, 「그럴 것이다」와 「재 봤다」도 다른 문장이다).

## 어떻게 재나 --- 적합 0회

씨앗0 의 **도메인별 ρ 열둘과 가중 열둘을 `runners/out898_wire.json` 에서 읽는다**
(손 전사 금지 · 조항 60). 그 열둘을 **순서만 바꿔** 가중 평균한다.
값은 하나도 안 바꾸고 **더하는 차례만** 바꾼다.

  ㄱ `sorted(dom)` 순      --- `wire898`·`board898` 이 쓰는 차례
  ㄴ 하네스 `list(data.dom)` 순 --- `lab/harness.py:168 Data.pooled` 이 쓰는 차례
  ㄷ `Data.pooled` **자신**을 두 차례로 각각 호출(재구현이 아니라 정본을 부른다)
  ㄹ 무작위 차례 20,000회 --- 서로 다른 double 이 **몇 개** 나오는지

## 왜 이게 중요한가

`==` 게이트를 세운 자리가 저장소에 여럿이다(`dose896:393` · `ruler890:245` ·
`verdict112`). 그 게이트가 **누적 차례 하나로 뒤집힌다면** 게이트가 재는 것은
「값이 같은가」가 아니라 「차례가 같은가」다. 어느 쪽인지 적어 두지 않으면
다음 세션이 「부동소수 정확일치 False」를 보고 **없는 회귀를 쫓는다.**

산출물: `runners/out900c_ulp.json`
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import datetime as dt                                           # noqa: E402
import hashlib                                                  # noqa: E402
import json                                                     # noqa: E402
import math                                                     # noqa: E402
import random                                                   # noqa: E402
import subprocess                                               # noqa: E402
import sys                                                      # noqa: E402
import time                                                     # noqa: E402
from pathlib import Path                                        # noqa: E402

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out900c_ulp.json"
SRC = ROOT / "runners/out898_wire.json"        #: 씨앗0 도메인별 ρ 의 동결 산출물


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def stamp() -> dict:
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    return {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git HEAD": head,
            "이 파일 sha256": sha(Path(__file__).resolve()),
            "읽은 산출물 sha256": {SRC.name: sha(SRC)}}


def pool_manual(S: dict, W: dict, order: list) -> float:
    """`wire898`·`board898`·`ruler890` 이 쓰는 손 누적을 **글자 그대로**.

    `sum(v*W[d] for d, v in s.items() if d in W) / sum(W[d] for d in s if d in W)`
    --- 파이썬 `sum` 은 왼쪽에서 오른쪽으로 더하므로 **dict 차례가 곧 누적 차례**다.
    """
    num = sum(float(S[d]) * W[d] for d in order if d in W)
    den = sum(W[d] for d in order if d in W)
    return num / den


def main():
    t0 = time.time()
    src = json.loads(SRC.read_text())
    #: 🔴 오늘 챔피언 경로 = post 배치 + 동률 평균. `wire898` 의 `post+scipy` 칸이 그것이다.
    S = src["도메인별 ρ"]["post+scipy"]
    W = src["도메인별 유보"]

    from dose896 import EXPECT_POOLED_K1_S0 as CANON       # noqa: E402
    import ruler890 as R890                                # noqa: E402
    from lab.harness import Data                           # noqa: E402
    import ff753 as FF                                     # noqa: E402

    d0 = FF.shell(FF.base())
    dom_order = list(d0.dom)                #: 하네스가 실제로 도는 차례
    srt = sorted(S)

    #: `Data.pooled` 은 `scores.items()` 차례로 더한다 --- dict 를 두 차례로 만들어
    #: **정본 함수 자신**을 두 번 부른다(재구현이 아니다).
    p_sorted_canon = d0.pooled({d: S[d] for d in srt if d in S})
    p_dom_canon = d0.pooled({d: S[d] for d in dom_order if d in S})

    p_sorted = pool_manual(S, W, srt)
    p_dom = pool_manual(S, W, [d for d in dom_order if d in S])

    random.seed(900)
    seen = {}
    for _ in range(20000):
        o = srt[:]
        random.shuffle(o)
        r = repr(pool_manual(S, W, o))
        seen[r] = seen.get(r, 0) + 1
    vals = sorted(float(k) for k in seen)
    ulp = math.ulp(CANON)

    res = {
        "무엇": "이슈 #131 미결① --- 씨앗0 판의 1 ULP 차가 어디서 나오나",
        "🔴 결론": ("누적 **차례**다. 값 열둘과 가중 열둘은 같고 더하는 순서만 다르다. "
                 "`sorted(dom)` 차례가 …83 을, 하네스 `list(data.dom)` 차례가 …84 를 낸다"),
        "입력": {"출처": str(SRC.relative_to(ROOT)),
               "칸": "도메인별 ρ.post+scipy (오늘 챔피언 경로 = post 배치 + 동률 평균)",
               "도메인 수": len(S), "유보 가중 합": sum(W.values())},
        "차례": {"sorted(dom)": srt, "하네스 list(data.dom)": dom_order},
        "손 누적(러너들이 쓰는 꼴)": {
            "sorted(dom) 차례": repr(p_sorted),
            "하네스 data.dom 차례": repr(p_dom),
            "두 차례가 같은 double 인가": p_sorted == p_dom,
        },
        "정본 Data.pooled 을 직접 호출": {
            "scores 를 sorted 차례로 넘김": repr(p_sorted_canon),
            "scores 를 data.dom 차례로 넘김": repr(p_dom_canon),
            "두 차례가 같은 double 인가": p_sorted_canon == p_dom_canon,
        },
        "상수와의 대조(손 전사 아님)": {
            "dose896.EXPECT_POOLED_K1_S0": repr(CANON),
            "ruler890.EXPECT_POOLED_K1_S0": repr(R890.EXPECT_POOLED_K1_S0),
            "ULP(=math.ulp)": ulp,
            "sorted 차례 − 정본 상수 (ULP)": (p_sorted - CANON) / ulp,
            "data.dom 차례 − 정본 상수 (ULP)": (p_dom - CANON) / ulp,
            "ruler890 상수 − 정본 상수 (ULP)": (R890.EXPECT_POOLED_K1_S0 - CANON) / ulp,
        },
        "무작위 차례 20,000회": {
            "서로 다른 double 수": len(seen),
            "값": {repr(v): seen[repr(v)] for v in vals},
            "폭(ULP)": (max(vals) - min(vals)) / ulp,
        },
        "🔴 그래서 게이트에 무엇을 쓰나": (
            "`==` 는 「값이 같은가」가 아니라 「누적 차례가 같은가」를 잰다. "
            "판 대조는 **ULP 거리**로 하고 정확일치 여부도 같이 찍는다(숨기지 않는다). "
            "도메인별 값 열둘은 누적이 없으므로 `==` 가 옳다"),
        "초": round(time.time() - t0, 1),
    }
    res.update(stamp())
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "차례"},
                     ensure_ascii=False, indent=1), flush=True)
    return res


if __name__ == "__main__":
    main()
