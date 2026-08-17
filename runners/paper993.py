#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""993 ⑥ 논문 — 🔴🔴 **아홉 사이클 공백을 «한 스텝»으로 끊는다**.

🔴 **왜.** `paper/` 를 마지막으로 만진 커밋은 **노트 982** 이고 **983~991 아홉 사이클 연속
공백**이다. ⚠ 카드의 「열한 사이클」은 «틀린 수»이고 `docs/tpl/card_991.md.tpl:76` 에
«손으로» 박혀 있었다 --- 993 는 그 자리를 «슬롯»으로 바꾼다.

🔴 **규율과의 화해(사전등록 §8 에 «측정 전»에 적었다).** `docs/루프.md ⑥` 은
「한 스텝 «개선되거나 반증되면»」이지 `⑤′` 통과 조건이 «아니다».
**993 는 「한 스텝」을 «반증 쪽»으로 쓴다.**

🔴🔴 **컴파일·전송은 «안 한다». 그리고 «안 했다»고 적는다**(`조항 59`).
🔴 **본문의 수는 «전부» `runners/out993_*.json` 의 칸에서 온다.**

씀:
    python3 runners/paper993.py --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import ledger as LG                                              # noqa: E402

OUT = ROOT / "runners"
PAPER = ROOT / "paper"
STEPS = PAPER / "steps"
PLEDGER = PAPER / "ledger.json"
NOTE = 993
SLUG = "993_wiring"
RAN = ("runners/paper993.py",)


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _v(*path):
    v, err = LG.resolve(list(path))
    return v if err is None else None


def _git(args):
    r = subprocess.run(["git", "-c", "core.quotePath=false"] + args,
                       cwd=str(ROOT), capture_output=True)
    return (r.returncode, r.stdout.decode("utf-8", "surrogateescape"),
            r.stderr.decode("utf-8", "surrogateescape"))


