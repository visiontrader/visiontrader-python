from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from visiontrader.auth import test_key
from visiontrader._credentials import write_default_api_key_id, write_key_file
from visiontrader.exceptions import ApiError, VisionTraderError


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path))
    return tmp_path


def _test_secret_key() -> str:
    seed = b'\x02' * 32
    payload = base64.urlsafe_b64encode(seed).rstrip(b'=').decode('ascii')
    return f'vt_sk_live_{payload}'


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(
        base_url='http://testserver',
        transport=httpx.MockTransport(handler),
    )


def test_test_key_with_explicit_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={'data': {'verify': 'success', 'api_key_id': 'key_abc123'}},
        )

    test_key(
        'key_abc123',
        _test_secret_key(),
        base_url='http://testserver',
        client=_mock_client(handler),
    )

    assert len(captured) == 1
    request = captured[0]
    assert request.method == 'GET'
    assert request.url.path == '/auth/test_key'
    assert request.headers['X-VT-Key-Id'] == 'key_abc123'
    assert request.headers['X-VT-Timestamp']
    assert request.headers['X-VT-Signature']
    assert "✓ API key 'key_abc123' is valid" in capsys.readouterr().out


def test_test_key_uses_default_key(isolated_home: Path) -> None:
    write_key_file('key_abc123', secret_key=_test_secret_key())
    write_default_api_key_id('key_abc123')

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={'data': {'verify': 'success', 'api_key_id': 'key_abc123'}},
        )

    test_key(base_url='http://testserver', client=_mock_client(handler))

    assert captured[0].headers['X-VT-Key-Id'] == 'key_abc123'


def test_test_key_requires_both_or_neither_credential() -> None:
    with pytest.raises(VisionTraderError, match='both api_key_id and secret_key'):
        test_key(api_key_id='key_abc123')

    with pytest.raises(VisionTraderError, match='both api_key_id and secret_key'):
        test_key(secret_key=_test_secret_key())


def test_test_key_raises_on_server_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={
                'error': 'invalid_signature',
                'message': 'Detached signature must be 64 bytes (Ed25519).',
            },
        )

    with pytest.raises(ApiError, match='invalid_signature: Detached signature must be 64 bytes') as exc_info:
        test_key(
            'key_abc123',
            _test_secret_key(),
            base_url='http://testserver',
            client=_mock_client(handler),
        )

    assert exc_info.value.error_code == 'invalid_signature'
    assert exc_info.value.status_code == 401
