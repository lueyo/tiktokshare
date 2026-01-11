import os
import re
import requests
from fastapi import HTTPException


class TiktokService:
    SAVETIK_API_URL = "https://savetik.net/api/action"
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
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error saving video file: {str(e)}"
            )

        return save_path
