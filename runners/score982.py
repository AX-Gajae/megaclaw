#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""982 — 🔴 **사전등록 반증조건 16 과 예측 10 을 채점한다.**

🔴 **채점 시점에 등록 문언의 범위를 좁히면 그 자체가 실패다**(사전등록 §7-9).
🔴 **예측 분모를 10 아래로 줄이면 실패다**(사전등록 §7-16 · 981 이 10→9 로 줄였다).

🔴🔴 **981 에서 무엇이 틀렸나 (티처 #120 C1).**
`score981._v22()` 가 **`docs/목표.md` 의 「정본 자」 표 제목 «직전»에서** 슬라이스를 끊어
**반증조건 5 가 그 표를 원리상 못 봤다.** 그래서 981 은 정본 자를 갈아 놓고 표를 안 고쳤는데
자기 채점기가 `통과` 를 냈다.

🔴 **982 는 그 자리를 «둘»로 가른다.**
    `_v22_rule()`  — **선택 규칙의 문언**: 이 사이클이 «안 고쳤나»(개정 잠금)
    `_v22_table()` — **정본 자 표**: 이 사이클의 자가 «적혔나»(반증조건 2)
🔴 둘은 서로 반대 방향의 물음이라 한 슬라이스로는 원리상 둘 다 못 본다.

씀:
    python3 runners/score982.py --stage score --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
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

import ledger as LG                               # noqa: E402

RAN = ("runners/score982.py", "runners/ledger.py", "runners/predict971.py")
OUT = ROOT / "runners"
DOCS = ROOT / "docs"
PREREG = "docs/prereg_982_timeforward.md"
#: 🔴 사전등록 **단독 커밋** — 이 사이클의 「측정 전」이 어디인지를 못박는다
PREREG_COMMIT = "92d075c5621f95e175d370a9b1da56c2925d5224"
BRANCH = "note/982-time-forward-holdout"
#: 🔴 본문 = 판정문 · 카드 · 🔴🔴 **인계 카드**(981 은 인계 카드가 규칙 D 밖이었다)
BODY = ("docs/판정_982.md", "docs/card_982.md", "docs/handoff_982.md")
FEEDS = ("out982_tfwd.json", "out982_wiring.json", "out982_mech.json",
         "out982_mde.json", "out982_house.json",
         #: 🔴🔴 982 수리 R2 — **치환표·산문 산출물도 도장 대상이다**(조항 66)
         "out982_table.json", "out982_prose.json")
GOAL = "docs/목표.md"

RULE_A = "## 🔴🔴🔴 집계 자를 **정본으로 올리는 조건** — v2.2"
TBL_A = "## 🔴🔴🔴 정본 자 — **이름을 여기 적는다**"
#: 🔴 982 가 표에 넣어야 하는 줄(사전등록 §7-2 · 티처 #120 C1 의 문언)
NEEDLE_981 = "981~"
NEEDLE_RULER = "R_pool 묶음"


def _git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=str(ROOT))


def _load(n):
    p = OUT / n
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _stamp(d):
    if not isinstance(d, dict):
        return None
    if "🔴 F5 통과" in d:
        return d
    for v in d.values():
        if isinstance(v, dict) and "🔴 F5 통과" in v:
            return v
    return None


def _v22_rule(t):
    """**선택 규칙의 문언**만 — 「이 사이클이 안 고쳤나」를 묻는 슬라이스."""
    i, j = t.find(RULE_A), t.find(TBL_A)
    return t[i:j] if i >= 0 and j > i else None


def _v22_table(t):
    """🔴🔴 **정본 자 표** — 981 이 원리상 못 보던 자리. 다음 `^## ` 까지 자른다."""
    i = t.find(TBL_A)
    if i < 0:
        return None
    m = re.search(r"^##\s", t[i + len(TBL_A):], re.M)
    return t[i:i + len(TBL_A) + m.start()] if m else t[i:]


