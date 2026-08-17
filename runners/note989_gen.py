#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""989 문서 생산기 — 🔴 **규칙 D: 손으로 안 쓴다.**

모든 수는 `runners/out989_*.json` 의 «칸»에서 오고 **치환표**로만 문서에 들어간다.
씀:
    python3 runners/note989_gen.py --stage docs --ref <40자 sha>
    python3 runners/note989_gen.py --stage card --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
OUT = ROOT / "runners"
DOCS = ROOT / "docs"
CARD = Path(os.path.expanduser(
    "~/.claude/projects/-Users-ax-world-model/memory/project-lab-state.md"))


def _load(name):
    p = OUT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _dig(o, *ks):
    cur = o
    for k in ks:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _sha(rel):
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def table(ref):
    W = _load("out989_world.json")
    A = _load("out989_audit.json")
    S = _load("out989_score.json")
    G = _load("out989_wiring.json")
    L = _load("out989_last.json")
    J = _dig(W, "§3 🔴🔴🔴 판정") or {}
    F = _dig(W, "🔴 깔때기") or {}
    idA = _dig(A, "§A 🔴🔴🔴 경로 동일성 — 987 (검정력 시연 · 조항 64)") or {}
    idB = _dig(A, "§B 🔴🔴🔴 경로 동일성 여덟째 칸") or {}
    reC = _dig(A, "§C 🔴🔴 988 의 예측을 다시 채점한다") or {}
    dsec = _dig(A, "§D 🔴🔴🔴 `R1` — 「걸린 자리」의 정의") or {}
    rec = [v for k, v in dsec.items() if "재분류" in k]
    rec = rec[0] if rec else {}
    E = _dig(A, "§E 🔴🔴🔴 `R4` — 단조 불변 자 수리") or {}
    Gg = _dig(A, "§G 🔴🔴🔴 §1-5 — 이 사이클이 «세계»를 만졌나") or {}
    ctlR = _dig(E, "🔴🔴 대조별 — 등록 문안 그대로") or {}
    old_neg = "🔴 988 이 쓴 음성 대조 `㉱ 대 h`(🔴 구성상 «단조 감소»)"
    perm = "🔴 음성 대조 ㉠ — 무작위 «치환»(참 귀무)"
    ushape = "🔴 음성 대조 ㉡ — U자(비단조 · 참 귀무)"
    ws = _dig(W, "🔴🔴🔴 세계 자료(런타임 지문)") or {}
    fal = _dig(S, "§5 🔴 반증조건") or {}
    prd = _dig(S, "§4 🔴 예측") or {}
    lad = _dig(W, "§1 🔴🔴🔴 사다리(u = 0 · 판정)") or {}

    t = collections.OrderedDict()
    t["ref"] = ref
    # 🔴 «지금»이 아니라 «측정이 끝난 시각»을 쓴다 --- 안 그러면 문서가 원리상 «수렴 못 한다»
    t["끝시각"] = _dig(W, "🔴 도장", "끝(UTC)")
    t["측정시작"] = _dig(W, "🔴 도장", "시작(UTC)")
    # ── 세계 ──────────────────────────────────────────────────
    t["세.Δ1800"] = J.get("🔴 Δ(1800)")
    t["세.Δ천장"] = J.get("🔴 Δ(천장)")
    t["세.SE천장"] = J.get("🔴 Δ(천장) 짝 SE")
    t["세.비"] = J.get("🔴 Δ(천장) / SE_짝")
    t["세.천장예산"] = J.get("🔴 천장 예산")
    t["세.Nstar"] = J.get("🔴 교차 예산 N*")
    t["세.Nstar창"] = J.get("🔴 N* 가 [1800, 6400) 안인가")
    t["세.양수도메인"] = J.get("🔴 천장에서 Δ_d > 0 인 도메인 수")
    t["세.도메인수"] = J.get("🔴 게이트 도메인 수")
    t["세.균등Δ"] = J.get("🔴🔴 도메인 «균등» Δ(천장)")
    t["세.균등SE"] = J.get("🔴🔴 도메인 균등 Δ 짝 SE")
    t["세.균등비"] = J.get("🔴🔴 도메인 균등 Δ / SE")
    t["세.큰도메인"] = J.get("🔴🔴🔴 가장 큰 도메인")
    t["세.큰몫"] = J.get("🔴🔴🔴 그 도메인의 유보 몫")
    t["세.큰Δ"] = J.get("🔴🔴🔴 그 도메인의 Δ_d")
    t["세.문턱넘음"] = J.get("🔴 Δ(천장) 이 문턱 0.00353 을 넘나")
    t["세.노트133"] = J.get("🔴🔴 노트 133 — 이 자를 넘었나")
    t["세.부호뒤집힘"] = J.get("🔴🔴🔴 부호가 뒤집혔나")
    t["세.u3Δ"] = J.get("🔴 병기: u = 3 의 Δ(천장)")
    t["세.u3Nstar"] = J.get("🔴 병기: u = 3 의 N*")
    t["깔.디스크"] = F.get("① 디스크(hplt shard 행)")
    t["깔.삼중쌍"] = F.get("② 삼중쌍으로 산 hplt 행")
    t["깔.base"] = F.get("③ base 삼중쌍 행(= 유보 전량)")
    t["깔.모형"] = F.get("④ 977 예산 상수가 학습에 넣은 hplt 행")
    t["깔.H천장"] = F.get("🔴 팔 H 의 «자료» 천장(겹당)")
    t["깔.B천장"] = F.get("🔴 팔 B 의 «자료» 천장(겹당)")
    for k in ("sao941", "sao959", "hplt_ko"):
        t["자료.%s.바이트" % k] = _dig(ws, k, "바이트")
        t["자료.%s.sha" % k] = _dig(ws, k, "sha256")
        t["자료.%s.경로" % k] = _dig(ws, k, "경로")
    t["세.씨앗수"] = len(_dig(W, "🔴 자", "씨앗") or [])
    t["세.눈금수"] = len(_dig(W, "🔴 자", "예산 눈금") or [])
    t["세.유보합"] = _dig(W, "🔴 자", "게이트 유보 행 합")
    t["세.Δ6400"] = _dig(lad, "6400", "🔴🔴🔴 Δ = ρ_H − ρ_B")
    t["세.Δ4800"] = _dig(lad, "4800", "🔴🔴🔴 Δ = ρ_H − ρ_B")
    t["세.H1800"] = _dig(lad, "1800", "🔴 팔 H 묶음 ρ")
    t["세.B1800"] = _dig(lad, "1800", "🔴 팔 B 묶음 ρ")
    t["세.H천장ρ"] = _dig(lad, str(t["세.천장예산"]), "🔴 팔 H 묶음 ρ")
    t["세.B천장ρ"] = _dig(lad, str(t["세.천장예산"]), "🔴 팔 B 묶음 ρ")
    # ── 자기 자 ────────────────────────────────────────────────
    t["자.987교체"] = idA.get("🔴🔴🔴 판정식 교체 수")
    t["자.987개명"] = idA.get("🔴🔴 라벨 개명 수")
    t["자.987걸린"] = idA.get("🔴🔴🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)")
    t["자.988교체"] = idB.get("🔴 988 에서 판정식 교체 수")
    t["자.988걸린"] = idB.get("🔴🔴🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)")
    t["자.988분자ⓐ"] = reC.get("🔴🔴 ⓐ 988 이 적은 분자 / 분모")
    t["자.988분자ⓑ"] = reC.get("🔴🔴 ⓑ 경로 동일성만 물린 분자 / 분모(= 티처 #127 이 준 수)")
    t["자.988분자ⓒ"] = reC.get("🔴🔴🔴 ⓒ 경로 동일성 + `조항 72-라` 를 물린 분자 / 분모")
    t["자.미측정989"] = rec.get("🔴🔴🔴 989 가 다시 센 「미측정」 수")
    t["자.미측정988"] = rec.get("🔴🔴 988 이 적은 「미측정」 수")
    t["자.훑은칸"] = rec.get("🔴 훑은 칸 수")
    t["자.통과절수"] = dsec.get("🔴🔴🔴 `통과` 키를 내는 절 수(자동 · 손으로 안 골랐다)")
    t["단.988발화"] = _dig(ctlR, old_neg, "🔴 `|스피어만| = 1` 인 짝")
    t["단.988분모"] = _dig(ctlR, old_neg, "🔴 짝 수(분모)")
    t["단.치환발화"] = _dig(ctlR, perm, "🔴 `|스피어만| = 1` 인 짝")
    t["단.U발화"] = _dig(ctlR, ushape, "🔴 `|스피어만| = 1` 인 짝")
    t["단.988평균ρ"] = E.get("🔴 988 음성 대조의 평균 스피어만")
    t["단.복제수"] = E.get("🔴 쓸 수 있는 복제 수")
    t["단.등록발화계열수"] = len(E.get("🔴🔴🔴 등록 문안으로 발화한 계열") or [])
    t["단.988발화계열수"] = len(E.get("🔴 988 구현으로 발화한 계열") or [])
    t["세계.연경로수"] = Gg.get("🔴🔴🔴 ㉠ 런타임 경로 수")
    t["세계.정적경로수"] = Gg.get("🔴 ㉠ 정적 경로 수")
    t["세계.인용문장수"] = Gg.get("🔴🔴🔴 ㉡ 세계 자료를 인용한 주장 문장 수")
    t["채.반증분모"] = fal.get("🔴 분모")
    t["채.반증분자"] = fal.get("🔴🔴 분자 / 분모")
    t["채.반증된"] = fal.get("🔴🔴 반증된 조건(식별자만)")
    t["채.예측분자"] = prd.get("🔴🔴 분자 / 분모")
    t["채.최상위"] = S.get("통과")
    t["채.F09"] = L.get("🔴🔴🔴 F09 반증됐나")
    t["채.F09걸린"] = L.get("🔴 걸린 자리(= 비교를 «수행»한 회수)")
    t["배.통과"] = G.get("통과")
    t["배.검사수"] = G.get("🔴 배선 검사 수")
    t["배.통과수"] = G.get("🔴 통과 수")
    t["배.구성상참"] = G.get("🔴 구성상 참인 검사 수(변이체가 안 떨어진 것)")
    t["배.977재현차"] = _dig(G, "🔴 977 재현", "🔴 차이")
    t["배.977공표"] = _dig(G, "🔴 977 재현", "🔴 977 이 공표한 값")
    t["배.977재현값"] = _dig(G, "🔴 977 재현", "🔴 989 가 다시 낸 값")
    for r in ("runners/world989.py", "runners/audit989.py", "runners/score989.py",
              "runners/last989.py", "runners/note989_gen.py"):
        t["sha.%s" % Path(r).name] = _sha(r)
    t["절통과"] = json.dumps(_dig(S, "🔴🔴🔴 최상위를 이루는 절의 `통과` 전량") or {},
                          ensure_ascii=False)
    return t


