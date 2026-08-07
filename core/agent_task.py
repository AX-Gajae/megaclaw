"""에이전트 작업 프로토콜 — 종량제 API 호출을 구독 세션 내 서브에이전트로 대체.

배경(2026-07-27): 인제스트·예측을 종량제 API로 돌려 하루 $297 발생. 무인 크론이 아닌 작업은
세션 에이전트가 처리하면 추가 비용이 0이다.

역할 분리:
  파이썬  Drive 문서 추출(remotezip·pptx XML·pdf), 레코드 입출력, 병합·판정 로직 — 에이전트가
          하기엔 느리거나 불가능한 것
  에이전트 LLM 추론(구조화 출력) — 종량제 API가 하던 바로 그 부분

2패스 프로토콜:
  1패스  call()이 요청을 {dir}/{task_id}.req.json 으로 덤프하고 None 반환 → 스크립트는 그 항목을 스킵
  (에이전트) req.json 을 읽고 스키마대로 추론 → {dir}/{task_id}.res.json 에 저장
  2패스  같은 스크립트 재실행 → call()이 res.json 을 읽어 즉시 반환 (API·에이전트 호출 0)

멱등성: res.json 이 있으면 항상 그것을 쓴다. 스크립트는 몇 번 재실행해도 안전하다.
"""
from __future__ import annotations

import json
from pathlib import Path


class AgentTask:
    """agent 모드면 요청을 파일로 덤프, api 모드면 즉시 API 호출."""

    def __init__(self, mode: str, task_dir: str | Path | None = None, client=None,
                 model: str = "claude-opus-4-8", effort: str = "low", max_tokens: int = 8000):
        assert mode in ("api", "agent")
        self.mode = mode
        self.dir = Path(task_dir) if task_dir else None
        self.client = client
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.dumped = 0
        self.loaded = 0
        if self.dir:
            self.dir.mkdir(parents=True, exist_ok=True)

    def call(self, task_id: str, system: str, schema: dict, user: str) -> dict | None:
        """구조화 출력 1건. agent 모드에서 응답이 아직 없으면 None(=이번 패스 스킵)."""
        if self.mode == "api":
            from core.llm_runtime import stream_structured
            return stream_structured(
                self.client, model=self.model,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
                schema=schema, effort=self.effort, max_tokens=self.max_tokens, tag=task_id)

        res = self.dir / f"{task_id}.res.json"
        if res.exists():
            self.loaded += 1
            out = json.loads(res.read_text(encoding="utf-8"))
            return out.get("result", out)
        req = self.dir / f"{task_id}.req.json"
        if not req.exists():
            req.write_text(json.dumps(
                {"task_id": task_id, "system": system, "schema": schema, "user": user},
                ensure_ascii=False, indent=1), encoding="utf-8")
            self.dumped += 1
        return None

    def report(self) -> str:
        if self.mode == "api":
            return "api 모드"
        return (f"agent 모드 — 신규 요청 {self.dumped}건 덤프 / 응답 적용 {self.loaded}건"
                + (f"\n요청 디렉토리: {self.dir}" if self.dumped else ""))


def pending(task_dir: str | Path) -> list[str]:
    """응답 대기 중인 task_id 목록 (에이전트에게 배분할 작업 목록)."""
    d = Path(task_dir)
    if not d.exists():
        return []
    return sorted(p.stem[:-4] for p in d.glob("*.req.json")
                  if not (d / f"{p.stem[:-4]}.res.json").exists())
