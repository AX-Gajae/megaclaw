"""연구 프로그램 층 — 사이클 위에 **트랙**을 얹고, 리포트를 생성한다(노트 642).

**왜 필요한가.** `data/lab/denominator.json` 은 사이클 단위다 --- 노트 하나에
측정 하나, 판정 하나. 그 구조는 *"이 축을 채택하나"* 처럼 한 번에 끝나는
질문에 맞다. 그런데 사용자가 물은 것들은 성질이 다르다:

    어떤 모델을 파인튜닝하나 · 상태를 어떻게 정의하나 · 어떤 소셜 법칙을
    찾나 · 어떤 기업의 어떤 문제를 푸나 · 어떤 아키텍처를 쓰나 · 무엇을
    최적화하나

이 여섯은 **한 사이클에 안 끝나고 입장이 쌓인다.** 641개 노트에 그 입장이
흩어져 있어서 물을 때마다 다시 찾아야 했고, 그래서 답이 매번 세 장짜리로
줄어들었다. 트랙은 그 입장을 **상시로** 들고 있는 자리다.

**리포트를 손으로 안 쓴다.** `data/lab/program.json` 의 트랙과
`denominator.json` 의 노트에서 생성한다. 그래야 사이클이 돌 때마다 리포트가
같이 갱신되고, 리포트와 대장이 어긋날 수 없다.

**규약 셋**(program.json 의 ``메타.규약`` 과 같은 것을 코드가 강제한다):

  ① 입장에는 **근거 노트 번호**를 단다 --- 근거 없는 문장은 트랙에 못 들어온다.
  ② 미결에는 **결정 규칙**을 단다 --- *무엇이 관측되면 이 입장이 바뀌나.*
  ③ 측정 안 한 것은 **측정 안 했다고** 적는다(노트 133).

쓰는 법::

    python3 -m paper.program status          # 트랙 요약
    python3 -m paper.program next            # 다음 실험 후보와 근거
    python3 -m paper.program report          # 긴 리포트(HTML) 생성
    python3 -m paper.program check           # 규약 위반 찾기
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROG = ROOT / "data/lab/program.json"
LEDGER = ROOT / "data/lab/denominator.json"
OUT = ROOT / "docs/program-report.html"

NOTE = re.compile(r"노트\s*(\d+)")


def load() -> dict:
    return json.loads(PROG.read_text())


def ledger() -> dict:
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}


def _notes_of(track: dict) -> set:
    """트랙이 인용한 노트 번호."""
    s = json.dumps(track, ensure_ascii=False)
    return {int(m) for m in NOTE.findall(s)}


def known_notes() -> set:
    """대장에 실재하는 노트 번호. **대장 전문을 훑는다.**

    처음에는 ``노트`` 필드만 봤는데 436개 항목 중 **102개**(400번 이후)에만
    있었다. 그 앞의 항목은 키가 ``targets`` · ``왜`` 처럼 설정 이름이고 노트
    번호가 **값 안에서만** 참조된다 --- 그래서 133 · 149 · 395 를 인용할 때마다
    '없는 노트' 로 오탐이 났다. 실제로 첫 실행에서 그렇게 나왔다.

    대신 이 검사는 *"이 번호가 대장 어딘가에 등장하나"* 까지만 본다. 오타가
    우연히 다른 곳의 번호와 겹치면 못 잡는다 --- **약한 가드임을 알고 쓴다.**
    강한 가드는 노트마다 항목을 하나씩 두도록 대장 형식을 정리한 뒤에 된다.
    """
    out = {int(x) for x in NOTE.findall(LEDGER.read_text())} if LEDGER.exists() else set()
    for _k, v in ledger().items():
        if isinstance(v, dict) and isinstance(v.get("노트"), int):
            out.add(v["노트"])
    return out


# ── 규약 검사 ──────────────────────────────────────────────────
def check(p: dict | None = None) -> list:
    """규약 위반을 찾는다. **리포트를 만들기 전에 돈다.**

    이 실험실이 반복해서 당한 것은 *근거 없이 승격된 문장*이다(노트 133 ·
    613). 트랙은 그 문장이 오래 남는 자리라 위험이 더 크다 --- 대장은
    사이클이 지나면 묻히지만 트랙은 리포트에 매번 실린다.
    """
    p = p or load()
    bad = []
    known = known_notes()
    OK_ST = {"지금 가능", "막힘", "닫힘", "쉼"}
    #: 칸의 **형태**를 못박는다(2026-08-07). `다음 실험` 을 리스트로 적었더니
    #: `check` 는 "위반 없음" 을 내고 **`next` 만 `AttributeError` 로 죽었다** ---
    #: 규약 40 과 같은 부류다: 검사가 통과했는데 다음 걸음이 깨진다.
    SHAPE = {"질문": str, "현재 입장": str, "근거": list, "미결": list,
             "다음 실험": str, "상태": str}
    for name, t in p.get("트랙", {}).items():
        for key, typ in SHAPE.items():
            if key in t and not isinstance(t[key], typ):
                bad.append(f"{name}: '{key}' 가 {typ.__name__} 이어야 하는데 "
                           f"{type(t[key]).__name__} 이다")
        #: **곁가지 키를 위반으로 찍는다**(노트 867 · 티처 #32 중대 1). '다음' 키에
        #: 갱신이 가고 `next` 는 '다음 실험' 을 읽어 — 죽은 좌표(0순위 813/814)가
        #: 세 관문(next → 티처 → 사전등록)을 통과했다. 노트 546/549 병의 재발.
        stray = set(t.keys()) - set(SHAPE)
        if stray:
            bad.append(f"{name}: 스키마 밖 키 {sorted(stray)} — '다음 실험' 하나에만 적는다(노트 867)")
        if not t.get("근거"):
            bad.append(f"{name}: 근거가 없다")
        # **상태는 값으로 적는다**(노트 730 · 규약 15). 산문 추론을 없앴으므로
        # 값이 없으면 `next` 가 "(상태 안 적힘)" 을 내고 트랙 고르기가 망가진다.
        st = (t.get("상태") or "").strip()
        if st not in OK_ST:
            bad.append(f"{name}: 상태가 없거나 모르는 값이다 ({st!r} · "
                       f"허용 {sorted(OK_ST)})")
        for i, m in enumerate(t.get("미결") or []):
            if not m.get("결정 규칙"):
                bad.append(f"{name}: 미결 {i} 에 결정 규칙이 없다")
        cited = _notes_of(t)
        ghost = {n for n in cited if known and n not in known}
        if ghost:
            bad.append(f"{name}: 대장에 없는 노트를 인용한다 {sorted(ghost)}")
    return bad


# ── 다음 실험 고르기 ───────────────────────────────────────────
def nxt(p: dict | None = None) -> list:
    """트랙별 다음 실험과 **막힌 이유**를 낸다.

    고르는 기준을 점수로 안 만든다 --- 이 판이 점수로 고르다 당한 적이
    많다(노트 82 · 90). 대신 **의존성**을 그대로 보여 준다: 어떤 트랙이
    다른 트랙을 기다리는지가 순서를 정한다.
    """
    p = p or load()
    out = []
    for name, t in p.get("트랙", {}).items():
        e = (t.get("다음 실험") or "").strip()
        # **상태는 값으로만 읽는다 --- 산문에서 추론하지 않는다**(노트 730).
        #
        # 원래는 '다음 실험' 글에 "대기"/"없음" 이 있나로 판정했다. T5 를 닫고
        # "없다" 라고 적었더니 안 걸려서 **"없다" 를 검사에 더했는데, 그러자
        # T7 의 "둘째 적재가 없다"(곁설명)를 막힘으로 잡았다.** 문자열 검사
        # 버그를 문자열 검사로 고치려 한 것이고, 노트 674 · 677 · 693 · 697 이
        # 같은 계열이다. **그래서 추론을 없애고 값을 요구한다** --- 값이 없으면
        # `check()` 가 규약 위반으로 잡는다.
        state = (t.get("상태") or "(상태 안 적힘)").strip()
        out.append({"트랙": name, "질문": t.get("질문"),
                    "다음": e or "(안 적힘)", "상태": state})
    out.sort(key=lambda x: x["상태"] != "지금 가능")
    return out


# ── 리포트 ─────────────────────────────────────────────────────
CSS = """
:root{--bg:#fbfaf8;--fg:#1b1a18;--mut:#6f6a62;--line:#e0dcd4;--card:#fff;
 --acc:#1f6f6b;--warn:#8a6a1f;--bad:#8f3030;--ok:#1f6f4a}
@media (prefers-color-scheme:dark){:root{--bg:#14150f;--fg:#eceae4;--mut:#9b968c;
 --line:#2d2f26;--card:#1b1d15;--acc:#63c9c0;--warn:#d6ab4e;--bad:#e08585;--ok:#77c79b}}
:root[data-theme=dark]{--bg:#14150f;--fg:#eceae4;--mut:#9b968c;--line:#2d2f26;
 --card:#1b1d15;--acc:#63c9c0;--warn:#d6ab4e;--bad:#e08585;--ok:#77c79b}
:root[data-theme=light]{--bg:#fbfaf8;--fg:#1b1a18;--mut:#6f6a62;--line:#e0dcd4;
 --card:#fff;--acc:#1f6f6b;--warn:#8a6a1f;--bad:#8f3030;--ok:#1f6f4a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:16px/1.72 "Iowan Old Style","Apple Garamond",Georgia,"Nanum Myeongjo",serif;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:52rem;margin:0 auto;padding:4rem 1.5rem 7rem}
h1{font-size:2.1rem;line-height:1.2;margin:0 0 .4rem;text-wrap:balance;letter-spacing:-.01em}
h2{font-size:1.35rem;margin:3.4rem 0 .3rem;text-wrap:balance}
h3{font-size:1.02rem;margin:1.8rem 0 .4rem;color:var(--mut);
 font-family:ui-sans-serif,system-ui,sans-serif;font-weight:650;
 text-transform:uppercase;letter-spacing:.08em;font-size:.76rem}
.sub{color:var(--mut);margin:0 0 2.4rem;font-size:.95rem}
.q{color:var(--mut);font-style:italic;margin:.1rem 0 1.1rem}
.pos{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--acc);
 padding:1rem 1.2rem;border-radius:.35rem;margin:.6rem 0 1.4rem}
ul{padding-left:1.15rem;margin:.3rem 0 1.2rem}
li{margin:.42rem 0}
.rule{background:var(--card);border:1px solid var(--line);border-radius:.35rem;
 padding:.75rem .95rem;margin:.5rem 0}
.rule b{color:var(--warn)}
.tag{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.72rem;
 border:1px solid var(--line);border-radius:.25rem;padding:.1rem .42rem;color:var(--mut)}
.go{color:var(--ok)} .stop{color:var(--bad)}
table{width:100%;border-collapse:collapse;font-size:.9rem;margin:1rem 0}
th,td{text-align:left;padding:.5rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}
th{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.72rem;letter-spacing:.06em;
 text-transform:uppercase;color:var(--mut)}
.scroll{overflow-x:auto}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.86em;
 background:var(--card);border:1px solid var(--line);border-radius:.2rem;padding:.05rem .3rem}
.cross{border-top:2px solid var(--acc);padding-top:1rem;margin-top:1rem}
hr{border:0;border-top:1px solid var(--line);margin:3rem 0}
"""


def _md(s: str) -> str:
    """**굵게** 와 ``코드`` 만 처리한다 --- 리포트 문장이 그 둘만 쓴다."""
    s = html.escape(str(s))
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"``(.+?)``", r"<code>\1</code>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def report(path: Path = OUT) -> Path:
    p = load()
    bad = check(p)
    m = p.get("메타", {})
    tr = p.get("트랙", {})
    parts = [f"<title>{html.escape(m.get('제목','연구 프로그램'))}</title>",
             f"<style>{CSS}</style>", "<div class=wrap>"]
    parts.append(f"<h1>{_md(m.get('제목',''))}</h1>")
    parts.append(f"<p class=sub>생성 {date.today().isoformat()} · 트랙 {len(tr)}개 · "
                 f"대장 노트 {len(ledger())}건 · 규약 위반 "
                 f"{'<span class=stop>%d건</span>' % len(bad) if bad else '<span class=go>없음</span>'}</p>")
    parts.append(f"<div class=pos>{_md(m.get('왜 이 층이 필요한가',''))}</div>")
    if m.get("규약"):
        parts.append("<h3>규약</h3><ul>" +
                     "".join(f"<li>{_md(x)}</li>" for x in m["규약"]) + "</ul>")
    if bad:
        parts.append("<h3 class=stop>규약 위반</h3><ul>" +
                     "".join(f"<li class=stop>{_md(x)}</li>" for x in bad) + "</ul>")

    # 한눈 표
    parts.append("<h2>트랙 한눈</h2><div class=scroll><table>")
    parts.append("<tr><th>트랙</th><th>질문</th><th>현재 입장</th><th>다음</th></tr>")
    for k, t in tr.items():
        #: 상태는 **값으로 읽는다**(노트 730 · 규약 15). 산문 추론('대기'/'없음' 문자열)은
        #: 노트 868 에서 제거 — 867 커밋이 주선 트랙 T1·T4 를 빨갛게 실어 날랐다(티처 #33).
        st = (t.get("상태") or "").strip() or "(상태 안 적힘)"
        cls = "go" if st == "지금 가능" else "stop"
        parts.append(f"<tr><td><span class=tag>{html.escape(k)}</span></td>"
                     f"<td>{_md(t.get('질문',''))}</td>"
                     f"<td>{_md(t.get('현재 입장',''))}</td>"
                     f"<td class={cls}>{st}</td></tr>")
    parts.append("</table></div>")

    # 트랙 본문
    for k, t in tr.items():
        parts.append(f"<hr><h2>{html.escape(k)}</h2>")
        parts.append(f"<p class=q>{_md(t.get('질문',''))}</p>")
        parts.append(f"<div class=pos>{_md(t.get('현재 입장',''))}</div>")
        parts.append("<h3>근거</h3><ul>" +
                     "".join(f"<li>{_md(x)}</li>" for x in t.get("근거", [])) + "</ul>")
        if t.get("미결"):
            parts.append("<h3>미결 — 무엇이 관측되면 입장이 바뀌나</h3>")
            for u in t["미결"]:
                parts.append(f"<div class=rule><b>{_md(u.get('무엇',''))}</b><br>"
                             f"{_md(u.get('결정 규칙',''))}</div>")
        parts.append(f"<h3>다음 실험</h3><p>{_md(t.get('다음 실험',''))}</p>")
        ns = sorted(_notes_of(t))
        if ns:
            parts.append("<p class=sub>인용 노트 " +
                         " · ".join(f"<span class=tag>{n}</span>" for n in ns) + "</p>")

    # 수집 감사 --- **글이 아니라 지금 잰 값을 싣는다.** 트랙 본문은 사람이
    # 적은 입장이고 이 절은 `ingest/audit` 이 방금 계산한 것이다. 둘이
    # 어긋나면 그것 자체가 신호다.
    try:
        from ingest.audit import audit as _audit
        a = _audit()
        parts.append("<hr><h2>수집 감사 <span class=tag>지금 잰 값</span></h2>")
        parts.append("<h3>덮음과 출처</h3><div class=scroll><table>"
                     "<tr><th>원천</th><th>대상</th><th>덮음</th><th>출처 구성</th></tr>")
        for r in a["덮음"]:
            parts.append(f"<tr><td>{_md(r.get('원천',''))}</td>"
                         f"<td>{r.get('대상','')}</td><td>{r.get('덮음','')}</td>"
                         f"<td>{_md(json.dumps(r.get('출처', {}), ensure_ascii=False))}</td></tr>")
        parts.append("</table></div>")
        parts.append("<h3>신선도 — 역사가 있나</h3><div class=scroll><table>"
                     "<tr><th>원천</th><th>범위</th><th>역사</th><th>쓸모</th></tr>")
        for r in a["신선도"]:
            parts.append(f"<tr><td>{_md(r['원천'])}</td>"
                         f"<td>{_md(' ~ '.join(map(str, r['범위'] or [])))}</td>"
                         f"<td>{_md(r['역사'])}</td><td>{_md(r['쓸모'])}</td></tr>")
        parts.append("</table></div>")
        parts.append("<h3>절단 — 잘린 걸 모르면 '많음'이 전부 같은 값이 된다</h3>")
        for r in a["절단"]:
            parts.append(f"<div class=rule><b>{_md(r['수집기'])}</b> — 상한 {_md(r['상한'])}<br>"
                         f"{_md(r['확인'])}<br>{_md(r['대응'])}</div>")
        parts.append("<h3>대조 — 수집 품질의 직접 증거</h3>")
        for r in a["대조"]:
            parts.append(f"<div class=rule><b>{_md(r['대상'])}</b> {_md(r['결과'])}<br>"
                         f"{_md(r['원천A'])} vs {_md(r['원천B'])}<br>{_md(r['덤'])}</div>")
        parts.append(f"<div class=rule><b>메타 신뢰</b><br>{_md(a['메타 신뢰']['확인'])}<br>"
                     f"{_md(a['메타 신뢰']['함의'])}<br>안 한 것: {_md(a['메타 신뢰']['안 한 것'])}</div>")
        parts.append(f"<div class=rule><b>승인 대기</b> — {_md(a['승인 대기']['규약'])}<br>"
                     + _md(" · ".join(a["승인 대기"]["라벨 후보"])) + "</div>")
    except Exception as e:
        parts.append(f"<hr><h2>수집 감사</h2><p class=stop>감사가 안 돌았다: "
                     f"{html.escape(type(e).__name__)}</p>")

    if p.get("교차 결론"):
        parts.append("<hr><h2>교차 결론</h2><div class=cross><ul>" +
                     "".join(f"<li>{_md(x)}</li>" for x in p["교차 결론"]) + "</ul></div>")
    parts.append("</div>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def status() -> None:
    p = load()
    print(json.dumps({"트랙": len(p.get("트랙", {})),
                      "규약 위반": check(p),
                      "다음": nxt(p)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "report":
        print(json.dumps({"생성": str(report())}, ensure_ascii=False))
    elif cmd == "next":
        print(json.dumps(nxt(), ensure_ascii=False, indent=1))
    elif cmd == "check":
        b = check()
        print(json.dumps({"위반": b or "없음"}, ensure_ascii=False, indent=1))
    else:
        status()
