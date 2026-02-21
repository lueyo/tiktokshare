import os
import re
import logging
import requests
from fastapi import HTTPException

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VideoNotFoundError(Exception):
    """Excepción cuando el video no existe o no se puede encontrar"""

    pass


class DownloadError(Exception):
    """Excepción cuando falla la descarga del video"""

    pass


class TiktokService:
    SAVETIK_API_URL = "https://savetik.net/api/action"
    SNAPTT_API_URL = "https://snaptik.app/api.php"
    TTDOWN_API_URL = "https://ttdownloader.com/api.php"
    TNKTOK_URL = "https://vt.tnktok.com"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://savetik.net",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Referer": "https://savetik.net/es",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0",
        "TE": "trailers",
    }

    # Alternative headers for snapTik API
    SNAPTt_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    @classmethod
    def download_video_with_requests(cls, tiktok_url: str, save_path: str) -> str:
        """
        Downloads TikTok video using the savetik.net API as a fallback method.
        Returns the path to the saved video file.
        Raises VideoNotFoundError or DownloadError on failure.
        """
        logger.info(f"[SAVETIK] Starting download for URL: {tiktok_url}")

        # Prepare form data - note the URL is repeated twice in the params
        params = {
            "url": tiktok_url,
        }

        logger.debug(f"[SAVETIK] Request URL: {cls.SAVETIK_API_URL}")
        logger.debug(f"[SAVETIK] Request params: {params}")
        logger.debug(f"[SAVETIK] Request headers: {cls.HEADERS}")

        try:
            response = requests.get(
                cls.SAVETIK_API_URL, headers=cls.HEADERS, params=params
            )
            logger.info(f"[SAVETIK] Response status code: {response.status_code}")
            logger.debug(f"[SAVETIK] Response headers: {dict(response.headers)}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"[SAVETIK] Error contacting savetik API: {str(e)}")
            raise DownloadError("Error contacting TikTok API")

        try:
            json_resp = response.json()
            logger.info(f"[SAVETIK] JSON response: {json_resp}")
        except Exception as e:
            logger.error(f"[SAVETIK] Invalid response from savetik API: {str(e)}")
            logger.error(f"[SAVETIK] Raw response text: {response.text}")
            raise DownloadError("Invalid response from TikTok API")

        # Check for status_code in response
        status_code = json_resp.get("status_code")
        logger.info(f"[SAVETIK] Response status_code: {status_code}")
        if status_code != 0:
            error_detail = json_resp.get("postinfo", {}).get(
                "media_title", "Unknown error"
            )
            logger.error(f"[SAVETIK] API error: {error_detail}")
            raise VideoNotFoundError("Video not found")

        # Extract download URL - prefer hdDownloadUrl, fall back to downloadUrl
        download_url = json_resp.get("hdDownloadUrl") or json_resp.get("downloadUrl")
        logger.info(f"[SAVETIK] Extracted download_url: {download_url}")
        if not download_url:
            logger.error("[SAVETIK] No download URL found in response")
            raise DownloadError("No download URL available")

        # Download the video
        logger.info(f"[SAVETIK] Starting video download from: {download_url}")
        try:
            video_response = requests.get(
                download_url,
                headers={"User-Agent": cls.HEADERS["User-Agent"]},
                stream=True,
            )
            logger.info(
                f"[SAVETIK] Video response status: {video_response.status_code}"
            )
            video_response.raise_for_status()
        except Exception as e:
            logger.error(f"[SAVETIK] Error downloading video: {str(e)}")
            raise DownloadError("Error downloading video")

        # Save the video content to save_path
        try:
            with open(save_path, "wb") as f:
                total_size = 0
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        total_size += len(chunk)
                        f.write(chunk)
            logger.info(f"[SAVETIK] Downloaded video size: {total_size} bytes")
        except Exception as e:
            logger.error(f"[SAVETIK] Error saving video file: {str(e)}")
            raise DownloadError("Error saving video file")

        # Verify file size is valid (at least 10KB for a video)
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            logger.info(f"[SAVETIK] File size verification: {file_size} bytes")
            if file_size < 10240:  # Less than 10KB is likely incomplete
                os.remove(save_path)
                logger.error(f"[SAVETIK] File too small ({file_size} bytes), removed")
                raise DownloadError("Downloaded file is incomplete")

        return save_path

    @classmethod
    def get_video_url(cls, tiktok_url: str) -> str:
        """
        Gets the direct video URL from a TikTok URL.
        Returns the direct video URL without downloading.
        Raises VideoNotFoundError or DownloadError on failure.
        """
        logger.info(f"[GET_URL] Getting video URL for: {tiktok_url}")

        video_id = None
        url_match = re.search(r"tiktok\.com/(?:@[^/]+/)?(?:video|l)/(\d+)", tiktok_url)
        if url_match:
            video_id = url_match.group(1)
            logger.info(f"[GET_URL] Extracted video_id: {video_id}")
        else:
            raise DownloadError("Could not extract video ID from URL")

        tnktok_url = f"{cls.TNKTOK_URL}/{video_id}"
        logger.info(f"[GET_URL] Request URL: {tnktok_url}")

        try:
            response = requests.get(
                tnktok_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
                },
                timeout=30,
            )
            logger.info(f"[GET_URL] Response status code: {response.status_code}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"[GET_URL] Error contacting vt.tnktok.com: {str(e)}")
            raise DownloadError("Error contacting vt.tnktok.com")

        html_content = response.text

        og_video_match = re.search(
            r'<meta\s+property="og:video"\s+content="([^"]+)"', html_content
        )
        if not og_video_match:
            logger.error("[GET_URL] Could not find og:video metatag in HTML")
            raise VideoNotFoundError("Video not found")

        download_url = og_video_match.group(1)
        logger.info(f"[GET_URL] Extracted video URL: {download_url}")

        if not download_url:
            logger.error("[GET_URL] No download URL found in metatag")
            raise DownloadError("No download URL available")

        return download_url

    @classmethod
    def download_video_with_tnktok(cls, tiktok_url: str, save_path: str) -> str:
        """
        Downloads TikTok video using vt.tnktok.com as first fallback.
        Returns the path to the saved video file.
        Raises VideoNotFoundError or DownloadError on failure.
        """
        logger.info(f"[TNKTOK] Starting download for URL: {tiktok_url}")

        video_id = None
        url_match = re.search(r"tiktok\.com/(?:@[^/]+/)?(?:video|l)/(\d+)", tiktok_url)
        if url_match:
            video_id = url_match.group(1)
            logger.info(f"[TNKTOK] Extracted video_id: {video_id}")
        else:
            raise DownloadError("Could not extract video ID from URL")

        tnktok_url = f"{cls.TNKTOK_URL}/{video_id}"
        logger.info(f"[TNKTOK] Request URL: {tnktok_url}")

        try:
            response = requests.get(
                tnktok_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
                },
                timeout=30,
            )
            logger.info(f"[TNKTOK] Response status code: {response.status_code}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"[TNKTOK] Error contacting vt.tnktok.com: {str(e)}")
            raise DownloadError("Error contacting vt.tnktok.com")

        html_content = response.text
        logger.debug(f"[TNKTOK] HTML content length: {len(html_content)} characters")

        og_video_match = re.search(
            r'<meta\s+property="og:video"\s+content="([^"]+)"', html_content
        )
        if not og_video_match:
            logger.error("[TNKTOK] Could not find og:video metatag in HTML")
            raise VideoNotFoundError("Video not found")

        download_url = og_video_match.group(1)
        logger.info(f"[TNKTOK] Extracted video URL: {download_url}")

        if not download_url:
            logger.error("[TNKTOK] No download URL found in metatag")
            raise DownloadError("No download URL available")

        return cls._download_video_file(download_url, save_path)

    @classmethod
    def download_video_with_alternative_api(
        cls, tiktok_url: str, save_path: str
    ) -> str:
        """
        Downloads TikTok video using alternative APIs as fallback.
        Tries multiple APIs until one succeeds.
        Returns the path to the saved video file.
        Raises VideoNotFoundError or DownloadError on failure.
        """
        logger.info(f"[ALT] Starting alternative API download for URL: {tiktok_url}")

        # Try snapTik API first
        try:
            return cls._download_via_snaptik(tiktok_url, save_path)
        except Exception as snap_e:
            logger.error(f"[ALT] snapTik API failed: {snap_e}")

        # Try ttdownloader API as second alternative
        try:
            return cls._download_via_ttdownloader(tiktok_url, save_path)
        except Exception as ttd_e:
            logger.error(f"[ALT] ttdownloader API failed: {ttd_e}")

        raise DownloadError("All TikTok download methods failed")

    @classmethod
    def _download_via_snaptik(cls, tiktok_url: str, save_path: str) -> str:
        """
        Download video using snapTik.app API.
        """
        logger.info(f"[SNAPTIK] Starting download for URL: {tiktok_url}")

        logger.debug(f"[SNAPTIK] Request URL: {cls.SNAPTT_API_URL}")
        logger.debug(f"[SNAPTIK] Request data: {{'url': {tiktok_url}}}")
        logger.debug(f"[SNAPTIK] Request headers: {cls.SNAPTt_HEADERS}")

        try:
            response = requests.post(
                cls.SNAPTT_API_URL,
                data={"url": tiktok_url},
                headers=cls.SNAPTt_HEADERS,
                timeout=30,
            )
            logger.info(f"[SNAPTIK] Response status code: {response.status_code}")
            logger.debug(f"[SNAPTIK] Response headers: {dict(response.headers)}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"[SNAPTIK] Error contacting snapTik API: {str(e)}")
            raise DownloadError("Error contacting TikTok API")

        # Parse response - snapTik returns JSON or direct video URL
        logger.debug(f"[SNAPTIK] Raw response text: {response.text}")
        try:
            json_resp = response.json()
            logger.info(f"[SNAPTIK] JSON response: {json_resp}")
        except Exception:
            # Try to parse as text (might return direct URL)
            text_resp = response.text
            logger.info(f"[SNAPTIK] Response is text: {text_resp[:200]}...")
            # Check if it's a direct video URL
            if text_resp.startswith("http") and (
                "tiktok" in text_resp or ".mp4" in text_resp
            ):
                download_url = text_resp.strip()
                logger.info(f"[SNAPTIK] Direct video URL found: {download_url}")
            else:
                logger.error("[SNAPTIK] Invalid response format from snapTik API")
                raise DownloadError("Invalid response from TikTok API")
        else:
            # Handle different snapTik response formats
            download_url = (
                json_resp.get("video")
                or json_resp.get("url")
                or json_resp.get("download_url")
            )
            logger.info(f"[SNAPTIK] Extracted download_url from JSON: {download_url}")
            if not download_url and json_resp.get("status") == "success":
                # Try nested structure
                data = json_resp.get("data", [{}])[0] if json_resp.get("data") else {}
                download_url = data.get("video") or data.get("url")
                logger.info(f"[SNAPTIK] Extracted from nested data: {download_url}")

        if not download_url:
            logger.error("[SNAPTIK] No download URL found in response")
            raise VideoNotFoundError("Video not found")

        return cls._download_video_file(download_url, save_path)

    @classmethod
    def _download_via_ttdownloader(cls, tiktok_url: str, save_path: str) -> str:
        """
        Download video using ttdownloader.com API.
        """
        logger.info(f"[TTDOWNLOADER] Starting download for URL: {tiktok_url}")

        logger.debug(f"[TTDOWNLOADER] Request URL: {cls.TTDOWN_API_URL}")
        logger.debug(f"[TTDOWNLOADER] Request data: {{'url': {tiktok_url}}}")
        logger.debug(f"[TTDOWNLOADER] Request headers: {cls.SNAPTt_HEADERS}")

        try:
            response = requests.post(
                cls.TTDOWN_API_URL,
                data={"url": tiktok_url},
                headers=cls.SNAPTt_HEADERS,
                timeout=30,
            )
            logger.info(f"[TTDOWNLOADER] Response status code: {response.status_code}")
            logger.debug(f"[TTDOWNLOADER] Response headers: {dict(response.headers)}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"[TTDOWNLOADER] Error contacting ttdownloader API: {str(e)}")
            raise DownloadError("Error contacting TikTok API")

        # Parse response
        try:
            json_resp = response.json()
            logger.info(f"[TTDOWNLOADER] JSON response: {json_resp}")
        except Exception:
            logger.error(f"[TTDOWNLOADER] Invalid response from ttdownloader API")
            logger.error(f"[TTDOWNLOADER] Raw response text: {response.text}")
            raise DownloadError("Invalid response from TikTok API")

        # Handle different response formats
        download_url = (
            json_resp.get("download_url")
            or json_resp.get("video")
            or json_resp.get("url")
        )
        logger.info(f"[TTDOWNLOADER] Extracted download_url: {download_url}")

        if not download_url:
            logger.error("[TTDOWNLOADER] No download URL found in response")
            raise VideoNotFoundError("Video not found")

        return cls._download_video_file(download_url, save_path)

    @classmethod
    def _download_video_file(cls, download_url: str, save_path: str) -> str:
        """
        Helper method to download video from a URL and save to file.
        """
        logger.info(f"[VIDEO] Starting video download from: {download_url}")
        logger.debug(f"[VIDEO] Save path: {save_path}")

        try:
            video_response = requests.get(
                download_url,
                headers={"User-Agent": cls.HEADERS["User-Agent"]},
                stream=True,
                timeout=120,  # Longer timeout for videos
            )
            logger.info(f"[VIDEO] Response status code: {video_response.status_code}")
            logger.debug(f"[VIDEO] Response headers: {dict(video_response.headers)}")
            video_response.raise_for_status()
        except Exception as e:
            logger.error(f"[VIDEO] Error downloading video from URL: {str(e)}")
            raise DownloadError("Error downloading video")

        try:
            with open(save_path, "wb") as f:
                total_size = 0
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        total_size += len(chunk)
                        f.write(chunk)
            logger.info(f"[VIDEO] Downloaded video size: {total_size} bytes")
        except Exception as e:
            logger.error(f"[VIDEO] Error saving video file: {str(e)}")
            raise DownloadError("Error saving video file")

        # Verify file size is valid (at least 10KB for a video)
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            logger.info(f"[VIDEO] File size verification: {file_size} bytes")
            if file_size < 10240:  # Less than 10KB is likely incomplete
                os.remove(save_path)
                logger.error(f"[VIDEO] File too small ({file_size} bytes), removed")
                raise DownloadError("Downloaded file is incomplete")

        return save_path
