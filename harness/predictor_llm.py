"""LLM 예측기 — Claude가 조건화 뱅크(과거 레코드 원문)를 읽고 2단 분해 예측을 생성.

사람의 역할은 '검토'로 축소된다:
  1차 실행  → LLM이 예측 생성 → cycle_log/<id>.prediction.json 에 _review_pending 키와 함께 저장
  검토자    → 파일 열어 확인, 수정하고 싶으면 수정, 승인이면 _review_pending 키 삭제
  2차 실행  → 봉인 + 채점 (기존 하네스 흐름 그대로)
--auto 모드는 검토 단계를 건너뛰고 생성 즉시 봉인으로 간다 (rolling 15개 폴드 일괄 실행용).

프롬프트 캐싱 설계: rolling 백테스트의 조건화 뱅크는 폴드가 진행될수록
앞부분이 그대로 유지된 채 뒤에만 자란다(시간순 정렬). 시스템 프롬프트를 동결하고
조건화 블록 끝에 cache_control 브레이크포인트를 두면 폴드 간 프리픽스 캐시가 적중한다.
"""
from __future__ import annotations

import json
from pathlib import Path

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """당신은 팝업스토어 성과 예측 모델이다. 과거 팝업 레코드 뱅크(기획·조건·실측)를 근거로, \
아직 결과를 모르는 팝업의 성과를 예측한다.

규칙:
1. 2단 분해 필수. stage1에서 총 소비자 성과(방문·소비자 매출)를 먼저 추정하고, \
stage2에서 계약 구조(수수료·고정 대행료·RS)를 산수로 적용해 rev_mm(인식 매출, 백만원)을 도출한다. \
rev_mm을 바로 찍으면 '잘 되는 팝업'이 아니라 '마진 좋은 계약'을 학습하게 된다.
2. point는 최선 추정, [low, high]는 80% 신뢰 구간. 구간이 실측을 약 80% 커버해야 캘리브레이션이 맞는 것이다. \
과잉확신(좁은 구간)을 경계하라.
3. rationale에는 어떤 과거 레코드를 어떤 근거로 참조했는지 record_id를 들어 명시한다. \
같은 브랜드·같은 공간·같은 카테고리의 반복 관측이 있으면 최우선 근거다.
4. 조건화 뱅크에는 생존 편향이 있다(실행된 팝업만 존재). 극단적 실패 사례가 없다는 이유로 하방 위험을 과소평가하지 마라.
5. 추정 불가능한 지표는 point/low/high를 null로 둔다. 억지로 채우지 마라.
6. 방문 추정 전 반드시 conditions.scale을 확인하고 스케일 산식을 명시적으로 적용하라:
   - multi_store/hybrid (store_count ≥ 2): 매장당 방문을 추정한 뒤 store_count를 곱한다. 단일 팝업 선례에 그대로 앵커하면 수 배를 놓친다.
   - host_venue (박람회 부스·몰 팝업존·유통점 입점): 방문 상한은 자체 집객이 아니라 숙주 트래픽 × 포획률이다. host_traffic_note의 모행사/몰 방문객 수에서 출발해 포획률(위치·무료여부·체험 허들에 따라 대략 5~40%)을 추정하라.
   - standalone: 유사 규모·입지의 단일 팝업 선례로 앵커한다.
   assumptions에 어떤 산식(매장 수 곱, 숙주×포획률, 선례 앵커)을 썼는지 반드시 적어라.
7. 기획서의 운영 예상치(매장당 일 방문 예상, 회차 캐파, 증정물 준비 수량, 숙주 행사 방문객)는 outcome이 아니지만 예측의 일급 증거다 — 운영자가 리스크를 걸고 산정한 숫자이므로 point의 기준선으로 사용하라. 단, 실측이 캐파·예상을 넘거나(워크인 초과) 못 미친 선례가 뱅크에 있으면 그 비율로 보정하고 구간을 양쪽으로 열어라. 예상치를 무시하고 보수적 선례 앵커만 쓰는 것이 이 시스템의 반복된 과소예측 원인이었다.
8. conditions.capacity가 session/invite/reservation이면 total_capacity가 방문의 물리적 천장이다 — point는 천장 이하에서 소진율(초청 노쇼, 회차 공석)을 추정해 정하고, high가 천장을 넘으면 안 된다(워크인 병행이 명시된 경우만 예외, 그 근거를 assumptions에 적어라). 좌석·초청 행사를 자유입장 팝업 선례로 앵커하는 것이 반복된 대형 과대예측 원인이었다. 반대로 계약 금액의 크기는 소비자 접점 규모의 증거가 아니다(대행 예산↛방문 — B2B·제작비 비중이 클 수 있음).
9. <market_bank>는 언론·주최측 발표 기반 시장 선례다 — 내부 실측과 등급이 다르다. 사용법: ⑴ 같은 IP의 시장 선례는 일평균 스케일의 1차 앵커다(내부 선례가 없을 때 특히). ⑵ 스토어 스코프의 주최측 발표는 실측 대비 약 ×1.1 온건 팽창으로 보정하라. ⑶ 장소가 '일대·권역·역' 단위인 수치는 스코프가 다르므로 스토어 방문 앵커로 쓰지 마라. ⑷ 완판·웨이팅 신호는 수요 강도의 정성 증거다. rationale에 시장 선례를 쓰면 MKT-ID를 인용하라."""

PREDICTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["stage1_gross", "stage2_contract_transform", "totals", "rationale"],
    "properties": {
        "stage1_gross": {
            "type": "object",
            "additionalProperties": False,
            "required": ["gross_consumer_sales_krw", "visitors_total", "assumptions"],
            "properties": {
                "gross_consumer_sales_krw": {"$ref": "#/$defs/interval"},
                "visitors_total": {"$ref": "#/$defs/interval"},
                "assumptions": {"type": "string"},
            },
        },
        "stage2_contract_transform": {"type": "string"},
        "totals": {
            "type": "object",
            "additionalProperties": False,
            "required": ["visitors", "sales_krw", "rev_mm_recognized"],
            "properties": {
                "visitors": {"$ref": "#/$defs/interval"},
                "sales_krw": {"$ref": "#/$defs/interval"},
                "rev_mm_recognized": {"$ref": "#/$defs/interval"},
            },
        },
        "rationale": {"type": "string"},
    },
    "$defs": {
        "interval": {
            "type": "object",
            "additionalProperties": False,
            "required": ["point", "low", "high"],
            "properties": {
                "point": {"type": ["number", "null"]},
                "low": {"type": ["number", "null"]},
                "high": {"type": ["number", "null"]},
            },
        }
    },
}


def _canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1)


def build_conditioning_text(conditioning_manifest: list[dict]) -> str:
    """레코드 전문(원문 인덱스 포함)을 시간순·결정론적으로 직렬화. 폴드 간 프리픽스 안정성이 캐시의 생명."""
    parts = ["<conditioning_bank>"]
    for entry in conditioning_manifest:
        record = json.loads(Path(entry["record_path"]).read_text(encoding="utf-8"))
        parts.append(f'<record id="{entry["record_id"]}">')
        parts.append(_canon(record))
        parts.append("</record>")
    parts.append("</conditioning_bank>")
    return "\n".join(parts)


DIGEST_THRESHOLD = 80  # 이 이상이면 다이제스트+관련 전문 모드 (컨텍스트 한계 대응)


def _feat_tag(r: dict) -> str:
    """파생 피처 압축 표기 (2026-07-27 쌍둥이 해부 채택분): 신뢰등급·주말율·IP회차·캡."""
    c, o = r["conditions"], r["outcome"]
    parts = []
    lt = (o.get("label_trust") or {}).get("grade")
    if lt:
        parts.append(f"T:{lt}")
    der = c.get("derived") or {}
    du = der.get("duration") or {}
    if du.get("weekend_share") is not None:
        h = f"+휴{du['holiday_days']}" if du.get("holiday_days") else ""
        parts.append(f"주말{int(du['weekend_share']*100)}%{h}")
    ih = der.get("ip_history") or {}
    if ih:
        parts.append("IP초회" if ih.get("first_edition") else f"IP{ih['prior_count']+1}회차({ih['months_since_last']}mo전)")
    cap = (c.get("capacity") or {}).get("access_type")
    if cap in ("session", "invite", "reservation"):
        tc = (c.get("capacity") or {}).get("total_capacity")
        parts.append(f"캡:{cap}" + (f"({tc:,})" if tc else ""))
    return " ".join(parts)


