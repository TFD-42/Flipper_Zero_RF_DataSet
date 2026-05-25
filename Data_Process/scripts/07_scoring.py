"""
Step 7 — Aggregate all checks into a final quality score.

Score breakdown (max 13):
  frequency_valid    : +2   (03_validation.frequency_in_range)
  protocol_known     : +2   (04_protocols.matched)
  timings_coherent   : +2   (03_validation.pulse_timings_sane)
  sdr_match          : +3   (skipped → 0)
  not_hallucinated   : +1   (05_llm.verdict == VALID)
  fact_check_passed  : +2   (06_fact.verdict == entailment)
  no_duplicate       : +1   (always +1 since dedup ran)

Thresholds:
  >= 8 → verified
  5-7  → partial
  < 5  → rejected

Output: 07_scoring/scored.jsonl
"""
import json, importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("config", Path(__file__).parent / "00_config.py")
config = importlib.util.module_from_spec(spec); spec.loader.exec_module(config)

IN  = config.SDR_CHECK / "fact_verified.jsonl"
OUT = config.SCORING / "scored.jsonl"
LOG = config.LOGS / "07_scoring.log"

def log(msg):
    line = f"[07_scoring] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

W = config.SCORING_WEIGHTS
T = config.SCORING_THRESHOLDS

records = [json.loads(l) for l in open(IN)]
log(f"Loaded {len(records)} records")

buckets = {"verified": 0, "partial": 0, "rejected": 0}

for r in records:
    v = r.get("validation", {})
    score = 0
    breakdown = {}

    # frequency
    pts = W["frequency_valid"] if v.get("frequency_in_range") is True else 0
    score += pts; breakdown["frequency_valid"] = pts

    # protocol
    pts = W["protocol_known"] if (r.get("protocol_match") or {}).get("matched") is True else 0
    score += pts; breakdown["protocol_known"] = pts

    # timings
    pts = W["timings_coherent"] if v.get("pulse_timings_sane") is True else 0
    score += pts; breakdown["timings_coherent"] = pts

    # SDR — always 0 (skipped)
    breakdown["sdr_match"] = 0

    # not hallucinated
    pts = W["not_hallucinated"] if r.get("llm_verdict") == "VALID" else 0
    score += pts; breakdown["not_hallucinated"] = pts

    # fact check
    pts = W["fact_check_passed"] if (r.get("fact_check") or {}).get("verdict") == "entailment" else 0
    score += pts; breakdown["fact_check_passed"] = pts

    # dedup pass
    score += W["no_duplicate"]; breakdown["no_duplicate"] = W["no_duplicate"]

    r["score"] = score
    r["score_breakdown"] = breakdown

    # Bucket
    if score >= T["verified"]:
        bucket = "verified"
    elif score >= T["partial"]:
        bucket = "partial"
    else:
        bucket = "rejected"
    r["bucket"] = bucket
    buckets[bucket] += 1

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

log(f"Wrote {len(records)} → {OUT}")
log(f"Buckets: {buckets}")
