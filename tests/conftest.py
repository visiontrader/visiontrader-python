"""Shared pytest fixtures."""

from __future__ import annotations

import base64
import secrets

import pytest


@pytest.fixture
def test_credentials() -> tuple[str, str]:
    """Generate a format-valid test api_key_id and secret_key."""
    payload = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('ascii')
    return f'key_{secrets.token_hex(6)}', f'vt_sk_live_{payload}'