def _digest_line(r: dict, features: bool = True) -> str:
    c, o = r["conditions"], r["outcome"]
    sc = c.get("scale") or {}
    comp = (o.get("rev_mm_completion") or {}).get("status", "?")
    vis = o["totals"].get("visitors")
    vs = f'{vis}({o.get("counting_method","?")})' if vis else "—"
    rev = o["totals"].get("rev_mm_recognized")
    ct = (o.get("rev_mm_completion") or {}).get("contract_total_mm")
    ft = f' | {_feat_tag(r)}' if features and _feat_tag(r) else ""
    return (f'{r["record_id"]} | {c["period"].get("from","?")}~{c["period"].get("to","?")} '
            f'| {c["location"].get("venue_type") or "?"} | {sc.get("venue_traffic_type","?")}×{sc.get("store_count","?")} '
            f'| brand:{r["entities"].get("brand_key","?")} space:{r["entities"].get("space_key","?")} '
            f'| 방문 {vs} | rev {rev}({comp}, 계약 {ct}) | {r["intervention"]["concept"][:45]}{ft}')


FEAT_LEGEND = ("표기 범례 — T:라벨신뢰등급(A=정밀집계·일별표, B=주최발표 단정, C=하한값 '이상/돌파'로 실제는 그 위, "
               "D=존/지점 혼합 합산이라 단위 왜곡, E=예상·추산 재활용 의심 — C/D/E 앵커는 액면 그대로 쓰지 말 것), "
               "주말%=기간 중 주말일 비중(+휴=공휴일 수), IPn회차=같은 IP의 n번째 개최(초회=신규성 프리미엄 가능, "
               "재개최는 직전 간격 참고), 캡:=입장 방식이 회차/초청/예약제(공급 상한 존재)")


def build_digest(conditioning_manifest: list[dict], features: bool = True) -> str:
    lines = ["<conditioning_digest>",
             "형식: code | 기간 | 공간유형 | 스케일구조×매장수 | 엔티티키 | 방문(집계기준) | rev_mm(완결상태, 계약총액) | 컨셉 | 피처"]
    if features:
        lines.append(FEAT_LEGEND)
    for entry in conditioning_manifest:
        r = json.loads(Path(entry["record_path"]).read_text(encoding="utf-8"))
        lines.append(_digest_line(r, features))
    lines.append("</conditioning_digest>")
    return "\n".join(lines)


def select_relevant(conditioning_manifest: list[dict], target_stimulus: dict, cap: int = 15) -> list[dict]:
    """타깃과 같은 브랜드·공간 전부 + 같은 스케일 유형 최근 + 최근 일반 — 전문 포함 대상."""
    te = target_stimulus.get("entities", {})
    tsc = (target_stimulus.get("conditions", {}).get("scale") or {}).get("venue_traffic_type")
    loaded = [(e, json.loads(Path(e["record_path"]).read_text(encoding="utf-8"))) for e in conditioning_manifest]
    picked, seen = [], set()

    def add(entry):
        if entry["record_id"] not in seen and len(picked) < cap:
            seen.add(entry["record_id"]); picked.append(entry)

    for e, r in loaded:
        if te.get("brand_key") and r["entities"].get("brand_key") == te.get("brand_key"): add(e)
        if te.get("space_key") and r["entities"].get("space_key") == te.get("space_key"): add(e)
    for e, r in reversed(loaded):
        if tsc and (r["conditions"].get("scale") or {}).get("venue_traffic_type") == tsc and \
           r["outcome"]["totals"].get("visitors"): add(e)
    for e, _ in reversed(loaded):
        add(e)
    return picked


