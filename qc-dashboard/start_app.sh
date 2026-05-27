#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -z "${PYTHON_BIN:-}" ]]; then
    if [[ -n "${CONDA_PREFIX:-}" && -x "$CONDA_PREFIX/bin/python" ]]; then
        PYTHON_BIN="$CONDA_PREFIX/bin/python"
    else
        PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
    fi
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8002}"

# Propagate the actual host/port to dash_app/config.py so the in-process
# Dash callbacks reach the API on the right URL when overridden.
export API_HOST="${API_HOST:-$HOST}"
export API_PORT="${API_PORT:-$PORT}"
if [[ "${RELOAD:-1}" == "0" || "${RELOAD:-}" == "false" ]]; then
    RELOAD_FLAG=""
else
    RELOAD_FLAG="${RELOAD_FLAG:---reload}"
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "VCBench Python environment not found at: $PYTHON_BIN" >&2
    echo "Activate the conda env first (e.g. 'conda activate vcbench')," >&2
    echo "or create a local venv from the repository root with:" >&2
    echo "  conda create -p ./.venv python=3.11 pip -y" >&2
    echo "  ./.venv/bin/python -m pip install -r requirements.txt" >&2
    exit 1
fi

cd "$SCRIPT_DIR"
exec "$PYTHON_BIN" -m uvicorn api.app.main:app --host "$HOST" --port "$PORT" $RELOAD_FLAG
