from contextlib import nullcontext
import streamlit as st
import pandas as pd
import src.config_env
from src.youtube_transcript import get_transcript
from youtube_helper import get_video_data
from src.key_management.youtube_api_key_management import (
    load_api_key,
    create_api_client,
)
from src.youtube_trend_analysis import get_trending_videos
from src.llm_analysis import (
    get_summary,
    get_summary_without_spoiler,
    get_recommendation,
    combine_video_id_title_and_transcript,
    extract_video_id_title_and_transcript,
)
import src.settings
import googleapiclient
from typing import Optional


## Hilfsfunktionen
def duration_to_seconds(duration_str: str) -> int:
    try:
        parts = duration_str.split(":")
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + int(seconds)
    except Exception as e:
        st.error(f"Fehler beim Parsen der Dauer: {e}")
    return 0


def initialize() -> Optional[googleapiclient.discovery.Resource]:
    try:
        YT_API_KEY = load_api_key()
        YOUTUBE = create_api_client(YT_API_KEY)
    except Exception as e:
        st.error(f"Fehler beim Initialisieren des YouTube-Clients: {e}")
        st.stop()

    return YOUTUBE


def build_recommendation_tab(retry_count: int = 0, show_spinner: bool = True) -> None:
    max_retries = 3
    if retry_count == 0:
        st.header("Personalisierte Empfehlungen")

    if retry_count >= max_retries:
        st.error(
            "Nach mehreren Versuchen konnte keine Empfehlung generiert werden.\nBitte versuchen Sie es später erneut."
        )
        return

    spinner_context = (
        st.spinner("Lade Empfehlungen...") if show_spinner else nullcontext()
    )
    with spinner_context:
        loading_time_information = st.empty()
        loading_time_information.info(
            "Bitte beachten Sie eine möglicherweise längere Ladezeit aufgrund der hohen Datenmenge und QA-Mechanismen."
        )
        df_videos = get_trending_videos(YOUTUBE)
        video_ids_titles_and_transcripts = combine_video_id_title_and_transcript(
            df_videos
        )
        recommendations_unfiltered = get_recommendation(
            video_ids_titles_and_transcripts=video_ids_titles_and_transcripts,
            interests=user_interests,
        )
        recommendations = extract_video_id_title_and_transcript(
            recommendations_unfiltered,
            on_fail=lambda: build_recommendation_tab(
                retry_count=retry_count + 1, show_spinner=False
            ),
        )
        loading_time_information.empty()

    st.write(recommendations["Titel"])
    st.video(f"https://www.youtube.com/watch?v={recommendations['Video-ID']}")
    st.write("## Begründung:")
    st.write(recommendations["Begründung"])
    st.write(
        "## Für die Interessierten: Hier die Kurzfassung (Achtung: Spoilergefahr!!!)"
    )
    if st.session_state.show_spoiler == True:
        st.write(get_summary(get_transcript(recommendations["Video-ID"])))
    else:
        st.write(
            get_summary_without_spoiler(get_transcript(recommendations["Video-ID"]))
        )

    st.info(
        "Diese Funktion wird in Zukunft erweitert, um noch besser auf deine Präferenzen einzugehen."
    )


## Session States
if "show_spoiler" not in st.session_state:
    st.session_state.show_spoiler = False


## Initialisierung
st.title("Dein personalisiertes YouTube-FY-Dashboard")

st.sidebar.header("Einstellungen")
length_filter = st.sidebar.slider(
    "Wie viele Minuten hast du heute für YouTube?",
    min_value=0,
    max_value=180,
    value=(0, 60),
    help="Wähle dein verfügbares Zeitbudget in Minuten.",
)
user_interests = st.sidebar.text_input(
    "Deine Interessensgebiete (kommagetrennt)", value=src.settings.interests
)
st.session_state.show_spoiler = st.sidebar.checkbox(
    "Spoiler anzeigen", value=st.session_state.show_spoiler
)


tabs = st.tabs(
    ["Trending Videos", "Empfehlungen", "Clickbait Analyse", "Suche", "Feedback"]
)

YOUTUBE = initialize()


####################################
# Tab 1: Trending Videos
with tabs[0]:
    st.header("Trending Videos")

    with st.spinner("Lade Trending Videos..."):
        df_videos = get_trending_videos(YOUTUBE)

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
        else:
            st.write("Kein Video passt in das angegebene Zeitbudget.")

####################################
# Tab 2: Personalisierte Empfehlungen
with tabs[1]:
    build_recommendation_tab()

####################################
# Tab 3: Clickbait Analyse

# with tabs[2]:
# st.header("Clickbait Analyse")
# st.write("Teste, ob ein Videotitel als Clickbait einzustufen ist.")
# video_title = st.text_input("Gib einen Videotitel ein:")
# if st.button("Analyse starten"):
# if video_title:
# score = evaluate_video_clickbait(video_title)
# st.write(f"Das Clickbait-Risiko für den Titel **{video_title}** wird als **{score}** eingestuft.")
# else:
# st.warning("Bitte gib einen Titel ein, um die Analyse zu starten.")"


####################################
# Tab 3: Suche
with tabs[3]:
    st.header("Suche")
    st.write("Hier kannst du nach Videos oder Kategorien suchen.")
    query = st.text_input("🔎 Wonach suchst du?", "KI Trends 2024")

    request = YOUTUBE.search().list(
        part="snippet", q=query, type="video", maxResults=10
    )
    response = request.execute()

    if st.button("🔍 Suchen"):
        videos = get_video_data(YOUTUBE, response)
        st.session_state["videos"] = videos

    if "videos" in st.session_state:
        videos = st.session_state["videos"]

        filtered_videos = [
            v
            for v in videos
            if length_filter[0] * 60
            <= duration_to_seconds(v["length"])
            <= length_filter[1] * 60
        ]
        for video in filtered_videos:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(video["thumbnail"], use_container_width=True)
            with col2:
                st.subheader(video["title"])

                st.write(
                    f"[📺 Video ansehen](https://www.youtube.com/watch?v={video['video_id']})"
                )

                with st.expander("📜 Zusammenfassung"):
                    st.write("Hier kommt GEMINI Zusammenfassung hin")

                st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
                st.write(video["length"])
####################################
# Tab 4: Feedback & Wünsche
with tabs[4]:
    st.header("Feedback & Wünsche")
    st.write("Hilf uns, das Dashboard zu verbessern!")
    feedback = st.text_area("Dein Feedback oder Verbesserungsvorschläge:")
    if st.button("Feedback absenden"):
        # Sollen wir Feedback speichern?
        st.success("Danke für dein Feedback!")

if st.button("Dashboard aktualisieren"):
    st.experimental_rerun()
