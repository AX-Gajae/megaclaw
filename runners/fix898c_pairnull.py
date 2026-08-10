"""노트 898 · 수리 C — 🔴 **897 의 판정을 나르는 세 수를 다시 잰다**(이슈 #120 · 티처 #60).

세 수가 각각 이런 자리에 서 있었다:

    「표현은 1열보다 4.5배」   분모(1열 팔)가 **F4 로 무효**인데 안 적혔다     → C7
    「ΔS = 널 2σ 의 0.24배」   ΔS 자신의 널을 안 뽑고 **각 팔의 S 널을 빌렸다** → M1
    「17.6배 · 25년치」        **사후 부분집합**(퇴화 제외)의 수인데 판정에 썼다 → M2

여기서 하는 넷:

    ㄱ  C7 재계산 — 위약 max|S| ÷ 진짜 |S| 를 **두 팔 다** 세고 F4 를 다시 판정한다
        (`out897_placebo.json` · `out897_decay.json` 을 **읽어서** 센다 — 손 전사 금지)
    ㄴ  M1 짝 널 — 🔴 **같은 라벨 순열을 ㅂ-1 과 ㅂ-2 에 동시에** 먹여 **ΔS 자신의 널**을
        1,000 뽑기(씨앗 897)로 뽑는다. 사전등록 문면: *"널을 직접 뽑는다 — 남의 문턱을
        안 빌린다"*. 897 은 그 문면을 적어 놓고 **ΔS 에는 안 지켰다**
    ㄷ  M2 — 필요 군집을 **전 도메인(사전등록)** 과 **퇴화 제외(사후)** 둘 다 낸다.
        897 은 사후 쪽만 헤드라인에 실었고 그 쪽이 **덜 유리하다**
    ㄹ  M3 — 「날짜 한 열」의 S 가 같은 사이클에 0.10028 / 0.06823 / 0.11491 세 값을 낸 이유.
        🔴 진단은 **S 의 `sign(ρ_학습)` 이 추정기에 따라 뒤집히는 것**이다
    ㅁ  C8 — 「사다리를 장 학습 과제로」 권고를 **날짜 군집 552** 로 다시 계산한다.
        897 의 헤드라인 발견(잡음의 단위 = 날짜 군집)을 897 의 권고에 적용하면 권고가 선다/무너진다

🔴 `decay897.py` · `ctl897.py` · `ctl897b.py` 는 **안 고친다**(동결물). 읽어서 부른다.

쓰는 법::

    python3 -m runners.fix898c_pairnull > runners/out898c_fix.log 2>&1
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")

from runners import decay897 as D           # noqa: E402

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()
OUT = ROOT / "runners/out898c_fix.json"

PERM = 1000
PERM_SEED = 897          # 897 과 같은 씨앗 — 비교 가능하게
F4_THRESH = 0.5          # 사전등록 문면: 위약 |S| 중 하나라도 진짜 |S| 의 0.5배 이상


def stamp() -> dict:
    """🔴 내 파일의 sha 는 내가 박는다(티처 #59 M7)."""
    h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                       capture_output=True, text=True).stdout.strip()
    return {"git HEAD": h, "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "코드 sha(fix898c_pairnull.py)":
                hashlib.sha256(ME.read_bytes()).hexdigest()[:16],
            "코드 sha(decay897.py)":
                hashlib.sha256((ROOT / "runners/decay897.py").read_bytes()).hexdigest()[:16],
            "scipy": __import__("scipy").__version__, "numpy": np.__version__}


