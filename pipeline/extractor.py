# ----- Core extraction logic using Groq Vision @ pipeline/extractor.py -----
import base64
import json
import os
import re
from dateutil import parser as dateutil_parser
from groq import Groq

from pipeline.models import Invoice

from utils.logger import get_logger
from utils.config import settings

logger = get_logger(__name__)

_client = Groq(api_key=settings.GROQ_API_KEY)

_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

_SYSTEM_PROMPT = """\
You are a precise invoice data extractor. Your ONLY job is to read the
provided invoice and return a single, valid JSON object with exactly these
keys and no others:

{
  "Invoice_Date":   "<date exactly as it appears on the invoice>",
  "Vendor_Name":    "<vendor name exactly as it appears>",
  "Net_Amount":     "<net / subtotal amount exactly as it appears>",
  "Tax_Amount":     "<tax amount exactly as it appears>",
  "Total_Amount":   "<total amount due exactly as it appears>"
}

Rules:
- Output ONLY the JSON object. No markdown, no explanation, no code fences.
- Copy values verbatim from the invoice — do NOT interpret, convert, or
  calculate anything.
- If a field is not present, use null.
"""

_USER_PROMPT = "Extract the invoice data from the attached document."


def _encode_bytes(raw_bytes: bytes) -> str:
    """
    Helper function to encode bytes
    """
    return base64.standard_b64encode(raw_bytes).decode("ascii")


def _build_messages(b64_data: str, media_type: str) -> list[dict]:
    """
    Assemble message payload for GROQ.
    """
    data_uri = f"data:{media_type};base64,{b64_data}"

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": data_uri},
                },
                {"type": "text", "text": _USER_PROMPT},
            ],
        },
    ]


def _strip_currency(value: str | None) -> float | None:
    """
    Helper function for cleaning currency strings.
    """
    if value is None:
        return None

    cleaned = re.sub(r"[^\d.,-]", "", str(value))

    if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Could not convert '%s' to float; returning None.", value)
        return None


def _normalise_date(raw_date: str | None, filename: str) -> str:
    """
    Helper function to parse and normalise date data.
    """
    if not raw_date:
        raise ValueError("invoice_date is missing from the extracted data.")

    try:
        parsed = dateutil_parser.parse(raw_date, dayfirst=False)
        iso_date = parsed.strftime("%Y-%m-%d")
        if re.match(r"^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}$", raw_date.strip()):
            logger.warning(
                "[%s] Ambiguous date '%s' interpreted as '%s' (month-first / US convention). "
                "Verify manually if European date order was intended.",
                filename,
                raw_date,
                iso_date,
            )
        return iso_date
    except (ValueError, OverflowError) as exc:
        raise ValueError(
            f"Cannot parse date '{raw_date}' from {filename}: {exc}"
        ) from exc


def extract_invoice_data(raw_bytes: bytes, media_type: str, filename: str) -> Invoice:
    """
    Run the full extraction pipeline for a single invoice file.

    Args:
        raw_bytes:  Binary content of the uploaded invoice.
        media_type: MIME type (e.g. ``"application/pdf"`` or ``"image/png"``).
        filename:   Original filename, used for logging and error messages.

    Returns:
        A fully validated :class:`Invoice` instance.

    Raises:
        ValueError: If the LLM response cannot be parsed or required fields
                    are missing / invalid.
    """
    vision_media_type = media_type if media_type.startswith("image/") else "image/jpeg"

    b64 = _encode_bytes(raw_bytes)
    messages = _build_messages(b64, vision_media_type)

    logger.info("[%s] Calling Groq Vision API (model=%s)…", filename, _VISION_MODEL)
    response = _client.chat.completions.create(
        model=_VISION_MODEL,
        messages=messages,
        temperature=0,          
        max_tokens=512,
        response_format={"type": "json_object"},
    )

    raw_content = response.choices[0].message.content or ""
    logger.debug("[%s] Raw LLM response: %s", filename, raw_content)

    raw_content = re.sub(r"```(?:json)?|```", "", raw_content).strip() # check for markdown responses

    try:
        payload: dict = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned non-JSON content for {filename}: {raw_content!r}"
        ) from exc

    payload = {k.lower(): v for k, v in payload.items()}

    net = _strip_currency(payload.get("net_amount"))
    tax = _strip_currency(payload.get("tax_amount"))
    total = _strip_currency(payload.get("total_amount"))

    if any(v is None for v in (net, tax, total)):
        raise ValueError(
            f"One or more amount fields could not be parsed for {filename}: "
            f"net={payload.get('net_amount')}, tax={payload.get('tax_amount')}, "
            f"total={payload.get('total_amount')}"
        )

    iso_date = _normalise_date(payload.get("invoice_date"), filename)
    vendor = str(payload.get("vendor_name") or "").strip() or "Unknown Vendor"

    invoice = Invoice(
        invoice_date=iso_date,
        vendor_name=vendor,
        net_amount=net,
        tax_amount=tax,
        total_amount=total,
    )
    logger.info("[%s] Extraction successful: %s", filename, invoice.model_dump())
    return invoice