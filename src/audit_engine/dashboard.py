from __future__ import annotations
from pathlib import Path
import json
import sqlite3
import pandas as pd


def build_dashboard(root: Path) -> Path:
    conn = sqlite3.connect(root / "output" / "audit_engine.db")

    all_cases = pd.read_sql_query(
        "SELECT * FROM audit_cases",
        conn,
    )

    cases = all_cases.sort_values(
        "risk_score",
        ascending=False,
    ).head(250)


    flagged_cases = all_cases.loc[all_cases["rule_count"] > 0]

    high_risk_mask = all_cases["risk_tier"].isin(["High", "Critical"])
    high_risk_cases = all_cases.loc[high_risk_mask]

    duplicate_cases = all_cases.loc[
        all_cases["rule_evidence"].str.contains(
            "EXACT_DUPLICATE",
            na=False,
        )
    ]

    suspected_duplicates = duplicate_cases.drop_duplicates(
        subset=["vendor_id", "invoice_number", "amount_usd"],
        keep="last",
    )



    benford = pd.read_sql_query("SELECT digit, observed, expected FROM benford_results ORDER BY digit", conn)
    dq = pd.read_sql_query("SELECT * FROM data_quality_results", conn)
    runs = pd.read_sql_query("SELECT * FROM audit_run ORDER BY completed_at DESC LIMIT 1", conn)
    rule_results = pd.read_sql_query(
        "SELECT * FROM audit_rule_results",
        conn,
    )
    benford_summary = pd.read_sql_query(
        "SELECT * FROM benford_summary ORDER BY run_id DESC LIMIT 1",
        conn,
    )
    conn.close()

    risk_by_erp = (
        all_cases.groupby("source_system")
        .agg(
            transactions=("invoice_id", "count"),
            flagged=("rule_count", lambda values: int((values > 0).sum())),
            high_risk=(
                "risk_tier",
                lambda values: int(
                    values.isin(["High", "Critical"]).sum()
                ),
            ),
            transaction_value=("amount_usd", "sum"),
        )
        .reset_index()
    )

    risk_by_erp["exception_rate"] = (
        risk_by_erp["flagged"]
        / risk_by_erp["transactions"]
        * 100
    ).round(2)

    risk_by_company = (
        all_cases.groupby("company_code")
        .agg(
            transactions=("invoice_id", "count"),
            flagged=("rule_count", lambda values: int((values > 0).sum())),
            high_risk=(
                "risk_tier",
                lambda values: int(
                    values.isin(["High", "Critical"]).sum()
                ),
            ),
            transaction_value=("amount_usd", "sum"),
        )
        .reset_index()
    )

    risk_by_company["exception_rate"] = (
        risk_by_company["flagged"]
        / risk_by_company["transactions"]
        * 100
    ).round(2)

    control_indicators = (
        rule_results.groupby("test_id")
        .agg(
            rule_triggers=("invoice_id", "count"),
            unique_transactions=("invoice_id", "nunique"),
        )
        .reset_index()
        .sort_values(
            "unique_transactions",
            ascending=False,
        )
    )

    benford_stats = benford_summary.iloc[0]
    benford_mad = float(benford_stats["mad"])
    benford_eligible = bool(benford_stats["eligible"])

    if not benford_eligible:
        benford_status = "Insufficient population"
        benford_conclusion = (
            "The population is too small for reliable Benford screening."
        )
    elif benford_mad <= 0.006:
        benford_status = "Close conformity"
        benford_conclusion = (
            "The first-digit distribution closely follows Benford's Law. "
            "No broad population-level anomaly was identified."
        )
    elif benford_mad <= 0.012:
        benford_status = "Acceptable conformity"
        benford_conclusion = (
            "The distribution shows moderate variation but remains within "
            "an acceptable screening range."
        )
    elif benford_mad <= 0.015:
        benford_status = "Marginal conformity"
        benford_conclusion = (
            "The population shows elevated digit variation and should be "
            "reviewed by ERP, company, vendor category, and period."
        )
    else:
        benford_status = "Nonconformity"
        benford_conclusion = (
            "The population shows substantial first-digit deviation. "
            "Perform targeted subgroup analysis and transaction review."
        )

    benford["deviation"] = (
        benford["observed"] - benford["expected"]
    ).abs()

    largest_deviation = benford.loc[
        benford["deviation"].idxmax()
    ]

    payload = {
        "cases": cases[["invoice_id","vendor_id","source_system","company_code","amount_usd","risk_score","risk_tier","anomaly_percentile","rule_evidence","case_narrative"]].to_dict("records"),
        "benford": benford.to_dict("records"),
        "quality": dq.to_dict("records"),
        "run": runs.to_dict("records")[0],
        "risk_by_erp": risk_by_erp.to_dict("records"),
        "risk_by_company": risk_by_company.to_dict("records"),
        "control_indicators": control_indicators.to_dict("records"),
        "benford_kpis": {
            "sample_size": int(benford_stats["sample_size"]),
            "eligible": benford_eligible,
            "mad": benford_mad,
            "chi_square": float(benford_stats["chi_square"]),
            "status": benford_status,
            "conclusion": benford_conclusion,
            "largest_deviation_digit": int(
                largest_deviation["digit"]
            ),
            "largest_deviation_points": float(
                largest_deviation["deviation"] * 100
            ),
        },


        "summary": {
            "transactions": int(len(all_cases)),
            "total_value": float(all_cases["amount_usd"].sum()),
            "rule_triggers": int(runs.iloc[0].exception_count),
            "flagged_transactions": int(len(flagged_cases)),
            "exception_rate": float(
                len(flagged_cases) / len(all_cases) * 100
            ),
            "high": int(len(high_risk_cases)),
            "multi_indicator": int(
                (all_cases["rule_count"] >= 2).sum()
            ),
            "review_value": float(
                high_risk_cases["amount_usd"].sum()
            ),
            "duplicate_exposure": float(
                suspected_duplicates["amount_usd"].sum()
            ),
        },
    }



    html = _template().replace("__AUDIT_DATA__", json.dumps(payload, default=str),)
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
<section id="overview">
<div class="grid">
    <div class="card kpi">
        <span class="muted">Transactions analyzed</span>
        <strong id="transactions"></strong>
    </div>

    <div class="card kpi">
        <span class="muted">Total transaction value</span>
        <strong id="total-value"></strong>
    </div>

    <div class="card kpi">
        <span class="muted">Unique flagged transactions</span>
        <strong id="flagged-transactions"></strong>
    </div>

    <div class="card kpi">
        <span class="muted">Exception rate</span>
        <strong id="exception-rate"></strong>
    </div>

    <div class="card kpi">
        <span class="muted">High/Critical review cases</span>
        <strong id="high"></strong>
    </div>

    <div class="card kpi">
        <span class="muted">Multi-indicator cases</span>
        <strong id="multi-indicator"></strong>
    </div>

    <div class="card kpi">
        <span class="muted">Value prioritized for review</span>
        <strong id="review-value"></strong>
    </div>

    <div class="card kpi">
        <span class="muted">Potential duplicate-payment exposure</span>
        <strong id="duplicate-exposure"></strong>
    </div>
