#!/usr/bin/env python3
"""
================================================================================
GHN168 Document Template Engine
================================================================================
HTML/CSS Document Template Generator for:
1. Quotation (QT) - ใบเสนอราคา
2. Invoice / Billing Note (IV) - ใบวางบิล / ใบแจ้งหนี้
3. Receipt / Tax Invoice (RE) - ใบเสร็จรับเงิน / ใบกำกับภาษี
4. Withholding Tax Certificate (WHT / 50 ทวิ) - หนังสือรับรองการหักภาษี ณ ที่จ่าย

Features:
- Built-in Thai Baht Text conversion (100% precision with satang and million chunks)
- Tax and total calculations (Subtotal, Discount, Pre-VAT, VAT 7%, WHT 1-5%, Grand Total)
- Self-contained HTML output with Base64 embedded assets (Logo, Company Seal, Signatures)
- Optimized for PDF generation via PDFShift and modern browser printing
================================================================================
"""

import base64
from datetime import datetime
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
SIGNATURES_DIR = BASE_DIR / "signatures"

# Default Corporate Profile for GHN 168 Media & Creation Co., Ltd.
DEFAULT_COMPANY_INFO = {
    "name_th": "บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด",
    "name_en": "GHN 168 MEDIA & CREATION COMPANY LIMITED",
    "tax_id": "0505566010089",
    "branch": "สำนักงานใหญ่ (00000)",
    "address": "65/1 ถนนต้นขาม 2 ตำบลท่าศาลา อำเภอเมือง จังหวัดเชียงใหม่ 50000",
    "phone": "089-554-4355",
    "email": "ghn168media@gmail.com",
    "bank_name": "ธนาคารกรุงไทย (KTB)",
    "bank_account_no": "520-0-61960-2",
    "bank_account_name": "บจ. จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น",
    "default_signer": "นาย มงคล วงศ์สกุลยานนท์",
    "default_signer_title": "กรรมการผู้มีอำนาจลงนาม / Authorized Signature"
}

# In-memory Base64 Asset Cache
_ASSET_CACHE: Dict[str, str] = {}


def get_asset_base64(file_path: Union[str, Path]) -> str:
    """Reads a file and converts it to a Base64 data URI string."""
    path = Path(file_path)
    if not path.is_file():
        return ""
    str_path = str(path)
    if str_path in _ASSET_CACHE:
        return _ASSET_CACHE[str_path]

    mime_type = "image/png"
    ext = path.suffix.lower()
    if ext in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    elif ext == ".svg":
        mime_type = "image/svg+xml"
    elif ext == ".webp":
        mime_type = "image/webp"

    try:
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            data_uri = f"data:{mime_type};base64,{encoded}"
            _ASSET_CACHE[str_path] = data_uri
            return data_uri
    except Exception:
        return ""


def get_default_assets() -> Dict[str, str]:
    """Loads default GHN168 assets as Base64 URIs."""
    logo_path = ASSETS_DIR / "logo.png"
    seal_path = ASSETS_DIR / "GHN_company_seal.png"
    sig_keng_path = SIGNATURES_DIR / "sig_keng.png"
    sig_hom_path = SIGNATURES_DIR / "sig_hom.png"

    return {
        "logo_base64": get_asset_base64(logo_path),
        "seal_base64": get_asset_base64(seal_path),
        "sig_keng_base64": get_asset_base64(sig_keng_path),
        "sig_hom_base64": get_asset_base64(sig_hom_path),
    }