# ── ㄱ · C7 — F4 를 두 팔 다 센다 ────────────────────────────────────────
def c7_f4() -> dict:
    """🔴 티처의 표를 믿지 않고 산출물에서 직접 센다."""
    pl = json.loads((ROOT / "runners/out897_placebo.json").read_text())
    dc = json.loads((ROOT / "runners/out897_decay.json").read_text())
    res = {"🔴 사전등록 F4 문면": "위약 팔의 |S| 중 하나라도 진짜 |S| 의 **0.5배 이상** → "
                              "🔴 잰 것이 장이 아니라 표본 구성이다 — **팔 전체 무효** "
                              "(docs/prereg_897_architecture.md §2 판정 규칙 표)",
           "위약 씨앗": [a["태그"] for a in pl["팔"]], "팔": {}}
    for arm in ("1열", "표현"):
        ss = [a[arm]["헤드라인 S"] for a in pl["팔"]]
        mx = max(abs(s) for s in ss)
        real = dc["진짜"][arm]["헤드라인 S"]
        ratio = mx / abs(real)
        res["팔"][arm] = {
            "위약 S 셋": ss, "max|S|(위약)": round(mx, 5),
            "진짜 S": real, "비 = max|S| ÷ |진짜|": round(ratio, 4),
            "F4(≥0.5)": "🔴 발동 — 팔 전체 무효" if ratio >= F4_THRESH else "미발동",
            "897 이 적었나": ("적혀 있다(주장 12)" if arm == "표현"
                          else "🔴 **어디에도 없다** — 원장·논문·PR 전부"),
        }
    a, b = res["팔"]["1열"], res["팔"]["표현"]
    res["🔴 헤드라인 「4.5배」"] = {
        "값": round(abs(b["진짜 S"]) / abs(a["진짜 S"]), 4),
        "분자": f'표현 {b["진짜 S"]} — F4 {b["F4(≥0.5)"]}',
        "분모": f'1열 {a["진짜 S"]} — F4 {a["F4(≥0.5)"]}',
        "판정": "🔴 **못 쓴다.** F4 문면이 '팔 전체 무효' 이므로 무효 팔의 S 로 만든 비는 "
              "분자도 분모도 서 있지 않다. 게다가 1열 팔의 비(1.14)가 표현 팔(0.53)보다 "
              "**두 배 이상 세게** 발동한다 — 대조 팔이 더 심하게 무효다",
    }
    # 🔴 1단계 재판정 — F4 를 둘 다 적고 나서
    n1 = dc["진짜"]["1열"]["순열 널"]
    n8 = dc["진짜"]["표현"]["순열 널"]
    res["🔴 1단계 재판정(F4 둘 다 적고)"] = {
        "① F4 는 두 팔 다 발동한다": "1열 1.142 · 표현 0.534 — **문면대로면 1단계에 남는 팔이 없다.** "
                             "F1·F2·F3 은 전부 S(표현) 에 걸린 조건인데 그 팔이 무효이므로 **채점 자체가 성립 안 한다**",
        "② 897 의 판정문": "*'어느 규칙도 발동하지 않았고(구멍) 위약 규칙은 과잉 발동했다'* — "
                     "🔴 **틀린 곳은 「과잉 발동」의 범위다.** 한 팔이 아니라 **두 팔 다** 발동했다",
        "③ 🔴 그런데 F4 는 널 안인 팔에서 **산술적으로** 발동한다": {
            "1열 팔": f'S {dc["진짜"]["1열"]["헤드라인 S"]} · 자기 순열 널 SD {n1["널 SD"]} · '
                   f'2σ {n1["널 2σ"]} → **자기 널 안**(|S|/SD = '
                   f'{round(abs(dc["진짜"]["1열"]["헤드라인 S"]) / n1["널 SD"], 2)}σ)',
            "표현 팔": f'S {dc["진짜"]["표현"]["헤드라인 S"]} · 널 SD {n8["널 SD"]} → '
                   f'{round(abs(dc["진짜"]["표현"]["헤드라인 S"]) / n8["널 SD"], 2)}σ 밖',
            "🔴 뜻": "위약의 흩어짐은 널 폭과 같은 자릿수다(≈0.021 대 0.0163~0.0165). 그러면 "
                  "**진짜 |S| 가 자기 널 안인 팔은 max|위약 S| ÷ |진짜 S| ≥ 0.5 가 거의 확실**하다 — "
                  "F4 는 *'표본 구성을 쟀다'* 를 진단하는 것이 아니라 **'이 팔에 신호가 없다'** 를 "
                  "비율로 되풀이한다. 1열 팔의 1.142 가 정확히 그 경우다. "
                  "즉 **대조 팔의 F4 는 새 결함이 아니라 대조 팔이 널 안이라는 사실의 다른 표현**이고, "
                  "🔴 **못 쓰게 되는 것은 그 팔을 분모로 쓴 비**다",
        },
        "④ 🔴 다시 쓴 1단계 판정문": "**1단계는 사전등록 규칙으로 아무것도 판정하지 못했다.** "
                          "ⓐ F4 가 두 팔 다 발동해 팔이 남지 않는다 ⓑ F4 자체가 널 안인 팔에서 "
                          "산술적으로 발동하도록 잘못 적혔다 ⓒ F1~F3 은 실측이 떨어진 자리(널 밖 + BCa 가 0 을 뭄)를 "
                          "안 덮는다(756 의 구멍, 세 번째). **셋이 겹쳐 1단계는 판정 불능이다.** "
                          "🔴 살아남는 사실은 **팔 안의 값** 둘뿐이다 — 표현 팔은 자기 순열 널 밖(3.1σ)이지만 "
                          "**날짜 군집 BCa [−0.00553,+0.13432] 가 0 을 물어 판정 불능**이고, 1열 팔은 자기 널 안이다. "
                          "**「4.5배」는 철회한다.**",
        "⑤ 2단계를 안 여는 결정은 서나": "🔴 **결론은 서는데 근거가 바뀐다.** 사전등록 팔이 판정 불능이므로 "
                            "*'표현 수준에서도 0 이라 안 연다'*(F1) 라고 말할 수 없다. 안 여는 근거는 "
                            "**판정력 계산 하나**로 좁아지고, 그 계산은 **사후 진단 팔(시각 통제)** 위에 서 있다. "
                            "그러므로 정확한 문장은 *'표현 수준에서 0 이었다'* 가 아니라 "
                            "**'이 자리에서는 판정할 수 없고, 필요 군집이 현재의 5.2배(사전등록 전 도메인)라 "
                            "지금 열면 널 안에서 만난다'** 이다",
    }
    res["🔴 주장 5·12 충돌 해소"] = {
        "충돌": "주장 5(표현은 1열보다 4.5배 — 1열로 눌러서 잃는 것이 실재한다) 대 "
              "주장 12(F4 는 규칙대로 발동시켜 팔을 무효로 적는다). 같은 팔이 실재의 근거이자 무효",
        "해소": "🔴 **주장 12 가 이긴다 — 규칙이 먼저 적혔기 때문이다.** F4 는 사전등록 문면이고 "
              "주장 5 는 그 규칙이 무효로 만든 팔에서 뽑은 비다. 사전등록 규칙과 사후 해석이 "
              "부딪히면 사전등록이 이긴다(노트 133 · 규약 47 의 정신). 그러므로 주장 5 는 "
              "**철회**하고, 「4.5배」는 판정에서 뺀다",
        "그러나 규칙 자체는 틀렸다(897 이 이미 적었다 · 유지한다)": "F4 를 발동시킨 것은 "
              "**음수 위약**이고 음의 방향으로 큰 위약은 교란이 아니라 **널 폭**이다. 문턱은 |S| 가 "
              "아니라 **부호 맞춘 S** 또는 **위약 SD 대비 z** 로 적었어야 하고 뽑기 셋으로 SD 를 "
              "재는 것 자체가 얇다. 🔴 **그래도 사후에 규칙을 고쳐 살리지 않는다** — 고친 규칙은 "
              "다음 사이클에 **사전등록해서** 쓴다",
    }
    return res


