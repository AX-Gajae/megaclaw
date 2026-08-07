"""도서 도메인의 결측 누출을 잡는다.

`state.rewire_test`에서 도서 타깃 폭을 판형만으로 좁히자 자기 상관이 0.459에서
0.213으로 떨어졌다. 처음에는 장르 수가 억제 변수(Horst 1941)라고 읽었다.
틀렸다 --- 판형이 61%만 관측되므로 판형만 쓰면 표본이 396에서 242로 줄고,
같은 242건에서는 기준도 0.220이다. 커버리지 효과였다.

그런데 그 확인 과정에서 훨씬 나쁜 것이 나왔다.

    판형 있음  242건  전부 종이책   판매지수 log 평균 4.30
    판형 없음  154건  전부 전자책   판매지수 log 평균 3.32

**판형 결측이 곧 전자책 여부다.** 두 형식의 라벨이 열 배 차이 나므로, 판형을
쓰는 축은 물리량을 재는 척하면서 실은 매체 형식을 맞힌다. 부분집합 안에서 재면
종이책 0.220, 전자책 0.045로 뚝 떨어진다.

노트 34의 ``판형으로 배선하니 자기 상관이 3.4배''는 이 누출을 포함한 값이다.
같은 의심이 양장 여부(전자책은 항상 0)에도 걸린다.

Kaufman(2012)의 분류로는 **결측 패턴 자체가 정보를 담는** 누출이다. 결측을
0으로 채우든 마스크로 남기든, 결측 여부가 라벨과 상관되면 축이 그것을 학습한다.

**처리 세 가지를 비교한다.**

  형식 통제   라벨에서 형식별 평균을 뺀다. 396건을 유지하되 형식 신호를 없앤다.
  종이책만    242건으로 도메인을 좁힌다. 형식이 하나이므로 누출이 없다.
  현행        아무것도 안 한다(비교 기준).

사용: python3 -m state.format_leak
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .rewire_test import (VARIANTS, _book_order, apply, book_hardcover_col,
                          evaluate, self_corr)
from .tri_domain import load_all

OUT = Path("data/state/format_leak.json")


def book_format() -> np.ndarray:
    rec = json.loads(Path("data/state/book_records.json").read_text())
    return np.array([((rec.get(k) or {}).get("book_format") or "?")
                     for k in _book_order()])


def control_format(doms):
    """도서 라벨에서 형식별 평균을 뺀다. 형식 간 차이는 도메인 성질이 아니다."""
    A, M, y, t = doms["도서"]
    f = book_format()
    yy = y.copy().astype(float)
    for g in np.unique(f):
        s = f == g
        if s.sum() >= 5:
            yy[s] = y[s] - y[s].mean()
    out = dict(doms)
    out["도서"] = (A, M, yy + y.mean(), t)
    return out


def paper_only(doms):
    """전자책을 빼고 종이책만 남긴다."""
    A, M, y, t = doms["도서"]
    s = book_format() != "EBook"
    out = dict(doms)
    out["도서"] = (A[s], M[s], y[s], t[s])
    return out


TREATMENTS = {
    "현행": lambda d: d,
    "형식 통제": control_format,
    "종이책만": paper_only,
}


def run() -> dict:
    base = load_all()
    f = book_format()
    print("=== 도서 형식 분포 ===")
    for g, c in zip(*np.unique(f, return_counts=True)):
        y = base["도서"][2][f == g]
        print(f"  {g:<12}{c:>4}건   라벨 평균 {y.mean():.2f}  SD {y.std():.2f}")

    out = {}
    print(f"\n{'처리':<10}{'배선':<14}{'도서 n':>7}{'도서 자기':>9}"
          f"{'유의':>7}{'평균이득':>10}")
    for tname, tfn in TREATMENTS.items():
        d0 = tfn(base)
        for vname in ("기준(현재)", "도서 굿즈=양장"):
            if tname == "종이책만" and vname == "도서 굿즈=양장":
                # 열 교체 함수는 396건 순서를 낸다. 종이책 부분집합에 맞춰 자른다.
                A, M, y, t = d0["도서"]
                v, m = book_hardcover_col()
                s = book_format() != "EBook"
                A = A.copy(); M = M.copy()
                A[:, 4], M[:, 4] = v[s], m[s]
                d = dict(d0); d["도서"] = (A, M, y, t)
            else:
                d = apply(d0, list(VARIANTS[vname]))
            r = evaluate(d)
            out[f"{tname} · {vname}"] = {k: v for k, v in r.items() if k != "lam"}
            print(f"{tname:<10}{vname:<14}{len(d['도서'][2]):>7}"
                  f"{r['self']['도서']:>9.3f}{r['sig']:>5}/12{r['gain']:>+10.4f}")

    print("\n=== 형식 통제가 다른 도메인에 미치는 영향 (자기 상관) ===")
    for k in ("팝업", "아이돌", "게임"):
        a = out["현행 · 기준(현재)"]["self"][k]
        b = out["형식 통제 · 기준(현재)"]["self"][k]
        print(f"  {k:<7}{a:+.3f} → {b:+.3f}")

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
