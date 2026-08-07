# PLAN — 한국 팝업스토어 시장 실측 레코드 수집 (KOREA POPUP MARKET RECORDS)

## 임무 요약
- 2023-01 ~ 2026-07 한국 팝업스토어 중 **outcome 숫자(방문객/매출/대기)가 있는 이벤트 500건+** 수집
- 모든 수치 = (source_quote, source_url, source_date) 3종 세트 필수. 추정/계산 금지.
- 산출물: `records.jsonl` + `report.md` (스키마/규칙은 임무 파일 그대로)
- 스킬: `deep-research-swarm` (Route B 변형 — 명확한 차원 분할 병렬 수집 + 적대적 검증)

## Stage 0 — 준비
- 출력 디렉토리: /mnt/agents/output/popup_records/
- 임무 스키마/규칙을 수집 에이전트 프롬프트에 그대로 탑재

## Stage 1 — PASS 1 수집 (Wave 1: 카테고리×8 병렬)
각 수집 에이전트 목표 35건+, 2025~2026 비중 60%+, 2023~2026 분기 커버:
1. 캐릭터/IP (포켓몬, 산리오, 디즈니, 치이카와, 카카오프렌즈, 짱구 등)
2. F&B (디저트/베이커리/커피/식품)
3. 뷰티 (올리브영, 아모레, 로드샵, 글로벌 뷰티)
4. 패션/스트릿/럭셔리 (무신사, 29CM, 명품)
5. 엔터/아이돌 (하이브, SM, JYP, YG, 케이팝 MD 팝업)
6. 게임/웹툰/애니 (넥슨, 원신, 네이버웹툰, 카카오페이지 등)
7. 전자/가전/자동차/주류/기타
8. 성수동 전담 (성수연방, 성수이로, LCDC 등 — 카테고리 무관, 성수 팝업 전반)

## Stage 2 — 병합/중복제거 + 분포 분석
- 기준: brand + venue + period 겹침 → 병합, 출처 전부 보존
- 분기×카테고리 분포 집계 → 빈 영역 식별

## Stage 3 — PASS 1 보강 (Wave 2: 갭 필러)
- 빈 분기/카테고리/장소(더현대 서울, 롯데월드몰, 신세계 강남, 코엑스, 부산/지방) 전담 에이전트 fan-out
- 누적 500건+ 도달까지 반복

## Stage 4 — PASS 2 적대적 검증
- 검증 에이전트 그룹 (레코드당 3-check): (a) URL 접속해 quote 존재 (b) 숫자 일치 (c) counting_basis 정합
- 실패 시 verification:"failed" 표시(삭제 금지). 통과율 리포트 포함.

## Stage 5 — 통합 산출
- records.jsonl (최종), report.md (통계: 총 건수, 검증 통과율, 분기×카테고리, counting_basis 분포, 방문객 min/median/max, 상충 건수, 공백 영역)

## 에이전트 운영
- 동시 백그라운드 에이전트 최대 8, 웨이브 단위 stage-gate
- 수집 에이전트: preset `general` (웹검색+페이지방문 필요) / 검증: `verifier`
