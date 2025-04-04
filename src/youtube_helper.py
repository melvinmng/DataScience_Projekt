import re
import isodate
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime
import streamlit as st
from typing import List, Dict
import feedparser
import yt_dlp
from streamlit.runtime.scriptrunner import get_script_run_ctx
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import os
from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id: str, required_languages: list[str] = ["de", "en"]) -> str:
    """
    Gets the transcript of a YouTube video in the specified languages.

    Args:
        video_id (str): YouTube video ID
        required_languages (list): list of Language codes. Defaults to ["en", "de"].

    Returns:
        str: video transcript as a single string
    """
    try:

        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=required_languages
        )
        transcript_text = " ".join([entry["text"] for entry in transcript])
        return transcript_text
    except:
        print(f"Video {video_id} hat kein Transkript und wird ignoriert")
        return ""
    
    
def parse_duration(duration: str) -> str:
    """
    Parse a YouTube video duration string into a human-readable format (MM:SS).

    Args:
        duration (str): ISO 8601 duration string (e.g., "PT5M10S").

    Returns:
        str: formatted duration (MM:SS).
    """
    pattern = re.compile(r"PT(\d+M)?(\d+S)?")
    match = pattern.match(duration)

    minutes = 0
    seconds = 0

    if match:
        if match.group(1):
            minutes = int(match.group(1)[:-1])
        if match.group(2):
            seconds = int(match.group(2)[:-1])

    return f"{minutes:02}:{seconds:02}"


def get_video_length(youtube: object, video_id: str) -> str:
    """
    Gets duration of a YouTube video via YouTube API.

    Args:
        youtube (object): The YouTube API client.
        video_id (str): The YouTube video ID.

    Returns:
        str: video duration
    """
    request = youtube.videos().list(part="snippet,contentDetails", id=video_id)
    response = request.execute()
    if "items" not in response or len(response["items"]) == 0:
        print(f"Fehler: Kein Video gefunden für ID {video_id}")
        return "00:00"

    duration = response["items"][0]["contentDetails"]["duration"]
    return parse_duration(duration)


