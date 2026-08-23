# -*- coding: utf-8 -*-
"""시대 고정 관문 — 배포물을 «여는 시점»의 sha 실측 대조 (루프 v5.3 부칙 4 · 티처 #142 발의).

왜 있는가(#142 0절 2 실측): 병행 3팔의 시대 단일성은 규율이 아니라 «운»이었다 — 1006 eval 은
배포 manifest 의 sha 를 재실측하지 않고 등록 «상수»를 out 에 게재했고, 1005 가 성공해 그 사이
배포했다면 조용히 새 시대를 읽으며 옛 시대 sha 를 찍었을 것이다(이번엔 1005 실패 = 배포 0 이라
단일 시대가 «결과적으로» 성립했을 뿐).

규격(부칙 4):
  · 배포물(manifest·conformal·리더보드·report)을 여는 모든 러너 phase 는 여는-시점에
    `assert_epoch(등록 sha)` 를 불러 실측 대조한다 — 불일치면 EpochMismatch 예외로
    **측정 없이 중단**(v5.3-2 방향 탐침과 같은 원리: 값을 보고 판정을 고치는 길을 막는다)
  · out/progress 게재는 등록 상수가 아니라 이 함수의 «반환값»(실측 sha + 여는 시각)으로 한다
  · torch 무의존(numpy 무의존) — 언 러너(torch 미사용 형)도 그대로 임포트한다. 배포물 경로는
    `pretrain/transition.py` 의 정의를 미러한다(다른 «목적»의 상수 물려쓰기가 아니라 같은
    실물의 같은 주소다 — 조항 66)

씀:  from pretrain.epoch_guard import assert_epoch, EpochMismatch
     stamp = assert_epoch("3a5c2543a55f1dab")          # 등록 기재값 — 불일치면 예외
     out["시대(부칙 4)"] = stamp                          # 게재는 실측 반환값으로

부칙 5 (티처 #143 발의 · 2026-08-23) — 실행 중 프로세스 판 대조:
왜 있는가(#143 ③ 실측): 데몬 프로세스(8/14 기동)가 방벽(8/16~8/17 커밋) «이전» 코드를 5일간
메모리에 들고 있다가 8/21 스테이지를 쓸어담았다 — 전례 973 사고(8/16) · 8/12 자가 적발
(`59806c146`). «수리 커밋 ≠ 실서빙 반영»이 세 번 실증됐다 — 상주 프로세스가 구판이면 저장소와
실서빙이 조용히 갈라진다.

씀:  from pretrain.epoch_guard import stale_process, StaleProcess
     st = stale_process("/path/daemon.pid", ["pretrain/wm_tools.py"])
     out["실서빙(부칙 5)"] = st                           # 게재는 실측 반환값으로(등록 상수 금지)
     if st["낡음"] and not 재시작_대기물_등재:              # 등재 여부 판정은 호출자 몫
         raise StaleProcess(...)                        # 수리 러너·완결 절차는 중단
재시작은 사용자 몫 그대로다 — 이 검사는 «구판이 돌고 있다»는 사실이 장부에 없는 상태를 막는다.

자기시험: python3 pretrain/epoch_guard.py
  부칙 4 참/거짓 + 부칙 5 참/거짓(임시 git 저장소 + 실제 ps 실측 — 모의 없음) + 본 저장소 스모크
"""
import hashlib
import os
import subprocess
import time

ART = os.environ.get("WM_FOUNDATION_DIR", "/Users/ax/wm_harvest/foundation")
MANIFEST = os.path.join(ART, "transition", "ensemble_manifest.json")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EpochMismatch(RuntimeError):
    """등록 시대 ≠ 실측 시대 — 측정 없이 중단 규격."""


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def assert_epoch(expected_manifest_sha, path=MANIFEST):
    """여는-시점 시대 검사 — path(기본: 배포 manifest)의 sha256/16 을 «지금» 실측해
    등록 기재값과 대조한다. 불일치면 EpochMismatch — 측정 없이 중단하라.

    반환(게재용 실측 스탬프): {"실측 sha", "등록 sha", "여는 시각", "경로"}
    """
    t_open = time.strftime("%Y-%m-%dT%H:%M:%S")
    got = sha16(path)
    if got != str(expected_manifest_sha):
        raise EpochMismatch(
            "🔴 시대 불일치 — 등록 %s ≠ 실측 %s (%s · 여는 시각 %s) — 측정 없이 중단"
            % (expected_manifest_sha, got, path, t_open))
    return {"실측 sha": got, "등록 sha": str(expected_manifest_sha),
            "여는 시각": t_open, "경로": path}


