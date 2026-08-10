"""노트 680 — **제목 텍스트만으로 판의 얼마를 맞히나.** GBDT 를 안 돌린다.

문자 n-gram TF-IDF → 능형회귀. **학습 구간에서만 적합하고 유보에서 채점**한다.
도메인을 섞지 않는다(제목 길이·언어가 도메인 지시자가 되는 것을 막는다 · 사각 ①).
"""
import json
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge

from ingest.news_counts import SRC

S = Path("data/state")

#: 판 ρ **정본** --- 12도메인 · 유보 3,775 · 씨앗 0~11(노트 837 재기선 · `docs/용어.md`).
#: 🔴 이 자리는 **판정이지 기록이 아니다.** 아래 `비` 는 이 러너를 돌릴 때마다 오늘
#: 자료로 새로 계산되므로, 나누는 수도 **오늘의 정본**이어야 짝이 맞는다(조항 60 ---
#: 두 수를 이어 붙일 때 분모가 같은지 본다. 분자는 12도메인 유보에서 나온다).
#: 노트 680 이 인쇄한 「챔피언 판 0.4689」와 그 비(0.51)는 **11도메인 시대의 값이고
#: 837 재기선으로 은퇴했다** --- 그 기록은 노트 680 · 논문 132 · 원장에 남아 있고
#: 여기서 되살리지 않는다(옛 분모로 나눈 비는 오늘 분자와 분모가 다르다).
#:
#: 🔴 **이슈 #112(티처 #59 C1) 로 값이 바뀌었다 --- 0.4710 → 0.46982.** #109 수리가
#: 은퇴한 0.4689 를 여기 0.4710 으로 갈아 끼웠는데, **0.4710 은 챔피언 경로로는 안 나오는
#: 숫자였다**(837 경로로는 오늘도 재현된다 --- 0.4709970 ± 0.0021019). 0.4710 은 지금
#: 판이 쓰지 않는 **두 옛 규약**의 값이다: ① 채점 배치 = post ∩ 라벨(노트 855 가 규약을
#: **post 전체**로 바꿨다 · 씨앗0 +0.00071993) ② **스피어만 구현** --- 837 은
#: `scipy.stats.spearmanr`(동률 **평균**), 챔피언은 `state/rank_test.py:44` 의
#: `np.argsort(np.argsort(v))`(**서수** --- 동률을 배열 순서로 깬다 · 씨앗0 +0.00061958).
#: 🔴 옛 원인 ②("`_fit_on` 이 GBM `random_state` 를 씨앗으로 갈아 끼운다")는 **틀렸다** ---
#: `lab/forms.py:702-703` 이 자루마다 `random_state` 를 자루 색인으로 덮으므로
#: `kw['random_state']` 는 GBM 에 안 닿는다(이슈 #117 · 티처 #60 C1 · 노트 898 실측).
#:
#: 🔴 **이슈 #117(티처 #60 C2 · 노트 898) 로 값이 또 바뀌었다 --- 0.46982 → 0.47034.**
#: 그 「원인 ②」가 **오늘의 정본 자신의 결함**이기도 했기 때문이다. `state/rank_test.py`
#: 의 순위 함수를 **서수 → 동률 평균**으로 통일했다. 이유는 크기가 아니라 원칙이다:
#:   · 서수는 동률을 **배열 순서**로 깨서 판 ρ 가 **자료 정렬에 의존**했다
#:     (실측: 행을 20번 섞으면 **12/12 도메인**에서 ρ 가 갈리고 최대 폭 **0.1562**)
#:   · 자(`ruler890.sp` · `thresh891`)는 처음부터 동률 평균이었다 --- **판과 자가
#:     다른 스피어만을 쓰고 있었다**
#: 12씨앗 짝 Δ **+0.00051922 ± 0.00003993(SE)** · BCa [+0.00044404, +0.00059359] ·
#: **12/12 양수** · 채택 문턱 0.00353 의 **0.147배**. 움직인 것은 사실상 한 도메인이다
#: (시장팝업 Δ +0.01530 → 판 기여 +0.000511 = 전체의 **98.4%**).
#: ⚠ **개선 주장이 아니다** --- 서수는 동률에서 순위를 무작위로 갈라 상관을 아래로 끄는
#: 편의가 있었고, 그 편의를 뺀 것이다. 손잡이를 돌린 것이 아니라 **통계량의 정의**다.
#:
#: 아래 값은 **오늘 챔피언 경로로 직접 잰 것**이다(2026-08-10 · 씨앗 0~11 · 유보 3,775):
#:   재현: `python3 -m runners.rerun112` → `runners/out112_board.json`
#:         (측정 산출물은 `runners/out898_board.json` · 판정은 `out898_verdict.json`)
#:   0.47034252170476804 · 씨앗 SD 0.0020895 · SE 0.00060319
#:   씨앗 0 단독은 0.4731063028988083.
#: 🔴 **이력(서수 시대 · 판정에 쓰지 마라)**: 0.4698232980146997 · SD 0.0020371 ·
#:   SE 0.00058806 · 씨앗 0 단독 0.4724867181663707.
BOARD_RHO = 0.47034


