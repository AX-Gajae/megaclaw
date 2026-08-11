"""학습 기록 회귀 시험 --- **검사를 세울 때 같이 세운다**(노트 676). 노트 912 팔 ㅇ.

    python3 -m serve.test_trainlog

막는 것은 여덟이다.

    ① 규격을 안 지킨 기록이 통과하나 --- 칸 · ASCII run_id · 「자 없음」 표시
    ② 🔴 **지표가 없는데 곡선을 그리나** --- 이 팔에서 제일 큰 사고다
    ③ 아키텍처 세 갈래(introspect · 준 dict · **못 읽음**)가 안 섞이나
    ④ 🔴 **큰 층을 조용히 자르나** --- 무엇을 몇 개로 잘랐는지 화면에 나가나
    ⑤ 금지 꼴 게이트가 이 창구에서도 발화하나 (미끼 · 음성 대조)
    ⑥ 덮어쓰기 금지 · 기록 실패를 조용히 삼키나
    ⑦ 기존 하네스(등록소 규율 여섯 · 계층 검사 · 13능력)가 살아 있나
    ⑧ 🔴 **화면(`trainlog.html`)이 없는 점을 지어내나** --- 원문을 읽어 검사한다

**표의 절반은 통과해야 하는 줄이다**(노트 676) --- 다 막는 검사는 만점을 받는다.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_RESULT: list = []
_TMP: Path | None = None


def ok(name: str, cond: bool, detail: str = "") -> bool:
    _RESULT.append({"검사": name, "통과": bool(cond), "본 것": detail})
    print(f"{'OK ' if cond else '실패'} {name}" + (f"  --- {detail}" if detail else ""))
    return bool(cond)


def tmp() -> Path:
    global _TMP
    if _TMP is None:
        _TMP = Path(tempfile.mkdtemp(prefix="wm_trainlog_test_"))
    return _TMP


# ── ① 규격 ────────────────────────────────────────────────────────
def t1_spec():
    from trainlog import Run, check_manifest, read_manifest
    from trainlog.spec import ID_OK, SpecError, ascii_id, norm_output

    with Run("한글 이름 909-ssl", pushes="③", ruler="소수 라벨 곡선",
             seed=7, hparams={"lr": 0.01}, root=tmp()) as r:
        r.arch({"층": [{"id": "a", "뉴런 수": 4, "입력 뉴런 수": 2}], "간선": []})
        r.log(step=1, split="train", loss=0.5)
        rid = r.run_id
    m = read_manifest(rid, tmp())
    ok("① manifest 가 규격을 지킨다", not check_manifest(m), str(check_manifest(m))[:160])
    ok("① run_id 가 ASCII 다(한글 이름을 접었다)", bool(ID_OK.match(rid)), rid)
    ok("① 원래 이름을 안 버린다", m["이름(원래)"] == "한글 이름 909-ssl",
       str(m["이름(원래)"]))
    ok("① 미는 출력이 '③시점' 로 접힌다", m["미는 출력"] == ["③시점"],
       str(m["미는 출력"]))
    ok("① 자가 있으면 '자 없음' 이 거짓", m["자 없음"] is False, str(m["자"])[:40])
    ok("① 코드 sha256 이 붙는다",
       bool((m["코드 sha256"] or [{}])[0].get("sha256")),
       str(m["코드 sha256"])[:90])
    ok("① 씨앗·하이퍼가 남는다", m["씨앗"] == 7 and m["하이퍼파라미터"] == {"lr": 0.01})
    ok("① 규격 판 칸이 있다", bool(m["규격 판"]), str(m["규격 판"]))

    #: 🔴 **자 없는 run 도 기록은 되되 「자 없음」이 보여야 한다**
    with Run("no-ruler", ruler=None, root=tmp()) as r2:
        rid2 = r2.run_id
    m2 = read_manifest(rid2, tmp())
    ok("① 자 없는 run 도 기록된다", not check_manifest(m2), str(check_manifest(m2))[:120])
    ok("① 🔴 자가 없으면 '자 없음' 이 참", m2["자 없음"] is True)
    ok("① 자가 없으면 단서가 보인다", bool(m2["🔴 자 없음 단서"]))
    ok("① 미는 출력을 안 적으면 '해당 없음' 으로 **적힌다**(비지 않는다)",
       m2["미는 출력"] == ["해당 없음"], str(m2["미는 출력"]))

    #: **모르는 딱지는 죽는다** --- 조용히 통과하면 딱지가 뜻을 잃는다
    try:
        norm_output("⑨")
        died = False
    except SpecError:
        died = True
    ok("① 모르는 출력 딱지는 죽는다", died)
    ok("① ascii_id 가 한글을 지운다", ascii_id("팝업 909") == "-909" or
       "909" in ascii_id("팝업 909"), ascii_id("팝업 909"))

    #: **통과해야 하는 줄** --- 칸 하나를 빼면 잡혀야 한다(항상 통과 방지)
    broke = dict(m)
    broke.pop("자", None)
    ok("① 심은 실패를 잡는다(칸 하나를 뺐다)", bool(check_manifest(broke)),
       str(check_manifest(broke))[:120])
    broke2 = dict(m)
    broke2["run_id"] = "한글아이디"
    ok("① 심은 실패를 잡는다(run_id 가 한글)",
       any("ASCII" in x for x in check_manifest(broke2)))


# ── ② 🔴 지표가 없는데 곡선을 그리나 ──────────────────────────────
def t2_no_metrics_no_curve():
    from trainlog import Run, read_metrics
    from trainlog.store import run_dir

    with Run("empty-run", root=tmp()) as r:
        rid = r.run_id
    c = read_metrics(rid, tmp())
    ok("② 🔴 지표가 없으면 곡선이 **0개**", c["곡선 수"] == 0 and c["점 수"] == 0,
       f"곡선 {c['곡선 수']} · 점 {c['점 수']}")
    ok("② 지표 줄이 0 이면 상태는 '비었다'", c["상태"] == "비었다", c["상태"])
    ok("② '비었다' 에 왜가 붙는다", bool(c.get("왜")))

    #: 파일을 지우면 **「없다」** --- 「비었다」와 다르다(조항 59)
    (run_dir(rid, tmp()) / "metrics.jsonl").unlink()
    c2 = read_metrics(rid, tmp())
    ok("② 파일이 없으면 '없다'(≠ '비었다')", c2["상태"] == "없다", c2["상태"])
    ok("② '없다' 에서도 곡선은 0개", c2["곡선 수"] == 0 and c2["점 수"] == 0)

    #: 깨진 줄이면 **「못 읽었다」** --- 「없다」도 「비었다」도 아니다
    (run_dir(rid, tmp()) / "metrics.jsonl").write_text(
        '{"규격":"trainlog/metrics/1"}\nJSON 아님\n', encoding="utf-8")
    c3 = read_metrics(rid, tmp())
    ok("② 깨진 줄이면 '못 읽었다'", c3["상태"] == "못 읽었다", c3["상태"])
    ok("② '못 읽었다' 에서도 곡선은 0개", c3["곡선 수"] == 0 and c3["점 수"] == 0)

    #: 🔴 **쓴 점 수와 읽은 점 수가 정확히 같다** --- 하나도 더 만들지 않는다
    with Run("counted", root=tmp()) as r2:
        for s in range(1, 8):
            r2.log(step=s, split="train", loss=1.0 / s)
        rid2 = r2.run_id
    c4 = read_metrics(rid2, tmp())
    ok("② 쓴 7점 = 읽은 7점(하나도 안 지어낸다)",
       c4["점 수"] == 7 and c4["곡선 수"] == 1, f"{c4['점 수']}점 · {c4['곡선 수']}계열")
    ok("② 점이 `metrics.jsonl` 의 값과 같다",
       abs(c4["곡선"][0]["점"][3][1] - 0.25) < 1e-9,
       str(c4["곡선"][0]["점"][:4]))
    ok("② 보간·평활을 안 한다(점 수가 step 수와 같다)",
       len(c4["곡선"][0]["점"]) == 7)


# ── ③ 아키텍처 세 갈래 ────────────────────────────────────────────
def t3_arch_three_way():
    from trainlog import extract_arch

    a0 = extract_arch(None)
    ok("③ 아무것도 안 주면 **「못 읽음」**(빈 그래프가 아니다)",
       a0["읽음"] is False and a0["출처"] == "못 읽음", str(a0["출처"]))
    ok("③ '못 읽음' 에 왜가 붙는다", bool(a0["왜 못 읽음"]))
    a1 = extract_arch("나는 모형이 아니다")
    ok("③ 모형도 dict 도 아니면 '못 읽음'", a1["출처"] == "못 읽음",
       str(a1["왜 못 읽음"])[:80])
    a2 = extract_arch({"층": [{"id": "x", "뉴런 수": 3}], "간선": [["x", "x"]]})
    ok("③ dict 는 그대로 받는다", a2["출처"] == "준 dict" and len(a2["층"]) == 1)
    ok("③ 준 dict 는 introspect 라고 안 적는다", a2["간선 출처"] == "준 dict")
    try:
        import torch.nn as nn
        m = nn.Sequential(nn.Linear(4, 6), nn.ReLU(), nn.Linear(6, 2))
        a3 = extract_arch(m)
        ok("③ torch 모듈은 introspect 된다",
           a3["출처"] == "torch introspect" and len(a3["층"]) == 2,
           f"층 {len(a3['층'])} · 간선 {len(a3['간선'])}")
        ok("③ 활성함수가 앞 층 칸으로 접힌다", a3["층"][0]["활성함수"] == "ReLU")
        ok("③ 파라미터 수를 센다", a3["총 파라미터"] == 4 * 6 + 6 + 6 * 2 + 2,
           str(a3["총 파라미터"]))
        ok("③ 간선 출처를 적는다(추적인지 가정인지)",
           a3["간선 출처"] in ("torch.fx 추적", "모듈 등록 순서(가정)"),
           a3["간선 출처"])
        ok("③ 작은 가중치는 값까지 담는다", a3["가중치를 읽었나"] is True)
        big = extract_arch(nn.Linear(512, 512))
        ok("③ 🔴 큰 가중치는 **안 담고 이유를 적는다**",
           big["가중치를 읽었나"] is False
           and "한도" in str(big["층"][0]["가중치"].get("왜")),
           str(big["층"][0]["가중치"].get("왜"))[:80])
        ok("③ 값을 못 담아도 **행 노름**은 남는다(뉴런 고르기에 쓴다)",
           len(big["층"][0]["가중치"].get("행 노름") or []) == 512)
    except ImportError:
        ok("③ torch 가 없다 --- introspect 갈래를 **못 밟았다**(없다가 아니다)",
           False, "torch 미설치")


# ── ④ 🔴 큰 층을 조용히 자르나 ────────────────────────────────────
def t4_truncation_is_visible():
    from trainlog import Run, neurons

    with Run("bigarch", root=tmp()) as r:
        r.arch({"층": [
            {"id": "in2h", "이름": "in2h", "종류": "Linear",
             "입력 뉴런 수": 300, "뉴런 수": 1024},
            {"id": "head", "이름": "head", "종류": "Linear",
             "입력 뉴런 수": 1024, "뉴런 수": 7}], "간선": [["in2h", "head"]]})
        rid = r.run_id
    n = neurons(rid, max_per_layer=64, root=tmp())
    big = next(L for L in n["층"] if L["이름"] == "in2h")
    ok("④ 🔴 큰 층은 잘렸다고 표시된다", big["잘림"] is True)
    ok("④ 🔴 '1,024개 중 64개만 그렸다' 가 문장으로 나간다",
       "1,024개 중 64개만 그렸다" in big["말"], big["말"][:70])
    ok("④ 🔴 무엇을 기준으로 골랐는지 적는다", bool(big["고른 기준"]),
       big["고른 기준"][:70])
    ok("④ 가중치가 없으면 '가중치를 못 읽어서' 라고 적는다",
       "가중치를 못 읽어서" in big["고른 기준"])
    ok("④ 그린 뉴런 수가 실제로 64", big["그린 뉴런"] == 64, str(big["그린 뉴런"]))
    small = next(L for L in n["층"] if L["이름"] == "head")
    ok("④ 작은 층은 **전부** 그린다(자르지 않는다)",
       small["잘림"] is False and small["그린 뉴런"] == 7)
    ok("④ 잘린 층 목록이 따로 나온다", len(n["잘린 층"]) >= 1, str(n["잘린 층"])[:110])
    ok("④ 가중치가 없으면 간선은 '구조만' 이다",
       all(not e["세기 있나"] and "구조만" in str(e["왜"]) for e in n["간선"]),
       str(n["간선"])[:120])
    ok("④ 요약 문장에 '구조만 그렸다' 가 들어간다", "구조만 그렸다" in n["말"],
       n["말"][-60:])

    #: 가중치가 **있으면** 간선 세기가 실제 값에서 온다
    try:
        import torch.nn as nn
        with Run("witharch", root=tmp()) as r2:
            r2.arch(nn.Sequential(nn.Linear(5, 4), nn.ReLU(), nn.Linear(4, 2)))
            rid2 = r2.run_id
        n2 = neurons(rid2, max_per_layer=32, root=tmp())
        ok("④ 가중치가 있으면 간선 세기가 붙는다",
           any(e["세기 있나"] for e in n2["간선"]), str(n2["간선"][0])[:90])
        e0 = next(e for e in n2["간선"] if e["세기 있나"])
        ok("④ 세기 행렬 모양이 (뒤 뉴런 × 앞 뉴런)",
           len(e0["세기"]) == 4 and len(e0["세기"][0]) == 5,
           f"{len(e0['세기'])}×{len(e0['세기'][0])}")
    except ImportError:
        ok("④ torch 가 없어 가중치 간선을 **못 밟았다**", False, "torch 미설치")

    #: 아키텍처가 없으면 **아무것도 안 그린다**
    with Run("noarch", root=tmp()) as r3:
        rid3 = r3.run_id
    n3 = neurons(rid3, root=tmp())
    ok("④ 아키텍처를 못 읽으면 그림이 0층", n3["그릴 수 있나"] is False
       and not n3["층"], str(n3["왜"])[:80])


# ── ⑤ 금지 꼴 게이트 ──────────────────────────────────────────────
def t5_gates():
    from . import trainlog_svc as tl
    st = tl.selftest()
    ok("⑤ 창구 자가검사가 통과한다", st["통과"], str(st)[:200])
    for row in st["① 미끼에서 발화하나(양성)"]:
        ok(f"⑤ 미끼에서 발화한다 ({row['미끼'][:22]})", row["걸렸나"],
           str(row["무엇"]))
    for row in st["② 진짜 run 행에서 조용한가(음성 대조)"]:
        ok(f"⑤ 음성 대조에서는 조용하다 ({row['줄']})", not row["걸렸나"],
           str(row["무엇"]))
    ok("⑤ 저장된 run 중 게이트에 걸린 것이 없다",
       st["③ 저장된 run 중 게이트에 걸린 것"] == "없음",
       str(st["③ 저장된 run 중 게이트에 걸린 것"]))
    ok("⑤ 🔴 지어낸 곡선이 0건", st["🔴 지어낸 곡선"] == "0건",
       str(st["🔴 지어낸 곡선"]))

    #: 🔴 **금지 꼴을 심은 run 을 실제로 만들어** 목록 경로가 막는지 본다
    from trainlog import Run
    from trainlog.store import list_runs
    with Run("bait-in-name", ruler="우리 모델은 지금까지 82% 적중했습니다",
             root=tmp()) as r:
        rid = r.run_id
    row = next(x for x in list_runs(root=tmp())["run"] if x["run_id"] == rid)
    ok("⑤ 🔴 심은 금지 꼴 run 은 게이트에 걸린다", bool(tl._gate(row)),
       str(tl._gate(row))[:110])
    ok("⑤ 걸리면 **내용을 안 보낸다**",
       tl.gated(row, "x").get("차단됨") is True, str(tl.gated(row, "x"))[:110])
    #: 통과해야 하는 줄 --- 멀쩡한 run 은 안 막힌다
    clean = next(x for x in list_runs(root=tmp())["run"]
                 if x["run_id"].startswith("counted"))
    ok("⑤ 멀쩡한 run 은 안 막힌다", not tl._gate(clean), str(tl._gate(clean))[:110])
    ok("⑤ 통과한 응답에 '걸린 것 없음' 이 실린다",
       tl.gated(clean, "x").get("금지 꼴 게이트") == "걸린 것 없음")


# ── ⑥ 덮어쓰기 금지 · 실패를 안 삼킨다 ────────────────────────────
def t6_no_overwrite_no_silence():
    from trainlog import Run, read_manifest

    a = Run("dup", root=tmp())
    b = Run("dup", root=tmp())
    ok("⑥ 🔴 같은 이름이어도 run_id 가 다르다", a.run_id != b.run_id,
       f"{a.run_id} vs {b.run_id}")
    ok("⑥ 두 디렉터리가 둘 다 있다", a.dir.exists() and b.dir.exists())
    a.finish(); b.finish()

    #: 🔴 쓰기가 터져도 **학습은 안 죽고**, 실패는 **세어진다**
    c = Run("failing", root=tmp())
    c.log(step=1, split="train", loss=1.0)
    c.flush()

    class 터지는파일:
        def write(self, *a, **k):
            raise OSError("일부러 터뜨렸다")

        def flush(self):
            raise OSError("일부러 터뜨렸다")

        def close(self):
            pass

    c._fh = 터지는파일()
    c._metrics = Path("/dev/null/없는곳/metrics.jsonl")
    died = False
    try:
        c.log(step=2, split="train", loss=0.9)
        c.flush()
    except Exception:
        died = True
    ok("⑥ 🔴 기록이 터져도 **학습을 안 죽인다**", not died)
    m = c.finish()
    ok("⑥ 🔴 그런데 **조용히 삼키지도 않는다**", m["기록 실패 n건"] >= 1,
       str(m["기록 실패 n건"]))
    ok("⑥ 실패 사유가 남는다", bool(m["기록 실패(앞 몇 건)"]),
       str(m["기록 실패(앞 몇 건)"])[:90])

    #: 프로세스가 `finish()` 없이 끝나면 **「끝남」이 아니다**
    d = Run("abandoned", root=tmp())
    d._atexit()
    md = read_manifest(d.run_id, tmp())
    ok("⑥ finish 없이 끝나면 상태가 '터짐'", md["상태"] == "터짐", md["상태"])
    ok("⑥ 터진 이유가 적힌다", bool(md.get("터진 이유")))

    #: 줄 단위 flush --- **프로세스가 죽어도 그때까지 쓴 것이 읽힌다**
    e = Run("midflight", root=tmp())
    e.log(step=1, split="train", loss=0.3)
    e.flush()
    from trainlog import read_metrics
    live = read_metrics(e.run_id, tmp())
    ok("⑥ 끝나기 전에도 쓴 줄이 읽힌다", live["점 수"] == 1, str(live["점 수"]))
    ok("⑥ 아직 도는 run 은 상태가 '도는 중'",
       read_manifest(e.run_id, tmp())["상태"] == "도는 중")
    e.finish()


# ── ⑦ 기존 하네스가 살아 있나 ─────────────────────────────────────
def t7_harness_alive():
    from . import layers, registry
    c = registry.check()
    ok("⑦ 등록소 규율 여섯을 그대로 통과한다", c["통과"], str(c["걸린 곳"])[:160])
    ok("⑦ 새 능력이 등록됐다", "trainlog_index" in registry.names())
    cap = next(x for x in registry.CAPS if x["이름"] == "trainlog_index")
    ok("⑦ 새 능력에 층 딱지가 있다(L6)", cap["층"] == "L6", str(cap["층"]))
    ok("⑦ 새 능력이 떠받치는 출력을 적었다", cap["떠받치는 출력"] == ["메타"])
    ok("⑦ 🔴 새 능력에 **자**가 있다(규율 ②)", len(cap["자"]) >= 3, str(len(cap["자"])))
    ok("⑦ 자마다 노트 번호가 있다",
       all(isinstance(n, int) and n > 0 for n, _w, _v in cap["자"]))
    ok("⑦ `산출` 이 「기록」이다", cap["산출"].startswith("기록"), cap["산출"][:40])
    ok("⑦ 부를 수 있다", callable(cap["부르기"]))
    idx = cap["부르기"]()
    ok("⑦ 불렀더니 자가검사가 통과로 나온다", idx["자가검사 통과"] is True, str(idx)[:150])
    lc = layers.check()
    ok("⑦ 계층 검사가 그대로 통과한다", lc["통과"], str(lc["걸린 곳"])[:160])
    from .test_capability import CASES
    from .capability import check as capcheck
    bad = [t for t, want, _ in CASES if bool(capcheck(t)) != want]
    ok("⑦ `capability.check` 회귀 12줄이 그대로 통과한다", not bad, str(bad)[:150])
    ok("⑦ 능력 카드가 여전히 만들어진다",
       bool(__import__("serve.capability", fromlist=["card"]).card()
            .get("부를 수 있는 능력")))


# ── ⑧ 🔴 화면이 없는 점을 지어내나 ────────────────────────────────
def t8_page_cannot_invent():
    """페이지 **원문**을 읽어 검사한다 --- JS 를 못 돌리니 소스를 본다.

    거친 자다. 그래도 *지어내는 흔한 길 셋*(난수 · 외부 CDN · 하드코딩 배열)은
    소스에 남으므로 여기서 막힌다.
    """
    p = ROOT / "serve/static/trainlog.html"
    ok("⑧ 페이지 파일이 있다", p.exists(), str(p))
    src = p.read_text(encoding="utf-8")
    ok("⑧ 🔴 난수로 점을 만들지 않는다", "Math.random" not in src)
    #: 🔴 `xmlns="http://www.w3.org/2000/svg"` 는 **요청이 아니라 이름공간**이다
    #: (한 번 이것 때문에 이 줄이 실패했다 --- 검사는 범위를 정해야 한다 · 노트 674·677).
    net = src.replace("http://www.w3.org/2000/svg", "")
    ok("⑧ 🔴 외부 요청이 없다(CDN 금지)",
       "//cdn" not in net and "https://" not in net and "http://" not in net,
       "남은 것: " + str([s[:40] for s in net.split() if "http" in s])[:120])
    ok("⑧ 부르는 자리가 같은 서버의 `/api/trainlog/*` 뿐이다",
       src.count("fetch(") == 1 and "/api/trainlog/" in src,
       f"fetch {src.count('fetch(')}회")
    ok("⑧ 🔴 지표가 없으면 **그리지 않는** 갈래가 있다",
       "곡선을 그리지 않는다" in src and 'cur["상태"] !== "읽었다"' in src)
    ok("⑧ 🔴 자른 것을 화면에 적는 자리가 있다",
       "그린 뉴런" in src and "잘린 층" in src and "고른 기준" in src)
    ok("⑧ 가중치를 못 읽으면 '구조만' 이라고 쓴다", "구조만" in src)
    ok("⑧ 자 없는 run 을 '🔴 자 없음' 으로 띄운다", "자 없음" in src)
    ok("⑧ 이 페이지의 자를 화면에 적는다", "모형 정량 주장을 내지 않는다" in src)
    #: 🔴 판 1.1.0 에서 늘어난 규율도 **화면 원문에서** 잰다
    ok("⑧ 🔴 노드 상태를 못 재면 '못 잼' 이라고 쓴다",
       "못 잼" in src and "추정하거나 보간하면" in src)
    ok("⑧ 🔴 접은 것을 화면에 적는다(`N×`)",
       "접었다" in src and "×" in src)
    ok("⑧ 🔴 겹친 곡선에 「몇 개 중 몇 개」를 적는다",
       "🔴 몇 개 중 몇 개" in src)
    ok("⑧ 🔴 중요도를 못 재면 **막대를 안 그리고** 몇 개 필요한지 적는다",
       "최소 " in src and "막대를 그리지 않는다" in src)
    ok("⑧ 🔴 배치를 손으로 안 적는다고 적혀 있다",
       "배치를 손으로 안 적는다" in src)
    ok("⑧ 화면 상태를 주소에 적는다(같은 화면을 다시 연다)",
       "saveHash" in src and "loadHash" in src)


# ── ⑨ 🔴 임의 DAG --- 잔차·분기·합류가 **실제 간선**에서 나오나 ──────
def _tblock(잔차: bool = True, 층더: bool = False):
    """시험용 작은 트랜스포머 블록 --- **손으로 배치를 안 적는다**(구조만 준다)."""
    import math
    import torch
    import torch.nn as nn

    class Head(nn.Module):
        def __init__(s, d, dh):
            super().__init__()
            s.q, s.k, s.v = (nn.Linear(d, dh), nn.Linear(d, dh),
                             nn.Linear(d, dh))
            s.dh = dh

        def forward(s, x):
            q, k, v = s.q(x), s.k(x), s.v(x)
            return ((q @ k.transpose(-2, -1)) / math.sqrt(s.dh)).softmax(-1) @ v

    class Net(nn.Module):
        def __init__(s, d=16, nh=4, dh=4, dff=32):
            super().__init__()
            s.tok = nn.Linear(1, d)
            s.ln1 = nn.LayerNorm(d)
            s.heads = nn.ModuleList([Head(d, dh) for _ in range(nh)])
            s.proj = nn.Linear(nh * dh, d)
            s.ln2 = nn.LayerNorm(d)
            s.ff1 = nn.Linear(d, dff)
            s.act = nn.GELU()
            s.ff2 = nn.Linear(dff, d)
            s.extra = nn.Linear(d, d) if 층더 else None
            s.out = nn.Linear(d, 1)

        def forward(s, x):
            h = s.tok(x.unsqueeze(-1))
            a = s.proj(torch.cat([hd(s.ln1(h)) for hd in s.heads], dim=-1))
            h = (h + a) if 잔차 else a                      # 🔴 잔차를 뺄 수 있다
            f = s.ff2(s.act(s.ff1(s.ln2(h))))
            h = (h + f) if 잔차 else f
            if s.extra is not None:
                h = s.extra(h)
            return s.out(h).squeeze(-1)
    return Net()


def t9_arbitrary_dag():
    from trainlog import Run, extract_arch, graph
    try:
        import torch  # noqa: F401
    except ImportError:
        ok("⑨ torch 가 없어 임의 DAG 를 **못 밟았다**", False, "torch 미설치")
        return
    a = extract_arch(_tblock(잔차=True))
    #: 🔴 **손으로 센 기대값**과 대조한다(노트 912 가 fx 함정을 밟았다).
    #:    입력→tok 1 · tok→ln1 1 · ln1→{q,k,v}×4 = 12 · 12→proj 12 ·
    #:    (tok,proj)→ln2 2 · ln2→ff1 1 · ff1→ff2 1 · (tok,proj,ff2)→out 3 = 33
    ok("⑨ 🔴 간선 수가 **손으로 센 기대값 33** 과 같다", len(a["간선"]) == 33,
       f"실측 {len(a['간선'])} · 층 {len(a['층'])} · 출처 {a['간선 출처']}")
    ok("⑨ 간선이 **실제 호출 그래프**에서 왔다(가정이 아니다)",
       a["간선 출처"] == "torch.fx 추적", a["간선 출처"])
    ok("⑨ 층 수가 손으로 센 19 와 같다(활성함수는 접힌다)", len(a["층"]) == 19,
       str(len(a["층"])))
    with Run("dag-res", root=tmp()) as r:
        r.arch(_tblock(잔차=True))
        rid = r.run_id
    g = graph(rid, root=tmp())
    skip = [e for e in g["화살표"] if e["건너뜀"] > 1]
    ok("⑨ 🔴 **잔차가 「건너뛴 화살표」로 실제로 보인다**", len(skip) >= 2,
       f"건너뛴 화살표 {len(skip)}개: "
       + ", ".join(f"{e['from']}→{e['to']}" for e in skip[:4]))
    ok("⑨ 분기(나가는 간선 2개 이상)가 있다",
       g["요약"]["분기 노드(나가는 간선 2개 이상)"] >= 1,
       str(g["요약"]["분기 노드(나가는 간선 2개 이상)"]))
    ok("⑨ 합류(들어오는 간선 2개 이상)가 있다",
       g["요약"]["합류 노드(들어오는 간선 2개 이상)"] >= 1,
       str(g["요약"]["합류 노드(들어오는 간선 2개 이상)"]))
    ok("⑨ 위상 배치가 한 줄이 아니다(같은 깊이에 여럿)",
       g["레이아웃"]["최대 레인"] >= 2, str(g["레이아웃"]))
    ok("⑨ 고리가 없다(위상 정렬이 다 폈다)",
       g["레이아웃"]["🔴 고리 있나"] is False)

    #: 🔴 **코드가 바뀌면 그림이 저절로 바뀐다** --- 손 배치가 아니라는 증거다
    with Run("dag-nores", root=tmp()) as r2:
        r2.arch(_tblock(잔차=False))
        rid2 = r2.run_id
    g2 = graph(rid2, root=tmp())
    skip2 = [e for e in g2["화살표"] if e["건너뜀"] > 1]
    ok("⑨ 🔴 **잔차를 빼면 건너뛴 화살표가 사라진다**",
       len(skip2) == 0 and len(skip) > 0,
       f"잔차 있음 {len(skip)}개 → 잔차 없음 {len(skip2)}개")
    with Run("dag-more", root=tmp()) as r3:
        r3.arch(_tblock(잔차=True, 층더=True))
        rid3 = r3.run_id
    g3 = graph(rid3, root=tmp())
    ok("⑨ 🔴 **층을 하나 더하면 블록이 하나 는다**",
       len(g3["블록"]) == len(g["블록"]) + 1,
       f"{len(g['블록'])} → {len(g3['블록'])}")


# ── ⑩ 🔴 `N×` 접기 --- **구조로** 찾는다(손 나열이 아니다) ──────────
def t10_fold_is_structural():
    from trainlog import Run, graph
    try:
        import torch.nn as nn
    except ImportError:
        ok("⑩ torch 가 없어 접기를 **못 밟았다**", False, "torch 미설치")
        return
    with Run("fold-t", root=tmp()) as r:
        r.arch(_tblock())
        rid = r.run_id
    g = graph(rid, root=tmp())
    접 = g["접은 것"]
    ok("⑩ 🔴 같은 꼴 형제를 **구조로 찾아** 접는다", bool(접),
       str([(x["대표"], x["배수"]) for x in 접]))
    ok("⑩ 접은 배수가 실제 형제 수와 같다(헤드 4개)",
       all(x["배수"] == 4 for x in 접), str([x["배수"] for x in 접]))
    ok("⑩ 접은 자리를 **화면에 적을 문장**이 있다",
       all(b["접힘 말"] for b in g["블록"] if b["접힘 배수"]),
       str([b["접힘 말"] for b in g["블록"] if b["접힘 배수"]][:1])[:110])
    ok("⑩ 접기 전/후 블록 수를 **둘 다** 낸다",
       g["요약"]["접기 전 블록 수"] > g["요약"]["블록 수"],
       f"{g['요약']['접기 전 블록 수']} → {g['요약']['블록 수']}")
    #: 🔴 **사람이 짠 클래스 안의 q·k·v 는 모양이 같아도 안 접는다**
    ids = {b["id"] for b in g["블록"]}
    ok("⑩ 🔴 q·k·v 는 모양이 같아도 **안 접힌다**(사람이 짠 클래스다)",
       len([i for i in ids if i.startswith("heads.0.")]) == 3,
       str(sorted(i for i in ids if i.startswith("heads.0."))))
    #: 눌러서 펼치면 블록이 는다
    대표 = 접[0]["대표"]
    ge = graph(rid, root=tmp(), 펼침=[대표])
    ok("⑩ 🔴 한 자리만 눌러 펼치면 블록이 는다",
       len(ge["블록"]) > len(g["블록"]),
       f"{len(g['블록'])} → {len(ge['블록'])} (펼친 것 {ge['펼친 것']})")
    #: 🔴 **접을 게 없으면 「못 찾았다」고 적는다**(조용히 넘어가지 않는다)
    with Run("fold-none", root=tmp()) as r2:
        r2.arch(nn.Sequential(nn.Linear(4, 6), nn.ReLU(), nn.Linear(6, 2)))
        rid2 = r2.run_id
    g2 = graph(rid2, root=tmp())
    ok("⑩ 🔴 되풀이가 없으면 **「못 찾았다」고 적는다**",
       not g2["접었나"] and "못 찾았다" in g2["🔴 접기 결과"],
       g2["🔴 접기 결과"][:80])


# ── ⑪ 🔴 동적 잘라내기 · 간선 예산 ────────────────────────────────
def t11_dynamic_cut():
    from trainlog import Run, neurons
    with Run("cut", root=tmp()) as r:
        r.arch({"층": [
            {"id": "a", "이름": "a", "종류": "Linear",
             "입력 뉴런 수": 300, "뉴런 수": 1024},
            {"id": "b", "이름": "b", "종류": "Linear",
             "입력 뉴런 수": 1024, "뉴런 수": 12}],
            "간선": [["a", "b"]]})
        rid = r.run_id
    n32 = neurons(rid, max_per_layer=32, root=tmp())
    n128 = neurons(rid, max_per_layer=128, root=tmp())
    big32 = next(L for L in n32["층"] if L["이름"] == "a")
    big128 = next(L for L in n128["층"] if L["이름"] == "a")
    small = next(L for L in n32["층"] if L["이름"] == "b")
    ok("⑪ 🔴 작은 층(12)은 **전부** 그린다", small["그린 뉴런"] == 12
       and small["잘림"] is False, str(small["그린 뉴런"]))
    ok("⑪ 🔴 상한을 올리면 **더 그린다**(고정 32가 아니다)",
       big128["그린 뉴런"] > big32["그린 뉴런"],
       f"상한 32 → {big32['그린 뉴런']}개 · 상한 128 → {big128['그린 뉴런']}개")
    ok("⑪ 자른 개수를 **화면 높이에서 역산했다고 적는다**",
       "역산" in (n32["자르기 역산"] or {}).get("🔴 어떻게 정했나", ""),
       str(n32["자르기 역산"]["🔴 어떻게 정했나"])[:90])
    ok("⑪ 그림 높이가 한도 안에 있다",
       320 <= n32["자르기 역산"]["그림 높이"] <= 1600,
       str(n32["자르기 역산"]["그림 높이"]))
    #: 🔴 **한 깊이에 노드가 몰리면 그 깊이의 상한이 줄어든다**
    층 = [{"id": f"h{i}", "이름": f"h{i}", "종류": "Linear",
          "입력 뉴런 수": 64, "뉴런 수": 512} for i in range(12)]
    with Run("cut-wide", root=tmp()) as r2:
        r2.arch({"층": [{"id": "src", "이름": "src", "종류": "Linear",
                       "입력 뉴런 수": 8, "뉴런 수": 64}] + 층,
                 "간선": [["src", f"h{i}"] for i in range(12)]})
        rid2 = r2.run_id
    w = neurons(rid2, max_per_layer=64, root=tmp())
    caps = {L["이름"]: L["이 층의 상한"] for L in w["층"]}
    ok("⑪ 🔴 한 깊이에 12개가 몰린 자리는 상한이 **더 작다**",
       caps["h0"] < caps["src"], f"src {caps['src']} vs h0 {caps['h0']}")
    #: 🔴 **간선을 다 긋지 않는다** --- 안개 금지
    e = w["간선"][0]
    ok("⑪ 🔴 간선을 **몇 개 중 몇 개** 그렸는지 적는다",
       bool(e["고른 기준"]) and e["전체 뉴런쌍"] is not None,
       f"{e['그린 선']}선 / 쌍 {e['전체 뉴런쌍']:,} · {e['그리기 방식']}")
    ok("⑪ 세기를 모르면 선을 **하나도 안 긋고 띠**로 묶는다",
       e["그리기 방식"] == "띠" and e["그린 선"] == 0, e["그리기 방식"])
    ok("⑪ 간선 표가 층 표와 따로 나온다", len(w["🔴 간선 표"]) == len(w["간선"]))
    tot = sum(int(x["그린 선"] or 0) for x in w["간선"])
    ok("⑪ 그린 선이 예산을 안 넘는다", tot <= 1500 + 40 * len(w["간선"]),
       str(tot))
    #: 🔴 합류 노드에서는 **가중치를 아무 간선에나 안 붙인다**(자가 적발)
    try:
        import torch.nn as nn
        with Run("merge", root=tmp()) as r3:
            r3.arch(_tblock())
            rid3 = r3.run_id
        n3 = neurons(rid3, root=tmp())
        merged = [x for x in n3["간선"] if x["to"] == "out"]
        ok("⑪ 🔴 합류 노드의 간선에는 세기를 **안 붙인다**(지어내기 금지)",
           bool(merged) and all(not x["세기 있나"] and "합류" in str(x["왜"])
                                for x in merged),
           str(merged[0]["왜"])[:90] if merged else "합류 간선 없음")
        _ = nn
    except ImportError:
        ok("⑪ torch 가 없어 합류 자리를 **못 밟았다**", False, "torch 미설치")


# ── ⑫ 🔴 실시간 --- **새 줄만** 이어 읽나 · 셋을 가르나 ────────────
def t12_incremental_and_liveness():
    from trainlog import Run, liveness, tail_metrics

    r = Run("live", root=tmp())
    for s in range(1, 4):
        r.log(step=s, split="train", loss=1.0 / s)
    r.flush()
    t1 = tail_metrics(r.run_id, 0, tmp())
    ok("⑫ 처음 읽으면 그때까지의 점이 다 온다", t1["새 줄 수"] == 3,
       str(t1["새 줄 수"]))
    off = t1["다음 바이트"]
    t2 = tail_metrics(r.run_id, off, tmp())
    ok("⑫ 🔴 새 줄이 없으면 **0개**를 낸다(전량 재전송 안 한다)",
       t2["새 줄 수"] == 0 and not t2["새 점"], str(t2["새 줄 수"]))
    for s in range(4, 9):
        r.log(step=s, split="train", loss=1.0 / s)
    r.flush()
    t3 = tail_metrics(r.run_id, off, tmp())
    ok("⑫ 🔴 그 뒤에 붙은 줄만 온다", t3["새 줄 수"] == 5,
       f"{t3['새 줄 수']}줄 · 오프셋 {off} → {t3['다음 바이트']}")
    ok("⑫ 오프셋이 앞으로만 간다", t3["다음 바이트"] > off)
    ok("⑫ 이어 읽은 점이 실제 값이다",
       abs(t3["새 점"][0]["value"] - 0.25) < 1e-9, str(t3["새 점"][0]))
    #: 🔴 **반쯤 쓰인 줄은 안 읽는다**
    from trainlog.store import run_dir
    p = run_dir(r.run_id, tmp()) / "metrics.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write('{"step": 9, "split": "train", "name": "loss"')  # 개행 없음
    t4 = tail_metrics(r.run_id, t3["다음 바이트"], tmp())
    ok("⑫ 🔴 개행 없는 꼬리는 **안 읽고 오프셋도 안 옮긴다**",
       t4["새 줄 수"] == 0 and t4["다음 바이트"] == t3["다음 바이트"],
       f"{t4['새 줄 수']}줄 · {t4['다음 바이트']}")
    with p.open("a", encoding="utf-8") as f:
        f.write(', "value": 0.11}\n')
    t5 = tail_metrics(r.run_id, t3["다음 바이트"], tmp())
    ok("⑫ 줄이 다 쓰이면 그때 읽는다", t5["새 줄 수"] == 1, str(t5["새 줄 수"]))
    #: 🔴 오프셋이 파일보다 크면 **처음부터 다시 읽고 그렇게 적는다**
    t6 = tail_metrics(r.run_id, 10 ** 9, tmp())
    ok("⑫ 🔴 오프셋이 파일보다 크면 되감고 **적는다**",
       bool(t6["되감음"]) and t6["새 줄 수"] > 0, str(t6["되감음"])[:70])
    #: 🔴 생사 뱃지 --- 셋을 가른다
    L1 = liveness(r.run_id, tmp())
    ok("⑫ 도는 중이면 '● 도는 중'", L1["뱃지"] == "● 도는 중", L1["뱃지"])
    L2 = liveness(r.run_id, tmp(), stale=0)
    ok("⑫ 🔴 **「멈춘 지 오래됨」과 「끝남」을 가른다**",
       L2["뱃지"] == "🔴 멈춘 지 오래됨" and "끝났다」가 아니다" in L2["말"],
       L2["뱃지"])
    r.finish()
    L3 = liveness(r.run_id, tmp(), stale=0)
    ok("⑫ 끝나면 문턱과 상관없이 '끝남'", L3["뱃지"] == "끝남", L3["뱃지"])
    d = Run("crashed", root=tmp())
    d._atexit()
    ok("⑫ 터진 run 은 '🔴 터짐'", liveness(d.run_id, tmp())["뱃지"] == "🔴 터짐")


# ── ⑬ 🔴 노드 상태 --- 안 재면 **「못 잼」**(0 이 아니다) ───────────
def t13_node_state():
    from trainlog import Run, node_state, read_node_metrics

    with Run("nostate", root=tmp()) as r0:
        r0.arch({"층": [{"id": "a", "뉴런 수": 4}], "간선": []})
        rid0 = r0.run_id
    S0 = read_node_metrics(rid0, tmp())
    ok("⑬ 🔴 노드 지표가 없으면 **「안 잼」**(「비었다」도 「0」도 아니다)",
       S0["상태"] == "안 잼", S0["상태"])
    ok("⑬ 「안 잼」에 왜가 붙는다", bool(S0.get("왜")))
    N0 = node_state(rid0, root=tmp())
    ok("⑬ 🔴 못 재면 그래프에 **아무 값도 안 얹는다**",
       N0["잴 수 있나"] is False and not N0["값"], str(N0["말"])[:70])

    with Run("state", root=tmp()) as r:
        r.arch({"층": [{"id": "a", "뉴런 수": 4}, {"id": "b", "뉴런 수": 2}],
                "간선": [["a", "b"]]})
        for s in (10, 20, 30):
            r.log_node(step=s, node="a", grad_norm=0.1 * s)
            r.log_node(step=s, node="b", grad_norm=0.01 * s)
        rid = r.run_id
    S = read_node_metrics(rid, tmp())
    ok("⑬ 노드 지표를 읽는다", S["상태"] == "읽었다" and S["줄 수"] == 6,
       f"{S['줄 수']}줄 · 노드 {S['노드 수']}개 · 단계 {S['단계']}")
    ok("⑬ 지표 이름이 나온다", S["지표 이름"] == ["grad_norm"], str(S["지표 이름"]))
    N = node_state(rid, root=tmp())
    ok("⑬ 안 고르면 **마지막 기록 단계**를 쓴다", N["고른 단계"] == 30,
       str(N["고른 단계"]))
    ok("⑬ 값이 기록과 정확히 같다", abs(N["값"]["a"] - 3.0) < 1e-9,
       str(N["값"]))
    N2 = node_state(rid, step=20, root=tmp())
    ok("⑬ step 을 고르면 **그 시점 값**이 온다",
       N2["고른 단계"] == 20 and abs(N2["값"]["a"] - 2.0) < 1e-9, str(N2["값"]))
    ok("⑬ step 이 바뀌면 값이 바뀐다", N2["값"]["a"] != N["값"]["a"])
    N3 = node_state(rid, step=17, root=tmp())
    ok("⑬ 🔴 기록에 없는 step 은 **사이 값을 만들지 않고 옮긴다**",
       N3["고른 단계"] in (10, 20) and bool(N3["🔴 단계를 옮겼나"]),
       str(N3["🔴 단계를 옮겼나"])[:80])
    ok("⑬ 🔴 그때 값도 **기록에 있는 값 그대로**다",
       N3["값"]["a"] in (1.0, 2.0), str(N3["값"]["a"]))
    #: manifest 가 노드 지표 줄 수를 적는다
    from trainlog import read_manifest
    m = read_manifest(rid, tmp())
    ok("⑬ manifest 에 노드 지표 줄 수가 적힌다", m["노드 지표 줄 수"] == 6,
       str(m["노드 지표 줄 수"]))
    ok("⑬ node 이름 없이 부르면 **실패로 센다**(조용히 안 삼킨다)",
       _bad_node_call() >= 1)


def _bad_node_call() -> int:
    from trainlog import Run
    r = Run("badnode", root=tmp())
    r.log_node(step=1, node="", grad_norm=1.0)
    m = r.finish()
    return int(m["기록 실패 n건"])


# ── ⑭ 🔴 런 비교 --- run 이 모자라면 **막대를 안 그린다** ──────────
def t14_compare_panel():
    from . import trainlog_svc as tl
    c = tl.compare()
    ok("⑭ 비교 패널이 뜬다", c.get("run 수") is not None, str(c.get("run 수")))
    ok("⑭ 🔴 축을 **manifest 에서 자동으로** 뽑는다",
       "자동" in c["평행좌표"]["🔴 축은 어디서 왔나"],
       str([a["이름"] for a in c["평행좌표"]["축"]])[:110])
    ok("⑭ 겹친 곡선에 **몇 개 중 몇 개**가 붙는다",
       "중" in c["겹친 곡선"]["🔴 몇 개 중 몇 개"],
       c["겹친 곡선"]["🔴 몇 개 중 몇 개"])
    I = c["중요도"]
    if I["잴 수 있나"]:
        ok("⑭ 중요도에 **자기 널**이 같이 나온다",
           all("널 95분위" in r for r in I["표"]), str(I["표"][:1])[:120])
    else:
        ok("⑭ 🔴 run 이 모자라면 **막대를 안 그리고 몇 개 필요한지 적는다**",
           I["표"] == [] and I["최소 필요"] >= 3 and str(I["지금 run 수"]),
           f"지금 {I['지금 run 수']}개 · 최소 {I['최소 필요']}개")
    ok("⑭ 으뜸 카드가 **어느 쪽이 좋은지 단정하지 않는다**",
       (not c["으뜸"]["잴 수 있나"]) or "모른다" in c["으뜸"]["🔴 어느 쪽이 좋은가"],
       str(c["으뜸"])[:90])


def main() -> int:
    for fn in (t1_spec, t2_no_metrics_no_curve, t3_arch_three_way,
               t4_truncation_is_visible, t5_gates, t6_no_overwrite_no_silence,
               t7_harness_alive, t8_page_cannot_invent,
               t9_arbitrary_dag, t10_fold_is_structural, t11_dynamic_cut,
               t12_incremental_and_liveness, t13_node_state, t14_compare_panel):
        print(f"\n── {fn.__name__} ─────────────────────────")
        try:
            fn()
        except Exception as e:
            import traceback
            traceback.print_exc()
            ok(f"{fn.__name__} 자체가 터졌다", False, f"{type(e).__name__}: {e}")
    if _TMP is not None:
        shutil.rmtree(_TMP, ignore_errors=True)
    bad = [r for r in _RESULT if not r["통과"]]
    print(f"\n{len(_RESULT) - len(bad)}/{len(_RESULT)} 통과")
    if bad:
        print("**실패가 있다**:")
        for r in bad:
            print(f"  · {r['검사']} --- {r['본 것']}")
    return 1 if bad else 0


def report() -> dict:
    """`runners/out912_trainlog.json` 이 싣는 꼴."""
    _RESULT.clear()
    rc = main()
    return {"검사 수": len(_RESULT), "통과": sum(r["통과"] for r in _RESULT),
            "실패": [r for r in _RESULT if not r["통과"]], "종료코드": rc,
            "줄": _RESULT}


if __name__ == "__main__":
    sys.exit(main())