# ── 부칙 5 — 실행 중 프로세스 판 대조 (티처 #143 발의 · 2026-08-23) ──────────────────

class StaleProcess(RuntimeError):
    """구판 실행 중(기동 < 수리 커밋)인데 «재시작 대기물» 미등재 — 중단 규격(부칙 5 ㉯).
    발화는 호출자(수리 러너·완결 절차) 몫 — stale_process 는 재는 것만 한다."""


def _proc_start_epoch(pid):
    """`ps -p <pid> -o lstart=` 실측 → 기동 시각 epoch. 프로세스 부재면 명시 예외(조항 59)."""
    out = subprocess.run(["ps", "-p", str(pid), "-o", "lstart="],
                         capture_output=True, text=True,
                         env=dict(os.environ, LC_ALL="C")).stdout.strip()
    if not out:
        raise RuntimeError(
            "프로세스 기동 시각을 못 쟀다 — pid %s 부재(ps 빈 출력 · 조항 59)" % pid)
    return int(time.mktime(time.strptime(out, "%a %b %d %H:%M:%S %Y")))


def _last_repair_epoch(paths, repo):
    """`git log -1 --format='%H %ct' -- <paths>` — 감시 파일들의 최종 수정 커밋 (sha16, epoch).
    커밋 이력에 없는 경로면 조용한 0 이 아니라 명시 예외다(조항 59)."""
    r = subprocess.run(
        ["git", "-C", repo, "log", "-1", "--format=%H %ct", "--"] + list(paths),
        capture_output=True, text=True)
    out = r.stdout.strip()
    if r.returncode != 0 or not out:
        raise RuntimeError(
            "수리 커밋 시각을 못 쟀다 — %s (git 이력 없음/오류: %s · 조항 59)"
            % (list(paths), r.stderr.strip() or "빈 출력"))
    sha, ct = out.split()
    return sha[:16], int(ct)


