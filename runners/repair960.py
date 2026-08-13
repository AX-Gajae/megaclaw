# -*- coding: utf-8 -*-
"""노트 960 [수리 회계] — 🔴 **고쳤다고 말하지 않는다. 고친 것을 돌려서 보인다.**

사전등록 `docs/prereg_960_cluster.md` §8 이 **수리 상한 6** 과 「어느 지시가 시켰나」를
측정 **전에** 적었다. 이 러너가 그 여섯을 하나씩 검사한다.

🔴 **조항 62**: 「생산기가 찍었다」는 경로를 보증하지 분자를 보증하지 않는다.
그래서 수리 1·2 는 **모래상자에서 실제로 돌려** 옛 행이 살아남는지 확인한다
(HTTP 0 — `fetch`/`page` 를 그루터기로 갈아 끼운다).

    python3 runners/repair960.py
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))

OUT = ROOT / "runners/out960_repair.json"


# ── 수리 1 — grow959.cmd_harvest 이어싣기 ───────────────────────────────────
def r1_grow959() -> dict:
    """🔴 모래상자에서 **부분 주행 + 실패 한 건**을 돌려 옛 행이 사는지 본다."""
    import runners.grow959 as G
    from ingest import wikidaily941 as W

    tmp = Path(tempfile.mkdtemp(prefix="r960_grow_"))
    old_out, old_root, old_tw, old_fetch = G.OUTDIR, G.ROOT, G.targets_wide, W.fetch
    try:
        G.OUTDIR = tmp / "wiki"
        G.ROOT = tmp
        (tmp / "runners").mkdir(parents=True, exist_ok=True)
        G.OUTDIR.mkdir(parents=True, exist_ok=True)
        # 옛 파일 — 개체 셋
        with gzip.open(G.OUTDIR / "게임.jsonl.gz", "wt", encoding="utf-8") as f:
            for k in ("GM-1", "GM-2", "GM-3"):
                f.write(json.dumps({"키": k, "도메인": "게임", "문서": k, "언어": "ko",
                                    "시작일": "2025-01-01", "첫날": "20250101",
                                    "끝날": "20250103", "일수": 3,
                                    "날짜": [20250101, 20250102, 20250103],
                                    "조회수": [1, 1, 1], "옛것": True},
                                   ensure_ascii=False) + "\n")

        tg = [{"도메인": "게임", "키": k, "문서": k, "언어": "ko", "시작일": "2025-01-01"}
              for k in ("GM-1", "GM-2", "GM-3")]
        G.targets_wide = lambda: (list(tg), {"🔴 넓힌 표적": 3})

        def stub(lang, doc, hi):
            """GM-1 만 성공 · GM-2 는 실패(timeout). 🔴 HTTP 0."""
            if doc == "GM-1":
                return [("20250401", 9), ("20250402", 9)], None
            return None, "timeout"
        W.fetch = stub

        a = argparse.Namespace(limit=None, sleep=0.0, workers=1,
                               keys="GM-1,GM-2", no_merge=False)
        R = G.cmd_harvest(a)
        rows = [json.loads(l) for l in
                gzip.open(G.OUTDIR / "게임.jsonl.gz", "rt", encoding="utf-8")]
        by = {r["키"]: r for r in rows}
        part = (tmp / "runners/out959_harvest_part.json").exists()
        full = (tmp / "runners/out959_harvest.json").exists()
        return {
            "🔴 무엇을 고쳤나": ("`cmd_harvest` 가 도메인 파일을 통째로 다시 써서 "
                          "**못 받은 키의 옛 행이 죽었다**. 지금 37건이 timeout 실패라 "
                          "다시 돌리면 그 37개가 사라진다(티처 #98 치명 ⑨)"),
            "모래상자": str(tmp),
            "표적": "GM-1(성공) · GM-2(실패) · GM-3(요청 안 함)",
            "파일 안의 키": sorted(by),
            "GM-1 이 새것인가": "옛것" not in by.get("GM-1", {}),
            "🔴 GM-2(실패)의 옛 행이 살았나": by.get("GM-2", {}).get("옛것") is True,
            "🔴 GM-3(미요청)의 옛 행이 살았나": by.get("GM-3", {}).get("옛것") is True,
            "이어실은 옛 개체": R.get("🔴 이어실은 옛 개체"),
            "부분 주행인가": R.get("🔴 부분 주행인가"),
            "🔴 집계가 별 파일로 갔나": {"부분 파일": part, "전량 파일을 안 덮었나": not full},
            "통과": bool(len(by) == 3 and by.get("GM-2", {}).get("옛것") is True
                       and by.get("GM-3", {}).get("옛것") is True
                       and "옛것" not in by.get("GM-1", {})
                       and part and not full),
        }
    finally:
        G.OUTDIR, G.ROOT, G.targets_wide = old_out, old_root, old_tw
        W.fetch = old_fetch


# ── 수리 2 — steamrev941 부분 주행 ──────────────────────────────────────────
def r2_steamrev() -> dict:
    from ingest import steamrev941 as S

    tmp = Path(tempfile.mkdtemp(prefix="r960_steam_"))
    old_out, old_root, old_tg, old_page, old_argv = (
        S.OUTDIR, S.ROOT, S.targets, S.page, list(sys.argv))
    try:
        S.OUTDIR = tmp / "steam"
        S.ROOT = tmp
        S.OUTDIR.mkdir(parents=True, exist_ok=True)
        (tmp / "runners").mkdir(parents=True, exist_ok=True)
        with gzip.open(S.OUTDIR / "reviews.jsonl.gz", "wt", encoding="utf-8") as f:
            for k in ("GAME-1", "GAME-2"):
                f.write(json.dumps({"키": k, "appid": k[-1], "id": "x",
                                    "본문": "옛 리뷰", "옛것": True},
                                   ensure_ascii=False) + "\n")
        S.targets = lambda holdout_only=False: (
            [("GAME-1", "1")] if holdout_only else [("GAME-1", "1"), ("GAME-2", "2")])
        S.page = lambda app, cur: ({"reviews": [
            {"recommendationid": "n", "review": "새 리뷰", "timestamp_created": 1,
             "timestamp_updated": 1, "voted_up": True, "language": "korean",
             "votes_up": 0, "weighted_vote_score": 0, "steam_purchase": True,
             "author": {"playtime_at_review": 1}}]}, None)
        sys.argv = ["steamrev941", "--holdout-only", "--pages", "1", "--sleep", "0"]
        res = S.main()
        rows = [json.loads(l) for l in
                gzip.open(S.OUTDIR / "reviews.jsonl.gz", "rt", encoding="utf-8")]
        keys = {r["키"] for r in rows}
        part = (tmp / "runners/out941_steamrev_part.json").exists()
        full = (tmp / "runners/out941_steamrev.json").exists()
        return {
            "🔴 무엇을 고쳤나": ("`--holdout-only` 는 **부분집합**을 받는데 최종 파일을 "
                          "그 부분집합으로 통째로 갈아 끼웠다 — 941 형제 · 미수리였다"),
            "모래상자": str(tmp),
            "파일 안의 키": sorted(keys),
            "🔴 GAME-2(미요청)의 옛 행이 살았나": any(
                r["키"] == "GAME-2" and r.get("옛것") for r in rows),
            "이어실은 옛 행": res.get("🔴 이어실은 옛 행"),
            "부분 주행인가": res.get("🔴 부분 주행인가"),
            "🔴 집계가 별 파일로 갔나": {"부분 파일": part, "전량 파일을 안 덮었나": not full},
            "통과": bool(keys == {"GAME-1", "GAME-2"} and part and not full
                       and any(r["키"] == "GAME-2" and r.get("옛것") for r in rows)),
        }
    finally:
        S.OUTDIR, S.ROOT, S.targets, S.page = old_out, old_root, old_tg, old_page
        sys.argv = old_argv


# ── 수리 3 — verify_market 원자적 쓰기 ──────────────────────────────────────
def r3_verify_market() -> dict:
    """🔴 이 러너는 HTTP 를 도니 **모래상자에서도 안 돌린다.** 코드로 확인한다."""
    src = (ROOT / "ingest/verify_market.py").read_text()
    # 🔴 **글자로 찾으면 거짓 붉음이 난다** — 959 의 W2 가 바로 그렇게 자기 독스트링에 걸렸다.
    #    그래서 **파싱해서 실행되는 호출만** 본다(주석·독스트링은 AST 에 안 남는다).
    import ast as _ast
    bad_calls = []
    for node in _ast.walk(_ast.parse(src)):
        if not (isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name)
                and node.func.id == "open" and len(node.args) >= 2):
            continue
        tgt = node.args[0]
        mode = node.args[1]
        name = tgt.id if isinstance(tgt, _ast.Name) else None
        mv = mode.value if isinstance(mode, _ast.Constant) else None
        if name == "OUT" and isinstance(mv, str) and "w" in mv:
            bad_calls.append(node.lineno)
    return {
        "🔴 무엇을 고쳤나": ("`out = open(OUT, \"w\")` 가 **여는 순간 자르고**, 그 손잡이를 쥔 채 "
                      "수백 번의 HTTP 요청을 돈다. 중간에 죽으면 옛 결과가 통째로 사라진다"),
        "🔴 자": "AST 로 **실행되는 호출**만 본다 — 글자 grep 은 주석에 걸려 거짓 붉음을 낸다(959 W2)",
        "옛 꼴 `open(OUT, \"w\")` 가 실행부에 남았나": bool(bad_calls),
        "걸린 줄": bad_calls,
        "⚠ 글자로만 세면": src.count('open(OUT, "w")'),
        "`.part` 에 쓰나": "_part" in src and 'open(_part, "w")' in src,
        "`os.replace` 로 갈아 끼우나": "_os.replace(_part, _final)" in src,
        "🔴 다시 열어 세나": "🔴 다시 열어 센 줄" in src,
        "⚠ 왜 안 돌렸나": "이 러너는 수백 개의 외부 URL 을 받는다 — 사전등록 §7 이 HTTP 0 을 걸었다",
        "통과": bool(not bad_calls and "_os.replace(_part, _final)" in src),
    }


# ── 수리 4 — out941_wikidaily.json 복구 ─────────────────────────────────────
def r4_restore() -> dict:
    live = ROOT / "runners/out941_wikidaily.json"
    frz = ROOT / "data/frozen/959_out941_pre/out941_wikidaily.json"
    a = hashlib.sha256(live.read_bytes()).hexdigest()
    b = hashlib.sha256(frz.read_bytes()).hexdigest()
    d = json.loads(live.read_text())
    return {
        "🔴 무엇을 고쳤나": ("959 의 수리 ⑤가 `--keys` 5키 주행으로 이 파일을 "
                      "「요청 5 · 3도메인 · 10,001행」으로 파괴했다 — "
                      "**논문 502 가 인용하는 「815 중 810」의 유일한 출처**였다"),
        "live sha256": a, "frozen sha256": b, "같나": a == b,
        "요청 수": d.get("요청 수"), "성공": d.get("성공"), "실패": d.get("실패"),
        "행 합": d.get("행(개체×일) 합"), "도메인 수": len(d.get("도메인별", {})),
        "통과": bool(a == b and d.get("요청 수") == 815 and d.get("성공") == 810),
    }


# ── 수리 5 — 논문 501 을 main 으로 ─────────────────────────────────────────
def r5_paper501() -> dict:
    step = ROOT / "paper/steps/501_retraction"
    led = json.loads((ROOT / "paper/ledger.json").read_text())
    ns = [s["n"] for s in led["steps"]]
    e500 = next((s for s in led["steps"] if s["n"] == 500), {})
    e501 = next((s for s in led["steps"] if s["n"] == 501), {})
    pr = subprocess.run(["gh", "pr", "view", "216", "--json", "state,mergeable"],
                        capture_output=True, text=True)
    return {
        "🔴 무엇을 고쳤나": ("`ledger[500]` 이 **없는 501** 을 가리키고 전송 완료된 502 가 "
                      "**없는 501** 을 정정했다 — 원장에 구멍이 뚫린 채 논문 둘이 나갔다"),
        "스텝 디렉터리가 main 에 있나": step.exists(),
        "파일": sorted(p.name for p in step.glob("*")) if step.exists() else [],
        "🔴 ledger 에 501 이 있나": 501 in ns,
        "🔴 ledger 순서": ns[-4:],
        "500 → 501 포인터": e500.get("철회 스텝"),
        "501 → 500 포인터": e501.get("🔴 정정 대상"),
        "🔴 왜 머지가 아니라 이관인가": (
            "PR #216 은 `data/ingest/wiki_daily/*` 등 **옛 자료 파일 30여 개**를 같이 들고 있다. "
            "머지하면 자료가 뒤로 감길 위험이 있고 그것이 티처 #97 F2 가 데인 자리다. "
            "**#216 은 열어 둔다** — 그 가지의 `out958_within.json` 은 아직 `채택=true` 를 담고 있고, "
            "🔴 **머지 전에 `within958.py` 를 `lab.adopt.adopt` 에 배선해야 한다**"),
        "PR #216 상태": (json.loads(pr.stdout).get("state") if pr.returncode == 0
                       else f"🔴 못 읽었다: {pr.stderr.strip()[:120]}"),
        "통과": bool(step.exists() and 501 in ns
                   and e501.get("🔴 정정 대상") == 500),
    }


# ── 수리 6 — 죽은 수 · 틀린 수 ─────────────────────────────────────────────
def r6_numbers() -> dict:
    post = json.loads((ROOT / "runners/out960_post.json").read_text())
    den = post["다 · 「815 중 810」의 네 분모 — 실측"]
    d3 = json.loads((ROOT / "runners/out959_d3.json").read_text())
    # Q7 재채점 — 959 의 사전등록 Q7 은 「0% 도 100% 도 아니다」였다.
    # 🔴 **959 는 그것을 `or` 로 채점했다**: 정본 ㉯ 가 정확히 1.0(= 배제된 값)인데
    #    ㉮ 0.5417 을 같이 실어 「맞았다」로 넘겼다. **정본 하나로 채점한다.**
    S7 = d3["§7 부트 설계 둘 × 씨앗 24"]
    canon = S7["㉯"]["🔴 씨앗 비율"]
    alt = S7["㉮"]["🔴 씨앗 비율"]
    q7 = bool(canon not in (0.0, 1.0))
    scored = d3["🔴 예측 채점"]["Q7 씨앗 비율이 0% 도 100% 도 아니다"]["맞았나"]
    return {
        "🔴 무엇을 고쳤나": "「815 중 810」이 한 분모처럼 쓰였다. **네 개의 다른 수다**(티처 #98 중대 ①)",
        "① targets() 행": den["① targets() 가 낸 **행**"],
        "② distinct 키": den["② 그중 **distinct 키**"],
        "③ 주행 성공": den["③ 그 주행의 **성공 건수**(out941_wikidaily)"],
        "④ 파일 개체": den["④ 살아 있는 파일의 **개체 수**"],
        "🔴 중복 키": den["🔴 중복 키"],
        "🔴 파일 줄 수 합": sum(den["파일별 줄 수"].values()),
        "🔴 줄 − 개체": sum(den["파일별 줄 수"].values()) - den["④ 살아 있는 파일의 **개체 수**"],
        "🔴 새로 잡은 것": ("살아 있는 파일에 **같은 키가 두 번 실린 행이 2개** 있다 — "
                     "`targets()` 가 815행/813키라 중복 키를 두 번 받아 두 번 썼다"),
        "🔴 959 의 「808 → 815」": f"실측 808 → {den['② 그중 **distinct 키**']}",
        "Q7 재채점": {
            "959 의 사전등록 Q7": "「T 를 넘는 씨앗 비율」이 0% 도 100% 도 아니다",
            "정본 ㉯ 비율": canon, "958 설계 ㉮ 비율": alt,
            "959 가 찍은 채점": scored, "🔴 정본으로 채점하면": q7,
            "🔴 뒤집혔나": bool(scored != q7),
            "🔴 959 가 쓴 방식": "㉮ 54.2% 를 `or` 로 끌어와 살렸다 — 정본 ㉯ 는 정확히 100% 다",
            "🔴 다시 센 예측 계수": "9 중 6 이 아니라 **9 중 5**"},
        "통과": bool(den["② 그중 **distinct 키**"] == 813 and q7 is False),
    }


def main() -> dict:
    t0 = time.time()
    R = {"노트": 960, "레인": "수리",
         "사전등록": "docs/prereg_960_cluster.md §8 (수리 상한 6 · 측정 전 선언)",
         "🔴 예고한 수리": 6, "🔴 상한": 6}
    fns = [("1 grow959.cmd_harvest 이어싣기", r1_grow959),
           ("2 steamrev941 부분 주행", r2_steamrev),
           ("3 verify_market 원자적 쓰기", r3_verify_market),
           ("4 out941_wikidaily.json 복구", r4_restore),
           ("5 논문 501 을 main 으로", r5_paper501),
           ("6 죽은 수 · 틀린 수", r6_numbers)]
    for name, fn in fns:
        try:
            R[name] = fn()
        except Exception as e:                                   # noqa: BLE001
            R[name] = {"🔴 터졌다": f"{type(e).__name__}: {e}", "통과": False}
    R["🔴 수리 회계"] = {
        "분자: 통과": sum(1 for k, v in R.items()
                     if isinstance(v, dict) and v.get("통과") is True),
        "분모: 예고 == 상한": 6,
        "붉은 것": [k for k, v in R.items()
                 if isinstance(v, dict) and v.get("통과") is not True and "통과" in v]}
    R["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    return R


if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=1)[:8000])
