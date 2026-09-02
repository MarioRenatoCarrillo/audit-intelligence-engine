# Audit Intelligence Engine — Demonstration Report

## Executive summary

Following the interview discussion about improving audit efficiency with AI, this project demonstrates how reusable SQL tests, Benford analysis, anomaly detection, and standardized case narratives can support Internal Audit. It uses only synthetic data and fictionalized ERP structures.

## Business value

The design separates source-specific ERP mapping from reusable audit tests. An audit team can define a test once, apply it consistently across approved populations, retain execution history, and prioritize review using explainable evidence.

## Demonstrated controls

- Duplicate invoices
- Transactions immediately below approval thresholds
- Conflicts between transaction entry and approval
- Payments shortly after vendor bank changes
- Round-dollar and after-hours activity
- Invoice-to-receipt variance
- Benford population screening
- Multivariate anomaly detection

## Responsible AI

The system does not conclude that fraud occurred. It presents risk indicators, source records, test versions, and explanations to an auditor. AI-generated narratives are grounded in structured evidence and require human approval.

## Production path

Before enterprise use, replace synthetic adapters with approved read-only extracts, validate each canonical mapping and audit population, calibrate risk thresholds with auditors, implement enterprise identity and row-level security, and deploy only through approved infrastructure and AI services.

## Recommended discussion

1. Which AP or master-data tests consume the most audit-team time today?
2. Which ERP datasets already exist in a central repository?
3. How are findings, actions, and reviewer dispositions currently tracked?
4. Which AI services are approved for structured audit evidence?
5. What would define a useful pilot: coverage, review yield, time saved, or recoveries?

