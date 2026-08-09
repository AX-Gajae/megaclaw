# -*- coding: utf-8 -*-
"""노트 886 후속 — **annex9: 출력(power) 동결 + '우주에 없다' 철회**. 개봉 8/11 전.

annex7·annex8 둘 다 *"더 고칠 것이 생기면 annex9 + 정오 사이드카"* 로 이 경로를
열어놨다. 라벨 무접촉이라 오늘 얼 수 있고, **8/11 이후엔 무슨 짓을 해도 골대
이동으로 읽힌다.**

무엇을 얼리나.
  ㄱ. 🔴 **'양성 갈래가 발화할 라벨이 우주에 없다' 철회** — 거짓이었다(티처 #51 F1).
  ㄴ. 두 통계의 **검정력 곡선**과 MDE — annex8 이 천장만 재고 출력을 안 쟀다.
  ㄷ. 🔴 **'없다' 갈래의 판독 조항** — 갈래 함수는 동결이라 못 고친다. 대신 그 문장을
      **어떻게 읽을지**를 라벨 이전에 못박는다. 이것 하나가 9/28 의 오독을 막는다.
  ㄹ. 티처 #51 F2 반박(내 실측) · M2 명시 등재.
"""
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
KD = ROOT / "cycle_log/forward/kobis"
OUT = KD / "annex9_2026-08-09.json"
BAND_RHO, BAND_ERR, TAU = 0.1668, 1.1612, 1.4667
NSIM, SEED = 4000, 88621


