"""
Step 4 — Build & query protocol reference database.

Sources:
  - rtl_433 protocols (from `rtl_433 -R help` or src list)
  - Flipper Zero supported protocols (subghz_protocol_registry.h equivalents)
  - SIGIDWiki dump (manual seed)

For each record, attempts to match its protocol name to the DB using rapidfuzz.
Output: 04_protocols_db/matched.jsonl  (records gain "protocol_match" field)
        04_protocols_db/protocols_db.json  (the reference DB itself)
"""
import json, importlib.util, subprocess, re
from pathlib import Path
from rapidfuzz import fuzz, process

spec = importlib.util.spec_from_file_location("config", Path(__file__).parent / "00_config.py")
config = importlib.util.module_from_spec(spec); spec.loader.exec_module(config)

IN  = config.VALIDATION / "validated.jsonl"
OUT = config.PROTOCOLS_DB / "matched.jsonl"
DB  = config.PROTOCOLS_DB / "protocols_db.json"
LOG = config.LOGS / "04_protocols.log"

def log(msg):
    line = f"[04_protocols] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

# ---------- Build protocol DB ----------
def build_protocols_db():
    db = {}

    # 1) rtl_433 protocols
    try:
        out = subprocess.check_output(["rtl_433", "-R", "help"], stderr=subprocess.STDOUT, timeout=10).decode()
        for line in out.splitlines():
            m = re.match(r"\s*\[\s*(\d+)\s*\]\s+(.+)", line)
            if m:
                pid, name = m.group(1), m.group(2).strip()
                db[name.lower()] = {"source": "rtl_433", "id": pid, "name": name, "category": "OOK/FSK ISM"}
    except Exception as e:
        log(f"rtl_433 not available: {e}")

    # 2) Flipper SubGHz known protocols (hardcoded — public list)
    flipper_protocols = [
        ("Princeton",       "OOK", "300-928 MHz"),
        ("Came",            "OOK", "433.92 MHz"),
        ("Came TwEE",       "OOK", "433.92 MHz"),
        ("Nice Flo",        "OOK", "433.92 MHz"),
        ("Nice FloR-S",     "OOK", "433.92 MHz"),
        ("Faac SLH",        "OOK", "433.92 MHz"),
        ("Hörmann HSM",     "FSK", "868.3 MHz"),
        ("Somfy Telis",     "FSK", "433.42 MHz"),
        ("Somfy Keytis",    "FSK", "433.42 MHz"),
        ("Chamberlain",     "OOK", "300-433 MHz"),
        ("Linear",          "OOK", "300-400 MHz"),
        ("Gate TX",         "OOK", "433.92 MHz"),
        ("Keeloq",          "OOK", "300-433 MHz"),
        ("Star Line",       "FSK", "433-868 MHz"),
        ("KIA Seed",        "OOK", "433.92 MHz"),
        ("Marantec",        "OOK", "433.92 MHz"),
        ("Magellan",        "OOK", "433.92 MHz"),
        ("Intertechno V3",  "OOK", "433.92 MHz"),
        ("CAME Atomo",      "OOK", "433.92 MHz"),
        ("Doitrand",        "OOK", "433.92 MHz"),
        ("Phoenix V2",      "OOK", "433.92 MHz"),
        ("Honeywell WDB",   "FSK", "868.3 MHz"),
        ("BFT Mitto",       "OOK", "433.92 MHz"),
        ("Holtek",          "OOK", "433.92 MHz"),
        ("Holtek HT12",     "OOK", "433.92 MHz"),
        ("UNILARM",         "OOK", "433.92 MHz"),
    ]
    for name, mod, freq in flipper_protocols:
        db[name.lower()] = {"source": "flipper_subghz", "name": name, "modulation": mod, "freq_range": freq}

    # 3) Known cellular / standards bands
    standards = [
        ("LTE Band 8",  "QPSK/16QAM/64QAM", "880-915/925-960 MHz"),
        ("LTE Band 20", "QPSK/16QAM/64QAM", "832-862/791-821 MHz"),
        ("LTE Band 28", "QPSK/16QAM/64QAM", "703-733/758-788 MHz"),
        ("GSM-900",     "GMSK",              "880-915/925-960 MHz"),
        ("GSM-R",       "GMSK",              "876-880/921-925 MHz"),
        ("TETRA",       "π/4-DQPSK",        "380-400 MHz"),
        ("TETRAPOL",    "GMSK",              "380-400 MHz"),
        ("DMR",         "4FSK",              "VHF/UHF land mobile"),
        ("APCO P25",    "C4FM/CQPSK",       "VHF/700/800 MHz"),
        ("ADS-B",       "PPM",               "1090 MHz"),
        ("Mode S",      "PPM",               "1090 MHz"),
        ("UAT",         "OQPSK",             "978 MHz (US)"),
        ("DME",         "Pulse-pair",        "962-1213 MHz"),
        ("LoRaWAN EU",  "CSS",               "863-870 MHz"),
        ("LoRaWAN US",  "CSS",               "902-928 MHz"),
        ("Sigfox",      "DBPSK",             "868.13 MHz (EU)"),
        ("Wize",        "GFSK",              "169 / 868.8 MHz"),
        ("Z-Wave EU",   "FSK",               "868.42 MHz"),
        ("Z-Wave US",   "FSK",               "908.42 MHz"),
        ("ILS Glide",   "AM",                "328.6-335.4 MHz"),
        ("Cospas-Sarsat","BPSK",             "406.0-406.1 MHz"),
        ("MICS",        "FSK",               "402-405 MHz"),
        ("PMR446",      "FM",                "446 MHz"),
        ("FRS",         "FM",                "462/467 MHz"),
    ]
    for name, mod, freq in standards:
        db[name.lower()] = {"source": "standards", "name": name, "modulation": mod, "freq_range": freq}

    return db

