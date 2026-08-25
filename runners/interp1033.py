#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사이클 1033 — [해석] 레인 v2: 정독 쌍비교 (교차-IP 조건정합 짝).

사전등록: docs/탐색/1033.md (실측 «전» 커밋 · 조항 66).
정본 절차: docs/루프.md 제7장 [해석] 레인 v1 · 부칙 6 · 조항 59·66·67·79.

세계 명제: 「관측 조건이 같은데 결과가 갈린 두 팝업의 차이는, 사건 직전 담론을 사람처럼 읽으면
           사전에 가릴 수 있다」 — 1031 이 「같은 IP 재개최 47쌍」에서 못 잰 것을 n 을 5배로 올린
           «다른 IP · 같은 관측 조건» 짝에서 다시 묻는다.

왜 v2 인가(1031 §8-마 실측 반영):
  ⓐ n=47 → MDE 0.2149 = 해상도 부족이 결론이었다. 교차-IP 짝은 표본 틀이 735 다.
  ⓑ 판독기가 「늦은 회차가 더 잘 됐다」에 78.7% 쏠렸다(실제 정답 R 비율 48.9%). 교차-IP 짝에는
     「늦은 회차」 개념 자체가 없다 — 그 교란이 원리상 사라진다.
  ⓒ 영 대조 4/4 「갑」(위치 편향) · 확신도↑ 정확도 불변(보정 실패) — 이번엔 둘 다 «자» 안에 넣는다.

봉인: 판독 자료 생성기가 결과 필드를 코드 경로에서 분리한다(기계 검사) · 판독 산출을 «먼저»
      커밋하고 채점은 그 «뒤».
판독기: `claude -p --model sonnet` 무료 CLI 경로만 — ANTHROPIC_API_KEY/AUTH_TOKEN/BASE_URL 이
      하나라도 있으면 중단(유료 API 절대 금지). 항목마다 새 프로세스 · 중립 작업 디렉터리 ·
      도구·MCP·슬래시 전면 차단.

하위명령: scout | build | probe | read | tri | export | score | chain
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import random
import subprocess
import sys
import time

import numpy as np

# ── 경로 ─────────────────────────────────────────────────────────────────────
REPO = "/Users/ax/world_model"
F = "/Users/ax/wm_harvest/foundation"
OUT = os.path.join(F, "interp1033")
ITEMS = os.path.join(OUT, "items")
WORK = os.path.join(OUT, "work")
LEDGER = os.path.join(F, "ledger_interventions/ledger.jsonl")
EDOCS = os.path.join(F, "entity_docs")
DOC = os.path.join(REPO, "docs/탐색/1033.md")
R1031 = os.path.join(REPO, "runners/interp1031.py")
R1030C = os.path.join(REPO, "runners/variance1030c.py")

sys.path.insert(0, REPO)

# ── 인용하는 자의 출처 (조항 66 — 잰 소스 sha · 등록 상수) ───────────────────
SHA_1030C = "b428e3afe7be6ea15c6b02d7ce2cf9c35ab414225d36fbeff1f3f43dcb65a66a"
SHA_1031 = "476d33941d73a7b8fb7e8159db33e93aa7dd5b0967b9e8f848a486875fbeec4c"
SHA_LEDGER = "9a76948d3e619424ceadcfb0e2c0c06eceb80992dfd36784b9cd554ed998cffd"
SHA_1031_SCORED = "b90d1f33a449c66241819977e46dd5607e06544f9473cd7d28b55a1127045c05"

# 1030 §10-3 등록 실측 — 인용 대조값(재구성 항등 검사의 표적)
X_PAIRS = 735
X_GROUPS = 135

# ── 사전 고정 상수 (등록문 §2~§7 — 여기 바꾸면 등록 위반) ────────────────────
SEED = 1033
MODEL = "sonnet"
N_DOC = 8              # 사례당 정독 발췌 상한 (1031 승계)
N_MAIN = 230           # 주표본 쌍 수 (틀이 작으면 min(230, |틀|) — §4 비상 규칙)
N_A = 40               # ⓐ(정보 0) 소표본 쌍 수 — 편향 재확인 전용
N_DUMMY = 12           # 영 대조 더미 항목 수 (양쪽 동일 — 위치 편향 실측)
GROUP_CAP = 6          # IP그룹 중복 상한 (클러스터 SE 를 위해)
RID_CAP = 4            # 개체(record) 중복 상한
CALL_CAP = 1150        # 🔴 총 판독기 호출 상한 (사전등록 · 기계 강제)
#   내역: 방향탐침 8 + 주표본 230×2팔×2회전 920 + ⓐ 40×2회전 80 + 더미 12 + 3차 ≤130 = 1150
B_BOOT = 2000          # 클러스터 붓스트랩 복제
Z_MDE = 2.80158        # z(0.975)+z(0.80) — 1031 산식 인용
AIM = 0.10             # 겨냥 효과(정확도 점) — §7 에 출처 등록
P_D_PRIOR = 13.0 / 47  # 불일치쌍 비율 사전값 = 1031 A층 ⓒ/ⓑ 실측 (out1031_scored.json)
ARMS = ("a", "b", "c")
CALL_TIMEOUT = 180
RETRY = 2
PAR = 4                # 동시 호출 (CPU 아님 · 망 대기)
LOAD_MAX = 10.0

STAMP_SIGN = ("부호 서명: 쌍 비교 «정확도»는 높을수록 좋다. ⓒ 정확도가 «낮을수록» 나쁘다. "
              "주대비 Δ = acc(ⓒ) − acc(ⓑ) 이고 Δ<0 이면 「정독이 해롭다」 쪽이다.")
STAMP_CAUSAL = ("인과 화법 금지 — 판독이 엮은 서사는 그 자체로 인과가 아니다(7-나 5). "
                "링크는 ⓐ시간순서·ⓑ근거sha·ⓒ대조검사 셋을 통과해야 「인과 후보」다.")
STAMP_CONF = ("확신도는 받되 «가중 금지» — 1031 §8-마 ② 실측: 정보↑ → 확신↑ · 정확도 불변"
              "(보정 실패). 확신도는 [관찰] 칸으로만 게재한다.")


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def now():
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def load_gate():
    while os.getloadavg()[0] > LOAD_MAX:
        print("[대기] load1=%.2f > %.1f" % (os.getloadavg()[0], LOAD_MAX), flush=True)
        time.sleep(20)


def tree_gate():
    """4-나 ⓪ 관문 — 작업 트리 = 가지의 커밋된 트리 (자기 파일 한정)."""
    mine = ["runners/interp1033.py", "docs/탐색/1033.md"]
    r = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--name-only", "HEAD", "--"]
                       + mine, cwd=REPO, capture_output=True, text=True)
    dirty = [x for x in r.stdout.split("\n") if x.strip()]
    if dirty:
        raise SystemExit("🔴 ⓪ 관문 실패 — 커밋 안 된 자기 파일: %r" % dirty)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    return {"관문": "작업트리=커밋트리", "자기파일": mine, "HEAD": head[:9]}


