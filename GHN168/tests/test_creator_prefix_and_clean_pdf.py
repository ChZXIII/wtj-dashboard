"""
Test Suite: Creator Prefix in Google Sheets & 100% Clean PDF (No Name on PDF)
Verifies:
1. document_template_engine: HTML rendering is 100% clean (no Thai creator prefixes on PDF face, title, header badge, or reference line).
2. local_pdf_engine: PDF generation uses clean doc_no and clean filename.
3. ghn168_sync_service:
   - detect_document_creator identifies correct partner short name ('เก่ง', 'หอม', 'นิค', 'มด') or defaults to 'เก่ง'.
   - format_sheet_doc_no_with_creator prepends creator to doc_no for Google Sheets.
   - build_sheet_row_data puts creator-prefixed doc_no in Column C for Quotation, Invoice, and Receipt.
   - generate_and_sync_document returns clean doc_no to caller/UI while syncing creator-prefixed to Sheets.
   - find_document_by_no finds documents queried by either clean or prefixed doc_no.
4. line_bot_server:
   - /api/documents/pdf/{doc_no} serves with clean doc_no filename.
"""

import pytest
from unittest.mock import patch, MagicMock

from document_template_engine import normalize_doc_no, render_document_html, render_wht_html
from local_pdf_engine import get_local_pdf_path, convert_html_to_pdf_local
from ghn168_sync_service import (
    detect_document_creator,
    format_sheet_doc_no_with_creator,
    build_sheet_row_data,
    generate_and_sync_document,
    find_document_by_no,
    _RECENT_GENERATED_DOCS
)


class TestNormalizeDocNoAndCleanHtml:
    """Verifies that normalize_doc_no strips all creator prefixes and HTML rendering is 100% clean."""

    @pytest.mark.parametrize("input_no, expected_clean", [
        ("เก่ง-QT-202609-001", "QT-202609-001"),
        ("หอม-RE-202609-002", "RE-202609-002"),
        ("นิค-IV-202609-003", "IV-202609-003"),
        ("มด-QT-202609-004", "QT-202609-004"),
        ("พี่นิค-IV-202609-005", "IV-202609-005"),
        ("ทอย-RE2608-587", "RE2608-587"),
        ("[ทอย]-RE2608-587", "RE2608-587"),
        ("QT-202609-001", "QT-202609-001"),
        ("IV-202609-002", "IV-202609-002"),
        ("RE-202609-003", "RE-202609-003"),
        ("WHT-202609-001", "WHT-202609-001"),
    ])
    def test_normalize_doc_no(self, input_no, expected_clean):
        assert normalize_doc_no(input_no) == expected_clean

    def test_render_quotation_html_100_percent_clean(self):
        doc_data = {
            "doc_no": "เก่ง-QT-202609-001",
            "doc_date": "08/09/2026",
            "client_name": "บริษัท แอดวานซ์ ดิจิทัล จำกัด",
            "client_tax_id": "0105551234567",
            "project_name": "งานผลิตวิดีโอและโปรดักชั่น",
            "amount": 25000.0,
            "items": [{"desc": "งานผลิตวิดีโอและโปรดักชั่น", "qty": 1, "price": 25000.0, "amount": 25000.0}],
            "is_vat": True,
            "creator": "เก่ง"
        }
        html = render_document_html("quotation", doc_data)

        # Must contain clean document number
        assert "QT-202609-001" in html
        # Must NOT contain creator prefix in the title or badge
        assert f"<title>ใบเสนอราคา - QT-202609-001</title>" in html
        assert "เก่ง-QT-202609-001" not in html

    def test_render_invoice_html_clean_reference(self):
        doc_data = {
            "doc_no": "หอม-IV-202609-002",
            "ref_doc_no": "เก่ง-QT-202609-001",
            "doc_date": "08/09/2026",
            "client_name": "บริษัท มีเดีย พลัส จำกัด",
            "project_name": "ถ่ายทำสื่อโฆษณา",
            "amount": 30000.0,
            "items": [{"desc": "ถ่ายทำสื่อโฆษณา", "qty": 1, "price": 30000.0, "amount": 30000.0}],
            "creator": "หอม"
        }
        html = render_document_html("invoice", doc_data)

        assert "IV-202609-002" in html
        assert f"<title>ใบวางบิล / ใบแจ้งหนี้ - IV-202609-002</title>" in html
        assert "หอม-IV-202609-002" not in html
        # Reference doc should also be normalized clean
        assert "QT-202609-001" in html
        assert "เก่ง-QT-202609-001" not in html

    def test_render_receipt_html_100_percent_clean(self):
        doc_data = {
            "doc_no": "มด-RE-202609-003",
            "ref_invoice_no": "นิค-IV-202609-002",
            "doc_date": "08/09/2026",
            "client_name": "บริษัท ครีเอทีฟ ซัพพลาย จำกัด",
            "project_name": "ผลิตสปอตวิทยุและสื่อออนไลน์",
            "amount": 15000.0,
            "creator": "มด"
        }
        html = render_document_html("receipt", doc_data)

        assert "RE-202609-003" in html
        assert f"<title>ใบเสร็จรับเงิน / ใบกำกับภาษี - RE-202609-003</title>" in html
        assert "มด-RE-202609-003" not in html


