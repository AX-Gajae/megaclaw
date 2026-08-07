"""배선을 의미가 아니라 검정으로 정한다.

노트 34까지 같은 실수를 세 번 했다.

  노트 25  게임의 굿즈 규모를 Steam 기능 수로 --- 폭 인자에 실려 신호의 75%를 놓침
  노트 28  게임의 매장 노출도를 퍼블리셔 이력으로 --- 물리량은 맞는데 기하를 흔듦
  노트 34  도서의 굿즈 규모를 쪽수로, 타깃 폭을 장르 수로 --- 둘 다 무효(r≈0)

매번 *의미로는 맞아 보이는* 배선이었다. 노트 28에 규칙을 적어 놓고도
(``의미로 판단할 수 있는 것은 후보 자격까지이고 채택은 검정으로만'') 노트 34에서
또 의미로 배선했다.

이 모듈은 그 규칙을 코드로 만든다. 도메인마다 관측 가능한 원변수를 전부 모아
각 축 슬롯에 무엇을 넣을지 **검정으로** 고른다.

**두 제약을 지킨다.**

  · 누출 금지 --- 라벨을 쓰지 않는 변수만 후보로 둔다. 사전 이력 통계는 시간
    인과적으로 계산된 것만 쓴다.
  · 정합성 --- 같은 축에 들어가는 변수는 도메인 간에 같은 기능을 재야 한다
    (노트 20·23). 그래서 축별로 '허용 유형'을 선언하고 그 안에서만 고른다.

선택 기준은 도메인의 **자기 상관**이다. 노트 33이 전이 성능을 지배한다고 밝힌
그 값이며, 노트 34가 배선으로 바뀐다는 것을 보였다.

사용: python3 -m state.wiring_search
"""
from __future__ import annotations

import glob
import json
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

from .tri_domain import detrend, z

SEED = 20260728
ASOF = date(2026, 7, 28)

# 축별 허용 유형 --- 도메인 간 기능 정합을 강제한다(노트 20·23).
#   breadth  얼마나 많은 사람에게 닿을 수 있게 만들었나
#   venue    유통·노출 자리를 얼마나 확보했나
#   friction 닿는 데 무엇을 치르나
#   goods    닿으면 무엇을 얻나
SLOT_KINDS = {
    "target_breadth": {"breadth"},
    "venue_prominence": {"venue"},
    "entry_friction": {"friction"},
    "goods_scale": {"goods"},
}


def _elapsed(d: str) -> float:
    try:
        return float(np.log10(max((ASOF - date(*map(int, d.split("-")))).days, 1)))
    except (ValueError, TypeError):
        return np.nan


def idol_vars():
    ax = json.loads(Path("data/state/idol_axes.json").read_text())
    alb = json.loads(Path("data/state/idol_album_meta.json").read_text())
    recs = {}
    for f in glob.glob("data/idol_records/*.json"):
        r = json.loads(Path(f).read_text())
        recs[r["record_id"]] = r
    ids = [k for k in ax if (ax[k].get("debut_date") or "")[:4].isdigit()]
    t = np.array([float(ax[k]["debut_date"][:4]) for k in ids])
    y = np.array([ax[k]["y"] for k in ids])
    V = {
        ("인원 수", "breadth"): [recs.get(k, {}).get("member_count") for k in ids],
        ("서바이벌 출신", "breadth"): [1.0 if recs.get(k, {}).get("survival_show") else 0.0
                                  for k in ids],
        ("사전 화제", "breadth"): [1.0 if recs.get(k, {}).get("pre_debut_signals") else 0.0
                                for k in ids],
        ("걸그룹", "breadth"): [1.0 if recs.get(k, {}).get("gender") == "girl" else 0.0
                             for k in ids],
        ("소속사 사전 데뷔", "venue"): [ax[k]["axes"]["venue_prominence"]
                                  if ax[k]["mask"]["venue_prominence"] else None for k in ids],
        ("앨범 정가", "friction"): [(alb.get(k) or {}).get("unit_price") for k in ids],
        ("앨범 버전 수", "goods"): [(alb.get(k) or {}).get("versions") for k in ids],
    }
    return V, y, t


def game_vars():
    ax = json.loads(Path("data/state/game_axes.json").read_text())
    rec = json.loads(Path("data/state/game_records.json").read_text())
    fr = json.loads(Path("data/state/game_friction.json").read_text())
    ids = [k for k in ax if rec.get(k, {}).get("y_w30")
           and not rec[k].get("y_w30_truncated")]
    t = np.array([_elapsed(ax[k]["release_date"]) for k in ids])
    y = np.log10(np.maximum([rec[k]["y_w30"] for k in ids], 1))
    V = {
        ("지원 언어 수", "breadth"): [rec[k].get("n_lang") or 0 for k in ids],
        ("장르 수", "breadth"): [len(rec[k].get("genres") or []) for k in ids],
        ("플랫폼 수", "breadth"): [rec[k].get("n_platform") or 0 for k in ids],
        ("퍼블리셔 사전작", "venue"): [ax[k]["axes"]["venue_prominence"] for k in ids],
        ("가격", "friction"): [rec[k].get("price_krw") or None for k in ids],
        ("무료 여부", "friction"): [1.0 if rec[k].get("is_free") else 0.0 for k in ids],
        # 연령 등급은 0이 '전체 이용가'라는 정상값이다 --- 결측이 아니다
        ("연령 등급", "friction"): [float((fr.get(k) or {}).get("required_age") or 0)
                                if fr.get(k) else None for k in ids],
        ("최소 RAM", "goods"): [(fr.get(k) or {}).get("ram_gb") for k in ids],
        ("설치 용량", "goods"): [(fr.get(k) or {}).get("disk_gb") for k in ids],
        ("Steam 기능 수", "goods"): [rec[k].get("n_category") or 0 for k in ids],
    }
    return V, y, t


