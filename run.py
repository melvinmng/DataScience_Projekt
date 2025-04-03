from contextlib import nullcontext
import re
import streamlit as st
st.set_page_config(page_title="YouTube FY Dashboard", layout="wide")
import googleapiclient
import os
import csv
from dotenv import load_dotenv, set_key, dotenv_values
import pandas as pd
from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.metric_cards import style_metric_cards

# Own Modules
import src.config_env

from src.youtube_transcript import get_transcript
from src.youtube_helper import (
    get_video_data,
    get_video_data_dlp,
    extract_video_id_from_url,
    get_subscriptions,
    get_recent_videos_from_subscriptions,
    search_videos_dlp,
    get_recent_videos_from_channels_RSS,
    get_trending_videos, 
    get_trending_videos_dlp
)

from src.key_management.api_key_management import get_api_key, create_youtube_client
from src.key_management.youtube_channel_id import load_channel_id

watch_later_history = 'watch_later_history.csv'
watch_later_csv = 'watch_later.csv'
gitignore ='.gitignore'
Interests_file = "interests.txt"  # Speicherdatei für die Interessen

result = None
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

@st.fragment
def lazy_expander(
    title: str,
    key: str,
    on_expand,
    expanded: bool = False,
    callback_kwargs: dict = None
):
    """
    A 'lazy' expander that only loads/renders content on expand.

    Args:
        title (str): Title to show beside the arrow.
        key (str): Unique key for storing expanded state in st.session_state.
        on_expand (callable): A function that takes a container (and optional kwargs)
                              to fill with content *only* after expanding.
        expanded (bool): Initial state (collapsed=False by default).
        callback_kwargs (dict): Extra kwargs for on_expand() if needed.
    """
    if callback_kwargs is None:
        callback_kwargs = {}

    # Initialize session state in the first run
    if key not in st.session_state or st.session_state[key] is None:
        st.session_state[key] = bool(expanded)

    outer_container = st.container(border=True)

    arrows = ["▼", "▲"]  # down, up
    arrow_keys = ["down", "up"]

    with outer_container:
        col1, col2 = st.columns([0.9, 0.1])
        col1.write(f"**{title}**")

        if col2.button(
            arrows[int(st.session_state[key])],
            key=f"{key}_arrow_{arrow_keys[int(st.session_state[key])]}"
        ):
            # If currently collapsed -> expand and call on_expand
            if not st.session_state[key]:
                st.session_state[key] = True
                on_expand(outer_container, **callback_kwargs)

            # If currently expanded -> collapse (force a rerun)
            else:
                st.session_state[key] = False

@st.fragment
def lazy_button(label: str, key: str, on_click, callback_kwargs: dict = None):
    """
    A 'lazy' button that stores its state in st.session_state and doesn't trigger a full rerun.

    Args:
        label (str): Button label.
        key (str): Unique session state key.
        on_click (callable): Function to call when the button is clicked.
        callback_kwargs (dict): Extra kwargs for on_click() if needed.
    """
    if callback_kwargs is None:
        callback_kwargs = {}

    # Initialisiere den Zustand, falls noch nicht gesetzt
    if key not in st.session_state:
        st.session_state[key] = False

    # Zeige den Button
    if st.button(label, key=f"{key}_btn"):
        st.session_state[key] = True
        on_click(**callback_kwargs)

    # Falls der Button-Status True ist, Erfolgsmeldung anzeigen
    if st.session_state[key]:
        st.success("✅") 
        if label == "🚮delete from list":
            st.rerun()


########################## CSV-Functions ##########################
def write_filename_to_gitignore(gitignore_path, filename):
    if os.path.exists(gitignore_path):
            with open(gitignore_path, "r+", encoding="utf-8") as gitignore_file:
                lines = gitignore_file.readlines()
                if filename not in [line.strip() for line in lines]:
                    gitignore_file.write(f"\n{filename}\n")
    else:
        with open(gitignore_path, "w", encoding="utf-8") as gitignore_file:
            gitignore_file.write(f"{filename}\n")

