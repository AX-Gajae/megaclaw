"""풀의 그림자 --- 풀을 넓히려 할 때 **자료가 옛 풀 모양인지** 본다(노트 326).

노트 325가 아이돌 94행이 왜 안 쓰이는지 보고 ``라벨 기준이 섞이면 기준이 곧
표지가 된다''로 끝냈다. 노트 326이 재 보니 그 논리는 모형이 기준을 볼 수
있을 때만 성립했고, 채점이 도메인 안 순위라 **수준 이동은 안 아팠다.**
진짜로 막은 것은 다른 것이었다.

    위키      한터 풀 99%   추가 94행 0%
    앨범 메타  한터 풀 100%  추가 94행 0%

**우리가 풀 안쪽만 긁었다.** 그래서 위키 표시자가 한터 여부와 99.4% 같고,
기준이 라벨을 0.58 log10 갈라 놓으므로 그 표시자가 곧 사후 표지가 된다.
노트 306은 *바깥 세계*가 결과에 따라 문서를 만든 경우였고 이것은 **우리가
만든** 사후 표시자다 --- 더 조용하다.

**필터를 만든 날에는 안 보인다.** 필터는 라벨을 고르는 결정이었는데, 그
뒤의 수집이 전부 그 결정을 따라가면서 필터가 **축의 결측에도 새겨진다.**
나중에 필터를 풀려고 하면 라벨이 아니라 결측이 막는다.

**이름표지 거부권이 아니다**(``hearing`` · ``overlap`` · ``marker`` ·
``ordering`` 과 같은 규약). 넓히지 말라고 막는 게 아니라, 넓히기 전에
**어떤 재료가 옛 풀 모양인지** 적어 둔다. 고치는 법은 둘뿐이다.

    ① 그 재료를 새 행에도 긁는다      --- 수집 과제
    ② 그 재료를 **뺀다**              --- 노트 326이 고른 쪽

②가 이길 때가 있다. 아이돌에서 뺀 축 둘은 한터만 쓸 때도 안 벌고 있었고
(0.2249 대 0.2199), 빼고 94행을 넣으니 0.2199 -> 0.4728 이 됐다.
**아무것도 안 버는 축 둘을 지키느라 행 94개를 못 쓰고 있었다.**
"""
from __future__ import annotations

BIG = 0.30             # 관측률 차가 이보다 크면 그 재료는 풀 모양이다
MIN_ROWS = 20


def gap(used: set, cand: set, have: set) -> dict:
    """한 재료. ``have`` 는 그 재료가 있는 키 집합."""
    used, cand = set(used), set(cand) - set(used)
    if len(used) < MIN_ROWS or len(cand) < MIN_ROWS:
        return {"판정": "못 잰다", "판": len(used), "후보": len(cand)}
    a = sum(1 for k in used if k in have) / len(used)
    b = sum(1 for k in cand if k in have) / len(cand)
    d = a - b
    return {"판": len(used), "후보": len(cand),
            "관측률 판": round(a, 3), "관측률 후보": round(b, 3),
            "차": round(d, 3),
            "판정": ("풀 모양" if abs(d) >= BIG else "괜찮다"),
            # 부호가 뜻을 갖는다 --- 어느 쪽이 덜 긁혔나
            "누가 비었나": ("후보" if d > 0 else "판") if abs(d) >= BIG else None}


def report(used: set, cand: set, mats: dict) -> dict:
    """``mats`` 는 {재료 이름: 그 재료가 있는 키 집합}.

    넓히기 **전에** 부른다. 판정이 ``풀 모양''인 재료는 넓힌 판에서
    표시자가 곧 옛 풀의 표지가 된다."""
    out, bad = {}, []
    for name, have in mats.items():
        g = gap(used, cand, have)
        out[name] = g
        if g.get("판정") == "풀 모양":
            bad.append(f"{name}({g['차']:+.0%})")
    return {"재료": out, "풀 모양": bad,
            "한 줄": ("풀 그림자 --- " + ", ".join(bad)) if bad
                    else "풀 그림자 --- 없음"}