def book_vars():
    ax = json.loads(Path("data/state/book_axes.json").read_text())
    rec = json.loads(Path("data/state/book_records.json").read_text())
    ids = [k for k in ax if rec.get(k)]
    t = np.array([_elapsed(ax[k]["pub_date"]) for k in ids])
    y = np.array([ax[k]["y"] for k in ids])
    V = {
        ("판형 높이(역)", "breadth"): [-rec[k]["height_mm"] if rec[k].get("height_mm")
                                  else None for k in ids],
        ("판형 너비(역)", "breadth"): [-rec[k]["width_mm"] if rec[k].get("width_mm")
                                  else None for k in ids],
        ("장르 수", "breadth"): [rec[k].get("n_genre") or 0 for k in ids],
        ("출판사 사전 출간", "venue"): [ax[k]["axes"]["venue_prominence"] for k in ids],
        ("정가", "friction"): [rec[k].get("price") for k in ids],
        ("쪽수", "goods"): [rec[k].get("pages") for k in ids],
        ("무게", "goods"): [rec[k].get("weight_g") for k in ids],
        ("양장 여부", "goods"): [1.0 if "Hardcover" in (rec[k].get("book_format") or "")
                             else 0.0 for k in ids],
    }
    return V, y, t


DOMAINS = {"아이돌": idol_vars, "게임": game_vars, "도서": book_vars}


def single_r(v, y, t):
    """결측은 **반드시 None**으로 들어와야 한다.

    처음에는 0의 비율로 '이 0이 결측인가 정상값인가'를 추측했다. 그러면 이진
    변수(0/1)와 결측(0)이 섞인다. 도서 판형은 61%만 값이 있는데 나머지 39%의
    '높이 0'이 상관에 들어가 부호가 뒤집혔다 --- 노트 34에서 -0.282였던 것이
    +0.712로 나왔다. 추측하지 않고 호출부에서 명시한다."""
    a = np.array([np.nan if x is None else float(x) for x in v], float)
    m = np.isfinite(a)
    if m.sum() < 30 or a[m].std() < 1e-9:
        return None, int(m.sum())
    return float(np.corrcoef(z(detrend(a[m], t[m])), z(detrend(y[m], t[m])))[0, 1]), int(m.sum())


def cv_self(X, y, t):
    """이 변수 집합으로 만든 축의 자기 상관(교차검증). 결측은 도메인 중앙값으로 채운다."""
    cols = []
    for c in X:
        a = np.array([np.nan if x is None else float(x) for x in c], float)
        if np.isfinite(a).sum() < 10:
            continue
        a[~np.isfinite(a)] = float(np.nanmedian(a))
        cols.append(z(detrend(a, t)))
    if not cols:
        return float("nan")
    Z = np.column_stack(cols)
    yy = z(detrend(y, t))
    kf = KFold(5, shuffle=True, random_state=SEED)
    pr = np.zeros(len(yy))
    for tr, te in kf.split(Z):
        pr[te] = Ridge(alpha=1.0).fit(Z[tr], yy[tr]).predict(Z[te])
    return float(np.corrcoef(pr, yy)[0, 1])


def run() -> dict:
    out = {}
    for dom, fn in DOMAINS.items():
        V, y, t = fn()
        print(f"\n=== {dom} (n={len(y)}) ===")
        print(f"  {'변수':<18}{'유형':<10}{'라벨과 r':>10}{'n':>7}")
        rows = []
        for (name, kind), v in V.items():
            r, n = single_r(v, y, t)
            if r is None:
                print(f"  {name:<18}{kind:<10}{'—':>10}{n:>7}")
                continue
            rows.append({"name": name, "kind": kind, "r": r, "n": n, "v": v})
            print(f"  {name:<18}{kind:<10}{r:>+10.3f}{n:>7}")
        # 축별 최선 변수 --- 유형 제약 안에서 |r| 최대
        best = {}
        for slot, kinds in SLOT_KINDS.items():
            cand = [x for x in rows if x["kind"] in kinds]
            if cand:
                b = max(cand, key=lambda x: abs(x["r"]))
                best[slot] = {"name": b["name"], "r": b["r"]}
        print("  축별 최선:", {k: f"{v['name']} ({v['r']:+.3f})" for k, v in best.items()})
        # 최선 조합의 자기 상관
        sel = [next(x["v"] for x in rows if x["name"] == v["name"]) for v in best.values()]
        cur = cv_self(sel, y, t)
        allv = cv_self([x["v"] for x in rows], y, t)
        print(f"  축별 최선 조합 자기 상관 {cur:+.3f}   (변수 전부 쓰면 {allv:+.3f})")
        out[dom] = {"vars": [{k: x[k] for k in ("name", "kind", "r", "n")} for x in rows],
                    "best": best, "self_best": cur, "self_all": allv}
    Path("data/state/wiring_search.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
