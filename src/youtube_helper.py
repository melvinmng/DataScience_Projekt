import re
from googleapiclient.discovery import build, Resource
import pandas as pd
from datetime import datetime
import streamlit as st
import feedparser
import yt_dlp
from streamlit.runtime.scriptrunner import get_script_run_ctx
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import os
from typing import Any
import concurrent.futures
from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id: str, required_languages: list[str] = ["de", "en"]) -> str:
    """Gets the transcript of a YouTube video in the specified languages.

    Uses the youtube_transcript_api library. Returns an empty string if
    no transcript is found for the specified languages or if an error occurs.

    Args:
        video_id (str): The unique identifier of the YouTube video.
        required_languages (list[str], optional): A list of language codes (e.g., 'en', 'de')
                                                  in order of preference.
                                                  Defaults to ["de", "en"].

    Returns:
        str: The video transcript text concatenated into a single string,
             or an empty string if unavailable or on error.
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
    """Parses an ISO 8601 duration string (YouTube format) into MM:SS format.

    Args:
        duration_str (str): The duration string in ISO 8601 format (e.g., "PT5M10S").

    Returns:
        str: The duration formatted as "MM:SS". Returns "00:00" if parsing fails
             or if minutes/seconds are not present.
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


def get_video_length(youtube: Resource, video_id: str) -> str:
    """Retrieves the duration of a YouTube video using the YouTube Data API.

    Args:
        youtube (Resource): An authenticated googleapiclient.discovery.Resource
                            object for the YouTube API.
        video_id (str): The unique identifier of the YouTube video.

    Returns:
        str: The video duration formatted as "MM:SS". Returns "00:00" if the
             video is not found or an API error occurs.
    """
    request = youtube.videos().list(part="snippet,contentDetails", id=video_id)
    response = request.execute()
    if "items" not in response or len(response["items"]) == 0:
        print(f"Fehler: Kein Video gefunden für ID {video_id}")
        return "00:00"  # Oder eine Default-Wert wie 00:00 zurückgeben

    duration = response["items"][0]["contentDetails"]["duration"]
    return parse_duration(duration)


def get_video_length_dlp(video_id: str) -> str:
    """Fetches the duration of a YouTube video using yt-dlp (no API key needed).

    Args:
        video_id (str): The unique identifier of the YouTube video.

    Returns:
        str: The video duration formatted as "MM:SS". Returns "00:00" if fetching
             fails or duration is not found.
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


def get_video_data_dlp(video_id: str) -> dict[str, Any]:
    """Retrieves metadata for a YouTube video using yt-dlp.

    Fetches title, tags, thumbnail, length, upload date, channel name,
    and view count without using the YouTube API.

    Args:
        video_id (str): The unique identifier of the YouTube video.

    Returns:
        dict[str, Any]: A dictionary containing video metadata. Keys include:
                        'video_id' (str), 'title' (str), 'tags' (str),
                        'thumbnail' (str), 'length' (str, "MM:SS"),
                        'upload_date' (Optional[datetime]),
                        'channel_name' (str), 'views' (int).
                        Returns an empty dictionary if an error occurs.
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


