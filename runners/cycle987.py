#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""987 배관 — 🔴🔴🔴 **「전」은 고정 ref 로만 읽고, 세는 것은 「이름 붙은 범위」로만 센다**.

🔴 **왜 (티처 #125).**

| 병 | 986 이 어떻게 걸렸나 | 987 의 배선 |
|---|---|---|
| 「전」을 디스크에서 읽었다 | `audit986.py:414` 가 `_text("docs/루프.md")` 로 **고정 ref 없이** 읽어, 자기가 38 분 전에 넣은 것을 「986 이 넣기 전 실측 = `True`」로 실었다(참값 `False`) | `fixed_ref_text()` **하나만** 「전」을 읽는다 --- 반환값이 **읽은 ref 를 들고 온다** |
| 한 이름 두 값 | 985 가 「분모 ② 역참조 소비자 수」라는 **한 이름**으로 `eba25b8fc..196c9e0ec`(446)와 `91ec43686..note/985`(415) **두 범위**를 쟀다 | `consumer_count()` 가 **이름·base·head·tree 를 반환값에 박는다** --- 이름 없는 계수를 만들 수 없다 |
| `DOC_INPUTS` 가 3 | 판정문이 싣는 `house`·`prose` 의 수가 **밖**이라 문서 뒤에 다시 돌아도 안 떨어졌다 | **5** 로 넓히고 **뺀 둘과 사유를 조문으로** 적는다 |

🔴 **`DOC_INPUTS` 에서 «뺀» 둘과 사유**(사전등록 §4-3 · 조용히 안 뺀다 · 조항 60):
`out987_certify.json` 과 `out987_table.json` 은 **문서 자체의 함수**다 ---
지문에 넣으면 이 자는 **원리상 고정점에 도달 못 한다**(자기 참조).
"""
import collections
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                                   # noqa: E402

#: 🔴🔴🔴 **사이클 전체 러너 합집합.** 987 의 모든 산출물이 이 하나를 쓴다.
RAN_ALL = (
    # ㉠ 987 이 돌린다
    "runners/cycle987.py",
    "runners/house987.py",
    "runners/audit987.py",
    "runners/power987.py",
    "runners/score987.py",
    "runners/note987_gen.py",
    "runners/certify987.py",
    "runners/prose987.py",
    "runners/plumb987.py",
    "runners/fiveprime902.py",
    # ㉡ 987 이 «값을 읽는» 러너 --- 🔴 조항 66-① 「잰 소스의 sha 를 산출물에 박는다」
    "runners/cycle986.py",
    "runners/audit986.py",
    "runners/power986.py",
    "runners/score986.py",
    "runners/note986_gen.py",
    "runners/certify986.py",
    "runners/house986.py",
    "runners/prose986.py",
    "runners/power985.py",
    "runners/score985.py",
    "runners/audit985.py",
    "runners/stat983.py",
    "runners/tgrid983.py",
    # ㉢ 그 둘이 import 한다
    "runners/ledger.py",
    "runners/alpha977.py",
    "runners/mix980.py",
    "runners/harvest_daemon.py",
)

#: 🔴🔴 **반증조건 14·15 의 분모** --- 987 이 «새로 쓴» 러너 전량.
RAN_987 = (
    "runners/cycle987.py",
    "runners/house987.py",
    "runners/audit987.py",
    "runners/power987.py",
    "runners/score987.py",
    "runners/note987_gen.py",
    "runners/certify987.py",
    "runners/prose987.py",
    "runners/plumb987.py",
)

DATA = dict(LG.DATA) if isinstance(getattr(LG, "DATA", None), dict) else {}

#: 987 이 값을 읽는 산출물
FEEDS_IN = (
    "runners/out983_grid.json",
    "runners/out983_reps.json",
    "runners/out985_table.json",
    "runners/out985_audit.json",
    "runners/fiveprime_985.json",
    "runners/out986_audit.json",
    "runners/out986_power.json",
    "runners/out986_score.json",
    "runners/out986_table.json",
    "runners/out986_certify.json",
    "runners/fiveprime_986.json",
)

SEAL_SKIP_DEFAULT = ("🔴🔴 치환표",)
WINDOW = "runners/out987_window.json"

SHARED = ("runners/cycle987.py", "runners/ledger.py")
PRODUCER = {
    "runners/out987_house.json": "runners/house987.py",
    "runners/out987_audit.json": "runners/audit987.py",
    "runners/out987_power.json": "runners/power987.py",
    "runners/out987_score.json": "runners/score987.py",
    "runners/out987_table.json": "runners/note987_gen.py",
    "runners/out987_certify.json": "runners/certify987.py",
    "runners/out987_prose.json": "runners/prose987.py",
}

# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 고정 ref --- 「전」을 «디스크에서» 읽는 길을 없앤다 (사전등록 §3-1)
# ══════════════════════════════════════════════════════════════════════
#: 🔴 **986 이 끝난 트리**(#244 배관 머지 직후의 `main`). 「986 이 실은 것」은 전부 여기서 읽는다.
REF_986 = "6b399dfc652b211fc0431bfb5259e2c496ddb757"
#: 🔴 **985 가 끝난 트리.** 「985 가 실은 것」은 전부 여기서 읽는다.
REF_985 = "582444a856f6c573c7d5ebb34c5579497f5faee6"

#: 🔴 **AST 자의 등록 면제**(사전등록 §3-1-가 · 조용히 안 뺀다).
#:  「지금」을 읽어야 하는 자리다 --- 규칙 D 채점·산문 자·문서 쓰기.
DISK_READ_EXEMPT = {
    "runners/score987.py": "🔴 규칙 D 는 «지금»의 문서를 읽어야 한다(「전」이 아니다)",
    "runners/prose987.py": "🔴 산문 자는 «지금»의 판정문을 읽어야 한다",
    "runners/note987_gen.py": "🔴 문서 생산기는 «지금»의 문서를 쓴다",
}


class RefError(RuntimeError):
    pass


def _git(args, binary=False):
    p = subprocess.run(["git", "-c", "core.quotePath=false"] + args, cwd=str(ROOT),
                       capture_output=True)
    if p.returncode != 0:
        raise RefError("git %s -> %d: %s" % (args[:2], p.returncode,
                                             p.stderr.decode("utf-8", "replace")[:300]))
    return p.stdout if binary else p.stdout.decode("utf-8", "surrogateescape")


def fixed_ref_text(ref, rel):
    """🔴🔴🔴 **「전」 값을 읽는 «유일한» 문**.

    🔴 반환값이 **읽은 ref 를 들고 온다** --- 그래야 치환표에 짝 칸 `전.*.ref` 를 박을 수 있고,
    그 칸이 40 자 sha 가 아니면 **반증조건 16** 이 반증된다.

    🔴 **디스크는 «안» 본다.** `ref` 가 40 자 sha 가 아니면 즉시 실패한다 ---
    가지 이름이나 `HEAD` 는 긴 러너에서 「시작 시점」으로 흔들린다(조항 66 · 루프 v3.2).
    """
    if not (isinstance(ref, str) and len(ref) == 40 and
            all(c in "0123456789abcdef" for c in ref)):
        raise RefError("🔴 고정 ref 가 40자 sha 가 아니다: %r" % (ref,))
    try:
        txt = _git(["show", "%s:%s" % (ref, rel)])
    except RefError as e:
        return {"🔴 고정 ref": ref, "🔴 경로": rel, "🔴 본문": None,
                "🔴 못 읽었다(= 「없다」가 아니다 · 조항 59)": str(e)[:200]}
    return {"🔴 고정 ref": ref, "🔴 경로": rel, "🔴 본문": txt,
            "🔴 sha256(그 트리의 blob)": hashlib.sha256(txt.encode("utf-8",
                                                                "surrogateescape")).hexdigest()}


def fixed_ref_json(ref, rel):
    """🔴 고정 ref 에서 JSON 을 읽는다. 「없다」·「못 읽었다」·「값」을 셋으로 가른다."""
    r = fixed_ref_text(ref, rel)
    if r["🔴 본문"] is None:
        return r, None
    try:
        return r, json.loads(r["🔴 본문"], object_pairs_hook=collections.OrderedDict)
    except Exception as e:                                          # noqa: BLE001
        r["🔴 JSON 이 아니다"] = str(e)[:200]
        return r, None


def before(ref, rel, fn, 이름):
    """🔴🔴 **「전」 측정의 «유일한» 꼴** --- 값과 ref 를 한 덩이로 낸다.

    `fn(txt)` 는 고정 ref 의 본문을 받아 값을 낸다. 🔴 **디스크를 볼 길이 없다.**
    """
    r = fixed_ref_text(ref, rel)
    txt = r["🔴 본문"]
    return collections.OrderedDict([
        ("🔴 이름", 이름),
        ("🔴🔴 고정 ref(= 이 값이 없으면 「전」이 아니다)", ref),
        ("🔴 경로", rel),
        ("🔴🔴🔴 값", (None if txt is None else fn(txt))),
        ("🔴 못 읽었다(= 「없다」가 아니다 · 조항 59)",
         r.get("🔴 못 읽었다(= 「없다」가 아니다 · 조항 59)", "없음")),
    ])


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 이름 붙은 범위로만 세는 소비자 계수기 (사전등록 §3-2)
# ══════════════════════════════════════════════════════════════════════
def consumer_count(이름, base, head, tree, needles=None):
    """🔴🔴🔴 **「분모 ② 역참조 소비자 수」를 «이름 붙은 범위»로만 센다**.

    🔴 **왜.** 985 는 **같은 이름**으로 `eba25b8fc..196c9e0ec`(446)와
    `91ec43686..note/985`(415)를 **둘 다** 실었다. 986 은 그 둘이 985 산출물에
    「없다」고 반박했는데 **둘 다 985 치환표 칸이었다**(티처 #125 C1).

    🔴 **고침은 「값」이 아니라 「꼴」이다** --- 이 함수는 반환값에
    **이름 · base · head · tree** 를 전부 박는다. **이름 없는 계수를 만들 수 없다.**
    """
    import lab.gitcall as GC                                        # noqa: E402
    rc, out, err = _grep_diff(base, head)
    if rc != 0:
        return collections.OrderedDict([
            ("🔴🔴 이름", 이름), ("🔴 범위", "%s..%s" % (base, head)),
            ("🔴 트리", tree),
            ("🔴 못 쟀다(= 0 이 아니다 · 조항 59)", err[:200]),
            ("🔴🔴🔴 값", None),
        ])
    changed = sorted(p for p in out.split("\0") if p)
    if needles is None:
        needles = sorted(set(_needles_for(changed)))
    files = GC.grep_files(needles, tree)
    got = files[1] if isinstance(files, tuple) else files
    if not isinstance(got, (list, tuple)):
        got = []
    got = sorted(set(got))
    return collections.OrderedDict([
        ("🔴🔴 이름", 이름),
        ("🔴🔴🔴 범위(= 이 값이 없으면 계수가 아니다)", "%s..%s" % (base, head)),
        ("🔴🔴 역참조한 트리", tree),
        ("🔴 바뀐 경로 수", len(changed)),
        ("🔴 바늘 수", len(needles)),
        ("🔴🔴🔴 값(역참조 소비자 수)", len(got)),
        ("🔴 그중 .py", len([g for g in got if g.endswith(".py")])),
    ])


def _grep_diff(base, head):
    p = subprocess.run(["git", "-c", "core.quotePath=false", "diff", "--name-only",
                        "-z", "%s..%s" % (base, head)], cwd=str(ROOT), capture_output=True)
    return (p.returncode, p.stdout.decode("utf-8", "surrogateescape"),
            p.stderr.decode("utf-8", "replace"))


def _needles_for(paths):
    out = []
    for p in paths:
        out.append(p)
        out.append(p.split("/")[-1])
        if p.endswith(".py"):
            out.append(p[:-3].replace("/", "."))
    return out


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴 여섯째 칸의 상수 + 🔴🔴🔴 일곱째 칸(사전등록 정본 값)
# ══════════════════════════════════════════════════════════════════════
SCORE_CELLS = {
    "채.반증분자모": ["§6 🔴 반증조건", "🔴🔴 분자 / 분모"],
    "채.반증분모": ["§6 🔴 반증조건", "🔴 분모"],
    "채.반증된": ["§6 🔴 반증조건", "🔴🔴 반증된 조건"],
    "채.반증통과": ["§6 🔴 반증조건", "통과"],
    "채.예측분자모": ["§5 🔴 예측", "🔴🔴 분자 / 분모"],
    "채.예측분자": ["§5 🔴 예측", "🔴 분자"],
    "채.예측통과": ["§5 🔴 예측", "통과"],
    "채.규칙D표밖": ["§D 🔴 규칙 D 감사(분모 여섯)", "🔴🔴 표 밖 합"],
    "채.규칙D분모": ["§D 🔴 규칙 D 감사(분모 여섯)", "🔴🔴 채점 분모"],
    "채.규칙D통과": ["§D 🔴 규칙 D 감사(분모 여섯)", "통과"],
    "채.한글어긋남": ["§K 🔴🔴 규칙 D — 한글 수사(987 신설)", "🔴🔴🔴 어긋난 수사 수"],
    "채.한글분모": ["§K 🔴🔴 규칙 D — 한글 수사(987 신설)", "🔴🔴 센 한글 수사 수"],
    "채.한글통과": ["§K 🔴🔴 규칙 D — 한글 수사(987 신설)", "통과"],
    "채.68근거없음": ["§68 🔴 조항 68 모양 주장 감사", "🔴🔴 근거 없는 모양 주장 수"],
    "채.68통과": ["§68 🔴 조항 68 모양 주장 감사", "통과"],
    "채.F5분모": ["§F5 🔴 인용 산출물 도장", "🔴 분모"],
    "채.F5통과": ["§F5 🔴 인용 산출물 도장", "통과"],
    "채.여섯자리": ["§9 🔴🔴 여섯 자리가 같은 수를 적나", "통과"],
    "채.최상위통과": ["통과"],
}

#: 🔴🔴🔴 **사전등록 §8 이 박은 「정본 값」** --- 채점에서 바뀌면 **반증조건 17**.
#:  🔴 **값이 아니라 「값 + 출처」다.** 여기 있는 것은 전부
#:  **이미 커밋된 남의 산출물에서 고정 ref 로 읽을 수 있는 것**뿐이다
#:  --- 이 사이클이 «새로 재는» 수는 여기 안 넣는다(986 이 저지른 형태).
PREREG_CANON = collections.OrderedDict([
    ("985 치환표 칸 소.전량", 446),
    ("985 치환표 칸 소.원장뺀", 349),
    ("985 fiveprime §1 분모 ②", 415),
    ("985 audit §C 분모 ②", 446),
    ("986 판정문의 「985 문서 수」 잰 값", 3),
    ("986 ⑤′ 절 3 대상 파일 수", 8),
    ("985 ⑤′ 절 3 대상 파일 수", 9),
])

DOC_PRODUCER = {
    "docs/판정_987.md": "runners/note987_gen.py",
    "docs/card_987.md": "runners/note987_gen.py",
    "docs/handoff_987.md": "runners/note987_gen.py",
    "docs/pr_987.md": "runners/note987_gen.py",
}

#: 🔴🔴🔴 **`[수리] R2` --- 「문서가 인용하는 산출물 전량」**(986 은 3 이었다).
DOC_INPUTS = (
    "runners/out987_score.json",
    "runners/out987_audit.json",
    "runners/out987_power.json",
    "runners/out987_house.json",
    "runners/out987_prose.json",
)

#: 🔴 **`DOC_INPUTS` 에서 «명시적으로» 뺀 것과 사유**(조용히 안 뺀다 · 조항 60).
DOC_INPUTS_EXCLUDED = collections.OrderedDict([
    ("runners/out987_certify.json",
     "🔴 `certify` 는 「표 ↔ 채점기 ↔ 디스크 문서」를 «검사»하는 자다. "
     "그 지문을 표에 박으면 문서가 자기 검사자의 지문을 싣는 «자기 참조»가 되어 "
     "이 자는 원리상 고정점에 도달 못 한다"),
    ("runners/out987_table.json",
     "🔴 치환표는 문서 «자신»이다 --- 표의 지문을 표 안에 박는 것은 정의상 불가능하다"),
])

TABLE = "runners/out987_table.json"
DOC_INPUT_KEY = "🔴🔴🔴 문서를 찍을 때 읽은 산출물 내용 지문(분모 5 · 987 R2)"

DIGEST_SKIP = ("🔴 도장", "🔴🔴 조항 66-② (987)", "🔴 987 이 읽은 산출물 sha256",
               "🔴🔴🔴 987 봉인 감사(무엇을 봉했고 무엇을 뺐나)")


def content_digest(rel):
    p = ROOT / rel
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                              # noqa: BLE001
        return None
    if isinstance(d, dict):
        d = {k: v for k, v in d.items() if k not in DIGEST_SKIP}
    return hashlib.sha256(
        json.dumps(d, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_file(rel):
    p = ROOT / rel
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


_sha_file = sha_file


def code_stamp():
    return LG.code_stamp(RAN_ALL)


def begin(ref, force=False):
    p = ROOT / WINDOW
    if p.is_file() and not force:
        return json.loads(p.read_text(encoding="utf-8"))
    d = {
        "무엇": "🔴🔴🔴 987 — **사이클 단위 측정 창**의 시작 도장",
        "🔴 사이클 시작(UTC)": now(),
        "🔴 기준 ref": ref,
        "🔴 시작 code_stamp(파일별 sha256)": code_stamp(),
    }
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return d


def cycle_start():
    p = ROOT / WINDOW
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def stale_outputs():
    rows, stale, unread = {}, [], []
    for out, prod in sorted(PRODUCER.items()):
        q = ROOT / out
        if not q.is_file():
            rows[out] = {"🔴": "🔴 산출물이 아직 없다(= 「낡지 않았다」가 아니다)"}
            continue
        try:
            d = json.loads(q.read_text(encoding="utf-8"))
        except Exception as e:                                     # noqa: BLE001
            rows[out] = {"🔴": "🔴 못 읽었다: %s" % e}
            unread.append(out)
            continue
        st = d.get(LG.STAMP_KEY) or {}
        per_r = st.get("러너별") or {}
        watch = [prod] + [x for x in SHARED if x != prod]
        cells, miss, moved = {}, [], []
        for w in watch:
            was = (per_r.get(w) or {}).get("디스크 sha256")
            cur = sha_file(w)
            if was is None:
                miss.append(w)
                continue
            cells[w] = {"낼 때 sha256": was, "지금 sha256": cur, "같은가": bool(was == cur)}
            if was != cur:
                moved.append(w)
        rows[out] = {"생산자": prod, "🔴 같이 보는 공용 배관": list(SHARED),
                     "🔴 파일별": cells,
                     "🔴 도장에 없어 못 본 것(= 「안 바뀌었다」가 아니다)": miss or "없음",
                     "🔴🔴 낼 때와 달라진 파일": moved or "없음"}
        if miss:
            unread.append(out)
        if moved:
            stale.append(out)
    return {
        "🔴🔴 무엇": "🔴 **값을 낸 뒤에 그 값을 내는 러너를 고치고 «안 다시 돌린» 산출물**",
        "🔴 분모: 생산자 표에 든 산출물": len(PRODUCER),
        "🔴 산출물별": rows,
        "🔴🔴🔴 낡은 산출물(고치고 안 다시 돌렸다)": stale or "없음",
        "🔴 못 읽은 것(= 「없다」가 아니다)": unread or "없음",
        "🔴🔴🔴 낡은 것이 있나": bool(stale),
    }


def stale_docs():
    """🔴🔴🔴 **`[수리] R2`** — 분모가 **3 → 5** 다. 뺀 둘과 사유를 같이 싣는다."""
    tp = ROOT / TABLE
    if not tp.is_file():
        return {
            "🔴🔴 무엇": "🔴 **채점기를 다시 돌리고 문서를 안 다시 찍었나**",
            "🔴": "🔴 치환표가 아직 없다 --- 「안 낡았다」가 아니라 **「모른다」**다(조항 59)",
            "🔴🔴🔴 낡은 문서가 있나": None,
        }
    try:
        tb = json.loads(tp.read_text(encoding="utf-8"))
    except Exception as e:                                          # noqa: BLE001
        return {"🔴": "🔴 치환표를 못 읽었다: %s" % e, "🔴🔴🔴 낡은 문서가 있나": None}
    was = tb.get(DOC_INPUT_KEY) or {}
    rows, moved, miss = {}, [], []
    for rel in DOC_INPUTS:
        w = was.get(rel)
        cur = content_digest(rel)
        if w is None:
            miss.append(rel)
            rows[rel] = {"🔴": "🔴 치환표가 이 입력의 내용 지문을 안 박았다(= 「같다」가 아니다)"}
            continue
        rows[rel] = {"문서를 찍을 때 내용 지문": w, "지금 내용 지문": cur,
                     "같은가": bool(w == cur)}
        if w != cur:
            moved.append(rel)
    docs = {}
    for d, prod in sorted(DOC_PRODUCER.items()):
        p = ROOT / d
        docs[d] = {"생산기": prod, "있나": p.is_file(), "지금 sha256": sha_file(d)}
    known = not miss
    return {
        "🔴🔴 무엇": ("🔴🔴🔴 **채점기를 다시 돌리고 문서(·PR 본문)를 안 다시 찍었나** --- "
                  "🔴 **`[수리] R2`: 분모가 3 → %d 다**" % len(DOC_INPUTS)),
        "🔴🔴 분모: 문서가 인용하는 산출물(986 은 3 · 987 은 %d)" % len(DOC_INPUTS):
            len(DOC_INPUTS),
        "🔴 분모의 내력(조항 60)": {"986 판": ["out986_score.json", "out986_audit.json",
                                        "out986_power.json"],
                            "987 판": list(DOC_INPUTS)},
        "🔴🔴 «명시적으로» 뺀 입력과 사유(조용히 안 뺀다)": dict(DOC_INPUTS_EXCLUDED),
        "🔴 분모: 이 표가 덮는 문서": len(DOC_PRODUCER),
        "🔴 내용 지문에서 뺀 키(조항 59·60)": list(DIGEST_SKIP),
        "🔴 입력별": rows,
        "🔴 문서별": docs,
        "🔴 치환표가 sha 를 안 박은 입력(= 「같다」가 아니다 · 조항 59)": miss or "없음",
        "🔴🔴🔴 문서를 찍은 뒤 달라진 산출물": moved or "없음",
        "🔴🔴🔴 낡은 문서가 있나": (bool(moved) if known else None),
        "🔴 이 값이 `None` 이면": "🔴 **「낡지 않았다」가 아니라 「모른다」**다(조항 59)",
    }


def clause66_2(cs0, cs1):
    keys = sorted(set(cs0) | set(cs1))
    moved_narrow = [k for k in keys if cs0.get(k) != cs1.get(k)]
    missing = [r for r in RAN_ALL if r not in cs1]
    win = cycle_start()
    csw = (win or {}).get("🔴 시작 code_stamp(파일별 sha256)") or {}
    if win is None:
        moved_wide, wide_known = None, False
    else:
        wide_known = True
        moved_wide = [k for k in sorted(set(csw) | set(cs1)) if csw.get(k) != cs1.get(k)]
    return {
        "🔴🔴 조항 66-② 신고": "🔴 **창은 「사이클 단위」다**(첫 단계 시작 ~ 지금)",
        "🔴 분모: `code_stamp` 가 덮는 파일 수": len(cs1),
        "🔴 분모: `RAN_ALL` 러너 수": len(RAN_ALL),
        "🔴🔴 분모가 못 덮은 `RAN_ALL` 항목(= 「없다」가 아니다 · 조항 59)": missing or "없음",
        "🔴 사이클 시작(UTC)": (win or {}).get("🔴 사이클 시작(UTC)")
        or "🔴 모른다 --- `out987_window.json` 이 없다(0 이 아니다)",
        "⚠ 좁은 창(이 러너의 t0~지금)에서 바뀐 파일": moved_narrow or "없음",
        "🔴🔴🔴 넓은 창(사이클 시작~지금)에서 바뀐 파일":
            (moved_wide or "없음") if wide_known else "🔴 모른다 --- 사이클 시작 도장이 없다",
        "🔴🔴🔴 측정 창 안에 러너를 고쳤나": (bool(moved_wide) if wide_known else None),
        "🔴🔴 좁은 창이 놓친 파일 수": (len(set(moved_wide or []) - set(moved_narrow))
                             if wide_known else None),
        "🔴🔴🔴 값을 낸 뒤 고치고 «안 다시 돌린» 산출물": stale_outputs(),
        "🔴🔴🔴 채점기를 다시 돌리고 «안 다시 찍은» 문서(분모 5 · R2)": stale_docs(),
        "🔴 시작 요약(좁은 창)": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "🔴 시작 요약(넓은 창)": hashlib.sha256(
            json.dumps(csw, sort_keys=True).encode()).hexdigest() if wide_known
        else "🔴 모른다",
        "🔴 끝 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
    }


def feeds_in():
    return {p: sha_file(p) for p in FEEDS_IN}


def seal_sections(obj, skip=SEAL_SKIP_DEFAULT):
    sealed, skipped, already = [], [], []
    for k, v in list(obj.items()):
        if not isinstance(v, dict):
            continue
        if k in skip:
            skipped.append(k)
            continue
        if "sha256" in k or "시각" in k:
            skipped.append(k)
            continue
        if "통과" in v:
            already.append(k)
            continue
        if "🔴 F5 통과" in v:
            v["통과"] = bool(v["🔴 F5 통과"])
            v["🔴 이 절의 `통과`"] = "도장의 `🔴 F5 통과` 그 값이다(리터럴이 아니다)"
        elif "🔴🔴🔴 측정 창 안에 러너를 고쳤나" in v:
            _miss = [k2 for k2 in v if k2.startswith("🔴🔴 분모가 못 덮은")]
            _known = v["🔴🔴🔴 측정 창 안에 러너를 고쳤나"] is not None
            _stale = (v.get("🔴🔴🔴 값을 낸 뒤 고치고 «안 다시 돌린» 산출물")
                      or {}).get("🔴🔴🔴 낡은 것이 있나")
            _sdoc = (v.get("🔴🔴🔴 채점기를 다시 돌리고 «안 다시 찍은» 문서(분모 5 · R2)")
                     or {}).get("🔴🔴🔴 낡은 문서가 있나")
            v["통과"] = bool(_known and _stale is False and _sdoc is False
                            and _miss and v[_miss[0]] == "없음")
            v["🔴 이 절의 `통과`"] = (
                "🔴🔴 **조건 넷**: ① 사이클 시작 도장을 읽었다 · ② 낡은 산출물 0 · "
                "③ **낡은 문서 0**(분모 5) · ④ 분모가 `RAN_ALL` 을 전부 덮었다. "
                "🔴 ③ 이 `None`(모른다)이면 «통과가 아니다»(조항 59)")
        else:
            v["통과"] = False
            v["🔴 이 절의 `통과`"] = (
                "🔴 **이 절은 `통과` 를 안 만들었다 --- 「모른다」다**(조항 59). `False` 로 센다")
        sealed.append(k)
    return {
        "🔴🔴🔴 987 봉인 감사": "🔴 봉인 대상은 «절 명부»이고 제외 키를 산출물에 싣는다",
        "🔴 봉인한 절": sealed or "없음",
        "🔴 이미 `통과` 가 있어 안 건드린 절": already or "없음",
        "🔴🔴 봉인에서 «명시적으로» 뺀 키(= 절이 아니라 자료다)": skipped or "없음",
        "🔴 제외 목록(인자로 받은 것)": list(skip),
    }


def write(path, obj, ref, cs0, t0, seal_skip=SEAL_SKIP_DEFAULT):
    cs1 = code_stamp()
    obj["🔴🔴 조항 66-② (987)"] = clause66_2(cs0, cs1)
    obj["🔴 987 이 읽은 산출물 sha256"] = feeds_in()
    LG.write_stamped(str(ROOT / path), obj, ref, cs0, t0, RAN_ALL, DATA)
    raw = json.loads((ROOT / path).read_text(encoding="utf-8"),
                     object_pairs_hook=collections.OrderedDict)
    audit = seal_sections(raw, seal_skip)
    KEY = "🔴🔴🔴 987 봉인 감사(무엇을 봉했고 무엇을 뺐나)"
    raw[KEY] = audit
    left = [k for k, v in raw.items()
            if isinstance(v, dict) and "통과" not in v and k != KEY
            and k not in seal_skip and not any(w in k for w in ("sha256", "시각"))]
    audit["🔴🔴 봉인 뒤에도 `통과` 가 없는 절"] = left or "없음"
    audit["통과"] = bool(not left)
    audit["🔴 이 절의 `통과`"] = (
        "🔴 **봉인 뒤에 `통과` 키가 없는 최상위 절이 0 인가** --- 이 자는 떨어질 수 있다")
    (ROOT / path).write_text(
        json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return raw


def resolve(obj, path):
    cur = obj
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return False, None
        cur = cur[k]
    return True, cur


def stamp_window(ref):
    p = ROOT / WINDOW
    if not p.is_file():
        return {"🔴": "🔴 창 파일이 없다"}
    d = json.loads(p.read_text(encoding="utf-8"),
                   object_pairs_hook=collections.OrderedDict)
    t0 = d.get("🔴 사이클 시작(UTC)") or now()
    cs0 = d.get("🔴 시작 code_stamp(파일별 sha256)") or code_stamp()
    d["⚠ 이 도장은 «사이클 끝»에 얹었다(987)"] = (
        "🔴 시작 시각과 시작 `code_stamp` 은 한 바이트도 «안» 바꿨다 --- "
        "반증조건 13 의 분모(원장이 싣는 산출물 전량)를 «면제 없이» 채우기 위해서다")
    LG.write_stamped(str(p), d, ref, cs0, t0, RAN_ALL, DATA)
    raw = json.loads(p.read_text(encoding="utf-8"),
                     object_pairs_hook=collections.OrderedDict)
    audit = seal_sections(raw, SEAL_SKIP_DEFAULT)
    KEY = "🔴🔴🔴 987 봉인 감사(무엇을 봉했고 무엇을 뺐나)"
    raw[KEY] = audit
    left = [k for k, v in raw.items()
            if isinstance(v, dict) and "통과" not in v and k != KEY
            and not any(w in k for w in ("sha256", "시각"))]
    audit["🔴🔴 봉인 뒤에도 `통과` 가 없는 절"] = left or "없음"
    audit["통과"] = bool(not left)
    audit["🔴 이 절의 `통과`"] = "봉인 뒤에 `통과` 키가 없는 최상위 절이 0 인가"
    p.write_text(json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"창": WINDOW, "도장": "얹었다", "봉인 뒤 `통과` 없는 절": left or "없음"}


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--stamp":
        print(json.dumps(stamp_window(sys.argv[2]), ensure_ascii=False))
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--begin":
        print(json.dumps(begin(sys.argv[2], force=("--force" in sys.argv)),
                         ensure_ascii=False)[:400])
        sys.exit(0)
    cs = code_stamp()
    print(json.dumps({
        "RAN_ALL": len(RAN_ALL),
        "RAN_987": len(RAN_987),
        "SCORE_CELLS": len(SCORE_CELLS),
        "PREREG_CANON": len(PREREG_CANON),
        "DOC_INPUTS": len(DOC_INPUTS),
        "code_stamp 분모": len(cs),
        "못 덮은 항목": [r for r in RAN_ALL if r not in cs],
    }, ensure_ascii=False))
