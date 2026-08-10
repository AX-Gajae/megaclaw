"""대화형 창구 --- 사람의 말로 물으면 모형을 불러 답하고, **자를 같이 낸다.**

    python3 -m serve.agent "체인소맨 애니화 가능성 어때?"
    python3 -m serve.agent            # 대화 모드

**왜 에이전트를 따로 두나.** 모형은 백분위와 확률만 낸다(노트 691 이 절대값을
막았다). 사람은 결정 언어로 묻는다. 그 사이를 번역하는 층이 필요한데, 그 층이
**과장하기 가장 쉬운 자리**다 --- 숫자를 말로 옮기는 순간 "약 1만명쯤" 같은
것이 슬쩍 들어온다.

그래서 이 층의 설계 원칙은 하나다: **번역기는 모형이 안 낸 숫자를 만들 수
없다.** 세 겹으로 막는다.

    1. 시스템 프롬프트가 `serve.capability` 카드를 그대로 받는다
       --- 말할 수 있는 꼴과 없는 꼴이 측정과 노트 번호로 적혀 있다.
    2. 도구만이 숫자의 출처다 --- 도구가 실패하면 답에 숫자가 없어야 한다.
    3. 답을 낸 뒤 `capability.check` 로 자기 검사를 하고, 걸리면 **표시한다**
       (조용히 고치지 않는다 --- 조용한 대체는 조용한 버그다 · 노트 133).

세 번째가 중요하다. 검사를 통과 못 한 답을 몰래 다시 쓰면 그 실패가 안 보인다.
`--strict` 를 주면 걸린 답을 아예 내보내지 않는다.

**열쇠.** `ANTHROPIC_API_KEY` 를 환경에서 읽는다. 없으면 도구를 직접 부르는
`--offline` 갈래로 떨어진다(모형은 열쇠 없이 돈다 --- 말만 못 붙인다).
"""
from __future__ import annotations

import json
import os
import sys

MODEL = "claude-opus-4-8"
MAX_TOKENS = 8000


def _load_env() -> bool:
    """저장소 규약대로 `.env` 에서 열쇠를 읽는다(`rotate_key.sh` 가 쓰는 자리).

    이미 환경에 있으면 안 덮는다 --- 셸에서 준 것이 우선이다.
    """
    from pathlib import Path
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    f = Path(__file__).resolve().parent.parent / ".env"
    if not f.exists():
        return False
    for line in f.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            v = line.split("=", 1)[1].strip().strip("\"'")
            if v:
                os.environ["ANTHROPIC_API_KEY"] = v
                return True
    return False


# ---------------------------------------------------------------- 도구
#
# **손으로 안 적는다 --- 등록소에서 온다**(노트 701). 예전에는 여기에 함수 넷을
# 적고 `serve/capability.py` 에 카드를 따로 적었다. 둘이 갈라지면 창구가 없는
# 능력을 말하거나 있는 능력을 못 부른다 --- 이 저장소가 세 번 밟은 병이다
# (노트 546 · 549 · 670).
#
# 도구 이름은 ASCII 여야 한다(한글이면 API 400 · 노트 693). 등록소의
# `check()` 가 그것을 검사한다.


def _reg():
    from . import registry
    return registry


def tool_schemas() -> list:
    return _reg().tool_schemas()


