"""예측 커밋(해시 봉인) + 사이클 로그. 블록 1(백테스트)과 블록 2(전향)가 공유하는 심장부.

봉인 규칙: 예측 JSON을 정규화(canonical)해서 sha256. 커밋 파일에는 예측 원문과 해시,
조건화에 쓴 재료 목록(manifest)이 함께 박힌다. 사후에 예측을 고치면 해시가 깨진다.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def canonical(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def seal_hash(prediction: dict) -> str:
    return hashlib.sha256(canonical(prediction).encode("utf-8")).hexdigest()


def commit_prediction(
    cycle_dir: str | Path,
    record_id: str,
    prediction: dict,
    conditioning_manifest: list[dict],
    predictor_id: str,
    mode: str,  # "backtest" | "forward"
) -> Path:
    cycle_dir = Path(cycle_dir)
    cycle_dir.mkdir(parents=True, exist_ok=True)
    commit = {
        "record_id": record_id,
        "mode": mode,
        "predictor_id": predictor_id,
        "prediction": prediction,
        "prediction_sha256": seal_hash(prediction),
        "conditioning_manifest": conditioning_manifest,
        "committed_at": datetime.now(timezone.utc).isoformat(),
    }
    path = cycle_dir / f"{record_id}.commit.json"
    if path.exists():
        raise FileExistsError(f"{path} 이미 봉인됨 — 커밋은 불변. 새 예측이면 record_id를 바꾸거나 커밋을 명시적으로 폐기할 것.")
    path.write_text(json.dumps(commit, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def verify_commit(commit_path: str | Path) -> bool:
    commit = json.loads(Path(commit_path).read_text(encoding="utf-8"))
    return seal_hash(commit["prediction"]) == commit["prediction_sha256"]


def append_cycle_log(
    cycle_dir: str | Path,
    record_id: str,
    stimulus_ref: dict,
    conditions_ref: dict,
    prediction: dict,
    actual: dict,
    scores: dict,
) -> Path:
    """(자극, 조건, 예측, 실측, 채점) 튜플 누적 — 자생하는 RCT 뱅크."""
    path = Path(cycle_dir) / "cycle_log.jsonl"
    row = {
        "record_id": record_id,
        "stimulus": stimulus_ref,
        "conditions": conditions_ref,
        "prediction": prediction,
        "actual": actual,
        "scores": scores,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path