def thai_baht_text(amount: Union[float, int, str, None]) -> str:
    """
    Converts a monetary amount (Thai Baht) into official Thai spoken/written words.
    Example:
        1250.50 -> 'หนึ่งพันสองร้อยห้าสิบบาทห้าสิบสตางค์'
        1000000 -> 'หนึ่งล้านบาทถ้วน'
    """
    if amount is None or amount == "":
        return "ศูนย์บาทถ้วน"
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return "ศูนย์บาทถ้วน"

    if round(val, 2) == 0:
        return "ศูนย์บาทถ้วน"

    prefix = "ลบ" if val < 0 else ""
    val = abs(round(val, 2))

    units = ["", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"]
    positions = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน"]

    parts = f"{val:.2f}".split(".")
    int_str = parts[0]
    dec_str = parts[1]

    def convert_group(s: str, is_first_group: bool = False) -> str:
        res = ""
        length = len(s)
        for i, ch in enumerate(s):
            digit = int(ch)
            pos = length - i - 1
            if digit != 0:
                if pos == 1:
                    if digit == 1:
                        res += "สิบ"
                    elif digit == 2:
                        res += "ยี่สิบ"
                    else:
                        res += units[digit] + "สิบ"
                elif pos == 0:
                    if digit == 1:
                        if is_first_group and length == 1:
                            res += "หนึ่ง"
                        elif length == 1 and not is_first_group:
                            res += "เอ็ด"
                        elif length > 1:
                            res += "เอ็ด"
                        else:
                            res += "หนึ่ง"
                    else:
                        res += units[digit]
                else:
                    res += units[digit] + positions[pos]
        return res

    groups = []
    temp_int = int_str
    while len(temp_int) > 6:
        groups.append(temp_int[-6:])
        temp_int = temp_int[:-6]
    groups.append(temp_int)

    int_text = ""
    num_groups = len(groups)
    for idx in range(num_groups - 1, -1, -1):
        group_str = groups[idx]
        is_first = (idx == num_groups - 1)
        if int(group_str) > 0:
            group_conv = convert_group(group_str, is_first_group=is_first)
            int_text += group_conv + ("ล้าน" * idx)

    if int(int_str) > 0:
        baht_text = int_text + "บาท"
    else:
        baht_text = "ศูนย์บาท" if int(dec_str) > 0 else ""

    satang_val = int(dec_str)
    if satang_val == 0:
        satang_text = "ถ้วน"
    else:
        d1 = int(dec_str[0])
        d2 = int(dec_str[1])
        s_res = ""
        if d1 != 0:
            if d1 == 1:
                s_res += "สิบ"
            elif d1 == 2:
                s_res += "ยี่สิบ"
            else:
                s_res += units[d1] + "สิบ"
        if d2 != 0:
            if d2 == 1 and d1 != 0:
                s_res += "เอ็ด"
            else:
                s_res += units[d2]
        satang_text = s_res + "สตางค์"

    return prefix + baht_text + satang_text


def calculate_document_totals(
    items: List[Dict[str, Any]],
    is_vat: bool = True,
    vat_rate: float = 0.07,
    wht_rate: float = 0.0,
    discount: float = 0.0
) -> Dict[str, Any]:
    """
    Computes Subtotal, Discount, Pre-VAT, VAT, WHT, Grand Total, and Thai Baht words.
    """
    subtotal = 0.0
    processed_items = []

    for idx, item in enumerate(items, start=1):
        desc = str(item.get("desc") or item.get("description") or f"รายการที่ {idx}").strip()
        if item.get("amount") is not None:
            line_total = round(float(item.get("amount") or 0.0), 2)
        elif item.get("line_total") is not None:
            line_total = round(float(item.get("line_total") or 0.0), 2)
        else:
            qty = float(item.get("qty") or item.get("quantity") or 1.0)
            price = float(item.get("price") or item.get("unit_price") or 0.0)
            line_total = round(qty * price, 2)

        worker = str(item.get("worker") or item.get("staff") or "เก่ง").strip()
        subtotal += line_total

        processed_items.append({
            "index": idx,
            "desc": desc,
            "amount": line_total,
            "line_total": line_total,
            "worker": worker
        })

    subtotal = round(subtotal, 2)
    discount = round(float(discount or 0.0), 2)
    pre_vat = max(0.0, round(subtotal - discount, 2))

    vat_amount = round(pre_vat * vat_rate, 2) if is_vat else 0.0
    gross_amount = round(pre_vat + vat_amount, 2)

    # WHT is calculated on pre-vat basis (standard Thai revenue code)
    wht_percent = float(wht_rate or 0.0)
    wht_amount = round(pre_vat * (wht_percent / 100.0), 2) if wht_percent > 0 else 0.0

    net_total = round(gross_amount - wht_amount, 2)

    return {
        "items": processed_items,
        "subtotal": subtotal,
        "discount": discount,
        "pre_vat": pre_vat,
        "is_vat": is_vat,
        "vat_rate": round(vat_rate * 100, 1),
        "vat_amount": vat_amount,
        "gross_amount": gross_amount,
        "wht_rate": wht_percent,
        "wht_amount": wht_amount,
        "net_total": net_total,
        "grand_total": net_total,
        "baht_text": thai_baht_text(net_total)
    }


def format_currency(val: Union[float, int, str]) -> str:
    """Format number as standard currency string e.g. 1,250.00"""
    try:
        num = float(val)
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return "0.00"


# ------------------------------------------------------------------------------
# Core CSS Styles for Printable A4 Documents
# ------------------------------------------------------------------------------
BASE_DOCUMENT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Prompt:wght@300;400;500;600;700;800&family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

@page {
  size: A4 portrait;
  margin: 0;
}

* {
  box-sizing: border-box;
  -webkit-print-color-adjust: exact !important;
  print-color-adjust: exact !important;
}

body {
  margin: 0;
  padding: 0;
  background-color: #f3f4f6;
  font-family: 'Outfit', 'Prompt', 'Sukhumvit Set', 'IBM Plex Sans Thai', sans-serif;
  color: #111827;
  font-size: 12px;
  line-height: 1.45;
}

h1, h2, h3, h4, h5, h6, .doc-badge-title, .doc-badge-title-en, .company-name-th, .company-name-en, .items-table th, .totals-table, .meta-table td:last-child {
  font-family: 'Outfit', 'Prompt', sans-serif;
}

.mono {
  font-family: 'Outfit', 'Prompt', 'JetBrains Mono', monospace;
  letter-spacing: -0.2px;
}

.page-container {
  width: 210mm;
  min-height: 297mm;
  padding: 12mm 14mm;
  margin: 15px auto;
  background: #ffffff;
  position: relative;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  box-sizing: border-box;
}

@media print {
  body {
    background: transparent;
    margin: 0;
    padding: 0;
  }
  .page-container {
    width: 210mm;
    min-height: 297mm;
    margin: 0;
    padding: 12mm 14mm;
    box-shadow: none;
    page-break-after: avoid;
    page-break-inside: avoid;
  }
}

/* Header Section */
.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 2px solid #111827;
  padding-bottom: 14px;
  margin-bottom: 16px;
}

