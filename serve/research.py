"""오토리서치 루프 --- **가설을 봉인하고, 병렬로 캐고, 사전 규칙으로 판정한다.**

**왜 이것이 필요한가.** 지금 창구(`serve/agent.py`)는 `--allowedTools
mcp__worldmodel` 만 허용한다 --- **웹 접근이 아예 없다.** 그래서 *"업계에서는
보통 얼마나 하나"* 를 물으면 우리 판 숫자만 되풀이하거나 모른다고 답한다.
바깥을 보려면 웹이 필요하고, 웹을 보게 하면 **바깥 주장과 우리 측정이 섞일
위험**이 생긴다. 이 저장소가 가장 자주 당한 병이 정확히 그것이다(노트 683:
자가 장부에만 있다 · 노트 794: 기준선 표가 두 시점에서 왔다).

**그래서 루프에 이 저장소의 규율을 박아 넣는다.** 다섯 걸음이다::

    ① 씨앗    우리가 **잰 것** 에서 출발한다(능력 카드 · 판 · 대장)
    ② 봉인    가설과 **반증 조건 · 결정 규칙** 을 먼저 적고 해시로 굳힌다
    ③ 조사    가설마다 **격리된 프로세스**에서 병렬로 웹을 캔다
    ④ 대조    바깥 숫자와 우리 숫자를 **출처 딱지**를 달아 나란히 놓는다
    ⑤ 판정    ②에서 적은 규칙을 그대로 적용한다 --- 결과를 보고 안 바꾼다

🔴 **봉인이 이 모듈의 핵심이다.** 증거를 본 뒤에 가설을 고치면 그것은 조사가
아니라 합리화다. 노트 133 이 *"첫 양성을 그냥 채택하지 않는다"* 를 적었고,
노트 770·791 이 **사전등록 규칙에 구멍이 있으면 결과를 보고 메우게 된다**는 것을
두 번 보여 줬다. 그래서 봉인 파일에 **가설 · 반증 조건 · 결정 규칙 · 해시**를
같이 적고, 판정할 때 해시를 다시 확인한다.

🔴 **출처 딱지도 핵심이다.** `serve/boardsvc.py` 가 모든 반환에 ``산출`` 을 붙이는
것과 같은 이유다 --- 서버가 둘을 섞어 내면 **바깥 주장을 우리 측정인 양 세탁**하게
된다. 이 모듈은 세 딱지를 쓴다::

    "측정"      이 저장소가 잰 값(노트 번호가 붙는다)
    "외부"      웹에서 온 남의 주장(URL 이 붙는다)
    "추정"      둘 중 어느 것도 아닌 것 --- **판정에 못 쓴다**

**격리.** 가설마다 `claude` CLI 를 **제 임시 디렉터리에서** 띄우고 도구를
`WebSearch`·`WebFetch` 와 우리 MCP **읽기 도구**로만 묶는다. `Bash`·`Write`·
`Edit` 는 안 준다 --- 조사가 저장소를 못 건드린다.

쓰는 법::

    python3 -m serve.research "팝업 방문객 예측을 업계는 어떻게 하나"
    python3 -m serve.research --hyp 5 --show <질문>
"""
from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEALS = ROOT / "data/lab/research"
MCP_SERVER = "worldmodel"

#: 조사 팔이 쓸 수 있는 도구. **읽기만이다** --- Bash·Write·Edit 를 안 준다.
PROBE_TOOLS = ("WebSearch", "WebFetch", f"mcp__{MCP_SERVER}")
#: 씨앗·판정 팔은 웹이 필요 없다. 우리 도구만.
LOCAL_TOOLS = (f"mcp__{MCP_SERVER}",)

MAX_PARALLEL = 4
TIMEOUT = 420

#: 출처 딱지. **"추정" 은 판정에 못 쓴다.**
TAGS = ("측정", "외부", "추정")


# ── 낮은 층: 격리된 한 프로세스 ────────────────────────────────────
def _mcp_config() -> str:
    return json.dumps({"mcpServers": {MCP_SERVER: {
        "command": sys.executable, "args": ["-m", "serve.mcp"],
        "env": {"PYTHONPATH": str(ROOT)}, "cwd": str(ROOT)}}},
        ensure_ascii=False)


