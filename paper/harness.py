"""논문 하네스 — 한 스텝 개선될 때마다 LaTeX 논문을 짜고 Slack DM으로 보낸다.

목표(2026-07-28 지시): IP 파운데이션 월드모델. 문제를 재설계·수정하고, 계획과
백프레셔를 세우고, 데이터를 인터넷에서 직접 수집하고, NN 아키텍처를 선행 연구와
프론티어 프로덕트를 참고해 만든다. 한 스텝마다 논문으로 남긴다.

**왜 논문 형식인가.** 이 프로젝트에서 반복해서 무너진 것은 코드가 아니라 주장이었다.
gbdt가 상수 예측기였던 것, 타깃 분모가 오염됐던 것, 공간 링크의 36%가 다른 팝업을
가리켰던 것 — 전부 "측정했다"고 믿은 뒤에 드러났다. 논문 형식은 **주장마다 근거와
반증 조건을 붙이도록 강제**한다. figure는 장식이 아니라 주장의 검증 가능한 형태다.

구성:
  paper/steps/NN_slug/         스텝별 디렉토리
    main.tex                   본문
    figs/*.pdf                 matplotlib 산출
    meta.json                  제목·요약·핵심 수치
  paper/build/                 컴파일 산출
  paper/ledger.json            스텝 이력 — 무엇을 주장했고 무엇이 뒤집혔는지

사용:
  python3 -m paper.harness new <slug> "<제목>"    # 스텝 생성
  python3 -m paper.harness build <slug>           # 컴파일
  python3 -m paper.harness send <slug>            # Slack DM 전송 (PDF 첨부)
  python3 -m paper.harness ledger                 # 이력
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = ROOT / "steps"
BUILD = ROOT / "build"
LEDGER = ROOT / "ledger.json"
OPENCLAW = Path("/Users/ax/.openclaw/openclaw.json")   # 읽기 전용
DM_USER = "U0AJ82VJS3W"      # Alex Lee — conversations.open으로 DM 채널을 연다

PREAMBLE = r"""\documentclass[10pt,a4paper]{article}
\usepackage[margin=2.2cm]{geometry}
\usepackage{fontspec}
\usepackage{kotex}
\setmainfont{Apple SD Gothic Neo}
\setsansfont{Apple SD Gothic Neo}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{caption}
\usepackage[dvipsnames]{xcolor}
\usepackage[colorlinks=true,linkcolor=MidnightBlue,citecolor=MidnightBlue,
            urlcolor=MidnightBlue]{hyperref}
