# Contributing

**All contributions are welcome.** This dataset is being fact-checked file by file — every correction, addition, or pair of eyes helps.

No CLA, no contributor agreement. Public regulatory data, open contribution.

## What's most useful

In priority order:

1. **Fact-corrections** — you spotted a wrong allocation, power limit, modulation, or regulatory reference for your country
2. **Country additions** — currently 9 covered (FR, US, UK, CN, DE, RU, ES, IT, CH). Adding JP, KR, BR, IN, AU, CA, others = huge value
3. **Device examples with model numbers** — real-world devices that actually transmit on a band in your region
4. **Regulatory reference enrichment** — pin a specific FCC Part / ECC Decision / national gazette to an entry
5. **HF datasets to cross-reference** — point at community RF / rtl_433 datasets the pipeline should triangulate against
6. **Pipeline improvements** — new sources, better confidence weighting, additional cross-check backends

Even a **single-line correction** is valuable — that's one less hallucination in someone's fine-tuned LLM.

## How to contribute

### Issues

Open one for:
- Factual errors (please include the source: regulator URL, doc reference, etc.)
- Missing devices / services / countries
- Pipeline bugs
- Suggestions

### Pull Requests

#### Data corrections

1. Edit the relevant JSON in `enriched_data/` or `merged_dataset/`
2. Add a `correction_note` field referencing the source you fact-checked against
3. Update the relevant report in `factcheck_reports/` if applicable
4. PR description: what changed, why, source consulted

Example minimal correction:
```json
{
  "freq_low_mhz": 868.0,
  "freq_high_mhz": 868.6,
  "country_code": "DE",
  "service": "SRD",
  "regulatory_ref": "BNetzA Vfg 60/2019, ETSI EN 300 220-2",
  "correction_note": "Power limit corrected from 25 mW ERP to 25 mW ERP with ≤1% duty cycle (was missing duty cycle constraint). Source: BNetzA Allgemeinzuteilung Vfg 60/2019 §4.2."
}
```

#### Pipeline changes

- PRs against `Data_Process/scripts/`
- Keep cross-check sources public / API-free where possible (DDG fallback, Wikipedia, HF public datasets)
- Add tests / smoke checks if you change confidence math
- Update `Data_Process/README.md` if you change behavior

#### New countries

1. Add country to the relevant 5 enriched JSON files (one entry per allocation × country)
2. Cite the national regulator at minimum
3. Add the regulator to `STANDARDS.md`
4. Add to the `CROSS_CHECK_SOURCES.websearch.trusted_domains` list in `00_config.py` if they have an official `.gov` / national TLD

## Code style

- Python 3.10+
- No formatter enforced; PEP8-ish
- Keep network calls behind env flags (e.g. `CROSS_CHECK=1`) so the pipeline stays offline-first

## What I'll merge fast

- Typo fixes ✅
- Single-line factual corrections with a source ✅
- New device examples ✅
- New regulatory citations ✅

## What I'll discuss first

- Removing entries (might need a `disputed_note` instead)
- Changing the confidence scoring weights
- Adding new cross-check sources (good — let's pick the right ones together)
- Schema changes (need to migrate existing files)

## Credit

Commit history is the credit log. If you want a different name in commits, configure your git locally before pushing — I won't rewrite history.

## Questions?

Open an issue with the `question` label. Discussion is welcome before opening a big PR.

---

**Thanks for helping make this dataset more accurate.** RF allocations are genuinely complex and per-country edge cases are everywhere — community knowledge is the only way this gets to the ×210 production target with real quality.
