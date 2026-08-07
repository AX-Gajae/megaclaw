"""시장 층(market_claim) 조건화 — Kimi 크롤링 검증분을 예측기에 별도 다이제스트로 주입.

내부 실측 뱅크와 등급이 다르다: 시장 라벨은 주최측 발표(organizer_claim) 계열이며
스토어 스코프에선 실측 대비 ×1.07~1.19 온건 팽창(2026-07-27 직접 측정 2건), '일대/권역'
집계는 스코프 자체가 달라 스토어 예측 앵커 금지(편입 시 single_event 필터로 대부분 제거됨).

시간 마스크: 타깃 오픈일 이전에 '종료'된 이벤트만 주입 (미래 누출 방지).
주의: 출처 기사 게재일이 이벤트 종료보다 늦을 수 있음 — 지식 시점 엄밀성은 종료일 기준으로 근사.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MARKET_DIR = Path("data/market_records")
OK_VERIF = ("verified", "num_only", "quote_only")


def _ipkey(r: dict) -> str:
    k = (r.get("ip_or_collab") or r.get("brand") or "").strip()
    return re.sub(r"\(.*?\)", "", k).split(" X ")[0].split("X")[0].strip()


def load_anchors() -> list[dict]:
    out = []
    if not MARKET_DIR.exists():
        return out
    for p in sorted(MARKET_DIR.glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        o = r["outcome"]
        if not r.get("single_event"):
            continue
        vis_ok = o.get("visitors_total") and r["verification"].get("visitors") in OK_VERIF
        sal_ok = o.get("sales_krw") and r["verification"].get("sales") in OK_VERIF
        if not (vis_ok or sal_ok):
            continue
        c = r["conditions"]
        from datetime import date
        try:
            days = (date.fromisoformat(c["period_to"]) - date.fromisoformat(c["period_from"])).days + 1
        except Exception:
            days = None
        ds = o.get("demand_signals") or {}
        der = c.get("derived") or {}
        out.append({
            "trust": (o.get("label_trust") or {}).get("grade"),
            "weekend_share": (der.get("duration") or {}).get("weekend_share"),
            "holiday_days": (der.get("duration") or {}).get("holiday_days"),
            "ip_hist": der.get("ip_history"),
            "cap_type": (c.get("capacity") or {}).get("access_type"),
            "id": r["market_record_id"], "ip": _ipkey(r), "name": (r.get("event_name") or "")[:40],
            "category": r.get("category"), "venue": (c.get("venue") or "")[:20], "city": c.get("city"),
            "from": c["period_from"], "to": c["period_to"], "days": days,
            "visitors": o.get("visitors_total") if vis_ok else None,
            "basis": o.get("counting_basis"), "basis_note": (o.get("counting_basis_note") or "")[:60],
            "sales": o.get("sales_krw") if sal_ok else None,
            "waiting": ds.get("waiting_time_reported"), "sold_out": ds.get("sold_out"),
            "resv_fill": ds.get("reservation_fill"),
        })
    return out


def _line(a: dict, signals: bool = True, features: bool = True) -> str:
    vis = f"방문{a['visitors']:,}" if a["visitors"] else "방문—"
    per = f"(일{a['visitors']//a['days']:,})" if a["visitors"] and a["days"] else ""
    sal = f"|매출{a['sales']/1e6:.0f}M" if a["sales"] else ""
    sig = ""
    if signals:
        parts = []
        if a["sold_out"]:
            parts.append("완판")
        if a.get("waiting"):
            parts.append(f"대기:{str(a['waiting'])[:14]}")
        if a.get("resv_fill"):
            parts.append(f"예약:{str(a['resv_fill'])[:10]}")
        if parts:
            sig = "|" + ",".join(parts)
    ft = ""
    if features:
        parts = []
        if a.get("trust"):
            parts.append(f"T:{a['trust']}")
        if a.get("weekend_share") is not None:
            h = f"+휴{a['holiday_days']}" if a.get("holiday_days") else ""
            parts.append(f"주말{int(a['weekend_share']*100)}%{h}")
        ih = a.get("ip_hist") or {}
        if ih:
            parts.append("IP초회" if ih.get("first_edition") else f"IP{ih['prior_count']+1}회차")
        if a.get("cap_type") in ("session", "invite", "reservation"):
            parts.append(f"캡:{a['cap_type']}")
        if parts:
            ft = "|" + " ".join(parts)
    return f"{a['id']}|{a['name']}|{a['category']}|{a['venue']}|{a['from']}~{(a['to'] or '')[5:]}({a['days']}일)|{vis}{per}[{a['basis']}]{sal}{sig}{ft}"


SIG_KEYS = ("sold_out", "waiting", "resv_fill")
# 파생피처 --- `_line` 이 features=True 일 때 붙이는 것들(노트 303)
FEAT_KEYS = ("trust", "weekend_share", "holiday_days", "ip_hist", "cap_type")


def _permute(anchors: list[dict], keys, seed: int) -> list[dict]:
    """keys 묶음을 앵커들 사이에서 통째로 치환한다. 씨앗 고정."""
    import random
    out = [dict(a) for a in anchors]
    vals = [tuple(a.get(k) for k in keys) for a in out]
    idx = list(range(len(vals)))
    random.Random(seed).shuffle(idx)
    for a, j in zip(out, idx):
        for k, v in zip(keys, vals[j]):
            a[k] = v
    return out


def shuffle_feats(anchors: list[dict], seed: int = 4321) -> list[dict]:
    """파생피처 다섯을 앵커들 사이에서 뒤섞는다 --- 피처 위약(노트 303).

    노트 302가 신호 층의 이득이 **내용이 아니라 모양**이라는 것을 봤다.
    하네스의 절제 팔 셋(`nomkt` · `nofeat` · `nosig`)이 전부 *지우는* 방식이라
    같은 혼동을 안고 있다. 피처에 같은 위약을 붙여 일반성을 본다."""
    return _permute(anchors, FEAT_KEYS, seed)


def shuffle_signals(anchors: list[dict], seed: int = 1234) -> list[dict]:
    """수요신호 삼종을 앵커들 사이에서 **뒤섞는다** --- 위약 팔(노트 299).

    노트 298이 신호 층만 복제되는 것을 봤는데, 그 신호 셋 중 어느 것도
    **앵커 자신의 일평균을 못 가른다**(완판 배수 1.20 p=0.23 · 대기 1.04 ·
    예약 1.00). 그러면 이득이 신호의 *내용*이 아니라 *모양*(줄이 길어지고
    토큰이 붙는 것)에서 왔을 수 있다.

    치환이라 각 신호의 **주변 분포와 프롬프트 모양이 정확히 같고** 앵커와의
    짝만 깨진다. 내용이 일하면 진짜 > 뒤섞음, 모양이 일하면 진짜 ~ 뒤섞음.
    씨앗을 고정해 실행마다 같은 치환을 쓴다."""
    return _permute(anchors, SIG_KEYS, seed)


def build_market_block(target_stimulus: dict, cap_relevant: int = 8, signals: bool = True,
                       features: bool = True, shuffle_sig: bool = False,
                       shuffle_feat: bool = False) -> str:
    """타깃 오픈 전 종료 이벤트만으로 시장 다이제스트 + 타깃 관련 상세를 구성.
    signals=False면 수요신호(완판·대기·예약), features=False면 파생피처(T등급·주말·IP회차·캡) 제거 — 절제용.
    shuffle_sig=True면 신호를 앵커 사이에서 치환한다 — 위약 팔(노트 299)."""
    cutoff = ((target_stimulus.get("conditions") or {}).get("period") or {}).get("from")
    anchors = load_anchors()
    if cutoff:
        anchors = [a for a in anchors if a["to"] and a["to"] < cutoff]
    if not anchors:
        return ""
    if shuffle_feat and features:
        anchors = shuffle_feats(anchors)
    if shuffle_sig and signals:
        # **자르고 나서 섞는다.** 전체에서 섞고 자르면 팔마다 남는 신호의
        # 주변 분포가 달라져 모양이 안 맞는다 --- 그러면 위약이 아니다.
        anchors = shuffle_signals(anchors)

    # 타깃 관련도: IP/브랜드 토큰 > 공간 토큰 > 카테고리 유사
    blob = json.dumps({"e": target_stimulus.get("entities"), "i": target_stimulus.get("intervention"),
                        "v": (target_stimulus.get("conditions") or {}).get("location")}, ensure_ascii=False)
    scored = []
    for a in anchors:
        s = 0
        if a["ip"] and len(a["ip"]) >= 2 and a["ip"] in blob:
            s += 10
        vt = [t for t in re.split(r"[ _()]", a["venue"]) if len(t) >= 3]
        if any(t in blob for t in vt):
            s += 4
        scored.append((s, a))
    rel = [a for s, a in sorted(scored, key=lambda x: -x[0]) if s > 0][:cap_relevant]

    legend = ""
    if features:
        from .predictor_llm import FEAT_LEGEND
        legend = FEAT_LEGEND + "\n"
    lines = "\n".join(_line(a, signals, features) for a in anchors)
    block = (f"\n<market_bank tier=\"주최측발표\" n=\"{len(anchors)}\">\n"
             "시장 공개 선례 (언론·주최측 발표 — 내부 실측과 등급 다름. 규칙 9 적용):\n"
             "형식: ID|이벤트|카테고리|장소|기간|방문(일평균)[집계]|매출|신호|피처\n"
             + legend + lines + "\n</market_bank>\n")
    if rel:
        det = "\n".join(f"- {_line(a, signals, features)} / 집계주석: {a['basis_note'] or '없음'}"
                         + (f" / 웨이팅: {a['waiting']}" if signals and a["waiting"] else "")
                         for a in rel)
        block += f"\n<market_relevant>\n타깃 관련 시장 선례 (IP·공간 일치):\n{det}\n</market_relevant>\n"
    return block
