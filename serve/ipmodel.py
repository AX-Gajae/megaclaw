"""IP 2차 전이 모형 --- **2단**(선별 → 조건부). 노트 692 가 형태를 정했다.

    ① 선별   이 만화가 애니로 만들어지나            7,982행 · 양성 564
    ② 조건부  만들어졌다면 애니 인기가 어디쯤인가     564행

**왜 2단인가.** 각색된 만화는 안 된 만화보다 인기 중앙이 **1.433 자리(27배)**
높다(노트 692). 조건부만 내면 27배 선별을 통과한 집단 안의 순위를 전체인 양
말하게 된다. 선별을 **모형으로** 다뤄야 그 편의가 답 안에 들어온다.

**가장 큰 함정은 시간이다 --- 그리고 우리는 발표일이 없다.**
`y_popularity` 는 *오늘* 값이다. 각색된 만화의 오늘 인기에는 **애니가 만든
몫**이 들어 있다. 그것을 선별 특징으로 쓰면 미래를 보고 과거를 맞히는 것이다.
발표일이 자료에 없으므로 시간 컷오프로 못 막는다. 그래서 **막는 방법을 바꾼다**:

    배급 팔      --- 시작연도 · 갈래수 · 태그수 · 작가수 · 국가 · 형태
    오염 자 팔    --- 위 + 화수 · 권수 · 완결 · **인기 · 즐겨찾기 · 점수**

**두 팔의 차이가 곧 오염의 크기다.** 배급하는 것은 배급 팔뿐이고, 오염 자 팔은
크기를 재는 데만 쓴다. 이것이 팝업 basis leakage 를 잡았던 것과 같은 자리다.
쟀더니 **오염 크기 0.0314**(AUC 0.9408 → 0.9722)이고, 절단 비용도 쟀다 ---
`SAFE_COLS` 주석에 네 팔의 AUC 가 있다. **시작연도만 쓰면 0.5000 이라
시간은 전혀 안 샌다.**

**한계를 미리 적는다.**
· 각색 짝은 **제목 정규화 조인**으로 우리가 만든 것이다(564건). 원 자료에
  각색 연결 필드가 없다 --- `manga_links` 는 스트리밍 링크다.
· 표본은 AniList 등재분이라 **시장 전수가 아니다**. 등재 자체가 선별이다.
· 화수 · 권수 · 완결은 **오늘** 값이라 배급 팔에서 뺐다(비용 1.2%p).
· 표본 시간 분할은 **만화 시작연도 2018** 이다. 각색 *발표일* 이 아니다 ---
  발표일이 자료에 없다. 그래서 "발표 전 정보만 썼다" 고 주장할 수 없고,
  대신 "발표로 안 움직이는 특징만 썼다" 고 주장한다. **다른 주장이다.**
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np

D = Path("data/state")
T_SPLIT = 2018          # 만화 시작연도 --- 이 해부터가 유보
MIN_POS = 30            # 유보 양성이 이만큼은 있어야 AUC 를 낸다
BOOT = 400              # 부트스트랩 --- 문턱은 배율 어림으로 안 낸다(노트 683)

#: 만화 레코드에서 뽑는 특징 전부 --- 순서가 `feats` 와 같아야 한다.
ALL = ("시작연도", "화수", "권수", "갈래수", "태그수", "작가수",
       "완결", "국가JP", "국가KR", "형태MANGA")
#: 오염을 재기 위한 특징 --- **배급 안 한다.**
DIRTY = ("인기", "즐겨찾기", "점수")

#: **배급하는 특징.** `화수 · 권수 · 완결` 을 뺐다 --- 셋이 *오늘* 값이라
#: 각색된 작품이 길게 연재된 몫을 나른다. 뺀 비용을 쟀다:
#:
#:     전부              AUC 0.9524
#:     화수·권수·완결 뺌   AUC 0.9408   ← **배급하는 팔**
#:     시작연도만         AUC 0.5000   ← 시간이 전혀 안 샌다
#:     화수·권수만        AUC 0.7966   ← 혼자서는 세지만 남은 것과 겹친다
#:
#: **1.2%p 를 내고 오늘 값 셋을 다 버린다.** 남는 신호는 갈래 · 태그 · 작가수 ·
#: 국가로, 넷 다 연재 시작 때 정해지는 것이다. 배급물에서 시간 논쟁을
#: 아예 없애는 값이 1.2%p 보다 크다.
SAFE_COLS = (0, 3, 4, 5, 7, 8, 9)
SAFE = tuple(ALL[i] for i in SAFE_COLS)


def _norm(s) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"[^0-9a-z぀-ヿ一-鿿가-힯]+", "", s)


def _load(f: str) -> list:
    j = json.loads((D / f).read_text())
    return list(j.values()) if isinstance(j, dict) else j


def pairs() -> tuple:
    """(만화 전체, 각색된 제목 집합, 각색 짝) --- 조인은 여기 한 군데서만 한다."""
    mg, wa = _load("manga_records.json"), _load("wanime_records.json")
    idx = {}
    for r in mg:
        n = _norm(r.get("title"))
        if n:
            idx.setdefault(n, r)
    ad, pr = set(), []
    for a in wa:
        if str(a.get("source", "")).upper() != "MANGA":
            continue
        n = _norm(a.get("title"))
        m = idx.get(n)
        if m is not None:
            ad.add(n)
            pr.append((m, a))
    return mg, ad, pr


def feats(r: dict, dirty: bool = False) -> tuple:
    """만화 레코드 → (특징 벡터, 시작연도)."""
    sd = str(r.get("start_date") or "")
    yr = float(sd[:4]) if len(sd) >= 4 and sd[:4].isdigit() else np.nan
    v = [yr,
         np.log10(max(float(r.get("n_chapter") or 0), 1.0)),
         np.log10(max(float(r.get("n_volume") or 0), 1.0)),
         float(r.get("n_genre") or 0),
         float(r.get("n_tag") or 0),
         float(r.get("n_author") or 0),
         1.0 if r.get("status") == "FINISHED" else 0.0,
         1.0 if r.get("country") == "JP" else 0.0,
         1.0 if r.get("country") == "KR" else 0.0,
         1.0 if r.get("format") == "MANGA" else 0.0]
    if dirty:
        v += [np.log10(max(float(r.get("y_popularity") or 0), 1.0)),
              np.log10(max(float(r.get("favourites") or 0), 1.0)),
              float(r.get("mean_score") or 0)]
    return np.array(v, float), yr


def _auc(y: np.ndarray, p: np.ndarray) -> float:
    """순위 AUC --- 동률은 평균 순위로."""
    from scipy.stats import rankdata
    r = rankdata(p)
    n1, n0 = y.sum(), (1 - y).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def _fit_stage1(dirty: bool, seed: int = 0, cols=None) -> dict:
    """선별 모형 한 팔. 시간 분할(만화 시작연도 `T_SPLIT`).

    `cols=None` 이면 **배급 팔**(`SAFE_COLS`). `dirty=True` 는 오염 자다.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier

    mg, ad, _ = pairs()
    X, y, yr = [], [], []
    for r in mg:
        v, t = feats(r, dirty)
        if not np.isfinite(t):
            continue
        X.append(v)
        y.append(1 if _norm(r.get("title")) in ad else 0)
        yr.append(t)
    X, y, yr = np.array(X), np.array(y), np.array(yr)
    # **배급 팔은 오늘 값 셋을 뺀다.** 오염 자(dirty)는 전부 + 인기를 쓴다
    if not dirty:
        X = X[:, list(cols if cols is not None else SAFE_COLS)]
    tr, te = yr < T_SPLIT, yr >= T_SPLIT
    if te.sum() < 50 or y[te].sum() < MIN_POS:
        return {"오류": f"유보 부족 (행 {int(te.sum())} · 양성 {int(y[te].sum())})"}
    m = HistGradientBoostingClassifier(max_iter=200, max_depth=4,
                                       learning_rate=0.06, random_state=seed)
    m.fit(X[tr], y[tr])
    p = m.predict_proba(X[te])[:, 1]
    # **위약** --- 값만 섞는다(노트 335). 관측 무늬는 그대로 둔다
    rng = np.random.default_rng(7 + seed)
    pl = p.copy()
    rng.shuffle(pl)
    # 캘리브레이션 --- 열 칸 묶음의 (평균 예보, 실제 비율)
    q = np.quantile(p, np.linspace(0, 1, 11))
    cal = []
    for i in range(10):
        m_ = (p >= q[i]) & (p <= q[i + 1] if i == 9 else p < q[i + 1])
        if m_.sum() >= 10:
            cal.append([round(float(p[m_].mean()), 4), round(float(y[te][m_].mean()), 4),
                        int(m_.sum())])
    return {"학습": int(tr.sum()), "유보": int(te.sum()), "유보양성": int(y[te].sum()),
            "AUC": round(_auc(y[te], p), 4), "위약AUC": round(_auc(y[te], pl), 4),
            "기저율": round(float(y[te].mean()), 4), "캘리브레이션": cal,
            "특징": list(DIRTY + ALL) if dirty else list(SAFE),
            "_m": m, "_dirty": dirty}


