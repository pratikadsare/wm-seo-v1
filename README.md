# Walmart Content Extractor

Internal Python + Streamlit tool for extracting Walmart PDP catalog data from your SKU and URL list.

The app has:

- Login page with file-based credentials
- Manual paste table for `SKU` and `Walmart URL`
- CSV / Excel upload option
- Checkbox field selection
- Strict original PDP extraction
- CSV and Excel downloads
- Status and error columns for every SKU

## Main file

Run this file:

```bash
streamlit run app.py
```

Main app path after extracting the ZIP:

```text
walmart_content_extractor/app.py
```

## Folder structure

```text
walmart_content_extractor/
  app.py
  auth.py
  scraper.py
  credentials.json
  credentials.example.json
  requirements.txt
  sample_input.csv
  README.md
  .streamlit/config.toml
```

## Setup on Windows

Open Command Prompt or PowerShell inside the extracted folder.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Setup on Mac / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Credentials setup

Edit `credentials.json` before using the tool.

Current starter file:

```json
{
  "allowed_domain": "@pattern.com",
  "users": []
}
```

Example filled file:

```json
{
  "allowed_domain": "@pattern.com",
  "users": [
    {
      "email": "first.user@pattern.com",
      "password": "ExactPasswordHere",
      "active": true
    },
    {
      "email": "second.user@pattern.com",
      "password": "AnotherExactPasswordHere",
      "active": true
    }
  ]
}
```

Rules:

- Email must be listed in `credentials.json`
- Password must match exactly
- Email must end with `@pattern.com`
- Set `active` to `false` to disable a user without deleting the record

For a private internal GitHub repository, you may keep `credentials.json` in the repo only if that is approved by your internal security process. For safer deployment, keep real credentials out of public repositories.

## How to use the tool

1. Sign in using an approved credential from `credentials.json`.
2. Add input data in one of two ways:
   - Paste into the table with columns `SKU` and `Walmart URL`
   - Upload a CSV / Excel file and select the SKU and URL columns
3. Select the exact fields you want to scrape using checkboxes.
4. Click `Start Scraping`.
5. Download CSV or Excel output.

## Output columns

These columns are always included:

- SKU
- Walmart URL
- Walmart Item ID
- Status
- Error

Selected fields are added after these base columns.

## Available scrape fields

- Title
- Brand
- Price
- Currency
- Seller
- Availability
- Rating
- Review Count
- Main Image
- Additional Images
- Original PDP Bullet Points
- Original PDP Description
- Specifications
- Ingredients
- Warnings
- Category / Breadcrumbs
- UPC / GTIN
- Model / Part Number

## Strict extraction rules included

The scraper is designed for clean internal catalog data extraction.

### Images

The tool only attempts to extract SKU/PDP product images from structured Walmart product data:

- Main image
- Additional product images for the same PDP item

The image filter skips:

- PNG files
- SVG/GIF/icon assets
- Rating stars
- Logos
- Badges
- Seller graphics
- Review images
- Swatches and variation images
- General UI images

### Bullets and description

The tool does not generate, rewrite, summarize, or infer content.

It extracts only original structured PDP fields such as:

- `shortDescription`
- `keyFeatures`
- `longDescription`
- product JSON-LD description fallback

If original structured PDP bullets or description are not found, the output stays blank for those fields instead of creating AI-style content.

## Status values

- `Success`: selected data was found
- `Partial`: page loaded but selected fields were missing from original structured data
- `Invalid URL`: input was not a valid Walmart URL
- `Not Found`: Walmart returned HTTP 404
- `Blocked`: Walmart returned a block, verification, or rate-limit response
- `Failed`: request or page error

## Internal use and compliance note

This project is intended for authorized internal catalog SKU workflows. It does not include proxy rotation, CAPTCHA bypass, account automation, or protection circumvention. It uses a delay between requests and records blocked/failed URLs instead of trying to bypass access controls.

Use it only for URLs and data access permitted by your organization and the target site terms.
