# Flipper Zero RF DataSet

RF frequency allocation dataset (280-1100 MHz) across 9 countries, with enriched metadata, fact-checked entries, Q&A training pairs, and an automated validation pipeline.

## Quick Stats

| | |
|---|---|
| **Frequency range** | 280 - 1100 MHz |
| **Countries** | FR, US, UK, CN, DE, RU, ES, IT, CH |
| **Entries** | 500 (178 unique services) |
| **Q&A pairs** | 1500 (JSONL, HuggingFace-ready) |
| **Corrections** | 16 critical fixes after fact-check |
| **Pipeline** | 8-step automated (GPU-accelerated) |

## Structure

```
enriched_data/           5 JSON files per sub-band (280-400, 400-470, 470-700, 700-870, 870-1100)
merged_dataset/          Merged 500-entry JSON + CSV
qa_dataset/              1500 Q&A pairs (JSONL + JSON) for fine-tuning
factcheck_reports/       5 sub-band reports + consolidated fact-check
baseline/                Original ITU/CEPT/FCC baseline CSVs
Data_Process/            Automated validation pipeline (8 steps)
  scripts/               Pipeline scripts (Python + Bash)
  README.md              Pipeline architecture & usage
```

## Data Fields

Each entry includes:
- Frequency range (low/high MHz), country code, ITU region
- Service name, application description, allocation status
- Real device examples, modulation type, channel spacing
- Power limits, regulatory references (with specific article/decision numbers)
- Correction notes where fact-check found errors
- Verified flag

## Validation Pipeline

Located in `Data_Process/` -- an 8-step automated pipeline designed for multi-GPU rigs:

1. **Ingestion** -- GitHub + HuggingFace + Flipper .sub files
2. **Dedup** -- MD5 hash + semantic similarity (sentence-transformers)
3. **RF Validation** -- Frequency ranges, modulations, timings, country codes
4. **Protocol Matching** -- rtl_433 + Flipper SubGHz DB (rapidfuzz)
5. **LLM Check** -- Hallucination detection (Ollama Qwen 32B, 6-GPU)
6. **Fact Verification** -- NLI entailment (DeBERTa-v3-large)
7. **Scoring** -- 0-13 composite score, bucketing (verified/partial/rejected)
8. **Export** -- JSONL splits + audit sample + manifest

See `Data_Process/README.md` for full details.

## References

Full list of standards and regulatory sources in [STANDARDS.md](STANDARDS.md).

Key sources: ITU Radio Regulations (Art. 5), FCC 47 CFR 2.106, CEPT ERC/REC 70-03, ETSI EN 300 220, ICAO Annex 10, 3GPP band specs, and 9 national regulatory agencies.

## Status

See [STATUS.md](STATUS.md) for detailed progress tracking.

Current: data collection, enrichment, fact-check, and Q&A generation complete. Validation pipeline code ready, pending execution on GPU rig.

## License

Dataset compiled from public regulatory sources. Pipeline code is provided as-is.