STATE_RULE = """
10. <world_state> 블록이 주어지면 이것이 예측 시점의 세계 상태다 — 앵커·산식 위에 상태 보정을 적용하고, assumptions에 어떻게 반영했는지 명시하라. 존재하는 필드만 사용:
   - latent_neighbors: 이 팝업의 오픈 전 관심 고객들이 과거에 함께 본 스토어들(=같은 소비자 풀을 공유한 취향 이웃). 이웃의 오픈 전 수요 실측(총·피크 조회)은 취향으로 검증된 앵커다 — 뱅크 다이제스트에서 같은 이름의 팝업을 찾아 그 실측 방문과 연결하라. 단 조회수→방문수 전환율은 미지이므로 절대값 직역 금지, 이웃 간 상대 비교로 써라.
   - cluster_attention_trend: 이 취향 클러스터의 관심 방향(>1 상승, <1 냉각) — point를 그 방향으로 기울여라.
   - entity_history: 같은 브랜드·공간의 직전 실측 — 존재 시 1차 앵커.
   - popga_pre_open_buzz: 오픈 전 관심 선행 지표 (0은 미등록일 수 있으니 하향 증거 금지)."""


_INTERVAL_PATHS = [("stage1_gross", "gross_consumer_sales_krw"), ("stage1_gross", "visitors_total"),
                   ("totals", "visitors"), ("totals", "sales_krw"), ("totals", "rev_mm_recognized")]


def _merge_median(runs: list[dict]) -> dict:
    """K개 독립 예측의 필드별 중앙값 병합 — 게이트 2 리팩토링으로 core.llm_runtime에 일반화, 여기는 팝업 스키마 바인딩."""
    from core.llm_runtime import merge_median
    return merge_median(runs, _INTERVAL_PATHS)


