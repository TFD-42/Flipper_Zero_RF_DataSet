"""
Step 8 — Export final HuggingFace-ready JSONL splits + audit manifest.

Outputs in 08_output/ :
  verified.jsonl   — score >= 8 (training-grade)
  partial.jsonl    — 5-7 (needs human audit)
  rejected.jsonl   — < 5 (discarded but kept for traceability)
  manifest.json    — counts, percentages, source attribution
  audit_sample.jsonl — random sample of 50 'partial' for human review
"""
import json, importlib.util, random, hashlib
from pathlib import Path
from collections import Counter

spec = importlib.util.spec_from_file_location("config", Path(__file__).parent / "00_config.py")
config = importlib.util.module_from_spec(spec); spec.loader.exec_module(config)

IN  = config.SCORING / "scored.jsonl"
OUT = config.OUTPUT
LOG = config.LOGS / "08_export.log"

def log(msg):
    line = f"[08_export] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

records = [json.loads(l) for l in open(IN)]
log(f"Loaded {len(records)} scored records")

verified = [r for r in records if r["bucket"] == "verified"]
partial  = [r for r in records if r["bucket"] == "partial"]
rejected = [r for r in records if r["bucket"] == "rejected"]

# Strip heavy intermediate fields for the verified output (keep traceability fields)
def slim(r):
    return {
        "id": hashlib.md5(json.dumps(r, sort_keys=True, default=str).encode()).hexdigest()[:16],
        "source": r.get("source"),
        "category": r.get("category"),
        "freq_hz": r.get("freq_hz"),
        "freq_low_hz": r.get("freq_low_hz"),
        "freq_high_hz": r.get("freq_high_hz"),
        "country": r.get("country"),
        "modulation": r.get("modulation"),
        "protocol": r.get("protocol"),
        "question": r.get("question"),
        "answer": r.get("answer"),
        "raw_data": r.get("raw_data"),
        "metadata": r.get("metadata"),
        "protocol_match": r.get("protocol_match"),
        "score": r.get("score"),
        "score_breakdown": r.get("score_breakdown"),
        "llm_verdict": r.get("llm_verdict"),
        "fact_check": r.get("fact_check"),
        "validation": r.get("validation"),
        "cross_check": r.get("cross_check"),
        "confidence_pct": (r.get("cross_check") or {}).get("confidence_pct"),
        "confidence_bucket": (r.get("cross_check") or {}).get("bucket"),
        "bucket": r.get("bucket"),
    }

for name, items in [("verified", verified), ("partial", partial), ("rejected", rejected)]:
    p = OUT / f"{name}.jsonl"
    with open(p, "w") as f:
        for r in items:
            f.write(json.dumps(slim(r), ensure_ascii=False) + "\n")
    log(f"Wrote {name}: {len(items)} → {p}")

# Audit sample
random.seed(42)
audit_sample = random.sample(partial, min(50, len(partial)))
with open(OUT / "audit_sample.jsonl", "w") as f:
    for r in audit_sample:
        f.write(json.dumps(slim(r), ensure_ascii=False) + "\n")
log(f"Audit sample: {len(audit_sample)} entries → 08_output/audit_sample.jsonl")

# Manifest
manifest = {
    "pipeline_version": "1.0",
    "total_records": len(records),
    "buckets": {
        "verified": len(verified),
        "partial":  len(partial),
        "rejected": len(rejected),
    },
    "verified_pct": round(100*len(verified)/max(len(records),1), 2),
    "partial_pct":  round(100*len(partial)/max(len(records),1), 2),
    "rejected_pct": round(100*len(rejected)/max(len(records),1), 2),
    "source_distribution": dict(Counter(r.get("source","unknown") for r in records)),
    "category_distribution": dict(Counter(r.get("category","unknown") for r in records)),
    "country_distribution": dict(Counter(r.get("country") for r in records if r.get("country"))),
    "llm_verdict_distribution": dict(Counter(r.get("llm_verdict","none") for r in records)),
    "fact_check_distribution": dict(Counter((r.get("fact_check") or {}).get("verdict","none") for r in records)),
    "confidence_bucket_distribution": dict(Counter((r.get("cross_check") or {}).get("bucket","none") for r in records)),
    "confidence_pct_avg": round(
        sum((r.get("cross_check") or {}).get("confidence_pct", 0) for r in records) / max(len(records), 1),
        1,
    ),
}

json.dump(manifest, open(OUT / "manifest.json", "w"), indent=2, ensure_ascii=False)
log(f"Manifest:")
log(json.dumps(manifest, indent=2, ensure_ascii=False))
