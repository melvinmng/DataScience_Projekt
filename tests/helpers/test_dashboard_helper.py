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
# Beispiel-Videodaten, wie sie von youtube_helper kommen könnten
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


# Add similar tests for load_interests, save_interests, save_feedback, update_history_csv using tmp_path

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
