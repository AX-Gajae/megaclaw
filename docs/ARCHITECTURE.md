# 아키텍처 경계 명세 — 코어 vs 도메인 어댑터

게이트 2 리팩토링(2026-07-27) 산출물. 2호 도메인(아이돌 데뷔 등)이 꽂힐 소켓의 정의다.
해설서는 `docs/architecture.html`, 실행 이력은 메모리 `project-build-roadmap.md`.

## 계층 분류 (현재 모듈)

### 코어 — 도메인 무관 (새 도메인이 그대로 공유)
| 모듈 | 역할 |
|---|---|
| `core/llm_runtime.py` | 구조화 출력 호출·5회 재시도, 앙상블 중앙값 병합(`merge_median` — 스키마는 interval_paths로 주입), 프롬프트 버전 해시 |
| `harness/cycle.py` | 예측 봉인(sha256)·검증·사이클 로그 |
| `harness/score.py` | APE·구간 적중 채점, 완결 라벨 가드 |
| `harness/gate.py` | 자극 빈곤 게이트 메커니즘 (pass/widen/refuse, 구간 강제 확대) — **임계값(1200/450자, F=4.5)은 팝업 실측 튜닝값: 새 도메인은 자기 데이터로 재캘리브레이션** |

### 팝업 어댑터 — 도메인 소유물 (새 도메인은 이 목록을 자기 것으로 대체)
| 모듈 | 역할 |
|---|---|
| `schema/popup_record.schema.json` | 레코드 스키마 (자극/조건/결과) |
| `harness/records.py` | 레코드 로더·검증 |
| `harness/predictor_llm.py` | 시스템 프롬프트(규칙 1–9)·출력 스키마·내부 다이제스트·관련 전문 선택·피처 태그 |
| `harness/market_bank.py` | 시장 층 다이제스트 (시간 마스크·신호·피처) |
| `harness/baselines.py` | naive 1/2/3 |
| `harness/latent_state.py` | popga 잠재 상태 (챌린저) |
| `ingest/*` | 정규화·라벨 발굴·신뢰등급·파생 피처·시장 편입 |

### 파이프라인 — 얇은 조립층 (도메인 준중립, 재사용 가능)
`harness/backtest.py`(홀드아웃 1건: 게이트→예측→봉인→채점), `rolling.py`, `runvar.py`,
`market_backtest.py`(페어드 절제), `forward.py`(주간 전향 4단계, 크론).

### 운영
`forward_run.sh` + crontab(월 09:00) · `data/ingest/`(인제스트 산출물 — 스크래치패드에서 이관됨,
**절대 임시폴더에 두지 말 것**) · `rotate_key.sh`.

## 도메인 어댑터 계약 — 새 도메인이 제공해야 하는 7가지

1. **레코드 스키마**: `{자극(개입), 조건, 결과}` 3분할. 결과는 예측 시 절대 노출 금지.
2. **라벨 온톨로지**: "결과 숫자가 무엇을 센 것인가"의 enum (팝업의 entry/participation/…에 해당)
   + 라벨 신뢰등급(A~E) 태깅 규칙. **수집 전에 정의할 것** — 이걸 늦게 하면 100배 오차 사고가 재현된다.
3. **자극 빌더**: 타깃 → 예측 입력 (시간 마스크 내장, 실측 누출 필드 차단 목록 포함).
4. **다이제스트 빌더**: 뱅크 1줄 요약 + 관련 전문 선택 + 피처 태그·범례.
5. **프롬프트 + 출력 스키마**: 도메인 규칙 (2단 분해에 해당하는 도메인 분해 구조 포함).
   출력 스키마의 interval_paths를 `merge_median`에 바인딩.
6. **naive 베이스라인 3종**: 카테고리 중앙값 / 최근접 선례 / 업계 사전 예상치.
7. **게이트 임계값 캘리브레이션**: 자기 도메인 빈곤 폴드에서 widen 배율 역산 (팝업은 80분위=4.5).

## 실행 경로 — 종량제 API vs 구독 에이전트 (2026-07-27 비용 사고 후 확립)

하루 $297이 종량제 API로 나간 사고(원인: ①절제 실험 3종을 API로 실행 ②캐시 브레이크포인트
오설정으로 캐시쓰기 18.1M 토큰) 후, **무인 실행이 필요한 것만 API로 남기는** 정책을 세웠다.

| 작업 | 경로 | 명령 | 비용 |
|---|---|---|---|
| 백테스트·절제 실험·탐색 | **agent** | `backtest --predictor agent` | $0 (구독) |
| 라벨 채굴 | **agent** | `mine_labels --agent-dir DIR` | $0 |
| 계약서 재독해 | **agent** | `fee_contractize --agent-dir DIR` | $0 |
| 문서 정규화·자극 보강 | **agent** | `bulk_normalize/enrich_stimulus --agent-dir DIR` | $0 |
| **전향 봉인 주간 크론** | **api 유지** | `forward.py` (월 09:00) | 주 6~9회 ≈ $2/주 |

**2패스 프로토콜** (`core/agent_task.py` / `harness/predictor_agent.py`):
1. 1패스 — 파이썬이 Drive 문서 추출·조건화 조립까지 하고 요청을 `{task_id}.req.json`
   (또는 예측은 `{code}.request.md`)으로 덤프하고 그 항목을 스킵. **API 호출 0**.
2. 에이전트 — req를 Read → system·schema대로 추론 → `{task_id}.res.json` Write.
   대기 목록은 `core.agent_task.pending(dir)`로 조회.
3. 2패스 — 같은 스크립트 재실행. res를 읽어 레코드 패치·봉인·채점. **API 호출 0**.

역할 분리 원칙: **문서 추출·병합·판정은 파이썬**(remotezip·pptx XML·pdf·BQ — 에이전트가 하기엔
느리거나 불가), **LLM 추론만 에이전트**. 멱등이라 몇 번 재실행해도 안전하다.

무결성: predictor_id가 `agent:{model}@...`로 구분되며, **모델이 다르므로 API 경로 성적(16~18%)과
합산 금지** — 버전 장부 원칙 그대로. 에이전트 경로로 전환하면 그 트랙의 소진선을 새로 측정해야 한다.

## 불변 조건 (건드리면 장부가 깨진다)

- **프롬프트 버전 해시** = sha256(시스템 프롬프트 + 출력 스키마). 현재 팝업 v3 = `a9149081da`.
  프롬프트를 고치면 버전이 갈리고, 버전 간 성적 합산 금지.
- **봉인 후 불변**: 커밋 파일은 수정 금지. 재채점은 봉인 재사용(API 무호출).
- **시간 마스크**: 조건화·시장층·파생 피처(ip_history) 전부 타깃 오픈일 이전 정보만.
- **평가 프로토콜**: 조건 비교는 페어드 절제 + (백테스트면) 반복≥3. 소모 폴드는 버전별 장부 관리.
- **GCP 읽기 전용**: BQ SELECT·Drive 읽기만. 쓰기는 전부 로컬.

## 남은 부채 (의도적으로 이번에 안 건드림 — KIOF 4일 전)

- backtest/rolling/runvar/market_backtest 간 중복 조립 로직 → 실전 1사이클 후 통합.
- `harness/records.py`가 팝업 스키마에 결합 → 도메인 2 착수 시 RecordSet 인터페이스로 추상화.
- gate 임계값의 도메인 파라미터화 (현재 모듈 상수).
- 버전 관리 부재: world_model은 git 저장소가 아님 — **git init 권장** (사용자 결정 사항).