# ── ㄴ · M1 짝 널 ────────────────────────────────────────────────────────
def arm_tab(rs, rows, F, drop_degenerate: bool):
    """`ctl897b.arm` 과 같은 표를 만든다(그 파일은 안 고친다 — 논리만 옮긴다)."""
    r2 = dict(rs)
    r2["F"] = F
    r2["one"] = np.arange(len(rs["yrs"]), dtype=float)
    tab = D.table(r2, rows)
    per = D.measure(tab)
    if drop_degenerate:
        bad = [dm for dm, p in per.items()
               if "제외" not in p and p["유보 고유날"] < 10]
        rows2 = {k: v for k, v in rows.items() if k not in bad}
        tab = D.table(r2, rows2)
        per = D.measure(tab)
    return tab, per


def cache_arm(tab, per):
    """도메인 → (sign, 유보 예보, 유보 라벨 순위, n). `decay897.perm_null` 과 같은 것."""
    from scipy.stats import rankdata
    out = {}
    for dm, t in tab.items():
        if "제외" in t or "제외" in per[dm]:
            continue
        a = per[dm]["표현 학습ρ(OOF)"]
        if not np.isfinite(a):
            continue
        _o, pte, _i = D.fit_preds(t)
        out[dm] = (float(np.sign(a)) if a != 0 else 1.0, np.asarray(pte, float),
                   rankdata(t["lab"][t["te"]]), int(per[dm]["유보"]))
    return out


