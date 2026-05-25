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
    # Pour la validation contre HF dataset existant (Step 03 cross-check #1)
    # On utilise transformers + device_map="auto" → split natif sur 6 GPU sans serveur externe
    "hallucination_detection": {
        "engine": "transformers-auto",
        "model": "Qwen/Qwen2.5-32B-Instruct",
        "device_map": "auto",       # accelerate split auto sur tous les GPU visibles
        "dtype": "bfloat16",         # ~64 GB → fit dans 48 GB VRAM avec offload CPU residuel
        "max_memory": {              # cap par GPU pour éviter OOM
            0: "7GiB", 1: "7GiB", 2: "7GiB",
            3: "7GiB", 4: "7GiB", 5: "7GiB",
            "cpu": "20GiB",
        },
        "temperature": 0.0,
        "max_new_tokens": 8,
    },
    # Pour le résumé / extraction depuis pages web fetchées (Step 03 cross-check #2)
    # vLLM tensor-parallel sur 6 GPU, serveur OpenAI-compatible localhost:8000
    "web_compare_llm": {
        "engine": "vllm",
        "model": "Qwen/Qwen2.5-7B-Instruct",   # 7B suffit pour extraction/comparaison
        "tensor_parallel_size": 6,
        "host": "http://localhost:8000/v1",
        "dtype": "bfloat16",
        "gpu_memory_utilization": 0.85,
        "max_model_len": 8192,
        "temperature": 0.0,
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

# Cross-check sources for 03_rf_validation (multi-source confidence scoring)
CROSS_CHECK_SOURCES = {
    # 1) HF dataset(s) — exact / fuzzy match against community RF data
    "hf_datasets": [
        # Tu peux ajouter d'autres datasets RF/rtl_433/Flipper ici
        # Format: (dataset_name, split, freq_field, modulation_field, protocol_field)
        # ex: ("merve/rtl_433_captures", "train", "frequency", "modulation", "protocol"),
    ],
    # 2) Wikipedia API (no key, structured, multilingual)
    "wikipedia": {
        "enabled": True,
        "endpoint": "https://en.wikipedia.org/w/api.php",
        "pages": [
            # Per-country frequency allocation pages
            "Frequency allocation",
            "Radio spectrum",
            "ISM radio band",
            "Short-range device",
            "List of UHF radio bands",
        ],
        "timeout": 8,
    },
    # 3) Web search (FCC, ITU, ANFR, Ofcom, BNetzA + forums RTL-SDR / Flipper)
    "websearch": {
        "enabled": True,
        # Auto-detected from env: BRAVE_API_KEY, SERPER_API_KEY, GOOGLE_CSE_KEY+CX
        # Falls back to DuckDuckGo HTML if no key present
        "max_results_per_claim": 5,
        "trusted_domains": [
            "fcc.gov", "itu.int", "anfr.fr", "ofcom.org.uk", "bundesnetzagentur.de",
            "miit.gov.cn", "rkn.gov.ru", "mincotur.gob.es", "mimit.gov.it", "bakom.admin.ch",
            "etsi.org", "cept.org", "ecodocdb.dk", "lora-alliance.org", "3gpp.org",
        ],
        "forum_domains": [
            "github.com/merbanan/rtl_433",
            "github.com/flipperdevices/flipperzero-firmware",
            "forum.flipper.net",
            "reddit.com/r/flipperzero",
            "reddit.com/r/RTLSDR",
            "reddit.com/r/amateurradio",
            "stackexchange.com",
        ],
        "timeout": 10,
    },
}

# Confidence scoring config (Step 03 → second score independent of Step 07)
# Range: 0.0 - 1.0, written as `confidence_pct` (0-100) per record
CONFIDENCE_SCORING = {
    # Base confidence par source qui CONFIRME le claim
    "source_weights": {
        "hf_dataset_match":       0.25,   # exact/fuzzy match in HF dataset
        "wikipedia_match":        0.20,   # entry in Wikipedia
        "official_regulator":     0.35,   # FCC / ITU / ANFR / Ofcom etc.
        "trusted_standard":       0.20,   # ETSI / CEPT / 3GPP / LoRa Alliance
        "forum_community":        0.10,   # rtl_433 / Flipper / Reddit (lower weight)
    },
    # Pénalités
    "penalties": {
        "source_contradiction":   -0.30,  # 2+ sources disagree
        "no_source_found":        -0.40,  # zero source returned anything
        "stale_data":             -0.10,  # source > 5 years old
        "single_source_only":     -0.15,  # only 1 source confirmed (no triangulation)
        "country_mismatch":       -0.20,  # source talks about another country
    },
    # Bonus
    "bonuses": {
        "triangulation_3plus":    +0.15,  # 3+ independent sources agree
        "official_plus_forum":    +0.05,  # both official and community confirm
    },
    # Output buckets
    "buckets": {
        "high_confidence":   0.75,        # ≥ 75%
        "medium_confidence": 0.50,        # 50-74%
        "low_confidence":    0.25,        # 25-49%
        "no_confidence":     0.00,        # < 25%
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
