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
# Clone repository and  navigate to directory
git clone https://github.com/Eros483/invoicePipe.git
cd invoicePipe

# Install dependencies (suggest using a venv or a package manager)
pip install -r requirements.txt

# Setup Groq API key in the environment file
cp .env.example .env
```

---

## Running the Pipeline

```bash
streamlit run main.py
```

The interactive prototype will be available at `http://localhost:8501/`

There are sample images present in the `src` directory labelled as:
1. `img1.png` acts as a sample for Invoice A, the "Happy Path".
2. `img2.jpg` acts as a sample for Invoice B, the "Ambiguous Format".
3. `img3.jpg` acts as a sample for Invoice C, the "Fraud/Error" case.

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

The system prompt instructs the LLM to act as a **transcriber** only, so as to force it to copy values exactly as they appear on the invoice and
return them in a fixed JSON schema with no markdown and no extra commentary.
`temperature=0` plus Groq's `response_format={"type":"json_object"}` (JSON
mode) guarantees a parseable structure every time. 

All data cleaning
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
---

## Notes
- This Prototype was intended to be a `FastAPI + React.JS` app to be deployed via `Render` and `Vercel`.
    - This was scrapped due to the lack of a persistent storage option available in free tiers.