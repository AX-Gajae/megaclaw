# -*- coding: utf-8 -*-
"""초경량 MCP 프록시 — 상시 창구(8899)로 위임한다. torch 적재 0.

왜 프록시인가: 채팅 서버(`serve/web.py`)의 백엔드는 `claude -p` 이고, CLI 는
«매 턴» MCP 서버를 새로 띄운다. `pretrain/mcp_server.py` 는 모형을 직접 적재해
턴마다 수 초를 먹는다 — 이 프록시는 표준 라이브러리만으로 뜨자마자 준비되고,
실제 계산은 이미 떠 있는 창구(serve.py · 127.0.0.1:8899)가 한다.

창구가 꺼져 있으면: 도구 목록은 비고, 호출은 켜는 법을 담은 오류를 돌려준다.
"""
import json
import sys
import urllib.request

WM_BASE = "http://127.0.0.1:8899"
HINT = ("월드모델 창구(8899)가 꺼져 있다 — cd /Users/ax/world_model && "
        "nohup python3 pretrain/serve.py > /Users/ax/wm_harvest/foundation/serve.log "
        "2>&1 & disown")


def _http(path, payload=None, timeout=180):
    req = urllib.request.Request(
        WM_BASE + path,
        data=(json.dumps(payload, ensure_ascii=False).encode("utf-8")
              if payload is not None else None),
        method=("POST" if payload is not None else "GET"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    try:
        tools = _http("/api/manifest", timeout=5)
    except Exception:
        tools = []
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
                "serverInfo": {"name": "wm", "version": "0.1.0"}}})
        elif method.startswith("notifications/"):
            continue
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": tools}})
        elif method == "tools/call":
            try:
                out = _http("/api/tool", {"name": params.get("name"),
                                          "arguments": None,  # (미사용 키 방지)
                                          "args": params.get("arguments") or {}})
            except Exception as e:                        # noqa: BLE001
                out = {"오류": "%s — %s" % (type(e).__name__, HINT)}
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text",
                             "text": json.dumps(out, ensure_ascii=False, indent=1)}],
                "isError": bool(isinstance(out, dict) and "오류" in out)}})
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": mid, "result": {}})
        elif mid is not None:
            send({"jsonrpc": "2.0", "id": mid,
                  "error": {"code": -32601, "message": "unknown %s" % method}})


if __name__ == "__main__":
    main()
