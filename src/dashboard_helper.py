from contextlib import nullcontext
import re
from typing import NoReturn
import streamlit as st

st.set_page_config(
    page_title="YourTime",
    layout="wide",
    page_icon="⏲️",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "https://github.com/melvinmng/DataScience_Projekt.git",
        "About": """
            Adrian Siebnich, Melvin Manning, Ricky Nguyen  
            WDS24B - Data Science Projekt

            ©2025
        
        """,
    },
)

import googleapiclient
from googleapiclient.discovery import Resource
import os
from pathlib import Path
import csv
from dotenv import load_dotenv, set_key, dotenv_values
import pandas as pd
import csv
from datetime import datetime
import time
import subprocess
import sys
import signal
from typing import Any, Callable, NoReturn

import src.config_env
from src.youtube_helper import (
    get_transcript,
    get_video_data,
    get_video_data_dlp,
    extract_video_id_from_url,
    get_subscriptions,
    get_recent_videos_from_subscriptions,
    search_videos_dlp,
    get_recent_videos_from_channels_RSS,
    get_trending_videos,
    get_trending_videos_dlp,
)
from src.key_management.api_key_management import get_api_key, create_youtube_client
from src.key_management.youtube_channel_id import load_channel_id


def initialize() -> Resource | NoReturn:
    """Initializes the Google API Client for YouTube.

    Checks for required API keys (YouTube and Gemini) in environment variables.
    If keys are missing or empty, it triggers a settings pop-up, stops
    the application execution via st.stop(), and raises a RuntimeError
    (the RuntimeError is primarily to satisfy static type checkers like mypy
    regarding the NoReturn path, as st.stop() halts execution before it).

    Returns:
        Resource: An initialized googleapiclient.discovery.Resource object for YouTube
                  if initialization is successful.

    Raises:
        RuntimeError: This is raised only after st.stop() to satisfy type checkers,
                      the application exits before this is truly raised.
                      Wraps the original exception if one occurred besides missing keys.
        ValueError: If API keys are found to be None or empty after retrieval.
                    This is caught internally and leads to the NoReturn path.
    """
    try:
        YT_API_KEY = get_api_key("YOUTUBE_API_KEY")
        GEMINI_API_KEY = get_api_key("TOKEN_GOOGLEAPI")
        if not YT_API_KEY or not GEMINI_API_KEY:
            raise ValueError("API keys not found. Please check your .env file.")
        youtube: Resource = create_youtube_client(YT_API_KEY)
        return youtube
    except Exception as e:
        build_settings_pop_up()
        st.stop()
        raise RuntimeError("App sollte bis jetzt schon abgebrochen worden sein") from e


####Needs to be executed after initialize()####
try:
    from src.gemini_helper import (
        extract_video_id_and_reason,
        get_summary,
        get_summary_without_spoiler,
        get_recommendation,
        combine_video_id_title_and_transcript,
        check_for_clickbait,
        get_subscriptions_based_on_interests,
        get_short_summary_for_watch_list,
        get_channel_recommondations,
    )
except:
    initialize()
    from src.gemini_helper import (
        extract_video_id_and_reason,
        get_summary,
        get_summary_without_spoiler,
        get_recommendation,
        combine_video_id_title_and_transcript,
        check_for_clickbait,
        get_subscriptions_based_on_interests,
        get_short_summary_for_watch_list,
        get_channel_recommondations,
    )


# Variables & constants
watch_later_history = "watch_later_history.csv"
watch_later_csv = "watch_later.csv"
gitignore = ".gitignore"
Interests_file = "interests.txt"

result = None

FEEDBACK_FILE = "feedback.csv"


# Helpers
def duration_to_seconds(duration_str: str) -> int:
    """Converts a duration string from "MM:SS" format to total seconds.

    Args:
        duration_str (str): The duration string in "MM:SS" format.

    Returns:
        int: The total duration in seconds. Returns 0 if parsing fails.
    """
    try:
        minutes, seconds = map(int, duration_str.split(":"))
        return minutes * 60 + seconds
    except Exception as e:
        st.error(f"Fehler beim Parsen der Dauer: {e}")
    return 0


