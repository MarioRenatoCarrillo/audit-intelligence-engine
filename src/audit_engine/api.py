from pathlib import Path
import sqlite3
from fastapi import FastAPI, HTTPException, Query
from .config import ROOT

app = FastAPI(title="Audit Intelligence Engine API", version="0.1.0")


def connection() -> sqlite3.Connection:
    conn = sqlite3.connect(ROOT / "output" / "audit_engine.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/health")
def health() -> dict:
    return {"status": "healthy" if (ROOT / "output" / "audit_engine.db").exists() else "not_ready"}


@app.get("/runs/latest")
def latest_run() -> dict:
    with connection() as conn:
        row = conn.execute("SELECT * FROM audit_run ORDER BY completed_at DESC LIMIT 1").fetchone()
    if not row:
        raise HTTPException(404, "No completed run")
    return dict(row)


@app.get("/exceptions")
def exceptions(min_risk: float = Query(60, ge=0, le=100), limit: int = Query(100, ge=1, le=1000)) -> list[dict]:
    with connection() as conn:
        rows = conn.execute("SELECT invoice_id, vendor_id, source_system, amount_usd, risk_score, risk_tier, rule_evidence FROM audit_cases WHERE risk_score >= ? ORDER BY risk_score DESC LIMIT ?", (min_risk, limit)).fetchall()
    return [dict(r) for r in rows]


@app.get("/exceptions/{invoice_id}")
def exception_detail(invoice_id: str) -> dict:
    with connection() as conn:
        row = conn.execute("SELECT * FROM audit_cases WHERE invoice_id = ?", (invoice_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Case not found")
    return dict(row)

