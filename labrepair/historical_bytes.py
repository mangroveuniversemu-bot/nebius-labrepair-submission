"""Restore only a historical CRLF representation proven by its fixed digest.

Git text normalization may store LF while an old receipt pins CRLF. No JSON
reserialization, whitespace stripping, mixed-newline cleanup or new pin is
allowed. The returned bytes must match the existing historical digest exactly.
"""

import hashlib


def pinned_historical_bytes(raw: bytes, expected_sha256: str) -> bytes:
    if hashlib.sha256(raw).hexdigest() == expected_sha256:
        return raw
    if b"\r" not in raw:
        historical = raw.replace(b"\n", b"\r\n")
        if hashlib.sha256(historical).hexdigest() == expected_sha256:
            return historical
    raise ValueError("HISTORICAL_BYTES_MISMATCH")
