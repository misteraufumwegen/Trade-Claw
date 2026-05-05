#!/usr/bin/env bash
# Trade-Claw launcher (macOS).
# Double-click this file in Finder — first run will create venv & install deps.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "[start-app] Python 3.11+ wurde nicht gefunden."
  echo "            Bitte installieren (z.B. via 'brew install python@3.11')."
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

"$PYTHON" launcher.py
status=$?
if [ $status -ne 0 ]; then
  echo
  echo "[start-app] Trade-Claw wurde mit Fehler beendet (Code $status)."
  read -n 1 -s -r -p "Press any key to close..."
fi
exit $status
