import pytest
import os
import re
import datetime as dt
import pandas as pd
from unittest.mock import patch, MagicMock, mock_open, call, ANY
from pathlib import Path
from concurrent.futures import Future


# === Mock Data ===

MOCK_YT_DLP_SEARCH_RESULT = {
    "entries": [
        {
            "id": "search_vid_1",
            "title": "Search Result 1 (DLP)",
            "thumbnail": "thumb_search1_url",
            "uploader": "Search Channel A",
            "duration": 65,  # 1:05
            "tags": ["search", "dlp"],
            "upload_date": "20240110",
            "view_count": 101,
        },
        {
            "id": "search_vid_2",
            "title": "Search Result 2 (DLP)",
            "thumbnail": "thumb_search2_url",
            "uploader": "Search Channel B",
            "duration": 125,  # 2:05
            "tags": [],
            "upload_date": "20240101",
            "view_count": 202,
        },
    ]
}

MOCK_YT_DLP_VIDEO_RESULT = {
    "video_id": "dlp_vid_1",
    "title": "Specific Video (DLP)",
    "tags": "dlp, video",
    "thumbnail": "thumb_dlp_vid1_url",
    "length": "03:25",
    "upload_date": dt.datetime(2024, 2, 1),
    "channel_name": "DLP Channel",
    "views": 325,
}

MOCK_FEED_CH1 = MagicMock()
MOCK_FEED_CH1.entries = [MagicMock(link="https://www.youtube.com/watch?v=4")]

MOCK_FEED_CH2 = MagicMock()
MOCK_FEED_CH2.entries = [MagicMock(link="https://www.youtube.com/watch?v=5")]

MOCK_VIDEO_RSS1 = {
    "video_id": "ch1_vid_rss1",
    "title": "RSS Vid 1",
    "tags": "rss, test",
    "thumbnail": "thumb_rss1",
    "length": "01:00",
    "upload_date": dt.datetime(2024, 3, 1, 10),
    "channel_name": "RSS Channel 1",
    "views": 111,
}
MOCK_VIDEO_RSS2 = {
    "video_id": "ch2_vid_rss1",
    "title": "RSS Vid 2",
    "tags": "rss, test2",
    "thumbnail": "thumb_rss2",
    "length": "02:00",
    "upload_date": dt.datetime(2024, 3, 5, 15),
    "channel_name": "RSS Channel 2",
    "views": 222,
}

MOCK_YT_API_CATEGORIES = {
    "items": [
        {"id": "1", "snippet": {"title": "Film & Animation"}},
        {"id": "10", "snippet": {"title": "Music"}},
        {"id": "20", "snippet": {"title": "Gaming"}},
    ]
}

MOCK_YT_API_SUBSCRIPTIONS_PAGE1 = {
    "items": [
        {
            "snippet": {
                "title": "Sub Channel 1",
                "resourceId": {"channelId": "sub_ch_1"},
                "publishedAt": "2023-01-01T00:00:00Z",
                "description": "Desc 1",
                "thumbnails": {"default": {"url": "thumb_sub1"}},
            },
            "contentDetails": {"totalItemCount": 100, "newItemCount": 5},
            "id": "sub_id_1",
        },
        {
            "snippet": {
                "title": "Sub Channel 2",
                "resourceId": {"channelId": "sub_ch_2"},
                "publishedAt": "2023-02-01T00:00:00Z",
                "description": "Desc 2",
                "thumbnails": {"default": {"url": "thumb_sub2"}},
            },
            "contentDetails": {"totalItemCount": 50, "newItemCount": 0},
            "id": "sub_id_2",
        },
    ],
    "nextPageToken": "page2_token",
}

MOCK_YT_API_SUBSCRIPTIONS_PAGE2 = {
    "items": [
        {
            "snippet": {
                "title": "Sub Channel 3",
                "resourceId": {"channelId": "sub_ch_3"},
                "publishedAt": "2023-03-01T00:00:00Z",
                "description": "Desc 3",
                "thumbnails": {"default": {"url": "thumb_sub3"}},
            },
            "contentDetails": {"totalItemCount": 200, "newItemCount": 10},
            "id": "sub_id_3",
        }
    ],
}

