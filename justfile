help:
    @just --list

dev:
    #!/usr/bin/env bash
    set -euo pipefail

    root={{ quote(justfile_directory()) }}
    pids=()
    cleanup() {
        trap - INT TERM EXIT
        if ((${#pids[@]})); then
            for pid in "${pids[@]}"; do
                kill -- -"$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
            done
            wait "${pids[@]}" 2>/dev/null || true
        fi
    }
    wait_for() {
        local url="$1"
        for _ in {1..80}; do
            if curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
                return 0
            fi
            sleep 0.25
        done
        echo "Timed out waiting for $url" >&2
        return 1
    }
    trap cleanup INT TERM EXIT

    setsid bash -c 'cd "$1" && exec uv run fastapi dev src/core/app.py --port 9101' _ "$root/extensions/core" &
    pids+=("$!")
    wait_for http://127.0.0.1:9101/health

    setsid bash -c 'cd "$1" && exec env EXTENSIONS_REGISTRY_PATH="$2" PYTHONPATH=. uv run --project . fastapi dev main.py --port 8000' _ "$root/processor" "$root/extensions.yaml" &
    pids+=("$!")
    wait_for http://127.0.0.1:8000/api/operations

    setsid bash -c 'cd "$1" && exec bun run dev' _ "$root/frontend" &
    pids+=("$!")
    wait -n "${pids[@]}"
