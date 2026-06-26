#!/usr/bin/env sh
set -e

# Start the application in background. Replace with your real start command if different.
# Example: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1
# If you use gunicorn, start the same command you use in production here.
APP_CMD="gunicorn -k uvicorn.workers.UvicornWorker backend.app.main:app --bind 0.0.0.0:8000 --workers 1"

log_file="/tmp/app_start.log"

echo "Starting app with: $APP_CMD"
# Start server in background and redirect logs so we can show them on failure
sh -c "$APP_CMD" > "$log_file" 2>&1 &

pid=$!
echo "Server PID: $pid"

# Wait for health endpoint
HEALTH_URL="http://127.0.0.1:8000/health"
TIMEOUT=120
SLEEP=1

i=0
while [ $i -lt $TIMEOUT ]; do
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    echo "App healthy"
    wait $pid
    exit 0
  fi
  i=$((i + SLEEP))
  sleep $SLEEP
done

echo "App failed to become healthy within ${TIMEOUT}s. Dumping log:"
cat "$log_file"
kill $pid || true
exit 1