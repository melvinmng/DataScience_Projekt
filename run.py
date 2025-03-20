from contextlib import nullcontext
import re
import streamlit as st
import pandas as pd
import googleapiclient
import os
from dotenv import load_dotenv, set_key, dotenv_values

# Own Modules
import src.config_env


from src.youtube_transcript import get_transcript
from src.youtube_helper import (
    get_video_data,
    extract_video_id_from_url,
    get_subscriptions,
    get_recent_videos_from_subscriptions,
    search_videos_dlp,
    get_recent_videos_from_channels_RSS,
)

from src.key_management.api_key_management import get_api_key, create_youtube_client
from src.key_management.youtube_channel_id import load_channel_id

from src.youtube_trend_analysis import get_trending_videos


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


def build_feedback_tab() -> None:
    st.header("Feedback & Wünsche")
    st.write("Hilf uns, das Dashboard zu verbessern!")
    feedback = st.text_area("Dein Feedback oder Verbesserungsvorschläge:")
    if st.button("Feedback absenden"):
        # Sollen wir Feedback speichern?
        st.success("Danke für dein Feedback!")


import streamlit as st

def build_search_tab():
    st.header("Suche")
    st.write("Hier kannst du nach Videos oder Kategorien suchen.")
    
    query = st.text_input("🔎 Wonach suchst du?", "KI Trends 2024")

    # Auswahl der Suchmethode
    search_method = st.radio("Suchmethode wählen:", ("YouTube API", "yt-dlp(Experimentell)"))

    # Falls yt-dlp gewählt wurde, zeige einen Slider für die Anzahl der Ergebnisse
    max_results = 10  
    if search_method == "yt-dlp(Experimentell)":
        max_results = st.slider("Anzahl der Videos", min_value=1, max_value=50, value=10)

    if st.button("🔍 Suchen"):
        if search_method == "YouTube API":
            request = youtube.search().list(
                part="snippet", q=query, type="video", maxResults=10
            )
            response = request.execute()
            videos = get_video_data(youtube, response)
        else:
            videos = search_videos_dlp(query, max_results=max_results)

        st.session_state["videos"] = videos  # Speichern, damit Filter funktionieren

    if "videos" in st.session_state:
        videos = st.session_state["videos"]

        filtered_videos = [
            v for v in videos if length_filter[0] * 60 <= duration_to_seconds(v["length"]) <= length_filter[1] * 60
        ]

        for video in filtered_videos:
            st.subheader(video["title"])
            st.write(video["channel_name"])

            st.write(f"[📺 Video ansehen](https://www.youtube.com/watch?v={video['video_id']})")

            # 🟢 **Zusammenfassung anzeigen**
            try:
                transcript = get_transcript(video["video_id"])
                summary = get_summary(transcript)
            except:
                summary = "Keine Zusammenfassung verfügbar."
            with st.expander("📜 Zusammenfassung"):
                st.write(summary)

            # 🎬 **YouTube-Video einbetten**
            st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
            st.write(video["length"])



def build_abobox_tab() -> None:
    st.header("Abobox")
    st.write("Hier findest du die Videos deiner letzten abonnierten Kanäle")
    abo_search_method = st.radio("Abo-Suchmethode wählen:", ("YouTube API", "yt-dlp(Experimentell)"))

    if abo_search_method == "YouTube API":
            max_results = st.slider("Anzahl der Videos pro Kanal", min_value=1, max_value=10, value=4)
    else:
            max_results = st.slider("Anzahl der Videos pro Kanal(yt_dlp)", min_value=1, max_value=100, value=10)
    
    try:
        channelId = load_channel_id()
    except:
        st.write("Kanal-ID nicht gefunden. Bitte überprüfe deine ID.")
        return
    #st.write(channelId)

    try:
        subscriptions = get_subscriptions(channel_Id=channelId, youtube=youtube)
        #st.dataframe(subscriptions)
    except:
        st.write("Bitte stelle sicher, dass deine Abos öffentlich einsehbar sind.")
        return

    

    if st.button("🔄 Abobox laden"):
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


        if abo_search_method == "YouTube API":  
            recent_videos = get_recent_videos_from_subscriptions(youtube, matched_ids, max_results)
        else:
            recent_videos = get_recent_videos_from_channels_RSS(matched_ids, max_results)
    
        st.session_state["videos"] = recent_videos  # Speichern, damit Filter funktionieren

    if "videos" in st.session_state:
        recent_videos = st.session_state["videos"]
        print(recent_videos)
        filtered_videos = [
            v
            for v in recent_videos
            if length_filter[0] * 60
            <= duration_to_seconds(v["length"])
            <= length_filter[1] * 60
        ]

        for video in filtered_videos:
            st.subheader(video["title"])
            st.write(video["channel_name"])

            st.write(f"[📺 Video ansehen](https://www.youtube.com/watch?v={video['video_id']})")

  
            try:
                transcript = get_transcript(video["video_id"])
                summary = get_summary(transcript)
            except:
                summary = "Keine Zusammenfassung verfügbar."
            with st.expander("📜 Zusammenfassung"):
                st.write(summary)

            # 🎬 **YouTube-Video einbetten**
            st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
            if abo_search_method == "yt-dlp(Experimentell)":
                st.write('Upload_Datum: ' + str(video["upload_date"]))
            st.write(video["length"])


