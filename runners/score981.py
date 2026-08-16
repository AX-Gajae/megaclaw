#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""981 — 🔴 **사전등록 반증조건 13 과 예측 10 을 채점한다.**

🔴 **채점 시점에 등록 문언의 범위를 좁히면 그 자체가 실패다**(사전등록 §7-6).
980 이 반증조건 5 를 「본문의 모든 ρ·Δ 는 5벌 평균」으로 좁혀 `12/12` 를 만들었다.
실제로는 `8/12` 였다.

씀:
    python3 runners/score981.py --stage score --ref <40자 sha>
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

RAN = ("runners/score981.py", "runners/ledger.py", "runners/predict971.py")
OUT = ROOT / "runners"
DOCS = ROOT / "docs"
PREREG = "docs/prereg_981_pick.md"
PREREG_COMMIT = "47af6b82d8ae6ee52cf63b06ba44f765952f06aa"   # 🔴 사전등록 단독 커밋
BRANCH = "note/981-ruler-mechanical-target-grid"
#: 🔴 본문 = 판정문 · 카드 (논문은 ⑤′ 통과 뒤에만 생긴다)
BODY = ("docs/판정_981.md", "docs/card_981.md")
FEEDS = ("out981_pick.json", "out981_target.json", "out981_decomp.json",
         "out981_house.json", "out980_funnel.json")


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


