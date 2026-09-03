# Audit Intelligence Engine

A production-oriented, synthetic-data portfolio project for multi-ERP audit analytics. It standardizes fictional AGRIS, CMIS, JDE, and SAP accounts-payable data; runs explainable controls tests; applies Isolation Forest anomaly detection; creates hybrid risk scores; and publishes an interactive audit dashboard and API.

> Results are risk indicators requiring auditor review. They are not determinations of fraud.

## Live demo

Explore the stakeholder-focused audit dashboard:

**[Open the Audit Intelligence Engine Dashboard](https://mariorenatocarrillo.github.io/audit-intelligence-engine/)**

The demonstration uses entirely synthetic data and fictionalized ERP structures. It does not contain CHS data or reproduce proprietary CHS schemas.


## What the MVP includes

- Reproducible synthetic data with separately stored ground-truth scenarios
- Four source-specific ERP extracts and a canonical SQL model
- Data-quality and reconciliation gate
- Benford first-digit analysis with MAD and chi-square measures
- Duplicate, threshold, segregation-of-duties, bank-change, round-dollar, after-hours, and three-way-match tests
- Isolation Forest transaction anomaly model
- Configurable hybrid risk score
- Grounded, template-based case narratives
- Interactive HTML dashboard
- FastAPI read-only case API
- Docker, CI, unit tests, model card, data dictionary, and runbook

## Quick start

The local pipeline uses SQLite and requires no credentials.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
audit-engine all
python -m http.server 8080 --directory dashboard
```

Open `http://localhost:8080/audit_dashboard.html`.

Start the API:

```bash
uvicorn audit_engine.api:app --reload
```

API documentation is available at `http://127.0.0.1:8000/docs`.

Alternatively:

```bash
docker compose up --build
```

## Pipeline

```text
Synthetic ERP extracts -> canonical SQL -> quality gate -> rules + Benford + ML
-> evidence and risk scoring -> dashboard/API -> human review and disposition
```

## Important limitations

- All organizations, people, accounts, and transactions are fictional.
- Source table names are educational approximations, not proprietary CHS schemas.
- Benford analysis is only appropriate for eligible naturally occurring populations.
- The synthetic benchmark measures scenario recovery, not real-world fraud performance.
- The generative-AI layer begins with safe templates; an approved enterprise model can later replace it behind the same interface.

See `docs/` for the data dictionary, model card, runbook, and manager report.