.company-info {
  flex: 1;
  max-width: 52%;
}

.company-logo {
  max-height: 52px;
  width: auto;
  margin-bottom: 6px;
  display: block;
}

.company-name-th {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
}

.company-name-en {
  font-size: 10.5px;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0.2px;
  margin-bottom: 6px;
}

.company-details {
  font-size: 10.5px;
  color: #334155;
  line-height: 1.45;
}

.doc-meta {
  width: 45%;
  text-align: right;
  flex-shrink: 0;
}

.doc-badge-title {
  display: inline-block;
  background: #0f172a;
  color: #ffffff;
  padding: 6px 14px;
  font-size: 15px;
  font-weight: 800;
  border-radius: 4px;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
  white-space: nowrap;
}

.doc-badge-title-en {
  font-size: 10.5px;
  font-weight: 700;
  color: #475569;
  letter-spacing: 1px;
  margin-bottom: 10px;
  white-space: nowrap;
}

.meta-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 6px;
}

.meta-table td {
  padding: 3px 6px;
  font-size: 11px;
  white-space: nowrap !important;
  word-break: keep-all !important;
}

.meta-table td.mono {
  white-space: nowrap !important;
  word-break: keep-all !important;
}

.meta-table td:first-child {
  color: #64748b;
  text-align: right;
  font-weight: 500;
  white-space: nowrap !important;
  word-break: keep-all !important;
}

.meta-table td:last-child {
  text-align: right;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap !important;
  word-break: keep-all !important;
}

/* Client & Project Cards */
.client-project-grid {
  display: flex;
  gap: 14px;
  margin-bottom: 16px;
}

.info-card {
  flex: 1;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 10px 14px;
}

.info-card-header {
  font-size: 11px;
  font-weight: 700;
  color: #0284c7;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
  border-bottom: 1px dashed #cbd5e1;
  padding-bottom: 4px;
}

.info-card-content {
  font-size: 11px;
  line-height: 1.45;
  color: #1e293b;
}

/* Document Table */
.items-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 14px;
}

.items-table th {
  background: #0f172a;
  color: #ffffff;
  padding: 8px 10px;
  font-size: 11px;
  font-weight: 600;
  text-align: left;
  border: 1px solid #0f172a;
}

.items-table th.center { text-align: center; }
.items-table th.right { text-align: right; }

.items-table td {
  padding: 8px 10px;
  font-size: 11px;
  border: 1px solid #e2e8f0;
  vertical-align: top;
  color: #1e293b;
}

.items-table tr:nth-child(even) td {
  background: #fcfdfd;
}

.items-table td.center { text-align: center; }
.items-table td.right { text-align: right; }

/* Totals Summary */
.totals-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
}

.baht-text-box {
  flex: 1;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 11.5px;
  line-height: 1.4;
}

.baht-text-label {
  font-size: 10px;
  font-weight: 600;
  color: #166534;
  text-transform: uppercase;
  margin-bottom: 2px;
}

.baht-text-value {
  font-weight: 700;
  color: #15803d;
  font-size: 12px;
}

.totals-table {
  width: 310px;
  border-collapse: collapse;
}

.totals-table td {
  padding: 5px 8px;
  font-size: 11px;
}

.totals-table td:first-child {
  text-align: right;
  color: #475569;
  font-weight: 500;
}

.totals-table td:last-child {
  text-align: right;
  font-weight: 700;
  color: #0f172a;
}

.totals-table tr.grand-total td {
  background: #0f172a;
  color: #ffffff;
  font-size: 13px;
  font-weight: 800;
  padding: 8px 10px;
  border-radius: 4px;
}

