from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path

import pytest

import visiontrader as vt
from visiontrader._credentials import (
    auth_keys_dir,
    default_key_file_path,
    display_path,
    ensure_default_key_file,
    key_file_path,
    mask_private_key,
    read_default_key_id,
    resolve_default_key_file,
    validate_key_id,
    validate_private_key,
    write_default_key_id,
    write_key_file,
)
from visiontrader.auth import setup_key
from visiontrader.exceptions import VisionTraderError


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path))
    return tmp_path


def test_validate_private_key_accepts_live_and_test_prefixes(test_credentials: tuple[str, str]) -> None:
    private_key, _ = test_credentials
    validate_private_key(private_key)
    validate_private_key(private_key.replace('vt_sk_live_', 'vt_sk_test_'))


def test_validate_private_key_rejects_invalid_prefix() -> None:
    with pytest.raises(VisionTraderError, match='must start with'):
        validate_private_key('sk_live_abc')


def test_validate_key_id_accepts_expected_format() -> None:
    validate_key_id('key_abc123')


def test_validate_key_id_rejects_invalid_format() -> None:
    with pytest.raises(VisionTraderError, match='key_<id>'):
        validate_key_id('abc123')


def test_mask_private_key_hides_payload(test_credentials: tuple[str, str]) -> None:
    private_key, _ = test_credentials
    masked = mask_private_key(private_key)
    assert masked.startswith('vt_sk_live_')
    assert masked.endswith('*****')
    assert private_key not in masked


def test_setup_key_writes_key_file(isolated_home: Path, test_credentials: tuple[str, str]) -> None:
    private_key, key_id = test_credentials
    setup_key(private_key, key_id)

    key_path = key_file_path(key_id)
    assert key_path.exists()
    assert key_path.parent == auth_keys_dir()
    assert key_path.read_text(encoding='utf-8') == f'key_id={key_id}\nprivate_key={private_key}\n'
    assert read_default_key_id() == key_id
    assert default_key_file_path().read_text(encoding='utf-8') == f'{key_id}\n'
    if os.name != 'nt':
        assert oct(key_path.stat().st_mode & 0o777) == oct(0o600)


def _make_test_credentials() -> tuple[str, str]:
    payload = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('ascii')
    return f'vt_sk_live_{payload}', f'key_{secrets.token_hex(6)}'


def test_setup_key_stores_multiple_keys_without_overwrite(isolated_home: Path) -> None:
    first_key, first_id = _make_test_credentials()
    second_key, second_id = _make_test_credentials()

    setup_key(first_key, first_id)
    setup_key(second_key, second_id)

    assert key_file_path(first_id).read_text(encoding='utf-8') == (
        f'key_id={first_id}\nprivate_key={first_key}\n'
    )
    assert key_file_path(second_id).read_text(encoding='utf-8') == (
        f'key_id={second_id}\nprivate_key={second_key}\n'
    )
    assert read_default_key_id() == second_id


def test_resolve_default_key_file_uses_default_key(isolated_home: Path) -> None:
    first_key, first_id = _make_test_credentials()
    second_key, second_id = _make_test_credentials()

    write_key_file(first_id, private_key=first_key)
    write_key_file(second_id, private_key=second_key)
    write_default_key_id(first_id)

    assert resolve_default_key_file() == key_file_path(first_id)


def test_resolve_default_key_file_returns_none_when_missing(isolated_home: Path) -> None:
    assert resolve_default_key_file() is None


def test_resolve_default_key_file_creates_default_key_from_first_key(isolated_home: Path) -> None:
    write_key_file('key_def456', private_key='vt_sk_live_def456payload')
    write_key_file('key_abc123', private_key='vt_sk_live_abc123payload')

    assert not default_key_file_path().exists()

    assert resolve_default_key_file() == key_file_path('key_abc123')
    assert read_default_key_id() == 'key_abc123'
    assert default_key_file_path().read_text(encoding='utf-8') == 'key_abc123\n'


def test_resolve_default_key_file_raises_when_key_file_missing(isolated_home: Path) -> None:
    default_key_file_path().parent.mkdir(parents=True)
    default_key_file_path().write_text('key_missing\n', encoding='utf-8')

    with pytest.raises(VisionTraderError, match='key file not found'):
        resolve_default_key_file()


def test_setup_key_exported_from_package(test_credentials: tuple[str, str], isolated_home: Path) -> None:
    private_key, key_id = test_credentials
    vt.setup_key(private_key, key_id)
    assert key_file_path(key_id).exists()


def test_display_path_uses_tilde(isolated_home: Path) -> None:
    path = isolated_home / '.visiontrader' / 'auth_keys' / 'key_abc123'
    assert display_path(path) == '~/.visiontrader/auth_keys/key_abc123'
