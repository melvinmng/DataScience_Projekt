import re
import isodate
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime
import streamlit as st
from typing import List, Dict
import feedparser
import yt_dlp

from concurrent.futures import ThreadPoolExecutor
import multiprocessing
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

def get_video_length_dlp(video_id: str) -> str: #Checked
    """
    Holt die Dauer eines YouTube-Videos ohne API, basierend auf der Video-ID.

    Args:
        video_id (str): Die YouTube-Video-ID.

    Returns:
        str: Die Videodauer im Format "MM:SS".
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {"quiet": True, "skip_download": True, "force_generic_extractor": True, 'no_warnings': True}
    
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
    global result 
    ydl_opts = {'quiet': True, 'noplaylist': True, 'no_warnings': True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            length_str = f"{info.get('duration', 0) // 60:02}:{info.get('duration', 0) % 60:02}"
            upload_date = info.get("upload_date", "")
            formatted_date = datetime.strptime(upload_date, "%Y%m%d") if upload_date else None
            
            video_dict = {
                "video_id": video_id,
                "title": info.get("title", "Unbekannter Titel"),
                "tags": ", ".join(info.get("tags", [])) if info.get("tags") else "Keine Tags",
                "thumbnail": info.get("thumbnail", "Keine Thumbnail-URL"),
                "length": length_str,
                "upload_date": formatted_date,
                "channel_name": info.get("uploader", "Unbekannter Kanal"),
            }
        except Exception:
            print("Fehler beim Abrufen der Video-Metadaten")
              

    return video_dict

 
def get_video_data(youtube: object, response: Dict, mode=None) -> List[Dict[str, str]]:
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
        if mode == "trends":
            video_id = item["id"]
        else:
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

@st.cache_data(ttl=3600) 
def search_videos_dlp(query: str, max_results: int = 100) -> list: #Checked
    """
    Führt eine YouTube-Suche ohne API durch und gibt eine Liste mit Video-Metadaten zurück.
    
    Args:
        query (str): Suchbegriff.
        max_results (int): Anzahl der gewünschten Ergebnisse (max. 1000).

    Returns:
        list: Eine Liste von Dictionaries mit Videodaten.
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
        search_results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

    videos = []
    if "entries" in search_results:
        for index, entry in enumerate(search_results["entries"], start=1):
            upload_date = entry.get("upload_date", "")
            formatted_date = datetime.strptime(upload_date, "%Y%m%d") if upload_date else None
            videos.append({
                "place": index,
                "title": entry.get("title", "Unbekannter Titel"),
                "video_id": entry.get("id"),
                "thumbnail": entry.get("thumbnail"),
                "channel_name": entry.get("uploader", "Unbekannter Kanal"),
                "length": f"{int(entry.get('duration', 0)) // 60:02}:{int(entry.get('duration', 0)) % 60:02}",
                "tags": ", ".join(entry.get("tags", [])) if entry.get("tags") else "Keine Tags",
                "upload_date": formatted_date,
            })

    return sorted(videos, key=lambda v: v["upload_date"] or datetime.min, reverse=True)

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



@st.cache_data(ttl=3600) 
def get_recent_videos_from_channels_RSS(channel_ids, max_videos=1):
    videos = []

    num_channels = len(channel_ids)
    num_threads = min(num_channels, multiprocessing.cpu_count() * 2) 
    print(f"Num_threads: {num_threads}") # Maximal doppelte CPU-Kerne

    def fetch_videos(channel_id):
        """Holt die neuesten Videos für einen einzelnen Kanal"""
        try:
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            feed = feedparser.parse(feed_url)
            video_urls = [entry.link for entry in feed.entries[:max_videos]]
            
            video_ids = []
            for video in video_urls:
                match = re.search(r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', video)
                if match:
                    video_ids.append(match.group(1))

            return List(set(video_ids))
        except Exception as e:
            st.warning(f"Fehler beim Abrufen der Videos für Kanal {channel_id}: {e}")
            return []

    # 1️⃣ Parallel Videos von allen Kanälen abrufen
    video_id_lists = []
    with ThreadPoolExecutor(max_workers= num_threads) as executor:
        future_to_channel = {executor.submit(fetch_videos, channel): channel for channel in channel_ids}
        for future in future_to_channel:
            video_id_lists.append(future.result()) 

    # Flach in eine Liste konvertieren
    video_ids = [video_id for sublist in video_id_lists for video_id in sublist]

    # 2️⃣ Parallel Video-Metadaten abrufen
    video_data_list = []
    with ThreadPoolExecutor(max_workers= num_threads) as executor:
        future_to_video = {executor.submit(get_video_data_dlp, video_id): video_id for video_id in video_ids}
        for future in future_to_video:
            video_data_list.append(future.result())
  
            

    # Sortieren nach Upload-Datum
    videos = sorted(video_data_list, key=lambda v: v.get("upload_date", datetime.min), reverse=True)


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


def create_youtube_client(api_key: str) -> object:
    api_service_name = "youtube"
    api_version = "v3"
    return build(api_service_name, api_version, developerKey=api_key)



def get_trending_videos(youtube: object, region_code) -> pd.DataFrame:
    """
    Retrieves trending videos from YouTube and formats them into a DataFrame.

    Args:
        youtube (object): The authenticated YouTube API client.

    Returns:
        pd.DataFrame: A DataFrame containing trending video data.
    """
    request = youtube.videos().list(
        part="snippet,contentDetails",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=50,
    )

    response = request.execute()

    return get_video_data(youtube, response,'trends')


import concurrent.futures

def get_trending_videos_dlp(region_code="DE", max_results=50):
    url = f"https://www.youtube.com/feed/trending?gl={region_code}"

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)

    trending_video_ids = [
        entry.get('id') for entry in info_dict.get('entries', []) if entry.get('id')
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
def get_trending_videos_dlp(region_code="DE", max_results=50):
    url = f"https://www.youtube.com/feed/trending?gl={region_code}"

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)

    trending_video_ids = [
        entry.get('id') for entry in info_dict.get('entries', []) if entry.get('id')
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


'''
youtube = create_youtube_client("AIzaSyB7DvFs_Yqq9GpFM2hUyEvWfgYv7jJ20xs")

request = youtube.search().list(
        part="snippet", q='Python', type="video", maxResults=10
    )
    ###youtube REQUEST###
search_response = request.execute()
'''

#print(get_video_length_dlp("D9YV-ykMfEA"))
#print(get_video_length(youtube, "D9YV-ykMfEA"))
"""
print(search_videos_dlp("Python", 10))
print('\n-------------------------------------------------------\n')
print(get_video_data(youtube, search_response))
print('\n-------------------------------------------------------\n')
print(get_video_data_dlp(["D9YV-ykMfEA", "D9YV-ykMfEA"]))
"""
#print(get_recent_videos_from_channels_RSS(["UC8butISFwT-Wl7EV0hUK0BQ","UC1uEIIdQo0F6wLV-XSMCSvQ"], 1)