/* Terms & Signatures */
.terms-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 10.5px;
  color: #334155;
  margin-bottom: 24px;
  line-height: 1.45;
}

.terms-title {
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 4px;
}

.signatures-container {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  align-items: flex-end;
  margin-top: 28px;
  padding-top: 10px;
  position: relative;
}

.signature-col-empty {
  min-height: 1px;
}

.seal-watermark-center {
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
  min-height: 90px;
}

.seal-watermark-center img,
.seal-watermark {
  width: 148px;
  max-width: 150px;
  height: auto;
  max-height: 120px;
  opacity: 0.88;
  mix-blend-mode: multiply;
  pointer-events: none;
  display: inline-block;
}

.signature-card {
  width: 100%;
  max-width: 220px;
  margin-left: auto;
  text-align: center;
  position: relative;
}

.signature-img {
  max-height: 62px;
  width: auto;
  display: block;
  margin: 0 auto -10px auto;
  mix-blend-mode: multiply;
  position: relative;
  z-index: 2;
}

.signature-line {
  border-bottom: 1px dashed #64748b;
  width: 85%;
  margin: 12px auto 6px auto;
}

.signer-name {
  font-size: 11.5px;
  font-weight: 700;
  color: #0f172a;
}

.signer-title {
  font-size: 9.5px;
  color: #64748b;
}

