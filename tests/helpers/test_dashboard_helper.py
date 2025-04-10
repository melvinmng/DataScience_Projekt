import pytest
import os
import csv
import subprocess
import signal
import sys
from unittest.mock import patch, MagicMock, mock_open, call
from pathlib import Path
import pandas as pd
import datetime as dt

# === HILFSFUNKTIONEN / DATEN für Tests ===
MOCK_VIDEO_DATA_LIST = [
    {
        "video_id": "vid1",
        "title": "Test Video 1",
        "channel_name": "Channel A",
        "length": "05:30",
        "views": 100,
        "upload_date": dt.datetime(2024, 1, 1),
        "thumbnail": "url1",
        "tags": "test, api",
    },
    {
        "video_id": "vid2",
        "title": "Test Video 2",
        "channel_name": "Channel B",
        "length": "10:00",
        "views": 5000,
        "upload_date": dt.datetime(2024, 1, 5),
        "thumbnail": "url2",
        "tags": "test, more",
    },
]

MOCK_VIDEO_DICT = MOCK_VIDEO_DATA_LIST[0]  # Für Tests mit einzelnem Video

# === FIXTURES ===


@pytest.fixture(autouse=True)
def mock_streamlit():
    """Automatically mock the streamlit module used within dashboard_helper."""
    with patch("src.helpers.dashboard_helper.st", MagicMock()) as mock_st:
        mock_st.session_state = MagicMock()
        mock_st.write = MagicMock()
        mock_st.video = MagicMock()
        mock_st.button = MagicMock()
        mock_st.expander = MagicMock()
        mock_st.tabs = MagicMock()
        mock_st.spinner = MagicMock()
        mock_st.radio = MagicMock()
        mock_st.rerun = MagicMock()
        yield mock_st


@pytest.fixture
def mock_youtube_client():
    return MagicMock(name="MockYouTubeClient")


# === TESTS ===

# --- Tests für einfache Hilfsfunktionen ---


def test_duration_to_seconds():
    from src.helpers.dashboard_helper import duration_to_seconds

    assert duration_to_seconds("01:30") == 90
    assert duration_to_seconds("00:05") == 5
    assert duration_to_seconds("10:00") == 600
    assert duration_to_seconds("0:0") == 0
    assert duration_to_seconds("00:00") == 0

    assert duration_to_seconds("abc") == 0
    assert duration_to_seconds("1:2:3") == 0
    assert duration_to_seconds("5") == 0
    assert duration_to_seconds(None) == 0
    assert duration_to_seconds("") == 0
    assert duration_to_seconds(1) == 0


# --- Tests für Dateisystem-Interaktionen (mit tmp_path) ---


def test_write_filename_to_gitignore_new_file(tmp_path):
    from src.helpers.dashboard_helper import write_filename_to_gitignore

    gitignore_path = tmp_path / ".gitignore"
    filename = "my_data.csv"

    write_filename_to_gitignore(str(gitignore_path), filename)

    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")
    assert f"\n{filename}\n" in content or content == f"{filename}\n"


def test_write_filename_to_gitignore_existing_file(tmp_path):
    from src.helpers.dashboard_helper import write_filename_to_gitignore

    gitignore_path = tmp_path / ".gitignore"
    initial_content = "node_modules/\n*.log\n"
    gitignore_path.write_text(initial_content, encoding="utf-8")
    filename_new = "my_data.csv"
    filename_existing = "*.log"

    write_filename_to_gitignore(str(gitignore_path), filename_new)
    content = gitignore_path.read_text(encoding="utf-8")
    assert f"\n{filename_new}\n" in content

    write_filename_to_gitignore(str(gitignore_path), filename_existing)
    final_content = gitignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in final_content.strip().split("\n")]
    assert lines.count(filename_existing) == 1


def test_read_csv_to_list(tmp_path):
    from src.helpers.dashboard_helper import read_csv_to_list

    csv_path = tmp_path / "test.csv"
    csv_content = "col1,col2\nvalA,valB\nvalC,valD\nvalA,valB\nvalE,valF\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    data = read_csv_to_list(str(csv_path))

    expected = [
        {"col1": "valA", "col2": "valB"},
        {"col1": "valC", "col2": "valD"},
        {"col1": "valE", "col2": "valF"},
    ]

    assert len(data) == len(expected)
    assert all(item in data for item in expected)
    assert all(item in expected for item in data)


