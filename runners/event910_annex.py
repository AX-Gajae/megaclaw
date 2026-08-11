"""910 팔 ㅂ 부록 — 🔴 **지평 902 와 수가 다르다.** 어디서 갈리는지 센다.

지평 902 §4 는 *「창 안에 스크린수 변화가 1회 이상 있는 개체 **398** / 분모 **404**
(D3 유보 중 2회+ 관측) · 창 안 변화 **사건 7,144회**」* 라고 적었다.
지시가 *「전부 직접 세라 · 인용하지 마라」* 였으므로 직접 셌더니 **다른 수**가 나왔다.

🔴 이 파일은 **누가 맞나를 판정하지 않는다.** 「어느 입력·어느 정의에서 갈리나」를 센다.
🔴 이벤트 표(`data/state/eventline910.jsonl`)를 **다시 읽어** 대조한다(손 전사 금지).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from event import sources as S                                        # noqa: E402

OUT = ROOT / "runners/out910_annex.json"
LINE = ROOT / "data/state/eventline910.jsonl"


def d3_map():
    import calendar
    ax = json.loads((ROOT / "data/state/kobis_axes.json").read_text())
    out = {}
    for k, v in ax.items():
        rd, y = v.get("release_date"), v.get("y")
        if not rd or y is None:
            continue
        d = S._parse_day(rd)
        if d is None:
            continue
        yf = d.year + (d.timetuple().tm_yday - 1) / (366 if calendar.isleap(d.year) else 365)
        if yf >= 2025.0:
            out[v.get("name")] = (d, v.get("마지막 관측일차"))
    return out


def count_window(panel, d3, *, last_day=None, win=20, use_last_obs_day=False):
    """창 안 스크린수 변화 — 개체 수와 사건 수. 🔴 창의 정의를 인자로 노출한다."""
    ents, ev = set(), 0
    ge2 = 0
    for t, (rd, lastn) in d3.items():
        seq = [o for o in panel.get(t, [])
               if (last_day is None or o[0] <= last_day)]
        if len(seq) >= 2:
            ge2 += 1
        w = win if not use_last_obs_day or lastn is None else int(lastn)
        prev = None
        for dt, cells, _ in seq:
            dd = S._parse_day(dt)
            if dd is None or not (rd <= dd <= rd + timedelta(days=w)):
                continue
            cur = cells.get("스크린수")
            if prev is not None and cur is not None and cur != prev:
                ents.add(t)
                ev += 1
            if cur is not None:
                prev = cur
    return {"개체": len(ents), "사건": ev, "2회 이상 관측(그 입력 기준)": ge2}


def main():
    t0 = datetime.now(timezone.utc).isoformat()
    pan = S.load_kobis_panel()
    panel, d3 = pan["panel"], d3_map()

    #: 🔴 이벤트 표를 **다시 읽어** 같은 수를 낸다(손 전사 금지)
    line_ents, line_ev = set(), 0
    n_line = 0
    for i, ln in enumerate(open(LINE)):
        if i == 0:
            hdr = json.loads(ln)
            continue
        e = json.loads(ln)
        n_line += 1
        if e["종류"] != "영화.스크린수변화":
            continue
        rec = d3.get(e["개체"])
        if not rec:
            continue
        t = S._parse_day(e["t_occur"])
        if t and rec[0] <= t <= rec[0] + timedelta(days=20):
            line_ents.add(e["개체"])
            line_ev += 1

    rep = {
        "노트": 910, "팔": "ㅂ 부록 — 지평 902 와의 수 차이",
        "시작 시각(UTC)": t0,
        "코드 sha256": {"runners/event910_annex.py": S.sha256(__file__),
                        "event/sources.py": S.sha256(ROOT / "event/sources.py")},
        "🔴 지평 902 §4 가 적은 수(인용 · 내가 안 잰 것)": {
            "창 안 스크린수 변화가 1회 이상인 개체": 398,
            "분모": 404, "분모의 뜻": "D3 유보 중 2회+ 관측",
            "창 안 변화 사건 수": 7144,
            "출처": "docs/지평/902.md §4",
        },
        "🔴 내가 직접 센 수 (같은 창 정의: 개봉일 ~ +20일)": {
            "지금 입력 전량(백필 2 + 날짜별 4)": count_window(panel, d3),
            "🔴 분모(D3 유보)": len(d3),
        },
        "🔴 어디서 갈리나 — 입력을 902 시점으로 되돌려 본다": {
            "🔴 무엇을 바꿨나": "일별 판의 관측일 상한을 옮긴다. 902 는 2026-08-11T06:18 에 돌았고 "
                        "`data/ingest/kobis/2026-08-10.json` 은 **그 뒤인 07:17 에 다시 쓰였다**",
            "≤ 2026-08-01 (백필만)": count_window(panel, d3, last_day="2026-08-01"),
            "≤ 2026-08-08": count_window(panel, d3, last_day="2026-08-08"),
            "≤ 2026-08-09": count_window(panel, d3, last_day="2026-08-09"),
            "≤ 2026-08-10 (= 전량)": count_window(panel, d3, last_day="2026-08-10"),
        },
        "🔴 창의 정의를 바꿔 본다": {
            "창 = 축 파일의 `마지막 관측일차`(개체마다 다르다)":
                count_window(panel, d3, use_last_obs_day=True),
            "⚠ 뜻": "라벨은 `개봉+20` 창의 마지막 값이지만 개체마다 실제 마지막 관측일차가 20 미만일 수 있다",
        },
        "🔴 이벤트 표를 다시 읽어 낸 같은 수": {
            "파일": str(LINE.relative_to(ROOT)),
            "파일 sha256": S.sha256(LINE),
            "읽은 행(헤더 제외)": n_line,
            "헤더가 적은 행": hdr["행 수(파일에 쓴 것)"],
            "🔴 둘이 같나(assert)": n_line == hdr["행 수(파일에 쓴 것)"],
            "창 안 스크린수 변화 개체": len(line_ents), "사건": line_ev,
        },
        "🔴 내 두 수가 서로 다른 이유 — 🔴 자백(조항 60)": None,
        "🔴 판정": None,
        "🔴 시운전 자백 — 값을 보고 **무엇을 바꿨나**(사후 부분집합 방지)": {
            "🔴 사전등록의 예측 P1~P8 은 **한 글자도 안 고쳤다**": True,
            "🔴 판정의 자(§6)도 안 고쳤다": True,
            "🔴 값을 보고 **더한** 것 둘 — 전부 「판정 미사용」 딱지를 달았다": [
                "가 — `climate.diag_nth_conditional` (개봉 후 일차 구간을 더한 조건부). "
                "이유: 「③ 을 0 에서 올리려면 무엇이 필요한가」를 수로 적으려고. **판정에 안 썼다**",
                "나 — `climate.transition_dayset` (하루의 종류 집합 단위 전이). "
                "🔴 이유: **초판의 전이 표에 인공물이 있었다** — 같은 날 동시 발생의 순서가 "
                "저장소에 없어서 (날짜, 종류) 알파벳 정렬이 순서를 만들어 냈다"
                "(초판 실측: 스크린수→상영횟수 80,070 대 반대 269). 그 인공물이 없는 단위로 다시 쟀다",
            ],
            "🔴 값을 보고 **뺀** 것": "없다",
            "🔴 시운전 횟수": "`--census` 1회 · `--dry`(이벤트 표를 안 쓰는 판) 2회 뒤 `--run` 1회",
        },
        "🔴 사전등록이 측정보다 앞섰나": {
            "사전등록 mtime(UTC)": S.mtime_utc(ROOT / "docs/prereg_910_event.md"),
            "본 러너 시작 시각(UTC)": json.loads(
                (ROOT / "runners/out910_event.json").read_text())["시작 시각(UTC)"],
            "🔴 앞섰나": S.mtime_utc(ROOT / "docs/prereg_910_event.md") < json.loads(
                (ROOT / "runners/out910_event.json").read_text())["시작 시각(UTC)"],
            "🔴 커밋은 없다": "지시가 `git add`·커밋을 금지했다. 그래서 **커밋 시각이라는 증거물이 없다** — "
                       "mtime 은 고쳐 쓸 수 있으므로 이 증거는 커밋보다 **약하다**. 그렇게 적는다",
        },
        "🔴 못 한 것": [
            "🔴 902 의 러너(`runners/out902h_snap.py`)를 **안 돌렸다** — 그 코드를 그대로 재실행해 "
            "비교하지 않았다. 그러니 「902 가 틀렸다」고 말하지 않는다",
            "🔴 영화 개체 키는 제목 문자열이다 — 재개봉이 뭉친다(지평 902 §2.1 이 이미 적었다)",
        ],
    }

    #: 🔴 내 안에서도 수가 둘이다. 왜인지 세서 적는다(조항 60 — 두 수를 이어 붙이기 전에)
    cross = 0
    for t, (rd, _ln) in d3.items():
        seq = panel.get(t, [])
        prev_out = None
        for dt, cells, _ in seq:
            dd = S._parse_day(dt)
            cur = cells.get("스크린수")
            if dd is None or cur is None:
                continue
            inwin = rd <= dd <= rd + timedelta(days=20)
            if inwin and prev_out is not None and prev_out[1] != cur \
                    and not (rd <= prev_out[0] <= rd + timedelta(days=20)):
                cross += 1
            prev_out = (dd, cur)
    rep["🔴 내 두 수가 서로 다른 이유 — 🔴 자백(조항 60)"] = {
        "수 A — 창 **안 관측 쌍**만(부록의 count_window)": count_window(panel, d3)["사건"],
        "수 B — `t_occur` 이 창 안(이벤트 표를 다시 읽은 값)": line_ev,
        "차": line_ev - count_window(panel, d3)["사건"],
        "🔴 차의 정체 — 직전 관측이 **창 밖**인 변화 사건 수": cross,
        "🔴 차 == 그 수인가(assert)": (line_ev - count_window(panel, d3)["사건"]) == cross,
        "🔴 뜻": "같은 이름(「창 안 스크린수 변화 사건」)의 수가 **정의에 따라 둘**이다. "
               "902 의 7,144 가 어느 쪽인지는 그 문서에 안 적혀 있다 — **못 짚었다**",
    }

    a = rep["🔴 내가 직접 센 수 (같은 창 정의: 개봉일 ~ +20일)"]["지금 입력 전량(백필 2 + 날짜별 4)"]
    b = rep["🔴 어디서 갈리나 — 입력을 902 시점으로 되돌려 본다"]
    rep["🔴 판정"] = {
        "형": "🔴 수가 다르다 — 그리고 **입력을 되돌려도 안 맞는다**"
        if b["≤ 2026-08-01 (백필만)"]["개체"] != 398 else "🔴 입력 시점 차이로 설명된다",
        "내 수": a, "902 의 수": {"개체": 398, "사건": 7144, "분모": 404},
        "🔴 조항 59 어법": "「902 가 틀렸다」가 아니라 **「같은 이름의 수가 두 개이고 나는 그 차이의 "
                   "출처를 못 짚었다」**. 아래 후보를 남긴다",
        "차이의 후보": [
            "가 — 창의 정의(개봉+20 고정 대 개체별 `마지막 관측일차`)",
            "나 — 분모(902 는 404 = 2회+ 관측 · 나는 406 = D3 유보 전량)",
            "다 — 같은 날 중복 제목 처리(나는 첫 판만 남긴다)",
            "라 — 결측 스크린수의 처리(나는 결측을 건너뛰고 직전 유효값과 잇는다)",
            "마 — 입력 시점(`2026-08-10.json` 이 902 뒤에 다시 쓰였다)",
        ],
    }
    rep["끝 시각(UTC)"] = datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps(rep["🔴 판정"], ensure_ascii=False, indent=1))
    print(json.dumps(rep["🔴 어디서 갈리나 — 입력을 902 시점으로 되돌려 본다"],
                     ensure_ascii=False, indent=1))
    print(json.dumps(rep["🔴 창의 정의를 바꿔 본다"], ensure_ascii=False, indent=1))
    print(json.dumps(rep["🔴 이벤트 표를 다시 읽어 낸 같은 수"], ensure_ascii=False, indent=1))
    print(json.dumps(rep["🔴 내 두 수가 서로 다른 이유 — 🔴 자백(조항 60)"],
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
