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
        #: 🔴 **학습 기록 뷰어**(노트 912 팔 ㅇ) --- L6 창구. `/api/brief` 를 안 건드린다.
        if self.path.split("?")[0] in ("/trainlog", "/trainlog.html"):
            f = STATIC / "trainlog.html"
            if not f.exists():
                return self._json(404, {"error": f"{f} 이 없다"})
            return self._send(200, f.read_bytes(), "text/html; charset=utf-8")
        if self.path.split("?")[0].startswith("/api/trainlog"):
            return self.trainlog()
        if self.path == "/api/card":
            from . import capability
            return self._json(200, capability.card())
        if self.path == "/api/glossary":
            from . import registry
            return self._json(200, {"용어": registry.TERMS,
                                    "방향": dict(registry.DIRECTION),
                                    "능력": [{"이름": c["이름"], "꼴": c["꼴"],
                                            "산출": c["산출"],
                                            "층": c.get("층"),
                                            "떠받치는 출력": c.get("떠받치는 출력"),
                                            "무엇": c["설명"].split("---")[0].strip(),
                                            "자": [f"[{n}] {w} = {v}"
                                                  for n, w, v in c["자"]]}
                                           for c in registry.CAPS]})
        #: 🔴 하네스 자기서술(노트 911) --- 층 · 층별 능력 수 · 다섯 출력별 상태 ·
        #: 게이트 자가검사. **"무엇을 할 수 있나" 의 정직한 판본**이다.
        if self.path == "/api/harness":
            from . import layers, registry
            return self._json(200, {
                "층": layers.census(), "계층 검사": layers.check(),
                "등록소 검사": registry.check(),
                "게이트 자가검사": layers.gate_selftest(),
                "L2 이벤트 표": layers.eventline(),
                "🔴 오늘 0 인 출력": {
                    "③시점": "이벤트 표는 생겼으나 간격 예측 판정이 없다(노트 769·910)",
                    "④개선": "A등급 개입 효과가 위약 한복판(노트 903)",
                    "⑤파생": "합류점 0개(노트 897 · 파이썬 604개 전수 AST)"}})
        if self.path == "/api/warm":
            from . import boardsvc
            from . import agent
            st = boardsvc.status()
            st["백엔드"] = DEFAULT_BACKEND
            st["claude CLI"] = agent.cli_path() or "없음"
            return self._json(200, st)
        self._json(404, {"error": "없는 자리다"})

    def trainlog(self):
        """`GET /api/trainlog/*` --- **학습 기록을 읽기만 한다**(노트 912 팔 ㅇ).

        자리 넷.

            /api/trainlog/runs                run 목록
            /api/trainlog/run?id=…            한 run 의 전부(manifest·곡선·구조·뉴런)
            /api/trainlog/metrics?id=…        곡선만
            /api/trainlog/arch?id=…&max_neurons=…&px_height=…   뉴런 그림만
            /api/trainlog/blocks?id=…&fold=0|1   🔴 블록 다이어그램(그림 1 꼴)
            /api/trainlog/tail?id=…&since_bytes=N  🔴 실시간 --- **새 줄만**
            /api/trainlog/selftest            🔴 이 창구의 자를 잰다

        🔴 **HTTP 200 을 성공으로 읽지 마라**(조항 59). 지표가 없는 run 은 200 을
        주면서 `곡선 수 = 0` 과 「비었다」를 낸다 --- 그것이 정직한 답이다.
        """
        from urllib.parse import parse_qs, urlparse
        u = urlparse(self.path)
        q = parse_qs(u.query or "")
        rid = (q.get("id") or [""])[0]
        mx = (q.get("max_neurons") or ["32"])[0]
        px = (q.get("px_height") or ["620"])[0]
        fold = (q.get("fold") or ["1"])[0] not in ("0", "false", "no")
        since = (q.get("since_bytes") or ["0"])[0]
        try:
            since = int(since)
        except Exception:
            since = 0
        #: 🔴 누른 자리만 펼친다 · 곡선에서 고른 step 을 그래프에 얹는다
        exp = [x for x in (q.get("expand") or [""])[0].split(",") if x]
        step = (q.get("step") or [""])[0] or None
        met = (q.get("node_metric") or ["grad_norm"])[0]
        try:
            from . import trainlog_svc as tl
        except Exception as e:
            return self._json(200, {"error": f"학습 기록 창구를 못 불렀다: "
                                             f"{type(e).__name__}: {e}"})
        try:
            tail = u.path[len("/api/trainlog"):].strip("/")
            if tail in ("", "runs", "index"):
                return self._json(200, tl.runs() if tail != "index" else tl.index())
            if tail == "selftest":
                return self._json(200, tl.selftest())
            #: 🔴 런 비교 패널 --- run 여럿을 나란히(사이드바·겹친 곡선·평행좌표)
            if tail == "compare":
                return self._json(200, tl.compare(
                    (q.get("target") or [""])[0]))
            if not rid:
                return self._json(400, {"error": "`id=` 가 없다 --- 어떤 run 인가"})
            if tail == "run":
                return self._json(200,
                                  tl.detail(rid, mx, px, fold, exp, step, met))
            if tail == "nodestate":
                return self._json(200, tl.nodestate(rid, step, met))
            if tail == "metrics":
                return self._json(200, tl.metrics(rid))
            if tail == "arch":
                return self._json(200, tl.neurons(rid, mx, px))
            if tail == "blocks":
                return self._json(200, tl.blocks(rid, fold, exp))
            #: 🔴 실시간 --- **새로 붙은 줄만** 낸다(전량 재전송 금지)
            if tail == "tail":
                return self._json(200, tl.tail(rid, since))
            return self._json(404, {"error": f"없는 자리다: {u.path}"})
        except Exception as e:
            traceback.print_exc()
            return self._json(200, {"error": f"{type(e).__name__}: {e}",
                                    "말": "학습 기록을 읽다가 터졌다 --- "
                                        "**곡선을 지어내지 않는다**"})

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
        #: 🔴 **L5 조립 창구**(노트 911) --- 이벤트 하나를 받아 다섯 절을 낸다.
        #: 이 자리는 **LLM 을 부르지 않는다** --- 모형이 안 낸 숫자가 말로 섞여
        #: 들어올 자리를 아예 안 만든다(유료 API 도 안 탄다).
        if self.path == "/api/brief":
            return self.brief()
        if self.path != "/api/chat":
            return self._json(404, {"error": "없는 자리다"})
        return self.chat()

    def brief(self):
        """`POST /api/brief` --- 이벤트 → 다섯 절.

        🔴 **HTTP 200 을 성공으로 읽지 마라**(조항 59). 이 자리는 200 을 주면서
        다섯 절 중 넷이 「못 잼」·「못 읽음」인 것이 **정상**이다. 응답의
        `요약`·`조립 검사`·`금지 꼴 게이트` 를 봐라.
        """
        req = self._read()
        if req is None:
            return
        try:
            from . import brief as _b
            out = _b.event_brief(req.get("event") or req)
        except Exception as e:
            traceback.print_exc()
            return self._json(200, {"error": f"{type(e).__name__}: {e}",
                                    "말": "조립이 터졌다 --- 다섯 절을 못 냈다"})
        return self._json(200, out)

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

    def chat(self):
        """스트림이 막힌 자리용 --- 한 번에 답을 준다.

        🔴 **이 몸통은 `research()` 꼬리에 붙어 있었다**(노트 911 팔 ㅅ 이 찾았다).
        `do_POST` 는 `/api/chat` 에 대해 **아무것도 안 하고 돌아갔고**(끝의 `if` 가
        404 만 내고 끝났다) 그래서 이 자리는 **응답을 한 글자도 안 보냈다** ---
        조사가 끝난 뒤에야 본문을 다시 읽으려 해서 언제나 400 이었다.
        고친 것은 **자리뿐**이고 논리는 그대로다(되돌릴 수 있게).
        """
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
        except SystemExit as e:
            #: 🔴 `core/noapi.assert_free` 는 **`SystemExit`** 로 막는다(노트 889).
            #: 그것은 `Exception` 이 아니라서 아래 `except` 에 안 걸리고, 그러면
            #: 이 실이 조용히 죽어 **응답이 한 글자도 안 나간다** --- 브라우저에는
            #: "연결이 끊겼다" 로만 보인다. 막힌 것과 터진 것은 다르다(조항 59).
            return self._json(200, {
                "error": "종량제 API 가 막혀 있다(사용자 상시 지시 · 노트 889)",
                "말": str(e),
                "대신": "`/api/stream` 은 기본이 `auth`(claude CLI) 라 열쇠 없이 돈다. "
                      "그리고 `/api/brief` 는 **LLM 을 아예 안 부른다**",
                "tools": [], "selfcheck": []})
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
    #: 🔴 `--no-warm` --- 데우기(판 적합 **약 340초**)를 건너뛴다(노트 911).
    #: 왜 필요한가: CPU 를 다른 팔과 나눠 쓰는 자리에서 창구만 확인하고 싶을 때가
    #: 있다. **건너뛰면 `②결과` 가 「못 읽음」으로 나가고 그것이 정직한 답이다** ---
    #: 창구는 그때도 다섯 절을 다 낸다(추측으로 메우지 않는다).
    nowarm = "--no-warm" in sys.argv or os.environ.get("WM_NO_WARM") == "1"
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"띄웠다 → http://127.0.0.1:{port}", flush=True)
    print("  (Ctrl-C 로 끝낸다 · 127.0.0.1 에만 묶었다)", flush=True)
    if nowarm:
        print("  🔴 --no-warm: 판을 안 데운다 --- `②결과` 는 '못 읽음' 으로 나간다",
              flush=True)
    else:
        threading.Thread(target=_warm, daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n끝냈다", flush=True)


if __name__ == "__main__":
    main()