@st.fragment
def lazy_expander(
    title: str,
    key: str,
    on_expand: Callable,
    expanded: bool = False,
    callback_kwargs: dict[Any, Any] | None = None,
) -> None:
    """Renders a 'lazy' expander that loads its content only upon expansion.

    Uses session state to manage the expanded state.

    Args:
        title (str): The title displayed next to the expander arrow.
        key (str): A unique key used for storing the expanded state in
                   st.session_state.
        on_expand (Callable): A function to call when the expander is opened.
                              It receives the container to populate and any
                              callback_kwargs.
        expanded (bool, optional): The initial state of the expander.
                                   Defaults to False (collapsed).
        callback_kwargs (Optional[Dict[Any, Any]], optional):
                        Extra keyword arguments to pass to the on_expand function.
                        Defaults to None.

    Returns:
        None
    """
    if callback_kwargs is None:
        callback_kwargs = {}

    if key not in st.session_state or st.session_state[key] is None:
        st.session_state[key] = bool(expanded)

    outer_container = st.container(border=True)

    arrows = ["▼", "▲"]
    arrow_keys = ["down", "up"]

    with outer_container:
        col1, col2 = st.columns([0.9, 0.1])
        col1.write(f"**{title}**")

        if col2.button(
            arrows[int(st.session_state[key])],
            key=f"{key}_arrow_{arrow_keys[int(st.session_state[key])]}",
        ):
            if not st.session_state[key]:
                st.session_state[key] = True
                on_expand(outer_container, **callback_kwargs)
            else:
                st.session_state[key] = False


@st.fragment
def lazy_button(
    label: str,
    key: str,
    on_click: Callable,
    callback_kwargs: dict[Any, Any] | None = None,
) -> None:
    """Renders a 'lazy' button that manages its clicked state via session state.

    Executes the on_click function when clicked and shows a success indicator.
    Optionally triggers a rerun for delete actions.

    Args:
        label (str): The text label displayed on the button.
        key (str): A unique key used for storing the button's state in
                   st.session_state.
        on_click (Callable): A function to call when the button is clicked.
                             It receives any callback_kwargs.
        callback_kwargs (Optional[Dict[Any, Any]], optional):
                        Extra keyword arguments to pass to the on_click function.
                        Defaults to None.

    Returns:
        None
    """
    if callback_kwargs is None:
        callback_kwargs = {}

    if key not in st.session_state:
        st.session_state[key] = False

    if st.button(label, key=f"{key}_btn"):
        st.session_state[key] = True
        on_click(**callback_kwargs)

    if st.session_state[key]:
        st.success("✅")
        if label == "🚮delete from list":
            st.rerun()


########################## CSV-Functions ##########################
def write_filename_to_gitignore(gitignore_path: str, filename: str) -> None:
    """Appends a filename to the specified .gitignore file if not already present.

    Creates the .gitignore file if it does not exist.

    Args:
        gitignore_path (str): The path to the .gitignore file.
        filename (str): The filename pattern to add to the .gitignore file.

    Returns:
        None
    """
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r+", encoding="utf-8") as gitignore_file:
            lines = gitignore_file.readlines()
            if filename not in [line.strip() for line in lines]:
                gitignore_file.write(f"\n{filename}\n")
    else:
        with open(gitignore_path, "w", encoding="utf-8") as gitignore_file:
            gitignore_file.write(f"{filename}\n")


