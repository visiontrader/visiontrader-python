"""Shared pytest fixtures."""

from __future__ import annotations

import base64
import secrets

import pytest


@pytest.fixture
def test_credentials() -> tuple[str, str]:
    """Generate a format-valid test private key and key_id."""
    payload = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('ascii')
    return f'vt_sk_live_{payload}', f'key_{secrets.token_hex(6)}'
