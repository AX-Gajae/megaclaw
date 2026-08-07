#!/bin/zsh
# API 키 로테이션 헬퍼: ./rotate_key.sh sk-ant-새키
# 콘솔(console.anthropic.com → API Keys)에서 새 키 발급 + 구 키 폐기 후 실행.
[ -z "$1" ] && echo "사용법: ./rotate_key.sh <새 키>" && exit 1
cd /Users/ax/world_model
printf 'ANTHROPIC_API_KEY=%s\n' "$1" > .env
sed -i '' "s|^export ANTHROPIC_API_KEY=.*|export ANTHROPIC_API_KEY=\"$1\"|" ~/.zshrc
export ANTHROPIC_API_KEY="$1"
python3 -c "import anthropic; anthropic.Anthropic().messages.create(model='claude-haiku-4-5', max_tokens=8, messages=[{'role':'user','content':'ping'}]); print('새 키 검증 OK — .env와 ~/.zshrc 갱신 완료')"
