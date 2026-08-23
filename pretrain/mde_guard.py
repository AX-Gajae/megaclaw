# -*- coding: utf-8 -*-
"""게이트 MDE(최소검출효과) 관문 — 등록문의 MDE 칸 기계 검사 (루프 부칙 6 · 티처 #144 발의).

왜 있는가(#144 ③·④·⑤ 실측): 의무의 원형은 v3.3 ⓪-가 「검출력 줄」(루프.md:1203 — «이 표본에서
이 자가 가를 수 있는 최소 효과는 얼마인가? 그 수를 여기 적어라 … 못 채우면 측정 단계로 안
넘어간다»)로 이미 있었으나, 파운데이션기 998~1011 열네 사이클의 사전등록에 이 줄이 **0회**
(grep) — 서식·집행에서 소멸했다. 그 결과: 검출한계가 시도 효과의 3.5배인 게이트(① 2SE 한계
상대 31.7% 대 시도 최대 9.9%)와 검정력 아닌 상수에서 온 확충 문턱(21 = 30−9 · 조항 66 형)이
«정직한 null» 을 낳았다 — **MDE 칸 없는 null 사슬은 「세계의 답」과 「자의 눈멂」을 못 가른다.**

규격(부칙 6):
  ㉮ [판정] 레인 사전등록은 게이트마다 「MDE = 2×max(SE_판정눈금, J)」를 **수로** 적는다 —
     SE 는 판정에 쓸 눈금(클러스터 눈금이 등록됐으면 클러스터 SE)으로, 직전 판 JSON·지터표의
     sha 인용으로 낸다(조항 66). 나란히 「겨냥 효과 크기」와 그 출처를 적는다.
  ㉯ 겨냥 효과 < MDE 인 게이트는 [판정] 레인에 못 세운다 — «자 수리» 선등록 또는 [탐색]·관찰
     강등. 「그래도 측정은 돌려 봤다」는 금지다.
  ㉰ 러너 시작 관문(v5.3-2 방향 탐침 자리): 칸 부재 / 산식 입력 sha 불일치 / 겨냥<MDE —
     하나면 **측정 없이 중단**(값을 보고 자를 고르는 길을 원리상 막는다).
  ㉱ null 판정문은 「효과 없음」이 아니라 「MDE(수) 미만」으로 적는다.
  ㉲ SE 정의가 서지 않는 정수 자(③ 승수)는 「±1 이동의 SD 환산」을 판 JSON 에 병기한다.

씀:  from pretrain.mde_guard import assert_mde, mde_of, MdeMissing, MdeUnderpowered
     mde = mde_of(se=0.056, jitter=0.0302)              # ㉮ 산식: 2×max(SE, J)
     stamp = assert_mde(mde, 겨냥효과, "5bcdd8f26b1520b8")  # 관문 — 어긋나면 측정 없이 중단
     out["MDE(부칙 6)"] = stamp                          # 게재는 실측 반환값으로(부칙 4 ㉯ 미러)

부호는 여기서 안 본다 — 방향(악화/개선)은 v5.3 게이트 부호 서명 몫이고, 이 관문은 «크기»만
대조한다(겨냥 효과는 절대값으로). torch·numpy 무의존 — 언 러너도 그대로 임포트한다.

자기시험: python3 pretrain/mde_guard.py   (참/거짓 양쪽 + 칸 부재·출처 부재·비수치)
"""
import math
import re
import time

_SHA_RE = re.compile(r"^[0-9a-f]{16,64}$")


class MdeGateError(RuntimeError):
    """부칙 6 관문 공통 밑동 — 측정 없이 중단 규격."""


class MdeMissing(MdeGateError):
    """MDE 칸 부재(수 아님·비유한·출처 sha 부재) — 등록 결함, 측정 없이 중단."""


class MdeUnderpowered(MdeGateError):
    """겨냥 효과 < MDE — 이 게이트는 [판정] 레인에 못 선다(부칙 6 ㉯)."""


