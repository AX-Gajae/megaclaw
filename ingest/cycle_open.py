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
AGENT_DIRS = [ROOT / "cycle_log/agent_tasks/forward",
              ROOT / "cycle_log/agent_tasks/attr",
              ROOT / "cycle_log/agent_tasks/venue"]


def _sh(cmd: list[str], timeout: int = 1800) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -9, f"시간초과 {timeout}s"


def _bar(t: str) -> None:
    print(f"\n{'─' * 4} {t} {'─' * max(0, 56 - len(t))}")


def pending_agent_tasks() -> list[Path]:
    """응답이 아직 없는 `.req.json`. **여기 있는 것이 내가 할 일이다.**"""
    out = []
    for d in AGENT_DIRS:
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
    a = ap.parse_args()
    todo: list[str] = []

    # ① 수집 --- 종료 코드가 아니라 산출물의 성장으로 판정한다(ingest.collect 규칙)
    if not a.no_collect:
        _bar("① 수집")
        code, out = _sh([sys.executable, "-m", "ingest.collect"])
        print(out.rstrip())
        if code:
            todo.append("🔴 수집 실패 --- 위 서명을 보고 **이번 사이클에** 고친다")
        if "연속 무성장" in out:
            todo.append("⚠ 연속 무성장 --- 원천이 멈춘 건지 우리가 막힌 건지 갈라라")

    # ② 전향 패스 --- 종량제 API 를 안 쓴다(에이전트 2패스)
    if not a.no_forward:
        _bar("② 전향 패스")
        code, out = _sh(["/bin/zsh", "-c",
                         'export PATH="$HOME/google-cloud-sdk/bin:/usr/local/bin:$PATH"; '
                         "set -a; source .env; set +a; "
                         f"{sys.executable} -m harness.forward"])
        for ln in out.splitlines():
            if ln.startswith("[") or ln.startswith("===") or "⛔" in ln or "⏳" in ln:
                print(ln)
        if code:
            todo.append("🔴 전향 패스 실패 --- 위 출력 확인")

    # ③ 내가 해야 하는 것 --- 파일로 세워서 넘긴다
    _bar("③ 에이전트 대기(= 이번 사이클에 내가 할 일)")
    reqs, preds = pending_agent_tasks(), pending_predictions()
    if not reqs and not preds:
        print("  없음")
    for p in reqs:
        print(f"  ⏳ 추출 {p.relative_to(ROOT)}")
        todo.append(f"{p.name} 을 읽고 같은 이름 .res.json 을 쓴 뒤 전향 패스 재실행")
    for p in preds:
        print(f"  ⏳ 예측 {p.relative_to(ROOT)}")
        todo.append(f"{p.name} 을 읽고 예측 JSON(median-of-3 이면 run1..3)을 쓴 뒤 재실행")

    # ④ 규약 위반
    _bar("④ 규약 검사")
    code, out = _sh([sys.executable, "-m", "paper.program", "check"])
    print(out.rstrip())
    if '"위반": "없음"' not in out:
        todo.append("🔴 규약 위반 --- 트랙에 근거 노트/결정 규칙을 채운다")

    # ⑤ 트랙 --- 무엇을 잴 차례인가
    _bar("⑤ 트랙(다음 실험)")
    code, out = _sh([sys.executable, "-m", "paper.program", "next"])
    try:
        for t in json.loads(out):
            if t.get("상태") == "지금 가능":
                print(f"  ▶ {t['트랙']}: {str(t.get('다음',''))[:180]}…")
    except Exception:
        print(out[:800])

    _bar("이번 사이클 할 일")
    if not todo:
        print("  기계적인 것은 다 돌았다 --- 트랙에서 하나 골라 재라(사전등록 먼저).")
    for i, t in enumerate(todo, 1):
        print(f"  {i}. {t}")
    print("\n크론이 아니라 이 명령이 사이클을 연다. 데몬 idle_exit 에 안 물린다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