def read_csv_to_list(filename):
    """
    Liest eine CSV-Datei aus und speichert jede Zeile als Dictionary in einer Liste.
    Entfernt am Ende doppelte Einträge.
    """
    data = []
    
    # CSV-Datei lesen
    with open(filename, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            data.append(dict(row)) 
    
    seen = set()
    unique_data = []
    
    for row in data:
        row_tuple = tuple(row.items())
        
        if row_tuple not in seen:
            seen.add(row_tuple)
            unique_data.append(row)
    
    return unique_data

def update_history_csv(source_file: str = watch_later_csv, history_file: str = watch_later_history, gitignore_path: str = gitignore):
    """
    Fügt neue Einträge aus source_file in history_file ein, falls sie dort noch nicht existieren.
    Falls history_file noch nicht existiert, wird sie erstellt und zur .gitignore hinzugefügt.

    Args:
        source_file (str): Pfad zur aktuellen CSV-Datei.
        history_file (str): Pfad zur History-CSV-Datei (Standard: "history.csv").
        gitignore_path (str): Pfad zur .gitignore-Datei (Standard: ".gitignore").
    """

    # Prüfen, ob die Quell-CSV existiert und nicht leer ist
    if not os.path.exists(source_file) or os.stat(source_file).st_size == 0:
        print("Die Quell-CSV ist leer oder existiert nicht. Keine neuen Einträge.")
        return

    # Falls die History-Datei nicht existiert, sie erstellen und zur .gitignore hinzufügen
    if not os.path.exists(history_file):
        with open(history_file, mode="w", encoding="utf-8") as file:
            pass  # Leere Datei erstellen
        print(f"{history_file} wurde erstellt.")

        write_filename_to_gitignore(gitignore_path, history_file)

    # Bestehende History-Daten einlesen
    history_data = set()
    if os.stat(history_file).st_size > 0:
        with open(history_file, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            header = next(reader, None)  # Header lesen
            for row in reader:
                history_data.add(tuple(row))

    # Neue Daten aus der Quell-CSV einlesen
    new_data = []
    with open(source_file, mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        header = next(reader, None)  # Header lesen
        for row in reader:
            if tuple(row) not in history_data:
                new_data.append(row)

    # Falls es neue Einträge gibt, in die History-CSV speichern
    if new_data:
        with open(history_file, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if not history_data:  # Falls die Datei gerade erst erstellt wurde, Header schreiben
                writer.writerow(header)
            writer.writerows(new_data)
        print(f"{len(new_data)} neue Einträge zur History hinzugefügt.")
    else:
        print("Keine neuen Einträge für die History gefunden.")


def save_video_to_csv(video, filename=watch_later_csv, gitignore_path=gitignore):
    file_exists = os.path.isfile(filename)
    # CSV-Datei schreiben
    with open(filename, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["title", "channel_name", "video_id", "video_url", "length", "views", "summarized_transcript"])
        
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "title": video["title"],
            "channel_name": video["channel_name"],
            "video_id": video["video_id"],
            "video_url": f"https://www.youtube.com/watch?v={video['video_id']}",
            "length": video["length"],
            "views": video['views'],
            "summarized_transcript": get_short_summary_for_watch_list(get_transcript(video['video_id']),video['title'],video["channel_name"]),
        })

    # .gitignore aktualisieren
    write_filename_to_gitignore(gitignore_path, filename)
    

    update_history_csv()

def load_interests():
    """Lädt die Interessen aus der Datei, falls sie existiert."""
    if os.path.exists(Interests_file):
        with open(Interests_file, "r", encoding="utf-8") as file:
            return file.read().strip()
    return ""  # Falls die Datei nicht existiert, leere Zeichenkette zurückgeben

def save_interests(interests):
    """Speichert die Interessen in die Datei, falls sie sich geändert haben."""
    current_interests = load_interests()
    if current_interests != interests:  # Speichern nur, wenn es Änderungen gibt
        with open(Interests_file, "w", encoding="utf-8") as file:
            file.write(interests)

    write_filename_to_gitignore(filename = Interests_file, gitignore_path = gitignore)


def delete_video_by_id(video, filename=watch_later_csv):
    """
    Löscht den Eintrag mit der angegebenen `video_id` aus der CSV-Datei.
    """
    # Liste der Zeilen (als Dictionaries) aus der CSV lesen
    videos = []
    video_id = video['video_id']
    with open(filename, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            videos.append(row)
    
    # Finde und lösche den Eintrag mit der gewünschten video_id
    videos_to_keep = [video for video in videos if video["video_id"] != video_id]

    # Schreibe die aktualisierte Liste zurück in die CSV-Datei
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        fieldnames = ["title", "channel_name", "video_id", "video_url", "length","views", "summarized_transcript"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        writer.writeheader()
        for video in videos_to_keep:
            writer.writerow(video) 

    print(f"Das Video mit der video_id {video_id} wurde erfolgreich gelöscht.")


def build_video_list(incoming_videos, key_id: str):
    saved_video_ids = []
    filename = watch_later_csv
    if os.path.exists(filename):
        # Öffne die CSV-Datei zum Lesen
        with open(filename, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            # Gehe jede Zeile durch und extrahiere den Wert der angegebenen Spalte
            for row in reader:
                if 'video_id' in row:
                    saved_video_ids.append(row['video_id'])
                else:
                    print(f"Spalte '{'video_id'}' nicht gefunden.")

    for video in incoming_videos:
        st.subheader(video["title"])
        st.write(video["channel_name"])
        st.write(f"[📺 Video ansehen](https://www.youtube.com/watch?v={video['video_id']})")

        expander_key = f"summary_{video['video_id']}_{key_id}"
        if expander_key not in st.session_state:
            st.session_state[expander_key] = None

        def load_summary(container, video_id, title):
            try:
                transcript = get_transcript(video_id)
                summary = get_summary(transcript, title) if transcript else "Keine Zusammenfassung verfügbar."
            except:
                summary = "Fehler beim Laden der Zusammenfassung."

            st.session_state[expander_key] = summary
            with container:
                st.write(summary)

        lazy_expander(
            title="📜 Zusammenfassung",
            key=expander_key,
            on_expand=load_summary,
            callback_kwargs={"video_id": video["video_id"], "title": video["title"]},
        )

        st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
        st.write(f"{video['length']} Min.")
        st.write(f"{video['views']} Views")

        if key_id =='watch_later':
            # Nutze den Lazy Button
            lazy_button(
                label="🚮delete from list",
                key=f"del_{video['video_id']}",
                on_click=delete_video_by_id,
                callback_kwargs={"video": video}
            )
            
        else:
            if video['video_id'] not in saved_video_ids:
                lazy_button(
                    label="➕add to watch list",
                    key=f"save_{video['video_id']}",
                    on_click=save_video_to_csv,
                    callback_kwargs={"video": video}
                )            
            
            




## BUILD TABS
def build_trending_videos_tab() -> None:
    st.header("Trending Videos")
    region_code = st.radio("Region wählen:", ("DE", "US", "GB"))
    
    if st.button("🔄 Trending Videos laden"):
        with st.spinner("Lade Trending Videos..."):
            if search_method == "YouTube API":
                try:
                    videos = get_trending_videos(youtube, region_code)
                except Exception as e:
                    st.error(f"API Suche fehlgeschlage: {e}")

            else:
                try:
                    videos = get_trending_videos_dlp(region_code)
                except Exception as e:
                    st.error(f"Video Suche fehlgeschlage: {e}")

            print(videos)
        if not videos:
            st.write("Keine Videos gefunden oder ein Fehler ist aufgetreten.")
        else:
            build_video_list(videos, key_id="trending_videos")

def build_trend_recommondations(retry_count: int = 0, show_spinner: bool = True, show_loading_time_information: bool = True,):
    loading_time_information = None
    max_retries = 3

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

        if search_method == "YouTube API":
            try:
                videos = get_trending_videos(youtube, region_code="DE")
            except Exception as e:
                st.error(f"API Suche fehlgeschlage: {e}")

        else:
            try:   
                videos = get_trending_videos_dlp(region_code="DE")
            except Exception as e:
                st.error(f"Video Suche fehlgeschlagen: {e}")

        if videos:
            video_ids_titles_and_transcripts = combine_video_id_title_and_transcript(
                videos
            )
            recommendations_unfiltered = get_recommendation(
                video_ids_titles_and_transcripts=video_ids_titles_and_transcripts,
                interests=user_interests,
            )

            if recommendations_unfiltered:
                recommendations = extract_video_id_and_reason(
                    recommendations_unfiltered,
                    on_fail=lambda: build_trend_recommondations(
                        retry_count=retry_count + 1,
                        show_spinner=False,
                        show_loading_time_information=False,
                    ),
                )

            if loading_time_information:
                loading_time_information.empty()
        else:
            st.error("Video Liste leer.")

    if recommendations:
        if search_method == "YouTube API":
            request = youtube.videos().list(
                part="snippet", 
                id=recommendations["video_id"]      
            )
            response = request.execute()
            video_data = get_video_data(youtube, response,'trends')
            build_video_list(video_data, key_id="recommendation")
        else:
            video_data = get_video_data_dlp(recommendations["video_id"])
            build_video_list([video_data], key_id="recommendation")

        st.write('## Begründung:')
        st.write(recommendations["Begründung"])

def build_gemini_recommondations(history_path):
    recommended_videos=[]
    try:
        channelId = load_channel_id()
    except Exception as e:
        st.error(f"Kanal-ID nicht gefunden. Bitte überprüfe deine ID.\nFehlermeldung:{e}")
    else:

        if search_method == "YouTube API":
            max_results = st.slider("Videoanzahl pro Kanal", min_value=1, max_value=5, value=2)
            max_abos = st.slider("Kanalanzahl", min_value=1, max_value=20, value=10)
        else:
            max_results = st.slider("Videoanzahl pro Kanal(yt_dlp)", min_value=1, max_value=10, value=5)
            max_abos = st.slider("Kanalanzahl (yt-dlp)", min_value=1, max_value=30, value=10)


        subscriptions = get_subscriptions(channel_Id=channelId, youtube=youtube)
        if os.path.exists(history_path):
            history = read_csv_to_list(history_path)
            if len(history) != 0:
                if st.button("🔄 Gemini Recommendation laden"): 
                    recommended_channels = get_channel_recommondations(history,subscriptions ,max_abos, user_interests)
                    for channel in recommended_channels:
                        print(channel)
                        print('response:_______________________________')
                        if search_method == "YouTube API":
                            request = youtube.search().list(
                                part="snippet", q=channel, type="video", maxResults=max_results
                            )
                            response = request.execute()
                            print(response)
                            videos = get_video_data(youtube, response)
                        else:
                            videos = search_videos_dlp(channel, max_results=max_results)

                        for video in videos:
                            recommended_videos.append(video)

                    build_video_list(recommended_videos, 'gemini_rec')
            else:
                st.error('Um Empfehlungen geben zu können brauchst du einen Watchlist Verlauf.')
        else:
            st.error('Um Empfehlungen geben zu können brauchst du einen Watchlist Verlauf.')

def build_recommendation_tab(
    retry_count: int = 0,
    show_spinner: bool = True,
    show_loading_time_information: bool = True,
) -> None:
    st.header("Personalisierte Empfehlungen")

    # Erstelle die Tabs
    tab1, tab2 = st.tabs(["Trends Recommendation", " Gemini Recommendation"])


    with tab1:
        if st.button("🔄 Trend Recommendation laden"):
            build_trend_recommondations(retry_count, show_spinner, show_loading_time_information)

    with tab2:
        build_gemini_recommondations('watch_later_history.csv')      



def build_clickbait_recognition_tab() -> None:
    st.header("Clickbait Analyse")
    st.write("Teste, ob ein Videotitel als Clickbait einzustufen ist.")

    video_url = st.text_input(
        "🔎 Welches Video möchtest du prüfen? Gib hier die Video-Url ein!",
        "https://www.youtube.com/watch?v=onE9aPkSmlw",
    )
    if st.button("🔄 Clickbait Analyse laden"):
        video_id = extract_video_id_from_url(video_url)

        if video_id:
            video_info = get_video_data_dlp(video_id)
            clickbait_elements = check_for_clickbait(get_transcript(video_id),video_info['title'])
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



def build_search_tab():
    st.session_state["active_tab"] = "search"

    if "videos" not in st.session_state or (st.session_state.get("new_search", False)):
        st.session_state["videos"] = []
        st.session_state["new_search"] = False  # Reset des Flags nach dem Setzen

    st.header("Suche")
    st.write("Hier kannst du nach Videos oder Kategorien suchen.")
    
    query = st.text_input("🔎 Wonach suchst du?", "KI Trends 2024")

    max_results = 10  
    if search_method == "yt-dlp(Experimentell)":
        max_results = st.slider("Anzahl der Videos", min_value=1, max_value=50, value=10)

    if st.button("🔍 Suchen"):
        st.session_state["new_search"] = True  # Neue Suche starten
        if search_method == "YouTube API":
            try:
                request = youtube.search().list(
                    part="snippet", q=query, type="video", maxResults=10
                )
                response = request.execute()
                print(response)
            except Exception as e:
                st.error(f"API Suche fehlgeschlagen: {e}")
            else:
                try:
                    videos = get_video_data(youtube, response)
                except Exception as e:
                    st.error(f"Videodatenformatierung fehlgeschlagen: {e}")
            
        else:
            try:
                videos = search_videos_dlp(query, max_results=max_results)
            except Exception as e:
                st.error(f"Videodatenformatierung fehlgeschlagen: {e}")

        if len(videos)!=0:
            st.session_state["videos"] = videos  # Ergebnisse speichern
            st.session_state["last_tab"] = "search" # Tab-Wechsel speichern
        else:
            st.error("Video Liste ist leer.")

    if st.session_state.get("videos"):
        build_video_list(st.session_state["videos"], key_id="search")
        
        



def build_abobox_tab():
    st.session_state["active_tab"] = "abobox"

    
    if "videos" in st.session_state and st.session_state.get("last_tab") != "abobox":
        st.session_state["videos"] = []

    st.header("Abobox")
    st.write("Hier findest du die Videos deiner letzten abonnierten Kanäle")
    

    if search_method == "YouTube API":
        max_results = st.slider("Anzahl der Videos pro Kanal", min_value=1, max_value=5, value=2)
        max_abos = st.slider("Anzahl der Kanäle", min_value=1, max_value=20, value=10)
    else:
        max_results = st.slider("Anzahl der Videos pro Kanal (yt_dlp)", min_value=1, max_value=10, value=5)
        max_abos = st.slider("Anzahl der Kanäle (yt_dlp)", min_value=1, max_value=30, value=10)
    
    try:
        channelId = load_channel_id()
    except Exception as e:
        st.error(f"Kanal-ID nicht gefunden. Bitte überprüfe deine ID.\nFehlermeldung:{e}")
    else:
        try:
            subscriptions = get_subscriptions(channel_Id=channelId, youtube=youtube)
            if len(subscriptions)==0:
                st.error('APi key aufgebraucht oder Abos nicht auf öffentlich')

        except:
            st.write("Bitte stelle sicher, dass deine Abos öffentlich einsehbar sind.")
        else:
            if st.button("🔄 Abobox laden"):
                channel_names_and_description = ", ".join(
                    subscriptions[subscriptions["description"].str.strip() != ""].apply(
                        lambda row: f"{row['channel_name']}:{row['description']}", axis=1
                    )
                )

                channel_string = get_subscriptions_based_on_interests(
                    channel_names_and_description, user_interests, max_abos
                )

                channel_list = channel_string.split(",")
                print(channel_list)
                if len(channel_list)!=0:
                    try:
                        matched_ids = []
                        for channel in channel_list:
                            normalized_channel = re.sub(r"\W+", "", channel.lower())
                            match = subscriptions[
                                subscriptions["channel_name"]
                                .str.lower()
                                .str.replace(r"\W+", "", regex=True)
                                .str.contains(normalized_channel, na=False)
                            ]
                            print(match)
                            if not match.empty:
                                matched_ids.append(match.iloc[0]["channel_id"])
                        print(matched_ids)
                        try:
                            if search_method == "YouTube API":  
                                recent_videos = get_recent_videos_from_subscriptions(youtube, matched_ids, max_results)
                            else:
                                recent_videos = get_recent_videos_from_channels_RSS(matched_ids, max_results)
                        except Exception as e:
                            st.error(f'Laden der Videos fehlgeschlagen: {e}')
                    except Exception as e :
                        st.error(f'Laden der Videos fehlgeschlagen: {e}')
                    else:
                        st.session_state["videos"] = recent_videos  
                        st.session_state["last_tab"] = "abobox"  # Tab-Wechsel speichern
                
                else:
                    st.error('Generierung der Abo-Vorschläge durch Gemini ist schiefgelaufen')
            if st.session_state.get("videos"):
                print(st.session_state['videos'])
                build_video_list(st.session_state["videos"], key_id="abobox")
            


def build_watch_later_tab():
    st.session_state["active_tab"] = "view_later"

    if "videos" in st.session_state and st.session_state.get("last_tab") != "view_later":
        st.session_state["videos"] = []

    if st.button('neu laden'):
        st.rerun()

    if os.path.exists(watch_later_csv):
        videos = read_csv_to_list(watch_later_csv)
        if len(videos) != 0:
            st.header("Watch list")
            build_video_list(videos, key_id="watch_later")
        else:
            st.error('Es wurden noch keine Videos zur Watchlist hinzugefügt')
    else:
        st.error('Es wurden noch keine Videos zur Watchlist hinzugefügt')

    

    


def build_settings_pop_up() -> None:


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
    gemini_key = st.text_input("🤖 Gemini API Key", openai_api_key, type="password")
    channel_id = st.text_input("ℹ️ Channel ID", channel_id, type="password")

    # Speichern-Button
    if st.button("💾 Speichern"):
        if youtube_key:
            set_key(env_path, "YOUTUBE_API_KEY", youtube_key)
        if gemini_key:
            set_key(env_path, "TOKEN_GOOGLEAPI", gemini_key)
        if channel_id:
            set_key(env_path, "CHANNEL_ID", channel_id)

        # API-Keys erneut aus der Datei laden
        updated_env = dotenv_values(env_path)

        # Prüfen, ob die Werte gespeichert wurden
        if (updated_env.get("YOUTUBE_API_KEY") == youtube_key and 
            updated_env.get("TOKEN_GOOGLEAPI") == gemini_key and
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
    channel_id = os.getenv("CHANNEL_ID", "") 
    # Eingabefelder für API-Keys
    youtube_key = st.text_input("🎬 YouTube API Key", youtube_api_key, type="password")
    gemini_key = st.text_input("🤖 Gemini API Key", openai_api_key, type="password")
    channel_id = st.text_input("ℹ️ Channel ID", channel_id, type="password")

    if st.button("🗑️Watch List history löschen"):
        history = watch_later_history
        
        # CSV einlesen
        df = pd.read_csv(history)
        df1 = pd.read_csv(watch_later_csv)

        # Nur die Header behalten und Datei neu schreiben
        df.iloc[0:0].to_csv(history, index=False)
        df1.iloc[0:0].to_csv(watch_later_csv, index=False)

        st.success('Erfolgreich gelöscht')
    # API-Keys speichern
    if st.button("💾 Speichern"):
        if youtube_key:
            set_key(env_path, "YOUTUBE_API_KEY", youtube_key)
        if gemini_key:
            set_key(env_path, "TOKEN_GOOGLEAPI", gemini_key)
        if channel_id:
            set_key(env_path, "CHANNEL_ID", channel_id)
        st.session_state["Trending Videos"] = 0

        # API-Keys erneut aus der Datei laden
        updated_env = dotenv_values(env_path)

        # Prüfen, ob die Werte gespeichert wurden
        if (updated_env.get("YOUTUBE_API_KEY") == youtube_key and 
            updated_env.get("TOKEN_GOOGLEAPI") == gemini_key and
            updated_env.get("CHANNEL_ID") == channel_id):

            st.success("✅ API-Keys wurden gespeichert!")
            initialize()  # YouTube-Client neu initialisieren
        else:
            st.error("⚠️ Fehler beim Speichern! Bitte erneut versuchen.")



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
youtube = initialize()

###----------------------------------###
import src.settings

from src.llm_analysis import (
    extract_video_id_and_reason,
    get_summary,
    get_summary_without_spoiler,
    get_recommendation,
    combine_video_id_title_and_transcript,
    check_for_clickbait,
    get_subscriptions_based_on_interests,
    get_short_summary_for_watch_list,
    get_channel_recommondations
)
###----------------------------------###

st.markdown(
    """
    <style>
        /* Allgemeine UI-Anpassungen */
        body {
            font-family: 'Arial', sans-serif;
            transition: background 0.3s ease, color 0.3s ease;
        }

        /* Light Mode (YouTube-inspiriert: Weiß, Rot, Grau) */
        @media (prefers-color-scheme: light) {
            body {
                background: #f9f9f9;
                color: #0f0f0f;
            }
            .stSidebar {
                background: rgba(255, 255, 255, 0.9);
                border-right: 2px solid #ddd;
                border-radius: 10px;
            }
            .stButton>button {
                background-color: #ff0000;
                color: white;
                transition: all 0.3s ease-in-out;
                border-radius: 10px;
                box-shadow: 2px 2px 6px rgba(0, 0, 0, 0.2);
            }
            .stButton>button:hover {
                background-color: #cc0000;
                transform: scale(1.05);
            }
            .stTabs {
                background: white;
                border-radius: 10px;
                padding: 15px;
                box-shadow: 2px 2px 12px rgba(0, 0, 0, 0.1);
            }
        }

        /* Dark Mode (Sanftes Blau-Grau für moderne Eleganz) */
        @media (prefers-color-scheme: dark) {
            body {
                background: #121826;
                color: #ffffff;
            }
            .stSidebar {
                background: rgba(30, 39, 50, 0.95);
                border-right: 2px solid #3c4a5f;
                border-radius: 10px;
            }
            .stButton>button {
                background-color: #ff4d4d;
                color: white;
                transition: all 0.3s ease-in-out;
                border-radius: 10px;
                box-shadow: 2px 2px 6px rgba(255, 255, 255, 0.1);
            }
            .stButton>button:hover {
                background-color: #d63030;
                transform: scale(1.05);
                box-shadow: 4px 4px 12px rgba(255, 255, 255, 0.2);
            }
            .stTabs {
                background: #1c2838;
                border-radius: 10px;
                padding: 15px;
                box-shadow: 2px 2px 12px rgba(255, 255, 255, 0.1);
            }
        }

        /* Interaktive Sidebar */
        .stSidebar {
            transition: all 0.3s ease-in-out;
        }
        .stSidebar:hover {
            transform: scale(1.02);
        }

        /* Tabs mit Hover-Animation */
        .stTabs {
            transition: all 0.3s ease-in-out;
        }
        .stTabs:hover {
            transform: scale(1.01);
        }

    </style>
    """,
    unsafe_allow_html=True,
)

# Header
st.title("YouTube FY Dashboard 🎬")
st.subheader("Intelligent. Modern. Interaktiv.")

# Sidebar-Einstellungen
st.sidebar.header("Präferenzen")
length_filter = st.sidebar.slider(
    "Wie lange möchtest du YouTube schauen?",
    min_value=0,
    max_value=180,
    value=(0, 60),
)

user_interests = st.sidebar.text_input("Deine Interessen", value=load_interests())
save_interests(user_interests)

search_method = st.sidebar.radio("Suchmethode wählen:", ("YouTube API", "yt-dlp (Experimentell)"))

st.session_state.show_spoiler = st.sidebar.checkbox("Spoiler anzeigen", value=st.session_state.show_spoiler)

# Tabs für verschiedene Funktionen
tabs = st.tabs(
    [
        "Trending Videos",
        "Empfehlungen",
        "Clickbait Analyse",
        "Suche",
        "Abobox",
        "Watch Later",
        "Feedback",
        "Einstellungen",
    ]
)

# Inhalte der Tabs
with tabs[0]: build_trending_videos_tab()
with tabs[1]: build_recommendation_tab()
with tabs[2]: build_clickbait_recognition_tab()
with tabs[3]: build_search_tab()
with tabs[4]: build_abobox_tab()
with tabs[5]: build_watch_later_tab()
with tabs[6]: build_feedback_tab()
with tabs[7]: build_settings_tab()