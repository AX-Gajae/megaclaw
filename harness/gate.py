"""자극 빈곤 게이트 — 프레임워크 레벨 캘리브레이션 강제.

배경(2026-07-24, rolling-v5): 자극 빈약 폴드에서 모델이 구간을 넓히지 않아 커버리지가
9/9(자극 풍부) → 8/20(빈곤)으로 붕괴. 뱅크 앵커가 많을수록 '아는 것 같은 착각'으로
좁게 찍는 과신이 관측됨. 따라서 "모른다" 출력을 모델 재량이 아니라 시스템 규칙으로 강제한다.

판정 3단:
  pass   — 자극 두께 충분: 예측 그대로 봉인
  widen  — 빈곤: 구간을 point 기준 [point/F, point*F]까지 강제 확대 (F=WIDEN_FACTOR)
  refuse — 사실상 정보 없음: 예측 자체를 거부 (봉인 안 함)

WIDEN_FACTOR=4.5 근거: rolling-v5 빈곤 19폴드의 max(actual/point, point/actual) 80분위 = 4.42
→ 4.5로 커버리지 16/19(84%) — 80% 구간 계약을 빈곤 레짐에서도 복원하는 최소 배율.
"""
from __future__ import annotations

import json

WIDEN_FACTOR = 4.5
PASS_MIN_LEN = 1200   # 원 9폴드(전부 커버 적중)의 자극 길이 하한이 1,397자
REFUSE_MAX_LEN = 450  # 이하이면 스키마 뼈대 수준 — 개입 정보 부재

THIN_MARKERS = ("추정되나", "문서 없음", "확인할 수 없", "제공되지 않아", "내용 없", "확인 불가")

INTERVAL_FIELDS = [("stage1_gross", "gross_consumer_sales_krw"), ("stage1_gross", "visitors_total"),
                   ("totals", "visitors"), ("totals", "sales_krw"), ("totals", "rev_mm_recognized")]


def assess(stimulus: dict) -> dict:
    """자극 두께 판정. 반환: {level, stim_len, thin_markers, reasons}"""
    blob = json.dumps({"intervention": stimulus.get("intervention"),
                       "conditions": stimulus.get("conditions")}, ensure_ascii=False)
    stim_len = len(blob)
    markers = [m for m in THIN_MARKERS if m in blob]
    concept = (stimulus.get("intervention") or {}).get("concept")

    reasons = []
    if not concept or stim_len < REFUSE_MAX_LEN:
        level = "refuse"
        reasons.append(f"개입 정보 부재 (concept={'없음' if not concept else '있음'}, 자극 {stim_len}자)")
    elif stim_len >= PASS_MIN_LEN and not markers:
        level = "pass"
        reasons.append(f"자극 {stim_len}자 ≥ {PASS_MIN_LEN}, 빈약마커 0")
    else:
        level = "widen"
        if stim_len < PASS_MIN_LEN:
            reasons.append(f"자극 {stim_len}자 < {PASS_MIN_LEN}")
        if markers:
            reasons.append(f"빈약마커 {len(markers)}개: {','.join(markers[:3])}")

    return {"level": level, "stim_len": stim_len, "thin_markers": markers, "reasons": reasons}


def widen(prediction: dict, factor: float = WIDEN_FACTOR) -> dict:
    """구간을 point 기준 [point/F, point*F]까지 강제 확대 (기존 구간이 더 넓으면 유지)."""
    for sec, key in INTERVAL_FIELDS:
        iv = (prediction.get(sec) or {}).get(key)
        if not iv or iv.get("point") is None:
            continue
        p = iv["point"]
        if p <= 0:
            continue
        lo, hi = p / factor, p * factor
        if iv.get("low") is None or iv["low"] > lo:
            iv["low"] = round(lo, 2) if lo < 10 else round(lo)
        if iv.get("high") is None or iv["high"] < hi:
            iv["high"] = round(hi, 2) if hi < 10 else round(hi)
    return prediction
