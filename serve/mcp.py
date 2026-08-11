"""월드모델을 **MCP 서버**로 내보낸다 --- `claude` CLI 가 우리 능력을 부를 수 있게.

**왜 이것이 필요한가.** 사용자가 *"api 말고 auth 로 돌려 달라"* 고 했다.
구독 토큰을 꺼내 SDK 에 꽂는 방법도 있지만 **그 자격 증명은 Claude Code 용으로
발급된 것**이고 다른 앱을 돌리라고 준 것이 아니다. 그래서 그 길로 안 간다.

**대신 지원되는 길로 간다** --- `claude` CLI 를 그대로 백엔드로 쓴다. CLI 는
사용자가 이미 한 로그인을 쓰고, `--mcp-config` 로 우리 도구를 붙일 수 있다.
즉 **Claude Code 를 Claude Code 로 쓰면서 우리 모형만 얹는다.**

    python3 -m serve.mcp                 # stdio 로 대기(직접 부를 일은 없다)
    claude -p --mcp-config <설정> ...     # `serve/agent.py` 가 이렇게 부른다

**프로토콜은 손으로 쓴다.** JSON-RPC 2.0 over stdio 이고 우리가 쓰는 것은 셋뿐
(`initialize` · `tools/list` · `tools/call`)이라 SDK 의존성을 새로 더할 이유가 없다.
도구 목록은 `serve/registry.py` 에서 온다 --- **손으로 두 벌 적지 않는다**(노트 701).
"""
from __future__ import annotations

import json
import sys
import traceback

NAME = "worldmodel"
VERSION = "1.0.0"
PROTO = "2024-11-05"


def _reg():
    from . import registry
    return registry


def _tools() -> list:
    """등록소 → MCP 도구 목록. 설명 앞에 `산출` 을 박아 창구가 못 놓치게 한다."""
    out = []
    for c in _reg().CAPS:
        rulers = " · ".join(f"[노트 {n}] {w} = {v}" for n, w, v in c["자"])
        #: 🔴 **층과 떠받치는 출력을 같이 박는다**(노트 911). 창구가 "무엇을 할 수
        #: 있나" 를 물을 때, **옛 13능력 중 다섯이 ②(결과) 하나**를 떠받치고 ①④⑤ 에
        #: 붙는 것은 `event_brief` 하나뿐(그것도 「못 잼」을 낸다)이라는 사실이
        #: 도구 목록에서 보여야 한다.
        out.append({
            "name": c["이름"],
            "description": (f"{c['설명']}\n\n"
                            f"산출: {c['산출']} · 꼴: {c['꼴']}\n"
                            f"층: {c.get('층')} · 떠받치는 출력: "
                            f"{' · '.join(c.get('떠받치는 출력') or ['없음'])}\n"
                            f"자: {rulers}"),
            "inputSchema": c["입력"],
        })
    return out


def _call(name: str, args: dict) -> str:
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
    return out if isinstance(out, str) else json.dumps(out, ensure_ascii=False,
                                                       default=str)


def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        mid, method = req.get("id"), req.get("method")
        try:
            if method == "initialize":
                res = {"protocolVersion": PROTO,
                       "capabilities": {"tools": {}},
                       "serverInfo": {"name": NAME, "version": VERSION}}
            elif method == "tools/list":
                res = {"tools": _tools()}
            elif method == "tools/call":
                p = req.get("params") or {}
                res = {"content": [{"type": "text",
                                    "text": _call(p.get("name", ""),
                                                  p.get("arguments") or {})}]}
            elif method in ("notifications/initialized", "notifications/cancelled"):
                continue                       # 알림에는 답하지 않는다
            elif method in ("resources/list", "prompts/list"):
                res = {"resources": []} if method.startswith("resources") else {"prompts": []}
            else:
                if mid is None:
                    continue
                _send({"jsonrpc": "2.0", "id": mid,
                       "error": {"code": -32601, "message": f"없는 method: {method}"}})
                continue
        except Exception as e:                 # 서버가 죽으면 창구가 통째로 막힌다
            traceback.print_exc(file=sys.stderr)
            if mid is not None:
                _send({"jsonrpc": "2.0", "id": mid,
                       "error": {"code": -32603, "message": f"{type(e).__name__}: {e}"}})
            continue
        if mid is not None:
            _send({"jsonrpc": "2.0", "id": mid, "result": res})


if __name__ == "__main__":
    main()
