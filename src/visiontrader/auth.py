"""Authentication helpers for the VisionTrader Python SDK."""

from __future__ import annotations

from visiontrader._credentials import (
    StoredKey,
    display_path,
    ensure_default_key_file,
    list_stored_keys,
    mask_secret_key,
    read_key_file,
    remove_key_file,
    validate_api_key_id,
    validate_secret_key,
    write_default_api_key_id,
    write_key_file,
)


def setup_key(api_key_id: str, secret_key: str) -> None:
    """
    Save API credentials for automatic login by :class:`~visiontrader.options.VisionOptionsClient`.

    Each key is stored in its own file under ``~/.visiontrader/auth_keys/`` (``%USERPROFILE%\\.visiontrader\\auth_keys\\``
    on Windows), named after ``api_key_id`` (e.g. ``~/.visiontrader/auth_keys/key_abc123``).

    ``default_key`` is always overwritten to point at the key from this call, so the most
    recently saved key becomes the default for automatic login.

    Parameters
    ----------
    api_key_id:
        API key identifier for the ``X-VT-Key-Id`` header (``key_...``).
    secret_key:
        Secret signing key (``vt_sk_live_...`` or ``vt_sk_test_...``).
    """
    validate_api_key_id(api_key_id)
    validate_secret_key(secret_key)

    key_path = write_key_file(api_key_id, secret_key=secret_key)
    write_default_api_key_id(api_key_id)
    print(f'✓ Secret key saved to {display_path(key_path)} (permissions 600)')


def set_default_key(api_key_id: str) -> None:
    """
    Set the default API key used for automatic login.

    Updates ``~/.visiontrader/auth_keys/default_key`` to point at an existing key file.

    Parameters
    ----------
    api_key_id:
        API key identifier (``key_...``). The corresponding file must already exist under
        ``~/.visiontrader/auth_keys/``.
    """
    validate_api_key_id(api_key_id)
    write_default_api_key_id(api_key_id)
    print(f'✓ Default key set to {api_key_id}')


def remove_key(api_key_id: str) -> None:
    """
    Remove an installed API key from ``~/.visiontrader/auth_keys``.

    If the removed key is the current default, ``default_key`` is recreated to point at the
    first remaining key (alphabetically), or removed when no keys are left.

    Parameters
    ----------
    api_key_id:
        API key identifier (``key_...``) to delete.
    """
    validate_api_key_id(api_key_id)
    remove_key_file(api_key_id)
    print(f'✓ Removed key {api_key_id}')


def get_key(api_key_id: str) -> tuple[str, str]:
    """
    Load a validated API key pair from ``~/.visiontrader/auth_keys/<api_key_id>``.

    Returns
    -------
    tuple[str, str]
        ``(api_key_id, secret_key)``
    """
    validate_api_key_id(api_key_id)
    return read_key_file(api_key_id)


def get_default_key() -> tuple[str, str]:
    """
    Load the default API key pair from ``~/.visiontrader/auth_keys``.

    Uses ``default_key`` when present; otherwise creates it from the first stored key.

    Returns
    -------
    tuple[str, str]
        ``(api_key_id, secret_key)``

    Raises
    ------
    VisionTraderError
        If no API keys are installed.
    """
    default_api_key_id = ensure_default_key_file()
    if default_api_key_id is None:
        raise VisionTraderError(
            'No API key found in ~/.visiontrader/auth_keys. '
            'Run vt.setup_key(api_key_id, secret_key) first.'
        )
    return read_key_file(default_api_key_id)


def _format_keys_table(keys: list[StoredKey], *, default_api_key_id: str | None) -> str:
    headers = ('api_key_id', 'secret_key', 'placed_time')
    rows: list[tuple[str, str, str]] = []
    for key in keys:
        display_api_key_id = (
            f'{key.api_key_id}*' if key.api_key_id == default_api_key_id else key.api_key_id
        )
        rows.append(
            (
                display_api_key_id,
                mask_secret_key(key.secret_key),
                key.placed_at.strftime('%Y-%m-%d %H:%M'),
            )
        )

    widths = [
        max([len(headers[0]), *(len(row[0]) for row in rows)]),
        max([len(headers[1]), *(len(row[1]) for row in rows)]),
        max([len(headers[2]), *(len(row[2]) for row in rows)]),
    ]
    lines = [
        f'{headers[0]:<{widths[0]}}  {headers[1]:<{widths[1]}}  {headers[2]}',
    ]
    for row in rows:
        lines.append(f'{row[0]:<{widths[0]}}  {row[1]:<{widths[1]}}  {row[2]}')
    return '\n'.join(lines)


def show_keys() -> None:
    """Print installed API keys from ``~/.visiontrader/auth_keys`` as an ASCII table."""
    default_api_key_id = ensure_default_key_file()
    keys = list_stored_keys()
    if not keys:
        print('No API keys installed.')
        return

    print(_format_keys_table(keys, default_api_key_id=default_api_key_id))
