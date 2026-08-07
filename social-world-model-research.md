# 소셜 월드모델(Social World Model) 딥리서치 보고서

작성일: 2026-07-22 · 딥리서치 워크플로우(106개 에이전트, 24개 소스, 25개 주장 3표 적대적 검증) + 보강 리서치 2건 종합

---

## 1. 소셜 월드모델이란 — 정의와 연구 계보

### 1.1 개념의 기원

- **용어의 공식 출처**: Zhou, Liu, Yerukola, Kim, Sap, *"Social World Models"* (arXiv:2509.00559, **NeurIPS 2025**). 의도·신념·진화하는 사회적 상태 등 **관찰 불가능한 사회 역학의 명시적 표현**으로 정의. 정적 텍스트 학습이 사회 역학 이해에 실패하는 이유로 (1) 보고 편향(reporting bias), (2) 정신 상태 표현 부재, (3) 전지적 시점 문제를 지목.
- 같은 논문이 **S3AP**(structured social world representation)를 제안 — 자유 텍스트 대신 에이전트들의 상태·행동·정신 상태를 POMDP 기반 구조화 튜플로 표현. FANToM(ToM 벤치마크)에서 o1 대비 **+51%**, SOTOPIA 멀티턴 상호작용에서 최대 **+18%** 개선 보고 (저자 자기보고, 독립 재현 미확인).

### 1.2 계보: World Models → Mental/Social World Models

1. **Ha & Schmidhuber (2018), World Models** (arXiv:1803.10122) — 기점. RL 환경의 압축 시공간 표현을 비지도 학습하는 생성 신경망. Vision(VAE) + Memory(MDN-RNN, P(z_{t+1}|a_t,z_t,h_t)) + Controller. 월드모델이 생성한 'dream' 안에서만 학습한 정책을 실제 환경으로 이전 가능함을 증명(VizDoom, τ=1.15 조건) — **시뮬레이션 기반 합성 데이터 전략의 이론적 토대**.
2. **Mental World Model 리뷰** (arXiv:2601.02378, ZTE, 프리프린트) — 물리적 월드모델(관찰 가능한 물리 상태)과 구분해, 타 에이전트의 신념·의도·감정·욕구·도덕 가치를 추론하는 Mental World Model을 정의하고, 이를 집단 수준으로 확장한 것이 소셜 월드모델. 형식적으로 **N-agent Dec-POMDP** + Theory of Mind 기반 타 에이전트 행동 예측.
3. **Agentic World Modeling 서베이** (arXiv:2604.22748, HKUST/NUS/Oxford/NTU) — 월드모델의 지배 법칙 regime 중 하나로 '사회 세계(Laws of the Social World)'를 정의. 사회 세계 전이의 고유 난제 두 가지: **반사성(reflexivity)** — 상태에 대한 신념이 상태 자체를 바꿈, **규범성(normativity)** — '일어날 일'뿐 아니라 '일어나야 할 일'의 지배. 사회 regime 대표 벤치마크로 Sotopia 지목.
4. **창발적 소셜 월드모델 증거** (arXiv:2602.10298, **ACL 2026**) — 48개 LM에서 ToM 성능과 화용추론 성능 간 상관 r=0.68 (p=1.24e-7). 기능적 국소화로 찾은 ToM 서브네트워크를 절제하면 화용추론도 인과적으로 저하(β=0.30) → LM 내부에 기능적으로 통합된 정신상태 표현(소셜 월드모델)이 창발한다는 증거. (저자들은 'suggestive evidence'로 헤지)

### 1.3 핵심 응용 논문

- **Sotopia** (ICLR 2024) — LLM 에이전트 사회지능 평가의 사실상 표준 벤치마크. SOTOPIA-π(ACL 2024), MPO(arXiv:2505.02156) 등 후속 채택으로 지위 확인.
- **ToMAgent/ToMA** (arXiv:2509.22887) — 대화 턴 사이에 정신 상태를 생성하는 프롬프팅만으로도 목표 지향 대화가 유의하게 개선. ToM + 대화 lookahead 학습으로 Sotopia에서 베이스라인 능가.
- **Generative Agents** (Stanford Smallville, 2023) — LLM 에이전트 사회 시뮬레이션의 원형. 단, 공개된 "데이터셋"은 없고 Apache-2.0 시뮬레이터만 존재.

