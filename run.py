from src.dashboard_helper import (
    initialize,
    load_interests,
    save_interests,
    build_trending_videos_tab,
    build_recommendation_tab,
    build_clickbait_recognition_tab,
    build_search_tab,
    build_abobox_tab,
    build_watch_later_tab,
    build_feedback_tab,
    build_settings_tab,
)
import streamlit as st
from pathlib import Path


if "show_spoiler" not in st.session_state:
    st.session_state.show_spoiler = False
youtube = initialize()


CSS_FILE_PATH = Path(__file__).parent / "style.css"
with open(CSS_FILE_PATH) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Header
st.title("YourTime")
st.subheader("Dein YouTube Dashboard")

# Sidebar-Einstellungen
st.sidebar.header("Präferenzen")
length_filter = st.sidebar.slider(
    "Wie viele Minuten möchtest du YouTube schauen?",
    min_value=0,
    max_value=180,
    value=(0, 60),
)

user_interests = st.sidebar.text_input("Deine Interessen", value=load_interests())
save_interests(user_interests)

search_method = st.sidebar.radio(
    "Suchmethode", ("YouTube API", "yt-dlp (Experimentell)")
)

st.session_state.show_spoiler = st.sidebar.checkbox(
    "Spoiler anzeigen", value=st.session_state.show_spoiler
)

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
with tabs[0]:
    build_trending_videos_tab(search_method, youtube)
with tabs[1]:
    build_recommendation_tab(search_method, youtube, user_interests)
with tabs[2]:
    build_clickbait_recognition_tab()
with tabs[3]:
    build_search_tab(search_method, youtube)
with tabs[4]:
    build_abobox_tab(search_method, youtube, user_interests)
with tabs[5]:
    build_watch_later_tab()
with tabs[6]:
    build_feedback_tab()
with tabs[7]:
    build_settings_tab()
