# Contributing to Flipper_Zero_RF_DataSet

**Last updated**: 2026-06-15

## Adding new RF samples
1. Fork the repository.
2. Place new samples in the appropriate frequency folder.
3. Update `metadata.json` with source, frequency, modulation, and country of collection.
4. Run `./validate_dataset.sh` (if provided) to check format and ethics.
5. Submit a pull request.

## Ethical guidelines for new data
- **No live capturing** without explicit permission from spectrum owners.
- **No personal or sensitive data** (e.g., voice, video, encrypted payloads).
- **Only legal, non‑restricted bands** (avoid licensed cellular or military bands).

## Pull request checklist
- [ ] Data is original or properly attributed.
- [ ] No PII or harmful payloads.
- [ ] Metadata includes collection method and location (general only).
- [ ] I have read and agree to the dataset’s ethics statement.
