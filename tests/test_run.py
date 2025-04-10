import pytest
import runpy
import streamlit as st
from unittest.mock import patch, MagicMock


@patch("src.helpers.dashboard_helper.initialize")
@patch("src.helpers.dashboard_helper.load_interests")
@patch("src.helpers.dashboard_helper.save_interests")
@patch("src.helpers.dashboard_helper.build_trending_videos_tab")
@patch("src.helpers.dashboard_helper.build_recommendation_tab")
@patch("src.helpers.dashboard_helper.build_clickbait_recognition_tab")
@patch("src.helpers.dashboard_helper.build_search_tab")
@patch("src.helpers.dashboard_helper.build_subs_tab")
@patch("src.helpers.dashboard_helper.build_watch_later_tab")
@patch("src.helpers.dashboard_helper.build_feedback_tab")
@patch("src.helpers.dashboard_helper.build_settings_tab")
@patch("streamlit.title")
@patch("streamlit.subheader")
@patch("streamlit.sidebar")
@patch("streamlit.tabs")
@patch("streamlit.session_state", MagicMock())
def test_run_script_calls(
    mock_st_tabs,
    mock_st_sidebar,
    mock_st_subheader,
    mock_st_title,
    mock_build_settings,
    mock_build_feedback,
    mock_build_watch_later,
    mock_build_abobox,
    mock_build_search,
    mock_build_clickbait,
    mock_build_recommendation,
    mock_build_trending,
    mock_save_interests,
    mock_load_interests,
    mock_initialize,
):
    """
    Tests if the main functions in run.py are called upon execution.
    This is a basic check, not a functional UI test.
    """

    mock_initialize.return_value = MagicMock()
    mock_load_interests.return_value = "Test Interests"
    mock_st_sidebar.slider.return_value = (0, 60)
    mock_st_sidebar.text_input.return_value = "Test Interests"
    mock_st_sidebar.radio.return_value = "YouTube API"
    mock_st_sidebar.checkbox.return_value = False

    mock_tab_objects = [MagicMock() for _ in range(8)]
    mock_st_tabs.return_value = mock_tab_objects
    for i, tab in enumerate(mock_tab_objects):
        tab.__enter__.return_value = tab  # Simulate entering 'with tab:'

    runpy.run_path("run.py")

    mock_initialize.assert_called_once()
    mock_load_interests.assert_called_once()
    mock_save_interests.assert_called_with("Test Interests")
    mock_st_title.assert_called_with("YouTube FY Dashboard 🎬")
    mock_st_subheader.assert_called_with("Intelligent. Modern. Interaktiv.")
    mock_st_sidebar.slider.assert_called()
    mock_st_sidebar.text_input.assert_called()
    mock_st_sidebar.radio.assert_called()
    mock_st_sidebar.checkbox.assert_called()
    mock_st_tabs.assert_called_once()

    mock_build_trending.assert_called_once_with(
        "YouTube API", mock_initialize.return_value
    )
    mock_build_recommendation.assert_called_once_with(
        "YouTube API", mock_initialize.return_value, "Test Interests"
    )
    mock_build_clickbait.assert_called_once()
    mock_build_search.assert_called_once_with(
        "YouTube API", mock_initialize.return_value
    )
    mock_build_abobox.assert_called_once_with(
        "YouTube API", mock_initialize.return_value, "Test Interests"
    )
    mock_build_watch_later.assert_called_once()
    mock_build_feedback.assert_called_once()
    mock_build_settings.assert_called_once()
