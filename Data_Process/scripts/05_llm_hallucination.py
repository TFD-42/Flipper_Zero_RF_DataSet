"""
Step 5 — LLM-based hallucination detection.

Backend: transformers + accelerate device_map="auto"
  → automatic tensor sharding across all visible GPUs (6× RTX 3070 here)
  → no external server needed (Ollama, vLLM)

Each Q&A is scored: VALID / SUSPICIOUS / FALSE
For allocations: the LLM verifies that (freq, country, service, application) is plausible.

Output: 05_llm_check/llm_checked.jsonl
"""
import json, importlib.util, time, os, gc
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

# All 6 GPUs visible to torch
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0,1,2,3,4,5")

cfg = config.BACKENDS["hallucination_detection"]
MODEL_NAME = cfg["model"]

LLM_READY = False
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    log(f"torch={torch.__version__} | CUDA available={torch.cuda.is_available()} | n_gpu={torch.cuda.device_count()}")
except ImportError as e:
    log(f"transformers/torch missing: {e}")
    raise

log(f"Loading {MODEL_NAME} with device_map='auto' across {torch.cuda.device_count()} GPUs...")
t_load = time.time()

try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    dtype = torch.bfloat16 if cfg.get("dtype") == "bfloat16" else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        device_map=cfg["device_map"],
        torch_dtype=dtype,
        max_memory=cfg.get("max_memory"),
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    model.eval()
    LLM_READY = True
    log(f"Model loaded in {time.time()-t_load:.1f}s")
    # Show GPU memory distribution
    for i in range(torch.cuda.device_count()):
        mem_gb = torch.cuda.memory_allocated(i) / 1e9
        log(f"  GPU {i}: {mem_gb:.2f} GB allocated")
except Exception as e:
    log(f"Could not load model: {e}. Skipping LLM verification.")
    LLM_READY = False

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

@torch.inference_mode() if LLM_READY else (lambda f: f)
def llm_verdict(prompt: str) -> str:
    if not LLM_READY:
        return "SKIPPED"
    try:
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        out = model.generate(
            **inputs,
            max_new_tokens=cfg.get("max_new_tokens", 8),
            do_sample=False,
            temperature=cfg.get("temperature", 0.0),
            pad_token_id=tokenizer.eos_token_id,
        )
        gen = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip().upper()
        for tok in ("VALID", "SUSPICIOUS", "FALSE"):
            if tok in gen:
                return tok
        return "SUSPICIOUS"
    except Exception as e:
        log(f"LLM error: {e}")
        return "ERROR"

records = [json.loads(l) for l in open(IN)]
log(f"Loaded {len(records)} records for LLM verification")
log(f"Backend: transformers device_map=auto / model={MODEL_NAME}")

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

# Cleanup
if LLM_READY:
    del model
    gc.collect()
    if 'torch' in dir() and torch.cuda.is_available():
        torch.cuda.empty_cache()