def pair_null(ca, cb, draws=PERM, seed=PERM_SEED):
    """🔴 **같은 라벨 순열을 두 팔에 동시에** 먹인다 — 이것이 ΔS 자신의 널이다.

    897 은 팔마다 널을 따로 뽑고 그 둘 중 하나(또는 평균)를 ΔS 의 문턱으로 **빌렸다**.
    두 팔의 널이 완전 상관이 아니면(실측 0.23~0.35) 차의 분산은
    `Var(a)+Var(b)−2Cov(a,b)` 라서 **각 팔의 널보다 오히려 넓다**.
    """
    doms = [d for d in ca if d in cb]
    rng = np.random.default_rng(seed)
    sa, sb = [], []
    for _ in range(draws):
        na = nb = den = 0.0
        for dm in doms:
            s1, p1, rl, n = ca[dm]
            s2, p2, rl2, n2 = cb[dm]
            assert n == n2 and len(rl) == len(rl2)
            pl = rng.permutation(rl)              # 🔴 같은 순열을 두 팔에
            na += n * s1 * D._sp(p1, pl)
            nb += n * s2 * D._sp(p2, pl)
            den += n
        sa.append(na / den)
        sb.append(nb / den)
    A, B = np.asarray(sa), np.asarray(sb)
    Dl = B - A
    ok = np.isfinite(Dl)
    A, B, Dl = A[ok], B[ok], Dl[ok]
    return {"도메인 수": len(doms), "도메인": doms, "뽑기": int(len(Dl)),
            "ΔS 널 평균": round(float(Dl.mean()), 6),
            "ΔS 널 SD": round(float(Dl.std(ddof=1)), 6),
            "🔴 짝 ΔS 널 2σ": round(float(2 * Dl.std(ddof=1)), 6),
            "ΔS 널 백분위 2.5/97.5": [round(float(np.percentile(Dl, 2.5)), 6),
                                    round(float(np.percentile(Dl, 97.5)), 6)],
            "ㅂ-1 널 SD": round(float(A.std(ddof=1)), 6),
            "ㅂ-2 널 SD": round(float(B.std(ddof=1)), 6),
            "🔴 두 팔 널 상관(피어슨)": round(float(np.corrcoef(A, B)[0, 1]), 4),
            "_delta": Dl}


def m1_m2(rs, rows) -> dict:
    t = np.arange(len(rs["yrs"]), dtype=float)[:, None]
    t = (t - t.mean()) / t.std()
    Fr = rs["F"]
    arms = {"ㅂ-1 시각만": t, "ㅂ-2 시각+장": np.hstack([t, Fr]), "ㅂ-3 장만": Fr}
    old = json.loads((ROOT / "runners/out897_partial.json").read_text())

    res = {"🔴 사전등록 문면(어긴 것)":
           "「널을 직접 뽑는다(891 방식) — **남의 문턱을 안 빌린다**」 "
           "(docs/prereg_897_architecture.md §2)",
           "관측치 재현(897 의 여섯)": {}, "짝 널": {}, "필요 군집": {}}

    tabs = {}
    for sub, dd in (("전 도메인", False), ("퇴화 제외", True)):
        for tag, F in arms.items():
            tab, per = arm_tab(rs, rows, F, dd)
            S, used, n = D.headline(tab, per, "표현")
            key = f"{tag} · {sub}"
            o = old["팔"][key]["S"]
            res["관측치 재현(897 의 여섯)"][key] = {
                "897": o, "오늘": round(float(S), 5), "n": n, "897 n": old["팔"][key]["n"],
                "재현": bool(round(float(S), 5) == o and n == old["팔"][key]["n"])}
            tabs[key] = (tab, per, float(S), n)

    for sub in ("퇴화 제외", "전 도메인"):
        ka, kb = f"ㅂ-1 시각만 · {sub}", f"ㅂ-2 시각+장 · {sub}"
        (ta, pa, Sa, na), (tb, pb, Sb, nb) = tabs[ka], tabs[kb]
        ca, cb = cache_arm(ta, pa), cache_arm(tb, pb)
        pn = pair_null(ca, cb)
        Dl = pn.pop("_delta")
        obs = Sb - Sa
        z = (obs - Dl.mean()) / Dl.std(ddof=1)
        p1 = float((Dl >= obs).mean())
        cl = old["팔"][kb]["군집 병기"]["군집(날짜)"]
        old_null = {"퇴화 제외": 0.03924, "전 도메인": 0.03235}[sub]   # 897 이 빌린 문턱
        need_pair = cl * (pn["🔴 짝 ΔS 널 2σ"] / obs) ** 2
        need_old = cl * (old_null / obs) ** 2
        pn.update({
            "관측 ΔS(반올림 전)": round(obs, 6), "관측 ΔS(897 표기)": round(Sb, 5) - round(Sa, 5),
            "n": nb, "군집(날짜)": cl,
            "z": round(float(z), 3), "단측 p(널 ≥ 관측)": round(p1, 4),
            "판정": ("**널 안** — 장의 증분은 이 자리에서 0 과 못 가른다"
                   if abs(obs - Dl.mean()) <= pn["🔴 짝 ΔS 널 2σ"] else "널 밖"),
            "897 이 빌린 널 2σ": old_null,
            "🔴 897 널이 얼마나 좁았나": f'{round(100 * (1 - old_null / pn["🔴 짝 ΔS 널 2σ"]), 1)}% 좁다',
        })
        res["짝 널"][sub] = pn
        res["필요 군집"][sub] = {
            "현재 군집": cl,
            "🔴 짝 널로": int(round(need_pair)), "배수(짝 널)": round(need_pair / cl, 1),
            "897 방식(빌린 널)로": int(round(need_old)), "배수(897 방식)": round(need_old / cl, 1),
            "날짜로 환산(군집=날짜)": f"{int(round(need_pair))}일 ≈ {round(need_pair / 365, 1)}년치",
        }
    res["🔴 M2 — 헤드라인이 덜 유리한 쪽을 골랐다"] = {
        "897 헤드라인": "9,476 군집 · 17.6배 · 25년치 — 🔴 **퇴화 제외(사후 부분집합)** 의 수다",
        "사전등록된 전 도메인(같은 897 방식)":
            f'{res["필요 군집"]["전 도메인"]["897 방식(빌린 널)로"]} 군집 · '
            f'{res["필요 군집"]["전 도메인"]["배수(897 방식)"]}배',
        "짝 널로 고치면": f'퇴화 제외 {res["필요 군집"]["퇴화 제외"]["🔴 짝 널로"]} · '
                    f'전 도메인 {res["필요 군집"]["전 도메인"]["🔴 짝 널로"]}',
        "🔴 병기 의무": "헤드라인은 **사전등록된 전 도메인**을 먼저 적고 퇴화 제외를 사후로 병기한다. "
                   "그리고 **2단계를 안 여는 결정 자체가 사후 부분집합에서 나왔다** — "
                   "원장의 *'판정에 안 썼다'* 는 문장이 틀렸다",
    }
    return res


