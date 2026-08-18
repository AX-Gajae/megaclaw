# pretrain — 한국어 웹 몸통 사전학습 (라벨 0 비트)

**목표**: `docs/목표.md` 의 파운데이션 물음을 «몸통 층»에서 세운다.
판 ρ 도 도메인 라벨도 안 본다 — **라벨 = 다음 토큰 하나**다.

## 재료 (전부 이 기계에 이미 있다)

| | |
|---|---|
| 몸통 | FineWeb2-ko `/Users/ax/wm_harvest/fineweb2_ko/` — **60,874,355 문서 · 98.5 GiB · 2013-05 ~ 2024-04** |
| 시대 축 | `dump` 열의 크롤 체크포인트 **96 개** → 챔피언 시간 절단으로 블록 0·1·2 (블록 3·4 는 몸통이 안 덮는다) |
| 장치 | M4 Pro · GPU 20 코어 · `torch 2.8.0` MPS — **폭 512 부터 3.3~3.7×** (`bench_device.py` 로 재현) |
| 산출물 | 전부 `/Users/ax/wm_harvest/foundation/` — **git 에는 코드만** |

## 한 번만 하는 것

```bash
cd /Users/ax/world_model
# ① 토크나이저 — 한국어 32k ByteLevel-BPE (5~20 분)
RAYON_NUM_THREADS=10 nohup python3 pretrain/tok_train.py > /Users/ax/wm_harvest/foundation/tok_train.log 2>&1 & disown
# ② 말뭉치 토큰화 — dump 당 14k 문서 균형 표집 ≈ 1.2B 토큰 (10~60 분)
RAYON_NUM_THREADS=10 nohup python3 pretrain/tokenize_corpus.py --docs-per-dump 14000 > /Users/ax/wm_harvest/foundation/tokenize.log 2>&1 & disown
#    전량(≈53.6G 토큰 · ≈100 GiB)이 필요해지면: --docs-per-dump 999999999 --force
```

## 학습

```bash
# 본 학습 (tiny 42M · MPS 자동 · ⚠ 하네스가 긴 전경 작업을 죽인다 — nohup 필수)
nohup python3 pretrain/train.py --preset tiny --steps 20000 --name tiny-v1 \
  > /Users/ax/wm_harvest/foundation/ckpt/tiny-v1.log 2>&1 & disown
# 진행:  cat /Users/ax/wm_harvest/foundation/ckpt/tiny-v1/progress.txt
# 재개:  같은 명령에 --resume auto   (배치 열이 (seed,step) 유도라 같은 자료 열을 밟는다)
# 중단:  kill -TERM <pid>            (체크포인트 저장 후 종료)
```

**시간 방향 사전학습** (월드모델의 원점 실험을 몸통 층에서):

```bash
python3 pretrain/train.py --preset tiny --steps 20000 --name tiny-b01 --max-block 1   # 2019.27 이전 웹으로만
python3 pretrain/evalbpb.py --ckpt /Users/ax/wm_harvest/foundation/ckpt/tiny-b01/latest.pt
#  → 블록별 bpb 표: 「과거로 학습한 몸통이 미래 텍스트를 얼마나 놓치는가」
```

## 크기와 장치 (실측)

| preset | 파라미터 | 장치(자동) |
|---|---:|---|
| nano | 11,536,640 | cpu — 단위시험용 |
| **tiny** | **41,951,744** | **mps** — 기본 |
| small | 110,119,680 | mps |
| base | 234,914,816 | mps |

`nano` 조차 `micro_batch 4` 실측에서 MPS 3.45× 가 나왔다(32k 어휘 CE 가 지배).
문턱은 `config.MPS_MIN_WIDTH = 512` — 근거·재측정은 `python3 pretrain/bench_device.py`.

## 설계 결정과 근거

- **32k BPE 를 새로 훈련** (XLM-R 250k · Qwen3 151k 를 안 쓰고): d=512 에서 250k 어휘면
  임베딩만 128M — 몸통(25M)의 5 배. 32k 면 16.8M 이고 **uint16 저장**이 서서 디스크 절반.
- **dump 당 문서 «상한»(균형 표집)**: dump 두께 차 실측 98.9 배 — 비례로 뽑으면 2023 이
  판을 먹고 시간 방향 실험의 검정력이 죽는다.
- **(seed, step) 유도 배치**: RNG 상태 저장 없이 재개가 같은 자료 열을 밟는다.
- **bpb 평가**: 토크나이저가 달라도 비교가 서는 «라벨 0 비트» 자.
  `bpb = nll/ln2 × (tokens/bytes)` — 블록별 tokens/bytes 는 index.json 에서.

## 흔한 함정 (이 저장소에서 실제로 난 것들)

- 🔴 **하네스가 ~2 분 넘는 전경 작업을 죽인다** — 긴 것은 전부 `nohup … & disown`.
- 🔴 **`| head` 파이프는 SIGPIPE 로 죽는데 종료코드 0** — 로그는 파일로.
- 🔴 산출물을 저장소 안에 만들지 마라 — GitHub 100MB · 60 초 데몬이 `data/` 를 커밋한다.
- `git checkout` 금지 — 가지가 필요하면 `git branch` + 배관.
