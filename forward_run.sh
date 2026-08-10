#!/bin/zsh
# 전향 사이클 정례 실행 래퍼 (crontab용).
# 로그: cycle_log/forward/cron.log — 실패해도 다음 주기에 재시도됨(모든 단계 멱등).
#
# 🔴 2026-08-09 — 이 래퍼는 **두 번 돌아 두 번 다 죽었다**(7/27·8/03, 종료코드 1).
# 두 가지가 함께 틀렸고 둘 다 크론 안에서만 드러난다(대화형 셸에서는 안 난다):
#
#   ① `bq` 가 PATH 에 없다. gcloud SDK 는 `~/google-cloud-sdk/bin` 에 있는데
#      옛 PATH 는 `/usr/local/bin:/opt/homebrew/bin` 뿐이라 step1 이 첫 줄에서
#      `FileNotFoundError: 'bq'` 로 죽었다 → 2~4 단계는 **한 번도 실행된 적이 없다**.
#
#   ② `export $(cat .env)` 가 주석 줄에서 **에러로 중단**된다.
#      `.env:4` 의 `# 검색 API 전용 앱 — ...` 이 단어분해되어
#      `zsh:export:1: not valid in this context: —` 을 내고 export 가 끊긴다.
#      그래서 그 아래의 `NAVER_SEARCH_ID`·`NAVER_SEARCH_SECRET`·`DATA_GO_KR_KEY`
#      는 이 크론 안에서 **존재한 적이 없다**. `bq` 를 고쳐도 이건 안 고쳐진다.
#      `set -a; source` 는 주석과 따옴표를 셸 문법대로 처리한다.
#
# 이 두 결함은 "돌고 있다고 믿었는데 안 돌고 있었다" 부류다 — 산출물이 안 생기는
# 것으로만 드러나고 로그를 열기 전에는 조용하다. 크론 로그를 사이클마다 본다.
# 🔴 **티처 #53 C4** — 이 스크립트는 crontab 에 살아 있는 **유일한** 작업인데,
# 노트 889 가 진단하고 `cycle_run.sh` 에서만 고친 결함을 그대로 이고 있었다:
#   ⓐ PATH 에 `~/.local/bin` 이 없어 gcloud 가 **python3.9** 를 잡고 `bq` 가
#      `TypeError: unsupported operand type(s) for |` 로 죽는다(티처 실측 · 종료 1).
#      그런데 `command -v bq` 는 **종료 0** 을 낸다 --- 존재 확인은 작동 확인이 아니다.
#   ⓑ `source .env` 로 `ANTHROPIC_API_KEY` 를 세우고 **unset 하지 않는다**.
#      `cycle_run.sh` 가 명시한 두 겹(코드 가드 + 키 제거) 중 한 겹이 없었다.
export PATH="$HOME/google-cloud-sdk/bin:$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
export CLOUDSDK_PYTHON="$HOME/.local/bin/python3.12"
cd /Users/ax/world_model || exit 1
set -a
source /Users/ax/world_model/.env
set +a

# 🔴 유료 API 를 크론에서 열지 않는다(사용자 상시 지시 · `cycle_run.sh` 와 같은 두 겹).
unset ANTHROPIC_API_KEY
unset WM_ALLOW_PAID_API
echo "\n===== $(date '+%Y-%m-%d %H:%M') 전향 패스 시작 ====="
# **있는지가 아니라 도는지** 본다(889 의 교훈을 여기에도 적용).
if ! bq query --project_id=sweetspot-ax --use_legacy_sql=false --format=json \
     --max_rows=1 'SELECT 1' >/dev/null 2>&1; then
  echo "🔴 프리플라이트 실패: bq 가 안 돈다(CLOUDSDK_PYTHON=$CLOUDSDK_PYTHON) — step1 이 죽는다"
fi
/usr/bin/python3 -m harness.forward
echo "===== 종료 코드 $? ====="
