# Walmart Content Extractor

Internal Streamlit tool for approved Pattern users to extract original Walmart PDP data from SKU and Walmart URL pairs.

## Main features

- Login page with email and password
- Separate `credentials.json` file
- Paste SKU and Walmart URL directly in a small table
- Upload CSV or Excel file
- Select fields using checkboxes
- Output keeps SKU and original URL
- Download CSV and Excel
- Strict image filtering to avoid logos, icons, rating images, PNG UI assets, variation swatches, and review images as much as possible
- Extracts original PDP bullets and description from page structured data, not AI-generated summaries

## Setup

Install Python 3.10 or newer.

```bash
pip install -r requirements.txt
```

## Credentials

Create a `credentials.json` file in the same folder as `app.py`.

Example:

```json
{
  "users": [
    {
      "email": "user1@pattern.com",
      "password": "YourPassword123"
    }
  ]
}
```

Only emails ending with `@pattern.com` are allowed.

## Run the tool

```bash
streamlit run app.py
```

## Input format

Your input should have these two columns:

```text
SKU
Walmart URL
```

You can paste rows in the tool or upload CSV / Excel.

## Notes

Walmart can change page structure or block requests. The tool is designed for internal controlled use and includes strict extraction rules, but some fields may be blank if Walmart does not expose them in the page data.
