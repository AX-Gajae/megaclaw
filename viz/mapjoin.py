"""지도 경계와 방문자 API 를 **시도까지 보고** 붙인다(노트 647).

이름만으로 붙이면 안 된다 --- ``중구`` 는 여섯 곳, ``서구`` 는 다섯 곳이다.
처음에 이름만으로 붙였더니 한 지도 구역에 API 코드 여섯 개가 몰렸다.

그리고 두 코드 체계가 다르다. 지도는 통계청 **2013년** 코드(제주 39 · 경남 38)
이고 API 는 현행 행정표준코드(제주 50 · 경남 48)다. 시도 대응표를 손으로
적는다 --- 열일곱 개뿐이고 안 바뀐다.

**부모 시를 버린다.** API 는 ``수원시`` 와 ``수원시 장안구`` 를 **둘 다** 준다.
지도에는 구만 있으므로 부모를 같이 칠하면 이중 계상이다. 구가 있는 시는
부모를 뺀다.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data/state/geo"

#: 현행 시도코드 → 2013 통계청 시도코드
SIDO_MAP = {"11": "11", "26": "21", "27": "22", "28": "23", "29": "24",
            "30": "25", "31": "26", "36": "29", "41": "31", "43": "33",
            "44": "34", "46": "36", "47": "37", "48": "38", "50": "39",
            "51": "32", "52": "35"}


def build() -> dict:
    from ingest.visitors import sgg_index
    idx = sgg_index()
    names = {c: n for (_s, n), c in idx.items()}
    feats = json.loads((GEO / "sigungu.json").read_text())["features"]

    # (2013시도, 정규화이름) → 지도코드
    gmap: dict = {}
    for f in feats:
        p = f["properties"]
        gmap[(p["code"][:2], p["name"].replace(" ", ""))] = p["code"]

    # 구를 가진 부모 시는 뺀다 --- 이중 계상 방지
    kids = {n.split(" ")[0] for n in names.values() if " " in n}
    out, miss = {}, []
    for code, nm in names.items():
        if nm in kids:                       # '수원시' 같은 부모
            continue
        sd = SIDO_MAP.get(code[:2])
        if not sd:
            miss.append((code, nm, "시도없음"))
            continue
        key = nm.replace(" ", "")
        hit = gmap.get((sd, key))
        if hit is None and " " in nm:        # '수원시 장안구' → '장안구'
            hit = gmap.get((sd, nm.split(" ", 1)[1].replace(" ", "")))
        if hit is None:
            miss.append((code, nm, "이름없음"))
        else:
            out[code] = hit
    rev: dict = {}
    for a, g in out.items():
        rev.setdefault(g, []).append(a)
    dup = {k: v for k, v in rev.items() if len(v) > 1}
    (GEO / "code_map.json").write_text(json.dumps(out, ensure_ascii=False))
    return {"붙음": len(out), "부모 제외": len(kids), "못 붙음": miss,
            "중복": dup, "지도 구역": len(feats)}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=1))