def _fit_stage2(seed: int = 0) -> dict:
    """조건부 전이 --- 각색 짝 안에서 애니 인기 백분위. **만화 라벨을 안 쓴다.**

    쓰면 노트 692 가 잰 +0.6434 를 그대로 되받는 자기충족이 된다. 안전
    특징만으로 애니 인기를 맞히는지 보는 것이 이 단의 물음이다.
    """
    from sklearn.ensemble import HistGradientBoostingRegressor
    from scipy.stats import rankdata, spearmanr

    _, _, pr = pairs()
    X, y, yr = [], [], []
    for m, a in pr:
        v, t = feats(m, dirty=False)
        pop = float(a.get("y_popularity") or 0)
        if not np.isfinite(t) or pop <= 0:
            continue
        X.append(v)
        y.append(np.log10(pop))
        yr.append(t)
    X, y, yr = np.array(X)[:, list(SAFE_COLS)], np.array(y), np.array(yr)
    tr, te = yr < T_SPLIT, yr >= T_SPLIT
    if te.sum() < 20:
        return {"오류": f"유보 부족 ({int(te.sum())})"}
    g = HistGradientBoostingRegressor(max_iter=200, max_depth=3,
                                      learning_rate=0.06, random_state=seed)
    g.fit(X[tr], y[tr])
    p = g.predict(X[te])
    rng = np.random.default_rng(11 + seed)
    pl = p.copy()
    rng.shuffle(pl)
    # 부트스트랩 문턱 --- 배율 어림을 안 쓴다(노트 683)
    bs = []
    for _ in range(BOOT):
        i = rng.integers(0, len(p), len(p))
        if len(np.unique(y[te][i])) > 2:
            bs.append(spearmanr(p[i], y[te][i]).statistic)
    return {"학습": int(tr.sum()), "유보": int(te.sum()),
            "스피어만": round(float(spearmanr(p, y[te]).statistic), 4),
            "위약": round(float(spearmanr(pl, y[te]).statistic), 4),
            "부트2σ": round(float(2 * np.std(bs)), 4) if bs else None,
            "_g": g}