if DB.exists():
    db = json.load(open(DB))
    log(f"Loaded existing DB ({len(db)} protocols)")
else:
    db = build_protocols_db()
    json.dump(db, open(DB, "w"), indent=2, ensure_ascii=False)
    log(f"Built DB with {len(db)} protocols → {DB}")

# ---------- Match each record ----------
records = [json.loads(l) for l in open(IN)]
choices = list(db.keys())
matched_count = 0
unknown_count = 0

for r in records:
    proto = r.get("protocol")
    if proto:
        proto_l = proto.lower()
        # exact match
        if proto_l in db:
            r["protocol_match"] = {"matched": True, "score": 100, "db_entry": db[proto_l]}
            matched_count += 1
        else:
            # fuzzy
            best = process.extractOne(proto_l, choices, scorer=fuzz.ratio)
            if best and best[1] >= config.BACKENDS["protocol_matching"]["fuzzy_threshold"]:
                r["protocol_match"] = {"matched": True, "score": best[1], "db_entry": db[best[0]]}
                matched_count += 1
            else:
                r["protocol_match"] = {"matched": False, "score": best[1] if best else 0, "db_entry": None}
                unknown_count += 1
    else:
        # No protocol field → try infer from text (Q&A allocations)
        text = " ".join(filter(None, [r.get("answer",""), str(r.get("metadata",{}).get("application","") or "")]))
        text_l = text.lower()
        hits = [name for name in choices if name in text_l]
        if hits:
            r["protocol_match"] = {"matched": True, "score": 90, "inferred_from_text": True, "db_entry": db[hits[0]], "all_hits": hits[:5]}
            matched_count += 1
        else:
            r["protocol_match"] = {"matched": None, "score": None, "db_entry": None}

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

log(f"Wrote {len(records)} → {OUT}")
log(f"Matched: {matched_count} | Unknown: {unknown_count} | N/A: {len(records)-matched_count-unknown_count}")
