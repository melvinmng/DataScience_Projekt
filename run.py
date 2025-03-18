from contextlib import nullcontext
from logging import warn
import streamlit as st
import pandas as pd
import src.config_env
from src.youtube_transcript import get_transcript
from youtube_helper import get_video_data, extract_video_id_from_url
from src.key_management.youtube_api_key_management import (
    load_api_key,
    create_api_client,
)
from src.youtube_trend_analysis import get_trending_videos
from src.llm_analysis import (
    extract_video_id_title_and_reason,
    get_summary,
    get_summary_without_spoiler,
    get_recommendation,
    combine_video_id_title_and_transcript,
    check_for_clickbait,
)
import re

# Konfiguration und API-Initialisierung
import src.config_env  # Lädt die .env-Date
from youtube_helper import (
    get_video_data,
    get_subscriptions,
    get_recent_videos_from_subscriptions,
)
from src.key_management.youtube_api_key_management import (
    load_api_key,
    create_api_client,
)
from src.key_management.gemini_api_key_management import get_api_key
from src.key_management.youtube_channel_id import load_channel_id
from src.youtube_trend_analysis import get_trending_videos
from src.llm_analysis import (
    get_summary,
    get_summary_without_spoiler,
    get_recommendation,
    combine_video_id_title_and_transcript,
    get_subscriptions_based_on_interests,
)  # check_for_clickbait sind noch Platzhalter
import src.settings
import googleapiclient
from typing import Optional


# HELPERS
def duration_to_seconds(duration_str: str) -> int:
    try:
        parts = duration_str.split(":")
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + int(seconds)
    except Exception as e:
        st.error(f"Fehler beim Parsen der Dauer: {e}")
    return 0


def initialize() -> googleapiclient.discovery.Resource | None:
    try:
        YT_API_KEY = load_api_key()
        youtube = create_api_client(YT_API_KEY)
    except Exception as e:
        st.error(f"Fehler beim Initialisieren des YouTube-Clients: {e}")
        st.stop()

    return youtube


## BUILD TABS
def build_recommendation_tab(
    retry_count: int = 0,
    show_spinner: bool = True,
    show_loading_time_information: bool = True,
) -> None:
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
        if show_loading_time_information:
            loading_time_information = st.empty()
            loading_time_information.info(
                "Bitte beachten Sie eine möglicherweise längere Ladezeit aufgrund der hohen Datenmenge und QA-Mechanismen."
            )
        df_videos = get_trending_videos(youtube)
        video_ids_titles_and_transcripts = combine_video_id_title_and_transcript(
            df_videos
        )
        recommendations_unfiltered = get_recommendation(
            video_ids_titles_and_transcripts=video_ids_titles_and_transcripts,
            interests=user_interests,
        )
        if recommendations_unfiltered:
            recommendations = extract_video_id_title_and_reason(
                recommendations_unfiltered,
                on_fail=lambda: build_recommendation_tab(
                    retry_count=retry_count + 1,
                    show_spinner=False,
                    show_loading_time_information=False,
                ),
            )
        if loading_time_information:
            loading_time_information.empty()

    st.write(recommendations["Titel"])
    st.video(f"https://www.youtube.com/watch?v={recommendations['Video-ID']}")
    st.write("## Begründung:")
    st.write(recommendations["Begründung"])
    st.write(
        "## Für die Interessierten: Hier die Kurzfassung (Achtung: Spoilergefahr je nach Einstellung in Sidebar!!!)"
    )
    if st.session_state.show_spoiler == True:
        st.write(get_summary(get_transcript(recommendations["Video-ID"])))
    else:
        st.write(
            get_summary_without_spoiler(get_transcript(recommendations["Video-ID"]))
        )


def build_clickbait_recognition_tab() -> None:
    st.header("Clickbait Analyse")
    st.write("Teste, ob ein Videotitel als Clickbait einzustufen ist.")

    video_url = st.text_input(
        "🔎 Welches Video möchtest du prüfen? Gib hier die Video-Url ein!",
        "https://www.youtube.com/watch?v=onE9aPkSmlw",
    )
    video_id = extract_video_id_from_url(video_url)

    if video_id:
        clickbait_elements = check_for_clickbait(get_transcript(video_id))
        if clickbait_elements == "no transcript":
            st.warning(
                "Leider konnte für dieses Video keine Transkript erstellt und folglich keine Analyse durchgeführt werden. Bitte versuchen Sie es mit einem anderen Video."
            )
        elif clickbait_elements == "no response":
            st.warning(
                "Es gab leider ein Problem mit Gemini. Bitte versuchen Sie es später noch einmal."
            )
        else:
            st.video(f"https://www.youtube.com/watch?v={video_id}")
            st.write(clickbait_elements)
    else:
        st.warning(
            "Kein Video mit dieser Video-ID gefunden, bitte versuchen Sie es noch einmal"
        )


## Session States
if "show_spoiler" not in st.session_state:
    st.session_state.show_spoiler = False


## INITIALIZATION


def load_tab(tab_name):
    st.session_state["loaded_tabs"][tab_name] = True


