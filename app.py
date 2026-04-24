from __future__ import annotations

import time
from io import BytesIO
from typing import Iterable

import pandas as pd
import requests
import streamlit as st

from auth import authenticate
from scraper import BASE_COLUMNS, FIELD_DEFINITIONS, FIELD_KEYS, FIELD_LABELS, scrape_walmart_product


APP_TITLE = "Walmart Content Extractor"
APP_SUBTITLE = "Only approved @pattern.com users can access this tool"


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)


LOGIN_CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background: #f5f7ff;
}
[data-testid="stHeader"] {
    background: rgba(245, 247, 255, 0.95);
}
.block-container {
    padding-top: 6.0rem;
    padding-bottom: 1.8rem;
    max-width: 980px;
}
div[data-testid="stForm"] {
    width: 620px;
    max-width: calc(100vw - 48px);
    margin: 0 auto;
    background: #ffffff;
    border: 1px solid rgba(17, 24, 39, 0.04);
    border-radius: 22px;
    padding: 48px 44px 38px 44px;
    box-shadow: 0 24px 70px rgba(30, 41, 59, 0.10);
}
div[data-testid="stForm"] h1 {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 34px;
    line-height: 1.15;
    color: #050505;
    margin: 0 0 18px 0;
    font-weight: 700;
}
div[data-testid="stForm"] .login-subtitle {
    font-family: Georgia, 'Times New Roman', serif;
    color: #505866;
    font-size: 17px;
    margin: 0 0 28px 0;
}
div[data-testid="stForm"] label p {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 20px;
    color: #050505;
    margin-bottom: 6px;
}
div[data-testid="stForm"] input {
    border-radius: 12px !important;
    min-height: 48px;
    font-size: 17px !important;
}
div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    min-height: 58px;
    border-radius: 13px;
    background: #0b5be7;
    border: 1px solid #0b5be7;
    font-size: 18px;
    font-weight: 700;
    margin-top: 12px;
}
div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
    background: #074fcb;
    border-color: #074fcb;
}
.login-help {
    font-family: Georgia, 'Times New Roman', serif;
    color: #555e6e;
    text-align: center;
    font-size: 16px;
    margin-top: 20px;
    line-height: 1.2;
}
.login-footer {
    font-family: Georgia, 'Times New Roman', serif;
    color: #6b7280;
    text-align: center;
    font-size: 16px;
    margin-top: 48px;
}
.stAlert {
    width: 620px;
    max-width: calc(100vw - 48px);
    margin-left: auto;
    margin-right: auto;
}
</style>
"""


APP_CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background: #f7f9fd;
}
[data-testid="stHeader"] {
    background: rgba(247, 249, 253, 0.95);
}
.block-container {
    padding-top: 2.0rem;
    padding-bottom: 3rem;
}
.main-card {
    background: #ffffff;
    border: 1px solid rgba(17, 24, 39, 0.07);
    border-radius: 20px;
    padding: 24px 28px;
    box-shadow: 0 14px 40px rgba(30, 41, 59, 0.06);
    margin-bottom: 20px;
}
.small-muted {
    color: #667085;
    font-size: 0.95rem;
}
.strict-note {
    background: #eef4ff;
    border: 1px solid #d6e4ff;
    color: #1d3b72;
    border-radius: 14px;
    padding: 14px 16px;
    margin: 10px 0 20px 0;
}
</style>
"""


def ensure_state() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user_email", "")
    st.session_state.setdefault("last_results", None)


def render_login() -> None:
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        st.markdown(f"<h1>{APP_TITLE}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p class='login-subtitle'>{APP_SUBTITLE}</p>", unsafe_allow_html=True)
        email = st.text_input("Email Address", placeholder="you@pattern.com", key="login_email")
        password = st.text_input("Password", placeholder="Enter password", type="password", key="login_password")
        submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
        st.markdown(
            "<div class='login-help'>New to this page? Please contact Pratik Adsare for creating your login<br>credential</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='login-footer'>© Designed and Developed by Pratik Adsare</div>", unsafe_allow_html=True)

    if submitted:
        ok, message = authenticate(email, password)
        if ok:
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = email.strip().lower()
            st.rerun()
        else:
            st.error(message)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Scraped Data")
        worksheet = writer.sheets["Scraped Data"]
        for column_cells in worksheet.columns:
            header = str(column_cells[0].value or "")
            max_length = max(len(str(cell.value or "")) for cell in column_cells[:50])
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, len(header) + 2), 60)
    return output.getvalue()


def normalize_uploaded_df(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)


