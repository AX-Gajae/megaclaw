"""전향 수집 패스 — **루프 안에서** 돌리고, 성장을 재서 판정한다 (노트 888).

**왜 크론이 아닌가.** 2026-08-09 에 실측한 것 하나가 이 모듈의 이유 전부다.
주 1회 크론 `forward_run.sh` 가 두 번 돌아(7/27 · 8/03) 두 번 다 죽어 있었고
(``FileNotFoundError: 'bq'``), 그 사실을 **2주 동안 아무도 몰랐다**. 고쳐서 다시
돌렸더니 이번엔 이렇게 끝났다::

    [2] 신규 발굴: Drive문서 1건 → ROPU2616
    [2]   ROPU2616 실패: 400 'Your credit balance is too low'
    [2] 뱅크 투입: 0건
    ===== 종료 코드 0 =====

**종료 코드가 0 이다.** 크론 로그만 보면 성공이고, 다음 주까지 아무도 모른다.
사용자 지적이 정확히 이것이었다 — *"코드로 크론 돌려두면 테스트 주기도 길고
틀렸을 때 대처가 안 된다."* 그래서 수집을 **사이클의 스텝 ⓪** 으로 옮긴다.
루프 안에 있으면 실패가 그 자리에서 보이고, 코드를 그 자리에서 고친다.

**그래서 이 모듈의 규칙은 하나다 — 종료 코드를 안 믿는다.**

수집기마다 **산출물을 실행 전후로 재고**, 그 차이로 판정한다. 이 저장소가
같은 병을 이미 네 번 앓았다: 노트 359(조용한 무작동) · 636('파이프라인이
켜졌다'가 20분 단일 소급 적재였다) · 673(같은 PDF 를 두 번 읽고 교차검증이라
했다) · 887(위약 Δ=0 이 통계가 아니라 항등식이었다). 전부 *"돌았다고 믿었는데
아니었다"* 이고, 전부 **산출물을 안 보고 신호를 봤기 때문**이다.

판정 넷::

    성장 +N   산출물이 늘었다 — 유일하게 좋은 결과
    무성장     돌았는데 안 늘었다 — 원천이 안 늘었을 수도, 우리가 막혔을 수도
    🔴 실패    종료 코드가 0 이 아니다
    🔴 조용한실패  종료 코드는 0 인데 출력에 실패 서명이 있다  ← 크론이 못 잡는 것

``무성장`` 은 실패가 아니지만 **연속 무성장은 실패다**. 장부에 연속 횟수를
적어 두어 다음 사이클이 판단할 수 있게 한다 — `popup_visitor_daily` 가
2026-08-05 이후 48행에서 안 늘고 있는 것이 그 예다(노트 673).

쓰는 법::

    python3 -m ingest.collect              # 전부
    python3 -m ingest.collect --only yt_poll
    python3 -m ingest.collect --report     # 장부 요약(수집 안 함)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "data/state/collect_log.jsonl"       # append-only · 단일 필자 = 이 모듈

#: 종료 코드 0 인데 실제로는 실패한 것을 잡는 서명. **이 목록은 겪은 만큼만
#: 자란다** — 새 조용한실패를 만나면 여기 추가하고 노트에 적는다.
#: 정규식이 아니라 부분 문자열이다(노트 674·677·693·697 의 부분문자열 오탐
#: 계열을 피하려고 일부러 넉넉한 문구를 쓴다).
QUIET_FAIL = (
    "credit balance is too low",
    "invalid_request_error",
    "Error code: 4",
    "Error code: 5",
    "FileNotFoundError",
    "Traceback (most recent call last)",
    "rate limit",
    "429",
    "인증 실패",
    "키 없음",
)


def _lines(p: Path) -> int:
    """jsonl 행 수. 없으면 0."""
    if not p.exists():
        return 0
    return sum(1 for _ in p.open(encoding="utf-8"))


def _files(d: Path, pat: str = "*.json", skip: tuple = ()) -> int:
    """디렉터리의 파일 수. `skip` 에 들어간 접두는 안 센다(백필·동결물 제외)."""
    if not d.is_dir():
        return 0
    return sum(1 for f in d.glob(pat) if not f.name.startswith(skip))


# 🔴 **파일 수는 자가 아니다**(2026-08-09 · 이 모듈 첫 실행에서 자가 적발).
# 초판은 `yt_poll` 과 `kobis` 를 `_files()` 로 쟀는데 **둘 다 하루에 한 파일을
# 덮어쓴다** --- `YYYY-MM-DD.json`. 그래서 kobis 가 111행을 새로 받아 오고
# yt_poll 이 242초를 돌아 오늘 파일을 갱신했는데 자는 **둘 다 "무성장"** 이라
# 읽었다. *산출물을 보라*고 써 놓고 **파일 이름을 봤다.**
#
# 이 저장소가 앓은 병(359 · 636 · 673 · 887)과 같은 계열이고, 그 병을 막으려고
# 만든 모듈이 첫 실행에서 같은 병에 걸렸다. 그러므로 **관측 수를 센다** ---
# 파일이 몇 개인지가 아니라 그 안에 관측이 몇 개인지.
def _obs(d: Path, count, skip: tuple = ()) -> int:
    """디렉터리 안 **관측 수**의 합. `count(파일내용) -> int` 를 받는다.

    깨진 파일은 0 으로 세고 조용히 넘어가지 않는다 --- 세다가 예외가 나면
    그 파일은 0 이지만, 총합이 줄어드는 것으로 드러난다(append-only 원천에서
    총합이 줄면 그 자체가 신호다)."""
    if not d.is_dir():
        return 0
    n = 0
    for f in sorted(d.glob("*.json")):
        if f.name.startswith(skip):
            continue
        try:
            n += count(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return n


def _yt_obs(d: dict) -> int:
    """(채널 × 영상) 관측 수. 하루 한 파일이라 파일 수로는 안 보인다."""
    return sum(len(t.get("영상") or []) for t in (d.get("대상") or []))


def _kobis_obs(d: dict) -> int:
    """일별 박스오피스 행 수. 표 이름이 판마다 달라서 리스트를 찾아 센다."""
    if isinstance(d, dict):
        for v in d.values():
            if isinstance(v, list):
                return len(v)
    return 0


# ─────────────────────────────────────────────────────────────────────────
# 🔴 노트 952 — **수집기 명세를 코드에서 등기부로 옮겼다.**
#
# 왜. 초판은 이 자리에 파이썬 리스트가 있었고 원천이 **셋**이었다(popupsnap ·
# yt_poll · kobis). 그런데 노트 941 이 실제로 받아 온 것 둘(위키 일별 · Steam
# 리뷰)은 **이 목록 밖**이라 상시 수집에 한 번도 안 들어갔다 — 🔴 **받아 놓고
# 안 도는 원천**이 있었다는 뜻이고, 아무도 20사이클 동안 몰랐다.
#
# 진짜 원인은 「누가 빼먹었다」가 아니라 **새 원천을 붙이는 일이 「파이썬을
# 고친다」였다**는 것이다. 그래서 등기부로 내린다 — 이제 새 원천 붙이기는
# **`data/lab/sources.json` 에 항목 하나**다. 다음 사이클이 실제로 붙이게.
#
# 덤으로 **라이선스가 원천 옆에 산다.** 상업 IP 모델이라 출처를 못 대는 데이터는
# 나중에 전부 버려야 하는데, 라이선스가 코드 주석에만 있으면 버릴 때 못 찾는다.
#
# **`측정` 은 여전히 산출물을 직접 센다** — 프로세스가 뭘 출력했는지가 아니라
# 디스크에 뭐가 남았는지다. 그게 이 모듈의 전부다.
# ─────────────────────────────────────────────────────────────────────────
REGISTRY = ROOT / "data/lab/sources.json"


class 못읽었다(Exception):
    """🔴 「0 행」과 「못 읽었다」를 가르는 예외 (조항 59 · 952 신설)."""


def _gz_lines(d: Path, recursive: bool = False) -> int:
    """디렉터리 안 `*.jsonl.gz` 의 줄 수 합.

    🔴 **952 자가 적발 --- 초판이 바로 이 모듈이 막으려는 병에 걸렸다.**

    초판은 이렇게 썼다::

        try:
            ... 줄을 센다 ...
        except Exception:
            pass          # 🔴 깨진 파일이 조용히 **0 행**이 된다

    실측(2026-08-12): 등기부가 새로 들인 `wiki_daily` 가 처음 돌았을 때 장부가
    **「무성장 · 델타 -140」**을 찍었다. 자료가 140행 사라진 것처럼 보였다.
    **사라지지 않았다.** 산수가 정확히 맞는다::

        지금 읽히는 합계                       812
        측정 순간 못 읽힌 파일 4개의 행 수       142   (게임80·도서28·만화3·모바일31)
        812 - 142 =                          670   ← `after` 에 찍힌 값 그대로
        커밋된 before 810 - 670 =            140   ← 장부의 「손실」

    🔴 **원천은 오히려 810 → 812 로 늘었다.** 「손실 140」은 **자가 만든 유령**이다.
    깨진 파일 넷을 **0 으로 세고 아무 말도 안 했기 때문**이다.

    이 저장소가 네 번 앓은 그 병이고(359·636·673·887), 이 모듈의 독스트링이
    *「산출물을 안 보고 신호를 봤기 때문」*이라 적어 둔 바로 그것이다.
    🔴 **그 병을 막으려고 만든 모듈에 952 가 같은 병을 새로 넣었다.**

    그래서 **삼키지 않는다.** 못 읽으면 `못읽었다` 를 던지고, 부르는 쪽이
    **「모른다」**로 판정한다 --- 「0」도 「줄었다」도 아니다.
    """
    import gzip
    if not d.is_dir():
        return 0
    n = 0
    bad = []
    # 🔴 1017 --- recursive 는 담론 수확물({원천}/{날짜}.jsonl.gz 켜켜이)용.
    #    한 단 평평한 기존 원천들의 자는 한 글자도 안 변한다(기본값 False).
    for f in sorted(d.rglob("*.jsonl.gz") if recursive else d.glob("*.jsonl.gz")):
        try:
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                n += sum(1 for _ in fh)
        except Exception as e:                                    # noqa: BLE001
            bad.append("%s(%s)" % (f.name, type(e).__name__))
    if bad:
        # 🔴 **왜 「부분 합」을 안 내놓나**: 그러면 「줄었다」와 구별이 안 된다.
        raise 못읽었다("못 읽은 파일 %d개: %s" % (len(bad), ", ".join(bad[:6])))
    return n


def _dir_bytes(d: Path, pat: str) -> int:
    if not d.is_dir():
        return 0
    return sum(f.stat().st_size for f in d.glob(pat) if f.is_file())


#: 측정꼴 이름 → 함수. 🔴 **JSON 이 코드를 못 부르게 한다** — 꼴은 여기 있는 것만
#: 쓸 수 있고, 모르는 꼴은 조용히 0 을 내지 않고 **터진다**(조항 59).
_COUNTERS = {"yt": _yt_obs, "kobis": _kobis_obs}


def _measure_fn(spec: dict | None):
    if not spec:
        return lambda: 0
    k = spec.get("꼴")
    if k == "jsonl행":
        p = ROOT / spec["경로"]
        return lambda: _lines(p)
    if k == "jsonl_gz행합":
        d = ROOT / spec["디렉터리"]
        return lambda: _gz_lines(d)
    if k == "jsonl_gz행합_재귀":
        # 🔴 1017 신설 --- 하위 디렉터리까지 센다. `디렉터리` 가 절대경로면
        # pathlib 규칙상 `ROOT /` 가 무시되므로 저장소 밖(wm_harvest)도 잴 수 있다.
        d = ROOT / spec["디렉터리"]
        return lambda: _gz_lines(d, recursive=True)
    if k == "디렉터리관측":
        d = ROOT / spec["디렉터리"]
        fn = _COUNTERS[spec["세는이"]]
        skip = tuple(spec.get("건너뛸접두") or ())
        return lambda: _obs(d, fn, skip=skip)
    if k == "디렉터리바이트":
        d = ROOT / spec["디렉터리"]
        pat = spec.get("유리", "*")
        return lambda: _dir_bytes(d, pat)
    raise KeyError("모르는 측정꼴: %r (등기부 `측정꼴` 절에 없다)" % (k,))


def _last_success(name: str):
    """장부에서 이 원천이 **마지막으로 성장한** 시각. 없으면 None."""
    if not LOG.exists():
        return None
    for ln in reversed(LOG.read_text(encoding="utf-8").splitlines()):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("이름") == name and r.get("판정") == "성장":
            try:
                return dt.datetime.fromisoformat(r["시각(UTC)"])
            except Exception:
                return None
    return None


def _last_run(name: str):
    """마지막으로 **돌린** 시각(성장이든 아니든). 최소간격을 재는 자."""
    if not LOG.exists():
        return None
    for ln in reversed(LOG.read_text(encoding="utf-8").splitlines()):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("이름") == name and r.get("판정") != "건너뜀":
            try:
                return dt.datetime.fromisoformat(r["시각(UTC)"])
            except Exception:
                return None
    return None


def load_registry(path: Path | None = None) -> list:
    """등기부를 읽어 수집기 명세로 바꾼다. 🔴 `켬:false` 는 아예 안 싣는다."""
    p = path or REGISTRY
    if not p.exists():
        raise FileNotFoundError(
            "등기부가 없다: %s — 🔴 「원천이 없다」가 아니라 「등기부를 못 찾았다」다" % p)
    reg = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for s in reg.get("원천", []):
        if not s.get("켬"):
            continue
        if not s.get("모듈"):
            continue
        gap = s.get("최소간격초")

        def _skip(name=s["이름"], gap=gap):
            if not gap:
                return False
            last = _last_run(name)
            if last is None:
                return False
            age = (dt.datetime.now(dt.timezone.utc) - last).total_seconds()
            return age < gap

        out.append({
            "이름": s["이름"],
            "cmd": [sys.executable, "-m", s["모듈"]],
            "측정": _measure_fn(s.get("측정")),
            "단위": s.get("단위", "관측"),
            "무엇": s.get("무엇", ""),
            "제한": s.get("제한초", 900),
            "정체사유": s.get("정체사유"),
            "건너뜀": _skip,
            "건너뜀사유": "최소간격 %s초가 아직 안 지났다(등기부)" % gap,
            "라이선스": s.get("라이선스", "🔴 모른다"),
        })
    return out


#: 🔴 모듈 적재 시점에 등기부를 읽는다. 없으면 **여기서 터진다** — 조용히 빈
#: 목록으로 도는 것이 이 모듈이 막으려는 병 그 자체다(노트 359 계열).
COLLECTORS = load_registry()


def _run_one(c: dict, timeout: int | None = None) -> dict:
    # **시간초과는 실패가 아니다**(2026-08-09 자가 적발). 초판은 제한이 900초
    # 한 값이었는데 `yt_poll` 이 242초에서 **10분 넘게로 늘었다**(채널 17개 ×
    # 영상마다 조회수 읽기 --- 원격이 느려지면 그대로 늘어난다). 900 에 걸리면
    # `code=-9` 라 `🔴 실패` 로 찍히는데, 그건 **느린 것을 고장이라 부르는 것**이고
    # 진짜 고장과 섞이면 장부가 못 쓰게 된다. 판정을 따로 세우고 제한도 수집기별로 둔다.
    timeout = timeout or int(c.get("제한", 900))
    # 🔴 952 --- 재는 것 자체가 실패할 수 있다. 「못 쟀다」를 「0」으로 안 읽는다
    try:
        before = c["측정"]()
    except 못읽었다 as e:
        return {"이름": c["이름"], "판정": "🔴 모른다(측정불가)", "델타": 0,
                "before": None, "after": None, "단위": c["단위"], "종료코드": 0,
                "서명": [], "초": 0.0, "출력끝": "",
                "사유": "돌리기 **전** 측정이 실패했다: %s" % e}
    # **안 돌려도 되는 것은 안 돌린다.** 판정은 `건너뜀` --- 무성장과 섞지 않는다
    # (무성장은 '돌렸는데 안 늘었다' 이고 이쪽은 '돌릴 필요가 없었다' 다).
    skip = c.get("건너뜀")
    if skip is not None and skip():
        return {"이름": c["이름"], "판정": "건너뜀", "델타": 0,
                "before": before, "after": before, "단위": c["단위"],
                "종료코드": 0, "서명": [], "초": 0.0, "출력끝": "",
                "사유": c.get("건너뜀사유", "")}
    t0 = dt.datetime.now()
    timed_out = False
    try:
        r = subprocess.run(c["cmd"], cwd=ROOT, capture_output=True,
                           text=True, timeout=timeout)
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        timed_out = True
        code = -9
        out = (e.stdout or b"").decode("utf-8", "ignore") if isinstance(e.stdout, bytes) \
            else (e.stdout or "")
        out += f"\n시간초과 {timeout}s"
    # 🔴 952 --- 뒤 측정도 실패할 수 있다
    try:
        after = c["측정"]()
    except 못읽었다 as e:
        return {"이름": c["이름"], "판정": "🔴 모른다(측정불가)", "델타": 0,
                "before": before, "after": None, "단위": c["단위"],
                "종료코드": code, "서명": [],
                "초": round((dt.datetime.now() - t0).total_seconds(), 1),
                "출력끝": out[-700:],
                "사유": ("돌린 **뒤** 측정이 실패했다: %s --- 🔴 **「줄었다」가 아니다.** "
                        "수집기가 아직 파일을 쓰는 중일 수 있다" % e)}
    delta = after - before

    hits = [s for s in QUIET_FAIL if s in out]
    if timed_out:
        # 잘린 사이에 산출물이 늘었으면 부분 성장이다 --- 그것도 적는다
        판정 = "⏱ 시간초과" + (f"(부분 +{delta})" if delta > 0 else "")
    elif code != 0:
        판정 = "🔴 실패"
    elif hits:
        판정 = "🔴 조용한실패"          # ← 크론이 구조적으로 못 잡는 자리
    elif delta > 0:
        판정 = "성장"
    elif delta < 0:
        # 🔴 **952 신설 --- 이 갈래가 없었다.**
        #
        # 초판의 판정은 넷(성장·무성장·실패·조용한실패)이고 `delta < 0` 은
        # **`else` 로 떨어져 「무성장」**이었다. 즉 **140행을 잃은 원천과 아무것도
        # 안 바뀐 원천이 장부에서 같은 글자**였다.
        #
        # 🔴 더 나쁜 것: 이 모듈의 `_obs()` 독스트링이 이미 이렇게 적어 두었다 ---
        # *「총합이 줄어드는 것으로 드러난다(append-only 원천에서 총합이 줄면 그
        # 자체가 신호다)」*. **신호가 있다고 적어 놓고 그 신호를 읽는 판정이 없었다.**
        # 코드가 자기 주석을 안 지킨 자리다.
        판정 = "🔴 줄었다"
    else:
        판정 = "무성장"

    return {
        "이름": c["이름"], "판정": 판정, "델타": delta,
        "before": before, "after": after, "단위": c["단위"],
        "종료코드": code, "서명": hits,
        "초": round((dt.datetime.now() - t0).total_seconds(), 1),
        # 실패했을 때만 출력을 남긴다 — 성공 로그로 장부를 불리지 않는다
        "출력끝": out[-700:] if 판정.startswith("🔴") else "",
    }


def _streak(name: str, 판정: str) -> int:
    """직전까지 같은 판정이 몇 번 연속인가. **무성장이 몇 번째인지**를 안다."""
    if not LOG.exists():
        return 1
    n = 0
    for ln in reversed(LOG.read_text(encoding="utf-8").splitlines()):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("이름") != name:
            continue
        # 판정 문자열에 `(부분 +3)` 같은 꼬리가 붙을 수 있으므로 **머리로 견준다** ---
        # 안 그러면 같은 부류인데 연속이 끊겨 '3회 연속' 경고가 영영 안 뜬다.
        if (r.get("판정") or "").split("(")[0] != 판정.split("(")[0]:
            break
        n += 1
    return n + 1


def run(only: str | None = None) -> dict:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rows = []
    for c in COLLECTORS:
        if only and c["이름"] != only:
            continue
        r = _run_one(c)
        r["연속"] = _streak(c["이름"], r["판정"])
        if c.get("정체사유"):
            r["정체사유"] = c["정체사유"]
        r["시각(UTC)"] = stamp
        rows.append(r)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 사람이 읽는 표. 🔴 는 눈에 띄게.
    print(f"수집 패스 {stamp}")
    for r in rows:
        mark = "%+d" % r["델타"] if r["델타"] else "  0"
        line = ("  %-11s %-12s %s %-6s (%s→%s) %4.1fs"
                % (r["이름"], r["판정"], mark, r["단위"],
                   r["before"], r["after"], r["초"]))
        if r["판정"] == "무성장" and r["연속"] >= 3:
            line += f"  ⚠ {r['연속']}회 연속 무성장"
        print(line)
        if r["판정"] == "무성장" and r["연속"] >= 3 and r.get("정체사유"):
            print("      아는 사유:", r["정체사유"])
        if r["판정"] == "건너뜀" and r.get("사유"):
            print("      사유:", r["사유"])
        if r["판정"].startswith("🔴"):
            if r["서명"]:
                print("      서명:", ", ".join(r["서명"]))
            for l in (r["출력끝"] or "").strip().splitlines()[-6:]:
                print("      |", l[:150])

    bad = [r for r in rows if r["판정"].startswith("🔴")]
    slow = [r for r in rows if r["판정"].startswith("⏱")]
    stale = [r for r in rows if r["판정"] == "무성장" and r["연속"] >= 3]
    print(f"── 성장 {sum(1 for r in rows if r['판정']=='성장')}"
          f" · 무성장 {sum(1 for r in rows if r['판정']=='무성장')}"
          f" · 건너뜀 {sum(1 for r in rows if r['판정']=='건너뜀')}"
          f" · 시간초과 {len(slow)} · 실패 {len(bad)}")
    if slow:
        print("⏱ 제한 안에 못 끝냄(고장 아님 — 제한을 올리거나 따로 돌린다):",
              ", ".join("%s(%ds)" % (r["이름"], r["초"]) for r in slow))
    if bad:
        print("🔴 이번 사이클에서 고칠 것:", ", ".join(r["이름"] for r in bad))
    # **사유를 아는 정체는 할 일이 아니다.** 둘을 갈라 찍는다 --- 안 그러면 매
    # 사이클 같은 ⚠ 가 떠서(popupsnap 은 원천이 동결이라 영영 안 는다) 보고가
    # 늑대소년이 되고, 그때 **진짜 정체를 놓친다**. 이 모듈이 막으려는 병과 같다.
    known = [r for r in stale if r.get("정체사유")]
    unknown = [r for r in stale if not r.get("정체사유")]
    if known:
        print("· 정체(사유 있음 · 조치 불필요):",
              ", ".join("%s(%d)" % (r["이름"], r["연속"]) for r in known))
    if unknown:
        print("⚠ 사유 모르는 3회+ 연속 무성장(원천이 멈췄나 우리가 막혔나 갈라야 한다):",
              ", ".join("%s(%d)" % (r["이름"], r["연속"]) for r in unknown))
    return {"행": rows, "실패": len(bad), "정체": len(stale),
            "사유없는정체": len(unknown)}


def report(n: int = 40) -> None:
    """장부 요약 — 수집은 안 한다."""
    if not LOG.exists():
        print("장부 없음:", LOG)
        return
    rs = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"수집 장부 {len(rs)}건 · {LOG}")
    for r in rs[-n:]:
        print("  %s %-11s %-12s %+d %s"
              % (r.get("시각(UTC)", "")[:16], r.get("이름"), r.get("판정"),
                 r.get("델타", 0), r.get("단위", "")))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report()
    else:
        s = run(a.only)
        # 🔴 가 있으면 종료 코드로도 알린다 — 다만 **판정의 근거는 장부**다.
        sys.exit(1 if s["실패"] else 0)
