# Project Status

> Last updated: 2026-05-25

## Dataset Overview

| Metric | Value |
|--------|-------|
| Frequency range | 280 - 1100 MHz |
| Countries | FR, US, UK, CN, DE, RU, ES, IT, CH (9) |
| Total entries | 500 |
| Unique services/applications | 178 |
| Q&A training pairs | 1500 |
| Fact-check corrections applied | 16 |
| Sources consulted for verification | 11 regulatory bodies |

## Pipeline Phases

### Phase 1 -- Data Collection & Enrichment `DONE`

- [x] Baseline frequency tables (280-1100 MHz, 9 countries)
- [x] Fine-grained segment split (5 sub-bands: 280-400, 400-470, 470-700, 700-870, 870-1100)
- [x] Per-country allocations with real device examples
- [x] Modulation types, channel spacing, power limits
- [x] Regulatory references (ITU, FCC, ANFR, Ofcom, BNetzA, MIIT, CNAF, Roskomnadzor, BAKOM)
- [x] Merged dataset: `merged_dataset/enriched_280_1100_mhz_ALL.json` (500 entries)
- [x] CSV export: `merged_dataset/enriched_280_1100_mhz_ALL.csv`

### Phase 2 -- Fact-Checking `DONE`

- [x] 5 independent fact-check reports per sub-band
- [x] Consolidated report: `factcheck_reports/factcheck_CONSOLIDATED_280_1100_mhz.json`
- [x] 16 critical corrections applied (see below)
- [x] Cross-referenced against official regulatory databases

#### Key Corrections Applied

| # | Issue | Fix |
|---|-------|-----|
| 1 | 315 MHz TPMS listed for EU | EU uses 433.92 MHz, 315 MHz is US/JP only |
| 2 | TETRA listed for US/CN/RU | US=P25 (NTIA), CN=PDT 350-370, RU=limited |
| 3 | WMTS 608-614 listed for EU | US-only (FCC Part 95H) |
| 4 | LoRaWAN 868 listed for US/CN | US=902-928 MHz, CN=470-510 MHz |
| 5 | UK 700 MHz Vodafone | Corrected to O2/VMO2 (Ofcom 2021 auction) |
| 6 | FR 700 MHz Free/Bouygues swap | ARCEP Dec 2015: Free=2x5, Bouygues=2x10 |
| 7 | ECC Decision (14)02 cited | Corrected to (15)01 for 700 MHz duplex gap |
| 8 | Gazpar gas meters at 868 MHz | Corrected to 169 MHz VHF Wize (GRDF) |
| 9 | AEHF listed as UHF MILSATCOM | Corrected to MUOS (AEHF is EHF 44 GHz) |
| 10 | COSPAS-SARSAT at 399.9 MHz | Corrected to 406.0-406.1 MHz |
| 11 | BeiDou/GLONASS at 399.9 MHz | Both are L-band only, removed |
| 12 | DME Y-mode 30 us | Corrected to 36 us (ICAO Annex 10) |
| 13 | ITU 5.328A for ADS-B | Corrected to 5.328B |
| 14 | 863-870 labeled ISM | Corrected to SRD (ETSI EN 300 220) |
| 15 | CH listed as TETRA | CH uses TETRAPOL (Polycom network) |
| 16 | CN listed TETRA 380 MHz | CN uses PDT 350-370 MHz |

### Phase 3 -- Q&A Dataset Generation `DONE`

- [x] 1500 Q&A pairs generated
- [x] 3 categories: fonction, reglementation, appareils_utilisateurs
- [x] Source citations in every answer
- [x] Format: JSONL (HuggingFace-ready) + JSON
- [x] Output: `qa_dataset/spectrum_qa_dataset.jsonl`

### Phase 4 -- Validation Pipeline `READY (not yet run)`

8-step automated pipeline in `Data_Process/`:

| Step | Script | Status |
|------|--------|--------|
| 01 | Ingestion multi-sources | Code ready |
| 02 | Dedup (hash + semantic) | Code ready |
| 03 | RF validation (rules) | Code ready |
| 04 | Protocol DB matching | Code ready |
| 05 | LLM hallucination check (Ollama Qwen 32B) | Code ready |
| 06 | NLI fact verification (DeBERTa) | Code ready |
| 07 | Scoring (0-13 scale) | Code ready |
| 08 | Export (JSONL buckets) | Code ready |

**Target rig:** 6x RTX 3070 (48 GB VRAM), Ubuntu 24.04

**Pending:**
- [ ] Transfer scripts to rig
- [ ] Pull Ollama model `qwen2.5:32b-instruct-q4_K_M`
- [ ] Run full pipeline end-to-end
- [ ] Human audit of 'partial' bucket via `audit_dashboard.py`
- [ ] Merge audit decisions back into final dataset

### Phase 5 -- HuggingFace Publication `TODO`

- [ ] Upload verified.jsonl as HF dataset
- [ ] Dataset card with methodology
- [ ] License selection

## File Structure

```
Flipper_Zero_RF_DataSet/
  baseline/                      Original CSV frequency tables
  enriched_data/                 5 enriched JSON files per sub-band
  merged_dataset/                Merged 500-entry JSON + CSV
  qa_dataset/                    1500 Q&A pairs (JSONL + JSON)
  factcheck_reports/             5 sub-band reports + consolidated
  Data_Process/
    README.md                    Pipeline architecture docs
    scripts/
      00_config.py               Global config & backend dispatch
      01_ingest_sources.py       Multi-source ingestion
      02_dedup.py                Hash + semantic deduplication
      03_rf_validation.py        RF rules validation
      04_protocols_db.py         Protocol DB matching (rapidfuzz)
      05_llm_hallucination.py    LLM hallucination detection (Ollama)
      06_fact_verification.py    NLI fact-check (DeBERTa)
      07_scoring.py              Score aggregation & bucketing
      08_export.py               Final JSONL export + manifest
      audit_dashboard.py         Human audit CLI
      run_pipeline.sh            Pipeline orchestrator
  STATUS.md                      This file
  STANDARDS.md                   RF standards & regulatory references
  README.md                      Project overview
```
