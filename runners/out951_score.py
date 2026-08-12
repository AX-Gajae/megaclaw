# -*- coding: utf-8 -*-
"""노트 951 — 사전등록 **채점기**. 🔴 산출물에서 찍는다(손 전사 0).

`docs/prereg_951_guard.md` §5 의 P1~P10 을 §3 의 채점 규칙으로 채점한다.
🔴 **채점 규칙은 사전등록에 예측보다 먼저 적혀 있고, 이 파일은 그것을 옮길 뿐이다.**

⚠ **§4 「나는 이미 읽었다」**: P1·P5·P8 은 티처가 답을 줬거나 내가 사전등록 전에 이미
실측한 것이다. **눈 감고 한 예측은 일곱**이고 이 러너가 그 둘을 **따로** 센다.

돌리기::

    python3 -m runners.out951_score
"""
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "runners/out951_score.json"
GUARD = "runners/out951_guard.json"
F951 = "runners/out951_fiveprime.json"
F950 = "runners/out950_fiveprime.json"

#: 🔴 §4 --- 성적에서 빼는 것(티처가 준 답 · 사전등록 전에 이미 본 것)
EYES_OPEN = ["P1", "P5", "P8"]

#: 🔴 P10 이 이름으로 요구한 셋
P10_MUST = ["3 판정 키 규약", "1-나", "2 게이트"]