### 1.4 대규모 사회 시뮬레이터 (합성 데이터 인프라)

| 시스템 | 규모 | 특징 | 공개 |
|---|---|---|---|
| **AgentSociety** (칭화대, arXiv:2502.08691) | 1만+ 에이전트, 500만 상호작용 | 현실적 사회 환경, 양극화/UBI/재난 등 계산 사회실험 | github.com/tsinghua-fib-lab/agentsociety |
| **OASIS** (camel-ai, arXiv:2411.11581) | 최대 100만 사용자 | X/Reddit형 SNS 시뮬레이션, 추천시스템 포함, 정보확산·양극화·군집효과 재현 | github.com/camel-ai/oasis |
| **SOTOPIA-S4** (CMU, NAACL 2025 demo) | — | pip 패키지, API 서버 + 웹 UI, 비개발자용 멀티턴·멀티파티 시뮬레이션 | pip install |
| **Concordia** (DeepMind) | — | 게임마스터 패턴 GABM 라이브러리, v2.0 엔티티-컴포넌트 구조 | github.com/google-deepmind/concordia |

⚠️ 알려진 충실도 문제: LLM 에이전트는 인간 대비 **사회적 아첨 과다**(감정적 검증 76% vs 22%), **분산 과소**(과잉 동질화), **군집 효과 과민**(OASIS 논문 자체 보고), **페르소나 붕괴**(긴 대화에서 assistant 성향 회귀). → 합성 데이터만으로 학습 금지, 인간 데이터 캘리브레이션 세트 필수.

---

## 2. 공개 데이터셋 카탈로그 (검증일 2026-07-22)

### 2.1 Theory of Mind 벤치마크

| 데이터셋 | 규모 | 라이선스 | 획득 | 상업 이용 |
|---|---|---|---|---|
| ToMi (Meta) | ~6k 문항 (생성기) | CC BY-NC 4.0 | GitHub facebookresearch/ToMi | ❌ |
| FANToM (AI2) | 256 대화 / ~10k 문항 | MIT | GitHub skywalker023/fantom | ✅ |
| ToMBench | 2,860 샘플 (영/중) | MIT | GitHub zhchen18/ToMBench | ✅ (평가 전용 요청) |
| OpenToM | 696 내러티브 / 16k 문항 | CC BY-NC 4.0 | HF SeacowX/OpenToM | ❌ |
| Hi-ToM | ~1,200 QA (고차 ToM) | Apache-2.0 | GitHub ying-hui-he/Hi-ToM_dataset | ✅ |
| BigToM (Stanford) | 5,000 평가 (생성기) | MIT | GitHub cicl-stanford/procedural-evals-tom | ✅ |
| Social IQa (AI2) | ~38k QA | CC BY 4.0 | HF allenai/social_i_qa | ✅ |
| ToMATO (NTT) | 753 대화 / 5.4k 문항 | Llama 3 Community | GitHub nttmdlab-nlp/ToMATO | ⚠️ |
| MMToM-QA (멀티모달) | 600 문항 + 비디오 | Apache-2.0 | GitHub chuanyangjin/MMToM-QA | ✅ |
| ExploreToM (Meta) | 13k 샘플 (생성기) | CC BY-NC 4.0 | HF facebook/ExploreToM | ❌ |

### 2.2 사회적 상호작용 / 전략 게임

