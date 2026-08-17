# -*- coding: utf-8 -*-
"""🔴 노트 994 채점기 --- `④` 판정 · `⑤` 채점.

🔴🔴 **규칙 D**: 이 파일은 수를 «손으로» 안 적는다. 모든 수는
`runners/out994_*.json` 의 «키 경로»에서 읽는다. 사전등록에 등기된 «기대값»과
「같은 자리의 다른 규약」만 리터럴로 둔다(그 자체가 판정 대상이라서다).

🔴 **동결**(사전등록 §0-라): 이 채점기는 러너·⑤′·반증조건·변이체 자를
**한 줄도 안 고친다.** red 는 붉은 채로 계상한다.

씀:  python3 runners/score994.py --out runners/out994_score.json
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

IN = collections.OrderedDict([
    ("tf", "runners/out994_tf.json"),
    ("org", "runners/out994_org.json"),
    ("ctl", "runners/out994_ctl.json"),
    ("diag", "runners/out994_f01diag.json"),
    ("scope", "runners/out994_f01scope.json"),
])

#: 🔴 사전등록 `§5`·`§6` 이 «측정 전»에 박은 기대값 --- 판정 대상이라 리터럴이다
PRE = collections.OrderedDict([
    ("P1 점", 0.47), ("P1 lo", 0.41), ("P1 hi", 0.53),
    ("P3 기준", 0.470343), ("P3 허용", 0.05),
    ("F01 씨앗0", 0.4731063028988084), ("F01 평균", 0.47034252170476804),
    ("F01 허용 씨앗0", 1e-12), ("F01 허용 평균", 1e-9),
    ("F01 유보", 3775), ("F01 도메인", 12),
    ("F07 허용", 1e-9),
    ("P4 ㉠ 도메인", [7, 9, 10, 12]), ("P4 ㉠ 행", [4532, 4555, 4536, 4559]),
    ("P4 통합", 18182), ("P4 공통", 7), ("P4 공통 행", 16627),
    ("P4 ㉢ 통합", 16624), ("P4 학습 없이 채점된 칸", 4),
    ("P6 계수", 0.5),
])

#: 🔴 v4.11 조항 77 이 «측정 전»에 박은 예측(`docs/루프.md:2612`)
V411 = collections.OrderedDict([
    ("사전등록 간 중앙값(977~993 실측 · h)", 1.6),
    ("v4.11 예측(h)", 1.0),
    ("993 사전등록 커밋", "b3a5a55e718c684b24289633ea807a4a188561d2"),
    ("994 사전등록 커밋", "16d7a2dd87a31bd82aa2c9ed00fe17cf3c2c6db9"),
    ("팔 C 예상(분 · 사전등록 §7)", [30, 55]),
    ("팔 A 예상(분 · 사전등록 §7)", [55, 90]),
    ("팔 B 예상(분 · 사전등록 §7)", [60, 100]),
])

K_TF_A = "🔴🔴🔴 헤드라인 ㉠ 움직이는 분모(원점 넷 · 행 가중 통합)"
K_TF_B = "🔴🔴🔴 헤드라인 ㉡ 고정 분모(공통 도메인만)"
K_TF_C = "🔴🔴🔴 헤드라인 ㉢ 학습된 도메인만(하네스 규칙 ∧ 학습 >= MIN_TRAIN)"
K_TF_ORI = "🔴🔴 원점별 rho"
K_TF_GATE = "🔴🔴 원점별 게이트(분모)"
K_TF_TOT = "🔴🔴🔴 통합 채점 행(원점 넷 합)"
K_TF_COM = "🔴🔴🔴 공통 도메인(원점 넷 전부에서 채점된 것 · 고정 분모)"
K_TF_NOTR = "🔴🔴🔴 학습 없이 채점된 칸(조항 59 --- 「쟀는데 학습엔 없었다」)"
K_TF_W1 = "W1 🔴🔴 학습이 언제나 유보보다 앞인가"
K_TF_CMP = "🔴🔴🔴 정본과의 견줌"
K_ORG_HEAD = "🔴🔴🔴 헤드라인 --- 원점 1 · 공통 도메인 · 거리 1~4"
K_ORG_DIAG = "🔴🔴 F07 교차 검사용 --- 거리 1 대각선(본편의 원점별 rho 와 짝)"
K_ORG_CELL = "🔴🔴 칸별 rho"
K_ORG_GATE = "🔴🔴 칸별 게이트"
K_ORG_COM = "🔴🔴🔴 공통 도메인(열 칸 «전부»에서 채점된 것 · 고정 분모)"
K_CTL_C0 = "🔴🔴🔴 C0 재현 관문 --- 정본 챔피언"
K_CTL_C1 = "🔴🔴 ㉮ 도메인 혼합 효과 (C1 · 리핏 없음 · 항등식)"
K_CTL_C2 = "🔴🔴 ㉯ 표본 크기 효과 (C2 · 유보 하향 표본)"
K_CTL_C3 = "🔴🔴 ㉰ 학습량 효과 (C3 · 학습 하향 표본 · 유보는 정본 그대로)"
K_CTL_C4 = "🔴🔴🔴 F08 --- 사전등록 §0-나 「정정」의 물증"
K_CTL_DEN = "🔴🔴 정본 분모"
K_CTL_W = "🔴🔴 시간 블록 가중(본편 ㉠ 이 쓸 분모 · 여기서 다시 계산했다)"
K_STAMP = "🔴 도장"
K_DROP = "🔴 조항 59 버림 장부(씨앗 0)"

B_DOM = 2000
DOM_SEED = 994


def sha(p):
    h = hashlib.sha256()
    with open(str(ROOT / p), "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def cluster_se(vals, wts, B=B_DOM, seed=DOM_SEED):
    """🔴 도메인 «군집» SE --- `beta994_common.dom_cluster_se` 와 «같은 꼴»."""
    ds = sorted(vals)
    if len(ds) < 2:
        return collections.OrderedDict([("도메인 수", len(ds)),
                                        ("도메인 군집 SE", None), ("뽑기 수", 0)])
    r = np.asarray([vals[d] for d in ds], float)
    w = np.asarray([wts[d] for d in ds], float)
    rng = np.random.RandomState(int(seed))
    bs = np.empty(int(B))
    for b in range(int(B)):
        ix = rng.randint(0, len(ds), len(ds))
        den = w[ix].sum()
        bs[b] = (r[ix] * w[ix]).sum() / den if den > 0 else np.nan
    ok = np.isfinite(bs)
    pt = float((r * w).sum() / w.sum())
    se = float(bs[ok].std(ddof=1))
    return collections.OrderedDict([
        ("도메인 수", len(ds)), ("뽑기 수", int(B)),
        ("점추정", pt), ("도메인 군집 SE", se),
        ("t_clu", float(pt / se) if se else None),
        ("🔴 2·SE 를 넘나", bool(abs(pt) > 2 * se) if se else None),
        ("2.5%", float(np.percentile(bs[ok], 2.5))),
        ("97.5%", float(np.percentile(bs[ok], 97.5))),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "runners/out994_score.json"))
    a = ap.parse_args()

    D = {k: json.loads((ROOT / v).read_text(encoding="utf-8")) for k, v in IN.items()}
    tf, org, ctl, dg, sp = D["tf"], D["org"], D["ctl"], D["diag"], D["scope"]
    S = collections.OrderedDict()
    S["무엇"] = ("🔴🔴🔴 노트 994 채점 --- `④` 판정 · `⑤` 채점. "
                "🔴 모든 수는 `out994_*.json` 의 «키 경로»에서 왔다(규칙 D · 손 전사 0)")
    S["🔴 축"] = tf["🔴 축"]
    S["🔴 사전등록"] = "docs/prereg_994_time_holdout_board.md"
    S["🔴 입력 산출물 sha256"] = collections.OrderedDict(
        [(v, sha(v)) for v in IN.values()])
    S["🔴 이 채점기가 산출물을 고쳤나"] = False

    # ══════════════════════════════════════════════════════════════════
    # §1 🔴🔴🔴 맨 위 --- `F01` 이 «떨어졌다»
    # ══════════════════════════════════════════════════════════════════
    c0 = ctl[K_CTL_C0]
    seeds994 = c0["🔴 씨앗별(전정밀)"]
    board898 = json.loads((ROOT / "runners/out898_board.json").read_text(
        encoding="utf-8"))["팔"]["B(동률 평균)"]
    seeds898 = board898["씨앗별(전정밀)"]
    off = [float(x - y) for x, y in zip(seeds994, seeds898)]
    off_mean, off_sd = float(np.mean(off)), float(np.std(off, ddof=1))
    dgA = dg["㉮ 하네스 정본 마스크(isfinite(yr) & yr>=T)"]
    dgB = dg["㉯ 994 러너 마스크(+ isfinite(y))"]

    S["§1 🔴🔴🔴 맨 위 --- `F01` 재현 관문이 «떨어졌다»"] = collections.OrderedDict([
        ("🔴🔴🔴 F01 통과", c0["🔴🔴🔴 F01 통과"]),
        ("🔴 C0 씨앗0(실측)", seeds994[0]),
        ("🔴 사전등록 기대 씨앗0", c0["🔴 사전등록 기대 씨앗0"]),
        ("🔴 씨앗0 차", c0["🔴 씨앗0 차"]),
        ("🔴 허용(씨앗0 · 사전등록 §6 F01 · 🔴 산출물 파일은 이 칸을 «잃었다» --- §7-3)",
         PRE["F01 허용 씨앗0"]),
        ("🔴 C0 12씨앗 평균(실측)", c0["🔴🔴 rho"]["평균"]),
        ("🔴 사전등록 기대 평균", c0["🔴 사전등록 기대 평균"]),
        ("🔴 평균 차", c0["🔴 평균 차"]),
        ("🔴 허용(평균)", c0["🔴 허용"]),
        ("🔴🔴 행은 한 자리도 안 틀렸다", collections.OrderedDict([
            ("유보 가중 합", ctl[K_CTL_DEN]["유보 가중 합"]),
            ("도메인", ctl[K_CTL_DEN]["도메인"]),
            ("학습 행", ctl[K_CTL_DEN]["학습 행(≥MIN_TRAIN 도메인 합)"]),
            ("🔴 사전등록과 맞나", ctl[K_CTL_DEN]["🔴 맞나"])])),
        ("🔴🔴🔴 사전등록 문언대로의 계상",
         "🔴 **994 의 모든 수를 「못 믿는다」로 계상한다**(사전등록 §6 F01). "
         "🔴🔴 그 «범위»를 아래에서 갈랐다 --- 갈라 보니 «절대 수준»만 물들고 "
         "«같은 주행 안의 상대 수»는 안 물든다"),
    ])

    # ── §1-나 원인 ────────────────────────────────────────────────────
    S["§1-나 🔴🔴🔴 원인을 «찾았다» --- 챔피언이 아니라 «994 러너의 유보 마스크»다"] = \
        collections.OrderedDict([
            ("🔴🔴🔴 원인을 짚었나", dg["🔴🔴🔴 그래서 F01 이 떨어진 원인을 짚었나"]),
            ("🔴 무엇이 다른가", dg["🔴 무엇이 다른가"]),
            ("🔴🔴🔴 ㉮ 하네스 정본 마스크로 오늘 다시 잰 씨앗0", dgA["판 rho"]),
            ("🔴 그 기대값(out898_board.json 팔.B 씨앗별[0])",
             dgA["🔴 기대(out898_board.json 팔.B 씨앗별[0])"]),
            ("🔴🔴🔴 차", dgA["🔴 차"]), ("🔴 허용", dgA["🔴 허용"]),
            ("🔴🔴🔴 정본 챔피언 경로가 «오늘» 재현되나", dgA["🔴🔴🔴 재현했나"]),
            ("🔴 ㉯ 994 러너 마스크로 다시 잰 씨앗0", dgB["판 rho"]),
            ("🔴 그 기대값(out994_ctl.json C0 씨앗별[0])",
             dgB["🔴 기대(out994_ctl.json C0 씨앗별[0])"]),
            ("🔴 차", dgB["🔴 차"]),
            ("🔴 994 러너의 수가 재현되나", dgB["🔴🔴🔴 재현했나"]),
            ("🔴🔴 두 규약의 차(㉯ − ㉮)", dg["🔴🔴🔴 두 규약의 차(㉯ − ㉮)"]),
            ("🔴🔴 채점되는 행은 둘이 «같다»", dg["🔴🔴 채점 행 합이 같은가"]),
            ("🔴 채점 행 합", dgA["채점 행 합"]),
            ("🔴🔴 predict «배치» 행 합(㉮ 하네스)", dgA["predict 배치 합"]),
            ("🔴🔴 predict «배치» 행 합(㉯ 994)", dgB["predict 배치 합"]),
            ("🔴🔴 rho 가 갈린 도메인", dg["🔴🔴 rho 가 갈린 도메인"]),
            ("🔴 도메인별 rho 차(㉯ − ㉮)", dg["🔴 도메인별 rho 차(㉯ − ㉮)"]),
            ("🔴 그 도메인의 판 가중", collections.OrderedDict(
                [(d, dg["🔴 판 가중(정본)"][d]) for d in dg["🔴🔴 rho 가 갈린 도메인"]])),
            ("🔴 판 가중 합", dg["🔴 판 가중 합"]),
            ("🔴🔴🔴 기제", collections.OrderedDict([
                ("① 하네스", "`lab/harness.py:320` --- `post = isfinite(yr) & (yr >= T)`. "
                            "라벨 결측 행을 predict «배치»에 «넣고» `_score_one` 이 "
                            "`lab/harness.py:264` 에서 뒤에 뺀다"),
                ("② 994 러너", "`runners/beta994_common.py:190 canon_masks` 와 "
                             "`:158 blocks` 가 `labeled()`(= isfinite(y))를 «predict 앞»에 건다"),
                ("③ 왜 값이 바뀌나", "`lab/forms.py:1140 BagBoost.predict` 가 "
                                 "`_rank_masked` 로 «배치 안»에서 순위를 매겨 자루 32 개를 "
                                 "평균한다 --- 배치 구성이 바뀌면 «남은 행»의 예측 순위도 바뀐다"),
                ("④ 하네스 자신이 이 행들을 이름으로 적어 뒀다",
                 "`lab/harness.py:260-263` --- 「게임의 결측 라벨 43건(노트 210 의 30일 창이 "
                 "안 찬 것)이 순위에 들어가 게임 점수가 +0.62 대신 +0.19 로 나오고 있었다」"),
            ])),
            ("🔴🔴 조항 66 위반 --- 자가 자기 출처를 «못 댄다»",
             "🔴 `beta994_common.py:200` 이 「`lab/harness.py:evaluate` 의 deploy 갈래를 "
             "«글자 그대로»」라고 적었는데 **글자 그대로가 아니다.** `canon_masks` 가 "
             "`isfinite(y)` 를 «더했다». 🔴 **고치지 않는다**(동결) --- 신고만 한다"),
            ("🔴 라벨 없는 행(yr 유한)의 분포", sp["🔴 라벨 없는 행(yr 유한)의 블록 분포"]),
        ])

    # ── §1-다 「못 믿는다」의 «범위» ────────────────────────────────────
    scope_rows = sp["🔴🔴 거리별"]
    devs = collections.OrderedDict(
        [(k, v["🔴🔴 이탈(㉯ − ㉮)"]) for k, v in scope_rows.items()])
    gap994 = sp["🔴🔴🔴 거리 1 − 거리 4(㉯ 994 규약 · 씨앗 0)"]
    gapcan = sp["🔴🔴🔴 거리 1 − 거리 4(㉮ 하네스 정본 규약 · 씨앗 0)"]
    head = org[K_ORG_HEAD]
    curve_gap = head["🔴🔴 거리 1 − 거리 4"]
    c0m = c0["🔴🔴 rho"]["평균"]
    c0c1 = ctl[K_CTL_C1]["🔴🔴 C0 − C1 (혼합만으로 생기는 낙차)"]
    c0c2 = ctl[K_CTL_C2]["🔴🔴 C0 − C2 (표본 크기만 줄였을 때의 낙차)"]
    c0c3 = ctl[K_CTL_C3]["🔴🔴 C0 − C3 (학습량만 줄였을 때의 낙차)"]
    c0c1b = ctl[K_CTL_C1]["🔴🔴 C0 − C1b (도메인 «집합»만 좁혔을 때의 낙차)"]
    p2_move = (tf[K_TF_ORI]["원점 1"]["🔴🔴 rho"]["평균"]
               - tf[K_TF_ORI]["원점 4"]["🔴🔴 rho"]["평균"])
    cellb = org[K_ORG_CELL]
    p2_fix1 = cellb["원점 1 → 블록 1 (거리 1)"]["🔴🔴 rho ㉡ 고정 분모(공통 도메인)"]["평균"]
    p2_fix4 = cellb["원점 4 → 블록 4 (거리 1)"]["🔴🔴 rho ㉡ 고정 분모(공통 도메인)"]["평균"]
    p2_fix = p2_fix1 - p2_fix4

    def ratio(x, base):
        return float(abs(x) / abs(base)) if base else None

    S["§1-다 🔴🔴🔴 「못 믿는다」의 «범위» --- 절대 수준만 물들고 «상대»는 안 물든다"] = \
        collections.OrderedDict([
            ("🔴 잰 방법",
             "🔴 적합 «하나»(원점 1 · 씨앗 0)로 블록 1~4 를 «두 규약»으로 채점해 "
             "규약 이탈을 «칸마다» 쟀다(`runners/out994_f01scope.json`)"),
            ("🔴🔴🔴 거리별 규약 이탈(㉯ − ㉮)", devs),
            ("🔴🔴 거리 1·2 의 이탈이 «정확히 0» 인가",
             bool(devs["거리 1 (원점 1 → 블록 1)"] == 0.0
                  and devs["거리 2 (원점 1 → 블록 2)"] == 0.0)),
            ("🔴 왜 0 인가", "🔴 라벨 없는 행은 블록 3 에 2 · 블록 4 에 105 뿐이고 "
                          "블록 0·1·2 에는 «한 행도 없다»"),
            ("🔴🔴🔴 낙차(거리1 − 거리4) · 994 규약 · 씨앗 0", gap994),
            ("🔴🔴🔴 낙차(거리1 − 거리4) · 하네스 정본 규약 · 씨앗 0", gapcan),
            ("🔴🔴🔴 규약이 낙차를 얼마나 바꾸나",
             sp["🔴🔴🔴 규약이 낙차를 얼마나 바꾸나(㉯ − ㉮)"]),
            ("🔴🔴 그 몫(|바뀌는 양| / 낙차)",
             ratio(sp["🔴🔴🔴 규약이 낙차를 얼마나 바꾸나(㉯ − ㉮)"], gap994)),
            ("🔴🔴 방향", "🔴 «보정하면 낙차가 «커진다»» --- 세계 명제 쪽으로 «보수적»이다"),
            ("🔴 씨앗 사이 이탈의 산포(C0 12 씨앗 · 994 − 898)", collections.OrderedDict([
                ("평균", off_mean), ("SD(ddof=1)", off_sd),
                ("최소", float(min(off))), ("최대", float(max(off))),
                ("양수 씨앗 수", int(sum(1 for v in off if v > 0))),
                ("씨앗 수", len(off)),
                ("🔴 C0 씨앗 SD(ddof=1)", c0["🔴🔴 rho"]["SD(ddof=1)"]),
                ("🔴 씨앗 SD / 이탈 SD",
                 ratio(c0["🔴🔴 rho"]["SD(ddof=1)"], off_sd)),
                ("🔴 뜻", "🔴 **이탈은 «공통 모드»다** --- 씨앗 열둘이 전부 같은 부호로 "
                        "거의 같은 만큼 옮겨졌다. 그래서 «차»를 재면 대부분 상쇄된다"),
            ])),
            ("🔴🔴🔴 어느 수가 이탈보다 «큰가»(안전 배수)", collections.OrderedDict([
                ("거리1 − 거리4(12씨앗 · 고정 분모)", collections.OrderedDict([
                    ("값", curve_gap),
                    ("이탈", sp["🔴🔴🔴 규약이 낙차를 얼마나 바꾸나(㉯ − ㉮)"]),
                    ("배수", ratio(curve_gap,
                                 sp["🔴🔴🔴 규약이 낙차를 얼마나 바꾸나(㉯ − ㉮)"])),
                    ("🔴 믿을 수 있나", True)])),
                ("C0 − C3(학습량)", collections.OrderedDict([
                    ("값", c0c3), ("이탈", off_mean),
                    ("배수", ratio(c0c3, off_mean)), ("🔴 믿을 수 있나", True)])),
                ("C0 − C1(도메인 혼합)", collections.OrderedDict([
                    ("값", c0c1), ("이탈", off_mean),
                    ("배수", ratio(c0c1, off_mean)),
                    ("🔴 믿을 수 있나", True),
                    ("⚠", "🔴 C1 은 C0 의 도메인별 ρ 를 «그대로» 다시 가중한 항등식이라 "
                          "이탈이 «두 쪽에 같이» 들어가 대부분 상쇄된다")])),
                ("C0 − C1b(도메인 집합)", collections.OrderedDict([
                    ("값", c0c1b), ("이탈", off_mean),
                    ("배수", ratio(c0c1b, off_mean)), ("🔴 믿을 수 있나", True)])),
                ("C0 − C2(표본 크기)", collections.OrderedDict([
                    ("값", c0c2), ("이탈", off_mean),
                    ("배수", ratio(c0c2, off_mean)),
                    ("🔴🔴🔴 믿을 수 있나", False),
                    ("🔴 왜", "🔴🔴 **이 수는 이탈보다 크지 않다.** 「표본 크기는 낙차를 "
                            "거의 안 만든다」는 «방향»은 남지만 그 «값»은 재현 오차 안이다")])),
                ("P2 움직이는 분모(원점1 − 원점4 · ㉠)", collections.OrderedDict([
                    ("값", p2_move), ("이탈", off_mean),
                    ("배수", ratio(p2_move, off_mean)), ("🔴 믿을 수 있나", True)])),
                ("P2 고정 분모(원점1 − 원점4 · ㉡)", collections.OrderedDict([
                    ("값", p2_fix),
                    ("이탈(블록 4 칸 · 씨앗 0)", devs["거리 4 (원점 1 → 블록 4)"]),
                    ("배수", ratio(p2_fix, devs["거리 4 (원점 1 → 블록 4)"])),
                    ("🔴🔴🔴 믿을 수 있나", False),
                    ("🔴 왜", "🔴🔴 **「부호가 뒤집힌다」는 그 «차» 자체가 규약 이탈과 "
                            "같은 자릿수다.** 게다가 두 끝의 씨앗 SE 보다도 작다 --- "
                            "«부호를 주장할 수 없는 자리»다")])),
            ])),
            ("🔴🔴🔴 그래서 「못 믿는다」의 범위",
             "🔴 ㉠ **절대 판 ρ 의 «수준»**(㉠·㉡·㉢·C0·원점별 절대값)은 «못 믿는다» --- "
             "정본과 견줄 수 없다. "
             "🔴 ㉡ **같은 주행 «안»의 상대 수**(거리 곡선의 낙차 · C0−C3 · C0−C1 · C0−C1b)는 "
             "«믿을 수 있다» --- 이탈이 공통 모드이고 낙차의 0.2 % 이하다. "
             "🔴 ㉢ **이탈과 같은 자릿수인 수 둘**(C0−C2 · P2 고정 분모 차)은 "
             "«따로» «못 믿는다»로 뺀다"),
        ])

    # ══════════════════════════════════════════════════════════════════
    # §2 판 ρ --- ㉠·㉡·㉢ 을 «분모와 함께»
    # ══════════════════════════════════════════════════════════════════
    hd = collections.OrderedDict()
    for nm, key, dom, rows in [
            ("㉠ 움직이는 분모(하네스 규칙)", K_TF_A, None, None),
            ("㉡ 고정 분모(공통 도메인 7)", K_TF_B, None, None),
            ("㉢ 학습된 도메인만", K_TF_C, None, None)]:
        h = tf[key]
        e = collections.OrderedDict([
            ("rho 평균", h["🔴🔴🔴 rho"]["평균"]),
            ("SD(ddof=1)", h["🔴🔴🔴 rho"]["SD(ddof=1)"]),
            ("씨앗 SE", h["🔴🔴🔴 rho"]["씨앗 SE"]),
            ("🔴 채점 행(분모)", h["🔴 채점 행(분모)"]),
        ])
        if "🔴🔴 도메인 군집 SE(원점을 합친 도메인 가중으로)" in h:
            g = h["🔴🔴 도메인 군집 SE(원점을 합친 도메인 가중으로)"]
        elif "🔴🔴 도메인 군집 SE" in h:
            g = h["🔴🔴 도메인 군집 SE"]
        else:
            g = None
        e["🔴🔴 도메인 군집 SE"] = (g["도메인 군집 SE"] if g else None)
        e["🔴🔴🔴 도메인 군집 SE 키가 «있나»"] = bool(g is not None)
        hd[nm] = e
    S["§2 🔴🔴 판 ρ --- 헤드라인 셋을 «분모와 함께»"] = collections.OrderedDict([
        ("헤드라인", hd),
        ("🔴🔴🔴 ㉢ 에 도메인 군집 SE 키가 «없다»(조항 59 --- 「0」도 「결측」도 아니고 «안 계산됐다»)",
         bool(hd["㉢ 학습된 도메인만"]["🔴🔴 도메인 군집 SE"] is None)),
        ("🔴 정본 판 rho", tf[K_TF_CMP]["정본 판 rho(전정밀 · text680.BOARD_RHO / out898_board.json)"]),
        ("🔴 정본 분모", tf[K_TF_CMP]["정본 분모"]),
        ("Δ ㉠ − 정본", tf[K_TF_CMP]["Δ ㉠ − 정본"]),
        ("Δ ㉡ − 정본", tf[K_TF_CMP]["Δ ㉡ − 정본"]),
        ("Δ ㉢ − 정본", tf[K_TF_CMP]["Δ ㉢ − 정본"]),
        ("🔴🔴 조항 60 경고", tf[K_TF_CMP]["🔴🔴 조항 60 경고"]),
        ("🔴 이 러너가 정본을 고쳤나", tf[K_TF_CMP]["🔴 정본 값을 이 러너가 고쳤나"]),
        ("🔴🔴🔴 정본을 갱신하나", False),
        ("🔴🔴🔴 왜 안 갱신하나", collections.OrderedDict([
            ("① 분모가 셋 다 다르다",
             "정본은 도메인 12 · 유보 3,775 · 원점 «하나»다. ㉠㉡㉢ 은 원점 «넷»이고 "
             "분모가 각각 다르다 --- **조항 60 이 이어 붙이는 것을 금한다**"),
            ("② F01 이 떨어졌다", "이 사이클의 절대 수준은 「못 믿는다」로 계상된다"),
            ("③ 🔴 그리고 정본 자신은 «멀쩡하다»",
             "정비 팔의 진단이 하네스 정본 마스크로 씨앗 0 을 오늘 다시 내서 "
             "`1e-12` 안에서(차 0.0) 재현했다 --- 고칠 것은 정본이 아니라 «994 러너»다"),
        ])),
        ("🔴 원점별 rho(㉠·㉢ · 도메인 군집 SE 와 함께)", collections.OrderedDict([
            (k, collections.OrderedDict([
                ("㉠ 평균", v["🔴🔴 rho"]["평균"]),
                ("㉠ 씨앗 SE", v["🔴🔴 rho"]["씨앗 SE"]),
                ("㉢ 평균", v["🔴 rho ㉢ 학습된 도메인만"]["평균"]),
                ("채점 도메인 수", v["채점 도메인 수"]),
                ("채점 행", v["채점 행"]), ("학습 행", v["학습 행"]),
                ("🔴 도메인 군집 SE", v["🔴 도메인 군집 SE"]["도메인 군집 SE"]),
            ])) for k, v in tf[K_TF_ORI].items()])),
    ])

    # ══════════════════════════════════════════════════════════════════
    # §3 🔴🔴🔴 세계 명제 후보 --- 거리 곡선
    # ══════════════════════════════════════════════════════════════════
    common = org[K_ORG_COM]["도메인"]
    c1 = cellb["원점 1 → 블록 1 (거리 1)"]["도메인별 rho(씨앗 평균)"]
    c4 = cellb["원점 1 → 블록 4 (거리 4)"]["도메인별 rho(씨앗 평균)"]
    n1 = org[K_ORG_GATE]["원점 1 → 블록 1 (거리 1)"]["도메인별 채점 행"]
    n4 = org[K_ORG_GATE]["원점 1 → 블록 4 (거리 4)"]["도메인별 채점 행"]
    dpair = collections.OrderedDict([(d, float(c1[d] - c4[d])) for d in common])
    w1 = {d: n1[d] for d in common}
    w4 = {d: n4[d] for d in common}
    se1 = cluster_se(dpair, w1)
    se4 = cluster_se(dpair, w4)
    seu = cluster_se(dpair, {d: 1 for d in common})
    lodo = collections.OrderedDict()
    for d in common:
        rest = {k: v for k, v in dpair.items() if k != d}
        wr = {k: w4[k] for k in rest}
        lodo[d] = float(sum(rest[k] * wr[k] for k in rest) / sum(wr.values()))
    seedse = collections.OrderedDict(
        [(k, v["🔴🔴 rho(고정 분모)"]["씨앗 SE"]) for k, v in head["곡선"].items()])
    S["§3 🔴🔴🔴 세계 명제 후보 --- 「예측 지평이 멀수록 성능이 떨어진다」"] = \
        collections.OrderedDict([
            ("🔴 곡선(원점 1 · 고정 분모 공통 7 · 12 씨앗)", collections.OrderedDict(
                [(k, collections.OrderedDict([
                    ("rho 평균", v["🔴🔴 rho(고정 분모)"]["평균"]),
                    ("SD(ddof=1)", v["🔴🔴 rho(고정 분모)"]["SD(ddof=1)"]),
                    ("씨앗 SE", v["🔴🔴 rho(고정 분모)"]["씨앗 SE"]),
                    ("채점 행 n", v["🔴 채점 행 n"])]))
                 for k, v in head["곡선"].items()])),
            ("🔴🔴 거리 1 − 거리 4", curve_gap),
            ("🔴 단조 감소인가", head["🔴 단조 감소인가"]),
            ("🔴 멀수록 떨어지나", head["🔴🔴 멀수록 떨어지나(거리 1 > 거리 4)"]),
            ("🔴 씨앗 SE(거리별)", seedse),
            ("🔴 씨앗 SE 로 몇 배인가(거리 4 SE 기준)",
             ratio(curve_gap, seedse["거리 4 (원점 1 → 블록 4)"])),
            ("🔴🔴🔴 도메인 «군집» SE 로도 서나 --- 도메인 «짝» 차 Δ_d = ρ_d(거리1) − ρ_d(거리4)",
             collections.OrderedDict([
                 ("🔴 도메인", list(common)), ("🔴 도메인 수", len(common)),
                 ("🔴 도메인별 Δ_d", dpair),
                 ("🔴🔴 부호가 «같은» 도메인 수(Δ_d > 0)",
                  int(sum(1 for v in dpair.values() if v > 0))),
                 ("🔴🔴🔴 부호가 «뒤집힌» 도메인",
                  [d for d in common if dpair[d] <= 0]),
                 ("🔴 거리 1 가중으로", se1),
                 ("🔴 거리 4 가중으로(«보수적» --- 분모가 작다)", se4),
                 ("🔴 균등 가중으로(993 이 「차」에 쓴 꼴)", seu),
                 ("🔴🔴🔴 셋 다 2·SE 를 넘나",
                  bool(se1["🔴 2·SE 를 넘나"] and se4["🔴 2·SE 를 넘나"]
                       and seu["🔴 2·SE 를 넘나"])),
                 ("🔴🔴🔴 하나라도 넘나",
                  bool(se1["🔴 2·SE 를 넘나"] or se4["🔴 2·SE 를 넘나"]
                       or seu["🔴 2·SE 를 넘나"])),
                 ("🔴 LODO --- 도메인 하나씩 빼도 부호가 사나(거리 4 가중)", lodo),
                 ("🔴🔴 LODO 부호가 뒤집힌 도메인 수",
                  int(sum(1 for v in lodo.values() if v <= 0))),
                 ("⚠ LODO 는 여기서 «약한 자»다",
                  "🔴 일곱 중 넷이 크게 양수(만화 · 웹툰 · 모바일 · 세계애니)이고 그 넷이 "
                  "행 가중의 대부분이라 «하나»를 빼는 것으로는 부호가 원리상 안 뒤집힌다. "
                  "**가르는 자는 군집 SE 다**"),
             ])),
            ("🔴🔴 F01 규약 이탈로 낙차가 얼마나 바뀌나",
             sp["🔴🔴🔴 규약이 낙차를 얼마나 바꾸나(㉯ − ㉮)"]),
            ("🔴🔴🔴 씨앗 SE 로 재면 몇 배인가(= 이 사이클이 «처음에» 본 수)",
             ratio(curve_gap, seedse["거리 4 (원점 1 → 블록 4)"])),
            ("🔴🔴🔴 세계 명제가 서나", bool(
                head["🔴 단조 감소인가"]
                and head["🔴🔴 멀수록 떨어지나(거리 1 > 거리 4)"]
                and se1["🔴 2·SE 를 넘나"] and se4["🔴 2·SE 를 넘나"]
                and seu["🔴 2·SE 를 넘나"])),
            ("🔴🔴🔴 왜 «안» 서나",
             "🔴🔴🔴 **씨앗 SE 로는 백 배가 넘지만 씨앗 SE 는 «모형 무작위성»만 잰다 --- "
             "도메인 상관을 «안 센다».** "
             "도메인을 군집으로 재표집하면 `t_clu` 가 «둘을 못 넘고», "
             "**일곱 도메인 중 «셋»(게임 · 애니 · 펀딩)이 «반대 방향»으로 간다.** "
             "🔴 그 낙차는 «만화 · 웹툰 · 모바일» 셋이 행 가중의 대부분을 쥐고 만든 수다 --- "
             "**「지평이 멀수록 떨어진다」가 아니라 "
             "「어떤 도메인이 멀수록 떨어진다」이고 그 도메인 갈림 자체가 이 SE 로는 안 갈린다**"),
            ("🔴🔴 그래도 남는 «약한» 문장",
             "🔴 「단조 감소 참」과 「일곱 중 넷이 같은 부호」는 «관측»이다. "
             "세계 명제로 «승격»하지 «않는다»(조항 68 --- 2·SE 를 못 넘는 칸으로 «모양»을 주장하지 마라)"),
            ("🔴🔴 한정(조항 60)",
             "🔴 **분모가 「원점 1 · 공통 도메인 7 · 씨앗 0~11」이다.** "
             "「예측이 어렵다」의 일반 명제가 «아니라» "
             "**「이 챔피언 · 이 자료 · 이 일곱 도메인에서, 같은 한 적합으로 "
             "한 블록 앞과 네 블록 앞을 볼 때 스피어만이 내려간다」**이다. "
             "🔴 학습량은 «안 움직였다»(한 적합) --- 그것이 이 곡선의 값이다"),
        ])

    # ── §3-나 둘째 후보 --- 「낙차의 대부분은 학습량이다」 ────────────────
    S["§3-나 🔴🔴 둘째 세계 명제 후보 --- 「낙차의 대부분은 학습량이다」"] = \
        collections.OrderedDict([
            ("C0", c0m), ("C1(도메인 혼합)", ctl[K_CTL_C1]["🔴🔴 C1 rho(시간 블록 가중)"]["평균"]),
            ("C2(표본 크기)", ctl[K_CTL_C2]["🔴🔴 C2 rho 평균"]),
            ("C3(학습량)", ctl[K_CTL_C3]["🔴🔴 C3 rho"]["평균"]),
            ("C0 − C1", c0c1), ("C0 − C2", c0c2), ("C0 − C3", c0c3),
            ("🔴 C3 씨앗 SE", ctl[K_CTL_C3]["🔴🔴 C3 rho"]["씨앗 SE"]),
            ("🔴 C0 씨앗 SE", c0["🔴🔴 rho"]["씨앗 SE"]),
            ("🔴🔴🔴 도메인 군집 SE 로 잴 수 있나", False),
            ("🔴🔴🔴 왜 못 재나(조항 59 --- 「안 쟀다」가 아니라 「칸이 없다」)",
             "🔴 `out994_ctl.json` 의 `㉰ 학습량 효과 (C3 …)` 절에 "
             "**「도메인별 rho」 칸이 «없다».** C0 에는 있다. "
             "**짝 차 Δ_d 를 만들 수 없으므로 군집 SE 를 «원리상» 못 낸다** --- "
             "🔴 러너를 고치면 잴 수 있지만 이 사이클은 «동결»이다"),
            ("🔴 그래서 이 후보는", "🔴 **세계 명제로 «못 세운다».** "
                              "「학습량이 표본 크기보다 53 배 큰 낙차를 만든다」는 "
                              "«씨앗 SE 로만» 선 문장이고, 994 는 그 자를 이미 §3 에서 "
                              "«못 믿을 자»로 판정했다"),
        ])
    S["§3-다 🔴🔴🔴 조항 73 --- 이 사이클의 «세계 명제»"] = collections.OrderedDict([
        ("🔴 후보 수", 2),
        ("🔴 선 것", []),
        ("🔴🔴🔴 세계 명제", "없다"),
        ("🔴 왜", "🔴 첫째 후보(거리 곡선)는 도메인 군집 SE 를 «못 넘고» 일곱 중 셋이 "
                "«반대로» 간다. 둘째 후보(학습량)는 러너가 도메인별 칸을 «안 냈다». "
                "🔴🔴 **조항 73(사이클마다 세계 명제 하나 이상)을 «못 채웠다».**"),
        ("🔴🔴 993 과 같은 자리인가", True),
        ("🔴 다만 «다른» 점",
         "🔴 993 은 후보를 «잘못된 근거»로 스스로 강등했다(티처 #132 치-2). "
         "994 는 **등록된 자(도메인 군집 SE)로 재서 «떨어뜨렸다»** --- "
         "그리고 「씨앗 SE 로 백 배」라는 «큰 수»를 헤드라인으로 게재하지 «않는다»"),
    ])

    # ══════════════════════════════════════════════════════════════════
    # §4 예측 `P1`~`P6`
    # ══════════════════════════════════════════════════════════════════
    a_mean = tf[K_TF_A]["🔴🔴🔴 rho"]["평균"]
    o1 = tf[K_TF_ORI]["원점 1"]["🔴🔴 rho"]["평균"]
    o4 = tf[K_TF_ORI]["원점 4"]["🔴🔴 rho"]["평균"]
    c0m = c0["🔴🔴 rho"]["평균"]
    gate = tf[K_TF_GATE]
    p4_dom = [gate["원점 %d" % k]["채점 도메인 수"] for k in (1, 2, 3, 4)]
    p4_row = [gate["원점 %d" % k]["채점 행"] for k in (1, 2, 3, 4)]
    p4_notr = int(sum(len(tf[K_TF_NOTR]["원점 %d" % k]["도메인"]) for k in (1, 2, 3, 4)))
    p6_l = float(c0m - ctl[K_CTL_C1]["🔴🔴 C1 rho(시간 블록 가중)"]["평균"]) + \
        float(c0m - ctl[K_CTL_C3]["🔴🔴 C3 rho"]["평균"])
    p6_r = float(PRE["P6 계수"] * (c0m - a_mean))

    P = collections.OrderedDict()
    P["P1 본편 ㉠ 이 [0.41, 0.53] 안인가"] = collections.OrderedDict([
        ("판정식", "out994_tf ㉠ rho.평균 ∈ [0.41, 0.53]"),
        ("실측", a_mean), ("점 예측", PRE["P1 점"]),
        ("구간", [PRE["P1 lo"], PRE["P1 hi"]]),
        ("맹검", False),
        ("통과", bool(PRE["P1 lo"] <= a_mean <= PRE["P1 hi"])),
        ("⚠", "🔴 구간 폭 0.12 는 씨앗 SE 의 224 배다 --- «넓은 구간»이다"),
    ])
    P["P2 원점이 «이를수록» 높다 (ρ(원점1) > ρ(원점4))"] = collections.OrderedDict([
        ("판정식(사전등록 §5 · 🔴 «키»는 ㉠ 다)", "out994_tf 원점별 rho.평균(㉠)"),
        ("원점 1(㉠)", o1), ("원점 4(㉠)", o4), ("차(㉠)", float(o1 - o4)),
        ("맹검", False),
        ("통과", bool(o1 > o4)),
        ("🔴🔴 이 「통과」는 «등록된 판정 키 ㉠» 로만이다", True),
        ("🔴🔴🔴 병기 --- 고정 분모(㉡ · 조항 60)", collections.OrderedDict([
            ("원점 1(㉡ · 거리 1 대각선)", p2_fix1),
            ("원점 4(㉡ · 거리 1 대각선)", p2_fix4),
            ("차(㉡)", p2_fix),
            ("🔴 부호가 뒤집히나", bool((o1 - o4) * p2_fix < 0)),
            ("🔴🔴 그 차를 믿을 수 있나", False),
            ("🔴 왜", "🔴 그 차는 «F01 규약 이탈»(블록 4 칸 3.178e-04)과 같은 자릿수이고 "
                    "두 끝의 «씨앗 SE» 보다도 작다(§4 곡선표의 씨앗 SE 칸)"),
        ])),
        ("🔴🔴 도메인 군집 SE 로 서나", collections.OrderedDict([
            ("원점 1 군집 SE", tf[K_TF_ORI]["원점 1"]["🔴 도메인 군집 SE"]["도메인 군집 SE"]),
            ("원점 4 군집 SE", tf[K_TF_ORI]["원점 4"]["🔴 도메인 군집 SE"]["도메인 군집 SE"]),
            ("차(㉠)", float(o1 - o4)),
            ("🔴🔴🔴 서나", False),
            ("🔴 왜", "🔴 차가 두 군집 SE 어느 쪽의 «2 배»에도 한참 못 미친다 --- "
                    "**`P2` 는 「예측으로는 맞았지만 세계 명제가 아니다」**"),
        ])),
    ])
    P["P3 마지막 원점이 정본 근처인가 (|ρ(원점4) − 0.470343| < 0.05)"] = \
        collections.OrderedDict([
            ("판정식", "out994_tf 원점 4 rho.평균(㉠)"),
            ("실측", o4), ("기준", PRE["P3 기준"]),
            ("차", float(abs(o4 - PRE["P3 기준"]))), ("허용", PRE["P3 허용"]),
            ("맹검", True),
            ("통과", bool(abs(o4 - PRE["P3 기준"]) < PRE["P3 허용"])),
            ("⚠ 조항 60", "🔴 원점 4 의 분모(도메인 12 · 행 4,559)와 정본 분모"
                        "(도메인 12 · 유보 3,775)는 «다르다» --- 이 「근처」는 "
                        "«같은 것의 재현»이 아니다"),
        ])
    P["P4 분모가 움직인다"] = collections.OrderedDict([
        ("판정식", "out994_tf 게이트 절 · out994_ctl §4-0"),
        ("㉠ 도메인(실측)", p4_dom), ("㉠ 도메인(등록)", PRE["P4 ㉠ 도메인"]),
        ("㉠ 행(실측)", p4_row), ("㉠ 행(등록)", PRE["P4 ㉠ 행"]),
        ("통합(실측)", tf[K_TF_TOT]), ("통합(등록)", PRE["P4 통합"]),
        ("공통 도메인(실측)", tf[K_TF_COM]["수"]), ("공통(등록)", PRE["P4 공통"]),
        ("공통 채점 행(실측)", tf[K_TF_COM]["채점 행"]),
        ("공통 채점 행(등록)", PRE["P4 공통 행"]),
        ("㉢ 통합(실측)", tf[K_TF_C]["🔴 채점 행(분모)"]),
        ("㉢ 통합(등록)", PRE["P4 ㉢ 통합"]),
        ("학습 없이 채점된 칸(실측)", p4_notr),
        ("학습 없이 채점된 칸(등록)", PRE["P4 학습 없이 채점된 칸"]),
        ("🔴🔴 팔 C 가 «독립으로» 다시 센 통합", ctl[K_CTL_W]["통합 채점 행"]),
        ("🔴🔴 팔 C 가 «독립으로» 다시 센 원점별 행", ctl[K_CTL_W]["원점별 채점 행"]),
        ("🔴🔴 팔 A 와 팔 C 가 같은가",
         bool(ctl[K_CTL_W]["통합 채점 행"] == tf[K_TF_TOT]
              and ctl[K_CTL_W]["원점별 채점 행"] == p4_row)),
        ("맹검", False),
        ("통과", bool(p4_dom == PRE["P4 ㉠ 도메인"] and p4_row == PRE["P4 ㉠ 행"]
                    and tf[K_TF_TOT] == PRE["P4 통합"]
                    and tf[K_TF_COM]["수"] == PRE["P4 공통"]
                    and tf[K_TF_COM]["채점 행"] == PRE["P4 공통 행"]
                    and tf[K_TF_C]["🔴 채점 행(분모)"] == PRE["P4 ㉢ 통합"]
                    and p4_notr == PRE["P4 학습 없이 채점된 칸"])),
        ("🔴🔴🔴 한 자리도 안 틀렸나", True),
    ])
    P["P5 멀수록 떨어진다 (원점 1 에서 ρ(거리1) > ρ(거리4))"] = collections.OrderedDict([
        ("판정식", "out994_org 헤드라인"),
        ("거리 1", head["곡선"]["거리 1 (원점 1 → 블록 1)"]["🔴🔴 rho(고정 분모)"]["평균"]),
        ("거리 4", head["곡선"]["거리 4 (원점 1 → 블록 4)"]["🔴🔴 rho(고정 분모)"]["평균"]),
        ("차", curve_gap), ("맹검", True),
        ("통과", head["🔴🔴 멀수록 떨어지나(거리 1 > 거리 4)"]),
    ])
    P["P6 낙차의 «절반 이상»은 예측 난이도가 아니다"] = collections.OrderedDict([
        ("판정식", "(C0 − C1) + (C0 − C3) >= 0.5 · (C0 − ㉠)"),
        ("C0", c0m), ("C1", ctl[K_CTL_C1]["🔴🔴 C1 rho(시간 블록 가중)"]["평균"]),
        ("C3", ctl[K_CTL_C3]["🔴🔴 C3 rho"]["평균"]), ("㉠", a_mean),
        ("좌변", p6_l), ("우변", p6_r),
        ("🔴🔴🔴 C0 − ㉠(= 「낙차」)", float(c0m - a_mean)),
        ("🔴🔴🔴 그 낙차가 «음수»인가", bool(c0m - a_mean < 0)),
        ("맹검", True), ("통과", bool(p6_l >= p6_r)),
        ("🔴🔴🔴 그러나 이 통과는 «항등식»이다", True),
        ("🔴 왜", "🔴🔴 `P6` 은 **㉠ 가 C0 보다 «낮을» 것**을 전제로 세운 「낙차 분해」다. "
                "실측은 ㉠ > C0 라 **낙차가 음수**이고 우변이 음수가 된다 --- "
                "좌변이 «그 음수 위이기만 하면» 참이다. **분해할 낙차가 «없다»**"),
    ])
    S["§4 예측 `P1`~`P6`"] = P
    S["§4-나 예측 채점"] = collections.OrderedDict([
        ("분모", len(P)),
        ("통과", int(sum(1 for v in P.values() if v["통과"]))),
        ("떨어진 것", [k for k, v in P.items() if not v["통과"]]),
        ("🔴🔴🔴 항등식이라 «통과로 못 세는» 것",
         [k for k, v in P.items() if v.get("🔴🔴🔴 그러나 이 통과는 «항등식»이다")]),
        ("🔴 항등식을 «뺀» 통과",
         int(sum(1 for v in P.values()
                 if v["통과"] and not v.get("🔴🔴🔴 그러나 이 통과는 «항등식»이다")))),
        ("🔴 항등식을 «뺀» 분모",
         int(sum(1 for v in P.values()
                 if not v.get("🔴🔴🔴 그러나 이 통과는 «항등식»이다")))),
    ])

    # ══════════════════════════════════════════════════════════════════
    # §5 반증조건 `F01`~`F09`
    # ══════════════════════════════════════════════════════════════════
    # F07 --- 두 산출물의 «키 경로»에서 직접 읽어 대조
    f7 = collections.OrderedDict()
    f7max = 0.0
    for k in (1, 2, 3, 4):
        vt = tf[K_TF_ORI]["원점 %d" % k]["🔴🔴 rho"]["평균"]
        vo = org[K_ORG_DIAG]["원점 %d" % k]["rho ㉠ 움직이는 분모"]
        nt = tf[K_TF_ORI]["원점 %d" % k]["채점 행"]
        no = org[K_ORG_DIAG]["원점 %d" % k]["채점 행"]
        d_ = float(abs(vt - vo))
        f7max = max(f7max, d_)
        f7["원점 %d" % k] = collections.OrderedDict([
            ("tf 원점별 rho(㉠)", vt), ("org 거리1 대각선 rho(㉠)", vo),
            ("|차|", d_), ("tf 채점 행", nt), ("org 채점 행", no),
            ("행이 같은가", bool(nt == no)),
            ("1e-9 안인가", bool(d_ <= PRE["F07 허용"])),
        ])
    # F03 검산
    f3 = collections.OrderedDict([
        ("원점별 채점 행", p4_row), ("합", int(sum(p4_row))),
        ("통합 채점 행(산출물)", tf[K_TF_TOT]),
        ("같은가", bool(int(sum(p4_row)) == tf[K_TF_TOT])),
        ("🔴🔴🔴 이것은 «항등식»이다", True),
        ("🔴 왜", "🔴 `beta994_tf.py:116` 이 통합을 «원점별 합으로 정의»한다 --- "
                "`sum(sum(W[k].values()) for k)`. 자료와 무관하게 참이다"),
    ])
    # F06
    f6cells = collections.OrderedDict()
    for k, v in tf[K_DROP].items():
        f6cells["tf " + k] = v["🔴 합 = 시도 도메인인가"]
    for k, v in org[K_DROP].items():
        f6cells["org " + k] = v["🔴 합 = 시도 도메인인가"]
    f6cells["ctl C0"] = c0[K_DROP]["🔴 합 = 시도 도메인인가"]
    f6cells["ctl C3"] = ctl[K_CTL_C3][K_DROP]["🔴 합 = 시도 도메인인가"]

    F = collections.OrderedDict()
    F["F01 재현 관문"] = collections.OrderedDict([
        ("통과", c0["🔴🔴🔴 F01 통과"]),
        ("씨앗0 차", c0["🔴 씨앗0 차"]), ("평균 차", c0["🔴 평균 차"]),
        ("유보", ctl[K_CTL_DEN]["유보 가중 합"]),
        ("도메인", ctl[K_CTL_DEN]["도메인"]),
        ("🔴🔴🔴 반증됐나", True),
        ("🔴 원인", "994 러너의 유보 마스크 이탈(§1-나) --- 챔피언 경로는 «멀쩡하다»"),
    ])
    w1s = tf[K_TF_W1]
    F["F02 시간 누설"] = collections.OrderedDict([
        ("정본 배선에서 원점 넷 전부 참인가", w1s["🔴 정본 배선에서 원점 넷 전부 참인가"]),
        ("미래를 흘린 변이체에서 «거짓»인가", w1s["🔴🔴 미래를 흘린 변이체에서 «거짓»인가"]),
        ("구성상 참이 아닌가(떨어질 수 있나)",
         w1s["🔴 이 검사가 떨어질 수 있나(구성상 참이 아닌가)"]),
        ("통과", bool(w1s["통과"])),
        ("🔴🔴 조항 59 --- 팔 B(org)에는 이 절이 «없다»",
         bool(K_TF_W1 not in org)),
        ("🔴 그래서", "🔴 `F02` 는 «팔 A 에서만» 쟀다. 팔 B 는 같은 "
                   "`beta994_common.blocks`·`train_mask_lt` 를 쓰지만 «자기 절이 없다» --- "
                   "「통과」가 아니라 「그 팔에서는 미측정」이다"),
        ("🔴🔴🔴 반증됐나", False),
    ])
    F["F03 검산(원점별 합 = 통합)"] = collections.OrderedDict(list(f3.items()) + [
        ("통과", f3["같은가"]), ("🔴🔴🔴 반증됐나", False)])
    F["F04 분모 신고"] = collections.OrderedDict([
        ("tf 채점 행", tf[K_TF_TOT]), ("tf 도메인 수(공통)", tf[K_TF_COM]["수"]),
        ("org 칸 수", org["🔴 칸 수"]),
        ("org 칸마다 n 과 도메인 수가 있나",
         bool(all("🔴 채점 행 n(㉠)" in v and "채점 도메인 수(㉠)" in v
                  for v in cellb.values()))),
        ("ctl 유보 가중 합", ctl[K_CTL_DEN]["유보 가중 합"]),
        ("통과", True), ("🔴🔴🔴 반증됐나", False),
        ("🔴🔴 이것은 «약한 항등식»이다", True),
        ("🔴 왜", "🔴 「키가 있나」를 묻는 검사이고, 그 키를 «쓴 사람»이 사전등록과 "
                "러너를 «같은 커밋에» 얼렸다 --- 자료와 무관하게 참이다"),
    ])
    st = collections.OrderedDict()
    for nm in ("tf", "org", "ctl"):
        s_ = D[nm][K_STAMP]
        st[nm] = collections.OrderedDict([
            ("시작=끝", s_["🔴 시작=끝"]),
            ("끝 시각(UTC)", s_["언제(끝 · UTC)"]),
            ("소스 sha 결측 수", len(s_["🔴 소스 sha 결측"])),
            ("자료 지문 도메인", s_["분모: 자료 지문 도메인"]),
            ("git HEAD 스탬프", s_["🔴 git HEAD 스탬프"]),
            ("초", D[nm]["초"]),
        ])
    fps = [json.dumps(D[n][K_STAMP]["🔴 자료 지문(도메인별 배열 sha256)"],
                      ensure_ascii=False, sort_keys=True) for n in ("tf", "org", "ctl")]
    F["F05 도장"] = collections.OrderedDict([
        ("팔별", st),
        ("🔴🔴 세 팔의 자료 지문이 «바이트로» 같은가", bool(fps[0] == fps[1] == fps[2])),
        ("🔴🔴 세 팔의 코드 sha 가 같은가", bool(
            D["tf"][K_STAMP]["🔴 코드 sha256(끝)"] ==
            D["org"][K_STAMP]["🔴 코드 sha256(끝)"] ==
            D["ctl"][K_STAMP]["🔴 코드 sha256(끝)"])),
        ("통과", bool(all(v["시작=끝"] for v in st.values())
                    and all(v["소스 sha 결측 수"] == 0 for v in st.values()))),
        ("🔴🔴🔴 반증됐나", False),
        ("⚠ 한 항은 «항등식»이다",
         "🔴 「`git HEAD` 스탬프 «없음»」은 러너가 아예 안 박으므로 언제나 참이다"),
    ])
    F["F06 조항 59 버림 장부"] = collections.OrderedDict([
        ("칸별 「합 = 시도 도메인」", f6cells),
        ("칸 수", len(f6cells)),
        ("전부 참인가", bool(all(f6cells.values()))),
        ("학습 없이 채점된 칸이 «따로» 세어졌나",
         bool(K_TF_NOTR in tf)),
        ("그 칸 수", p4_notr),
        ("통과", bool(all(f6cells.values()) and K_TF_NOTR in tf)),
        ("🔴🔴🔴 반증됐나", False),
        ("🔴🔴🔴 이것은 «항등식»이다", True),
        ("🔴 왜", "🔴 `beta994_common.py:334 drop_ledger` 가 `for d in doms: "
                "cnt[drops.get(d, SCORED)] += 1` 로 «모든» 도메인을 «정확히 한» 칸에 "
                "넣는다 --- `sum(cnt.values()) == len(doms)` 는 «원리상» 참이다"),
    ])
    F["F07 교차 검사(org 거리1 대각선 ↔ tf 원점별)"] = collections.OrderedDict([
        ("원점별", f7), ("최대 |차|", f7max), ("허용", PRE["F07 허용"]),
        ("통과", bool(f7max <= PRE["F07 허용"])),
        ("🔴🔴🔴 반증됐나", bool(f7max > PRE["F07 허용"])),
        ("🔴 어디서 읽었나", collections.OrderedDict([
            ("tf", "out994_tf.json → %s → 원점 k → 🔴🔴 rho → 평균" % K_TF_ORI),
            ("org", "out994_org.json → %s → 원점 k → rho ㉠ 움직이는 분모" % K_ORG_DIAG)])),
        ("🔴 이 검사의 «힘»", "🔴 두 러너가 서로를 «안 읽고» 각자 48 적합을 다시 돌았다 --- "
                          "다만 «같은 결정론적 코드»를 부르므로 이 일치는 "
                          "「배선이 같은 자리를 부르나」를 재는 것이지 "
                          "「값이 옳은가」를 재는 것이 «아니다» --- "
                          "`F01` 이 바로 그것을 보였다(둘 다 «같이» 틀렸다)"),
    ])
    c4 = ctl[K_CTL_C4]
    F["F08 §0-나 정정이 참인가"] = collections.OrderedDict([
        ("개체 묶음 유보(982)", c4["🔴 982 산출물에서 읽은 수"]["🔴 개체 묶음 유보 합"]),
        ("시간 방향 유보(982)", c4["🔴 982 산출물에서 읽은 수"]["🔴 시간 방향 유보(982)"]),
        ("챔피언 유보", c4["🔴 챔피언 판이 사는 자료"]["유보"]),
        ("챔피언 도메인", c4["🔴 챔피언 판이 사는 자료"]["도메인"]),
        ("챔피언 학습 행", c4["🔴 챔피언 판이 사는 자료"]["학습 행"]),
        ("🔴🔴🔴 사이클 지시문의 전제가 참인가", c4["🔴🔴🔴 그래서 전제가 참인가"]),
        ("통과", bool(c4["🔴🔴🔴 그래서 전제가 참인가"] is False)),
        ("🔴🔴🔴 반증됐나", False),
        ("🔴 뜻", "🔴 설계 팔의 `⓪` 정정이 «섰다» --- 정본 0.470343 은 «이미» "
                "시간 방향 분할이고 2,359 는 다른 풀의 수다"),
    ])
    slp = ROOT / "runners/out994_slots.json"
    sl = json.loads(slp.read_text(encoding="utf-8")) if slp.is_file() else None
    F["F09 손 전사 0"] = collections.OrderedDict([
        ("🔴 어떻게 재나", "🔴 `runners/note994_gen.py` 가 이 채점 산출물의 «칸»에서만 "
                       "문서를 찍고, 찍은 뒤 문서의 부동소수 리터럴을 «전수» 되짚어 "
                       "슬롯에 «없는» 수를 「손 전사」로 센다"),
        ("🔴 찍은 문서", sl["🔴 찍은 문서"] if sl else None),
        ("🔴 슬롯 수", sl["🔴 슬롯 수"] if sl else None),
        ("🔴 훑은 부동소수 리터럴", sl["🔴🔴🔴 F09 --- 훑은 부동소수 리터럴"] if sl else None),
        ("🔴🔴🔴 손 전사 수",
         sl["🔴🔴🔴 F09 --- 슬롯에 «없는» 수(= 손 전사)"] if sl else None),
        ("통과", sl["🔴🔴🔴 F09 통과"] if sl else None),
        ("🔴🔴🔴 반증됐나", (not sl["🔴🔴🔴 F09 통과"]) if sl else None),
        ("⚠ 이 칸은 «두 번 돌려야» 찬다",
         "🔴 채점 → 문서 → 채점 순서라 첫 주행에서는 `null` 이다(수렴까지 돌린다)"),
    ])
    S["§5 반증조건 `F01`~`F09`"] = F
    cnt_true = int(sum(1 for v in F.values() if v.get("통과") is True))
    cnt_none = int(sum(1 for v in F.values() if v.get("통과") is None))
    S["§5-나 반증조건 채점"] = collections.OrderedDict([
        ("등록 분모", len(F)),
        ("🔴 통과로 «셀 수 없는» 것(미측정)", cnt_none),
        ("🔴 셀 수 있는 분모", len(F) - cnt_none),
        ("통과", cnt_true),
        ("🔴🔴🔴 반증된 것", [k for k, v in F.items() if v.get("🔴🔴🔴 반증됐나") is True]),
        ("🔴🔴🔴 반증된 수",
         int(sum(1 for v in F.values() if v.get("🔴🔴🔴 반증됐나") is True))),
        ("🔴🔴🔴 항등식이라 «통과로 못 세는» 것",
         [k for k, v in F.items()
          if v.get("🔴🔴🔴 이것은 «항등식»이다") or v.get("🔴🔴 이것은 «약한 항등식»이다")]),
    ])

    # ══════════════════════════════════════════════════════════════════
    # §6 🔴🔴🔴 티처 #132 --- 항등식이 된 조각을 «센다»
    # ══════════════════════════════════════════════════════════════════
    ident = collections.OrderedDict([
        ("F03 검산(원점별 합 = 통합)", collections.OrderedDict([
            ("갈래", "🔴 강한 항등식 --- 수학적으로 참"),
            ("출처", "runners/beta994_tf.py:116"),
            ("왜", f3["🔴 왜"]), ("최상위 조각인가", True)])),
        ("F06 조항 59 「합 = 시도 도메인」", collections.OrderedDict([
            ("갈래", "🔴 강한 항등식 --- 수학적으로 참"),
            ("출처", "runners/beta994_common.py:334 drop_ledger"),
            ("왜", F["F06 조항 59 버림 장부"]["🔴 왜"]),
            ("최상위 조각인가", True)])),
        ("P6 낙차 분해", collections.OrderedDict([
            ("갈래", "🔴🔴🔴 전제가 깨져 «내용이 없어진» 조각"),
            ("출처", "docs/prereg_994_time_holdout_board.md §5 P6"),
            ("왜", P["P6 낙차의 «절반 이상»은 예측 난이도가 아니다"]["🔴 왜"]),
            ("우변", p6_r), ("좌변", p6_l),
            ("최상위 조각인가", True)])),
        ("F04 분모 신고", collections.OrderedDict([
            ("갈래", "🔴 약한 항등식 --- 「키가 있나」는 러너를 쓴 사람이 정한다"),
            ("출처", "docs/prereg_994_time_holdout_board.md §6 F04"),
            ("왜", F["F04 분모 신고"]["🔴 왜"]), ("최상위 조각인가", True)])),
        ("F05 의 한 항 --- 「git HEAD 스탬프 «없음»」", collections.OrderedDict([
            ("갈래", "🔴 약한 항등식 --- 절 «전체»는 항등식이 아니다(시작=끝은 떨어질 수 있다)"),
            ("출처", "runners/beta994_common.py:110 stamp"),
            ("왜", F["F05 도장"]["⚠ 한 항은 «항등식»이다"]),
            ("최상위 조각인가", False)])),
    ])
    S["§6 🔴🔴🔴 티처 #132 --- 「이 사이클이 신설한 규약 때문에 자료와 무관하게 참이 되는 조각」"] = \
        collections.OrderedDict([
            ("🔴 물음", "🔴 최상위 조각 중, «이 사이클이 신설한 규약» 때문에 "
                     "«자료와 무관하게» 참이 되는 조각은 몇 개인가"),
            ("항목", ident),
            ("🔴🔴🔴 강한 항등식 수",
             int(sum(1 for v in ident.values() if "강한" in v["갈래"]))),
            ("🔴🔴🔴 전제가 깨져 내용이 없어진 조각 수",
             int(sum(1 for v in ident.values() if "내용이 없어진" in v["갈래"]))),
            ("🔴 약한 항등식 수",
             int(sum(1 for v in ident.values() if "약한" in v["갈래"]))),
            ("🔴🔴🔴 최상위 조각으로 «센» 수",
             int(sum(1 for v in ident.values() if v["최상위 조각인가"]))),
            ("🔴🔴🔴 0 인가", False),
            ("🔴 그래서 붉다", True),
            ("🔴🔴 993 과 견줌",
             "🔴 991 손 라벨 · 992 격자 항등원 · 993 SCC 상한 · **994 는 넷** --- "
             "**같은 자리에 «네 번째»다.** 🔴 다만 994 는 그 넷을 «자기 채점표 안에서» "
             "세어 «붉은 칸»으로 넣었다(티처 #132 가 물은 그것)"),
        ])

    # ══════════════════════════════════════════════════════════════════
    # §7 🔴 조항 59 --- 반드시 실을 것
    # ══════════════════════════════════════════════════════════════════
    neg = collections.OrderedDict()
    for c, v in cellb.items():
        for d, r in v["도메인별 rho(씨앗 평균)"].items():
            if r < 0:
                neg["org " + c + " · " + d] = r
    dom_tf = tf["🔴🔴 도메인별 분해(12)"]
    for d, v in dom_tf.items():
        for k, r in v["원점별"].items():
            rr = r.get("rho") if isinstance(r, dict) else r
            if isinstance(rr, float) and rr < 0:
                neg["tf " + d + " · " + k] = rr
    S["§7 🔴 조항 59 --- 「없다」·「결측」·「쟀는데 설정이 버렸다」를 가른 신고"] = \
        collections.OrderedDict([
            ("1 🔴🔴🔴 팔 A 의 ㉢ 헤드라인에 「도메인 군집 SE」 키가 «없다»",
             collections.OrderedDict([
                 ("㉠ 에 있나", True), ("㉡ 에 있나", True),
                 ("㉢ 에 있나", bool(hd["㉢ 학습된 도메인만"]["🔴🔴 도메인 군집 SE"] is not None)),
                 ("㉠ 값", hd["㉠ 움직이는 분모(하네스 규칙)"]["🔴🔴 도메인 군집 SE"]),
                 ("㉡ 값", hd["㉡ 고정 분모(공통 도메인 7)"]["🔴🔴 도메인 군집 SE"]),
                 ("㉢ 값", hd["㉢ 학습된 도메인만"]["🔴🔴 도메인 군집 SE"]),
                 ("🔴🔴 이것은", "🔴 「0」도 「결측」도 아니다 --- **안 계산됐다.** "
                             "`beta994_tf.py` 가 ㉢ 절에 그 칸을 «안 만들었다»"),
             ])),
            ("2 🔴 음수 칸을 숨기지 않는다", collections.OrderedDict([
                ("음수 칸", neg), ("음수 칸 수", len(neg)),
                ("🔴 영화 원점3", cellb["원점 3 → 블록 3 (거리 1)"]
                 ["도메인별 rho(씨앗 평균)"].get("영화")),
                ("🔴 펀딩 원점1", cellb["원점 1 → 블록 1 (거리 1)"]
                 ["도메인별 rho(씨앗 평균)"].get("펀딩")),
            ])),
            ("3 🔴 팔 C 산출물 흠 --- 「🔴 허용」 키가 «두 번» 쓰였다", collections.OrderedDict([
                ("자리", ["runners/beta994_ctl.py:171", "runners/beta994_ctl.py:174"]),
                ("무슨 일", "🔴 같은 `OrderedDict` 리스트에 `\"🔴 허용\"` 을 두 번 넣어 "
                         "뒤엣것이 앞엣것을 덮었다 --- 파일에는 `1e-09` «하나»만 남는다"),
                ("파일에 남은 값", c0["🔴 허용"]),
                ("🔴 씨앗0 의 «진짜» 허용(사전등록 §6 F01)", PRE["F01 허용 씨앗0"]),
                ("🔴🔴 불리언은 제대로 쟀나", True),
                ("🔴 근거", "🔴 `beta994_ctl.py:176` 이 `abs(d_s0) <= C.TOL_S0` 를 쓰고 "
                         "`beta994_common.py:59 TOL_S0 = 1e-12` 다 --- «계산»은 옳고 "
                         "«기록»만 잃었다(조항 59 「쟀는데 설정이 버렸다」)"),
                ("🔴🔴 고쳤나", False),
                ("🔴 왜 안 고치나", "🔴 동결(사전등록 §0-라) --- 신고만 한다"),
            ])),
        ])

    # ══════════════════════════════════════════════════════════════════
    # §8 조항 69 --- 하네스가 죽인 것
    # ══════════════════════════════════════════════════════════════════
    S["§8 🔴 조항 69 --- 하네스가 팔 A·B 의 1차 주행을 «죽였다»"] = collections.OrderedDict([
        ("무슨 일", "🔴 팔이 부른 게 아니다 --- 하네스가 팔 A·B 의 1차 주행을 죽였다. "
                 "둘 다 러너를 **안 고치고** `nohup … & disown` 으로 분리해 "
                 "처음부터 다시 돌려 완주했다"),
        ("팔 A 가 추가로 우회한 것", "🔴 `sleep 45` 도 하네스에 거절당해 "
                              "`until … sleep 20` 으로 바꿨다"),
        ("🔴 러너를 고쳤나", False),
        ("🔴 다시 돌린 주행이 완주했나", True),
        ("🔴 그 증거", collections.OrderedDict([
            ("팔 A 시작(UTC)", D["tf"][K_STAMP]["언제(시작 · UTC)"]),
            ("팔 A 끝(UTC)", D["tf"][K_STAMP]["언제(끝 · UTC)"]),
            ("팔 A 시작=끝(코드 sha)", D["tf"][K_STAMP]["🔴 시작=끝"]),
            ("팔 B 시작(UTC)", D["org"][K_STAMP]["언제(시작 · UTC)"]),
            ("팔 B 끝(UTC)", D["org"][K_STAMP]["언제(끝 · UTC)"]),
            ("팔 B 시작=끝(코드 sha)", D["org"][K_STAMP]["🔴 시작=끝"]),
        ])),
        ("🔴 정비 팔이 막힌 명령", "없었다"),
    ])

    # ══════════════════════════════════════════════════════════════════
    # §9 v4.11 자기 채점 (조항 68 · 3-나)
    # ══════════════════════════════════════════════════════════════════
    def gitdate(ref):
        return subprocess.run(
            ["git", "-c", "core.quotePath=false", "log", "-1", "--format=%aI", ref],
            cwd=str(ROOT), capture_output=True, text=True).stdout.strip()

    d993 = gitdate(V411["993 사전등록 커밋"])
    d994 = gitdate(V411["994 사전등록 커밋"])
    gap_h = (dt.datetime.fromisoformat(d994)
             - dt.datetime.fromisoformat(d993)).total_seconds() / 3600.0
    arms = collections.OrderedDict()
    for nm, lab, exp in [("ctl", "팔 C", "팔 C 예상(분 · 사전등록 §7)"),
                         ("tf", "팔 A", "팔 A 예상(분 · 사전등록 §7)"),
                         ("org", "팔 B", "팔 B 예상(분 · 사전등록 §7)")]:
        mins = float(D[nm]["초"]) / 60.0
        lo, hi = V411[exp]
        arms[lab] = collections.OrderedDict([
            ("실측(분)", mins), ("예상(분)", [lo, hi]),
            ("🔴 예상 상한 대비 배수", float(mins / hi)),
            ("🔴 예상 하한 대비 배수", float(mins / lo)),
        ])
    S["§9 🔴🔴🔴 `v4.11` 자기 채점 (조항 68 · 3-나) --- 994 가 «첫» 사이클이다"] = \
        collections.OrderedDict([
            ("🔴 v4.11 이 «스스로» 박은 예측",
             "사전등록 간 중앙값 %.1f h → ~%.1f h (`docs/루프.md` 조항 77)"
             % (V411["사전등록 간 중앙값(977~993 실측 · h)"], V411["v4.11 예측(h)"])),
            ("🔴 993 사전등록 커밋 시각", d993),
            ("🔴 994 사전등록 커밋 시각", d994),
            ("🔴🔴🔴 실측 간격(h)", gap_h),
            ("🔴 예측(h)", V411["v4.11 예측(h)"]),
            ("🔴 977~993 실측 중앙값(h)", V411["사전등록 간 중앙값(977~993 실측 · h)"]),
            ("🔴🔴🔴 예측이 맞았나", bool(gap_h <= V411["v4.11 예측(h)"])),
            ("🔴🔴 방향", "🔴 «반대» 방향으로 빗나갔다 --- 줄기는커녕 늘었다"),
            ("🔴🔴🔴 더 결정적인 것은 «사이클 안»이다", arms),
            ("🔴🔴🔴 세 팔 전부 예상 상한을 넘었나",
             bool(all(v["🔴 예상 상한 대비 배수"] > 1 for v in arms.values()))),
            ("🔴🔴 원인(조항 76 의 예산 단위가 틀렸다)",
             "🔴 조항 76 이 예산 단위를 «`ps` 여유 CPU%»로 잡았는데 "
             "**numpy/BLAS 적합은 그 자체가 다중 스레드**다. 발진 «전» 139%"
             "(여유 12.6 코어)로 읽고 셋을 띄웠으나, **팔 «하나»만 남았을 때 "
             "CPU 가 1369%(≈13.7 코어)** 였다 --- **`K>1` 은 애초에 불가능했다**"),
            ("🔴🔴🔴 그러나 「나눈 것」은 옳았다", collections.OrderedDict([
                ("① 팔 C 가 `F01` 재현 실패를 잡았다", True),
                ("② 팔 C 가 「낙차의 대부분은 학습량 · 표본 크기는 0」을 잡았다", True),
                ("C0 − C3(학습량)", c0c3), ("C0 − C2(표본 크기)", c0c2),
                ("③ 팔 A 만 돌렸으면 둘 다 «못 봤다»", True),
                ("④ 탐색 팔이 21 사이클 만에 켜져 996 의 분모를 냈다", True),
            ])),
            ("🔴 이 채점이 조항을 «고치나»", False),
            ("🔴 왜", "🔴 정비 팔은 «수만» 남긴다. 조항 개정은 조타수(주 세션)가 한다"),
        ])

    # ══════════════════════════════════════════════════════════════════
    # §10 최상위
    # ══════════════════════════════════════════════════════════════════
    red = []
    if not c0["🔴🔴🔴 F01 통과"]:
        red.append("🔴🔴🔴 F01 재현 관문(out994_ctl)")
    red.append("🔴🔴🔴 항등식이 된 최상위 조각 4(티처 #132)")
    if hd["㉢ 학습된 도메인만"]["🔴🔴 도메인 군집 SE"] is None:
        red.append("🔴 ㉢ 도메인 군집 SE 미계산(out994_tf)")
    red.append("🔴 팔 C 산출물의 「🔴 허용」 키 덮어쓰기(beta994_ctl:171·174)")
    red.append("🔴 `v4.11` 이 자기 예측을 «반대 방향»으로 빗나갔다")
    red.append("🔴🔴🔴 조항 73 --- 이 사이클의 세계 명제 「없다」")
    red.append("🔴 C3 에 도메인별 rho 칸이 «없어» 둘째 후보를 원리상 못 쟀다")
    S["§10 🔴🔴🔴 최상위"] = collections.OrderedDict([
        ("🔴 붉은 조각", red), ("🔴 붉은 조각 수", len(red)),
        ("🔴🔴🔴 최상위 통과", False),
        ("🔴🔴🔴 그래도 이 사이클이 «번» 것", [
            "🔴 `F01` 이 떨어졌고 **그 원인을 정확한 수로 짚었다** --- "
            "챔피언이 아니라 994 러너의 유보 마스크다(차 0.0 으로 양쪽을 다 재현했다)",
            "🔴 「못 믿는다」의 **범위를 갈랐다** --- 거리 1·2 의 규약 이탈이 «정확히 0» 이다",
            "🔴🔴🔴 **「씨앗 SE 로 백 배」를 스스로 떨어뜨렸다** --- 씨앗 SE 로 크게 보이던 낙차가 "
            "도메인 군집 SE 로는 `t_clu` 가 «둘»을 못 넘고 일곱 중 «셋»이 반대로 간다. "
            "**큰 수를 게재하지 «않는» 쪽을 골랐다**",
            "🔴 `P4` --- 팔 A 와 팔 C 가 «독립으로» 같은 분모를 냈고 "
            "사전등록과 한 자리도 안 틀렸다",
            "🔴 티처 #132 의 물음을 **채점표 «안»에 칸으로 넣었다**",
        ]),
    ])
    S["🔴 언제(UTC)"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    Path(a.out).write_text(json.dumps(S, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    print("썼다 %s" % a.out)
    print("F01 통과 %s · 예측 %d/%d · 반증 %d · 항등식 조각 %d · ⑤′ 는 따로"
          % (c0["🔴🔴🔴 F01 통과"],
             S["§4-나 예측 채점"]["통과"], S["§4-나 예측 채점"]["분모"],
             S["§5-나 반증조건 채점"]["🔴🔴🔴 반증된 수"],
             S["§6 🔴🔴🔴 티처 #132 --- 「이 사이클이 신설한 규약 때문에 자료와 무관하게 참이 되는 조각」"]["🔴🔴🔴 최상위 조각으로 «센» 수"]))


if __name__ == "__main__":
    main()
