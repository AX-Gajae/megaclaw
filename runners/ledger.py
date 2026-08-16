#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴🔴 **공유 채점기** — 976 수리 1~4.

## 왜 이 파일이 생겼나

`runners/ledger892.py … ledger975.py` 가 **21 벌**이었다. 채점기 수리가 **일회용 파일에
살아서 대물림이 안 됐다**(티처 #114 3순위: 공유 코드 착지 3/5). 976 이 하나로 합친다.
🔴 **976 은 `ledger976.py` 를 만들지 않는다.**

## 976 이 고친 것

- **수리 2** 🔴🔴 **슬롯 검사가 문서 본문을 읽는다.**
  975 판은 `render(resolve(키경로)) == 매니페스트["값"]` 을 견줬는데, 매니페스트의 `값` 이
  **같은 `resolve` 로 써 넣어진 것**이라 **항진명제**였다 — 문서 본문의 그 자리를
  **한 번도 안 읽었다**. 티처 #114 가 심으니 **975 판이 셋 다 못 잡고 974 판이 둘을 잡았다**.
  976 판: `본문[시작:끝) == render(resolve(키경로))`.
- **수리 3** 🔴 **양성 대조를 진짜로 심는다**(`plant_control`). 세 무리 A(슬롯 안)·
  B(슬롯 밖)·C(면제 자리)를 문서 **사본**에 심고 채점기 셋을 나란히 건다.
- **수리 4** 🔴 **`ALLOW_CTX` 를 줄인다** — **맨-9xx 규칙을 지웠다.** 그 규칙이
  수리 2 의 헤드라인 자신(「1,000 중 901」)을 조용히 면제했다. 구판을 `ALLOW_CTX_975`
  로 남겨 전후를 나란히 싣는다(조항 66-③).

씀:
    python3 runners/ledger.py --stage f5       --ref <40자 sha> --cycle 976
    python3 runners/ledger.py --stage numaudit --ref <40자 sha> --cycle 976
    python3 runners/ledger.py --stage control  --ref <40자 sha> --cycle 976
"""
import argparse
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import runners.predict971 as P                    # noqa: E402

OUT = ROOT / "runners"
NUMPAT = re.compile(r"-?\d[\d,]*(?:\.\d+)?")

#: 🔴🔴 **978 수리 4 — 한글 수사(數詞)를 채점 대상에 넣는다.**
#: 977 의 「본문 **넷** 0 / 370」이 **판정문·카드·원장 셋을 그대로 통과**했다.
#: 실제 `numaudit` 분모는 **다섯**(194+71+51+25+29 = 370)이었다. `NUMPAT` 은 아라비아
#: 숫자만 보므로 **한글로 적은 수는 원리상 안 세었다** — 규칙 D 의 구멍이다.
#: 🔴 낱말 목록을 여기 **등록해 두고 산출물이 그대로 싣는다**(분모를 숨기지 않는다).
KOR_NUM = collections.OrderedDict([
    ("하나", 1), ("둘", 2), ("셋", 3), ("넷", 4), ("다섯", 5), ("여섯", 6),
    ("일곱", 7), ("여덟", 8), ("아홉", 9), ("열", 10), ("스물", 20),
])
#: 🔴 `둘러`·`열쇠`·`열린` 처럼 수사가 아닌 자리를 뺀다. **뺀 규칙을 적는다.**
KNUM_NOT = re.compile(r"둘(?=러|레|리|russ)|열(?=쇠|린|리|어|고|다|자|중|한|은|을|린)")
KNUMPAT = re.compile(
    r"(?<![가-힣])(하나|둘|셋|넷|다섯|여섯|일곱|여덟|아홉|열|스물)")

# ══════════════════════════════════════════════════════════════════════
# 🔴🔴 **981 수리 R4 — 규칙 D 가 「한자어 자릿수 수사」를 원리상 못 봤다.**
#
# 980 논문의 **제목**이 「**천이백만** 배를 버리는 관」이고 초록이 「디스크의
# **이천이백만** 행」인데, 그 두 양은 **어느 산출물에도 없다**(디스크는 38,866,835 행 ·
# 「몇 행 중 1 행」은 22,729.1). 🔴 **규칙 D 는 소수 넷째 자리 이상의 «아라비아 숫자»만
# 보고, `audit_korean` 은 하나~스물의 «고유어 수사»만 봤다.** 그 사이에
# **자릿수 한자어 수사(만·억·조)** 가 통째로 비어 있었다.
#
# 🔴 오검을 줄이는 세 조건(전부 산출물에 적는다):
#   ① 첫 덩이가 **두 글자 이상**이어야 한다(「이 조」·「만 이」 같은 산문 조각을 뺀다)
#   ② **자릿수 글자(백·천·만·억·조)를 하나라도** 담아야 한다
#   ③ 🔴 뒤에 **등록된 셈낱말**이 와야 한다(「천이백만 **배**」·「이만 이천칠백여 **행**」)
# ══════════════════════════════════════════════════════════════════════
KMAG_DIG = collections.OrderedDict([
    ("영", 0), ("일", 1), ("이", 2), ("삼", 3), ("사", 4), ("오", 5),
    ("육", 6), ("륙", 6), ("칠", 7), ("팔", 8), ("구", 9)])
KMAG_UNIT = collections.OrderedDict([("십", 10), ("백", 100), ("천", 1000)])
KMAG_BIG = collections.OrderedDict([("만", 10 ** 4), ("억", 10 ** 8), ("조", 10 ** 12)])
KMAG_SET = "".join(list(KMAG_DIG) + list(KMAG_UNIT) + list(KMAG_BIG))
#: 🔴 등록된 셈낱말 — 이 목록 밖에서는 안 센다(안 세는 자리를 숨기지 않는다)
KMAG_CNT = ("배|행|개|건|명|원|번|쪽|자리|칸|줄|문서|삼중쌍|년|달|일|시간|회|편|"
            "가지|도메인|사이클|벌|복제|씨앗|샤드|shard")
KMAGPAT = re.compile(
    r"(?<![가-힣])([%s]{2,}(?:\s[%s]+)*)(?:여|남짓)?\s*(?=(?:%s))"
    % (KMAG_SET, KMAG_SET, KMAG_CNT))
#: 🔴 수사가 아닌 자리 — **뺀 규칙과 뺀 수를 적는다**(조항 59)
KMAG_NOT = re.compile(r"^(?:구조|조사|조작|조절|조건|조항|조금|조차|만일|만약|만족|"
                      r"천천|만만|십중팔구)$")


def kmag_value(tok):
    """🔴 한자어 자릿수 수사를 정수로 읽는다. 「천이백만」 → 12000000."""
    s = tok.replace(" ", "")
    tot = sec = cur = 0
    for ch in s:
        if ch in KMAG_DIG:
            cur = KMAG_DIG[ch]
        elif ch in KMAG_UNIT:
            sec += (cur if cur else 1) * KMAG_UNIT[ch]
            cur = 0
        elif ch in KMAG_BIG:
            sec += cur
            cur = 0
            tot += (sec if sec else 1) * KMAG_BIG[ch]
            sec = 0
    return tot + sec + cur


def audit_korean_magnitude(src, S, tol=0.005):
    """🔴🔴 **981 수리 R4** — 본문의 한자어 자릿수 수사를 **치환표와 대조한다**.

    `S` = 치환표(또는 산출물)에서 온 **허용된 수의 집합**(문자열).
    수사 하나마다 `S` 안의 가장 가까운 수를 찾아 **상대오차**를 적는다.
    🔴 상대오차가 `tol`(기본 0.5%) 안이면 「반올림한 인용」으로 통과, 밖이면 **어긋남**이다.
    🔴 **분모가 0 이면 실패다** — 「안 세었다」와 「없다」는 둘이다(조항 59).
    """
    nums = []
    for v in S:
        try:
            nums.append(float(str(v).replace(",", "")))
        except (TypeError, ValueError):
            continue
    code = [(m.start(), m.end()) for m in re.finditer(r"`[^`\n]*`", src)]
    hits, bad, exempt, notnum = [], [], 0, 0
    for m in KMAGPAT.finditer(src):
        tok = m.group(1)
        if not any(c in tok for c in "백천만억조"):
            continue
        if KMAG_NOT.match(tok.replace(" ", "")):
            notnum += 1
            continue
        if any(a <= m.start() and m.end() <= b for a, b in code):
            exempt += 1
            continue
        val = kmag_value(tok)
        near, rel = None, None
        for x in nums:
            if x == 0:
                continue
            r = abs(val - x) / abs(x)
            if rel is None or r < rel:
                near, rel = x, r
        row = {"수사": tok, "값": val, "가장 가까운 치환표 값": near,
               "상대오차": (None if rel is None else round(rel, 6)),
               "맞나": bool(rel is not None and rel <= tol),
               "맥락": re.sub(r"\s+", " ", src[max(0, m.start() - 25):m.end() + 25])}
        hits.append(row)
        if not row["맞나"]:
            bad.append(row)
    return {
        "🔴 무엇": "🔴🔴 981 수리 R4 — 한자어 자릿수 수사(만·억·조)를 치환표와 대조한다",
        "🔴 등록한 셈낱말": KMAG_CNT,
        "🔴 뺀 규칙(수사가 아닌 자리)": KMAG_NOT.pattern,
        "🔴 허용 상대오차(반올림 인용)": tol,
        "🔴 대조한 치환표 수의 개수": len(nums),
        "🔴 센 한자어 수사": len(hits),
        "🔴 면제한 수사(인라인 코드 안)": exempt,
        "🔴 수사가 아니라고 뺀 것": notnum,
        "🔴🔴🔴 치환표에 없는 수사": len(bad),
        "🔴 어긋난 자리": bad[:20],
        "수사별": collections.Counter([h["수사"] for h in hits]),
        "통과": bool(len(bad) == 0),
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "본문의 한자어 자릿수 수사가 **전부 치환표의 어떤 수의 반올림**이다. "
            "🔴 980 의 「천이백만 배」는 이 검사에서 떨어진다"),
    }

#: 🔴🔴 **977 수리 4** — 규칙 C 는 도장에 **자료 지문**을 요구한다. 976 은 이 파일의
#: 네 stage 에서 `stamp_block(..., data=…)` 를 안 채워 **산출물 8 중 5 의 자료 지문이 0**
#: 이었다. 여기 한 자리에 두고 넷이 같이 쓴다.
DATA = collections.OrderedDict([
    ("sao941", "data/ingest/sao941/pairs.jsonl.gz"),
    ("sao959", "data/ingest/sao959/pairs.jsonl.gz"),
    ("hplt_ko", "data/ingest/sao973_hplt/pairs.jsonl.gz"),
])

#: 🔴 **975 판 면제 규칙** — 대조용으로 남긴다(조항 66-③: 자를 고치면 전후를 같이 싣는다).
ALLOW_CTX_975 = (
    ("노트 번호·사이클 번호", re.compile(r"(?:노트|티처 #|사이클|PR #|#)\s*\d+")),
    ("연도·날짜·시각", re.compile(r"\d{4}-\d{2}-\d{2}|\d{4}년|\d{2}:\d{2}")),
    ("절 번호", re.compile(r"§\s*\d+(?:\.\d+)?|v\d+\.\d+")),
    ("사전등록 딱지", re.compile(r"[PAHWVDERC]\d+")),
    ("🔴 975 신설: 사이클 번호(9xx)", re.compile(r"(?<![\d.,])9[0-9]{2}(?![\d.,])")),
    ("🔴 975 신설: 신뢰수준", re.compile(r"95\s*\\?%")),
    ("🔴 975 신설: 목록·표의 차례 번호",
     re.compile(r"(?m)^\s*\d+\.\s|\|\s*\d+\s*\||^\s*\d+\s*&")),
    ("🔴 975 신설: 순위 낱말", re.compile(r"\d+\s*(?:순위|위)")),
    ("🔴 975 신설: 수리·문항 번호",
     re.compile(r"(?:수리|예측|반증조건)\s*\d+|[PAHWVDERCF]\d+|A-\d")),
    ("🔴 975 신설: 인라인 코드(글자가 든 것만)",
     re.compile(r"`[^`\n]*[A-Za-z가-힣][^`\n]*`")),
)

#: 🔴🔴 **976 판 면제 규칙 (수리 4)** — 🔴 **맨-9xx 규칙을 지웠다.**
#: 그 규칙은 `(?<![\d.,])9[0-9]{2}(?![\d.,])` 로 **900~999 를 통째로** 면제해서
#: 수리 2 의 헤드라인 자신(「1,000 중 **901**」)을 안 셌다.
#: 🔴 **사이클 번호는 「노트 976」·「티처 #114」 처럼 낱말이 붙은 꼴로만 면제한다.**
ALLOW_CTX = (
    ("노트 번호·사이클 번호(낱말이 붙은 것만)",
     re.compile(r"(?:노트|티처 #|사이클|PR #|#)\s*\d+")),
    ("연도·날짜·시각", re.compile(r"\d{4}-\d{2}-\d{2}|\d{4}년|\d{2}:\d{2}")),
    ("절 번호", re.compile(r"§\s*\d+(?:\.\d+)?|v\d+\.\d+")),
    ("🔴 976 축소: 사전등록 딱지(등록된 접두어만)",
     re.compile(r"(?<![0-9A-Za-z])(?:P|W|E|C|R|F|V|D|H)\d{1,2}(?![0-9])")),
    ("신뢰수준", re.compile(r"95\s*\\?%")),
    ("목록·표의 차례 번호",
     re.compile(r"(?m)^\s*\d+\.\s|\|\s*\d+\s*\||^\s*\d+\s*&")),
    ("순위 낱말", re.compile(r"\d+\s*(?:순위|위)")),
    ("수리·문항 번호", re.compile(r"(?:수리|정정|예측|반증조건)\s*\d+|A-\d")),
    ("인라인 코드(글자가 든 것만)",
     re.compile(r"`[^`\n]*[A-Za-z가-힣][^`\n]*`")),
)


# ══════════════════════════════════════════════════════════════════════
# 도장 (규칙 C)
# ══════════════════════════════════════════════════════════════════════
def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_stamp(ran) -> dict:
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in ran]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def stamp_block(ref, cs0, cs1, t0, ran, data=None) -> dict:
    """🔴 시작·끝 두 번 + 돌린 러너 전부 + 고정 40자 ref + 자료 지문."""
    ds = {k: P._sha_file(str(ROOT / v)) for k, v in (data or {}).items()}
    runner, ok = {}, 0
    for r in ran:
        disk = P._sha_file(str(ROOT / r))
        try:
            cm = hashlib.sha256(subprocess.check_output(
                ["git", "show", "%s:%s" % (ref, r)], cwd=str(ROOT))).hexdigest()
        except Exception:                                          # noqa: BLE001
            cm = None
        runner[r] = {"디스크 sha256": disk, "커밋 blob sha256": cm, "일치": disk == cm}
        ok += 1 if disk == cm else 0
    return {
        "언제(시작)": t0, "언제(끝)": now(),
        "시작 code_stamp 요약": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "끝 code_stamp 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
        "🔴 시작=끝": cs0 == cs1,
        "분모: 도장이 덮는 파일": len(cs1),
        "🔴 자료 지문": ds, "분모: 연 자료 파일": len(ds),
        "🔴 F1 기준 ref(준 대로)": ref,
        "🔴 40자 고정 sha 인가": bool(re.fullmatch(r"[0-9a-f]{40}", ref or "")),
        "🔴 기준 ref 가 0000…0000 인가": bool(re.fullmatch(r"0{40}", ref or "")),
        "러너별": runner, "🔴 분자/분모": "%d / %d" % (ok, len(ran)),
        "🔴 F5 통과": ok == len(ran) and bool(re.fullmatch(r"[0-9a-f]{40}", ref or ""))
        and not re.fullmatch(r"0{40}", ref or ""),
    }


#: 🔴🔴🔴 **982 수리 R2** — 도장 «없이» 산출물을 못 쓰게 한다 (조항 66 · 티처 #120 M8).
STAMP_KEY = "🔴 도장"


def write_stamped(path, obj, ref, cs0, t0, ran, data=None, key=STAMP_KEY):
    """🔴🔴 산출물을 **도장과 «같이»** 쓴다 — 도장 없이 쓰는 길을 없앤다.

    🔴 **왜 생겼나.** 981 의 치환표(`out981_table.json`)와 산문 대조(`out981_prose.json`)에
    **도장이 없었다**(티처 #120 M8). 🔴 **「모든 수의 유일한 출처」인 파일이 자기 출처를
    못 댔다** — 조항 66 이 금지하는 바로 그 꼴이다. 뿌리는 「도장을 «따로» 붙여야 한다」는
    데 있었고, 붙이는 것을 잊으면 아무도 안 물었다.

    🔴 그래서 **쓰기를 도장에 묶는다.** 이 함수 말고 다른 길로 쓰면 규칙 C 위반이고,
    `ref` 가 40자 고정 sha 가 아니면 **여기서 터진다**(fail-closed).

    돌려주는 값: 실제로 박힌 도장 블록(호출자가 판정에 쓸 수 있다).
    """
    if not re.fullmatch(r"[0-9a-f]{40}", str(ref or "")):
        raise SystemExit(
            "🔴 규칙 C — `%s` 를 쓰려는데 기준 ref 가 40자 고정 sha 가 아니다: %r" %
            (path, ref))
    st = stamp_block(ref, cs0, code_stamp(ran), t0, ran, data)
    if isinstance(obj, collections.OrderedDict) or isinstance(obj, dict):
        obj[key] = st
    else:                                                          # noqa: RET506
        raise SystemExit("🔴 `write_stamped` 는 dict 만 쓴다: %r" % type(obj))
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    return st


# ══════════════════════════════════════════════════════════════════════
# 산출물 값 읽기 / 그리기
# ══════════════════════════════════════════════════════════════════════
def _norm(x: str) -> str:
    x = x.replace(",", "")
    if "." in x:
        x = x.rstrip("0").rstrip(".")
    return x or "0"


def artifact_numbers(glob_pat) -> set:
    """🔴 **974 판 채점기** — 산출물 어딘가에 나오는 수의 집합. 나란히 세우려고 남긴다."""
    S = set()

    def add(v):
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            s = ("%r" % v) if isinstance(v, float) else str(v)
            S.add(_norm(s))
            if isinstance(v, float):
                for k in range(0, 7):
                    S.add(_norm("%.*f" % (k, v)))
                S.add(_norm("%.1f" % (100.0 * v)))
                S.add(_norm("%.2f" % (100.0 * v)))
                S.add(_norm("%.4f" % (100.0 * v)))
        elif isinstance(v, str):
            for m in NUMPAT.findall(v):
                S.add(_norm(m))
        elif isinstance(v, dict):
            for k, x in v.items():
                add(k)
                add(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                add(x)

    for p in sorted(glob.glob(str(OUT / glob_pat))):
        try:
            add(json.loads(Path(p).read_text(encoding="utf-8")))
        except Exception:                                          # noqa: BLE001
            pass
    return S


def resolve(path):
    """`[파일, 키, 키, …]` 를 산출물에서 실제로 따라간다."""
    if not path:
        return None, "빈 경로"
    f = OUT / path[0]
    if not f.is_file():
        return None, "산출물이 없다: %s" % path[0]
    cur = json.loads(f.read_text(encoding="utf-8"))
    for k in path[1:]:
        if isinstance(cur, dict):
            if k not in cur:
                return None, "키가 없다: %s" % k
            cur = cur[k]
        elif isinstance(cur, list):
            try:
                cur = cur[int(k)]
            except Exception:                                      # noqa: BLE001
                return None, "자리가 없다: %s" % k
        else:
            return None, "더 못 들어간다: %s" % k
    return cur, None


def render(v):
    """산출물 값 하나를 **본문에 실을 문자열**로. 여기 말고 다른 데서 안 만든다."""
    if isinstance(v, bool):
        return "참" if v else "거짓"
    if isinstance(v, float):
        return ("%.6f" % v).rstrip("0").rstrip(".") if abs(v) < 1e15 else repr(v)
    if isinstance(v, int):
        return "{:,}".format(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(render(x) for x in v) + "]"
    return str(v)


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴 수리 2 — **본문을 읽는** 슬롯 검사
# ══════════════════════════════════════════════════════════════════════
def allow_spans(src, rules=ALLOW_CTX):
    spans, why = [], collections.Counter()
    for name, pat in rules:
        for m in pat.finditer(src):
            spans.append((m.start(), m.end()))
            why[name] += 1
    return spans, why


def audit_text(src, slots, S, rules=ALLOW_CTX):
    """🔴 **본문 `src` 를 실제로 읽어** 수마다 출처를 묻는다.

    반환 키:
      `슬롯` — 슬롯별 `{본문, 키경로값, 일치}` (🔴 **`본문` 은 `src[시작:끝)` 이다**)
      `976 판이 못 찾는 수` — 슬롯 밖이거나, 슬롯 본문이 키 경로 값과 다른 수
      `974 판이 못 찾는 수` — 산출물 값 집합 `S` 에 없는 수
    """
    spans = []
    for sl in slots:
        val, err = resolve(sl["키 경로"])
        want = render(val) if err is None else None
        body = src[sl["시작"]:sl["끝"]]          # 🔴🔴 **여기가 수리 2 다**
        spans.append({"시작": sl["시작"], "끝": sl["끝"],
                      "키 경로": sl["키 경로"],
                      "본문": body, "키 경로 값": want,
                      "일치": bool(want is not None and body == want)})
    allow, why = allow_spans(src, rules)
    counted = exempt = 0
    miss_old, miss_new = [], []
    for m in NUMPAT.finditer(src):
        if any(a <= m.start() and m.end() <= b for a, b in allow):
            exempt += 1
            continue
        counted += 1
        ctx = re.sub(r"\s+", " ", src[max(0, m.start() - 40):m.end() + 40])
        if _norm(m.group()) not in S:
            miss_old.append({"수": m.group(), "맥락": ctx})
        cov = [sp for sp in spans if sp["시작"] <= m.start() and m.end() <= sp["끝"]]
        if not cov:
            miss_new.append({"수": m.group(), "왜": "슬롯 밖(손으로 적은 수)",
                             "자리": m.start(), "맥락": ctx})
        elif not cov[0]["일치"]:
            miss_new.append({"수": m.group(),
                             "왜": "슬롯 본문이 키 경로 값과 다르다",
                             "자리": m.start(),
                             "본문": cov[0]["본문"], "키 경로 값": cov[0]["키 경로 값"],
                             "맥락": ctx})
    return {"슬롯": spans, "센 수": counted, "면제된 수": exempt,
            "면제 사유별": dict(why),
            "🔴 키 경로와 본문이 다른 슬롯": sum(1 for sp in spans if not sp["일치"]),
            "🔴 974 판이 못 찾는 수": miss_old,
            "🔴🔴 976 판이 못 찾는 수": miss_new}


def audit_korean(src, counts):
    """🔴🔴 **978 수리 4** — 본문의 **한글 수사**를 세고, 등록된 셈과 대조한다.

    `counts` = `{앞말: 참값}` (예: `{"본문": 5, "산출물": 9}`). 앞말 바로 뒤에 오는
    수사는 **그 참값과 같아야 한다.**

    🔴 977 이 걸린 자리가 정확히 이것이다 — 「본문 **넷**」인데 참값은 **다섯**이었고,
    `NUMPAT` 이 아라비아 숫자만 봐서 **세 문서가 그대로 통과했다.**
    """
    #: 🔴 **인라인 코드 안은 안 센다** — 976 의 `ALLOW_CTX` 가 아라비아 숫자에 준 것과
    #: 같은 면제다. 🔴 **정정 문장이 「틀린 수」를 인용해야 할 때 쓰는 자리이고,
    #: 면제한 자리 수를 산출물에 적는다**(안 세는 자리를 숨기지 않는다).
    code = [(m.start(), m.end()) for m in re.finditer(r"`[^`\n]*`", src)]
    hits, bad, exempt = [], [], 0
    for m in KNUMPAT.finditer(src):
        if KNUM_NOT.match(src, m.start()):
            continue
        if any(a <= m.start() and m.end() <= b for a, b in code):
            exempt += 1
            continue
        word = m.group()
        ctx = re.sub(r"\s+", " ", src[max(0, m.start() - 30):m.end() + 20])
        row = {"수사": word, "값": KOR_NUM[word], "자리": m.start(), "맥락": ctx}
        hits.append(row)
        head = src[max(0, m.start() - 12):m.start()]
        for name, want in counts.items():
            if re.search(re.escape(name) + r"(?:의)?\s*$", head):
                row["앞말"] = name
                row["등록된 참값"] = want
                row["맞나"] = bool(KOR_NUM[word] == want)
                if not row["맞나"]:
                    bad.append(row)
    tied = [h for h in hits if "앞말" in h]
    return {
        "🔴 등록한 수사 낱말": dict(KOR_NUM),
        "🔴 뺀 규칙(수사가 아닌 자리)": KNUM_NOT.pattern,
        "🔴 대조한 앞말과 참값": dict(counts),
        "🔴 센 한글 수사": len(hits),
        "🔴 면제한 수사(인라인 코드 안)": exempt,
        "🔴 앞말이 걸린 수사": len(tied),
        "🔴🔴 등록된 참값과 다른 수사": len(bad),
        "🔴 어긋난 자리": bad[:20],
        "수사별": collections.Counter([h["수사"] for h in hits]),
        "통과": bool(len(bad) == 0 and len(hits) > 0),
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "본문의 한글 수사가 **하나도 등록된 셈과 안 어긋난다**. "
            "🔴 분모가 0 이면 실패다 — 「안 세었다」와 「없다」는 둘이다"),
    }


def audit_975(src, slots, S, rules=ALLOW_CTX_975):
    """🔴 **975 판 그대로** — 슬롯 판정이 `render(resolve(키경로)) == 매니페스트["값"]`.

    🔴 **본문을 한 번도 안 읽는다.** 항진명제임을 보이려고 남긴다.
    """
    spans = []
    for sl in slots:
        val, err = resolve(sl["키 경로"])
        ok = (err is None and render(val) == sl["값"])      # 🔴 txt == txt
        spans.append((sl["시작"], sl["끝"], ok))
    allow, _ = allow_spans(src, rules)
    counted, miss = 0, []
    for m in NUMPAT.finditer(src):
        if any(a <= m.start() and m.end() <= b for a, b in allow):
            continue
        counted += 1
        cov = [sp for sp in spans if sp[0] <= m.start() and m.end() <= sp[1]]
        if not cov or not cov[0][2]:
            miss.append({"수": m.group(), "자리": m.start()})
    return {"센 수": counted, "🔴 975 판이 못 찾는 수": miss}


# ══════════════════════════════════════════════════════════════════════
# 🔴 수리 3 — **양성 대조를 진짜로 심는다**
# ══════════════════════════════════════════════════════════════════════
_BUMP = re.compile(r"\d")


def _bump_last_digit(txt):
    """마지막 숫자 문자를 `(d+1) mod 10` 으로. 🔴 **글자 수가 안 변한다.**"""
    pos = [m.start() for m in _BUMP.finditer(txt)]
    if not pos:
        return None
    i = pos[-1]
    return txt[:i] + str((int(txt[i]) + 1) % 10) + txt[i + 1:]


def plant_control(src, slots, S, n_a=3, n_b=6, n_c=6, seed=976):
    """🔴 문서 **사본**에 셋을 심고 채점기 셋을 나란히 건다.

    - **무리 A** 슬롯 **안**의 수를 바꾼다(길이 보존) → 🔴 976 판이 전부 잡아야 한다.
    - **무리 B** 문서 **끝에** 새 수를 끼워 넣는다(슬롯 오프셋을 안 흔든다)
      → 🔴 976 판이 전부 잡아야 한다.
    - **무리 C** `ALLOW_CTX` 가 **면제하는 자리**의 수를 바꾼다(길이 보존)
      → 🔴 **0 개를 잡는 것이 정상**이고, 그것이 **선언된 사각지대**다.
    """
    allow, _ = allow_spans(src, ALLOW_CTX)

    def in_allow(a, b):
        return any(x <= a and b <= y for x, y in allow)

    # ── 무리 A ────────────────────────────────────────────────
    cand = [(i, sl) for i, sl in enumerate(slots)
            if _BUMP.search(src[sl["시작"]:sl["끝"]])
            and not in_allow(sl["시작"], sl["끝"])]
    picks = []
    if cand:
        idx = sorted({0, len(cand) // 2, len(cand) - 1})
        picks = [cand[i] for i in idx][:n_a]
    a_src = src
    a_planted = []
    for _i, sl in picks:
        body = a_src[sl["시작"]:sl["끝"]]
        new = _bump_last_digit(body)
        if new is None or new == body:
            continue
        a_src = a_src[:sl["시작"]] + new + a_src[sl["끝"]:]
        a_planted.append({"무리": "A(슬롯 안)", "자리": sl["시작"],
                          "원래": body, "심은 것": new, "키 경로": sl["키 경로"]})

    # ── 무리 B ────────────────────────────────────────────────
    b_src = a_src
    b_planted = []
    tail = ["8675309", "4815162", "9128374", "6203945", "7391026", "5847213"]
    head = "\n대조 삽입 값은 "
    for j in range(min(n_b, len(tail))):
        add = head + tail[j] + " 이다\n"
        b_planted.append({"무리": "B(슬롯 밖)", "자리": len(b_src) + len(head),
                          "원래": "", "심은 것": tail[j]})
        b_src = b_src + add

    # ── 무리 C ────────────────────────────────────────────────
    c_src = b_src
    c_planted = []
    stable = re.compile(r"\d{4}-\d{2}-\d{2}|(?:노트|티처 #|사이클|PR #)\s*\d+"
                        r"|§\s*\d+(?:\.\d+)?")
    hits = []
    for m in stable.finditer(c_src):
        if any(sl["시작"] <= m.start() and m.end() <= sl["끝"] for sl in slots):
            continue
        hits.append(m.span())
    step = max(1, len(hits) // max(1, n_c))
    for a, b in hits[::step][:n_c]:
        body = c_src[a:b]
        new = _bump_last_digit(body)
        if new is None or new == body:
            continue
        c_src = c_src[:a] + new + c_src[b:]
        c_planted.append({"무리": "C(면제 자리)", "자리": a,
                          "원래": body, "심은 것": new})

    planted = a_planted + b_planted + c_planted

    def caught(res_new, res_old, res_975):
        """심은 자리마다 세 채점기가 잡았는지."""
        pos_new = {d.get("자리") for d in res_new["🔴🔴 976 판이 못 찾는 수"]}
        num_old = collections.Counter(_norm(d["수"])
                                      for d in res_old["🔴 974 판이 못 찾는 수"])
        pos_975 = {d["자리"] for d in res_975["🔴 975 판이 못 찾는 수"]}
        rows = []
        for pl in planted:
            lo, hi = pl["자리"], pl["자리"] + max(1, len(pl["심은 것"]))
            hit_new = any(lo <= p < hi for p in pos_new)
            hit_975 = any(lo <= p < hi for p in pos_975)
            digits = _norm(re.sub(r"[^\d.,-]", "", pl["심은 것"]) or "0")
            hit_old = num_old.get(digits, 0) > 0
            rows.append(dict(pl, **{"🔴 976 판이 잡았나": bool(hit_new),
                                    "975 판이 잡았나": bool(hit_975),
                                    "974 판이 잡았나": bool(hit_old)}))
        return rows

    r_new = audit_text(c_src, slots, S)
    r_975 = audit_975(c_src, slots, S)
    rows = caught(r_new, r_new, r_975)
    by = collections.OrderedDict()
    for g in ("A(슬롯 안)", "B(슬롯 밖)", "C(면제 자리)"):
        sub = [r for r in rows if r["무리"] == g]
        by[g] = {
            "심은 수": len(sub),
            "🔴🔴 976 판 분자/분모": "%d / %d" % (
                sum(1 for r in sub if r["🔴 976 판이 잡았나"]), len(sub)),
            "975 판 분자/분모": "%d / %d" % (
                sum(1 for r in sub if r["975 판이 잡았나"]), len(sub)),
            "974 판 분자/분모": "%d / %d" % (
                sum(1 for r in sub if r["974 판이 잡았나"]), len(sub)),
        }
    return {"심은 것": rows, "무리별": by,
            "🔴 심은 수 합": len(rows),
            "🔴🔴 976 판 전체 분자/분모": "%d / %d" % (
                sum(1 for r in rows if r["🔴 976 판이 잡았나"]), len(rows)),
            "🔴 975 판 전체 분자/분모": "%d / %d" % (
                sum(1 for r in rows if r["975 판이 잡았나"]), len(rows)),
            "🔴 974 판 전체 분자/분모": "%d / %d" % (
                sum(1 for r in rows if r["974 판이 잡았나"]), len(rows))}


# ══════════════════════════════════════════════════════════════════════
def stage_f5(ref, cycle, ran) -> dict:
    t0 = now()
    cs0 = code_stamp(ran)
    pat = "out%s_*.json" % cycle
    rows = collections.OrderedDict()
    num = den = 0
    for p in sorted(glob.glob(str(OUT / pat))):
        name = Path(p).name
        den += 1
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception as e:                                     # noqa: BLE001
            rows[name] = {"🔴 읽기 실패": str(e), "F5": False}
            continue
        st = d.get("🔴 도장")
        if not isinstance(st, dict):
            rows[name] = {"🔴 도장이 없다": True, "F5": False}
            continue
        ok = bool(st.get("🔴 F5 통과"))
        num += 1 if ok else 0
        rows[name] = {"F5": ok, "분자/분모": st.get("🔴 분자/분모"),
                      "기준 ref": st.get("🔴 F1 기준 ref(준 대로)"),
                      "40자 고정 sha 인가": st.get("🔴 40자 고정 sha 인가"),
                      "🔴 0000…0000 인가": st.get("🔴 기준 ref 가 0000…0000 인가"),
                      "시작=끝": st.get("🔴 시작=끝"),
                      "도장이 덮는 파일": st.get("분모: 도장이 덮는 파일")}
    out = {"무엇": "%s — F5 를 산출물 전량에 채점한다(공유 `ledger.py`)" % cycle,
           "🔴 채점 대상 글롭": pat,
           "🔴🔴 F5 분자/분모(전량)": "%d / %d" % (num, den),
           "🔴 전량 통과인가": num == den,
           "산출물별": rows}
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(ran), t0, ran, DATA)
    (OUT / ("out%s_f5.json" % cycle)).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def stage_numaudit(ref, cycle, ran) -> dict:
    t0 = now()
    cs0 = code_stamp(ran)
    S = artifact_numbers("out%s_*.json" % cycle)
    sf = OUT / ("out%s_slots.json" % cycle)
    #: 🔴🔴 **977 수리 3 — fail-open 을 닫는다.** 976 판은 슬롯 대장이 없으면 `{}` 로 돌아
    #: `files` 가 비고 `통과 = (miss_new == 0)` 이 **자료 없이 참**이 됐다.
    #: 🔴 **대장이 없으면 실패다.** 첫 바퀴 문제는 「생성기를 먼저 돌려라」로 푼다.
    man = json.loads(sf.read_text(encoding="utf-8")) if sf.is_file() else {}
    files = man.get("파일별", {})
    fail_open = (not files)
    #: 🔴🔴 **978 수리 4** — 한글 수사가 대조할 **참값**. 손으로 안 적는다.
    kcounts = collections.OrderedDict([
        ("본문", len(files)),
        ("산출물", len(glob.glob(str(OUT / ("out%s_*.json" % cycle))))),
    ])
    kor_per, kor_hits, kor_bad, kor_tied, kor_ex = (
        collections.OrderedDict(), 0, 0, 0, 0)
    per = collections.OrderedDict()
    tot = miss_old = miss_new = exempt_new = exempt_975 = bad_slot = 0
    for rel, info in files.items():
        p = Path(info["절대경로"]) if info.get("절대경로") else (ROOT / rel)
        if not p.is_file():
            per[rel] = {"🔴 파일이 없다": True}
            continue
        src = p.read_text(encoding="utf-8")
        kr = audit_korean(src, kcounts)
        kor_per[rel] = {"🔴 센 한글 수사": kr["🔴 센 한글 수사"],
                        "🔴 면제한 수사(인라인 코드 안)": kr["🔴 면제한 수사(인라인 코드 안)"],
                        "🔴 앞말이 걸린 수사": kr["🔴 앞말이 걸린 수사"],
                        "🔴🔴 어긋난 수사": kr["🔴🔴 등록된 참값과 다른 수사"],
                        "🔴 어긋난 자리": kr["🔴 어긋난 자리"]}
        kor_ex += kr["🔴 면제한 수사(인라인 코드 안)"]
        kor_hits += kr["🔴 센 한글 수사"]
        kor_tied += kr["🔴 앞말이 걸린 수사"]
        kor_bad += kr["🔴🔴 등록된 참값과 다른 수사"]
        r = audit_text(src, info["슬롯"], S)
        _a975, why975 = allow_spans(src, ALLOW_CTX_975)
        tot += r["센 수"]
        miss_old += len(r["🔴 974 판이 못 찾는 수"])
        miss_new += len(r["🔴🔴 976 판이 못 찾는 수"])
        exempt_new += r["면제된 수"]
        exempt_975 += len(_a975)
        bad_slot += r["🔴 키 경로와 본문이 다른 슬롯"]
        per[rel] = {
            "🔴 센 수(면제 뺀)": r["센 수"],
            "🔴 면제된 자리(976 판)": r["면제된 수"],
            "🔴 면제 규칙이 무는 자리(975 판)": len(_a975),
            "🔴 면제 사유별(976 판)": r["면제 사유별"],
            "🔴 슬롯 수": len(r["슬롯"]),
            "🔴🔴 키 경로와 본문이 다른 슬롯": r["🔴 키 경로와 본문이 다른 슬롯"],
            "🔴 974 판(값 집합)이 못 찾는 수": len(r["🔴 974 판이 못 찾는 수"]),
            "🔴🔴 976 판(본문 대조)이 못 찾는 수": len(r["🔴🔴 976 판이 못 찾는 수"]),
            "974 판 목록": r["🔴 974 판이 못 찾는 수"][:40],
            "🔴 976 판 목록": r["🔴🔴 976 판이 못 찾는 수"][:60],
        }
    out = {
        "무엇": "%s — 본문 넷의 모든 수가 **본문 대조**로 출처를 대는지 훑는다" % cycle,
        "🔴 대상": list(files),
        "🔴 분모: 대상 파일": len(files),
        "🔴 산출물에서 모은 수의 가짓수(974 판 허용집합)": len(S),
        "🔴🔴 974 판 분자/분모": "%d / %d" % (miss_old, tot),
        "🔴🔴🔴 976 판 분자/분모(본문이 출처를 못 대는 수 / 센 수)": "%d / %d" % (miss_new, tot),
        "🔴🔴 977 수리 3 — 슬롯 대장이 없거나 비었나(fail-open 자리)": bool(fail_open),
        "🔴 통과(976 판 · 하나도 없어야 한다)": bool((not fail_open) and miss_new == 0),
        "🔴🔴🔴 978 수리 4 — 한글 수사 채점": {
            "🔴 왜 생겼나": (
                "977 의 「본문 **넷** 0 / 370」이 판정문·카드·원장 셋을 그대로 통과했다. "
                "참값은 **다섯**이고 `NUMPAT` 은 아라비아 숫자만 본다"),
            "🔴 등록한 수사 낱말": dict(KOR_NUM),
            "🔴 뺀 규칙(수사가 아닌 자리)": KNUM_NOT.pattern,
            "🔴 대조한 앞말과 참값": dict(kcounts),
            "🔴🔴 센 한글 수사(전체)": kor_hits,
            "🔴 면제한 수사(인라인 코드 안 · 안 세는 자리)": kor_ex,
            "🔴🔴 앞말이 걸린 수사(전체)": kor_tied,
            "🔴🔴🔴 등록된 참값과 어긋난 수사": kor_bad,
            "파일별": kor_per,
            "통과": bool(kor_bad == 0 and kor_hits > 0),
            "🔴 이 절의 `통과` 가 뜻하는 것": (
                "한글 수사가 하나도 안 어긋난다. 🔴 **분모가 0 이면 실패다**"),
        },
        "통과": bool((not fail_open) and miss_new == 0 and tot > 0
                   and kor_bad == 0 and kor_hits > 0),
        "🔴🔴 키 경로와 본문이 다른 슬롯(전체)": bad_slot,
        "🔴🔴 수리 4 — 면제 자리(안 세는 자리)": {
            "🔴 976 판 면제 자리": exempt_new,
            "🔴 975 판 면제 규칙이 무는 자리": exempt_975,
            "🔴 면제 규칙 수(976 판)": len(ALLOW_CTX),
            "🔴 면제 규칙 수(975 판)": len(ALLOW_CTX_975),
            "🔴 지운 규칙": "맨-9xx(900~999 를 통째로 면제) · 사전등록 딱지를 등록 접두어로 좁힘",
            "🔴 뜻": "🔴 **이 수만큼은 원리상 안 본다** — 판정문에 그대로 적는다",
        },
        "파일별": per,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(ran), t0, ran, DATA)
    (OUT / ("out%s_numaudit.json" % cycle)).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def stage_control(ref, cycle, ran) -> dict:
    """🔴 수리 3 — 양성 대조. **문서를 안 고친다**(사본에만 심는다)."""
    t0 = now()
    cs0 = code_stamp(ran)
    S = artifact_numbers("out%s_*.json" % cycle)
    sf = OUT / ("out%s_slots.json" % cycle)
    #: 🔴🔴 **977 수리 3 — fail-open 을 닫는다.** 대장이 없으면 심은 수가 0 이 되고
    #: `무리 A 는 전부 잡아야 한다` 가 `0 == 0` 으로 **자료 없이 참**이 됐다.
    man = json.loads(sf.read_text(encoding="utf-8")) if sf.is_file() else {}
    files = man.get("파일별", {})
    fail_open = (not files)
    per = collections.OrderedDict()
    agg = collections.Counter()
    for rel, info in files.items():
        p = Path(info["절대경로"]) if info.get("절대경로") else (ROOT / rel)
        if not p.is_file():
            continue
        src = p.read_text(encoding="utf-8")
        r = plant_control(src, info["슬롯"], S, n_a=3, n_b=6, n_c=6)
        per[rel] = r["무리별"]
        for row in r["심은 것"]:
            agg["심음/" + row["무리"]] += 1
            if row["🔴 976 판이 잡았나"]:
                agg["976/" + row["무리"]] += 1
            if row["975 판이 잡았나"]:
                agg["975/" + row["무리"]] += 1
            if row["974 판이 잡았나"]:
                agg["974/" + row["무리"]] += 1
    groups = ("A(슬롯 안)", "B(슬롯 밖)", "C(면제 자리)")
    tot = collections.OrderedDict()
    for g in groups:
        n = agg["심음/" + g]
        tot[g] = {"심은 수": n,
                  "🔴🔴 976 판": "%d / %d" % (agg["976/" + g], n),
                  "975 판": "%d / %d" % (agg["975/" + g], n),
                  "974 판": "%d / %d" % (agg["974/" + g], n)}
    n_all = sum(agg["심음/" + g] for g in groups)
    out = {
        "무엇": "%s — 수리 3: 양성 대조를 진짜로 심는다(문서 사본에만)" % cycle,
        "🔴 왜": ("975 사전등록 §8 E4 가 양성 대조를 등록하고 안 만들었다. "
               "그리고 975 의 슬롯 검사는 `txt == txt` 라 항진명제였다."),
        "🔴 무리별(전 파일 합)": tot,
        "🔴 심은 수 합": n_all,
        "🔴🔴 976 판 전체": "%d / %d" % (
            sum(agg["976/" + g] for g in groups), n_all),
        "🔴 975 판 전체": "%d / %d" % (
            sum(agg["975/" + g] for g in groups), n_all),
        "🔴 974 판 전체": "%d / %d" % (
            sum(agg["974/" + g] for g in groups), n_all),
        "🔴🔴 977 수리 3 — 슬롯 대장이 없거나 비었나(fail-open 자리)": bool(fail_open),
        "🔴 무리 A 는 976 판이 전부 잡아야 한다": bool(
            (not fail_open) and agg["심음/A(슬롯 안)"] > 0
            and agg["976/A(슬롯 안)"] == agg["심음/A(슬롯 안)"]),
        "🔴 무리 B 는 976 판이 전부 잡아야 한다": bool(
            (not fail_open) and agg["심음/B(슬롯 밖)"] > 0
            and agg["976/B(슬롯 밖)"] == agg["심음/B(슬롯 밖)"]),
        "🔴 무리 C 는 아무도 못 잡는 것이 정상(선언된 사각지대)": bool(
            (not fail_open) and agg["976/C(면제 자리)"] == 0),
        "통과": bool((not fail_open) and n_all > 0
                   and agg["976/A(슬롯 안)"] == agg["심음/A(슬롯 안)"]
                   and agg["976/B(슬롯 밖)"] == agg["심음/B(슬롯 밖)"]),
        "파일별": per,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(ran), t0, ran, DATA)
    (OUT / ("out%s_control.json" % cycle)).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


DEFAULT_RAN = ("runners/ledger.py", "runners/predict971.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["f5", "numaudit", "control"])
    ap.add_argument("--ref", default="")
    ap.add_argument("--cycle", default="976")
    a = ap.parse_args()
    fn = {"f5": stage_f5, "numaudit": stage_numaudit, "control": stage_control}
    r = fn[a.stage](a.ref, a.cycle, DEFAULT_RAN)
    print(json.dumps({k: v for k, v in r.items()
                      if k not in ("파일별", "산출물별", "심은 것")},
                     ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
