"""Credentials paths, validation, and persistence helpers."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from visiontrader.exceptions import VisionTraderError

CREDENTIALS_DIR_NAME = '.visiontrader'
AUTH_KEYS_DIR_NAME = 'auth_keys'
DEFAULT_KEY_FILE_NAME = 'default_key'

PRIVATE_KEY_PREFIXES = ('vt_sk_live_', 'vt_sk_test_')
KEY_ID_PATTERN = re.compile(r'^key_[A-Za-z0-9]+$')


@dataclass(frozen=True)
class StoredKey:
    key_id: str
    private_key: str
    placed_at: datetime


def credentials_dir() -> Path:
    return Path.home() / CREDENTIALS_DIR_NAME


def auth_keys_dir() -> Path:
    return credentials_dir() / AUTH_KEYS_DIR_NAME


def key_file_path(key_id: str) -> Path:
    validate_key_id(key_id)
    return auth_keys_dir() / key_id


def default_key_file_path() -> Path:
    return auth_keys_dir() / DEFAULT_KEY_FILE_NAME


def display_path(path: Path) -> str:
    try:
        relative = path.relative_to(Path.home())
    except ValueError:
        return str(path)
    return '~/' + relative.as_posix()


def validate_private_key(key: str) -> None:
    if not isinstance(key, str) or not key:
        raise VisionTraderError('Private key must be a non-empty string.')
    if not any(key.startswith(prefix) for prefix in PRIVATE_KEY_PREFIXES):
        prefixes = ', '.join(repr(prefix) for prefix in PRIVATE_KEY_PREFIXES)
        raise VisionTraderError(f'Private key must start with one of: {prefixes}.')
    payload = key[next(len(prefix) for prefix in PRIVATE_KEY_PREFIXES if key.startswith(prefix)) :]
    if not payload:
        raise VisionTraderError('Private key payload is empty.')


def validate_key_id(key_id: str) -> None:
    if not isinstance(key_id, str) or not key_id:
        raise VisionTraderError('key_id must be a non-empty string.')
    if not KEY_ID_PATTERN.match(key_id):
        raise VisionTraderError("key_id must match the pattern 'key_<id>' (e.g. key_abc123).")


def mask_private_key(key: str) -> str:
    prefix = next(p for p in PRIVATE_KEY_PREFIXES if key.startswith(p))
    payload = key[len(prefix) :]
    visible = payload[:5] if len(payload) >= 5 else payload
    return f'{prefix}{visible}*****'


def key_file_placed_at(path: Path) -> datetime:
    """Local date/time when the key file was last modified on disk."""
    stat = path.stat()
    local_time = time.localtime(stat.st_mtime)
    return datetime(
        local_time.tm_year,
        local_time.tm_mon,
        local_time.tm_mday,
        local_time.tm_hour,
        local_time.tm_min,
        local_time.tm_sec,
    )


def write_key_file(key_id: str, *, private_key: str) -> Path:
    path = key_file_path(key_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f'key_id={key_id}\nprivate_key={private_key}\n'
    path.write_text(content, encoding='utf-8', newline='\n')
    _set_private_file_permissions(path)
    return path


def read_key_file(key_id: str) -> tuple[str, str]:
    path = key_file_path(key_id)
    if not path.is_file():
        raise VisionTraderError(f'Key file not found: {display_path(path)}')

    values: dict[str, str] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line or '=' not in line:
            continue
        name, value = line.split('=', 1)
        values[name.strip()] = value.strip()

    file_key_id = values.get('key_id')
    private_key = values.get('private_key')
    if not file_key_id or not private_key:
        raise VisionTraderError(f'Key file is missing required fields: {display_path(path)}')
    if file_key_id != key_id:
        raise VisionTraderError(
            f'Key file name {key_id!r} does not match key_id field {file_key_id!r} in '
            f'{display_path(path)}'
        )
    validate_private_key(private_key)
    return file_key_id, private_key


def list_stored_keys() -> list[StoredKey]:
    stored: list[StoredKey] = []
    for key_id in list_auth_key_ids():
        path = key_file_path(key_id)
        _, private_key = read_key_file(key_id)
        placed_at = key_file_placed_at(path)
        stored.append(StoredKey(key_id=key_id, private_key=private_key, placed_at=placed_at))
    return stored


def write_default_key_id(key_id: str) -> Path:
    validate_key_id(key_id)
    key_path = key_file_path(key_id)
    if not key_path.is_file():
        raise VisionTraderError(f'Key file not found: {display_path(key_path)}')

    path = default_key_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'{key_id}\n', encoding='utf-8', newline='\n')
    _set_private_file_permissions(path)
    return path


def list_auth_key_ids() -> list[str]:
    directory = auth_keys_dir()
    if not directory.is_dir():
        return []

    key_ids: list[str] = []
    for entry in directory.iterdir():
        if not entry.is_file() or entry.name == DEFAULT_KEY_FILE_NAME:
            continue
        if KEY_ID_PATTERN.match(entry.name):
            key_ids.append(entry.name)
    return sorted(key_ids)


def ensure_default_key_file() -> str | None:
    if default_key_file_path().is_file():
        return read_default_key_id()

    first_key_id = next(iter(list_auth_key_ids()), None)
    if first_key_id is None:
        return None

    write_default_key_id(first_key_id)
    return first_key_id


def read_default_key_id() -> str | None:
    path = default_key_file_path()
    if not path.is_file():
        return None

    key_id = path.read_text(encoding='utf-8').strip()
    if not key_id:
        raise VisionTraderError(f'Default key file is empty: {display_path(path)}')
    validate_key_id(key_id)
    return key_id


def resolve_default_key_file() -> Path | None:
    key_id = ensure_default_key_file()
    if key_id is None:
        return None

    key_path = key_file_path(key_id)
    if not key_path.is_file():
        raise VisionTraderError(
            f'Default key {key_id!r} is set in {display_path(default_key_file_path())}, '
            f'but key file not found: {display_path(key_path)}'
        )
    return key_path


def remove_key_file(key_id: str) -> None:
    validate_key_id(key_id)
    path = key_file_path(key_id)
    if not path.is_file():
        raise VisionTraderError(f'Key file not found: {display_path(path)}')

    was_default = read_default_key_id() == key_id
    path.unlink()

    if was_default:
        reset_default_key_file()


def reset_default_key_file() -> str | None:
    default_path = default_key_file_path()
    first_key_id = next(iter(list_auth_key_ids()), None)
    if first_key_id is None:
        if default_path.is_file():
            default_path.unlink()
        return None

    write_default_key_id(first_key_id)
    return first_key_id


def _set_private_file_permissions(path: Path) -> None:
    if os.name != 'nt':
        path.chmod(0o600)
