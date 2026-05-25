# DataSet_Process — RF Dataset Quality Pipeline

Pipeline semi-automatique pour transformer un dataset RF brut multi-sources en dataset propre, vérifié et **scoré en confiance**.

## Architecture

```
01_raw_input    →  Ingestion multi-sources (GitHub + HF + .sub Flipper)
02_dedup        →  Hash + sentence-transformers semantic dedup
03_validation   →  Règles RF + cross-check multi-sources (HF/Wikipedia/Web/forums) + confidence %
04_protocols_db →  Match contre DB rtl_433 + Flipper SubGHz + standards
05_llm_check    →  transformers + device_map="auto" (Qwen 32B sharded sur 6 GPU)
06_sdr_check    →  NLI/entailment transformers DeBERTa (fact-check)
07_scoring      →  Score 0-13 → bucket {verified, partial, rejected}
08_output       →  JSONL HF-ready + audit sample + manifest (avec confidence_pct)
```

## Backend dispatch

| Étape | Backend | Engine | Pourquoi |
|-------|---------|--------|----------|
| Dedup sémantique | sentence-transformers | cuda:0 | Léger, rapide (80 MB) |
| Validation RF (rules) | regex | CPU | Instantané |
| **Cross-check sources** | HF datasets + Wikipedia API + WebSearch (Brave/Serper/DDG) | net | Triangulation |
| Match protocole | rapidfuzz | CPU | Pas de modèle nécessaire |
| **Hallucination check** | **transformers + device_map="auto"** (Qwen 2.5 32B) | **6× RTX 3070 sharded** | **Multi-GPU natif via accelerate** |
| Web compare (optionnel) | vLLM tensor-parallel | 6× RTX 3070 | Serveur OpenAI-compatible |
| Fact-check (NLI) | transformers DeBERTa-v3 | cuda:1 | Entailment précis |
| Embeddings | BAAI/bge-large | cuda:2 | Recherche sémantique |

## Confidence scoring (Step 03)

**Indépendant du score 0-13 de l'étape 07.** Sortie par record :

```json
{
  "cross_check": {
    "confidence":     0.78,
    "confidence_pct": 78,
    "bucket":         "high_confidence",
    "matched_sources": 3,
    "official_sources": 1,
    "forum_sources":   1,
    "rationale": [
      "+0.32 (official_regulator, conf=0.90, evidence=...)",
      "+0.14 (wikipedia_match, conf=0.70, evidence=...)",
      "+0.05 (forum_community, conf=0.50, evidence=...)",
      "+0.15 triangulation_3plus",
      "+0.05 official_plus_forum"
    ],
    "sources": [ {...}, {...}, {...} ]
  }
}
```

### Logique de confidence

- **Poids par source** : official (0.35), HF dataset (0.25), trusted standard (0.20), Wikipedia (0.20), forum (0.10)
- **Pénalités** : contradiction (-0.30), no_source_found (-0.40), single_source_only (-0.15), country_mismatch (-0.20), stale_data (-0.10)
- **Bonus** : triangulation 3+ sources (+0.15), official + forum (+0.05)
- **Buckets** : ≥75 % high, 50-74 % medium, 25-49 % low, <25 % no_confidence

## Lancement

```bash
cd Data_Process/scripts
bash run_pipeline.sh
```

### Mode complet (avec cross-check réseau)

```bash
export CROSS_CHECK=1
# optionnel pour search rapide :
export BRAVE_API_KEY=...   # ou SERPER_API_KEY=...
# (sinon fallback DuckDuckGo HTML)
bash run_pipeline.sh
```

### Override du chemin de base

```bash
export DATASET_PROCESS_BASE=/your/custom/path
bash run_pipeline.sh
```

### Debug du cross-check sur N records seulement

```bash
export CROSS_CHECK=1
export CROSS_CHECK_LIMIT=20
python3 03_rf_validation.py
```

## Suivi en temps réel

```bash
tail -f ${DATASET_PROCESS_BASE:-/home/xwiss/Desktop/DataSet_Process}/logs/*.log

# GPU usage (toutes les 2s)
watch -n 2 'nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader'

# Progression
watch -n 5 'for d in 01_raw_input 02_dedup 03_validation 04_protocols_db 05_llm_check 06_sdr_check 07_scoring 08_output; do printf "%-22s " "$d"; ls "'$DATASET_PROCESS_BASE'/$d/" 2>/dev/null | wc -l; done'
```

## Audit humain

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
  manifest.json        (stats globales + confidence_pct_avg + bucket distribution)
  audit_decisions.jsonl (accept/reject/edit du dashboard)
```

Chaque entrée JSONL contient désormais :
- `score` / `score_breakdown` / `bucket` (logique 0-13)
- `confidence_pct` / `confidence_bucket` (logique 0-100 multi-sources)
- `cross_check.sources` : détail des 3+ sources consultées avec URL et evidence

## Resume / Re-run

Chaque étape lit l'output de la précédente. Tu peux re-run une seule étape :

```bash
python3 05_llm_hallucination.py   # ne re-fait que le LLM check
```

## Dépendances

```bash
pip install --user \
  sentence-transformers \
  transformers \
  accelerate \
  torch \
  rapidfuzz \
  datasets \
  duckdb

# vLLM (optionnel, pour web_compare_llm endpoint)
pip install --user vllm
```
