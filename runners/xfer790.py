"""노트 790 — **전이를 네 정의 모두에서 재고 4/4 만 통과로 센다.**

노트 789 가 정의에 따라 모양이 뒤집히는 도메인을 찾았다(애니 · 웹툰). 그래서
한 정의로 잰 전이는 그 정의의 성질일 수 있다. **네 정의 전부에서 문턱을 넘는
쌍만** 센다 --- 657 재현을 요구하는 것보다 **엄한** 자다.

재는 코드는 이제 `lab/decay.py` 에 있다(노트 789 · 규약 41).
"""
import json
import sys
import time

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/"
                   "ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import decay as D

NPERM = 200


def main():
    t0 = time.time()
    d0 = FF.shell(FF.base())

    per, wire0, names = {}, None, None
    for how in D.DEFS:
        dom, wire = D.by_domain(D.load_rates(how), d0)
        per[how] = dom
        wire0 = wire0 or wire
        nm = sorted(dom)
        if names is None:
            names = nm
        elif nm != names:
            print(json.dumps({"중단": f"정의마다 도메인이 다르다 {names} 대 {nm}"},
                             ensure_ascii=False), flush=True)
            return
    print(json.dumps({"배선": wire0, "도메인": names,
                      "행": {k: len(per[D.DEFS[0]][k][0]) for k in names},
                      "정의": list(D.DEFS)}, ensure_ascii=False), flush=True)

    cells = {}
    for a in names:
        for b in names:
            key = f"{a}→{b}"
            row = {}
            for how in D.DEFS:
                dom = per[how]
                row[how] = D.transfer(dom[a], dom[b], nperm=NPERM, seed=0)
            npass = sum(1 for h in D.DEFS if row[h].get("**넘나**"))
            cells[key] = {"정의별": row, "**넘은 정의 수**": npass,
                          "**4/4**": npass == 4,
                          "rho": [row[h].get("rho") for h in D.DEFS]}
            if a != b:
                print(f"  {key:22s} 넘은 정의 {npass}/4 · rho " +
                      " ".join(f"{(row[h].get('rho') or 0):+.3f}"
                               for h in D.DEFS), flush=True)

    cross = [k for k, v in cells.items()
             if v["**4/4**"] and k.split("→")[0] != k.split("→")[1]]
    both = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if cells[f"{a}→{b}"]["**4/4**"] and cells[f"{b}→{a}"]["**4/4**"]:
                both.append(f"{a}↔{b}")
    #: 무리 --- 양방향 쌍의 연결 성분
    par = {k: k for k in names}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for s in both:
        a, b = s.split("↔")
        par[find(a)] = find(b)
    grp = {}
    for k in names:
        grp.setdefault(find(k), []).append(k)
    clusters = [v for v in grp.values() if len(v) >= 2]

    #: 참고 --- 3/4 만 넘은 쌍(통과는 아니다. 사전등록이 4/4 라 했다)
    near = [k for k, v in cells.items()
            if v["**넘은 정의 수**"] == 3 and k.split("→")[0] != k.split("→")[1]]
    selfs = {c: cells[f"{c}→{c}"]["**넘은 정의 수**"] for c in names}

    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "도메인": names,
        "자기 전이 A→A 넘은 정의 수(참고 · 계단이 도는지)": selfs,
        "쌍별": cells,
        "**4/4 교차 순서쌍**": cross or "없음",
        "3/4 만(통과 아님 · 참고)": near or "없음",
        "**양방향 쌍**": both or "없음",
        "**무리**": clusters or "없음",
        "판정 (가) 무리 하나 이상": bool(clusters),
        "판정 (나) 4/4 는 있으나 양방향 0": bool(cross and not both),
        "판정 (다) 4/4 가 0": bool(not cross),
        "예측 ① 4/4 교차 ≤3": len(cross) <= 3,
        "예측 ② 세계애니→가 가장 잘 넘음":
            [k for k in cross if k.startswith("세계애니")],
        "예측 ③ 양방향 0": not both,
        "예측 ④ 게임 낀 쌍은 안 넘음":
            not [k for k in cross if "게임" in k],
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