SLOT = re.compile(r"\{\{([^}]+)\}\}")


def render(tpl, t):
    def rep(m):
        k = m.group(1).strip()
        if k not in t:
            raise SystemExit("🔴 치환표에 없는 슬롯: %s" % k)
        v = t[k]
        return "없음" if v is None else (
            json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict))
            else str(v))
    return SLOT.sub(rep, tpl)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="docs", choices=("docs", "card"))
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    t = table(a.ref)
    (OUT / "out989_table.json").write_text(
        json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.stage == "docs":
        for name in ("판정_989", "card_989", "handoff_989", "pr_989"):
            tp = DOCS / "tpl" / ("%s.md.tpl" % name)
            if not tp.is_file():
                continue
            (DOCS / ("%s.md" % name)).write_text(
                render(tp.read_text(encoding="utf-8"), t), encoding="utf-8")
    else:
        # 🔴 «치환»이지 «덧붙임»이 아니다 --- 표지 구획만 갈아 끼운다
        body = (DOCS / "handoff_989.md").read_text(encoding="utf-8")
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        head = ("<!-- 989:인계:시작 -->\n"
                "## 🔴🔴🔴 지금 여기부터 — **노트 989 가 끝났다**\n\n"
                "> 🔴🔴🔴 **아래는 `docs/handoff_989.md` 를 «바이트로» 옮긴 것이다.**\n"
                "> `sha256 = %s`\n"
                "> 🔴 **손으로 안 썼다** --- `runners/note989_gen.py --stage card` 가 옮겼다.\n\n"
                "%s\n<!-- 989:인계:끝 -->\n" % (sha, body))
        cur = CARD.read_text(encoding="utf-8") if CARD.is_file() else ""
        pat = re.compile(r"<!-- 989:인계:시작 -->.*?<!-- 989:인계:끝 -->\n?", re.S)
        cur = pat.sub("", cur)
        i = cur.index("\n") + 1 if "\n" in cur else 0
        CARD.write_text(cur[:i] + "\n" + head + "\n" + cur[i:], encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
