#!/usr/bin/env bash

# -----------------------------------------------------------------------------
# Set Up Local Airflow IDE Environment
# -----------------------------------------------------------------------------
#
# Purpose:
#   Creates or checks .venv-airflow-ide so VS Code can resolve Airflow imports,
#   hover over Airflow classes, and use F12/go-to-definition while editing DAGs.
#
# macOS / Linux:
#   bash orchestration/airflow/scripts/setup_airflow_ide_env.sh
#
# macOS / Linux, force reinstall/check again:
#   bash orchestration/airflow/scripts/setup_airflow_ide_env.sh --refresh
#
# Optional macOS / Linux direct execution:
#   chmod +x orchestration/airflow/scripts/setup_airflow_ide_env.sh
#   ./orchestration/airflow/scripts/setup_airflow_ide_env.sh
#
# Windows:
#   Run from Git Bash or WSL:
#     bash orchestration/airflow/scripts/setup_airflow_ide_env.sh
#
#   Native PowerShell does not run .sh files directly. Use Git Bash/WSL, or create
#   a separate .ps1 script later if Windows-native setup is needed.
#
# VS Code interpreter after setup:
#   .venv-airflow-ide/bin/python
#
# Notes:
#   This environment is only for local editor support.
#   The real Airflow runtime remains Astro/Docker.
# -----------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

VENV_PATH="${REPO_ROOT}/.venv-airflow-ide"
REQUIREMENTS_FILE="${REPO_ROOT}/orchestration/airflow/requirements.txt"

AIRFLOW_VERSION="3.2.2"
FORCE_REFRESH="${1:-}"

run_import_check() {
  "${VENV_PATH}/bin/python" - <<'PY'
from pathlib import Path

from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import dag, task
from pendulum import datetime
import duckdb
import dbt.adapters.duckdb

print("Airflow IDE environment OK")
print(EmptyOperator)
print(f"DuckDB: {duckdb.__version__}")
print(f"Temporary path exists: {Path('/tmp').exists()}")
PY
}

cd "${REPO_ROOT}"

echo "Repo root: ${REPO_ROOT}"
echo "IDE virtual environment: ${VENV_PATH}"

if [ -d "${VENV_PATH}" ] && [ "${FORCE_REFRESH}" != "--refresh" ]; then
  echo ".venv-airflow-ide already exists. Checking whether it is ready..."

  if run_import_check; then
    echo ""
    echo "Environment is already ready. No install needed."
    echo "Use this interpreter in VS Code:"
    echo "${VENV_PATH}/bin/python"
    exit 0
  fi

  echo ""
  echo "Environment exists, but the import check failed. Reinstalling packages..."
fi

if [ ! -d "${VENV_PATH}" ]; then
  echo "Creating .venv-airflow-ide..."
  python3 -m venv "${VENV_PATH}"
fi

source "${VENV_PATH}/bin/activate"

echo "Upgrading pip..."
python -m pip install --upgrade pip

LOCAL_PYTHON_VERSION="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

echo "Installing Apache Airflow ${AIRFLOW_VERSION} for local VS Code support..."
echo "Local Python version: ${LOCAL_PYTHON_VERSION}"

pip install "apache-airflow==${AIRFLOW_VERSION}" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${LOCAL_PYTHON_VERSION}.txt"

echo "Installing local Airflow project requirements..."
pip install -r "${REQUIREMENTS_FILE}"

echo "Testing imports..."
run_import_check

echo ""
echo "Environment setup complete."
echo "Use this interpreter in VS Code:"
echo "${VENV_PATH}/bin/python"