def _num(x, name):
    """수 검사 — bool·None·NaN·inf 는 «칸 부재»다(조용한 통과 금지 · 조항 59)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise MdeMissing(
            "🔴 MDE 칸 부재 — %s 가 수가 아니다(%r) — 측정 없이 중단 · [판정] 레인 금지 (부칙 6)"
            % (name, x))
    if not math.isfinite(float(x)):
        raise MdeMissing(
            "🔴 MDE 칸 부재 — %s 가 유한한 수가 아니다(%r) — 측정 없이 중단 · [판정] 레인 금지 (부칙 6)"
            % (name, x))
    return float(x)


def mde_of(se, jitter):
    """부칙 6 ㉮ 산식 — MDE = 2×max(SE_판정눈금, J). 입력은 양의 유한수여야 한다."""
    se = _num(se, "SE_판정눈금")
    j = _num(jitter, "지터 J")
    if se <= 0 or j < 0:
        raise MdeMissing(
            "🔴 MDE 산식 입력 결함 — SE=%r · J=%r (SE 는 양수 · J 는 0 이상) — 측정 없이 중단 (부칙 6)"
            % (se, j))
    return 2.0 * max(se, j)


def assert_mde(mde, aim, source_sha):
    """부칙 6 관문 — 등록문의 MDE 칸을 «측정 전에» 검사한다.

    mde: 등록된 MDE 수(㉮ 산식 2×max(SE,J) 로 낸 값) · aim: 겨냥 효과 크기(가설이 참일 때
    기대하는 Δ — 부호는 v5.3 부호 서명 몫이라 절대값으로 대조) · source_sha: MDE 산식 입력
    (SE·J)을 낸 판 JSON·지터표의 sha(sha256/16 이상 · 조항 66 — 출처를 못 대는 자는 자가 아니다).

    어긋나면 예외로 **측정 없이 중단**(값을 보고 자를 고르는 길을 원리상 막는다):
      · 칸 부재(수 아님·비유한·출처 sha 부재/비정형) → MdeMissing
      · |겨냥 효과| < MDE → MdeUnderpowered — 「[판정] 레인 금지」(㉯: 자 수리 선등록 또는 강등)

    통과 시 게재용 실측 스탬프 반환(게재는 등록 상수가 아니라 이 반환값으로 — 부칙 4 ㉯ 미러):
      {"MDE", "겨냥 효과", "여유"(= |겨냥| − MDE · 양수), "눈금 출처 sha", "잰 시각"}
    """
    m = _num(mde, "MDE")
    a = abs(_num(aim, "겨냥 효과"))
    if m <= 0:
        raise MdeMissing(
            "🔴 MDE 칸 부재 — MDE=%r (양수 아님) — 측정 없이 중단 · [판정] 레인 금지 (부칙 6)" % mde)
    if not isinstance(source_sha, str) or not _SHA_RE.match(source_sha.strip().lower()):
        raise MdeMissing(
            "🔴 MDE 눈금 출처 부재 — sha=%r (판 JSON·지터표 sha256/16 인용 의무 · 조항 66) — "
            "측정 없이 중단 · [판정] 레인 금지 (부칙 6)" % (source_sha,))
    if a < m:
        raise MdeUnderpowered(
            "🔴 겨냥 효과 %.6g < MDE %.6g (부족 %.6g) — 측정 없이 중단 · [판정] 레인 금지 "
            "(부칙 6 ㉯: 표본·눈금을 늘리는 «자 수리»를 먼저 등록하거나 [탐색]·관찰 칸으로 "
            "강등하라 · 「그래도 측정은 돌려 봤다」는 금지)" % (a, m, m - a))
    return {"MDE": m, "겨냥 효과": a, "여유": a - m,
            "눈금 출처 sha": source_sha.strip().lower(),
            "잰 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}


if __name__ == "__main__":
    import json
    결함 = 0

    # ① 참 쪽 — 1012 실물값 형: 겨냥 +0.0270 · 전체-오차 눈금 SE^cl 0.0043 · J 미만 가정 0.004
    m = mde_of(0.0043, 0.004)                      # = 2×0.0043 = 0.0086
    if abs(m - 0.0086) > 1e-12:
        print("🔴 결함 — mde_of 산식: %r ≠ 0.0086" % m); 결함 += 1
    stamp = assert_mde(m, 0.0270, "5bcdd8f26b1520b8")
    print("참 쪽 통과:", json.dumps(stamp, ensure_ascii=False))
    if stamp["여유"] <= 0:
        print("🔴 결함 — 참 쪽 여유가 양수가 아니다"); 결함 += 1

    # ② 거짓 쪽 — 겨냥 < MDE (① 게이트 실형: MDE 상대 31.7% 대 시도 최대 9.9%)
    try:
        assert_mde(0.317, 0.099, "5bcdd8f26b1520b8")
    except MdeUnderpowered as e:
        print("거짓 쪽(겨냥<MDE) 예외 OK:", e)
    else:
        print("🔴 결함 — 겨냥<MDE 인데 예외가 안 났다"); 결함 += 1

    # ③ 칸 부재 — MDE 가 수가 아니다
    for bad in (None, "0.01", float("nan"), True, 0.0, -0.01):
        try:
            assert_mde(bad, 0.027, "5bcdd8f26b1520b8")
        except MdeMissing:
            pass
        else:
            print("🔴 결함 — MDE=%r 인데 예외가 안 났다" % (bad,)); 결함 += 1
    print("칸 부재(MDE 비수치·비양수) 예외 OK: 6형")

    # ④ 출처 부재 — sha 없음·비정형
    for bad in (None, "", "판JSON", "xyz", "5bcd"):
        try:
            assert_mde(0.0086, 0.027, bad)
        except MdeMissing:
            pass
        else:
            print("🔴 결함 — sha=%r 인데 예외가 안 났다" % (bad,)); 결함 += 1
    print("출처 부재(sha 결측·비정형) 예외 OK: 5형")

    # ⑤ 겨냥 효과 칸 부재
    try:
        assert_mde(0.0086, None, "5bcdd8f26b1520b8")
    except MdeMissing as e:
        print("겨냥 칸 부재 예외 OK:", e)
    else:
        print("🔴 결함 — 겨냥=None 인데 예외가 안 났다"); 결함 += 1

    # ⑥ 산식 입력 결함 — SE 0 이하
    try:
        mde_of(0.0, 0.01)
    except MdeMissing as e:
        print("산식 입력 결함 예외 OK:", e)
    else:
        print("🔴 결함 — SE=0 인데 예외가 안 났다"); 결함 += 1

    if 결함:
        print("🔴 자기시험 실패 — 결함 %d" % 결함)
        raise SystemExit(1)
    print("부칙 6 자기시험 통과 (참/거짓 양쪽 + 칸 부재·출처 부재·비수치)")
