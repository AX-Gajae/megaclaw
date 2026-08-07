"""제품 도구 --- 새 팝업 기획서를 넣으면 자리를 낸다.

노트 76이 배선을 닫았고 80이 부분집합을, 82가 도메인 제거를, 83이 도메인
추가를, 85--88이 구조를 닫았다. \\textbf{모델 쪽 지렛대가 다 닫혔으므로 남은
일은 쓸 수 있게 만드는 것이다.}

**규약은 노트 77의 가장 엄격한 것 그대로다(규약 ④).**

    1. 지금까지 연 팝업의 **축만으로** 인자 공간을 만든다(라벨 안 씀)
    2. 새 기획 **한 장**을 그 공간에 투영한다
    3. 아홉 출처 도메인에서 각각 회귀를 학습해 예측한다
    4. 순위 평균으로 합치고 **과거 팝업들 사이에서의 자리**를 낸다

노트 77이 이 규약으로 미래 팝업 59건을 $\\rho=+$0.5268로 줄 세웠다.

**내는 것과 안 내는 것.**

    낸다     지금까지 연 팝업 중 상위 몇 퍼센트인가
    낸다     그 백분위에 해당하는 과거 팝업들의 일평균 방문자 범위
    안 낸다  "몇 명 올 것이다" --- 배수 구간이 [1.78, 14.52]다(노트 71 · 76)

사용:
  python3 -m state.score --demo
  python3 -m state.score --plan plan.json
  python3 -m state.score --plan plan.json --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import Ridge

from .audit import domains
from .onebyone import fit_apply, predict
from .orient import spaces
from .tri_domain import ALL5

SEED = 20260729

# 기획서에서 받는 열 속성. 전부 0~4 정수이고 모르면 빼면 된다(마스크 0).
ATTRS = {
    "target_breadth": "타깃 폭 --- 몇 명에게 닿게 만들었나",
    "venue_prominence": "매장 노출도 --- 자리가 얼마나 눈에 띄나",
    "entry_friction": "입장 허들 --- 들어오기가 얼마나 어렵나",
    "media_push": "미디어 투입 --- 홍보에 얼마나 썼나",
    "goods_scale": "굿즈 규모 --- 닿으면 무엇을 얻나",
    "experience_density": "체험 밀도 --- 안에서 할 일이 얼마나 되나",
    "photo_zones": "포토존 --- 찍을 자리가 얼마나 되나",
    "collab_strength": "컬래버 강도 --- 협업이 얼마나 센가",
    "ip_awareness": "IP 인지도 --- 원래 얼마나 알려진 IP인가",
    "season_fit": "계절 적합 --- 시기가 얼마나 맞나",
}
DEMO = {"target_breadth": 3, "venue_prominence": 4, "entry_friction": 1,
        "media_push": 3, "goods_scale": 3, "experience_density": 2,
        "photo_zones": 3, "collab_strength": 2, "ip_awareness": 4,
        "season_fit": 3}


def _popup_raw():
    """팝업의 원 속성과 라벨. 축 다섯은 슬롯 순서로 낸다."""
    from .own_axes import _popup_keep
    d = np.load("data/state/popup_v2.npz", allow_pickle=True)
    cols = [str(c) for c in d["names"]]
    keep = _popup_keep(d, cols)
    X = d["X"][keep]
    return X, cols


def score(plan: dict) -> dict:
    doms, names = domains()
    A, M, y, t = doms["팝업"]
    nm = names.get("팝업") or ALL5

    # 새 기획을 팝업 축 배열의 마지막 행으로 붙인다. 값은 0~4를 0~1로 옮긴다.
    v = np.zeros(A.shape[1])
    m = np.zeros(A.shape[1])
    for j, a in enumerate(nm):
        if a in plan and plan[a] is not None:
            v[j], m[j] = float(plan[a]) / 4.0, 1.0
    A2 = np.vstack([A, v])
    M2 = np.vstack([M, m])
    y2 = np.append(y, np.nan)
    t2 = np.append(t, np.nanmax(t))          # 시점은 가장 최근으로 둔다

    past = np.arange(len(y))
    Ft = fit_apply(A2, M2, np.nan_to_num(y2, nan=float(np.nanmean(y))), t2,
                   past, np.append(past, len(y)), names=nm)
    if Ft is None or Ft["rows"][-1] != len(y):
        return {"오류": "축이 모자라 투영할 수 없다 --- 공통 축 둘 이상이 필요하다"}

    F = spaces(doms, names)
    src = {k2: F[k2] for k2 in F if k2 != "팝업"}
    r = predict(src, Ft)
    if r is None:
        return {"오류": "출처 정렬 실패"}

    pct = float(rankdata(r)[-1] / len(r))
    # 과거 팝업의 실제 방문자에서 같은 백분위 근방을 찾는다
    raw = 10.0 ** np.asarray(F["팝업"]["y_raw"], float)
    band = max(3, int(round(len(raw) * 0.15)))
    order = np.argsort(rankdata(r[:-1]))
    pos = int(round(pct * (len(order) - 1)))
    lo_i, hi_i = max(0, pos - band // 2), min(len(order), pos + band // 2 + 1)
    near = np.sort(raw[order[lo_i:hi_i]])
    return {
        "백분위": round(pct * 100, 1),
        "순위": f"{len(r) - int(rankdata(r)[-1]) + 1} / {len(r)}",
        "비슷한 과거 팝업의 일평균 방문자": {
            "중앙": int(np.median(near)),
            "범위": [int(near.min()), int(near.max())],
            "표본": len(near)},
        "쓴 축": [a for a in nm if a in plan and plan[a] is not None],
        "안 쓴 축": [a for a in ATTRS if a not in nm],
        "과거 팝업 수": len(raw),
        "출처 도메인": len(src),
    }


def report(plan: dict, as_json: bool = False) -> int:
    r = score(plan)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if "오류" in r:
        print("오류:", r["오류"])
        return 1
    n = r["비슷한 과거 팝업의 일평균 방문자"]
    print("── 새 기획의 자리 " + "─" * 32)
    print(f"  지금까지 연 팝업 {r['과거 팝업 수']}건 중 "
          f"\033[1m상위 {100 - r['백분위']:.0f}%\033[0m  ({r['순위']})")
    print(f"  비슷한 자리의 과거 팝업 일평균 방문자 "
          f"중앙 {n['중앙']:,}명 · 범위 {n['범위'][0]:,}~{n['범위'][1]:,}명"
          f" ({n['표본']}건)")
    print(f"  쓴 축 {len(r['쓴 축'])}개 · 출처 도메인 {r['출처 도메인']}개")
    if r.get("안 쓴 축"):
        print(f"  안 쓴 축 {len(r['안 쓴 축'])}개 --- {', '.join(r['안 쓴 축'])}")
        print("    (팝업에만 있는 축이라 다른 도메인과 맞출 자리가 없다. "
              "노트 54에서 넣어 봤다가 -0.017로 뺐다.)")
    print("── 읽는 법 " + "─" * 38)
    print("  · 이 도구가 내는 것은 \033[1m순위\033[0m다. 미래 팝업 59건에서 "
          "ρ=+0.53으로 맞혔다(노트 77).")
    print("  · \033[1m몇 명 올지는 약속 못 한다.\033[0m 상하위 20%의 방문자 배수가"
          " 7.6배인데")
    print("    그 구간이 [1.8, 14.5]다(노트 76). 표본이 75건이라 좁힐 수 없다.")
    print("  · 쓸 곳 --- \033[1m어느 기획을 먼저 밀지 고르는 것\033[0m. "
          "쓰면 안 되는 곳 --- 방문자 수 약속.")
    return 0


def selftest(dom: str = "팝업", folds: int | None = None, k: int | None = None) -> dict:
    """그 도메인의 과거 레코드를 **빼고 매겨** 순위 상관을 낸다.

    도구가 실제로 쓰이는 방식과 같다 --- 지금까지 쌓인 것으로 공간을 만들고
    새 기획 하나를 넣는다(노트 77의 규약 ④).

    folds --- None 이면 200건 미만은 하나씩 빼고(LOO) 그 이상은 10겹으로
    나눈다. 큰 도메인에서 LOO 는 계산이 $n$배라 못 돌린다."""
    from sklearn.model_selection import KFold
    from .rank_test import spearman
    doms, names = domains()
    if dom not in doms:
        return {"오류": f"{dom} 없음"}
    A, M, y, t = doms[dom]
    nm = names.get(dom) or ALL5
    F = spaces(doms, names, k=k)
    src = {x: F[x] for x in F if x != dom}
    n = len(y)
    if folds is None:
        folds = n if n < 200 else 10
    pred, actual = [], []
    idx = np.arange(n)
    for tr, te in (KFold(folds, shuffle=True, random_state=SEED).split(idx)
                   if folds < n else ((np.delete(idx, i), np.array([i]))
                                      for i in idx)):
        Ft = fit_apply(A, M, y, t, tr, np.concatenate([tr, te]), names=nm, k=k)
        if Ft is None:
            continue
        r = predict(src, Ft)
        if r is None:
            continue
        rk = rankdata(r) / len(r)
        pos = {v: q for q, v in enumerate(Ft["rows"])}
        for i in te:
            if i in pos:
                pred.append(float(rk[pos[i]]))
                actual.append(float(y[i]))
    if len(pred) < 10:
        return {"오류": "투영된 레코드가 너무 적다"}
    return {"n": len(pred), "rho": round(float(spearman(np.array(pred),
                                                        np.array(actual))), 4)}


def table(k: int | None = None) -> dict:
    """열 도메인 전부에서 자기 검사. 어느 카테고리에 쓸 수 있는지 낸다."""
    doms, _ = domains()
    out = {}
    for d in doms:
        r = selftest(d, k=k)
        out[d] = r
        print(f"  {d:<7}{r.get('rho', float('nan')):>+9.4f}  n={r.get('n', 0)}",
              flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="새 팝업 기획서의 자리를 낸다")
    ap.add_argument("--plan", help="속성 JSON 파일 (0~4 정수)")
    ap.add_argument("--demo", action="store_true", help="예시로 한 번 돌려 본다")
    ap.add_argument("--json", action="store_true", help="JSON 으로 낸다")
    ap.add_argument("--attrs", action="store_true", help="받는 속성 목록")
    ap.add_argument("--selftest", action="store_true",
                    help="과거 레코드를 빼고 매겨 순위 상관을 낸다")
    ap.add_argument("--domain", default="팝업", help="자기 검사할 도메인")
    ap.add_argument("--table", action="store_true", help="열 도메인 전부 자기 검사")
    ap.add_argument("--k", type=int, default=None, help="성분 수(기본 2)")
    a = ap.parse_args()
    if a.attrs:
        for k, v in ATTRS.items():
            print(f"  {k:<20} {v}")
        return 0
    if a.table:
        print(f"자기 검사 --- 열 도메인 (성분 k={a.k or 2})")
        table(k=a.k)
        return 0
    if a.selftest:
        r = selftest(a.domain, k=a.k)
        if "오류" in r:
            print("오류:", r["오류"]); return 1
        print(f"자기 검사 --- {a.domain} {r['n']}건")
        print(f"  순위 상관 ρ = {r['rho']:+.4f}")
        return 0
    if a.demo:
        print("예시 기획:", json.dumps(DEMO, ensure_ascii=False), "\n")
        return report(DEMO, a.json)
    if not a.plan:
        ap.print_help()
        return 1
    return report(json.loads(Path(a.plan).read_text()), a.json)


if __name__ == "__main__":
    raise SystemExit(main())