# ── ㄹ · M3 — S 의 부호가 추정기에 따라 뒤집힌다 ─────────────────────────
def m3_sign(rs, rows) -> dict:
    """「날짜 한 열」이 0.10028 / 0.06823 / 0.11491 세 값을 낸 이유를 **실측**한다.

    셋의 정체:
      0.10028  `ctl897.py` ㄷ 의 「1열」 — 날짜 지표를 **그대로** 축으로 쓰고 스피어만
      0.06823  `ctl897b.py` ㅂ-1 전 도메인 — 표준화한 날짜를 **능형 1열**에 넣고 OOF
      0.11491  같은 ㅂ-1 인데 **퇴화 제외 부분집합**(n 2,598)

    앞의 둘은 **같은 자료·같은 부분집합**이다. 1열 능형은 날짜의 아핀 변환이므로
    |ρ_유보| 가 같아야 하고 실제로 같다 — 그러면 차이는 **부호 채널뿐**이다.
    """
    from scipy.stats import rankdata
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import GroupKFold

    # ㄷ 추정기: 날짜 지표 그대로(arm="1열")
    rs_t = dict(rs)
    rs_t["one"] = np.arange(len(rs["yrs"]), dtype=float)
    tab_c = D.table(rs_t, rows)
    per_c = D.measure(tab_c)
    S_c, used_c, n_c = D.headline(tab_c, per_c, "1열")

    # ㅂ-1 추정기: 표준화 날짜 1열 능형 OOF(arm="표현")
    t = np.arange(len(rs["yrs"]), dtype=float)[:, None]
    t = (t - t.mean()) / t.std()
    tab_b, per_b = arm_tab(rs, rows, t, False)
    S_b, used_b, n_b = D.headline(tab_b, per_b, "표현")

    rows_out, gap = {}, 0.0
    for dm in used_c:
        c, b = used_c[dm], used_b.get(dm)
        if b is None:
            continue
        t_ = tab_b[dm]
        X = t_["X"][t_["tr"]]
        r = rankdata(t_["lab"][t_["tr"]])
        z = (r - r.mean()) / (r.std() + 1e-12)
        A = (X - t_["X"][t_["tr"]].mean(0)) / (t_["X"][t_["tr"]].std(0) + 1e-9)
        g = t_["j"][t_["tr"]]
        full = Ridge(alpha=D.ALPHA).fit(A, z)
        ng = len(np.unique(g))
        folds = []
        if ng >= 2:
            for tri, _tei in GroupKFold(n_splits=int(min(D.FOLDS, ng))).split(A, z, groups=g):
                folds.append(float(np.sign(Ridge(alpha=D.ALPHA).fit(A[tri], z[tri]).coef_[0])))
        oof, _pte, _i = D.fit_preds(t_)
        o = np.isfinite(oof)
        d = (b["n"] * b["sign"] * b["유보ρ"]) - (c["n"] * c["sign"] * c["유보ρ"])
        gap += d
        rows_out[dm] = {
            "n": c["n"],
            "ㄷ(날짜 그대로)": {"sign(ρ_학습)": c["sign"], "ρ_유보": c["유보ρ"],
                          "ρ_학습": per_c[dm]["1열 학습ρ"],
                          "기여": round(c["n"] * c["sign"] * c["유보ρ"], 2)},
            "ㅂ-1(능형 OOF)": {"sign(ρ_학습)": b["sign"], "ρ_유보": b["유보ρ"],
                           "ρ_학습(OOF)": per_b[dm]["표현 학습ρ(OOF)"],
                           "기여": round(b["n"] * b["sign"] * b["유보ρ"], 2)},
            "|ρ_유보| 같나": bool(abs(abs(c["유보ρ"]) - abs(b["유보ρ"])) < 5e-4),
            "🔴 부호 뒤집혔나": bool(c["sign"] * np.sign(c["유보ρ"])
                             != b["sign"] * np.sign(b["유보ρ"])),
            "능형 계수 부호(전체 적합)": int(np.sign(full.coef_[0])),
            "접기별 계수 부호": folds,
            "🔴 접기별 부호가 섞였나": bool(len(set(folds)) > 1),
            "ρ(OOF 예보, 날짜)|학습": round(D._sp(oof[o], t_["j"][t_["tr"]][o]), 4),
            "기여 차(ㅂ-1 − ㄷ)": round(d, 2),
        }
    return {
        "세 값의 정체": {
            "0.10028": "ctl897.py ㄷ 「1열」 — 날짜 지표 **그대로** · 전 도메인 n 3,710",
            "0.06823": "ctl897b.py ㅂ-1 — 표준화 날짜 **능형 1열 OOF** · 전 도메인 n 3,710",
            "0.11491": "같은 ㅂ-1 인데 **퇴화 제외**(사후 부분집합) n 2,598",
        },
        "오늘 재현": {"ㄷ(날짜 그대로)": round(float(S_c), 5), "n": n_c,
                   "ㅂ-1(능형 OOF)": round(float(S_b), 5), "n2": n_b},
        "🔴 부호 결정 로직(실측)": {
            "코드": "`decay897.headline:263` — `s = np.sign(a)`, `a = per[dm][key_tr]`. "
                  "1열 팔은 `a = spearman(축, 라벨)|학습`, 표현 팔은 "
                  "`a = spearman(**OOF 능형 예보**, 라벨)|학습`. 유보 쪽은 "
                  "`ρ_유보 = spearman(**전체적합 능형 예보**, 라벨)|유보`(`fit_preds:214`)",
            "🔴 진짜 결함": "**부호는 OOF 예보(접기 모형 다섯)에서 재고, ρ_유보 는 전체적합 예보(모형 하나)에서 잰다 — "
                       "서로 다른 예측기다.** 축의 방향(능형 계수 부호)이 뒤집히면 ρ_유보 가 통째로 뒤집히는데, "
                       "OOF 예보의 방향은 접기마다 달라서 **같이 안 뒤집힌다.** 그러면 "
                       "`sign(ρ_학습)·ρ_유보` 가 **축의 방향에 불변이 아니게 된다** — 같은 자료·같은 부분집합인데 "
                       "축을 날짜로 쓰느냐 「날짜를 능형에 통과시킨 것」으로 쓰느냐에 따라 도메인 기여가 "
                       "`±2·n·ρ` 만큼 뒤집힌다",
            "실측 갈래 둘": "① **도서** — 접기별 계수 부호가 섞여(+,+,+,+,−) OOF 가 날짜의 단조 함수가 아니고 "
                       "`ρ_학습` 이 +0.1135(날짜) → −0.3391(OOF) 로 **부호 자체가 뒤집힌다** "
                       "② **모바일·영화·펀딩** — 전체적합 계수가 음수라 `ρ_유보` 가 뒤집히는데 "
                       "`ρ_학습(OOF)` 은 안 뒤집혀 **보정이 안 된다**",
            "🔴 위약이 못 잡는 이유": "위약은 날짜 연결을 끊어 축을 지우지, **축의 방향을 안 건드린다.** "
                             "이 결함은 널이 아니라 **자의 항등성** 문제다",
        },
        "도메인별": rows_out,
        "🔴 차의 분해": {
            "S(ㅂ-1) − S(ㄷ)": round(float(S_b) - float(S_c), 5),
            "부호 뒤집힌 도메인의 기여 차 합 ÷ n": round(gap / n_c, 5),
            "일치": bool(abs((gap / n_c) - (float(S_b) - float(S_c))) < 1e-4),
            "뜻": "🔴 **두 값의 차이는 전부 부호 채널에서 나온다.** |ρ_유보| 는 한 도메인도 안 바뀐다. "
                "즉 이것은 '추정기가 더 좋다/나쁘다' 가 아니라 **자가 도메인마다 동전을 던진다**는 뜻이다",
        },
        "🔴 처방(다음 사이클 · 사전등록해서)":
            "① 부호는 **팔과 무관하게 한 번만** 정한다(예: 원축 `spearman(날짜, 라벨)|학습` 고정) "
            "② 부호가 안 서는 도메인(|ρ_학습| 이 자기 널 안)은 **기여를 0 으로 두거나 빼고 그 수를 적는다** "
            "③ 접기별 계수 부호가 섞이면 **그 도메인은 '부호 불능' 으로 표시**한다 — 지금은 조용히 섞인다",
    }


