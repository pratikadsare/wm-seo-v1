"""Simple file-based authentication for the Streamlit app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CREDENTIALS_FILE = Path(__file__).with_name("credentials.json")


def load_credentials(path: Path = DEFAULT_CREDENTIALS_FILE) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return None, f"Credentials file not found: {path.name}"
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {path.name}: {exc}"
    except OSError as exc:
        return None, f"Could not read {path.name}: {exc}"

    if not isinstance(data, dict):
        return None, f"{path.name} must contain a JSON object."
    if "users" not in data or not isinstance(data["users"], list):
        return None, f"{path.name} must contain a users list."
    return data, ""


def authenticate(email: str, password: str, path: Path = DEFAULT_CREDENTIALS_FILE) -> tuple[bool, str]:
    email_clean = (email or "").strip().lower()
    password_value = password or ""

    data, error = load_credentials(path)
    if error:
        return False, error
    assert data is not None

    allowed_domain = str(data.get("allowed_domain", "@pattern.com")).strip().lower()
    users = data.get("users", [])

    if not email_clean or not password_value:
        return False, "Please enter both email and password."
    if allowed_domain and not email_clean.endswith(allowed_domain):
        return False, f"Only approved {allowed_domain} users can access this tool."
    if not users:
        return False, "No users are configured. Add users inside credentials.json first."

    for user in users:
        if not isinstance(user, dict):
            continue
        stored_email = str(user.get("email", "")).strip().lower()
        stored_password = str(user.get("password", ""))
        active = bool(user.get("active", True))
        if stored_email == email_clean and stored_password == password_value and active:
            return True, ""

    return False, "Invalid email or password."
