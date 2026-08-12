# -*- coding: utf-8 -*-
"""상시 수집 데몬 --- 크론(하루 한 번) 대신 **계속** 돈다(기본 60초).

🔴 **노트 952 에서 저장소 안으로 들어왔다.** `/Users/ax/wm_harvest/harvest_daemon.py`
가 원본이었고, 그 자리에 둔 이유는 *「사이클 에이전트가 `git add -A` 를 쓴다」* 였다.
🔴 **그 이유는 코드를 저장소 밖에 두는 근거가 못 된다** --- 이유가 참이면 고칠 것은
`git add -A` 쪽이지 코드의 거처가 아니고, 저장소 밖에 있는 동안 **이 파일은
버전 관리도 티처 검토도 ⑤′ 도 안 받았다**. 실제로 이 사이클이 열어 보니 매 회차
`popupsnap` 이 죽고 있었는데 **아무 자에도 안 걸렸다.**
(로그와 상태는 여전히 `/Users/ax/wm_harvest/` 에 쓴다 --- 그건 산출물이지 코드가 아니다.)

🔴 **환경을 명시적으로 세운다**(952 실측). launchd 가 주는 PATH 는
`/usr/bin:/bin:/usr/sbin:/sbin` 뿐이라 gcloud SDK 도 python3.12 도 안 보인다.
`popupsnap` 이 **매 회차** ``FileNotFoundError: 'bq'`` 로 죽던 뿌리가 그것이고,
겹은 하나가 아니라 **넷**이었다(`ingest/popupsnap.py:_bq_env()` 참조).

🔴 조항 59 --- 종료 코드 0 을 성공으로 안 읽는다. **자랐는지**를 본다.
🔴🔴 그런데 「바이트가 늘었다」도 성공이 아니었다(2026-08-12 13:41 실측):
   `ingest.kobis` 는 매 회차 같은 파일에 **시각과 git HEAD 만 새로 쓰고 실행 기록을
   덧붙인다.** 행 102 는 그대로인데 +134바이트가 는다. 60초마다 커밋하면
   **하루 1,440 커밋 잡음 + 파일 무한 증식**이다.
   → **`ingest.collect` 자신이 세는 「성장 N」을 쓴다.** 성장 0 이면 커밋하지 않고
     **수정분을 되돌려 작업 트리를 깨끗하게 유지한다**(다른 사이클의 ⑤′ ⓪ 관문 보호).
     되돌리는 것은 **타임스탬프 잡음뿐**이고 실제 관측은 `성장>0` 일 때만 남는다.
"""
import json, os, re, subprocess, sys, time, datetime as dt
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
LOG = Path("/Users/ax/wm_harvest/harvest.jsonl")
STATE = Path("/Users/ax/wm_harvest/state.json")
INTERVAL = int(os.environ.get("WM_HARVEST_INTERVAL", "60"))
PATHS = ["data/ingest", "data/state"]   # 🔴 951 머지가 data/state 로그로 막혔다(2026-08-12)


def _env() -> dict:
    """🔴 952 신설 --- launchd 의 헐벗은 PATH 를 **여기서 한 번** 채운다.

    안 채우면 `bq`·`gcloud`·python3.12 가 안 보이고, 그 결과가 **매 회차 조용한
    실패**다. 🔴 이 저장소가 이미 두 번 앓은 병이다(노트 888 의 크론 · 티처 #53 C4).
    """
    env = dict(os.environ)
    extra = [d for d in ("/Users/ax/google-cloud-sdk/bin", "/Users/ax/.local/bin",
                         "/opt/homebrew/bin", "/usr/local/bin") if Path(d).is_dir()]
    parts = env.get("PATH", "").split(":")
    env["PATH"] = ":".join([d for d in extra if d not in parts] + parts)
    env.setdefault("PYTHONPATH", str(ROOT))
    return env


def _sh(cmd, cwd=ROOT, timeout=1800):
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                           timeout=timeout, env=_env())
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT"
    except Exception as e:                                        # noqa: BLE001
        return -1, "%s: %s" % (type(e).__name__, e)


def _bytes() -> int:
    n = 0
    for p in (ROOT / "data/ingest").rglob("*"):
        if p.is_file():
            try:
                n += p.stat().st_size
            except OSError:
                pass
    return n


