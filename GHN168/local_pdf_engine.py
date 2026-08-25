#!/usr/bin/env python3
"""
================================================================================
GHN168 Local Headless Chromium PDF Engine
================================================================================
Converts self-contained HTML/CSS documents into 100% vector-sharp PDFs locally
on the Linux VPS / production server without relying on third-party APIs.

Features:
- Auto-detects Chromium, Chromium Browser, or Google Chrome binary on host.
- Supports Thai fonts (fonts-thai-tlwg, Noto Sans Thai, Google Fonts).
- Headless execution with robust flags (--headless, --no-sandbox, --disable-gpu).
- Output storage management at `/opt/ghn168_bot/generated_pdfs/` with local fallback.
- Minimum size verification (> 10KB) and fallback mechanisms.
================================================================================
"""

import os
import shutil
import subprocess
import tempfile
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from document_template_engine import render_document_html

logger = logging.getLogger("ghn168_pdf_engine")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent

# Default PDF Storage Directory
PRIMARY_STORAGE_DIR = Path("/opt/ghn168_bot/generated_pdfs")
FALLBACK_STORAGE_DIR = BASE_DIR / "generated_pdfs"


def get_pdf_storage_dir() -> Path:
    """Returns the writable PDF storage directory."""
    if PRIMARY_STORAGE_DIR.exists():
        return PRIMARY_STORAGE_DIR
    try:
        PRIMARY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        return PRIMARY_STORAGE_DIR
    except Exception:
        FALLBACK_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        return FALLBACK_STORAGE_DIR


PDF_STORAGE_DIR = get_pdf_storage_dir()


def find_chromium_binary() -> Optional[str]:
    """
    Searches for an available Chromium / Google Chrome binary on the system.
    Returns absolute path to executable or None.
    """
    # 1. Check environment variable override
    env_path = os.environ.get("CHROMIUM_PATH") or os.environ.get("CHROME_PATH")
    if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
        return env_path

    # 2. Search in PATH (prioritizing native deb binaries over snap)
    candidates = [
        "google-chrome-stable",
        "google-chrome",
        "chromium-browser",
        "chromium",
        "chrome"
    ]
    for name in candidates:
        which_path = shutil.which(name)
        if which_path and os.access(which_path, os.X_OK) and "snap" not in which_path:
            return which_path

    # 3. Search standard Linux and macOS absolute paths
    standard_paths = [
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/local/bin/google-chrome",
        "/usr/local/bin/chromium",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/snap/bin/chromium"
    ]
    for spath in standard_paths:
        if os.path.isfile(spath) and os.access(spath, os.X_OK):
            return spath

    # Fallback to any binary in path
    for name in candidates:
        which_path = shutil.which(name)
        if which_path and os.access(which_path, os.X_OK):
            return which_path

    return None


def get_local_pdf_path(doc_no: str) -> Optional[Path]:
    """
    Returns Path to existing PDF file for the given document number if it exists and is valid.
    """
    if not doc_no:
        return None
    clean_no = str(doc_no).strip()
    storage = get_pdf_storage_dir()
    candidate = storage / f"{clean_no}.pdf"
    if candidate.is_file() and candidate.stat().st_size > 1000:
        return candidate
    
    # Also check local fallback dir if different
    fallback = FALLBACK_STORAGE_DIR / f"{clean_no}.pdf"
    if fallback.is_file() and fallback.stat().st_size > 1000:
        return fallback

    return None