def build_settings_pop_up() -> None:
    """Einstellungen als pseudo-modales Fenster mit st.session_state"""
    env_path = ".env"
    load_dotenv()

    # Falls die .env Datei nicht existiert, erstelle sie
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write("# API Keys\n")

    # Lade vorhandene API-Keys
    current_env = dotenv_values(env_path)
    youtube_api_key = current_env.get("YOUTUBE_API_KEY", "")
    openai_api_key = current_env.get("TOKEN_GOOGLEAPI", "")
    channel_id = current_env.get("CHANNEL_ID", "") 

    # Eingabefelder für API-Keys
    youtube_key = st.text_input("🎬 YouTube API Key", youtube_api_key, type="password")
    openai_key = st.text_input("🤖 OpenAI API Key", openai_api_key, type="password")
    channel_id = st.text_input("ℹ️ Channel ID", channel_id, type="password")

    # Speichern-Button
    if st.button("💾 Speichern"):
        if youtube_key:
            set_key(env_path, "YOUTUBE_API_KEY", youtube_key)
        if openai_key:
            set_key(env_path, "TOKEN_GOOGLEAPI", openai_key)
        if channel_id:
            set_key(env_path, "CHANNEL_ID", channel_id)

        # 🔄 API-Keys erneut aus der Datei laden
        updated_env = dotenv_values(env_path)

        # Prüfen, ob die Werte gespeichert wurden
        if (updated_env.get("YOUTUBE_API_KEY") == youtube_key and 
            updated_env.get("TOKEN_GOOGLEAPI") == openai_key and
            updated_env.get("CHANNEL_ID") == channel_id):

            st.success("✅ API-Keys wurden gespeichert!")
            st.session_state.show_settings = False  # Schließt das "Pop-up"
            st.rerun()
            initialize()  # YouTube-Client neu initialisieren
        else:
            st.error("⚠️ Fehler beim Speichern! Bitte erneut versuchen.")

def build_settings_tab() -> None:
    """Tab für API-Key Einstellungen"""
    st.header("⚙️ Einstellungen")

    # Lade vorhandene .env-Datei oder erstelle sie
    env_path = ".env"
    load_dotenv()
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write("# API Keys\n")

    # Vorhandene API-Keys abrufen
    youtube_api_key = os.getenv("YOUTUBE_API_KEY", "")
    openai_api_key = os.getenv("TOKEN_GOOGLEAPI", "")

    # Eingabefelder für API-Keys
    youtube_key = st.text_input("🎬 YouTube API Key", youtube_api_key, type="password")
    openai_key = st.text_input("🤖 OpenAI API Key", openai_api_key, type="password")

    # API-Keys speichern
    if st.button("💾 Speichern"):
        if youtube_key:
            set_key(env_path, "YOUTUBE_API_KEY", youtube_key)
        if openai_key:
            set_key(env_path, "TOKEN_GOOGLEAPI", openai_key)
        st.success("✅ API-Keys wurden gespeichert!")
        st.session_state["Trending Videos"] = 0
        st.rerun()
        initialize()



def initialize() -> googleapiclient.discovery.Resource | None:
    try:
        YT_API_KEY = get_api_key("YOUTUBE_API_KEY")
        youtube: object = create_youtube_client(YT_API_KEY)

        return youtube
    except Exception as e:
        build_settings_pop_up()
        st.stop()

   



############################### CODE #######################################
## Session States
if "show_spoiler" not in st.session_state:
    st.session_state.show_spoiler = False


# Dashboard-Titel
st.title("Dein personalisiertes YouTube-FY-Dashboard")

youtube = initialize()

###----------------------------------###
import src.settings

from src.llm_analysis import (
    extract_video_id_title_and_reason,
    get_summary,
    get_summary_without_spoiler,
    get_recommendation,
    combine_video_id_title_and_transcript,
    check_for_clickbait,
    get_subscriptions_based_on_interests,
)
###----------------------------------###

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
        "Einstellungen"
    ]
)


####################################
# Tab 1: Trending Videos
with tabs[0]:
    if st.button("🔄 Trending Videos laden"):
        build_trending_videos_tab()

####################################
# Tab 2: Personalisierte Empfehlungen
with tabs[1]:
    if st.button("🔄 Empfehlungen laden"):
        build_recommendation_tab()

####################################
# Tab 3: Clickbait Analyse
with tabs[2]:
    if st.button("🔄 Clickbait Analyse laden"):
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

####################################
# Tab 6: Einstellungen
with tabs[6]:
    build_settings_tab()

if st.button("Dashboard aktualisieren"):
    st.experimental_rerun()
