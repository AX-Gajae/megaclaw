"""집 밖 짝 --- **판이 한 줄도 안 본 행**을 만든다(노트 683).

노트 683 이 찾은 것: 규약은 채택에 **다섯 자**를 요구하는데 그중 넷의 채점기가
저장소에 없었다. 숫자는 ``lab/sideaudit.SENS`` 에 있고 자료도 있는데 **계산하는
함수가 없었다** --- 노트 583/586 채택 커밋이 KR 0.684 · 앱 0.505 를 적었으면서
건드린 파일은 ``forms.py``·``loop.py`` 뿐이었다.

**그런데 새 코드가 거의 필요 없었다.** 짝의 정의가 기존 빌더의 매개변수다:

    KR 만화     ``ingest/manga_axes`` 의 ``KEEP_COUNTRY=("KR",)``   → **1,716행**
    CN 만화     같은 빌더 ``KEEP_COUNTRY=("CN",)``                  → **352행**
    비게임 앱   ``ingest/mobile_axes`` 의 ``SRC=app_records.json``  → **1,600행**

세 수가 **기록과 정확히 일치한다**(노트 683 받아들임 시험 ①). 그리고 판의 만화
도메인은 ``KEEP_COUNTRY=("JP",)`` 로 5,905행이므로 **KR·CN 은 판에서 통째로
빠져 있다** --- 그래서 '집 밖' 이고, 채점은 L2 전이다.

**축 파일을 새로 저장하지 않는다.** 몇 초면 다시 만들 수 있는 파생물이고, 파일로
두면 낡는다(노트 672 가 낡은 숫자로 잡은 자리 · 노트 669 가 자료 성장으로 R² 가
0.1639 → 0.1098 이 된 것을 쟀다). **부를 때 만든다.**

.. warning::

   **아직 채점기가 아니다.** 이 모듈은 짝의 *행과 축* 까지만 만든다. 기준선
   (KR $+0.6841$ · 앱 $+0.5053$ · CN $+0.3094$)을 재현하는 것이 노트 683 의
   받아들임 시험 ②이고 **그것을 통과하기 전에는 채택에 쓰지 않는다.**

   미리 아는 위험 하나 --- **짝의 축 집합이 판과 다르다.** CN 은 이 빌더에서
   ``entry_friction`` 이 상수라 강등된다. 노트 577 이 *'집 밖 짝은 ALL5 축만
   갖는다'* 고 적은 것이 이 이야기이고, **그 차이가 기준선을 못 맞추는 첫
   후보다**(노트 683 예측).
"""
from __future__ import annotations

from pathlib import Path

#: 짝 이름 → (빌더 모듈, 덮어쓸 속성, 기대 행수). 행수는 **받아들임 시험 ①** 이다.
PAIRS = {
    "KR 만화": ("ingest.manga_axes", {"KEEP_COUNTRY": ("KR",)}, 1716),
    "CN 만화": ("ingest.manga_axes", {"KEEP_COUNTRY": ("CN",)}, 352),
    "비게임 앱": ("ingest.mobile_axes",
                {"SRC": Path("data/state/app_records.json")}, 1600),
}


def build(name: str, check: bool = True) -> dict:
    """짝 이름 → ``{record_id: {axes, mask, y, ...}}``.

    **기존 빌더를 그대로 부른다.** 축 유도 코드를 새로 쓰면 판과 다른 축이
    되고, 그러면 기준선과 견줄 수 없다(노트 579·580 분모 조항).
    """
    import importlib
    mod_name, over, want = PAIRS[name]
    mod = importlib.import_module(mod_name)
    old = {k: getattr(mod, k) for k in over}
    for k, v in over.items():
        setattr(mod, k, v)
    try:
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):     # 빌더가 표를 찍는다
            rows = mod.run(write=False)
    finally:
        for k, v in old.items():
            setattr(mod, k, v)
    if check and len(rows) != want:
        raise AssertionError(
            f"{name}: 행수 {len(rows)} 인데 기록은 {want} --- "
            "**새 자로 취급하고 기록된 숫자와 견주지 않는다**(노트 683 시험 ①)")
    return rows


def counts() -> dict:
    """받아들임 시험 ① 만 빠르게 --- 채점 없이 행수만."""
    out = {}
    for nm in PAIRS:
        try:
            out[nm] = {"행": len(build(nm, check=False)), "기대": PAIRS[nm][2]}
            out[nm]["맞나"] = out[nm]["행"] == out[nm]["기대"]
        except Exception as e:
            out[nm] = {"오류": f"{type(e).__name__}: {e}"}
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(counts(), ensure_ascii=False, indent=1))


#: 짝 → **판의 어느 도메인으로 취급하나.** 전이는 *그 도메인의 모형으로 이 행을
#: 본다* 는 뜻이므로 원천 도메인을 지정해야 한다.
SRC_DOM = {"KR 만화": "만화", "CN 만화": "만화", "비게임 앱": "모바일"}

