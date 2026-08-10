# -*- coding: utf-8 -*-
"""노트 896 — **용량-반응: 텍스트를 더 넣으면 판이 오르는가.**

사전등록은 `docs/prereg_896_dose_response.md`(팔 측정 **전에** 커밋됨).

    0단계  분모 세기(조항 60) --- 요청 0 · 적합 0 · **설계를 정한다**
    팔 A   관찰 --- 유보 행별 오차가 용량과 상관되는가 (순열 널 1,000)
    팔 B   개입 --- 용량을 열로 주입 → 판 Δρ vs 문턱 **0.00353**

용량이 **둘**이다(티처 #58 C4 --- 존재와 양을 갈라 재라):

    ㄱ 존재 이진   `data/state/wiki_views/*.json` 의 `page != null` (7도메인)
    ㄴ 양(글자수)  `desc_wanime.json` · `funding_pool.json:shortDescription`

🔴 조항 59 --- **확인된 있음 / 확인된 없음 / 안 두드림**을 절대 안 섞는다.
🔴 티처 #58 M6 --- 산출물마다 `git HEAD` · UTC 시각 · 코드 sha256 을 박는다.
🔴 규약 47 --- 구간은 `lab.pairboot.cluster_boot` **BCa** · 폴백이면 사유를 필드에.
"""
import os

#: 적합은 사실상 단일 코어다(노트 892 실측) --- 스레드를 못박고 프로세스로 병렬한다.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import datetime as dt                                           # noqa: E402
import hashlib                                                  # noqa: E402
import json                                                     # noqa: E402
import multiprocessing as mp                                    # noqa: E402
import subprocess                                               # noqa: E402
import sys                                                      # noqa: E402
import time                                                     # noqa: E402
from pathlib import Path                                        # noqa: E402

import numpy as np                                              # noqa: E402
from scipy.stats import rankdata                                # noqa: E402

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
DS = ROOT / "data/state"
ME = Path(__file__).resolve()

T = 2025.0
#: 🔴 이슈 #113 / 티처 #59 M1 --- **이 6은 문턱 0.00353 과 분모가 다르다.**
#: 문턱은 `thresh891` 이 12씨앗 앙상블 짝으로 만든 자이고 여기는 6씨앗이라
#: 씨앗 성분만 √2 어긋난다. 씨앗 목록의 정본은 이제 `ff753.RULER_SEEDS`(12)이고
#: 12씨앗 재측정은 `runners/dose113.py B` → `runners/out113_armB12.json` 이다.
#: 이 상수는 **노트 896 을 그대로 재현하기 위해** 6으로 남긴다(이력을 안 뭉갠다).
SEEDS = tuple(range(6))                #: = ff753.SEEDS (ff753.RULER_SEEDS[:6])
NULL_DRAWS = (8960, 8961, 8962)        #: 널 팔 뽑기 셋(값만 섞고 마스크 무늬 보존 · 노트 335)
B_BOOT = 10_000
BOOT_SEED = 896
PERM = 1_000                           #: 팔 A 순열 널
THRESH = 0.00353                       #: 정본 채택 문턱(노트 891 · 12도메인 2σ)
JUNK_FLOOR = 0.01055                   #: 1열 잡동사니 잡음 바닥(노트 892) --- 병기용
BASE_OK = (0.455, 0.485)               #: 기준선 게이트(raw780 관례)
#: 🔴 **오늘 챔피언 경로의 씨앗0 판**(`lab.harness.evaluate` + `Data.pooled`).
#: 이 상수의 일은 `stage0` 이 도는 배선이 **정본 경로 그대로인가**를 재는 것이다 ---
#: 그러니 정본이 옮겨가면 **이 상수도 같이 옮겨야 한다**(이슈 #123 · 규칙은 아래).
#:
#: 2026-08-10 · 이슈 #123 · 티처 #61 C7 --- 노트 898 이 판을 자에 맞추면서
#: (`state/rank_test.spearman` 서수 → 동률 평균) 이 상수가 **은퇴했는데 아무도 안
#: 옮겼다.** 그래서 :367 의 판정 게이트가 **영구 False** 였다. 게이트가 죽은 채로
#: `stage0` 이 여섯 번 더 돌아도 아무 소리가 안 났다.
#:   은퇴값(서수 시대) 0.4724867181663707 --- `runners/board898.py` 의 팔 A 가
#:   **옛 구현을 박아서** 지금도 재현한다. 역사에서는 옳고 「오늘」 자리에서만 죽었다.
#: 새 값은 손으로 옮기지 않았다 --- 챔피언 경로를 실제로 돌려서 읽었다
#: (`runners/out899a_gates.json` 의 `오늘 챔피언 경로 씨앗0`).
EXPECT_POOLED_K1_S0 = 0.4731063028988084   #: 노트 898 정본 경로(동률 평균) 씨앗0

#: 🔴 **은퇴한 씨앗0 값**(노트 898 · 이슈 #123). 딱지를 숫자 바로 뒤 괄호에 붙인다 ---
#: 수리 B 가 세운 `_mark_owner` 규칙이 그 꼴만 「그 숫자의 딱지」로 읽는다.
SEED0_RETIRED = 0.4724867181663707  # 0.4724867181663707(은퇴 · 「서수 순위 시대 값」 · 노트 898)

