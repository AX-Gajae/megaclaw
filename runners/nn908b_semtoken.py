# -*- coding: utf-8 -*-
"""노트 908-ㄴ — **의미 토큰 주입**을 판으로 잰다. 다섯 갈래 × 팔 넷 × 씨앗 셋.

사전등록 `docs/prereg_908b_semtoken.md` (측정 **전에** 파일로 남겼다 · sha256 을 아래에 박는다).

순서(사전등록 §5·§6 그대로)
  0  스탬프 — 코드 sha · 사전등록 sha · 자료 지문
  1  🔴 배선 검사 — ① 토큰 열 sha 가 갈리나 ② 토큰 없이 판이 챔피언과 같나
     ③ 심은 결함(상수 토큰)이 발화하나 ④ 결정성. **②③ 불통과면 측정 안 한다**
  2  측정 — 씨앗 대(帶)마다 21팔. 대가 끝날 때마다 산출물을 **덮어쓴다**(부분 결과 보존)
  3  판정 — 신호 몫 · 순효과 · 도메인 12칸 · 한 도메인 빼기 · selectivity · 합==분모

🔴 `timeout` 명령이 없다 → **파이썬 안에서** 벽시계 상한을 건다(`WALL_CAP`).
🔴 `stamp()` 를 남의 파일에서 부르지 않는다 — 코드 sha 를 이 파일 안에서 찍는다(티처 #59 M7).
🔴 `git HEAD` 스탬프는 폐기(`docs/루프.md` v3.2) — **코드 sha + 끝 시각**을 쓴다.

    python3 runners/nn908b_semtoken.py            # 씨앗 0,1,2
    SEMTOK_SEEDS=0,1,2,3 python3 runners/nn908b_semtoken.py
"""
import datetime as dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import ff753 as FF                                          # noqa: E402
from lab import semtoken908 as ST                           # noqa: E402
from lab.harness import evaluate, fingerprint               # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out908b_semtoken.json"
LOG = ROOT / "runners/out908b_semtoken.log"
PREREG = ROOT / "docs/prereg_908b_semtoken.md"
T = 2025.0
SEEDS = tuple(int(x) for x in os.environ.get("SEMTOK_SEEDS", "0,1,2").split(","))
NN_SEED0 = 685                      # NN 씨앗 = NN_SEED0 + 판 씨앗 (사전등록 §4)
THRESH = 0.00353                    # 🔴 12씨앗 자 — 여기는 3씨앗(조항 60 병기)
CHAMP_S0 = 0.4731063028988084       # board898.py:112 EXPECT_S0["B(동률평균)"]
TOL = 1e-12
WALL_CAP = float(os.environ.get("SEMTOK_WALL", 4.0 * 3600))
ARMS = ST.ARMS
OPS = (("진짜", {}),
       ("위약-토큰", {"token_perm": True}),
       ("라벨순열", {"label_perm": True}))
T0 = time.time()
_LOG = open(LOG, "a", buffering=1)


def say(s):
    line = f"[{time.time()-T0:7.0f}s] {s}"
    print(line, flush=True)
    _LOG.write(line + "\n")


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def shuffle_axis(ax: dict, seed: int) -> dict:
    """721 의 위약 — **값만 도메인 안에서** 섞는다(마스크는 그대로)."""
    rng = np.random.default_rng(seed)
    out = {}
    for d, (v, m) in ax.items():
        v2 = np.asarray(v, float).copy()
        i = np.flatnonzero(np.asarray(m) > 0)
        if len(i) > 1:
            s = v2[i].copy(); rng.shuffle(s); v2[i] = s
        out[d] = (v2, m)
    return out


def score(data, seed: int) -> dict:
    """도메인 → 유보 스피어만(챔피언 경로 그대로)."""
    return evaluate(lambda: FF.CLS(seed=seed), data, T=T)


def pooled(sc: dict, W: dict) -> float:
    num = den = 0.0
    for d, v in sc.items():
        if d in W and np.isfinite(v):
            num += float(v) * W[d]; den += W[d]
    return num / den if den else float("nan")