def get_video_data(
    youtube: Resource, response: dict[str, Any], mode: str | None = None
) -> list[dict[str, Any]]:
    """Extracts and formats video metadata from a YouTube Data API response.

    Parses items from an API response (e.g., from search or videos list).
    Also fetches view counts and video length using separate API calls.
    Handles different response structures based on the 'mode'.

    Args:
        youtube (Resource): An authenticated YouTube API client resource.
        response (dict[str, Any]): The raw dictionary response from a YouTube API call
                                   (e.g., search.list, videos.list).
        mode (Optional[str], optional): A string indicating the parsing mode,
                                        e.g., "trends". Affects how video IDs
                                        are extracted. Defaults to None.

    Returns:
        list[dict[str, Any]]: A list of dictionaries, each containing metadata
                              for a video. Keys include 'place', 'title', 'tags',
                              'video_id', 'thumbnail', 'length', 'channel_name',
                              'views', 'upload_date'. Returns an empty list if
                              no items are found or errors occur.
    """

    def get_views_with_youtube_api(youtube: Resource, video_id: str) -> str:
        """Retrieves the view count for a video using the YouTube API.

        Args:
            youtube (Resource): The authenticated YouTube API client.
            video_id (str): The ID of the video.

        Returns:
            str: The view count as a string, or "Unknown" if fetching fails.
        """
        try:
            # Anfrage an die YouTube API, um Video-Daten abzurufen
            request = youtube.videos().list(
                part="statistics", id=video_id  # Nur Statistiken (einschließlich Views)
            )
            response = request.execute()

            # Die Anzahl der Aufrufe aus der Antwort extrahieren
            view_count = response["items"][0]["statistics"].get("viewCount", "Unknown")
            return view_count
        except Exception as e:
            print(
                f"Fehler beim Abrufen der Views für Video {video_id} mit der YouTube API: {e}"
            )
            return "Unknown"

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
            views = get_views_with_youtube_api(
                youtube, video_id
            )  # Hole die Views mit yt_dlp
            upload_date = item["snippet"].get(
                "publishedAt", "Unknown"
            )  # Das Upload-Datum wird hier extrahiert

        except KeyError:
            # Alternative Methode zur Verarbeitung
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
                views = get_views_with_youtube_api(youtube, video_id)
                upload_date = item.get("snippet", {}).get("publishedAt", "Unknown")
            except Exception as e:
                print(f"Fehler beim Verarbeiten des Items {index}: {e}")
                continue  # Falls auch die alternative Methode fehlschlägt, überspringe das Item

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
                "upload_date": upload_date,
            }
        )

        # Entfernen der leeren Dictionaries
        videos = [d for d in videos if d]  # Ein leeres Dictionary ist falsy in Python

    # Sortieren nach Upload-Datum (neueste zuerst)
    return sorted(videos, key=lambda v: v["upload_date"] or datetime.min, reverse=True)


@st.cache_data(ttl=3600)
def search_videos_dlp(query: str, max_results: int = 100) -> list[dict[str, Any]]:
    """Performs a Youtube using yt-dlp and returns video metadata.

    Extracts flat list of search results up to max_results.

    Args:
        query (str): The search term.
        max_results (int, optional): The maximum number of search results to retrieve
                                     (limit enforced by yt-dlp, max practical ~1000).
                                     Defaults to 100.

    Returns:
        list[dict[str, Any]]: A list of dictionaries, each containing metadata for a
                              found video. Keys include 'place', 'title', 'video_id',
                              'thumbnail', 'channel_name', 'length', 'tags',
                              'upload_date' (Optional[datetime]), 'views' (int).
                              Returns an empty list on error or if no results.
    """

    max_results = min(max_results, 1000)  # Begrenze auf max. 1000
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
                    "views": view_count,  # ✅ Views integriert!
                }
            )

    # Entfernen der leeren Dictionaries
    videos = [d for d in videos if d]  # Ein leeres Dictionary ist falsy in Python
    return sorted(videos, key=lambda v: v["upload_date"] or datetime.min, reverse=True)


def get_category_name(youtube: Resource, category_id: str) -> str:
    """Gets the display name of a YouTube video category by its ID for a region.

    Currently hardcoded to fetch categories for region "DE" (Germany).

    Args:
        youtube (Resource): The authenticated YouTube API client resource.
        category_id (str): The ID of the category (e.g., "10" for Music).

    Returns:
        str: The title of the category for the specified region ('DE').
             Returns "Unbekannte Kategorie" if the ID is not found or an error occurs.
    """
    request = youtube.videoCategories().list(part="snippet", regionCode="DE")

    response = request.execute()

    categories = {item["id"]: item["snippet"]["title"] for item in response["items"]}

    return categories.get(category_id, "Unbekannte Kategorie")