# ── ㅁ · C8 — 「사다리를 장 학습 과제로」를 날짜 군집으로 다시 센다 ──────
def c8_ladder(need: dict) -> dict:
    """🔴 897 의 헤드라인 발견을 897 자신의 권고에 적용한다.

    발견: *"잡음의 단위가 씨앗이 아니라 **날짜 군집**"*(판 유보 3,710행 → 540 군집).
    권고: *"판 유보에선 못 잰다 → 사다리를 **장 학습 과제(관측 143,892)** 로 옮겨라"*.

    그런데 143,892 는 **유보 552창 × 동네 264** 다(노트 733·735·736 이 셋 다
    *"유보 552창 · 관측 143,892 · 목표일 2025-01-01~2026-07-06 · 동네 264"*).
    **날짜 군집으로 세면 552 이고 판의 540 과 1.02배**다.
    """
    win, hood, obs = 552, 264, 143892
    board_cl, board_rows_ = 540, 3710
    return {
        "원장에서 직접 읽은 것(노트 733·735·736 — 셋이 같은 문장)": {
            "노트 733": "모수 5,505 · 동네 264 · 학습 창 1,368 · 검증 343 · "
                     "**유보 창 552**(목표일 2025-01-01 ~ 2026-07-06 · 유보 관측 143,892)",
            "노트 735": "③ 유보 552창 · 관측 143,892 · 목표일 2025-01-01~2026-07-06 · 동네 264 · 모수 5,505",
            "노트 736": "유보 창 552 · 관측 143,892 · 목표일 2025-01-01~2026-07-06",
            "🔴 확인": "셋 다 같은 분해를 적는다. **143,892 는 독립 관측 수가 아니라 창×동네다**",
        },
        "산수": {
            "552창 × 264동": win * hood,
            "실제 관측": obs, "관측률": round(obs / (win * hood), 4),
            "창당 평균 동네": round(obs / win, 1),
            "🔴 목표일 2025-01-01~2026-07-06 은 정확히 552일": True,
            "즉 날짜 군집": win,
        },
        "🔴 조항 60 — 분모 대조": {
            "판 유보": f"행 {board_rows_} · **날짜 군집 {board_cl}**",
            "장 학습 과제 유보": f"관측 {obs} · **날짜 군집 {win}**",
            "행으로 세면": f"{round(obs / board_rows_, 1)}배",
            "🔴 날짜 군집으로 세면": f"{round(win / board_cl, 3)}배",
            "판정력 환산(σ ∝ 1/√군집)": f"SE 가 {round((win / board_cl) ** 0.5, 3)}배 좁아진다 — "
                                 f"즉 **{round(100 * (1 - (board_cl / win) ** 0.5), 1)}% 개선**",
        },
        "🔴 권고는 서나": {
            "897 이 쓴 논거": "관측 143,892 → *'여기서만 L3~L8 을 잰다. 유일하게 n 이 받쳐 준다'*",
            "판정": "🔴 **논거는 무너진다.** 897 의 헤드라인 발견(잡음의 단위 = 날짜 군집)을 "
                  "적용하면 장 학습 과제의 날짜 군집은 **552**로 판의 **540 과 1.02배**다. "
                  "38.8배는 **행 수의 비**이고 897 자신이 그 분모를 못 쓴다고 적은 자리다 — "
                  "**자기가 세운 자를 자기 권고에 안 갖다 댔다**(조항 60).",
            "필요 군집과 대조": {
                "전 도메인(사전등록 · 짝 널)": f'{need["전 도메인"]["🔴 짝 널로"]} 군집 필요 → '
                                     f'장 학습 과제 552 로도 '
                                     f'{round(need["전 도메인"]["🔴 짝 널로"] / win, 1)}배 모자라다',
                "퇴화 제외(사후 · 짝 널)": f'{need["퇴화 제외"]["🔴 짝 널로"]} 군집 필요 → '
                                  f'{round(need["퇴화 제외"]["🔴 짝 널로"] / win, 1)}배 모자라다',
            },
            "🔴 그러나 여기까지가 정직한 상한·하한이다": "장 학습 과제의 **추정 대상이 다르다** — "
                "판의 S 는 특성이 **날짜만의 함수**라 같은 날 행이 완전 종속(그래서 군집 = 날짜)인데, "
                "장의 유보 R² 는 **동네마다 다른 목표**를 예측하므로 같은 날 264 동네가 완전 종속은 아니다. "
                "그러므로 참 유효 표본은 **552(하한 · 판과 같은 논리) 와 143,892(상한 · 하루 안 상관 0 가정) 사이**이고, "
                "🔴 **그 사이 어디인지는 아무도 잰 적이 없다**(하루 안 잔차 상관 · 설계효과 미측정).",
            "🔴 그러므로 결정": "**「사다리를 장 학습 과제로 옮긴다」는 지금 근거로는 못 정한다.** "
                        "권고를 살리려면 먼저 **장 유보 잔차의 하루 안 상관(설계효과)** 을 재야 하고, "
                        "그것이 유효 군집을 552 에서 얼마나 밀어 올리는지가 **결정 수**다. "
                        "그 수 없이 143,892 를 인용하는 것은 조항 60 위반이다. "
                        "**측정 하나가 권고 하나를 살리거나 죽인다 — 그것을 다음 사이클의 0단계로 둔다.**",
        },
        "고친 문서": "docs/아키텍처.md §2 표 — 143,892 에 「유보 552창 × 동네 264」와 날짜 군집 552 를 병기했다",
    }


