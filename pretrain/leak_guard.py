# -*- coding: utf-8 -*-
"""L0-3 누수 관문 — «as_of 에 알 수 있었던 것»만 입력이게 하는 코드 관문.

정본: docs/아키텍처_결정기.md (커밋 b32e7eb5f) §L0.
  · 원칙 1(시점 정합): 모든 산출물은 as_of 를 갖고 그 시각에 «알 수 있었던 것»만으로 계산.
    코드 관문: `assert max(input.published_at) < as_of`.
  · L0-3: `assert_no_leak(inputs, as_of, tag)` — 사후 입력 있으면 **측정 없이 중단** ·
    통과 시 반환 스탬프 게재(부칙 4 미러 — 등록 상수가 아니라 «실측 반환값»을 게재한다).

판정 규칙(사이클 1015 사전등록 docs/탐색/1015.md §1):
  · published_at 이 **None** 이거나 **파싱 불능**이면 — «as_of 이전임을 증명 못 한» 입력이다.
    조용히 거르지 않고 **누수로 중단**한다(조항 59 — 결측을 0 으로 채우는 길을 원리상 막는다).
  · 비교는 **날 해상도** — published_at == as_of 날짜(같은 날)도 누수다(보수 쪽).
  · 빈 입력(n=0)은 통과다 — 막을 사후 입력이 없다. 스탬프에 n_입력=0 이 실측으로 남는다.

씀:  from pretrain.leak_guard import assert_no_leak, LeakDetected
     stamp = assert_no_leak(rows, "2024-01-01", tag="L1-4 상태벡터")   # rows: {"id":…, "published_at":"YYYY-MM-DD"}
     out["누수관문(L0-3)"] = stamp                                      # 게재는 실측 반환값으로

자기시험: python3 pretrain/leak_guard.py   →  참/거짓 5경우 JSON (전부 «기대대로»여야 0 종료)
"""
import datetime as _dt
import hashlib
import json
import os
import re
import sys

_ISO_D = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


class LeakDetected(RuntimeError):
    """사후(또는 발행일 미상) 입력 — «측정 없이 중단» 규격."""


def _self_sha16():
    try:
        with open(os.path.abspath(__file__), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return None


def _to_date(v):
    """ISO 문자열('YYYY-MM-DD' 또는 'YYYY-MM-DDT…')·date·datetime → date. 못 읽으면 None."""
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    if isinstance(v, str):
        m = _ISO_D.match(v.strip())
        if m:
            try:
                return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
    return None


def assert_no_leak(inputs, as_of, tag):
    """L0-3 누수 관문.

    inputs : iterable of dict — 각 원소는 "published_at"(ISO 날짜 문자열/date) 필수,
             "id" 는 있으면 위반 예시 게재에 쓴다.
    as_of  : ISO 날짜 문자열/date/datetime — 이 «날» 이후(같은 날 포함) 발행이면 누수.
    tag    : 어느 계산의 입구인지 (예: "L1-4 상태벡터 t=2024-01-01").

    통과 → 스탬프 dict(실측값) 반환. 위반 → LeakDetected (측정 없이 중단).
    """
    as_of_d = _to_date(as_of)
    if as_of_d is None:
        raise LeakDetected("«측정 없이 중단» — L0-3(tag=%s): as_of 자체를 날짜로 못 읽었다: %r" % (tag, as_of))
    n = 0
    max_pub = None
    bad_post, bad_null = [], []          # (id, published_at)
    for row in inputs:
        n += 1
        rid = row.get("id") if isinstance(row, dict) else None
        pub_raw = row.get("published_at") if isinstance(row, dict) else None
        pub = _to_date(pub_raw)
        if pub is None:
            if len(bad_null) < 3:
                bad_null.append((rid, pub_raw))
            continue
        if max_pub is None or pub > max_pub:
            max_pub = pub
        if pub >= as_of_d:
            if len(bad_post) < 3:
                bad_post.append((rid, pub.isoformat()))
    if bad_post or bad_null:
        raise LeakDetected(
            "«측정 없이 중단» — L0-3 누수(tag=%s): as_of=%s · n_입력=%d · "
            "사후(≥as_of) 예시=%s · 발행일_미상(null/파싱불능) 예시=%s "
            "(예시는 각 3건 상한 — 존재 자체가 중단 사유다)"
            % (tag, as_of_d.isoformat(), n, bad_post or "없음", bad_null or "없음"))
    return {
        "관문": "L0-3",
        "검사": "max(published_at) < as_of (날 해상도 · 같은 날=누수 · null=누수)",
        "tag": tag,
        "as_of": as_of_d.isoformat(),
        "n_입력": n,
        "max_published_at": max_pub.isoformat() if max_pub else None,
        "여유일": (as_of_d - max_pub).days if max_pub else None,
        "판정": "통과",
        "검사시각(UTC)": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "코드sha256_16": _self_sha16(),
    }


# ── 자기시험 (참/거짓 양쪽 · 조항 66 규격 — 값을 보고 판정을 고치는 길을 막는 방향 탐침) ──

def selftest():
    r = {"자기시험": "pretrain/leak_guard.py", "경우": []}
    ok = True

    def case(name, fn, expect):
        nonlocal ok
        try:
            got = fn()
            verdict = "통과(스탬프)"
            detail = {"스탬프": got}
        except LeakDetected as e:
            verdict = "LeakDetected"
            detail = {"메시지": str(e)[:300]}
        good = (verdict == expect)
        ok = ok and good
        r["경우"].append({"이름": name, "기대": expect, "실측": verdict,
                          "기대대로": good, **detail})

    past = [{"id": "a", "published_at": "2022-01-01"},
            {"id": "b", "published_at": "2023-06-30"},
            {"id": "c", "published_at": _dt.date(2023, 12, 31)}]
    case("참 — 전부 as_of 이전", lambda: assert_no_leak(past, "2024-01-01", "selftest-참"), "통과(스탬프)")
    case("거짓 — 사후 1건(> as_of)",
         lambda: assert_no_leak(past + [{"id": "심은키", "published_at": "2024-03-01"}],
                                "2024-01-01", "selftest-사후"), "LeakDetected")
    case("거짓 — 같은 날(= as_of · 보수 쪽)",
         lambda: assert_no_leak(past + [{"id": "d", "published_at": "2024-01-01"}],
                                "2024-01-01", "selftest-같은날"), "LeakDetected")
    case("거짓 — published_at=None",
         lambda: assert_no_leak(past + [{"id": "e", "published_at": None}],
                                "2024-01-01", "selftest-null"), "LeakDetected")
    case("거짓 — 파싱 불능 문자열",
         lambda: assert_no_leak(past + [{"id": "f", "published_at": "지난주쯤"}],
                                "2024-01-01", "selftest-파싱불능"), "LeakDetected")
    case("참 — 빈 입력(n=0)", lambda: assert_no_leak([], "2024-01-01", "selftest-빈"), "통과(스탬프)")
    r["전부_기대대로"] = ok
    return r


if __name__ == "__main__":
    res = selftest()
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    sys.exit(0 if res["전부_기대대로"] else 1)
