from __future__ import annotations
from pathlib import Path
import json
import sqlite3
import pandas as pd


def build_dashboard(root: Path) -> Path:
    conn = sqlite3.connect(root / "output" / "audit_engine.db")
    cases = pd.read_sql_query("SELECT * FROM audit_cases ORDER BY risk_score DESC LIMIT 250", conn)
    benford = pd.read_sql_query("SELECT digit, observed, expected FROM benford_results ORDER BY digit", conn)
    dq = pd.read_sql_query("SELECT * FROM data_quality_results", conn)
    runs = pd.read_sql_query("SELECT * FROM audit_run ORDER BY completed_at DESC LIMIT 1", conn)
    conn.close()
    payload = {
        "cases": cases[["invoice_id","vendor_id","source_system","company_code","amount_usd","risk_score","risk_tier","anomaly_percentile","rule_evidence","case_narrative"]].to_dict("records"),
        "benford": benford.to_dict("records"),
        "quality": dq.to_dict("records"),
        "run": runs.to_dict("records")[0],
        "summary": {
            "transactions": int(runs.iloc[0].transaction_count),
            "exceptions": int(runs.iloc[0].exception_count),
            "high": int(cases.risk_tier.isin(["High","Critical"]).sum()),
            "exposure": float(cases.loc[cases.risk_tier.isin(["High","Critical"]), "amount_usd"].sum()),
        }
    }
    html = _template().replace("__AUDIT_DATA__", json.dumps(payload, default=str))
    path = root / "dashboard" / "audit_dashboard.html"
    path.write_text(html, encoding="utf-8")
    return path