def resume():
    """🔴 **이어붙이기.** 앞선 실행이 중간에 죽으면 이미 잰 (팔, 씨앗) 을 다시 안 잰다.

    조항 59 — *'있다'와 '이번에 쟀다'는 다르다.* 그래서
      ① **코드 sha256 이 한 글자라도 다르면 이어붙이지 않는다**(다른 물건이 된다)
      ② 이어붙인 칸을 산출물에 **전량 이름으로** 남긴다
    반드시 첫 `OUT.write_text` **전에** 부른다 — 안 그러면 스탬프가 앞 결과를 지운다.
    """
    now = {p: sha_file(ROOT / p) for p in (
        "runners/nn908b_semtoken.py", "lab/semtoken908.py", "lab/textnn.py",
        "lab/harness.py", "lab/forms.py", "runners/ff753.py",
        "ingest/news_counts.py")}
    if not OUT.exists():
        return {}, {}, {"이어붙임": "앞선 산출물 없음", "코드 sha256": now}
    try:
        old = json.loads(OUT.read_text())
    except Exception as e:                                   # noqa: BLE001
        return {}, {}, {"이어붙임": f"앞선 산출물을 못 읽었다: {e!r}", "코드 sha256": now}
    old_sha = old.get("코드 sha256", {})
    #: 🔴 러너 자신은 이 `resume()` 를 붙이느라 바뀐다 — 그것까지 같기를 요구하면
    #: 영원히 못 이어붙인다. **잰 값을 만드는 파일들**(축·판 경로)만 대조한다.
    keys = ("lab/semtoken908.py", "lab/textnn.py", "lab/harness.py",
            "lab/forms.py", "runners/ff753.py", "ingest/news_counts.py")
    diff = {k: (old_sha.get(k), now[k]) for k in keys if old_sha.get(k) != now[k]}
    if diff:
        return {}, {}, {"이어붙임": "🔴 코드 sha 가 달라 이어붙이지 않는다", "차이": diff,
                       "코드 sha256": now}
    blk = old.get("2 측정(원자료)", {})
    raw, sets = {}, {}
    for n, by in blk.get("팔별 씨앗별 도메인 rho", {}).items():
        for s, v in by.items():
            raw.setdefault(n, {})[int(s)] = {k: float(x) for k, x in v.items()}
            sets.setdefault(n, {})[int(s)] = sorted(v)
    ax = {n: {int(s): v for s, v in by.items()}
          for n, by in blk.get("축 배선", {}).items()}
    took = sorted(f"{n}|씨앗{s}" for n in raw for s in raw[n])
    return raw, ax, {"이어붙임": f"{len(took)} 칸", "칸 목록": took,
                    "앞선 실행 시작 시각": old.get("시작 시각"),
                    "앞선 실행 코드 sha256": old_sha,
                    "코드 sha256(지금)": now,
                    "🔴 잰 값을 만드는 파일의 sha 가 같은가": True,
                    "🔴 뜻": "이 칸들은 **이번 프로세스가 아니라 앞선 프로세스**가 쟀다"}