def render_input_section() -> tuple[pd.DataFrame | None, str | None, str | None]:
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    st.subheader("1. Add SKU and Walmart links")
    input_method = st.radio(
        "Choose input method",
        ["Paste SKU + URL table", "Upload CSV / Excel"],
        horizontal=True,
        label_visibility="collapsed",
    )

    df: pd.DataFrame | None = None
    sku_col: str | None = None
    url_col: str | None = None

    if input_method == "Paste SKU + URL table":
        starter = pd.DataFrame(
            {
                "SKU": ["", "", ""],
                "Walmart URL": ["", "", ""],
            }
        )
        df = st.data_editor(
            starter,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "SKU": st.column_config.TextColumn("SKU", help="Your internal SKU or identifier"),
                "Walmart URL": st.column_config.LinkColumn("Walmart URL", help="Walmart product link"),
            },
            key="manual_input_table",
        )
        sku_col = "SKU"
        url_col = "Walmart URL"
        st.caption("Tip: You can paste two Excel columns directly into this table: SKU and Walmart URL.")

    else:
        uploaded_file = st.file_uploader("Upload file", type=["csv", "xlsx"])
        if uploaded_file is not None:
            try:
                df = normalize_uploaded_df(uploaded_file)
                st.dataframe(df.head(20), use_container_width=True)
                columns = list(df.columns)
                sku_col = st.selectbox("Select SKU column", columns, index=0)
                guessed_url_index = 0
                for idx, col in enumerate(columns):
                    if "url" in str(col).lower() or "link" in str(col).lower():
                        guessed_url_index = idx
                        break
                url_col = st.selectbox("Select Walmart URL column", columns, index=guessed_url_index)
            except Exception as exc:
                st.error(f"Could not read uploaded file: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)
    return df, sku_col, url_col


def render_field_selector() -> list[str]:
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    st.subheader("2. Select fields to scrape")
    st.markdown(
        "<div class='strict-note'>Strict mode is built in: image output comes only from SKU/PDP product image data, PNG/UI/logo/rating assets are skipped, and bullets/descriptions are copied only from original PDP structured fields.</div>",
        unsafe_allow_html=True,
    )

    select_all = st.checkbox("Select all content fields", value=True)
    selected: list[str] = []
    cols = st.columns(3)
    for index, (key, label) in enumerate(FIELD_DEFINITIONS):
        with cols[index % 3]:
            checked = st.checkbox(label, value=select_all, key=f"field_{key}")
            if checked:
                selected.append(key)

    st.caption("Output always includes SKU, Walmart URL, Walmart Item ID, Status, and Error.")
    st.markdown("</div>", unsafe_allow_html=True)
    return selected


def build_records(df: pd.DataFrame, sku_col: str, url_col: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    if df is None or df.empty:
        return records

    for _, row in df.iterrows():
        sku = "" if pd.isna(row.get(sku_col, "")) else str(row.get(sku_col, "")).strip()
        url = "" if pd.isna(row.get(url_col, "")) else str(row.get(url_col, "")).strip()
        if not sku and not url:
            continue
        records.append({"sku": sku, "url": url})
    return records


def render_downloads(df: pd.DataFrame) -> None:
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    excel_bytes = to_excel_bytes(df)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="walmart_scraped_catalog_data.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download Excel",
            data=excel_bytes,
            file_name="walmart_scraped_catalog_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def scrape_records(records: list[dict[str, str]], selected_fields: Iterable[str], delay_seconds: float, timeout: int) -> pd.DataFrame:
    results = []
    progress = st.progress(0)
    status_placeholder = st.empty()
    total = len(records)

    session = requests.Session()
    for index, record in enumerate(records, start=1):
        sku = record.get("sku", "")
        url = record.get("url", "")
        status_placeholder.info(f"Scraping {index}/{total}: {sku or url}")
        result = scrape_walmart_product(
            sku=sku,
            url=url,
            selected_fields=selected_fields,
            timeout=timeout,
            session=session,
        )
        results.append(result)
        progress.progress(index / total)
        if index < total and delay_seconds > 0:
            time.sleep(delay_seconds)

    status_placeholder.success("Scraping completed.")
    return pd.DataFrame(results)


def render_app() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.write(f"Signed in as **{st.session_state.get('user_email', '')}**")
        if st.button("Sign out", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user_email"] = ""
            st.session_state["last_results"] = None
            st.rerun()

    st.title(APP_TITLE)
    st.write("Internal catalog SKU extraction tool for Walmart PDP links.")

    df, sku_col, url_col = render_input_section()
    selected_fields = render_field_selector()

    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    st.subheader("3. Scrape settings")
    c1, c2, c3 = st.columns(3)
    with c1:
        delay_seconds = st.number_input("Delay between URLs", min_value=0.0, max_value=30.0, value=1.5, step=0.5)
    with c2:
        timeout = st.number_input("Request timeout seconds", min_value=5, max_value=90, value=25, step=5)
    with c3:
        st.write("Base output columns")
        st.caption(", ".join(BASE_COLUMNS))

    start = st.button("Start Scraping", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if start:
        if df is None or sku_col is None or url_col is None:
            st.error("Please add or upload SKU and URL data first.")
            return
        if not selected_fields:
            st.error("Please select at least one field to scrape.")
            return

        records = build_records(df, sku_col, url_col)
        if not records:
            st.error("No rows found. Add at least one SKU and Walmart URL.")
            return

        with st.spinner("Scraping PDP data..."):
            output_df = scrape_records(records, selected_fields, float(delay_seconds), int(timeout))
        st.session_state["last_results"] = output_df

    if st.session_state.get("last_results") is not None:
        output_df = st.session_state["last_results"]
        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        st.subheader("Scrape output")
        st.dataframe(output_df, use_container_width=True)
        render_downloads(output_df)

        failed = output_df[output_df["Status"].astype(str).str.lower().isin(["failed", "blocked", "not found", "invalid url", "partial"])]
        if not failed.empty:
            with st.expander("Review failed / partial rows"):
                st.dataframe(failed, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


ensure_state()
if st.session_state["authenticated"]:
    render_app()
else:
    render_login()
