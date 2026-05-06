#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_ROOT/.venv/bin/python}"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
if [[ "${RELOAD:-1}" == "0" || "${RELOAD:-}" == "false" ]]; then
    RELOAD_FLAG=""
else
    RELOAD_FLAG="${RELOAD_FLAG:---reload}"
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "VCBench Python environment not found at: $PYTHON_BIN" >&2
    echo "Create it from the repository root with:" >&2
    echo "  conda create -p ./.venv python=3.11 pip -y" >&2
    echo "  ./.venv/bin/python -m pip install -r requirements.txt" >&2
    exit 1
fi

exec "$PYTHON_BIN" -m uvicorn api.app.main:app --host "$HOST" --port "$PORT" $RELOAD_FLAG
