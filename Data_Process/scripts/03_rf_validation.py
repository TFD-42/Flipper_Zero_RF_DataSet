"""
Step 3 — RF rule-based validation + multi-source cross-check + confidence scoring.

Part A — Rule checks (offline, fast):
  - frequency_in_range : freq_hz dans une bande connue
  - modulation_valid   : modulation in VALID_MODULATIONS
  - pulse_timings_sane : |pulse| < 20000 µs
  - country_code_valid : ISO 2 letters
  - text_length_sane   : Q/A entre 10 et 4000 chars

Part B — Cross-check (network):
  - HF dataset match    : rtl_433 / Flipper RF community datasets
  - Wikipedia API       : frequency band / service pages
  - Web search          : FCC / ITU / ANFR / regulators + RTL-SDR / Flipper forums

Part C — Confidence scoring (independent of Step 07 score):
  - confidence (0.0-1.0) and confidence_pct (0-100)
  - bucket: high_confidence | medium_confidence | low_confidence | no_confidence
  - Bonuses: triangulation_3plus, official_plus_forum
  - Penalties: contradiction, no_source_found, single_source_only, country_mismatch

Output: 03_validation/validated.jsonl
        Each record gains "validation" (rules) and "cross_check" (sources + confidence).

Env vars to enable cross-check:
  CROSS_CHECK=1           # turn on networked cross-check (default OFF for speed)
  CROSS_CHECK_LIMIT=N     # limit cross-check to first N records (debug)
  BRAVE_API_KEY=...       # optional, fastest search backend
  SERPER_API_KEY=...      # alternative
"""
import json, re, importlib.util, os, time
from pathlib import Path

spec = importlib.util.spec_from_file_location("config", Path(__file__).parent / "00_config.py")
config = importlib.util.module_from_spec(spec); spec.loader.exec_module(config)

# Lazy import of cross-check helpers (avoid imports if disabled)
CROSS_CHECK_ENABLED = os.environ.get("CROSS_CHECK", "0") == "1"
CROSS_CHECK_LIMIT   = int(os.environ.get("CROSS_CHECK_LIMIT", "0"))  # 0 = no limit

IN  = config.DEDUP / "dedup.jsonl"
OUT = config.VALIDATION / "validated.jsonl"
REPORT = config.VALIDATION / "validation_report.json"
LOG = config.LOGS / "03_validation.log"

def log(msg):
    line = f"[03_validation] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

# ---------- Rule checks ----------
def in_known_band(freq_hz):
    if freq_hz is None: return None
    return any(lo <= freq_hz <= hi for lo, hi in config.KNOWN_RF_BANDS)

def modulation_valid(mod):
    if not mod: return None
    return any(m.lower() == mod.lower() or mod.lower().startswith(m.lower()) for m in config.VALID_MODULATIONS)

def pulse_timings_sane(raw_data):
    if not raw_data: return None
    try:
        nums = [int(x) for x in raw_data.split() if x.lstrip("-").isdigit()]
        if not nums: return False
        return max(abs(n) for n in nums) < 20000
    except Exception:
        return False

COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
def country_valid(cc):
    if not cc: return None
    return bool(COUNTRY_RE.match(cc)) or cc == "ALL"

def text_length_sane(*texts):
    lens = [len(t) for t in texts if t]
    if not lens: return None
    return all(10 <= L <= 4000 for L in lens)

# ---------- Cross-check (network) ----------
def cross_check_record(rec) -> dict:
    """Run HF + Wikipedia + WebSearch cross-checks and aggregate confidence."""
    import _cross_check as cc
    cfg_sources = config.CROSS_CHECK_SOURCES
    cfg_weights = config.CONFIDENCE_SCORING

    freq_hz = rec.get("freq_hz")
    country = rec.get("country")
    meta = rec.get("metadata", {}) or {}
    service = meta.get("service") or rec.get("protocol") or ""
    modulation = rec.get("modulation")

    results = []
    # 1) HF datasets
    try:
        results.append(cc.hf_dataset_match(freq_hz, country, modulation, cfg_sources))
    except Exception as e:
        results.append({"source": "hf_dataset", "matched": None, "confidence": 0.0,
                        "evidence": f"error: {e}", "url": None, "stale": False, "country_match": None})
    # 2) Wikipedia
    try:
        results.append(cc.wikipedia_check(freq_hz, service, country, cfg_sources["wikipedia"]))
    except Exception as e:
        results.append({"source": "wikipedia", "matched": None, "confidence": 0.0,
                        "evidence": f"error: {e}", "url": None, "stale": False, "country_match": None})
    # 3) Web search (regulators + forums)
    try:
        results.append(cc.web_cross_check(freq_hz, service, country, cfg_sources["websearch"]))
    except Exception as e:
        results.append({"source": "websearch", "matched": None, "confidence": 0.0,
                        "evidence": f"error: {e}", "url": None, "stale": False, "country_match": None})

    agg = cc.aggregate_confidence(results, cfg_weights)
    return {"sources": results, **agg}