def ask(prompt: str, tools=LOCAL_TOOLS, model: str | None = None,
        timeout: int = TIMEOUT, sandbox: bool = True) -> dict:
    """`claude` CLI 한 번. **제 임시 디렉터리에서 돈다**(격리).

    `cwd` 를 저장소가 아니라 빈 임시 폴더로 준다 --- 도구를 읽기로 묶어 두긴
    했지만 **작업 디렉터리까지 떼어 놓는 것**이 격리의 기본이다. MCP 서버는
    저장소에서 돌아야 하므로 그쪽 `cwd` 만 저장소로 둔다.
    """
    exe = shutil.which("claude")
    if exe is None:
        return {"ok": False, "오류": "`claude` CLI 가 PATH 에 없다", "글": ""}
    work = tempfile.mkdtemp(prefix="wm-research-") if sandbox else str(ROOT)
    cmd = [exe, "-p", "--output-format", "json",
           "--mcp-config", _mcp_config(), "--strict-mcp-config",
           "--allowedTools", ",".join(tools),
           "--permission-mode", "bypassPermissions"]
    if model:
        cmd += ["--model", model]
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)      # auth 로 돈다(노트 701 과 같은 규율)
    env["PYTHONPATH"] = str(ROOT)
    t0 = time.time()
    try:
        pr = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                            cwd=work, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "오류": f"{timeout}초 넘김", "글": "",
                "초": timeout}
    except Exception as e:
        return {"ok": False, "오류": f"{type(e).__name__}: {e}", "글": ""}
    finally:
        if sandbox:
            shutil.rmtree(work, ignore_errors=True)
    out = (pr.stdout or "").strip()
    text = out
    try:
        j = json.loads(out)
        text = j.get("result") or j.get("text") or out
    except Exception:
        pass
    return {"ok": pr.returncode == 0 and bool(text), "글": text,
            "오류": (pr.stderr or "")[-400:] if pr.returncode else None,
            "초": round(time.time() - t0, 1)}


def _json_in(text: str):
    """모형 글에서 JSON 덩어리를 꺼낸다. **못 꺼내면 None** --- 지어내지 않는다."""
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    cand = m.group(1) if m else text
    i, j = cand.find("{"), cand.rfind("}")
    if i < 0 or j <= i:
        i, j = cand.find("["), cand.rfind("]")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(cand[i:j + 1])
    except Exception:
        return None


