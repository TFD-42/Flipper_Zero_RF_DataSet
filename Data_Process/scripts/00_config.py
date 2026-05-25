"""
DataSet_Process pipeline — Global config & backend dispatch.

Multi-backend strategy:
- transformers + torch : HuggingFace native models, embeddings, classification
- ollama (6-GPU sharding) : large GGUF models for hallucination detection
- sentence-transformers : semantic deduplication (lightweight)
- regex/rules : fast validation (no model)
"""
from pathlib import Path
import os

# Base paths — override with DATASET_PROCESS_BASE env var if needed
BASE = Path(os.environ.get("DATASET_PROCESS_BASE", "/home/xwiss/Desktop/DataSet_Process"))
RAW_INPUT      = BASE / "01_raw_input"
DEDUP          = BASE / "02_dedup"
VALIDATION     = BASE / "03_validation"
PROTOCOLS_DB   = BASE / "04_protocols_db"
LLM_CHECK      = BASE / "05_llm_check"
SDR_CHECK      = BASE / "06_sdr_check"
SCORING        = BASE / "07_scoring"
OUTPUT         = BASE / "08_output"
LOGS           = BASE / "logs"

for d in (RAW_INPUT, DEDUP, VALIDATION, PROTOCOLS_DB, LLM_CHECK, SDR_CHECK, SCORING, OUTPUT, LOGS):
    d.mkdir(parents=True, exist_ok=True)

# Backend dispatch table — chaque check choisit son backend optimal
BACKENDS = {
    "deduplication": {
        "engine": "sentence-transformers",
        "model": "sentence-transformers/all-MiniLM-L6-v2",  # 80 MB, rapide
        "device": "cuda:0",
        "threshold": 0.95,
    },
    "rf_validation": {
        "engine": "rules",  # regex + range checks, pas de modèle
    },
    "protocol_matching": {
        "engine": "rules+fuzzy",
        "fuzzy_threshold": 88,
    },
    "hallucination_detection": {
        "engine": "ollama",
        "models": [
            # Sharding multi-GPU via Ollama OLLAMA_NUM_GPU + OLLAMA_GPU_OVERHEAD
            "qwen2.5:32b-instruct-q4_K_M",  # principal
            "mistral-small:24b-instruct",   # fallback
        ],
        "gpu_layers": -1,        # all on GPU
        "num_gpu": 6,            # split sur 6× RTX 3070
        "temperature": 0.0,      # déterministe
    },
    "fact_verification": {
        "engine": "transformers",
        "model": "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",  # NLI / entailment
        "device": "cuda:1",
    },
    "embedding_similarity": {
        "engine": "transformers",
        "model": "BAAI/bge-large-en-v1.5",
        "device": "cuda:2",
    },
}

# Scoring weights
SCORING_WEIGHTS = {
    "frequency_valid":      2,
    "protocol_known":       2,
    "timings_coherent":     2,
    "sdr_match":            3,   # 0 si SDR check skip
    "not_hallucinated":     1,
    "fact_check_passed":    2,
    "no_duplicate":         1,
}

SCORING_THRESHOLDS = {
    "verified":   8,
    "partial":    5,
    "rejected":   0,
}

# Known protocols (sera enrichi par 04_protocols_db)
KNOWN_RF_BANDS = [
    (300e6,   348e6),    # UHF low
    (387e6,   464e6),    # PMR / 433
    (433.05e6, 434.79e6), # 433 ISM EU
    (470e6,   790e6),    # UHF TV / PMSE
    (863e6,   870e6),    # SRD EU
    (902e6,   928e6),    # ISM US
    (1030e6,  1090e6),   # SSR / ADS-B
]

VALID_MODULATIONS = {
    "ASK", "OOK", "FSK", "GFSK", "MSK", "GMSK", "BPSK", "QPSK",
    "8PSK", "PSK", "QAM", "FM", "AM", "LoRa", "CSS", "PWM", "PPM",
    "Manchester", "DBPSK", "DQPSK"
}

# Sources d'entrée
SOURCES = {
    "github_repo": "https://github.com/TFD-42/Flipper_Zero_RF_DataSet",
    "hf_datasets": [
        # ajouter ici les datasets HF RF/Flipper pertinents
        # ex: "username/flipper-zero-rf-captures"
    ],
    "local_sub_dir": str(BASE / "01_raw_input" / "flipper_sub"),
}
