# -*- coding: utf-8 -*-
"""노트 944(수리) — 판정 단위를 「열」에서 **「(계열, 열)」**로 바꾼다.

티처 #83 C1: `runners/out943_axis.py:81` 이 `GRADE["capacity"]=PRE` 로 놓고 근거를
`ingest/derive_features.py:98` 로 드는데, **그 근거는 A 계열 경로(:150-152)에만 참**이다.
B 계열은 `:170-172` 에서 blob 이 다르다 — `json.dumps(iv) + str(r.get("notes"))`.
**`notes` 는 행사 뒤에 쓰인 보도 요약**이다.

그리고 `out943_axis.py:263` 의 `grade_of(k)` 는 **열 이름만** 받는데 같은 러너의
`colcnt` 는 이미 `(fam, key)` 로 센다 — **한 검출기, 두 스키마**(942 의 병)를
그것을 고치는 러너가 자기 판정표에 남겼다.

이 러너가 하는 것 다섯:

  **ㄱ** 🔴 **배선 검사** — 943 의 `GRADE`·`grade_of` 를 **import 해서 호출**해
        `PRE 1,053 · 모른다 90 · POST 22` 를 **고치기 전 그대로** 재현하고,
        동결 산출물 `runners/out943_axis.json` 과 대조한다.
  **ㄴ** `grade_of(fam, key)` 로 갈라 다시 판정한다.
  **ㄷ** 🔴 **겹침을 명시한다** — 세 통은 분할이 아니다(합 > 분모).
  **ㄹ** 🔴 **notes 가 실제로 승격을 만드는가**를 직접 잰다(사전등록 밖의 추가 측정):
        같은 정규식을 `notes` **없이** 물려 본다.
  **ㅁ** 🔴 **규약 충돌** — `lab/provenance.py` 를 정본으로 놓고, `state/dataset_v2.py`
        가 만드는 축 이름을 전수로 뽑아 `WHEN` 등록 여부를 센다.

🔴 941·942·943 산출물은 동결이다 — 이 러너는 `runners/out944_famgrade.json` 만 쓴다.
🔴 판 ρ 는 안 부른다.
🔴 스탬프 넷: 시작 시각 · **끝 시각** · **입력 sha256** · **코드 sha256**.

사전등록: `docs/prereg_944_famgrade.md`(측정 **전** 커밋 `e71dc122f`)

쓰는 법::  python3 runners/out944_famgrade.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

REC_DIRS = ("data/records", "data/market_records", "data/idol_records",
            "data/records_draft", "data/records_incomplete",
            "data/records_thinbak")
OUT = ROOT / "runners/out944_famgrade.json"

PERIOD_KEYS = {"period", "period_from", "period_to"}

#: 🔴 **이 사이클의 수리 그 자체** — (계열 첫 글자, 열) 에만 붙는 판정.
#:   여기 없으면 943 의 열 단위 표(`GRADE`)로 떨어진다. 즉 **바뀐 것은 한 칸**이다.
FAM_GRADE = {
    ("B", "capacity"): (
        "모른다", "ㅁ",
        "🔴 B 계열은 ingest/derive_features.py:170-172 에서 "
        "`blob = json.dumps(iv) + str(r.get('notes'))` 로 capacity_upgrade 를 부른다. "
        "`notes` 는 **행사 뒤에 쓰인 보도 요약**이다(ingest/market_merge.py:169 이 "
        "'2차 수집(2026-07-27)' 을 이어 붙인다). 943 이 근거로 든 :98 의 정규식은 같지만 "
        "**입력이 다르다** — A 의 :150-152 는 intervention+conditions(계획 원문)뿐이다. "
        "'없다'가 아니라 '액션 앞에 알 수 있었는지 못 가른다'(조항 59)"),
}

#: ㄹ 943 의 `CAP_PAT` 을 **import 해서** 쓴다(베끼지 않는다).


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dir_digest(d: str) -> dict:
    h = hashlib.sha256()
    n = 0
    for f in sorted((ROOT / d).glob("*.json")):
        h.update(f.name.encode())
        h.update(sha(f).encode())
        n += 1
    return {"파일": n, "sha256(파일명+파일sha 이어붙임)": h.hexdigest()}


def _nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, (str, list, dict, tuple)) and len(v) == 0:
        return False
    return True


def main() -> dict:                                        # noqa: PLR0912, PLR0915
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # ── ㄱ 배선 검사: 943 의 표와 함수를 **import 해서 호출**한다 ──────────
    from runners.out942_stock import family as fam_942       # noqa: PLC0415
    from runners.out943_axis import GRADE as GRADE_943       # noqa: PLC0415
    from runners.out943_axis import grade_of as grade_943    # noqa: PLC0415
    from ingest.derive_features import CAP_PAT               # noqa: PLC0415

    wiring = {
        "943 의 GRADE 를 import 했나": isinstance(GRADE_943, dict),
        "GRADE 항목 수": len(GRADE_943),
        "943 이 capacity 를 뭐라 했나": GRADE_943.get("capacity", (None,))[0],
        "grade_of 가 받는 인자 수(943)": grade_943.__code__.co_argcount,
        "CAP_PAT 을 ingest 에서 import 했나": sorted(CAP_PAT),
    }

    def grade_new(fam: str, key: str) -> tuple:
        """🔴 **(계열, 열)** 로 판정한다. 없으면 943 의 열 단위 표로 떨어진다."""
        hit = FAM_GRADE.get((fam[0], key))
        if hit:
            return hit
        return grade_943(key)

    n = 0
    fam_c: Counter = Counter()
    colcnt: Counter = Counter()
    # 고치기 전(943 · 열 단위)
    bucket_old: Counter = Counter()
    pre_old: Counter = Counter()
    # 고친 뒤(944 · (계열,열) 단위)
    bucket_new: Counter = Counter()
    pre_new: Counter = Counter()
    pair_new: Counter = Counter()      # 겹침 — 통 쌍
    unknown_new: Counter = Counter()
    unknown_fam: Counter = Counter()
    fell_out = []                      # PRE 통에서 아주 떨어진 레코드
    both_fam: dict = {}                # 열 → 그 열이 값을 가진 계열 집합

    # ㄹ notes 가 승격을 만드는가
    capdet: Counter = Counter()
    cap_access: Counter = Counter()
    notes_needed = 0
    notes_notneeded = 0
    cap_b_total = 0
    cap_examples = []
    #: 🔴 blob 셋을 갈라 잰다. `intervention.concept_description` 이 **notes 의 복사본**일 수
    #:   있어서(ingest/market_merge.py:150 `notes[:200]`) 「notes 를 뺐다」가 참이 아닐 수 있다.
    blob3: Counter = Counter()
    cd_is_notes = 0
    # P4 — A 계열 capacity
    cap_a_total = 0
    capdet_a: Counter = Counter()
    cap_access_a: Counter = Counter()

    for d in REC_DIRS:
        for f in sorted((ROOT / d).glob("*.json")):
            try:
                r = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(r, dict):
                continue
            n += 1
            fam = fam_942(r)
            fam_c[fam] += 1
            c = r.get("conditions")
            if not isinstance(c, dict):
                continue

            seen_old, seen_new = set(), set()
            npre_old = npre_new = 0
            for k, v in c.items():
                if k in PERIOD_KEYS:
                    colcnt[(fam, k + "  → a 로 옮김")] += _nonempty(v)
                    continue
                items = ([("derived." + k2, v2) for k2, v2 in v.items()]
                         if (k == "derived" and isinstance(v, dict)) else [(k, v)])
                for key, val in items:
                    g_old = grade_943(key)[0]
                    g_new, src_new, _w = grade_new(fam, key)
                    colcnt[(fam, key + f"  [{g_new}·{src_new}]")] += _nonempty(val)
                    if not _nonempty(val):
                        continue
                    both_fam.setdefault(key, set()).add(fam[0])
                    seen_old.add(g_old)
                    npre_old += (g_old == "PRE")
                    seen_new.add(g_new)
                    npre_new += (g_new == "PRE")
                    if g_new == "모른다":
                        unknown_new[key] += 1
                        unknown_fam[(fam[0], key)] += 1
            for g in seen_old:
                bucket_old[g] += 1
            for g in seen_new:
                bucket_new[g] += 1
            for a in sorted(seen_new):
                for b in sorted(seen_new):
                    if a < b:
                        pair_new[a + " ∩ " + b] += 1
            pre_old[npre_old] += 1
            pre_new[npre_new] += 1
            if "PRE" in seen_old and "PRE" not in seen_new:
                fell_out.append(r.get("record_id") or f.stem)

            # ── P4 A 계열 capacity ────────────────────────────────────────
            cap = c.get("capacity")
            if fam.startswith("A") and isinstance(cap, dict) and _nonempty(cap):
                cap_a_total += 1
                det_a = cap.get("detail") or ""
                capdet_a["키워드 승격" if "키워드 승격" in det_a else "그 밖"] += 1
                cap_access_a[cap.get("access_type")] += 1

            # ── ㄹ notes 가 승격을 만드는가 (B 계열만) ────────────────────
            if fam.startswith("B") and isinstance(cap, dict) and _nonempty(cap):
                cap_b_total += 1
                det = cap.get("detail") or ""
                capdet["키워드 승격" if "키워드 승격" in det else "그 밖"] += 1
                cap_access[cap.get("access_type")] += 1
                iv = r.get("intervention") or {}
                blob_no = json.dumps(iv, ensure_ascii=False)
                if iv.get("reservation_required"):
                    blob_no += " 예약제"
                blob_yes = (json.dumps(iv, ensure_ascii=False)
                            + str(r.get("notes") or ""))
                if iv.get("reservation_required"):
                    blob_yes += " 예약제"
                # 🔴 세 번째 blob — intervention 에서 concept_description 까지 뺀다
                iv_bare = {k2: v2 for k2, v2 in iv.items()
                           if k2 != "concept_description"}
                blob_bare = json.dumps(iv_bare, ensure_ascii=False)
                if iv.get("reservation_required"):
                    blob_bare += " 예약제"
                nt = str(r.get("notes") or "")
                cd = str(iv.get("concept_description") or "")
                if cd and nt and (cd in nt or nt.startswith(cd[:60])):
                    cd_is_notes += 1
                hit_no = any(re.search(p, blob_no) for p in CAP_PAT.values())
                hit_yes = any(re.search(p, blob_yes) for p in CAP_PAT.values())
                hit_bare = any(re.search(p, blob_bare) for p in CAP_PAT.values())
                blob3["실제 blob(iv+notes) 에서 걸림"] += hit_yes
                blob3["notes 만 뺀 blob 에서 걸림"] += hit_no
                blob3["🔴 notes·concept_description 둘 다 뺀 blob 에서 걸림"] += hit_bare
                if hit_yes and not hit_bare:
                    blob3["🔴 사후 문자열이 있어야만 걸리는 레코드"] += 1
                if hit_yes and not hit_no:
                    notes_needed += 1
                    if len(cap_examples) < 3:
                        cap_examples.append({
                            "record": r.get("record_id") or f.stem,
                            "notes": str(r.get("notes") or "")[:120],
                            "access_type": cap.get("access_type"),
                            "detail": det[:80]})
                elif hit_no:
                    notes_notneeded += 1

    # ── ㅁ 규약 충돌 — provenance 를 정본으로 놓고 dataset_v2 축을 전수로 ──
    prov_rep: dict = {}
    try:
        from lab import provenance as PV                     # noqa: PLC0415
        prov_rep["WHEN 등록 축 수"] = len(PV.WHEN)
        prov_rep["기본값(미등록 축)"] = PV.when("__없는축__")[0]
        t1b = ["t1b_host_traffic", "t1b_venue_footfall", "t1b_pass_rate", "t1b_tier"]
        prov_rep["🔴 t1b 넷"] = {a: {"WHEN 에 있나": a in PV.WHEN,
                                   "when()": PV.when(a)[0],
                                   "usable()": PV.usable(a)} for a in t1b}
    except Exception as e:                                   # noqa: BLE001
        prov_rep["🔴 못 읽음"] = repr(e)

    ds_rep: dict = {}
    try:
        from state.dataset_v2 import popup_rows              # noqa: PLC0415
        _X, _yt, _yp, _w, _meta, names = popup_rows()
        from lab import provenance as PV2                    # noqa: PLC0415
        base = [x for x in names if not x.endswith("_mask")]
        unreg = [x for x in base if x not in PV2.WHEN]
        blocked = [x for x in base if not PV2.usable(x)]
        ds_rep = {
            "dataset_v2 축 이름 수(마스크 제외)": len(base),
            "축 이름 수(마스크 포함)": len(names),
            "🔴 provenance.WHEN 에 미등록": len(unreg),
            "🔴 usable() == False": len(blocked),
            "미등록 축(앞 40개)": unreg[:40],
            "🔴 t1b 넷이 실제 축에 있나": [x for x in base if x.startswith("t1b_")],
        }
    except Exception as e:                                   # noqa: BLE001
        ds_rep["🔴 못 지음"] = repr(e)

    # 🔴 지어 둔 판 행렬에서 t1b 넷이 **살아 있나**. `lab/guards.py:374` 의 g_when 은
    #    표시자 평균 > 0.01 인 축만 본다 — 그 문턱을 넘는지 실측한다.
    npz_rep: dict = {}
    try:
        import numpy as _np                                   # noqa: PLC0415
        z = _np.load(ROOT / "data/state/popup_v2.npz", allow_pickle=True)
        nm = [str(x) for x in z["names"]]
        X = z["X"]
        npz_rep = {"파일": "data/state/popup_v2.npz",
                   "sha256": sha(ROOT / "data/state/popup_v2.npz"),
                   "행": int(X.shape[0]), "열": int(X.shape[1]),
                   "g_when 문턱": 0.01,
                   "🔴 t1b 넷의 표시자 평균": {
                       a: round(float(X[:, nm.index(a + "_mask")].mean()), 4)
                       for a in ("t1b_host_traffic", "t1b_venue_footfall",
                                 "t1b_pass_rate", "t1b_tier") if a + "_mask" in nm},
                   }
        npz_rep["🔴 넷 다 문턱을 넘나"] = all(
            v > 0.01 for v in npz_rep["🔴 t1b 넷의 표시자 평균"].values())
    except Exception as e:                                   # noqa: BLE001
        npz_rep["🔴 못 읽음"] = repr(e)

    # P7 — 게이트가 실제로 물려 있나
    #: 🔴 초판은 `callers(pat, "lab/ state/ ingest/ runners/")` 로 **경로 넷을 한 문자열**로
    #:   넘겨서 grep 이 아무것도 못 찾고 **[] 를 냈다**. 「0건」으로 읽힐 뻔했다 — 조항 59.
    def callers(pat: str, where: list) -> list:
        r = subprocess.run(["grep", "-rn", "--include=*.py", pat, *where],
                           capture_output=True, text=True, timeout=120)
        return [x for x in r.stdout.splitlines() if x]

    scope = ["lab", "state", "ingest", "runners", "harness", "serve"]
    gate = {
        "🔴 grep 범위(조항 60)": {"명령": "grep -rn --include=*.py <pat> " + " ".join(scope),
                             "트리": "작업 트리"},
        "state/dataset_v2.py 안의 usable/audit/when 호출":
            callers(r"usable(\|audit(\|when(\|when_in(", ["state/dataset_v2.py"]),
        "provenance 를 import 하는 파일":
            sorted({x.split(":")[0] for x in callers(r"import.*provenance\|from .*provenance",
                                                     scope)}),
        "🔴 usable( 를 부르는 곳": callers(r"usable(", scope),
        "🔴 audit( · audit_data( 를 부르는 곳": callers(r"audit(\|audit_data(", scope),
    }

    both = {k: sorted(v) for k, v in sorted(both_fam.items()) if len(v) > 1}

    inputs = {d: dir_digest(d) for d in REC_DIRS}
    frozen = {p: sha(ROOT / p) for p in ("runners/out943_axis.json",
                                         "runners/out942_stock.json") if (ROOT / p).exists()}
    code = {p: sha(ROOT / p) for p in ("runners/out944_famgrade.py",
                                       "runners/out943_axis.py",
                                       "ingest/derive_features.py",
                                       "lab/provenance.py", "state/dataset_v2.py")}

    denom = fam_c["A_팝업(outcome.totals)"] + fam_c["B_시장(평평한 outcome)"]

    res = {
        "노트": 944, "레인": "수리",
        "무엇": "판정 단위를 「열」 → 「(계열, 열)」 · 규약 충돌의 정본을 정한다 (티처 #83 C1·M7)",
        "사전등록": "docs/prereg_944_famgrade.md (커밋 e71dc122f · 측정 전)",
        "🔴 스탬프(git rev-parse HEAD 안 쓴다)": {
            "시작 시각": t_start, "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256(D1 디렉터리별)": inputs,
            "입력 sha256(동결 산출물)": frozen,
            "코드 sha256": code,
        },
        "🔴 조항 60 — 명령·범위·트리": {
            "명령": "python3 runners/out944_famgrade.py",
            "범위": list(REC_DIRS),
            "트리": "작업 트리만 읽는다(인덱스와 안 섞는다)",
        },
        "🔴 안 부른 자": "판 ρ · 문턱 0.00353",

        "🔴 분모": {"D1(파일)": n, "계열 분포": dict(fam_c),
                  "🔴 합 == 분모": sum(fam_c.values()) == n,
                  "🔴 ㄹ 판정의 분모(A+B · C 는 conditions 행 0)": denom},

        "🔴 ㄱ 배선 검사": wiring,

        "🔴 ㄴ 고치기 전/후 나란히": {
            "고치기 전(943 · 열 단위)": dict(bucket_old),
            "🔴 고친 뒤(944 · (계열,열) 단위)": dict(bucket_new),
            "차": {k: bucket_new[k] - bucket_old[k]
                  for k in set(bucket_old) | set(bucket_new)},
            "🔴 PRE 통에서 아주 떨어진 레코드": fell_out,
            "레코드당 PRE 열 개수 — 전": dict(sorted(pre_old.items())),
            "레코드당 PRE 열 개수 — 후": dict(sorted(pre_new.items())),
        },

        "🔴 ㄷ 겹침 (세 통은 분할이 아니다)": {
            "분모": denom,
            "세 통 세로합": sum(bucket_new.values()),
            "🔴 세로합 − 분모": sum(bucket_new.values()) - denom,
            "쌍별 겹침": dict(pair_new),
        },

        "🔴 모른다로 센 열": {"열별": dict(unknown_new.most_common()),
                        "(계열,열)별": {f"{a} · {b}": v
                                    for (a, b), v in unknown_fam.most_common()}},

        "🔴 ㄹ notes 가 승격을 만드는가 (사전등록 밖의 추가 측정 · B 계열)": {
            "B 계열 capacity 값 있는 레코드": cap_b_total,
            "detail 분포": dict(capdet),
            "access_type 분포": dict(cap_access),
            "🔴 notes 를 빼면 정규식이 안 걸리는 레코드": notes_needed,
            "notes 없이도 걸리는 레코드": notes_notneeded,
            "🔴 분모": cap_b_total,
            "🔴 blob 셋 — concept_description 이 notes 의 복사본이라 「notes 를 뺐다」가 참이 아니다":
                dict(blob3),
            "🔴 concept_description 이 notes 안에 그대로 든 레코드": cd_is_notes,
            "보기 셋": cap_examples,
        },

        "🔴 P4 — A 계열 capacity (분모 A 407)": {
            "값 있는 레코드": cap_a_total,
            "detail 분포": dict(capdet_a),
            "access_type 분포": dict(cap_access_a),
            "🔴 A 는 PRE 유지": "derive_features.py:150-152 의 blob 은 "
                            "intervention + conditions(derived 제외)뿐 — notes 를 안 먹는다",
        },

        "🔴 P5 — 두 계열에 다 값이 있는 열": {
            "열 목록": both,
            "🔴 그중 계열별로 코드 경로가 다른 것": ["capacity"],
            "손으로 확인한 근거": {
                "derived.ip_history": "A·B 가 **같은 함수** ip_history() 를 부른다"
                                      "(derive_features.py:129 · 둘 다 `e[0] < open_from` 컷) → PRE 유지",
                "derived.duration": "A·B 가 같은 duration_features(from,to) → PRE 유지",
                "area_pyeong": "B 는 market_merge.py:156 이 **None 으로 박는다**"
                               "(값 있는 14 는 그 앞 MKT- 경로) — notes 를 안 먹는다 → PRE 유지",
                "capacity": "🔴 A :150-152 vs B :170-172 — **입력이 다르다**",
            },
        },

        "🔴 ㅁ 규약 충돌 — lab/provenance.py 가 정본": {
            "정본 선언": "「축을 판에 써도 되나」는 provenance 가 정한다(미등록=사후=막는다). "
                     "943 의 「모른다」는 **다른 물음**(아는가)의 답이고 막는 힘이 없다. "
                     "포섭: 회계에서 모른다인 열이 만드는 축은 usable()==False 여야 한다. "
                     "그 포섭을 **기본값에 안 기대고** WHEN 에 명시 등록한다",
            "provenance": prov_rep,
            "dataset_v2": ds_rep,
            "🔴 지어 둔 판 행렬에서 t1b 가 살아 있나": npz_rep,
            "게이트가 물려 있나": gate,
            "🔴 못 본 것": "이 79 축이 `data.names['팝업']` 에 그대로 들어가는지는 **안 봤다** — "
                      "lab/popupset.py·lab/popaxes.py 가 부분집합을 고른다. "
                      "확인한 것은 ①dataset_v2 가 넷을 만든다 ②지어 둔 npz 에 살아 있고 "
                      "표시자가 g_when 문턱을 넘는다 ③provenance 에 미등록이라 usable()=False "
                      "④state/dataset_v2.py 가 게이트를 **한 번도 안 부른다**",
        },

        "🔴 열별 레코드 수(계열 · 값 있는 것만)":
            {f"{f} · {k}": v for (f, k), v in
             sorted(colcnt.items(), key=lambda x: (x[0][0], -x[1])) if v},
    }

    # 동결 산출물과 대조 (배선 검사 — 943 이 **적었던 수**와 내가 **다시 부른 값**)
    fz = ROOT / "runners/out943_axis.json"
    if fz.exists():
        z = json.loads(fz.read_text())["🔴 ㄹ conditions 열 단위 판정 (PRE / POST / 모른다)"]
        old = z["🔴 그 통의 열을 하나라도 가진 레코드 수"]
        oldpre = {int(k): v for k, v in z["🔴 레코드당 PRE 열 개수 분포"].items()}
        res["🔴 ㄱ 배선 검사"]["🔴 943 산출물과 같은가(고치기 전)"] = {
            "943 이 적은 통": old, "지금 부른 통": dict(bucket_old),
            "같나": old == dict(bucket_old),
            "943 이 적은 PRE 분포 == 지금": oldpre == dict(pre_old),
        }

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items()
                      if k != "🔴 열별 레코드 수(계열 · 값 있는 것만)"},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