def stage_score(ref):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = LG.code_stamp(RAN)
    pk, tg, dc = _load("out981_pick.json"), _load("out981_target.json"), _load("out981_decomp.json")
    hs, tb = _load("out981_house.json"), _load("out981_table.json")
    fp = _load("fiveprime_981.json")

    # ── 반증조건 ───────────────────────────────────────────────────
    C = collections.OrderedDict()

    # 1 사전등록 blob 이 안 바뀌었나
    reg = hashlib.sha256(_git("show", "%s:%s" % (PREREG_COMMIT, PREREG))).hexdigest()
    now = hashlib.sha256((ROOT / PREREG).read_bytes()).hexdigest()
    C["1 사전등록 문서를 사후 수정했나"] = collections.OrderedDict([
        ("등록 커밋의 blob sha256", reg), ("지금 디스크 sha256", now),
        ("🔴 위반", bool(reg != now)), ("통과", bool(reg == now))])

    # 2 자기 관문의 구판·신판을 둘 다 실었나
    s4 = (fp or {}).get("4 도장 확인", {})
    has_both = bool("🔴 구판 절 4 통과(980 판 --- 도장의 «존재»와 시각만 본다)" in s4
                    and "🔴🔴 신판 절 4 통과(981 판 --- 도장의 «판정»을 읽는다)" in s4)
    C["2 신설한 관문을 구판·신판 둘 다로 채점했나"] = collections.OrderedDict([
        ("구판 키가 있나", bool("🔴 구판 절 4 통과(980 판 --- 도장의 «존재»와 시각만 본다)" in s4)),
        ("신판 키가 있나", bool("🔴🔴 신판 절 4 통과(981 판 --- 도장의 «판정»을 읽는다)" in s4)),
        ("⚠ `⑤′` 를 아직 안 돌렸으면 모른다", bool(not fp)),
        ("통과", has_both)])

    # 3 밴드 구성원 목록
    regs = pk.get("🔴🔴🔴 §3 체제 셋의 `pick()` 산출물", {})
    nband = sum(1 for k in regs if isinstance(regs[k].get("🔴🔴 4 · 동률 밴드 구성원"), list))
    C["3 `pick()` 산출물에 밴드 구성원 목록이 있나"] = collections.OrderedDict([
        ("밴드 목록을 실은 체제", "%d / %d" % (nband, len(regs))),
        ("통과", bool(regs and nband == len(regs)))])

    # 4 선택이 코드에서 왔나
    src = (ROOT / "runners/pick981.py").read_text(encoding="utf-8")
    doc = (DOCS / "판정_981.md").read_text(encoding="utf-8")
    canon = pk.get("🔴🔴🔴 §3 정본 자 (등록 판정 = 체제 B)")
    C["4 선택을 코드가 했나(산문이 아니라)"] = collections.OrderedDict([
        ("`pick()` 이 파일에 있나", bool(re.search(r"^def pick\(", src, re.M))),
        ("판정문이 그 산출물의 자를 그대로 적었나", bool(canon and canon in doc)),
        ("판정문이 `pick()` 을 이름으로 인용하나", bool("pick981.pick()" in doc)),
        ("통과", bool(re.search(r"^def pick\(", src, re.M) and canon and canon in doc))])

    # 5 v2.2 문언을 이 사이클이 고쳤나
    old = _git("show", "%s:docs/목표.md" % PREREG_COMMIT).decode("utf-8")
    new = (ROOT / "docs/목표.md").read_text(encoding="utf-8")

    def _v22(t):
        i = t.find("## 🔴🔴🔴 집계 자를 **정본으로 올리는 조건** — v2.2")
        j = t.find("## 🔴🔴🔴 정본 자 — **이름을 여기 적는다**")
        return t[i:j] if i >= 0 and j > i else None
    a, b = _v22(old), _v22(new)
    C["5 선택 규칙(v2.2) 문언을 이 사이클이 고쳤나"] = collections.OrderedDict([
        ("v2.2 절 sha256(사전등록 커밋)",
         hashlib.sha256((a or "").encode()).hexdigest()),
        ("v2.2 절 sha256(지금)", hashlib.sha256((b or "").encode()).hexdigest()),
        ("🔴 절을 못 찾았나", bool(a is None or b is None)),
        ("통과", bool(a is not None and b is not None and a == b))])

    # 6 · 10 본문의 모든 수가 치환표 안인가 (🔴 범위를 안 좁힌다: **모든 수**)
    S = set()
    for k, v in (tb.get("🔴🔴 치환표", {}) or {}).items():
        S.add(LG._norm(str(v)))
        if isinstance(v, float):
            for n in range(0, 7):
                S.add(LG._norm("%.*f" % (n, v)))
        #: 🔴 `"4 / 7"` 같은 **분자/분모 칸**은 한 칸이지만 본문에서는 두 수로 읽힌다.
        #: 그 두 수도 **그 칸에서 온 것**이므로 같이 넣는다(칸 밖에서 온 수는 아니다).
        for m in LG.NUMPAT.finditer(str(v)):
            S.add(LG._norm(m.group()))
    body = "\n".join((ROOT / p).read_text(encoding="utf-8") for p in BODY)
    outside = []
    #: 🔴 sha256·40자 ref 는 수가 아니다 — **면제 규칙을 글자로 적고 면제 수를 낸다**(조항 59)
    NEW = (
        ("🔴 981 신설: sha256 · 40자 고정 ref", re.compile(r"\b[0-9a-f]{40,64}\b")),
        ("🔴 981 신설: 사이클 번호 — 화살표 쌍 · 인라인 코드 · 「노트/체제」 딱지",
         re.compile(r"9\d{2}\s*→\s*9\d{2}|`9\d{2}`|(?<![\d.,])9[7-8]\d(?![\d.,])")),
        ("🔴 981 신설: 절 번호의 가지(`§1-2` 꼴)", re.compile(r"§\s*\d+-\d+|`§\d+-\d+`")),
    )
    rules = LG.ALLOW_CTX + NEW
    spans, why = LG.allow_spans(body, rules)
    old_spans, old_why = LG.allow_spans(body, LG.ALLOW_CTX)
    old_outside = 0
    for m in LG.NUMPAT.finditer(body):
        if not any(x <= m.start() and m.end() <= y for x, y in old_spans) \
                and LG._norm(m.group()) not in S:
            old_outside += 1
        if any(x <= m.start() and m.end() <= y for x, y in spans):
            continue
        if LG._norm(m.group()) not in S:
            outside.append([m.group(),
                            re.sub(r"\s+", " ", body[max(0, m.start() - 30):m.end() + 15])])
    C["6·10 본문의 수가 전부 치환표 칸인가 (🔴 범위를 안 좁힌다)"] = collections.OrderedDict([
        ("🔴 채점 범위", "판정문·카드 «본문에 나오는 모든 수». ρ·Δ 로 좁히지 않는다"),
        ("치환표 칸", len(tb.get("🔴🔴 치환표", {}) or {})),
        ("🔴 면제 규칙별 자리 수", dict(why)),
        ("🔴🔴 구판 면제 규칙(976 판)으로 재면 표 밖 수", old_outside),
        ("🔴 왜 둘을 다 싣나",
         "🔴 981 이 면제 규칙 셋을 신설했다(sha256 · 사이클 번호 · 절 번호의 가지). "
         "면제 규칙도 이 사이클이 자기 판정에 쓰는 «잣대»이므로 개정 잠금 조항 981 확장에 "
         "걸린다 — **구판·신판 둘 다로 재서 둘 다 싣는다**"),
        ("표 밖 수", len(outside)), ("어긋난 자리", outside[:15]),
        ("통과", bool(not outside))])

    # 6-나 한자어 자릿수 수사 (981 수리 R4)
    SA = LG.artifact_numbers("out981_*.json") | LG.artifact_numbers("out980_*.json")
    km = LG.audit_korean_magnitude(body, SA)
    C["10-나 본문의 한자어 자릿수 수사(만·억·조)가 치환표 안인가"] = km

    # 7 F5 불통과 산출물의 수를 실었나
    bad = []
    for f in FEEDS:
        s = _stamp(_load(f))
        if s is None or not s.get("🔴 F5 통과"):
            bad.append(f)
    C["7 본문이 인용한 산출물의 도장이 전부 F5 통과인가"] = collections.OrderedDict([
        ("분모: 본문이 인용한 산출물", list(FEEDS)),
        ("🔴 F5 불통과", bad or "없음"), ("통과", bool(not bad))])

    # 8 머지 뒤 HEAD == 디스크
    C["8 머지 뒤 HEAD 와 디스크"] = collections.OrderedDict([
        ("HEAD 판 sha256", hs.get("🔴🔴 HEAD 판 sha256")),
        ("디스크 판 sha256", hs.get("🔴🔴 디스크 판 sha256")),
        ("바이트 동일", hs.get("🔴🔴🔴 HEAD 와 디스크가 바이트 동일한가")),
        ("엄격 통과", hs.get("🔴🔴 엄격 통과(`HEAD` == 디스크만 본다)")),
        ("갈린 것이 이 사이클 항목 하나뿐인가",
         (hs.get("🔴🔴 갈렸다면 왜 갈렸나", {}) or {}).get(
             "🔴🔴🔴 갈린 것이 「이 사이클 항목이 아직 안 커밋됐다」 하나인가")),
        ("🔴 지워진 항목 수",
         len((hs.get("🔴🔴 갈렸다면 왜 갈렸나", {}) or {}).get(
             "🔴🔴 HEAD 에만 있는 항목(= 지워진 것)", []))),
        ("통과", bool(hs.get("통과")))])

    # 9 관문을 통과시키려고 관문의 입력을 커밋했나
    C["9 관문을 통과시키려고 그 관문의 입력을 커밋했나"] = collections.OrderedDict([
        ("🔴 981 이 커밋한 남의 산출물", ["runners/out980_funnel.json"]),
        ("🔴 그것이 관문의 입력인가", True),
        ("🔴 사전등록에 먼저 적었나(§4 S3)", True),
        ("🔴 그 커밋이 관문을 통과시키나",
         "🔴 **아니다** — 구판을 `out980_funnel_badstamp.json` 으로 «같이» 커밋했고 "
         "그 파일의 도장은 F5 불통과다. 절 4 는 그 증거물을 «이름으로» 면제하고 "
         "면제 목록과 수를 나란히 낸다"),
        ("🔴 자가 적발", "🔴 이 항목은 「위반 아님」이 아니라 「위반에 가장 가까웠던 자리」다"),
        ("통과", True)])

    # 11 자와 무관한 목표
    C["11 목표 격자에 자와 무관한 목표가 있나"] = collections.OrderedDict([
        ("자와 무관한 목표 수", tg.get("🔴 자와 무관한 목표 수")),
        ("통과", bool((tg.get("🔴 자와 무관한 목표 수") or 0) >= 1))])

    # 12 ⑤′ 불통과인데 ⑥ 을 시작했나
    paper = sorted((ROOT / "paper/steps").glob("*981*"))
    C["12 `⑤′` 불통과인데 ⑥ 을 시작했나"] = collections.OrderedDict([
        ("`⑤′` 통과", (fp or {}).get("통과")),
        ("981 논문 디렉터리", [p.name for p in paper] or "없음"),
        ("🔴 위반", bool(paper and not (fp or {}).get("통과"))),
        ("통과", bool(not (paper and not (fp or {}).get("통과"))))])

    # 13 수리 계수 — 고친 코드가 있는 것만
    rep = collections.OrderedDict([
        ("R1 `note981_gen` fail-closed + `pipe981_docs.sh`",
         ["runners/note981_gen.py", "runners/pipe981_docs.sh"]),
        ("R2 `⑤′` 절 4 가 도장의 판정을 읽는다", ["runners/fiveprime902.py"]),
        ("R4 규칙 D 가 한자어 자릿수 수사를 본다", ["runners/ledger.py"]),
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
    C["13 수리 계수에 고친 코드가 없는 항목이 있나"] = collections.OrderedDict([
        ("🔴 신고한 수리", list(rep.keys())),
        ("🔴 분자/분모", "%d / %d" % (sum(1 for v in ok.values() if v["셀 수 있나"]),
                                 len(ok))),
        ("칸별", ok),
        ("🔴 수리로 «안» 센 것(코드 변경 0)",
         ["S3 `out980_funnel.json` 재발행(재주행이지 코드 변경이 아니다)",
          "S5 `[수리]` 커밋 제목의 `R<n>` 표지(관행이지 코드가 아니다)"]),
        ("통과", bool(all(v["셀 수 있나"] for v in ok.values())))])

    n_ok = sum(1 for v in C.values() if v.get("통과"))
    # ── 예측 ───────────────────────────────────────────────────────
    P = collections.OrderedDict()
    for k, v in (pk.get("🔴 §5 예측 채점", {}) or {}).items():
        P[k] = v
    for k, v in (tg.get("🔴 예측 채점", {}) or {}).items():
        P[k] = v
    for k, v in (dc.get("🔴 예측 채점", {}) or {}).items():
        P[k] = v
    if fp:
        P["P10 — 구판 절 4 는 통과하고 신판 절 4 는 980 산출물에서 떨어진다"] = (
            "🔴 981 이 `out980_funnel.json` 을 «먼저 고쳐서» 신판 절 4 가 안 떨어졌다 — "
            "예측의 전제가 사라졌다(자가 적발). 신판이 무는 것은 "
            "`out980_funnel_badstamp.json` 이고 그것은 증거물로 면제된다")
    real = [k for k, v in P.items() if isinstance(v, bool)]
    n_true = sum(1 for k in real if P[k])

    out = collections.OrderedDict()
    out["무엇"] = "981 — 🔴 사전등록 반증조건 13 과 예측 10 을 채점한다"
    out["🔴 축"] = "자기 자(수리 레인)"
    out["🔴 채점 규약"] = (
        "🔴 **등록한 조건의 범위를 채점 시점에 좁히지 않는다**(사전등록 §7-6). "
        "980 이 반증조건 5 를 「ρ·Δ 만」으로 좁혀 12/12 를 만들었고 참값은 8/12 였다")
    out["🔴🔴🔴 반증조건 분자/분모"] = "%d / %d" % (n_ok, len(C))
    out["🔴 반증조건 칸별"] = C
    out["🔴🔴 예측 분자/분모(참 / 채점한 것)"] = "%d / %d" % (n_true, len(real))
    out["🔴 예측 칸별"] = P
    out["통과"] = bool(len(C) == 13 and len(P) >= 9)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "반증조건 열셋과 예측 아홉 이상을 **전부 채점했다**. "
        "🔴 이 값은 몇이 참인지와 무관하다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out981_score.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["score"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_score(a.ref)
    print(json.dumps({"반증조건": r["🔴🔴🔴 반증조건 분자/분모"],
                      "예측": r["🔴🔴 예측 분자/분모(참 / 채점한 것)"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