def from_files(axes_json: str, records_json: str, mats: dict) -> dict:
    """축 json 의 키가 곧 판이 쓰는 행이고, 레코드 json 이 후보 전체다."""
    import json
    from pathlib import Path
    ax = json.loads(Path(axes_json).read_text())
    rec = json.loads(Path(records_json).read_text())
    keys = set(rec) if isinstance(rec, dict) else {
        r.get("record_id") for r in rec if isinstance(r, dict)}
    return report(set(ax), keys, mats)


def wiki_keys(root: str = ".") -> set:
    from pathlib import Path
    return {f.stem for f in (Path(root) / "data/state/wiki_views").glob("*.json")}


def trend_keys(name: str, root: str = ".") -> set:
    import json
    from pathlib import Path
    p = Path(root) / "data/state/naver" / f"{name}.json"
    return set(json.loads(p.read_text())) if p.exists() else set()


# 도메인 → (축 json, 레코드 json, 검색 파일). ``provenance.RECORDS`` 와 같은
# 자리인데 여기서는 **판이 안 쓰는 행**을 알아야 하므로 짝으로 둔다.
SPEC = {
    "만화": ("manga_axes", "manga_records", "manga_trend"),
    "세계애니": ("wanime_axes", "wanime_records", None),
    "도서": ("book_axes", "book_records", "book_trend"),
    "웹툰": ("webtoon_axes", "webtoon_records", "webtoon_trend"),
    "애니": ("anime_axes", "anime_records", "anime_trend"),
    "모바일": ("mobile_axes", "mobile_records", "mobile_trend"),
    "펀딩": ("funding_axes", "funding_records", "funding_trend"),
    "게임": ("game_axes", "game_records", "game_trend"),
}


def audit(root: str = ".") -> dict:
    """판 전체. 아이돌은 레코드가 파일 하나씩이라 따로 센다."""
    import json
    from pathlib import Path
    D = Path(root) / "data/state"
    wk = wiki_keys(root)
    out, flags = {}, []
    for dom, (af, rf, tf) in SPEC.items():
        ap, rp = D / f"{af}.json", D / f"{rf}.json"
        if not ap.exists() or not rp.exists():
            continue
        mats = {"위키": wk}
        if tf:
            t = trend_keys(tf, root)
            if t:
                mats["검색"] = t
        r = from_files(str(ap), str(rp), mats)
        out[dom] = r
        for m in r["풀 모양"]:
            flags.append(f"{dom}·{m}")
    ip = Path(root) / "data/idol_records"
    if ip.is_dir():
        recs = [json.loads(f.read_text()) for f in sorted(ip.glob("*.json"))]
        U = [x for x in recs if x.get("chodong") and x.get("debut_date")]
        used = {x["record_id"] for x in U
                if x.get("chodong_basis_resolved") == "hanteo"}
        alb = D / "idol_album_meta.json"
        mats = {"위키": wk, "검색": trend_keys("idol_trend", root)}
        if alb.exists():
            mats["앨범메타"] = set(json.loads(alb.read_text()))
        r = report(used, {x["record_id"] for x in U}, mats)
        out["아이돌"] = r
        for m in r["풀 모양"]:
            flags.append(f"아이돌·{m}")
    return {"도메인": out, "풀 모양": flags,
            "한 줄": ("풀 그림자 --- " + ", ".join(flags)) if flags
                    else "풀 그림자 --- 없음"}


if __name__ == "__main__":
    a = audit()
    print(a["한 줄"])
    for dom, r in a["도메인"].items():
        for k, v in r["재료"].items():
            if "차" in v:
                print(f"  {dom:<8}{k:<6} 판 {v['관측률 판']:.2f}"
                      f" 후보 {v['관측률 후보']:.2f}  차 {v['차']:+.2f}"
                      f"  {v['판정']}")
            else:
                print(f"  {dom:<8}{k:<6} {v.get('판정')}"
                      f" (판 {v.get('판')} 후보 {v.get('후보')})")
