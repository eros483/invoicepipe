# ----- Prototype streamlit app for invoice auditing pipeline @ main.py -----
from pathlib import Path
import streamlit as st

from pipeline.extractor import extract_invoice_data
from pipeline.router import route_invoice
from pipeline.validator import validate_invoice

from utils.logger import get_logger
from utils.config import settings

logger = get_logger(__name__)

APPROVED_CSV = Path(settings.PATH_APPROVED_CSV)
REVIEW_TXT = Path(settings.PATH_REVIEW_TXT)

def _ensure_output_files() -> None:
    """
    Helper to Create output files with headers if they do not already exist.
    """
    if not APPROVED_CSV.exists():
        APPROVED_CSV.write_text(
            "filename,invoice_date,vendor_name,net_amount,tax_amount,total_amount\n",
            encoding="utf-8",
        )
    if not REVIEW_TXT.exists():
        REVIEW_TXT.write_text("", encoding="utf-8")


def _run_pipeline(raw_bytes: bytes, mime_type: str, filename: str) -> dict:
    """
    Execute pipeline stages for a single invoice file.
    """
    invoice_data = extract_invoice_data(raw_bytes, mime_type, filename)
    is_valid, error_message = validate_invoice(invoice_data)
    route_invoice(
        invoice_data=invoice_data,
        filename=filename,
        is_valid=is_valid,
        error_message=error_message,
        approved_path=APPROVED_CSV,
        review_path=REVIEW_TXT,
    )

    return {
        "status": "approved" if is_valid else "flagged_for_review",
        "data": invoice_data.model_dump(),
        "validation_error": error_message,
    }

# ----- Streamlit UI configuration -----

st.set_page_config(
    page_title="Invoice Auditing Pipeline Prototype",
    page_icon="🧾",
    layout="centered",
)

_ensure_output_files()


st.title("Invoice Auditing Pipeline")
st.divider()

uploaded_files = st.file_uploader(
    "Drop one or more invoice files (PDF, PNG, JPEG, WEBP)",
    type=["pdf", "png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
)

if uploaded_files:
    if st.button("Process Invoices", type="primary", use_container_width=True):
        st.divider()

        approved_count = 0
        flagged_count = 0

        for uploaded_file in uploaded_files:
            filename = uploaded_file.name
            mime_type = uploaded_file.type or "image/png"

            with st.expander(f"{filename}", expanded=True):
                with st.spinner("Extracting data via Groq Vision…"):
                    try:
                        result = _run_pipeline(
                            raw_bytes=uploaded_file.read(),
                            mime_type=mime_type,
                            filename=filename,
                        )
                    except ValueError as exc:
                        st.error(f"**Extraction failed:** {exc}")
                        logger.error("Pipeline error for %s: %s", filename, exc)
                        continue

                data = result["data"]
                status = result["status"]
                error = result["validation_error"]

                col1, col2 = st.columns(2)
                col1.metric("Vendor", data["vendor_name"])
                col1.metric("Invoice Date", data["invoice_date"])
                col2.metric("Net Amount", f"${data['net_amount']:,.2f}")
                col2.metric("Tax Amount", f"${data['tax_amount']:,.2f}")
                st.metric("Total Amount", f"${data['total_amount']:,.2f}")

                if status == "approved":
                    st.success("**Validation passed** — appended to `approved_invoices.csv`")
                    approved_count += 1
                else:
                    st.error(
                        f"**Flagged for review** — logged to `manual_review_needed.txt`\n\n"
                        f"`{error}`"
                    )
                    flagged_count += 1

        st.divider()
        s_col1, s_col2 = st.columns(2)
        s_col1.metric("Approved", approved_count)
        s_col2.metric("Flagged", flagged_count)

st.sidebar.header("Output Files")

if st.sidebar.button("Refresh", use_container_width=True):
    st.rerun()

with st.sidebar.expander("approved_invoices.csv", expanded=True):
    csv_content = APPROVED_CSV.read_text(encoding="utf-8") if APPROVED_CSV.exists() else ""
    st.sidebar.code(csv_content or "(empty)", language="text")

with st.sidebar.expander("manual_review_needed.txt", expanded=True):
    txt_content = REVIEW_TXT.read_text(encoding="utf-8") if REVIEW_TXT.exists() else ""
    st.sidebar.code(txt_content or "(empty)", language="text")