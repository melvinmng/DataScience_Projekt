# Personalized YouTube Content Curation

## Purpose
This multifunctional application connects interfaces to 
YouTube and Gemini and allows interaction by means of a graphical representation through Streamlit.
Thereby YouTube content can be structured in a user-specific way. By using artificial intelligence, videos can be summarized and analyzed for clickbait.


## Typical procedure of the application
1. Configuration by the user
2. Fetching data with YouTube API or yt_dlp, respecitvely
3. Processing data with Python and Gemini (2.0 Flash)
4. Displaying results in a graphical user interface with Streamlit


## Setup
### Prerequisites
- Python (3.9+)
- Google account (YouTube account/channel is recommended additionally)


### 1. Clone the repository
```
    https://github.com/melvinmng/DataScience_Projekt.git
    cd DataScience_Projekt
```

### 2. Install requirements
```
    pip install -r requirements.txt
```


### How to work with .env-files
1. Create an .env file in your project folder
2. Save your passwords in the following form in your .env file: NAME_OF_PASSWORD = “Password/Key”

> The .env file can also be automatically generated on first use.


### How to activate APIs
1. Create an account for the Google AI Studio: https://aistudio.google.com/app/apikey?_gl=1*e137ex*_ga*MTE4NjE1OTYwLjE3NDE2MDM4Mzk.*_ga_P1DBVKWT6V*MTc0MTYwNTEyMS4xLjEuMTc0MTYwNTIzMy4wLjAuMTgyNDY0NDU1Nw.


#### Gemini API Key
1. Log in to Google Cloud Platform with your Google account: https://console.cloud.google.com/
2. If necessary, create a project and select it for the API key
3. Activate the Generative Language API for your project via "API and Services" or directly via the search bar.
4. Click on "Get API Key"
5. Click on "Create API Key"
6. Click on "Create API Key in existing project"
7. Copy your API key and paste it into your local .env file so that the code can access it (keep the following structure: TOKEN_GOOGLEAPI = "YOUR_KEY")

> API Keys can be added through the GUI as well.


#### How to create a YouTube API Key
1. Log in to Google Cloud Platform with your Google account: https://console.cloud.google.com/
2. If necessary, create a project and select it for the API key
3. Activate the YouTube Data API v3 for your project via "API and Services" or directly via the search bar.
4. Click on "Credentials"
5. Click on "Create credentials" and select "API key" from
6. Copy your API key and paste it into your local .env file so that the code can access it (keep the following structure: YOUTUBE_API_KEY = "YOUR_KEY")

> API Keys can be added through the GUI as well.


#### [Recommended] Set up access to YouTube subscriptions
1. Make sure you have a YouTube account/channel
2. Log in to YouTube: https://www.youtube.com/
3. Click on "Settings"
4. Click on "Privacy"
5. Make sure that subscriptions are <u>not</u> kept private
6. Click on "Advanced settings"
7. Copy your Channel ID and paste it into your local .env file so that the code can access it (keep the following structure: CHANNEL_ID = "YOUR_ID")

> Access to subscriptions is optional and can be configured later thorugh the GUI as well.


## Run the application
```
    streamlit run run.py
```