_CACHE: dict = {}


def report(seed: int = 0) -> dict:
    """두 단 + 오염 크기. **배급 전에 이것을 먼저 읽는다.**"""
    if seed in _CACHE:
        return _CACHE[seed]
    s1 = _fit_stage1(False, seed)
    s1d = _fit_stage1(True, seed)
    s2 = _fit_stage2(seed)
    gap = (round(s1d["AUC"] - s1["AUC"], 4)
           if "AUC" in s1 and "AUC" in s1d else None)
    arms = {nm: _fit_stage1(False, seed, cols=c)["AUC"]
            for nm, c in (("오늘값 포함", tuple(range(10))),
                          ("시작연도만", (0,)),
                          ("화수·권수만", (1, 2)))}
    out = {"① 선별 (배급하는 팔 · 오늘 값 셋을 뺌)":
           {k: v for k, v in s1.items() if not k.startswith("_")},
           "① 선별 (인기 넣은 팔 · 배급 안 함)":
           {k: v for k, v in s1d.items() if not k.startswith("_")},
           "**오염 크기** (인기를 넣어 오르는 AUC)": gap,
           "오늘 값 절단 비용 (다른 팔들의 AUC)": arms,
           "② 조건부 전이": {k: v for k, v in s2.items() if not k.startswith("_")},
           "_s1": s1, "_s2": s2}
    _CACHE[seed] = out
    return out


