import os
import re
import requests


class VideoNotFoundError(Exception):
    """Excepción cuando el video no existe o no se puede encontrar"""

    pass


class DownloadError(Exception):
    """Excepción cuando falla la descarga del video"""

    pass


class XService:
    FX_TWITTER_URL = "https://fxtwitter.com/i/status/{x_id}"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    @classmethod
    def get_video_url(cls, x_id: str) -> str:
        """
        Gets the direct video URL from an X (Twitter) post ID.
        Returns the direct video URL without downloading.
        Raises VideoNotFoundError or DownloadError on failure.
        """
        url = cls.FX_TWITTER_URL.format(x_id=x_id)
        print(f"[GET_URL] Request URL: {url}")

        try:
            response = requests.get(url, headers=cls.HEADERS, timeout=30)
            print(f"[GET_URL] Response status code: {response.status_code}")
            response.raise_for_status()
        except Exception as e:
            print(f"[GET_URL] Error contacting fxtwitter.com: {e}")
            raise DownloadError(f"Error contacting fxtwitter.com: {e}")

        html_content = response.text
        print(f"[GET_URL] HTML content length: {len(html_content)} characters")

        download_url = None

        twitter_stream_match = re.search(
            r'<meta\s+property="twitter:player:stream"\s+content="([^"]+)"',
            html_content,
        )
        if twitter_stream_match:
            download_url = twitter_stream_match.group(1)
            print(f"[GET_URL] Found video URL in twitter:player:stream")

        if not download_url:
            og_video_match = re.search(
                r'<meta\s+property="og:video"\s+content="([^"]+)"', html_content
            )
            if og_video_match:
                download_url = og_video_match.group(1)
                print(f"[GET_URL] Found video URL in og:video")

        if not download_url:
            og_video_secure_match = re.search(
                r'<meta\s+property="og:video:secure_url"\s+content="([^"]+)"',
                html_content,
            )
            if og_video_secure_match:
                download_url = og_video_secure_match.group(1)
                print(f"[GET_URL] Found video URL in og:video:secure_url")

        if not download_url:
            print("[GET_URL] No video URL found in meta tags")
            raise VideoNotFoundError("Video not found in fxtwitter.com response")

        print(f"[GET_URL] Download URL: {download_url}")
        return download_url

    @classmethod
    def download_video_with_fxtwitter(cls, x_id: str, save_path: str) -> str:
        """
        Downloads X (Twitter) video using fxtwitter.com as fallback.
        Makes a request to https://fxtwitter.com/i/status/{id} and extracts
        the video URL from meta tags in this priority:
        1. twitter:player:stream
        2. og:video
        3. og:video:secure_url

        Returns the path to the saved video file.
        Raises VideoNotFoundError or DownloadError on failure.
        """
        url = cls.FX_TWITTER_URL.format(x_id=x_id)
        print(f"[FXTWITTER] Request URL: {url}")

        try:
            response = requests.get(url, headers=cls.HEADERS, timeout=30)
            print(f"[FXTWITTER] Response status code: {response.status_code}")
            response.raise_for_status()
        except Exception as e:
            print(f"[FXTWITTER] Error contacting fxtwitter.com: {e}")
            raise DownloadError(f"Error contacting fxtwitter.com: {e}")

        html_content = response.text
        print(f"[FXTWITTER] HTML content length: {len(html_content)} characters")

        download_url = None

        # Priority 1: twitter:player:stream
        twitter_stream_match = re.search(
            r'<meta\s+property="twitter:player:stream"\s+content="([^"]+)"',
            html_content,
        )
        if twitter_stream_match:
            download_url = twitter_stream_match.group(1)
            print(f"[FXTWITTER] Found video URL in twitter:player:stream")

        # Priority 2: og:video
        if not download_url:
            og_video_match = re.search(
                r'<meta\s+property="og:video"\s+content="([^"]+)"', html_content
            )
            if og_video_match:
                download_url = og_video_match.group(1)
                print(f"[FXTWITTER] Found video URL in og:video")

        # Priority 3: og:video:secure_url
        if not download_url:
            og_video_secure_match = re.search(
                r'<meta\s+property="og:video:secure_url"\s+content="([^"]+)"',
                html_content,
            )
            if og_video_secure_match:
                download_url = og_video_secure_match.group(1)
                print(f"[FXTWITTER] Found video URL in og:video:secure_url")

        if not download_url:
            print("[FXTWITTER] No video URL found in meta tags")
            raise VideoNotFoundError("Video not found in fxtwitter.com response")

        print(f"[FXTWITTER] Download URL: {download_url}")

        # Download the video
        try:
            video_response = requests.get(
                download_url,
                headers={"User-Agent": cls.HEADERS["User-Agent"]},
                stream=True,
                timeout=120,
            )
            print(f"[FXTWITTER] Video response status: {video_response.status_code}")
            video_response.raise_for_status()
        except Exception as e:
            print(f"[FXTWITTER] Error downloading video: {e}")
            raise DownloadError("Error downloading video")

        # Save the video
        try:
            with open(save_path, "wb") as f:
                total_size = 0
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        total_size += len(chunk)
                        f.write(chunk)
            print(f"[FXTWITTER] Downloaded video size: {total_size} bytes")
        except Exception as e:
            print(f"[FXTWITTER] Error saving video file: {e}")
            raise DownloadError("Error saving video file")

        # Verify file size is valid (at least 10KB for a video)
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            print(f"[FXTWITTER] File size verification: {file_size} bytes")
            if file_size < 10240:  # Less than 10KB is likely incomplete
                os.remove(save_path)
                print(f"[FXTWITTER] File too small ({file_size} bytes), removed")
                raise DownloadError("Downloaded file is incomplete")

        return save_path
