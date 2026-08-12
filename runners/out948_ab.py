# -*- coding: utf-8 -*-
"""노트 948 [수리] --- ㉮/㉯ 가르기를 「이름 접두사」에서 「증거」로 되돌린다.

사전등록: ``docs/prereg_948_evidence.md`` (커밋 ``1c6ac37ec`` · **측정 전**)
입력: 티처 #87 C1 · C2 · C3 · M2 · M3 · M4 · M5 · M8 · m8

🔴 **증거력의 한계(조항 61 --- 먼저 적는다)**: 이 러너는 **분류기**를 잰다.
날 것 호출 자리는 **하나도 안 움직인다** --- 움직이는 것은 그 자리를 부르는 **이름**뿐이다.
그러므로 아래 수는 **개선폭이 아니라 947 이 「원리상 못 고친다」로 덮어 둔 자리의 크기**다.

🔴 **채점기에 상수를 박지 않는다**(티처 #87 M5). 못 잰 예측은 ``안 쟀다`` 로 적고
**분모에서 뺀다**. 🔴 **옛 산출물을 지우고 시작한다**(조항 59 · 947 이 세 번 밟았다).
"""
import ast
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab import gitcall as gc            # noqa: E402
from ingest import audit                 # noqa: E402

OUT = ROOT / "runners/out948_ab.json"
FIVE = ROOT / "runners/out948_fiveprime.json"
STAMP_CODE = ("lab/gitcall.py", "lab/keyspace.py", "runners/fiveprime902.py",
              "ingest/audit.py", "runners/out948_ab.py")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stamp(inputs) -> dict:
    return {
        "시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "🔴 코드 sha256(이게 자다)": {c: (sha(ROOT / c) if (ROOT / c).exists()
                                   else "🔴 파일 없음") for c in STAMP_CODE},
        "🔴 입력 산출물 sha256": {i: (sha(ROOT / i) if (ROOT / i).exists()
                             else "🔴 파일 없음") for i in inputs},
    }


#: 🔴 **수리 전 rev**(티처 #87 원장 항목 = 이 사이클이 손대기 전 트리).
PRE_REV = "3d2e66fa3"


def _old_ratchet(rev: str = PRE_REV):
    """`rev` 의 **옛** 래칫 등록을 읽는다 --- P9 를 재현 가능하게 재려고.

    🔴🔴 **채점기 정정(같은 세션 · 자백)**: 초판은 `HEAD` 를 읽었다. 그런데 이 러너는
    **수리를 커밋한 뒤에** 도므로 `HEAD` 에는 **이미 새 등록표가 들어 있다** ---
    「옛 등록으로 재면 넘치나」를 **새 등록으로 재고 있었다.** 그래서 P9 가 `false` 로
    채점됐는데 그것은 **예측의 반증이 아니라 자의 고장**이다(조항 59).
    자가 **가리키는 곳**을 고쳤고 **자 자체는 안 갈았다** --- 그리고 고치기 전 값
    (`HEAD` 로 읽은 것)을 **같은 산출물에 나란히 싣는다**. 🔴 감추면 그것이 티처 #87 M1 이
    잡은 「측정이 자를 갈아 끼웠다」와 같은 짓이 된다.
    """
    r = subprocess.run(["git", "-C", str(ROOT), "show", "%s:ingest/audit.py" % rev],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, None
    debt = by = None
    for n in ast.parse(r.stdout).body:
        tgt = None
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None):
            tgt = n.targets[0].id
        elif isinstance(n, ast.AnnAssign) and getattr(n.target, "id", None):
            tgt = n.target.id
        if tgt == "DEAD_HISTORY_DEBT":
            debt = ast.literal_eval(n.value)
        elif tgt == "DEAD_HISTORY_BY_DOC":
            by = ast.literal_eval(n.value)
    return debt, by


