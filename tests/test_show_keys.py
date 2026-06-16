from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from visiontrader._credentials import StoredKey, write_default_key_id, write_key_file
from visiontrader.auth import _format_keys_table, show_keys


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path))
    return tmp_path


def test_show_keys_prints_table_with_default_marker(
    isolated_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_key_file('key_testlocal01', private_key='vt_sk_live_dGVzdEtleUZvckxvY2Fs')
    write_key_file('key_abc123', private_key='vt_sk_live_abc123payloadvalue')
    write_default_key_id('key_abc123')

    show_keys()
    output = capsys.readouterr().out

    assert 'key_id' in output
    assert 'private_key' in output
    assert 'placed time' in output
    assert 'key_testlocal01' in output
    assert 'key_abc123*' in output
    assert 'vt_sk_live_dGVzd*****' in output
    assert 'vt_sk_live_abc12*****' in output


def test_show_keys_prints_message_when_no_keys(
    isolated_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    show_keys()
    assert capsys.readouterr().out.strip() == 'No API keys installed.'


def test_format_keys_table_aligns_columns() -> None:
    placed = datetime(2026, 6, 14, 14, 58)
    table = _format_keys_table(
        [
            StoredKey('key_testlocal01', 'vt_sk_live_dGVzdEtleUZvckxvY2Fs', placed),
            StoredKey('key_abc123', 'vt_sk_live_abc123payloadvalue', placed),
        ],
        default_key_id='key_abc123',
    )
    lines = table.splitlines()
    assert len(lines) == 3
    assert lines[0].startswith('key_id')
    assert 'key_abc123*' in lines[2]
    assert '2026-06-14 14:58' in lines[1]
    assert '2026-06-14 14:58' in lines[2]
