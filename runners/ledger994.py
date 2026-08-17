# -*- coding: utf-8 -*-
"""🔴 노트 994 원장 항목 --- `⑦`. **손으로 안 적는다.**

🔴 `runners/out994_score.json` 과 `runners/fiveprime_994.json` 의 «칸»에서만 짓는다.
🔴 **추가만 한다** --- 옛 항목을 고치지 않는다(규칙 A).
🔴 원장 «정본»은 «가지»의 것이다 --- `git show <ref>:data/lab/denominator.json`.

씀:  python3 runners/ledger994.py --ref <가지 sha>
"""
import argparse
import collections
import datetime as dt
import json
import subprocess
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
DEN = ROOT / "data/lab/denominator.json"
S = json.loads((ROOT / "runners/out994_score.json").read_text(encoding="utf-8"))
FP = ROOT / "runners/fiveprime_994.json"
SL = ROOT / "runners/out994_slots.json"

K1 = "§1 🔴🔴🔴 맨 위 --- `F01` 재현 관문이 «떨어졌다»"
K1B = "§1-나 🔴🔴🔴 원인을 «찾았다» --- 챔피언이 아니라 «994 러너의 유보 마스크»다"
K1C = "§1-다 🔴🔴🔴 「못 믿는다」의 «범위» --- 절대 수준만 물들고 «상대»는 안 물든다"
K2 = "§2 🔴🔴 판 ρ --- 헤드라인 셋을 «분모와 함께»"
K3 = "§3 🔴🔴🔴 세계 명제 후보 --- 「예측 지평이 멀수록 성능이 떨어진다」"
K3G = "🔴🔴🔴 도메인 «군집» SE 로도 서나 --- 도메인 «짝» 차 Δ_d = ρ_d(거리1) − ρ_d(거리4)"
K3C = "§3-다 🔴🔴🔴 조항 73 --- 이 사이클의 «세계 명제»"
K4B = "§4-나 예측 채점"
K5B = "§5-나 반증조건 채점"
K6 = "§6 🔴🔴🔴 티처 #132 --- 「이 사이클이 신설한 규약 때문에 자료와 무관하게 참이 되는 조각」"
K7 = "§7 🔴 조항 59 --- 「없다」·「결측」·「쟀는데 설정이 버렸다」를 가른 신고"
K8 = "§8 🔴 조항 69 --- 하네스가 팔 A·B 의 1차 주행을 «죽였다»"
K9 = "§9 🔴🔴🔴 `v4.11` 자기 채점 (조항 68 · 3-나) --- 994 가 «첫» 사이클이다"
K10 = "§10 🔴🔴🔴 최상위"


def V(*p):
    o = S
    for k in p:
        o = o[k]
    return o


