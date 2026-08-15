#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴🔴 **공유 채점기** — 976 수리 1~4.

## 왜 이 파일이 생겼나

`runners/ledger892.py … ledger975.py` 가 **21 벌**이었다. 채점기 수리가 **일회용 파일에
살아서 대물림이 안 됐다**(티처 #114 3순위: 공유 코드 착지 3/5). 976 이 하나로 합친다.
🔴 **976 은 `ledger976.py` 를 만들지 않는다.**

## 976 이 고친 것

- **수리 2** 🔴🔴 **슬롯 검사가 문서 본문을 읽는다.**
  975 판은 `render(resolve(키경로)) == 매니페스트["값"]` 을 견줬는데, 매니페스트의 `값` 이
  **같은 `resolve` 로 써 넣어진 것**이라 **항진명제**였다 — 문서 본문의 그 자리를
  **한 번도 안 읽었다**. 티처 #114 가 심으니 **975 판이 셋 다 못 잡고 974 판이 둘을 잡았다**.
  976 판: `본문[시작:끝) == render(resolve(키경로))`.
- **수리 3** 🔴 **양성 대조를 진짜로 심는다**(`plant_control`). 세 무리 A(슬롯 안)·
  B(슬롯 밖)·C(면제 자리)를 문서 **사본**에 심고 채점기 셋을 나란히 건다.
- **수리 4** 🔴 **`ALLOW_CTX` 를 줄인다** — **맨-9xx 규칙을 지웠다.** 그 규칙이
  수리 2 의 헤드라인 자신(「1,000 중 901」)을 조용히 면제했다. 구판을 `ALLOW_CTX_975`
  로 남겨 전후를 나란히 싣는다(조항 66-③).

씀:
    python3 runners/ledger.py --stage f5       --ref <40자 sha> --cycle 976
    python3 runners/ledger.py --stage numaudit --ref <40자 sha> --cycle 976
    python3 runners/ledger.py --stage control  --ref <40자 sha> --cycle 976
"""
import argparse
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import runners.predict971 as P                    # noqa: E402

OUT = ROOT / "runners"
NUMPAT = re.compile(r"-?\d[\d,]*(?:\.\d+)?")

#: 🔴 **975 판 면제 규칙** — 대조용으로 남긴다(조항 66-③: 자를 고치면 전후를 같이 싣는다).
ALLOW_CTX_975 = (
    ("노트 번호·사이클 번호", re.compile(r"(?:노트|티처 #|사이클|PR #|#)\s*\d+")),
    ("연도·날짜·시각", re.compile(r"\d{4}-\d{2}-\d{2}|\d{4}년|\d{2}:\d{2}")),
    ("절 번호", re.compile(r"§\s*\d+(?:\.\d+)?|v\d+\.\d+")),
    ("사전등록 딱지", re.compile(r"[PAHWVDERC]\d+")),
    ("🔴 975 신설: 사이클 번호(9xx)", re.compile(r"(?<![\d.,])9[0-9]{2}(?![\d.,])")),
    ("🔴 975 신설: 신뢰수준", re.compile(r"95\s*\\?%")),
    ("🔴 975 신설: 목록·표의 차례 번호",
     re.compile(r"(?m)^\s*\d+\.\s|\|\s*\d+\s*\||^\s*\d+\s*&")),
    ("🔴 975 신설: 순위 낱말", re.compile(r"\d+\s*(?:순위|위)")),
    ("🔴 975 신설: 수리·문항 번호",
     re.compile(r"(?:수리|예측|반증조건)\s*\d+|[PAHWVDERCF]\d+|A-\d")),
    ("🔴 975 신설: 인라인 코드(글자가 든 것만)",
     re.compile(r"`[^`\n]*[A-Za-z가-힣][^`\n]*`")),
)

#: 🔴🔴 **976 판 면제 규칙 (수리 4)** — 🔴 **맨-9xx 규칙을 지웠다.**
#: 그 규칙은 `(?<![\d.,])9[0-9]{2}(?![\d.,])` 로 **900~999 를 통째로** 면제해서
#: 수리 2 의 헤드라인 자신(「1,000 중 **901**」)을 안 셌다.
#: 🔴 **사이클 번호는 「노트 976」·「티처 #114」 처럼 낱말이 붙은 꼴로만 면제한다.**
ALLOW_CTX = (
    ("노트 번호·사이클 번호(낱말이 붙은 것만)",
     re.compile(r"(?:노트|티처 #|사이클|PR #|#)\s*\d+")),
    ("연도·날짜·시각", re.compile(r"\d{4}-\d{2}-\d{2}|\d{4}년|\d{2}:\d{2}")),
    ("절 번호", re.compile(r"§\s*\d+(?:\.\d+)?|v\d+\.\d+")),
    ("🔴 976 축소: 사전등록 딱지(등록된 접두어만)",
     re.compile(r"(?<![0-9A-Za-z])(?:P|W|E|C|R|F|V|D|H)\d{1,2}(?![0-9])")),
    ("신뢰수준", re.compile(r"95\s*\\?%")),
    ("목록·표의 차례 번호",
     re.compile(r"(?m)^\s*\d+\.\s|\|\s*\d+\s*\||^\s*\d+\s*&")),
    ("순위 낱말", re.compile(r"\d+\s*(?:순위|위)")),
    ("수리·문항 번호", re.compile(r"(?:수리|정정|예측|반증조건)\s*\d+|A-\d")),
    ("인라인 코드(글자가 든 것만)",
     re.compile(r"`[^`\n]*[A-Za-z가-힣][^`\n]*`")),
)


# ══════════════════════════════════════════════════════════════════════
# 도장 (규칙 C)
# ══════════════════════════════════════════════════════════════════════
def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_stamp(ran) -> dict:
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in ran]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def stamp_block(ref, cs0, cs1, t0, ran, data=None) -> dict:
    """🔴 시작·끝 두 번 + 돌린 러너 전부 + 고정 40자 ref + 자료 지문."""
    ds = {k: P._sha_file(str(ROOT / v)) for k, v in (data or {}).items()}
    runner, ok = {}, 0
    for r in ran:
        disk = P._sha_file(str(ROOT / r))
        try:
            cm = hashlib.sha256(subprocess.check_output(
                ["git", "show", "%s:%s" % (ref, r)], cwd=str(ROOT))).hexdigest()
        except Exception:                                          # noqa: BLE001
            cm = None
        runner[r] = {"디스크 sha256": disk, "커밋 blob sha256": cm, "일치": disk == cm}
        ok += 1 if disk == cm else 0
    return {
        "언제(시작)": t0, "언제(끝)": now(),
        "시작 code_stamp 요약": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "끝 code_stamp 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
        "🔴 시작=끝": cs0 == cs1,
        "분모: 도장이 덮는 파일": len(cs1),
        "🔴 자료 지문": ds, "분모: 연 자료 파일": len(ds),
        "🔴 F1 기준 ref(준 대로)": ref,
        "🔴 40자 고정 sha 인가": bool(re.fullmatch(r"[0-9a-f]{40}", ref or "")),
        "🔴 기준 ref 가 0000…0000 인가": bool(re.fullmatch(r"0{40}", ref or "")),
        "러너별": runner, "🔴 분자/분모": "%d / %d" % (ok, len(ran)),
        "🔴 F5 통과": ok == len(ran) and bool(re.fullmatch(r"[0-9a-f]{40}", ref or ""))
        and not re.fullmatch(r"0{40}", ref or ""),
    }


# ══════════════════════════════════════════════════════════════════════
# 산출물 값 읽기 / 그리기
# ══════════════════════════════════════════════════════════════════════
def _norm(x: str) -> str:
    x = x.replace(",", "")
    if "." in x:
        x = x.rstrip("0").rstrip(".")
    return x or "0"


def artifact_numbers(glob_pat) -> set:
    """🔴 **974 판 채점기** — 산출물 어딘가에 나오는 수의 집합. 나란히 세우려고 남긴다."""
    S = set()

    def add(v):
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            s = ("%r" % v) if isinstance(v, float) else str(v)
            S.add(_norm(s))
            if isinstance(v, float):
                for k in range(0, 7):
                    S.add(_norm("%.*f" % (k, v)))
                S.add(_norm("%.1f" % (100.0 * v)))
                S.add(_norm("%.2f" % (100.0 * v)))
                S.add(_norm("%.4f" % (100.0 * v)))
        elif isinstance(v, str):
            for m in NUMPAT.findall(v):
                S.add(_norm(m))
        elif isinstance(v, dict):
            for k, x in v.items():
                add(k)
                add(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                add(x)

    for p in sorted(glob.glob(str(OUT / glob_pat))):
        try:
            add(json.loads(Path(p).read_text(encoding="utf-8")))
        except Exception:                                          # noqa: BLE001
            pass
    return S


def resolve(path):
    """`[파일, 키, 키, …]` 를 산출물에서 실제로 따라간다."""
    if not path:
        return None, "빈 경로"
    f = OUT / path[0]
    if not f.is_file():
        return None, "산출물이 없다: %s" % path[0]
    cur = json.loads(f.read_text(encoding="utf-8"))
    for k in path[1:]:
        if isinstance(cur, dict):
            if k not in cur:
                return None, "키가 없다: %s" % k
            cur = cur[k]
        elif isinstance(cur, list):
            try:
                cur = cur[int(k)]
            except Exception:                                      # noqa: BLE001
                return None, "자리가 없다: %s" % k
        else:
            return None, "더 못 들어간다: %s" % k
    return cur, None


def render(v):
    """산출물 값 하나를 **본문에 실을 문자열**로. 여기 말고 다른 데서 안 만든다."""
    if isinstance(v, bool):
        return "참" if v else "거짓"
    if isinstance(v, float):
        return ("%.6f" % v).rstrip("0").rstrip(".") if abs(v) < 1e15 else repr(v)
    if isinstance(v, int):
        return "{:,}".format(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(render(x) for x in v) + "]"
    return str(v)


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴 수리 2 — **본문을 읽는** 슬롯 검사
# ══════════════════════════════════════════════════════════════════════
def allow_spans(src, rules=ALLOW_CTX):
    spans, why = [], collections.Counter()
    for name, pat in rules:
        for m in pat.finditer(src):
            spans.append((m.start(), m.end()))
            why[name] += 1
    return spans, why


def audit_text(src, slots, S, rules=ALLOW_CTX):
    """🔴 **본문 `src` 를 실제로 읽어** 수마다 출처를 묻는다.

    반환 키:
      `슬롯` — 슬롯별 `{본문, 키경로값, 일치}` (🔴 **`본문` 은 `src[시작:끝)` 이다**)
      `976 판이 못 찾는 수` — 슬롯 밖이거나, 슬롯 본문이 키 경로 값과 다른 수
      `974 판이 못 찾는 수` — 산출물 값 집합 `S` 에 없는 수
    """
    spans = []
    for sl in slots:
        val, err = resolve(sl["키 경로"])
        want = render(val) if err is None else None
        body = src[sl["시작"]:sl["끝"]]          # 🔴🔴 **여기가 수리 2 다**
        spans.append({"시작": sl["시작"], "끝": sl["끝"],
                      "키 경로": sl["키 경로"],
                      "본문": body, "키 경로 값": want,
                      "일치": bool(want is not None and body == want)})
    allow, why = allow_spans(src, rules)
    counted = exempt = 0
    miss_old, miss_new = [], []
    for m in NUMPAT.finditer(src):
        if any(a <= m.start() and m.end() <= b for a, b in allow):
            exempt += 1
            continue
        counted += 1
        ctx = re.sub(r"\s+", " ", src[max(0, m.start() - 40):m.end() + 40])
        if _norm(m.group()) not in S:
            miss_old.append({"수": m.group(), "맥락": ctx})
        cov = [sp for sp in spans if sp["시작"] <= m.start() and m.end() <= sp["끝"]]
        if not cov:
            miss_new.append({"수": m.group(), "왜": "슬롯 밖(손으로 적은 수)",
                             "자리": m.start(), "맥락": ctx})
        elif not cov[0]["일치"]:
            miss_new.append({"수": m.group(),
                             "왜": "슬롯 본문이 키 경로 값과 다르다",
                             "자리": m.start(),
                             "본문": cov[0]["본문"], "키 경로 값": cov[0]["키 경로 값"],
                             "맥락": ctx})
    return {"슬롯": spans, "센 수": counted, "면제된 수": exempt,
            "면제 사유별": dict(why),
            "🔴 키 경로와 본문이 다른 슬롯": sum(1 for sp in spans if not sp["일치"]),
            "🔴 974 판이 못 찾는 수": miss_old,
            "🔴🔴 976 판이 못 찾는 수": miss_new}


def audit_975(src, slots, S, rules=ALLOW_CTX_975):
    """🔴 **975 판 그대로** — 슬롯 판정이 `render(resolve(키경로)) == 매니페스트["값"]`.

    🔴 **본문을 한 번도 안 읽는다.** 항진명제임을 보이려고 남긴다.
    """
    spans = []
    for sl in slots:
        val, err = resolve(sl["키 경로"])
        ok = (err is None and render(val) == sl["값"])      # 🔴 txt == txt
        spans.append((sl["시작"], sl["끝"], ok))
    allow, _ = allow_spans(src, rules)
    counted, miss = 0, []
    for m in NUMPAT.finditer(src):
        if any(a <= m.start() and m.end() <= b for a, b in allow):
            continue
        counted += 1
        cov = [sp for sp in spans if sp[0] <= m.start() and m.end() <= sp[1]]
        if not cov or not cov[0][2]:
            miss.append({"수": m.group(), "자리": m.start()})
    return {"센 수": counted, "🔴 975 판이 못 찾는 수": miss}


# ══════════════════════════════════════════════════════════════════════
# 🔴 수리 3 — **양성 대조를 진짜로 심는다**
# ══════════════════════════════════════════════════════════════════════
_BUMP = re.compile(r"\d")


def _bump_last_digit(txt):
    """마지막 숫자 문자를 `(d+1) mod 10` 으로. 🔴 **글자 수가 안 변한다.**"""
    pos = [m.start() for m in _BUMP.finditer(txt)]
    if not pos:
        return None
    i = pos[-1]
    return txt[:i] + str((int(txt[i]) + 1) % 10) + txt[i + 1:]


def plant_control(src, slots, S, n_a=3, n_b=6, n_c=6, seed=976):
    """🔴 문서 **사본**에 셋을 심고 채점기 셋을 나란히 건다.

    - **무리 A** 슬롯 **안**의 수를 바꾼다(길이 보존) → 🔴 976 판이 전부 잡아야 한다.
    - **무리 B** 문서 **끝에** 새 수를 끼워 넣는다(슬롯 오프셋을 안 흔든다)
      → 🔴 976 판이 전부 잡아야 한다.
    - **무리 C** `ALLOW_CTX` 가 **면제하는 자리**의 수를 바꾼다(길이 보존)
      → 🔴 **0 개를 잡는 것이 정상**이고, 그것이 **선언된 사각지대**다.
    """
    allow, _ = allow_spans(src, ALLOW_CTX)

    def in_allow(a, b):
        return any(x <= a and b <= y for x, y in allow)

    # ── 무리 A ────────────────────────────────────────────────
    cand = [(i, sl) for i, sl in enumerate(slots)
            if _BUMP.search(src[sl["시작"]:sl["끝"]])
            and not in_allow(sl["시작"], sl["끝"])]
    picks = []
    if cand:
        idx = sorted({0, len(cand) // 2, len(cand) - 1})
        picks = [cand[i] for i in idx][:n_a]
    a_src = src
    a_planted = []
    for _i, sl in picks:
        body = a_src[sl["시작"]:sl["끝"]]
        new = _bump_last_digit(body)
        if new is None or new == body:
            continue
        a_src = a_src[:sl["시작"]] + new + a_src[sl["끝"]:]
        a_planted.append({"무리": "A(슬롯 안)", "자리": sl["시작"],
                          "원래": body, "심은 것": new, "키 경로": sl["키 경로"]})

    # ── 무리 B ────────────────────────────────────────────────
    b_src = a_src
    b_planted = []
    tail = ["8675309", "4815162", "9128374", "6203945", "7391026", "5847213"]
    head = "\n대조 삽입 값은 "
    for j in range(min(n_b, len(tail))):
        add = head + tail[j] + " 이다\n"
        b_planted.append({"무리": "B(슬롯 밖)", "자리": len(b_src) + len(head),
                          "원래": "", "심은 것": tail[j]})
        b_src = b_src + add

    # ── 무리 C ────────────────────────────────────────────────
    c_src = b_src
    c_planted = []
    stable = re.compile(r"\d{4}-\d{2}-\d{2}|(?:노트|티처 #|사이클|PR #)\s*\d+"
                        r"|§\s*\d+(?:\.\d+)?")
    hits = []
    for m in stable.finditer(c_src):
        if any(sl["시작"] <= m.start() and m.end() <= sl["끝"] for sl in slots):
            continue
        hits.append(m.span())
    step = max(1, len(hits) // max(1, n_c))
    for a, b in hits[::step][:n_c]:
        body = c_src[a:b]
        new = _bump_last_digit(body)
        if new is None or new == body:
            continue
        c_src = c_src[:a] + new + c_src[b:]
        c_planted.append({"무리": "C(면제 자리)", "자리": a,
                          "원래": body, "심은 것": new})

    planted = a_planted + b_planted + c_planted

    def caught(res_new, res_old, res_975):
        """심은 자리마다 세 채점기가 잡았는지."""
        pos_new = {d.get("자리") for d in res_new["🔴🔴 976 판이 못 찾는 수"]}
        num_old = collections.Counter(_norm(d["수"])
                                      for d in res_old["🔴 974 판이 못 찾는 수"])
        pos_975 = {d["자리"] for d in res_975["🔴 975 판이 못 찾는 수"]}
        rows = []
        for pl in planted:
            lo, hi = pl["자리"], pl["자리"] + max(1, len(pl["심은 것"]))
            hit_new = any(lo <= p < hi for p in pos_new)
            hit_975 = any(lo <= p < hi for p in pos_975)
            digits = _norm(re.sub(r"[^\d.,-]", "", pl["심은 것"]) or "0")
            hit_old = num_old.get(digits, 0) > 0
            rows.append(dict(pl, **{"🔴 976 판이 잡았나": bool(hit_new),
                                    "975 판이 잡았나": bool(hit_975),
                                    "974 판이 잡았나": bool(hit_old)}))
        return rows

    r_new = audit_text(c_src, slots, S)
    r_975 = audit_975(c_src, slots, S)
    rows = caught(r_new, r_new, r_975)
    by = collections.OrderedDict()
    for g in ("A(슬롯 안)", "B(슬롯 밖)", "C(면제 자리)"):
        sub = [r for r in rows if r["무리"] == g]
        by[g] = {
            "심은 수": len(sub),
            "🔴🔴 976 판 분자/분모": "%d / %d" % (
                sum(1 for r in sub if r["🔴 976 판이 잡았나"]), len(sub)),
            "975 판 분자/분모": "%d / %d" % (
                sum(1 for r in sub if r["975 판이 잡았나"]), len(sub)),
            "974 판 분자/분모": "%d / %d" % (
                sum(1 for r in sub if r["974 판이 잡았나"]), len(sub)),
        }
    return {"심은 것": rows, "무리별": by,
            "🔴 심은 수 합": len(rows),
            "🔴🔴 976 판 전체 분자/분모": "%d / %d" % (
                sum(1 for r in rows if r["🔴 976 판이 잡았나"]), len(rows)),
            "🔴 975 판 전체 분자/분모": "%d / %d" % (
                sum(1 for r in rows if r["975 판이 잡았나"]), len(rows)),
            "🔴 974 판 전체 분자/분모": "%d / %d" % (
                sum(1 for r in rows if r["974 판이 잡았나"]), len(rows))}


# ══════════════════════════════════════════════════════════════════════
def stage_f5(ref, cycle, ran) -> dict:
    t0 = now()
    cs0 = code_stamp(ran)
    pat = "out%s_*.json" % cycle
    rows = collections.OrderedDict()
    num = den = 0
    for p in sorted(glob.glob(str(OUT / pat))):
        name = Path(p).name
        den += 1
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception as e:                                     # noqa: BLE001
            rows[name] = {"🔴 읽기 실패": str(e), "F5": False}
            continue
        st = d.get("🔴 도장")
        if not isinstance(st, dict):
            rows[name] = {"🔴 도장이 없다": True, "F5": False}
            continue
        ok = bool(st.get("🔴 F5 통과"))
        num += 1 if ok else 0
        rows[name] = {"F5": ok, "분자/분모": st.get("🔴 분자/분모"),
                      "기준 ref": st.get("🔴 F1 기준 ref(준 대로)"),
                      "40자 고정 sha 인가": st.get("🔴 40자 고정 sha 인가"),
                      "🔴 0000…0000 인가": st.get("🔴 기준 ref 가 0000…0000 인가"),
                      "시작=끝": st.get("🔴 시작=끝"),
                      "도장이 덮는 파일": st.get("분모: 도장이 덮는 파일")}
    out = {"무엇": "%s — F5 를 산출물 전량에 채점한다(공유 `ledger.py`)" % cycle,
           "🔴 채점 대상 글롭": pat,
           "🔴🔴 F5 분자/분모(전량)": "%d / %d" % (num, den),
           "🔴 전량 통과인가": num == den,
           "산출물별": rows}
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(ran), t0, ran)
    (OUT / ("out%s_f5.json" % cycle)).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def stage_numaudit(ref, cycle, ran) -> dict:
    t0 = now()
    cs0 = code_stamp(ran)
    S = artifact_numbers("out%s_*.json" % cycle)
    sf = OUT / ("out%s_slots.json" % cycle)
    #: 🔴 슬롯 대장이 아직 없으면 **빈 대장**으로 돈다 — 생성기와 채점기가 서로를
    #: 인용하므로 첫 바퀴를 돌리려면 이 자리가 필요하다(뒤 바퀴에서 진짜 값이 든다).
    man = json.loads(sf.read_text(encoding="utf-8")) if sf.is_file() else {}
    files = man.get("파일별", {})
    per = collections.OrderedDict()
    tot = miss_old = miss_new = exempt_new = exempt_975 = bad_slot = 0
    for rel, info in files.items():
        p = Path(info["절대경로"]) if info.get("절대경로") else (ROOT / rel)
        if not p.is_file():
            per[rel] = {"🔴 파일이 없다": True}
            continue
        src = p.read_text(encoding="utf-8")
        r = audit_text(src, info["슬롯"], S)
        _a975, why975 = allow_spans(src, ALLOW_CTX_975)
        tot += r["센 수"]
        miss_old += len(r["🔴 974 판이 못 찾는 수"])
        miss_new += len(r["🔴🔴 976 판이 못 찾는 수"])
        exempt_new += r["면제된 수"]
        exempt_975 += len(_a975)
        bad_slot += r["🔴 키 경로와 본문이 다른 슬롯"]
        per[rel] = {
            "🔴 센 수(면제 뺀)": r["센 수"],
            "🔴 면제된 자리(976 판)": r["면제된 수"],
            "🔴 면제 규칙이 무는 자리(975 판)": len(_a975),
            "🔴 면제 사유별(976 판)": r["면제 사유별"],
            "🔴 슬롯 수": len(r["슬롯"]),
            "🔴🔴 키 경로와 본문이 다른 슬롯": r["🔴 키 경로와 본문이 다른 슬롯"],
            "🔴 974 판(값 집합)이 못 찾는 수": len(r["🔴 974 판이 못 찾는 수"]),
            "🔴🔴 976 판(본문 대조)이 못 찾는 수": len(r["🔴🔴 976 판이 못 찾는 수"]),
            "974 판 목록": r["🔴 974 판이 못 찾는 수"][:40],
            "🔴 976 판 목록": r["🔴🔴 976 판이 못 찾는 수"][:60],
        }
    out = {
        "무엇": "%s — 본문 넷의 모든 수가 **본문 대조**로 출처를 대는지 훑는다" % cycle,
        "🔴 대상": list(files),
        "🔴 분모: 대상 파일": len(files),
        "🔴 산출물에서 모은 수의 가짓수(974 판 허용집합)": len(S),
        "🔴🔴 974 판 분자/분모": "%d / %d" % (miss_old, tot),
        "🔴🔴🔴 976 판 분자/분모(본문이 출처를 못 대는 수 / 센 수)": "%d / %d" % (miss_new, tot),
        "🔴 통과(976 판 · 하나도 없어야 한다)": miss_new == 0,
        "🔴🔴 키 경로와 본문이 다른 슬롯(전체)": bad_slot,
        "🔴🔴 수리 4 — 면제 자리(안 세는 자리)": {
            "🔴 976 판 면제 자리": exempt_new,
            "🔴 975 판 면제 규칙이 무는 자리": exempt_975,
            "🔴 면제 규칙 수(976 판)": len(ALLOW_CTX),
            "🔴 면제 규칙 수(975 판)": len(ALLOW_CTX_975),
            "🔴 지운 규칙": "맨-9xx(900~999 를 통째로 면제) · 사전등록 딱지를 등록 접두어로 좁힘",
            "🔴 뜻": "🔴 **이 수만큼은 원리상 안 본다** — 판정문에 그대로 적는다",
        },
        "파일별": per,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(ran), t0, ran)
    (OUT / ("out%s_numaudit.json" % cycle)).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def stage_control(ref, cycle, ran) -> dict:
    """🔴 수리 3 — 양성 대조. **문서를 안 고친다**(사본에만 심는다)."""
    t0 = now()
    cs0 = code_stamp(ran)
    S = artifact_numbers("out%s_*.json" % cycle)
    sf = OUT / ("out%s_slots.json" % cycle)
    #: 🔴 슬롯 대장이 아직 없으면 **빈 대장**으로 돈다 — 생성기와 채점기가 서로를
    #: 인용하므로 첫 바퀴를 돌리려면 이 자리가 필요하다(뒤 바퀴에서 진짜 값이 든다).
    man = json.loads(sf.read_text(encoding="utf-8")) if sf.is_file() else {}
    files = man.get("파일별", {})
    per = collections.OrderedDict()
    agg = collections.Counter()
    for rel, info in files.items():
        p = Path(info["절대경로"]) if info.get("절대경로") else (ROOT / rel)
        if not p.is_file():
            continue
        src = p.read_text(encoding="utf-8")
        r = plant_control(src, info["슬롯"], S, n_a=3, n_b=6, n_c=6)
        per[rel] = r["무리별"]
        for row in r["심은 것"]:
            agg["심음/" + row["무리"]] += 1
            if row["🔴 976 판이 잡았나"]:
                agg["976/" + row["무리"]] += 1
            if row["975 판이 잡았나"]:
                agg["975/" + row["무리"]] += 1
            if row["974 판이 잡았나"]:
                agg["974/" + row["무리"]] += 1
    groups = ("A(슬롯 안)", "B(슬롯 밖)", "C(면제 자리)")
    tot = collections.OrderedDict()
    for g in groups:
        n = agg["심음/" + g]
        tot[g] = {"심은 수": n,
                  "🔴🔴 976 판": "%d / %d" % (agg["976/" + g], n),
                  "975 판": "%d / %d" % (agg["975/" + g], n),
                  "974 판": "%d / %d" % (agg["974/" + g], n)}
    n_all = sum(agg["심음/" + g] for g in groups)
    out = {
        "무엇": "%s — 수리 3: 양성 대조를 진짜로 심는다(문서 사본에만)" % cycle,
        "🔴 왜": ("975 사전등록 §8 E4 가 양성 대조를 등록하고 안 만들었다. "
               "그리고 975 의 슬롯 검사는 `txt == txt` 라 항진명제였다."),
        "🔴 무리별(전 파일 합)": tot,
        "🔴 심은 수 합": n_all,
        "🔴🔴 976 판 전체": "%d / %d" % (
            sum(agg["976/" + g] for g in groups), n_all),
        "🔴 975 판 전체": "%d / %d" % (
            sum(agg["975/" + g] for g in groups), n_all),
        "🔴 974 판 전체": "%d / %d" % (
            sum(agg["974/" + g] for g in groups), n_all),
        "🔴 무리 A 는 976 판이 전부 잡아야 한다": (
            agg["976/A(슬롯 안)"] == agg["심음/A(슬롯 안)"]),
        "🔴 무리 B 는 976 판이 전부 잡아야 한다": (
            agg["976/B(슬롯 밖)"] == agg["심음/B(슬롯 밖)"]),
        "🔴 무리 C 는 아무도 못 잡는 것이 정상(선언된 사각지대)": (
            agg["976/C(면제 자리)"] == 0),
        "파일별": per,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(ran), t0, ran)
    (OUT / ("out%s_control.json" % cycle)).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


DEFAULT_RAN = ("runners/ledger.py", "runners/predict971.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["f5", "numaudit", "control"])
    ap.add_argument("--ref", default="")
    ap.add_argument("--cycle", default="976")
    a = ap.parse_args()
    fn = {"f5": stage_f5, "numaudit": stage_numaudit, "control": stage_control}
    r = fn[a.stage](a.ref, a.cycle, DEFAULT_RAN)
    print(json.dumps({k: v for k, v in r.items()
                      if k not in ("파일별", "산출물별", "심은 것")},
                     ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
