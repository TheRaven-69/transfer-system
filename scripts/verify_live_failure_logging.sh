#!/usr/bin/env bash

set -Eeuo pipefail

base_url="http://localhost:8081"
confirmed=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --confirm-chaos)
            confirmed=true
            shift
            ;;
        --base-url)
            base_url="${2:?--base-url requires a value}"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [[ "$confirmed" != true ]]; then
    echo "This script temporarily stops local Redis and PostgreSQL." >&2
    echo "Re-run with --confirm-chaos." >&2
    exit 2
fi

wait_healthy_container() {
    local container_name="$1"
    local timeout_seconds="${2:-60}"
    local deadline=$((SECONDS + timeout_seconds))
    local status

    while ((SECONDS < deadline)); do
        status="$(
            docker inspect \
                --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
                "$container_name" 2>/dev/null || true
        )"
        if [[ "$status" == "healthy" || "$status" == "running" ]]; then
            return 0
        fi
        sleep 1
    done

    echo "Container '$container_name' did not become healthy within ${timeout_seconds}s." >&2
    return 1
}

restore_dependencies() {
    echo "Restoring PostgreSQL and Redis..."
    docker compose start db redis >/dev/null
    wait_healthy_container transfer_db
    wait_healthy_container transfer_redis
}

trap restore_dependencies EXIT

started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

docker compose up -d --build db redis app
wait_healthy_container transfer_db
wait_healthy_container transfer_redis
wait_healthy_container transfer_app

echo "Stopping Redis and triggering real post-commit/cache failures..."
docker compose stop redis
docker compose exec -T app sh -c \
    'python scripts/verify_json_logging.py --real-redis > /proc/1/fd/1 2> /proc/1/fd/2'

docker compose start redis
wait_healthy_container transfer_redis

echo "Stopping PostgreSQL and triggering a real metrics collection failure..."
docker compose stop db
if curl --fail --max-time 15 --silent --show-error "$base_url/metrics" >/dev/null; then
    echo "Metrics endpoint responded; inspect the application log for the DB failure."
else
    echo "The HTTP request failed as expected."
fi

echo "Relevant application logs:"
docker logs transfer_app --since "$started_at" 2>&1 \
    | grep -E \
        'post_commit_hook_failed|redis_delete_failed|system_metrics_collection_failed' \
    || true
