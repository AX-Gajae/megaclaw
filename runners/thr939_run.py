# -*- coding: utf-8 -*-
"""팔 939 — **비교가능성 문턱을 자료에서 정하고 · 규약 48 을 소급하고 · 배선 분류를 값으로 한다.**

사전등록: `docs/prereg_939_threshold.md` · 스탬프: `runners/out939_prereg_stamp.json`.

🔴 이 러너가 지키는 것
  · **남의 산출물을 읽기만 한다.** `runners/out*.json` 은 증거물이라 한 글자도 안 고친다.
  · **새 순열 뽑기를 안 돌린다** — 200기록을 읽어서 다시 센다.
  · 문턱은 **사전등록이 박은 공식**이 낸다. 손 전사 금지.
  · `state/perm922.py` · `state/gap925.py` 를 **안 고친다**.

사용: python3 runners/thr939_run.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import pairboot            # noqa: E402
from state import gate939           # noqa: E402

OUT = ROOT / "runners/out939_threshold.json"
PREREG = ROOT / "docs/prereg_939_threshold.md"
STAMP = ROOT / "runners/out939_prereg_stamp.json"

P935 = ["① 원판 전량", "② 원판 − b_prv=−1 칸", "진단 b_prv=−1 칸만"]
P_MAIN = P935[0]
OLD_THR = 0.05                      # perm922.COMPARABLE_REL — 🔴 안 고친다
X_ADOPT = 1.0                       # 채택 크기(일) — docs/목표.md 표 ③
BOOT_B, BOOT_SEED = 10_000, 939
CARD = Path("/Users/ax/.claude/projects/-Users-ax-world-model/memory/"
            "project-lab-state.md")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jload(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════ 0 · 사전등록 시각 증거
def part0() -> dict:
    st = json.loads(STAMP.read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.timezone.utc)
    def git(*a):
        return subprocess.run(["git", "-C", str(ROOT), *a],
                              capture_output=True, text=True).stdout.strip()
    return {
        "stamp": str(STAMP.relative_to(ROOT)),
        "stamp 이 박은 사전등록 sha256":
            st["파일별 sha256·mtime"]["docs/prereg_939_threshold.md"]["sha256"],
        "사전등록 sha256(지금 다시 계산)": sha(PREREG),
        "🔴 같은가": (st["파일별 sha256·mtime"]["docs/prereg_939_threshold.md"]["sha256"]
                 == sha(PREREG)),
        "stamp 를 쓴 시각(UTC)": st["이 stamp 를 쓴 시각(UTC)"],
        "측정 시작(UTC)": now.isoformat(),
        "🔴 stamp 가 측정보다 먼저인가":
            dt.datetime.fromisoformat(st["이 stamp 를 쓴 시각(UTC)"]) < now,
        "🔴 사전등록만 담은 커밋": git("log", "--oneline", "-1", "--", str(PREREG)),
        "🔴 그 커밋에 측정 러너가 들어 있나":
            "runners/thr939_run.py" in git("show", "--name-only", "--pretty=format:",
                                           "ffd6f9b79"),
        "🔴 os.utime 을 썼나": False,
        "🔴 남의 파일이 안 바뀌었나(스탬프 대조)": {
            f: {"stamp": r["sha256"], "지금": sha(ROOT / f),
                "같은가": r["sha256"] == sha(ROOT / f)}
            for f, r in st["🔴 남의 파일(읽기만 · 측정 뒤 대조한다)"].items()},
    }


# ══════════════════════════════════════════════════════ A · 문턱을 자료에서
def slope_bca(x: np.ndarray, y: np.ndarray) -> dict:
    def stat(idx, x=x, y=y):
        xi, yi = x[idx], y[idx]
        xm = xi.mean()
        den = float(((xi - xm) ** 2).sum())
        if den <= 0:
            return float("nan")
        return float(((xi - xm) * (yi - yi.mean())).sum() / den)
    cl, cinfo = pairboot.solo_clusters(len(x))
    th, lo, hi, kind = pairboot.cluster_boot(stat, cl, B=BOOT_B, seed=BOOT_SEED)
    return {"기울기": th, "BCa 95%": [lo, hi], "구간 종류": kind,
            "🔴 폴백 사유(규약 47)": None if kind == "BCa" else kind,
            "군집 병기": cinfo, "판정": pairboot.verdict(lo, hi)}


def part_A() -> dict:
    d935 = jload("runners/out935_rawpanel.json")
    recs = d935["⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다"]["기록"]
    real_mae = d935["② 항등 검사 (사전등록 §7-2·§7-4)"]["진짜 기준·시험 팔 MAE"]
    verdicts = d935["⑥ 🔴 판정용 순열"]

    out: dict = {
        "무엇": "🔴 비교가능성 문턱을 **자료에서** 정한다 — 사전등록 §A 의 공식 그대로",
        "🔴 A-1 출처 추적": {
            "찾았나": "🔴 **찾았다**(「못 찾았다」가 아니다 — 조항 59)",
            "출처 ①": "docs/prereg_922_permfix.md:95 — 「5% 는 지금 박는다. 결과를 보고 "
                   "고치지 않는다. (근거: **#175 가 예로 든 수.** 옛 귀무는 19.319% 로 이 "
                   "문턱을 네 배 넘는다 — 즉 이 문턱은 실제로 무엇을 걸러낸 적이 있다.)」",
            "출처 ②": "이슈 #175 51줄 — 「두 세계의 기후값 MAE 차가 **문턱(예: 5%)** 안인지를 "
                   "검사하고, …」",
            "🔴 그래서 0.05 의 근거는 무엇인가":
                "**예시 수 하나다.** 「옛 귀무가 19.319% 로 네 배 넘는다」는 **문턱이 무엇을 "
                "걸러낸 적이 있다는 사후 확인**이지 크기의 근거가 아니다 — 19.319% 를 "
                "걸러내는 문턱은 0.05 말고도 무한히 많다",
            "🔴 저장소가 같은 수를 이미 거부한 적이 있다":
                "docs/목표.md:140 채택 크기 표 ③ — 「병기 후보: **기준 MAE 의 5% = 0.519일**"
                "(**출처가 관례뿐이라 안 씀**)」. 🔴 **같은 축의 5% 를 크기로 쓰는 것을 928 이 "
                "명시로 거부했는데, 관문의 문턱은 그 거부된 수 그 자체다**",
        },
        "🔴 A-2 「비교 불가」의 정의(관례 상수 0개)":
            "기준 팔 차이 **하나만으로** 그 뽑기의 개선이 진짜를 넘어설 수 있을 때. "
            "판정이 순위 검정이므로 자격을 잃는 지점은 **순위를 뒤집을 수 있는 지점**이다",
        "🔴 A-3 공식": "T = G / (L_used × cr) · G = min_i(R − y_i) · L_used = max(1.0, BCa 상한)",
    }

    per = {}
    for p in P935:
        y = np.asarray([r[p]["개선(일)"] for r in recs], float)
        x = np.asarray([r[p]["기준 팔 MAE"] for r in recs], float)
        xt = np.asarray([r[p]["시험 팔 MAE"] for r in recs], float)
        cr = float(real_mae[p]["기준"])
        R = float(verdicts[p]["진짜"])
        G = float((R - y).min())
        sl = slope_bca(x, y)
        L_used = max(1.0, float(sl["BCa 95%"][1]))
        ok = G > 0
        T = (G / (L_used * cr)) if ok else None
        per[p] = {
            "cr 진짜 기준 팔 MAE(일)": cr,
            "R 진짜 개선(일)": R,
            "귀무 개선 최대(일)": float(y.max()),
            "🔴 G 빈틈 = min(R − y_i)(일)": G,
            "🔴 G > 0 인가": ok,
            "전달률 L(개선 ~ 기준 팔 MAE 의 OLS 기울기 · 규약 47 BCa)": sl,
            "🔴 L_used = max(1.0, BCa 상한)": L_used,
            "🔴🔴 T = G/(L_used·cr)": T,
            "병기 T_X (X=1.0일 채택 크기)": (X_ADOPT / (L_used * cr)),
            "병기 T_SD (귀무 개선 SD)": float(y.std(ddof=1)) / (L_used * cr),
            "🔴 개선 = 기준 − 시험 인가(L 해석의 근거)": {
                "|차| > 1e-12 인 뽑기": int((np.abs(y - (x - xt)) > 1e-12).sum()),
                "최대 차": float(np.abs(y - (x - xt)).max()),
                "🔴 뜻": "부동소수 마지막 비트 말고는 정확히 성립한다 — 그래서 기준 팔이 "
                      "1일 나빠지면 시험 팔이 안 따라올 때 개선이 정확히 1일 커진다"},
            "🔴 병기 — L=1 로 고정하면 T": G / cr if ok else None,
            "🔴 옛 문턱 0.05 가 허용하던 왜곡(일) = 0.05·L_used·cr": OLD_THR * L_used * cr,
            "🔴 그 왜곡은 G 의 몇 배인가": (OLD_THR * L_used * cr) / G if ok else None,
            "🔴 그 왜곡은 채택 크기 1.0일의 몇 배인가": (OLD_THR * L_used * cr) / X_ADOPT,
            "상대차 실측(최소·최대)": [float(np.min([r[p]["비교가능성 상대차"] for r in recs])),
                              float(np.max([r[p]["비교가능성 상대차"] for r in recs]))],
        }
    out["팔별"] = per

    Ts = [per[p]["🔴🔴 T = G/(L_used·cr)"] for p in P935]
    spread = max(Ts) / min(Ts)
    T_main = per[P_MAIN]["🔴🔴 T = G/(L_used·cr)"]
    out["🔴🔴 A-4 판정"] = {
        "🔴 정본 팔": P_MAIN,
        "🔴🔴 자료가 정한 문턱 T": T_main,
        "옛 문턱": OLD_THR,
        "T ÷ 옛 문턱": T_main / OLD_THR,
        "세 팔의 T": dict(zip(P935, Ts)),
        "🔴 세 팔의 T 가 몇 배 갈리나": spread,
        "🔴 (ㄷ) 조건(10배 넘게 갈리면 「상수가 아니다」)": bool(spread > 10),
        "🔴 정했나": ("**정했다**" if all(per[p]["🔴 G > 0 인가"] for p in P935) and spread <= 10
                 else "🔴 **못 정했다** — 사전등록 §A-4-2 의 갈래를 보라"),
        "🔴 미리 적은 예상의 채점(사전등록 §A-4-4)": {
            "예상한 T": "≈ 0.033",
            "실측 T": T_main,
            "🔴 예상이 맞았나(0.030~0.036 안인가)": bool(0.030 <= T_main <= 0.036),
            "🔴 왜 틀렸나": {
                "예상은 L_used = 1 을 깔고 있었다": per[P_MAIN]["🔴 병기 — L=1 로 고정하면 T"],
                "실측 L 의 BCa 상한": per[P_MAIN]["🔴 L_used = max(1.0, BCa 상한)"],
                "🔴 뜻": "**예상한 0.033 은 L=1 판의 값이었다.** 전달률의 BCa 가 "
                      "[−0.94, +2.17] 로 **판정 불능**이고 사전등록이 「상한을 쓴다」고 "
                      "박아 뒀으므로 T 가 그 절반 아래로 내려갔다. 🔴 **예상은 틀렸고, "
                      "규칙은 지켰다**"},
            "예상 ②: 판① 은 새 문턱에서도 0/200": None,   # A-5 에서 채운다
            "예상 ③: 판② 는 처음으로 걸리는 뽑기가 생긴다": None,
        },
    }
    return out, per, recs, T_main


# ══════════════════════════════════════════════════════ A-5 · 관문 재계수
def part_A5(per: dict, recs: list, T: float) -> dict:
    d933 = jload("runners/out933_calpanel.json")
    d925 = jload("runners/out925_gapsplit.json")
    r933 = d933["⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다"]["기록"]
    rel933 = [r["비교가능성 상대차"] for r in r933]
    g2 = d925["⑥ 관문 신고 (#178) — 🔴 관문마다 도달 가능 폭 ÷ 문턱"]["G2"]

    arms = {f"935 {p}": [r[p]["비교가능성 상대차"] for r in recs] for p in P935}
    arms["933 전량(판 하나 · 상대차는 뽑기마다 하나)"] = rel933
    arms["925 G2(뽑기 하나 — B=1)"] = [g2["실측"]]

    rep = {}
    for name, vals in arms.items():
        rep[name] = {
            "옛 문턱 0.05": gate939.gate_report_939(
                name, axis="기후값 MAE 상대차", threshold=OLD_THR, values=vals,
                note="🔴 규약 48 재개정판 문안으로 다시 낸다(금지어 둘을 안 쓴다)"),
            "🔴 새 문턱 T": gate939.gate_report_939(
                name, axis="기후값 MAE 상대차", threshold=T, values=vals,
                note="🔴 자료가 정한 문턱(사전등록 §A-3)"),
        }
    tot_old = sum(rep[n]["옛 문턱 0.05"]["🔴 걸린 뽑기 k"] for n in rep)
    tot_new = sum(rep[n]["🔴 새 문턱 T"]["🔴 걸린 뽑기 k"] for n in rep)
    arms_new = [n for n in rep if rep[n]["🔴 새 문턱 T"]["🔴 걸린 뽑기 k"] > 0]
    return {
        "무엇": "🔴 925~935 의 비교가능성 관문을 **두 문턱으로** 다시 센다(사전등록 §A-5)",
        "🔴 새 문턱 T": T,
        "팔별": rep,
        "🔴🔴 몇 개나 걸리나": {
            "옛 문턱에서 걸린 뽑기 합": tot_old,
            "🔴 새 문턱에서 걸린 뽑기 합": tot_new,
            "🔴 새 문턱에서 걸리는 팔": arms_new,
            "팔 수(분모)": len(rep),
        },
        "⚠ 925 G2 는 뽑기가 하나다": "925 는 N2 를 한 판만 냈다 — B=1 이라 u 가 크다. "
                            "뽑기 수를 같이 읽어라(조항 60)",
    }


# ══════════════════════════════════════════════════════ B · 규약 48 소급
def part_B() -> dict:
    words = ["통과", "검정력 0"]
    gate_marks = ("관문", "비교가능성", "gate", "도달 가능", "문턱")
    WIN = 8   # 🔴 사전등록의 「그 줄이 속한 키」를 .md 에서는 **앞 8줄 창**으로 구현한다
    # 🔴 `-z` 로 읽는다 — 기본 `ls-files` 는 한글 경로를 8진 이스케이프로 감싸서
    #    `docs/목표.md` 가 목록에서 조용히 빠진다(이 러너의 첫 판이 그렇게 틀렸다)
    files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                           capture_output=True, text=True).stdout.split("\0")
    files = [f for f in files if f.endswith((".md", ".json", ".py", ".html"))]
    hits = {w: {} for w in words}
    for f in files:
        p = ROOT / f
        try:
            if not p.exists() or p.stat().st_size > 20_000_000:
                continue
            txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = txt.split("\n")
        for i, line in enumerate(lines, 1):
            for w in words:
                if w in line:
                    win = "\n".join(lines[max(0, i - 1 - WIN):i])
                    ctx = any(m in win for m in gate_marks)
                    hits[w].setdefault(f, []).append(
                        {"줄": i, "관문 문맥": ctx,
                         "줄 자체에 표지가 있나": any(m in line for m in gate_marks)})
    # 인계 카드(저장소 밖 · 다음 세션이 읽는 정본)
    card_hits = {w: [] for w in words}
    if CARD.exists():
        clines = CARD.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(clines, 1):
            for w in words:
                if w in line:
                    win = "\n".join(clines[max(0, i - 1 - WIN):i])
                    card_hits[w].append({"줄": i,
                                         "관문 문맥": any(m in win for m in gate_marks)})

    def group(f: str) -> str:
        if f.startswith("docs/prereg_"):
            return "docs/prereg_*(🔴 증거물 — 안 고친다)"
        if f.startswith("docs/"):
            return "docs/(살아 있는 정본 — 고친다)"
        if f.startswith("runners/out"):
            return "runners/out*.json(🔴 증거물 — 안 고친다)"
        if f.endswith(".py"):
            return "코드(.py — 이번엔 안 고친다)"
        return "그 밖"

    summ = {}
    for w in words:
        g = {}
        for f, lst in hits[w].items():
            k = group(f)
            g.setdefault(k, {"파일": 0, "줄": 0, "관문 문맥 줄": 0})
            g[k]["파일"] += 1
            g[k]["줄"] += len(lst)
            g[k]["관문 문맥 줄"] += sum(1 for x in lst if x["관문 문맥"])
        summ[w] = {
            "갈래별": g,
            "전체 줄": sum(len(v) for v in hits[w].values()),
            "전체 파일": len(hits[w]),
            "🔴 관문 문맥 줄(규약 48 의 대상)":
                sum(1 for v in hits[w].values() for x in v if x["관문 문맥"]),
            "인계 카드": {"줄": len(card_hits[w]),
                     "관문 문맥": sum(1 for x in card_hits[w] if x["관문 문맥"])},
        }
    live = {w: {f: [x for x in lst if x["관문 문맥"]]
                for f, lst in hits[w].items()
                if group(f) == "docs/(살아 있는 정본 — 고친다)"
                and any(x["관문 문맥"] for x in lst)} for w in words}
    return {
        "무엇": "🔴 「통과」·「검정력 0」을 **저장소 전수로** 세고, 살아 있는 정본만 고친다",
        "세는 규칙": "줄에 낱말이 있고, **그 줄 또는 앞 8줄**에 관문|비교가능성|gate|"
                "도달 가능|문턱 중 하나가 있으면 **관문 문맥**(규약 48 의 대상)",
        "🔴 자백 — 이 러너의 첫 판이 틀렸다": [
            "① `git ls-files` 가 한글 경로를 8진 이스케이프로 감싸서 **`docs/목표.md` 가 "
            "목록에서 조용히 빠졌다**. `-z` 로 고쳤다",
            "② 문맥을 **줄 단위**로만 봐서 `목표.md` 의 관문 표(줄 187·188)를 놓쳤다. "
            "사전등록이 적은 「그 줄이 속한 키」를 .md 에서는 **앞 8줄 창**으로 구현했다",
        ],
        "요약": summ,
        "🔴 고칠 자리(살아 있는 정본의 관문 문맥 줄)": live,
        "🔴 안 고치는 것과 이유": {
            "runners/out*.json": "증거물이다(docs/두갈래.md:37) — **세어서 신고만** 한다",
            "docs/prereg_*.md": "🔴 **사전등록도 증거물이다.** 소급 수정은 「측정 전에 박았다」는 "
                             "성질 자체를 없앤다 — 지시서의 '문서'를 나는 이렇게 좁혔고 "
                             "이유를 사전등록 §B-2 에 미리 적었다",
            "state/gap925.py:gate_report": "🔴 필드 이름 「🔴 검정력 0 인가(비 < 1 이면 자동)」가 "
                                        "규약 48 재개정판이 **거짓이라 판정한 딱지**를 찍는다. "
                                        "이름을 고치면 그것을 읽는 933·935·937 러너가 재실행 때 "
                                        "깨진다 → **새 함수 `state/gate939.gate_report_939`** 를 "
                                        "두고 옛 함수는 **이슈로 낸다**",
        },
    }


# ══════════════════════════════════════════════════════ C · 배선 회계
UNPLANT_935 = [
    {"무엇": "interval918 · perm922 · gap925 의 관 자체가 옳은가",
     "갈래": "㉮", "증거": None,
     "⚠ 부분 증거": "925 ③ 은 `gap925.permute_gaps(plant_identity=True)` 로 **관의 한 함수에** "
                "항등을 심었다 — 그러나 「관 자체가 옳은가」는 그보다 넓다"},
    {"무엇": "daily.npz 가 옳게 만들어졌는가", "갈래": "㉯",
     "증거": "runners/out937_repair.json A — 원천 zip 19개에서 56.8초에 다시 만들어 "
           "sha 4472b7f6…97b2 가 바이트로 같았다(티처 #78 이 58.0초로 재확인)",
     "🔴 뜻": "**심을 수 있었는데 안 심었다** — 분모에 남는다(티처 #78 M2)"},
    {"무엇": "N2(간격순서 순열)가 이 물음의 옳은 귀무인가", "갈래": "㉮", "증거": None},
]
UNPLANT_933 = UNPLANT_935 + [
    {"무엇": "경계 강제 판이 「순서의 몫」을 옳게 가르는가 — 부호를 못 정한다",
     "갈래": "㉯",
     "증거": "runners/out935_rawpanel.json ⑥-다 ㉠ 이 **200/200 으로 부호를 정했다**"
           "(티처 #76 도 오른 144·내린 53·같은 3 으로 쟀다)",
     "🔴 뜻": "정할 수 있는 것이었다 — 분모에 남는다"},
]


def part_C() -> dict:
    d935 = jload("runners/out935_rawpanel.json")
    d933 = jload("runners/out933_calpanel.json")
    k935 = [k for k in d935 if k.startswith("③ 배선")][0]
    k933 = [k for k in d933 if k.startswith("③ 배선")][0]
    a935 = gate939.account_939(d935[k935]["검사"], UNPLANT_935)
    a933 = gate939.account_939(d933[k933]["검사"], UNPLANT_933)

    hist = [
        {"언제": "933 정본", "출처": "runners/out933_calpanel.json ③",
         "심음": 6, "발화": 5, "눈금 ㄱ": "5/6 = 0.833", "둘째 눈금": "5/10 = 0.500",
         "분모 정의": "심음 6 + 못 심은 4", "무엇이 틀렸나": "W8(대조)과 W3(항등)을 심음으로 셌다"},
        {"언제": "논문 497·원장·카드", "출처": "티처 #76 C1 이 잡았다",
         "심음": 6, "발화": 6, "눈금 ㄱ": "6/6 = 1.000", "둘째 눈금": "6/10 = 0.600",
         "분모 정의": "같음", "무엇이 틀렸나": "🔴 **연습 주행(4뽑기)의 수를 본 주행 자리에 옮겼다**"},
        {"언제": "티처 #76 C1", "출처": "runners/out934_teacher.json",
         "심음": 5, "발화": 5, "눈금 ㄱ": "5/5 = 1.000", "둘째 눈금": "5/8 = 0.625",
         "분모 정의": "심음 5 + 못 심은 3", "무엇이 틀렸나": "W3(항등)이 아직 심음이다"},
        {"언제": "937 B", "출처": "runners/out937_repair.json B",
         "심음": 5, "발화": 5, "눈금 ㄱ": "5/5 = 1.000", "둘째 눈금": "5/8 = 0.625",
         "분모 정의": "심음 5 + 못 심은 3(🔴 daily.npz 를 분모에서 뺐다)",
         "무엇이 틀렸나": "W3 오분류 + 🔴 **분모를 자기에게 유리하게 줄였다**(티처 #78 M2)"},
        {"언제": "티처 #78 C4", "출처": "runners/out938_teacher.json C4",
         "심음": 4, "발화": 4, "눈금 ㄱ": "4/4 = 1.000", "둘째 눈금": "4/8 = 0.500",
         "분모 정의": "🔴 **안 적혀 있다** — 심음 4 + 못 심은 4 면 8 이지만 그 사이클의 "
                  "못 심은 것은 3 이었다",
         "무엇이 틀렸나": "🔴 **같은 파일 M2 가 「4/9」라고 다르게 적는다**"},
        {"언제": "🔴 939(이 산출물)", "출처": "runners/out939_threshold.json C",
         "심음": a933["심은 수"], "발화": a933["발화한 수"],
         "눈금 ㄱ": a933["🔴 눈금 ㄱ — 심은 것 기준"],
         "둘째 눈금": a933["🔴🔴 눈금 ㄴ(정본) — 못 심은 것 **전량**까지 분모에"],
         "분모 정의": f"심음 {a933['심은 수']} + 못 심은 것 전량 {a933['못 심은 수(전량)']} "
                  f"(🔴 daily.npz 를 **되돌려 놓았다**)",
         "무엇이 틀렸나": "—"},
    ]
    return {
        "무엇": "🔴 배선 분류를 **값으로** 다시 한다(티처 #78 C4·M2) — 이름도 접두어도 안 본다",
        "935": a935, "933": a933,
        "🔴🔴 933 회계의 이력 — 몇 번 다른 값이 나왔나": {
            "표": hist,
            "🔴 서로 다른 값의 가짓수(눈금 ㄱ 기준)":
                len({h["눈금 ㄱ"] for h in hist}),
            "🔴 서로 다른 값의 가짓수(둘째 눈금 기준)":
                len({h["둘째 눈금"] for h in hist}),
        },
        "🔴 티처 #78 의 두 수를 검산한다": {
            "C4 가 적은 값": "4/8 = 0.500",
            "M2 가 적은 값": "4/9 = 0.444",
            "🔴 내가 센 값": a933["🔴🔴 눈금 ㄴ(정본) — 못 심은 것 **전량**까지 분모에"],
            "🔴 왜 갈리나": "M2 는 937 의 분모 9(심음 5 + 못 심은 4)를 **그대로 두고** 분자만 "
                     "4 로 내렸다. C4 를 함께 적용하면 심음이 5→4 로 줄어 **분모도 9→8** 이 "
                     "된다. 🔴 **티처의 두 수 중 어느 것도 러너가 센 값이 아니다**",
        },
        "🔴 M2 — 「못 심은 것」을 갈랐다": {
            "규칙": "㉯ ⟺ 저장소에 그 주입을 **실제로 잰 산출물**이 있다(파일:필드를 인용한다)",
            "935": {"㉮": [u["무엇"] for u in UNPLANT_935 if u["갈래"] == "㉮"],
                   "㉯": [u["무엇"] for u in UNPLANT_935 if u["갈래"] == "㉯"]},
            "933": {"㉮": [u["무엇"] for u in UNPLANT_933 if u["갈래"] == "㉮"],
                   "㉯": [u["무엇"] for u in UNPLANT_933 if u["갈래"] == "㉯"]},
            "🔴 937 이 뺀 것": "daily.npz(㉯) — **㉯ 를 뺐으므로 눈금 ㄷ 보다도 유리한 축소였다**",
        },
    }


def main() -> None:
    t0 = dt.datetime.now(dt.timezone.utc)
    A, per, recs, T = part_A()
    A5 = part_A5(per, recs, T)
    # 예상 채점을 채운다(사전등록 §A-4-4)
    k1 = A5["팔별"][f"935 {P935[0]}"]["🔴 새 문턱 T"]["🔴 걸린 뽑기 k"]
    k2 = A5["팔별"][f"935 {P935[1]}"]["🔴 새 문턱 T"]["🔴 걸린 뽑기 k"]
    g = A["🔴🔴 A-4 판정"]["🔴 미리 적은 예상의 채점(사전등록 §A-4-4)"]
    g["예상 ②: 판① 은 새 문턱에서도 0/200"] = {"실측 k": k1, "🔴 맞았나": k1 == 0}
    g["예상 ③: 판② 는 처음으로 걸리는 뽑기가 생긴다"] = {"실측 k": k2, "🔴 맞았나": k2 > 0}

    out = {
        "팔": "939-ㄱ — 🔴 **비교가능성 문턱을 자료에서 정한다** · 규약 48 소급 · 배선 분류를 값으로",
        "사전등록": "docs/prereg_939_threshold.md",
        "티처": "runners/out938_teacher.json (#78) 의 1·2·3·4순위",
        "🔴 판 ρ": "안 쓴다(지시)",
        "🔴 이 사이클에 크기 판정이 없다":
            "새 팔을 안 쟀다 — 규율 4 의 X · Y_상한 · Y_도달 · Z 전부 **해당 없음**(빈칸 아님). "
            "병기: 935 네 판의 Z_self 1.1553 / 2.1345 / 3.0452 / 4.587 — 넷 다 1 초과",
        "🔴 사전등록 시각 증거": part0(),
        "코드 sha256": {f: sha(ROOT / f) for f in
                      ["state/gate939.py", "runners/thr939_run.py",
                       "runners/thr939_stamp.py", "state/perm922.py", "state/gap925.py"]},
        "🔴 이 러너가 안 한 것": [
            "새 순열 뽑기 — 200기록을 **읽어서** 다시 셌다",
            "산출물 수정 0 — `runners/out*.json` 을 읽기만 했다",
            "`state/perm922.py`·`state/gap925.py` 수정 0",
            "🔴 `b_prv=−1` 칸의 새 귀무 — 지시대로 안 건드렸다(이슈 #187)",
        ],
        "A · 문턱": A,
        "A-5 · 관문 재계수": A5,
        "B · 규약 48 소급": part_B(),
        "C · 배선 회계": part_C(),
        "시작 UTC": t0.isoformat(),
    }
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat()
    out["초"] = (dt.datetime.fromisoformat(out["끝 UTC"]) - t0).total_seconds()
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT, out["초"], "초")
    print("T =", T, " k(판①) =", k1, " k(판②) =", k2)


if __name__ == "__main__":
    main()