def _template() -> str:
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit Intelligence Engine</title>
<style>
:root{--ink:#172033;--muted:#64748b;--bg:#f4f7fb;--panel:#fff;--blue:#1261a0;--orange:#d97706;--red:#b42318;--green:#16803c;--line:#dbe3ee}*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui;background:var(--bg);color:var(--ink)}header{padding:22px 28px;background:#11365a;color:#fff}header h1{margin:0;font-size:24px}header p{margin:5px 0 0;opacity:.8}.wrap{padding:22px;max-width:1400px;margin:auto}.tabs{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}.tabs button{border:1px solid var(--line);background:var(--panel);padding:9px 13px;border-radius:7px;cursor:pointer}.tabs button.active{background:var(--blue);color:#fff}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px}.kpi strong{display:block;font-size:25px;margin-top:5px}.muted{color:var(--muted)}.panel{margin-top:14px}.panel h2{font-size:17px;margin:0 0 12px}table{width:100%;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid var(--line);text-align:left}th{font-size:12px;color:var(--muted)}.tier{font-weight:700}.Critical{color:var(--red)}.High{color:var(--orange)}.Low{color:var(--green)}.bars{display:flex;align-items:flex-end;gap:10px;height:260px;padding:10px 5px 25px}.pair{height:100%;display:flex;align-items:flex-end;gap:3px;flex:1;position:relative}.bar{width:50%;background:var(--blue);min-height:2px}.bar.expected{background:#a7b7c9}.pair label{position:absolute;bottom:-22px;left:45%}.hidden{display:none}.case-row{cursor:pointer}.case-row:hover{background:#f6f9fc}.detail{white-space:pre-wrap;padding:12px;background:#f6f9fc;border-left:4px solid var(--blue)}@media(max-width:800px){.grid{grid-template-columns:1fr 1fr}.wrap{padding:12px}.tablewrap{overflow:auto}}@media(max-width:480px){.grid{grid-template-columns:1fr}}
</style></head><body><header><h1>Audit Intelligence Engine</h1><p>Multi-ERP fraud-risk and controls analytics — synthetic demonstration data</p></header>
<main class="wrap"><nav class="tabs"><button class="active" data-tab="overview">Executive overview</button><button data-tab="benford">Benford analysis</button><button data-tab="cases">Case explorer</button><button data-tab="health">Data health</button></nav>
<section id="overview"><div class="grid"><div class="card kpi"><span class="muted">Transactions analyzed</span><strong id="transactions"></strong></div><div class="card kpi"><span class="muted">Rule exceptions</span><strong id="exceptions"></strong></div><div class="card kpi"><span class="muted">High-priority cases</span><strong id="high"></strong></div><div class="card kpi"><span class="muted">Potential exposure for review</span><strong id="exposure"></strong></div></div><div class="panel"><h2>Top prioritized cases</h2><div class="tablewrap"><table><thead><tr><th>Invoice</th><th>ERP</th><th>Amount</th><th>Risk</th><th>Tier</th><th>Evidence</th></tr></thead><tbody id="top-cases"></tbody></table></div></div></section>
<section id="benford" class="hidden"><div class="panel"><h2>First-digit distribution: observed vs expected</h2><p class="muted">Use only for eligible naturally occurring populations. A deviation is a screening indicator, not proof of fraud.</p><div class="bars" id="benford-bars"></div></div></section>
<section id="cases" class="hidden"><div class="panel"><h2>Audit case explorer</h2><label>Filter by ERP: <select id="erp-filter"><option value="">All</option><option>AGRIS</option><option>CMIS</option><option>JDE</option><option>SAP</option></select></label><div class="tablewrap"><table><thead><tr><th>Invoice</th><th>Vendor</th><th>ERP</th><th>Amount</th><th>Risk</th><th>Anomaly percentile</th><th>Evidence</th></tr></thead><tbody id="case-table"></tbody></table></div><div id="case-detail" class="detail hidden"></div></div></section>
<section id="health" class="hidden"><div class="panel"><h2>Data-quality gate</h2><table><thead><tr><th>Check</th><th>Status</th><th>Actual</th><th>Expected</th></tr></thead><tbody id="quality"></tbody></table></div></section></main>
<script>const D=__AUDIT_DATA__;const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);transactions.textContent=D.summary.transactions.toLocaleString();exceptions.textContent=D.summary.exceptions.toLocaleString();high.textContent=D.summary.high.toLocaleString();exposure.textContent=money(D.summary.exposure);
function row(c){return `<tr class="case-row" data-id="${c.invoice_id}"><td>${c.invoice_id}</td><td>${c.vendor_id||''}</td><td>${c.source_system}</td><td>${money(c.amount_usd)}</td><td>${c.risk_score}</td><td>${c.anomaly_percentile.toFixed(1)}</td><td>${c.rule_evidence}</td></tr>`}document.getElementById('top-cases').innerHTML=D.cases.slice(0,12).map(c=>`<tr><td>${c.invoice_id}</td><td>${c.source_system}</td><td>${money(c.amount_usd)}</td><td>${c.risk_score}</td><td class="tier ${c.risk_tier}">${c.risk_tier}</td><td>${c.rule_evidence}</td></tr>`).join('');
function renderCases(){const f=document.getElementById('erp-filter').value;document.getElementById('case-table').innerHTML=D.cases.filter(c=>!f||c.source_system===f).map(row).join('')}renderCases();document.getElementById('erp-filter').onchange=renderCases;document.getElementById('case-table').onclick=e=>{const tr=e.target.closest('tr');if(!tr)return;const c=D.cases.find(x=>x.invoice_id===tr.dataset.id);const box=document.getElementById('case-detail');box.textContent=c.case_narrative;box.classList.remove('hidden')};
document.getElementById('benford-bars').innerHTML=D.benford.map(x=>`<div class="pair"><div class="bar" style="height:${x.observed*300}%" title="Observed ${(x.observed*100).toFixed(1)}%"></div><div class="bar expected" style="height:${x.expected*300}%" title="Expected ${(x.expected*100).toFixed(1)}%"></div><label>${x.digit}</label></div>`).join('');document.getElementById('quality').innerHTML=D.quality.map(q=>`<tr><td>${q.check_name}</td><td class="${q.passed?'Low':'Critical'}">${q.passed?'PASS':'FAIL'}</td><td>${q.actual}</td><td>${q.expected}</td></tr>`).join('');
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('active'));b.classList.add('active');['overview','benford','cases','health'].forEach(id=>document.getElementById(id).classList.toggle('hidden',id!==b.dataset.tab))});</script></body></html>'''