MOCK_YT_API_SEARCH_RESULT_CH1 = {
    "items": [{"id": {"videoId": "ch1_vid1"}, "snippet": {"title": "Video from Ch1"}}],
}
MOCK_YT_API_SEARCH_RESULT_CH2 = {
    "items": [{"id": {"videoId": "ch2_vid1"}, "snippet": {"title": "Video from Ch2"}}],
}

MOCK_GET_VIDEO_DATA_RESULT_CH1 = [
    {
        "video_id": "ch1_vid1",
        "title": "Parsed Video from Ch1",
        "length": "1:00",
        "views": 1,
        "channel_name": "Ch1",
    }
]
MOCK_GET_VIDEO_DATA_RESULT_CH2 = [
    {
        "video_id": "ch2_vid1",
        "title": "Parsed Video from Ch2",
        "length": "2:00",
        "views": 2,
        "channel_name": "Ch2",
    }
]

MOCK_FEED_CH1 = MagicMock()
MOCK_FEED_CH1.entries = [
    MagicMock(link="https://www.youtube.com/feed/trending?gl=ch1_vid_rss1")
]
MOCK_FEED_CH2 = MagicMock()
MOCK_FEED_CH2.entries = [
    MagicMock(link="https://www.youtube.com/feed/trending?gl=ch2_vid_rss1")
]

MOCK_YT_API_TRENDING_RESULT = {
    "items": [
        {
            "id": "trend_vid_1",
            "snippet": {"title": "Trending 1", "publishedAt": "2024-04-09T10:00:00Z"},
        },
        {
            "id": "trend_vid_2",
            "snippet": {"title": "Trending 2", "publishedAt": "2024-04-10T12:00:00Z"},
        },
    ]
}
MOCK_GET_VIDEO_DATA_RESULT_TRENDING = [
    {
        "video_id": "trend_vid_2",
        "title": "Parsed Trending 2",
        "length": "3:00",
        "views": 3,
        "channel_name": "Trendsetter",
        "upload_date": dt.datetime(2024, 4, 10, 12),
    },
    {
        "video_id": "trend_vid_1",
        "title": "Parsed Trending 1",
        "length": "4:00",
        "views": 4,
        "channel_name": "Trendsetter",
        "upload_date": dt.datetime(2024, 4, 9, 10),
    },
]

MOCK_YT_DLP_TRENDING_ENTRIES = {
    "entries": [
        {"id": "trend_dlp_1"},
        {"id": "trend_dlp_2"},
        {"id": "trend_dlp_3"},
    ]
}


# === TESTS ===


@patch("src.helpers.youtube_helper.yt_dlp.YoutubeDL")
def test_search_videos_dlp(mock_yt_dlp_cls):
    """Tests searching videos using yt-dlp."""
    from src.helpers.youtube_helper import search_videos_dlp

    mock_ydl_instance = MagicMock()
    mock_yt_dlp_cls.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.return_value = MOCK_YT_DLP_SEARCH_RESULT

    query = "test query"
    max_results = 50
    videos = search_videos_dlp(query, max_results=max_results)

    expected_ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "default_search": "ytsearch",
        "noplaylist": True,
        "extract_flat": True,
        "no_warnings": True,
    }

    mock_ydl_instance.extract_info.assert_called_once_with(
        f"ytsearch{max_results}:{query}", download=False
    )

    assert len(videos) == 2
    # Results should be sorted by date descending (2024-01-10 then 2024-01-01)
    assert videos[0]["video_id"] == "search_vid_1"
    assert videos[1]["video_id"] == "search_vid_2"
    assert videos[0]["title"] == "Search Result 1 (DLP)"
    assert videos[0]["length"] == "01:05"
    assert videos[0]["tags"] == "search, dlp"
    assert videos[0]["upload_date"] == dt.datetime(2024, 1, 10)
    assert videos[1]["tags"] == "Keine Tags"
    assert videos[1]["upload_date"] == dt.datetime(2024, 1, 1)
    assert videos[1]["length"] == "02:05"


