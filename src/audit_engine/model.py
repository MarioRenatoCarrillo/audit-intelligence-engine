from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .benford import digit_rarity


def score_anomalies(invoices: pd.DataFrame, settings: dict) -> tuple[pd.DataFrame, Pipeline]:
    df = invoices.copy()
    df["invoice_date"] = pd.to_datetime(df.invoice_date)
    vendor_stats = df.groupby("vendor_id").amount_usd.agg(["median", "count"]).rename(columns={"median":"vendor_median", "count":"vendor_frequency"})
    features = df.join(vendor_stats, on="vendor_id")
    features["log_amount"] = np.log1p(features.amount_usd)
    features["amount_to_vendor_median"] = features.amount_usd / features.vendor_median.clip(lower=1)
    features["weekend"] = (features.invoice_date.dt.dayofweek >= 5).astype(int)
    features["after_hours"] = ((features.entry_hour < 5) | (features.entry_hour > 21)).astype(int)
    features["threshold_distance"] = features.amount_usd.map(lambda x: min(abs(x - t) for t in settings["approval_thresholds"]))
    features["receipt_variance_pct"] = ((features.amount_usd - features.receipt_amount).abs() / features.receipt_amount.clip(lower=1)).clip(upper=10)
    features["digit_rarity"] = digit_rarity(features.amount_usd)
    numeric = ["log_amount", "amount_to_vendor_median", "vendor_frequency", "weekend", "after_hours", "threshold_distance", "receipt_variance_pct", "digit_rarity", "manual_entry"]
    categorical = ["source_system", "company_code"]
    prep = ColumnTransformer([("num", StandardScaler(), numeric), ("cat", OneHotEncoder(handle_unknown="ignore"), categorical)])
    model = IsolationForest(n_estimators=settings["isolation_forest"]["estimators"], contamination=settings["isolation_forest"]["contamination"], random_state=settings["seed"], n_jobs=-1)
    pipeline = Pipeline([("features", prep), ("model", model)])
    X = features[numeric + categorical]
    pipeline.fit(X)
    raw = -pipeline.decision_function(X)
    percentile = pd.Series(raw).rank(pct=True).mul(100)
    result = pd.DataFrame({"invoice_id": df.invoice_id, "anomaly_raw": raw, "anomaly_percentile": percentile})
    return result, pipeline

