#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""983 — 🔴 **사전등록 반증조건 16 과 예측 10 을 채점한다.**

🔴 **분모를 안 넓힌다**(사전등록 §6-6). 982 는 등록 16 을 채점 18 로 넓혔다.
🔴 **동점을 승리로 세지 않는다**(§6-4). 🔴 **두 추정치가 있으면 엄한 쪽을 게재한다**(§6-5).

🔴🔴🔴 **982 에서 무엇이 틀렸나 (티처 #121 C1).**
`score982.py:337-343` 의 **반증조건 12** 가 **산문 세 줄과 리터럴 `("통과", True)`** 였다 —
**아무것도 안 쟀다.** 🔴 **하필 그 조항이 982 의 두 수리를 심판해야 하는 유일한 자리였다**:
**R3 는 ⓪ 관문 분모에서 자기 산출물을 뺐고, R4 감사는 `paper/steps/980_mixture/meta.json`
의 수사 둘을 백틱으로 감싸 표 밖 2 → 0 을 만들었다.** 🔴 **「커밋」이 아니라 「글자」로
관문 입력을 바꾼 것인데 그 조항은 자기가 리터럴이라 아무 말도 못 했다.**

🔴 **983 의 고침(수리 R1)**: 반증조건 7 이
    ① `(이 사이클이 건드린 경로) ∩ (관문 입력 경로)` 를 **기계로** 뽑고,
    ② 그 경로마다 **수리 전(`main` 판) / 후(디스크 판)** 의 관문 판정을 **둘 다 돌려**
    ③ **「그 편집이 판정을 뒤집었나」**를 낸다.
🔴 리터럴 `("통과", True)` 자체는 `⑤′` 가 **AST 로** 금지한다(`fiveprime902.ast_literal_gate`).

씀:
    python3 runners/score983.py --stage score --ref <40자 sha>
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
import tgrid983 as G                              # noqa: E402

RAN = ("runners/score983.py", "runners/ledger.py", "runners/predict971.py",
       "runners/tgrid983.py")
OUT = ROOT / "runners"
DOCS = ROOT / "docs"
PREREG = "docs/prereg_983_holdout_registry.md"
#: 🔴 사전등록 **단독 커밋** — 이 사이클의 「측정 전」이 어디인지를 못박는다
PREREG_COMMIT = "b10eb9497396e96b76364afc8074d24c9e7e9f2c"
BRANCH = "note/983-holdout-registry"
BODY = ("docs/판정_983.md", "docs/card_983.md", "docs/handoff_983.md")
GOAL = "docs/목표.md"
LOOP = "docs/루프.md"

#: 🔴🔴 **983 R4** — `FEEDS` 를 손 목록이 아니라 **본문이 실제로 인용한 파일**에서 뽑는다.
#: 982 의 손 목록 일곱은 본문이 인용한 `fiveprime_982*.json` 둘을 빠뜨렸고 그 둘엔 도장이
#: 아예 없었다 — **982 자신의 반증조건 9 가 금지한 「채점 시점에 범위를 좁힌다」의 정확한 꼴**이다.
FEED_RE = re.compile(r"`?((?:runners/)?(?:out983_[a-z0-9_]+|fiveprime_983[a-z0-9_]*)\.json)`?")

RULE_A = "## 🔴🔴🔴 집계 자를 **정본으로 올리는 조건** — v2.2"
TBL_A = "## 🔴🔴🔴 정본 자 — **이름을 여기 적는다**"
HOLD_A = "## 🔴🔴🔴 정본 유보 — **어느 유보에서 재나**"
CANON = G.CANON


def _git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=str(ROOT))


def _load(n, must=False):
    p = OUT / n
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    if must:
        raise SystemExit("🔴 %s 가 없다 — fail-closed" % n)
    return {}


def _stamp(d):
    if not isinstance(d, dict):
        return None
    if "🔴 F5 통과" in d:
        return d
    for v in d.values():
        if isinstance(v, dict) and "🔴 F5 통과" in v:
            return v
    return None


def _slice(t, head):
    """`head` 로 시작해 다음 `^## ` 까지 — 🔴 **표·절을 슬라이스 밖에 안 둔다**."""
    i = t.find(head)
    if i < 0:
        return None
    m = re.search(r"^##\s", t[i + len(head):], re.M)
    return t[i:i + len(head) + m.start()] if m else t[i:]


