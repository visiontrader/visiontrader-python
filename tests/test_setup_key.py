from __future__ import annotations

import os
from pathlib import Path

import pytest

import visiontrader as vt
from visiontrader._credentials import (
    ENV_KEY_ID,
    ENV_PRIVATE_KEY,
    credentials_file_path,
    display_path,
    env_file_path,
    mask_private_key,
    normalize_save_to,
    validate_key_id,
    validate_private_key,
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


@pytest.mark.parametrize(
    ('save_to', 'expected'),
    [
        ('file', ('file',)),
        ('env', ('env',)),
        (('file', 'env'), ('file', 'env')),
    ],
)
def test_normalize_save_to(save_to: str | tuple[str, ...], expected: tuple[str, ...]) -> None:
    assert normalize_save_to(save_to) == expected


@pytest.mark.parametrize(
    'save_to',
    [(), 'both', 123, ['file']],
)
def test_normalize_save_to_rejects_invalid_values(save_to: object) -> None:
    with pytest.raises(VisionTraderError):
        normalize_save_to(save_to)  # type: ignore[arg-type]


def test_mask_private_key_hides_payload(test_credentials: tuple[str, str]) -> None:
    private_key, _ = test_credentials
    masked = mask_private_key(private_key)
    assert masked.startswith('vt_sk_live_')
    assert masked.endswith('*****')
    assert private_key not in masked


def test_setup_key_writes_credentials_file(isolated_home: Path, test_credentials: tuple[str, str]) -> None:
    private_key, key_id = test_credentials
    setup_key(private_key, key_id, save_to='file')

    cred_path = credentials_file_path()
    assert cred_path.exists()
    assert cred_path.read_text(encoding='utf-8') == f'key_id={key_id}\nprivate_key={private_key}\n'
    if os.name != 'nt':
        assert oct(cred_path.stat().st_mode & 0o777) == oct(0o600)


def test_setup_key_writes_env_file(isolated_home: Path, test_credentials: tuple[str, str]) -> None:
    private_key, key_id = test_credentials
    setup_key(private_key, key_id, save_to='env')

    dotenv_path = env_file_path()
    assert dotenv_path.exists()
    assert dotenv_path.read_text(encoding='utf-8') == (
        f'{ENV_KEY_ID}={key_id}\n{ENV_PRIVATE_KEY}={private_key}\n'
    )


def test_setup_key_writes_both_targets(isolated_home: Path, test_credentials: tuple[str, str]) -> None:
    private_key, key_id = test_credentials
    setup_key(private_key, key_id, save_to=('file', 'env'))

    assert credentials_file_path().exists()
    assert env_file_path().exists()


def test_setup_key_exported_from_package(test_credentials: tuple[str, str], isolated_home: Path) -> None:
    private_key, key_id = test_credentials
    vt.setup_key(private_key, key_id, save_to='file')
    assert credentials_file_path().exists()


def test_display_path_uses_tilde(isolated_home: Path) -> None:
    path = isolated_home / '.visiontrader' / 'credentials'
    assert display_path(path) == '~/.visiontrader/credentials'
