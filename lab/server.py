"""모니터링 서버 --- 의존성 없음(표준 라이브러리만).

    python3 -m lab.server            # 7801 포트
    python3 -m lab.server --port 9000

`/`      다크 UI
`/api/*` JSON
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import store

UI = Path(__file__).parent / "ui.html"


def api(path: str, qs: dict) -> object:
    g = lambda k, d=None: (qs.get(k) or [d])[0]
    if path == "/api/runs":
        lim = int(g("limit", 200))
        rows = store.q(
            "SELECT id,formulation,program,status,started,ended,summary,note"
            " FROM runs ORDER BY started DESC LIMIT ?", (lim,))
        for r in rows:
            try:
                r["summary"] = json.loads(r["summary"] or "{}")
            except Exception:
                r["summary"] = {}
        return rows
    if path == "/api/run":
        rid = g("id")
        r = store.q("SELECT * FROM runs WHERE id=?", (rid,))
        if not r:
            return {"error": "no such run"}
        r = r[0]
        for k in ("config", "summary"):
            try:
                r[k] = json.loads(r[k] or "{}")
            except Exception:
                r[k] = {}
        r["metrics"] = store.q(
            "SELECT step,key,value FROM metrics WHERE run_id=? ORDER BY step",
            (rid,))
        r["scores"] = store.q(
            "SELECT split,target,metric,value,lo,hi FROM scores WHERE run_id=?",
            (rid,))
        r["guards"] = store.q(
            "SELECT name,passed,detail FROM guards WHERE run_id=?", (rid,))
        r["events"] = store.q(
            "SELECT ts,level,msg FROM events WHERE run_id=? ORDER BY ts DESC"
            " LIMIT 300", (rid,))
        return r
    if path == "/api/portfolio":
        return store.q("SELECT * FROM portfolio ORDER BY"
                       " CASE status WHEN 'champion' THEN 0"
                       " WHEN 'challenger' THEN 1 WHEN 'baseline' THEN 2"
                       " WHEN 'idea' THEN 3 ELSE 4 END, best DESC")
    if path == "/api/board":
        return store.q(
            "SELECT r.formulation, s.target, s.split, MAX(s.value) v,"
            " COUNT(*) n FROM scores s JOIN runs r ON r.id=s.run_id"
            " GROUP BY r.formulation, s.target, s.split")
    if path == "/api/events":
        since = float(g("since", 0))
        return store.q(
            "SELECT ts,level,msg,run_id FROM events WHERE ts>? "
            "ORDER BY ts DESC LIMIT 200", (since,))
    if path == "/api/stat":
        a = store.q("SELECT status, COUNT(*) n FROM runs GROUP BY status")
        b = store.q("SELECT COUNT(*) n FROM scores")
        c = store.q("SELECT COUNT(*) n FROM portfolio")
        return {"runs": a, "scores": b[0]["n"] if b else 0,
                "forms": c[0]["n"] if c else 0, "now": time.time()}
    return {"error": "unknown endpoint"}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, body: bytes, ctype: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/api/"):
            try:
                body = json.dumps(api(u.path, parse_qs(u.query)),
                                  ensure_ascii=False).encode()
                self._send(body, "application/json; charset=utf-8")
            except Exception as e:
                self._send(json.dumps({"error": str(e)}).encode(),
                           "application/json", 500)
            return
        if u.path in ("/", "/index.html"):
            self._send(UI.read_bytes(), "text/html; charset=utf-8")
            return
        self._send(b"not found", "text/plain", 404)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7801)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    store.init()
    srv = ThreadingHTTPServer((a.host, a.port), H)
    print(f"실험실 모니터  http://{a.host}:{a.port}", flush=True)
    store.event(f"모니터 서버 시작 {a.host}:{a.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
