import json
from pathlib import Path
import streamlit as st

CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
ALLOWED_DOMAIN = "@pattern.com"


def load_credentials():
    if not CREDENTIALS_FILE.exists():
        return []
    try:
        data = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
        return data.get("users", [])
    except Exception:
        return []


def is_valid_login(email: str, password: str) -> bool:
    email = (email or "").strip().lower()
    password = password or ""

    if not email.endswith(ALLOWED_DOMAIN):
        return False

    users = load_credentials()
    for user in users:
        saved_email = str(user.get("email", "")).strip().lower()
        saved_password = str(user.get("password", ""))
        if email == saved_email and password == saved_password:
            return True
    return False


def show_login_page():
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background: #f4f7fd;
        }
        [data-testid="stHeader"] {
            background: rgba(0,0,0,0);
        }
        [data-testid="stToolbar"] {
            display: none;
        }
        .block-container {
            max-width: 100% !important;
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        .login-outer {
            min-height: 82vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding-top: 55px;
        }
        .login-card {
            width: 560px;
            min-height: 455px;
            background: #ffffff;
            border-radius: 20px;
            padding: 58px 45px 38px 45px;
            box-shadow: 0 22px 55px rgba(30, 45, 90, 0.10);
        }
        .login-title {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 32px;
            font-weight: 700;
            color: #000000;
            margin-bottom: 22px;
        }
        .login-subtitle {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 17px;
            color: #555555;
            margin-bottom: 26px;
        }
        .login-note {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 15px;
            color: #606060;
            text-align: center;
            margin-top: 18px;
            line-height: 1.25;
        }
        .login-footer {
            text-align: center;
            font-family: Georgia, 'Times New Roman', serif;
            color: #555555;
            font-size: 15px;
            margin-top: -12px;
        }
        div[data-testid="stTextInput"] label {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 20px;
            color: #000000;
            font-weight: 400;
        }
        div[data-testid="stTextInput"] input {
            height: 50px;
            border-radius: 10px;
            font-size: 16px;
            padding-left: 14px;
        }
        div.stButton > button:first-child {
            width: 100%;
            height: 54px;
            border-radius: 11px;
            background: #0f5be8;
            color: white;
            font-size: 16px;
            font-weight: 700;
            border: none;
            margin-top: 8px;
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

    left, center, right = st.columns([1, 1.05, 1])
    with center:
        st.markdown('<div class="login-outer"><div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Walmart Content Extractor</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Only approved @pattern.com users can access this tool</div>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email Address", placeholder="you@pattern.com")
            password = st.text_input("Password", placeholder="Enter password", type="password")
            submitted = st.form_submit_button("Sign In")

        if submitted:
            if is_valid_login(email, password):
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = email.strip().lower()
                st.rerun()
            else:
                st.error("Invalid email or password.")

        st.markdown(
            '<div class="login-note">New to this page? Please contact Pratik Adsare for creating your login<br>credential</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="login-footer">© Designed and Developed by Pratik Adsare</div>', unsafe_allow_html=True)
