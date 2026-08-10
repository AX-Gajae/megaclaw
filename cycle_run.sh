#!/bin/zsh
# 월드모델 사이클 정례 실행 래퍼 (crontab용) — 노트 889.
# 로그: cycle_log/cycle_cron.log · 보고: 슬랙 DM
#
# **크론이 하는 일은 기계적인 것뿐이다.** 판단이 필요한 자리(문서 추출·예측)는
# 에이전트 2패스라 요청 파일로 쌓이고, 그 목록이 슬랙으로 온다. 세션에서
# `python3 -m ingest.cycle_open` 으로 이어받는다.
#
# 2026-08-09 에 이 저장소의 다른 크론(`forward_run.sh`)이 **두 번 돌아 두 번 다
# 죽어 있었고 2주 동안 아무도 몰랐다**. 그때 원인이 셋이었고 여기서 셋 다 막는다:
#   ① PATH 에 gcloud SDK 가 없어 `bq` 가 안 잡혔다 → 아래에서 명시한다
#   ② `export $(cat .env)` 가 주석 줄에서 죽었다 → `set -a; source` 로 바꿨다
#   ③ 실패해도 아무 데도 안 알렸다 → `--slack` 으로 매번 보고한다
# 🔴 `$HOME/.local/bin` 이 **PATH 에 있어야 한다**(2026-08-10 · 첫 launchd 실행에서 잡음).
# gcloud SDK 는 PATH 에서 python 을 고르는데, 최소 환경에서는 `/usr/bin/python3`(**3.9**)
# 가 잡히고 `bq` 가 `TypeError: unsupported operand type(s) for |` 로 죽는다 ---
# SDK 내부 `urllib3` 이 `bytes | str`(3.10+ 문법)을 쓴다. 인터랙티브 셸에서는
# `~/.local/bin/python3.12` 가 먼저라 안 났고, 그래서 **크론에서만 나는 고장**이었다.
# PATH 순서에 기대지 않고 `CLOUDSDK_PYTHON` 으로 못박는다.
export PATH="$HOME/google-cloud-sdk/bin:$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
export CLOUDSDK_PYTHON="$HOME/.local/bin/python3.12"
cd /Users/ax/world_model || exit 1
set -a
source /Users/ax/world_model/.env
set +a

# 🔴 **유료 API 를 크론에서 절대 안 연다**(사용자 지시 2026-08-10:
# *"무조건 api 키로 클로드 돌리지 말고"*). 두 겹으로 막는다:
#   ⒜ `core/noapi.py` 가 코드에서 기본 차단(WM_ALLOW_PAID_API 없으면 SystemExit)
#   ⒝ 키 자체를 환경에서 지운다 --- 가드를 우회하는 새 코드가 생겨도 못 쓴다
# 한 겹은 잊히고, 두 겹은 덜 잊힌다.
unset ANTHROPIC_API_KEY
unset WM_ALLOW_PAID_API

echo "\n===== $(date '+%Y-%m-%d %H:%M') 사이클 시작 ====="
# **프리플라이트 — 있는지가 아니라 도는지를 본다**(2026-08-10). 옛 검사는
# `command -v bq` 뿐이었는데 첫 launchd 실행에서 bq 는 **있었고 죽었다**(파이썬
# 3.9 를 잡아서). 존재 확인은 작동 확인이 아니다 --- 한 번 실제로 쏴 본다.
if ! bq query --project_id=sweetspot-ax --use_legacy_sql=false --format=json \
     --max_rows=1 'SELECT 1' >/dev/null 2>&1; then
  echo "🔴 프리플라이트 실패: bq 가 안 돈다(CLOUDSDK_PYTHON=$CLOUDSDK_PYTHON) — 전향 패스가 죽는다"
fi
/usr/bin/python3 -m ingest.cycle_open --slack
echo "===== 종료 코드 $? ====="
