"""시장 팝업 도메인의 축 --- 열째 채점 도메인(노트 283 · 284).

노트 283이 잰 것: 시장 레코드 647건 중 방문 라벨 + 단일 이벤트가 207건이고,
**붙이면 안 된다** --- 내부 팝업은 손 축 마스크가 100% 인데 시장은 0% 라
마스크 무늬가 곧 출처 표지가 되고 출처가 라벨을 3.2배로 가른다(노트 266 덫).
**그래서 붙이지 않고 따로 연다.**

전제 셋을 확인했다.
  ① 시간   ``period_from`` 이 개최일이다. 다만 이 도메인은 **결과로 선택된
           모집단**이다(기사가 된 팝업만 있다) --- 그 안에서의 순위 과제로만
           읽는다.
  ② 겹침   내부와 브랜드 + 기간이 모두 겹치는 진짜 중복이 둘(미래엔 디지털초코 ·
           블룸타이드, 둘 다 자사 프로젝트가 기사가 된 것)이라 뺀다.
  ③ 라벨   신뢰등급 A 2 · B 88 · C 81 · D 11 · E 23. 하한(C) · 추정(E) 이
           많지만 **A · B 만 써도 학습 47행**으로 청력 문턱 22 위다.

공유 축 다섯에 태우는 근거(노트 283의 규약 --- 얇은 도메인은 전용 이름 대신
공유 축에 태운다. 다만 여기는 학습 101행이라 얇지 않고, 공유 축을 쓰는 것은
정렬 때문이다):

    venue_prominence  ip_history.prior_count   덮음 86% · 라벨 +0.217
                      다른 도메인의 ``n_prior'' 관례와 같다(표본 안 시간 인과)
    goods_scale       multi_store              덮음 95% · 라벨 +0.227
    entry_friction    is_free_entry/reservation 덮음 42% · 29%
    target_breadth    ip_or_collab             덮음 83% · 라벨 +0.114
    media_push        --- 대응물 없음. 마스크 0

``venue_type`` 은 안 쓴다 --- 일평균 라벨을 못 가른다(크루스칼 p=0.15).
``category`` 는 공유 축에 대응물이 없어 여기 안 넣는다(전용 축 후보).
``기간 일수`` 는 **안 쓴다** --- 라벨이 일평균이라 그 분모다(노트 276 · 283).
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np

ALL5 = ("target_breadth", "venue_prominence", "entry_friction",
        "media_push", "goods_scale")
# 내부와 브랜드 · 기간이 모두 겹치는 진짜 중복(노트 283)
DUP = {"MKT-2025-0010", "MKT-2026-0020"}
OUT = "data/state/market_axes.json"


def _g(o, p):
    for k in p.split("."):
        if not isinstance(o, dict):
            return None
        o = o.get(k)
    return o


def _pct(v: np.ndarray, ok: np.ndarray) -> np.ndarray:
    """관측된 값만 백분위로. **동률은 평균 순위로 묶는다**(노트 292).

    처음에 ``argsort(argsort())`` 로 썼는데 그것은 동률을 **행 순서로** 깬다.
    ``prior_count`` 는 205행 중 182행(89%)이 0 이고 행 순서가
    ``MKT-YYYY-NNNN`` 이라 연도와 $+$0.864 다 --- 그래서 값이 전부 같은
    182행 안에서 축이 라벨과 $+$0.1371 이 나왔다. **있지도 않은 정보를 축이
    나르고 있었다.** 노트 291이 잰 ``조인을 넓히면 학습 상관 $+$0.139 $\\to$
    $+$0.211'' 도 그 인공물이었다.
    """
    from scipy.stats import rankdata
    out = np.full(len(v), 0.5)
    if ok.sum() < 3:
        return out
    out[ok] = (rankdata(v[ok]) - 1.0) / max(int(ok.sum()) - 1, 1)
    # **만드는 자리에서 잡는다**(노트 292). 백분위는 단조 변환이므로 서로 다른
    # 값의 수가 늘어나면 안 된다 --- 늘었다면 동률을 무언가로 깬 것이고, 그
    # 무언가는 대개 행 순서다. 판 수준 가드로는 못 본다(행 순서는 자료 안에서
    # 교환 가능해야 하고, 판만 봐서는 원본 값을 모른다).
    n_in = len(np.unique(v[ok]))
    n_out = len(np.unique(out[ok]))
    if n_out != n_in:
        raise AssertionError(
            f"_pct 가 동률을 깼다: 입력 {n_in}가지 → 출력 {n_out}가지")
    return out


def _single(d) -> bool:
    """단일 행사인가.

    **``single_event`` 는 MKT 배치에만 쓰였다**(노트 354). MKT2 239건은
    ``single_event`` 도 ``tier`` 도 한 번도 안 쓰였고(239/239 ``None``),
    그래서 이 빌더가 ``not d.get("single_event")`` 로 **배치 통째로**
    떨어뜨리고 있었다 --- ``단일 행사가 아니어서''가 아니라 ``칸이 비어서''다.
    축 파일 205행이 전부 MKT 인 것이 그 자국이다.

    떨어진 것 중 라벨 · 기간 · 등급이 멀쩡한 46건은 ``multi_store`` 가 전부
    ``False`` 이고 ``_aggregate`` · ``exclude_reason`` 도 없다 --- 마뗑킴
    롯데백화점 부산점 · 원신 신촌 · W컨셉 성수 · 빵빵이 더현대 같은 평범한
    단일 팝업이다.

    **레코드별로 보고 정하지 않는다.** 칸이 비었으면 규칙으로 메운다 ---
    여러 점포가 아니고, 집계도 아니고, 제외 사유도 없으면 단일 행사다.
    """
    v = d.get("single_event")
    if v is not None:
        return bool(v)
    return (_g(d, "conditions.multi_store") is False
            and not d.get("_aggregate")
            and not d.get("exclude_reason"))


def build(root: str = ".", grades=("A", "B", "C", "D", "E")) -> dict:
    recs = []
    for f in sorted(glob.glob(str(Path(root) / "data/market_records/*.json"))):
        d = json.load(open(f))
        if d["market_record_id"] in DUP or not _single(d):
            continue
        v = (_g(d, "outcome.visitors_total") or _g(d, "outcome.totals.visitors")
             or _g(d, "outcome.visitors"))
        gr = _g(d, "outcome.label_trust.grade") or "?"
        if not v or gr not in grades:
            continue
        pf = _g(d, "conditions.period_from") or ""
        pt = _g(d, "conditions.period_to") or ""
        try:
            days = ((np.datetime64(pt) - np.datetime64(pf))
                    / np.timedelta64(1, "D") + 1)
        except Exception:
            continue
        if not (days == days and days > 0) or not pf[:4].isdigit():
            continue
        recs.append((d, float(v) / float(days), pf, gr))
    if not recs:
        return {}

    def col(fn):
        raw = np.array([fn(d) if fn(d) is not None else np.nan
                        for d, _, _, _ in recs], float)
        return _pct(raw, np.isfinite(raw)), np.isfinite(raw).astype(float)

    prior, m_prior = col(lambda d: _g(d, "conditions.derived.ip_history.prior_count"))
    multi, m_multi = col(lambda d: (1.0 if _g(d, "conditions.multi_store")
                                    else (0.0 if _g(d, "conditions.multi_store") is False
                                          else None)))
    collab, m_col = col(lambda d: 1.0 if d.get("ip_or_collab") else 0.0)

    def _friction(d):
        free = _g(d, "intervention.is_free_entry")
        resv = _g(d, "intervention.reservation_required")
        if free is None and resv is None:
            return None
        s = 0.0
        if free is False:
            s += 1.0                 # 유료면 마찰
        if resv is True:
            s += 1.0                 # 예약 필요하면 마찰
        return s
    fric, m_fric = col(_friction)

    out = {}
    for i, (d, per, pf, gr) in enumerate(recs):
        out[d["market_record_id"]] = {
            "axes": {"target_breadth": float(collab[i]),
                     "venue_prominence": float(prior[i]),
                     "entry_friction": float(fric[i]),
                     "media_push": 0.5,
                     "goods_scale": float(multi[i])},
            "mask": {"target_breadth": float(m_col[i]),
                     "venue_prominence": float(m_prior[i]),
                     "entry_friction": float(m_fric[i]),
                     "media_push": 0.0,
                     "goods_scale": float(m_multi[i])},
            "y": float(np.log10(per)),
            "period_from": pf,
            "label_trust": gr,
            "category": d.get("category"),
            "why": {"venue_prominence": "ip_history.prior_count",
                    "goods_scale": "multi_store",
                    "entry_friction": "is_free_entry / reservation_required",
                    "target_breadth": "ip_or_collab",
                    "media_push": "대응물 없음 --- 마스크 0"},
        }
    return out


if __name__ == "__main__":
    d = build()
    Path(OUT).write_text(json.dumps(d, ensure_ascii=False, indent=1))
    yrs = {}
    for v in d.values():
        yrs[v["period_from"][:4]] = yrs.get(v["period_from"][:4], 0) + 1
    pre = sum(n for y, n in yrs.items() if int(y) < 2025)
    print(f"{OUT} --- {len(d)}행 (학습 {pre} · 유보 {len(d)-pre})")
    print("  연도", dict(sorted(yrs.items())))
    for a in ALL5:
        m = np.mean([v["mask"][a] for v in d.values()])
        print(f"  {a:<18} 마스크 {100*m:.0f}%")
