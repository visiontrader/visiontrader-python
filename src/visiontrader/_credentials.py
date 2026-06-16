"""Credentials paths, validation, and persistence helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path

from visiontrader.exceptions import VisionTraderError

CREDENTIALS_DIR_NAME = '.visiontrader'
CREDENTIALS_FILE_NAME = 'credentials'
ENV_FILE_NAME = '.env'

ENV_KEY_ID = 'VISIONTRADER_KEY_ID'
ENV_PRIVATE_KEY = 'VISIONTRADER_PRIVATE_KEY'

PRIVATE_KEY_PREFIXES = ('vt_sk_live_', 'vt_sk_test_')
KEY_ID_PATTERN = re.compile(r'^key_[A-Za-z0-9]+$')

SAVE_TARGETS = frozenset({'file', 'env'})


def credentials_dir() -> Path:
    return Path.home() / CREDENTIALS_DIR_NAME


def credentials_file_path() -> Path:
    return credentials_dir() / CREDENTIALS_FILE_NAME


def env_file_path() -> Path:
    return credentials_dir() / ENV_FILE_NAME


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


def normalize_save_to(save_to: str | tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(save_to, str):
        targets = (save_to,)
    elif isinstance(save_to, tuple):
        if not save_to:
            raise VisionTraderError('save_to must include at least one target: "file", "env".')
        if not all(isinstance(item, str) for item in save_to):
            raise VisionTraderError('save_to must be a str or tuple[str, ...].')
        targets = save_to
    else:
        raise VisionTraderError('save_to must be a str or tuple[str, ...].')

    unknown = [target for target in targets if target not in SAVE_TARGETS]
    if unknown:
        allowed = ', '.join(f'"{target}"' for target in sorted(SAVE_TARGETS))
        raise VisionTraderError(f'save_to accepts only {allowed}; got {unknown!r}.')

    return targets


def mask_private_key(key: str) -> str:
    prefix = next(p for p in PRIVATE_KEY_PREFIXES if key.startswith(p))
    payload = key[len(prefix) :]
    visible = payload[:5] if len(payload) >= 5 else payload
    return f'{prefix}{visible}*****'


def write_credentials_file(path: Path, *, key_id: str, private_key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f'key_id={key_id}\nprivate_key={private_key}\n'
    path.write_text(content, encoding='utf-8', newline='\n')
    _set_private_file_permissions(path)


def write_env_file(path: Path, *, key_id: str, private_key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f'{ENV_KEY_ID}={key_id}\n{ENV_PRIVATE_KEY}={private_key}\n'
    path.write_text(content, encoding='utf-8', newline='\n')
    _set_private_file_permissions(path)


def _set_private_file_permissions(path: Path) -> None:
    if os.name != 'nt':
        path.chmod(0o600)
