"""아이돌을 넓힌 판 --- 라벨 기준 필터를 풀되 **풀의 그림자**를 같이 뗀다(노트 326).

``ingest/idol_axes.py`` 가 ``chodong_basis_resolved == "hanteo"`` 로 풀을
정한다. 초동과 데뷔일을 둘 다 가진 173건 중 79건만 남고 94건이 빠진다.

노트 325는 그 필터가 옳다고 적었다 --- 한터 log10 초동 중앙 5.115 대 나머지
4.281 이고 원값으로 일곱 배라, 섞으면 기준이 곧 표지가 된다고 봤다.

**노트 326이 그 절반을 뒤집었다.**

    ① 차 0.835 는 관측 축으로도 출처 종류로도 안 없어진다(0.580 · t=3.65)
    ② 그런데 **채점이 도메인 안 순위**라 수준 이동을 안 느낀다 ---
       원값 그대로 +0.588 · 수준을 맞춰도 +0.538 · 기준별 순위 정규화는
       오히려 +0.428 로 나쁘다(모집단이 다른데 같은 분포로 억지로 맞춘다).
       라벨 섞은 위약은 +0.179 --- 이득의 70%가 진짜 정보다.
    ③ **진짜로 막은 것은 우리 수집 경로다.** 위키 99%->0% · 앨범 메타
       100%->0% · 검색 35%->17%. 한터 풀에만 긁었다. 그래서 위키 표시자가
       한터 여부와 **99.4%** 같고(표시자~라벨 rho=0.363 · p<1e-6) marker 가
       곧장 "볼 것"이다. 노트 306은 바깥 세계가 만든 사후 표시자였고
       이것은 **우리가 만든** 사후 표시자다.
    ④ 그래서 고치는 법이 더하기가 아니라 **빼기**다. 한터에만 있는 축 둘
       (entry_friction · goods_scale --- 둘 다 앨범 메타 파생)을 빼고 94행을
       넣으면 아이돌 유보 순위상관이 0.2199 -> 0.4728 (+0.2413 · 씨앗 20/20).
       그 둘을 지키면 이득이 +0.111 로 반이 된다. **그리고 그 둘은 한터만
       쓸 때도 안 벌고 있었다**(0.2249 대 0.2199).

**유보는 안 건드린다**(노트 82 · 90의 분모 규칙). 추가 94건 중 2025년 이후
26건은 **버린다** --- 학습만 54 -> 122 로 늘린다. 판 분모가 2,675 그대로라
옛 점수와 직접 견줄 수 있다.

모드 둘:

    "cut"   전용 축 둘을 뺀다(노트 326이 잰 것). 기본.
    "keep"  다섯 축을 다 두고 추가행은 마스크 0 --- 표시자가 기준을 나른다.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

REC = Path("data/idol_records")
ALBUM = Path("data/state/idol_album_meta.json")
DOM = "아이돌"
T = 2025.0
# 풀 그림자 축 --- 앨범 메타에서만 나오고 앨범 메타는 한터 풀만 긁혔다
SHADOW = ("entry_friction", "goods_scale")


def _records():
    from ingest.idol_axes import agency_prior
    recs = [json.loads(f.read_text()) for f in sorted(REC.glob("*.json"))]
    return recs, agency_prior(recs)


def build(mode: str = "cut", placebo: int | None = None,
          keep_axes: tuple = (), scramble: int | None = None,
          wide_post: bool = False) -> tuple:
    """(A, M, y, t, names, info). 행 순서는 한터 79 먼저, 그 뒤 추가 68.

    ``placebo`` 는 씨앗이다 --- **추가 68행의 라벨만 섞는다.** 행이 늘어서
    생기는 이득(부스팅이 덜 과적합한다)과 라벨 정보를 가르는 대조다.
    노트 326의 손 실험에서 위약이 이득의 30%를 먹었다(+0.179/+0.588).
    """
    from ingest.idol_axes import AXES, derive
    recs, pri = _records()
    alb = json.loads(ALBUM.read_text()) if ALBUM.exists() else {}
    U = [r for r in recs if r.get("chodong") and r.get("debut_date")]
    han = [r for r in U if r.get("chodong_basis_resolved") == "hanteo"]
    # **추가행은 2025년 이전만.** 유보를 안 늘려야 분모가 안 바뀐다.
    #
    # ``wide_post`` 는 그 규칙을 푼다(노트 353). 노트 352가 아이돌 rho 의
    # 95% 구간을 $[0.052, 0.817]$ --- 폭 0.756 --- 으로 쟀다. 판에서 제일
    # 안 재지는 도메인이고, 유보 25행이 원인이다. 버려 둔 2025년 이후 26행을
    # 넣으면 폭이 $1/\sqrt2$ 로 준다.
    #
    # **모형은 안 바뀐다.** 이 26행은 2025년 이후라 어차피 학습에 안 들어간다
    # --- 켜고 끄는 것으로 달라지는 것은 채점 집합뿐이고 재적합이 없다.
    # 대신 판 분모가 2,675 -> 2,701 로 바뀌므로 옛 판 수와 직접 못 견준다.
    ext = [r for r in U if r.get("chodong_basis_resolved") != "hanteo"
           and (wide_post or float(r["debut_date"][:4]) < T)]
    rows = han + ext
    A, M = [], []
    for r in rows:
        d = derive(r, pri, alb)
        A.append([d["axes"][x] for x in AXES])
        M.append([d["mask"][x] for x in AXES])
    A = np.array(A, float)
    M = np.array(M, float)
    names = list(AXES)
    if mode == "cut":
        # ``keep_axes`` 에 든 것은 살린다(노트 335). 노트 326·334 는 둘을
        # 한 묶음으로 뺐는데, 채택 검사로 보면 둘이 다르다 ---
        # goods_scale 은 검사 ①(rho +0.475 · p<1e-4) ②(시간 조각 5/5)를
        # 통과하고 entry_friction 은 ①(p=0.137) ②(3/5, 최근 조각에서 부호가
        # 뒤집힌다) 를 둘 다 떨어진다. **원천이 같다고 축이 같지 않다.**
        for s in SHADOW:
            if s in keep_axes:
                # **열 자체가 해로운가**(노트 335). 값만 섞으면 열 수와
                # 관측 무늬는 그대로고 정보만 없어진다 --- 유보 25행에서
                # ``열을 하나 더하는 값'' 을 재는 위약이다.
                if scramble is not None:
                    j = names.index(s)
                    ok = M[:, j] > .5
                    idx = np.where(ok)[0]
                    rng = np.random.default_rng(scramble)
                    A[idx, j] = A[idx[rng.permutation(len(idx))], j]
                continue
            M[:, names.index(s)] = 0.0        # 통째로 끈다(표시자도 상수)
    y = np.array([float(np.log10(r["chodong"])) for r in rows])
    t = np.array([float(r["debut_date"][:4]) for r in rows])
    if placebo is not None and ext:
        rng = np.random.default_rng(placebo)
        i = np.arange(len(han), len(rows))
        y[i] = y[i][rng.permutation(len(i))]
    info = {"한터": len(han), "추가": len(ext), "유보": int((t >= T).sum()),
            "학습": int((t < T).sum()), "모드": mode,
            "위약": placebo,
            "뺀 축": [x for x in SHADOW if x not in keep_axes]
                    if mode == "cut" else []}
    return A, M, y, t, names, info


def cal(rows_t=None, mode: str = "cut", wide_post: bool = False) -> dict:
    """넓힌 아이돌 행 순서의 달력 축. ``lab/calaxes`` 와 같은 재료를 쓴다."""
    from ingest.idol_axes import agency_prior  # noqa: F401  (순서 고정용)
    from .calaxes import FEATS, _feat, _parse, _pct
    recs, _ = _records()
    U = [r for r in recs if r.get("chodong") and r.get("debut_date")]
    han = [r for r in U if r.get("chodong_basis_resolved") == "hanteo"]
    ext = [r for r in U if r.get("chodong_basis_resolved") != "hanteo"
           and (wide_post or float(r["debut_date"][:4]) < T)]
    ds = [_parse(r["debut_date"]) for r in han + ext]
    out = {}
    for f in FEATS:
        raw = np.array([_feat(x)[f] if x else np.nan for x in ds], float)
        if np.isfinite(raw).sum() < 20:
            continue
        out[f] = _pct(raw)
    return out


def _rows(mode_wide: bool = True, wide_post: bool = False):
    """넓힌 아이돌의 행 순서(한터 79 먼저, 그 뒤 추가 68)."""
    from ingest.idol_axes import agency_prior  # noqa: F401
    recs, _ = _records()
    U = [r for r in recs if r.get("chodong") and r.get("debut_date")]
    han = [r for r in U if r.get("chodong_basis_resolved") == "hanteo"]
    ext = [r for r in U if r.get("chodong_basis_resolved") != "hanteo"
           and (wide_post or float(r["debut_date"][:4]) < T)]
    return (han + ext) if mode_wide else han


def wiki(zero_is_data: bool = False, part: str = "both",
         wide_post: bool = False) -> dict:
    """넓힌 아이돌 행 순서의 위키 축(노트 332).

    노트 326이 위키가 한터 풀만 긁혀 있다고 잡았고(표시자가 한터 여부와
    99.4% 같았다) 노트 332에서 ``ingest/wiki_views.idol_items`` 를
    **원천 레코드**에서 후보를 만들게 고쳐 173건을 다 긁었다. 그 뒤
    관측률이 한터 54% 대 추가 39% 로 좁혀졌고 ``poolshadow`` 판정이
    ``풀 모양`` 에서 ``괜찮다`` 로 바뀌었다.

    ``zero_is_data=False`` 는 노트 306의 정정이다 --- 빈 창(문서는 있는데
    사전 조회수 0)을 자료로 세면 표시자가 ``긁은 시점에 문서를 찾았나''가
    되어 사후가 된다.
    """
    import numpy as np
    from scipy.stats import rankdata
    from .wikiaxes import FEATS, _read
    rows = _rows(wide_post=wide_post)
    r = _read(0.0, False)
    out = {}
    for f in FEATS:
        raw = np.full(len(rows), np.nan)
        for i, rec in enumerate(rows):
            e = r.get(rec["record_id"])
            if e is None or e[0] is None:
                continue
            if not e[1] and not zero_is_data:
                continue
            raw[i] = e[0][f]
        ok = np.isfinite(raw)
        if ok.sum() < 20:
            continue
        v = np.full(len(raw), 0.5)
        v[ok] = rankdata(raw[ok]) / ok.sum()
        # **값이 버나 표시자가 버나**(노트 332, 노트 133의 규약).
        #   "값만"   표시자를 상수로 만든다 --- 관측 여부가 정보를 못 나른다
        #   "표시자만" 값을 중립으로 만든다 --- 관측 여부만 남는다
        # 노트 306이 위키 표시자가 사후일 수 있다고 했다(2026년에 문서가
        # 남아 있어야 긁힌다). 이득이 표시자에서 오면 같은 덫이다.
        if part == "값만":
            out[f"wiki_{f}"] = (v, np.ones(len(v)))
        elif part == "표시자만":
            out[f"wiki_{f}"] = (np.full(len(v), 0.5), ok.astype(float))
        else:
            out[f"wiki_{f}"] = (v, ok.astype(float))
    return out


def trend(zero_is_data: bool = True, wide_post: bool = False) -> dict:
    """넓힌 아이돌 행 순서의 검색 축(노트 333).

    ``ingest/naver_trend --records --domain idol`` 은 원래부터 원천
    레코드를 읽었다(필터 없음) --- 그런데 44건만 수집돼 있었다. 다 돌리니
    169건이 되고 한터 96% · 추가 99% 로 ``poolshadow`` 판정이 ``괜찮다``다.
    **여기는 그림자가 아니라 그냥 덜 긁힌 것이었다.**
    """
    import numpy as np
    from scipy.stats import rankdata
    from . import trendaxes
    from .trendaxes import FEATS
    rows = _rows(wide_post=wide_post)
    trendaxes._ZERO_IS_DATA = zero_is_data
    out = {}
    for f in FEATS:
        raw = np.array([(trendaxes._state(DOM, r["record_id"]) or {}).get(f, np.nan)
                        for r in rows], float)
        ok = np.isfinite(raw)
        if ok.sum() < 20:
            continue
        v = np.full(len(raw), 0.5)
        v[ok] = rankdata(raw[ok]) / ok.sum()
        out[f"trend_{f}"] = (v, ok.astype(float))
    return out


if __name__ == "__main__":
    t = trend()
    if t:
        print("검색 축", len(t), "· 관측률",
              {k: round(float(v[1].mean()), 3) for k, v in t.items()})
    w = wiki()
    if w:
        import numpy as np
        print("위키 축", len(w), "· 관측률",
              {k: round(float(v[1].mean()), 3) for k, v in w.items()})
    for m in ("cut", "keep"):
        A, M, y, t, nm, info = build(m)
        print(f"[{m}] {info}")
        print(f"  행 {len(A)} · 축 {len(nm)}")
        for i, c in enumerate(nm):
            print(f"    {c:<20} 마스크 {M[:, i].mean():.2f}")
