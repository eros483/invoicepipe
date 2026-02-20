# ----- Router logic for poorly extracted invoices @ pipeline/router.py -----

import csv
from datetime import datetime, timezone
from pathlib import Path
from pipeline.models import Invoice
from utils.logger import get_logger

logger=get_logger(__name__)

def route_invoice(
    invoice_data: Invoice,
    filename: str,
    is_valid: bool,
    error_message: str | None,
    approved_path: Path,
    review_path: Path,
) -> None:
    """Write invoice data to the appropriate output destination.

    Args:
        invoice_data:   The parsed and validated :class:`Invoice`.
        filename:       Original upload filename (used in log entries).
        is_valid:       ``True`` if the invoice passed the logic gate.
        error_message:  Validation error string; ``None`` when valid.
        approved_path:  Path to the approved invoices CSV file.
        review_path:    Path to the manual-review log text file.
    """
    if is_valid:
        _write_approved(invoice_data, filename, approved_path)
    else:
        _write_review(filename, error_message, review_path)


def _write_approved(invoice: Invoice, filename: str, path: Path) -> None:
    """Append a validated invoice row to the approved CSV.

    Args:
        invoice:  Parsed invoice data.
        filename: Source filename for audit context.
        path:     Target CSV file path.
    """
    row = {
        "filename": filename,
        "invoice_date": invoice.invoice_date,
        "vendor_name": invoice.vendor_name,
        "net_amount": f"{invoice.net_amount:.2f}",
        "tax_amount": f"{invoice.tax_amount:.2f}",
        "total_amount": f"{invoice.total_amount:.2f}",
    }
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
        writer.writerow(row)
    logger.info("Appended to %s: %s", path, row)


def _write_review(filename: str, error_message: str | None, path: Path) -> None:
    """Append a flagged-invoice entry to the manual-review log.

    Args:
        filename:      Source filename.
        error_message: Human-readable description of the mismatch.
        path:          Target text file path.
    """
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"[{timestamp}] FILE: {filename} | ERROR: {error_message}\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(entry)
    logger.info("Flagged in %s: %s", path, entry.strip())