</div>

<div class="panel">
<div class="panel">
    <h2>Management insights and recommended actions</h2>

    <p class="muted">
        Automated observations highlight where audit attention may provide
        the greatest value. All recommendations require auditor validation.
    </p>

    <div class="tablewrap">
        <table>
            <thead>
                <tr>
                    <th>Priority insight</th>
                    <th>Supporting evidence</th>
                    <th>Recommended action</th>
                </tr>
            </thead>
            <tbody id="management-insights"></tbody>
        </table>
    </div>
</div>

    <h2>Top prioritized cases</h2>
    <p class="muted">
        Transactions are prioritized for auditor review and do not represent
        confirmed fraud.
    </p>
    <div class="tablewrap">
        <table>
            <thead>
                <tr>
                    <th>Invoice</th>
                    <th>ERP</th>
                    <th>Amount</th>
                    <th>Risk</th>
                    <th>Tier</th>
                    <th>Evidence</th>
                </tr>
            </thead>
            <tbody id="top-cases"></tbody>
        </table>
    </div>
</div>
</section>

<div class="panel">
    <h2>Risk concentration by ERP</h2>

    <p class="muted">
        Compare transaction volume, flagged activity, and exception rates
        across source systems.
    </p>

    <div class="tablewrap">
        <table>
            <thead>
                <tr>
                    <th>ERP</th>
                    <th>Transactions</th>
                    <th>Flagged</th>
                    <th>High/Critical</th>
                    <th>Exception rate</th>
                    <th>Transaction value</th>
                </tr>
            </thead>
            <tbody id="risk-by-erp"></tbody>
        </table>
    </div>
