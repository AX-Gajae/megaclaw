"""제목 텍스트를 **열 하나**로 만든다(노트 681).

노트 680 이 제목만으로 판 rho **0.2399**(챔피언 0.4689 의 51%)를 쟀다. 그러면
남는 물음은 *"텍스트가 챔피언 축 **위에** 무엇을 더하나"* 이고, 그것은 텍스트
예보를 열 하나로 넣어 재야 안다.

**누출을 막는 것이 이 모듈의 전부다.** 텍스트 모형은 라벨을 보고 적합되므로
그 예보를 그대로 학습 행에 넣으면 *자기 라벨을 본 열*이 된다. 그래서 겹쳐
쌓기 규율을 지킨다:

    학습 행   K겹(기본 5)으로 --- 4겹으로 적합해 남은 1겹을 예측한다
    유보 행   학습 **전체**로 적합한 모형으로 예측한다

그리고 **도메인 안에서만** 적합·예측하고 **도메인 내 백분위**로 넣는다. 도메인을
섞으면 제목 길이·언어가 도메인 지시자가 되고(노트 646), 성적이 도메인마다
크게 달라(애니 0.491 대 만화 0.059) 원값으로는 눈금이 공유되지 않는다.
"""
from __future__ import annotations

import json

import numpy as np

AX = "text_fit"
FOLDS = 5
NG = (2, 4)
MIN_TRAIN = 100
MIN_LEN = 2


def _pct(v: np.ndarray, ok: np.ndarray) -> np.ndarray:
    """관측된 값만으로 백분위. 동률은 평균 순위로(노트 292)."""
    from scipy.stats import rankdata
    out = np.zeros(len(v), np.float32)
    if ok.sum() < 3:
        return out
    r = rankdata(v[ok]) - 1.0
    out[ok] = (r / max(ok.sum() - 1, 1)).astype(np.float32)
    return out


def build(data, T: float = 2025.0, folds: int = FOLDS,
          report: bool = False) -> dict:
    """{"text_fit": {도메인: (백분위값, 표시자)}}.

    `data` 를 받는다 --- 라벨과 연도를 그 판에서 그대로 읽어야 자가 같다.
    """
    from scipy.stats import rankdata
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import Ridge
    from ingest.news_counts import titles

    out, rep = {}, {}
    for dom in data.dom:
        ts = titles(dom)
        if ts is None:
            rep[dom] = "제목 원천 없음"
            continue
        y, yr = data.dom[dom][2], data.yr[dom]
        n = min(len(ts), len(y), len(yr))
        ts = list(ts[:n])
        y, yr = y[:n], yr[:n]
        has = np.array([len(t.strip()) >= MIN_LEN for t in ts])
        tr = has & np.isfinite(y) & np.isfinite(yr) & (yr < T)
        te = has & np.isfinite(yr) & (yr >= T)          # 유보는 라벨을 안 본다
        if tr.sum() < MIN_TRAIN:
            rep[dom] = f"학습부족({int(tr.sum())})"
            continue
        col = np.full(len(y), np.nan)
        itr = np.flatnonzero(tr)
        rk = rankdata(y[tr]) / tr.sum()

        def fit_predict(fit_idx, pred_idx, fit_rank):
            V = TfidfVectorizer(analyzer="char_wb", ngram_range=NG, min_df=3,
                                max_features=40000, sublinear_tf=True)
            X = V.fit_transform([ts[i] for i in fit_idx])
            m = Ridge(alpha=1.0).fit(X, fit_rank)
            return m.predict(V.transform([ts[i] for i in pred_idx]))

        # ① 학습 행 --- K겹 겹쳐 쌓기
        rng = np.random.default_rng(681)
        order = rng.permutation(len(itr))
        for f in range(folds):
            hold = order[f::folds]
            keep = np.setdiff1d(order, hold, assume_unique=False)
            if len(keep) < 20 or len(hold) == 0:
                continue
            col[itr[hold]] = fit_predict(itr[keep], itr[hold], rk[keep])
        # ② 유보 행 --- 학습 전체로
        ite = np.flatnonzero(te)
        if len(ite):
            col[ite] = fit_predict(itr, ite, rk)
        ok = np.isfinite(col)
        if ok.sum() < 30 or len(np.unique(col[ok])) < 3:
            rep[dom] = f"열부족({int(ok.sum())})"
            continue
        out[dom] = (_pct(col, ok), ok.astype(np.float32))
        # 사각 ① --- 학습/유보 예보 분포를 같이 찍는다
        rep[dom] = {"학습": int(tr.sum()), "유보": int(te.sum()),
                    "학습예보 평균": round(float(np.nanmean(col[tr])), 4),
                    "유보예보 평균": round(float(np.nanmean(col[ite])), 4)
                    if len(ite) else None,
                    "학습예보 SD": round(float(np.nanstd(col[tr])), 4),
                    "유보예보 SD": round(float(np.nanstd(col[ite])), 4)
                    if len(ite) else None}
    res = {AX: out} if out else {}
    if report:
        # **`flush` 를 빼면 안 된다**(노트 686). stdout 을 파일로 돌리면
        # 블록 버퍼(8KB)에 갇혀 **몇 십 분 동안 안 보인다** --- 경고는
        # stderr 라 바로 보이므로 *'축 만들기가 아직 도는 중'* 으로 오독한다.
        print(json.dumps({"축": list(res), "도메인별": rep},
                         ensure_ascii=False, indent=1), flush=True)
    return res


