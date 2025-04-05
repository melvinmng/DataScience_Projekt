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
    build_settings_tab 
)

import streamlit as st
############################### CODE #######################################
## Session States

if __name__ == "__main__":
    if "show_spoiler" not in st.session_state:
        st.session_state.show_spoiler = False


    youtube, ai_client, ai_model, ai_generate_content_config= initialize()

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
    with tabs[0]: build_trending_videos_tab(search_method, youtube)
    with tabs[1]: build_recommendation_tab(search_method, youtube, user_interests)
    with tabs[2]: build_clickbait_recognition_tab()
    with tabs[3]: build_search_tab(search_method, youtube)
    with tabs[4]: build_abobox_tab(search_method, youtube, user_interests)
    with tabs[5]: build_watch_later_tab()
    with tabs[6]: build_feedback_tab()
    with tabs[7]: build_settings_tab()