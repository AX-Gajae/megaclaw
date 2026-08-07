"""아이돌 초동 라벨의 계수 기준을 출처에서 분리한다.

문제. `chodong_basis` 가 통제 어휘가 아니라 자유 텍스트다. 175건의 값이 28가지로
흩어져 있는데, 그 대부분은 기준이 아니라 **출처**다 --- "나무위키 앨범 문서
'초동 판매량' 전사표(...)" 같은 문자열이 통째로 들어가 있다. 나무위키는 출처지
계수 기준이 아니다. 같은 나무위키 전사가 한터 수치일 수도 써클 수치일 수도 있다.

이것은 노트 1이 팝업에서 규명한 병과 정확히 같다. 거기서는 주최자 발표와 현장 계수가
한 컬럼에 섞여 2.75배 벌어져 있었다. 여기서는 한터와 써클과 오리콘이 섞여 있다.
세 기준은 집계 기간도 유통망도 다르므로 다른 물리량이다.

  · 한터(hanteo)  --- 한터차트 가맹 소매점 실판매, 발매 후 7일
  · 써클(circle)  --- 구 가온, 출고량 기준 월간 집계
  · 오리콘(oricon) --- 일본 시장, 국내와 유통망 자체가 다르다

해법. 출처 문자열은 `chodong_source_kind` 로 옮기고, 기준은 노트·인용문 전체에서
명시적 언급을 찾아 `chodong_basis_resolved` 로 확정한다. 두 기준이 함께 언급되면
어느 수치인지 결정할 수 없으므로 `ambiguous` 로 남긴다 --- 추측하지 않는다.

결과(2026-07-28): 한터 단독 확정 67 → 96건. 모호 14, 미상 61, 오리콘 1.

사용:
  python3 -m ingest.idol_basis            # 진단만
  python3 -m ingest.idol_basis --write    # 레코드에 필드 추가
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

REC = Path("data/idol_records")

HANTEO = re.compile(r"한터|hanteo", re.I)
CIRCLE = re.compile(r"써클|서클|가온|circle\s*chart|gaon", re.I)
ORICON = re.compile(r"오리콘|oricon", re.I)
BILLBOARD = re.compile(r"빌보드|billboard", re.I)

# 출처 종류 — 기준이 아니다. 섞이면 안 되는 두 개념이므로 분리해 기록한다.
SRC = [("namu", re.compile(r"나무위키|namu", re.I)),
       ("hanteo_official", re.compile(r"한터차트\s*공식|hanteonews|hanteochart", re.I)),
       ("press", re.compile(r"^press|언론|뉴스|일보|신문|연합", re.I)),
       ("agency", re.compile(r"소속사|공식\s*발표|보도자료", re.I))]


# 기준 판정에 쓸 필드는 **초동 전용 필드로 한정**한다.
# 처음에 notes·chart_note까지 훑었더니 33건이 ambiguous로 나왔는데, 전부 오탐이었다 ---
# "써클차트 2019년 12주차 주간 앨범차트 최고 N위" 같은 문장은 초동 수치의 기준이 아니라
# 별개의 차트 순위 서술이다. 초동이 무엇으로 세어졌는지는 초동 필드만 말할 수 있다.
CHODONG_KEYS = ("chodong_basis", "chodong_note", "chodong_source_quote")
CONTEXT_KEYS = ("notes", "chart_note", "chodong_source_url")


def blob(r: dict, wide: bool = False) -> str:
    keys = CHODONG_KEYS + (CONTEXT_KEYS if wide else ())
    return " ".join(str(r.get(k) or "") for k in keys)


def resolve(r: dict) -> dict:
    b = blob(r)
    found = [n for n, rx in (("hanteo", HANTEO), ("circle", CIRCLE),
                             ("oricon", ORICON), ("billboard", BILLBOARD)) if rx.search(b)]
    # 오리콘·빌보드가 단독이면 그 기준이다. 국내 기준과 섞이면 결정 불가다.
    if len(found) == 1:
        basis, why = found[0], "명시 단일"
    elif not found:
        basis, why = "unknown", "기준 언급 없음"
    else:
        # 노트가 초동 수치를 특정 기준에 직접 귀속하면 그것을 따른다.
        # '한터 차트 초동 판매량', '한터 기준', '오리콘 주간 1주차' 같은 형태.
        m = re.search(r"(한터|써클|가온|오리콘)\s*(차트)?\s*"
                      r"(기준|집계|초동|판매량|주간|1주차)", b)
        if m:
            k = m.group(1)
            basis = {"한터": "hanteo", "써클": "circle", "가온": "circle",
                     "오리콘": "oricon"}[k]
            why = "초동 필드 내 직접 귀속"
        else:
            basis, why = "ambiguous", "복수 기준 언급: " + "+".join(found)

    kind = next((n for n, rx in SRC if rx.search(str(r.get("chodong_basis") or ""))), None)
    if kind is None:
        kind = next((n for n, rx in SRC if rx.search(b)), "unknown")
    return {"chodong_basis_resolved": basis, "chodong_basis_why": why,
            "chodong_source_kind": kind}


def run(write: bool = False) -> dict:
    files = sorted(REC.glob("*.json"))
    stat, changed = Counter(), 0
    per_kind = Counter()
    for f in files:
        r = json.loads(f.read_text())
        if not isinstance(r.get("chodong"), (int, float)):
            continue
        out = resolve(r)
        stat[out["chodong_basis_resolved"]] += 1
        per_kind[(out["chodong_source_kind"], out["chodong_basis_resolved"])] += 1
        if write and any(r.get(k) != v for k, v in out.items()):
            r.update(out)
            f.write_text(json.dumps(r, ensure_ascii=False, indent=1))
            changed += 1

    total = sum(stat.values())
    print(f"라벨 보유 {total}건")
    print("\n=== 확정된 계수 기준 ===")
    for k, v in stat.most_common():
        print(f"  {k:<12}{v:>4} ({v/total:.0%})")
    print("\n=== 출처 종류 × 기준 ===")
    for (s, b), v in sorted(per_kind.items(), key=lambda x: -x[1])[:12]:
        print(f"  {s:<18}{b:<12}{v:>4}")
    print(f"\n학습 가능 풀(한터 단독): {stat['hanteo']}건")
    if write:
        print(f"기록 완료: {changed}건 갱신")
    return dict(stat)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    run(write=a.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
