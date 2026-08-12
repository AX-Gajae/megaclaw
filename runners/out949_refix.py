# -*- coding: utf-8 -*-
"""노트 949 — **고친 두 자리가 실제로 도는가**를 재고, 옛 산출물은 안 건드린다.

🔴 티처 #88 C4 가 지목한 것: 948 은 「이번 변경은 실행 결과를 안 바꾼다」를 `--exempt`
사유로 **적어만 놓고 안 쟀다**. 949 는 고친 두 파일을 **실제로 돌려** 그 자리가
살아 있음을 보인다.

⚠ **옛 산출물을 덮어쓰지 않는다.** `gate940_wiring.py` 는 `runners/out940_gate.json`
을 쓰므로, 돌린 뒤 그 파일을 `git checkout` 으로 되돌리고 **결과는 이 파일에** 담는다.

쓰기::

    python3 -m runners.out949_refix
"""
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "runners/out949_refix.json"
G940 = "runners/out940_gate.json"


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    t0 = time.time()
    # ── ① gate940_wiring.py --- 통째로 돌린다(옛 산출물은 뒤에 되돌린다)
    r = subprocess.run([sys.executable, str(ROOT / "runners/gate940_wiring.py")],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=1800)
    got = json.loads((ROOT / G940).read_text(encoding="utf-8"))
    subprocess.run(["git", "-C", str(ROOT), "checkout", "--", G940],  # 날것허용: 🔴 옛
                   capture_output=True)                              # 산출물 되돌리기
    g = {"종료": r.returncode,
         "🔴 절별 판정": {k: v["통과"] for k, v in got.items()
                    if isinstance(v, dict) and "통과" in v},
         "🔴 고친 줄이 낸 것(작업 트리 목록)": got.get("5 작업 트리(따로)", {}).get("목록"),
         "⚠ 옛 산출물": "다시 돌리면 `%s` 를 덮어쓰므로 **되돌렸다**(git checkout). "
                  "결과는 이 파일에만 남긴다" % G940,
         "통과": r.returncode == 0}
    # ── ② ratio940_run.py --- 고친 줄이 든 `part0()` 만 부른다(전체는 판 계산이라 안 돈다)
    try:
        from runners import ratio940_run as rr
        p0 = rr.part0()
        rres = {"🔴 part0() 이 돌았나": True,
                "🔴 그 커밋에 측정 러너가 들어 있었나(= 고친 줄의 값)":
                    p0.get("🔴 그 커밋에 측정 러너가 들어 있었나"),
                "사전등록 sha256 대조": p0.get("🔴 같은가"),
                "⚠ 왜 전체를 안 돌리나": "이 러너는 **판 계산**이다. 949 는 [판정] 레인이지만 "
                                "판 ρ 를 안 건드리기로 사전등록했다(P11) --- 전체를 "
                                "돌리면 판 산출물을 덮어쓴다. 🔴 **고친 줄이 든 절만** 부른다",
                "통과": True}
    except Exception as e:                                          # noqa: BLE001
        rres = {"🔴 못 돌렸다": "%s: %s" % (type(e).__name__, e), "통과": False}
    res = {"무엇": "949 — 고친 두 자리가 실제로 도나(티처 #88 C4: 「안 바꾼다」를 안 쟀다)",
           "① runners/gate940_wiring.py (통째로)": g,
           "② runners/ratio940_run.py (고친 줄이 든 `part0()` 만)": rres,
           "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "초": round(time.time() - t0, 1),
           "통과": g["통과"] and rres["통과"]}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("산출물: %s · 통과 %s" % (OUT, res["통과"]))


if __name__ == "__main__":
    main()