#: 🔴 **규칙(이슈 #123 --- 이 규칙이 없어서 위 게이트가 조용히 죽었다)**
#:
#:   **정본(채점 함수·채점 배치·적합 경로)이 옮겨가면 씨앗0 상수도 같이 옮긴다.**
#:   옛 값을 계속 재야 하는 러너는 **옛 구현을 파일 안에 박는다**(반입 금지 ---
#:   `runners/thr898.py:41-43` · `runners/board898.py`). 두 길뿐이고, 아무것도
#:   안 하는 셋째 길이 「영구 False 게이트」다.
#:
#: 기계 확인: `python3 runners/out899a_gates.py` (씨앗0 상수를 이고 있는 자리를
#: 전수로 훑고, 오늘 챔피언 경로를 **실제로 돌려서** 대조한다).

#: 🔴 895 산출물에서 **읽은** 값의 복사본. 다른 에이전트가 지금 895 를 고치고 있어
#: 중간에 바뀔 수 있으므로 여기 박아 둔다(사용자 지시).
COPY_895 = {
    "읽은 때(UTC)": "2026-08-10T08:55 (0단계) · 09:2x 재확인(BCa 정정 뒤)",
    "정답지 실물": 200, "음성": 20,
    "R1 네이버 news B 스피어만": 0.6808,
    "R3a 나무위키 바이트 B": 0.5291, "R3a 존재 이진 B(티처 #58 C4)": 0.5365,
    "R2 베이스모델 B": 0.1126,
    "🔴 895 BCa 정정(커밋 e49b517c · 이슈 #105)": {
        "한글 실물 58 정답지 AUC 하한": {"옛 percentile": 0.7211, "정본 BCa": 0.6880},
        "🔴 뜻": "정정된 하한 0.6880 이 895 가 **자에게** 요구하는 A 문턱 0.70 보다 낮다 ---"
               " 자에게 들이대는 잣대를 정답지 자신에게 대면 이제 못 넘는다."
               " 896 은 이것을 알고 열렸다.",
        "F5 게이트": "살았다(0.6880 > 0.5)",
        "분모 정본(티처 #58 M8)": "A 는 62 · B·C·천장·통과선은 78. 두 수를 한 문장에 잇지 마라.",
        "896 에 대한 영향": "없다 --- 0단계에서 895 자와 유보의 교집합이 3행이라"
                       " 895 자를 안 쓰기로 이미 갈렸다. 정정은 그 결론을 더 강하게 만든다.",
    },
    "출처": "runners/out895_truth.json · out895_score.json · 원장 895 항목",
}


# ── 공통 ────────────────────────────────────────────────────────────────────
def stamp() -> dict:
    """🔴 티처 #58 M6 --- 산출물마다 박는다."""
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        head = "안 잡힘"
    return {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git HEAD": head,
            "코드 sha256": hashlib.sha256(ME.read_bytes()).hexdigest(),
            "코드": str(ME.relative_to(ROOT))}


def sp(a, b):
    """동률 평균 스피어만. 20행 미만이면 nan(ruler890.sp 와 같은 게이트)."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 20:
        return np.nan
    x, y = rankdata(a[ok]), rankdata(b[ok])
    x = x - x.mean(); y = y - y.mean()
    den = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / den) if den > 0 else np.nan


def partial_sp(a, b, ctrl):
    """순위 잔차 편상관. ctrl 은 (n, k) --- 상수는 자동으로 붙인다."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    C = np.asarray(ctrl, float).reshape(len(a), -1) if len(np.shape(ctrl)) else None
    ok = np.isfinite(a) & np.isfinite(b)
    if C is not None and C.size:
        ok &= np.isfinite(C).all(axis=1)
    if ok.sum() < 20:
        return np.nan
    x, y = rankdata(a[ok]), rankdata(b[ok])
    if C is None or not C.size:
        return sp(a[ok], b[ok])
    Z = np.column_stack([np.ones(ok.sum())]
                        + [rankdata(C[ok, j]) for j in range(C.shape[1])])
    # 상수만 남은 통제(값 가짓수 1)는 빼 준다 --- 특이행렬 방지
    keep = [0] + [j for j in range(1, Z.shape[1]) if len(np.unique(Z[:, j])) > 1]
    Z = Z[:, keep]
    rx = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
    ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    den = np.sqrt((rx * rx).sum() * (ry * ry).sum())
    return float((rx * ry).sum() / den) if den > 0 else np.nan


# ── 0단계 자료 ──────────────────────────────────────────────────────────────
def board_ids():
    """도메인 → 판 행 순서 id. `lab.trendaxes._ids` 가 정본(newcol884 관례)."""
    from lab import trendaxes as TT
    return TT._ids() or {}


def wiki_page_map():
    """record_id → (두드렸나, 문서 있나). 🔴 **셋을 안 섞는다**(조항 59)."""
    out = {}
    p = DS / "wiki_views"
    for f in p.glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        rid = d.get("record_id") or f.stem
        out[rid] = (True, bool(d.get("page")))
    return out


