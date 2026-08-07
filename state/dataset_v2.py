"""학습 테이블 v2 — preprocess.py 정책(P1~P7)을 전면 적용한 빌더.

v1 대비 교정:
  · 결측을 0으로 채우지 않고 (값, 마스크) 쌍으로 인코딩          [P4]
  · days/store_count/prior_* 등 롱테일을 log1p                  [P5]
  · **라벨 단위(counting)를 피처로 명시** — 단위가 다르면 타깃 의미가 다름  [P1]
  · 라벨 신뢰등급을 피처 + 표본가중으로 이중 반영                [P3]
  · 총계/일평균 두 타깃 축 산출                                  [P2]
  · IP 상태 피처에 콜드스타트 shrinkage 적용(82%가 1회 관측)      [P7]
  · 도메인별 타깃 z-정규화는 학습 시점에 TargetScaler로            [P6]

블록 구조(아키텍처가 모달리티를 분리해 다루도록 인덱스를 함께 저장):
  state(IP 상태) | num(수치) | cat(범주 one-hot) | unit(라벨단위) | trust(신뢰) | time(시간)

사용: python3 -m state.dataset_v2 --domain popup
산출: data/state/{domain}_v2.npz  (X, y_total, y_perday, w, block_idx)
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path

import numpy as np

from ingest.calendar_features import calendar_features

from .entity_graph import build as build_graph, norm
from .preprocess import (COUNT_UNITS, TRUST_GRADES, num, shrink, targets,
                         trust_onehot, trust_weight, unit_onehot)

VENUE_TIER = {"더현대": 1, "롯데월드몰": 1, "스타필드": 1, "코엑스": 1, "신세계": 1, "잠실": 1,
              "성수": 2, "홍대": 2, "강남": 2, "한남": 2, "명동": 2, "압구정": 2, "여의도": 2}
CATEGORIES = ["character", "fashion", "fnb", "beauty", "game_webtoon", "entertainment",
              "electronics", "liquor", "other"]
# T1 태거(ingest/attr_tagger.py) 산출 — 기획서 원문에서 뽑은 예측용 속성
T1_NUM = ["host_daily_traffic", "plan_visitors_per_day", "capacity_per_session",
          "giveaway_qty", "area_sqm",
          "throughput_units", "unit_minutes", "operating_hours_per_day", "staff_count"]
# planned_operating_days는 T1_NUM에 넣지 않는다 — 피처가 아니라 **분모**로 승격시킨다.
# y_perday = visitors / days 이므로 days가 틀리면 타깃 자체가 오염된다.
# conditions.period 기반 days는 20건 중 5건에서 문서와 어긋났고 최대 16일 차였다.
T1_ORD = ["experience_density", "goods_scale", "photo_zones", "collab_strength", "ip_awareness",
          "target_breadth", "entry_friction", "media_push", "season_fit", "venue_prominence"]
# 달력 파생(ingest/calendar_features.py) — 수집 비용 0, 시간 마스크 자동 통과
CAL_NUM = ["holiday_since", "holiday_until", "holiday_block_in", "nat_event_gap", "doc_lag_days"]
# 네이버 데이터랩 검색량 상태(ingest/naver_trend.py) — 오픈 **이전** 12주 창에서만 계산되므로
# 시간 마스크를 통과한다(naver_trend.py:84 `p < open_date`). 95/96건 수집돼 있었는데
# 학습 테이블에 배선되지 않아 쓰이지 않고 있었다.
TREND_NUM = ["level", "momentum", "volatility", "peak_ratio", "n_weeks"]
# 경쟁밀도(ingest/competition.py) — 오픈 **이전에 이미 열려 있던** 팝업만 센다
COMP_NUM = ["comp_same_addr_open", "comp_prior_at_venue",
            "comp_within_500m_open", "comp_within_1000m_open"]
# PnL 사전 계상(ingest/pnl_features.py) — 오픈 **전 달**까지 계상된 판관비
PNL_NUM = ["pnl_pre_total", "pnl_pre_accounts", "pnl_pre_months"]
_TREND = None


def trend_state(code: str) -> dict:
    global _TREND
    if _TREND is None:
        f = Path("data/state/naver/popup_trend.json")
        _TREND = json.loads(f.read_text()) if f.exists() else {}
    return (_TREND.get(code) or {}).get("state") or {}


def venue_tier(v) -> int:
    s = str(v or "")
    for k, t in VENUE_TIER.items():
        if k in s:
            return t
    return 3


def ip_state_block(graph: dict, ip_key: str, at: str | None) -> tuple[list[float], list[str]]:
    """[P7] shrinkage 적용 IP 상태. 값+마스크 쌍으로."""
    names = ["prior_n_log", "prior_label_n_log", "prior_log_mean", "prior_log_max",
             "months_since_log", "cross_domain", "family", "obs_mask"]
    n = graph.get(ip_key)
    prior = []
    if n and at:
        prior = [o for o in n["obs"] if (o.get("date") or "9999") < at]
    if not prior:
        return [0.0] * 7 + [0.0], names
    labs = [o["label"] for o in prior if o.get("label")]
    logs = [math.log10(max(1, x)) for x in labs]
    months = 0.0
    dates = [o["date"] for o in prior if o.get("date")]
    if dates and at:
        try:
            months = (date.fromisoformat(at) - date.fromisoformat(max(dates))).days / 30.4
        except Exception:
            months = 0.0
    sh = shrink(len(prior))                      # 콜드스타트 수축
    vals = [
        math.log1p(len(prior)),
        math.log1p(len(labs)),
        (sum(logs) / len(logs)) * sh if logs else 0.0,
        max(logs) * sh if logs else 0.0,
        math.log1p(min(months, 60.0)),
        float(len({o["domain"] for o in prior}) > 1),
        float(bool(n.get("parent"))),
        1.0,                                      # 관측 있음 마스크
    ]
    return vals, names


def _popup_common(g, ip, at, label, trust, unit, num_feats, cat_vec, days_label=None):
    st, st_names = ip_state_block(g, norm(ip), at)
    nums, num_names = [], []
    for k, (v, lg) in num_feats.items():
        x, m = num(v, log=lg)
        nums += [x, m]
        num_names += [k, f"{k}_mask"]
    tgt = targets(label, days_label if days_label else num_feats.get("days", (None, False))[0])
    row = st + nums + cat_vec + unit_onehot(unit) + trust_onehot(trust)
    names = (st_names + num_names + [f"cat_{c}" for c in CATEGORIES]
             + [f"unit_{u}" for u in COUNT_UNITS] + [f"trust_{t}" for t in TRUST_GRADES])
    return row, names, tgt, trust_weight(trust)


def popup_rows():
    g = build_graph()
    X, yt, yp, w, meta, names = [], [], [], [], [], None
    for p in sorted(Path("data/records").glob("*.json")):
        r = json.loads(p.read_text())
        o, c = r["outcome"], r["conditions"]
        v = o["totals"].get("visitors")
        if not v:
            continue
        du = (c.get("derived") or {}).get("duration") or {}
        sc = c.get("scale") or {}
        cap = (c.get("capacity") or {}).get("access_type")
        cat = [0.0] * len(CATEGORIES)
        cat[CATEGORIES.index("other")] = 1.0        # 내부는 카테고리 필드 없음 → other
        at = r["intervention"].get("attributes") or {}      # T1 태거 산출 (2026-07-27)
        # 일수는 두 갈래로 쓴다. 섞으면 안 된다.
        #  · 피처 days      = 문서에서 읽은 계획 운영일수(예측 시점에 알 수 있는 것)
        #  · 타깃 분모      = 라벨이 실제로 덮은 운영일수(라벨 자신의 정의)
        # RIPU2501은 계획 13일인데 라벨은 28일을 덮는다. 하나로 뭉개면
        # '계획대로 안 됐다'는 사실이 타깃과 피처 양쪽에서 동시에 사라진다.
        pod = at.get("planned_operating_days")
        days_feat = pod if pod else du.get("days")
        ls = o.get("label_scope") or {}
        days_label = ls.get("label_active_days") or days_feat
        nums = {"days": (days_feat, True), "days_from_doc": (1.0 if pod else 0.0, False),
                "weekend_share": (du.get("weekend_share"), False),
                "holiday_days": (du.get("holiday_days"), True),
                "venue_tier": (venue_tier(r["entities"].get("space_key")), False),
                "store_count": (sc.get("store_count"), True),
                "area_pyeong": (c.get("area_pyeong"), True),
                "is_host": (1.0 if sc.get("venue_traffic_type") == "host_venue" else 0.0, False),
                "cap_bound": (1.0 if cap in ("session", "invite", "reservation") else 0.0, False),
                "total_capacity": ((c.get("capacity") or {}).get("total_capacity"), True),
                "is_market": (0.0, False)}
        # [D8] 라벨이 증정물 준비 수량에 걸린 건에서는 giveaway_qty가 피처가 아니라
        # 라벨 자신이다(입장 시 1매 증정 → 수량 소진 시 계수 정지). 가려야 한다.
        gq = at.get("giveaway_qty")
        gq_is_label = bool(gq and gq > 0 and gq <= v <= gq * 1.02)
        for k in T1_NUM:                                     # 값+마스크 (P4)
            val = None if (k == "giveaway_qty" and gq_is_label) else at.get(k)
            nums[f"t1_{k}"] = (val, True)
        for k in T1_ORD:                                     # 순서형은 결측 시 중앙 2
            nums[f"t1o_{k}"] = (at.get(k) if at.get(k) is not None else 2, False)
        # [R1 throughput_cap] 회차 기반 물리 천장 = 회차정원 × (운영시간×60 / 회차길이).
        # 예측 대상은 수요가 아니라 min(수요, 캡)이다. 회차제일 때만 계산한다 —
        # 회차가 없으면 '전원이 통과하는 병목'이라는 보편성 조건을 확인할 수 없고,
        # 유닛 수만으로 계산하면 900~1200% 초과가 난다(RTPU2415 메이크업 3인은
        # 병목이 아니었다. 대부분의 방문객은 시술을 받지 않았다).
        cps, ohr, umin = (at.get("capacity_per_session"), at.get("operating_hours_per_day"),
                          at.get("unit_minutes"))
        cap_day = cps * (ohr * 60 / umin) if (cps and ohr and umin) else None
        nums["cap_per_day"] = (cap_day, True)
        tr = trend_state(r["record_id"])                     # 네이버 검색량 상태
        for k in TREND_NUM:
            nums[f"trend_{k}"] = (tr.get(k), k == "n_weeks")
        cp = (c.get("derived") or {}).get("competition") or {}
        for k in COMP_NUM:
            nums[k] = (cp.get(k), True)
        pn = (c.get("derived") or {}).get("pnl_pre") or {}
        for k in PNL_NUM:
            nums[k] = (pn.get(k), True)
        cal = (c.get("derived") or {}).get("calendar") or {}  # 발견 루프 R1 채택 (2026-07-28)
        for k in CAL_NUM:
            nums[f"cal_{k}"] = (cal.get(k), k in ("holiday_since", "holiday_until",
                                                  "nat_event_gap", "doc_lag_days"))
        vk = c.get("venue_knowledge") or {}                  # T1b 세계지식 (2026-07-28)
        nums["t1b_host_traffic"] = (vk.get("host_traffic_est"), True)
        nums["t1b_venue_footfall"] = (vk.get("venue_daily_footfall"), True)
        nums["t1b_pass_rate"] = (vk.get("popup_zone_pass_rate"), False)
        nums["t1b_tier"] = (vk.get("venue_scale_tier"), False)
        row, nm, tgt, ww = _popup_common(
            g, r["entities"].get("brand_key") or r["intervention"].get("brand_name"),
            (c.get("period") or {}).get("from"), v, (o.get("label_trust") or {}).get("grade"),
            o.get("counting_method"), nums, cat, days_label)
        names = names or nm
        X.append(row); yt.append(tgt["log_total"]); yp.append(tgt["log_per_day"] or np.nan)
        w.append(ww); meta.append({"id": r["record_id"], "domain": "popup_internal",
                                    "scope_usable": True,
                                    "counting": o.get("counting_method") or "unknown",
                                    "ip": norm(r["entities"].get("brand_key")
                                               or r["intervention"].get("brand_name")),
                                    "date": (c.get("period") or {}).get("from")})
    for p in sorted(Path("data/market_records").glob("*.json")):
        m = json.loads(p.read_text())
        o, c = m["outcome"], m["conditions"]
        v = o.get("visitors_total")
        if not v or m.get("single_event") is False:
            continue
        du = (c.get("derived") or {}).get("duration") or {}
        # [노트 2] 인용문이 말하는 기간이 저장 일수와 다르면 그것이 옳다.
        # 21건이 중간 집계 라벨에 전체 기간을 분모로 써서 일평균이 중앙 3.25배 과소였다.
        sc = o.get("scope_class") or {}
        days_market = sc.get("days_stated") or du.get("days")
        mc = calendar_features(c.get("period_from"), c.get("period_to")) or {}
        cat = [0.0] * len(CATEGORIES)
        cc = m.get("category") if m.get("category") in CATEGORIES else "other"
        cat[CATEGORIES.index(cc)] = 1.0
        row, nm, tgt, ww = _popup_common(
            g, m.get("ip_or_collab") or m.get("brand"), c.get("period_from"), v,
            (o.get("label_trust") or {}).get("grade"), o.get("counting_basis"),
            {"days": (days_market, True), "days_from_doc": (0.0, False),
             "weekend_share": (du.get("weekend_share"), False),
             "holiday_days": (du.get("holiday_days"), True),
             "venue_tier": (venue_tier(c.get("venue")), False),
             "store_count": (2 if c.get("multi_store") else 1, True),
             "area_pyeong": (c.get("area_pyeong"), True),
             "is_host": (1.0 if str(c.get("venue_type")) in ("department", "mall") else 0.0, False),
             "cap_bound": (1.0 if (c.get("capacity") or {}).get("access_type")
                           in ("session", "invite", "reservation") else 0.0, False),
             "total_capacity": ((c.get("capacity") or {}).get("total_capacity"), True),
             "is_market": (1.0, False),
             **{f"t1_{k}": (None, True) for k in T1_NUM},
             **{f"t1o_{k}": (2, False) for k in T1_ORD},
             "cap_per_day": (None, True),
             **{f"trend_{k}": (None, k == "n_weeks") for k in TREND_NUM},
             **{k: (None, True) for k in COMP_NUM}, **{k: (None, True) for k in PNL_NUM},
             **{f"cal_{k}": (mc.get(k), k != "holiday_block_in") for k in CAL_NUM},
             "t1b_host_traffic": (None, True), "t1b_venue_footfall": (None, True),
             "t1b_pass_rate": (None, False), "t1b_tier": (None, False)}, cat, days_market)
        names = names or nm
        X.append(row); yt.append(tgt["log_total"]); yp.append(tgt["log_per_day"] or np.nan)
        w.append(ww); meta.append({"id": m["market_record_id"], "domain": "popup_market",
                                    "scope_usable": bool(sc.get("usable", True)),
                                    "counting": o.get("counting_basis") or "unknown",
                                    "ip": norm(m.get("ip_or_collab") or m.get("brand")),
                                    "date": c.get("period_from")})
    return np.array(X, float), np.array(yt, float), np.array(yp, float), np.array(w, float), meta, names


def block_index(names: list[str]) -> dict:
    """아키텍처가 모달리티별로 다르게 처리하도록 컬럼 블록 경계를 제공."""
    idx = {"state": [], "num": [], "cat": [], "unit": [], "trust": [], "mask": []}
    for i, n in enumerate(names):
        if n.endswith("_mask") or n == "obs_mask":
            idx["mask"].append(i)
        if n.startswith("cat_"):
            idx["cat"].append(i)
        elif n.startswith("unit_"):
            idx["unit"].append(i)
        elif n.startswith("trust_"):
            idx["trust"].append(i)
        elif n.startswith("prior_") or n in ("months_since_log", "cross_domain", "family", "obs_mask"):
            idx["state"].append(i)
        elif not n.endswith("_mask"):
            idx["num"].append(i)
    return idx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="popup")
    args = ap.parse_args()
    X, yt, yp, w, meta, names = popup_rows()
    idx = block_index(names)
    out = Path(f"data/state/{args.domain}_v2.npz")
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out, X=X, y_total=yt, y_perday=yp, w=w,
             names=np.array(names), block=json.dumps(idx))
    Path(f"data/state/{args.domain}_v2_meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    print(json.dumps({"표본": len(yt), "피처": X.shape[1],
                       "블록": {k: len(v) for k, v in idx.items()},
                       "일평균 타깃 가능": int(np.isfinite(yp).sum()),
                       "가중 평균": round(float(w.mean()), 3)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
