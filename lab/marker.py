"""표시자 --- 관측 표시자가 값 너머로 무엇을 나르나(노트 306).

``forms._design`` 은 축마다 **(값, 관측 표시자)** 쌍을 낸다. 표시자는
``모르는 자리를 알리라''고 넣은 것인데, **표시자가 어떻게 정해지느냐**가
축마다 다르고 그중 일부는 **사후**다.

노트 306이 잡은 것: 위키 축의 마스크가 ``긁은 시점(2026)에 위키 문서를
찾았나''였다. 값은 깨끗한데(창이 시작일 이전 90일) 표시자가 결과를
나르고 있었다 --- 2025년에 나온 게임이 2026년까지 문서를 갖게 되는 것은
그 게임이 어떻게 됐는지의 결과다. ``provenance`` 는 ``wiki_*`` 를 PRE 로
등록해 뒀는데 그 등록은 **값**에 대해 맞았고 표시자를 말하지 않았다.

**어떻게 자동으로 잡나.** 노트 306이 손으로 쓴 결정적 대조를 그대로 옮긴다.

    ① 표시자와 라벨의 상관을 잰다              --- 의심 후보
    ② **값이 바닥인 관측 행**과 결측 행을 견준다 --- 값으로 설명되나

②가 열쇠다. 축의 값이 ``정보 없음''을 뜻하는 바닥(관측된 것 중 최저)인
행과, 아예 결측인 행은 **그 축에 대해 같은 것을 말한다.** 그런데 라벨이
갈리면, 표시자가 값이 안 나르는 무언가를 나른다는 뜻이다. 위키에서 그것이
``출시 전 조회수 0 인데 문서는 있다''대 ``문서가 없다''였고 게임 유보에서
7.643 대 9.087(p=0.0008)이었다.

**거부권이 아니라 이름표다**(``hearing`` · ``overlap`` 과 같은 규약).
표시자가 사후인지 아닌지는 **자료가 어떻게 만들어졌나**를 알아야 정해지고
그건 사람이 안다. 이 파일은 **어디를 봐야 하는지**를 매 실행에 적어 둔다.

검색 축이 반례다 --- 수집기가 데이터랩에 물어보고 빈 계열을 받은 것은
수집 시점의 진짜 측정이라 마스크가 사후가 아니다. 그래서 ②가 걸려도
``사후''라고 단정하지 않는다. ``볼 것''이라고만 적는다.
"""
from __future__ import annotations

import numpy as np

MIN_ROWS = 30          # 한쪽 무리의 최소
RHO_FLAG = 0.20        # ① 표시자~라벨 --- 이보다 크면 후보
P_FLAG = 0.01          # ② 바닥 대조의 유의수준
FLOOR_Q = 0.10         # 값 ``바닥''의 정의 --- 관측된 것의 하위 10%


def _families(names: list[str]) -> dict:
    """축 이름 → 계열(prefix). ``forms._family`` 와 같은 나눔을 쓰되
    표시자는 계열 단위로 함께 움직이므로 계열로 묶는다."""
    out = {}
    for i, n in enumerate(names):
        for p, f in (("cal_", "달력"), ("wiki_", "위키"), ("trend_", "검색"),
                     ("tag_", "태그"), ("meta_", "메타"), ("pop_", "팝업전용")):
            if n.startswith(p):
                out.setdefault(f, []).append(i)
                break
    return out


def check(A, M, y, cols) -> dict:
    """한 (도메인, 계열) 자리. 학습/유보 구분 없이 주어진 행에서만 센다."""
    from scipy.stats import spearmanr, mannwhitneyu
    obs = (M[:, cols].max(1) > .5)
    k = np.isfinite(y)
    n_obs, n_mis = int((obs & k).sum()), int(((~obs) & k).sum())
    if n_obs < MIN_ROWS or n_mis < MIN_ROWS:
        return {"판정": "못 잰다", "관측": n_obs, "결측": n_mis}
    r = spearmanr(obs[k].astype(float), y[k])
    out = {"관측": n_obs, "결측": n_mis,
           "표시자~라벨": (round(float(r.statistic), 3), round(float(r.pvalue), 4))}

    # ② 값이 바닥인 관측 행 대 결측 행 --- 축 값이 같은 것을 말하는 두 무리
    v = A[:, cols].max(1)                       # 계열 안 최고값을 대표로
    ov = v[obs & k]
    if len(ov) < MIN_ROWS:
        out["판정"] = "못 잰다"
        return out
    floor = np.quantile(ov, FLOOR_Q)
    lo = obs & k & (v <= floor)
    mis = (~obs) & k
    if int(lo.sum()) < 15 or int(mis.sum()) < 15:
        out["바닥 대조"] = None
        out["판정"] = "바닥 표본 부족"
        return out
    u = mannwhitneyu(y[mis], y[lo], alternative="two-sided")
    out["바닥 대조"] = {"결측 n": int(mis.sum()), "결측 중앙": round(float(np.median(y[mis])), 3),
                    "바닥 n": int(lo.sum()), "바닥 중앙": round(float(np.median(y[lo])), 3),
                    "p": round(float(u.pvalue), 4)}
    strong = abs(r.statistic) >= RHO_FLAG and r.pvalue < 0.01
    split = u.pvalue < P_FLAG
    out["판정"] = ("볼 것" if (strong and split) else
                 ("표시자만 큼" if strong else
                  ("바닥만 갈림" if split else "괜찮다")))
    return out


def report(data, T: float = 2025.0) -> dict:
    """도메인 × 계열마다 학습 · 유보에서 센다."""
    out, flags = {}, []
    for d in sorted(data.dom):
        A, M, y, _ = data.dom[d]
        yr = data.yr[d]
        fam = _families(list(data.names[d]))
        if not fam:
            continue
        per = {}
        for f, cols in fam.items():
            row = {}
            for lab, m in (("학습", np.isfinite(yr) & (yr < T)),
                           ("유보", np.isfinite(yr) & (yr >= T))):
                if m.sum() < 2 * MIN_ROWS:
                    continue
                row[lab] = check(A[m], M[m], y[m], cols)
                if row[lab].get("판정") == "볼 것":
                    flags.append(f"{d}·{f}·{lab}")
            if row:
                per[f] = row
        if per:
            out[d] = per
    return {"도메인": out, "볼 것": flags,
            "한 줄": ("표시자 --- 볼 것 " + ", ".join(flags)) if flags
                    else "표시자 --- 볼 것 없음"}