def get_subscriptions(
    channel_Id: str,
    youtube: Resource,
    csv_filename: str = "subscriptions.csv",
    gitignore_path: str = ".gitignore",
) -> pd.DataFrame:
    """Fetches YouTube subscriptions for a given channel ID using the API.

    Caches results to a CSV file. Reads from CSV if it exists, otherwise
    fetches from API, saves to CSV, and adds CSV filename to .gitignore.

    Args:
        channel_Id (str): The YouTube channel ID for which to fetch subscriptions.
        youtube (Resource): The authenticated YouTube API client resource.
        csv_filename (str, optional): Path to the CSV file used for caching.
                                      Defaults to "subscriptions.csv".
        gitignore_path (str, optional): Path to the .gitignore file.
                                        Defaults to ".gitignore".

    Returns:
        pd.DataFrame: A pandas DataFrame containing subscription details (channel name,
                      ID, description, video counts, etc.). Returns an empty
                      DataFrame if an API error occurs or fetching fails.
    """
    # Falls CSV existiert, lese Daten daraus und returne
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
            return pd.DataFrame()  # Leeres DataFrame zurückgeben

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

    # DataFrame erstellen
    subs = pd.DataFrame(channels)

    # Daten in CSV speichern
    subs.to_csv(csv_filename, index=False, encoding="utf-8")

    # Falls die .gitignore existiert, prüfen ob die CSV bereits eingetragen ist
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as gitignore_file:
            gitignore_content = gitignore_file.readlines()

        if csv_filename not in [line.strip() for line in gitignore_content]:
            with open(gitignore_path, "a", encoding="utf-8") as gitignore_file:
                gitignore_file.write(f"\n{csv_filename}\n")
    else:
        # Falls .gitignore nicht existiert, erstelle sie und füge die Datei hinzu
        with open(gitignore_path, "w", encoding="utf-8") as gitignore_file:
            gitignore_file.write(f"{csv_filename}\n")

    return subs


def get_recent_videos_from_subscriptions(
    youtube: Resource, channel_ids: list[str], number_of_videos: int
) -> list[dict[str, Any]]:
    """Retrieves the most recent videos from a list of YouTube channels using the API.

    Performs one search API call per channel ID to get recent videos.

    Args:
        youtube (Resource): The authenticated YouTube API client resource.
        channel_ids (list[str]): A list of YouTube channel IDs.
        number_of_videos (int): The maximum number of recent videos to retrieve
                                per channel (API max is 50, usually lower is better).

    Returns:
        list[dict[str, Any]]: A list of dictionaries, where each dictionary contains
                              metadata for a recent video from the specified channels.
                              Returns an empty list if errors occur or no videos found.
    """
    videos = []
    # API-Anfragen minimieren: 1 Request pro Kanal
    for channel_id in channel_ids:
        try:
            request = youtube.search().list(
                part="id,snippet",
                channelId=channel_id,
                maxResults=number_of_videos,  # Maximal 10 neueste Videos abrufen
                order="date",  # Neueste zuerst
                type="video",  # Nur Videos (keine Streams oder Playlists)
            )
            response = request.execute()
            print()
            print(channel_id)
            print(f"------------------\n{response}--------------------\n")
            video_data = get_video_data(youtube, response)
            for video in video_data:
                videos.append(video)
        except Exception as e:
            st.warning(f"Fehler beim Abrufen der Videos für Kanal {channel_id}: {e}")

    return videos