def main():
    rows = json.loads((KD / "annex7_2026-08-09.json").read_text())["예측 팔(자루 평균 순위)"]
    rn = np.array([r["국적 팔 순위"] for r in rows], float)
    rc = np.array([r["대조 순위"] for r in rows], float)
    m = len(rn)

    def d_rho(y):
        return float(spearmanr(-rn, y)[0] - spearmanr(-rc, y)[0])

    def d_err(y):
        ry = (-np.asarray(y, float)).argsort().argsort() + 1.0
        return float((np.abs(rc - ry) - np.abs(rn - ry)).mean())

    # ── ㄱ 적대적 y (재배열 부등식 정확해) ────────────────────────
    az = (-rn - (-rn).mean()) / (-rn).std()
    bz = (-rc - (-rc).mean()) / (-rc).std()
    w = az - bz
    ys = np.arange(1.0, m + 1)
    y_adv = np.empty(m)
    y_adv[np.argsort(w)] = ys

    # ── ㄴ 검정력 곡선: 라벨 = 국적 팔 순위 + 잡음 ───────────────
    rs = np.random.default_rng(SEED)
    base = (-rn - (-rn).mean()) / (-rn).std()
    curve = []
    for sd in (0.0, 0.30, 0.45, 0.60, 0.90, 1.30, 2.0, 3.0, 4.0, 6.0, 9.0):
        hr = he = hh = 0
        rr = []
        for _ in range(NSIM):
            y = base + rs.normal(0, sd, m)
            rr.append(float(spearmanr(-rn, y)[0]))
            dr, de = d_rho(y), d_err(y)
            hr += dr > BAND_RHO
            he += de > BAND_ERR
            hh += de < -BAND_ERR
        curve.append({"잡음 SD": sd, "ρ_국적팔": round(float(np.mean(rr)), 3),
                      "P(Δρ > 밴드)": round(hr / NSIM, 4),
                      "🔴 검정력 P(Δ|err| > 밴드)": round(he / NSIM, 4),
                      "P('해롭다' 오발화)": round(hh / NSIM, 4)})
    sz_r = sz_e = sz_h = 0
    for _ in range(NSIM):
        y = rs.permutation(ys)
        sz_r += d_rho(y) > BAND_RHO
        de = d_err(y)
        sz_e += de > BAND_ERR
        sz_h += de < -BAND_ERR

    # 80% MDE (Δ|err| 기준) — 곡선에서 보간
    xs = [c["🔴 검정력 P(Δ|err| > 밴드)"] for c in curve]
    rho_at80 = None
    for a, b in zip(curve, curve[1:]):
        if a["🔴 검정력 P(Δ|err| > 밴드)"] >= 0.8 >= b["🔴 검정력 P(Δ|err| > 밴드)"]:
            f = (a["🔴 검정력 P(Δ|err| > 밴드)"] - 0.8) / (
                a["🔴 검정력 P(Δ|err| > 밴드)"] - b["🔴 검정력 P(Δ|err| > 밴드)"])
            rho_at80 = round(a["ρ_국적팔"] + f * (b["ρ_국적팔"] - a["ρ_국적팔"]), 3)
            break

    out = {
     "작성일": dt.date.today().isoformat(),
     "성격": ("🔴 **annex9 — 출력 동결 + 정오**(노트 886 후속 · 티처 #51). annex7·annex8 이 지정한 "
            "유일한 수정 경로. **정본·annex7·annex8·harvest844·harvest885_nation 전부 불변.** "
            "첫 봉인작 개봉 2026-08-11 이전 · 라벨 무접촉."),

     "ㄱ. 🔴 철회 — '양성 갈래가 발화할 라벨이 우주에 없다'는 거짓이었다": {
       "무엇을 철회하나": ("노트 886 판정문 · 인계 카드 · PR #98 · 논문 474 · 규약 55 가 공통으로 "
                    "*'양성 갈래가 발화할 라벨이 우주에 없다 — 확률이 아니라 구조다'* 라고 적었다. **거짓이다.**"),
       "반증": {"적대적 y 의 Δρ": round(d_rho(y_adv), 4), "밴드": BAND_RHO,
              "넘나": bool(d_rho(y_adv) > BAND_RHO),
              "그 y 와 국적 팔 spearman": round(float(spearmanr(-rn, y_adv)[0]), 4),
              "그 y 와 대조 팔 spearman": round(float(spearmanr(-rc, y_adv)[0]), 4),
              "자백": ("이 수(±0.4245)는 **886 자신의 산출물 `out886_band.json` 이 이미 인쇄하고 있었다.** "
                     "나는 그것을 적어 놓고 다섯 줄 뒤에 반대되는 결론을 썼다. "
                     "티처 #51 F1 이 같은 파일 안에서 찾아냈다.")},
       "참인 명제(이것으로 교체한다)": (
         "① **y = 국적 팔 순위(완벽 예측) 방향으로는 못 넘는다** — 그 방향의 상한은 1 − ρ_arms = 0.101 이고 "
         "밴드는 0.1668 이다. ② 넘는 라벨은 존재하지만 그것은 **대조 팔이 음의 상관인 세계**다"
         f"(최적 y 에서 대조 팔 spearman {round(float(spearmanr(-rc, y_adv)[0]), 4)}) — "
         "'국적 팔이 단지 더 낫다'가 아니라 '대조 팔이 틀렸다'는 뜻이다. "
         "③ 닫힌형: 천장/SD = √(m(1−ρ_arms)/2). m=30·ρ=0.899 → 1.23σ. **2σ 를 넘으려면 m > 79** — "
         "이 부분은 옳고 값지다(티처 #51 도 동의·강화)."),
     },

     "ㄴ. 검정력 — annex8 이 천장만 재고 출력을 안 쟀다": {
       "설계": (f"라벨 = 국적 팔 순위 + 정규잡음 · {NSIM}회 · 씨앗 {SEED} · **두 통계에 같은 라벨**을 먹인다. "
              "동결된 순위 벡터만 쓰므로 라벨·자료 무접촉."),
       "곡선": curve,
       "귀무 크기": {"Δρ": round(sz_r / NSIM, 4), "Δ|err|": round(sz_e / NSIM, 4),
                 "'해롭다'": round(sz_h / NSIM, 4)},
       "80% 검정력이 되는 ρ_국적팔": rho_at80,
       "🔴 읽는 법": ("전향 정합 기준은 ρ≈0.2101 이고 동결 문턱은 0.2046 이다. **그 자리에서 검정력은 5% 안팎**이다"
                 "(귀무 크기 2~3%). 즉 이 시험은 **집안에서 본 크기의 효과를 검출할 힘이 사실상 없다.** "
                 "τ = 1.4667 은 ρ_국적팔 ≈ 0.92 짜리 효과에 해당한다 — 이 판이 낸 어떤 도메인 ρ 보다 크다."),
     },

     "ㄷ. 🔴 '없다' 갈래의 판독 조항 — 라벨 이전에 못박는다": {
       "왜 필요한가": ("`harvest885_nation.verdict()` 는 동결이라 못 고친다. 그 함수는 |Δ|err|| ≤ 밴드 이고 "
                  "밴드 < τ 이면 **'없다'** 를 내고, 동결 문면은 그것을 *'의미 있는 크기였다면 발화했을 자인데 "
                  "안 났다 → 집안 전용으로 확정하고 서빙에 안 올린다'* 로 읽으라고 한다. "
                  "**ㄴ 이 보인 것: 그 전제가 거짓이다.** 집안 크기의 효과는 발화 안 한다(검정력 ~5%). "
                  "출력 없는 시험의 음성을 확정 판정으로 승격시키는 조항이다(티처 #51 F3)."),
       "🔴 조항": ("9/28 에 갈래가 **'없다'** 로 나오면 그 문장은 "
               "**'영화 국적은 집 밖에서 죽었다'가 아니라 "
               "'이 30편 시험은 집안에서 본 효과 크기(도메인 +0.0577 · 판 +0.0063)를 검출할 출력이 없었다'** 로 읽는다. "
               "**'집안 전용 확정'도 '서빙 금지 해제'도 하지 않는다** — 국적은 그대로 서빙에 안 올리되, "
               "그 이유는 '집 밖에서 죽어서'가 아니라 **'규약 12 를 아직 못 채워서'** 다. "
               "즉 이 수확은 **증거를 더하지도 빼지도 않는 관측**이 된다."),
       "'좋다'가 나오면": ("검정력이 낮다는 것은 **위양성이 늘어난다는 뜻이 아니다**(귀무 크기 2.7% — 정상). "
                    "그러므로 '좋다'가 나오면 그것은 **진짜 증거**다. 낮은 출력은 음성만 무력화한다."),
       "'해롭다'가 나오면": (f"순수 잡음에서도 {round(sz_h / NSIM, 4)} 로 발화한다. 885 의 집안 통과를 "
                     "**재분류하기 전에** 그 확률을 함께 적는다 — 단발 음성으로 재현된 집안 결과를 뒤집지 않는다."),
     },

     "ㄹ. 티처 #51 F2 반박(내 실측) · M2 등재": {
       "F2 주장": "티처 #51 은 *'Δ|err| 는 ρ_n<0.31 부터 Δρ 보다 나쁘다 — 통계 교체가 아무것도 사지 못했다'* 고 했다.",
       "내 실측": ("**티처가 말한 곳에서는 재현 안 된다.** 같은 라벨을 두 통계에 먹여 **기각률**을 직접 세면 "
               "Δ|err| 가 ρ_국적팔 **0.16 까지** Δρ 를 이긴다(0.315 에서 5.8% 대 3.8% · 0.240 에서 4.8% 대 3.6%). "
               "티처가 역전점이라 한 0.31 에서는 Δ|err| 가 오히려 **1.5배 낫다**. "
               "역전은 ρ_국적팔 ≈ 0.11 부터인데(2.85% 대 2.88%) **거기선 둘 다 귀무 크기라 무의미**하다. "
               "티처는 **평균 통계량의 σ 배수**를 비교했는데 분포 모양이 달라 σ 배수는 검정력이 아니다."),
       "그러나 티처의 경고는 옳다": ("통계 교체가 **산 것은 있지만 충분하지 않다**. 5% 를 8% 로 올린 것은 "
                          "판정을 바꾸지 못한다. **문제는 통계가 아니라 m 이었다** — "
                          "886 이 '통계를 잘못 골랐다'로 착지한 것은 절반만 맞다."),
       "M2 명시 등재(티처 #50 이 지적하고 886 이 결정 없이 넘겼다)": (
         "9/28 에 채점되는 팔은 annex7 의 **학습만 3범주 코딩**이고, 885 헤드라인 +0.0577 을 낸 팔(전체 5범주)이 "
         "**아니다**. 그 팔은 씨앗 3회만 돌았고 **위약 0회 · 씨앗별 미기록**이다. 886 의 M1 검산이 이것을 "
         "날카롭게 만들었다 — 두 팔의 차이는 정확히 **영국·중국 48행 마스크아웃 하나**다. "
         "여기에 annex8 정오2(채움값 0.5 ≡ 미국 코드)가 겹친다. **채점 결과를 읽을 때 셋을 함께 읽는다.**"),
     },

     "지문": {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       capture_output=True, text=True).stdout.strip(),
            "annex7 sha": hashlib.sha256((KD / "annex7_2026-08-09.json").read_bytes()).hexdigest()[:12],
            "annex8 sha": hashlib.sha256((KD / "annex8_2026-08-09.json").read_bytes()).hexdigest()[:12],
            "생산자 sha": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]},
     "🔴 금지": "이 파일도 수정 금지. 더 고칠 것이 생기면 annex10 + 정오 사이드카.",
    }
    with open(OUT, "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "ㄴ. 검정력 — annex8 이 천장만 재고 출력을 안 쟀다"},
                     ensure_ascii=False, indent=1), flush=True)
    print(json.dumps(out["ㄴ. 검정력 — annex8 이 천장만 재고 출력을 안 쟀다"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