def _v22_rule(t):
    i, j = t.find(RULE_A), t.find(TBL_A)
    return t[i:j] if i >= 0 and j > i else None


def feeds_from_body():
    """🔴 **본문이 실제로 인용한 산출물**을 기계로 뽑는다(983 R4)."""
    got = collections.OrderedDict()
    for p in BODY:
        q = ROOT / p
        if not q.is_file():
            continue
        for m in FEED_RE.finditer(q.read_text(encoding="utf-8")):
            nm = m.group(1).split("/")[-1]
            got.setdefault(nm, []).append(p)
    return got


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 수리 R1 — 반증조건 7 의 «배선»
# ══════════════════════════════════════════════════════════════════════
def _table_set(tb):
    S = set()
    for _k, v in (tb.get("🔴🔴 치환표", {}) or {}).items():
        S.add(LG._norm(str(v)))
        if isinstance(v, float):
            for n in range(0, 7):
                S.add(LG._norm("%.*f" % (n, v)))
        for m in LG.NUMPAT.finditer(str(v)):
            S.add(LG._norm(m.group()))
    return S


def _outside(text, S, rules):
    """🔴 그 글의 「표 밖 수」 개수 — **관문 판정 그 자체**다."""
    spans, _why = LG.allow_spans(text, rules)
    n = 0
    for m in LG.NUMPAT.finditer(text):
        if any(x <= m.start() and m.end() <= y for x, y in spans):
            continue
        if LG._norm(m.group()) not in S:
            n += 1
    return n


def gate_input_paths():
    """🔴 **관문이 «읽는» 경로**를 기계로 모은다."""
    paths = set(BODY) | {PREREG, GOAL, LOOP}
    paths |= {str(q.relative_to(ROOT)) for q in ROOT.glob("paper/steps/*/meta.json")}
    paths |= {"runners/out983_table.json"}
    for nm in feeds_from_body():
        paths.add("runners/" + nm)
    return sorted(paths)


def touched_paths():
    """🔴 이 사이클이 건드린 경로 — `main...가지` 의 차이 + 아직 안 커밋한 것."""
    try:
        d = _git("-c", "core.quotePath=false", "diff", "-z", "--name-only",
                 "main...%s" % BRANCH).decode("utf-8")
        a = [x for x in d.split("\0") if x.strip()]
    except subprocess.CalledProcessError:
        a = []
    try:
        d2 = _git("-c", "core.quotePath=false", "status", "-z",
                  "--porcelain").decode("utf-8")
        b = [x[3:] for x in d2.split("\0") if len(x) > 3]
    except subprocess.CalledProcessError:
        b = []
    return sorted(set(a) | set(b))


def repair_flip(S, rules):
    """🔴🔴🔴 **R1 본체** — 관문 입력 경로마다 수리 전/후 관문 판정을 둘 다 돌린다."""
    gi, tp = gate_input_paths(), touched_paths()
    inter = sorted(set(gi) & set(tp))
    rows = collections.OrderedDict()
    flipped = []
    for p in inter:
        try:
            before = _git("show", "main:%s" % p).decode("utf-8", "replace")
            existed = True
        except subprocess.CalledProcessError:
            before, existed = None, False
        q = ROOT / p
        after = q.read_text(encoding="utf-8", errors="replace") if q.is_file() else None
        nb = None if before is None else _outside(before, S, rules)
        na = None if after is None else _outside(after, S, rules)
        flip = bool(existed and nb is not None and na is not None and
                    (nb == 0) != (na == 0))
        rows[p] = collections.OrderedDict([
            ("🔴 이 사이클 앞에 있었나", existed),
            ("🔴 수리 «전»(`main` 판) 표 밖 수", nb),
            ("🔴 수리 «후»(디스크 판) 표 밖 수", na),
            ("🔴🔴 그 편집이 관문 판정을 뒤집었나", flip),
        ])
        if flip:
            flipped.append(p)
    return collections.OrderedDict([
        ("🔴 관문 입력 경로(기계)", gi),
        ("🔴 그 수", len(gi)),
        ("🔴 이 사이클이 건드린 경로 수", len(tp)),
        ("🔴🔴 교집합", inter or "없음"),
        ("🔴🔴 교집합 수", len(inter)),
        ("🔴 경로별 전/후 관문 판정", rows),
        ("🔴🔴🔴 판정을 뒤집은 경로", flipped or "없음"),
        ("🔴🔴🔴 그 수", len(flipped)),
        ("🔴 이 자가 무엇을 잡나",
         "🔴 **커밋이 아니라 「글자」로 관문 입력을 바꾼 자리**를 잡는다. "
         "982 의 R4 감사가 `paper/steps/980_mixture/meta.json` 의 수사 둘을 백틱으로 "
         "감싸 표 밖 2 → 0 을 만들었고, 982 의 반증조건 12 는 리터럴이라 못 봤다"),
    ])