def desc_len_map():
    """도메인 → {행 id: 설명문 글자수}. **양(量)의 원천**."""
    ids = board_ids()
    out = {}
    # 세계애니 --- AniList 줄거리
    dw = json.loads((DS / "desc_wanime.json").read_text())
    wrec = json.loads((DS / "wanime_records.json").read_text())
    m = {}
    for k in ids.get("세계애니", []):
        mid = str((wrec.get(k) or {}).get("media_id", ""))
        t = dw.get(mid)
        if t:
            m[k] = len(str(t))
    out["세계애니"] = m
    # 펀딩 --- 텀블벅 shortDescription (⚠ 10~50자 절단)
    pool = json.loads((DS / "funding_pool.json").read_text())
    by = {}
    for x in pool:
        for kk in (x.get("permalink"), x.get("id")):
            if kk:
                by[str(kk)] = x
    frec = json.loads((DS / "funding_records.json").read_text())
    m = {}
    for k in ids.get("펀딩", []):
        r = frec.get(k) or {}
        x = by.get(str(r.get("permalink"))) or by.get(str(r.get("uuid")))
        t = (x or {}).get("shortDescription")
        if t:
            m[k] = len(str(t))
    out["펀딩"] = m
    # 만화 --- 유보 덮음이 6/258 이라 **못 쓴다**. 세어서 남긴다(조항 59)
    dm = json.loads((DS / "desc_manga.json").read_text())
    mrec = json.loads((DS / "manga_records.json").read_text())
    m = {}
    for k in ids.get("만화", []):
        mid = str((mrec.get(k) or {}).get("media_id", ""))
        t = dm.get(mid)
        if t:
            m[k] = len(str(t))
    out["만화"] = m
    return out


def title_country(d0):
    """도메인 → (제목 글자수, 제목 어절수, 원산국) --- 팔 A 편상관 통제."""
    from ingest.news_counts import titles
    ids = board_ids()
    mrec = json.loads((DS / "manga_records.json").read_text())
    wrec = json.loads((DS / "wanime_records.json").read_text())
    out = {}
    for dom in sorted(d0.dom):
        n = len(d0.dom[dom][2])
        ts = titles(dom)
        if ts is None or len(ts) != n:
            ts = None
        ch = np.array([len(str(x or "")) for x in ts], float) if ts is not None \
            else np.full(n, np.nan)
        wd = np.array([len(str(x or "").split()) for x in ts], float) if ts is not None \
            else np.full(n, np.nan)
        cty = np.full(n, np.nan)
        rec = {"만화": mrec, "세계애니": wrec}.get(dom)
        I = ids.get(dom)
        if rec is not None and I is not None and len(I) == n:
            lab = {}
            for i, k in enumerate(I):
                c = (rec.get(k) or {}).get("country")
                if c:
                    cty[i] = lab.setdefault(c, float(len(lab)))
        out[dom] = (ch, wd, cty)
    return out


def doses(d0):
    """용량 둘을 **판 행 순서**로 짓는다. 반환 {이름: {도메인: (값, 마스크)}}.

    값은 원값(백분위 변환은 주입 직전에) · 마스크는 **확인된 행만** 1.
    """
    ids = board_ids()
    wm = wiki_page_map()
    dl = desc_len_map()
    ga, na = {}, {}
    for dom in sorted(d0.dom):
        n = len(d0.dom[dom][2])
        I = ids.get(dom)
        v = np.full(n, np.nan); msk = np.zeros(n)
        if I is not None and len(I) == n:
            for i, k in enumerate(I):
                e = wm.get(k)
                if e is None:                 # **안 두드림** --- 결측이지 0 이 아니다
                    continue
                msk[i] = 1.0
                v[i] = 1.0 if e[1] else 0.0
        ga[dom] = (v, msk)
        m = dl.get(dom) or {}
        v2 = np.full(n, np.nan); msk2 = np.zeros(n)
        if I is not None and len(I) == n:
            for i, k in enumerate(I):
                if k in m:
                    v2[i] = float(m[k]); msk2[i] = 1.0
        na[dom] = (v2, msk2)
    return {"ㄱ 존재 이진": ga, "ㄴ 양(설명문 글자수)": na}


def coverage(d0, dose, post):
    """도메인별 유보 덮음 · 값 가짓수. 🔴 **판정 모집단을 여기서 정한다**."""
    out = {}
    for dom in sorted(d0.dom):
        v, m = dose[dom]
        te = post[dom]
        knocked = int(((m > 0) & te).sum())
        vv = v[(m > 0) & te]
        vv = vv[np.isfinite(vv)]
        out[dom] = {"유보": int(te.sum()), "두드림": knocked,
                    "값 가짓수": int(len(np.unique(vv))),
                    "양수(있음)": int((vv > 0).sum()) if len(vv) else 0,
                    "덮음률(유보)": round(knocked / max(int(te.sum()), 1), 4)}
        # 🔴 사전등록 ⓓ 의 채택 규칙(문면 그대로): 유보를 **절반 이상 두드렸고**
        # **확인된 '있음'(또는 값 있음)이 20행 이상**일 때만 그 도메인을 판정에 넣는다.
        # 만화(덮음률 0.023)·펀딩 ㄱ(있음 2)이 여기서 빠진다 --- 사전등록에 그렇게 적혀 있다.
        out[dom]["채택"] = bool(out[dom]["덮음률(유보)"] >= 0.5
                              and out[dom]["양수(있음)"] >= 20
                              and out[dom]["값 가짓수"] >= 2)
    return out