def src_gate():
    """조항 66 — 인용하는 소스의 sha 실물 대조. 어긋나면 측정 없이 중단."""
    got = {"variance1030c.py": sha256_file(R1030C), "interp1031.py": sha256_file(R1031),
           "ledger.jsonl": sha256_file(LEDGER)}
    want = {"variance1030c.py": SHA_1030C, "interp1031.py": SHA_1031, "ledger.jsonl": SHA_LEDGER}
    bad = {k: got[k] for k in want if got[k] != want[k]}
    if bad:
        raise SystemExit("🔴 소스 sha 불일치 — 측정 없이 중단: %r" % bad)
    return {k: v[:16] for k, v in got.items()}


def guard_free():
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
        if os.environ.get(k):
            raise SystemExit("🔴 유료 API 경로 흔적(%s) — 이 사이클은 무료 CLI 경로만 쓴다. 중단." % k)


# ══ 자료 렌더 (조항 67 — 세 팔이 «같은 함수»로 렌더된다) ═════════════════════
# 🔴 1031 대비 «단 하나» 바뀐 곳: ASK 에 최근성 추론 금지 문언(§5 ⑤)을 넣었다.
ASK = ('결과가 더 좋았을 쪽을 «반드시» 하나 고르라. 모른다고 답하지 말 것.\n'
       '🔴 금지: 「어느 쪽이 더 최근인가」·「나중에 열린 쪽이 더 잘 됐다」류의 추론을 쓰지 마라.\n'
       '   시기는 관측 조건의 하나일 뿐이고, 두 사례의 선후는 이 과제의 답과 무관하다.\n'
       '출력은 «JSON 한 줄»만. 다른 말 금지.\n'
       '{"pick":"갑"|"을","conf":1~5,"reason":"한 줄","known":true|false}\n'
       '  conf = 확신도(1 전혀 없음 ~ 5 매우 높음)\n'
       '  known = 이 사례의 «실제 결과»를 이미 알고 있다면 true.\n')

WORDING = {
    1: ("당신은 오프라인 행사 흥행을 판정하는 분석가다.\n"
        "아래 두 사례 가운데 «결과가 더 좋았던» 쪽을 고르라.\n\n"),
    2: ("다음은 한 비교 과제다. 두 사례 중 성과가 더 컸던 쪽을 판정하라.\n"
        "직관이 아니라 주어진 자료만으로 판단하되, 자료가 부족해도 반드시 한쪽을 택하라.\n\n"),
    3: ("아래 사례 갑/을을 비교한다. 어느 쪽이 더 성공적이었겠는가.\n\n"),
}

TASK = "관측 조건이 서로 맞춰진 두 팝업 개최의 결과 비교"
HEAD = "서로 다른 두 팝업 (장소유형·무료입장 동일 · 기간 비 ≤1.5 · 개장 연도 차 ≤1)"


def render(item, arm, wording, flip):
    """세 팔 공통 렌더 — 문안·순서·질문·출력 규격이 글자 단위로 같고 «주는 정보»만 다르다."""
    L, R = item["L"], item["R"]
    a, b = (R, L) if flip else (L, R)
    s = WORDING[wording]
    s += "[과제] %s\n" % item["task"]
    s += "[대상] %s\n\n" % item["head"]
    if arm == "a":
        s += "갑: 이 비교의 한 사례\n을: 이 비교의 다른 사례\n(그 밖의 정보는 주어지지 않는다.)\n\n"
    else:
        for tag, sd in (("갑", a), ("을", b)):
            s += "■ 사례 %s — 관측 조건\n" % tag
            for k, v in sd["cond"]:
                s += "  · %s: %s\n" % (k, v)
            if arm == "c":
                s += "  · 사건 직전 자료(발행일 순 · 이 사례가 열리기 «전» 문서만):\n"
                if not sd["docs"]:
                    s += "     (해당 없음)\n"
                for e in sd["docs"]:
                    s += "     [%s] %s\n" % (e["pub"], e["head"])
            s += "\n"
    s += ASK
    return s


# ── 판독기 호출 ──────────────────────────────────────────────────────────────
_ENV_DROP = ("NODE_OPTIONS", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID",
             "CLAUDE_JOB_DIR", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_CHILD_SESSION",
             "CLAUDE_PID", "CLAUDE_EFFORT", "CLAUDE_CODE_EXECPATH", "AI_AGENT")


def call_reader(prompt):
    env = {k: v for k, v in os.environ.items() if k not in _ENV_DROP}
    env["OMP_NUM_THREADS"] = "1"
    cmd = ["claude", "-p", "--model", MODEL, "--disable-slash-commands",
           "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--disallowed-tools", "WebSearch WebFetch Bash Read Glob Grep Task Edit Write"]
    import re as _re
    last = ""
    for _ in range(RETRY + 1):
        try:
            p = subprocess.run(cmd, input=prompt.encode("utf-8"), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, cwd=WORK, env=env, timeout=CALL_TIMEOUT)
            txt = p.stdout.decode("utf-8", "replace").strip()
            last = txt
            m = _re.search(r"\{.*\}", txt, _re.S)
            if m:
                try:
                    j = json.loads(m.group(0))
                except Exception:
                    j = None
                if j and str(j.get("pick", "")).strip() in ("갑", "을"):
                    return {"pick": str(j["pick"]).strip(), "conf": j.get("conf"),
                            "reason": str(j.get("reason", ""))[:300],
                            "known": bool(j.get("known", False)), "raw_ok": True}
        except subprocess.TimeoutExpired:
            last = "TIMEOUT"
    return {"pick": None, "conf": None, "reason": "", "known": None, "raw_ok": False,
            "raw": last[:300]}


def canon(r, m):
    """판독 pick(갑/을) → 정본 좌표(L/R). flip=True 면 갑=R."""
    if r["pick"] is None:
        return None
    if m["flip"]:
        return "R" if r["pick"] == "갑" else "L"
    return "L" if r["pick"] == "갑" else "R"


def mcnemar_mde(n_d, n):
    return Z_MDE * math.sqrt(n_d) / n if n else None