def _tally(out: str):
    """`ingest.collect` 가 스스로 센 수를 읽는다 --- 「── 성장 0 · 무성장 1 · …」."""
    m = re.search(r"성장\s+(\d+)\s*·\s*무성장\s+(\d+)\s*·\s*건너뜀\s+(\d+)\s*·\s*시간초과\s+(\d+)\s*·\s*실패\s+(\d+)", out)
    if not m:
        return None                                               # 🔴 「0」이 아니라 「못 읽었다」
    k = ("성장", "무성장", "건너뜀", "시간초과", "실패")
    return dict(zip(k, (int(x) for x in m.groups())))


def _new_files() -> list:
    c, o = _sh(["git", "-c", "core.quotePath=false", "ls-files", "--others",
                "--exclude-standard", "--"] + PATHS)
    return [x for x in o.split("\n") if x.strip()] if c == 0 else []


def _wait_lock(sec: int = 60) -> bool:
    for _ in range(sec // 2):
        if not (ROOT / ".git/index.lock").exists():
            return True
        time.sleep(2)
    return not (ROOT / ".git/index.lock").exists()


def _commit(msg: str) -> str:
    if not _wait_lock():
        return "잠금 --- 안 커밋했다(다음 회차 재시도)"
    if _sh(["git", "-c", "core.quotePath=false", "add", "--"] + PATHS)[0] != 0:
        return "add 실패"
    if not _sh(["git", "-c", "core.quotePath=false", "diff", "--cached", "--name-only"])[1].strip():
        return "바뀐 것 없음"
    mf = Path("/Users/ax/wm_harvest/_msg.txt")
    mf.write_text(msg, encoding="utf-8")
    c, o = _sh(["git", "commit", "-F", str(mf), "--"] + PATHS)
    return "커밋함" if c == 0 else "commit 실패: " + o[:200]


def _revert_noise() -> str:
    """🔴 성장 0 일 때만 부른다. **추적 파일의 수정분만** 되돌린다.
    새 파일(untracked)은 **건드리지 않는다** --- 그건 진짜 새 자료일 수 있다."""
    if not _wait_lock():
        return "잠금 --- 안 되돌렸다"
    c, o = _sh(["git", "-c", "core.quotePath=false", "checkout", "--"] + PATHS)
    return "되돌렸다(타임스탬프 잡음)" if c == 0 else "되돌리기 실패: " + o[:150]


def once() -> dict:
    t0 = time.time()
    before = _bytes()
    # 🔴 952 --- 제한을 1800 → 5400 으로 올린다. 등기부가 원천을 셋에서 **다섯**으로
    # 늘렸고, 새로 든 둘은 941 실측으로 각각 **0.633h · 0.485h** 다. 1800 이면
    # 한 회차가 통째로 `TIMEOUT` 이 되고 **느린 것이 고장으로 찍힌다**
    # (`ingest/collect.py` 가 이미 「시간초과는 실패가 아니다」로 갈라 둔 그 병).
    code, out = _sh([sys.executable, "-m", "ingest.collect"], timeout=5400)
    grew = _bytes() - before
    tally = _tally(out)
    new = _new_files()

    # 🔴 판정 --- 세 갈래를 구별한다(조항 59)
    if tally is None:
        real, why = bool(new), "🔴 집계 줄을 못 읽었다(「성장 0」이 아니다) --- 새 파일 %d개로만 판단" % len(new)
    elif tally["성장"] > 0 or new:
        real, why = True, "성장 %d · 새 파일 %d" % (tally["성장"], len(new))
    else:
        real, why = False, "성장 0 · 새 파일 0 --- 바이트 %+d 는 시각/실행기록 잡음" % grew

    rec = {
        "시각": dt.datetime.now().isoformat(timespec="seconds"),
        "종료코드": code,
        "🔴 collect 자신의 집계": tally if tally is not None else "🔴 못 읽었다",
        "새 파일": new or "없음",
        "바이트 변화": grew,
        "🔴 실질 성장인가": real,
        "🔴 왜": why,
        "초": round(time.time() - t0, 1),
        "브랜치": _sh(["git", "rev-parse", "--abbrev-ref", "HEAD"])[1].strip(),
        "꼬리": out.strip()[-400:],
    }
    rec["처리"] = (_commit("[수집] 상시 데몬 %s — %s\n\n종료코드 %s\n" % (rec["시각"], why, code))
                 if real else _revert_noise())
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    STATE.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def main() -> int:
    while True:
        try:
            r = once()
            print(r["시각"], "실질성장" if r["🔴 실질 성장인가"] else "잡음", r["처리"], flush=True)
        except Exception as e:                                    # noqa: BLE001
            print("루프 예외(계속 돈다):", type(e).__name__, e, flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