# ── 적합 (팔 A 의 행별 예측 · ruler890.fit_arm 의 챔피언판) ──────────────────
def _fit_pred(seed):
    """씨앗 하나로 챔피언을 적합하고 **유보 행별 예측**을 낸다."""
    import ff753 as FF
    from lab.forms import REGISTRY
    from lab.harness import Data, MIN_TRAIN
    CLS = REGISTRY["F18_bagboost"]["cls"]
    d = FF.shell(FF.base())
    post = {k: (np.isfinite(np.asarray(d.yr[k], float))
                & (np.asarray(d.yr[k], float) >= T)) for k in d.dom}
    train, tmask = {}, {}
    for k in d.dom:
        m = (np.isfinite(d.yr[k]) & (d.yr[k] < T) & np.isfinite(d.dom[k][2]))
        if m.sum() >= MIN_TRAIN:
            train[k] = d.slice(k, m); tmask[k] = m
    f = CLS(seed=seed)
    f.fit(Data(train, d.names, {k: d.yr[k][tmask[k]] for k in train}))
    pr, sc = {}, {}
    for k in d.dom:
        if post[k].sum() < 20:
            continue
        A, M, y, t = d.slice(k, post[k])
        p = np.asarray(f.predict(k, A, M, t), float)
        pr[k] = p.tolist()
        sc[k] = sp(p, y)
    return seed, pr, sc


def _board_one(args):
    """(팔이름, 축 dict 또는 None, 씨앗) → 도메인 점수. 팔 B 용."""
    name, ax, seed = args
    import ff753 as FF
    from lab.forms import REGISTRY
    from lab.harness import evaluate
    CLS = REGISTRY["F18_bagboost"]["cls"]
    extra = FF.base()
    if ax is not None:
        extra = {**extra, "dose896": {k: (np.asarray(v, np.float32),
                                          np.asarray(m, np.float32))
                                      for k, (v, m) in ax.items()}}
    d = FF.shell(extra)
    sc = evaluate(lambda: CLS(seed=seed), d, T=T)
    return name, seed, {k: float(v) for k, v in sc.items()}, float(d.pooled(sc, T=T))


# ── 0단계 ───────────────────────────────────────────────────────────────────
def stage0():
    import ff753 as FF
    from lab.forms import REGISTRY
    from lab.harness import evaluate
    CLS = REGISTRY["F18_bagboost"]["cls"]
    t0 = time.time()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    post = {k: (np.isfinite(np.asarray(d0.yr[k], float))
                & (np.asarray(d0.yr[k], float) >= T)) for k in doms}
    W = d0.weights(T)
    sc0 = evaluate(lambda: CLS(seed=0), d0, T=T)
    pooled0 = float(d0.pooled(sc0, T=T))

    ids = board_ids()
    # ⓑ 895 교집합
    tr = json.loads((ROOT / "runners/out895_truth.json").read_text())
    real = [x for x in tr["작품"] if not x.get("음성")]
    keys = [x["key"] for x in real]
    mrec = json.loads((DS / "manga_records.json").read_text())
    I = ids.get("만화") or []
    postset = {k for i, k in enumerate(I) if post["만화"][i]}
    inter = {"895 실물": len(keys),
             "manga_records(7982) 안": sum(1 for k in keys if k in mrec),
             "판 만화 행(manga_axes) 안": sum(1 for k in keys if k in set(I)),
             "🔴 유보 교집합 n": sum(1 for k in keys if k in postset)}
    inter["필요 도메인 Δρ(만화 하나로 문턱)"] = round(THRESH * sum(W.values())
                                            / max(W.get("만화", 1), 1), 5)
    inter["스피어만 최소행(ruler890.sp)"] = 20
    inter["판정"] = ("🔴 895 의 자로는 팔 B 를 못 연다 --- F4 발화"
                   if inter["🔴 유보 교집합 n"] < 20 else "쓸 수 있다")

    dz = doses(d0)
    cov = {k: coverage(d0, v, post) for k, v in dz.items()}
    dl = desc_len_map()

    out = {
        "무엇": "노트 896 0단계 --- 분모 세기(조항 60). 요청 0 · 적합 1(재현 대조).",
        "배선": {
            "가중 합": int(sum(W.values())), "3775 인가": sum(W.values()) == 3775,
            "도메인별 유보": {k: int(W[k]) for k in sorted(W, key=lambda x: -W[x])},
            "챔피언 씨앗0 판": pooled0,
            "EXPECT_POOLED_K1_S0(노트 898 정본 경로)": EXPECT_POOLED_K1_S0,
            "🔴 부동소수 완전 일치": pooled0 == EXPECT_POOLED_K1_S0,
            # 🔴 이슈 #123 --- 은퇴값을 **같이** 적는다. 위 한 줄이 True/False 만
            # 내면 「언제부터 False 였나」를 다음 세션이 못 센다.
            "은퇴값(서수 시대 · 노트 890 배선 ㄷ)": 0.4724867181663707,
            "은퇴값(서수 순위 시대)과의 차": pooled0 - SEED0_RETIRED,
            "⚠": ("정본이 옮겨가면 이 상수도 같이 옮긴다(이슈 #123). 옛 값을 재려면 "
                 "옛 구현을 파일에 박는다 --- `runners/board898.py`·`thr898.py`."),
            "도메인 점수(씨앗0)": {k: round(float(v), 4) for k, v in sc0.items()},
        },
        "ⓑ 895 자 ↔ 유보 교집합": inter,
        "ⓒ 용량 후보 덮음(유보 기준)": {
            "895 자 셋": inter["🔴 유보 교집합 n"],
            "만화 설명문(desc_manga)": int(sum(1 for i, k in enumerate(I)
                                           if post["만화"][i] and k in dl["만화"])),
            "세계애니 설명문(desc_wanime)":
                int(sum(1 for i, k in enumerate(ids.get("세계애니") or [])
                        if post["세계애니"][i] and k in dl["세계애니"])),
            "펀딩 shortDescription":
                int(sum(1 for i, k in enumerate(ids.get("펀딩") or [])
                        if post["펀딩"][i] and k in dl["펀딩"])),
            "뉴스 기사 수(news_counts 캐시 파일)":
                len(list((DS / "news_counts").glob("*.json"))),
            "⚠ tgt_desc(팝업·도서)": "제외 --- LLM 생성물이라 라벨 누출 위험(사전등록 ⓒ)",
        },
        "ⓓ 용량 덮음 · 판정 모집단": cov,
        "ⓔ 배선 사실 --- 용량 ㄱ 은 이미 판 안에 있다": {
            "근거 ①": "lab/forms.py:136-138 DirectPool._feat 가 축마다 값 열 + **관측 표시자 열**을 낸다",
            "근거 ②": "lab/wikiaxes.py:194 col[d]=(v, ok) --- page 를 못 찾은 행의 마스크가 0",
            "wiki 축이 names 에 있는 도메인":
                {k: [n for n in d0.names[k] if n.startswith("wiki_")] for k in doms},
            "🔴 뜻": "팔 B-ㄱ 는 새 정보 검정이 아니라 **중복 검정**이다(사전등록 P3ㄱ 로 미리 등록)",
        },
        "🔴 895 에서 읽은 값(복사본)": COPY_895,
        "초": round(time.time() - t0, 1),
    }
    out.update(stamp())
    (ROOT / "runners/out896_step0.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: out[k] for k in ("ⓑ 895 자 ↔ 유보 교집합", "ⓒ 용량 후보 덮음(유보 기준)")},
                     ensure_ascii=False, indent=1), flush=True)
    for nm in cov:
        print(nm, json.dumps({k: v for k, v in cov[nm].items() if v["두드림"]},
                             ensure_ascii=False), flush=True)