def J(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def rows() -> dict:
    g = J(GUARD)
    s1, s2, s3, s4, s5 = (g["1 채널을 심어서 센다"], g["2 지문 자"], g["3 C2 를 가른다"],
                          g["4 재실행무해 재계수"], g["5 기록기 「모른다」 갈래"])
    f951, f950 = J(F951), J(F950)
    ign = s2["🔴 `.gitignore` 채널(티처 #90 m6)"]["950 판"]
    d3 = s3["파일별"]
    a, b = d3["runners/exp947_npzflow.json"], d3["runners/out945_stampscan.json"]
    fail = f951["🔴 실패한 절"]
    fail = fail if isinstance(fail, list) else []
    return {
        "P1": {"예측": "950 판 --- 발화 2 · 파일 생김 4",
               "실측": "발화 %d · 파일 생김 %d" % (
                   s1["🔴 950 판 --- 가드가 발화한 채널 수"],
                   s1["🔴 950 판 --- 파일이 실제로 생긴 채널 수"]),
               "맞았나": (s1["🔴 950 판 --- 가드가 발화한 채널 수"] == 2
                      and s1["🔴 950 판 --- 파일이 실제로 생긴 채널 수"] == 4)},
        "P2": {"예측": "951 판 --- 발화 5",
               "실측": s1["🔴 951 판 --- 가드가 발화한 채널 수"],
               "맞았나": s1["🔴 951 판 --- 가드가 발화한 채널 수"] == 5},
        "P3": {"예측": "지문 자가 여섯 채널을 **6/6** 잡는다",
               "실측": s2["🔴 950 판 드라이버 아래에서 지문이 잡은 채널 수"],
               "맞았나": s2["🔴 950 판 드라이버 아래에서 지문이 잡은 채널 수"] == 6,
               "🔴 왜 빗맞혔나": (
                   "가드가 막은 채널은 **쓰지 않았으므로 지문이 잴 것이 없다**. "
                   "「6/6」은 **원리상 성립할 수 없는 예측**이었다 --- 내가 잘못 적었다. "
                   "실제로 쓴 채널만 보면 %s 다"
                   % s2["🔴 **실제로 파일이 생긴 채널** 중 지문이 잡은 수(950 판)"])},
        "P4": {"예측": "`.gitignore` 채널 --- `git status` 0/1 · 지문의 무시 칸 1/1",
               "실측": "`git status` 가 봤나 %s · 지문의 바뀐 무시 경로 수 %s" % (
                   ign["🔴 `git status` 가 봤나"], ign["지문 --- 바뀐 무시 경로 수"]),
               "맞았나": (ign["🔴 `git status` 가 봤나"] is False
                      and ign["지문 --- 바뀐 무시 경로 수"] == 1
                      and ign["🔴 지문이 봤나"] is True)},
        "P5": {"예측": "문자열 0/0 · dict 4/0 → 🔴 **주 세션이 틀렸다**",
               "실측": "문자열 %d/%d · dict %d/%d" % (
                   a["🔴 경로 **문자열**로 부르면"], b["🔴 경로 **문자열**로 부르면"],
                   a["🔴 **로드된 dict** 로 부르면"], b["🔴 **로드된 dict** 로 부르면"]),
               "맞았나": (a["🔴 경로 **문자열**로 부르면"] == 0
                      and b["🔴 경로 **문자열**로 부르면"] == 0
                      and a["🔴 **로드된 dict** 로 부르면"] == 4
                      and b["🔴 **로드된 dict** 로 부르면"] == 0)},
        "P6": {"예측": "950 의 「같다 2」 → 「같다 1 · 모른다 1」",
               "실측": s4["🔴 950 의 「✅ 같다 2」가 오늘 무엇이 되었나"],
               "맞았나": (s4["🔴 ✅ 견주었고 같다"] == 1
                      and s4["🔴 견줄 절이 0 개다(950 은 「같다」로 셌다)"] == 1)},
        "P7": {"예측": "지문만 잡은 러너 **0**",
               "실측": s4["🔴 지문만 잡은 것(몽키패치는 못 잡았다)"],
               "맞았나": s4["🔴 지문만 잡은 것(몽키패치는 못 잡았다)"] == "없음"},
        "P8": {"예측": "`기록기` 13 중 「모른다」 **2**",
               "실측": s5["🔴 갈래별 수"].get("🔴 모른다", 0),
               "맞았나": s5["🔴 갈래별 수"].get("🔴 모른다", 0) == 2},
        "P9": {"예측": "sha 64자리로 고쳐도 ⑤′ `4 도장 확인` 통과 여부는 **안 바뀐다**",
               "실측": "950 %s → 951 %s" % (f950["4 도장 확인"]["통과"],
                                          f951["4 도장 확인"]["통과"]),
               "맞았나": f950["4 도장 확인"]["통과"] == f951["4 도장 확인"]["통과"]},
        "P10": {"예측": "⑤′ 실패한 절 **4 이상**이고 그 안에 %s 셋이 다 있다" % P10_MUST,
                "실측": {"실패한 절 수": len(fail), "실패한 절": fail or "없음"},
                "맞았나": (len(fail) >= 4
                       and all(any(m in k for k in fail) for m in P10_MUST))},
    }


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    t0 = time.time()
    r = rows()
    hit = sorted(k for k, v in r.items() if v["맞았나"] is True)
    miss = sorted(k for k, v in r.items() if v["맞았나"] is False)
    nom = sorted(k for k, v in r.items() if v["맞았나"] is None)
    blind = [k for k in r if k not in EYES_OPEN]
    res = {
        "무엇": "노트 951 사전등록 채점 --- 🔴 **산출물에서 찍는다(손 전사 0)**",
        "사전등록": "docs/prereg_951_guard.md",
        "🔴 분모(예측 수)": len(r),
        "🔴 맞았다": len(hit), "🔴 빗맞혔다": len(miss), "🔴 못 쟀다": len(nom),
        "맞은 것": hit, "빗맞힌 것": miss, "못 잰 것": nom or "없음",
        "🔴 §4 --- 눈 감고 한 예측만(P1·P5·P8 을 뺀다)": {
            "분모": len(blind),
            "맞았다": len([k for k in blind if r[k]["맞았나"] is True]),
            "빗맞혔다": len([k for k in blind if r[k]["맞았나"] is False]),
            "🔴 뜻": ("티처가 준 답의 재현과 사전등록 전에 이미 본 것은 **성적이 아니다**. "
                   "두 수를 **이어 붙이지 마라**(조항 60)"),
        },
        "예측별": r,
        "🔴 채점 규칙(사전등록 §3 그대로)": [
            "맞았다 = 예측이 실측과 **정확히** 같다. 「방향은 맞았다」는 **빗맞힌 것**이다",
            "못 쟀다 = 그 자를 못 돌렸다. 🔴 **「없다」로 적지 않는다**",
            "부등식 예측은 그 부등식이 성립하면 맞은 것으로 센다",
        ],
        "🔴 이 채점이 성적이 아닌 까닭": (
            "사전등록 §6 이 판정 규칙을 따로 적었다 --- **판정은 「맞은 예측 수」로 하지 않는다.** "
            "① 잡히는 채널이 늘었나 ② 채널과 무관한 자가 생겼나 ③ C2 를 갈랐나, 셋으로 한다"),
        "시각(UTC)": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "초": round(time.time() - t0, 1),
        "🔴 입력 산출물 sha256": {x: _sha(x) for x in (GUARD, F951, F950)},
        "🔴 코드 sha256(이게 자다)": {"runners/out951_score.py": _sha("runners/out951_score.py")},
        "통과": True,
        "🔴 통과의 뜻": "🔴 **「채점했다」는 뜻이다.** 빗맞힌 예측이 있어도 이 절은 초록이다",
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("맞았다 %d · 빗맞혔다 %d · 못 쟀다 %d (분모 %d)"
          % (len(hit), len(miss), len(nom), len(r)))


if __name__ == "__main__":
    main()