\usepackage{titlesec}
\titleformat{\section}{\large\bfseries}{\thesection}{0.6em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{0.5em}{}
\captionsetup{font=small,labelfont=bf}
\setlength{\parskip}{0.35em}
\setlength{\parindent}{0pt}

% 주장 상자 — 모든 주장은 반증 조건을 함께 적는다
\usepackage{mdframed}
\newmdenv[linewidth=0.4pt,linecolor=gray!60,backgroundcolor=gray!5,
          innertopmargin=6pt,innerbottommargin=6pt,skipabove=8pt,skipbelow=8pt]{claimbox}
\newcommand{\claim}[2]{\begin{claimbox}\textbf{주장.} #1\par\smallskip
  \textcolor{gray!70}{\textbf{반증 조건.} #2}\end{claimbox}}
"""


def _ledger() -> dict:
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {"steps": []}


def _save(d: dict) -> None:
    LEDGER.write_text(json.dumps(d, ensure_ascii=False, indent=1))


def new(slug: str, title: str) -> Path:
    led = _ledger()
    n = len(led["steps"]) + 1
    d = STEPS / f"{n:02d}_{slug}"
    (d / "figs").mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(json.dumps(
        {"n": n, "slug": slug, "title": title,
         "created": datetime.now().isoformat(timespec="seconds"),
         "claims": [], "figures": [], "sent": False}, ensure_ascii=False, indent=1))
    led["steps"].append({"n": n, "slug": slug, "title": title,
                         "created": datetime.now().isoformat(timespec="seconds")})
    _save(led)
    print(json.dumps({"스텝": n, "디렉토리": str(d)}, ensure_ascii=False))
    return d


def _dir(slug: str) -> Path:
    """🔴 슬러그가 겹치면 **고르지 말고 멈춘다**(2026-08-07).

    옛 `sorted(...)[-1]` 은 사전순 마지막을 골랐다 --- `157_onecolumn` 과
    `338_onecolumn` 이 함께 있으면 **번호가 큰 옛 논문**이 잡혔고, 그래서
    **엉뚱한 PDF 가 DM 으로 나갔다**(스텝 157 을 보내려다 338 이 갔다).
    보낸 쪽에서는 반환값이 `{"전송": true}` 라 티가 안 났다.

    이제 `"157_onecolumn"` 처럼 **디렉터리 이름 전체**나 `"157"` 처럼
    **번호**로도 부를 수 있고, 맨 슬러그가 여럿에 걸리면 예외다.
    """
    d = STEPS / slug
    if d.is_dir():
        return d
    if slug.isdigit():                       # 번호로 부르기
        cands = sorted(STEPS.glob(f"{int(slug):02d}_*"))
        if len(cands) == 1:
            return cands[0]
        if cands:
            raise SystemExit(f"번호 {slug} 가 여럿: {[c.name for c in cands]}")
    cands = sorted(STEPS.glob(f"*_{slug}")) or sorted(STEPS.glob(f"{slug}*"))
    if not cands:
        raise SystemExit(f"스텝 없음: {slug}")
    if len(cands) > 1:
        raise SystemExit(
            f"🔴 슬러그 '{slug}' 가 {len(cands)}개에 걸린다: "
            f"{[c.name for c in cands]} --- 디렉터리 이름 전체로 불러라")
    return cands[0]


def build(slug: str) -> Path:
    d = _dir(slug)
    # 번호 충돌 경고(2026-08-08 · 노트 880) — 전수 스캔 실측: 62~213 이 거의 전부 2~3중
    # (두 계열 공존 · 유산 규범)이라 생성-시 차단은 불가능하다. 유일 키는 디렉터리 이름이고
    # 호출-시 모호성은 _dir 가 이미 예외로 막는다(788). 신규 논문은 470+(첫 빈 번호)를 쓴다.
    num = d.name.split("_")[0]
    dups = [c.name for c in STEPS.glob(f"{num}_*") if c.name != d.name]
    if dups:
        print(f"⚠ 번호 {num} 공유: {d.name} 대 {dups} — 신규면 470+ 를 쓰라(노트 880)")
    BUILD.mkdir(exist_ok=True)
    r = subprocess.run(["tectonic", "-X", "compile", str(d / "main.tex"),
                        "--outdir", str(BUILD)], capture_output=True, text=True)
    pdf = BUILD / "main.pdf"
    out = BUILD / f"{d.name}.pdf"
    if r.returncode or not pdf.exists():
        print((r.stderr or r.stdout)[-1800:])
        raise SystemExit("컴파일 실패")
    pdf.rename(out)
    print(json.dumps({"산출": str(out), "크기": f"{out.stat().st_size/1024:.0f}KB"},
                     ensure_ascii=False))
    return out


def _token() -> str:
    """openclaw 설정에서 봇 토큰을 **읽기만** 한다. 폴더는 수정하지 않는다."""
    return json.loads(OPENCLAW.read_text())["channels"]["slack"]["botToken"]


def send(slug: str, note: str = "") -> None:
    import urllib.parse
    import urllib.request

    d = _dir(slug)
    meta = json.loads((d / "meta.json").read_text())
    pdf = BUILD / f"{d.name}.pdf"
    if not pdf.exists():
        pdf = build(slug)
    tok = _token()

    def api(method: str, data: dict, get: bool = False):
        url = f"https://slack.com/api/{method}"
        if get:
            url += "?" + urllib.parse.urlencode(data)
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        else:
            req = urllib.request.Request(
                url, data=json.dumps(data).encode(),
                headers={"Authorization": f"Bearer {tok}",
                         "Content-type": "application/json; charset=utf-8"})
        return json.loads(urllib.request.urlopen(req).read())

    # DM 채널 ID를 연다. files.completeUploadExternal은 사용자 ID가 아니라
    # 채널 ID(D...)를 요구한다.
    conv = api("conversations.open", {"users": DM_USER})
    if not conv.get("ok"):
        raise SystemExit(f"DM 채널 열기 실패: {conv.get('error')}")
    ch = conv["channel"]["id"]

    size = pdf.stat().st_size
    up = api("files.getUploadURLExternal",
             {"filename": pdf.name, "length": size}, get=True)
    if not up.get("ok"):
        raise SystemExit(f"업로드 URL 실패: {up.get('error')}")
    body = pdf.read_bytes()
    req = urllib.request.Request(up["upload_url"], data=body, method="POST")
    urllib.request.urlopen(req).read()

    title = f"[스텝 {meta['n']}] {meta['title']}"
    # **본문에 LaTeX 원문을 넣지 않는다**(2026-08-05). ``note`` 는 슬랙에
    # 그대로 찍히는 코멘트다. 스텝 461~469 가 여기에 ``main.tex`` 를 통째로
    # 넣어 보내서 DM 이 소스코드로 도착했다 --- PDF 는 멀쩡히 올라갔는데
    # 딸린 글이 깨진 것이라 **보낸 쪽에서는 티가 안 났다**.
    if note and (note.lstrip().startswith("\\documentclass")
                 or "\\begin{document}" in note or len(note) > 1200):
        raise SystemExit(
            "send(slug, note): note 는 **슬랙 코멘트**다. LaTeX 원문이나 "
            "1,200자 넘는 글을 넣지 마라. 짧은 요약을 주거나 비워 둔다 "
            "(비우면 meta['summary'] → 제목 순으로 쓴다).")
    msg = note or meta.get("summary") or title
    fin = api("files.completeUploadExternal",
              {"files": [{"id": up["file_id"], "title": title}],
               "channel_id": ch, "initial_comment": msg})
    if not fin.get("ok"):
        raise SystemExit(f"업로드 완료 실패: {fin.get('error')}")
    meta["sent"] = True
    meta["sent_at"] = datetime.now().isoformat(timespec="seconds")
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps({"전송": True, "스텝": meta["n"], "제목": meta["title"]},
                     ensure_ascii=False))


def ledger() -> None:
    led = _ledger()
    print(f"논문 스텝 {len(led['steps'])}개")
    for s in led["steps"]:
        d = STEPS / f"{s['n']:02d}_{s['slug']}"
        m = json.loads((d / "meta.json").read_text()) if (d / "meta.json").exists() else {}
        mark = "📤" if m.get("sent") else "  "
        print(f"  {mark} {s['n']:02d}. {s['title']}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ledger"
    if cmd == "new":
        new(sys.argv[2], sys.argv[3])
    elif cmd == "build":
        build(sys.argv[2])
    elif cmd == "send":
        send(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    else:
        ledger()