# ── 팔 A ────────────────────────────────────────────────────────────────────
def stageA():
    import ff753 as FF
    from lab import pairboot as PB
    from ingest.news_counts import titles
    t0 = time.time()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    post = {k: (np.isfinite(np.asarray(d0.yr[k], float))
                & (np.asarray(d0.yr[k], float) >= T)) for k in doms}
    W = d0.weights(T)

    with mp.Pool(min(6, len(SEEDS))) as pool:
        res = pool.map(_fit_pred, list(SEEDS))
    PRED = {}
    SC = {}
    for seed, pr, sc in res:
        SC[seed] = {k: (None if not np.isfinite(v) else round(float(v), 4))
                    for k, v in sc.items()}
        for k, p in pr.items():
            PRED.setdefault(k, []).append(np.asarray(p, float))

    # 앙상블 순위 → 행별 오차
    # 🔴 배선 검사가 잡은 것: `scipy 1.13 rankdata` 는 배열에 NaN 이 **하나라도** 있으면
    # **전부 NaN** 을 낸다(nan_policy='propagate'). 초판은 라벨 결측이 있는 게임(43건)과
    # 웹툰의 오차를 통째로 NaN 으로 만들어 두 도메인을 **조용히 중립화**했다 ---
    # '채택 도메인' 에 이름은 남고 통계에는 한 행도 안 들어갔다(조항 59 · 887 재발형).
    # 고침: **유한한 행만 골라 그 안에서** 순위를 낸다.
    ERR, NFIN = {}, {}
    for k in PRED:
        y = np.asarray(d0.dom[k][2], float)[post[k]]
        pr = np.asarray(PB.rank_ensemble(PRED[k]), float)
        e = np.full(len(y), np.nan)
        ok = np.isfinite(y) & np.isfinite(pr)
        if ok.sum() >= 20:
            n = int(ok.sum())
            e[ok] = np.abs(rankdata(pr[ok]) / n - rankdata(y[ok]) / n)
        ERR[k] = e
        NFIN[k] = {"유보 행": int(len(y)), "라벨·예측 유한": int(ok.sum()),
                   "🔴 결측": int(len(y) - ok.sum())}

    dz = doses(d0)
    cov = {nm: coverage(d0, v, post) for nm, v in dz.items()}
    tc = title_country(d0)

    rng = np.random.default_rng(BOOT_SEED)
    result = {}
    for nm, ax in dz.items():
        use = [k for k in doms if cov[nm][k]["채택"] and k in ERR]
        per, rows = {}, []
        for k in use:
            v, m = ax[k]
            te = post[k]
            sel = (m[te] > 0) & np.isfinite(v[te])
            dose = v[te][sel]
            err = ERR[k][sel]
            ch, wd, cty = tc[k]
            ch, wd, cty = ch[te][sel], wd[te][sel], cty[te][sel]
            ttl = titles(k)
            ttl = ([str(x) for x in np.asarray(ttl, object)[te][sel]]
                   if (ttl is not None and len(ttl) == len(te)) else None)
            r0 = sp(dose, -err)
            c1 = partial_sp(dose, -err, np.column_stack([ch]))
            c2 = partial_sp(dose, -err, np.column_stack([ch, wd]))
            c3 = (partial_sp(dose, -err, np.column_stack([ch, wd, cty]))
                  if np.isfinite(cty).any() else None)
            per[k] = {"n(용량 있음)": int(sel.sum()),
                      "n(오차도 유한 · 통계에 실제로 든 행)": int(np.isfinite(err).sum()),
                      "유보 가중": int(W.get(k, 0)),
                      "ρ_A 무통제": None if not np.isfinite(r0) else round(r0, 4),
                      "ρ_A +글자수": None if not np.isfinite(c1) else round(c1, 4),
                      "ρ_A +글자수+어절수": None if not np.isfinite(c2) else round(c2, 4),
                      "ρ_A +원산국": (None if c3 is None or not np.isfinite(c3)
                                 else round(c3, 4)),
                      "원산국 통제": "있다" if c3 is not None else "🔴 없다(원천 없음)",
                      "용량 평균": round(float(np.nanmean(dose)), 4),
                      "오차 평균": (round(float(np.nanmean(err)), 4)
                                if np.isfinite(err).any() else None)}
            for i in range(int(sel.sum())):
                rows.append((k, dose[i], err[i], ch[i], wd[i], cty[i],
                             ttl[i] if ttl else ""))
        if not rows:
            result[nm] = {"⛔": "채택 도메인 0"}
            continue
        dm_ = np.array([r[0] for r in rows], object)
        do_ = np.array([r[1] for r in rows], float)
        er_ = np.array([r[2] for r in rows], float)
        ch_ = np.array([r[3] for r in rows], float)
        wd_ = np.array([r[4] for r in rows], float)
        ti_ = [r[6] for r in rows]

        def agg(idx, dose=None):
            """도메인 안 스피어만을 **행수 가중**으로 모은다."""
            num = den = 0.0
            dd = do_ if dose is None else dose
            for k in use:
                s = idx[dm_[idx] == k]
                w_ = int((np.isfinite(dd[s]) & np.isfinite(er_[s])).sum())
                if w_ < 20:
                    continue
                r = sp(dd[s], -er_[s])
                if np.isfinite(r):
                    num += r * w_; den += w_
            return num / den if den else np.nan

        allidx = np.arange(len(rows))
        point = agg(allidx)

        # 순열 널 --- 도메인 **안에서** 용량 라벨을 섞는다(891 방식)
        nulls = []
        for _ in range(PERM):
            dd = do_.copy()
            for k in use:
                s = np.flatnonzero(dm_ == k)
                dd[s] = rng.permutation(dd[s])
            nulls.append(agg(allidx, dd))
        nulls = np.array([x for x in nulls if np.isfinite(x)])
        two_sig = float(2 * nulls.std(ddof=1))
        p2 = float((np.abs(nulls - nulls.mean()) >= abs(point - nulls.mean())).mean())

        cl, wire = PB.clusters_of(ti_)
        try:
            pt, lo, hi, kind = PB.cluster_boot(agg, cl, B=B_BOOT, seed=BOOT_SEED)
            fb = None
        except Exception as e:                       # 폴백은 **사유를 적는다**(규약 47)
            pt, lo, hi, kind = point, float("nan"), float("nan"), "실패"
            fb = f"cluster_boot 예외: {e!r}"
        eff = [k for k in use if per[k]["ρ_A 무통제"] is not None]
        result[nm] = {
            "채택 도메인": use, "뺀 도메인": [k for k in doms if k not in use],
            "🔴 뺀 이유": {k: cov[nm][k] for k in doms if k not in use},
            "🔴 통계에 실제로 든 도메인": eff,
            "🔴 이름만 남고 못 잰 도메인": [k for k in use if k not in eff],
            "행 수(용량 있음)": len(rows),
            "행 수(통계에 든 것)": int(np.isfinite(er_).sum()),
            "라벨·예측 유한 회계": {k: NFIN.get(k) for k in use},
            "ρ_A (행수 가중 · 무통제)": round(float(point), 5),
            "순열 널 평균": round(float(nulls.mean()), 5),
            "순열 널 2σ": round(two_sig, 5),
            "🔴 순열 널 2σ 대 문턱 0.00353": round(two_sig / THRESH, 2),
            "순열 널 양측 p": p2,
            "순열 널 밖인가(|점−널평균| > 2σ)": bool(abs(point - nulls.mean()) > two_sig),
            "BCa 95%": [round(float(lo), 5), round(float(hi), 5)],
            "구간 종류": kind, "폴백 사유": fb, "군집": wire,
            "판정(pairboot.verdict)": PB.verdict(lo, hi),
            "도메인별": per,
        }
        # 통제 후 가중 평균(도메인별 값을 **통계에 든 행수**로 가중)
        for lab in ("ρ_A 무통제", "ρ_A +글자수", "ρ_A +글자수+어절수", "ρ_A +원산국"):
            num = den = 0.0
            got = []
            for k in eff:
                v = per[k][lab]
                if v is not None:
                    w_ = per[k]["n(오차도 유한 · 통계에 실제로 든 행)"]
                    num += v * w_; den += w_; got.append(k)
            result[nm][f"가중 {lab}"] = round(num / den, 5) if den else None
            # 🔴 원산국은 원천이 세계애니뿐이라 '가중 평균' 이 아니라 **한 도메인**이다.
            #    분모를 병기하지 않으면 조항 60 위반이 된다.
            result[nm][f"가중 {lab} · 든 도메인"] = got
        base_ = result[nm]["가중 ρ_A 무통제"]
        result[nm]["🔴 통제 후 유지율(글자수+어절수)"] = (
            round(result[nm]["가중 ρ_A +글자수+어절수"] / base_, 3)
            if base_ and abs(base_) > 0.01 else
            "🔴 안 낸다 --- 무통제 점추정이 0 근처라 비가 뜻을 잃는다")

    out = {"무엇": "노트 896 팔 A --- 관찰. 유보 행별 오차 vs 용량. 요청 0.",
           "설계": {"반응": "|rank(pred)/n − rank(y)/n| · 씨앗 0~5 순위 앙상블",
                  "부호": "ρ_A = Spearman(용량, −오차) · 양수 = 텍스트 많은 행을 더 잘 맞힌다",
                  "널": f"도메인 안 용량 라벨 순열 {PERM}회 · 씨앗 {BOOT_SEED}",
                  "🔴 문턱 0.00353 은 이 팔에 안 쓴다": "널 팔 쌍으로 잰 개입 채택선이다"},
           "씨앗별 도메인 점수": SC,
           "결과": result, "초": round(time.time() - t0, 1)}
    out.update(stamp())
    (ROOT / "runners/out896_armA.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    for nm, r in result.items():
        print(nm, json.dumps({k: r.get(k) for k in
                              ("ρ_A (행수 가중 · 무통제)", "순열 널 2σ", "순열 널 양측 p",
                               "BCa 95%", "구간 종류", "가중 ρ_A +글자수+어절수",
                               "채택 도메인")}, ensure_ascii=False), flush=True)


# ── 팔 B ────────────────────────────────────────────────────────────────────
def _pct_axis(ax, post, shuffle_seed=None, keep=None):
    """도메인 안 백분위 1열 + 마스크. shuffle_seed 면 **값만** 섞는다(노트 335).

    `keep` 은 사전등록 ⓓ 가 채택한 도메인 집합이다 --- 그 밖은 마스크 0 으로
    **명시적으로** 끈다(조용한 중립화가 아니라 등록된 배제다).
    """
    rng = np.random.default_rng(shuffle_seed) if shuffle_seed is not None else None
    out = {}
    for k, (v, m) in ax.items():
        n = len(v)
        ok = (np.asarray(m) > 0) & np.isfinite(v)
        if keep is not None and k not in keep:
            ok = np.zeros(n, bool)
        r = np.full(n, 0.5, np.float32)
        if ok.sum() >= 3:
            vv = np.asarray(v, float)[ok]
            if rng is not None:
                vv = rng.permutation(vv)
            r[ok] = (rankdata(vv) / ok.sum()).astype(np.float32)
        out[k] = (r, ok.astype(np.float32))
    return out


def stageB():
    import ff753 as FF
    from lab import pairboot as PB
    t0 = time.time()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    post = {k: (np.isfinite(np.asarray(d0.yr[k], float))
                & (np.asarray(d0.yr[k], float) >= T)) for k in doms}
    W = d0.weights(T); tot = sum(W.values())
    dz = doses(d0)
    cov = {nm: coverage(d0, v, post) for nm, v in dz.items()}

    # ── 배선 검사 (측정 전) ────────────────────────────────────────────────
    wire = {}
    jobs = []
    axes = {}
    for nm, ax in dz.items():
        keep = {k for k in doms if cov[nm][k]["채택"]}
        real = _pct_axis(ax, post, keep=keep)
        axes[(nm, "진짜")] = real
        w = {}
        for k in doms:
            v, m = real[k]
            te = post[k]
            uniq = int(len(np.unique(np.asarray(v)[np.asarray(m) > 0])))
            w[k] = {"관측": int((np.asarray(m) > 0).sum()), "행": len(v),
                    "덮음률": round(float((np.asarray(m) > 0).mean()), 4),
                    "유보 덮음률": round(float(((np.asarray(m) > 0) & te).sum()
                                        / max(int(te.sum()), 1)), 4),
                    "고유값": uniq,
                    "🔴 조용한 중립화": bool((np.asarray(m) > 0).sum() == 0 or uniq < 2)}
        wire[nm] = w
        wire[nm]["🔴 등록된 배제(사전등록 ⓓ)"] = sorted(set(doms) - keep)
        for ds in NULL_DRAWS:
            axes[(nm, f"널 {ds}")] = _pct_axis(ax, post, shuffle_seed=ds, keep=keep)

    # 주입 열 sha256 --- 진짜와 널이 **다른** 비트인지, 마스크는 **같은지**
    def dig(a):
        h = hashlib.sha256()
        for k in sorted(a):
            h.update(np.ascontiguousarray(np.asarray(a[k][0], np.float32)).tobytes())
        return h.hexdigest()[:16]

    def digm(a):
        h = hashlib.sha256()
        for k in sorted(a):
            h.update(np.ascontiguousarray(np.asarray(a[k][1], np.float32)).tobytes())
        return h.hexdigest()[:16]

    sha = {f"{nm} · {tag}": {"값 sha": dig(a), "마스크 sha": digm(a)}
           for (nm, tag), a in axes.items()}
    for nm in dz:
        rm = digm(axes[(nm, "진짜")])
        sha[f"{nm} · 마스크 무늬 보존"] = all(
            digm(axes[(nm, t_)]) == rm for t_ in [f"널 {d}" for d in NULL_DRAWS])
        sha[f"{nm} · 널이 진짜와 다른 값"] = all(
            dig(axes[(nm, t_)]) != dig(axes[(nm, "진짜")])
            for t_ in [f"널 {d}" for d in NULL_DRAWS])

    jobs.append(("기준선", None, None))
    for (nm, tag), a in axes.items():
        jobs.append((f"{nm} · {tag}", a, None))
    tasks = [(name, a, s) for (name, a, _) in jobs for s in SEEDS]
    print(f"팔 B: 판 {len(jobs)}개 × 씨앗 {len(SEEDS)} = {len(tasks)} 적합", flush=True)

    with mp.Pool(6) as pool:
        res = pool.map(_board_one, tasks)
    BD = {}
    for name, seed, sc, pooled in res:
        BD.setdefault(name, {"씨앗별": {}, "도메인": {}})
        BD[name]["씨앗별"][seed] = pooled
        for k, v in sc.items():
            BD[name]["도메인"].setdefault(k, []).append(v)
    for name in BD:
        BD[name]["판"] = float(np.mean(list(BD[name]["씨앗별"].values())))
        BD[name]["씨앗SD"] = float(np.std(list(BD[name]["씨앗별"].values()), ddof=1))
        BD[name]["도메인"] = {k: float(np.mean(v)) for k, v in BD[name]["도메인"].items()}

    base = BD["기준선"]["판"]
    verdicts = {}
    for nm in dz:
        real = BD[f"{nm} · 진짜"]
        nl = [BD[f"{nm} · 널 {d}"]["판"] for d in NULL_DRAWS]
        sig = real["판"] - float(np.mean(nl))
        net = real["판"] - base
        # 씨앗 짝: 진짜 − 널평균 을 씨앗마다
        paired = np.array([real["씨앗별"][s]
                           - np.mean([BD[f"{nm} · 널 {d}"]["씨앗별"][s]
                                      for d in NULL_DRAWS]) for s in SEEDS])
        cl, wr = PB.solo_clusters(len(paired))
        try:
            pt, lo, hi, kind = PB.cluster_boot(
                lambda ix: float(np.mean(paired[ix])), cl, B=B_BOOT, seed=BOOT_SEED)
            fb = ("⚠ 씨앗 6개짜리 짝 부트 --- 행 군집이 아니라 **씨앗** 재표집이다. "
                  "행 잡음은 이 구간에 안 들어간다(병기 의무)")
        except Exception as e:
            pt, lo, hi, kind, fb = sig, float("nan"), float("nan"), "실패", f"예외 {e!r}"
        per = {}
        for k in set(real["도메인"]) & set(BD["기준선"]["도메인"]):
            pm = float(np.mean([BD[f"{nm} · 널 {d}"]["도메인"].get(k, np.nan)
                                for d in NULL_DRAWS]))
            per[k] = {"신호 몫": round(real["도메인"][k] - pm, 4),
                      "순효과": round(real["도메인"][k] - BD["기준선"]["도메인"][k], 4),
                      "유보": int(W.get(k, 0)),
                      "유보 덮음률": wire[nm][k]["유보 덮음률"],
                      "판 기여": round((real["도메인"][k] - pm) * W.get(k, 0) / tot, 5)}
        verdicts[nm] = {
            "기준선 판": round(base, 5), "진짜 판": round(real["판"], 5),
            "널 판 셋": {str(d): round(BD[f"{nm} · 널 {d}"]["판"], 5) for d in NULL_DRAWS},
            "널 평균": round(float(np.mean(nl)), 5),
            "널 폭(최대−최소)": round(float(np.max(nl) - np.min(nl)), 5),
            "**신호 몫(진짜 − 널평균)**": round(sig, 5),
            "**순효과(진짜 − 기준선)**": round(net, 5),
            "씨앗 짝 평균": round(float(paired.mean()), 5),
            "씨앗 짝 BCa 95%": [round(float(lo), 5), round(float(hi), 5)],
            "구간 종류": kind, "🔴 구간 한계 병기": fb,
            "판정(pairboot.verdict)": PB.verdict(lo, hi),
            "문턱 0.00353 넘었나": bool(sig > THRESH),
            "🔴 잡음 바닥 0.01055 병기": round(sig / JUNK_FLOOR, 3),
            "도메인별": dict(sorted(per.items(), key=lambda x: -abs(x[1]["판 기여"]))),
        }

    out = {"무엇": "노트 896 팔 B --- 개입. 용량을 열로 주입 → 판 Δρ. 요청 0.",
           "설계": {"주입": "ff753 열 주입 정본 · 도메인 안 백분위 1열 + 마스크",
                  "널 팔": f"값만 섞고 마스크 무늬 보존(노트 335) · 뽑기 {NULL_DRAWS}",
                  "씨앗": list(SEEDS), "판정선": THRESH,
                  "잡음 바닥(노트 892)": JUNK_FLOOR},
           "배선 검사": wire, "주입 열 sha256": sha,
           "기준선 게이트": {"판": round(base, 5), "범위": list(BASE_OK),
                      "통과": bool(BASE_OK[0] <= base <= BASE_OK[1])},
           "판별": verdicts,
           "판 원자료": {k: {"판": round(v["판"], 5), "씨앗SD": round(v["씨앗SD"], 5),
                         "씨앗별": {str(s): round(x, 5) for s, x in v["씨앗별"].items()},
                         "도메인": {a: round(b, 4) for a, b in v["도메인"].items()}}
                     for k, v in BD.items()},
           "용량 덮음(0단계 재계산)": cov,
           "초": round(time.time() - t0, 1)}
    out.update(stamp())
    (ROOT / "runners/out896_armB.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(verdicts, ensure_ascii=False, indent=1)[:4000], flush=True)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "0"
    {"0": stage0, "A": stageA, "B": stageB}[which]()
