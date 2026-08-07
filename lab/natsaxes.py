"""전국 상태 축 — **11개 도메인 전부에 붙는다**(노트 646).

**왜 이 축이 있어야 하나.** 노트 638·640·645 가 같은 벽을 세 번 쳤다 ---
팝업 89행에 열을 더하면 성적이 내려간다(날씨 −0.0283 · 위약 −0.0344 ·
방문자 −0.067). 위약이 진짜보다 더 나빴으므로 원인은 신호가 아니라 **행이
얇다는 것**이다.

그런데 그 세 번 동안 나는 팝업을 시험대로 썼다. **그게 틀렸다.** 판에는
도메인이 열하나 있고 행이 **21,672** 개다. 팝업 89행은 그중 **0.4%** 다.
파운데이션 모델을 찾는다면서 0.4% 짜리 도메인에서 축을 시험한 것이다 ---
그래서 판이 −0.0018 밖에 안 움직이고(씨앗SE 0.0002) 무엇을 넣든 결론이
"안 통한다" 로 나온다. 그건 축에 대한 정보가 아니라 산수다.

**그리고 답은 내가 방금 버린 것 안에 있었다.** 노트 644 에서 유동인구 장을
분석할 때 *"전국 공통 충격"* 을 잡음으로 빼냈다 --- 명절 · 연휴 · 전국적
사건이 264개 동네를 같이 움직이므로, 그걸 안 빼면 공통 요인이 확산으로
보이기 때문이다. 그 통제는 옳았다.

    그런데 도메인을 가로지르는 관점에서는 **그 뺀 성분이 바로 공유 상태**다.

지역은 팝업 · 시장팝업에만 붙는다. 만화 · 웹툰 · 게임 · 모바일 · 도서 ·
펀딩 · 애니는 장소가 없다. 그러나 **그 시기 한국이 평소보다 얼마나 움직이나**
는 전부에 붙는다. 어느 작품이든 언제 나오는지는 있기 때문이다 --- 노트 130 이
달력 축을 지을 때 쓴 것과 같은 논리이고, 그때 달력은 검색을 이겼다.

**달력과 무엇이 다른가.** `cal_*` 는 *예정된* 것을 안다(요일 · 계절 · 공휴일).
이 축은 **예정에서 벗어난 정도**를 잰다. 그래서 만들 때 요일과 연중 계절을
**빼고 남은 잔차**만 쓴다 --- 그 둘은 이미 `cal_*` 가 나른다. 남는 것은
*"이 시기에 사람들이 평소보다 더/덜 돌아다녔다"* 이고, 그건 날씨 · 사건 ·
경기 · 분위기가 섞인 값이다. 사용자가 상태층을 정의하며 말한 것에 제일 가깝다.

축 둘. **적게 넣는다** --- 노트 640 이 열의 값을 가르쳤다.

    nat_flow   출시 이전 30일, 전국 이동량 잔차의 평균
    nat_mom    최근 30일 − 그 이전 60일 (오르는 국면인가)

**시간 게이트.** 출시일 **이전** 창만 본다. 당일과 이후는 한 칸도 안 본다
(노트 149 규약).

**누출.** 연중 계절 성분을 뺄 때 그 평균을 **2024년까지로만** 계산한다.
판의 유보가 2025+ 이므로 전 구간으로 계산하면 유보가 정규화에 새어든다
(노트 645 에서 같은 자리를 한 번 밟았다 --- 그때 누출 몫이 R² 0.011 이었다).
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import numpy as np

#: 정규화 통계를 여기까지로만 잡는다. 판 유보(2025+)를 안 본다.
STATS_END = "20241231"
NEAR = 30        # 출시 이전 창
FAR = 90         # 비교 창의 끝
MIN_DAYS = 15    # 창 안에 이만큼은 있어야 쓴다


def national() -> dict:
    """{날짜(date): 잔차}. 전국 외지인 총량에서 요일과 연중 계절을 뺀 나머지.

    **요일과 계절을 빼는 것이 이 축의 전부다.** 안 빼면 `cal_dow_*` ·
    `cal_month_*` 를 복사한 열이 되고, 노트 638 이 날씨에서 당한 것이 정확히
    그것이었다(평년값은 사실상 계절의 사본이었다).
    """
    from ingest.visitors import series
    ser = series("2")                                  # 외지인
    if not ser:
        return {}
    tot: dict = {}
    for _code, byd in ser.items():
        for ymd, v in byd.items():
            tot[ymd] = tot.get(ymd, 0.0) + v
    days = sorted(tot)
    y = np.log10(np.array([tot[d] for d in days]))
    ds = [datetime.date(int(d[:4]), int(d[4:6]), int(d[6:8])) for d in days]
    fit = np.array([d <= STATS_END for d in days])     # 누출 차단
    dow = np.array([x.weekday() for x in ds])
    r = y - np.mean(y[fit])
    for w in range(7):                                 # 요일
        m = dow == w
        if (m & fit).sum() > 5:
            r[m] -= np.mean(r[m & fit])
    doy = np.array([x.timetuple().tm_yday for x in ds])
    # 연중 계절 --- 30일 폭으로 감싸며 평균(순환)
    seas = np.zeros(367)
    for k in range(1, 367):
        d = np.minimum(np.abs(doy - k), 366 - np.abs(doy - k))
        m = (d <= 15) & fit
        if m.sum() > 10:
            seas[k] = np.mean(r[m])
    r = r - seas[doy]
    return dict(zip(ds, r))


def _win(nat: dict, d: datetime.date, a: int, b: int) -> tuple:
    """[d-a, d-b) 구간 평균과 관측 일수. **당일과 이후는 안 본다.**"""
    v = [nat[d - datetime.timedelta(days=i)] for i in range(b, a)
         if (d - datetime.timedelta(days=i)) in nat]
    return (float(np.mean(v)) if v else np.nan), len(v)


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


def detrend(nat: dict, win: int = 365) -> dict:
    """장기 추세를 뺀다 — **후행 이동평균**이라 미래를 안 본다(노트 649).

    노트 646 이 잰 것: 수준을 그대로 쓰면 축이 **연도 지표**가 된다. 계절은
    뺐지만 추세는 안 뺐고, 2020~2022 는 코로나로 눌렸다가 회복했다. 판은
    2025년으로 잘라 채점하므로 학습과 유보의 값 분포가 체계적으로 달라
    나무가 외삽에 실패한다.

    중심 이동평균을 쓰면 미래를 보므로 **후행**만 쓴다. 창이 안 차면 있는
    만큼으로 평균한다.
    """
    ds = sorted(nat)
    v = np.array([nat[d] for d in ds])
    out = {}
    for i, d in enumerate(ds):
        a = v[max(0, i - win + 1):i + 1]
        out[d] = float(v[i] - a.mean())
    return out


def build(report: bool = False, axes: tuple = None) -> dict:
    """{축이름: {도메인: (값, 표시자)}} — **전 도메인**.

    ``axes`` 로 넣을 축을 고른다. ``nat_dev`` 는 추세를 뺀 `nat_flow` 다.
    """
    from .calaxes import _dates
    nat = national()
    if not nat:
        return {}
    axes = axes or ("nat_flow", "nat_mom")
    dev = detrend(nat) if "nat_dev" in axes else None
    dates = _dates()
    out: dict = {"nat_flow": {}, "nat_mom": {}, "nat_dev": {}}
    rep: dict = {}
    for dom, ds in dates.items():
        n = len(ds)
        flow = np.full(n, np.nan)
        mom = np.full(n, np.nan)
        for i, d in enumerate(ds):
            if d is None:
                continue
            near, n1 = _win(nat, d, NEAR, 1)
            far, n2 = _win(nat, d, FAR, NEAR)
            if n1 >= MIN_DAYS:
                flow[i] = _win(dev, d, NEAR, 1)[0] if dev is not None else near
                if n2 >= MIN_DAYS:
                    mom[i] = near - far
        # ``nat_dev`` 는 ``flow`` 자리에 추세를 뺀 값이 들어간 것이므로 이름만
        # 갈아 준다. **고른 축만 낸다** --- 노트 641 의 열 예산 때문에 팔마다
        # 열 하나로 재야 해서, 안 고른 축이 딸려 나가면 실험이 무의미해진다.
        first = "nat_dev" if "nat_dev" in axes else "nat_flow"
        for nm, col in ((first, flow), ("nat_mom", mom)):
            if nm not in axes:
                continue
            ok = np.isfinite(col)
            if ok.sum() >= 30 and len(np.unique(col[ok])) >= 3:
                out[nm][dom] = (_pct(col, ok), ok.astype(np.float32))
        rep[dom] = {"행": n, "덮음": round(float(np.isfinite(flow).mean()), 3)}
    out = {k: v for k, v in out.items() if v}
    if report:
        print(json.dumps({"축": list(out), "도메인별": rep,
                          "전국 시계열 날": len(nat)}, ensure_ascii=False, indent=1), flush=True)
    return out


if __name__ == "__main__":
    build(report=True)