</div>

<div class="panel">
    <h2>Risk concentration by company</h2>

    <p class="muted">
        Identify business entities with elevated exception rates or
        concentrations of high-priority transactions.
    </p>

    <div class="tablewrap">
        <table>
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Transactions</th>
                    <th>Flagged</th>
                    <th>High/Critical</th>
                    <th>Exception rate</th>
                    <th>Transaction value</th>
                </tr>
            </thead>
            <tbody id="risk-by-company"></tbody>
        </table>
    </div>
</div>

<div class="panel">
    <h2>Top control indicators</h2>

    <p class="muted">
        Control tests are ranked by the number of unique transactions
        requiring review.
    </p>

    <div class="tablewrap">
        <table>
            <thead>
                <tr>
                    <th>Control indicator</th>
                    <th>Unique transactions</th>
                    <th>Total rule triggers</th>
                    <th>Recommended audit response</th>
                </tr>
            </thead>
            <tbody id="control-indicators"></tbody>
        </table>
    </div>
</div>

<section id="benford" class="hidden">
<div class="grid">
    <div class="card kpi">
        <span class="muted">Population tested</span>
        <strong id="benford-sample"></strong>
    </div>

    <div class="card kpi">
        <span class="muted">Population eligibility</span>
        <strong id="benford-eligible"></strong>
    </div>

    <div class="card kpi">
        <span class="muted">Mean Absolute Deviation</span>
        <strong id="benford-mad"></strong>
    </div>

    <div class="card kpi">
        <span class="muted">Conformity assessment</span>
        <strong id="benford-status"></strong>
    </div>
</div>

<div class="panel">
    <h2>First-digit distribution: observed vs expected</h2>

    <p class="muted">
        Blue bars represent the observed transaction distribution.
        Gray bars represent the distribution expected under Benford's Law.
    </p>

    <div class="bars" id="benford-bars"></div>
</div>

<div class="panel">
    <h2>Stakeholder interpretation</h2>

    <p id="benford-conclusion"></p>

    <p>
        <strong>Largest deviation:</strong>
        <span id="benford-largest-deviation"></span>
    </p>

    <p class="muted">
        Benford's Law is a population-level screening test. A deviation does
        not prove fraud, and close conformity does not establish that every
        transaction is valid. Results should be considered together with
        duplicate-payment, access-control, threshold, and anomaly tests.
    </p>
</div>

<div class="panel">
    <h2>Digit-level analysis</h2>

    <div class="tablewrap">
        <table>
            <thead>
                <tr>
                    <th>First digit</th>
                    <th>Observed</th>
                    <th>Expected</th>
                    <th>Absolute difference</th>
                </tr>
            </thead>
            <tbody id="benford-table"></tbody>
        </table>
    </div>
</div>
</section>
<section id="cases" class="hidden"><div class="panel"><h2>Audit case explorer</h2><label>Filter by ERP: <select id="erp-filter"><option value="">All</option><option>AGRIS</option><option>CMIS</option><option>JDE</option><option>SAP</option></select></label><div class="tablewrap"><table><thead><tr><th>Invoice</th><th>Vendor</th><th>ERP</th><th>Amount</th><th>Risk</th><th>Anomaly percentile</th><th>Evidence</th></tr></thead><tbody id="case-table"></tbody></table></div><div id="case-detail" class="detail hidden"></div></div></section>
<section id="health" class="hidden"><div class="panel"><h2>Data-quality gate</h2><table><thead><tr><th>Check</th><th>Status</th><th>Actual</th><th>Expected</th></tr></thead><tbody id="quality"></tbody></table></div></section></main>
<script>
const D = __AUDIT_DATA__;

const money = value => new Intl.NumberFormat(
    "en-US",
    {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
    }
).format(value);

document.getElementById("transactions").textContent =
    D.summary.transactions.toLocaleString();

document.getElementById("total-value").textContent =
    money(D.summary.total_value);

document.getElementById("flagged-transactions").textContent =
    D.summary.flagged_transactions.toLocaleString();

document.getElementById("exception-rate").textContent =
    `${D.summary.exception_rate.toFixed(2)}%`;

document.getElementById("high").textContent =
    D.summary.high.toLocaleString();

document.getElementById("multi-indicator").textContent =
    D.summary.multi_indicator.toLocaleString();

document.getElementById("review-value").textContent =
    money(D.summary.review_value);

