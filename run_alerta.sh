#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/vuelos.log"

mkdir -p "$LOG_DIR"

if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

ROUTES_OVERRIDE="${1:-}"
RUN_TS="$(date '+%Y-%m-%d %H:%M:%S %z')"

{
  echo
  echo "================================================================================"
  echo "[$RUN_TS] Inicio de corrida de vuelos"
  if [[ -n "$ROUTES_OVERRIDE" ]]; then
    echo "[$RUN_TS] ROUTES override: $ROUTES_OVERRIDE"
  else
    echo "[$RUN_TS] ROUTES override: (none, se usa .env)"
  fi
  echo "================================================================================"
} >> "$LOG_FILE"

cd "$SCRIPT_DIR"

if [[ -n "$ROUTES_OVERRIDE" ]]; then
  ROUTES="$ROUTES_OVERRIDE" "$PYTHON_BIN" vuelo_alerta.py >> "$LOG_FILE" 2>&1
else
  "$PYTHON_BIN" vuelo_alerta.py >> "$LOG_FILE" 2>&1
fi
