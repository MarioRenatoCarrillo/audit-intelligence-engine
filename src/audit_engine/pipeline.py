from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import pandas as pd

from .benford import analyze
from .config import ROOT, load_settings
from .database import build_database, quality_checks
from .model import score_anomalies
from .rules import evaluate
from .synthetic import generate


def run(root: Path = ROOT) -> dict:
    settings = load_settings(root / "config" / "settings.yml")
    run_id = datetime.now(timezone.utc).strftime("RUN-%Y%m%dT%H%M%SZ")
    frames = generate(settings, root / "data" / "synthetic")
    conn = build_database(frames, root / "output" / "audit_engine.db")
    dq = quality_checks(conn)
    if not dq.passed.all():
        raise RuntimeError("Data quality gate failed")
    invoices = pd.read_sql_query("SELECT * FROM canonical_invoices", conn)
    vendors = pd.read_sql_query("SELECT * FROM dim_vendor", conn)
    labels = pd.read_sql_query("SELECT * FROM validation_labels", conn)
    exceptions, rule_summary = evaluate(invoices, vendors, settings["approval_thresholds"])
    anomaly, model = score_anomalies(invoices, settings)
    benford_rows, benford_summary = analyze(invoices.amount_usd)

    scored = invoices.merge(rule_summary, on="invoice_id", how="left").merge(anomaly, on="invoice_id", how="left")
    scored["rule_score"] = scored.rule_score.fillna(0)
    scored["rule_count"] = scored.rule_count.fillna(0).astype(int)
    scored["rule_evidence"] = scored.rule_evidence.fillna("No deterministic exception")
    materiality = scored.amount_usd.rank(pct=True).mul(100)
    control = ((scored.entered_by == scored.approved_by).astype(int) * 100 + scored.manual_entry * 35).clip(upper=100)
    w = settings["risk_weights"]
    scored["risk_score"] = (w["rule"] * scored.rule_score + w["anomaly"] * scored.anomaly_percentile + w["materiality"] * materiality + w["control"] * control).round(1)
    scored["risk_tier"] = pd.cut(scored.risk_score, [-1, 35, 60, 80, 100], labels=["Low", "Moderate", "High", "Critical"]).astype(str)
    scored["case_narrative"] = scored.apply(lambda r: f"Invoice {r.invoice_id} from vendor {r.vendor_id} was prioritized with risk score {r.risk_score}. Evidence: {r.rule_evidence}. The anomaly percentile is {r.anomaly_percentile:.1f}. This is a risk indicator requiring auditor review, not a fraud conclusion.", axis=1)
    scored["run_id"] = run_id

    scored.to_sql("audit_cases", conn, if_exists="replace", index=False)
    exceptions.assign(run_id=run_id).to_sql("audit_rule_results", conn, if_exists="replace", index=False)
    benford_rows.assign(run_id=run_id).to_sql("benford_results", conn, if_exists="replace", index=False)
    pd.DataFrame([{**benford_summary, "run_id": run_id}]).to_sql("benford_summary", conn, if_exists="replace", index=False)
    conn.execute("CREATE TABLE IF NOT EXISTS audit_run (run_id TEXT PRIMARY KEY, completed_at TEXT, transaction_count INTEGER, exception_count INTEGER, status TEXT)")
    conn.execute("INSERT OR REPLACE INTO audit_run VALUES (?, ?, ?, ?, ?)", (run_id, datetime.now(timezone.utc).isoformat(), len(scored), len(exceptions), "SUCCEEDED"))
    conn.commit()

    validation = scored[["invoice_id", "risk_score", "anomaly_percentile"]].merge(labels, on="invoice_id")
    top_n = max(1, int(len(validation) * .03))
    detected = validation.nlargest(top_n, "risk_score").is_injected_anomaly.sum()
    total_anomalies = int(validation.is_injected_anomaly.sum())
    metrics = {
        "run_id": run_id,
        "transactions": len(scored),
        "rule_exceptions": len(exceptions),
        "high_or_critical_cases": int(scored.risk_tier.isin(["High", "Critical"]).sum()),
        "injected_scenarios": total_anomalies,
        "top_3pct_recall": round(float(detected / total_anomalies), 4) if total_anomalies else 0,
        "benford_mad": round(benford_summary["mad"], 6),
        "data_quality_passed": bool(dq.passed.all()),
    }
    (root / "output" / "run_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    conn.close()
    return metrics