@patch("googleapiclient.discovery.Resource")
def test_get_category_name(MockResource):
    """Tests getting category name from YouTube API."""
    from src.helpers.youtube_helper import get_category_name

    mock_youtube = MockResource()
    mock_categories_list = mock_youtube.videoCategories.return_value.list
    mock_execute = mock_categories_list.return_value.execute
    mock_execute.return_value = MOCK_YT_API_CATEGORIES

    name_music = get_category_name(mock_youtube, "10")
    assert name_music == "Music"

    name_unknown = get_category_name(mock_youtube, "999")
    assert name_unknown == "Unbekannte Kategorie"

    assert mock_categories_list.call_count == 2
    assert mock_execute.call_count == 2


@patch("src.helpers.youtube_helper.pd.read_csv")
@patch("src.helpers.youtube_helper.os.path.isfile")
@patch("googleapiclient.discovery.Resource")
def test_get_subscriptions_csv_exists(
    mock_resource, mock_isfile, mock_read_csv, tmp_path
):
    """Tests get_subscriptions when the CSV file already exists."""
    from src.helpers.youtube_helper import get_subscriptions

    mock_youtube = mock_resource()
    csv_filename = tmp_path / "subs.csv"
    mock_isfile.return_value = True
    mock_df = pd.DataFrame({"channel_id": ["ch1"]})
    mock_read_csv.return_value = mock_df

    result_df = get_subscriptions(
        "my_channel_id", mock_youtube, csv_filename=str(csv_filename)
    )

    mock_isfile.assert_called_once_with(str(csv_filename))
    mock_read_csv.assert_called_once_with(str(csv_filename))
    mock_youtube.subscriptions.assert_not_called()
    pd.testing.assert_frame_equal(result_df, mock_df)


@patch("builtins.open", new_callable=mock_open)
@patch("src.helpers.youtube_helper.pd.DataFrame.to_csv")
@patch("src.helpers.youtube_helper.os.path.isfile")
@patch("googleapiclient.discovery.Resource")
def test_get_subscriptions_fetch_from_api(
    mock_resource,
    mock_isfile,
    mock_to_csv,
    mock_file_open,
    tmp_path,
):
    """Tests get_subscriptions fetching data from API and saving to CSV."""
    from src.helpers.youtube_helper import get_subscriptions

    mock_youtube = mock_resource()
    csv_filename = tmp_path / "subs.csv"
    gitignore_path = tmp_path / ".gitignore"
    channel_id_to_fetch = "fetch_my_subs"

    def isfile_side_effect(path):
        if path == str(csv_filename):
            return False
        elif path == str(gitignore_path):
            return True
        return False

    mock_isfile.side_effect = isfile_side_effect

    mock_subscriptions_list = mock_youtube.subscriptions.return_value.list
    mock_execute = mock_subscriptions_list.return_value.execute
    mock_execute.side_effect = [
        MOCK_YT_API_SUBSCRIPTIONS_PAGE1,
        MOCK_YT_API_SUBSCRIPTIONS_PAGE2,
    ]

    df = get_subscriptions(
        channel_id_to_fetch, mock_youtube, str(csv_filename), str(gitignore_path)
    )

    mock_isfile.assert_has_calls(
        [call(str(csv_filename)), call(str(gitignore_path))], any_order=False
    )

    assert mock_subscriptions_list.call_count == 2
    assert mock_execute.call_count == 2

    list_calls = mock_subscriptions_list.call_args_list
    assert len(list_calls) == 2

    assert list_calls[0] == call(
        part="snippet,contentDetails",
        channelId=channel_id_to_fetch,
        maxResults=50,
        pageToken=None,
    )
    assert list_calls[1] == call(
        part="snippet,contentDetails",
        channelId=channel_id_to_fetch,
        maxResults=50,
        pageToken="page2_token",
    )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3  # 2 from page 1, 1 from page 2
    assert df.iloc[0]["channel_id"] == "sub_ch_1"
    assert df.iloc[2]["channel_id"] == "sub_ch_3"

    mock_to_csv.assert_called_once_with(
        str(csv_filename), index=False, encoding="utf-8"
    )

    assert mock_file_open.call_count == 2

    open_calls = mock_file_open.call_args_list
    assert len(open_calls) == 2

    assert open_calls[0] == call(str(gitignore_path), "r", encoding="utf-8")
    assert open_calls[1] == call(str(gitignore_path), "a", encoding="utf-8")

    handle = mock_file_open()
    handle.write.assert_called_once_with(f"\n{str(csv_filename)}\n")


