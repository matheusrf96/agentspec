#!/usr/bin/env bash
set -euo pipefail

echo "=== Pre-push Validation ==="
echo ""

echo "--- ruff check ---"
ruff check .
echo "OK"
echo ""

echo "--- ruff format check ---"
ruff format --check .
echo "OK"
echo ""

echo "--- flake8 ---"
flake8 agentspec/ tests/
echo "OK"
echo ""

echo "--- pytest ---"
python -m pytest tests/ -q --tb=short
echo ""

echo "=== All checks passed! Ready to push. ==="