#: **받아들임 시험 ②** --- 노트 586 씨앗 40 의 챔피언 기준선(노트 683).
#: 이 값을 씨앗 잡음 안에서 재현해야 기록과 견줄 수 있다.
#: 🔴 **CN 은 `None` 이다 --- 재현 가능한 기준선이 없다**(규약 44 · 노트 796).
#:
#: 옛 값 0.3094 는 노트 577(채택 전)에서 왔고 KR·앱은 노트 586(채택 후)에서
#: 왔다 --- **한 표에 두 시점이 섞여 있었다**(노트 794). 그리고 노트 796 이
#: 채택 스위치 둘(OOC_DROP·orient)을 되돌려 봤는데 **CN 은 거의 안 움직였다**
#: (0.3872 → 0.3927). 즉 0.3094 와의 격차 0.078 은 채택 탓이 아니라 노트 577
#: 이후의 **재구성 불가능한 파이프라인/자료 드리프트**다(앱도 되돌림에서
#: 0.1148 이 나와 0.2895 를 크게 벗어났다 --- 그 시점 자체를 복원할 수 없다).
#:
#: 빈 칸은 "안 쟀다" 를 말하고 옛 값은 "쟀는데 이 값이다" 를 말한다. 둘이
#: 다르다 --- CN 에 값을 다시 적으려면 **씨앗 폭을 단 새 측정**(아래
#: `MEASURED`)에서 새 채택이 그것을 갱신해야 한다.
BASELINE = {"KR 만화": 0.6841, "비게임 앱": 0.5053, "CN 만화": None}

#: 채택 절차 밖에서 잰 참고값 --- **시험 ② 의 자로 쓰지 않는다.**
#: (노트 793 · 씨앗 12 · 판 적합 공유 · SD 는 씨앗 SD)
MEASURED = {"KR 만화": (0.6850, 0.0076), "비게임 앱": (0.4916, 0.0069),
            "CN 만화": (0.3872, 0.0066)}


#: `state/tri_domain.ASOF` 와 **같은 값이어야 한다** --- 경과일수의 기준점이다.
ASOF = None      # `to_arrays` 가 처음 불릴 때 tri_domain 에서 가져온다


def to_arrays(rows: dict, names: list):
    """짝 행 → ``(A, M, y, t)``. **열 순서를 판의 도메인과 똑같이 맞춘다.**

    짝은 ALL5 축만 갖는다(노트 577). 나머지 열은 **0.5 · 마스크 0** 으로 둔다 ---
    ``_idol`` 이 없는 값에 하는 것과 같은 처리다(노트 326: 마스크 0 을 한쪽에만
    주면 그 표시자가 곧 기준이 되므로, **전 행에 같게** 준다).
    """
    import numpy as np
    from datetime import date
    global ASOF
    if ASOF is None:                      # **한 군데서만 정의한다**(노트 359)
        from state.tri_domain import ASOF as _A
        ASOF = _A
    n, m = len(rows), len(names)
    idx = {nm: i for i, nm in enumerate(names)}
    A = np.full((n, m), 0.5, float)
    M = np.zeros((n, m), float)
    y = np.full(n, np.nan)
    t = np.full(n, np.nan)
    for i, r in enumerate(rows.values()):
        for a, v in (r.get("axes") or {}).items():
            j = idx.get(a)
            if j is None:
                continue
            A[i, j] = float(v)
            M[i, j] = float((r.get("mask") or {}).get(a, 1.0))
        try:
            y[i] = float(r["y"])
        except Exception:
            pass
        # **`t` 는 연도가 아니라 `log10(경과일수)` 다**(노트 684 사각 ①이 실재했다).
        # `state/tri_domain._from_axes_json` 이 만화·모바일을 `trend="elapsed"` 로
        # 만든다 --- 연+월/12 로 넣으면 `harness.years()` 가 그것을 **연도로**
        # 읽어(>1000 판정) 판과 다른 자를 쓰게 된다. 같은 상수·같은 식을 쓴다.
        d = str(r.get("start_date") or r.get("release_date") or "")[:10]
        try:
            dd = (ASOF - date(*map(int, d.split("-")))).days
            t[i] = float(np.log10(max(dd, 1)))
        except (ValueError, TypeError):
            pass
    return A, M, y, t


def score(name: str, data=None, T: float = 2025.0, seeds=(0, 1, 2),
          form: str = "F18_bagboost") -> dict:
    """짝 rho --- **판을 적합하고 짝 행에 예측한다**(노트 683 시험 ②).

    짝 행은 판에 한 줄도 없으므로 이것은 L2 전이다. 씨앗을 갈아 평균한다
    (노트 146: 씨앗은 성가신 모수이고 판정치에 남길 이유가 없다).
    """
    import numpy as np
    from scipy.stats import spearmanr
    from . import forms, guards as G
    if data is None:
        from .sideaudit import champion_data
        data = champion_data()
    src = SRC_DOM[name]
    names = list(data.names.get(src) or [])
    if not names:
        return {"오류": f"판에 {src} 도메인이 없다"}
    rows = build(name)                       # 행수 불일치면 예외(시험 ①)
    A, M, y, t = to_arrays(rows, names)
    ok = np.isfinite(y)
    cls = forms.REGISTRY[form]["cls"]
    rs, cov = [], float(M.mean())
    for s in seeds:
        f = G._fit_on(lambda s=s: cls(seed=s), data, T, seed=s)
        p = np.asarray(f.predict(src, A, M, t), float)
        k = ok & np.isfinite(p)
        if k.sum() < 40 or len(np.unique(p[k])) < 3:
            continue
        rs.append(float(spearmanr(p[k], y[k]).statistic))
    if not rs:
        return {"오류": "예측이 상수이거나 표본 부족"}
    r = float(np.mean(rs))
    base = BASELINE.get(name)
    return {"짝": name, "원천 도메인": src, "행": len(rows),
            "rho": round(r, 4), "씨앗별": [round(x, 4) for x in rs],
            "씨앗SD": round(float(np.std(rs, ddof=1)), 4) if len(rs) > 1 else None,
            "**기록된 기준선**": base,
            "차": round(r - base, 4) if base is not None else None,
            "마스크 평균(축 덮음)": round(cov, 3),
            "**시험 ② 판정**": None if base is None else
            ("맞는다" if abs(r - base) <= 0.02 else
             "**어긋난다 — 새 자로 취급한다**(노트 579·580)")}
