from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from visiontrader import VisionOptionsClient
from visiontrader._credentials import write_default_api_key_id, write_key_file
from visiontrader.auth import get_default_key, get_key
from visiontrader.exceptions import VisionTraderError


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path))
    return tmp_path


def test_get_key_loads_specific_key(isolated_home: Path) -> None:
    write_key_file('key_abc123', secret_key='vt_sk_live_abc123payloadvalue')
    write_key_file('key_def456', secret_key='vt_sk_live_def456payloadvalue')

    api_key_id, secret_key = get_key('key_def456')

    assert api_key_id == 'key_def456'
    assert secret_key == 'vt_sk_live_def456payloadvalue'


def test_get_default_key_uses_default_key_file(isolated_home: Path) -> None:
    write_key_file('key_abc123', secret_key='vt_sk_live_abc123payloadvalue')
    write_key_file('key_def456', secret_key='vt_sk_live_def456payloadvalue')
    write_default_api_key_id('key_abc123')

    api_key_id, secret_key = get_default_key()

    assert api_key_id == 'key_abc123'
    assert secret_key == 'vt_sk_live_abc123payloadvalue'


def test_get_default_key_raises_when_no_keys(isolated_home: Path) -> None:
    with pytest.raises(VisionTraderError, match='No API key found'):
        get_default_key()


def _noop_transport() -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: httpx.Response(200, json={'data': []}))


def test_login_loads_default_key(isolated_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_key_file('key_abc123', secret_key='vt_sk_live_abc123payloadvalue')
    write_default_api_key_id('key_abc123')

    client = VisionOptionsClient(client=httpx.Client(transport=_noop_transport()))

    assert client._auth_api_key_id == 'key_abc123'
    assert client._auth_secret_key == 'vt_sk_live_abc123payloadvalue'
    output = capsys.readouterr().out
    assert "Options client will be using secret key 'vt_sk_live_abc12*****'" in output
    assert '~/.visiontrader/auth_keys/key_abc123' in output


def test_login_with_api_key_id(isolated_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_key_file('key_abc123', secret_key='vt_sk_live_abc123payloadvalue')
    write_key_file('key_def456', secret_key='vt_sk_live_def456payloadvalue')
    write_default_api_key_id('key_abc123')

    client = VisionOptionsClient(client=httpx.Client(transport=_noop_transport()))
    capsys.readouterr()

    client.login('key_def456')

    assert client._auth_api_key_id == 'key_def456'
    assert client._auth_secret_key == 'vt_sk_live_def456payloadvalue'
    assert 'key_def456' in capsys.readouterr().out


def test_client_init_skips_login_when_no_keys(
    isolated_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = VisionOptionsClient(client=httpx.Client(transport=_noop_transport()))

    assert client._auth_api_key_id is None
    assert client._auth_secret_key is None
    assert capsys.readouterr().out == ''