# ── 685a --- **공유 인코더** (도메인 토큰 없음) ─────────────────
#
# 노트 685 가 사용자 제안('공유 인코더 + 도메인별 토큰')을 두 단계로 갈랐다.
# 여기는 **첫 단계**다: 도메인 토큰을 안 넣고 **어휘와 가중을 공유**한다.
#
# **왜 토큰을 안 넣나.** 선형에서 도메인 원핫은 **도메인별 절편**만 움직이고,
# 목표가 **도메인 내 순위**라 순위는 상수 이동에 불변이다 --- 즉 원핫이 예측을
# 하나도 안 바꾼다. 토큰이 일하려면 텍스트 가중을 도메인이 **조절**해야 하고
# 선형에서 그것은 `특성 ⊗ 도메인` 이며 그러면 다시 도메인별 모형이다. 그래서
# **학습된 도메인 토큰은 비선형을 요구하고**(685b) 여기서는 *공유 자체* 만 잰다.
#
# **이 팔이 겨누는 것은 행 부족이다.** 노트 681 에서 팝업(학습 17) · 아이돌(56) ·
# 도서(80)가 `MIN_TRAIN=100` 에 걸려 축을 못 받았다. 공유하면 그 셋이 **다른
# 도메인의 가중에 얹혀** 예보를 받는다 --- 그것이 '파운데이션' 의 최소 형태다.

#: 공유 팔에서 축을 받으려면 그 도메인에 **관측이 이만큼**은 있어야 한다.
#: 도메인 내 백분위를 만들 수 있어야 하므로 학습 행이 아니라 **관측 행** 기준이다.
MIN_OBS_SHARED = 30


