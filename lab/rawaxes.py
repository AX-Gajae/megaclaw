"""원천 레코드에서 캐낸 **전용 축 열**(노트 324).

노트 321이 축 파일(``*_axes.json``)의 안 쓰인 필드를 훑어 하나를 찾았다.
**원천 레코드**(``*_records.json``)로 넓히니 검사 ①③④ 를 통과하는 후보가
\\textbf{마흔셋} 나왔다 --- 그런데 **서른둘(74%)을 출처가 막는다.**

    사후 --- 라벨 자체        y_positive · y_raw · y_w30 · y_favorite ·
                            y_review · y_popularity · y_backers
    사후 --- 지금 긁은 스냅샷  favourites · mean_score · avg_rating ·
                            review_count · sales_point (노트 224)
    사후 --- 식별자           title_id · media_id · item_id · series_id ·
                            artist_id (시간과 붙는다)
    사후 --- 끝나야 붙는다     finished (노트 255)
    사후 의심 --- 쌓인다       n_episode · n_tag
    사후 의심                is_dubbed · daily_pass

**통계만으로는 못 고른다.** 노트 323의 규약("도구를 만들었으면 주장할 때마다
부르라")의 짝이다 --- 도구가 마흔셋을 주고 사람이 열하나로 줄인다.

남은 열하나 중 검사 ②(시간 조각 다섯 부호 일치)를 무리 셋 이상으로 돌릴 수
있는 **열 개**가 전부 5/5 다. 그 열을 여기서 만든다.

    모바일   advisory   n_genre   n_lang
    웹툰    age_type
    애니    air_quarter   production
    세계애니  n_genre   source   studio_name
    펀딩    max_price

**시점은 전부 사전이다** --- 연령 등급 · 장르 수 · 지원 언어 수(출시 시점
확정) · 이용 등급 · 방영 분기 · 제작사 · 원작 매체 · 최고 후원가(등록 시).

눈금:
    범주형  집단을 크기 순으로 0~1(``grpaxes``·``mktaxes``·``fundaxes`` 관례),
            20건 미만은 마스크 0
    수치형  관측된 값만 ``rankdata`` 로 백분위(노트 292 --- ``argsort`` 두 번은
            동률을 행 순서로 깬다)

**라벨을 한 번도 안 본다.** 범주는 집단 크기만, 수치는 값의 순위만 쓴다.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

D = Path("data/state")
MIN_GROUP = 20

# (도메인, 축 파일, 레코드 파일, 필드, 범주형인가, 축 이름)
SPEC = [
    ("모바일", "mobile_axes", "mobile_records", "advisory", True, "mob_advisory"),
    ("모바일", "mobile_axes", "mobile_records", "n_genre", False, "mob_ngenre"),
    ("모바일", "mobile_axes", "mobile_records", "n_lang", False, "mob_nlang"),
    ("웹툰", "webtoon_axes", "webtoon_records", "age_type", True, "wt_agetype"),
    ("애니", "anime_axes", "anime_records", "air_quarter", True, "ani_quarter"),
    ("애니", "anime_axes", "anime_records", "production", True, "ani_studio"),
    ("세계애니", "wanime_axes", "wanime_records", "n_genre", False, "wa_ngenre"),
    ("세계애니", "wanime_axes", "wanime_records", "source", True, "wa_source"),
    ("세계애니", "wanime_axes", "wanime_records", "studio_name", True, "wa_studio"),
    ("펀딩", "funding_axes", "funding_records", "max_price", False, "fund_maxprice"),
]


def _cat(raw, min_group: int):
    c = Counter(x for x in raw if x not in (None, ""))
    big = [u for u, n in c.items() if n >= min_group]
    if len(big) < 2:
        return None
    order = sorted(big, key=lambda u: -c[u])
    pos = {u: i / max(1, len(order) - 1) for i, u in enumerate(order)}
    v = np.array([pos.get(x, 0.5) for x in raw], np.float32)
    o = np.array([1.0 if x in pos else 0.0 for x in raw], np.float32)
    return v, o


def _num(raw):
    v = np.array([x if isinstance(x, (int, float)) and not isinstance(x, bool)
                  else np.nan for x in raw], float)
    ok = np.isfinite(v)
    if ok.sum() < 30 or len(np.unique(v[ok])) < 3:
        return None
    out = np.full(len(v), 0.5)
    out[ok] = (rankdata(v[ok]) - 1.0) / max(int(ok.sum()) - 1, 1)
    # 노트 292 의 단언 --- 백분위는 단조라 값 가짓수가 늘면 안 된다
    if len(np.unique(out[ok])) != len(np.unique(v[ok])):
        raise AssertionError("동률을 깼다")
    return out.astype(np.float32), ok.astype(np.float32)


def build(root: str = ".", min_group: int = MIN_GROUP) -> dict:
    out = {}
    for dom, axf, recf, field, cat, name in SPEC:
        ap, rp = Path(root) / D / f"{axf}.json", Path(root) / D / f"{recf}.json"
        if not (ap.exists() and rp.exists()):
            continue
        ax = json.loads(ap.read_text())
        rec = json.loads(rp.read_text())
        byid = rec if isinstance(rec, dict) else {
            x.get("record_id") or x.get("id"): x for x in rec}
        ids = list(ax)
        raw = [(byid.get(k) or {}).get(field) for k in ids]
        got = _cat(raw, min_group) if cat else _num(raw)
        if got is None:
            continue
        out[name] = {dom: got}
    return out


if __name__ == "__main__":
    d = build()
    print(f"전용 축 {len(d)}개")
    for k, v in d.items():
        dom = list(v)[0]
        val, msk = v[dom]
        print(f"  {k:<16}{dom:<8}{len(val):>6}행 · 마스크 {100*float(msk.mean()):>3.0f}%"
              f" · 값 {len(np.unique(val[msk > .5])):>4}가지")
