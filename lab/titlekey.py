# -*- coding: utf-8 -*-
# 제목 매처 v1(노트 874 · 820/825 의 언어-정합) — exact 정규형에 **대체 제목 확장**을 더한다.
# 세계애니(AniList)는 title/native/english/synonyms 전부의 정규형 집합을 키로 낸다 —
# synonyms 에 한글 제목이 실재('주술회전' 등 · 874 배선 실측)해 라프텔(한글)과 접합된다.
# norm 은 ipctl825.norm 과 동일식(소문자·괄호 제거·기호 제거) — 자 비교성 유지.
import re


def norm(s: str) -> str:
    s = str(s or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(r"[^0-9a-z가-힣]+", "", s)
    return s


def keys_of(rec: dict) -> set:
    """레코드 하나의 제목 키 집합 — 있는 필드만 쓴다(v1: title·native·english·synonyms·name)."""
    out = set()
    for f in ("title", "native", "english", "name"):
        k = norm(rec.get(f))
        if k:
            out.add(k)
    for s in rec.get("synonyms") or []:
        k = norm(s)
        if k:
            out.add(k)
    return out
