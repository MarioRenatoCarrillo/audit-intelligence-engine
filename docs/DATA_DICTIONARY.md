# Data dictionary

## Canonical invoices

| Field | Meaning |
|---|---|
| invoice_id | Unique synthetic document identifier |
| vendor_id | Fictional vendor identifier |
| invoice_number | Supplier invoice reference |
| invoice_date / posting_date / payment_date | Transaction lifecycle dates |
| amount_usd | Synthetic invoice amount in USD-equivalent terms |
| source_system | AGRIS, CMIS, JDE, or SAP |
| company_code | Fictional reporting entity/location |
| entered_by / approved_by | Synthetic ERP user identifiers |
| entry_hour | Hour of initial entry |
| po_number | Synthetic purchase-order reference |
| receipt_amount | Synthetic received-value comparison |
| manual_entry | Manual-entry indicator |

## Audit cases

| Field | Meaning |
|---|---|
| rule_score | Maximum configured deterministic-rule severity |
| rule_count | Number of triggered deterministic tests |
| rule_evidence | Human-readable triggered-test list |
| anomaly_percentile | Relative Isolation Forest anomaly score |
| risk_score | Configured hybrid prioritization score from 0–100 |
| risk_tier | Low, Moderate, High, or Critical review priority |
| case_narrative | Evidence-grounded review summary |

`validation_labels` is segregated from features and outputs. It records only the synthetic scenario injected for evaluation.

