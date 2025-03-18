import re
from googleapiclient.discovery import build
import pandas as pd
import datetime as dt
import streamlit as st


def parse_duration(duration):
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


def get_video_length(youtube, video_id):
    request = youtube.videos().list(part="snippet,contentDetails", id=video_id)
    response = request.execute()
    if "items" not in response or len(response["items"]) == 0:
        print(f"Fehler: Kein Video gefunden für ID {video_id}")
        return 0  # Oder eine Default-Wert wie 0 zurückgeben

    duration = response["items"][0]["contentDetails"]["duration"]
    return parse_duration(duration)


def get_video_data(youtube, response: dict) -> list:

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


def get_subscriptions(channel_Id: str, YOUTUBE) -> pd.DataFrame:
    """
    Retrieves all YouTube channel subscriptions for a given channel ID.

    Args:
        channel_Id (str): The YouTube channel ID.
        YOUTUBE (str): Youtube API Client.

    Returns:
        pd.DataFrame: A DataFrame containing subscription details.
    """
    subscriptions = []
    next_page_token = None

    while True:
        request = YOUTUBE.subscriptions().list(
            part="snippet,contentDetails",
            channelId=channel_Id,
            maxResults=50,  # Maximum pro Anfrage
            pageToken=next_page_token,
        )
        response = request.execute()

        #
        subscriptions.extend(response["items"])

        # Prüfen, ob es noch mehr Seiten gibt
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
    youtube, channel_ids: list, number_of_videos: int
) -> list:

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
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None
