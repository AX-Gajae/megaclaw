# -*- coding: utf-8 -*-
"""997 관문 — 🔴 **가벼운 팔.** 두 산출물을 읽어 가족 보정·분모·분기를 «계산»한다.

사전등록 `docs/prereg_997_unsupervised_mde.md` §5.

🔴 **이 러너는 예측을 채점하지 않는다.** 기계가 셀 수 있는 것만 센다:
  · 다중비교 가족 `FC-997`(`m` 을 «측정 전»에 박았다) 의 Holm
  · 이 사이클이 낸 `cluster_se` 칸 «전량»(조항 79 개정 2)
  · 조항 78 ㉮·㉯ 분자 합
  · 🔴 분기 --- `MDE` 가 `ρ 0.1` 아래냐 `ρ 0.3+` 냐

🔴 **리터럴 금지**: 이 파일에는 `("...", True)` 꼴이 없다. 모든 판정은 산출물에서
읽어 «계산»한다. 산출물이 없으면 그 칸은 `None` 이고 통과가 «안» 된다.

산출: `runners/out997_gate.json`
사용: `python3 runners/mde997_gate.py`   (🔴 두 러너가 끝난 «뒤»)
"""
import collections
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import delta996_common as C                       # noqa: E402
import mde997_common as K                         # noqa: E402

OUT = Path(os.environ.get("M997_OUT", "")) if os.environ.get("M997_OUT") \
    else ROOT / "runners/out997_gate.json"
SRC = collections.OrderedDict([
    ("㉠ 라벨 프로브", "runners/out997_probe.json"),
    ("㉡ 라벨 0 개 자", "runners/out997_mask.json")])

#: 🔴🔴 다중비교 가족과 `m` --- **측정 «전»에 박았다**(조항 79 개정 1 · 995 가 안 했던 것)
FAMILY = "FC-997 · 997 이 «세계에 대해» 낸 헤드라인 대비 전량"
FAMILY_M = 8
FAMILY_MEMBERS = (
    "㉡ 학습−난수표현",
    "㉠ 전량 실측−난수표현(④)",
    "㉠ 전량 실측−라벨순열(⑤)",
    "㉠ k=8 실측−난수표현", "㉠ k=16 실측−난수표현", "㉠ k=32 실측−난수표현",
    "㉠ k=64 실측−난수표현", "㉠ k=128 실측−난수표현")
#: 🔴 `MDE` 자신은 «검정이 아니다» --- 가족에 «안» 넣는다. 검정력 계산이지 가설이 아니다
MDE_NOT_IN_FAMILY = ("`MDE` 는 기각 여부를 묻지 않는다. 가족 크기 m 에 «안» 센다.")


def _get(o, *path):
    for p in path:
        if not isinstance(o, dict) or p not in o:
            return None
        o = o[p]
    return o


