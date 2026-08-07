"""출시 혼잡도 — **(시간 × 대상)** 형태의 첫 무료 축(노트 650).

노트 649 가 규칙을 하나 줬다.

    범도메인 상태 축이 서려면 같은 날짜라도 **대상마다 값이 달라야** 한다.
    상태는 *시간* 이 아니라 **(시간 × 대상)** 으로 들어와야 한다.

전국 이동량은 날짜만의 축이라 세 변형(수준 · 차분 · 추세제거) 전부 실패했다
(−0.0211 · −0.0177 · −0.0092, 다 0/12). 그리고 실패 무늬가 **축 내용과
무관했다** --- 아이돌(덮음 0)이 세 번 다 +0.05 를 벌었다. 검색 · 위키 축이
선 이유가 그 형태이고, 지역 방문자수가 팝업에서만 양수였던 이유도 그것이다
(장소가 있어야 (시간 × 대상) 이 된다).

**그러면 수집 없이 그 형태가 되는 것이 있나.** 있다 --- `genres` 다.
`lab/genaxes`(노트 419)가 다섯 도메인(만화 · 모바일 · 애니 · 세계애니 · 게임)에
**어휘를 공유하는** 갈래를 이미 세워 뒀다. 그러면 이렇게 물을 수 있다:

    이 작품이 나오기 **직전 90일**에, **같은 갈래**로 몇이나 나왔나.

같은 날 나온 두 작품이라도 갈래가 다르면 값이 다르다 --- **(시간 × 대상)** 이다.
그리고 긁을 것이 없다. 레코드만 있으면 된다.

**노트 649 의 함정을 피해 짓는다.** 생 개수를 쓰면 안 된다 --- 우리 레코드는
최근 연도가 더 촘촘해서 개수가 **시간 추세**를 그대로 나른다. 그러면 방금
실패한 것과 같은 물건이 된다. 그래서 **몫**으로 쓴다:

    crowd_share = (직전 90일 같은 갈래 출시 수) / (직전 90일 전체 출시 수)

몫은 촘촘함에 안 흔들리고 갈래로만 갈린다. **열은 하나만 넣는다**(노트 641).

**시간 게이트.** 직전 창만 본다 --- 출시 당일과 이후는 한 칸도 안 본다.
기획 시점에 *이미 나온 것* 은 알 수 있지만 *앞으로 나올 것* 은 모른다.

**한계를 미리 적는다.** 우리 레코드는 시장 전수가 아니라 표본이므로 이 몫은
*시장 혼잡도* 가 아니라 **우리 표본 안의 혼잡도**다. 표본 뽑기가 갈래마다
다르면 그 편의가 축에 실린다 --- 노트 554 가 만화·위키에서 당한 자리다.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import numpy as np

WIN = 90         # 출시 이전 창(일)
MIN_TOT = 10     # 창 안 전체 출시가 이만큼은 있어야 몫이 뜻이 있다

#: **축을 받는 도메인.** `None` 이면 갈래가 있는 도메인 전부(기본).
#:
#: 노트 675 가 `gen` 겹침 ↔ 신호 몫 스피어만 **−1.000** 을 쟀다(만화 0.316 →
#: +0.0184 · 모바일 0.770 → −0.0104). 그 표로 처방을 만들면 노트 551·560·563
#: 이 세 번 밟은 함정이므로 **단일 전환으로 다시 재려고** 이 손잡이를 뒀다.
#:
#: **풀(몫의 분모)은 줄이지 않는다** --- 갈래 어휘는 도메인 사이에서 공유되므로
#: 분모를 줄이면 축의 정의가 바뀐다. 바뀌는 것은 *누가 그 열을 받나* 뿐이다.
DOMS = None


def _pct(v: np.ndarray, ok: np.ndarray) -> np.ndarray:
    from scipy.stats import rankdata
    out = np.zeros(len(v), np.float32)
    if ok.sum() < 3:
        return out
    r = rankdata(v[ok]) - 1.0
    out[ok] = (r / max(ok.sum() - 1, 1)).astype(np.float32)
    n_in, n_out = len(np.unique(v[ok])), len(np.unique(out[ok]))
    if n_out != n_in:
        raise AssertionError(f"_pct 가 동률을 깼다: {n_in} → {n_out}")
    return out


def _rows():
    """(도메인, 행 순서, 날짜, 갈래집합) — `genaxes` 와 같은 어휘를 쓴다."""
    from .calaxes import _dates
    from .genaxes import CANON, SRC
    from .trendaxes import _ids
    ids, dates = _ids(), _dates()
    D = Path("data/state")
    out = {}
    for dom, ds in dates.items():
        f = SRC.get(dom)
        recs = {}
        if f and (D / f).exists():
            recs = json.loads((D / f).read_text())
        gs = []
        for k in (ids.get(dom) or []):
            g = (recs.get(k) or {}).get("genres") if isinstance(recs, dict) else None
            if isinstance(g, str):
                g = [g]
            s = set()
            if isinstance(g, list):
                for x in g:
                    c = CANON.get(str(x).strip().lower())
                    if c:
                        s.add(c)
            gs.append(s)
        n = min(len(ds), len(gs)) if gs else 0
        out[dom] = (ds[:n], gs[:n])
    return out


def build(report: bool = False) -> dict:
    """{"crowd_share": {도메인: (값, 표시자)}} — 갈래가 있는 도메인만."""
    rows = _rows()
    # 전 도메인을 한 통에 넣는다 --- 갈래 어휘를 공유하므로 도메인을 안 가른다
    pool = []
    for _dom, (ds, gs) in rows.items():
        for d, g in zip(ds, gs):
            if d is not None and g:
                pool.append((d, g))
    pool.sort(key=lambda x: x[0])
    if len(pool) < 200:
        return {}
    pdates = np.array([x[0].toordinal() for x in pool])

    # **갈래마다 따로 센다**(노트 670). 합집합(`pool[k][1] & g`)으로 세면
    # *갈래를 하나라도 공유하는* 이전 출시를 세게 되고, 그러면 갈래를 많이
    # 단 작품이 기계적으로 높은 값을 받는다 --- 축이 혼잡도가 아니라
    # **갈래 개수**를 잰다. 갈래 개수는 그 작품의 **상수**이므로 창을 12배
    # 바꿔도 안 변하고, 노트 651 이 관측한 '창 불변 · 자기상관 0.87~0.91' 이
    # 정확히 그 지문이다.
    #
    # 대장 노트 650 에는 이 고침이 **적혀 있었는데 코드에는 없었다**(git 전
    # 이력에 `cumsum` 0회). '장부와 코드가 따로 자란다' 세 번째 자리다.
    #
    # 누적합으로 갈래당 O(1) --- `cum[g][i]` 는 pool 앞 i 개 중 갈래 g 의 수.
    cum: dict = {}
    for gname in {x for _d, gs in pool for x in gs}:
        c = np.zeros(len(pool) + 1, np.int32)
        for i, (_d, gs) in enumerate(pool):
            c[i + 1] = c[i] + (1 if gname in gs else 0)
        cum[gname] = c

    out, rep = {}, {}
    for dom, (ds, gs) in rows.items():
        if DOMS is not None and dom not in DOMS:
            rep[dom] = {"행": len(ds), "덮음": 0.0, "빠짐": "DOMS 밖"}
            continue
        n = len(ds)
        col = np.full(n, np.nan)
        for i, (d, g) in enumerate(zip(ds, gs)):
            if d is None or not g:
                continue
            hi = d.toordinal()
            lo = hi - WIN
            # **직전 창만.** 당일과 이후는 안 본다
            j0, j1 = np.searchsorted(pdates, lo), np.searchsorted(pdates, hi)
            tot = j1 - j0
            if tot < MIN_TOT:
                continue
            # 갈래 **각각**의 몫을 구해 평균한다 --- 갈래 수에 불변이다
            shares = [(cum[x][j1] - cum[x][j0]) / tot for x in g if x in cum]
            if not shares:
                continue
            col[i] = float(np.mean(shares))
        ok = np.isfinite(col)
        if ok.sum() >= 30 and len(np.unique(col[ok])) >= 3:
            out[dom] = (_pct(col, ok), ok.astype(np.float32))
        rep[dom] = {"행": n, "덮음": round(float(ok.mean()), 3) if n else 0.0}
    res = {"crowd_share": out} if out else {}
    if report:
        print(json.dumps({"풀": len(pool), "도메인별": rep,
                          "축": list(res)}, ensure_ascii=False, indent=1), flush=True)
    return res


if __name__ == "__main__":
    build(report=True)
