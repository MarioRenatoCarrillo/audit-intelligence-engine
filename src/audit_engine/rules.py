from __future__ import annotations
import numpy as np
import pandas as pd


RULE_WEIGHTS = {
    "EXACT_DUPLICATE": 95,
    "SOD_CONFLICT": 90,
    "RAPID_BANK_CHANGE_PAYMENT": 85,
    "THRESHOLD_PROXIMITY": 65,
    "ROUND_DOLLAR": 45,
    "AFTER_HOURS": 40,
    "THREE_WAY_MATCH": 60,
}


def evaluate(invoices: pd.DataFrame, vendors: pd.DataFrame, thresholds: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = invoices.copy()
    for col in ("invoice_date", "payment_date"):
        df[col] = pd.to_datetime(df[col])
    v = vendors[["vendor_id", "bank_changed_date"]].copy()
    v["bank_changed_date"] = pd.to_datetime(v.bank_changed_date)
    df = df.merge(v, on="vendor_id", how="left")

    dup = df.duplicated(["vendor_id", "invoice_number", "amount_usd"], keep=False)
    sod = df.entered_by == df.approved_by
    bank_days = (df.payment_date - df.bank_changed_date).dt.days
    bank = bank_days.between(0, 7)
    threshold = np.zeros(len(df), dtype=bool)
    for limit in thresholds:
        threshold |= df.amount_usd.between(limit - 25, limit - .01)
    rounded = (df.amount_usd >= 5000) & ((df.amount_usd % 1000) == 0)
    after = (df.entry_hour < 5) | (df.entry_hour > 21)
    match = ((df.amount_usd - df.receipt_amount).abs() / df.receipt_amount.clip(lower=1)) > .05

    flags = {
        "EXACT_DUPLICATE": dup,
        "SOD_CONFLICT": sod,
        "RAPID_BANK_CHANGE_PAYMENT": bank,
        "THRESHOLD_PROXIMITY": threshold,
        "ROUND_DOLLAR": rounded,
        "AFTER_HOURS": after,
        "THREE_WAY_MATCH": match,
    }
    detail = []
    for rule, mask in flags.items():
        for invoice_id in df.loc[mask, "invoice_id"]:
            detail.append({"invoice_id": invoice_id, "test_id": rule, "severity": RULE_WEIGHTS[rule]})
    exceptions = pd.DataFrame(detail, columns=["invoice_id", "test_id", "severity"])
    evidence = exceptions.groupby("invoice_id").agg(rule_score=("severity", "max"), rule_count=("test_id", "count"), rule_evidence=("test_id", lambda x: " | ".join(sorted(set(x))))).reset_index() if len(exceptions) else pd.DataFrame(columns=["invoice_id","rule_score","rule_count","rule_evidence"])
    return exceptions, evidence