def parallel(jobs: list, workers: int = MAX_PARALLEL) -> list:
    """`jobs` 는 무인자 호출체 목록. 순서를 지켜 결과를 돌려준다."""
    out = [None] * len(jobs)
    q = queue.Queue()
    for i, f in enumerate(jobs):
        q.put((i, f))

    def worker():
        while True:
            try:
                i, f = q.get_nowait()
            except queue.Empty:
                return
            try:
                out[i] = f()
            except Exception as e:
                out[i] = {"ok": False, "오류": f"{type(e).__name__}: {e}"}
            finally:
                q.task_done()

    ts = [threading.Thread(target=worker, daemon=True)
          for _ in range(min(workers, max(len(jobs), 1)))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return out


# ── ① 씨앗 --- 우리가 **잰 것** ────────────────────────────────────
def seed() -> dict:
    """가설의 출발점을 **측정에서** 가져온다. 지어낸 전제로 시작하지 않는다."""
    from . import capability, registry
    out = {"능력": {"말할 수 있는 것": [a["꼴"] for a in capability.ALLOWED],
                  "말할 수 없는 것": [f["꼴"] for f in capability.FORBIDDEN]},
           "측정": [], "판": None}
    try:
        out["측정"] = [{"노트": n, "무엇": w, "값": v}
                      for n, w, v in capability.measured()][:40]
    except Exception as e:
        out["측정_오류"] = f"{type(e).__name__}: {e}"
    try:
        from . import boardsvc
        #: **캐시를 읽기만 한다.** `warm()` 을 부르면 캐시가 낡았을 때
        #: 씨앗 만들다가 340초를 굽는다 --- 조사 루프가 거기서 멈춘다.
        if boardsvc.status()["상태"] != "데움":
            hit = boardsvc._load_cache()
            if hit is not None:
                boardsvc._S = hit
        st = boardsvc.status()
        out["판"] = {"상태": st["상태"], "rho": st.get("판 rho"),
                    "도메인 수": st.get("도메인 수"), "산출": st.get("산출")}
    except Exception as e:
        out["판_오류"] = f"{type(e).__name__}: {e}"
    try:
        out["도메인 범위"] = registry.SCOPE
    except Exception:
        pass
    return out


# ── ② 봉인 --- 증거를 보기 **전에** 굳힌다 ─────────────────────────
SEAL_PROMPT = """\
너는 측정 규율이 엄한 연구실의 사전등록을 쓴다. 아래는 **우리가 실제로 잰 것**이다.

<질문>
{question}
</질문>

<우리가 잰 것>
{seed}
</우리가 잰 것>

가설을 **{n}개** 만들어라. 규칙:

1. 각 가설은 **바깥 세계에 대한 것**이어야 한다(업계 관행 · 표준 · 남들의 방법).
   우리 모형 자체에 대한 가설이 아니다.
2. 각 가설에 **반증 조건**을 단다 --- *무엇을 찾으면 이 가설이 틀린 것인가*.
   찾을 수 없는 조건(예: "아무도 안 한다")은 반증 조건이 아니다.
3. 각 가설에 **결정 규칙**을 단다 --- 증거가 어떠하면 (가)채택 (나)기각
   (다)판정 미룸인지. **세 갈래를 다 적는다.**
4. 각 가설에 **찾을 것**을 3~5개 적는다(구체적인 검색어 · 문서 종류).
5. 🔴 우리 숫자를 그대로 되풀이하는 가설은 만들지 마라. 가설은 **바깥에서
   확인되거나 반증될 수 있어야** 한다.

JSON 만 출력한다:
{{"가설": [{{"이름": "...", "주장": "...", "반증 조건": "...",
  "결정 규칙": {{"가": "...", "나": "...", "다": "..."}},
  "찾을 것": ["...", "..."]}}]}}
"""


def preregister(question: str, n: int = 4, model: str | None = None) -> dict:
    """가설을 만들고 **해시로 봉인**한다. 봉인 뒤에는 안 고친다."""
    sd = seed()
    r = ask(SEAL_PROMPT.format(question=question, n=n,
                               seed=json.dumps(sd, ensure_ascii=False)[:6000]),
            tools=LOCAL_TOOLS, model=model)
    j = _json_in(r.get("글", "")) or {}
    hyps = j.get("가설") or []
    #: **모양을 검사한다.** 반증 조건이나 결정 규칙이 없으면 사전등록이 아니다
    bad = [h.get("이름", "?") for h in hyps
           if not h.get("반증 조건") or not isinstance(h.get("결정 규칙"), dict)
           or set(h["결정 규칙"]) < {"가", "나", "다"}]
    body = {"질문": question, "만든때": datetime.now().isoformat(timespec="seconds"),
            "가설": hyps, "씨앗 요약": {"측정 수": len(sd.get("측정") or []),
                                  "판": (sd.get("판") or {}).get("rho")}}
    seal = hashlib.sha256(
        json.dumps(body["가설"], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:16]
    body["봉인"] = seal
    body["모양 이상"] = bad or "없음"
    SEALS.mkdir(parents=True, exist_ok=True)
    (SEALS / f"seal_{seal}.json").write_text(
        json.dumps(body, ensure_ascii=False, indent=1))
    return body


# ── ③ 조사 --- 격리 · 병렬 ─────────────────────────────────────────
PROBE_PROMPT = """\
너는 **하나의 가설만** 조사한다. 다른 가설은 신경 쓰지 마라.

<가설>
{hyp}
</가설>

<반증 조건>
{falsif}
</반증 조건>

웹을 찾아 증거를 모아라. 규칙:

1. 🔴 **반증 조건을 먼저 찾아라.** 가설을 뒷받침하는 것부터 찾으면 확증 편향이다.
   반증 증거를 못 찾았으면 *"못 찾았다"* 고 적는다 --- 없다는 뜻이 아니다.
2. 모든 숫자에 **출처 딱지**를 단다:
   - `"외부"` --- 웹에서 온 남의 주장. **URL 을 반드시 적는다.**
   - `"측정"` --- `mcp__worldmodel` 도구로 우리 저장소에서 읽은 값. 노트 번호를 적는다.
   - `"추정"` --- 둘 다 아닌 것. **추정은 판정에 못 쓴다.**
3. 업계 표준을 말하려면 **출처가 둘 이상**이어야 한다. 하나뿐이면 `"단일 출처"`로 적는다.
4. 우리 저장소 값이 필요하면 `mcp__worldmodel` 도구를 불러라. **기억으로 적지 마라.**
5. 못 찾은 것은 못 찾았다고 적는다. **채워 넣지 마라.**

JSON 만 출력한다:
{{"찾은 것": [{{"말": "...", "딱지": "외부|측정|추정", "출처": "URL 또는 노트 N",
   "숫자": null 또는 값}}],
 "반증 증거": "찾은 반증 증거 또는 '못 찾았다'",
 "출처 수": 0,
 "한 줄": "..."}}
"""


def probe(h: dict, model: str | None = None) -> dict:
    r = ask(PROBE_PROMPT.format(hyp=json.dumps(h, ensure_ascii=False),
                                falsif=h.get("반증 조건", "")),
            tools=PROBE_TOOLS, model=model)
    j = _json_in(r.get("글", "")) or {}
    finds = j.get("찾은 것") or []
    tags = {}
    for f in finds:
        t = f.get("딱지")
        tags[t if t in TAGS else "딱지없음"] = tags.get(
            t if t in TAGS else "딱지없음", 0) + 1
    #: **URL 없는 "외부" 는 외부가 아니다.** 딱지를 스스로 강등한다
    demoted = 0
    for f in finds:
        if f.get("딱지") == "외부" and not re.search(r"https?://",
                                                 str(f.get("출처") or "")):
            f["딱지"] = "추정"
            f["강등"] = "URL 이 없어 '추정' 으로 내렸다"
            demoted += 1
    return {"이름": h.get("이름"), "ok": r.get("ok"), "초": r.get("초"),
            "찾은 것": finds, "반증 증거": j.get("반증 증거"),
            "한 줄": j.get("한 줄"), "딱지 세기": tags,
            "URL 없어 강등": demoted, "오류": r.get("오류")}


# ── 훅 --- 걸음 사이의 문 ──────────────────────────────────────────
#: 각 훅은 (걸음 이름, 산출물) 을 받아 **이상 목록**을 돌려준다. 이상이 있으면
#: 기록에 남고, `게이트=True` 인 훅이 걸리면 **다음 걸음을 멈춘다.**
#: 사람 기억이 아니라 훅이 막는다 --- 노트 598 '가드는 불려야 가드다'.
def _hook_seal_shape(pre: dict) -> list:
    """봉인 뒤: 가설 모양 검사. 반증 조건·결정 규칙 세 갈래가 없으면 막는다."""
    bad = pre.get("모양 이상")
    return [] if bad == "없음" else [f"가설 모양 이상: {bad}"]


def _hook_probe_sources(found: list) -> list:
    """조사 뒤: 딱지 위생. 외부 주장이 0 이면 그 가설은 판정에 못 간다."""
    out = []
    for f in found:
        tags = f.get("딱지 세기") or {}
        if not f.get("ok"):
            out.append(f"{f.get('이름')}: 조사 실패 ({f.get('오류')})")
        elif not tags.get("외부"):
            out.append(f"{f.get('이름')}: 외부 출처 0 --- 판정 불가로 표시")
    return out


def _hook_verdict_scope(verdicts: list) -> list:
    """판정 뒤: 갈래 밖 판정·추정 근거 사용을 잡는다."""
    out = []
    for v in verdicts:
        if v.get("판정") not in ("가", "나", "다"):
            out.append(f"갈래 밖 판정: {v.get('판정')}")
    return out


HOOKS = {
    "봉인": [(_hook_seal_shape, True)],       # 게이트 --- 모양이 틀리면 멈춘다
    "조사": [(_hook_probe_sources, False)],   # 기록만 --- 가설 하나 실패로 전체를 안 멈춘다
    "판정": [(_hook_verdict_scope, False)],
}


def _run_hooks(step: str, payload) -> tuple:
    """(이상 목록, 멈출 것인가)."""
    issues, gate = [], False
    for fn, is_gate in HOOKS.get(step, ()):
        got = fn(payload) or []
        issues += got
        if got and is_gate:
            gate = True
    return issues, gate


# ── ④⑤ 대조와 판정 ────────────────────────────────────────────────
JUDGE_PROMPT = """\
너는 **사전에 적힌 결정 규칙만** 적용한다. 규칙을 고치지 마라.

<가설과 결정 규칙 (봉인됨 · 고칠 수 없다)>
{hyp}
</가설과 결정 규칙>

<조사가 찾은 것>
{found}
</조사가 찾은 것>

규칙:
1. 🔴 결정 규칙 (가)(나)(다) 중 **하나를 고른다.** 새 갈래를 만들지 마라.
2. 🔴 딱지가 `"추정"` 인 것은 **판정 근거로 쓰지 마라.** 세되 근거에서 뺀다.
3. 출처가 하나뿐이면 업계 표준이라 부르지 마라 --- `"단일 출처"` 로 적는다.
4. 우리 측정과 바깥 주장이 어긋나면 **어긋난 채로 적는다.** 평균 내지 마라.
5. 무엇을 못 알아냈는지 반드시 적는다.

JSON 만 출력한다:
{{"판정": "가|나|다", "왜": "...", "쓴 근거 수": 0, "뺀 추정 수": 0,
 "우리 측정과 어긋나는 것": "...", "못 알아낸 것": "...",
 "업계 표준이라 부를 수 있나": true|false}}
"""


def judge(h: dict, found: dict, model: str | None = None) -> dict:
    r = ask(JUDGE_PROMPT.format(
        hyp=json.dumps(h, ensure_ascii=False),
        found=json.dumps(found, ensure_ascii=False)[:9000]),
        tools=LOCAL_TOOLS, model=model)
    j = _json_in(r.get("글", "")) or {}
    if j.get("판정") not in ("가", "나", "다"):
        j = {**j, "판정": "다", "왜": (j.get("왜") or "")
             + " [판정을 못 읽어 '다(판정 미룸)' 로 둔다]"}
    return j


#: 🔴 **선발 기준 --- 코드에 못박는다.** 판정자가 고르는 게 아니라 이 순서가
#: 고른다. 결과를 보고 기준을 바꾸는 것을 막는 자리다(노트 133).
#:   ① 판정 "가"(채택) 만 후보다
#:   ② 외부 출처 수가 많은 쪽 (표준 주장은 출처 둘 이상 --- 하나면 후보 밖)
#:   ③ 강등(URL 없는 외부) 이 적은 쪽
#:   ④ 우리 측정과 어긋남이 없는 쪽이 있으면 그쪽
def select_best(results: list) -> dict:
    cands = []
    for r in results:
        if r.get("판정") != "가":
            continue
        tags = r.get("딱지 세기") or {}
        ext = tags.get("외부", 0)
        if ext < 2:
            continue                          # 단일 출처는 표준이 못 된다
        clash = str(r.get("우리 측정과 어긋나는 것") or "")
        cands.append((ext, -(r.get("URL 없어 강등") or 0),
                      0 if ("없" in clash[:20] or not clash) else -1,
                      r))
    if not cands:
        return {"채택": None,
                "왜": "판정 '가' 이면서 외부 출처 둘 이상인 가설이 없다 --- "
                     "**억지로 하나를 고르지 않는다**"}
    cands.sort(key=lambda x: x[:3], reverse=True)
    best = cands[0][3]
    return {"채택": best.get("가설"), "주장": best.get("주장"),
            "왜": f"판정 '가' · 외부 출처 {cands[0][0]}개 · "
                 f"강등 {-cands[0][1]}건 · 기준은 코드에 못박힌 넷",
            "차점": [c[3].get("가설") for c in cands[1:3]]}


def run(question: str, n: int = 4, model: str | None = None,
        on_step=None) -> dict:
    """여섯 걸음. **봉인 → 병렬 조사 → 사전 규칙 판정 → 선발.**

    걸음 사이에 **훅**이 선다(`HOOKS`) --- 봉인 모양이 틀리면 조사로 못 가고,
    외부 출처가 0 인 가설은 그렇게 표시되고, 갈래 밖 판정은 기록된다.
    """
    t0 = time.time()
    hook_log = {}

    def step(k, v=None):
        if on_step:
            on_step(k, v)

    step("씨앗")
    step("봉인")
    pre = preregister(question, n=n, model=model)
    hyps = pre.get("가설") or []
    if not hyps:
        return {"오류": "가설을 못 만들었다", "사전등록": pre,
                "초": round(time.time() - t0, 1)}
    issues, gate = _run_hooks("봉인", pre)
    hook_log["봉인"] = issues or "통과"
    if gate:
        return {"오류": "봉인 모양이 틀려 조사로 못 간다(게이트)",
                "훅": hook_log, "사전등록": pre,
                "초": round(time.time() - t0, 1)}

    step("조사", len(hyps))
    found = parallel([(lambda h=h: probe(h, model=model)) for h in hyps])
    hook_log["조사"] = _run_hooks("조사", found)[0] or "통과"

    step("판정")
    verdicts = parallel([(lambda h=h, f=f: judge(h, f, model=model))
                         for h, f in zip(hyps, found)])
    hook_log["판정"] = _run_hooks("판정", verdicts)[0] or "통과"

    #: 🔴 **봉인을 다시 확인한다** --- 도는 동안 가설이 바뀌지 않았음을 보인다
    reseal = hashlib.sha256(
        json.dumps(hyps, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:16]
    out = {"질문": question, "봉인": pre["봉인"],
           "**봉인 그대로인가**": reseal == pre["봉인"],
           "훅": hook_log,
           "사전등록": pre, "결과": [
               {"가설": h.get("이름"), "주장": h.get("주장"),
                "판정": v.get("판정"), "왜": v.get("왜"),
                "업계 표준이라 부를 수 있나": v.get("업계 표준이라 부를 수 있나"),
                "우리 측정과 어긋나는 것": v.get("우리 측정과 어긋나는 것"),
                "못 알아낸 것": v.get("못 알아낸 것"),
                "딱지 세기": f.get("딱지 세기"), "URL 없어 강등": f.get("URL 없어 강등"),
                "반증 증거": f.get("반증 증거"), "조사 초": f.get("초")}
               for h, f, v in zip(hyps, found, verdicts)],
           "초": round(time.time() - t0, 1)}
    step("선발")
    out["**선발**"] = select_best(out["결과"])
    #: 🔴 **능력 카드 자기 검사** --- 루프가 금지 꼴을 뱉지 못하게
    try:
        from . import capability
        blob = json.dumps(out, ensure_ascii=False)
        out["자기 검사"] = capability.check(blob) or "통과"
    except Exception as e:
        out["자기 검사"] = f"못 돌렸다: {type(e).__name__}"
    (SEALS / f"run_{pre['봉인']}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main() -> None:
    #: **깃발의 *값* 도 질문에서 빼야 한다.** 처음엔 `--` 로 시작하는 것만
    #: 걸렀더니 `--hyp 3` 의 `3` 이 질문 앞에 붙어 들어갔다.
    argv = sys.argv[1:]
    n, args, skip = 4, [], False
    for i, a in enumerate(argv):
        if skip:
            skip = False
            continue
        if a == "--hyp":
            n = int(argv[i + 1]) if i + 1 < len(argv) else 4
            skip = True
        elif a.startswith("--hyp="):
            n = int(a.split("=", 1)[1])
        elif a.startswith("--"):
            continue
        else:
            args.append(a)
    if not args:
        print("쓰는 법: python3 -m serve.research [--hyp N] \"<질문>\"")
        raise SystemExit(2)
    q = " ".join(args)
    out = run(q, n=n, on_step=lambda k, v=None: print(
        f"  … {k}{'' if v is None else f' ({v})'}", flush=True))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
