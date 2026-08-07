"""실험 기록 저장소 --- 모든 실행이 여기로 흐른다.

노트 124까지의 구조는 ``한 번 깨어남 = 한 노트''였고, 그래서 루프의 크기가
한 사이클로 고정됐다. 큰 루프를 돌리려면 **실행이 노트와 분리**돼야 한다 ---
실험은 수백 번 돌고 논문은 프로그램이 끝날 때 나온다.

의존성 없음(sqlite3 · 표준 라이브러리만). 동시 쓰기를 위해 WAL 을 켠다.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

DB = Path(os.environ.get("LAB_DB", "data/lab/lab.db"))
_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  formulation TEXT NOT NULL,
  program TEXT,
  status TEXT NOT NULL,           -- running | done | failed | killed
  started REAL NOT NULL,
  ended REAL,
  config TEXT,                    -- json
  summary TEXT,                   -- json (headline numbers)
  note TEXT
);
CREATE TABLE IF NOT EXISTS metrics (
  run_id TEXT NOT NULL, step INTEGER NOT NULL,
  key TEXT NOT NULL, value REAL, ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_metrics ON metrics(run_id, key, step);
CREATE TABLE IF NOT EXISTS scores (
  run_id TEXT NOT NULL, split TEXT NOT NULL, target TEXT NOT NULL,
  metric TEXT NOT NULL, value REAL, lo REAL, hi REAL
);
CREATE INDEX IF NOT EXISTS ix_scores ON scores(run_id);
CREATE TABLE IF NOT EXISTS guards (
  run_id TEXT NOT NULL, name TEXT NOT NULL,
  passed INTEGER NOT NULL, detail TEXT
);
CREATE INDEX IF NOT EXISTS ix_guards ON guards(run_id);
CREATE TABLE IF NOT EXISTS events (
  run_id TEXT, ts REAL NOT NULL, level TEXT NOT NULL, msg TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events ON events(ts);
CREATE TABLE IF NOT EXISTS portfolio (
  formulation TEXT PRIMARY KEY,
  status TEXT NOT NULL,           -- champion | challenger | retired | idea
  born REAL NOT NULL,
  best REAL,                      -- 대표 점수
  best_run TEXT,
  idea TEXT,                      -- 한 줄 설명
  killed_why TEXT
);
"""


def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=30.0, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


def init() -> None:
    with _LOCK, _conn() as c:
        c.executescript(SCHEMA)


def q(sql: str, args: tuple = ()) -> list[dict]:
    with _LOCK, _conn() as c:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def x(sql: str, args: tuple = ()) -> None:
    with _LOCK, _conn() as c:
        c.execute(sql, args)


# ── 실행 ───────────────────────────────────────────────────────────────
class Run:
    """with Run('F1', program='P0') as r: r.log(...); r.score(...)"""

    def __init__(self, formulation: str, program: str = "", config: dict | None = None,
                 note: str = ""):
        init()
        self.id = uuid.uuid4().hex[:12]
        self.formulation = formulation
        self.program = program
        self.t0 = time.time()
        self._step = 0
        x("INSERT INTO runs(id,formulation,program,status,started,config,note)"
          " VALUES(?,?,?,?,?,?,?)",
          (self.id, formulation, program, "running", self.t0,
           json.dumps(config or {}, ensure_ascii=False), note))
        upsert_formulation(formulation)

    # 시계열 --- 학습 곡선 · 손실 · 무엇이든
    def log(self, step: int | None = None, **kv) -> None:
        if step is None:
            self._step += 1
            step = self._step
        ts = time.time()
        with _LOCK, _conn() as c:
            c.executemany(
                "INSERT INTO metrics(run_id,step,key,value,ts) VALUES(?,?,?,?,?)",
                [(self.id, step, k, float(v), ts) for k, v in kv.items()
                 if v is not None])

    # 최종 점수 --- 하네스가 부른다
    def score(self, split: str, target: str, metric: str, value: float,
              lo: float | None = None, hi: float | None = None) -> None:
        x("INSERT INTO scores(run_id,split,target,metric,value,lo,hi)"
          " VALUES(?,?,?,?,?,?,?)",
          (self.id, split, target, metric, float(value), lo, hi))

    def guard(self, name: str, passed: bool, detail: str = "") -> None:
        x("INSERT INTO guards(run_id,name,passed,detail) VALUES(?,?,?,?)",
          (self.id, name, 1 if passed else 0, detail))

    def event(self, msg: str, level: str = "info") -> None:
        x("INSERT INTO events(run_id,ts,level,msg) VALUES(?,?,?,?)",
          (self.id, time.time(), level, msg))

    def finish(self, status: str = "done", summary: dict | None = None) -> None:
        x("UPDATE runs SET status=?, ended=?, summary=? WHERE id=?",
          (status, time.time(),
           json.dumps(summary or {}, ensure_ascii=False), self.id))
        # 포트폴리오 순위는 유보 표본의 판 rho. z 는 가드지 순위가 아니다
        # (F8 부스팅이 rho 최저인데 z 최고로 나온 사건 — lab/loop.py::rank_key)
        v = (summary or {}).get("pooled")
        if v is None:
            v = (summary or {}).get("headline")
        if v is not None and v == v:                      # nan 제외
            bump_formulation(self.formulation, float(v), self.id)

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if et is not None:
            self.event(f"{et.__name__}: {ev}", "error")
            self.finish("failed")
        return False


