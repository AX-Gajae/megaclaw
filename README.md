<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.svg">
  <img src="docs/assets/logo.svg" width="84" alt="MEGACLAW mark">
</picture>

# MEGACLAW

**IP 파운데이션 월드모델 — 순위와 확률만 말한다.**

문화 IP 11개 도메인(게임 · 웹툰 · 애니 · 만화 · 도서 · 펀딩 · 아이돌 · 모바일 · 팝업 …)의
흥행을 하나의 판 위에서 재고, 예측을 **측정 전에 봉인**하고, 틀리면 틀렸다고 적는 실험실.

![판 ρ](https://img.shields.io/badge/판_ρ-0.4689-1f6feb?style=flat-square)
![도메인](https://img.shields.io/badge/도메인-11-30363d?style=flat-square)
![노트](https://img.shields.io/badge/연구_노트-823-30363d?style=flat-square)
![논문](https://img.shields.io/badge/사내_논문-182편-30363d?style=flat-square)
![규약](https://img.shields.io/badge/실험_규약-46개-8957e5?style=flat-square)

<img src="docs/assets/megaclaw-hero.png" width="88%" alt="MEGACLAW — 홀로그램 지구본 앞의 랍스터 연구원">

</div>

---

## 이 실험실이 하는 일

작품 하나가 세상에 나왔을 때 **어디까지 갈지의 순위**를 예측한다. 절대값("관객 몇 명")은
팔지 않는다 — 자릿수를 유의미한 확률로 틀린다는 것을 스스로 측정했기 때문이다.
파는 것은 세 가지다:

1. **순위와 구간** — 도메인 안에서의 상대 위치 (챔피언 합동 모형, 판 ρ 0.4689)
2. **드리프트 보정 절대값** — 자(불확실성 눈금)와 함께만 (노트 791~809 사슬)
3. **정직한 능력 카드** — 무엇을 못 보는지의 목록까지 포함

## 지금까지 실측으로 확정된 것

> 이 판의 가장 값진 산출물은 예측력 자체가 아니라 **어디서 무엇이 통하는지의 지도**다.

| 발견 | 근거 |
|---|---|
| 도메인 간 "공유 장(場)"은 얇다 — 진폭·시간을 다 빼야 곡선이 겹친다 | 노트 813~818 |
| 합동 모형은 공유 기저를 안 쓴다 — 정렬은 사실상 한 축(target_breadth) | 노트 819 |
| 시간 갈림에서 **단순 릿지가 전이를 이긴다** (두 짝 모두) — 전이의 가치는 cold-start 전용 | 노트 821~822 |
| 판 안에서 합동의 이득은 10개 중 5개 도메인에만 실재 — 아이돌은 오히려 손해 | 노트 822 |
| 도메인 범주가 겹쳐 있었다 (게임-모바일 38 · 만화-세계애니 838 제목) | 노트 820 |
| 예보 드리프트는 예측 가능하고(r 0.762) 보정하면 98% 닫힌다 | 노트 800~802 |

## 아키텍처 — 4층 스택

```mermaid
flowchart LR
    A["① 자료·축 층<br/>ingest → data/state/*_axes.json<br/>11 도메인 · 공유 축 36 (값+표시자)"]
    B["② 예측 층 (챔피언)<br/>F18_bagboost 합동 적합<br/>HistGBR 32자루 × 220트리 × 깊이12"]
    C["③ 레짐 보조 헤드<br/>TabPFN — 소외 도메인 전담<br/>(아이돌 · 시장팝업)"]
    D["④ 보정·서빙 층<br/>lab/calib 드리프트 보정<br/>serve/boardsvc · 능력 카드 · 오토리서치"]
    A --> B --> D
    A --> C --> D
```

## 연구 루프 — 한 사이클의 규율

```
① 트랙 선택(paper.program next)   ② 사전등록(갈래에 번호 우선순위 — 규약 46)
③ 측정(배선 검사 → 위약 → 표본 2σ 문턱)   ④ 트랙 갱신 + check
⑤ 대장 기록(data/lab/denominator.json — 못 넘었으면 못 넘었다고)
⑥ report + ingest.audit   ⑦ 논문(figure + 창의적 제목) + DM
⑧ 커밋   ⑨ GitHub push   ⑩ 프레시 티처 세션 비평 → 다음 사이클 입력
```

- **첫 양성은 채택하지 않는다** (노트 133) — 확인 사이클이 따른다.
- **씨앗 SE 는 재현성이지 일반화가 아니다** (노트 613) — 채택 문턱은 표본 2σ.
- **바닥(잡음 추정)도 뽑기 6회 이상** (규약 20 확장) — 잡음의 잡음을 재지 않으면 비율을 두세 배 틀린다.
- **BQ/GCP 는 읽기 전용** — SELECT 와 메타 조회만. 변경물은 로컬로 준비해 담당자에게 전달.

## 저장소 지도

```
lab/          측정 기계 — forms(정식화) · guards · calib(보정) · challenger(TabPFN)
              decay/curveshape(곡선 층) · pairs(집 밖 짝) · sideaudit
state/        도메인 정본 — tri_domain(11 도메인 적재) · slots · procrustes
ingest/       수집 — 위키 · 트렌드 · 뉴스 · 문서 채굴 · audit(사람 게이트 대기열)
serve/        서빙 — boardsvc(웜 캐시) · capability(능력 카드) · research(오토리서치) · web
paper/        사내 논문 하네스 — steps/NNN_slug/(main.tex·meta.json·figs) · build · send
harness/      백테스트/전향 사이클 — 예측 봉인(커밋 해시) · rolling-origin · 채점
data/lab/     대장 — denominator.json(노트 원장) · program.json(트랙)
```

## GitHub 운영 흐름

- **가설 = 이슈** — 사전등록 본문으로 연다.
- **측정 = 브랜치** `note/NNN-slug` — 커밋에 노트 번호를 단다.
- **판정 = PR** — 결과·갈래 판정을 본문에, 예측 채점을 셀프 코멘트로, merge 로 확정.
- 판정이 "못 넘음"이어도 기록은 남긴다 — 이 저장소의 절반은 부정 결과다. 그게 자산이다.

## 정직 조항 (능력 카드 발췌)

- 맨 절대값 예측은 **팔지 않는다** — 보정 후에도 자릿수(10배)를 14% 확률로 틀린다.
- "50건이면 전이와 동급" 온보딩 서사는 **폐기됐다** (노트 821~822) — 과거 자료를 가진
  고객은 자기 릿지가 우리 전이보다 낫다. 전이의 가치는 자료 0건 구간과
  단독 모형이 성립 불가한 도메인이다.
- 감쇠-이중피크 곡선 구분은 현재 자(RMSE)로 **못 본다** — 형태 특징 자로 수리 중(노트 823).
- 예측은 오픈 전 봉인 — 커밋 해시 없는 예측은 존재하지 않는 예측이다.
- 생존 편향(실행된 것만 관측된다)은 모든 리포트에 명시하고 안고 간다.

---

<div align="center">
<sub>MEGACLAW · 비공개 연구 저장소 · 예측은 봉인되고, 실측이 채점하고, 대장은 거짓말하지 않는다</sub>
</div>
