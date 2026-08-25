import json, os, requests
from document_template_engine import render_document_html
from local_pdf_engine import convert_html_to_pdf_local
from ghn168_sync_service import build_sheet_row_data, sync_document_to_sheets

doc_data = json.loads("{\"doc_no\": \"IV-202608-586\", \"doc_date\": \"25/08/2026\", \"due_date\": \"26/08/2026\", \"payment_terms\": \"1 \u0e27\u0e31\u0e19\", \"client_name\": \"\u0e1a\u0e23\u0e34\u0e29\u0e31\u0e17 \u0e40\u0e2d\u0e47\u0e21-\u0e04\u0e39\u0e25 \u0e40\u0e2e\u0e49\u0e32\u0e2a\u0e4c \u0e2d\u0e2d\u0e41\u0e01\u0e44\u0e19\u0e0b\u0e4c \u0e08\u0e33\u0e01\u0e31\u0e14\", \"client_tax_id\": \"0505568016475\", \"client_branch\": \"\u0e2a\u0e33\u0e19\u0e31\u0e01\u0e07\u0e32\u0e19\u0e43\u0e2b\u0e0d\u0e48 (00000)\", \"client_address\": \"21/6 \u0e2b\u0e21\u0e39\u0e48 2 \u0e15.\u0e23\u0e34\u0e21\u0e43\u0e15\u0e49 \u0e2d.\u0e41\u0e21\u0e48\u0e23\u0e34\u0e21 \u0e08.\u0e40\u0e0a\u0e35\u0e22\u0e07\u0e43\u0e2b\u0e21\u0e48 50180\", \"client_phone\": \"092-419-3953\", \"project_name\": \"Thailand Food Therapy FESTIVAL\", \"items\": [{\"desc\": \"\u0e16\u0e48\u0e32\u0e22\u0e20\u0e32\u0e1e Event 3 \u0e27\u0e31\u0e19\", \"qty\": 1, \"price\": 18000.0, \"amount\": 18000.0}], \"is_vat\": true, \"vat_rate\": 0.07, \"wht_rate\": 0.0, \"discount\": 0.0, \"signer_name\": \"\u0e19\u0e32\u0e22 \u0e21\u0e07\u0e04\u0e25 \u0e27\u0e07\u0e28\u0e4c\u0e2a\u0e01\u0e38\u0e25\u0e22\u0e32\u0e19\u0e19\u0e17\u0e4c\", \"show_signature\": true, \"show_seal\": true, \"remarks\": \"\"}")

# 1. Render HTML & Local Vector PDF
html = render_document_html('invoice', doc_data)
pdf_res = convert_html_to_pdf_local(html, doc_no=doc_data['doc_no'])

# 2. Sync to Google Sheets tab 'ใบวางบิล'
vps_pdf_url = f"https://srv1913532.hstgr.cloud/api/documents/pdf/{doc_data['doc_no']}"
sheet_name, row_values = build_sheet_row_data('invoice', doc_data, pdf_url=vps_pdf_url)

gas_url = "https://script.google.com/macros/s/AKfycbylMN5ot9w2_LfD4hgwnmTz4y7dSRLKdR-__0THDVzDivW-lUeF0YG25Hj3apCf0lWx/exec"
gas_payload = {
    "type": "sync",
    "spreadsheetId": "1vIc7kxO9q_FN2mmgyAYf8aly9lMdPRp7onqRaGx8y20",
    "sheetName": sheet_name,
    "values": row_values
}
try:
    r = requests.post(gas_url, json=gas_payload, timeout=60)
    sheets_res = r.json()
except Exception as e:
    sheets_res = {"status": "error", "message": str(e)}

res = {
    "status": "success",
    "pdf_res": pdf_res,
    "sheets_res": sheets_res,
    "pdf_url": vps_pdf_url
}
print('VPS_GEN_RESULT:' + json.dumps(res, ensure_ascii=False))
