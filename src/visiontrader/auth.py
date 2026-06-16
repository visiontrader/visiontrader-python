"""Authentication helpers for the VisionTrader Python SDK."""

from __future__ import annotations

from visiontrader._credentials import (
    StoredKey,
    display_path,
    ensure_default_key_file,
    list_stored_keys,
    mask_private_key,
    validate_key_id,
    validate_private_key,
    write_default_key_id,
    write_key_file,
)


def setup_key(key: str, key_id: str) -> None:
    """
    Save API credentials for automatic login by :class:`~visiontrader.options.VisionOptionsClient`.

    Each key is stored in its own file under ``~/.visiontrader/auth_keys/`` (``%USERPROFILE%\\.visiontrader\\auth_keys\\``
    on Windows), named after ``key_id`` (e.g. ``~/.visiontrader/auth_keys/key_abc123``).

    ``default_key`` is always overwritten to point at the key from this call, so the most
    recently saved key becomes the default for automatic login.

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
    write_default_key_id(key_id)
    print(f'✓ Private key saved to {display_path(key_path)} (permissions 600)')
    print()
    print('Next: create VisionOptionsClient(base_url=...) — credentials will load automatically.')


def _format_keys_table(keys: list[StoredKey], *, default_key_id: str | None) -> str:
    headers = ('key_id', 'private_key', 'placed time')
    rows: list[tuple[str, str, str]] = []
    for key in keys:
        display_key_id = f'{key.key_id}*' if key.key_id == default_key_id else key.key_id
        rows.append(
            (
                display_key_id,
                mask_private_key(key.private_key),
                key.placed_at.strftime('%Y-%m-%d %H:%M'),
            )
        )

    widths = [
        max(len(headers[0]), *(len(row[0]) for row in rows), default=0),
        max(len(headers[1]), *(len(row[1]) for row in rows), default=0),
        max(len(headers[2]), *(len(row[2]) for row in rows), default=0),
    ]
    lines = [
        f'{headers[0]:<{widths[0]}}  {headers[1]:<{widths[1]}}  {headers[2]}',
    ]
    for row in rows:
        lines.append(f'{row[0]:<{widths[0]}}  {row[1]:<{widths[1]}}  {row[2]}')
    return '\n'.join(lines)


def show_keys() -> None:
    """Print installed API keys from ``~/.visiontrader/auth_keys`` as an ASCII table."""
    default_key_id = ensure_default_key_file()
    keys = list_stored_keys()
    if not keys:
        print('No API keys installed.')
        return

    print(_format_keys_table(keys, default_key_id=default_key_id))
