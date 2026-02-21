import os
import re
import requests
from fastapi import HTTPException
from typing import Optional


class VideoNotFoundError(Exception):
    """Excepción cuando el video no existe o no se puede encontrar"""

    pass


class DownloadError(Exception):
    """Excepción cuando falla la descarga del video"""

    pass


class FacebookService:
    FSAVE_API_URL = "https://fsave.net/proxy.php"
    FIXACEBOOK_URL = "https://www.fixacebook.com/share/v/{share_id}"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0",
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://fsave.net",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Referer": "https://fsave.net/es/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0",
        "TE": "trailers",
    }

    @classmethod
    def get_video_url(cls, facebook_url: str, is_share_type: bool = False, original_share_id: Optional[str] = None) -> str:
        """
        Gets the direct video URL from a Facebook URL.
        Returns the direct video URL without downloading.
        Raises VideoNotFoundError or DownloadError on failure.
        """
        if is_share_type and original_share_id:
            url = cls.FIXACEBOOK_URL.format(share_id=original_share_id)
        else:
            url = facebook_url
        
        print(f"[GET_URL] Request URL: {url}")

        try:
            response = requests.get(url, headers=cls.HEADERS, timeout=30)
            response.raise_for_status()
        except Exception as e:
            raise DownloadError(f"Error contacting fixacebook.com: {e}")

        html_content = response.text

        video_urls = []
        
        twitter_stream_match = re.search(
            r'<meta\s+name="twitter:player:stream"\s+content="([^"]+)"',
            html_content
        )
        if twitter_stream_match:
            video_urls.append(twitter_stream_match.group(1))

        og_video_match = re.search(
            r'<meta\s+property="og:video"\s+content="([^"]+)"',
            html_content
        )
        if og_video_match:
            video_urls.append(og_video_match.group(1))

        if not video_urls:
            raise VideoNotFoundError("No video URLs found in fixacebook response")

        return video_urls[0]

    @classmethod
    def download_video_with_requests(cls, facebook_url: str, save_path: str) -> str:
        """
        Descarga un video de Facebook usando la API de fsave.net como método alternativo.
        Devuelve la ruta al archivo guardado.
        Lanza VideoNotFoundError o DownloadError en caso de error.
        """
        data = {"url": facebook_url}
        try:
            response = requests.post(cls.FSAVE_API_URL, headers=cls.HEADERS, data=data)
            response.raise_for_status()
        except Exception as e:
            raise DownloadError("Error contacting Facebook API")

        try:
            json_resp = response.json()
        except Exception as e:
            raise DownloadError("Invalid response from Facebook API")

        # El parámetro que nos interesa es previewUrl
        preview_url = None
        if "api" in json_resp and "previewUrl" in json_resp["api"]:
            preview_url = json_resp["api"]["previewUrl"]
        if not preview_url:
            raise VideoNotFoundError("Video not found")

        # Descargar el video
        try:
            video_response = requests.get(
                preview_url,
                headers={"User-Agent": cls.HEADERS["User-Agent"]},
                stream=True,
            )
            video_response.raise_for_status()
        except Exception as e:
            raise DownloadError("Error downloading video")

        # Guardar el video
        try:
            with open(save_path, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            raise DownloadError("Error saving video file")

        return save_path

    @classmethod
    def download_video_from_fixacebook(cls, share_id: str, save_path: str) -> str:
        """
        Descarga un video de Facebook usando fixacebook.com para videos tipo share.
        Devuelve la ruta al archivo guardado.
        Lanza VideoNotFoundError o DownloadError en caso de error.
        """
        url = cls.FIXACEBOOK_URL.format(share_id=share_id)
        
        try:
            response = requests.get(url, headers=cls.HEADERS, timeout=30)
            response.raise_for_status()
        except Exception as e:
            raise DownloadError(f"Error contacting fixacebook.com: {e}")

        html_content = response.text

        video_urls = []
        
        twitter_stream_match = re.search(
            r'<meta\s+name="twitter:player:stream"\s+content="([^"]+)"',
            html_content
        )
        if twitter_stream_match:
            video_urls.append(twitter_stream_match.group(1))

        og_video_match = re.search(
            r'<meta\s+property="og:video"\s+content="([^"]+)"',
            html_content
        )
        if og_video_match:
            video_urls.append(og_video_match.group(1))

        if not video_urls:
            raise VideoNotFoundError("No video URLs found in fixacebook response")

        last_error = None
        for video_url in video_urls:
            try:
                video_response = requests.get(
                    video_url,
                    headers={"User-Agent": cls.HEADERS["User-Agent"]},
                    stream=True,
                    timeout=60,
                )
                video_response.raise_for_status()
            except Exception as e:
                last_error = e
                print(f"Failed to download from {video_url[:50]}..., trying next URL...")
                continue

            try:
                with open(save_path, "wb") as f:
                    for chunk in video_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return save_path
            except Exception as e:
                last_error = e
                if os.path.exists(save_path):
                    os.remove(save_path)
                print(f"Failed to save video from {video_url[:50]}..., trying next URL...")
                continue

        raise DownloadError(f"Failed to download video from all sources: {last_error}")