/* WHT Specific Styles */
.wht-header-badge {
  text-align: center;
  border: 2px solid #0f172a;
  padding: 10px;
  margin-bottom: 16px;
  background: #f8fafc;
}
.wht-header-title {
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: 0.5px;
}
.wht-header-subtitle {
  font-size: 10.5px;
  color: #475569;
}
.wht-box-table {
  width: 100%;
  border: 1px solid #0f172a;
  border-collapse: collapse;
  margin-bottom: 12px;
  font-size: 11px;
}
.wht-box-table td {
  border: 1px solid #cbd5e1;
  padding: 8px 12px;
  vertical-align: top;
}
.wht-box-label {
  width: 180px;
  background: #f1f5f9;
  font-weight: 700;
  color: #1e293b;
  border-right: 1px solid #94a3b8 !important;
}
"""


# ------------------------------------------------------------------------------
# HTML Renderers
# ------------------------------------------------------------------------------
def generate_financial_document_html(doc_type: str, data: Dict[str, Any]) -> str:
    """Main generator function to produce financial document HTML with strict signer binding."""
    return _render_standard_document_html(doc_type, data)


def render_quotation_html(data: Dict[str, Any]) -> str:
    """Generates complete HTML for Quotation (QT)."""
    return _render_standard_document_html("quotation", data)


def render_invoice_html(data: Dict[str, Any]) -> str:
    """Generates complete HTML for Invoice / Billing Note (IV)."""
    return _render_standard_document_html("invoice", data)


def render_receipt_html(data: Dict[str, Any]) -> str:
    """Generates complete HTML for Receipt / Tax Invoice (RE)."""
    return _render_standard_document_html("receipt", data)


def _render_standard_document_html(doc_type: str, data: Dict[str, Any]) -> str:
    """Internal helper to render QT, IV, or RE standard documents."""
    assets = get_default_assets()
    company = {**DEFAULT_COMPANY_INFO, **data.get("company", {})}

    # Document Type Meta Titles
    if doc_type == "quotation":
        doc_badge_th = "ใบเสนอราคา"
        doc_badge_en = "QUOTATION"
        doc_prefix = "QT"
        payment_due_label = "ยืนราคาถึงวันที่ / Valid Until"
    elif doc_type == "invoice":
        doc_badge_th = "ใบวางบิล / ใบแจ้งหนี้"
        doc_badge_en = "INVOICE / BILLING NOTE"
        doc_prefix = "IV"
        payment_due_label = "ครบกำหนดชำระ / Due Date"
    elif doc_type == "receipt":
        doc_badge_th = "ใบเสร็จรับเงิน / ใบกำกับภาษี"
        doc_badge_en = "RECEIPT / TAX INVOICE"
        doc_prefix = "RE"
        payment_due_label = "วันที่รับชำระ / Paid Date"
    else:
        doc_badge_th = "เอกสารทางการเงิน"
        doc_badge_en = "FINANCIAL DOCUMENT"
        doc_prefix = "DOC"
        payment_due_label = "วันที่ครบกำหนด / Due Date"

    # Meta Info
    doc_no = data.get("doc_no") or f"{doc_prefix}-{datetime.now().strftime('%Y%m')}-001"
    doc_date = data.get("doc_date") or datetime.now().strftime("%d/%m/%Y")
    due_date = data.get("due_date") or doc_date
    ref_doc_no = data.get("ref_doc_no") or data.get("ref_invoice_no") or data.get("invoice_no") or data.get("ref_no")
    ref_row_html = f"""
        <tr>
          <td>อ้างอิงเอกสาร / Ref:</td>
          <td class="mono">{ref_doc_no}</td>
        </tr>""" if ref_doc_no else ""

    # Client Info
    client_name = data.get("client_name") or data.get("customer_name") or "ลูกค้าทั่วไป"
    client_tax_id = data.get("client_tax_id") or data.get("customer_tax_id") or "-"
    client_branch = data.get("client_branch") or "สำนักงานใหญ่ (00000)"
    client_address = data.get("client_address") or data.get("customer_address") or "-"
    client_phone = data.get("client_phone") or data.get("customer_phone") or "-"

    # Project & Payment Terms
    project_name = data.get("project_name") or data.get("description") or "บริการงานสื่อและโปรดักชั่น"
    payment_terms = data.get("payment_terms") or "เงินสด / โอนเงินผ่านบัญชีธนาคาร"
    remarks = data.get("remarks") or ""

    # Totals calculation
    items = data.get("items") or [
        {"desc": project_name, "amount": float(data.get("subtotal") or data.get("amount") or 0.0)}
    ]
    is_vat = bool(data.get("is_vat", True))
    vat_rate = float(data.get("vat_rate", 0.07))
    wht_rate = float(data.get("wht_rate", 0.0))
    discount = float(data.get("discount", 0.0))
    discount_desc = str(data.get("discount_desc") or "").strip()

    totals = calculate_document_totals(
        items=items,
        is_vat=is_vat,
        vat_rate=vat_rate,
        wht_rate=wht_rate,
        discount=discount
    )

    # Logo, Seal, Signatures
    logo_src = data.get("logo_base64") or assets.get("logo_base64")
    seal_src = data.get("seal_base64") or assets.get("seal_base64")

    # Strict Signer Binding (บอสเก่ง / นาย มงคล วงศ์สกุลยานนท์ vs บอสหอม / นาย ณัฐวัฒน์ ปวงจันทร์หอม)
    signer_input = str(data.get("signer_name") or company["default_signer"]).strip()
    signer_title = data.get("signer_title") or company["default_signer_title"]

    if "หอม" in signer_input or "ณัฐวัฒน์" in signer_input or "hom" in signer_input.lower():
        signer_name = "นาย ณัฐวัฒน์ ปวงจันทร์หอม"
        sig_src = data.get("sig_base64") or assets.get("sig_hom_base64")
    elif "เก่ง" in signer_input or "มงคล" in signer_input or "keng" in signer_input.lower():
        signer_name = "นาย มงคล วงศ์สกุลยานนท์"
        sig_src = data.get("sig_base64") or assets.get("sig_keng_base64")
    else:
        signer_name = signer_input
        sig_src = data.get("sig_base64") or assets.get("sig_keng_base64")

    show_seal = data.get("show_seal", True)
    show_signature = data.get("show_signature", True)

    # Render items HTML rows (3 columns: [ลำดับ | รายการ / รายละเอียด | จำนวนเงิน])
    item_rows = []
    for it in totals["items"]:
        item_rows.append(f"""
        <tr>
          <td class="center mono" style="width: 50px;">{it['index']}</td>
          <td>
            <strong>{it['desc']}</strong>
          </td>
          <td class="right mono" style="width: 140px;"><strong>{format_currency(it['line_total'])}</strong></td>
        </tr>
        """)
    items_tbody_html = "".join(item_rows)

    # Render Totals Rows
    discount_row_html = ""
    if totals["discount"] > 0:
        disc_label = f"ส่วนลด / Discount ({discount_desc})" if discount_desc else "ส่วนลด / Discount"
        discount_row_html = f"""
        <tr>
          <td>{disc_label}</td>
          <td class="mono" style="color: #dc2626;">-{format_currency(totals['discount'])} ฿</td>
        </tr>
        """

    vat_row_html = ""
    if totals["is_vat"]:
        vat_row_html = f"""
        <tr>
          <td>ภาษีมูลค่าเพิ่ม / VAT ({totals['vat_rate']:g}%)</td>
          <td class="mono">{format_currency(totals['vat_amount'])} ฿</td>
        </tr>
        """

    wht_row_html = ""
    if totals["wht_rate"] > 0:
        wht_row_html = f"""
        <tr>
          <td>หักภาษี ณ ที่จ่าย / WHT ({totals['wht_rate']:g}%)</td>
          <td class="mono" style="color: #dc2626;">-{format_currency(totals['wht_amount'])} ฿</td>
        </tr>
        """

    # Terms and Notes section
    terms_html = ""
    if doc_type == "quotation":
        terms_html = f"""
        <div class="terms-box">
          <div class="terms-title">เงื่อนไขและข้อตกลง (Terms & Conditions):</div>
          <div>• ชำระมัดจำ 30-50% ของมูลค่าโครงการเพื่อสำรองคิวงานและยืนยันการว่าจ้าง</div>
          <div>• กำหนดยืนราคา 30 วันนับจากวันที่ออกเอกสาร</div>
          {f"<div>• หมายเหตุ: {remarks}</div>" if remarks else ""}
          <div style="margin-top: 4px; color: #0284c7;">* บัญชีรับโอน: {company['bank_name']} เลขที่ <strong>{company['bank_account_no']}</strong> ({company['bank_account_name']})</div>
        </div>
        """
    elif doc_type in ["invoice", "receipt"]:
        terms_html = f"""
        <div class="terms-box">
          <div class="terms-title">รายละเอียดการชำระเงิน (Payment Details):</div>
          <div>• บัญชีธนาคาร: <strong>{company['bank_name']}</strong> เลขที่บัญชี <strong>{company['bank_account_no']}</strong></div>
          <div>• ชื่อบัญชี: <strong>{company['bank_account_name']}</strong></div>
          {f"<div>• หมายเหตุ: {remarks}</div>" if remarks else ""}
          <div style="margin-top: 2px; font-size: 9.5px; color: #64748b;">* ในกรณีชำระด้วยเช็ค เอกสารนี้จะสมบูรณ์เมื่อเช็คได้เรียกเก็บเงินผ่านธนาคารเรียบร้อยแล้ว</div>
        </div>
        """

    # Full HTML assembly
    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{doc_badge_th} - {doc_no}</title>
  <style>
    {BASE_DOCUMENT_CSS}
  </style>
</head>
<body>

<div class="page-container">
  
  <!-- Header -->
  <div class="doc-header">
    <div class="company-info">
      {'<img src="' + logo_src + '" class="company-logo" alt="Logo">' if logo_src else ''}
      <div class="company-name-th">{company['name_th']}</div>
      <div class="company-name-en">{company['name_en']}</div>
      <div class="company-details">
        เลขประจำตัวผู้เสียภาษี: <span class="mono" style="font-weight:700;">{company['tax_id']}</span> ({company['branch']})<br>
        ที่อยู่: {company['address']}<br>
        โทรศัพท์: {company['phone']} | อีเมล: {company['email']}
      </div>
    </div>
    
    <div class="doc-meta">
      <div class="doc-badge-title">{doc_badge_th}</div>
      <div class="doc-badge-title-en">{doc_badge_en}</div>
      
      <table class="meta-table">
        <tr>
          <td>เลขที่เอกสาร / No:</td>
          <td class="mono" style="font-size: 13px; color: #0284c7;">{doc_no}</td>
        </tr>{ref_row_html}
        <tr>
          <td>วันที่ / Date:</td>
          <td class="mono">{doc_date}</td>
        </tr>
        <tr>
          <td>{payment_due_label}:</td>
          <td class="mono">{due_date}</td>
        </tr>
      </table>
    </div>
  </div>

  <!-- Client & Project Info Cards -->
  <div class="client-project-grid">
    <div class="info-card">
      <div class="info-card-header">ข้อมูลลูกค้า (Customer Details)</div>
      <div class="info-card-content">
        <strong style="font-size: 12px; color: #0f172a;">{client_name}</strong><br>
        เลขประจำตัวผู้เสียภาษี: <span class="mono" style="font-weight: 700;">{client_tax_id}</span> ({client_branch})<br>
        ที่อยู่: {client_address}<br>
        โทรศัพท์: {client_phone}
      </div>
    </div>

    <div class="info-card">
      <div class="info-card-header">รายละเอียดงาน & เงื่อนไข (Project & Terms)</div>
      <div class="info-card-content">
        <strong>โครงการ:</strong> {project_name}<br>
        <strong>เงื่อนไขการชำระ:</strong> {payment_terms}<br>
        <strong>ผู้ติดต่อประสานงาน:</strong> ทีมงาน GHN168 Media
      </div>
    </div>
  </div>

  <!-- Items Table (3 Columns) -->
  <table class="items-table">
    <thead>
      <tr>
        <th class="center" style="width: 50px;">ลำดับ</th>
        <th>รายการ / รายละเอียด (Description)</th>
        <th class="right" style="width: 140px;">จำนวนเงิน</th>
      </tr>
    </thead>
    <tbody>
      {items_tbody_html}
    </tbody>
  </table>

  <!-- Totals Section -->
  <div class="totals-section">
    <div class="baht-text-box">
      <div class="baht-text-label">จำนวนเงินตัวอักษร (Thai Baht Text):</div>
      <div class="baht-text-value">{totals['baht_text']}</div>
    </div>

    <table class="totals-table">
      <tr>
        <td>รวมเงิน / Subtotal</td>
        <td class="mono">{format_currency(totals['subtotal'])} ฿</td>
      </tr>
      {discount_row_html}
      {vat_row_html}
      {wht_row_html}
      <tr class="grand-total">
        <td>ยอดเงินสุทธิ / Net Total</td>
        <td class="mono">{format_currency(totals['net_total'])} ฿</td>
      </tr>
    </table>
  </div>

  <!-- Terms & Notes -->
  {terms_html}

  <!-- Signatures Section -->
  <div class="signatures-container">
    <div class="signature-col-empty"></div>

    <div class="seal-watermark-center">
      {'<img src="' + seal_src + '" class="seal-watermark" alt="Company Seal">' if show_seal and seal_src else ''}
    </div>

    <div class="signature-card">
      {'<img src="' + sig_src + '" class="signature-img" alt="Signature">' if show_signature and sig_src else '<div style="height:55px;"></div>'}
      <div class="signature-line"></div>
      <div class="signer-name">{signer_name}</div>
      <div class="signer-title">{signer_title}</div>
    </div>
  </div>

</div>

</body>
</html>"""
    return html


