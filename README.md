# Flipper Zero RF DataSet — Sub-GHz Frequency Database for LLM Training

> **Open dataset & validation pipeline for Flipper Zero Sub-GHz RF research, LLM fine-tuning, and SDR ML projects.**

`#FlipperZero` `#FlipperZeroSubGHz` `#RFDataset` `#LLM` `#LLMTraining` `#FineTuning` `#SDR` `#RTL433` `#Sub-GHz` `#RFSecurity` `#OSINT` `#Spectrum` `#HuggingFace` `#OpenDataset`

A curated **Flipper Zero RF database** covering the 280–1100 MHz Sub-GHz spectrum across 9 countries, with fact-checked regulatory metadata, a Q&A corpus for **LLM fine-tuning** (Hugging Face JSONL), and a GPU-accelerated **validation pipeline** combining `sentence-transformers`, **Qwen 32B (transformers + device_map="auto", 6× GPU sharded)**, **vLLM tensor-parallel**, and `DeBERTa-v3` NLI fact-checking.

---

## ⚠️ Status: PRE-PRODUCTION — actively fact-checked, file by file

This dataset is the **seed baseline**. I'm currently going through **every file, one by one**, manually fact-checking each entry and enriching it with finer-grained sub-bands, per-country variants, real device examples, and protocol cross-references.

**Roadmap target:**

| Metric | Current (seed) | Target (production) | Multiplier |
|---|---|---|---|
| Allocation entries | 500 | **~105 000** | **×210** |
| Q&A pairs | 1 500 | **~315 000** | ×210 |
| Fact-check coverage | manual per-file (in progress) | 100 % cross-checked vs ≥3 independent sources | — |
| Confidence scoring | binary (verified / not) | continuous 0-100 % with triangulation | — |

The ×210 target comes from decomposing each current "broad" allocation into its finest legally-defined sub-segments × 9 countries × multiple use-cases per band. Each entry is cross-checked against official regulators (ITU, FCC, ANFR, Ofcom, BNetzA, MIIT, etc.), community sources (rtl_433, Flipper SubGHz, RTL-SDR forums), and Wikipedia.

**End goal: an optimally fact-checked, structured RF database — as exhaustive as I can possibly verify.**

See [STATUS.md](STATUS.md) for live progress, the per-file checklist, and the fact-check log.

---

## 🤝 Contributions welcome

**All help is welcome — especially for fact-checking, corrections, and adding country-specific knowledge.**

### How you can help

- 🔎 **Fact-check entries** — spot an allocation that's wrong for your country? Open an issue or PR with the regulator reference
- 📡 **Add device examples** — know which devices actually transmit on a band in your region? Add them with model numbers
- 📜 **Add regulatory references** — link a specific FCC Part / ECC Decision / national gazette to an entry
- 🌍 **Add countries** — currently 9 covered; expansions welcome (JP, KR, BR, IN, AU, CA, …)
- 🦠 **Report errors** — anything that contradicts the relevant ITU footnote, national table, or community knowledge
- 🔧 **Improve the pipeline** — new sources, better confidence weighting, additional cross-check backends
- 📚 **Suggest HF datasets to cross-reference** in `Data_Process/scripts/00_config.py` (`CROSS_CHECK_SOURCES.hf_datasets`)

### Contribution flow

1. **Issues** for discussion (typos, factual errors, missing references, suggestions)
2. **Pull Requests** for changes — please include the source you fact-checked against (URL or doc reference)
3. **For data corrections**: edit the JSON in `enriched_data/`, add a `correction_note` field referencing the source
4. **For pipeline changes**: PRs against `Data_Process/scripts/` — keep cross-check sources public / API-free where possible
5. Even **single-entry corrections are valuable** — one verified line is one less hallucination in someone's LLM

No CLA, no contributor agreement — public regulatory data, open contribution. Credit goes in commit history.

---

## Why this repo

- **Train an LLM on Flipper Zero / Sub-GHz RF knowledge** — every Q&A cites its regulatory source
- **Build a Flipper-aware copilot** — protocol matching against rtl_433 + native Flipper SubGHz protocols
- **SDR ML / spectrum research** — country-resolved frequency allocations with device examples, modulations, power limits
- **Reproducible quality pipeline** — every entry gets a quality score **and** a multi-source confidence percentage

## Quick Stats (current seed)

