"""사이클 개시 — **크론을 대신한다**. 한 번 부르면 그 사이클의 할 일이 나온다 (노트 888).

**왜 이 파일이 있나.** 2026-08-09 에 셋을 실측했고 셋 다 같은 말을 했다.

  ① 주 1회 크론 `forward_run.sh` 가 **두 번 돌아 두 번 다 죽어 있었다**
     (7/27·8/03 · `FileNotFoundError: 'bq'`). 2주 동안 아무도 몰랐다.
  ② 고쳐서 다시 돌렸더니 `400 credit balance is too low` 를 내고도
     **종료 코드 0** 으로 끝났다. 크론 로그만 보면 성공이다.
  ③ 그 유료 경로가 하려던 일은 **시공 계약서(`ROPU2616`)를 팝업 뱅크에 넣는 것**
     이었다. 승격 게이트가 "문서가 있나" 하나뿐이라 통과했을 것이고, step3 가
     **방문객이 없는 것에 방문 예측을 봉인**했을 것이다.

셋 다 **루프 안에 판단하는 자가 있어야만** 잡힌다. 그리고 넷째가 있다 ---
예약 작업을 발화시키는 데몬이 2026-08-06 15:29 UTC 에 `cause=idle_exit` 로
스스로 내려갔다(붙어 있는 클라이언트가 없어서). 무인 자동실행을 그 위에 얹으면
**멈춘 사실이 어디에도 안 남는다.**

그래서 사용자가 골랐다(2026-08-09): *"(나) 세션 안에서 도는 루프로 바꾼다."*
T7 트랙이 이미 그렇게 적어 두고 있었다 --- *"남은 사람 게이트는 크론 설치뿐이고
**그것도 사이클 수동 실행으로 대체 가능**하다."*

**이 모듈은 일을 대신 안 한다 --- 무엇을 할지 보여 준다.**
기계적인 것(수집·전향 패스·규약 검사)은 돌리고, 판단이 필요한 자리는
**대기 목록으로 세워서** 세션에 넘긴다. 스스로 판단한 척하지 않는다.

쓰는 법::

    python3 -m ingest.cycle_open              # 전부
    python3 -m ingest.cycle_open --no-forward # 수집·트랙만(빠름)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 🔴 **하드코딩한 목록은 새 디렉터리를 못 본다.** `postprocess` 에 에이전트 모드를
# 붙였을 때(2026-08-10) 이 목록에 없어서 그 대기가 사이클 할 일에 **안 올라왔다** ---
# 요청은 쌓이는데 아무도 안 보는 상태. 목록을 지우고 **부모를 훑는다**.
AGENT_ROOT = ROOT / "cycle_log/agent_tasks"


def _sh(cmd: list[str], timeout: int = 1800) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -9, f"시간초과 {timeout}s"


def _bar(t: str) -> None:
    # **flush 는 선택이 아니다**(노트 686). stdout 을 파일로 돌리면 파이썬이
    # 블록 버퍼(8KB)를 쓰므로 진행이 로그에 안 보이고, 그러면 '멈춘 것'과
    # '버퍼에 갇힌 것'을 못 가른다. 보고가 요지인 모듈이 그 함정에 걸렸었다.
    print(f"\n{'─' * 4} {t} {'─' * max(0, 56 - len(t))}", flush=True)


def pending_agent_tasks() -> list[Path]:
    """응답이 아직 없는 `.req.json`. **여기 있는 것이 내가 할 일이다.**"""
    out = []
    for d in sorted(AGENT_ROOT.glob("*")) if AGENT_ROOT.is_dir() else []:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.req.json")):
            if not (d / (p.name[:-len(".req.json")] + ".res.json")).exists():
                out.append(p)
    return out


def pending_predictions() -> list[Path]:
    """봉인 대기 --- `.request.md` 는 있는데 예측(또는 런)이 아직 없는 것."""
    out = []
    for d in (ROOT / "cycle_log/forward", ROOT / "cycle_log/forward_challenger"):
        if not d.is_dir():
            continue
        for r in sorted(d.glob("*.request.md")):
            code = r.name[:-len(".request.md")]
            if (d / f"{code}.prediction.json").exists():
                continue
            out.append(r)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-forward", action="store_true", help="전향 패스를 건너뛴다")
    ap.add_argument("--no-collect", action="store_true")
    ap.add_argument("--slack", action="store_true",
                    help="사이클 요약을 슬랙 DM 으로 (크론에서 켠다)")
    a = ap.parse_args()
    todo: list[str] = []
    lines: list[str] = []          # 슬랙 본문 --- 화면과 따로 모은다

    # ① 수집 --- 종료 코드가 아니라 산출물의 성장으로 판정한다(ingest.collect 규칙)
    if not a.no_collect:
        _bar("① 수집")
        code, out = _sh([sys.executable, "-m", "ingest.collect"])
        print(out.rstrip(), flush=True)
        lines += [l for l in out.splitlines() if l.strip().startswith(("성장", "──", "  "))][:8]
        if code:
            todo.append("🔴 수집 실패 --- 위 서명을 보고 **이번 사이클에** 고친다")
        # **사유를 아는 정체는 할 일에 안 올린다**(노트 889). `ingest.collect` 가
        # 둘을 갈라 찍으므로 여기서는 '사유 모르는' 쪽만 본다 --- 그래야 슬랙이
        # 매 사이클 '할 일 1건' 을 반복하지 않고, 반복하지 않아야 진짜일 때 읽힌다.
        if "사유 모르는 3회+ 연속 무성장" in out:
            todo.append("⚠ 사유 모르는 연속 무성장 --- 원천이 멈춘 건지 우리가 막힌 건지 갈라라")

    # ② 전향 패스 --- 종량제 API 를 안 쓴다(에이전트 2패스)
    if not a.no_forward:
        _bar("② 전향 패스")
        code, out = _sh(["/bin/zsh", "-c",
                         'export PATH="$HOME/google-cloud-sdk/bin:/usr/local/bin:$PATH"; '
                         "set -a; source .env; set +a; "
                         f"{sys.executable} -m harness.forward"])
        keep = [ln for ln in out.splitlines()
                if ln.startswith("[") or ln.startswith("===") or "⛔" in ln or "⏳" in ln]
        for ln in keep:
            print(ln, flush=True)
        lines += keep[-6:]
        if code:
            # 🔴 **실패했으면 이유를 찍는다**(2026-08-10 자가 적발). 위 필터는
            # `[`·`===` 로 시작하는 줄만 남기는데 **파이썬 트레이스백은 둘 다
            # 아니다.** 그래서 첫 launchd 실행에서 전향 패스가 죽었을 때 로그에
            # 남은 것이 `===== 전향 패스 2026-08-10 =====` 한 줄뿐이었다 ---
            # 실패를 보고하면서 실패의 이유를 버렸다. 오늘 아침에 잡은
            # '종료 코드가 거짓말한다' 의 사촌이다: **보고가 반쪽이면 없는 것과 같다.**
            tail = [l for l in out.strip().splitlines() if l.strip()][-8:]
            print("  🔴 실패 꼬리:", flush=True)
            for l in tail:
                print("   |", l[:200], flush=True)
            lines += ["🔴 전향 실패:"] + ["  " + l[:160] for l in tail[-4:]]
            todo.append("🔴 전향 패스 실패 --- " + (tail[-1][:120] if tail else "출력 없음"))
        # 후처리는 이제 무료 경로가 있다(2026-08-10). 문구가 바뀌었으므로 감지도 바꾼다
        # --- 안 바꾸면 **영영 안 걸리는 검사**가 남는다(죽은 검사).
        if "⏳ 후처리 에이전트 대기" in out:
            todo.append("⏳ `cycle_log/agent_tasks/postprocess/*.req.json` 을 채우고 전향 패스 재실행")
        if "🔴 후처리 실패" in out:
            todo.append("🔴 후처리 실패 --- 위 꼬리 확인")

    # ③ 내가 해야 하는 것 --- 파일로 세워서 넘긴다
    _bar("③ 에이전트 대기(= 이번 사이클에 내가 할 일)")
    reqs, preds = pending_agent_tasks(), pending_predictions()
    if not reqs and not preds:
        print("  없음", flush=True)
    for p in reqs:
        print(f"  ⏳ 추출 {p.relative_to(ROOT)}", flush=True)
        todo.append(f"{p.name} 을 읽고 같은 이름 .res.json 을 쓴 뒤 전향 패스 재실행")
    for p in preds:
        print(f"  ⏳ 예측 {p.relative_to(ROOT)}", flush=True)
        todo.append(f"{p.name} 을 읽고 예측 JSON(median-of-3 이면 run1..3)을 쓴 뒤 재실행")

    # ④ 규약 위반
    _bar("④ 규약 검사")
    code, out = _sh([sys.executable, "-m", "paper.program", "check"])
    print(out.rstrip(), flush=True)
    if '"위반": "없음"' not in out:
        todo.append("🔴 규약 위반 --- 트랙에 근거 노트/결정 규칙을 채운다")

    # ⑤ 트랙 --- 무엇을 잴 차례인가
    _bar("⑤ 트랙(다음 실험)")
    code, out = _sh([sys.executable, "-m", "paper.program", "next"])
    try:
        for t in json.loads(out):
            if t.get("상태") == "지금 가능":
                print(f"  ▶ {t['트랙']}: {str(t.get('다음',''))[:180]}…", flush=True)
    except Exception:
        print(out[:800], flush=True)

    _bar("이번 사이클 할 일")
    if not todo:
        print("  기계적인 것은 다 돌았다 --- 트랙에서 하나 골라 재라(사전등록 먼저).", flush=True)
    for i, t in enumerate(todo, 1):
        print(f"  {i}. {t}", flush=True)

    # ⑥ 슬랙 --- **크론으로 돌리면 아무도 안 본다**(2026-08-09 실측). 보고가
    # 사람에게 도착해야 크론이 의미가 있다. 알림 실패는 루프를 안 죽인다.
    if a.slack:
        head = ("🔴 사이클 — 할 일 %d건" % len(todo)) if todo else "✅ 사이클 — 할 일 없음"
        body = [head, ""]
        body += [l for l in lines if l.strip()]
        if todo:
            body += ["", "*할 일*"] + [f"{i}. {t}" for i, t in enumerate(todo, 1)]
        body += ["", "`python3 -m ingest.cycle_open` 로 세션에서 이어간다."]
        from .notify import dm
        r = dm("\n".join(body))
        print("\n슬랙:", "보냄" if r.get("보냄") else "실패 — " + str(r.get("사유"))[:120], flush=True)

    print("\n크론은 기계적인 것만 돌린다. 판단이 필요한 자리는 위 '할 일' 로 나온다.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
