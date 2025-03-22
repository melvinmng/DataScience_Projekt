from contextlib import nullcontext
import re
import streamlit as st
import pandas as pd
import googleapiclient
import os
import csv
from datetime import datetime

# Own Modules
import src.config_env
from src.youtube_transcript import get_transcript
from src.youtube_helper import (
    get_video_data,
    extract_video_id_from_url,
    get_subscriptions,
    get_recent_videos_from_subscriptions,
)
from src.key_management.api_key_management import get_api_key, create_youtube_client
from src.key_management.youtube_channel_id import load_channel_id
from src.youtube_trend_analysis import get_trending_videos
from src.gemini_helper import (
    extract_video_id_title_and_reason,
    get_summary,
    get_summary_without_spoiler,
    get_recommendation,
    combine_video_id_title_and_transcript,
    check_for_clickbait,
    get_subscriptions_based_on_interests,
)


FEEDBACK_FILE = "feedback.csv"


## HELPERS
def duration_to_seconds(duration_str: str) -> int:
    """
    Converts a duration in "MM:SS" format to seconds.

    Args:
        duration_str (str): The duration in "MM:SS" format.

    Returns:
        int: The duration in seconds.
    """
    try:
        minutes, seconds = map(int, duration_str.split(":"))
        return minutes * 60 + seconds
    except Exception as e:
        st.error(f"Fehler beim Parsen der Dauer: {e}")
    return 0


def initialize() -> googleapiclient.discovery.Resource | None:
    try:
        YT_API_KEY = get_api_key("YOUTUBE_API_KEY")
        youtube: object = create_youtube_client(YT_API_KEY)
    except Exception as e:
        st.error(f"Fehler beim Initialisieren des YouTube-Clients: {e}")
        st.stop()

    return youtube


## BUILD TABS
def build_trending_videos_tab() -> None:
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


def build_recommendation_tab(
    retry_count: int = 0,
    show_spinner: bool = True,
    show_loading_time_information: bool = True,
) -> None:
    loading_time_information = None
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
    if recommendations:
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


def save_feedback(feedback_text: str) -> None:
    """
    Speichert das Feedback in einer CSV-Datei mit Datum und Uhrzeit.

    Falls die Datei nicht existiert, wird sie mit den entsprechenden Spalten erstellt.

    Args:
        feedback_text (str): Der eingegebene Feedback-Text.
    """

    # Daten vorbereiten
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")
    feedback_data = [date, time, feedback_text]

    # Prüfen, ob die Datei existiert, falls nicht, erstellen wir sie mit Header
    file_exists = os.path.exists(FEEDBACK_FILE)

    with open(FEEDBACK_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Datum", "Uhrzeit", "Feedback"])  # Header schreiben
        writer.writerow(feedback_data)

    # Erfolgsnachricht anzeigen und Textfeld zurücksetzen
    st.session_state["feedback_submitted"] = True  # Setzt einen Status, dass Feedback gesendet wurde
    st.session_state["feedback_text"] = ""  # Leert das Textfeld
    st.rerun()  # Lädt die Seite neu


def build_feedback_tab() -> None:
    """
    Erstellt das Feedback-Tab im Streamlit-Dashboard.
    """
    st.header("Feedback & Wünsche")
    st.write("Hilf uns, das Dashboard zu verbessern!")

    if "feedback_text" not in st.session_state:
        st.session_state["feedback_text"] = ""

    if "feedback_submitted" not in st.session_state:
        st.session_state["feedback_submitted"] = False  # Status, ob Feedback abgegeben wurde

    feedback = st.text_area("Dein Feedback oder Verbesserungsvorschläge:")

    # Feedback erfolgreich abgegeben
    if st.session_state["feedback_submitted"]:
        st.session_state["feedback_submitted"] = False  # Setzt den Status zurück
        st.success("Vielen Dank für dein Feedback!")

    if st.button("Feedback absenden"):
        if feedback.strip():  # Verhindert Absenden leerer Nachrichten
            save_feedback(feedback)
        else:
            st.warning("Bitte gib ein Feedback ein, bevor du es absendest.")


def build_search_tab():
    st.header("Suche")
    st.write("Hier kannst du nach Videos oder Kategorien suchen.")
    query = st.text_input("🔎 Wonach suchst du?", "KI Trends 2024")

    request = youtube.search().list(
        part="snippet", q=query, type="video", maxResults=10
    )
    ###youtube REQUEST###
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


def build_abobox_tab() -> None:
    st.header("Abobox")
    st.write("Hier findest du die Videos deiner letzten abonnierten Kanäle")
    try:
        channelId = load_channel_id()
    except:
        st.warning("Kanal-ID nicht gefunden. Bitte überprüfe deine ID.")
        return
    st.write(channelId)

    try:
        subscriptions = get_subscriptions(channel_Id=channelId, youtube=youtube)
        st.dataframe(subscriptions)
    except:
        st.warning("Bitte stelle sicher, dass deine Abos öffentlich einsehbar sind.")
        return

    channel_names_and_description = ", ".join(
        subscriptions[subscriptions["description"].str.strip() != ""].apply(
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

        # Filtert Kanäle aus subscriptions mit flexiblerem Regex-Match
        match = subscriptions[
            subscriptions["channel_name"]
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
## Session States
if "show_spoiler" not in st.session_state:
    st.session_state.show_spoiler = False

## Initialization
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
    "Deine Interessensgebiete (kommagetrennt)", value="DM"
)
st.session_state.show_spoiler = st.sidebar.checkbox(
    "Spoiler anzeigen", value=st.session_state.show_spoiler
)


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
    build_trending_videos_tab()

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
    build_search_tab()

####################################
# Tab 4 Abobox
with tabs[4]:
    build_abobox_tab()

####################################
# Tab 5: Feedback & Wünsche
with tabs[5]:
    build_feedback_tab()

if st.button("Dashboard aktualisieren"):
    st.rerun()