@st.cache_data(ttl=3600)
def get_recent_videos_from_channels_RSS(
    channel_ids: list[str], max_videos: int = 1
) -> list[dict[str, Any]]:
    """Retrieves recent videos from YouTube channels using RSS feeds and yt-dlp.

    Fetches video IDs from RSS feeds concurrently and then fetches detailed
    metadata for each video using yt-dlp concurrently.

    Args:
        channel_ids (list[str]): A list of YouTube channel IDs.
        max_videos (int, optional): The maximum number of recent videos to retrieve
                                    per channel's RSS feed. Defaults to 1.

    Returns:
        list[dict[str, Any]]: A list of dictionaries, each containing metadata
                              for a recent video, sorted by upload date (descending).
                              Returns an empty list on errors or if no videos found.
    """
    videos = []
    num_threads = min(len(channel_ids), multiprocessing.cpu_count() * 2)

    ctx = get_script_run_ctx()  # 🔥 Streamlit-Thread-Kontext sichern

    def fetch_videos(channel_id: str) -> list[str]:
        """Fetches the latest video IDs for one channel via its RSS feed."""
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
            # Einfach ohne 'with ctx:' arbeiten
            st.warning(f"Fehler beim Abrufen der Videos für Kanal {channel_id}: {e}")
            return []

    video_id_lists = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_channel = {
            executor.submit(fetch_videos, channel): channel for channel in channel_ids
        }
        for future in future_to_channel:
            video_id_lists.append(future.result())

    video_ids = [video_id for sublist in video_id_lists for video_id in sublist]

    def fetch_video_data(video_id: str) -> dict[str, Any]:
        """Fetches metadata for a single video ID using yt-dlp."""
        try:
            return get_video_data_dlp(video_id)
        except Exception as e:
            st.warning(f"Fehler beim Abrufen der Metadaten für Video {video_id}: {e}")
            return {}

    video_data_list: list = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_video = {
            executor.submit(fetch_video_data, video_id): video_id
            for video_id in video_ids
        }
        for future in future_to_video:
            video_data_list.append(future.result())

    # Entfernen der leeren Dictionaries
    video_data_list = [
        d for d in video_data_list if d
    ]  # Ein leeres Dictionary ist falsy in Python
    videos = sorted(
        video_data_list, key=lambda v: v.get("upload_date", datetime.min), reverse=True
    )

    return videos


def extract_video_id_from_url(url: str) -> str | None:
    """Extracts the 11-character video ID from various YouTube URL formats.

    Args:
        url (str): The YouTube video URL (e.g., full URL, share URL).

    Returns:
        Optional[str]: The extracted 11-character video ID if found,
                       otherwise None.
    """
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def create_youtube_client(api_key: str) -> Resource:
    """Builds a Google API client resource for the YouTube Data API v3.

    Args:
        api_key (str): The YouTube Data API v3 developer key.

    Returns:
        Resource: An initialized googleapiclient.discovery.Resource object.
                  Can raise errors from googleapiclient if API key is invalid
                  or other connection issues occur.
    """
    api_service_name = "youtube"
    api_version = "v3"
    return build(api_service_name, api_version, developerKey=api_key)


def get_trending_videos(
    youtube: Resource, region_code: str
) -> list[dict[str, Any]]:  # Corrected return type
    """Retrieves current trending videos for a specific region using the YouTube API.

    Args:
        youtube (Resource): The authenticated YouTube API client resource.
        region_code (str): The ISO 3166-1 alpha-2 country code (e.g., "DE", "US").

    Returns:
        list[dict[str, Any]]: A list of dictionaries containing metadata for trending
                              videos, sorted by upload date (descending). Returns an
                              empty list if errors occur or no videos are found.
                              See get_video_data for dict structure.

    Raises:
        googleapiclient.errors.HttpError: If the API call fails.
        Exception: For other potential errors during processing.
    """
    request = youtube.videos().list(
        part="snippet,contentDetails",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=50,
    )

    response = request.execute()

    return get_video_data(youtube, response, "trends")


def get_trending_videos_dlp(
    region_code: str = "DE", max_results: int = 50
) -> list[dict[str, Any]]:
    """Retrieves current trending videos for a specific region using yt-dlp.

    Fetches trending video IDs and then retrieves metadata for each using yt-dlp.

    Args:
        region_code (str, optional): The ISO 3166-1 alpha-2 country code.
                                     Defaults to "DE".
        max_results (int, optional): The maximum number of trending videos to return.
                                     Defaults to 50.

    Returns:
        list[dict[str, Any]]: A list of dictionaries containing metadata for trending
                              videos. Returns an empty list if errors occur or no
                              videos found. See get_video_data_dlp for dict structure.
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
