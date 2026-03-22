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
        "https://iv.nbojb.com",
        "https://iv.didthis.net",
        "https://iv.1d4.us",
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

        for fmt in all_formats:
            url = fmt.get("url", "")
            if url and not url.startswith("https://i.ytimg.com/sb/"):
                return url

        return all_formats[0].get("url") or ""

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
            "nocheckcertificate": True,
            "prefer_insecure": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    @classmethod
    async def get_video_info(cls, video_id: str) -> Dict[str, Any]:
        try:
            return await cls._get_video_info_yt_dlp(video_id)
        except Exception:
            pass

        for instance in cls.INVIDIOUS_INSTANCES:
            try:
                data = cls._get_video_info_invidious(instance, video_id)
                if data:
                    return data
            except Exception:
                pass

        raise DownloadError("All methods failed")

    @classmethod
    async def get_duration(cls, video_id: str) -> int:
        info = await cls.get_video_info(video_id)
        length = info.get("lengthSeconds")
        if length is not None:
            return int(length)

        duration = info.get("duration")
        if duration:
            return int(duration)

        return 0

    @classmethod
    def _get_stream_url_yt_dlp(cls, video_id: str) -> str:
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "prefer_insecure": True,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise DownloadError("No info returned from yt-dlp")

            direct_url = info.get("url") or ""
            if direct_url and not direct_url.startswith("https://i.ytimg.com/sb/"):
                return direct_url

            formats = info.get("formats") or []
            for fmt in formats:
                fmt_url = fmt.get("url") or ""
                if fmt_url and not fmt_url.startswith("https://i.ytimg.com/sb/"):
                    return fmt_url

            if direct_url:
                return direct_url

            raise DownloadError("No valid stream URL from yt-dlp")

    @classmethod
    async def get_stream_url(cls, video_id: str) -> str:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._get_stream_url_yt_dlp, video_id)
        except Exception:
            pass

        for instance in cls.INVIDIOUS_INSTANCES:
            try:
                url = cls._get_stream_url_from_invidious(instance, video_id)
                if url:
                    return url
            except Exception:
                pass

        raise DownloadError("Could not get stream URL from any service")

    @classmethod
    async def download_video(cls, video_id: str, save_path: str) -> str:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, cls._download_yt_dlp, video_id, save_path)
            if os.path.exists(save_path) and os.path.getsize(save_path) > 10240:
                return save_path
        except Exception:
            pass

        for instance in cls.INVIDIOUS_INSTANCES:
            try:
                stream_url = cls._get_stream_url_from_invidious(instance, video_id)
                if stream_url and not stream_url.startswith("https://i.ytimg.com/sb/"):
                    cls._download_file(stream_url, save_path)
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 10240:
                        return save_path
            except Exception:
                pass

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
            "nocheckcertificate": True,
            "prefer_insecure": True,
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