| 데이터셋 | 규모 | 라이선스 | 획득 | 상업 이용 |
|---|---|---|---|---|
| SOTOPIA 에피소드 | 1K-10K행, ~547MB | "cc" (변형 불명) | HF cmu-lti/sotopia | ⚠️ |
| **SOTOPIA-π** | 33,410행, 558MB | CC BY-SA 4.0 | HF cmu-lti/sotopia-pi | ✅ (SA 주의) |
| CaSiNo (협상) | 1,030 대화 + 전략 주석 | CC BY 4.0 | HF kchawla123/casino | ✅ |
| DealOrNoDeal | 5,808 대화 | CC BY-NC | GitHub facebookresearch/end-to-end-negotiator | ❌ |
| CICERO Diplomacy 코퍼스 | 4만 게임/1,290만 메시지 | 미공개 | **입수 불가** (RFP 2023 마감) | ❌ |
| It Takes Two to Lie (Diplomacy) | 17,289 메시지 (기만 주석) | CC BY 4.0 | GitHub DenisPeskoff/2020_acl_diplomacy, ConvoKit | ✅ |
| Werewolf Among Us | 199 게임, 설득전략 주석 26,647 | Apache-2.0 (주석) | HF bolinlai/Werewolf-Among-Us | ⚠️ 비디오는 별도 |
| Generative Agents | 시뮬 세이브 3종만 | Apache-2.0 | 직접 실행 필요 | ✅ |

### 2.3 사회·감정 대화

| 데이터셋 | 규모 | 라이선스 | 상업 이용 |
|---|---|---|---|
| DailyDialog | 13,118 대화 | CC BY-NC-SA 4.0 | ❌ |
| PersonaChat | ~11k 대화 | 명시 없음 | ⚠️ 연구용 취급 권장 |
| EmpatheticDialogues | 24,850 대화 | CC BY-NC 4.0 | ❌ |
| ESConv (감정지원) | 1,300 대화 + 전략 주석 | CC BY-NC 4.0 | ❌ |
| MultiWOZ 2.x | ~10,400 대화 | MIT | ✅ |
| Cornell Movie-Dialogs | 30만 발화 | 없음 (영화 대본) | ❌ |
| MELD (Friends) | 13,708 발화 | GPL 태그 무효 (WB 저작물) | ❌ |
| **SODA** (AI2, 합성) | **149만 대화** | CC BY 4.0 | ✅ |
| ProsocialDialog | 5.8만 대화 | CC BY 4.0 | ✅ |

### 2.4 사회 규범 / 도덕

| 데이터셋 | 규모 | 라이선스 | 상업 이용 |
|---|---|---|---|
| Social Chemistry 101 | 규범 29.2만 | CC BY-SA 4.0 | ✅ (Reddit 유래 주의) |
| Moral Stories | 12,000 내러티브 | MIT | ✅ |
| ETHICS | 134k 예제 | MIT | ✅ |
| NormBank | 155k 규범 | CC BY-SA 4.0 | ✅ |
| ATOMIC / ATOMIC-2020 | 877k / 1.33M 트리플 | CC BY 4.0 | ✅ |
| Scruples | 32k 일화 (AITA 원문) | "연구 전용" | ❌ 고위험 |
| Delphi Norm Bank | 170만 판단 | CC BY-NC-SA 4.0 | ❌ |

### 2.5 멀티모달

| 데이터셋 | 규모 | 조건 |
|---|---|---|
| **Ego4D** (Social 벤치마크) | 3,670+시간, ~7.1TB | 서명식 라이선스, 무료. **학습된 모델의 상업화 가능 / 원본 재배포 불가** — 실용적 |
| CANDOR | 1,656 화상통화, 850+시간 | 등록 심사제, 비상업 |
| MPIIGroupInteraction | 26시간 그룹토론 | EULA, 비상업 전용 |
| Social-IQ 1.0/2.0 | 1,250 비디오/7,500 문항 | 주석 MIT, 비디오는 YouTube 유실 진행 중 |

### 2.6 소셜미디어 (2026-07 현황)

