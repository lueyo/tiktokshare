import os
import re
import requests
from fastapi import HTTPException

class InstagramService:
    SAVEGRAM_API_URL = "https://savegram.app/api/ajaxSearch"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://savegram.app",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Referer": "https://savegram.app/es",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0",
        "TE": "trailers",
    }

    @classmethod
    def download_video_with_requests(cls, instagram_url: str, save_path: str) -> str:
        """
        Downloads Instagram video using the savegram.app API as a fallback method.
        Returns the path to the saved video file.
        Raises HTTPException on failure.
        """
        # Prepare form data for POST request
        data = {
            "k_exp": "1750806645",
            "k_token": "5a8c8b9e362e34d00abce4f46035d891dab65f2cc5396a4fd53680587530351e",
            "q": instagram_url,
            "t": "media",
            "lang": "es",
            "v": "v2",
        }

        try:
            response = requests.post(cls.SAVEGRAM_API_URL, headers=cls.HEADERS, data=data)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error contacting savegram API: {str(e)}")

        json_resp = response.json()
        if json_resp.get("status") != "ok" or "data" not in json_resp:
            raise HTTPException(status_code=500, detail="Invalid response from savegram API")

        # Extract the download URL from the HTML in json_resp["data"]
        html_data = json_resp["data"]
        # The download URL is in an <a href="..."> tag with class "abutton is-success"
        # Use regex to extract the href link for the video download
        match = re.search(r'<a href="([^"]+)"[^>]*class="abutton is-success[^"]*"[^>]*title="Descargar video"', html_data)
        if not match:
            raise HTTPException(status_code=500, detail="Download URL not found in savegram response")

        download_url = match.group(1)

        # Download the video content
        try:
            video_response = requests.get(download_url, headers={"User-Agent": cls.HEADERS["User-Agent"]}, stream=True)
            video_response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error downloading video from savegram URL: {str(e)}")

        # Save the video content to save_path
        try:
            with open(save_path, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving video file: {str(e)}")

        return save_path
