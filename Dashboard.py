import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
import isodate
import os
from dotenv import load_dotenv

# API-Setup
load_dotenv()
API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE = build("youtube", "v3", developerKey=API_KEY)

# 🔹 **Funktion: Videos suchen**
def get_videos(query, max_results=10):
    request = YOUTUBE.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=max_results
    )
    response = request.execute()

    videos = []
    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        thumbnail = item["snippet"]["thumbnails"]["medium"]["url"]
        videos.append({"video_id": video_id, "title": title, "thumbnail": thumbnail})
    
    return videos

# 🔹 **Funktion: Video-Zusammenfassung abrufen**
def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["de", "en"])
        text = " ".join([entry["text"] for entry in transcript])
        return text[:500] + "..." if len(text) > 500 else text
    except:
        return "Keine Zusammenfassung verfügbar."

# 🔹 **Funktion: Video-Länge abrufen**
def get_video_length(video_id):
    request = YOUTUBE.videos().list(
        part="contentDetails",
        id=video_id
    )
    response = request.execute()
    
    if response["items"]:
        duration = response["items"][0]["contentDetails"]["duration"]
        return parse_duration(duration)
    return 0

# 🔹 **Funktion: YouTube-Zeitformat (PT10M30S) in Minuten umwandeln**
def parse_duration(duration):
    parsed_duration = isodate.parse_duration(duration)
    return parsed_duration.total_seconds() / 60  # Minuten zurückgeben

# 🔥 **Streamlit Dashboard Funktion**
os.system('streamlit run Dashboard.py')

st.title("🎬 YouTube Video Empfehlungen")

# 🟠 **Suchfeld für YouTube-Videos**
query = st.text_input("🔎 Wonach suchst du?", "KI Trends 2024")

if st.button("🔍 Suchen"):
    videos = get_videos(query, max_results=10)
    st.session_state["videos"] = videos  # Speichern, damit Filter funktionieren

# **Wenn Videos geladen sind**
if "videos" in st.session_state:
    videos = st.session_state["videos"]

    # 🟠 **Filter nach Videolänge**
    length_filter = st.slider("🎛 Filtern nach Länge (Minuten)", 0, 60, (0, 60))
    
    # Länge für alle Videos abrufen
    for video in videos:
        video["length"] = get_video_length(video["video_id"])
    
    # 🟢 **Videos nach Länge filtern**
    filtered_videos = [v for v in videos if length_filter[0] <= v["length"] <= length_filter[1]]

    # 🟠 **Videos anzeigen**
    for video in filtered_videos:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(video["thumbnail"], use_column_width=True)
        with col2:
            st.subheader(video["title"])
            st.write(f"**Länge:** {video['length']:.1f} Minuten")
            st.write(f"[📺 Video ansehen](https://www.youtube.com/watch?v={video['video_id']})")

            # 🟢 **Zusammenfassung anzeigen**
            with st.expander("📜 Zusammenfassung"):
                st.write(get_transcript(video["video_id"]))

            # 🎬 **YouTube-Video einbetten**
            st.video(f"https://www.youtube.com/watch?v={video['video_id']}")

