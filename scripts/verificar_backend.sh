#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=backend
python -m compileall -q backend/app
python -m pytest -q backend/tests
printf '\nPruebas automáticas terminadas. Para RAG real: ollama list y prueba desde frontend.\n'
