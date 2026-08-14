dev:
    #!/usr/bin/env bash
    set -euo pipefail

    root={{ quote(justfile_directory()) }}
    pids=()
    cleanup() {
        trap - INT TERM EXIT
        if ((${#pids[@]})); then
            kill "${pids[@]}" 2>/dev/null || true
            wait "${pids[@]}" 2>/dev/null || true
        fi
    }
    trap cleanup INT TERM EXIT

    (cd "$root/processor" && exec uv run fastapi dev --port 8000) &
    pids+=("$!")
    (cd "$root/frontend" && exec bun run dev) &
    pids+=("$!")
    wait -n "${pids[@]}"
