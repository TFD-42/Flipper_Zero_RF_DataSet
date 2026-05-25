"""
Step 3 — RF rule-based validation (no model, pure regex/range checks).

Checks:
  - frequency_in_range : freq_hz dans une bande connue
  - modulation_valid   : modulation ∈ VALID_MODULATIONS
  - pulse_timings_sane : |pulse| < 20000 µs
  - country_code_valid : ISO 2 letters
  - text_length_sane   : Q/A entre 10 et 4000 chars

Output: 03_validation/validated.jsonl
        Each record gains a "validation" subdict with per-check booleans.
"""
import json, re, importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("config", Path(__file__).parent / "00_config.py")
config = importlib.util.module_from_spec(spec); spec.loader.exec_module(config)

IN  = config.DEDUP / "dedup.jsonl"
OUT = config.VALIDATION / "validated.jsonl"
REPORT = config.VALIDATION / "validation_report.json"
LOG = config.LOGS / "03_validation.log"

def log(msg):
    line = f"[03_validation] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

def in_known_band(freq_hz):
    if freq_hz is None: return None  # N/A for Q&A
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

records = [json.loads(l) for l in open(IN)]
log(f"Loaded {len(records)} records to validate")

stats = {
    "frequency_in_range_pass": 0, "frequency_in_range_fail": 0, "frequency_na": 0,
    "modulation_valid_pass": 0,   "modulation_valid_fail": 0,   "modulation_na": 0,
    "pulse_timings_pass": 0,      "pulse_timings_fail": 0,      "pulse_na": 0,
    "country_valid_pass": 0,      "country_valid_fail": 0,      "country_na": 0,
    "text_length_pass": 0,        "text_length_fail": 0,        "text_na": 0,
    "all_checks_pass": 0,
}

def bump(key, val):
    if val is True: stats[f"{key}_pass"] += 1
    elif val is False: stats[f"{key}_fail"] += 1
    else: stats[f"{key}_na"] += 1

for r in records:
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

    # all_checks_pass = all non-None checks return True
    checks = [v_freq, v_mod, v_pulse, v_cc, v_text]
    relevant = [c for c in checks if c is not None]
    if relevant and all(c is True for c in relevant):
        stats["all_checks_pass"] += 1

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

json.dump(stats, open(REPORT, "w"), indent=2)
log(f"Wrote {len(records)} → {OUT}")
log(f"Stats: {json.dumps(stats, indent=2)}")