def get_video_length_dlp(video_id: str) -> str:
    """
    Gets duration of a YouTube video via yt_dlp based on video ID.

    Args:
        video_id (str): YouTube video ID

    Returns:
        str: video duration
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "force_generic_extractor": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            duration = info.get("duration")  # Dauer in Sekunden

            if duration:
                return f"{duration // 60:02}:{duration % 60:02}"
            else:
                return "00:00"  # Falls keine Dauer gefunden wurde
    except Exception as e:
        print(f"Fehler beim Abrufen der Videolänge für {video_id}: {e}")
        return "00:00"


def get_video_data_dlp(video_id) -> list:
    """@Adrian

    Args:
        video_id (str): YouTube video ID

    Returns:
        list: @Adrian
    """
    ydl_opts = {"quiet": True, "noplaylist": True, "no_warnings": True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
            length_str = (
                f"{info.get('duration', 0) // 60:02}:{info.get('duration', 0) % 60:02}"
            )
            upload_date = info.get("upload_date", "")
            formatted_date = (
                datetime.strptime(upload_date, "%Y%m%d") if upload_date else None
            )

            video_dict = {
                "video_id": video_id,
                "title": info.get("title", "Unbekannter Titel"),
                "tags": (
                    ", ".join(info.get("tags", []))
                    if info.get("tags")
                    else "Keine Tags"
                ),
                "thumbnail": info.get("thumbnail", "Keine Thumbnail-URL"),
                "length": length_str,
                "upload_date": formatted_date,
                "channel_name": info.get("uploader", "Unbekannter Kanal"),
                "views": info.get("view_count", 0),
            }
        except Exception:
            print("Fehler beim Abrufen der Video-Metadaten")

    return video_dict


def get_video_data(youtube: object, response: Dict, mode=None) -> List[Dict[str, str]]:
    """
    Extracts video data from a YouTube API response.

    Args:
        youtube (object): YouTube API client
        response (dict): response from YouTube API search query
        mode (str, optional): mode to determine parsing behavior (e.g., "trends")

    Returns:
        list: list of dictionaries containing video metadata such as title, tags, video ID, views, etc.
    """
    videos = []

    for index, item in enumerate(response.get("items", []), start=1):
        try:
            if mode == "trends":
                video_id = item["id"]
            else:
                video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel_name = item["snippet"]["channelTitle"]
            tags = item["snippet"].get("tags", [])
            thumbnail = item["snippet"]["thumbnails"]["medium"]["url"]
            length = get_video_length(youtube, video_id)
            views = (
                item["statistics"]["viewCount"] if "statistics" in item else "Unknown"
            )

        except KeyError:
            print(
                f"Warnung: Unerwartete API-Struktur für Item {index}, alternative Verarbeitung wird versucht."
            )
            try:
                video_id = item.get("id", {}).get("videoId", "Unknown")
                title = item.get("snippet", {}).get("title", "Unknown Title")
                channel_name = item.get("snippet", {}).get(
                    "channelTitle", "Unknown Channel"
                )
                tags = item.get("snippet", {}).get("tags", [])
                thumbnail = (
                    item.get("snippet", {})
                    .get("thumbnails", {})
                    .get("medium", {})
                    .get("url", "")
                )
                length = "Unknown"
                views = item.get("statistics", {}).get("viewCount", "Unknown")
            except Exception as e:
                print(f"Fehler beim Verarbeiten des Items {index}: {e}")
                continue

        videos.append(
            {
                "place": index,
                "title": title,
                "tags": ", ".join(tags) if tags else "Keine Tags",
                "video_id": video_id,
                "thumbnail": thumbnail,
                "length": length,
                "channel_name": channel_name,
                "views": views,
            }
        )

    return videos


@st.cache_data(ttl=3600)
def search_videos_dlp(query: str, max_results: int = 100) -> list:
    """
    Runs a search query via yt_dlp

    Args:
        query (str): search query
        max_results (int): max. number of search results (<= 1000)

    Returns:
        list: list of dictionaries including video meta data including views
    """
    max_results = min(max_results, 1000)
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "default_search": "ytsearch",
        "noplaylist": True,
        "extract_flat": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_results = ydl.extract_info(
            f"ytsearch{max_results}:{query}", download=False
        )

    videos = []
    if "entries" in search_results:
        for index, entry in enumerate(search_results["entries"], start=1):
            upload_date = entry.get("upload_date", "")
            formatted_date = (
                datetime.strptime(upload_date, "%Y%m%d") if upload_date else None
            )
            view_count = entry.get("view_count", 0)  # 👈 Views hinzufügen

            videos.append(
                {
                    "place": index,
                    "title": entry.get("title", "Unbekannter Titel"),
                    "video_id": entry.get("id"),
                    "thumbnail": entry.get("thumbnail"),
                    "channel_name": entry.get("uploader", "Unbekannter Kanal"),
                    "length": f"{int(entry.get('duration', 0)) // 60:02}:{int(entry.get('duration', 0)) % 60:02}",
                    "tags": (
                        ", ".join(entry.get("tags", []))
                        if entry.get("tags")
                        else "Keine Tags"
                    ),
                    "upload_date": formatted_date,
                    "views": view_count,
                }
            )

    return sorted(videos, key=lambda v: v["upload_date"] or datetime.min, reverse=True)


def get_category_name(youtube: object, category_id: str) -> str:
    """
    Gets the name of a YouTube video category by ID.

    Args:
        youtube (object): YouTube API client
        category_id (str): video category ID

    Returns:
        str: category name or "Unbekannte Kategorie" if not found
    """
    request = youtube.videoCategories().list(part="snippet", regionCode="DE")

    response = request.execute()

    categories = {item["id"]: item["snippet"]["title"] for item in response["items"]}

    return categories.get(category_id, "Unbekannte Kategorie")


def get_subscriptions(
    channel_Id: str,
    youtube: object,
    csv_filename="subscriptions.csv",
    gitignore_path=".gitignore",
) -> pd.DataFrame:
    """
    Gets subscriptions for YouTube channel ID via YouTube API or pre-saved csv file.

    Args:
        channel_Id (str): YouTube channel ID
        youtube (object): YouTube API Client
        csv_filename (str): filename of csv file to store subscriptions
        gitignore_path (str): path to .gitignore file

    Returns:
        pd.DataFrame: DataFrame containing details about subscriptions
    """
    if os.path.isfile(csv_filename):
        return pd.read_csv(csv_filename)

    subscriptions = []
    next_page_token = None

    while True:
        try:
            request = youtube.subscriptions().list(
                part="snippet,contentDetails",
                channelId=channel_Id,
                maxResults=50,
                pageToken=next_page_token,
            )
            response = request.execute()
        except Exception as e:
            st.write("API Tokens aufgebraucht oder Fehler aufgetreten:", str(e))
            return pd.DataFrame()

        subscriptions.extend(response.get("items", []))
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    channels = []
    for item in subscriptions:
        snippet = item["snippet"]
        content_details = item["contentDetails"]

        channels.append(
            {
                "channel_name": snippet["title"],
                "channel_id": snippet["resourceId"]["channelId"],
                "published_at": snippet["publishedAt"],
                "description": snippet["description"],
                "subscription_id": item["id"],
                "total_videos": content_details["totalItemCount"],
                "new_videos": content_details["newItemCount"],
                "thumbnail_url": snippet["thumbnails"]["default"]["url"],
            }
        )

    subs = pd.DataFrame(channels)

    subs.to_csv(csv_filename, index=False, encoding="utf-8")

    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as gitignore_file:
            gitignore_content = gitignore_file.readlines()

        if csv_filename not in [line.strip() for line in gitignore_content]:
            with open(gitignore_path, "a", encoding="utf-8") as gitignore_file:
                gitignore_file.write(f"\n{csv_filename}\n")
    else:
        with open(gitignore_path, "w", encoding="utf-8") as gitignore_file:
            gitignore_file.write(f"{csv_filename}\n")

    return subs


def get_recent_videos_from_subscriptions(
    youtube: object, channel_ids: List[str], number_of_videos: int
) -> List[Dict[str, str]]:
    """
    Gets the most recent videos from a list of subscribed YouTube channels.

    Args:
        youtube (object): YouTube API client
        channel_ids (list): list of YouTube channel IDs
        number_of_videos (int): number of recent videos to retrieve

    Returns:
        list: list of dictionaries containing video metadata from the subscriptions
    """
    videos = []
    for channel_id in channel_ids:
        try:
            request = youtube.search().list(
                part="id,snippet",
                channelId=channel_id,
                maxResults=number_of_videos,
                order="date",
                type="video",
            )
            response = request.execute()
            print()
            print(channel_id)
            print(f"------------------\n{response}--------------------\n")
            video_data = get_video_data(youtube, response)
            for video in video_data:
                videos.append(video)
        except Exception as e:
            print(e)

    return videos


@st.cache_data(ttl=3600)
def get_recent_videos_from_channels_RSS(channel_ids: str, max_videos: int = 1):
    """_summary_

    Args:
        channel_ids (str): YouTube channel IDs
        max_videos (int, optional): max. number of videos. Defaults to 1.

    Returns:
        _type_: @Adrian
    """
    videos = []
    num_threads = min(len(channel_ids), multiprocessing.cpu_count() * 2)

    ctx = get_script_run_ctx()  # Streamlit-Thread-Kontext sichern

    def fetch_videos(channel_id: str):
        """Fetches latest videos of a channel.

        Args:
            channel_id (str): YouTube channel ID

        Returns:
            _type_: @Adrian
        """
        try:
            feed_url = (
                f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            )
            feed = feedparser.parse(feed_url)
            video_urls = [entry.link for entry in feed.entries[:max_videos]]

            video_ids = []
            for video in video_urls:
                match = re.search(
                    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",
                    video,
                )
                if match:
                    video_ids.append(match.group(1))

            return list(set(video_ids))

        except Exception as e:
            if ctx:  # Streamlit-Kontext setzen
                with ctx:
                    st.warning(
                        f"Fehler beim Abrufen der Videos für Kanal {channel_id}: {e}"
                    )
            return []

    video_id_lists = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_channel = {
            executor.submit(fetch_videos, channel): channel for channel in channel_ids
        }
        for future in future_to_channel:
            video_id_lists.append(future.result())

    video_ids = [video_id for sublist in video_id_lists for video_id in sublist]

    def fetch_video_data(video_id: str):
        """Fetches meta data of a video.

        Args:
            video_id (str): YouTube channel ID

        Returns:
            _type_: @Adrian
        """
        try:
            return get_video_data_dlp(video_id)
        except Exception as e:
            if ctx:
                with ctx:
                    st.warning(
                        f"Fehler beim Abrufen der Metadaten für Video {video_id}: {e}"
                    )
            return {}

    video_data_list = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_video = {
            executor.submit(fetch_video_data, video_id): video_id
            for video_id in video_ids
        }
        for future in future_to_video:
            video_data_list.append(future.result())

    videos = sorted(
        video_data_list, key=lambda v: v.get("upload_date", datetime.min), reverse=True
    )

    return videos


def extract_video_id_from_url(url: str) -> str | None:
    """
    Extracts YouTube video ID from URL.

    Args:
        url (str): URL of YouTube video

    Returns:
        str | None: extracted video ID or None if ID is not found
    """
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def create_youtube_client(api_key: str) -> object:
    api_service_name = "youtube"
    api_version = "v3"
    return build(api_service_name, api_version, developerKey=api_key)


def get_trending_videos(youtube: object, region_code) -> pd.DataFrame:
    """
    Gets trending videos via YouTube API

    Args:
        youtube (object): YouTube API client

    Returns:
        pd.DataFrame: DataFrame containing trending video data
    """
    request = youtube.videos().list(
        part="snippet,contentDetails",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=50,
    )

    response = request.execute()

    return get_video_data(youtube, response, "trends")


import concurrent.futures


def get_trending_videos_dlp(region_code: str = "DE", max_results: int = 50):
    """
    Gets trending videos via yt_dlp

    Args:
        region_code (str): YouTube region code. Defaults to 'DE'

    Returns:
        _name_ (_type_): @Adrian
    """
    url = f"https://www.youtube.com/feed/trending?gl={region_code}"

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "force_generic_extractor": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)

    trending_video_ids = [
        entry.get("id") for entry in info_dict.get("entries", []) if entry.get("id")
    ][:max_results]

    if not trending_video_ids:
        print("Keine Trend-Videos gefunden.")
        return []

    videos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_video_id = {
            executor.submit(get_video_data_dlp, video_id): video_id
            for video_id in trending_video_ids
        }

        for future in concurrent.futures.as_completed(future_to_video_id):
            try:
                videos.append(future.result())
            except Exception as e:
                print(f"Fehler beim Abrufen von Videodaten: {e}")

    return videos


"""
youtube = create_youtube_client("AIzaSyB7DvFs_Yqq9GpFM2hUyEvWfgYv7jJ20xs")

request = youtube.search().list(
        part="snippet", q='Python', type="video", maxResults=10
    )
    ###youtube REQUEST###
search_response = request.execute()
"""

# print(get_video_length_dlp("D9YV-ykMfEA"))
# print(get_video_length(youtube, "D9YV-ykMfEA"))
"""
print(search_videos_dlp("Python", 10))
print('\n-------------------------------------------------------\n')
print(get_video_data(youtube, search_response))
print('\n-------------------------------------------------------\n')
print(get_video_data_dlp(["D9YV-ykMfEA", "D9YV-ykMfEA"]))
"""
# print(get_recent_videos_from_channels_RSS(["UC8butISFwT-Wl7EV0hUK0BQ","UC1uEIIdQo0F6wLV-XSMCSvQ"], 1)
