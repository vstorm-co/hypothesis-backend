from logging import getLogger
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi

from src.config import settings

logger = getLogger(__name__)


class YouTubeService:
    def get_youtube_link(self, url: str):
        """Return the YouTube link from the given video ID."""
        video_id = self.get_video_id(url)
        if not video_id:
            return None

        return f"https://www.youtube.com/watch?v={video_id}"

    @staticmethod
    def get_video_id(url: str):
        """Return the YouTube video ID from the given URL, or None."""
        parsed = urlparse(url)
        path_parts = parsed.path.split("/")

        # youtu.be/VIDEO_ID
        if parsed.netloc == "youtu.be" and len(path_parts) >= 2 and not path_parts[0]:
            return path_parts[1]

        if parsed.netloc not in ["www.youtube.com", "youtube.com", "m.youtube.com"]:
            return None

        query_params = parse_qs(parsed.query)

        # https://youtube.com?v=VIDEO_ID, youtube.com/watch?v=VIDEO_ID, etc.
        if "v" in query_params:
            return query_params["v"][0]

        path_parts = parsed.path.split("/")

        # https://yotube.com/v/VIDEO_ID, /embed/VIDEO_ID, etc.
        if (
            len(path_parts) >= 3
            and not path_parts[0]
            and path_parts[1] in ["v", "embed", "shorts", "live"]
        ):
            return path_parts[2]

        return None

    def get_video_transcription(self, url: str) -> str:
        """Return the transcription of the video."""
        video_id = self.get_video_id(url)

        # Proxy configuration
        proxies = {
            "http": f"http://{settings.YOUTUBE_PROXY_URL}",
            "https": f"https://{settings.YOUTUBE_PROXY_URL}",
        }

        try:
            transcription_data = YouTubeTranscriptApi.get_transcript(
                video_id, proxies=proxies
            )
        except Exception as e:
            logger.error(f"Failed to get transcription for video: {video_id}")
            logger.error(f"Error: {e}")
            return ""

        if not transcription_data:
            return ""

        return " ".join([item.get("text") for item in transcription_data])
