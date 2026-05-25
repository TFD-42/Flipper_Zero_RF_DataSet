"""
Step 5 — LLM-based hallucination detection.

Backend dispatch:
  - Ollama (multi-GPU sharding) for the heavy verifier model
  - transformers (NLI/entailment) for fact-checking when applicable

Each Q&A is scored by the LLM with one of: VALID / SUSPICIOUS / FALSE
For allocations: the LLM verifies that the (freq, country, service, application) tuple is plausible.

Output: 05_llm_check/llm_checked.jsonl
"""
import json, importlib.util, time, os
from pathlib import Path

spec = importlib.util.spec_from_file_location("config", Path(__file__).parent / "00_config.py")
config = importlib.util.module_from_spec(spec); spec.loader.exec_module(config)

IN  = config.PROTOCOLS_DB / "matched.jsonl"
OUT = config.LLM_CHECK / "llm_checked.jsonl"
LOG = config.LOGS / "05_llm.log"

def log(msg):
    line = f"[05_llm] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

# Configure Ollama multi-GPU
os.environ.setdefault("OLLAMA_NUM_PARALLEL", "6")
os.environ.setdefault("OLLAMA_MAX_LOADED_MODELS", "2")
os.environ.setdefault("OLLAMA_KEEP_ALIVE", "30m")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0,1,2,3,4,5")

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    log("ollama python lib not available — install with `pip install ollama`")

cfg = config.BACKENDS["hallucination_detection"]
MODEL = cfg["models"][0]

# Ensure model is pulled
if OLLAMA_AVAILABLE:
    try:
        installed = [m["name"] for m in ollama.list()["models"]]
        if not any(MODEL.split(":")[0] in m for m in installed):
            log(f"Pulling model {MODEL}...")
            ollama.pull(MODEL)
            log(f"Model {MODEL} ready")
    except Exception as e:
        log(f"Could not connect to Ollama: {e}. Falling back to skip.")
        OLLAMA_AVAILABLE = False

PROMPT_QA = """You are an RF/radio regulation expert. Evaluate if the following Q&A is technically valid.

Question: {q}

Answer: {a}

Source primary: {src}

Reply ONLY with one of three tokens, nothing else:
VALID       — the answer is technically correct and well-supported.
SUSPICIOUS  — partially correct or contains uncertain details.
FALSE       — contains factual errors, hallucinations, or invented information.
"""

PROMPT_ALLOC = """You are an RF/radio spectrum expert. Evaluate if this frequency allocation entry is technically plausible.

Frequency: {freq:.3f} MHz
Country: {country}
Service: {service}
Application: {app}
Devices cited: {dev}

Reply ONLY with one of three tokens, nothing else:
VALID       — the allocation matches reality (right country, right band, right service).
SUSPICIOUS  — band is plausible but some detail is questionable.
FALSE       — wrong country/band/service combination, or invented devices.
"""

def llm_verdict(prompt: str) -> str:
    if not OLLAMA_AVAILABLE:
        return "SKIPPED"
    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": cfg["temperature"],
                "num_gpu": cfg["num_gpu"],
                "num_predict": 8,  # we only need one token
            },
        )
        out = resp["message"]["content"].strip().upper()
        for tok in ("VALID", "SUSPICIOUS", "FALSE"):
            if tok in out:
                return tok
        return "SUSPICIOUS"
    except Exception as e:
        log(f"LLM error: {e}")
        return "ERROR"

records = [json.loads(l) for l in open(IN)]
log(f"Loaded {len(records)} records for LLM verification")
log(f"Backend: Ollama / model={MODEL} / 6× RTX 3070")

verdicts = {"VALID": 0, "SUSPICIOUS": 0, "FALSE": 0, "SKIPPED": 0, "ERROR": 0}
t0 = time.time()

for i, r in enumerate(records):
    if r.get("category") == "qa":
        prompt = PROMPT_QA.format(
            q=r.get("question","")[:500],
            a=r.get("answer","")[:1500],
            src=(r.get("metadata",{}) or {}).get("source_primary","unknown"),
        )
    elif r.get("category") == "allocation":
        meta = r.get("metadata", {}) or {}
        prompt = PROMPT_ALLOC.format(
            freq=(r.get("freq_hz") or 0) / 1e6,
            country=r.get("country","?"),
            service=meta.get("service","?"),
            app=(meta.get("application") or "")[:300],
            dev=(meta.get("typical_devices") or "")[:300],
        )
    else:
        r["llm_verdict"] = "SKIPPED"
        verdicts["SKIPPED"] += 1
        continue

    v = llm_verdict(prompt)
    r["llm_verdict"] = v
    verdicts[v] = verdicts.get(v, 0) + 1

    if (i+1) % 25 == 0:
        elapsed = time.time() - t0
        eta = elapsed / (i+1) * (len(records) - i - 1)
        log(f"  {i+1}/{len(records)} | elapsed {elapsed:.0f}s | ETA {eta:.0f}s | {verdicts}")

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

log(f"Done. Final verdicts: {verdicts}")
log(f"Total time: {time.time()-t0:.0f}s")
log(f"Wrote {len(records)} → {OUT}")
