# Flipper Zero RF DataSet — Sub-GHz Frequency Database for LLM Training

> **Open dataset & validation pipeline for Flipper Zero Sub-GHz RF research, LLM fine-tuning, and SDR ML projects.**

`#FlipperZero` `#FlipperZeroSubGHz` `#RFDataset` `#LLM` `#LLMTraining` `#FineTuning` `#SDR` `#RTL433` `#Sub-GHz` `#RFSecurity` `#OSINT` `#Spectrum` `#HuggingFace` `#OpenDataset`

A curated **Flipper Zero RF database** covering the 280–1100 MHz Sub-GHz spectrum across 9 countries, with fact-checked regulatory metadata, a 1500-pair Q&A corpus ready for **LLM fine-tuning** (Hugging Face JSONL), and a GPU-accelerated **validation pipeline** combining `sentence-transformers`, **Ollama (Qwen 32B)**, and `DeBERTa-v3` NLI fact-checking.

## Why this repo

- **Train an LLM on Flipper Zero / Sub-GHz RF knowledge** — clean Q&A pairs, every answer cites a regulatory source
- **Build a Flipper-aware copilot** — protocol matching against rtl_433 + Flipper SubGHz native protocols (26 supported)
- **SDR ML / spectrum research** — country-resolved frequency allocations with device examples, modulations, power limits
- **Reproducible quality pipeline** — every entry is scored (0–13) and bucketed (verified / partial / rejected)

## Quick Stats

| | |
|---|---|
| **Frequency range** | 280 – 1100 MHz (Sub-GHz / UHF) |
| **Countries** | FR · US · UK · CN · DE · RU · ES · IT · CH |
| **Entries** | 500 (178 unique services) |
| **Q&A pairs for LLM fine-tuning** | 1500 (JSONL, Hugging Face–ready) |
| **Fact-check corrections applied** | 16 critical fixes |
| **Validation pipeline** | 8-step, GPU-accelerated |
| **Models in the loop** | Qwen 2.5 32B (Ollama, 6× RTX 3070), DeBERTa-v3 NLI, BGE-large, MiniLM |

## Structure

```
enriched_data/           5 JSON files per Sub-GHz sub-band (280-400, 400-470, 470-700, 700-870, 870-1100)
merged_dataset/          Merged 500-entry JSON + CSV (full Sub-GHz spectrum)
qa_dataset/              1500 Q&A pairs (JSONL + JSON) — LLM fine-tuning ready
factcheck_reports/       5 sub-band fact-check reports + consolidated audit
baseline/                Original ITU / CEPT / FCC baseline CSVs
Data_Process/            Automated validation pipeline (8 GPU-accelerated steps)
  scripts/               Pipeline scripts (Python + Bash)
  README.md              Pipeline architecture & usage
STANDARDS.md             RF standards reference (ITU, FCC, CEPT, ETSI, ICAO, +9 regulators)
STATUS.md                Project progress & correction log
```

## Data Fields

Each entry includes:
- Frequency range (low / high MHz), country code, ITU region
- Service name, application description, allocation status
- **Flipper Zero / rtl_433 protocol matches** where applicable
- Real device examples, modulation type, channel spacing
- Power limits, regulatory references (specific article/decision numbers)
- Correction notes where fact-check found errors
- `verified` flag + quality score

## Validation Pipeline (LLM-in-the-loop)

Located in `Data_Process/` — an 8-step automated pipeline designed for multi-GPU rigs:

1. **Ingestion** — GitHub + Hugging Face datasets + Flipper `.sub` files
2. **Dedup** — MD5 hash + semantic similarity (`sentence-transformers/all-MiniLM-L6-v2`)
3. **RF Validation** — Frequency ranges, modulations, pulse timings, country codes
4. **Protocol Matching** — `rtl_433` + Flipper SubGHz protocol DB (rapidfuzz)
5. **LLM Hallucination Check** — **Ollama Qwen 2.5 32B**, sharded across 6× RTX 3070
6. **Fact Verification** — NLI entailment with `DeBERTa-v3-large-mnli-fever-anli`
7. **Scoring** — 0–13 composite, bucketed verified / partial / rejected
8. **Export** — JSONL splits + audit sample + manifest (Hugging Face–ready)

See `Data_Process/README.md` for full architecture.

## Use Cases

- **Fine-tune an LLM** on Flipper Zero / Sub-GHz RF knowledge (Llama, Mistral, Qwen, Phi)
- **Build a Flipper Zero assistant** that knows allocations per country
- **RAG over regulatory data** for SDR / amateur radio / pentest tooling
- **Protocol identification** training data for rtl_433 / Universal Radio Hacker
- **Compliance research** — what's legal where, with citations
- **OSINT** — device fingerprinting by frequency + modulation

## References

Full list of standards in [STANDARDS.md](STANDARDS.md).

Key sources: ITU Radio Regulations (Art. 5), FCC 47 CFR 2.106, CEPT ERC/REC 70-03, ETSI EN 300 220, ICAO Annex 10, 3GPP band specs, plus 9 national regulators (ANFR, FCC/NTIA, Ofcom, MIIT, BNetzA, Roskomnadzor, CNAF/SETSI, AGCOM/MIMIT, BAKOM).

## Status

See [STATUS.md](STATUS.md) for detailed progress tracking. Current: collection / enrichment / fact-check / Q&A generation complete. Pipeline code ready, pending execution on GPU rig.

## Related Projects & Tags

**Topics:** `flipper-zero` `flipper-zero-subghz` `rf` `sub-ghz` `rf-dataset` `llm-dataset` `llm-fine-tuning` `huggingface` `sdr` `rtl-433` `rf-security` `osint` `radio-frequency` `spectrum` `qa-dataset` `dataset` `lora` `lorawan` `tetra` `ads-b` `ism-band` `srd-band`

## License

Dataset compiled from public regulatory sources. Pipeline code provided as-is.