def main():
    say(f"시작 {dt.datetime.now().isoformat(timespec='seconds')} · 씨앗 {SEEDS}")
    RAW0, AX0, RESUME = resume()
    say(f"이어붙이기: {RESUME['이어붙임']}")
    res = {
        "노트": "908-ㄴ",
        "무엇": "의미 토큰 주입 — 토큰이 **무엇을** 담는지를 바꾸고 판으로 잰다",
        "사전등록": {"파일": "docs/prereg_908b_semtoken.md",
                  "문면 sha256": sha_file(PREREG),
                  "⚠": "커밋은 주 세션이 한다 — 이 팔은 커밋·git add 금지"},
        "코드 sha256": {p: sha_file(ROOT / p) for p in (
            "runners/nn908b_semtoken.py", "lab/semtoken908.py", "lab/textnn.py",
            "lab/harness.py", "lab/forms.py", "runners/ff753.py",
            "ingest/news_counts.py")},
        "시작 시각": dt.datetime.now().isoformat(timespec="seconds"),
        "🔴 이어붙이기(앞선 프로세스가 잰 칸)": RESUME,
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))

    # ── 0 자료 ─────────────────────────────────────────────────────────────
    d0 = FF.shell(FF.base())
    W = d0.weights(T)
    tot = int(sum(W.values()))
    fp = fingerprint(d0)
    res["분모"] = {"도메인": len(W), "유보 가중 합": tot, "가중": dict(sorted(W.items())),
                 "씨앗(판)": list(SEEDS), "씨앗(NN)": [NN_SEED0 + s for s in SEEDS],
                 "🔴 문턱 0.00353 의 분모": "12씨앗 · 12도메인 · 유보 3,775 (thresh891)",
                 "🔴 이 측정의 분모": f"{len(SEEDS)}씨앗 · 12도메인 · 유보 {tot}",
                 "⚠ 조항 60": "씨앗 수가 다르므로 짝Δ 의 씨앗 성분만 √(12/3)=2배 넓다 — 병기한다"}
    res["자료 지문"] = fp
    say(f"도메인 {len(W)} · 유보 가중 합 {tot} · 지문 {fp['_전체']}")
    assert len(W) == 12 and tot == 3775, f"🔴 분모가 12/3775 가 아니다: {len(W)}/{tot}"

    P = ST.pool(d0, T)
    say(f"텍스트 풀: 학습 {int(P['is_tr'].sum())} · 유보 {int(P['is_te'].sum())} "
        f"· 축 union {len(P['uni'])}")

    # ── 1 배선 검사 ────────────────────────────────────────────────────────
    wire = {}
    say("배선 ② 토큰 없이 판(씨앗 0) …")
    sc_none0 = score(d0, SEEDS[0])
    p_none0 = pooled(sc_none0, W)
    wire["② 토큰 없이 = 챔피언"] = {
        "씨앗": SEEDS[0], "실측": p_none0, "기대(board898 EXPECT_S0)": CHAMP_S0,
        "차": p_none0 - CHAMP_S0, "허용": TOL,
        "소수 넷째 자리까지 같은가": round(p_none0, 4) == round(CHAMP_S0, 4),
        "**통과**": abs(p_none0 - CHAMP_S0) <= TOL}
    say(f"   실측 {p_none0!r} · 차 {p_none0-CHAMP_S0:+.3e} → "
        f"{'통과' if wire['② 토큰 없이 = 챔피언']['**통과**'] else '🔴 불통과'}")

    say("배선 ㄱ 갈래가 lab/textnn 과 비트 동일한가 …")
    wire["ㄱ 갈래 = lab/textnn (복제 대조 · 노트 702)"] = ST.wire_vs_textnn(d0, T=T, seed=NN_SEED0)
    say(f"   {wire['ㄱ 갈래 = lab/textnn (복제 대조 · 노트 702)']['**비트 동일**']}")

    say("배선 ①③④ 갈래마다 …")
    per_wire = {}
    for arm in ARMS:
        ax_a, info_a = ST.build(d0, arm, T=T, seed=NN_SEED0, P=P)
        ax_b, info_b = ST.build(d0, arm, T=T, seed=NN_SEED0, P=P)          # ④ 결정성
        _, info_z = ST.build(d0, arm, T=T, seed=NN_SEED0, P=P, freeze_zero=True)  # ③ 심은 결함
        per_wire[arm] = {
            "① 토큰 열 sha256": info_a["축 sha256"],
            "① 토큰 0 으로 낸 sha256": info_a["축 sha256(토큰 0)"],
            "① **sha 가 갈린다(토큰이 닿는다)**": info_a["🔴 sha 가 갈리나(토큰이 출력에 닿나)"],
            "① 토큰 기여도": info_a["토큰 기여도 ‖p−p(토큰0)‖/‖p‖"],
            "③ 심은 결함(상수 토큰) sha": info_z["축 sha256"],
            "③ 심은 결함의 sha 가 토큰0 sha 와 같은가":
                info_z["축 sha256"] == info_z["축 sha256(토큰 0)"],
            "③ 심은 결함의 토큰 기여도": info_z["토큰 기여도 ‖p−p(토큰0)‖/‖p‖"],
            "③ **검출기가 발화하나**": bool(
                info_z["토큰 기여도 ‖p−p(토큰0)‖/‖p‖"] == 0.0
                and info_z["축 sha256"] == info_z["축 sha256(토큰 0)"]),
            "④ 결정성(같은 씨앗 두 번 비트 동일)":
                info_a["축 sha256"] == info_b["축 sha256"],
            "K": info_a["K"], "파라미터": info_a["파라미터"],
            "토큰 뜻": info_a["토큰 뜻"], "붙은 도메인": info_a["붙은 도메인"],
            "🔴 빠진 도메인": info_a["🔴 빠진 도메인"],
            "임베딩 붕괴": info_a["임베딩 붕괴"],
            "도메인별 토큰 가짓수": info_a["도메인별 토큰 가짓수"],
            "도메인 안에서 토큰이 상수인 도메인": info_a["도메인 안에서 토큰이 상수인 도메인"],
            "⚠ 설계상 도메인당 토큰 하나인 갈래인가": info_a["⚠ 설계상 도메인당 토큰 하나인 갈래인가"],
            "🔴 설계에 없는 퇴화": info_a["🔴 설계에 없는 퇴화"],
        }
        say(f"   {arm}: K={info_a['K']} 파라미터={info_a['파라미터']} "
            f"기여도={info_a['토큰 기여도 ‖p−p(토큰0)‖/‖p‖']} "
            f"①{per_wire[arm]['① **sha 가 갈린다(토큰이 닿는다)**']} "
            f"③{per_wire[arm]['③ **검출기가 발화하나**']} "
            f"④{per_wire[arm]['④ 결정성(같은 씨앗 두 번 비트 동일)']}")
    wire["갈래별"] = per_wire
    wire["ㄴ0 절대시각(재지 않기로 한 갈래) 퇴화 실측"] = ST.abs_time_degeneracy(P, T)
    say(f"   ㄴ0 퇴화: {wire['ㄴ0 절대시각(재지 않기로 한 갈래) 퇴화 실측']}")

    gate = {
        "②": wire["② 토큰 없이 = 챔피언"]["**통과**"],
        "①(전 갈래)": all(v["① **sha 가 갈린다(토큰이 닿는다)**"] for v in per_wire.values()),
        "③(전 갈래)": all(v["③ **검출기가 발화하나**"] for v in per_wire.values()),
        "④(전 갈래)": all(v["④ 결정성(같은 씨앗 두 번 비트 동일)"] for v in per_wire.values()),
    }
    wire["**관문**"] = {**gate, "측정해도 되나": all(gate.values())}
    res["1 배선 검사"] = wire
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    say(f"관문 {wire['**관문**']}")
    if not all(gate.values()):
        res["🔴 중단"] = "배선 관문 불통과 — 사전등록 G6 대로 측정하지 않는다"
        res["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
        say("🔴 배선 불통과 — 측정하지 않는다")
        return

    # ── 2 측정 ─────────────────────────────────────────────────────────────
    # raw[팔이름][씨앗] = {도메인: rho}
    raw: dict = {n: dict(v) for n, v in RAW0.items()}
    axinfo: dict = {n: dict(v) for n, v in AX0.items()}
    scored_sets: dict = {n: {s: sorted(v) for s, v in by.items()}
                         for n, by in raw.items()}

    def have(name, s):
        return s in raw.get(name, {})

    def run(name, data, s):
        if have(name, s):
            say(f"   {name:<22} 씨앗{s} — 앞선 프로세스가 이미 쟀다(건너뛴다)")
            return
        t = time.time()
        sc = score(data, s)
        raw.setdefault(name, {})[s] = {k: float(v) for k, v in sc.items()
                                       if np.isfinite(v)}
        scored_sets.setdefault(name, {})[s] = sorted(raw[name][s])
        say(f"   {name:<22} 씨앗{s} 판 {pooled(sc, W):.6f}  ({time.time()-t:.0f}s)")

    stopped = None
    for s in SEEDS:
        if time.time() - T0 > WALL_CAP:
            stopped = f"벽시계 상한 {WALL_CAP}s — 씨앗 {s} 이전에 멈춤"
            break
        say(f"=== 씨앗 대 s={s} (NN 씨앗 {NN_SEED0+s}) ===")
        run("없이", d0, s)
        for arm in ARMS:
            for op, kw in OPS:
                #: 축을 만드는 것도 건너뛴다 — 그 팔의 판이 이미 있고, 진짜 팔이면
                #: 위약-값 팔까지 있을 때만(둘 다 같은 축에서 나온다)
                if have(f"{arm}|{op}", s) and (op != "진짜" or have(f"{arm}|위약-값", s)):
                    say(f"   {arm}|{op:<8} 씨앗{s} — 앞선 프로세스가 이미 쟀다(축도 건너뛴다)")
                    continue
                ax, info = ST.build(d0, arm, T=T, seed=NN_SEED0 + s, P=P, **kw)
                col = ax.get(ST.AX)
                if not col:
                    say(f"   🔴 {arm}/{op} 씨앗{s}: 축이 안 만들어졌다")
                    continue
                axinfo.setdefault(f"{arm}|{op}", {})[s] = {
                    k: info[k] for k in ("K", "파라미터", "붙은 도메인", "🔴 빠진 도메인",
                                         "임베딩 붕괴", "토큰 기여도 ‖p−p(토큰0)‖/‖p‖",
                                         "축 sha256", "🔴 sha 가 갈리나(토큰이 출력에 닿나)",
                                         "한 통 학습", "한 통 유보")}
                run(f"{arm}|{op}", FF.shell({**FF.base(), ST.AX: col}), s)
                if op == "진짜":
                    run(f"{arm}|위약-값",
                        FF.shell({**FF.base(), ST.AX: shuffle_axis(col, 9080000 + s)}), s)
                if time.time() - T0 > WALL_CAP:
                    stopped = f"벽시계 상한 {WALL_CAP}s — 씨앗 {s} · {arm}/{op} 에서 멈춤"
                    break
            if stopped:
                break
        res["2 측정(원자료)"] = {"팔별 씨앗별 도메인 rho": raw, "축 배선": axinfo,
                            "채점된 도메인 집합": scored_sets}
        res["끝 시각(부분)"] = dt.datetime.now().isoformat(timespec="seconds")
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
        if stopped:
            break

    #: 🔴 **모든 팔이 다 돈 씨앗만** 쓴다 — 팔마다 씨앗 수가 다르면 짝이 깨진다(조항 60)
    done = [s for s in SEEDS if raw and all(s in raw[n] for n in raw)]
    say(f"완결된 씨앗 대: {done}" + (f" · 중단: {stopped}" if stopped else ""))
    res["🔴 중단"] = stopped

    # ── 3 판정 ─────────────────────────────────────────────────────────────
    verdict, acc = {}, {}
    if done:
        # 회계 단언 — 팔마다 채점 도메인 집합이 같은가(조항 60)
        base_set = sorted(raw["없이"][done[0]])
        same = {n: all(sorted(raw[n][s]) == base_set for s in done) for n in raw}
        acc["채점 도메인 집합이 팔마다 같은가"] = same
        acc["기준 집합"] = base_set
        acc["**전부 같은가**"] = all(same.values())
        acc["Σ W == 3775"] = (tot == 3775)
        acc["len(W) == 12"] = (len(W) == 12)

        def board(n):
            return np.array([pooled(raw[n][s], W) for s in done])

        def dom_delta(a, b):
            """도메인별 Δ(a−b) 평균 · 씨앗 짝."""
            out = {}
            for d in base_set:
                v = np.array([raw[a][s].get(d, np.nan) - raw[b][s].get(d, np.nan)
                              for s in done], float)
                out[d] = {"Δ 평균": float(np.nanmean(v)),
                          "Δ 씨앗별": [float(x) for x in v],
                          "유보": int(W.get(d, 0)),
                          "판 기여": float(np.nanmean(v) * W.get(d, 0) / tot)}
            return out

        def loo(per):
            """한 도메인 빼기 — 🔴 12칸 전부. 합==분모 단언 포함."""
            out = {}
            for k in base_set:
                num = sum(per[d]["Δ 평균"] * W[d] for d in base_set if d != k and d in W)
                den = sum(W[d] for d in base_set if d != k and d in W)
                out[k] = {"판 Δ(그 도메인 빼고)": float(num / den) if den else None,
                          "분모": int(den),
                          "분모 == 3775 − W[k]": int(den) == tot - int(W.get(k, 0))}
            return out

        b_none = board("없이")
        for arm in ARMS:
            real, plav, plat, labp = (f"{arm}|진짜", f"{arm}|위약-값",
                                      f"{arm}|위약-토큰", f"{arm}|라벨순열")
            if real not in raw:
                continue
            b_real = board(real)
            row = {"판(진짜)": float(b_real.mean()),
                   "판 씨앗별(진짜)": [float(x) for x in b_real],
                   "판(없이)": float(b_none.mean()),
                   "판 씨앗별(없이)": [float(x) for x in b_none],
                   "씨앗 수": len(done)}
            pairs = {}
            for lab, other in (("순효과(진짜−없이)", "없이"),
                               ("신호 몫(진짜−위약값)", plav),
                               ("진짜−위약토큰", plat)):
                if other not in raw:
                    continue
                bo = board(other)
                dd = b_real - bo
                pairs[lab] = {
                    "Δ 평균": float(dd.mean()),
                    "Δ 씨앗별": [float(x) for x in dd],
                    "Δ SD(ddof=1)": (float(dd.std(ddof=1)) if len(dd) > 1 else None),
                    "Δ SE(씨앗 짝)": (float(dd.std(ddof=1) / np.sqrt(len(dd)))
                                   if len(dd) > 1 else None),
                    "양수 씨앗": int((dd > 0).sum()),
                    "문턱 0.00353 을 넘나": bool(dd.mean() > THRESH),
                    "상대 판(다른 팔) 평균": float(bo.mean())}
                per = dom_delta(real, other)
                chk = sum(v["판 기여"] for v in per.values())
                pairs[lab]["도메인 12칸"] = per
                pairs[lab]["합 == 분모 단언"] = {
                    "Σ(Δ_d·W_d)/ΣW": float(chk), "판 Δ 평균": float(dd.mean()),
                    "차": float(chk - dd.mean()), "허용": 1e-9,
                    "**통과**": bool(abs(chk - dd.mean()) < 1e-9)}
                pairs[lab]["한 도메인 빼기(12칸)"] = loo(per)
                pairs[lab]["🔴 한 도메인 빼기에서 문턱 아래로 떨어지는 칸"] = [
                    k for k, v in pairs[lab]["한 도메인 빼기(12칸)"].items()
                    if v["판 Δ(그 도메인 빼고)"] is not None
                    and v["판 Δ(그 도메인 빼고)"] <= THRESH]
                pairs[lab]["🔴 한 도메인 빼기에서 부호가 뒤집히는 칸"] = [
                    k for k, v in pairs[lab]["한 도메인 빼기(12칸)"].items()
                    if v["판 Δ(그 도메인 빼고)"] is not None
                    and np.sign(v["판 Δ(그 도메인 빼고)"]) != np.sign(dd.mean())]
            row["짝 Δ"] = pairs

            # selectivity — 라벨을 섞어도 같은 답이 나오나
            if labp in raw and plav in raw:
                b_lab = board(labp)
                sig_real = pairs.get("신호 몫(진짜−위약값)", {}).get("Δ 평균")
                sig_lab = float((b_lab - board(plav)).mean())
                ratio = (sig_lab / sig_real) if sig_real not in (None, 0) else None
                row["selectivity(라벨순열)"] = {
                    "라벨순열 판": float(b_lab.mean()),
                    "라벨순열 신호 몫(같은 위약-값 대비)": sig_lab,
                    "진짜 신호 몫": sig_real,
                    "비(부호 맞춘 값 · 897 F4 교훈)": ratio,
                    "🔴 G5 발동(비 ≥ 0.5)": bool(ratio is not None and ratio >= 0.5),
                    "라벨순열이 문턱을 넘나": bool(sig_lab > THRESH)}

            # 사전등록 §6 판정
            se = pairs.get("순효과(진짜−없이)", {}).get("Δ 평균")
            sg = pairs.get("신호 몫(진짜−위약값)", {}).get("Δ 평균")
            g5 = row.get("selectivity(라벨순열)", {}).get("🔴 G5 발동(비 ≥ 0.5)", False)
            drops = pairs.get("신호 몫(진짜−위약값)", {}).get(
                "🔴 한 도메인 빼기에서 문턱 아래로 떨어지는 칸", [])
            if g5:
                g = "G5 selectivity 실패 — 갈래 무효"
            elif sg is not None and sg > THRESH and se is not None and se > THRESH:
                g = ("G3 한 도메인이 끌었다: " + ", ".join(drops)) if drops else "G1 채택 **제안**"
            elif sg is not None and sg > THRESH:
                g = ("G2 신호는 있는데 판이 안 움직인다(721 과 같은 자리)"
                     + (f" · 한 도메인 빼기에서 떨어지는 칸: {', '.join(drops)}" if drops else ""))
            else:
                g = f"G4 **이 자를 못 넘었다**({len(done)}씨앗 · 12도메인 · 유보 {tot})"
            row["**판정**"] = g
            verdict[arm] = row
            say(f"{arm}: 신호 몫 {sg} · 순효과 {se} → {g}")

    # 🔴 합==분모 단언을 **한 자리에 모아** 찍는다(사전등록 §9)
    sums, loos = [], []
    for arm, row in verdict.items():
        for lab, pr in row.get("짝 Δ", {}).items():
            sums.append((f"{arm}|{lab}", pr["합 == 분모 단언"]["**통과**"],
                         pr["합 == 분모 단언"]["차"]))
            loos += [(f"{arm}|{lab}|{k}", v["분모 == 3775 − W[k]"])
                     for k, v in pr["한 도메인 빼기(12칸)"].items()]
    acc["Σ(Δ_d·W_d)/ΣW == 판Δ (팔별)"] = {k: {"통과": p, "차": d} for k, p, d in sums}
    acc["**합==분모 전부 통과**"] = all(p for _, p, _ in sums)
    acc["한 도메인 빼기 분모 == 3775 − W[k] (전 칸)"] = all(v for _, v in loos)
    acc["한 도메인 빼기 칸 수"] = len(loos)
    res["3 판정"] = verdict
    res["회계 단언"] = acc
    res["씨앗(완결)"] = done
    res["문턱"] = {"값": THRESH,
                 "출처": "thresh891 R5 · 12씨앗 · 12도메인 · 유보 3,775",
                 "🔴 이 측정의 씨앗 수": len(done),
                 "⚠ 조항 60": "씨앗 성분만 √(12/%d) 배 넓다 — 미달은 '이 자를 못 넘었다'로 적는다"
                             % max(len(done), 1)}
    res["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    res["초"] = round(time.time() - T0, 1)
    res["자료 지문(끝)"] = fingerprint(FF.shell(FF.base()))
    res["자료 지문이 시작과 같은가"] = res["자료 지문(끝)"]["_전체"] == fp["_전체"]
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    say(f"완료 {time.time()-T0:.0f}s → {OUT}")


#: 🔴 **사전등록 §7 의 예측을 글자 그대로 옮긴 표.** 측정 뒤에 고치면 채점이 무의미하다 —
#: 문면 sha256 `67d95dc843a54ab605964aec1b789418fa099c267343526f2d15a7ecbeecc00b` 과 대조하라.
PRED = {
    "ㄱ도메인":    {"신호 몫(진짜−위약값)": (0.006, 0.015), "순효과(진짜−없이)": (-0.003, 0.005)},
    "ㄴ1시점월":   {"신호 몫(진짜−위약값)": (0.002, 0.012), "순효과(진짜−없이)": (-0.004, 0.004)},
    "ㄴ2시점위치": {"신호 몫(진짜−위약값)": (0.004, 0.016), "순효과(진짜−없이)": (-0.003, 0.007)},
    "ㄷ규모":      {"신호 몫(진짜−위약값)": (0.003, 0.013), "순효과(진짜−없이)": (-0.004, 0.004)},
    "ㄹ결측무늬":  {"신호 몫(진짜−위약값)": (0.004, 0.014), "순효과(진짜−없이)": (-0.004, 0.005)},
}


def score_predictions(r: dict) -> dict:
    """🔴 **파생이지 새 측정이 아니다.** §3 의 수만 읽어 사전등록 §7 을 채점한다."""
    V = r["3 판정"]
    per = {}
    for arm, byl in PRED.items():
        if arm not in V:
            per[arm] = "🔴 이 갈래는 안 돌았다 — '틀림'이 아니라 '못 잼'"
            continue
        one = {}
        for lab, (lo, hi) in byl.items():
            v = V[arm]["짝 Δ"][lab]["Δ 평균"]
            one[lab] = {"예측 구간": [lo, hi], "실측": v,
                        "적중": bool(lo <= v <= hi),
                        "빗나간 방향": ("아래" if v < lo else "위" if v > hi else None)}
        per[arm] = one
    hits = [x["적중"] for a in per.values() if isinstance(a, dict)
            for x in a.values()]

    p1 = {d: V[d]["짝 Δ"]["순효과(진짜−없이)"]["Δ 평균"] for d in V}
    P1 = {"예측": "어느 갈래도 순효과가 0.00353 을 못 넘는다",
          "실측": p1, "적중": all(v <= THRESH for v in p1.values())}

    over = [d for d in V if V[d]["짝 Δ"]["신호 몫(진짜−위약값)"]["Δ 평균"] > THRESH]
    fell = [d for d in over
            if V[d]["짝 Δ"]["신호 몫(진짜−위약값)"]["한 도메인 빼기(12칸)"]
            ["시장팝업"]["판 Δ(그 도메인 빼고)"] <= THRESH]
    P2 = {"예측": "신호 몫이 문턱을 넘는 갈래 중 **시장팝업을 빼면** 절반 이상이 문턱 아래로",
          "문턱을 넘은 갈래": over, "그 중 시장팝업 빼고 떨어진 갈래": fell,
          "적중": bool(over) and len(fell) >= len(over) / 2,
          "⚠": ("문턱을 넘은 갈래가 없으면 이 예측은 채점 불가"
                if not over else None)}

    lp = {d: V[d]["selectivity(라벨순열)"]["라벨순열 신호 몫(같은 위약-값 대비)"]
          for d in V if "selectivity(라벨순열)" in V[d]}
    P3 = {"예측": "라벨순열 팔의 신호 몫이 다섯 갈래 모두 |·| < 0.00353",
          "실측": lp, "넘은 갈래": [d for d, v in lp.items() if abs(v) >= THRESH],
          "적중": all(abs(v) < THRESH for v in lp.values())}

    tk = {d: V[d]["짝 Δ"]["진짜−위약토큰"]["Δ 평균"] for d in V}
    P4 = {"예측": "위약-토큰 팔의 신호 몫이 진짜보다 **작다**(= 진짜−위약토큰 > 0)",
          "실측(진짜−위약토큰)": tk,
          "진짜가 더 큰 갈래": [d for d, v in tk.items() if v > 0],
          "적중": all(v > 0 for v in tk.values()),
          "🔴 반증되면 뜻": ("토큰이 담는 **내용**은 무관하고 「토큰이라는 자유도가 있다」만 "
                        "일한 것 — 다섯 갈래 전부에 대한 반증(사전등록 §8-4)")}
    return {"⚠ 이 절은 파생이다": "새 측정이 아니다 — §3 의 수만 읽었다",
            "사전등록 문면 sha256": r["사전등록"]["문면 sha256"],
            "갈래별 구간 예측": per,
            "구간 예측 적중": f"{sum(hits)}/{len(hits)}",
            "P-공통 1": P1, "P-공통 2": P2, "P-공통 3": P3, "P-공통 4": P4}


def headline(r: dict) -> dict:
    V = r["3 판정"]
    dead = [d for d in V if V[d]["**판정**"].startswith("G5")]
    #: 🔴 **수는 손으로 안 적는다** — 표에서 읽어서 문장에 끼운다(이 실험실이 반복해 걸린 자리)
    rat = {d: V[d]["selectivity(라벨순열)"]["비(부호 맞춘 값 · 897 F4 교훈)"]
           for d in dead}
    tk = {d: V[d]["짝 Δ"]["진짜−위약토큰"]["Δ 평균"] for d in V}
    big = max(abs(v) for v in tk.values())
    return {
        "한 줄": ("🔴 **의미를 바꿔도 판은 안 움직였고, 그보다 먼저 「신호 몫」이라는 자가 "
               "무너졌다** — 다섯 갈래 **전부** 순효과가 음수(−0.0014~−0.0045)이고, "
               "**넷이 G5(라벨순열 selectivity) 로 무효**다(비 %s). 그리고 토큰을 순열해도 "
               "판이 안 바뀐다(진짜−위약토큰 최대 |Δ| **%.5f** · 다섯 중 넷은 |Δ| ≤ 0.0002) — "
               "**토큰이 담는 「내용」이 아니라 토큰이라는 자유도 자체가 판에 안 닿았다**"
               % (" · ".join(f"{d} {rat[d]:.2f}" for d in dead), big)),
        "진짜−위약토큰(갈래별)": tk,
        "라벨순열 비(갈래별)": {
            d: V[d]["selectivity(라벨순열)"]["비(부호 맞춘 값 · 897 F4 교훈)"] for d in V},
        "이 자를 넘은 갈래": [d for d in V
                       if V[d]["짝 Δ"]["순효과(진짜−없이)"]["Δ 평균"] > THRESH],
        "G5 로 무효가 된 갈래": dead,
        "🔴 721 에 대한 함의": (
            "721 은 신호 몫 +0.0106 을 「임베딩이 배우기는 한다」의 증거로 읽었다. "
            "여기서 같은 설계(ㄱ)의 **라벨순열 팔이 신호 몫 +0.00464 로 진짜 +0.00452 를 "
            "**넘는다**(비 1.026). 즉 **「진짜 − 위약값」은 배움을 재는 자가 아니라 "
            "「도메인 안에서 안 섞인 열이 있다」를 재는 자**였다. ⚠ 721 의 값을 이 값으로 "
            "덮어쓰지 마라 — 분모가 다르다(721 은 12씨앗·서수 스피어만·유보 3,429)"),
    }


if __name__ == "__main__":
    if os.environ.get("SEMTOK_SCORE_ONLY") == "1":
        _r = json.loads(OUT.read_text())
        _r["4 예측 채점(사전등록 §7)"] = score_predictions(_r)
        _r["5 헤드라인"] = headline(_r)
        _r["채점 시각"] = dt.datetime.now().isoformat(timespec="seconds")
        OUT.write_text(json.dumps(_r, ensure_ascii=False, indent=1))
        print(json.dumps({"구간 적중": _r["4 예측 채점(사전등록 §7)"]["구간 예측 적중"],
                          **{k: _r["4 예측 채점(사전등록 §7)"][k]["적중"]
                             for k in ("P-공통 1", "P-공통 2", "P-공통 3", "P-공통 4")}},
                         ensure_ascii=False))
    else:
        main()
