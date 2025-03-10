import pytest
import src.key_management
import src.key_management.gemini_api_key_management
import src.key_management.youtube_api_key_management


def test_get_gemini_api_key():
    try:
        src.key_management.gemini_api_key_management.get_api_key()
    except Exception as e:
        pytest.fail(f"Test ist fehlgeschlagen, weil ein Fehler auftrat: {e}")


def test_load_youtube_api_key():
    try:
        src.key_management.youtube_api_key_management.load_api_key()
    except Exception as e:
        pytest.fail(f"Test ist fehlgeschlagen, weil ein Fehler auftrat: {e}")
