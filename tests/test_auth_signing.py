from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from visiontrader._auth_signing import build_canonical_string, build_snapshot_auth_headers, canonicalize_query
from visiontrader._credentials import write_default_api_key_id, write_key_file
from visiontrader.options import VisionOptionsClient


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path))
    return tmp_path


def _test_secret_key() -> str:
    seed = b'\x01' * 32
    payload = base64.urlsafe_b64encode(seed).rstrip(b'=').decode('ascii')
    return f'vt_sk_live_{payload}'


def test_canonicalize_query_sorts_and_encodes() -> None:
    query = canonicalize_query({'underlying': 'BTC USDC', 'exchange': 'deribit'})
    assert query == 'exchange=deribit&underlying=BTC%20USDC'


def test_build_canonical_string_matches_spec_shape() -> None:
    canonical = build_canonical_string(
        method='GET',
        path='/options/snapshot',
        params={'exchange': 'deribit', 'underlying': 'BTC'},
        timestamp='1718467200',
        body_sha256_hex='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    )
    assert canonical == (
        'GET\n'
        '/options/snapshot\n'
        'exchange=deribit&underlying=BTC\n'
        '1718467200\n'
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n'
    )


def test_build_snapshot_auth_headers_contains_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('visiontrader._auth_signing.time.time', lambda: 1718467200.0)
    headers = build_snapshot_auth_headers(
        api_key_id='key_abc123',
        secret_key=_test_secret_key(),
        method='GET',
        path='/options/snapshot',
        params={'exchange': 'deribit', 'underlying': 'BTC'},
    )
    assert headers['X-VT-Key-Id'] == 'key_abc123'
    assert headers['X-VT-Timestamp'] == '1718467200'
    assert len(headers['X-VT-Signature']) > 10


def test_snapshot_headers_added_only_after_login(
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('visiontrader._auth_signing.time.time', lambda: 1718467200.0)
    write_key_file('key_abc123', secret_key=_test_secret_key())
    write_default_api_key_id('key_abc123')

    client = VisionOptionsClient(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={'data': []}))))
    headers = client._snapshot_headers(
        path='/options/snapshot',
        params={'exchange': 'deribit', 'underlying': 'BTC'},
    )
    assert headers is not None
    assert headers['X-VT-Key-Id'] == 'key_abc123'

    client_no_key = VisionOptionsClient(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={'data': []}))))
    client_no_key._auth_api_key_id = None
    client_no_key._auth_secret_key = None
    assert client_no_key._snapshot_headers(path='/options/snapshot', params={'exchange': 'deribit'}) is None
