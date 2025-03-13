import streamlit as st
import pandas as pd

# Konfiguration und API-Initialisierung
import src.config_env  # Lädt die .env-Date
from youtube_helper import get_video_data
from src.key_management.youtube_api_key_management import load_api_key, create_api_client
from src.key_management.gemini_api_key_management import get_api_key
from src.youtube_trend_analysis import get_trending_videos
from src.llm_analysis import get_summary, get_summary_without_spoiler # get_recommendation und check_for_clickbait sind noch Platzhalter
import src.settings

# Hilfsfunktion: Konvertiere "MM:SS" in Sekunden
def duration_to_seconds(duration_str: str) -> int:
    try:
        parts = duration_str.split(":")
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + int(seconds)
    except Exception as e:
        st.error(f"Fehler beim Parsen der Dauer: {e}")
    return 0

# Dummy-Implementierung für personalisierte Empfehlungen (Platzhalter)
def get_personalized_recommendations(interests: str) -> pd.DataFrame:
    # Hier könntest du z. B. die Funktion get_recommendation in llm_analysis nutzen,
    # um auf Basis der Interessen personalisierte Vorschläge zu generieren.
    # Aktuell wird ein Dummy-DataFrame zurückgegeben.
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

# Dashboard-Titel
st.title("Dein personalisiertes YouTube-FY-Dashboard")

# Sidebar: Grundlegende Einstellungen
st.sidebar.header("Einstellungen")

# Range-Slider für die verfügbare Zeit
length_filter = st.sidebar.slider(
    "Wie viele Minuten hast du heute für YouTube?",
    min_value=0,
    max_value=180,
    value=(0, 60),  # Standardbereich (von 10 bis 60 Minuten)
    help="Wähle dein verfügbares Zeitbudget in Minuten."
)

user_interests = st.sidebar.text_input("Deine Interessensgebiete (kommagetrennt)", value=src.settings.interests)

# Verwenden von Tabs, um verschiedene Funktionen übersichtlich zu präsentieren
tabs = st.tabs(["Trending Videos", "Empfehlungen", "Clickbait Analyse", "Suche", "Feedback"])

####################################
# Tab 1: Trending Videos
with tabs[0]:
    st.header("Trending Videos")
    try:
        yt_api_key = load_api_key()
        youtube = create_api_client(yt_api_key)
    except Exception as e:
        st.error(f"Fehler beim Initialisieren des YouTube-Clients: {e}")
        st.stop()

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
            if cumulative_time + video_duration_seconds <= length_filter[1]:
                selected_videos.append(row)
                cumulative_time += video_duration_seconds

        if selected_videos:
            st.header("Empfohlene Videos für dein Zeitbudget")
            for video in selected_videos:
                st.subheader(f"{video['Platz']}. {video['Titel']}")
                st.write(f"**Dauer:** {video['Dauer']}")
                st.write(f"**Kategorie:** {video['Kategorie']}")
                st.write(f"**Tags:** {video['Tags']}")
                # Beispiel: Clickbait-Bewertung (hier könnte man später noch differenziertere Ansätze einbinden)
                #clickbait_score = evaluate_video_clickbait(video['Titel'])
                #st.write(f"**Clickbait-Risiko:** {clickbait_score}")
                #st.markdown("---")
        else:
            st.write("Kein Video passt in das angegebene Zeitbudget.")

####################################
# Tab 2: Personalisierte Empfehlungen
with tabs[1]:
    st.header("Personalisierte Empfehlungen")
    st.write("Hier werden Videos angezeigt, die basierend auf deinen Interessen und deinem Zeitbudget empfohlen werden.")
    # Hier wird eine Dummy-Funktion verwendet. Ersetze sie später durch deine eigene Logik.
    recommendations_df = get_personalized_recommendations(user_interests)
    st.dataframe(recommendations_df)
    # Beispiel: Man könnte hier auch Details oder Zusammenfassungen via LLM einbinden
    st.info("Diese Funktion wird in Zukunft erweitert, um noch besser auf deine Präferenzen einzugehen.")

####################################
# Tab 3: Clickbait Analyse

#with tabs[2]:
    #st.header("Clickbait Analyse")
    #st.write("Teste, ob ein Videotitel als Clickbait einzustufen ist.")
    #video_title = st.text_input("Gib einen Videotitel ein:")
    #if st.button("Analyse starten"):
        #if video_title:
            #score = evaluate_video_clickbait(video_title)
            #st.write(f"Das Clickbait-Risiko für den Titel **{video_title}** wird als **{score}** eingestuft.")
        #else:
            #st.warning("Bitte gib einen Titel ein, um die Analyse zu starten.")"


####################################
#Tab 3: Suche
with tabs[3]:
    st.header("Suche")
    st.write("Hier kannst du nach Videos oder Kategorien suchen.")
    query = st.text_input("🔎 Wonach suchst du?", "KI Trends 2024")

    ###YOUTUBE REQUEST###
    yt_api_key = load_api_key()
    YOUTUBE = create_api_client(yt_api_key)

    request = YOUTUBE.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=10
    )
    ###YOUTUBE REQUEST###
    response = request.execute()

    if st.button("🔍 Suchen"):
        videos = get_video_data(YOUTUBE, response)
        st.session_state["videos"] = videos  # Speichern, damit Filter funktionieren

    if "videos" in st.session_state:
        videos = st.session_state["videos"]

        filtered_videos = [v for v in videos if length_filter[0]*60 <= duration_to_seconds(v["length"]) <= length_filter[1]*60]
        #FIlter so konfigurieren, dass Videos mit ensprechender Länge gesucht werden.
        for video in filtered_videos:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(video["thumbnail"], use_container_width=True)
                with col2:
                    st.subheader(video["title"])

                    st.write(f"[📺 Video ansehen](https://www.youtube.com/watch?v={video['video_id']})")

                    # 🟢 **Zusammenfassung anzeigen**
                    with st.expander("📜 Zusammenfassung"):
                        st.write('Hier kommt GEMINI Zusammenfassung hin')

                    # 🎬 **YouTube-Video einbetten**
                    st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
                    st.write(video["length"])
####################################
# Tab 4: Feedback & Wünsche
with tabs[4]:
    st.header("Feedback & Wünsche")
    st.write("Hilf uns, das Dashboard zu verbessern!")
    feedback = st.text_area("Dein Feedback oder Verbesserungsvorschläge:")
    if st.button("Feedback absenden"):
        # Hier könntest du das Feedback speichern, per E-Mail versenden oder in einer Datenbank ablegen.
        st.success("Danke für dein Feedback!")

# Optional: Button, um das Dashboard manuell zu aktualisieren
if st.button("Dashboard aktualisieren"):
    st.experimental_rerun()
