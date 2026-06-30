#!/bin/bash
set -e
# Run core INI tests and write logs into Test_Results
cd "$(dirname "$0")/.."
mkdir -p Test_Results
run_ini(){
  ini="$1"
  out="Test_Results/${ini%.ini}.log"
  echo "=== Running $ini at $(date -Iseconds) ===" > "$out"
  if [ -f "$ini" ]; then
    ./class "$ini" >> "$out" 2>&1 || echo "EXIT_STATUS=$?" >> "$out"
  else
    echo "MISSING: $ini" >> "$out"
  fi
}
run_ini test_lambda_cdm.ini
run_ini test_prtoe_background.ini
run_ini test_prtoe_null_limit.ini
