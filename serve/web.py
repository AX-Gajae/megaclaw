"""채팅 UI 서버 --- `serve/agent.py` 를 웹으로 낸다.

    python3 -m serve.web --port 8791     # http://127.0.0.1:8791

두 자리를 낸다 --- `/api/stream` 은 **SSE 로 토막을 흘리고**(기본) `/api/chat` 은
한 번에 준다(대체 · 스트림이 막힌 자리용).

**왜 표준 라이브러리인가.** 붙여 준 디자인은 Next.js + shadcn/ui + lucide 인데
스캐폴드와 `npm install` 이 무거운 의존성을 부른다. 디자인 토큰(`#262624` ·
`#30302E` · `#C2C0B6` · amber-600 · zinc 계열 · 125px 붙임 카드 · 200자 붙여넣기
임계 · 끌어놓기 덮개 `#1C3F62`)을 **그대로 옮긴 단일 파일**로 짓고 `http.server`
로 낸다. 곧 뜨고, 빌드 단계가 없고, 배급물에 새 의존성을 안 더한다.

**능력 가드는 그대로다.** 이 서버는 답을 만들지 않고 `serve.agent.run` 을 부른다
--- 시스템 프롬프트(능력 카드) · 도구 독점 · 답 뒤 자기 검사 세 겹이 그대로
걸린다. 그리고 **자기 검사 결과를 화면에 표시한다**(조용히 고치지 않는다 ·
노트 133).

**한 사람용이다.** `127.0.0.1` 에만 묶고 열쇠를 브라우저로 안 보낸다.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STATIC = Path(__file__).resolve().parent / "static"
#: 기본 백엔드. `auth` = `claude` CLI(사용자 로그인) · `api` = SDK + `.env` 키.
DEFAULT_BACKEND = os.environ.get("WM_BACKEND", "auth")
MAX_BODY = 4 * 1024 * 1024          # 붙임까지 4MB
MAX_ATTACH_CHARS = 20_000           # 한 붙임에서 프롬프트로 넣는 글자 수


def _prompt(msg: str, attachments: list) -> str:
    """붙임을 프롬프트로 접는다 --- **자른 것을 말한다**(조용히 자르지 않는다)."""
    if not attachments:
        return msg
    parts = [msg, "", "--- 사용자가 붙인 것 ---"]
    for a in attachments:
        body = str(a.get("body") or "")
        cut = len(body) > MAX_ATTACH_CHARS
        parts.append(f"\n[{a.get('kind')}] {a.get('name')}"
                     + (f"  (전체 {len(body):,}자 중 앞 {MAX_ATTACH_CHARS:,}자만)"
                        if cut else ""))
        parts.append(body[:MAX_ATTACH_CHARS])
    return "\n".join(parts)


class H(BaseHTTPRequestHandler):
    server_version = "worldmodel/1.0"

    def log_message(self, fmt, *args):          # 조용히
        if "/api/" in (self.path or ""):
            sys.stderr.write("  %s %s\n" % (self.command, self.path))

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(),
                   "application/json; charset=utf-8")

    def stream(self):
        """SSE --- 토막이 나오는 대로 내보낸다."""
        req = self._read()
        if req is None:
            return
        msg = str(req.get("message") or "").strip()
        if not msg:
            return self._json(400, {"error": "빈 물음이다"})
        from . import agent
        # **기본은 auth** --- `claude` CLI 가 사용자 로그인을 쓴다(노트 713).
        # 자격 증명을 우리가 만지지 않는다. `backend:"api"` 를 주면 SDK+키로 돈다.
        backend = str(req.get("backend") or DEFAULT_BACKEND)
        if backend == "auth" and agent.cli_path() is None:
            backend = "api"                    # CLI 가 없으면 조용히 안 떨어진다
            print("  claude CLI 가 없어 api 로 떨어진다", file=sys.stderr)
        if backend == "api" and not agent._load_env():
            return self._json(200, {"error": "auth 도 api 도 못 쓴다 --- "
                                             "`claude` CLI 가 없고 .env 에 키도 없다"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()
        prompt = _prompt(msg, req.get("attachments") or [])
        model = str(req.get("model") or "") or None
        sess = str(req.get("session") or "") or None
        try:
            self._sse({"type": "backend", "text": backend})
            gen = (agent.stream_cli(prompt, model=model, session=sess)
                   if backend == "auth" else agent.stream(prompt, model=model))
            for ev in gen:
                self._sse(ev)
        except BrokenPipeError:
            return                      # 브라우저가 떠났다 --- 조용히 끝낸다
        except Exception as e:
            traceback.print_exc()
            try:
                self._sse({"type": "error", "text": f"{type(e).__name__}: {e}"})
            except Exception:
                pass

    def do_GET(self):
        if self.path.split("?")[0] in ("/", "/index.html"):
            f = STATIC / "index.html"
            if not f.exists():
                return self._json(404, {"error": f"{f} 이 없다"})
            return self._send(200, f.read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/card":
            from . import capability
            return self._json(200, capability.card())
        if self.path == "/api/glossary":
            from . import registry
            return self._json(200, {"용어": registry.TERMS,
                                    "방향": dict(registry.DIRECTION),
                                    "능력": [{"이름": c["이름"], "꼴": c["꼴"],
                                            "산출": c["산출"],
                                            "무엇": c["설명"].split("---")[0].strip(),
                                            "자": [f"[{n}] {w} = {v}"
                                                  for n, w, v in c["자"]]}
                                           for c in registry.CAPS]})
        if self.path == "/api/warm":
            from . import boardsvc
            from . import agent
            st = boardsvc.status()
            st["백엔드"] = DEFAULT_BACKEND
            st["claude CLI"] = agent.cli_path() or "없음"
            return self._json(200, st)
        self._json(404, {"error": "없는 자리다"})

    def _read(self) -> dict | None:
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                self._json(413, {"error": f"본문이 {MAX_BODY:,} 바이트를 넘는다"})
                return None
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            self._json(400, {"error": f"본문을 못 읽었다: {e}"})
            return None

    def _sse(self, obj: dict):
        """한 사건을 내보내고 **바로 흘려보낸다** --- 안 흘리면 스트림이 아니다."""
        self.wfile.write(b"data: " + json.dumps(obj, ensure_ascii=False).encode()
                         + b"\n\n")
        self.wfile.flush()

    def do_POST(self):
        if self.path == "/api/stream":
            return self.stream()
        if self.path == "/api/research":
            return self.research()
        if self.path != "/api/chat":
            return self._json(404, {"error": "없는 자리다"})

    def research(self):
        """오토리서치 루프를 **걸어 두고 바로 돌려준다**(SSE 로 걸음을 흘린다).

        조사가 몇 분 걸리므로 동기로 잡고 있으면 창구가 멎는다. 걸음마다
        `{"type":"step"}` 을 흘리고 끝나면 `{"type":"done","result":…}` 를 낸다.
        """
        req = self._read()
        if req is None:
            return
        q = str(req.get("question") or req.get("message") or "").strip()
        if not q:
            return self._json(400, {"error": "빈 물음이다"})
        n = int(req.get("hypotheses") or 4)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        from . import research
        try:
            out = research.run(
                q, n=n,
                on_step=lambda k, v=None: self._sse(
                    {"type": "step", "걸음": k, "수": v}))
            self._sse({"type": "done", "result": out})
        except Exception as e:
            traceback.print_exc()
            self._sse({"type": "error", "text": f"{type(e).__name__}: {e}"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._json(413, {"error": f"본문이 {MAX_BODY:,} 바이트를 넘는다"})
            req = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._json(400, {"error": f"본문을 못 읽었다: {e}"})

        msg = str(req.get("message") or "").strip()
        if not msg:
            return self._json(400, {"error": "빈 물음이다"})
        model = str(req.get("model") or "") or None
        atts = req.get("attachments") or []

        try:
            from . import agent, capability
            if not agent._load_env():
                return self._json(200, {
                    "text": "**열쇠가 없다.** `.env` 에 `ANTHROPIC_API_KEY=` 를 넣으면 "
                            "말을 붙일 수 있다. 지금은 모형만 돌아간다 — "
                            "`python3 -m serve.ipmodel` 로 원값을 볼 수 있다.",
                    "tools": [], "selfcheck": []})
            tools: list = []
            text = agent.run(_prompt(msg, atts), strict=False, verbose=False,
                             model=model, on_tool=tools.append, annotate=False)
            # 에이전트가 이미 검사해 꼬리를 붙였을 수 있으므로 **원문만** 다시 본다
            return self._json(200, {"text": text, "tools": tools,
                                    "selfcheck": capability.check(text)})
        except Exception as e:
            traceback.print_exc()
            return self._json(200, {"error": f"{type(e).__name__}: {e}"})


def _warm() -> None:
    """모형을 미리 적합해 둔다 --- **첫 물음이 21초 걸리던 이유가 이것이다.**

    둘을 데운다:
      ① `ipmodel.report()` --- IP 2단 모형 팔 넷(몇 초)
      ② `boardsvc.warm()` --- **챔피언 판 한 씨앗**(몇 분). 이것이 없으면
         `domain_rank` 와 `board_overview` 가 값을 못 낸다. 그래도 서버는
         곧 뜨고, 그동안 창구는 **'아직 안 데워졌다' 고 말한다**(추측 금지).
    """
    for tag, fn in (("IP 모형", lambda: _ipwarm()), ("판", lambda: _bdwarm())):
        try:
            t = time.time()
            r = fn()
            print(f"  {tag} 데움 ({time.time()-t:.1f}초) {r}", flush=True)
        except Exception as e:                  # 데우기 실패는 치명적이지 않다
            print(f"  {tag} 데우기 실패: {type(e).__name__}: {e}", flush=True)


def _ipwarm():
    from . import ipmodel
    ipmodel.report()
    return ""


def _bdwarm():
    from . import boardsvc
    s = boardsvc.warm()
    return f"판 rho {s.get('판 rho')} · 도메인 {s.get('도메인 수')}"


def main() -> None:
    port = 8765
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"띄웠다 → http://127.0.0.1:{port}", flush=True)
    print("  (Ctrl-C 로 끝낸다 · 127.0.0.1 에만 묶었다)", flush=True)
    threading.Thread(target=_warm, daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n끝냈다", flush=True)


if __name__ == "__main__":
    main()
