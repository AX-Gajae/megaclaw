#!/bin/zsh
# 전향 사이클 정례 실행 래퍼 (crontab용).
# 로그: cycle_log/forward/cron.log — 실패해도 다음 주기에 재시도됨(모든 단계 멱등).
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
cd /Users/ax/world_model || exit 1
export $(cat .env)
echo "\n===== $(date '+%Y-%m-%d %H:%M') 전향 패스 시작 ====="
/usr/bin/python3 -m harness.forward
echo "===== 종료 코드 $? ====="