@patch("src.helpers.youtube_helper.get_video_data")
@patch("googleapiclient.discovery.Resource")
def test_get_recent_videos_from_subscriptions(mock_resource, mock_get_vid_data):
    """Tests getting recent videos by calling search API for each channel."""
    from src.helpers.youtube_helper import get_recent_videos_from_subscriptions

    mock_youtube_instance = mock_resource()
    mock_search_method = mock_youtube_instance.search()
    mock_search_list = mock_search_method.list
    mock_execute = mock_search_list.return_value.execute

    channel_ids = ["ch1", "ch2"]
    num_videos = 3

    def search_execute_side_effect(*args, **kwargs):
        list_call_args = mock_search_list.call_args
        channel_id_arg = list_call_args.kwargs.get("channelId")
        if channel_id_arg == "ch1":
            return MOCK_YT_API_SEARCH_RESULT_CH1
        elif channel_id_arg == "ch2":
            return MOCK_YT_API_SEARCH_RESULT_CH2
        else:
            return {"items": []}

    mock_execute.side_effect = search_execute_side_effect

    def get_video_data_side_effect(yt, response, mode=None):
        if response == MOCK_YT_API_SEARCH_RESULT_CH1:
            return MOCK_GET_VIDEO_DATA_RESULT_CH1
        elif response == MOCK_YT_API_SEARCH_RESULT_CH2:
            return MOCK_GET_VIDEO_DATA_RESULT_CH2
        else:
            return []

    mock_get_vid_data.side_effect = get_video_data_side_effect

    videos = get_recent_videos_from_subscriptions(
        mock_youtube_instance, channel_ids, num_videos
    )

    expected_search_calls = [
        call(
            part="id,snippet",
            channelId="ch1",
            maxResults=num_videos,
            order="date",
            type="video",
        ),
        call(
            part="id,snippet",
            channelId="ch2",
            maxResults=num_videos,
            order="date",
            type="video",
        ),
    ]

    assert mock_search_list.call_count == 2
    assert mock_execute.call_count == 2

    mock_get_vid_data.assert_has_calls(
        [
            call(mock_youtube_instance, MOCK_YT_API_SEARCH_RESULT_CH1),
            call(mock_youtube_instance, MOCK_YT_API_SEARCH_RESULT_CH2),
        ]
    )

    assert len(videos) == 2
    assert videos[0] == MOCK_GET_VIDEO_DATA_RESULT_CH1[0]
    assert videos[1] == MOCK_GET_VIDEO_DATA_RESULT_CH2[0]


@patch("src.helpers.youtube_helper.get_video_data")
@patch("googleapiclient.discovery.Resource")
def test_get_trending_videos(mock_resource, mock_get_vid_data):
    """Tests getting trending videos using the YouTube API."""
    from src.helpers.youtube_helper import get_trending_videos

    mock_youtube = mock_resource()
    region = "US"

    mock_videos_list = mock_youtube.videos.return_value.list
    mock_execute = mock_videos_list.return_value.execute
    mock_execute.return_value = MOCK_YT_API_TRENDING_RESULT
    mock_get_vid_data.return_value = MOCK_GET_VIDEO_DATA_RESULT_TRENDING

    videos = get_trending_videos(mock_youtube, region)

    mock_videos_list.assert_called_once_with(
        part="snippet,contentDetails",
        chart="mostPopular",
        regionCode=region,
        maxResults=50,
    )
    mock_execute.assert_called_once()
    mock_get_vid_data.assert_called_once_with(
        mock_youtube, MOCK_YT_API_TRENDING_RESULT, "trends"
    )
    assert videos == MOCK_GET_VIDEO_DATA_RESULT_TRENDING


