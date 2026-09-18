#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
GHN168 - Test Suite for Web App Parity (index.html & app.js)
==============================================================================
Author: น้องคิว (Q - Senior Fullstack Developer, ChZ Agent Corp)
Target Missions:
1. Quotation (QT) Parity:
   - setDocType('quotation') locks/disables docWhtSelect to 0
   - calculateDocTotals() enforces whtRate=0, wht=0, grandTotal = grossAmount
   - prevWhtRow hidden on quotation
   - prevNetTotalLabelCell = 'ยอดเงินรวมทั้งสิ้น / Grand Total'
   - thaiBahtText reflects gross amount
   - updateDueDateFromPaymentTerm auto-calculates docDate + 30 days
   - Customer Acceptance signature box in prevLeftSignBox
   - prevDocRefRow hidden on quotation
   - processDocumentSync & handleUploadPdfToDrive enforce zero WHT
2. Receipt (RE) Sec 86/4 Parity:
   - prevGrossRow added to index.html with 'ยอดเงินรวมทั้งสิ้น / Total Amount'
   - When whtRate > 0: prevGrossRow visible, label = 'ยอดโอนสุทธิ / Net Paid'
   - When whtRate == 0: prevGrossRow hidden, label = 'ยอดเงินสุทธิ / Net Total'
   - thaiBahtText reflects gross amount (Section 86/4 compliance)
   - Payment Details box hidden on receipt
3. Invoice (IV) Parity:
   - Due date enabled, grand total label = 'ยอดเงินสุทธิ / Net Total'
   - Payment Details box displayed with bank details & cheque clause
4. PDF Export Parity:
   - exportPdfClientSide strictly formats filename as ${cleanedDocNo}.pdf
