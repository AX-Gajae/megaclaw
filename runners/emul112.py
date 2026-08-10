"""이슈 #112 — **837 이 실제로 잰 조립**을 오늘 코드로 흉내 내 판을 다시 잰다.

`runners/rebase837.py:44-56` 은 영화를 손으로 붙였다: 11도메인 공통 이름
**전체**(36개)를 주되 **KOBIS 5축만 실값**이고 나머지 31열은 `A=0.5 · M=0`
이다. 오늘 파이프라인은 영화를 `state/tri_domain.py:179 _from_axes_json` 으로
만들고, `lab/loop.py` 의 챔피언 껍질이 영화에도 trend·cal·wiki·tag·fund·gen·
grp 을 붙**이려 한다** --- 837 이 잰 판에는 없던 열이라고 **가정**했다.

여기서는 오늘 자료·오늘 코드 위에서 **영화의 31 열만 837 처럼 중립화**하고
씨앗 0~11 로 판을 잰다. 0.4710 이 돌아오면 차이의 원인은 「영화 조립」이다.

🔴 **결과(2026-08-10) --- 가정이 틀렸고, 영화 조립은 원인이 아니다.**
씨앗 0 이 중립화 **안 한** 판과 `0.4724867181663707` 로 **비트 동일**이었다.
즉 중립화가 무연산이다 --- 오늘 파이프라인의 영화도 그 31열이 **이미**
`0.5/마스크 0` 이다(제공자에 영화 항목이 없어 `else` 로 떨어진다).
같은 결론을 **적합 0회**로 더 강하게 얻었다: 837 손 조립과 오늘 영화를 직접
대조하니 행 887=887 · 축 이름 **순서까지 동일** · y/yr/t 최대차 0.0 ·
**열이 다른 축 0개** · 유보 406=406 · 영화 ρ 0.485(837 인쇄) 대 0.48485(오늘).
그래서 나머지 11씨앗은 안 돌리고 `runners/refit112.py`(진짜 원인)에 CPU 를 넘겼다.
→ 원인은 `runners/out112_verdict.json` 의 ② 를 봐라(채점 배치 + 적합 경로).

산출물: `runners/out112_emul837.json` --- **씨앗 0 에서 중단해 미생성**.
로그만 남았다: `runners/out112_emul837.log`

🔴 **정오(2026-08-10 · 이슈 #123 · 티처 #61 C7) --- 딱지만이다. 결론은 안 바뀐다.**
위 13행의 `0.4724867181663707` 은 **노트 898 이전(서수 순위) 챔피언의 씨앗0** 이다.
898 이 판을 자에 맞추면서(동률 평균) 정본 씨앗0 은 **0.4731063028988084** 로
옮겨갔다(`runners/dose896.py:EXPECT_POOLED_K1_S0`). 이 파일은 상수를 **게이트로
쓰지 않고 산문으로만** 이고 있어서 죽은 채로 조용히 통과하는 자리가 없다 ---
그래서 딱지만 붙인다. 「중립화가 무연산이다」는 두 판 어느 쪽으로 재도 참이다
(대비가 영화 31열이지 순위 함수가 아니다).
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")

from lab.harness import Data, evaluate
from runners import ff753 as FF

T = 2025.0
SEEDS = tuple(range(12))
ALL5 = ["target_breadth", "venue_prominence", "entry_friction", "media_push",
        "goods_scale"]
OUT = "/Users/ax/world_model/runners/out112_emul837.json"


def main():
    t0 = time.time()
    d0 = FF.shell(FF.base())
    nm = list(d0.names["영화"])
    A, M, y, t = d0.dom["영화"]
    A2, M2 = np.array(A, float).copy(), np.array(M, float).copy()
    killed = [a for j, a in enumerate(nm) if a not in ALL5]
    for j, a in enumerate(nm):
        if a not in ALL5:
            A2[:, j] = 0.5
            M2[:, j] = 0.0
    dom = dict(d0.dom)
    dom["영화"] = (A2, M2, y, t)
    d1 = Data(dom, dict(d0.names), dict(d0.yr))
    W = d1.weights(T)
    print(json.dumps({"중립화한 열 수": len(killed), "영화 축 수": len(nm),
                      "유보 가중 합": int(sum(W.values()))},
                     ensure_ascii=False), flush=True)

    vals, per = [], {}
    for s in SEEDS:
        sc = evaluate(lambda s=s: FF.CLS(seed=s), d1, T=T)
        v = float(d1.pooled(sc, T=T))
        vals.append(v)
        for k, x in sc.items():
            if np.isfinite(x):
                per.setdefault(k, []).append(float(x))
        print(f"  씨앗 {s}: {v!r}  ({time.time()-t0:.0f}s)", flush=True)

    a = np.array(vals, float)
    res = {"무엇": "오늘 코드·오늘 자료 · 영화의 비-KOBIS 31열을 837 처럼 0.5/마스크0",
           "중립화한 열": killed,
           "씨앗별 판(전정밀)": vals,
           "평균": float(a.mean()),
           "SD(ddof=1)": float(a.std(ddof=1)),
           "SE": float(a.std(ddof=1) / np.sqrt(len(a))),
           "도메인별 ρ(씨앗 평균)": {k: float(np.mean(v)) for k, v in sorted(per.items())},
           "유보 가중 합": int(sum(W.values())),
           "초": round(time.time() - t0, 1)}
    print("=== 모아서 ===", flush=True)
    print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("완료", flush=True)


if __name__ == "__main__":
    main()
