# DataSet_Process — RF Dataset Quality Pipeline

Pipeline semi-automatique pour transformer un dataset RF brut multi-sources en dataset propre & vérifié.

## Architecture

```
01_raw_input        →  Ingestion multi-sources (GitHub + HF + .sub Flipper)
02_dedup            →  Hash + sentence-transformers semantic dedup
03_validation       →  Règles RF (freq range, modulation, timings, country)
04_protocols_db     →  Match contre DB rtl_433 + Flipper SubGHz + standards
05_llm_check        →  Ollama multi-GPU verdict (VALID/SUSPICIOUS/FALSE)
06_sdr_check        →  NLI/entailment transformers (fact-check)
07_scoring          →  Score 0-13 → bucket {verified, partial, rejected}
08_output           →  JSONL HF-ready + audit sample + manifest
```

## Backend dispatch (selon le check)

| Étape | Backend | GPU | Pourquoi |
|-------|---------|-----|----------|
| Dedup sémantique | sentence-transformers | cuda:0 | Léger, rapide |
| Validation RF | regex/rules | CPU | Instantané |
| Match protocole | rapidfuzz | CPU | Pas besoin de modèle |
| Hallucination | Ollama (Qwen 32B) | 6× RTX 3070 | Reasoning |
| Fact-check (NLI) | transformers DeBERTa | cuda:1 | Entailment précis |
| Embeddings | BAAI/bge-large | cuda:2 | Recherche sémantique |

## Lancement

```bash
cd Data_Process/scripts
bash run_pipeline.sh
```

Override du chemin de base (optionnel) :
```bash
export DATASET_PROCESS_BASE=/your/custom/path
bash run_pipeline.sh
```

Suivi en temps réel :
```bash
tail -f ${DATASET_PROCESS_BASE:-/home/xwiss/Desktop/DataSet_Process}/logs/*.log
```

## Audit humain

Après le pipeline, audit du bucket 'partial' :
```bash
python3 audit_dashboard.py
```

## Sortie finale

```
08_output/
  verified.jsonl       (score ≥ 8 — training grade)
  partial.jsonl        (5-7 — à auditer)
  rejected.jsonl       (< 5 — gardé pour traçabilité)
  audit_sample.jsonl   (50 entrées tirées au sort de 'partial')
  manifest.json        (stats globales)
  audit_decisions.jsonl (accept/reject/edit du dashboard)
```

## Resume / Re-run

Chaque étape lit l'output de la précédente et écrit son own output. Tu peux re-run une seule étape :
```bash
python3 05_llm_hallucination.py   # ne re-fait que le LLM check
```
