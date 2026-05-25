# DB_RF_TO_CHECK

Dataset d'allocations de fréquences radio 280–1100 MHz pour 9 pays (FR, US, UK, CN, DE, RU, ES, IT, CH).

## Structure

- `enriched_data/` — 5 fichiers JSON par bande de fréquence (500 entrées au total)
- `merged_dataset/` — Dataset fusionné JSON + CSV
- `qa_dataset/` — 1500 paires Q&A (JSONL + JSON) pour fine-tuning
- `factcheck_reports/` — Rapports de fact-check par bande + consolidé
- `baseline/` — Données baseline ITU/CEPT/FCC

## Stats

- 500 entrées, 101 segments fréquence fins
- 9 pays + worldwide
- 16 corrections critiques appliquées après fact-check
- Sources : ITU RR, FCC 47 CFR, CEPT ECC, ETSI, ICAO Annex 10, 3GPP, régulateurs nationaux

⚠️ **À vérifier** : fact-check fait via expertise réglementaire, pas via accès live aux registres officiels. Détails opérateurs et changements 2025+ à confirmer.