def main():
    out = {"stamp": stamp(),
           "무엇": "이슈 #120(티처 #60 C7·C8·M1·M2·M3) 정정 — 897 은 되돌리지 않는다. 정정을 얹는다",
           "ㄱ C7 — F4 를 두 팔 다 센다": c7_f4()}
    print(json.dumps(out["ㄱ C7 — F4 를 두 팔 다 센다"]["팔"], ensure_ascii=False,
                     indent=1), flush=True)

    rs = D.rep_series()
    rows, _d0 = D.board_rows()
    out["ㄴㄷ M1·M2 — ΔS 자신의 짝 널"] = m1_m2(rs, rows)
    print(json.dumps({k: v for k, v in out["ㄴㄷ M1·M2 — ΔS 자신의 짝 널"].items()
                      if k in ("관측치 재현(897 의 여섯)", "필요 군집")},
                     ensure_ascii=False, indent=1), flush=True)

    out["ㄹ M3 — S 의 부호가 추정기에 따라 뒤집힌다"] = m3_sign(rs, rows)
    out["ㅁ C8 — 사다리를 장 학습 과제로?"] = c8_ladder(
        out["ㄴㄷ M1·M2 — ΔS 자신의 짝 널"]["필요 군집"])
    print(json.dumps(out["ㅁ C8 — 사다리를 장 학습 과제로?"]["🔴 조항 60 — 분모 대조"],
                     ensure_ascii=False, indent=1), flush=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print("→", OUT)


if __name__ == "__main__":
    main()
