"""제작 주체의 사전 출시작 수 --- 이름이 없던 축(노트 166).

노트 164가 코드를 읽어 \\texttt{venue\\_prominence} 슬롯이 열 도메인 중
일곱에서 실은 ``제작사/개발사의 사전 출시작 수''임을 확인했고, 노트 165가
그것을 따로 세우면 사전 부호가 **5/5** 임을 쟀다. 다섯 칸뿐이라 우연일 수
있어서, 아직 안 붙은 세 도메인(게임 · 애니 · 웹툰)에도 같은 구성물을
만들어 여덟 칸으로 늘린다.

**세는 법은 기존 모듈과 같다 --- 표본 안 시간 인과.** 레코드 $i$ 에 대해
같은 제작 주체를 가지면서 날짜가 앞선 레코드의 수를 센다. 그러므로
사전 정보이고 노트 141의 시점 규칙을 통과한다.

    웹툰   artists      (작가 --- 여럿이면 각각 세고 최대를 쓴다)
    애니   production   (제작사)
    게임   publishers   (퍼블리셔 --- game_axes 가 이미 세지만 마스크가 0이다)

**0은 결측이 아니다**(게임 모듈의 주석 그대로). ``표본 안 사전작 0건''은
관측된 값이다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

SRC = {
    "웹툰": ("webtoon_records.json", "webtoon_axes.json", "artists",
           "start_date"),
    "애니": ("anime_records.json", "anime_axes.json", "production",
           "start_date"),
    "게임": ("game_records.json", "game_axes.json", "publishers",
           "release_date"),
}


def _names(v) -> list:
    if v is None:
        return []
    if isinstance(v, (list, tuple, set)):
        return [str(x).strip() for x in v if str(x).strip()]
    s = str(v).strip()
    return [s] if s else []


def _prior(items, key, dkey) -> dict:
    """{record_id: 사전작 수}. 같은 주체 · 더 이른 날짜만 센다."""
    rows = []
    for r in items:
        rid = r.get("record_id")
        d = str(r.get(dkey) or "")[:10]
        if not rid or len(d) < 7:
            continue
        rows.append((rid, d, _names(r.get(key))))
    rows.sort(key=lambda x: x[1])
    seen: dict = {}
    out = {}
    for rid, d, ns in rows:
        out[rid] = max((seen.get(n, 0) for n in ns), default=0)
        for n in ns:
            seen[n] = seen.get(n, 0) + 1
    return out


@lru_cache(maxsize=1)
def build() -> dict:
    """{'creator_track': {도메인: (값, 표시자)}} --- harness.load 가 받는 모양."""
    col = {}
    for d, (recf, axf, key, dkey) in SRC.items():
        rp, ap = Path("data/state") / recf, Path("data/state") / axf
        if not (rp.exists() and ap.exists()):
            continue
        recs = json.loads(rp.read_text())
        items = list(recs.values()) if isinstance(recs, dict) else recs
        pri = _prior(items, key, dkey)
        ids = list(json.loads(ap.read_text()))
        raw = np.array([pri.get(i, np.nan) for i in ids], float)
        ok = np.isfinite(raw)
        if ok.sum() < 20:
            continue
        v = np.full(len(raw), 0.5)
        v[ok] = rankdata(np.log2(raw[ok] + 1)) / ok.sum()
        col[d] = (v, ok.astype(float))
    return {"creator_track": col} if col else {}


def coverage() -> dict:
    b = build().get("creator_track") or {}
    return {d: {"행": len(v[0]), "덮음": round(float(v[1].mean()), 3),
                "사전작 0건 비율": round(float((v[0][v[1] > 0] ==
                                          np.min(v[0][v[1] > 0])).mean()), 3)}
            for d, v in b.items()}


if __name__ == "__main__":
    print(json.dumps(coverage(), ensure_ascii=False, indent=1))
