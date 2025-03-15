import streamlit as st
import pandas as pd
from src.key_management.api_key_management import get_api_key, create_youtube_client
from src.youtube_helper import get_video_data  # Wiederverwendet die Funktion für Videodaten
from src.youtube_trend_analysis import get_trending_videos
from src.llm_analysis import get_recommendation, combine_video_id_title_and_transcript
import src.settings
from typing import Optional
import googleapiclient


# Hilfsfunktion: Konvertiere "MM:SS" in Sekunden
def duration_to_seconds(duration_str: str) -> int:
    try:
        minutes, seconds = map(int, duration_str.split(":"))
        return minutes * 60 + seconds
    except Exception as e:
        st.error(f"Fehler beim Parsen der Dauer: {e}")
    return 0


# Dummy-Implementierung für personalisierte Empfehlungen (Platzhalter)
def get_personalized_recommendations(interests: str) -> pd.DataFrame:
    data = {
        "Titel": ["Empfehlung 1", "Empfehlung 2"],
        "Dauer": ["04:30", "05:15"],
        "Beschreibung": [
            "Ein Video, das zu deinen Interessen passt.",
            "Noch ein Video, das du dir anschauen könntest."
        ],
        "Clickbait": ["Niedrig", "Mittel"]
    }
    return pd.DataFrame(data)


# API-Client-Initialisierung
def initialize() -> Optional[googleapiclient.discovery.Resource]:
    try:
        yt_api_key = get_api_key("YOUTUBE_API_KEY")
        youtube = create_youtube_client(yt_api_key)
    except Exception as e:
        st.error(f"Fehler beim Initialisieren des YouTube-Clients: {e}")
        st.stop()
    
    return youtube


# Dashboard-Titel
st.title("Dein personalisiertes YouTube-FY-Dashboard")

# Sidebar: Grundlegende Einstellungen
st.sidebar.header("Einstellungen")

# Range-Slider für die verfügbare Zeit
length_filter = st.sidebar.slider(
    "Wie viele Minuten hast du heute für YouTube?",
    min_value=0,
    max_value=180,
    value=(0, 60),
    help="Wähle dein verfügbares Zeitbudget in Minuten."
)

user_interests = st.sidebar.text_input("Deine Interessensgebiete (kommagetrennt)", value=src.settings.interests)

# Verwenden von Tabs, um verschiedene Funktionen übersichtlich zu präsentieren
tabs = st.tabs(["Trending Videos", "Empfehlungen", "Clickbait Analyse", "Suche", "Feedback"])

####################################
# Tab 1: Trending Videos
with tabs[0]:
    st.header("Trending Videos")
    youtube = initialize()

    with st.spinner("Lade Trending Videos..."):
        df_videos = get_trending_videos(youtube)

    if df_videos.empty:
        st.write("Keine Videos gefunden oder ein Fehler ist aufgetreten.")
    else:
        st.subheader("Alle Trending Videos")
        for _, video in df_videos.sort_values(by="Platz").iterrows():
            st.markdown(f"### {video['Platz']}. {video['Titel']}")
            st.write(f"**Dauer:** {video['Dauer']}")
            st.write(f"**Kategorie:** {video['Kategorie']}")
            st.write(f"**Tags:** {video['Tags']}")
            st.video(video["Video_URL"])
            st.markdown("---")

        selected_videos = []
        cumulative_time = 0

        df_videos = df_videos.sort_values(by="Platz")
        for _, row in df_videos.iterrows():
            video_duration_seconds = duration_to_seconds(row["Dauer"])
            if cumulative_time + video_duration_seconds <= length_filter[1] * 60:
                selected_videos.append(row)
                cumulative_time += video_duration_seconds

        if selected_videos:
            st.header("Empfohlene Videos für dein Zeitbudget")
            for video in selected_videos:
                st.subheader(f"{video['Platz']}. {video['Titel']}")
                st.write(f"**Dauer:** {video['Dauer']}")
                st.write(f"**Kategorie:** {video['Kategorie']}")
                st.write(f"**Tags:** {video['Tags']}")
        else:
            st.write("Kein Video passt in das angegebene Zeitbudget.")

####################################
# Tab 2: Personalisierte Empfehlungen
with tabs[1]:
    st.header("Personalisierte Empfehlungen")
    with st.spinner("Lade Empfehlungen..."):
        df_videos = get_trending_videos(youtube)
        video_ids_titles_and_transcripts = combine_video_id_title_and_transcript(df_videos)
        recommendations = get_recommendation(video_ids_titles_and_transcripts=video_ids_titles_and_transcripts, interests=user_interests)

    st.write(recommendations["Titel"])
    st.video(f"https://www.youtube.com/watch?v={recommendations['Video-ID']}")
    st.write("## Begründung:")
    st.write(recommendations["Begründung"])
    st.write("## Für die Interessierten: Hier die Kurzfassung (Achtung: Spoilergefahr!!!)")
    st.write(get_summary(recommendations["Video-ID"]))

    st.info("Diese Funktion wird in Zukunft erweitert, um noch besser auf deine Präferenzen einzugehen.")

####################################
# Tab 3: Suche
with tabs[3]:
    st.header("Suche")
    st.write("Hier kannst du nach Videos oder Kategorien suchen.")
    query = st.text_input("🔎 Wonach suchst du?", "KI Trends 2024")

    youtube = initialize()

    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=10
    )

    if st.button("🔍 Suchen"):
        response = request.execute()
        videos = get_video_data(youtube, response)
        st.session_state["videos"] = videos  # Speichern, damit Filter funktionieren

    if "videos" in st.session_state:
        videos = st.session_state["videos"]

        filtered_videos = [v for v in videos if length_filter[0] * 60 <= duration_to_seconds(v["length"]) <= length_filter[1] * 60]
        for video in filtered_videos:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(video["thumbnail"], use_container_width=True)
            with col2:
                st.subheader(video["title"])
                st.write(f"[📺 Video ansehen](https://www.youtube.com/watch?v={video['video_id']})")

                with st.expander("📜 Zusammenfassung"):
                    st.write('Hier kommt GEMINI Zusammenfassung hin')

                st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
                st.write(video["length"])

####################################
# Tab 4: Feedback & Wünsche
with tabs[4]:
    st.header("Feedback & Wünsche")
    st.write("Hilf uns, das Dashboard zu verbessern!")
    feedback = st.text_area("Dein Feedback oder Verbesserungsvorschläge:")
    if st.button("Feedback absenden"):
        st.success("Danke für dein Feedback!")

# Optional: Button, um das Dashboard manuell zu aktualisieren
if st.button("Dashboard aktualisieren"):
    st.experimental_rerun()
