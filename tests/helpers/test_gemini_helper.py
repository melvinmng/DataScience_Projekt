import pytest
import pandas as pd
import importlib
from unittest.mock import patch, MagicMock, call


@patch("google.genai.Client")
def test_module_initialization(mock_genai_client, monkeypatch):
    """Tests if the Gemini client is initialized on module import."""

    mock_get_key_func = MagicMock(return_value="fake_gemini_key")
    monkeypatch.setattr(
        "src.env_management.api_key_management.get_api_key", mock_get_key_func
    )

    try:
        import src.helpers.gemini_helper

        importlib.reload(src.helpers.gemini_helper)

        mock_get_key_func.assert_called_with("TOKEN_GOOGLEAPI")
        mock_genai_client.assert_called_with(api_key="fake_gemini_key")
    except Exception as e:
        pytest.fail(f"Module import failed: {e}")


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_get_short_summary_for_watch_list_no_response(
    mock_client_instance, mock_get_api_key
):
    """Tests handling of no text in API response."""
    mock_response = MagicMock()
    mock_response.text = None
    mock_client_instance.models.generate_content.return_value = mock_response

    from src.helpers.gemini_helper import get_short_summary_for_watch_list

    summary = get_short_summary_for_watch_list("Transcript", "Title", "Channel")
    assert summary is None


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_get_short_summary_for_watch_list_api_error(
    mock_client_instance, mock_get_api_key
):
    """Tests handling of API call exception."""
    mock_client_instance.models.generate_content.side_effect = Exception("API Error")

    from src.helpers.gemini_helper import get_short_summary_for_watch_list

    summary = get_short_summary_for_watch_list(
        "Original Transcript", "Title", "Channel"
    )
    assert summary == "Original Transcript"


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_get_channel_recommendations_error(mock_client_instance, mock_get_api_key):
    """Tests getting channel recommendations failure."""
    mock_response = MagicMock()
    mock_response.text = None
    mock_client_instance.models.generate_content.return_value = mock_response

    from src.helpers.gemini_helper import get_channel_recommendations

    recommendations = get_channel_recommendations("hist", "chans", 2, "int")
    assert recommendations == "Fehler"

    mock_client_instance.models.generate_content.side_effect = Exception("API Error")
    recommendations = get_channel_recommendations("hist", "chans", 2, "int")
    assert recommendations == "Fehler"


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_get_summary_api_error(mock_client_instance, mock_get_api_key):
    """Tests handling of API call exception."""
    mock_client_instance.models.generate_content.side_effect = Exception("API Error")

    from src.helpers.gemini_helper import get_summary

    summary = get_summary(True, "transcript", "title")

    assert "Fehler beim Erzeugen der Zusammenfassung: API Error" in summary


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_get_summary_without_spoiler_api_error(mock_client_instance, mock_get_api_key):
    """Tests handling of API call exception."""
    mock_client_instance.models.generate_content.side_effect = Exception("API Error")

    from src.helpers.gemini_helper import get_summary_without_spoiler

    summary = get_summary_without_spoiler("transcript", "title")

    assert "Fehler beim Erzeugen der Zusammenfassung: API Error" in summary


@patch("src.helpers.gemini_helper.get_transcript", return_value="Mocked Transcript")
def test_get_transcript_safe_success(mock_get_transcript):
    """Tests the safe transcript getter on success."""
    from src.helpers.gemini_helper import get_transcript_safe

    transcript = get_transcript_safe("vid1")
    assert transcript == "Mocked Transcript"
    mock_get_transcript.assert_called_once_with("vid1")


@patch(
    "src.helpers.gemini_helper.get_transcript",
    side_effect=Exception("Transcript Error"),
)
def test_get_transcript_safe_failure(mock_get_transcript):
    """Tests the safe transcript getter on failure."""
    from src.helpers.gemini_helper import get_transcript_safe

    transcript = get_transcript_safe("vid1")
    assert "Fehler beim Abrufen des Transkripts: Transcript Error" in transcript
    mock_get_transcript.assert_called_once_with("vid1")


