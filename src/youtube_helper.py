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
        mode (str, optional): Mode to determine parsing behavior (e.g., "trends").

    Returns:
        list: A list of dictionaries containing video metadata such as title, tags, video ID, etc.
    """
    videos = []
    
    for index, item in enumerate(response.get("items", []), start=1):
        try:
            # Primäre Methode zur Extraktion
            if item["id"]["kind"] != "youtube#video":
                continue  # Überspringe Nicht-Video-Ergebnisse

            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel_name = item["snippet"]["channelTitle"]
            tags = item["snippet"].get("tags", [])
            thumbnail = item["snippet"]["thumbnails"]["medium"]["url"]
            length = get_video_length(youtube, video_id)
        
        except KeyError:
            # Alternative Methode zur Verarbeitung
            print(f"Warnung: Unerwartete API-Struktur für Item {index}, alternative Verarbeitung wird versucht.")
            try:
                video_id = item.get("id", {}).get("videoId", "Unknown")
                title = item.get("snippet", {}).get("title", "Unknown Title")
                channel_name = item.get("snippet", {}).get("channelTitle", "Unknown Channel")
                tags = item.get("snippet", {}).get("tags", [])
                thumbnail = item.get("snippet", {}).get("thumbnails", {}).get("medium", {}).get("url", "")
                length = "Unknown"
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


def get_subscriptions(channel_Id: str, youtube: object, csv_filename="subscriptions.csv", gitignore_path=".gitignore") -> pd.DataFrame:
    """
    Holt YouTube-Abonnements für eine gegebene Kanal-ID.
    Falls die CSV-Datei existiert, werden die Daten aus der Datei gelesen.
    Falls nicht, werden die Daten von der API abgerufen und gespeichert.

    Args:
        channel_Id (str): Die YouTube-Kanal-ID.
        youtube (object): YouTube API Client.
        csv_filename (str): Name der CSV-Datei zum Speichern.
        gitignore_path (str): Pfad zur .gitignore-Datei.

    Returns:
        pd.DataFrame: Ein DataFrame mit den Abonnementdetails.
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
    num_threads = min(len(channel_ids), multiprocessing.cpu_count() * 2) 

    ctx = get_script_run_ctx()  # 🔥 Streamlit-Thread-Kontext sichern

    def fetch_videos(channel_id):
        """Holt die neuesten Videos für einen Kanal."""
        try:
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            feed = feedparser.parse(feed_url)
            video_urls = [entry.link for entry in feed.entries[:max_videos]]

            video_ids = []
            for video in video_urls:
                match = re.search(r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', video)
                if match:
                    video_ids.append(match.group(1))

            return list(set(video_ids))

        except Exception as e:
            if ctx:  # 🔥 Hier den richtigen Streamlit-Kontext setzen!
                with ctx:
                    st.warning(f"Fehler beim Abrufen der Videos für Kanal {channel_id}: {e}")
            return []

    video_id_lists = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_channel = {executor.submit(fetch_videos, channel): channel for channel in channel_ids}
        for future in future_to_channel:
            video_id_lists.append(future.result()) 

    video_ids = [video_id for sublist in video_id_lists for video_id in sublist]

    def fetch_video_data(video_id):
        """Holt die Metadaten eines Videos."""
        try:
            return get_video_data_dlp(video_id)
        except Exception as e:
            if ctx:  
                with ctx:
                    st.warning(f"Fehler beim Abrufen der Metadaten für Video {video_id}: {e}")
            return {}

    video_data_list = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_video = {executor.submit(fetch_video_data, video_id): video_id for video_id in video_ids}
        for future in future_to_video:
            video_data_list.append(future.result())

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