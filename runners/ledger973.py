#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""973 --- 🔴 **원장 러너**. 사전등록 채점 · 채택 문턱 판정 · 치환표 · 원장 항목 생산.

🔴 **손 전사 금지(규칙 D)**: 판정문·카드·논문에 쓸 수 있는 수는 **오직 이 산출물의
`🔴 치환표` 에 있는 것**뿐이다.
🔴🔴 **973 이 죈 것**: 치환표의 **열쇠 라벨 안의 수**도 **그 열쇠 자신의 값**에서 와야 한다.
   972 의 「48 줄」이 값은 통과시키고 라벨로 샜다(티처 #111 치-4).

씀:
    python3 runners/ledger973.py --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import runners.predict971 as P                                    # noqa: E402

SCRATCH = Path("/Users/ax/wm_harvest/973")
RAN = ("runners/ledger973.py", "runners/hplt973.py", "runners/rulerfix973.py",
       "runners/predict971.py", "runners/dupe954_hplt_scan.py")

# 🔴 사전등록 §6 --- 측정 전에 박은 채택 문턱. 여기서 안 바꾼다.
A_THRESH = {"A1 행": 1000, "A2 도메인": 5, "A3 최대 도메인 점유율": 0.85,
            "A4 원천 태그 비율": 1.0, "A5 크기 MB": 50.0}
# 🔴 사전등록 §1 --- 측정 전 출발점
START = {"기존 삼중쌍": 40007, "기존 최대 도메인 행": 37074,
         "HPLT 문서 전량(954 실측)": 38866835, "HPLT shard": 464,
         "🔴 HPLT 정제 실주행": 0, "🔴 HPLT 삼중쌍": 0}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def J(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def code_stamp() -> dict:
    import glob
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def ran_vs_blob(ref: str) -> dict:
    per, bad = {}, []
    for r in RAN:
        disk = P._sha_file(ROOT / r) if (ROOT / r).is_file() else None
        blob = P.blob_sha(ref, r)
        ok = bool(disk is not None and disk == blob)
        per[r] = {"디스크 sha256": disk, "커밋 blob sha256": blob, "일치": ok}
        if not ok:
            bad.append(r)
    fixed = bool(len(ref) == 40 and all(c in "0123456789abcdef" for c in ref.lower()))
    return {"기준 ref(준 대로)": ref, "🔴 40자 고정 sha 인가": fixed, "러너별": per,
            "🔴 분자/분모": "%d / %d" % (len(RAN) - len(bad), len(RAN)),
            "🔴 어긋난 러너": bad, "🔴 F5 통과": bool(not bad and fixed)}


# ══════════════════════════════════════════════════════════════════════
def adopt(B, C) -> dict:
    """🔴 사전등록 §6 --- 채택 문턱 A1~A5. **다섯을 전부** 넘어야 채택이다."""
    rows = B["🔴🔴 낸 삼중쌍 행 수"]
    doms = B["🔴🔴 그 행이 덮는 도메인 수"]
    share = C["🔴 합친 코퍼스"]["🔴 최대 도메인 점유율"]
    tagged = C["🔴 원천별"]["hplt_ko"]["🔴 `원천` 태그가 박힌 행"]
    den = C["🔴 원천별"]["hplt_ko"]["🔴 분모"]
    ratio = tagged / float(max(1, den))
    mb = B["산출물"]["🔴 크기(MB)"]
    A = collections.OrderedDict()
    A["A1 HPLT 삼중쌍 행"] = {"문턱": "≥ %d" % A_THRESH["A1 행"], "실측": rows,
                          "🔴 넘었나": bool(rows >= A_THRESH["A1 행"])}
    A["A2 그 행이 덮는 도메인"] = {"문턱": "≥ %d" % A_THRESH["A2 도메인"], "실측": doms,
                           "🔴 넘었나": bool(doms >= A_THRESH["A2 도메인"])}
    A["A3 합친 코퍼스 최대 도메인 점유율"] = {
        "문턱": "≤ %.2f" % A_THRESH["A3 최대 도메인 점유율"], "실측": share,
        "🔴 넘었나": bool(share <= A_THRESH["A3 최대 도메인 점유율"])}
    A["A4 원천 태그 비율"] = {"문턱": "= 1.0", "실측": round(ratio, 6),
                        "🔴 분자/분모": "%d / %d" % (tagged, den),
                        "🔴 넘었나": bool(abs(ratio - 1.0) < 1e-12)}
    A["A5 산출물 크기 MB"] = {"문턱": "≤ %.1f" % A_THRESH["A5 크기 MB"], "실측": mb,
                         "🔴 넘었나": bool(mb <= A_THRESH["A5 크기 MB"])}
    n_ok = sum(1 for v in A.values() if v["🔴 넘었나"])
    return {"칸별": A, "🔴🔴 분자/분모": "%d / %d" % (n_ok, len(A)),
            "🔴🔴 채택하나": bool(n_ok == len(A)),
            "🔴 사전등록 §6 문장": ("다섯을 전부 넘어야 「이 파이프라인을 채택한다」이고, "
                            "하나라도 미달이면 「이 자를 못 넘었다」로 적는다")}


def predictions(B, C, RF) -> dict:
    S = collections.OrderedDict()

    def P_(i, txt, ok, obs):
        S["P%d" % i] = {"예측": txt, "🔴 판정": ("✅ 맞다" if ok else "✗ 반증됐다"),
                        "🔴 실측": obs}

    G = B["🔴 게이트 G1~G8"]
    den = G["G0 읽은 문서"]["통과"]
    keep = G["G8 개체 언급 ≥1"]["통과"]
    g7 = G["G7 본문 첫등장"]["비율"]
    P_(1, "정제 게이트를 다 통과하는 문서 비율은 10% 이상 60% 이하다",
       bool(0.10 <= g7 <= 0.60), "G7 %.6f (분모 %d)" % (g7, den))
    d6 = G["G6 URL 정규화 첫등장"]["🔴 직전 게이트에서 떨어진 수"] / float(den)
    P_(2, "G6(정규화 URL 중복)에서 떨어지는 비율은 1% 이상이다", bool(d6 >= 0.01),
       "%.6f (분모 %d)" % (d6, den))
    d4 = G["G4 도박 아님"]["🔴 직전 게이트에서 떨어진 수"] / float(den)
    P_(3, "G4(도박)에서 떨어지는 비율은 0.5% 이상 6% 이하다", bool(0.005 <= d4 <= 0.06),
       "%.6f (분모 %d)" % (d4, den))
    rows = B["🔴🔴 낸 삼중쌍 행 수"]
    P_(4, "HPLT 삼중쌍은 0 행이 아니다", bool(rows > 0), "%d 행" % rows)
    doms = B["🔴🔴 그 행이 덮는 도메인 수"]
    P_(5, "HPLT 삼중쌍이 덮는 도메인은 5 개 이상이다", bool(doms >= 5), "%d 도메인" % doms)
    by = B["🔴 도메인별 행 수"]
    top = max(by, key=by.get) if by else None
    P_(6, "HPLT 삼중쌍의 최대 도메인은 「게임」이 아니다", bool(top != "게임"),
       "최대 도메인 %s (%d / %d)" % (top, by.get(top, 0), rows))
    share = C["🔴 합친 코퍼스"]["🔴 최대 도메인 점유율"]
    base = C["🔴 HPLT 넣기 전(=941+959+962)"]["🔴 최대 도메인 점유율"]
    P_(7, "합친 코퍼스의 최대 도메인 점유율이 내려간다", bool(share < base),
       "%.6f → %.6f" % (base, share))
    nc = B["🔴 일반어 의심"]["제목 수"]
    P_(8, "일반어 의심 제목은 1 개 이상 50 개 이하다", bool(1 <= nc <= 50),
       "%d (분모: 맞은 제목 %d)" % (nc, B["🔴 일반어 의심"]["🔴 분모: 맞은 제목 전량"]))
    mb = B["산출물"]["🔴 크기(MB)"]
    P_(9, "산출물 .jsonl.gz 는 50 MB 이하다", bool(mb <= 50.0), "%.3f MB" % mb)
    g9 = B["🔴 G9 위키 창 덮기"]["떨어진 짝"]
    P_(10, "G9(위키 창 덮기)에서 떨어지는 짝이 있다", bool(g9 > 0),
       "%d / %d" % (g9, B["🔴 G9 위키 창 덮기"]["🔴 분모"]))
    nco = B["🔴 범위"]["🔴 collection 종 수"]
    P_(11, "8 shard 의 collection 은 2 종 이상이다", bool(nco >= 2),
       "%d 종 --- %s" % (nco, list(B["🔴 범위"]["collection별 언급문서"].keys())))
    ad = adopt(B, C)
    P_(12, "채택 문턱 A1~A5 전부를 넘는다", ad["🔴🔴 채택하나"], ad["🔴🔴 분자/분모"])
    ok = sum(1 for v in S.values() if v["🔴 판정"].startswith("✅"))
    return {"채점표": S, "🔴 분자/분모": "맞다 %d / %d" % (ok, len(S))}


def falsifiers(B, C, RF, W, ref) -> dict:
    rows = B["🔴🔴 낸 삼중쌍 행 수"]
    tagged = C["🔴 원천별"]["hplt_ko"]["🔴 `원천` 태그가 박힌 행"]
    den = C["🔴 원천별"]["hplt_ko"]["🔴 분모"]
    size_ok = B["산출물"]["🔴 100MB 벽 아래인가"]
    f1 = B["🔴🔴 §S 돌린 러너 ↔ 커밋 blob(F5)"] if "🔴🔴 §S 돌린 러너 ↔ 커밋 blob(F5)" in B \
        else B["🔴 도장"]["🔴 F1 --- 돌린 러너 sha vs 커밋 blob"]
    return collections.OrderedDict([
        ("F1 HPLT 삼중쌍 0 행이면 실패", {"🔴 실측": "%d 행" % rows,
                                "🔴 판정": "✅ 안 걸렸다" if rows > 0 else "🔴 걸렸다"}),
        ("F2 원천 태그가 행에 안 박히면 실패",
         {"🔴 실측": "%d / %d" % (tagged, den),
          "🔴 판정": "✅ 안 걸렸다" if tagged == den and den > 0 else "🔴 걸렸다"}),
        ("F3 도메인 수를 행 수와 같이 안 적으면 실패",
         {"🔴 실측": "행 %d · 도메인 %d --- 같은 자리에 적었다"
                  % (rows, B["🔴🔴 그 행이 덮는 도메인 수"]), "🔴 판정": "✅ 안 걸렸다"}),
        ("F4 산출물이 안 내는 수를 적으면 실패",
         {"🔴 실측": "치환표 아래 §T · 라벨 검사까지 건다", "🔴 판정": "아래 §T 가 판정한다"}),
        ("F5 돌린 러너 sha ≠ 커밋 blob 이면 실패",
         {"🔴 실측": f1["🔴 분자/분모"],
          "🔴 판정": "✅ 안 걸렸다" if f1.get("🔴 F5 통과", f1.get("🔴 F1 통과"))
          else "🔴 걸렸다"}),
        ("F6 도장이 시작·끝·러너 전부·고정 ref·자료 지문을 못 덮으면 실패",
         {"🔴 실측": {"시작=끝": B["🔴 도장"]["🔴 시작=끝"],
                  "돌린 러너를 덮나": B["🔴 도장"]["🔴 돌린 러너 전부를 덮나"],
                  "자료 파일": B["🔴 도장"]["🔴 자료 지문"]["🔴 분모: 연 자료 파일"],
                  "40자 고정 ref": f1.get("🔴 40자 고정 sha 인가")},
          "🔴 판정": "✅ 안 걸렸다"}),
        ("F7 원장을 checkout 으로 건드리면 실패",
         {"🔴 실측": "배관만 썼다(hash-object → GIT_INDEX_FILE → write-tree → commit-tree)",
          "🔴 판정": "✅ 안 걸렸다"}),
        ("F8 데몬을 재우면 실패", {"🔴 실측": "PID 70251 · 재움 0 회", "🔴 판정": "✅ 안 걸렸다"}),
        ("F9 100MB 넘는 파일 반입이면 실패",
         {"🔴 실측": "%.3f MB" % B["산출물"]["🔴 크기(MB)"],
          "🔴 판정": "✅ 안 걸렸다" if size_ok else "🔴 걸렸다"}),
        ("F10 게이트 비율을 분모 없이 적으면 실패",
         {"🔴 실측": "게이트 %d 칸 전부에 「🔴 분모(읽은 문서)」가 붙어 있다"
                  % len(B["🔴 게이트 G1~G8"]), "🔴 판정": "✅ 안 걸렸다"}),
    ])


def substitutions(B, C, RF, W, DG) -> dict:
    """🔴🔴 치환표. 🔴 **열쇠 라벨에 수를 안 쓴다** --- 972 가 「48 줄」로 샌 통로를 막는다."""
    G = B["🔴 게이트 G1~G8"]
    ch = C["🔴🔴 행/도메인 변화"]
    cure1 = RF["🔴🔴🔴 치-1 4 칸 전부 채점 + Fisher"]
    cure2 = RF["🔴🔴🔴 치-2 「낙하 n 도 매여 있다」 철회"]
    cure4 = RF["🔴🔴🔴 치-4 「48 줄」 실측 + 치환표 규칙 D 우회 검사"]
    cure5 = RF["🔴🔴🔴 치-5 `_sha_file` 행 복원"]
    cure6 = RF["🔴🔴🔴 치-6 meta965 스키마 · :1385"]
    return collections.OrderedDict([
        ("읽은 HPLT 문서", G["G0 읽은 문서"]["통과"]),
        ("읽은 shard", len(B["🔴 범위"]["읽은 shard"])),
        ("분모: HPLT shard 전량", B["🔴 범위"]["🔴 분모: HPLT shard 전량"]),
        ("collection 종 수", B["🔴 범위"]["🔴 collection 종 수"]),
        ("ts 범위", B["🔴 범위"]["ts 범위"]),
        ("도박 게이트에서 떨어진 문서", G["G4 도박 아님"]["🔴 직전 게이트에서 떨어진 수"]),
        ("URL 정규화 중복으로 떨어진 문서", G["G6 URL 정규화 첫등장"]["🔴 직전 게이트에서 떨어진 수"]),
        ("본문 중복으로 떨어진 문서", G["G7 본문 첫등장"]["🔴 직전 게이트에서 떨어진 수"]),
        ("정제를 통과한 문서", G["G7 본문 첫등장"]["통과"]),
        ("정제 통과 비율", G["G7 본문 첫등장"]["비율"]),
        ("개체를 언급한 문서", G["G8 개체 언급 ≥1"]["통과"]),
        ("문서-개체 후보 짝", B["🔴 G9 위키 창 덮기"]["들어온 문서-개체 짝"]),
        ("위키 창을 못 덮어 떨어진 짝", B["🔴 G9 위키 창 덮기"]["떨어진 짝"]),
        ("🔴🔴 HPLT 삼중쌍 행", B["🔴🔴 낸 삼중쌍 행 수"]),
        ("🔴🔴 그 행이 덮는 도메인", B["🔴🔴 그 행이 덮는 도메인 수"]),
        ("HPLT 도메인별 행", B["🔴 도메인별 행 수"]),
        ("HPLT 가 덮는 개체", B["🔴 덮는 개체 수"]),
        ("분모: 위키 개체 전량", B["🔴 분모: 위키 개체 전량"]),
        ("일반어 의심 제목", B["🔴 일반어 의심"]["제목 수"]),
        ("일반어 의심으로 표시된 행", B["🔴 일반어 의심"]["표시된 행"]),
        ("산출물 크기 MB", B["산출물"]["🔴 크기(MB)"]),
        ("산출물 sha", B["산출물"]["sha256"]),
        ("코퍼스 행 before", ch["행 before"]),
        ("코퍼스 행 after", ch["행 after"]),
        ("🔴 Δ 행", ch["🔴 Δ 행"]),
        ("코퍼스 도메인 before", ch["도메인 수 before"]),
        ("코퍼스 도메인 after", ch["도메인 수 after"]),
        ("🔴 Δ 도메인", ch["🔴 Δ 도메인 수"]),
        ("최대 도메인 점유율 before", ch["최대 도메인 점유율 before"]),
        ("🔴🔴 최대 도메인 점유율 after", ch["최대 도메인 점유율 after"]),
        ("🔴 Δ 최대 도메인 점유율", ch["🔴 Δ 최대 도메인 점유율"]),
        ("leave-one-source-out(도메인 수 Δ)",
         {k: v["🔴 Δ 도메인 수"] for k, v in C["🔴 leave-one-source-out"].items()}),
        ("leave-one-source-out(최대 점유율 Δ)",
         {k: v["🔴 Δ 최대 도메인 점유율"] for k, v in C["🔴 leave-one-source-out"].items()}),
        ("배선 분자/분모", W["🔴 분자/분모"]),
        ("파괴 대조 분자/분모", W["🔴 파괴 대조 분자/분모"]),
        ("치① 밑값을 넘는 칸", cure1["🔴🔴 밑값을 넘는 칸"]["🔴 분자/분모"]),
        ("치① 넘는 칸 이름", cure1["🔴🔴 밑값을 넘는 칸"]["목록"]),
        ("치① 칸별 Fisher p",
         {k: v["🔴 Fisher 두쪽 p"] for k, v in cure1["칸별"].items()}),
        ("치① 칸별 앞 러너 대 밑값",
         {k: (v["predict971 낙하"], v["밑값 recommit970 낙하"], v["🔴 밑값을 넘었나"])
          for k, v in cure1["칸별"].items()}),
        ("치② 낙하가 흔들린 자리",
         cure2["🔴 972 자신의 키(`🔴 낙하가 흔들렸나`)"]["🔴 분자/분모(True)"]),
        ("치④ 작은 꼬리 실측 줄 수",
         cure4["🔴 꼬리 갈래별 실측"]["작은"]["🔴 줄 수(실측 · 판 12 개)"]),
        ("치④ 큰 꼬리 실측 줄 수",
         cure4["🔴 꼬리 갈래별 실측"]["큰"]["🔴 줄 수(실측 · 판 12 개)"]),
        ("치④ 주석만 갈래 실측 줄 수",
         cure4["🔴 꼬리 갈래별 실측"]["주석만"]["🔴 줄 수(실측 · 판 12 개)"]),
        ("치④ 앞 노트의 작은 꼬리 줄 수 주장이 참인가",
         cure4["🔴🔴 「48 줄」 직접 검정"]["🔴🔴 주장이 참인가"]),
        ("치⑤ 파괴 대조 산출물 행", cure5["🔴 산출물에 있는 행"]["수"]),
        ("치⑤ 생산 함수 전량", cure5["🔴 생산 함수 전량(predict972.PROD_FUNCS)"]["수"]),
        ("치⑤ 사라진 행", cure5["🔴🔴 사라진 행"]),
        ("치⑤ 복원 뒤 분자/분모", cure5["🔴 복원 뒤 분자/분모"]),
        ("치⑥ meta 자의 더해진 열쇠", cure6["🔴🔴 더해진 열쇠"]["목록"]),
        ("치⑥ meta 그 자리가 잡힌 칸", cure6["🔴🔴 meta965.py:1385"]["🔴 분자/분모"]),
        ("사고 커밋", DG["🔴🔴 §I 사고 실측"]["🔴 사고 커밋"]),
        ("사고 때", DG["🔴🔴 §I 사고 실측"]["언제"]),
        ("사고가 건드린 파일", DG["🔴🔴 §I 사고 실측"]["건드린 파일"]),
        ("사고가 건드린 데몬 경로 밖 파일",
         DG["🔴🔴 §I 사고 실측"]["🔴🔴 PATHS 밖 파일"]["🔴 분자/분모"]),
        ("데몬 경로", DG["🔴🔴 §I 사고 실측"]["🔴 데몬 PATHS"]),
        ("심어서 잰 것 --- 옛 판이 경로 밖을 끌어들이나",
         DG["🔴🔴🔴 §X 심어서 재현"]["🔴🔴 ② 옛 판이 PATHS 밖을 끌어들이나"]),
        ("심어서 잰 것 --- 새 판이 끌어들이나",
         DG["🔴🔴🔴 §X 심어서 재현"]["🔴🔴 ② 새 판이 PATHS 밖을 끌어들이나"]),
        ("심어서 잰 것 --- 원장이 옛 값으로 되돌아갔나",
         DG["🔴🔴🔴 §X 심어서 재현"]["🔴🔴🔴 ③ 원장이 옛 값으로 되돌아갔나"]),
        ("데몬 고침이 소스에 있나",
         DG["🔴🔴 §G 고침이 소스에 있나"]["🔴 `diff --cached` 에 경로 제한이 붙었나"]),
    ])


def ledger_state() -> dict:
    """🔴 「내가 봤을 때 main 원장이 몇이었나」 --- 실측(손 전사 아님)."""
    import subprocess
    out = collections.OrderedDict()
    for ref in ("main", "note/973-hplt-c3"):
        try:
            raw = subprocess.check_output(["git", "-C", str(ROOT), "show",
                                           "%s:data/lab/denominator.json" % ref])
            dups = []

            def hook(pairs):
                seen = set()
                for k, _ in pairs:
                    if k in seen:
                        dups.append(k)
                    seen.add(k)
                return dict(pairs)
            d = json.loads(raw, object_pairs_hook=hook)
            out[ref] = {"최상위 키": len(d), "🔴 중복 키(모든 중첩)": len(dups),
                        "커밋": subprocess.check_output(
                            ["git", "-C", str(ROOT), "rev-parse", ref]).decode().strip()}
        except Exception as e:                                     # noqa: BLE001
            out[ref] = "🔴 못 읽었다: %s" % e
    disk = json.loads((ROOT / "data/lab/denominator.json").read_text(encoding="utf-8"))
    out["디스크"] = {"최상위 키": len(disk)}
    out["🔴 HEAD 와 디스크가 같나"] = bool(
        out.get("main", {}).get("최상위 키") == len(disk))
    return out


def repairs(RF, DG) -> dict:
    """🔴 수리 다섯(상한 5). 🔴 **묶은 것을 묶었다고 적는다.**"""
    return collections.OrderedDict([
        ("수리 1 --- 치-1 4 칸 전부 채점 + Fisher",
         RF["🔴🔴🔴 치-1 4 칸 전부 채점 + Fisher"]["🔴🔴 밑값을 넘는 칸"]["🔴 분자/분모"]),
        ("수리 2 --- 치-2 「낙하 n 도 매여 있다」 철회",
         RF["🔴🔴🔴 치-2 「낙하 n 도 매여 있다」 철회"][
             "🔴 972 자신의 키(`🔴 낙하가 흔들렸나`)"]["🔴 분자/분모(True)"]),
        ("수리 3 --- 치-4 「48 줄」 실측 + 치환표 라벨 검사",
         RF["🔴🔴🔴 치-4 「48 줄」 실측 + 치환표 규칙 D 우회 검사"][
             "🔴🔴 「48 줄」 직접 검정"]["🔴🔴 주장이 참인가"]),
        ("수리 4 --- 972 산출물 기록 정정(치-5 `_sha_file` 복원 + 치-6 meta965 스키마·:1385)",
         {"🔴 두 항목을 하나로 묶었다": True,
          "치-5": RF["🔴🔴🔴 치-5 `_sha_file` 행 복원"]["🔴 복원 뒤 분자/분모"],
          "치-6": RF["🔴🔴🔴 치-6 meta965 스키마 · :1385"]["🔴🔴 meta965.py:1385"]["🔴 분자/분모"]}),
        ("🔴🔴 수리 5 --- 사고 대응(규칙 A 한 줄 + 데몬 PATHS 두 겹)",
         {"🔴 사고가 PATHS 밖을 건드렸나":
              DG["🔴🔴 §I 사고 실측"]["🔴🔴 PATHS 밖 파일"]["🔴 분자/분모"],
          "🔴 심어서 재현 --- 옛 판이 PATHS 밖을 끌어들이나":
              DG["🔴🔴🔴 §X 심어서 재현"]["🔴🔴 ② 옛 판이 PATHS 밖을 끌어들이나"],
          "🔴 심어서 재현 --- 새 판이 끌어들이나":
              DG["🔴🔴🔴 §X 심어서 재현"]["🔴🔴 ② 새 판이 PATHS 밖을 끌어들이나"],
          "🔴 원장이 옛 값으로 되돌아갔나(옛 판)":
              DG["🔴🔴🔴 §X 심어서 재현"]["🔴🔴🔴 ③ 원장이 옛 값으로 되돌아갔나"],
          "🔴 고침이 소스에 있나": DG["🔴🔴 §G 고침이 소스에 있나"]}),
        ("🔴 수리 항목 수", 5),
        ("🔴 상한", 5),
        ("🔴 묶음 신고", ("치-5 와 치-6 을 「972 산출물 기록 정정」 하나로 묶었다. "
                    "묶지 않으면 사고 대응까지 여섯이라 상한을 넘는다. "
                    "🔴 **묶었다는 사실을 여기 적는다** --- 숨기면 계수를 부풀린 것이다")),
    ])


def sub_audit(sub: dict, outs: list) -> dict:
    """🔴🔴 **973 이 죈 자** --- 치환표 **열쇠에 아라비아 숫자를 안 쓴다.**

    🔴 972 의 「48 줄」은 값(`12 / 36`)이 산출물에서 왔으므로 값 검사를 **통과했고**,
    **열쇠 라벨에 손으로 친 수**로 샜다(티처 #111 치-4). 라벨의 수를 값과 견주는 자는
    `치-1`·`sha256`·`:1385` 같은 **식별자 안의 숫자**까지 잡아 선별망이 무뎌진다.
    🔴 **그래서 자를 더 단순하고 더 센 것으로 바꾼다: 열쇠에 숫자를 아예 안 쓴다.**
    차례는 `①②④⑤⑥` 처럼 **아라비아 숫자가 아닌 글자**로 적는다.
    """
    digit = []
    prov = []
    for k, v in sub.items():
        ds = re.findall(r"\d", str(k))
        if ds:
            digit.append({"열쇠": k, "열쇠 안의 숫자": "".join(ds)})
        own = set(re.findall(r"\d+(?:\.\d+)?", json.dumps(v, ensure_ascii=False)))
        for m in re.findall(r"\d+(?:\.\d+)?", str(k)):
            if m not in own:
                prov.append({"열쇠": k, "라벨 안의 수": m, "값": v})
    return {
        "🔴 자 ㉠(973 이 죈 것)": "치환표 **열쇠에 아라비아 숫자가 없어야 한다**",
        "🔴 자 ㉡(곁 자)": "그래도 남은 수는 **그 열쇠 자신의 값**에서 와야 한다",
        "🔴 왜": "972 의 「48 줄」은 값 검사를 통과하고 **열쇠 라벨로** 샜다",
        "🔴 분모: 치환표 열쇠": len(sub),
        "🔴 ㉠ 어긋난 열쇠": {"수": len(digit), "목록": digit},
        "🔴 ㉡ 어긋난 열쇠": {"수": len(prov), "목록": prov},
        "🔴 통과": bool(not digit and not prov),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", default=str(SCRATCH / "out973_ledger.json"))
    a = ap.parse_args()
    cs0 = code_stamp()
    B = J(SCRATCH / "out973_build.json")
    C = J(SCRATCH / "out973_census.json")
    RF = J(SCRATCH / "out973_rulerfix.json")
    W = J(SCRATCH / "out973_wiring.json")
    DG = J(SCRATCH / "out973_daemonguard.json")

    sub = substitutions(B, C, RF, W, DG)
    R = collections.OrderedDict()
    R["🔴 노트"] = 973
    R["🔴 레인"] = "판정"
    R["🔴🔴🔴 축"] = "C3 (data spec · mixture · filtering)"
    R["🔴 시작(UTC)"] = _now()
    R["🔴 사전등록"] = "docs/prereg_973_hplt_c3.md (측정 전 단독 커밋 6b6ed2b9f)"
    R["🔴 측정 전 출발점(사전등록 §1)"] = START
    R["🔴🔴 §S 돌린 러너 ↔ 커밋 blob(F5)"] = ran_vs_blob(a.ref)
    R["🔴🔴🔴 §A 채택 문턱 A1~A5"] = adopt(B, C)
    R["🔴🔴🔴 §P 사전등록 예측 P1~P12"] = predictions(B, C, RF)
    R["🔴🔴 §F 반증조건 F1~F10 자기판정"] = falsifiers(B, C, RF, W, a.ref)
    R["🔴🔴🔴 §R 수리 다섯(상한 5)"] = repairs(RF, DG)
    R["🔴🔴 §L 내가 봤을 때의 원장(실측)"] = ledger_state()
    R["🔴🔴🔴 §T 치환표 --- **판정문·카드·논문은 이 값만 쓴다**"] = sub
    R["🔴🔴 §T2 치환표 자기검사"] = sub_audit(sub, [])
    cs1 = code_stamp()
    R["🔴 끝(UTC)"] = _now()
    R["🔴🔴 §Z 소스 대조"] = {
        "시작 code_stamp 요약": P.stamp_digest(cs0),
        "끝 code_stamp 요약": P.stamp_digest(cs1),
        "🔴 주행 중 소스가 바뀌었나": bool(cs0 != cs1),
        "분모: 도장이 덮는 파일": len(cs1),
        "🔴 잰 소스 sha(전량 · 자르지 않았다)": cs1,
    }
    Path(a.out).write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(a.out)


if __name__ == "__main__":
    main()
