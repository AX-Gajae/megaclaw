# 매핑 워크시트 (2026-07-23 생성, 전부 로컬 — BQ에는 아무것도 쓰지 않음)

블록 1의 전제인 "정제 67건 engagement→venue/brand 매핑"용. 자동 후보는 제안일 뿐이고 confirmed_* 컬럼을 사람이 채우는 것이 완료 조건.

| 파일 | 내용 | 자동 후보 수율 |
|---|---|---|
| `venue_mapping_worksheet.csv` | 67건 전체 + 이름 매칭 venue 후보 최대 3개 + confirmed 빈 컬럼 | 62건 중 15건 |
| `venue_candidates_via_property.csv` | property(건물명) 경유 보조 후보 | 14건 |
| `popga_spot_candidates.csv` | popga(sophy) 스팟 후보 — 이름+오픈일 ±45일 매칭 | 4건 (주토피아 5개점, 쿠키런 등) |

수율이 낮은 이유: core.venue 마스터가 주소 문자열 위주라 프로젝트의 공간 표기("성수 키다리스튜디오 사옥")와 텍스트가 겹치지 않음. popga는 내부 프로젝트명과 소비자용 스팟명 관례가 다름. → 나머지는 수기 확인이 정공법이고, 이 워크시트는 그 수기 작업의 시작점.

완료 후: confirmed_venue_id/confirmed_brand_id가 채워지면 이 CSV가 `engagement_venue` 적재용 원천이 된다. **적재는 데이터 담당자가 수행** (이 저장소는 BQ에 쓰지 않는 원칙).
