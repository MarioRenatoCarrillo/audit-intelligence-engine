DROP TABLE IF EXISTS canonical_invoices;
CREATE TABLE canonical_invoices AS
SELECT belnr AS invoice_id, lifnr AS vendor_id, invoice_number, invoice_date,
       posting_date, payment_date, wrbtr AS amount_usd, currency,
       bukrs AS company_code, 'SAP' AS source_system, entered_by, approved_by,
       entry_hour, po_number, receipt_amount, manual_entry, reversal_flag
FROM raw_sap
UNION ALL
SELECT rpdoc, rpan8, invoice_number, invoice_date, posting_date, payment_date,
       rpag, currency, rpco, 'JDE', entered_by, approved_by, entry_hour,
       po_number, receipt_amount, manual_entry, reversal_flag FROM raw_jde
UNION ALL
SELECT settlement_no, producer_no, invoice_number, invoice_date, posting_date,
       payment_date, settlement_amount, currency, location_code, 'AGRIS',
       entered_by, approved_by, entry_hour, po_number, receipt_amount,
       manual_entry, reversal_flag FROM raw_agris
UNION ALL
SELECT document_key, counterparty_id, invoice_number, invoice_date, posting_date,
       payment_date, net_amount, currency, entity_code, 'CMIS', entered_by,
       approved_by, entry_hour, po_number, receipt_amount, manual_entry,
       reversal_flag FROM raw_cmis;

