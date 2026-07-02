#!/usr/bin/env bash
# Run PRTOE validation tests 1-9; skip test 10 (full publication / PolyChord).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# classy wheel targets the active `python` (conda 3.13 here), not system python3.
PY="${PYTHON:-python}"
LOG="${ROOT}/Test-Results/validation_suite_$(date +%Y%m%d_%H%M%S).log"
mkdir -p Test-Results

run_step() {
  local n="$1" name="$2"
  shift 2
  echo "" | tee -a "$LOG"
  echo "========== TEST $n: $name ==========" | tee -a "$LOG"
  echo "Command: $*" | tee -a "$LOG"
  local t0=$SECONDS
  if "$@" >>"$LOG" 2>&1; then
    echo "RESULT: PASS (${SECONDS}-$t0 s)" | tee -a "$LOG"
    return 0
  else
    local rc=$?
    echo "RESULT: FAIL exit=$rc (${SECONDS}-$t0 s)" | tee -a "$LOG"
    return $rc
  fi
}

echo "Validation suite log: $LOG"
: >"$LOG"

FAIL=0
run_step 1 "env check" "$PY" scripts/check_prtoe_env.py || FAIL=1
run_step 2 "local gravity" "$PY" scripts/test_local_gravity.py --classy || FAIL=1
run_step 3 "background only" ./class test_prtoe_bg_only.ini || FAIL=1
run_step 4 "null simple mPk" ./class test_prtoe_null_simple.ini || FAIL=1
run_step 5 "active mPk fast" ./class test_prtoe_mpk_fast.ini || FAIL=1
run_step 6 "BBN activation" "$PY" scripts/test_bbn_activation.py --classy || FAIL=1
run_step 7 "null publication fast" ./class test_prtoe_null_publication_fast.ini || FAIL=1
run_step 8 "LambdaCDM baseline" ./class test_lambda_cdm.ini || FAIL=1
run_step 9 "null limit Python" "$PY" scripts/test_prtoe_null_limit.py --fast --null-only || FAIL=1

echo "" | tee -a "$LOG"
echo "========== SUITE SUMMARY ==========" | tee -a "$LOG"
if [[ $FAIL -eq 0 ]]; then
  echo "ALL TESTS 1-9 PASSED" | tee -a "$LOG"
else
  echo "ONE OR MORE TESTS FAILED (see $LOG)" | tee -a "$LOG"
fi
echo "Skipped test 10 (full publication / PolyChord)" | tee -a "$LOG"
exit $FAIL