def main():
    t0 = time.time()
    out = collections.OrderedDict()
    out["무엇"] = "997 관문 · 가족 보정 · 분모 · 분기 --- 🔴 예측 채점은 «안 한다»"
    out["🔴 다중비교 가족"] = collections.OrderedDict([
        ("가족", FAMILY), ("🔴 사전등록 m", FAMILY_M),
        ("구성원", list(FAMILY_MEMBERS)),
        ("🔴 m 이 맞나(구성원 수 == 사전등록 m)",
         bool(len(FAMILY_MEMBERS) == FAMILY_M)),
        ("🔴 `MDE` 를 가족에 안 넣는 까닭", MDE_NOT_IN_FAMILY)])

    got = collections.OrderedDict()
    for nm, rel in SRC.items():
        p = ROOT / rel
        got[nm] = collections.OrderedDict([
            ("파일", rel), ("있나", bool(p.exists())),
            ("sha256", C.sha_file(rel) if p.exists() else None),
            ("바이트", int(p.stat().st_size) if p.exists() else None)])
    out["산출물"] = got
    D = {}
    for nm, rel in SRC.items():
        p = ROOT / rel
        if p.exists():
            D[nm] = json.loads(p.read_text(encoding="utf-8"))

    # ── 가족 p 를 모아 Holm ───────────────────────────────────────────
    pairs = []
    pr = D.get("㉠ 라벨 프로브")
    mk = D.get("㉡ 라벨 0 개 자")
    if mk:
        pairs.append(("㉡ 학습−난수표현",
                      _get(mk, "🔴 헤드라인 대비 ㉡ = 학습 − 난수표현",
                           "🔴 양측 p(정규 근사)")))
    if pr:
        for lab, key in (("㉠ 전량 실측−난수표현(④)", "실측 − 난수 표현(④)"),
                         ("㉠ 전량 실측−라벨순열(⑤)", "실측 − 라벨 순열(⑤)")):
            pairs.append((lab, _get(pr, "🔴 헤드라인 대비 · 전량 라벨", key,
                                    "🔴 양측 p(정규 근사)")))
        for k in (8, 16, 32, 64, 128):
            pairs.append(("㉠ k=%d 실측−난수표현" % k,
                          _get(pr, "🔴🔴🔴 MDE (자 ㉠ · 소수 라벨)", "k=%d" % k,
                               "🔴 헤드라인 대비(실측 − 난수표현) · 등록된 자",
                               "🔴 양측 p(정규 근사)")))
    out["🔴 Holm(가족 FC-997)"] = C.holm(pairs, family=FAMILY) if pairs else \
        {"🔴 못 쟀다": "산출물이 없다"}
    out["🔴 가족이 다 모였나"] = collections.OrderedDict([
        ("🔴 사전등록 m", FAMILY_M), ("모인 p 수", len(pairs)),
        ("🔴 다 모였나", bool(len(pairs) == FAMILY_M)),
        ("🔴 안 모였으면", "Holm 은 «부분 가족»에 대한 것이고 그 사실을 판정문에 적어야 한다"
                     "(995 `F15` 가 정확히 이 병으로 반증됐다)")])

    # ── `cluster_se` 칸 «전량» 분모 (조항 79 개정 2) ─────────────────────
    tot = non = hit = nul = 0
    per = collections.OrderedDict()
    for nm, d in D.items():
        c = d.get("🔴 조항 79 개정 2 — cluster_se 칸 전량") or {}
        n = c.get("🔴🔴 분모: 이 주행이 낸 cluster_se 칸 전량")
        per[nm] = c
        if isinstance(n, int):
            tot += n
            hit += int(c.get("🔴 2·SE 를 넘은 칸") or 0)
            non += int(c.get("안 넘은 칸") or 0)
            nul += int(c.get("🔴 판정 불가 칸(SD=0 ⇒ SE=0 ⇒ None · ㉯-2)") or 0)
    out["🔴 조항 79 개정 2 — 이 사이클의 cluster_se 칸 전량"] = \
        collections.OrderedDict([
            ("분모: 전량", tot), ("2·SE 를 넘은 칸", hit), ("안 넘은 칸", non),
            ("판정 불가 칸", nul),
            ("넘은 비율", K._r(hit / tot, 4) if tot else None),
            ("러너별", per)])

    # ── 조항 78 ㉮·㉯ 분자 합 ────────────────────────────────────────
    a = b = cl = 0
    t78 = collections.OrderedDict()
    for nm, d in D.items():
        s = d.get("🔴🔴 조항 78 ㉮·㉯ (기계)") or {}
        t78[nm] = collections.OrderedDict(
            [(k, s.get(k)) for k in ("분모: 검사한 주장", "분모: 변이체",
                                     "🔴🔴 기계가 센 ㉮ 분자", "🔴🔴 기계가 센 ㉯ 분자",
                                     "🔴 대조 ㉮ 분자", "🔴 대조 ㉯ 분자")])
        a += int(s.get("🔴🔴 기계가 센 ㉮ 분자") or 0)
        b += int(s.get("🔴🔴 기계가 센 ㉯ 분자") or 0)
        cl += int(s.get("분모: 검사한 주장") or 0)
    out["🔴🔴 조항 78 ㉮·㉯ 합(기계)"] = collections.OrderedDict([
        ("분모: 검사한 주장 합", cl), ("🔴 ㉮ 분자 합", a), ("🔴 ㉯ 분자 합", b),
        ("🔴 둘 다 0 인가", bool(cl > 0 and a == 0 and b == 0)),
        ("🔴 0 이 아니면", "그 조각을 최상위 연언에서 «뺀다»(조항 78-2)"),
        ("러너별", t78)])

    # ── 🔴🔴🔴 분기 ─────────────────────────────────────────────────
    def _mde(d, *path):
        return _get(d, *path, "🔴🔴 MDE_s", "🔴 ㉠ 2·SE(헤드라인)", "MDE_s(선형 보간)")

    m_a = _mde(pr, "🔴🔴🔴 MDE (자 ㉠ · 전량 라벨)") if pr else None
    m_a16 = _get(pr, "🔴🔴🔴 MDE (자 ㉠ · 소수 라벨)", "k=16", "🔴🔴 MDE",
                 "🔴 ㉠ 2·SE(헤드라인)", "MDE_s(선형 보간)") if pr else None
    m_b = _mde(mk, "🔴🔴🔴 MDE (자 ㉡ · 라벨 0 개 자)") if mk else None
    out["🔴🔴🔴 MDE 표 — 997 의 유일한 필수 산출"] = collections.OrderedDict([
        ("㉠ 라벨 프로브 · 전량 라벨", K._r(m_a) if m_a is not None else None),
        ("㉠ 라벨 프로브 · k=16(915 의 자리)",
         K._r(m_a16) if m_a16 is not None else None),
        ("🔴 ㉡ 라벨 0 개 자(가림 복원)", K._r(m_b) if m_b is not None else None),
        ("🔴 ㉡ 가 ㉠ 보다 작나", bool(m_b is not None and m_a is not None
                                and m_b < m_a)),
        ("🔴 배수 ㉠/㉡", K._r(m_a / m_b) if (m_a and m_b) else None),
        ("분기 · ㉠ 전량", K.branch(m_a)), ("분기 · ㉠ k=16", K.branch(m_a16)),
        ("🔴 분기 · ㉡", K.branch(m_b))])
    out["🔴🔴 915 의 차를 잴 수 있었나"] = _get(
        pr, "🔴🔴🔴 MDE (자 ㉠ · 소수 라벨)", "k=16",
        "🔴🔴 915 의 차(0.1719 − 0.1708 = 0.0011)를 잴 수 있었나") if pr else None
    out["🔴 라벨 0 비트 증거(자 ㉡)"] = collections.OrderedDict([
        ("라벨 순열이 «글자 그대로» 같은가",
         _get(mk, "🔴🔴 바닥 ⑤ 라벨 순열 (자 ㉡ · 라벨 0 비트)",
              "🔴🔴 글자 그대로 같은가(=라벨 비트 0)") if mk else None),
        ("누출 대조판이 «달라졌나»(같은 격자에서 반대를 낸다)",
         _get(mk, "🔴🔴 라벨 누출 대조판 (같은 격자 · 라벨을 «입력열»로 넣었다)",
              "🔴🔴 대조가 뒤집혔나(누출판은 달라야 한다)") if mk else None)])
    out.update(K.stamp(t0))
    h = K.json_dump(OUT, out)
    print("→ %s  sha256 %s" % (OUT, h[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