@patch("src.helpers.youtube_helper.get_video_data_dlp")
@patch("concurrent.futures.as_completed")
@patch("concurrent.futures.ThreadPoolExecutor")
@patch("src.helpers.youtube_helper.yt_dlp.YoutubeDL")
def test_get_trending_videos_dlp(
    mock_yt_dlp_cls,
    mock_executor_cls,
    mock_as_completed,
    mock_get_vid_data_dlp,
):
    """Tests getting trending videos using yt-dlp, mocking concurrency properly."""
    from src.helpers.youtube_helper import get_trending_videos_dlp

    region = "GB"
    max_res = 3

    mock_ydl_instance = MagicMock()
    mock_yt_dlp_cls.return_value.__enter__.return_value = mock_ydl_instance

    mock_ydl_instance.extract_info.return_value = {
        "entries": [{"id": "trend_dlp_1"}, {"id": "trend_dlp_2"}, {"id": "trend_dlp_3"}]
    }

    MOCK_TREND_DLP_1 = {
        "video_id": "trend_dlp_1",
        "title": "DLP Trend 1",
        "upload_date": dt.datetime(2024, 4, 1),
    }
    MOCK_TREND_DLP_2 = {
        "video_id": "trend_dlp_2",
        "title": "DLP Trend 2",
        "upload_date": dt.datetime(2024, 4, 2),
    }
    MOCK_TREND_DLP_3 = {
        "video_id": "trend_dlp_3",
        "title": "DLP Trend 3",
        "upload_date": dt.datetime(2024, 4, 3),
    }

    def get_dlp_side_effect(vid):
        if vid == "trend_dlp_1":
            return MOCK_TREND_DLP_1
        if vid == "trend_dlp_2":
            return MOCK_TREND_DLP_2
        if vid == "trend_dlp_3":
            return MOCK_TREND_DLP_3
        return {}

    mock_get_vid_data_dlp.side_effect = get_dlp_side_effect

    mock_executor_instance = MagicMock()
    mock_executor_cls.return_value.__enter__.return_value = mock_executor_instance

    mock_future1 = MagicMock(spec=Future)
    mock_future1.result.return_value = MOCK_TREND_DLP_1
    mock_future2 = MagicMock(spec=Future)
    mock_future2.result.return_value = MOCK_TREND_DLP_2
    mock_future3 = MagicMock(spec=Future)
    mock_future3.result.return_value = MOCK_TREND_DLP_3

    future_map = {
        "trend_dlp_1": mock_future1,
        "trend_dlp_2": mock_future2,
        "trend_dlp_3": mock_future3,
    }

    def submit_side_effect(func, vid):
        if vid in future_map:
            return future_map[vid]
        raise ValueError(f"Unexpected video ID submitted: {vid}")

    mock_executor_instance.submit.side_effect = submit_side_effect

    mock_as_completed.return_value = [
        mock_future2,
        mock_future1,
        mock_future3,
    ]

    videos = get_trending_videos_dlp(region_code=region, max_results=max_res)

    mock_ydl_instance.extract_info.assert_called_once_with(
        f"https://www.youtube.com/feed/trending?gl={region}", download=False
    )

    from src.helpers.youtube_helper import get_video_data_dlp as real_get_video_data_dlp

    mock_executor_instance.submit.assert_has_calls(
        [
            call(real_get_video_data_dlp, "trend_dlp_1"),
            call(real_get_video_data_dlp, "trend_dlp_2"),
            call(real_get_video_data_dlp, "trend_dlp_3"),
        ],
        any_order=True,
    )
    assert mock_executor_instance.submit.call_count == 3

    mock_as_completed.assert_called_once()

    assert len(videos) == 3

    assert MOCK_TREND_DLP_1 in videos
    assert MOCK_TREND_DLP_2 in videos
    assert MOCK_TREND_DLP_3 in videos


@patch("src.helpers.youtube_helper.YouTubeTranscriptApi.get_transcript")
def test_get_transcript_success(mock_api_get_transcript):
    """Tests getting transcript successfully."""
    from src.helpers.youtube_helper import get_transcript

    mock_api_get_transcript.return_value = [
        {"text": "Hello world", "start": 0.5, "duration": 1.2},
        {"text": "this is a test", "start": 2.0, "duration": 1.8},
    ]
    transcript = get_transcript("v1", required_languages=["en"])
    assert transcript == "Hello world this is a test"
    mock_api_get_transcript.assert_called_once_with("v1", languages=["en"])


