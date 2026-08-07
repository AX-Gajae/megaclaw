"""레코드 ↔ popga 스토어 링크 — 집단 상태를 라벨 관측에 연결하는 다리.

이 링크가 성립해야 "비라벨로 배운 집단 상태가 라벨 태스크(방문객·초동)로 전이되는가"를
측정할 수 있다. 매칭은 브랜드/IP 문자열 대조 + 기간 근접으로 하고, 시간 마스크를 위해
상태는 **오픈 주차 직전** 값만 취한다.

사용: python3 -m state.link_records --report
산출: data/state/record_store_link.json
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

ENC = Path("data/encoder")
OUT = Path("data/state/record_store_link.json")
NOISE = re.compile(r"(팝가|POPGA|Popga|팝업스토어|팝업|스토어|공식|기념|콜라보|전시|이벤트|"
                   r"오픈|store|popup|\||-|—)", re.I)


def norm(s) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", str(s))
    s = re.sub(r"\(.*?\)", " ", s)
    s = NOISE.sub(" ", s)
    return re.sub(r"[^0-9A-Za-z가-힣]", "", s).lower()


def iso_week(d: str) -> str | None:
    try:
        y, w, _ = date.fromisoformat(d).isocalendar()
        return f"{y}-{w:02d}"
    except Exception:
        return None


def load_stores() -> list[dict]:
    out = []
    for row in csv.reader(open(ENC / "stores.csv")):
        if len(row) < 5:
            continue
        path, users, title, d0, d1 = row[:5]
        out.append({"path": path, "users": int(users or 0), "title": title,
                    "key": norm(title), "from": d0, "to": d1})
    return out


def link() -> dict:
    stores = load_stores()
    # 긴 키 우선(구체적 매칭이 먼저 잡히도록)
    stores.sort(key=lambda s: -len(s["key"]))
    links = {}

    def try_match(rid, name, period_from):
        k = norm(name)
        if len(k) < 3:
            return None
        cands = [s for s in stores if s["key"] and (k in s["key"] or s["key"] in k)]
        if not cands:
            return None
        # 기간 근접으로 선택
        if period_from:
            def gap(s):
                try:
                    return abs((date.fromisoformat(period_from)
                                - date(int(s["from"][:4]), int(s["from"][4:6]), int(s["from"][6:8]))).days)
                except Exception:
                    return 9999
            cands.sort(key=lambda s: (gap(s), -s["users"]))
            if gap(cands[0]) > 180:
                return None
        else:
            cands.sort(key=lambda s: -s["users"])
        s = cands[0]
        return {"store": s["path"], "store_title": s["title"][:50], "users": s["users"]}

    for p in sorted(Path("data/records").glob("*.json")):
        r = json.loads(p.read_text())
        c = r["conditions"]
        pf = (c.get("period") or {}).get("from")
        for name in (r["entities"].get("brand_key"), r["intervention"].get("brand_name"),
                     (r["intervention"].get("concept") or "")[:20]):
            m = try_match(r["record_id"], name, pf)
            if m:
                m.update({"record_id": r["record_id"], "domain": "popup_internal",
                          "open_week": iso_week(pf) if pf else None,
                          "label": r["outcome"]["totals"].get("visitors")})
                links[r["record_id"]] = m
                break
    for p in sorted(Path("data/market_records").glob("*.json")):
        m0 = json.loads(p.read_text())
        pf = m0["conditions"].get("period_from")
        for name in (m0.get("ip_or_collab"), m0.get("brand"), m0.get("event_name")):
            m = try_match(m0["market_record_id"], name, pf)
            if m:
                m.update({"record_id": m0["market_record_id"], "domain": "popup_market",
                          "open_week": iso_week(pf) if pf else None,
                          "label": m0["outcome"].get("visitors_total")})
                links[m0["market_record_id"]] = m
                break
    return links


def main() -> int:
    links = link()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(links, ensure_ascii=False, indent=1))
    lab = [v for v in links.values() if v.get("label")]
    wk = [v for v in lab if v.get("open_week")]
    print(json.dumps({"링크된 레코드": len(links), "그중 라벨 보유": len(lab),
                       "오픈주차까지 확보": len(wk), "저장": str(OUT)}, ensure_ascii=False))
    for v in list(lab)[:6]:
        print(f"  {v['record_id']} → {v['store']} ({v['store_title'][:34]}) 유저 {v['users']} 라벨 {v['label']:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
