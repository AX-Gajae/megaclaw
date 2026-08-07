"""학습 테이블 빌더 — 도메인별 (피처, 라벨)을 공통 인터페이스로 산출.

설계(2026-07-27 확정): 상태는 하나(공유 IP 인코더), 결과 헤드는 도메인별.
따라서 각 도메인은 같은 IP 상태 피처 + 도메인 고유 개입 피처를 낸다.

라벨은 **로그 구간**으로 다룬다 — 라벨 신뢰등급이 섞여 있고(A~E), 절대치 회귀는 자(尺) 잡음에
과적합되기 때문. 회귀 타깃은 log10(라벨), 평가는 구간 정확도와 MAE(log space).

시간 마스크: IP 상태 피처는 각 표본의 자기 시점 **이전** 관측만 사용(누출 방지, 팝업 ip_history와 동일 원칙).

사용: python3 -m state.dataset --domain popup|idol
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import numpy as np

from .entity_graph import build as build_graph, norm

TRUST_W = {"A": 1.0, "B": 0.8, "C": 0.5, "D": 0.25, "E": 0.25, None: 0.5}
VENUE_TIER = {  # 1=최상급 유동, 3=비전형
    "더현대": 1, "롯데월드몰": 1, "스타필드": 1, "코엑스": 1, "신세계": 1, "잠실": 1,
    "성수": 2, "홍대": 2, "강남": 2, "한남": 2, "명동": 2, "압구정": 2, "여의도": 2,
}


def venue_tier(v: str | None) -> int:
    s = str(v or "")
    for k, t in VENUE_TIER.items():
        if k in s:
            return t
    return 3


def ip_state(graph: dict, ip_key: str, at: str | None) -> dict:
    """자기 시점 이전 관측만으로 만든 IP 상태 (누출 방지)."""
    n = graph.get(ip_key)
    if not n or not at:
        return {"prior_n": 0, "prior_label_n": 0, "prior_log_mean": 0.0, "prior_log_max": 0.0,
                "months_since": 0.0, "cross_domain": 0, "family": 0}
    prior = [o for o in n["obs"] if (o.get("date") or "9999") < at]
    labs = [o["label"] for o in prior if o.get("label")]
    logs = [math.log10(max(1, x)) for x in labs]
    months = 0.0
    if prior:
        try:
            last = max(o["date"] for o in prior if o.get("date"))
            months = round((date.fromisoformat(at) - date.fromisoformat(last)).days / 30.4, 1)
        except Exception:
            months = 0.0
    return {"prior_n": len(prior), "prior_label_n": len(labs),
            "prior_log_mean": round(sum(logs) / len(logs), 3) if logs else 0.0,
            "prior_log_max": round(max(logs), 3) if logs else 0.0,
            "months_since": min(months, 60.0),
            "cross_domain": int(len({o["domain"] for o in prior}) > 1),
            "family": int(bool(n.get("parent")))}


POPUP_FEATS = ["prior_n", "prior_label_n", "prior_log_mean", "prior_log_max", "months_since",
               "cross_domain", "family", "days", "weekend_share", "holiday_days",
               "venue_tier", "store_count", "is_host_venue", "cap_bound", "is_market_tier"]


def popup_rows() -> tuple[np.ndarray, np.ndarray, np.ndarray, list]:
    g = build_graph()
    X, y, w, meta = [], [], [], []

    def push(ip, at, label, trust, f):
        st = ip_state(g, norm(ip), at)
        row = [st[k] for k in POPUP_FEATS[:7]] + [f.get(k, 0) for k in POPUP_FEATS[7:]]
        X.append(row); y.append(math.log10(max(1, label)))
        w.append(TRUST_W.get(trust, 0.5)); meta.append({"ip": norm(ip), "date": at, "raw": label})

    for p in Path("data/records").glob("*.json"):
        r = json.loads(p.read_text())
        o, c = r["outcome"], r["conditions"]
        v = o["totals"].get("visitors")
        if not v:
            continue
        der = c.get("derived") or {}
        du = der.get("duration") or {}
        sc = c.get("scale") or {}
        cap = (c.get("capacity") or {}).get("access_type")
        push(r["entities"].get("brand_key") or r["intervention"].get("brand_name"),
             (c.get("period") or {}).get("from"), v, (o.get("label_trust") or {}).get("grade"),
             {"days": du.get("days", 0), "weekend_share": du.get("weekend_share", 0),
              "holiday_days": du.get("holiday_days", 0),
              "venue_tier": venue_tier(r["entities"].get("space_key")),
              "store_count": sc.get("store_count") or 1,
              "is_host_venue": int(sc.get("venue_traffic_type") == "host_venue"),
              "cap_bound": int(cap in ("session", "invite", "reservation")),
              "is_market_tier": 0})
    for p in Path("data/market_records").glob("*.json"):
        m = json.loads(p.read_text())
        o, c = m["outcome"], m["conditions"]
        v = o.get("visitors_total")
        if not v or m.get("single_event") is False:
            continue
        der = c.get("derived") or {}
        du = der.get("duration") or {}
        push(m.get("ip_or_collab") or m.get("brand"), c.get("period_from"), v,
             (o.get("label_trust") or {}).get("grade"),
             {"days": du.get("days", 0), "weekend_share": du.get("weekend_share", 0),
              "holiday_days": du.get("holiday_days", 0),
              "venue_tier": venue_tier(c.get("venue")),
              "store_count": 2 if c.get("multi_store") else 1,
              "is_host_venue": int(str(c.get("venue_type")) in ("department", "mall")),
              "cap_bound": int((c.get("capacity") or {}).get("access_type")
                               in ("session", "invite", "reservation")),
              "is_market_tier": 1})
    return np.array(X, float), np.array(y, float), np.array(w, float), meta


IDOL_FEATS = ["prior_n", "prior_label_n", "prior_log_mean", "prior_log_max", "months_since",
              "cross_domain", "family", "member_count", "is_girl", "survival",
              "agency_tier", "has_preorder", "debut_year"]


def idol_rows() -> tuple[np.ndarray, np.ndarray, np.ndarray, list]:
    """아이돌 데뷔 — data/idol_records/*.json 이 생기면 자동 동작."""
    g = build_graph()
    X, y, w, meta = [], [], [], []
    BIG = ("하이브", "SM", "JYP", "YG", "빅히트", "어도어", "쏘스뮤직", "플레디스", "빌리프랩", "카카오")
    d = Path("data/idol_records")
    if not d.exists():
        return np.zeros((0, len(IDOL_FEATS))), np.zeros(0), np.zeros(0), []
    for p in d.glob("*.json"):
        r = json.loads(p.read_text())
        c = r.get("chodong")
        if not c:
            continue
        at = r.get("debut_date")
        st = ip_state(g, norm(r.get("group_name")), at)
        ag = str(r.get("agency") or "")
        row = [st[k] for k in IDOL_FEATS[:7]] + [
            r.get("member_count") or 0,
            int(str(r.get("gender")) == "girl"),
            int(bool(r.get("survival_show"))),
            1 if any(b in ag for b in BIG) else 2,
            int(bool(r.get("preorder"))),
            int((at or "2020")[:4]) - 2019,
        ]
        X.append(row); y.append(math.log10(max(1, c)))
        w.append(TRUST_W.get((r.get("label_trust") or {}).get("grade"), 0.5))
        meta.append({"ip": norm(r.get("group_name")), "date": at, "raw": c})
    return np.array(X, float), np.array(y, float), np.array(w, float), meta


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="popup", choices=["popup", "idol"])
    args = ap.parse_args()
    X, y, w, meta = popup_rows() if args.domain == "popup" else idol_rows()
    print(json.dumps({"도메인": args.domain, "표본": len(y), "피처": X.shape[1] if len(y) else 0,
                       "라벨 log10 범위": [round(float(y.min()), 2), round(float(y.max()), 2)] if len(y) else None,
                       "가중 평균(신뢰도)": round(float(w.mean()), 3) if len(y) else None},
                      ensure_ascii=False))
    if len(y):
        out = Path(f"data/state/{args.domain}_table.npz")
        out.parent.mkdir(parents=True, exist_ok=True)
        np.savez(out, X=X, y=y, w=w)
        Path(f"data/state/{args.domain}_meta.json").write_text(json.dumps(meta, ensure_ascii=False))
        print(f"저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
