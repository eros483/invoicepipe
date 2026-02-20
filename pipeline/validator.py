"""Validation for LLM generated invoice data @pipeline/validator.py"""

from utils.logger import get_logger
from pipeline.models import Invoice
from utils.config import settings
logger = get_logger(__name__)

_ROUNDING_TOLERANCE = settings.ROUNDING_TOLERANCE

def validate_invoice(invoice: Invoice) -> tuple[bool, str | None]:
    """
    Arithmetic Check whether (Net + Tax) equals Total within the allowed tolerance.

    Args:
        invoice: Pydantic `invoice` model instance containing extracted data.

    Returns:
        - ``True, None`` if the invoice is mathematically valid.
        - ``False, "<error message>"`` if the totals do not reconcile.
    """
    calculated = round(invoice.net_amount + invoice.tax_amount, 2)
    reported = round(invoice.total_amount, 2)
    diff = abs(calculated - reported)

    if diff <= _ROUNDING_TOLERANCE:
        logger.info(
            "Validation PASSED for vendor '%s': %.2f + %.2f = %.2f ✓",
            invoice.vendor_name,
            invoice.net_amount,
            invoice.tax_amount,
            invoice.total_amount,
        )
        return True, None

    error = (
        f"Math Mismatch: Calculated {calculated:.2f} "
        f"(net {invoice.net_amount:.2f} + tax {invoice.tax_amount:.2f}) "
        f"vs Total {reported:.2f} — discrepancy of {diff:.2f}"
    )
    logger.warning("Validation FAILED: %s", error)
    return False, error