def render_wht_html(data: Dict[str, Any]) -> str:
    """
    Generates complete HTML for Withholding Tax Certificate (50 ทวิ - WHT).
    """
    assets = get_default_assets()
    company = {**DEFAULT_COMPANY_INFO, **data.get("company", {})}

    # Payer Info (GHN 168 or Custom)
    payer_name = data.get("payer_name") or company["name_th"]
    payer_tax_id = data.get("payer_tax_id") or company["tax_id"]
    payer_address = data.get("payer_address") or company["address"]

    # Payee Info (Vendor / Freelancer / Partner)
    payee_name = data.get("payee_name") or data.get("vendor_name") or data.get("client_name") or data.get("customer_name") or "-"
    payee_tax_id = data.get("payee_tax_id") or data.get("id_card_no") or data.get("client_tax_id") or data.get("customer_tax_id") or "-"
    payee_address = data.get("payee_address") or data.get("client_address") or data.get("customer_address") or "-"


    # Document Meta
    doc_no = data.get("doc_no") or f"WHT-{datetime.now().strftime('%Y%m')}-001"
    doc_date = data.get("doc_date") or datetime.now().strftime("%d/%m/%Y")

    # Income & Tax Details
    income_desc = data.get("income_desc") or data.get("description") or "ค่าบริการและงานตัดต่อผลิตสื่อ"
    gross_amount = float(data.get("gross_amount") or data.get("amount") or 0.0)
    wht_rate = float(data.get("wht_rate") or 3.0)
    tax_amount = round(gross_amount * (wht_rate / 100.0), 2)
    net_paid = round(gross_amount - tax_amount, 2)
    tax_baht_text = thai_baht_text(tax_amount)

    signer_name = "ณัฐนรี วงศ์สกุลยานนท์"
    signer_title = "ผู้มีหน้าที่หักภาษี ณ ที่จ่าย / ผู้มีอำนาจลงนาม"

    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>หนังสือรับรองการหักภาษี ณ ที่จ่าย (50 ทวิ) - {doc_no}</title>
  <style>
    {BASE_DOCUMENT_CSS}
  </style>
