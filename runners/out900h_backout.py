# -*- coding: utf-8 -*-
"""지평 900 — 조항 60: 저장소가 이미 가진 열로 두 필드를 역산할 수 있나. 읽기 전용."""
import json, glob, re, collections
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
ax = json.load(open(ROOT / "data/state/market_axes.json"))

FREE_POS = [r"무료\s*입장", r"입장\s*무료", r"무료로\s*입장", r"관람\s*무료", r"입장료\s*(는\s*)?없", r"무료\s*운영", r"누구나\s*무료"]
FREE_NEG = [r"입장료", r"유료\s*입장", r"입장\s*유료", r"티켓\s*(가격|구매|판매|값)", r"관람료", r"\d[\d,]*\s*원\s*(의\s*)?입장"]
RESV_POS = [r"사전\s*예약", r"예약\s*(필수|제)", r"네이버\s*예약", r"캐치테이블", r"예약\s*링크", r"예약자\s*(만|에\s*한)", r"예약\s*후\s*(방문|입장)"]
RESV_NEG = [r"예약\s*없이", r"예약\s*불(필요|가)", r"현장\s*(방문|접수|등록)만", r"워크\s*인", r"walk[- ]?in", r"자유\s*관람"]
ANY_RESV = [r"예약"]

def txt(d):
    iv = d.get("intervention") or {}; oc = d.get("outcome") or {}; ds = oc.get("demand_signals") or {}
    parts = [d.get("event_name"), d.get("brand"), d.get("ip_or_collab"), d.get("notes"),
             iv.get("concept_description"), oc.get("counting_basis_note"),
             oc.get("visitors_source_quote"), oc.get("sales_source_quote"),
             ds.get("waiting_time_reported")]
    parts += list(iv.get("experience_elements") or []) + list(iv.get("promotions") or [])
    parts += list(ds.get("signal_quotes") or [])
    return " \n ".join(str(x) for x in parts if x)

def hit(pats, s): return [p for p in pats if re.search(p, s)]

recs = {}
for f in glob.glob(str(ROOT / "data/market_records/*.json")):
    d = json.load(open(f)); recs[d["market_record_id"]] = d

groups = {
 "유보결측37": [k for k in ax if ax[k]["period_from"][:4] >= "2025"
        and (recs[k]["intervention"].get("is_free_entry") is None
             and recs[k]["intervention"].get("reservation_required") is None)],
 "축파일결측88": [k for k in ax
        if (recs[k]["intervention"].get("is_free_entry") is None
            and recs[k]["intervention"].get("reservation_required") is None)],
 "MKT2전체239": [k for k in recs if k.startswith("MKT2")],
 "MKT값있음(검정용)": [k for k in recs if not k.startswith("MKT2")
        and recs[k]["intervention"].get("is_free_entry") is not None],
}

for name, ids in groups.items():
    fp = fn = rp = rn = both = 0; anyr = 0
    for k in sorted(ids):
        s = txt(recs[k])
        a, b = bool(hit(FREE_POS, s)), bool(hit(FREE_NEG, s))
        c, e = bool(hit(RESV_POS, s)), bool(hit(RESV_NEG, s))
        fp += a; fn += b; rp += c; rn += e
        anyr += bool(hit(ANY_RESV, s))
        both += (a or b) and (c or e)
    print("%-16s n=%4d | 무료단서 %3d · 유료단서 %3d · 예약필요단서 %3d · 예약없음단서 %3d · '예약'언급 %3d · 둘다 %3d"
          % (name, len(ids), fp, fn, rp, rn, anyr, both))

# 검정: MKT 에서 값이 있는 행에 규칙을 돌려 정확도를 잰다
print("\n=== 규칙 검정 (MKT 중 값이 있는 행) ===")
for fld, POS, NEG, want_pos in (("is_free_entry", FREE_POS, FREE_NEG, True),
                                ("reservation_required", RESV_POS, RESV_NEG, True)):
    tab = collections.Counter()
    for k, d in recs.items():
        if k.startswith("MKT2"): continue
        v = d["intervention"].get(fld)
        if v is None: continue
        s = txt(d)
        p, n = bool(hit(POS, s)), bool(hit(NEG, s))
        pred = "pos" if (p and not n) else ("neg" if (n and not p) else ("both" if p and n else "none"))
        tab[(bool(v), pred)] += 1
    print(" ", fld)
    for kk in sorted(tab, key=lambda x: (x[0], x[1])):
        print("     실제=%-5s 규칙=%-5s %4d" % (kk[0], kk[1], tab[kk]))
