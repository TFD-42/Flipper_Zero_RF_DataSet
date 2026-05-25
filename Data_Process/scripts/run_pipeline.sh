#!/usr/bin/env bash
# Master orchestrator — runs all pipeline steps sequentially with logging.
set -e
cd "$(dirname "$0")"

START=$(date +%s)
echo "=========================================="
echo "DataSet_Process Pipeline — $(date)"
echo "=========================================="

run_step() {
    local step="$1"
    local script="$2"
    echo ""
    echo "[STEP $step] Running $script..."
    local t0=$(date +%s)
    python3 "$script"
    local dt=$(( $(date +%s) - t0 ))
    echo "[STEP $step] Done in ${dt}s"
}

run_step 1 01_ingest_sources.py
run_step 2 02_dedup.py
run_step 3 03_rf_validation.py
run_step 4 04_protocols_db.py
run_step 5 05_llm_hallucination.py
run_step 6 06_fact_verification.py
run_step 7 07_scoring.py
run_step 8 08_export.py

TOTAL=$(( $(date +%s) - START ))
echo ""
echo "=========================================="
echo "PIPELINE DONE in ${TOTAL}s"
echo "=========================================="
echo ""
BASE_DIR="${DATASET_PROCESS_BASE:-/home/xwiss/Desktop/DataSet_Process}"
echo "Final outputs in ${BASE_DIR}/08_output/ :"
ls -lah "${BASE_DIR}/08_output/"