def data():
    from lab import loop as L
    e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
         **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
    return L._idol(lambda: e, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def titles(dom):
    """레코드 id → 제목. `_ids()` 순서에 맞춰 리스트로."""
    from lab.trendaxes import _ids
    f, fld = SRC.get(dom, (None, None))
    if not f or not (S / f).exists():
        return None
    recs = json.loads((S / f).read_text())
    ids = _ids().get(dom) or []
    if isinstance(recs, dict):
        return [str((recs.get(k) or {}).get(fld) or "") for k in ids]
    return None


d = data()
out, rep = {}, {}
num = den = 0.0
for dom in d.dom:
    ts = titles(dom)
    if ts is None:
        rep[dom] = "제목 원천 없음"
        continue
    y = d.dom[dom][2]
    yr = d.yr[dom]
    n = min(len(ts), len(y), len(yr))
    ts, y, yr = ts[:n], y[:n], yr[:n]
    has = np.array([len(t.strip()) >= 2 for t in ts])
    tr = has & np.isfinite(y) & np.isfinite(yr) & (yr < 2025.0)
    te = has & np.isfinite(y) & np.isfinite(yr) & (yr >= 2025.0)
    if tr.sum() < 100 or te.sum() < 20:
        rep[dom] = f"행부족 학습{int(tr.sum())}/유보{int(te.sum())}"
        continue
    V = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4),
                        min_df=3, max_features=40000, sublinear_tf=True)
    Xtr = V.fit_transform([ts[i] for i in np.flatnonzero(tr)])
    Xte = V.transform([ts[i] for i in np.flatnonzero(te)])
    ytr = y[tr]
    # 라벨을 도메인 안 순위로 (스피어만 판정과 맞춘다)
    from scipy.stats import rankdata
    r = rankdata(ytr) / len(ytr)
    m = Ridge(alpha=1.0).fit(Xtr, r)
    p = m.predict(Xte)
    rho = float(spearmanr(p, y[te]).statistic)
    if not np.isfinite(rho):
        rep[dom] = "rho NaN"
        continue
    w = int(te.sum())
    out[dom] = {"rho": round(rho, 4), "학습": int(tr.sum()), "유보": w,
                "어휘": Xtr.shape[1]}
    num += rho * w; den += w
    rep[dom] = "ok"

print(json.dumps({"도메인별": out, "빠짐": {k: v for k, v in rep.items() if v != "ok"},
                  "**텍스트만 판 rho**": round(num / den, 4) if den else None,
                  "채점 유보 합": int(den),
                  "챔피언 판(정본 · 12도메인 · 유보 3,775 · 씨앗 0~11 · 이슈 #112 재측정)":
                      BOARD_RHO,
                  "정본 재현 명령": "python3 -m runners.rerun112",
                  "비": round((num / den) / BOARD_RHO, 3) if den else None},
                 ensure_ascii=False, indent=1), flush=True)

# 판정이 양성이면 상위 n-gram 을 눈으로 (사각 ②)
if den and (num / den) >= 0.10:
    print("\n상위 n-gram — 사후 정보인지 눈으로 본다:", flush=True)
    for dom in list(out)[:4]:
        ts = titles(dom)
        y = d.dom[dom][2]; yr = d.yr[dom]
        n = min(len(ts), len(y), len(yr)); ts, y, yr = ts[:n], y[:n], yr[:n]
        has = np.array([len(t.strip()) >= 2 for t in ts])
        tr = has & np.isfinite(y) & np.isfinite(yr) & (yr < 2025.0)
        V = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3,
                            max_features=40000, sublinear_tf=True)
        X = V.fit_transform([ts[i] for i in np.flatnonzero(tr)])
        from scipy.stats import rankdata
        m = Ridge(alpha=1.0).fit(X, rankdata(y[tr]) / tr.sum())
        nm = np.array(V.get_feature_names_out())
        o = np.argsort(m.coef_)
        print(f"  {dom} 상위+: {list(nm[o[-12:]][::-1])}")
        print(f"  {dom} 상위-: {list(nm[o[:8]])}")
