"""
Step 1 — Ingest from multiple sources into a unified raw JSONL.

Sources:
  1. GitHub repo Flipper_Zero_RF_DataSet (git clone)
  2. HuggingFace datasets (datasets.load_dataset)
  3. Local Flipper .sub files (parsed from RAW_Data)

Output: 01_raw_input/raw_unified.jsonl  (one JSON per line)
Schema:
  {
    "source": str,         # "github" | "hf:<name>" | "local_sub"
    "source_path": str,
    "category": str,       # "qa" | "allocation" | "capture"
    "freq_hz": float|null,
    "modulation": str|null,
    "protocol": str|null,
    "raw_data": str|null,
    "question": str|null,
    "answer": str|null,
    "country": str|null,
    "metadata": dict,
  }
"""
import json
import subprocess
import os
import sys
from pathlib import Path
import importlib.util

# Load config
spec = importlib.util.spec_from_file_location("config", Path(__file__).parent / "00_config.py")
config = importlib.util.module_from_spec(spec); spec.loader.exec_module(config)

OUT = config.RAW_INPUT / "raw_unified.jsonl"
LOG = config.LOGS / "01_ingest.log"

def log(msg):
    line = f"[01_ingest] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

records = []

# ---------- Source 1: GitHub repo ----------
def ingest_github():
    repo_dir = config.RAW_INPUT / "github_repo"
    if not repo_dir.exists():
        log(f"Cloning {config.SOURCES['github_repo']}")
        subprocess.run(["git", "clone", "--depth=1", config.SOURCES["github_repo"], str(repo_dir)], check=True)
    else:
        log("Repo already cloned, pulling latest")
        subprocess.run(["git", "-C", str(repo_dir), "pull", "--quiet"], check=False)

    # 1a. Enriched dataset (500 allocations)
    enriched = repo_dir / "merged_dataset" / "enriched_280_1100_mhz_ALL.json"
    if enriched.exists():
        for e in json.load(open(enriched)):
            freq_mid = ((e.get("freq_low_mhz", 0) + e.get("freq_high_mhz", 0)) / 2) * 1e6
            records.append({
                "source": "github:Flipper_Zero_RF_DataSet",
                "source_path": str(enriched.relative_to(repo_dir)),
                "category": "allocation",
                "freq_hz": freq_mid,
                "freq_low_hz": e.get("freq_low_mhz", 0) * 1e6,
                "freq_high_hz": e.get("freq_high_mhz", 0) * 1e6,
                "modulation": e.get("modulation"),
                "protocol": None,
                "raw_data": None,
                "question": None,
                "answer": None,
                "country": e.get("country_code"),
                "metadata": {
                    "service": e.get("service"),
                    "application": e.get("application"),
                    "typical_devices": e.get("typical_devices"),
                    "regulatory_ref": e.get("regulatory_ref"),
                    "notes": e.get("notes"),
                },
            })
        log(f"Loaded {len(records)} allocations from enriched dataset")

    # 1b. Q&A dataset (1500 pairs)
    qa = repo_dir / "qa_dataset" / "spectrum_qa_dataset.jsonl"
    if qa.exists():
        n = 0
        with open(qa) as f:
            for line in f:
                e = json.loads(line)
                freq_mid = ((e.get("freq_low_mhz", 0) + e.get("freq_high_mhz", 0)) / 2) * 1e6
                records.append({
                    "source": "github:Flipper_Zero_RF_DataSet",
                    "source_path": "qa_dataset/spectrum_qa_dataset.jsonl",
                    "category": "qa",
                    "freq_hz": freq_mid,
                    "freq_low_hz": e.get("freq_low_mhz", 0) * 1e6,
                    "freq_high_hz": e.get("freq_high_mhz", 0) * 1e6,
                    "modulation": None,
                    "protocol": None,
                    "raw_data": None,
                    "question": e.get("question"),
                    "answer": e.get("answer"),
                    "country": e.get("country_code"),
                    "metadata": {
                        "qa_id": e.get("id"),
                        "category": e.get("category"),
                        "source_primary": e.get("source_primary"),
                        "fact_check_status": e.get("fact_check_status"),
                    },
                })
                n += 1
        log(f"Loaded {n} Q&A pairs")