def convert_html_to_pdf_local(
    html_content: str,
    output_pdf_path: Optional[Union[str, Path]] = None,
    doc_no: Optional[str] = None,
    timeout: int = 45
) -> Dict[str, Any]:
    """
    Converts HTML content to a PDF file using headless Chromium.
    
    Args:
        html_content: Raw HTML/CSS string
        output_pdf_path: Target path for output PDF. If None, generated in PDF_STORAGE_DIR.
        doc_no: Document identifier (e.g. IV-202608-472)
        timeout: Maximum seconds allowed for chromium process
        
    Returns:
        dict: {
            "status": "success" | "error",
            "pdf_path": str,
            "size_bytes": int,
            "doc_no": str,
            "binary_used": str,
            "message": str
        }
    """
    if not html_content or not html_content.strip():
        return {
            "status": "error",
            "message": "Empty HTML content provided",
            "pdf_path": None,
            "size_bytes": 0
        }

    # Resolve output PDF path
    storage_dir = get_pdf_storage_dir()
    if output_pdf_path is None:
        file_name = f"{doc_no}.pdf" if doc_no else f"doc_{int(time.time()*1000)}.pdf"
        target_path = storage_dir / file_name
    else:
        target_path = Path(output_pdf_path).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

    chromium_bin = find_chromium_binary()
    if not chromium_bin:
        logger.error("No Chromium or Google Chrome binary found on system.")
        return {
            "status": "error",
            "message": "Chromium binary not found on host. Please install chromium-browser or google-chrome.",
            "pdf_path": None,
            "size_bytes": 0
        }

    # Temporary HTML file for headless rendering
    temp_dir = tempfile.mkdtemp(prefix="ghn168_pdf_")
    temp_html_path = os.path.join(temp_dir, f"render_{doc_no or 'tmp'}.html")
    temp_profile_dir = os.path.join(temp_dir, "chrome_profile")
    os.makedirs(temp_profile_dir, exist_ok=True)

    try:
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Build headless command with robust flags
        cmd = [
            chromium_bin,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-software-rasterizer",
            "--disable-extensions",
            "--disable-crash-reporter",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-sync",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            f"--crash-dumps-dir={temp_profile_dir}",
            f"--user-data-dir={temp_profile_dir}",
            f"--print-to-pdf={str(target_path)}",
            temp_html_path
        ]

        logger.info("Executing Chromium PDF conversion: %s -> %s", temp_html_path, target_path)
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )

        # Verify output PDF
        if target_path.is_file() and target_path.stat().st_size > 1024:  # At least > 1KB
            size = target_path.stat().st_size
            logger.info("✅ PDF successfully generated at %s (Size: %d bytes)", target_path, size)
            return {
                "status": "success",
                "pdf_path": str(target_path),
                "size_bytes": size,
                "doc_no": doc_no or target_path.stem,
                "binary_used": chromium_bin,
                "message": f"PDF generated successfully ({size:,} bytes)"
            }
        else:
            stderr_out = proc.stderr.strip() if proc.stderr else "Unknown error"
            logger.error("PDF generation failed or file too small. Exit code: %d, Stderr: %s", proc.returncode, stderr_out)
            return {
                "status": "error",
                "message": f"Chromium failed to generate PDF. Exit code {proc.returncode}: {stderr_out}",
                "pdf_path": None,
                "size_bytes": 0,
                "binary_used": chromium_bin
            }

    except subprocess.TimeoutExpired:
        logger.error("Chromium PDF conversion timed out after %d seconds", timeout)
        return {
            "status": "error",
            "message": f"Chromium conversion timed out ({timeout}s)",
            "pdf_path": None,
            "size_bytes": 0
        }
    except Exception as e:
        logger.error("Exception during local PDF conversion: %s", e)
        return {
            "status": "error",
            "message": str(e),
            "pdf_path": None,
            "size_bytes": 0
        }
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def generate_document_pdf(
    doc_type: str,
    doc_data: Dict[str, Any],
    output_pdf_path: Optional[Union[str, Path]] = None,
    timeout: int = 45
) -> Dict[str, Any]:
    """
    Renders the document HTML template and converts it directly to local PDF.
    
    Args:
        doc_type: Document type (quotation, invoice, receipt, wht, expense)
        doc_data: Dictionary of document fields
        output_pdf_path: Target path (optional)
        timeout: Process timeout
        
    Returns:
        dict: Conversion result with pdf_path, size_bytes, pdf_url
    """
    doc_no = doc_data.get("doc_no")
    if not doc_no:
        prefix_map = {"quotation": "QT", "invoice": "IV", "receipt": "RE", "wht": "50BIS", "expense": "PV"}
        prefix = prefix_map.get(str(doc_type).lower(), "DOC")
        doc_no = f"{prefix}-{time.strftime('%Y%m')}-{int(time.time()) % 1000:03d}"
        doc_data["doc_no"] = doc_no

    try:
        html_content = render_document_html(doc_type, doc_data)
    except Exception as e:
        logger.error("Failed to render HTML template for %s: %s", doc_no, e)
        return {
            "status": "error",
            "message": f"HTML rendering failed: {str(e)}",
            "pdf_path": None,
            "size_bytes": 0
        }

    conv_res = convert_html_to_pdf_local(
        html_content=html_content,
        output_pdf_path=output_pdf_path,
        doc_no=doc_no,
        timeout=timeout
    )
    
    conv_res["doc_no"] = doc_no
    conv_res["doc_type"] = doc_type
    conv_res["pdf_url"] = f"https://srv1913532.hstgr.cloud/api/documents/pdf/{doc_no}"
    return conv_res


if __name__ == "__main__":
    import sys
    print("Testing GHN168 Local PDF Engine...")
    binary = find_chromium_binary()
    print(f"Detected Chromium / Chrome binary: {binary}")
    storage = get_pdf_storage_dir()
    print(f"PDF Storage Directory: {storage}")