def test_read_csv_to_list_empty_and_header_only(tmp_path):
    from src.helpers.dashboard_helper import read_csv_to_list

    empty_csv = tmp_path / "empty.csv"
    empty_csv.touch()
    header_csv = tmp_path / "header.csv"
    header_csv.write_text("h1,h2\n", encoding="utf-8")

    assert read_csv_to_list(str(empty_csv)) == []
    assert read_csv_to_list(str(header_csv)) == []


@patch(
    "src.helpers.dashboard_helper.get_transcript", return_value="Mock Transcript Text"
)
@patch(
    "src.helpers.dashboard_helper.get_short_summary_for_watch_list",
    return_value="Mock Summary",
)
@patch("src.helpers.dashboard_helper.write_filename_to_gitignore")
@patch("src.helpers.dashboard_helper.update_history_csv")
def test_save_video_to_csv(
    mock_update_hist, mock_write_git, mock_get_summary, mock_get_transcript, tmp_path
):
    from src.helpers.dashboard_helper import (
        save_video_to_csv,
        watch_later_csv,
        gitignore,
    )

    target_csv_path = tmp_path / watch_later_csv
    target_gitignore = tmp_path / gitignore

    save_video_to_csv(MOCK_VIDEO_DICT, str(target_csv_path), str(target_gitignore))

    assert target_csv_path.exists()
    with open(target_csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["title"] == MOCK_VIDEO_DICT["title"]
    assert rows[0]["video_id"] == MOCK_VIDEO_DICT["video_id"]
    assert (
        rows[0]["video_url"]
        == f"https://www.youtube.com/watch?v={MOCK_VIDEO_DICT['video_id']}"
    )
    assert rows[0]["length"] == MOCK_VIDEO_DICT["length"]
    assert rows[0]["views"] == str(MOCK_VIDEO_DICT["views"])
    assert rows[0]["summarized_transcript"] == "Mock Summary"

    mock_get_transcript.assert_called_once_with(MOCK_VIDEO_DICT["video_id"])
    mock_get_summary.assert_called_once_with(
        "Mock Transcript Text",
        MOCK_VIDEO_DICT["title"],
        MOCK_VIDEO_DICT["channel_name"],
    )
    mock_write_git.assert_called_once_with(str(target_gitignore), str(target_csv_path))
    mock_update_hist.assert_called_once()


def test_delete_video_by_id(tmp_path):
    from src.helpers.dashboard_helper import delete_video_by_id, watch_later_csv

    csv_path = tmp_path / watch_later_csv
    fieldnames = [
        "title",
        "channel_name",
        "video_id",
        "video_url",
        "length",
        "views",
        "summarized_transcript",
    ]
    rows_to_write = [
        dict(zip(fieldnames, ["T1", "C1", "id1", "url1", "1:00", "10", "S1"])),
        dict(zip(fieldnames, ["T2", "C2", "id2", "url2", "2:00", "20", "S2"])),
        dict(zip(fieldnames, ["T3", "C3", "id3", "url3", "3:00", "30", "S3"])),
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_to_write)

    video_to_delete = {"video_id": "id2"}
    delete_video_by_id(video_to_delete, str(csv_path))

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        final_rows = list(reader)

    assert len(final_rows) == 2
    assert final_rows[0]["video_id"] == "id1"
    assert final_rows[1]["video_id"] == "id3"
    assert not any(row["video_id"] == "id2" for row in final_rows)


def test_load_interests_file_not_exist(tmp_path):
    """Test load_interests when the file doesn't exist."""
    from src.helpers.dashboard_helper import load_interests

    with patch(
        "src.helpers.dashboard_helper.Interests_file",
        str(tmp_path / "non_existent_interests.txt"),
    ):
        assert load_interests() == ""


def test_load_interests_file_exists(tmp_path):
    """Test load_interests when the file exists with content."""
    from src.helpers.dashboard_helper import load_interests

    interests_file_path = tmp_path / "my_interests.txt"
    test_content = "  AI, Python, Data Visualization \n"
    expected_content = "AI, Python, Data Visualization"
    interests_file_path.write_text(test_content, encoding="utf-8")

    with patch("src.helpers.dashboard_helper.Interests_file", str(interests_file_path)):
        assert load_interests() == expected_content


@patch("src.helpers.dashboard_helper.load_interests")
@patch("src.helpers.dashboard_helper.write_filename_to_gitignore")
def test_save_interests_new_file(mock_write_git, mock_load, tmp_path):
    """Test save_interests creating a new file."""
    from src.helpers.dashboard_helper import save_interests

    interests_file_path = tmp_path / "interests.txt"
    gitignore_path = tmp_path / ".gitignore"
    new_interests = "Gardening, Cooking"

    mock_load.return_value = ""

    with patch(
        "src.helpers.dashboard_helper.Interests_file", str(interests_file_path)
    ), patch("src.helpers.dashboard_helper.gitignore", str(gitignore_path)):

        save_interests(new_interests)

    assert interests_file_path.exists()
    assert interests_file_path.read_text(encoding="utf-8") == new_interests
    mock_load.assert_called_once()
    mock_write_git.assert_called_once_with(
        filename=str(interests_file_path), gitignore_path=str(gitignore_path)
    )


@patch("src.helpers.dashboard_helper.load_interests")
@patch("src.helpers.dashboard_helper.write_filename_to_gitignore")
def test_save_interests_overwrite_file(mock_write_git, mock_load, tmp_path):
    """Test save_interests overwriting existing file with different content."""
    from src.helpers.dashboard_helper import save_interests

    interests_file_path = tmp_path / "interests.txt"
    gitignore_path = tmp_path / ".gitignore"
    initial_interests = "Old Stuff"
    new_interests = "New Stuff"

    interests_file_path.write_text(initial_interests, encoding="utf-8")
    mock_load.return_value = initial_interests

    with patch(
        "src.helpers.dashboard_helper.Interests_file", str(interests_file_path)
    ), patch("src.helpers.dashboard_helper.gitignore", str(gitignore_path)):

        save_interests(new_interests)

    assert interests_file_path.read_text(encoding="utf-8") == new_interests
    mock_load.assert_called_once()
    mock_write_git.assert_called_once_with(
        filename=str(interests_file_path), gitignore_path=str(gitignore_path)
    )


@patch("src.helpers.dashboard_helper.load_interests")  # Mock internal call
@patch("src.helpers.dashboard_helper.write_filename_to_gitignore")  # Mock helper call
def test_save_interests_same_content(mock_write_git, mock_load, tmp_path):
    """Test save_interests when content is the same (should not rewrite)."""
    from src.helpers.dashboard_helper import save_interests

    interests_file_path = tmp_path / "interests.txt"
    gitignore_path = tmp_path / ".gitignore"
    current_interests = "Same Stuff"

    interests_file_path.write_text(current_interests, encoding="utf-8")
    mock_load.return_value = current_interests
    mtime_before = interests_file_path.stat().st_mtime

    with patch(
        "src.helpers.dashboard_helper.Interests_file", str(interests_file_path)
    ), patch("src.helpers.dashboard_helper.gitignore", str(gitignore_path)):

        save_interests(current_interests)

    mtime_after = interests_file_path.stat().st_mtime
    assert mtime_after == mtime_before
    assert interests_file_path.read_text(encoding="utf-8") == current_interests
    mock_load.assert_called_once()
    mock_write_git.assert_called_once_with(
        filename=str(interests_file_path), gitignore_path=str(gitignore_path)
    )


@patch("src.helpers.dashboard_helper.datetime")
def test_save_feedback_new_file(mock_datetime, tmp_path, mock_streamlit):
    """Test save_feedback when the feedback file doesn't exist."""
    from src.helpers.dashboard_helper import save_feedback

    feedback_file_path = tmp_path / "feedback.csv"
    feedback_text = "This is my feedback"
    test_time = dt.datetime(2024, 5, 1, 12, 30, 0)
    mock_datetime.now.return_value = test_time

    with patch("src.helpers.dashboard_helper.FEEDBACK_FILE", str(feedback_file_path)):
        save_feedback(feedback_text)

    assert feedback_file_path.exists()
    with open(feedback_file_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert len(rows) == 2  # Header + 1 data row
    assert rows[0] == ["Datum", "Uhrzeit", "Feedback"]
    assert rows[1] == ["2024-05-01", "12:30:00", feedback_text]

    mock_streamlit.session_state.__setitem__.assert_any_call("feedback_submitted", True)
    mock_streamlit.session_state.__setitem__.assert_any_call("feedback_text", "")
    mock_streamlit.rerun.assert_called_once()


@patch("src.helpers.dashboard_helper.datetime")
def test_save_feedback_append_file(mock_datetime, tmp_path, mock_streamlit):
    """Test save_feedback appending to an existing file."""
    from src.helpers.dashboard_helper import save_feedback

    feedback_file_path = tmp_path / "feedback.csv"
    feedback_text_1 = "Initial feedback"
    feedback_text_2 = "More feedback"

    test_time_1 = dt.datetime(2024, 5, 1, 10, 0, 0)
    with open(feedback_file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Datum", "Uhrzeit", "Feedback"])
        writer.writerow(["2024-05-01", "10:00:00", feedback_text_1])

    test_time_2 = dt.datetime(2024, 5, 2, 11, 15, 0)
    mock_datetime.now.return_value = test_time_2
    mock_streamlit.rerun.reset_mock()

    with patch("src.helpers.dashboard_helper.FEEDBACK_FILE", str(feedback_file_path)):
        save_feedback(feedback_text_2)

    with open(feedback_file_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert len(rows) == 3  # Header + 2 data rows
    assert rows[0] == ["Datum", "Uhrzeit", "Feedback"]
    assert rows[1] == [
        "2024-05-01",
        "10:00:00",
        feedback_text_1,
    ]
    assert rows[2] == ["2024-05-02", "11:15:00", feedback_text_2]

    mock_streamlit.session_state.__setitem__.assert_any_call("feedback_submitted", True)
    mock_streamlit.session_state.__setitem__.assert_any_call("feedback_text", "")
    mock_streamlit.rerun.assert_called_once()


@patch("src.helpers.dashboard_helper.write_filename_to_gitignore")
def test_update_history_csv_new_history(mock_write_git, tmp_path):
    """Test update_history_csv when history file doesn't exist."""
    from src.helpers.dashboard_helper import update_history_csv

    source_path = tmp_path / "source.csv"
    history_path = tmp_path / "history.csv"
    gitignore_path = tmp_path / ".gitignore"

    source_content = "id,data\n1,A\n2,B\n"
    source_path.write_text(source_content, encoding="utf-8")

    assert not history_path.exists()

    update_history_csv(str(source_path), str(history_path), str(gitignore_path))

    assert history_path.exists()
    assert history_path.read_text(encoding="utf-8") == source_content
    mock_write_git.assert_called_once_with(str(gitignore_path), str(history_path))


@patch("src.helpers.dashboard_helper.write_filename_to_gitignore")
def test_update_history_csv_append_unique(mock_write_git, tmp_path):
    """Test update_history_csv appending unique rows to existing history."""
    from src.helpers.dashboard_helper import update_history_csv

    source_path = tmp_path / "source.csv"
    history_path = tmp_path / "history.csv"
    gitignore_path = tmp_path / ".gitignore"

    history_content = "id,data\n1,A\n2,B\n"
    history_path.write_text(history_content, encoding="utf-8")

    source_content = "id,data\n2,B\n3,C\n1,A\n4,D\n"
    source_path.write_text(source_content, encoding="utf-8")

    update_history_csv(str(source_path), str(history_path), str(gitignore_path))

    final_history = history_path.read_text(encoding="utf-8")

    assert "id,data" in final_history
    assert "1,A" in final_history
    assert "2,B" in final_history
    assert "3,C" in final_history
    assert "4,D" in final_history
    assert len(final_history.strip().split("\n")) == 5  # Header + 4 unique data rows
    mock_write_git.assert_not_called()


@patch("src.helpers.dashboard_helper.write_filename_to_gitignore")
def test_update_history_csv_no_new_rows(mock_write_git, tmp_path):
    """Test update_history_csv when source has no new rows."""
    from src.helpers.dashboard_helper import update_history_csv

    source_path = tmp_path / "source.csv"
    history_path = tmp_path / "history.csv"
    gitignore_path = tmp_path / ".gitignore"

    history_content = "id,data\n1,A\n2,B\n"
    history_path.write_text(history_content, encoding="utf-8")
    source_content = "id,data\n2,B\n1,A\n"
    source_path.write_text(source_content, encoding="utf-8")

    update_history_csv(str(source_path), str(history_path), str(gitignore_path))

    assert history_path.read_text(encoding="utf-8") == history_content
    mock_write_git.assert_not_called()


def test_update_history_csv_source_empty_or_missing(tmp_path):
    """Test update_history_csv when source is empty or missing."""
    from src.helpers.dashboard_helper import update_history_csv

    source_path = tmp_path / "source.csv"
    history_path = tmp_path / "history.csv"
    gitignore_path = tmp_path / ".gitignore"

    history_content = "id,data\n1,A\n"
    history_path.write_text(history_content, encoding="utf-8")

    # Case 1: Source is empty
    source_path.write_text("", encoding="utf-8")
    update_history_csv(str(source_path), str(history_path), str(gitignore_path))
    assert history_path.read_text(encoding="utf-8") == history_content

    # Case 2: Source is missing
    os.remove(source_path)
    assert not source_path.exists()
    update_history_csv(str(source_path), str(history_path), str(gitignore_path))
    assert history_path.read_text(encoding="utf-8") == history_content


# --- Tests for Orchestration / Logic Functions ---


@patch("src.helpers.dashboard_helper.get_api_key")
@patch("src.helpers.dashboard_helper.create_youtube_client")
@patch("src.helpers.dashboard_helper.build_settings_pop_up")
@patch("src.helpers.dashboard_helper.st")
def test_initialize_success(
    mock_st_obj, mock_build_popup, mock_create_client, mock_get_key
):
    """Tests successful initialization when API keys are found."""
    from src.helpers.dashboard_helper import initialize

    mock_get_key.side_effect = [
        "fake_youtube_key",
        "fake_gemini_key",
    ]
    mock_yt_client = MagicMock(name="MockYouTubeClientInstance")
    mock_create_client.return_value = mock_yt_client

    result_client = initialize()

    mock_get_key.assert_has_calls([call("YOUTUBE_API_KEY"), call("TOKEN_GOOGLEAPI")])
    mock_create_client.assert_called_once_with("fake_youtube_key")
    mock_build_popup.assert_not_called()
    mock_st_obj.stop.assert_not_called()
    assert result_client is mock_yt_client


@patch("src.helpers.dashboard_helper.get_api_key")
@patch("src.helpers.dashboard_helper.create_youtube_client")
@patch("src.helpers.dashboard_helper.build_settings_pop_up")
@patch("src.helpers.dashboard_helper.st")
def test_initialize_missing_key(
    mock_st_obj, mock_build_popup, mock_create_client, mock_get_key
):
    """Tests initialization failure when an API key is missing."""
    from src.helpers.dashboard_helper import initialize

    mock_get_key.return_value = None

    with pytest.raises(
        RuntimeError, match="App sollte bis jetzt schon abgebrochen worden sein"
    ):
        initialize()

    mock_get_key.assert_has_calls([call("YOUTUBE_API_KEY"), call("TOKEN_GOOGLEAPI")])
    mock_create_client.assert_not_called()
    mock_build_popup.assert_called_once()
    mock_st_obj.stop.assert_called_once()


# --- Example Test for a Tab Builder ---


@patch("src.helpers.dashboard_helper.get_trending_videos")
@patch("src.helpers.dashboard_helper.get_trending_videos_dlp")
@patch("src.helpers.dashboard_helper.build_video_list")
@patch("src.helpers.dashboard_helper.st")
def test_build_trending_videos_tab_api(
    mock_st_obj, mock_build_list, mock_get_dlp, mock_get_api
):
    """Tests build_trending_videos_tab logic when using API method."""
    from src.helpers.dashboard_helper import build_trending_videos_tab

    mock_youtube = MagicMock(name="MockYouTubeForTabTest")

    mock_st_obj.radio.return_value = "DE"
    mock_st_obj.button.return_value = True

    mock_get_api.return_value = MOCK_VIDEO_DATA_LIST

    build_trending_videos_tab(search_method="YouTube API", youtube=mock_youtube)

    mock_st_obj.header.assert_called_with("Trending Videos")
    mock_st_obj.radio.assert_called_with("Region wählen:", ("DE", "US", "GB"))
    mock_st_obj.button.assert_called_with("🔄 Trending Videos laden")
    mock_st_obj.spinner.assert_called_with("Lade Trending Videos...")
    mock_get_api.assert_called_once_with(mock_youtube, "DE")
    mock_get_dlp.assert_not_called()
    mock_build_list.assert_called_once_with(
        MOCK_VIDEO_DATA_LIST, key_id="trending_videos"
    )
