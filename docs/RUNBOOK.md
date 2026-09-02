# Production runbook

## Standard run

1. Confirm source snapshot and configuration version.
2. Run `audit-engine all`.
3. Confirm all data-quality checks pass.
4. Review `output/run_metrics.json`.
5. Open the dashboard and validate transaction and exception totals.
6. Record the run ID in the audit workpaper.

## Failure response

- **Reconciliation failure:** stop; compare raw and canonical counts and totals.
- **Missing keys:** quarantine invalid records and request a corrected extract.
- **Unexpected alert spike:** compare source volume, configuration, and score drift before distributing cases.
- **Model failure:** retain deterministic rule results and mark model output unavailable.
- **Narrative failure:** display structured evidence only; never block case review.

## Security

Use read-only source credentials, managed secrets, encrypted storage, role-based access, row-level security, and immutable run/disposition logs. Mask bank accounts and tax identifiers.

