"""Authentication helpers for the VisionTrader Python SDK."""

from __future__ import annotations

from visiontrader._credentials import (
    display_path,
    validate_key_id,
    validate_private_key,
    write_key_file,
)


def setup_key(key: str, key_id: str) -> None:
    """
    Save API credentials for automatic login by :class:`~visiontrader.options.VisionOptionsClient`.

    Each key is stored in its own file under ``~/.visiontrader/auth_keys/`` (``%USERPROFILE%\\.visiontrader\\auth_keys\\``
    on Windows), named after ``key_id`` (e.g. ``~/.visiontrader/auth_keys/key_abc123``).

    Parameters
    ----------
    key:
        Private signing key (``vt_sk_live_...`` or ``vt_sk_test_...``).
    key_id:
        API key identifier for the ``X-VT-Key-Id`` header (``key_...``).
    """
    validate_private_key(key)
    validate_key_id(key_id)

    key_path = write_key_file(key_id, private_key=key)
    print(f'✓ Private key saved to {display_path(key_path)} (permissions 600)')
    print()
    print('Next: create VisionOptionsClient(base_url=...) — credentials will load automatically.')
