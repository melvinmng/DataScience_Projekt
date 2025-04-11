import pytest
import os
from unittest.mock import patch


def test_load_channel_id_success(monkeypatch):
    """Tests loading a valid channel ID."""
    from src.env_management.youtube_channel_id import load_channel_id

    valid_id = "UC" + "a" * 22
    monkeypatch.setenv("CHANNEL_ID", valid_id)
    assert load_channel_id() == valid_id


def test_load_channel_id_missing(monkeypatch):
    """Tests when the CHANNEL_ID environment variable is not set."""
    from src.env_management.youtube_channel_id import load_channel_id

    monkeypatch.delenv("CHANNEL_ID", raising=False)
    with pytest.raises(ValueError, match="CHANNEL_ID nicht gefunden"):
        load_channel_id()


def test_load_channel_id_incorrect_length(monkeypatch):
    """Tests when the channel ID has incorrect length."""
    from src.env_management.youtube_channel_id import load_channel_id

    invalid_id_short = "UCabc"
    invalid_id_long = "UC" + "a" * 23

    monkeypatch.setenv("CHANNEL_ID", invalid_id_short)
    with pytest.raises(ValueError, match="muss 24 Zeichen lang sein"):
        load_channel_id()

    monkeypatch.setenv("CHANNEL_ID", invalid_id_long)
    with pytest.raises(ValueError, match="muss 24 Zeichen lang sein"):
        load_channel_id()
