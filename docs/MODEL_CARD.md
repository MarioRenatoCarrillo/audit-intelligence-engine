# Model card — Isolation Forest baseline

## Intended use

Prioritize accounts-payable transactions for human audit review when confirmed fraud labels are limited.

## Inputs

Log amount, amount relative to vendor median, vendor frequency, weekend and after-hours indicators, approval-threshold distance, receipt variance, first-digit rarity, manual-entry flag, source system, and company code.

## Output

An anomaly percentile used as one component of the hybrid risk score.

## Prohibited use

- Declaring or proving fraud
- Adverse action against an employee or vendor without investigation
- Automatic payment blocking
- Training on the segregated synthetic scenario label

## Limitations

Isolation Forest identifies rarity, not misconduct. Legitimate rare transactions can receive high scores, while coordinated or common-pattern abuse can remain undetected. Synthetic evaluation does not establish real-world accuracy.

## Monitoring

Monitor score distribution, alert volume, source and peer-group drift, top-N review yield, false-positive disposition, and version lineage. Replace a model only after champion/challenger review.

