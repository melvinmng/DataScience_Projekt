"""

Das Key management für Gemini und YouTube wurde zusammengefasst.
Die Test müssen geupdatet werden.

import pytest
from src.env_management.gemini_api_key_management import get_api_key
from src.env_management.youtube_api_key_management import load_api_key


def test_get_gemini_api_key():
    try:
        get_api_key()
    except Exception as e:
        pytest.fail(f"Test ist fehlgeschlagen, weil ein Fehler auftrat: {e}")


def test_load_youtube_api_key():
    try:
        load_api_key()
    except Exception as e:
        pytest.fail(f"Test ist fehlgeschlagen, weil ein Fehler auftrat: {e}")
"""
