"""장소 키 정규화 — '미상' 75건이 뱅크 최대 장소가 되어 있던 문제.

entities.space_key는 예측기가 '같은 장소의 선례'를 찾는 조인 키다. 그런데 75건이
'미상'으로 들어가 있고, 그중 9건은 conditions.location.venue_name에 멀쩡한 장소가
적혀 있다. '미상' 75건은 더현대서울(33건)보다 큰 최대 노드이고, 서로 다른 장소들이
하나로 뭉쳐 있으니 조인 결과는 잡음이다.

발견 루프 R1의 venue_slot_key 후보(8건 지지)가 지적한 바로 그 지점:
  "RIPU2401: venue 필드 하나로 APE 84.3%→0.8% — 같은 존 선례 4건이 이미 뱅크 안에 있었다"
실제로 RIPU2401의 venue_name은 '더현대서울 B2F ICONIC ZONE'이고 뱅크에 더현대서울
레코드가 33건 있다. 조인 키만 비어 있었다.

방식: 기존 space_key 어휘를 사전으로 삼아 venue_name을 매칭한다. 새 키를 지어내기보다
이미 쓰이는 키에 붙이는 쪽이 조인을 만든다. 매칭 실패 시에만 새 키를 만든다.

층·존은 별도 필드(venue_slot)로 분리한다 — 같은 건물이라도 B2 아이코닉존과 8F
대행사장은 유동이 다르지만, 건물 단위 선례도 없는 것보단 낫기 때문에 키를 쪼개지 않는다.

사용:
  python3 -m ingest.venue_key            # 무엇이 어떻게 바뀌는지만 출력
  python3 -m ingest.venue_key --write    # 적용
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

MISSING = {None, "", "미상", "불명", "N/A", "없음"}
# 층·존 표기 — 건물명에서 떼어내 venue_slot으로 보관
SLOT = re.compile(r"(B?\d+\s*F|지하\s*\d+층|\d+\s*층|[A-Z]홀|[A-Z]\d{3,4}|"
                  r"아이코닉\s*존|ICONIC\s*ZONE|팝업\s*존|대행사장|행사장|로비|아트리움|"
                  r"(?<![가-힣])광장(?![가-힣]))",          # '광장시장'을 자르지 않도록
                  re.IGNORECASE)
# 구·동 단위 키 — 건물이 아니므로 여기에 붙이면 '같은 장소'라는 조인의 의미가 깨진다
DISTRICT_ONLY = {"성수", "강남", "홍대", "명동", "여의도", "압구정", "한남", "잠실",
                 "종로", "이태원", "가로수길", "삼성동", "청담"}
# 여러 장소가 한 레코드에 담긴 표기
MULTI = re.compile(r"\d\s*개\s*(대학|매장|점포|지점|빌딩|공장|곳)|외\s*\d|[,/]\s*\S+[,/]|일대")


def nfc(s) -> str:
    return unicodedata.normalize("NFC", str(s or ""))


def _core(s: str) -> str:
    """건물명 핵심부만 — 공백·기호·층존 표기 제거."""
    s = SLOT.sub(" ", nfc(s))
    s = re.sub(r"\([^)]*\)", " ", s)                 # 괄호 주석 제거
    s = re.sub(r"[^\w가-힣A-Za-z]", "", s)
    return s.lower()


def vocabulary() -> Counter:
    """현재 쓰이는 space_key 어휘 — 빈도 높은 키에 붙이는 쪽이 조인을 만든다."""
    c = Counter()
    for p in Path("data/records").glob("*.json"):
        k = json.loads(p.read_text())["entities"].get("space_key")
        if k not in MISSING and not str(k).startswith("multi_"):
            c[k] += 1
    return c


def match(venue_name: str, vocab: Counter) -> tuple[str | None, str]:
    """venue_name → 기존 space_key. 반환 (키, 매칭근거)."""
    vn = _core(venue_name)
    if not vn:
        return None, ""
    best, why = None, ""
    for k, n in vocab.most_common():                 # 빈도순 — 큰 노드에 우선 붙인다
        if k in DISTRICT_ONLY:                       # 구 단위 키에는 붙이지 않는다
            continue
        kc = _core(k.replace("_", " "))
        if not kc or len(kc) < 3:                    # 2글자 키는 오매칭이 잦다
            continue
        if kc in vn or vn in kc:
            best, why = k, f"'{kc}' ⊂ '{vn}'"
            break
        # '_'로 구성된 키는 마지막 토큰(지점명)이 핵심인 경우가 많다
        parts = [_core(x) for x in k.split("_") if len(_core(x)) >= 2]
        if parts and all(p in vn for p in parts):
            best, why = k, f"토큰 {parts} 전부 포함"
            break
    return best, why


def slot_of(venue_name: str) -> str | None:
    m = SLOT.findall(nfc(venue_name))
    return " ".join(dict.fromkeys(x.strip() for x in m)) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    vocab = vocabulary()
    fixed, newkey, unresolved, slots = [], [], [], 0

    for p in sorted(Path("data/records").glob("*.json")):
        r = json.loads(p.read_text())
        loc = r["conditions"].get("location") or {}
        vn = loc.get("venue_name")
        sk = r["entities"].get("space_key")
        lab = r["outcome"]["totals"].get("visitors")
        changed = False

        s = slot_of(vn) if vn else None
        if s and loc.get("venue_slot") != s:
            loc["venue_slot"] = s
            slots += 1
            changed = True

        if sk in MISSING and vn:
            k, why = match(vn, vocab)
            if k:
                fixed.append((r["record_id"], vn, k, why, lab))
                r["entities"]["space_key"] = k
                r["entities"]["space_key_source"] = "venue_key 정규화 (venue_name 매칭)"
                changed = True
            elif MULTI.search(nfc(vn)):
                # 여러 장소가 한 레코드 — 단일 건물 키를 지어내면 거짓 조인이 된다
                newkey.append((r["record_id"], vn, "multi_미지정", lab))
                r["entities"]["space_key"] = "multi_미지정"
                r["entities"]["space_key_source"] = "venue_key 정규화 (다중 장소)"
                changed = True
            else:
                base = SLOT.sub(" ", nfc(vn).split("(")[0].split(",")[0])
                base = re.split(r"\s+(?:및|외)\s+", base)[0]
                nk = re.sub(r"\s+", "_", base.strip()).strip("_")[:32]
                if nk:
                    newkey.append((r["record_id"], vn, nk, lab))
                    r["entities"]["space_key"] = nk
                    r["entities"]["space_key_source"] = "venue_key 정규화 (신규 키)"
                    changed = True
        elif sk in MISSING:
            unresolved.append((r["record_id"], lab))

        if changed and a.write:
            p.write_text(json.dumps(r, ensure_ascii=False, indent=1))

    print(json.dumps({"기존 키 매칭": len(fixed), "신규 키 생성": len(newkey),
                      "여전히 미상(venue_name 자체가 없음)": len(unresolved),
                      "venue_slot 추출": slots, "기록": bool(a.write)}, ensure_ascii=False))
    print("\n■ 기존 키에 붙은 건 (조인 복구)")
    for x in fixed:
        tag = f"방문 {x[4]:,}" if x[4] else "라벨X"
        print(f"   {x[0]:10s} {x[1][:42]:42s} → {x[2]:20s} [{tag}]  {x[3]}")
    if newkey:
        print("\n■ 신규 키 (뱅크에 선례 없음)")
        for x in newkey[:20]:
            tag = f"방문 {x[3]:,}" if x[3] else "라벨X"
            print(f"   {x[0]:10s} {x[1][:42]:42s} → {x[2]:24s} [{tag}]")
        if len(newkey) > 20:
            print(f"   … 외 {len(newkey)-20}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
