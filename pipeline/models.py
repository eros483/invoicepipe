# ----- Pydanic models for strict data type validation @ pipeline/models.py -----
from pydantic import BaseModel, field_validator
import re

class Invoice(BaseModel):
    """
    Representation of an extracted invoice.

    Attributes:
        invoice_date: ISO 8601 date string (YYYY-MM-DD).
        vendor_name:  Name of the vendor / supplier.
        net_amount:   Pre-tax subtotal as a float.
        tax_amount:   Tax component as a float.
        total_amount: Final amount due as a float.
    """

    invoice_date: str
    vendor_name: str
    net_amount: float
    tax_amount: float
    total_amount: float

    @field_validator("invoice_date")
    @classmethod
    def validate_date_format(cls, value: str) -> str:
        """
        Ensure the date string conforms to YYYY-MM-DD.

        Args:
            value: Raw date string from LLM extraction.

        Returns:
            The original value if it matches YYYY-MM-DD.
        """
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):            
            raise ValueError(
                f"invoice_date '{value}' is not in YYYY-MM-DD format. "
                "The extractor should normalise dates before creating this model."
            )
        
        return value