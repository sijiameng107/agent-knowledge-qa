#!/bin/zsh
set -eu
cd "${0:A:h:h}"
if [[ -z "${ZHIPU_API_KEY:-}" ]]; then
  read -r -s 'ZHIPU_API_KEY?粘贴智谱普通 API Key 后回车（不显示）：'
  print
  export ZHIPU_API_KEY
fi
export ZHIPU_MODEL="${ZHIPU_MODEL:-glm-4-flash-250414}"
python3 scripts/evaluate.py --mode live --output "examples/live-$(date +%Y%m%d-%H%M%S)"