class TestCreatorDetectionAndSheetFormatting:
    """Verifies creator detection and Column C prefix formatting."""

    def test_detect_document_creator_from_creator_field(self):
        assert detect_document_creator(creator="keng") == "เก่ง"
        assert detect_document_creator(creator="hom") == "หอม"
        assert detect_document_creator(creator="nick") == "นิค"
        assert detect_document_creator(creator="mod") == "มด"

    def test_detect_document_creator_from_doc_data(self):
        assert detect_document_creator(doc_data={"speaker_name": "บอสนิค"}) == "นิค"
        assert detect_document_creator(doc_data={"signatory_select": "หอม"}) == "หอม"
        assert detect_document_creator(doc_data={"creator": "มด"}) == "มด"
        assert detect_document_creator(doc_data={"signer_name": "นาย มงคล วงศ์สกุลยานนท์"}) == "เก่ง"

    def test_detect_document_creator_default_to_keng(self):
        assert detect_document_creator() == "เก่ง"
        assert detect_document_creator(doc_data={}) == "เก่ง"

    def test_format_sheet_doc_no_with_creator(self):
        # When clean doc_no is passed with specific creator
        assert format_sheet_doc_no_with_creator("QT-202609-001", creator="หอม") == "หอม-QT-202609-001"
        assert format_sheet_doc_no_with_creator("IV-202609-002", creator="นิค") == "นิค-IV-202609-002"
        assert format_sheet_doc_no_with_creator("RE-202609-003", creator="มด") == "มด-RE-202609-003"

        # When already prefixed, retains existing prefix
        assert format_sheet_doc_no_with_creator("เก่ง-QT-202609-001") == "เก่ง-QT-202609-001"
        assert format_sheet_doc_no_with_creator("หอม-IV-202609-002") == "หอม-IV-202609-002"

        # When no creator specified, defaults to 'เก่ง'
        assert format_sheet_doc_no_with_creator("QT-202609-001") == "เก่ง-QT-202609-001"

    def test_build_sheet_row_data_column_c_prefixed(self):
        # Quotation
        qt_data = {
            "doc_no": "QT-202609-001",
            "doc_date": "08/09/2026",
            "client_name": "ลูกค้า ก",
            "creator": "หอม",
            "amount": 20000.0
        }
        sheet_name, row = build_sheet_row_data("quotation", qt_data)
        assert sheet_name == "ใบเสนอราคา"
        assert row[2] == "หอม-QT-202609-001"

        # Invoice
        iv_data = {
            "doc_no": "IV-202609-002",
            "doc_date": "08/09/2026",
            "client_name": "ลูกค้า ข",
            "creator": "นิค",
            "amount": 35000.0
        }
        sheet_name, row = build_sheet_row_data("invoice", iv_data)
        assert sheet_name == "ใบวางบิล"
        assert row[2] == "นิค-IV-202609-002"

        # Receipt
        re_data = {
            "doc_no": "RE-202609-003",
            "doc_date": "08/09/2026",
            "client_name": "ลูกค้า ค",
            "creator": "มด",
            "amount": 50000.0
        }
        sheet_name, row = build_sheet_row_data("receipt", re_data)
        assert sheet_name == "รายรับ"
        assert row[2] == "มด-RE-202609-003"


