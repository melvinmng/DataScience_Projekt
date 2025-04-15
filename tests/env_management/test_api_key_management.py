import pytest
import os
from unittest.mock import patch, MagicMock, call


def test_get_api_key_success(monkeypatch):
    """Tests retrieving an existing environment variable."""
    from src.env_management.api_key_management import get_api_key

    api_key_name = "MY_TEST_API_KEY"
    api_key_value = "12345abcdef"
    monkeypatch.setenv(api_key_name, api_key_value)
    assert get_api_key(api_key_name) == api_key_value


def test_get_api_key_not_set(monkeypatch):
    """Tests retrieving a non-existent environment variable."""
    from src.env_management.api_key_management import get_api_key

    api_key_name = "NON_EXISTENT_KEY"
    monkeypatch.delenv(api_key_name, raising=False)
    assert get_api_key(api_key_name) is None


@patch("os.getenv", side_effect=ValueError("Getenv Error"))
def test_get_api_key_value_error(mock_getenv):
    """Tests handling of ValueError during os.getenv."""
    from src.env_management.api_key_management import get_api_key

    assert get_api_key("SOME_KEY") is None


@patch("os.getenv", side_effect=Exception("Unexpected Error"))
def test_get_api_key_generic_exception(mock_getenv):
    """Tests handling of unexpected errors during os.getenv."""
    from src.env_management.api_key_management import get_api_key

    assert get_api_key("SOME_KEY") is None


@patch("src.env_management.api_key_management.build")
def test_create_youtube_client(mock_build):
    """Tests the creation of the YouTube client resource."""
    from src.env_management.api_key_management import create_youtube_client

    api_key = "fake_youtube_key"
    mock_build.return_value = MagicMock()

    client = create_youtube_client(api_key)

    mock_build.assert_called_once_with("youtube", "v3", developerKey=api_key)
    assert client == mock_build.return_value


@patch("src.env_management.api_key_management.get_api_key")
@patch("src.env_management.api_key_management.create_youtube_client")
@patch("builtins.print")
def test_main_block_execution(mock_print, mock_create_client, mock_get_key):
    """Tests the code execution within the main guard."""

    # Scenario 1: Both keys found
    mock_get_key.side_effect = ["google_key_value", "youtube_key_value"]
    mock_create_client.return_value = MagicMock()

    from src.env_management.api_key_management import main

    main()

    mock_get_key.assert_has_calls([call("TOKEN_GOOGLEAPI"), call("YOUTUBE_API_KEY")])
    mock_print.assert_has_calls(
        [
            call("Google API Key loaded:", "google_key_value"),
            call("YouTube API Client successfully created."),
        ]
    )
    mock_create_client.assert_called_once_with("youtube_key_value")

    # Scenario 2: YouTube key missing
    mock_get_key.reset_mock()
    mock_print.reset_mock()
    mock_create_client.reset_mock()
    mock_get_key.side_effect = ["google_key_value", None]

    main()

    mock_get_key.assert_has_calls([call("TOKEN_GOOGLEAPI"), call("YOUTUBE_API_KEY")])
    mock_print.assert_has_calls(
        [
            call("Google API Key loaded:", "google_key_value"),
            call("YouTube API Key not found or is None."),
        ]
    )
    mock_create_client.assert_not_called()
