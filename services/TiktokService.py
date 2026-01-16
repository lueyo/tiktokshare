import os
import re
import requests
from fastapi import HTTPException


class TiktokService:
    SAVETIK_API_URL = "https://savetik.net/api/action"
    # Alternative TikTok download APIs
    SNAPTT_API_URL = "https://snaptik.app/api.php"
    TTDOWN_API_URL = "https://ttdownloader.com/api.php"

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
        Raises HTTPException on failure.
        """
        # Prepare form data - note the URL is repeated twice in the params
        params = {
            "url": tiktok_url,
        }

        try:
            response = requests.get(
                cls.SAVETIK_API_URL, headers=cls.HEADERS, params=params
            )
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error contacting savetik API: {str(e)}"
            )

        try:
            json_resp = response.json()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Invalid response from savetik API: {str(e)}"
            )

        # Check for status_code in response
        if json_resp.get("status_code") != 0:
            error_detail = json_resp.get("postinfo", {}).get(
                "media_title", "Unknown error"
            )
            raise HTTPException(
                status_code=500, detail=f"savetik API error: {error_detail}"
            )

        # Extract download URL - prefer hdDownloadUrl, fall back to downloadUrl
        download_url = json_resp.get("hdDownloadUrl") or json_resp.get("downloadUrl")
        if not download_url:
            raise HTTPException(
                status_code=500, detail="No download URL found in savetik response"
            )

        # Download the video
        try:
            video_response = requests.get(
                download_url,
                headers={"User-Agent": cls.HEADERS["User-Agent"]},
                stream=True,
            )
            video_response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error downloading video from savetik URL: {str(e)}",
            )

        # Save the video content to save_path
        try:
            with open(save_path, "wb") as f:
                total_size = 0
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        total_size += len(chunk)
                        f.write(chunk)
            print(f"Downloaded video size: {total_size} bytes")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error saving video file: {str(e)}"
            )

        # Verify file size is valid (at least 10KB for a video)
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            if file_size < 10240:  # Less than 10KB is likely incomplete
                os.remove(save_path)
                raise HTTPException(
                    status_code=500,
                    detail=f"Downloaded file too small ({file_size} bytes), likely incomplete",
                )

        return save_path

    @classmethod
    def download_video_with_alternative_api(
        cls, tiktok_url: str, save_path: str
    ) -> str:
        """
        Downloads TikTok video using alternative APIs as fallback.
        Tries multiple APIs until one succeeds.
        Returns the path to the saved video file.
        Raises HTTPException on failure.
        """
        # Try snapTik API first
        try:
            return cls._download_via_snaptik(tiktok_url, save_path)
        except Exception as snap_e:
            print(f"snapTik API failed: {snap_e}")

        # Try ttdownloader API as second alternative
        try:
            return cls._download_via_ttdownloader(tiktok_url, save_path)
        except Exception as ttd_e:
            print(f"ttdownloader API failed: {ttd_e}")

        raise HTTPException(
            status_code=500, detail="All alternative TikTok download APIs failed"
        )

    @classmethod
    def _download_via_snaptik(cls, tiktok_url: str, save_path: str) -> str:
        """
        Download video using snapTik.app API.
        """
        try:
            response = requests.post(
                cls.SNAPTT_API_URL,
                data={"url": tiktok_url},
                headers=cls.SNAPTt_HEADERS,
                timeout=30,
            )
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error contacting snapTik API: {str(e)}"
            )

        # Parse response - snapTik returns JSON or direct video URL
        try:
            json_resp = response.json()
        except Exception:
            # Try to parse as text (might return direct URL)
            text_resp = response.text
            # Check if it's a direct video URL
            if text_resp.startswith("http") and (
                "tiktok" in text_resp or ".mp4" in text_resp
            ):
                download_url = text_resp.strip()
            else:
                raise HTTPException(
                    status_code=500, detail=f"Invalid response from snapTik API"
                )
        else:
            # Handle different snapTik response formats
            download_url = (
                json_resp.get("video")
                or json_resp.get("url")
                or json_resp.get("download_url")
            )
            if not download_url and json_resp.get("status") == "success":
                # Try nested structure
                data = json_resp.get("data", [{}])[0] if json_resp.get("data") else {}
                download_url = data.get("video") or data.get("url")

        if not download_url:
            raise HTTPException(
                status_code=500, detail="No download URL found in snapTik response"
            )

        return cls._download_video_file(download_url, save_path)

    @classmethod
    def _download_via_ttdownloader(cls, tiktok_url: str, save_path: str) -> str:
        """
        Download video using ttdownloader.com API.
        """
        try:
            response = requests.post(
                cls.TTDOWN_API_URL,
                data={"url": tiktok_url},
                headers=cls.SNAPTt_HEADERS,
                timeout=30,
            )
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error contacting ttdownloader API: {str(e)}"
            )

        # Parse response
        try:
            json_resp = response.json()
        except Exception:
            raise HTTPException(
                status_code=500, detail=f"Invalid response from ttdownloader API"
            )

        # Handle different response formats
        download_url = (
            json_resp.get("download_url")
            or json_resp.get("video")
            or json_resp.get("url")
        )

        if not download_url:
            raise HTTPException(
                status_code=500, detail="No download URL found in ttdownloader response"
            )

        return cls._download_video_file(download_url, save_path)

    @classmethod
    def _download_video_file(cls, download_url: str, save_path: str) -> str:
        """
        Helper method to download video from a URL and save to file.
        """
        try:
            video_response = requests.get(
                download_url,
                headers={"User-Agent": cls.HEADERS["User-Agent"]},
                stream=True,
                timeout=120,  # Longer timeout for videos
            )
            video_response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error downloading video from URL: {str(e)}",
            )

        try:
            with open(save_path, "wb") as f:
                total_size = 0
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        total_size += len(chunk)
                        f.write(chunk)
            print(f"Downloaded video size: {total_size} bytes")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error saving video file: {str(e)}"
            )

        # Verify file size is valid (at least 10KB for a video)
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            if file_size < 10240:  # Less than 10KB is likely incomplete
                os.remove(save_path)
                raise HTTPException(
                    status_code=500,
                    detail=f"Downloaded file too small ({file_size} bytes), likely incomplete",
                )

        return save_path