@patch("src.helpers.youtube_helper.YouTubeTranscriptApi.get_transcript")
def test_get_transcript_failure(mock_api_get_transcript):
    """Tests getting transcript when the API fails."""
    from src.helpers.youtube_helper import get_transcript

    mock_api_get_transcript.side_effect = Exception("API Error")
    transcript = get_transcript("v2")
    assert transcript == ""
    mock_api_get_transcript.assert_called_once_with("v2", languages=["de", "en"])


def test_parse_duration():
    """Tests parsing ISO 8601 duration strings."""
    from src.helpers.youtube_helper import parse_duration

    assert parse_duration("PT1M30S") == "01:30"
    assert parse_duration("PT5S") == "00:05"
    assert parse_duration("PT10M") == "10:00"
    assert parse_duration("PT1H5M10S") == "05:10"
    assert parse_duration("P1DT12H30M5S") == "30:05"
    assert parse_duration("PT") == "00:00"
    assert parse_duration("Invalid") == "00:00"


@patch("googleapiclient.discovery.Resource")
def test_get_video_length_api(MockResource):
    """Tests getting video length using the YouTube API."""
    from src.helpers.youtube_helper import get_video_length

    mock_youtube = MockResource()
    mock_videos_list = mock_youtube.videos.return_value.list
    mock_execute = mock_videos_list.return_value.execute
    mock_execute.return_value = {"items": [{"contentDetails": {"duration": "PT2M15S"}}]}

    length = get_video_length(mock_youtube, "v1")

    assert length == "02:15"
    mock_videos_list.assert_called_once_with(part="snippet,contentDetails", id="v1")
    mock_execute.assert_called_once()


@patch("googleapiclient.discovery.Resource")
def test_get_video_length_api_not_found(MockResource):
    """Tests getting video length via API when video not found."""
    from src.helpers.youtube_helper import get_video_length

    mock_youtube = MockResource()
    mock_execute = mock_youtube.videos.return_value.list.return_value.execute
    mock_execute.return_value = {"items": []}

    length = get_video_length(mock_youtube, "v_nonexistent")
    assert length == "00:00"


@patch("yt_dlp.YoutubeDL")
def test_get_video_length_dlp(mock_yt_dlp_cls):
    """Tests getting video length using yt-dlp."""
    from src.helpers.youtube_helper import get_video_length_dlp

    mock_ydl_instance = MagicMock()
    mock_yt_dlp_cls.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.return_value = {"duration": 135}

    length = get_video_length_dlp("v1")

    assert length == "02:15"
    mock_ydl_instance.extract_info.assert_called_once_with(
        f"https://www.youtube.com/watch?v=v1", download=False
    )


@patch("yt_dlp.YoutubeDL")
def test_get_video_length_dlp_failure(mock_yt_dlp_cls):
    """Tests getting video length via yt-dlp on failure."""
    from src.helpers.youtube_helper import get_video_length_dlp

    mock_ydl_instance = MagicMock()
    mock_yt_dlp_cls.return_value.__enter__.return_value = mock_ydl_instance

    mock_ydl_instance.extract_info.return_value = {}
    assert get_video_length_dlp("v_nodur") == "00:00"

    mock_ydl_instance.extract_info.side_effect = Exception("yt-dlp error")
    assert get_video_length_dlp("v_error") == "00:00"


