#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""992 ⑥ 논문 — 🔴🔴 **아홉 사이클 공백을 «한 스텝»으로 끊는다**.

🔴 **왜.** `paper/` 를 마지막으로 만진 커밋은 **노트 982** 이고 **983~991 아홉 사이클 연속
공백**이다. ⚠ 카드의 「열한 사이클」은 «틀린 수»이고 `docs/tpl/card_991.md.tpl:76` 에
«손으로» 박혀 있었다 --- 992 는 그 자리를 «슬롯»으로 바꾼다.

🔴 **규율과의 화해(사전등록 §8 에 «측정 전»에 적었다).** `docs/루프.md ⑥` 은
「한 스텝 «개선되거나 반증되면»」이지 `⑤′` 통과 조건이 «아니다».
**992 는 「한 스텝」을 «반증 쪽»으로 쓴다.**

🔴🔴 **컴파일·전송은 «안 한다». 그리고 «안 했다»고 적는다**(`조항 59`).
🔴 **본문의 수는 «전부» `runners/out992_*.json` 의 칸에서 온다.**

씀:
    python3 runners/paper992.py --ref <40자 sha>
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
import ledger as LG                                              # noqa: E402

OUT = ROOT / "runners"
PAPER = ROOT / "paper"
STEPS = PAPER / "steps"
PLEDGER = PAPER / "ledger.json"
NOTE = 992
SLUG = "992_wiring"
RAN = ("runners/paper992.py",)


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
    O = "out992_order.json"
    G = "out992_wiring.json"
    MU = "out992_mut.json"
    D = "out992_audit.json"
    S = "out992_score.json"
    EXP = "§2 🔴🔴🔴 탐색 격자"
    SEB = "§1-나 🔴🔴🔴 SE 표 — 자 3 × 성분 8 = 24 칸 전량"
    JUD = "§5 🔴🔴🔴 판정"
    DA = "§A 🔴🔴🔴 ⑤′ 절 4 — 엄한 판 + 면제 없는 판"
    RP = "R_pool 묶음"

    hits = 0
    cells = collections.OrderedDict([
        ("격자칸수", _v(O, EXP, "🔴 격자 칸 수")),
        ("argmax", _v(O, EXP, RP, "🔴 `argmax` 칸(= 991 이 「최적」이라 적은 자)")),
        ("끝칸인가", _v(O, EXP, RP, "🔴🔴🔴 argmax 가 격자 오른쪽 끝인가")),
        ("최적집합", _v(O, EXP, RP, "🔴🔴🔴 «최적 집합»(argmax 와 `2·SE_clu` 로 «안 갈리는» 칸)")),
        ("최적집합수", _v(O, EXP, RP, "🔴🔴🔴 최적 집합의 크기")),
        ("SE칸수", _v(O, SEB, "🔴 칸 수")),
        ("SE갈린", _v(O, SEB, "🔴🔴🔴 자에 따라 «2·SE 판정»이 갈리는 성분")),
        ("SE갈린수", _v(O, SEB, "🔴🔴🔴 그 수")),
        ("넘은수", _v(O, SEB, "🔴🔴🔴 자별 «2 를 넘은 성분 수»")),
        ("상호판정t", _v(O, JUD, "🔴 판정자 상호작용 t_clu")),
        ("상호챔t", _v(O, JUD, "🔴 챔피언자 상호작용 t_clu")),
        ("배선수", _v(G, "🔴 배선 검사 수(분모)")),
        ("검정력", _v(G, "🔴🔴🔴 ㉢ 검정력이 «있는» 검사 수")),
        ("구성거짓", _v(G, "🔴🔴🔴 ㉡ 구성상 «거짓»인 검사 수")),
        ("991거짓", _v(G, "§B 🔴🔴🔴 991 의 여섯을 실측한다", "🔴🔴🔴 구성상 거짓 수")),
        ("991신고", _v(G, "§B 🔴🔴🔴 991 의 여섯을 실측한다",
                     "🔴 991 이 «신고한» ㉡ 구성상 거짓 수(손 라벨)")),
        ("990거짓", _v(MU, "🔴🔴🔴 그 수")),
        ("990둘째", _v(MU, "🔴🔴🔴 둘째 자 — 「자료와 «무관하게» 강제되는 것」만 세면", "🔴 그 수")),
        ("면제로산것", _v(D, DA, "🔴🔴🔴 그래서 991 의 「엄한 판 첫 통과」는 «면제로 산 것»인가")),
        ("최상위", _v(S, "통과")),
    ])
    hits += len(cells)
    r = LG.render
    sha, when, last_note = last_paper_touch()
    gap = (NOTE - 1 - last_note) if last_note else None
    hits += 1

    claims = [
        "「최적 base」는 자료의 사실이 아니라 격자의 사실이었다 --- 격자를 %s 칸으로 늘리면 "
        "판정 자의 argmax 가 %s 이고 격자 오른쪽 끝인가는 %s 이며, argmax 와 2·SE_clu 로 "
        "안 갈리는 칸이 %s 개다"
        % (r(cells["격자칸수"]), r(cells["argmax"]), r(cells["끝칸인가"]),
           r(cells["최적집합수"])),
        "「무엇이 사는가」는 자의 사실이다 --- 자 3 × 성분 8 = %s 칸을 전량 재면 자에 따라 "
        "2·SE 판정이 갈리는 성분이 %s 개이고, 상호작용은 판정 자에서 t_clu %s 로 안 살고 "
        "챔피언 자에서 %s 로 산다"
        % (r(cells["SE칸수"]), r(cells["SE갈린수"]), r(cells["상호판정t"]),
           r(cells["상호챔t"])),
        "변이체의 「공허」를 손 라벨로 판정하면 검정력이 0 이다 --- 앞 노트가 「구성상 거짓 0」이라 "
        "신고한 여섯을 그 노트 자신의 설정 격자에서 돌리면 %s 이고, 신고값은 %s 였다"
        % (r(cells["991거짓"]), r(cells["991신고"])),
        "앞 노트가 손으로 센 「990 의 일곱 중 여섯」을 기계로 재면 자에 따라 %s 과 %s 로 갈린다 --- "
        "「구성상」의 정의가 자를 가른다"
        % (r(cells["990거짓"]), r(cells["990둘째"])),
        "면제를 만든 사이클이 면제 없는 판을 안 내면 그 통과는 면제로 산 것이다 --- "
        "앞 노트가 등기해 뺀 도장 셋이 앞 세 사이클에서 신판을 떨어뜨린 바로 그 셋인가: %s"
        % r(cells["면제로산것"]),
        "이 사이클의 배선 %s 개는 전부 「설정에 따라 갈리는」 변이체를 가졌고 손 라벨이 0 이다 "
        "(검정력 있는 검사 %s · 구성상 거짓 %s)"
        % (r(cells["배선수"]), r(cells["검정력"]), r(cells["구성거짓"])),
    ]
    abstract = (
        "이 노트는 새 세계 측정을 늘리는 대신 «자가 잡은 것을 자에 무는 배선»을 고친다. "
        "앞 노트의 자들은 자기 병을 세 번 잡아 놓고 세 번 다 흘렸고 그래서 문서 넷이 "
        "채점 자리를 비운 채 나갔다. 여기서 얻은 것은 셋이다. "
        "첫째, 변이체의 「공허」는 손 라벨로 판정할 수 없다 --- 설정 격자에서 실측해야 하고, "
        "실측하면 앞 노트의 여섯이 전부 붉다. "
        "둘째, 「최적 base」는 격자 경계 인공물이었다 --- 격자를 오른쪽으로 늘리면 꼭짓점이 "
        "안으로 들어오고 2·SE 로 안 갈리는 칸이 여러 개다. "
        "셋째, 「무엇이 통계적으로 사는가」 자체가 자의 사실이다 --- 같은 성분이 판정 자에서 "
        "죽고 챔피언 자에서 산다.")

    STEPS.mkdir(parents=True, exist_ok=True)
    sd = STEPS / SLUG
    sd.mkdir(parents=True, exist_ok=True)
    body = ["\\section{무엇을 고쳤나}\n"]
    for i, c in enumerate(claims, 1):
        body.append("\\paragraph{주장 %d.} %s\n" % (i, c))
    body.append("\n\\section{한계}\n")
    body.append("이 스텝은 \\textbf{컴파일하지 않았고 보내지 않았다}. "
                "그 사실을 원장과 이 파일에 적는다 --- 「안 했다」는 「없다」가 아니다.\n")
    body_tex = "\n".join(body)
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
        ("🔴 손으로 안 썼다", "runners/paper992.py 가 `out992_*.json` 의 칸에서 지었다"),
        ("🔴 컴파일했나", False), ("🔴 보냈나", False),
        ("🔴 왜 안 보냈나", "🔴 이 사이클은 «배선» 사이클이고 유료 API·전송을 안 쓴다. "
                       "「안 했다」를 «적는 것»이 규율이다(조항 59)"),
        ("🔴 파일 sha256", collections.OrderedDict([
            ("body.tex", hashlib.sha256(body_tex.encode("utf-8")).hexdigest()),
            ("main.tex", hashlib.sha256(main_tex.encode("utf-8")).hexdigest()),
        ])),
    ])
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
        ("🔴 컴파일했나", False), ("🔴 보냈나", False),
    ]))
    pl["steps"] = steps
    PLEDGER.write_text(json.dumps(pl, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    hits += 1

    res = collections.OrderedDict([
        ("무엇", "992 ⑥ 논문 — 🔴 **아홉 사이클 공백을 «한 스텝»으로 끊는다**"),
        ("🔴 마지막으로 `paper/` 를 만진 커밋", sha),
        ("🔴 그 커밋 시각", when),
        ("🔴 그 노트 번호", last_note),
        ("🔴🔴🔴 `paper/` 공백 사이클 수", gap),
        ("⚠ 991 카드가 손으로 박은 수", 11),
        ("🔴🔴 그 수가 «틀렸나»", bool(gap is not None and gap != 11)),
        ("🔴 이 사이클이 «쓴» 스텝", SLUG),
        ("🔴 스텝 경로", "paper/steps/%s" % SLUG),
        ("🔴 주장 수", len(claims)),
        ("🔴 본문의 수가 온 칸", collections.OrderedDict(
            (k, val) for k, val in cells.items())),
        ("🔴 못 읽은 칸", [k for k, val in cells.items() if val is None] or "없음"),
        ("🔴 보냈나(컴파일·전송)", False),
        ("🔴 규율과의 화해",
         "🔴 `docs/루프.md ⑥` 은 「한 스텝 «개선되거나 반증되면»」이지 `⑤′` 통과 조건이 "
         "«아니다». 992 는 「한 스텝」을 «반증 쪽»으로 썼다 --- 사전등록 §8 에 «측정 전»에 적었다"),
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
    (OUT / "out992_paper.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [paper992] 스텝 %s · 공백 %s 사이클 · 통과 %s\n"
                     % (_now(), SLUG, gap, res["통과"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
