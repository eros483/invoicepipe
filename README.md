# <centre> InvoicePipe </centre>

A lightweight Python pipeline that ingests invoice files, extracts structured
data via the **Groq Vision API** (LLaMA-4 Scout), validates quantities via basic arithmetic, and routes results to either `approved_invoices.csv` or
`manual_review_needed.txt`.

---

## Project Structure

```
invoicePipe/
├── main.py
├── pipeline
│   ├── extractor.py
│   ├── models.py
│   ├── router.py
│   └── validator.py
├── README.md
├── requirements.txt
├── TODO.md
└── utils
    ├── config.py
    ├── logger.py
```

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python      | ≥ 3.11  |
| Groq API key | [console.groq.com](https://console.groq.com) |

---

## Setup

```bash
# 1. Clone / unzip the project
cd invoicePipe

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Groq API key
export GROQ_API_KEY="gsk_..."      # Windows: set GROQ_API_KEY=gsk_...

# 5. Generate the three mock test invoices
python generate_test_invoices.py
```

---

## Running the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
Interactive docs: `http://127.0.0.1:8000/docs`

---

## Processing an Invoice

### Using curl

```bash
# Invoice A – Happy Path
curl -X POST "http://127.0.0.1:8000/process-invoice" \
     -F "file=@invoices/invoice_a_acme.png"

# Invoice B – Ambiguous Date
curl -X POST "http://127.0.0.1:8000/process-invoice" \
     -F "file=@invoices/invoice_b_globex.png"

# Invoice C – Fraud/Error Case
curl -X POST "http://127.0.0.1:8000/process-invoice" \
     -F "file=@invoices/invoice_c_soylent.png"
```

### Expected Outcomes

| Invoice | Vendor       | Validation | Output destination          |
|---------|--------------|------------|-----------------------------|
| A       | Acme Corp    | ✅ PASS    | `approved_invoices.csv`     |
| B       | Globex       | ✅ PASS    | `approved_invoices.csv`     |
| C       | Soylent Corp | ❌ FAIL    | `manual_review_needed.txt`  |

---

## Design Notes

### Handling the Ambiguous Date (Invoice B)

Invoice B carries the date `02/03/24`, which is ambiguous — it could mean
February 3rd (US) or March 2nd (European). The pipeline uses
`dateutil.parser.parse` with `dayfirst=False` (the US / ISO convention) to
resolve ambiguity, interpreting `02/03/24` as **2024-02-03** (February 3rd).
Whenever the input matches a short numeric pattern like `MM/DD/YY`, a
`WARNING`-level log entry is emitted so that a human auditor is always aware
a judgment call was made and can override it if needed.

### Prompting Strategy

The system prompt instructs the LLM to act as a **pure transcriber**, not an
interpreter — it must copy values exactly as they appear on the invoice and
return them in a fixed JSON schema with no markdown and no extra commentary.
`temperature=0` plus Groq's `response_format={"type":"json_object"}` (JSON
mode) guarantees a parseable structure every time. All data cleaning
(currency stripping, date normalisation, type casting) happens in Python
**after** extraction, keeping the LLM focused solely on OCR/reading and
preventing it from silently "correcting" values that should be flagged as
errors (e.g., Invoice C's fraudulent total).

---

## Output Files

### `approved_invoices.csv`

```
filename,invoice_date,vendor_name,net_amount,tax_amount,total_amount
invoice_a_acme.png,2024-10-05,Acme Corp,100.00,10.00,110.00
invoice_b_globex.png,2024-02-03,Globex,500.00,50.00,550.00
```

### `manual_review_needed.txt`

```
[2024-12-01T10:23:45Z] FILE: invoice_c_soylent.png | ERROR: Math Mismatch: Calculated 220.00 (net 200.00 + tax 20.00) vs Total 5000.00 — discrepancy of 4780.00
```