"""팝업 **전용** 축(노트 276).

노트 274가 팝업에 대해 두 가지를 확정했다. 하나 --- 팝업을 올려도 판은
못 본다(도메인 안에서 $\\Delta\\rho=0.435$ 가 있어야 판이 미결정 폭을
넘는다). 둘 --- 그래도 올릴 이유가 있다(노트 254의 배포 단위). 노트 275가
그 둘을 규칙으로 묶었다: **판이 미결정 폭 안이고 어느 도메인도 $|t|>2$ 로
안 나빠지면 배포 이득이 정한다.**

그래서 팝업 프로젝트 레코드 380건에서 아직 축이 아닌 파생 열을 봤다.
쓰는 행 75건 위에서 덮음이 88~91% 인 후보가 열여섯이었고, 노트 239 · 256의
채택 검사로 걸렀다.

**넷은 하나였다.** 경쟁 열 넷(같은주소 · 이전개최 · 500m · 1km)이 서로
0.85~1.00 으로 겹친다 --- ``500m`` 와 ``1km`` 는 순위 상관이 **정확히
1.000** 이라 같은 열이다. 덮음 100% 짜리 열 넷처럼 보였지만 신호는 하나다.
가드 **겹말**이 채택 뒤에 잡을 것을 채택 전에 잡았다. 그래서 하나만 쓴다.

**떨어진 것.** ``달력_연휴전``은 기존 ``cal_holiday_gap`` 과 0.592 겹쳐서
뺐다 --- 그 축을 다시 쓰는 것이다. ``달력_연휴포함``은 ``기간_연휴일`` 과
0.652 겹쳐 둘 중 뒤엣것만 남겼다. ``손익_*`` 은 덮음이 65% 로 얇고
``pnl_pre`` 가 실제로 사전인지 확인이 안 돼 이번엔 뺀다.

**쌓임.** 다섯 다 연도 순위 상관이 $|{\\cdot}|<0.13$ 이라 가드 **쌓임**의
문턱에서 멀다. 경쟁 열은 ``이전개최``(장소에 쌓인다)를 안 고르고
``1km``(동시 개최)를 골랐다.

**이름은 도메인 전용이다**(노트 250 · 251). 팝업만 갖는 축을 이름 공유로
주면 결국 전용 열이 되면서 측정만 헷갈린다.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

# 이름 → 레코드 경로. 노트 276의 검사 ①③ 을 통과하고 서로 안 겹치는 넷.
#
# **``기간_일수''는 검사를 통과했는데도 뺐다.** ``state/dataset_v2.py`` 가
# 이미 그 결정을 적어 뒀다 --- ``planned_operating_days 는 피처가 아니라
# 분모로 승격시킨다. y_perday = visitors / days 이므로 days 가 틀리면 타깃
# 자체가 오염된다.'' 라벨의 분모를 피처로 다시 넣을 뻔했다. 검사 ①이
# 0.177 로 통과시켰지만 통과가 근거는 아니다(노트 133).
#
# 남긴 것 중 ``연휴일수''는 기간과 순위 상관 0.207 이라 분모 정보를 조금
# 나른다(``주말몫''은 $-$0.005 로 안 나른다). 0.207 은 두고 보기로 한다.
KEEP = {
    "comp": "conditions.derived.competition.comp_within_1000m_open",
    "wkend": "conditions.derived.duration.weekend_share",
    "holid": "conditions.derived.duration.holiday_days",
    "stores": "conditions.scale.store_count",
}


def _get(o, path: str):
    for k in path.split("."):
        if not isinstance(o, dict):
            return None
        o = o.get(k)
    return o


def _pct(v: np.ndarray, ok: np.ndarray) -> np.ndarray:
    """관측된 값만으로 백분위를 매긴다 --- 결측이 0 으로 몰리지 않게.

    **동률은 평균 순위로 묶는다**(노트 292). 처음에 ``argsort(argsort())`` 로
    썼는데 그것은 동률을 **행 순서로** 깬다. ``prior_count`` 는 205행 중
    182행(89%)이 0 이고 행 순서가 ``MKT-YYYY-NNNN`` 이라 연도와 +0.864 다 ---
    그래서 값이 전부 같은 182행 안에서 축이 라벨과 +0.1371 이 나왔다.
    있지도 않은 정보를 축이 나르고 있었다. ``rankdata`` 는 동률에 같은 값을
    준다.
    """
    from scipy.stats import rankdata
    out = np.zeros(len(v), np.float32)
    if ok.sum() < 3:
        return out
    r = rankdata(v[ok]) - 1.0
    out[ok] = (r / max(ok.sum() - 1, 1)).astype(np.float32)
    # 만드는 자리에서 잡는다(노트 292) --- 백분위가 서로 다른 값의 수를
    # 늘렸다면 동률을 행 순서로 깬 것이다.
    n_in, n_out = len(np.unique(v[ok])), len(np.unique(out[ok]))
    if n_out != n_in:
        raise AssertionError(
            f"_pct 가 동률을 깼다: 입력 {n_in}가지 → 출력 {n_out}가지")
    return out


def build(root: str = ".", data=None) -> dict:
    """{축이름: {"팝업": (값, 표시자)}} --- 팝업 전용."""
    from .trendaxes import _ids
    ids_all = _ids()
    ids = ids_all.get("팝업")
    if not ids:
        return {}
    R = Path(root) / "data/records"
    recs = []
    for i in ids:
        p = R / f"{i}.json"
        recs.append(json.loads(p.read_text()) if p.exists() else {})
    out: dict = {}
    for nm, path in KEEP.items():
        raw = []
        for d in recs:
            v = _get(d, path)
            if isinstance(v, bool):
                v = float(v)
            raw.append(float(v) if isinstance(v, (int, float)) else np.nan)
        arr = np.asarray(raw, float)
        ok = np.isfinite(arr)
        if ok.sum() < 30 or len(np.unique(arr[ok])) < 3:
            continue
        out[f"pop_{nm}"] = {"팝업": (_pct(arr, ok), ok.astype(np.float32))}
    return out