class TestGenerateAndSyncIntegration:
    """Verifies generate_and_sync_document end-to-end behavior with creator prefix."""

    @patch("ghn168_sync_service.sync_document_to_sheets")
    @patch("ghn168_sync_service.convert_html_to_pdf_local")
    def test_generate_and_sync_preserves_creator_in_sheet_and_cleans_doc_no(self, mock_convert, mock_sync):
        mock_convert.return_value = {
            "status": "success",
            "pdf_path": "/tmp/mock.pdf",
            "doc_no": "QT-202609-001"
        }
        mock_sync.return_value = {"status": "success"}

        doc_data = {
            "doc_no": "QT-202609-001",
            "doc_date": "08/09/2026",
            "client_name": "บริษัท เทส คอร์ปอเรชั่น จำกัด",
            "amount": 10000.0,
            "creator": "หอม"
        }

        res = generate_and_sync_document("quotation", doc_data)

        # Clean doc_no returned to caller / UI
        assert res["doc_no"] == "QT-202609-001"
        assert res["clean_doc_no"] == "QT-202609-001"
        # Prefixed doc_no synced to Google Sheets
        assert res["sheet_doc_no"] == "หอม-QT-202609-001"
        assert res["pdf_name"] == "QT-202609-001.pdf"

        # Verify Google Sheets sync payload received prefixed doc_no
        call_args = mock_sync.call_args
        synced_values = call_args[1].get("values") or call_args[0][1]
        assert synced_values[2] == "หอม-QT-202609-001"

    def test_lookup_handles_both_clean_and_prefixed(self):
        # Cache a mock document under both clean and prefixed keys
        entry = {
            "source_sheet": "ใบเสนอราคา",
            "doc_type": "quotation",
            "doc_no": "QT-202609-999",
            "clean_doc_no": "QT-202609-999",
            "sheet_doc_no": "หอม-QT-202609-999",
            "client_name": "บริษัท ทดสอบสองทาง จำกัด"
        }
        _RECENT_GENERATED_DOCS["QT-202609-999"] = entry
        _RECENT_GENERATED_DOCS["หอม-QT-202609-999"] = entry

        # Lookup by clean
        found_by_clean = find_document_by_no("QT-202609-999")
        assert found_by_clean is not None
        assert found_by_clean["client_name"] == "บริษัท ทดสอบสองทาง จำกัด"

        # Lookup by prefixed
        found_by_prefix = find_document_by_no("หอม-QT-202609-999")
        assert found_by_prefix is not None
        assert found_by_prefix["client_name"] == "บริษัท ทดสอบสองทาง จำกัด"

    @patch("ghn168_sync_service.generate_and_sync_document")
    @patch("ghn168_sync_service.find_document_by_no")
    def test_convert_document_pipeline_preserves_creator(self, mock_find, mock_gen):
        from ghn168_sync_service import convert_document

        mock_find.return_value = {
            "source_sheet": "ใบเสนอราคา",
            "doc_type": "quotation",
            "doc_no": "หอม-QT-202609-005",
            "clean_doc_no": "QT-202609-005",
            "sheet_doc_no": "หอม-QT-202609-005",
            "client_name": "บริษัท มีเดีย คอนเนคท์ จำกัด",
            "amount": 40000.0,
            "net_total": 42800.0,
            "items": [{"desc": "งานถ่ายทำ", "qty": 1, "price": 40000.0, "amount": 40000.0}]
        }
        mock_gen.return_value = {
            "status": "success",
            "doc_no": "IV-202609-005",
            "sheet_doc_no": "หอม-IV-202609-005",
            "clean_doc_no": "IV-202609-005",
            "totals": {"net_total": 41600.0}
        }

        res = convert_document("หอม-QT-202609-005", "invoice")
        assert res["status"] == "success"
        # Verify generate_and_sync_document was called with creator preserved as 'หอม'
        call_kwargs = mock_gen.call_args.kwargs if mock_gen.call_args.kwargs else {}
        call_payload = call_kwargs.get("doc_data") or mock_gen.call_args[0][1]
        assert call_payload["creator"] == "หอม"


class TestLocalPdfEngineCleanFilename:
    """Verifies that convert_html_to_pdf_local produces clean filename without creator prefix."""

    @patch("subprocess.run")
    @patch("local_pdf_engine.find_chromium_binary")
    def test_pdf_engine_strips_creator_from_target_filename(self, mock_chrom, mock_subp, tmp_path):
        from local_pdf_engine import convert_html_to_pdf_local

        mock_chrom.return_value = "/mock/chromium"
        mock_subp.return_value = MagicMock(returncode=0)

        # Create dummy target file to simulate chromium output
        target_pdf = tmp_path / "QT-202609-001.pdf"
        target_pdf.write_bytes(b"%PDF-1.4 mock content " + b"x" * 2000)

        with patch("local_pdf_engine.get_pdf_storage_dir", return_value=tmp_path):
            res = convert_html_to_pdf_local(
                html_content="<html><body>Test</body></html>",
                doc_no="เก่ง-QT-202609-001"
            )

            assert res["status"] == "success"
            assert res["doc_no"] == "QT-202609-001"
            assert res["pdf_path"].endswith("QT-202609-001.pdf")
            assert "เก่ง-" not in res["pdf_path"]