# ── 포트폴리오 ─────────────────────────────────────────────────────────
def upsert_formulation(name: str, status: str = "challenger", idea: str = "") -> None:
    r = q("SELECT formulation FROM portfolio WHERE formulation=?", (name,))
    if not r:
        x("INSERT INTO portfolio(formulation,status,born,idea) VALUES(?,?,?,?)",
          (name, status, time.time(), idea))
    elif idea:
        x("UPDATE portfolio SET idea=? WHERE formulation=?", (idea, name))


def bump_formulation(name: str, headline: float, run_id: str) -> None:
    r = q("SELECT best FROM portfolio WHERE formulation=?", (name,))
    if r and (r[0]["best"] is None or headline > r[0]["best"]):
        x("UPDATE portfolio SET best=?, best_run=? WHERE formulation=?",
          (headline, run_id, name))


def set_status(name: str, status: str, why: str = "") -> None:
    x("UPDATE portfolio SET status=?, killed_why=? WHERE formulation=?",
      (status, why, name))


def event(msg: str, level: str = "info") -> None:
    init()
    x("INSERT INTO events(run_id,ts,level,msg) VALUES(NULL,?,?,?)",
      (time.time(), level, msg))


# ── 견줄 수 있나 ───────────────────────────────────────────────────────
def comparable(run_a: str, run_b: str) -> dict:
    """두 실행의 도메인 점수를 **뺄 수 있나**.

    오늘(노트 274 · 275) 같은 병에 세 번 걸렸다 --- 저장소에 축 세트
    ``이름``만 남아서, 이름이 같은 07-30 실행과 07-31 실행의 차를 뺐고 그
    차가 통째로 잡음이었다. 노트 262 · 263이 그 사이에 웹툰 두 열을 막았고
    이름은 안 변했다.

    ``지문``(노트 275에서 넣음)이 있는 실행끼리는 도메인마다 열이 같은지
    바로 답할 수 있다. 지문이 없는 옛 실행은 ``모름``으로 돌려준다 ---
    **모름은 ``같다''가 아니다.**
    """
    import json as _json
    rows = {r["id"]: r for r in
            q("SELECT id,formulation,config,started FROM runs WHERE id IN (?,?)",
              (run_a, run_b))}
    if len(rows) < 2:
        return {"판정": "실행 없음"}

    def fp(rid):
        try:
            return (_json.loads(rows[rid]["config"] or "{}") or {}).get("지문")
        except Exception:
            return None

    fa, fb = fp(run_a), fp(run_b)
    if not fa or not fb:
        return {"판정": "모름", "왜": "지문 없는 실행(노트 275 이전) --- 빼지 말 것",
                "지문있음": {run_a: bool(fa), run_b: bool(fb)}}
    same = sorted(d for d in fa if d != "_전체" and fa.get(d) == fb.get(d))
    diff = sorted(d for d in set(fa) | set(fb)
                  if d != "_전체" and fa.get(d) != fb.get(d))
    return {"판정": "전부 같음" if not diff else "일부 다름",
            "뺄 수 있는 도메인": same, "열이 변한 도메인": diff,
            "전체": fa.get("_전체") == fb.get("_전체")}