# ---------- Source 2: HuggingFace datasets ----------
def ingest_hf():
    if not config.SOURCES.get("hf_datasets"):
        log("No HF datasets configured, skipping")
        return
    try:
        from datasets import load_dataset
    except ImportError:
        log("datasets library not available, skipping HF")
        return

    for ds_name in config.SOURCES["hf_datasets"]:
        try:
            log(f"Loading HF dataset: {ds_name}")
            ds = load_dataset(ds_name, split="train", streaming=True)
            n = 0
            for row in ds:
                records.append({
                    "source": f"hf:{ds_name}",
                    "source_path": ds_name,
                    "category": "capture" if "raw" in row else "qa",
                    "freq_hz": row.get("frequency") or row.get("freq_hz"),
                    "modulation": row.get("modulation") or row.get("Modulation"),
                    "protocol": row.get("protocol") or row.get("Protocol"),
                    "raw_data": row.get("raw_data") or row.get("RAW_Data"),
                    "question": row.get("question"),
                    "answer": row.get("answer"),
                    "country": None,
                    "metadata": {k: v for k, v in row.items() if k not in {
                        "frequency","freq_hz","modulation","Modulation","protocol",
                        "Protocol","raw_data","RAW_Data","question","answer"}},
                })
                n += 1
                if n >= 10000: break  # safety cap
            log(f"Loaded {n} rows from {ds_name}")
        except Exception as e:
            log(f"Failed to load {ds_name}: {e}")

# ---------- Source 3: Local Flipper .sub files ----------
def parse_sub(path: Path) -> dict:
    """Parse Flipper Zero .sub file (Filetype/Frequency/Modulation/RAW_Data)."""
    out = {"freq_hz": None, "modulation": None, "protocol": None, "raw_data": None, "preset": None}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("Frequency:"):
                    out["freq_hz"] = float(line.split(":",1)[1].strip())
                elif line.startswith("Preset:"):
                    out["preset"] = line.split(":",1)[1].strip()
                    # Preset → modulation guess
                    p = out["preset"].lower()
                    if "ook" in p: out["modulation"] = "OOK"
                    elif "fsk" in p: out["modulation"] = "FSK"
                    elif "psk" in p: out["modulation"] = "PSK"
                    elif "ask" in p: out["modulation"] = "ASK"
                elif line.startswith("Protocol:"):
                    out["protocol"] = line.split(":",1)[1].strip()
                elif line.startswith("RAW_Data:"):
                    if out["raw_data"] is None: out["raw_data"] = ""
                    out["raw_data"] += " " + line.split(":",1)[1].strip()
    except Exception:
        return None
    return out

def ingest_local_sub():
    sub_dir = Path(config.SOURCES["local_sub_dir"])
    if not sub_dir.exists():
        log(f"No local .sub dir ({sub_dir}), skipping")
        return
    n = 0
    for p in sub_dir.rglob("*.sub"):
        parsed = parse_sub(p)
        if not parsed or parsed["freq_hz"] is None:
            continue
        records.append({
            "source": "local_sub",
            "source_path": str(p.relative_to(sub_dir)),
            "category": "capture",
            "freq_hz": parsed["freq_hz"],
            "modulation": parsed["modulation"],
            "protocol": parsed["protocol"],
            "raw_data": parsed["raw_data"],
            "question": None,
            "answer": None,
            "country": None,
            "metadata": {"preset": parsed["preset"], "filename": p.name},
        })
        n += 1
    log(f"Loaded {n} .sub captures")

# ---------- Run ingestion ----------
log("=" * 60)
log("Starting multi-source ingestion")
ingest_github()
ingest_hf()
ingest_local_sub()

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
log(f"Wrote {len(records)} records → {OUT}")
log(f"Size: {os.path.getsize(OUT):,} bytes")