document.getElementById("duplicate-exposure").textContent =
    money(D.summary.duplicate_exposure);
document.getElementById("benford-sample").textContent =
    D.benford_kpis.sample_size.toLocaleString();

document.getElementById("benford-eligible").textContent =
    D.benford_kpis.eligible ? "Eligible" : "Not eligible";

document.getElementById("benford-mad").textContent =
    D.benford_kpis.mad.toFixed(4);

document.getElementById("benford-status").textContent =
    D.benford_kpis.status;

document.getElementById("benford-conclusion").textContent =
    D.benford_kpis.conclusion;

document.getElementById("benford-largest-deviation").textContent =
    `Digit ${D.benford_kpis.largest_deviation_digit}, ` +
    `${D.benford_kpis.largest_deviation_points.toFixed(2)} percentage points`;

document.getElementById("benford-table").innerHTML =
    D.benford.map(item => {
        const observed = `${(item.observed * 100).toFixed(2)}%`;
        const expected = `${(item.expected * 100).toFixed(2)}%`;
        const difference =
            `${(Math.abs(item.observed - item.expected) * 100).toFixed(2)}%`;

        return `
            <tr>
                <td>${item.digit}</td>
                <td>${observed}</td>
                <td>${expected}</td>
                <td>${difference}</td>
            </tr>
        `;
    }).join("");

const controlDetails = {
    EXACT_DUPLICATE: {
        label: "Potential duplicate invoice",
        action: "Validate invoice, payment status, and supporting documents",
    },
    SOD_CONFLICT: {
        label: "Segregation-of-duties conflict",
        action: "Review user access and approval history",
    },
    RAPID_BANK_CHANGE_PAYMENT: {
        label: "Payment after vendor bank change",
        action: "Validate bank-change authorization and payment ownership",
    },
    THRESHOLD_PROXIMITY: {
        label: "Approval-threshold proximity",
        action: "Review related invoices for possible transaction splitting",
    },
    ROUND_DOLLAR: {
        label: "Unusual round-dollar transaction",
        action: "Inspect business purpose and supporting documentation",
    },
    AFTER_HOURS: {
        label: "After-hours transaction entry",
        action: "Validate user activity, timing, and business justification",
    },
    THREE_WAY_MATCH: {
        label: "Three-way-match variance",
        action: "Compare invoice, purchase order, and receipt",
    },
};

const topErp = [...D.risk_by_erp]
    .sort((a, b) => b.exception_rate - a.exception_rate)[0];

const topCompany = [...D.risk_by_company]
    .sort((a, b) => b.exception_rate - a.exception_rate)[0];

const topControl = [...D.control_indicators]
    .sort(
        (a, b) =>
            b.unique_transactions - a.unique_transactions
    )[0];

const topControlDetails =
    controlDetails[topControl.test_id] || {
        label: topControl.test_id,
        action: "Perform targeted transaction review",
    };

const highRiskRate =
    D.summary.high / D.summary.transactions * 100;

const managementInsights = [
    {
        insight: "Highest ERP exception rate",
        evidence:
            `${topErp.source_system} has an exception rate of ` +
            `${topErp.exception_rate.toFixed(2)}%, with ` +
            `${topErp.flagged.toLocaleString()} flagged transactions.`,
        action:
            "Review the control mix and high-priority cases within this ERP.",
    },
    {
        insight: "Highest company exception rate",
        evidence:
            `${topCompany.company_code} has an exception rate of ` +
            `${topCompany.exception_rate.toFixed(2)}%, with ` +
            `${topCompany.high_risk.toLocaleString()} High/Critical cases.`,
        action:
            "Prioritize business-unit walkthroughs and supporting-document review.",
    },
    {
        insight: "Most frequent control indicator",
        evidence:
            `${topControlDetails.label} affected ` +
            `${topControl.unique_transactions.toLocaleString()} ` +
            `unique transactions.`,
        action: topControlDetails.action,
    },
    {
        insight: "High-priority review population",
        evidence:
            `${D.summary.high.toLocaleString()} cases, or ` +
            `${highRiskRate.toFixed(2)}% of analyzed transactions, ` +
            `are classified as High or Critical.`,
        action:
            "Assign the highest-scoring multi-indicator cases for immediate review.",
    },
    {
        insight: "Benford population assessment",
        evidence:
            `${D.benford_kpis.status}; MAD is ` +
            `${D.benford_kpis.mad.toFixed(4)}.`,
        action:
            D.benford_kpis.status === "Nonconformity"
                ? "Perform subgroup analysis by ERP, company, vendor, and period."
                : "Continue transaction-level tests; no broad digit anomaly was identified.",
    },
];