| | |
|---|---|
| **Frequency range** | 280 – 1100 MHz (Sub-GHz / UHF) |
| **Countries** | FR · US · UK · CN · DE · RU · ES · IT · CH |
| **Entries (seed)** | 500 → target **~105 000** |
| **Q&A pairs (seed)** | 1 500 → target **~315 000** |
| **Fact-check corrections applied so far** | 16 critical fixes (see STATUS.md) |
| **Validation pipeline** | 8 GPU-accelerated steps |
| **Models in the loop** | Qwen 2.5 32B (transformers device_map=auto, 6× RTX 3070), Qwen 2.5 7B (vLLM tensor-parallel), DeBERTa-v3 NLI, BGE-large, MiniLM |

## Structure

```
enriched_data/    5 JSON files per Sub-GHz sub-band (280-400, 400-470, 470-700, 700-870, 870-1100)
merged_dataset/   Merged 500-entry JSON + CSV (full Sub-GHz spectrum)
qa_dataset/       1500 Q&A pairs (JSONL + JSON) — LLM fine-tuning ready
factcheck_reports/ 5 sub-band fact-check reports + consolidated audit
baseline/         Original ITU / CEPT / FCC baseline CSVs
Data_Process/     Automated validation pipeline (8 GPU-accelerated steps)
  scripts/        Pipeline scripts (Python + Bash)
  README.md       Pipeline architecture & usage
STANDARDS.md      RF standards reference (ITU, FCC, CEPT, ETSI, ICAO, +9 regulators)
STATUS.md         Project progress, per-file fact-check log, roadmap
```

## Data Fields

Each entry includes:
- Frequency range (low / high MHz), country code, ITU region
- Service name, application description, allocation status
- **Flipper Zero / rtl_433 protocol matches** where applicable
- Real device examples, modulation type, channel spacing
- Power limits, regulatory references (specific article/decision numbers)
- Correction notes where fact-check found errors
- `verified` flag + quality score (0-13) + **confidence_pct (0-100)**

## Validation Pipeline (LLM-in-the-loop)

Located in `Data_Process/` — an 8-step automated pipeline for multi-GPU rigs:

1. **Ingestion** — GitHub + Hugging Face datasets + Flipper `.sub` files
2. **Dedup** — MD5 hash + semantic similarity (`sentence-transformers/all-MiniLM-L6-v2`)
3. **RF Validation + Multi-source Cross-check** — freq/mod/timing rules **plus** triangulation across HF datasets, Wikipedia API, web search (FCC/ITU/ANFR + RTL-SDR/Flipper forums) → produces **confidence_pct (0-100)** per record
4. **Protocol Matching** — `rtl_433` + Flipper SubGHz protocol DB (rapidfuzz)
5. **LLM Hallucination Check** — **Qwen 2.5 32B** sharded across **6× RTX 3070** via `transformers` + `accelerate device_map="auto"` (native multi-GPU, no Ollama)
6. **Fact Verification** — NLI entailment with `DeBERTa-v3-large-mnli-fever-anli`
7. **Scoring** — 0–13 composite (internal quality), bucketed verified / partial / rejected
8. **Export** — JSONL splits + audit sample + manifest with **dual scoring** (0-13 internal + 0-100 % external confidence)

Optional **web compare LLM**: vLLM tensor-parallel running Qwen 2.5 7B on 6 GPUs for fast snippet extraction during cross-check.

See [`Data_Process/README.md`](Data_Process/README.md) for full architecture.

## Dual Scoring System

Each record gets **two independent scores**:

| Score | Range | Source | Meaning |
|---|---|---|---|
| **Quality score** | 0-13 | internal rules + LLM + NLI | Does the entry pass our checks? |
| **Confidence %** | 0-100 % | external multi-source triangulation | How many independent sources agree? |

Confidence weights: official regulator (0.35), HF dataset (0.25), trusted standard (0.20), Wikipedia (0.20), forum/community (0.10). Bonuses for triangulation 3+, penalties for contradiction / missing sources / country mismatch.

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

See [STATUS.md](STATUS.md) for the live per-file fact-check log and the path from the current 500-entry seed to the **×210 production target**.

## Topics

`flipper-zero` `flipper-zero-subghz` `flipperzero` `subghz` `sub-ghz` `rf` `rf-dataset` `radio-frequency` `llm` `llm-dataset` `llm-training` `llm-fine-tuning` `fine-tuning` `huggingface` `dataset` `qa-dataset` `sdr` `rtl-433` `rtl433` `ollama`

## License

Dataset compiled from public regulatory sources. Pipeline code provided as-is.
