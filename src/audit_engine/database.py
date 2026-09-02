from pathlib import Path
import sqlite3
import pandas as pd

from .config import ROOT


def build_database(frames: dict[str, pd.DataFrame], db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    frames["vendors"].to_sql("dim_vendor", conn, index=False)
    for source in ("sap", "jde", "agris", "cmis"):
        frames[source].drop(columns=["is_injected_anomaly", "scenario_type"], errors="ignore").to_sql(f"raw_{source}", conn, index=False)
    with (ROOT / "sql" / "canonical.sql").open(encoding="utf-8") as handle:
        conn.executescript(handle.read())
    frames["invoices"][["invoice_id", "is_injected_anomaly", "scenario_type"]].to_sql("validation_labels", conn, index=False)
    conn.commit()
    return conn


def quality_checks(conn: sqlite3.Connection) -> pd.DataFrame:
    checks = []
    total = conn.execute("SELECT COUNT(*) FROM canonical_invoices").fetchone()[0]
    raw = sum(conn.execute(f"SELECT COUNT(*) FROM raw_{s}").fetchone()[0] for s in ("sap", "jde", "agris", "cmis"))
    checks.append(("row_count_reconciliation", total == raw, total, raw))
    missing = conn.execute("SELECT COUNT(*) FROM canonical_invoices WHERE invoice_id IS NULL OR vendor_id IS NULL OR amount_usd IS NULL").fetchone()[0]
    checks.append(("required_fields", missing == 0, missing, 0))
    duplicate_keys = conn.execute("SELECT COUNT(*) - COUNT(DISTINCT invoice_id) FROM canonical_invoices").fetchone()[0]
    checks.append(("canonical_key_uniqueness", duplicate_keys == 0, duplicate_keys, 0))
    invalid = conn.execute("SELECT COUNT(*) FROM canonical_invoices WHERE amount_usd <= 0").fetchone()[0]
    checks.append(("positive_amounts", invalid == 0, invalid, 0))
    result = pd.DataFrame(checks, columns=["check_name", "passed", "actual", "expected"])
    result.to_sql("data_quality_results", conn, if_exists="replace", index=False)
    return result