def git(*a):
    return subprocess.run(["git", "-c", "core.quotePath=false"] + list(a),
                          cwd=str(ROOT), capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="🔴 가지 sha --- 원장 정본이 사는 곳")
    ap.add_argument("--pr", default=None, help="🔴 PR 번호(생성 «뒤»에만 준다)")
    a = ap.parse_args()

    r = git("show", "%s:data/lab/denominator.json" % a.ref)
    assert r.returncode == 0, "🔴 가지 원장을 못 읽었다: %s" % r.stderr[:300]
    den = json.loads(r.stdout, object_pairs_hook=collections.OrderedDict)
    n_before = len(den)

    fp = json.loads(FP.read_text(encoding="utf-8")) if FP.is_file() else None
    sl = json.loads(SL.read_text(encoding="utf-8")) if SL.is_file() else None

    fpsec = collections.OrderedDict([
        ("🔴 돌렸나", bool(fp is not None)),
        ("🔴 절 수(분모)", fp["🔴 절 수(분모)"] if fp else None),
        ("🔴🔴🔴 실패한 절 수", fp["🔴🔴🔴 실패한 절 수"] if fp else None),
        ("🔴🔴🔴 통과한 절 수", fp["🔴🔴🔴 통과한 절 수"] if fp else None),
        ("🔴 실패한 절", fp["🔴 실패한 절"] if fp else None),
        ("통과", fp["통과"] if fp else None),
    ])

    e1 = collections.OrderedDict([
        ("언제", dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("🔴 축", V("🔴 축")),
        ("🔴 가지", "note/994-time-holdout-board"),
        ("🔴 사전등록", V("🔴 사전등록")),
        ("🔴 ref(정비 팔이 읽은 가지 sha)", a.ref),

        ("🔴🔴🔴 맨 위 --- `F01` 이 떨어졌고 원인은 «챔피언이 아니다»",
         collections.OrderedDict([
             ("F01 통과", V(K1, "🔴🔴🔴 F01 통과")),
             ("C0 씨앗0 차", V(K1, "🔴 씨앗0 차")),
             ("C0 평균 차", V(K1, "🔴 평균 차")),
             ("🔴 하네스 정본 마스크로 오늘 다시 잰 씨앗0",
              V(K1B, "🔴🔴🔴 ㉮ 하네스 정본 마스크로 오늘 다시 잰 씨앗0")),
             ("🔴 그 차", V(K1B, "🔴🔴🔴 차")),
             ("🔴🔴🔴 정본 챔피언 경로가 오늘 재현되나",
              V(K1B, "🔴🔴🔴 정본 챔피언 경로가 «오늘» 재현되나")),
             ("🔴 두 규약의 차", V(K1B, "🔴🔴 두 규약의 차(㉯ − ㉮)")),
             ("🔴 rho 가 갈린 도메인", V(K1B, "🔴🔴 rho 가 갈린 도메인")),
             ("🔴 predict 배치 행(하네스 / 994)",
              [V(K1B, "🔴🔴 predict «배치» 행 합(㉮ 하네스)"),
               V(K1B, "🔴🔴 predict «배치» 행 합(㉯ 994)")]),
             ("🔴 채점 행은 같다", V(K1B, "🔴🔴 채점되는 행은 둘이 «같다»")),
             ("🔴 원인 자리", "runners/beta994_common.py:190 canon_masks · :158 blocks "
                          "(유보 마스크에 isfinite(y) 를 더했다) · "
                          "lab/harness.py:320 은 안 더한다 · "
                          "lab/forms.py:1140 BagBoost.predict 가 배치 안에서 순위를 매긴다"),
             ("🔴 고쳤나(동결)", False),
         ])),

        ("🔴🔴 「못 믿는다」의 범위", collections.OrderedDict([
            ("거리별 규약 이탈", V(K1C, "🔴🔴🔴 거리별 규약 이탈(㉯ − ㉮)")),
            ("거리 1·2 의 이탈이 정확히 0 인가",
             V(K1C, "🔴🔴 거리 1·2 의 이탈이 «정확히 0» 인가")),
            ("규약이 낙차를 바꾸는 양", V(K1C, "🔴🔴🔴 규약이 낙차를 얼마나 바꾸나")),
            ("그 몫", V(K1C, "🔴🔴 그 몫(|바뀌는 양| / 낙차)")),
            ("🔴 못 믿는 수 둘",
             [k for k, v in V(K1C, "🔴🔴🔴 어느 수가 이탈보다 «큰가»(안전 배수)").items()
              if v.get("🔴 믿을 수 있나", v.get("🔴🔴🔴 믿을 수 있나")) is False]),
        ])),

        ("🔴🔴 판 ρ (분모와 함께 · 🔴 정본은 «안» 갱신했다)", collections.OrderedDict([
            (k, collections.OrderedDict([
                ("rho", v["rho 평균"]), ("씨앗 SE", v["씨앗 SE"]),
                ("도메인 군집 SE", v["🔴🔴 도메인 군집 SE"]),
                ("채점 행", v["🔴 채점 행(분모)"])]))
            for k, v in V(K2, "헤드라인").items()])),
        ("🔴 정본 판 rho(안 고쳤다)", V(K2, "🔴 정본 판 rho")),
        ("🔴 정본을 갱신했나", V(K2, "🔴🔴🔴 정본을 갱신하나")),

        ("🔴🔴🔴 세계 명제", collections.OrderedDict([
            ("이 사이클의 세계 명제", V(K3C, "🔴🔴🔴 세계 명제")),
            ("후보 수", V(K3C, "🔴 후보 수")),
            ("거리 1 − 거리 4", V(K3, "🔴🔴 거리 1 − 거리 4")),
            ("단조 감소인가", V(K3, "🔴 단조 감소인가")),
            ("씨앗 SE 로 몇 배",
             V(K3, "🔴🔴🔴 씨앗 SE 로 재면 몇 배인가(= 이 사이클이 «처음에» 본 수)")),
            ("🔴🔴 도메인 군집 SE t_clu(거리1 가중 / 거리4 가중 / 균등)",
             [V(K3, K3G, "🔴 거리 1 가중으로", "t_clu"),
              V(K3, K3G, "🔴 거리 4 가중으로(«보수적» --- 분모가 작다)", "t_clu"),
              V(K3, K3G, "🔴 균등 가중으로(993 이 「차」에 쓴 꼴)", "t_clu")]),
            ("🔴🔴🔴 하나라도 2·SE 를 넘나", V(K3, K3G, "🔴🔴🔴 하나라도 넘나")),
            ("🔴🔴🔴 부호가 뒤집힌 도메인", V(K3, K3G, "🔴🔴🔴 부호가 «뒤집힌» 도메인")),
            ("부호가 같은 도메인 수 / 도메인 수",
             [V(K3, K3G, "🔴🔴 부호가 «같은» 도메인 수(Δ_d > 0)"),
              V(K3, K3G, "🔴 도메인 수")]),
            ("🔴 둘째 후보를 못 잰 까닭", "out994_ctl.json 의 C3 절에 「도메인별 rho」 칸이 «없다»"),
        ])),

        ("🔴 채점", collections.OrderedDict([
            ("예측 통과 / 분모", [V(K4B, "통과"), V(K4B, "분모")]),
            ("🔴 항등식을 뺀 통과 / 분모",
             [V(K4B, "🔴 항등식을 «뺀» 통과"), V(K4B, "🔴 항등식을 «뺀» 분모")]),
            ("반증조건 통과 / 셀 수 있는 분모",
             [V(K5B, "통과"), V(K5B, "🔴 셀 수 있는 분모")]),
            ("반증된 것", V(K5B, "🔴🔴🔴 반증된 것")),
            ("항등식이라 통과로 못 세는 반증조건",
             V(K5B, "🔴🔴🔴 항등식이라 «통과로 못 세는» 것")),
        ])),

        ("🔴🔴🔴 티처 #132 --- 항등식이 된 최상위 조각", collections.OrderedDict([
            ("최상위 조각으로 «센» 수", V(K6, "🔴🔴🔴 최상위 조각으로 «센» 수")),
            ("강한 항등식", V(K6, "🔴🔴🔴 강한 항등식 수")),
            ("전제가 깨져 내용이 없어진 조각", V(K6, "🔴🔴🔴 전제가 깨져 내용이 없어진 조각 수")),
            ("약한 항등식", V(K6, "🔴 약한 항등식 수")),
            ("이름", list(V(K6, "항목"))),
            ("0 인가", V(K6, "🔴🔴🔴 0 인가")),
        ])),

        ("🔴 조항 59 신고 셋", collections.OrderedDict([
            ("① ㉢ 에 도메인 군집 SE 키가 있나",
             V(K7, "1 🔴🔴🔴 팔 A 의 ㉢ 헤드라인에 「도메인 군집 SE」 키가 «없다»", "㉢ 에 있나")),
            ("② 음수 칸 수", V(K7, "2 🔴 음수 칸을 숨기지 않는다", "음수 칸 수")),
            ("② 영화 원점3", V(K7, "2 🔴 음수 칸을 숨기지 않는다", "🔴 영화 원점3")),
            ("② 펀딩 원점1", V(K7, "2 🔴 음수 칸을 숨기지 않는다", "🔴 펀딩 원점1")),
            ("③ 팔 C 「🔴 허용」 키 덮어쓰기 자리",
             V(K7, "3 🔴 팔 C 산출물 흠 --- 「🔴 허용」 키가 «두 번» 쓰였다", "자리")),
            ("③ 파일에 남은 값",
             V(K7, "3 🔴 팔 C 산출물 흠 --- 「🔴 허용」 키가 «두 번» 쓰였다", "파일에 남은 값")),
            ("③ 불리언은 제대로 쟀나",
             V(K7, "3 🔴 팔 C 산출물 흠 --- 「🔴 허용」 키가 «두 번» 쓰였다",
               "🔴🔴 불리언은 제대로 쟀나")),
            ("③ 고쳤나", V(K7, "3 🔴 팔 C 산출물 흠 --- 「🔴 허용」 키가 «두 번» 쓰였다",
                        "🔴🔴 고쳤나")),
        ])),

        ("🔴 조항 69 --- 하네스가 팔 A·B 의 1차 주행을 죽였다", collections.OrderedDict([
            ("무슨 일", V(K8, "무슨 일")),
            ("팔 A 가 추가로 우회한 것", V(K8, "팔 A 가 추가로 우회한 것")),
            ("러너를 고쳤나", V(K8, "🔴 러너를 고쳤나")),
            ("다시 돌린 주행이 완주했나", V(K8, "🔴 다시 돌린 주행이 완주했나")),
            ("정비 팔이 막힌 명령", V(K8, "🔴 정비 팔이 막힌 명령")),
        ])),

        ("🔴 규칙 D --- 문서를 손으로 안 썼다", collections.OrderedDict([
            ("슬롯 수", sl["🔴 슬롯 수"] if sl else None),
            ("훑은 부동소수 리터럴",
             sl["🔴🔴🔴 F09 --- 훑은 부동소수 리터럴"] if sl else None),
            ("🔴 손 전사", sl["🔴🔴🔴 F09 --- 슬롯에 «없는» 수(= 손 전사)"] if sl else None),
            ("문서에서 못 앉힌 슬롯",
             sl["🔴 문서에서 못 찾은 슬롯 수(조항 59 --- 「0」이 아니라 「못 앉혔다」)"]
             if sl else None),
        ])),

        ("🔴 `⑤′`", fpsec),

        ("🔴🔴🔴 R5 원장 키 수", collections.OrderedDict([
            ("🔴 원장 키 수(이 항목을 쓰기 «전» · 가지)", n_before),
            ("🔴 그중 «중복 아닌» 키 수(전)", len(set(den))),
            ("🔴 중복 키 수(전)", n_before - len(set(den))),
        ])),
        ("🔴 PR", ("#%s" % a.pr) if a.pr else "🔴 아직 안 만들었다(「없다」가 아니다 · 조항 59)"),
        ("🔴 가지 끝 sha(이 항목을 쓸 때)", a.ref),
        ("🔴 최상위 통과", V(K10, "🔴🔴🔴 최상위 통과")),
        ("🔴 붉은 조각", V(K10, "🔴 붉은 조각")),
        ("🔴 붉은 조각 수", V(K10, "🔴 붉은 조각 수")),
    ])

    arms = V(K9, "🔴🔴🔴 더 결정적인 것은 «사이클 안»이다")
    e2 = collections.OrderedDict([
        ("언제", e1["언제"]),
        ("🔴 무엇", "🔴🔴🔴 `v4.11`(조항 74~77)이 «스스로» 박은 예측을 «첫» 사이클에서 쟀다. "
                "🔴 **조항 개정은 조타수가 한다 --- 정비 팔은 «수만» 남긴다**"),
        ("🔴 v4.11 이 박은 예측", V(K9, "🔴 v4.11 이 «스스로» 박은 예측")),
        ("993 사전등록 커밋 시각", V(K9, "🔴 993 사전등록 커밋 시각")),
        ("994 사전등록 커밋 시각", V(K9, "🔴 994 사전등록 커밋 시각")),
        ("🔴🔴🔴 실측 간격(h)", V(K9, "🔴🔴🔴 실측 간격(h)")),
        ("🔴 예측(h)", V(K9, "🔴 예측(h)")),
        ("🔴 977~993 실측 중앙값(h)", V(K9, "🔴 977~993 실측 중앙값(h)")),
        ("🔴🔴🔴 예측이 맞았나", V(K9, "🔴🔴🔴 예측이 맞았나")),
        ("🔴🔴 방향", V(K9, "🔴🔴 방향")),
        ("🔴🔴🔴 팔별 실측(분) 대 사전등록 예상(분)", collections.OrderedDict([
            (k, collections.OrderedDict([
                ("실측(분)", v["실측(분)"]), ("예상(분)", v["예상(분)"]),
                ("상한 대비 배수", v["🔴 예상 상한 대비 배수"])]))
            for k, v in arms.items()])),
        ("🔴 세 팔 전부 예상 상한을 넘었나", V(K9, "🔴🔴🔴 세 팔 전부 예상 상한을 넘었나")),
        ("🔴🔴 원인", V(K9, "🔴🔴 원인(조항 76 의 예산 단위가 틀렸다)")),
        ("🔴🔴🔴 그러나 「나눈 것」은 옳았다",
         V(K9, "🔴🔴🔴 그러나 「나눈 것」은 옳았다")),
        ("🔴 이 채점이 조항을 고치나", V(K9, "🔴 이 채점이 조항을 «고치나»")),
        ("통과", V(K9, "🔴🔴🔴 예측이 맞았나")),
    ])

    n1 = "노트 994"
    n2 = "🔴🔴🔴 v4.11 자기 채점 (조항 68) — 994 가 «첫» 사이클이다 · 예측이 «반대 방향»으로 빗나갔다"
    den[n1] = e1
    den[n2] = e2
    e1["🔴🔴🔴 R5 원장 키 수"]["🔴🔴🔴 원장 키 수(이 항목을 «쓴 뒤»)"] = len(den)
    e1["🔴🔴🔴 R5 원장 키 수"]["🔴 중복 키 수(후)"] = len(den) - len(set(den))
    DEN.write_text(json.dumps(den, ensure_ascii=False, indent=1), encoding="utf-8")
    print("원장 %d → %d · 중복 %d · 새 키 %s"
          % (n_before, len(den), len(den) - len(set(den)), [n1, n2]))


if __name__ == "__main__":
    main()
