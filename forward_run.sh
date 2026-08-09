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
export PATH="$HOME/google-cloud-sdk/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
cd /Users/ax/world_model || exit 1
set -a
source /Users/ax/world_model/.env
set +a
echo "\n===== $(date '+%Y-%m-%d %H:%M') 전향 패스 시작 ====="
command -v bq >/dev/null || echo "🔴 bq 없음 — step1 이 죽는다"
/usr/bin/python3 -m harness.forward
echo "===== 종료 코드 $? ====="
