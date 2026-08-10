# -*- coding: utf-8 -*-
"""노트 900 자가 적발 — **내 사전등록이 죽은 숫자를 인용했다.**

`docs/prereg_900_levers.md` §1 이 판 정본으로 **은퇴한 「서수 순위 시대 값」**
(`runners/out112_board.json` 의 평균)을 적었다. 노트 898(커밋 `39afa03e6`)이
*"판과 자가 다른 스피어만을 쓰고 있었다. 판을 자에 맞췄다"* 로 갈아 끼웠고,
그때 **정정**된 오늘의 정본은 **0.47034** 다.
저장소 인계 카드 본문(83~86줄)은 옳고, **메모리 인덱스 한 줄이 옛 값**이다.

**판정은 안 바뀐다** --- 짝 Δ 는 같은 실행 안에서 같은 자료로 뺀 값이라 판 수준값과
무관하다. 바뀌는 것은 「팔 A 가 정본을 재현했나」를 어느 수와 견주느냐 하나다.

여기서는 **적합을 한 번도 안 하고** 산출물 셋을 읽어서 대조만 한다(손 전사 금지):
    runners/out900_levers.json   이번 팔 A (12씨앗)
    runners/out898_board.json    노트 898 의 팔 A(서수 · 옛) / 팔 B(동률 · 새 정본)
    runners/out112_board.json    #112 동결 산출물(= 898 의 팔 A)

산출물: `runners/out900_ruler.json`
"""
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()
OUT = ROOT / "runners/out900_ruler.json"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    lv = json.loads((ROOT / "runners/out900_levers.json").read_text("utf-8"))
    b8 = json.loads((ROOT / "runners/out898_board.json").read_text("utf-8"))
    b1 = json.loads((ROOT / "runners/out112_board.json").read_text("utf-8"))

    mine = lv["판 수준(팔별)"]["A_common"]["씨앗별 판(전정밀)"]
    old = b8["팔"]["A(서수 · 현행 챔피언)"]
    new = b8["팔"]["B(동률 평균)"]
    frozen = b1["씨앗별 판(전정밀)"]

    def cmp(tag, ref):
        d = [float(a) - float(b) for a, b in zip(mine, ref["씨앗별(전정밀)"]
                                                 if "씨앗별(전정밀)" in ref else ref)]
        return {"평균(그쪽 · 딱지는 이 항목 이름에 있다)": float(np.mean(ref["씨앗별(전정밀)"]
                                       if "씨앗별(전정밀)" in ref else ref)),
                "평균 차": float(np.mean(mine)) - float(np.mean(
                    ref["씨앗별(전정밀)"] if "씨앗별(전정밀)" in ref else ref)),
                "씨앗별 차": d,
                "최대 |차|": float(np.max(np.abs(d))),
                "부동소수 완전 일치(전 씨앗)": all(x == 0.0 for x in d),
                "1 ULP 안(전 씨앗)": all(abs(x) <= 4 * np.spacing(0.47) for x in d)}

    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        head = "안 잡힘"

    res = {
        "노트": 900,
        "무엇": "🔴 자가 적발 — 사전등록 §1 이 판 정본으로 **은퇴**한 시대 값을 인용했다",
        "언제 알았나": "측정을 끝내고 팔 A 를 정본과 대조하는 자리에서",
        "배선 스탬프": {
            "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git HEAD": head,
            "🔴 코드 sha256(이 파일 · runners/ruler900.py)": sha(ME),
            "참조 산출물 sha256": {
                "runners/out900_levers.json": sha(ROOT / "runners/out900_levers.json"),
                "runners/out898_board.json": sha(ROOT / "runners/out898_board.json"),
                "runners/out112_board.json": sha(ROOT / "runners/out112_board.json")}},
        "🔴 근거": {
            "커밋": "39afa03e6",
            "제목": ("🔴 898 판정 — 판과 자가 다른 스피어만을 쓰고 있었다. "
                   "판을 자에 맞췄다: 정본 0.46982 → 0.47034"),
            "무엇이 바뀌었나": ("state/rank_test.spearman 이 서수 → 동률 평균"
                        "(scipy.stats.spearmanr)으로. **손잡이가 아니라 통계량의 정의**"),
            "⚠ 옛 정본(팔 A · 서수 · **은퇴**한 시대 값)": old["평균"],
            "🔴 새 정본(팔 B · 동률 평균)": new["평균"],
            "898 이 등록한 짝 Δ": 0.00051922,
        },
        "이번 팔 A": {"씨앗별(전정밀)": mine,
                  "평균": float(np.mean(mine)),
                  "SD(ddof=1)": float(np.std(mine, ddof=1)),
                  "SE": float(np.std(mine, ddof=1) / np.sqrt(len(mine)))},
        "대조": {
            "🔴 오늘의 정본(898 팔 B · 동률 평균)": cmp("new", new),
            "⚠ 옛 정본(898 팔 A · 서수 · **은퇴**한 시대 값)": cmp("old", old),
            "⚠ #112 동결 산출물(out112_board.json · **은퇴**한 시대 값)": cmp("frozen", frozen),
        },
        "🔴 판정에 미치는 영향": (
            "없다. 짝 Δ 는 **같은 실행·같은 자료(sha 721a7b7e0d15)** 안에서 뺀 값이라 "
            "판 수준값과 무관하다. out900_levers.json 의 「🔴 팔 A 와 판 정본 대조」 "
            "필드가 옛 값과 견줬을 뿐이고, 그 필드가 낸 차 +0.00051922 는 **898 이 이미 "
            "등록한 「스피어만 구현」 성분과 같은 수다** --- 즉 그 필드는 틀린 이름표가 "
            "붙은 채로도 옳은 수를 냈다."),
        "🔴 고칠 것(내가 안 고친다 · 저장소 밖)": (
            "메모리 인덱스 MEMORY.md 의 판 정본 한 줄이 **은퇴**한 시대 값(#112 로 "
            "2026-08-10 갱신이라 적힌 그 줄)이다. 인계 카드 본문(83~86줄)은 이미 옳다."),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"대조": res["대조"]}, ensure_ascii=False, indent=1), flush=True)
    print(f"완료 · {OUT}", flush=True)


if __name__ == "__main__":
    main()
