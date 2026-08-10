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


#: `paper_dead()` 반환에서 우리가 **이름으로 붙잡는** 칸. 이름이 바뀌면 조용히
#: 빈 목록을 읽고 통과시키게 되므로 --- 그게 정확히 이 게이트가 없던 이유다 ---
#: 없으면 **계약 파기로 멈춘다**. 내가 배선한 시점(2026-08-10)의 시그니처는
#: `paper_dead(baseline_at: str = PAPER_BASELINE_AT, debt: int = PAPER_DEBT) -> dict`.
_GATE_FRESH = "🔴 기준선 뒤 논문(경성 실패)"


def _dead_gate(d: Path, phase: str) -> None:
    """죽은 숫자 게이트 --- `ingest.audit.paper_dead()` 를 **실제로 부른다**(노트 898).

    🔴 **왜 생겼나(티처 #60 C6 · 이슈 119).** `docs/루프.md` 는 *"죽은 숫자를 표지
    없이 인용하면 `paper_dead()` 가 막는다"* 라고 적어 놓았는데 **이 파일은 그 함수를
    한 번도 안 불렀다**(전수 grep: 호출자는 `ingest/audit.py` 두 곳뿐이었다). 논문
    483 이 경성 실패인 채로 build 되고 send 되고 **재전송까지** 됐다. 배선 없이
    "막는다"고 적힌 자리다.

    **막는 방식**(넷 다 일부러 다르다):

      · **이 스텝이 경성 실패면 멈춘다**(`SystemExit`). 컴파일도 전송도 안 한다.
      · **다른 논문의 경성 실패는 경고만** 한다. 남의 논문 때문에 내 빌드가 막히면
        게이트가 제일 먼저 꺼진다 --- 그리고 발행물은 개작하지 않는 것이 규칙이다.
      · **묵은 빚 래칫이 올랐으면 경고만** 한다. 그건 이 빌드가 만든 일이 아니라
        `DEAD_NUMBERS` 표가 자란 결과이고, 고칠 자리는 `ingest/audit.py` 다.
      · **게이트가 못 돌면 통과가 아니라 멈춤이다**(조항 59 --- '없다'와 '못 봤다'는
        다르다). 반입 실패 · 예외 · **반환 칸 이름이 바뀐 경우** 전부 멈춘다.

    **빠져나가는 길은 하나뿐이고 그것이 이 게이트의 목적이다**: 본문에 정정 표시
    (`죽은 숫자`·`정정`·`철회`·`은퇴` 중 하나 또는 산 값)를 앞뒤 2줄 안에 달거나,
    오탐이면 `meta.json` 의 `errata` 에 **그 숫자를 문자로** 적는다. 환경변수 같은
    조용한 우회로는 **일부러 안 만들었다**.
    """
    repo = ROOT.parent
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    try:
        from ingest.audit import paper_dead
    except Exception as e:                              # 반입 실패 = 못 봤다
        raise SystemExit(
            f"🔴 죽은 숫자 게이트를 반입하지 못했다({type(e).__name__}: {e}) --- "
            "'통과'가 아니라 '모른다'다. ingest/audit.py 를 고친 뒤 다시 하라.")
    try:
        r = paper_dead()
    except Exception as e:                              # 예외 = 못 봤다
        raise SystemExit(
            f"🔴 paper_dead() 가 예외로 죽었다({type(e).__name__}: {e}) --- "
            "게이트가 안 돌았으므로 build/send 를 멈춘다.")
    if not isinstance(r, dict) or _GATE_FRESH not in r or "통과" not in r:
        raise SystemExit(
            f"🔴 게이트 계약이 깨졌다 --- paper_dead() 반환에 '{_GATE_FRESH}' 나 "
            f"'통과' 칸이 없다(받은 칸: {list(r)[:12] if isinstance(r, dict) else type(r)}). "
            "칸 이름이 바뀌었으면 harness._GATE_FRESH 를 같이 고쳐라. 이름이 어긋난 채로 "
            "돌면 빈 목록을 읽고 **조용히 통과**한다 --- 그게 이 게이트가 없던 이유다.")

    fresh = r[_GATE_FRESH]
    fresh = [] if isinstance(fresh, str) else [x for x in fresh if isinstance(x, dict)]
    mine = [x for x in fresh if x.get("논문") == d.name]
    others = len(fresh) - len(mine)
    if others:
        print(f"⚠ 다른 논문 {others}곳이 경성 실패다 --- 이 스텝({d.name})은 아니므로 "
              f"막지 않는다: {sorted({x.get('논문') for x in fresh if x not in mine})}")
    if r.get("빚이 늘었나"):
        print(f"⚠ 묵은 빚 {r.get('묵은 빚')} > 등록된 빚 {r.get('등록된 빚')} --- 래칫이 "
              "올랐다(고칠 자리는 ingest/audit.py 의 DEAD_NUMBERS·PAPER_DEBT 다)")
    if mine:
        for x in mine:
            print(f"   줄 {x.get('줄')} · 죽은 값 \"{x.get('죽은 값')}\" → 산 값 "
                  f"\"{x.get('산 값')}\"(정정 노트 {x.get('정정 노트')}) · "
                  f"errata 있나: {x.get('errata 있나')}")
        raise SystemExit(
            f"🔴 죽은 숫자 게이트({phase}): {d.name} 이 정정된 숫자 {len(mine)}곳을 "
            "표지 없이 인용한다. 푸는 길 둘 --- ⓐ 그 줄 앞뒤 2줄 안에 정정 문단"
            "(`죽은 숫자`·`정정`·`철회`·`은퇴` 중 한 낱말 또는 산 값)을 넣는다 "
            "ⓑ 오탐이면 meta.json 의 `errata` 에 **그 숫자를 문자로** 적고 왜 오탐인지 쓴다.")
    print(f"✅ 죽은 숫자 게이트({phase}) 통과 --- {d.name} 경성 실패 0곳 "
          f"(묵은 빚 {r.get('묵은 빚')}/{r.get('등록된 빚')})")


def build(slug: str) -> Path:
    d = _dir(slug)
    _dead_gate(d, "build")
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
    # 🔴 build 를 건너뛰고 보내는 길이 있다(PDF 가 이미 있으면 아래에서 build 를 안
    # 부른다). 483 이 그렇게 나갔다 --- 그래서 게이트는 **두 곳 다** 걸어야 한다.
    _dead_gate(d, "send")
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