def ask(title: str) -> dict:
    """제목 하나 → 배급되는 답. **절대값을 안 낸다**(노트 691)."""
    from scipy.stats import rankdata
    mg, ad, _ = pairs()
    n = _norm(title)
    rec = next((r for r in mg if _norm(r.get("title")) == n), None)
    if rec is None:
        return {"찾음": False, "말": f"'{title}' 이 우리 만화 명부 {len(mg):,}건에 없다. "
                                    "명부는 AniList 등재분이고 시장 전수가 아니다"}
    rp = report()
    s1, s2 = rp["_s1"], rp["_s2"]
    v, _ = feats(rec, dirty=False)
    v = v[list(SAFE_COLS)].reshape(1, -1)
    p_sel = float(s1["_m"].predict_proba(v)[0, 1])
    yhat = float(s2["_g"].predict(v)[0])
    # 조건부 백분위는 **각색 짝 안에서** --- 전체 안이 아니다
    _, _, pr = pairs()
    pool = np.array([np.log10(max(float(a.get("y_popularity") or 1), 1))
                     for _, a in pr])
    pct = float((pool < yhat).mean())
    # **키를 겹치면 앞의 것이 조용히 덮인다** --- 처음 쓴 판에서 ①의 자가
    # ②의 자로 바뀌어 있었다. 사전 리터럴에서 같은 키를 두 번 쓴 것이고
    # 예외가 안 난다. 노트 133 이 말한 '조용한 대체' 의 파이썬 판이다.
    return {"찾음": True, "제목": rec.get("title"),
            "① 각색될 확률": round(p_sel, 4),
            "① 자": f"유보 AUC {s1['AUC']} (위약 {s1['위약AUC']} · 기저율 {s1['기저율']} · "
                   f"유보 {s1['유보']}행/양성 {s1['유보양성']})",
            "① 단서": f"오염 크기 {rp['**오염 크기** (인기를 넣어 오르는 AUC)']} --- "
                    "오늘 인기를 넣으면 AUC 가 이만큼 오르는데 그것은 애니가 만든 인기다. "
                    "배급하는 팔은 그것을 안 쓴다",
            "② 각색된다면 애니 인기 백분위 (각색 짝 안)": round(pct, 3),
            "② 자": f"유보 스피어만 {s2['스피어만']} (위약 {s2['위약']} · "
                   f"부트2σ {s2['부트2σ']} · 유보 {s2['유보']}행) --- "
                   f"{'문턱을 넘는다' if s2['스피어만'] > (s2['부트2σ'] or 9) else '문턱 미달'}",
            "② 단서": "이 백분위는 **각색된 564건 안에서**의 순위다. 각색 안 된 만화까지 "
                    "넣은 전체 순위가 아니다 --- 그래서 ①을 같이 읽어야 한다",
            "못 내는 것": ["절대 관객수·매출 (노트 691 · 자릿수 오차 42%)",
                        "이름 붙인 구간 (노트 691 · 80% 구간 실측 덮음 50%)",
                        "전향 실적 (기록 0건)"]}


if __name__ == "__main__":
    r = report()
    print(json.dumps({k: v for k, v in r.items() if not k.startswith("_")},
                     ensure_ascii=False, indent=1))