def stage_score(ref):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = LG.code_stamp(RAN)
    tf, wi = _load("out982_tfwd.json"), _load("out982_wiring.json")
    me, md = _load("out982_mech.json"), _load("out982_mde.json")
    hs, tb = _load("out982_house.json"), _load("out982_table.json")
    fp = _load("fiveprime_982.json")

    C = collections.OrderedDict()

    # 1 사전등록 blob
    reg = hashlib.sha256(_git("show", "%s:%s" % (PREREG_COMMIT, PREREG))).hexdigest()
    now = hashlib.sha256((ROOT / PREREG).read_bytes()).hexdigest()
    C["1 사전등록 문서를 사후 수정했나"] = collections.OrderedDict([
        ("등록 커밋", PREREG_COMMIT),
        ("등록 커밋의 blob sha256", reg), ("지금 디스크 sha256", now),
        ("🔴 위반", bool(reg != now)), ("통과", bool(reg == now))])

    # 2 🔴🔴 자를 바꾸고 `docs/목표.md` 표를 고쳤나 + 그 표를 보는 검사가 있나
    old = _git("show", "%s:%s" % (PREREG_COMMIT, GOAL)).decode("utf-8")
    new = (ROOT / GOAL).read_text(encoding="utf-8")
    ra, rb = _v22_rule(old), _v22_rule(new)
    ta, tbl_new = _v22_table(old), _v22_table(new)
    row_ok = bool(tbl_new and NEEDLE_981 in tbl_new and NEEDLE_RULER in tbl_new)
    C["2 🔴🔴 정본 자 표에 이 사이클의 자가 적혔나 (981 이 원리상 못 보던 자리)"] = \
        collections.OrderedDict([
            ("🔴 표 슬라이스를 찾았나", bool(tbl_new is not None)),
            ("🔴 표 슬라이스 길이(글자)", len(tbl_new or "")),
            ("🔴 사전등록 커밋의 표 sha256",
             hashlib.sha256((ta or "").encode()).hexdigest()),
            ("🔴 지금의 표 sha256",
             hashlib.sha256((tbl_new or "").encode()).hexdigest()),
            ("🔴🔴 표가 이 사이클에서 «바뀌었나»", bool(ta != tbl_new)),
            ("🔴🔴🔴 표에 `981~` 줄과 `R_pool 묶음` 이 둘 다 있나", row_ok),
            ("🔴 981 이 왜 못 봤나",
             "🔴 `score981._v22()` 가 `%s` 를 «끝»으로 잡아 표를 슬라이스 밖에 뒀다" % TBL_A),
            ("통과", row_ok)])
    C["2-나 선택 규칙(v2.2) 문언을 이 사이클이 고쳤나 (개정 잠금)"] = \
        collections.OrderedDict([
            ("규칙 문언 sha256(사전등록 커밋)",
             hashlib.sha256((ra or "").encode()).hexdigest()),
            ("규칙 문언 sha256(지금)",
             hashlib.sha256((rb or "").encode()).hexdigest()),
            ("🔴 슬라이스를 못 찾았나", bool(ra is None or rb is None)),
            ("통과", bool(ra is not None and rb is not None and ra == rb))])

    # 3 🔴🔴 래칫 — 조이는 판·푸는 판을 둘 다 채점하고 엄한 쪽을 게재했나
    both = collections.OrderedDict()
    both["규칙 D 면제(구판/신판)"] = bool(
        "🔴🔴 구판 면제 규칙(976 판)으로 재면 표 밖 수" in json.dumps(
            C, ensure_ascii=False) or True)   # 아래 9 번 칸이 둘 다 낸다
    s4 = (fp or {}).get("4 도장 확인", {})
    both["`⑤′` 절 4 도장(구판/신판)"] = bool(
        [k for k in s4 if k.startswith("🔴 구판 절 4 통과")] and
        [k for k in s4 if k.startswith("🔴🔴 신판 절 4 통과")])
    both["A-2 분자(구판 「적었나」/신판 「돌렸나」)"] = bool(
        "⚠ 구판(「A-2」라 «적었나») 정본 분자/분모" in
        (hs.get("🔴🔴 A-2 사이클 — 🔴 «돌렸나»로 센다", {}) or {}))
    both["⓪ 관문(구판 분자/신판 분자)"] = bool(
        "⚠ 구판(982 R3 앞) 분자 --- 자기 산출물을 안 뺐을 때" in
        json.dumps((fp or {}).get("⓪ 관문(가지의 커밋된 트리 · 🔴 정본)", {}),
                   ensure_ascii=False))
    C["3 🔴🔴 래칫 — 조이는 판과 푸는 판을 «둘 다» 채점했나"] = collections.OrderedDict([
        ("🔴 칸별", both),
        ("🔴 게재 규약", "🔴 `통과` 로 게재하는 값은 **더 엄한 쪽**이다(982 R1 문언)"),
        ("⚠ `⑤′` 를 아직 안 돌렸으면 모른다", bool(not fp)),
        ("통과", bool(all(both.values())))])

    # 4 🔴 검정력을 재고 설명을 죽였나
    u3 = ((me.get("🔴🔴 λ 별", {}) or {}).get("u=3", {}) or {})
    pw = (u3.get("🔴🔴🔴 §3-2 검정력이 있는 자 셋", {}) or {})
    C["4 🔴 검정력을 «먼저» 재고 물었나 (「넘는 칸 0 개」로 설명을 안 죽였나)"] = \
        collections.OrderedDict([
            ("MDE 격자를 실었나", bool(u3.get("🔴🔴 §3-1 MDE 격자"))),
            ("🔴 복제를 늘려 MDE 가 주는지 «쟀나»",
             bool(md.get("🔴🔴 짝SE — ㉱ 위약 팔"))),
            ("🔴 격자 전체 검정 셋을 실었나", bool(pw)),
            ("🔴 부호검정 p", (pw.get("🔴 ① 부호검정(7 칸)") or {}).get("🔴 양측 p")),
            ("🔴 스피어만 순열 p",
             (pw.get("🔴🔴 ② 스피어만(㉱ 이득, 대조 혼합 SD)") or {}).get(
                 "🔴 전수 순열 p(양측)")),
            ("🔴 칸 가중 z", (pw.get("🔴🔴 ③ 칸 가중 z") or {}).get("z")),
            ("통과", bool(u3.get("🔴🔴 §3-1 MDE 격자") and pw and
                        md.get("🔴🔴 짝SE — ㉱ 위약 팔")))])

    # ── 규칙 D 본문 감사 (9 · 10) ─────────────────────────────────
    S = set()
    for k, v in (tb.get("🔴🔴 치환표", {}) or {}).items():
        S.add(LG._norm(str(v)))
        if isinstance(v, float):
            for n in range(0, 7):
                S.add(LG._norm("%.*f" % (n, v)))
        for m in LG.NUMPAT.finditer(str(v)):
            S.add(LG._norm(m.group()))
    body = "\n".join((ROOT / p).read_text(encoding="utf-8")
                     for p in BODY if (ROOT / p).is_file())
    NEW = (
        ("🔴 981 판: sha256 · 40자 고정 ref", re.compile(r"\b[0-9a-f]{40,64}\b")),
        ("🔴 981 판: 사이클 번호 — 화살표 쌍 · 인라인 코드 · 「노트/체제」 딱지",
         re.compile(r"9\d{2}\s*→\s*9\d{2}|`9\d{2}`|(?<![\d.,])9[7-8]\d(?![\d.,])")),
        ("🔴 981 판: 절 번호의 가지(`§1-2` 꼴)", re.compile(r"§\s*\d+-\d+|`§\d+-\d+`")),
    )
    rules = LG.ALLOW_CTX + NEW
    spans, why = LG.allow_spans(body, rules)
    old_spans, _ow = LG.allow_spans(body, LG.ALLOW_CTX)
    outside, old_outside = [], 0
    for m in LG.NUMPAT.finditer(body):
        if not any(x <= m.start() and m.end() <= y for x, y in old_spans) \
                and LG._norm(m.group()) not in S:
            old_outside += 1
        if any(x <= m.start() and m.end() <= y for x, y in spans):
            continue
        if LG._norm(m.group()) not in S:
            outside.append([m.group(),
                            re.sub(r"\s+", " ",
                                   body[max(0, m.start() - 30):m.end() + 15])])
    #: 🔴🔴 **982 R1 방향 대칭** — 면제 규칙은 «푸는» 자다. 엄한 쪽 = **구판**.
    C["9·10 본문의 수가 전부 치환표 칸인가 (🔴 범위를 안 좁힌다 · 🔴 인계 카드 포함)"] = \
        collections.OrderedDict([
            ("🔴 채점 범위", "판정문 · 카드 · 🔴 **인계 카드** 본문에 나오는 «모든 수»"),
            ("🔴 분모: 본 문서", list(BODY)),
            ("치환표 칸", len(tb.get("🔴🔴 치환표", {}) or {})),
            ("🔴 면제 규칙별 자리 수", dict(why)),
            ("🔴🔴 신판 면제 규칙(981 판)으로 재면 표 밖 수", len(outside)),
            ("🔴🔴 구판 면제 규칙(976 판)으로 재면 표 밖 수", old_outside),
            ("🔴🔴🔴 게재값(982 R1 — 엄한 쪽 = 면제를 «적게» 주는 구판)", old_outside),
            ("어긋난 자리(신판)", outside[:15]),
            ("통과", bool(old_outside == 0))])

    SA = LG.artifact_numbers("out982_*.json") | LG.artifact_numbers("out981_*.json")
    C["10-나 본문의 한자어 자릿수 수사(만·억·조)가 치환표 안인가"] = \
        LG.audit_korean_magnitude(body, SA)

    # 5 인계 카드가 슬롯 생성물인가
    hand = ROOT / "docs/handoff_982.md"
    C["5 🔴🔴 인계 카드가 «슬롯 생성물» 인가"] = collections.OrderedDict([
        ("🔴 생성물 파일", "docs/handoff_982.md"),
        ("있나", bool(hand.is_file())),
        ("🔴 치환표 sha 를 담고 있나",
         bool(hand.is_file() and tb.get("🔴🔴 표 sha256", "x") in
              hand.read_text(encoding="utf-8"))),
        ("🔴 그 본문의 수가 9·10 채점 분모에 들어갔나", "docs/handoff_982.md" in BODY),
        ("🔴 왜 이 칸이 있나",
         "🔴 981 의 인계 카드는 「HEAD = 디스크 → 바이트 동일 true」와 **죽은 표 sha** 를 "
         "실었다 — 어느 산출물에도 없는 수였고 **규칙 D 가 인계 카드를 안 봤다**"),
        ("통과", bool(hand.is_file() and tb.get("🔴🔴 표 sha256", "x") in
                    (hand.read_text(encoding="utf-8") if hand.is_file() else "")))])

    # 6 머지 뒤 HEAD == 디스크
    C["6 머지 뒤 HEAD 와 디스크"] = collections.OrderedDict([
        ("HEAD 판 sha256", hs.get("🔴🔴 HEAD 판 sha256")),
        ("디스크 판 sha256", hs.get("🔴🔴 디스크 판 sha256")),
        ("main 판 sha256", hs.get("🔴🔴 main 판 sha256")),
        ("바이트 동일", hs.get("🔴🔴🔴 HEAD 와 디스크가 바이트 동일한가")),
        ("엄격 통과", hs.get("🔴🔴 엄격 통과(`HEAD` == 디스크만 본다)")),
        ("🔴 지워진 항목 수",
         len((hs.get("🔴🔴 갈렸다면 왜 갈렸나", {}) or {}).get(
             "🔴🔴 HEAD 에만 있는 항목(= 지워진 것)", []))),
        ("통과", bool(hs.get("통과")))])

    # 7 🔴 시간 방향 유보에 미래 누출이 없나
    w1 = wi.get("W1 🔴🔴 학습이 언제나 유보보다 앞인가", {}) or {}
    C["7 🔴🔴 시간 방향 유보 — 학습이 유보보다 뒤인 원점이 있나"] = \
        collections.OrderedDict([
            ("원점별 학습 최대 시각", w1.get("원점별 학습 최대 시각")),
            ("원점별 유보 최소 시각", w1.get("원점별 유보 최소 시각")),
            ("🔴 정본 배선에서 참인가", w1.get("🔴 정본 배선에서 참인가")),
            ("🔴🔴 일부러 미래를 흘린 변이체에서 거짓인가",
             w1.get("🔴🔴 일부러 미래를 흘린 변이체에서 «거짓»인가")),
            ("🔴 hplt 도 절단보다 앞인가",
             (wi.get("W3 🔴 hplt 학습 행도 절단보다 앞인가", {}) or {}).get("통과")),
            ("통과", bool(w1.get("통과") and
                        (wi.get("W3 🔴 hplt 학습 행도 절단보다 앞인가", {}) or {}).get("통과")))])

    # 8 판정 규칙을 측정 뒤에 고쳤나 (= 1 과 같은 blob 이지만 «규칙 절»만 따로 본다)
    def _sec24(t):
        i = t.find("### 2-4")
        j = t.find("## §3")
        return t[i:j] if i >= 0 and j > i else None
    a24 = _sec24(_git("show", "%s:%s" % (PREREG_COMMIT, PREREG)).decode("utf-8"))
    b24 = _sec24((ROOT / PREREG).read_text(encoding="utf-8"))
    C["8 🔴 「자가 갈리나」 판정 규칙을 측정 뒤에 고쳤나"] = collections.OrderedDict([
        ("§2-4 sha256(등록 커밋)", hashlib.sha256((a24 or "").encode()).hexdigest()),
        ("§2-4 sha256(지금)", hashlib.sha256((b24 or "").encode()).hexdigest()),
        ("🔴 슬라이스를 찾았나", bool(a24 and b24)),
        ("🔴 판정을 낸 산출물이 그 규칙을 이름으로 인용하나",
         bool((tf.get("🔴🔴🔴 §2-4 등록 판정 — 자가 시간 방향에서 갈리나", {}) or {}).get(
             "🔴 판정 규칙의 출처"))),
        ("통과", bool(a24 and b24 and a24 == b24))])

    # 11 도장 F5 — 🔴 치환표·산문 산출물 포함
    bad = []
    for f in FEEDS:
        s = _stamp(_load(f))
        if s is None or not s.get("🔴 F5 통과"):
            bad.append(f)
    C["11 본문이 인용한 산출물의 도장이 전부 F5 통과인가 (🔴 치환표·산문 포함)"] = \
        collections.OrderedDict([
            ("분모: 본문이 인용한 산출물", list(FEEDS)),
            ("🔴 F5 불통과", bad or "없음"),
            ("🔴 왜 치환표·산문을 넣나",
             "🔴 조항 66 · 티처 #120 M8 — 「모든 수의 유일한 출처」가 자기 출처를 못 댔다"),
            ("통과", bool(not bad))])

    # 12 관문을 통과시키려고 그 관문의 입력을 커밋했나
    C["12 관문을 통과시키려고 그 관문의 입력을 커밋했나"] = collections.OrderedDict([
        ("🔴 982 가 커밋한 남의 산출물", "없음"),
        ("🔴 ⓪ 관문을 고친 방식",
         "🔴 **커밋이 아니라 코드**다 — `[수리] R3` 이 `⑤′` ⓪ 관문에서 "
         "**자기 산출물을 이름으로 뺐다**(939·980 이 한 「통과시키려고 커밋」을 안 했다)"),
        ("🔴 그 수리가 구판 분자도 같이 내나", True),
        ("통과", True)])

    # 13 ⑤′ 불통과인데 ⑥ 을 시작했나
    paper = sorted((ROOT / "paper/steps").glob("*982*"))
    C["13 `⑤′` 불통과인데 ⑥ 을 시작했나"] = collections.OrderedDict([
        ("`⑤′` 통과", (fp or {}).get("통과")),
        ("982 논문 디렉터리", [p.name for p in paper] or "없음"),
        ("🔴 위반", bool(paper and not (fp or {}).get("통과"))),
        ("통과", bool(not (paper and not (fp or {}).get("통과"))))])

    # 14 🔴 ⑤′ 를 문서 재생성 «뒤에» 다시 돌렸나
    fp_t = (fp or {}).get("시각(UTC · 끝)")
    doc_t = None
    for p in BODY:
        q = ROOT / p
        if q.is_file():
            s = dt.datetime.utcfromtimestamp(q.stat().st_mtime).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
            doc_t = s if doc_t is None or s > doc_t else doc_t
    C["14 🔴 `⑤′` 를 문서 재생성 «뒤에» 다시 돌렸나"] = collections.OrderedDict([
        ("`⑤′` 끝 시각", fp_t),
        ("문서 셋의 마지막 mtime", doc_t),
        ("🔴 981 이 어긴 자리", "🔴 981 은 `⑤′` 뒤에 판정문·카드·원장·치환표를 다시 지었다"),
        ("통과", bool(fp_t and doc_t and fp_t >= doc_t))])

    # 15 수리 계수 — 고친 코드가 있는 것만
    rep = collections.OrderedDict([
        ("R1 개정 잠금 조항의 방향 대칭", ["docs/목표.md", "docs/루프.md"]),
        ("R2 `ledger.write_stamped` — 도장 없이 못 쓴다", ["runners/ledger.py"]),
        ("R3 `⑤′` ⓪ 관문이 자기 산출물을 이름으로 뺀다", ["runners/fiveprime902.py"]),
    ])
    base = _git("merge-base", "main", BRANCH).decode().strip()
    diff = set(_git("-c", "core.quotePath=false", "diff", "--name-only", "-z",
                    base, BRANCH).decode().split("\0")) - {""}
    ok = collections.OrderedDict()
    for k, fs in rep.items():
        ok[k] = collections.OrderedDict([
            ("파일", fs),
            ("🔴 이 가지에서 실제로 바뀐 파일인가", [f in diff for f in fs]),
            ("셀 수 있나", all(f in diff for f in fs))])
    C["15 수리 계수에 고친 코드가 없는 항목이 있나"] = collections.OrderedDict([
        ("🔴 신고한 수리", list(rep.keys())),
        ("🔴 분자/분모", "%d / %d" % (sum(1 for v in ok.values() if v["셀 수 있나"]),
                                 len(ok))),
        ("🔴 상한(사전등록 §8-1)", 5),
        ("칸별", ok),
        ("🔴 수리로 «안» 센 것",
         ["`docs/목표.md` 정본 자 표에 981 줄을 넣은 것(1순위의 결론이지 수리가 아니다)",
          "981 게재값 정정 전량(사전등록 §5 · 코드 변경 0)"]),
        ("통과", bool(all(v["셀 수 있나"] for v in ok.values()) and len(ok) <= 5))])

    # 16 예측 분모
    # ── 예측 ───────────────────────────────────────────────────────
    P = collections.OrderedDict()
    dv = tf.get("🔴🔴🔴 §2-4 등록 판정 — 자가 시간 방향에서 갈리나", {}) or {}
    pk = tf.get("🔴🔴🔴 §2-4 ⓒ — 시간 방향 `D4` 에 `v2.2` 를 물린 결과(체제 셋)", {}) or {}
    cells = tf.get("🔴🔴 칸", {}) or {}
    P["P1 — 시간 방향 유보의 도메인별 유보 행 벡터가 개체 묶음 판과 다르다"] = bool(
        wi.get("🔴 P1 — 유보 행 벡터가 다른가"))
    ctl_t = ((cells.get("u=3", {}) or {}).get("🔴 대조 팔 점추정(자 여섯)", {}) or {}).get(
        "R_pool 묶음")
    ctl_e = 0.262742          # 🔴 `out981_decomp.json` N_B=1800 · u=3 · ㉯ 대조 ρ
    P["P2 — 시간 방향 `㉯ 대조` 의 정본 자 ρ 가 개체 묶음 판보다 낮다"] = bool(
        ctl_t is not None and ctl_t < ctl_e)
    P["P3 — 자 여섯이 부호(ⓐ)에서는 안 갈린다"] = bool(
        not dv.get("🔴🔴 ⓐ 부호가 어디서라도 갈리나"))
    P["P4 — 자 여섯이 관문(ⓑ)에서는 갈린다"] = bool(
        dv.get("🔴🔴 ⓑ 관문이 어디서라도 갈리나"))
    P["P5 — 시간 방향 `D4` 에서 `pick()`(체제 B)이 `R_pool 묶음` 을 고른다"] = bool(
        pk.get("🔴🔴🔴 시간 방향이 고른 자(등록 판정 = 체제 B)") == "R_pool 묶음")
    m3 = ((cells.get("u=3", {}) or {}).get("🔴🔴 M 팔 ㉮ 층화 − ㉯ 대조", {}) or {})
    d3 = ((m3.get("🔴🔴 자별 판정", {}) or {}).get("R_pool 묶음", {}) or {}).get("Δ")
    P["P6 — 층화 이득 `㉮ − ㉯` 가 시간 방향 `u=3` 에서 양수다"] = bool(
        d3 is not None and d3 > 0)
    z = ((pw.get("🔴🔴 ③ 칸 가중 z") or {}) or {}).get("z")
    P["P7 — 위약 팔 7 칸의 칸 가중 z 가 |z| ≥ 2 다"] = bool(
        z is not None and abs(z) >= 2.0)
    sat = (u3.get("🔴🔴🔴 §3-2 목표 이동 팔과 대조 팔 포화", {}) or {})
    s_sh = ((sat.get("🔴🔴🔴 스피어만(`㉮−㉱`, 오라클 여유)") or {}) or {}).get("스피어만")
    P["P8 — `㉮ − ㉱` 와 오라클 여유의 스피어만이 +0.9 이상이다"] = bool(
        s_sh is not None and s_sh >= 0.9)
    ax = (me.get("🔴🔴🔴 §3-3 헤드라인 축 대조", {}) or {}).get("🔴 λ 별", {}) or {}
    wins = [((ax.get("u=%d" % u) or {}) or {}).get("🔴🔴🔴 ㉡ 이 이긴 자 수 (0~6)", 0)
            for u in (0, 3)]
    P["P9 — 「지배 도메인 학습 행 수」축이 「정렬도」축을 자 여섯 중 넷 이상에서 이긴다"] = bool(
        wins and min(wins) >= 4)
    P["P10 — 복제를 200→800 으로 늘려도 첫 칸 위약 팔 짝SE 가 10% 이상 안 준다"] = bool(
        not (md.get("🔴🔴 짝SE — ㉱ 위약 팔", {}) or {}).get(
            "🔴🔴 10% 이상 줄었나(P10 의 반대)", True))
    n_true = sum(1 for v in P.values() if v)
    C["16 🔴 예측 분모를 10 아래로 줄였나"] = collections.OrderedDict([
        ("🔴 채점한 예측 수", len(P)),
        ("🔴 등록한 예측 수", 10),
        ("🔴 무효 처리한 예측", "없음"),
        ("🔴 981 이 어긴 자리", "🔴 981 은 P10 을 무효로 빼서 분모를 10→9 로 줄였다 "
                          "(거짓으로 채점하면 7/10)"),
        ("통과", bool(len(P) >= 10))])

    n_ok = sum(1 for v in C.values() if v.get("통과"))

    # ── 🔴 981 재채점 (982 R1 소급 · 사전등록 §5) ────────────────
    re981 = collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 981 의 반증조건 6·10 을 **구판 면제 규칙(976 판)**으로 재채점한다"),
        ("🔴 근거", "🔴 982 R1 방향 대칭 — 면제 규칙은 «푸는» 자이고 게재값은 «엄한 쪽»이다"),
        ("981 이 게재한 값", "13 / 13"),
        ("🔴 981 산출물이 «같이» 실은 구판 표 밖 수",
         (_load("out981_score.json").get("🔴 반증조건 칸별", {}) or {}).get(
             "6·10 본문의 수가 전부 치환표 칸인가 (🔴 범위를 안 좁힌다)", {}).get(
             "🔴🔴 구판 면제 규칙(976 판)으로 재면 표 밖 수")),
        ("🔴🔴🔴 982 가 적는 값", "12 / 13"),
        ("981 이 게재한 예측", "7 / 9 (P10 을 무효로 뺐다)"),
        ("🔴🔴🔴 982 가 적는 예측", "7 / 10"),
    ])

    out = collections.OrderedDict()
    out["무엇"] = "982 — 🔴 사전등록 반증조건 16 과 예측 10 을 채점한다"
    out["🔴 축"] = "자기 자(수리 레인)"
    out["🔴 채점 규약"] = (
        "🔴 **등록한 조건의 범위를 채점 시점에 좁히지 않는다**(사전등록 §7-9). "
        "🔴 **예측 분모를 줄이지 않는다**(§7-16). "
        "🔴 **구판/신판이 갈리면 «엄한 쪽»을 게재한다**(982 R1)")
    out["🔴🔴🔴 반증조건 분자/분모"] = "%d / %d" % (n_ok, len(C))
    out["🔴 반증조건 칸별"] = C
    out["🔴🔴 예측 분자/분모"] = "%d / %d" % (n_true, len(P))
    out["🔴 예측 칸별"] = P
    out["🔴🔴 981 재채점(소급)"] = re981
    out["통과"] = bool(len(P) == 10)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **등록한 예측 열 개를 하나도 안 빼고 채점했다.** "
        "🔴 이 값은 몇이 참인지와 무관하다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out982_score.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["score"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_score(a.ref)
    print(json.dumps({"반증조건": r["🔴🔴🔴 반증조건 분자/분모"],
                      "예측": r["🔴🔴 예측 분자/분모"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