def main():
    t0 = time.time()
    if OUT.exists():
        OUT.unlink()                       # 🔴 조항 59 --- 옛 JSON 을 새 결과로 읽지 마라
    st = stamp([FIVE.relative_to(ROOT).as_posix()])
    res = {"무엇": "948 [수리] ㉮/㉯/㉲ 가르기 --- 증거를 먼저 본다(티처 #87 C3)",
           "🔴 증거력의 한계(조항 61)": __doc__.split("🔴 **증거력의 한계")[1].split("🔴 **채점")[0].strip()}

    # ── 절 1 --- 분류 실측 ------------------------------------------------
    cen = gc.census()
    raw = cen["🔴 날 것 전량(목록)"]
    K_W = "🔴 지금 sha 를 인용하는 커밋된 파일(HEAD 전량)"
    K_N = "⚠ 947 의 좁은 자로 세면(음성 대조 · 판정에 쓰지 마라)"
    narrow_diff = [{"파일:줄": s["파일:줄"], "넓은 자": s[K_W], "좁은 자": s[K_N]}
                   for s in raw if set(s[K_W]) != set(s[K_N])]
    robots = [s for s in raw if s["파일:줄"] == "runners/out942_robots.py:293"]
    res["1 🔴 분류 실측(자: 이 실행의 census 하나)"] = {
        "검사": "1 🔴 ㉮/㉯/㉲ --- 증거를 먼저 본 분류",
        "🔴 분모 ① 훑은 .py": cen["🔴 분모 ① 훑은 .py"],
        "🔴 분모 ② 자 A 호출 자리": cen["🔴 분모 ② 자 A 호출 자리(경로를 내는 것만)"],
        "🔴 분모 ③ 자 B 줄 히트": cen["🔴 분모 ③ 자 B 줄 히트"],
        "🔴 분모 ④ 날 것": cen["🔴 분모 ④ 날 것"],
        "🔴 ㉮ 원리상 못 고친다": cen["🔴 분모 ④-㉮ 원리상 못 고친다(sha 인용 ≥ 1)"],
        "🔴 ㉯ 고칠 수 있다(㉲ 포함 · 이 수가 0 이어야 통과)":
            cen["🔴 분모 ④-㉯ 고칠 수 있다(🔴 이 수가 0 이어야 통과)"],
        "🔴 ㉲ 규약상 안 고친다(㉯ 의 부분집합)":
            cen["🔴 분모 ④-㉲ 그중 규약상 안 고친다(동결 · ㉯ 의 부분집합)"],
        "🔴 순㉯ 막는 것이 아무것도 없는 것": cen["🔴 분모 ④-순㉯ 막는 것이 아무것도 없는 것"],
        "분모 ⑤ 의도적": cen["분모 ⑤ 의도적 날 것(음성 대조)"],
        "분모 ⑥ 안전": cen["분모 ⑥ 안전"],
        "🔴 분해가 닫히나(④+⑤+⑥ == ②)": (
            cen["🔴 분모 ④ 날 것"] + cen["분모 ⑤ 의도적 날 것(음성 대조)"]
            + cen["분모 ⑥ 안전"] == cen["🔴 분모 ② 자 A 호출 자리(경로를 내는 것만)"]),
        "⚠ 왜 이것을 세나": ("티처 #87 M6 --- 947 원장은 `46 ≠ 15+5+23` 이었다. "
                       "**두 실행의 수를 이어 붙였기 때문**이다. 이 절의 수는 "
                       "**전부 이 한 실행**에서 나온다(조항 60)"),
        "🔴 ㉯/㉲ 목록과 사유": cen["🔴 ㉯/㉲ 목록과 사유"],
        "㉮ 목록과 사유(🔴 dict 가 아니라 목록 --- 티처 #87 M8)": cen["㉮ 목록과 사유"],
        "🔴 M8 대조 --- 날 것 수 대 ㉮+㉯ 목록 길이": {
            "날 것": len(raw),
            "㉮ 목록 길이": len(cen["㉮ 목록과 사유"]),
            "㉯/㉲ 목록 길이": len(cen["🔴 ㉯/㉲ 목록과 사유"]),
            "🔴 합이 날 것과 같나": (len(cen["㉮ 목록과 사유"])
                             + len(cen["🔴 ㉯/㉲ 목록과 사유"]) == len(raw)),
            "⚠ 947 은": "dict 키가 `파일:줄` 이라 두 갈래가 겹치면 삼켰다 --- 15 대 13",
        },
        "🔴 음성 대조 --- 947 의 좁은 자(pathspec 둘)와 948 의 넓은 자(HEAD 전량)": {
            "왜": ("티처 #87 m8 --- 좁은 pathspec 은 `docs/**` 의 sha 인용을 **원리상** "
                  "안 본다. 「안 걸렸다」와 「못 걸린다」를 가르려면 넓혀서 재야 한다"),
            "🔴 두 자가 다른 답을 낸 자리 수": len(narrow_diff),
            "그 목록": narrow_diff or "없음",
            "🔴 오늘의 결론": ("두 자가 같은 답을 낸다 --- m8 은 **오늘 결론 불변**이다. "
                        "🔴 「안 걸렸다」이지 「못 걸린다」가 아니다"
                        if not narrow_diff else
                        "🔴 두 자가 갈렸다 --- **넓은 자가 정본**이고 947 의 수를 정정한다"),
        },
        "🔴 out942_robots.py:293(티처 #87 C3 이 지목한 자리)": (
            {"사유": robots[0]["🔴 ㉮/㉯/㉲"], "sha 인용": robots[0][K_W],
             "동결 접두사인가": robots[0]["동결(941~946)"]} if robots else
            "🔴 못 찾았다 --- 그 자리가 사라졌다(「없다」가 아니라 「달라졌다」)"),
        "🔴🔴 래칫": cen["🔴🔴 래칫(티처 #87 C3 --- 이 성질을 산출물에 적는다)"],
        "통과": cen["통과"],
        "🔴 통과의 뜻": ("**㉯(㉲ 포함)가 0 이어야 통과.** 🔴 오늘은 붉은 것이 옳다 --- "
                   "947 이 이름으로 비워 둔 분모가 증거로 다시 채워지는 자리다"),
    }

    # ── 절 2 --- 죽은 숫자 게이트 -----------------------------------------
    dn = audit.dead_numbers()
    aged = dn["역사 기록(래칫)"]["문서별"]

    def _p9(rev):
        debt, by = _old_ratchet(rev)
        if debt is None:
            return {"🔴 못 읽었다": "`git show %s:ingest/audit.py` --- 「없다」가 아니다" % rev}
        grew_old = {d: [n, by.get(d)] for d, n in aged.items()
                    if d in by and n > by[d]}
        return {"자(rev)": rev, "등록 총합": debt, "등록표 합": sum(by.values()),
                "⚠ 등록이 자기와 어긋나나(표 합 != 상수)": sum(by.values()) != debt,
                "지금 실측 총합": dn["역사 기록(래칫)"]["수"],
                "이 등록으로 재면 넘치나": (dn["역사 기록(래칫)"]["수"] > debt
                                  or bool(grew_old)),
                "이 등록으로 재면 늘어난 문서": grew_old or "없음"}

    p9 = _p9(PRE_REV)
    p9_head = _p9("HEAD")
    old_debt = p9.get("등록 총합")
    p9["🔴 채점기 정정(자백) --- 초판이 읽던 곳"] = {
        "무엇": ("초판 채점기는 `HEAD` 를 읽었다. 이 러너는 **수리를 커밋한 뒤에** 돌므로 "
               "`HEAD` 에는 **이미 새 등록표**가 있다 --- 「옛 등록으로 재면」을 "
               "**새 등록으로 재고 있었다.** P9 가 `false` 로 채점됐고 그것은 "
               "**예측의 반증이 아니라 자의 고장**이다(조항 59)"),
        "🔴 자를 갈아 끼운 것이 아니다": ("고친 것은 자가 **가리키는 rev** 하나이고 판정식은 "
                             "그대로다. 그리고 고치기 전 값을 **여기 나란히 싣는다** --- "
                             "감추면 티처 #87 M1 이 잡은 「측정이 자를 갈아 끼웠다」가 된다"),
        "초판(HEAD)으로 읽은 값": p9_head,
    }
    res["2 🔴 죽은 숫자 게이트"] = {
        "검사": "2 🔴 `ingest.audit.dead_numbers()` --- 947 이 되살린 은퇴값",
        "🔴 경성 걸린 곳": dn["걸린 곳"],
        "🔴 경성 걸린 곳 수": 0 if dn["걸린 곳"] == "없음" else len(dn["걸린 곳"]),
        "정본 대조": dn["정본 대조"]["표기"],
        "역사 래칫": {k: dn["역사 기록(래칫)"][k]
                 for k in ("수", "등록된 빚", "빚이 늘었나", "🔴 늘어난 문서(지금 대 등록)")},
        "🔴 P9 재현 --- 947.md 만 고쳤을 때 통과했겠나(옛 등록으로 다시 잼)": p9,
        "통과": dn["통과"],
    }

    # ── 절 3 --- ⑤′ 에서 읽는 것(게이트 사유 · 조항 62) --------------------
    if not FIVE.exists():
        res["3 🔴 ⑤′ 에서 읽는 것"] = {
            "검사": "3 ⑤′ 산출물 읽기",
            "🔴 못 읽었다": "`runners/out948_fiveprime.json` 이 없다 --- ⑤′ 를 먼저 돌려라. "
                      "**「없다」가 아니라 「못 읽었다」다**(조항 59)",
            "통과": False}
        five = None
    else:
        five = json.loads(FIVE.read_text(encoding="utf-8"))
        g = five["2 게이트"]
        b = five["1 소비자 역참조"]
        src = g["🔴 사유의 출처(948 신설 · 티처 #87 M2 가 연 길의 구멍을 센다)"]
        cli_n = src["🔴 CLI 사유(`--exempt`)로 닫힌 게이트 수"]
        nore = g["🔴 사유 없이 안 돌린 것"]
        would = sorted(set(nore) | set(src["그 목록"]))
        d62 = {}
        for sec, dd in (("1", b), ("2", g)):
            for kk, vv in dd.items():
                if kk.startswith("🔴 조항 62"):
                    plant = vv.get("④ 심은 키")
                    d62["절 %s · %s" % (sec, kk)] = {
                        "통과": vv.get("통과"),
                        "🔴 심었나": (plant.get("🔴 심었나") if isinstance(plant, dict)
                                 else "🔴 못 심었다"),
                        "🔴 발화했나": (plant.get("🔴 발화했나") if isinstance(plant, dict)
                                  else False),
                        "A − B": vv.get("🔴 A − B"), "B − A": vv.get("🔴 B − A"),
                    }
        res["3 🔴 ⑤′ 에서 읽는 것"] = {
            "검사": "3 ⑤′(`runners/out948_fiveprime.json`)에서 읽는 것",
            "🔴 자": "이 절의 수는 전부 **⑤′ 한 실행**에서 온다(조항 60 · 티처 #87 M6)",
            "게이트 명부(분모)": g["🔴 게이트 생산자 수(분모)"],
            "안 돌린 수": g["🔴 안 돌린 수"],
            "🔴 사유 없이 안 돌린 것": nore,
            "🔴 사유 없이 안 돌린 수": len(nore),
            "🔴 CLI 사유(`--exempt`)로 닫힌 수": cli_n,
            "🔴 exempt 를 안 넘겼다면 사유 없이 안 돌렸을 것(= 947 의 9)": len(would),
            "그 목록": would,
            "🔴 P7 의 「9」는 **남의 실행의 수**다(자백 · 조항 60)": (
                "사전등록 P7 은 「9 → 0」이라 적었다. 그 **9 는 947 의 ⑤′ 실행**"
                "(다른 `--base` · 다른 `--ran` · 다른 트리)에서 나온 수다. "
                "**이 실행의 같은 수는 %d** 다 --- 🔴 **분모가 다른 두 수를 이어 붙인 것**이고, "
                "그것은 내가 이 사이클에 갚기로 한 티처 #87 M6 그 자체다. "
                "**기제 주장(사유는 이미 있었고 함수가 안 받았을 뿐)은 이 실행 안에서 서고, "
                "상수 9 는 안 선다.**" % len(would)),
            "🔴 이 A/B 가 무엇을 갈랐나": (
                "947 은 이 절을 「`--gate-exempt` CLI 가 없어서 **구조적으로 영원히 붉다**」로 "
                "닫았다. 같은 실행 안의 두 수(%d → %d)가 그 문장을 **거짓으로** 만든다 --- "
                "사유는 이미 있었고 함수가 안 받았을 뿐이다(티처 #87 M2)"
                % (len(would), len(nore))),
            "🔴 조항 62 를 건 절 넷(티처 #87 M3)": d62,
            "🔴 조항 62 전부 통과인가": (bool(d62) and all(v["통과"] for v in d62.values())),
            "통과": (len(nore) == 0 and bool(d62)
                    and all(v["통과"] for v in d62.values())),
        }

    # ── 절 4 --- 사전등록 채점 (🔴 상수 금지 · 티처 #87 M5) -----------------
    s1 = res["1 🔴 분류 실측(자: 이 실행의 census 하나)"]
    rt = cen["🔴🔴 래칫(티처 #87 C3 --- 이 성질을 산출물에 적는다)"]["파일별"]
    late = [(rel, c) for rel, v in rt.items()
            for c, t in v["인용 파일의 마지막 커밋"].items()
            if t < v["이 소스의 마지막 커밋"]]
    same = [(rel, c) for rel, v in rt.items()
            for c, t in v["인용 파일의 마지막 커밋"].items()
            if t == v["이 소스의 마지막 커밋"]]
    NOTMEASURED = "🔴 안 쟀다"
    scores = {
        "P1 out942_robots.py:293 이 ㉯ 로 넘어온다(sha 인용 0)": (
            bool(robots) and robots[0]["🔴 ㉮/㉯/㉲"].startswith("🔴 ㉯")
            and not robots[0][K_W]),
        "P2 절 1-나 가 통과 False 가 된다": (cen["통과"] is False),
        "P3 날 것 15 · ㉮ 14 · ㉯ 1 · ㉲ 1 · 순㉯ 0": (
            [cen["🔴 분모 ④ 날 것"],
             cen["🔴 분모 ④-㉮ 원리상 못 고친다(sha 인용 ≥ 1)"],
             cen["🔴 분모 ④-㉯ 고칠 수 있다(🔴 이 수가 0 이어야 통과)"],
             cen["🔴 분모 ④-㉲ 그중 규약상 안 고친다(동결 · ㉯ 의 부분집합)"],
             cen["🔴 분모 ④-순㉯ 막는 것이 아무것도 없는 것"]] == [15, 14, 1, 1, 0]),
        "P4 넓힌 자와 좁은 자가 같은 답": (len(narrow_diff) == 0),
        "P5 인용이 소스보다 먼저인 자리 0": (len(late) == 0),
        "P6 ㉮ 목록 길이 == ㉮ 수": (len(cen["㉮ 목록과 사유"])
                             == cen["🔴 분모 ④-㉮ 원리상 못 고친다(sha 인용 ≥ 1)"]),
        "P7 게이트 「사유 없이 안 돌린 것」 9 → 0": (
            NOTMEASURED if five is None else
            (res["3 🔴 ⑤′ 에서 읽는 것"]["🔴 사유 없이 안 돌린 수"] == 0
             and res["3 🔴 ⑤′ 에서 읽는 것"][
                 "🔴 exempt 를 안 넘겼다면 사유 없이 안 돌렸을 것(= 947 의 9)"] == 9)),
        "P8 죽은 숫자 경성 걸린 곳 1 → 0": (res["2 🔴 죽은 숫자 게이트"]["🔴 경성 걸린 곳 수"] == 0),
        "P9 947.md 만으로는 통과 못 한다(래칫이 이미 넘쳤다)": (
            NOTMEASURED if old_debt is None else p9["이 등록으로 재면 넘치나"]),
        "P10 조항 62 심은 키가 절 1·2 에서 발화한다": (
            NOTMEASURED if five is None else
            (bool(d62) and all(v["🔴 발화했나"] for v in d62.values()))),
    }
    hit = [k for k, v in scores.items() if v is True]
    miss = [k for k, v in scores.items() if v is False]
    unmeasured = [k for k, v in scores.items() if v == NOTMEASURED]
    res["4 🔴 사전등록 채점"] = {
        "검사": "4 사전등록 채점(`docs/prereg_948_evidence.md` · 커밋 `1c6ac37ec`)",
        "🔴 채점기에 상수를 박지 않는다": ("티처 #87 M5 --- 947 의 P3 채점기 마지막 인자가 "
                              "**하드코딩된 `True`** 였다. 아래는 전부 **계산**이고, "
                              "못 잰 것은 `안 쟀다` 로 분모에서 뺀다"),
        "예측별": scores,
        "🔴 분모(계산으로 채점된 예측 수)": len(hit) + len(miss),
        "🔴 맞은 수": len(hit), "🔴 빗나간 수": len(miss),
        "🔴 안 쟀다": unmeasured or "없음",
        "빗나간 목록": miss or "없음",
        "🔴 래칫 방향 실측": {
            "인용이 소스보다 **나중**": sum(len(v["인용 파일의 마지막 커밋"])
                                 for v in rt.values()) - len(late) - len(same),
            "🔴 **같은 커밋**(소스와 인용이 한 커밋에 들어갔다)": len(same),
            "인용이 소스보다 **먼저**": len(late),
            "⚠": ("같은 커밋이 대부분이면 「인용이 나중에 붙어 자리를 잠갔다」가 아니라 "
                  "**「사이클이 자기 코드와 자기 산출물을 한 커밋에 넣는다」**는 뜻이다 --- "
                  "래칫은 **다음 사이클이 아니라 그 사이클 자신이** 채운다"),
        },
        "통과": (len(miss) == 0),
    }

    secs = {k: v for k, v in res.items() if isinstance(v, dict) and "통과" in v}
    fail = sorted(k for k, v in secs.items() if not v["통과"])
    res["🔴 절 수(분모)"] = len(secs)
    res["🔴 실패한 절"] = fail or "없음"
    res["🔴 붉은 것이 옳은 절"] = ["1 🔴 분류 실측(자: 이 실행의 census 하나)"]
    res["통과"] = (not [f for f in fail if f not in res["🔴 붉은 것이 옳은 절"]])
    res["🔴 통과의 뜻"] = ("절 1 은 **붉은 것이 예측**이다(P2). 그래서 이 러너의 `통과` 는 "
                    "**절 1 을 뺀 나머지**가 전부 초록인가를 뜻한다. 🔴 **절 1 의 붉음을 "
                    "감추지 않는다** --- 위 `🔴 실패한 절` 에 그대로 실린다")
    st["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    st["초"] = round(time.time() - t0, 1)
    res.update(st)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items()
                           if kk.startswith(("🔴", "통과", "검사"))}
                          if isinstance(v, dict) and "통과" in v else v)
                      for k, v in res.items()}, ensure_ascii=False, indent=1))
    print("산출물: %s" % OUT)
    return 0 if res["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