document.getElementById("management-insights").innerHTML =
    managementInsights
        .map(item => `
            <tr>
                <td><strong>${item.insight}</strong></td>
                <td>${item.evidence}</td>
                <td>${item.action}</td>
            </tr>
        `)
        .join("");

const erpRows = [...D.risk_by_erp]
    .sort((a, b) => b.exception_rate - a.exception_rate)
    .map(item => `
        <tr>
            <td><strong>${item.source_system}</strong></td>
            <td>${item.transactions.toLocaleString()}</td>
            <td>${item.flagged.toLocaleString()}</td>
            <td>${item.high_risk.toLocaleString()}</td>
            <td>${item.exception_rate.toFixed(2)}%</td>
            <td>${money(item.transaction_value)}</td>
        </tr>
    `)
    .join("");

document.getElementById("risk-by-erp").innerHTML = erpRows;

const companyRows = [...D.risk_by_company]
    .sort((a, b) => b.exception_rate - a.exception_rate)
    .map(item => `
        <tr>
            <td><strong>${item.company_code}</strong></td>
            <td>${item.transactions.toLocaleString()}</td>
            <td>${item.flagged.toLocaleString()}</td>
            <td>${item.high_risk.toLocaleString()}</td>
            <td>${item.exception_rate.toFixed(2)}%</td>
            <td>${money(item.transaction_value)}</td>
        </tr>
    `)
    .join("");

document.getElementById("risk-by-company").innerHTML = companyRows;

const controlRows = D.control_indicators
    .map(item => {
        const details = controlDetails[item.test_id] || {
            label: item.test_id,
            action: "Perform targeted transaction review",
        };

        return `
            <tr>
                <td><strong>${details.label}</strong></td>
                <td>${item.unique_transactions.toLocaleString()}</td>
                <td>${item.rule_triggers.toLocaleString()}</td>
                <td>${details.action}</td>
            </tr>
        `;
    })
    .join("");

document.getElementById("control-indicators").innerHTML =
    controlRows;

function row(c){return `<tr class="case-row" data-id="${c.invoice_id}"><td>${c.invoice_id}</td><td>${c.vendor_id||''}</td><td>${c.source_system}</td><td>${money(c.amount_usd)}</td><td>${c.risk_score}</td><td>${c.anomaly_percentile.toFixed(1)}</td><td>${c.rule_evidence}</td></tr>`}document.getElementById('top-cases').innerHTML=D.cases.slice(0,12).map(c=>`<tr><td>${c.invoice_id}</td><td>${c.source_system}</td><td>${money(c.amount_usd)}</td><td>${c.risk_score}</td><td class="tier ${c.risk_tier}">${c.risk_tier}</td><td>${c.rule_evidence}</td></tr>`).join('');
function renderCases(){const f=document.getElementById('erp-filter').value;document.getElementById('case-table').innerHTML=D.cases.filter(c=>!f||c.source_system===f).map(row).join('')}renderCases();document.getElementById('erp-filter').onchange=renderCases;document.getElementById('case-table').onclick=e=>{const tr=e.target.closest('tr');if(!tr)return;const c=D.cases.find(x=>x.invoice_id===tr.dataset.id);const box=document.getElementById('case-detail');box.textContent=c.case_narrative;box.classList.remove('hidden')};
document.getElementById('benford-bars').innerHTML=D.benford.map(x=>`<div class="pair"><div class="bar" style="height:${x.observed*300}%" title="Observed ${(x.observed*100).toFixed(1)}%"></div><div class="bar expected" style="height:${x.expected*300}%" title="Expected ${(x.expected*100).toFixed(1)}%"></div><label>${x.digit}</label></div>`).join('');document.getElementById('quality').innerHTML=D.quality.map(q=>`<tr><td>${q.check_name}</td><td class="${q.passed?'Low':'Critical'}">${q.passed?'PASS':'FAIL'}</td><td>${q.actual}</td><td>${q.expected}</td></tr>`).join('');
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('active'));b.classList.add('active');['overview','benford','cases','health'].forEach(id=>document.getElementById(id).classList.toggle('hidden',id!==b.dataset.tab))});</script></body></html>'''