def call(name: str, args: dict) -> str:
    """도구 하나를 부르고 **문자열로** 돌려준다(API 가 문자열을 요구한다)."""
    fns = _reg().fns()
    f = fns.get(name)
    if f is None:
        return json.dumps({"오류": f"'{name}' 은 등록소에 없다",
                           "있는 것": sorted(fns)}, ensure_ascii=False)
    try:
        out = f(**(args or {}))
    except TypeError as e:
        return json.dumps({"오류": f"인자가 안 맞는다: {e}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"오류": f"{type(e).__name__}: {e}"}, ensure_ascii=False)
    if isinstance(out, str):
        return out
    return json.dumps(out, ensure_ascii=False, default=str)


def stream(question: str, model: str | None = None):
    """토막을 내보내는 발생기. **도구 고리를 손으로 돈다.**

    `tool_runner` 는 편하지만 토막 단위 스트림을 안 준다. 사람이 기다리는
    화면에서는 그 차이가 크므로 고리를 직접 돈다 --- 요청 → 스트림 → 도구
    실행 → 결과를 되먹임 → `stop_reason` 이 `tool_use` 가 아니면 끝.

    **되먹일 때 `msg.content` 를 통째로 넣는다.** 생각 블록을 빼면 API 가
    거부하거나 다음 턴이 앞 생각을 못 본다.

    도구는 **등록소에서** 온다(노트 701) --- `tool_schemas()` · `call()`.

    내보내는 것: `{"type": "thinking"|"text"|"tool"|"done"|"error", ...}`
    """
    import anthropic
    from . import capability

    # 🔴 **일곱 번째 진입점**(티처 #53 M5). 노트 889 가 '여섯 자리를 막았다'고
    # 했는데 저장소 전수 grep 은 **7곳**이었고 여기가 빠져 있었다 --- 그것도
    # 사용자 대면 창구다. grep 한 번이면 잡혔을 자리다.
    from core.noapi import assert_free
    assert_free("serve_agent")
    client = anthropic.Anthropic()
    msgs = [{"role": "user", "content": question}]
    full = ""
    for _round in range(8):                      # 고리 상한 --- 무한 도구 고리 방지
        with client.messages.stream(
            model=model or MODEL, max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=capability.system_prompt(),
            tools=tool_schemas(), messages=msgs,
        ) as st:
            for ev in st:
                if ev.type != "content_block_delta":
                    continue
                d = ev.delta
                if d.type == "text_delta":
                    full += d.text
                    yield {"type": "text", "text": d.text}
                elif d.type == "thinking_delta":
                    yield {"type": "thinking", "text": d.thinking}
            msg = st.get_final_message()
        msgs.append({"role": "assistant", "content": msg.content})
        calls = [b for b in msg.content if b.type == "tool_use"]
        if msg.stop_reason != "tool_use" or not calls:
            break
        results = []
        for b in calls:
            yield {"type": "tool",
                   "text": f"{b.name}({json.dumps(b.input, ensure_ascii=False)})"}
            results.append({"type": "tool_result", "tool_use_id": b.id,
                            "content": call(b.name, b.input or {})})
        msgs.append({"role": "user", "content": results})
    else:
        yield {"type": "error", "text": "도구 고리가 8번을 넘었다 --- 끊었다"}
    yield {"type": "done", "selfcheck": capability.check(full)}


# ------------------------------------------------------- auth 백엔드(CLI)
#
# 사용자가 "api 말고 auth 로" 라고 했다. 구독 토큰을 꺼내 SDK 에 꽂는 길도
# 있지만 **그 자격 증명은 Claude Code 용으로 발급된 것**이라 다른 앱을 돌리라고
# 준 것이 아니다. 그래서 그 길로 안 간다.
#
# 대신 **`claude` CLI 를 그대로 백엔드로 쓴다** --- 사용자가 이미 한 로그인을
# 쓰고, `--mcp-config` 로 우리 도구를 붙인다. 즉 Claude Code 를 Claude Code 로
# 쓰면서 우리 모형만 얹는다. 자격 증명을 우리가 만지지 않는다.

import os as _os
import shutil as _shutil
import subprocess as _sp
from pathlib import Path as _Path

#: MCP 도구는 `mcp__<서버>__<도구>` 로 불린다.
MCP_SERVER = "worldmodel"


def cli_path() -> str | None:
    return _shutil.which("claude")


def _mcp_config() -> str:
    root = _Path(__file__).resolve().parent.parent
    return json.dumps({"mcpServers": {MCP_SERVER: {
        "command": sys.executable, "args": ["-m", "serve.mcp"],
        "env": {"PYTHONPATH": str(root)}, "cwd": str(root)}}},
        ensure_ascii=False)


def stream_cli(question: str, model: str | None = None,
               session: str | None = None):
    """`claude -p --output-format stream-json` 을 백엔드로 쓰는 발생기.

    내보내는 것은 `stream()` 과 **같은 꼴**이고 하나가 더 있다 ---
    `{"type": "session", "text": <id>}`. **그것을 다음 턴에 `session=` 으로
    돌려주면 대화가 이어진다**(`--resume`).

    처음엔 그걸 안 넣어서 **매 요청이 새 세션이었다** --- 창구가 앞 턴을 하나도
    기억하지 못했다. `session_id` 는 `stream_event` 와 `result` 에 들어 있다.
    """
    from . import capability
    exe = cli_path()
    if exe is None:
        yield {"type": "error", "text": "`claude` CLI 가 PATH 에 없다"}
        yield {"type": "done", "selfcheck": []}
        return
    root = str(_Path(__file__).resolve().parent.parent)
    cmd = [exe, "-p",
           "--output-format", "stream-json", "--include-partial-messages",
           "--verbose",
           "--mcp-config", _mcp_config(), "--strict-mcp-config",
           "--append-system-prompt", capability.system_prompt(),
           "--allowedTools", f"mcp__{MCP_SERVER}",
           "--permission-mode", "bypassPermissions"]
    if session:
        cmd += ["--resume", session]
    # **`--bare` 를 쓰면 안 된다** --- 도움말이 "Anthropic auth is strictly
    # ANTHROPIC_API_KEY or apiKeyHelper (OAuth and keychain are never read)"
    # 라고 적는다. 우리가 원하는 것이 정확히 그 반대다(auth 로 돌리기).
    # 처음에 넣었다가 "Not logged in" 을 받고 알았다.
    if model:
        cmd += ["--model", model]
    env = dict(_os.environ)
    env.pop("ANTHROPIC_API_KEY", None)     # **auth 로 돌린다** --- 키를 안 넘긴다
    env["PYTHONPATH"] = root
    full = ""
    sid = None
    try:
        pr = _sp.Popen(cmd, stdin=_sp.PIPE, stdout=_sp.PIPE, stderr=_sp.PIPE,
                       text=True, bufsize=1, cwd=root, env=env)
    except Exception as e:
        yield {"type": "error", "text": f"CLI 를 못 띄웠다: {type(e).__name__}: {e}"}
        yield {"type": "done", "selfcheck": []}
        return
    try:
        pr.stdin.write(question)
        pr.stdin.close()
        for line in pr.stdout:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            got = ev.get("session_id")
            if got and got != sid:
                sid = got
                yield {"type": "session", "text": sid}
            for out in _from_cli(ev):
                if out["type"] == "text":
                    full += out["text"]
                yield out
        pr.wait(timeout=30)
        if pr.returncode not in (0, None):
            err = (pr.stderr.read() or "").strip()[-400:]
            yield {"type": "error",
                   "text": f"CLI 가 코드 {pr.returncode} 로 끝났다: {err}"}
    except Exception as e:
        yield {"type": "error", "text": f"{type(e).__name__}: {e}"}
    finally:
        try:
            pr.kill()
        except Exception:
            pass
    yield {"type": "done", "selfcheck": capability.check(full)}


def _from_cli(ev: dict):
    """CLI 의 stream-json 한 줄 → 우리 사건 꼴. 모르는 것은 버린다."""
    t = ev.get("type")
    if t == "stream_event":
        d = (ev.get("event") or {}).get("delta") or {}
        if d.get("type") == "text_delta" and d.get("text"):
            yield {"type": "text", "text": d["text"]}
        elif d.get("type") == "thinking_delta" and d.get("thinking"):
            yield {"type": "thinking", "text": d["thinking"]}
        return
    if t == "assistant":
        for b in ((ev.get("message") or {}).get("content") or []):
            if b.get("type") == "tool_use":
                nm = str(b.get("name") or "")
                short = nm.split("__")[-1] if "__" in nm else nm
                yield {"type": "tool",
                       "text": f"{short}({json.dumps(b.get('input') or {}, ensure_ascii=False)})"}
        return
    if t == "result" and ev.get("is_error"):
        yield {"type": "error", "text": str(ev.get("result") or "CLI 오류")}


# ---------------------------------------------------------------- 대화
def run(question: str, strict: bool = False, verbose: bool = False,
        model: str | None = None, on_tool=None, annotate: bool = True) -> str:
    """한 번 묻고 한 번 답한다. 도구 호출은 SDK 의 tool_runner 가 돌린다.

    `on_tool` 은 도구 호출을 하나씩 받는 콜백이다 --- 웹 UI 가 **숫자의 출처**를
    화면에 보여 주는 데 쓴다. 출처를 안 보이면 사용자는 어느 숫자가 모형에서
    왔고 어느 것이 말인지 못 가른다.
    """
    from . import capability

    text = ""
    for ev in stream(question, model=model):
        if ev["type"] == "text":
            text += ev["text"]
        elif ev["type"] == "tool":
            if on_tool is not None:
                on_tool(ev["text"])
            if verbose:
                print(f"  [도구] {ev['text']}", file=sys.stderr, flush=True)
    bad = capability.check(text)
    if bad:
        # **꼬리를 두 번 붙이지 않는다.** 웹 UI 는 자기 검사를 자기가 그리므로
        # 여기서 또 붙이면 화면에 경고가 두 번 뜬다(직접 겪었다 · 노트 697).
        if not annotate:
            return text
        note = "\n\n⚠️ **자기 검사에 걸렸다**: " + " · ".join(bad)
        if strict:
            return ("답을 내보내지 않았다 --- 자기 검사에 걸렸다: "
                    + " · ".join(bad))
        return text + note
    return text


def offline(question: str) -> str:
    """열쇠가 없을 때 --- 도구를 직접 불러 원값을 낸다. 말은 안 붙인다."""
    from . import capability, ipmodel
    out = {"열쇠": "없다 --- 원값만 낸다",
           "물음": question,
           "능력카드 말할 수 없는 꼴": [f["꼴"] for f in capability.FORBIDDEN],
           "모형 보고": {k: v for k, v in ipmodel.report().items()
                      if not k.startswith("_")}}
    # 물음에 제목이 있으면 그것도 낸다
    q = question.strip().strip("\"'")
    if q:
        a = ipmodel.ask(q)
        if a.get("찾음"):
            out["제목으로 찾음"] = a
    return json.dumps(out, ensure_ascii=False, indent=1)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    strict, verbose = "--strict" in flags, "--verbose" in flags
    have_key = _load_env()
    if "--offline" in flags or not have_key:
        if not have_key and "--offline" not in flags:
            print("ANTHROPIC_API_KEY 가 없다 --- 원값 갈래로 떨어진다\n",
                  file=sys.stderr)
        print(offline(" ".join(args)))
        return
    if args:
        print(run(" ".join(args), strict, verbose))
        return
    print("대화 모드. 빈 줄로 끝낸다.")
    while True:
        try:
            q = input("\n> ").strip()
        except EOFError:
            break
        if not q:
            break
        print(run(q, strict, verbose))


if __name__ == "__main__":
    main()
