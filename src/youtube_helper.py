import re
import isodate
from googleapiclient.discovery import build
import pandas as pd
import datetime as dt
import streamlit as st
from typing import List, Dict


def parse_duration(duration: str) -> str:
    """
    Parse a YouTube video duration string into a human-readable format (MM:SS).

    Args:
        duration (str): The ISO 8601 duration string (e.g., "PT5M10S").

    Returns:
        str: The formatted duration in the format "MM:SS".
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
    Get the duration of a YouTube video.

    Args:
        youtube (object): The YouTube API client.
        video_id (str): The YouTube video ID.

    Returns:
        str: The formatted video duration in the format "MM:SS".
    """
    request = youtube.videos().list(part="snippet,contentDetails", id=video_id)
    response = request.execute()
    if "items" not in response or len(response["items"]) == 0:
        print(f"Fehler: Kein Video gefunden für ID {video_id}")
        return "00:00"  # Oder eine Default-Wert wie 00:00 zurückgeben

    duration = response["items"][0]["contentDetails"]["duration"]
    return parse_duration(duration)


def get_video_data(youtube: object, response: Dict) -> List[Dict[str, str]]:
    """
    Extract video data from a YouTube API response.

    Args:
        youtube (object): The YouTube API client.
        response (dict): The response from a YouTube API search query.

    Returns:
        list: A list of dictionaries containing video metadata such as title, tags, video ID, etc.
    """
    videos = []
    for index, item in enumerate(response["items"], start=1):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        channel_name = item["snippet"]["channelTitle"]
        tags = item["snippet"].get("tags", [])
        thumbnail = item["snippet"]["thumbnails"]["medium"]["url"]
        length = get_video_length(youtube, video_id)

        videos.append(
            {
                "place": index,
                "title": title,
                "tags": ", ".join(tags) if tags else "Keine Tags",
                "video_id": video_id,
                "thumbnail": thumbnail,
                "length": length,
                "channel_name": channel_name,
            }
        )

    return videos


def get_category_name(youtube: object, category_id: str) -> str:
    """
    Get the name of a YouTube video category by its ID.

    Args:
        youtube (object): The YouTube API client.
        category_id (str): The category ID.

    Returns:
        str: The category name or "Unbekannte Kategorie" if not found.
    """
    request = youtube.videoCategories().list(part="snippet", regionCode="DE")

    response = request.execute()

    categories = {item["id"]: item["snippet"]["title"] for item in response["items"]}

    return categories.get(category_id, "Unbekannte Kategorie")


def get_subscriptions(channel_Id: str, youtube: object) -> pd.DataFrame:
    """
    Retrieves all YouTube channel subscriptions for a given channel ID.

    Args:
        channel_Id (str): The YouTube channel ID.
        youtube (str): Youtube API Client.

    Returns:
        pd.DataFrame: A DataFrame containing subscription details.
    """
    subscriptions = []
    next_page_token = None

    while True:
        request = youtube.subscriptions().list(
            part="snippet,contentDetails",
            channelId=channel_Id,
            maxResults=50,  # Maximum pro Anfrage
            pageToken=next_page_token,
        )
        response = request.execute()

        subscriptions.extend(response["items"])

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break  # Keine weiteren Seiten → Beende die Schleife

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

    return subs


def get_recent_videos_from_subscriptions(
    youtube: object, channel_ids: List[str], number_of_videos: int
) -> List[Dict[str, str]]:
    """
    Get the most recent videos from a list of subscribed YouTube channels.

    Args:
        youtube (object): The YouTube API client.
        channel_ids (list): A list of YouTube channel IDs.
        number_of_videos (int): The number of recent videos to retrieve.

    Returns:
        list: A list of dictionaries containing video metadata from the subscriptions.
    """
    videos = []
    # API-Anfragen minimieren: 1 Request pro Kanal
    for channel_id in channel_ids:
        request = youtube.search().list(
            part="id,snippet",
            channelId=channel_id,
            maxResults=number_of_videos,  # Maximal 10 neueste Videos abrufen
            order="date",  # Neueste zuerst
            type="video",  # Nur Videos (keine Streams oder Playlists)
        )
        response = request.execute()
        videos.append(get_video_data(youtube, response)[0])

    return videos


def extract_video_id_from_url(url: str) -> str | None:
    """
    Extract the video ID from a YouTube URL.

    Args:
        url (str): The YouTube video URL.

    Returns:
        str or None: The extracted video ID, or None if no ID is found.
    """
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None