- **Reddit**: Pushshift API는 2023-05부터 모더레이터 전용. 단 **역사 덤프는 Academic Torrents에서 계속 배포 중**(2005-06~2025-06 통합 3.46TB, 월별 갱신). Arctic Shift가 post-Pushshift 수집 지속. ⚠️ Reddit은 데이터를 유료 라이선싱(Google 연 $60M)하며 Anthropic(2025-06)·Perplexity(2025-10) 상대 소송 중 — **상업적 AI 학습은 실질적 소송 리스크**.
- **X(트위터)**: Academic API 2023년 폐지. 2026-02부터 신규는 종량제($0.005/읽기), Enterprise ~$42k/월. 연구 접근 사실상 소멸. 트윗 ID 기반 레거시 데이터셋은 하이드레이션 도구 사망으로 복원 불가능.
- **Bluesky**: Firehose 완전 개방·무인증. 수억 게시물 규모 수집 기술적으로 가능하나, HF '100만 포스트' 사건(2024-11)이 보여주듯 **기술적 접근 가능 ≠ 동의**. 개인정보법은 그대로 적용.
- **Mastodon**: 중앙 덤프 없음, GDPR로 대규모 배포 사례가 철회된 전례(ICWSM 2020 데이터셋 삭제·논문 철회).
- **ConvoKit** (Cornell): `pip install convokit`으로 31+ 코퍼스(대법원 구두변론, Wikipedia Talk, CMV, Persuasion For Good 등) 통일 포맷 접근 — 우회 경로로 유용.

---

## 3. 자체 데이터셋 구축 전략 (우선순위 순)

### 전략 1 (주력): 오픈웨이트 LLM 시뮬레이션 합성 데이터

**SOTOPIA-π 레시피** (검증된 실전 절차):
1. Social Chemistry/Social IQa/NormBank에서 영감받은 프롬프트로 사회 시나리오(목표·관계·페르소나) 자동 생성
2. **행동복제(BC)**: 강한 모델 에이전트 간 대화 수집 → SFT
3. **자기강화(SR)**: 학습 모델 자신의 상호작용 중 평가 점수 상위만 필터링해 재학습
4. 결과: 7B 모델이 GPT-4 수준 사회적 목표달성 도달 (단, LLM 평가자의 과대평가 문제 자체 보고)

**⚠️ 모델 선택이 법적으로 결정적**:

| 생성 모델 | 경쟁모델 학습용 합성 데이터 |
|---|---|
| GPT/Claude/Gemini API | **금지** (약관상 경쟁모델 학습 금지) |
| Llama 3/4 | 조건부 ("Built with Llama" 표기 등) |
| **Qwen (Apache-2.0), DeepSeek (MIT)** | **자유** ← 권장 |

다자·집단 역학은 OASIS(SNS형)·AgentSociety(도시·사회형)·Concordia(GM 패턴)로 확장. 아첨·저분산·군집과민 편향이 있으므로 인간 데이터 캘리브레이션 필수(전략 2).

### 전략 2 (보정·검증): Prolific 크라우드소싱

- **MTurk는 2026-07-30부로 신규 고객 중단** (워커 33-46%가 LLM 사용 문제) → Prolific이 표준.
- Prolific: 최저 $8/시간(권장 $12) + 수수료(기업 42.8%) → **2인 20분 대화 1건 ≈ $11-12**. 수천 건 규모로 합성 데이터 편향 측정·교정용 골드 세트 구축.
- 설계 모범: EmpatheticDialogues(감정 라벨 기반 상황 → 2인 대화 24,850건), CaSiNo(자원 협상 게임화 + 전략 주석 1,030건). 구조화 시나리오·역할·인센티브가 품질을 좌우. 국내 대안: 크라우드웍스·셀렉트스타 + 데이터바우처.
- 학회 발표 계획이 있으면 **공용 IRB(irb.or.kr) 심의** 확보 권장.

### 전략 3 (중기 자산): 자체 게임/앱 환경 로그

