"""LLM 런타임 (도메인 무관) — 구조화 출력 호출·재시도, 앙상블 중앙값 병합, 프롬프트 버전 해시.

도메인 어댑터(팝업/아이돌/…)는 프롬프트·스키마·다이제스트만 소유하고, 호출 역학은 여기서 공유한다.
게이트 2 리팩토링(2026-07-27)으로 harness/predictor_llm.py에서 추출 — 동작·해시 완전 동일.
"""
from __future__ import annotations

import hashlib
import json
import time


def prompt_version(system_prompt: str, schema: dict) -> str:
    """시스템 프롬프트+출력 스키마의 sha256 앞 10자 — 예측기 버전 장부의 키."""
    return hashlib.sha256((system_prompt + json.dumps(schema, sort_keys=True)).encode()).hexdigest()[:10]


def stream_structured(client, *, model: str, system: list, messages: list, schema: dict,
                      effort: str = "high", max_tokens: int = 16000, tag: str = "") -> dict:
    """구조화 출력 스트리밍 호출 + 5회 재시도(20s×n 백오프). 사용량 로그와 refusal 처리 포함."""
    import anthropic

    response = None
    for attempt in range(5):
        try:
            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                thinking={"type": "adaptive"},
                output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
                system=system,
                messages=messages,
            ) as stream:
                response = stream.get_final_message()
            break
        except anthropic.APIStatusError as e:
            if attempt == 4:
                raise
            wait = 20 * (attempt + 1)
            print(f"  [{tag}] API {getattr(e, 'status_code', '?')} 재시도 {attempt+1} ({wait}s)", flush=True)
            time.sleep(wait)

    u = response.usage
    print(f"  [{tag}] in={u.input_tokens} cache_read={u.cache_read_input_tokens} "
          f"cache_write={u.cache_creation_input_tokens} out={u.output_tokens}")
    if response.stop_reason == "refusal":
        raise RuntimeError(f"{model} 이 예측을 거부함 — stop_details: {response.stop_details}")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def merge_median(runs: list[dict], interval_paths: list[tuple[str, str]],
                 rep_path: tuple = ("totals", "visitors", "point"),
                 text_fields: tuple = (("stage1_gross", "assumptions"), ("stage2_contract_transform",),
                                        ("rationale",))) -> dict:
    """K개 독립 예측의 필드별 중앙값 병합 (도메인 스키마는 interval_paths로 주입).

    수치는 point/low/high 각각 중앙값(null 제외, 전부 null이면 null). 서술 필드는
    rep_path 값이 병합 중앙값에 가장 가까운 대표 런에서 가져온다."""
    import statistics as st

    def med(vals):
        vals = [v for v in vals if v is not None]
        return st.median(vals) if vals else None

    def get(d, path):
        for k in path:
            d = d.get(k) if isinstance(d, dict) else None
            if d is None:
                return None
        return d

    merged = json.loads(json.dumps(runs[0]))
    for sec, key in interval_paths:
        for bound in ("point", "low", "high"):
            merged[sec][key][bound] = med([r[sec][key].get(bound) for r in runs])

    target = get(merged, rep_path)
    rep = runs[0]
    if target is not None:
        cands = [r for r in runs if get(r, rep_path) is not None]
        if cands:
            rep = min(cands, key=lambda r: abs(get(r, rep_path) - target))
    for path in text_fields:
        if len(path) == 1:
            merged[path[0]] = rep[path[0]]
        else:
            merged[path[0]][path[1]] = rep[path[0]][path[1]]
    if "rationale" in merged:
        merged["rationale"] = f"[median-of-{len(runs)} 앙상블 — 대표 런의 근거] " + rep["rationale"]
    return merged
