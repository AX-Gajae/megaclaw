# -*- coding: utf-8 -*-
# popup_visitor_daily 일일 스냅샷(노트 871·872 · T7 · 노트 636 '채굴보다 배선' 이행)
# 읽기: `bq head`(tabledata.list) + `bq show`(tables.get numRows 대조) — 잡 생성 없음(읽기 전용).
# 쓰기: data/state/popup_visitor_daily.jsonl 멱등 append — 키는 **전행 해시**(872: (id, updated_at)
#       키는 제자리 수정에 장님이었다 — 48행 전건 created==updated 실측) + 장부(_log.jsonl).
# 성장물 선언: 두 파일 다 append-only · 단일 필자 = 이 모듈.
# 사용: python3 -m ingest.popupsnap   (상시 조항: 매 사이클 첫 행동 · 크론 후보)
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

TABLE = "sweetspot-ax:core.popup_visitor_daily"
CAP = 100000
OUT = Path("/Users/ax/world_model/data/state/popup_visitor_daily.jsonl")
LOG = Path("/Users/ax/world_model/data/state/popup_visitor_daily_log.jsonl")


def row_key(r: dict) -> str:
    body = {k: v for k, v in r.items() if k != "_스냅샷(UTC)"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _bq_path() -> str:
    """🔴 노트 952 수리 — `bq` 를 이름으로 부르면 **launchd 아래에서 죽는다**.

    실측(2026-08-12): 1분 주기 상시 데몬의 **매 회차** `popupsnap` 이
    ``FileNotFoundError: 'bq'`` 로 실패했다. launchd 가 주는 PATH 에는
    gcloud SDK 가 없다(로그인 셸의 PATH 가 아니다). 🔴 **데몬이 첫 회차에 이걸
    잡아냈다** --- 하루 한 번 크론이었으면 다음 날까지 아무도 몰랐을 것이고,
    그게 이 저장소가 이미 두 번 앓은 병이다(노트 888 의 `forward_run.sh`).

    그래서 **이름이 아니라 경로로 부른다.** PATH 에 있으면 그걸 쓰고, 없으면
    알려진 설치 자리를 찾아본다. 🔴 못 찾으면 **거짓말하지 않고 그대로 던진다**
    --- 「없다」와 「못 찾았다」를 가르는 것은 부르는 쪽의 일이다(조항 59).
    """
    p = shutil.which("bq")
    if p:
        return p
    for c in ("/Users/ax/google-cloud-sdk/bin/bq",
              str(Path.home() / "google-cloud-sdk/bin/bq"),
              "/opt/homebrew/bin/bq", "/usr/local/bin/bq",
              "/usr/local/google-cloud-sdk/bin/bq"):
        if Path(c).exists():
            return c
    return "bq"          # 못 찾았다 --- 원래대로 던져서 FileNotFoundError 가 보이게 둔다


def _bq_env() -> dict:
    """🔴 노트 952 수리 **둘째 겹** --- 경로만 고쳤더니 **다른 데서 죽었다**.

    사전등록 P12 는 *「원인이 PATH 하나이고 절대경로를 주면 종료 0」* 이라 예측했다.
    🔴 **빗맞혔다.** 절대경로로 부르니 이번엔 이렇게 죽는다(실측 · `env -i PATH=/usr/bin:/bin`)::

        File ".../third_party/urllib3/_base_connection.py", line 10
          bytes, typing.IO[typing.Any], typing.Iterable[bytes | str], str
        TypeError: unsupported operand type(s) for |: 'type' and 'type'

    `bytes | str` 는 **파이썬 3.10 문법**이다. gcloud 가 `/usr/bin/python3`(3.9.6)로
    자신을 돌리면 자기 번들 라이브러리를 못 읽는다. 로그인 셸에서 안 죽던 이유는
    PATH 에 `~/.local/bin` 이 있어서 gcloud 가 거기 **python3.12** 를 집었기 때문이고,
    launchd 의 기본 PATH(`/usr/bin:/bin:/usr/sbin:/sbin`)에는 그게 없다.

    🔴 **이건 새 병이 아니다.** 티처 #53 C4 가 옛 크론 `forward_run.sh` 에 대해
    똑같이 적었다 --- *「`~/.local/bin` 이 PATH 에 없어 gcloud 가 python3.9 를 잡고
    `bq` 가 TypeError」*. **크론에서 고친 것을 launchd 에서 다시 앓았다.**
    그래서 PATH 에 기대지 않고 **`CLOUDSDK_PYTHON` 을 명시**한다.

    🔴 **그리고 셋째 겹이 또 있었다.** `CLOUDSDK_PYTHON` 을 세웠더니 이번엔::

        BigQuery error in show operation: 'gcloud' not found but is required
        for authentication.

    `bq` 는 인증을 **`gcloud` 를 불러서** 한다 --- 그래서 `bq` 의 절대경로를 아는
    것만으로는 모자라고 **SDK 의 bin 디렉터리가 PATH 에 있어야** 한다.

    🔴 **그래서 「PATH 하나」였던 예측(P12)은 세 번 틀렸다.** 실제 겹은 넷이다:
    ① `bq` 를 못 찾는다 ② gcloud 가 3.9 를 잡아 `TypeError` ③ 인증하려고 `gcloud`
    를 찾는데 PATH 에 없다 ④ 자격증명 환경변수. **하나를 고치면 다음이 나왔다** ---
    이것이 「종료 코드를 안 믿는다」를 넘어 **「한 겹을 고쳤다고 고친 게 아니다」**의 실례다.
    """
    env = dict(os.environ)
    if not env.get("CLOUDSDK_PYTHON"):
        for c in ("/Users/ax/.local/bin/python3.12",
                  "/Users/ax/.local/bin/python3.10",
                  "/opt/homebrew/bin/python3.12",
                  "/opt/homebrew/bin/python3.11",
                  "/usr/local/bin/python3.12"):
            if Path(c).exists():
                env["CLOUDSDK_PYTHON"] = c
                break
        # 🔴 못 찾으면 **안 세운다.** 억지로 3.9 를 넣으면 위의 TypeError 로 돌아간다.
    # 🔴 SDK bin 을 PATH 앞에 붙인다 --- `bq` 가 인증할 때 `gcloud` 를 찾는다
    bq = _bq_path()
    if bq != "bq":
        d = str(Path(bq).parent)
        parts = env.get("PATH", "").split(":")
        if d not in parts:
            env["PATH"] = d + ":" + env.get("PATH", "")
    return env


def _bq(args, timeout=120):
    r = subprocess.run([_bq_path()] + args, capture_output=True, text=True,
                       timeout=timeout, env=_bq_env())
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return json.loads(r.stdout)


def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        rows = _bq(["head", "-n", str(CAP), "--format=json", TABLE])
        meta = _bq(["show", "--format=json", TABLE])
        num_rows = int(meta.get("numRows", -1))
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError,
            FileNotFoundError, OSError, ValueError) as e:
        entry = {"시각(UTC)": now, "실패": f"{type(e).__name__}: {str(e)[:180]}"}
        with open(LOG, "a") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(json.dumps(entry, ensure_ascii=False), flush=True)
        return
    warn = []
    if len(rows) >= CAP:
        warn.append(f"상한 {CAP} 도달 — 절단 위험")
    if num_rows >= 0 and num_rows != len(rows):
        warn.append(f"numRows {num_rows} ≠ head {len(rows)}")
    seen = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            seen.add(row_key(json.loads(line)))
    new = [r for r in rows if row_key(r) not in seen]
    with open(OUT, "a") as fh:
        for r in new:
            fh.write(json.dumps({**r, "_스냅샷(UTC)": now}, ensure_ascii=False) + "\n")
    entry = {"시각(UTC)": now, "전체 행": len(rows), "신규 행": len(new),
             "누적 로컬": len(seen) + len(new), "키": "전행해시(872)"}
    if warn:
        entry["경고"] = warn
    with open(LOG, "a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
