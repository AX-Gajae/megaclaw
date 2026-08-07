"""달력 축 --- 전 도메인 공통이고 수집 비용이 0이다.

**왜 이걸 재나.** 노트 130에서 팝업의 일평균 방문자를 무엇이 정하는지 갈라
봤더니 뜻밖의 답이 나왔다.

    주말 비중        $+$0.427     달력
    500m 내 경쟁     $+$0.313     공급
    공휴일수         $+$0.251     달력
    장소 유동        $+$0.219     공급
    오픈 전 검색      $+$0.088     수요

수요도 장소도 아니고 \\textbf{달력}이 제일 세다. 그리고 달력은 검색과 달리
\\emph{전 도메인이 공유}한다 --- 어느 작품이든 언제 나오는지는 있다.
노트 126이 ``공통 축만 값어치가 있다''고 했고 노트 128의 검색 축이 그
예언을 맞혔다. 달력은 같은 조건을 맞추면서 **API 한 번도 안 쓴다.**

축 여섯.

    요일     내는 날의 요일 (주기 좌표 둘)
    주말     금·토·일에 시작하나
    계절     달 (주기 좌표 둘)
    연휴     가장 가까운 장기연휴 블록까지의 거리

전부 오픈 훨씬 전에 확정되므로 시간 마스크를 자동으로 통과한다.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

D = Path("data/state")
# 도메인 → (레코드 파일, 날짜 필드)
SPEC = {"게임": ("game_records.json", "release_date"),
        "도서": ("book_records.json", "pub_date"),
        "만화": ("manga_records.json", "start_date"),
        "모바일": ("mobile_records.json", "release_date"),
        "세계애니": ("wanime_records.json", "start_date"),
        "애니": ("anime_records.json", "start_date"),
        "웹툰": ("webtoon_records.json", "start_date"),
        "펀딩": ("funding_records.json", "start_date")}
FEATS = ["cal_dow_sin", "cal_dow_cos", "cal_weekend",
         "cal_month_sin", "cal_month_cos", "cal_holiday_gap"]


@lru_cache(maxsize=1)
def _blocks() -> list:
    """장기연휴 블록 --- 공휴일·주말이 사흘 이상 이어지는 구간."""
    from ingest.derive_features import HOLIDAYS
    hs = {date(*(int(x) for x in h.split("-"))) for h in HOLIDAYS}
    if not hs:
        return []
    lo, hi = min(hs) - timedelta(days=400), max(hs) + timedelta(days=400)
    off, cur, out = lo, [], []
    while off <= hi:
        rest = off.weekday() >= 5 or off in hs
        if rest:
            cur.append(off)
        else:
            if len(cur) >= 3:
                out.append((cur[0], cur[-1]))
            cur = []
        off += timedelta(days=1)
    if len(cur) >= 3:
        out.append((cur[0], cur[-1]))
    return out


def _feat(d: date) -> dict:
    dow = d.weekday()                       # 0=월
    bl = _blocks()
    gap = min((min(abs((d - a).days), abs((d - b).days)) for a, b in bl),
              default=999)
    inside = any(a <= d <= b for a, b in bl)
    return {"cal_dow_sin": math.sin(2 * math.pi * dow / 7),
            "cal_dow_cos": math.cos(2 * math.pi * dow / 7),
            "cal_weekend": 1.0 if dow >= 4 else 0.0,        # 금·토·일
            "cal_month_sin": math.sin(2 * math.pi * (d.month - 1) / 12),
            "cal_month_cos": math.cos(2 * math.pi * (d.month - 1) / 12),
            "cal_holiday_gap": 0.0 if inside else float(min(gap, 120))}


def _parse(s) -> date | None:
    s = str(s or "")[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return None
    try:
        return date(*(int(x) for x in s.split("-")))
    except ValueError:
        return None


@lru_cache(maxsize=1)
def _dates() -> dict:
    """도메인 → 행 순서대로의 날짜. lab/trendaxes 의 id 순서를 따른다."""
    from .trendaxes import _ids
    ids = _ids()
    out = {}
    for dom, (f, df) in SPEC.items():
        p = D / f
        if not p.exists() or dom not in ids:
            continue
        j = json.loads(p.read_text())
        out[dom] = [_parse((j.get(k) or {}).get(df)) for k in ids[dom]]
    # 팝업 · 아이돌은 별도 저장소
    pm = D / "popup_v2_meta.json"
    if pm.exists() and "팝업" in ids:
        by = {m["id"]: m.get("date") for m in json.loads(pm.read_text())}
        out["팝업"] = [_parse(by.get(k)) for k in ids["팝업"]]
    ip = D / "idol_axes.json"
    if ip.exists() and "아이돌" in ids:
        j = json.loads(ip.read_text())
        out["아이돌"] = [_parse((j.get(k) or {}).get("debut_date")
                               if isinstance(j.get(k), dict) else None)
                       for k in ids["아이돌"]]
    return out


def _pct(raw):
    ok = np.isfinite(raw)
    v = np.full(len(raw), 0.5)
    if ok.sum() > 20:
        v[ok] = rankdata(raw[ok]) / ok.sum()
    return v, ok.astype(float)


@lru_cache(maxsize=1)
def _holiday_span():
    """공휴일 목록이 덮는 구간. 그 밖에서는 ``다음 연휴까지''가 정의 안 된다."""
    from ingest.derive_features import HOLIDAYS
    hs = sorted(HOLIDAYS)
    if not hs:
        return None, None
    lo = date(*(int(x) for x in hs[0].split("-")))
    hi = date(*(int(x) for x in hs[-1].split("-")))
    return lo, hi


def build(feats=tuple(FEATS)) -> dict:
    """{축이름: {도메인: (값, 표시자)}}

    **공휴일 간격은 목록 밖에서 결측이다**(노트 213). 목록이 2023-01-01
    부터라 그 이전 레코드는 가까운 연휴를 못 찾고 ``min(gap, 120)'' 의
    상한에 붙는다 --- 만화 94\% · 세계애니 76\% · 모바일 60\%가 상한값이고,
    상한인 것의 **100\%가 2023년 이전**이다. 상한 표시자와 연도의 상관이
    여덟 도메인에서 $-$0.80$\sim$$-$0.87 이다 --- **그 축이 사실상 시간
    분할 변수의 대리였다.**

    목록 밖을 결측으로 돌리면 F6 능형 $+$0.0133($t{=}3.1$) · F21
    $+$0.0123($t{=}2.9$)이고 챔피언은 안 움직인다. 축을 통째로 끄면 챔피언이
    $-$0.0205 잃으므로 **축 자체는 값이 있고 목록 밖 값만 해로웠다.**"""
    dd = _dates()
    lo, hi = _holiday_span()
    out = {}
    for f in feats:
        col = {}
        for dom, ds in dd.items():
            raw = np.array([_feat(x)[f] if x else np.nan for x in ds], float)
            if f == "cal_holiday_gap" and lo is not None:
                for i, x in enumerate(ds):
                    if x is None or x < lo or x > hi:
                        raw[i] = np.nan
            if np.isfinite(raw).sum() < 20:
                continue
            col[dom] = _pct(raw)
        if col:
            out[f] = col
    return out


def coverage() -> dict:
    dd = _dates()
    return {k: {"행": len(v), "날짜 있음": sum(1 for x in v if x),
                "덮음": round(sum(1 for x in v if x) / max(1, len(v)), 3)}
            for k, v in sorted(dd.items())}


if __name__ == "__main__":
    print(json.dumps(coverage(), ensure_ascii=False, indent=1))
