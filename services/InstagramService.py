import os
import re
import requests
from fastapi import HTTPException


class VideoNotFoundError(Exception):
    """Excepción cuando el video no existe o no se puede encontrar"""

    pass


class DownloadError(Exception):
    """Excepción cuando falla la descarga del video"""

    pass


class InstagramService:
    SAVEGRAM_API_URL = "https://savegram.app/api/ajaxSearch"
    VXINSTAGRAM_URL = "https://vxinstagram.com"
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
        Raises VideoNotFoundError or DownloadError on failure.
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
            response = requests.post(
                cls.SAVEGRAM_API_URL, headers=cls.HEADERS, data=data
            )
            response.raise_for_status()
        except Exception as e:
            raise DownloadError("Error contacting Instagram API")

        try:
            json_resp = response.json()
        except Exception as e:
            raise DownloadError("Invalid response from Instagram API")

        if json_resp.get("status") != "ok" or "data" not in json_resp:
            raise VideoNotFoundError("Video not found")

        # Extract the download URL from the HTML in json_resp["data"]
        html_data = json_resp["data"]
        # The download URL is in an <a href="..."> tag with class "abutton is-success"
        # Use regex to extract the href link for the video download
        match = re.search(
            r'<a href="([^"]+)"[^>]*class="abutton is-success[^"]*"[^>]*title="Descargar video"',
            html_data,
        )
        if not match:
            raise VideoNotFoundError("Video not found")

        download_url = match.group(1)

        # Download the video content
        try:
            video_response = requests.get(
                download_url,
                headers={"User-Agent": cls.HEADERS["User-Agent"]},
                stream=True,
            )
            video_response.raise_for_status()
        except Exception as e:
            raise DownloadError("Error downloading video")

        # Save the video content to save_path
        try:
            with open(save_path, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            raise DownloadError("Error saving video file")

        return save_path

    @classmethod
    def get_video_url(cls, instagram_url: str) -> str:
        """
        Gets the direct video URL from an Instagram URL.
        Returns the direct video URL without downloading.
        Raises VideoNotFoundError or DownloadError on failure.
        """
        video_id = None
        url_match = re.search(r"instagram\.com/(?:p|reel|tv)/([^/?]+)", instagram_url)
        if url_match:
            video_id = url_match.group(1)
            print(f"[GET_URL] Extracted video_id: {video_id}")
        else:
            raise DownloadError("Could not extract video ID from URL")

        vx_url = f"{cls.VXINSTAGRAM_URL}/reel/{video_id}"
        print(f"[GET_URL] Request URL: {vx_url}")

        try:
            response = requests.get(
                vx_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
                },
                timeout=30,
            )
            response.raise_for_status()
        except Exception as e:
            raise DownloadError("Error contacting vxinstagram.com")

        html_content = response.text

        download_url = None

        og_video_match = re.search(
            r'<meta\s+property="og:video"\s+content="([^"]+)"', html_content
        )
        if og_video_match:
            content_url = og_video_match.group(1)
            rapidsave_match = re.search(r"rapidsaveUrl=([^&]+)", content_url)
            if rapidsave_match:
                download_url = rapidsave_match.group(1)
                print(f"[GET_URL] Extracted rapidsaveUrl from og:video")

        if not download_url:
            og_video_secure_match = re.search(
                r'<meta\s+property="og:video:secure_url"\s+content="([^"]+)"',
                html_content,
            )
            if og_video_secure_match:
                content_url = og_video_secure_match.group(1)
                rapidsave_match = re.search(r"rapidsaveUrl=([^&]+)", content_url)
                if rapidsave_match:
                    download_url = rapidsave_match.group(1)
                    print(f"[GET_URL] Extracted rapidsaveUrl from og:video:secure_url")

        if not download_url:
            raise VideoNotFoundError("Video not found in vxinstagram.com")

        print(f"[GET_URL] Download URL: {download_url}")
        return download_url

    @classmethod
    def download_video_with_vxinstagram(
        cls, instagram_url: str, save_path: str
    ) -> str:
        """
        Downloads Instagram video using vxinstagram.com as fallback.
        Returns the path to the saved video file.
        Raises VideoNotFoundError or DownloadError on failure.
        """
        video_id = None
        url_match = re.search(r"instagram\.com/(?:p|reel|tv)/([^/?]+)", instagram_url)
        if url_match:
            video_id = url_match.group(1)
            print(f"[VXINSTAGRAM] Extracted video_id: {video_id}")
        else:
            raise DownloadError("Could not extract video ID from URL")

        vx_url = f"{cls.VXINSTAGRAM_URL}/reel/{video_id}"
        print(f"[VXINSTAGRAM] Request URL: {vx_url}")

        try:
            response = requests.get(
                vx_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
                },
                timeout=30,
            )
            response.raise_for_status()
        except Exception as e:
            raise DownloadError("Error contacting vxinstagram.com")

        html_content = response.text

        download_url = None

        og_video_match = re.search(
            r'<meta\s+property="og:video"\s+content="([^"]+)"', html_content
        )
        if og_video_match:
            content_url = og_video_match.group(1)
            rapidsave_match = re.search(r"rapidsaveUrl=([^&]+)", content_url)
            if rapidsave_match:
                download_url = rapidsave_match.group(1)
                print(f"[VXINSTAGRAM] Extracted rapidsaveUrl from og:video")

        if not download_url:
            og_video_secure_match = re.search(
                r'<meta\s+property="og:video:secure_url"\s+content="([^"]+)"',
                html_content,
            )
            if og_video_secure_match:
                content_url = og_video_secure_match.group(1)
                rapidsave_match = re.search(r"rapidsaveUrl=([^&]+)", content_url)
                if rapidsave_match:
                    download_url = rapidsave_match.group(1)
                    print(f"[VXINSTAGRAM] Extracted rapidsaveUrl from og:video:secure_url")

        if not download_url:
            raise VideoNotFoundError("Video not found in vxinstagram.com")

        print(f"[VXINSTAGRAM] Download URL: {download_url}")

        try:
            video_response = requests.get(
                download_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0"
                },
                stream=True,
                timeout=120,
            )
            video_response.raise_for_status()
        except Exception as e:
            raise DownloadError("Error downloading video")

        try:
            with open(save_path, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            raise DownloadError("Error saving video file")

        return save_path