# ---------- Main ----------
records = [json.loads(l) for l in open(IN)]
log(f"Loaded {len(records)} records to validate")
log(f"CROSS_CHECK={'ON' if CROSS_CHECK_ENABLED else 'OFF'}  (set CROSS_CHECK=1 to enable network checks)")
if CROSS_CHECK_LIMIT:
    log(f"CROSS_CHECK_LIMIT={CROSS_CHECK_LIMIT} (debug mode)")

stats = {
    "frequency_in_range_pass": 0, "frequency_in_range_fail": 0, "frequency_na": 0,
    "modulation_valid_pass": 0,   "modulation_valid_fail": 0,   "modulation_na": 0,
    "pulse_timings_pass": 0,      "pulse_timings_fail": 0,      "pulse_na": 0,
    "country_valid_pass": 0,      "country_valid_fail": 0,      "country_na": 0,
    "text_length_pass": 0,        "text_length_fail": 0,        "text_na": 0,
    "all_checks_pass": 0,
    "cross_check_run": 0,
    "confidence_high":   0,
    "confidence_medium": 0,
    "confidence_low":    0,
    "confidence_none":   0,
}

def bump(key, val):
    if val is True: stats[f"{key}_pass"] += 1
    elif val is False: stats[f"{key}_fail"] += 1
    else: stats[f"{key}_na"] += 1

t0 = time.time()
cc_count = 0

for i, r in enumerate(records):
    # Part A — Rule checks
    v_freq  = in_known_band(r.get("freq_hz"))
    v_mod   = modulation_valid(r.get("modulation"))
    v_pulse = pulse_timings_sane(r.get("raw_data"))
    v_cc    = country_valid(r.get("country"))
    v_text  = text_length_sane(r.get("question"), r.get("answer"))

    r["validation"] = {
        "frequency_in_range": v_freq,
        "modulation_valid":   v_mod,
        "pulse_timings_sane": v_pulse,
        "country_code_valid": v_cc,
        "text_length_sane":   v_text,
    }
    bump("frequency_in_range", v_freq)
    bump("modulation_valid", v_mod)
    bump("pulse_timings", v_pulse)
    bump("country_valid", v_cc)
    bump("text_length", v_text)

    checks = [v_freq, v_mod, v_pulse, v_cc, v_text]
    relevant = [c for c in checks if c is not None]
    if relevant and all(c is True for c in relevant):
        stats["all_checks_pass"] += 1

    # Part B/C — Cross-check + confidence (network, only if enabled)
    if CROSS_CHECK_ENABLED and (CROSS_CHECK_LIMIT == 0 or cc_count < CROSS_CHECK_LIMIT):
        try:
            xc = cross_check_record(r)
            r["cross_check"] = xc
            stats["cross_check_run"] += 1
            bucket = xc["bucket"]
            if bucket == "high_confidence":   stats["confidence_high"]   += 1
            elif bucket == "medium_confidence": stats["confidence_medium"] += 1
            elif bucket == "low_confidence":  stats["confidence_low"]    += 1
            else:                              stats["confidence_none"]   += 1
            cc_count += 1
            if cc_count % 25 == 0:
                elapsed = time.time() - t0
                log(f"  cross-check {cc_count} done | elapsed {elapsed:.0f}s | conf_high={stats['confidence_high']} med={stats['confidence_medium']} low={stats['confidence_low']}")
        except Exception as e:
            log(f"cross-check failed on record {i}: {e}")
            r["cross_check"] = {"error": str(e)}
    else:
        r["cross_check"] = {"skipped": True, "reason": "CROSS_CHECK env not set"}

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

json.dump(stats, open(REPORT, "w"), indent=2)
log(f"Wrote {len(records)} → {OUT}")
log(f"Stats: {json.dumps(stats, indent=2)}")
log(f"Elapsed: {time.time()-t0:.0f}s")
