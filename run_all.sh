#!/usr/bin/env bash
# полный прогон лабы: поднять стек, построить слои, бенчмарк, эксперименты, графики
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

SF_LIST="${SF_LIST:-sf1 sf10}"
REPEATS="${REPEATS:-5}"

docker compose up -d --wait

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

for sf in $SF_LIST; do
  echo "######## $sf"
  .venv/bin/python bench/run_benchmark.py --sf "$sf" --repeats "$REPEATS"
  .venv/bin/python bench/run_benchmark.py --sf "$sf" --repeats 7 --queries-only
  .venv/bin/python bench/experiments.py metadata --sf "$sf" --repeats "$REPEATS"
  .venv/bin/python bench/experiments.py cache --sf "$sf" --repeats "$REPEATS"
done

.venv/bin/python bench/plots.py
