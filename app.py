from io import BytesIO

import pandas as pd
import streamlit as st

from auth import show_login_page
from scraper import DEFAULT_FIELDS, scrape_walmart_product

st.set_page_config(page_title="Walmart Content Extractor", page_icon="🛒", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] { background: #f7f9fc; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    .main-title {
        font-family: Georgia, 'Times New Roman', serif;
        font-size: 34px;
        font-weight: 700;
        color: #111111;
        margin-bottom: 4px;
    }
    .sub-text {
        color: #555555;
        font-size: 15px;
        margin-bottom: 20px;
    }
    .section-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 10px 28px rgba(30, 45, 90, 0.06);
        border: 1px solid #eef1f7;
        margin-bottom: 16px;
    }
    div.stButton > button:first-child {
        border-radius: 9px;
        background: #0f5be8;
        color: white;
        border: none;
        font-weight: 700;
    }
    div.stButton > button:first-child:hover {
        background: #0d50cc;
        color: white;
        border: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

header_left, header_right = st.columns([4, 1])
with header_left:
    st.markdown('<div class="main-title">Walmart Content Extractor</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-text">Paste SKU and Walmart URL rows or upload a file. Select only the fields you need, then download clean output.</div>',
        unsafe_allow_html=True,
    )
with header_right:
    st.caption(f"Signed in as {st.session_state.get('user_email', '')}")
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state.pop("user_email", None)
        st.rerun()

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("1. Add Input")
input_mode = st.radio("Choose input method", ["Paste in table", "Upload CSV/Excel"], horizontal=True)

input_df = pd.DataFrame(columns=["SKU", "Walmart URL"])

if input_mode == "Paste in table":
    starter_df = pd.DataFrame(
        [
            {"SKU": "SKU001", "Walmart URL": "https://www.walmart.com/ip/132797244"},
            {"SKU": "", "Walmart URL": ""},
            {"SKU": "", "Walmart URL": ""},
        ]
    )
    input_df = st.data_editor(
        starter_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "SKU": st.column_config.TextColumn("SKU", width="medium"),
            "Walmart URL": st.column_config.TextColumn("Walmart URL", width="large"),
        },
        key="manual_input_table",
    )
else:
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file)

            st.dataframe(uploaded_df.head(20), use_container_width=True)
            sku_col = st.selectbox("Select SKU column", uploaded_df.columns)
            url_col = st.selectbox("Select Walmart URL column", uploaded_df.columns)
            input_df = uploaded_df[[sku_col, url_col]].copy()
            input_df.columns = ["SKU", "Walmart URL"]
        except Exception as exc:
            st.error(f"Could not read file: {exc}")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("2. Select Fields to Scrape")

col1, col2, col3 = st.columns(3)
selected_fields = []
for index, field in enumerate(DEFAULT_FIELDS):
    target_col = [col1, col2, col3][index % 3]
    default_checked = field in [
        "Item ID", "Title", "Brand", "Price", "Seller", "Availability",
        "Main Image", "Additional Images", "Bullet Points", "Description",
    ]
    with target_col:
        if st.checkbox(field, value=default_checked, key=f"field_{field}"):
            selected_fields.append(field)

strict_note = (
    "Strict mode is always ON: the tool skips PNG/SVG/GIF icons, logos, rating images, "
    "review images, swatches, and variation-style images as much as possible. Bullets and descriptions are pulled from original page data only."
)
st.info(strict_note)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("3. Scrape and Download")

settings_col1, settings_col2 = st.columns([1, 3])
with settings_col1:
    delay_seconds = st.number_input("Delay between links in seconds", min_value=0.0, max_value=10.0, value=1.0, step=0.5)
with settings_col2:
    st.caption("Use a small delay for safer bulk scraping. Walmart may block frequent requests.")

valid_df = input_df.copy()
valid_df["SKU"] = valid_df["SKU"].fillna("").astype(str).str.strip()
valid_df["Walmart URL"] = valid_df["Walmart URL"].fillna("").astype(str).str.strip()
valid_df = valid_df[valid_df["Walmart URL"].str.contains("walmart.com/ip", case=False, na=False)]

st.write(f"Valid Walmart links ready: **{len(valid_df)}**")

if st.button("Start Scraping", type="primary"):
    if valid_df.empty:
        st.error("Please add at least one valid Walmart product URL.")
    elif not selected_fields:
        st.error("Please select at least one field to scrape.")
    else:
        results = []
        progress = st.progress(0)
        status_box = st.empty()

        for idx, row in valid_df.reset_index(drop=True).iterrows():
            sku = row["SKU"]
            url = row["Walmart URL"]
            status_box.write(f"Scraping {idx + 1} of {len(valid_df)}: {sku} | {url}")
            result = scrape_walmart_product(sku, url, selected_fields, delay_seconds=delay_seconds)
            results.append(result)
            progress.progress((idx + 1) / len(valid_df))

        output_df = pd.DataFrame(results)
        st.session_state["last_output_df"] = output_df
        st.success("Scraping completed.")

if "last_output_df" in st.session_state:
    output_df = st.session_state["last_output_df"]
    st.dataframe(output_df, use_container_width=True)

    csv_data = output_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download CSV",
        data=csv_data,
        file_name="walmart_content_extractor_output.csv",
        mime="text/csv",
    )

    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        output_df.to_excel(writer, index=False, sheet_name="Scraped Output")
        failed_df = output_df[output_df["Status"].isin(["Failed", "Partial"])]
        failed_df.to_excel(writer, index=False, sheet_name="Failed or Partial")
    excel_buffer.seek(0)

    st.download_button(
        "Download Excel",
        data=excel_buffer,
        file_name="walmart_content_extractor_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.markdown('</div>', unsafe_allow_html=True)