def build_shared(data, T: float = 2025.0, folds: int = FOLDS,
                 report: bool = False) -> dict:
    """{"text_fit": {도메인: (백분위값, 표시자)}} --- **한 어휘 · 한 가중.**

    ``build`` 와 **같은 벡터화 모수 · 같은 겹 씨앗**을 쓴다. 바뀌는 것은
    *적합을 도메인 안에서 하나 밖에서 하나* 뿐이라야 견줄 수 있다(노트 579·580).

    목표는 **도메인 내 라벨 순위**다 --- 라벨 눈금이 도메인마다 다르므로
    (서재 등록 수 · 평가 수 · 초동) 원값을 한 통에 넣으면 도메인 지시자를
    배운다(노트 646).
    """
    from scipy.stats import rankdata
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import Ridge
    from ingest.news_counts import titles

    # ① 전 도메인 행을 한 통에 --- 도메인 이름을 같이 들고 다닌다
    txt, dom_of, y_all, is_tr, is_te, idx_in_dom = [], [], [], [], [], []
    per_dom = {}
    for dom in data.dom:
        ts = titles(dom)
        if ts is None:
            per_dom[dom] = "제목 원천 없음"
            continue
        y, yr = data.dom[dom][2], data.yr[dom]
        n = min(len(ts), len(y), len(yr))
        per_dom[dom] = {"행": n}
        for i in range(n):
            t0 = str(ts[i]).strip()
            if len(t0) < MIN_LEN or not np.isfinite(yr[i]):
                continue
            tr = bool(np.isfinite(y[i]) and yr[i] < T)
            te = bool(yr[i] >= T)
            if not (tr or te):
                continue
            txt.append(t0); dom_of.append(dom); y_all.append(y[i])
            is_tr.append(tr); is_te.append(te); idx_in_dom.append(i)
    dom_of = np.array(dom_of); y_all = np.array(y_all, float)
    is_tr = np.array(is_tr); is_te = np.array(is_te)
    idx_in_dom = np.array(idx_in_dom)
    if is_tr.sum() < MIN_TRAIN:
        return {}

    # ② 목표는 **도메인 안 순위** --- 눈금을 도메인이 안 나르게 한다
    rk = np.full(len(y_all), np.nan)
    for dom in set(dom_of[is_tr]):
        m = is_tr & (dom_of == dom)
        if m.sum() >= 2:
            rk[m] = rankdata(y_all[m]) / m.sum()
    fitable = is_tr & np.isfinite(rk)

    def fit_predict(fit_m, pred_m):
        V = TfidfVectorizer(analyzer="char_wb", ngram_range=NG, min_df=3,
                            max_features=40000, sublinear_tf=True)
        X = V.fit_transform([txt[i] for i in np.flatnonzero(fit_m)])
        m = Ridge(alpha=1.0).fit(X, rk[fit_m])
        return m.predict(V.transform([txt[i] for i in np.flatnonzero(pred_m)]))

    pred = np.full(len(y_all), np.nan)
    # ③ 학습 행은 **한 통 안에서** K겹 --- 다른 도메인이 든 겹으로 적합된다
    itr = np.flatnonzero(fitable)
    rng = np.random.default_rng(681)          # `build` 와 같은 씨앗
    order = rng.permutation(len(itr))
    for f in range(folds):
        hold = itr[order[f::folds]]
        keep = np.setdiff1d(itr, hold)
        if len(keep) < 20 or len(hold) == 0:
            continue
        km = np.zeros(len(y_all), bool); km[keep] = True
        hm = np.zeros(len(y_all), bool); hm[hold] = True
        pred[hold] = fit_predict(km, hm)
    # ④ 유보 행은 학습 **전체**로
    ite = np.flatnonzero(is_te)
    if len(ite):
        hm = np.zeros(len(y_all), bool); hm[ite] = True
        pred[ite] = fit_predict(fitable, hm)

    # ⑤ 도메인 안 백분위로 되돌린다
    out = {}
    for dom in data.dom:
        n_rows = len(data.dom[dom][2])
        col = np.full(n_rows, np.nan)
        m = dom_of == dom
        col[idx_in_dom[m]] = pred[m]
        ok = np.isfinite(col)
        if ok.sum() < MIN_OBS_SHARED or len(np.unique(col[ok])) < 3:
            if isinstance(per_dom.get(dom), dict):
                per_dom[dom]["빠짐"] = f"관측 {int(ok.sum())}"
            continue
        out[dom] = (_pct(col, ok), ok.astype(np.float32))
        if isinstance(per_dom.get(dom), dict):
            per_dom[dom].update({
                "관측": int(ok.sum()),
                "예보 평균": round(float(np.nanmean(col[ok])), 4),
                "예보 SD": round(float(np.nanstd(col[ok])), 4)})
    res = {AX: out} if out else {}
    if report:
        print(json.dumps({"축": list(res), "붙은 도메인": sorted(out),
                          "한 통 학습": int(fitable.sum()),
                          "한 통 유보": int(is_te.sum()),
                          "도메인별": per_dom}, ensure_ascii=False,
                         indent=1), flush=True)
    return res