- 선례: Meta CICERO는 webDiplomacy와 **데이터 제공 계약**(스크레이핑 아님, 익명화 조건)으로 4만 게임 확보.
- 가장 깨끗한 경로: **자체 소셜 디덕션 게임/디스코드 봇 환경 구축** + 약관에 "AI 학습 목적 로그 수집" 동의 명시. 기만·설득·협상 신호가 풍부. 대안으로 기존 플랫폼 운영자와 계약.
- 타사 게임 로그 무단 스크레이핑은 금물 (로그인 상태 스크레이핑 = 계약위반 판례 추세).

### 전략 4 (최후순위): SNS 스크레이핑

한다면 반드시:
- **비로그인 + 공개 페이지만** (Meta v. Bright Data 2024: 로그아웃 스크레이핑은 약관 위반 아님 / hiQ v. LinkedIn: 로그인 스크레이핑으로 $500k 합의 + 데이터 전량 파기)
- **PIPC 「AI 개발용 공개 개인정보 처리 안내서」(2024-07)의 정당한 이익 3요건 문서화**: 목적 정당성 + 필요성·상당성 + 이익형량, 그리고 안전조치(민감정보 필터링, 옵트아웃 창구)
- EU 데이터 혼입 시 EDPB Opinion 28/2024 + Guidelines 03/2026 (웹스크레이핑) 준수
- **한국은 TDM 면책 미입법** — 저작권법 개정안(2021 발의) 미통과 상태라 공정이용(§35조의5)에 기대야 하며 판례 미확립. 저작권 리스크가 별도로 남음.

### 한국 법률 체크리스트

- **생명윤리법 IRB**: 대화 수집은 인간대상연구. 면제 요건(식별정보 비수집 + 대상자 불특정 + 민감정보 비수집 + 비취약계층) 충족이 어려우면 공용 IRB 신속심의.
- **가명정보**: 법 제28조의2 — '과학적 연구'(산업적 연구 포함) 목적은 동의 없이 가명정보 처리 가능. 「가명정보 처리 가이드라인」 2024-02 개정판이 텍스트 등 비정형데이터 기준 신설.
- **PIPC 안내서 3종**: 공개 개인정보 처리(2024-07), 생성형 AI 개인정보 처리(2025-08), 합성데이터 생성·활용(2024-12).
- **AI 기본법** (2026-01-22 시행): 생성형 AI 투명성 의무 (AI 생성물 표시, 위반 시 과태료 최대 3천만 원).

---

## 4. 미해결 질문 (추가 검증 필요)

1. S3AP +51%/+18%, ToMA의 Sotopia 우위 — 독립 재현 여부 미확인 (전부 저자 자기보고)
2. LLM 시뮬레이션 합성 데이터의 인간 행동 분포 대표성을 정량 검증하는 표준 방법론 부재 (군집효과 과대 편향 보정 등)
3. SWM 용어 정의가 아직 유동적 — Zhou et al.의 표현 중심 정의 vs Dec-POMDP 형식 정의 병존
4. SOTOPIA 에피소드 데이터셋의 정확한 CC 변형 — 상업 이용 전 CMU에 확인 필요

## 주요 출처

- Social World Models: arxiv.org/abs/2509.00559 (NeurIPS 2025)
- World Models: arxiv.org/abs/1803.10122, worldmodels.github.io
- Agentic World Modeling 서베이: arxiv.org/abs/2604.22748
- Mental World Model 리뷰: arxiv.org/abs/2601.02378
- 창발적 SWM 증거: arxiv.org/abs/2602.10298 (ACL 2026)
- ToMAgent: arxiv.org/abs/2509.22887 · Sotopia: aclanthology.org/2024.acl-long.698
- SOTOPIA-π: arxiv.org/abs/2403.08715 · AgentSociety: arxiv.org/abs/2502.08691 · OASIS: arxiv.org/abs/2411.11581
- SOTOPIA-S4: arxiv.org/abs/2504.16122 (NAACL 2025)
- 큐레이션 목록: github.com/sotopia-lab/awesome-social-agents
- PIPC 안내서: privacy.go.kr, pipc.go.kr · EDPB: edpb.europa.eu
