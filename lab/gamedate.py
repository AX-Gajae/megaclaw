# -*- coding: utf-8 -*-
# 예정일 입도 파서 — gameknock864.granularity 의 동결 사본(864 러너는 main 가드가 없어 import 금지)
import re

ENG = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def granularity(s):
    """예정일 원문 → (입도, 표준일 or None). 863 파서의 죽은 31행 제거 + 영어 월 처리."""
    s = str(s or "").strip()
    if not s:
        return "미정", None
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", s)
    if m:
        return "일", f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*,?\s+(\d{4})", s)
    if m and m.group(2).lower() in ENG:
        return "일", f"{m.group(3)}-{ENG[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),\s*(\d{4})", s)
    if m and m.group(1).lower() in ENG:
        return "일", f"{m.group(3)}-{ENG[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월(?!.*일)", s)
    if m:
        return "월", f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{4})", s)
    if m and m.group(1).lower() in ENG:
        return "월", f"{m.group(2)}-{ENG[m.group(1).lower()]:02d}"
    if re.search(r"분기|Q[1-4]", s):
        return "분기", None
    if re.search(r"\d{4}", s) and not re.search(r"월|일", s):
        return "연", None
    return "미정", None