@patch("src.helpers.gemini_helper.get_transcript_safe")
@patch("concurrent.futures.ThreadPoolExecutor")
def test_combine_video_id_title_and_transcript(
    mock_executor_cls, mock_get_transcript_safe
):
    """Tests combining video info, mocking concurrency."""

    mock_executor_instance = MagicMock()
    mock_executor_cls.return_value.__enter__.return_value = mock_executor_instance

    transcript_map = {
        "id1": "Transcript 1",
        "id2": "Transcript 2",
        "id3": "",
        "id4": "Transcript 4",
    }
    mock_get_transcript_safe.side_effect = lambda vid: transcript_map.get(vid, "Error")

    mock_futures = []
    for vid in ["id1", "id2", "id3", "id4"]:
        future = MagicMock()
        future.result.return_value = transcript_map.get(vid, "Error")
        mock_futures.append((future, vid))

    submitted_futures = {}

    def mock_submit(func, arg):
        for f, video_id in mock_futures:
            if video_id == arg:
                submitted_futures[f] = video_id  # Store future -> video_id map
                return f
        raise ValueError(f"No mock future prepared for {arg}")

    mock_executor_instance.submit.side_effect = mock_submit

    with patch(
        "concurrent.futures.as_completed", return_value=[f for f, vid in mock_futures]
    ):
        from src.helpers.gemini_helper import combine_video_id_title_and_transcript

        videos = [
            {"video_id": "id1", "title": "Title 1"},
            {"video_id": "id2", "title": "Title 2"},
            {"video_id": "id3", "title": "Title 3"},
            {"video_id": "id4", "title": "Title 4"},
            {"title": "Title 5"},
        ]

        result = combine_video_id_title_and_transcript(videos)

    assert mock_executor_instance.submit.call_count == 4

    expected_submit_calls = [
        call(mock_get_transcript_safe, "id1"),
        call(mock_get_transcript_safe, "id2"),
        call(mock_get_transcript_safe, "id3"),
        call(mock_get_transcript_safe, "id4"),
    ]
    mock_executor_instance.submit.assert_has_calls(
        expected_submit_calls, any_order=True
    )

    assert len(result) == 3  # id1, id2, id4 (id3 had empty transcript)
    assert "Titel: Title 1\nTranskript: Transcript 1\nVideo-ID: id1\n" in result
    assert "Titel: Title 2\nTranskript: Transcript 2\nVideo-ID: id2\n" in result
    assert "Titel: Title 4\nTranskript: Transcript 4\nVideo-ID: id4\n" in result
    assert "Title 3" not in str(result)


def test_extract_video_id_and_reason_success():
    """Tests successful extraction of video ID and reason."""
    from src.helpers.gemini_helper import extract_video_id_and_reason

    json_str = """
    Some text before...
    'video_id': "xyz789" ,
    'explanation': "Reason: it is relevant."
    Some text after.
    """
    expected = {"video_id": "xyz789", "Begründung": "Reason: it is relevant."}
    assert extract_video_id_and_reason(json_str) == expected


def test_extract_video_id_and_reason_success_different_format():
    """Tests successful extraction with slightly different formatting."""
    from src.helpers.gemini_helper import extract_video_id_and_reason

    json_str = '{"video_id": "abc", "explanation": "Reason"}'
    expected = {
        "video_id": "abc",
        "Begründung": "Reason",
    }
    assert extract_video_id_and_reason(json_str) == expected