</head>
<body>

<div class="page-container">

  <div class="wht-header-badge">
    <div class="wht-header-title">หนังสือรับรองการหักภาษี ณ ที่จ่าย (50 ทวิ)</div>
    <div class="wht-header-subtitle">ตามมาตรา 50 ทวิ แห่งประมวลรัษฎากร (ฉบับสำหรับผู้ถูกหักภาษี ณ ที่จ่าย)</div>
  </div>

  <table class="wht-box-table">
    <tr>
      <td class="wht-box-label">ผู้มีหน้าที่หักภาษี ณ ที่จ่าย (Payer):</td>
      <td>
        <strong style="font-size: 12px; color: #0f172a;">{payer_name}</strong><br>
        เลขประจำตัวผู้เสียภาษี: <span class="mono" style="font-weight: 700;">{payer_tax_id}</span><br>
        ที่อยู่: {payer_address}
      </td>
    </tr>
    <tr>
      <td class="wht-box-label">ผู้ถูกหักภาษี ณ ที่จ่าย (Payee):</td>
      <td>
        <strong style="font-size: 12px; color: #0f172a;">{payee_name}</strong><br>
        เลขประจำตัวผู้เสียภาษี / บัตรประชาชน: <span class="mono" style="font-weight: 700;">{payee_tax_id}</span><br>
        ที่อยู่: {payee_address}
      </td>
    </tr>
    <tr>
      <td class="wht-box-label">ข้อมูลเอกสาร (Document):</td>
      <td>
        <div style="display: flex; gap: 30px;">
          <div>เลขที่เอกสาร: <strong class="mono" style="color: #0284c7;">{doc_no}</strong></div>
          <div>วันที่จ่ายเงิน: <strong class="mono">{doc_date}</strong></div>
        </div>
      </td>
    </tr>
  </table>

  <!-- Money Table -->
  <table class="items-table" style="margin-top: 10px;">
    <thead>
      <tr>
        <th>ประเภทเงินได้พึงประเมินที่จ่าย (Type of Income)</th>
        <th class="center" style="width: 110px;">อัตราภาษี (Rate)</th>
        <th class="right" style="width: 150px;">จำนวนเงินที่จ่าย (Gross)</th>
        <th class="right" style="width: 150px;">ภาษีที่หักและนำส่ง (Tax)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="padding: 12px 10px;">
          <strong>{income_desc}</strong><br>
          <span style="font-size: 10px; color: #64748b;">(ตามมาตรา 40(8) ค่าบริการ / จ้างทำของ / ภ.ง.ด.3 / ภ.ง.ด.53)</span>
        </td>
        <td class="center mono" style="vertical-align: middle;">{wht_rate:g}%</td>
        <td class="right mono" style="vertical-align: middle;"><strong>{format_currency(gross_amount)}</strong></td>
        <td class="right mono" style="vertical-align: middle; color: #dc2626;"><strong>{format_currency(tax_amount)}</strong></td>
      </tr>
      <tr style="background: #f8fafc; font-weight: 700;">
        <td colspan="2" style="text-align: right; padding: 10px;">รวมเงินที่จ่ายและภาษีที่นำส่ง (Total)</td>
        <td class="right mono" style="padding: 10px;">{format_currency(gross_amount)} ฿</td>
        <td class="right mono" style="padding: 10px; color: #dc2626;">{format_currency(tax_amount)} ฿</td>
      </tr>
    </tbody>
  </table>

  <div class="baht-text-box" style="margin-bottom: 16px;">
    <div class="baht-text-label">ตัวหนังสือยอดเงินภาษีสุทธิที่นำส่ง (Net Tax in Words):</div>
    <div class="baht-text-value">{tax_baht_text}</div>
  </div>

  <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; font-size: 10.5px; color: #475569; margin-bottom: 24px;">
    <div><strong>ยอดจ่ายเงินสุทธิให้ผู้รับเงิน (Net Paid Amount):</strong> <span class="mono" style="font-size: 12px; font-weight: 700; color: #166534;">{format_currency(net_paid)} บาท</span></div>
    <div style="margin-top: 4px; font-size: 9.5px;">ขอรับรองว่าข้อความและตัวเลขภาษีที่หักและนำส่งไว้นี้ถูกต้องตรงกับความเป็นจริงทุกประการ</div>
  </div>

  <div class="signatures-container" style="justify-content: flex-end; margin-top: 30px;">
    <div class="signature-card" style="width: 250px;">
      <div style="height: 55px;"></div>
      <div class="signature-line"></div>
      <div class="signer-name">{signer_name}</div>
      <div class="signer-title">{signer_title}</div>
    </div>
  </div>

