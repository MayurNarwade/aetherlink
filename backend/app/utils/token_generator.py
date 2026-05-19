"""
Secure token generation utilities.

Session IDs, OTPs, and peer tokens with cryptographic entropy.
"""

import secrets
import string


def generate_session_id() -> str:
    """
    Generate secure session ID.

    Format: random alphanumeric string (12 chars)
    Entropy: 12 * 5.95 bits = ~71 bits
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))


def generate_otp() -> str:
    """
    Generate 6-digit OTP.

    Format: numeric only (000000-999999)
    Entropy: 6 * 3.32 bits = ~20 bits
    """
    return "".join(secrets.choice(string.digits) for _ in range(6))


def generate_peer_token() -> str:
    """
    Generate secure peer token.

    Format: random alphanumeric string (32 chars)
    Entropy: 32 * 5.95 bits = ~190 bits (128+ bits required)
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))