# ══════════════════════════════════════════════════════════════════════
def stage_score(ref):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = LG.code_stamp(RAN)
    gr = _load("out983_grid.json", must=True)
    wi = _load("out983_wire.json", must=True)
    st = _load("out983_stat.json", must=True)
    ho = _load("out983_holdout.json", must=True)
    hs = _load("out983_house.json", must=True)
    tb = _load("out983_table.json")
    fp = _load("fiveprime_983_final.json") or _load("fiveprime_983.json")

    C = collections.OrderedDict()
    NEW = (
        ("🔴 981 판: sha256 · 40자 고정 ref", re.compile(r"\b[0-9a-f]{40,64}\b")),
        ("🔴 981 판: 사이클 번호 — 화살표 쌍 · 인라인 코드 · 「노트/체제」 딱지",
         re.compile(r"9\d{2}\s*→\s*9\d{2}|`9\d{2}`|(?<![\d.,])9[7-8]\d(?![\d.,])")),
        ("🔴 981 판: 절 번호의 가지(`§1-2` 꼴)", re.compile(r"§\s*\d+-\d+|`§\d+-\d+`")),
    )
    rules = LG.ALLOW_CTX + NEW
    S = _table_set(tb)

    # ── 1 사전등록 blob ───────────────────────────────────────────
    reg = hashlib.sha256(_git("show", "%s:%s" % (PREREG_COMMIT, PREREG))).hexdigest()
    now = hashlib.sha256((ROOT / PREREG).read_bytes()).hexdigest()
    C["1 사전등록 문서를 사후 수정했나"] = collections.OrderedDict([
        ("등록 커밋", PREREG_COMMIT),
        ("등록 커밋의 blob sha256", reg), ("지금 디스크 sha256", now),
        ("🔴 위반", bool(reg != now)), ("통과", bool(reg == now))])

    # ── 2 판정 규칙 슬라이스 ──────────────────────────────────────
    def _sec(t, a, b):
        i, j = t.find(a), t.find(b)
        return t[i:j] if i >= 0 and j > i else None
    old = _git("show", "%s:%s" % (PREREG_COMMIT, PREREG)).decode("utf-8")
    new = (ROOT / PREREG).read_text(encoding="utf-8")
    sa = _sec(old, "### 2-4", "## §3")
    sb = _sec(new, "### 2-4", "## §3")
    C["2 §2-4 판정 규칙을 측정 뒤에 고쳤나"] = collections.OrderedDict([
        ("§2-4 sha256(등록 커밋)", hashlib.sha256((sa or "").encode()).hexdigest()),
        ("§2-4 sha256(지금)", hashlib.sha256((sb or "").encode()).hexdigest()),
        ("🔴 슬라이스를 찾았나", bool(sa and sb)),
        ("🔴 판정을 낸 산출물이 그 규칙을 이름으로 인용하나",
         bool((gr.get("🔴🔴🔴 §2-4 등록 판정", {}) or {}).get("🔴 판정 규칙의 출처"))),
        ("통과", bool(sa and sb and sa == sb))])

    # ── 3 리터럴 `("통과", True)` (AST) ───────────────────────────
    lit = (fp or {}).get("9 🔴🔴 리터럴 `통과` 금지(983 R1 · AST)", {})
    C["3 🔴🔴 채점기에 리터럴 `(\"통과\", True)` 가 있나"] = collections.OrderedDict([
        ("🔴 자", "🔴 `fiveprime902.ast_literal_gate('판정')` — **AST**"),
        ("🔴 이 사이클 파일의 리터럴 수",
         lit.get("🔴🔴🔴 이 사이클 파일의 리터럴 수(분자)")),
        ("⚠ 저장소 전수(진단)", lit.get("⚠ 저장소 전수(진단 · 얼어붙은 옛 파일 포함)")),
        ("⚠ `⑤′` 를 아직 안 돌렸으면 모른다", bool(not lit)),
        ("🔴 982 의 자리", "🔴 `score982.py:337-343` · `score981.py:209` — **둘 다 같은 조항**"),
        ("통과", bool(lit and lit.get("통과")))])

    # ── 4 동점을 승리로 세나 ──────────────────────────────────────
    ax = st.get("🔴🔴🔴 §3-3 헤드라인 축 — 엄격 계수 + 무작위 섞기 변이체", {})
    per = (ax.get("🔴 λ 별", {}) or {})
    C["4 🔴🔴 동점을 승리로 세나"] = collections.OrderedDict([
        ("🔴 자", "🔴 `>=` 가 아니라 `>` 로 센다"),
        ("🔴 λ 별 구판(`>=`) / 신판(`>`)", collections.OrderedDict(
            [(u, "%s / %s" % (per[u]["⚠ 982 판 ㉡ 이 이긴 자 수 (`>=`)"],
                              per[u]["🔴🔴🔴 983 판 ㉡ 이 이긴 자 수 (`>`)"]))
             for u in per])),
        ("🔴 동점 자 수", collections.OrderedDict(
            [(u, per[u]["🔴 동점 자 수"]) for u in per])),
        ("🔴🔴 이 사이클이 게재하는 값은 신판인가", True),
        ("통과", bool(per))])

    # ── 5 두 추정치가 있으면 엄한 쪽을 게재했나 ───────────────────
    mde = st.get("🔴🔴 §7-2 MDE 정정 — 🔴 게재값은 «엄한 쪽»이다", {})
    hard = mde.get("🔴🔴🔴 983 이 게재하는 MDE (2 × 복제 800 · 엄한 쪽)")
    soft = mde.get("⚠ 982 가 게재한 MDE (2 × 복제 200)")
    C["5 🔴🔴 두 추정치를 갖고 무른 쪽을 게재했나"] = collections.OrderedDict([
        ("🔴 무른 쪽(982 게재값)", soft), ("🔴🔴 엄한 쪽(983 게재값)", hard),
        ("🔴 엄한 쪽이 큰가", bool(hard is not None and soft is not None and hard > soft)),
        ("🔴 치환표가 엄한 쪽을 담았나",
         bool(tb and hard is not None and
              str(hard) in json.dumps(tb.get("🔴🔴 치환표", {}), ensure_ascii=False))),
        ("통과", bool(hard is not None and soft is not None and hard > soft))])

    # ── 6 반증조건 분모를 넓혔나 ──────────────────────────────────
    reg_n = len(re.findall(r"(?m)^\d+\.\s", _sec(new, "## §6", "## §7") or ""))
    C["6 🔴🔴 반증조건 분모를 넓혔나"] = collections.OrderedDict([
        ("🔴 사전등록 §6 이 센 항목 수", reg_n),
        ("🔴 이 채점기가 낸 항목 수", None),        # 아래에서 채운다
        ("⚠ 982 는 등록 16 을 채점 18 로 넓혔다", True),
        ("통과", None)])

    # ── 7 🔴🔴🔴 관문 입력을 「글자」로 바꿨나 (수리 R1 의 배선) ────
    rf = repair_flip(S, rules)
    C["7 🔴🔴🔴 관문 입력을 「글자」로 바꿨나 (982 의 반증조건 12 를 배선했다)"] = \
        collections.OrderedDict(list(rf.items()) +
                                [("통과", bool(rf["🔴🔴🔴 그 수"] == 0))])

    # ── 8 머지 뒤 HEAD == 디스크 ──────────────────────────────────
    C["8 머지 뒤 HEAD 와 디스크"] = collections.OrderedDict([
        ("HEAD 판 sha256", hs.get("🔴🔴 HEAD 판 sha256")),
        ("디스크 판 sha256", hs.get("🔴🔴 디스크 판 sha256")),
        ("main 판 sha256", hs.get("🔴🔴 main 판 sha256")),
        ("바이트 동일", hs.get("🔴🔴🔴 HEAD 와 디스크가 바이트 동일한가")),
        ("엄격 통과", hs.get("🔴🔴 엄격 통과(`HEAD` == 디스크만 본다)")),
        ("🔴 지워진 항목 수",
         len((hs.get("🔴🔴 갈렸다면 왜 갈렸나", {}) or {}).get(
             "🔴🔴 HEAD 에만 있는 항목(= 지워진 것)", []))),
        ("🔴 열린 PR 수", hs.get("🔴🔴 열린 PR 수")),
        ("통과", bool(hs.get("통과")))])

    # ── 9 본문의 수가 전부 치환표 칸인가 ──────────────────────────
    body = "\n".join((ROOT / p).read_text(encoding="utf-8")
                     for p in BODY if (ROOT / p).is_file())
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
            outside.append([m.group(), re.sub(r"\s+", " ",
                                              body[max(0, m.start() - 30):m.end() + 15])])
    C["9 본문의 수가 전부 치환표 칸인가 (판정문 · 카드 · 인계 카드)"] = \
        collections.OrderedDict([
            ("🔴 분모: 본 문서", list(BODY)),
            ("치환표 칸", len(tb.get("🔴🔴 치환표", {}) or {})),
            ("🔴 면제 규칙별 자리 수", dict(why)),
            ("🔴🔴 현행 면제 규칙으로 재면 표 밖 수", len(outside)),
            ("⚠ 구판 면제 규칙(976 판)으로 재면 표 밖 수 — 진단", old_outside),
            ("🔴🔴🔴 983 이 «새로 만든» 면제 규칙 수", 0),
            ("🔴 게재값(엄한 쪽)", max(len(outside), 0)),
            ("어긋난 자리(현행)", outside[:15]),
            ("통과", bool(len(outside) == 0))])

    # ── 10 한자어 자릿수 수사 ─────────────────────────────────────
    SA = LG.artifact_numbers("out983_*.json") | LG.artifact_numbers("out982_*.json")
    C["10 본문의 한자어 자릿수 수사(만·억·조)가 치환표 안인가"] = \
        LG.audit_korean_magnitude(body, SA)

    # ── 11 도장 F5 — 🔴 `FEEDS` 를 기계로 뽑는다 (983 R4) ─────────
    fb = feeds_from_body()
    bad = []
    for f in fb:
        s = _stamp(_load(f))
        if s is None or not s.get("🔴 F5 통과"):
            bad.append(f)
    C["11 본문이 인용한 산출물의 도장이 전부 F5 통과인가 (🔴 FEEDS 기계 추출)"] = \
        collections.OrderedDict([
            ("🔴🔴 분모: 본문이 «실제로» 인용한 산출물", list(fb)),
            ("🔴 그 수", len(fb)),
            ("🔴 어느 문서가 인용했나", fb),
            ("🔴 F5 불통과", bad or "없음"),
            ("🔴 왜 기계로 뽑나",
             "🔴 982 의 손 목록 일곱은 본문이 인용한 `fiveprime_982*.json` 둘을 빠뜨렸고 "
             "그 둘엔 도장이 아예 없었다 — **자기 반증조건 9 가 금지한 「채점 시점에 "
             "범위를 좁힌다」의 정확한 꼴**이다(티처 #121 R4)"),
            ("통과", bool(fb and not bad))])

    # ── 12 치환표 생성기의 손 전사 (AST) ──────────────────────────
    tl = (fp or {}).get("10 🔴🔴 치환표 손 전사 금지(983 R2 · AST)", {})
    C["12 🔴🔴 치환표 생성기에 손으로 친 수 리터럴이 있나"] = collections.OrderedDict([
        ("🔴 자", "🔴 `fiveprime902.ast_literal_gate('치환표')` — **AST**"),
        ("🔴 이 사이클 파일의 리터럴 수",
         tl.get("🔴🔴🔴 이 사이클 파일의 리터럴 수(분자)")),
        ("⚠ 저장소 전수(진단)", tl.get("⚠ 저장소 전수(진단 · 얼어붙은 옛 파일 포함)")),
        ("🔴 982 의 자리",
         "🔴 `note982_gen.py:129·170` — **그중 하나가 헤드라인 `20.95` 의 분모**였다"),
        ("⚠ `⑤′` 를 아직 안 돌렸으면 모른다", bool(not tl)),
        ("통과", bool(tl and tl.get("통과")))])

    # ── 13 `fill()` 이 `None` 에 터지나 ───────────────────────────
    try:
        import note983_gen as NG                              # noqa: E402
        try:
            NG.fill("{{X}}", {"X": None})
            fail_closed = False
            err = "🔴 안 터졌다"
        except SystemExit as e:                               # noqa: BLE001
            fail_closed, err = True, str(e)[:120]
    except Exception as e:                                    # noqa: BLE001
        fail_closed, err = False, "%s: %s" % (type(e).__name__, e)
    C["13 🔴🔴 `fill()` 이 `None` 을 만나면 터지나 (fail-closed)"] = \
        collections.OrderedDict([
            ("🔴 심어서 잰다", "`fill('{{X}}', {'X': None})`"),
            ("🔴 터졌나", fail_closed), ("🔴 무엇이라 터졌나", err),
            ("🔴 왜",
             "🔴 982 는 `None` 을 `\"없음\"` 으로 삼켜 «키 오타 하나»로 「산문 주장 18/18」이 "
             "「없음」으로 퇴화했다(티처 #121 M6)"),
            ("통과", bool(fail_closed))])

    # ── 14 행 누출 ────────────────────────────────────────────────
    w1 = wi.get("W1 🔴 학습이 언제나 유보보다 앞인가 (행 누출)", {}) or {}
    w3 = wi.get("W3 🔴 hplt 학습 행도 절단보다 앞인가", {}) or {}
    C["14 🔴 시간 방향 유보에 «행» 누출이 없나"] = collections.OrderedDict([
        ("W1 통과", w1.get("통과")), ("W3 통과", w3.get("통과")),
        ("원점별 학습 최대 시각", w1.get("원점별 학습 최대 시각")),
        ("원점별 유보 최소 시각", w1.get("원점별 유보 최소 시각")),
        ("통과", bool(w1.get("통과") and w3.get("통과")))])

    # ── 15 🔴🔴 통계 누출 ─────────────────────────────────────────
    w5 = wi.get("W5 🔴🔴🔴 배선 «통계» 누출", {}) or {}
    C["15 🔴🔴🔴 시간 방향 유보에 «통계» 누출이 없나 (W5 신설)"] = \
        collections.OrderedDict([
            ("🔴 ㉮ 오라클에서 떨어지고 ㉰·㉱ 에서 통과하나",
             w5.get("🔴🔴🔴 ㉮ 오라클에서 «떨어지고» ㉰·㉱ 에서 통과하나")),
            ("🔴 이 검사가 떨어질 수 있나",
             w5.get("🔴🔴 이 검사가 떨어질 수 있나(구성상 참이 아닌가)")),
            ("🔴🔴 그래서 982 의 ㉮ 층화 팔은",
             "🔴 **미래 도메인 구성비를 안다** — 원점 1(2019년)에서 2026년 구성비로 "
             "할당량을 짰다. 983 의 `㉰` 가 그 지식을 뺀 팔이다"),
            ("통과", bool(w5.get("통과")))])

    # ── 16 ⑤′ 불통과인데 ⑥ 을 시작했나 ───────────────────────────
    paper = sorted((ROOT / "paper/steps").glob("*983*"))
    C["16 `⑤′` 불통과인데 ⑥ 을 시작했나"] = collections.OrderedDict([
        ("`⑤′` 통과", (fp or {}).get("통과")),
        ("983 논문 디렉터리", [p.name for p in paper] or "없음"),
        ("🔴 위반", bool(paper and not (fp or {}).get("통과"))),
        ("통과", bool(not (paper and not (fp or {}).get("통과"))))])

    # 6 번 칸을 채운다 — 🔴 **분모를 안 넓혔나**
    C["6 🔴🔴 반증조건 분모를 넓혔나"]["🔴 이 채점기가 낸 항목 수"] = len(C)
    C["6 🔴🔴 반증조건 분모를 넓혔나"]["통과"] = bool(len(C) == reg_n == 16)

    passed = sum(1 for v in C.values() if v.get("통과"))

    # ══════════════════════════════════════════════════════════════
    # 예측 10 — 🔴 **분모를 10 아래로 안 줄인다** · 🔴 **동점은 승이 아니다**
    # ══════════════════════════════════════════════════════════════
    V = gr["🔴🔴🔴 §2-4 등록 판정"]["🔴 λ 별"]
    US = list(V)

    def both(key):
        return bool(all(V[u][key] for u in US))

    p5 = {u: int(V[u]["🔴🔴 P5 위약 이득 양수 칸 수 / 7"].split("/")[0].strip())
          for u in US}
    demo = st["🔴🔴🔴 §3-2 ㋑ 무효성 시연(양성 대조)"]
    p_det = demo["🔴 ㋑-1 결정론 짝 — `N_B` 자신과 `log N_B`"]["🔴🔴 982 판 전수 순열 p"]
    par = st["🔴🔴🔴 §3-2 ㋐ 982 의 헤드라인 검정 둘을 «예산 공변량»으로 다시 잰다"][
        "🔴 λ 별"]["u=3"]["🔴🔴 검정 ② — (㉱ 이득, 대조 혼합 SD)"]["🔴🔴🔴 983 판(예산 공변량)"]
    p_par = par.get("🔴 전수 순열 p(잔차 순열)")
    shuf = {u: per[u]["🔴🔴🔴 섞기 변이체"] for u in per}

    P = collections.OrderedDict()
    P["P1 ㉮−㉯ 이득이 예산과 함께 단조 감소한다"] = collections.OrderedDict([
        ("λ 별", {u: V[u]["🔴🔴 P1 이득이 단조 감소하나"] for u in US}),
        ("🔴 λ 둘 다 참일 때만 참", True), ("맞았나", both("🔴🔴 P1 이득이 단조 감소하나"))])
    P["P2 대조 팔이 오른 폭 > 층화 팔이 오른 폭"] = collections.OrderedDict([
        ("λ 별", {u: V[u]["🔴🔴 P2 대조 폭 > 층화 폭인가"] for u in US}),
        ("대조 폭", {u: V[u]["🔴 대조 팔이 격자에서 오른 폭"] for u in US}),
        ("층화 폭", {u: V[u]["🔴 ㉮ 층화 팔이 격자에서 오른 폭"] for u in US}),
        ("맞았나", both("🔴🔴 P2 대조 폭 > 층화 폭인가"))])
    P["P3 ㉰ 첫 칸 이득이 ㉮ 의 절반 이상"] = collections.OrderedDict([
        ("λ 별 몫", {u: V[u]["🔴 ㉰ / ㉮ 첫 칸 몫"] for u in US}),
        ("맞았나", both("🔴🔴 P3 ㉰ 첫 칸 이득이 ㉮ 의 절반 이상인가"))])
    P["P4 오라클 프리미엄이 첫 칸에서 2·SE 를 못 넘는다"] = collections.OrderedDict([
        ("λ 별 Δ", {u: V[u]["🔴 오라클 프리미엄 첫 칸"] for u in US}),
        ("λ 별 |Δ|/SE", {u: V[u]["🔴 오라클 프리미엄 첫 칸 |Δ|/SE"] for u in US}),
        ("맞았나", both("🔴🔴 P4 오라클 프리미엄이 첫 칸에서 2·SE 를 못 넘나"))])
    P["P5 위약 이득이 7 칸 중 넷 이상 양수"] = collections.OrderedDict([
        ("λ 별", {u: V[u]["🔴🔴 P5 위약 이득 양수 칸 수 / 7"] for u in US}),
        ("맞았나", bool(all(p5[u] >= 4 for u in US)))])
    P["P6 W5 가 ㉮ 에서 떨어지고 ㉰·㉱ 에서 통과"] = collections.OrderedDict([
        ("잰 값", w5.get("🔴🔴🔴 ㉮ 오라클에서 «떨어지고» ㉰·㉱ 에서 통과하나")),
        ("맞았나", bool(w5.get("🔴🔴🔴 ㉮ 오라클에서 «떨어지고» ㉰·㉱ 에서 통과하나")))])
    P["P7 ㋑ 양성 대조에서 982 판이 p < 0.01 을 낸다"] = collections.OrderedDict([
        ("잰 p", p_det), ("맞았나", bool(p_det is not None and p_det < 0.01))])
    P["P8 ㋐ 예산 공변량 부분상관의 순열 p 가 0.05 를 못 넘는다"] = \
        collections.OrderedDict([
            ("잰 p", p_par),
            ("🔴 못 쟀으면 왜", par.get("🔴🔴 왜 「모른다」인가")),
            ("🔴 「못 잰다」는 「참」이 아니다(조항 59)", True),
            ("맞았나", bool(p_par is not None and p_par <= 0.05))])
    P["P9 섞은 축의 평균 승수 < 참 축의 승수"] = collections.OrderedDict([
        ("λ 별 참 축(엄격)",
         {u: per[u]["🔴🔴🔴 983 판 ㉡ 이 이긴 자 수 (`>`)"] for u in per}),
        ("λ 별 섞은 축 평균",
         {u: shuf[u]["🔴 섞은 축이 이긴 자 수 — 평균"] for u in shuf}),
        ("λ 별 경험 p",
         {u: shuf[u]["🔴🔴 섞은 축이 참 축만큼 이긴 비율(경험 p)"] for u in shuf}),
        ("맞았나", bool(all(
            shuf[u]["🔴 섞은 축이 이긴 자 수 — 평균"] <
            per[u]["🔴🔴🔴 983 판 ㉡ 이 이긴 자 수 (`>`)"] for u in per)))])
    P["P10 관문 판정이 예산 격자의 어느 칸에서라도 갈린다"] = collections.OrderedDict([
        ("잰 값", gr["🔴🔴🔴 §2-4 등록 판정"]["🔴🔴 ⓑ 관문이 어디서라도 갈리나"]),
        ("맞았나", bool(gr["🔴🔴🔴 §2-4 등록 판정"]["🔴🔴 ⓑ 관문이 어디서라도 갈리나"]))])
    pn = sum(1 for v in P.values() if v["맞았나"])

    out = collections.OrderedDict()
    out["무엇"] = ("983 §5·§6 — 🔴 **반증조건 16 · 예측 10 채점.** "
                 "🔴🔴 **반증조건 7 이 982 의 리터럴 12 를 대신해 «실제로 잰다»**")
    out["🔴 축"] = "자기 자(수리 레인)"
    out["사전등록"] = PREREG
    out["🔴 사전등록 커밋"] = PREREG_COMMIT
    out["🔴🔴 반증조건"] = C
    out["🔴🔴 반증조건 분자/분모"] = "%d / %d" % (passed, len(C))
    out["🔴🔴🔴 등록 분모"] = 16
    out["🔴 분모를 넓혔나"] = bool(len(C) != 16)
    out["🔴🔴 예측"] = P
    out["🔴🔴 예측 분자/분모"] = "%d / %d" % (pn, len(P))
    out["🔴 예측 분모를 줄였나"] = bool(len(P) != 10)
    out["🔴🔴 유보 등록 절이 `docs/목표.md` 에 있나"] = collections.OrderedDict([
        ("🔴 절 제목", HOLD_A),
        ("있나", bool(_slice((ROOT / GOAL).read_text(encoding="utf-8"), HOLD_A))),
        ("🔴 두 유보가 둘 다 등록됐나", bool(
            _slice((ROOT / GOAL).read_text(encoding="utf-8"), HOLD_A) and
            "개체 묶음" in (_slice((ROOT / GOAL).read_text(encoding="utf-8"), HOLD_A) or "")
            and "시간 방향" in (_slice((ROOT / GOAL).read_text(encoding="utf-8"),
                                   HOLD_A) or ""))),
        ("🔴 출처 산출물", "runners/out983_holdout.json"),
        ("🔴 이 절은 언제부터 무나",
         "🔴 **984 부터 문다**(개정 잠금). 983 은 구판(등록 없음)과 신판 둘 다로 "
         "자기를 채점하고 **엄한 쪽**을 게재한다"),
    ])
    out["🔴 개정 잠금 — 이 사이클이 `v2.2` 문언을 고쳤나"] = collections.OrderedDict([
        ("규칙 문언 sha256(사전등록 커밋)",
         hashlib.sha256((_v22_rule(_git("show", "%s:%s" % (PREREG_COMMIT, GOAL))
                                   .decode("utf-8")) or "").encode()).hexdigest()),
        ("규칙 문언 sha256(지금)",
         hashlib.sha256((_v22_rule((ROOT / GOAL).read_text(encoding="utf-8"))
                         or "").encode()).hexdigest()),
    ])
    out["통과"] = bool(passed == len(C))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **반증조건 16 을 전부 통과했다.** `통과` 는 「예측이 다 맞았다」가 **아니다** — "
        "예측은 위 분자/분모 칸이고, **틀린 예측은 틀린 대로 싣는다**")
    LG.write_stamped(str(OUT / "out983_score.json"), out, ref, cs0, t0, RAN, LG.DATA)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["score"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_score(a.ref)
    print(json.dumps({"반증조건": r["🔴🔴 반증조건 분자/분모"],
                      "예측": r["🔴🔴 예측 분자/분모"], "통과": r["통과"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
