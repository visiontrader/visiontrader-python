"""Request signing helpers for VisionTrader snapshot endpoints."""

from __future__ import annotations

import base64
import hashlib
import time
from typing import Any
from urllib.parse import quote

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from visiontrader._credentials import SECRET_KEY_PREFIXES
from visiontrader.exceptions import VisionTraderError

EMPTY_BODY_SHA256_HEX = hashlib.sha256(b'').hexdigest()


def build_snapshot_auth_headers(
    *,
    api_key_id: str,
    secret_key: str,
    method: str,
    path: str,
    params: dict[str, Any] | None,
) -> dict[str, str]:
    timestamp = str(int(time.time()))
    canonical = build_canonical_string(
        method=method,
        path=path,
        params=params,
        timestamp=timestamp,
        body_sha256_hex=EMPTY_BODY_SHA256_HEX,
    )
    signature = sign_canonical_string(secret_key, canonical)
    return {
        'X-VT-Key-Id': api_key_id,
        'X-VT-Timestamp': timestamp,
        'X-VT-Signature': signature,
    }


def build_canonical_string(
    *,
    method: str,
    path: str,
    params: dict[str, Any] | None,
    timestamp: str,
    body_sha256_hex: str,
) -> str:
    canonical_query = canonicalize_query(params)
    return f'{method.upper()}\n{path}\n{canonical_query}\n{timestamp}\n{body_sha256_hex}\n'


def canonicalize_query(params: dict[str, Any] | None) -> str:
    if not params:
        return ''
    pairs = []
    for key in sorted(params):
        value = params[key]
        if value is None:
            continue
        encoded_key = quote(str(key), safe='-._~')
        encoded_value = quote(str(value), safe='-._~')
        pairs.append(f'{encoded_key}={encoded_value}')
    return '&'.join(pairs)


def sign_canonical_string(secret_key: str, canonical_string: str) -> str:
    secret_bytes = decode_secret_key_bytes(secret_key)
    signature = Ed25519PrivateKey.from_private_bytes(secret_bytes).sign(canonical_string.encode('utf-8'))
    return base64url_encode(signature)


def decode_secret_key_bytes(secret_key: str) -> bytes:
    prefix = next((p for p in SECRET_KEY_PREFIXES if secret_key.startswith(p)), None)
    if prefix is None:
        raise VisionTraderError('secret_key has unsupported prefix.')
    payload = secret_key[len(prefix) :]
    if not payload:
        raise VisionTraderError('secret_key payload is empty.')
    decoded = base64url_decode(payload)
    if len(decoded) == 32:
        return decoded
    if len(decoded) == 64:
        return decoded[:32]
    raise VisionTraderError('secret_key payload must decode to 32 or 64 bytes for Ed25519.')


def base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')


def base64url_decode(value: str) -> bytes:
    padding = '=' * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode('ascii'))