# ── 699 --- **집 밖 짝으로 옮겨가나** (L2 전이) ────────────────────
#
# `build` 는 판 도메인(`data.dom`)만 돈다. 짝 행은 판에 없으므로 그대로 쓰면
# `pairs.to_arrays` 가 그 열을 **0.5 · 마스크 0 으로 조용히 중립화**한다
# (노트 359 · 326) --- 그러면 '효과 없음' 이 신호 없음인지 배선 끊김인지
# 못 갈린다. 그래서 **임의의 제목 목록에 직접 예측하는 자**를 둔다.
#
# 규율은 `build` 와 같다: 원천 도메인의 **학습 구간만** 보고 적합하고
# (노트 645), 넣을 때는 **그 집합 안 백분위**로 넣는다(판 열이 도메인 안
# 백분위인 것과 같은 꼴이라 눈금이 견줄 수 있다).

def predict_titles(data, dom: str, titles_out: list, T: float = 2025.0) -> dict:
    """원천 도메인 `dom` 학습 행으로 적합해 `titles_out` 을 예측한다.

    돌려주는 것:
        값     그 집합 안 백분위(0~1) · 예측 못 한 자리는 0.5
        마스크  1 = 제목이 있고 예측이 유한하다
        겹침    **예측의 기제를 재는 자** --- 학습 어휘가 짝 제목을 얼마나 보나
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import Ridge
    from scipy.stats import rankdata
    from ingest.news_counts import titles as src_titles

    ts = src_titles(dom)
    if ts is None:
        return {"오류": f"{dom} 제목 원천 없음"}
    y, yr = data.dom[dom][2], data.yr[dom]
    n = min(len(ts), len(y), len(yr))
    ts, y, yr = list(ts[:n]), y[:n], yr[:n]
    has = np.array([len(str(t).strip()) >= MIN_LEN for t in ts])
    tr = has & np.isfinite(y) & np.isfinite(yr) & (yr < T)
    if tr.sum() < MIN_TRAIN:
        return {"오류": f"{dom} 학습부족({int(tr.sum())})"}
    itr = np.flatnonzero(tr)
    V = TfidfVectorizer(analyzer="char_wb", ngram_range=NG, min_df=3,
                        max_features=40000, sublinear_tf=True)
    X = V.fit_transform([ts[i] for i in itr])
    m = Ridge(alpha=1.0).fit(X, rankdata(y[tr]) / tr.sum())

    out_ts = [str(t or "").strip() for t in titles_out]
    ok = np.array([len(t) >= MIN_LEN for t in out_ts])
    col = np.full(len(out_ts), np.nan)
    if ok.sum():
        Z = V.transform([t for t, k in zip(out_ts, ok) if k])
        col[ok] = m.predict(Z)
        # **어휘 겹침** --- 짝 제목의 n-gram 중 학습 어휘에 있는 몫.
        # 이것이 0 에 가까우면 `Z` 가 거의 영행렬이고 예측이 상수에 붙는다.
        nz = np.asarray((Z != 0).sum(axis=1)).ravel()
        seen = float((nz > 0).mean())
        dens = float(np.median(nz))
    else:
        seen = dens = 0.0
    fin = np.isfinite(col)
    val = np.full(len(out_ts), 0.5, np.float32)
    if fin.sum() >= 3:
        val[fin] = _pct(col, fin)[fin]
    return {"값": val, "마스크": fin.astype(np.float32),
            "겹침": {"학습 행": int(tr.sum()), "학습 어휘": int(len(V.vocabulary_)),
                   "짝 제목 있음": int(ok.sum()), "짝 예측 유한": int(fin.sum()),
                   "**어휘가 닿은 제목 몫**": round(seen, 4),
                   "제목당 닿은 n-gram 중앙": dens,
                   "예측 SD": round(float(np.nanstd(col)), 5) if fin.sum() else None}}
