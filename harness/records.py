"""popup_record 로드 + 최소 검증. 스키마 전체 검증은 수기 검수 단계의 몫."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REQUIRED_TOP = ["record_id", "schema_version", "entities", "intervention", "conditions", "docs", "provenance"]
REQUIRED_ENTITIES = ["brand_id", "space_id"]


class RecordError(ValueError):
    pass


@dataclass
class PopupRecord:
    path: Path
    data: dict

    @property
    def record_id(self) -> str:
        return self.data["record_id"]

    @property
    def start(self) -> date:
        return date.fromisoformat(self.data["conditions"]["period"]["from"])

    @property
    def has_outcome(self) -> bool:
        return bool(self.data.get("outcome"))

    @property
    def doc_uris(self) -> list[dict]:
        return self.data.get("docs", [])

    def validate(self) -> list[str]:
        problems = []
        for k in REQUIRED_TOP:
            if k not in self.data:
                problems.append(f"필수 필드 누락: {k}")
        ent = self.data.get("entities", {})
        for k in REQUIRED_ENTITIES:
            if not ent.get(k):
                problems.append(f"entities.{k} 누락 — 블록 3 조인 키, 미해소면 'unresolved:<이름>'으로라도 채울 것")
        if not self.data.get("docs"):
            problems.append("docs 비어 있음 — 조건화 시점 원문 사용 원칙 위반")
        prov = self.data.get("provenance", {})
        if prov.get("extracted_by", "").startswith("llm:") and not prov.get("reviewed_by"):
            problems.append("LLM 추출인데 reviewed_by 없음 — 수기 검수 전까지 미완성 취급")
        return problems


def load_records(records_dir: str | Path) -> list[PopupRecord]:
    records = []
    for p in sorted(Path(records_dir).glob("*.json")):
        with open(p, encoding="utf-8") as f:
            rec = PopupRecord(path=p, data=json.load(f))
        problems = rec.validate()
        if problems:
            raise RecordError(f"{p.name}: " + "; ".join(problems))
        records.append(rec)
    return sorted(records, key=lambda r: r.start)
