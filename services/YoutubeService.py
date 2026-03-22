import os
import re
import requests
import yt_dlp
import asyncio
from typing import Optional, Dict, Any


class VideoNotFoundError(Exception):
    pass


class DownloadError(Exception):
    pass


class YoutubeService:
    INVIDIOUS_INSTANCES = [
        "https://inv.nadeko.net",
        "https://yewtu.be",
        "https://invidious.nerdvpn.de",
    ]
    DURATION_THRESHOLD_SECONDS = 480
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US;q=0.7,en;q=0.3",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
    }

    @classmethod
    def _get_video_info_invidious(cls, instance: str, video_id: str) -> Dict[str, Any]:
        url = f"{instance}/api/v1/videos/{video_id}"
        response = requests.get(url, headers=cls.HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise DownloadError(f"Invidious error: {data.get('error')}")
        return data

    @classmethod
    def _get_stream_url_from_invidious(cls, instance: str, video_id: str) -> str:
        data = cls._get_video_info_invidious(instance, video_id)
        format_streams = data.get("formatStreams") or []
        adaptive_formats = data.get("adaptiveFormats") or []
        all_formats = format_streams + adaptive_formats

        if not all_formats:
            raise DownloadError("No format streams available")

        best = all_formats[0]
        return best.get("url") or ""

    @classmethod
    async def _get_video_info_yt_dlp(cls, video_id: str) -> Dict[str, Any]:
        url = f"https://www.youtube.com/watch?v={video_id}"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, cls._extract_yt_dlp_info, url)

    @classmethod
    def _extract_yt_dlp_info(cls, url: str) -> Dict[str, Any]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "geo_bypass": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    @classmethod
    async def get_video_info(cls, video_id: str) -> Dict[str, Any]:
        for instance in cls.INVIDIOUS_INSTANCES:
            try:
                data = cls._get_video_info_invidious(instance, video_id)
                if data:
                    return data
            except Exception:
                pass

        try:
            return await cls._get_video_info_yt_dlp(video_id)
        except Exception as e:
            raise DownloadError(f"All methods failed: {e}")

    @classmethod
    async def get_duration(cls, video_id: str) -> int:
        info = await cls.get_video_info(video_id)
        return int(info.get("lengthSeconds", 0))

    @classmethod
    async def get_stream_url(cls, video_id: str) -> str:
        for instance in cls.INVIDIOUS_INSTANCES:
            try:
                url = cls._get_stream_url_from_invidious(instance, video_id)
                if url:
                    return url
            except Exception:
                pass

        loop = asyncio.get_event_loop()
        try:
            info = await loop.run_in_executor(
                None, cls._extract_yt_dlp_info, f"https://www.youtube.com/watch?v={video_id}"
            )
            formats = info.get("formats") or []
            if formats:
                best = formats[0]
                return best.get("url") or ""
        except Exception:
            pass

        raise DownloadError("Could not get stream URL from any service")

    @classmethod
    async def download_video(cls, video_id: str, save_path: str) -> str:
        for instance in cls.INVIDIOUS_INSTANCES:
            try:
                stream_url = cls._get_stream_url_from_invidious(instance, video_id)
                if stream_url:
                    cls._download_file(stream_url, save_path)
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 10240:
                        return save_path
            except Exception:
                pass

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, cls._download_yt_dlp, video_id, save_path
        )
        if os.path.exists(save_path) and os.path.getsize(save_path) > 10240:
            return save_path

        raise DownloadError("Download failed with all methods")

    @classmethod
    def _download_file(cls, url: str, save_path: str) -> str:
        response = requests.get(url, headers=cls.HEADERS, stream=True, timeout=120)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return save_path

    @classmethod
    def _download_yt_dlp(cls, video_id: str, save_path: str) -> None:
        url = f"https://www.youtube.com/watch?v={video_id}"
        directory = os.path.dirname(save_path)
        filename_without_ext = os.path.splitext(os.path.basename(save_path))[0]
        ydl_opts = {
            "outtmpl": os.path.join(directory, f"{filename_without_ext}.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "geo_bypass": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        expected_ext = "mp4"
        actual_path = os.path.join(directory, f"{filename_without_ext}.{expected_ext}")
        if os.path.exists(actual_path):
            if save_path != actual_path:
                os.rename(actual_path, save_path)
        elif not os.path.exists(save_path):
            raise DownloadError("yt-dlp did not produce expected file")