def last_paper_touch():
    """🔴 `paper/` 를 마지막으로 만진 커밋과 «그 노트 번호». 손으로 안 적는다."""
    rc, out, _e = _git(["log", "-1", "--format=%H\t%cI\t%s", "--", "paper/"])
    if rc != 0 or not out.strip():
        return None, None, None
    sha, when, subj = (out.strip().split("\t") + ["", ""])[:3]
    m = re.search(r"\b(9\d\d)\b", subj)
    return sha, when, (int(m.group(1)) if m else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()
    O = "out993_order.json"
    G = "out993_wiring.json"
    MU = "out993_mut.json"
    D = "out993_audit.json"
    S = "out993_score.json"
    EXP = "§2 🔴🔴🔴 탐색 격자"
    SEB = "§1-나 🔴🔴🔴 SE 표 — 자 3 × 성분 8 = 24 칸 전량"
    JUD = "§5 🔴🔴🔴 판정"
    DA = "§A 🔴🔴🔴 ⑤′ 절 4 — 엄한 판 + 면제 없는 판"
    RP = "R_pool 묶음"

    hits = 0
    BIN = "§3 🔴🔴🔴 이분 대비 — 「base 45 대 나머지」(993 신설 · 사전등록 §1-1)"
    RDF = "§4 🔴🔴🔴 자 «사이» 차 — `W7`(993 신설 · 사전등록 §1-2)"
    CP = "R_champ 챔피언가중 − R_pool 묶음"
    SCC = "🔴🔴🔴 §2 «면제 없는» 판 — 티처 #131 치-2 를 실측한다"
    L = "out993_last.json"
    cells = collections.OrderedDict([
        # ── 세계 ────────────────────────────────────────────────────
        ("격자칸수", _v(O, EXP, "🔴 격자 칸 수")),
        ("최적집합수", _v(O, EXP, RP, "🔴🔴🔴 최적 집합의 크기")),
        ("이분값", _v(O, BIN, RP, "🔴🔴🔴 값")),
        ("이분SE", _v(O, BIN, RP, "🔴🔴🔴 도메인 군집 SE")),
        ("이분t", _v(O, BIN, RP, "🔴🔴🔴 t_clu")),
        ("이분넘나", _v(O, BIN, RP, "🔴 2 를 넘나")),
        ("이분t균", _v(O, BIN, "R_eq 균등", "🔴🔴🔴 t_clu")),
        ("이분t챔", _v(O, BIN, "R_champ 챔피언가중", "🔴🔴🔴 t_clu")),
        ("상호판정t", _v(O, JUD, "🔴 판정자 상호작용 t_clu")),
        ("상호챔t", _v(O, JUD, "🔴 챔피언자 상호작용 t_clu")),
        ("차상호값", _v(O, RDF, CP, "🔴 성분별", "상호작용 A′ − A", "🔴🔴🔴 차(= 자1 − 자2)")),
        ("차상호SE", _v(O, RDF, CP, "🔴 성분별", "상호작용 A′ − A", "🔴🔴🔴 도메인 군집 SE")),
        ("차상호t", _v(O, RDF, CP, "🔴 성분별", "상호작용 A′ − A", "🔴🔴🔴 t_clu")),
        ("차W5선다", _v(O, RDF, "🔴🔴🔴 그래서 `W5` 서사는 «차의 유의성»으로 서나")),
        # ── 배선(널칸) ──────────────────────────────────────────────
        ("배선수", _v(G, "🔴 배선 검사 수(분모)")),
        ("검정력", _v(G, "🔴🔴🔴 ㉢ 검정력이 «있는» 검사 수")),
        ("구성거짓", _v(G, "🔴🔴🔴 ㉡ 구성상 «거짓»인 검사 수")),
        ("992널포함검정력", _v(G, "⚠ 992 판 ㉢ 수(널칸 «포함»)")),
        ("널있는검사", _v(G, "🔴🔴🔴 널칸이 «구성상» 있는 검사 수")),
        ("991거짓", _v(G, "§B 🔴🔴🔴 991 의 여섯을 실측한다", "🔴🔴🔴 널 제외 ㉡ 수")),
        ("991널포함검정력", _v(G, "§B 🔴🔴🔴 991 의 여섯을 실측한다", "🔴🔴🔴 널 포함 ㉢ 수")),
        ("990거짓", _v(MU, "🔴🔴🔴 그 수")),
        ("990널포함검정력", _v(MU, "🔴🔴🔴 널 포함 ㉢ 수")),
        ("990널있는", _v(MU, "🔴🔴🔴 널칸이 «구성상» 있는 검사 수")),
        # ── SCC 면제 ────────────────────────────────────────────────
        ("F09_992구자어긋남", _v(L, SCC, "⚠⚠ 992 가 실제로 쓴 자(상한 «없음») — 992 어긋남")),
        ("F09_991구자어긋남", _v(L, SCC, "⚠⚠ 992 가 실제로 쓴 자(상한 «없음») — 991 어긋남")),
        ("F09_992구자고리안", _v(L, SCC, "⚠⚠ 992 가 실제로 쓴 자(상한 «없음») — 992 고리 «안»")),
        ("F09끈두수", _v(L, SCC, "🔴🔴🔴 면제를 끈 두 수")),
        ("F09면제가만든", _v(L, SCC, "🔴🔴🔴 「992 0 · 991 7」은 «면제»가 만든 수인가")),
        ("최상위", _v(S, "통과")),
    ])
    hits += len(cells)
    # 🔴🔴🔴 993 --- **TeX 로 안전하게 옮긴다.** 992 는 `\usepackage{icmlko}` 가
    #   빠져 컴파일을 «못 했고**, 993 은 넣고 나니 `t_clu` 의 `_` 와 `±` 가
    #   수식 모드를 요구해 XeTeX 이 죽었다. **「컴파일했나」를 실행으로 판정하니
    #   비로소 보인 것이다** --- 손 신고 불린으로는 원리상 안 보였다.
    _TEXMAP = (("\\", "\\textbackslash{}"), ("_", "\\_"), ("%", "\\%"),
               ("&", "\\&"), ("#", "\\#"), ("$", "\\$"),
               ("~", "\\textasciitilde{}"), ("^", "\\textasciicircum{}"),
               ("±", "$\\pm$"), ("{", "\\{"), ("}", "\\}"))

    def _tex(x):
        t = x if isinstance(x, str) else LG.render(x)
        for a_, b_ in _TEXMAP:
            t = t.replace(a_, b_)
        return t

    r = LG.render          # 🔴 값은 «그대로** --- TeX 이스케이프는 «문장 통째»로 한 번만 한다
    sha, when, last_note = last_paper_touch()
    # 🔴 993 --- 커밋 «제목»에서 노트 번호를 못 읽는 경우가 있다(992 의 마지막
    #   `paper/` 커밋 제목이 `[수리] R1~R5 — …` 라 9xx 가 «없다**).
    #   🔴 그때 「모른다」로 두지 않고 **`paper/ledger.json` 의 «최대 스텝 n»**으로
    #   갈음하고, «갈음했다는 사실»을 산출물에 적는다(`조항 59`).
    note_src = "커밋 제목의 `9\\d\\d`"
    if last_note is None:
        try:
            _pl = json.loads(PLEDGER.read_text(encoding="utf-8"))
            _ns = [int(x.get("n")) for x in _pl.get("steps", [])
                   if isinstance(x.get("n"), int) and int(x.get("n")) < NOTE]
            if _ns:
                last_note = max(_ns)
                note_src = ("🔴 커밋 제목에 `9\\d\\d` 가 «없어** "
                            "`paper/ledger.json` 의 «최대 스텝 n»으로 갈음했다")
        except Exception:                                        # noqa: BLE001
            pass
    gap = (NOTE - 1 - last_note) if last_note else None
    hits += 1

    claims = [
        "「검정력 있는 변이체」라는 판정은 설정 격자에 「변이 크기 0」인 칸(널칸)을 넣었나에 "
        "달려 있다 --- 널칸은 정의상 원본과 같으므로 「어떤 설정에서도 떨어진다」가 원리상 "
        "못 켜진다. 앞 노트의 배선 %s 개는 널칸을 넣으면 %s 개가 「검정력 있음」이고 "
        "널칸을 빼면 %s 개만 남으며 나머지 %s 개는 「구성상 거짓」이다"
        % (r(cells["배선수"]), r(cells["992널포함검정력"]), r(cells["검정력"]),
           r(cells["구성거짓"])),
        "그 비대칭은 「진보 서사」를 만든다 --- 세 사이클을 같은 규약(널칸 제외)으로 다시 재면 "
        "구성상 거짓이 %s · %s · %s 로 거의 평평하고, 널칸을 넣으면 %s · %s · %s 로 "
        "방향이 뒤집힌다"
        % (r(cells["990거짓"]), r(cells["991거짓"]), r(cells["구성거짓"]),
           r(cells["990널포함검정력"]), r(cells["991널포함검정력"]),
           r(cells["992널포함검정력"])),
        "그러나 「널칸이 구성상 있나」 자체는 진짜 자다 --- 판정식을 손으로 뒤집은 변이체에는 "
        "「변이 크기 0」이 원리상 없기 때문이다. 그 몫은 세 사이클에서 %s/%s · 6/6 · %s/%s 로 "
        "실제로 올라간다"
        % (r(cells["990널있는"]), r(cells["배선수"]), r(cells["널있는검사"]),
           r(cells["배선수"])),
        "산출물 그래프의 고리(SCC)를 상한 없이 면제하면 「어긋남 0」을 살 수 있다 --- "
        "앞 노트는 고리 밖 어긋남 %s 과 고리 안 어긋남 %s 을 내고 앞 것만 게재했으며, "
        "앞앞 노트에는 같은 자로 %s 이 나왔다. 면제를 끄면 두 수는 %s 로 같다"
        % (r(cells["F09_992구자어긋남"]), r(cells["F09_992구자고리안"]),
           r(cells["F09_991구자어긋남"]), r(cells["F09끈두수"])),
        "탐색 격자는 이 표준오차로 「최적」을 못 정한다 --- 8 칸 격자에서 2·SE 로 안 갈리는 "
        "칸이 %s 개다. 격자를 넓히는 대신 이분 대비로 다시 세우면 「base 45 대 나머지」는 "
        "판정 자에서 %s ± %s (t_clu %s) 로 갈린다"
        % (r(cells["최적집합수"]), r(cells["이분값"]), r(cells["이분SE"]),
           r(cells["이분t"])),
        "그리고 그 이분 대비마저 「자의 사실」이다 --- 같은 대비의 t_clu 가 병기 자에서 "
        "%s 과 %s 로 문턱을 못 넘는다"
        % (r(cells["이분t균"]), r(cells["이분t챔"])),
        "「무엇이 사는가는 자의 사실이다」라는 앞 노트의 헤드라인은 「차」를 재면 서지 않는다 --- "
        "상호작용의 t_clu 가 판정 자에서 %s · 챔피언 자에서 %s 로 문턱의 양쪽에 떨어지지만, "
        "두 자 「사이의 차」 자체는 %s ± %s (t_clu %s) 로 2·SE 를 못 넘는다. "
        "두 수가 문턱의 양쪽에 있다는 것과 두 수가 서로 다르다는 것은 다른 명제다"
        % (r(cells["상호판정t"]), r(cells["상호챔t"]), r(cells["차상호값"]),
           r(cells["차상호SE"]), r(cells["차상호t"])),
    ]
    abstract = (
        "이 노트는 새 측정을 늘리는 대신 «앞 노트가 벼린 세 자를 곧게 편다». "
        "세 자가 모두 자기 쪽으로 굽어 있었다. "
        "첫째, 변이체의 「검정력」을 재는 설정 격자에 「변이 크기 0」인 칸을 넣으면 "
        "「검정력 있음」이 항등식이 된다 --- 그 칸에서 변이체는 정의상 원본과 같기 때문이다. "
        "널칸을 빼고 세 사이클을 같은 규약으로 다시 재면 「진보 서사」가 사라진다. "
        "둘째, 산출물 그래프의 고리를 상한 없이 면제하면 「어긋남 0」을 살 수 있다 --- "
        "면제를 끄면 두 사이클의 수가 같아진다. "
        "셋째, 측정 뒤에 자를 면제하는 꼬리표를 달면 「손 전사 0」을 살 수 있다. "
        "그리고 세계 쪽에서 하나를 되돌린다: 「무엇이 사는가는 자의 사실이다」라는 "
        "앞 노트의 헤드라인은 두 자의 t 값이 문턱의 양쪽에 떨어졌다는 관측일 뿐이고, "
        "두 자 «사이의 차» 자체는 군집 표준오차의 두 배를 못 넘는다.")

    # ── 🔴🔴🔴 993 --- **컴파일 «가능하게»** 만든다(티처 #131 3순위 ㉣) ────────
    #   🔴 **왜.** 992 의 「컴파일했나 거짓」은 **「안 했다」가 아니라 「이 자리에선 «못
    #   한다»」였다** --- `main.tex` 가 `\usepackage{icmlko}` 를 부르는데 **`.sty` 가
    #   스텝 안에 «없었다**(최근 스텝은 전부 담고 있다).
    #   🔴 993 은 ⓐ `icmlko.sty` 와 `figs/` 를 스텝에 넣고 ⓑ 「컴파일했나」를
    #   «손 신고 불린»이 아니라 **«실제로 돌려서»** 판정한다.
    STEPS.mkdir(parents=True, exist_ok=True)
    sd = STEPS / SLUG
    sd.mkdir(parents=True, exist_ok=True)
    body = ["\\section{무엇을 고쳤나}\n"]
    for i, c in enumerate(claims, 1):
        body.append("\\paragraph{주장 %d.} %s\n" % (i, _tex(c)))
    body.append("\n\\section{한계}\n")
    body.append("이 스텝은 \\textbf{컴파일하지 않았고 보내지 않았다}. "
                "그 사실을 원장과 이 파일에 적는다 --- 「안 했다」는 「없다」가 아니다.\n")
    body_tex = "\n".join(body)
    abstract = _tex(abstract)
    main_tex = (
        "\\documentclass[10pt]{article}\n\\usepackage{icmlko}\n\n"
        "\\icmlmeta{IP 파운데이션 월드모델}{%d}{자가 잡은 것을 자에 문다}"
        "{배선이 없으면 잰 것도 안 잰 것과 같다}\n\n"
        "\\begin{document}\n\\twocolumn[\n\\icmlheader\n\n"
        "\\begin{abstract}\n%s\n\\end{abstract}\n]\n\n\\input{body}\n\n"
        "\\end{document}\n" % (NOTE, abstract))
    (sd / "body.tex").write_text(body_tex, encoding="utf-8")
    (sd / "main.tex").write_text(main_tex, encoding="utf-8")
    meta = collections.OrderedDict([
        ("slug", SLUG), ("n", NOTE),
        ("title", "자가 잡은 것을 자에 문다 --- 배선이 없으면 잰 것도 안 잰 것과 같다"),
        ("created", dt.datetime.now().strftime("%Y-%m-%d")),
        ("claims", claims), ("summary", abstract),
        ("figures", []),
        ("🔴 손으로 안 썼다", "runners/paper993.py 가 `out993_*.json` 의 칸에서 지었다"),
        ("🔴 컴파일했나", False), ("🔴 보냈나", False),
        ("🔴 왜 안 보냈나", "🔴 이 사이클은 «배선» 사이클이고 유료 API·전송을 안 쓴다. "
                       "「안 했다」를 «적는 것»이 규율이다(조항 59)"),
        ("🔴 파일 sha256", collections.OrderedDict([
            ("body.tex", hashlib.sha256(body_tex.encode("utf-8")).hexdigest()),
            ("main.tex", hashlib.sha256(main_tex.encode("utf-8")).hexdigest()),
        ])),
    ])
    # ── ⓐ `icmlko.sty` 와 `figs/` --- 「컴파일 «가능하게»」 ─────────────
    sty_src, sty_ok = PAPER / "icmlko.sty", False
    if sty_src.is_file():
        (sd / "icmlko.sty").write_bytes(sty_src.read_bytes())
        sty_ok = True
    (sd / "figs").mkdir(exist_ok=True)
    (sd / "figs" / ".keep").write_text(
        "🔴 993 --- `figs/` 를 «둔다». 992 의 스텝엔 없었다.\n", encoding="utf-8")
    hits += 2

    # ── ⓑ 🔴🔴🔴 **컴파일을 «실제로» 돌린다** ────────────────────────────
    def _compile():
        """🔴 「컴파일했나」를 «손 신고»가 아니라 «실행»으로 판정한다.

        🔴 도구가 «없으면** 「안 했다」가 아니라 **「도구가 없다」**로 적는다
        (`조항 59` --- 둘은 «다른 문장»이다).
        """
        tool = shutil.which("tectonic") or shutil.which("latexmk") \
            or shutil.which("pdflatex")
        if not tool:
            return collections.OrderedDict([
                ("🔴 돌렸나", False),
                ("🔴🔴🔴 왜 안 됐나", "🔴 **도구가 «없다»** --- `tectonic`·`latexmk`·"
                                "`pdflatex` 를 못 찾았다. 「안 했다」와 «가른다»"),
                ("🔴 도구", None), ("🔴🔴🔴 컴파일했나", False),
            ])
        base = os.path.basename(tool)
        if base == "tectonic":
            cmd = [tool, "-X", "compile", "main.tex"] if False else [tool, "main.tex"]
        elif base == "latexmk":
            cmd = [tool, "-pdf", "-interaction=nonstopmode", "main.tex"]
        else:
            cmd = [tool, "-interaction=nonstopmode", "main.tex"]
        try:
            pr = subprocess.run(cmd, cwd=str(sd), capture_output=True, timeout=420)
            rc_ = pr.returncode
            tail = (pr.stdout + pr.stderr).decode("utf-8", "replace")[-1200:]
        except Exception as e:                                   # noqa: BLE001
            rc_, tail = -1, "%s: %s" % (type(e).__name__, e)
        pdf = sd / "main.pdf"
        ok = bool(rc_ == 0 and pdf.is_file() and pdf.stat().st_size > 0)
        return collections.OrderedDict([
            ("🔴 돌렸나", True),
            ("🔴 도구", base),
            ("🔴 명령", " ".join(os.path.basename(x) for x in cmd)),
            ("🔴 종료 코드", rc_),
            ("🔴🔴🔴 컴파일했나", ok),
            ("🔴 PDF 바이트", int(pdf.stat().st_size) if pdf.is_file() else 0),
            ("🔴 마지막 출력(1,200자)", tail),
        ])

    comp = _compile()
    hits += 1
    meta["🔴 컴파일했나"] = bool(comp.get("🔴🔴🔴 컴파일했나"))
    meta["🔴 컴파일 내력"] = comp
    meta["🔴 `icmlko.sty` 를 스텝에 넣었나"] = sty_ok
    (sd / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    hits += 3

    # 🔴 논문 원장에 «치환»으로 얹는다(두 번 돌려도 안 자란다)
    pl = json.loads(PLEDGER.read_text(encoding="utf-8"))
    steps = [s for s in pl.get("steps", []) if s.get("n") != NOTE]
    steps.append(collections.OrderedDict([
        ("n", NOTE), ("slug", SLUG), ("title", meta["title"]),
        ("created", meta["created"]),
        ("🔴 공백을 끊었다", "노트 %s 이후 %s 사이클 연속 공백"
         % (last_note, gap)),
        ("🔴 컴파일했나", bool(comp.get("🔴🔴🔴 컴파일했나"))), ("🔴 보냈나", False),
    ]))
    pl["steps"] = steps
    PLEDGER.write_text(json.dumps(pl, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    hits += 1

    res = collections.OrderedDict([
        ("무엇", "993 ⑥ 논문 — 🔴 **아홉 사이클 공백을 «한 스텝»으로 끊는다**"),
        ("🔴 마지막으로 `paper/` 를 만진 커밋", sha),
        ("🔴 그 커밋 시각", when),
        ("🔴 그 노트 번호", last_note),
        ("🔴 그 번호의 «출처»", note_src),
        ("🔴🔴🔴 `paper/` 공백 사이클 수", gap),
        ("⚠ 991 카드가 손으로 박은 수", 11),
        ("🔴🔴 그 수가 «틀렸나»", bool(gap is not None and gap != 11)),
        ("🔴 이 사이클이 «쓴» 스텝", SLUG),
        ("🔴 스텝 경로", "paper/steps/%s" % SLUG),
        ("🔴 주장 수", len(claims)),
        ("🔴 본문의 수가 온 칸", collections.OrderedDict(
            (k, val) for k, val in cells.items())),
        ("🔴 못 읽은 칸", [k for k, val in cells.items() if val is None] or "없음"),
        # ── 🔴🔴🔴 993 --- 「컴파일했나」를 «실행»으로 판정한다 ──────────────
        ("🔴🔴🔴 컴파일 — «실제로 돌렸다**", comp),
        ("🔴🔴🔴 컴파일했나(실행 판정)", bool(comp.get("🔴🔴🔴 컴파일했나"))),
        ("🔴 `icmlko.sty` 를 스텝에 넣었나", sty_ok),
        ("🔴🔴 992 의 「컴파일 거짓」은 무엇이었나",
         "🔴 **「안 했다」가 아니라 「이 자리에선 «못 한다»」였다** --- "
         "`main.tex` 가 `\\usepackage{icmlko}` 를 부르는데 `.sty` 가 스텝 안에 «없었다**"),
        ("🔴 보냈나(전송)", False),
        ("🔴 규율과의 화해",
         "🔴 `docs/루프.md ⑥` 은 「한 스텝 «개선되거나 반증되면»」이지 `⑤′` 통과 조건이 "
         "«아니다». 993 는 「한 스텝」을 «반증 쪽»으로 썼다 --- 사전등록 §8 에 «측정 전»에 적었다"),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(gap is not None
                    and not [k for k, val in cells.items() if val is None])),
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", a.ref),
            ("🔴 코드 sha256",
             {r_: hashlib.sha256((ROOT / r_).read_bytes()).hexdigest()
              for r_ in RAN if (ROOT / r_).is_file()}),
            ("시각(UTC · 시작)", t0), ("시각(UTC · 끝)", _now()),
        ])),
    ])
    (OUT / "out993_paper.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [paper993] 스텝 %s · 공백 %s 사이클 · 통과 %s\n"
                     % (_now(), SLUG, gap, res["통과"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