def stale_process(pidfile, paths, repo=REPO):
    """부칙 5 (티처 #143) — 실행 중 프로세스가 감시 파일들의 수리 커밋 «이전» 기동인지 실측 대조.

    pidfile: pid 파일 경로(정수 pid 직접도 허용) · paths: 그 프로세스가 적재·실행하는 파일 목록
    (repo 상대 경로) · repo: git 저장소 뿌리(기본: 이 파일의 저장소).

    반환(게재용 실측 스탬프 — 참/거짓 + 두 시각, 등록 상수 게재 금지 · 부칙 4 ㉯ 미러):
      {"낡음": 참/거짓, "pid", "기동 시각"/"기동 epoch", "수리 커밋 시각"/"수리 커밋 epoch",
       "수리 커밋": sha16, "경로", "잰 시각"}

    낡음 == 참 (기동 < 최종 수정 커밋) = «실서빙 미반영 — 재시작 대기물» — 커밋 메시지와 카드에
    등재하라. 반영됐다고 적으면 조항 59 위반. 수리 러너·완결 절차는 참인데 대기물 미등재면
    StaleProcess 로 중단한다(발화는 호출자 몫). 결측(pid 부재·이력 없는 경로)은 조용한 거짓이
    아니라 명시 예외다(조항 59). 재시작 강제 아님 — 재시작은 사용자 몫.
    """
    if isinstance(pidfile, int):
        pid = pidfile
    else:
        with open(pidfile) as f:
            tok = f.read().split()
        if not tok or not tok[0].isdigit():
            raise RuntimeError("pid 파일을 못 읽었다 — %s (내용 비정상 · 조항 59)" % pidfile)
        pid = int(tok[0])
    t_start = _proc_start_epoch(pid)
    sha, t_repair = _last_repair_epoch(paths, repo)

    def _iso(t):
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))

    return {"낡음": t_start < t_repair, "pid": pid,
            "기동 시각": _iso(t_start), "기동 epoch": t_start,
            "수리 커밋 시각": _iso(t_repair), "수리 커밋 epoch": t_repair,
            "수리 커밋": sha, "경로": list(paths),
            "잰 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}


if __name__ == "__main__":
    import json
    import shutil
    import tempfile
    # ── 부칙 4 자기시험 ──
    # ① 참 쪽 — 현 manifest 실측 sha 로 통과해야 한다
    cur = sha16(MANIFEST)
    stamp = assert_epoch(cur)
    print("참 쪽 통과:", json.dumps(stamp, ensure_ascii=False))
    # ② 거짓 쪽 — 틀린 등록값은 예외가 나야 한다
    try:
        assert_epoch("0" * 16)
    except EpochMismatch as e:
        print("거짓 쪽 예외 OK:", e)
    else:
        print("🔴 결함 — 거짓 쪽에서 예외가 안 났다")
        raise SystemExit(1)

    # ── 부칙 5 자기시험 (임시 git 저장소 + 실제 ps 실측 — 모의 없음) ──
    tmp = tempfile.mkdtemp(prefix="bu5_selftest_")
    proc = None
    try:
        def _git(*a):
            r = subprocess.run(
                ["git", "-C", tmp, "-c", "user.name=selftest",
                 "-c", "user.email=selftest@local", "-c", "commit.gpgsign=false"]
                + list(a), capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError("자기시험 git 실패: %s" % r.stderr.strip())
        _git("init", "-q")
        with open(os.path.join(tmp, "watched.txt"), "w") as f:
            f.write("v1\n")
        _git("add", "watched.txt")
        _git("commit", "-q", "-m", "v1")
        time.sleep(1.2)                    # 커밋 «후» 기동 — 초 경계 동률 회피
        proc = subprocess.Popen(["/bin/sleep", "60"])
        pidfile = os.path.join(tmp, "proc.pid")
        with open(pidfile, "w") as f:
            f.write("%d\n" % proc.pid)
        # ③ 거짓 쪽 — 수리 커밋 «후» 기동한 프로세스는 낡지 않았다
        st3 = stale_process(pidfile, ["watched.txt"], repo=tmp)
        print("부칙 5 거짓 쪽(신판 실행):", json.dumps(st3, ensure_ascii=False))
        if st3["낡음"]:
            print("🔴 결함 — 커밋 후 기동인데 낡음=참")
            raise SystemExit(1)
        time.sleep(1.2)                    # 기동 «후» 수리 커밋 — 참 쪽 실물
        with open(os.path.join(tmp, "watched.txt"), "w") as f:
            f.write("v2 수리\n")
        _git("add", "watched.txt")
        _git("commit", "-q", "-m", "v2 수리")
        # ④ 참 쪽 — 같은 프로세스가 이제 수리 커밋 «이전» 기동 = 구판 실행 중
        st4 = stale_process(pidfile, ["watched.txt"], repo=tmp)
        print("부칙 5 참 쪽(구판 실행):", json.dumps(st4, ensure_ascii=False))
        if not st4["낡음"]:
            print("🔴 결함 — 기동 후 수리 커밋인데 낡음=거짓")
            raise SystemExit(1)
    finally:
        if proc is not None:
            proc.terminate()
        shutil.rmtree(tmp, ignore_errors=True)
    # ⑤ 본 저장소 스모크 — 지금 뜬 이 파이썬(자기 pid)은 epoch_guard 최종 커밋 «후» 기동이다
    st5 = stale_process(os.getpid(), ["pretrain/epoch_guard.py"])
    print("본 저장소 스모크(자기 pid):", json.dumps(st5, ensure_ascii=False))
    if st5["낡음"]:
        print("🔴 결함 — 지금 프로세스가 낡음=참")
        raise SystemExit(1)
    print("부칙 4·5 자기시험 통과 (참/거짓 양쪽)")