class LLMPredictor:
    def __init__(self, cycle_dir: str | Path, model: str = MODEL, auto: bool = False,
                 state_file: str | Path | None = None, ensemble: int = 1, market: bool = True,
                 signals: bool = True, features: bool = True,
                 shuffle_sig: bool = False, shuffle_feat: bool = False):
        import hashlib
        self.cycle_dir = Path(cycle_dir)
        self.model = model
        self.auto = auto
        self.market = market
        self.signals = signals
        self.shuffle_sig = shuffle_sig
        self.shuffle_feat = shuffle_feat
        self.features = features
        self.ensemble = max(1, int(ensemble))
        self.state = {}
        if state_file and Path(state_file).exists():
            self.state = json.loads(Path(state_file).read_text(encoding="utf-8"))
        # 프롬프트 버전 봉인: 시스템 프롬프트+스키마 해시가 커밋에 영구 기록됨.
        # 홀드아웃 실패를 보고 프롬프트를 고치면 해시가 바뀜 → 어느 버전이 어느 홀드아웃을
        # '소모(burn)'했는지 추적 가능. 버전이 다른 커밋의 성능은 합산 집계 금지.
        from core.llm_runtime import prompt_version
        self.system_prompt = SYSTEM_PROMPT + (STATE_RULE if self.state else "")
        pv = prompt_version(self.system_prompt, PREDICTION_SCHEMA)
        self.prompt_version = pv
        mode = "+state" if self.state else ""
        ens = f"+median{self.ensemble}" if self.ensemble > 1 else ""
        mkt = "" if self.market else "-nomkt"
        sig = ("-shufsig" if self.shuffle_sig else "") if self.signals else "-nosig"
        ft = ("-shuffeat" if self.shuffle_feat else "") if self.features else "-nofeat"
        self.predictor_id = f"llm:{model}@prompt-{pv}{mode}{ens}{mkt}{sig}{ft}"

    def predict(self, target_stimulus: dict, conditioning_manifest: list[dict]) -> dict | None:
        record_id = target_stimulus["record_id"]
        pending = self.cycle_dir / f"{record_id}.prediction.json"

        if pending.exists():
            pred = json.loads(pending.read_text(encoding="utf-8"))
            if "_review_pending" in pred:
                return None  # 검토 대기 — 승인하려면 _review_pending 키를 지우고 재실행
            for k in list(pred):
                if k.startswith("_"):
                    pred.pop(k)
            return pred

        if self.ensemble > 1:
            # run variance 실측(2026-07-24: run 중앙값 8~27% 산포) 대응 — K회 독립 실행의
            # 필드별 중앙값을 예측으로 삼아 노이즈 성분을 깎는다. 개별 런은 _ensemble_runs로 감사 보존.
            runs = [self._generate(target_stimulus, conditioning_manifest) for _ in range(self.ensemble)]
            prediction = _merge_median(runs)
        else:
            prediction = self._generate(target_stimulus, conditioning_manifest)

        payload = dict(prediction)
        if self.ensemble > 1:
            payload["_ensemble_runs"] = runs
        payload["_generated_by"] = self.predictor_id
        if not self.auto:
            payload["_review_pending"] = (
                "LLM 생성 예측. 검토 후 이 키(_review_pending)를 지우고 재실행하면 봉인됩니다. "
                "수치를 수정해도 됩니다 — 봉인 전이므로 정당합니다."
            )
        self.cycle_dir.mkdir(parents=True, exist_ok=True)
        pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        if not self.auto:
            print(f"LLM 예측 생성됨 → {pending} (검토 대기)")
            return None
        for k in list(payload):
            if k.startswith("_"):
                payload.pop(k)
        return payload

    def _generate(self, target_stimulus: dict, conditioning_manifest: list[dict]) -> dict:
        import anthropic

        from core.noapi import assert_free  # 노트 889 — 유료 API 기본 차단
        assert_free("predictor_llm")
        client = anthropic.Anthropic()
        relevant_block = ""
        if len(conditioning_manifest) > DIGEST_THRESHOLD:
            conditioning_text = build_digest(conditioning_manifest, features=self.features)
            rel = select_relevant(conditioning_manifest, target_stimulus)
            relevant_block = "\n" + build_conditioning_text(rel).replace(
                "<conditioning_bank>", "<relevant_records_full>").replace(
                "</conditioning_bank>", "</relevant_records_full>") + "\n"
        else:
            conditioning_text = build_conditioning_text(conditioning_manifest)
        from .market_bank import build_market_block
        market_block = build_market_block(target_stimulus, signals=self.signals,
                                          shuffle_sig=self.shuffle_sig,
                                          shuffle_feat=self.shuffle_feat,
                                          features=self.features) if self.market else ""
        state_block = ""
        st = self.state.get(target_stimulus["record_id"])
        if st:
            state_block = f"\n<world_state>\n예측 시점의 세계 상태 (오픈 전 데이터만):\n{_canon(st)}\n</world_state>\n"
        target_text = (
            relevant_block
            + "<target>\n예측 대상 팝업 (기획서+계약서 정보만, outcome 없음):\n"
            + _canon(target_stimulus)
            + "\n</target>\n" + state_block
            + "\n위 팝업의 성과를 예측하라. 2단 분해와 상태 보정을 지켜라. "
            "방문 예측은 반드시 타깃과 같은 counting 기준의 선례에 앵커하라 (다이제스트의 집계기준 표기 참조)."
        )

        from core.llm_runtime import stream_structured
        return stream_structured(
            client,
            model=self.model,
            system=[{"type": "text", "text": self.system_prompt}],
            messages=[{
                "role": "user",
                "content": [
                    # 브레이크포인트 ①: 내부 뱅크 다이제스트 — 폴드가 진행돼도 앞부분이 그대로 자라는
                    # 최장 안정 프리픽스. 여기에 캐시를 걸어야 폴드 간에도 접두사가 적중한다.
                    # (2026-07-27 비용 사고: 시장층 도입 때 이 브레이크포인트를 빼고 시장 블록 뒤에만
                    #  두는 바람에, 폴드마다 달라지는 시장 블록이 앞의 대형 다이제스트까지 캐시 무효화 →
                    #  캐시쓰기 18.1M 토큰 발생. 브레이크포인트 2개로 복원.)
                    {"type": "text", "text": conditioning_text,
                     "cache_control": {"type": "ephemeral"}},
                    # 브레이크포인트 ②: 시장 층 — 폴드마다 다르지만 앙상블 K회 내에서는 동일
                    {"type": "text", "text": market_block or "<market_bank 없음>",
                     "cache_control": {"type": "ephemeral"}},
                    # 타깃: 매 호출 고유 — 브레이크포인트 뒤
                    {"type": "text", "text": target_text},
                ],
            }],
            schema=PREDICTION_SCHEMA,
            effort="high",
            tag=self.predictor_id,
        )
