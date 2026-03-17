# KorumOS Internal Records

Classification: CONFIDENTIAL - TRADE SECRET

This folder stores dated internal engineering and process records for KorumOS.

Rules for use:

- Create a new `YYYY-MM-DD_*` markdown file for each material architecture, product, security, or commercialization change.
- Record both local time and UTC, plus the current branch and commit hash.
- List impacted files, the reason for the change, and the person responsible.
- Keep these records in private storage with access limited to people under written confidentiality obligations.
- If this repository or any copy of these records is made public, do not rely on that copy for trade-secret treatment.

Minimum template:

```md
# Title

Classification: CONFIDENTIAL - TRADE SECRET
Created (local): YYYY-MM-DDTHH:MM:SS-04:00
Created (UTC): YYYY-MM-DDTHH:MM:SSZ
Repository: KorumOS
Branch: main
Commit: <git sha>
Author: <name>

## Summary

## Files Affected

## Technical Detail

## Access + Handling Notes
```