def read_csv_to_list(filename: str) -> list[dict[str, str]]:
    """Reads a CSV file into a list of dictionaries, removing duplicate rows.

    Args:
        filename (str): The path to the CSV file to read.

    Returns:
        list: A list where each element is a dictionary representing a unique
              row from the CSV file.
    """
    data = []

    with open(filename, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            data.append(dict(row))

    seen = set()
    unique_data = []

    for row in data:
        row_tuple = tuple(row.items())

        if row_tuple not in seen:
            seen.add(row_tuple)
            unique_data.append(row)

    return unique_data


def update_history_csv(
    source_file: str = watch_later_csv,
    history_file: str = watch_later_history,
    gitignore_path: str = gitignore,
) -> None:
    """Appends new, unique rows from a source CSV file to a history CSV file.

    Creates the history file if it doesn't exist and adds it to .gitignore.
    Handles potential errors during file operations.

    Args:
        source_file (str, optional): Path to the source CSV file.
                                     Defaults to watch_later_csv.
        history_file (str, optional): Path to the history CSV file.
                                      Defaults to watch_later_history.
        gitignore_path (str, optional): Path to the .gitignore file.
                                        Defaults to gitignore.

    Returns:
        None
    """
    if not os.path.exists(source_file) or os.stat(source_file).st_size == 0:
        print("Die Quell-CSV ist leer oder existiert nicht. Keine neuen Einträge.")
        return

    if not os.path.exists(history_file):
        with open(history_file, mode="w", encoding="utf-8") as file:
            pass  # Leere Datei erstellen
        print(f"{history_file} wurde erstellt.")

        write_filename_to_gitignore(gitignore_path, history_file)

    history_data = set()
    if os.stat(history_file).st_size > 0:
        with open(history_file, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            header = next(reader, None)  # Header lesen
            if header:
                for row in reader:
                    history_data.add(tuple(row))

    new_data = []
    with open(source_file, mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        header = next(reader, None)  # Header lesen
        if header:
            for row in reader:
                if tuple(row) not in history_data:
                    new_data.append(row)

    if new_data:
        with open(history_file, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if not history_data and header:
                writer.writerow(header)
            writer.writerows(new_data)
        print(f"{len(new_data)} neue Einträge zur History hinzugefügt.")
    else:
        print("Keine neuen Einträge für die History gefunden.")


def save_video_to_csv(
    video: dict[str, Any],
    filename: str = watch_later_csv,
    gitignore_path: str = gitignore,
) -> None:
    """Saves video metadata to a specified CSV file and updates history.

    Appends the video information as a new row. Creates the CSV file
    with headers if it doesn't exist. Adds the filename to .gitignore.
    Includes fetching and summarizing the transcript.

    Args:
        video (Dict[str, Any]): A dictionary containing video metadata. Must include
                                keys: 'title', 'channel_name', 'video_id',
                                'length', 'views'.
        filename (str, optional): Path to the CSV file for saving.
                                  Defaults to watch_later_csv.
        gitignore_path (str, optional): Path to the .gitignore file.
                                        Defaults to gitignore.

    Returns:
        None

    Raises:
        KeyError: If the 'video' dictionary is missing essential keys.
    """
    file_exists = os.path.isfile(filename)
    with open(filename, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "title",
                "channel_name",
                "video_id",
                "video_url",
                "length",
                "views",
                "summarized_transcript",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            {
                "title": video["title"],
                "channel_name": video["channel_name"],
                "video_id": video["video_id"],
                "video_url": f"https://www.youtube.com/watch?v={video['video_id']}",
                "length": video["length"],
                "views": video["views"],
                "summarized_transcript": get_short_summary_for_watch_list(
                    get_transcript(video["video_id"]),
                    video["title"],
                    video["channel_name"],
                ),
            }
        )

    # .gitignore aktualisieren
    write_filename_to_gitignore(gitignore_path, filename)

    update_history_csv()


def load_interests() -> str:
    """Loads user interests from the predefined interests text file.

    Returns:
        str: The content of the interests file as a string, stripped of
             leading/trailing whitespace. Returns an empty string if the file
             does not exist or an error occurs.
    """
    if os.path.exists(Interests_file):
        with open(Interests_file, "r", encoding="utf-8") as file:
            return file.read().strip()
    return ""


def save_interests(interests: str) -> None:
    """Saves the given interests string to the predefined interests text file.

    Only writes to the file if the new interests string differs from the
    currently saved one. Ensures the interests file is listed in .gitignore.

    Args:
        interests (str): The string containing user interests to save.

    Returns:
        None
    """
    current_interests = load_interests()
    if current_interests != interests:  # Speichern nur, wenn es Änderungen gibt
        with open(Interests_file, "w", encoding="utf-8") as file:
            file.write(interests)

    write_filename_to_gitignore(filename=Interests_file, gitignore_path=gitignore)


def delete_video_by_id(video: dict[str, Any], filename: str = watch_later_csv) -> None:
    """Deletes a video entry from the specified CSV file based on 'video_id'.

    Rewrites the CSV file excluding the row that matches the video_id
    from the input video dictionary.

    Args:
        video (Dict[str, Any]): A dictionary representing the video to delete.
                                Must contain at least the 'video_id' key.
        filename (str, optional): Path to the CSV file from which to delete.
                                  Defaults to watch_later_csv.

    Returns:
        None
    """
    videos = []
    video_id = video["video_id"]
    with open(filename, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            videos.append(row)

    videos_to_keep = [video for video in videos if video["video_id"] != video_id]

    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "title",
            "channel_name",
            "video_id",
            "video_url",
            "length",
            "views",
            "summarized_transcript",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        for video in videos_to_keep:
            writer.writerow(video)

    print(f"Das Video mit der video_id {video_id} wurde erfolgreich gelöscht.")


def build_video_list(incoming_videos: list[dict[str, Any]], key_id: str) -> None:
    """Renders a list of videos using Streamlit components.

    Displays title, channel, link, an expandable summary, video player,
    length, views, and conditional add/delete buttons for each video.

    Args:
        incoming_videos (List[Dict[str, Any]]): A list of dictionaries,
                        where each dictionary represents a video and contains
                        keys like 'title', 'channel_name', 'video_id', 'length', 'views'.
        key_id (str): A unique identifier string to be incorporated into the keys
                      of Streamlit elements created within this function, ensuring
                      uniqueness across different lists.

    Returns:
        None
    """
    saved_video_ids = []
    filename = watch_later_csv
    if os.path.exists(filename):
        with open(filename, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                if "video_id" in row:
                    saved_video_ids.append(row["video_id"])
                else:
                    print(f"Spalte '{'video_id'}' nicht gefunden.")

    for video in incoming_videos:
        st.subheader(video["title"])
        st.write(video["channel_name"])
        st.write(
            f"[📺 Video ansehen](https://www.youtube.com/watch?v={video['video_id']})"
        )

        expander_key = f"summary_{video['video_id']}_{key_id}"
        if expander_key not in st.session_state:
            st.session_state[expander_key] = None

        def load_summary(container: Any, video_id: str, title: str) -> None:
            """Loads and displays the video summary within a given container.

            Handles potential errors during transcript fetching or summary generation.

            Args:
                container (Any): The Streamlit container element to display the summary in.
                video_id (str): The YouTube video ID.
                title (str): The title of the YouTube video.

            Returns:
                None
            """
            try:
                transcript = get_transcript(video_id)
                summary = (
                    get_summary(transcript, title)
                    if transcript
                    else "Keine Zusammenfassung verfügbar."
                )
            except:
                summary = "Fehler beim Laden der Zusammenfassung."

            st.session_state[expander_key] = summary
            with container:
                st.write(summary)

        lazy_expander(
            title="📜 Zusammenfassung",
            key=expander_key,
            on_expand=load_summary,
            callback_kwargs={"video_id": video["video_id"], "title": video["title"]},
        )

        st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
        st.write(f"{video['length']} Min.")
        st.write(f"{video['views']} Views")

        if key_id == "watch_later":
            lazy_button(
                label="🚮delete from list",
                key=f"del_{video['video_id']}",
                on_click=delete_video_by_id,
                callback_kwargs={"video": video},
            )

        else:
            if video["video_id"] not in saved_video_ids:
                lazy_button(
                    label="➕add to watch list",
                    key=f"save_{video['video_id']}",
                    on_click=save_video_to_csv,
                    callback_kwargs={"video": video},
                )


# Build Tabs
def build_trending_videos_tab(search_method: str, youtube: Resource | None) -> None:
    """Builds the Streamlit tab displaying trending YouTube videos.

    Allows selection of region and loads trending videos using either the
    YouTube API or yt-dlp based on the search_method.

    Args:
        search_method (str): The method to use for fetching videos
                             ("YouTube API" or other).
        youtube (Resource | None): The initialized YouTube API client resource,
                                    or None if API method is not used or failed.

    Returns:
        None
    """
    st.header("Trending Videos")
    region_code = st.radio("Region wählen:", ("DE", "US", "GB"))

    if st.button("🔄 Trending Videos laden"):
        with st.spinner("Lade Trending Videos..."):
            if search_method == "YouTube API":
                videos = get_trending_videos(youtube, region_code)
            else:
                videos = get_trending_videos_dlp(region_code)
            print(videos)
        if not videos:
            st.write("Keine Videos gefunden oder ein Fehler ist aufgetreten.")
        else:
            build_video_list(videos, key_id="trending_videos")


def build_trend_recommendations(
    search_method: str,
    youtube: Resource | None,
    user_interests: str,
    retry_count: int = 0,
    show_spinner: bool = True,
    show_loading_time_information: bool = True,
) -> None:
    """Builds the content for recommendations based on trending videos.

    Fetches trending videos, gets recommendations from Gemini based on them
    and user interests, and displays the recommended video. Includes retry logic.

    Args:
        search_method (str): The method for fetching videos ("YouTube API" or other).
        youtube (Resource | None): The initialized YouTube API client resource, or None.
        user_interests (str): A string describing the user's interests.
        retry_count (int, optional): Internal counter for retry attempts. Defaults to 0.
        show_spinner (bool, optional): Whether to show the spinner during loading.
                                       Defaults to True.
        show_loading_time_information (bool, optional): Whether to show the info
                                                        message about loading times.
                                                        Defaults to True.

    Returns:
        None
    """
    loading_time_information = None
    max_retries = 3

    if retry_count >= max_retries:
        st.error(
            "Nach mehreren Versuchen konnte keine Empfehlung generiert werden.\nBitte versuchen Sie es später erneut."
        )
        return

    spinner_context = (
        st.spinner("Lade Empfehlungen...") if show_spinner else nullcontext()
    )
    with spinner_context:
        if show_loading_time_information:
            loading_time_information = st.empty()
            loading_time_information.info(
                "Bitte beachten Sie eine möglicherweise längere Ladezeit aufgrund der hohen Datenmenge und QA-Mechanismen."
            )

        if search_method == "YouTube API":
            videos = get_trending_videos(youtube, region_code="DE")
        else:
            videos = get_trending_videos_dlp(region_code="DE")

        video_ids_titles_and_transcripts = combine_video_id_title_and_transcript(videos)
        recommendations_unfiltered = get_recommendation(
            video_ids_titles_and_transcripts=video_ids_titles_and_transcripts,
            interests=user_interests,
        )

        if recommendations_unfiltered:
            recommendations = extract_video_id_and_reason(
                recommendations_unfiltered,
                on_fail=lambda: build_trend_recommendations(
                    search_method,
                    youtube,
                    user_interests,
                    retry_count=retry_count + 1,
                    show_spinner=False,
                    show_loading_time_information=False,
                ),
            )

        if loading_time_information:
            loading_time_information.empty()

    if recommendations:
        if search_method == "YouTube API":
            if youtube:
                request = youtube.videos().list(
                    part="snippet", id=recommendations["video_id"]
                )
                response = request.execute()
                video_data = get_video_data(youtube, response, "trends")
                build_video_list(video_data, key_id="recommendation")
            else:
                st.error("YouTube API Client nicht verfügbar.")
        else:
            video_dict = get_video_data_dlp(recommendations["video_id"])
            if video_dict:
                video_data = [video_dict]
            else:
                video_data = []
            if video_data:
                build_video_list(video_data, key_id="recommendation")
            else:
                st.warning(
                    f"Konnte Videodaten für {recommendations['video_id']} nicht laden."
                )

        st.write("## Begründung:")
        st.write(recommendations["Begründung"])


def build_gemini_recommondations(
    search_method: str,
    youtube: Resource | None,
    user_interests: str,
    history_path: str,
) -> None:
    """Builds the content for recommendations based on user history and Gemini.

    Fetches user subscriptions and watch history, gets channel recommendations
    from Gemini, fetches recent videos from those channels, and displays them.

    Args:
        search_method (str): The method for fetching videos ("YouTube API" or other).
        youtube (Resource | None): The initialized YouTube API client resource, or None.
        user_interests (str): A string describing the user's interests.
        history_path (str): The file path to the user's watch history CSV.

    Returns:
        None
    """
    recommended_videos = []
    try:
        channelId = load_channel_id()
    except Exception as e:
        st.error(
            f"Kanal-ID nicht gefunden. Bitte überprüfe deine ID.\nFehlermeldung:{e}"
        )
    else:

        if search_method == "YouTube API":
            max_results = st.slider(
                "Videoanzahl pro Kanal", min_value=1, max_value=5, value=2
            )
            max_abos = st.slider("Kanalanzahl", min_value=1, max_value=20, value=10)
        else:
            max_results = st.slider(
                "Videoanzahl pro Kanal(yt_dlp)", min_value=1, max_value=10, value=5
            )
            max_abos = st.slider(
                "Kanalanzahl (yt-dlp)", min_value=1, max_value=30, value=10
            )

        subscriptions = get_subscriptions(channel_Id=channelId, youtube=youtube)
        if os.path.exists(history_path):
            history = read_csv_to_list(history_path)
            if len(history) != 0:
                if st.button("🔄 Gemini Recommendation laden"):
                    recommended_channels = get_channel_recommondations(
                        history, subscriptions, max_abos, user_interests
                    )
                    for channel in recommended_channels:
                        print(channel)
                        print("response:_______________________________")
                        if search_method == "YouTube API":
                            if youtube:
                                try:
                                    request = youtube.search().list(
                                        part="snippet",
                                        q=channel,
                                        type="video",
                                        maxResults=max_results,
                                    )
                                    response = request.execute()
                                    videos = get_video_data(youtube, response)
                                except Exception as e:
                                    st.error(
                                        f"API-Fehler bei Suche nach Kanal '{channel}': {e}"
                                    )
                                    videos = []
                            else:
                                st.error("YouTube API Client nicht verfügbar.")
                                videos = []
                        else:
                            videos = search_videos_dlp(channel, max_results=max_results)

                        for video in videos:
                            recommended_videos.append(video)

                    build_video_list(recommended_videos, "gemini_rec")
            else:
                st.error(
                    "Um Empfehlungen geben zu können brauchst du einen Watchlist Verlauf."
                )
        else:
            st.error(
                "Um Empfehlungen geben zu können brauchst du einen Watchlist Verlauf."
            )


def build_recommendation_tab(
    search_method: str,
    youtube: Resource | None,
    user_interests: str,
    # Parameters below seem intended for build_trend_recommendations, pass them down
    retry_count: int = 0,
    show_spinner: bool = True,
    show_loading_time_information: bool = True,
) -> None:
    """Builds the main Streamlit tab for personalized recommendations.

    Contains sub-tabs for recommendations based on trends and recommendations
    based on Gemini/user history.

    Args:
        search_method (str): The method for fetching videos ("YouTube API" or other).
        youtube (Resource): The initialized YouTube API client resource, or None.
        user_interests (str): A string describing the user's interests.
        retry_count (int, optional): Passed down to sub-functions if they implement
                                     retry logic. Defaults to 0.
        show_spinner (bool, optional): Passed down to sub-functions. Defaults to True.
        show_loading_time_information (bool, optional): Passed down to sub-functions.
                                                        Defaults to True.

    Returns:
        None
    """
    st.header("Personalisierte Empfehlungen")

    tab1, tab2 = st.tabs(["Trends Recommendation", " Gemini Recommendation"])

    with tab1:
        if st.button("🔄 Trend Recommendation laden"):
            build_trend_recommendations(
                search_method,
                youtube,
                user_interests,
                retry_count,
                show_spinner,
                show_loading_time_information,
            )

    with tab2:
        build_gemini_recommondations(
            search_method, youtube, user_interests, "watch_later_history.csv"
        )


def build_clickbait_recognition_tab() -> None:
    """Builds the Streamlit tab for analyzing video clickbait potential.

    Takes a video URL input, fetches transcript and title, calls Gemini
    for analysis, and displays the results.

    Returns:
        None
    """
    st.header("Clickbait Analyse")
    st.write("Teste, ob ein Videotitel als Clickbait einzustufen ist.")

    video_url = st.text_input(
        "🔎 Welches Video möchtest du prüfen? Gib hier die Video-Url ein!",
        "https://www.youtube.com/watch?v=onE9aPkSmlw",
    )
    if st.button("🔄 Clickbait Analyse laden"):
        video_id = extract_video_id_from_url(video_url)

        if video_id:
            video_info = get_video_data_dlp(video_id)
            clickbait_elements = check_for_clickbait(
                get_transcript(video_id), video_info["title"]
            )
            if clickbait_elements == "no transcript":
                st.warning(
                    "Leider konnte für dieses Video keine Transkript erstellt und folglich keine Analyse durchgeführt werden. Bitte versuchen Sie es mit einem anderen Video."
                )
            elif clickbait_elements == "no response":
                st.warning(
                    "Es gab leider ein Problem mit Gemini. Bitte versuchen Sie es später noch einmal."
                )
            else:
                st.video(f"https://www.youtube.com/watch?v={video_id}")
                st.write(clickbait_elements)
        else:
            st.warning(
                "Kein Video mit dieser Video-ID gefunden, bitte versuchen Sie es noch einmal"
            )


def save_feedback(feedback_text: str) -> None:
    """Saves user feedback along with timestamp to the feedback CSV file.

    Appends a new row with date, time, and feedback text. Creates the
    file with headers if it doesn't exist. Sets session state flags
    after saving and triggers a rerun.

    Args:
        feedback_text (str): The feedback message provided by the user.

    Returns:
        None
    """
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")
    feedback_data = [date, time, feedback_text]

    file_exists = os.path.exists(FEEDBACK_FILE)

    with open(FEEDBACK_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Datum", "Uhrzeit", "Feedback"])
        writer.writerow(feedback_data)

    st.session_state["feedback_submitted"] = True
    st.session_state["feedback_text"] = ""
    st.rerun()


def build_feedback_tab() -> None:
    """Builds the Streamlit tab for collecting user feedback.

    Provides a text area for input and a button to submit. Shows a success
    message upon submission using session state.

    Returns:
        None
    """
    st.header("Feedback & Wünsche")
    st.write("Hilf uns, das Dashboard zu verbessern!")

    if "feedback_text" not in st.session_state:
        st.session_state["feedback_text"] = ""

    if "feedback_submitted" not in st.session_state:
        st.session_state["feedback_submitted"] = False

    feedback = st.text_area("Dein Feedback oder Verbesserungsvorschläge:")

    if st.session_state["feedback_submitted"]:
        st.session_state["feedback_submitted"] = False
        st.success("Vielen Dank für dein Feedback!")

    if st.button("Feedback absenden"):
        if feedback.strip():
            save_feedback(feedback)
        else:
            st.warning("Bitte gib ein Feedback ein, bevor du es absendest.")


def build_search_tab(search_method: str, youtube: Resource | None) -> None:
    """Builds the Streamlit tab for searching YouTube videos.

    Provides a text input for the query and optionally a slider for max results.
    Fetches and displays search results using the specified method. Manages
    results in session state.

    Args:
        search_method (str): The method for searching videos ("YouTube API" or other).
        youtube (Resource | None): The initialized YouTube API client resource, or None.

    Returns:
        None
    """
    st.session_state["active_tab"] = "search"

    if "videos" not in st.session_state or (st.session_state.get("new_search", False)):
        st.session_state["videos"] = []
        st.session_state["new_search"] = False

    st.header("Suche")
    st.write("Hier kannst du nach Videos oder Kategorien suchen.")

    query = st.text_input("🔎 Wonach suchst du?", "KI Trends 2024")

    max_results = 10
    if search_method == "yt-dlp(Experimentell)":
        max_results = st.slider(
            "Anzahl der Videos", min_value=1, max_value=50, value=10
        )

    if st.button("🔍 Suchen"):
        st.session_state["new_search"] = True
        if search_method == "YouTube API":
            if youtube:
                try:
                    request = youtube.search().list(
                        part="snippet", q=query, type="video", maxResults=10
                    )
                    response = request.execute()
                    videos = get_video_data(youtube, response)
                except Exception as e:
                    st.error(f"API-Fehler bei der Suche: {e}")
                    videos = []
            else:
                st.error("YouTube API Client nicht verfügbar.")
                videos = []
        else:
            videos = search_videos_dlp(query, max_results=max_results)

        st.session_state["videos"] = videos
        st.session_state["last_tab"] = "search"

    if st.session_state.get("videos"):
        build_video_list(st.session_state["videos"], key_id="search")


def build_abobox_tab(
    search_method: str, youtube: Resource, user_interests: str
) -> None:
    """Builds the Streamlit tab displaying recent videos from subscribed channels.

    Fetches subscriptions, filters channels based on interests using Gemini,
    retrieves recent videos from those channels using the specified method,
    and displays them.

    Args:
        search_method (str): The method for fetching videos ("YouTube API" or other).
        youtube (Resource): The initialized YouTube API client resource, or None.
        user_interests (str): A string describing the user's interests.

    Returns:
        None
    """
    st.session_state["active_tab"] = "abobox"

    if "videos" in st.session_state and st.session_state.get("last_tab") != "abobox":
        st.session_state["videos"] = []

    st.header("Abobox")
    st.write("Hier findest du die Videos deiner letzten abonnierten Kanäle")

    if search_method == "YouTube API":
        max_results = st.slider(
            "Anzahl der Videos pro Kanal", min_value=1, max_value=5, value=2
        )
        max_abos = st.slider("Anzahl der Kanäle", min_value=1, max_value=20, value=10)
    else:
        max_results = st.slider(
            "Anzahl der Videos pro Kanal (yt_dlp)", min_value=1, max_value=10, value=5
        )
        max_abos = st.slider(
            "Anzahl der Kanäle (yt_dlp)", min_value=1, max_value=30, value=10
        )

    try:
        channelId = load_channel_id()
    except Exception as e:
        st.error(
            f"Kanal-ID nicht gefunden. Bitte überprüfe deine ID.\nFehlermeldung:{e}"
        )
    else:
        try:
            subscriptions = get_subscriptions(channel_Id=channelId, youtube=youtube)
            if len(subscriptions) == 0:
                st.error("APi key aufgebraucht oder Abos nicht auf öffentlich")

        except:
            st.write("Bitte stelle sicher, dass deine Abos öffentlich einsehbar sind.")
        else:
            if st.button("🔄 Abobox laden"):
                channel_names_and_description = ", ".join(
                    subscriptions[subscriptions["description"].str.strip() != ""].apply(
                        lambda row: f"{row['channel_name']}:{row['description']}",
                        axis=1,
                    )
                )

                channel_string = get_subscriptions_based_on_interests(
                    channel_names_and_description, user_interests, max_abos
                )

                channel_list = []
                if channel_string:
                    channel_list = channel_string.split(",")
                else:
                    st.warning("Keine Kanal-Empfehlungen von Gemini erhalten.")

                matched_ids = []
                for channel in channel_list:
                    normalized_channel = re.sub(r"\W+", "", channel.lower())
                    match = subscriptions[
                        subscriptions["channel_name"]
                        .str.lower()
                        .str.replace(r"\W+", "", regex=True)
                        .str.contains(normalized_channel, na=False)
                    ]
                    if not match.empty:
                        matched_ids.append(match.iloc[0]["channel_id"])

                if search_method == "YouTube API":
                    recent_videos = get_recent_videos_from_subscriptions(
                        youtube, matched_ids, max_results
                    )
                else:
                    recent_videos = get_recent_videos_from_channels_RSS(
                        matched_ids, max_results
                    )

                st.session_state["videos"] = recent_videos
                st.session_state["last_tab"] = "abobox"

            if st.session_state.get("videos"):
                build_video_list(st.session_state["videos"], key_id="abobox")


def build_watch_later_tab() -> None:
    """Builds the Streamlit tab displaying the user's 'Watch Later' list.

    Reads videos from the watch later CSV file and displays them using
    the build_video_list function. Provides a button to reload the list.

    Returns:
        None
    """
    st.session_state["active_tab"] = "view_later"

    if (
        "videos" in st.session_state
        and st.session_state.get("last_tab") != "view_later"
    ):
        st.session_state["videos"] = []

    if st.button("neu laden"):
        st.rerun()

    if os.path.exists(watch_later_csv):
        videos = read_csv_to_list(watch_later_csv)
        if len(videos) != 0:
            st.header("Watch list")
            build_video_list(videos, key_id="watch_later")
        else:
            st.error("Es wurden noch keine Videos zur Watchlist hinzugefügt")
    else:
        st.error("Es wurden noch keine Videos zur Watchlist hinzugefügt")


def build_settings_pop_up() -> None:
    """Builds a pop-up modal (simulated via main page content) for initial API key setup.

    Displayed when API keys are missing upon initialization. Allows user
    to input and save keys to the .env file. Triggers an app restart on save.

    Returns:
        None
    """
    env_path = ".env"
    load_dotenv()

    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write("# API Keys\n")

    current_env = dotenv_values(env_path)
    youtube_api_key = current_env.get("YOUTUBE_API_KEY", "")
    openai_api_key = current_env.get("TOKEN_GOOGLEAPI", "")
    channel_id = current_env.get("CHANNEL_ID", "")

    youtube_key = st.text_input("🎬 YouTube API Key", youtube_api_key, type="password")
    openai_key = st.text_input("🤖 Gemini API Key", openai_api_key, type="password")
    channel_id = st.text_input("ℹ️ Channel ID", channel_id, type="password")

    if st.button("💾 Speichern"):
        if youtube_key:
            set_key(env_path, "YOUTUBE_API_KEY", youtube_key)
        if openai_key:
            set_key(env_path, "TOKEN_GOOGLEAPI", openai_key)
        if channel_id:
            set_key(env_path, "CHANNEL_ID", channel_id)

        updated_env = dotenv_values(env_path)

        if (
            updated_env.get("YOUTUBE_API_KEY") == youtube_key
            and updated_env.get("TOKEN_GOOGLEAPI") == openai_key
            and updated_env.get("CHANNEL_ID") == channel_id
        ):

            st.success("✅ API-Keys wurden gespeichert!")
            st.session_state.show_settings = False
            time.sleep(2)
            subprocess.Popen([sys.executable, "src/restart_app.py"])
            # Beende aktuellen Prozess
            os.kill(os.getpid(), signal.SIGTERM)

        else:
            st.error("⚠️ Fehler beim Speichern! Bitte erneut versuchen.")


def build_settings_tab() -> None:
    """Builds the Streamlit tab for managing API keys and other settings.

    Allows viewing/updating API keys stored in the .env file and provides
    an option to clear the watch list history. Triggers an app restart
    when settings are saved.

    Returns:
        None
    """
    st.header("⚙️ Einstellungen")

    # Lade vorhandene .env-Datei oder erstelle sie
    env_path = ".env"
    load_dotenv()
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write("# API Keys\n")

    # Vorhandene API-Keys abrufen
    youtube_api_key = os.getenv("YOUTUBE_API_KEY", "")
    openai_api_key = os.getenv("TOKEN_GOOGLEAPI", "")
    channel_id = os.getenv("CHANNEL_ID", "")
    # Eingabefelder für API-Keys
    youtube_key = st.text_input("🎬 YouTube API Key", youtube_api_key, type="password")
    gemini_key = st.text_input("🤖 Gemini API Key", openai_api_key, type="password")
    channel_id = st.text_input("ℹ️ Channel ID", channel_id, type="password")

    layout_mode = st.radio("Layout basierend auf", ("Browser", "Streamlit"))
    layout_information = st.empty()
    layout_information.info(
        "Eventuell musst du die Einstellungen von Streamlit anpassen ( ⋮ > Choose app theme, colors and fonts)."
    )

    CSS_FILE_PATH = Path(__file__).parent / "style.css"

    if layout_mode == "Browser":
        with open(CSS_FILE_PATH) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    if st.button("🗑️ Watch List history löschen"):
        history = watch_later_history

        if os.path.exists(history) and os.path.exists(watch_later_csv):
            # CSV einlesen
            df = pd.read_csv(history)
            df1 = pd.read_csv(watch_later_csv)

            # Nur die Header behalten und Datei neu schreiben
            df.iloc[0:0].to_csv(history, index=False)
            df1.iloc[0:0].to_csv(watch_later_csv, index=False)
        else:
            st.error("Es existiert noch keine Historie. Der Vorgang wird abgebrochen.")
    if st.button("💾 Speichern"):
        if youtube_key:
            set_key(env_path, "YOUTUBE_API_KEY", youtube_key)
        if gemini_key:
            set_key(env_path, "TOKEN_GOOGLEAPI", gemini_key)
        if channel_id:
            set_key(env_path, "CHANNEL_ID", channel_id)
        st.session_state["Trending Videos"] = 0

        updated_env = dotenv_values(env_path)

        # Prüfen, ob die Werte gespeichert wurden
        if (
            updated_env.get("YOUTUBE_API_KEY") == youtube_key
            and updated_env.get("TOKEN_GOOGLEAPI") == gemini_key
            and updated_env.get("CHANNEL_ID") == channel_id
        ):

            st.success(
                "✅ Gespeichert. Bitte laden sie das Dashboard neu um die Änderungen zu übernehmen."
            )
            st.write("Starte App neu...")
            time.sleep(2)
            subprocess.Popen([sys.executable, "src/restart_app.py"])
            os.kill(os.getpid(), signal.SIGTERM)
        else:
            st.error("⚠️ Fehler beim Speichern! Bitte erneut versuchen.")
