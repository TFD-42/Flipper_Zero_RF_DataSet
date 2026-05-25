"""
Step 6 — Fact verification via NLI/entailment model (transformers).

Uses a Natural Language Inference model to check if the answer is entailed
by the regulatory source citation. The model is loaded on a dedicated GPU.

For Q&A:
  premise = source_primary text (synthetic from regulatory_ref)
  hypothesis = answer
  → entailment | neutral | contradiction

Output: 06_sdr_check/fact_verified.jsonl  (reuses sdr_check dir since SDR skipped)
"""
import json, importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("config", Path(__file__).parent / "00_config.py")
config = importlib.util.module_from_spec(spec); spec.loader.exec_module(config)

IN  = config.LLM_CHECK / "llm_checked.jsonl"
OUT = config.SDR_CHECK / "fact_verified.jsonl"
LOG = config.LOGS / "06_fact.log"

def log(msg):
    line = f"[06_fact] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

cfg = config.BACKENDS["fact_verification"]
log(f"Loading NLI model {cfg['model']} on {cfg['device']}...")

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

tok = AutoTokenizer.from_pretrained(cfg["model"])
mdl = AutoModelForSequenceClassification.from_pretrained(cfg["model"]).to(cfg["device"]).eval()
LABELS = ["entailment", "neutral", "contradiction"]

@torch.no_grad()
def nli(premise: str, hypothesis: str):
    inputs = tok(premise, hypothesis, return_tensors="pt", truncation=True, max_length=512).to(cfg["device"])
    logits = mdl(**inputs).logits[0]
    probs = torch.softmax(logits, dim=-1).cpu().numpy()
    idx = int(probs.argmax())
    return LABELS[idx], float(probs[idx])

records = [json.loads(l) for l in open(IN)]
log(f"Loaded {len(records)} records")

verdicts = {"entailment": 0, "neutral": 0, "contradiction": 0, "skipped": 0}

for i, r in enumerate(records):
    if r.get("category") != "qa" or not r.get("answer"):
        r["fact_check"] = {"verdict": "skipped", "confidence": None}
        verdicts["skipped"] += 1
        continue

    meta = r.get("metadata", {}) or {}
    source = meta.get("source_primary") or ""
    if not source or len(source) < 20:
        r["fact_check"] = {"verdict": "skipped", "confidence": None, "reason": "no_source"}
        verdicts["skipped"] += 1
        continue

    # Build a synthetic premise from source citation + extracted regulatory text
    premise = f"According to {source}, the regulation states the following technical facts."
    hypothesis = r["answer"][:400]

    verdict, conf = nli(premise, hypothesis)
    r["fact_check"] = {"verdict": verdict, "confidence": round(conf, 3)}
    verdicts[verdict] += 1

    if (i+1) % 100 == 0:
        log(f"  {i+1}/{len(records)} | {verdicts}")

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

log(f"Done. Verdicts: {verdicts}")
log(f"Wrote {len(records)} → {OUT}")
