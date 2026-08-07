"""크로스 도메인 IP 그래프 — 팝업(내부·시장)과 아이돌 도메인의 엔티티를 하나의 IP 노드로 정준화.

공유 상태 인코더의 선결과제(2026-07-27 설계 확정): "이 팝업의 NCT WISH"와 "이 데뷔의 NCT WISH"가
같은 IP임을 기계가 알아야 도메인 간 상태 이월이 성립한다.

노드: ip_id (정준 키)
엣지: 관측(observation) — 도메인·시점·라벨을 가진 사건
      부모/계열(parent) — NCT WISH → NCT, 산리오캐릭터즈 → 산리오

사용: python3 -m state.entity_graph [--report]
산출: data/state/ip_graph.json
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

OUT = Path("data/state/ip_graph.json")

# 계열 부모 (자식 키워드 → 부모 IP)
FAMILY = {
    "NCT": ["NCT WISH", "NCT DREAM", "NCT 127", "엔시티"],
    "산리오": ["산리오캐릭터즈", "헬로키티", "시나모롤", "쿠로미", "마이멜로디", "폼폼푸린"],
    "포켓몬": ["포켓몬스터", "피카츄", "메타몽"],
    "짱구는못말려": ["짱구", "크레용신짱"],
    "하이브": ["빅히트", "쏘스뮤직", "플레디스", "어도어", "빌리프랩", "KOZ"],
}
NOISE = re.compile(r"(팝업|스토어|팝업스토어|공식|기념|콜라보|콜라보레이션|x |X |×|주년|시즌\d?|"
                   r"in |인 서울|서울|부산|대구|팬미팅|전시|페스타|스토어$|popup|store)", re.I)


def norm(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", str(s))
    s = s.replace("unresolved:", "").strip()
    s = re.sub(r"\(.*?\)", " ", s)          # 괄호 주석 제거
    s = s.split(" X ")[0].split(" x ")[0]    # 콜라보 앞부분
    s = NOISE.sub(" ", s)
    s = re.sub(r"[^0-9A-Za-z가-힣]+", "", s)
    return s


def family_of(key: str) -> str | None:
    for parent, kids in FAMILY.items():
        if key == norm(parent):
            return None
        for k in kids:
            if norm(k) and norm(k) in key:
                return norm(parent)
    return None


def build() -> dict:
    nodes: dict[str, dict] = {}

    def add(ip_raw, domain, rec_id, date_, label, label_kind, meta):
        key = norm(ip_raw)
        if len(key) < 2:
            return
        n = nodes.setdefault(key, {"ip_id": key, "display": str(ip_raw)[:40],
                                    "parent": family_of(key), "obs": []})
        n["obs"].append({"domain": domain, "record_id": rec_id, "date": date_,
                          "label": label, "label_kind": label_kind, **meta})

    # 팝업 내부
    for p in Path("data/records").glob("*.json"):
        r = json.loads(p.read_text())
        e, o, c = r.get("entities", {}), r["outcome"], r["conditions"]
        ip = e.get("brand_key") or r["intervention"].get("brand_name")
        add(ip, "popup_internal", r["record_id"], (c.get("period") or {}).get("from"),
            o["totals"].get("visitors"), o.get("counting_method"),
            {"venue": e.get("space_key"), "trust": (o.get("label_trust") or {}).get("grade"),
             "source": o.get("label_source", "internal")})
    # 팝업 시장
    for p in Path("data/market_records").glob("*.json"):
        m = json.loads(p.read_text())
        c, o = m["conditions"], m["outcome"]
        ip = m.get("ip_or_collab") or m.get("brand")
        add(ip, "popup_market", m["market_record_id"], c.get("period_from"),
            o.get("visitors_total"), o.get("counting_basis"),
            {"venue": c.get("venue"), "trust": (o.get("label_trust") or {}).get("grade"),
             "category": m.get("category")})
    # 아이돌 (수집되면 자동 편입)
    idol = Path("data/idol_records")
    if idol.exists():
        for p in idol.glob("*.json"):
            r = json.loads(p.read_text())
            add(r.get("group_name"), "idol_debut", r.get("record_id") or p.stem,
                r.get("debut_date"), r.get("chodong"), r.get("chodong_basis"),
                {"agency": r.get("agency"), "survival": r.get("survival_show")})

    for n in nodes.values():
        n["obs"].sort(key=lambda x: x.get("date") or "")
        n["n_obs"] = len(n["obs"])
        n["n_label"] = sum(1 for x in n["obs"] if x.get("label"))
        n["domains"] = sorted({x["domain"] for x in n["obs"]})
        n["cross_domain"] = len(n["domains"]) > 1
    return nodes


def main() -> int:
    nodes = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(nodes, ensure_ascii=False, indent=1))
    multi = {k: v for k, v in nodes.items() if v["n_obs"] >= 2}
    cross = {k: v for k, v in nodes.items() if v["cross_domain"]}
    lab2 = {k: v for k, v in nodes.items() if v["n_label"] >= 2}
    print(json.dumps({"IP 노드": len(nodes), "관측 2회+": len(multi),
                       "라벨 2건+(쌍둥이)": len(lab2), "크로스 도메인": len(cross)},
                      ensure_ascii=False))
    if cross:
        print("\n크로스 도메인 IP (상태 이월 후보):")
        for k, v in sorted(cross.items(), key=lambda x: -x[1]["n_obs"])[:15]:
            print(f"  {v['display'][:24]:26s} {v['domains']} 관측 {v['n_obs']} / 라벨 {v['n_label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
