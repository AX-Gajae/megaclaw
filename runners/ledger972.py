# -*- coding: utf-8 -*-
"""노트 972 — 🔴 **원장 러너**. 사전등록 채점표 · 3순위 수 정정 · 반증조건 자기판정.

🔴 **손 전사 금지(규칙 D)**: 판정문·카드·논문에 쓸 수 있는 수는 **오직 이 산출물의
`🔴 치환표` 에 있는 것**뿐이다. 치환표에 없는 수를 적으면 F4 다.

사전등록: `docs/prereg_972_c1null.md` (측정 전 단독 커밋 `8675748ed`).
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
os.chdir(str(ROOT))

import predict972 as PZ                                           # noqa: E402

OUT971 = ["runners/out971_wiring.json", "runners/out971_predict.json",
          "runners/out971_board.json", "runners/out971_meta.json",
          "runners/out971_meta_exact.json", "runners/out971_tautprobe.json",
          "runners/out971_w6.json", "runners/out971_design_census.json"]


def _load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def _dig(o, *names):
    """중첩 딕트에서 **이름 조각을 포함하는** 첫 키를 따라 내려간다."""
    cur = o
    for nm in names:
        if not isinstance(cur, dict):
            return None
        hit = None
        for k in cur:
            if nm in str(k):
                hit = k
                break
        if hit is None:
            return None
        cur = cur[hit]
    return cur


# ══════════════════════════════════════════════════════════════════════
def census971() -> dict:
    """🔴 **조항 66-② 를 실제로 신고한다** --- 971 은 세지도 신고하지도 않았다."""
    rows, summaries, no_z = {}, {}, []
    for p in OUT971:
        if not (ROOT / p).is_file():
            rows[p] = {"🔴": "없다"}
            continue
        o = _load(p)
        has_z = any("§Z" in str(k) for k in o)
        # 「요약」 꼴 --- 그 산출물이 자기 계수를 어떤 키로 내나
        forms = sorted({str(k) for k in _walk_keys(o)
                        if "분자/분모" in str(k) or "분자 / 분모" in str(k)})
        rows[p] = {"§Z 있나": has_z, "요약 키 꼴": forms,
                   "sha256": PZ.P._sha_file(ROOT / p)}
        for f in forms:
            summaries[f] = summaries.get(f, 0) + 1
        if not has_z:
            no_z.append(p)
    return {
        "🔴 분모: 971 산출물": len(OUT971),
        "산출물별": rows,
        "🔴🔴 요약 키 꼴(종수)": {"종수": len(summaries), "꼴별 자리 수": summaries},
        "🔴🔴 §Z 없는 산출물": {"목록": no_z,
                       "🔴 분자/분모": "%d / %d" % (len(no_z), len(OUT971))},
        "🔴 조항 66-② 신고": ("한 사이클 한 요약이 원칙인데 971 의 실측 요약 키 꼴은 위 종수다. "
                      "🔴 **971 은 이것을 세지도 신고하지도 않았다** --- 972 가 신고한다"),
    }


def _walk_keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            for x in _walk_keys(v):
                yield x
    elif isinstance(o, list):
        for v in o:
            for x in _walk_keys(v):
                yield x


def score(NUL, WIR, RST, META) -> dict:
    """🔴 사전등록 §4 P1~P14 채점표 --- **기계가 만든다**."""
    S = {}

    def P(i, pred, ok, obs):
        S["P%d" % i] = {"예측": pred, "🔴 판정": ("✅ 맞다" if ok else "✗ 반증됐다"),
                        "🔴 실측": obs}

    mf = META["file"]["predict971"]
    mfun = META["func"]["predict971"]
    base = META["file"]["recommit970"]
    P(1, "낙하 ≠ 4", mf["🔴 증명된 낙하"] != 4,
      "%d / %d (%.1f%%)" % (mf["🔴 증명된 낙하"], mf["🔴 분모"], mf["🔴 증명된 낙하 %"]))
    P(2, "밑값(recommit970)보다 나쁘거나 같다",
      mf["🔴 증명된 낙하 %"] <= base["🔴 증명된 낙하 %"],
      "predict971 %.1f%% vs recommit970 %.1f%%" % (mf["🔴 증명된 낙하 %"],
                                                   base["🔴 증명된 낙하 %"]))
    P(3, "티처 #110 의 2(15.4%) 를 재현", mf["🔴 증명된 낙하"] == 2,
      "%d (%.1f%%)" % (mf["🔴 증명된 낙하"], mf["🔴 증명된 낙하 %"]))

    rs = RST["🔴🔴🔴 §R 요약"]
    f_all = rs["🔴🔴 file 범위 뒤집힌 판 합(주석만 제외)"]
    u_all = rs["🔴🔴 func 범위 뒤집힌 판 합(주석만 제외)"]
    P(4, "file 범위에서 하나 이상 뒤집힌다", f_all > 0,
      "뒤집힌 판 %d --- 갈래별 %s · %s · **음성 대조(주석만) %s**"
      % (f_all, "작은 " + rs["file · 작은"], "큰 " + rs["file · 큰"], rs["file · 주석만"]))
    P(5, "func 범위에서 하나도 안 뒤집힌다", u_all == 0,
      "뒤집힌 판 %d --- 갈래별 %s · %s · %s"
      % (u_all, "작은 " + rs["func · 작은"], "큰 " + rs["func · 큰"], rs["func · 주석만"]))

    N = NUL["🔴🔴🔴 §N 유보 예측 --- 진짜 귀무"]
    perm = _dig(N, "§3-가 정본 자")
    pv = perm["🔴🔴🔴 순열 p(단측 · 사전등록 §3-가 정본 자)"]
    ps = perm["🔴🔴🔴 부호 일관성 p(사전등록 §3-나)"]
    P(6, "유보 순열 p 는 0.05 를 못 넘는다(채택 실패)", pv > 0.05, "p = %.6f" % pv)
    P(7, "부호 일관성 p 는 0.05 를 넘는다(채택)", ps <= 0.05, "p = %.6f" % ps)

    b3 = _dig(N, "§3-다 폭 셋")
    dbl = _dig(b3, "이중")["🔴 짝 SD"]
    P(8, "이중 붓스트랩 SD > 0.030", dbl > 0.030, "SD = %.6f (971 유보-only 0.021669)" % dbl)

    lo = _dig(N, "§3-라 잎-하나-빼기")
    P(9, "최대 기여 = 시장팝업 · 기여 > 40%",
      lo["🔴 최대 기여 도메인"] == "시장팝업" and lo["🔴 그 기여 %"] > 40,
      "%s · %.1f%%" % (lo["🔴 최대 기여 도메인"], lo["🔴 그 기여 %"]))
    fl = _dig(N, "§3-마 팔 R")
    P(10, "그 하나를 빼면 팔 R 95 분위 아래",
      lo["🔴🔴 잎-하나-빼기 최소값"] < fl["🔴 95 분위"],
      "최소값 %.6f vs 바닥 %.6f" % (lo["🔴🔴 잎-하나-빼기 최소값"], fl["🔴 95 분위"]))
    P(11, "팔 R 2000 뽑기 95 분위 > 0.016593", fl["🔴 95 분위"] > 0.016593,
      "%.6f" % fl["🔴 95 분위"])

    af = _dig(N, "3순위 --- 연관 정정")
    ratio = af["🔴🔴 정정 --- **부호를 살린 판**"]
    P(12, "부호 살린 배수 < 2", ratio < 2.0,
      "%.2f 배 (abs 판 %.2f 배)" % (ratio, af["🔴🔴 971 헤드라인 「연관이 예측보다 몇 배」 --- `abs()` 판"]))
    flip = af["🔴🔴 실측 --- **학습 연관과 유보 연관의 부호가 갈리는 도메인**"]
    P(13, "갈리는 도메인 3 · 도서·세계애니 없음",
      flip["수"] == 3 and "도서" not in flip["목록"] and "세계애니" not in flip["목록"],
      "%s (%d 개)" % (", ".join(flip["목록"]) or "없음", flip["수"]))

    side = _dig(N, "§3-바 곁 팔")
    P(14, "MIN_TRAIN=15 곁 팔이 도메인을 8 이상으로", side["게이트 통과 도메인"] >= 8,
      "%d 도메인 (새로 들어온 것: %s)" % (side["게이트 통과 도메인"],
                                  ", ".join(side["새로 들어온 도메인"]) or "없음"))

    ok = sum(1 for v in S.values() if v["🔴 판정"].startswith("✅"))
    return {"채점표": S, "🔴 분자/분모": "맞다 %d / %d" % (ok, len(S))}


def substitutions(NUL, WIR, RST, META, C971) -> dict:
    """🔴🔴 **치환표(규칙 D)** --- 판정문·카드·논문은 **이 표의 값만** 쓸 수 있다."""
    N = NUL["🔴🔴🔴 §N 유보 예측 --- 진짜 귀무"]
    perm = _dig(N, "§3-가 정본 자")
    b3 = _dig(N, "§3-다 폭 셋")
    lo = _dig(N, "§3-라 잎-하나-빼기")
    fl = _dig(N, "§3-마 팔 R")
    af = _dig(N, "3순위 --- 연관 정정")
    mde = _dig(N, "묶음 최소검출효과")
    side = _dig(N, "§3-바 곁 팔")
    flip = af["🔴🔴 실측 --- **학습 연관과 유보 연관의 부호가 갈리는 도메인**"]
    W = WIR["§W 배선 --- 🔴 생산 함수를 태운다"]
    V = WIR["🔴🔴 §V 배선 파괴 대조(sabotage)"]
    rs = RST["🔴🔴🔴 §R 요약"]
    return {
        "묶음 Δρ_pred": N["🔴🔴 묶음 Δρ_pred(C−B)"],
        "971 과의 차": N["🔴 971 과의 차(묶음 Δ)"],
        "분모 ② 게이트 통과 도메인": N["🔴 분모 ② 게이트 통과 도메인"],
        "분모 ③ 유보 행 합": N["🔴 분모 ③ 유보 행 합"],
        "분모 ④ 학습 행 합": N["🔴 분모 ④ 학습 행 합"],
        "🔴 순열 p(정본 자)": perm["🔴🔴🔴 순열 p(단측 · 사전등록 §3-가 정본 자)"],
        "🔴 순열 채택": perm["🔴🔴 채택(p ≤ 0.05)"],
        "🔴 부호 일관성 p": perm["🔴🔴🔴 부호 일관성 p(사전등록 §3-나)"],
        "🔴 부호 일관성 채택": perm["🔴🔴 부호 일관성 채택(p ≤ 0.05)"],
        "🔴 971 조건 ⑤(≥5)가 귀무에서 통과하는 %": perm[
            "🔴 참고: 971 의 조건 ⑤(≥5 양수)가 귀무에서 통과하는 비율"],
        "귀무 중심": perm["귀무 중심(평균)"],
        "붓스트랩 SD 유보만": _dig(b3, "유보만")["🔴 짝 SD"],
        "붓스트랩 SD 학습만": _dig(b3, "학습만")["🔴 짝 SD"],
        "🔴 붓스트랩 SD 이중": _dig(b3, "이중")["🔴 짝 SD"],
        "🔴 이중 95% 구간": _dig(b3, "이중")["🔴 95% 구간"],
        "🔴 최대 기여 도메인": lo["🔴 최대 기여 도메인"],
        "🔴 그 기여 %": lo["🔴 그 기여 %"],
        "🔴 잎-하나-빼기 최소값": lo["🔴🔴 잎-하나-빼기 최소값"],
        "🔴 팔 R 2000 95 분위": fl["🔴 95 분위"],
        "팔 R 첫 50 재현": fl["🔴 첫 50 뽑기만 다시 낸 값"],
        "🔴 유보 가중 연관(부호 있음)": af["🔴 유보 행 가중 연관 ρ --- **부호 있음**"],
        "🔴 유보 가중 |연관|(971 판)": af["🔴 유보 행 가중 |연관 ρ| --- 971 이 쓴 수"],
        "🔴 연관÷예측 abs 판(971 헤드라인)":
            af["🔴🔴 971 헤드라인 「연관이 예측보다 몇 배」 --- `abs()` 판"],
        "🔴🔴 연관÷예측 부호 판(정정)": af["🔴🔴 정정 --- **부호를 살린 판**"],
        "🔴 유보 연관 음수 도메인 수": len(af["🔴 유보 연관이 음수인 도메인"]["목록"]),
        "🔴 그 도메인 유보 행 %": af["🔴 유보 연관이 음수인 도메인"]["유보 행 %"],
        "🔴🔴 부호 갈리는 도메인(정정)": flip["목록"],
        "🔴 그 수": flip["수"],
        "🔴 묶음 2SE 실값(원장의 「약 0.090」)": mde["🔴🔴 2 SE --- **원장이 「약 0.090」이라 적은 수**"],
        "곁 팔 MIN_TRAIN=15 도메인": side["게이트 통과 도메인"],
        "곁 팔 새 도메인": side["새로 들어온 도메인"],
        "곁 팔 묶음 Δ": side["묶음 Δρ_pred"],
        "🔴 배선 분자/분모": W["🔴 분자/분모(요약)"],
        "🔴 배선 붉은 자리": W["🔴 붉은 자리"],
        "🔴 파괴 대조 분자/분모": V["🔴 분자/분모"],
        "🔴 자 file 범위 뒤집힌 판(작은 꼬리 48줄)": rs["file · 작은"],
        "🔴 자 file 범위 뒤집힌 판(큰 꼬리 · 풀 잘림 넘김)": rs["file · 큰"],
        "🔴 자 file 범위 음성 대조(주석만)": rs["file · 주석만"],
        "🔴 자 func 범위 뒤집힌 판(작은)": rs["func · 작은"],
        "🔴 자 func 범위 뒤집힌 판(큰)": rs["func · 큰"],
        "🔴 자 func 범위 음성 대조(주석만)": rs["func · 주석만"],
        "🔴 범위만 바꿔도 낙하가 갈리나": rs["🔴🔴 범위를 바꾸는 것만으로 낙하가 갈리나"],
        "🔴 predict971 낙하(file · 커밋본)": META["file"]["predict971"]["🔴 증명된 낙하"],
        "🔴 predict971 낙하 %(file)": META["file"]["predict971"]["🔴 증명된 낙하 %"],
        "🔴 predict971 분모": META["file"]["predict971"]["🔴 분모"],
        "🔴 predict971 낙하(func)": META["func"]["predict971"]["🔴 증명된 낙하"],
        "🔴 predict971 낙하 %(func)": META["func"]["predict971"]["🔴 증명된 낙하 %"],
        "🔴 recommit970 낙하 %(밑값)": META["file"]["recommit970"]["🔴 증명된 낙하 %"],
        "🔴 971 이 적은 낙하": "4 / 13 (30.8%)",
        "🔴 971 요약 키 꼴 종수": C971["🔴🔴 요약 키 꼴(종수)"]["종수"],
        "🔴 971 §Z 없는 산출물": C971["🔴🔴 §Z 없는 산출물"]["🔴 분자/분모"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--null", default="runners/out972_null.json")
    ap.add_argument("--wiring", default="runners/out972_wiring.json")
    ap.add_argument("--rulerstab", default="runners/out972_rulerstab.json")
    ap.add_argument("--meta-file", default="runners/out972_meta_file.json")
    ap.add_argument("--meta-func", default="runners/out972_meta_func.json")
    a = ap.parse_args()

    t_start = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.time()
    NUL, WIR, RST = _load(a.null), _load(a.wiring), _load(a.rulerstab)

    def _meta(p):
        o = _load(p)
        pf = _dig(o, "§1", "파일별")
        return {k.split("/")[-1].replace(".py", ""): v for k, v in pf.items()}
    META = {"file": _meta(a.meta_file), "func": _meta(a.meta_func)}

    C971 = census971()
    R = {"🔴 노트": 972, "🔴 레인": "판정", "🔴 축": "C1 상태→예측",
         "🔴 시작(UTC)": t_start,
         "🔴 사전등록": "docs/prereg_972_c1null.md (측정 전 단독 커밋 8675748ed "
                   "· 2026-08-15T13:44:57Z)"}
    with PZ.ReadTap():
        cs0 = PZ.code_stamp()
        R["🔴🔴 §S 내가 돌린 러너 ↔ 커밋 blob(F1)"] = PZ.ran_vs_blob(a.ref)
        R["🔴🔴🔴 §P 사전등록 P1~P14 채점표"] = score(NUL, WIR, RST, META)
        R["🔴🔴 §C 971 산출물 전수(조항 66-② 신고)"] = C971
        R["🔴🔴🔴 §T 치환표 --- **판정문·카드·논문은 이 값만 쓴다**"] = \
            substitutions(NUL, WIR, RST, META, C971)
        R["🔴🔴 §M 자 팔 --- 커밋본 재주행"] = {
            "🔴 무엇": ("971 의 `out971_meta.json` 은 `predict971.py` sha `7a0f3f65…` 에서 "
                   "났는데 커밋된 blob 은 `c870fe5d…` 다. **자 팔이 돈 뒤 그 파일이 "
                   "+48/−4 고쳐졌고 산출물을 다시 안 냈다**(티처 #110 치명 1)"),
            "🔴 971 이 적은 것": "predict971 낙하 4 / 13 (30.8%) --- 밑값 recommit970 1/6 (16.7%)",
            "🔴 972 재주행(file 범위 · 965~971 과 같은 자)": META["file"],
            "🔴 972 재주행(func 범위 · 972 수리)": META["func"],
        }
        cs1 = PZ.code_stamp()
    seal = PZ.data_seal()    # 🔴 규칙 C --- 자료 지문은 **끝에 한 번**
    R["🔴 끝(UTC)"] = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    R["🔴 걸린 초"] = round(time.time() - t0, 1)
    R["🔴🔴 §Z 소스 대조"] = {
        "시작 code_stamp 요약": PZ.P.stamp_digest(cs0),
        "끝 code_stamp 요약": PZ.P.stamp_digest(cs1),
        "🔴 주행 중 소스가 바뀌었나": bool(cs0 != cs1),
        "🔴 잰 소스 sha(전량 · 자르지 않았다)": cs1,
        "🔴🔴 §D 자료 입력 지문(규칙 C)": seal,
    }
    Path(a.out if os.path.isabs(a.out) else str(ROOT / "runners" / a.out)).write_text(
        json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", a.out, R["🔴 걸린 초"], "s")


if __name__ == "__main__":
    main()