def test_extract_video_id_and_reason_missing_field():
    """Tests extraction when a field is missing."""
    from src.helpers.gemini_helper import extract_video_id_and_reason

    json_str_missing_exp = '"video_id": "xyz789"'
    json_str_missing_id = '"explanation": "Reason."'
    json_str_empty = ""
    mock_on_fail = MagicMock()

    assert (
        extract_video_id_and_reason(json_str_missing_exp, on_fail=mock_on_fail) is None
    )
    mock_on_fail.assert_called_once()
    mock_on_fail.reset_mock()
    assert (
        extract_video_id_and_reason(json_str_missing_id, on_fail=mock_on_fail) is None
    )
    mock_on_fail.assert_called_once()
    mock_on_fail.reset_mock()
    assert extract_video_id_and_reason(json_str_empty, on_fail=mock_on_fail) is None
    mock_on_fail.assert_called_once()


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_check_for_clickbait_with_transcript(mock_client_instance, mock_get_api_key):
    """Tests clickbait check when transcript is available."""
    mock_response = MagicMock()
    mock_response.text = "Analysis result: Potential clickbait found."
    mock_client_instance.models.generate_content.return_value = mock_response

    from src.helpers.gemini_helper import check_for_clickbait

    result = check_for_clickbait("This is the transcript.", "Amazing Title!!!")

    assert result == "Analysis result: Potential clickbait found."
    args, kwargs = mock_client_instance.models.generate_content.call_args
    assert "This is the transcript." in kwargs["contents"]
    assert "Amazing Title!!!" in kwargs["contents"]
    assert "Clickbait-Elemente" in kwargs["contents"]


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_check_for_clickbait_no_transcript(mock_client_instance, mock_get_api_key):
    """Tests clickbait check when transcript is empty."""

    from src.helpers.gemini_helper import check_for_clickbait

    result_none = check_for_clickbait(None, "Title")
    result_empty = check_for_clickbait("", "Title")

    assert result_none == "no transcript"
    assert result_empty == "no transcript"
    mock_client_instance.models.generate_content.assert_not_called()


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_check_for_clickbait_no_response(mock_client_instance, mock_get_api_key):
    """Tests clickbait check when API returns no text."""
    mock_response = MagicMock()
    mock_response.text = None
    mock_client_instance.models.generate_content.return_value = mock_response

    from src.helpers.gemini_helper import check_for_clickbait

    result = check_for_clickbait("Transcript", "Title")
    assert result == "no response"


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_check_for_clickbait_api_error(mock_client_instance, mock_get_api_key):
    """Tests handling of API call exception."""
    mock_client_instance.models.generate_content.side_effect = Exception("API Error")

    from src.helpers.gemini_helper import check_for_clickbait

    summary = check_for_clickbait("transcript", "title")

    assert "Fehler beim Erzeugen der Clickbait-Einordnung: API Error" in summary


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_get_subscriptions_based_on_interests(mock_client_instance, mock_get_api_key):
    """Tests filtering subscriptions based on interests."""
    mock_response = MagicMock()
    mock_response.text = "TechChannel,GamingChannel"
    mock_client_instance.models.generate_content.return_value = mock_response

    from src.helpers.gemini_helper import get_subscriptions_based_on_interests

    subs_str = "TechChannel:Tech news,GamingChannel:Let's plays,CookingChannel:Recipes"
    interests = "Technology, Gaming"
    num_channels = 2

    result = get_subscriptions_based_on_interests(subs_str, interests, num_channels)

    assert result == "TechChannel,GamingChannel"
    args, kwargs = mock_client_instance.models.generate_content.call_args
    assert subs_str in kwargs["contents"]
    assert interests in kwargs["contents"]
    assert f"{num_channels} Youtube Kanäle filtern" in kwargs["contents"]


@patch("src.helpers.gemini_helper.get_api_key", return_value="fake_gemini_key")
@patch("src.helpers.gemini_helper.ai_client")
def test_get_subscriptions_based_on_interests_api_error(
    mock_client_instance, mock_get_api_key
):
    """Tests handling of API call exception."""
    mock_client_instance.models.generate_content.side_effect = Exception("API Error")

    from src.helpers.gemini_helper import get_subscriptions_based_on_interests

    filtered_channels = get_subscriptions_based_on_interests(
        "subscriptions", "interests", 4
    )

    assert "Fehler beim Erzeugen der Empfehlung: API Error" in filtered_channels
