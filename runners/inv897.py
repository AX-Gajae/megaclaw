"""노트 897 · 0단계 — **이미 있는 조각을 센다.** 짓기 전에 실행해 본다(조항 59).

각 조각을 실제로 돌리고 ① 도는가 ② 입출력 ③ 채점물 ④ **서로 닿는가** 를 적는다.
종료 코드 0 을 성공으로 읽지 않는다 --- 산출물의 **내용**을 본다.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()
OUT = ROOT / "runners/out897_inventory.json"

#: 🔴 **초판은 1800초였다.** `state.shared_encoder` 가 그 30분을 통째로 태우고
#: 아무것도 안 냈다 --- 그래서 나머지 여섯을 잴 시간이 안 남았다. `docs/아키텍처.md`
#: §4 가 *"팔 하나가 10분을 넘으면 사다리를 줄여라"* 라고 적었으므로 **상한을 300초로
#: 내리고 「300초 안에 안 끝난다」를 결과로 적는다**(조항 59 — 시간초과는 '안 돈다'가
#: 아니라 **'이 상한 안에 안 끝난다'** 이고 셋째 범주다).
CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 300
PIECES = [
    ("state.fieldmodel", ["horizons"], CAP),
    ("state.shared_encoder", [], CAP),
    ("state.foundation", [], CAP),
    ("state.masked_encoder", [], CAP),
    ("state.fewshot", [], CAP),
    ("state.transfer_eval", [], CAP),
    ("state.encoder", [], CAP),
]


def stamp() -> dict:
    h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                       capture_output=True, text=True).stdout.strip()
    return {"git HEAD": h, "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "코드 sha(이 파일)": hashlib.sha256(ME.read_bytes()).hexdigest()[:16]}


def run(mod: str, args: list[str], timeout: int) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-m", mod, *args], cwd=ROOT,
                           capture_output=True, text=True, timeout=timeout)
        out, err, rc = p.stdout, p.stderr, p.returncode
        to = False
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = (e.stderr or b"").decode("utf8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        rc, to = None, True
    dt = round(time.time() - t0, 1)
    # 🔴 종료 코드가 아니라 **내용**으로 판정한다
    parsed = None
    try:
        parsed = json.loads(out)
    except Exception:
        pass
    return {"모듈": mod, "인자": args, "초": dt, "종료코드": rc, "시간초과": to,
            "stdout 바이트": len(out), "stderr 바이트": len(err),
            "stdout 앞 400": out[:400],
            "stderr 끝 400": err[-400:],
            "JSON 파싱됨": parsed is not None,
            "🔴 내용 판정": ("돈다" if (parsed is not None or len(out) > 40) and not to
                          else ("시간초과" if to else "안 돈다")),
            "산출 키": (sorted(parsed)[:12] if isinstance(parsed, dict) else None)}


def main():
    res = {"stamp": stamp(), "조각": []}
    for mod, args, to in PIECES:
        r = run(mod, args, to)
        res["조각"].append(r)
        print(json.dumps({k: r[k] for k in ("모듈", "초", "종료코드", "🔴 내용 판정")},
                         ensure_ascii=False), flush=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("→", OUT)


if __name__ == "__main__":
    main()
