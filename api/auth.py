import base64
from typing import Optional, Tuple

# Credentials are hard-coded for this assignment. In a real system these
# would come from environment variables or a secrets manager
# NEVER from source control.
# Format: { "username": "password" }
VALID_USERS = {
    "admin": "momo2026",
    "suwafa": "team_astro_2026",
    "kaliza": "team_astro_2026",
    "elie": "team_astro_2026",
}

def parse_basic_auth_header(header_value: str) -> Optional[Tuple[str, str]]:
    """Decode an Authorization header into (username, password)."""
    if not header_value:
        return None

    # The header should look like:  "Basic dXNlcm5hbWU6cGFzc3dvcmQ="
    parts = header_value.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "basic":
        return None

    encoded = parts[1]
    try:
        # base64 expects bytes
        decoded_bytes = base64.b64decode(encoded, validate=True)
        decoded = decoded_bytes.decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None

    # username can't contain ':' so split on the first one only
    if ":" not in decoded:
        return None
    username, password = decoded.split(":", 1)
    return username, password


def is_authenticated(header_value: Optional[str]) -> bool:
    """Top-level check used by the request handler."""
    if not header_value:
        return False

    credentials = parse_basic_auth_header(header_value)
    if credentials is None:
        return False

    username, password = credentials

    expected_password = VALID_USERS.get(username)
    return expected_password is not None and expected_password == password