# ══ scout — 짝 인용 + 항등 검사 + 문서 색인 (판독기 호출 0) ═══════════════════
def cmd_scout(args):
    os.makedirs(OUT, exist_ok=True)
    t0 = now()
    gate0 = tree_gate()
    srcs = src_gate()
    load_gate()

    C30 = _load("variance1030c", R1030C)
    rows, lad, margins = C30.build_rows()

    # ① 동결 함수 «인용» — 1030 §9-자 의 정합 규칙을 그대로 돌린다(재구성 아님)
    frozen = C30.matched_cross_ip(rows, {})
    if frozen["n_쌍"] != X_PAIRS or frozen["관여 IP그룹"] != X_GROUPS:
        raise SystemExit("🔴 인용 불일치 — 1030 §10-3 등록 %d쌍/%d그룹 대 실측 %d/%d · 측정 없이 중단"
                         % (X_PAIRS, X_GROUPS, frozen["n_쌍"], frozen["관여 IP그룹"]))

    # ② 행 «인덱스»가 필요해 같은 술어를 다시 돌리고, 동결 함수 산출과 «원소별 항등»을 요구한다
    pairs = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            if a["key"] == b["key"]:
                continue
            if a["venue_type"] is None or b["venue_type"] is None or a["venue_type"] != b["venue_type"]:
                continue
            if a["is_free_entry"] is None or b["is_free_entry"] is None or a["is_free_entry"] != b["is_free_entry"]:
                continue
            if not a["dur"] or not b["dur"]:
                continue
            if max(a["dur"], b["dur"]) / min(a["dur"], b["dur"]) > 1.5:
                continue
            if abs(a["year"] - b["year"]) > 1:
                continue
            lo, hi = (a, b) if a["f"] <= b["f"] else (b, a)
            pairs.append((lo, hi, hi["y"] - lo["y"]))

    ds = np.array([p[2] for p in pairs])
    keys = sorted(set([p[0]["key"] for p in pairs] + [p[1]["key"] for p in pairs]))
    ki = {k: i for i, k in enumerate(keys)}
    med = float(np.median(np.abs(ds)))
    rng = np.random.RandomState(C30.SEED_MAIN)
    boots = []
    for _ in range(C30.B_BOOT):
        pick = set(rng.randint(0, len(keys), len(keys)).tolist())
        sel = [p[2] for p in pairs if ki[p[0]["key"]] in pick and ki[p[1]["key"]] in pick]
        if len(sel) >= 5:
            boots.append(float(np.median(np.abs(sel))))
    se_boot = float(np.std(boots, ddof=1))
    ident = {
        "n_쌍": (len(pairs), frozen["n_쌍"]),
        "관여 IP그룹": (len(keys), frozen["관여 IP그룹"]),
        "median|d|": (med, frozen["median|d|"]),
        "클러스터SE": (se_boot, [v for k, v in frozen.items() if k.startswith("클러스터SE")][0]),
        "붓스트랩 유효 복제": (len(boots), frozen["붓스트랩 유효 복제"]),
    }
    bad = {k: v for k, v in ident.items() if v[0] != v[1]}
    if bad:
        raise SystemExit("🔴 재구성이 동결 함수와 항등이 아니다 — 측정 없이 중단: %r" % list(bad))

    # ③ 문서 색인 — 이 사이클 전용 캐시(1031 색인 무접촉)
    I31 = _load("interp1031", R1031)
    rids = sorted(set(r["record_id"] for r in rows))
    cache = os.path.join(OUT, "docidx1033.json")
    print("[scout] 문서 색인 시작 %s · 대상 record %d" % (now(), len(rids)), flush=True)
    idx = I31.build_doc_index(set(rids), cache)
    print("[scout] 문서 색인 끝 %s · 키 %d" % (now(), len(idx)), flush=True)

    # ④ 짝 목록 기록 — 결과(y·d)는 «truth 파일»에만, 짝 파일에는 안 넣는다(봉인 §5-1)
    def cond_of(rec_row, rec):
        w, wh, wt, c = rec["A"]["when"], rec["A"]["where"], rec["A"]["what"], rec["C"]

        def s(v):
            return "미상" if v is None else v
        return [("개최 시기", w["opened_at"][:7]),
                ("기간(일)", s(w["duration_days"])),
                ("주말 비중", s(w["weekend_share"])),
                ("공휴일 수", s(w["holiday_days"])),
                ("장소유형", s(wh["venue_type"])),
                ("도시", s(wh["city"])),
                ("다점포", s(wh["multi_store"])),
                ("면적(평)", s(wh["area_pyeong"])),
                ("카테고리", s(wt["category"])),
                ("무료입장", s(wt["is_free_entry"])),
                ("예약필요", s(wt["reservation_required"])),
                ("직전 개최 수", s(c["ip_history"]["prior_count"])),
                ("첫 회 여부", s(c["ip_history"]["first_edition"]))]

    need = set(p[0]["record_id"] for p in pairs) | set(p[1]["record_id"] for p in pairs)
    led = {}
    for l in open(LEDGER):
        r = json.loads(l)
        if r["record_id"] in need:
            led[r["record_id"]] = r

    plist, truth = [], {}
    n_tie = 0
    for k, (lo, hi, d) in enumerate(pairs):
        pid = "P%04d" % k
        if d == 0.0:
            n_tie += 1
            continue
        nL = len([x for x in idx.get(lo["record_id"], []) if x[0] < led[lo["record_id"]]["A"]["when"]["opened_at"]])
        nR = len([x for x in idx.get(hi["record_id"], []) if x[0] < led[hi["record_id"]]["A"]["when"]["opened_at"]])
        plist.append(dict(pid=pid, rid_L=lo["record_id"], rid_R=hi["record_id"],
                          key_L=lo["key"], key_R=hi["key"], venue_type=lo["venue_type"],
                          open_L=led[lo["record_id"]]["A"]["when"]["opened_at"],
                          open_R=led[hi["record_id"]]["A"]["when"]["opened_at"],
                          n_predoc_L=nL, n_predoc_R=nR))
        truth[pid] = "R" if d > 0 else "L"

    frame = [p for p in plist if p["n_predoc_L"] >= 1 and p["n_predoc_R"] >= 1]
    fr_groups = sorted(set([p["key_L"] for p in frame] + [p["key_R"] for p in frame]))

    n_plan = min(N_MAIN, len(frame))
    mde_reg = mcnemar_mde(P_D_PRIOR * n_plan, n_plan)
    scout = {"사이클": 1033, "시작": t0, "끝": now(), "⓪ 관문": gate0, "소스sha16": srcs,
             "인용": {"출처": "1030 §10-3 · runners/variance1030c.py matched_cross_ip",
                     "동결함수산출": {k: v for k, v in frozen.items() if k != "낙인"},
                     "항등검사": {k: "일치" for k in ident}, "항등불일치": len(bad)},
             "C층행": len(rows), "사다리": lad,
             "짝": {"전체": len(pairs), "동률제외": n_tie, "유효": len(plist)},
             "틀": {"정의": "양측 모두 t0 이전 문서 ≥1건", "n_쌍": len(frame),
                   "IP그룹": len(fr_groups)},
             "계획": {"N_MAIN등록": N_MAIN, "n_실행": n_plan, "N_A": N_A, "N_DUMMY": N_DUMMY,
                     "호출상한": CALL_CAP,
                     "등록MDE_McNemar": (round(mde_reg, 4) if mde_reg else None),
                     "MDE산식": "Δacc_MDE = %.5f·√n_d / n (1031 §7 인용)" % Z_MDE,
                     "불일치쌍_사전값": "13/47 = %.4f (out1031_scored.json sha16 %s)"
                                     % (P_D_PRIOR, SHA_1031_SCORED[:16])}}
    json.dump(scout, open(os.path.join(OUT, "scout1033.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(plist, open(os.path.join(OUT, "pairs1033.json"), "w"), ensure_ascii=False)
    json.dump(truth, open(os.path.join(OUT, "truth1033.json"), "w"), ensure_ascii=False)
    json.dump({r["record_id"]: cond_of(r, led[r["record_id"]])
               for r in rows if r["record_id"] in led},
              open(os.path.join(OUT, "cond1033.json"), "w"), ensure_ascii=False)
    print(json.dumps(scout, ensure_ascii=False, indent=1))


# ══ build — 표본 추출 + 자료 렌더 + 봉인 검사 ════════════════════════════════
def cmd_build(args):
    os.makedirs(ITEMS, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    t0 = now()
    gate0 = tree_gate()
    srcs = src_gate()
    mysha = sha256_file(os.path.abspath(__file__))
    I31 = _load("interp1031", R1031)

    plist = json.load(open(os.path.join(OUT, "pairs1033.json")))
    cond = json.load(open(os.path.join(OUT, "cond1033.json")))
    idx = json.load(open(os.path.join(OUT, "docidx1033.json")))
    scout = json.load(open(os.path.join(OUT, "scout1033.json")))

    frame = [p for p in plist if p["n_predoc_L"] >= 1 and p["n_predoc_R"] >= 1]
    n_goal = min(N_MAIN, len(frame))

    # ── 표본 추출 (씨앗 1033 · venue_type 비례 층화 · 그룹/개체 상한) ─────────
    def h(p):
        return hashlib.sha256(("%d|%s|%s" % (SEED, p["rid_L"], p["rid_R"])).encode()).hexdigest()

    frame_sorted = sorted(frame, key=h)
    import collections
    vt_cnt = collections.Counter(p["venue_type"] for p in frame_sorted)
    target = {v: int(round(n_goal * c / float(len(frame_sorted)))) for v, c in vt_cnt.items()}
    gcnt, rcnt, vcnt = {}, {}, {}
    sample = []

    def take(p, respect_stratum):
        if len(sample) >= n_goal:
            return False
        if gcnt.get(p["key_L"], 0) >= GROUP_CAP or gcnt.get(p["key_R"], 0) >= GROUP_CAP:
            return False
        if rcnt.get(p["rid_L"], 0) >= RID_CAP or rcnt.get(p["rid_R"], 0) >= RID_CAP:
            return False
        if respect_stratum and vcnt.get(p["venue_type"], 0) >= target.get(p["venue_type"], 0):
            return False
        gcnt[p["key_L"]] = gcnt.get(p["key_L"], 0) + 1
        gcnt[p["key_R"]] = gcnt.get(p["key_R"], 0) + 1
        rcnt[p["rid_L"]] = rcnt.get(p["rid_L"], 0) + 1
        rcnt[p["rid_R"]] = rcnt.get(p["rid_R"], 0) + 1
        vcnt[p["venue_type"]] = vcnt.get(p["venue_type"], 0) + 1
        sample.append(p)
        return True

    for p in frame_sorted:
        take(p, True)
    for p in frame_sorted:              # 층화 잔여분 — 등록 순서대로 메운다
        if p not in sample:
            take(p, False)
    sample.sort(key=lambda p: p["pid"])

    # ── 발췌 채취 + 봉인 ────────────────────────────────────────────────────
    seal = dict(발췌후보=0, 정규식탈락=0, 채택=0, t0이후=0, 본문결측=0,
                금칙히트=0, 값금칙_탈락발췌=0, 값금칙히트=0)
    want = set()
    picked = {}
    for p in sample:
        for side in ("L", "R"):
            rid, opn = p["rid_" + side], p["open_" + side]
            ds = I31.pick_docs(idx, rid, opn, N_DOC)
            picked[(p["pid"], side)] = ds
            for d in ds:
                want.add((d[1], d[2]))
    heads = I31.fetch_heads(want)

    def mk_docs(ds, before):
        outl = []
        for pub, src, did in ds:
            seal["발췌후보"] += 1
            if pub >= before:
                seal["t0이후"] += 1
                continue
            hd, tsha = heads.get((src, did), ("", ""))
            if not hd:
                seal["본문결측"] += 1
                continue
            hd = hd.replace("\n", " ").strip()[:280]
            if I31.RESULT_RE.search(hd):
                seal["정규식탈락"] += 1
                continue
            outl.append(dict(pub=pub, head=hd, sha16=tsha, src=src.split("_")[1].split(".")[0]))
            seal["채택"] += 1
            if len(outl) >= N_DOC:
                break
        return outl

    led = {}
    need = set([p["rid_L"] for p in sample] + [p["rid_R"] for p in sample])
    for l in open(LEDGER):
        r = json.loads(l)
        if r["record_id"] in need:
            led[r["record_id"]] = r

    items, meta_by_iid = [], {}
    for i, p in enumerate(sample):
        iid = "X%03d" % i
        it = dict(iid=iid, kind="pair", task=TASK, head=HEAD,
                  L=dict(cond=cond[p["rid_L"]], docs=mk_docs(picked[(p["pid"], "L")], p["open_L"])),
                  R=dict(cond=cond[p["rid_R"]], docs=mk_docs(picked[(p["pid"], "R")], p["open_R"])),
                  meta=dict(pid=p["pid"], rid_L=p["rid_L"], rid_R=p["rid_R"],
                            key_L=p["key_L"], key_R=p["key_R"], venue_type=p["venue_type"]))
        items.append(it)
        meta_by_iid[iid] = p

    # ── 영 대조 더미 (양쪽 동일 · 정답 없음 · 위치 편향 실측) ────────────────
    dummies = []
    for i, it in enumerate([x for x in items if x["L"]["docs"]][:N_DUMMY]):
        d = dict(iid="Z%02d" % i, kind="dummy", task=TASK, head=HEAD,
                 L=dict(cond=it["L"]["cond"], docs=it["L"]["docs"]),
                 R=dict(cond=it["L"]["cond"], docs=it["L"]["docs"]),
                 meta=dict(src_iid=it["iid"]))
        dummies.append(d)

    all_items = items + dummies

    # ── 제시 순서 (씨앗 고정 · 정답 무관 · 회전 2 는 회전 1 의 정확한 반전) ──
    order = {}
    for it in all_items:
        for p_ in (1, 2, 3):
            r2 = random.Random("%d|%s|%d" % (SEED, it["iid"], p_))
            if p_ == 2:
                order["%s|2" % it["iid"]] = not order["%s|1" % it["iid"]]
            else:
                order["%s|%d" % (it["iid"], p_)] = (r2.random() < 0.5)

    # ── 값 수준 금칙 (1031 자 수리 2 판 «인용·재사용» — 탈락 후 재검사) ──────
    def val_strings(it):
        vs = set()
        if it["kind"] != "pair":
            return vs
        import re as _re
        for rid in (it["meta"]["rid_L"], it["meta"]["rid_R"]):
            Y = led[rid]["Y"]
            for v in (Y.get("u_daily_visitors"), Y.get("visitors_total"), Y.get("sales_krw")):
                if v is None:
                    continue
                n = int(round(float(v)))
                for t in (str(n), "{:,}".format(n), str(v)):
                    if len(_re.sub(r"\D", "", t)) >= 3:
                        vs.add(t)
        return vs

    for it in items:
        vs0 = val_strings(it)
        for sd in (it["L"], it["R"]):
            keep = []
            for e in sd["docs"]:
                if any(v in e["head"] for v in vs0):
                    seal["값금칙_탈락발췌"] += 1
                    seal["채택"] -= 1
                else:
                    keep.append(e)
            sd["docs"] = keep
    for d in dummies:                     # 더미는 원본 항목의 탈락 후 발췌를 다시 가져온다
        src = [x for x in items if x["iid"] == d["meta"]["src_iid"]][0]
        d["L"]["docs"] = src["L"]["docs"]
        d["R"]["docs"] = src["L"]["docs"]

    # ── ⓐ 소표본 (편향 재확인 전용 · 등록 순서 앞 N_A) ───────────────────────
    a_iids = [it["iid"] for it in items][:N_A]

    # ── 자료 파일 기록 + 금칙 전수 검사 ─────────────────────────────────────
    man = []
    for it in all_items:
        vs = val_strings(it)
        arms = ARMS if it["iid"] in a_iids else ("b", "c")
        if it["kind"] == "dummy":
            arms = ("c",)
        for arm in arms:
            for p_ in (1, 2, 3):
                txt = render(it, arm, p_, order["%s|%d" % (it["iid"], p_)])
                low = txt.lower()
                for f in I31.FORBID:
                    if f.lower() in low:
                        seal["금칙히트"] += 1
                for v in vs:
                    if v in txt:
                        seal["값금칙히트"] += 1
                fp = os.path.join(ITEMS, "%s_%s_p%d.txt" % (it["iid"], arm, p_))
                with open(fp, "w") as fh:
                    fh.write(txt)
                man.append(dict(iid=it["iid"], kind=it["kind"], arm=arm, pass_=p_,
                                flip=order["%s|%d" % (it["iid"], p_)], sha256=sha256_text(txt),
                                n_doc_L=len(it["L"]["docs"]), n_doc_R=len(it["R"]["docs"])))

    n = len(items)
    doc_both = sum(1 for it in items if it["L"]["docs"] and it["R"]["docs"])
    planned = 8 + 4 * n + 2 * len(a_iids) + len(dummies)
    tri_room = CALL_CAP - planned
    mde_reg = mcnemar_mde(P_D_PRIOR * n, n)

    # 부칙 6 관문 — 이 사이클의 주대비는 [해석] 레인 대비이지 [판정] 게이트가 아니다.
    # assert_mde 는 «진단»으로 호출하고 예외는 잡아서 계수·게재한다(§7 등록대로 중단하지 않는다).
    from pretrain.mde_guard import assert_mde, MdeGateError
    try:
        mde_stamp = assert_mde(mde_reg, AIM, SHA_1031_SCORED[:32])
        mde_stamp["결과"] = "통과(겨냥 ≥ MDE)"
    except MdeGateError as e:
        mde_stamp = {"결과": "미달", "사유": str(e), "MDE": mde_reg, "겨냥 효과": AIM,
                     "낙인": "부칙 6 ㉯ — [판정] 레인 금지. 본 대비는 처음부터 [해석] 레인이고 "
                             "판정 게이트가 아니다(§7 등록). 해상도 부족을 수로 게재한다."}

    meta = {"사이클": 1033, "시작": t0, "끝": now(), "러너sha256": mysha,
            "러너sha_전후일치": (mysha == sha256_file(os.path.abspath(__file__))),
            "⓪ 관문": gate0, "소스sha16": srcs, "문서_sha256": sha256_file(DOC),
            "인용": scout["인용"], "틀": scout["틀"],
            "판독기": {"모델": MODEL, "경로": "claude -p (무료 CLI)", "유료API": False,
                      "도구차단": True, "MCP차단": True, "항목마다_새_프로세스": True},
            "표본": {"n_쌍": n,
                    "IP그룹": len(set([p["key_L"] for p in sample]
                                     + [p["key_R"] for p in sample])),
                    "고유record": len(need), "양측유발췌": doc_both,
                    "그룹상한": GROUP_CAP, "record상한": RID_CAP,
                    "층화": "venue_type 비례(틀 안 비중)", "씨앗": SEED,
                    "venue_type분포": dict(collections.Counter(p["venue_type"] for p in sample))},
            "팔": {"ⓐ 소표본": len(a_iids), "ⓑ": n, "ⓒ": n,
                  "ⓐ 사유": "1031 이 ⓐ(정보 0)를 47쌍에서 이미 쟀다(0.3191 · 우연 이하). "
                          "예산을 주대비(ⓒ−ⓑ)에 몰기 위해 ⓐ 는 편향 재확인용 소표본만 돌린다."},
            "더미영대조": len(dummies),
            "호출": {"상한": CALL_CAP, "계획": planned, "3차 여유": tri_room,
                    "내역": "탐침 8 + 주표본 %d×2팔×2회전 %d + ⓐ %d×2 %d + 더미 %d"
                           % (n, 4 * n, len(a_iids), 2 * len(a_iids), len(dummies))},
            "봉인": seal,
            "MDE": {"등록_McNemar": round(mde_reg, 4),
                    "산식": "Δacc_MDE = %.5f·√n_d / n" % Z_MDE,
                    "불일치쌍_사전값": round(P_D_PRIOR, 4),
                    "출처": "1031 A층 ⓒ/ⓑ n_d=13/47 (out1031_scored.json sha256 %s)"
                          % SHA_1031_SCORED,
                    "단일팔_이항": round(0.5 + Z_MDE * 0.5 / math.sqrt(n), 4),
                    "표_by_n_d": {str(nd): round(mcnemar_mde(nd, n), 4)
                                 for nd in (20, 40, 60, 80, 100)},
                    "부칙 6": mde_stamp},
            "부호서명": STAMP_SIGN, "인과화법": STAMP_CAUSAL, "확신도": STAMP_CONF}
    truth_all = json.load(open(os.path.join(OUT, "truth1033.json")))
    truth = {it["iid"]: truth_all[it["meta"]["pid"]] for it in items}
    json.dump(meta, open(os.path.join(OUT, "build_meta.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), ensure_ascii=False)
    json.dump(all_items, open(os.path.join(OUT, "items.json"), "w"), ensure_ascii=False)
    json.dump(truth, open(os.path.join(OUT, "truth.json"), "w"), ensure_ascii=False)
    json.dump(dict(a_iids=a_iids, dummies=[d["iid"] for d in dummies],
                   pairs=[it["meta"] for it in items]),
              open(os.path.join(OUT, "plan.json"), "w"), ensure_ascii=False)
    json.dump(dict(meta=meta, manifest=man),
              open(os.path.join(REPO, "runners/out1033_prereg.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=1))


# ══ probe — 측정 «전» 방향 탐침 (8호출) ══════════════════════════════════════
def cmd_probe(args):
    guard_free()
    os.makedirs(WORK, exist_ok=True)
    tasks = []
    for i in range(4):
        tasks.append(dict(pid="POS%d" % i, kind="pos", truth="갑", prompt=(
            WORDING[1] + "[과제] 두 사례의 결과 비교\n[대상] 시험용 사례\n\n"
            "■ 사례 갑 — 관측 조건\n  · 비고: 이 사례가 «더 좋은 결과»를 냈다고 자료에 명시되어 있다\n\n"
            "■ 사례 을 — 관측 조건\n  · 비고: 이 사례가 «더 나쁜 결과»를 냈다고 자료에 명시되어 있다\n\n" + ASK)))
        tasks.append(dict(pid="NUL%d" % i, kind="null", truth=None, prompt=(
            WORDING[1] + "[과제] 두 사례의 결과 비교\n[대상] 시험용 사례\n\n"
            "■ 사례 갑 — 관측 조건\n  · 비고: 정보 없음\n\n"
            "■ 사례 을 — 관측 조건\n  · 비고: 정보 없음\n\n" + ASK)))
    res = []
    with cf.ThreadPoolExecutor(max_workers=PAR) as ex:
        for t, r in zip(tasks, ex.map(lambda t: call_reader(t["prompt"]), tasks)):
            res.append(dict(pid=t["pid"], kind=t["kind"], truth=t["truth"], **r))
    pos = [r for r in res if r["kind"] == "pos"]
    nul = [r for r in res if r["kind"] == "null"]
    out = dict(시각=now(), 호출=len(res),
               양성대조_정답=sum(1 for r in pos if r["pick"] == "갑"), 양성대조_n=len(pos),
               영대조_갑선택=sum(1 for r in nul if r["pick"] == "갑"), 영대조_n=len(nul),
               파싱실패=sum(1 for r in res if not r["raw_ok"]), 원문=res)
    json.dump(out, open(os.path.join(OUT, "probe.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "원문"}, ensure_ascii=False, indent=1))


# ══ read ════════════════════════════════════════════════════════════════════
def _do_read(job):
    iid, arm, p = job
    fp = os.path.join(ITEMS, "%s_%s_p%d.txt" % (iid, arm, p))
    txt = open(fp).read()
    r = call_reader(txt)
    r.update(iid=iid, arm=arm, pass_=p, item_sha256=sha256_text(txt), ts=now())
    return r


def _probe_calls():
    p = os.path.join(OUT, "probe.json")
    return json.load(open(p))["호출"] if os.path.exists(p) else 0


def _spent():
    path = os.path.join(OUT, "readings.jsonl")
    n = sum(1 for _ in open(path)) if os.path.exists(path) else 0
    return n + _probe_calls()


def _run_jobs(jobs, outpath, spent_before):
    if spent_before + len(jobs) > CALL_CAP:
        raise SystemExit("🔴 호출 상한 초과 — 사전등록 %d · 이미 %d · 요청 %d"
                         % (CALL_CAP, spent_before, len(jobs)))
    res = []
    with open(outpath, "a") as fh:
        with cf.ThreadPoolExecutor(max_workers=PAR) as ex:
            for i, r in enumerate(ex.map(_do_read, jobs)):
                res.append(r)
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                fh.flush()
                if (i + 1) % 40 == 0:
                    print("  %d/%d  %s" % (i + 1, len(jobs), now()), flush=True)
    return res


def cmd_read(args):
    guard_free()
    load_gate()
    plan = json.load(open(os.path.join(OUT, "plan.json")))
    items = json.load(open(os.path.join(OUT, "items.json")))
    a_iids = set(plan["a_iids"])
    dummies = set(plan["dummies"])
    path = os.path.join(OUT, "readings.jsonl")
    done = set()
    if os.path.exists(path):
        for l in open(path):
            r = json.loads(l)
            done.add((r["iid"], r["arm"], r["pass_"]))
    jobs = []
    for it in items:
        iid = it["iid"]
        if iid in dummies:
            jobs.append((iid, "c", 1))
            continue
        for arm in (("a", "b", "c") if iid in a_iids else ("b", "c")):
            for p in (1, 2):
                jobs.append((iid, arm, p))
    jobs = [j for j in jobs if j not in done]
    print("[read] 남은 호출 %d · 이미 %d · 시작 %s" % (len(jobs), len(done), now()), flush=True)
    _run_jobs(jobs, path, len(done) + _probe_calls())
    print("[read] 끝 %s" % now())


def cmd_tri(args):
    """이중 판독 불일치 → 3차 판독 (예산 우선순위 ⓒ→ⓑ→ⓐ)."""
    guard_free()
    man = {(m["iid"], m["arm"], m["pass_"]): m
           for m in json.load(open(os.path.join(OUT, "manifest.json")))}
    path = os.path.join(OUT, "readings.jsonl")
    R = {}
    for l in open(path):
        r = json.loads(l)
        R[(r["iid"], r["arm"], r["pass_"])] = r
    need = []
    for (iid, arm, p), r in list(R.items()):
        if p != 1 or iid.startswith("Z"):
            continue
        r2 = R.get((iid, arm, 2))
        if not r2:
            continue
        c1, c2 = canon(r, man[(iid, arm, 1)]), canon(r2, man[(iid, arm, 2)])
        if c1 is None or c2 is None or c1 != c2:
            if (iid, arm, 3) not in R:
                need.append((iid, arm, 3))
    PRIO = {"c": 0, "b": 1, "a": 2}
    need.sort(key=lambda t: (PRIO[t[1]], t[0]))
    spent = _spent()
    room = CALL_CAP - spent
    skipped, need = need[room:], need[:room]
    print("[tri] 3차 필요 %d · 예산 여유 %d · 실시 %d · 미실시 %d"
          % (len(need) + len(skipped), room, len(need), len(skipped)), flush=True)
    json.dump(dict(시각=now(), 필요=len(need) + len(skipped), 실시=len(need),
                   미실시=[list(x) for x in skipped]),
              open(os.path.join(OUT, "tri_budget.json"), "w"), ensure_ascii=False, indent=1)
    if need:
        _run_jobs(need, path, spent)
    print("[tri] 끝 %s" % now())


# ══ export — 봉인 판독 산출 (정답 대조 «전» 커밋) ════════════════════════════
def cmd_export(args):
    R = []
    for l in open(os.path.join(OUT, "readings.jsonl")):
        r = json.loads(l)
        R.append(dict(iid=r["iid"], arm=r["arm"], pass_=r["pass_"], pick=r["pick"],
                      conf=r["conf"], known=r["known"], raw_ok=r["raw_ok"],
                      item_sha256=r["item_sha256"], ts=r["ts"]))
    meta = json.load(open(os.path.join(OUT, "build_meta.json")))
    pp = os.path.join(OUT, "probe.json")
    probe = json.load(open(pp)) if os.path.exists(pp) else None
    if probe:
        probe = {k: v for k, v in probe.items() if k != "원문"}
    tb = os.path.join(OUT, "tri_budget.json")
    json.dump({"주의": "봉인 판독 산출 — 정답 대조 «전» 커밋(제7장 7-나 ①). 실명·발췌 없음.",
               "시각": now(), "판독": len(R), "호출상한": CALL_CAP,
               "총호출": len(R) + _probe_calls(), "방향탐침": probe,
               "봉인": meta["봉인"], "판독기": meta["판독기"], "표본": meta["표본"],
               "MDE": meta["MDE"],
               "3차 예산": (json.load(open(tb)) if os.path.exists(tb) else None),
               "판독원문": R},
              open(os.path.join(REPO, "runners/out1033_readings.json"), "w"),
              ensure_ascii=False, indent=1)
    print("판독 수 %d · 총호출 %d / %d" % (len(R), len(R) + _probe_calls(), CALL_CAP))


# ══ score ═══════════════════════════════════════════════════════════════════
def cmd_score(args):
    truth = json.load(open(os.path.join(OUT, "truth.json")))
    plan = json.load(open(os.path.join(OUT, "plan.json")))
    items = {it["iid"]: it for it in json.load(open(os.path.join(OUT, "items.json")))}
    man = {(m["iid"], m["arm"], m["pass_"]): m
           for m in json.load(open(os.path.join(OUT, "manifest.json")))}
    meta = json.load(open(os.path.join(OUT, "build_meta.json")))
    R = {}
    for l in open(os.path.join(OUT, "readings.jsonl")):
        r = json.loads(l)
        R[(r["iid"], r["arm"], r["pass_"])] = r

    a_iids, dummies = set(plan["a_iids"]), set(plan["dummies"])
    pmeta = {m["pid"]: m for m in plan["pairs"]}
    iid2pid = {}
    for it in items.values():
        if it["kind"] == "pair":
            iid2pid[it["iid"]] = it["meta"]["pid"]

    fin, agree, tri_used, badparse, known_flags, nofb = {}, {}, 0, 0, {}, set()
    for iid in items:
        if iid in dummies:
            continue
        for arm in ARMS:
            if arm == "a" and iid not in a_iids:
                continue
            c = []
            for p in (1, 2):
                r = R.get((iid, arm, p))
                if not r:
                    continue
                if not r["raw_ok"]:
                    badparse += 1
                c.append(canon(r, man[(iid, arm, p)]))
                if r.get("known"):
                    known_flags[(iid, arm)] = True
            if len(c) == 2 and c[0] is not None and c[0] == c[1]:
                agree[(iid, arm)] = True
                fin[(iid, arm)] = c[0]
            else:
                agree[(iid, arm)] = False
                r3 = R.get((iid, arm, 3))
                if r3:
                    tri_used += 1
                    c3 = canon(r3, man[(iid, arm, 3)])
                    if r3.get("known"):
                        known_flags[(iid, arm)] = True
                    votes = [x for x in c + [c3] if x]
                    fin[(iid, arm)] = max(set(votes), key=votes.count) if votes else None
                else:
                    fin[(iid, arm)] = c[0] if c and c[0] else (c[1] if len(c) > 1 else None)
                    nofb.add((iid, arm))

    def acc(sel, arm):
        n = ok = 0
        for iid in sel:
            f = fin.get((iid, arm))
            if f is None:
                continue
            n += 1
            ok += int(f == truth[iid])
        return ok, n, (ok / float(n) if n else None)

    def mcnemar(sel, a1, a2):
        b = c = npair = 0
        for iid in sel:
            f1, f2 = fin.get((iid, a1)), fin.get((iid, a2))
            if f1 is None or f2 is None:
                continue
            npair += 1
            o1, o2 = int(f1 == truth[iid]), int(f2 == truth[iid])
            if o1 and not o2:
                b += 1
            elif o2 and not o1:
                c += 1
        nd = b + c
        if nd == 0 or npair == 0:
            return dict(b=b, c=c, n_d=nd, 짝분모=npair, p=None, MDE=None, Δacc=0.0)
        p = 0.0
        base = math.comb(nd, b) * 0.5 ** nd
        for k in range(nd + 1):
            pk = math.comb(nd, k) * 0.5 ** nd
            if pk <= base + 1e-12:
                p += pk
        return dict(b=b, c=c, n_d=nd, 짝분모=npair, p=round(min(1.0, p), 5),
                    MDE=round(mcnemar_mde(nd, npair), 4),
                    Δacc=round((b - c) / float(npair), 4))

    def cluster_boot(sel, a1, a2):
        """IP그룹 클러스터 붓스트랩 — 1030 §9-자 규칙 승계(양쪽 그룹이 모두 뽑힌 쌍만)."""
        rows = []
        for iid in sel:
            f1, f2 = fin.get((iid, a1)), fin.get((iid, a2))
            if f1 is None or f2 is None:
                continue
            m = pmeta[iid2pid[iid]]
            rows.append((m["key_L"], m["key_R"],
                         int(f1 == truth[iid]) - int(f2 == truth[iid])))
        if not rows:
            return None
        keys = sorted(set([r[0] for r in rows] + [r[1] for r in rows]))
        ki = {k: i for i, k in enumerate(keys)}
        rng = np.random.RandomState(SEED)
        boots = []
        for _ in range(B_BOOT):
            pick = set(rng.randint(0, len(keys), len(keys)).tolist())
            sel2 = [r[2] for r in rows if ki[r[0]] in pick and ki[r[1]] in pick]
            if len(sel2) >= 20:
                boots.append(float(np.mean(sel2)))
        return dict(IP그룹=len(keys), 유효복제=len(boots),
                    Δacc=round(float(np.mean([r[2] for r in rows])), 4),
                    클러스터SE=(round(float(np.std(boots, ddof=1)), 4) if len(boots) > 1 else None))

    def binom_p(k, n):
        if not n:
            return None
        p = 0.0
        base = math.comb(n, k) * 0.5 ** n
        for i in range(n + 1):
            pi = math.comb(n, i) * 0.5 ** n
            if pi <= base + 1e-12:
                p += pi
        return round(min(1.0, p), 5)

    ALL = [i for i in items if items[i]["kind"] == "pair"]
    DOCSEL = [i for i in ALL if items[i]["L"]["docs"] and items[i]["R"]["docs"]]
    A_SUB = [i for i in ALL if i in a_iids]

    def table(sel, name, arms=("b", "c")):
        t = dict(표본=name, n=len(sel))
        for arm in arms:
            ok, n, a = acc(sel, arm)
            t[arm] = dict(맞음=ok, n=n, 정확도=(round(a, 4) if a is not None else None),
                          우연대비p=binom_p(ok, n) if n else None,
                          일치율=round(sum(1 for i in sel if agree.get((i, arm))) / float(len(sel)), 4))
        if "c" in arms and "b" in arms:
            t["ⓒ−ⓑ"] = mcnemar(sel, "c", "b")
            t["ⓒ−ⓑ 클러스터"] = cluster_boot(sel, "c", "b")
        if "a" in arms:
            t["ⓑ−ⓐ"] = mcnemar(sel, "b", "a")
        return t

    # 위치 편향 — 더미(양쪽 동일) 실측
    dz = [R.get((z, "c", 1)) for z in sorted(dummies)]
    dz = [x for x in dz if x]
    z_gap = sum(1 for x in dz if x["pick"] == "갑")
    # 「늦게 연 쪽(R)」 선택 쏠림 — 1031 §8-마 ① 의 교차-IP 판
    late = {}
    for arm in ("b", "c"):
        sel = [i for i in ALL if fin.get((i, arm))]
        k = sum(1 for i in sel if fin[(i, arm)] == "R")
        late[arm] = dict(R선택=k, n=len(sel), 비율=round(k / float(len(sel)), 4) if sel else None,
                         이항p=binom_p(k, len(sel)))
    truth_R = sum(1 for i in ALL if truth[i] == "R")
    late["정답_R비율"] = round(truth_R / float(len(ALL)), 4)

    conf = {}
    for arm in ("b", "c"):
        cc = {}
        for i in ALL:
            r = R.get((i, arm, 1))
            if r and r.get("conf") is not None:
                cc[str(r["conf"])] = cc.get(str(r["conf"]), 0) + 1
        conf[arm] = cc

    known_items = sorted({i for (i, a) in known_flags})
    out = dict(시각=now(), 러너sha256=sha256_file(os.path.abspath(__file__)),
               문서_sha256=sha256_file(DOC),
               판독총호출=len(R) + _probe_calls(), 호출상한=CALL_CAP,
               파싱실패=badparse, 삼차판독=tri_used,
               부호서명=STAMP_SIGN, 인과화법=STAMP_CAUSAL, 확신도=STAMP_CONF,
               등록MDE=meta["MDE"],
               표=[table(ALL, "주표본 전량(ITT · 주대비)"),
                   table(DOCSEL, "양측 채택발췌≥1 [부차·관찰]"),
                   table(A_SUB, "ⓐ 소표본(편향 재확인) [관찰]", arms=("a", "b", "c"))],
               영대조_위치편향=dict(더미=len(dz), 갑선택=z_gap,
                                    비율=round(z_gap / float(len(dz)), 4) if dz else None,
                                    이항p=binom_p(z_gap, len(dz)) if dz else None,
                                    낙인="양쪽이 «글자 단위로 동일»한 항목 — 정답 없음. 위치 편향만 잰다."),
               늦은쪽쏠림_관찰=late,
               확신도_관찰=dict(분포=conf, 낙인=STAMP_CONF),
               오염=dict(자진신고_항목수=len(known_items),
                         민감도_제외후=[table([i for i in ALL if i not in known_items],
                                              "주표본(오염 신고 제외)")]),
               삼차미실시=dict(항목팔수=len(nofb),
                               낙인="예산 소진 — 회전 1 정본 좌표로 대체(씨앗 동전 = 정답 독립)",
                               민감도_제외후=[table([i for i in ALL
                                                     if (i, "c") not in nofb and (i, "b") not in nofb],
                                                    "주표본(3차 미실시 제외)")]))
    json.dump(out, open(os.path.join(OUT, "scored.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(out, open(os.path.join(REPO, "runners/out1033_scored.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


# ══ chain — 인과 체인 v0 링크 (판독기 호출 0 · 7-다 규격) ════════════════════
def cmd_chain(args):
    K = int(args.k)
    truth = json.load(open(os.path.join(OUT, "truth.json")))
    items = {it["iid"]: it for it in json.load(open(os.path.join(OUT, "items.json")))}
    man = {(m["iid"], m["arm"], m["pass_"]): m
           for m in json.load(open(os.path.join(OUT, "manifest.json")))}
    R = {}
    for l in open(os.path.join(OUT, "readings.jsonl")):
        r = json.loads(l)
        R[(r["iid"], r["arm"], r["pass_"])] = r
    ok_iids = []
    for iid, it in sorted(items.items()):
        if it["kind"] != "pair":
            continue
        r1 = R.get((iid, "c", 1))
        r2 = R.get((iid, "c", 2))
        if not r1 or not r2:
            continue
        c1, c2 = canon(r1, man[(iid, "c", 1)]), canon(r2, man[(iid, "c", 2)])
        if c1 and c1 == c2 and c1 == truth[iid]:
            ok_iids.append(iid)
    links = []
    for iid in ok_iids[:K]:
        it = items[iid]
        win = truth[iid]
        docs = it[win]["docs"]
        r1 = R[(iid, "c", 1)]
        links.append(dict(
            링크id="L%02d" % len(links), 항목=iid,
            선행사건="이긴 쪽 사례의 t0 이전 담론 %d건(발행일 %s ~ %s)"
                     % (len(docs), docs[0]["pub"] if docs else "-", docs[-1]["pub"] if docs else "-"),
            후행결과="그 사례의 일평균 방문자가 조건 정합 상대보다 컸다",
            시간차="모든 근거 문서가 개최일 «이전»(기계 검사 통과 · t0이후 0)",
            근거문서sha=[d["sha16"] for d in docs],
            기제문장=r1.get("reason", "")[:200],
            반증조건="같은 장소유형·같은 무료입장·기간비≤1.5·연도차≤1 인 유사 개체 K개 중 "
                     "t0 이전 담론이 «없던» 쪽이 이긴 사례 비율이 0.5 와 다르지 않다면 이 링크는 반증된다",
            대조검사="미실측 — 다음 사이클 몫(등록)"))
    out = {"시각": now(), "규격": "docs/루프.md 7-다 chain v0", "K": len(links),
           "ⓒ 정답_이중일치_항목수": len(ok_iids),
           "확증링크비율": "0 / %d" % len(links),
           "낙인": ["대조 검사 미실측 — 전부 「미검」이고 전부 「서사」다. 「인과 후보」 0개.",
                   STAMP_CAUSAL],
           "링크": links}
    json.dump(out, open(os.path.join(REPO, "runners/out1033_chain.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "링크"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scout", "build", "probe", "read", "tri",
                                    "export", "score", "chain"])
    ap.add_argument("--k", default="10")
    a = ap.parse_args()
    {"scout": cmd_scout, "build": cmd_build, "probe": cmd_probe, "read": cmd_read,
     "tri": cmd_tri, "export": cmd_export, "score": cmd_score, "chain": cmd_chain}[a.cmd](a)
