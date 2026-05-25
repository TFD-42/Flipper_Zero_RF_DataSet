"""
Step 2 — Semantic deduplication using sentence-transformers.

Two-pass strategy:
  Pass 1: exact hash dedup (instant)
  Pass 2: semantic similarity > 0.95 → drop second occurrence

Input:  01_raw_input/raw_unified.jsonl
Output: 02_dedup/dedup.jsonl + dedup_report.json
"""
import json, hashlib, importlib.util
from pathlib import Path
import numpy as np

spec = importlib.util.spec_from_file_location("config", Path(__file__).parent / "00_config.py")
config = importlib.util.module_from_spec(spec); spec.loader.exec_module(config)

IN  = config.RAW_INPUT / "raw_unified.jsonl"
OUT = config.DEDUP / "dedup.jsonl"
REPORT = config.DEDUP / "dedup_report.json"
LOG = config.LOGS / "02_dedup.log"

def log(msg):
    line = f"[02_dedup] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

# Load
records = [json.loads(l) for l in open(IN)]
log(f"Loaded {len(records)} records")

# ---------- Pass 1: exact hash dedup ----------
def make_key(r):
    h = hashlib.md5()
    for k in ("freq_hz", "modulation", "protocol", "raw_data", "question", "answer", "country"):
        h.update(str(r.get(k, "")).encode())
    return h.hexdigest()

seen_hash = {}
exact_dupes = 0
deduped = []
for r in records:
    k = make_key(r)
    if k in seen_hash:
        exact_dupes += 1
        continue
    seen_hash[k] = True
    deduped.append(r)
log(f"Pass 1 (exact hash): removed {exact_dupes} duplicates → {len(deduped)} remain")

# ---------- Pass 2: semantic dedup (Q&A only, allocations are already unique per (freq,country)) ----------
qa_records  = [(i, r) for i, r in enumerate(deduped) if r.get("category") == "qa"]
other_records = [(i, r) for i, r in enumerate(deduped) if r.get("category") != "qa"]

semantic_dupes = 0
if qa_records:
    cfg = config.BACKENDS["deduplication"]
    log(f"Pass 2 (semantic): loading {cfg['model']} on {cfg['device']}")
    from sentence_transformers import SentenceTransformer
    import torch
    device = cfg["device"] if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(cfg["model"], device=device)

    texts = [(r.get("question","") or "") + " " + (r.get("answer","") or "") for _, r in qa_records]
    log(f"Encoding {len(texts)} Q&A pairs...")
    emb = model.encode(texts, batch_size=128, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)

    # Cluster: cosine sim > threshold → duplicate
    threshold = cfg["threshold"]
    keep_mask = np.ones(len(qa_records), dtype=bool)
    log(f"Computing pairwise similarity (threshold={threshold})...")
    # Chunk to avoid OOM: sim = emb @ emb.T but with batched comparison
    BATCH = 256
    for i in range(0, len(emb), BATCH):
        chunk = emb[i:i+BATCH]
        sims = chunk @ emb.T  # (BATCH, N)
        for li, gi in enumerate(range(i, min(i+BATCH, len(emb)))):
            if not keep_mask[gi]: continue
            # find indices > gi where sim > threshold
            close = np.where(sims[li, gi+1:] > threshold)[0]
            for c in close:
                if keep_mask[gi+1+c]:
                    keep_mask[gi+1+c] = False
                    semantic_dupes += 1

    final_qa = [qa_records[i][1] for i in range(len(qa_records)) if keep_mask[i]]
    log(f"Pass 2 (semantic): removed {semantic_dupes} near-duplicates")
else:
    final_qa = []

# Recombine, preserving original order
final = []
qa_keep_indices = {qa_records[i][0] for i in range(len(qa_records)) if i < len(qa_records) and (not qa_records or keep_mask[i] if qa_records else True)}
for i, r in enumerate(deduped):
    if r.get("category") == "qa":
        idx_in_qa = next((j for j,(orig_i,_) in enumerate(qa_records) if orig_i == i), None)
        if idx_in_qa is not None and keep_mask[idx_in_qa]:
            final.append(r)
    else:
        final.append(r)

with open(OUT, "w") as f:
    for r in final:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

report = {
    "input_count": len(records),
    "exact_duplicates_removed": exact_dupes,
    "semantic_duplicates_removed": semantic_dupes,
    "output_count": len(final),
    "reduction_pct": round(100 * (len(records) - len(final)) / max(len(records),1), 2),
}
json.dump(report, open(REPORT, "w"), indent=2)
log(f"Wrote {len(final)} records → {OUT}")
log(f"Report: {report}")