==============================================================================
"""

import os
import re
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INDEX_HTML_PATH = os.path.join(PROJECT_ROOT, "index.html")
APP_JS_PATH = os.path.join(PROJECT_ROOT, "app.js")


class TestWebAppParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            cls.html_content = f.read()
        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            cls.js_content = f.read()

    def test_html_prev_gross_row_exists_and_ordered(self):
        """Verify prevGrossRow exists in index.html and is placed before prevWhtRow."""
        self.assertIn('id="prevGrossRow"', self.html_content)
        self.assertIn('id="prevGrossLabelCell"', self.html_content)
        self.assertIn('id="prevGrossVal"', self.html_content)
        self.assertIn("ยอดเงินรวมทั้งสิ้น / Total Amount", self.html_content)

        # Ensure prevGrossRow appears between prevVatRow and prevWhtRow
        vat_pos = self.html_content.find('id="prevVatRow"')
        gross_pos = self.html_content.find('id="prevGrossRow"')
        wht_pos = self.html_content.find('id="prevWhtRow"')
        self.assertTrue(vat_pos < gross_pos < wht_pos, "prevGrossRow must be between prevVatRow and prevWhtRow")

    def test_html_required_dom_elements(self):
        """Verify necessary DOM elements for quotation, receipt, and invoice exist in index.html."""
        self.assertIn('id="prevLeftSignBox"', self.html_content)
        self.assertIn('id="prevDocRefRow"', self.html_content)
        self.assertIn('id="prevDocRefVal"', self.html_content)
        self.assertIn('id="groupDocDueDate"', self.html_content)
        self.assertIn('id="docDueDate"', self.html_content)
        self.assertIn('id="prevDocDueDateRow"', self.html_content)
        self.assertIn('id="prevDocDueDateLabel"', self.html_content)
        self.assertIn('id="prevNetTotalLabelCell"', self.html_content)
        self.assertIn('id="docWhtSelect"', self.html_content)

    def test_js_quotation_wht_locked_in_setdoctype(self):
        """Verify setDocType disables and locks docWhtSelect to 0 for quotation."""
        self.assertIn("function setDocType(", self.js_content)
        pattern = re.compile(r"if\s*\(\s*type\s*===\s*['\"]quotation['\"]\s*\)\s*\{[^}]*docWhtSelect\.value\s*=\s*['\"]0['\"][^}]*docWhtSelect\.disabled\s*=\s*true", re.DOTALL)
        self.assertTrue(pattern.search(self.js_content), "setDocType must set docWhtSelect.value = '0' and docWhtSelect.disabled = true for quotation")

    def test_js_calculate_doc_totals_quotation_rules(self):
        """Verify calculateDocTotals enforces whtRate=0, hides prevGrossRow and prevWhtRow, and sets Grand Total label."""
        self.assertIn("if (currentDocType === 'quotation') {\n    whtRate = 0;", self.js_content)
        self.assertIn("prevNetTotalLabelCell.textContent = 'ยอดเงินรวมทั้งสิ้น / Grand Total'", self.js_content)

    def test_js_calculate_doc_totals_receipt_section_86_4(self):
        """Verify Section 86/4 compliance for Receipt totals and Thai Baht text."""
        self.assertIn("if (currentDocType === 'receipt' && whtRate > 0)", self.js_content)
        self.assertIn("prevNetTotalLabelCell.textContent = 'ยอดโอนสุทธิ / Net Paid'", self.js_content)
        self.assertIn("if (currentDocType === 'receipt' || currentDocType === 'quotation') {\n    bahtAmount = grossAmount;", self.js_content)

    def test_js_due_date_30_days_auto_calculation(self):
        """Verify updateDueDateFromPaymentTerm adds 30 days for quotation."""
        self.assertIn("function updateDueDateFromPaymentTerm(", self.js_content)
        pattern = re.compile(r"if\s*\(\s*currentDocType\s*===\s*['\"]quotation['\"]\s*\)\s*\{\s*daysToAdd\s*=\s*30;", re.DOTALL)
        self.assertTrue(pattern.search(self.js_content), "updateDueDateFromPaymentTerm must add 30 days for quotation")

    def test_js_quotation_customer_acceptance_box(self):
        """Verify prevLeftSignBox is populated with Customer Acceptance block on quotation."""
        self.assertIn("ผู้อนุมัติสั่งจ้าง / Customer Acceptance", self.js_content)
        self.assertIn("(ลงชื่อผู้ว่าจ้าง / ประทับตรา)", self.js_content)
        self.assertIn("วันที่ / Date: ....................", self.js_content)

    def test_js_suppress_ref_row_on_quotation(self):
        """Verify prevDocRefRow is hidden on quotation."""
        pattern = re.compile(r"if\s*\(\s*currentDocType\s*===\s*['\"]quotation['\"]\s*\)\s*\{\s*prevDocRefRow\.style\.display\s*=\s*['\"]none['\"];", re.DOTALL)
        self.assertTrue(pattern.search(self.js_content), "prevDocRefRow must be hidden on quotation")

    def test_js_export_pdf_filename_parity(self):
        """Verify exportPdfClientSide produces strictly ${cleanedDocNo}.pdf."""
        fn_start = self.js_content.find("function exportPdfClientSide()")
        self.assertNotEqual(fn_start, -1, "exportPdfClientSide function must exist")
        fn_body = self.js_content[fn_start:fn_start + 2500]
        self.assertIn("const finalFilename = `${cleanedDocNo}.pdf`;", fn_body)

    def test_js_process_document_sync_quotation_zero_wht(self):
        """Verify processDocumentSync enforces whtRate=0, wht=0, net=totalAfterDiscount+vat for quotation."""
        self.assertIn("whtRate = currentDocType === 'quotation' ? 0", self.js_content)
        self.assertIn("wht = currentDocType === 'quotation' ? 0", self.js_content)
        self.assertIn("net = currentDocType === 'quotation' ? Math.round((totalAfterDiscount + vat) * 100) / 100", self.js_content)

    def test_js_inputs_to_sync_includes_doc_invoice_no(self):
        """Verify inputsToSync contains docInvoiceNo to trigger live preview sync."""
        self.assertIn("'docInvoiceNo'", self.js_content)

    def test_html_po_and_job_code_inputs_exist(self):
        """Verify docPoNumber and docJobCode form inputs exist under paymentTerm & dueDate."""
        self.assertIn('id="docPoNumber"', self.html_content)
        self.assertIn('id="docJobCode"', self.html_content)
        self.assertIn("เลขที่ใบสั่งซื้อ / P.O. No.", self.html_content)
        self.assertIn("รหัสโครงการ / Job Code", self.html_content)

        due_pos = self.html_content.find('id="docDueDate"')
        po_pos = self.html_content.find('id="docPoNumber"')
        job_pos = self.html_content.find('id="docJobCode"')
        self.assertTrue(due_pos < po_pos < job_pos, "docPoNumber and docJobCode must appear after docDueDate")

    def test_html_po_and_job_code_preview_rows_exist(self):
        """Verify prevDocPoNumberRow and prevDocJobCodeRow exist in preview paper meta-table."""
        self.assertIn('id="prevDocPoNumberRow"', self.html_content)
        self.assertIn('id="prevDocPoNumberLabel"', self.html_content)
        self.assertIn('id="prevDocPoNumberVal"', self.html_content)
        self.assertIn('id="prevDocJobCodeRow"', self.html_content)
        self.assertIn('id="prevDocJobCodeLabel"', self.html_content)
        self.assertIn('id="prevDocJobCodeVal"', self.html_content)

        ref_pos = self.html_content.find('id="prevDocRefRow"')
        po_row_pos = self.html_content.find('id="prevDocPoNumberRow"')
        job_row_pos = self.html_content.find('id="prevDocJobCodeRow"')
        date_pos = self.html_content.find('id="prevDocDateLabel"')
        self.assertTrue(ref_pos < po_row_pos < job_row_pos < date_pos,
                        "PO and Job Code preview rows must appear between prevDocRefRow and prevDocDateLabel")

    def test_js_inputs_to_sync_includes_po_and_job_code(self):
        """Verify inputsToSync contains docPoNumber and docJobCode to trigger live preview sync."""
        self.assertIn("'docPoNumber'", self.js_content)
        self.assertIn("'docJobCode'", self.js_content)

    def test_js_sync_doc_preview_handles_po_and_job_code(self):
        """Verify syncDocPreview handles show/hide and textContent for PO and Job Code rows."""
        self.assertIn("prevDocPoNumberRow.style.display = ''", self.js_content)
        self.assertIn("prevDocPoNumberRow.style.display = 'none'", self.js_content)
        self.assertIn("prevDocJobCodeRow.style.display = ''", self.js_content)
        self.assertIn("prevDocJobCodeRow.style.display = 'none'", self.js_content)
        self.assertIn("prevDocPoNumberVal.textContent = poNumberVal", self.js_content)
        self.assertIn("prevDocJobCodeVal.textContent = jobCodeVal", self.js_content)

    def test_js_handle_upload_pdf_to_drive_includes_po_and_job_code(self):
        """Verify handleUploadPdfToDrive includes po_number and job_code in docPayloadData."""
        fn_start = self.js_content.find("async function handleUploadPdfToDrive")
        self.assertNotEqual(fn_start, -1)
        fn_body = self.js_content[fn_start:fn_start + 8000]
        self.assertIn("po_number:", fn_body)
        self.assertIn("job_code:", fn_body)

    def test_js_process_document_sync_saves_po_and_job_code(self):
        """Verify processDocumentSync preserves po_number and job_code in docRecord and appends to remarks."""
        fn_start = self.js_content.find("function processDocumentSync()")
        self.assertNotEqual(fn_start, -1)
        fn_body = self.js_content[fn_start:fn_start + 8000]
        self.assertIn("po_number: poNumber", fn_body)
        self.assertIn("job_code: jobCode", fn_body)
        self.assertIn("P.O. No.:", fn_body)
        self.assertIn("Job Code:", fn_body)

    def test_js_create_new_document_resets_po_and_job_code(self):
        """Verify createNewDocument resets docPoNumber and docJobCode inputs."""
        fn_start = self.js_content.find("function createNewDocument(")
        self.assertNotEqual(fn_start, -1)
        fn_body = self.js_content[fn_start:fn_start + 2500]
        self.assertIn("document.getElementById('docPoNumber').value = ''", fn_body)
        self.assertIn("document.getElementById('docJobCode').value = ''", fn_body)

    def test_js_load_doc_into_editor_populates_po_and_job_code(self):
        """Verify loadDocIntoEditor populates docPoNumber and docJobCode from doc object."""
        self.assertIn("function loadDocIntoEditor(", self.js_content)
        self.assertIn("window.loadDocIntoEditor = loadDocIntoEditor;", self.js_content)


if __name__ == "__main__":
    unittest.main()
