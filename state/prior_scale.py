"""사전 이력을 '건수'가 아니라 '최대 규모'로 다시 잰다 --- 여섯 도메인 공정 비교.

노트 50은 여섯 도메인의 매장 노출도 신호를 나란히 놓고($+$0.322에서 $-$0.011까지)
``이력이 통하는 시장과 통하지 않는 시장''이라고 읽었다. 노트 51이 그 해석을
부분 철회했다 --- 펀딩에서 이력을 \\emph{건수}가 아니라 \\emph{최대 후원자 수}로
재니 $-$0.018이 $+$0.180이 됐다. 그러면 노트 50의 비교 자체가 불공정하다.
다섯 도메인은 전부 건수로 쟀기 때문이다.

여기서 같은 눈금으로 다시 잰다.

    아이돌  소속사의 사전 최대 초동
    도서    출판사의 사전 최대 판매지수
    게임    퍼블리셔의 사전 최대 리뷰 수
    웹툰    작가의 사전 최대 관심 수
    펀딩    창작자의 사전 최대 후원자 수(노트 51)

**설계상 갈림길이 하나 열린다.** 지금까지 축은 라벨을 전혀 쓰지 않았다 ---
건수, 판형, 리워드 수처럼 관측만으로 정해지는 값이었다. '사전 최대 라벨'은
그 도메인의 **과거 라벨**을 쓴다.

  · 원칙으로는 후퇴다. '대상 라벨을 한 번도 보지 않는 전이'가 '대상 도메인의
    과거 라벨을 쓰는 전이'가 된다.
  · 실무로는 후퇴가 아니다. 새 팝업을 예측할 때 그 IP의 지난 팝업 성과는
    이미 알고 있다. 예측 시점에 관측 가능한 것을 안 쓸 이유가 없다.

그래서 **두 버전을 다 재고 구분해서 보고한다.** 축 계산에 과거 라벨을 쓰는
것과 대상의 \\emph{현재} 라벨을 쓰는 것은 다르며, 후자는 여전히 금지다.

사용: python3 -m state.prior_scale
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np

from .tri_domain import detrend, load_all, z

OUT = Path("data/state/prior_scale.json")


def _prior_max(entities, dates, labels, self_ent, self_date):
    """자기 시점보다 엄격히 이전인 같은 주체의 최대 라벨."""
    best = 0.0
    for e, d, y in zip(entities, dates, labels):
        if e and self_ent and e == self_ent and d < self_date:
            best = max(best, y)
    return best


def idol():
    ax = json.loads(Path("data/state/idol_axes.json").read_text())
    recs = {}
    for f in glob.glob("data/idol_records/*.json"):
        r = json.loads(Path(f).read_text())
        recs[r["record_id"]] = r
    ids = list(ax)
    ent = [((recs.get(k) or {}).get("agency") or "").strip() or None for k in ids]
    dt = [(ax[k].get("debut_date") or "9999")[:10] for k in ids]
    y = [ax[k]["y"] for k in ids]
    t = np.array([float(ax[k]["debut_date"][:4])
                  if (ax[k].get("debut_date") or "")[:4].isdigit() else np.nan
                  for k in ids])
    return ids, ent, dt, y, t, np.array(y)


def book():
    ax = json.loads(Path("data/state/book_axes.json").read_text())
    ids = list(ax)
    ent = [(ax[k].get("publisher") or "").strip() or None for k in ids]
    dt = [(ax[k].get("pub_date") or "9999")[:10] for k in ids]
    y = [ax[k]["y"] for k in ids]
    from datetime import date
    asof = date(2026, 7, 29)
    t = []
    for k in ids:
        try:
            t.append(np.log10(max((asof - date(*map(int, ax[k]["pub_date"][:10].split("-")))).days, 1)))
        except (ValueError, TypeError):
            t.append(np.nan)
    return ids, ent, dt, y, np.array(t), np.array(y)


def game():
    ax = json.loads(Path("data/state/game_axes.json").read_text())
    rec = json.loads(Path("data/state/game_records.json").read_text())
    ids = list(ax)
    ent = []
    for k in ids:
        p = ((rec.get(k) or {}).get("publishers") or [None])
        ent.append((p[0] or "").strip() or None if p else None)
    dt = [(ax[k].get("release_date") or "9999")[:10] for k in ids]
    y = [ax[k]["y"] for k in ids]
    from datetime import date
    asof = date(2026, 7, 29)
    t = []
    for k in ids:
        try:
            t.append(np.log10(max((asof - date(*map(int, ax[k]["release_date"][:10].split("-")))).days, 1)))
        except (ValueError, TypeError):
            t.append(np.nan)
    return ids, ent, dt, y, np.array(t), np.array(y)


def webtoon():
    ax = json.loads(Path("data/state/webtoon_axes.json").read_text())
    rec = json.loads(Path("data/state/webtoon_records.json").read_text())
    ids = list(ax)
    ent = []
    for k in ids:
        a = ((rec.get(k) or {}).get("artists") or [None])
        ent.append((a[0] or "").strip() or None if a else None)
    dt = [(ax[k].get("start_date") or "9999")[:10] for k in ids]
    y = [ax[k]["y"] for k in ids]
    from datetime import date
    asof = date(2026, 7, 29)
    t = []
    for k in ids:
        try:
            t.append(np.log10(max((asof - date(*map(int, ax[k]["start_date"][:10].split("-")))).days, 1)))
        except (ValueError, TypeError):
            t.append(np.nan)
    return ids, ent, dt, y, np.array(t), np.array(y)


DOMS = {"아이돌": idol, "도서": book, "게임": game, "웹툰": webtoon}


def run() -> dict:
    out = {}
    print("사전 이력을 '건수'와 '최대 규모'로 각각 잰 것\n")
    print(f"  {'도메인':<7}{'주체':<10}{'이력 있는 것':>12}{'건수 r':>9}{'최대규모 r':>11}")
    ENT = {"아이돌": "소속사", "도서": "출판사", "게임": "퍼블리셔", "웹툰": "작가"}
    for k, fn in DOMS.items():
        ids, ent, dt, ylab, t, y = fn()
        cnt = np.array([sum(1 for e, d in zip(ent, dt)
                            if e and ei and e == ei and d < di)
                        for ei, di in zip(ent, dt)], float)
        mx = np.array([_prior_max(ent, dt, ylab, ei, di)
                       for ei, di in zip(ent, dt)], float)
        has = (cnt > 0)
        if has.sum() < 25:
            print(f"  {k:<7}{ENT[k]:<10}{int(has.sum()):>12}   표본 부족")
            continue
        yy = z(detrend(y, t))
        rc = np.corrcoef(z(detrend(np.log2(cnt + 1), t)), yy)[0, 1]
        rm = np.corrcoef(z(detrend(mx, t)), yy)[0, 1]
        out[k] = {"n_hist": int(has.sum()), "n": len(ids), "r_count": float(rc),
                  "r_max": float(rm)}
        print(f"  {k:<7}{ENT[k]:<10}{int(has.sum()):>7}/{len(ids):<4}"
              f"{rc:>+9.3f}{rm:>+11.3f}")
        np.save(f"data/state/prior_max_{k}.npy", mx)
    out["펀딩"] = {"r_count": -0.018, "r_max": 0.180, "note": "노트 51"}
    print(f"  {'펀딩':<7}{'창작자':<10}{'285/400':>12}{-0.018:>+9.3f}{0.180:>+11.3f}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
