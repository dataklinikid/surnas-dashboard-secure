#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${SURNAS_PYTHON_BIN:-${project_dir}/.venv/bin/python}"
gunicorn_bin="$(dirname "${python_bin}")/gunicorn"

if [[ ! -x "${python_bin}" ]]; then
  echo "ERROR: Python virtual environment tidak ditemukan: ${python_bin}" >&2
  exit 1
fi

echo "[1/5] Django test"
"${python_bin}" "${project_dir}/manage.py" test --settings=config.settings.test

echo "[2/5] Django system check"
"${python_bin}" "${project_dir}/manage.py" check --settings=config.settings.test

echo "[3/5] Import dependency production"
"${python_bin}" -c "import gunicorn, psycopg; print('gunicorn=' + gunicorn.__version__); print('psycopg=' + psycopg.__version__)"

echo "[4/5] Validasi sintaks konfigurasi Gunicorn"
DJANGO_SETTINGS_MODULE=config.settings.test "${gunicorn_bin}" --check-config \
  --config "${project_dir}/deploy/gunicorn.conf.py" \
  config.wsgi:application

echo "[5/5] Validasi Python"
"${python_bin}" -m compileall -q \
  "${project_dir}/config" \
  "${project_dir}/aggregate" \
  "${project_dir}/surnasdes26" \
  "${project_dir}/deploy/gunicorn.conf.py"

echo "STAGE 7A: OK"
