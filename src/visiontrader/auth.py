"""Authentication helpers for the VisionTrader Python SDK."""

from __future__ import annotations

from visiontrader._credentials import (
    credentials_file_path,
    display_path,
    env_file_path,
    normalize_save_to,
    validate_key_id,
    validate_private_key,
    write_credentials_file,
    write_env_file,
)


def setup_key(
    key: str,
    key_id: str,
    save_to: str | tuple[str, ...] = ('file',),
) -> None:
    """
    Save API credentials for automatic login by :class:`~visiontrader.options.VisionOptionsClient`.

    Parameters
    ----------
    key:
        Private signing key (``vt_sk_live_...`` or ``vt_sk_test_...``).
    key_id:
        API key identifier for the ``X-VT-Key-Id`` header (``key_...``).
    save_to:
        Where to persist credentials: ``"file"``, ``"env"``, or ``("file", "env")``.
        Default: credentials file only (``~/.visiontrader/credentials``).
    """
    validate_private_key(key)
    validate_key_id(key_id)
    targets = normalize_save_to(save_to)

    if 'file' in targets:
        cred_path = credentials_file_path()
        write_credentials_file(cred_path, key_id=key_id, private_key=key)
        print(f'✓ Private key saved to {display_path(cred_path)} (permissions 600)')

    if 'env' in targets:
        dotenv_path = env_file_path()
        write_env_file(dotenv_path, key_id=key_id, private_key=key)
        print(f'✓ Private key written to {display_path(dotenv_path)} as VISIONTRADER_PRIVATE_KEY')
        print()
        print('⚠ Add .env to .gitignore. Never commit private keys.')

    print()
    print('Next: create VisionOptionsClient(base_url=...) — credentials will load automatically.')
