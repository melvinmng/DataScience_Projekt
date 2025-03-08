import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.discovery import build
from IPython.display import JSON
import json
import os

def config_api_key():
    with open("api_config.json") as f:
        config = json.load(f)
    api_key = config["api_key"]
    # print(api_key)
    return api_key

def create_api_client():
    api_service_name = "youtube"
    api_version = "v3"

    # Get credentials and create an API client
    youtube = build(
        api_service_name, api_version, developerKey=config_api_key())
    return youtube

youtube = create_api_client()

# Example Request
'''
request = youtube.channels().list(
    part="snippet,contentDetails,statistics",
    id="UC_x5XG1OV2P6uZZ5FSM9Ttw"
)
response = request.execute()

print(response)
'''