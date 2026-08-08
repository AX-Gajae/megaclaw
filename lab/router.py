# -*- coding: utf-8 -*-
"""서빙 라우터 가드(노트 859 부수 · 티처 #20~22 — 측정 가설 없는 가드 코드).

규약(855 확정 · 854): 신규(판 밖) 행의 predict 는 **무정체 + names 명시 등록**.
판 밖 행에 '만화' 정체 부여 금지(−0.136 실측 · 854). 서빙 배치 = 짝 단독.

    identity, names = route(data, "KR 만화")        # → ("NL_KR 만화", 만화 이름)
    route(data, "KR 만화", force_identity="만화")   # → ValueError(금지)
"""
from __future__ import annotations

FORBIDDEN_OOP = {"만화"}          # 판 밖 행에 금지된 정체(854 격자 실측)


def route(data, pair_name: str, force_identity: str | None = None):
    """짝 이름 → (정체, names). 무정체 기본값 · names 등록 의무(폴백 지뢰 차단)."""
    try:
        from lab.pairs import SRC_DOM
    except ImportError:
        from .pairs import SRC_DOM

    if force_identity is not None:
        if force_identity in FORBIDDEN_OOP:
            raise ValueError(f"판 밖 행에 '{force_identity}' 정체 부여 금지(854 · −0.136)")
        if force_identity not in data.dom:
            raise ValueError(f"미등록 정체 {force_identity}")
        return force_identity, list(data.names[force_identity])
    src = SRC_DOM.get(pair_name)
    if src is None or src not in data.names:
        raise ValueError(f"짝 {pair_name} 의 축 원천 도메인을 모른다 — 등록 후 서빙(폴백 금지)")
    ident = f"NL_{pair_name}"
    data.names[ident] = list(data.names[src])       # 명시 등록(855 규약 ② — _feat ALL5 폴백 차단)
    return ident, data.names[ident]


def _selftest():
    class _D:
        dom = {"만화": None}
        names = {"만화": ["target_breadth", "venue_prominence"]}
    d = _D()
    ident, names = route(d, "KR 만화")
    assert ident == "NL_KR 만화" and d.names[ident] == d.names["만화"]
    try:
        route(d, "KR 만화", force_identity="만화")
        raise AssertionError("만화 금지 미작동")
    except ValueError:
        pass
    try:
        route(d, "미지의 짝")
        raise AssertionError("미등록 짝 가드 미작동")
    except ValueError:
        pass
    print("router selftest 통과")


if __name__ == "__main__":
    _selftest()
