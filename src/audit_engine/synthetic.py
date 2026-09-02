from __future__ import annotations

import hashlib
from pathlib import Path
import numpy as np
import pandas as pd


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def generate(settings: dict, output_dir: Path) -> dict[str, pd.DataFrame]:
    """Generate reproducible, fictional AP data with hidden validation labels."""
    rng = np.random.default_rng(settings["seed"])
    n_vendors = settings["vendors"]
    n = settings["invoices"]
    sources = np.array(settings["sources"])
    companies = np.array(settings["companies"])
    start = pd.Timestamp.today().normalize() - pd.DateOffset(months=settings["months"])

    vendors = pd.DataFrame({
        "vendor_id": [f"V{i:05d}" for i in range(1, n_vendors + 1)],
        "vendor_name": [f"Fictional Supplier {i:05d}" for i in range(1, n_vendors + 1)],
        "source_system": rng.choice(sources, n_vendors),
        "vendor_category": rng.choice(["GRAIN", "FREIGHT", "ENERGY", "SERVICES", "MRO", "OFFICE"], n_vendors, p=[.18,.20,.14,.20,.20,.08]),
        "company_code": rng.choice(companies, n_vendors),
        "created_date": start + pd.to_timedelta(rng.integers(0, settings["months"] * 30, n_vendors), unit="D"),
        "created_by": [f"U{x:04d}" for x in rng.integers(1, 181, n_vendors)],
        "bank_account_hash": [_hash(f"BANK-{x}") for x in rng.integers(1, n_vendors * 2, n_vendors)],
        "bank_changed_date": pd.NaT,
        "status": "ACTIVE",
    })

    vendor_idx = rng.integers(0, n_vendors, n)
    invoice_dates = start + pd.to_timedelta(rng.integers(0, settings["months"] * 30, n), unit="D")
    category_scale = {"GRAIN": 18000, "FREIGHT": 4500, "ENERGY": 10000, "SERVICES": 3500, "MRO": 2200, "OFFICE": 450}
    cats = vendors.loc[vendor_idx, "vendor_category"].to_numpy()
    amounts = np.array([rng.lognormal(np.log(category_scale[c]), .75) for c in cats]).round(2)
    entered = np.array([f"U{x:04d}" for x in rng.integers(1, 181, n)])
    approved = np.array([f"U{x:04d}" for x in rng.integers(181, 241, n)])
    invoices = pd.DataFrame({
        "invoice_id": [f"INV{i:07d}" for i in range(1, n + 1)],
        "vendor_id": vendors.loc[vendor_idx, "vendor_id"].to_numpy(),
        "invoice_number": [f"{rng.choice(['A','B','PO','X'])}-{rng.integers(10000,999999)}" for _ in range(n)],
        "invoice_date": invoice_dates,
        "posting_date": invoice_dates + pd.to_timedelta(rng.integers(0, 8, n), unit="D"),
        "payment_date": invoice_dates + pd.to_timedelta(rng.integers(7, 46, n), unit="D"),
        "amount_usd": amounts,
        "currency": rng.choice(["USD", "CAD"], n, p=[.96, .04]),
        "company_code": vendors.loc[vendor_idx, "company_code"].to_numpy(),
        "source_system": vendors.loc[vendor_idx, "source_system"].to_numpy(),
        "entered_by": entered,
        "approved_by": approved,
        "entry_hour": rng.choice(np.arange(7, 19), n),
        "po_number": [f"PO{rng.integers(100000,999999)}" for _ in range(n)],
        "receipt_amount": (amounts * rng.normal(1, .015, n)).round(2),
        "manual_entry": rng.choice([0, 1], n, p=[.86, .14]),
        "reversal_flag": 0,
        "is_injected_anomaly": 0,
        "scenario_type": "NORMAL",
    })


    # Inject exact duplicates.
    dup_count = max(1, round(n * 45 / 20_000))
    dup_src = rng.choice(
        invoices.index[: n - dup_count],
        dup_count,
        replace=False,
    )
    dup_tgt = invoices.index[-dup_count:]
    for src, tgt in zip(dup_src, dup_tgt):
        keep_id = invoices.at[tgt, "invoice_id"]
        invoices.loc[tgt] = invoices.loc[src]
        invoices.at[tgt, "invoice_id"] = keep_id
        invoices.at[tgt, "payment_date"] = (
            invoices.at[src, "payment_date"] + pd.Timedelta(days=2)
        )
        invoices.at[tgt, "is_injected_anomaly"] = 1
        invoices.at[tgt, "scenario_type"] = "EXACT_DUPLICATE"


    # Split invoices just below approval limits.
    split_rows = rng.choice(invoices.index[100:-100], 45, replace=False)
    for i, idx in enumerate(split_rows):
        threshold = settings["approval_thresholds"][i % len(settings["approval_thresholds"])]
        invoices.at[idx, "amount_usd"] = threshold - rng.choice([1, 5, 10, 25])
        invoices.at[idx, "scenario_type"] = "THRESHOLD_SPLIT"
        invoices.at[idx, "is_injected_anomaly"] = 1

    # Segregation-of-duties exceptions.
    sod_rows = rng.choice(invoices.index[100:-100], 35, replace=False)
    invoices.loc[sod_rows, "approved_by"] = invoices.loc[sod_rows, "entered_by"].to_numpy()
    invoices.loc[sod_rows, ["is_injected_anomaly", "scenario_type"]] = [1, "SOD_CONFLICT"]

    # Bank changes shortly before payment.
    bank_rows = rng.choice(invoices.index[100:-100], 35, replace=False)
    affected_vendors = invoices.loc[bank_rows, "vendor_id"].unique()
    for vendor_id in affected_vendors:
        pay = invoices.loc[(invoices.vendor_id == vendor_id) & invoices.index.isin(bank_rows), "payment_date"].min()
        vendors.loc[vendors.vendor_id == vendor_id, "bank_changed_date"] = pay - pd.Timedelta(days=int(rng.integers(1, 4)))
    invoices.loc[bank_rows, ["is_injected_anomaly", "scenario_type"]] = [1, "RAPID_BANK_CHANGE_PAYMENT"]

    # Round-dollar and after-hours anomalies.
    round_rows = rng.choice(invoices.index[100:-100], 35, replace=False)
    invoices.loc[round_rows, "amount_usd"] = rng.choice([10000, 15000, 25000, 50000], len(round_rows))
    invoices.loc[round_rows, ["is_injected_anomaly", "scenario_type"]] = [1, "ROUND_DOLLAR"]
    after_rows = rng.choice(invoices.index[100:-100], 25, replace=False)
    invoices.loc[after_rows, "entry_hour"] = rng.choice([0, 1, 2, 3, 22, 23], len(after_rows))
    invoices.loc[after_rows, ["is_injected_anomaly", "scenario_type"]] = [1, "AFTER_HOURS"]

    # Synthetic source extracts use different ERP-style names.
    source_frames = {}
    mappings = {
        "SAP": {"invoice_id":"belnr", "vendor_id":"lifnr", "amount_usd":"wrbtr", "company_code":"bukrs"},
        "JDE": {"invoice_id":"rpdoc", "vendor_id":"rpan8", "amount_usd":"rpag", "company_code":"rpco"},
        "AGRIS": {"invoice_id":"settlement_no", "vendor_id":"producer_no", "amount_usd":"settlement_amount", "company_code":"location_code"},
        "CMIS": {"invoice_id":"document_key", "vendor_id":"counterparty_id", "amount_usd":"net_amount", "company_code":"entity_code"},
    }
    for source, rename in mappings.items():
        source_frames[source.lower()] = invoices[invoices.source_system == source].rename(columns=rename).copy()

    output_dir.mkdir(parents=True, exist_ok=True)
    vendors.to_csv(output_dir / "vendors.csv", index=False)
    for name, frame in source_frames.items():
        frame.to_csv(output_dir / f"raw_{name}_invoices.csv", index=False)
    invoices[["invoice_id", "is_injected_anomaly", "scenario_type"]].to_csv(output_dir / "validation_labels.csv", index=False)
    return {"vendors": vendors, "invoices": invoices, **source_frames}

