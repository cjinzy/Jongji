#!/usr/bin/env bash
set -euo pipefail

export COMPOSE_PROJECT_NAME=jongji-e2e

COMPOSE_FILE="$(cd "$(dirname "$0")/.." && pwd)/docker-compose.e2e.yml"
E2E_DIR="$(cd "$(dirname "$0")/.." && pwd)/e2e"

cleanup() {
  echo "[e2e] Tearing down containers..."
  docker compose -f "$COMPOSE_FILE" down -v
}
trap cleanup EXIT

echo "[e2e] Building and starting services..."
docker compose -f "$COMPOSE_FILE" up --build -d

echo "[e2e] Waiting for backend health (http://localhost:3100/api/v1/health)..."
elapsed=0
until curl -sf http://localhost:3100/api/v1/health > /dev/null 2>&1; do
  if [ "$elapsed" -ge 60 ]; then
    echo "[e2e] ERROR: backend did not become healthy within 60 seconds"
    exit 1
  fi
  sleep 2
  elapsed=$((elapsed + 2))
done
echo "[e2e] Backend is healthy."

echo "[e2e] Waiting for backend readiness (http://localhost:3100/api/v1/ready)..."
elapsed=0
until curl -sf http://localhost:3100/api/v1/ready > /dev/null 2>&1; do
  if [ "$elapsed" -ge 30 ]; then
    echo "[e2e] ERROR: backend did not become ready within 30 seconds"
    exit 1
  fi
  sleep 2
  elapsed=$((elapsed + 2))
done
echo "[e2e] Backend is ready."

echo "[e2e] Installing e2e dependencies..."
cd "$E2E_DIR"
npm ci
npx playwright install chromium --with-deps

echo "[e2e] Running Playwright tests..."
set +e
npx playwright test "$@"
TEST_EXIT_CODE=$?
set -e

echo "[e2e] Tests finished with exit code $TEST_EXIT_CODE."
exit $TEST_EXIT_CODE
