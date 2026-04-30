#!/usr/bin/env bash
# ──────────────────────────────────────────────────────
# Run tests using docker compose (PostgreSQL + pytest).
# Usage:  ./scripts/run_tests.sh
# ──────────────────────────────────────────────────────
set -euo pipefail

if docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE=(docker-compose)
else
  echo "Docker Compose is not available. Install docker compose or docker-compose."
  exit 1
fi

echo "🚀 Building and starting test environment..."
set +e
"${DOCKER_COMPOSE[@]}" -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner
EXIT_CODE=$?
set -e

echo "🧹 Cleaning up containers..."
"${DOCKER_COMPOSE[@]}" -f docker-compose.test.yml down -v

exit $EXIT_CODE