@patch("yt_dlp.YoutubeDL")
def test_get_video_data_dlp(mock_yt_dlp_cls):
    """Tests getting full video metadata using yt-dlp."""
    from src.helpers.youtube_helper import get_video_data_dlp

    mock_ydl_instance = MagicMock()
    mock_yt_dlp_cls.return_value.__enter__.return_value = mock_ydl_instance
    mock_info = {
        "title": "Test Title",
        "tags": ["tag1", "tag2"],
        "thumbnail": "thumb_url",
        "duration": 95,
        "upload_date": "20230115",
        "uploader": "Test Uploader",
        "view_count": 12345,
    }
    mock_ydl_instance.extract_info.return_value = mock_info

    video_data = get_video_data_dlp("v1")

    expected_data = {
        "video_id": "v1",
        "title": "Test Title",
        "tags": "tag1, tag2",
        "thumbnail": "thumb_url",
        "length": "01:35",
        "upload_date": dt.datetime(2023, 1, 15),
        "channel_name": "Test Uploader",
        "views": 12345,
    }
    assert video_data == expected_data


@patch("src.helpers.youtube_helper.get_video_length", return_value="05:10")
@patch("googleapiclient.discovery.Resource")
def test_get_video_data_api(MockResource, mock_get_len):
    """Tests getting video data from API response (e.g., search results)."""
    from src.helpers.youtube_helper import get_video_data

    mock_youtube = MockResource()

    mock_stats_execute = mock_youtube.videos.return_value.list.return_value.execute
    mock_stats_execute.return_value = {
        "items": [{"statistics": {"viewCount": "12345"}}]
    }

    api_response = {
        "items": [
            {
                "id": {"videoId": "vid1"},
                "snippet": {
                    "title": "Title 1",
                    "channelTitle": "Channel 1",
                    "tags": ["api", "test"],
                    "thumbnails": {"medium": {"url": "thumb1_url"}},
                    "publishedAt": "2023-10-26T10:00:00Z",
                },
            },
            {
                "id": {"videoId": "vid2"},
                "snippet": {
                    "title": "Title 2",
                    "channelTitle": "Channel 2",
                    # "tags": [], # Missing tags key
                    "thumbnails": {"medium": {"url": "thumb2_url"}},
                    "publishedAt": "2023-10-27T11:00:00Z",
                },
            },
        ]
    }

    videos = get_video_data(mock_youtube, api_response)

    assert len(videos) == 2

    assert videos[0]["video_id"] == "vid2"
    assert videos[0]["title"] == "Title 2"
    assert videos[0]["channel_name"] == "Channel 2"
    assert videos[0]["tags"] == "Keine Tags"
    assert videos[0]["thumbnail"] == "thumb2_url"
    assert videos[0]["length"] == "05:10"
    assert videos[0]["views"] == "12345"
    assert videos[0]["upload_date"] == "2023-10-27T11:00:00Z"

    assert videos[1]["video_id"] == "vid1"
    assert videos[1]["title"] == "Title 1"
    assert videos[1]["channel_name"] == "Channel 1"
    assert videos[1]["tags"] == "api, test"
    assert videos[1]["thumbnail"] == "thumb1_url"
    assert videos[1]["length"] == "05:10"
    assert videos[1]["views"] == "12345"
    assert videos[1]["upload_date"] == "2023-10-26T10:00:00Z"

    mock_get_len.assert_has_calls(
        [call(mock_youtube, "vid1"), call(mock_youtube, "vid2")]
    )
    mock_stats_execute.assert_has_calls([call(), call()])


def test_extract_video_id_from_url():
    """Tests extracting video IDs from various URL formats."""
    from src.helpers.youtube_helper import extract_video_id_from_url

    urls = {
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=abcdefghijk": "abcdefghijk",
        "https://youtu.be/1234567890_": "1234567890_",
        "https://www.youtube.com/embed/xyz-abc_123": "xyz-abc_123",
        "Not a url": None,
        "https://www.youtube.com/watch?v=": None,
        "https://youtube.com/watch?list=PL...&v=okOkOkOkOk0": "okOkOkOkOk0",
    }
    for url, expected_id in urls.items():
        assert extract_video_id_from_url(url) == expected_id


@patch("src.helpers.youtube_helper.build")
def test_create_youtube_client(mock_build):
    """Tests the creation of the YouTube API client."""
    from src.helpers.youtube_helper import create_youtube_client

    api_key = "fake_yt_key"
    client = create_youtube_client(api_key)
    mock_build.assert_called_once_with("youtube", "v3", developerKey=api_key)
    assert client == mock_build.return_value
