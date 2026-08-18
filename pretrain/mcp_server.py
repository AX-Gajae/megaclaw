# -*- coding: utf-8 -*-
"""MCP 서버 — 월드모델 도구층을 Claude(하네스 LLM)에 노출한다.

stdio 전송(개행 구분 JSON-RPC 2.0). 의존성 0.
등록: 저장소 루트 .mcp.json 이 이 파일을 가리킨다 — 이 저장소에서 여는
Claude Code 세션은 wm_* 도구 일곱을 자동으로 갖는다.

⚠ stdout 은 프로토콜 전용 — 진단은 전부 stderr 로.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import json
import sys


def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    print("[worldmodel-mcp] 모형 적재 중…", file=sys.stderr, flush=True)
    from pretrain import wm_tools                        # 여기서 LM·전이 모형 적재
    tools = [{"name": t["name"], "description": t["description"],
              "inputSchema": t["inputSchema"]} for t in wm_tools.MANIFEST]
    print("[worldmodel-mcp] 준비 완료 — 도구 %d" % len(tools), file=sys.stderr, flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
        except Exception:
            continue
        mid, method = m.get("id"), m.get("method", "")
        params = m.get("params") or {}
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "worldmodel", "version": "0.1.0"}}})
        elif method.startswith("notifications/"):
            continue                                     # 알림엔 응답하지 않는다
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": tools}})
        elif method == "tools/call":
            out = wm_tools.call(params.get("name"), params.get("arguments") or {})
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text",
                             "text": json.dumps(out, ensure_ascii=False, indent=1)}],
                "isError": bool(isinstance(out, dict) and "오류" in out)}})
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": mid, "result": {}})
        elif mid is not None:
            send({"jsonrpc": "2.0", "id": mid,
                  "error": {"code": -32601, "message": "unknown method %s" % method}})


if __name__ == "__main__":
    main()