def search():
    st.header("Suche")
    load_tab("Suche")
    st.write("Hier kannst du nach Videos oder Kategorien suchen.")
    query = st.text_input("🔎 Wonach suchst du?", "KI Trends 2024")

    request = youtube.search().list(
        part="snippet", q=query, type="video", maxResults=10
    )
    ###YOUTUBE REQUEST###
    response = request.execute()

    if st.button("🔍 Suchen"):
        videos = get_video_data(youtube, response)
        st.session_state["videos"] = videos  # Speichern, damit Filter funktionieren

    if "videos" in st.session_state:
        videos = st.session_state["videos"]

        filtered_videos = [
            v
            for v in videos
            if length_filter[0] * 60
            <= duration_to_seconds(v["length"])
            <= length_filter[1] * 60
        ]
        # FIlter so konfigurieren, dass Videos mit ensprechender Länge gesucht werden.
        for video in filtered_videos:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(video["thumbnail"], use_container_width=True)
            with col2:
                st.subheader(video["title"])
                st.write(video["channel_name"])

                st.write(
                    f"[📺 Video ansehen](https://www.youtube.com/watch?v={video['video_id']})"
                )

                # 🟢 **Zusammenfassung anzeigen**
                with st.expander("📜 Zusammenfassung"):
                    st.write("Hier kommt GEMINI Zusammenfassung hin")

                # 🎬 **YouTube-Video einbetten**
                st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
                st.write(video["length"])


def abobox():
    st.header("Abobox")
    load_tab("Abobox")
    st.write("Hier findest du die Videos deiner letzten abonnierten Kanäle")
    try:
        channelId = load_channel_id()
    except:
        st.write("Kanal-ID nicht gefunden. Bitte überprüfe deine ID.")
    st.write(channelId)
    try:
        Subs = get_subscriptions(channel_Id=channelId, YOUTUBE=youtube)
        st.dataframe(Subs)
    except:
        st.write("Bitte stelle sicher, dass deine Abos öffentlich einsehbar sind.")

    channel_names_and_description = ", ".join(
        Subs[Subs["description"].str.strip() != ""].apply(
            lambda row: f"{row['channel_name']}:{row['description']}", axis=1
        )
    )

    channel_string = get_subscriptions_based_on_interests(
        channel_names_and_description, user_interests, 10
    )

    channel_list = channel_string.split(",")

    matched_ids = []

    for channel in channel_list:
        # Kanalnamen normalisieren (entfernt Leerzeichen & Sonderzeichen)
        normalized_channel = re.sub(r"\W+", "", channel.lower())

        # Filtert Kanäle aus Subs mit flexiblerem Regex-Match
        match = Subs[
            Subs["channel_name"]
            .str.lower()
            .str.replace(r"\W+", "", regex=True)
            .str.contains(normalized_channel, na=False)
        ]

        if not match.empty:
            matched_ids.append(match.iloc[0]["channel_id"])

    recent_videos = get_recent_videos_from_subscriptions(youtube, matched_ids, 4)
    filtered_videos = [
        v
        for v in recent_videos
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
            st.write(video["channel_name"])

            st.write(
                f"[📺 Video ansehen](https://www.youtube.com/watch?v={video['video_id']})"
            )

            # 🟢 **Zusammenfassung anzeigen**
            with st.expander("📜 Zusammenfassung"):
                st.write("Hier kommt GEMINI Zusammenfassung hin")

            # 🎬 **YouTube-Video einbetten**
            st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
            st.write(video["length"])


############################### CODE #######################################


if "loaded_tabs" not in st.session_state:
    st.session_state["loaded_tabs"] = {
        "Trending Videos": False,
        "Empfehlungen": False,
        "Clickbait Analyse": False,
        "Suche": False,
        "Abobox": False,
        "Feedback": False,
    }

# Dashboard-Titel
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


# Verwenden von Tabs, um verschiedene Funktionen übersichtlich zu präsentieren
tabs = st.tabs(
    [
        "Trending Videos",
        "Empfehlungen",
        "Clickbait Analyse",
        "Suche",
        "Abobox",
        "Feedback",
    ]
)

youtube = initialize()
####################################
# Tab 1: Trending Videos
with tabs[0]:
    st.header("Trending Videos")

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
        else:
            st.write("Kein Video passt in das angegebene Zeitbudget.")

####################################
# Tab 2: Personalisierte Empfehlungen
with tabs[1]:
    build_recommendation_tab()

####################################
# Tab 3: Clickbait Analyse

with tabs[2]:
    build_clickbait_recognition_tab()


####################################
# Tab 3: Suche
with tabs[3]:
    search()

####################################
# Tab 4 Abobox
with tabs[4]:
    abobox()

####################################
# Tab 5: Feedback & Wünsche
with tabs[5]:
    st.header("Feedback & Wünsche")
    load_tab("Feedback & Wünsche")
    st.write("Hilf uns, das Dashboard zu verbessern!")
    feedback = st.text_area("Dein Feedback oder Verbesserungsvorschläge:")
    if st.button("Feedback absenden"):
        # Sollen wir Feedback speichern?
        st.success("Danke für dein Feedback!")

if st.button("Dashboard aktualisieren"):
    st.experimental_rerun()