</div>

</body>
</html>"""
    return html


def render_document_html(doc_type: str, data: Dict[str, Any]) -> str:
    """
    Main dispatch function to render HTML for any supported document type:
    'quotation', 'invoice', 'receipt', or 'wht'.
    """
    norm_type = str(doc_type).lower().strip()
    if norm_type in ["quotation", "qt"]:
        return render_quotation_html(data)
    elif norm_type in ["invoice", "iv", "billing", "bill"]:
        return render_invoice_html(data)
    elif norm_type in ["receipt", "re", "tax_invoice"]:
        return render_receipt_html(data)
    elif norm_type in ["wht", "50bis", "50tawi", "50_tawi", "withholding"]:
        return render_wht_html(data)
    else:
        raise ValueError(f"Unsupported document type: '{doc_type}'. Expected 'quotation', 'invoice', 'receipt', or 'wht'.")


if __name__ == "__main__":
    print("Testing GHN168 Document Template Engine...")
    sample_qt = render_document_html("quotation", {
        "doc_no": "QT-202608-001",
        "client_name": "บริษัท ตัวอย่างทดสอบ จำกัด",
        "items": [{"desc": "ถ่ายวิดีโอและตัดต่อโปรดักชั่น", "qty": 1, "price": 25000}],
        "is_vat": True,
        "wht_rate": 3.0
    })
    print(f"Generated Quotation HTML length: {len(sample_qt)} chars")
    assert "<!DOCTYPE html>" in sample_qt
    assert "บริษัท ตัวอย่างทดสอบ จำกัด" in sample_qt
    print("Template Engine test completed successfully!")
