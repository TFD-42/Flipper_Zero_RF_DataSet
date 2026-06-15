# Security Policy – Dataset Integrity

**Last updated**: 2026-06-15

## Reporting a Vulnerability in the Dataset
If you find corrupted, malicious, or privacy‑violating entries in the dataset, **do not open a public issue**.

Please use GitHub’s **private security advisory** (repository Settings → Security → Advisories) to describe the problem.  
We will investigate and publish a corrected version within 7 days.

## Dataset Integrity Checks
- All samples are validated with a checksum (see `checksums.txt` in the root).
- If you suspect tampering, verify hashes before use.
