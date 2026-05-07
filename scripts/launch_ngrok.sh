#!/usr/bin/env zsh
# One-command launcher: starts the multi-user Streamlit app and exposes
# it via ngrok so a friend can hit it from any browser.
#
# Prereqs:
#   - ngrok installed (`brew install ngrok` on macOS) AND `ngrok authtoken
#     <your-token>` run once. Free signup at https://ngrok.com.
#   - This repo installed: `pip install -e .[ui]`
#   - DEEPSEEK_API_KEY (or other provider key) optional at the server
#     level; users can also paste their own key in the Setup tab.
#
# Usage:
#   ./scripts/launch_ngrok.sh              # default: port 8501
#   PORT=8888 ./scripts/launch_ngrok.sh    # override port
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-8501}"

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok not found. Install it (https://ngrok.com/download) and run \`ngrok config add-authtoken <token>\` once." >&2
  exit 1
fi
if ! command -v streamlit >/dev/null 2>&1; then
  echo "streamlit not found. Run \`pip install -e .[ui]\` first." >&2
  exit 1
fi

mkdir -p users
echo "Starting Streamlit on http://localhost:${PORT}"
streamlit run src/job_apply/ui/streamlit_app.py \
  --server.port="${PORT}" \
  --server.headless=true \
  --browser.gatherUsageStats=false \
  > /tmp/streamlit-${PORT}.log 2>&1 &
ST_PID=$!

cleanup() {
  echo ""
  echo "Stopping Streamlit (pid ${ST_PID})..."
  kill ${ST_PID} 2>/dev/null || true
  pkill -P $$ 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Wait for Streamlit health
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/_stcore/health" 2>/dev/null | grep -q 200; then
    break
  fi
  sleep 1
done

echo "Starting ngrok tunnel -> port ${PORT}"
ngrok http "${PORT}" --log stdout
